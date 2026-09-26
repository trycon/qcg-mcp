"""Route MCP tool calls to Scanova API functions."""

import json

import docs_client
from design import DESIGN_OPTIONS, apply_design, build_pattern_info, extract_design_args
from design_checks import check_design, data_uri, render, summary, verify_scans
from domains import list_custom_domains
from mcp_http.more_tools import MORE_TOOLS
from analytics import get_account_stats, get_qr_analytics
from billing import get_current_plan
from folders import (
    create_folder,
    delete_folder,
    list_folders,
    move_qr_codes_to_folder,
    unassign_qr_codes_from_folder,
    update_folder,
)
from forms import build_form_blocks, create_form, delete_form, list_forms, retrieve_form, update_form
from leads import delete_lead_list, list_lead_lists, retrieve_lead_list, update_lead_list
from qrcode import (
    activate_qr_code,
    attach_form_to_qr,
    attach_lead_list_to_qr,
    create_qr_code,
    deactivate_qr_code,
    delete_qr_code,
    detach_form_from_qr,
    detach_lead_list_from_qr,
    download_qr_code,
    get_qr_categories,
    get_qr_category_fields,
    list_qr_codes,
    retrieve_qr_code,
    update_qr_code,
    validate_qr_info,
)
from tags import list_tags
from users import (
    add_user,
    create_custom_role,
    get_user,
    list_user_roles,
    list_users,
    remove_user,
    update_user_role,
)


_DESIGN_KEYS = {
    "pattern", "start_color", "end_color", "gradient_style", "dot_scale",
    "background_color", "eye_shape", "eye_inner_color", "eye_outer_color",
    "frame_id", "frame_primary_color", "frame_secondary_color",
    "frame_text_color", "frame_bg_color", "frame_category",
    "frame_text", "frame_text_placement", "frame_text_font",
    "shape_id", "shape_stroke_color", "shape_bg_color", "shape_pattern_color",
    "shape_stroke_width", "shape_margin", "error_correction", "logo_url", "padding",
}


def _encoded_content(qr: dict) -> str:
    """What the QR image encodes: a dynamic code's short URL (as the backend encodes it), else its URL."""
    duo = qr.get("dynamic_url_object") or {}
    if duo.get("complete_url"):
        url = duo["complete_url"]
        return url if "?" in url else f"{url}?qr=1"
    info = qr.get("info")
    try:
        data = (json.loads(info) if isinstance(info, str) else info or {}).get("data", {})
    except (json.JSONDecodeError, AttributeError):
        data = {}
    return data.get("url") or "https://scnv.io/preview"


def _merged_design(arguments: dict, api_key: str) -> tuple:
    """
    The design after applying the caller's changes over the QR code's current
    one (when a qrid is given), and the content its image encodes.
    Returns (pattern_info dict, content, error dict or None).
    """
    qrid = arguments.get("qrid")
    existing_design_args: dict = {}
    content = arguments.get("content")
    if qrid:
        existing_qr = retrieve_qr_code(qrid, api_key=api_key)
        if not isinstance(existing_qr, dict) or existing_qr.get("error"):
            return None, None, existing_qr if isinstance(existing_qr, dict) else {"error": "QR code not found"}
        pi_str = existing_qr.get("pattern_info")
        if pi_str:
            try:
                existing_design_args = extract_design_args(json.loads(pi_str))
            except (json.JSONDecodeError, TypeError):
                pass
        content = content or _encoded_content(existing_qr)
    user_args = {k: v for k, v in arguments.items() if k in _DESIGN_KEYS and v is not None}
    pattern_info = json.loads(build_pattern_info(**{**existing_design_args, **user_args}))
    return pattern_info, content or "https://scnv.io/preview", None


def _design_report(pattern_info: dict, content: str, render_image: bool, fmt: str = "png") -> dict:
    """Checks, a scan test and (optionally) the rendered image, for a design."""
    checks = check_design(pattern_info)
    image = None
    png = None
    if render_image or fmt == "png":
        try:
            png = render(content, pattern_info, "png", 400)
        except Exception:
            png = None
    scan = verify_scans(content, pattern_info, png) if png else {"scannable": None, "message": "Couldn't render the design for a scan test just now."}
    if render_image:
        if fmt == "svg":
            try:
                image = data_uri(render(content, pattern_info, "svg", 400), "svg")
            except Exception:
                image = None
        elif png:
            image = data_uri(png, "png")
    report = {"checks": checks, "scan": scan, "summary": summary(checks, scan)}
    if image:
        report["image"] = image
    return report


