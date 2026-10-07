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
    rows = "".join(f"{1700000000000000000 + k * 5_000_000_000},{10000000.0 + k},1.0\n" for k in range(200))
    (root / "data" / "tape.csv").write_text("t_ns,px,qty\n" + rows, encoding="utf-8")
    t0 = 1700000000000000000
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


def _market(root: Path) -> None:
    """The seal ledger (P2-08 / P2-08b) and the instrument's 1-minute price store under `root`, as the chart reads them."""
    import gzip
    from datetime import datetime, timezone
    for unit, fwd, files in (("P2-08", "2026-09-06T00:00:00+00:00", [{"path": "backtest_data/bf/c.csv.gz", "time_column": "ts",
                                                                     "seal_from_ts": "2023-12-18T00:00:00+00:00"}]),
                             ("P2-08b", "2026-09-08T00:00:00+00:00", [{"path": "backtest_data/e.csv.gz", "time_column": "d",
                                                                      "seal_from_ts": "2026-08-23T00:00:00+00:00"}])):
        d = root / "backtest_data" / "phase2_sealed" / unit
        d.mkdir(parents=True)
        (d / "SEALED.json").write_text(json.dumps({"unit": unit, "forward_start": fwd, "files": files}))
    f = root / "backtest_data" / "bitflyer_lightchart_FX_BTC_JPY_1m_20260906" / "candles_1m_2023.csv.gz"
    f.parent.mkdir(parents=True)
    with gzip.open(f, "wt") as fh:
        fh.write("ts,open,high,low,close,volume\n")
        for k in range(120):
            t = datetime.fromtimestamp(1700000000 + k * 60, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
            fh.write(f"{t},{10000000 + k},{10000010 + k},{9999990 + k},{10000005 + k},1\n")


def test_backtest_tab_is_wired_from_page_to_run(tmp_path):
    from http.server import ThreadingHTTPServer
    import threading
    rid = _fixture(tmp_path)
    _market(tmp_path)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), D.dashboard_module().make_handler(os.path.join(tmp_path, "runs"), data_root=tmp_path))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        page = _get(port, "/")
        nav = re.search(r'<nav class="tabs">(.*?)</nav>', page, re.S).group(1)
        assert "showTab('backtest')" in nav and "バックテスト" in nav
        assert 'id="view-backtest"' in page and "/static/backtest_tab.js" in page
        assert "/api/backtest/catalog" in _get(port, "/static/backtest_tab.js")
        runs = json.loads(_get(port, "/api/backtest/runs"))["runs"]
        assert [r["run_id"] for r in runs] == [rid]
        # catalog -> summary -> chart, the way the page follows them
        cat = json.loads(_get(port, "/api/backtest/catalog"))
        listed = [r["run_id"] for t in cat["themes"] for s in t["strategies"] for r in s["runs"]]
        assert listed == [rid]
        # a run with no road/ record is an 古い形の走らせ: it is listed (last), has no chart and no table, and keeps its old detail tabs
        assert cat["themes"][-1]["id"] == "legacy" and cat["n_legacy_runs"] == 1
        summ = json.loads(_get(port, f"/api/backtest/summary/{rid}"))
        assert summ["legacy"] is True and "古い形" in summ["unavailable"] and "stats" not in summ
        for path in (f"/api/backtest/chart/{rid}", f"/api/backtest/table/{rid}/trades"):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=20)
                raise AssertionError(f"{path} answered 200")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400
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


def test_backtest_tab_is_wired_for_a_road_run(tmp_path):
    """catalog -> summary -> chart -> table -> trace for a road run (road/ beside record.json), over the real handler."""
    import threading
    from http.server import ThreadingHTTPServer
    sys_path = str(Path(__file__).resolve().parents[2])
    import sys
    sys.path.insert(0, sys_path)
    from road_fixture import trade, write_road_run  # noqa: PLC0415
    _market(tmp_path)
    t0 = 1700000000
    rid = "d" * 64
    write_road_run(tmp_path, rid, [trade(t0 + 600, t0 + 1200, 10000010, 10000030)], group="", instrument="FX_BTC_JPY", first=t0, last=t0 + 7000,
                   shared="runs", data=[])
    srv = ThreadingHTTPServer(("127.0.0.1", 0), D.dashboard_module().make_handler(os.path.join(tmp_path, "runs"), data_root=tmp_path))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        cat = json.loads(_get(port, "/api/backtest/catalog"))
        assert [r["run_id"] for t in cat["themes"] for s in t["strategies"] for r in s["runs"]] == [rid]
        summ = json.loads(_get(port, f"/api/backtest/summary/{rid}"))
        assert summ["road"]["version"] == "road-record-7" and summ["headline"]["pessimistic"]["trades"]["closed"] == 1 and summ["price"]["available"]
        import time as _t
        chart = json.loads(_get(port, f"/api/backtest/chart/{rid}?interval=60"))
        for _ in range(60):
            if not chart.get("building"):
                break
            _t.sleep(0.5)
            chart = json.loads(_get(port, f"/api/backtest/chart/{rid}?interval=60"))
        assert chart["bars"] and chart["layers"]["pessimistic"]["counts"]["trades"] == 1
        tab = json.loads(_get(port, f"/api/backtest/table/{rid}/fills"))
        assert tab["matched"] == 2 and len(tab["rows"]) == 2
        tr = json.loads(_get(port, f"/api/backtest/trace/{rid}/trades/0"))
        assert {l["table"]: l["count"] for l in tr["links"]}["fills"] == 2
        # the old ten-tab view is not used for a road run
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/backtest/run/{rid}", timeout=20)
            raise AssertionError("old view answered 200")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
    finally:
        srv.shutdown()
        srv.server_close()
