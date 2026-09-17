"""`scripts/o3c_price_level_ext.py` の単体テスト(2026-09-17)。

固定するのは 5 点:
  (a) 束ね方(60,000ms ちょうどは同じ束 / 同一 ms も同じ束)と、束の最初の 1 件の選び方。
  (b) ノード 1 つの合成プロファイルでの SELL / BUY 帯の位置、帯の重なりと範囲の切り落とし
      を含む `band_coverage`、そして清算価格が帯に入ったかの判定。

このテストは**観測表の作り方**だけを固定する。相場についての判定は一切しない。
"""

from __future__ import annotations

import csv
import importlib.util
import io
import math
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


base = _load("o3c_price_level_table")
ext = _load("o3c_price_level_ext")


# --------------------------------------------------------------------------
# (a) 束ね方と最初の 1 件
# --------------------------------------------------------------------------


def test_bundle_ranges_keeps_exact_gap_and_same_ms_together():
    """60,000ms ちょうどは同じ束、60,001ms で切れる。同一 ms は同じ束。"""
    t0 = 1_700_000_000_000
    times = [
        t0,  # 束 1
        t0,  # 同一 ms -> 束 1
        t0 + 60_000,  # ちょうど 60 秒 -> 束 1
        t0 + 120_001,  # 直前から 60,001ms -> 束 2
        t0 + 121_001,  # 束 2
    ]
    assert ext.base.bundle_ranges(times, 60_000) == [(0, 2), (3, 4)]
    # 境界の反対側: 60,000 を 1ms 超えたら切れる
    assert base.bundle_ranges([t0, t0 + 60_001], 60_000) == [(0, 0), (1, 1)]
    # 空
    assert base.bundle_ranges([], 60_000) == []


DAY = "2024-01-02"
PREV = "2024-01-01"
D_START, _ = base.day_bounds_ms(DAY)
P_START, _ = base.day_bounds_ms(PREV)
T_BUNDLE = D_START + 12 * 3600_000


