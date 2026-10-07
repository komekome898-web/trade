"""道の記録の形の受け入れの場面 1〜5(委任文 DELEGATION_record_form.md「受け入れの場面」、RECORD_FORM_L766.md)。

足は道の走らせ(`bot.bt.pipeline`)の生成器 `random_walk` で作る(合成の足。市場のデータは読まない)。
手計算の数は、値段が動かない足(step_pct = 0)の上で書く:
- 1 段の量 = 200,000 × 0.70 ÷ 段数 ÷ 値段、0.001 BTC 未満切り捨て(L-745・L-746)
- 1 分足、足 k 本目(1 本目 = 0:00〜0:01)は 0:k に閉じて戦略に届く。足 3 本目が届いた 0:03 に合図の発生と買い、
  足 6 本目が届いた 0:06 に合図の消失と売り。成行は次の足の始まり(next_bar_open)の値で約定する(約定の時刻 = 0:03・0:06)
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys

from decimal import Decimal

import pytest

from bot.bt import pipeline as P
from bot.bt.core import BarEvent, OrderCanceledEvent, OrderRejectEvent
from bot.bt.costs import FxPoint
from bot.bt.road import DATA_END, NO_SIGNAL, ZERO_QTY_STATE, RoadStrategyError, check_outputs
from bot.bt.road.ledger import book
from bot.bt.road.tables import ROAD_DIR, SCHEMA, SCHEMA_FILE, columns, read_csv

M = 60_000_000_000  # 1 分(ns)
T0 = 1_700_000_040_000_000_000  # 分の区切り(0:00 とみなす。2023-11-14、合成の足の時刻)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(REPO, "scripts", "road", "check_outputs.py")
MODULE = "bot.strategy.road_scene_test"
ZERO = {"kind": "constant", "ns": 0}
TABLES7 = ("signals", "orders", "fills", "fx", "ledger_fills", "trades", "summary")


@pytest.fixture(scope="module", autouse=True)
def scene_module():
    """試験の戦略(tests/road/road_scene_strategy.py)を、道の走らせが受け付ける名 bot.strategy.road_scene_test で読む。"""
    spec = importlib.util.spec_from_file_location(MODULE, os.path.join(HERE, "road_scene_strategy.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[MODULE] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop(MODULE, None)


def _gen(price0, step_pct=0.0, n=30, seed=1):
    return {"name": "random_walk", "seed": seed, "params": {"kind": "bar", "start_ns": T0, "step_ns": M, "n": n,
                                                            "price0": price0, "step_pct": step_pct, "qty": 1.0}}


def _plan(root, gen, params, ccy="JPY", min_qty=0.001, feed=ZERO, rules=None):
    sym = "BTCJPY" if ccy == "JPY" else "XBTUSD"
    return P.plan_pipeline(
        root=str(root), datasets=[{"name": "g", "generator": gen}],
        instruments=[{"name": sym, "price": "g", "with": [],
                      "product": {"symbol": sym, "venue": "test", "tick": 0.5, "min_qty": min_qty, "qty_step": 0.001,
                                  "quote_ccy": ccy, "margin": True},
                      "rules": dict(rules or {"market_ref": "next_bar_open"})}],
        strategy={"kind": "module", "module": MODULE, "factory": "pipeline_strategy", "params": params},
        fill={"optimistic": {"tier": 2}, "pessimistic": {"tier": 2}},
        latency={"feed": feed, "order": ZERO, "cancel": ZERO, "notice": ZERO},
        costs={"maker_rate": 0, "taker_rate": 0, "spread": 0, "source": "試験: 0"},
        account={"currency": ccy, "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None,
                 "margin_check": "position_only"},
        purpose="動作確認", prereg=None)


def _run(root, gen, params, ccy="JPY", **kw):
    res = P.run_pipeline(_plan(root, gen, params, ccy, **kw), runs_dir=str(root / "runs"))
    return res, os.path.join(res.run_dir, ROAD_DIR)


def _bars(gen):
    return [{"t_ns": r["t_ns"], "high": r["high"], "low": r["low"]} for r in P._generate(gen)[1]]


def _tables(store):
    out = {t: read_csv(os.path.join(store, SCHEMA["tables"][t]["file"]), t)[1] for t in TABLES7 if t != "summary"}
    with open(os.path.join(store, "summary.json"), encoding="utf-8") as fh:
        out["summary"] = json.load(fh)
    return out


def _side(rows, side="pessimistic"):
    return [r for r in rows if r["range"] == side]


def _write_csv(path, head, rows):
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(head)
    for r in rows:
        w.writerow([r[c] for c in head])
    with gzip.open(path, "wb") as fh:
        fh.write(buf.getvalue().encode("utf-8"))


def _cli(store, bars, tmp_path):
    bp = tmp_path / "bars.json"
    bp.write_text(json.dumps(bars), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    return subprocess.run([sys.executable, SCRIPT, str(store), "--bars", str(bp)], capture_output=True, text=True,
                          env=env)


BASIC = {"mode": "basic", "quote_ccy": "JPY", "levels": 2, "open_bar": 3, "close_bar": 6}
GEN_5M = _gen(5_000_000.0)


@pytest.fixture(scope="module")
def basic_store(tmp_path_factory):
    root = tmp_path_factory.mktemp("basic")
    res, store = _run(root, GEN_5M, BASIC)
    return res, store


# ---------------------------------------------------------------- 場面 1: 7 つの表と SCHEMA、検査が通る、1 本につながる
def test_scene1_seven_tables_schema_and_check_pass(basic_store, tmp_path):
    res, store = basic_store
    assert sorted(os.listdir(store)) == sorted([SCHEMA_FILE] + [SCHEMA["tables"][t]["file"] for t in TABLES7])
    with open(os.path.join(store, SCHEMA_FILE), encoding="utf-8") as fh:
        assert json.load(fh) == SCHEMA
    for t in TABLES7:
        if t != "summary":
            head, _ = read_csv(os.path.join(store, SCHEMA["tables"][t]["file"]), t)
            assert head == columns(t)
    # 2 回の実行が同じバイト(gzip の時刻を 0 にしている)で、置き場の指紋に road/ の表も入る
    assert res.repro["identical"] is True
    assert {f"road/{SCHEMA['tables'][t]['file']}" for t in TABLES7} <= set(res.repro["sha256"])
    # 既存の書き出しはそのまま(読む口の一覧に road/ は入らない)
    assert sorted(res.exports) == ["data_quality.json", "fills.json", "metrics.json", "orders.json", "trades.json"]
    assert check_outputs(store, _bars(GEN_5M)).failures == []
    p = _cli(store, _bars(GEN_5M), tmp_path)
    assert p.returncode == 0 and "検査 通過" in p.stdout, p.stdout + p.stderr


def test_scene1_signal_order_fill_trade_is_one_chain(basic_store):
    _, store = basic_store
    t = _tables(store)
    for side in ("pessimistic", "optimistic"):
        sig = _side(t["signals"], side)
        orders = _side(t["orders"], side)
        fills = _side(t["fills"], side)
        lf = _side(t["ledger_fills"], side)
        trades = _side(t["trades"], side)
        # 手計算: 合図 s1 は 0:03 に発生、0:06 に消失
        assert [(s["signal_id"], s["start_t_ns"], s["end_t_ns"], s["end_reason"]) for s in sig] == [
            ("s1", str(T0 + 3 * M), str(T0 + 6 * M), "条件が外れた")]
        # 合図 → 注文: 買い 2 つは合図 s1(量の計算)、売りは「無し」の決済(flatten。量 = 建玉 0.014 × 2 = 0.028)
        assert [(o["order_id"], o["signal_id"], o["side"], o["qty"], o["state"], o["qty_source"],
                 o["position_at_send"]) for o in orders] == [
            ("road-0", "s1", "buy", "0.014", "FILLED", "量の計算", "0"),
            ("road-1", "s1", "buy", "0.014", "FILLED", "量の計算", "0"),
            ("road-2", NO_SIGNAL, "sell", "0.028", "FILLED", "建玉", "0.028")]
        # 決済の行は量の計算の列が空
        assert {c: orders[2][c] for c in ("margin_jpy", "use_ratio", "levels", "size_px", "size_px_source", "usdjpy",
                                           "usdjpy_t_ns", "qty_raw")} == dict.fromkeys(
            ("margin_jpy", "use_ratio", "levels", "size_px", "size_px_source", "usdjpy", "usdjpy_t_ns", "qty_raw"), "")
        # 注文 → 約定(表を結ぶ: 約定の注文の番号で注文の表を引く)
        by_order = {o["order_id"]: o for o in orders}
        assert [(f["fill_id"], f["order_id"], by_order[f["order_id"]]["signal_id"], f["signal_id"], f["t_ns"], f["qty"],
                 f["px"]) for f in fills] == [
            ("0", "road-0", "s1", "s1", str(T0 + 3 * M), "0.014", "5000000.0"),
            ("1", "road-1", "s1", "s1", str(T0 + 3 * M), "0.014", "5000000.0"),
            ("2", "road-2", NO_SIGNAL, NO_SIGNAL, str(T0 + 6 * M), "0.028", "5000000.0")]
        # 約定 → 取引: 3 つの約定が取引 0 に属し、取引 0 の合図は最初の約定の合図 s1
        assert [(r["fill_id"], r["trade_id"], r["position_after"], r["avg_px_after"]) for r in lf] == [
            ("0", "0", "0.014", "5000000"), ("1", "0", "0.028", "5000000"), ("2", "0", "0", "")]
        # 手計算: 段 2・最大の建玉 0.014 × 2 = 0.028・保有 0:03 → 0:06 = 3 分・損益 (5,000,000 − 5,000,000) × 0.028 = 0
        assert [(r["trade_id"], r["signal_id"], r["first_fill_id"], r["fill_count"], r["levels"], r["max_position"],
                 r["hold_ns"], r["pnl_jpy"], r["status"]) for r in trades] == [
            ("0", "s1", "0", "3", "2", "0.028", str(3 * M), "0", "closed")]
        # 円建て: 使った USDJPY は "1"、相場の時刻は空
        assert {(r["usdjpy"], r["usdjpy_t_ns"]) for r in lf + trades} == {("1", "")}
        assert t["fx"] == []
    assert t["summary"]["groups"] == [["BTCJPY", "optimistic"], ["BTCJPY", "pessimistic"]]
    assert t["summary"]["rows"] == [
        {"instrument": "BTCJPY", "range": side, "fill_count": 3, "closed_trades": 1, "pnl_jpy": "0", "open_trades": 0}
        for side in ("optimistic", "pessimistic")]


def test_scene1_order_lifecycle_times(basic_store):
    _, store = basic_store
    o = _side(_tables(store)["orders"])
    # 遅れ 0: 出した・受け付けられた時刻 = 足が届いた時刻。成行は次の足で全部約定(取り消し・期限切れは無い)
    assert [(r["placed_t_ns"], r["sent_t_ns"], r["acked_t_ns"], r["canceled_t_ns"], r["expired_t_ns"], r["filled_qty"])
            for r in o] == [(str(T0 + 3 * M), str(T0 + 3 * M), str(T0 + 3 * M), "", "", "0.014")] * 2 + [
        (str(T0 + 6 * M), str(T0 + 6 * M), str(T0 + 6 * M), "", "", "0.028")]


def test_scene1_limit_order_canceled_times(tmp_path):
    # 指値 2,500,000(終値 5,000,000 の半分)の買い、段数 1: 手計算 200,000 × 0.70 ÷ 1 ÷ 2,500,000 = 0.056。
    # 値段の動かない足では届かず、0:06 に取り消しを出し、遅れ 0 なので 0:06 に取り消しの答え(answers = cancel)が届く
    _, store = _run(tmp_path, GEN_5M, {"mode": "limit_cancel", "quote_ccy": "JPY", "levels": 1, "open_bar": 3,
                                       "close_bar": 6})
    t = _tables(store)
    o = _side(t["orders"])
    assert [(r["order_type"], r["limit_px"], r["size_px"], r["size_px_source"], r["qty"], r["sent_t_ns"],
             r["acked_t_ns"], r["cancel_sent_t_ns"], r["canceled_t_ns"], r["expired_t_ns"], r["close_kind"],
             r["state"], r["filled_qty"]) for r in o] == [
        ("limit", "2500000.0", "2500000.0", "指値", "0.056", str(T0 + 3 * M), str(T0 + 3 * M), str(T0 + 6 * M),
         str(T0 + 6 * M), "", "cancel", "CANCELED", "0")]
    assert t["fills"] == []
    assert check_outputs(store, _bars(GEN_5M)).failures == []


def test_scene1_random_walk_store_passes_check(tmp_path):
    # 値段が動く足でも、表がそろい検査が通る(手計算の数は持たない: つながりと検査だけを見る)
    gen = _gen(5_000_000.0, step_pct=0.3, n=40, seed=11)
    _, store = _run(tmp_path, gen, dict(BASIC, keep_open=True))
    assert check_outputs(store, _bars(gen)).failures == []
    t = _tables(store)
    assert len(_side(t["fills"])) == 3 and len(_side(t["signals"])) == 2


# ---------------------------------------------------------------- 場面 2: 量
def test_scene2_size_values_are_all_recorded(basic_store):
    _, store = basic_store
    o = _side(_tables(store)["orders"])[0]
    # 手計算: 200,000 × 0.70 ÷ 2 ÷ 5,000,000 = 0.014(切り捨て前もちょうど 0.014)
    assert {k: o[k] for k in ("margin_jpy", "use_ratio", "levels", "size_px", "size_px_source", "quote_ccy", "usdjpy",
                              "usdjpy_t_ns", "qty_raw", "qty")} == {
        "margin_jpy": "200000", "use_ratio": "0.7", "levels": "2", "size_px": "5000000.0",
        "size_px_source": "直近の足の終値", "quote_ccy": "JPY", "usdjpy": "", "usdjpy_t_ns": "", "qty_raw": "0.014",
        "qty": "0.014"}


def test_scene2_zero_size_is_not_sent_and_leaves_one_row(tmp_path):
    # 手計算: 200,000 × 0.70 ÷ 100 ÷ 5,000,000 = 0.00028 → 0.001 未満切り捨てで 0
    _, store = _run(tmp_path, GEN_5M, {"mode": "zero", "quote_ccy": "JPY", "levels": 100, "open_bar": 3})
    t = _tables(store)
    o = _side(t["orders"])
    assert [(r["order_id"], r["qty"], r["qty_raw"], r["levels"], r["state"], r["sent_t_ns"], r["placed_t_ns"])
            for r in o] == [("road-0", "0.0", "0.00028", "100", ZERO_QTY_STATE, "", str(T0 + 3 * M))]
    assert t["fills"] == [] and t["ledger_fills"] == [] and t["trades"] == []
    assert check_outputs(store, _bars(GEN_5M)).failures == []


# ---------------------------------------------------------------- 場面 3: 合図
@pytest.mark.parametrize("mode,msg", [("end_unknown", "合図 zz は発生していない(発生していない番号の消失)"),
                                      ("order_unknown", "合図 zz は発生していない(発生していない合図の番号の注文"),
                                      ("twice", "合図 s1 は既に発生している")])
def test_scene3_bad_signal_use_stops_the_run(tmp_path, mode, msg):
    with pytest.raises(RoadStrategyError) as ei:
        _run(tmp_path, GEN_5M, {"mode": mode, "quote_ccy": "JPY", "levels": 2, "open_bar": 3})
    assert msg in str(ei.value)
    assert not os.path.exists(tmp_path / "runs") or not [n for n in os.listdir(tmp_path / "runs")
                                                         if not n.startswith(".")]


def test_scene3_signal_alive_at_data_end(tmp_path):
    _, store = _run(tmp_path, GEN_5M, dict(BASIC, keep_open=True))
    s2 = [s for s in _side(_tables(store)["signals"]) if s["signal_id"] == "s2"]
    assert [(s["start_t_ns"], s["end_t_ns"], s["end_reason"]) for s in s2] == [(str(T0 + 3 * M), "", DATA_END)]
    assert check_outputs(store, _bars(GEN_5M)).failures == []


# ---------------------------------------------------------------- 場面 4: 検査の失敗
def _copy(basic_store, tmp_path):
    _, store = basic_store
    d = tmp_path / "store"
    shutil.copytree(store, d)
    return d


def _edit(d, table, fn):
    path = os.path.join(d, SCHEMA["tables"][table]["file"])
    head, rows = read_csv(path, table)
    head, rows = fn(head, rows)
    _write_csv(path, head, rows)


def _first_pess(rows, **kw):
    return next(k for k, r in enumerate(rows) if r["range"] == "pessimistic" and all(r[a] == b for a, b in kw.items()))


def _t_avg(head, rows):
    k = _first_pess(rows, fill_id="0")
    rows[k]["avg_px_after"] = "5000001"
    return head, rows


def _t_qty(head, rows):
    k = _first_pess(rows, order_id="road-0")
    rows[k]["qty"] = "0.015"  # 0.014 + 0.001
    return head, rows


def _t_sig_plus(head, rows):
    k = _first_pess(rows, signal_id="s1")
    rows[k]["start_t_ns"] = str(int(rows[k]["start_t_ns"]) + 20_000_000_000)
    return head, rows


def _t_sig_minus(head, rows):
    k = _first_pess(rows, signal_id="s1")
    rows[k]["start_t_ns"] = str(int(rows[k]["start_t_ns"]) - 20_000_000_000)
    return head, rows


def _t_fill_sig(head, rows):
    k = _first_pess(rows, fill_id="0")
    rows[k]["signal_id"] = "zz"
    return head, rows


def _t_fx_col(head, rows):
    return [c for c in head if c != "source"], rows


@pytest.mark.parametrize("table,fn,check,row_words", [
    ("ledger_fills", _t_avg, "ii", ["ledger_fills の", "約定 0", "avg_px_after"]),
    ("orders", _t_qty, "v", ["orders の", "注文 road-0", "計算し直した量"]),
    ("signals", _t_sig_plus, "iv", ["signals の", "合図 s1", "分の区切りから 20000000000 ns ずれている"]),
    ("signals", _t_sig_minus, "iv", ["signals の", "合図 s1", "分の区切りから 40000000000 ns ずれている"]),
    ("fills", _t_fill_sig, "iii", ["fills の", "約定 0", "合図の番号 'zz'"]),
    ("fx", _t_fx_col, "i", ["fx", "欠けた列 ['source']"]),
])
def test_scene4_tampered_store_fails_in_japanese(basic_store, tmp_path, table, fn, check, row_words):
    d = _copy(basic_store, tmp_path)
    _edit(d, table, fn)
    res = check_outputs(str(d), _bars(GEN_5M))
    assert not res.ok
    hits = [f for f in res.failures if f["check"] == check]
    assert hits, res.failures
    text = " ".join(f"{f['row']} {f['reason']}" for f in hits)
    for w in row_words:
        assert w in text, (w, res.failures)
    p = _cli(d, _bars(GEN_5M), tmp_path)
    assert p.returncode == 1 and "検査 失敗" in p.stdout, p.stdout + p.stderr
    assert "Traceback" not in p.stderr
    for line in p.stdout.splitlines()[1:]:
        assert re.search(r"[぀-ヿ一-鿿]", line), line  # 失敗した行は日本語
    print(p.stdout)


def test_scene4_signal_shifted_later_also_breaks_the_order_link(basic_store, tmp_path):
    # 発生を 20 秒後ろにずらすと、合図 s1 の買い(0:03 に受けた)が発生より前になる
    d = _copy(basic_store, tmp_path)
    _edit(d, "signals", _t_sig_plus)
    iii = [f for f in check_outputs(str(d), _bars(GEN_5M)).failures if f["check"] == "iii"]
    assert len(iii) == 2 and all("発生の時刻" in f["reason"] for f in iii)


# ---------------------------------------------------------------- 場面 5: ドル建て
FX = [{"t_ns": T0 - 60 * M, "pair": "USDJPY", "rate": 149.5}, {"t_ns": T0 + 2 * M, "pair": "USDJPY", "rate": 150.0},
      {"t_ns": T0 + 4 * M, "pair": "USDJPY", "rate": 151.0}]
GEN_30K = _gen(30_000.0)


def test_scene5_usd_rate_and_quote_time_on_ledger_rows(tmp_path):
    # USDT は道の走らせで回さない: 銘柄の値段の通貨は口座の通貨と同じでなければならず、口座(MarginAccount)は通貨に
    # 3 文字の符号しか受けない(「currency must be a 3-letter code, got 'USDT'」で止まる)。帳簿のツールの USDT は
    # test_road_ledger.py の場面 6 が見る
    ccy = "USD"
    params = {"mode": "basic", "quote_ccy": ccy, "levels": 2, "open_bar": 3, "close_bar": 6, "fx": FX,
              "fx_source": "試験の相場"}
    _, store = _run(tmp_path, GEN_30K, params, ccy)
    t = _tables(store)
    assert check_outputs(store, _bars(GEN_30K)).failures == []
    o = _side(t["orders"])
    # 手計算: 0:03 の最新の相場 = 0:02 の 150。200,000 × 0.70 ÷ 2 ÷ (30,000 × 150) = 0.01555… → 0.015
    # 0:06 の決済(flatten)の量 = 建玉 0.015 × 2 = 0.03。量の計算をしないので USDJPY の列は空
    assert [(r["qty"], r["usdjpy"], r["usdjpy_t_ns"], r["qty_source"]) for r in o] == [
        ("0.015", "150.0", str(T0 + 2 * M), "量の計算"), ("0.015", "150.0", str(T0 + 2 * M), "量の計算"),
        ("0.03", "", "", "建玉")]
    lf, trades = _side(t["ledger_fills"]), _side(t["trades"])
    # 取引の開始(最初の約定 0:03)以前の最後の相場 = 0:02 の 150。決済(0:06、その時 151)も開始の 150 で円に(L-764)
    start = int(trades[0]["first_t_ns"])
    last = max((p for p in FX if p["t_ns"] <= start), key=lambda p: p["t_ns"])
    assert (last["rate"], last["t_ns"]) == (150.0, T0 + 2 * M)
    assert [(r["usdjpy"], r["usdjpy_t_ns"]) for r in lf] == [("150", str(last["t_ns"]))] * 3
    assert [(r["usdjpy"], r["usdjpy_t_ns"], r["pnl_jpy"], r["status"]) for r in trades] == [
        ("150", str(last["t_ns"]), "0", "closed")]
    assert [(r["t_ns"], r["pair"], r["rate"], r["source"]) for r in _side(t["fx"])] == [
        (str(p["t_ns"]), "USDJPY", repr(p["rate"]), "試験の相場") for p in FX]


def test_scene5_ledger_rows_carry_rate_and_time_doten():
    # 帳簿のツールだけで: 0:00 に 0.01 を 30,000 USD で買い(相場 0:00 の 150)、0:05 に 0.02 を 30,100 で売る(ドテン。
    # その時 0:05 の 151)、0:08 に 0.01 を 30,000 で買い戻す。手計算: 閉じた側 1 USD × 150 = 150 円、新しい売りの取引
    # 1 USD × 151 = 151 円。ドテンの約定の行の相場は閉じた側の 150、新しい取引の行は 151
    fx = [FxPoint(time_ns=T0, pair="USDJPY", rate=150.0), FxPoint(time_ns=T0 + 5 * M, pair="USDJPY", rate=151.0),
          FxPoint(time_ns=T0 + 8 * M, pair="USDJPY", rate=152.0)]
    f = [{"t_ns": T0, "side": "buy", "qty": 0.01, "px": 30000, "ccy": "USD"},
         {"t_ns": T0 + 5 * M, "side": "sell", "qty": 0.02, "px": 30100, "ccy": "USD"},
         {"t_ns": T0 + 8 * M, "side": "buy", "qty": 0.01, "px": 30000, "ccy": "USD"}]
    led = book(f, fx)
    assert [(r["pnl_quote"], r["usdjpy"], r["usdjpy_t_ns"], r["pnl_jpy"]) for r in led.fills] == [
        ("0", "150", T0, "0"), ("1", "150", T0, "150"), ("1", "151", T0 + 5 * M, "151")]
    assert [(tr["usdjpy"], tr["usdjpy_t_ns"]) for tr in led.trades] == [("150", T0), ("151", T0 + 5 * M)]
    # 円建ては "1" と None
    j = book([{"t_ns": T0, "side": "buy", "qty": 0.01, "px": 10000, "ccy": "JPY"}])
    assert (j.fills[0]["usdjpy"], j.fills[0]["usdjpy_t_ns"], j.trades[0]["usdjpy"], j.trades[0]["usdjpy_t_ns"]) == \
        ("1", None, "1", None)


# ---------------------------------------------------------------- 2 周目 (d): 決済の口 flatten
def test_r2_flatten_on_moving_bars_returns_position_to_zero(tmp_path):
    # 値段が動く足: 0:03 と 0:04 の買いは、その時の値段が違うので量が違う。0:08 の flatten の量 = その 2 つの和
    gen = _gen(1_000_000.0, step_pct=2.0, n=30, seed=1)
    _, store = _run(tmp_path, gen, {"mode": "ladder", "quote_ccy": "JPY", "levels": 2, "open_bar": 3, "close_bar": 8})
    assert check_outputs(store, _bars(gen)).failures == []
    t = _tables(store)
    for side in ("pessimistic", "optimistic"):
        o = _side(t["orders"], side)
        buys = [Decimal(r["qty"]) for r in o if r["qty_source"] == "量の計算"]
        assert len(buys) == 2 and buys[0] != buys[1]
        fl = [r for r in o if r["qty_source"] == "建玉"]
        assert [(r["side"], Decimal(r["qty"]), r["position_at_send"], r["signal_id"], r["state"]) for r in fl] == [
            ("sell", sum(buys), str(sum(buys)), "s1", "FILLED")]
        lf = _side(t["ledger_fills"], side)
        assert lf[-1]["position_after"] == "0"
        assert [(r["status"], r["levels"], r["fill_count"]) for r in _side(t["trades"], side)] == [("closed", "2", "3")]


def test_r2_flatten_without_position_leaves_a_zero_row(tmp_path):
    _, store = _run(tmp_path, GEN_5M, {"mode": "flatten_empty", "quote_ccy": "JPY", "levels": 1, "open_bar": 3})
    t = _tables(store)
    assert [(r["qty"], r["qty_source"], r["position_at_send"], r["state"], r["sent_t_ns"], r["side"])
            for r in _side(t["orders"])] == [("0.0", "建玉", "0", ZERO_QTY_STATE, "", "")]
    assert check_outputs(store, _bars(GEN_5M)).failures == []


def _t_flat_qty(head, rows):
    k = _first_pess(rows, order_id="road-2")
    rows[k]["qty"] = "0.029"
    return head, rows


def test_r2_check_v_fails_when_flatten_qty_is_not_the_position(basic_store, tmp_path):
    d = _copy(basic_store, tmp_path)
    _edit(d, "orders", _t_flat_qty)
    f = [x for x in check_outputs(str(d), _bars(GEN_5M)).failures if x["check"] == "v"]
    assert len(f) == 1 and "注文 road-2" in f[0]["row"] and "建玉 0.028 の絶対値 '0.028'" in f[0]["reason"], f


# ---------------------------------------------------------------- 2 周目 (b): 拒否と期限切れを分ける
def test_r2_rejections_go_to_rejected_not_expired(tmp_path):
    # 最小の量 0.1 BTC の銘柄に 0.014 BTC(段数 2)を出す: 成行は門が預けて取引所が拒む(answers = venue、理由
    # rejected_by_venue: ...)、指値は取引所がその場で拒む(OrderRejectEvent)。どちらも拒否の時刻に入り、期限切れは空
    _, store = _run(tmp_path, GEN_5M, {"mode": "reject", "quote_ccy": "JPY", "levels": 2, "open_bar": 3}, min_qty=0.1,
                    rules={"market_ref": "next_bar_open", "below_min_qty": "reject"})
    o = _side(_tables(store)["orders"])
    got = [(r["order_type"], r["close_kind"], r["close_reason"].split(":")[0], r["rejected_t_ns"] != "",
            r["expired_t_ns"], r["canceled_t_ns"]) for r in o]
    assert got == [("market", "venue", "rejected_by_venue", True, "", ""), ("limit", "reject", got[1][2], True, "", "")]
    assert all(r["state"] in ("CANCELED", "REJECTED") for r in o)
    assert check_outputs(store, _bars(GEN_5M)).failures == []


class _View:
    def __init__(self, state):
        self.state = state


class _Ctx:
    """土台の知らせの分け方だけを見るための、最小の文脈(core の StrategyContext の now_ns・order・place_order の形)。"""
    def __init__(self, now):
        self.now_ns = now

    def place_order(self, req):
        return req.client_order_id

    def order(self, coid):
        from bot.bt.core.api import OrderState
        return _View(OrderState.CANCELED)


@pytest.mark.parametrize("make,col", [
    (lambda c: OrderCanceledEvent(received_time_ns=T0 + 5 * M, client_order_id=c, reason="expired", answers="venue"),
     "expired_t_ns"),
    (lambda c: OrderCanceledEvent(received_time_ns=T0 + 5 * M, client_order_id=c, reason="rejected_by_venue: x",
                                  answers="venue"), "rejected_t_ns"),
    # 門が口座の確かめで止めたもの(pipeline.py の "refused_by_account: ...")も拒否(リードの直し)
    (lambda c: OrderCanceledEvent(received_time_ns=T0 + 5 * M, client_order_id=c, reason="refused_by_account: x",
                                  answers="venue"), "rejected_t_ns"),
    (lambda c: OrderRejectEvent(received_time_ns=T0 + 5 * M, client_order_id=c, reason="below_min_qty"),
     "rejected_t_ns"),
    (lambda c: OrderCanceledEvent(received_time_ns=T0 + 5 * M, client_order_id=c, reason="canceled", answers="cancel"),
     "canceled_t_ns"),
    (lambda c: OrderCanceledEvent(received_time_ns=T0 + 5 * M, client_order_id=c, reason="ioc_remainder",
                                  answers="new"), None),
])
def test_r2_close_notice_columns(scene_module, make, col):
    s = scene_module.SceneStrategy({"mode": "nothing", "quote_ccy": "JPY", "levels": 1, "open_bar": 1})
    s.on_event(BarEvent(received_time_ns=T0 + M, start_time_ns=T0, open=1e6, high=1e6, low=1e6, close=1e6, volume=1.0),
               _Ctx(T0 + M))
    s._ctx = _Ctx(T0 + M)
    coid = s.place("buy", "market", None, 1, NO_SIGNAL)
    s._ctx = None
    s.on_event(make(coid), _Ctx(T0 + 5 * M))
    row = s.road_record()["orders"][0]
    cols = ("expired_t_ns", "rejected_t_ns", "canceled_t_ns")
    assert {c: row[c] for c in cols} == {c: (T0 + 5 * M if c == col else "") for c in cols}
    assert row["closed_t_ns"] == T0 + 5 * M


# ---------------------------------------------------------------- 2 周目 (e): 足の遅れが 0 でない走らせは (iv) に落ちる
def test_r2_feed_latency_fails_signal_bar_check(tmp_path):
    feed = {"kind": "constant", "ns": 1_000_000_000}  # 足が 1 秒遅れて届く
    _, store = _run(tmp_path, GEN_5M, BASIC, feed=feed)
    f = [x for x in check_outputs(store, _bars(GEN_5M)).failures if x["check"] == "iv"]
    assert f and all("signals の" in x["row"] and "分の区切りから 1000000000 ns ずれている" in x["reason"] for x in f), f
    from bot.bt.road import check as C
    assert "足の遅れ(feed の遅延)が 0 でない走らせでは" in C.__doc__


# ---------------------------------------------------------------- 2 周目 (f): 何もしなかった (銘柄, 側) も summary に行
def test_r2_summary_rows_for_groups_with_nothing(tmp_path):
    res, store = _run(tmp_path, GEN_5M, {"mode": "nothing", "quote_ccy": "JPY", "levels": 1, "open_bar": 3})
    t = _tables(store)
    assert t["signals"] == [] and t["orders"] == [] and t["fills"] == []
    assert t["summary"] == {"version": SCHEMA["version"], "groups": [["BTCJPY", "optimistic"], ["BTCJPY", "pessimistic"]],
                            "rows": [{"instrument": "BTCJPY", "range": r, "fill_count": 0, "closed_trades": 0,
                                      "pnl_jpy": "0", "open_trades": 0} for r in ("optimistic", "pessimistic")]}
    assert check_outputs(store, _bars(GEN_5M)).failures == []
    # 走らせの置き場ごと写し、summary から 1 つの組を消す: 走らせの記録(record.json)の銘柄 × 側と違うので失敗
    run = tmp_path / "copy"
    shutil.copytree(res.run_dir, run)
    path = run / ROAD_DIR / "summary.json"
    sm = json.loads(path.read_text(encoding="utf-8"))
    sm["groups"] = sm["groups"][1:]
    sm["rows"] = sm["rows"][1:]
    path.write_text(json.dumps(sm, ensure_ascii=False), encoding="utf-8")
    f = check_outputs(str(run / ROAD_DIR), _bars(GEN_5M)).failures
    assert any(x["check"] == "ii" and "record.json" in x["reason"] for x in f), f
