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
LAG_LIMIT_MS = 5_000   # D-5: 約定の遅れを絞った版の上限
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


def cascades_from_prints(df: pd.DataFrame, where: str = "") -> dict:
    """`bundle_id` でまとめる。**`bundle_id` が欠損している行は `groupby` が黙って
    落とす**ので、落とした行数をここで数えて出す(反証者レビュー9 致命-2)。"""
    n_drop = int(df["bundle_id"].isna().sum()) if "bundle_id" in df.columns else 0
    out = sp.cascades_from_prints(df)
    n_used = sum(len(v) for v in out.values())
    if n_drop:
        print(f"[束] {where or 'cascades_from_prints'}: 入力 {len(df)} 行のうち "
              f"bundle_id 欠損 {n_drop} 行を落とした(連鎖に入るのは {n_used} 行、"
              f"連鎖 {len(out)} 本)", flush=True)
    return out


def bundle_drop_count(df: pd.DataFrame) -> int:
    return int(df["bundle_id"].isna().sum()) if "bundle_id" in df.columns else 0


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
    """材料の列を持つファイルに値段のラベルを付け、前半を 1 件目 / 連鎖の中に分ける。

    **`bundle_id` のあるプリント(= 方策が実際に通るプリント)だけ**を当てはめ・較正・
    基準率の母集団にする(反証者レビュー9 致命-2、リードの決定 2026-09-21)。
    束の外のプリント(前半 1,041 件)は 3 つ目の戻り値として返し、Q0 に出す。"""
    mat = pd.read_csv(rows_materials, low_memory=False)
    lab = pd.read_csv(rows_continue,
                      usecols=["print_id", "kind", LABEL_VALUE, "notional"],
                      low_memory=False)
    lab = lab[lab["kind"] == "print"][["print_id", LABEL_VALUE, "notional"]]
    df = mat.merge(lab, on="print_id", how="left")
    fh = df[df["half"] == FRONT_HALF].reset_index(drop=True)
    assert_front_half_only(fh, "rows_materials(段1)")
    in_bundle = fh["bundle_id"].notna()
    outside = fh[~in_bundle].reset_index(drop=True)
    fh = fh[in_bundle].reset_index(drop=True)
    cand1 = pd.to_numeric(fh["cand_1"], errors="coerce")
    return (fh[cand1 == 0].reset_index(drop=True),
            fh[cand1 > 0].reset_index(drop=True),
            outside)


def outside_bundle_rows(outside: pd.DataFrame) -> list:
    """Q0: 方策が通らないプリント(束の外)の件数・値段のラベルの割合・想定元本の中央値。"""
    if outside is None or outside.empty:
        return [{"区分": "束の外(方策が通らないプリント)", "件数": 0}]
    y = pd.to_numeric(outside[LABEL_VALUE], errors="coerce")
    n = pd.to_numeric(outside["notional"], errors="coerce")
    c1 = pd.to_numeric(outside["cand_1"], errors="coerce")
    return [{"区分": "束の外(方策が通らないプリント)", "件数": int(len(outside)),
             "値段のラベルの割合": float(y.mean()),
             "想定元本の中央値": float(np.nanmedian(n.to_numpy(float))),
             "1件目(cand_1==0)": int((c1 == 0).sum()),
             "連鎖の中(cand_1>0)": int((c1 > 0).sum()),
             "掛かる日数": int(outside["day"].nunique())}]


def add_n2_by_day(sb, df_first: pd.DataFrame) -> pd.DataFrame:
    """N2(1 件目だけ)を日ごとに計算する(`lg.add_n2_column` をそのまま使い、
    日が変わるたびに約定のキャッシュを空にして記憶を抑える)。"""
    parts = []
    for day, g in df_first.groupby("day", sort=True):
        parts.append(lg.add_n2_column(sb, g.reset_index(drop=True)))
        sb._window_cache.clear()
        sb._raw_trade_cache.clear()
    return pd.concat(parts, ignore_index=True)


def day_block_folds(days_of_rows, n_folds: int = lg.N_FOLDS,
                    seed: int = lg.CV_SEED) -> list:
    """**日でブロックした** k 分割(反証者レビュー9 S-1)。日を種で混ぜて k 群に割り、
    同じ日の行は必ず同じ群に入る(同じ連鎖のプリントが訓練側と試験側に跨らない)。"""
    days_of_rows = np.asarray(days_of_rows, dtype=object)
    uniq = sorted(set(days_of_rows.tolist()))
    rng = np.random.default_rng(seed)
    order = np.array(uniq, dtype=object)[rng.permutation(len(uniq))]
    groups = np.array_split(order, n_folds)
    group_of_day = {}
    for gi, g in enumerate(groups):
        for d in g.tolist():
            group_of_day[d] = gi
    idx = np.arange(days_of_rows.size)
    return [idx[np.array([group_of_day[d] == gi for d in days_of_rows.tolist()])]
            for gi in range(n_folds)]


def run_scene_day_blocked(df_s: pd.DataFrame, features: list, scene: str,
                          label_col: str = LABEL_VALUE) -> dict:
    """`lg.run_scene` と同じ量を、**日でブロックした 5 分割**で出す(S-1)。
    経験分布(`lg.build_ecdf`)・順位(`lg.apply_frozen_rank`)・当てはめ
    (`lg.newton_logistic`)・順位分離(`lg.separation_auc`)は前段の関数をそのまま呼ぶ。"""
    ecdf = lg.build_ecdf(df_s, features)
    X = lg.apply_frozen_rank(ecdf, features, df_s)
    y_all = pd.to_numeric(df_s[label_col], errors="coerce").to_numpy(float)
    ok = np.isfinite(y_all)
    pid = df_s["print_id"].to_numpy(object)[ok]
    days = df_s["day"].astype(str).to_numpy(object)[ok]
    X, y = X[ok], y_all[ok].astype(int)
    n = X.shape[0]
    beta_full = lg.newton_logistic(X, y.astype(float))
    folds = day_block_folds(days)
    oof = np.full(n, NAN)
    for i, test_idx in enumerate(folds):
        train_idx = np.concatenate([folds[j] for j in range(len(folds)) if j != i])
        beta_f = lg.newton_logistic(X[train_idx], y[train_idx].astype(float))
        oof[test_idx] = lg.predict(X[test_idx], beta_f)
    report = {
        "場面": scene, "件数": n,
        f"基準率({label_col}、前半)": float(y.mean()),
        "5fold_out_of_fold_順位分離": lg.separation_auc(oof[y == 1], oof[y == 0]),
        "的中(閾値0.5)": float(((oof >= 0.5).astype(int) == y).mean()),
        "分割": "日でブロックした 5 分割(S-1)",
        "分割の日数": [int(len(set(days[f].tolist()))) for f in folds],
        "閾値ごとの適合率": [
            {"閾値": thr, "適合率": lg.precision_at(oof, y, thr)[0],
             "件数": lg.precision_at(oof, y, thr)[1]} for thr in (0.6, 0.7, 0.8)],
    }
    return {"beta": beta_full, "ecdf": ecdf, "n": n, "report": report,
            "oof_by_pid": {str(a): float(b) for a, b in zip(pid, oof)}}


