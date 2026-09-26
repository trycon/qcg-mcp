"""JSON Schema fragments for MCP tool input parameters."""

CREATE_QR_PARAMS_SCHEMA = {
    "type": "object",
    "description": "Scanova API create payload (POST /qr/). See https://docs.scanova.io/api-reference/endpoint/qr_manager/create",
    "properties": {
        "name": {
            "type": "string",
            "description": "Human-readable name for the QR code",
        },
        "category": {
            "description": "QR code category ID (e.g. 1=Website URL, 7=vCard, 11=Google Map, 23=App Deep Link). Integer or string. See the info field's description for the full list of supported categories.",
            "oneOf": [{"type": "integer"}, {"type": "string"}],
        },
        "qr_type": {
            "type": "string",
            "enum": ["dy", "st"],
            "description": "dy = Dynamic (content editable after creation); st = Static (fixed content)",
        },
        "info": {
            "type": "string",
            "description": (
                "JSON string of QR content. The structure depends on the category.\n"
                "\n"
                "Simple object format (categories 1, 2, 3, 4, 5, 6, 10, 11):\n"
                '  Website URL (cat 1):   {"type":"url","data":{"url":"https://example.com"}}\n'
                '  Email (cat 2):         {"type":"email","data":{"to":"a@b.com","cc":"c@b.com","bcc":"d@b.com","subject":"Hi","body":"Hello"}}\n'
                '                         to is required; cc, bcc, subject, body are optional.\n'
                '  Text (cat 3):          {"type":"text","data":{"text":"Hello World"}}\n'
                '  Phone (cat 4):         {"type":"phoneNumber","data":{"number":"7011472701"}}\n'
                '  SMS (cat 5):           {"type":"sms","data":{"contactNumber":"7011472701","message":"Hello"}}\n'
                '  WiFi (cat 6):          {"type":"wifi","data":{"ssid":"MyNet","password":"secret","authentication":"WPA"}}\n'
                '                         authentication values: WPA | WPA2 | WEP | none\n'
                '  App Store (cat 10):    {"type":"appStore","data":[{"type":"playStore","url":"https://play.google.com/store/apps/details?id=com.example"},{"type":"appleStore","url":"https://apps.apple.com/app/id123456789"}]}\n'
                '  Google Map (cat 11):   {"type":"map","data":{"provider":"google","latitude":28.6139,"longitude":77.2090,"placeId":"ChIJL_P_CXMEDTkRs_FGKBLBFBE","placeName":"New Delhi, India"}}\n'
                "\n"
                "IMPORTANT: categories 2 and 3 were swapped from an earlier version of this "
                "description — category 2 is Email, category 3 is Text. Also note the field "
                "names above: Email uses data.to (NOT data.email), Phone uses data.number (NOT "
                "data.phone/data.contactNumber), SMS uses data.contactNumber (NOT data.phone).\n"
                "\n"
                "vCard (cat 7) — info is a JSON ARRAY of page-builder sections, NOT a flat "
                "\"vcard\" object:\n"
                '  [{"type":"profile_info","data":{"name":"John Doe","title":"Engineer","company":"Acme Inc"}},'
                '{"type":"contact_details","data":{"emails":[{"email":"john@example.com"}],"phoneNumbers":[{"phoneNumber":"7011472701"}]}}]\n'
                "\n"
                "App Deep Link (cat 23) — info IS the JSON ARRAY of typed sections directly (NO "
                "outer {type,data} wrapper). intentUri (at least one of android/ios) and fallback "
                "are BOTH required; appStore is always optional:\n"
                '  [{"type":"intentUri","data":[{"type":"android","uri":"myapp://open/screen/123"},{"type":"ios","uri":"myapp://open/screen/123"}]},'
                '{"type":"appStore","data":[{"type":"playStore","url":"https://play.google.com/store/apps/details?id=com.example"},{"type":"appleStore","url":"https://apps.apple.com/app/id123456789"}]},'
                '{"type":"fallback","data":{"url":"https://example.com/download"}}]\n'
                "\n"
                "Categories 9, 13, 14, 15, 16, 17, 18, 19, 20, 24, 26, 27, 28, and 31 (Custom Page, "
                "Document, Wedding, Social Media, Audio, Coupon, Product, Image, Event, Business "
                "Card, Feedback, Real Estate, Link Page, GS1) plus Restaurant (25, 44) are BLOCKED "
                "by this server — calling create_qr_code with one of these category IDs returns a "
                "message telling the user to create it via https://app.scanova.io instead. Don't "
                "attempt to construct info for these; tell the user to use the Scanova app.\n"
                "For any other category not listed above, call get_qr_category_fields to look up "
                "the correct info schema before attempting create_qr_code."
            ),
        },
        "pattern_info": {
            "type": "string",
            "description": "Optional JSON string for QR design (pattern, colors, eyes, frame)",
        },
        "custom_domain": {
            "type": "integer",
            "description": "Optional custom domain ID assigned in Scanova",
        },
        "expire_on": {
            "type": "string",
            "description": "Optional expiration timestamp (ISO 8601, e.g. 2025-12-31T23:59:59+05:30)",
        },
    },
    "required": ["name", "category", "qr_type", "info"],
    "additionalProperties": True,
}

