import base64
import json
import requests
from config import SCANOVA_BASE_URL
from api_response import api_result

_BASE = SCANOVA_BASE_URL.rstrip("/")


def get_url_from_user():
    """
    Prompt the user to enter a URL and name for QR code creation.
    
    This function interactively asks the user for:
    1. A URL to encode in the QR code
    2. A name for the QR code (optional, defaults to 'qrcode')
    
    The function automatically adds 'http://' prefix to URLs if not present.
    
    Returns:
        tuple: A tuple containing (url, name) where:
            - url (str): The URL to encode in the QR code
            - name (str): The name for the QR code
    
    Raises:
        ValueError: If no URL is provided by the user
    
    Example:
        >>> url, name = get_url_from_user()
        Enter the URL you want to encode in the QR code:
        URL: google.com
        Enter a name for the QR code (press Enter for default 'qrcode'):
        Name: my-google-qr
        >>> print(url, name)
        http://google.com my-google-qr
    """
    print("Enter the URL you want to encode in the QR code:")
    url = input("URL: ").strip()
    
    if not url:
        raise ValueError("URL is required to create a QR code")
    
    # Add http:// prefix if not present
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    print("Enter a name for the QR code (press Enter for default 'qrcode'):")
    name = input("Name: ").strip()
    
    # Use default name if none provided
    if not name:
        name = "qrcode"
    
    return url, name

