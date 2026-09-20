"""`scripts/o3c_signal_continue_jev.py`(続く/止まるの単位 — 後半 Jev 5,000 件 + Q7)の試験。

委任文の【テスト】(a)〜(d):
  (a) 層化の件数(側 × 材料1の3群で quota どおりに選ばれる)。
  (b) state に p0 と ts 以後の値が入らない(合成データ。プリント側・Q7 候補側の両方)。
  (c) 閾値の判断の符号(prob >= threshold を「続く」とする)。
  (d) 前半のプリントが入らない(後半だけから選ぶ)。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_continue_jev", ROOT / "scripts" / "o3c_signal_continue_jev.py")
cj = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cj)
sc = cj.cont  # scripts/o3c_signal_continue.py(下見の実装。そのまま再利用している側)


# ---------------------------------------------------------------------------
# 小道具
# ---------------------------------------------------------------------------
def _synthetic_trades(ts: int, lo_off=4_000_000, hi_off=400_000):
    lo, hi = ts - lo_off, ts + hi_off
    times = np.arange(lo, hi + 1, 1000, dtype=np.int64)
    prices = 30000.0 + 0.001 * (times - lo)
    qtys = np.ones(times.size)
    maker = (np.arange(times.size) % 2 == 0)
    return times, prices, qtys, maker


def make_prints_csv(tmp_path: Path, rows: list) -> "sc.PrintsCSV":
    cols = ["kind", "print_id", "day", "side", "ts_ms", "t0_ms", "p0", "notional",
           "dist_node_bp", "oi_covered", "bundle_id"]
    df = pd.DataFrame([{c: r.get(c, "") for c in cols} for r in rows])
    df["kind"] = "print"
    p = tmp_path / "rows_prints.csv.gz"
    df.to_csv(p, index=False, compression="gzip")
    return sc.PrintsCSV(p)


def _bh_pool_df(per_stratum: int) -> pd.DataFrame:
    """側 × 材料1の3群(0/1-2/3+)を、それぞれ `per_stratum` 件ずつ持つ後半プリント。"""
    rows = []
    counts = {"0": 0.0, "1-2": 2.0, "3+": 5.0}
    i = 0
    for side in ("SELL", "BUY"):
        for grp, cnt in counts.items():
            for _ in range(per_stratum):
                rows.append({"print_id": f"p{i:05d}", "side": side,
                            "mat1_same_side_count_60s_and_elapsed": cnt})
                i += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# (a) 層化の件数
# ---------------------------------------------------------------------------
def test_select_5000_stratified_counts_exact_division():
    df_bh = _bh_pool_df(per_stratum=100)  # 6 層 × 100 = 600 件のプール
    picked = cj.select_5000(df_bh, seed=1, n_sample=60)  # 6 層 × 10、余り無し
    assert len(picked) == 60
    assert len(set(picked)) == 60  # 重複なし
    grp = df_bh.set_index("print_id")
    tally = {}
    for pid in picked:
        r = grp.loc[pid]
        key = (r["side"], cj.count_group(r["mat1_same_side_count_60s_and_elapsed"]))
        tally[key] = tally.get(key, 0) + 1
    for side in ("SELL", "BUY"):
        for g in ("0", "1-2", "3+"):
            assert tally.get((side, g)) == 10, tally


def test_select_5000_stratified_counts_with_remainder():
    df_bh = _bh_pool_df(per_stratum=100)
    n_sample = 62  # 6 層 × 10 = 60、余り 2 は列挙順の先頭 2 層(SELL_0, SELL_1-2)へ
    picked = cj.select_5000(df_bh, seed=1, n_sample=n_sample)
    assert len(picked) == n_sample
    grp = df_bh.set_index("print_id")
    tally = {}
    for pid in picked:
        r = grp.loc[pid]
        key = (r["side"], cj.count_group(r["mat1_same_side_count_60s_and_elapsed"]))
        tally[key] = tally.get(key, 0) + 1
    assert tally[("SELL", "0")] == 11
    assert tally[("SELL", "1-2")] == 11
    assert tally[("SELL", "3+")] == 10
    assert tally[("BUY", "0")] == 10
    assert tally[("BUY", "1-2")] == 10
    assert tally[("BUY", "3+")] == 10


def test_select_5000_deterministic_for_same_seed():
    df_bh = _bh_pool_df(per_stratum=50)
    a = cj.select_5000(df_bh, seed=20260920, n_sample=30)
    b = cj.select_5000(df_bh, seed=20260920, n_sample=30)
    assert a == b


# ---------------------------------------------------------------------------
# (b) state に p0 と ts 以後の値が入らない(合成)
# ---------------------------------------------------------------------------
def test_jev_state_for_print_excludes_p0_and_future(tmp_path):
    """既存(下見)の `jev_state_for_print` をそのまま呼ぶ(この委任は state 作りを
    変えていないことの確認)。"""
    day = "2024-01-02"
    ts = sc.day_start_ms(day) + 3_600_000
    rows = [{"print_id": "cur", "day": day, "side": "SELL", "ts_ms": ts,
             "t0_ms": ts, "p0": 30003.6, "notional": 500_000.0,
             "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": ""}]
    pc = make_prints_csv(tmp_path, rows)
    all_ts = pc.all_ts_sorted()
    o = np.argsort(pc.ts, kind="stable")
    all_side, all_notional = pc.side[o], pc.notional[o]

    times, prices, _q, _m = _synthetic_trades(ts)
    future_price = 999_999.0
    prices2 = prices.copy()
    prices2[times > ts] = future_price

    mat_row = {sc.MAT_COL[n]: 1.0 for n in sc.MAT_NUMS}
    mat_row[sc.MAT_COL[6]] = "UTC 00–06"
    state = sc.jev_state_for_print("cur", pc, all_ts, all_side, all_notional,
                                   times, prices2, mat_row)

    blob = json.dumps(state, ensure_ascii=False)
    assert "30003.6" not in blob  # p0
    assert future_price not in [p for p in state["price_path_bp_last_60s"] if p is not None]
    assert len(state["price_path_bp_last_60s"]) == 61
    for ev in state["prints_last_60s"]:
        assert ev["t_rel_s"] <= 0
    assert "p0" not in state["materials"]


def test_jev_state_for_q7_candidate_excludes_p0_and_future():
    ts = 1_704_196_800_000 + 3_600_000
    all_ts = np.array([ts - 30_000, ts - 5_000], dtype=np.int64)
    all_side = np.array(["SELL", "BUY"], dtype=object)
    all_notional = np.array([12_345.0, 999_999_999.0], dtype=float)  # p0 に似た値は使わない

    times, prices, _q, _m = _synthetic_trades(ts)
    future_price = 888_888.0
    prices2 = prices.copy()
    prices2[times > ts] = future_price

    cand_row = {"ts_ms": ts, "dir_sign": -1.0,
               sc.MAT_COL[9]: 0.4, sc.MAT_COL[15]: 0.6}
    for n in sc.MAT_NUMS:
        cand_row.setdefault(sc.MAT_COL[n], None)

    state = cj.jev_state_for_q7_candidate(cand_row, all_ts, all_side, all_notional,
                                          times, prices2)
    assert state["side"] == "SELL"  # dir_sign = -1 -> REACT_SIGN の SELL と同じ向き
    blob = json.dumps(state, ensure_ascii=False)
    assert future_price not in [p for p in state["price_path_bp_last_60s"] if p is not None]
    assert "888888.0" not in blob
    assert len(state["price_path_bp_last_60s"]) == 61
    for ev in state["prints_last_60s"]:
        assert ev["t_rel_s"] <= 0
    assert "p0" not in state["materials"]
    assert "ts_ms" not in json.dumps(state)  # 生の ts 自体も渡さない(相対値だけ)


# ---------------------------------------------------------------------------
# (c) 閾値の判断の符号
# ---------------------------------------------------------------------------
def test_predict_continue_threshold_sign():
    assert cj.predict_continue(0.49, 0.5) is False
    assert cj.predict_continue(0.50, 0.5) is True
    assert cj.predict_continue(0.51, 0.5) is True
    assert cj.predict_continue(0.29, 0.3) is False
    assert cj.predict_continue(0.30, 0.3) is True
    assert cj.predict_continue(0.69, 0.7) is False
    assert cj.predict_continue(0.70, 0.7) is True
    assert cj.predict_continue(None, 0.5) is None
    assert cj.predict_continue(float("nan"), 0.5) is None


# ---------------------------------------------------------------------------
# (d) 前半のプリントが入らない
# ---------------------------------------------------------------------------
def test_build_manifest_excludes_first_half(monkeypatch):
    monkeypatch.setattr(cj, "N_SAMPLE", 60)  # プール(層あたり 60 件)に収まる小さい件数で試す
    rows = []
    i = 0
    for half in ("前半", "後半"):
        for side in ("SELL", "BUY"):
            for grp, cnt in (("0", 0.0), ("1-2", 2.0), ("3+", 5.0)):
                for _ in range(60):
                    rows.append({
                        "kind": "print", "print_id": f"{half}_{i:05d}", "day": "2024-01-01",
                        "side": side, "half": half,
                        "mat1_same_side_count_60s_and_elapsed": cnt,
                        "q7_matched_print_id": np.nan,
                    })
                    i += 1
    df = pd.DataFrame(rows)
    manifest = cj.build_manifest(df)
    picked = {m["print_id"] for m in manifest["prints"]}
    assert all(pid.startswith("後半_") for pid in picked)
    assert not any(pid.startswith("前半_") for pid in picked)
    assert len(manifest["prints"]) == cj.N_SAMPLE
