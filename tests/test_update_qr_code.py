"""update_qr_code keeps the code's name and type when a change leaves them out (the API's update is a full one)."""
from unittest.mock import MagicMock, patch

import qrcode as qr


def _resp(status, body):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body
    r.text = str(body)
    r.headers = {"content-type": "application/json"}
    return r


def test_destination_only_change_keeps_name_and_type():
    current = {"qrid": "Q1", "name": "Milkshake Recipes QR", "qr_type": "dy", "category": {"id": 1}}
    with patch.object(qr.requests, "get", return_value=_resp(200, current)) as get, patch.object(qr.requests, "put", return_value=_resp(200, {**current, "info": "x"})) as put:
        qr.update_qr_code("Q1", {"info": '{"type":"url","data":{"url":"https://x.test"}}'}, api_key="Token t")
    get.assert_called_once()
    sent = put.call_args.kwargs["json"]
    assert sent["name"] == "Milkshake Recipes QR" and sent["qr_type"] == "dy"
    assert sent["info"] == '{"type":"url","data":{"url":"https://x.test"}}'


def test_given_name_wins_and_no_lookup_when_both_given():
    with patch.object(qr.requests, "get") as get, patch.object(qr.requests, "put", return_value=_resp(200, {})) as put:
        qr.update_qr_code("Q1", {"name": "New name", "qr_type": "dy", "info": "{}"}, api_key="Token t")
    get.assert_not_called()
    assert put.call_args.kwargs["json"]["name"] == "New name"


def test_unknown_code_is_reported_not_put():
    with patch.object(qr.requests, "get", return_value=_resp(404, {"detail": "Not found."})), patch.object(qr.requests, "put") as put:
        out = qr.update_qr_code("Qnope", {"info": "{}"}, api_key="Token t")
    put.assert_not_called()
    assert out
