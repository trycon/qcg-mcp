"""The server on MCP Python SDK 2.x: dual-era protocol, Scanova's auth rules,
and parity with the pre-upgrade tool list (tests/fixtures/v1_baseline.json,
captured from the hand-rolled server before it was replaced)."""

import json
from pathlib import Path

import anyio
import pytest

import cloud_server
import mcp_http.sdk_server as sdk_server
from conftest import CLIENT_META, LEGACY, MODERN, post, rpc

BASELINE = json.loads((Path(__file__).parent / "fixtures" / "v1_baseline.json").read_text())


def _modern_call(name, headers=None, arguments=None):
    h = {"accept": "application/json", "mcp-protocol-version": MODERN, "mcp-method": "tools/call", "mcp-name": name, **(headers or {})}
    return post({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}, "_meta": CLIENT_META}}, h)


# --- parity -------------------------------------------------------------------

# Reworked on purpose since the upgrade: annotations (tests/test_tool_annotations.py)
# and output schemas, now the real result envelope (tests/test_output_schemas.py).
_REWORKED = ("annotations", "outputSchema")


def _without_annotations(tools):
    return [{k: v for k, v in t.items() if k not in _REWORKED} for t in tools]


# Tools added since the upgrade, and tools that gained optional inputs (none removed or changed).
from mcp_http.more_tools import MORE_TOOLS  # noqa: E402

_ADDED = {"preview_qr_design", "list_custom_domains", *(t.name for t in MORE_TOOLS)}
_NEW_INPUTS = {"set_qr_design": {"accept_risk"}}
# Rewritten on purpose: create_form's old `data` ({"fields": [...]}, an object)
# never matched the API, which takes a list of blocks as a JSON string, so every
# call failed. It now takes title + questions (tests/test_more_tools.py).
_REWRITTEN = {"create_form"}


def test_tools_list_matches_the_pre_upgrade_server_on_both_eras():
    """Every original tool keeps its name, input schema and UI _meta; additions are listed above."""
    for era in ("modern", "legacy"):
        tools = rpc("tools/list", {"id": 1}, era=era)["result"]["tools"]
        assert {t["name"] for t in tools} - {t["name"] for t in BASELINE["tools"]} == _ADDED, era
        current = {t["name"]: t for t in _without_annotations(tools)}
        for before in _without_annotations(BASELINE["tools"]):
            if before["name"] in _REWRITTEN:
                assert before["name"] in current, era
                continue
            after = current[before["name"]]
            added = _NEW_INPUTS.get(before["name"], set())
            if added:
                props = {k: v for k, v in after["inputSchema"]["properties"].items() if k not in added}
                after = {**after, "inputSchema": {**after["inputSchema"], "properties": props}}
                assert set(after["inputSchema"].get("required", [])) == set(before["inputSchema"].get("required", [])), before["name"]
            assert after == before, (era, before["name"])


def test_annotation_changes_since_the_upgrade_only_add_caution():
    before = {t["name"]: t["annotations"] for t in BASELINE["tools"]}
    after = {t["name"]: t["annotations"] for t in rpc("tools/list", {"id": 1})["result"]["tools"]}
    for name, a in after.items():
        if name in _ADDED:
            continue
        assert a["readOnlyHint"] == before[name]["readOnlyHint"], name
        # A tool may become destructive, never the reverse.
        assert a["destructiveHint"] >= before[name]["destructiveHint"], name


def test_resources_list_is_identical_to_the_pre_upgrade_server():
    assert rpc("resources/list", {"id": 1})["result"]["resources"] == BASELINE["resources"]


# --- 2026-07-28 protocol --------------------------------------------------------

def test_modern_list_results_carry_result_type_and_public_cache_hints():
    result = rpc("tools/list", {"id": 1})["result"]
    assert result["resultType"] == "complete"
    assert result["cacheScope"] == "public" and result["ttlMs"] == 3_600_000


