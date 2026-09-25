"""Scanova API HTTP errors must reach the model as failures, not as successes.

Before this, every API module returned `resp.json()`: a 404/403/401 body such
as {"detail": "Not found."} was normalized to ok=true, status 200."""

import qrcode as qrcode_api
from api_response import api_result
from conftest import CLIENT_META, MODERN, post
from mcp_http.normalizer import normalize


class _Resp:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


def test_success_bodies_pass_through_unchanged():
    assert api_result(_Resp(200, {"qrid": "Q1"})) == {"qrid": "Q1"}
    assert api_result(_Resp(200, [1, 2])) == [1, 2]
    assert api_result(_Resp(204)) == {"success": True, "status_code": 204}


def test_http_errors_keep_their_body_and_status():
    assert api_result(_Resp(404, {"detail": "Not found."})) == {"error": {"detail": "Not found."}, "status_code": 404}
    assert api_result(_Resp(502, text="Bad Gateway")) == {"error": "Bad Gateway", "status_code": 502}
    assert api_result(_Resp(500)) == {"error": "Scanova API returned HTTP 500", "status_code": 500}


def test_normalizer_reports_the_real_status():
    for status in (401, 403, 404, 429, 500):
        env = normalize(api_result(_Resp(status, {"detail": "x"})), "retrieve_qr_code")
        assert env["ok"] is False and env["status_code"] == status


def test_a_scanova_404_is_a_tool_error_end_to_end(monkeypatch):
    monkeypatch.setattr(qrcode_api.requests, "get", lambda *a, **k: _Resp(404, {"detail": "Not found."}))
    resp = post(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "retrieve_qr_code", "arguments": {"qrid": "missing"}, "_meta": CLIENT_META}},
        {"authorization": "k", "mcp-protocol-version": MODERN, "mcp-method": "tools/call", "mcp-name": "retrieve_qr_code"},
    )
    result = resp.json()["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["status_code"] == 404
    assert "Not found." in result["content"][0]["text"]


def test_an_expired_key_now_triggers_the_reconnect_message(monkeypatch):
    monkeypatch.setattr(qrcode_api.requests, "get", lambda *a, **k: _Resp(401, {"detail": "Invalid token."}))
    resp = post(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_qr_codes", "arguments": {}, "_meta": CLIENT_META}},
        {"authorization": "expired", "mcp-protocol-version": MODERN, "mcp-method": "tools/call", "mcp-name": "list_qr_codes"},
    )
    assert "reconnect your Scanova API key" in resp.json()["result"]["content"][0]["text"]