UPDATE_QR_PARAMS_SCHEMA = {
    "type": "object",
    "description": (
        "Fields to update (PUT /qr/{qrid}/). Only include fields to change. "
        "category, qr_type, and custom_domain cannot be updated after creation."
    ),
    "properties": {
        "name": {"type": "string", "description": "New display name for the QR code"},
        "info": {
            "type": "string",
            "description": (
                "Updated QR content as a JSON string (structure depends on original category). "
                'URL example: {"type":"url","data":{"url":"https://updated-url.com"}}'
            ),
        },
        "pattern_info": {
            "description": "Design updates (pattern, colors, eyes, frame)",
            "oneOf": [{"type": "string"}, {"type": "object"}],
        },
        "expire_on": {
            "type": "string",
            "description": "Expiration timestamp (ISO 8601)",
        },
        "expire_on_text": {
            "type": "string",
            "description": "HTML shown when the QR code has expired",
        },
        "expire_on_timezone": {
            "type": "string",
            "description": "Timezone for expiration (e.g. Asia/Kolkata)",
        },
        "high_accuracy_confirmation": {"type": "boolean"},
        "high_accuracy_geo_fencing": {"type": "boolean"},
        "high_accuracy_mode": {"type": "boolean"},
        "high_accuracy_mode_text": {"type": "string"},
        "lead_list": {
            "description": "Lead list ID to capture leads; use null to remove association",
            "oneOf": [{"type": "integer"}, {"type": "null"}],
        },
        "minimum_age": {"type": "integer", "description": "Minimum age to access content"},
        "password": {"type": "string", "description": "Password to protect QR code content"},
        "is_active": {
            "type": "boolean",
            "description": "Activate (true) or deactivate (false) the QR code",
        },
    },
    "minProperties": 1,
    "additionalProperties": True,
}

DOWNLOAD_QR_PARAMS_SCHEMA = {
    "type": "object",
    "description": "Download options (GET /qr/{qrid}/download/ query parameters)",
    "properties": {
        "file": {
            "type": "string",
            "enum": ["png", "jpg", "pdf"],
            "default": "png",
            "description": "Output image format",
        },
        "size": {
            "type": "integer",
            "minimum": 10,
            "maximum": 1000,
            "default": 300,
            "description": "Image width and height in pixels",
        },
        "for_print": {
            "type": "boolean",
            "default": False,
            "description": "When true, returns a print-optimized (black and white) QR image",
        },
    },
    "additionalProperties": False,
}

QRID_SCHEMA = {
    "type": "string",
    "description": "Scanova QR code ID (e.g. Qc22580d20dd14c44)",
}

# ---------------------------------------------------------------------------
# QR Code Creation & Validation
# ---------------------------------------------------------------------------

GET_QR_CATEGORY_FIELDS_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "description": "QR code category ID to look up (e.g. 1=Website URL, 24=Business Card). Omit to list all categories.",
            "oneOf": [{"type": "integer"}, {"type": "string"}],
        },
    },
}

