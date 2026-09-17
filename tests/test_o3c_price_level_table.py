"""scripts/o3c_price_level_table.py の単体検査(合成データ)。

設計: docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md
検査するのは表の作り方だけで、相場についての主張は一切しない。
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import random
import zipfile
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "o3c_price_level_table",
    Path(__file__).resolve().parents[1] / "scripts" / "o3c_price_level_table.py",
)
mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(mod)


# --------------------------------------------------------------------------
# (a) ビンの百分位が手計算と一致する
# --------------------------------------------------------------------------


def _fixture_profile():
    """5 ビンのプロファイル。中央(相対 2)が p_liq のビン。"""
    step = mod.log_step(0.1)
    b0 = mod.bin_index(30000.0, step)
    qty = np.array([10.0, 0.0, 5.0, 20.0, 3.0])
    lo_bin = b0 - 2
    p_liq = float(mod.bin_center_price(b0, step))
    return step, lo_bin, qty, p_liq


def test_bin_pct_matches_hand_count():
    step, lo_bin, qty, p_liq = _fixture_profile()
    # p_liq は相対 2(数量 5)のビンに落ちる
    assert mod.bin_index(p_liq, step) - lo_bin == 2
    st = mod.profile_stats(qty, lo_bin, step, p_liq, p_liq)
    # 数量 5 より少ないビンは 0 と 3 の 2 本 / 全 5 本 -> 40%
    assert st["bin_pct"] == pytest.approx(40.0)
    assert st["n_bins"] == 5
    assert st["total_qty"] == pytest.approx(38.0)
    assert st["p_liq_in_range"] is True


def test_bin_pct_counts_zero_bins_inside_range():
    """数量 0 のビンも範囲内の 1 本として百分位の母数に入る。"""
    step, lo_bin, qty, p_liq = _fixture_profile()
    # 相対 1 の空白ビン(数量 0)を p_liq にすると、より少ないビンは 0 本 -> 0%
    p_zero = float(mod.bin_center_price(lo_bin + 1, step))
    st = mod.profile_stats(qty, lo_bin, step, p_zero, p_zero)
    assert st["bin_pct"] == pytest.approx(0.0)
    assert st["n_bins"] == 5


# --------------------------------------------------------------------------
# (b) dist_node_bp / dist_gap_bp の符号
# --------------------------------------------------------------------------


def test_dist_node_and_gap_signs():
    step, lo_bin, qty, p_liq = _fixture_profile()
    st = mod.profile_stats(qty, lo_bin, step, p_liq, p_liq)
    # ノード(上位 10% = 1 本)は数量 20 の相対 3 = p_liq より 1 ビン上 -> 正で約 +10bp
    assert st["dist_node_bp"] > 0
    assert st["dist_node_bp"] == pytest.approx(10.0, abs=0.2)
    # 空白(下位 10% = 1 本)は数量 0 の相対 1 = p_liq より 1 ビン下 -> 負
    assert st["dist_gap_bp"] < 0
    assert st["dist_gap_bp"] == pytest.approx(-10.0, abs=0.2)


def test_dist_node_sign_flips_when_node_is_below():
    """ノードが p_liq より下にあれば符号は負になる。"""
    step = mod.log_step(0.1)
    b0 = mod.bin_index(30000.0, step)
    qty = np.array([50.0, 1.0, 1.0, 1.0, 1.0])  # 最も厚いのは相対 0(= 2 ビン下)
    lo_bin = b0 - 2
    p_liq = float(mod.bin_center_price(b0, step))
    st = mod.profile_stats(qty, lo_bin, step, p_liq, p_liq)
    assert st["dist_node_bp"] < 0
    assert st["dist_node_bp"] == pytest.approx(-20.0, abs=0.4)


def test_vol_between_ratio_uses_bins_between_p0_and_p_liq():
    step, lo_bin, qty, _ = _fixture_profile()
    p_low = float(mod.bin_center_price(lo_bin, step))  # 相対 0
    p_high = float(mod.bin_center_price(lo_bin + 2, step))  # 相対 2
    st = mod.profile_stats(qty, lo_bin, step, p_high, p_low)
    # 相対 0..2 の数量 10 + 0 + 5 = 15 / 全 38
    assert st["vol_between_ratio"] == pytest.approx(15.0 / 38.0)


# --------------------------------------------------------------------------
# (c) 対照時刻が清算から 5 分以上離れる
# --------------------------------------------------------------------------


def test_control_times_keep_five_minute_gap():
    day_start, day_end = mod.day_bounds_ms("2020-01-02")
    liqs = [day_start + h * 3600_000 for h in range(0, 24, 2)]  # 2 時間ごと 12 件
    rng = random.Random("1|2020-01-02")
    ts = mod.sample_control_times(liqs, day_start, day_end, 300, rng)
    assert len(ts) == 300
    for t in ts:
        assert day_start <= t < day_end
        assert min(abs(t - x) for x in liqs) >= mod.CONTROL_GAP_MS


def test_control_times_are_deterministic_for_a_seed():
    day_start, day_end = mod.day_bounds_ms("2020-01-02")
    liqs = [day_start + 12 * 3600_000]
    a = mod.sample_control_times(liqs, day_start, day_end, 20, random.Random("7|d"))
    b = mod.sample_control_times(liqs, day_start, day_end, 20, random.Random("7|d"))
    assert a == b


def test_control_times_empty_when_day_is_fully_blocked():
    day_start, day_end = mod.day_bounds_ms("2020-01-02")
    # 1 分ごとに清算があれば ±5 分の除外で 1 日が埋まる
    liqs = [day_start + m * 60_000 for m in range(0, 1440)]
    assert mod.sample_control_times(liqs, day_start, day_end, 5, random.Random("1")) == []


# --------------------------------------------------------------------------
# (d) 窓の外の約定が使われない(zip を作って実際に走らせる)
# --------------------------------------------------------------------------

DAY = "2020-01-02"
PREV = "2020-01-01"
T_LIQ = 1577966400000  # 2020-01-02 12:00:00 UTC
WINDOW_LEFT = T_LIQ - 24 * 3600_000  # 2020-01-01 12:00:00 UTC

AGG_ROWS = {
    PREV: [
        # (transact_time, price, quantity)
        (1577858400000, 29000.0, 999.0),  # 窓の 6 時間前 -> 使わない
        (WINDOW_LEFT - 1, 29500.0, 500.0),  # 窓の 1ms 前 -> 使わない
        (WINDOW_LEFT, 30000.0, 11.0),  # 窓の左端ちょうど -> 使う
        (1577901600000, 30000.0, 5.0),  # 使う
    ],
    DAY: [
        (1577944800000, 30030.0, 7.0),  # 使う
        (T_LIQ - 60_000, 30060.0, 3.0),  # 使う(直前の約定 = p0)
        (T_LIQ, 31000.0, 400.0),  # 清算と同時刻 -> 直前ではないので使わない
        (T_LIQ + 3600_000, 30100.0, 2.0),
    ],
}

LIQ_ROWS = [
    (T_LIQ, "SELL", "LIMIT", "IOC", 100, 30050.0, 30040.0, "FILLED", 100, 100),
    (T_LIQ + 3600_000, "BUY", "LIMIT", "IOC", 40, 30150.0, 30140.0, "FILLED", 40, 40),
]


def _write_zip(path: Path, csv_name: str, header: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(csv_name, buf.getvalue())


@pytest.fixture()
def synth_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    for day, rows in AGG_ROWS.items():
        _write_zip(
            mod.agg_path(root, day),
            f"{mod.SYMBOL}-aggTrades-{day}.csv",
            mod.AGG_NAMES,
            [(i, p, q, i, i, t, "true") for i, (t, p, q) in enumerate(rows, start=1)],
        )
    _write_zip(
        mod.liq_path(root, DAY),
        f"{mod.SYMBOL}-liquidationSnapshot-{DAY}.csv",
        mod.LIQ_NAMES,
        LIQ_ROWS,
    )
    return root


def test_trades_outside_window_are_not_used(synth_root: Path):
    rows, note = mod.process_day(DAY, synth_root, 24.0, 0.1, seed=1)
    liq_rows = [r for r in rows if r["kind"] == "liq"]
    assert note["prev_day_agg_present"] is True
    first = next(r for r in liq_rows if r["time_ms"] == T_LIQ)
    # 窓の中の 4 本ぶんだけ: 11 + 5 + 7 + 3 = 26。999 も 500 も 400 も入らない。
    assert first["total_qty"] == pytest.approx(26.0)
    # p0 は清算の直前の約定価格(同時刻の 31000 ではない)
    assert first["p0"] == pytest.approx(30060.0)
    # 既定は average_price
    assert first["p_liq"] == pytest.approx(30040.0)
    assert first["p_avg"] == pytest.approx(30040.0)
    assert first["side"] == "SELL"


def test_liq_price_field_switches_between_avg_and_limit(synth_root: Path):
    """--liq-price-field で p_liq に入る列が切り替わる(既定 = average_price)。"""
    avg_rows, _ = mod.process_day(
        DAY, synth_root, 24.0, 0.1, seed=1, liq_price_field="average_price"
    )
    lim_rows, _ = mod.process_day(
        DAY, synth_root, 24.0, 0.1, seed=1, liq_price_field="price"
    )
    avg = {r["time_ms"]: r for r in avg_rows if r["kind"] == "liq"}
    lim = {r["time_ms"]: r for r in lim_rows if r["kind"] == "liq"}
    for t, _side, _ot, _tif, _q, price, avg_price, *_ in LIQ_ROWS:
        assert avg[t]["p_liq"] == pytest.approx(avg_price)
        assert lim[t]["p_liq"] == pytest.approx(price)
        # p_avg 列はどちらでも average_price のまま
        assert avg[t]["p_avg"] == pytest.approx(avg_price)
        assert lim[t]["p_avg"] == pytest.approx(avg_price)
    # 既定引数は average_price
    default_rows, _ = mod.process_day(DAY, synth_root, 24.0, 0.1, seed=1)
    assert [r["p_liq"] for r in default_rows if r["kind"] == "liq"] == [
        r["p_liq"] for r in avg_rows if r["kind"] == "liq"
    ]
    with pytest.raises(ValueError):
        mod.process_day(DAY, synth_root, 24.0, 0.1, seed=1, liq_price_field="p_avg")


def test_rows_without_the_chosen_price_are_dropped_and_counted(
    synth_root: Path,
):
    """average_price が空か 0 の行は落とし、件数を注記に残す。"""
    rows = [
        (T_LIQ, "SELL", "LIMIT", "IOC", 100, 30050.0, 30040.0, "FILLED", 100, 100),
        (T_LIQ + 60_000, "SELL", "LIMIT", "IOC", 10, 30055.0, 0, "NEW", 0, 0),
        (T_LIQ + 120_000, "BUY", "LIMIT", "IOC", 10, 30160.0, "", "NEW", 0, 0),
    ]
    _write_zip(
        mod.liq_path(synth_root, DAY),
        f"{mod.SYMBOL}-liquidationSnapshot-{DAY}.csv",
        mod.LIQ_NAMES,
        rows,
    )
    out, note = mod.process_day(DAY, synth_root, 24.0, 0.1, seed=1)
    assert note["liq_rows_in_file"] == 3
    assert note["liq_rows_dropped_no_price"] == 2
    assert [r["time_ms"] for r in out if r["kind"] == "liq"] == [T_LIQ]
    # 対照は残った清算行と同数
    assert len([r for r in out if r["kind"] == "control"]) == 1
    # price 版なら 3 件とも残る
    _, note2 = mod.process_day(DAY, synth_root, 24.0, 0.1, seed=1, liq_price_field="price")
    assert note2["liq_rows_dropped_no_price"] == 0


def test_control_rows_use_p0_as_p_liq(synth_root: Path):
    rows, _ = mod.process_day(DAY, synth_root, 24.0, 0.1, seed=1)
    ctl = [r for r in rows if r["kind"] == "control"]
    assert ctl, "対照行が 1 件も出ていない"
    for r in ctl:
        assert r["p_liq"] == pytest.approx(r["p0"])
        assert r["side"] == ""
        assert min(abs(r["time_ms"] - t) for t, *_ in LIQ_ROWS) >= mod.CONTROL_GAP_MS


def test_missing_previous_day_is_recorded(synth_root: Path, tmp_path: Path):
    """前日の aggTrades が無ければ窓が短くなることを注記に残す。"""
    mod.agg_path(synth_root, PREV).unlink()
    rows, note = mod.process_day(DAY, synth_root, 24.0, 0.1, seed=1)
    assert note["prev_day_agg_present"] is False
    assert "warning" in note and "短い" in note["warning"]
    first = next(r for r in rows if r["kind"] == "liq" and r["time_ms"] == T_LIQ)
    # その日の約定だけ = 7 + 3
    assert first["total_qty"] == pytest.approx(10.0)


def test_run_writes_table_summary_and_md5sums(synth_root: Path, tmp_path: Path):
    out = tmp_path / "out"
    summary = mod.run([DAY], synth_root, out, 24.0, 0.1, seed=1)
    assert (out / "table.csv").exists()
    assert (out / "summary.json").exists()
    header = (out / "table.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",") == mod.COLUMNS
    loaded = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert loaded["rows_liq"] == summary["rows_liq"] == 2
    assert loaded["side_counts"] == {"SELL": 1, "BUY": 1}
    md5 = (out / "MD5SUMS").read_text(encoding="utf-8").splitlines()
    assert [ln.split("  ")[1] for ln in md5] == ["table.csv", "summary.json"]
    assert all(not ln.split("  ")[1].startswith("./") for ln in md5)


# --------------------------------------------------------------------------- #
# --dedup-liq(2026-09-17、L-192 の行 1)
# --------------------------------------------------------------------------- #

def test_dedup_liq_drops_only_all_column_duplicates(tmp_path: Path):
    """`--dedup-liq` は**全 10 列一致**の行だけを 1 件にする。既定は落とさない。"""
    root = tmp_path / "data"
    for day, rows in AGG_ROWS.items():
        _write_zip(
            mod.agg_path(root, day),
            f"{mod.SYMBOL}-aggTrades-{day}.csv",
            mod.AGG_NAMES,
            [(i, p, q, i, i, t, "true") for i, (t, p, q) in enumerate(rows, start=1)],
        )
    a, b = LIQ_ROWS[0], LIQ_ROWS[1]
    c = (a[0], a[1], "MARKET") + a[3:]          # order_type だけ違う -> 残る
    _write_zip(
        mod.liq_path(root, DAY),
        f"{mod.SYMBOL}-liquidationSnapshot-{DAY}.csv",
        mod.LIQ_NAMES,
        [a, a, b, b, b, b, c],                  # 多重度 2 / 4 / 1
    )
    raw = mod.load_liquidations(mod.liq_path(root, DAY))
    uniq = mod.load_liquidations(mod.liq_path(root, DAY), dedup=True)
    assert len(raw) == 7
    assert len(uniq) == 3

    rows_raw, note_raw = mod.process_day(DAY, root, 24.0, 0.1, seed=1)
    rows_ded, note_ded = mod.process_day(DAY, root, 24.0, 0.1, seed=1, dedup_liq=True)
    assert note_raw["dedup_liq"] is False and note_ded["dedup_liq"] is True
    # liq_rows_in_file は前の走行と比べられるように一意化**前**の行数のまま
    assert note_raw["liq_rows_in_file"] == note_ded["liq_rows_in_file"] == 7
    assert note_raw["liq_rows_used"] == 7 and note_ded["liq_rows_used"] == 3
    assert len([r for r in rows_raw if r["kind"] == "liq"]) == 7
    assert len([r for r in rows_ded if r["kind"] == "liq"]) == 3


def test_dedup_liq_does_not_change_the_bundle_first_rows(tmp_path: Path):
    """束ねるときは、一意化しても『束の最初の 1 件』の中身が変わらない。

    重複行は同一 ms なので束の境界にも最初の行にも効かない。変わるのは
    `bundle_n_events`(一意化後は `bundle_n_events_dedup` と同じ値になる)だけ。
    """
    root = tmp_path / "data"
    for day, rows in AGG_ROWS.items():
        _write_zip(
            mod.agg_path(root, day),
            f"{mod.SYMBOL}-aggTrades-{day}.csv",
            mod.AGG_NAMES,
            [(i, p, q, i, i, t, "true") for i, (t, p, q) in enumerate(rows, start=1)],
        )
    doubled = [r for r in LIQ_ROWS for _ in range(2)]
    doubled.sort(key=lambda r: r[0])
    _write_zip(
        mod.liq_path(root, DAY),
        f"{mod.SYMBOL}-liquidationSnapshot-{DAY}.csv",
        mod.LIQ_NAMES,
        doubled,
    )
    raw, n_raw = mod.process_day(DAY, root, 24.0, 0.1, seed=1, bundle_gap_ms=60_000)
    ded, n_ded = mod.process_day(
        DAY, root, 24.0, 0.1, seed=1, bundle_gap_ms=60_000, dedup_liq=True
    )
    assert n_raw["bundles_in_file"] == n_ded["bundles_in_file"]
    lr = [r for r in raw if r["kind"] == "liq"]
    ld = [r for r in ded if r["kind"] == "liq"]
    assert len(lr) == len(ld)
    for x, y in zip(lr, ld):
        for col in ("time_ms", "side", "p_liq", "p0", "bin_pct", "dist_node_bp",
                    "dist_gap_bp", "dist_vwap_bp", "n_bins", "total_qty"):
            assert x[col] == y[col], col
        assert x["bundle_n_events"] == 2 * y["bundle_n_events"]
        assert y["bundle_n_events"] == y["bundle_n_events_dedup"]
        assert x["bundle_n_events_dedup"] == y["bundle_n_events_dedup"]
