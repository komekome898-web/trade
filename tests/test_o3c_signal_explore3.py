"""`scripts/o3c_signal_explore3.py`(清算を起点とした値動きの探索段 3)の試験。

**測るもの**(委任文【テスト】(1)〜(7))
  1. r_end(60) の gap60 清算側が探索段 2 の Δ = 0・h = 60 と一致する
     (5 日分を実データで走らせて**行ごと**に一致。本走行があれば平均 −6.800 も見る)。
  2. 基準の約定の時刻 < `start_ms`。
  3. 3 区分(f > 1 / 0 ≤ f ≤ 1 / f < 0)の和が 1(sweep > 0 の束で)。
  4. sweep ≤ 0 の束は f が NaN で、数が `summary.json` に出る。
  5. 対照 (a) の c_t が相手の sweep と同じ分位帯に入り、区間が束と重ならず、
     取った区間どうしも重ならない(置換なし)。
  6. `paper_logs/` を開かない(探索段 2 と同じモック)。
  7. 日クラスタ SE が探索段 2 の式と一致する。
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

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_explore3", ROOT / "scripts" / "o3c_signal_explore3.py")
ex3 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ex3)
ex2 = ex3.ex2

RUNS_DIR = ROOT / "backtest_data" / "o3c_reaction_20260918_full"
DATA_ROOT = ROOT / "backtest_data" / "binance_cm_o3c_20260913"
BF_DIR = ROOT / "backtest_data" / "bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
MAIN_TABLE = RUNS_DIR / "gap60_w8" / "table.csv"
FULL_OUT = ROOT / "backtest_data" / "o3c_signal_explore3_20260920"
EX2_OUT = ROOT / "backtest_data" / "o3c_signal_explore2_20260919"

have_data = MAIN_TABLE.exists() and (DATA_ROOT / "aggTrades").exists()
needs_data = pytest.mark.skipif(not have_data, reason="1 周目の表か公開アーカイブが無い")

N_SMOKE_DAYS = 5


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


@pytest.fixture(scope="module")
def smoke(tmp_path_factory):
    """先頭 5 日だけを実データで走らせた出力(重いので 1 度だけ)。"""
    if not have_data:
        pytest.skip("1 周目の表か公開アーカイブが無い")
    out = tmp_path_factory.mktemp("explore3")
    rc = ex3.main([
        "--runs-dir", str(RUNS_DIR), "--data-root", str(DATA_ROOT),
        "--bitflyer-dir", str(BF_DIR), "--out", str(out),
        "--limit-days", str(N_SMOKE_DAYS), "--progress-every", "1000",
        "--skip-liq-dup",
    ])
    assert rc == 0
    return out


def _rows(path: Path, kind=None) -> list:
    with gzip.open(path, "rt", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [r for r in rows if kind is None or r["kind"] == kind]


# ---------------------------------------------------------------------------
# (1) r_end(60) が探索段 2 の Δ = 0・h = 60 と一致する
# ---------------------------------------------------------------------------
@needs_data
def test_r_end_60_matches_explore2_row_by_row(smoke):
    new = _rows(smoke / "rows_gap60.csv.gz", "liq")
    days = {r["day"] for r in new}
    assert len(days) == N_SMOKE_DAYS
    with open(MAIN_TABLE, newline="") as fh:
        old = {r["cascade_id"]: r for r in csv.DictReader(fh)
               if r["kind"] == "liq" and r["day"] in days}
    assert len(new) == len(old) > 0
    for r in new:
        o = old[r["cascade_id"]]
        a, b = _f(r["r_end_60"]), _f(o["bp_1m_reactdir"])
        assert (a is None) == (b is None), r["cascade_id"]
        if a is not None:
            assert abs(a - b) < 1e-3, (r["cascade_id"], a, b)
        # 終端は探索段 2 の Δ = 0 の起点(1 周目の `anchor_ts_ms`)と同じ点
        assert str(r["t_end_ms"]) == str(o["anchor_ts_ms"])


@needs_data
def test_r_end_60_full_run_matches_minus_6_800_if_present():
    """本走行があれば、gap60 清算側 r_end(60) の平均が探索段 2 の −6.800 と小数 2 桁で一致。"""
    p2 = EX2_OUT / "e1_delta.csv"
    p3 = FULL_OUT / "f2_retrace.csv"
    if not (p2.exists() and p3.exists()):
        pytest.skip("本走行の出力が無い")
    with open(p2, newline="") as fh:
        want = [r for r in csv.DictReader(fh)
                if r["Δ(秒)"] == "0" and r["群"] == "清算 全体"]
    assert len(want) == 1
    with open(p3, newline="") as fh:
        got = [r for r in csv.DictReader(fh)
               if r["gap(秒)"] == "60" and r["h(秒)"] == "60" and r["群"] == "清算 全体"]
    assert len(got) == 1
    assert round(float(want[0]["平均(bp)"]), 2) == round(float(got[0]["r_end 平均(bp)"]), 2)
    assert round(float(got[0]["r_end 平均(bp)"]), 2) == -6.80
    assert int(got[0]["n"]) == int(want[0]["n"]) == 21198


# ---------------------------------------------------------------------------
# (2) 基準の約定の時刻 < start_ms
# ---------------------------------------------------------------------------
@needs_data
def test_baseline_is_strictly_before_start(smoke):
    with open(MAIN_TABLE, newline="") as fh:
        start = {r["cascade_id"]: int(r["start_ms"]) for r in csv.DictReader(fh)
                 if r["kind"] == "liq"}
    rows = _rows(smoke / "rows_gap60.csv.gz", "liq")
    seen = 0
    for r in rows:
        if not r["t_pre_ms"]:
            continue
        assert int(r["t_pre_ms"]) < start[r["cascade_id"]], r["cascade_id"]
        # baseline_lag_ms = start_ms − 基準の約定の時刻
        assert int(r["baseline_lag_ms"]) == start[r["cascade_id"]] - int(r["t_pre_ms"])
        seen += 1
    assert seen > 0


def test_baseline_lookup_never_sees_the_future():
    """`at_or_before(start_ms − 1)` は start_ms 以後の約定を返さない(合成)。"""
    times = np.array([90, 100, 101, 200], dtype=np.int64)
    prices = np.array([10.0, 11.0, 12.0, 13.0])
    m = ex3.measure(times, prices, np.array([99], dtype=np.int64),
                    np.array([101], dtype=np.int64), np.array([1.0]))
    assert m["t_pre_ms"][0] == 90 and m["p_pre"][0] == 10.0
    assert m["t_end_ms"][0] == 101 and m["p_end"][0] == 12.0
    # 5 分より古い基準は引かない
    m2 = ex3.measure(np.array([0, 400_000], dtype=np.int64), np.array([10.0, 11.0]),
                     np.array([399_999], dtype=np.int64),
                     np.array([400_000], dtype=np.int64), np.array([1.0]))
    assert not bool(m2["ok_pre"][0])
    assert not math.isfinite(m2["sweep_bp"][0])


# ---------------------------------------------------------------------------
# (3) 3 区分の和が 1 / (4) sweep ≤ 0 は f が NaN
# ---------------------------------------------------------------------------
@needs_data
def test_three_way_shares_sum_to_one(smoke):
    with open(smoke / "f2_retrace.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            vals = [_f(r["f > 1 の割合"]), _f(r["0 ≤ f ≤ 1 の割合"]), _f(r["f < 0 の割合"])]
            if any(v is None for v in vals):
                continue
            assert math.isclose(sum(vals), 1.0, abs_tol=2e-6), r


def test_three_way_covers_the_whole_line():
    """f の 3 区分に隙間も重なりも無い(境界 0 と 1 を含む合成)。"""
    v = np.array([-0.5, 0.0, 0.5, 1.0, 1.5])
    gt1 = (v > 1).mean()
    mid = ((v >= 0) & (v <= 1)).mean()
    lt0 = (v < 0).mean()
    assert math.isclose(gt1 + mid + lt0, 1.0)


@needs_data
def test_sweep_non_positive_bundles_have_nan_f(smoke):
    rows = _rows(smoke / "rows_gap60.csv.gz", "liq")
    n_bad = 0
    for r in rows:
        sw = _f(r["sweep_bp"])
        if sw is None or sw > 0:
            continue
        n_bad += 1
        for h in ex3.HORIZONS_SEC:
            assert r[f"f_{h}"] == "", (r["cascade_id"], h, r[f"f_{h}"])
    summ = json.loads((smoke / "summary.json").read_text())
    assert summ["走行ごと"]["gap60"]["sweep ≤ 0 の束"] == n_bad
    assert n_bad > 0


# ---------------------------------------------------------------------------
# (5) 対照 (a): 帯・重なり・置換なし
# ---------------------------------------------------------------------------
def test_band_rule_excludes_zero_and_is_lower_closed():
    cuts = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
    assert int(ex3.band_of(0.0, cuts)) == -1      # 0 は帯 1 に入らない
    assert int(ex3.band_of(-1.0, cuts)) == -1
    assert int(ex3.band_of(0.5, cuts)) == 1       # 帯 1 = (0, q_1)
    assert int(ex3.band_of(1.0, cuts)) == 2       # 下限を含む
    assert int(ex3.band_of(1.5, cuts)) == 2
    assert int(ex3.band_of(9.0, cuts)) == 10      # 帯 10 = [q_9, +∞)
    assert int(ex3.band_of(1e9, cuts)) == 10
    assert int(ex3.band_of(float("nan"), cuts)) == -1


@needs_data
def test_control_a_band_no_overlap_and_no_replacement(smoke):
    liq = {r["cascade_id"]: r for r in _rows(smoke / "rows_gap60.csv.gz", "liq")}
    ca = _rows(smoke / "rows_gap60.csv.gz", "control_a")
    assert len(ca) > 0
    sweeps = np.array([_f(r["sweep_bp"]) if _f(r["sweep_bp"]) is not None
                       else float("nan") for r in liq.values()])
    cuts = ex3.band_cuts(sweeps)
    with open(MAIN_TABLE, newline="") as fh:
        bundles = [(int(r["start_ms"]), int(r["end_ms"]), r["cascade_id"])
                   for r in csv.DictReader(fh) if r["kind"] == "liq"]
    bundles.sort()
    widths = {c: e - s for s, e, c in bundles}
    taken = []
    for r in ca:
        cid = r["matched_liq_id"]
        assert cid in liq
        s_b = _f(liq[cid]["sweep_bp"])
        c_t = _f(r["c_t"])
        assert c_t is not None and s_b is not None and s_b > 0
        assert int(ex3.band_of(c_t, cuts)) == int(ex3.band_of(s_b, cuts))
        t = int(r["ctrl_t_ms"])
        w = widths[cid]
        lo, hi = t - w - 1, t + ex3.CTRL_WINDOW_MS
        for s, e, _c in bundles:
            assert not (max(lo, s) <= min(hi, e)), (cid, t, s, e)
        taken.append((lo, hi))
        # 候補時刻は 10 秒刻み(その日の 00:00 UTC 起点)
        assert (t - ex3.day_start_ms(r["day"])) % ex3.GRID_STEP_MS == 0
        assert 0 <= t - ex3.day_start_ms(r["day"]) < 86_400_000
    taken.sort()
    for (a_lo, a_hi), (b_lo, b_hi) in zip(taken, taken[1:]):
        assert b_lo > a_hi, ((a_lo, a_hi), (b_lo, b_hi))


@needs_data
def test_control_a_counts_are_reported(smoke):
    summ = json.loads((smoke / "summary.json").read_text())
    g = summ["走行ごと"]["gap60"]
    assert (g["対照 (a) を取れた束"] + g["対照 (a) が取れなかった束"]
            == g["対照 (a) の対象(sweep > 0)"])
    with open(smoke / "f0_selfcheck.csv", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["量"] == "|c_t − S_b|(bp)"]
    assert len(rows) == 3
    assert int(rows[0]["n"]) == g["対照 (a) を取れた束"]


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
    rc = ex3.main([
        "--runs-dir", str(RUNS_DIR), "--data-root", str(DATA_ROOT),
        "--bitflyer-dir", str(BF_DIR), "--out", str(tmp_path / "o"),
        "--limit-days", "2", "--progress-every", "1000", "--skip-liq-dup",
    ])
    assert rc == 0
    assert touched == []
    src = (ROOT / "scripts" / "o3c_signal_explore3.py").read_text().splitlines()
    hits = [ln for ln in src if "paper_logs" in ln]
    assert hits and all(ln.lstrip().startswith(("#", "*", '"""')) or "開かない" in ln
                        for ln in hits), hits


