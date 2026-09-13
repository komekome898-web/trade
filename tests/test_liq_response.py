"""清算→価格反応の測定器(`bot.research.liq_response`)の単体テスト。

**ここでも判定はしない**。確認するのは (1) カスケードの境界、(2) 先読みが構造的に
起きないこと、(3) 欠測区間で行が消えず NaN になること、(4) 向きの判定、
(5) プラセボが規模の分布で揃うこと。合成データのみを使う(実データは使わない)。
"""
from __future__ import annotations

import gzip
import json
import math
import random

from bot.research.liq_response import (
    Cascade,
    LiquidationEvent,
    PriceSeries,
    build_cascades,
    build_dataset,
    compute_reactions,
    load_gate_liquidations,
    sample_no_liquidation_windows,
    sample_placebo_windows,
)


def _ev(ts_ms: int, side: str, qty: float = 1.0, price: float = 100.0, exchange: str = "gate"):
    return LiquidationEvent(exchange=exchange, ts_ms=ts_ms, side=side, qty=qty, price=price)


# --------------------------------------------------------------------------- #
# (1) カスケードの境界(閾値の前後で切れる/切れない)
# --------------------------------------------------------------------------- #

def test_cascade_boundary_exactly_at_gap_stays_together():
    """gap がちょうど閾値なら**同じカスケード**に残す(この一点は恣意的な境界規則)。"""
    events = [_ev(0, "long"), _ev(60_000, "long")]  # 60_000ms 差、gap_ms=60_000
    cascades = build_cascades(events, "gate", gap_ms=60_000)
    assert len(cascades) == 1
    assert cascades[0].n_events == 2
    assert cascades[0].start_ms == 0 and cascades[0].end_ms == 60_000


def test_cascade_boundary_just_over_gap_splits():
    """gap が閾値を 1ms でも超えたら**別のカスケード**に切れる。"""
    events = [_ev(0, "long"), _ev(60_001, "long")]
    cascades = build_cascades(events, "gate", gap_ms=60_000)
    assert len(cascades) == 2
    assert [c.n_events for c in cascades] == [1, 1]


def test_multiple_events_form_one_cascade_when_all_close():
    events = [_ev(0, "long"), _ev(10_000, "long"), _ev(25_000, "long"), _ev(40_000, "long")]
    cascades = build_cascades(events, "gate", gap_ms=60_000)
    assert len(cascades) == 1
    c = cascades[0]
    assert c.n_events == 4
    assert c.total_size == 4 * 1.0 * 100.0
    assert c.start_ms == 0 and c.end_ms == 40_000


def test_other_exchange_events_are_filtered_out():
    events = [_ev(0, "long", exchange="gate"), _ev(1_000, "long", exchange="binance_cm")]
    cascades = build_cascades(events, "gate", gap_ms=60_000)
    assert len(cascades) == 1 and cascades[0].exchange == "gate"


# --------------------------------------------------------------------------- #
# (2) 先読みが起きないこと(起点より後の価格を変えても起点の値は変わらない)
# --------------------------------------------------------------------------- #

def test_anchor_price_is_unaffected_by_future_price_changes():
    cascade = Cascade(
        cascade_id="c0", exchange="gate", kind="real",
        start_ms=0, end_ms=100_000, n_events=1, total_size=1.0,
        direction="long", first_price=100.0, last_price=100.0,
    )
    base_points = [(0, 100.0), (100_000, 200.0)]  # 起点時刻ちょうどの価格 = 200.0

    prices_a = PriceSeries.from_trades(base_points + [(200_000, 9_999.0)])
    prices_b = PriceSeries.from_trades(base_points + [(200_000, -9_999.0)])  # 未来だけ大きく変える

    rows_a = compute_reactions([cascade], prices_a, horizons_min=(1,))
    rows_b = compute_reactions([cascade], prices_b, horizons_min=(1,))

    assert rows_a[0]["anchor_price"] == rows_b[0]["anchor_price"] == 200.0
    assert rows_a[0]["anchor_ts_ms"] == rows_b[0]["anchor_ts_ms"] == 100_000


