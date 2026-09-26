"""Output schema definitions for all MCP tools (JSON Schema format)."""

from mcp_http.more_tools import MORE_TOOLS

# ── Shared building blocks ─────────────────────────────────────────────────── #

_ERROR = {"error": {"type": "string", "description": "Human-readable error message"}}

_QR_OBJECT = {
    "type": "object",
    "description": "A Scanova QR code object",
    "properties": {
        "qrid": {"type": "string", "description": "Unique QR code identifier"},
        "name": {"type": "string", "description": "Display name of the QR code"},
        "category": {"type": "integer", "description": "QR code category ID (1=URL, 11=vCard, etc.)"},
        "qr_type": {"type": "string", "enum": ["dy", "st"], "description": "Dynamic or static"},
        "status": {"type": "string", "enum": ["active", "inactive"], "description": "Activation status"},
        "info": {"type": "object", "description": "Payload data (type + data fields)"},
        "pattern_info": {"type": "string", "description": "JSON string with visual design settings"},
        "created_at": {"type": "string", "description": "ISO 8601 creation timestamp"},
        "updated_at": {"type": "string", "description": "ISO 8601 last-modified timestamp"},
        **_ERROR,
    },
}

_FOLDER_OBJECT = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "folder_type": {"type": "string"},
        "qr_count": {"type": "integer"},
        **_ERROR,
    },
}

_FORM_OBJECT = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "is_active": {"type": "boolean"},
        "fields": {"type": "array", "items": {"type": "object"}},
        **_ERROR,
    },
}

_LEAD_LIST_OBJECT = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "is_active": {"type": "boolean"},
        "webhook_url": {"type": "string"},
        **_ERROR,
    },
}

_USER_OBJECT = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "email": {"type": "string"},
        "role": {"type": "string"},
        "status": {"type": "string"},
        **_ERROR,
    },
}

# ── Docs MCP Bridge ────────────────────────────────────────────────────────── #

PROBE_DOCS_MCP_OUTPUT = {
    "type": "object",
    "properties": {
        "connected": {"type": "boolean", "description": "True if the docs MCP server responded"},
        "server": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
            },
        },
        "available_tools": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of tool names offered by the docs MCP server",
        },
        **_ERROR,
    },
}

QUERY_DOCS_OUTPUT = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean", "description": "True when the docs server returned a result"},
        "result": {"type": "string", "description": "Text content from the documentation"},
        "truncated": {"type": "boolean", "description": "True when the result was cut to fit a model's context"},
        "note": {"type": "string", "description": "How to narrow down a truncated result"},
        "error": {"type": "string", "description": "Error message when ok is false"},
    },
}

# ── QR Code Design ─────────────────────────────────────────────────────────── #

GET_QR_DESIGN_OPTIONS_OUTPUT = {
    "type": "object",
    "properties": {
        "data_patterns": {
            "type": "array",
            "items": {"type": "string"},
            "description": "All valid pattern names for the pattern field",
        },
        "eye_shapes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "All valid eye shape codes (Shape0, Shape1, …)",
        },
        "gradient_styles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Gradient options: None, Horizontal, Vertical, Diagonal, Radial",
        },
        "frame_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Available frame template IDs",
        },
        "shape_container_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Available shape container IDs",
        },
        "error_correction": {
            "type": "object",
            "description": "Error correction levels: L (7%), M (15%), Q (25%), H (30%)",
            "properties": {
                "L": {"type": "string"},
                "M": {"type": "string"},
                "Q": {"type": "string"},
                "H": {"type": "string"},
            },
        },
        "fonts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Available font families for frame text",
        },
        "tips": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Design tips and recommendations",
        },
    },
}

SET_QR_DESIGN_OUTPUT = {
    "type": "object",
    "description": "Updated QR code with the new design applied",
    "properties": {
        **_QR_OBJECT["properties"],
    },
}

_CHECK = {
    "type": "object",
    "properties": {
        "check": {"type": "string"},
        "level": {"type": "string", "enum": ["ok", "warn", "fail"]},
        "message": {"type": "string"},
        "ratio": {"type": "number"},
    },
}

