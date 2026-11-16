"""Internal tools: for Scanova's own services (Trycon AI), never for customers.

- ``lookup_customer_plan``: the plan of the Scanova account an email belongs to (its owner's, for a team member), for
  Trycon AI's bug reporting. Calls qcg-backend's ``POST /internal/plan-lookup/`` on the backend's VPC-only internal
  listener (``INTERNAL_API_BASE_URL``), not the public Management API, with the service token
  (``SCANOVA_SERVICE_TOKEN``, a ``qsvc_…`` key). Spec: trycon/internal-ai
  docs/internal/plans/qcg-mcp-plan-lookup-by-email.md.

The tool is in the ``internal`` toolset, which no customer-facing group includes. It is still listed in tools/list
(the list is the same for every caller), so it guards itself: it runs only for a caller whose own credential *is*
the configured service token, raw or as `Bearer <token>` (constant-time compare). Anyone else — a customer's Management API key, an OAuth token —
gets a 403 tool error here and their credential never reaches the internal route. Until both env vars are set the
tool answers "not configured".

The email is sent in the POST body (never a URL) and is never logged.
"""

import hmac
import re

import requests

import config
from api_response import api_result
from mcp_http.more_tools import MoreTool, _input
from scanova_api import NO_KEY

# The caller gives the whole call 5 s, so time out first and answer an error.
TIMEOUT_S = 4
PATH = "internal/plan-lookup/"
ENDPOINT = "/internal/plan-lookup/"
MAX_EMAIL_CHARS = 254
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

NOT_CONFIGURED = {
    "error": "lookup_customer_plan isn't configured on this server (INTERNAL_API_BASE_URL / SCANOVA_SERVICE_TOKEN).",
    "status_code": 503,
}
FORBIDDEN = {
    "error": "lookup_customer_plan is for Scanova's internal services only; this credential can't use it.",
    "status_code": 403,
}


_BEARER = re.compile(r"^bearer\s+", re.IGNORECASE)


def _presented_token(api_key: str) -> str:
    """The caller's credential without a `Bearer ` prefix (any case); the raw form is kept as is."""
    return _BEARER.sub("", api_key.strip(), count=1).strip()


def _authorized(api_key: str, service_token: str) -> bool:
    presented = _presented_token(api_key)
    expected = service_token.strip()
    if not presented or not expected:
        return False
    # Constant time, so the comparison doesn't leak how much of the key matched.
    return hmac.compare_digest(presented.encode(), expected.encode())


def lookup_customer_plan(email, api_key: str = None):
    """POST /internal/plan-lookup/ {email} on the internal listener, with the service token."""
    if not api_key:
        return NO_KEY
    base_url = (config.INTERNAL_API_BASE_URL or "").rstrip("/")
    service_token = config.SCANOVA_SERVICE_TOKEN or ""
    if not base_url or not service_token:
        return NOT_CONFIGURED
    if not _authorized(api_key, service_token):
        return FORBIDDEN

    if not isinstance(email, str) or not email.strip():
        return {"error": "email is required", "status_code": 400}
    email = email.strip().lower()
    if len(email) > MAX_EMAIL_CHARS or not _EMAIL.match(email):
        return {"error": "email isn't a valid address", "status_code": 400}

    try:
        resp = requests.post(
            f"{base_url}/{PATH}",
            headers={"Authorization": service_token.strip(), "Content-Type": "application/json"},
            json={"email": email},
            timeout=TIMEOUT_S,
        )
    except requests.RequestException as e:
        # The exception text is the URL and the network error; requests never puts the body in it.
        return {"error": f"API request failed: {type(e).__name__}", "status_code": 503}
    return api_result(resp)


_FAMILY = {
    "type": ["object", "null"],
    "properties": {"slug": {"type": "string"}, "name": {"type": "string"}},
}

LOOKUP_CUSTOMER_PLAN_OUTPUT = {
    "type": "object",
    "description": "The plan of the account the email belongs to (its owner's, for a team member); only `found` when there's no such account",
    "properties": {
        "found": {"type": "boolean", "description": "Whether a Scanova user has that email; nothing else is returned when false"},
        "role": {"type": "string", "enum": ["owner", "team_member"], "description": "team_member: the plan shown is the account owner's"},
        "plan": {
            "type": ["object", "null"],
            "description": "Null when the account has no plan",
            "properties": {
                "name": {"type": "string"},
                "family": _FAMILY,
                "plan_type": {"type": "string", "enum": ["free", "normal", "on_request", "api"]},
                "is_enterprise": {"type": "boolean"},
                "is_trial": {"type": "boolean", "description": "The plan is the default signup (trial) plan"},
            },
        },
        "status": {"type": "string", "enum": ["active", "expired", "inactive"], "description": "inactive also for a closed account"},
        "is_free": {"type": "boolean"},
        "expire": {"type": "string", "description": "YYYY-MM-DD, or \"Lifetime\""},
        "days_left": {"type": "integer"},
        "recurring_enabled": {"type": "boolean"},
        "billing_interval": {"type": "string", "description": "e.g. Monthly, Yearly"},
        "upcoming_plan": {
            "type": ["object", "null"],
            "description": "A scheduled plan change",
            "properties": {"name": {"type": "string"}, "family": _FAMILY, "starts": {"type": "string"}},
        },
        "seats": {
            "type": "object",
            "properties": {
                "used": {"type": "integer", "description": "Team members, including SCIM-provisioned ones and pending invitations"},
                "limit": {"type": "integer", "description": "Null when unlimited or not on the plan"},
            },
        },
        "error": {"type": "string", "description": "Human-readable error message"},
    },
}


INTERNAL_TOOLS = [
    MoreTool(
        "lookup_customer_plan", "Look up a customer's plan (internal)",
        (
            "Internal — Scanova's own services only; customers' credentials are refused. The plan of the Scanova account "
            "an email belongs to (the owner's plan for a team member): plan name and family, trial/enterprise, status "
            "(active, expired, inactive), expiry, billing interval, a scheduled change and seats. found: false when no "
            "account has that email."
        ),
        "Internal", ENDPOINT,
        _input({"email": {"type": "string", "format": "email", "description": "The customer's email address"}}, ("email",)),
        LOOKUP_CUSTOMER_PLAN_OUTPUT,
        lambda a, k: lookup_customer_plan(email=a.get("email"), api_key=k),
    ),
]

INTERNAL_TOOL_NAMES = frozenset(t.name for t in INTERNAL_TOOLS)