OPEN_QR_CODE_CREATION_FORM_SCHEMA = {
    "type": "object",
    "description": (
        "Show an interactive QR code creation form. Use this when the user wants "
        "to create a QR code but hasn't provided enough information yet (missing "
        "or ambiguous name/category/content) — do not guess or invent placeholder "
        "values in that case."
    ),
    "properties": {
        "name": {"type": "string", "description": "Pre-fill the QR name, if already known"},
        "category": {
            "description": "Pre-fill the category ID, if already known",
            "oneOf": [{"type": "integer"}, {"type": "string"}],
        },
        "qr_type": {
            "type": "string",
            "enum": ["dy", "st"],
            "description": "Pre-fill dynamic/static, if already known",
        },
    },
}

VALIDATE_QR_INFO_SCHEMA = {
    "type": "object",
    "description": "Validate a category + info payload before create_qr_code/update_qr_code.",
    "properties": {
        "category": {
            "description": "QR code category ID (see get_qr_categories / get_qr_category_fields).",
            "oneOf": [{"type": "integer"}, {"type": "string"}],
        },
        "info": {
            "type": "string",
            "description": "JSON string of QR content, matching the shape for the given category (see get_qr_category_fields).",
        },
    },
    "required": ["category", "info"],
}

# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

_FILTER_BY_SCHEMA = {
    "type": "string",
    "enum": ["qrid", "tags", "folder"],
    "description": "Filter by: 'qrid' = specific IDs, 'tags' = tag names, 'folder' = folder ID",
}
_Q_SCHEMA = {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of QR code IDs, tags, or folder IDs depending on filter_by",
}

ACCOUNT_STATS_SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "total_qr_count", "static_qr_count", "dynamic_qr_count",
                    "total_scan_count", "total_designer_qr_count",
                    "custom_domain_count", "lead_list_count", "shared_user_count",
                ],
            },
            "description": "Fields to include (omit for all)",
        }
    },
}

GET_QR_ANALYTICS_SCHEMA = {
    "type": "object",
    "properties": {
        "filter_by": _FILTER_BY_SCHEMA,
        "q": _Q_SCHEMA,
        "types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "count", "qr", "device", "os", "browser", "date",
                    "handset", "geography", "geo_location", "age", "day_time",
                ],
            },
            "description": "Metric breakdowns to retrieve",
        },
        "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
        "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
        "exclude_bot_scan": {"type": "boolean", "default": False, "description": "Exclude bot scans"},
    },
    "required": ["filter_by", "q", "types", "from_date", "to_date"],
}

EXPORT_ANALYTICS_SCHEMA = {
    "type": "object",
    "properties": {
        "filter_by": _FILTER_BY_SCHEMA,
        "q": _Q_SCHEMA,
        "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
        "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
        "file_format": {
            "type": "string",
            "enum": ["xls", "xlsx", "pdf"],
            "default": "xlsx",
            "description": "Output file format",
        },
        "exclude_bot_scan": {"type": "boolean", "default": False},
    },
    "required": ["filter_by", "q", "from_date", "to_date"],
}

EXPORT_RAW_SCANS_SCHEMA = {
    "type": "object",
    "properties": {
        "filter_by": _FILTER_BY_SCHEMA,
        "q": _Q_SCHEMA,
        "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
        "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
        "file_format": {
            "type": "string",
            "enum": ["csv", "xls", "xlsx"],
            "default": "csv",
        },
        "scan_type": {
            "type": "string",
            "enum": ["raw", "raw_bot"],
            "default": "raw",
            "description": "'raw' for real scans, 'raw_bot' to include bot scans",
        },
        "exclude_bot_scan": {"type": "boolean", "default": False},
    },
    "required": ["filter_by", "q", "from_date", "to_date"],
}

# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------

FOLDER_TYPE_SCHEMA = {
    "type": "string",
    "enum": ["qr", "page"],
    "description": "'qr' for QR code folders, 'page' for page folders",
}
FOLDER_ID_SCHEMA = {"type": "integer", "description": "Numeric folder ID"}

