"""`scripts/o3c_signal_explore4.py`(清算を起点とした値動きの探索段 4)の試験。

**測るもの**(委任文【テスト】(1)〜(7))
  1. r_end(60) の gap 60 清算側が探索段 3 と一致する(5 日ぶんを実データで走らせて
     **行ごと**に 1 周目の表と一致 / 本走行があれば全体平均 −6.800366 と小数 4 桁で一致)。
  2. T 秒前の約定の時刻 ≤ `start_ms` − T·1000(先読みをしていない)。
  3. g の 3 区分(g > 1 / 0 ≤ g ≤ 1 / g < 0)の和が 1(分母 > 0 と 分母 ≥ 1 bp の両方で)。
  4. 対照 (c) の c_t が相手の m の帯に入り、区間が束と重ならず、置換なし、処理順どおり。
  5. `paper_logs/` を開かない(探索段 3 と同じモック)。
  6. 出力に判定語が 1 つも無い。
  7. 表の行数。
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
    "o3c_signal_explore4", ROOT / "scripts" / "o3c_signal_explore4.py")
ex4 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ex4)
ex3 = ex4.ex3
ex2 = ex4.ex2

RUNS_DIR = ROOT / "backtest_data" / "o3c_reaction_20260918_full"
DATA_ROOT = ROOT / "backtest_data" / "binance_cm_o3c_20260913"
BF_DIR = ROOT / "backtest_data" / "bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
MAIN_TABLE = RUNS_DIR / "gap60_w8" / "table.csv"
FULL_OUT = ROOT / "backtest_data" / "o3c_signal_explore4_20260920"
EX3_OUT = ROOT / "backtest_data" / "o3c_signal_explore3_20260920"

have_data = MAIN_TABLE.exists() and (DATA_ROOT / "aggTrades").exists()
needs_data = pytest.mark.skipif(not have_data, reason="1 周目の表か公開アーカイブが無い")

N_SMOKE_DAYS = 5

# 委任文【テスト】(7) と設計 §6 の行数
EXPECTED_ROWS = {
    "g0_selfcheck.csv": 70,      # 設計は「約 40 行 + T の下見 5 行」。実装の数え直し
    "g1_reversal.csv": 80,       # T 2 × m 10 × h 3 + gap 30/180 の 10 行ずつ
    "g2_continuation.csv": 54,   # 掃き 3 × m 3 × T 2 × h 3
    "g3_timeshape.csv": 30,      # m 3 × T 2 × h 5
    "g4_control.csv": 60,        # T 2 × m 10 × h 3
    "g5_daystate.csv": 27,       # 日の束数 3 × m 3 × h 3
    "g6_attributes.csv": 153,    # 17 群 × m 3 × h 3
    "g7_bitflyer.csv": 24,       # m 3 × T 2 × 会場 2 × h 2
}


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
    out = tmp_path_factory.mktemp("explore4")
    rc = ex4.main([
        "--runs-dir", str(RUNS_DIR), "--data-root", str(DATA_ROOT),
        "--bitflyer-dir", str(BF_DIR), "--out", str(out),
        "--limit-days", str(N_SMOKE_DAYS), "--progress-every", "1000",
    ])
    assert rc == 0
    return out


def _rows(path: Path, kind=None) -> list:
    with gzip.open(path, "rt", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [r for r in rows if kind is None or r["kind"] == kind]


# ---------------------------------------------------------------------------
# (1) r_end(60) が探索段 3 と一致する
# ---------------------------------------------------------------------------
@needs_data
def test_r_end_60_matches_first_round_row_by_row(smoke):
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
        # 終端は探索段 1〜3 の起点(1 周目の `anchor_ts_ms`)と同じ点
        assert str(r["t_end_ms"]) == str(o["anchor_ts_ms"])


def test_r_end_60_full_run_matches_explore3():
    """本走行があれば r_end(60) の gap60 清算 全体の平均が探索段 3 と小数 4 桁で一致。"""
    p3 = EX3_OUT / "f2_retrace.csv"
    p4 = FULL_OUT / "summary.json"
    if not (p3.exists() and p4.exists()):
        pytest.skip("本走行の出力が無い")
    with open(p3, newline="") as fh:
        want = [r for r in csv.DictReader(fh)
                if r["gap(秒)"] == "60" and r["h(秒)"] == "60"
                and r["群"] == "清算 全体"]
    assert len(want) == 1
    w = float(want[0]["r_end 平均(bp)"])
    assert round(w, 6) == -6.800366
    got = json.loads(p4.read_text())["探索段 3 との突き合わせ"]
    assert round(got["この段"], 4) == round(w, 4)
    assert int(got["n"]) == int(want[0]["n"]) == 21198


# ---------------------------------------------------------------------------
# (2) T 秒前の約定の時刻 ≤ start_ms − T·1000
# ---------------------------------------------------------------------------
@needs_data
def test_pre_move_window_never_sees_the_future(smoke):
    with open(MAIN_TABLE, newline="") as fh:
        start = {r["cascade_id"]: int(r["start_ms"]) for r in csv.DictReader(fh)
                 if r["kind"] == "liq"}
    rows = _rows(smoke / "rows_gap60.csv.gz", "liq")
    seen = 0
    for r in rows:
        s = start[r["cascade_id"]]
        assert int(r["t_pre_ms"]) < s
        assert int(r["baseline_lag_ms"]) == s - int(r["t_pre_ms"])
        for T in ex4.T_ALL:
            lag = r[f"m_lag_ms_{T}"]
            if lag == "":
                continue
            # m_lag_ms_T = (start_ms − T·1000) − T 秒前の約定の時刻 ≥ 0
            assert int(lag) >= 0, (r["cascade_id"], T, lag)
            t_T = s - T * 1000 - int(lag)
            assert t_T <= s - T * 1000
            assert t_T < int(r["t_pre_ms"]) or T * 1000 <= int(r["baseline_lag_ms"])
        seen += 1
    assert seen > 0


def test_measure_lookups_are_time_only():
    """合成データで `at_or_before` / `at_or_after` の境界を測る。"""
    times = np.array([0, 90, 100, 101, 200], dtype=np.int64)
    prices = np.array([9.0, 10.0, 11.0, 12.0, 13.0])
    m = ex4.measure(times, prices, np.array([99], dtype=np.int64),
                    np.array([101], dtype=np.int64), np.array([1.0]),
                    {60: np.array([0], dtype=np.int64)})
    assert m["t_pre_ms"][0] == 90 and m["p_pre"][0] == 10.0
    assert m["t_end_ms"][0] == 101 and m["p_end"][0] == 12.0
    assert m["t_m_ms_60"][0] == 0 and m["m_lag_ms_60"][0] == 0
    # m(60) = (10 − 9)/9 × 1e4
    assert math.isclose(float(m["m_60"][0]), (10.0 - 9.0) / 9.0 * 1e4)
    # 5 分より古い基準・T 秒前は引かない
    m2 = ex4.measure(np.array([0, 400_000], dtype=np.int64), np.array([10.0, 11.0]),
                     np.array([399_999], dtype=np.int64),
                     np.array([400_000], dtype=np.int64), np.array([1.0]),
                     {60: np.array([399_000], dtype=np.int64)})
    assert not bool(m2["ok_pre"][0])
    assert not bool(m2["ok_m_60"][0])
    assert not math.isfinite(m2["sweep_bp"][0])
    assert not math.isfinite(m2["m_60"][0])


def test_grid_base_is_before_the_bundle():
    """G7 の 1 分格子の基準は `start_ms` を含む足の 1 本前(先読みなし)。"""
    minute = 3 * ex4.MINUTE_MS
    times = np.array([minute - 5_000, minute - 1, minute + 10,
                      minute - 1 + 300_000], dtype=np.int64)
    prices = np.array([100.0, 101.0, 500.0, 202.0])
    bf = {"t_ms": np.zeros(0, dtype=np.int64), "close": np.zeros(0),
          "years_missing": []}
    g = ex4.grid_returns(times, prices, bf, np.array([minute + 30_000]),
                         np.array([1.0]))
    # 基準 = at_or_before(minute − 1) = 101.0(束の中の 500.0 は使わない)
    assert math.isclose(float(g["bn_grid_300"][0]),
                        (202.0 - 101.0) / 101.0 * 1e4)


# ---------------------------------------------------------------------------
# (3) g の 3 区分の和が 1
# ---------------------------------------------------------------------------
@needs_data
def test_g_three_way_shares_sum_to_one(smoke):
    for name in ("g1_reversal.csv", "g2_continuation.csv", "g4_control.csv",
                 "g5_daystate.csv"):
        with open(smoke / name, newline="") as fh:
            for r in csv.DictReader(fh):
                for tag in ("分母>0", "分母≥1bp"):
                    vals = [_f(r[f"g > 1 の割合({tag})"]),
                            _f(r[f"0 ≤ g ≤ 1 の割合({tag})"]),
                            _f(r[f"g < 0 の割合({tag})"])]
                    if any(v is None for v in vals):
                        assert int(r[f"g の母数({tag})"]) == 0, (name, r)
                        continue
                    assert math.isclose(sum(vals), 1.0, abs_tol=2e-6), (name, tag, r)


def test_g_three_way_covers_the_whole_line():
    """g の 3 区分に隙間も重なりも無い(境界 0 と 1 を含む合成)。"""
    v = np.array([-0.5, 0.0, 0.5, 1.0, 1.5])
    assert math.isclose(float((v > 1).mean())
                        + float(((v >= 0) & (v <= 1)).mean())
                        + float((v < 0).mean()), 1.0)


@needs_data
def test_g_is_nan_when_the_denominator_is_not_positive(smoke):
    rows = _rows(smoke / "rows_gap60.csv.gz", "liq")
    n_bad = 0
    for r in rows:
        for T in ex4.T_MAIN:
            den = _f(r[f"den_bp_{T}"])
            if den is None or den > 0:
                continue
            n_bad += 1
            for h in ex4.H_MAIN:
                assert r[f"g_{T}_{h}"] == "", (r["cascade_id"], T, h)
    summ = json.loads((smoke / "summary.json").read_text())
    got = summ["走行ごと"]["gap60"]["g の分母 ≤ 0 の束"]
    assert sum(int(v) for v in got.values()) == n_bad


# ---------------------------------------------------------------------------
# (4) 対照 (c): 帯・重なり・置換なし・処理順
# ---------------------------------------------------------------------------
def test_m_band_rule_is_lower_closed_and_covers_negatives():
    cuts = np.array([-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    assert int(ex4.band_of_m(-1e9, cuts)) == 1      # 帯 1 = (−∞, q_1)
    assert int(ex4.band_of_m(-3.0, cuts)) == 2      # 下限を含む
    assert int(ex4.band_of_m(-2.5, cuts)) == 2
    assert int(ex4.band_of_m(0.0, cuts)) == 5       # 0 も帯に入る(負を含む切り方)
    assert int(ex4.band_of_m(5.0, cuts)) == 10      # 帯 10 = [q_9, +∞)
    assert int(ex4.band_of_m(1e9, cuts)) == 10
    assert int(ex4.band_of_m(float("nan"), cuts)) == -1
    lo, hi = ex4.band_bounds(cuts, 1)
    assert lo == -math.inf and hi == -3.0
    lo, hi = ex4.band_bounds(cuts, 10)
    assert lo == 5.0 and hi == math.inf


@needs_data
def test_control_c_band_no_overlap_and_no_replacement(smoke):
    liq = {r["cascade_id"]: r for r in _rows(smoke / "rows_gap60.csv.gz", "liq")}
    ctrl = _rows(smoke / "rows_gap60.csv.gz", "control_c")
    assert len(ctrl) > 0
    with open(MAIN_TABLE, newline="") as fh:
        bundles = [(int(r["start_ms"]), int(r["end_ms"]))
                   for r in csv.DictReader(fh) if r["kind"] == "liq"]
    bundles.sort()
    for T in ex4.T_MAIN:
        sel = [r for r in ctrl if int(r["ctrl_T"]) == T]
        assert len(sel) > 0
        m_all = np.array([_f(r[f"m_{T}"]) for r in liq.values()], dtype=float)
        cuts = ex4.band_cuts_m(m_all)
        taken = []
        for r in sel:
            cid = r["matched_liq_id"]
            assert cid in liq
            m_b = _f(liq[cid][f"m_{T}"])
            c_t = _f(r["c_t"])
            assert c_t is not None and m_b is not None
            # 帯が一致する
            assert int(ex4.band_of_m(c_t, cuts)) == int(ex4.band_of_m(m_b, cuts))
            # 行の m_T は c_t そのもの(同じ式で引き直している)
            assert abs(_f(r[f"m_{T}"]) - c_t) < 1e-6
            t = int(r["ctrl_t_ms"])
            lo, hi = t - T * 1000, t + ex4.CTRL_WINDOW_MS
            for s, e in bundles:
                assert not (max(lo, s) <= min(hi, e)), (cid, T, t, s, e)
            taken.append((lo, hi))
            # 候補時刻は 10 秒刻み(その日の 00:00 UTC 起点)
            assert (t - ex4.day_start_ms(r["day"])) % ex4.GRID_STEP_MS == 0
            assert 0 <= t - ex4.day_start_ms(r["day"]) < 86_400_000
        taken.sort()
        for (a_lo, a_hi), (b_lo, b_hi) in zip(taken, taken[1:]):
            assert b_lo > a_hi, (T, (a_lo, a_hi), (b_lo, b_hi))


class _StubBundles:
    """`select_control_c` が使う束の並びだけを持つ最小の入れ物。"""

    def __init__(self, day, starts, ends, signs):
        n = len(starts)
        self.cascade_id = np.array([f"b{i}" for i in range(n)], dtype=object)
        self.day = np.array([day] * n, dtype=object)
        self.side = np.array(["BUY"] * n, dtype=object)
        self.sign = np.array(signs, dtype=float)
        self.start_ms = np.array(starts, dtype=np.int64)
        self.end_ms = np.array(ends, dtype=np.int64)
        self.width_ms = self.end_ms - self.start_ms
        self.max_width_ms = int(self.width_ms.max()) if n else 0
        self.by_day = {day: np.arange(n, dtype=int)}


def _flat_series(day: str, jump_at_ms: int | None = None, jump: float = 0.0):
    d0 = ex4.day_start_ms(day)
    t = np.arange(d0 - 3_600_000, d0 + 86_400_000 + 1_800_000, 1000,
                  dtype=np.int64)
    p = np.full(t.size, 100.0)
    if jump_at_ms is not None:
        m = (t >= jump_at_ms - 500) & (t <= jump_at_ms + 500)
        p[m] = 100.0 * (1.0 + jump)
    return t, p


def test_control_c_processing_order_is_day_then_start_ms():
    """同じ m の束が同じ候補を欲しがったら、`start_ms` が早い束が取る。"""
    day = "2024-03-13"
    d0 = ex4.day_start_ms(day)
    t_star = d0 + 40_000_000 // ex4.GRID_STEP_MS * ex4.GRID_STEP_MS
    times, prices = _flat_series(day, jump_at_ms=t_star, jump=5e-4)
    # 束は t_star の区間から十分離す
    bd = _StubBundles(day,
                      starts=[d0 + 200_000, d0 + 400_000],
                      ends=[d0 + 200_100, d0 + 400_100],
                      signs=[1.0, 1.0])
    cuts = np.array([-100.0, -90.0, -80.0, -70.0, -60.0, -50.0, -40.0, -30.0, -20.0])
    m_all = np.array([5.0, 5.0])
    taken: dict = {}
    rows, note = ex4.select_control_c(day, bd, 60, cuts, m_all, times, prices, taken)
    assert note == {"n_bundles": 2, "n_taken": 2}
    cols = ex4.CHUNK_HEADER
    got = [dict(zip(cols, r)) for r in rows]
    assert got[0]["cascade_id"] == "b0" and got[1]["cascade_id"] == "b1"
    # 早い束が「ちょうど合う」候補 t_star を取る
    assert int(got[0]["ctrl_t_ms"]) == t_star
    assert abs(float(got[0]["c_t"]) - 5.0) < 1e-6
    # 遅い束は t_star を取れない(置換なし)
    assert int(got[1]["ctrl_t_ms"]) != t_star
    lo0 = t_star - 60_000
    hi0 = t_star + ex4.CTRL_WINDOW_MS
    t1 = int(got[1]["ctrl_t_ms"])
    assert not (max(t1 - 60_000, lo0) <= min(t1 + ex4.CTRL_WINDOW_MS, hi0))


def test_control_c_never_overlaps_a_bundle():
    """束の区間と重なる候補は 1 つも選ばれない(合成)。"""
    day = "2024-03-13"
    d0 = ex4.day_start_ms(day)
    times, prices = _flat_series(day)
    # 1 日のほとんどを束で埋め、残りの窓を 1 つだけ空ける
    bd = _StubBundles(day, starts=[d0 + 1000, d0 + 40_000_000],
                      ends=[d0 + 38_000_000, d0 + 86_000_000],
                      signs=[1.0, 1.0])
    cuts = np.array([-100.0, -90.0, -80.0, -70.0, -60.0, -50.0, -40.0, -30.0, -20.0])
    taken: dict = {}
    rows, note = ex4.select_control_c(day, bd, 60, cuts, np.array([0.0, 0.0]),
                                      times, prices, taken)
    assert note["n_bundles"] == 2
    cols = ex4.CHUNK_HEADER
    for r in rows:
        d = dict(zip(cols, r))
        t = int(d["ctrl_t_ms"])
        lo, hi = t - 60_000, t + ex4.CTRL_WINDOW_MS
        for s, e in zip(bd.start_ms.tolist(), bd.end_ms.tolist()):
            assert not (max(lo, s) <= min(hi, e)), (t, s, e)


# ---------------------------------------------------------------------------
# (5) `paper_logs/` を開かない
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
    rc = ex4.main([
        "--runs-dir", str(RUNS_DIR), "--data-root", str(DATA_ROOT),
        "--bitflyer-dir", str(BF_DIR), "--out", str(tmp_path / "o"),
        "--limit-days", "2", "--progress-every", "1000",
    ])
    assert rc == 0
    assert touched == []
    src = (ROOT / "scripts" / "o3c_signal_explore4.py").read_text().splitlines()
    hits = [ln for ln in src if "paper_logs" in ln]
    assert hits and all(ln.lstrip().startswith(("#", "*", '"""')) or "開かない" in ln
                        for ln in hits), hits