PREVIEW_QR_DESIGN_OUTPUT = {
    "type": "object",
    "description": "A design that was checked and rendered but not saved",
    "properties": {
        "preview": {"type": "boolean"},
        "saved": {"type": "boolean"},
        "content": {"type": "string", "description": "What the image encodes"},
        "pattern_info": {"type": "object", "description": "The design, as set_qr_design would save it"},
        "checks": {"type": "array", "items": _CHECK},
        "scan": {"type": "object", "properties": {"scannable": {"type": ["boolean", "null"]}, "message": {"type": "string"}}},
        "summary": {
            "type": "object",
            "properties": {"safe": {"type": "boolean"}, "verdict": {"type": "string"}, "failures": {"type": "integer"}, "warnings": {"type": "integer"}},
        },
        "image": {"type": "string", "description": "data: URI of the rendered preview"},
        **_ERROR,
    },
}

LIST_CUSTOM_DOMAINS_OUTPUT = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "domain": {"type": "string"},
                    "is_default": {"type": "boolean"},
                    "is_txt_verified": {"type": "boolean"},
                    "is_cname_verified": {"type": "boolean"},
                },
            },
        },
        **_ERROR,
    },
}

# ── QR Code Creation & Validation ──────────────────────────────────────────── #

GET_QR_CATEGORY_FIELDS_OUTPUT = {
    "type": "object",
    "description": "Either one category's info-field reference (when `category` was given) or the full {categories: {...}} catalog",
    "properties": {
        "category": {"type": "integer"},
        "name": {"type": "string"},
        "slug": {"type": "string"},
        "documented": {"type": "boolean"},
        "info_example": {"description": "Example info payload — object or array depending on the category"},
        "notes": {"type": "string"},
        "categories": {"type": "object", "description": "Present when no category was given — the full catalog keyed by category ID"},
        **_ERROR,
    },
}

OPEN_QR_CODE_CREATION_FORM_OUTPUT = {
    "type": "object",
    "properties": {
        "mode": {"type": "string"},
        "prefill": {"type": "object"},
    },
}

VALIDATE_QR_INFO_OUTPUT = {
    "type": "object",
    "properties": {
        "valid": {"type": "boolean"},
        "message": {"type": "string"},
        "error": {"description": "Validation error details when valid is false"},
        **_ERROR,
    },
}

# ── QR Code Management ─────────────────────────────────────────────────────── #

CREATE_QR_CODE_OUTPUT = _QR_OBJECT

# Matches normalizer.py's actual envelope for paginated list tools: the
# full {ok, data: {count, results}, pagination, error, ...} shape emitted
# as structuredContent — not just the inner "data" object.
LIST_QR_CODES_OUTPUT = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "data": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "results": {"type": "array", "items": _QR_OBJECT},
            },
            "description": "Page of QR code objects with the total count",
        },
        "pagination": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "next": {"type": ["integer", "null"]},
                "previous": {"type": ["integer", "null"]},
            },
        },
        **_ERROR,
    },
}

UPDATE_QR_CODE_OUTPUT = _QR_OBJECT
RETRIEVE_QR_CODE_OUTPUT = _QR_OBJECT
ACTIVATE_QR_CODE_OUTPUT = _QR_OBJECT
DEACTIVATE_QR_CODE_OUTPUT = _QR_OBJECT

DOWNLOAD_QR_CODE_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        "content_type": {
            "type": "string",
            "description": "MIME type, e.g. image/png, image/svg+xml, application/pdf",
        },
        **_ERROR,
    },
}

DELETE_QR_CODE_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string", "example": "QR code deleted"},
        **_ERROR,
    },
}

GET_QR_CATEGORIES_OUTPUT = {
    "type": "object",
    "properties": {
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "slug": {"type": "string"},
                },
            },
        },
        **_ERROR,
    },
}

DOWNLOAD_QR_PRINTABLE_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "content_type": {"type": "string", "example": "application/pdf"},
        "content_length": {"type": "integer", "description": "File size in bytes"},
        "size": {"type": "integer", "description": "Requested pixel size"},
        "name": {"type": "string"},
        **_ERROR,
    },
}

ATTACH_DETACH_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        **_ERROR,
    },
}

# ── Analytics ─────────────────────────────────────────────────────────────── #

GET_ACCOUNT_STATS_OUTPUT = {
    "type": "object",
    "description": "Account-level usage counters",
    "properties": {
        "total_qr_codes": {"type": "integer"},
        "total_scans": {"type": "integer"},
        "total_users": {"type": "integer"},
        "active_qr_codes": {"type": "integer"},
        **_ERROR,
    },
}

