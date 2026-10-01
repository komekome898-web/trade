"""The integrated run on the environment's REAL data (item 4, old item 13:
「§1 の実データ(bitFlyer の約定 + 板 top10 の 1 日、Binance aggTrades の 1 日、FX のイベントティック
1 日、JPX と FX の 1 分足)を新エンジンに通し、実行記録・指標の書き出し・ダッシュボードまで」).

Purpose 動作確認, the fixed time-only procedure only (委任文 §4): per
instrument, two round trips in one hour hh of DAYS: buy 1 unit at hh:20,
sell at hh:25, buy at hh:50, sell at hh:55 (`schedule()`). Every time lies
inside every file's time span: the FX event-tick file covers 12:15:01 to
13:14:59 UTC of 2026-08-07 only (its first and last `ts_utc`, read with
`zcat ... | sed -n 2p` / `tail -1`); until round 2 the second round trip
was an hour later, outside that span, and its buy stayed OPEN -- the check
then accepted OPEN, which hid it (critic i4-r1-14). The test asserts the run's
STRUCTURE only -- it reaches the run record, the exports and the dashboard's
10 tabs, every tab carries the 動作確認 banner, every export carries the
purpose, every dataset is recorded as real with the evidence of its rows (finishing
stage i4-r2-03: the rows equal a market file's rows through the data layer),
both sides of the fill range ran through the item-2 venue, latency, cost and
account models (i4-r2-06), every scheduled order ends FILLED with its whole
quantity on both sides (an order left OPEN / ACKED / unanswered
fails the test) -- and never a number the data produced (委任文 §4:
実データから出た数値は ... 入れない).

Binance aggTrades: the spot BTCUSDT day files this item names are not in
this environment -- tried `find backtest_data -iname "*aggTrades*" -type f`:
binance_BTCUSDT_aggTrades_tardis_days/, binance_BTCUSDT_aggTrades_20260723_20260906/
and binance_um_BTCUSDT_aggTrades_20260723_20260906/ hold README.md and
MD5SUMS only; the owner's PC is not checked. What IS here and not used:
audit_fetch_P2-08b_20260906/binance_aggTrades_2019-06-01_head5.csv (the
first 5 rows of a day, not a day) and
binance_cm_o3c_20260913/aggTrades/BTCUSD_PERP/*.zip (COIN-M perpetual, zip:
the data layer reads "none" / "gzip" only; and the folder is the o3c
study's download, which the delegation says not to read as market data --
whether its raw zips may be read is a question to the lead). So this is
data wait (データ待ち) for the smoke run; test_binance_spot_aggtrades_is_data_wait
pins the fact so it is re-read when the files arrive. The same declaration
runs on the battery's synthetic aggTrades file (i4-5-fills).
Bars whose label (start / end) the source does not state (the 225Labo
1-minute file) are declared "start" here; that is a declaration for this
smoke run, not a checked fact. The same file has rows out of time order
(the data layer reports them as "backward"); the run names the policy
"sort" for them (recorded in the data-quality export), a choice for this
smoke run.
Sealed windows are not read (the data layer refuses them: SEALED.json of
P2-08b seals the bitFlyer tape executions from 2026-08-23 and P2-01 the
Nikkei 225 futures 1-minute bars): the days chosen are outside every seal
(bitFlyer tape 2026-09-21 -- its file is not in any SEALED.json --, TOPIX
futures 1-minute bars of 2026-08-21, the NFP event ticks of 2026-08-07,
USD/JPY 1-minute bars of 2026-08-21), found with
`grep -l <file> backtest_data/phase2_sealed/*/SEALED.json` (no hit).

Round 2 of the k1 env fixes (2026-09-30, delegation docs/DATA/delegations/20260927_k1_env_fixes.md §4 (d)3): the
files above (the bitFlyer tape of 2026-09-21, the NFP event ticks, the TOPIX futures and USD/JPY 1-minute files) are
data after 2026-08-28, data not consumed, or (the USD/JPY file) a file the consumption log's row "USD/JPY 1分足
3.5年" could not be tied to; they are no longer read. Now:
- bitFlyer (trade + book): REAL, the executions and board top-5 1-second snapshots of 2026-08-21 00:00-05:59 UTC
  (the rows before BF_CUT; the board file holds a row with an ask of 0.0 later that day, which the data layer
  refuses as a book) in backtest_data/auto_bitflyer_executions_20260905/ -- consumed (docs/DATA_CONSUMPTION_LOG.md §1), rows before
  2026-08-28, in no SEALED.json (docs/PHASE2/K1/NEWENV_A/FIXES.md §11). The book has 5 levels (was 10).
- FX event ticks, TOPIX-futures-like 1-minute bars (with two rows out of time order, so the "sort" policy still
  runs) and USD/JPY-like 1-minute bars: SYNTHETIC files in the same formats (`_synthetic_files`, seeded).
All five files are written into a temporary environment (the bitFlyer files as copies of those rows) that is the run's root
and pipeline.MARKET_BASE, so the evidence of every dataset is its rows in that environment's market folder. What the
test asserts is unchanged (the run's structure, never a number the data produced). The run no longer shows that the
FX / JPX file formats of this repository's real files parse: only the synthetic files in their formats do.
"""
from __future__ import annotations

