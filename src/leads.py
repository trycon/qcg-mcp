import requests
from config import SCANOVA_BASE_URL
from api_response import api_result

_BASE = SCANOVA_BASE_URL.rstrip("/")


def _headers(api_key: str) -> dict:
    return {"Authorization": api_key, "Content-Type": "application/json"}


def _auth_error():
    return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}


def list_lead_lists(is_active: bool = None, api_key: str = None) -> dict:
    """GET /lead/ — list all lead lists with optional active filter."""
    if not api_key:
        return _auth_error()
    params = {}
    if is_active is not None:
        params["is_active"] = is_active
    try:
        resp = requests.get(f"{_BASE}/lead/", headers=_headers(api_key), params=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def retrieve_lead_list(lead_list_id: str, api_key: str = None) -> dict:
    """GET /lead/{id}/ — get detailed lead list information."""
    if not api_key:
        return _auth_error()
    if not lead_list_id:
        return {"error": "lead_list_id is required"}
    try:
        resp = requests.get(f"{_BASE}/lead/{lead_list_id}/", headers=_headers(api_key))
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def update_lead_list(lead_list_id: str, name: str = None, is_active: bool = None,
                     api_key: str = None) -> dict:
    """PATCH /lead/{id}/ — update lead list name or active status."""
    if not api_key:
        return _auth_error()
    if not lead_list_id:
        return {"error": "lead_list_id is required"}
    body = {}
    if name is not None:
        body["name"] = name
    if is_active is not None:
        body["is_active"] = is_active
    if not body:
        return {"error": "At least one of name or is_active must be provided"}
    try:
        resp = requests.patch(f"{_BASE}/lead/{lead_list_id}/", headers=_headers(api_key), json=body)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def delete_lead_list(lead_list_id: str, api_key: str = None) -> dict:
    """DELETE /lead/{id}/ — permanently delete a lead list."""
    if not api_key:
        return _auth_error()
    if not lead_list_id:
        return {"error": "lead_list_id is required"}
    try:
        resp = requests.delete(f"{_BASE}/lead/{lead_list_id}/", headers=_headers(api_key))
        if resp.status_code == 204:
            return {"success": True, "message": "Lead list deleted"}
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