def _preview_qr_design_handler(arguments: dict, api_key: str) -> dict:
    """
    A design, checked and (optionally) rendered — never saved. With a qrid,
    changes apply over that code's current design; for a code that doesn't
    exist yet, pass `content` (what it will encode). An app that renders QR
    designs itself can pass render: false and draw `pattern_info` locally.
    """
    if not arguments.get("qrid") and not arguments.get("content"):
        return {"error": "give a qrid (an existing QR code) or content (what a new one will encode)"}
    if arguments.get("qrid") and not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    pattern_info, content, error = _merged_design(arguments, api_key)
    if error:
        return error
    render_image = arguments.get("render", True) is not False
    report = _design_report(pattern_info, content, render_image, arguments.get("format", "png"))
    return {"preview": True, "saved": False, "content": content, "pattern_info": pattern_info, **report}


def _set_qr_design_handler(arguments: dict, api_key: str) -> dict:
    """
    Build pattern_info from friendly params then PATCH the QR code.
    Fetches the existing design first so only the specified fields are changed —
    all other design settings (eye shape, pattern, colors, frame, etc.) are preserved.
    Refuses a design that fails the scan-safety checks or the scan test unless
    accept_risk is true.
    """
    qrid = arguments.get("qrid")
    if not qrid:
        return {"error": "qrid is required"}
    pattern_info, content, error = _merged_design(arguments, api_key)
    if error:
        return error
    report = _design_report(pattern_info, content, render_image=False)
    if not report["summary"]["safe"] and arguments.get("accept_risk") is not True:
        problems = [c["message"] for c in report["checks"] if c["level"] == "fail"]
        if report["scan"].get("scannable") is False:
            problems.append(report["scan"]["message"])
        return {
            "error": "Not saved: this design may not scan. " + " ".join(problems) + " Change it, or set accept_risk to save anyway.",
            "checks": report["checks"],
            "scan": report["scan"],
        }
    result = apply_design(qrid, json.dumps(pattern_info), api_key)
    if isinstance(result, dict) and not result.get("error"):
        result = {**result, "design_checks": report["summary"], "scan": report["scan"]}
    return result


def _create_form_handler(arguments: dict, api_key: str) -> dict:
    """create_form from title + questions (built into Scanova's form blocks), or from raw `data` blocks."""
    data = arguments.get("data")
    if not data:
        data, err = build_form_blocks(
            arguments.get("title") or arguments.get("name"),
            arguments.get("questions") or [],
            description=arguments.get("description"),
            submit_label=arguments.get("submit_label"),
            thank_you=arguments.get("thank_you"),
        )
        if err:
            return {"error": err}
    return create_form(
        name=arguments.get("name"),
        data=data,
        qr_id=arguments.get("qr_id"),
        theme_id=arguments.get("theme_id"),
        theme_overrides=arguments.get("theme_overrides"),
        api_key=api_key,
    )


def _list_custom_domains_handler(arguments: dict, api_key: str) -> dict:
    return list_custom_domains(api_key=api_key)


# QR category IDs whose `info` shape is a page-builder-style nested/typed
# section array (Custom Page, Document, Wedding, Social Media, Audio,
# Product, Event), an unsupported array-of-files shape (Image), is entirely
# undocumented (Feedback, Real Estate, Link Page, GS1), has conflicting/
# unverified documentation (Restaurant, 25 and 44 — Scanova's own docs
# disagree on whether its info is a flat object or a page-builder array),
# or was explicitly deemed out of scope for this form (Business Card, 24;
# Coupon, 17 — its info shape is unconfirmed, two sources in Scanova's own
# frontend codebase disagree) — see QR_CATEGORY_FIELDS in qrcode.py for the
# per-category detail. Rather than let a freehand-constructed payload fail
# with a confusing API validation error, these are blocked here with
# guidance to create them in the app.
CATEGORIES_REQUIRING_SCANOVA_APP = {9, 13, 14, 15, 16, 17, 18, 19, 20, 24, 25, 26, 27, 28, 31, 44}


def _create_qr_code_handler(arguments: dict, api_key: str) -> dict:
    """
    Wraps create_qr_code so a failed attempt echoes back what was submitted
    (as `attempted_params`) — the UI form is only shown on failure (see
    ui_response.py:CONDITIONAL_UI_RULES), and needs this to pre-fill itself
    instead of the user re-typing everything from scratch.
    """
    params = arguments.get("params") or {}
    try:
        category_id = int(params.get("category"))
    except (TypeError, ValueError):
        category_id = None
    if category_id in CATEGORIES_REQUIRING_SCANOVA_APP:
        return {
            "error": (
                "This QR code category needs to be created via the Scanova application — "
                "visit https://app.scanova.io to create it there."
            ),
            "attempted_params": params,
        }

    result = create_qr_code(params, api_key=api_key)
    if isinstance(result, dict) and not result.get("qrid"):
        return {**result, "attempted_params": params}
    return result


