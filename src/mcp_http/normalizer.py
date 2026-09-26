"""
Normalize every Scanova tool response into a stable, machine-parseable JSON schema.

Output shape (all keys always present):
{
    "ok":         bool,
    "status_code": int,
    "endpoint":   str | null,
    "request_id": any | null,
    "data":       dict | list | null,
    "pagination": {"count": int, "next": int|null, "previous": int|null} | null,
    "error":      any | null,
    "raw":        any
}

Fallback shape (when the raw payload cannot be parsed at all):
{
    "ok":            false,
    "status_code":   int,
    "parse_error":   str,
    "raw_text":      str,
    "content_type":  str,
    "suggested_fix": str
}
"""

import ast
import json
import re

from mcp_http.more_tools import MORE_TOOLS

# Map tool names to the Scanova API endpoint path (informational, not used for routing)
_TOOL_ENDPOINTS = {
    # QR codes
    "create_qr_code":          "qr/",
    "list_qr_codes":           "qr/",
    "update_qr_code":          "qr/{qrid}/",
    "retrieve_qr_code":        "qr/{qrid}/",
    "download_qr_code":        "qr/{qrid}/download/",
    "activate_qr_code":        "qr/{qrid}/",
    "deactivate_qr_code":      "qr/{qrid}/",
    "delete_qr_code":          "qr/{qrid}/",
    "get_qr_categories":       "qr/category/",
    "download_qr_printable":   "qr/{qrid}/download/",
    "attach_form_to_qr":       "qr/{qrid}/",
    "detach_form_from_qr":     "qr/{qrid}/",
    "attach_lead_list_to_qr":  "qr/{qrid}/",
    "detach_lead_list_from_qr":"qr/{qrid}/",
    "get_qr_design_options":   "(local)",
    "set_qr_design":           "qr/{qrid}/",
    # Analytics
    "get_account_stats":       "auth/stats/",
    "get_qr_analytics":        "analytics/qr/",
    "export_analytics":        "analytics/qr/export/",
    "export_raw_scans":        "analytics/qr/raw/",
    # Folders
    "create_folder":           "folder/",
    "list_folders":            "folder/",
    "update_folder":           "folder/{id}/",
    "delete_folder":           "folder/{id}/",
    "move_qr_codes_to_folder":    "folder/{id}/bulk_move/",
    "unassign_qr_codes_from_folder": "folder/{id}/bulk_unassign/",
    # Forms
    "list_forms":              "form/",
    "retrieve_form":           "form/{id}/",
    "update_form":             "form/{id}/",
    "delete_form":             "form/{id}/",
    # Leads
    "list_lead_lists":         "lead/",
    "retrieve_lead_list":      "lead/{id}/",
    "update_lead_list":        "lead/{id}/",
    "delete_lead_list":        "lead/{id}/",
    # Users
    "list_users":              "user/",
    "get_user":                "user/{id}/",
    "add_user":                "user/",
    "remove_user":             "user/{id}/",
    "list_user_roles":         "multi-users/access-levels/",
    "update_user_role":        "user/{id}/",
    # Docs bridge
    "probe_docs_mcp":          "docs.scanova.io/mcp",
    "query_docs":              "docs.scanova.io/mcp",
    # One-endpoint tools declared in more_tools.py
    **{t.name: t.endpoint for t in MORE_TOOLS},
}

# Keys containing large binary payloads — excluded from `raw` to avoid doubling the payload
_BINARY_KEYS = frozenset({"data_base64"})


def _strip_binary(obj):
    """Return a copy of a dict with binary keys removed (for the raw field)."""
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if k not in _BINARY_KEYS}
    return obj


# Auth-error substrings that indicate a 401
_AUTH_STRINGS = frozenset({
    "api key is required",
    "unauthorized",
    "authentication credentials were not provided",
    "invalid token",
})

# Substrings that map to specific status codes
_STATUS_HINTS = [
    ({"api request failed", "connection error", "timed out"}, 503),
    ({"not found"}, 404),
    ({"permission denied", "forbidden"}, 403),
]