import calendar
import os
import tempfile
from pathlib import Path

import pytest

import i4w_decl as D
from bot.bt.pipeline import plan_pipeline, run_pipeline
from bot.bt.report.exports import read_export
from bot.monitoring.backtest_view import TABS, WARNING, run_view

REPO = Path(__file__).resolve().parents[3]
NS = 1_000_000_000
BF_SRC = "backtest_data/auto_bitflyer_executions_20260905"
BF_CUT = "2026-08-21T06:00"  # the bitFlyer rows kept: 00:00-05:59 UTC of 2026-08-21


def t(y, mo, d, h=0, mi=0, off_h=0):
    return (calendar.timegm((y, mo, d, h, mi, 0, 0, 0, 0)) - off_h * 3600) * NS


FILES = {
    "bf_trades": "backtest_data/bf/executions_20260821.csv.gz",
    "bf_board": "backtest_data/bf/board_top5_20260821.csv.gz",
    "fx_ticks": "backtest_data/syn/fx_event_ticks_like.csv.gz",
    "jpx_1m": "backtest_data/syn/topixf_like_bars_1min.csv.gz",
    "fx_1m": "backtest_data/syn/usdjpy_like_1m.csv.gz",
}
LEVELS = 5
BOOK = {"levels": LEVELS,
        **{f"{s}_{k}": [f"{s}_{k}_{i}" for i in range(1, LEVELS + 1)] for s in ("bid", "ask") for k in ("px", "sz")}}
OHLCV = {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}


def _synthetic_files() -> dict:
    """Seeded synthetic files in the formats of the files read before round 2."""
    import random
    rnd = random.Random(20260930)
    fx = ["ts_utc,bid,ask,bidvol,askvol"]
    mid, t0 = 147.0, t(2026, 8, 7, 12) // 1_000_000  # ms, 12:00:00 UTC, one quote a second for an hour
    for k in range(3600):
        mid = round(mid + rnd.choice((-0.003, 0.0, 0.003)), 3)
        fx.append(f"{t0 + k * 1000},{mid - 0.0025:.4f},{mid + 0.0025:.4f},{rnd.randint(1, 9)},{rnd.randint(1, 9)}")
    jpx, px = ["date,time,open,high,low,close,volume"], 3000.0
    rows = []
    for k in range(390):  # 08:45-15:14 JST, the bar's start
        h, m = divmod(8 * 60 + 45 + k, 60)
        o, c = px, px + rnd.choice((-1.0, -0.5, 0.0, 0.5, 1.0))
        rows.append(f"2026-08-21,{h:02d}:{m:02d},{o:.1f},{max(o, c) + 0.5:.1f},{min(o, c) - 0.5:.1f},{c:.1f},"
                    f"{rnd.randint(10, 99)}")
        px = c
    rows[200], rows[201] = rows[201], rows[200]  # two rows out of time order (the data layer's "backward")
    jpx += rows
    fx1, px = ["timestamp,open,high,low,close,volume"], 147.0
    for k in range(720):  # 2026-08-21 00:00-11:59 UTC
        h, m = divmod(k, 60)
        o, c = px, round(px + rnd.choice((-0.01, 0.0, 0.01)), 3)
        fx1.append(f"2026-08-21T{h:02d}:{m:02d}:00Z,{o:.3f},{max(o, c) + 0.005:.3f},{min(o, c) - 0.005:.3f},{c:.3f},"
                   f"{rnd.randint(1, 50)}")
        px = c
    return {FILES["fx_ticks"]: "\n".join(fx) + "\n", FILES["jpx_1m"]: "\r\n".join(jpx) + "\r\n",
            FILES["fx_1m"]: "\n".join(fx1) + "\n"}


