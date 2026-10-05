"""Landing pages: build and change a QR code's page in the page builder's block format.

A page is an ordinary QR code (``qr_type: "dy"``) whose ``info`` is the page
builder's envelope — a theme, the customer's changes to it, and pages made of
``{id, type, data}`` blocks. These tools write the same envelope the builder
at app.scanova.io writes, so a page made here opens there and can be edited
block by block. Every change is saved as a draft (``is_draft``): the live page
only changes on ``publish_page``.

The blocks' rules come from Scanova's own sources, copied to page_blocks/ by
scripts/sync_page_blocks.py: the backend's JSON Schemas (what a page must
pass to publish) and the builder's block definitions (labels, limits, which
page categories a block belongs to, defaults). Changes are checked against
them before anything is saved.
"""

import copy
import html
import json
import re
import time
from functools import lru_cache
from pathlib import Path

import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from mcp_http.more_tools import _SEGMENT, MoreTool, _input, _missing, _object
from scanova_api import NO_KEY, scanova

_DIR = Path(__file__).resolve().parent.parent / "page_blocks"
_SCHEMAS = _DIR / "schemas"
BUILDER_URL = "https://app.scanova.io/qr/{qrid}/landing"
MAX_CHANGES = 40
# What the builder shows for an unnamed page.
DEFAULT_NAME = "Landing Page"


def _id_ok(value) -> bool:
    """Ids go into the request path, so each must be one plain path segment."""
    return bool(_SEGMENT.match(str(value).strip())) if value not in (None, "") else False


def _tool(*required: str, ids: tuple = ()):
    """A handler that needs an API key, its required arguments, and path-safe ids."""
    def wrap(fn):
        def run(a: dict, api_key: str):
            if not api_key:
                return NO_KEY
            if err := _missing(a, *required):
                return err
            for field in ids:
                if a.get(field) not in (None, "") and not _id_ok(a[field]):
                    return {"error": f"{field} isn't a valid id"}
            return fn(a, api_key)
        return run
    return wrap


@lru_cache(maxsize=1)
def blocks() -> dict:
    return json.loads((_DIR / "blocks.json").read_text())


# ── validation against the backend's schemas ──────────────────────────────── #

