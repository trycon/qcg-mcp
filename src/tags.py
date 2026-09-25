import requests
from config import SCANOVA_BASE_URL
from api_response import api_result

_BASE = SCANOVA_BASE_URL.rstrip("/")


def _headers(api_key: str) -> dict:
    return {"Authorization": api_key, "Content-Type": "application/json"}


def _auth_error():
    return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}


def list_tags(name: str = None, page: int = None, page_size: int = None, api_key: str = None) -> dict:
    """GET /tag/list/ — list tags attached to (or assignable against) the account's QR codes."""
    if not api_key:
        return _auth_error()
    params = {}
    if name:
        params["name"] = name
    if page:
        params["page"] = page
    if page_size:
        params["page_size"] = page_size
    try:
        resp = requests.get(f"{_BASE}/tag/list/", headers=_headers(api_key), params=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
