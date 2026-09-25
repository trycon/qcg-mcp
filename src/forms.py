import requests
from config import SCANOVA_BASE_URL
from api_response import api_result

_BASE = SCANOVA_BASE_URL.rstrip("/")


def _headers(api_key: str) -> dict:
    return {"Authorization": api_key, "Content-Type": "application/json"}


def _auth_error():
    return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}


def list_forms(is_active: bool = None, api_key: str = None) -> dict:
    """GET /form/ — list all forms with optional active filter."""
    if not api_key:
        return _auth_error()
    params = {}
    if is_active is not None:
        params["is_active"] = is_active
    try:
        resp = requests.get(f"{_BASE}/forms/", headers=_headers(api_key), params=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def create_form(name: str, data: dict, qr_id: str = None, theme_id: int = None,
                 theme_overrides: dict = None, api_key: str = None) -> dict:
    """POST /forms/ — create a new lead-capture form."""
    if not api_key:
        return _auth_error()
    if not name:
        return {"error": "name is required"}
    if not data:
        return {"error": "data is required"}
    body = {"name": name, "data": data}
    if qr_id is not None:
        body["qr_id"] = qr_id
    if theme_id is not None:
        body["theme_id"] = theme_id
    if theme_overrides is not None:
        body["theme_overrides"] = theme_overrides
    try:
        resp = requests.post(f"{_BASE}/forms/", headers=_headers(api_key), json=body)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def retrieve_form(form_id: str, api_key: str = None) -> dict:
    """GET /form/{id}/ — get detailed form information."""
    if not api_key:
        return _auth_error()
    if not form_id:
        return {"error": "form_id is required"}
    try:
        resp = requests.get(f"{_BASE}/forms/{form_id}/", headers=_headers(api_key))
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def update_form(form_id: str, name: str = None, is_active: bool = None, api_key: str = None) -> dict:
    """PATCH /form/{id}/ — update form name or active status."""
    if not api_key:
        return _auth_error()
    if not form_id:
        return {"error": "form_id is required"}
    body = {}
    if name is not None:
        body["name"] = name
    if is_active is not None:
        body["is_active"] = is_active
    if not body:
        return {"error": "At least one of name or is_active must be provided"}
    try:
        resp = requests.patch(f"{_BASE}/forms/{form_id}/", headers=_headers(api_key), json=body)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def delete_form(form_id: str, api_key: str = None) -> dict:
    """DELETE /form/{id}/ — permanently delete a form."""
    if not api_key:
        return _auth_error()
    if not form_id:
        return {"error": "form_id is required"}
    try:
        resp = requests.delete(f"{_BASE}/forms/{form_id}/", headers=_headers(api_key))
        if resp.status_code == 204:
            return {"success": True, "message": "Form deleted"}
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
