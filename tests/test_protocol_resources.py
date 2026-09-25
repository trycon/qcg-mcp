import mcp_http.sdk_server as sdk_server
from conftest import rpc
import mcp_http.ui_response as ui_response
from mcp_http.ui_resources import get_resource_for_tool


def test_legacy_initialize_negotiates_the_clients_version_and_declares_resources():
    result = rpc("initialize", {"id": 1}, api_key="k")
    assert result["result"]["protocolVersion"] == "2025-06-18"
    assert "resources" in result["result"]["capabilities"]


def test_modern_discover_declares_2026_protocol_resources_and_mcp_apps():
    result = rpc("server/discover", {"id": 1})["result"]
    assert "2026-07-28" in result["supportedVersions"]
    assert "resources" in result["capabilities"]
    assert "io.modelcontextprotocol/ui" in result["capabilities"]["extensions"]
    assert result["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "scanova-mcp"


def test_resources_list_includes_qr_design():
    result = rpc("resources/list", {"id": 2}, api_key=None)
    uris = {r["uri"] for r in result["result"]["resources"]}
    assert get_resource_for_tool("set_qr_design").versioned_uri in uris


def test_resources_read_known_uri():
    body = {"id": 3, "params": {"uri": "ui://scanova/qr-design.html"}}
    result = rpc("resources/read", body, api_key=None)
    assert "result" in result
    assert result["result"]["contents"][0]["mimeType"] == "text/html;profile=mcp-app"
    assert "<html" in result["result"]["contents"][0]["text"].lower()


def test_resources_read_declares_csp_meta():
    body = {"id": 6, "params": {"uri": "ui://scanova/qr-design.html"}}
    result = rpc("resources/read", body, api_key=None)
    csp = result["result"]["contents"][0]["_meta"]["ui"]["csp"]
    assert csp["connectDomains"] == []
    assert csp["resourceDomains"] == []


def test_resources_list_declares_csp_meta():
    result = rpc("resources/list", {"id": 2}, api_key=None)
    for r in result["result"]["resources"]:
        assert "csp" in r["_meta"]["ui"]


def test_resources_read_unknown_uri_returns_jsonrpc_error():
    body = {"id": 4, "params": {"uri": "ui://scanova/nope.html"}}
    result = rpc("resources/read", body, api_key=None)
    assert "error" in result
    # 2026-07-28: resource-not-found is Invalid Params (was -32002).
    assert result["error"]["code"] == -32602
    assert result["error"]["data"] == {"uri": "ui://scanova/nope.html"}


def test_tools_call_content_block_unchanged_for_non_ui_tool(monkeypatch):
    """Backward-compat guardrail: a non-UI-enabled tool's content[0] text
    block must be byte-identical to what it was before UI Elements existed."""
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: {"ok": True})
    body = {"id": 5, "params": {"name": "query_docs", "arguments": {}}}
    result = rpc("tools/call", body, api_key="k")
    # Results always carry the server's identity in _meta (2026-07-28); a
    # non-UI tool must not carry any UI keys there.
    meta = result["result"].get("_meta", {})
    assert "ui" not in meta and "openai/outputTemplate" not in meta
    assert result["result"]["content"][0]["type"] == "text"


def test_tools_call_includes_structured_content_for_ui_hydration(monkeypatch):
    """window.openai.toolOutput (and callTool's resolved value) hydrate from
    structuredContent, not content[0].text — a UI widget gets no data without it."""
    monkeypatch.setattr(ui_response, "UI_ELEMENTS_ENABLED", True, raising=False)
    envelope = {"ok": True, "data": {"count": 1, "results": [{"id": "qr-1"}]}, "pagination": {"count": 1, "next": None, "previous": None}}
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: envelope)
    monkeypatch.setattr(sdk_server, "normalize", lambda raw, tool_name: raw)
    body = {"id": 9, "params": {"name": "list_qr_codes", "arguments": {}}}
    result = rpc("tools/call", body, api_key="k")
    assert result["result"]["structuredContent"] == envelope


def test_tools_list_declares_meta_for_ui_enabled_tool():
    result = rpc("tools/list", {"id": 7}, api_key="k")
    tools = {t["name"]: t for t in result["result"]["tools"]}
    expected = get_resource_for_tool("get_account_stats").versioned_uri
    assert tools["get_account_stats"]["_meta"]["openai/outputTemplate"] == expected
    assert tools["get_account_stats"]["_meta"]["ui"]["resourceUri"] == expected


def test_tools_list_omits_meta_for_non_ui_tool():
    result = rpc("tools/list", {"id": 8}, api_key="k")
    tools = {t["name"]: t for t in result["result"]["tools"]}
    assert "_meta" not in tools["query_docs"]


def test_tools_list_omits_meta_for_list_qr_codes():
    """Deliberately disabled — tested and working fine as plain text."""
    result = rpc("tools/list", {"id": 10}, api_key="k")
    tools = {t["name"]: t for t in result["result"]["tools"]}
    assert "_meta" not in tools["list_qr_codes"]


def test_tools_call_attaches_meta_for_ui_enabled_tool(monkeypatch):
    monkeypatch.setattr(ui_response, "UI_ELEMENTS_ENABLED", True, raising=False)
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: {"id": "qr-1", "pattern_info": "{}"})
    body = {"id": 6, "params": {"name": "set_qr_design", "arguments": {"qrid": "qr-1"}}}
    result = rpc("tools/call", body, api_key="k")
    assert result["result"]["_meta"]["openai/outputTemplate"] == get_resource_for_tool("set_qr_design").versioned_uri
    # the text content block itself is still present and untouched in shape
    assert result["result"]["content"][0]["type"] == "text"