GET_QR_ANALYTICS_OUTPUT = {
    "type": "object",
    "description": "QR code scan metrics broken down by the requested dimension",
    "properties": {
        "data": {"type": "array", "items": {"type": "object"}},
        "total": {"type": "integer"},
        **_ERROR,
    },
}

EXPORT_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "content_type": {"type": "string"},
        "content_length": {"type": "integer"},
        "download_url": {"type": "string"},
        **_ERROR,
    },
}

# ── Folder Management ─────────────────────────────────────────────────────── #

CREATE_FOLDER_OUTPUT = _FOLDER_OBJECT
UPDATE_FOLDER_OUTPUT = _FOLDER_OBJECT

LIST_FOLDERS_OUTPUT = {
    "type": "object",
    "properties": {
        "data": {"type": "array", "items": _FOLDER_OBJECT},
        **_ERROR,
    },
}

DELETE_FOLDER_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        **_ERROR,
    },
}

MOVE_QR_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "moved": {"type": "integer", "description": "Number of QR codes moved"},
        **_ERROR,
    },
}

# ── Forms ─────────────────────────────────────────────────────────────────── #

LIST_FORMS_OUTPUT = {
    "type": "object",
    "properties": {
        "data": {"type": "array", "items": _FORM_OBJECT},
        **_ERROR,
    },
}

RETRIEVE_FORM_OUTPUT = _FORM_OBJECT
UPDATE_FORM_OUTPUT = _FORM_OBJECT

DELETE_FORM_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        **_ERROR,
    },
}

CREATE_FORM_OUTPUT = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "form_id": {"type": "string"},
        "name": {"type": "string"},
        "form_url": {"type": "string"},
        "is_active": {"type": "boolean"},
        "linked_qrs": {"type": "array"},
        "data": {"type": "object"},
        **_ERROR,
    },
}

# ── Lead Lists ────────────────────────────────────────────────────────────── #

LIST_LEAD_LISTS_OUTPUT = {
    "type": "object",
    "properties": {
        "data": {"type": "array", "items": _LEAD_LIST_OBJECT},
        **_ERROR,
    },
}

RETRIEVE_LEAD_LIST_OUTPUT = _LEAD_LIST_OBJECT
UPDATE_LEAD_LIST_OUTPUT = _LEAD_LIST_OBJECT

DELETE_LEAD_LIST_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        **_ERROR,
    },
}

# ── Tags ──────────────────────────────────────────────────────────────────── #

_TAG_OBJECT = {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}}

LIST_TAGS_OUTPUT = {
    "type": "object",
    "description": "Matches normalizer.py's paginated envelope shape — see LIST_QR_CODES_OUTPUT",
    "properties": {
        "ok": {"type": "boolean"},
        "data": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "results": {"type": "array", "items": _TAG_OBJECT},
            },
        },
        "pagination": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "next": {"type": ["integer", "null"]},
                "previous": {"type": ["integer", "null"]},
            },
        },
        **_ERROR,
    },
}

# ── Account & Billing ─────────────────────────────────────────────────────── #

GET_CURRENT_PLAN_OUTPUT = {
    "type": "object",
    "properties": {
        "is_active": {"type": "boolean"},
        "is_free": {"type": "boolean"},
        "expire": {"type": "string", "description": "YYYY-MM-DD, or 'Lifetime'"},
        "is_expired": {"type": "boolean"},
        "days_left": {"type": "integer"},
        "recurring_enabled": {"type": "boolean"},
        "plan": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "plan_type": {"type": "string"},
                "quotas": {"type": "array", "items": {"type": "object"}},
            },
        },
        "upcoming_plan": {"type": ["object", "null"]},
        **_ERROR,
    },
}

# ── User Management ───────────────────────────────────────────────────────── #

LIST_USERS_OUTPUT = {
    "type": "object",
    "properties": {
        "data": {"type": "array", "items": _USER_OBJECT},
        **_ERROR,
    },
}

GET_USER_OUTPUT = _USER_OBJECT
ADD_USER_OUTPUT = _USER_OBJECT
UPDATE_USER_ROLE_OUTPUT = _USER_OBJECT

REMOVE_USER_OUTPUT = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        **_ERROR,
    },
}

