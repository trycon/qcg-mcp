"""Tools that are thin wrappers over one Scanova Management API endpoint each.

Each tool is declared once here — its descriptor text, input schema, output
schema, endpoint and handler — and registry.py, dispatcher.py, normalizer.py
and output_schemas.py read MORE_TOOLS instead of repeating it. Its safety
class (read-only / additive / destructive) stays in annotations.py, which is
authoritative for every tool.

Left out on purpose (see the docs' "Available tools" page): permanent deletes
(emptying the trash, deleting form responses, media or domains), exports and
downloads that produce a file or send an email to someone else, anything that
needs a browser or an upload (bulk generation, Slack/HubSpot connect, SSL
certificates), tracking-site API key generation (it returns a secret),
changing a QR code's short URL (it breaks printed codes), and lead lists
beyond the existing tools.
"""

import json
import re
import string
from dataclasses import dataclass
from typing import Callable

from scanova_api import scanova

_ERROR = {"error": {"type": "string", "description": "Human-readable error message"}}


# ── schema helpers ─────────────────────────────────────────────────────────── #

def _input(props: dict | None = None, required: tuple = ()) -> dict:
    schema = {"type": "object", "properties": props or {}}
    if required:
        schema["required"] = list(required)
    return schema


def _list_of(item_props: dict | None = None) -> dict:
    return {"type": "object", "properties": {"data": {"type": "array", "items": {"type": "object", "properties": item_props or {}}}, **_ERROR}}


def _object(props: dict | None = None) -> dict:
    return {"type": "object", "properties": {**(props or {}), **_ERROR}}


_PAGE = {"page": {"type": "integer", "minimum": 1, "description": "Page number (default 1)"}}
_DATE = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}


def _date(desc: str) -> dict:
    return {**_DATE, "description": f"{desc} (YYYY-MM-DD)"}


def _missing(a: dict, *keys: str):
    gone = [k for k in keys if a.get(k) in (None, "", [])]
    return {"error": f"{', '.join(gone)} {'is' if len(gone) == 1 else 'are'} required"} if gone else None


# ── the tools ──────────────────────────────────────────────────────────────── #

@dataclass(frozen=True)
class MoreTool:
    name: str
    title: str
    description: str
    group: str
    endpoint: str
    input_schema: dict
    output_schema: dict
    handler: Callable[[dict, str], object]


_SEGMENT = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _path(template: str, a: dict):
    """The endpoint path with its {placeholders} filled from the arguments — each must be one plain path segment."""
    values = {}
    for _, field, _, _ in string.Formatter().parse(template):
        if field is None:
            continue
        value = str(a.get(field, "")).strip()
        if not _SEGMENT.match(value):
            return None, {"error": f"{field} isn't a valid id"}
        values[field] = value
    return template.format(**values), None


def _get(path: str, params: Callable[[dict], dict] = lambda a: {}, required: tuple = ()):
    def run(a: dict, k: str):
        if err := _missing(a, *required):
            return err
        url, err = _path(path, a)
        return err or scanova("GET", url, k, params=params(a))
    return run


# Forms ─────────────────────────────────────────────────────────────────────── #

_FREQUENCY = {"per_response": 1, "daily": 2, "weekly": 3, "monthly": 4}
_NOTIFICATION_FIELDS = {
    "name": {"type": "string", "maxLength": 100, "description": "A name for the alert"},
    "to": {"type": "string", "maxLength": 100, "description": "Email address to notify"},
    "cc": {"type": "string", "maxLength": 100, "description": "CC email address"},
    "bcc": {"type": "string", "maxLength": 100, "description": "BCC email address"},
    "frequency": {"type": "string", "enum": list(_FREQUENCY), "description": "How often to send: every response, or a daily/weekly/monthly digest"},
    "form_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 50, "description": "Forms (form_id) whose responses trigger the alert"},
    "is_active": {"type": "boolean", "description": "Whether the alert is on"},
}


