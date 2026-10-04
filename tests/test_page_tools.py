"""Landing-page tools (mcp_http/page_tools.py), with the Scanova API faked at requests.request.

The blocks are checked against qcg-backend's own schemas (src/page_blocks/),
so a page these tools save is one the backend will publish.
"""

import json

import pytest

import scanova_api
from mcp_http import page_tools as P
from mcp_http.annotations import annotations_for
from mcp_http.dispatcher import execute_tool
from mcp_http.normalizer import normalize

KEY = "key123"


class _Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = {"ok": True} if body is None else body
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


@pytest.fixture
def api(monkeypatch):
    calls, routes = [], {}

    def fake(method, url, headers=None, params=None, json=None, timeout=None):
        path = url.split("/", 3)[-1]
        calls.append({"method": method, "path": path, "body": json})
        answer = routes.get((method, path))
        if callable(answer):
            answer = answer(json)
        return answer if isinstance(answer, _Resp) else _Resp(body=answer)

    monkeypatch.setattr(scanova_api.requests, "request", fake)
    fake.calls, fake.routes = calls, routes
    return fake


def _page(blocks, theme_id=3, overrides=None, draft=True, category="dynamicText"):
    env = {"theme_id": theme_id, "theme_overrides": overrides or {}, "pageName": "Opening", "settings": {},
           "pages": [{"id": "main", "name": "Page 1", "type": "component", "data": {"blocks": blocks}}]}
    return {"qrid": "Qa1", "name": "Opening", "category": {"id": 9, "slug": category},
            "draft_info": json.dumps(env) if draft else None, "info": "[]" if draft else json.dumps(env),
            "dynamic_url_object": {"complete_url": "https://scnv.io/AbC"}}


def _block(id_, type_, **data):
    return {"id": id_, "type": type_, "data": {**P.blocks()[type_]["defaults"], **data}}


HERO = _block("b1", "page_title", title="Our Coffee Shop Opens in Pune", subtitle="20 October")
TEXT = _block("b2", "description_box", text="<p>Freshly brewed coffee.</p>")
BUTTON = _block("b3", "button", label="Get directions", link="https://maps.example.com/x")


def _saved(api):
    patch = [c for c in api.calls if c["method"] == "PATCH" and c["path"] == "qr/Qa1/"]
    return json.loads(patch[-1]["body"]["info"]) if patch else None


@pytest.fixture
def page(api):
    api.routes[("GET", "qr/Qa1/")] = _page([HERO, TEXT, BUTTON])
    api.routes[("PATCH", "qr/Qa1/")] = lambda body: {"qrid": "Qa1", "name": body.get("name") or "Opening"}
    api.routes[("POST", "qr/Qa1/preview-token/")] = {"token": "t0k", "complete_url": "https://scnv.io/AbC"}
    return api


# ── the block catalogue ────────────────────────────────────────────────────── #

def test_catalogue_leaves_out_special_and_script_blocks():
    assert {"page_title", "button", "map", "rsvp", "menu_info", "coupon_details"} <= set(P.blocks())
    assert not {"custom_script", "auto_redirect", "intro_page", "gs1_info"} & set(P.blocks())


def test_every_blocks_defaults_pass_the_backend_schema():
    for block_type, info in P.blocks().items():
        assert P.block_problems([{"id": "b1", "type": block_type, "data": info["defaults"]}]) == [], block_type


def test_problems_name_the_block_and_field_without_noise():
    bad = {**BUTTON, "data": {**BUTTON["data"], "link": "abc"}}
    assert P.block_problems([HERO, bad]) == ["block 2 (button, id b3): link: 'abc' is not valid under any of the given schemas"]


def test_blocks_listed_for_a_category():
    general = {b["type"] for b in execute_tool("list_page_blocks", {}, KEY)["data"]}
    restaurant = {b["type"] for b in execute_tool("list_page_blocks", {"category": "restaurant"}, KEY)["data"]}
    assert "menu_info" not in general and "menu_info" in restaurant
    assert "button" in general and "button" in restaurant


# ── reading a page ─────────────────────────────────────────────────────────── #

