"""Turn a Scanova API HTTP response into what the tools return.

Every API module used to `return resp.json()`, dropping the HTTP status: a 404,
403 or 401 from the Scanova API reached the model as a *successful* result.
`api_result` keeps the body on success and marks a failure as one — `{"error":
<body>, "status_code": <n>}`, which the normalizer reports as `ok: false`
(and the server as a tool error, `isError: true`) with the real status code.
"""

import requests


def api_result(resp: requests.Response):
    try:
        body = resp.json()
    except ValueError:
        body = resp.text.strip() or None
    if 200 <= resp.status_code < 300:
        return body if body is not None else {"success": True, "status_code": resp.status_code}
    return {
        "error": body if body is not None else f"Scanova API returned HTTP {resp.status_code}",
        "status_code": resp.status_code,
    }
