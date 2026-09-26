"""
Scan-safety checks for a QR design, and rendering through Scanova's generator.

Checks are plain code, not a model's opinion: colour contrast of the dots and
the three corner eyes against the background, error correction when there's a
logo, a transparent background. `verify_scans` goes further: it renders the
design with the same generator Scanova uses for downloads and decodes the
image, proving it scans and encodes the right content.
"""

import base64
import io
import json
import logging

import requests

from config import QCG_GENERATOR_URL

log = logging.getLogger("mcp.design_checks")

GENERATOR_TIMEOUT_S = 15
# Contrast ratio (WCAG formula) between dark parts and background. Low
# contrast on the dots (most of the code) is a failure; on the corner eyes it's
# a warning — a clean render may still decode (the scan test says), but print,
# glare and cheap cameras make low-contrast eyes the usual cause of misses.
FAIL_BELOW = 2.5
WARN_BELOW = 4.0


def _hex(color: str):
    c = (color or "").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return None
    try:
        return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _luminance(rgb) -> float:
    def ch(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_ratio(a: str, b: str):
    """WCAG contrast between two hex colours (1–21), or None if either isn't a colour."""
    ra, rb = _hex(a), _hex(b)
    if ra is None or rb is None:
        return None
    la, lb = _luminance(ra), _luminance(rb)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def check_design(pattern_info: dict) -> list:
    """
    Checks a pattern_info dict. Each result: {"check", "level": ok|warn|fail, "message"}.
    A `fail` means it's likely not to scan reliably; `warn` means it may struggle
    in some conditions.
    """
    results = []
    bg = pattern_info.get("backGroundColor", "#ffffff")
    di = pattern_info.get("dataInfo", {}) or {}
    transparent = bg in ("", None, "transparent")
    if transparent:
        results.append({
            "check": "background",
            "level": "warn",
            "message": "Transparent background: it only scans when printed on a plain, light surface.",
        })
        bg = "#ffffff"

    def contrast(check: str, what: str, color: str, hard: bool = True):
        ratio = contrast_ratio(color, bg)
        if ratio is None:
            return
        if ratio < FAIL_BELOW:
            level = "fail" if hard else "warn"
            advice = f"{what} ({color}) barely stands out from the background ({bg}): contrast {ratio}:1. It may not scan once printed or in poor light; a darker colour is much safer."
        elif ratio < WARN_BELOW:
            level, advice = "warn", f"{what} ({color}) has low contrast with the background ({bg}): {ratio}:1. It may not scan in poor light; a darker colour is safer."
        else:
            level, advice = "ok", f"{what}: contrast {ratio}:1."
        results.append({"check": check, "level": level, "message": advice, "ratio": ratio})

    contrast("dots", "The dots", di.get("startColor", "#000000"))
    if di.get("endColor") and di.get("endColor") != di.get("startColor"):
        contrast("dots_gradient", "The gradient's end colour", di["endColor"])
    eyes = pattern_info.get("eyeInfo", {}) or {}
    seen = set()
    for corner in ("TL", "TR", "BL"):
        eye = eyes.get(corner) or {}
        for part, label in (("outerEyeColor", "The outer corner eyes"), ("innerEyeColor", "The inner corner eyes")):
            color = eye.get(part)
            if color and (part, color) not in seen:
                seen.add((part, color))
                contrast(f"eyes_{part.replace('EyeColor', '')}", label, color, hard=False)

    # Light dots on a dark background: many scanner apps can't read inverted codes.
    dots = _hex(di.get("startColor", "#000000"))
    if dots and not transparent and _luminance(dots) > _luminance(_hex(bg) or (255, 255, 255)):
        results.append({
            "check": "inverted",
            "level": "warn",
            "message": "Light dots on a dark background: some phone cameras can't read inverted QR codes.",
        })

    if di.get("logo") and pattern_info.get("errorCorrection", "M") in ("L", "M"):
        results.append({
            "check": "logo",
            "level": "fail",
            "message": "A logo covers part of the code: use error correction Q or H so it still scans.",
        })
    return results


def render(content: str, pattern_info: dict, fmt: str = "png", size: int = 300) -> bytes:
    """Renders a design with Scanova's generator (the one downloads use). Raises on failure."""
    fmt = fmt if fmt in ("png", "svg", "jpg") else "png"
    size = max(300, min(6000, int(size)))
    resp = requests.post(
        f"{QCG_GENERATOR_URL.rstrip('/')}/v2/qrcode",
        params={"size": "custom", "custom_size": size, "format": fmt},
        data={"info": content, "patternInfo": json.dumps(pattern_info)},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=GENERATOR_TIMEOUT_S,
    )
    if not resp.ok:
        raise RuntimeError(f"generator answered {resp.status_code}")
    return resp.content


def data_uri(image: bytes, fmt: str = "png") -> str:
    mime = {"png": "image/png", "jpg": "image/jpeg", "svg": "image/svg+xml"}.get(fmt, "image/png")
    return f"data:{mime};base64,{base64.b64encode(image).decode()}"


def verify_scans(content: str, pattern_info: dict, png: bytes = None) -> dict:
    """
    Renders (unless given the PNG) and decodes the design. Returns
    {"scannable": True|False|None, "message"}; None when it couldn't be checked
    (the generator or the decoder unavailable) — never a false pass.
    """
    try:
        import zxingcpp
        from PIL import Image
    except ImportError:
        return {"scannable": None, "message": "Couldn't run the scan test here."}
    try:
        png = png or render(content, pattern_info, "png", 600)
    except Exception as e:
        log.warning("render for scan test failed: %s", e)
        return {"scannable": None, "message": "Couldn't render the design for a scan test just now."}
    image = Image.open(io.BytesIO(png)).convert("RGB")
    found = zxingcpp.read_barcodes(image)
    texts = [b.text for b in found]
    if content in texts:
        return {"scannable": True, "message": "Scan test passed: the design decodes to the right content."}
    if texts:
        return {"scannable": False, "message": "Scan test: it decodes, but not to the expected content."}
    return {"scannable": False, "message": "Scan test failed: a standard QR reader couldn't read this design."}


def summary(checks: list, scan: dict = None) -> dict:
    """Overall verdict: `safe` only with no failures and (when tested) a passing scan test."""
    fails = [c for c in checks if c["level"] == "fail"]
    warns = [c for c in checks if c["level"] == "warn"]
    scannable = (scan or {}).get("scannable")
    safe = not fails and scannable is not False
    if fails or scannable is False:
        verdict = "Not safe to use as is."
    elif warns:
        verdict = "Scans, with caveats — see the warnings."
    else:
        verdict = "Looks good to print."
    return {"safe": safe, "verdict": verdict, "failures": len(fails), "warnings": len(warns)}