def test_get_page_outline_and_links(page):
    out = execute_tool("get_page", {"qrid": "Qa1"}, KEY)
    assert [(b["id"], b["label"], b.get("summary")) for b in out["blocks"]] == [
        ("b1", "Page Title", "Our Coffee Shop Opens in Pune"), ("b2", "Description", "Freshly brewed coffee."), ("b3", "Button", "Get directions")]
    assert out["builder_url"] == "https://app.scanova.io/qr/Qa1/landing"
    assert out["preview_url"] == "https://scnv.io/AbC?preview_token=t0k"
    assert out["has_unpublished_changes"] is True and "before_publishing" not in out
    assert normalize(out, "get_page")["ok"] is True  # lists in the result aren't a validation error


def test_a_published_page_reads_its_live_blocks(api):
    live = _page([HERO], draft=False)
    env = json.loads(live["info"])
    env["pages"][0]["blocks"] = env["pages"][0].pop("data")["blocks"]  # the published shape
    live["info"] = json.dumps(env)
    api.routes[("GET", "qr/Qa1/")] = live
    assert [b["id"] for b in execute_tool("get_page", {"qrid": "Qa1"}, KEY)["blocks"]] == ["b1"]


def test_a_code_without_a_builder_page_points_to_the_builder(api):
    api.routes[("GET", "qr/Qa1/")] = {"qrid": "Qa1", "info": '{"url": "https://x.com"}', "category": {"slug": "url"}}
    out = execute_tool("get_page", {"qrid": "Qa1"}, KEY)
    assert "Open it once in the builder" in out["error"]


# ── creating ───────────────────────────────────────────────────────────────── #

def test_create_page_saves_a_draft_in_the_builders_format(api):
    api.routes[("GET", "theme/")] = [{"id": 7, "slug": "mine", "is_system": False}, {"id": 3, "slug": "clean", "is_system": True}]
    api.routes[("GET", "qr/category/")] = {"Pages": [{"id": 9, "slug": "dynamicText"}, {"id": 20, "slug": "event"}]}
    api.routes[("POST", "qr/")] = lambda body: {"qrid": "Qn1", "name": body["name"], "category": {"slug": "dynamicText"}, "draft_info": body["info"]}
    out = execute_tool("create_page", {"name": "Grand opening", "blocks": [
        {"type": "page_title", "data": {"title": "We're open"}},
        {"type": "button", "data": {"label": "Directions", "link": "https://maps.example.com"}},
    ], "theme_values": {"color": {"accent": "#1F7A4D"}}}, KEY)
    post = next(c for c in api.calls if c["method"] == "POST" and c["path"] == "qr/")
    body = post["body"]
    assert (body["qr_type"], body["category"], body["is_draft"], body["name"]) == ("dy", 9, True, "Grand opening")
    env = json.loads(body["info"])
    assert env["theme_id"] == 3  # the first system theme, never another account's
    assert env["theme_overrides"] == {"color": {"accent": "#1F7A4D"}, "_v": 2}
    blocks = env["pages"][0]["data"]["blocks"]
    assert [b["type"] for b in blocks] == ["page_title", "button"]
    assert all(b["id"].startswith("b") for b in blocks) and blocks[0]["data"]["align"] == "center"  # defaults kept
    assert out["created"] is True and [b["type"] for b in out["blocks"]] == ["page_title", "button"]


def test_create_page_from_a_template(api):
    api.routes[("GET", "page-template/wed-royal-affair/")] = {"slug": "wed-royal-affair", "theme": {"id": 11, "slug": "noir"}, "blocks_json": {
        "theme_overrides": {}, "pages": [{"data": {"blocks": [{"type": "page_title", "data": {"title": "You're Invited"}}]}}]}}
    api.routes[("GET", "qr/category/")] = [{"id": 14, "slug": "wedding"}]
    api.routes[("POST", "qr/")] = lambda body: {"qrid": "Qn2", "category": {"slug": "wedding"}}
    execute_tool("create_page", {"name": "Our wedding", "category": "wedding", "template": "wed-royal-affair"}, KEY)
    env = json.loads(next(c for c in api.calls if c["path"] == "qr/")["body"]["info"])
    assert env["theme_id"] == 11 and env["pages"][0]["data"]["blocks"][0]["data"]["title"] == "You're Invited"
    assert env["pages"][0]["category"] == "wedding"


