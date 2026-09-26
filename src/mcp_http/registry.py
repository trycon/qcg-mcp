"""MCP tools/list definitions for the HTTP JSON-RPC endpoint."""

from mcp_http.annotations import (
    annotations_for,
    DESTRUCTIVE_TOOL_ANNOTATIONS_JSON,
    READ_ONLY_TOOL_ANNOTATIONS_JSON,
    WRITE_TOOL_ANNOTATIONS_JSON,
)
from mcp_http.more_tools import MORE_TOOLS
from mcp_http.output_schemas import TOOL_OUTPUT_SCHEMAS, tool_output_schema
from mcp_http.ui_response import tool_descriptor_meta
from mcp_http.schemas import (
    # Docs bridge
    QUERY_DOCS_SCHEMA,
    # QR Code Creation & Validation
    CREATE_QR_PARAMS_SCHEMA,
    GET_QR_CATEGORIES_SCHEMA,
    GET_QR_CATEGORY_FIELDS_SCHEMA,
    OPEN_QR_CODE_CREATION_FORM_SCHEMA,
    VALIDATE_QR_INFO_SCHEMA,
    # QR Code Design
    SET_QR_DESIGN_SCHEMA,
    PREVIEW_QR_DESIGN_SCHEMA,
    LIST_CUSTOM_DOMAINS_SCHEMA,
    # QR Code Lifecycle & Retrieval / Export
    DOWNLOAD_QR_PARAMS_SCHEMA,
    LIST_QR_CODES_INPUT_SCHEMA,
    QRID_SCHEMA,
    UPDATE_QR_PARAMS_SCHEMA,
    # Folders
    CREATE_FOLDER_SCHEMA,
    DELETE_FOLDER_SCHEMA,
    FOLDER_ID_SCHEMA,
    LIST_FOLDERS_SCHEMA,
    MOVE_QR_TO_FOLDER_SCHEMA,
    UNASSIGN_QR_FROM_FOLDER_SCHEMA,
    UPDATE_FOLDER_SCHEMA,
    # Tags
    LIST_TAGS_SCHEMA,
    # Forms
    ATTACH_FORM_TO_QR_SCHEMA,
    CREATE_FORM_SCHEMA,
    FORM_ID_SCHEMA,
    LIST_FORMS_SCHEMA,
    UPDATE_FORM_SCHEMA,
    # Lead Lists
    ATTACH_LEAD_LIST_TO_QR_SCHEMA,
    LEAD_LIST_ID_SCHEMA,
    LIST_LEAD_LISTS_SCHEMA,
    UPDATE_LEAD_LIST_SCHEMA,
    # Analytics
    ACCOUNT_STATS_SCHEMA,
    GET_QR_ANALYTICS_SCHEMA,
    # Account & Billing
    GET_CURRENT_PLAN_SCHEMA,
    # Users
    ADD_USER_SCHEMA,
    CREATE_CUSTOM_ROLE_SCHEMA,
    UPDATE_USER_ROLE_SCHEMA,
    USER_ID_SCHEMA,
)


def _tool(name, title, description, annotations, input_schema):
    # The per-tool classification in annotations.py is authoritative; the
    # argument only documents intent at the call site.
    descriptor = {
        "name": name,
        "title": title,
        "description": description,
        "annotations": annotations_for(name),
        "inputSchema": input_schema,
    }
    output_schema = TOOL_OUTPUT_SCHEMAS.get(name)
    if output_schema:
        descriptor["outputSchema"] = tool_output_schema(output_schema)
    meta = tool_descriptor_meta(name)
    if meta:
        descriptor["_meta"] = meta
    return descriptor


