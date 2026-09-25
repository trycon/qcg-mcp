import requests
from config import SCANOVA_BASE_URL
from api_response import api_result

_BASE = SCANOVA_BASE_URL.rstrip("/")


def _headers(api_key: str) -> dict:
    return {"Authorization": api_key, "Content-Type": "application/json"}


def _auth_error():
    return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}


def create_folder(name: str, folder_type: str, api_key: str = None) -> dict:
    """POST /folder/ — create a new folder (folder_type: 'qr' or 'page')."""
    if not api_key:
        return _auth_error()
    try:
        resp = requests.post(
            f"{_BASE}/folder/",
            headers=_headers(api_key),
            json={"name": name, "folder_type": folder_type},
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def list_folders(folder_type: str, api_key: str = None) -> dict:
    """GET /folder/ — list folders by type ('qr' or 'page')."""
    if not api_key:
        return _auth_error()
    try:
        resp = requests.get(
            f"{_BASE}/folder/",
            headers=_headers(api_key),
            params={"folder_type": folder_type},
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def update_folder(folder_id: int, name: str, api_key: str = None) -> dict:
    """PUT /folder/{id}/ — rename a folder."""
    if not api_key:
        return _auth_error()
    try:
        resp = requests.put(
            f"{_BASE}/folder/{folder_id}/",
            headers=_headers(api_key),
            json={"name": name},
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def delete_folder(folder_id: int, move_to_uncategorized: bool = True,
                  delete_permanently: bool = False, api_key: str = None) -> dict:
    """DELETE /folder/{id}/ — delete a folder."""
    if not api_key:
        return _auth_error()
    try:
        resp = requests.delete(
            f"{_BASE}/folder/{folder_id}/",
            headers=_headers(api_key),
            params={
                "move_to_uncategorized": move_to_uncategorized,
                "delete_permanently": delete_permanently,
            },
        )
        if resp.status_code == 204:
            return {"success": True, "message": "Folder deleted"}
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def move_qr_codes_to_folder(folder_id: int, qr_code_ids: list,
                             from_folder_id: int = None, api_key: str = None) -> dict:
    """POST /folder/{id}/bulk_move/ — move QR codes into a folder."""
    if not api_key:
        return _auth_error()
    body = {"qr_code_ids": qr_code_ids, "from": from_folder_id}
    try:
        resp = requests.post(
            f"{_BASE}/folder/{folder_id}/bulk_move/",
            headers=_headers(api_key),
            json=body,
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def unassign_qr_codes_from_folder(folder_id: int, qr_code_ids: list, api_key: str = None) -> dict:
    """POST /folder/{id}/bulk_unassign/ — remove QR codes from a folder."""
    if not api_key:
        return _auth_error()
    try:
        resp = requests.post(
            f"{_BASE}/folder/{folder_id}/bulk_unassign/",
            headers=_headers(api_key),
            json={"qr_code_ids": qr_code_ids},
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