# ---------------------------------------------------------------------------
# (7) 日クラスタ SE が探索段 2 の式と一致 / 日等重み
# ---------------------------------------------------------------------------
def test_day_cluster_se_is_the_explore2_function():
    assert ex3.mean_se_cluster is ex2.mean_se_cluster
    rng = np.random.default_rng(11)
    v = rng.normal(size=400)
    days = np.array([f"d{i % 7}" for i in range(400)], dtype=object)
    got = ex3.mean_se_cluster(v, days)
    want = ex2.mean_se_cluster(v, days)
    assert got == want
    assert math.isclose(got[2], float(v.std(ddof=0)) / math.sqrt(400), rel_tol=1e-12)


def test_day_equal_weight_mean():
    v = np.array([1.0, 3.0, 10.0, np.nan])
    d = np.array(["a", "a", "b", "b"], dtype=object)
    assert math.isclose(ex3.day_equal_weight_mean(v, d), (2.0 + 10.0) / 2)


# ---------------------------------------------------------------------------
# 出力の形
# ---------------------------------------------------------------------------
@needs_data
def test_table_row_counts(smoke):
    def n(name):
        with open(smoke / name, newline="") as fh:
            return len(list(csv.DictReader(fh)))
    assert n("f0_selfcheck.csv") == 63
    assert n("f1_sweep.csv") == 21
    assert n("f2_retrace.csv") == 54
    assert n("f3_overshoot.csv") == 9
    assert n("f5_attributes.csv") == 99
    assert 63 + 21 + 54 + 9 + 99 == 246


@needs_data
def test_no_verdict_words_in_outputs(smoke):
    for name in ("tables.md", "summary.json", "f0_selfcheck.csv", "f1_sweep.csv",
                 "f2_retrace.csv", "f3_overshoot.csv", "f5_attributes.csv"):
        txt = (smoke / name).read_text()
        for w in ex3.BANNED_WORDS:
            assert w not in txt, (name, w)