def _notification_body(a: dict) -> dict:
    body = {k: a[k] for k in ("name", "to", "cc", "bcc", "form_ids", "is_active") if k in a}
    if "frequency" in a:
        body["frequency"] = _FREQUENCY.get(a["frequency"], a["frequency"])
    return body


def _create_form_notification(a: dict, k: str):
    return _missing(a, "name", "to", "form_ids") or scanova("POST", "forms/notification/", k, body=_notification_body(a))


def _update_form_notification(a: dict, k: str):
    if err := _missing(a, "notification_id"):
        return err
    path, err = _path("forms/notification/{notification_id}/", a)
    if err:
        return err
    body = _notification_body(a)
    if "form_ids" not in body:
        # The API replaces the alert's forms with whatever form_ids it's sent —
        # an update without them would unlink every form. Keep the current ones.
        current = scanova("GET", path, k)
        if isinstance(current, dict) and "error" in current:
            return current
        body["form_ids"] = [f["form_id"] for f in (current or {}).get("form_list") or [] if f.get("form_id")]
    return scanova("PATCH", path, k, body=body)


# QR codes ──────────────────────────────────────────────────────────────────── #

_QRID = {"type": "string", "description": "The QR code's qrid, e.g. Q1a2b3c4d"}


def _restore_qr_codes(a: dict, k: str):
    if err := _missing(a, "qrids"):
        return err
    qrids = [q for q in a["qrids"] if isinstance(q, str) and q.strip()]
    if not qrids or any(q.strip().lower() == "all" for q in qrids):
        return {"error": "List the qrids to restore; restoring the whole trash at once isn't supported here."}
    return scanova("POST", "qr/trash/restore/", k, body={"ids": qrids})


def _update_qr_tags(a: dict, k: str):
    if err := _missing(a, "qrid"):
        return err
    tags = [t.strip() for t in a.get("tags") or [] if isinstance(t, str) and t.strip()]
    if any("," in t for t in tags):
        return {"error": "A tag can't contain a comma."}
    path, err = _path("qr/{qrid}/tags/", a)
    return err or scanova("PATCH", path, k, body={"tags": ", ".join(tags)})


_RECALL_FIELDS = {
    "gtin": {"type": "string", "pattern": r"^\d{8,14}$", "description": "The product's GTIN (8–14 digits)"},
    "batch_lot_value": {"type": "string", "maxLength": 20, "description": "The batch or lot being recalled"},
    "message": {"type": "string", "description": "What people who scan an affected product see"},
    "is_active": {"type": "boolean", "description": "Whether the recall notice is shown (default true on create)"},
}


def _create_gs1_recall(a: dict, k: str):
    body = {f: a[f] for f in _RECALL_FIELDS if f in a}
    return _missing(a, "gtin", "batch_lot_value", "message") or scanova("POST", "qr/gs1-recalls/", k, body=body)


def _update_gs1_recall(a: dict, k: str):
    body = {f: a[f] for f in _RECALL_FIELDS if f in a}
    if err := _missing(a, "recall_id"):
        return err
    if not body:
        return {"error": "Nothing to change: pass message, is_active, gtin or batch_lot_value."}
    path, err = _path("qr/gs1-recalls/{recall_id}/", a)
    return err or scanova("PATCH", path, k, body=body)


# Analytics ─────────────────────────────────────────────────────────────────── #

_OVERVIEW = ("all_time", "current_month", "last_months", "scan_dates")
_REPORT_FORMATS = ["csv", "xlsx", "xls", "pdf"]


def _create_analytics_report(a: dict, k: str):
    if err := _missing(a, "scope", "start_date", "end_date", "report_type"):
        return err
    ids = [str(i) for i in a.get("ids") or []]
    if not ids and not a.get("all"):
        return {"error": "Pass the ids to report on, or all: true for every QR code in the scope."}
    body = {
        "filter_type": a["scope"],
        "filter_data": _json_list(["all"] if a.get("all") else ids),
        "start_date": a["start_date"],
        "end_date": a["end_date"],
        "report_type": a["report_type"],
        "exclude_bot_scan": bool(a.get("exclude_bot_scan", False)),
    }
    if a["report_type"] in ("analytics", "both"):
        body["analytics_format"] = a.get("analytics_format", "pdf")
    if a["report_type"] in ("scan_data", "both"):
        body["scan_format"] = a.get("scan_format", "csv")
    if a.get("save_as"):
        body.update(is_saved=True, saved_name=a["save_as"])
    return scanova("POST", "analytics/report/", k, body=body)


