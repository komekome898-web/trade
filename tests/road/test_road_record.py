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
import hashlib
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


def _plan(root, gen, params, ccy="JPY", min_qty=0.001, feed=ZERO, rules=None, notice=ZERO):
    sym = "BTCJPY" if ccy == "JPY" else "XBTUSD"
    return P.plan_pipeline(
        root=str(root), datasets=[{"name": "g", "generator": gen}],
        instruments=[{"name": sym, "price": "g", "with": [],
                      "product": {"symbol": sym, "venue": "test", "tick": 0.5, "min_qty": min_qty, "qty_step": 0.001,
                                  "quote_ccy": ccy, "margin": True},
                      "rules": dict(rules or {"market_ref": "next_bar_open"})}],
        strategy={"kind": "module", "module": MODULE, "factory": "pipeline_strategy", "params": params},
        fill={"optimistic": {"tier": 2}, "pessimistic": {"tier": 2}},
        latency={"feed": feed, "order": ZERO, "cancel": ZERO, "notice": notice},
        costs={"maker_rate": 0, "taker_rate": 0, "spread": 0, "source": "試験: 0"},
        account={"currency": ccy, "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None,
                 "margin_check": "position_only"},
        purpose="動作確認", prereg=None)


def _run(root, gen, params, ccy="JPY", **kw):
    res = P.run_pipeline(_plan(root, gen, params, ccy, **kw), runs_dir=str(root / "runs"))
    return res, os.path.join(res.run_dir, ROAD_DIR)


