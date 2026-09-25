"""Covers the create_qr_code / open_qr_code_creation_form split: a
successful create_qr_code call gets no UI (the text confirmation already
says everything), a failed one echoes back attempted_params so the form can
pre-fill itself, and open_qr_code_creation_form always shows the form for
when the user hasn't given enough information to create yet."""

import mcp_http.dispatcher as dispatcher
import mcp_http.sdk_server as sdk_server
from conftest import rpc
import mcp_http.registry as registry
from mcp_http.ui_resources import get_resource_for_tool


def test_create_qr_code_and_open_form_share_one_resource():
    a = get_resource_for_tool("create_qr_code")
    b = get_resource_for_tool("open_qr_code_creation_form")
    assert a is not None and b is not None
    assert a.uri == b.uri == "ui://scanova/create-qr-code.html"


def test_open_qr_code_creation_form_registered_in_tools_list():
    names = {t["name"] for t in registry.list_mcp_tools()}
    assert "open_qr_code_creation_form" in names


def test_handler_echoes_attempted_params_on_failure(monkeypatch):
    monkeypatch.setattr(dispatcher, "create_qr_code", lambda params, api_key: {"error": "category is required"})
    params = {"name": "Test", "category": None}
    result = dispatcher._create_qr_code_handler({"params": params}, api_key="k")
    assert result["attempted_params"] == params
    assert result["error"] == "category is required"


def test_handler_does_not_echo_attempted_params_on_success(monkeypatch):
    monkeypatch.setattr(dispatcher, "create_qr_code", lambda params, api_key: {"qrid": "Qabc", "name": "Test"})
    result = dispatcher._create_qr_code_handler({"params": {"name": "Test"}}, api_key="k")
    assert "attempted_params" not in result
    assert result["qrid"] == "Qabc"


def test_handler_blocks_page_builder_category_without_calling_api(monkeypatch):
    """Categories whose info shape is page-builder-style/undocumented/
    conflicting are blocked here with app.scanova.io guidance instead of
    letting a freehand-constructed payload fail with a confusing API error."""
    def _unexpected_call(params, api_key):
        raise AssertionError("create_qr_code should not be called for a blocked category")
    monkeypatch.setattr(dispatcher, "create_qr_code", _unexpected_call)
    params = {"name": "Test", "category": "20", "qr_type": "dy", "info": {}}
    result = dispatcher._create_qr_code_handler({"params": params}, api_key="k")
    assert "app.scanova.io" in result["error"]
    assert result["attempted_params"] == params


def test_handler_blocks_restaurant_category(monkeypatch):
    def _unexpected_call(params, api_key):
        raise AssertionError("create_qr_code should not be called for a blocked category")
    monkeypatch.setattr(dispatcher, "create_qr_code", _unexpected_call)
    for category in ("25", "44"):
        result = dispatcher._create_qr_code_handler(
            {"params": {"name": "Test", "category": category}}, api_key="k"
        )
        assert "app.scanova.io" in result["error"]


def test_handler_blocks_business_card_category(monkeypatch):
    """Business Card (24) deliberately blocked (2026-08-24) at the user's
    request, after live testing showed its info shape doesn't match either
    a flat object or a simple array-wrapped one."""
    def _unexpected_call(params, api_key):
        raise AssertionError("create_qr_code should not be called for a blocked category")
    monkeypatch.setattr(dispatcher, "create_qr_code", _unexpected_call)
    result = dispatcher._create_qr_code_handler(
        {"params": {"name": "Test", "category": "24"}}, api_key="k"
    )
    assert "app.scanova.io" in result["error"]


def test_handler_blocks_coupon_category(monkeypatch):
    """Coupon (17) deliberately blocked (2026-08-24) at the user's request —
    its real info shape is unconfirmed (two sources in Scanova's own
    frontend codebase disagree on the field names)."""
    def _unexpected_call(params, api_key):
        raise AssertionError("create_qr_code should not be called for a blocked category")
    monkeypatch.setattr(dispatcher, "create_qr_code", _unexpected_call)
    result = dispatcher._create_qr_code_handler(
        {"params": {"name": "Test", "category": "17"}}, api_key="k"
    )
    assert "app.scanova.io" in result["error"]


def test_handler_allows_unblocked_category(monkeypatch):
    monkeypatch.setattr(dispatcher, "create_qr_code", lambda params, api_key: {"qrid": "Qabc"})
    result = dispatcher._create_qr_code_handler(
        {"params": {"name": "Test", "category": "7"}}, api_key="k"
    )
    assert result["qrid"] == "Qabc"


def test_open_form_handler_returns_prefill():
    result = dispatcher._open_qr_code_creation_form_handler({"name": "Storefront", "category": 1})
    assert result["mode"] == "blank"
    assert result["prefill"]["name"] == "Storefront"
    assert result["prefill"]["category"] == 1
    assert result["prefill"]["qr_type"] is None


def test_tools_call_no_meta_on_successful_create(monkeypatch):
    import mcp_http.ui_response as ui_response
    monkeypatch.setattr(ui_response, "UI_ELEMENTS_ENABLED", True, raising=False)
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: {"qrid": "Qabc", "name": "Test"})
    body = {"id": 1, "params": {"name": "create_qr_code", "arguments": {"params": {"name": "Test"}}}}
    result = rpc("tools/call", body, api_key="k")
    meta = result["result"].get("_meta", {})
    assert "ui" not in meta and "openai/outputTemplate" not in meta


def test_tools_call_has_meta_on_failed_create(monkeypatch):
    import mcp_http.ui_response as ui_response
    monkeypatch.setattr(ui_response, "UI_ELEMENTS_ENABLED", True, raising=False)
    monkeypatch.setattr(sdk_server, "execute_tool", lambda name, args, key: {"error": "bad request", "attempted_params": {"name": "Test"}})
    body = {"id": 2, "params": {"name": "create_qr_code", "arguments": {"params": {"name": "Test"}}}}
    result = rpc("tools/call", body, api_key="k")
    assert result["result"]["_meta"]["openai/outputTemplate"] == get_resource_for_tool("create_qr_code").versioned_uri