LIST_USER_ROLES_OUTPUT = {
    "type": "object",
    "properties": {
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        **_ERROR,
    },
}

CREATE_CUSTOM_ROLE_OUTPUT = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "permissions": {"type": "array", "items": {"type": "object"}},
        "is_custom": {"type": "boolean"},
        **_ERROR,
    },
}

# ── Lookup table: tool_name → outputSchema ────────────────────────────────── #

TOOL_OUTPUT_SCHEMAS: dict[str, dict] = {
    # Docs bridge
    "probe_docs_mcp": PROBE_DOCS_MCP_OUTPUT,
    "query_docs": QUERY_DOCS_OUTPUT,
    # QR Code Creation & Validation
    "get_qr_categories": GET_QR_CATEGORIES_OUTPUT,
    "get_qr_category_fields": GET_QR_CATEGORY_FIELDS_OUTPUT,
    "validate_qr_info": VALIDATE_QR_INFO_OUTPUT,
    "create_qr_code": CREATE_QR_CODE_OUTPUT,
    "open_qr_code_creation_form": OPEN_QR_CODE_CREATION_FORM_OUTPUT,
    # QR Code Design
    "get_qr_design_options": GET_QR_DESIGN_OPTIONS_OUTPUT,
    "set_qr_design": SET_QR_DESIGN_OUTPUT,
    "preview_qr_design": PREVIEW_QR_DESIGN_OUTPUT,
    "list_custom_domains": LIST_CUSTOM_DOMAINS_OUTPUT,
    # QR Code Lifecycle & Retrieval
    "list_qr_codes": LIST_QR_CODES_OUTPUT,
    "retrieve_qr_code": RETRIEVE_QR_CODE_OUTPUT,
    "update_qr_code": UPDATE_QR_CODE_OUTPUT,
    "activate_qr_code": ACTIVATE_QR_CODE_OUTPUT,
    "deactivate_qr_code": DEACTIVATE_QR_CODE_OUTPUT,
    "delete_qr_code": DELETE_QR_CODE_OUTPUT,
    # QR Code Export & Download
    "download_qr_code": DOWNLOAD_QR_CODE_OUTPUT,
    "download_qr_printable": DOWNLOAD_QR_PRINTABLE_OUTPUT,
    # Organization: Folders
    "create_folder": CREATE_FOLDER_OUTPUT,
    "list_folders": LIST_FOLDERS_OUTPUT,
    "update_folder": UPDATE_FOLDER_OUTPUT,
    "delete_folder": DELETE_FOLDER_OUTPUT,
    "move_qr_codes_to_folder": MOVE_QR_OUTPUT,
    "unassign_qr_codes_from_folder": MOVE_QR_OUTPUT,
    # Organization: Tags
    "list_tags": LIST_TAGS_OUTPUT,
    # Forms
    "list_forms": LIST_FORMS_OUTPUT,
    "retrieve_form": RETRIEVE_FORM_OUTPUT,
    "create_form": CREATE_FORM_OUTPUT,
    "update_form": UPDATE_FORM_OUTPUT,
    "delete_form": DELETE_FORM_OUTPUT,
    "attach_form_to_qr": ATTACH_DETACH_OUTPUT,
    "detach_form_from_qr": ATTACH_DETACH_OUTPUT,
    # Lead Lists (legacy)
    "list_lead_lists": LIST_LEAD_LISTS_OUTPUT,
    "retrieve_lead_list": RETRIEVE_LEAD_LIST_OUTPUT,
    "update_lead_list": UPDATE_LEAD_LIST_OUTPUT,
    "delete_lead_list": DELETE_LEAD_LIST_OUTPUT,
    "attach_lead_list_to_qr": ATTACH_DETACH_OUTPUT,
    "detach_lead_list_from_qr": ATTACH_DETACH_OUTPUT,
    # Analytics & Reporting
    "get_account_stats": GET_ACCOUNT_STATS_OUTPUT,
    "get_qr_analytics": GET_QR_ANALYTICS_OUTPUT,
    "export_analytics": EXPORT_OUTPUT,
    "export_raw_scans": EXPORT_OUTPUT,
    # Account & Billing
    "get_current_plan": GET_CURRENT_PLAN_OUTPUT,
    # Team & Access Management
    "list_users": LIST_USERS_OUTPUT,
    "get_user": GET_USER_OUTPUT,
    "add_user": ADD_USER_OUTPUT,
    "remove_user": REMOVE_USER_OUTPUT,
    "list_user_roles": LIST_USER_ROLES_OUTPUT,
    "create_custom_role": CREATE_CUSTOM_ROLE_OUTPUT,
    "update_user_role": UPDATE_USER_ROLE_OUTPUT,
    # One-endpoint tools declared in more_tools.py
    **{t.name: t.output_schema for t in MORE_TOOLS},
}