def fit_value_logit(df_first: pd.DataFrame, df_chain: pd.DataFrame) -> dict:
    """前半だけで値段のラベルの logistic を当てはめ、5 分割 OOF も返す。"""
    out = {}
    for key, df_s, features, scene, cfg, ecdf_path in (
            ("first", df_first, lg.FEATURES_FIRST, "1件目",
             CONFIG_VALUE_FIRST, ECDF_VALUE_FIRST),
            ("chain", df_chain, lg.FEATURES_CHAIN, "連鎖の中",
             CONFIG_VALUE_CHAIN, ECDF_VALUE_CHAIN)):
        assert_front_half_only(df_s, f"当てはめ({scene})")
        res = run_scene_day_blocked(df_s, features, scene, label_col=LABEL_VALUE)
        # 委任文が名指しする経路そのもの。`run_scene` の全件当てはめと一致することを
        # 毎回確かめる(同じ前半・同じ材料・同じラベルなので一致するはず)。
        beta_named = lg.fit_beta_front_half(df_s, features, label_col=LABEL_VALUE)
        max_gap = float(np.max(np.abs(beta_named - res["beta"])))
        if max_gap > 1e-8:
            raise RuntimeError(f"[止め] {scene}: fit_beta_front_half と "
                               f"run_scene_day_blocked の係数が食い違う(最大差 {max_gap})")
        lg.save_ecdf_npz(ecdf_path, res["ecdf"])
        doc = {
            "_由来": (f"scripts/o3c_signal_value.py stage1。前半全件({res['n']} 件、"
                    f"{scene})で `fit_beta_front_half(label_col=\"{LABEL_VALUE}\")` = "
                    "ニュートン法(L2 1e-3、sklearn 不使用)。入力は前半の経験分布の"
                    "中央順位(`apply_frozen_rank`、欠測 0.5)。**前段の清算のラベルの"
                    "係数(config/o3c_signal_logit_{first,chain}.yaml)は触っていない。**"
                    "母集団は bundle_id のあるプリントだけ(反証者9 致命-2)、"
                    "5 分割は日でブロック(S-1)。"),
            "母集団": "bundle_id のあるプリントだけ(束の外は入れない)",
            "分割": "日でブロックした 5 分割",
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


def residual_move_after_delay(times: np.ndarray, prices: np.ndarray, t0_ms: int,
                              sign: float, delay_s: float = MAIN_DELAY,
                              horizon_s: int = LABEL_MAIN_S) -> float:
    """**遅れ d の約定価格から** t₀+horizon までの最大順行(bp)。
    反証者レビュー9 D-3: 「到達が d より早い = 取れない」ではないことを測るための量。"""
    delay_ms = int(round(float(delay_s) * 1000))
    p_in, m_in = price_at_or_after(times, prices, int(t0_ms) + delay_ms, STALENESS_MS)
    if p_in != p_in or p_in <= 0:
        return NAN
    hi_ms = int(t0_ms) + int(horizon_s) * 1000
    i0 = int(np.searchsorted(times, int(m_in), side="right"))
    i1 = int(np.searchsorted(times, hi_ms, side="right"))
    if i1 <= i0:
        return NAN
    seg = prices[i0:i1]
    return float(np.max(sign * (seg - p_in) / p_in * 1e4))


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
                         "遅れ1秒の約定からの最大順行_bp": residual_move_after_delay(
                             times, prices, int(r.t0_ms), float(r.dir_sign)),
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
        # D-3: 到達が遅れより早くても「取れない」わけではない。遅れ 1 秒の約定価格から
        # なお 5 bp 以上動く割合を、到達 < 1 秒 / >= 1 秒 の別に出す。
        def resid(sub):
            rv = np.array([r["遅れ1秒の約定からの最大順行_bp"] for r in sub], dtype=float)
            rv = rv[np.isfinite(rv)]
            return (len(sub), int(rv.size),
                    (float(np.mean(rv >= VALUE_CONT_BP)) if rv.size else NAN),
                    (float(np.median(rv)) if rv.size else NAN))
        fast = [r for r in sel if np.isfinite(r["到達秒"]) and r["到達秒"] < 1.0]
        slow = [r for r in sel if np.isfinite(r["到達秒"]) and r["到達秒"] >= 1.0]
        nf, nf_ok, f_share, f_med = resid(fast)
        ns, ns_ok, s_share, s_med = resid(slow)
        rows.append({
            "場面": scene, "値段のラベルが1の件数": len(sel), "秒が取れた件数": int(v.size),
            "p10_秒": q[0], "p25_秒": q[1], "p50_秒": q[2], "p75_秒": q[3],
            "p90_秒": q[4],
            "1秒未満の割合": (float(np.mean(v < 1.0)) if v.size else NAN),
            "2秒未満の割合": (float(np.mean(v < 2.0)) if v.size else NAN),
            "到達1秒未満の件数": nf,
            "到達1秒未満_遅れ1秒の約定からなお5bp以上の割合": f_share,
            "到達1秒未満_遅れ1秒の約定からの最大順行の中央値_bp": f_med,
            "到達1秒以上の件数": ns,
            "到達1秒以上_遅れ1秒の約定からなお5bp以上の割合": s_share,
            "到達1秒以上_遅れ1秒の約定からの最大順行の中央値_bp": s_med})
    return rows


# ===========================================================================
# 6. ② の格子(設計 §5)
# ===========================================================================
def grid_combos() -> list:
    """189 組(位置 3 × 条件 7 × 出口 3 × 損切り 3)を事前に固定した順で列挙する。"""
    return [{"入る位置": a, "入る条件": b, "出口": c, "損切り": d}
            for a, b, c, d in itertools.product(
                ENTRY_POS_LEVELS, COND_LEVELS, EXIT_LEVELS, STOP_LEVELS)]


def condition_cuts(df_front: pd.DataFrame) -> tuple:
    """入る条件の分位。**母集団は `bundle_id` のあるプリント**(反証者9 D-4。
    帯・基準率と揃える)。材料ごとに有限値の件数が違う(材料 12 は 1 件目で全欠測)ので、
    切り値と一緒に「何件で切ったか」も返す。"""
    if "bundle_id" in df_front.columns:
        df_front = df_front[df_front["bundle_id"].notna()]
    cuts, note = {}, {}
    for name, col in COND_MATERIALS.items():
        v = pd.to_numeric(df_front[col], errors="coerce").to_numpy(float)
        v = v[np.isfinite(v)]
        q = quantiles(v, [75, 90]) if v.size else [NAN, NAN]
        cuts[f"{name}≥p75"] = (col, q[0])
        cuts[f"{name}≥p90"] = (col, q[1])
        note[name] = {"列": col, "有限値の件数": int(v.size), "母数": int(len(df_front)),
                      "p75": q[0], "p90": q[1]}
    return cuts, note


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


def max_concurrent(intervals: list) -> int:
    """区間 [入りの約定時刻, 出の約定時刻) の**同時建玉の最大**(本)。"""
    if not intervals:
        return 0
    events = []
    for a, b in intervals:
        if a is None or b is None:
            continue
        events.append((int(a), 1))
        events.append((int(b), -1))
    if not events:
        return 0
    events.sort(key=lambda e: (e[0], e[1]))   # 同時刻は「閉じる」を先に(半開区間)
    cur = best = 0
    for _t, d in events:
        cur += d
        best = max(best, cur)
    return int(best)


def exposure_of(rows: list) -> dict:
    """露出(致命-3): 合計保有時間(時間)・保有 1 時間あたりの収支(bp/h)・
    同時建玉の最大(本)・1 本あたりの平均保有秒。`rows` は
    {"pnl_net_bp", "保有秒", "入りの約定時刻", "出の約定時刻"} を持つ行の並び。"""
    hold_s = float(sum(r["保有秒"] for r in rows if r["保有秒"] == r["保有秒"]))
    total = float(sum(r["pnl_net_bp"] for r in rows if r["pnl_net_bp"] == r["pnl_net_bp"]))
    hours = hold_s / 3600.0
    iv = [(r["入りの約定時刻"], r["出の約定時刻"]) for r in rows]
    return {"合計保有時間_時間": hours,
            "保有1時間あたりの収支_bp/h": (total / hours if hours > 0 else NAN),
            "同時建玉の最大_本": max_concurrent(iv),
            "平均保有秒": (hold_s / len(rows) if rows else NAN)}


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


def combo_chain_rows(per_chain: dict, cuts: dict, cost_bp: float, combo: dict,
                     split_day: str | None = None) -> list:
    """1 つの組の**連鎖 1 本ごとの行**(致命-1・致命-3。保有秒と約定時刻を残す)。"""
    ei = ENTRY_POS_LEVELS.index(combo["入る位置"])
    cond = combo["入る条件"]
    out = []
    for bid, rec in per_chain.items():
        r = rec["結果"][(ei, combo["出口"], combo["損切り"])]
        if not r["入った"]:
            continue
        if cond != "なし":
            col, thr = cuts[cond]
            v = cont._f(rec["entry_rows"][ei].get(col))
            if not (math.isfinite(v) and math.isfinite(thr) and v >= thr):
                continue
        pr = rec["entry_rows"]
        out.append({
            "bundle_id": bid, "day": rec["day"], "side": str(pr[0]["side"]),
            "連鎖の大きさ": sp.size_bucket(len(pr)), "n_prints": len(pr),
            "pnl_bp": r["pnl_bp"],
            "pnl_net_bp": (r["pnl_bp"] - cost_bp * r["建玉の回数"]
                           if r["pnl_bp"] == r["pnl_bp"] else NAN),
            "建玉の回数": r["建玉の回数"], "保有秒": r["保有秒"],
            "入りの約定時刻": r["入りの約定時刻"], "出の約定時刻": r["出の約定時刻"],
            "入った": 1, "欠測": r["欠測"], "出口の理由": r["出口の理由"],
            "前半の前": (None if split_day is None else int(rec["day"] <= split_day))})
    return out


def _empty_reason(per_chain: dict, cuts: dict, combo: dict) -> str:
    """1 本も入らなかった組の理由(D-4)。構造的に空なら、どの材料がどこで全欠測かを書く。"""
    cond = combo["入る条件"]
    ei = ENTRY_POS_LEVELS.index(combo["入る位置"])
    n_reach = sum(1 for rec in per_chain.values() if rec["n_prints"] > ei)
    if n_reach == 0:
        return f"構造的に空(連鎖の {ei + 1} 件目に届く連鎖が 0 本)"
    if cond == "なし":
        return ""
    col, thr = cuts[cond]
    n_fin = sum(1 for rec in per_chain.values() if rec["n_prints"] > ei
                and math.isfinite(cont._f(rec["entry_rows"][ei].get(col))))
    if n_fin == 0:
        return (f"構造的に空({cond} の材料 `{col}` が「{combo['入る位置']}」の"
                f"入りのプリントで全欠測。届く連鎖 {n_reach} 本すべて)")
    if not math.isfinite(thr):
        return f"構造的に空({cond} の切り値が引けない)"
    return f"条件を満たす連鎖が 0 本(届く連鎖 {n_reach} 本、材料が有限 {n_fin} 本)"


def build_grid_table(per_chain: dict, cuts: dict, cost_bp: float,
                     split_day: str) -> list:
    """189 組の表。費用は 連鎖 1 本 = c × 建玉の回数(② はいつも 1 回)。
    致命-3 を受けて**露出の 3 列**(合計保有時間・保有 1 時間あたりの収支・
    同時建玉の最大)を足した。D-4 を受けて空の組に理由を書く。"""
    rows = []
    for combo in grid_combos():
        ei = ENTRY_POS_LEVELS.index(combo["入る位置"])
        cond = combo["入る条件"]
        chain_rows = combo_chain_rows(per_chain, cuts, cost_bp, combo, split_day)
        n_missing = sum(1 for r in chain_rows if r["欠測"])
        ok_rows = [r for r in chain_rows if not r["欠測"]]
        n_cond_out = 0
        if cond != "なし":
            col, thr = cuts[cond]
            for rec in per_chain.values():
                r = rec["結果"][(ei, combo["出口"], combo["損切り"])]
                if not r["入った"]:
                    continue
                v = cont._f(rec["entry_rows"][ei].get(col))
                if not (math.isfinite(v) and math.isfinite(thr) and v >= thr):
                    n_cond_out += 1
        v = np.array([r["pnl_net_bp"] for r in ok_rows], dtype=float)
        d = np.array([r["day"] for r in ok_rows], dtype=object)
        fm = np.array([bool(r["前半の前"]) for r in ok_rows], dtype=bool)
        row = {**combo}
        row.update(_combo_metrics(v, d, len(per_chain), fm))
        row.update(exposure_of(ok_rows))
        row["欠測"] = n_missing
        row["条件で外れた本数"] = n_cond_out
        row["空の理由"] = ("" if ok_rows else _empty_reason(per_chain, cuts, combo))
        rows.append(row)
    return rows


def build_exposure_table(per_chain: dict, cuts: dict, cost_bp: float,
                         combos: dict) -> list:
    """Q3 の露出の表(致命-3): 名前付きの組について、本数・合計保有時間・
    保有 1 時間あたりの収支・同時建玉の最大・平均保有秒を並べる。"""
    rows = []
    for name, combo in combos.items():
        ch = [r for r in combo_chain_rows(per_chain, cuts, cost_bp, combo)
              if not r["欠測"]]
        tot = float(sum(r["pnl_net_bp"] for r in ch
                        if r["pnl_net_bp"] == r["pnl_net_bp"]))
        rows.append({"通り": name, **combo, "入った本数": len(ch),
                     "総収支_bp": tot, **exposure_of(ch)})
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
                         "中央値_入った本のみ": r["中央値_入った本のみ"],
                         "合計保有時間_時間": r.get("合計保有時間_時間"),
                         "保有1時間あたりの収支_bp/h": r.get("保有1時間あたりの収支_bp/h"),
                         "同時建玉の最大_本": r.get("同時建玉の最大_本")})
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