# ---------------------------------------------------------------------------
# (6) 判定語なし / (7) 表の行数
# ---------------------------------------------------------------------------
@needs_data
def test_no_verdict_words_in_outputs(smoke):
    names = list(EXPECTED_ROWS) + ["tables.md", "summary.json"]
    for name in names:
        txt = (smoke / name).read_text()
        for w in ex4.BANNED_WORDS:
            assert w not in txt, (name, w)


@needs_data
def test_table_row_counts(smoke):
    for name, want in EXPECTED_ROWS.items():
        with open(smoke / name, newline="") as fh:
            got = len(list(csv.DictReader(fh)))
        assert got == want, (name, got, want)
    assert sum(EXPECTED_ROWS.values()) == 498
    assert sum(EXPECTED_ROWS.values()) - EXPECTED_ROWS["g0_selfcheck.csv"] == 428
    summ = json.loads((smoke / "summary.json").read_text())
    assert summ["表の行数"]["合計"] == 498
    assert summ["表の行数"]["G0 を除く合計"] == 428


@needs_data
def test_chunk_files_are_removed(smoke):
    assert not (smoke / "chunks1").exists()
    assert not (smoke / "chunks2").exists()


@needs_data
def test_every_share_column_has_a_denominator(smoke):
    """割合の列にはすべて母数の列が添えてある(反証者 3 の致命 3)。"""
    pairs = {
        "r_end > 0 の割合": "r_end > 0 の母数",
        f"次の束が {ex4.CONT_SEC} 秒以内の割合": f"次の束が {ex4.CONT_SEC} 秒以内の母数",
        "g > 1 の割合(分母>0)": "g の母数(分母>0)",
        "g > 1 の割合(分母≥1bp)": "g の母数(分母≥1bp)",
        "0 ≤ g ≤ 1 の割合(分母>0)": "g の母数(分母>0)",
        "g < 0 の割合(分母>0)": "g の母数(分母>0)",
    }
    for name in EXPECTED_ROWS:
        with open(smoke / name, newline="") as fh:
            cols = set(csv.DictReader(fh).fieldnames or [])
        for share, denom in pairs.items():
            if share in cols:
                assert denom in cols, (name, share)