def _infer_status_code(raw: dict, ok: bool) -> int:
    if ok:
        return 200
    # The real HTTP status, when the API module kept it (api_response.api_result).
    status = raw.get("status_code")
    if isinstance(status, int) and 400 <= status <= 599:
        return status
    err = raw.get("error") or raw.get("detail") or ""
    if isinstance(err, dict):
        # DRF / JSON-RPC error object
        code = err.get("code")
        if isinstance(code, int) and 100 <= code <= 599:
            return code
        err = str(err)
    if isinstance(err, str):
        lower = err.lower()
        for hint_set, code in _STATUS_HINTS:
            if any(h in lower for h in hint_set):
                return code
        if any(a in lower for a in _AUTH_STRINGS):
            return 401
    # DRF validation errors arrive as dicts with field names
    if isinstance(raw, dict) and not raw.get("error") and not raw.get("success"):
        return 422
    return 400


def _parse_python_literal(text: str):
    """
    Try to parse a Python-repr string (None, True/False, single-quoted keys, etc.)
    using ast.literal_eval and return the result, or None on failure.
    """
    try:
        return ast.literal_eval(text.strip())
    except Exception:
        return None


def _try_parse_string(value: str):
    """
    Try to parse a string value as JSON, then as a Python literal.
    Returns the parsed object or None if both fail.
    """
    stripped = value.strip()
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    return _parse_python_literal(stripped)


def _expand_string_fields(obj):
    """
    Walk a dict; for any string value that looks like embedded JSON or Python repr,
    keep the original as `<key>_raw` and add the parsed form as `<key>_parsed`.
    Non-string fields and unparseable strings are left untouched.
    """
    if not isinstance(obj, dict):
        return obj
    out = {}
    for k, v in obj.items():
        if isinstance(v, str):
            parsed = _try_parse_string(v)
            if parsed is not None:
                out[f"{k}_raw"] = v
                out[f"{k}_parsed"] = parsed
                continue
        out[k] = v
    return out


def _extract_page_number(url_or_val) -> int | None:
    """Extract a page number from a URL query string, an integer, or a numeric string."""
    if url_or_val is None:
        return None
    if isinstance(url_or_val, int):
        return url_or_val
    if isinstance(url_or_val, str):
        m = re.search(r"[?&]page=(\d+)", url_or_val)
        if m:
            return int(m.group(1))
        try:
            return int(url_or_val)
        except ValueError:
            pass
    return None


def _unwrap_jsonrpc(raw: dict, tool_name: str) -> dict | None:
    """
    If `raw` is a JSON-RPC envelope, unwrap it and return the normalized inner payload.
    Returns None if `raw` is not a JSON-RPC envelope.
    """
    if "jsonrpc" not in raw:
        return None

    request_id = raw.get("id")

    if "error" in raw:
        err = raw["error"]
        code = err.get("code", 400) if isinstance(err, dict) else 400
        return {
            "ok": False,
            "status_code": code if isinstance(code, int) and 100 <= code <= 599 else 400,
            "endpoint": _TOOL_ENDPOINTS.get(tool_name),
            "request_id": request_id,
            "data": None,
            "pagination": None,
            "error": err,
            "raw": _strip_binary(raw),
        }

    inner = raw.get("result", {})

    # MCP tool-call result: result.content[0].text may contain Python repr
    if isinstance(inner, dict) and "content" in inner:
        content = inner["content"]
        if content and isinstance(content, list) and content[0].get("type") == "text":
            text = content[0]["text"]
            parsed = None
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = _parse_python_literal(text)
            if parsed is not None:
                inner = parsed

    # Recurse on the unwrapped payload (may itself be another envelope or a plain dict)
    result = normalize(inner, tool_name)
    result["request_id"] = request_id
    return result


