import base64
import requests
from config import SCANOVA_BASE_URL
from api_response import api_result

_BASE = SCANOVA_BASE_URL.rstrip("/")


def _headers(api_key: str) -> dict:
    return {"Authorization": api_key, "Content-Type": "application/json"}


def _auth_error():
    return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}


def get_account_stats(fields: list = None, api_key: str = None) -> dict:
    """GET /auth/stats/ — account-level usage counters."""
    if not api_key:
        return _auth_error()
    params = {}
    if fields:
        params["fields"] = ",".join(fields)
    try:
        resp = requests.get(f"{_BASE}/auth/stats/", headers=_headers(api_key), params=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def get_qr_analytics(filter_by: str, q: list, types: list, from_date: str, to_date: str,
                     exclude_bot_scan: bool = False, api_key: str = None) -> dict:
    """POST /analytics/qr/ — QR code performance metrics."""
    if not api_key:
        return _auth_error()
    params = {
        "type": ",".join(types),
        "from": from_date,
        "to": to_date,
        "exclude_bot_scan": exclude_bot_scan,
    }
    body = {"filter_by": filter_by, "q": q}
    try:
        resp = requests.post(f"{_BASE}/analytics/qr/", headers=_headers(api_key), params=params, json=body)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def export_analytics(filter_by: str, q: list, from_date: str, to_date: str,
                     file_format: str = "xlsx", exclude_bot_scan: bool = False,
                     api_key: str = None) -> dict:
    """POST /analytics/qr/export/ — export analytics as Excel or PDF."""
    if not api_key:
        return _auth_error()
    params = {
        "from": from_date,
        "to": to_date,
        "file_format": file_format,
        "exclude_bot_scan": exclude_bot_scan,
    }
    body = {"filter_by": filter_by, "q": q}
    try:
        resp = requests.post(f"{_BASE}/analytics/qr/export/", headers=_headers(api_key), params=params, json=body)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "application/octet-stream")
            return {
                "success": True,
                "content_type": content_type,
                "size_bytes": len(resp.content),
                "data_base64": base64.b64encode(resp.content).decode("utf-8"),
            }
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def export_raw_scans(filter_by: str, q: list, from_date: str, to_date: str,
                     file_format: str = "csv", scan_type: str = "raw",
                     exclude_bot_scan: bool = False, api_key: str = None) -> dict:
    """POST /analytics/qr/raw/ — export row-level scan logs."""
    if not api_key:
        return _auth_error()
    params = {
        "type": scan_type,
        "from": from_date,
        "to": to_date,
        "file_format": file_format,
        "exclude_bot_scan": exclude_bot_scan,
    }
    body = {"filter_by": filter_by, "q": q}
    try:
        resp = requests.post(f"{_BASE}/analytics/qr/raw/", headers=_headers(api_key), params=params, json=body)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "application/octet-stream")
            return {
                "success": True,
                "content_type": content_type,
                "size_bytes": len(resp.content),
                "data_base64": base64.b64encode(resp.content).decode("utf-8"),
            }
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