def list_mcp_tools():
    """Return tool descriptors for MCP ``tools/list`` responses."""
    return [
        # ------------------------------------------------------------------ #
        # Docs MCP Bridge (infrastructure utility, not a business domain)
        # ------------------------------------------------------------------ #
        _tool(
            "probe_docs_mcp",
            "Probe Scanova docs MCP",
            "Check connectivity to the Scanova docs MCP server and list its available tools",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {}},
        ),
        _tool(
            "query_docs",
            "Query Scanova API documentation",
            (
                "Bridge to the live Scanova docs MCP server. "
                "mode='search' runs a semantic search across all docs. "
                "mode='filesystem' runs a read-only shell command (cat, head, rg, tree, jq…) "
                "on the docs virtual filesystem — use this to read specific pages like "
                "/api-reference/references/pattern-info.mdx or /api-reference/references/category-list.mdx"
            ),
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            QUERY_DOCS_SCHEMA,
        ),
        # ------------------------------------------------------------------ #
        # QR Code Creation & Validation
        # ------------------------------------------------------------------ #
        _tool(
            "get_qr_categories",
            "Get QR code categories",
            "List available QR code categories (URL, vCard, WiFi, Document, Social Media, etc.)",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            GET_QR_CATEGORIES_SCHEMA,
        ),
        _tool(
            "get_qr_category_fields",
            "Get QR category field reference",
            (
                "Return the required/optional `info` JSON field reference for a QR code category "
                "(or all categories if none is given) — static reference data, no API call. "
                "Call this before create_qr_code/update_qr_code so the `info` payload matches the "
                "shape the category expects. Use validate_qr_info afterward to confirm a specific payload."
            ),
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            GET_QR_CATEGORY_FIELDS_SCHEMA,
        ),
        _tool(
            "validate_qr_info",
            "Validate QR code info payload",
            (
                "Validate a category + info JSON payload before calling create_qr_code or update_qr_code — "
                "catches malformed JSON, missing required fields, and invalid URLs/emails ahead of time. "
                "Call get_qr_category_fields first if you're unsure of the expected shape for a category."
            ),
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            VALIDATE_QR_INFO_SCHEMA,
        ),
        _tool(
            "create_qr_code",
            "Create QR code",
            (
                "Create a new QR code. Only call this when you already have all required fields "
                "(name, category, qr_type, info) explicitly stated or clearly inferable from the "
                "conversation — never invent or guess placeholder values. If the user asked to "
                "create a QR code but hasn't given enough detail, call open_qr_code_creation_form "
                "instead so they can fill in a form (do not call this tool with guesses just to "
                "show the form — on success this tool does NOT show any UI, only a text confirmation; "
                "the form only appears automatically if this call fails, pre-filled with what was "
                "attempted, so the user can fix and retry). "
                "For categories you're unsure about, call get_qr_category_fields first to see the "
                "expected `info` shape, and optionally validate_qr_info to check the payload before creating."
            ),
            WRITE_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"params": CREATE_QR_PARAMS_SCHEMA}, "required": ["params"]},
        ),
        _tool(
            "open_qr_code_creation_form",
            "Open QR code creation form",
            (
                "Show an interactive form for creating a QR code. Use this when the user wants to "
                "create a QR code but hasn't provided enough information (missing or ambiguous "
                "name/category/content) — do not call create_qr_code with guessed values in this case. "
                "Any fields already known can be passed here to pre-fill the form."
            ),
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            OPEN_QR_CODE_CREATION_FORM_SCHEMA,
        ),
        # ------------------------------------------------------------------ #
        # QR Code Design
        # ------------------------------------------------------------------ #
        _tool(
            "get_qr_design_options",
            "Get QR code design options",
            (
                "Return the full catalog of available QR design options: all data pattern names, "
                "gradient styles, eye shape codes, frame IDs, error correction levels, fonts, "
                "and design tips. Use this before calling set_qr_design so users can see and "
                "choose from available options without writing any JSON."
            ),
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {}},
        ),
        _tool(
            "set_qr_design",
            "Set QR code design",
            (
                "Apply a visual design to an existing QR code using human-friendly named parameters. "
                "Only the fields you specify are changed — all other design settings (eye shape, pattern, "
                "colors, frame, etc.) are automatically preserved from the current design. "
                "Internally fetches the existing design and merges your changes on top. "
                "Call get_qr_design_options first to show users available patterns, eye shapes, and frames."
            ),
            WRITE_TOOL_ANNOTATIONS_JSON,
            SET_QR_DESIGN_SCHEMA,
        ),
        _tool(
            "preview_qr_design",
            "Preview a QR design",
            (
                "Preview a QR code design without saving it: the design, scan-safety checks (colour contrast, "
                "logo and error correction), a real scan test, and a rendered image. Works for an existing code "
                "(qrid) or a new one (content). Use it to show options and changes before set_qr_design."
            ),
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            PREVIEW_QR_DESIGN_SCHEMA,
        ),
        _tool(
            "list_custom_domains",
            "List custom domains",
            "List the account's custom short-link domains (e.g. qr.example.com), which is the default, and whether each is verified.",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            LIST_CUSTOM_DOMAINS_SCHEMA,
        ),
        # ------------------------------------------------------------------ #
        # QR Code Lifecycle & Retrieval
        # ------------------------------------------------------------------ #
        _tool(
            "list_qr_codes",
            "List QR codes",
            (
                "List QR codes and/or Pages in the account. By default returns all items (QR codes + Pages combined). "
                "Use is_page=false to list only QR Codes, or is_page=true to list only Pages. "
                "Use the count field from the response for accurate totals — do not infer counts from page size alone."
            ),
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            LIST_QR_CODES_INPUT_SCHEMA,
        ),
        _tool(
            "retrieve_qr_code",
            "Retrieve QR code details",
            "Get details of a specific QR code",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"qrid": QRID_SCHEMA}, "required": ["qrid"]},
        ),
        _tool(
            "update_qr_code",
            "Update QR code",
            "Update an existing QR code",
            WRITE_TOOL_ANNOTATIONS_JSON,
            {
                "type": "object",
                "properties": {"qrid": QRID_SCHEMA, "params": UPDATE_QR_PARAMS_SCHEMA},
                "required": ["qrid", "params"],
            },
        ),
        _tool(
            "activate_qr_code",
            "Activate QR code",
            "Activate a QR code",
            WRITE_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"qrid": QRID_SCHEMA}, "required": ["qrid"]},
        ),
        _tool(
            "deactivate_qr_code",
            "Deactivate QR code",
            "Deactivate a QR code",
            WRITE_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"qrid": QRID_SCHEMA}, "required": ["qrid"]},
        ),
        _tool(
            "delete_qr_code",
            "Delete QR code",
            "Permanently delete a QR code",
            DESTRUCTIVE_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"qrid": QRID_SCHEMA}, "required": ["qrid"]},
        ),
        # ------------------------------------------------------------------ #
        # QR Code Export & Download
        # ------------------------------------------------------------------ #
        _tool(
            "download_qr_code",
            "Download QR code image",
            "Download QR code image in PNG, JPG, or PDF format",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            {
                "type": "object",
                "properties": {"qrid": QRID_SCHEMA, "params": DOWNLOAD_QR_PARAMS_SCHEMA},
                "required": ["qrid"],
            },
        ),
        # download_qr_printable removed for now (2026-08-21) — not registered
        # as a tool, but the underlying qrcode.download_qr_printable function
        # and DOWNLOAD_QR_PRINTABLE_SCHEMA/_OUTPUT are left in place for an
        # easy re-enable later.
        # ------------------------------------------------------------------ #
        # Organization: Folders
        # ------------------------------------------------------------------ #
        _tool(
            "create_folder",
            "Create folder",
            "Create a new folder to organize QR codes or pages",
            WRITE_TOOL_ANNOTATIONS_JSON,
            CREATE_FOLDER_SCHEMA,
        ),
        _tool(
            "list_folders",
            "List folders",
            "List all folders of a given type (qr or page)",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            LIST_FOLDERS_SCHEMA,
        ),
        _tool(
            "update_folder",
            "Rename folder",
            "Rename an existing folder",
            WRITE_TOOL_ANNOTATIONS_JSON,
            UPDATE_FOLDER_SCHEMA,
        ),
        _tool(
            "delete_folder",
            "Delete folder",
            (
                "Delete a folder. IMPORTANT: Before calling this tool, ask the user which action "
                "to take for QR codes inside the folder: (1) move to Uncategorized "
                "(move_to_uncategorized=true, delete_permanently=false) or (2) permanently delete "
                "them along with the folder (delete_permanently=true, move_to_uncategorized=false). "
                "Do not proceed without explicit user confirmation of the desired behavior."
            ),
            DESTRUCTIVE_TOOL_ANNOTATIONS_JSON,
            DELETE_FOLDER_SCHEMA,
        ),
        _tool(
            "move_qr_codes_to_folder",
            "Move QR codes to folder",
            "Move multiple QR codes into a folder",
            WRITE_TOOL_ANNOTATIONS_JSON,
            MOVE_QR_TO_FOLDER_SCHEMA,
        ),
        _tool(
            "unassign_qr_codes_from_folder",
            "Unassign QR codes from folder",
            "Remove multiple QR codes from a folder (moves them to uncategorized)",
            WRITE_TOOL_ANNOTATIONS_JSON,
            UNASSIGN_QR_FROM_FOLDER_SCHEMA,
        ),
        # ------------------------------------------------------------------ #
        # Organization: Tags
        # ------------------------------------------------------------------ #
        _tool(
            "list_tags",
            "List tags",
            (
                "List tags attached to (or assignable against) the account's QR codes. "
                "Read-only — tags are created implicitly when attached to a QR code, not through a standalone call."
            ),
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            LIST_TAGS_SCHEMA,
        ),
        # ------------------------------------------------------------------ #
        # Forms
        # ------------------------------------------------------------------ #
        _tool(
            "list_forms",
            "List forms",
            "List all lead capture forms, optionally filtered by active status",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            LIST_FORMS_SCHEMA,
        ),
        _tool(
            "retrieve_form",
            "Retrieve form details",
            "Get detailed information about a specific form including its configuration",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"form_id": FORM_ID_SCHEMA}, "required": ["form_id"]},
        ),
        _tool(
            "create_form",
            "Create form",
            (
                "Create a new lead-capture form from a title and its questions (each with an answer type — "
                "short answer, email, multiple choice, rating… — and options for choice questions). "
                "Optionally pass qr_id to attach it to a dynamic QR code immediately, or use attach_form_to_qr afterward. "
                "list_form_templates has ready-made forms to start from."
            ),
            WRITE_TOOL_ANNOTATIONS_JSON,
            CREATE_FORM_SCHEMA,
        ),
        _tool(
            "update_form",
            "Update form",
            "Update a form's name or active status",
            WRITE_TOOL_ANNOTATIONS_JSON,
            UPDATE_FORM_SCHEMA,
        ),
        _tool(
            "delete_form",
            "Delete form",
            "Permanently delete a form",
            DESTRUCTIVE_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"form_id": FORM_ID_SCHEMA}, "required": ["form_id"]},
        ),
        _tool(
            "attach_form_to_qr",
            "Attach form to QR code",
            "Attach a lead capture form to a QR code",
            WRITE_TOOL_ANNOTATIONS_JSON,
            ATTACH_FORM_TO_QR_SCHEMA,
        ),
        _tool(
            "detach_form_from_qr",
            "Detach form from QR code",
            "Remove the lead capture form from a QR code",
            WRITE_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"qrid": QRID_SCHEMA}, "required": ["qrid"]},
        ),
        # ------------------------------------------------------------------ #
        # Lead Lists (legacy — superseded by Forms; maintenance only)
        # ------------------------------------------------------------------ #
        _tool(
            "list_lead_lists",
            "List lead lists",
            "List all lead lists, optionally filtered by active status. Legacy feature — Forms is the recommended lead-capture tool going forward.",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            LIST_LEAD_LISTS_SCHEMA,
        ),
        _tool(
            "retrieve_lead_list",
            "Retrieve lead list details",
            "Get detailed information about a specific lead list including webhook config",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            {
                "type": "object",
                "properties": {"lead_list_id": LEAD_LIST_ID_SCHEMA},
                "required": ["lead_list_id"],
            },
        ),
        _tool(
            "update_lead_list",
            "Update lead list",
            "Update a lead list's name or active status",
            WRITE_TOOL_ANNOTATIONS_JSON,
            UPDATE_LEAD_LIST_SCHEMA,
        ),
        _tool(
            "delete_lead_list",
            "Delete lead list",
            "Permanently delete a lead list",
            DESTRUCTIVE_TOOL_ANNOTATIONS_JSON,
            {
                "type": "object",
                "properties": {"lead_list_id": LEAD_LIST_ID_SCHEMA},
                "required": ["lead_list_id"],
            },
        ),
        _tool(
            "attach_lead_list_to_qr",
            "Attach lead list to QR code",
            "Attach a lead list to a QR code for lead capture",
            WRITE_TOOL_ANNOTATIONS_JSON,
            ATTACH_LEAD_LIST_TO_QR_SCHEMA,
        ),
        _tool(
            "detach_lead_list_from_qr",
            "Detach lead list from QR code",
            "Remove the lead list from a QR code",
            WRITE_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"qrid": QRID_SCHEMA}, "required": ["qrid"]},
        ),
        # ------------------------------------------------------------------ #
        # Analytics & Reporting
        # ------------------------------------------------------------------ #
        _tool(
            "get_account_stats",
            "Get account statistics",
            "Retrieve account-level usage counters (total QR codes, scans, users, etc.)",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            ACCOUNT_STATS_SCHEMA,
        ),
        _tool(
            "get_qr_analytics",
            "Get QR code analytics",
            "Retrieve QR code performance metrics broken down by device, geography, date, etc.",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            GET_QR_ANALYTICS_SCHEMA,
        ),
        # export_analytics / export_raw_scans removed for now (2026-08-24) —
        # not registered as tools, but the underlying analytics.py functions
        # and their EXPORT_ANALYTICS_SCHEMA/EXPORT_RAW_SCANS_SCHEMA/output
        # schemas are left in place for an easy re-enable later.
        # ------------------------------------------------------------------ #
        # Account & Billing
        # ------------------------------------------------------------------ #
        _tool(
            "get_current_plan",
            "Get current plan",
            "Retrieve the account's active subscription plan — expiry, billing state, and the full quota list it grants",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            GET_CURRENT_PLAN_SCHEMA,
        ),
        # ------------------------------------------------------------------ #
        # Team & Access Management
        # ------------------------------------------------------------------ #
        _tool(
            "list_users",
            "List users",
            "List all users in the account",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {}},
        ),
        _tool(
            "get_user",
            "Get user details",
            "Get details of a specific user",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"user_id": USER_ID_SCHEMA}, "required": ["user_id"]},
        ),
        _tool(
            "add_user",
            "Add user",
            "Invite a new user to the account by email",
            WRITE_TOOL_ANNOTATIONS_JSON,
            ADD_USER_SCHEMA,
        ),
        _tool(
            "remove_user",
            "Remove user",
            "Remove a user from the account",
            DESTRUCTIVE_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {"user_id": USER_ID_SCHEMA}, "required": ["user_id"]},
        ),
        _tool(
            "list_user_roles",
            "List user roles",
            "List all available user roles that can be assigned",
            READ_ONLY_TOOL_ANNOTATIONS_JSON,
            {"type": "object", "properties": {}},
        ),
        _tool(
            "create_custom_role",
            "Create custom role",
            (
                "Create a custom role/access-level (requires a dedicated plan quota — a 403 means the "
                "plan doesn't include it). Call list_user_roles first to see existing roles and valid permission IDs."
            ),
            WRITE_TOOL_ANNOTATIONS_JSON,
            CREATE_CUSTOM_ROLE_SCHEMA,
        ),
        _tool(
            "update_user_role",
            "Update user role",
            "Change the role of an existing user",
            WRITE_TOOL_ANNOTATIONS_JSON,
            UPDATE_USER_ROLE_SCHEMA,
        ),
        # ------------------------------------------------------------------ #
        # One-endpoint tools (forms, trash, health, GS1 recalls, reports,
        # billing history, activity, integrations…): declared in more_tools.py
        # ------------------------------------------------------------------ #
        *(_tool(t.name, t.title, t.description, None, t.input_schema) for t in MORE_TOOLS),
    ]


HTTP_AUTH_STUB_RESPONSE = {
    "error": "Please use the HTTP MCP endpoint for API key authentication",
}
