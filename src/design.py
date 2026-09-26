"""
Human-friendly QR code design options and pattern_info builder.

All values sourced from the live Scanova docs MCP:
  https://docs.scanova.io/mcp → /api-reference/references/pattern-info.mdx
"""
import json

import requests

from config import SCANOVA_BASE_URL
from api_response import api_result

_BASE = SCANOVA_BASE_URL.rstrip("/")

# ---------------------------------------------------------------------------
# Design option catalogs (sourced from docs MCP pattern-info.mdx)
# ---------------------------------------------------------------------------

DATA_PATTERNS = [
    "Default", "Round", "RoundedCorners", "RotatedSquares", "connectedCircles",
    "Newone1", "Newone3", "circularDiagonal", "lightCircle", "lightSquare",
    "lightRoundedCorners", "lightCircleInSquare", "diamond", "stars", "heart",
    "cross", "signalGrid", "boltWeave", "starBurst", "metroPulse", "pulseBars",
]

GRADIENT_STYLES = ["None", "Horizontal", "Vertical", "Diagonal", "Radial"]

EYE_SHAPES = [
    "Shape0", "Shape1", "Shape2", "Shape3", "Shape4", "Shape5",
    "Shape6", "Shape7", "Shape8", "Shape9", "Shape10", "Shape15",
    "Shape30", "Shape31", "Shape32", "Shape33", "Shape35", "Shape36",
    "Shape38", "Shape39", "Shape40", "Shape41", "Shape42", "Shape43",
    "Shape44", "Shape45", "Shape46", "Shape47", "Shape48", "Shape49",
    "Shape50", "Shape51", "Shape52", "Shape53", "Shape54", "Shape55",
    "Shape57", "Shape58", "Shape59",
]

# Decorative shape containers that wrap the whole QR code
SHAPE_CONTAINER_IDS = ["1", "2", "3", "4", "5", "6", "7"]

# Frame IDs 1–5 (omit to have no frame)
FRAME_IDS = [1, 2, 3, 4, 5]

ERROR_CORRECTION_LEVELS = {
    "L": "Low — 7% recovery, highest data capacity",
    "M": "Medium — 15% recovery, default for most use cases",
    "Q": "Quartile — 25% recovery, recommended when adding a logo",
    "H": "High — 30% recovery, best for logo overlay (reduces data capacity)",
}

AVAILABLE_FONTS = [
    "Montserrat", "Inter", "Arial", "Roboto", "Noto Sans",
    "Times New Roman", "Brush Script MT", "Raleway",
    "Porsche Next", "Porsche Next Thin", "Porsche Next Bold",
    "American Typewriter", "Bungasai", "Copperplate",
]

TEXT_PLACEMENTS = [
    "center", "top", "bottom", "left", "right",
    "top-left", "top-right", "bottom-left", "bottom-right",
]

# Frame IDs that support custom text, keyed by QR category slug
FRAMES_WITH_CUSTOM_TEXT = {
    "businessCard": [1],
    "document": [3],
    "dynamicVCard": [1],
    "feedback": [3],
    "map": [6],
    "url": [10],
}

DESIGN_OPTIONS = {
    "data_patterns": DATA_PATTERNS,
    "gradient_styles": GRADIENT_STYLES,
    "eye_shapes": {
        "description": "Shape codes for the three corner finder patterns (TL, TR, BL). "
                       "Shape0–Shape10 are the standard set; Shape15–Shape59 are advanced styles. "
                       "Use get_design_docs to see visual examples.",
        "values": EYE_SHAPES,
    },
    "shape_container_ids": {
        "description": "Decorative outline/container wrapped around the entire QR code (optional). "
                       "IDs 1–7.",
        "values": SHAPE_CONTAINER_IDS,
    },
    "frame_ids": {
        "description": "Decorative frame/badge around the QR code (optional). IDs 1–5. "
                       "Omit or set to null for no frame.",
        "values": FRAME_IDS,
    },
    "error_correction": ERROR_CORRECTION_LEVELS,
    "available_fonts": AVAILABLE_FONTS,
    "text_placements": TEXT_PLACEMENTS,
    "frames_with_custom_text": FRAMES_WITH_CUSTOM_TEXT,
    "dot_scale": "Integer 10–100. Controls module (dot) size — lower = more spacing between dots.",
    "logo_url": "HTTPS URL of an image to embed in the QR center. Keep logo ≤ 30% of QR area.",
    "padding": "Integer — quiet zone margin around the QR code.",
    "background_color": "Hex #RRGGBB. Set to empty string '' for transparent background.",
    "tips": [
        "High contrast between start_color and background_color is critical for scan reliability.",
        "Use error_correction Q or H when embedding a logo.",
        "gradient_style 'None' with a single start_color = solid color (no gradient).",
        "eye_inner_color and eye_outer_color can be set independently for multi-tone eyes.",
        "frame_category should match the QR code type slug (e.g. 'url', 'document', 'map').",
        "frame_text is only supported on specific frame_id + frame_category combinations.",
        "shape_container wraps the entire QR; frame wraps just the QR scan area.",
    ],
}


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_pattern_info(
    pattern: str = "Default",
    start_color: str = "#000000",
    end_color: str = None,
    gradient_style: str = "None",
    dot_scale: int = None,
    background_color: str = "#ffffff",
    eye_shape: str = "Shape4",
    eye_inner_color: str = "#000000",
    eye_outer_color: str = "#000000",
    frame_id: int = None,
    frame_primary_color: str = None,
    frame_secondary_color: str = None,
    frame_text_color: str = "#FFFFFF",
    frame_bg_color: str = "#FFFFFF",
    frame_category: str = "url",
    frame_text: str = None,
    frame_text_placement: str = "center",
    frame_text_font: str = "Montserrat",
    shape_id: str = None,
    shape_stroke_color: str = None,
    shape_bg_color: str = "#FFFFFF",
    shape_pattern_color: str = "#000000",
    shape_stroke_width: int = 5,
    shape_margin: int = 5,
    error_correction: str = "M",
    logo_url: str = None,
    padding: int = None,
) -> str:
    """
    Build a pattern_info JSON string from human-friendly parameters.
    Pass only the parameters you want to customise — all have sensible defaults.
    """
    data_info: dict = {
        "pattern": pattern,
        "gradientStyle": gradient_style,
        "startColor": start_color,
        "endColor": end_color if end_color else start_color,
    }
    if dot_scale is not None:
        data_info["dotScale"] = max(10, min(100, int(dot_scale)))
    if logo_url is not None:
        data_info["logo"] = logo_url

    eye_entry = {
        "innerEyeColor": eye_inner_color,
        "outerEyeColor": eye_outer_color,
        "shape": eye_shape,
    }

    obj: dict = {
        "type": "qrcode",
        "version": "1.5",
        "backGroundColor": background_color,
        "dataInfo": data_info,
        "eyeInfo": {"TL": eye_entry, "TR": eye_entry, "BL": eye_entry},
        "errorCorrection": error_correction,
    }

    if frame_id is not None:
        frame: dict = {
            "id": frame_id,
            "primaryColor": frame_primary_color or start_color,
            "secondaryColor": frame_secondary_color,
            "textColor": frame_text_color,
            "bgColor": frame_bg_color,
            "category": frame_category,
        }
        if frame_text:
            frame["textConfig"] = {
                "text": frame_text,
                "placement": frame_text_placement,
                "fontFamily": frame_text_font,
            }
        obj["frame"] = frame

    if shape_id is not None:
        obj["shape"] = {
            "id": str(shape_id),
            "color": {
                "stroke": shape_stroke_color or start_color,
                "shapeBg": shape_bg_color,
                "pattern": shape_pattern_color,
            },
            "strokeWidth": shape_stroke_width,
            "margin": shape_margin,
        }

    if padding is not None:
        obj["padding"] = padding

    return json.dumps(obj)


