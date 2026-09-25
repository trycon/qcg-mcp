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

### QR Code Management

| Tool                          | Description                                        |
|-------------------------------|-----------------------------------------------------|
| `create_qr_code`              | Create a new QR code                                 |
| `list_qr_codes`               | List existing QR codes (paginated/searchable)        |
| `update_qr_code`               | Update an existing QR code                          |
| `retrieve_qr_code`            | Get details of a specific QR code                    |
| `download_qr_code`            | Download a QR code image (PNG/JPG/PDF/SVG/EPS)       |
| `download_qr_printable`       | Generate a print-optimized PDF of a QR code          |
| `activate_qr_code`            | Activate a QR code                                   |
| `deactivate_qr_code`          | Deactivate a QR code                                 |
| `delete_qr_code`              | Permanently delete a QR code                         |
| `get_qr_categories`           | List QR categories (URL, vCard, WiFi, etc.)          |
| `attach_form_to_qr`           | Attach a lead-capture form to a QR code              |
| `detach_form_from_qr`         | Remove a form from a QR code                         |
| `attach_lead_list_to_qr`      | Attach a lead list to a QR code                      |
| `detach_lead_list_from_qr`    | Remove a lead list from a QR code                    |

### QR Code Design

| Tool                     | Description                                                    |
|--------------------------|------------------------------------------------------------------|
| `get_qr_design_options`  | List available design options (patterns, eye shapes, frames, gradients, error correction) |
| `set_qr_design`          | Apply a visual design to an existing QR code                    |

### Folder Management

| Tool                              | Description                                  |
|------------------------------------|-----------------------------------------------|
| `create_folder`                   | Create a new folder                           |
| `list_folders`                    | List folders                                  |
| `update_folder`                   | Update an existing folder                     |
| `delete_folder`                   | Delete a folder                               |
| `move_qr_codes_to_folder`         | Move QR codes into a folder                   |
| `unassign_qr_codes_from_folder`   | Remove QR codes from a folder                 |

### Forms & Lead Lists

| Tool                | Description                        |
|---------------------|-------------------------------------|
| `list_forms`        | List lead-capture forms             |
| `retrieve_form`     | Get details of a specific form      |
| `update_form`       | Update an existing form             |
| `delete_form`       | Delete a form                       |
| `list_lead_lists`   | List lead lists                     |
| `retrieve_lead_list`| Get details of a specific lead list |
| `update_lead_list`  | Update an existing lead list        |
| `delete_lead_list`  | Delete a lead list                  |

### Analytics

| Tool                 | Description                                              |
|----------------------|------------------------------------------------------------|
| `get_account_stats`  | Get account-level usage statistics                          |
| `get_qr_analytics`   | Get QR performance metrics by device, geography, and date   |
| `export_analytics`   | Export an analytics report (XLSX/PDF)                       |
| `export_raw_scans`   | Export row-level scan logs (CSV/XLSX)                       |

### Account Administration

| Tool                | Description                              |
|---------------------|--------------------------------------------|
| `list_users`        | List account users                          |
| `get_user`          | Get details of a specific user              |
| `add_user`          | Invite a new user by email                  |
| `remove_user`       | Remove a user from the account              |
| `list_user_roles`   | List available user roles                   |
| `update_user_role`  | Update a user's role assignment             |

### Documentation

| Tool               | Description                                                |
|--------------------|---------------------------------------------------------------|
| `probe_docs_mcp`   | Check connectivity to the Scanova docs MCP server and list its tools |
| `query_docs`       | Query Scanova documentation via the docs MCP bridge            |

## Usage

The server provides the following MCP tools that you can use in your MCP-compatible IDE:


## API Endpoints

The deployed server provides these endpoints:

- **POST `/mcp`** - Main MCP JSON-RPC endpoint
- **GET `/health`** - Health check endpoint
- **GET `/`** - Service information and documentation

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
   # HTTP server mode
   uv run cloud_server.py
   
   # Or stdio mode for local MCP testing
   uv run main.py
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
