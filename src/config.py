import os
from pathlib import Path

# Base URL for Scanova API
# api.scanova.io is the Management API's public name (docs' server URL);
# management.scanova.io serves the same routes but is being retired.
SCANOVA_BASE_URL = os.getenv("API_BASE_URL", "https://api.scanova.io/")

# Optional: Access token for MCP server authentication (if needed)
MCP_ACCESS_TOKEN = os.getenv("MCP_ACCESS_TOKEN")

# OAuth server URL for discovery endpoint
OAUTH_SERVER_URL = os.getenv("OAUTH_SERVER_URL", "https://qcg-api.scanova.io")

# Resource URL for lazy authentication 401 header
MCP_RESOURCE_URL = os.getenv("MCP_RESOURCE_URL", "https://mcp.scanova.io")

OPENAI_APPS_CHALLENGE = os.getenv("OPENAI_APPS_CHALLENGE")

# Global kill switch for MCP UI Elements (resources + _meta attachment).
# Per-tool enablement is separate — see mcp_http/ui_response.py:UI_ENABLED_TOOLS.
UI_ELEMENTS_ENABLED = os.getenv("UI_ELEMENTS_ENABLED", "true").strip().lower() in ("1", "true", "yes")

# CORS allowlist for the /mcp endpoint. Defaults to "*" intentionally —
# this server accepts connections from any compliant MCP/AI client, so a
# fixed origin allowlist isn't applicable. Override with a comma-separated
# list (e.g. "https://chatgpt.com,https://claude.ai") only if that ever
# changes.
_allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
ALLOWED_ORIGINS = (
    ["*"] if _allowed_origins_raw == "*"
    else [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]
)
# Host header values accepted when Host/Origin checks are on (i.e. when
# ALLOWED_ORIGINS is an explicit list). "host:*" allows any port.
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "mcp.scanova.io,localhost:*,127.0.0.1:*").split(",") if h.strip()]

# Per-caller request limits on /mcp (see mcp_http/rate_limit.py). Tool calls
# are limited per credential, public discovery requests per client IP.
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "40"))
ANON_RATE_LIMIT_PER_MINUTE = int(os.getenv("ANON_RATE_LIMIT_PER_MINUTE", "60"))

# Scanova's QR renderer (qcg-generator): the same one downloads use. Design
# previews and scan tests render through it (design_checks.py).
QCG_GENERATOR_URL = os.getenv("QCG_GENERATOR_URL", "https://generator.scanova.io")
