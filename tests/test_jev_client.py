"""`scripts/jev/client.py` — `urllib.request.urlopen` をモックしてネットワークに触れない。"""
from __future__ import annotations

import io
import json
import sys
import urllib.error
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest

from scripts.jev.client import JevClient, JevError


class _FakeHTTPResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _ok_response(payload: dict):
    return _FakeHTTPResponse(json.dumps(payload).encode("utf-8"))


def test_evaluate_success(tmp_path, monkeypatch):
    payload = {
        "model": "jev-1.13.0",
        "answers": {"P1": {"type": "noul", "noul": 0.1}},
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }
    with mock.patch("scripts.jev.client.urllib.request.urlopen", return_value=_ok_response(payload)) as m:
        client = JevClient(api_key="k", model="jev-1.13.0", log_dir=str(tmp_path))
        resp = client.evaluate(state="hello", questions={"P1": {"type": "noul"}})
    assert resp == payload
    req = m.call_args[0][0]
    assert req.get_header("Authorization") == "Bearer k"
    # ログに state 本文が書かれていないこと
    log_files = list(tmp_path.glob("calls_*.jsonl"))
    assert len(log_files) == 1
    line = json.loads(log_files[0].read_text(encoding="utf-8").strip())
    assert "hello" not in json.dumps(line)
    assert line["model_answered"] == "jev-1.13.0"
    assert line["status"] == "ok"
    assert "usage" in line and "state_chars" in line and "state_sha256" in line


def test_evaluate_401_raises(tmp_path):
    err = urllib.error.HTTPError("url", 401, "unauthorized", {}, io.BytesIO(b"no auth"))
    with mock.patch("scripts.jev.client.urllib.request.urlopen", side_effect=err):
        client = JevClient(api_key="k", model="jev-1.13.0", log_dir=str(tmp_path))
        with pytest.raises(JevError):
            client.evaluate(state="x", questions={})
    log_files = list(tmp_path.glob("calls_*.jsonl"))
    line = json.loads(log_files[0].read_text(encoding="utf-8").strip())
    assert line["status"] == "error"


def test_evaluate_retries_on_429_then_succeeds(tmp_path):
    payload = {"model": "jev-1.13.0", "answers": {}, "usage": {}}
    err = urllib.error.HTTPError("url", 429, "too many", {}, io.BytesIO(b"slow down"))
    calls = {"n": 0}

    def side_effect(*a, **kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise err
        return _ok_response(payload)

    with mock.patch("scripts.jev.client.urllib.request.urlopen", side_effect=side_effect):
        with mock.patch("scripts.jev.client.time.sleep") as sleep_mock:
            client = JevClient(api_key="k", model="jev-1.13.0", log_dir=str(tmp_path))
            resp = client.evaluate(state="x", questions={})
    assert resp == payload
    assert calls["n"] == 3
    assert sleep_mock.call_count == 2
    sleep_mock.assert_any_call(2)
    sleep_mock.assert_any_call(4)


def test_evaluate_gives_up_after_max_retries(tmp_path):
    err = urllib.error.HTTPError("url", 529, "overloaded", {}, io.BytesIO(b"overloaded"))
    with mock.patch("scripts.jev.client.urllib.request.urlopen", side_effect=err):
        with mock.patch("scripts.jev.client.time.sleep"):
            client = JevClient(api_key="k", model="jev-1.13.0", log_dir=str(tmp_path))
            with pytest.raises(JevError):
                client.evaluate(state="x", questions={})


def test_non_retry_status_raises_immediately(tmp_path):
    err = urllib.error.HTTPError("url", 500, "server error", {}, io.BytesIO(b"boom"))
    with mock.patch("scripts.jev.client.urllib.request.urlopen", side_effect=err) as m:
        with mock.patch("scripts.jev.client.time.sleep") as sleep_mock:
            client = JevClient(api_key="k", model="jev-1.13.0", log_dir=str(tmp_path))
            with pytest.raises(JevError):
                client.evaluate(state="x", questions={})
    assert m.call_count == 1
    sleep_mock.assert_not_called()


def test_missing_model_raises(tmp_path):
    with pytest.raises(JevError):
        JevClient(api_key="k", model=None, log_dir=str(tmp_path))


def test_missing_key_does_not_raise_but_sends_without_auth_header(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    payload = {"model": "jev-1.13.0", "answers": {}, "usage": {}}
    with mock.patch("scripts.jev.client.urllib.request.urlopen", return_value=_ok_response(payload)) as m:
        client = JevClient(api_key=None, model="jev-1.13.0", log_dir=str(tmp_path))
        resp = client.evaluate(state="x", questions={})
    assert resp == payload
    req = m.call_args[0][0]
    assert req.get_header("Authorization") is None
    captured = capsys.readouterr()
    assert "鍵なしで送信" in captured.err


def test_present_key_sends_auth_header(tmp_path):
    payload = {"model": "jev-1.13.0", "answers": {}, "usage": {}}
    with mock.patch("scripts.jev.client.urllib.request.urlopen", return_value=_ok_response(payload)) as m:
        client = JevClient(api_key="k", model="jev-1.13.0", log_dir=str(tmp_path))
        client.evaluate(state="x", questions={})
    req = m.call_args[0][0]
    assert req.get_header("Authorization") == "Bearer k"


def test_key_from_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("TYPESAFE_API_KEY", "env-key")
    payload = {"model": "jev-1.13.0", "answers": {}, "usage": {}}
    with mock.patch("scripts.jev.client.urllib.request.urlopen", return_value=_ok_response(payload)) as m:
        client = JevClient(model="jev-1.13.0", log_dir=str(tmp_path))
        client.evaluate(state="x", questions={})
    req = m.call_args[0][0]
    assert req.get_header("Authorization") == "Bearer env-key"


def test_jev_latest_warns_but_does_not_raise(tmp_path, capsys):
    client = JevClient(api_key="k", model="jev-latest", log_dir=str(tmp_path))
    captured = capsys.readouterr()
    assert "jev-latest" in captured.err
    assert client.model == "jev-latest"


def test_keep_alive_reuses_one_connection(tmp_path, monkeypatch):
    """keep_alive=True は http.client の接続を 1 本作って使い回す(2 回送っても構築は 1 回)。"""
    import http.client
    from scripts.jev import client as jc
    calls = {"made": 0}

    class FakeResp:
        status = 200
        def read(self):
            return json.dumps({"model": "jev-1.13.0", "answers": {"q": {"type": "noul", "noul": 0.5}},
                               "usage": {"input_tokens": 1}}).encode()

    class FakeConn:
        def __init__(self, *a, **k):
            calls["made"] += 1
        def set_tunnel(self, *a, **k):
            pass
        def request(self, *a, **k):
            pass
        def getresponse(self):
            return FakeResp()
        def close(self):
            pass

    monkeypatch.setattr(http.client, "HTTPSConnection", FakeConn)
    c = jc.JevClient(api_key="k", model="jev-1.13.0", log_dir=str(tmp_path), keep_alive=True)
    c.evaluate("s", {"q": {"type": "noul", "instructions": "x"}})
    c.evaluate("s", {"q": {"type": "noul", "instructions": "x"}})
    assert calls["made"] == 1
