"""`scripts/o3c_reaction.py` の単体テスト(2026-09-18、L-197)。

設計 `docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md` §9 の「テストの案」9 件を
そのまま固定する。**合成データだけを使う。**相場についての判定は 1 つも書かない。

  1 到達の判定が**ちょうど位置に触れた**とき到達になる(境界)
  2 到達までの時間が、窓の中で最初に触れた時刻から出る(終値ではない)
  3 最大順行 / 逆行の符号が清算の side で反転する(SELL と BUY の同じ系列で)
  4 `after_shift` で窓の終点が `anchor_ts + h` になる(`end_ms + h` ではない)
  5 `doi_pre_*` / `doi_in` が起点より後の metrics 行を 1 つも読まない(先読み無し)
  6 対照 (ii) のマッチングが同日・±5 ポイント・置換なしで、作れない束を黙って落とさない
  7 mixed の束が主表から外れ、件数が `summary.json` に残る
  8 null の 1 分足(bitFlyer)が NaN になり、前値で埋まらない
  9 gap 30 / 60 / 180 秒で束の数が変わり、60 秒のとき ROWS4 の 22,036 と一致する

9 は実データ(`backtest_data/binance_cm_o3c_20260913`)が要るので、無ければ skip する。
それ以外は合成データだけで動く。
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import random
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


react = _load("o3c_reaction")

import o3c_oi_distance as oid  # noqa: E402
import o3c_price_level_table as base  # noqa: E402

from bot.research.liq_response import (  # noqa: E402
    Cascade,
    LiquidationEvent,
    PriceSeries,
    build_cascades,
    compute_reactions,
    load_binance_cm_liquidations_with_dedup_stats,
)


def _casc(cid: str, start: int, end: int, direction: str = "long") -> Cascade:
    return Cascade(
        cascade_id=cid,
        exchange=react.EXCHANGE,
        kind="real",
        start_ms=start,
        end_ms=end,
        n_events=1,
        total_size=1.0,
        direction=direction,
        first_price=100.0,
        last_price=100.0,
    )


# --------------------------------------------------------------------------- #
# 1 到達の境界(ちょうど触れたら到達)
# --------------------------------------------------------------------------- #


def test_first_touch_counts_exact_touch_upward():
    times = np.array([0, 1000, 2000, 3000], dtype=np.int64)
    prices = np.array([100.0, 100.5, 101.0, 100.2])
    # 目標 101.0 にちょうど触れる -> 2000ms で到達
    assert react.first_touch_ms(times, prices, 0, 4, 100.0, 101.0) == 2000.0
    # 目標が 1 ティック上 -> 到達しない
    assert np.isnan(react.first_touch_ms(times, prices, 0, 4, 100.0, 101.0001))


def test_first_touch_counts_exact_touch_downward():
    times = np.array([0, 1000, 2000], dtype=np.int64)
    prices = np.array([100.0, 99.5, 99.0])
    assert react.first_touch_ms(times, prices, 0, 3, 100.0, 99.0) == 2000.0
    assert np.isnan(react.first_touch_ms(times, prices, 0, 3, 100.0, 98.9999))


def test_first_touch_at_anchor_itself_is_a_touch():
    """目標 = 起点価格なら、起点の点そのものが到達になる(境界)。"""
    times = np.array([0, 1000], dtype=np.int64)
    prices = np.array([100.0, 99.0])
    assert react.first_touch_ms(times, prices, 0, 2, 100.0, 100.0) == 0.0


def test_first_touch_returns_nan_for_undefined_target():
    times = np.array([0, 1000], dtype=np.int64)
    prices = np.array([100.0, 99.0])
    assert np.isnan(react.first_touch_ms(times, prices, 0, 2, 100.0, float("nan")))
    assert np.isnan(react.first_touch_ms(times, prices, 1, 1, 100.0, 99.0))


# --------------------------------------------------------------------------- #
# 2 到達までの時間は「窓の中で最初に触れた時刻」から出る(終値ではない)
# --------------------------------------------------------------------------- #


def test_first_touch_uses_the_first_crossing_not_the_last_point():
    times = np.array([0, 60_000, 120_000, 180_000], dtype=np.int64)
    # 途中(60 秒)で 101 に触れ、最後は 99 に戻る。終値だけを見ると到達を落とす。
    prices = np.array([100.0, 101.0, 100.4, 99.0])
    assert react.first_touch_ms(times, prices, 0, 4, 100.0, 101.0) == 60_000.0
    assert prices[-1] < 101.0  # 終値は目標に届いていない


# --------------------------------------------------------------------------- #
# 3 最大順行 / 逆行の符号が side で反転する
# --------------------------------------------------------------------------- #


def test_react_sign_is_opposite_of_liq_sign():
    """値動きの符号 `REACT_SIGN` と距離の符号 `LIQ_SIGN` は逆である(別の列名にしてある)。"""
    for side in ("SELL", "BUY"):
        assert react.REACT_SIGN[side] == -oid.LIQ_SIGN[side]


def test_running_extremes_flip_with_side():
    prices = np.array([100.0, 102.0, 98.0, 101.0])
    rmax, rmin = react.running_extremes(prices, 0, 4)
    anchor = 100.0
    up = (rmax[-1] - anchor) / anchor * 1e4
    dn = (rmin[-1] - anchor) / anchor * 1e4
    sell = react.REACT_SIGN["SELL"]
    buy = react.REACT_SIGN["BUY"]
    mfe_sell, mae_sell = max(up * sell, dn * sell), min(up * sell, dn * sell)
    mfe_buy, mae_buy = max(up * buy, dn * buy), min(up * buy, dn * buy)
    # SELL(ロングの強制決済 = 下向きが順行)-> 順行は下の 98、逆行は上の 102
    assert mfe_sell == pytest.approx(-dn)
    assert mae_sell == pytest.approx(-up)
    # BUY はその逆
    assert mfe_buy == pytest.approx(up)
    assert mae_buy == pytest.approx(dn)
    assert mfe_sell == -mae_buy and mae_sell == -mfe_buy


def test_running_extremes_are_monotone():
    prices = np.array([100.0, 101.0, 99.0, 100.5])
    rmax, rmin = react.running_extremes(prices, 0, 4)
    assert rmax.tolist() == [100.0, 101.0, 101.0, 101.0]
    assert rmin.tolist() == [100.0, 100.0, 99.0, 99.0]


# --------------------------------------------------------------------------- #
# 4 `after_shift` の窓の終点は `anchor_ts + h`(`end_ms + h` ではない)
# --------------------------------------------------------------------------- #


def test_after_shift_window_end_follows_the_anchor():
    # 束の終わり 30_000ms。起点は at_or_after(30_000) = 60_000。
    # h = 1 分なら窓の終点は at_or_before(60_000 + 60_000) = 120_000。
    series = PriceSeries.from_trades(
        [(0, 100.0), (60_000, 110.0), (120_000, 121.0), (180_000, 130.0)]
    )
    rows = compute_reactions(
        [_casc("a", 30_000, 30_000)], series, horizons_min=(1,), anchor="after_shift"
    )
    r = rows[0]
    assert r["anchor_ts_ms"] == 60_000
    assert r["anchor_price"] == 110.0
    # 終点が anchor_ts + 60_000 = 120_000 の点(121.0)であること
    assert r["bp_1m"] == pytest.approx((121.0 - 110.0) / 110.0 * 1e4)
    # `end_ms + h` = 90_000 の点(110.0)を使っていたら 0 になる -> そうではない
    assert r["bp_1m"] != 0.0


def test_reaction_uses_after_shift_in_this_script():
    """段 A の走行が `after_shift` を使うこと(設計 §2.2)。"""
    src = (REPO / "scripts" / "o3c_reaction.py").read_text(encoding="utf-8")
    assert 'anchor="after_shift"' in src
    assert 'anchor="before"' in src  # 手順 1 の突き合わせ用にだけ出る


# --------------------------------------------------------------------------- #
# 5 `doi_pre_*` / `doi_in` が起点より後の metrics 行を読まない
# --------------------------------------------------------------------------- #


def test_window_sum_is_left_open_right_closed():
    t = np.array([100, 200, 300, 400], dtype=np.int64)
    d = np.array([1.0, 2.0, 4.0, 8.0])
    # (100, 300] -> 200 と 300 の 2 本
    assert react.window_sum(t, d, 100, 300) == (6.0, 2)
    # 上端ちょうどは入る / 下端ちょうどは入らない
    assert react.window_sum(t, d, 199, 200) == (2.0, 1)
    v0, n0 = react.window_sum(t, d, 200, 200)
    assert n0 == 0 and np.isnan(v0)


def test_doi_pre_and_in_read_nothing_after_the_anchor():
    """起点 = anchor_ts。pre / in の窓はどちらも anchor_ts 以下しか読まない。"""
    bucket = react.BUCKET_MS
    t = np.arange(10, dtype=np.int64) * bucket
    start_ms = int(t[5])
    end_ms = int(t[6])
    anchor_ts = end_ms + 1_000  # 起点は束の終わり以後
    for lo, hi in (
        (start_ms - 3_600_000, start_ms),
        (start_ms - 14_400_000, start_ms),
        (start_ms, end_ms),
    ):
        a = int(np.searchsorted(t, lo, side="right"))
        b = int(np.searchsorted(t, hi, side="right"))
        used = t[a:b]
        assert used.size == 0 or int(used.max()) <= anchor_ts
        assert used.size == 0 or int(used.max()) <= hi


def test_doi_in_is_nan_not_zero_for_zero_width_bundle():
    """幅 0 の束は桶が 0 個 -> NaN。**0 を入れて「変化なし」に見せない。**"""
    t = np.arange(5, dtype=np.int64) * react.BUCKET_MS
    d = np.array([1.0, -2.0, 3.0, -4.0, 5.0])
    start = end = int(t[2]) + 1234
    v, n = react.window_sum(t, d, start, end)
    assert n == 0 and np.isnan(v)


def test_all_deltas_matches_build_delta_buckets_on_positive_rows():
    """ΔOI の作り方(直前の行がちょうど 5 分前にある行だけ)が既存と同じであること。"""
    bucket = react.BUCKET_MS
    t = np.array([0, bucket, 2 * bucket, 4 * bucket, 5 * bucket], dtype=np.int64)
    oi = np.array([10.0, 12.0, 11.0, 30.0, 33.0])
    t_end, delta = react.all_deltas(t, oi)
    # 3 本目 (2b -> 4b) は 5 分ではないので作られない
    assert t_end.tolist() == [bucket, 2 * bucket, 5 * bucket]
    assert delta.tolist() == [2.0, -1.0, 3.0]
    lookup = {int(x) - bucket: (100.0, 0.5, 1.0, 1, 100.0, 100.0) for x in t_end}
    b = oid.build_delta_buckets([(t, oi)], lookup)
    assert b["t_all"].tolist() == t_end.tolist()
    assert b["t_ms"].tolist() == [int(x) for x, dd in zip(t_end, delta) if dd > 0]


# --------------------------------------------------------------------------- #
# 6 対照 (ii) のマッチング
# --------------------------------------------------------------------------- #


def test_matched_controls_respects_tolerance_and_no_replacement():
    rng = random.Random(0)
    liq = [10.0, 10.0, 90.0]
    cand_t = [1000, 2000, 3000]
    cand_v = [10.5, 12.0, 50.0]  # 90.0 に ±5 の候補が無い
    out, note = react.matched_controls(liq, cand_t, cand_v, rng, tol=5.0)
    assert out[0] == 1000            # 一番近い 10.5
    assert out[1] == 2000            # 置換なしなので次に近い 12.0
    assert out[2] is None            # ±5 に候補が無い -> 作らない
    assert note["bundles_without_candidate"] == 1
    assert note["candidates"] == 3
    assert note["match_tolerance_pct"] == 5.0


def test_matched_controls_does_not_drop_bundles_silently():
    """作れなかった束は None として返り、件数が残る(黙って落とさない)。"""
    rng = random.Random(1)
    liq = [1.0, 2.0, 3.0]
    out, note = react.matched_controls(liq, [], [], rng)
    assert out == [None, None, None]
    assert note["bundles_without_candidate"] == 3
    assert len(out) == len(liq)


def test_matched_controls_is_deterministic_for_the_same_seed():
    liq = [10.0]
    cand_t = [1000, 2000]
    cand_v = [12.0, 12.0]  # 同点
    a, _ = react.matched_controls(liq, cand_t, cand_v, random.Random(7))
    b, _ = react.matched_controls(liq, cand_t, cand_v, random.Random(7))
    assert a == b


def test_matched_candidates_are_at_least_five_minutes_from_any_liquidation():
    """候補の作り方(1 分刻み・清算から ±5 分以上)が既存の対照と同じ規則であること。"""
    day_start, day_end = base.day_bounds_ms("2024-01-01")
    liq_t = [day_start + 60 * 60 * 1000]
    iv = base.allowed_intervals(liq_t, day_start, day_end, react.CONTROL_GAP_MS)
    cand = []
    for a, b in iv:
        t = -(-a // react.MATCH_GRID_MS) * react.MATCH_GRID_MS
        while t < b:
            cand.append(t)
            t += react.MATCH_GRID_MS
    assert cand, "候補が 1 つも作れない"
    assert all(abs(t - liq_t[0]) >= react.CONTROL_GAP_MS for t in cand)
    assert all(t % react.MATCH_GRID_MS == 0 for t in cand)


# --------------------------------------------------------------------------- #
# 7 mixed の束が主表から外れ、件数が summary に残る
# --------------------------------------------------------------------------- #


def test_mixed_bundles_are_split_out_of_the_main_table():
    import pandas as pd

    rows = [{"kind": react.KIND_LIQ, "direction": "long", "cascade_id": "a"}]
    mixed = [{"kind": react.KIND_LIQ, "direction": "mixed", "cascade_id": "b"}]
    assert all(r["direction"] != "mixed" for r in rows)
    cols = react.sample_columns()
    df = pd.DataFrame(
        [{c: r.get(c, np.nan) for c in cols} for r in rows], columns=cols
    )

    class _DS:
        n_in, n_out = 2, 1

    s = react.build_table_summary(
        df,
        mixed,
        [],
        {},
        _DS(),
        0.0,
        {"mode": "sample", "horizons_min": list(react.HORIZONS_MIN)},
    )
    assert s["rows_mixed_excluded"] == 1
    assert s["mixed_cascade_ids"] == ["b"]
    assert s["rows_total"] == 1
    json.dumps(s, ensure_ascii=False)  # summary.json に書ける形であること


def test_matched_liq_id_is_the_last_column_and_only_matched_rows_carry_it():
    """合わせた対照 (ii) の 1 対 1 の相手を `matched_liq_id` 列で残す。

    **走行前の再監査(3 回目)の指摘 6 への処置**(2026-09-18)。
    読みの道具は `cascade_id` の連番の算術で相手を**復元**していて、相手が mixed 束の
    ときに静かに外れていた。列で持てば復元が要らない。

    測るもの:
      - 列は**並びの末尾**に足してある(既にある列の位置が 1 つも動かない)
      - 実データの標本 6 日で、合わせた対照の行だけが値を持ち、相手が同じ日で、
        `bin_pct` の差がマッチングの許容(±5.0 ポイント)以内である
    """
    import csv

    cols = react.sample_columns()
    assert cols[-1] == "matched_liq_id"
    assert cols.count("matched_liq_id") == 1
    # 末尾に足しただけ = それ以外の列の並びは前の版と同じ
    assert cols[:-1] == (
        react.BASE_COLUMNS
        + react.PROFILE_COLUMNS
        + oid.OI_COLUMNS
        + [dst for _, dst in oid.LIQDIR_SOURCE]
        + oid.LEVERAGE_COLUMNS
        + ["oi_covered"]
        + react.ANCHOR_COLUMNS
        + react.TARGET_PRICE_COLUMNS
        + react.horizon_columns()
        + react.DOI_COLUMNS
        + react.RATIO_OUT_COLUMNS
        + react.BF_COLUMNS
    )

    smp = REPO / "backtest_data" / "o3c_reaction_20260918_sample" / "gap60_w8"
    if not (smp / "table.csv").exists():
        pytest.skip("標本 6 日の出力が無い")
    rows = list(csv.DictReader((smp / "table.csv").open(encoding="utf-8", newline="")))
    mixed_p = smp / "table_mixed.csv"
    mixed = (
        list(csv.DictReader(mixed_p.open(encoding="utf-8", newline="")))
        if mixed_p.exists()
        else []
    )
    by_id = {r["cascade_id"]: r for r in rows if r["kind"] == react.KIND_LIQ}
    for r in mixed:
        by_id.setdefault(r["cascade_id"], r)

    n_mat = 0
    for r in rows + mixed:
        v = r.get("matched_liq_id") or ""
        if r["kind"] != react.KIND_MATCHED:
            assert v == "", (r["kind"], v)       # 束・一様対照・mixed は空
            continue
        n_mat += 1
        p = by_id.get(v)
        assert p is not None, v                  # 相手が実在する
        assert p["day"] == r["day"]              # 同じ日
        d = abs(float(p["bin_pct"]) - float(r["bin_pct"]))
        assert d <= react.MATCH_TOL_PCT + 1e-9, d
    assert n_mat == sum(1 for r in rows if r["kind"] == react.KIND_MATCHED) == 213


def test_direction_of_mixed_cascade_is_mixed():
    evs = [
        LiquidationEvent(react.EXCHANGE, 0, "long", 1.0, 100.0),
        LiquidationEvent(react.EXCHANGE, 1_000, "short", 1.0, 100.0),
    ]
    cs = build_cascades(evs, react.EXCHANGE, gap_ms=60_000)
    assert len(cs) == 1 and cs[0].direction == "mixed"
    assert react.SIDE_OF_DIRECTION.get("mixed", "") == ""
    assert react.REACT_SIGN.get("", 1.0) == 1.0  # side 無しは符号を掛けない


# --------------------------------------------------------------------------- #
# 8 null の 1 分足(bitFlyer)が NaN になり、前値で埋まらない
# --------------------------------------------------------------------------- #


def test_bitflyer_null_minute_stays_nan(tmp_path):
    csv = (
        "ts,open,high,low,close,volume\n"
        "2023-01-01T00:00:00+00:00,100,101,99,100.0,1\n"
        "2023-01-01T00:01:00+00:00,,,,,0\n"
        "2023-01-01T00:02:00+00:00,102,103,101,102.0,1\n"
    )
    with gzip.open(tmp_path / "candles_1m_2023.csv.gz", "wt") as fh:
        fh.write(csv)
    bf = react.load_bitflyer_minutes([2023], tmp_path)
    assert bf["t_ms"].size == 3
    assert np.isnan(bf["close"][1])
    # null の分をまたぐ読み方でも前値(100.0)で埋まらない
    t1 = int(bf["t_ms"][1])
    assert np.isnan(react.bf_close_at_or_before(bf, t1))
    assert react.bf_close_at_or_before(bf, t1 - 1) == 100.0
    assert react.bf_close_at_or_before(bf, int(bf["t_ms"][2])) == 102.0


def test_bitflyer_missing_year_is_recorded_not_silently_empty(tmp_path):
    bf = react.load_bitflyer_minutes([1999], tmp_path)
    assert bf["years_missing"] == [1999]
    assert bf["t_ms"].size == 0


def test_bitflyer_staleness_returns_nan_instead_of_an_old_bar(tmp_path):
    csv = (
        "ts,open,high,low,close,volume\n"
        "2023-01-01T00:00:00+00:00,100,101,99,100.0,1\n"
    )
    with gzip.open(tmp_path / "candles_1m_2023.csv.gz", "wt") as fh:
        fh.write(csv)
    bf = react.load_bitflyer_minutes([2023], tmp_path)
    t0 = int(bf["t_ms"][0])
    assert react.bf_close_at_or_before(bf, t0 + react.STALENESS_MS) == 100.0
    assert np.isnan(react.bf_close_at_or_before(bf, t0 + react.STALENESS_MS + 1))


# --------------------------------------------------------------------------- #
# 9 gap 30 / 60 / 180 秒で束の数が変わる(実データがあれば 60 秒 = 22,036)
# --------------------------------------------------------------------------- #


def test_gap_changes_the_number_of_bundles_synthetic():
    ts = [0, 45_000, 200_000]  # 45 秒 / 155 秒 の間隔
    evs = [LiquidationEvent(react.EXCHANGE, t, "long", 1.0, 100.0) for t in ts]
    n30 = len(build_cascades(evs, react.EXCHANGE, gap_ms=30_000))
    n60 = len(build_cascades(evs, react.EXCHANGE, gap_ms=60_000))
    n180 = len(build_cascades(evs, react.EXCHANGE, gap_ms=180_000))
    assert (n30, n60, n180) == (3, 2, 1)
    assert react.GAP_SEC_CHOICES == (30, 60, 180)


@pytest.mark.skipif(
    not (
        REPO
        / "backtest_data"
        / "binance_cm_o3c_20260913"
        / "liquidationSnapshot"
        / "BTCUSD_PERP"
    ).exists(),
    reason="実データ(binance_cm_o3c_20260913)が無い",
)
def test_gap60_reproduces_rows4_bundle_count():
    """一意化 + gap 60 秒で ROWS4 の 22,036 個(2026-09-17 実測)と一致すること。"""
    root = REPO / "backtest_data" / "binance_cm_o3c_20260913"
    events, stats = load_binance_cm_liquidations_with_dedup_stats(react.liq_dir(root))
    assert stats.n_in == 106_822 and stats.n_out == 53_398
    counts = {
        g: len(build_cascades(events, react.EXCHANGE, gap_ms=g * 1000))
        for g in react.GAP_SEC_CHOICES
    }
    assert counts[60] == 22_036
    assert counts[30] > counts[60] > counts[180]


# --------------------------------------------------------------------------- #
# 承認の関門(設計 §9 の機械。手順 3 を走らせないための門)
# --------------------------------------------------------------------------- #


def test_full_mode_requires_approval_flag():
    with pytest.raises(SystemExit):
        react.check_approval("full", None)


def test_full_mode_requires_an_existing_owner_log_line(tmp_path):
    """台帳の行の実在(関門の (c))。

    **prereg 監査(7 回目)の指摘 1 で、この関門に (a)(b)(d)(e) が足された。**
    この試験は (c) だけを見るので、他の 4 つは通る形で渡す
    (欄 = L-200 / 出力先 = まだ無い許された 1 つ)。
    """
    log = tmp_path / "OWNER_LOG.md"
    log.write_text("| L-200 | 2026-09-18 | 承認 |\n", encoding="utf-8")
    out = tmp_path / "gap60_w8"
    kw = dict(out_dir=out, prereg=_prereg(tmp_path, "L-200"),
              allowed_out_dirs=(out,))
    react.check_approval("full", "L-200", log, **kw)  # 実在するので通る
    with pytest.raises(SystemExit):
        react.check_approval("full", "L-999", log,
                             out_dir=out, prereg=_prereg(tmp_path, "L-999"),
                             allowed_out_dirs=(out,))
    with pytest.raises(SystemExit):
        react.check_approval("full", "not-a-number", log, **kw)


def test_sample_and_anchor_modes_do_not_need_approval(tmp_path):
    """標本 6 日だけの `--mode sample` と `--mode anchor` は無審査で通る。

    **prereg 監査(8 回目)の指摘 1 で、判定区間の日を含む非 full の経路は
    `--approval` があっても止まる形になった**(下の試験)。
    **この試験は「判定区間の日を 1 日も含まない」側だけを見る**ので、
    在庫の無い一時ディレクトリを `data_root` に渡す(= 判定区間の日は 0 日)。
    """
    react.check_approval("sample", None, data_root=tmp_path)
    react.check_approval("sample", None, days=list(react.SAMPLE_DAYS),
                         data_root=tmp_path)
    react.check_approval("anchor", None, data_root=tmp_path)
    # 実在の在庫でも、日を標本 6 日に切れば通る(`--mode anchor` の手順 1 の形)。
    react.check_approval("anchor", None, days=list(react.SAMPLE_DAYS))


# --------------------------------------------------------------------------- #
# 承認の関門の穴(2026-09-18 の監査の指摘 3・4。リードの決定 3・4)
# --------------------------------------------------------------------------- #


def test_sample_mode_rejects_days_outside_the_sample_without_approval():
    """`--mode sample --days <判定区間の日>` は `--approval` 無しでは止まる。

    2026-09-18 の監査の指摘 3: 前版は `mode != "full"` で即 return していたので、
    2024-02-15〜26 の 12 日(= 標本 6 日ではない)が無審査で走っていた。
    """
    with pytest.raises(SystemExit):
        react.check_approval("sample", None, days=["2024-02-15"])
    with pytest.raises(SystemExit):
        # 標本 6 日に 1 日でも外の日が混ざれば止まる。
        react.check_approval(
            "sample", None, days=list(react.SAMPLE_DAYS) + ["2024-02-26"]
        )


def test_sample_mode_outside_days_need_a_real_owner_log_line(tmp_path):
    log = tmp_path / "OWNER_LOG.md"
    log.write_text("| L-197 | 2026-09-18 | 承認 |\n", encoding="utf-8")
    react.check_approval("sample", "L-197", log, days=["2024-02-15"])  # 通る
    with pytest.raises(SystemExit):
        react.check_approval("sample", "L-999", log, days=["2024-02-15"])


def test_judgment_days_excludes_the_sample_days(monkeypatch):
    """`--mode full` が走る範囲 = 全日 − 標本 6 日(指摘 4)。"""
    fake = ["2023-06-24"] + list(react.SAMPLE_DAYS) + ["2024-10-15"]
    monkeypatch.setattr(react, "all_days", lambda root: list(fake))
    got = react.judgment_days(Path("."))
    assert got == ["2023-06-24", "2024-10-15"]
    assert not (set(got) & set(react.SAMPLE_DAYS))
    assert len(got) == len(fake) - len(react.SAMPLE_DAYS)


# --------------------------------------------------------------------------- #
# 12 日走行で開いた 10 日を判定区間から外す
# (2026-09-18 の監査の指摘 2・14 / 返答 060 の #1。a・b に共通の作業)
# --------------------------------------------------------------------------- #


def test_scale12_opened_days_are_the_ten_outside_the_sample():
    """定数の中身。12 日走行 2024-02-15〜26 から標本 6 日の 2 日を除いた 10 日。"""
    assert react.SCALE12_JUDGMENT_DAYS_OPENED == (
        "2024-02-15",
        "2024-02-16",
        "2024-02-17",
        "2024-02-18",
        "2024-02-21",
        "2024-02-22",
        "2024-02-23",
        "2024-02-24",
        "2024-02-25",
        "2024-02-26",
    )
    assert len(react.SCALE12_JUDGMENT_DAYS_OPENED) == 10
    # 標本 6 日(2024-02-19 / 20)とは重ならない。合わせて 12 日走行の 12 日になる。
    assert not (set(react.SCALE12_JUDGMENT_DAYS_OPENED) & set(react.SAMPLE_DAYS))
    twelve = set(react.SCALE12_JUDGMENT_DAYS_OPENED) | {"2024-02-19", "2024-02-20"}
    assert twelve == {f"2024-02-{d:02d}" for d in range(15, 27)}


def test_judgment_days_excludes_the_scale12_days_too(monkeypatch):
    """合成の日付一覧で、標本 6 日と 10 日の両方が外れること(日付で測る)。"""
    fake = (
        ["2023-06-24"]
        + list(react.SAMPLE_DAYS)
        + list(react.SCALE12_JUDGMENT_DAYS_OPENED)
        + ["2024-10-15"]
    )
    monkeypatch.setattr(react, "all_days", lambda root: list(fake))
    got = react.judgment_days(Path("."))
    assert got == ["2023-06-24", "2024-10-15"]
    assert len(got) == len(fake) - 6 - 10


@pytest.mark.skipif(
    not (
        REPO
        / "backtest_data"
        / "binance_cm_o3c_20260913"
        / "liquidationSnapshot"
        / "BTCUSD_PERP"
    ).exists(),
    reason="実データ(binance_cm_o3c_20260913)が無い",
)
def test_judgment_days_on_the_real_inventory_is_456_days():
    """実物の在庫で **472 − 6 − 10 = 456 日**になること。日数と日付の両方で測る。

    日付の一覧は `backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP/`
    の zip のファイル名から取る(`react.all_days`)。
    """
    root = REPO / "backtest_data" / "binance_cm_o3c_20260913"
    days = react.all_days(root)
    assert len(days) == 472
    assert len(set(days)) == 472          # 重複が無い
    # 外す 16 日が全部在庫にあること(名前の書き間違いをここで捕まえる)。
    for d in react.SAMPLE_DAYS:
        assert d in days
    for d in react.SCALE12_JUDGMENT_DAYS_OPENED:
        assert d in days

    got = react.judgment_days(root)
    assert len(got) == 456
    assert len(got) == 472 - 6 - 10
    # 日付で: 外した 16 日が 1 日も残っていない。
    assert not (set(got) & set(react.SAMPLE_DAYS))
    assert not (set(got) & set(react.SCALE12_JUDGMENT_DAYS_OPENED))
    # 2024-02-15〜26 の 12 日は 1 日も残らない(標本 2 日 + 開いた 10 日)。
    assert not (set(got) & {f"2024-02-{d:02d}" for d in range(15, 27)})
    # 残りは元の順序のまま、外した 16 日を引いた集合と一致する。
    assert got == [
        d
        for d in days
        if d not in set(react.SAMPLE_DAYS) | set(react.SCALE12_JUDGMENT_DAYS_OPENED)
    ]
    # 隣の日(2024-02-14 / 2024-02-27)は残っている = 外し過ぎていない。
    assert "2024-02-14" in got and "2024-02-27" in got


# --------------------------------------------------------------------------- #
# 生の主観測量を判定区間の日で出さない(指摘 2。リードの決定 2・3)
# --------------------------------------------------------------------------- #


def test_emit_raw_bp_only_inside_the_sample_days():
    assert react.emit_raw_bp(list(react.SAMPLE_DAYS)) is True
    assert react.emit_raw_bp([react.SAMPLE_DAYS[0]]) is True
    assert react.emit_raw_bp(None) is False          # 全日
    assert react.emit_raw_bp(["2024-02-15"]) is False
    assert react.emit_raw_bp(list(react.SAMPLE_DAYS) + ["2024-02-15"]) is False


def test_anchor_table_has_no_raw_bp_columns_outside_the_sample():
    cols = react.anchor_table_columns(emit_raw=False)
    for h in react.HORIZONS_MIN:
        assert f"bp_{h}m_diff" in cols            # 差だけは出す
        assert f"bp_{h}m_after_shift" not in cols
        assert f"bp_{h}m_before" not in cols
        assert f"pred_under_{h}m" not in cols     # before の線形変換なので落とす
        assert f"resid_{h}m" not in cols
    # 生の列が 1 つも残っていないこと(列名の集合で確かめる)。
    assert not (set(cols) & set(react.ANCHOR_RAW_COLUMNS))


def test_anchor_table_keeps_raw_bp_columns_inside_the_sample():
    cols = react.anchor_table_columns(emit_raw=True)
    for h in react.HORIZONS_MIN:
        assert f"bp_{h}m_after_shift" in cols
        assert f"bp_{h}m_before" in cols
        assert f"pred_under_{h}m" in cols
        assert f"resid_{h}m" in cols


def test_anchor_output_written_for_judgment_days_has_no_raw_columns(tmp_path):
    """`_finish_anchor` を通した実際の CSV / summary に生の列が無いこと。"""
    import pandas as pd

    rows = []
    for i in range(4):
        r = {c: 0 for c in react.ANCHOR_BASE_COLUMNS}
        r["cascade_id"] = f"c{i}"
        r["day"] = "2024-02-15"
        r["direction"] = "long"
        r["tie_after_shift"] = i % 2 == 0
        r["tie_before"] = i < 2
        r["anchor_lag_ms"] = 1000.0 * i
        r["anchor_price_diff_bp"] = 0.1 * i
        for h in react.HORIZONS_MIN:
            r[f"bp_{h}m_diff"] = 0.5 * i
        rows.append(r)
    df = pd.DataFrame(rows, columns=react.anchor_table_columns(False))

    class _S:
        n_in, n_out, n_dropped = 8, 4, 4

    s = react._finish_anchor(
        df, tmp_path, 60_000, ["2024-02-15"], "bar60", False, _S(), tmp_path, 0.0, 0, []
    )
    head = (tmp_path / "table.csv").read_text(encoding="utf-8").splitlines()[0]
    for h in react.HORIZONS_MIN:
        assert f"bp_{h}m_after_shift" not in head
        assert f"bp_{h}m_before" not in head
    assert s["params"]["raw_bp_columns_emitted"] is False
    body = json.dumps(s, ensure_ascii=False)
    assert "after_shift\": {\"q5" not in body  # 参考表(生の分位)が無い
    # 2x2 が出ている(指摘 1)。
    ct = s["tie_counts"]["crosstab_after_shift_x_before"]
    assert ct["both_non_tie"] == 1
    assert ct["after_shift_non_tie_but_before_tie"] == 1
    assert ct["both_tie"] == 1
    assert s["diff_quantiles"]["h1m"]["non_tie_both"]["diff"]["n"] == 1


# --------------------------------------------------------------------------- #
# 対照 (ii) の順序依存(指摘 21)
# --------------------------------------------------------------------------- #


def test_matched_controls_is_order_dependent_in_who_gets_no_candidate():
    """貪欲・置換なしなので、束の順で「候補なし」になる束が入れ替わりうる。

    候補が 1 点しかなく、2 つの束がどちらも許容幅の中にいる合成例。
    先に見た方が候補を取り、後の方が「候補なし」になる。
    """
    cand_times = [60_000]
    cand_bp = [10.0]
    liq = [8.0, 12.0]
    a, _ = react.matched_controls(liq, cand_times, cand_bp, random.Random("x"))
    b, _ = react.matched_controls(liq[::-1], cand_times, cand_bp, random.Random("x"))
    assert [t is None for t in a] == [False, True]
    assert [t is None for t in b] == [False, True]
    # 逆順で「候補なし」になった束は、元の並びでは 0 番目(= 入れ替わっている)。
    assert a.index(None) != b[::-1].index(None)


def test_approval_line_must_be_at_the_start_of_the_line(tmp_path):
    log = tmp_path / "OWNER_LOG.md"
    log.write_text("本文の途中に | L-197 | と書いてあるだけ\n", encoding="utf-8")
    assert react.approval_line_exists("L-197", log) is False


def test_approval_missing_file_is_not_an_approval(tmp_path):
    assert react.approval_line_exists("L-197", tmp_path / "no_such.md") is False


# --------------------------------------------------------------------------- #
# 定義を変えていないこと(O-7)
# --------------------------------------------------------------------------- #


def test_node_definition_matches_profile_stats():
    """方向つきノードの選び方が `base.profile_stats` のノードと同じ集合から出ること。"""
    rng = np.random.default_rng(0)
    step = base.log_step(0.1)
    for _ in range(20):
        n = int(rng.integers(5, 60))
        qty = rng.random(n) * 10
        lo_bin = base.bin_index(30_000.0, step)
        centers = base.bin_center_price(np.arange(lo_bin, lo_bin + n), step)
        p_liq = float(centers[n // 2])
        st = base.profile_stats(qty, lo_bin, step, p_liq, p_liq)
        up = react.directional_node_bp(qty, lo_bin, step, p_liq, +1.0)
        dn = react.directional_node_bp(qty, lo_bin, step, p_liq, -1.0)
        cands = [v for v in (up, dn) if np.isfinite(v)]
        if not cands:
            continue
        nearest = min(cands, key=abs)
        # `profile_stats` は p_liq のビンそのもの(距離 ~0)も候補にするので、
        # 方向つきの最小より近いか同じになる。
        assert abs(st["dist_node_bp"]) <= abs(nearest) + 1e-6
        assert up != up or up > 0  # NaN でなければ必ず正
        assert dn != dn or dn < 0  # NaN でなければ必ず負


def test_directional_node_is_nan_when_no_node_on_that_side():
    step = base.log_step(0.1)
    lo_bin = base.bin_index(30_000.0, step)
    qty = np.array([0.0, 0.0, 10.0])  # ノードは最後のビンだけ
    centers = base.bin_center_price(np.arange(lo_bin, lo_bin + 3), step)
    p_ref = float(centers[2])  # ノードそのものの位置 -> 上にも下にも無い
    assert np.isnan(react.directional_node_bp(qty, lo_bin, step, p_ref, +1.0))
    assert np.isnan(react.directional_node_bp(qty, lo_bin, step, p_ref, -1.0))
    p_low = float(centers[0])
    assert react.directional_node_bp(qty, lo_bin, step, p_low, +1.0) > 0
    assert np.isnan(react.directional_node_bp(qty, lo_bin, step, p_low, -1.0))


def test_profile_columns_match_base_profile_stats_on_a_hand_window():
    """`profile_columns` の窓 [t-W, t) と列が `base.profile_stats` と一致すること。"""
    step = base.log_step(0.1)
    times = np.array([0, 1000, 2000, 3000, 4000], dtype=np.int64)
    prices = np.array([30000.0, 30030.0, 30060.0, 30090.0, 30120.0])
    qtys = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    t = 4000
    window_ms = 4000  # [0, 4000) -> 先頭 4 本
    ev = [{"profile_ts_ms": t, "p_liq": 30060.0}]
    cols, note = react.profile_columns(ev, times, prices, qtys, window_ms, step)
    sel = (times >= t - window_ms) & (times < t)
    bins = base.bin_index_array(prices[sel], step)
    lo_bin = int(bins.min())
    acc = np.zeros(int(bins.max()) - lo_bin + 1)
    for b, q in zip(bins, qtys[sel]):
        acc[b - lo_bin] += q
    st = base.profile_stats(acc, lo_bin, step, 30060.0, float(prices[sel][-1]))
    assert cols[0]["bin_pct"] == pytest.approx(round(st["bin_pct"], 4))
    assert cols[0]["dist_node_bp"] == pytest.approx(round(st["dist_node_bp"], 4))
    assert cols[0]["dist_vwap_bp"] == pytest.approx(round(st["dist_vwap_bp"], 4))
    assert cols[0]["n_bins"] == st["n_bins"]
    assert note["rows_skipped_empty_window"] == 0
    assert cols[0]["p0"] == float(prices[sel][-1])


def test_profile_columns_keep_rows_with_empty_window():
    """窓に約定が 1 件も無い行も落とさず、NaN で残す(行を落とさない)。"""
    step = base.log_step(0.1)
    times = np.array([10_000], dtype=np.int64)
    prices = np.array([30000.0])
    qtys = np.array([1.0])
    ev = [{"profile_ts_ms": 5_000, "p_liq": None}]
    cols, note = react.profile_columns(ev, times, prices, qtys, 1_000, step)
    assert len(cols) == 1
    assert np.isnan(cols[0]["bin_pct"])
    assert note["rows_skipped_empty_window"] == 1


def test_cascade_event_segments_line_up_with_build_cascades():
    evs = [
        LiquidationEvent(react.EXCHANGE, t, "long", 1.0, 100.0)
        for t in (0, 10_000, 200_000, 210_000, 500_000)
    ]
    cs = build_cascades(evs, react.EXCHANGE, gap_ms=60_000)
    segs = react.cascade_event_segments(evs, cs)
    assert [len(s) for s in segs] == [c.n_events for c in cs]
    assert sum(len(s) for s in segs) == len(evs)
    for c, seg in zip(cs, segs):
        assert seg[0].ts_ms == c.start_ms and seg[-1].ts_ms == c.end_ms


def test_minute_close_takes_the_last_trade_of_each_minute():
    times = np.array([0, 30_000, 59_999, 60_000, 120_000], dtype=np.int64)
    prices = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    out = react.minute_close(times, prices, 0, 3)
    assert out.tolist() == [3.0, 4.0, 5.0]
    # 約定の無い分は NaN(前値で埋めない)
    out2 = react.minute_close(times, prices, 0, 5)
    assert np.isnan(out2[3]) and np.isnan(out2[4])


def test_horizons_are_the_six_in_the_design():
    assert react.HORIZONS_MIN == (1, 5, 15, 30, 60, 240)
    assert react.SAMPLE_DAYS == (
        "2023-06-25",
        "2023-06-26",
        "2024-02-19",
        "2024-02-20",
        "2024-10-13",
        "2024-10-14",
    )


def test_xcorr_best_lag_finds_a_shifted_series():
    rng = np.random.default_rng(3)
    a = rng.normal(size=60)
    b = np.full(60, np.nan)
    b[3:] = a[:-3]  # bitFlyer が 3 分遅れる
    lag, r, n = react.xcorr_best_lag(a, b, 10, 5)
    assert lag == 3.0
    assert r > 0.99 and n >= 5


def test_run_summary_records_the_approval_number_passed_to_the_run():
    """走行に渡した --approval の番号が summary.json の params に残る
    (prereg 監査(6 回目)の指摘 2。読みの側が事前登録 §14.4 の欄と突き合わせる)。
    標本の走行は承認なしなので None が入る。鍵が無ければ読みの側の突き合わせが成り立たない。"""
    import json
    from pathlib import Path

    p = Path(__file__).resolve().parents[1] / "backtest_data" / "o3c_reaction_20260918_sample" / "gap60_w8" / "summary.json"
    if not p.exists():
        pytest.skip("標本の走行の出力が無い")
    params = json.loads(p.read_text(encoding="utf-8"))["params"]
    assert "approval" in params
    assert params["approval"] is None


# --------------------------------------------------------------------------- #
# 開封前の関門(prereg 監査(7 回目)の指摘 1・18・20。リードの決定 1・18・20)
#
# **前版の `--mode full` の関門は「`docs/OWNER_LOG.md` に行頭 `| L-NNN |` の行が
# 実在するか」しか見ていなかった**ので、**間違った(あるいは古い)L 番号のまま
# 456 日を 6 回開け終わるまで何も止まらなかった。**
# **通る側と止まる側の両方を測る。迂回する旗は作っていない。**
# --------------------------------------------------------------------------- #


def _prereg(tmp_path, value: str):
    # **欄の値ごとに別のファイルにする**(同じ名前だと後から書いた値で上書きされ、
    # 「止まる側」の試験が黙って通ってしまう)。
    p = tmp_path / f"PREREG_{abs(hash(value))}.md"
    p.write_text(
        "本文\n\n   **応答の L 番号**: **" + value + "**\n\n本文\n", encoding="utf-8"
    )
    return p


def _owner_log(tmp_path, *numbers: str):
    p = tmp_path / "OWNER_LOG.md"
    p.write_text(
        "".join(f"| {n} | 2026-09-18 | 応答 |\n" for n in numbers), encoding="utf-8"
    )
    return p


def test_full_mode_gate_passes_when_all_five_checks_are_met(tmp_path):
    """通る側: 欄と一致 / L-199 より後 / 台帳に実在 / 出力先が 6 つの 1 つ / まだ無い。"""
    out = tmp_path / "gap60_w8"          # 許す一覧は下で差し替える(試験用の既定引数)
    react.check_approval(
        "full", "L-200",
        owner_log=_owner_log(tmp_path, "L-200"),
        out_dir=out,
        prereg=_prereg(tmp_path, "L-200"),
        allowed_out_dirs=(out,),
    )


def test_full_mode_gate_stops_on_each_of_the_five_checks(tmp_path):
    """止まる側: (a) 欄が空 / 番号違い、(b) L-199 以下、(c) 台帳に無い、
    (d) 出力先が 6 つに無い、(e) 出力先が既に在る。**5 つを 1 つずつ崩す。**"""
    out = tmp_path / "gap60_w8"
    log = _owner_log(tmp_path, "L-199", "L-200", "L-201")

    def call(**kw):
        args = dict(approval="L-200", owner_log=log, out_dir=out,
                    prereg=_prereg(tmp_path, "L-200"), allowed_out_dirs=(out,))
        args.update(kw)
        react.check_approval("full", args.pop("approval"), **args)

    # (a-1) 欄が「(まだ無い)」
    with pytest.raises(SystemExit):
        call(prereg=_prereg(tmp_path, "(まだ無い。オーナーの応答を待っている。)"))
    # (a-2) 欄と --approval が違う
    with pytest.raises(SystemExit):
        call(approval="L-201")
    # (b) L-199 は「1 = a、9 = a」への応答であって、報告 062 への応答ではない
    with pytest.raises(SystemExit):
        call(approval="L-199", prereg=_prereg(tmp_path, "L-199"))
    # (c) 台帳にその行が無い
    with pytest.raises(SystemExit):
        call(approval="L-777", prereg=_prereg(tmp_path, "L-777"))
    # (d) 出力先が事前登録の 6 つに無い
    with pytest.raises(SystemExit):
        call(out_dir=tmp_path / "どこか別の場所")
    # (e) 出力先が既に在る(再走行・上書きをここで止める)
    out.mkdir()
    with pytest.raises(SystemExit):
        call()
    # (f) 出力先が渡っていない
    with pytest.raises(SystemExit):
        call(out_dir=None)


def test_full_mode_gate_has_no_bypass_flag_and_is_wired_into_main():
    """迂回する旗を作っていないこと、`main()` が `--out-dir` を関門に渡していること。"""
    text = (REPO / "scripts" / "o3c_reaction.py").read_text(encoding="utf-8")
    for flag in ("--force", "--skip-approval", "--allow-reopen", "--no-gate"):
        assert flag not in text, flag
    assert ("check_approval(a.mode, a.approval, days=days, out_dir=out_dir,\n"
            "                   data_root=root, days_given=bool(a.days))") in text
    # 許す出力先は事前登録 §14.1・§14.2 の 6 つである
    assert len(react.FULL_OUT_DIRS_REL) == 6
    assert all(p.startswith("backtest_data/o3c_reaction_20260918_full/")
               for p in react.FULL_OUT_DIRS_REL)


def test_the_approval_field_is_read_from_the_real_prereg():
    """既定の読み先が事前登録そのものであること(欄はまだ埋まっていない = 走らせない)。"""
    assert react.PREREG.exists()
    value, note = react.read_approval_from_prereg()
    assert value is None, "事前登録 §14.4 の欄が埋まっている(開封の前に読む欄である)"
    assert "応答の L 番号" in note or "埋まっていない" in note


def test_run_table_records_the_real_approval_number(tmp_path):
    """**決定 3(7 回目の指摘 3)**: `--mode full --approval L-NNN` で L 番号が
    `summary.json` の `params` に書かれる経路を測る。

    **前版の試験は標本の出力を読んで `params["approval"] is None` を測るだけで、
    実際の L 番号が書かれる経路は 1 度も測られていなかった**(指摘 3)。
    **判定区間は開けない**: `run_table` を**標本 6 日のうち 1 日**で直接呼ぶ
    (`check_approval` を通る経路ではないので、承認の関門は当たらない)。
    """
    out = tmp_path / "out"
    s = react.run_table(
        "sample",
        [react.SAMPLE_DAYS[0]],
        base.DEFAULT_DATA_ROOT,
        oid.DEFAULT_METRICS_ROOT,
        out,
        8.0,
        0.1,
        60_000,
        1,
        0.004,
        "table",
        approval="L-999",
    )
    assert s["params"]["approval"] == "L-999"
    written = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert written["params"]["approval"] == "L-999"


# --------------------------------------------------------------------------- #
# prereg 監査(8 回目)の指摘 1・2・6・16。リードの決定 1・2・6・16。
# **通る側と止まる側の両方を測る。迂回する旗は作っていない。**
# --------------------------------------------------------------------------- #


def _inventory(tmp_path, days):
    """在庫の形だけを作る(`all_days` が読む zip の名前だけ。中身は空)。"""
    d = tmp_path / "inv" / "liquidationSnapshot" / base.SYMBOL
    d.mkdir(parents=True, exist_ok=True)
    for day in days:
        (d / f"{base.SYMBOL}-liquidationSnapshot-{day}.zip").write_bytes(b"")
    return tmp_path / "inv"


def test_judgment_day_set_is_the_inventory_minus_the_opened_days(tmp_path):
    """**決定 1**: 判定区間の日の集合 = 在庫 − 標本 6 日 − 12 日走行の 10 日。"""
    days = (["2023-06-24", "2024-10-15"] + list(react.SAMPLE_DAYS)
            + list(react.SCALE12_JUDGMENT_DAYS_OPENED))
    root = _inventory(tmp_path, days)
    assert react.judgment_day_set(root) == frozenset({"2023-06-24", "2024-10-15"})
    # 在庫が無ければ空集合(この関門は何も止めない = 射程として関数の注に書いた)
    assert react.judgment_day_set(tmp_path / "無い") == frozenset()


def test_the_judgment_days_cannot_be_opened_outside_full_mode(tmp_path):
    """**決定 1(8 回目の指摘 1)**: `--mode sample --days` と `--mode anchor` は、
    判定区間の日を 1 日でも含めば **`--approval` があっても**止まる。

    **前版は (c)「台帳に行頭 `| L-NNN |` がある」だけで通っていた**(指摘 1)。
    """
    root = _inventory(tmp_path, ["2023-06-24", "2024-10-15", *react.SAMPLE_DAYS,
                                 *react.SCALE12_JUDGMENT_DAYS_OPENED])
    log = _owner_log(tmp_path, "L-200")
    # 通る側: 標本 6 日だけの sample / 標本 6 日に切った anchor
    react.check_approval("sample", None, log, days=list(react.SAMPLE_DAYS),
                         data_root=root)
    react.check_approval("anchor", None, log, days=list(react.SAMPLE_DAYS),
                         data_root=root)
    # 通る側: 12 日走行で既に開いた 10 日は判定区間ではない(承認は要る = 従来どおり)
    react.check_approval("sample", "L-200", log, days=["2024-02-15"], data_root=root)
    # 止まる側 1: sample に判定区間の日が 1 日混ざる(承認があっても止まる)
    with pytest.raises(SystemExit) as e:
        react.check_approval("sample", "L-200", log,
                             days=list(react.SAMPLE_DAYS) + ["2023-06-24"],
                             data_root=root)
    assert "判定区間の日を開けない" in str(e.value)
    # 止まる側 2: anchor に判定区間の日が混ざる
    with pytest.raises(SystemExit):
        react.check_approval("anchor", "L-200", log, days=["2024-10-15"],
                             data_root=root)
    # 止まる側 3: anchor で `--days` を渡さない = 在庫の全日を読む
    with pytest.raises(SystemExit) as e:
        react.check_approval("anchor", "L-200", log, days=None, data_root=root)
    assert "判定区間の日を開けない" in str(e.value)


def test_full_mode_does_not_take_a_days_flag(tmp_path):
    """**決定 6(8 回目の指摘 6)**: `--mode full` に `--days` は渡せない。

    **前版の `main()` は `if a.days:` を先に見ていたので、`--mode full --days <任意>` が
    (a)〜(e) を全部通り、6 つの出力先の 1 つを 456 日以外の日で消費できた。**
    """
    out = tmp_path / "gap60_w8"
    kw = dict(owner_log=_owner_log(tmp_path, "L-200"), out_dir=out,
              prereg=_prereg(tmp_path, "L-200"), allowed_out_dirs=(out,),
              ledger=tmp_path / "OPENED.txt")
    react.check_approval("full", "L-200", **kw)            # 通る(days_given 既定 False)
    with pytest.raises(SystemExit) as e:
        react.check_approval("full", "L-200", days_given=True, **kw)
    assert "--days は渡せない" in str(e.value)
    # `main()` は --mode full では --days を見ずに judgment_days に固定している
    text = (REPO / "scripts" / "o3c_reaction.py").read_text(encoding="utf-8")
    assert "days_given=bool(a.days)" in text
    assert 'if a.mode == "full":\n        days = judgment_days(root)' in text


def test_the_opened_ledger_stops_a_rerun_after_deleting_the_output(tmp_path):
    """**決定 2(8 回目の指摘 2)**: 出力先を消してからの再走行も止まる。

    (e) は「出力先が既に在るとき」しか止めない。**台帳 `OPENED.txt` は出力先の有無を
    見ないので、消してから走らせ直しても (g) で止まる。**
    """
    out = tmp_path / "gap60_w8"
    ledger = tmp_path / "OPENED.txt"
    kw = dict(owner_log=_owner_log(tmp_path, "L-200"), out_dir=out,
              prereg=_prereg(tmp_path, "L-200"), allowed_out_dirs=(out,),
              ledger=ledger)
    react.check_approval("full", "L-200", **kw)             # 1 本目は通る
    react.record_opened(out, "L-200", ledger)               # 走行の側が追記する
    assert ledger.exists() and str(out.resolve()) in ledger.read_text(encoding="utf-8")
    # 出力先を作らずに(= 消した状態で)もう一度呼ぶ -> 台帳で止まる
    assert not out.exists()
    with pytest.raises(SystemExit) as e:
        react.check_approval("full", "L-200", **kw)
    assert "OPENED.txt" in str(e.value) and "[止め]" in str(e.value)
    # 台帳に載っていない別の出力先は止まらない
    other = tmp_path / "gap60_w24"
    react.check_approval("full", "L-200", owner_log=_owner_log(tmp_path, "L-200"),
                         out_dir=other, prereg=_prereg(tmp_path, "L-200"),
                         allowed_out_dirs=(other,), ledger=ledger)


def test_the_opened_ledger_records_out_dir_time_and_approval(tmp_path):
    """**決定 2**: 台帳の 1 行は「出力先・UTC 時刻・approval」である。"""
    ledger = tmp_path / "OPENED.txt"
    react.record_opened(tmp_path / "gap30_w8", "L-200", ledger)
    react.record_opened(tmp_path / "gap180_w8", "L-200", ledger)
    body = ledger.read_text(encoding="utf-8")
    rows = [r for r in body.splitlines() if r and not r.startswith("#")]
    assert len(rows) == 2
    for r in rows:
        m = react.OPENED_LINE_RE.match(r)
        assert m is not None, r
        assert m.group("approval") == "L-200"
        assert m.group("utc").endswith("Z")
    assert react.opened_out_dirs(ledger) == {
        str((tmp_path / "gap30_w8").resolve()),
        str((tmp_path / "gap180_w8").resolve()),
    }
    # `main()` は関門を通った直後に(出力を書く前に)追記する
    text = (REPO / "scripts" / "o3c_reaction.py").read_text(encoding="utf-8")
    assert "record_opened(out_dir, a.approval)" in text
    assert text.index("record_opened(out_dir, a.approval)") < text.index("s = run_table(")


def test_the_opened_ledger_is_tracked_by_git():
    """**決定 2**: 台帳は git で追跡する(`.gitignore` の除外が掛かっていない)。"""
    import subprocess
    rel = "backtest_data/o3c_reaction_20260918_full/OPENED.txt"
    r = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", rel],
                       capture_output=True)
    assert r.returncode == 1, f"{rel} が .gitignore で除外されている"
    assert react.FULL_OPENED_LEDGER == REPO / rel


def test_the_run_records_its_own_commit(tmp_path):
    """**決定 16(8 回目の指摘 16)**: 走行の出力に `tool_commit` を残す。"""
    got = react.tool_commit()
    assert got == "不明" or len(got) == 40
    # git の無い場所を指せば「不明」になる(断定しないための逃げ道を機械で持つ)
    assert react.tool_commit(tmp_path) in ("不明", got)
    s = react.run_table(
        "sample", [react.SAMPLE_DAYS[0]], base.DEFAULT_DATA_ROOT,
        oid.DEFAULT_METRICS_ROOT, tmp_path / "out", 8.0, 0.1, 60_000, 1, 0.004,
        "table", approval=None,
    )
    assert s["tool_commit"] == got
    written = json.loads((tmp_path / "out" / "summary.json").read_text(encoding="utf-8"))
    assert written["tool_commit"] == got