def _json_list(items: list) -> str:
    return json.dumps(items)


# Team ──────────────────────────────────────────────────────────────────────── #

def _resend_invitation(a: dict, k: str):
    if err := _missing(a, "user_id"):
        return err
    path, err = _path("multi-users/{user_id}/resend-invitation/", a)
    return err or scanova("POST", path, k)


MORE_TOOLS: list[MoreTool] = [
    # ── Forms ──
    MoreTool(
        "list_form_responses", "List form responses", (
            "List the responses a form has collected, newest first: each with its answers, when it came in "
            "and which QR code it came from. Filter by date range, QR code or a search term; paged."
        ), "Forms", "forms/{form_id}/responses/",
        _input({
            "form_id": {"type": "string", "description": "The form's form_id"},
            "created_from": _date("Only responses on or after this date"),
            "created_till": _date("Only responses on or before this date"),
            "qr_code_id": {"type": "string", "description": "Only responses that came through this QR code"},
            "search": {"type": "string", "description": "Search the answers and QR code name"},
            "ordering": {"type": "string", "enum": ["-created", "created"], "description": "Newest first (default) or oldest first"},
            "page_size": {"type": "integer", "minimum": 1, "maximum": 200, "description": "Responses per page (default 20)"},
            **_PAGE,
        }, ("form_id",)),
        _list_of({"id": {"type": "string"}, "created": {"type": "string"}, "qr_code_id": {"type": "string"}, "qr_code_name": {"type": "string"}, "data": {}}),
        _get("forms/{form_id}/responses/", lambda a: {p: a.get(p) for p in ("created_from", "created_till", "qr_code_id", "search", "ordering", "page", "page_size")}, ("form_id",)),
    ),
    MoreTool(
        "get_form_analytics", "Get form analytics", (
            "A form's performance: total responses and skips (with the change against the previous period), "
            "responses and skips by date, and responses by source QR code."
        ), "Forms", "forms/{form_id}/analytics/",
        _input({"form_id": {"type": "string", "description": "The form's form_id"}, "from": _date("Start of the period"), "to": _date("End of the period")}, ("form_id",)),
        _object({"entries_count": {"type": "object"}, "responses": {}, "skips": {}, "responses_by_source": {}}),
        _get("forms/{form_id}/analytics/", lambda a: {"from": a.get("from"), "to": a.get("to")}, ("form_id",)),
    ),
    MoreTool(
        "get_form_question_analytics", "Get per-question form analytics", (
            "How each question of a form was answered, in the form's order: how many responses answered it "
            "(and the rate), and for choice, rating and scale questions how often each answer was given. "
            "Filter by date range or source QR code."
        ), "Forms", "forms/{form_id}/analytics/questions/",
        _input({
            "form_id": {"type": "string", "description": "The form's form_id"},
            "from": _date("Start of the period"),
            "to": _date("End of the period"),
            "qr_code_id": {"type": "string", "description": "Only responses that came through this QR code"},
        }, ("form_id",)),
        _list_of({
            "question": {"type": "string"}, "type": {"type": "string"},
            "answered": {"type": "integer"}, "response_rate": {"type": "number"},
            "distribution": {"type": "array", "items": {"type": "object", "properties": {"label": {"type": "string"}, "count": {"type": "integer"}}}},
        }),
        _get("forms/{form_id}/analytics/questions/", lambda a: {"from": a.get("from"), "to": a.get("to"), "qr_code_id": a.get("qr_code_id")}, ("form_id",)),
    ),
    MoreTool(
        "list_form_templates", "List form templates",
        "List ready-made form templates (name, description and their blocks), to start a new form from with create_form.",
        "Forms", "forms/template/", _input(),
        _list_of({"id": {"type": "integer"}, "name": {"type": "string"}, "slug": {"type": "string"}, "description": {"type": "string"}, "blocks_json": {}}),
        _get("forms/template/"),
    ),
    MoreTool(
        "list_form_notifications", "List form alerts",
        "List the email alerts set up for new form responses: who they go to, how often, which forms, and whether each is on.",
        "Forms", "forms/notification/", _input(),
        _list_of({"id": {"type": "integer"}, "name": {"type": "string"}, "to": {"type": "string"}, "frequency_display": {"type": "string"}, "form_list": {"type": "array"}, "is_active": {"type": "boolean"}}),
        _get("forms/notification/"),
    ),
    MoreTool(
        "create_form_notification", "Create a form alert", (
            "Email someone when forms get new responses — for every response, or as a daily, weekly or monthly digest. "
            "The address receives the respondents' answers, so only use one the account owner has asked for."
        ), "Forms", "forms/notification/",
        _input({**_NOTIFICATION_FIELDS}, ("name", "to", "form_ids")),
        _object({"id": {"type": "integer"}, "name": {"type": "string"}, "to": {"type": "string"}, "frequency_display": {"type": "string"}, "form_list": {"type": "array"}, "is_active": {"type": "boolean"}}),
        _create_form_notification,
    ),
    MoreTool(
        "update_form_notification", "Update a form alert", (
            "Change a form alert: its recipient, frequency or forms, or switch it on or off. "
            "Only the fields you pass change; its forms are kept unless you pass form_ids."
        ), "Forms", "forms/notification/{notification_id}/",
        _input({"notification_id": {"type": "integer", "description": "The alert's id (from list_form_notifications)"}, **_NOTIFICATION_FIELDS}, ("notification_id",)),
        _object({"id": {"type": "integer"}, "name": {"type": "string"}, "to": {"type": "string"}, "frequency_display": {"type": "string"}, "form_list": {"type": "array"}, "is_active": {"type": "boolean"}}),
        _update_form_notification,
    ),
    # ── QR codes ──
    MoreTool(
        "list_trashed_qr_codes", "List deleted QR codes",
        "List QR codes in the trash (deleted but restorable), with when each was deleted and its scan count. Search by name; paged.",
        "QR codes", "qr/trash/",
        _input({"search": {"type": "string", "description": "Search by name"}, "ordering": {"type": "string", "enum": ["-created", "created", "name", "-name"]}, **_PAGE}),
        _list_of({"qrid": {"type": "string"}, "name": {"type": "string"}, "deleted": {"type": "string"}, "scan_count": {"type": "integer"}}),
        _get("qr/trash/", lambda a: {"search": a.get("search"), "ordering": a.get("ordering"), "page": a.get("page")}),
    ),
    MoreTool(
        "restore_qr_codes", "Restore deleted QR codes",
        "Restore QR codes from the trash so they work again. Counts against the plan's QR code limits; restoring more than the plan allows fails.",
        "QR codes", "qr/trash/restore/",
        _input({"qrids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 100, "description": "qrids to restore (from list_trashed_qr_codes)"}}, ("qrids",)),
        _object({"success": {"type": "boolean"}}),
        _restore_qr_codes,
    ),
    MoreTool(
        "get_qr_health", "Check QR code health", (
            "The account's QR code health check: problems that stop codes working as intended — e.g. inactive or "
            "expired codes, broken destinations, forms or custom domains that need attention."
        ), "QR codes", "qr/health/", _input(), _object(), _get("qr/health/"),
    ),
    MoreTool(
        "update_qr_tags", "Set a QR code's tags",
        "Replace a QR code's tags with the ones given (an empty list removes them all). Tags that don't exist yet are created.",
        "QR codes", "qr/{qrid}/tags/",
        _input({"qrid": _QRID, "tags": {"type": "array", "items": {"type": "string", "maxLength": 50}, "maxItems": 20, "description": "The complete set of tags"}}, ("qrid", "tags")),
        _object({"tags_list": {"type": "array", "items": {"type": "string"}}}),
        _update_qr_tags,
    ),
    MoreTool(
        "list_gs1_recalls", "List GS1 recall notices",
        "List the account's GS1 batch/lot recall notices: which GTIN and batch, the message shown to people who scan an affected product, and whether each is active.",
        "QR codes", "qr/gs1-recalls/", _input({**_PAGE}),
        _list_of({"id": {"type": "integer"}, "gtin": {"type": "string"}, "batch_lot_value": {"type": "string"}, "message": {"type": "string"}, "is_active": {"type": "boolean"}}),
        _get("qr/gs1-recalls/", lambda a: {"page": a.get("page")}),
    ),
    MoreTool(
        "create_gs1_recall", "Create a GS1 recall notice",
        "Recall a product batch: everyone who scans a GS1 QR code for this GTIN and batch/lot sees the message instead.",
        "QR codes", "qr/gs1-recalls/", _input({**_RECALL_FIELDS}, ("gtin", "batch_lot_value", "message")),
        _object({"id": {"type": "integer"}, "gtin": {"type": "string"}, "batch_lot_value": {"type": "string"}, "message": {"type": "string"}, "is_active": {"type": "boolean"}}),
        _create_gs1_recall,
    ),
    MoreTool(
        "update_gs1_recall", "Update a GS1 recall notice",
        "Change a recall notice's message, or set is_active false once the recall is over (its history is kept).",
        "QR codes", "qr/gs1-recalls/{recall_id}/",
        _input({"recall_id": {"type": "integer", "description": "The notice's id (from list_gs1_recalls)"}, **_RECALL_FIELDS}, ("recall_id",)),
        _object({"id": {"type": "integer"}, "gtin": {"type": "string"}, "batch_lot_value": {"type": "string"}, "message": {"type": "string"}, "is_active": {"type": "boolean"}}),
        _update_gs1_recall,
    ),
    # ── Analytics ──
    MoreTool(
        "get_analytics_overview", "Get the scan overview",
        "The account's scan overview: all-time totals, this month, the last months, and scans by date.",
        "Analytics", "analytics/overview/",
        _input({"sections": {"type": "array", "items": {"type": "string", "enum": list(_OVERVIEW)}, "description": "Which sections (default: all)"}}),
        _object({"all_time": {}, "current_month": {}, "last_months": {}, "scan_dates": {}}),
        _get("analytics/overview/", lambda a: {"type": ",".join(a.get("sections") or _OVERVIEW)}),
    ),
    MoreTool(
        "list_analytics_reports", "List analytics reports",
        "List the scan-analytics reports that have been generated: their scope, dates, status, and a download link once complete.",
        "Analytics", "analytics/report/", _input({**_PAGE}),
        _list_of({"id": {"type": "integer"}, "status": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "report_file": {"type": "string"}, "saved_name": {"type": "string"}}),
        _get("analytics/report/", lambda a: {"page": a.get("page")}),
    ),
    MoreTool(
        "create_analytics_report", "Generate an analytics report", (
            "Generate a scan-analytics report for some QR codes, tags or folders over a date range. It's built in the "
            "background and emailed to the person who asked; list_analytics_reports shows its status and link."
        ), "Analytics", "analytics/report/",
        _input({
            "scope": {"type": "string", "enum": ["qrcode", "tag", "folder"], "description": "What `ids` are: QR codes (qrids), tags or folders"},
            "ids": {"type": "array", "items": {"type": ["string", "integer"]}, "maxItems": 500, "description": "The QR codes, tags or folders to report on"},
            "all": {"type": "boolean", "description": "Every QR code, instead of `ids`"},
            "start_date": _date("Start of the period"),
            "end_date": _date("End of the period"),
            "report_type": {"type": "string", "enum": ["analytics", "scan_data", "both"], "description": "Summary analytics, raw scan data, or both"},
            "analytics_format": {"type": "string", "enum": _REPORT_FORMATS, "description": "File format for the analytics part (default pdf)"},
            "scan_format": {"type": "string", "enum": _REPORT_FORMATS, "description": "File format for the scan data (default csv)"},
            "exclude_bot_scan": {"type": "boolean", "description": "Leave out scans from bots"},
            "save_as": {"type": "string", "maxLength": 100, "description": "Save it under this name to run again later"},
        }, ("scope", "start_date", "end_date", "report_type")),
        _object({"message": {"type": "string"}}),
        _create_analytics_report,
    ),
    # ── Plan & billing ──
    MoreTool(
        "list_available_plans", "List available plans",
        "List the plans the account can move to, with their features and quotas.",
        "Account & billing", "plans/available/", _input(), _list_of(), _get("plans/available/"),
    ),
    MoreTool(
        "get_downgrade_impact", "Check a downgrade's impact",
        "Before moving to a smaller plan: which of the account's QR codes, users, domains and other resources exceed that plan and would block or be affected by the change.",
        "Account & billing", "plans/downgrade-impact/",
        _input({"target_plan": {"type": "string", "description": "The plan's slug (from list_available_plans)"}}, ("target_plan",)),
        _object(), _get("plans/downgrade-impact/", lambda a: {"target_plan": a.get("target_plan")}, ("target_plan",)),
    ),
    MoreTool(
        "list_payments", "List payments",
        "The account's payment history: amount, date and status of each payment.",
        "Account & billing", "payment/",
        _input({"ordering": {"type": "string", "enum": ["-sale_date", "sale_date", "-amount", "amount"]}, **_PAGE}),
        _list_of(), _get("payment/", lambda a: {"ordering": a.get("ordering"), "page": a.get("page")}),
    ),
    MoreTool(
        "list_orders", "List orders",
        "The account's orders (plan purchases, renewals and top-ups) and their status.",
        "Account & billing", "payment/orders/", _input({**_PAGE}), _list_of(),
        _get("payment/orders/", lambda a: {"page": a.get("page")}),
    ),
    MoreTool(
        "list_quota_topups", "List quota top-ups",
        "Extra quota bought on top of the plan (e.g. more QR codes or scans) and when each runs out.",
        "Account & billing", "plans/quota-topups/", _input(), _list_of(), _get("plans/quota-topups/"),
    ),
    # ── Team & activity ──
    MoreTool(
        "resend_user_invitation", "Resend an invitation",
        "Send a team member's invitation email again, for someone who hasn't accepted yet.",
        "Team", "multi-users/{user_id}/resend-invitation/",
        _input({"user_id": {"type": "integer", "description": "The member's id (from list_users)"}}, ("user_id",)),
        _object({"message": {"type": "string"}}), _resend_invitation,
    ),
    MoreTool(
        "get_activity_feed", "Get the activity feed",
        "What happened in the account: who created, changed or deleted what, and when. Filter by event type, team member or date; paged.",
        "Team", "user-logs/activity-feed/",
        _input({
            "event_types": {"type": "array", "items": {"type": "string"}, "description": "Only these event types"},
            "actor_user": {"type": "integer", "description": "Only this team member's actions (user id)"},
            "occurred_from": _date("From"),
            "occurred_till": _date("Until"),
            "search": {"type": "string", "description": "Search by what was changed"},
            **_PAGE,
        }),
        _list_of(),
        _get("user-logs/activity-feed/", lambda a: {
            "event_type": ",".join(a.get("event_types") or []) or None,
            "actor_user": a.get("actor_user"), "occurred_from": a.get("occurred_from"), "occurred_till": a.get("occurred_till"),
            "search": a.get("search"), "page": a.get("page"),
        }),
    ),
    MoreTool(
        "get_activity_summary", "Get the activity summary",
        "Counts of the account's activity over a period, for a quick picture of who did what.",
        "Team", "user-logs/activity-summary/", _input({"from": _date("From"), "to": _date("To")}), _object(),
        _get("user-logs/activity-summary/", lambda a: {"from": a.get("from"), "to": a.get("to")}),
    ),
    # ── Workspace resources ──
    MoreTool(
        "get_custom_domain", "Get a custom domain",
        "One custom domain's details: its DNS (TXT/CNAME) verification, SSL status and whether it's the default.",
        "Custom domains", "custom-domain/{domain_id}/",
        _input({"domain_id": {"type": "integer", "description": "The domain's id (from list_custom_domains)"}}, ("domain_id",)),
        _object({"id": {"type": "integer"}, "domain": {"type": "string"}, "is_default": {"type": "boolean"}}),
        _get("custom-domain/{domain_id}/", required=("domain_id",)),
    ),
    MoreTool(
        "list_bulk_operations", "List bulk operations",
        "List the account's bulk operations (bulk QR code generation and updates): what each did, its status and results.",
        "Bulk operations", "bulk-operation/", _input({**_PAGE}), _list_of(),
        _get("bulk-operation/", lambda a: {"page": a.get("page")}),
    ),
    MoreTool(
        "get_bulk_operation_stats", "Get bulk operation stats",
        "Totals across the account's bulk operations.",
        "Bulk operations", "bulk-operation/stats/", _input(), _object(), _get("bulk-operation/stats/"),
    ),
    MoreTool(
        "list_media", "List media files",
        "List files in the account's media library (images, PDFs, videos…), e.g. to pick a logo or a document for a QR code. Filter by type or whether it's in use.",
        "Media", "media/",
        _input({
            "file_type": {"type": "string", "description": "e.g. image, pdf, video, audio"},
            "in_use": {"type": "boolean", "description": "Only files used (or not used) by a QR code"},
            "search": {"type": "string", "description": "Search by file name"},
            **_PAGE,
        }),
        _list_of(), _get("media/", lambda a: {"file_type": a.get("file_type"), "in_use": a.get("in_use"), "search": a.get("search"), "page": a.get("page")}),
    ),
    MoreTool(
        "get_integrations_overview", "Get integrations overview",
        "Which integrations the account has connected (webhooks, Zapier, Slack, HubSpot, Google Analytics…) and their state.",
        "Integrations", "webhook/overview/", _input(), _object(), _get("webhook/overview/"),
    ),
    MoreTool(
        "list_webhooks", "List webhooks",
        "List the account's webhooks: where each sends events, for which forms or QR codes, and whether it's on.",
        "Integrations", "webhook/", _input({"search": {"type": "string"}, **_PAGE}), _list_of(),
        _get("webhook/", lambda a: {"search": a.get("search"), "page": a.get("page")}),
    ),
    MoreTool(
        "list_tracking_sites", "List conversion tracking sites",
        "List the websites set up for conversion tracking (what visitors do after scanning), with their domains.",
        "Conversion tracking", "web-tracking/sites/", _input({**_PAGE}), _list_of(),
        _get("web-tracking/sites/", lambda a: {"page": a.get("page")}),
    ),
    MoreTool(
        "list_tracking_funnels", "List conversion funnels",
        "List a tracking site's conversion funnels: the steps from scan to conversion.",
        "Conversion tracking", "web-tracking/sites/{site_id}/funnels/",
        _input({"site_id": {"type": "integer", "description": "The site's id (from list_tracking_sites)"}}, ("site_id",)),
        _list_of(), _get("web-tracking/sites/{site_id}/funnels/", required=("site_id",)),
    ),
    MoreTool(
        "list_page_templates", "List landing page templates",
        "List landing page templates for QR codes that open a page — Scanova's own, or only the account's saved ones. Filter by category or search.",
        "Landing pages", "page-template/",
        _input({
            "mine": {"type": "boolean", "description": "Only the account's own saved templates"},
            "category": {"type": "string", "description": "Template category"},
            "search": {"type": "string"},
            **_PAGE,
        }),
        _list_of(), _get("page-template/", lambda a: {"mine": "true" if a.get("mine") else None, "category": a.get("category"), "search": a.get("search"), "page": a.get("page")}),
    ),
]

MORE_TOOLS_BY_NAME: dict[str, MoreTool] = {t.name: t for t in MORE_TOOLS}
