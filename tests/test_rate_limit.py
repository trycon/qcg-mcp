"""Per-caller rate limits on /mcp."""

from unittest.mock import patch

from starlette.testclient import TestClient

from cloud_server import McpFrontMiddleware, build_app
from mcp_http.rate_limit import RateLimiter, credential_key

HEADERS = {"accept": "application/json, text/event-stream", "mcp-protocol-version": "2025-06-18"}


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_bucket_allows_burst_then_waits_and_refills():
    clock = FakeClock()
    limiter = RateLimiter(per_minute=60, burst=3, clock=clock)
    assert [limiter.acquire("k") for _ in range(3)] == [0, 0, 0]
    assert limiter.acquire("k") == 1.0  # one token per second
    clock.now += 2
    assert limiter.acquire("k") == 0
    assert limiter.acquire("other") == 0  # buckets are per key


def test_batch_cost_counts_every_message():
    limiter = RateLimiter(per_minute=60, burst=5, clock=FakeClock())
    assert limiter.acquire("k", cost=5) == 0
    assert limiter.acquire("k", cost=1) > 0


def test_idle_buckets_are_dropped():
    clock = FakeClock()
    limiter = RateLimiter(per_minute=60, clock=clock)
    limiter.acquire("k")
    clock.now += 16 * 60
    limiter.acquire("fresh")
    assert set(limiter._buckets) == {"fresh"}


def test_credential_key_never_holds_the_credential():
    key = credential_key("sk_live_secret")
    assert "sk_live_secret" not in key and key.startswith("cred:")


def _limited_client(per_minute: int, burst: int, anon: int) -> TestClient:
    app = build_app()
    front = app.app
    assert isinstance(front, McpFrontMiddleware)
    front.credential_limiter = RateLimiter(per_minute, burst)
    front.anonymous_limiter = RateLimiter(anon)
    return TestClient(app)


def _call(client: TestClient, key: str):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_folders", "arguments": {}}}
    return client.post("/mcp", json=body, headers={**HEADERS, "authorization": key})


def test_tool_calls_are_limited_per_credential():
    with patch("mcp_http.sdk_server.execute_tool", return_value={"folders": []}), _limited_client(60, 2, 1000) as client:
        assert _call(client, "key-a").status_code == 200
        assert _call(client, "key-a").status_code == 200
        limited = _call(client, "key-a")
        assert limited.status_code == 429
        assert int(limited.headers["retry-after"]) >= 1
        assert limited.json()["error"]["data"]["retryAfter"] >= 1
        # Another customer isn't affected.
        assert _call(client, "key-b").status_code == 200


def test_public_discovery_is_limited_per_ip():
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    with _limited_client(1000, 1000, 2) as client:
        ip1 = {**HEADERS, "x-forwarded-for": "203.0.113.1, 10.0.0.1"}
        assert client.post("/mcp", json=body, headers=ip1).status_code == 200
        assert client.post("/mcp", json=body, headers=ip1).status_code == 200
        assert client.post("/mcp", json=body, headers=ip1).status_code == 429
        ip2 = {**HEADERS, "x-forwarded-for": "203.0.113.2"}
        assert client.post("/mcp", json=body, headers=ip2).status_code == 200


def test_unauthenticated_tool_call_still_gets_401_not_429():
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_folders", "arguments": {}}}
    with _limited_client(1, 1, 1) as client:
        for _ in range(3):
            assert client.post("/mcp", json=body, headers=HEADERS).status_code == 401
