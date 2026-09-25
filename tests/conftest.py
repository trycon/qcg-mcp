"""Shared test helpers: drive the real server app over HTTP, as a client would.

`rpc()` replaces the old hand-rolled `protocol.handle_tool_method()`: it posts
a JSON-RPC request to `cloud_server.app` (the SDK-served endpoint) and returns
the JSON-RPC response dict. Modern (2026-07-28) requests by default; `initialize`
and `era="legacy"` use the pre-2026 handshake-era wire.
"""

import pytest
from starlette.testclient import TestClient

MODERN = "2026-07-28"
LEGACY = "2025-06-18"
CLIENT_META = {
    "io.modelcontextprotocol/protocolVersion": MODERN,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "tests", "version": "1"},
}

_client: TestClient | None = None


@pytest.fixture(scope="session", autouse=True)
def _http_client():
    global _client
    from cloud_server import app

    with TestClient(app) as client:
        _client = client
        yield client
    _client = None


def post(body: dict, headers: dict | None = None):
    assert _client is not None
    return _client.post("/mcp", json=body, headers=headers or {})


def post_raw(content: bytes, headers: dict | None = None):
    assert _client is not None
    return _client.post("/mcp", content=content, headers={"content-type": "application/json", **(headers or {})})


def get(path: str):
    assert _client is not None
    return _client.get(path)


def rpc(method: str, body: dict | None = None, api_key: str | None = None, era: str | None = None) -> dict:
    """Send `method` with `body`'s params (and id); return the JSON-RPC response dict."""
    body = dict(body or {})
    params = dict(body.get("params") or {})
    era = era or ("legacy" if method == "initialize" else "modern")
    headers = {"accept": "application/json, text/event-stream"}
    if api_key:
        headers["authorization"] = api_key
    if era == "modern":
        params["_meta"] = {**CLIENT_META, **params.get("_meta", {})}
        headers["mcp-protocol-version"] = MODERN
        headers["mcp-method"] = method
        if method == "tools/call":
            headers["mcp-name"] = params.get("name", "")
        elif method == "resources/read":
            headers["mcp-name"] = params.get("uri", "")
    elif method == "initialize":
        params = {"protocolVersion": LEGACY, "capabilities": {}, "clientInfo": {"name": "tests", "version": "1"}, **params}
    else:
        headers["mcp-protocol-version"] = LEGACY
    message = {"jsonrpc": "2.0", "id": body.get("id", 1), "method": method}
    if params:
        message["params"] = params
    return post(message, headers).json()
