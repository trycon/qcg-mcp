"""Every tool is explicitly classified, and the classes follow the spec."""

import pytest

from mcp_http import annotations as ann
from mcp_http.registry import list_mcp_tools

TOOLS = {t["name"]: t for t in list_mcp_tools()}


def test_every_tool_has_exactly_one_class():
    classes = [ann.READ_ONLY, ann.ADDITIVE, ann.DESTRUCTIVE]
    for name in TOOLS:
        assert sum(name in c for c in classes) == 1, name
    listed = ann.READ_ONLY | ann.ADDITIVE | ann.DESTRUCTIVE
    assert listed == set(TOOLS), f"classified but not a tool: {sorted(listed - set(TOOLS))}"


def test_unclassified_tool_fails_loudly():
    with pytest.raises(KeyError):
        ann.annotations_for("brand_new_tool")


@pytest.mark.parametrize("name", sorted(ann.DESTRUCTIVE))
def test_destructive_tools_say_so(name):
    a = TOOLS[name]["annotations"]
    assert a["destructiveHint"] is True and a["readOnlyHint"] is False


def test_things_that_change_live_codes_or_access_need_confirmation():
    for name in ("update_qr_code", "set_qr_design", "deactivate_qr_code", "update_user_role", "detach_form_from_qr"):
        assert TOOLS[name]["annotations"]["destructiveHint"] is True, name


def test_read_only_and_additive_tools_are_not_destructive():
    for name in ann.READ_ONLY | ann.ADDITIVE:
        assert TOOLS[name]["annotations"]["destructiveHint"] is False, name
    for name in ann.READ_ONLY:
        assert TOOLS[name]["annotations"]["readOnlyHint"] is True, name


def test_creates_are_not_idempotent():
    for name in ("create_qr_code", "create_folder", "create_form", "add_user"):
        assert TOOLS[name]["annotations"]["idempotentHint"] is False, name
