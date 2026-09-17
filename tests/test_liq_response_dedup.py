"""`liquidationSnapshot` の全列一致の重複行を 1 件にする一意化(2026-09-17)。

経緯: Binance COIN-M の `liquidationSnapshot` は 1 件の清算が全列まったく同じ行として
2 回現れる(全 472 日で 106,822 行 → 一意 53,398 行、多重度 2 が 53,385 群 / 4 が 13 群。
`docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md` §2.0 の実測)。
`build_cascades` の `n_events` / `total_size` は一意化しないと 2 倍になる。
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pytest

from bot.research.liq_response import (
    build_cascades,
    dedup_exact_rows,
    load_binance_cm_liquidations,
    load_binance_cm_liquidations_with_dedup_stats,
)

HEADER = [
    "time", "side", "order_type", "time_in_force", "original_quantity",
    "price", "average_price", "order_status", "last_fill_quantity",
    "accumulated_fill_quantity",
]


def _row(ts: int, side: str = "SELL", qty: str = "10", avg: str = "30000.0",
         order_type: str = "LIMIT") -> list[str]:
    return [str(ts), side, order_type, "IOC", qty, "29990.0", avg, "FILLED", qty, qty]


def _write_zip(dirpath: Path, day: str, rows: list[list[str]]) -> Path:
    dirpath.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADER)
    for r in rows:
        w.writerow(r)
    zpath = dirpath / f"BTCUSD_PERP-liquidationSnapshot-{day}.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr(f"BTCUSD_PERP-liquidationSnapshot-{day}.csv", buf.getvalue())
    return zpath


# --------------------------------------------------------------------------- #
# dedup_exact_rows それ自体
# --------------------------------------------------------------------------- #

def test_dedup_mixes_multiplicity_2_and_4_and_singletons():
    """重複 2・4・非重複の混在で件数が合う。"""
    rows = (
        [("a", 1)] * 2      # 多重度 2
        + [("b", 2)] * 4    # 多重度 4
        + [("c", 3)]        # 非重複
        + [("d", 4)] * 2    # 多重度 2
        + [("e", 5)]        # 非重複
    )
    out, stats = dedup_exact_rows(rows)
    assert [r[0] for r in out] == ["a", "b", "c", "d", "e"]
    assert stats.n_in == 10
    assert stats.n_out == 5
    assert stats.n_dropped == 5
    assert stats.multiplicity == {1: 2, 2: 2, 4: 1}
    # 恒等式: 入力 = Σ(多重度 × 群数) / 出力 = Σ 群数
    assert sum(k * v for k, v in stats.multiplicity.items()) == stats.n_in
    assert sum(stats.multiplicity.values()) == stats.n_out
    assert stats.drop_rate == pytest.approx(0.5)


def test_dedup_keeps_row_that_differs_in_one_column():
    """列が 1 つでも違う行は残る。"""
    base = _row(1_000)
    for i in range(len(base)):
        other = list(base)
        other[i] = other[i] + "X"
        out, stats = dedup_exact_rows([tuple(base), tuple(base), tuple(other)])
        assert stats.n_in == 3 and stats.n_out == 2, f"列 {HEADER[i]} で潰れた"
        assert stats.multiplicity == {1: 1, 2: 1}
        assert tuple(other) in out


def test_dedup_preserves_first_occurrence_order():
    out, _ = dedup_exact_rows([("b", 1), ("a", 2), ("b", 1), ("c", 3)])
    assert out == [("b", 1), ("a", 2), ("c", 3)]


def test_dedup_on_empty_input_reports_nan_rate():
    out, stats = dedup_exact_rows([])
    assert out == []
    assert stats.n_in == 0 and stats.n_out == 0 and stats.multiplicity == {}
    assert stats.drop_rate != stats.drop_rate  # NaN。0.0 を返して「重複なし」に見せない


def test_dedup_key_argument_uses_only_that_key():
    pairs = [(("x",), "ev1"), (("x",), "ev2"), (("y",), "ev3")]
    out, stats = dedup_exact_rows(pairs, key=lambda p: p[0])
    assert [p[1] for p in out] == ["ev1", "ev3"]
    assert stats.multiplicity == {1: 1, 2: 1}


# --------------------------------------------------------------------------- #
# 読み出し層(実データと同じ形の zip)
# --------------------------------------------------------------------------- #

def test_loader_default_keeps_duplicates_and_dedup_true_drops_them(tmp_path):
    """既定(`dedup=False`)は従来どおり全行。`dedup=True` で全列一致だけ落ちる。"""
    root = tmp_path / "liquidationSnapshot" / "BTCUSD_PERP"
    _write_zip(root, "2023-06-25", [
        _row(1_000), _row(1_000),                       # 多重度 2
        _row(2_000, side="BUY"), _row(2_000, side="BUY"),
        _row(2_000, side="BUY"), _row(2_000, side="BUY"),  # 多重度 4
        _row(3_000, qty="7"),                            # 非重複
        _row(3_000, qty="7", order_type="MARKET"),       # 1 列だけ違う -> 残る
    ])
    raw = load_binance_cm_liquidations(root)
    assert len(raw) == 8
    uniq, stats = load_binance_cm_liquidations_with_dedup_stats(root)
    assert len(uniq) == 4
    assert stats.n_in == 8 and stats.n_out == 4
    assert stats.multiplicity == {1: 2, 2: 1, 4: 1}
    assert load_binance_cm_liquidations(root, dedup=True) == uniq
    assert [e.ts_ms for e in uniq] == [1_000, 2_000, 3_000, 3_000]


def test_loader_dedup_is_per_exact_row_not_per_timestamp(tmp_path):
    """同じ ms でも中身が違えば 2 件のまま残る(時刻で潰さない)。"""
    root = tmp_path / "liquidationSnapshot" / "BTCUSD_PERP"
    _write_zip(root, "2023-06-25", [
        _row(5_000, qty="1"), _row(5_000, qty="2"), _row(5_000, qty="2"),
    ])
    uniq, stats = load_binance_cm_liquidations_with_dedup_stats(root)
    assert stats.n_in == 3 and stats.n_out == 2
    assert sorted(e.qty for e in uniq) == [1.0, 2.0]


def test_build_cascades_n_events_halves_after_dedup(tmp_path):
    """一意化しないと `build_cascades` の件数・規模が 2 倍になる(束の切れ目は不変)。"""
    root = tmp_path / "liquidationSnapshot" / "BTCUSD_PERP"
    rows: list[list[str]] = []
    for ts in (1_000, 2_000, 3_000):          # 60 秒以内 -> 同じ束
        rows += [_row(ts, qty="4"), _row(ts, qty="4")]
    for ts in (200_000, 201_000):             # 60 秒超の空きの後 -> 次の束
        rows += [_row(ts, qty="4"), _row(ts, qty="4")]
    _write_zip(root, "2023-06-25", rows)

    raw = build_cascades(load_binance_cm_liquidations(root), "binance_cm")
    uniq = build_cascades(load_binance_cm_liquidations(root, dedup=True), "binance_cm")
    assert len(raw) == len(uniq) == 2                      # 束の切れ目は変わらない
    assert [c.n_events for c in raw] == [6, 4]
    assert [c.n_events for c in uniq] == [3, 2]
    assert [c.start_ms for c in raw] == [c.start_ms for c in uniq]
    assert [c.end_ms for c in raw] == [c.end_ms for c in uniq]
    for r, u in zip(raw, uniq):
        assert r.total_size == pytest.approx(2 * u.total_size)