# ---------------------------------------------------------------------------
# 群の作り方(設計 §0 の機械的な規則)
# ---------------------------------------------------------------------------
@needs_data
def test_g6_is_six_attributes_and_seventeen_groups():
    table = ex2.RunTable(RUNS_DIR / "gap60_w8")
    groups = ex4.g6_groups(table)
    assert len(groups) == 17
    attrs = sorted({g["属性"] for g in groups})
    assert attrs == sorted(list(ex4.G6_ATTRS) + [ex2.ATTR_SIDE])
    # 連続 5 属性は 3 分位、側は 2 群
    for a in ex4.G6_ATTRS:
        assert len([g for g in groups if g["属性"] == a]) == 3
    assert len([g for g in groups if g["属性"] == ex2.ATTR_SIDE]) == 2
    # 切り値は探索段 2 の E4(= 探索段 3 の F5)と同じ関数から来る
    ref = {(g["属性"], g["群"]): (g["下限"], g["上限"])
           for g in ex2.attribute_groups(table)}
    for g in groups:
        assert ref[(g["属性"], g["群"])] == (g["下限"], g["上限"])


def test_sweep_cuts_are_the_explore3_values():
    assert ex4.SWEEP_CUTS == (0.2009, 8.0760)


# ---------------------------------------------------------------------------
# SE と日等重み(探索段 2・3 と同じ関数)
# ---------------------------------------------------------------------------
def test_se_helpers_are_the_earlier_functions():
    assert ex4.mean_se_cluster is ex2.mean_se_cluster
    assert ex4.day_equal_weight_mean is ex3.day_equal_weight_mean
    rng = np.random.default_rng(4)
    v = rng.normal(size=300)
    days = np.array([f"d{i % 9}" for i in range(300)], dtype=object)
    assert ex4.mean_se_cluster(v, days) == ex2.mean_se_cluster(v, days)
