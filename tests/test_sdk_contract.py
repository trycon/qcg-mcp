"""
Contract tests: every result the server sends over HTTP validates against the
official `mcp` SDK's own Pydantic result models.

Since the SDK 2.x upgrade the SDK serves the protocol itself
(mcp_http/sdk_server.py); these now guard Scanova's content (tool
descriptors, UI `_meta`, resources) rather than a hand-rolled JSON-RPC layer.
"""

from mcp.types import (
    CallToolResult,
    InitializeResult,
    ListResourcesResult,
    ListToolsResult,
    ReadResourceResult,
)

import mcp_http.sdk_server as sdk_server
from conftest import rpc


def test_initialize_result_matches_sdk_model():
    result = rpc("initialize", {"id": 1}, api_key="k")
    InitializeResult.model_validate(result["result"])


def test_tools_list_result_matches_sdk_model():
    result = rpc("tools/list", {"id": 2}, api_key="k")
    ListToolsResult.model_validate(result["result"])


def test_resources_list_result_matches_sdk_model():
    result = rpc("resources/list", {"id": 3}, api_key=None)
    ListResourcesResult.model_validate(result["result"])


def test_resources_read_result_matches_sdk_model():
    body = {"id": 4, "params": {"uri": "ui://scanova/qr-design.html"}}
    result = rpc("resources/read", body, api_key=None)
    ReadResourceResult.model_validate(result["result"])


def test_tools_call_result_matches_sdk_model_without_ui_meta(monkeypatch):
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: {"ok": True})
    body = {"id": 5, "params": {"name": "query_docs", "arguments": {}}}
    result = rpc("tools/call", body, api_key="k")
    CallToolResult.model_validate(result["result"])


def test_tools_call_result_matches_sdk_model_with_ui_meta(monkeypatch):
    import mcp_http.ui_response as ui_response

    monkeypatch.setattr(ui_response, "UI_ELEMENTS_ENABLED", True, raising=False)
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: {"id": "qr-1"})
    body = {"id": 6, "params": {"name": "set_qr_design", "arguments": {"qrid": "qr-1"}}}
    result = rpc("tools/call", body, api_key="k")
    # The SDK's Result base model accepts arbitrary extra fields via its
    # own `_meta` alias — validating here confirms our _meta attachment
    # (Part 5A) doesn't produce a shape the SDK's own model would reject.
    CallToolResult.model_validate(result["result"])
