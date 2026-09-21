#!/usr/bin/env python3
"""「値段の続き」を判断の対象にした方策の模擬(①)+ 全部逆張りの最適化(②)の道具
(2026-09-21)。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md`(オーナー承認 L-344)
委任文: `docs/DATA/delegations/20260921_o3c_signal_value_prompt.md`
前段: `docs/PHASE2/O3C/SIGNAL/POLICY_STAGE1_REPORT_2026-09-20.md`
      / `scripts/o3c_signal_policy.py`(状態機械・`simulate_cascade` はこの道具が**流用**する)

**この道具がすること**
  - `stage1`(この委任の範囲): **前半だけ**。
      ① 判断の当てはめ(`fit_beta_front_half(label_col="value_continuation_60")`)、
        5 分割 OOF の 0.02 刻みの較正表と「わからない」の帯(L-277 の規則)、
        値段のラベルが 1 のプリントで 5 bp に達するまでの秒の分布。
      ② 全部逆張りの 4 ノブの格子(位置 3 × 条件 7 × 出口 3 × 損切り 3 = 189 組)を
        前半の全連鎖 8,931 本に当て、事前に固定した規則で 1 組を選ぶ。
      前半 200 本(種 20260920)での ① の 7 方策 × 型 A/B × 遅れ 3 の動作確認。
      Q5b (a) 秒単位の経路差(標本日に掛かる前半 285 本)と (b) 1 分の始値の道具。
  - `stage2`(**この委任では実装だけして走らせない**): 後半 2,000 本での比較。

**`stage1` は `half == "前半"` 以外の行を読んだら例外で止まる**(`assert_front_half_only` /
`require_front_half`)。費用 c は `scripts/o3c_bitflyer_spread.py` が作った
**集計表だけ**を読む(生データはこの道具から触らない)。

**探索段なので判定語を 1 つも書かない。`paper_logs/` は開かない。**
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import itertools
import json
import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parent
NAN = float("nan")


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# 前段の道具(流用元。複製しない)
sp = _load("o3c_signal_policy", "o3c_signal_policy.py")
cont = sp.cont
lg = sp.lg
js = sp.js
spread = _load("o3c_bitflyer_spread", "o3c_bitflyer_spread.py")

check_no_banned = cont.check_no_banned
quantiles = cont.quantiles
mean_se_cluster = cont.mean_se_cluster
day_equal_weight_mean = cont.day_equal_weight_mean
md5_of = cont.md5_of
write_csv = cont.write_csv
md_table = cont.md_table
count_numeric_cells = cont.count_numeric_cells
normalize_rows = cont.normalize_rows
_fmt = cont._fmt
STALENESS_MS = cont.STALENESS_MS
REACT_SIGN = cont.REACT_SIGN
price_at_or_after = sp.price_at_or_after

# ---------------------------------------------------------------------------
# 固定値(設計・委任文。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
SEED = 20260920
N_CASCADES_STAGE1 = 200          # 前半の動作確認(前段と同じ種・同じ本数)
N_CASCADES_STAGE2 = 2000
DELAYS_S = sp.DELAYS_S           # (0.5, 1, 2)
MAIN_DELAY = sp.MAIN_DELAY       # 1
GRID_DELAY_S = 1                 # ② の格子は遅れ 1 秒(委任文)
CASCADE_END_GAP_S = sp.CASCADE_END_GAP_S   # 60
LABEL_VALUE = "value_continuation_60"
LABEL_LIQ = "label_60"
VALUE_CONT_BP = cont.VALUE_CONT_BP   # 5.0
LABEL_MAIN_S = cont.LABEL_MAIN       # 60
BAND_STEP = 0.02                 # 帯の幅(L-277 の規則)
FRONT_HALF = "前半"
BACK_HALF = "後半"

ROWS_CONTINUE = sp.ROWS_CONTINUE
ROWS_MATERIALS = sp.ROWS_MATERIALS
DATA_ROOT = cont.DEFAULT_DATA_ROOT
CANDLES_DIR = (REPO_ROOT / "backtest_data"
               / "bitflyer_lightchart_FX_BTC_JPY_1m_20260906")

OUT_ROOT = REPO_ROOT / "backtest_data" / "o3c_signal_value_20260921"
DEFAULT_OUT = OUT_ROOT / "stage1_firsthalf"
DEFAULT_OUT_STAGE2 = OUT_ROOT / "stage2_secondhalf"
SPREAD_DIR = OUT_ROOT / "spread"
CONFIG_VALUE_FIRST = REPO_ROOT / "config" / "o3c_signal_logit_value_first.yaml"
CONFIG_VALUE_CHAIN = REPO_ROOT / "config" / "o3c_signal_logit_value_chain.yaml"
ECDF_VALUE_FIRST = OUT_ROOT / "logit_ecdf_value_first.npz"
ECDF_VALUE_CHAIN = OUT_ROOT / "logit_ecdf_value_chain.npz"
DELEGATION = "docs/DATA/delegations/20260921_o3c_signal_value_prompt.md"
DESIGN = "docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md"

# 状態機械の記号(前段の用語表。流用)
POS_NONE, POS_WITH, POS_AGAINST = sp.POS_NONE, sp.POS_WITH, sp.POS_AGAINST
JUDGE_STOP, JUDGE_CONTINUE, JUDGE_UNKNOWN = (sp.JUDGE_STOP, sp.JUDGE_CONTINUE,
                                             sp.JUDGE_UNKNOWN)
TYPE_A, TYPE_B = sp.TYPE_A, sp.TYPE_B
POS_1ST, POS_CHAIN = sp.POS_1ST, sp.POS_CHAIN
JUDGED_POLICIES = sp.JUDGED_POLICIES
ALL_POLICIES = sp.ALL_POLICIES
COUNT_JUDGE_POLICIES = sp.COUNT_JUDGE_POLICIES
POLICY_IS_BASELINE = sp.POLICY_IS_BASELINE

# ② の格子(設計 §5。事前に固定する)
ENTRY_POS_LEVELS = ("1件目から", "2件目以降だけ", "3件目以降だけ")
COND_MATERIALS = {"材料12": "mat12_notional_over_max_recent_print",
                  "材料14": "mat14_trade_count_60s",
                  "材料15": "mat15_burst_ratio_10s_over_60s"}
COND_LEVELS = ("なし", "材料12≥p75", "材料12≥p90", "材料14≥p75", "材料14≥p90",
               "材料15≥p75", "材料15≥p90")
EXIT_LEVELS = ("連鎖の終わり+d", "最後のプリント+300秒+d", "入ってから300秒+d")
STOP_LEVELS = ("なし", "含み損20bp", "含み損50bp")
STOP_BP = {"なし": None, "含み損20bp": 20.0, "含み損50bp": 50.0}
EXIT_HOLD_S = 300
N_GRID = len(ENTRY_POS_LEVELS) * len(COND_LEVELS) * len(EXIT_LEVELS) * len(STOP_LEVELS)

COST_NONE, COST_MAIN, COST_P75 = "費用なし", "費用あり(主のc)", "費用あり(p75)"


# ===========================================================================
# 0. 前半だけの門(委任文【作るもの】1)
# ===========================================================================
def _rel(path: Path) -> str:
    try:
        return str(Path(path).relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def assert_front_half_only(df: pd.DataFrame, where: str) -> pd.DataFrame:
    """`half` 列に「前半」以外が 1 行でもあれば例外で止まる。"""
    if "half" not in df.columns:
        raise RuntimeError(f"[止め] {where}: half 列が無い(前半だけの確認ができない)")
    bad = sorted(set(df["half"].astype(str)) - {FRONT_HALF})
    if bad:
        raise RuntimeError(f"[止め] 段1は前半だけ。{where} に前半以外の行がある: {bad}")
    return df


def require_front_half(half: str) -> str:
    if str(half) != FRONT_HALF:
        raise RuntimeError(f"[止め] 段1は前半だけ。指定された半期: {half}")
    return half


# ===========================================================================
# 1. 入力(前半)
# ===========================================================================
def load_prints(half: str = FRONT_HALF, rows_continue: Path = ROWS_CONTINUE
                ) -> pd.DataFrame:
    """`rows_continue.csv.gz` の `kind == "print"` のうち指定した半期の行。
    (`kind == "q7_candidate"` の 22,545 行は読まない。)"""
    df = pd.read_csv(rows_continue, low_memory=False)
    df = df[(df["kind"] == "print") & (df["half"] == str(half))].copy()
    if df.empty:
        raise RuntimeError(f"[止め] {rows_continue} に {half} のプリントが無い")
    df["ts_ms"] = df["ts_ms"].astype(np.int64)
    return df.sort_values(["bundle_id", "ts_ms"]).reset_index(drop=True)


def load_stage1_prints(rows_continue: Path = ROWS_CONTINUE) -> pd.DataFrame:
    df = load_prints(FRONT_HALF, rows_continue)
    return assert_front_half_only(df, "rows_continue(段1)")


def cascades_from_prints(df: pd.DataFrame) -> dict:
    return sp.cascades_from_prints(df)


def chain_ids_in_day_order(cascades: dict) -> list:
    """連鎖の id を (日, 最初のプリントの時刻) の順に並べる(日ごとの約定を
    1 回読めば済むようにするため。`bundle_id` の並びが日の並びと同じとは限らない)。"""
    return [bid for bid, _k in sorted(
        ((bid, (str(pr[0]["day"]), int(pr[0]["ts_ms"]))) for bid, pr in cascades.items()),
        key=lambda x: x[1])]


# ===========================================================================
# 2. ①: 値段のラベルでの当てはめ(`fit_beta_front_half(label_col=...)`)
# ===========================================================================
def build_scene_frames(rows_materials: Path = ROWS_MATERIALS,
                       rows_continue: Path = ROWS_CONTINUE) -> tuple:
    """材料の列を持つファイルに値段のラベルを付け、前半を 1 件目 / 連鎖の中に分ける。"""
    mat = pd.read_csv(rows_materials, low_memory=False)
    lab = pd.read_csv(rows_continue, usecols=["print_id", "kind", LABEL_VALUE],
                      low_memory=False)
    lab = lab[lab["kind"] == "print"][["print_id", LABEL_VALUE]]
    df = mat.merge(lab, on="print_id", how="left")
    fh = df[df["half"] == FRONT_HALF].reset_index(drop=True)
    assert_front_half_only(fh, "rows_materials(段1)")
    cand1 = pd.to_numeric(fh["cand_1"], errors="coerce")
    return (fh[cand1 == 0].reset_index(drop=True),
            fh[cand1 > 0].reset_index(drop=True))


def add_n2_by_day(sb, df_first: pd.DataFrame) -> pd.DataFrame:
    """N2(1 件目だけ)を日ごとに計算する(`lg.add_n2_column` をそのまま使い、
    日が変わるたびに約定のキャッシュを空にして記憶を抑える)。"""
    parts = []
    for day, g in df_first.groupby("day", sort=True):
        parts.append(lg.add_n2_column(sb, g.reset_index(drop=True)))
        sb._window_cache.clear()
        sb._raw_trade_cache.clear()
    return pd.concat(parts, ignore_index=True)


def fit_value_logit(df_first: pd.DataFrame, df_chain: pd.DataFrame) -> dict:
    """前半だけで値段のラベルの logistic を当てはめ、5 分割 OOF も返す。"""
    out = {}
    for key, df_s, features, scene, cfg, ecdf_path in (
            ("first", df_first, lg.FEATURES_FIRST, "1件目",
             CONFIG_VALUE_FIRST, ECDF_VALUE_FIRST),
            ("chain", df_chain, lg.FEATURES_CHAIN, "連鎖の中",
             CONFIG_VALUE_CHAIN, ECDF_VALUE_CHAIN)):
        assert_front_half_only(df_s, f"当てはめ({scene})")
        res = lg.run_scene(df_s, features, scene, label_col=LABEL_VALUE)
        # 委任文が名指しする経路そのもの。`run_scene` の全件当てはめと一致することを
        # 毎回確かめる(同じ前半・同じ材料・同じラベルなので一致するはず)。
        beta_named = lg.fit_beta_front_half(df_s, features, label_col=LABEL_VALUE)
        max_gap = float(np.max(np.abs(beta_named - res["beta"])))
        if max_gap > 1e-8:
            raise RuntimeError(f"[止め] {scene}: fit_beta_front_half と run_scene の"
                               f"係数が食い違う(最大差 {max_gap})")
        lg.save_ecdf_npz(ecdf_path, res["ecdf"])
        doc = {
            "_由来": (f"scripts/o3c_signal_value.py stage1。前半全件({res['n']} 件、"
                    f"{scene})で `fit_beta_front_half(label_col=\"{LABEL_VALUE}\")` = "
                    "ニュートン法(L2 1e-3、sklearn 不使用)。入力は前半の経験分布の"
                    "中央順位(`apply_frozen_rank`、欠測 0.5)。**前段の清算のラベルの"
                    "係数(config/o3c_signal_logit_{first,chain}.yaml)は触っていない。**"),
            "判断の対象": LABEL_VALUE,
            "場面": scene,
            "件数": res["n"],
            "材料": list(features),
            "ecdf_ファイル": _rel(ecdf_path),
            "ecdf_md5": lg.md5_of(ecdf_path),
            "係数": {"切片": float(res["beta"][0]),
                   **{f: float(b) for f, b in zip(features, res["beta"][1:])}},
        }
        cfg.parent.mkdir(parents=True, exist_ok=True)
        txt = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
        check_no_banned(txt, cfg.name)
        cfg.write_text(txt)
        out[key] = {"res": res, "df": df_s, "features": features, "scene": scene,
                    "beta": res["beta"], "config": cfg, "ecdf_path": ecdf_path}
    return out


# ===========================================================================
# 3. Q1: 0.02 刻みの較正表と「わからない」の帯(L-277 の規則)
# ===========================================================================
def calibration_table(prob: np.ndarray, y: np.ndarray, step: float = BAND_STEP) -> dict:
    """幅 `step` の帯ごとに、続く割合と 2 SE(二項 `sqrt(p(1-p)/n)`)を出し、
    基準率と 2 SE で区別できない帯を拾う。「わからない」= 基準率を跨ぐ位置の周りで
    連続している区別できない帯(L-277 の規則)。その下 = 止まる、上 = 続く。"""
    prob = np.asarray(prob, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(prob) & np.isfinite(y)
    prob, y = prob[ok], y[ok]
    base = float(y.mean()) if y.size else NAN
    n_bins = int(round(1.0 / step))
    rows = []
    for b in range(n_bins):
        lo, hi = b * step, (b + 1) * step
        m = (prob >= lo) & (prob < hi) if b < n_bins - 1 else (prob >= lo) & (prob <= hi)
        n = int(m.sum())
        if n == 0:
            continue
        rate = float(y[m].mean())
        se = math.sqrt(max(rate * (1.0 - rate), 0.0) / n)
        rows.append({"帯下端": round(lo, 4), "帯上端": round(hi, 4), "件数": n,
                     "続く割合": rate, "2SE": 2.0 * se,
                     "基準率": base,
                     "基準率と区別できない": int(abs(rate - base) <= 2.0 * se)})
    if not rows:
        return {"rows": [], "基準率": base, "帯": None}

    indist = [bool(r["基準率と区別できない"]) for r in rows]
    rates = [r["続く割合"] for r in rows]
    # 基準率を跨ぐ位置: 下から見て初めて基準率以上になる帯(無ければ基準率に最も近い帯)
    cross = None
    for i in range(1, len(rates)):
        if rates[i] >= base and rates[i - 1] < base:
            cross = i
            break
    if cross is None:
        cross = int(np.argmin([abs(r - base) for r in rates]))
    # 区別できない帯の連続区間のうち、跨ぐ位置を含むもの(無ければ最も近いもの)
    runs = []
    i = 0
    while i < len(rows):
        if indist[i]:
            j = i
            while j + 1 < len(rows) and indist[j + 1]:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    band = None
    if runs:
        containing = [r for r in runs if r[0] <= cross <= r[1]]
        if containing:
            band = containing[0]
        else:
            band = min(runs, key=lambda r: min(abs(r[0] - cross), abs(r[1] - cross)))
    for k, r in enumerate(rows):
        if band is not None and band[0] <= k <= band[1]:
            r["区分"] = JUDGE_UNKNOWN
        elif band is not None and k < band[0]:
            r["区分"] = JUDGE_STOP
        elif band is not None:
            r["区分"] = JUDGE_CONTINUE
        else:
            r["区分"] = JUDGE_STOP if r["続く割合"] < base else JUDGE_CONTINUE
    band_edges = (None if band is None
                  else (rows[band[0]]["帯下端"], rows[band[1]]["帯上端"]))
    return {"rows": rows, "基準率": base, "帯": band_edges,
            "跨ぐ位置の帯": (rows[cross]["帯下端"], rows[cross]["帯上端"])}


def judge_3way_with_band(prob, band) -> str:
    """帯(lo, hi)で 3 択にする。帯が無い(= 区別できない帯が 1 つも無い)ときは
    基準率の 2 値と同じ挙動になる(lo == hi)。確率が読めなければ「わからない」。"""
    if prob is None or not math.isfinite(float(prob)):
        return JUDGE_UNKNOWN
    if band is None:
        return JUDGE_UNKNOWN
    p, (lo, hi) = float(prob), band
    if p < lo:
        return JUDGE_STOP
    if p >= hi:
        return JUDGE_CONTINUE
    return JUDGE_UNKNOWN


def judge_2way_with_threshold(prob, thr: float) -> str:
    if prob is None or not math.isfinite(float(prob)):
        return JUDGE_UNKNOWN
    return JUDGE_CONTINUE if float(prob) >= float(thr) else JUDGE_STOP


def judge_perfect_value(value_label) -> str:
    """① の「完全な判断」= 事後の**値段のラベル**をそのまま判断に使う参照点
    (損益の上限ではない)。ラベルが読めなければ「わからない」。"""
    v = cont._f(value_label)
    if not math.isfinite(v):
        return JUDGE_UNKNOWN
    return JUDGE_CONTINUE if v >= 0.5 else JUDGE_STOP


# ===========================================================================
# 4. 日ごとの約定の窓(前段の `PriceCache` を広げて配列も出す)
# ===========================================================================
class WindowCache(sp.PriceCache):
    """`sp.PriceCache`(at_or_after)に、日ごとの配列そのものを返す口を足しただけ。"""

    def window_for(self, day: str):
        self.raw_at_or_after(cont.day_start_ms(day))   # 未読み込みならここで読む
        return self._window_cache[day]


def _seg_first_index(times: np.ndarray, t_ms: int) -> int:
    return int(np.searchsorted(times, int(t_ms), side="left"))


# ===========================================================================
# 5. 値段のラベルの再計算と 5 bp への到達時間(Q0・Q1)
# ===========================================================================
def value_label_and_time_to_target(times: np.ndarray, prices: np.ndarray,
                                   t0_ms: int, p0: float, sign: float,
                                   horizon_s: int = LABEL_MAIN_S,
                                   target_bp: float = VALUE_CONT_BP) -> tuple:
    """(再計算したラベル, 5 bp に初めて達するまでの秒)。
    `o3c_signal_continue.path_extreme_bp` と同じ窓 `(t0, t0+horizon]` を使い、
    その中で `sign*(p-p0)/p0*1e4 >= target_bp` になる最初の約定の時刻を返す。"""
    if times is None or times.size == 0 or not (math.isfinite(p0) and p0 > 0):
        return NAN, NAN
    hi_ms = int(t0_ms) + int(horizon_s) * 1000
    i0 = int(np.searchsorted(times, int(t0_ms), side="right"))
    i1 = int(np.searchsorted(times, hi_ms, side="right"))
    if i1 <= i0:
        return NAN, NAN
    seg = prices[i0:i1]
    move = sign * (seg - p0) / p0 * 1e4
    hit = np.nonzero(move >= target_bp)[0]
    if hit.size == 0:
        return 0.0, NAN
    return 1.0, float(int(times[i0 + int(hit[0])]) - int(t0_ms)) / 1000.0


def _recheck_rows_for_day(g: pd.DataFrame, day: str, times: np.ndarray,
                          prices: np.ndarray) -> list:
    rows = []
    if True:
        for r in g.itertuples(index=False):
            lab, sec = value_label_and_time_to_target(
                times, prices, int(r.t0_ms), float(r.p0), float(r.dir_sign))
            old = cont._f(getattr(r, LABEL_VALUE))
            rows.append({"print_id": r.print_id, "day": str(day),
                         "既存のラベル": old, "再計算したラベル": lab,
                         "一致": int((lab == lab and old == old and lab == old)
                                   or (lab != lab and old != old)),
                         "到達秒": sec,
                         "位置": (POS_1ST if cont._f(
                             getattr(r, sp.MAT1_COL)) == 0 else POS_CHAIN)})
    return rows


def recompute_value_labels(df_prints: pd.DataFrame, cache: WindowCache) -> list:
    """プリントごとに値段のラベルを再計算し、既存列と突き合わせた行を返す
    (日ごとに約定を 1 回だけ読む)。"""
    rows = []
    for day, g in df_prints.groupby("day", sort=True):
        times, prices = cache.window_for(str(day))
        rows.extend(_recheck_rows_for_day(g, str(day), times, prices))
    return rows


def time_to_target_table(recheck_rows: list) -> list:
    rows = []
    for scene in ("全体", POS_1ST, POS_CHAIN):
        sel = [r for r in recheck_rows
               if (scene == "全体" or r["位置"] == scene) and r["再計算したラベル"] == 1.0]
        v = np.array([r["到達秒"] for r in sel], dtype=float)
        v = v[np.isfinite(v)]
        q = quantiles(v, [10, 25, 50, 75, 90]) if v.size else [NAN] * 5
        rows.append({
            "場面": scene, "値段のラベルが1の件数": len(sel), "秒が取れた件数": int(v.size),
            "p10_秒": q[0], "p25_秒": q[1], "p50_秒": q[2], "p75_秒": q[3],
            "p90_秒": q[4],
            "1秒未満の割合": (float(np.mean(v < 1.0)) if v.size else NAN),
            "2秒未満の割合": (float(np.mean(v < 2.0)) if v.size else NAN)})
    return rows


# ===========================================================================
# 6. ② の格子(設計 §5)
# ===========================================================================
def grid_combos() -> list:
    """189 組(位置 3 × 条件 7 × 出口 3 × 損切り 3)を事前に固定した順で列挙する。"""
    return [{"入る位置": a, "入る条件": b, "出口": c, "損切り": d}
            for a, b, c, d in itertools.product(
                ENTRY_POS_LEVELS, COND_LEVELS, EXIT_LEVELS, STOP_LEVELS)]


def condition_cuts(df_front: pd.DataFrame) -> dict:
    """入る条件の分位(前半のプリント全件で切る)。"""
    cuts = {}
    for name, col in COND_MATERIALS.items():
        v = pd.to_numeric(df_front[col], errors="coerce").to_numpy(float)
        v = v[np.isfinite(v)]
        q = quantiles(v, [75, 90]) if v.size else [NAN, NAN]
        cuts[f"{name}≥p75"] = (col, q[0])
        cuts[f"{name}≥p90"] = (col, q[1])
    return cuts


def exit_ts_of(prints: list, entry_idx: int, exit_level: str) -> int:
    last_ts = int(prints[-1]["ts_ms"])
    if exit_level == EXIT_LEVELS[0]:
        return last_ts + CASCADE_END_GAP_S * 1000
    if exit_level == EXIT_LEVELS[1]:
        return last_ts + EXIT_HOLD_S * 1000
    return int(prints[entry_idx]["ts_ms"]) + EXIT_HOLD_S * 1000


def simulate_reverse_entry(prints: list, side_sign: float, entry_idx: int,
                           exit_level: str, stop_bp, delay_s: float,
                           times: np.ndarray, prices: np.ndarray) -> dict:
    """② の 1 本: `entry_idx` 件目のプリントで逆張りで入り、`exit_level` で出る。
    損切りがあれば「含み損が閾値に達した最初の約定の時刻 + d」以後の最初の約定で出る。
    価格は全て `at_or_after`(ts + 遅れ 以後)。"""
    delay_ms = int(round(float(delay_s) * 1000))
    blank = {"入った": 0, "欠測": 0, "pnl_bp": NAN, "建玉の回数": 0, "保有秒": NAN,
             "出口の理由": "入らない", "入りの目標時刻": None, "入りの約定時刻": None,
             "出の目標時刻": None, "出の約定時刻": None, "損切りの引き金時刻": None}
    if entry_idx >= len(prints):
        return blank
    entry_ts = int(prints[entry_idx]["ts_ms"])
    t_in = entry_ts + delay_ms
    p_in, m_in = price_at_or_after(times, prices, t_in, STALENESS_MS)
    if p_in != p_in:
        return {**blank, "入った": 1, "欠測": 1, "建玉の回数": 1, "出口の理由": "欠測",
                "入りの目標時刻": t_in}
    direction = -float(side_sign)          # 全部逆張り
    t_out = exit_ts_of(prints, entry_idx, exit_level) + delay_ms
    reason = exit_level
    t_trigger = None
    if stop_bp is not None and t_out > m_in:
        i0 = _seg_first_index(times, m_in)
        i1 = _seg_first_index(times, t_out + 1)
        if i1 > i0:
            seg = prices[i0:i1]
            pnl_path = direction * (seg - p_in) / p_in * 1e4
            hit = np.nonzero(pnl_path <= -float(stop_bp))[0]
            if hit.size:
                t_trigger = int(times[i0 + int(hit[0])])
                t_out = t_trigger + delay_ms
                reason = f"損切り({stop_bp:.0f}bp)"
    p_out, m_out = price_at_or_after(times, prices, t_out, STALENESS_MS)
    if p_out != p_out:
        return {**blank, "入った": 1, "欠測": 1, "建玉の回数": 1, "出口の理由": "欠測",
                "入りの目標時刻": t_in, "入りの約定時刻": m_in, "出の目標時刻": t_out,
                "損切りの引き金時刻": t_trigger}
    pnl = direction * (p_out - p_in) / p_in * 1e4
    return {"入った": 1, "欠測": 0, "pnl_bp": float(pnl), "建玉の回数": 1,
            "保有秒": (m_out - m_in) / 1000.0, "出口の理由": reason,
            "入りの目標時刻": t_in, "入りの約定時刻": m_in,
            "出の目標時刻": t_out, "出の約定時刻": m_out,
            "損切りの引き金時刻": t_trigger}


def run_grid_core(cascades: dict, cache: WindowCache, delay_s: float = GRID_DELAY_S
                  ) -> dict:
    """連鎖ごとに(入る位置 3 × 出口 3 × 損切り 3 = 27 通り)を 1 回だけ計算する
    (条件 7 はこの 27 通りの**絞り込み**なので、189 組を数え直す必要はない)。"""
    per_chain = {}
    n_done = 0
    for bid in chain_ids_in_day_order(cascades):
        prints = cascades[bid]
        day = str(prints[0]["day"])
        side_sign = REACT_SIGN[str(prints[0]["side"])]
        times, prices = cache.window_for(day)
        res = {}
        for ei, _lvl in enumerate(ENTRY_POS_LEVELS):
            for ex in EXIT_LEVELS:
                for st in STOP_LEVELS:
                    res[(ei, ex, st)] = simulate_reverse_entry(
                        prints, side_sign, ei, ex, STOP_BP[st], delay_s,
                        times, prices)
        per_chain[bid] = {"day": day, "n_prints": len(prints), "結果": res,
                          "entry_rows": prints}
        n_done += 1
        if n_done % 1000 == 0:
            print(f"  [②] {n_done}/{len(cascades)} 本", flush=True)
    return per_chain


def front_half_day_pass(prints_df: pd.DataFrame, cascades: dict,
                        mat_first: pd.DataFrame, sb, cache: WindowCache,
                        delay_s: float = GRID_DELAY_S, cost_bp: float = 0.0) -> dict:
    """**日ごとに約定を 1 回だけ読み**、その日のぶんをまとめて計算する:
      (1) N2(1 件目の材料。`lg.add_n2_column` をそのまま呼ぶ)
      (2) 値段のラベルの再計算と 5 bp への到達時間
      (3) ② の 27 通り(入る位置 3 × 出口 3 × 損切り 3。条件 7 は後で絞り込むだけ)
      (4) Q5b (b) の 1 分の始値(bitFlyer の 1 分足と Binance の同じ近似)
    N2 の窓は前後に広い窓をそのまま渡す(`price_at_or_before` / `n2_position` は
    ts 以前しか見ないので、後ろに伸びた分は結果に入らない)。"""
    chains_by_day = defaultdict(list)
    for bid, pr in cascades.items():
        chains_by_day[str(pr[0]["day"])].append(bid)
    for d in chains_by_day:
        chains_by_day[d].sort(key=lambda b: int(cascades[b][0]["ts_ms"]))
    mat_by_day = {str(d): g.reset_index(drop=True)
                  for d, g in mat_first.groupby("day", sort=True)}
    bf_ts, bf_open = load_bitflyer_1m()

    n2_parts, recheck, per_chain, minute_rows = [], [], {}, []
    days = sorted(set(prints_df["day"].astype(str)))
    for k, day in enumerate(days):
        times, prices = cache.window_for(day)
        sb._window_cache = {day: (times, prices)}
        sb._raw_trade_cache.clear()
        if day in mat_by_day:
            n2_parts.append(lg.add_n2_column(sb, mat_by_day[day]))
        g = prints_df[prints_df["day"].astype(str) == day]
        recheck.extend(_recheck_rows_for_day(g, day, times, prices))
        mt, mp = minute_open_map(times, prices)
        for bid in chains_by_day.get(day, []):
            prints = cascades[bid]
            side_sign = REACT_SIGN[str(prints[0]["side"])]
            res = {}
            for ei in range(len(ENTRY_POS_LEVELS)):
                for ex in EXIT_LEVELS:
                    for st in STOP_LEVELS:
                        res[(ei, ex, st)] = simulate_reverse_entry(
                            prints, side_sign, ei, ex, STOP_BP[st], delay_s,
                            times, prices)
            per_chain[bid] = {"day": day, "n_prints": len(prints), "結果": res,
                              "entry_rows": prints}
            direction = -side_sign
            entry_ts = int(prints[0]["ts_ms"])
            exit_ts = int(prints[-1]["ts_ms"]) + CASCADE_END_GAP_S * 1000
            v_bf = pnl_next_minute_open(entry_ts, exit_ts, direction, bf_ts, bf_open)
            v_bx = pnl_next_minute_open(entry_ts, exit_ts, direction, mt, mp)
            minute_rows.append({"bundle_id": bid, "day": day,
                                "bitFlyer_bp": (v_bf - cost_bp if v_bf == v_bf else NAN),
                                "Binance_bp": (v_bx - cost_bp if v_bx == v_bx else NAN)})
        if (k + 1) % 40 == 0:
            print(f"  [日ごとの一巡] {k + 1}/{len(days)} 日", flush=True)
    df_first = pd.concat(n2_parts, ignore_index=True) if n2_parts else mat_first
    return {"df_first_with_n2": df_first, "recheck": recheck,
            "per_chain": per_chain, "minute_rows": minute_rows}


def _combo_metrics(vals: np.ndarray, days: np.ndarray, n_all: int,
                   first_mask: np.ndarray) -> dict:
    q = quantiles(vals, [25, 50, 75]) if vals.size else [NAN] * 3
    m, se_c, _se_n, _nn, ndays = (mean_se_cluster(vals, days) if vals.size
                                  else (NAN, NAN, NAN, 0, 0))
    with_zero = np.zeros(n_all, dtype=float)
    with_zero[:vals.size] = vals
    return {
        "総収支_bp": float(vals.sum()) if vals.size else 0.0,
        "中央値_入った本のみ": q[1], "p25": q[0], "p75": q[2],
        "中央値_0含む": float(np.median(with_zero)) if n_all else NAN,
        "負の割合": float(np.mean(vals < 0)) if vals.size else NAN,
        "日等重み平均": day_equal_weight_mean(vals, days) if vals.size else NAN,
        "日クラスタSE": se_c, "入った本数": int(vals.size), "日数": ndays,
        "建玉の回数": int(vals.size),
        "前半の前_総収支_bp": float(vals[first_mask].sum()) if vals.size else 0.0,
        "前半の後_総収支_bp": float(vals[~first_mask].sum()) if vals.size else 0.0,
    }


def build_grid_table(per_chain: dict, cuts: dict, cost_bp: float,
                     split_day: str) -> list:
    """189 組の表。費用は 連鎖 1 本 = c × 建玉の回数(② はいつも 1 回)。"""
    rows = []
    for combo in grid_combos():
        ei = ENTRY_POS_LEVELS.index(combo["入る位置"])
        cond = combo["入る条件"]
        vals, days, firsts = [], [], []
        n_missing = 0
        n_cond_out = 0
        for bid, rec in per_chain.items():
            r = rec["結果"][(ei, combo["出口"], combo["損切り"])]
            if not r["入った"]:
                continue
            if cond != "なし":
                col, thr = cuts[cond]
                v = cont._f(rec["entry_rows"][ei].get(col))
                if not (math.isfinite(v) and math.isfinite(thr) and v >= thr):
                    n_cond_out += 1
                    continue
            if r["欠測"]:
                n_missing += 1
                continue
            vals.append(r["pnl_bp"] - cost_bp * r["建玉の回数"])
            days.append(rec["day"])
            firsts.append(rec["day"] <= split_day)
        v = np.array(vals, dtype=float)
        d = np.array(days, dtype=object)
        fm = np.array(firsts, dtype=bool)
        row = {**combo}
        row.update(_combo_metrics(v, d, len(per_chain), fm))
        row["欠測"] = n_missing
        row["条件で外れた本数"] = n_cond_out
        rows.append(row)
    return rows


def select_combo(grid_rows: list, median_col: str = "中央値_入った本のみ") -> dict:
    """事前に固定した規則: (a) 前半を日付順に 2 分割した両側で総収支 > 0、
    (b) 連鎖 1 本の中央値 > 0、を満たす組の中で総収支が最大の 1 組。
    満たす組が無ければ `選ばれた` を False にして返す(規則は緩めない)。"""
    ok = [r for r in grid_rows
          if r["前半の前_総収支_bp"] > 0 and r["前半の後_総収支_bp"] > 0
          and (r[median_col] == r[median_col]) and r[median_col] > 0]
    if not ok:
        return {"選ばれた": False, "規則を満たした組の数": 0, "使った中央値": median_col,
                "組": None}
    best = max(ok, key=lambda r: r["総収支_bp"])
    return {"選ばれた": True, "規則を満たした組の数": len(ok), "使った中央値": median_col,
            "組": {k: best[k] for k in ("入る位置", "入る条件", "出口", "損切り")},
            "総収支_bp": best["総収支_bp"], "中央値_入った本のみ": best["中央値_入った本のみ"],
            "中央値_0含む": best["中央値_0含む"],
            "前半の前_総収支_bp": best["前半の前_総収支_bp"],
            "前半の後_総収支_bp": best["前半の後_総収支_bp"],
            "入った本数": best["入った本数"]}


def combo_day_totals(per_chain: dict, cuts: dict, cost_bp: float, combo: dict) -> dict:
    """1 つの組の、日ごとの総収支(費用込み)。"""
    ei = ENTRY_POS_LEVELS.index(combo["入る位置"])
    acc = defaultdict(float)
    n = 0
    for _bid, rec in per_chain.items():
        r = rec["結果"][(ei, combo["出口"], combo["損切り"])]
        if not r["入った"] or r["欠測"]:
            continue
        if combo["入る条件"] != "なし":
            col, thr = cuts[combo["入る条件"]]
            val = cont._f(rec["entry_rows"][ei].get(col))
            if not (math.isfinite(val) and math.isfinite(thr) and val >= thr):
                continue
        acc[rec["day"]] += r["pnl_bp"] - cost_bp * r["建玉の回数"]
        n += 1
    return {"日ごとの総収支_bp": dict(acc), "入った本数": n}


PLAIN_COMBO = {"入る位置": ENTRY_POS_LEVELS[0], "入る条件": "なし",
               "出口": EXIT_LEVELS[0], "損切り": "なし"}


def _day_summary(day_tot: dict) -> dict:
    ser = sorted(day_tot["日ごとの総収支_bp"].items(), key=lambda kv: kv[1])
    vals = [v for _d, v in ser]
    return {"総収支_bp": float(sum(vals)), "入った本数": day_tot["入った本数"],
            "日数": len(ser),
            "負の日の割合": (float(sum(1 for v in vals if v < 0)) / len(vals)
                       if vals else NAN),
            "最も低い5日": {d: round(v, 2) for d, v in ser[:5]},
            "最も高い5日": {d: round(v, 2) for d, v in ser[-5:]},
            "2023-08-17": round(float(day_tot["日ごとの総収支_bp"].get(
                "2023-08-17", NAN)), 2)}


def build_grid_selected(grid_rows: list, chosen: dict, chosen_zero: dict,
                        per_chain: dict, cuts: dict, cost_bp: float,
                        split_day: str) -> dict:
    """`grid_selected.json` の中身。選んだ組と、その裏付けに使う日ごとの内訳。
    **2023-08-17 型の裾を損切りが切ったか**を読むため、素(全部逆張り)と
    素 + 損切り 20/50 bp、選んだ組と 選んだ組 + 損切り 20 bp を並べる。"""
    top = sorted(grid_rows, key=lambda r: -r["総収支_bp"])[:5]
    look = {"素(全部逆張り)": PLAIN_COMBO,
            "素 + 損切り20bp": {**PLAIN_COMBO, "損切り": STOP_LEVELS[1]},
            "素 + 損切り50bp": {**PLAIN_COMBO, "損切り": STOP_LEVELS[2]}}
    if chosen.get("選ばれた"):
        look["選んだ組"] = chosen["組"]
        look["選んだ組 + 損切り20bp"] = {**chosen["組"], "損切り": STOP_LEVELS[1]}
    breakdown = {name: _day_summary(combo_day_totals(per_chain, cuts, cost_bp, cb))
                 for name, cb in look.items()}
    return {
        "選ぶ規則(事前固定)": "(a) 前半を日付順に 2 分割した両側で総収支 > 0、"
                       "(b) 連鎖 1 本の中央値 > 0 を満たす組の中で総収支が最大の 1 組。"
                       "満たす組が無ければ「規則を満たす組は無かった」と書く(緩めない)",
        "2 分割の境の日": split_day,
        "費用_bp": cost_bp,
        "格子の組数": len(grid_rows),
        "選んだ組(主 = 入った本のみの中央値)": chosen,
        "参考(中央値を 0 含みで読んだ場合)": chosen_zero,
        "総収支の上位 5 組": [{k: r[k] for k in ("入る位置", "入る条件", "出口", "損切り",
                                          "総収支_bp", "中央値_入った本のみ",
                                          "前半の前_総収支_bp", "前半の後_総収支_bp",
                                          "入った本数")} for r in top],
        "日ごとの内訳(なぜを読むため)": breakdown,
    }


def knob_contribution(grid_rows: list, chosen: dict) -> list:
    """選んだ組について 1 ノブずつ他を固定して動かした総収支と、その差(4 表)。"""
    if not chosen.get("選ばれた"):
        return []
    base = chosen["組"]
    index = {(r["入る位置"], r["入る条件"], r["出口"], r["損切り"]): r for r in grid_rows}
    base_total = index[(base["入る位置"], base["入る条件"], base["出口"],
                        base["損切り"])]["総収支_bp"]
    rows = []
    for knob, levels in (("入る位置", ENTRY_POS_LEVELS), ("入る条件", COND_LEVELS),
                         ("出口", EXIT_LEVELS), ("損切り", STOP_LEVELS)):
        for lv in levels:
            key = dict(base)
            key[knob] = lv
            r = index[(key["入る位置"], key["入る条件"], key["出口"], key["損切り"])]
            rows.append({"ノブ": knob, "水準": lv, "選んだ組の水準": base[knob],
                         "総収支_bp": r["総収支_bp"],
                         "選んだ組との差_bp": r["総収支_bp"] - base_total,
                         "入った本数": r["入った本数"],
                         "中央値_入った本のみ": r["中央値_入った本のみ"]})
    return rows


# ===========================================================================
# 7. ① の方策(前半 200 本の動作確認)
# ===========================================================================
def compute_value_logit_probs(sb, df: pd.DataFrame, n2_by_pid: dict | None = None
                              ) -> dict:
    """print_id -> 値段のラベルの logistic の予測。`stage2.compute_logit_probs` と
    同じ経路(`apply_frozen_rank` だけ)で、読む係数・経験分布がこの単位のものになる。
    `n2_by_pid` を渡すと N2 を計算し直さない(日ごとの一巡で計算済みの値を使う。
    値そのものは `lg.add_n2_column` が出したもので、計算式は変えていない)。"""
    out = {}
    ecdf_first = lg.load_ecdf_npz(ECDF_VALUE_FIRST)
    ecdf_chain = lg.load_ecdf_npz(ECDF_VALUE_CHAIN)
    beta_first = sp.stage2.load_beta(CONFIG_VALUE_FIRST, lg.FEATURES_FIRST)
    beta_chain = sp.stage2.load_beta(CONFIG_VALUE_CHAIN, lg.FEATURES_CHAIN)
    cand1 = pd.to_numeric(df["cand_1"], errors="coerce")
    df_first = df[cand1 == 0].reset_index(drop=True)
    df_chain = df[cand1 > 0].reset_index(drop=True)
    if len(df_first):
        have = (n2_by_pid is not None
                and all(pid in n2_by_pid for pid in df_first["print_id"]))
        if have:
            df_first = df_first.copy()
            df_first["cand_N2"] = [n2_by_pid[pid] for pid in df_first["print_id"]]
        else:
            df_first = lg.add_n2_column(sb, df_first)
        p = lg.predict(lg.apply_frozen_rank(ecdf_first, lg.FEATURES_FIRST, df_first),
                       beta_first)
        out.update(dict(zip(df_first["print_id"].tolist(), p.tolist())))
    if len(df_chain):
        p = lg.predict(lg.apply_frozen_rank(ecdf_chain, lg.FEATURES_CHAIN, df_chain),
                       beta_chain)
        out.update(dict(zip(df_chain["print_id"].tolist(), p.tolist())))
    return out


def load_value_probs_for_cascades(cascades: dict, sb=None,
                                  materials_path: Path = ROWS_MATERIALS,
                                  n2_by_pid: dict | None = None) -> tuple:
    ids = {pr["print_id"] for prints in cascades.values() for pr in prints}
    mat = pd.read_csv(materials_path, low_memory=False)
    df = mat[mat["print_id"].isin(ids)].reset_index(drop=True)
    assert_front_half_only(df, "materials(200 本の動作確認)")
    if len(df) != len(ids):
        missing = ids - set(df["print_id"])
        raise RuntimeError(f"[止め] materials に無い print_id: {sorted(missing)[:5]}")
    sb = js.StateBuilder() if sb is None else sb
    prob_of = compute_value_logit_probs(sb, df, n2_by_pid)
    pos_of = {pid: sp.position_of(c1) for pid, c1 in zip(df["print_id"], df["cand_1"])}
    return prob_of, pos_of


def judgments_for_policy_value(prints: list, policy: str, prob_of: dict,
                               pos_of: dict, bands: dict, base_rates: dict) -> list:
    """① の判断(判断の対象 = 値段の続き)。前段 `judgments_for_policy` と同じ形で、
    帯・閾値・「完全な判断」だけが値段のラベルのものになる。"""
    if policy == "完全な判断":
        return [judge_perfect_value(p.get(LABEL_VALUE)) for p in prints]
    if policy == "規則":
        return [sp.judge_from_rule(p.get(sp.MAT1_COL)) for p in prints]
    out = []
    for p in prints:
        pid = p["print_id"]
        pos = pos_of.get(pid, POS_1ST)
        prob = prob_of.get(pid)
        if policy == "logistic_3択":
            out.append(judge_3way_with_band(prob, bands[pos]))
        elif policy == "logistic_2値0.5":
            out.append(judge_2way_with_threshold(prob, 0.5))
        elif policy == "logistic_2値基準率":
            out.append(judge_2way_with_threshold(prob, base_rates[pos]))
        else:
            raise ValueError(f"未知の方策: {policy}")
    return out


def run_policies(cascades: dict, prob_of: dict, pos_of: dict, bands: dict,
                 base_rates: dict, cache: WindowCache) -> dict:
    """前段 `run_simulation` と同じ組み立て(状態機械は `sp.simulate_cascade` /
    `sp.simulate_baseline` をそのまま呼ぶ)。判断だけが値段のラベルのもの。"""
    cascade_rows, print_rows = [], []
    judge_counts = defaultdict(int)
    action_counts = defaultdict(int)
    for bid in sorted(cascades.keys()):
        prints = cascades[bid]
        n = len(prints)
        side = str(prints[0]["side"])
        day = str(prints[0]["day"])
        s_sign = REACT_SIGN[side]
        end_ts = int(prints[-1]["ts_ms"]) + CASCADE_END_GAP_S * 1000
        sb_size = sp.size_bucket(n)
        judge_cache = {pol: judgments_for_policy_value(prints, pol, prob_of, pos_of,
                                                       bands, base_rates)
                       for pol in JUDGED_POLICIES}
        for pol in COUNT_JUDGE_POLICIES:
            for j, pr in enumerate(prints):
                judge_counts[(pol, pos_of.get(pr["print_id"], POS_1ST),
                              judge_cache[pol][j])] += 1
        for delay in DELAYS_S:
            price_fn = cache.raw_at_or_after
            for pol in JUDGED_POLICIES:
                for ptype in (TYPE_A, TYPE_B):
                    res = sp.simulate_cascade(prints, judge_cache[pol], s_sign, ptype,
                                              delay, price_fn, end_ts)
                    cascade_rows.append({
                        "bundle_id": bid, "day": day, "side": side,
                        "連鎖の大きさ": sb_size, "n_prints": n, "方策": pol, "型": ptype,
                        "遅れ_秒": delay, "pnl_bp": res["pnl_bp"],
                        "建玉の回数": res["n_entries"], "保有秒": res["hold_seconds"],
                        "入った": int(res["entered"]), "欠測": int(res["missing"]),
                        "最初に入った位置": sp.entry_bucket(res["first_entry_pos"])})
                    if delay == MAIN_DELAY:
                        for row in res["path"]:
                            action_counts[(pol, ptype, row["行動"])] += 1
                            print_rows.append({
                                "print_id": row["print_id"], "bundle_id": bid,
                                "day": day, "side": side, "方策": pol, "型": ptype,
                                "遅れ_秒": delay, "位置": row["位置"],
                                "判断": row["判断"], "行動": row["行動"],
                                "建玉": row["建玉"], "約定価格": row["約定価格"],
                                "レグ損益_bp": row["レグ損益_bp"]})
            for pol_name, direction in POLICY_IS_BASELINE.items():
                for ptype in (TYPE_A, TYPE_B):
                    res = sp.simulate_baseline(prints, s_sign, direction, delay,
                                               price_fn, end_ts)
                    cascade_rows.append({
                        "bundle_id": bid, "day": day, "side": side,
                        "連鎖の大きさ": sb_size, "n_prints": n, "方策": pol_name,
                        "型": ptype, "遅れ_秒": delay, "pnl_bp": res["pnl_bp"],
                        "建玉の回数": res["n_entries"], "保有秒": res["hold_seconds"],
                        "入った": int(res["entered"]), "欠測": int(res["missing"]),
                        "最初に入った位置": sp.entry_bucket(res["first_entry_pos"])})
                    if delay == MAIN_DELAY:
                        action_counts[(pol_name, ptype, res["path"][0]["行動"])] += 1
    return {"cascade_rows": cascade_rows, "print_rows": print_rows,
            "judge_counts": judge_counts, "action_counts": action_counts}


def apply_cost(cascade_rows: list, cost_bp: float) -> pd.DataFrame:
    """費用 = c × 建玉の回数(型 B のドテン 1 回 = c)を損益から引く。"""
    cdf = pd.DataFrame(cascade_rows).copy()
    cdf["pnl_bp"] = cdf["pnl_bp"] - float(cost_bp) * cdf["建玉の回数"].astype(float)
    return cdf


# ===========================================================================
# 8. Q5b: 経路差の下見
# ===========================================================================
def bitflyer_day_arrays(day: str, tardis_dir: Path = spread.TARDIS_DIR) -> tuple:
    """標本日の bitFlyer 約定(時刻 ms・値段)。無ければ (空, 空)。"""
    path = Path(tardis_dir) / f"FX_BTC_JPY_{day.replace('-', '')}.csv.gz"
    if not path.exists():
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    t_ms, price, _sgn = spread.load_tardis_day(path)
    return t_ms, price


def minute_open_map(times: np.ndarray, prices: np.ndarray) -> tuple:
    """約定列から「各 1 分の始値」= その分の最初の約定の値段(時刻 ms の配列と値段)。"""
    if times.size == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    minute = (times // 60_000) * 60_000
    first = np.nonzero(np.r_[True, minute[1:] != minute[:-1]])[0]
    return minute[first], prices[first]


def next_minute_open(minute_ts: np.ndarray, minute_px: np.ndarray, t_ms: int,
                     tol_ms: int = STALENESS_MS):
    """`t_ms` の**次の 1 分**の始値(その分に約定が無ければ `tol_ms` まで先を探す)。"""
    target = (int(t_ms) // 60_000) * 60_000 + 60_000
    if minute_ts.size == 0:
        return NAN
    i = int(np.searchsorted(minute_ts, target, side="left"))
    if i >= minute_ts.size or int(minute_ts[i]) - target > tol_ms:
        return NAN
    return float(minute_px[i])


def load_bitflyer_1m(years=(2023, 2024), candles_dir: Path = CANDLES_DIR) -> tuple:
    ts_all, op_all = [], []
    for y in years:
        p = Path(candles_dir) / f"candles_1m_{y}.csv.gz"
        if not p.exists():
            continue
        df = pd.read_csv(p, usecols=["ts", "open"])
        # pandas の版によって `to_datetime` の刻み(s / us / ns)が変わるので、
        # 明示的に ms へそろえてから整数にする。
        dti = pd.to_datetime(df["ts"], utc=True).dt.tz_localize(None)
        t = dti.values.astype("datetime64[ms]").astype(np.int64)
        ts_all.append(t)
        op_all.append(df["open"].to_numpy(float))
    if not ts_all:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    ts = np.concatenate(ts_all)
    op = np.concatenate(op_all)
    o = np.argsort(ts, kind="stable")
    return ts[o], op[o]


def pnl_next_minute_open(entry_ts: int, exit_ts: int, direction: float,
                         minute_ts: np.ndarray, minute_px: np.ndarray) -> float:
    """入る・出る時刻の**次の 1 分の始値**で測った損益(bp)。"""
    p_in = next_minute_open(minute_ts, minute_px, entry_ts)
    p_out = next_minute_open(minute_ts, minute_px, exit_ts)
    if not (p_in == p_in and p_out == p_out and p_in > 0):
        return NAN
    return float(direction) * (p_out - p_in) / p_in * 1e4


def paired_diff_row(label: str, a: list, b: list, name_a: str, name_b: str) -> dict:
    """対差(a − b)の分布。符号が変わった本数も出す。"""
    av = np.array(a, dtype=float)
    bv = np.array(b, dtype=float)
    ok = np.isfinite(av) & np.isfinite(bv)
    d = av[ok] - bv[ok]
    q = quantiles(d, [25, 50, 75]) if d.size else [NAN] * 3
    sign_flip = int(np.sum(np.sign(av[ok]) != np.sign(bv[ok]))) if d.size else 0
    return {"区分": label, f"{name_a}": float(np.nansum(av[ok])) if d.size else NAN,
            f"{name_b}": float(np.nansum(bv[ok])) if d.size else NAN,
            "対の数": int(d.size), "対差の中央値_bp": q[1], "対差のp25_bp": q[0],
            "対差のp75_bp": q[2], "符号が変わった本数": sign_flip,
            "対差の平均_bp": float(np.mean(d)) if d.size else NAN}


# ===========================================================================
# 9. 合成の連鎖(状態機械・損切り・出口 3 種・費用の加算の道筋)
# ===========================================================================
def build_synthetic_traces_value(cost_bp: float = 2.0) -> list:
    """前段の合成 3 本(状態機械)+ この単位で足した ② の道筋(出口 3 種 × 損切り)+
    費用の加算。価格は `100 + t_ms/1e7` の単調増加な偽の約定列(手計算しやすい)。"""
    rows = []
    for r in sp.build_synthetic_traces():
        rows.append({"区分": "①の状態機械(前段の合成3本)", **r})

    # ② の合成: 値段が単調に上がる列(SELL の清算 → 逆張り = 買い建玉 → 勝つ)と、
    # 単調に下がる列(逆張りの建玉が負ける → 損切りが効く)の 2 本。
    times = np.arange(0, 700_000 + 1, 1_000, dtype=np.int64)
    up = 100.0 + times / 1.0e7
    down = 100.0 - times / 1.0e7 * 30.0      # 700 秒で −21 bp 相当の下げ
    prints = [{"print_id": "g1", "ts_ms": 0, "side": "SELL", "day": "2023-07-01"},
              {"print_id": "g2", "ts_ms": 30_000, "side": "SELL", "day": "2023-07-01"}]
    for series_name, px in (("値段が上がる列", up), ("値段が下がる列", down)):
        for ex in EXIT_LEVELS:
            for st in STOP_LEVELS:
                r = simulate_reverse_entry(prints, REACT_SIGN["SELL"], 0, ex,
                                           STOP_BP[st], 1, times, px)
                gross = r["pnl_bp"]
                net = (gross - cost_bp * r["建玉の回数"]) if gross == gross else NAN
                rows.append({
                    "区分": f"②の格子({series_name})", "合成連鎖": f"{ex} / {st}",
                    "print_id": "g1", "ts_ms": 0, "判断": "(②は判断を使わない)",
                    "行動": "新規_逆張り", "建玉": POS_AGAINST,
                    "約定価格": "", "レグ損益_bp": "",
                    "出口の理由": r["出口の理由"], "保有秒": _fmt(r["保有秒"], 3),
                    "費用なしの損益_bp": _fmt(gross, 4),
                    f"費用 c={cost_bp:.4f} を引いた損益_bp": _fmt(net, 4),
                    "建玉の回数": r["建玉の回数"]})
    return rows


# ===========================================================================
# 10. 出力
# ===========================================================================
def _dist_rows_with_cost(cascade_rows: list, costs: dict) -> tuple:
    dist, posb = [], []
    for label, c in costs.items():
        cdf = apply_cost(cascade_rows, c)
        for r in sp.build_dist_table(cdf):
            dist.append({"費用": label, "c_bp": c, **r})
        for r in sp.build_position_breakdown(cdf):
            posb.append({"費用": label, "c_bp": c, **r})
    return dist, posb


def write_output(out_dir: Path, tables: list, summary: dict) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    norm = {name: normalize_rows(rows) for name, rows, _k in tables}
    for name, _rows, _k in tables:
        if name.endswith(".csv"):
            write_csv(out_dir / name, norm[name])
    md = [f"# O3C SIGNAL 値段の続き — {summary['段']}の表", "",
          f"- 委任文: `{DELEGATION}`", f"- 設計: `{DESIGN}`",
          f"- 費用 c(主) = {summary['費用']['主のc_bp']:.4f} bp / "
          f"p75 = {summary['費用']['p75_bp']:.4f} bp", ""]
    for name, _rows, key in tables:
        md += [f"## {key}(`{name}`、{len(norm[name])} 行)", "",
               md_table(norm[name]), ""]
    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "tables.md")
    (out_dir / "tables.md").write_text(mdtxt, encoding="utf-8")

    summary["行数の内訳"] = {name: len(norm[name]) for name, _r, _k in tables}
    summary["行数の合計"] = sum(len(v) for v in norm.values())
    summary["数値セル数(tables.md)"] = count_numeric_cells(mdtxt)
    txt = json.dumps(summary, ensure_ascii=False, indent=2, default=str)
    check_no_banned(txt, "summary.json")
    (out_dir / "summary.json").write_text(txt, encoding="utf-8")

    lines = []
    for p in sorted(out_dir.iterdir()):
        if p.name == "MD5SUMS" or p.is_dir():
            continue
        lines.append(f"{md5_of(p)}  {p.name}")
    (out_dir / "MD5SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


# ===========================================================================
# 11. 段1
# ===========================================================================
def _rename_report(report: dict) -> dict:
    """`lg.run_scene` の見出しは清算のラベル向けの語なので、値段のラベルの語に直す
    (中身の数値は `label_col` で計算済み。見出しだけの付け替え)。"""
    out = dict(report)
    if "基準率(label_60、前半)" in out:
        out[f"基準率({LABEL_VALUE}、前半)"] = out.pop("基準率(label_60、前半)")
    return out


def run_stage1(out_dir: Path = DEFAULT_OUT, half: str = FRONT_HALF,
               spread_dir: Path = SPREAD_DIR) -> dict:
    require_front_half(half)
    t0 = time.time()
    c_main, c_p75 = spread.read_cost(spread_dir)
    print(f"[段1-0] 費用 c(主) = {c_main:.4f} bp / p75 = {c_p75:.4f} bp", flush=True)

    prints_df = load_stage1_prints()
    all_cascades = cascades_from_prints(prints_df)
    days = sorted(set(prints_df["day"].astype(str)))
    split_day = days[len(days) // 2 - 1]
    print(f"[段1-1] 前半 プリント {len(prints_df)} 件 / 連鎖 {len(all_cascades)} 本 / "
          f"日 {len(days)}(2 分割の境 {split_day})", flush=True)

    # --- 日ごとの一巡(N2・ラベル再計算・②の 27 通り・1 分の始値) ----------
    sb = js.StateBuilder()
    df_first, df_chain = build_scene_frames()
    print(f"[段1-2] 1件目 {len(df_first)} 件 / 連鎖の中 {len(df_chain)} 件 "
          f"({time.time() - t0:.0f}s)", flush=True)
    cache = WindowCache(DATA_ROOT)
    day_pass = front_half_day_pass(prints_df, all_cascades, df_first, sb, cache,
                                   GRID_DELAY_S, c_main)
    df_first = day_pass["df_first_with_n2"]
    recheck = day_pass["recheck"]
    per_chain = day_pass["per_chain"]
    minute_rows = day_pass["minute_rows"]
    n_match = sum(r["一致"] for r in recheck)
    ttt = time_to_target_table(recheck)
    print(f"[段1-3] 日ごとの一巡を終えた(ラベル再計算 {n_match}/{len(recheck)} 一致、"
          f"②の下ごしらえ {len(per_chain)} 本、{time.time() - t0:.0f}s)", flush=True)

    # --- ① の当てはめ ------------------------------------------------------
    fits = fit_value_logit(df_first, df_chain)
    print(f"[段1-4] 当てはめと 5 分割 OOF ({time.time() - t0:.0f}s)", flush=True)

    calib, bands, base_rates, calib_rows = {}, {}, {}, {}
    for key, scene in (("first", POS_1ST), ("chain", POS_CHAIN)):
        res = fits[key]["res"]
        dfs = fits[key]["df"]
        y = pd.to_numeric(dfs[LABEL_VALUE], errors="coerce").to_numpy(float)
        pid = dfs["print_id"].astype(str).to_numpy()
        oof = np.array([res["oof_by_pid"].get(p, NAN) for p in pid], dtype=float)
        cal = calibration_table(oof, y)
        calib[key] = cal
        bands[scene] = cal["帯"]
        base_rates[scene] = cal["基準率"]
        calib_rows[key] = [{"場面": scene, **r} for r in cal["rows"]]
        print(f"[段1-5] {scene}: 基準率 {cal['基準率']:.4f} / 帯 {cal['帯']} / "
              f"順位分離 {res['report']['5fold_out_of_fold_順位分離']:.4f}", flush=True)

    # --- ② の格子 ----------------------------------------------------------
    cuts = condition_cuts(prints_df)
    grid_rows = build_grid_table(per_chain, cuts, c_main, split_day)
    chosen = select_combo(grid_rows)
    chosen_zero = select_combo(grid_rows, median_col="中央値_0含む")
    knob_rows = knob_contribution(grid_rows, chosen)
    print(f"[段1-7] 格子 {len(grid_rows)} 組 / 選ばれた: {chosen['選ばれた']} "
          f"({time.time() - t0:.0f}s)", flush=True)

    # --- 前半 200 本の動作確認 ---------------------------------------------
    select_info = sp.stage1_select(k=N_CASCADES_STAGE1)
    picked = select_info["cascades"]
    n2_by_pid = dict(zip(df_first["print_id"].astype(str).tolist(),
                         pd.to_numeric(df_first["cand_N2"],
                                       errors="coerce").tolist()))
    sample_days = {spread.day_of_path(q) for q in spread.sample_day_paths()}
    need_probs = dict(picked)
    for bid, pr in all_cascades.items():
        if str(pr[0]["day"]) in sample_days:
            need_probs[bid] = pr
    prob_of, pos_of = load_value_probs_for_cascades(need_probs, sb,
                                                    n2_by_pid=n2_by_pid)
    built = run_policies(picked, prob_of, pos_of, bands, base_rates, cache)
    costs = {COST_NONE: 0.0, COST_MAIN: c_main, COST_P75: c_p75}
    dist_rows, pos_rows = _dist_rows_with_cost(built["cascade_rows"], costs)
    judge_rows = sp.build_judge_count_table(built["judge_counts"])
    action_rows = sp.build_action_count_table(built["action_counts"])
    print(f"[段1-8] 200 本の動作確認({time.time() - t0:.0f}s)", flush=True)

    # --- Q5b ---------------------------------------------------------------
    q5b_rows = run_q5b(all_cascades, chosen, prob_of, pos_of, bands,
                       base_rates, cache, c_main, cuts, minute_rows)
    print(f"[段1-9] Q5b({time.time() - t0:.0f}s)", flush=True)

    # --- 出力 ---------------------------------------------------------------
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    selected = build_grid_selected(grid_rows, chosen, chosen_zero, per_chain, cuts,
                                   c_main, split_day)
    sel_txt = json.dumps(selected, ensure_ascii=False, indent=2, default=str)
    check_no_banned(sel_txt, "grid_selected.json")
    (Path(out_dir) / "grid_selected.json").write_text(sel_txt, encoding="utf-8")

    q0_rows = [
        {"項目": "前半のプリント数", "値": len(prints_df)},
        {"項目": "前半の連鎖数", "値": len(all_cascades)},
        {"項目": "前半の日数", "値": len(days)},
        {"項目": "値段のラベルの割合(前半、プリント)",
         "値": float(pd.to_numeric(prints_df[LABEL_VALUE], errors="coerce").mean())},
        {"項目": "清算のラベルの割合(前半、プリント)",
         "値": float(pd.to_numeric(prints_df[LABEL_LIQ], errors="coerce").mean())},
        {"項目": "2 つのラベルの一致率(前半、プリント)",
         "値": float((pd.to_numeric(prints_df[LABEL_VALUE], errors="coerce")
                     == pd.to_numeric(prints_df[LABEL_LIQ], errors="coerce")).mean())},
        {"項目": "値段のラベルの再計算が既存列と一致した件数",
         "値": f"{n_match}/{len(recheck)}"},
        {"項目": "費用の標本日数", "値": len(spread.sample_day_paths())},
        {"項目": "主の c(bp)", "値": c_main},
        {"項目": "併記の c = p75(bp)", "値": c_p75},
        {"項目": "格子の組数", "値": len(grid_rows)},
        {"項目": "動作確認の連鎖の本数", "値": select_info["抜いた本数"]},
    ]
    for scene in (POS_1ST, POS_CHAIN):
        q0_rows.append({"項目": f"値段のラベルの割合({scene}、前半)",
                        "値": base_rates[scene]})
        q0_rows.append({"項目": f"「わからない」の帯({scene})", "値": str(bands[scene])})

    tables = [
        ("q0_selfcheck.csv", q0_rows, "Q0 自己点検"),
        ("calib_first.csv", calib_rows["first"], "Q1 較正(1件目、前半 5 分割 OOF、幅 0.02)"),
        ("calib_chain.csv", calib_rows["chain"], "Q1 較正(連鎖の中、前半 5 分割 OOF、幅 0.02)"),
        ("time_to_target.csv", ttt, "Q1 5 bp への到達時間(値段のラベルが 1 のプリント)"),
        ("grid.csv", grid_rows, "Q3 ② の格子 189 組(前半・遅れ 1 秒・費用込み)"),
        ("knob_contrib.csv", knob_rows, "Q3 選んだ組の 1 ノブずつの寄与"),
        ("dist_table.csv", dist_rows, "前半 200 本 連鎖ごとの損益分布(方策×型×遅れ×費用)"),
        ("position_breakdown.csv", pos_rows, "前半 200 本 位置別の内訳"),
        ("judge_counts.csv", judge_rows, "前半 200 本 判断の件数"),
        ("action_counts.csv", action_rows, "前半 200 本 行動の件数(遅れ 1 秒)"),
        ("synthetic_traces.csv", build_synthetic_traces_value(c_main),
         "合成の連鎖(状態機械・損切り・出口 3 種・費用の加算の道筋)"),
        ("q5b_secs_firsthalf.csv", q5b_rows, "Q5b 経路差の下見(前半)"),
    ]
    summary = {
        "段": "段1(前半だけ)",
        "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "委任文": DELEGATION, "設計": DESIGN, "種": SEED,
        "半期": FRONT_HALF,
        "前半のプリント数": len(prints_df), "前半の連鎖数": len(all_cascades),
        "前半の日数": len(days), "2 分割の境の日": split_day,
        "費用": {"主のc_bp": c_main, "p75_bp": c_p75,
               "引き方": "連鎖 1 本 = c × 建玉の回数(型 B のドテン 1 回 = c)"},
        "①の基準率": {k: base_rates[k] for k in base_rates},
        "①の帯": {k: (list(bands[k]) if bands[k] else None) for k in bands},
        "①の5分割OOF": {fits[k]["scene"]: _rename_report(fits[k]["res"]["report"])
                    for k in fits},
        "値段のラベルの再計算": {"件数": len(recheck), "一致": n_match},
        "②の格子": {"組数": len(grid_rows), "遅れ_秒": GRID_DELAY_S,
                 "ノブ": {"入る位置": list(ENTRY_POS_LEVELS),
                       "入る条件": list(COND_LEVELS), "出口": list(EXIT_LEVELS),
                       "損切り": list(STOP_LEVELS)},
                 "条件の分位": {k: [v[0], v[1]] for k, v in cuts.items()},
                 "選ぶ規則": "(a) 前半 2 分割の両側で総収支 > 0、(b) 連鎖 1 本の中央値 > 0"
                          " を満たす組の中で総収支が最大の 1 組",
                 "選んだ組(主 = 入った本のみの中央値)": chosen,
                 "参考(中央値を 0 含みで読んだ場合)": chosen_zero},
        "動作確認": {"連鎖の本数": select_info["抜いた本数"],
                 "内訳(単発/2件/3件以上)": select_info["抜いた本数の内訳(単発/2件/3件以上)"],
                 "方策": list(ALL_POLICIES), "遅れ_秒": list(DELAYS_S),
                 "費用の通り": list(costs.keys())},
        "入力のMD5(読むだけ、書き換えていない)": {
            _rel(p): md5_of(p)
            for p in (ROWS_CONTINUE, ROWS_MATERIALS, SPREAD_DIR / "spread_by_day.csv")
            if p.exists()},
        "作った設定": {_rel(CONFIG_VALUE_FIRST): md5_of(CONFIG_VALUE_FIRST),
                   _rel(CONFIG_VALUE_CHAIN): md5_of(CONFIG_VALUE_CHAIN)},
        "所要秒": round(time.time() - t0, 1),
    }
    summary = write_output(Path(out_dir), tables, summary)
    print(f"完了 {time.time() - t0:.0f}s -> {out_dir}", flush=True)
    print(json.dumps({"行数の合計": summary["行数の合計"],
                      "数値セル数": summary["数値セル数(tables.md)"]},
                     ensure_ascii=False), flush=True)
    return summary


# ===========================================================================
# 12. Q5b(経路差の下見、前半分)
# ===========================================================================
def run_q5b(all_cascades: dict, chosen: dict, prob_of: dict,
            pos_of: dict, bands: dict, base_rates: dict, cache: WindowCache,
            cost_bp: float, cuts: dict, minute_rows: list) -> list:
    """(a) 秒単位: 標本日に掛かる前半の連鎖で、入る・出る・損切りの約定を bitFlyer の
    約定の `at_or_after` に置き換えた損益と Binance の損益の対差。
    (b) 1 分の粗さ: 入る・出る時刻の次の 1 分の始値の損益を bitFlyer と Binance で。"""
    rows = []
    sample_days = {spread.day_of_path(p) for p in spread.sample_day_paths()}
    target = {bid: pr for bid, pr in all_cascades.items()
              if str(pr[0]["day"]) in sample_days}
    delay = GRID_DELAY_S

    # 200 本の動作確認と同じ材料を使えない連鎖があるので、①は確率が引けた連鎖だけ。
    bf_cache = {}

    def bf_arrays(day):
        if day not in bf_cache:
            bf_cache[day] = bitflyer_day_arrays(day)
        return bf_cache[day]

    acc = defaultdict(lambda: ([], []))   # 方策 -> (bitFlyer, Binance)
    n_no_prob = 0
    for bid in chain_ids_in_day_order(target):
        prints = target[bid]
        day = str(prints[0]["day"])
        s_sign = REACT_SIGN[str(prints[0]["side"])]
        end_ts = int(prints[-1]["ts_ms"]) + CASCADE_END_GAP_S * 1000
        bx_t, bx_p = cache.window_for(day)
        bf_t, bf_p = bf_arrays(day)
        if bf_t.size == 0:
            continue

        def bf_price(t_ms):
            return price_at_or_after(bf_t, bf_p, int(t_ms), STALENESS_MS)

        # 全部逆張り(素)
        r_bx = sp.simulate_baseline(prints, s_sign, POS_AGAINST, delay,
                                    cache.raw_at_or_after, end_ts)
        r_bf = sp.simulate_baseline(prints, s_sign, POS_AGAINST, delay, bf_price, end_ts)
        if not r_bx["missing"] and not r_bf["missing"]:
            a, b = acc["全部逆張り(素)"]
            a.append(r_bf["pnl_bp"] - cost_bp * r_bf["n_entries"])
            b.append(r_bx["pnl_bp"] - cost_bp * r_bx["n_entries"])

        # ① 3 択 A(確率が引けた連鎖だけ)
        if all(pr["print_id"] in prob_of for pr in prints):
            jud = judgments_for_policy_value(prints, "logistic_3択", prob_of, pos_of,
                                             bands, base_rates)
            j_bx = sp.simulate_cascade(prints, jud, s_sign, TYPE_A, delay,
                                       cache.raw_at_or_after, end_ts)
            j_bf = sp.simulate_cascade(prints, jud, s_sign, TYPE_A, delay, bf_price,
                                       end_ts)
            if not j_bx["missing"] and not j_bf["missing"]:
                a, b = acc["①3択A"]
                a.append(j_bf["pnl_bp"] - cost_bp * j_bf["n_entries"])
                b.append(j_bx["pnl_bp"] - cost_bp * j_bx["n_entries"])
        else:
            n_no_prob += 1

        # ②opt(選ばれた組があるときだけ)
        if chosen.get("選ばれた"):
            combo = chosen["組"]
            ei = ENTRY_POS_LEVELS.index(combo["入る位置"])
            cond = combo["入る条件"]
            take = True
            if cond != "なし" and ei < len(prints):
                col, thr = cuts[cond]
                v = cont._f(prints[ei].get(col))
                take = math.isfinite(v) and math.isfinite(thr) and v >= thr
            if take and ei < len(prints):
                o_bx = simulate_reverse_entry(prints, s_sign, ei, combo["出口"],
                                              STOP_BP[combo["損切り"]], delay,
                                              bx_t, bx_p)
                o_bf = simulate_reverse_entry(prints, s_sign, ei, combo["出口"],
                                              STOP_BP[combo["損切り"]], delay,
                                              bf_t, bf_p)
                if not o_bx["欠測"] and not o_bf["欠測"]:
                    a, b = acc["②opt"]
                    a.append(o_bf["pnl_bp"] - cost_bp * o_bf["建玉の回数"])
                    b.append(o_bx["pnl_bp"] - cost_bp * o_bx["建玉の回数"])

    for name in ("全部逆張り(素)", "①3択A", "②opt"):
        if name == "②opt" and not chosen.get("選ばれた"):
            rows.append({"経路": "秒単位(標本日に掛かる前半の連鎖)", "区分": "②opt",
                         "対の数": 0,
                         "備考": "規則を満たす組が無かったので ②opt の行は作らない"})
            continue
        a, b = acc[name]
        rows.append({"経路": "秒単位(標本日に掛かる前半の連鎖)",
                     **paired_diff_row(name, a, b, "bitFlyerの合計_bp",
                                       "Binanceの合計_bp")})
    rows.append({"経路": "秒単位(標本日に掛かる前半の連鎖)", "区分": "(母集団)",
                 "対の数": len(target),
                 "備考": f"標本日 {len(sample_days)} 日のうち前半に掛かる連鎖 "
                       f"{len(target)} 本。① の確率が引けなかった連鎖 {n_no_prob} 本"})

    # (b) 1 分の始値(前半の全連鎖、全部逆張り(素)。日ごとの一巡で計算済み)
    a_list = [r["bitFlyer_bp"] for r in minute_rows]
    b_list = [r["Binance_bp"] for r in minute_rows]
    rows.append({"経路": "1分の始値(前半の全連鎖)",
                 **paired_diff_row("全部逆張り(素)", a_list, b_list,
                                   "bitFlyerの合計_bp", "Binanceの合計_bp")})
    return rows


# ===========================================================================
# 13. 段2(**この委任では実装だけ。走らせない**)
# ===========================================================================
def run_stage2(out_dir: Path = DEFAULT_OUT_STAGE2, spread_dir: Path = SPREAD_DIR
               ) -> dict:
    """段2(後半 2,000 本、一度だけ = 11 度目の読み)。**この委任では走らせない。**
    前段と同じ `bundle_id`(`sp.select_stage2_cascades`)に、段1で前半から固定した
    帯・係数・費用・②opt をそのまま当てる(どれもここでは作り直さない)。"""
    t0 = time.time()
    c_main, c_p75 = spread.read_cost(spread_dir)
    s1 = json.loads((DEFAULT_OUT / "summary.json").read_text(encoding="utf-8"))
    bands = {k: (tuple(v) if v else None) for k, v in s1["①の帯"].items()}
    base_rates = s1["①の基準率"]
    chosen = s1["②の格子"]["選んだ組(主 = 入った本のみの中央値)"]
    cuts = {k: (v[0], v[1]) for k, v in s1["②の格子"]["条件の分位"].items()}

    select_info = sp.select_stage2_cascades(k=N_CASCADES_STAGE2)
    picked = select_info["cascades"]
    sb = js.StateBuilder()
    ids = {pr["print_id"] for prints in picked.values() for pr in prints}
    mat = pd.read_csv(ROWS_MATERIALS, low_memory=False)
    df = mat[mat["print_id"].isin(ids)].reset_index(drop=True)
    prob_of = compute_value_logit_probs(sb, df)
    pos_of = {pid: sp.position_of(c1) for pid, c1 in zip(df["print_id"], df["cand_1"])}

    cache = WindowCache(DATA_ROOT)
    built = run_policies(picked, prob_of, pos_of, bands, base_rates, cache)
    costs = {COST_NONE: 0.0, COST_MAIN: c_main, COST_P75: c_p75}
    dist_rows, pos_rows = _dist_rows_with_cost(built["cascade_rows"], costs)

    opt_rows = []
    if chosen and chosen.get("選ばれた"):
        combo = chosen["組"]
        ei = ENTRY_POS_LEVELS.index(combo["入る位置"])
        for bid in chain_ids_in_day_order(picked):
            prints = picked[bid]
            day = str(prints[0]["day"])
            times, prices = cache.window_for(day)
            if ei >= len(prints):
                continue
            if combo["入る条件"] != "なし":
                col, thr = cuts[combo["入る条件"]]
                v = cont._f(prints[ei].get(col))
                if not (math.isfinite(v) and v >= thr):
                    continue
            r = simulate_reverse_entry(prints, REACT_SIGN[str(prints[0]["side"])], ei,
                                       combo["出口"], STOP_BP[combo["損切り"]],
                                       GRID_DELAY_S, times, prices)
            if r["入った"] and not r["欠測"]:
                opt_rows.append({"bundle_id": bid, "day": day,
                                 "pnl_bp": r["pnl_bp"] - c_main * r["建玉の回数"],
                                 "出口の理由": r["出口の理由"]})

    tables = [
        ("dist_table.csv", dist_rows, "後半 2,000 本 連鎖ごとの損益分布"),
        ("position_breakdown.csv", pos_rows, "後半 2,000 本 位置別の内訳"),
        ("judge_counts.csv", sp.build_judge_count_table(built["judge_counts"]),
         "後半 2,000 本 判断の件数"),
        ("action_counts.csv", sp.build_action_count_table(built["action_counts"]),
         "後半 2,000 本 行動の件数"),
        ("opt_cascades.csv", opt_rows, "後半 2,000 本 ②opt の連鎖ごとの損益"),
    ]
    summary = {"段": "段2(後半 2,000 本、一度だけ)",
               "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
               "委任文": DELEGATION, "設計": DESIGN, "種": SEED,
               "抜いた連鎖の本数": select_info["抜いた本数"],
               "費用": {"主のc_bp": c_main, "p75_bp": c_p75},
               "段1から読んだもの(作り直していない)":
                   {"帯": s1["①の帯"], "基準率": s1["①の基準率"],
                    "②opt": chosen},
               "所要秒": round(time.time() - t0, 1)}
    return write_output(Path(out_dir), tables, summary)


# ===========================================================================
# main
# ===========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="O3C SIGNAL 値段の続き(段1: 前半だけ / 段2: 後半、一度だけ)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("stage1", help="前半だけ(この委任の範囲)")
    p1.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p1.add_argument("--half", default=FRONT_HALF)
    p2 = sub.add_parser("stage2", help="後半 2,000 本(この委任では走らせない)")
    p2.add_argument("--out", type=Path, default=DEFAULT_OUT_STAGE2)
    a = ap.parse_args(argv)
    if a.cmd == "stage1":
        run_stage1(a.out, a.half)
    else:
        run_stage2(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
