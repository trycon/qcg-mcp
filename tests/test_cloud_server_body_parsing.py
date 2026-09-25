"""Malformed requests to POST /mcp are client errors: HTTP 400 with a JSON-RPC
parse error, never a 500 — the SDK's transport handles this since the 2.x
upgrade; these keep it that way."""

from conftest import post_raw, rpc


def test_empty_body_returns_400_parse_error():
    resp = post_raw(b"")
    assert resp.status_code == 400
    body = resp.json()
    assert body["jsonrpc"] == "2.0"
    assert body["id"] is None
    assert body["error"]["code"] == -32700


def test_malformed_body_returns_400_parse_error():
    resp = post_raw(b"not json")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == -32700


def test_valid_request_still_works():
    assert rpc("initialize", {"id": 1})["result"]["serverInfo"]["name"] == "scanova-mcp"