def _open_qr_code_creation_form_handler(arguments: dict) -> dict:
    """No API call — just tells the widget what (if anything) to pre-fill."""
    return {
        "mode": "blank",
        "prefill": {
            "name": arguments.get("name"),
            "category": arguments.get("category"),
            "qr_type": arguments.get("qr_type"),
        },
    }


LIST_QR_CODES_MAX_LIMIT = 20


def _list_qr_params(arguments: dict) -> dict | None:
    qr_params = {}
    if arguments.get("page"):
        qr_params["page"] = arguments["page"]
    if arguments.get("limit"):
        # Scanova API's qrcode/ list endpoint expects "page_size", not "limit" —
        # https://docs.scanova.io/api-reference/management-api/qr/list
        # Enforced here (not just the schema's "maximum") so a client that
        # ignores the input schema can't request more than one page's worth
        # in a single call — it must paginate via "page" instead.
        qr_params["page_size"] = min(arguments["limit"], LIST_QR_CODES_MAX_LIMIT)
    if arguments.get("search"):
        qr_params["search"] = arguments["search"]
    if arguments.get("is_page") is not None:
        qr_params["is_page"] = arguments["is_page"]
    return qr_params or None


def _list_tags_params(arguments: dict) -> dict:
    params = {}
    if arguments.get("name"):
        params["name"] = arguments["name"]
    if arguments.get("page"):
        params["page"] = arguments["page"]
    if arguments.get("page_size"):
        params["page_size"] = arguments["page_size"]
    return params