def test_at_or_before_never_returns_a_point_after_the_query_time():
    """`PriceSeries.at_or_before` 自体の性質: 戻り値の時刻は常に `ts_ms` 以下。"""
    series = PriceSeries.from_trades([(t, float(t)) for t in range(0, 1_000_000, 1_000)])
    rng = random.Random(1)
    for _ in range(200):
        query = rng.randint(-500, 1_500_000)
        found = series.at_or_before(query)
        if found is not None:
            assert found[0] <= query


def test_future_bp_uses_a_later_price_than_anchor_but_anchor_stays_fixed():
    """反応窓の値(未来)は起点と別に変わってよいが、起点自体はどの窓を計算しても同じ。"""
    cascade = Cascade(
        cascade_id="c0", exchange="gate", kind="real",
        start_ms=0, end_ms=0, n_events=1, total_size=1.0,
        direction="long", first_price=100.0, last_price=100.0,
    )
    prices = PriceSeries.from_trades([
        (0, 100.0),
        (60_000, 110.0),   # +1分
        (300_000, 90.0),   # +5分
    ])
    rows = compute_reactions([cascade], prices, horizons_min=(1, 5))
    assert rows[0]["anchor_price"] == 100.0
    assert math.isclose(rows[0]["bp_1m"], (110.0 - 100.0) / 100.0 * 10_000)
    assert math.isclose(rows[0]["bp_5m"], (90.0 - 100.0) / 100.0 * 10_000)


# --------------------------------------------------------------------------- #
# (3) 欠測区間で NaN になり、行が消えないこと
# --------------------------------------------------------------------------- #

def test_missing_anchor_price_yields_nan_row_not_dropped():
    """起点時刻より前に価格が 1 点も無ければ anchor は NaN、行自体は残る。"""
    cascade = Cascade(
        cascade_id="c0", exchange="gate", kind="real",
        start_ms=0, end_ms=0, n_events=1, total_size=1.0,
        direction="long", first_price=100.0, last_price=100.0,
    )
    prices = PriceSeries.from_trades([(1_000, 100.0)])  # 全点が起点より後
    rows = compute_reactions([cascade], prices, horizons_min=(1,))
    assert len(rows) == 1
    assert math.isnan(rows[0]["anchor_price"])
    assert math.isnan(rows[0]["bp_1m"])


def test_gap_beyond_staleness_yields_nan_but_keeps_the_row():
    """起点は引けるが、反応窓側の価格が古すぎて staleness を超える場合は NaN。"""
    cascade = Cascade(
        cascade_id="c0", exchange="gate", kind="real",
        start_ms=0, end_ms=0, n_events=1, total_size=1.0,
        direction="long", first_price=100.0, last_price=100.0,
    )
    # +1分の時点(60_000ms)に近い価格が無く、直近の点は 0ms(60秒遡り) のみ
    prices = PriceSeries.from_trades([(0, 100.0)])
    rows = compute_reactions([cascade], prices, horizons_min=(1,), future_max_staleness_ms=1_000)
    assert len(rows) == 1
    assert rows[0]["anchor_price"] == 100.0     # 起点自体は引ける
    assert math.isnan(rows[0]["bp_1m"])          # だが 1 分後の値は staleness 超えで NaN


def test_multiple_cascades_all_rows_present_even_with_mixed_missing_data():
    cascades = [
        Cascade(f"c{i}", "gate", "real", i * 1_000_000, i * 1_000_000, 1, 1.0, "long", 100.0, 100.0)
        for i in range(5)
    ]
    prices = PriceSeries.from_trades([(2_000_000, 100.0)])  # c2 だけ価格が引ける
    rows = compute_reactions(cascades, prices, horizons_min=(1,))
    assert len(rows) == 5   # 行は 1 件も落ちない
    nan_count = sum(1 for r in rows if math.isnan(r["anchor_price"]))
    assert nan_count == 4    # c0,c1,c3,c4 は NaN、c2 だけ値がある


