"""Scan-safety checks, the design preview (never saved) and set_qr_design's safety gate."""

import io
import json
from unittest.mock import patch

import zxingcpp
from PIL import Image

import design_checks as dc
from mcp_http.dispatcher import execute_tool

SCANOVA_EYES = {c: {"innerEyeColor": "#1D3A8A", "outerEyeColor": "#FCC305", "shape": "Shape4"} for c in ("TL", "TR", "BL")}
DESIGN = {"dataInfo": {"pattern": "Default", "gradientStyle": "None", "startColor": "#1D3A8A"}, "eyeInfo": SCANOVA_EYES, "backGroundColor": "#ffffff", "errorCorrection": "M"}


def qr_png(text: str) -> bytes:
    """A real QR code image, as a stand-in for the generator's render."""
    bc = zxingcpp.create_barcode(text, zxingcpp.BarcodeFormat.QRCode)
    img = bc.to_image(scale=8)
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="PNG") if not isinstance(img, Image.Image) else img.save(buf, format="PNG")
    return buf.getvalue()


def blank_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), "white").save(buf, format="PNG")
    return buf.getvalue()


def levels(pattern_info):
    return {c["check"]: c["level"] for c in dc.check_design(pattern_info)}


def test_contrast_ratio_is_the_wcag_one():
    assert dc.contrast_ratio("#000000", "#ffffff") == 21.0
    assert dc.contrast_ratio("#FCC305", "#ffffff") == 1.62
    assert dc.contrast_ratio("nope", "#ffffff") is None


def test_pale_eyes_warn_pale_dots_fail():
    assert levels(DESIGN) == {"dots": "ok", "eyes_outer": "warn", "eyes_inner": "ok"}
    pale_dots = {**DESIGN, "dataInfo": {**DESIGN["dataInfo"], "startColor": "#E8E8E8"}}
    assert levels(pale_dots)["dots"] == "fail"


def test_logo_needs_q_or_h_and_inverted_and_transparent_warn():
    logo = {**DESIGN, "dataInfo": {**DESIGN["dataInfo"], "logo": "https://x.test/l.png"}}
    assert levels(logo)["logo"] == "fail"
    assert "logo" not in levels({**logo, "errorCorrection": "H"})
    inverted = {**DESIGN, "dataInfo": {**DESIGN["dataInfo"], "startColor": "#ffffff"}, "backGroundColor": "#000000"}
    assert levels(inverted)["inverted"] == "warn"
    assert levels({**DESIGN, "backGroundColor": ""})["background"] == "warn"


def test_scan_test_decodes_the_render():
    assert dc.verify_scans("https://scnv.io/abc?qr=1", DESIGN, qr_png("https://scnv.io/abc?qr=1"))["scannable"] is True
    assert dc.verify_scans("https://scnv.io/abc?qr=1", DESIGN, qr_png("https://other.test"))["scannable"] is False
    assert dc.verify_scans("https://scnv.io/abc?qr=1", DESIGN, blank_png())["scannable"] is False
    # Can't render: unknown, never a pass.
    with patch("design_checks.render", side_effect=RuntimeError("down")):
        assert dc.verify_scans("https://x.test", DESIGN)["scannable"] is None


def test_summary_is_safe_only_without_failures_or_a_failed_scan():
    ok = [{"check": "dots", "level": "ok", "message": ""}]
    assert dc.summary(ok, {"scannable": True})["safe"] is True
    assert dc.summary([{"check": "eyes", "level": "warn", "message": ""}], {"scannable": True}) == {"safe": True, "verdict": "Scans, with caveats — see the warnings.", "failures": 0, "warnings": 1}
    assert dc.summary(ok, {"scannable": False})["safe"] is False
    assert dc.summary([{"check": "dots", "level": "fail", "message": ""}], {"scannable": None})["safe"] is False


def test_preview_renders_checks_and_never_saves():
    with patch("mcp_http.dispatcher.render", side_effect=lambda content, pi, fmt, size: qr_png(content)), patch("mcp_http.dispatcher.apply_design") as save:
        out = execute_tool("preview_qr_design", {"content": "https://menu.test", "start_color": "#1D3A8A", "eye_outer_color": "#FCC305"}, "key")
    save.assert_not_called()
    assert out["saved"] is False and out["content"] == "https://menu.test"
    assert out["pattern_info"]["eyeInfo"]["TL"]["outerEyeColor"] == "#FCC305"
    assert out["scan"]["scannable"] is True
    assert out["summary"]["warnings"] >= 1
    assert out["image"].startswith("data:image/png;base64,")
    assert execute_tool("preview_qr_design", {}, "key")["error"]


def test_preview_for_an_existing_code_merges_its_design_and_encodes_its_short_url():
    existing = {"qrid": "Q1", "pattern_info": json.dumps({**DESIGN, "dataInfo": {**DESIGN["dataInfo"], "pattern": "Round"}}), "dynamic_url_object": {"complete_url": "https://scnv.io/Q1"}}
    with patch("mcp_http.dispatcher.retrieve_qr_code", return_value=existing), patch("mcp_http.dispatcher.render", side_effect=lambda content, pi, fmt, size: qr_png(content)):
        out = execute_tool("preview_qr_design", {"qrid": "Q1", "eye_outer_color": "#000000", "render": False}, "key")
    assert out["content"] == "https://scnv.io/Q1?qr=1"
    assert out["pattern_info"]["dataInfo"]["pattern"] == "Round"  # kept
    assert "image" not in out  # the app draws it


def test_set_qr_design_refuses_an_unsafe_design_unless_accepted():
    existing = {"qrid": "Q1", "pattern_info": None, "dynamic_url_object": {"complete_url": "https://scnv.io/Q1"}}
    with patch("mcp_http.dispatcher.retrieve_qr_code", return_value=existing), patch("mcp_http.dispatcher.render", return_value=blank_png()), patch(
        "mcp_http.dispatcher.apply_design", return_value={"qrid": "Q1"}
    ) as save:
        refused = execute_tool("set_qr_design", {"qrid": "Q1", "start_color": "#EEEEEE"}, "key")
        assert "Not saved" in refused["error"]
        save.assert_not_called()
        accepted = execute_tool("set_qr_design", {"qrid": "Q1", "start_color": "#EEEEEE", "accept_risk": True}, "key")
        save.assert_called_once()
        assert accepted["design_checks"]["safe"] is False
    with patch("mcp_http.dispatcher.retrieve_qr_code", return_value=existing), patch("mcp_http.dispatcher.render", side_effect=lambda content, pi, fmt, size: qr_png(content)), patch(
        "mcp_http.dispatcher.apply_design", return_value={"qrid": "Q1"}
    ) as save:
        ok = execute_tool("set_qr_design", {"qrid": "Q1", "start_color": "#1D3A8A"}, "key")
        save.assert_called_once()
        assert ok["scan"]["scannable"] is True