def test_create_page_refuses_a_block_from_another_category(api):
    out = execute_tool("create_page", {"blocks": [{"type": "menu_info"}]}, KEY)
    assert "only goes on restaurant pages" in out["error"]
    assert not [c for c in api.calls if c["method"] == "POST"]


# ── changing ───────────────────────────────────────────────────────────────── #

def test_add_update_move_remove_in_one_go(page):
    out = execute_tool("edit_page", {"qrid": "Qa1", "changes": [
        {"op": "add", "type": "map", "after": "b1", "data": {"title": "Find us"}},
        {"op": "update", "block": "b1", "data": {"subtitle": "Sunday 20 October, 8am"}},
        {"op": "move", "block": "b3", "position": 1},
        {"op": "remove", "block": "description_box"},
    ]}, KEY)
    blocks = _saved(page)["pages"][0]["data"]["blocks"]
    assert [b["type"] for b in blocks] == ["button", "page_title", "map"]
    assert blocks[1]["data"] == {**HERO["data"], "subtitle": "Sunday 20 October, 8am"}
    assert out["changed"][0].startswith("added Map") and out["has_unpublished_changes"] is True
    patch = next(c for c in page.calls if c["method"] == "PATCH")
    assert patch["body"]["is_draft"] is True and "publish" not in patch["body"]


def test_a_failed_change_saves_nothing(page):
    out = execute_tool("edit_page", {"qrid": "Qa1", "changes": [
        {"op": "remove", "block": "b2"},
        {"op": "update", "block": "nope", "data": {}},
    ]}, KEY)
    assert "Change 2 (update)" in out["error"] and "Nothing was changed" in out["error"]
    assert _saved(page) is None and len(out["blocks"]) == 3


def test_limits_and_categories_hold(page):
    out = execute_tool("edit_page", {"qrid": "Qa1", "changes": [{"op": "add", "type": "page_title"}]}, KEY)
    assert "most Page Title blocks" in out["error"]
    out = execute_tool("edit_page", {"qrid": "Qa1", "changes": [{"op": "add", "type": "rsvp"}]}, KEY)
    assert "only goes on wedding, event pages" in out["error"]
    assert _saved(page) is None


def test_null_removes_a_field(page):
    execute_tool("edit_page", {"qrid": "Qa1", "changes": [{"op": "update", "block": "b1", "data": {"subtitle": None}}]}, KEY)
    assert "subtitle" not in _saved(page)["pages"][0]["data"]["blocks"][0]["data"]


def test_switching_theme_and_theme_values(page):
    page.routes[("GET", "theme/forest/")] = {"id": 21, "slug": "forest", "name": "Forest"}
    execute_tool("edit_page", {"qrid": "Qa1", "changes": [
        {"op": "theme", "theme": "forest"},
        {"op": "theme_values", "values": {"color": {"accent": "#1F7A4D"}, "radius": {"button": "999px"}}},
    ]}, KEY)
    env = _saved(page)
    assert env["theme_id"] == 21
    assert env["theme_overrides"] == {"color": {"accent": "#1F7A4D"}, "radius": {"button": "999px"}, "_v": 2}


def test_bad_theme_values_are_refused(page):
    out = execute_tool("edit_page", {"qrid": "Qa1", "changes": [{"op": "theme_values", "values": {"color": {"accent": "green"}}}]}, KEY)
    assert "color.accent" in out["error"] and _saved(page) is None


def test_template_look_keeps_the_blocks_unless_asked(page):
    page.routes[("GET", "page-template/evt-neon/")] = {"theme": {"id": 30}, "blocks_json": {"theme_overrides": {"_v": 2, "color": {"accent": "#FF00AA"}},
        "pages": [{"data": {"blocks": [{"type": "page_title", "data": {"title": "Neon night"}}]}}]}}
    execute_tool("edit_page", {"qrid": "Qa1", "changes": [{"op": "template", "template": "evt-neon"}]}, KEY)
    env = _saved(page)
    assert env["theme_id"] == 30 and env["theme_overrides"]["color"]["accent"] == "#FF00AA"
    assert [b["id"] for b in env["pages"][0]["data"]["blocks"]] == ["b1", "b2", "b3"]
    execute_tool("edit_page", {"qrid": "Qa1", "changes": [{"op": "template", "template": "evt-neon", "keep_content": False}]}, KEY)
    assert [b["data"]["title"] for b in _saved(page)["pages"][0]["data"]["blocks"]] == ["Neon night"]