def _bars(gen):
    return [{"t_ns": r["t_ns"], "high": r["high"], "low": r["low"], "close": r["close"]} for r in P._generate(gen)[1]]


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
    assert [(r["placed_t_ns"], r["sent_t_ns"], r["acked_t_ns"], r["canceled_t_ns"], r["venue_closed_t_ns"], r["filled_qty"])
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
             r["acked_t_ns"], r["cancel_sent_t_ns"], r["canceled_t_ns"], r["venue_closed_t_ns"], r["close_kind"],
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
    """走らせの置き場ごと写し、写した road/ を返す(検査は road/ の外の repro.json・record.json・fills.json・orders.json も読む)。"""
    res, _ = basic_store
    run = tmp_path / "run"
    shutil.copytree(res.run_dir, run)
    return run / ROAD_DIR


def _forge_repro(d):
    """書き換えた人が repro.json の road/ の指紋も合わせた場合(指紋の突き合わせの後ろの検査だけを見るため)。"""
    rp = os.path.join(os.path.dirname(str(d)), "repro.json")
    with open(rp, encoding="utf-8") as fh:
        body = json.load(fh)
    for n in os.listdir(d):
        with open(os.path.join(d, n), "rb") as fh:
            body["sha256"][f"{ROAD_DIR}/{n}"] = hashlib.sha256(fh.read()).hexdigest()
    with open(rp, "w", encoding="utf-8") as fh:
        json.dump(body, fh)


def _edit(d, table, fn, forge=True):
    path = os.path.join(d, SCHEMA["tables"][table]["file"])
    head, rows = read_csv(path, table)
    head, rows = fn(head, rows)
    _write_csv(path, head, rows)
    if forge:
        _forge_repro(d)


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
    assert len(f) == 1 and "注文 road-2" in f[0]["row"] and "建玉 0.028 と出ていた決済の量 0 から決まる量 '0.028'" in \
        f[0]["reason"], f


# ---------------------------------------------------------------- 2 周目 (b): 拒否と期限切れを分ける
def test_r2_rejections_go_to_rejected_not_expired(tmp_path):
    # 最小の量 0.1 BTC の銘柄に 0.014 BTC(段数 2)を出す: 成行は門が預けて取引所が拒む(answers = venue、理由
    # rejected_by_venue: ...)、指値は取引所がその場で拒む(OrderRejectEvent)。どちらも拒否の時刻に入り、期限切れは空
    _, store = _run(tmp_path, GEN_5M, {"mode": "reject", "quote_ccy": "JPY", "levels": 2, "open_bar": 3}, min_qty=0.1,
                    rules={"market_ref": "next_bar_open", "below_min_qty": "reject"})
    o = _side(_tables(store)["orders"])
    got = [(r["order_type"], r["close_kind"], r["close_reason"].split(":")[0], r["rejected_t_ns"] != "",
            r["venue_closed_t_ns"], r["canceled_t_ns"]) for r in o]
    assert got == [("market", "venue", "rejected_by_venue", True, "", ""), ("limit", "reject", got[1][2], True, "", "")]
    assert all(r["state"] in ("CANCELED", "REJECTED") for r in o)
    assert check_outputs(store, _bars(GEN_5M)).failures == []


class _View:
    def __init__(self, state):
        self.state = state
        self.cancel_pending = False


class _Ctx:
    """土台の知らせの分け方だけを見るための、最小の文脈(core の StrategyContext の now_ns・order・place_order の形)。"""
    def __init__(self, now):
        self.now_ns = now

    def place_order(self, req):
        return req.client_order_id

    def cancel_order(self, coid):
        return None

    def order(self, coid):
        from bot.bt.core.api import OrderState
        return _View(OrderState.CANCELED)


@pytest.mark.parametrize("make,col", [
    (lambda c: OrderCanceledEvent(received_time_ns=T0 + 5 * M, client_order_id=c, reason="expired", answers="venue"),
     "venue_closed_t_ns"),
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
    if col == "canceled_t_ns":
        s.cancel(coid)  # 取り消しの答えは土台の cancel を通った取り消しにだけ届く(3 周目 問 1 (5))
    s._ctx = None
    s.on_event(make(coid), _Ctx(T0 + 5 * M))
    row = s.road_record()["orders"][0]
    cols = ("venue_closed_t_ns", "rejected_t_ns", "canceled_t_ns")
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


# ================================================================ 3 周目(批評家 1 回目の指摘。DELEGATION_record_form.md「## 3 周目」)
from bot.bt.core import OrderStateUnknownEvent  # noqa: E402
from bot.bt.road.tables import CSV_TABLES, write_tables  # noqa: E402

GEN_LIMIT = {"mode": "limit_cancel", "quote_ccy": "JPY", "levels": 1, "open_bar": 3, "close_bar": 6}
USD_BASIC = {"mode": "basic", "quote_ccy": "USD", "levels": 2, "open_bar": 3, "close_bar": 6, "fx": FX,
             "fx_source": "試験の相場"}


def _mutate(col, v):
    """批評家の sweep.py と同じ書き換え(時刻は +1 分、数は +0.001 か +1、文字は後ろに x)。"""
    if col.endswith("_t_ns") or col == "hold_ns":
        return str(int(v) + M) if v else str(T0 + 4 * M)
    if v == "":
        return "1"
    try:
        x = float(v)
    except ValueError:
        return v + "x"
    if col in ("qty", "filled_qty", "position_after", "max_position", "position", "position_at_send", "qty_raw",
               "exit_pending_at_send"):
        return repr(round(x + 0.001, 6))
    if "." in v:
        return repr(x + 1.0)
    return str(int(x) + 1)


def _sweep(res, gen, tmp_path, forge, all_rows=False):
    """悲観側の最初の行(all_rows なら悲観側の全部の行)を、表ごと・欄ごとに 1 欄ずつ書き換え、検査を通った欄を返す。"""
    store = os.path.join(res.run_dir, ROAD_DIR)
    passed = []
    for t in CSV_TABLES:
        head, rows = read_csv(os.path.join(store, SCHEMA["tables"][t]["file"]), t)
        idx = [i for i, r in enumerate(rows) if r["range"] == "pessimistic"]
        if not idx:
            continue
        for k in (idx if all_rows else idx[:1]):
            for c in head:
                run = tmp_path / f"sw-{t}-{k}-{c}"
                shutil.copytree(res.run_dir, run)

                def fn(h, rs, c=c, k=k):
                    rs[k][c] = _mutate(c, rs[k][c])
                    return h, rs
                _edit(run / ROAD_DIR, t, fn, forge=forge)
                if not check_outputs(str(run / ROAD_DIR), _bars(gen)).failures:
                    passed.append(f"{t}[{k}].{c}" if all_rows else f"{t}.{c}")
                shutil.rmtree(run)
    return passed


# 問 2(sweep.py): repro.json の指紋を合わせずに書き換えた欄は全部落ちる。合わせた場合に通る欄は SCHEMA の限界に書いた欄
_FORGED_PASS = {
    "JPY": ["signals.kind", "signals.direction", "signals.end_t_ns", "signals.end_reason", "orders.acked_t_ns",
            "orders.cancel_sent_t_ns", "orders.cancel_rejected_t_ns", "orders.state_unknown_t_ns"],
    "USD": ["signals.kind", "signals.direction", "signals.end_t_ns", "signals.end_reason", "orders.acked_t_ns",
            "orders.cancel_sent_t_ns", "orders.cancel_rejected_t_ns", "orders.state_unknown_t_ns", "fx.t_ns", "fx.rate",
            "fx.source"],
    "LIMIT": ["signals.kind", "signals.direction", "orders.placed_seq", "orders.acked_t_ns",
              "orders.cancel_rejected_t_ns", "orders.state_unknown_t_ns", "orders.closed_seq", "orders.close_reason"],
}


@pytest.mark.parametrize("kind", ["JPY", "USD", "LIMIT"])
def test_r3_sweep_every_field(tmp_path, kind):
    if kind == "JPY":
        res, _ = _run(tmp_path, GEN_5M, dict(BASIC, keep_open=True))
        gen = GEN_5M
    elif kind == "USD":
        res, _ = _run(tmp_path, GEN_30K, USD_BASIC, "USD")
        gen = GEN_30K
    else:
        res, _ = _run(tmp_path, GEN_5M, GEN_LIMIT)
        gen = GEN_5M
    assert check_outputs(os.path.join(res.run_dir, ROAD_DIR), _bars(gen)).failures == []
    assert _sweep(res, gen, tmp_path, forge=False) == []
    passed = _sweep(res, gen, tmp_path, forge=True)
    assert passed == _FORGED_PASS[kind]  # 落ちない欄の記録(SCHEMA の limits に書いた欄)
    limit_text = " ".join(SCHEMA["limits"])
    for f in passed:
        assert f.split(".")[1] in limit_text, f


def _scene_failures(tmp_path, params, gen=GEN_5M, ccy="JPY"):
    res, store = _run(tmp_path, gen, params, ccy)
    return R_tables(store), check_outputs(store, _bars(gen)).failures


def R_tables(store):
    return _tables(store)


# 問 1 (1)(probe.py margin_patch): 道の外で証拠金を書き換えても、検査の側の定数(20 万円・0.70)で落ちる
def test_r3_margin_patched_outside_fails(tmp_path):
    import bot.bt.road.strategy as RS
    keep = RS.MARGIN_JPY
    try:
        t, f = _scene_failures(tmp_path, {"mode": "margin_patch", "quote_ccy": "JPY", "levels": 1, "open_bar": 3,
                                          "close_bar": 6})
    finally:
        RS.MARGIN_JPY = keep
    o = _side(t["orders"])[0]
    assert (o["margin_jpy"], o["qty"]) == ("1000000", "0.14")
    assert any(x["check"] == "v" and "証拠金 '1000000'" in x["reason"] for x in f), f


# 問 1 (2)(probe.py fake_px): 量の計算の値段を偽ると、出した時刻以前に閉じた最後の足の終値と違って落ちる
def test_r3_fake_size_price_fails(tmp_path):
    t, f = _scene_failures(tmp_path, {"mode": "fake_px", "quote_ccy": "JPY", "levels": 1, "open_bar": 3,
                                      "close_bar": 6})
    assert _side(t["orders"])[0]["size_px"] == "2500000.0"
    assert any(x["check"] == "v" and "終値 5000000.0 と違う" in x["reason"] for x in f), f


# 問 1 (3)(probe.py edit_records の注文の部分): 送った量 0.028 と記録の量 0.014 が違うと落ちる
def test_r3_edited_order_record_fails(tmp_path):
    t, f = _scene_failures(tmp_path, {"mode": "edit_order", "quote_ccy": "JPY", "levels": 1, "open_bar": 3,
                                      "close_bar": 6})
    reasons = " ".join(x["reason"] for x in f)
    assert "orders.json の量 '0.028'" in reasons and "証拠金 '100000'" in reasons
    assert "約定の和 0.028 が注文の量 0.014 を超える" in reasons


# probe.py edit_records の合図の部分: 戦略が土台の合図の記録を書き換えるのは落とせない(SCHEMA の限界)。落ちないことを記録する
def test_r3_edited_signal_times_are_not_caught(tmp_path):
    t, f = _scene_failures(tmp_path, dict(BASIC, mode="edit_signal"))
    s1 = _side(t["signals"])[0]
    assert (s1["start_t_ns"], s1["end_t_ns"]) == (str(T0 + 2 * M), str(T0 + 7 * M))  # 本当は 0:03・0:06
    assert f == []
    assert any("合図の発生・消失の時刻など" in x for x in SCHEMA["limits"])


# 問 1 (5)(dcancel.py): 土台を通さない取り消しは走らせを止める
def test_r3_direct_cancel_stops_the_run(tmp_path):
    with pytest.raises(RoadStrategyError, match="土台を通さずに出した取り消し"):
        _run(tmp_path, GEN_5M, {"mode": "direct_cancel", "quote_ccy": "JPY", "levels": 1, "open_bar": 3, "close_bar": 5})


# 問 1 (4)・問 2(compound.py の (a)(c)(d)): 生の表と作った表をそろえて書き換え、repro.json の指紋も合わせても落ちる
def _rewrite(res, tmp_path, name, edit, forge):
    run = tmp_path / name
    shutil.copytree(res.run_dir, run)
    dd = run / ROAD_DIR
    t = {x: read_csv(os.path.join(dd, SCHEMA["tables"][x]["file"]), x)[1] for x in CSV_TABLES}
    with open(dd / "summary.json", encoding="utf-8") as fh:
        groups = [tuple(g) for g in json.load(fh)["groups"]]
    edit(t)
    write_tables(str(dd), {k: t[k] for k in ("signals", "orders", "fills", "fx")}, groups)
    if forge:
        _forge_repro(dd)
    return dd


def _pess(rows, **kw):
    return next(r for r in rows if r["range"] == "pessimistic" and all(r[a] == b for a, b in kw.items()))


def _c_a(t):
    _pess(t["fills"], order_id="road-2")["qty"] = "0.027"


def _c_c(t):
    from bot.bt.road.sizing import size_detail
    o = _pess(t["orders"], order_id="road-0")
    raw, q = size_detail(levels=2, price=30000.0, quote_ccy="USD", usdjpy_at_entry=100.0)
    o["usdjpy"], o["qty_raw"], o["qty"] = "100.0", str(raw), repr(q)


def _c_d(t):
    next(p for p in t["fx"] if p["range"] == "pessimistic" and p["rate"] == "150.0")["rate"] = "140.0"


@pytest.mark.parametrize("name,ccy,edit,checks", [
    ("a", "JPY", _c_a, {"v", "vi"}),
    ("c", "USD", _c_c, {"v", "vi"}),
    ("d", "USD", _c_d, {"v"}),
])
@pytest.mark.parametrize("forge", [False, True])
def test_r3_compound_rewrites_fail(tmp_path, name, ccy, edit, checks, forge):
    if ccy == "JPY":
        res, _ = _run(tmp_path, GEN_5M, BASIC)
        gen = GEN_5M
    else:
        res, _ = _run(tmp_path, GEN_30K, USD_BASIC, "USD")
        gen = GEN_30K
    dd = _rewrite(res, tmp_path, f"c-{name}", edit, forge)
    f = check_outputs(str(dd), _bars(gen)).failures
    got = {x["check"] for x in f}
    if forge:
        assert checks <= got and "repro.json" not in " ".join(x["reason"] for x in f), f
    else:
        assert "vi" in got and any("repro.json の指紋と違う" in x["reason"] for x in f), f


# 問 2: fx の行を走らせに無い組に移すと、黙って捨てずに落ちる
def test_r3_fx_row_in_unknown_group_fails(tmp_path):
    res, _ = _run(tmp_path, GEN_30K, USD_BASIC, "USD")
    run = tmp_path / "fx"
    shutil.copytree(res.run_dir, run)

    def fn(h, rs):
        rs[0]["instrument"] = "ETHUSD"
        return h, rs
    _edit(run / ROAD_DIR, "fx", fn)
    f = check_outputs(str(run / ROAD_DIR), _bars(GEN_30K)).failures
    assert any(x["check"] == "iii" and "ETHUSD" in x["reason"] and "黙って捨てない" in x["reason"] for x in f), f


# 問 2: 置き場が走らせの置き場の road/ でなければ落ちる
def test_r3_store_outside_run_dir_fails(basic_store, tmp_path):
    _, store = basic_store
    d = tmp_path / "road"
    shutil.copytree(store, d)
    f = check_outputs(str(d), _bars(GEN_5M)).failures
    assert any(x["check"] == "vi" and "repro.json" in str(x["row"]) for x in f), f


# 問 5(probe.py quick_flatten): 買いの約定の知らせが届く前の flatten でも、建玉が 0 に戻り、検査が通る
@pytest.mark.parametrize("notice_ns", [0, 90_000_000_000])
def test_r3_quick_flatten_returns_to_zero(tmp_path, notice_ns):
    params = {"mode": "quick_flatten", "quote_ccy": "JPY", "levels": 2, "open_bar": 3, "close_bar": 4}
    res = P.run_pipeline(_plan(tmp_path, GEN_5M, params, notice={"kind": "constant", "ns": notice_ns}),
                         runs_dir=str(tmp_path / "runs"))
    store = os.path.join(res.run_dir, ROAD_DIR)
    assert check_outputs(store, _bars(GEN_5M)).failures == []
    t = _tables(store)
    for side in ("pessimistic", "optimistic"):
        o = _side(t["orders"], side)
        # 4 周目 (2) C: 取り消しの答え(ここでは約定と取り消しの拒否)が全部届いてから、建玉 0.028 を 1 つの成行で決済した
        assert [(r["side"], r["qty"], r["qty_source"], r["position_at_send"], r["exit_pending_at_send"], r["exit_kind"])
                for r in o if r["sent_t_ns"]] == [
            ("buy", "0.014", "量の計算", "0", "", ""), ("buy", "0.014", "量の計算", "0", "", ""),
            ("sell", "0.028", "建玉", "0.028", "0", "flatten")]
        # 4 周目 (2) D: 呼んだときは答え待ちで出さなかったので、呼んだ記録の行が 1 つ残る(0:04、合図「無し」)
        assert [(r["exit_kind"], r["qty"], r["state"], r["placed_t_ns"], r["signal_id"], r["position_at_send"])
                for r in o if r["exit_kind"] == "flatten_call"] == [
            ("flatten_call", "0.0", ZERO_QTY_STATE, str(T0 + 4 * M), NO_SIGNAL, "0")]
        # 0:04 の flatten の時点では買いの約定の知らせがまだ届いていない: 買いを取り消しに行き(既に約定していたので
        # 取り消しは拒否される)、届いた約定の知らせのぶんを決済した
        assert all(r["cancel_sent_t_ns"] == str(T0 + 4 * M) for r in o[:2])
        assert _side(t["ledger_fills"], side)[-1]["position_after"] == "0"
        assert [(r["status"], r["levels"]) for r in _side(t["trades"], side)] == [("closed", "2")]


# 問 4 (3): 取り消しの拒否の時刻が列に残る(cancel を 2 回: 2 回目は取引所に注文が無く拒否される)
def test_r3_cancel_rejected_time_is_recorded(tmp_path):
    res, store = _run(tmp_path, GEN_5M, {"mode": "cancel_twice", "quote_ccy": "JPY", "levels": 1, "open_bar": 3,
                                         "close_bar": 5})
    o = _side(_tables(store)["orders"])[0]
    assert (o["cancel_sent_t_ns"], o["canceled_t_ns"], o["cancel_rejected_t_ns"], o["state"]) == (
        str(T0 + 5 * M), str(T0 + 5 * M), str(T0 + 5 * M), "CANCELED")
    assert check_outputs(store, _bars(GEN_5M)).failures == []


# 問 4 (3)(4): 状態不明・取り消しの拒否・answers = new で中身が拒否のもの
@pytest.mark.parametrize("make,col,cancel_first", [
    (lambda c: OrderStateUnknownEvent(received_time_ns=T0 + 5 * M, client_order_id=c, detail="timeout"),
     "state_unknown_t_ns", False),
    (lambda c: OrderStateUnknownEvent(received_time_ns=T0 + 5 * M, client_order_id=c, detail="t", request_kind="cancel"),
     "state_unknown_t_ns", True),
    (lambda c: OrderRejectEvent(received_time_ns=T0 + 5 * M, client_order_id=c, reason="order_not_found",
                                request_kind="cancel"), "cancel_rejected_t_ns", True),
    (lambda c: OrderCanceledEvent(received_time_ns=T0 + 5 * M, client_order_id=c, reason="post_only_would_take",
                                  answers="new"), "rejected_t_ns", False),
])
def test_r3_notice_columns(scene_module, make, col, cancel_first):
    s = scene_module.SceneStrategy({"mode": "nothing", "quote_ccy": "JPY", "levels": 1, "open_bar": 1})
    s.on_event(BarEvent(received_time_ns=T0 + M, start_time_ns=T0, open=1e6, high=1e6, low=1e6, close=1e6, volume=1.0),
               _Ctx(T0 + M))
    s._ctx = _Ctx(T0 + M)
    coid = s.place("buy", "market", None, 1, NO_SIGNAL)
    if cancel_first:
        s.cancel(coid)
    s._ctx = None
    s.on_event(make(coid), _Ctx(T0 + 5 * M))
    row = s.road_record()["orders"][0]
    cols = ("venue_closed_t_ns", "rejected_t_ns", "canceled_t_ns", "cancel_rejected_t_ns", "state_unknown_t_ns")
    assert {c: row[c] for c in cols} == {c: (T0 + 5 * M if c == col else "") for c in cols}


def test_r3_cancel_answer_without_cancel_stops(scene_module):
    s = scene_module.SceneStrategy({"mode": "nothing", "quote_ccy": "JPY", "levels": 1, "open_bar": 1})
    s.on_event(BarEvent(received_time_ns=T0 + M, start_time_ns=T0, open=1e6, high=1e6, low=1e6, close=1e6, volume=1.0),
               _Ctx(T0 + M))
    s._ctx = _Ctx(T0 + M)
    coid = s.place("buy", "market", None, 1, NO_SIGNAL)
    s._ctx = None
    with pytest.raises(RoadStrategyError, match="土台を通さずに出した取り消し"):
        s.on_event(OrderRejectEvent(received_time_ns=T0 + 5 * M, client_order_id=coid, reason="x",
                                    request_kind="cancel"), _Ctx(T0 + 5 * M))


# 問 3 (1)・問 4 (1)(2)(5): SCHEMA.json の文
def test_r3_schema_texts():
    assert "FIFO" in SCHEMA["read_from"] and "trades.json" in SCHEMA["read_from"]
    cols = {c[0]: c[2] for c in SCHEMA["tables"]["orders"]["columns"]}
    assert "成行の残り" in cols["venue_closed_t_ns"] and "reduce_only" in cols["venue_closed_t_ns"]
    assert "refused_by_account" in cols["rejected_t_ns"] and "post_only_would_take" in cols["rejected_t_ns"]
    assert "取引所の受け付けではない" in cols["acked_t_ns"]
    assert {"cancel_rejected_t_ns", "state_unknown_t_ns"} <= set(cols)


# ================================================================ 4 周目(批評家 2 回目の指摘と決済の口。DELEGATION_record_form.md「## 4 周目」)
from bot.bt.core import OrderFillEvent  # noqa: E402


# (1) 問 2: 全部の行の全部の欄を 1 欄ずつ書き換え、repro.json の指紋も合わせた場合に通る欄(SCHEMA の limits に書いた欄)
_FORGED_PASS_ALL = {
    "JPY": ["signals[2].kind", "signals[2].direction", "signals[2].end_t_ns", "signals[2].end_reason",
            "signals[3].signal_id", "signals[3].kind", "signals[3].direction", "signals[3].start_t_ns",
            "orders[3].acked_t_ns", "orders[3].cancel_sent_t_ns", "orders[3].cancel_rejected_t_ns",
            "orders[3].state_unknown_t_ns", "orders[4].placed_seq", "orders[4].acked_t_ns", "orders[4].cancel_sent_t_ns",
            "orders[4].cancel_rejected_t_ns", "orders[4].state_unknown_t_ns", "orders[5].placed_seq",
            "orders[5].acked_t_ns", "fills[4].notice_t_ns", "fills[4].notice_seq", "fills[5].notice_t_ns",
            "fills[5].notice_seq"],
    "USD": ["signals[1].kind", "signals[1].direction", "signals[1].end_t_ns", "signals[1].end_reason",
            "orders[3].acked_t_ns", "orders[3].cancel_sent_t_ns", "orders[3].cancel_rejected_t_ns",
            "orders[3].state_unknown_t_ns", "orders[4].placed_seq", "orders[4].acked_t_ns", "orders[4].cancel_sent_t_ns",
            "orders[4].cancel_rejected_t_ns", "orders[4].state_unknown_t_ns", "orders[5].placed_seq",
            "orders[5].acked_t_ns", "fills[4].notice_t_ns", "fills[4].notice_seq", "fills[5].notice_t_ns",
            "fills[5].notice_seq", "fx[3].t_ns", "fx[3].rate", "fx[3].source", "fx[4].source", "fx[5].t_ns",
            "fx[5].rate", "fx[5].source"],
    "LIMIT": ["signals[1].kind", "signals[1].direction", "orders[1].placed_seq", "orders[1].acked_t_ns",
              "orders[1].cancel_rejected_t_ns", "orders[1].state_unknown_t_ns", "orders[1].closed_seq",
              "orders[1].close_reason"],
}


@pytest.mark.parametrize("kind", ["JPY", "USD", "LIMIT"])
def test_r4_sweep_every_row_forged(tmp_path, kind):
    if kind == "JPY":
        res, _ = _run(tmp_path, GEN_5M, dict(BASIC, keep_open=True))
        gen = GEN_5M
    elif kind == "USD":
        res, _ = _run(tmp_path, GEN_30K, USD_BASIC, "USD")
        gen = GEN_30K
    else:
        res, _ = _run(tmp_path, GEN_5M, GEN_LIMIT)
        gen = GEN_5M
    passed = _sweep(res, gen, tmp_path, forge=True, all_rows=True)
    assert passed == _FORGED_PASS_ALL[kind]
    limit_text = " ".join(SCHEMA["limits"])
    for f in passed:
        assert f.split(".")[1] in limit_text, f
    assert "全部の行の全部の欄" in limit_text


# (1) 問 2: 決済の行の quote_ccy も値の形を確かめる(批評家の sweep2.py で orders[5].quote_ccy 'JPY'->'JPYx' が通った)
def test_r4_quote_ccy_form_on_exit_rows(basic_store, tmp_path):
    d = _copy(basic_store, tmp_path)

    def fn(h, rs):
        rs[_first_pess(rs, order_id="road-2")]["quote_ccy"] = "JPYx"
        return h, rs
    _edit(d, "orders", fn)
    f = check_outputs(str(d), _bars(GEN_5M)).failures
    assert any(x["check"] == "iii" and "値段の通貨 'JPYx'" in x["reason"] and "road-2" in x["row"] for x in f), f


# (1) 問 4: expired_t_ns → venue_closed_t_ns(O-7)
def test_r4_venue_closed_column_renamed():
    cols = {c[0]: c[2] for c in SCHEMA["tables"]["orders"]["columns"]}
    assert "expired_t_ns" not in cols
    assert "期限切れはここに入る(今の取引所の模型には期限つきの注文が無い)" in cols["venue_closed_t_ns"]


def _fresh(scene_module, quote="JPY"):
    s = scene_module.SceneStrategy({"mode": "nothing", "quote_ccy": quote, "levels": 1, "open_bar": 1})
    s.on_event(BarEvent(received_time_ns=T0 + M, start_time_ns=T0, open=1e6, high=1e6, low=1e6, close=1e6, volume=1.0),
               _Ctx(T0 + M))
    return s


class _OpenCtx(_Ctx):
    def order(self, coid):
        from bot.bt.core.api import OrderState
        return _View(OrderState.OPEN)


# (2) A: 決済の成行が拒否されたら、出し直さずに止める(理由を文に入れる)
@pytest.mark.parametrize("make", [
    lambda c: OrderRejectEvent(received_time_ns=T0 + 3 * M, client_order_id=c, reason="off_tick"),
    lambda c: OrderCanceledEvent(received_time_ns=T0 + 3 * M, client_order_id=c, reason="refused_by_account: x",
                                 answers="venue"),
])
def test_r4_rejected_flatten_stops(scene_module, make):
    s = _fresh(scene_module)
    s._ctx = _OpenCtx(T0 + M)
    buy = s.place("buy", "market", None, 1, NO_SIGNAL)
    s._ctx = None
    s.on_event(OrderFillEvent(received_time_ns=T0 + 2 * M, client_order_id=buy, price=1e6, size=0.14, side="buy"),
               _Ctx(T0 + 2 * M))  # 0.14 BTC の建玉(140,000 円 ÷ 1,000,000)
    s._ctx = _OpenCtx(T0 + 2 * M)
    fid = s.flatten(NO_SIGNAL, "market", None)
    s._ctx = None
    assert s.road_record()["orders"][-1]["exit_kind"] == "flatten" and fid == "road-1"
    with pytest.raises(RoadStrategyError, match=r"決済の注文 'road-1' が拒否された.*flatten は出し直さずに止める"):
        s.on_event(make(fid), _Ctx(T0 + 3 * M))
    assert len(s.road_record()["orders"]) == 2  # 出し直していない


# (2) B: flatten は成行だけ
def test_r4_flatten_limit_is_refused(scene_module):
    s = _fresh(scene_module)
    s._ctx = _Ctx(T0 + M)
    with pytest.raises(RoadStrategyError, match="flatten: 成行だけ"):
        s.flatten(NO_SIGNAL, "limit", 2e6)


def _run_trades(tmp_path, params, tier, seed=2, step_pct=0.0, qty=0.01):
    gen = {"name": "random_walk", "seed": seed, "params": {"kind": "trade", "start_ns": T0, "step_ns": M, "n": 30,
                                                           "price0": 5_000_000.0, "step_pct": step_pct, "qty": qty}}
    plan = P.plan_pipeline(
        root=str(tmp_path), datasets=[{"name": "g", "generator": gen}],
        instruments=[{"name": "BTCJPY", "price": "g", "with": [],
                      "product": {"symbol": "BTCJPY", "venue": "test", "tick": 0.5, "min_qty": 0.001, "qty_step": 0.001,
                                  "quote_ccy": "JPY", "margin": True}, "rules": {"market_ref": "last_trade"}}],
        strategy={"kind": "module", "module": MODULE, "factory": "pipeline_strategy", "params": params},
        fill={"optimistic": {"tier": tier}, "pessimistic": {"tier": tier}},
        latency={"feed": ZERO, "order": ZERO, "cancel": ZERO, "notice": ZERO},
        costs={"maker_rate": 0, "taker_rate": 0, "spread": 0, "source": "試験: 0"},
        account={"currency": "JPY", "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None,
                 "margin_check": "position_only"},
        purpose="動作確認", prereg=None)
    res = P.run_pipeline(plan, runs_dir=str(tmp_path / "runs"))
    # 約定(trade)の上の走らせ: 検査の足は約定の時刻の分ごとの足(値段の範囲は広く取る。終値は約定の値段)
    bars = [{"t_ns": r["t_ns"], "high": 1e12, "low": 0.0, "close": r["px"]} for r in P._generate(gen)[1]]
    return os.path.join(res.run_dir, ROAD_DIR), bars


# (2) B: close。マチルダの利確の形(足ごとに線が動く指値を取り消して置き直し、最後に約定して建玉 0)
def test_r4_close_moving_line_fills_and_flat(tmp_path):
    # 約定(trade)の足・tier 3(線に届いた最初の約定で残りが約定)。線 = その足の値段 × 1.001(刻み 0.5)
    store, bars = _run_trades(tmp_path, {"mode": "close_tp", "on_trades": True, "quote_ccy": "JPY", "levels": 1,
                                         "open_bar": 3, "line_pct": 0.001}, tier=3, seed=3, step_pct=0.3, qty=1.0)
    assert check_outputs(store, bars).failures == []
    t = _tables(store)
    for side in ("pessimistic", "optimistic"):
        o = _side(t["orders"], side)
        closes = [r for r in o if r["exit_kind"] == "close"]
        assert len(closes) >= 3  # 置き直した
        assert all(r["state"] == "CANCELED" and r["cancel_sent_t_ns"] != "" for r in closes[:-1])
        assert closes[-1]["state"] == "FILLED"
        # 置き直すたびに線が動いた、量は毎回 建玉の全部(出ている決済は取り消しの答えで消えている)
        assert len({r["limit_px"] for r in closes}) == len(closes)
        assert {(r["qty"], r["exit_pending_at_send"], r["position_at_send"]) for r in closes} == {
            (o[0]["qty"], "0", o[0]["qty"])}
        assert _side(t["ledger_fills"], side)[-1]["position_after"] == "0"
        assert [x["status"] for x in _side(t["trades"], side)] == ["closed"]


# (2) B: 段を 2 つ積んだ後の close。手計算: 0:03・0:04 に 0.014 ずつ(5,000,000 円)、0:06 に close の成行 0.028。
# 同じ足でもう 1 回 close: 出ている 1 回目の決済(0.028 の売り)で足りているので量 0 の行
def test_r4_close_after_two_levels(tmp_path):
    _, store = _run(tmp_path, GEN_5M, {"mode": "close_levels", "quote_ccy": "JPY", "levels": 2, "open_bar": 3,
                                       "close_bar": 6})
    assert check_outputs(store, _bars(GEN_5M)).failures == []
    t = _tables(store)
    o = _side(t["orders"])
    assert [(r["side"], r["qty"], r["exit_kind"], r["position_at_send"], r["exit_pending_at_send"], r["state"])
            for r in o] == [("buy", "0.014", "", "0", "", "FILLED"),
                            ("buy", "0.014", "", "0", "", "FILLED"),  # 0:04 の足は 1 つ目の約定の知らせより先に届く
                            ("sell", "0.028", "close", "0.028", "0", "FILLED"),
                            ("", "0.0", "close", "0.028", "-0.028", ZERO_QTY_STATE)]
    assert [(x["status"], x["levels"], x["pnl_jpy"]) for x in _side(t["trades"])] == [("closed", "2", "0")]


# (2) B: 一部だけ約定した close を取り消して置き直す。約定(trade)の量は 1 つ 0.01、tier 4(届いた約定の量まで約定)。
# 手計算: 0.028 を 5,000,000 で買い、売りの線 4,995,000(× 0.999)に close 0.028 → 0.01 だけ約定 → 取り消し → 残りの
# 建玉 0.018 で置き直し → 0.01 約定 → 0.008 で置き直し → 0.008 約定で建玉 0。損益 (4,995,000 − 5,000,000) × 0.028 = −140 円
def test_r4_close_partial_cancel_and_replace(tmp_path):
    store, bars = _run_trades(tmp_path, {"mode": "close_partial", "on_trades": True, "quote_ccy": "JPY", "levels": 1,
                                         "open_bar": 3, "line_pct": -0.001}, tier=4)
    assert check_outputs(store, bars).failures == []
    t = _tables(store)
    for side in ("pessimistic", "optimistic"):
        o = _side(t["orders"], side)
        assert [(r["order_id"], r["qty"], r["filled_qty"], r["state"], r["exit_kind"], r["limit_px"]) for r in o] == [
            ("road-0", "0.028", "0.028", "FILLED", "", ""),
            ("road-1", "0.028", "0.01", "CANCELED", "close", "4995000.0"),
            ("road-2", "0.018", "0.01", "CANCELED", "close", "4995000.0"),
            ("road-3", "0.008", "0.008", "FILLED", "close", "4995000.0")]
        assert [(x["status"], x["pnl_jpy"]) for x in _side(t["trades"], side)] == [("closed", "-140")]


# (2) C: ドテンの後、知らせが届く前の flatten も、取り消しの答えを待ってから建玉の分だけ出す(建玉を倍にしない)
@pytest.mark.parametrize("notice_ns", [0, 90_000_000_000])
def test_r4_flatten_after_doten_waits(tmp_path, notice_ns):
    params = {"mode": "doten_flatten", "quote_ccy": "JPY", "levels": 1, "open_bar": 3, "close_bar": 6}
    res = P.run_pipeline(_plan(tmp_path, GEN_5M, params, notice={"kind": "constant", "ns": notice_ns}),
                         runs_dir=str(tmp_path / "runs"))
    store = os.path.join(res.run_dir, ROAD_DIR)
    assert check_outputs(store, _bars(GEN_5M)).failures == []
    t = _tables(store)
    for side in ("pessimistic", "optimistic"):
        # 手計算: +0.014 → ドテン 0.028 の売りで −0.014 → flatten の買い 0.014 で 0(−0.028 を通らない)
        assert [(x["side"], x["qty"], x["position_after"]) for x in _side(t["ledger_fills"], side)] == [
            ("buy", "0.014", "0.014"), ("sell", "0.028", "-0.014"), ("buy", "0.014", "0")]
        assert [(x["direction"], x["status"], x["levels"]) for x in _side(t["trades"], side)] == [
            ("long", "closed", "1"), ("short", "closed", "1")]


# (2) D: 建玉 0 で、出ている注文の取り消しだけの flatten も、呼んだ記録の行が 1 つ残る
def test_r4_flatten_cancel_only_leaves_a_row(tmp_path):
    _, store = _run(tmp_path, GEN_5M, {"mode": "flatten_cancel_only", "quote_ccy": "JPY", "levels": 1, "open_bar": 3,
                                       "close_bar": 5})
    assert check_outputs(store, _bars(GEN_5M)).failures == []
    o = _side(_tables(store)["orders"])
    assert [(r["order_type"], r["state"], r["cancel_sent_t_ns"], r["exit_kind"], r["qty"], r["placed_t_ns"],
             r["signal_id"]) for r in o] == [
        ("limit", "CANCELED", str(T0 + 5 * M), "", "0.056", str(T0 + 3 * M), "s1"),
        ("market", ZERO_QTY_STATE, "", "flatten_call", "0.0", str(T0 + 5 * M), NO_SIGNAL)]


# ================================================================ 5 周目(批評家 3 回目の [直す] 2 件。DELEGATION_record_form.md「## 5 周目」)
# (2-1) close と flatten は reduce_only で出す: 後から建玉が減っても、決済が逆向きの建玉を作らず、「段」に数えられない
def test_r5_close_after_doten_does_not_open_reverse(tmp_path):
    # 批評家の close_run.py doten_after_close。手計算: +0.014 → ドテンの売り 0.028 で −0.014。0:05 の close の売り 0.014 は
    # 0:07 の足で届くが、そのとき建玉は売り(−0.014)なので取引所の模型が reduce_only で閉じ、約定しない
    _, store = _run(tmp_path, GEN_5M, {"mode": "doten_after_close", "quote_ccy": "JPY", "levels": 2, "open_bar": 3})
    assert check_outputs(store, _bars(GEN_5M)).failures == []
    t = _tables(store)
    for side in ("pessimistic", "optimistic"):
        assert [(x["side"], x["qty"], x["position_after"]) for x in _side(t["ledger_fills"], side)] == [
            ("buy", "0.014", "0.014"), ("sell", "0.028", "-0.014")]
        assert [(x["direction"], x["levels"], x["max_position"], x["status"]) for x in _side(t["trades"], side)] == [
            ("long", "1", "0.014", "closed"), ("short", "1", "0.014", "open")]
        c = [r for r in _side(t["orders"], side) if r["exit_kind"] == "close"]
        assert [(r["qty"], r["reduce_only"], r["filled_qty"], r["state"], r["close_reason"]) for r in c] == [
            ("0.014", "true", "0", "CANCELED", "reduce_only")]


def test_r5_close_then_partial_exit_is_cut(tmp_path):
    # 批評家の close_run.py place_sell_after_close。手計算: 建玉 0.028、0:07 に close の売り 0.028 と成行の売り 0.014。
    # 成行で 0.014 になった後、close は建玉の 0.014 だけ約定し(取引所の模型が切る)、建玉 0。空売りの取引はできない
    _, store = _run(tmp_path, GEN_5M, {"mode": "place_sell_after_close", "quote_ccy": "JPY", "levels": 2,
                                       "open_bar": 3})
    assert check_outputs(store, _bars(GEN_5M)).failures == []
    t = _tables(store)
    for side in ("pessimistic", "optimistic"):
        assert [(x["side"], x["qty"], x["position_after"]) for x in _side(t["ledger_fills"], side)] == [
            ("buy", "0.014", "0.014"), ("buy", "0.014", "0.028"), ("sell", "0.014", "0.014"), ("sell", "0.014", "0")]
        assert [(x["direction"], x["levels"], x["max_position"], x["status"]) for x in _side(t["trades"], side)] == [
            ("long", "2", "0.028", "closed")]
        c = [r for r in _side(t["orders"], side) if r["exit_kind"] == "close"]
        assert [(r["qty"], r["reduce_only"], r["filled_qty"], r["state"]) for r in c] == [
            ("0.028", "true", "0.014", "CANCELED")]


def test_r5_reduce_only_column(basic_store):
    _, store = basic_store
    o = _side(_tables(store)["orders"])
    assert [(r["exit_kind"], r["reduce_only"]) for r in o] == [("", "false"), ("", "false"), ("flatten", "true")]


# (2-5) 足で約定させた指値の約定は、t_ns で閉じた足と比べる(批評家の limit_at.py)
def _limit_at(tmp_path, seed, px):
    gen = _gen(5_000_000.0, step_pct=0.3, n=20, seed=seed)
    _, store = _run(tmp_path, gen, {"mode": "limit_at", "quote_ccy": "JPY", "levels": 2, "open_bar": 3, "limit_px": px})
    return gen, store


def _bar_at(gen, minute):
    return next(b for b in _bars(gen) if b["t_ns"] == T0 + minute * M)


@pytest.mark.parametrize("seed", [2, 5])
def test_r5_limit_fill_at_bar_high_passes(tmp_path, seed):
    # 0:05 に、0:06 の足の高値ちょうど(刻み 0.5 で内側)の売りの指値。0:06 の足で約定し、t_ns は足が閉じた 0:07。
    # 前の検査は 0:07 の足と比べて落とした(正直な記録が落ちた)
    hi = _bar_at(_gen(5_000_000.0, step_pct=0.3, n=20, seed=seed), 6)["high"]
    px = round(hi * 2) / 2
    if px > hi:
        px -= 0.5
    gen, store = _limit_at(tmp_path, seed, px)
    f = [x for x in _side(_tables(store)["fills"]) if x["order_id"] == "road-1"]
    assert [(x["px"], x["t_ns"], x["liquidity"]) for x in f] == [(repr(px), str(T0 + 7 * M), "maker")]
    assert px > _bar_at(gen, 7)["high"]  # 次の足(0:07)の高値より上: 前の検査はここで落とした
    assert check_outputs(store, _bars(gen)).failures == []


@pytest.mark.parametrize("seed,px", [(3, 4960000.0), (1, None)])
def test_r5_limit_fill_outside_the_filling_bar_fails(tmp_path, seed, px):
    # (3, 4960000.0): 0:06 の足の安値(約 4,967,307)より下の売りの指値。約定させた足の値幅の外なのに、前の検査は次の足と
    # 比べて通した。(1, None): 終値 × 0.99 の売りの指値(相場より不利な側。取引所の模型が指値の値段で約定させる)
    if px is None:
        px = round(_bar_at(_gen(5_000_000.0, step_pct=0.3, n=20, seed=seed), 4)["close"] * 0.99 * 2) / 2
    gen, store = _limit_at(tmp_path, seed, px)
    f = check_outputs(store, _bars(gen)).failures
    assert len(f) == 2 and all(x["check"] == "iv" and "約定させた足(足 6、始まり" in x["reason"] for x in f), f


# (3) 説明の文
def test_r5_flatten_doc_texts():
    from bot.bt.road import strategy as S
    assert "1 分足の走らせでは門が成行を次の足まで預かるので" in S.__doc__
    assert "戦略が「出ている注文を\n  全部取り消す」と書くと、決済の成行に当たったところで止まる" in S.__doc__
