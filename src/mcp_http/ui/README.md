# Adding a new UI-enabled tool

Runbook per `docs/mcp-ui-architecture.md` Part 16. Follow these steps for every tool that gets a UI resource.

1. Confirm the tool's existing `inputSchema`/`outputSchema` in `mcp_http/schemas.py` / `mcp_http/output_schemas.py` — reuse those field names and shapes in the HTML form/table. Don't invent a second schema for the same tool.
2. Add (or extend) an entry in `mcp_http/ui_resources.py`: a `UIResource(uri, file_path, mime_type, tools=(...))`. One resource can serve multiple related tools (see `folders.html`, `download_qr.html`) — `get_resource_for_tool` resolves any tool name listed in `tools`.
3. Add the tool name(s) to `UI_ENABLED_TOOLS` in `mcp_http/ui_response.py` once the resource is ready to ship. Leaving a tool out of this set is how you stage a resource without exposing it yet (Part 12's per-tool rollout flag).
4. Write the HTML file in this directory:
   - Include the CSP `<meta>` tag every other resource here has (`default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none';`).
   - Copy the `Bridge` adapter block verbatim from an existing resource (e.g. `qr-design.html`) — it feature-detects `window.openai` vs. a generic `postMessage` handshake so the same file works for ChatGPT and Claude/other MCP-UI clients without branching server-side.
   - Render errors from the `{ok:false, status_code, error}` envelope shape directly — don't invent a new error shape (Part 9B).
   - No build step, no bundler, no shared JS import across files — that's a deliberate Phase 1-3/5 scope boundary (see `docs/mcp-ui-architecture.md` §7/Part 8). A shared `ui://scanova/shared/*.js` runtime is reserved for if/when a Preact/Vite build pipeline is introduced.
5. Add tests:
   - `tests/test_ui_resources.py` — the new URI appears in `list_resources()`, and `get_resource_for_tool` resolves for each tool name.
   - `tests/test_ui_response.py` — `attach_ui_metadata` returns the expected `_meta` for the tool once enabled.
   - Re-run `tests/test_sdk_contract.py` unmodified — it validates every `tools/call`/`resources/read` shape against the SDK's own Pydantic models regardless of which tool triggered it.
6. Before merging, check the standing PR guardrail: **does this change alter the `content[0]` `TextContent` shape for any existing tool?** It should always be "no." `attach_ui_metadata` (`ui_response.py`) is the only place `_meta` gets attached — if you find yourself editing `sdk_server.py`'s `call_tool` to add UI behavior, stop; that logic belongs in `ui_response.py` (Part 5A).

## Naming convention

`ui://scanova/<tool-or-entity>.html` — e.g. `ui://scanova/qr-design.html`, `ui://scanova/folders.html`. Filenames use snake_case (`qr_codes_list.html`); URIs use kebab-case (`ui://scanova/qr-codes-list.html`) to match MCP resource URI conventions.

## Current resources

| Resource | Tools |
|---|---|
| `qr-design.html` | `set_qr_design` |
| `create-qr-code.html` | `create_qr_code` |
| `create-folder.html` | `create_folder` |
| `download-qr.html` | `download_qr_code`, `download_qr_printable` |
| `qr-codes-list.html` | `list_qr_codes` |
| `folders.html` | `list_folders`, `update_folder`, `delete_folder`, `move_qr_codes_to_folder`, `unassign_qr_codes_from_folder` |
| `forms.html` | `list_forms`, `retrieve_form`, `update_form`, `delete_form` |
| `lead-lists.html` | `list_lead_lists`, `retrieve_lead_list`, `update_lead_list`, `delete_lead_list` |
| `users.html` | `list_users`, `get_user`, `add_user`, `remove_user`, `list_user_roles`, `update_user_role` |
| `account-stats.html` | `get_account_stats` |
| `analytics-export.html` | `export_analytics`, `export_raw_scans` |

`probe_docs_mcp` and `query_docs` deliberately have no UI resource — see the tool audit in `docs/mcp-ui-architecture.md` Part 11. `get_qr_analytics` also deliberately has no UI resource (2026-08-24) — the dashboard widget was simplified to show account stats only, dropping the query-builder UI that used to trigger it; it now returns plain text.

## Known gap

`analytics-export.html` was built vanilla-JS by explicit instruction, holding off on the Preact/Vite build pipeline `docs/mcp-ui-architecture.md` §7/Phase 4 originally called for. Separately: `output_schemas.py`'s `EXPORT_OUTPUT` documents a `download_url` field that `analytics.py`'s actual `export_analytics`/`export_raw_scans` implementations don't return (they return `data_base64`/`content_type`/`size_bytes`, matching `download_qr_code`) — `analytics-export.html` handles both, but the schema/implementation drift itself is a pre-existing issue worth fixing independently of this UI work.
