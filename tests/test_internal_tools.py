"""lookup_customer_plan (mcp_http/internal_tools.py): the internal plan lookup by email.

The backend is faked at requests.post. Checked: the exact request (internal base URL, POST body, the service token),
that only a caller presenting the service token gets through, the "not configured" state, input checks, how backend
answers come back, and that the tool is grouped, read-only and never logs the email.
"""

import json
import logging

import pytest
import requests

import config
from mcp_http import internal_tools
from mcp_http.annotations import annotations_for
from mcp_http.dispatcher import execute_tool
from mcp_http.normalizer import normalize
from mcp_http.registry import list_mcp_tools
from mcp_http.toolsets import TOOLSETS, toolset_for
from conftest import rpc

SERVICE = "qsvc_test-service-token"
BASE = "https://internal.scanova.test"
FOUND = {
    "found": True,
    "role": "owner",
    "plan": {"name": "Pro", "family": {"slug": "pro", "name": "Pro"}, "plan_type": "normal",
             "is_enterprise": False, "is_trial": False},
    "status": "active",
    "is_free": False,
    "expire": "2027-03-31",
    "days_left": 136,
    "recurring_enabled": True,
    "billing_interval": "Yearly",
    "upcoming_plan": None,
    "seats": {"used": 4, "limit": 10},
}


class _Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setattr(config, "INTERNAL_API_BASE_URL", BASE)
    monkeypatch.setattr(config, "SCANOVA_SERVICE_TOKEN", SERVICE)
    calls = []
    state = {"resp": _Resp(200, FOUND)}

    def fake_post(url, headers=None, json=None, timeout=None, **kw):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if isinstance(state["resp"], Exception):
            raise state["resp"]
        return state["resp"]

    monkeypatch.setattr(internal_tools.requests, "post", fake_post)
    return type("Backend", (), {"calls": calls, "state": state})


def test_posts_the_email_to_the_internal_listener_with_the_service_token(backend):
    out = execute_tool("lookup_customer_plan", {"email": "  Owner@Example.com "}, SERVICE)

    assert out == FOUND
    (call,) = backend.calls
    assert call["url"] == f"{BASE}/internal/plan-lookup/"
    assert call["json"] == {"email": "owner@example.com"}
    assert call["headers"]["Authorization"] == SERVICE
    assert "owner@example.com" not in call["url"]
    assert call["timeout"]


def test_customer_credentials_are_refused_and_never_forwarded(backend):
    for key in ("customer-management-api-key", "qsvc_some-other-token", f"{SERVICE}x"):
        out = execute_tool("lookup_customer_plan", {"email": "a@example.com"}, key)
        assert out["status_code"] == 403, key
    assert backend.calls == []


def test_no_credential_calls_nothing(backend):
    assert "error" in execute_tool("lookup_customer_plan", {"email": "a@example.com"}, None)
    assert backend.calls == []


@pytest.mark.parametrize("base,token", [("", SERVICE), (BASE, None), ("", None)])
def test_not_configured(monkeypatch, base, token):
    monkeypatch.setattr(config, "INTERNAL_API_BASE_URL", base)
    monkeypatch.setattr(config, "SCANOVA_SERVICE_TOKEN", token)
    out = execute_tool("lookup_customer_plan", {"email": "a@example.com"}, SERVICE)
    assert out["status_code"] == 503 and "isn't configured" in out["error"]


@pytest.mark.parametrize("email", [None, "", "   ", "not-an-email", "a b@x.com", 42, "x" * 250 + "@x.com"])
def test_bad_email_calls_nothing(backend, email):
    out = execute_tool("lookup_customer_plan", {"email": email}, SERVICE)
    assert out["status_code"] == 400
    assert backend.calls == []


def test_not_found_passes_through(backend):
    backend.state["resp"] = _Resp(200, {"found": False})
    assert execute_tool("lookup_customer_plan", {"email": "a@example.com"}, SERVICE) == {"found": False}


@pytest.mark.parametrize("status,code", [(401, "unauthorized"), (403, "forbidden"), (429, "rate_limited"), (500, "internal")])
def test_backend_errors_become_tool_errors(backend, status, code):
    backend.state["resp"] = _Resp(status, {"error": code})
    out = execute_tool("lookup_customer_plan", {"email": "a@example.com"}, SERVICE)
    assert out == {"error": {"error": code}, "status_code": status}
    envelope = normalize(out, "lookup_customer_plan")
    assert envelope["ok"] is False and envelope["status_code"] == status


def test_network_error_has_no_detail(backend):
    backend.state["resp"] = requests.ConnectionError("https://internal.scanova.test/ a@example.com")
    out = execute_tool("lookup_customer_plan", {"email": "a@example.com"}, SERVICE)
    assert out["status_code"] == 503
    assert "a@example.com" not in json.dumps(out)


def test_grouped_read_only_and_listed():
    assert toolset_for("lookup_customer_plan") == "internal"
    assert TOOLSETS["internal"][2] == frozenset({"lookup_customer_plan"})
    assert annotations_for("lookup_customer_plan")["readOnlyHint"] is True
    tool = next(t for t in list_mcp_tools() if t["name"] == "lookup_customer_plan")
    assert tool["inputSchema"]["required"] == ["email"]
    assert tool["annotations"]["readOnlyHint"] is True


def test_over_mcp_a_customer_gets_a_tool_error(backend):
    resp = rpc("tools/call", {"params": {"name": "lookup_customer_plan", "arguments": {"email": "a@example.com"}}},
               api_key="customer-management-api-key")
    result = resp["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["status_code"] == 403
    assert backend.calls == []


def test_over_mcp_the_service_gets_the_plan_and_the_email_is_not_logged(backend, caplog):
    with caplog.at_level(logging.DEBUG):
        resp = rpc("tools/call", {"params": {"name": "lookup_customer_plan", "arguments": {"email": "who@example.com"}}},
                   api_key=SERVICE)
    result = resp["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["ok"] is True
    assert result["structuredContent"]["data"]["plan"]["family"]["name"] == "Pro"
    assert "who@example.com" not in caplog.text