def datasets():
    gz = {"compression": "gzip", "format": "csv", "header": True, "delimiter": ","}
    return [
        {"name": "bf_trades", "paths": [FILES["bf_trades"]], "origin": "real",
         "spec": {**gz, "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto",
                  "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
                  "fields": {"px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}}},
        {"name": "bf_board", "paths": [FILES["bf_board"]], "origin": "real",
         "spec": {**gz, "kind": "book", "symbol": "FX_BTC_JPY", "asset": "crypto",
                  "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"}, "fields": BOOK}},
        {"name": "fx_ticks", "paths": [FILES["fx_ticks"]], "origin": "real",
         "spec": {**gz, "kind": "quote", "symbol": "USDJPY", "asset": "fx",
                  "time": {"columns": ["ts_utc"], "unit": "ms", "tz": "UTC"},
                  "fields": {"bid": "bid", "ask": "ask", "bid_qty": "bidvol", "ask_qty": "askvol"}}},
        {"name": "jpx_1m", "paths": [FILES["jpx_1m"]], "origin": "real", "resolve": {"backward": "sort"},
         "range_ns": [t(2026, 8, 21, off_h=9), t(2026, 8, 22, off_h=9)],
         "spec": {**gz, "kind": "bar", "symbol": "TOPIXF", "asset": "jpx",
                  "time": {"columns": ["date", "time"], "join": " ", "unit": "iso", "tz": "Asia/Tokyo"},
                  "fields": OHLCV, "bar": {"interval_s": 60, "label": "start"}, "key": "start"}},
        {"name": "fx_1m", "paths": [FILES["fx_1m"]], "origin": "real", "range_ns": [t(2026, 8, 21), t(2026, 8, 22)],
         "spec": {**gz, "kind": "bar", "symbol": "USDJPY", "asset": "fx",
                  "time": {"columns": ["timestamp"], "unit": "iso", "tz": "UTC"},
                  "fields": OHLCV, "bar": {"interval_s": 60, "label": "start", "session": "24x5"}, "key": "start"}},
    ]


INSTRUMENTS = [D.instrument("bf", "bf_trades", "trade", ["bf_board"]),
               D.instrument("fx_tick", "fx_ticks", "quote"),
               D.instrument("jpx", "jpx_1m", "bar"),
               D.instrument("fx_1m", "fx_1m", "bar")]
QTY = {"bf": 0.01, "fx_tick": 1.0, "jpx": 1.0, "fx_1m": 1.0}  # bf: a size the displayed top-5 book holds
DAYS = {"bf": (2026, 8, 21, 0, 0), "fx_tick": (2026, 8, 7, 12, 0), "jpx": (2026, 8, 21, 1, 0), "fx_1m": (2026, 8, 21, 1, 0)}


def schedule():
    orders = []
    for name, (y, mo, d, h, _) in DAYS.items():
        for m in (20, 50):
            orders += [{"t_ns": t(y, mo, d, h, m), "side": "buy", "qty": QTY[name], "instrument": name},
                       {"t_ns": t(y, mo, d, h, m + 5), "side": "sell", "qty": QTY[name], "instrument": name}]
    return {"kind": "schedule", "orders": orders}


def _missing():
    return [f"{BF_SRC}/{os.path.basename(FILES[k])}" for k in ("bf_trades", "bf_board")
            if not (REPO / BF_SRC / os.path.basename(FILES[k])).is_file()]


@pytest.fixture
def env():
    """The run's root and pipeline.MARKET_BASE: the two bitFlyer files (byte copies) and the synthetic files."""
    import gzip
    import shutil
    from bot.bt import pipeline as P
    tmp = tempfile.mkdtemp(prefix="i4w_real_env_")
    for k in ("bf_trades", "bf_board"):  # the rows before BF_CUT (the board file has a row with ask 0.0 at 18:4x UTC,
        dst = os.path.join(tmp, FILES[k])  # which the data layer refuses as a book: not a question of this test)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with gzip.open(REPO / BF_SRC / os.path.basename(FILES[k]), "rt", encoding="utf-8", newline="") as fh:
            lines = [ln for i, ln in enumerate(fh) if i == 0 or ln[:len(BF_CUT)] < BF_CUT]
        with open(dst, "wb") as fh:
            fh.write(gzip.compress("".join(lines).encode("utf-8"), mtime=0))
    for rel, body in _synthetic_files().items():
        dst = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(gzip.compress(body.encode(), mtime=0))
    mp = pytest.MonkeyPatch()
    mp.setattr(P, "MARKET_BASE", tmp)
    yield tmp
    mp.undo()
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.skipif(bool(_missing()), reason="the bitFlyer files of 2026-08-21 are not in this environment")
def test_real_data_reaches_record_exports_and_dashboard_under_the_smoke_purpose(env):
    runs = tempfile.mkdtemp(prefix="i4w_real_runs_")
    plan = plan_pipeline(root=env, datasets=datasets(), instruments=INSTRUMENTS, strategy=schedule(),
                         purpose="動作確認", **D.kw())
    res = run_pipeline(plan, runs_dir=runs)
    assert res.repro["identical"] is True
    assert set(res.record["data_sha256"]) == set(FILES.values())
    assert set(res.exports.values()) == {"動作確認"}
    for name in res.exports:
        body = read_export(os.path.join(res.run_dir, name))
        assert body["purpose"] == "動作確認" and body["warning"] == WARNING
    view = run_view(runs, res.run_id)
    assert [x["label"] for x in view["tabs"]] == list(TABS)
    assert all(WARNING in x["text"] for x in view["tabs"])
    assert {d["origin"] for d in res.record["data"]} == {"real"}
    assert {d["origin_evidence"]["by"] for d in res.record["data"]} == {"rows"}  # the rows match the market files
    assert set(res.record["components"]["models"]) == {"optimistic", "pessimistic"}  # both sides ran (i4-r2-06)
    for side, per in res.range.items():
        for name, r in per.items():
            assert len(r.orders) == 4, (side, name)
            for o in r.orders:
                assert o["state"] == "FILLED" and o["filled"] == pytest.approx(o["qty"]), (side, name, o["id"], o["state"])
            assert all(v > 0 for v in r.events_read.values()), (side, name)
    for name in res.instruments:
        acc = res.record["components"]["account"]["pessimistic"][name]
        assert acc["position"] == pytest.approx(0.0, abs=1e-9) and acc["currency"] == "JPY", name  # margin recorded


SPOT_AGG_DIRS = ("binance_BTCUSDT_aggTrades_tardis_days", "binance_BTCUSDT_aggTrades_20260723_20260906",
                 "binance_um_BTCUSDT_aggTrades_20260723_20260906")


def test_binance_spot_aggtrades_is_data_wait():
    for d in SPOT_AGG_DIRS:
        files = sorted(os.listdir(REPO / "backtest_data" / d)) if (REPO / "backtest_data" / d).is_dir() else []
        assert set(files) <= {"README.md", "MD5SUMS"}, (
            f"{d} now holds data files: add a Binance aggTrades day to the real-data smoke run", files[:5])