CREATE_FOLDER_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Folder name"},
        "folder_type": FOLDER_TYPE_SCHEMA,
    },
    "required": ["name", "folder_type"],
}

LIST_FOLDERS_SCHEMA = {
    "type": "object",
    "properties": {"folder_type": FOLDER_TYPE_SCHEMA},
    "required": ["folder_type"],
}

UPDATE_FOLDER_SCHEMA = {
    "type": "object",
    "properties": {
        "folder_id": FOLDER_ID_SCHEMA,
        "name": {"type": "string", "description": "New folder name"},
    },
    "required": ["folder_id", "name"],
}

DELETE_FOLDER_SCHEMA = {
    "type": "object",
    "properties": {
        "folder_id": FOLDER_ID_SCHEMA,
        "move_to_uncategorized": {
            "type": "boolean",
            "default": True,
            "description": "Move contained QR codes to uncategorized instead of deleting",
        },
        "delete_permanently": {
            "type": "boolean",
            "default": False,
            "description": "Permanently delete contained QR codes",
        },
    },
    "required": ["folder_id"],
}

MOVE_QR_TO_FOLDER_SCHEMA = {
    "type": "object",
    "properties": {
        "folder_id": FOLDER_ID_SCHEMA,
        "qr_code_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "QR code IDs to move",
        },
        "from_folder_id": {
            "type": "integer",
            "description": "Source folder ID (omit for uncategorized)",
        },
    },
    "required": ["folder_id", "qr_code_ids"],
}

UNASSIGN_QR_FROM_FOLDER_SCHEMA = {
    "type": "object",
    "properties": {
        "folder_id": FOLDER_ID_SCHEMA,
        "qr_code_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "QR code IDs to remove from the folder",
        },
    },
    "required": ["folder_id", "qr_code_ids"],
}

# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

FORM_ID_SCHEMA = {"type": "string", "description": "Form ID"}

LIST_FORMS_SCHEMA = {
    "type": "object",
    "properties": {
        "is_active": {"type": "boolean", "description": "Filter by active status (omit for all)"},
    },
}

CREATE_FORM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Form name (for the account's list of forms)"},
        "title": {"type": "string", "description": "The title people see at the top of the form"},
        "description": {"type": "string", "description": "Text under the title"},
        "questions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 40,
            "description": "The questions, in order",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "maxLength": 200},
                    "type": {
                        "type": "string",
                        "enum": [
                            "shortAnswer", "paragraph", "email", "phoneNumber", "number",
                            "multipleChoice", "checkbox", "dropdown", "linearScale",
                            "dateFormat", "timeFormat", "starRating", "emoji", "likeDislike",
                        ],
                        "default": "shortAnswer",
                        "description": "The answer type; multipleChoice, checkbox and dropdown need options",
                    },
                    "options": {"type": "array", "items": {"type": "string", "maxLength": 200}, "description": "Choices, for multipleChoice/checkbox/dropdown"},
                    "required": {"type": "boolean", "default": False},
                    "description": {"type": "string", "description": "Help text under the question"},
                },
                "required": ["question"],
            },
        },
        "submit_label": {"type": "string", "maxLength": 100, "description": "The submit button's text (default Submit)"},
        "thank_you": {"type": "string", "description": "Message shown after someone submits"},
        "data": {
            "type": "array",
            "items": {"type": "object"},
            "description": (
                "Advanced, instead of title/questions: the form's blocks as Scanova stores them, "
                "e.g. [{\"type\": \"form_details\", \"data\": {\"title\": ..., \"questions\": [...]}}, "
                "{\"type\": \"submit_button\", \"data\": {\"label\": \"Send\"}}]"
            ),
        },
        "qr_id": {"type": "string", "description": "A dynamic QR code's qrid to attach immediately on creation"},
        "theme_id": {"type": "integer", "description": "An active theme's ID to style the form's public page"},
        "theme_overrides": {"type": "object", "description": "Partial theme token overrides layered on theme_id"},
    },
    "required": ["name"],
}

