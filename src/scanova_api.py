"""One Scanova Management API call, for tools that are a thin wrapper over an endpoint.

The older modules (qrcode.py, forms.py, …) each repeat this request/response
boilerplate; newer tools (mcp_http/more_tools.py) share it from here.
"""

import requests

from api_response import api_result
from config import SCANOVA_BASE_URL

_BASE = SCANOVA_BASE_URL.rstrip("/")
TIMEOUT_S = 20
NO_KEY = {"error": "API key is required. Please configure your Scanova API key in your MCP client."}


def scanova(method: str, path: str, api_key: str, params: dict = None, body=None):
    """`method` `path` (relative, e.g. "qr/trash/") as the caller; the result as api_result gives it."""
    if not api_key:
        return NO_KEY
    query = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    try:
        resp = requests.request(
            method,
            f"{_BASE}/{path.lstrip('/')}",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            params=query or None,
            json=body,
            timeout=TIMEOUT_S,
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