def require_materials_cover(ids, found, where: str) -> None:
    """materials に無い `print_id` があれば例外で止める(段1・段2 の両方で使う。
    反証者レビュー9 D-6(a): 段2 にこの検査が無いと、確率が引けないプリントが
    静かに「わからない」= 入らない に落ちる)。"""
    missing = set(ids) - set(found)
    if missing:
        raise RuntimeError(f"[止め] {where}: materials に無い print_id: "
                           f"{sorted(missing)[:5]}(計 {len(missing)} 件)")


def load_value_probs_for_cascades(cascades: dict, sb=None,
                                  materials_path: Path = ROWS_MATERIALS,
                                  n2_by_pid: dict | None = None) -> tuple:
    ids = {pr["print_id"] for prints in cascades.values() for pr in prints}
    mat = pd.read_csv(materials_path, low_memory=False)
    df = mat[mat["print_id"].isin(ids)].reset_index(drop=True)
    assert_front_half_only(df, "materials(200 本の動作確認)")
    require_materials_cover(ids, set(df["print_id"]), "段1 の 200 本 + 標本日の連鎖")
    sb = js.StateBuilder() if sb is None else sb
    prob_of = compute_value_logit_probs(sb, df, n2_by_pid)
    pos_of = {pid: sp.position_of(c1) for pid, c1 in zip(df["print_id"], df["cand_1"])}
    return prob_of, pos_of


JUDGE_VALUE, JUDGE_LIQ = "値段", "清算"
REF_POLICIES = ("前段の3択(清算)", "完全な判断(清算)")


def judgments_for_policy_value(prints: list, policy: str, prob_of: dict,
                               pos_of: dict, bands: dict, base_rates: dict,
                               kind: str = JUDGE_VALUE) -> list:
    """判断の列。`kind == "値段"` なら判断の対象は値段の続き(① 本体)。
    `kind == "清算"` は Q2・Q4 の参照 2 本で、**前段の帯**(`sp.BAND_*`)と
    **前段の完全な判断**(`sp.judge_perfect`、連鎖の道筋の位置)をそのまま使う。"""
    if kind == JUDGE_LIQ:
        if policy in ("完全な判断(清算)", "完全な判断"):
            n = len(prints)
            return [sp.judge_perfect(i, n) for i in range(n)]
        if policy in ("前段の3択(清算)", "logistic_3択"):
            return [sp.judge_3way_from_prob(prob_of.get(p["print_id"]),
                                            pos_of.get(p["print_id"], POS_1ST))
                    for p in prints]
        raise ValueError(f"未知の参照方策: {policy}")
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


def _baseline_fill_times(res: dict, delay_s: float, entry_ts: int, exit_ts: int
                         ) -> tuple:
    delay_ms = int(round(float(delay_s) * 1000))
    lags = list(res.get("fill_lag_ms") or [])
    if len(lags) != 2:
        return None, None
    return (int(entry_ts) + delay_ms + int(lags[0]),
            int(exit_ts) + delay_ms + int(lags[1]))


def entry_exit_fill_times(res: dict, delay_s: float) -> tuple:
    """`sp.simulate_cascade` / `sp.simulate_baseline` の戻り値から、**最初の約定**と
    **最後の約定**の時刻(ms)を復元する(`path` の値段が付いた行と `fill_lag_ms` は
    同じ順で 1 対 1 に対応する)。

    注: 型 A は決済したあと後のプリントで入り直せるので、この 2 つの間には建玉が
    無い時間が混じることがある。**合計保有時間は `保有秒` を使う**(こちらは
    状態機械が持っている建玉の時間の合計)。この区間は同時建玉を数えるための近似。"""
    delay_ms = int(round(float(delay_s) * 1000))
    filled = [r for r in res.get("path", []) if r.get("約定価格") is not None]
    lags = list(res.get("fill_lag_ms") or [])
    if not filled or len(lags) != len(filled):
        return None, None
    return (int(filled[0]["ts_ms"]) + delay_ms + int(lags[0]),
            int(filled[-1]["ts_ms"]) + delay_ms + int(lags[-1]))