UPDATE_FORM_SCHEMA = {
    "type": "object",
    "properties": {
        "form_id": FORM_ID_SCHEMA,
        "name": {"type": "string", "description": "New form name"},
        "is_active": {"type": "boolean", "description": "Enable or disable the form"},
    },
    "required": ["form_id"],
}

# ---------------------------------------------------------------------------
# Lead Lists
# ---------------------------------------------------------------------------

LEAD_LIST_ID_SCHEMA = {
    "type": "string",
    "description": (
        "Lead list string identifier — use the lead_id field (e.g. 'L3f4cc7db5bda42ee') "
        "returned by list_lead_lists. Do NOT use the numeric id field; the API only accepts the lead_id string."
    ),
}

LIST_LEAD_LISTS_SCHEMA = {
    "type": "object",
    "properties": {
        "is_active": {"type": "boolean", "description": "Filter by active status (omit for all)"},
    },
}

UPDATE_LEAD_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "lead_list_id": LEAD_LIST_ID_SCHEMA,
        "name": {"type": "string", "description": "New lead list name"},
        "is_active": {"type": "boolean", "description": "Enable or disable the lead list"},
    },
    "required": ["lead_list_id"],
}

# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

LIST_TAGS_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Case-insensitive prefix filter"},
        "page": {"type": "integer", "description": "Page number"},
        "page_size": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
    },
}

# ---------------------------------------------------------------------------
# Account & Billing
# ---------------------------------------------------------------------------

GET_CURRENT_PLAN_SCHEMA = {"type": "object", "properties": {}}

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

USER_ID_SCHEMA = {"type": "string", "description": "User ID"}

ADD_USER_SCHEMA = {
    "type": "object",
    "properties": {
        "email": {"type": "string", "format": "email", "description": "Email address to invite"},
        "role": {"type": "string", "description": "Role to assign (use list_user_roles to see options)"},
    },
    "required": ["email", "role"],
}

CREATE_CUSTOM_ROLE_SCHEMA = {
    "type": "object",
    "description": "Create a custom role (requires a dedicated plan quota — a 403 means the plan doesn't include it).",
    "properties": {
        "name": {"type": "string", "description": "Role name; must be unique among this account's roles"},
        "permissions": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Permission IDs to grant, from list_user_roles' permissions[].id values",
        },
    },
    "required": ["name", "permissions"],
}

UPDATE_USER_ROLE_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": USER_ID_SCHEMA,
        "access_level": {"type": "string", "description": "New access level to assign"},
    },
    "required": ["user_id", "access_level"],
}

# ---------------------------------------------------------------------------
# Docs MCP bridge
# ---------------------------------------------------------------------------

QUERY_DOCS_SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["search", "filesystem"],
            "description": (
                "'search' — semantic full-text search across all Scanova API docs. "
                "'filesystem' — run a read-only shell command (rg, cat, head, tree, ls, jq…) "
                "on the docs virtual filesystem rooted at /."
            ),
        },
        "query": {
            "type": "string",
            "description": "Search query (for mode='search') or shell command (for mode='filesystem'). "
                           "Filesystem examples: 'cat /api-reference/references/pattern-info.mdx', "
                           "'tree / -L 2', 'rg -il \"pattern\" /'",
        },
    },
    "required": ["mode", "query"],
}

# ---------------------------------------------------------------------------
# QR Code Design
# ---------------------------------------------------------------------------

