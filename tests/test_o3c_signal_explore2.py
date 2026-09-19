"""`scripts/o3c_signal_explore2.py`(清算を起点とした値動きの探索段 2)の試験。

**測るもの**(委任文【テスト】(1)〜(8))
  1. Δ = 0 の gap60 の清算側 h=60 秒の平均が、1 周目の `bp_1m_reactdir` と一致する
     (**実データ**。全 456 日は重いので 5 日に絞り、同じ 5 日の 1 周目の表と突き合わせる)。
  2. 対照の行にも同じ Δ が当たる(`anchor_ts_ms` ≥ 対照の時刻 + Δ*1000)。
  3. 起点の後 5 分に約定が無ければ NaN。
  4. `paper_logs/` を開かない(`open` / `Path.glob` / `Path.iterdir` を見張る)。
  5. 日クラスタ SE が `docs/DATA/probes/20260919_o3c_signal_refuter_verify.py` の式と一致。
  6. 3 区分の割合の和が 1。
  7. 対照 (i) の符号が設計 §4 の規則どおりで、mixed を含む日で末尾の余りが落ちる
     (合成の小さな表で。実データで落ちた数が 180 であることは別の試験で測る)。
  8. E0 の出力に Δ × kind の 18 行があり、Δ = 0 の清算側 lag==0 の割合が
     1 周目の表の値 0.7949 と一致する。
"""
from __future__ import annotations

import builtins
import collections
import csv
import gzip
import importlib.util
import math
import statistics
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_explore2", ROOT / "scripts" / "o3c_signal_explore2.py"
)
ex = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ex)

RUNS_DIR = ROOT / "backtest_data" / "o3c_reaction_20260918_full"
DATA_ROOT = ROOT / "backtest_data" / "binance_cm_o3c_20260913"
BF_DIR = ROOT / "backtest_data" / "bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
MAIN_TABLE = RUNS_DIR / "gap60_w8" / "table.csv"

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
    out = tmp_path_factory.mktemp("explore2")
    rc = ex.main([
        "--runs-dir", str(RUNS_DIR), "--data-root", str(DATA_ROOT),
        "--bitflyer-dir", str(BF_DIR), "--out", str(out),
        "--limit-days", str(N_SMOKE_DAYS), "--progress-every", "1000",
    ])
    assert rc == 0
    return out


def _read_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# (1) Δ = 0 が 1 周目と一致する(実データ)
# ---------------------------------------------------------------------------
@needs_data
def test_delta0_matches_first_round_bp_1m(smoke):
    new = [r for r in _read_rows(smoke / "rows_gap60.csv.gz")
           if r["delta_sec"] == "0" and r["kind"] == "liq"]
    days = {r["day"] for r in new}
    assert len(days) == N_SMOKE_DAYS
    with open(MAIN_TABLE, newline="") as fh:
        old = {r["cascade_id"]: r for r in csv.DictReader(fh)
               if r["kind"] == "liq" and r["day"] in days}
    assert len(new) == len(old) > 0
    # 行ごとに一致(1 周目は小数 4 桁に丸めて書き出しているのでその分だけ許す)
    for r in new:
        o = old[r["cascade_id"]]
        a, b = _f(r["r_60"]), _f(o["bp_1m_reactdir"])
        assert (a is None) == (b is None), r["cascade_id"]
        if a is not None:
            assert abs(a - b) < 1e-3, (r["cascade_id"], a, b)
        assert str(r["anchor_ts_ms"]) == str(o["anchor_ts_ms"])
    va = [x for x in (_f(r["r_60"]) for r in new) if x is not None]
    vb = [x for x in (_f(o["bp_1m_reactdir"]) for o in old.values()) if x is not None]
    assert round(sum(va) / len(va), 2) == round(sum(vb) / len(vb), 2)


@needs_data
def test_delta0_full_run_mean_matches_minus_6_800_if_present():
    """全 456 日の走行があれば、Δ=0 の清算側 h=60 秒の平均が −6.800(n 21,198)。

    走行が無い環境では飛ばす(この試験は本走行の再現を測るためのもの)。
    """
    p = ROOT / "backtest_data" / "o3c_signal_explore2_20260919" / "e1_delta.csv"
    if not p.exists():
        pytest.skip("本走行の出力が無い")
    with open(p, newline="") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["Δ(秒)"] == "0" and r["群"] == "清算 全体"]
    assert len(rows) == 1
    assert round(float(rows[0]["平均(bp)"]), 3) == -6.800
    assert int(rows[0]["n"]) == 21198


