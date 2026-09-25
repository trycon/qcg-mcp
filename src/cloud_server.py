"""Scanova MCP server over Streamable HTTP (production entry point, see Dockerfile).

The MCP protocol itself is served by the MCP Python SDK 2.x
(``mcp_http/sdk_server.py``): dual-era — the 2026-07-28 stateless protocol and
the legacy ``initialize`` handshake — in stateless JSON-response mode. This
module adds what's specific to hosting Scanova's server:

- the non-MCP routes (health, OAuth protected-resource metadata, the OpenAI
  Apps challenge, a service description at ``/``);
- lazy authentication: discovery (``tools/list``, UI resources…) is public, but
  a request that needs a Scanova credential and has none gets HTTP 401 with a
  ``WWW-Authenticate`` challenge, so OAuth-capable clients start sign-in;
- a keep-alive ``GET /mcp`` stream for legacy clients that treat a 405 there
  as the connector being down (claude.ai's connector proxy);
- per-caller rate limits (HTTP 429 with Retry-After);
- CORS, and optional Host/Origin checks (see config.ALLOWED_ORIGINS).
"""

import json
import logging
import math
import os

import anyio
import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from config import (
    ALLOWED_HOSTS,
    ALLOWED_ORIGINS,
    ANON_RATE_LIMIT_PER_MINUTE,
    MCP_RESOURCE_URL,
    OAUTH_SERVER_URL,
    OPENAI_APPS_CHALLENGE,
    RATE_LIMIT_BURST,
    RATE_LIMIT_PER_MINUTE,
)
from mcp_http.rate_limit import RateLimiter, credential_key
from mcp_http.sdk_server import SERVER_VERSION, api_key_from_headers, build_server

log = logging.getLogger("mcp")

MCP_PATH = "/mcp"

# Methods that never touch a customer's Scanova data: no credential required.
PUBLIC_METHODS = frozenset({
    "initialize",
    "server/discover",
    "ping",
    "tools/list",
    "resources/list",
    "resources/read",
    "resources/templates/list",
})

RESOURCE_METADATA_URL = f"{MCP_RESOURCE_URL}/.well-known/oauth-protected-resource/mcp"
WWW_AUTHENTICATE = f'Bearer realm="Scanova MCP", resource_metadata="{RESOURCE_METADATA_URL}"'

SERVICE_INFO = {
    "service": "Scanova MCP Server",
    "version": SERVER_VERSION,
    "endpoints": {"mcp": MCP_PATH, "health": "/health"},
    "authentication": {
        "required": "Scanova API Key or OAuth access token",
        "headers": ["Authorization", "X-API-Key", "Scanova-API-Key"],
        "note": "Configure your Scanova API key in your MCP client headers",
    },
}


# --------------------------------------------------------------------------- #
# Non-MCP routes
# --------------------------------------------------------------------------- #

def _protected_resource(_: Request) -> JSONResponse:
    return JSONResponse({"resource": MCP_RESOURCE_URL, "authorization_servers": [OAUTH_SERVER_URL] if OAUTH_SERVER_URL else []})


def _health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "scanova-mcp"})


def _openai_challenge(_: Request) -> PlainTextResponse:
    return PlainTextResponse(OPENAI_APPS_CHALLENGE or "No challenge token configured")


def _root(_: Request) -> JSONResponse:
    return JSONResponse(SERVICE_INFO)


ROUTES = [
    Route("/health", _health, methods=["GET"]),
    Route("/.well-known/oauth-protected-resource", _protected_resource, methods=["GET"]),
    Route("/.well-known/oauth-protected-resource/mcp", _protected_resource, methods=["GET"]),
    Route("/mcp/.well-known/oauth-protected-resource", _protected_resource, methods=["GET"]),
    Route("/.well-known/openai-apps-challenge", _openai_challenge, methods=["GET"]),
    Route("/", _root, methods=["GET", "POST"]),
]


# --------------------------------------------------------------------------- #
# Front layer for /mcp: lazy auth and the legacy GET stream
# --------------------------------------------------------------------------- #

# The keep-alive GET stream: a comment every 25 s (under common proxy idle
# timeouts), closed after 10 minutes so idle clients don't hold a connection
# forever; a client that wants it again simply reconnects.
GET_STREAM_HEARTBEAT_S = 25
GET_STREAM_MAX_S = 600


