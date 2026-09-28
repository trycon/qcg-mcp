"""Every tool belongs to exactly one toolset, and tools/list says which."""

import pytest

from mcp_http import toolsets as ts
from mcp_http.registry import list_mcp_tools

TOOLS = {t["name"]: t for t in list_mcp_tools()}


def test_every_tool_is_in_exactly_one_toolset():
    for name in TOOLS:
        assert sum(name in tools for _, _, tools in ts.TOOLSETS.values()) == 1, name
    grouped = set().union(*(tools for _, _, tools in ts.TOOLSETS.values()))
    assert grouped == set(TOOLS), f"grouped but not a tool: {sorted(grouped - set(TOOLS))}"


def test_ungrouped_tool_fails_loudly():
    with pytest.raises(KeyError):
        ts.toolset_for("brand_new_tool")


def test_descriptors_carry_their_toolset():
    for name, t in TOOLS.items():
        assert t["_meta"][ts.TOOLSET_META_KEY] == ts.toolset_for(name), name
    assert TOOLS["get_form_question_analytics"]["_meta"][ts.TOOLSET_META_KEY] == "forms"
    assert TOOLS["set_qr_design"]["_meta"][ts.TOOLSET_META_KEY] == "design"


def test_ui_meta_is_kept_alongside():
    with_ui = [t for t in TOOLS.values() if "ui" in t["_meta"]]
    for t in with_ui:
        assert ts.TOOLSET_META_KEY in t["_meta"] and t["_meta"]["ui"]["resourceUri"]


def test_every_toolset_is_labelled_and_used():
    for key, (label, description, tools) in ts.TOOLSETS.items():
        assert label and description and tools, key
