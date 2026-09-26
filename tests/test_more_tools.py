"""The one-endpoint tools (mcp_http/more_tools.py) and create_form's form builder.

Every tool is checked for the exact request it makes — method, path, query and
body — with the Scanova API faked at requests.request. The guards (no bulk
"restore everything", ids that must be one path segment, alerts that keep
their forms) are checked on their own. create_form's blocks are validated
against qcg-backend's own form schema (tests/fixtures/form_schema).
"""

import json
from pathlib import Path

import jsonschema
import pytest
from referencing import Registry, Resource

import scanova_api
from forms import build_form_blocks
from mcp_http.annotations import annotations_for
from mcp_http.dispatcher import execute_tool
from mcp_http.more_tools import MORE_TOOLS

KEY = "key123"


class _Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = {"ok": True} if body is None else body
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


@pytest.fixture
def api(monkeypatch):
    calls = []
    answers = []

    def fake(method, url, headers=None, params=None, json=None, timeout=None):
        calls.append({"method": method, "path": url.split("/", 3)[-1], "params": params or {}, "body": json, "headers": headers})
        return answers.pop(0) if answers else _Resp()

    monkeypatch.setattr(scanova_api.requests, "request", fake)
    fake.calls, fake.answers = calls, answers
    return fake


# (tool, arguments, method, path, query, body) — every tool in more_tools.py.
CASES = [
    ("list_form_responses", {"form_id": "F1", "created_from": "2026-09-01", "qr_code_id": "Qa", "page": 2}, "GET", "forms/F1/responses/", {"created_from": "2026-09-01", "qr_code_id": "Qa", "page": 2}, None),
    ("get_form_analytics", {"form_id": "F1", "from": "2026-09-01", "to": "2026-09-26"}, "GET", "forms/F1/analytics/", {"from": "2026-09-01", "to": "2026-09-26"}, None),
    ("list_form_templates", {}, "GET", "forms/template/", {}, None),
    ("list_form_notifications", {}, "GET", "forms/notification/", {}, None),
    ("create_form_notification", {"name": "Sales", "to": "a@b.co", "frequency": "daily", "form_ids": ["F1"]}, "POST", "forms/notification/", {}, {"name": "Sales", "to": "a@b.co", "frequency": 2, "form_ids": ["F1"]}),
    ("update_form_notification", {"notification_id": 7, "is_active": False, "form_ids": ["F2"]}, "PATCH", "forms/notification/7/", {}, {"is_active": False, "form_ids": ["F2"]}),
    ("list_trashed_qr_codes", {"search": "menu"}, "GET", "qr/trash/", {"search": "menu"}, None),
    ("restore_qr_codes", {"qrids": ["Qa", "Qb"]}, "POST", "qr/trash/restore/", {}, {"ids": ["Qa", "Qb"]}),
    ("get_qr_health", {}, "GET", "qr/health/", {}, None),
    ("update_qr_tags", {"qrid": "Qa", "tags": ["Summer", " menu "]}, "PATCH", "qr/Qa/tags/", {}, {"tags": "Summer, menu"}),
    ("list_gs1_recalls", {}, "GET", "qr/gs1-recalls/", {}, None),
    ("create_gs1_recall", {"gtin": "09506000134352", "batch_lot_value": "L42", "message": "Do not use"}, "POST", "qr/gs1-recalls/", {}, {"gtin": "09506000134352", "batch_lot_value": "L42", "message": "Do not use"}),
    ("update_gs1_recall", {"recall_id": 3, "is_active": False}, "PATCH", "qr/gs1-recalls/3/", {}, {"is_active": False}),
    ("get_analytics_overview", {"sections": ["all_time"]}, "GET", "analytics/overview/", {"type": "all_time"}, None),
    ("list_analytics_reports", {}, "GET", "analytics/report/", {}, None),
    ("create_analytics_report", {"scope": "qrcode", "ids": ["Qa"], "start_date": "2026-09-01", "end_date": "2026-09-26", "report_type": "both"}, "POST", "analytics/report/", {},
     {"filter_type": "qrcode", "filter_data": '["Qa"]', "start_date": "2026-09-01", "end_date": "2026-09-26", "report_type": "both", "exclude_bot_scan": False, "analytics_format": "pdf", "scan_format": "csv"}),
    ("list_available_plans", {}, "GET", "plans/available/", {}, None),
    ("get_downgrade_impact", {"target_plan": "lite"}, "GET", "plans/downgrade-impact/", {"target_plan": "lite"}, None),
    ("list_payments", {"ordering": "-sale_date"}, "GET", "payment/", {"ordering": "-sale_date"}, None),
    ("list_orders", {}, "GET", "payment/orders/", {}, None),
    ("list_quota_topups", {}, "GET", "plans/quota-topups/", {}, None),
    ("resend_user_invitation", {"user_id": 12}, "POST", "multi-users/12/resend-invitation/", {}, None),
    ("get_activity_feed", {"event_types": ["qr_created", "qr_deleted"], "actor_user": 5}, "GET", "user-logs/activity-feed/", {"event_type": "qr_created,qr_deleted", "actor_user": 5}, None),
    ("get_activity_summary", {"from": "2026-09-01"}, "GET", "user-logs/activity-summary/", {"from": "2026-09-01"}, None),
    ("get_custom_domain", {"domain_id": 4}, "GET", "custom-domain/4/", {}, None),
    ("list_bulk_operations", {}, "GET", "bulk-operation/", {}, None),
    ("get_bulk_operation_stats", {}, "GET", "bulk-operation/stats/", {}, None),
    ("list_media", {"file_type": "image", "in_use": True}, "GET", "media/", {"file_type": "image", "in_use": True}, None),
    ("get_integrations_overview", {}, "GET", "webhook/overview/", {}, None),
    ("list_webhooks", {"search": "crm"}, "GET", "webhook/", {"search": "crm"}, None),
    ("list_tracking_sites", {}, "GET", "web-tracking/sites/", {}, None),
    ("list_tracking_funnels", {"site_id": 9}, "GET", "web-tracking/sites/9/funnels/", {}, None),
    ("list_page_templates", {"mine": True, "search": "menu"}, "GET", "page-template/", {"mine": "true", "search": "menu"}, None),
]


