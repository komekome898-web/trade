"""`scripts/o3c_signal_explore5.py`(清算を起点とした値動きの探索段 5)の試験。

**測るもの**(委任文【テスト】(1)〜(8))
  1. プリント数 53,398(472 日、全列一致の重複除去後)と対象 456 日。
  2. H0 診断「最後」の r(60) が探索段 4 の gap 60 清算 全体 −6.800366 と
     小数 4 桁で一致(**起点の約定の時刻 t₀ から h を測った列 `r_t0`**。
     設計の訂正 2026-09-20 でこれが**主**になった)。
  2'. 主の表 H1〜H6 の r が t₀ 基準の列 `r_t0_h` から作られており、
     `ts` 基準の列 `r_h` は H0 の「診断(束の位置)」「起点の取り方」の
     **併記**の列にしか出ない。
  3. 層の列が未来を使わない:
     (a) t₀(p₀ の約定の時刻)より後の約定・清算を消した入力で作り直しても同じ値、
     (b) m・d・付け直した属性は `ts` 以後を消した入力でも同じ値(k は対象外)、
     (c) 合成データで p₀ より後の約定の価格を変えても層の列が変わらない。
  4. 対照 (c') の帯・重なり・置換なし・処理順。
  5. すべての表に中央値の列がある。
  6. `paper_logs/` を開かない(探索段 4 と同じモック)。
  7. 出力に判定語が 1 つも無い。
  8. 表の行数。
"""
from __future__ import annotations

import builtins
import csv
import gzip
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_explore5", ROOT / "scripts" / "o3c_signal_explore5.py")
ex5 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ex5)
ex4 = ex5.ex4
ex3 = ex5.ex3
ex2 = ex5.ex2
base = ex5.base

RUNS_DIR = ROOT / "backtest_data" / "o3c_reaction_20260918_full"
DATA_ROOT = ROOT / "backtest_data" / "binance_cm_o3c_20260913"
MAIN_TABLE = RUNS_DIR / "gap60_w8" / "table.csv"
LIQ_DIR = DATA_ROOT / "liquidationSnapshot" / base.SYMBOL
FULL_OUT = ROOT / "backtest_data" / "o3c_signal_explore5_20260920"
EX4_OUT = ROOT / "backtest_data" / "o3c_signal_explore4_20260920"

have_data = MAIN_TABLE.exists() and (DATA_ROOT / "aggTrades").exists()
needs_data = pytest.mark.skipif(not have_data, reason="1 周目の表か公開アーカイブが無い")

N_SMOKE_DAYS = 3

# 委任文【テスト】(8) と設計 §6 の行数
EXPECTED_ROWS = {
    "h0_selfcheck.csv": 103,       # 設計は「約 40 行 + 診断 21 行」。実装の数え直し
    "h1_all_prints.csv": 7,        # h 7
    "h2_premove.csv": 140,         # T 2 × m 10 分位 × h 7
    "h3_impact_premove.csv": 36,   # k 4 群 × m 3 × h 3
    "h4_control.csv": 60,          # T 2 × m 10 分位 × h 3
    "h5_density.csv": 27,          # d 3 群 × m 3 × h 3
    "h6_attributes.csv": 162,      # 18 群(9 + 付け直せた属性 3 × 3)× m 3 × h 3
}
EXPLORE4_R60 = -6.800366

# H0 の 2 つの列(主 = t₀ 基準、併記 = ts 基準。設計の訂正 2026-09-20)
R_MAIN_COL_H0 = "r(t₀ 基準・主)平均"
R_ALT_COL_H0 = "r(ts 基準・併記)平均"


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


@pytest.fixture(scope="module")
def smoke(tmp_path_factory):
    """先頭 3 日だけを実データで走らせた出力(重いので 1 度だけ)。"""
    if not have_data:
        pytest.skip("1 周目の表か公開アーカイブが無い")
    out = tmp_path_factory.mktemp("explore5")
    rc = ex5.main([
        "--runs-dir", str(RUNS_DIR), "--data-root", str(DATA_ROOT),
        "--out", str(out), "--limit-days", str(N_SMOKE_DAYS),
        "--progress-every", "1000",
    ])
    assert rc == 0
    return out


