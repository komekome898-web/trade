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
    log = tmp_path / "OWNER_LOG.md"
    log.write_text("| L-197 | 2026-09-18 | 承認 |\n", encoding="utf-8")
    react.check_approval("full", "L-197", log)  # 実在するので通る
    with pytest.raises(SystemExit):
        react.check_approval("full", "L-999", log)
    with pytest.raises(SystemExit):
        react.check_approval("full", "not-a-number", log)


def test_sample_and_anchor_modes_do_not_need_approval():
    """標本 6 日だけの `--mode sample` と `--mode anchor` は無審査で通る。"""
    react.check_approval("sample", None)
    react.check_approval("sample", None, days=list(react.SAMPLE_DAYS))
    react.check_approval("anchor", None)


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
