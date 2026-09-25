import requests
from config import SCANOVA_BASE_URL
from api_response import api_result

_BASE = SCANOVA_BASE_URL.rstrip("/")


def _headers(api_key: str) -> dict:
    return {"Authorization": api_key, "Content-Type": "application/json"}


def _auth_error():
    return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}


def get_current_plan(api_key: str = None) -> dict:
    """GET /plans/current/ — active subscription plan, billing state, and full quota list."""
    if not api_key:
        return _auth_error()
    try:
        resp = requests.get(f"{_BASE}/plans/current/", headers=_headers(api_key))
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