def test_every_new_tool_has_a_case():
    assert {c[0] for c in CASES} == {t.name for t in MORE_TOOLS}


@pytest.mark.parametrize("tool,args,method,path,query,body", CASES, ids=[c[0] for c in CASES])
def test_request(api, tool, args, method, path, query, body):
    execute_tool(tool, args, KEY)
    call = api.calls[-1]
    assert (call["method"], call["path"]) == (method, path)
    assert {k: v for k, v in call["params"].items()} == query
    assert call["body"] == body
    assert call["headers"]["Authorization"] == KEY  # forwarded exactly as given


@pytest.mark.parametrize("tool", [t.name for t in MORE_TOOLS])
def test_no_api_key_calls_nothing(api, tool):
    args = next(c[1] for c in CASES if c[0] == tool)
    assert "error" in execute_tool(tool, args, None)
    assert api.calls == []


def test_writes_are_never_read_only():
    writes = {"create_form_notification", "update_form_notification", "restore_qr_codes", "update_qr_tags",
              "create_gs1_recall", "update_gs1_recall", "create_analytics_report", "resend_user_invitation"}
    for t in MORE_TOOLS:
        assert annotations_for(t.name)["readOnlyHint"] is (t.name not in writes), t.name
    for name in ("update_qr_tags", "update_gs1_recall", "update_form_notification"):
        assert annotations_for(name)["destructiveHint"] is True, name


# ── guards ─────────────────────────────────────────────────────────────────── #

def test_ids_must_be_one_path_segment(api):
    for tool, args in (
        ("list_form_responses", {"form_id": "../qr"}),
        ("update_qr_tags", {"qrid": "Qa/../../x", "tags": []}),
        ("get_custom_domain", {"domain_id": "4?x=1"}),
        ("update_form_notification", {"notification_id": "7/../8", "is_active": True}),
    ):
        assert "isn't a valid id" in execute_tool(tool, args, KEY)["error"], tool
    assert api.calls == []


def test_missing_required_arguments_call_nothing(api):
    assert "form_id is required" in execute_tool("list_form_responses", {}, KEY)["error"]
    assert "required" in execute_tool("create_gs1_recall", {"gtin": "09506000134352"}, KEY)["error"]
    assert "Pass the ids" in execute_tool("create_analytics_report", {"scope": "qrcode", "start_date": "2026-09-01", "end_date": "2026-09-02", "report_type": "analytics"}, KEY)["error"]
    assert api.calls == []


def test_restore_never_restores_the_whole_trash(api):
    assert "error" in execute_tool("restore_qr_codes", {"qrids": ["all"]}, KEY)
    assert "error" in execute_tool("restore_qr_codes", {"qrids": []}, KEY)
    assert api.calls == []