SET_QR_DESIGN_SCHEMA = {
    "type": "object",
    "description": (
        "Apply a visual design to an existing QR code. "
        "All design fields are optional — omit any you don't want to change. "
        "Call get_qr_design_options first to see all available patterns, eye shapes, and frame IDs."
    ),
    "properties": {
        "qrid": {"type": "string", "description": "Scanova QR code ID to apply the design to"},
        "pattern": {
            "type": "string",
            "description": (
                "Data module pattern shape. Options: Default, Round, RoundedCorners, "
                "RotatedSquares, connectedCircles, Newone1, Newone3, circularDiagonal, "
                "lightCircle, lightSquare, lightRoundedCorners, lightCircleInSquare, "
                "diamond, stars, heart, cross, signalGrid, boltWeave, starBurst, "
                "metroPulse, pulseBars"
            ),
            "default": "Default",
        },
        "start_color": {
            "type": "string",
            "description": "Primary/start color of data modules. Hex #RRGGBB. Default: #000000",
        },
        "end_color": {
            "type": "string",
            "description": "End color for gradient. Omit or same as start_color for solid color.",
        },
        "gradient_style": {
            "type": "string",
            "enum": ["None", "Horizontal", "Vertical", "Diagonal", "Radial"],
            "description": "Gradient direction. Use 'None' for solid color.",
            "default": "None",
        },
        "dot_scale": {
            "type": "integer",
            "minimum": 10,
            "maximum": 100,
            "description": "Module (dot) size scale 10–100. Lower = more spacing between dots.",
        },
        "background_color": {
            "type": "string",
            "description": "QR canvas background color. Hex #RRGGBB, or empty string '' for transparent.",
            "default": "#ffffff",
        },
        "eye_shape": {
            "type": "string",
            "description": (
                "Corner finder pattern shape. Standard: Shape0–Shape10. "
                "Advanced: Shape15, Shape30–Shape59 (various). "
                "Default: Shape4"
            ),
            "default": "Shape4",
        },
        "eye_inner_color": {
            "type": "string",
            "description": "Color of the inner square of the corner eyes. Hex #RRGGBB.",
            "default": "#000000",
        },
        "eye_outer_color": {
            "type": "string",
            "description": "Color of the outer border of the corner eyes. Hex #RRGGBB.",
            "default": "#000000",
        },
        "error_correction": {
            "type": "string",
            "enum": ["L", "M", "Q", "H"],
            "description": "L=7%, M=15% (default), Q=25% (use with logo), H=30% (best for logo overlay)",
            "default": "M",
        },
        "logo_url": {
            "type": "string",
            "description": "HTTPS URL of an image to embed in the QR center. Keep ≤ 30% of QR area.",
        },
        "frame_id": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "Decorative frame ID (1–5). Omit for no frame.",
        },
        "frame_primary_color": {
            "type": "string",
            "description": "Main frame color. Defaults to start_color if omitted.",
        },
        "frame_secondary_color": {
            "type": "string",
            "description": "Secondary frame color for two-tone frames. Null for single-color frames.",
        },
        "frame_text_color": {
            "type": "string",
            "description": "Color of any text inside the frame.",
            "default": "#FFFFFF",
        },
        "frame_bg_color": {
            "type": "string",
            "description": "Background color of the frame area (behind the QR scan region).",
            "default": "#FFFFFF",
        },
        "frame_category": {
            "type": "string",
            "description": "QR category slug for frame style (e.g. 'url', 'document', 'map', 'businessCard').",
            "default": "url",
        },
        "frame_text": {
            "type": "string",
            "description": "Custom text displayed inside the frame (only supported on certain frame_id + frame_category combos).",
        },
        "frame_text_placement": {
            "type": "string",
            "enum": ["center", "top", "bottom", "left", "right", "top-left", "top-right", "bottom-left", "bottom-right"],
            "description": "Placement of the custom frame text.",
            "default": "center",
        },
        "frame_text_font": {
            "type": "string",
            "description": "Font for frame text. Options: Montserrat, Inter, Arial, Roboto, Noto Sans, Times New Roman, Brush Script MT, Raleway, and more.",
            "default": "Montserrat",
        },
        "shape_id": {
            "type": "string",
            "enum": ["1", "2", "3", "4", "5", "6", "7"],
            "description": "Decorative shape container wrapped around the entire QR code. Omit for no shape.",
        },
        "shape_stroke_color": {
            "type": "string",
            "description": "Border/stroke color of the shape container.",
        },
        "shape_bg_color": {
            "type": "string",
            "description": "Fill color inside the shape container.",
            "default": "#FFFFFF",
        },
        "shape_pattern_color": {
            "type": "string",
            "description": "Color of decorative dots/pattern inside the shape.",
            "default": "#000000",
        },
        "shape_stroke_width": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10,
            "description": "Stroke width of the shape border (0–10).",
            "default": 5,
        },
        "shape_margin": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10,
            "description": "Margin between shape border and QR code (0–10).",
            "default": 5,
        },
        "padding": {
            "type": "integer",
            "description": "Quiet zone (empty margin) around the QR code.",
        },
        "accept_risk": {
            "type": "boolean",
            "description": (
                "The design is checked before saving (colour contrast, logo and error correction, and a real "
                "scan test). One that fails isn't saved unless this is true — only set it when the user has seen "
                "the warning and still wants it."
            ),
        },
    },
    "required": ["qrid"],
}

