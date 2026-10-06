"""`bot.research.liq_cascade_fill` ほかの試験(カード 9 の走らせ直し、2026-10-06)。

どれも合成の小さな入力で、答えを手で書ける形にしてある。状態機械の表は
`test_liq_cascade_v2.EXPECTED` と同じ手書きの表を使う(前の道具の表は使わない)。
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

from bot.research import liq_cascade_fill as fill
from bot.research import liq_cascade_v2 as v2

REPO = Path(__file__).resolve().parents[2]
RERUN_DIR = REPO / "docs" / "RESEARCH" / "cards" / "c9_liquidation_cascade" / "rerun_2026-10-06"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

D0 = v2.day_start_ms("2023-07-01")

EXPECTED = {
    ("わからない", "止まる"): {"A": "新規_逆張り", "B": "新規_逆張り"},
    ("わからない", "続く"): {"A": "新規_順張り", "B": "新規_順張り"},
    ("わからない", "わからない"): {"A": "何もしない", "B": "何もしない"},
    ("続く", "止まる"): {"A": "決済", "B": "ドテン_逆張り"},
    ("続く", "続く"): {"A": "ホールド", "B": "ホールド"},
    ("続く", "わからない"): {"A": "ホールド", "B": "ホールド"},
    ("止まる", "止まる"): {"A": "ホールド", "B": "ホールド"},
    ("止まる", "続く"): {"A": "決済", "B": "ドテン_順張り"},
    ("止まる", "わからない"): {"A": "ホールド", "B": "ホールド"},
}


def _prints(rows):
    return v2.Prints.from_rows([(t, s, q, q + 1, 30000.0) for t, s, q in rows])


def _bundle(pr, gap_s=60):
    return v2.same_side_bundles(pr, gap_s)["bundles"][0]


def _two_sided(t_lo_s, t_hi_s):
    """毎秒 2 件: k 秒ちょうどに売りの成行(maker 真)の約定 100 + k、k 秒 + 100 ms に買いの成行
    (maker 偽)の約定 100.5 + k。売り板 = 買いの成行が付く値段が 0.5 高い。"""
    ks = np.arange(t_lo_s, t_hi_s + 1)
    t = np.empty(2 * ks.size, np.int64)
    p = np.empty(2 * ks.size)
    m = np.empty(2 * ks.size, bool)
    t[0::2], p[0::2], m[0::2] = D0 + ks * 1000, 100.0 + ks, True
    t[1::2], p[1::2], m[1::2] = D0 + ks * 1000 + 100, 100.5 + ks, False
    return v2.Trades(t, p, np.ones(t.size), m)


def bp(d, a, b):
    return d * (b - a) / a * 1e4


# --------------------------------------------------------------------------- #
# 既定(any)は元の `v2.simulate_bundle` と同じ値
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("j1,j2", list(EXPECTED))
@pytest.mark.parametrize("typ", ["A", "B"])
def test_any_side_equals_original(j1, j2, typ):
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 1)])
    tr = _two_sided(0, 200)
    b = _bundle(pr)
    ref = v2.simulate_bundle(pr, b, [j1, j2], typ, 1, v2.make_price_fn(tr))
    got = fill.simulate(pr, b, [j1, j2], typ, 1, tr, fill.FILL_ANY, leg_path=True)
    assert got["pnl_bp"] == ref["pnl_bp"]
    assert got["hold_seconds"] == ref["hold_seconds"]
    assert got["path"] == ref["path"]
    assert got["legs"] == ref["legs"]
    assert len(got["leg_rows"]) == len(ref["legs"])


@pytest.mark.parametrize("direction", ["順張り", "逆張り"])
def test_any_side_baseline_equals_original(direction):
    pr = _prints([(D0, "BUY", 1), (D0 + 20_000, "BUY", 1)])
    tr = _two_sided(0, 300)
    b = _bundle(pr, 30)
    ref = v2.simulate_bundle(pr, b, None, "-", 3, v2.make_price_fn(tr), baseline=direction)
    got = fill.simulate(pr, b, None, "-", 3, tr, fill.FILL_ANY, leg_path=True,
                        baseline=direction)
    assert got["pnl_bp"] == ref["pnl_bp"] and got["path"] == ref["path"]
    assert len(got["leg_rows"]) == 1


# --------------------------------------------------------------------------- #
# 注文の向き(本体の path から)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("j1,j2", list(EXPECTED))
@pytest.mark.parametrize("typ", ["A", "B"])
def test_order_signs_hand(j1, j2, typ):
    # SELL の清算(清算の向き −1)。順張り = 売り(−1)、逆張り = 買い(+1)
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 1)])
    tr = _two_sided(0, 200)
    res = v2.simulate_bundle(pr, _bundle(pr), [j1, j2], typ, 1, v2.make_price_fn(tr))
    got = [s for s, _k in fill.order_signs_from_path(res["path"], -1.0)]
    first = {"続く": [-1], "止まる": [+1], "わからない": []}[j1]
    pos1 = {"続く": -1, "止まる": +1, "わからない": 0}[j1]   # 1 件目の後の建玉(+1 = 買い)
    a2 = EXPECTED[(j1, j2)][typ]
    mid = {"新規_逆張り": [+1], "新規_順張り": [-1], "何もしない": [], "ホールド": [],
           "決済": [-pos1], "ドテン_逆張り": [+1], "ドテン_順張り": [-1]}[a2]
    pos2 = {"新規_逆張り": +1, "新規_順張り": -1, "何もしない": 0, "ホールド": pos1,
            "決済": 0, "ドテン_逆張り": +1, "ドテン_順張り": -1}[a2]
    end = [-pos2] if pos2 != 0 else []
    assert got == first + mid + end


# --------------------------------------------------------------------------- #
# quote(主 = 目標の時刻以前で最新の最良気配。(b)・(a)・元の付け方は並べる列)
# --------------------------------------------------------------------------- #
DAY = "2023-07-01"


def _qb(rows, ok_days=(DAY,)):
    """rows = {目標の秒: (気配の秒 or None, 買い気配, 売り気配)}(秒は D0 から)。"""
    return fill.QuoteBook({D0 + int(k * 1000): (None if q is None else D0 + int(q * 1000), b, a)
                           for k, (q, b, a) in rows.items()}, ok_days)


def _flip_quotes():
    # 目標 1 秒: ちょうどの気配。11 秒: 10.5 秒の気配。71 秒: 70.99 秒の気配
    return _qb({1: (1, 100.9, 101.1), 11: (10.5, 110.9, 111.1), 71: (70.99, 170.9, 171.1)})


def test_quote_flip_hand():
    # SELL の清算、止まる → 続く、型 B: 逆張り(買い)で入る → ドテン(売り 1 回)→ 終わりで買い戻し
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 1)])
    tr = _two_sided(0, 200)
    res = fill.simulate(pr, _bundle(pr), ["止まる", "続く"], "B", 1, tr, fill.FILL_QUOTE,
                        leg_path=True, quotes=_flip_quotes())
    # 主: 買いは売り気配 101.1、売りは買い気配 110.9、買い戻しは売り気配 171.1
    leg1, leg2 = bp(+1, 101.1, 110.9), bp(-1, 110.9, 171.1)
    assert res["pnl_bp"] == pytest.approx(leg1 + leg2)
    assert [x["レグ損益_bp"] for x in res["legs"]] == pytest.approx([leg1, leg2])
    # (b) 以前で最後の同じ側の約定: 0.1 秒 100.5 → 11 秒ちょうど 111 → 70.1 秒 170.5
    assert res["pnl_bp_taker_prev"] == pytest.approx(bp(+1, 100.5, 111) + bp(-1, 111, 170.5))
    # (a) 以後で最初: 1.1 秒 101.5 → 11 秒 111 → 71.1 秒 171.5
    assert res["pnl_bp_taker_wait"] == pytest.approx(bp(+1, 101.5, 111) + bp(-1, 111, 171.5))
    assert res["leg_pnl_taker_wait"] == pytest.approx([bp(+1, 101.5, 111), bp(-1, 111, 171.5)])
    # 元の付け方: 1 秒 101 → 11 秒 111 → 71 秒 171
    assert res["pnl_bp_anyside"] == pytest.approx(bp(+1, 101, 111) + bp(-1, 111, 171))
    assert res["res_any"]["pnl_bp"] == res["pnl_bp_anyside"]
    r1, r2 = res["leg_rows"]
    assert (r1["order_in"], r1["order_out"], r2["order_in"], r2["order_out"]) == (1, -1, -1, 1)
    assert (r1["in_fill_ms"] - D0, r1["in_lag_ms"], r1["in_quote_age_ms"]) == (1000, 0, 0)
    assert (r1["out_fill_ms"] - D0, r1["out_lag_ms"], r1["out_quote_age_ms"]) == (10500, -500, 500)
    assert (r2["out_lag_ms"], r2["out_quote_age_ms"]) == (-10, 10)
    assert r1["in_px"] == 101.1 and r1["out_px"] == 110.9 and r2["out_px"] == 171.1
    # 経路の起点は気配の入りの値段 101.1。経路 = (1 秒, 11 秒] の約定。1 秒ちょうどの約定 101 は
    # 入らない(入れば mae < 0)。最大は 11 秒の 111(入りの目標から 10 秒後)
    assert r1["mfe_bp"] == pytest.approx(bp(+1, 101.1, 111.0)) and r1["mfe_after_s"] == 10.0
    assert r1["mae_bp"] == 0.0 and r1["path_n"] == 20


def test_quote_stale_missing_day_and_unknown_target():
    pr = _prints([(D0, "SELL", 1)])
    tr = _two_sided(0, 200)
    b = _bundle(pr)
    # 入り 1 秒の気配が 301 秒前 → 古さ 300 秒越えで欠け
    res = fill.simulate(pr, b, ["止まる"], "A", 1, tr, fill.FILL_QUOTE,
                        quotes=_qb({1: (-300, 99.0, 99.1), 61: (60, 1.0, 1.1)}))
    assert res["missing"] and math.isnan(res["pnl_bp"]) and not res["missing_anyside"]
    # ちょうど 300 秒前は可
    res = fill.simulate(pr, b, ["止まる"], "A", 1, tr, fill.FILL_QUOTE,
                        quotes=_qb({1: (-299, 99.0, 99.1), 61: (60, 1.0, 1.1)}))
    assert not res["missing"]
    # 気配のファイルが無い日(ok_days に無い)→ 欠け。前の日の気配で埋めない
    res = fill.simulate(pr, b, ["止まる"], "A", 1, tr, fill.FILL_QUOTE,
                        quotes=_qb({1: (1, 99.0, 99.1), 61: (60, 1.0, 1.1)}, ok_days=()))
    assert res["missing"]
    # 取れた日なのに目標が表に無い → 止める(目標の組が走らせと違う)
    with pytest.raises(RuntimeError, match="気配の表に無い"):
        fill.simulate(pr, b, ["止まる"], "A", 1, tr, fill.FILL_QUOTE, quotes=_qb({1: (1, 9, 9)}))


def test_quote_book_load_and_fetch_quotes_at(tmp_path):
    fetch = _load(REPO / "scripts" / "c9_fetch_bookticker.py", "c9_fetch_bookticker")
    import pandas as pd
    df = pd.DataFrame({"update_id": [1, 2, 3], "best_bid_price": [10.0, 11.0, 12.0],
                       "best_ask_price": [10.1, 11.1, 12.1],
                       "transaction_time": [D0 + 500, D0 + 1000, D0 + 1000]})
    tg = np.array([D0 + 100, D0 + 999, D0 + 1000], dtype=np.int64)
    rows = fetch.quotes_at(df, tg, {"q_ms": D0 - 50, "bid": 9.0, "ask": 9.1})
    # 100 ms: 当日に以前の気配が無い → 前の日の最後。999: 500 ms の気配。1000: 同じ ms の後の行
    assert [r["src"] for r in rows] == ["前日", "当日", "当日"]
    assert [r["bid"] for r in rows] == [9.0, 10.0, 12.0]
    rows2 = fetch.quotes_at(df, tg[:1], None)          # 前の日が取れていない → 無し
    assert rows2[0]["src"] == "無し" and rows2[0]["q_ms"] == ""
    out = tmp_path / "q"
    fetch.write_rows(out / "days" / f"{DAY}.csv.gz", rows + rows2[:0])
    (out / "fetch_log.jsonl").write_text(json.dumps({"day": DAY, "status": "ok"}) + "\n"
                                         + json.dumps({"day": "2023-07-02", "status": "取れない"}))
    qb = fill.QuoteBook.load(out, [DAY, "2023-07-02"])
    assert qb.lookup(+1, D0 + 1000) == (12.1, D0 + 1000)
    assert qb.lookup(-1, D0 + 100) == (9.0, D0 - 50)
    assert qb.lookup(+1, v2.day_start_ms("2023-07-02") + 5) == (pytest.approx(float("nan"),
                                                                nan_ok=True), None)


def test_fetch_refuses_days_after_seal(tmp_path):
    fetch = _load(REPO / "scripts" / "c9_fetch_bookticker.py", "c9_fetch_bookticker2")
    with pytest.raises(SystemExit, match="2023-12-17 以後"):
        fetch.main(["--data-root", str(tmp_path), "--start", "2023-07-01", "--end", "2023-07-01",
                    "--out", str(tmp_path / "o"), "--last-day", "2023-12-17"])


def test_targets_cover_every_price_call():
    # いくつかの束・方策・型・遅れで、本体が値段を引いた時刻がすべて目標の組に入る
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 2), (D0 + 95_000, "SELL", 1),
                  (D0 + 5_000, "BUY", 1), (D0 + 400_000, "BUY", 3)])
    tr = _two_sided(0, 1500)
    tg = set(fill.targets_for_prints(pr).tolist())
    seen = []

    def rec(t):
        seen.append(int(t))
        return v2.make_price_fn(tr)(t)
    ctx = v2.same_side_context(pr)
    for g in v2.GAPS_S:
        for b in v2.same_side_bundles(pr, g)["bundles"]:
            for d in v2.DELAYS_S:
                for pol in v2.JUDGED_POLICIES:
                    for typ in ("A", "B"):
                        v2.simulate_bundle(pr, b, v2.judgments_for(pol, b["members"], ctx), typ,
                                           d, rec)
                for direction in v2.BASELINE_POLICIES.values():
                    v2.simulate_bundle(pr, b, None, "-", d, rec, baseline=direction)
    assert seen and set(seen) <= tg


# --------------------------------------------------------------------------- #
# 並べる列 (b)・(a) の引き方と、欠けた日
# --------------------------------------------------------------------------- #
def test_taker_book_respects_staleness_boundary_and_exact_target():
    tr = v2.Trades(np.array([D0, D0 + 300_000, D0 + 300_001], np.int64),
                   np.array([1.0, 2.0, 3.0]), np.ones(3), np.array([True, False, False]))
    book = fill.TakerBook(tr)
    # (a)(以後で最初)
    assert book.at_or_after(+1, D0) == (1, True)       # ちょうど 300 秒は可
    assert book.at_or_after(+1, D0 - 1) == (-1, False)  # 300.001 秒は不可
    assert book.at_or_after(-1, D0) == (0, True)        # 目標の時刻ちょうど
    # (b)(以前で最後)
    assert book.at_or_before(-1, D0) == (0, True)               # 目標の時刻ちょうど
    assert book.at_or_before(+1, D0 + 400_000) == (2, True)     # 前の約定
    assert book.at_or_before(+1, D0 + 600_001) == (2, True)     # ちょうど 300 秒前は可
    assert book.at_or_before(+1, D0 + 600_002) == (-1, False)   # 300.001 秒前は不可
    assert book.at_or_before(+1, D0 + 299_999) == (-1, False)   # 以前に買いの約定が無い


def test_taker_book_missing_day_after_gap():
    # 前の日(06-30)の最後の約定から 10 秒後の目標でも、目標の日(07-01)のファイルが無ければ欠け
    tr = v2.Trades(np.array([D0 - 10_000, D0 + 90_000_000], np.int64), np.array([1.0, 2.0]),
                   np.ones(2), np.array([False, False]))
    assert fill.TakerBook(tr).at_or_before(+1, D0) == (0, True)
    book = fill.TakerBook(tr, present_days=["2023-06-30", "2023-07-02"])
    assert book.at_or_before(+1, D0) == (-1, False)
    assert book.at_or_after(+1, D0 - 5_000) == (-1, False)     # 以後は 07-02(300 秒越え)
    assert book.at_or_before(+1, D0 - 5_000) == (0, True)      # 06-30 の中は可


def test_quote_mode_columns_missing_on_gap_day():
    # 約定のファイルが無い日の (b)・(a) は欠け。気配は取れていれば値になる
    pr = _prints([(D0, "SELL", 1)])
    tr = _two_sided(0, 200)
    res = fill.simulate(pr, _bundle(pr), ["止まる"], "A", 1, tr, fill.FILL_QUOTE,
                        book=fill.TakerBook(tr, present_days=["2023-06-30"]),
                        quotes=_qb({1: (1, 99.0, 99.1), 61: (60, 1.0, 1.1)}))
    assert not res["missing"]
    assert res["missing_taker_prev"] and res["missing_taker_wait"]


# --------------------------------------------------------------------------- #
# 回数と行動の並びの検めが止まること(偽物の本体)
# --------------------------------------------------------------------------- #
def _fake_body(extra_calls_on_second=0, change_action=False):
    state = {"n": 0}

    def fake(pr, bundle, judgments, policy_type, delay_s, price_fn, baseline=None):
        state["n"] += 1
        t = int(pr.ts[0]) + 1000
        price_fn(t)
        path = [{"建玉": "逆張り", "行動": "新規_逆張り"}]
        if state["n"] >= 2:
            for _ in range(extra_calls_on_second):
                price_fn(t)
            if change_action:
                path = [{"建玉": "逆張り", "行動": "ドテン_逆張り"}]
        return {"pnl_bp": 0.0, "missing": False, "path": path, "legs": [], "entered": True,
                "n_entries": 1, "hold_seconds": 0.0}
    return fake


@pytest.mark.parametrize("extra,change,msg", [(1, False, "多い"), (0, True, "行動の並び")])
def test_queue_checks_stop_on_fake_body(monkeypatch, extra, change, msg):
    pr = _prints([(D0, "SELL", 1)])
    tr = _two_sided(0, 200)
    monkeypatch.setattr(fill.v2, "simulate_bundle", _fake_body(extra, change))
    with pytest.raises(RuntimeError, match=msg):
        fill.simulate(pr, _bundle(pr), ["止まる"], "A", 1, tr, fill.FILL_QUOTE,
                      quotes=_qb({1: (1, 99.0, 99.1)}))


def test_queue_checks_stop_when_fewer_calls(monkeypatch):
    pr = _prints([(D0, "SELL", 1)])
    tr = _two_sided(0, 200)
    state = {"n": 0}

    def fake(pr_, bundle, judgments, policy_type, delay_s, price_fn, baseline=None):
        state["n"] += 1
        if state["n"] == 1:
            price_fn(int(pr_.ts[0]) + 1000)
        return {"pnl_bp": 0.0, "missing": False, "legs": [], "entered": True, "n_entries": 1,
                "hold_seconds": 0.0, "path": [{"建玉": "逆張り", "行動": "新規_逆張り"}]}
    monkeypatch.setattr(fill.v2, "simulate_bundle", fake)
    with pytest.raises(RuntimeError, match="少ない"):
        fill.simulate(pr, _bundle(pr), ["止まる"], "A", 1, tr, fill.FILL_QUOTE,
                      quotes=_qb({1: (1, 99.0, 99.1)}))


# --------------------------------------------------------------------------- #
# 経路(MFE・MAE)
# --------------------------------------------------------------------------- #
def _six():
    t = D0 + np.arange(6) * 1000
    return v2.Trades(t.astype(np.int64), np.array([100.0, 101.0, 98.0, 103.0, 99.0, 100.0]),
                     np.ones(6), np.zeros(6, bool))


def test_path_by_index_hand():
    tr = _six()
    st = fill.path_by_index(tr, 0, 4, +1.0)             # (0, 4] = 101, 98, 103, 99
    assert st["path_ok"] == 1 and st["path_n"] == 4
    assert st["mfe_bp"] == pytest.approx(300.0) and st["mfe_after_s"] == 3.0
    assert st["mae_bp"] == pytest.approx(-200.0) and st["mae_after_s"] == 2.0
    st2 = fill.path_by_index(tr, 0, 4, -1.0)            # 売りの建玉は符号が逆
    assert st2["mfe_bp"] == pytest.approx(200.0) and st2["mae_bp"] == pytest.approx(-300.0)
    st0 = fill.path_by_index(tr, 2, 2, +1.0)            # 入りと出が同じ約定 → 0
    assert (st0["path_n"], st0["mfe_bp"], st0["mae_bp"]) == (0, 0.0, 0.0)
    bad = fill.path_by_index(tr, 3, 2, +1.0)            # 出が入りより前
    assert bad["path_ok"] == 0 and math.isnan(bad["mfe_bp"])


def test_path_by_target_hand():
    tr = _six()
    # 入りの目標 1 秒ちょうど(1 秒の約定 101 は入らない)、出の目標 4 秒ちょうど(4 秒の 99 は入る)
    st = fill.path_by_target(tr, 100.0, D0 + 1000, D0 + 4000, +1.0)
    assert st["path_n"] == 3                            # 98, 103, 99
    assert st["mfe_bp"] == pytest.approx(300.0) and st["mfe_after_s"] == 2.0
    assert st["mae_bp"] == pytest.approx(-200.0) and st["mae_after_s"] == 1.0
    st2 = fill.path_by_target(tr, 100.0, D0 + 1500, D0 + 4500, +1.0)
    assert st2["path_n"] == 3 and st2["mfe_after_s"] == 1.5
    assert fill.path_by_target(tr, 100.0, D0 + 4000, D0 + 3000, +1.0)["path_ok"] == 0


def test_leg_path_in_any_mode_uses_entry_fill_price():
    # BUY の清算(清算の向き +1)、続く → 続く、型 A: 順張り(買い)で 1 秒に入り 71 秒で出る
    pr = _prints([(D0, "BUY", 1), (D0 + 10_000, "BUY", 1)])
    tr = _two_sided(0, 200)
    res = fill.simulate(pr, _bundle(pr), ["続く", "続く"], "A", 1, tr, fill.FILL_ANY,
                        leg_path=True)
    (r,) = res["leg_rows"]
    assert r["in_px"] == 101.0 and r["out_px"] == 171.0
    assert r["mfe_bp"] == pytest.approx(bp(+1, 101.0, 171.0))
    assert r["mae_bp"] == 0.0 and r["mfe_after_s"] == 70.0
    assert math.isnan(r["in_quote_age_ms"])


def test_extra_columns_names_and_banned_words():
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 1)])
    tr = _two_sided(0, 200)
    res = fill.simulate(pr, _bundle(pr), ["止まる", "続く"], "B", 1, tr, fill.FILL_QUOTE,
                        leg_path=True, quotes=_flip_quotes())
    row = fill.leg_extra(res, 0, fill.FILL_QUOTE, True)
    assert list(row)[:len(fill.LEG_PATH_COLS)] == list(fill.LEG_PATH_COLS)
    assert {"pnl_bp_anyside", "pnl_bp_taker_prev", "pnl_bp_taker_wait"} <= set(row)
    c = fill.cascade_extra(res, fill.FILL_QUOTE)
    assert set(c) == {"fill_side"} | {f"{p}_{k}" for p in ("pnl_bp", "missing")
                                      for k in ("anyside", "taker_prev", "taker_wait")}
    banned = ("差あり", "検出されず", "陽性", "陰性", "有意", "支持", "棄却")
    assert not any(w in k for k in list(row) + list(c) for w in banned)


# --------------------------------------------------------------------------- #
# c9_run_a.make_sim・make_cut_root.py・check_repro.py
# --------------------------------------------------------------------------- #
def test_make_sim_default_is_original_call():
    run = _load(REPO / "scripts" / "c9_run_a.py", "c9_run_a_t")
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 1)])
    tr = _two_sided(0, 200)
    b = _bundle(pr)
    pf = v2.make_price_fn(tr)
    sim = run.make_sim(pr, tr, pf, fill.FILL_ANY, False)
    ref = v2.simulate_bundle(pr, b, ["止まる", "続く"], "B", 1, pf)
    got = sim(b, ["止まる", "続く"], "B", 1)
    assert got == ref and "leg_rows" not in got
    refb = v2.simulate_bundle(pr, b, None, "-", 3, pf, baseline="逆張り")
    assert sim(b, None, "-", 3, baseline="逆張り") == refb
    simq = run.make_sim(pr, tr, pf, fill.FILL_QUOTE, True, present_days=[DAY],
                        quotes=_flip_quotes())
    gq = simq(b, ["止まる", "続く"], "B", 1)
    assert gq["pnl_bp_anyside"] == ref["pnl_bp"] and len(gq["leg_rows"]) == 2
    assert not run.extra_on(fill.FILL_ANY, False) and run.extra_on(fill.FILL_QUOTE, False)


def test_any_rows_match_original_columns():
    run = _load(REPO / "scripts" / "c9_run_a.py", "c9_run_a_t2")
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 1)])
    tr = _two_sided(0, 200)
    res = fill.simulate(pr, _bundle(pr), None, "-", 1, tr, fill.FILL_QUOTE, baseline="逆張り",
                        quotes=_qb({1: (1, 99.0, 99.1), 71: (71, 150.0, 150.1)}))
    c, ls = run.any_rows(res, {"bundle_id": "x"}, {"bundle_id": "x"}, "逆張り")
    assert c["pnl_bp"] == res["pnl_bp_anyside"] and c["missing"] == 0
    assert len(ls) == 1 and ls[0]["pnl_bp"] == res["pnl_bp_anyside"]
    assert ls[0]["leg_dir"] == "逆張り" and ls[0]["exit_reason"] == "連鎖の終わり"


def test_make_cut_root(tmp_path):
    cut = _load(RERUN_DIR / "make_cut_root.py", "make_cut_root_t")
    src = tmp_path / "src"
    for kind in ("aggTrades", "liquidationSnapshot", "metrics"):
        for day in ("2023-12-15", "2023-12-16", "2023-12-17"):
            p = src / kind / "BTCUSD_PERP" / f"BTCUSD_PERP-{kind}-{day}.zip"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x")
    for m in ("2023-11", "2023-12"):
        p = src / "fundingRate" / "BTCUSD_PERP" / f"BTCUSD_PERP-fundingRate-{m}.zip"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    dst = tmp_path / "dst"
    assert cut.main(["--src", str(src), "--dst", str(dst), "--first-day", "2023-11-01"]) == 0
    got = sorted(str(p.relative_to(dst)) for p in dst.rglob("*.zip"))
    assert got == sorted([f"{k}/BTCUSD_PERP/BTCUSD_PERP-{k}-{d}.zip"
                          for k in ("aggTrades", "liquidationSnapshot", "metrics")
                          for d in ("2023-12-15", "2023-12-16")]
                         + ["fundingRate/BTCUSD_PERP/BTCUSD_PERP-fundingRate-2023-11.zip"])
    assert all(p.is_symlink() for p in dst.rglob("*.zip"))
    with pytest.raises(SystemExit, match="境"):
        cut.main(["--src", str(src), "--dst", str(tmp_path / "d2"), "--last-day", "2023-12-17"])


def test_check_repro_main_value_checks():
    chk = _load(RERUN_DIR / "check_repro.py", "check_repro_t")
    import pandas as pd
    base = {"side": "SELL", "gap_s": "60", "start_ms": "1", "delay_s": "1", "policy": "p",
            "type": "A", "leg_dir": "逆張り", "order_in": "1", "order_out": "-1",
            "in_lag_ms": "-5", "out_lag_ms": "0", "in_quote_age_ms": "5", "out_quote_age_ms": "0",
            "in_px": "100", "out_px": "101", "pnl_bp": "100", "path_ok": "1", "mfe_bp": "120",
            "mae_bp": "-3"}
    legs = pd.DataFrame([base])
    cas = pd.DataFrame([{k: base[k] for k in chk.KEY} | {"pnl_bp": "100", "missing": "0"}])
    assert chk.main_value_checks(legs, cas)["外れ"] == {}
    for k, v, name in (("in_lag_ms", "5", "遅れ > 0"), ("order_in", "-1", "order_in ≠ 側 × 向き"),
                       ("pnl_bp", "0", "pnl_bp ≠ 値段から計算"), ("mfe_bp", "-1", "mfe < 0 または mae > 0"),
                       ("in_quote_age_ms", "300001", "古さ ≠ −遅れ")):
        bad = legs.copy()
        bad[k] = v
        assert name in chk.main_value_checks(bad, cas)["外れ"], k


# --------------------------------------------------------------------------- #
# 批評家 2 回目の試験の網(Q9・Q10・Q11〜Q13・Q15・境の守り・気配の表の突き合わせ)
# --------------------------------------------------------------------------- #
def test_make_sim_passes_present_days_to_taker_columns():
    # Q9: make_sim が (b)・(a) に約定のファイルがある日を渡す。目標の日(07-01)が無ければ欠け
    run = _load(REPO / "scripts" / "c9_run_a.py", "c9_run_a_q9")
    pr = _prints([(D0, "SELL", 1)])
    tr = _two_sided(0, 200)
    q = _qb({1: (1, 99.0, 99.1), 61: (60, 1.0, 1.1)})
    sim = run.make_sim(pr, tr, v2.make_price_fn(tr), fill.FILL_QUOTE, False,
                       present_days=["2023-06-30"], quotes=q)
    res = sim(_bundle(pr), ["止まる"], "A", 1)
    assert res["missing_taker_prev"] and res["missing_taker_wait"] and not res["missing"]
    sim2 = run.make_sim(pr, tr, v2.make_price_fn(tr), fill.FILL_QUOTE, False,
                        present_days=[DAY], quotes=q)
    res2 = sim2(_bundle(pr), ["止まる"], "A", 1)
    assert not res2["missing_taker_prev"] and not res2["missing_taker_wait"]


def test_stage3_window():
    # Q10: 段 3 の窓。quote は前の日も読む、既定は元のとおり [当日, 翌日]
    run = _load(REPO / "scripts" / "c9_run_a.py", "c9_run_a_q10")
    assert run.stage3_window("2023-07-01", fill.FILL_QUOTE) == ["2023-06-30", "2023-07-01",
                                                                 "2023-07-02"]
    assert run.stage3_window("2023-07-01", fill.FILL_ANY) == ["2023-07-01", "2023-07-02"]


def _good_leg_and_cascade(chk):
    base = {"side": "SELL", "gap_s": "60", "start_ms": "1", "delay_s": "1", "policy": "p",
            "type": "A", "leg_dir": "逆張り", "order_in": "1", "order_out": "-1",
            "in_lag_ms": "-5", "out_lag_ms": "0", "in_quote_age_ms": "5", "out_quote_age_ms": "0",
            "in_px": "100", "out_px": "101", "pnl_bp": "100", "path_ok": "1", "mfe_bp": "120",
            "mae_bp": "-3"}
    import pandas as pd
    legs = pd.DataFrame([base])
    cas = pd.DataFrame([{k: base[k] for k in chk.KEY} | {"pnl_bp": "100", "missing": "0"}])
    return legs, cas


def test_check_repro_specific_checks():
    # Q11: 古さ > 300 秒(遅れとは合っている)/ Q12: 連鎖の損益 ≠ レグの和 / Q13: order_out
    chk = _load(RERUN_DIR / "check_repro.py", "check_repro_q11")
    legs, cas = _good_leg_and_cascade(chk)
    assert chk.main_value_checks(legs, cas)["外れ"] == {}
    b = legs.copy()
    b["in_lag_ms"], b["in_quote_age_ms"] = "-300001", "300001"
    assert chk.main_value_checks(b, cas)["外れ"] == {"古さ > 300 秒": 1}
    c2 = cas.copy()
    c2["pnl_bp"] = "50"
    assert chk.main_value_checks(legs, c2)["外れ"] == {"連鎖の pnl_bp ≠ レグの和": 1}
    b = legs.copy()
    b["order_out"] = "1"
    assert chk.main_value_checks(b, cas)["外れ"] == {"order_out ≠ −order_in": 1}


def test_check_repro_quote_table_check():
    chk = _load(RERUN_DIR / "check_repro.py", "check_repro_qt")
    import pandas as pd
    q = _qb({1: (0.995, 100.0, 100.1), 11: (10.9, 100.9, 101.0)})
    row = {"in_lag_ms": "-5", "out_lag_ms": "-100", "in_target_ms": str(D0 + 1000),
           "out_target_ms": str(D0 + 11000), "order_in": "1", "order_out": "-1",
           "in_px": "100.1", "out_px": "100.9", "in_fill_ms": str(D0 + 995),
           "out_fill_ms": str(D0 + 10900)}
    assert chk.quote_checks(pd.DataFrame([row]), q)["外れ"] == {}
    bad = dict(row, in_px="100.0")                       # 買いに買い気配 → 外れ
    assert chk.quote_checks(pd.DataFrame([bad]), q)["外れ"] == {"in_px・in_fill_ms ≠ 気配の表": 1}
    bad = dict(row, out_fill_ms=str(D0 + 10901))
    assert chk.quote_checks(pd.DataFrame([bad]), q)["外れ"] == {"out_px・out_fill_ms ≠ 気配の表": 1}


def test_check_repro_never_opens_orig_after_seal(tmp_path, monkeypatch):
    chk = _load(RERUN_DIR / "check_repro.py", "check_repro_seal")
    with pytest.raises(SystemExit, match="開かない"):
        chk.read_orig(tmp_path, "cascades", "2023-12-17")
    # main を 12-16〜12-17 で打っても、元の置き場の 12-17 は開かない(新しい出力だけ数える)
    orig, new = tmp_path / "orig", tmp_path / "new"
    for root in (orig, new):
        (root / "chunks").mkdir(parents=True)
    (new / "run_meta.json").write_text(json.dumps({}))
    opened = []
    real = chk.read

    def spy(p):
        opened.append(str(p))
        return real(p)
    monkeypatch.setattr(chk, "read", spy)
    assert chk.main(["--orig", str(orig), "--new", str(new), "--start", "2023-12-16",
                     "--end", "2023-12-17"]) == 0
    assert any(str(orig) in p and "2023-12-16" in p for p in opened)
    assert not any(str(orig) in p and "2023-12-17" in p for p in opened)


def test_check_repro_missing_counts():
    chk = _load(RERUN_DIR / "check_repro.py", "check_repro_mc")
    import pandas as pd
    k = {"side": "SELL", "gap_s": "60", "start_ms": "1", "delay_s": "1", "policy": "p",
         "type": "A"}
    cas = pd.DataFrame([k | {"missing": "1", "missing_anyside": "0", "missing_taker_prev": "1",
                             "missing_taker_wait": "0"},
                        dict(k, start_ms="2") | {"missing": "0", "missing_anyside": "0",
                                                 "missing_taker_prev": "0",
                                                 "missing_taker_wait": "0"}])
    legs = pd.DataFrame([k | {"pnl_bp_anyside": "1", "pnl_bp_taker_prev": "", "pnl_bp_taker_wait": "2"},
                         dict(k, start_ms="2") | {"pnl_bp_anyside": "1", "pnl_bp_taker_prev": "3",
                                                  "pnl_bp_taker_wait": "2"}])
    m = chk.missing_counts(legs, cas)
    assert m["主(気配)"] == {"欠けた連鎖": 1, "欠けた連鎖のレグ": 1, "損益の列が NaN のレグ": None}
    assert m["(b) 直前の同じ側の約定"] == {"欠けた連鎖": 1, "欠けた連鎖のレグ": 1,
                                       "損益の列が NaN のレグ": 1}
    assert m["元の付け方"]["欠けた連鎖"] == 0


def test_read_quotes_orders_same_ms_by_update_id(tmp_path):
    # Q15: ファイルの中で同じ ms の行が update_id の逆順に並んでいても、後の更新(大きい update_id)を最新にする
    import zipfile
    fetch = _load(REPO / "scripts" / "c9_fetch_bookticker.py", "c9_fetch_q15")
    csv_text = ("update_id,best_bid_price,best_bid_qty,best_ask_price,best_ask_qty,"
                "transaction_time,event_time\n"
                f"9,12.0,1,12.1,1,{D0 + 1000},{D0 + 1001}\n"
                f"8,11.0,1,11.1,1,{D0 + 1000},{D0 + 1001}\n"
                f"7,10.0,1,10.1,1,{D0 + 500},{D0 + 501}\n")
    zp = tmp_path / "q.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("q.csv", csv_text)
    df = fetch.read_quotes(zp)
    assert df["update_id"].tolist() == [7, 8, 9]
    rows = fetch.quotes_at(df, np.array([D0 + 1000, D0 + 999], np.int64), None)
    assert [r["bid"] for r in rows] == [12.0, 10.0]