# ---------------------------------------------------------------------------
# (2) 対照の行にも同じ Δ が当たる
# ---------------------------------------------------------------------------
@needs_data
def test_delta_applies_to_controls(smoke):
    with open(MAIN_TABLE, newline="") as fh:
        base_ts = {r["cascade_id"]: int(r["end_ms"]) for r in csv.DictReader(fh)}
    rows = _read_rows(smoke / "rows_gap60.csv.gz")
    seen = collections.Counter()
    for r in rows:
        if r["kind"] == "liq" or not r["anchor_ts_ms"]:
            continue
        d = int(r["delta_sec"])
        want = base_ts[r["cascade_id"]] + d * 1000
        assert int(r["anchor_ts_ms"]) >= want, (r["cascade_id"], d)
        assert int(r["anchor_lag_ms"]) == int(r["anchor_ts_ms"]) - want
        seen[(r["kind"], d)] += 1
    for kind in ("control_uniform", "control_matched"):
        for d in ex.DELTAS_SEC:
            assert seen[(kind, d)] > 0, (kind, d)


# ---------------------------------------------------------------------------
# (3) 起点の後 5 分に約定が無ければ NaN
# ---------------------------------------------------------------------------
def test_anchor_nan_when_no_trade_within_5min():
    times = np.array([0, 1_000, 10_000_000], dtype=np.int64)
    prices = np.array([100.0, 100.5, 120.0])
    sign = np.array([1.0, 1.0])
    base_ts = np.array([0, 2_000], dtype=np.int64)
    # Δ = 60 秒 -> 基準は 60_000 / 62_000 ms。次の約定は 10_000_000 ms = 5 分の外。
    a_ts, a_px, a_ok, r = ex.anchor_and_reactions(base_ts, sign, 60, times, prices)
    assert not a_ok.any()
    assert all(not math.isfinite(x) for x in a_px)
    for h in ex.HORIZONS_SEC:
        assert all(not math.isfinite(x) for x in r[h])
    # Δ = 0 なら起点は引ける(0 ms と 10_000 ms 以内の点)
    a_ts0, a_px0, a_ok0, r0 = ex.anchor_and_reactions(base_ts, sign, 0, times, prices)
    assert a_ok0.tolist() == [True, False]
    assert a_ts0[0] == 0 and a_px0[0] == 100.0
    # h 後の点が 5 分より古ければ NaN(起点 0 ms、h = 1 秒 -> 1_000 ms 以前の点 = 1_000 ms)
    a2, p2, a_ok2, r2 = ex.anchor_and_reactions(
        np.array([0], dtype=np.int64), np.array([1.0]), 0, times, prices)
    assert a_ok2[0] and a2[0] == 0
    assert math.isclose(r2[1][0], (100.5 - 100.0) / 100.0 * 1e4)
    # h = 3600 秒 -> 3_600_000 ms 以前で最も新しい点は 1_000 ms、遡り 3_599_000 ms > 5 分
    assert not math.isfinite(r2[3600][0])


# ---------------------------------------------------------------------------
# (4) `paper_logs/` を開かない
# ---------------------------------------------------------------------------
@needs_data
def test_does_not_touch_paper_logs(tmp_path, monkeypatch):
    touched: list[str] = []

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
    rc = ex.main([
        "--runs-dir", str(RUNS_DIR), "--data-root", str(DATA_ROOT),
        "--bitflyer-dir", str(BF_DIR), "--out", str(tmp_path / "o"),
        "--limit-days", "2", "--progress-every", "1000",
    ])
    assert rc == 0
    assert touched == []
    # 道具の本文で `paper_logs` が出るのは覚書の行だけで、コードには出ない
    src = (ROOT / "scripts" / "o3c_signal_explore2.py").read_text().splitlines()
    hits = [ln for ln in src if "paper_logs" in ln]
    assert hits and all(ln.lstrip().startswith(("#", "*", '"""')) or "開かない" in ln
                        for ln in hits), hits


# ---------------------------------------------------------------------------
# (5) 日クラスタ SE がプローブの式と一致
# ---------------------------------------------------------------------------
def _probe_mean_se_cluster(vals_days):
    """`docs/DATA/probes/20260919_o3c_signal_refuter_verify.py` から写した式。"""
    v = [x for x, _ in vals_days]
    n = len(v)
    m = sum(v) / n
    byday = collections.defaultdict(float)
    for x, d in vals_days:
        byday[d] += x - m
    G = len(byday)
    se = math.sqrt(sum(s * s for s in byday.values())) / n * math.sqrt(G / (G - 1))
    return m, se, n, G


