import json

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


# Answer types a form question can have (forms/json_schema/components/questions
# in qcg-backend). File upload, signature and content blocks need the builder UI.
ANSWER_TYPES = (
    "shortAnswer", "paragraph", "email", "phoneNumber", "number",
    "multipleChoice", "checkbox", "dropdown", "linearScale",
    "dateFormat", "timeFormat", "starRating", "emoji", "likeDislike",
)
CHOICE_TYPES = ("multipleChoice", "checkbox", "dropdown")


def build_form_blocks(title: str, questions: list, description: str = None,
                      submit_label: str = None, thank_you: str = None):
    """The Form.data blocks (form_details + submit_button) for a simple form, or an error string."""
    if not title or not str(title).strip():
        return None, "title is required"
    if not questions:
        return None, "add at least one question"
    built = []
    for i, q in enumerate(questions, 1):
        text = str((q or {}).get("question") or "").strip()
        kind = (q or {}).get("type") or "shortAnswer"
        if not text:
            return None, f"question {i} has no text"
        if kind not in ANSWER_TYPES:
            return None, f"question {i}: type must be one of {', '.join(ANSWER_TYPES)}"
        answer = {"type": kind}
        if kind in CHOICE_TYPES:
            options = [str(o).strip() for o in q.get("options") or [] if str(o).strip()]
            if not options:
                return None, f"question {i} ({kind}) needs options"
            if len(set(o.lower() for o in options)) != len(options):
                return None, f"question {i} has the same option twice"
            answer["data"] = [{"option": o} for o in options]
        item = {"question": text[:200], "isRequired": bool(q.get("required", False)), "answer": answer}
        if q.get("description"):
            item["questionDescription"] = str(q["description"])
        built.append(item)
    details = {"title": str(title).strip(), "questions": built}
    if description:
        details["description"] = str(description)
    if thank_you:
        details["submissionBehaviour"] = {"submissionOption": "message", "message": str(thank_you)}
    return [
        {"type": "form_details", "data": details},
        {"type": "submit_button", "data": {"label": (submit_label or "Submit").strip()[:100]}},
    ], None


def create_form(name: str, data=None, qr_id: str = None, theme_id: int = None,
                theme_overrides: dict = None, api_key: str = None) -> dict:
    """POST /forms/ — create a new lead-capture form.

    `data` is the form's blocks (a list, as build_form_blocks makes them). The
    API stores it as text, so it's sent as a JSON string.
    """
    if not api_key:
        return _auth_error()
    if not name:
        return {"error": "name is required"}
    if not data:
        return {"error": "data is required"}
    if isinstance(data, dict):
        return {"error": "data is a list of form blocks, e.g. [{\"type\": \"form_details\", \"data\": {...}}] — or pass title and questions instead."}
    body = {"name": name, "data": data if isinstance(data, str) else json.dumps(data)}
    if qr_id is not None:
        body["qr_id"] = qr_id
    if theme_id is not None:
        body["theme_id"] = theme_id
    if theme_overrides is not None:
        body["theme_overrides"] = theme_overrides
    try:
        resp = requests.post(f"{_BASE}/forms/", headers=_headers(api_key), json=body, timeout=20)
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