def create_qr_code(params=None, api_key=None):
    """
    Create a new QR code with URL and name from user input or provided parameters.
    
    Args:
        params (dict, optional): Pre-defined parameters for QR code creation.
        api_key (str): Scanova API key from the MCP client
    
    Returns:
        dict: JSON response from the Scanova API containing the created QR code details.
    """
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    
    # Get URL and name from user if not provided in params
    if params is None or 'info' not in params:
        # For MCP server, we need params to be provided
        return {"error": "Parameters with 'info' field are required for QR code creation"}
    
    # Auto-serialize info if caller passed a dict instead of a JSON string
    if params and isinstance(params.get("info"), (dict, list)):
        params = {**params, "info": json.dumps(params["info"])}
    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.post(f"{_BASE}/qrcode/", headers=headers, json=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def get_qr_id_from_user():
    """
    Prompt the user to enter a QR code ID for update operations.
    
    This function interactively asks the user for the ID of an existing QR code
    that they want to update or modify.
    
    Returns:
        str: The QR code ID entered by the user
    
    Raises:
        ValueError: If no QR code ID is provided by the user
    
    Example:
        >>> qr_id = get_qr_id_from_user()
        Enter the QR code ID you want to update:
        QR ID: 12345
        >>> print(qr_id)
        12345
    """
    print("Enter the QR code ID you want to update:")
    qr_id = input("QR ID: ").strip()
    
    if not qr_id:
        raise ValueError("QR ID is required to update a QR code")
    
    return qr_id

def list_qr_codes(params=None, api_key=None):
    """
    Retrieve a list of QR codes from the Scanova API.
    
    Args:
        params (dict): Query parameters for filtering and pagination.
        api_key (str): Scanova API key from the MCP client
    
    Returns:
        dict: JSON response from the Scanova API containing the list of QR codes.
    """
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}

    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.get(f"{_BASE}/qrcode/", headers=headers, params=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def update_qr_code(qrid=None, params=None, api_key=None):
    """
    Update an existing QR code with new parameters.
    
    Args:
        qrid (str): The ID of the QR code to update.
        params (dict): Parameters for QR code update.
        api_key (str): Scanova API key from the MCP client
    
    Returns:
        dict: JSON response from the Scanova API containing the updated QR code details.
    """
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    
    if not qrid:
        return {"error": "QR code ID is required for update operation"}
    
    if not params:
        return {"error": "Parameters are required for QR code update"}
    
    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.put(f"{_BASE}/qrcode/{qrid}/", headers=headers, json=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def retrieve_qr_code(qrid=None, params=None, api_key=None):
    """
    Retrieve a QR code from the Scanova API.
    
    Args:
        qrid (str): The ID of the QR code to retrieve.
        params (dict, optional): Additional parameters.
        api_key (str): Scanova API key from the MCP client
    
    Returns:
        dict: JSON response from the Scanova API containing the QR code details.
    """
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    
    if not qrid:
        return {"error": "QR code ID is required for retrieve operation"}

    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.get(f"{_BASE}/qrcode/{qrid}/", headers=headers, params=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def download_qr_code(qrid=None, params=None, api_key=None):
    """
    Download a QR code from the Scanova API.
    
    Args:
        qrid (str): The ID of the QR code to download.
        params (dict, optional): Download parameters (size, format, etc.).
        api_key (str): Scanova API key from the MCP client
    
    Returns:
        dict: Response containing download information or error.
    """
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    
    if not qrid:
        return {"error": "QR code ID is required for download operation"}

    headers = {"Authorization": f"{api_key}"}
    try:
        resp = requests.get(f"{_BASE}/qr/{qrid}/download/", headers=headers, params=params)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "image/png")
            return {
                "success": True,
                "content_type": content_type,
                "size_bytes": len(resp.content),
                "data_base64": base64.b64encode(resp.content).decode("utf-8"),
            }
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def activate_qr_code(qrid=None, params=None, api_key=None):
    """
    Activate a QR code from the Scanova API.
    
    Args:
        qrid (str): The ID of the QR code to activate.
        params (dict, optional): Additional parameters.
        api_key (str): Scanova API key from the MCP client
    
    Returns:
        dict: JSON response from the Scanova API.
    """
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    
    if not qrid:
        return {"error": "QR code ID is required for activate operation"}

    if params is None:
        params = {"is_active": True}
    
    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.patch(f"{_BASE}/qrcode/{qrid}/", headers=headers, json=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def deactivate_qr_code(qrid=None, params=None, api_key=None):
    """
    Deactivate a QR code from the Scanova API.

    Args:
        qrid (str): The ID of the QR code to deactivate.
        params (dict, optional): Additional parameters.
        api_key (str): Scanova API key from the MCP client

    Returns:
        dict: JSON response from the Scanova API.
    """
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}

    if not qrid:
        return {"error": "QR code ID is required for deactivate operation"}

    if params is None:
        params = {"is_active": False}

    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.patch(f"{_BASE}/qrcode/{qrid}/", headers=headers, json=params)
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def delete_qr_code(qrid=None, api_key=None):
    """DELETE /qrcode/{qrid}/ — permanently delete a QR code."""
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    if not qrid:
        return {"error": "QR code ID is required for delete operation"}
    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.delete(f"{_BASE}/qrcode/{qrid}/", headers=headers)
        if resp.status_code == 204:
            return {"success": True, "message": "QR code deleted"}
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def get_qr_categories(view_type="all", api_key=None):
    """GET /qrcode/category/ — list available QR code categories."""
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.get(
            f"{_BASE}/qrcode/category/",
            headers=headers,
            params={"view_type": view_type},
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def download_qr_printable(qrid=None, size=600, name=None, api_key=None):
    """GET /qr/{qrid}/download/ with for_print=true — generate a print-optimised PDF QR code."""
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    if not qrid:
        return {"error": "QR code ID is required for printable download"}
    headers = {"Authorization": f"{api_key}"}
    params = {"for_print": "true", "file": "pdf", "size": str(size)}
    if name:
        params["name"] = name
    try:
        resp = requests.get(f"{_BASE}/qr/{qrid}/download/", headers=headers, params=params)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "application/pdf")
            return {
                "success": True,
                "content_type": content_type,
                "size_bytes": len(resp.content),
                "data_base64": base64.b64encode(resp.content).decode("utf-8"),
            }
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def validate_qr_info(category=None, info=None, api_key=None):
    """
    POST /qrcode/validate-info/ (form-data) — validate a category + info payload
    before calling create_qr_code/update_qr_code, catching malformed `info` JSON,
    missing required fields, or invalid URLs/emails ahead of time.
    """
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    if category is None:
        return {"error": "category is required"}
    if info is None:
        return {"error": "info is required"}

    info_str = json.dumps(info) if isinstance(info, (dict, list)) else info
    headers = {"Authorization": f"{api_key}"}
    try:
        resp = requests.post(
            f"{_BASE}/qrcode/validate-info/",
            headers=headers,
            data={"category": str(category), "info": info_str},
        )
        if resp.status_code == 200:
            return {"valid": True, "message": "QR code info data is valid"}
        try:
            body = resp.json()
        except ValueError:
            body = {"detail": resp.text}
        return {"valid": False, "error": body.get("info") or body.get("detail") or body}
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


# Static per-category `info` field reference — sourced from the Scanova docs
# (components.mdx + category-list.mdx via https://docs.scanova.io/mcp) and
# from the existing CREATE_QR_PARAMS_SCHEMA description in mcp_http/schemas.py.
# Categories not yet documented by Scanova are marked "documented": False —
# use validate_qr_info to check payloads for those instead of guessing the shape.
QR_CATEGORY_FIELDS = {
    1: {
        "name": "Website URL", "slug": "url", "documented": True,
        "info_example": {"type": "url", "data": {"url": "https://example.com"}},
        "notes": "Simple object. Required: data.url.",
    },
    # NOTE (2026-08-24): categories 2 and 3 were swapped from an earlier
    # version of this catalog — live API validation errors confirmed
    # category 2 requires type "email" and category 3 requires type "text"
    # (the reverse of what was previously documented here).
    2: {
        "name": "Email", "slug": "email", "documented": True,
        "info_example": {"type": "email", "data": {
            "to": "a@b.com", "cc": "c@b.com", "bcc": "d@b.com", "subject": "Hi", "body": "Hello",
        }},
        "notes": "Simple object. Required: data.to (NOT data.email — confirmed via real API schema). Optional: data.cc, data.bcc, data.subject, data.body.",
    },
    3: {
        "name": "Text", "slug": "text", "documented": True,
        "info_example": {"type": "text", "data": {"text": "Hello World"}},
        "notes": "Simple object. Required: data.text.",
    },
    4: {
        "name": "Phone", "slug": "phoneNumber", "documented": True,
        "info_example": {"type": "phoneNumber", "data": {"number": "7011472701"}},
        "notes": (
            "Simple object. Required: data.number (confirmed via qcg-frontend's "
            "PhoneNumberDataModel/ContactNumberModel — NOT data.phone or data.contactNumber, "
            "both of which were tried and rejected by a live validation error)."
        ),
    },
    5: {
        "name": "SMS", "slug": "sms", "documented": True,
        "info_example": {"type": "sms", "data": {"contactNumber": "7011472701", "message": "Hello"}},
        "notes": "Simple object. Required: data.contactNumber (NOT data.phone — confirmed by a live validation error). Optional: data.message.",
    },
    6: {
        "name": "WiFi", "slug": "wifi", "documented": True,
        "info_example": {"type": "wifi", "data": {"ssid": "MyNet", "password": "secret", "authentication": "WPA"}},
        "notes": "Simple object. Required: data.ssid, data.authentication (WPA|WPA2|WEP|none). Optional: data.password.",
    },
    7: {
        "name": "vCard", "slug": "vcard", "documented": True,
        "info_example": [
            {"type": "profile_info", "data": {"name": "John Doe", "title": "Engineer", "company": "Acme Inc"}},
            {"type": "contact_details", "data": {
                "emails": [{"email": "john@example.com"}],
                "phoneNumbers": [{"phoneNumber": "7011472701"}],
            }},
        ],
        "notes": (
            "info must be a JSON ARRAY of page-builder-style sections — confirmed via qcg-frontend's "
            "dynamic-v-card component and a literal example found in its source (there is no bare "
            "\"vcard\" type; the array elements' types come from ['profile_info', 'contact_details'], "
            "confirmed by a live validation error). profile_info.data: name, title, company (all "
            "optional, no explicit required field found). contact_details.data: emails (array of "
            "{email}), phoneNumbers (array of {phoneNumber}), website (array of {url}), addresses "
            "(array), faxes (array of {faxNumber}) — all optional arrays, include only what you have."
        ),
    },
    9: {
        "name": "Custom Page", "slug": "dynamicText", "documented": True,
        "info_example": {"type": "page_layout", "data": {"backgroundColor": "#ffffff", "sections": [
            {"type": "banner_images", "data": {"images": ["https://example.com/banner1.jpg"]}},
            {"type": "text_content", "data": {"title": "Page Title", "content": "Page content goes here"}},
        ]}},
        "notes": "Page-builder object with a sections array; section types vary (banner_images, text_content, etc.).",
    },
    10: {
        "name": "App Store", "slug": "appStore", "documented": True,
        "info_example": {"type": "appStore", "data": [
            {"type": "playStore", "url": "https://play.google.com/store/apps/details?id=com.example"},
            {"type": "appleStore", "url": "https://apps.apple.com/app/id123456789"},
        ]},
        "notes": "data is an array of {type: playStore|appleStore, url}.",
    },
    11: {
        "name": "Google Map", "slug": "map", "documented": True,
        "info_example": {"type": "map", "data": {
            "provider": "google", "latitude": 28.6139, "longitude": 77.2090,
            "placeId": "ChIJL_P_CXMEDTkRs_FGKBLBFBE", "placeName": "New Delhi, India",
        }},
        "notes": "Simple object. Required: data.provider, data.latitude, data.longitude.",
    },
    13: {
        "name": "Document", "slug": "document", "documented": True,
        "info_example": [
            {"type": "page_layout", "data": {"templateId": "default_1"}},
            {"type": "main_page", "data": {"pageTitle": "My Documents", "files": [
                {"url": "https://example.com/doc.pdf", "name": "My Document", "fileName": "doc", "size": 78482}
            ], "allowFileDownload": True}},
        ],
        "notes": "info must be a JSON ARRAY. files[].url must be a publicly accessible URL — file upload isn't supported via the API.",
    },
    14: {
        "name": "Wedding", "slug": "wedding", "documented": True,
        "info_example": [
            {"type": "page_layout", "data": {"templateName": "classic", "backgroundColor": "#ffffff"}},
            {"type": "couple_name", "data": {"first_name": "Alice", "second_name": "Bob"}},
            {"type": "description_box", "data": {"text": "Join us for our wedding"}},
        ],
        "notes": "info must be a JSON ARRAY. Shares the Event/Wedding page-builder component family.",
    },
    15: {
        "name": "Social Media", "slug": "sMedia", "documented": True,
        "info_example": [
            {"type": "page_layout", "data": {"templateName": "linear", "backgroundColor": "#ffffff"}},
            {"type": "social_media_profiles", "data": {"profiles": [
                {"platform": "instagram", "url": "https://instagram.com/handle"}
            ]}},
        ],
        "notes": "info must be a JSON ARRAY. profiles[].platform is a supported network slug (facebook, twitter, instagram, linkedin, youtube, etc.).",
    },
    16: {
        "name": "Audio", "slug": "audio", "documented": True,
        "info_example": [
            {"type": "page_layout", "data": {"templateId": "default_1"}},
            {"type": "main_page", "data": {"pageTitle": "My Playlist", "files": [
                {"url": "https://example.com/audio.mp3", "name": "Track Name", "mime": "audio/mpeg"}
            ]}},
        ],
        "notes": "info must be a JSON ARRAY. files[].url must be a publicly accessible audio URL (mp3, wav, aac, m4a) — file upload isn't supported via the API.",
    },
    17: {
        "name": "Coupon", "slug": "coupon", "documented": False,
        "notes": (
            "Blocked (2026-08-24) — this server does not support creating this category via "
            "create_qr_code. Its real info shape is unconfirmed: two sources in Scanova's own "
            "frontend codebase disagree (CouponDetailsData model vs. the live coupon-details "
            "form component), and a live API error confirmed the previously-documented flat "
            "'coupon' shape is wrong. Tell the user to create it via https://app.scanova.io instead."
        ),
    },
    18: {
        "name": "Product", "slug": "product", "documented": True,
        "info_example": [
            {"type": "page_layout", "data": {"backgroundColor": "#ffffff"}},
            {"type": "description_box", "data": {"text": "Product description"}},
            {"type": "button", "data": {"text": "Buy Now", "url": "https://example.com/buy"}},
        ],
        "notes": "info must be a JSON ARRAY (page-builder style).",
    },
    19: {
        "name": "Image", "slug": "image", "documented": True,
        "info_example": {"type": "image", "data": [{"url": "https://example.com/image.jpg", "name": "Image Name"}]},
        "notes": "data is an array of {url, name}.",
    },
    20: {
        "name": "Event", "slug": "event", "documented": True,
        "info_example": {"type": "page_layout", "data": {"backgroundColor": "#ffffff", "eventDetails": {
            "title": "Event Title", "date": "2024-01-15", "time": "18:00", "venue": "Event Venue",
            "description": "Event description", "rsvp": {"enabled": True, "url": "https://example.com/rsvp"},
        }}},
        "notes": "Required: data.eventDetails.title, data.eventDetails.date. Shares the Wedding page-builder component family.",
    },
    23: {
        "name": "App Deep Link", "slug": "appDeepLink", "documented": True,
        "info_example": [
            {"type": "intentUri", "data": [
                {"type": "android", "uri": "https://example.com/open"},
                {"type": "ios", "uri": "https://example.com/open"},
            ]},
            {"type": "appStore", "data": [
                {"type": "playStore", "url": "https://play.google.com/store/apps/details?id=com.example"},
                {"type": "appleStore", "url": "https://apps.apple.com/app/id123456789"},
            ]},
            {"type": "fallback", "data": {"url": "https://example.com/download"}},
        ],
        "notes": (
            "info IS the ARRAY of typed sections directly — there is no outer "
            "{type:'appDeepLink'} wrapper (confirmed by a live schema check, 2026-08-24). "
            "Sections: 'intentUri' (data: array of {type: 'android'|'ios', uri}), 'appStore' "
            "(data: array of {type: 'playStore'|'appleStore', url}), 'fallback' (data: {url}). "
            "intentUri (at least one of android/ios) and fallback are both required; appStore "
            "is always optional."
        ),
    },
    24: {
        "name": "Business Card", "slug": "businessCard", "documented": False,
        "notes": (
            "Blocked (2026-08-24) — this server does not support creating this category via "
            "create_qr_code. Tell the user to create it via https://app.scanova.io instead."
        ),
    },
    25: {
        "name": "Restaurant", "slug": "restaurant", "documented": False,
        "notes": (
            "Blocked (2026-08-24) — this server does not support creating this category via "
            "create_qr_code. Scanova's own docs disagree on its real info shape (a flat object "
            "in one place, a page-builder array of {page_layout, brand_info, footer_info, ...} "
            "sections in another). Tell the user to create it via https://app.scanova.io instead."
        ),
    },
    44: {
        "name": "Restaurant", "slug": "restaurant", "documented": False,
        "notes": "Duplicate category ID for Restaurant — same blocked status as category 25.",
    },
    26: {"name": "Feedback", "slug": "feedback", "documented": False,
         "notes": "Not documented in the Scanova API reference yet. Use validate_qr_info to check a payload before creating."},
    27: {"name": "Real Estate", "slug": "realEstate", "documented": False,
         "notes": "Not documented in the Scanova API reference yet. Use validate_qr_info to check a payload before creating."},
    28: {"name": "Link Page", "slug": "linkPage", "documented": False,
         "notes": "Not documented in the Scanova API reference yet. Use validate_qr_info to check a payload before creating."},
    31: {"name": "GS1", "slug": "gs1", "documented": False,
         "notes": "Not documented in the Scanova API reference yet. Use validate_qr_info to check a payload before creating."},
}


def get_qr_category_fields(category=None):
    """
    Static reference (no API call) describing the `info` JSON shape required
    for a QR code category, so a caller doesn't have to guess it before
    calling create_qr_code/update_qr_code. Omit `category` to list all of them.
    """
    if category is None:
        return {"categories": QR_CATEGORY_FIELDS}
    try:
        key = int(category)
    except (TypeError, ValueError):
        return {"error": f"category must be a numeric QR category ID, got: {category!r}"}
    entry = QR_CATEGORY_FIELDS.get(key)
    if entry is None:
        return {"error": f"Unknown category ID: {key}. Call get_qr_categories or get_qr_category_fields with no arguments to see valid IDs."}
    return {"category": key, **entry}


def attach_form_to_qr(qrid=None, form_id=None, api_key=None):
    """PATCH /qrcode/{qrid}/ — attach a lead capture form to a QR code."""
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    if not qrid:
        return {"error": "QR code ID is required"}
    if form_id is None:
        return {"error": "form_id is required"}
    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.patch(
            f"{_BASE}/qrcode/{qrid}/", headers=headers, json={"form": form_id}
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def detach_form_from_qr(qrid=None, api_key=None):
    """PATCH /qrcode/{qrid}/ — remove the lead capture form from a QR code."""
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    if not qrid:
        return {"error": "QR code ID is required"}
    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.patch(
            f"{_BASE}/qrcode/{qrid}/", headers=headers, json={"form": None}
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def attach_lead_list_to_qr(qrid=None, lead_list_id=None, api_key=None):
    """PATCH /qrcode/{qrid}/ — attach a lead list to a QR code."""
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    if not qrid:
        return {"error": "QR code ID is required"}
    if lead_list_id is None:
        return {"error": "lead_list_id is required"}
    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.patch(
            f"{_BASE}/qrcode/{qrid}/", headers=headers, json={"lead_list": lead_list_id}
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def detach_lead_list_from_qr(qrid=None, api_key=None):
    """PATCH /qrcode/{qrid}/ — remove the lead list from a QR code."""
    if not api_key:
        return {"error": "API key is required. Please configure your Scanova API key in your MCP client."}
    if not qrid:
        return {"error": "QR code ID is required"}
    headers = {"Authorization": f"{api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.patch(
            f"{_BASE}/qrcode/{qrid}/", headers=headers, json={"lead_list": None}
        )
        return api_result(resp)
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