# --------------------------------------------------------------------------- #
# (4) 向き(ロング/ショート/混在)の判定
# --------------------------------------------------------------------------- #

def test_direction_all_long():
    c = build_cascades([_ev(0, "long"), _ev(1_000, "long")], "gate")[0]
    assert c.direction == "long"


def test_direction_all_short():
    c = build_cascades([_ev(0, "short"), _ev(1_000, "short")], "gate")[0]
    assert c.direction == "short"


def test_direction_mixed():
    c = build_cascades([_ev(0, "long"), _ev(1_000, "short")], "gate")[0]
    assert c.direction == "mixed"


# --------------------------------------------------------------------------- #
# (4b) Gate の size 符号 → long/short の対応(傍証で確定済み、固定する)
# --------------------------------------------------------------------------- #

def test_load_gate_liquidations_positive_size_is_long(tmp_path):
    """正の `size` = ロング清算、負の `size` = ショート清算(2026-09-13 の傍証による決着。
    `docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md` 参照。
    バースト内 first→last の `fill_price` が正の size で下降・負の size で上昇に
    明確に偏ったことから決めた対応で、退行させない)。"""
    path = tmp_path / "BTC_USDT.jsonl.gz"
    rows = [
        {"contract": "BTC_USDT", "left": "0", "size": "5", "order_size": "5",
         "fill_price": "100", "order_price": "100", "time": 1_700_000_000},
        {"contract": "BTC_USDT", "left": "0", "size": "-7", "order_size": "7",
         "fill_price": "100", "order_price": "100", "time": 1_700_000_010},
    ]
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    events = load_gate_liquidations(path)
    by_size = {e.qty: e for e in events}
    assert by_size[5.0].side == "long"
    assert by_size[7.0].side == "short"


# --------------------------------------------------------------------------- #
# (5) プラセボが規模の分布でカスケードと揃うこと
# --------------------------------------------------------------------------- #

def test_placebo_windows_match_cascade_size_within_tolerance():
    cascades = [
        Cascade("c0", "gate", "real", 0, 60_000, 3, 300.0, "long", 100.0, 100.0),
        Cascade("c1", "gate", "real", 1_000_000, 1_060_000, 5, 1_000.0, "short", 100.0, 100.0),
    ]
    # 出来高バー: 1分幅、大半は無関係な量。カスケードの窓自体には清算イベントを置く
    liq_events = [_ev(0, "long"), _ev(60_000, "long"),
                  _ev(1_000_000, "short"), _ev(1_060_000, "short")]
    vol_bars = []
    target_c0 = 3_000_000
    target_c1 = 6_000_000
    for t in range(-4_980_000, 10_000_000, 60_000):
        # 300 前後と 1000 前後の「清算を伴わない」出来高急増を仕込む(選ばれるべき候補)
        if t == target_c0:
            vol = 310.0
        elif t == target_c1:
            vol = 980.0
        else:
            vol = 20.0
        vol_bars.append((t, t + 60_000, vol))

    placebo = sample_placebo_windows(cascades, vol_bars, liq_events, "gate",
                                      size_tolerance=0.1, rng=random.Random(0))
    assert len(placebo) == 2
    for p, c in zip(sorted(placebo, key=lambda p: p.total_size), sorted(cascades, key=lambda c: c.total_size)):
        assert abs(p.total_size - c.total_size) / c.total_size <= 0.1
        assert p.kind == "placebo"
        assert p.n_events == 0


