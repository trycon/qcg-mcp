"""Verifies the domain reorganization: the 6 new tools are registered and
dispatched correctly, and the 4 moved attach/detach tools are unaffected by
their move to the Forms/Lead Lists sections."""

import mcp_http.dispatcher as dispatcher
import mcp_http.sdk_server as sdk_server
from conftest import rpc
import mcp_http.registry as registry

NEW_TOOLS = {
    "get_qr_category_fields",
    "validate_qr_info",
    "create_form",
    "list_tags",
    "get_current_plan",
    "create_custom_role",
}

MOVED_TOOLS = {
    "attach_form_to_qr",
    "detach_form_from_qr",
    "attach_lead_list_to_qr",
    "detach_lead_list_from_qr",
}


def test_registry_and_dispatcher_stay_in_sync():
    registry_names = {t["name"] for t in registry.list_mcp_tools()}
    dispatch_names = set(dispatcher._DISPATCH.keys())
    assert registry_names == dispatch_names


def test_new_tools_present_in_tools_list():
    result = rpc("tools/list", {"id": 1}, api_key="k")
    names = {t["name"] for t in result["result"]["tools"]}
    assert NEW_TOOLS <= names


def test_moved_tools_still_present_and_dispatchable():
    registry_names = {t["name"] for t in registry.list_mcp_tools()}
    assert MOVED_TOOLS <= registry_names
    assert MOVED_TOOLS <= set(dispatcher._DISPATCH.keys())


def test_get_qr_category_fields_dispatches_without_api_key():
    # Static reference data — no api_key required, unlike every other tool.
    result = dispatcher.execute_tool("get_qr_category_fields", {"category": 1}, api_key=None)
    assert result["name"] == "Website URL"


def test_list_tags_dispatch_wires_params(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        dispatcher, "list_tags", lambda **kwargs: captured.update(kwargs) or {"count": 0, "results": []}
    )
    dispatcher.execute_tool("list_tags", {"name": "sale", "page": 2}, api_key="k")
    assert captured == {"name": "sale", "page": 2, "api_key": "k"}


def test_create_custom_role_dispatch_wires_params(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        dispatcher, "create_custom_role", lambda **kwargs: captured.update(kwargs) or {"id": 1}
    )
    dispatcher.execute_tool("create_custom_role", {"name": "Support", "permissions": [1, 2]}, api_key="k")
    assert captured == {"name": "Support", "permissions": [1, 2], "api_key": "k"}
