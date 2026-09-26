# Scanova MCP Server

A Model Context Protocol (MCP) server for managing your Scanova QR code platform using the Scanova API. This server provides tools for QR code creation, design, and lifecycle management; folder organization; lead-capture forms and lead lists; analytics exports; and account user administration, through MCP-compatible IDEs like Cursor, VS Code, and Claude Desktop.

## Features

- ✅ **QR Codes**: Create, list, retrieve, update, activate/deactivate, and delete QR codes; download them as PNG/JPG/PDF/SVG/EPS or as print-ready PDFs; and browse QR categories
- ✅ **QR Design**: Customize QR code visuals — patterns, eye shapes, frames, gradients, and error correction
- ✅ **Folders**: Create, list, update, and delete folders, and move or unassign QR codes between them
- ✅ **Forms & Lead Capture**: List, retrieve, update, and delete lead-capture forms and lead lists, and attach or detach either from a QR code
- ✅ **Analytics**: Pull account-level usage stats and per-QR performance metrics, and export analytics reports or raw scan logs
- ✅ **Account Administration**: List users and roles, invite or remove users, and update user role assignments
- ✅ **Documentation Bridge**: Query Scanova's docs via a live bridge to the Scanova docs MCP server

## Prerequisites

- Scanova API key (get one from [https://app.scanova.io/](https://app.scanova.io/))
- MCP-compatible IDE (Cursor, VS Code, Claude Desktop, etc.)

## Quick Setup

### Step 1: Get Your Scanova API Key
1. Visit [https://app.scanova.io/](https://app.scanova.io/)
2. Sign up or log in to your account
3. Navigate to API settings [https://app.scanova.io/settings/api] and generate your API key.

### Step 2: Configure Your IDE

Add the following configuration to your IDE's MCP settings:

**For Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "scanova-mcp": {
      "transport": "http",
      "url": "https://mcp.scanova.io/mcp",
      "headers": {
        "Authorization": "YOUR_SCANOVA_API_KEY_HERE"
      }
    }
  }
}
```

**For VS Code** (`~/.vscode/mcp.json`):
```json
{
  "mcpServers": {
    "scanova-mcp": {
      "transport": "http", 
      "url": "https://mcp.scanova.io/mcp",
      "headers": {
        "Authorization": "YOUR_SCANOVA_API_KEY_HERE"
      }
    }
  }
}
```

**For Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "scanova-mcp": {
      "transport": "http",
      "url": "https://mcp.scanova.io/mcp", 
      "headers": {
        "Authorization": "YOUR_SCANOVA_API_KEY_HERE"
      }
    }
  }
}
```

## Tools

81 tools. **Type** is the tool's MCP annotation: read-only, write (only adds), or destructive (can change or switch off something live — hosts should confirm first).

### Documentation

| Tool | Type | Description |
|---|---|---|
| `probe_docs_mcp` | Read-only | Check connectivity to the Scanova docs MCP server and list its available tools |
| `query_docs` | Read-only | Bridge to the live Scanova docs MCP server |

### Categories & validation

| Tool | Type | Description |
|---|---|---|
| `get_qr_categories` | Read-only | List available QR code categories (URL, vCard, WiFi, Document, Social Media, etc.) |
| `get_qr_category_fields` | Read-only | Return the required/optional `info` JSON field reference for a QR code category (or all categories if none is given) — static reference data, no API call |
| `validate_qr_info` | Read-only | Validate a category + info JSON payload before calling create_qr_code or update_qr_code — catches malformed JSON, missing required fields, and invalid URLs/emails ahead of time |

### QR code design

| Tool | Type | Description |
|---|---|---|
| `get_qr_design_options` | Read-only | Return the full catalog of available QR design options: all data pattern names, gradient styles, eye shape codes, frame IDs, error correction levels, fonts, and design tips |
| `preview_qr_design` | Read-only | Preview a QR code design without saving it: the design, scan-safety checks (colour contrast, logo and error correction), a real scan test, and a rendered image |
| `set_qr_design` | Destructive | Apply a visual design to an existing QR code using human-friendly named parameters |
| `list_custom_domains` | Read-only | List the account's custom short-link domains (e.g |

### QR codes

| Tool | Type | Description |
|---|---|---|
| `create_qr_code` | Write | Create a new QR code |
| `open_qr_code_creation_form` | Read-only | Show an interactive form for creating a QR code |
| `list_qr_codes` | Read-only | List QR codes and/or Pages in the account |
| `retrieve_qr_code` | Read-only | Get details of a specific QR code |
| `update_qr_code` | Destructive | Update an existing QR code |
| `activate_qr_code` | Write | Activate a QR code |
| `deactivate_qr_code` | Destructive | Deactivate a QR code |
| `delete_qr_code` | Destructive | Permanently delete a QR code |
| `download_qr_code` | Read-only | Download QR code image in PNG, JPG, or PDF format |
| `list_tags` | Read-only | List tags attached to (or assignable against) the account's QR codes |
| `list_trashed_qr_codes` | Read-only | List QR codes in the trash (deleted but restorable), with when each was deleted and its scan count |
| `restore_qr_codes` | Write | Restore QR codes from the trash so they work again |
| `get_qr_health` | Read-only | The account's QR code health check: problems that stop codes working as intended — e.g |
| `update_qr_tags` | Destructive | Replace a QR code's tags with the ones given (an empty list removes them all) |
| `list_gs1_recalls` | Read-only | List the account's GS1 batch/lot recall notices: which GTIN and batch, the message shown to people who scan an affected product, and whether each is active |
| `create_gs1_recall` | Write | Recall a product batch: everyone who scans a GS1 QR code for this GTIN and batch/lot sees the message instead |
| `update_gs1_recall` | Destructive | Change a recall notice's message, or set is_active false once the recall is over (its history is kept) |

### Folders

| Tool | Type | Description |
|---|---|---|
| `create_folder` | Write | Create a new folder to organize QR codes or pages |
| `list_folders` | Read-only | List all folders of a given type (qr or page) |
| `update_folder` | Write | Rename an existing folder |
| `delete_folder` | Destructive | Delete a folder |
| `move_qr_codes_to_folder` | Write | Move multiple QR codes into a folder |
| `unassign_qr_codes_from_folder` | Write | Remove multiple QR codes from a folder (moves them to uncategorized) |

### Forms

| Tool | Type | Description |
|---|---|---|
| `list_forms` | Read-only | List all lead capture forms, optionally filtered by active status |
| `retrieve_form` | Read-only | Get detailed information about a specific form including its configuration |
| `create_form` | Write | Create a new lead-capture form from a title and its questions (each with an answer type — short answer, email, multiple choice, rating… — and options for choice questions) |
| `update_form` | Destructive | Update a form's name or active status |
| `delete_form` | Destructive | Permanently delete a form |
| `attach_form_to_qr` | Write | Attach a lead capture form to a QR code |
| `detach_form_from_qr` | Destructive | Remove the lead capture form from a QR code |
| `list_form_responses` | Read-only | List the responses a form has collected, newest first: each with its answers, when it came in and which QR code it came from |
| `get_form_analytics` | Read-only | A form's performance: total responses and skips (with the change against the previous period), responses and skips by date, and responses by source QR code |
| `list_form_templates` | Read-only | List ready-made form templates (name, description and their blocks), to start a new form from with create_form |
| `list_form_notifications` | Read-only | List the email alerts set up for new form responses: who they go to, how often, which forms, and whether each is on |
| `create_form_notification` | Write | Email someone when forms get new responses — for every response, or as a daily, weekly or monthly digest |
| `update_form_notification` | Destructive | Change a form alert: its recipient, frequency or forms, or switch it on or off |

### Lead lists (legacy)

| Tool | Type | Description |
|---|---|---|
| `list_lead_lists` | Read-only | List all lead lists, optionally filtered by active status |
| `retrieve_lead_list` | Read-only | Get detailed information about a specific lead list including webhook config |
| `update_lead_list` | Destructive | Update a lead list's name or active status |
| `delete_lead_list` | Destructive | Permanently delete a lead list |
| `attach_lead_list_to_qr` | Write | Attach a lead list to a QR code for lead capture |
| `detach_lead_list_from_qr` | Destructive | Remove the lead list from a QR code |

### Analytics

| Tool | Type | Description |
|---|---|---|
| `get_account_stats` | Read-only | Retrieve account-level usage counters (total QR codes, scans, users, etc.) |
| `get_qr_analytics` | Read-only | Retrieve QR code performance metrics broken down by device, geography, date, etc |
| `get_analytics_overview` | Read-only | The account's scan overview: all-time totals, this month, the last months, and scans by date |
| `list_analytics_reports` | Read-only | List the scan-analytics reports that have been generated: their scope, dates, status, and a download link once complete |
| `create_analytics_report` | Write | Generate a scan-analytics report for some QR codes, tags or folders over a date range |

### Account & billing

| Tool | Type | Description |
|---|---|---|
| `get_current_plan` | Read-only | Retrieve the account's active subscription plan — expiry, billing state, and the full quota list it grants |
| `list_available_plans` | Read-only | List the plans the account can move to, with their features and quotas |
| `get_downgrade_impact` | Read-only | Before moving to a smaller plan: which of the account's QR codes, users, domains and other resources exceed that plan and would block or be affected by the change |
| `list_payments` | Read-only | The account's payment history: amount, date and status of each payment |
| `list_orders` | Read-only | The account's orders (plan purchases, renewals and top-ups) and their status |
| `list_quota_topups` | Read-only | Extra quota bought on top of the plan (e.g |

### Team

| Tool | Type | Description |
|---|---|---|
| `list_users` | Read-only | List all users in the account |
| `get_user` | Read-only | Get details of a specific user |
| `add_user` | Write | Invite a new user to the account by email |
| `remove_user` | Destructive | Remove a user from the account |
| `list_user_roles` | Read-only | List all available user roles that can be assigned |
| `create_custom_role` | Write | Create a custom role/access-level (requires a dedicated plan quota — a 403 means the plan doesn't include it) |
| `update_user_role` | Destructive | Change the role of an existing user |
| `resend_user_invitation` | Write | Send a team member's invitation email again, for someone who hasn't accepted yet |
| `get_activity_feed` | Read-only | What happened in the account: who created, changed or deleted what, and when |
| `get_activity_summary` | Read-only | Counts of the account's activity over a period, for a quick picture of who did what |

### Custom domains

| Tool | Type | Description |
|---|---|---|
| `get_custom_domain` | Read-only | One custom domain's details: its DNS (TXT/CNAME) verification, SSL status and whether it's the default |

### Bulk operations

| Tool | Type | Description |
|---|---|---|
| `list_bulk_operations` | Read-only | List the account's bulk operations (bulk QR code generation and updates): what each did, its status and results |
| `get_bulk_operation_stats` | Read-only | Totals across the account's bulk operations |

### Media

| Tool | Type | Description |
|---|---|---|
| `list_media` | Read-only | List files in the account's media library (images, PDFs, videos…), e.g |

### Integrations

| Tool | Type | Description |
|---|---|---|
| `get_integrations_overview` | Read-only | Which integrations the account has connected (webhooks, Zapier, Slack, HubSpot, Google Analytics…) and their state |
| `list_webhooks` | Read-only | List the account's webhooks: where each sends events, for which forms or QR codes, and whether it's on |

### Conversion tracking

| Tool | Type | Description |
|---|---|---|
| `list_tracking_sites` | Read-only | List the websites set up for conversion tracking (what visitors do after scanning), with their domains |
| `list_tracking_funnels` | Read-only | List a tracking site's conversion funnels: the steps from scan to conversion |

### Landing pages

| Tool | Type | Description |
|---|---|---|
| `list_page_templates` | Read-only | List landing page templates for QR codes that open a page — Scanova's own, or only the account's saved ones |

## Usage

The server provides the following MCP tools that you can use in your MCP-compatible IDE:


## API Endpoints

The deployed server provides these endpoints:

- **POST `/mcp`** - Main MCP endpoint (Streamable HTTP)
- **GET `/health`** - Health check endpoint
- **GET `/`** - Service information and documentation
- **GET `/.well-known/oauth-protected-resource`** - OAuth protected-resource metadata

## Protocol

Built on the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) 2.x, which serves
the protocol. The server is **dual-era**:

- **MCP 2026-07-28** (stateless): every request carries its protocol version; `server/discover`,
  cache hints, `resultType` and request-header validation are supported.
- **Earlier revisions** (2025-11-25 and before): clients that open with `initialize` — today's
  Cursor, VS Code, Claude Desktop, claude.ai and ChatGPT connectors — keep working unchanged.

**Authentication.** Send your Scanova API key (or an OAuth access token from Scanova's
authorization server) in `Authorization` — `Bearer <key>` or the bare key — or in `X-API-Key`.
Listing tools and UI resources needs no key; calling a tool without one returns
`401` with a `WWW-Authenticate` challenge pointing at the protected-resource metadata.

Tool failures (for example a Scanova API error) come back as tool results with `isError: true`,
so the assistant can read and explain them.

UI widgets use the [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview)
extension (`io.modelcontextprotocol/ui`), plus `openai/outputTemplate` for ChatGPT.

## Local Development (Optional)

If you want to run the server locally for development:

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd qcg-mcp
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Run locally**:
   ```bash
   # HTTP server mode (same app as production)
   uv run src/cloud_server.py

   # Or stdio mode for local MCP testing (uses MCP_ACCESS_TOKEN for the Scanova API)
   MCP_ACCESS_TOKEN=your-key uv run src/main.py --stdio
   ```

4. **Configure for local testing**:
   ```json
   {
     "mcpServers": {
       "qcg-mcp": {
         "transport": "http",
         "url": "http://localhost:8000/mcp",
         "headers": {
           "Authorization": "YOUR_SCANOVA_API_KEY_HERE"
         }
       }
     }
   }
   ```

### Docker Deployment (Local)

1. **Build the Docker image**:
   ```bash
   docker build -t mcpserver:local .
   ```

2. **Start the container**:
   ```bash
   docker run -d --name mcpserver -p 8000:8000 mcpserver:local
   ```

   Or with Docker Compose:
   ```bash
   docker compose up -d
   ```

3. **Verify the server is running**:
   ```bash
   curl http://localhost:8000/health
   ```

4. **Configure your IDE (HTTP transport)**:
   Use the "Configure for local testing" snippet above and point to `http://localhost:8000/mcp`, ensuring the `Authorization` header contains your Scanova API key.

5. **View logs and stop**:
   ```bash
   # View logs
   docker logs -f mcpserver

   # Stop and remove with Compose
   docker compose down

   # Or stop/remove single container
   docker stop mcpserver && docker rm mcpserver
   ```

## Releases and deploys

Pull request titles follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat: …`, `fix: …`, `docs: …`, `chore: …`; add `!` — `feat!: …` — for a breaking change).
Merging adds the PR to the **draft release**, versioned by
[release-drafter](https://github.com/release-drafter/release-drafter) with semantic versioning:
`feat` → minor, `fix` and the rest → patch, breaking → major.

**Publishing the draft release deploys it** (`.github/workflows/deploy.yml`): tests run, the
image is built and tagged with the version, the `scanova-mcp` ECS Express service is updated to it,
and `/health` and `initialize` are checked. A merge to `main` does not deploy. To redeploy or roll
back, run the Deploy workflow from the Actions tab with that release's tag as the ref.

AWS access is GitHub OIDC → IAM role `qcg-mcp-github-deploy` (no stored keys): it trusts only this
repository's `production` environment (release tags `v*` only) and can only push this image, update
the `scanova-mcp` service and pass its task roles.

## Troubleshooting

### Common Issues

1. **"API key is required"**
   - Ensure your Scanova API key is correctly set in the headers
   - Check that the header format matches one of the supported formats
   - Get your API key from [https://app.scanova.io/](https://app.scanova.io/)

2. **"Invalid token" error**
   - Verify your API key is valid and active
   - Ensure there are no extra spaces or characters in the API key
   - Try regenerating your API key from the Scanova dashboard

3. **Connection errors**
   - Check that the server URL is correct
   - Ensure your internet connection is working
   - Verify the server is deployed and running

4. **Tool not found**
   - Restart your IDE after adding the MCP configuration
   - Check that the JSON configuration is valid
   - Verify the server responds at the `/health` endpoint

## License

This project is licensed under the terms of the MIT open source license. Please refer to [MIT](./LICENSE) for the full terms.