def normalize(raw, tool_name: str) -> dict:
    """
    Convert any raw Scanova tool result into the stable output schema.

    Handles:
    - Plain dicts returned by API modules
    - Python repr strings (ast.literal_eval)
    - JSON strings
    - JSON-RPC envelopes (jsonrpc + id + result/error)
    - MCP content envelopes with Python repr inside content[0].text
    - Paginated lists (count + results)
    - Nested string-encoded JSON / Python repr in field values
    - Auth errors, validation errors, network errors
    """
    endpoint = _TOOL_ENDPOINTS.get(tool_name)

    # ------------------------------------------------------------------ #
    # 1. Coerce the input to a Python object
    # ------------------------------------------------------------------ #
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            parsed = _parse_python_literal(raw)
            if parsed is not None:
                raw = parsed
            else:
                return {
                    "ok": False,
                    "status_code": 500,
                    "parse_error": "Response was not valid JSON or a Python literal",
                    "raw_text": raw,
                    "content_type": "text/plain",
                    "suggested_fix": (
                        "Inspect the raw API response. "
                        "If it is Python repr (single quotes, None, True/False), "
                        "ensure ast.literal_eval can parse it."
                    ),
                }

    # Wrap bare scalars
    if not isinstance(raw, (dict, list)):
        raw = {"value": raw}

    # ------------------------------------------------------------------ #
    # 2. Unwrap JSON-RPC envelopes
    # ------------------------------------------------------------------ #
    if isinstance(raw, dict) and "jsonrpc" in raw:
        unwrapped = _unwrap_jsonrpc(raw, tool_name)
        if unwrapped is not None:
            return unwrapped

    # ------------------------------------------------------------------ #
    # 3. Bare list — treat as a successful result set
    # ------------------------------------------------------------------ #
    if isinstance(raw, list):
        return {
            "ok": True,
            "status_code": 200,
            "endpoint": endpoint,
            "request_id": None,
            "data": raw,
            "pagination": None,
            "error": None,
            "raw": _strip_binary(raw),
        }

    # ------------------------------------------------------------------ #
    # 4. Determine ok / error
    # ------------------------------------------------------------------ #
    local_error = raw.get("error")
    ok_field = raw.get("ok")        # docs_client uses {"ok": bool}
    success_field = raw.get("success")  # some endpoints use {"success": True}

    is_error = (
        local_error is not None
        or ok_field is False
        or (success_field is False and "error" in raw)
    )

    # DRF validation errors: dict with field-name keys, no "error" top-level key,
    # no "count"/"results" — treated as 422
    is_validation_error = (
        not is_error
        and "count" not in raw
        and "results" not in raw
        and success_field is None
        and ok_field is None
        and any(isinstance(v, list) for v in raw.values())
        and not raw.get("id")  # avoid false-positive on QR code objects
    )

    if is_error:
        return {
            "ok": False,
            "status_code": _infer_status_code(raw, False),
            "endpoint": endpoint,
            "request_id": None,
            "data": None,
            "pagination": None,
            "error": local_error if local_error is not None else raw,
            "raw": _strip_binary(raw),
        }

    if is_validation_error:
        return {
            "ok": False,
            "status_code": 422,
            "endpoint": endpoint,
            "request_id": None,
            "data": None,
            "pagination": None,
            "error": raw,
            "raw": _strip_binary(raw),
        }

    # ------------------------------------------------------------------ #
    # 5. Success — paginated list?
    # ------------------------------------------------------------------ #
    if "count" in raw and "results" in raw:
        results = raw["results"]
        expanded = [
            _expand_string_fields(r) if isinstance(r, dict) else r
            for r in results
        ]
        return {
            "ok": True,
            "status_code": 200,
            "endpoint": endpoint,
            "request_id": None,
            "data": {"count": raw["count"], "results": expanded},
            "pagination": {
                "count": raw["count"],
                "next": _extract_page_number(raw.get("next")),
                "previous": _extract_page_number(raw.get("previous")),
            },
            "error": None,
            "raw": _strip_binary(raw),
        }

    # ------------------------------------------------------------------ #
    # 6. Success — single object or flat result
    # ------------------------------------------------------------------ #
    return {
        "ok": True,
        "status_code": 200,
        "endpoint": endpoint,
        "request_id": None,
        "data": _expand_string_fields(raw),
        "pagination": None,
        "error": None,
        "raw": _strip_binary(raw),
    }