def test_rename_updates_the_codes_name(page):
    out = execute_tool("edit_page", {"qrid": "Qa1", "changes": [{"op": "rename", "name": "Pune opening"}]}, KEY)
    patch = next(c for c in page.calls if c["method"] == "PATCH")
    assert patch["body"]["name"] == "Pune opening" and out["name"] == "Pune opening"


# ── publishing and previews ────────────────────────────────────────────────── #

def test_publish_refuses_a_page_that_wont_pass(page):
    page.routes[("GET", "qr/Qa1/")] = _page([{**BUTTON, "data": {**BUTTON["data"], "link": "abc"}}])
    out = execute_tool("publish_page", {"qrid": "Qa1"}, KEY)
    assert "can't be published yet" in out["error"] and "link" in out["error"]
    assert not [c for c in page.calls if c["method"] == "PATCH"]


def test_publish_promotes_the_draft(page):
    page.routes[("PATCH", "qr/Qa1/")] = {"qrid": "Qa1", "dynamic_url_object": {"complete_url": "https://scnv.io/AbC"}}
    out = execute_tool("publish_page", {"qrid": "Qa1", "custom_domain_id": 4}, KEY)
    assert page.calls[-1]["body"] == {"publish": True, "custom_domain": 4}
    assert out == {"qrid": "Qa1", "published": True, "page_url": "https://scnv.io/AbC", "builder_url": "https://app.scanova.io/qr/Qa1/landing"}


def test_preview_image_when_the_backend_has_one(page):
    page.routes[("POST", "qr/Qa1/preview-image/")] = {"status": "warming"}
    assert "starting" in execute_tool("get_page_preview", {"qrid": "Qa1", "image": True}, KEY)["image_status"]
    page.routes[("POST", "qr/Qa1/preview-image/")] = {"image": "data:image/jpeg;base64,AAA"}
    assert execute_tool("get_page_preview", {"qrid": "Qa1", "image": True}, KEY)["image"].startswith("data:image/jpeg")
    page.routes[("POST", "qr/Qa1/preview-image/")] = _Resp(404, {"detail": "Not found."})
    out = execute_tool("get_page_preview", {"qrid": "Qa1", "image": True}, KEY)
    assert out["preview_url"].endswith("preview_token=t0k") and "image" not in out


# ── guards ─────────────────────────────────────────────────────────────────── #

@pytest.mark.parametrize("tool", sorted(P.PAGE_TOOL_NAMES))
def test_no_api_key_calls_nothing(api, tool):
    assert "error" in execute_tool(tool, {"qrid": "Qa1", "type": "button", "theme": "x", "template": "x", "changes": []}, None)
    assert api.calls == []


def test_ids_must_be_one_path_segment(api):
    assert "isn't a valid id" in execute_tool("get_page", {"qrid": "Qa/../../x"}, KEY)["error"]
    assert "isn't a valid id" in execute_tool("get_page_theme", {"theme": "1?x=1"}, KEY)["error"]
    assert api.calls == []
    api.routes[("GET", "qr/Qa1/")] = _page([HERO])
    out = execute_tool("edit_page", {"qrid": "Qa1", "changes": [{"op": "theme", "theme": "../user"}]}, KEY)
    assert "theme's id or slug" in out["error"]
    assert [c["path"] for c in api.calls] == ["qr/Qa1/"]


def test_safety_classes():
    for name in ("list_page_blocks", "get_page_block", "list_page_themes", "get_page_theme", "get_page_template", "get_page", "get_page_preview"):
        assert annotations_for(name)["readOnlyHint"] is True, name
    for name in ("create_page", "edit_page"):
        assert annotations_for(name)["destructiveHint"] is False, name
    assert annotations_for("publish_page")["destructiveHint"] is True
