"""`scripts/o3c_oi_distance.py` の単体テスト(2026-09-17)。

固定するのは 4 点(委任の逐語「**プロファイルの構築(ΔOI > 0 だけ積む、按分の和が ΔOI に
一致、欠測日の NaN、符号)**」):

  (a) ΔOI の桶の作り方: ΔOI > 0 の 5 分だけを使う / metrics の行が飛んでいる所では
      ΔOI を作らない / ΔOI を置く価格は [T−5 分, T) の VWAP。
  (b) taker の向きによる按分の和が ΔOI に一致する。
  (c) 建玉が欠測(桶が無い / 窓が被覆の外)のとき、建玉側の列が NaN になり `oi_covered` が 0。
  (d) 符号: SELL はそのまま、BUY は反転、対照は NaN。レバレッジ換算の式と NaN の境目。

**観測表の作り方だけを固定する。相場についての判定は一切しない。**
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


M = _load("o3c_oi_distance")
BASE = _load("o3c_price_level_table")

STEP = BASE.log_step(0.1)
MS5 = M.BUCKET_MS


def _bucket_lookup(pairs):
    """{桶の開始時刻: (vwap, buy_share, vol, n)} を作る。"""
    return {int(t): (float(v), float(s), 1.0, 1) for t, v, s in pairs}


def _metrics(t0, ois, step_ms=MS5):
    t = np.array([t0 + i * step_ms for i in range(len(ois))], dtype=np.int64)
    return (t, np.array(ois, dtype=np.float64))


# ---------------------------------------------------------------- (a) ΔOI > 0


def test_only_positive_delta_is_stacked():
    """ΔOI ≤ 0 の 5 分は積まない(件数は数える)。"""
    t0 = 1_700_000_000_000
    md = [_metrics(t0, [100.0, 90.0, 120.0, 120.0])]
    lookup = _bucket_lookup(
        [
            (t0 + 0 * MS5, 30000.0, 0.5),
            (t0 + 1 * MS5, 31000.0, 0.5),
            (t0 + 2 * MS5, 32000.0, 0.5),
        ]
    )
    b = M.build_delta_buckets(md, lookup)
    assert b["n_delta_rows"] == 3          # 3 本の差分(−10, +30, 0)
    assert b["n_positive"] == 1
    assert b["n_nonpositive"] == 2         # 負の 1 本と 0 の 1 本
    assert b["t_ms"].tolist() == [t0 + 2 * MS5]
    assert b["delta"].tolist() == [30.0]
    # ΔOI(T) は [T−5 分, T) の VWAP に置く。T = t0+2*MS5 なので桶 t0+1*MS5。
    assert b["vwap"].tolist() == [31000.0]


def test_gap_in_metrics_makes_no_delta():
    """metrics の行が 5 分刻みで並んでいない所では ΔOI を作らない。"""
    t0 = 1_700_000_000_000
    t = np.array([t0, t0 + MS5, t0 + 3 * MS5], dtype=np.int64)
    md = [(t, np.array([100.0, 150.0, 400.0]))]
    lookup = _bucket_lookup(
        [(t0, 30000.0, 0.5), (t0 + MS5, 30100.0, 0.5), (t0 + 2 * MS5, 30200.0, 0.5)]
    )
    b = M.build_delta_buckets(md, lookup)
    assert b["n_delta_rows"] == 1          # 5 分ちょうどの並びは 1 組だけ
    assert b["t_ms"].tolist() == [t0 + MS5]
    assert b["delta"].tolist() == [50.0]


def test_positive_delta_without_trades_is_counted_and_dropped():
    """ΔOI > 0 でもその 5 分に約定が無ければ置けない(件数だけ数える)。"""
    t0 = 1_700_000_000_000
    md = [_metrics(t0, [100.0, 130.0])]
    b = M.build_delta_buckets(md, {})      # 桶が引けない
    assert b["n_positive"] == 1
    assert b["n_positive_no_trades"] == 1
    assert b["t_ms"].size == 0


def test_coverage_start_is_last_contiguous_run():
    t0 = 1_700_000_000_000
    t_all = np.array([t0, t0 + MS5, t0 + 5 * MS5, t0 + 6 * MS5], dtype=np.int64)
    assert M.coverage_start_ms(t_all) == t0 + 5 * MS5
    assert M.coverage_start_ms(np.zeros(0, dtype=np.int64)) is None


# ------------------------------------------------------------------- (b) 按分


def test_taker_split_sums_to_delta():
    """買い taker ぶん + 売り taker ぶん = ΔOI(桶ごと・合計とも)。"""
    t0 = 1_700_000_000_000
    md = [_metrics(t0, [100.0, 160.0, 260.0])]
    lookup = _bucket_lookup([(t0, 30000.0, 0.25), (t0 + MS5, 30100.0, 0.8)])
    b = M.build_delta_buckets(md, lookup)
    w_long = b["delta"] * b["buy_share"]
    w_short = b["delta"] * (1.0 - b["buy_share"])
    assert np.allclose(w_long + w_short, b["delta"])
    assert np.allclose(w_long, [60.0 * 0.25, 100.0 * 0.8])
    assert np.allclose(w_short, [60.0 * 0.75, 100.0 * 0.2])


def test_bucket_trade_stats_vwap_and_buy_share():
    """`is_buyer_maker == False` が買い taker。約定が無い桶は NaN。"""
    day = "2023-06-25"
    day_start, _ = BASE.day_bounds_ms(day)
    times = np.array([day_start + 1, day_start + 2, day_start + MS5 + 1], dtype=np.int64)
    prices = np.array([100.0, 200.0, 300.0])
    qtys = np.array([1.0, 3.0, 5.0])
    maker = np.array([True, False, False])  # True = 売り taker
    bs = M.bucket_trade_stats(day, times, prices, qtys, maker)
    assert bs["vwap"][0] == pytest.approx((100.0 * 1 + 200.0 * 3) / 4.0)
    assert bs["buy_share"][0] == pytest.approx(3.0 / 4.0)
    assert bs["vwap"][1] == pytest.approx(300.0)
    assert bs["buy_share"][1] == pytest.approx(1.0)
    assert math.isnan(bs["vwap"][2])
    assert math.isnan(bs["buy_share"][2])


def test_side_profile_uses_apportioned_weights():
    """SELL はロング側、BUY はショート側のプロファイルを見る。

    2 本の桶を離れた価格に置き、片方を買い taker 100%、もう片方を売り taker 100% にすると、
    ロング側とショート側で平均建値が別の桶に寄る。
    """
    t0 = 1_700_000_000_000
    buckets = {
        "t_ms": np.array([t0, t0 + MS5], dtype=np.int64),
        "delta": np.array([100.0, 100.0]),
        "vwap": np.array([30000.0, 31000.0]),
        "buy_share": np.array([1.0, 0.0]),
    }
    p_liq = 30500.0
    rows = [
        {"time_ms": t0 + MS5, "side": "SELL", "p_liq": p_liq, "p0": p_liq},
        {"time_ms": t0 + MS5, "side": "BUY", "p_liq": p_liq, "p0": p_liq},
    ]
    # 窓 10 分 = 桶 2 本ぶん(被覆の先頭 t0 から測って窓の先頭がちょうど t0−5 分)。
    out, n_unc = M.oi_columns_for_rows(rows, buckets, 2 * MS5, STEP, t0)
    assert n_unc == 0
    # 全体の平均建値は 2 本の真ん中あたり、ロング側は 30000 側、ショート側は 31000 側。
    assert out[0]["oi_side_dist_vwap_bp"] < out[0]["oi_dist_vwap_bp"]
    assert out[1]["oi_side_dist_vwap_bp"] > out[1]["oi_dist_vwap_bp"]
    assert out[0]["oi_side_total_delta"] == pytest.approx(100.0)
    assert out[1]["oi_side_total_delta"] == pytest.approx(100.0)
    # 全体のプロファイルの重みの合計は ΔOI の合計。
    assert out[0]["oi_total_delta"] == pytest.approx(200.0)


def test_single_bucket_profile_matches_bin_center():
    """桶が 1 本だけなら、平均建値もノードもそのビンの代表価格になる。"""
    t0 = 1_700_000_000_000
    buckets = {
        "t_ms": np.array([t0], dtype=np.int64),
        "delta": np.array([500.0]),
        "vwap": np.array([30000.0]),
        "buy_share": np.array([0.6]),
    }
    p_liq = 30300.0
    rows = [{"time_ms": t0 + 1000, "side": "SELL", "p_liq": p_liq, "p0": p_liq}]
    out, _ = M.oi_columns_for_rows(rows, buckets, 60_000, STEP, t0)
    center = float(BASE.bin_center_price(BASE.bin_index(30000.0, STEP), STEP))
    expect = (center - p_liq) / p_liq * 1e4
    assert out[0]["oi_dist_vwap_bp"] == pytest.approx(round(expect, 4))
    assert out[0]["oi_dist_node_bp"] == pytest.approx(round(expect, 4))
    assert out[0]["oi_n_bins"] == 1
    assert out[0]["oi_n_buckets"] == 1
    assert out[0]["oi_side_total_delta"] == pytest.approx(300.0)


# ------------------------------------------------------------- (c) 欠測の NaN


def test_no_buckets_gives_nan_and_uncovered():
    """建玉の桶が 1 本も無い(metrics 欠測の日)なら、建玉側は全部 NaN。"""
    rows = [{"time_ms": 1_700_000_000_000, "side": "SELL", "p_liq": 100.0, "p0": 100.0}]
    empty = {
        "t_ms": np.zeros(0, dtype=np.int64),
        "delta": np.zeros(0),
        "vwap": np.zeros(0),
        "buy_share": np.zeros(0),
    }
    out, n_unc = M.oi_columns_for_rows(rows, empty, 8 * 3600 * 1000, STEP, None)
    assert n_unc == 1
    assert out[0]["oi_covered"] == 0
    for col in M.OI_COLUMNS:
        assert isinstance(out[0][col], float) and math.isnan(out[0][col])


def test_window_reaching_outside_coverage_gives_nan():
    """窓の先頭が建玉の被覆より前なら NaN(W の窓が欠測にかかる日)。"""
    t0 = 1_700_000_000_000
    buckets = {
        "t_ms": np.array([t0, t0 + MS5], dtype=np.int64),
        "delta": np.array([100.0, 100.0]),
        "vwap": np.array([30000.0, 30100.0]),
        "buy_share": np.array([0.5, 0.5]),
    }
    w = 8 * 3600 * 1000
    late = t0 + MS5 + 1000
    rows = [{"time_ms": late, "side": "SELL", "p_liq": 30050.0, "p0": 30050.0}]
    # 被覆の先頭が t0 なので、窓 (late−8h) は t0−5 分 より前 -> NaN。
    out, n_unc = M.oi_columns_for_rows(rows, buckets, w, STEP, t0)
    assert n_unc == 1
    assert out[0]["oi_covered"] == 0
    assert math.isnan(out[0]["oi_dist_vwap_bp"])
    # 窓を短く(1 分)すれば同じ行が埋まる。
    out2, n_unc2 = M.oi_columns_for_rows(rows, buckets, 60_000, STEP, t0)
    assert n_unc2 == 0
    assert out2[0]["oi_covered"] == 1
    assert not math.isnan(out2[0]["oi_dist_vwap_bp"])


# --------------------------------------------------------------------- (d) 符号


def test_liqdir_sign_sell_buy_control():
    """SELL はそのまま、BUY は符号を反転、対照(side 空)は NaN。"""
    vals = {
        "dist_vwap_bp": 100.0,
        "dist_node_bp": -20.0,
        "oi_dist_vwap_bp": 50.0,
        "oi_dist_node_bp": -5.0,
        "oi_side_dist_vwap_bp": 40.0,
        "oi_side_dist_node_bp": 7.0,
    }
    sell = dict(vals, side="SELL")
    buy = dict(vals, side="BUY")
    ctl = dict(vals, side="")
    for r in (sell, buy, ctl):
        M._apply_liqdir_and_leverage(r, None)
    assert sell["dist_vwap_bp_liqdir"] == pytest.approx(100.0)
    assert sell["oi_dist_node_bp_liqdir"] == pytest.approx(-5.0)
    assert buy["dist_vwap_bp_liqdir"] == pytest.approx(-100.0)
    assert buy["oi_dist_node_bp_liqdir"] == pytest.approx(5.0)
    for _, dst in M.LIQDIR_SOURCE:
        assert math.isnan(ctl[dst])
    # --mmr を渡していないのでレバレッジ換算は作らない。
    assert math.isnan(sell["implied_leverage"])
    assert math.isnan(sell["implied_leverage_side"])


def test_implied_leverage_formula_and_nan_boundary():
    """implied_leverage = 1 / (d/1e4 + mmr)。分母が 0 以下なら NaN。"""
    mmr = 0.005
    r = {
        "side": "SELL",
        "dist_vwap_bp": 0.0,
        "dist_node_bp": 0.0,
        "oi_dist_vwap_bp": 100.0,   # 1% 離れている
        "oi_dist_node_bp": 0.0,
        "oi_side_dist_vwap_bp": 200.0,
        "oi_side_dist_node_bp": 0.0,
    }
    M._apply_liqdir_and_leverage(r, mmr)
    assert r["implied_leverage"] == pytest.approx(1.0 / (0.01 + mmr), abs=1e-3)
    assert r["implied_leverage_side"] == pytest.approx(1.0 / (0.02 + mmr), abs=1e-3)

    neg = dict(r, oi_dist_vwap_bp=-100.0, oi_side_dist_vwap_bp=-50.0)
    M._apply_liqdir_and_leverage(neg, mmr)
    assert math.isnan(neg["implied_leverage"])          # −0.01 + 0.005 < 0
    assert math.isnan(neg["implied_leverage_side"])     # −0.005 + 0.005 = 0

    buy = dict(r, side="BUY")
    M._apply_liqdir_and_leverage(buy, mmr)
    # BUY は符号が反転するので、同じ生の値では分母が負になり NaN。
    assert math.isnan(buy["implied_leverage"])


# ------------------------------------------------- (e) --side-price split(09-18)


def _split_buckets(t0, vwap, vwap_buy, vwap_sell, delta=100.0, share=0.5):
    n = len(vwap)
    return {
        "t_ms": np.array([t0 + i * MS5 for i in range(n)], dtype=np.int64),
        "delta": np.full(n, float(delta)),
        "vwap": np.array(vwap, dtype=np.float64),
        "buy_share": np.full(n, float(share)),
        "vwap_buy": np.array(vwap_buy, dtype=np.float64),
        "vwap_sell": np.array(vwap_sell, dtype=np.float64),
    }


def test_split_uses_buy_only_and_sell_only_vwap():
    """split では、ロング側が買い taker の VWAP、ショート側が売り taker の VWAP に載る。"""
    t0 = 1_700_000_000_000
    b = _split_buckets(t0, [30000.0], [30100.0], [29900.0])
    p_liq = 30000.0
    rows = [
        {"time_ms": t0 + 1000, "side": "SELL", "p_liq": p_liq, "p0": p_liq},
        {"time_ms": t0 + 1000, "side": "BUY", "p_liq": p_liq, "p0": p_liq},
    ]
    same, _ = M.oi_columns_for_rows(rows, b, 60_000, STEP, t0, side_price="same")
    split, _ = M.oi_columns_for_rows(rows, b, 60_000, STEP, t0, side_price="split")

    def center_bp(price):
        c = float(BASE.bin_center_price(BASE.bin_index(price, STEP), STEP))
        return (c - p_liq) / p_liq * 1e4

    # same: 両側とも全体の VWAP のビン。
    for o in same:
        assert o["oi_side_dist_vwap_bp"] == pytest.approx(round(center_bp(30000.0), 4))
        assert o["oi_side_dist_node_bp"] == pytest.approx(round(center_bp(30000.0), 4))
    # split: SELL(ロング側)は買い taker の VWAP、BUY(ショート側)は売り taker の VWAP。
    assert split[0]["oi_side_dist_vwap_bp"] == pytest.approx(round(center_bp(30100.0), 4))
    assert split[1]["oi_side_dist_vwap_bp"] == pytest.approx(round(center_bp(29900.0), 4))
    assert split[0]["oi_side_dist_vwap_bp"] > split[1]["oi_side_dist_vwap_bp"]
    # 全体のプロファイルと按分の重みは split でも変わらない。
    for a, c in zip(same, split):
        assert a["oi_dist_vwap_bp"] == pytest.approx(c["oi_dist_vwap_bp"])
        assert a["oi_dist_node_bp"] == pytest.approx(c["oi_dist_node_bp"])
        assert a["oi_total_delta"] == pytest.approx(c["oi_total_delta"])
        assert a["oi_side_total_delta"] == pytest.approx(c["oi_side_total_delta"])


def test_split_one_side_empty_is_skipped():
    """片側の約定が 0 件の 5 分は、その側を積まない(重みが 0 なので重心は動かない)。"""
    t0 = 1_700_000_000_000
    # 桶 0 は売り taker だけ(買い taker 0 件 -> buy_share 0、vwap_buy は NaN)。
    b = {
        "t_ms": np.array([t0, t0 + MS5], dtype=np.int64),
        "delta": np.array([100.0, 100.0]),
        "vwap": np.array([30000.0, 31000.0]),
        "buy_share": np.array([0.0, 0.5]),
        "vwap_buy": np.array([np.nan, 31050.0]),
        "vwap_sell": np.array([30000.0, 30950.0]),
    }
    p_liq = 30500.0
    rows = [{"time_ms": t0 + MS5 + 1, "side": "SELL", "p_liq": p_liq, "p0": p_liq}]
    split, _ = M.oi_columns_for_rows(rows, b, 2 * MS5, STEP, t0, side_price="split")
    same, _ = M.oi_columns_for_rows(rows, b, 2 * MS5, STEP, t0, side_price="same")
    # ロング側の重みは桶 1 のぶんだけ(桶 0 は buy_share = 0)。
    assert split[0]["oi_side_total_delta"] == pytest.approx(50.0)
    assert same[0]["oi_side_total_delta"] == pytest.approx(50.0)
    # 重心は桶 1 の買い taker VWAP のビン。
    c = float(BASE.bin_center_price(BASE.bin_index(31050.0, STEP), STEP))
    assert split[0]["oi_side_dist_vwap_bp"] == pytest.approx(
        round((c - p_liq) / p_liq * 1e4, 4)
    )
    # 片側 0 件の桶の件数は build_delta_buckets が数える。
    md = [_metrics(t0, [100.0, 200.0, 300.0])]
    lookup = {
        int(t0): (30000.0, 0.0, 10.0, 5, float("nan"), 30000.0),
        int(t0 + MS5): (31000.0, 0.5, 10.0, 5, 31050.0, 30950.0),
    }
    bb = M.build_delta_buckets(md, lookup)
    assert bb["t_ms"].size == 2
    assert bb["n_no_buy_taker"] == 1
    assert bb["n_no_sell_taker"] == 0
    assert math.isnan(bb["vwap_buy"][0])


def test_same_ignores_side_prices():
    """`same` は側別 VWAP の列を一切見ない(鍵が有っても無くても同じ出力)。"""
    t0 = 1_700_000_000_000
    with_side = _split_buckets(
        t0, [30000.0, 30500.0], [30400.0, 31200.0], [29500.0, 29800.0], share=0.4
    )
    without = {k: v for k, v in with_side.items() if k not in ("vwap_buy", "vwap_sell")}
    p_liq = 30200.0
    rows = [
        {"time_ms": t0 + MS5 + 1, "side": s, "p_liq": p_liq, "p0": p_liq}
        for s in ("SELL", "BUY", "")
    ]
    a, na = M.oi_columns_for_rows(rows, with_side, 2 * MS5, STEP, t0, side_price="same")
    b, nb = M.oi_columns_for_rows(rows, without, 2 * MS5, STEP, t0, side_price="same")
    assert na == nb
    assert a == b
    # 側別の価格が全体とまったく違っても、`same` の側別の列は全体と同じビンに載る。
    for o in a[:2]:
        assert o["oi_side_dist_node_bp"] is not None


def test_bucket_trade_stats_side_vwaps():
    """`vwap_buy` / `vwap_sell` は片側の約定だけの VWAP。無い側は NaN。"""
    day = "2023-06-25"
    day_start, _ = BASE.day_bounds_ms(day)
    times = np.array(
        [day_start + 1, day_start + 2, day_start + 3, day_start + MS5 + 1],
        dtype=np.int64,
    )
    prices = np.array([100.0, 200.0, 400.0, 300.0])
    qtys = np.array([1.0, 3.0, 1.0, 5.0])
    maker = np.array([True, False, False, True])  # True = 売り taker
    bs = M.bucket_trade_stats(day, times, prices, qtys, maker)
    # 桶 0: 買い taker = (200,3) と (400,1)、売り taker = (100,1)。
    assert bs["vwap_buy"][0] == pytest.approx((200.0 * 3 + 400.0 * 1) / 4.0)
    assert bs["vwap_sell"][0] == pytest.approx(100.0)
    assert bs["n_buy"][0] == 2
    assert bs["n_sell"][0] == 1
    # 桶 1: 売り taker だけ -> 買い側は NaN。
    assert math.isnan(bs["vwap_buy"][1])
    assert bs["vwap_sell"][1] == pytest.approx(300.0)
    # 全体の VWAP は両側を合わせたもの(既存の列は変わらない)。
    assert bs["vwap"][0] == pytest.approx((100.0 + 600.0 + 400.0) / 5.0)


def test_side_spread_block_counts_and_quantiles():
    """側別 VWAP の差(bp)は桶の時刻で一意化して集計する。"""
    t0 = 1_700_000_000_000
    acc: dict = {}
    b = {
        "t_ms": np.array([t0, t0 + MS5], dtype=np.int64),
        "vwap": np.array([30000.0, 30000.0]),
        "vwap_buy": np.array([30003.0, np.nan]),
        "vwap_sell": np.array([29997.0, 30000.0]),
    }
    M.collect_side_spread(b, acc)
    M.collect_side_spread(b, acc)  # 同じ桶を 2 度読んでも増えない
    blk = M.side_spread_block(acc)
    assert blk["buckets_unique"] == 2
    assert blk["buckets_no_buy_taker"] == 1
    assert blk["buckets_no_sell_taker"] == 0
    assert blk["n"] == 1
    assert blk["q50"] == pytest.approx(2.0)   # (30003−29997)/30000*1e4 = 2bp


def test_columns_cover_everything_written():
    """`COLUMNS` に建玉側・符号揃え・レバレッジの列が全部入っている。"""
    for col in M.OI_COLUMNS + M.LEVERAGE_COLUMNS + [d for _, d in M.LIQDIR_SOURCE]:
        assert col in M.COLUMNS
    for col in BASE.COLUMNS:
        assert col in M.COLUMNS