def test_unsupported_protocol_version_is_rejected_with_the_supported_list():
    meta = {**CLIENT_META, "io.modelcontextprotocol/protocolVersion": "1999-01-01"}
    resp = post(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": meta}},
        {"mcp-protocol-version": "1999-01-01", "mcp-method": "tools/list"},
    )
    error = resp.json()["error"]
    assert error["code"] == -32022
    assert MODERN in error["data"]["supported"]


def test_header_body_mismatch_is_rejected():
    resp = post(
        {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {"_meta": CLIENT_META}},
        {"mcp-protocol-version": MODERN, "mcp-method": "tools/list"},
    )
    assert resp.status_code == 400 and resp.json()["error"]["code"] == -32020


def test_legacy_ping_still_answers():
    assert rpc("ping", {"id": 1}, era="legacy") == {"jsonrpc": "2.0", "id": 1, "result": {}}


# --- auth ------------------------------------------------------------------------

def test_discovery_needs_no_credential():
    for method in ("tools/list", "resources/list", "server/discover"):
        assert "result" in rpc(method, {"id": 1}), method


def test_tool_call_without_credential_is_a_401_challenge_with_a_well_formed_header():
    resp = _modern_call("list_folders")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == (
        'Bearer realm="Scanova MCP", resource_metadata="https://mcp.scanova.io/.well-known/oauth-protected-resource/mcp"'
    )


@pytest.mark.parametrize(
    "headers",
    [
        {"authorization": "raw-api-key"},
        {"authorization": "Bearer oauth-token"},
        {"x-api-key": "raw-api-key"},
        {"scanova-api-key": "raw-api-key"},
    ],
)
def test_every_documented_credential_form_reaches_the_scanova_api_as_is(monkeypatch, headers):
    seen = {}
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: seen.update(key=key) or {"results": []})
    assert _modern_call("list_folders", headers).status_code == 200
    assert seen["key"] == next(iter(headers.values()))


def test_stdio_calls_use_the_local_access_token(monkeypatch):
    seen = {}
    monkeypatch.setattr(sdk_server, "MCP_ACCESS_TOKEN", "local-token")
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: seen.update(key=key) or {"results": []})

    class Ctx:
        request = None

    import mcp.types as types

    result = anyio.run(sdk_server.call_tool, Ctx(), types.CallToolRequestParams(name="list_folders", arguments={}))
    assert seen["key"] == "local-token" and result.is_error is False


# --- tool results ---------------------------------------------------------------

def test_a_failed_scanova_call_is_a_tool_error_the_model_can_read(monkeypatch):
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: {"error": "API request failed: timeout"})
    result = _modern_call("list_folders", {"authorization": "k"}).json()["result"]
    assert result["isError"] is True
    assert "API request failed: timeout" in result["content"][0]["text"]


def test_a_crash_is_a_generic_tool_error_that_leaks_nothing(monkeypatch):
    def boom(name, args, key):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(sdk_server, "execute_tool", boom)
    resp = _modern_call("list_folders", {"authorization": "k"})
    result = resp.json()["result"]
    assert result["isError"] is True
    assert "secret" not in resp.text


def test_an_unknown_tool_is_a_protocol_error():
    assert _modern_call("no_such_tool", {"authorization": "k"}).json()["error"]["code"] == -32602


def test_an_expired_key_gets_the_reconnect_message(monkeypatch):
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: {"detail": "Invalid token."})
    monkeypatch.setattr(sdk_server, "normalize", lambda raw, name: {"ok": False, "status_code": 401, "error": raw})
    result = _modern_call("list_folders", {"authorization": "k"}).json()["result"]
    assert "reconnect your Scanova API key" in result["content"][0]["text"]


# --- legacy keep-alive GET ------------------------------------------------------

def test_get_mcp_opens_a_keepalive_stream_that_ends(monkeypatch):
    monkeypatch.setattr(cloud_server, "GET_STREAM_HEARTBEAT_S", 0.01)
    monkeypatch.setattr(cloud_server, "GET_STREAM_MAX_S", 0.05)
    from conftest import get

    resp = get("/mcp")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.text.startswith(": connected")