@pytest.fixture(scope="module")
def prints_all():
    if not have_data:
        pytest.skip("公開アーカイブが無い")
    return ex5.load_prints(LIQ_DIR)


def _rows(path: Path, kind=None) -> list:
    with gzip.open(path, "rt", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [r for r in rows if kind is None or r["kind"] == kind]


def _csv(path: Path) -> list:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# (1) プリント数
# ---------------------------------------------------------------------------
@needs_data
def test_print_count_is_53398_over_472_days(prints_all):
    """`docs/DATA.md` §2 の実測: 472 日・106,822 行 -> 全列一致で一意 53,398 件。"""
    assert prints_all.n_files == 472
    assert prints_all.raw_rows == 106_822
    assert prints_all.uniq_rows == 53_398
    assert prints_all.n == 53_398


@needs_data
def test_target_days_are_the_explore4_456_days():
    days = ex2.RunTable(RUNS_DIR / "gap60_w8").days()
    assert len(days) == 456
    p = EX4_OUT / "summary.json"
    if p.exists():
        s = json.loads(p.read_text())
        assert s["日数"] == len(days)
        assert s["欠けた日"] == ex5.calendar_gaps(days)


# ---------------------------------------------------------------------------
# (2) H0 診断「最後」が探索段 4 と一致する
# ---------------------------------------------------------------------------
@needs_data
def test_last_print_matches_explore4_row_by_row(smoke):
    """束の終端 = その束の最後のプリントの直後の約定なので、行ごとに同じ量になる。"""
    new = _rows(smoke / "rows_prints.csv.gz", ex5.KIND_PRINT)
    days = {r["day"] for r in new}
    assert len(days) == N_SMOKE_DAYS
    old = {r["cascade_id"]: r for r in _rows(EX4_OUT / "rows_gap60.csv.gz", "liq")
           if r["day"] in days}
    assert len(old) > 0
    last = [r for r in new
            if r["bundle_pos"] == ex5.POS_LAST and r["bundle_id"] in old]
    assert len(last) == len(old), (len(last), len(old))
    for r in last:
        o = old[r["bundle_id"]]
        # 起点そのもの(t₀ と p₀)が探索段 4 の終端と同じ点
        assert r["t0_ms"] == o["t_end_ms"], r["print_id"]
        for h in ex5.HORIZONS_SEC:
            a, b = _f(r[f"r_t0_{h}"]), _f(o[f"r_end_{h}"])
            assert (a is None) == (b is None), (r["print_id"], h)
            if a is not None:
                assert abs(a - b) < 1e-6, (r["print_id"], h, a, b)


def test_last_print_r60_matches_explore4_full_run():
    """本走行があれば「最後」の r_t0(60) の平均が −6.800366 と小数 4 桁で一致。

    設計の訂正(2026-09-20)で t₀ 基準が**主**になったので、H0 診断の主の列
    `r(t₀ 基準・主)平均` を見る。`ts` 基準は同じ行の併記の列にある。
    """
    p = FULL_OUT / "summary.json"
    if not p.exists():
        pytest.skip("本走行の出力が無い")
    s = json.loads(p.read_text())
    assert s["主の表の r(h) の基準"].startswith("t₀")
    got = s["探索段 4 との突き合わせ"]["この段"]["t₀ 基準"]["平均"]
    assert round(got, 4) == round(EXPLORE4_R60, 4), got
    rows = _csv(FULL_OUT / "h0_selfcheck.csv")
    hit = [r for r in rows if r["区分"] == "診断(束の位置)"
           and r["群"] == ex5.POS_LAST and r["量"].endswith("h=60")]
    assert len(hit) == 1
    assert round(float(hit[0][R_MAIN_COL_H0]), 4) == round(EXPLORE4_R60, 4)
    # 併記の ts 基準は小数 4 桁で一致しない(2 つの列が入れ替わっていないこと)
    assert round(float(hit[0][R_ALT_COL_H0]), 4) != round(EXPLORE4_R60, 4)


@needs_data
def test_main_tables_use_the_t0_origin(smoke):
    """主の表 H1 の r は t₀ 基準の列 `r_t0_h` から作られている(設計の訂正)。"""
    rows = _rows(smoke / "rows_prints.csv.gz", ex5.KIND_PRINT)
    h1 = {int(r["h(秒)"]): r for r in _csv(smoke / "h1_all_prints.csv")}
    n_diff = 0
    for h in ex5.HORIZONS_SEC:
        v_t0 = [x for x in (_f(r[f"r_t0_{h}"]) for r in rows) if x is not None]
        v_ts = [x for x in (_f(r[f"r_{h}"]) for r in rows) if x is not None]
        m_t0 = sum(v_t0) / len(v_t0)
        m_ts = sum(v_ts) / len(v_ts)
        got = float(h1[h]["r 平均(bp)"])
        assert abs(got - m_t0) < 1e-6, (h, got, m_t0)
        if abs(m_t0 - m_ts) > 1e-5:
            n_diff += 1
            assert abs(got - m_ts) > 1e-6, (h, got, m_ts)
    assert n_diff > 0, "2 つの起点が 1 本も違わない(取り違えを検出できていない)"


@needs_data
def test_ts_origin_appears_only_in_the_h0_side_by_side_rows(smoke):
    """`ts` 基準は H0 の併記の列だけ。主の表 H1〜H6 の列名に `ts 基準` が無い。"""
    h0 = _csv(smoke / "h0_selfcheck.csv")
    cols0 = set(h0[0])
    assert R_MAIN_COL_H0 in cols0 and R_ALT_COL_H0 in cols0
    marked = [r for r in h0 if r[R_ALT_COL_H0] not in ("", ex5.DASH)]
    assert marked, "併記の行が無い"
    assert {r["区分"] for r in marked} == {"診断(束の位置)", "起点の取り方"}
    for name in EXPECTED_ROWS:
        if name == "h0_selfcheck.csv":
            continue
        with open(smoke / name, newline="") as fh:
            cols = csv.DictReader(fh).fieldnames or []
        assert not [c for c in cols if "ts 基準" in c], name


@needs_data
def test_h0_missing_r_rows_count_the_main_column(smoke):
    """H0 の「r(h) が引けない」は主の列(t₀ 基準)を数えている。"""
    rows = _rows(smoke / "rows_prints.csv.gz", ex5.KIND_PRINT)
    h0 = _csv(smoke / "h0_selfcheck.csv")
    hit = [r for r in h0 if r["区分"] == "欠測" and "r(h)" in r["量"]]
    assert len(hit) == len(ex5.HORIZONS_SEC)
    for r in hit:
        assert "t₀ 基準" in r["量"], r["量"]
        h = int(r["量"].rsplit("h=", 1)[1])
        want = sum(1 for x in rows if _f(x[f"r_t0_{h}"]) is None)
        assert int(r["n"]) == want, (h, r["n"], want)


# ---------------------------------------------------------------------------
# (3) 層の列が未来を使わない
# ---------------------------------------------------------------------------
LAYER_KEYS_T0 = (["k", "d", "bin_pct", "dist_node_bp", "implied_leverage"]
                 + [f"m_{T}" for T in ex5.T_MAIN])
LAYER_KEYS_TS = (["d", "bin_pct", "dist_node_bp", "implied_leverage"]
                 + [f"m_{T}" for T in ex5.T_MAIN])


def _eq(a, b) -> bool:
    a, b = float(a), float(b)
    if math.isnan(a) and math.isnan(b):
        return True
    return a == b


def _truncate_buckets(buckets: dict, t: int) -> dict:
    out = dict(buckets)
    m = np.asarray(buckets["t_ms"]) <= t
    for k in ("t_ms", "delta", "vwap", "buy_share", "vwap_buy", "vwap_sell"):
        out[k] = np.asarray(buckets[k])[m]
    ta = np.asarray(buckets["t_all"])
    out["t_all"] = ta[ta <= t]
    return out


@needs_data
def test_layers_do_not_use_data_after_t0():
    """(a) t₀ より後の約定・清算を消しても層の列が変わらない(p₀ は残す)。"""
    day = ex2.RunTable(RUNS_DIR / "gap60_w8").days()[0]
    prints = ex5.load_prints(LIQ_DIR)
    cache: dict = {}
    times, prices, qtys, _miss, _need = ex5.load_window5(
        DATA_ROOT, day, cache, int(ex5.W_HOURS * 3600 * 1000) + ex5.STALENESS_MS,
        max(ex5.HORIZONS_SEC) * 1000 + ex5.STALENESS_MS)
    buckets, cov, _mm = ex5.build_oi_context(DATA_ROOT, DATA_ROOT, day, cache, {})
    step = base.log_step(ex5.BIN_PCT)
    wms = int(ex5.W_HOURS * 3600 * 1000)
    sel_all = prints.by_day[day]
    assert sel_all.size > 5
    sel_all = sel_all[:20]
    full = ex5.compute_layers(times, prices, qtys, prints.ts, prints.side,
                              prints.price, sel_all, buckets=buckets, cov=cov,
                              step=step, window_ms=wms)
    n_checked = 0
    for pos, i in enumerate(sel_all.tolist()):
        t0 = int(full["t0_ms"][pos])
        assert t0 >= int(prints.ts[i])
        mt = times <= t0
        mp = prints.ts <= t0
        idx_map = np.flatnonzero(mp)
        j = int(np.flatnonzero(idx_map == i)[0])
        cut = ex5.compute_layers(
            times[mt], prices[mt], qtys[mt], prints.ts[mp], prints.side[mp],
            prints.price[mp], np.array([j]),
            buckets=_truncate_buckets(buckets, t0), cov=cov, step=step,
            window_ms=wms)
        for key in LAYER_KEYS_T0:
            assert _eq(full[key][pos], cut[key][0]), (i, key, full[key][pos],
                                                      cut[key][0])
        n_checked += 1
    assert n_checked == sel_all.size


@needs_data
def test_layers_from_ts_only_ignore_everything_at_or_after_ts():
    """(b) `ts` 以後の約定・清算を消しても m・d・属性は同じ(k は対象外)。"""
    day = ex2.RunTable(RUNS_DIR / "gap60_w8").days()[0]
    prints = ex5.load_prints(LIQ_DIR)
    cache: dict = {}
    times, prices, qtys, _miss, _need = ex5.load_window5(
        DATA_ROOT, day, cache, int(ex5.W_HOURS * 3600 * 1000) + ex5.STALENESS_MS,
        max(ex5.HORIZONS_SEC) * 1000 + ex5.STALENESS_MS)
    buckets, cov, _mm = ex5.build_oi_context(DATA_ROOT, DATA_ROOT, day, cache, {})
    step = base.log_step(ex5.BIN_PCT)
    wms = int(ex5.W_HOURS * 3600 * 1000)
    sel_all = prints.by_day[day][:20]
    full = ex5.compute_layers(times, prices, qtys, prints.ts, prints.side,
                              prints.price, sel_all, buckets=buckets, cov=cov,
                              step=step, window_ms=wms)
    for pos, i in enumerate(sel_all.tolist()):
        ts = int(prints.ts[i])
        mt = times < ts
        # プリント自身は残す(入力の一部)。他のプリントは `ts` より前だけ。
        mp = (prints.ts < ts) | (np.arange(prints.n) == i)
        idx_map = np.flatnonzero(mp)
        j = int(np.flatnonzero(idx_map == i)[0])
        cut = ex5.compute_layers(
            times[mt], prices[mt], qtys[mt], prints.ts[mp], prints.side[mp],
            prints.price[mp], np.array([j]),
            buckets=_truncate_buckets(buckets, ts - 1), cov=cov, step=step,
            window_ms=wms)
        for key in LAYER_KEYS_TS:
            assert _eq(full[key][pos], cut[key][0]), (i, key, full[key][pos],
                                                      cut[key][0])


def _synthetic():
    """合成データ: 1 ms 刻みの約定 2,000 点と、同じ側のプリント 3 件。"""
    t0 = ex5.day_start_ms("2024-01-02") + 3_600_000
    times = t0 + np.arange(0, 2_000_000, 1_000, dtype=np.int64)
    prices = 30_000.0 + np.arange(times.size) * 0.5
    qtys = np.ones(times.size)
    pr_ts = np.array([t0 + 900_000, t0 + 1_000_500, t0 + 1_200_000],
                     dtype=np.int64)
    pr_side = np.array(["SELL", "SELL", "SELL"], dtype=object)
    pr_price = np.array([30_450.0, 30_500.0, 30_600.0])
    return times, prices, qtys, pr_ts, pr_side, pr_price


def test_layers_unchanged_when_prices_after_p0_change():
    """(c) 合成データで p₀ より後の約定の価格を変えても層の列が変わらない。"""
    times, prices, qtys, pr_ts, pr_side, pr_price = _synthetic()
    step = base.log_step(ex5.BIN_PCT)
    wms = 8 * 3600 * 1000
    sel = np.arange(pr_ts.size)
    a = ex5.compute_layers(times, prices, qtys, pr_ts, pr_side, pr_price, sel,
                           step=step, window_ms=wms)
    for pos in range(pr_ts.size):
        t0 = int(a["t0_ms"][pos])
        after = times > t0
        assert bool(after.any())
        changed = prices.copy()
        changed[after] = changed[after] * 1.05 + 7.0
        b = ex5.compute_layers(times, changed, qtys, pr_ts, pr_side, pr_price,
                               np.array([pos]), step=step, window_ms=wms)
        for key in (["k", "d", "bin_pct", "dist_node_bp"]
                    + [f"m_{T}" for T in ex5.T_MAIN]):
            assert _eq(a[key][pos], b[key][0]), (pos, key)
        # r(h) は起点より後を見る量なので、**変わる**(層ではない)
        fa = ex5.forward_moves(times, prices, a["ts"][pos:pos + 1],
                               a["t0_ms"][pos:pos + 1], a["p0"][pos:pos + 1],
                               a["ok_p0"][pos:pos + 1], a["sign"][pos:pos + 1])
        fb = ex5.forward_moves(times, changed, b["ts"], b["t0_ms"], b["p0"],
                               b["ok_p0"], b["sign"])
        assert not _eq(fa["r_900"][0], fb["r_900"][0]), pos


def test_density_counts_only_the_past_five_minutes_same_side():
    times, prices, qtys, pr_ts, pr_side, pr_price = _synthetic()
    out = ex5.compute_layers(times, prices, qtys, pr_ts, pr_side, pr_price,
                             np.arange(3))
    # 1 件目 = 直前 5 分に同じ側なし / 2 件目 = 100.5 秒前の 1 件 / 3 件目 = 2 件
    assert list(out["d"]) == [0.0, 1.0, 2.0]
    # 反対側は数えない
    side2 = np.array(["SELL", "BUY", "SELL"], dtype=object)
    out2 = ex5.compute_layers(times, prices, qtys, pr_ts, side2, pr_price,
                              np.arange(3))
    assert list(out2["d"]) == [0.0, 0.0, 1.0]


def test_coverage_is_decided_from_the_past_only():
    """`covered_before` は `ts` 以前の metrics 行だけで被覆を決める。"""
    b = ex5.oid.BUCKET_MS
    t_all = np.array([0, b, 2 * b, 10 * b, 11 * b, 12 * b], dtype=np.int64)
    # `ts` が 2b のときの区間の先頭は 0(末尾から遡る 1 周目の定義なら 10b)
    got = ex5.covered_before(t_all, np.array([2 * b]), 2 * b)
    assert bool(got[0]) is True
    assert ex5.oid.coverage_start_ms(t_all) == 10 * b
    # 窓が区間の先頭より前まで伸びると被覆の外
    assert bool(ex5.covered_before(t_all, np.array([11 * b]), 3 * b)[0]) is False
    assert bool(ex5.covered_before(t_all, np.array([12 * b]), 2 * b)[0]) is True


# ---------------------------------------------------------------------------
# (4) 対照 (c')
# ---------------------------------------------------------------------------
@needs_data
def test_control_c_band_no_overlap_no_replacement_and_order(smoke):
    ctrl = _rows(smoke / "rows_prints.csv.gz", ex5.KIND_C)
    pr = {r["print_id"]: r for r in
          _rows(smoke / "rows_prints.csv.gz", ex5.KIND_PRINT)}
    assert ctrl
    notes = json.loads((smoke / "summary.json").read_text())
    cuts = {int(k): np.array(v) for k, v in notes["m の帯の切り値"].items()}
    taken: dict = {}
    order: dict = {}
    for r in ctrl:
        T = int(r["ctrl_T"])
        c_t = _f(r["c_t"])
        m_p = _f(pr[r["matched_print_id"]][f"m_{T}"])
        # 帯が同じ
        assert (int(ex5.band_of_m(c_t, cuts[T]))
                == int(ex5.band_of_m(m_p, cuts[T]))), r["print_id"]
        t = int(r["ctrl_t_ms"])
        lo, hi = t - T * 1000, t + ex5.CTRL_WINDOW_MS
        # 置換なし(同じ T のあいだで区間が重ならない)
        for s, e in taken.setdefault(T, []):
            assert not (max(lo, s) <= min(hi, e)), (T, t, s, e)
        taken[T].append((lo, hi))
        # 処理順: 日の昇順 -> ts の昇順
        key = (r["day"], int(pr[r["matched_print_id"]]["ts_ms"]))
        assert key >= order.get(T, ("", -1)), (T, key, order.get(T))
        order[T] = key


@needs_data
def test_control_c_interval_never_contains_a_print(smoke, prints_all):
    """候補の区間 [t − T 秒, t + 900 秒] にはどの側のプリントも無い。"""
    ctrl = _rows(smoke / "rows_prints.csv.gz", ex5.KIND_C)
    ts = prints_all.ts
    for r in ctrl:
        t = int(r["ctrl_t_ms"])
        T = int(r["ctrl_T"])
        lo, hi = t - T * 1000, t + ex5.CTRL_WINDOW_MS
        i = int(np.searchsorted(ts, lo, side="left"))
        assert not (i < ts.size and ts[i] <= hi), (t, T, int(ts[i]))


def test_block_marks_exactly_the_overlapping_candidates():
    d0 = ex5.day_start_ms("2024-02-03")
    allowed = np.ones(ex5.GRID_N, dtype=bool)
    a = d0 + 3_600_000
    ex5._block(allowed, a, a, 60_000, d0)
    grid = d0 + np.arange(ex5.GRID_N, dtype=np.int64) * ex5.GRID_STEP_MS
    want = ~((grid - 60_000 <= a) & (a <= grid + ex5.CTRL_WINDOW_MS))
    assert np.array_equal(allowed, want)


# ---------------------------------------------------------------------------
# (5) 中央値の列 / 母数の列
# ---------------------------------------------------------------------------
@needs_data
def test_every_table_has_a_median_column(smoke):
    for name in EXPECTED_ROWS:
        with open(smoke / name, newline="") as fh:
            cols = csv.DictReader(fh).fieldnames or []
        assert any("中央値" in c for c in cols), name


@needs_data
def test_every_share_column_has_a_denominator(smoke):
    pairs = {"r < 0 の割合": "r < 0 の母数"}
    for sec in ex5.NEXT_SEC:
        pairs[f"同じ側の次の清算 {sec} 秒以内の割合"] = \
            f"同じ側の次の清算 {sec} 秒以内の母数"
    for name in EXPECTED_ROWS:
        with open(smoke / name, newline="") as fh:
            cols = set(csv.DictReader(fh).fieldnames or [])
        for share, denom in pairs.items():
            if share in cols:
                assert denom in cols, (name, share)
        if "割合" in cols:
            assert "母数" in cols, name


@needs_data
def test_h2_carries_k_and_h1_carries_control_b(smoke):
    h2 = _csv(smoke / "h2_premove.csv")
    assert {"k 平均", "k 中央値"} <= set(h2[0])
    h1 = _csv(smoke / "h1_all_prints.csv")
    assert "対照 (b) 日集約 平均(bp)" in h1[0]


# ---------------------------------------------------------------------------
# (6) `paper_logs/` を開かない
# ---------------------------------------------------------------------------
@needs_data
def test_does_not_touch_paper_logs(tmp_path, monkeypatch):
    touched: list = []
    real_open = builtins.open
    real_glob = Path.glob
    real_iterdir = Path.iterdir
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

    def guarded_glob(self, pattern, *a, **k):
        note(self)
        return real_glob(self, pattern, *a, **k)

    def guarded_iterdir(self, *a, **k):
        note(self)
        return real_iterdir(self, *a, **k)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(gzip, "open", guarded_gzopen)
    monkeypatch.setattr(Path, "glob", guarded_glob)
    monkeypatch.setattr(Path, "iterdir", guarded_iterdir)
    rc = ex5.main([
        "--runs-dir", str(RUNS_DIR), "--data-root", str(DATA_ROOT),
        "--out", str(tmp_path / "o"), "--limit-days", "2",
        "--progress-every", "1000",
    ])
    assert rc == 0
    assert touched == []
    src = (ROOT / "scripts" / "o3c_signal_explore5.py").read_text().splitlines()
    hits = [ln for ln in src if "paper_logs" in ln]
    assert hits and all(ln.lstrip().startswith(("#", "*", '"""')) or "開かない" in ln
                        for ln in hits), hits


# ---------------------------------------------------------------------------
# (7) 判定語なし / (8) 表の行数
# ---------------------------------------------------------------------------
@needs_data
def test_no_verdict_words_in_outputs(smoke):
    for name in list(EXPECTED_ROWS) + ["tables.md", "summary.json"]:
        txt = (smoke / name).read_text()
        for w in ex5.BANNED_WORDS:
            assert w not in txt, (name, w)


@needs_data
def test_table_row_counts(smoke):
    for name, want in EXPECTED_ROWS.items():
        assert len(_csv(smoke / name)) == want, name
    total = sum(EXPECTED_ROWS.values())
    assert total == 535
    assert total - EXPECTED_ROWS["h0_selfcheck.csv"] == 432
    summ = json.loads((smoke / "summary.json").read_text())
    assert summ["表の行数"]["合計"] == total
    assert summ["表の行数"]["H0 を除く合計"] == 432
    assert summ["tables.md の数値セル数"] > 0


@needs_data
def test_chunk_files_are_removed(smoke):
    assert not (smoke / "chunks1").exists()
    assert not (smoke / "chunks2").exists()


@needs_data
def test_h0_has_the_21_bundle_position_diagnostic_rows(smoke):
    rows = _csv(smoke / "h0_selfcheck.csv")
    diag = [r for r in rows if r["区分"] == "診断(束の位置)"]
    assert len(diag) == 21
    assert sorted({r["群"] for r in diag}) == sorted(ex5.POSITIONS)


# ---------------------------------------------------------------------------
# 群の作り方・切り方
# ---------------------------------------------------------------------------
def test_m_bands_are_ten_with_open_ends():
    cuts = ex5.band_cuts_m(np.linspace(-10, 10, 1001))
    assert cuts.size == ex5.N_BANDS - 1
    assert ex5.band_bounds(cuts, 1)[0] == -math.inf
    assert ex5.band_bounds(cuts, ex5.N_BANDS)[1] == math.inf
    assert int(ex5.band_of_m(-1e9, cuts)) == 1
    assert int(ex5.band_of_m(1e9, cuts)) == ex5.N_BANDS
    assert int(ex5.band_of_m(float("nan"), cuts)) == -1


def test_k_groups_are_four():
    blk = {"k": np.array([-3.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0,
                          float("nan")])}
    pos = blk["k"][np.isfinite(blk["k"]) & (blk["k"] > 0)]
    groups = ex5.k_group_masks(blk, ex5.tertile_cuts(pos))
    assert len(groups) == 4
    assert groups[0][0].startswith("K0")
    counts = [int(m.sum()) for _l, m in groups]
    assert counts[0] == 2               # k = −3 と k = 0
    assert sum(counts) == 8             # NaN は入らない
    # 群は重ならない
    stack = np.vstack([m for _l, m in groups]).sum(axis=0)
    assert stack.max() <= 1


def test_d_groups_are_zero_one_two_and_three_plus():
    blk = {"d": np.array([0.0, 1.0, 2.0, 3.0, 9.0])}
    labels = [lb for lb, _m in ex5.d_group_masks(blk)]
    assert labels == ["d = 0", "d = 1〜2", "d ≥ 3"]
    counts = [int(m.sum()) for _l, m in ex5.d_group_masks(blk)]
    assert counts == [1, 2, 2]


def test_single_print_bundle_counts_as_both_first_and_last():
    pos = np.array([ex5.POS_LAST, ex5.POS_FIRST, ex5.POS_MID, ex5.POS_LAST],
                   dtype=object)
    single = np.array([1.0, 0.0, 0.0, 0.0])
    assert list(ex5.position_mask(pos, single, ex5.POS_FIRST)) == [True, True,
                                                                   False, False]
    assert list(ex5.position_mask(pos, single, ex5.POS_LAST)) == [True, False,
                                                                  False, True]
    assert list(ex5.position_mask(pos, single, ex5.POS_MID)) == [False, False,
                                                                 True, False]


def test_numeric_cell_counter():
    md = ("| a | b |\n|---|---|\n| 1 | x |\n| 2.5 | 3 |\n\n"
          "| c |\n|---|\n| — |\n| 4 |\n")
    assert ex5.count_numeric_cells(md) == 4


# ---------------------------------------------------------------------------
# SE と日等重み(探索段 2・3・4 と同じ関数)
# ---------------------------------------------------------------------------
def test_se_helpers_are_the_earlier_functions():
    assert ex5.mean_se_cluster is ex2.mean_se_cluster
    assert ex5.day_equal_weight_mean is ex3.day_equal_weight_mean
    assert ex5.band_of_m is ex4.band_of_m
    rng = np.random.default_rng(5)
    v = rng.normal(size=300)
    days = np.array([f"d{i % 9}" for i in range(300)], dtype=object)
    assert ex5.mean_se_cluster(v, days) == ex2.mean_se_cluster(v, days)


def test_sign_convention_is_the_same_as_explore_1_to_4():
    assert ex5.REACT_SIGN == {"SELL": -1.0, "BUY": 1.0}
    assert ex5.STALENESS_MS == 300_000
    assert ex5.T_MAIN == (10, 60)
    assert ex5.HORIZONS_SEC == (1, 5, 10, 30, 60, 300, 900)