# ---------------------------------------------------------------------------
# Apply design to an existing QR code
# ---------------------------------------------------------------------------

def extract_design_args(pi: dict) -> dict:
    """
    Reverse-map a parsed pattern_info dict back to build_pattern_info kwargs.
    Used by set_qr_design to preserve existing design settings before applying partial updates.
    """
    args: dict = {}
    di = pi.get("dataInfo", {})
    if "pattern" in di:         args["pattern"] = di["pattern"]
    if "startColor" in di:      args["start_color"] = di["startColor"]
    if "endColor" in di:        args["end_color"] = di["endColor"]
    if "gradientStyle" in di:   args["gradient_style"] = di["gradientStyle"]
    if "dotScale" in di:        args["dot_scale"] = di["dotScale"]
    if "logo" in di:            args["logo_url"] = di["logo"]
    if "backGroundColor" in pi: args["background_color"] = pi["backGroundColor"]
    if "errorCorrection" in pi: args["error_correction"] = pi["errorCorrection"]
    if "padding" in pi:         args["padding"] = pi["padding"]
    ei = pi.get("eyeInfo", {}).get("TL", {})
    if "shape" in ei:           args["eye_shape"] = ei["shape"]
    if "innerEyeColor" in ei:   args["eye_inner_color"] = ei["innerEyeColor"]
    if "outerEyeColor" in ei:   args["eye_outer_color"] = ei["outerEyeColor"]
    frame = pi.get("frame")
    if frame:
        if "id" in frame:              args["frame_id"] = frame["id"]
        if "primaryColor" in frame:    args["frame_primary_color"] = frame["primaryColor"]
        if "secondaryColor" in frame:  args["frame_secondary_color"] = frame["secondaryColor"]
        if "textColor" in frame:       args["frame_text_color"] = frame["textColor"]
        if "bgColor" in frame:         args["frame_bg_color"] = frame["bgColor"]
        if "category" in frame:        args["frame_category"] = frame["category"]
        tc = frame.get("textConfig")
        if tc:
            if "text" in tc:        args["frame_text"] = tc["text"]
            if "placement" in tc:   args["frame_text_placement"] = tc["placement"]
            if "fontFamily" in tc:  args["frame_text_font"] = tc["fontFamily"]
    shape = pi.get("shape")
    if shape:
        if "id" in shape:        args["shape_id"] = shape["id"]
        sc = shape.get("color", {})
        if "stroke" in sc:       args["shape_stroke_color"] = sc["stroke"]
        if "shapeBg" in sc:      args["shape_bg_color"] = sc["shapeBg"]
        if "pattern" in sc:      args["shape_pattern_color"] = sc["pattern"]
        if "strokeWidth" in shape: args["shape_stroke_width"] = shape["strokeWidth"]
        if "margin" in shape:    args["shape_margin"] = shape["margin"]
    return args


def apply_design(qrid: str, pattern_info_json: str, api_key: str) -> dict:
    """PATCH /qr/{qrid}/ — update only the pattern_info field."""
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    if not qrid:
        return {"error": "qrid is required"}
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    try:
        resp = requests.patch(
            f"{_BASE}/qr/{qrid}/",
            headers=headers,
            json={"pattern_info": pattern_info_json},
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
