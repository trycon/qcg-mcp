"""Toolsets: every tool in registry.py belongs to exactly one group.

Hosts that build assistants on this server (e.g. Scanova AI's product
assistants) can give a specialist whole groups ("forms", "analytics") instead
of picking from 80+ tools one by one, and a tool added later joins its group
without anyone updating the host. Each descriptor in tools/list carries its
group as ``_meta["io.scanova/toolset"]`` (tests/test_toolsets.py fails for a
tool that isn't grouped).
"""

TOOLSET_META_KEY = "io.scanova/toolset"

# key -> (label, description, tools)
TOOLSETS: dict[str, tuple[str, str, frozenset[str]]] = {
    "docs": ("Documentation", "Search Scanova's help documentation.", frozenset({
        "probe_docs_mcp", "query_docs",
    })),
    "qr_codes": ("QR codes", "Find, create, change, switch on/off, download, tag, trash and restore QR codes; check their health.", frozenset({
        "list_qr_codes", "retrieve_qr_code", "download_qr_code", "get_qr_categories", "get_qr_category_fields",
        "validate_qr_info", "open_qr_code_creation_form", "create_qr_code", "update_qr_code",
        "activate_qr_code", "deactivate_qr_code", "delete_qr_code", "list_trashed_qr_codes", "restore_qr_codes",
        "get_qr_health", "list_tags", "update_qr_tags", "list_bulk_operations", "get_bulk_operation_stats",
    })),
    "design": ("Design & domains", "A QR code's look (options, previews with scan-safety checks, saving) and custom domains.", frozenset({
        "get_qr_design_options", "preview_qr_design", "set_qr_design", "list_custom_domains", "get_custom_domain",
    })),
    "folders": ("Folders", "Organise QR codes into folders.", frozenset({
        "list_folders", "create_folder", "update_folder", "delete_folder", "move_qr_codes_to_folder", "unassign_qr_codes_from_folder",
    })),
    "forms": ("Forms", "Forms, their responses, per-question analytics, templates and response alerts; attaching forms to QR codes.", frozenset({
        "list_forms", "retrieve_form", "create_form", "update_form", "delete_form", "attach_form_to_qr", "detach_form_from_qr",
        "list_form_responses", "get_form_analytics", "get_form_question_analytics", "list_form_templates",
        "list_form_notifications", "create_form_notification", "update_form_notification",
    })),
    "leads": ("Lead lists", "Lead lists and attaching them to QR codes.", frozenset({
        "list_lead_lists", "retrieve_lead_list", "update_lead_list", "delete_lead_list", "attach_lead_list_to_qr", "detach_lead_list_from_qr",
    })),
    "analytics": ("Analytics & activity", "Scans and account statistics, reports, and the account's activity feed.", frozenset({
        "get_account_stats", "get_qr_analytics", "get_analytics_overview", "list_analytics_reports", "create_analytics_report",
        "get_activity_feed", "get_activity_summary",
    })),
    "billing": ("Plan & billing", "The current plan, other plans and what a downgrade would affect, payments, orders and top-ups.", frozenset({
        "get_current_plan", "list_available_plans", "get_downgrade_impact", "list_payments", "list_orders", "list_quota_topups",
    })),
    "team": ("Team & roles", "Users, roles and invitations.", frozenset({
        "list_users", "get_user", "add_user", "remove_user", "update_user_role", "list_user_roles", "create_custom_role", "resend_user_invitation",
    })),
    "gs1": ("GS1 recalls", "Product recalls on GS1 QR codes.", frozenset({
        "list_gs1_recalls", "create_gs1_recall", "update_gs1_recall",
    })),
    "integrations": ("Integrations & tracking", "Connected integrations, webhooks, tracking sites and funnels.", frozenset({
        "get_integrations_overview", "list_webhooks", "list_tracking_sites", "list_tracking_funnels",
    })),
    "pages": ("Pages & media", "Landing-page templates and the media library.", frozenset({
        "list_page_templates", "list_media",
    })),
}

_BY_TOOL = {tool: key for key, (_, _, tools) in TOOLSETS.items() for tool in tools}


def toolset_for(tool_name: str) -> str:
    """The group a tool belongs to. Raises KeyError for an ungrouped tool."""
    return _BY_TOOL[tool_name]