# Same design fields, for a preview that's never saved.
PREVIEW_QR_DESIGN_SCHEMA = {
    "type": "object",
    "description": (
        "Preview a QR design without saving it: returns the design (pattern_info), scan-safety checks, a real "
        "scan test and a rendered image. With qrid, the changes apply over that code's current design; for a new "
        "code pass content (what it will encode, e.g. its URL). Show the preview and checks before set_qr_design."
    ),
    "properties": {
        **{k: v for k, v in SET_QR_DESIGN_SCHEMA["properties"].items() if k not in ("qrid", "accept_risk")},
        "qrid": {"type": "string", "description": "An existing QR code to preview a new design for (optional)."},
        "content": {"type": "string", "description": "What a new QR code will encode, e.g. https://example.com (when there's no qrid)."},
        "render": {"type": "boolean", "description": "Include a rendered image (default true). Apps that draw QR designs themselves can pass false.", "default": True},
        "format": {"type": "string", "enum": ["png", "svg"], "description": "Image format of the preview (default png).", "default": "png"},
    },
}

LIST_CUSTOM_DOMAINS_SCHEMA = {"type": "object", "properties": {}}

# ---------------------------------------------------------------------------
# Additional QR Code Operations
# ---------------------------------------------------------------------------

GET_QR_CATEGORIES_SCHEMA = {
    "type": "object",
    "properties": {
        "view_type": {
            "type": "string",
            "enum": ["all", "recommended", "use_case", "content_type", "favourite"],
            "default": "all",
            "description": "Category view filter",
        }
    },
}

DOWNLOAD_QR_PRINTABLE_SCHEMA = {
    "type": "object",
    "properties": {
        "qrid": {"type": "string", "description": "Scanova QR code ID"},
        "size": {
            "type": "integer",
            "minimum": 300,
            "maximum": 600,
            "default": 600,
            "description": "Output size in pixels",
        },
        "name": {"type": "string", "description": "Filename for the downloaded PDF (optional)"},
    },
    "required": ["qrid"],
}

ATTACH_FORM_TO_QR_SCHEMA = {
    "type": "object",
    "properties": {
        "qrid": {"type": "string", "description": "Scanova QR code ID"},
        "form_id": {"type": ["integer", "string"], "description": "The form to attach: its numeric id, or its form_id (e.g. F1a2b3c)"},
    },
    "required": ["qrid", "form_id"],
}

ATTACH_LEAD_LIST_TO_QR_SCHEMA = {
    "type": "object",
    "properties": {
        "qrid": {"type": "string", "description": "Scanova QR code ID"},
        "lead_list_id": {"type": "integer", "description": "ID of the lead list to attach"},
    },
    "required": ["qrid", "lead_list_id"],
}

# ---------------------------------------------------------------------------
# Original QR schemas (below)
# ---------------------------------------------------------------------------

LIST_QR_CODES_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "page": {
            "type": "integer",
            "minimum": 1,
            "default": 1,
            "description": "Page number for pagination",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "default": 10,
            "description": (
                "Number of results per page, capped at 20. To fetch more "
                "than 20 QR codes, make additional calls incrementing "
                "'page' rather than raising this value."
            ),
        },
        "search": {
            "type": "string",
            "description": "Optional search filter by name",
        },
        "is_page": {
            "type": "boolean",
            "description": (
                "Filter by content type: true = Pages only, false = QR Codes only. "
                "Omit to list everything (QR codes and Pages combined)."
            ),
        },
    },
}