# ── The envelope every tool call actually returns ─────────────────────────── #
#
# call_tool returns normalizer.normalize()'s envelope as structuredContent, and
# MCP requires structured results to conform to the tool's outputSchema. The
# per-tool schemas above describe the Scanova payload; tool_output_schema()
# wraps one in the envelope, with the payload under `data`.
#
# The payload is described leniently on purpose: every field may be null, and a
# list may arrive bare, paginated ({count, results}) or wrapped ({data: [...]}),
# depending on the endpoint. A schema that rejects a real response breaks the
# call in clients that validate (the TypeScript SDK does).

_PAGINATION = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "next": {"type": ["integer", "null"]},
        "previous": {"type": ["integer", "null"]},
    },
}


def _any_id(key, schema):
    # Scanova ids are integers on some endpoints and strings on others.
    if key == "id" and isinstance(schema, dict) and schema.get("type") in ("integer", "string"):
        return {**schema, "type": ["integer", "string"]}
    return schema


def _nullable(schema):
    if not isinstance(schema, dict):
        return schema
    out = dict(schema)
    kind = out.get("type")
    if isinstance(kind, str) and kind != "null":
        out["type"] = [kind, "null"]
    elif isinstance(kind, list) and "null" not in kind:
        out["type"] = [*kind, "null"]
    if "enum" in out:
        out["enum"] = [*out["enum"], None] if None not in out["enum"] else out["enum"]
    if isinstance(out.get("properties"), dict):
        out["properties"] = {k: _nullable(_any_id(k, v)) for k, v in out["properties"].items()}
    if isinstance(out.get("items"), dict):
        out["items"] = _nullable(out["items"])
    for key in ("anyOf", "oneOf"):
        if isinstance(out.get(key), list):
            out[key] = [_nullable(v) for v in out[key]]
    return out


def _list_shapes(item, extra=None):
    items = {"type": "array", "items": item}
    return {
        "anyOf": [
            items,
            {"type": "object", "properties": {"count": {"type": "integer"}, "results": items}},
            {"type": "object", "properties": {"data": items, **(extra or {})}},
        ]
    }


def _payload(schema: dict) -> dict:
    props = schema.get("properties", {})
    data = props.get("data", {})
    if "pagination" in props:
        # Already written as the paginated envelope: its `data` is the payload.
        results = data.get("properties", {}).get("results", {})
        return _list_shapes(results.get("items", {"type": "object"}))
    if data.get("type") == "array":
        extra = {k: v for k, v in props.items() if k not in ("data", "error")}
        return _list_shapes(data.get("items", {"type": "object"}), extra)
    payload = {k: v for k, v in schema.items() if k != "properties"}
    payload["properties"] = {k: v for k, v in props.items() if k != "error"}
    return payload


def tool_output_schema(schema: dict) -> dict:
    payload = _nullable(_payload(schema))
    return {
        "type": "object",
        "description": schema.get("description", "Result envelope; the tool's result is in `data`"),
        "required": ["ok", "status_code"],
        "properties": {
            "ok": {"type": "boolean", "description": "True when the call succeeded"},
            "status_code": {"type": "integer", "description": "HTTP-style status of the Scanova call"},
            "endpoint": {"type": ["string", "null"]},
            "request_id": {},
            "data": {"description": "The result on success; null on failure", "anyOf": [payload, {"type": "null"}]},
            "pagination": {"anyOf": [_PAGINATION, {"type": "null"}]},
            "error": {"description": "Null on success; the error message or the API's error object on failure"},
            "raw": {"description": "The unmodified API response"},
            "parse_error": {"type": "string"},
            "raw_text": {"type": "string"},
            "content_type": {"type": "string"},
            "suggested_fix": {"type": "string"},
        },
    }
