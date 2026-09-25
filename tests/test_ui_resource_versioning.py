"""Covers UI_ASSET_VERSION — the cache-busting mechanism for hosts (confirmed:
ChatGPT) that cache a resources/read response per URI for the life of a
conversation/connector. Bumping the version must make externally-emitted
URIs change while keeping internal lookups working for both the old
(unversioned or previously-versioned) and new URI forms."""

import mcp_http.sdk_server as sdk_server
from conftest import rpc
import mcp_http.ui_resources as ui_resources
from mcp_http.ui_resources import get_resource_by_uri, get_resource_for_tool


def test_versioned_uri_carries_the_version_suffix():
    resource = get_resource_for_tool("list_qr_codes")
    assert resource.versioned_uri == f"{resource.uri}?v={ui_resources.UI_ASSET_VERSION}"


def test_lookup_resolves_versioned_and_unversioned_uri_the_same_way():
    resource = get_resource_for_tool("list_qr_codes")
    assert get_resource_by_uri(resource.uri) is resource
    assert get_resource_by_uri(resource.versioned_uri) is resource
    assert get_resource_by_uri(f"{resource.uri}?v=999-some-old-version") is resource


def test_resources_list_emits_versioned_uris():
    result = rpc("resources/list", {"id": 1}, api_key=None)
    uris = {r["uri"] for r in result["result"]["resources"]}
    for resource in ui_resources.list_resources():
        assert resource.versioned_uri in uris
        assert resource.uri not in uris  # the bare, unversioned form should not be emitted


def test_resources_read_echoes_versioned_uri():
    resource = get_resource_for_tool("set_qr_design")
    body = {"id": 2, "params": {"uri": resource.uri}}
    result = rpc("resources/read", body, api_key=None)
    assert result["result"]["contents"][0]["uri"] == resource.versioned_uri


def test_bumping_version_changes_emitted_uri(monkeypatch):
    resource = get_resource_for_tool("set_qr_design")
    original = resource.versioned_uri
    monkeypatch.setattr(ui_resources, "UI_ASSET_VERSION", "999-test-bump")
    assert resource.versioned_uri != original
    assert resource.versioned_uri.endswith("?v=999-test-bump")