def test_placebo_windows_never_overlap_a_liquidation_event():
    cascades = [Cascade("c0", "gate", "real", 0, 60_000, 2, 100.0, "long", 100.0, 100.0)]
    liq_events = [_ev(0, "long"), _ev(60_000, "long"), _ev(5_000_000, "long")]  # 中盤に1件散らす
    vol_bars = [(t, t + 60_000, 100.0) for t in range(-2_000_000, 10_000_000, 60_000)]
    placebo = sample_placebo_windows(cascades, vol_bars, liq_events, "gate",
                                      size_tolerance=0.5, rng=random.Random(0))
    for p in placebo:
        for e in liq_events:
            assert not (p.start_ms <= e.ts_ms <= p.end_ms)


def test_no_liquidation_windows_contain_no_events_and_match_duration():
    cascades = [Cascade("c0", "gate", "real", 0, 30_000, 2, 100.0, "long", 100.0, 100.0)]
    liq_events = [_ev(0, "long"), _ev(30_000, "long"), _ev(2_000_000, "long")]
    windows = sample_no_liquidation_windows(cascades, liq_events, "gate",
                                             span_start_ms=0, span_end_ms=5_000_000,
                                             rng=random.Random(0))
    assert len(windows) == 1
    w = windows[0]
    assert w.end_ms - w.start_ms == 30_000
    for e in liq_events:
        assert not (w.start_ms <= e.ts_ms <= w.end_ms)


# --------------------------------------------------------------------------- #
# build_dataset: 行数の確認のみ(判定はしない)
# --------------------------------------------------------------------------- #

def test_build_dataset_keeps_all_rows_across_kinds():
    real = build_cascades([_ev(0, "long"), _ev(10_000, "long")], "gate")
    placebo = [Cascade("gate_placebo_000000", "gate", "placebo", 100_000, 130_000, 0, 300.0, "none", None, None)]
    no_liq = [Cascade("gate_no_liq_000000", "gate", "no_liquidation", 200_000, 230_000, 0, 0.0, "none", None, None)]
    prices = PriceSeries.from_trades([(t, 100.0 + t / 1_000_000) for t in range(0, 300_000, 1_000)])
    rows = build_dataset(real, placebo, no_liq, prices, horizons_min=(1, 5))
    assert len(rows) == len(real) + len(placebo) + len(no_liq) == 3
    kinds = {r["kind"] for r in rows}
    assert kinds == {"real", "placebo", "no_liquidation"}


def test_load_binance_cm_liquidations_raises_when_no_zip_found(tmp_path):
    """パスを間違えたときに黙って 0 件を返さない(2026-09-13)。

    `read_rows` と同じ欠陥。1 階層違うディレクトリを渡すと空が返り、
    「その期間に清算が無かった」と読めてしまう。
    """
    import pytest

    from bot.research.liq_response import load_binance_cm_liquidations

    empty = tmp_path / "wrong_level"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        load_binance_cm_liquidations(empty)


# --------------------------------------------------------------------------- #
# 転換(内部の値動き × その後の反応): タイを黙って落とさない
#
# 段 0 の実行スクリプト(`scripts/run_o3c_stage0.py` の内側で操作的に定義された
# `reversal()`)は `internal_bp == 0` の行を NaN として落としていた。カスケードは
# 1 分バーに収まることが多く、タイは実群で 8 割・プラセボで 0% と**群間で非対称**に
# 出るため、非無作為な部分集合と全体を比べる形になっていた。以下はその再発防止。
# --------------------------------------------------------------------------- #

def _rev_row(cid, internal_bp, bp, first_price=None, last_price=None, start_ms=0):
    """転換の計算に必要な列だけを持つ合成行。"""
    return {
        "cascade_id": cid, "start_ms": start_ms, "end_ms": start_ms + 10_000,
        "internal_bp": internal_bp, "bp_1m": bp,
        "first_price": first_price, "last_price": last_price,
        "anchor_price": 100.0,
    }


