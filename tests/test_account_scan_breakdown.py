"""get_account_scan_breakdown: account-wide scan analytics via POST analytics/qr/ with all=true and q=['all']."""

import json

import pytest

import analytics
from mcp_http.annotations import annotations_for
from mcp_http.dispatcher import execute_tool
from mcp_http.registry import list_mcp_tools


class _Resp:
    status_code = 200
    text = '{"device": [["Mobile", 5]]}'

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def post(monkeypatch):
    calls = []

    def fake(url, headers=None, params=None, json=None, **kw):
        calls.append({"url": url, "headers": headers, "params": params, "body": json})
        return _Resp()

    monkeypatch.setattr(analytics.requests, "post", fake)
    return calls


def test_request_covers_the_whole_account(post):
    out = analytics.get_account_scan_breakdown(
        ["device", "geography"], "2026-10-01", "2026-10-31", exclude_bot_scan=True, api_key="k"
    )
    assert out == {"device": [["Mobile", 5]]}
    (c,) = post
    assert c["url"].endswith("/analytics/qr/")
    assert c["body"] == {"filter_by": "qrid", "q": ["all"]}
    assert c["params"] == {
        "type": "device,geography", "from": "2026-10-01", "to": "2026-10-31",
        "exclude_bot_scan": True, "all": "true",
    }
    assert c["headers"]["Authorization"] == "k"


def test_requires_api_key(post):
    assert "error" in analytics.get_account_scan_breakdown(["count"], "2026-10-01", "2026-10-31")
    assert post == []


def test_registered_read_only_with_no_qr_inputs():
    tool = next(t for t in list_mcp_tools() if t["name"] == "get_account_scan_breakdown")
    props = tool["inputSchema"]["properties"]
    assert "filter_by" not in props and "q" not in props
    assert set(tool["inputSchema"]["required"]) == {"types", "from_date", "to_date"}
    assert "get_qr_analytics" in tool["description"]
    assert annotations_for("get_account_scan_breakdown")["readOnlyHint"] is True


def test_dispatch_passes_arguments_through(post):
    execute_tool("get_account_scan_breakdown", {"types": ["browser"], "from_date": "2026-10-01", "to_date": "2026-10-02"}, "k")
    assert post[0]["body"]["q"] == ["all"] and post[0]["params"]["all"] == "true"
    assert post[0]["params"]["exclude_bot_scan"] is False
