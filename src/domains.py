"""Custom domains: the account's own short-link domains (e.g. qr.milkfarm.com)."""

import requests

from api_response import api_result
from config import SCANOVA_BASE_URL

_BASE = SCANOVA_BASE_URL.rstrip("/")


def list_custom_domains(api_key=None):
    """GET /custom-domain/ — the account's connected custom domains and which one is the default."""
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    try:
        resp = requests.get(f"{_BASE}/custom-domain/", headers={"Authorization": api_key, "Content-Type": "application/json"}, timeout=20)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