def test_reversal_default_keeps_ties_and_drops_no_rows():
    """既定(`tie_policy="keep"`)ではタイの行が 1 つも落ちない。"""
    from bot.research.liq_response import reversal_scores

    rows = [
        _rev_row("a", 5.0, 10.0),    # 内部 +、反応 + → 転換 -10
        _rev_row("b", 0.0, 10.0),    # タイ
        _rev_row("c", 0.0, -4.0),    # タイ
        _rev_row("d", -2.0, 6.0),    # 内部 -、反応 + → 転換 +6
    ]
    g = reversal_scores(rows, "bp_1m", name="real")
    assert g.n_rows == 4
    assert g.n_used == 4                      # 1 行も落ちていない
    assert g.n_excluded == 0 and g.n_excluded_tie == 0
    assert g.exclusion_rate == 0.0
    assert g.n_tie == 2 and g.tie_rate == 0.5
    assert g.scores == [-10.0, 0.0, 0.0, 6.0]  # タイは符号 0 = 別の水準として残る
    assert g.mean == (-10.0 + 0.0 + 0.0 + 6.0) / 4


def test_reversal_drop_reports_the_number_it_excluded():
    """除外を選んだときは、除外件数と除外率が戻り値に必ず現れる。"""
    from bot.research.liq_response import reversal_scores

    rows = [_rev_row("a", 5.0, 10.0), _rev_row("b", 0.0, 10.0), _rev_row("c", 0.0, -4.0),
            _rev_row("d", -2.0, 6.0)]
    g = reversal_scores(rows, "bp_1m", name="real", tie_policy="drop")
    assert g.n_rows == 4
    assert g.n_tie == 2
    assert g.n_excluded_tie == 2               # 黙って消えない
    assert g.n_used == 2 and g.scores == [-10.0, 6.0]
    assert g.exclusion_rate == 0.5
    # 行数の内訳は必ず閉じる(どこかへ消えた行が無い)
    assert g.n_rows == g.n_used + g.n_excluded_tie + g.n_excluded_missing


def test_reversal_missing_values_counted_separately_from_ties():
    """本物の欠測(NaN)はタイとは別に数える。どの方針でも集計には入れない。"""
    from bot.research.liq_response import reversal_scores

    rows = [_rev_row("a", 5.0, 10.0), _rev_row("b", float("nan"), 10.0),
            _rev_row("c", 5.0, float("nan")), _rev_row("d", 0.0, 3.0)]
    g = reversal_scores(rows, "bp_1m", name="real")
    assert g.n_excluded_missing == 2
    assert g.n_tie == 1 and g.n_excluded_tie == 0
    assert g.n_used == 2
    assert g.n_rows == g.n_used + g.n_excluded_tie + g.n_excluded_missing


def test_reversal_raises_when_groups_are_excluded_at_different_rates():
    """群間の除外率が大きく違えば、警告ではなく例外(既定 strict=True)。"""
    import pytest

    from bot.research.liq_response import ReversalExclusionImbalance, compute_reversal

    # 実群は 8 割がタイ、対照はタイ無し(段 0 で実際に起きた形)
    real = [_rev_row(f"r{i}", 0.0, 1.0) for i in range(8)] + \
           [_rev_row(f"r{i}", 3.0, 1.0) for i in range(8, 10)]
    control = [_rev_row(f"c{i}", 3.0, 1.0) for i in range(10)]

    with pytest.raises(ReversalExclusionImbalance) as ei:
        compute_reversal({"real": real, "placebo": control}, "bp_1m", tie_policy="drop")
    msg = str(ei.value)
    assert "80.0%" in msg and "0.0%" in msg      # 群ごとの除外率が本文に出る

    # 既定(タイを落とさない)なら除外が起きないので例外にならない
    rep = compute_reversal({"real": real, "placebo": control}, "bp_1m")
    assert rep.max_exclusion_gap == 0.0
    assert rep.exclusion_rates == {"real": 0.0, "placebo": 0.0}
    assert rep.groups["real"].n_tie == 8

    # 診断目的で通したいときは strict=False を明示する(そのとき除外率は残る)
    rep2 = compute_reversal({"real": real, "placebo": control}, "bp_1m",
                            tie_policy="drop", strict=False)
    assert rep2.exclusion_rates == {"real": 0.8, "placebo": 0.0}
    assert rep2.max_exclusion_gap == 0.8
    assert [r["n_excluded_tie"] for r in rep2.summary_rows()] == [8, 0]