# Dispatch table: tool_name -> callable(arguments, api_key) -> result
_DISPATCH = {
    # ------------------------------------------------------------------ #
    # Docs MCP Bridge (api_key unused — public docs server)
    # ------------------------------------------------------------------ #
    "probe_docs_mcp": lambda a, k: docs_client.probe(),
    "query_docs": lambda a, k: (
        docs_client.search(a["query"]) if a.get("mode") == "search"
        else docs_client.filesystem(a["query"])
    ),
    # ------------------------------------------------------------------ #
    # QR Code Creation & Validation
    # ------------------------------------------------------------------ #
    "get_qr_categories": lambda a, k: get_qr_categories(
        view_type=a.get("view_type", "all"), api_key=k
    ),
    "get_qr_category_fields": lambda a, k: get_qr_category_fields(a.get("category")),
    "validate_qr_info": lambda a, k: validate_qr_info(
        category=a.get("category"), info=a.get("info"), api_key=k
    ),
    "create_qr_code": lambda a, k: _create_qr_code_handler(a, k),
    "open_qr_code_creation_form": lambda a, k: _open_qr_code_creation_form_handler(a),
    # ------------------------------------------------------------------ #
    # QR Code Design
    # ------------------------------------------------------------------ #
    "get_qr_design_options": lambda a, k: DESIGN_OPTIONS,
    "set_qr_design": lambda a, k: _set_qr_design_handler(a, k),
    "preview_qr_design": lambda a, k: _preview_qr_design_handler(a, k),
    "list_custom_domains": lambda a, k: _list_custom_domains_handler(a, k),
    # ------------------------------------------------------------------ #
    # QR Code Lifecycle & Retrieval
    # ------------------------------------------------------------------ #
    "list_qr_codes": lambda a, k: list_qr_codes(_list_qr_params(a), api_key=k),
    "retrieve_qr_code": lambda a, k: retrieve_qr_code(a.get("qrid"), api_key=k),
    "update_qr_code": lambda a, k: update_qr_code(a.get("qrid"), a.get("params"), api_key=k),
    "activate_qr_code": lambda a, k: activate_qr_code(a.get("qrid"), api_key=k),
    "deactivate_qr_code": lambda a, k: deactivate_qr_code(a.get("qrid"), api_key=k),
    "delete_qr_code": lambda a, k: delete_qr_code(a.get("qrid"), api_key=k),
    # ------------------------------------------------------------------ #
    # QR Code Export & Download
    # ------------------------------------------------------------------ #
    "download_qr_code": lambda a, k: download_qr_code(a.get("qrid"), a.get("params"), api_key=k),
    # download_qr_printable removed for now (2026-08-21) — not registered.
    # ------------------------------------------------------------------ #
    # Organization: Folders
    # ------------------------------------------------------------------ #
    "create_folder": lambda a, k: create_folder(
        name=a["name"], folder_type=a["folder_type"], api_key=k
    ),
    "list_folders": lambda a, k: list_folders(
        folder_type=a["folder_type"], api_key=k
    ),
    "update_folder": lambda a, k: update_folder(
        folder_id=a["folder_id"], name=a["name"], api_key=k
    ),
    "delete_folder": lambda a, k: delete_folder(
        folder_id=a["folder_id"],
        move_to_uncategorized=a.get("move_to_uncategorized", True),
        delete_permanently=a.get("delete_permanently", False),
        api_key=k,
    ),
    "move_qr_codes_to_folder": lambda a, k: move_qr_codes_to_folder(
        folder_id=a["folder_id"],
        qr_code_ids=a["qr_code_ids"],
        from_folder_id=a.get("from_folder_id"),
        api_key=k,
    ),
    "unassign_qr_codes_from_folder": lambda a, k: unassign_qr_codes_from_folder(
        folder_id=a["folder_id"], qr_code_ids=a["qr_code_ids"], api_key=k
    ),
    # ------------------------------------------------------------------ #
    # Organization: Tags
    # ------------------------------------------------------------------ #
    "list_tags": lambda a, k: list_tags(**_list_tags_params(a), api_key=k),
    # ------------------------------------------------------------------ #
    # Forms
    # ------------------------------------------------------------------ #
    "list_forms": lambda a, k: list_forms(is_active=a.get("is_active"), api_key=k),
    "retrieve_form": lambda a, k: retrieve_form(form_id=a["form_id"], api_key=k),
    "create_form": lambda a, k: _create_form_handler(a, k),
    "update_form": lambda a, k: update_form(
        form_id=a["form_id"],
        name=a.get("name"),
        is_active=a.get("is_active"),
        api_key=k,
    ),
    "delete_form": lambda a, k: delete_form(form_id=a["form_id"], api_key=k),
    "attach_form_to_qr": lambda a, k: attach_form_to_qr(
        qrid=a.get("qrid"), form_id=a.get("form_id"), api_key=k
    ),
    "detach_form_from_qr": lambda a, k: detach_form_from_qr(a.get("qrid"), api_key=k),
    # ------------------------------------------------------------------ #
    # Lead Lists (legacy — superseded by Forms)
    # ------------------------------------------------------------------ #
    "list_lead_lists": lambda a, k: list_lead_lists(is_active=a.get("is_active"), api_key=k),
    "retrieve_lead_list": lambda a, k: retrieve_lead_list(
        lead_list_id=a["lead_list_id"], api_key=k
    ),
    "update_lead_list": lambda a, k: update_lead_list(
        lead_list_id=a["lead_list_id"],
        name=a.get("name"),
        is_active=a.get("is_active"),
        api_key=k,
    ),
    "delete_lead_list": lambda a, k: delete_lead_list(
        lead_list_id=a["lead_list_id"], api_key=k
    ),
    "attach_lead_list_to_qr": lambda a, k: attach_lead_list_to_qr(
        qrid=a.get("qrid"), lead_list_id=a.get("lead_list_id"), api_key=k
    ),
    "detach_lead_list_from_qr": lambda a, k: detach_lead_list_from_qr(a.get("qrid"), api_key=k),
    # ------------------------------------------------------------------ #
    # Analytics & Reporting
    # ------------------------------------------------------------------ #
    "get_account_stats": lambda a, k: get_account_stats(
        fields=a.get("fields"), api_key=k
    ),
    "get_qr_analytics": lambda a, k: get_qr_analytics(
        filter_by=a["filter_by"],
        q=a["q"],
        types=a["types"],
        from_date=a["from_date"],
        to_date=a["to_date"],
        exclude_bot_scan=a.get("exclude_bot_scan", False),
        api_key=k,
    ),
    # export_analytics / export_raw_scans removed for now (2026-08-24) — not
    # registered as tools, but the underlying analytics.py functions are
    # left in place for an easy re-enable later.
    # ------------------------------------------------------------------ #
    # Account & Billing
    # ------------------------------------------------------------------ #
    "get_current_plan": lambda a, k: get_current_plan(api_key=k),
    # ------------------------------------------------------------------ #
    # Team & Access Management
    # ------------------------------------------------------------------ #
    "list_users": lambda a, k: list_users(api_key=k),
    "get_user": lambda a, k: get_user(user_id=a["user_id"], api_key=k),
    "add_user": lambda a, k: add_user(email=a["email"], role=a["role"], api_key=k),
    "remove_user": lambda a, k: remove_user(user_id=a["user_id"], api_key=k),
    "list_user_roles": lambda a, k: list_user_roles(api_key=k),
    "create_custom_role": lambda a, k: create_custom_role(
        name=a["name"], permissions=a["permissions"], api_key=k
    ),
    "update_user_role": lambda a, k: update_user_role(
        user_id=a["user_id"], access_level=a["access_level"], api_key=k
    ),
    # One-endpoint tools declared in more_tools.py
    **{t.name: t.handler for t in MORE_TOOLS},
}


def execute_tool(tool_name: str, arguments: dict, api_key: str):
    """Invoke the Scanova backend for a named MCP tool."""
    handler = _DISPATCH.get(tool_name)
    if handler is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    return handler(arguments, api_key)
