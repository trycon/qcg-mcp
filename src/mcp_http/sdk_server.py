"""The Scanova MCP server on the MCP Python SDK 2.x lowlevel ``Server``.

The SDK now owns the protocol: the Streamable HTTP transport, dual-era
support (2026-07-28 stateless requests *and* the legacy ``initialize``
handshake used by today's IDE and ChatGPT/claude.ai clients),
``server/discover``, ``resultType``, cache hints, header validation and
JSON-RPC error codes. This module only supplies Scanova's content:

- tools come from ``registry.list_mcp_tools()`` — the single source of truth
  for names, input/output schemas, annotations and UI ``_meta`` (the SDK's
  high-level ``MCPServer`` derives schemas from Python signatures, which is
  how the old stdio tool list drifted from the HTTP one);
- tool calls run the existing dispatcher → normalizer → UI metadata pipeline;
- resources are the static UI assets in ``ui_resources``.

The lowlevel ``Server`` is used rather than ``MCPServer`` precisely so the
hand-written schemas in ``registry.py`` are served verbatim.
"""

import json
import logging
import os
from typing import Any

import anyio
import mcp.types as types
from mcp.server.apps import EXTENSION_ID as APPS_EXTENSION_ID
from mcp.server.caching import CacheHint
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.shared.exceptions import MCPError

from config import MCP_ACCESS_TOKEN, UI_ELEMENTS_ENABLED
from mcp_http.dispatcher import execute_tool
from mcp_http.normalizer import normalize
from mcp_http.registry import list_mcp_tools
from mcp_http.ui_resources import get_resource_by_uri, list_resources, read_resource_contents
from mcp_http.ui_response import attach_ui_metadata

log = logging.getLogger("mcp")

SERVER_NAME = "scanova-mcp"
# The release the image was built from (deploy.yml → Dockerfile APP_VERSION), e.g. "v2.1.0".
SERVER_VERSION = os.getenv("APP_VERSION", "dev").removeprefix("v")

# Headers a Scanova API key or OAuth access token may arrive in. The README has
# always told users to put the raw key in Authorization (no "Bearer"), so every
# form keeps working; the value is passed to the Scanova API as-is.
_KEY_HEADERS = ("x-api-key", "scanova-api-key", "api-key")

EXPIRED_KEY_MESSAGE = (
    "Your Scanova session has expired or the API key is invalid. "
    "Please reconnect your Scanova API key in your MCP client settings."
)


def api_key_from_headers(headers: Any) -> str | None:
    """The caller's Scanova credential from request headers, or None."""
    if headers is None:
        return None
    auth = headers.get("authorization")
    if auth:
        return auth
    for name in _KEY_HEADERS:
        value = headers.get(name)
        if value:
            return value
    return None


def _tool_descriptors() -> list[dict]:
    return list_mcp_tools()


def _tool_names() -> set[str]:
    return {t["name"] for t in _tool_descriptors()}


async def list_tools(ctx: ServerRequestContext[Any], params: types.PaginatedRequestParams | None) -> types.ListToolsResult:
    # Static and identical for every caller, in a fixed order (cacheable, see CACHE_HINTS).
    return types.ListToolsResult(tools=[types.Tool.model_validate(t) for t in _tool_descriptors()])


def _error_result(text: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)


async def call_tool(ctx: ServerRequestContext[Any], params: types.CallToolRequestParams) -> types.CallToolResult:
    name = params.name
    if name not in _tool_names():
        # An unknown tool is a protocol error (the model can't fix it by retrying).
        raise MCPError(types.INVALID_PARAMS, f"Unknown tool: {name}")

    request = ctx.request
    # Over HTTP the caller's own credential; over stdio (no request) the local
    # MCP_ACCESS_TOKEN, as the old stdio server did.
    api_key = api_key_from_headers(request.headers) if request is not None else (MCP_ACCESS_TOKEN or None)
    arguments = dict(params.arguments or {})

    try:
        # The dispatcher calls the Scanova API with blocking `requests`; run it off
        # the event loop so one slow call doesn't stall every other request.
        raw = await anyio.to_thread.run_sync(execute_tool, name, arguments, api_key)
    except Exception:
        log.exception("Tool %s raised", name)
        # Never leak exception text to the client; the log has the traceback.
        return _error_result(f"Error executing tool {name}. Please try again.")

    envelope = normalize(raw, name)
    if isinstance(envelope, dict) and envelope.get("status_code") == 401:
        envelope["error"] = EXPIRED_KEY_MESSAGE
    built = attach_ui_metadata(name, envelope)
    envelope = built["envelope"]
    # A failed Scanova call is a tool execution error the model can read and act on.
    failed = isinstance(envelope, dict) and envelope.get("ok") is False
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(envelope))],
        # window.openai.toolOutput and MCP Apps widgets are hydrated from structuredContent.
        structured_content=envelope,
        is_error=failed,
        meta=built["meta"],
    )


async def list_resources_handler(
    ctx: ServerRequestContext[Any], params: types.PaginatedRequestParams | None
) -> types.ListResourcesResult:
    return types.ListResourcesResult(
        resources=[
            types.Resource(uri=r.versioned_uri, name=r.file_path, mime_type=r.mime_type, meta=r.meta)
            for r in list_resources()
        ]
    )


async def read_resource(ctx: ServerRequestContext[Any], params: types.ReadResourceRequestParams) -> types.ReadResourceResult:
    uri = str(params.uri)
    resource = get_resource_by_uri(uri)
    contents = read_resource_contents(uri) if resource else None
    if resource is None or contents is None:
        raise MCPError(types.INVALID_PARAMS, f"Resource not found: {uri}", {"uri": uri})
    return types.ReadResourceResult(
        contents=[types.TextResourceContents(uri=resource.versioned_uri, mime_type=resource.mime_type, text=contents, meta=resource.meta)]
    )


# Tool and resource lists are the same for every caller and change only on deploy.
# UI resources are versioned (content-hashed URIs), so they can be cached longer.
CACHE_HINTS = {
    "tools/list": CacheHint(ttl_ms=60 * 60 * 1000, scope="public"),
    "resources/list": CacheHint(ttl_ms=60 * 60 * 1000, scope="public"),
    "resources/read": CacheHint(ttl_ms=24 * 60 * 60 * 1000, scope="public"),
}


def build_server() -> Server:
    server = Server(
        SERVER_NAME,
        version=SERVER_VERSION,
        title="Scanova",
        description="Create, design and manage Scanova QR codes, folders, forms, leads, analytics and users.",
        website_url="https://scanova.io",
        cache_hints=CACHE_HINTS,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
        on_list_resources=list_resources_handler,
        on_read_resource=read_resource,
    )
    if UI_ELEMENTS_ENABLED:
        # MCP Apps (SEP-2133): tools carry `_meta.ui.resourceUri` → `ui://` HTML resources.
        server.extensions[APPS_EXTENSION_ID] = {}
    return server
