"""The dashboard's wiring test for the バックテスト tab (item 3, old item 10:
「配線の試験」). Serves the real handler of scripts/dashboard.py over a runs
directory that bot.bt.repro wrote, and follows the page the way a viewer
does: the top tab 「バックテスト」 exists, the runs API lists the run, the run
API gives its ten tabs, and the run page is served. Any cut in that chain
(a route that answers 404, a tab label that is gone) fails this test.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import i3_driver as D  # noqa: E402

TABS = ["概要", "前提", "損益", "取引", "約定の質", "費用", "分布", "検証", "再現性", "データ品質"]


def _fixture(root: Path) -> str:
    (root / "data").mkdir()
    rows = "".join(f"{1767225600000000000 + k * 5_000_000_000},{10000000.0 + k},1.0\n" for k in range(200))
    (root / "data" / "tape.csv").write_text("t_ns,px,qty\n" + rows, encoding="utf-8")
    t0 = 1767225600000000000
    cfg = {"instrument": "FX_BTC_JPY",
           "strategy": {"kind": "fixed_times", "legs": [{"t_ns": t0 + 60_000_000_000, "side": "buy", "qty": 0.01},
                                                        {"t_ns": t0 + 360_000_000_000, "side": "sell", "qty": 0.01}]},
           "order_type": "market", "fill": {"market": "next_trade_price"},
           "latency_ns": {"feed": 0, "order": 0, "cancel": 0},
           "costs": {"maker_fee_rate": 0.0, "taker_fee_rate": 0.0, "funding": "none", "source": "配線の試験の宣言"}}
    return D._run(str(root), {"data": ["data/tape.csv"], "config": cfg, "seed": 1, "strategy": "fixed_times",
                              "runs_dir": "runs", "purpose": "動作確認"}).run_id


def _get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=20) as r:
        assert r.status == 200
        return r.read().decode("utf-8")


def test_backtest_tab_is_wired_from_page_to_run(tmp_path):
    rid = _fixture(tmp_path)
    srv = D._serve(os.path.join(tmp_path, "runs"))
    try:
        port = srv.server_address[1]
        page = _get(port, "/")
        nav = re.search(r'<nav class="tabs">(.*?)</nav>', page, re.S).group(1)
        assert "showTab('backtest')" in nav and "バックテスト" in nav
        assert 'id="view-backtest"' in page and "/api/backtest/runs" in page
        runs = json.loads(_get(port, "/api/backtest/runs"))["runs"]
        assert [r["run_id"] for r in runs] == [rid]
        view = json.loads(_get(port, f"/api/backtest/run/{rid}"))
        assert [t["label"] for t in view["tabs"]] == TABS
        assert all("動作確認の実行。相場の結論には使わない" in t["text"] for t in view["tabs"])
        run_page = _get(port, f"/backtest/run/{rid}")
        assert "バックテスト" in run_page and all(f'data-tab="{t}"' in run_page for t in TABS)
    finally:
        srv.shutdown()
        srv.server_close()


def test_unknown_run_is_404_not_a_crash(tmp_path):
    _fixture(tmp_path)
    srv = D._serve(os.path.join(tmp_path, "runs"))
    try:
        port = srv.server_address[1]
        for path in ("/api/backtest/run/" + "0" * 64, "/api/backtest/run/..%2Fsecret", "/backtest/run/zz"):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=20)
                raise AssertionError(f"{path} answered 200")
            except urllib.error.HTTPError as exc:
                assert exc.code == 404
    finally:
        srv.shutdown()
        srv.server_close()