def test_tags_with_commas_are_refused(api):
    assert "comma" in execute_tool("update_qr_tags", {"qrid": "Qa", "tags": ["a,b"]}, KEY)["error"]
    assert api.calls == []


def test_updating_an_alert_without_form_ids_keeps_its_forms(api):
    api.answers.append(_Resp(body={"id": 7, "form_list": [{"form_id": "F1", "form_name": "A"}, {"form_id": "F2", "form_name": "B"}]}))
    execute_tool("update_form_notification", {"notification_id": 7, "frequency": "weekly"}, KEY)
    get, patch = api.calls
    assert (get["method"], get["path"]) == ("GET", "forms/notification/7/")
    assert (patch["method"], patch["path"]) == ("PATCH", "forms/notification/7/")
    assert patch["body"] == {"frequency": 3, "form_ids": ["F1", "F2"]}


def test_updating_an_alert_that_cant_be_read_changes_nothing(api):
    api.answers.append(_Resp(status=404, body={"detail": "Not found."}))
    result = execute_tool("update_form_notification", {"notification_id": 7, "is_active": False}, KEY)
    assert "error" in result
    assert [c["method"] for c in api.calls] == ["GET"]


def test_all_report_scope(api):
    execute_tool("create_analytics_report", {"scope": "folder", "all": True, "start_date": "2026-09-01", "end_date": "2026-09-02", "report_type": "scan_data", "save_as": "Weekly"}, KEY)
    body = api.calls[-1]["body"]
    assert body["filter_data"] == '["all"]'
    assert body["scan_format"] == "csv" and "analytics_format" not in body
    assert (body["is_saved"], body["saved_name"]) == (True, "Weekly")


def test_api_failures_come_back_as_errors(api):
    api.answers.append(_Resp(status=403, body={"detail": "Your plan doesn't include this."}))
    result = execute_tool("get_qr_health", {}, KEY)
    assert result["status_code"] == 403 and "error" in result


# ── create_form ────────────────────────────────────────────────────────────── #

_SCHEMA_DIR = Path(__file__).parent / "fixtures" / "form_schema"


def _form_validator():
    def retrieve(uri):
        return Resource.from_contents(json.loads((_SCHEMA_DIR / uri.removeprefix("file:///")).read_text()))

    root = json.loads((_SCHEMA_DIR / "form.json").read_text())
    registry = Registry(retrieve=retrieve)
    # form.json's refs are relative to its own directory ("components/…").
    root = {**root, "$id": "file:///form.json"}
    return jsonschema.Draft201909Validator(root, registry=registry)


def test_built_forms_match_the_backend_schema():
    blocks, err = build_form_blocks(
        "Book a table",
        [
            {"question": "Name", "required": True},
            {"question": "Email", "type": "email", "required": True},
            {"question": "Party size", "type": "dropdown", "options": ["1-2", "3-4", "5+"]},
            {"question": "Seating", "type": "multipleChoice", "options": ["Inside", "Terrace"]},
            {"question": "Extras", "type": "checkbox", "options": ["High chair", "Birthday"]},
            {"question": "How was your last visit?", "type": "starRating", "description": "Optional"},
            {"question": "Date", "type": "dateFormat"},
        ],
        description="We'll confirm by email",
        submit_label="Book",
        thank_you="Thanks! See you soon.",
    )
    assert err is None
    _form_validator().validate(blocks)


def test_form_builder_refuses_what_the_backend_would():
    assert build_form_blocks("", [{"question": "x"}])[1]
    assert build_form_blocks("T", [])[1]
    assert "needs options" in build_form_blocks("T", [{"question": "Pick", "type": "dropdown"}])[1]
    assert "same option" in build_form_blocks("T", [{"question": "Pick", "type": "checkbox", "options": ["A", "a"]}])[1]
    assert "type must be" in build_form_blocks("T", [{"question": "Sign", "type": "signature"}])[1]


def test_create_form_from_questions_sends_blocks_as_a_json_string(monkeypatch):
    import forms

    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.update(json)
        return _Resp(status=201, body={"form_id": "F9", "name": json["name"]})

    monkeypatch.setattr(forms.requests, "post", fake_post)
    result = execute_tool("create_form", {"name": "Feedback", "title": "Tell us", "questions": [{"question": "Rating", "type": "emoji"}]}, KEY)
    assert result["form_id"] == "F9"
    blocks = json.loads(sent["data"])
    assert blocks[0]["data"]["questions"][0]["answer"] == {"type": "emoji"}
    _form_validator().validate(blocks)
