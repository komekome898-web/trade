"""`scripts/o3c_signal_materials.py`(清算を起点とした値動きの予測可能性 —
材料の選定)の試験。

**測るもの**(委任文【テスト】(1)〜(7))
  1. 候補 22 本が ts 以後を使わない(ts 以後の約定・清算・5 分値を消した合成入力で
     同じ値。**p₀ に当たる約定の価格を実際に別の値に書き換えた入力でも同じ値**)。
  2. 2 組の分け方(合成の `bundle_pos`・`bundle_pos_single` で 4 群 -> 2 組)。
  3. 分かれ方の数(合成の 2 群で手計算と一致、同値 0.5、欠測の除外)。
  4. 表が前半だけから作られる(後半の値を変えても表が変わらない)。
  5. 5' が「先」だけ(通り過ぎた水準は除く)。
  6. 判定語が `tables.md` に無い。
  7. `paper_logs/` を開かない(ソースに文字列が無い)。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_materials", ROOT / "scripts" / "o3c_signal_materials.py")
sm = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(sm)
sc = sm.sc

DATA_ROOT = ROOT / "backtest_data" / "binance_cm_o3c_20260913"
ROWS_PRINTS = sm.DEFAULT_ROWS_PRINTS
have_data = ROWS_PRINTS.exists() and (DATA_ROOT / "aggTrades").exists()
needs_data = pytest.mark.skipif(not have_data, reason="探索段5の行データか公開アーカイブが無い")


def make_prints_csv(tmp_path: Path, rows: list) -> "sc.PrintsCSV":
    cols = ["print_id", "day", "side", "ts_ms", "t0_ms", "p0", "notional",
           "dist_node_bp", "oi_covered", "bundle_id"]
    df = pd.DataFrame([{c: r.get(c, "") for c in cols} for r in rows])
    df["kind"] = "print"
    p = tmp_path / "rows_prints.csv.gz"
    df.to_csv(p, index=False, compression="gzip")
    return sc.PrintsCSV(p)


# ---------------------------------------------------------------------------
# (1) 候補が ts 以後を使わない(新規 9 本 + 5')
# ---------------------------------------------------------------------------
def _synthetic_trades(ts: int, future_prices_differ: bool, p0_differs: bool):
    """1 秒刻みの約定列。`ts` より後だけ、または `ts` 時点の 1 件(=「p₀ に当たる
    約定」)だけを、2 通りの価格にできる。"""
    lo = ts - 7 * 3600_000 - 300_000   # 5'(8h)にも足りる範囲
    hi = ts + 5_000
    times = np.arange(lo, hi + 1, 1000, dtype=np.int64)
    prices = 30000.0 + 0.02 * np.sin((times - lo) / 50_000.0) * (times - lo) / 3_600_000.0
    qtys = np.ones(times.size)
    maker = (np.arange(times.size) % 2 == 0)
    after = times > ts
    if future_prices_differ:
        prices = prices.copy()
        prices[after] = prices[after] + 5_000.0
    if p0_differs:
        # 「p₀ に当たる約定」= ts 以後で最初の約定(at_or_after(ts))の価格を書き換える。
        prices = prices.copy()
        at_or_after = np.flatnonzero(times >= ts)
        if at_or_after.size:
            prices[at_or_after[0]] = prices[at_or_after[0]] + 12_345.0
    return times, prices, qtys, maker


def _make_chain_pc(tmp_path, day, ts_prev, ts_cur, side="SELL"):
    rows = [
        {"print_id": "prev", "day": day, "side": side, "ts_ms": ts_prev,
         "t0_ms": ts_prev, "p0": 30000.0, "notional": 300_000.0,
         "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": "b1"},
        {"print_id": "cur", "day": day, "side": side, "ts_ms": ts_cur,
         "t0_ms": ts_cur, "p0": 29990.0, "notional": 500_000.0,
         "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": "b1"},
        # 反対側(A9 が拾う)
        {"print_id": "opp", "day": day, "side": "BUY", "ts_ms": ts_cur - 10_000,
         "t0_ms": ts_cur - 10_000, "p0": 30000.0, "notional": 70_000.0,
         "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": "b2"},
    ]
    pc = make_prints_csv(tmp_path, rows)
    return pc


def test_new_candidates_do_not_use_data_after_ts_or_p0(tmp_path):
    day = "2024-01-02"
    ts_prev = sc.day_start_ms(day) + 3600_000
    ts_cur = ts_prev + 30_000   # 連鎖の内側(gap 30s <= 60s)
    pc = _make_chain_pc(tmp_path, day, ts_prev, ts_cur)
    nb = sc.same_side_neighbors(pc)
    chain_cum = sm.build_chain_cum_notional(pc)
    side_prefix = sm.build_side_prefix(pc)
    i_cur = int(np.flatnonzero(pc.print_id == "cur")[0])
    t_oi = np.array([ts_prev - 3_600_000, ts_prev - 1, ts_cur - 1], dtype=np.int64)
    oi_lvl = np.array([1000.0, 900.0, 850.0])

    def run(times, prices, qtys, maker):
        p_pre, _ = sc.price_at_or_before(times, prices, ts_cur - 1)
        day0 = sc.day_start_ms(day)
        dmax, dmin = sm.day_extremes_batch(times, prices, np.array([ts_cur]), day0)
        cand5p = sm.node_ahead_bp_batch(times, prices, qtys, np.array([ts_cur]),
                                        np.array([p_pre]), np.array([pc.sign[i_cur]]))
        new = sm.compute_new_candidates(pc, nb, i_cur, times, prices, qtys, maker,
                                       t_oi, oi_lvl, chain_cum, side_prefix,
                                       float(p_pre), float(dmax[0]), float(dmin[0]))
        return cand5p[0], new

    times_a, prices_a, qtys_a, maker_a = _synthetic_trades(ts_cur, False, False)
    times_b, prices_b, qtys_b, maker_b = _synthetic_trades(ts_cur, True, False)
    times_c, prices_c, qtys_c, maker_c = _synthetic_trades(ts_cur, False, True)
    assert np.array_equal(prices_a[times_a <= ts_cur - 1], prices_b[times_b <= ts_cur - 1])
    # (c) は「p₀ に当たる約定」(ts 以後で最初の約定)の価格だけを書き換えている
    at_ts = np.flatnonzero(times_c >= ts_cur)[0]
    assert prices_c[at_ts] != prices_a[at_ts]
    assert np.array_equal(prices_a[times_a < ts_cur], prices_c[times_c < ts_cur])

    cand5p_a, new_a = run(times_a, prices_a, qtys_a, maker_a)
    cand5p_b, new_b = run(times_b, prices_b, qtys_b, maker_b)
    cand5p_c, new_c = run(times_c, prices_c, qtys_c, maker_c)

    def eq(x, y):
        if isinstance(x, float) and isinstance(y, float) and x != x and y != y:
            return True
        return x == y

    for tag, cand5p_x, new_x in (("未来を変えた", cand5p_b, new_b),
                                 ("p0 を書き換えた", cand5p_c, new_c)):
        assert eq(cand5p_a, cand5p_x), f"5' が {tag} 入力で変わった: {cand5p_a} != {cand5p_x}"
        for k in ("F3", "F4", "A3", "A4", "A5", "A6", "A9", "C3", "C4"):
            assert eq(new_a[k], new_x[k]), (
                f"{k} が {tag} 入力で変わった: {new_a[k]} != {new_x[k]}")
    # このプリントは連鎖の 2 件目なので F3/F4/A3/A5 は欠測にならない(前提の確認)
    for k in ("F3", "F4", "A3", "A5"):
        assert new_a[k] == new_a[k], f"{k} が前提と違って欠測になっている"


def test_chain_first_print_has_missing_inner_candidates(tmp_path):
    """1 件目(連鎖の開始)では F3・F4・A3・A5 が欠測。"""
    day = "2024-01-02"
    ts0 = sc.day_start_ms(day) + 3600_000
    rows = [{"print_id": "solo", "day": day, "side": "SELL", "ts_ms": ts0,
            "t0_ms": ts0, "p0": 30000.0, "notional": 100_000.0,
            "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": "b1"}]
    pc = make_prints_csv(tmp_path, rows)
    nb = sc.same_side_neighbors(pc)
    chain_cum = sm.build_chain_cum_notional(pc)
    side_prefix = sm.build_side_prefix(pc)
    times, prices, qtys, maker = _synthetic_trades(ts0, False, False)
    p_pre, _ = sc.price_at_or_before(times, prices, ts0 - 1)
    t_oi = np.array([ts0 - 1], dtype=np.int64)
    oi_lvl = np.array([1000.0])
    new = sm.compute_new_candidates(pc, nb, 0, times, prices, qtys, maker, t_oi, oi_lvl,
                                   chain_cum, side_prefix, float(p_pre), float("nan"),
                                   float("nan"))
    for k in ("F3", "F4", "A3", "A5"):
        assert new[k] != new[k], f"1 件目なのに {k} が欠測でない: {new[k]}"


# ---------------------------------------------------------------------------
# (5) 5' が「先」だけ(通り過ぎた水準は除く)
# ---------------------------------------------------------------------------
def test_5prime_only_counts_nodes_ahead():
    """(a) 全ての約定が p_ref より下(95 前後)しか無ければ、BUY(先=上)は NaN、
    SELL(先=下)は @95 のノードを拾う。(b) p_ref より上(105)に厚いノードを足すと、
    BUY はそれを拾い、SELL は変わらず @95 のまま(105 は SELL の先ではない)。"""
    rng = np.random.default_rng(3)
    times = np.arange(0, 3600 * 1000, 1000, dtype=np.int64)
    n = times.size
    ts_arr = np.array([3_600_000 - 1])
    p_ref_arr = np.array([100.0])

    # (a) p_ref(100)より下(95 前後)にしか約定が無い
    prices_a = 95.0 + 0.3 * rng.standard_normal(n)
    qtys_a = np.ones(n)
    out_buy_a = sm.node_ahead_bp_batch(times, prices_a, qtys_a, ts_arr, p_ref_arr,
                                       np.array([1.0]), window_ms=3_600_000,
                                       step=sm.NODE_STEP)
    out_sell_a = sm.node_ahead_bp_batch(times, prices_a, qtys_a, ts_arr, p_ref_arr,
                                        np.array([-1.0]), window_ms=3_600_000,
                                        step=sm.NODE_STEP)
    assert out_buy_a[0] != out_buy_a[0], (
        f"BUY(先=上)なのに先に何も無いのに値が出た(@95 前後は後ろ側): {out_buy_a[0]}")
    assert out_sell_a[0] == out_sell_a[0], "SELL(先=下)なのに@95のノードを拾えていない"
    # (95-100)/100*1e4 = -500bp -> 距離(正)は約 500bp
    assert abs(out_sell_a[0] - 500.0) < 15.0, f"距離が @95 の想定から外れる: {out_sell_a[0]}"

    # (b) さらに 105(p_ref より上)に厚いノードを足す
    prices_b = prices_a.copy()
    qtys_b = qtys_a.copy()
    mask = (times > 1_000_000) & (times < 1_100_000)
    prices_b[mask] = 105.0
    qtys_b[mask] = 200.0
    out_buy_b = sm.node_ahead_bp_batch(times, prices_b, qtys_b, ts_arr, p_ref_arr,
                                       np.array([1.0]), window_ms=3_600_000,
                                       step=sm.NODE_STEP)
    out_sell_b = sm.node_ahead_bp_batch(times, prices_b, qtys_b, ts_arr, p_ref_arr,
                                        np.array([-1.0]), window_ms=3_600_000,
                                        step=sm.NODE_STEP)
    assert out_buy_b[0] == out_buy_b[0], "BUY(先=上)なのに先のノード(@105)を拾えていない"
    assert abs(out_buy_b[0] - 500.0) < 15.0, f"距離が @105 の想定から外れる: {out_buy_b[0]}"
    # SELL の先(下)は @95 近辺のまま(@105 は SELL の先ではないので、そちらには飛ばない。
    # 上位 10 分位の母集団が変わる分だけ僅かにずれてよいので緩めに見る)
    assert abs(out_sell_b[0] - 500.0) < 60.0, (
        f"SELL(先=下)が、先ではない@105 を足した影響で @95 から離れすぎた: {out_sell_b[0]}")


# ---------------------------------------------------------------------------
# (2) 2 組の分け方
# ---------------------------------------------------------------------------
def test_pos_and_group_four_way_split():
    cases = [
        (("最初", 0), ("多件の最初", "A")),
        (("最後", 1), ("単発", "A")),
        (("途中", 0), ("途中", "B")),
        (("最後", 0), ("多件の最後", "B")),
        (("束の外", 0), ("束の外", "")),
    ]
    for (bp, single), expect in cases:
        assert sm.pos_and_group(bp, single) == expect


# ---------------------------------------------------------------------------
# (3) 分かれ方の数
# ---------------------------------------------------------------------------
def test_separation_prob_hand_computed():
    # 止まる側 = [1, 2, 3]、続く側 = [2, 4]。
    # ペア(3*2=6組): (1,2)=0 (1,4)=0 (2,2)=0.5 (2,4)=0 (3,2)=1 (3,4)=0
    # 合計 = 1.5 / 6 = 0.25
    stop = np.array([1.0, 2.0, 3.0])
    cont = np.array([2.0, 4.0])
    got = sm.separation_prob(stop, cont)
    assert abs(got - 0.25) < 1e-9

    # 完全に分かれる場合 -> 1.0
    got2 = sm.separation_prob(np.array([10.0, 11.0]), np.array([1.0, 2.0]))
    assert got2 == 1.0

    # 欠測は両側から除く
    stop_nan = np.array([1.0, 2.0, np.nan, 3.0])
    got3 = sm.separation_prob(stop_nan, cont)
    assert abs(got3 - 0.25) < 1e-9


# ---------------------------------------------------------------------------
# (4) 表が前半だけから作られる
# ---------------------------------------------------------------------------
def _synthetic_screen_df(seed: int, back_half_shift: float) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for half in ("前半", "後半"):
        for pos_label, group in (("単発", "A"), ("多件の最初", "A"),
                                 ("途中", "B"), ("多件の最後", "B")):
            for k in range(20):
                v = float(rng.normal())
                if half == "後半":
                    v += back_half_shift
                rows.append({"half": half, "pos_label": pos_label, "group": group,
                            "cand_1": v})
    return pd.DataFrame(rows)


def test_tables_built_from_front_half_only():
    df1 = _synthetic_screen_df(0, back_half_shift=0.0)
    df2 = _synthetic_screen_df(0, back_half_shift=9999.0)  # 後半だけ派手に変える
    front1 = df1[df1["half"] == "前半"].reset_index(drop=True)
    front2 = df2[df2["half"] == "前半"].reset_index(drop=True)
    a1 = sm.screen_rows(front1, "A", ["1"], "単発", "多件の最初")
    a2 = sm.screen_rows(front2, "A", ["1"], "単発", "多件の最初")
    assert a1 == a2, "後半の値を変えたら前半だけの表が変わった"


# ---------------------------------------------------------------------------
# (6) 判定語
# ---------------------------------------------------------------------------
def test_no_banned_words_raises():
    with pytest.raises(SystemExit):
        sm.check_no_banned("この材料は陽性だ", "test")
    sm.check_no_banned("この材料は分かれ方の数が大きい", "test")  # 通る


@needs_data
def test_tables_md_has_no_banned_words_if_present():
    p = sm.DEFAULT_OUT / "tables.md"
    if not p.exists():
        pytest.skip("まだ tables.md が無い")
    sm.check_no_banned(p.read_text(), "tables.md")


# ---------------------------------------------------------------------------
# (7) paper_logs/ を開かない
# ---------------------------------------------------------------------------
def test_source_never_opens_paper_logs():
    """`paper_logs` という文字列が出るのは説明文(docstring)だけで、実際にそれを
    開くコードは無い(`o3c_signal_continue.py` の同名試験と同じ流儀)。"""
    src = (ROOT / "scripts" / "o3c_signal_materials.py").read_text().splitlines()
    hits = [ln for ln in src if "paper_logs" in ln]
    assert hits and all(
        ln.lstrip().startswith(("#", "*", '"""', "設計:", "委任文:")) or "開かない" in ln
        for ln in hits), hits


@needs_data
def test_run_does_not_touch_paper_logs(tmp_path, monkeypatch):
    import builtins
    import gzip

    touched: list = []
    real_open = builtins.open
    real_gzopen = gzip.open

    def note(p):
        if "paper_logs" in Path(str(p)).parts:
            touched.append(str(p))

    def guarded_open(file, *a, **k):
        note(file)
        return real_open(file, *a, **k)

    def guarded_gzopen(filename, *a, **k):
        note(filename)
        return real_gzopen(filename, *a, **k)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(gzip, "open", guarded_gzopen)
    rc = sm.main(["--data-root", str(DATA_ROOT), "--rows-prints", str(ROWS_PRINTS),
                 "--rows-continue", str(sm.DEFAULT_ROWS_CONTINUE),
                 "--out", str(tmp_path / "o"), "--probe-md", str(tmp_path / "probe.md"),
                 "--limit-days", "2", "--skip-probes", "--progress-every", "1000"])
    assert rc == 0
    assert touched == []