def run_policies(cascades: dict, prob_of: dict, pos_of: dict, bands: dict,
                 base_rates: dict, cache: WindowCache,
                 policies: tuple = JUDGED_POLICIES,
                 types: tuple = (TYPE_A, TYPE_B),
                 baselines: dict | None = None,
                 kind: str = JUDGE_VALUE,
                 count_policies: tuple | None = None) -> dict:
    """前段 `run_simulation` と同じ組み立て(状態機械は `sp.simulate_cascade` /
    `sp.simulate_baseline` をそのまま呼ぶ)。判断だけが値段のラベル(または参照の
    清算のラベル)のもの。"""
    if baselines is None:
        baselines = POLICY_IS_BASELINE
    if count_policies is None:
        count_policies = COUNT_JUDGE_POLICIES
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
                                                       bands, base_rates, kind)
                       for pol in policies}
        for pol in count_policies:
            if pol not in judge_cache:
                continue
            for j, pr in enumerate(prints):
                judge_counts[(pol, pos_of.get(pr["print_id"], POS_1ST),
                              judge_cache[pol][j])] += 1
        for delay in DELAYS_S:
            price_fn = cache.raw_at_or_after
            for pol in policies:
                for ptype in types:
                    res = sp.simulate_cascade(prints, judge_cache[pol], s_sign, ptype,
                                              delay, price_fn, end_ts)
                    t_in, t_out = entry_exit_fill_times(res, delay)
                    cascade_rows.append({
                        "bundle_id": bid, "day": day, "side": side,
                        "連鎖の大きさ": sb_size, "n_prints": n, "方策": pol, "型": ptype,
                        "遅れ_秒": delay, "pnl_bp": res["pnl_bp"],
                        "建玉の回数": res["n_entries"], "保有秒": res["hold_seconds"],
                        "入りの約定時刻_ms": t_in, "出の約定時刻_ms": t_out,
                        "出口の理由": "連鎖の終わり+d",
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
            for pol_name, direction in baselines.items():
                for ptype in types:
                    res = sp.simulate_baseline(prints, s_sign, direction, delay,
                                               price_fn, end_ts)
                    t_in, t_out = _baseline_fill_times(
                        res, delay, int(prints[0]["ts_ms"]), end_ts)
                    cascade_rows.append({
                        "bundle_id": bid, "day": day, "side": side,
                        "連鎖の大きさ": sb_size, "n_prints": n, "方策": pol_name,
                        "型": ptype, "遅れ_秒": delay, "pnl_bp": res["pnl_bp"],
                        "建玉の回数": res["n_entries"], "保有秒": res["hold_seconds"],
                        "入りの約定時刻_ms": t_in, "出の約定時刻_ms": t_out,
                        "出口の理由": "連鎖の終わり+d",
                        "入った": int(res["entered"]), "欠測": int(res["missing"]),
                        "最初に入った位置": sp.entry_bucket(res["first_entry_pos"])})
                    if delay == MAIN_DELAY:
                        action_counts[(pol_name, ptype, res["path"][0]["行動"])] += 1
    return {"cascade_rows": cascade_rows, "print_rows": print_rows,
            "judge_counts": judge_counts, "action_counts": action_counts}


CASCADE_COLUMNS = ("bundle_id", "day", "side", "連鎖の大きさ", "n_prints", "方策",
                   "型", "遅れ_秒", "費用の通り", "pnl_bp", "pnl_net_bp", "建玉の回数",
                   "保有秒", "入りの約定時刻_ms", "出の約定時刻_ms", "入った",
                   "最初に入った位置", "出口の理由")


def build_cascade_rows_file(policy_rows: list, costs: dict,
                            opt_rows_by_name: dict | None = None) -> list:
    """**連鎖 1 本ごとの行**(反証者レビュー9 致命-1)。① の方策の行と ② の行を
    同じ列で 1 つの表にし、費用の通りを行の次元にする。"""
    out = []
    for label, c in costs.items():
        for r in policy_rows:
            gross = r["pnl_bp"]
            out.append({
                "bundle_id": r["bundle_id"], "day": r["day"], "side": r["side"],
                "連鎖の大きさ": r["連鎖の大きさ"], "n_prints": r["n_prints"],
                "方策": r["方策"], "型": r["型"], "遅れ_秒": r["遅れ_秒"],
                "費用の通り": label, "pnl_bp": gross,
                "pnl_net_bp": (gross - c * r["建玉の回数"]
                               if gross == gross else NAN),
                "建玉の回数": r["建玉の回数"], "保有秒": r["保有秒"],
                "入りの約定時刻_ms": r.get("入りの約定時刻_ms"),
                "出の約定時刻_ms": r.get("出の約定時刻_ms"),
                "入った": r["入った"],
                "最初に入った位置": r["最初に入った位置"],
                "出口の理由": r.get("出口の理由", "")})
        for name, rows in (opt_rows_by_name or {}).items():
            for r in rows:
                gross = r["pnl_bp"]
                out.append({
                    "bundle_id": r["bundle_id"], "day": r["day"], "side": r["side"],
                    "連鎖の大きさ": r["連鎖の大きさ"], "n_prints": r["n_prints"],
                    "方策": name, "型": "-", "遅れ_秒": GRID_DELAY_S,
                    "費用の通り": label, "pnl_bp": gross,
                    "pnl_net_bp": (gross - c * r["建玉の回数"]
                                   if gross == gross else NAN),
                    "建玉の回数": r["建玉の回数"], "保有秒": r["保有秒"],
                    "入りの約定時刻_ms": r["入りの約定時刻"],
                    "出の約定時刻_ms": r["出の約定時刻"],
                    "入った": r["入った"], "最初に入った位置": "-",
                    "出口の理由": r["出口の理由"]})
    return [{c: r.get(c, "") for c in CASCADE_COLUMNS} for r in out]


def write_cascades_gz(out_dir: Path, rows: list) -> int:
    sp.write_csv_gz(Path(out_dir) / "cascades.csv.gz", rows)
    return len(rows)


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
    # D-7 の注記: `np.sign(0) != np.sign(x)` も 1 と数えるので、0(入らなかった)を
    # 含む行では「符号が変わった」の意味が変わる。0 の本数は「どちらも0の本数」に出す。
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
def _dist_rows_with_cost(cascade_rows: list, costs: dict,
                         extra_policies: tuple = ()) -> tuple:
    """`sp.build_dist_table` / `sp.build_position_breakdown` は前段の 7 方策しか回らないので、
    参照 2 本(前段の 3 択(清算)A・完全な判断(清算)A)は `sp.dist_stats` を直接呼んで足す
    (反証者レビュー9 致命-1 の Q2 の参照)。"""
    dist, posb = [], []
    for label, c in costs.items():
        cdf = apply_cost(cascade_rows, c)
        for r in sp.build_dist_table(cdf):
            dist.append({"費用": label, "c_bp": c, **r})
        for pol in extra_policies:
            for delay in DELAYS_S:
                for inc0 in (True, False):
                    dist.append({"費用": label, "c_bp": c,
                                 **sp.dist_stats(cdf, pol, TYPE_A, delay, inc0)})
        for r in sp.build_position_breakdown(cdf):
            posb.append({"費用": label, "c_bp": c, **r})
        sub_all = cdf[(cdf["遅れ_秒"] == MAIN_DELAY) & (cdf["欠測"] == 0)]
        for pol in extra_policies:
            sub = sub_all[(sub_all["方策"] == pol) & (sub_all["型"] == TYPE_A)]
            for bucket in ("1件目で入った", "途中で入った", "入らなかった"):
                g = sub[sub["最初に入った位置"] == bucket]
                vals = g["pnl_bp"].to_numpy(float)
                q = quantiles(vals, [50])
                posb.append({"費用": label, "c_bp": c, "方策": pol, "型": TYPE_A,
                             "位置": bucket, "n": int(g.shape[0]), "中央値": q[0],
                             "負の割合": (float(np.mean(vals < 0)) if vals.size
                                      else NAN)})
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
    n_no_bundle = bundle_drop_count(prints_df)
    all_cascades = cascades_from_prints(prints_df, "段1 前半")
    n_in_bundle = sum(len(v) for v in all_cascades.values())
    days = sorted(set(prints_df["day"].astype(str)))
    split_day = days[len(days) // 2 - 1]
    print(f"[段1-1] 前半 プリント {len(prints_df)} 件 / 連鎖 {len(all_cascades)} 本 / "
          f"日 {len(days)}(2 分割の境 {split_day})", flush=True)

    # --- 日ごとの一巡(N2・ラベル再計算・②の 27 通り・1 分の始値) ----------
    sb = js.StateBuilder()
    df_first, df_chain, df_outside = build_scene_frames()
    print(f"[段1-2] 1件目 {len(df_first)} 件 / 連鎖の中 {len(df_chain)} 件 / "
          f"束の外 {len(df_outside)} 件(当てはめには入れない)"
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
    cuts, cuts_note = condition_cuts(prints_df)
    grid_rows = build_grid_table(per_chain, cuts, c_main, split_day)
    chosen = select_combo(grid_rows)
    chosen_zero = select_combo(grid_rows, median_col="中央値_0含む")
    knob_rows = knob_contribution(grid_rows, chosen)
    n_empty = sum(1 for r in grid_rows if r["入った本数"] == 0)
    exposure_combos = {
        "素(1件目から・連鎖の終わり・損切りなし)": dict(PLAIN_COMBO),
        "3件目以降だけ・連鎖の終わり・損切りなし": {
            **PLAIN_COMBO, "入る位置": ENTRY_POS_LEVELS[2]},
    }
    if chosen.get("選ばれた"):
        exposure_combos["②opt(選んだ組)"] = dict(chosen["組"])
    exposure_rows = build_exposure_table(per_chain, cuts, c_main, exposure_combos)
    print(f"[段1-7] 格子 {len(grid_rows)} 組(1 本も入らない組 {n_empty})/ "
          f"選ばれた: {chosen['選ばれた']} ({time.time() - t0:.0f}s)", flush=True)

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
    # 致命-1: 連鎖 1 本ごとの行(① の 200 本 + ② の露出の 3 通り、全連鎖)
    opt_named = {name: combo_chain_rows(per_chain, cuts, 0.0, combo)
                 for name, combo in exposure_combos.items()}
    cascade_file_rows = build_cascade_rows_file(built["cascade_rows"], costs, opt_named)
    print(f"[段1-8] 200 本の動作確認 / 連鎖 1 本ごとの行 {len(cascade_file_rows)} 行"
          f"({time.time() - t0:.0f}s)", flush=True)

    # --- Q5b ---------------------------------------------------------------
    q5b_rows = run_q5b(all_cascades, chosen, prob_of, pos_of, bands,
                       base_rates, cache, c_main, cuts, minute_rows)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    n_cascade_rows = write_cascades_gz(Path(out_dir), cascade_file_rows)
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
        {"項目": "うち連鎖(bundle_id)に入るプリント", "値": n_in_bundle},
        {"項目": "うち束の外(方策が通らない)プリント", "値": n_no_bundle},
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
        q0_rows.append({"項目": f"値段のラベルの割合({scene}、前半・束の中だけ)",
                        "値": base_rates[scene]})
        q0_rows.append({"項目": f"「わからない」の帯({scene})", "値": str(bands[scene])})
    for r in outside_bundle_rows(df_outside):
        for k, v in r.items():
            if k == "区分":
                continue
            q0_rows.append({"項目": f"束の外: {k}", "値": v})
    q0_rows.append({"項目": "格子で 1 本も入らなかった組", "値": f"{n_empty}/189"})
    for name, note in cuts_note.items():
        q0_rows.append({"項目": f"入る条件の分位を切った件数({name})",
                        "値": f"{note['有限値の件数']}/{note['母数']}"})

    tables = [
        ("q0_selfcheck.csv", q0_rows, "Q0 自己点検"),
        ("calib_first.csv", calib_rows["first"], "Q1 較正(1件目、前半 5 分割 OOF、幅 0.02)"),
        ("calib_chain.csv", calib_rows["chain"], "Q1 較正(連鎖の中、前半 5 分割 OOF、幅 0.02)"),
        ("time_to_target.csv", ttt, "Q1 5 bp への到達時間(値段のラベルが 1 のプリント)"),
        ("grid.csv", grid_rows, "Q3 ② の格子 189 組(前半・遅れ 1 秒・費用込み・露出つき)"),
        ("knob_contrib.csv", knob_rows, "Q3 選んだ組の 1 ノブずつの寄与(露出つき)"),
        ("exposure.csv", exposure_rows, "Q3 露出(合計保有時間・保有 1 時間あたりの収支・"
                                        "同時建玉の最大)"),
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
        "前半のプリント数": len(prints_df),
        "連鎖に入るプリント": n_in_bundle, "束の外のプリント": n_no_bundle,
        "前半の連鎖数": len(all_cascades),
        "前半の日数": len(days), "2 分割の境の日": split_day,
        "費用": {"主のc_bp": c_main, "p75_bp": c_p75,
               "引き方": "連鎖 1 本 = c × 建玉の回数(型 B のドテン 1 回 = c)"},
        "①の基準率": {k: base_rates[k] for k in base_rates},
        "①の帯": {k: (list(bands[k]) if bands[k] else None) for k in bands},
        "①の5分割OOF": {fits[k]["scene"]: _rename_report(fits[k]["res"]["report"])
                    for k in fits},
        "値段のラベルの再計算": {"件数": len(recheck), "一致": n_match},
        "束の外(方策が通らないプリント)": outside_bundle_rows(df_outside)[0],
        "連鎖 1 本ごとの行": {"ファイル": "cascades.csv.gz", "行数": n_cascade_rows},
        "露出": exposure_rows,
        "②の格子": {"組数": len(grid_rows), "遅れ_秒": GRID_DELAY_S,
                 "ノブ": {"入る位置": list(ENTRY_POS_LEVELS),
                       "入る条件": list(COND_LEVELS), "出口": list(EXIT_LEVELS),
                       "損切り": list(STOP_LEVELS)},
                 "条件の分位": {k: [v[0], v[1]] for k, v in cuts.items()},
                 "条件の分位を切った母集団": cuts_note,
                 "1 本も入らなかった組": n_empty,
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
    ok5 = defaultdict(list)               # 方策 -> bitFlyer の約定の遅れが 5 秒以内か
    both_zero = defaultdict(int)          # 方策 -> どちらも 0(入らなかった)本数
    lags = {"Binance_入り": [], "Binance_出": [], "bitFlyer_入り": [], "bitFlyer_出": []}
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
        lag_ok = True
        if not r_bx["missing"] and not r_bf["missing"]:
            # D-5: 約定の遅れ(目標時刻から実際に約定するまで)を残す
            lx, lf = list(r_bx["fill_lag_ms"]), list(r_bf["fill_lag_ms"])
            if len(lx) == 2:
                lags["Binance_入り"].append(int(lx[0]))
                lags["Binance_出"].append(int(lx[1]))
            if len(lf) == 2:
                lags["bitFlyer_入り"].append(int(lf[0]))
                lags["bitFlyer_出"].append(int(lf[1]))
                lag_ok = max(lf) <= LAG_LIMIT_MS
            a, b = acc["全部逆張り(素)"]
            a.append(r_bf["pnl_bp"] - cost_bp * r_bf["n_entries"])
            b.append(r_bx["pnl_bp"] - cost_bp * r_bx["n_entries"])
            ok5["全部逆張り(素)"].append(bool(lag_ok))

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
                va = j_bf["pnl_bp"] - cost_bp * j_bf["n_entries"]
                vb = j_bx["pnl_bp"] - cost_bp * j_bx["n_entries"]
                a.append(va)
                b.append(vb)
                ok5["①3択A"].append(bool(lag_ok))
                if (not j_bx["entered"]) and (not j_bf["entered"]):
                    both_zero["①3択A"] += 1
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
                    lf2 = [x for x in (
                        (o_bf["入りの約定時刻"] or 0) - (o_bf["入りの目標時刻"] or 0),
                        (o_bf["出の約定時刻"] or 0) - (o_bf["出の目標時刻"] or 0))]
                    ok5["②opt"].append(max(lf2) <= LAG_LIMIT_MS)

    for name in ("全部逆張り(素)", "①3択A", "②opt"):
        if name == "②opt" and not chosen.get("選ばれた"):
            rows.append({"経路": "秒単位(標本日に掛かる前半の連鎖)", "区分": "②opt",
                         "対の数": 0,
                         "備考": "規則を満たす組が無かったので ②opt の行は作らない"})
            continue
        a, b = acc[name]
        rows.append({"経路": "秒単位(標本日に掛かる前半の連鎖)",
                     **paired_diff_row(name, a, b, "bitFlyerの合計_bp",
                                       "Binanceの合計_bp"),
                     "どちらも0の本数": both_zero.get(name, 0)})
        # D-5: bitFlyer の約定の遅れが 5 秒以内の対だけの版
        m = ok5.get(name) or []
        if len(m) == len(a):
            aa = [x for x, k in zip(a, m) if k]
            bb = [x for x, k in zip(b, m) if k]
            rows.append({"経路": "秒単位・bitFlyer の約定の遅れ ≤ 5 秒の対だけ",
                         **paired_diff_row(name, aa, bb, "bitFlyerの合計_bp",
                                           "Binanceの合計_bp")})
    rows.append({"経路": "秒単位(標本日に掛かる前半の連鎖)", "区分": "(母集団)",
                 "対の数": len(target),
                 "備考": f"標本日 {len(sample_days)} 日のうち前半に掛かる連鎖 "
                       f"{len(target)} 本。① の確率が引けなかった連鎖 {n_no_prob} 本"})
    # D-5: 約定の遅れの分位(全部逆張り(素)の入り・出、目標時刻からの差)
    for key, vals in lags.items():
        v = np.array(vals, dtype=float)
        q = quantiles(v, [50, 75, 90, 99]) if v.size else [NAN] * 4
        rows.append({"経路": "約定の遅れ(目標時刻からの差、全部逆張り(素))",
                     "区分": key, "対の数": int(v.size),
                     "遅れp50_ms": q[0], "遅れp75_ms": q[1], "遅れp90_ms": q[2],
                     "遅れp99_ms": q[3],
                     "遅れ最大_ms": (float(v.max()) if v.size else NAN),
                     "1秒超の割合": (float(np.mean(v > 1000)) if v.size else NAN),
                     "5秒超の割合": (float(np.mean(v > LAG_LIMIT_MS)) if v.size else NAN)})

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
# ---------------------------------------------------------------------------
# Q4 の表(連鎖 1 本ごとの行から作る。致命-1)
# ---------------------------------------------------------------------------
def _stats_of(vals: np.ndarray, days: np.ndarray) -> dict:
    q = quantiles(vals, [25, 50, 75]) if vals.size else [NAN] * 3
    _m, se_c, _sn, _n, ndays = (mean_se_cluster(vals, days) if vals.size
                                else (NAN, NAN, NAN, 0, 0))
    return {"n": int(vals.size), "合計_bp": float(vals.sum()) if vals.size else 0.0,
            "中央値": q[1], "p25": q[0], "p75": q[2],
            "負の割合": float(np.mean(vals < 0)) if vals.size else NAN,
            "日等重み平均": day_equal_weight_mean(vals, days) if vals.size else NAN,
            "日クラスタSE": se_c, "日数": ndays}


def build_q4_tables(lines: dict) -> dict:
    """`lines` = 表示名 -> 連鎖 1 本ごとの行(`bundle_id`・`day`・`side`・
    `連鎖の大きさ`・`最初に入った位置`・`pnl_net_bp`・`保有秒`・約定時刻)。
    設計 Q4 の 並置・対差・日ごと・位置別・大きさ別・側別・露出 を作る。"""
    side_by, size_by, pos_by, day_rows, main_rows, expo = [], [], [], [], [], []
    for name, rows in lines.items():
        ok = [r for r in rows if r["pnl_net_bp"] == r["pnl_net_bp"]]
        v = np.array([r["pnl_net_bp"] for r in ok], dtype=float)
        d = np.array([r["day"] for r in ok], dtype=object)
        main_rows.append({"方策": name, **_stats_of(v, d)})
        expo.append({"方策": name, "入った本数": sum(1 for r in ok if r.get("入った", 1)),
                     **exposure_of(ok)})
        by_day = defaultdict(float)
        for r in ok:
            by_day[r["day"]] += r["pnl_net_bp"]
        ser = sorted(by_day.items(), key=lambda kv: kv[1])
        vals = [x for _k, x in ser]
        day_rows.append({
            "方策": name, "日数": len(ser),
            "負の日の割合": (float(np.mean(np.array(vals) < 0)) if vals else NAN),
            "日の合計の中央値_bp": (float(np.median(vals)) if vals else NAN),
            "下位5日の合計_bp": float(sum(vals[:5])),
            "上位5日の合計_bp": float(sum(vals[-5:])),
            "上位5日": ", ".join(f"{k}:{x:.0f}" for k, x in ser[-5:]),
            "下位5日": ", ".join(f"{k}:{x:.0f}" for k, x in ser[:5])})
        for key, col in (("側別", "side"), ("大きさ別", "連鎖の大きさ"),
                         ("位置別", "最初に入った位置")):
            buckets = defaultdict(list)
            for r in ok:
                buckets[str(r.get(col, "-"))].append(r)
            for b, rs in sorted(buckets.items()):
                vv = np.array([r["pnl_net_bp"] for r in rs], dtype=float)
                dd = np.array([r["day"] for r in rs], dtype=object)
                row = {"方策": name, "区分": key, "水準": b, **_stats_of(vv, dd)}
                (side_by if key == "側別" else
                 size_by if key == "大きさ別" else pos_by).append(row)
    return {"並置": main_rows, "日ごと": day_rows, "側別": side_by,
            "大きさ別": size_by, "位置別": pos_by, "露出": expo}


def build_pair_diff_rows(lines: dict, pairs: tuple) -> list:
    """連鎖ごとの**対差**(同じ `bundle_id` で対にする)。設計 Q4。"""
    by_name = {}
    for name, rows in lines.items():
        by_name[name] = {r["bundle_id"]: r["pnl_net_bp"] for r in rows
                         if r["pnl_net_bp"] == r["pnl_net_bp"]}
    out = []
    for a, b in pairs:
        if a not in by_name or b not in by_name:
            out.append({"対差": f"{a} − {b}", "対の数": 0,
                        "備考": "片側の行が無いので作らない"})
            continue
        common = sorted(set(by_name[a]) & set(by_name[b]))
        d = np.array([by_name[a][k] - by_name[b][k] for k in common], dtype=float)
        q = quantiles(d, [25, 50, 75]) if d.size else [NAN] * 3
        out.append({"対差": f"{a} − {b}", "対の数": int(d.size),
                    "対差の合計_bp": float(d.sum()) if d.size else 0.0,
                    "対差の中央値_bp": q[1], "対差のp25_bp": q[0], "対差のp75_bp": q[2],
                    "対差が正の割合": (float(np.mean(d > 0)) if d.size else NAN),
                    "対差が0の本数": int(np.sum(d == 0)) if d.size else 0})
    return out


def cascade_rows_from_policy_rows(policy_rows: list, policy: str, ptype: str,
                                  delay: float, cost_bp: float) -> list:
    """`run_policies` の `cascade_rows` から 1 本の線(方策×型×遅れ)を取り出し、
    費用を引いた連鎖 1 本ごとの行にする。"""
    out = []
    for r in policy_rows:
        if r["方策"] != policy or r["型"] != ptype or r["遅れ_秒"] != delay:
            continue
        gross = r["pnl_bp"]
        out.append({**r,
                    "pnl_net_bp": (gross - cost_bp * r["建玉の回数"]
                                   if gross == gross else NAN),
                    "入りの約定時刻": r.get("入りの約定時刻_ms"),
                    "出の約定時刻": r.get("出の約定時刻_ms")})
    return out


# ---------------------------------------------------------------------------
# 段2(後半 2,000 本、一度だけ = 11 度目)。**この委任では走らせない。**
# ---------------------------------------------------------------------------
PRIOR_STAGE2_CASCADES = (REPO_ROOT / "backtest_data" / "o3c_signal_policy_20260920"
                         / "stage2_secondhalf" / "cascades.csv.gz")


def bundle_id_fingerprint(ids) -> str:
    """`bundle_id` の集合の指紋(並べて改行で繋いだ文字列の MD5)。"""
    import hashlib
    text = "\n".join(sorted(set(str(x) for x in ids))) + "\n"
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def prior_stage2_bundle_ids(path: Path = PRIOR_STAGE2_CASCADES) -> set:
    df = pd.read_csv(path, usecols=["bundle_id"], dtype={"bundle_id": str})
    return set(df["bundle_id"].astype(str))


def add_n2_by_day(sb, df_first: pd.DataFrame) -> pd.DataFrame:
    """N2 を日ごとに計算し、**日が変わるたびに約定のキャッシュを空にする**
    (反証者レビュー9 D-6(b): 228 日ぶんを溜めると 1.2 GB を超える)。"""
    parts = []
    for _day, g in df_first.groupby("day", sort=True):
        parts.append(lg.add_n2_column(sb, g.reset_index(drop=True)))
        sb._window_cache.clear()
        sb._raw_trade_cache.clear()
    return pd.concat(parts, ignore_index=True) if parts else df_first


def compute_value_probs_for_frame(sb, df: pd.DataFrame) -> tuple:
    """段2 用: materials の欠落で止まり(D-6(a))、N2 は日ごとにキャッシュを空にして
    計算する(D-6(b))。"""
    cand1 = pd.to_numeric(df["cand_1"], errors="coerce")
    first = df[cand1 == 0].reset_index(drop=True)
    if len(first):
        first = add_n2_by_day(sb, first)
    n2 = dict(zip(first["print_id"].astype(str).tolist(),
                  pd.to_numeric(first.get("cand_N2"), errors="coerce").tolist())
              ) if len(first) else {}
    prob = compute_value_logit_probs(sb, df, n2)
    pos = {pid: sp.position_of(c1) for pid, c1 in zip(df["print_id"], df["cand_1"])}
    return prob, pos


def synthetic_stage2_inputs() -> dict:
    """`--dry-run` 用の合成データ(**後半の行は 1 行も読まない**)。
    2 本の連鎖・偽の約定列で、段2 の組み立て(Q4 の表・対差・露出・cascades の列)を
    通す。"""
    times = np.arange(0, 800_000 + 1, 1_000, dtype=np.int64)
    prices = 100.0 + times / 1.0e7
    cascades = {
        "dry_0001": [
            {"print_id": "d1a", "ts_ms": 10_000, "side": "SELL", "day": "2024-03-01",
             "half": BACK_HALF, LABEL_VALUE: 1, sp.MAT1_COL: 0},
            {"print_id": "d1b", "ts_ms": 40_000, "side": "SELL", "day": "2024-03-01",
             "half": BACK_HALF, LABEL_VALUE: 0, sp.MAT1_COL: 1},
            {"print_id": "d1c", "ts_ms": 70_000, "side": "SELL", "day": "2024-03-01",
             "half": BACK_HALF, LABEL_VALUE: 0, sp.MAT1_COL: 2}],
        "dry_0002": [
            {"print_id": "d2a", "ts_ms": 200_000, "side": "BUY", "day": "2024-03-02",
             "half": BACK_HALF, LABEL_VALUE: 1, sp.MAT1_COL: 0}],
    }
    prob = {"d1a": 0.30, "d1b": 0.80, "d1c": 0.50, "d2a": 0.90}
    pos = {"d1a": POS_1ST, "d1b": POS_CHAIN, "d1c": POS_CHAIN, "d2a": POS_1ST}
    return {"cascades": cascades, "prob": prob, "pos": pos,
            "times": times, "prices": prices}


class SyntheticCache:
    """`--dry-run` 用の偽の約定の窓(`WindowCache` と同じ口だけ持つ)。"""

    def __init__(self, times, prices):
        self._t, self._p = times, prices

    def raw_at_or_after(self, t_ms, tol: int = STALENESS_MS):
        return price_at_or_after(self._t, self._p, int(t_ms), tol)

    def window_for(self, _day: str):
        return self._t, self._p


def run_stage2(out_dir: Path = DEFAULT_OUT_STAGE2, spread_dir: Path = SPREAD_DIR,
               dry_run: bool = False) -> dict:
    """段2(後半 2,000 本、一度だけ = 11 度目の読み)。**この委任では走らせない。**
    段1 で前半から固定した 帯・係数・費用・②opt をそのまま当てる(作り直さない)。
    `dry_run=True` は合成データで組み立てだけを通す(後半を 1 行も読まない)。"""
    t0 = time.time()
    c_main, c_p75 = spread.read_cost(spread_dir)
    s1 = json.loads((DEFAULT_OUT / "summary.json").read_text(encoding="utf-8"))
    bands = {k: (tuple(v) if v else None) for k, v in s1["①の帯"].items()}
    base_rates = s1["①の基準率"]
    chosen = s1["②の格子"]["選んだ組(主 = 入った本のみの中央値)"]
    cuts = {k: (v[0], v[1]) for k, v in s1["②の格子"]["条件の分位"].items()}
    costs = {COST_NONE: 0.0, COST_MAIN: c_main, COST_P75: c_p75}
    out_dir = Path(out_dir)
    if dry_run and out_dir == Path(DEFAULT_OUT_STAGE2):
        out_dir = OUT_ROOT / "stage2_dryrun"

    q0_rows = []
    if dry_run:
        syn = synthetic_stage2_inputs()
        picked = syn["cascades"]
        prob_of, pos_of = syn["prob"], syn["pos"]
        prob_liq, pos_liq = syn["prob"], syn["pos"]
        cache = SyntheticCache(syn["times"], syn["prices"])
        select_info = {"抜いた本数": len(picked),
                       "抜いた本数の内訳(単発/2件/3件以上)": {"合成": len(picked)}}
        q0_rows.append({"項目": "dry-run(合成データ、後半を読んでいない)",
                        "値": len(picked)})
    else:
        select_info = sp.select_stage2_cascades(k=N_CASCADES_STAGE2)
        picked = select_info["cascades"]
        # Q0: 後半 2,000 本の bundle_id が前段と同一か(MD5 で照合)
        ours = set(picked.keys())
        prior = prior_stage2_bundle_ids()
        q0_rows += [
            {"項目": "後半 2,000 本の bundle_id の MD5(この単位)",
             "値": bundle_id_fingerprint(ours)},
            {"項目": "後半 2,000 本の bundle_id の MD5(前段)",
             "値": bundle_id_fingerprint(prior)},
            {"項目": "前段と同一か", "値": int(ours == prior)},
            {"項目": "この単位にだけある bundle_id", "値": len(ours - prior)},
            {"項目": "前段にだけある bundle_id", "値": len(prior - ours)},
        ]
        if ours != prior:
            raise RuntimeError("[止め] 後半 2,000 本が前段の bundle_id と一致しない "
                               f"(この単位にだけ {len(ours - prior)} 本 / "
                               f"前段にだけ {len(prior - ours)} 本)")
        ids = {pr["print_id"] for prints in picked.values() for pr in prints}
        mat = pd.read_csv(ROWS_MATERIALS, low_memory=False)
        df = mat[mat["print_id"].isin(ids)].reset_index(drop=True)
        # D-6(a): 段1 と同じ停止を段2 にも入れる
        require_materials_cover(ids, set(df["print_id"]), "段2 の後半 2,000 本")
        sb = js.StateBuilder()
        prob_of, pos_of = compute_value_probs_for_frame(sb, df)
        # 参照 2 本(前段の清算のラベル。係数・経験分布・帯は前段のものを読むだけ)
        sb._window_cache.clear()
        sb._raw_trade_cache.clear()
        prob_liq = sp.stage2.compute_logit_probs(sb, df)
        sb._window_cache.clear()
        sb._raw_trade_cache.clear()
        pos_liq = pos_of
        cache = WindowCache(DATA_ROOT)

    built = run_policies(picked, prob_of, pos_of, bands, base_rates, cache)
    built_ref = run_policies(picked, prob_liq, pos_liq, bands, base_rates, cache,
                             policies=REF_POLICIES, types=(TYPE_A,),
                             baselines={}, kind=JUDGE_LIQ, count_policies=())
    all_policy_rows = built["cascade_rows"] + built_ref["cascade_rows"]
    dist_rows, pos_rows = _dist_rows_with_cost(all_policy_rows, costs,
                                              extra_policies=REF_POLICIES)

    # ②opt(段1 で選んだ組をそのまま当てる)
    opt_rows = []
    if chosen and chosen.get("選ばれた"):
        combo = chosen["組"]
        ei = ENTRY_POS_LEVELS.index(combo["入る位置"])
        for bid in chain_ids_in_day_order(picked):
            prints = picked[bid]
            times, prices = cache.window_for(str(prints[0]["day"]))
            if ei >= len(prints):
                continue
            if combo["入る条件"] != "なし":
                col, thr = cuts[combo["入る条件"]]
                v = cont._f(prints[ei].get(col))
                if not (math.isfinite(v) and math.isfinite(thr) and v >= thr):
                    continue
            r = simulate_reverse_entry(prints, REACT_SIGN[str(prints[0]["side"])], ei,
                                       combo["出口"], STOP_BP[combo["損切り"]],
                                       GRID_DELAY_S, times, prices)
            if r["入った"] and not r["欠測"]:
                opt_rows.append({
                    "bundle_id": bid, "day": str(prints[0]["day"]),
                    "side": str(prints[0]["side"]),
                    "連鎖の大きさ": sp.size_bucket(len(prints)), "n_prints": len(prints),
                    "pnl_bp": r["pnl_bp"],
                    "pnl_net_bp": r["pnl_bp"] - c_main * r["建玉の回数"],
                    "建玉の回数": r["建玉の回数"], "保有秒": r["保有秒"],
                    "入りの約定時刻": r["入りの約定時刻"], "出の約定時刻": r["出の約定時刻"],
                    "入った": 1, "欠測": 0, "出口の理由": r["出口の理由"],
                    "最初に入った位置": combo["入る位置"]})

    # Q4: 6 本の並置(主の c・遅れ 1 秒)
    lines = {
        "①3択A": cascade_rows_from_policy_rows(built["cascade_rows"], "logistic_3択",
                                              TYPE_A, MAIN_DELAY, c_main),
        "①3択B": cascade_rows_from_policy_rows(built["cascade_rows"], "logistic_3択",
                                              TYPE_B, MAIN_DELAY, c_main),
        "全部逆張り(素)": cascade_rows_from_policy_rows(built["cascade_rows"], "全部逆張り",
                                                  TYPE_A, MAIN_DELAY, c_main),
        "前段の3択(清算)A": cascade_rows_from_policy_rows(
            built_ref["cascade_rows"], "前段の3択(清算)", TYPE_A, MAIN_DELAY, c_main),
        "完全な判断(値段)A": cascade_rows_from_policy_rows(built["cascade_rows"], "完全な判断",
                                                    TYPE_A, MAIN_DELAY, c_main),
    }
    pairs = (("①3択A", "全部逆張り(素)"),)
    if opt_rows:
        lines["②opt"] = opt_rows
        pairs = (("①3択A", "②opt"), ("①3択A", "全部逆張り(素)"),
                 ("②opt", "全部逆張り(素)"))
    q4 = build_q4_tables(lines)
    pair_rows = build_pair_diff_rows(lines, pairs)
    if not opt_rows:
        pair_rows.append({"対差": "②opt を含む対差",
                          "備考": "②opt は規則を満たす組が無かったので作らない",
                          "対の数": 0})

    # Q1 併記(前段の 5,000 件に値段のラベルの較正表を当てる)
    calib5000 = []
    if not dry_run:
        manifest = json.loads(Path(sp.CALIB_MANIFEST).read_text(encoding="utf-8"))
        calib_ids = {p["print_id"] for p in manifest["prints"]}
        lab = pd.read_csv(ROWS_CONTINUE, usecols=["print_id", "kind", LABEL_VALUE],
                          low_memory=False)
        lab = lab[(lab["kind"] == "print") & (lab["print_id"].isin(calib_ids))]
        mat5 = mat[mat["print_id"].isin(calib_ids)].reset_index(drop=True)
        prob5, pos5 = compute_value_probs_for_frame(sb, mat5)
        y_of = dict(zip(lab["print_id"], pd.to_numeric(lab[LABEL_VALUE],
                                                       errors="coerce")))
        for scene in (POS_1ST, POS_CHAIN):
            pid = [p for p in mat5["print_id"] if pos5.get(p) == scene]
            pr = np.array([prob5.get(p, NAN) for p in pid], dtype=float)
            yy = np.array([y_of.get(p, NAN) for p in pid], dtype=float)
            cal = calibration_table(pr, yy)
            calib5000 += [{"場面": scene, "母集団": "前段の5,000件(後半)", **r}
                          for r in cal["rows"]]

    # Q5b
    q5b_rows = []
    if not dry_run:
        q5b_rows = run_q5b(picked, chosen, prob_of, pos_of, bands, base_rates,
                           cache, c_main, cuts, minute_rows_for(picked, cache, c_main))

    out_dir.mkdir(parents=True, exist_ok=True)
    cascade_file_rows = build_cascade_rows_file(
        all_policy_rows, costs, {"②opt": opt_rows} if opt_rows else None)
    n_cascade_rows = write_cascades_gz(out_dir, cascade_file_rows)

    tables = [
        ("q0_selfcheck.csv", q0_rows, "Q0 自己点検(bundle_id の MD5 照合)"),
        ("calib_5000.csv", calib5000, "Q1 併記(前段の 5,000 件に値段のラベルの較正表)"),
        ("dist_table.csv", dist_rows, "Q2 連鎖ごとの損益分布(参照 2 本を含む)"),
        ("position_breakdown.csv", pos_rows, "Q2 位置別の内訳"),
        ("judge_counts.csv", sp.build_judge_count_table(built["judge_counts"]),
         "Q2 判断の件数"),
        ("action_counts.csv", sp.build_action_count_table(built["action_counts"]),
         "Q2 行動の件数"),
        ("q4_main.csv", q4["並置"], "Q4 6 本の並置(費用込み・遅れ 1 秒)"),
        ("q4_pair_diff.csv", pair_rows, "Q4 連鎖ごとの対差"),
        ("q4_by_day.csv", q4["日ごと"], "Q4 日ごとの合計の分布"),
        ("q4_by_side.csv", q4["側別"], "Q4 側別"),
        ("q4_by_size.csv", q4["大きさ別"], "Q4 大きさ別"),
        ("q4_by_position.csv", q4["位置別"], "Q4 位置別"),
        ("q4_exposure.csv", q4["露出"], "Q4 露出(合計保有時間・保有 1 時間あたり・"
                                       "同時建玉の最大)"),
        ("q5b_secs_secondhalf.csv", q5b_rows, "Q5b 経路差(後半)"),
    ]
    summary = {"段": ("段2(dry-run、合成データ)" if dry_run
                    else "段2(後半 2,000 本、一度だけ)"),
               "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
               "委任文": DELEGATION, "設計": DESIGN, "種": SEED,
               "抜いた連鎖の本数": select_info["抜いた本数"],
               "費用": {"主のc_bp": c_main, "p75_bp": c_p75},
               "連鎖 1 本ごとの行": {"ファイル": "cascades.csv.gz", "行数": n_cascade_rows},
               "段1から読んだもの(作り直していない)":
                   {"帯": s1["①の帯"], "基準率": s1["①の基準率"], "②opt": chosen},
               "参照 2 本": list(REF_POLICIES),
               "所要秒": round(time.time() - t0, 1)}
    return write_output(out_dir, tables, summary)


def minute_rows_for(cascades: dict, cache, cost_bp: float) -> list:
    """Q5b (b) 用の 1 分の始値の行(段2 は日ごとの一巡を持たないのでここで作る)。"""
    bf_ts, bf_open = load_bitflyer_1m(years=(2023, 2024, 2025))
    rows = []
    cur_day, mt, mp = None, None, None
    for bid in chain_ids_in_day_order(cascades):
        prints = cascades[bid]
        day = str(prints[0]["day"])
        if day != cur_day:
            t, pxs = cache.window_for(day)
            mt, mp = minute_open_map(t, pxs)
            cur_day = day
        direction = -REACT_SIGN[str(prints[0]["side"])]
        entry_ts = int(prints[0]["ts_ms"])
        exit_ts = int(prints[-1]["ts_ms"]) + CASCADE_END_GAP_S * 1000
        v_bf = pnl_next_minute_open(entry_ts, exit_ts, direction, bf_ts, bf_open)
        v_bx = pnl_next_minute_open(entry_ts, exit_ts, direction, mt, mp)
        rows.append({"bundle_id": bid, "day": day,
                     "bitFlyer_bp": (v_bf - cost_bp if v_bf == v_bf else NAN),
                     "Binance_bp": (v_bx - cost_bp if v_bx == v_bx else NAN)})
    return rows


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
    p2.add_argument("--dry-run", action="store_true",
                    help="合成データで組み立てだけを通す(後半を 1 行も読まない)")
    a = ap.parse_args(argv)
    if a.cmd == "stage1":
        run_stage1(a.out, a.half)
    else:
        run_stage2(a.out, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
