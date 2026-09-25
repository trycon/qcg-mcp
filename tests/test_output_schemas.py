"""Every tool's structuredContent conforms to its advertised outputSchema.

MCP requires it, and clients that validate (the TypeScript SDK) fail the call
otherwise. The results go through the same normalize → UI metadata pipeline as
call_tool, for every response shape the Scanova API and local tools produce.
"""

import json

import jsonschema
import pytest

from mcp_http.normalizer import normalize
from mcp_http.registry import list_mcp_tools
from mcp_http.ui_response import attach_ui_metadata

QR = {
    "qrid": "Qa1b2c", "name": "Menu", "category": 1, "qr_type": "dy", "status": "active",
    "info": {"type": "url", "data": {"url": "https://example.com"}},
    "pattern_info": json.dumps({"pattern": "Classic"}), "created_at": "2026-01-01T00:00:00Z", "updated_at": None,
}

RAW_RESPONSES = {
    "object": QR,
    "object_with_nulls": {"id": 7, "name": None, "status": None, "email": None, "webhook_url": None},
    "paginated": {"count": 2, "next": "https://api/x/?page=2", "previous": None, "results": [QR, {"id": 3, "name": "Folder"}]},
    "bare_list": [{"id": 1, "name": "Admin"}, {"id": 2, "name": "Viewer"}],
    "wrapped_list": {"data": [{"id": 1, "name": "x"}], "total": 1},
    "success_flag": {"success": True, "message": "Deleted"},
    "docs_result": {"ok": True, "result": "text", "truncated": True, "note": "narrow it down"},
    "error_string": {"error": "name is required"},
    "error_object": {"error": {"detail": "Not found."}, "status_code": 404},
    "drf_validation": {"name": ["This field is required."]},
    "jsonrpc_result": {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": json.dumps(QR)}]}},
    "jsonrpc_error": {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "boom"}},
    "unparseable": "<html>502 Bad Gateway</html>",
}

TOOLS = [t for t in list_mcp_tools() if t.get("outputSchema")]


def _is_list_tool(tool) -> bool:
    payload = tool["outputSchema"]["properties"]["data"]["anyOf"][0]
    return any(shape.get("type") == ["array", "null"] for shape in payload.get("anyOf", []))


def test_every_tool_has_an_output_schema():
    assert len(TOOLS) == len(list_mcp_tools())


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t["name"])
@pytest.mark.parametrize("shape", RAW_RESPONSES)
def test_structured_content_matches_output_schema(tool, shape):
    if shape == "bare_list" and not _is_list_tool(tool):
        pytest.skip("single-object tools don't return bare lists")
    envelope = attach_ui_metadata(tool["name"], normalize(RAW_RESPONSES[shape], tool["name"]))["envelope"]
    jsonschema.Draft202012Validator(tool["outputSchema"]).validate(envelope)


def test_schemas_are_valid_json_schema():
    for tool in TOOLS:
        jsonschema.Draft202012Validator.check_schema(tool["outputSchema"])


def test_payload_fields_are_still_described():
    by_name = {t["name"]: t["outputSchema"] for t in TOOLS}
    qr = by_name["retrieve_qr_code"]["properties"]["data"]["anyOf"][0]["properties"]
    assert qr["qrid"]["type"] == ["string", "null"]
    assert qr["qr_type"]["enum"] == ["dy", "st", None]
    listed = by_name["list_qr_codes"]["properties"]["data"]["anyOf"][0]["anyOf"]
    assert listed[1]["properties"]["results"]["items"]["properties"]["qrid"]