def _write_zip(path: Path, csv_name: str, header: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(csv_name, buf.getvalue())


def _write_agg(root: Path, day: str, rows: list[tuple[int, float, float]]) -> None:
    _write_zip(
        base.agg_path(root, day),
        f"{base.SYMBOL}-aggTrades-{day}.csv",
        base.AGG_NAMES,
        [(i, p, q, i, i, t, "true") for i, (t, p, q) in enumerate(rows, start=1)],
    )


def _write_liq(root: Path, day: str, rows: list[tuple]) -> None:
    _write_zip(
        base.liq_path(root, day),
        f"{base.SYMBOL}-liquidationSnapshot-{day}.csv",
        base.LIQ_NAMES,
        rows,
    )


def _liq_row(t: int, side: str, qty: float, px: float) -> tuple:
    return (t, side, "LIMIT", "IOC", qty, px, px, "FILLED", qty, qty)


@pytest.fixture()
def bundle_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    # 1 時間おきの約定(前日 + 当日)。価格は 30000 近辺。
    _write_agg(
        root,
        PREV,
        [(P_START + h * 3600_000, 30000.0 + h, 5.0) for h in range(24)],
    )
    _write_agg(
        root,
        DAY,
        [(D_START + h * 3600_000, 30000.0 + h, 5.0) for h in range(24)],
    )
    _write_liq(
        root,
        DAY,
        [
            _liq_row(T_BUNDLE, "SELL", 10, 30010.0),
            _liq_row(T_BUNDLE, "SELL", 20, 30011.0),  # 同一 ms
            _liq_row(T_BUNDLE + 60_000, "BUY", 30, 30012.0),  # ちょうど 60 秒
            _liq_row(T_BUNDLE + 120_001, "BUY", 40, 30013.0),  # 新しい束
            _liq_row(T_BUNDLE + 121_001, "SELL", 50, 30014.0),
        ],
    )
    return root


def test_bundle_mode_keeps_only_the_first_row_of_each_bundle(bundle_root: Path):
    """束の最初の 1 件だけが清算行になり、束の件数と数量合計が列に付く。"""
    rows, note = base.process_day(
        DAY, bundle_root, 24.0, 0.1, seed=1, bundle_gap_ms=60_000
    )
    liq = [r for r in rows if r["kind"] == "liq"]
    ctl = [r for r in rows if r["kind"] == "control"]
    assert note["liq_rows_in_file"] == 5
    assert note["bundles_in_file"] == 2
    assert note["bundles_dropped_no_price"] == 0
    assert [r["time_ms"] for r in liq] == [T_BUNDLE, T_BUNDLE + 120_001]
    # 最初の 1 件の属性(side / 価格)がそのまま入る
    assert [r["side"] for r in liq] == ["SELL", "BUY"]
    assert [r["p_liq"] for r in liq] == [30010.0, 30013.0]
    assert [r["qty"] for r in liq] == [10.0, 40.0]
    # 束全体の件数と数量
    assert [r["bundle_n_events"] for r in liq] == [3, 2]
    assert [r["bundle_total_qty"] for r in liq] == [60.0, 90.0]
    # 完全一致の行が無いので、一意にした件数も同じ
    assert [r["bundle_n_events_dedup"] for r in liq] == [3, 2]
    assert [r["bundle_total_qty_dedup"] for r in liq] == [60.0, 90.0]
    assert note["liq_rows_unique_in_file"] == 5
    # 対照は束と同数、束の最初の時刻から ±5 分以上
    assert len(ctl) == 2
    for r in ctl:
        assert r["bundle_n_events"] == ""
        assert min(abs(r["time_ms"] - t) for t in (T_BUNDLE, T_BUNDLE + 120_001)) >= (
            base.CONTROL_GAP_MS
        )
    # 束ねない既定では 5 件そのまま
    plain, _ = base.process_day(DAY, bundle_root, 24.0, 0.1, seed=1)
    assert len([r for r in plain if r["kind"] == "liq"]) == 5


def test_bundle_counts_exact_duplicate_rows_once_in_the_dedup_columns(
    bundle_root: Path,
):
    """本物の liquidationSnapshot は 1 件の清算が全列同じ行として 2 回現れる。

    束の切れ目(同一 ms)は変わらず、`*_dedup` 側だけが 1 回として数える。
    """
    _write_liq(
        bundle_root,
        DAY,
        [
            _liq_row(T_BUNDLE, "SELL", 10, 30010.0),
            _liq_row(T_BUNDLE, "SELL", 10, 30010.0),  # 全列まったく同じ
            _liq_row(T_BUNDLE + 30_000, "SELL", 20, 30011.0),
            _liq_row(T_BUNDLE + 30_000, "SELL", 20, 30011.0),  # 同上
        ],
    )
    rows, note = base.process_day(
        DAY, bundle_root, 24.0, 0.1, seed=1, bundle_gap_ms=60_000
    )
    liq = [r for r in rows if r["kind"] == "liq"]
    assert note["liq_rows_in_file"] == 4
    assert note["liq_rows_unique_in_file"] == 2
    assert note["bundles_in_file"] == 1
    assert len(liq) == 1
    assert liq[0]["bundle_n_events"] == 4
    assert liq[0]["bundle_n_events_dedup"] == 2
    assert liq[0]["bundle_total_qty"] == pytest.approx(60.0)
    assert liq[0]["bundle_total_qty_dedup"] == pytest.approx(30.0)


# --------------------------------------------------------------------------
# (b) 帯の位置・広さ・入ったかの判定
# --------------------------------------------------------------------------

STEP = base.log_step(0.1)


def test_band_sits_at_the_side_offset_from_a_single_node():
    """ノード 1 つのプロファイルで、SELL 帯は下、BUY 帯は上の所定のビンに出る。

    ビン幅 0.1% の対数ビンなので、ノードのビン k(代表価格は k+0.5 の位置)から見ると
      SELL: ln(1-0.0056)/ln(1.001) = -5.618 ビン -> floor(k+0.5-5.618) = k-6
      BUY : ln(1+0.0070)/ln(1.001) = +6.979 ビン -> floor(k+0.5+6.979) = k+7
    帯はその ±1 ビン。
    """
    lo = base.bin_index(30000.0, STEP)
    qty = [1.0] * 10
    qty[5] = 100.0
    nodes = ext.node_bins(qty, lo)
    assert list(nodes) == [lo + 5]  # 上位 10% = 1 本
    k = lo + 5

    sell = ext.band_bins_for_side(nodes, STEP, ext.SIDE_OFFSET["SELL"])
    buy = ext.band_bins_for_side(nodes, STEP, ext.SIDE_OFFSET["BUY"])
    assert list(sell) == [k - 7, k - 6, k - 5]
    assert list(buy) == [k + 6, k + 7, k + 8]
    # 手計算の確認(ビンのずれが bp でだいたい −56 / +70 になる)
    assert math.log(1 + ext.SIDE_OFFSET["SELL"]) / STEP == pytest.approx(-5.618, abs=0.01)
    assert math.log(1 + ext.SIDE_OFFSET["BUY"]) / STEP == pytest.approx(6.979, abs=0.01)


def test_band_coverage_clips_to_range_and_counts_overlap_once():
    """範囲の外に出た帯は切り落とす。重なった帯は 1 回だけ数える。"""
    lo = base.bin_index(30000.0, STEP)
    # (1) 範囲 10 ビン、ノード 1 つ -> SELL 帯 {k-7,k-6,k-5} = {lo-2,lo-1,lo} で
    #     範囲 [lo, lo+9] に入るのは lo の 1 本だけ。
    qty = [1.0] * 10
    qty[5] = 100.0
    nodes = ext.node_bins(qty, lo)
    sell = ext.band_bins_for_side(nodes, STEP, ext.SIDE_OFFSET["SELL"])
    cov, cov_log, n_in = ext.band_coverage(sell, lo, 10, STEP)
    assert n_in == 1
    assert cov_log == pytest.approx(0.1)
    assert cov == pytest.approx(0.1, abs=0.01)  # 価格幅で測ってもほぼ 1/10

    # (2) ノード 2 本が隣り合うと帯が重なる: 3+3 = 6 本ではなく 4 本
    qty2 = [1.0] * 20
    qty2[10] = 100.0
    qty2[11] = 99.0
    nodes2 = ext.node_bins(qty2, lo)
    assert list(nodes2) == [lo + 10, lo + 11]  # 上位 10% = 2 本
    sell2 = ext.band_bins_for_side(nodes2, STEP, ext.SIDE_OFFSET["SELL"])
    assert list(sell2) == [lo + 3, lo + 4, lo + 5, lo + 6]
    cov2, cov_log2, n_in2 = ext.band_coverage(sell2, lo, 20, STEP)
    assert n_in2 == 4
    assert cov_log2 == pytest.approx(4 / 20)

    # 帯が 1 本も範囲に入らなければ 0
    assert ext.band_coverage(sell2, lo + 50, 20, STEP) == (0.0, 0.0, 0)


T_HOUR = D_START + 1 * 3600_000
NODE_PX = 30000.0


@pytest.fixture()
def band_root(tmp_path: Path) -> Path:
    """30000 に厚み(ノード)がある合成日。清算は 01:00 台に 2 件(SELL)。"""
    root = tmp_path / "data"
    prev_rows: list[tuple[int, float, float]] = []
    for h in range(24):
        prev_rows.append((P_START + h * 3600_000, NODE_PX, 1e9))  # ノード
        prev_rows.append((P_START + h * 3600_000 + 60_000, NODE_PX * 0.995, 1.0))
        prev_rows.append((P_START + h * 3600_000 + 120_000, NODE_PX * 1.008, 1.0))
    day_rows = [
        (D_START + 60_000, NODE_PX, 1.0),
        # 01:00 台の約定 2 本: 1 本は SELL 帯の中、1 本はノードの上(帯の外)
        (T_HOUR + 1_800_000, NODE_PX * (1 - 0.0056), 1.0),
        (T_HOUR + 1_860_000, NODE_PX, 1.0),
    ]
    _write_agg(root, PREV, prev_rows)
    _write_agg(root, DAY, day_rows)
    _write_liq(
        root,
        DAY,
        [
            # ノード × (1 − 0.0056) = SELL 帯のど真ん中
            _liq_row(T_HOUR + 600_000, "SELL", 5, NODE_PX * (1 - 0.0056)),
            # 範囲のはるか外(どのノードの帯にも入りようがない)
            _liq_row(T_HOUR + 1_200_000, "SELL", 5, NODE_PX * 1.5),
        ],
    )
    return root


def test_in_band_counts_only_liquidations_inside_the_side_band(band_root: Path):
    """帯の中の清算だけが `n_liq_in_band` に入る(01:00 台の SELL は 2 件中 1 件)。"""
    rows, note = ext.process_day_band(DAY, band_root, 24.0, 0.1)
    assert note["hours_written"] == 24
    hour = {
        r["side"]: r for r in rows if r["t_ms"] == T_HOUR
    }
    sell = hour["SELL"]
    assert sell["n_liq"] == 2
    assert sell["n_liq_in_band"] == 1
    assert sell["in_band_rate"] == pytest.approx(0.5)
    # BUY 側にはこの 1 時間の清算が無い
    assert hour["BUY"]["n_liq"] == 0
    assert hour["BUY"]["in_band_rate"] == ""
    # 対照の 2 本も同じ行に入っている(約定は 2 本中 1 本が帯の中)
    assert 0.0 < sell["band_coverage"] <= 1.0
    assert sell["n_trades"] == 2
    assert sell["n_trades_in_band"] == 1
    assert sell["trade_in_band_rate"] == pytest.approx(0.5)
