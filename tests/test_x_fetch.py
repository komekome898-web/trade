import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import x_fetch  # noqa: E402


def test_parse_id_from_url_and_bare():
    assert x_fetch.parse_id("https://x.com/OpenRouter/status/2100744709589316009") == "2100744709589316009"
    assert x_fetch.parse_id("2100744709589316009") == "2100744709589316009"
    assert x_fetch.parse_id("not-an-id") is None


def test_normalize_success_and_failure():
    data = {"tweet": {"url": "u", "author": {"screen_name": "a"}, "created_at": "d", "text": "t",
                      "likes": 1, "retweets": 2, "replies": 3, "views": 4,
                      "quote": {"id": "9", "author": {"screen_name": "q"}, "text": "x" * 300},
                      "replying_to_status": "8"}}
    row = x_fetch.normalize("1", 200, data, None)
    assert row["author"] == "a" and row["quote"]["author"] == "q" and len(row["quote"]["text"]) == 200
    assert row["replying_to_status"] == "8"
    bad = x_fetch.normalize("2", 404, None, "HTTP 404")
    assert bad["http"] == 404 and bad["error"] == "HTTP 404" and "text" not in bad


def test_walks_up_to_root_without_network(monkeypatch, capsys):
    chain = {"300000003": "300000002", "300000002": "300000001", "300000001": None}
    calls = []

    def fake(tid, timeout=20.0):
        calls.append(tid)
        return 200, {"tweet": {"text": tid, "replying_to_status": chain[tid], "author": {"screen_name": "s"}}}, None

    monkeypatch.setattr(x_fetch, "fetch_status", fake)
    monkeypatch.setattr(x_fetch.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["x_fetch", "300000003"])
    x_fetch.main()
    rows = [json.loads(l) for l in capsys.readouterr().out.strip().splitlines()]
    assert calls == ["300000003", "300000002", "300000001"] and [r["id"] for r in rows] == calls