def _methods(body: bytes) -> list[str] | None:
    """JSON-RPC method names in a request body; None if it isn't valid JSON-RPC."""
    try:
        parsed = json.loads(body or b"null")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    messages = parsed if isinstance(parsed, list) else [parsed]
    if not messages or not all(isinstance(m, dict) for m in messages):
        return None
    return [m["method"] for m in messages if isinstance(m.get("method"), str)]


def _needs_credential(methods: list[str]) -> bool:
    return any(m not in PUBLIC_METHODS and not m.startswith("notifications/") for m in methods)


def _client_ip(scope: Scope) -> str:
    # Behind the load balancer the caller is the first X-Forwarded-For hop.
    forwarded = Request(scope).headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


def _rate_limited(retry_after: float) -> JSONResponse:
    seconds = max(1, math.ceil(retry_after))
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32000, "message": f"Rate limit exceeded; retry in {seconds}s", "data": {"retryAfter": seconds}},
        },
        status_code=429,
        headers={"Retry-After": str(seconds)},
    )


class McpFrontMiddleware:
    """Runs in front of the SDK's /mcp endpoint; everything else passes through."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.credential_limiter = RateLimiter(RATE_LIMIT_PER_MINUTE, RATE_LIMIT_BURST)
        self.anonymous_limiter = RateLimiter(ANON_RATE_LIMIT_PER_MINUTE)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].rstrip("/") != MCP_PATH:
            await self.app(scope, receive, send)
            return
        method = scope["method"]
        if method == "GET":
            await self._keepalive_stream(send)
            return
        if method != "POST":
            await self.app(scope, receive, send)
            return

        # Buffer the body to see which method is being called, then replay it.
        chunks: list[bytes] = []
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunks.append(message.get("body", b""))
            more = message.get("more_body", False)
        body = b"".join(chunks)

        methods = _methods(body)
        credential = api_key_from_headers(Request(scope).headers)
        needs_credential = methods is not None and _needs_credential(methods)
        if needs_credential and not credential:
            log.warning("Unauthorized MCP request: %s", ",".join(methods))
            response = JSONResponse(
                {"error": "unauthorized", "message": "Valid Bearer token required"},
                status_code=401,
                headers={"WWW-Authenticate": WWW_AUTHENTICATE},
            )
            await response(scope, receive, send)
            return

        # A batch costs one token per message; a malformed body still costs one.
        cost = max(1, len(methods or []))
        if needs_credential:
            wait = self.credential_limiter.acquire(credential_key(credential), cost)
        else:
            wait = self.anonymous_limiter.acquire("ip:" + _client_ip(scope), cost)
        if wait:
            log.warning("Rate limited MCP request: %s", ",".join(methods or ["?"]))
            await _rate_limited(wait)(scope, receive, send)
            return

        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)

    @staticmethod
    async def _keepalive_stream(send: Send) -> None:
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/event-stream"), (b"cache-control", b"no-cache")],
        })
        await send({"type": "http.response.body", "body": b": connected\n\n", "more_body": True})
        with anyio.move_on_after(GET_STREAM_MAX_S):
            while True:
                await anyio.sleep(GET_STREAM_HEARTBEAT_S)
                await send({"type": "http.response.body", "body": b": keepalive\n\n", "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #

def _transport_security() -> TransportSecuritySettings:
    # The server accepts any compliant client by default (ALLOWED_ORIGINS="*"),
    # which the SDK's Host/Origin checks can't express; they switch on as soon
    # as an explicit origin list is configured.
    if ALLOWED_ORIGINS == ["*"]:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=ALLOWED_HOSTS, allowed_origins=ALLOWED_ORIGINS)


def build_app() -> ASGIApp:
    sdk_app = build_server().streamable_http_app(
        streamable_http_path=MCP_PATH,
        stateless_http=True,
        json_response=True,
        transport_security=_transport_security(),
        host=os.getenv("HOST", "0.0.0.0"),
        custom_starlette_routes=ROUTES,
    )
    return CORSMiddleware(
        McpFrontMiddleware(sdk_app),
        allow_origins=ALLOWED_ORIGINS,
        # Credentials travel in headers, never cookies; with "*" origins a
        # credentialed CORS response would effectively allow any site.
        allow_credentials=ALLOWED_ORIGINS != ["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["WWW-Authenticate"],
    )


# The SDK app's lifespan runs its session manager; the wrappers pass lifespan
# events through, so uvicorn drives it as usual.
app = build_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    log.info("Starting Scanova MCP Server on %s:%s (MCP endpoint %s)", host, port, MCP_PATH)
    uvicorn.run(app, host=host, port=port)
