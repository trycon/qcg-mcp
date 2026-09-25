import requests
from config import SCANOVA_BASE_URL
from api_response import api_result

_BASE = SCANOVA_BASE_URL.rstrip("/")


def _headers(api_key: str) -> dict:
    return {"Authorization": api_key, "Content-Type": "application/json"}


def _auth_error():
    return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}


def list_users(api_key: str = None) -> dict:
    """GET /multi-users/ — list all users in the account."""
    if not api_key:
        return _auth_error()
    try:
        resp = requests.get(f"{_BASE}/multi-users/", headers=_headers(api_key))
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def get_user(user_id: str, api_key: str = None) -> dict:
    """GET /multi-users/{id}/ — get details of a specific user."""
    if not api_key:
        return _auth_error()
    if not user_id:
        return {"error": "user_id is required"}
    try:
        resp = requests.get(f"{_BASE}/multi-users/{user_id}/", headers=_headers(api_key))
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def add_user(email: str, role: str, api_key: str = None) -> dict:
    """POST /multi-users/ — invite a new user to the account."""
    if not api_key:
        return _auth_error()
    if not email:
        return {"error": "email is required"}
    if not role:
        return {"error": "role is required"}
    try:
        resp = requests.post(
            f"{_BASE}/multi-users/",
            headers=_headers(api_key),
            json={"email": email, "role": role},
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def remove_user(user_id: str, api_key: str = None) -> dict:
    """DELETE /multi-users/{id}/ — remove a user from the account."""
    if not api_key:
        return _auth_error()
    if not user_id:
        return {"error": "user_id is required"}
    try:
        resp = requests.delete(f"{_BASE}/multi-users/{user_id}/", headers=_headers(api_key))
        if resp.status_code == 204:
            return {"success": True, "message": "User removed"}
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def list_user_roles(api_key: str = None) -> dict:
    """GET /multi-users/access-levels/ — list available user roles."""
    if not api_key:
        return _auth_error()
    try:
        resp = requests.get(f"{_BASE}/multi-users/access-levels/", headers=_headers(api_key))
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def create_custom_role(name: str, permissions: list, api_key: str = None) -> dict:
    """POST /multi-users/access-levels/ — create a custom role (plan-gated feature)."""
    if not api_key:
        return _auth_error()
    if not name:
        return {"error": "name is required"}
    if not permissions:
        return {"error": "permissions is required"}
    try:
        resp = requests.post(
            f"{_BASE}/multi-users/access-levels/",
            headers=_headers(api_key),
            json={"name": name, "permissions": permissions},
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def update_user_role(user_id: str, access_level: str, api_key: str = None) -> dict:
    """PATCH /multi-users/{id}/ — update a user's access_level."""
    if not api_key:
        return _auth_error()
    if not user_id:
        return {"error": "user_id is required"}
    if not access_level:
        return {"error": "access_level is required"}
    try:
        resp = requests.patch(
            f"{_BASE}/multi-users/{user_id}/",
            headers=_headers(api_key),
            json={"access_level": access_level},
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
