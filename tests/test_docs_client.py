"""docs_client: output cap and probe via tools/list."""

import json
from unittest.mock import patch

import docs_client


class _Resp:
    def __init__(self, payload: dict) -> None:
        self.text = "event: message\ndata: " + json.dumps(payload) + "\n\n"
        self.status_code = 200

    def raise_for_status(self) -> None:
        pass


def _tool_result(text: str) -> _Resp:
    return _Resp({"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": text}]}})


def test_small_results_pass_through():
    with patch("docs_client.requests.post", return_value=_tool_result("hello")):
        assert docs_client.filesystem("ls /") == {"ok": True, "result": "hello"}


def test_large_results_are_cut_with_a_hint():
    big = "x" * (docs_client.MAX_RESULT_CHARS + 500)
    with patch("docs_client.requests.post", return_value=_tool_result(big)):
        out = docs_client.filesystem("cat /big.mdx")
    assert out["ok"] and out["truncated"]
    assert len(out["result"]) == docs_client.MAX_RESULT_CHARS
    assert "rg -n" in out["note"]


def test_probe_lists_tools_from_tools_list():
    init = _Resp({"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "docs"}, "capabilities": {"tools": {"listChanged": True}}}})
    listed = _Resp({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "search_docs"}, {"name": "query_fs"}]}})
    with patch("docs_client.requests.post", side_effect=[init, listed]):
        out = docs_client.probe()
    assert out == {"connected": True, "server": {"name": "docs"}, "available_tools": ["search_docs", "query_fs"]}
