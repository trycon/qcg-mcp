import json
"""Unit tests for the 6 new domain-gap backend functions added alongside the
tool restructuring: validate_qr_info, get_qr_category_fields, create_form,
list_tags, get_current_plan, create_custom_role."""

import qrcode
import forms
import tags
import billing
import users


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self):
        if self._json_data is None:
            raise ValueError("no json body")
        return self._json_data


# --------------------------------------------------------------------------- #
# validate_qr_info
# --------------------------------------------------------------------------- #

def test_validate_qr_info_requires_api_key():
    assert "error" in qrcode.validate_qr_info(category=1, info={"type": "url", "data": {"url": "https://x.com"}})


def test_validate_qr_info_success(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, data=None, **kwargs):
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        return _FakeResponse(status_code=200)

    monkeypatch.setattr(qrcode.requests, "post", fake_post)
    result = qrcode.validate_qr_info(category=1, info={"type": "url", "data": {"url": "https://x.com"}}, api_key="k")
    assert result == {"valid": True, "message": "QR code info data is valid"}
    assert captured["url"].endswith("/qr/validate-info/")
    assert captured["data"]["category"] == "1"
    assert '"url": "https://x.com"' in captured["data"]["info"] or "url" in captured["data"]["info"]
    assert "Content-Type" not in captured["headers"]


def test_validate_qr_info_failure(monkeypatch):
    def fake_post(url, headers=None, data=None, **kwargs):
        return _FakeResponse(status_code=400, json_data={"info": ["This field is required."]})

    monkeypatch.setattr(qrcode.requests, "post", fake_post)
    result = qrcode.validate_qr_info(category=1, info={"type": "url", "data": {}}, api_key="k")
    assert result["valid"] is False
    assert result["error"] == ["This field is required."]


# --------------------------------------------------------------------------- #
# get_qr_category_fields (static, no network)
# --------------------------------------------------------------------------- #

def test_get_qr_category_fields_known_category():
    result = qrcode.get_qr_category_fields(1)
    assert result["name"] == "Website URL"
    assert result["documented"] is True


def test_get_qr_category_fields_undocumented_category():
    result = qrcode.get_qr_category_fields(26)
    assert result["documented"] is False


def test_get_qr_category_fields_unknown_category():
    result = qrcode.get_qr_category_fields(9999)
    assert "error" in result


def test_get_qr_category_fields_no_argument_lists_all():
    result = qrcode.get_qr_category_fields()
    assert isinstance(result["categories"], dict)
    assert 1 in result["categories"]


# --------------------------------------------------------------------------- #
# create_form
# --------------------------------------------------------------------------- #

def test_create_form_requires_name_and_data():
    assert "error" in forms.create_form(name=None, data={"fields": []}, api_key="k")
    assert "error" in forms.create_form(name="Signup", data=None, api_key="k")


def test_create_form_success(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, **kwargs):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(status_code=201, json_data={"id": 1, "form_id": "F1", "name": "Signup"})

    monkeypatch.setattr(forms.requests, "post", fake_post)
    blocks = [{"type": "form_details", "data": {"title": "Signup", "questions": []}}]
    result = forms.create_form(name="Signup", data=blocks, qr_id="Qabc", api_key="k")
    assert result["form_id"] == "F1"
    assert captured["url"].endswith("/forms/")
    assert captured["json"]["name"] == "Signup"
    assert captured["json"]["qr_id"] == "Qabc"
    # The API stores Form.data as text: blocks go as a JSON string.
    assert json.loads(captured["json"]["data"]) == blocks


def test_create_form_rejects_an_object_for_data():
    assert "error" in forms.create_form(name="Signup", data={"fields": []}, api_key="k")


# --------------------------------------------------------------------------- #
# list_tags
# --------------------------------------------------------------------------- #

def test_list_tags_requires_api_key():
    assert "error" in tags.list_tags()


def test_list_tags_success(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(status_code=200, json_data={"count": 1, "next": None, "previous": None, "results": [{"id": 1, "name": "sale"}]})

    monkeypatch.setattr(tags.requests, "get", fake_get)
    result = tags.list_tags(name="sa", api_key="k")
    assert result["results"][0]["name"] == "sale"
    assert captured["url"].endswith("/tag/list/")
    assert captured["params"] == {"name": "sa"}


# --------------------------------------------------------------------------- #
# get_current_plan
# --------------------------------------------------------------------------- #

def test_get_current_plan_requires_api_key():
    assert "error" in billing.get_current_plan()


def test_get_current_plan_success(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, **kwargs):
        captured["url"] = url
        return _FakeResponse(status_code=200, json_data={"is_active": True, "plan": {"name": "Pro"}})

    monkeypatch.setattr(billing.requests, "get", fake_get)
    result = billing.get_current_plan(api_key="k")
    assert result["plan"]["name"] == "Pro"
    assert captured["url"].endswith("/plans/current/")


# --------------------------------------------------------------------------- #
# create_custom_role
# --------------------------------------------------------------------------- #

def test_create_custom_role_requires_name_and_permissions():
    assert "error" in users.create_custom_role(name=None, permissions=[1], api_key="k")
    assert "error" in users.create_custom_role(name="Support", permissions=None, api_key="k")


def test_create_custom_role_success(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, **kwargs):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(status_code=201, json_data={"id": 42, "name": "Support", "is_custom": True})

    monkeypatch.setattr(users.requests, "post", fake_post)
    result = users.create_custom_role(name="Support", permissions=[23, 24], api_key="k")
    assert result["id"] == 42
    assert captured["url"].endswith("/multi-users/access-levels/")
    assert captured["json"] == {"name": "Support", "permissions": [23, 24]}
