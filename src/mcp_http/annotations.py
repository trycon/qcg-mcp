"""Tool annotations (MCP ``ToolAnnotations``) for every tool in registry.py.

Hosts use these to decide what to confirm with the user before calling, so
each tool is classified here explicitly (tests/test_tool_annotations.py fails
for a tool that isn't):

- READ_ONLY: never changes anything.
- ADDITIVE: only adds (creates, invites, attaches) — ``destructiveHint: false``.
- DESTRUCTIVE: may delete, overwrite or switch off something that is live —
  ``destructiveHint: true`` per the spec's definition ("may perform destructive
  updates"; false means "only additive updates"). Includes changing what a
  printed QR code shows, deactivating one, and changing someone's access.

IDEMPOTENT tools can be retried with the same arguments without further effect.
"""

READ_ONLY = frozenset({
    "probe_docs_mcp", "query_docs",
    "list_qr_codes", "retrieve_qr_code", "download_qr_code", "get_qr_categories", "get_qr_category_fields",
    "validate_qr_info", "open_qr_code_creation_form", "get_qr_design_options", "preview_qr_design", "list_custom_domains",
    "list_folders", "list_forms", "retrieve_form", "list_lead_lists", "retrieve_lead_list", "list_tags",
    "get_account_stats", "get_qr_analytics", "get_current_plan",
    "list_users", "get_user", "list_user_roles",
    # more_tools.py
    "list_form_responses", "get_form_analytics", "get_form_question_analytics", "list_form_templates", "list_form_notifications",
    "list_trashed_qr_codes", "get_qr_health", "list_gs1_recalls",
    "get_analytics_overview", "list_analytics_reports",
    "list_available_plans", "get_downgrade_impact", "list_payments", "list_orders", "list_quota_topups",
    "get_activity_feed", "get_activity_summary",
    "get_custom_domain", "list_bulk_operations", "get_bulk_operation_stats", "list_media",
    "get_integrations_overview", "list_webhooks", "list_tracking_sites", "list_tracking_funnels",
    "list_page_templates",
})

ADDITIVE = frozenset({
    "create_qr_code", "create_folder", "create_form", "create_custom_role", "add_user",
    "activate_qr_code", "attach_form_to_qr", "attach_lead_list_to_qr",
    "move_qr_codes_to_folder", "unassign_qr_codes_from_folder", "update_folder",
    # more_tools.py — create_form_notification emails respondents' answers to
    # the address given; resend_user_invitation sends an email.
    "create_form_notification", "restore_qr_codes", "create_gs1_recall",
    "create_analytics_report", "resend_user_invitation",
})

DESTRUCTIVE = frozenset({
    "delete_qr_code", "delete_folder", "delete_form", "delete_lead_list", "remove_user",
    "update_qr_code", "set_qr_design", "deactivate_qr_code",
    "update_form", "update_lead_list", "detach_form_from_qr", "detach_lead_list_from_qr",
    "update_user_role",
    # more_tools.py — replaces all of a code's tags; changes or switches off
    # what scanners of a recalled product see; changes or stops an alert.
    "update_qr_tags", "update_gs1_recall", "update_form_notification",
})

IDEMPOTENT = frozenset({
    "delete_qr_code", "delete_folder", "delete_form", "delete_lead_list", "remove_user",
    "update_qr_code", "set_qr_design", "activate_qr_code", "deactivate_qr_code",
    "update_folder", "update_form", "update_lead_list", "update_user_role",
    "attach_form_to_qr", "attach_lead_list_to_qr", "detach_form_from_qr", "detach_lead_list_from_qr",
    "move_qr_codes_to_folder", "unassign_qr_codes_from_folder",
    "update_qr_tags", "update_gs1_recall", "update_form_notification", "restore_qr_codes",
})


def annotations_for(name: str) -> dict:
    """The annotations for one tool; raises for a tool that hasn't been classified."""
    if name in READ_ONLY:
        return {"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False}
    if name not in ADDITIVE and name not in DESTRUCTIVE:
        raise KeyError(f"tool {name!r} has no annotation class in annotations.py")
    return {
        "readOnlyHint": False,
        "openWorldHint": True,
        "destructiveHint": name in DESTRUCTIVE,
        "idempotentHint": name in IDEMPOTENT,
    }


# Kept for registry.py's call sites; the class tables above are authoritative.
READ_ONLY_TOOL_ANNOTATIONS_JSON = {"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False}
WRITE_TOOL_ANNOTATIONS_JSON = {"readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
DESTRUCTIVE_TOOL_ANNOTATIONS_JSON = {"readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