def test_day_cluster_se_matches_probe():
    rng = np.random.default_rng(7)
    v = rng.normal(size=500)
    days = np.array([f"d{i % 13}" for i in range(500)], dtype=object)
    v[5] = np.nan  # NaN は落として数える
    m, se, naive, n, g = ex.mean_se_cluster(v, days)
    pairs = [(x, d) for x, d in zip(v.tolist(), days.tolist()) if math.isfinite(x)]
    pm, pse, pn, pg = _probe_mean_se_cluster(pairs)
    assert n == pn == 499 and g == pg == 13
    assert math.isclose(m, pm, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(se, pse, rel_tol=1e-12)
    pnaive = statistics.pstdev([x for x, _ in pairs]) / math.sqrt(pn)
    assert math.isclose(naive, pnaive, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# (6) 3 区分の割合の和が 1
# ---------------------------------------------------------------------------
def test_three_way_sums_to_one():
    v = np.array([-1.0, 0.0, 0.0, 2.5, np.nan, -0.1])
    neg, zero, pos = ex.three_way(v)
    assert math.isclose(neg + zero + pos, 1.0)
    assert (neg, zero, pos) == (2 / 5, 2 / 5, 1 / 5)
    assert all(not math.isfinite(x) for x in ex.three_way(np.array([np.nan])))


@needs_data
def test_three_way_sums_to_one_in_outputs(smoke):
    for name in ("e1_delta.csv", "e2_shape.csv", "e3_gap.csv", "e4_attributes.csv"):
        with open(smoke / name, newline="") as fh:
            for r in csv.DictReader(fh):
                vals = [_f(r["r<0"]), _f(r["r=0"]), _f(r["r>0"])]
                if any(v is None for v in vals):
                    continue
                assert math.isclose(sum(vals), 1.0, abs_tol=2e-6), (name, r)


# ---------------------------------------------------------------------------
# (7) 対照 (i) の符号の規則(合成の小さな表)
# ---------------------------------------------------------------------------
def _write_synth_table(dirpath: Path) -> None:
    """2 日分の小さな表。d1 は束 2 / 一様 3(mixed が 1 つあった日)、d2 は束 2 / 一様 2。"""
    dirpath.mkdir(parents=True, exist_ok=True)
    cols = sorted(ex.TABLE_COLUMNS_NEEDED)
    rows = []

    def add(kind, day, cid, side, start, end, tms, partner=""):
        r = dict.fromkeys(cols, "")
        r.update({"kind": kind, "day": day, "cascade_id": cid, "side": side,
                  "start_ms": str(start), "end_ms": str(end), "time_ms": str(tms),
                  "matched_liq_id": partner})
        for c in ("dist_vwap_bp", "dist_node_bp", "bin_pct",
                  "bundle_n_events_dedup", "bundle_total_notional",
                  "bundle_width_ms", "doi_pre_1h", "implied_leverage"):
            r[c] = "1.0"
        rows.append(r)

    # d1: 束 A(start 100、SELL)、束 B(start 300、BUY)。一様 3 本。
    add("liq", "2024-01-01", "A", "SELL", 100, 150, 100)
    add("liq", "2024-01-01", "B", "BUY", 300, 350, 300)
    add("control_uniform", "2024-01-01", "U1", "", 900, 900, 900)
    add("control_uniform", "2024-01-01", "U2", "", 700, 700, 700)
    add("control_uniform", "2024-01-01", "U3", "", 800, 800, 800)
    add("control_matched", "2024-01-01", "M1", "", 950, 950, 950, partner="A")
    # 相手が主表に居ない対照(相手が mixed の束)
    add("control_matched", "2024-01-01", "M2", "", 960, 960, 960, partner="ZZZ")
    # d2: 束 2 / 一様 2(余りなし)
    add("liq", "2024-01-02", "C", "BUY", 100, 120, 100)
    add("liq", "2024-01-02", "D", "SELL", 200, 220, 200)
    add("control_uniform", "2024-01-02", "V1", "", 500, 500, 500)
    add("control_uniform", "2024-01-02", "V2", "", 400, 400, 400)

    with open(dirpath / "table.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def test_uniform_sign_rule_and_surplus_dropped(tmp_path):
    _write_synth_table(tmp_path / "run")
    t = ex.RunTable(tmp_path / "run")
    side = {c: s for c, s in zip(t.cascade_id.tolist(), t.side.tolist())}
    # d1: 束は start_ms 昇順で A(SELL), B(BUY)。一様は time_ms 昇順で U2(700), U3(800), U1(900)。
    # 1 対 1 -> U2←A(SELL), U3←B(BUY)。U1 は余りなので落ちる(side 空)。
    assert side["U2"] == "SELL"
    assert side["U3"] == "BUY"
    assert side["U1"] == ""
    # d2: C(start 100, BUY), D(start 200, SELL) / V2(400), V1(500) -> V2←C, V1←D
    assert side["V2"] == "BUY"
    assert side["V1"] == "SELL"
    assert t.n_uniform_dropped == 1
    assert t.uniform_dropped_by_day == {"2024-01-01": 1}
    # 対照 (ii): 相手の side。相手が主表に居なければ空。
    assert side["M1"] == "SELL"
    assert side["M2"] == ""
    assert t.n_matched_partner_missing == 1
    # 符号は SELL: −1 / BUY: +1、空なら NaN
    sgn = {c: s for c, s in zip(t.cascade_id.tolist(), t.sign.tolist())}
    assert sgn["U2"] == -1.0 and sgn["U3"] == 1.0
    assert not math.isfinite(sgn["U1"])
    # 束に対照 (ii) が付いたか
    has = {c: b for c, b in zip(t.cascade_id.tolist(), t.liq_has_matched.tolist())}
    assert has["A"] is True and has["B"] is False


@needs_data
def test_uniform_surplus_is_180_on_real_gap60():
    t = ex.RunTable(RUNS_DIR / "gap60_w8")
    assert t.n_uniform_dropped == 180
    assert len(t.uniform_dropped_by_day) == 75
    assert t.n_liq == 21198 and t.n_uniform == 21378


# ---------------------------------------------------------------------------
# (8) E0 の 18 行と Δ = 0 の清算側 lag==0 の割合
# ---------------------------------------------------------------------------
@needs_data
def test_e0_shape(smoke):
    with open(smoke / "e0_anchor_lag.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(ex.DELTAS_SEC) * 3 == 18
    keys = {(r["Δ(秒)"], r["kind"]) for r in rows}
    assert len(keys) == 18


@needs_data
def test_e0_lag_zero_fraction_matches_first_round():
    """Δ = 0 の清算側 lag==0 の割合 = 1 周目の表の 0.7949(全 456 日)。"""
    p = ROOT / "backtest_data" / "o3c_signal_explore2_20260919" / "e0_anchor_lag.csv"
    with open(MAIN_TABLE, newline="") as fh:
        lags = [_f(r["anchor_lag_ms"]) for r in csv.DictReader(fh) if r["kind"] == "liq"]
    lags = [x for x in lags if x is not None]
    want = round(sum(1 for x in lags if x == 0) / len(lags), 4)
    assert want == 0.7949
    if not p.exists():
        pytest.skip("本走行の出力が無い")
    with open(p, newline="") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["Δ(秒)"] == "0" and r["kind"] == ex.KIND_LABEL["liq"]]
    assert len(rows) == 1
    assert round(float(rows[0]["lag==0 の割合"]), 4) == want


# ---------------------------------------------------------------------------
# 出力に判定語が 1 つも無い / 表の行数
# ---------------------------------------------------------------------------
@needs_data
def test_no_verdict_words_in_outputs(smoke):
    for name in ("tables.md", "summary.json", "e0_anchor_lag.csv", "e1_delta.csv",
                 "e2_shape.csv", "e3_gap.csv", "e4_attributes.csv"):
        txt = (smoke / name).read_text()
        for w in ex.BANNED_WORDS:
            assert w not in txt, (name, w)


@needs_data
def test_table_row_counts(smoke):
    def n(name):
        with open(smoke / name, newline="") as fh:
            return len(list(csv.DictReader(fh)))
    assert n("e0_anchor_lag.csv") == 18
    assert n("e1_delta.csv") == 30
    assert n("e2_shape.csv") == 90
    assert n("e3_gap.csv") == 90
    assert n("e4_attributes.csv") == 90
    assert 18 + 30 + 90 + 90 + 90 == 318