def _fix_fragments(node):
    """A few backend schema files write `x.json#properties/a` for `#/properties/a`; the backend repairs it the same way."""
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and "#" in ref:
            file_part, fragment = ref.split("#", 1)
            if fragment and not fragment.startswith("/"):
                node = {**node, "$ref": f"{file_part}#/{fragment}"}
        return {k: _fix_fragments(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_fix_fragments(v) for v in node]
    return node


def _load(path: Path) -> Resource:
    return Resource.from_contents(_fix_fragments(json.loads(path.read_text())), default_specification=DRAFT7)


def _file_registry(*search: Path) -> Registry:
    def retrieve(uri: str):
        path = Path(uri[len("file://"):] if uri.startswith("file://") else uri)
        if path.is_absolute() and path.exists():
            return _load(path)
        for base in search:
            if (base / path).exists():
                return _load(base / path)
        raise FileNotFoundError(uri)
    return Registry(retrieve=retrieve)


@lru_cache(maxsize=1)
def _blocks_validator():
    path = _SCHEMAS / "v2" / "page-types" / "component-page.json"
    schema = {**_fix_fragments(json.loads(path.read_text())), "$id": path.as_uri()}
    cls = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
    return cls(schema, registry=_file_registry(path.parent), format_checker=jsonschema.FormatChecker())


@lru_cache(maxsize=1)
def _theme_validator():
    base = _SCHEMAS / "theme"
    schema = json.loads((base / "theme_config_v2.json").read_text())
    cls = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
    return cls(schema, registry=_file_registry(base, _SCHEMAS / "categories" / "components"), format_checker=jsonschema.FormatChecker())


def _where(path) -> str:
    return ".".join(str(p) for p in path)


def block_problems(page_blocks: list) -> list[str]:
    """What stops these blocks publishing, as the backend would see it: one line per problem."""
    if not page_blocks:
        return ["The page has no blocks."]
    by_block: dict = {}
    for error in _blocks_validator().iter_errors(page_blocks):
        best = jsonschema.exceptions.best_match([error])
        path = list(best.absolute_path)
        if path and isinstance(path[0], int) and path[0] < len(page_blocks):
            block = page_blocks[path[0]]
            rest = path[2:] if len(path) > 1 and path[1] == "data" else path[1:]
            where = f'block {path[0] + 1} ({block.get("type")}, id {block.get("id")})'
            by_block.setdefault(path[0], []).append((best, f"{where}{': ' + _where(rest) if rest else ''}: {best.message}"))
        else:
            by_block.setdefault(None, []).append((best, best.message))
    problems = []
    for found in by_block.values():
        # A block that fails one part of its schema also reports every field as
        # "unevaluated"; that's noise beside the real problem.
        real = [msg for e, msg in found if e.validator != "unevaluatedProperties"]
        problems += real or [msg for _, msg in found]
    return sorted(set(problems))[:15]


def theme_problems(overrides: dict) -> list[str]:
    return sorted({
        f"{_where(e.absolute_path) or 'theme values'}: {e.message}"
        for e in _theme_validator().iter_errors(overrides)
    })[:15]


# ── the page document ──────────────────────────────────────────────────────── #

def _parsed(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return value


def envelope_of(qr: dict):
    """The page's envelope in the builder's draft shape (blocks under page.data.blocks): the draft if there is one, else the live page. None for a page the builder hasn't converted."""
    env = _parsed(qr.get("draft_info")) or _parsed(qr.get("info"))
    if not isinstance(env, dict) or not isinstance(env.get("pages"), list) or not env["pages"]:
        return None
    env = copy.deepcopy(env)
    for page in env["pages"]:
        data = page.get("data") if isinstance(page.get("data"), dict) else {}
        if "blocks" not in data and isinstance(page.get("blocks"), list):
            data["blocks"] = page.pop("blocks")
        data.setdefault("blocks", [])
        page["data"] = data
    env.setdefault("theme_overrides", {})
    return env


_counter = [0]


def new_block_id() -> str:
    """Same shape as the builder's makeBlockId: b<ms>-<n>."""
    _counter[0] += 1
    return f"b{int(time.time() * 1000)}-{_counter[0]}"


def _text(value) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip() if isinstance(value, str) else ""


_SUMMARY_KEYS = ("title", "heading", "label", "text", "first_name", "name", "description", "address", "code")


def _summary(data: dict) -> str:
    for key in _SUMMARY_KEYS:
        text = _text(data.get(key))
        if text:
            return text[:70]
    return ""


def outline(env: dict) -> list[dict]:
    pages = env.get("pages") or []
    rows = []
    for page in pages:
        for i, b in enumerate(page["data"]["blocks"], 1):
            row = {"id": b.get("id"), "type": b.get("type"), "label": (blocks().get(b.get("type")) or {}).get("label") or b.get("type"), "position": i}
            summary = _summary(b.get("data") or {})
            if summary:
                row["summary"] = summary
            if len(pages) > 1:
                row["page"] = page.get("name") or page.get("id")
            rows.append(row)
    return rows


def _category_slug(qr: dict) -> str:
    cat = qr.get("category")
    return (cat.get("slug") if isinstance(cat, dict) else None) or ""


def _allowed_here(block_type: str, category: str) -> bool:
    cats = (blocks().get(block_type) or {}).get("categories")
    return not cats or category in cats


def _merge(base, patch):
    """Merge `patch` into `base`: objects merge key by key, null removes a key, anything else replaces."""
    if not isinstance(base, dict) or not isinstance(patch, dict):
        return copy.deepcopy(patch)
    out = dict(base)
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = _merge(out.get(k), v)
    return out


def _resolve_theme(ref, api_key):
    """(theme, error) for a theme id or slug."""
    if not _id_ok(ref):
        return None, "Give a theme's id or slug."
    theme = scanova("GET", f"theme/{ref}/", api_key)
    if not isinstance(theme, dict) or "error" in theme or "id" not in theme:
        return None, f"There's no theme {ref!r} — list_page_themes shows the ones available."
    return theme, None


def _set_theme(env: dict, theme_id, config) -> None:
    """The theme, and its values as the builder keeps them in a draft (theme_config): Scanova's draft preview draws
    the page with them — without, a page that was never published previews in the default look."""
    env["theme_id"] = theme_id
    if isinstance(config, dict) and config:
        env["theme_config"] = copy.deepcopy(config)
    else:
        env.pop("theme_config", None)


def _template(slug, api_key):
    """(theme_id, theme_config, theme_overrides, blocks, error) for a page template."""
    if not _id_ok(slug):
        return None, None, None, None, "Give a template's slug."
    t = scanova("GET", f"page-template/{slug}/", api_key)
    if not isinstance(t, dict) or "error" in t:
        return None, None, None, None, f"There's no page template {slug!r} — list_page_templates shows them."
    raw = t.get("blocks_json")
    raw = _parsed(raw) if isinstance(raw, str) else raw
    if isinstance(raw, list):
        tpl_blocks, overrides = raw, {}
    else:
        raw = raw or {}
        first = (raw.get("pages") or [{}])[0]
        tpl_blocks = (first.get("data") or {}).get("blocks") or first.get("blocks") or []
        overrides = raw.get("theme_overrides") or {}
    theme = t.get("theme")
    theme_id = theme.get("id") if isinstance(theme, dict) else theme
    made = [{"id": new_block_id(), "type": b.get("type"), "data": copy.deepcopy(b.get("data") or {})} for b in tpl_blocks if b.get("type")]
    config = theme.get("config_json") if isinstance(theme, dict) and isinstance(theme.get("config_json"), dict) else None
    return theme_id, config, overrides, made, None


def _new_block(spec: dict, category: str):
    """(block, error) for {"type", "data"}: the builder's defaults with the given data merged over them."""
    block_type = spec.get("type")
    info = blocks().get(block_type)
    if not info:
        return None, f"{block_type!r} isn't a block type that can go on a page — list_page_blocks shows them."
    if not _allowed_here(block_type, category):
        return None, f"A {info['label']} block only goes on {', '.join(info['categories'])} pages, not this one ({category or 'custom'})."
    return {"id": new_block_id(), "type": block_type, "data": _merge(info.get("defaults") or {}, spec.get("data") or {})}, None


def _find(page_blocks: list, ref):
    """Index of the block `ref` names — its id, its type when only one block has it, or its position (1-based)."""
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        i = int(ref) - 1
        return i if 0 <= i < len(page_blocks) else None
    for i, b in enumerate(page_blocks):
        if b.get("id") == ref:
            return i
    matches = [i for i, b in enumerate(page_blocks) if b.get("type") == ref]
    return matches[0] if len(matches) == 1 else None


def _place(page_blocks: list, change: dict):
    """Where an added or moved block goes: after/before a block, a position, else the end. (index, error)"""
    if change.get("after") is not None:
        i = _find(page_blocks, change["after"])
        return (i + 1, None) if i is not None else (None, f"There's no block {change['after']!r} to put it after.")
    if change.get("before") is not None:
        i = _find(page_blocks, change["before"])
        return (i, None) if i is not None else (None, f"There's no block {change['before']!r} to put it before.")
    if change.get("position") is not None:
        return max(0, min(int(change["position"]) - 1, len(page_blocks))), None
    return len(page_blocks), None


def apply_changes(env: dict, changes: list, category: str, api_key: str):
    """Apply edit_page's changes to a copy of the envelope. (envelope, done, error) — nothing is applied on an error."""
    env = copy.deepcopy(env)
    page = env["pages"][0]
    page_blocks = page["data"]["blocks"]
    done = []
    for n, change in enumerate(changes, 1):
        op = change.get("op")
        ref = change.get("block")
        fail = lambda msg: (None, done, f"Change {n} ({op}): {msg} Nothing was changed.")  # noqa: E731
        if op == "add":
            block, err = _new_block(change, category)
            if err:
                return fail(err)
            limit = blocks()[block["type"]].get("limit")
            if limit and sum(1 for b in page_blocks if b.get("type") == block["type"]) >= limit:
                return fail(f"The page already has the most {blocks()[block['type']]['label']} blocks it can ({limit}); change that one instead.")
            at, err = _place(page_blocks, change)
            if err:
                return fail(err)
            page_blocks.insert(at, block)
            done.append(f"added {blocks()[block['type']]['label']} ({block['id']})")
        elif op in ("update", "replace", "remove", "move"):
            i = _find(page_blocks, ref)
            if i is None:
                return fail(f"There's no block {ref!r} on the page — use a block id from the outline.")
            block = page_blocks[i]
            label = (blocks().get(block.get("type")) or {}).get("label") or block.get("type")
            if op == "update":
                block["data"] = _merge(block.get("data") or {}, change.get("data") or {})
                done.append(f"changed {label}")
            elif op == "replace":
                block["data"] = _merge((blocks().get(block["type"]) or {}).get("defaults") or {}, change.get("data") or {})
                done.append(f"rewrote {label}")
            elif op == "remove":
                if (blocks().get(block.get("type")) or {}).get("removable") is False:
                    return fail(f"The {label} block can't be removed from this kind of page.")
                page_blocks.pop(i)
                done.append(f"removed {label}")
            else:
                moved = page_blocks.pop(i)
                at, err = _place(page_blocks, change)
                if err:
                    return fail(err)
                page_blocks.insert(at, moved)
                done.append(f"moved {label} to position {at + 1}")
        elif op == "theme":
            theme, err = _resolve_theme(change.get("theme"), api_key)
            if err:
                return fail(err)
            _set_theme(env, theme["id"], theme.get("config_json"))
            if not change.get("keep_values"):
                env["theme_overrides"] = {}
            done.append(f"theme set to {theme.get('name')}")
        elif op == "theme_values":
            values = change.get("values")
            if not isinstance(values, dict) or not values:
                return fail("Give the theme values to change, e.g. {\"color\": {\"accent\": \"#1F7A4D\"}}.")
            merged = _merge(env.get("theme_overrides") or {}, {**values, "_v": 2})
            problems = theme_problems(merged)
            if problems:
                return fail("Those theme values aren't valid: " + "; ".join(problems))
            env["theme_overrides"] = merged
            done.append("theme values changed")
        elif op == "template":
            theme_id, config, overrides, tpl_blocks, err = _template(change.get("template"), api_key)
            if err:
                return fail(err)
            _set_theme(env, theme_id, config)
            env["theme_overrides"] = overrides or {}
            if change.get("keep_content", True):
                done.append(f"took the look of template {change.get('template')} (blocks kept)")
            else:
                page["data"]["blocks"] = page_blocks = tpl_blocks
                done.append(f"replaced the page with template {change.get('template')}")
        elif op == "rename":
            if not (change.get("name") or "").strip():
                return fail("Give the new name.")
            env["pageName"] = change["name"].strip()
            done.append(f"renamed to {env['pageName']}")
        elif op == "seo":
            seo = {k: change[k] for k in ("title", "description") if change.get(k) is not None}
            page["settings"] = _merge(page.get("settings") or {}, {"seo": seo})
            done.append("search and sharing details changed")
        else:
            return fail("Unknown change — use add, update, replace, remove, move, theme, theme_values, template, rename or seo.")
    return env, done, None


# ── talking to Scanova ─────────────────────────────────────────────────────── #

def _failed(result) -> bool:
    return not isinstance(result, dict) or "error" in result


def _links(qrid: str, api_key: str, draft: bool = False) -> dict:
    # With a draft, the builder opens it directly (?draft=continue) instead of asking "draft or live page?".
    links = {"builder_url": BUILDER_URL.format(qrid=qrid) + ("?draft=continue" if draft else "")}
    token = scanova("POST", f"qr/{qrid}/preview-token/", api_key, body={})
    if not _failed(token) and token.get("token") and token.get("complete_url"):
        sep = "&" if "?" in token["complete_url"] else "?"
        links["preview_url"] = f"{token['complete_url']}{sep}preview_token={token['token']}"
        links["preview_expires"] = "in 1 hour"
    return links


def _page_report(qr: dict, env: dict, api_key: str, **extra) -> dict:
    qrid = qr.get("qrid")
    duo = qr.get("dynamic_url_object") if isinstance(qr.get("dynamic_url_object"), dict) else {}
    report = {
        "qrid": qrid,
        "name": qr.get("name"),
        "category": _category_slug(qr) or None,
        "theme_id": env.get("theme_id"),
        "theme_values": {k: v for k, v in (env.get("theme_overrides") or {}).items() if k != "_v"},
        "blocks": outline(env),
        "has_unpublished_changes": bool(qr.get("draft_info")),
        "published": bool(qr.get("published_at")),
        "page_url": duo.get("complete_url"),
        **_links(qrid, api_key, draft=bool(qr.get("draft_info"))),
        **extra,
    }
    problems = block_problems(env["pages"][0]["data"]["blocks"])
    if problems:
        report["before_publishing"] = problems
    return report


def _get_page(qrid, api_key):
    """(qr, envelope, error)"""
    qr = scanova("GET", f"qr/{qrid}/", api_key)
    if _failed(qr):
        return None, None, f"There's no QR code {qrid!r} in this account."
    env = envelope_of(qr)
    if env is None:
        return qr, None, (
            "This QR code doesn't have a page in the page builder's format (it's a different kind of code, "
            f"or a page made in the older builder). Open it once in the builder to convert it: {BUILDER_URL.format(qrid=qrid)}"
        )
    return qr, env, None


def _save_draft(qrid, env, api_key, name=None):
    body = {"info": json.dumps(env), "is_draft": True}
    if name:
        body["name"] = name
    return scanova("PATCH", f"qr/{qrid}/", api_key, body=body)


@_tool("qrid", ids=('qrid',))
def get_page(a: dict, api_key: str):
    qr, env, err = _get_page(a["qrid"], api_key)
    if err:
        return {"error": err}
    report = _page_report(qr, env, api_key)
    if a.get("include_block_data"):
        report["block_data"] = {b["id"]: b.get("data") for b in env["pages"][0]["data"]["blocks"]}
    return report


def _category_id(slug: str, api_key: str):
    groups = scanova("GET", "qr/category/", api_key)
    cats = [c for g in groups.values() for c in g] if isinstance(groups, dict) and "error" not in groups else groups if isinstance(groups, list) else []
    for c in cats:
        if isinstance(c, dict) and c.get("slug") == slug:
            return c.get("id")
    return None


PAGE_CATEGORIES = ["dynamicText", "event", "wedding", "restaurant", "businessCard", "feedback", "realEstate", "coupon", "product", "linkPage"]


@_tool()
def create_page(a: dict, api_key: str):
    category = a.get("category") or "dynamicText"
    if category not in PAGE_CATEGORIES:
        return {"error": f"category must be one of {', '.join(PAGE_CATEGORIES)} (dynamicText is a general page)."}
    theme_id, theme_config, overrides, page_blocks = None, None, {}, []
    if a.get("template"):
        theme_id, theme_config, overrides, page_blocks, err = _template(a["template"], api_key)
        if err:
            return {"error": err}
    if a.get("theme"):
        theme, err = _resolve_theme(a["theme"], api_key)
        if err:
            return {"error": err}
        theme_id, theme_config = theme["id"], theme.get("config_json")
    if a.get("blocks"):
        page_blocks = []
        for spec in a["blocks"]:
            block, err = _new_block(spec, category)
            if err:
                return {"error": err + " Nothing was created."}
            page_blocks.append(block)
    if not page_blocks:
        return {"error": "Give the page's blocks, or a template to start from."}
    if a.get("theme_values"):
        overrides = _merge(overrides or {}, {**a["theme_values"], "_v": 2})
        problems = theme_problems(overrides)
        if problems:
            return {"error": "Those theme values aren't valid: " + "; ".join(problems) + ". Nothing was created."}
    if theme_id is None:
        themes = scanova("GET", "theme/", api_key)
        system = [t for t in themes if isinstance(t, dict) and t.get("is_system")] if isinstance(themes, list) else []
        if not system:
            return {"error": "Couldn't load the themes to start the page with; give a theme or a template."}
        theme_id, theme_config = system[0]["id"], system[0].get("config_json")
    name = (a.get("name") or "").strip() or DEFAULT_NAME
    env = {
        "theme_overrides": overrides or {},
        "pageName": name,
        "settings": {"nav": "none", "navItems": []},
        "iconImages": [],
        "pages": [{"id": "main", "name": "Page 1", "type": "component", "category": category, "data": {"blocks": page_blocks}}],
    }
    _set_theme(env, theme_id, theme_config)
    category_id = _category_id(category, api_key)
    if category_id is None:
        return {"error": f"Couldn't find the {category} category in this account."}
    body = {"name": name, "category": category_id, "qr_type": "dy", "info": json.dumps(env), "is_draft": True}
    if a.get("custom_domain_id"):
        body["custom_domain"] = a["custom_domain_id"]
    qr = scanova("POST", "qr/", api_key, body=body)
    if _failed(qr):
        return qr if isinstance(qr, dict) else {"error": "Scanova didn't create the page."}
    return _page_report(qr, env, api_key, created=True)


@_tool("qrid", "changes", ids=('qrid',))
def edit_page(a: dict, api_key: str):
    changes = a["changes"]
    if not isinstance(changes, list) or len(changes) > MAX_CHANGES:
        return {"error": f"changes must be a list of at most {MAX_CHANGES} changes."}
    qr, env, err = _get_page(a["qrid"], api_key)
    if err:
        return {"error": err}
    new_env, done, err = apply_changes(env, changes, _category_slug(qr), api_key)
    if err:
        return {"error": err, "blocks": outline(env)}
    saved = _save_draft(a["qrid"], new_env, api_key, name=new_env.get("pageName") if new_env.get("pageName") != env.get("pageName") else None)
    if _failed(saved):
        return saved if isinstance(saved, dict) else {"error": "Scanova didn't save the change."}
    qr = {**qr, "name": saved.get("name") or qr.get("name"), "draft_info": json.dumps(new_env)}
    return _page_report(qr, new_env, api_key, changed=done)


@_tool("qrid", ids=('qrid',))
def publish_page(a: dict, api_key: str):
    qr, env, err = _get_page(a["qrid"], api_key)
    if err:
        return {"error": err}
    problems = block_problems(env["pages"][0]["data"]["blocks"])
    if problems:
        return {"error": "The page can't be published yet: " + "; ".join(problems), "blocks": outline(env)}
    if not qr.get("draft_info"):
        # Publish promotes the saved draft; save the current page as one first.
        saved = _save_draft(a["qrid"], env, api_key)
        if _failed(saved):
            return saved
    body = {"publish": True}
    if a.get("custom_domain_id"):
        body["custom_domain"] = a["custom_domain_id"]
    result = scanova("PATCH", f"qr/{a['qrid']}/", api_key, body=body)
    if _failed(result):
        return result if isinstance(result, dict) else {"error": "Scanova didn't publish the page."}
    duo = result.get("dynamic_url_object") if isinstance(result.get("dynamic_url_object"), dict) else {}
    return {"qrid": a["qrid"], "published": True, "page_url": duo.get("complete_url"), "builder_url": BUILDER_URL.format(qrid=a["qrid"])}


@_tool("qrid", ids=('qrid',))
def get_page_preview(a: dict, api_key: str):
    links = _links(a["qrid"], api_key, draft=True)
    if "preview_url" not in links:
        return {"error": f"Couldn't make a preview link for {a['qrid']!r}."}
    if a.get("image"):
        shot = scanova("POST", f"qr/{a['qrid']}/preview-image/", api_key, body={})
        if not _failed(shot) and isinstance(shot.get("image"), str) and shot["image"].startswith("data:image/"):
            links["image"] = shot["image"]
        elif not _failed(shot) and shot.get("status") == "warming":
            links["image_status"] = "The screenshot service is starting; ask again in a minute."
        else:
            links["image_status"] = "No screenshot available; use the preview link."
    return links


@_tool()
def list_page_blocks(a: dict, api_key: str):
    category = a.get("category") or "dynamicText"
    return {"category": category, "data": [
        {"type": t, "label": b["label"], "description": b["description"], "limit": b.get("limit"), "removable": b.get("removable", True)}
        for t, b in blocks().items() if _allowed_here(t, category)
    ]}


MAX_BLOCK_TYPES = 10


def _block_info(block_type: str):
    b = blocks().get(block_type)
    if not b:
        return None
    schema_path = _SCHEMAS / "v2" / "components" / f"{block_type}.json"
    if not schema_path.exists():
        schema_path = _SCHEMAS / "categories" / "components" / f"{block_type}.json"
    schema = json.loads(schema_path.read_text()) if schema_path.exists() else None
    return {"type": block_type, **b, "data_schema": _compact_schema(schema, schema_path.parent)}


_STYLE_KEYS = {"cardStyle", "textStyle", "layout", "formatting", "tracking", "buttonStyle", "subtitleStyle"}


def _compact_schema(schema, base: Path | None = None):
    """The block's data contract without the noise: its own fields (types, allowed values, limits, which are
    required); styling objects and long comments left out — the full file is the backend's, and saves still validate
    against it."""
    if not isinstance(schema, dict):
        return None
    parts = [schema, *[x for x in schema.get("allOf", []) if isinstance(x, dict)]]
    # A shared base it builds on (button → _base_button.json): its fields count too.
    for part in list(parts):
        ref = part.get("$ref")
        if base and isinstance(ref, str) and ref.endswith(".json") and "/" not in ref and (base / ref).exists():
            shared = json.loads((base / ref).read_text())
            parts += [shared, *[x for x in shared.get("allOf", []) if isinstance(x, dict)]]
    props, required = {}, []
    for part in parts:
        required += [r for r in part.get("required", []) if isinstance(r, str)]
        for name, spec in (part.get("properties") or {}).items():
            if name in _STYLE_KEYS or not isinstance(spec, dict):
                continue
            keep = {k: spec[k] for k in ("type", "enum", "maxLength", "minLength", "maxItems", "format", "const") if k in spec}
            if "$ref" in spec:
                keep["ref"] = spec["$ref"].split("/")[-1].removesuffix(".json")
            if isinstance(spec.get("items"), dict):
                item = spec["items"]
                keep["items"] = {k: item[k] for k in ("type", "enum") if k in item} or {"ref": str(item.get("$ref", "")).split("/")[-1].removesuffix(".json")}
                if isinstance(item.get("properties"), dict):
                    keep["items"]["properties"] = sorted(item["properties"])
            if isinstance(spec.get("properties"), dict):
                keep["properties"] = sorted(k for k in spec["properties"] if k not in _STYLE_KEYS)
            if isinstance(spec.get("description"), str) and len(spec["description"]) <= 120:
                keep["description"] = spec["description"]
            props[name] = keep
    return {"required": sorted(set(required)), "properties": props}


@_tool()
def get_page_block(a: dict, api_key: str):
    """One block type (`type`), or several at once (`types`) — one call instead of one per block."""
    wanted = a.get("types") if isinstance(a.get("types"), list) else [a.get("type")] if a.get("type") else []
    wanted = [t for t in dict.fromkeys(str(t) for t in wanted if t)][:MAX_BLOCK_TYPES]
    if not wanted:
        return {"error": "type (or types) is required"}
    found = [info for info in map(_block_info, wanted) if info]
    unknown = [t for t in wanted if not blocks().get(t)]
    if not found:
        return {"error": f"{', '.join(map(repr, unknown))} isn't a page block — list_page_blocks shows them."}
    if not isinstance(a.get("types"), list):
        return found[0]
    return {"data": found, **({"unknown": unknown} if unknown else {})}


@_tool()
def list_page_themes(a: dict, api_key: str):
    themes = scanova("GET", "theme/", api_key)
    if _failed(themes) and not isinstance(themes, list):
        return themes
    rows = []
    for t in themes if isinstance(themes, list) else []:
        color = ((t.get("config_json") or {}).get("color") or {})
        rows.append({
            "id": t.get("id"), "slug": t.get("slug"), "name": t.get("name"), "description": t.get("description"),
            "mine": not t.get("is_system"), "premium": bool(t.get("is_premium")), "suits": t.get("category_hints") or [],
            "colors": {k: color.get(k) for k in ("background", "surface", "title", "body", "accent") if color.get(k)},
        })
    return {"data": rows}


@_tool("theme", ids=('theme',))
def get_page_theme(a: dict, api_key: str):
    theme, err = _resolve_theme(a["theme"], api_key)
    if err:
        return {"error": err}
    return {k: theme.get(k) for k in ("id", "slug", "name", "description", "category_hints", "is_system", "is_premium", "config_json")}


@_tool("template", ids=('template',))
def get_page_template(a: dict, api_key: str):
    t = scanova("GET", f"page-template/{a['template']}/", api_key)
    if _failed(t):
        return {"error": f"There's no page template {a['template']!r} — list_page_templates shows them."}
    theme_id, _config, overrides, tpl_blocks, _ = _template(a["template"], api_key)
    theme = t.get("theme") if isinstance(t.get("theme"), dict) else {}
    return {
        "slug": t.get("slug"), "name": t.get("name"), "description": t.get("description"),
        "theme": {"id": theme_id, "slug": theme.get("slug"), "name": theme.get("name")},
        "theme_values": overrides,
        "blocks": [{"type": b["type"], "data": b["data"]} for b in tpl_blocks or []],
    }


# ── tool declarations ──────────────────────────────────────────────────────── #

_QRID = {"type": "string", "description": "The page's QR code id (qrid)"}
_BLOCK_REF = {"type": ["string", "integer"], "description": "A block's id from the page outline (or its position, 1 = first)"}
_DATA = {"type": "object", "description": "The block's data — the fields get_page_block lists for its type"}
_CHANGE = {
    "type": "object",
    "properties": {
        "op": {"type": "string", "enum": ["add", "update", "replace", "remove", "move", "theme", "theme_values", "template", "rename", "seo"]},
        "type": {"type": "string", "description": "add: the block type"},
        "data": _DATA,
        "block": _BLOCK_REF,
        "after": _BLOCK_REF, "before": _BLOCK_REF,
        "position": {"type": "integer", "minimum": 1},
        "theme": {"type": ["string", "integer"], "description": "theme: a theme id or slug"},
        "keep_values": {"type": "boolean", "description": "theme: keep the page's own theme values (default false)"},
        "values": {"type": "object", "description": "theme_values: the theme values to change, nested like the theme's config (color.accent, radius.button, typography.title.fontFamily…); null removes one"},
        "template": {"type": "string", "description": "template: the template's slug"},
        "keep_content": {"type": "boolean", "description": "template: true (default) takes only its look; false replaces the blocks too"},
        "name": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"},
    },
    "required": ["op"],
}
_PAGE_OUT = _object({
    "qrid": {"type": "string"}, "blocks": {"type": "array"}, "builder_url": {"type": "string"},
    "preview_url": {"type": "string"}, "page_url": {"type": ["string", "null"]},
})

PAGE_TOOLS: list[MoreTool] = [
    MoreTool(
        "list_page_blocks", "List page blocks",
        "The blocks a landing page can have (hero, title, text, buttons, map, video, coupon, RSVP…) for a page category, with what each is for and how many a page can hold.",
        "Landing pages", "(local)",
        _input({"category": {"type": "string", "enum": PAGE_CATEGORIES, "description": "The page's category (default dynamicText, a general page)"}}),
        _object({"data": {"type": "array"}}), list_page_blocks,
    ),
    MoreTool(
        "get_page_block", "Get page blocks' fields",
        "Block types' fields, defaults and data schema — what to put in `data` when adding or changing them. Ask for every type you need at once with `types`.",
        "Landing pages", "(local)",
        _input({
            "type": {"type": "string", "description": "One block type"},
            "types": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_BLOCK_TYPES, "description": "Several block types at once"},
        }), _object(), get_page_block,
    ),
    MoreTool(
        "list_page_themes", "List page themes",
        "The themes a landing page can use, with their main colours and the kinds of page each suits.",
        "Landing pages", "theme/", _input(), _object({"data": {"type": "array"}}), list_page_themes,
    ),
    MoreTool(
        "get_page_theme", "Get a page theme",
        "One theme's full values (colours, fonts, corner radius, shadows, spacing, background) — what theme values a page can change.",
        "Landing pages", "theme/{theme}/", _input({"theme": {"type": ["string", "integer"], "description": "Theme id or slug"}}, ("theme",)), _object(), get_page_theme,
    ),
    MoreTool(
        "get_page_template", "Get a page template",
        "One landing page template's theme and blocks.",
        "Landing pages", "page-template/{template}/", _input({"template": {"type": "string", "description": "Template slug"}}, ("template",)), _object(), get_page_template,
    ),
    MoreTool(
        "get_page", "Get a landing page",
        "A QR code's landing page: its blocks in order (with ids to change them by), theme and theme values, whether it has unpublished changes, a preview link and a link to open it in the page builder.",
        "Landing pages", "qr/{qrid}/",
        _input({"qrid": _QRID, "include_block_data": {"type": "boolean", "description": "Also return every block's data"}}, ("qrid",)),
        _PAGE_OUT, get_page,
    ),
    MoreTool(
        "create_page", "Create a landing page",
        "Create a QR code with a landing page, as a draft (nothing is live until publish_page). Start from a template, or give the blocks; optionally a theme and theme values. Returns the outline, a preview link and a link to open it in the page builder.",
        "Landing pages", "qr/",
        _input({
            "name": {"type": "string"},
            "category": {"type": "string", "enum": PAGE_CATEGORIES, "description": "dynamicText (default) is a general page; others unlock their own blocks (e.g. RSVP on event/wedding, menu on restaurant)"},
            "template": {"type": "string", "description": "A template slug to start from"},
            "blocks": {"type": "array", "items": {"type": "object", "properties": {"type": {"type": "string"}, "data": _DATA}, "required": ["type"]}},
            "theme": {"type": ["string", "integer"], "description": "Theme id or slug"},
            "theme_values": {"type": "object", "description": "Theme values to change, nested like the theme's config"},
            "custom_domain_id": {"type": "integer"},
        }),
        _PAGE_OUT, create_page,
    ),
    MoreTool(
        "edit_page", "Change a landing page",
        "Change a landing page's draft in one go: add, change, rewrite, remove or move blocks; switch theme; change theme values; take a template's look (or its whole layout); rename; set search/sharing details. All changes apply or none do. The live page doesn't change until publish_page.",
        "Landing pages", "qr/{qrid}/",
        _input({"qrid": _QRID, "changes": {"type": "array", "items": _CHANGE, "maxItems": MAX_CHANGES}}, ("qrid", "changes")),
        _PAGE_OUT, edit_page,
    ),
    MoreTool(
        "get_page_preview", "Preview a landing page",
        "A link (valid 1 hour) showing the page's latest draft exactly as visitors would see it; optionally a phone-sized screenshot.",
        "Landing pages", "qr/{qrid}/preview-token/",
        _input({"qrid": _QRID, "image": {"type": "boolean", "description": "Also return a screenshot (may take up to a minute the first time)"}}, ("qrid",)),
        _object({"preview_url": {"type": "string"}, "builder_url": {"type": "string"}}), get_page_preview,
    ),
    MoreTool(
        "publish_page", "Publish a landing page",
        "Make the page's draft live: everyone scanning the QR code sees it from now on.",
        "Landing pages", "qr/{qrid}/",
        _input({"qrid": _QRID, "custom_domain_id": {"type": "integer", "description": "Publish on this custom domain"}}, ("qrid",)),
        _object({"page_url": {"type": ["string", "null"]}}), publish_page,
    ),
]

PAGE_TOOL_NAMES = frozenset(t.name for t in PAGE_TOOLS)
