"""Grids for the バックテスト tab (item 3, old item 10): purpose x setup x
validation attached or not -> every tab of every run carries the warning
exactly when the purpose is 動作確認; the served values are the exports'
values; no served page or tab names an external URL; every label is
Japanese; an unfinished run directory is not listed.

Not in the grid: how the page looks (colours, layout) -- not a behaviour a
test can judge; the critic reads it.
"""
from __future__ import annotations

import itertools
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import i3_driver as D  # noqa: E402

from bot.monitoring import backtest_view as BV  # noqa: E402
from bot.bt import repro as RP  # noqa: E402

T0 = 1767225600000000000
S = 1_000_000_000
JP = re.compile(r"[぀-ヿ㐀-鿿]")


def _root(tmp):
    (tmp / "data").mkdir()
    rows = "".join(f"{T0 + k * 5 * S},{10000000.0 + (k % 7) * 100},1.0\n" for k in range(400))
    (tmp / "data" / "tape.csv").write_text("t_ns,px,qty\n" + rows, encoding="utf-8")
    (tmp / "P.md").write_text("# 事前登録\n本文\n", encoding="utf-8")


def _cfg():
    legs = []
    for k in range(3):
        legs += [{"t_ns": T0 + (100 + 400 * k) * S, "side": "buy", "qty": 0.01},
                 {"t_ns": T0 + (300 + 400 * k) * S, "side": "sell", "qty": 0.01}]
    return {"instrument": "FX_BTC_JPY", "strategy": {"kind": "fixed_times", "legs": legs}, "order_type": "market",
            "fill": {"market": "next_trade_price"}, "latency_ns": {"feed": 0, "order": 0, "cancel": 0},
            "costs": {"maker_fee_rate": 0.0, "taker_fee_rate": 0.001, "funding": "none", "source": "試験"}}


def test_dashboard_grid(tmp_path):
    _root(tmp_path)
    runs = str(tmp_path / "runs")
    made = {}
    for purpose, kind, val in itertools.product(("動作確認", "研究"), ("fixed_times", "seeded_random"), (None, {"mde": 1.5})):
        r = RP.run(runs_dir=runs, root=str(tmp_path), data=[RP.DataInput("data/tape.csv", D.TAPE_SPEC)], config=_cfg(),
                   seed=3, setup=RP.FixedSetup(kind), purpose=purpose, prereg="P.md" if purpose == "研究" else None,
                   validation=val)
        made[r.run_id] = (purpose, val, r)
    assert len(made) == 8
    os.makedirs(os.path.join(runs, "f" * 64))  # unfinished: no record, no repro
    listed = [x["run_id"] for x in BV.list_runs(runs)]
    assert sorted(listed) == sorted(made)
    srv = D._serve(runs)
    try:
        port = srv.server_address[1]
        get = lambda p: urllib.request.urlopen(f"http://127.0.0.1:{port}{p}", timeout=20).read().decode("utf-8")  # noqa: E731
        page = get("/")
        assert D._external(page) == []
        for rid, (purpose, val, res) in made.items():
            v = json.loads(get(f"/api/backtest/run/{rid}"))
            assert [t["label"] for t in v["tabs"]] == list(BV.TABS)
            assert all(JP.search(t["label"]) for t in v["tabs"])
            for t in v["tabs"]:
                assert (BV.WARNING in t["text"]) == (purpose == "動作確認") == (BV.WARNING in t["html"])
            m = json.loads((Path(res.run_dir) / "metrics.json").read_text(encoding="utf-8"))["data"]["trades"]
            assert v["values"] == {"per_trade_bp": m["per_trade_bp"], "neg_frac": m["neg_frac"]}
            check = next(t for t in v["tabs"] if t["label"] == "検証")
            assert ("mde" in check["text"]) == (val is not None)
            rep = next(t for t in v["tabs"] if t["label"] == "再現性")
            assert rid in rep["text"] and "2 回の実行で一致" in rep["text"]
            html_page = get(f"/backtest/run/{rid}")
            assert D._external(html_page) == [] and "<script" not in html_page
    finally:
        srv.shutdown()
        srv.server_close()
