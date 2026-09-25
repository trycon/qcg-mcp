"""
UI response builder — the seam between a normalized tool result and the
final result built by sdk_server.call_tool.

Owns: the decision of whether a tool call should carry UI metadata, and the
shape of that metadata. Never touches the normalized envelope itself.
See docs/mcp-ui-architecture.md Part 4A (layer ownership) and Part 5A
(this abstraction, with rationale).

Multi-client support: rather than picking one UI convention, this emits
BOTH the OpenAI Apps SDK convention (_meta["openai/outputTemplate"]) and a
generic MCP-UI-style convention (_meta["ui"]["resourceUri"]) pointing at the
same resource. Per MCP Core, _meta is an arbitrary dict and unknown keys
must be ignored by conformant clients — so a client that only understands
one convention simply ignores the other key. This avoids branching on
client identity server-side (which Part 6 of the architecture doc found
has no reliable signal anyway).
"""

from config import UI_ELEMENTS_ENABLED
from mcp_http.ui_resources import get_resource_for_tool

# Per-tool enablement. Add tool names here as each subsequent phase's UI
# resource ships (see roadmap in docs/mcp-ui-architecture.md Part 16 /
# Part 11 priority column). Phase 1: set_qr_design. Phase 2: creation tools.
# Phase 3: download/media tools. Phase 5: remaining CRUD tools (folders,
# forms, lead lists, users) plus list_qr_codes. Phase 4: analytics
# dashboard (vanilla JS + hand-rolled inline-SVG bar chart, no Preact/Vite —
# a deliberate deviation from docs/mcp-ui-architecture.md's Phase 4
# recommendation to introduce a build pipeline; revisit if/when this
# dashboard's component needs outgrow hand-written JS).
UI_ENABLED_TOOLS = frozenset({
    "get_qr_design_options",
    "set_qr_design",
    "create_qr_code",
    "open_qr_code_creation_form",
    "download_qr_code",
    # download_qr_printable removed for now (2026-08-21) — tool not registered.
    # list_qr_codes deliberately excluded: tested and working fine as plain
    # text — the model can decide how to present a QR list, no widget
    # needed. The resource file (qr_codes_list.html) and its registry entry
    # in ui_resources.py are kept as-is; only the UI-enablement trigger is
    # removed here, so re-adding "list_qr_codes" above fully restores it.
    #
    # All folder-related tools deliberately excluded (2026-08-24): create_folder,
    # list_folders, update_folder, delete_folder, move_qr_codes_to_folder,
    # unassign_qr_codes_from_folder — tested and confirmed working fine as
    # plain text, for both folder types (qr and page). create_folder.html /
    # folders.html and their ui_resources.py registry entries are kept as-is;
    # only the UI-enablement trigger is removed here.
    # Forms deliberately excluded (2026-08-24): list_forms, retrieve_form,
    # update_form, delete_form — tested and confirmed working fine as plain
    # text. forms.html and its ui_resources.py registry entry are kept
    # as-is; only the UI-enablement trigger is removed here.
    #
    # Lead Lists deliberately excluded (2026-08-24): list_lead_lists,
    # retrieve_lead_list, update_lead_list, delete_lead_list — tested and
    # confirmed working fine as plain text. lead-lists.html and its
    # ui_resources.py registry entry are kept as-is; only the
    # UI-enablement trigger is removed here.
    #
    # Team & Access Management deliberately excluded (2026-08-24): list_users,
    # get_user, add_user, remove_user, list_user_roles, update_user_role —
    # tested and confirmed working fine as plain text. users.html and its
    # ui_resources.py registry entry are kept as-is; only the
    # UI-enablement trigger is removed here.
    "get_account_stats",
    # get_qr_analytics deliberately excluded (2026-08-24): the dashboard
    # widget was simplified to show account stats only, dropping the
    # query-builder UI that used to trigger this tool. get_qr_analytics
    # now returns plain text. No widget currently covers it — re-add a
    # dedicated resource/entry here if a UI for it is built again.
    #
    # export_analytics / export_raw_scans removed for now (2026-08-24) —
    # tools no longer registered (see registry.py/dispatcher.py). Kept out
    # of this set accordingly; analytics-export.html and its
    # ui_resources.py registry entry are left in place for an easy
    # re-enable later.
})

OPENAI_OUTPUT_TEMPLATE_META_KEY = "openai/outputTemplate"

# Tools where whether to show the UI depends on the *result*, not just the
# tool name — e.g. create_qr_code already has everything it needs conveyed
# in the text confirmation on success, so its form widget should only
# appear when the call failed (letting the user fix and retry via the UI).
# Keyed by tool name -> predicate(envelope) -> True means "show the UI".
CONDITIONAL_UI_RULES = {
    "create_qr_code": lambda envelope: envelope.get("ok") is False,
}


def _resource_meta(tool_name: str) -> dict | None:
    """Shared {_meta} shape linking a tool to its UI resource, or None if
    UI Elements are disabled, the tool isn't UI-enabled, or it has no
    registered resource."""
    if not UI_ELEMENTS_ENABLED or tool_name not in UI_ENABLED_TOOLS:
        return None
    resource = get_resource_for_tool(tool_name)
    if resource is None:
        return None
    return {
        OPENAI_OUTPUT_TEMPLATE_META_KEY: resource.versioned_uri,
        "ui": {"resourceUri": resource.versioned_uri},
    }


def attach_ui_metadata(tool_name: str, envelope: dict) -> dict:
    """
    Given a tool name and its already-normalized envelope, return
    {"envelope": envelope, "meta": <_meta dict or None>}.

    Never modifies `envelope` — purely additive. Returns meta=None when UI
    Elements are globally disabled, the tool isn't UI-enabled, no resource
    is registered for it, or (for tools in CONDITIONAL_UI_RULES) the result
    doesn't meet that tool's condition for showing the UI.
    """
    meta = _resource_meta(tool_name)
    if meta is None:
        return {"envelope": envelope, "meta": None}
    rule = CONDITIONAL_UI_RULES.get(tool_name)
    if rule is not None and not rule(envelope):
        return {"envelope": envelope, "meta": None}
    return {"envelope": envelope, "meta": meta}


def tool_descriptor_meta(tool_name: str) -> dict | None:
    """
    The `_meta` block a tool's `tools/list` descriptor must carry so a host
    (e.g. ChatGPT) can discover its associated UI resource up front — hosts
    read this at listing time and only call resources/read for tools that
    declare it here; declaring it solely on the tools/call result (as
    attach_ui_metadata does) is not sufficient for discovery.
    """
    return _resource_meta(tool_name)