def test_reversal_refine_uses_cascade_prices_when_the_minute_bar_collapses():
    """1 分バーの終値では潰れるが `first_price`/`last_price` では区別できる行。

    カスケードが 1 本のバーに収まると粗い内部方向は 0(タイ)になる。`refine` は
    その行だけカスケード自身の価格で符号を取り直し、**それでも決まらない行は
    落とさずに 0 のまま残す**。
    """
    from bot.research.liq_response import reversal_scores

    rows = [
        # バーでは潰れる(0)が、清算約定の価格は 100.0 → 99.0(内部 -)
        _rev_row("collapsed_down", 0.0, 8.0, first_price=100.0, last_price=99.0),
        # バーでは潰れる(0)が、清算約定の価格は 100.0 → 101.0(内部 +)
        _rev_row("collapsed_up", 0.0, 8.0, first_price=100.0, last_price=101.0),
        # 細かい価格でも動いていない → タイのまま(落とさない)
        _rev_row("really_flat", 0.0, 8.0, first_price=100.0, last_price=100.0),
        # 対照窓は first/last を持たない → タイのまま(落とさない)
        _rev_row("control_like", 0.0, 8.0, first_price=None, last_price=None),
    ]
    fine = reversal_scores(rows, "bp_1m", name="real", tie_policy="refine")
    assert fine.n_rows == 4 and fine.n_used == 4 and fine.n_excluded == 0
    assert fine.n_tie == 4 and fine.n_tie_resolved == 2
    assert fine.scores == [8.0, -8.0, 0.0, 0.0]

    # 既定(keep)では 4 行ともタイのまま = 0。落ちる行はどちらでも無い。
    kept = reversal_scores(rows, "bp_1m", name="real")
    assert kept.scores == [0.0, 0.0, 0.0, 0.0] and kept.n_used == 4


def test_attach_internal_direction_marks_ties_not_nan_and_keeps_every_row():
    """1 分バーの終値で作った価格系列では、1 分に収まる窓の内部方向は 0(NaN ではない)。"""
    from bot.research.liq_response import attach_internal_direction, compute_reactions

    # 1 分ごとの終値だけを持つ系列(段 0 の実行と同じ作り)
    bars = [(m * 60_000, 100.0 + m) for m in range(0, 10)]
    prices = PriceSeries.from_trades(bars)
    # 分 3 の内側で始まり内側で終わるカスケード(3:10 → 3:40)
    inside = Cascade("x_real_000000", "x", "real", 190_000, 220_000, 2, 10.0, "long", 100.5, 99.5)
    # 分 3 から分 5 にまたがるカスケード
    across = Cascade("x_real_000001", "x", "real", 190_000, 310_000, 2, 10.0, "long", 100.5, 99.5)
    rows = compute_reactions([inside, across], prices, horizons_min=(1,))
    attach_internal_direction(rows, prices)

    assert len(rows) == 2                       # 行は落ちない
    assert rows[0]["internal_bp"] == 0.0        # 同じバーの終値どうし = タイ(NaN ではない)
    assert rows[1]["internal_bp"] != 0.0        # バーをまたげば符号が付く
    assert not math.isnan(rows[0]["internal_bp"])
    # 細かい分解能(カスケード自身の価格)では、収まった窓にも符号がある
    assert rows[0]["internal_bp_fine"] < 0.0
