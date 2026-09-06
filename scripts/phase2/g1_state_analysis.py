#!/usr/bin/env python
"""G1 条件分析 — PHASE2_TEMPLATES.md §6 applied to P2-01 / P2-02 / P2-03.

DESCRIPTIVE, POST-SEAL, HYPOTHESIS-GENERATING ONLY.

All three units' seals are already consumed: their final evaluations ran on
2026-09-06 and their judgment proposals are written. Nothing computed here can
change those judgments (§6.4: 条件分析は主検定の判定を変えない). This pass exists
only to say WHERE each unit's overnight leg was larger or smaller, so that a
state which reaches 候補 can be written up as a CONDITIONAL hypothesis in a NEW
pre-registered unit (added to that unit's 探索面 N) and tested on data that is
still sealed, or forward.

What it does, per unit (and per series where a unit has several):

  1. Rebuilds the unit's FULL history by concatenating the dev-set pair CSV
     and the sealed-period pair CSV that unit's own runners already wrote
     (`backtest_data/phase2_runs/<unit>/...`). No raw price file, no external
     market data, and no P2-04 file is opened — every state variable below is
     derived from the pair rows themselves (their dates, their close_t series,
     and the columns the unit's own runner already put there).
  2. Builds the pre-registered candidate state variables from §6.1 that are
     computable that way: realized-vol tercile, prior-day return sign, prior-day
     return tercile, days to the next monthly second Friday, weekday, month,
     night count, and the unit's own pre-registered institutional regimes.
     §6.1's "海外市場の同日リターン" is deliberately NOT built in this pass (it
     would need external market data).
  3. Runs `bot.research.overnight.state_split` on the unit's main-set rows with
     the unit's own primary value column and conservative per-pair cost, and
     writes the state table, the difference table and the joint-permutation null
     p95, plus a Japanese RESULTS.md with the fixed three-line summary.

Usage:
    PYTHONPATH=src python scripts/phase2/g1_state_analysis.py
    PYTHONPATH=src python scripts/phase2/g1_state_analysis.py --units P2-03
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.research.overnight import (  # noqa: E402
    STATE_VERDICT_CANDIDATE,
    STATE_VERDICT_NO_DIFF,
    STATE_VERDICT_UNDECIDABLE,
    block_bootstrap_ci,
    state_split,
)

RUNS = REPO_ROOT / "backtest_data" / "phase2_runs"
OUT_DIR = RUNS / "G1_state_analysis_20260906"

# Pre-registered resampling parameters, identical to the three units' own runs
# (PREREG "ブロック・ブートストラップ(20 営業日、2,000 回)"). §6.3 reuses the
# same block for the joint permutation null.
BLOCK = 20
N_BOOT = 2000
SEED = 20260906

# Realized vol / prior-day return are built from close-to-close returns of the
# pair rows' own close_t series. A close-to-close move beyond this magnitude is
# a split or a bad print, not a return (it is exactly the 30% threshold P2-02
# and P2-03 pre-registered for their bad-print rule), so it is marked MISSING
# rather than used -- the affected days' vol/prior-return states become 不明 and
# drop out of those two variables only.
CC_ABS_MAX = 0.30
VOL_WINDOW = 20

LABEL_UNKNOWN = None  # a state variable that is not defined for a row

# --- state variable names (also the "variable" column of the output CSVs) ---
V_VOL = "実現ボラ三分位"
V_PREV_SIGN = "直前リターン符号"
V_PREV_TERCILE = "直前リターン三分位"
V_SQ = "SQまでの日数"
V_WEEKDAY = "曜日"
V_MONTH = "月"
V_NIGHTS = "泊数"
V_REGIME = "制度区分"

WEEKDAY_LABELS = ["1_月", "2_火", "3_水", "4_木", "5_金", "6_土", "7_日"]


# ---------------------------------------------------------------------------
# unit specifications
# ---------------------------------------------------------------------------

# Each series names the two pair CSVs to concatenate (dev set first), the
# column layout of that unit's runner, the unit's main-set filter, its primary
# value column and its conservative per-pair cost column.
UNITS: dict[str, dict] = {
    "P2-01": {
        "title": "P2-01 日経 225 先物オーバーナイト(マイクロ)",
        "note": (
            "本単位の封印データは開封済み(最終評価をオーナー承認のもとで実施、"
            "`final_20260906/RUN.json` に `unseal_approved_md5` を記録)。"
            "したがってここでは 2007-09-19 以降の全履歴(開発セット + 封印期間)を使う。"
        ),
        "date_col": "date",
        "date_t1_col": "date_t1",
        "value_col": "r_night_bps",
        "cost_col": "cost_bps_cons",
        "main_filter": lambda d: (~d["is_glitch"].astype(bool))
                                 & (~d["roll_quarterly"].astype(bool)),
        "main_filter_text": (
            "誤プリント(|単純収益| > 0.10)除外 かつ 四半期ロール隣接ペア除外"
            "(最終評価の確定構成)"
        ),
        "value_text": "r_night_bps(グロス夜間リターン、単純収益 bps)",
        "cost_text": "cost_bps_cons(保守往復コスト 122 円 / (close_t × 10) bps)",
        "nights_col": "nights",
        "regime_col": "regime",
        "regime_text": "各ペア CSV の `regime` 列(本単位が事前登録した制度区分そのもの)",
        "series": [{
            "name": "N225F",
            "dev": "P2-01/iter1_20260906/pairs.csv",
            "sealed": "P2-01/final_20260906/pairs.csv",
        }],
    },
    "P2-02": {
        "title": "P2-02 J-REIT ETF 夜間プレミアム(1343、対照 1321)",
        "note": (
            "1343 は権利落ち補正後の `r_night_adj_bps`(本単位の主指標の系列)、"
            "対照の 1321 は分配金補正を持たないため `r_night_raw_bps` を使う。"
        ),
        "date_col": "t_date",
        "date_t1_col": "t1_date",
        "cost_col": "cost_conservative_bps",
        "main_filter": lambda d: d["kept"].astype(bool),
        "main_filter_text": "`kept`(規則 1 の式入力異常・幽霊行を除外した集合)",
        "cost_text": "cost_conservative_bps(呼値 1 ティック×片側 2 回、ペアごとに bps 換算)",
        "nights_col": None,
        "regime_col": None,
        # Pre-registered institutional dates named in docs/PHASE2/P2-02/PREREG.md:
        # the JPX T+2 settlement cutover (used by the unit's own ex-date rule)
        # and the 2024-11-05 closing-auction move 15:00 -> 15:30.
        "regime_dates": ["2019-07-16", "2024-11-05"],
        "regime_text": "2019-07-16(T+2 移行)・2024-11-05(引け板寄せ 15:30 化)",
        "series": [
            {"name": "1343", "dev": "P2-02/iter0_20260906/pairs_1343_dev.csv",
             "sealed": "P2-02/final_20260906/pairs_1343_sealed.csv",
             "value_col": "r_night_adj_bps",
             "value_text": "r_night_adj_bps(権利落ち補正後のグロス夜間リターン bps)"},
            {"name": "1321", "dev": "P2-02/iter0_20260906/pairs_1321_dev.csv",
             "sealed": "P2-02/final_20260906/pairs_1321_sealed.csv",
             "value_col": "r_night_raw_bps",
             "value_text": "r_night_raw_bps(グロス夜間リターン bps)"},
        ],
    },
    "P2-03": {
        "title": "P2-03 JPX 夜間プレミアム 市場横断(1306 / 1591 / 2516、参照 1321)",
        "note": "ETF ごとに独立に条件分析を行う(帰無も ETF ごとに別立て)。",
        "date_col": "date_t",
        "date_t1_col": "date_t1",
        "value_col": "r_night_bps",
        "cost_col": "cost_cons_bps",
        "main_filter": lambda d: d["clean"].astype(bool),
        "main_filter_text": "`clean`(誤プリント・分割・null・幽霊行を除外した集合)",
        "value_text": "r_night_bps(グロス夜間リターン bps)",
        "cost_text": "cost_cons_bps(価格帯ごとの呼値 1 ティック×片側 2 回)",
        "nights_col": None,
        "regime_col": None,
        "regime_dates": ["2024-11-05"],
        "regime_text": "2024-11-05(引け板寄せ 15:30 化)",
        "series": [
            {"name": s, "dev": f"P2-03/iter1_20260906/pairs_{s.replace('.', '')}.csv",
             "sealed": f"P2-03/final_20260906/pairs_{s.replace('.', '')}.csv"}
            for s in ("1306T", "1591T", "2516T", "1321T")
        ],
    },
}


# ---------------------------------------------------------------------------
# state variable construction
# ---------------------------------------------------------------------------

def second_friday(year: int, month: int) -> pd.Timestamp:
    """The monthly SQ reference day: the 2nd Friday of the given month."""
    first = pd.Timestamp(year=year, month=month, day=1)
    offset = (4 - first.dayofweek) % 7  # 4 == Friday
    return first + pd.Timedelta(days=offset + 7)


def days_to_next_second_friday(d: pd.Timestamp) -> int:
    """Calendar days from `d` to the next monthly 2nd Friday on or after `d`."""
    target = second_friday(d.year, d.month)
    if target < d:
        nxt = d + pd.offsets.MonthBegin(1)
        target = second_friday(nxt.year, nxt.month)
    return int((target - d).days)


def tercile_labels(values: np.ndarray, labels: tuple[str, str, str]) -> np.ndarray:
    """Label each finite value by its tercile of the finite values' own
    distribution; non-finite values get LABEL_UNKNOWN.

    The tercile cut points are those of the ANALYSED sample (this unit's main
    set over its full history), which is a whole-sample quantity -- fine for a
    descriptive, post-seal pass, and stated as such in RESULTS.md.
    """
    out = np.full(len(values), LABEL_UNKNOWN, dtype=object)
    ok = np.isfinite(values)
    if ok.sum() < 3:
        return out
    q1, q2 = np.quantile(values[ok], [1 / 3, 2 / 3])
    out[ok & (values <= q1)] = labels[0]
    out[ok & (values > q1) & (values <= q2)] = labels[1]
    out[ok & (values > q2)] = labels[2]
    return out


def close_to_close_returns(dates: pd.Series, closes: pd.Series) -> np.ndarray:
    """cc(t) = close(t)/close(t-1) - 1 over the pair rows' own close series.

    Rows are assumed already sorted by date. A non-positive close, or a move
    beyond CC_ABS_MAX (a split or a bad print, not a return), yields nan.
    """
    c = pd.to_numeric(closes, errors="coerce").astype(float)
    c = c.where(c > 0)
    cc = np.array((c / c.shift(1) - 1.0).to_numpy(dtype=float), copy=True)
    cc[np.abs(cc) > CC_ABS_MAX] = np.nan
    return cc


def realized_vol(cc: np.ndarray, window: int = VOL_WINDOW) -> np.ndarray:
    """Rolling standard deviation of the last `window` close-to-close returns,
    ending at (and including) t -- i.e. observable at the close(t) entry.

    A window containing any missing cc is itself missing (fail closed).
    """
    return pd.Series(cc).rolling(window, min_periods=window).std(ddof=1).to_numpy()


def regime_labels(dates: pd.Series, boundaries: list[str]) -> np.ndarray:
    """Label rows by the pre-registered institutional boundary dates.

    Labels read "<lo>..<hi>" so that sorting them as strings is chronological.
    """
    bounds = [pd.Timestamp(b) for b in sorted(boundaries)]
    edges = [dates.min()] + bounds + [dates.max() + pd.Timedelta(days=1)]
    out = np.full(len(dates), LABEL_UNKNOWN, dtype=object)
    d = dates.to_numpy()
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        mask = (d >= np.datetime64(lo)) & (d < np.datetime64(hi))
        hi_label = (hi - pd.Timedelta(days=1)).date()
        out[mask] = f"{lo.date()}..{hi_label}"
    return out


def build_states(df: pd.DataFrame, spec: dict, cc: np.ndarray,
                 vol: np.ndarray) -> dict[str, np.ndarray]:
    """The §6.1 candidate state variables computable from the pair rows alone.

    `df` is the unit's MAIN SET, sorted by entry date, with the columns
    `_date`, `_date_t1` and (where the unit has one) the runner's nights and
    regime columns. `cc` and `vol` are the close-to-close returns and the
    realized vol for exactly those rows, but computed BEFORE the main-set
    filter (on the unit's full pair series) so that a day dropped by the
    filter -- a roll-adjacent pair, say -- still contributes its close to the
    following days' vol window instead of silently shortening it.
    """
    dates = df["_date"]
    states: dict[str, np.ndarray] = {}
    states[V_VOL] = tercile_labels(vol, ("1_低", "2_中", "3_高"))
    sign = np.full(len(df), LABEL_UNKNOWN, dtype=object)
    ok = np.isfinite(cc)
    sign[ok & (cc > 0)] = "1_上昇"
    sign[ok & (cc <= 0)] = "2_非上昇"
    states[V_PREV_SIGN] = sign
    states[V_PREV_TERCILE] = tercile_labels(cc, ("1_下位", "2_中位", "3_上位"))

    sq = np.array([days_to_next_second_friday(d) for d in dates], dtype=float)
    sq_lab = np.full(len(df), LABEL_UNKNOWN, dtype=object)
    sq_lab[sq <= 2] = "1_0-2日"
    sq_lab[(sq >= 3) & (sq <= 9)] = "2_3-9日"
    sq_lab[sq >= 10] = "3_10日以上"
    states[V_SQ] = sq_lab

    states[V_WEEKDAY] = np.array(
        [WEEKDAY_LABELS[d.dayofweek] for d in dates], dtype=object)
    states[V_MONTH] = np.array([f"{d.month:02d}" for d in dates], dtype=object)

    if spec["nights_col"] and spec["nights_col"] in df.columns:
        nights = pd.to_numeric(df[spec["nights_col"]], errors="coerce").to_numpy(float)
    else:
        nights = (df["_date_t1"] - dates).dt.days.to_numpy(dtype=float)
    nb = np.full(len(df), LABEL_UNKNOWN, dtype=object)
    nb[nights == 1] = "1_1泊"
    nb[(nights >= 2) & (nights <= 3)] = "2_2-3泊"
    nb[nights >= 4] = "3_4泊以上"
    states[V_NIGHTS] = nb

    if spec["regime_col"] and spec["regime_col"] in df.columns:
        states[V_REGIME] = df[spec["regime_col"]].astype(object).to_numpy()
    else:
        states[V_REGIME] = regime_labels(dates, spec["regime_dates"])
    return states


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_series(spec: dict, series: dict) -> tuple[pd.DataFrame, dict]:
    """Concatenate the dev-set and sealed-period pair CSVs into full history."""
    paths = [RUNS / series["dev"], RUNS / series["sealed"]]
    frames = []
    for p in paths:
        d = pd.read_csv(p)
        d["_source"] = "dev" if p == paths[0] else "sealed"
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["_date"] = pd.to_datetime(df[spec["date_col"]])
    df["_date_t1"] = pd.to_datetime(df[spec["date_t1_col"]])
    df["_close"] = pd.to_numeric(df["close_t"], errors="coerce")
    df = df.sort_values("_date", kind="stable").reset_index(drop=True)
    if df["_date"].duplicated().any():
        raise ValueError(f"{series['name']}: duplicate entry dates across dev+sealed")
    provenance = {
        "series": series["name"],
        "inputs": [{"path": str(p.relative_to(REPO_ROOT)), "md5": md5(p),
                    "rows": int(len(f))} for p, f in zip(paths, frames)],
        "rows_combined": int(len(df)),
        "span": [str(df["_date"].min().date()), str(df["_date"].max().date())],
        "seam": [str(frames[0][spec["date_col"]].max()),
                 str(frames[1][spec["date_col"]].min())],
    }
    return df, provenance


# ---------------------------------------------------------------------------
# per-series analysis
# ---------------------------------------------------------------------------

def analyse_series(unit: str, spec: dict, series: dict) -> dict:
    df, provenance = load_series(spec, series)
    n_all = len(df)
    # vol / prior-day return come from the FULL pair series' close column, so
    # that rows the main-set filter drops still supply their close.
    cc_all = close_to_close_returns(df["_date"], df["_close"])
    vol_all = realized_vol(cc_all)

    value_col = series.get("value_col", spec.get("value_col"))
    cost_col = spec["cost_col"]
    values_all = pd.to_numeric(df[value_col], errors="coerce").to_numpy(float)
    cost_all = pd.to_numeric(df[cost_col], errors="coerce").to_numpy(float)
    keep = (spec["main_filter"](df).to_numpy(bool)
            & np.isfinite(values_all) & np.isfinite(cost_all))
    main = df[keep].reset_index(drop=True)
    values, cost = values_all[keep], cost_all[keep]

    states = build_states(main, spec, cc_all[keep], vol_all[keep])
    res = state_split(values, states, block=BLOCK, n_boot=N_BOOT, seed=SEED,
                      cost_bps=cost)

    gross_ci = block_bootstrap_ci(values, block=BLOCK, n_boot=N_BOOT, seed=SEED)
    net = values - cost
    net_ci = block_bootstrap_ci(net, block=BLOCK, n_boot=N_BOOT, seed=SEED)

    res["state_table"].insert(0, "series", series["name"])
    res["diff_table"].insert(0, "series", series["name"])
    return {
        "unit": unit,
        "series": series["name"],
        "provenance": provenance,
        "n_all_pairs": n_all,
        "n_main": int(len(main)),
        "value_col": value_col,
        "value_text": series.get("value_text", spec.get("value_text")),
        "span_main": [str(main["_date"].min().date()), str(main["_date"].max().date())],
        "uncond_mean": float(values.mean()),
        "uncond_ci": list(gross_ci),
        "uncond_net_mean": float(net.mean()),
        "uncond_net_ci": list(net_ci),
        "null_p95": res["null_p95"],
        "state_table": res["state_table"],
        "diff_table": res["diff_table"],
        "params": res["params"],
    }


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def fmt(v: float, nd: int = 2) -> str:
    return "nan" if v is None or not np.isfinite(v) else f"{v:.{nd}f}"


def summary_lines(out: dict) -> list[str]:
    """The fixed three-line 平文要約 of §6.6."""
    dt = out["diff_table"]
    cand = dt[dt["verdict"] == STATE_VERDICT_CANDIDATE]
    p95 = out["null_p95"]

    if len(cand):
        hi, lo = [], []
        for r in cand.itertuples():
            # name the HIGHER state first, flipping the difference and its CI
            # together so the quoted interval is the interval of the quoted
            # difference (higher - lower), not of a - b.
            if r.diff > 0:
                a, b, d, ci = r.state_a, r.state_b, r.diff, (r.ci_lo, r.ci_hi)
            else:
                a, b, d, ci = r.state_b, r.state_a, -r.diff, (-r.ci_hi, -r.ci_lo)
            hi.append(f"{r.variable}={a}(対 {r.variable}={b} で差 {fmt(d)}bps, "
                      f"CI [{fmt(ci[0])}, {fmt(ci[1])}])")
            lo.append(f"{r.variable}={b}")
        works = "・".join(dict.fromkeys(hi))
        fails = "・".join(dict.fromkeys(lo))
    else:
        works = f"該当なし(同時置換の帰無 95 点 {fmt(p95)}bps を超える差が無い)"
        fails = "該当なし(候補水準に達した差が無いため名指しできない)"

    und = dt[dt["verdict"] == STATE_VERDICT_UNDECIDABLE].copy()
    if len(und):
        und["absdiff"] = und["diff"].abs()
        top = und.sort_values("absdiff", ascending=False).head(3)
        gaps = "・".join(
            f"{r.variable} {r.state_a}−{r.state_b}(差 {fmt(r.diff)}bps < MDE {fmt(r.mde)}bps)"
            for r in top.itertuples())
        undecided = f"{len(und)} 組が MDE 未満で判定不能。最大の穴は {gaps}"
    else:
        undecided = "該当なし"

    return [
        f"- **効く状況**: {works}",
        f"- **効かない状況**: {fails}",
        f"- **判定不能な状況**: {undecided}",
    ]


BANNER = """> ## ⚠ この文書は記述であって判定ではない
>
> - **記述的・封印後・仮説生成のみ**。P2-01 / P2-02 / P2-03 の封印は既に消費され、
>   最終評価と判定案は確定している。本書の数値は **その判定を一切変えない**
>   (`docs/PHASE2_TEMPLATES.md` §6.4「条件分析は主検定の判定を変えない」)。
> - ここで「候補」と付いた状態は、**次の単位の材料**でしかない。使うには
>   §6.4 のとおり **条件付き仮説として新規単位を事前登録**し(探索面 N に加算)、
>   封印が残っていれば封印で、無ければフォワードで検証する。
> - 本書の状態変数は**封印を消費した後の全履歴**の上で作られており、三分位の
>   切り所も分析対象標本そのものから取っている。したがってここに現れた差は
>   **検証されていない**。「候補」を成績として読んではならない。
> - 「判定不能」は「差が無い」ではない(§6.2)。n が足りず**見えない**という意味。
"""


def write_results(results: dict[str, list[dict]], out_dir: Path) -> None:
    lines: list[str] = []
    lines.append("# G1 3 単位の条件分析(PHASE2_TEMPLATES.md §6)— 2026-09-06")
    lines.append("")
    lines.append(BANNER)
    lines.append("")
    lines.append("## 0. 手順(全単位共通)")
    lines.append("")
    lines.append(
        f"- 実装 = `src/bot/research/overnight.py: state_split`。"
        f"ブロック長 {BLOCK}、ブートストラップ/置換 {N_BOOT} 回、seed {SEED}。")
    lines.append(
        "- 各状態の n・平均・95% CI(ブロック・ブートストラップ)と費用後平均・CI、"
        "変数ごとの全状態対の差・CI・MDE(2.8016 × ブートストラップ SE)を出す。")
    lines.append(
        "- **多重性**: 全変数 × 全状態対を 1 つの**同時置換の帰無**で扱う(§6.3)。"
        "1 draw = 値系列を 20 標本ブロック単位で 1 回だけ並べ替え、その 1 つの世界から"
        "全変数の全状態差を計算して最大絶対差を取る。2,000 draw の 95 点が「候補」のバー。")
    lines.append(
        "- 判定文(固定): |差| > 帰無 95 点 **かつ** 差の CI がゼロを除外 → 「候補」/ "
        "MDE > |差| → 「判定不能」/ それ以外 → 「差なし」。")
    lines.append("")
    lines.append("### 状態変数(§6.1 のうち、ペア CSV だけで作れるもの)")
    lines.append("")
    lines.append(f"| 変数 | 定義 |")
    lines.append("|---|---|")
    lines.append(f"| {V_VOL} | close(t)/close(t−1)−1 の直近 {VOL_WINDOW} 標本の標準偏差"
                 "(t 時点で観測可能)の三分位 |")
    lines.append(f"| {V_PREV_SIGN} | 直前の close-to-close リターンの符号(> 0 / ≤ 0) |")
    lines.append(f"| {V_PREV_TERCILE} | 同リターンの三分位 |")
    lines.append(f"| {V_SQ} | 建玉日から次の「月次第 2 金曜」までの暦日数(0-2 / 3-9 / 10+) |")
    lines.append(f"| {V_WEEKDAY} | 建玉日(t)の曜日 |")
    lines.append(f"| {V_MONTH} | 建玉日(t)の月 |")
    lines.append(f"| {V_NIGHTS} | 建玉の泊数(1 / 2-3 / 4+) |")
    lines.append(f"| {V_REGIME} | 各単位が事前登録した制度日で区切った区分 |")
    lines.append("")
    lines.append(
        "- **本パスでは海外市場の同日リターン(米国株・為替)は一切使っていない**"
        "(§6.1 の候補のうち外部データが要るものは次パスに回す)。出来高三分位も"
        "全単位に共通して揃わないため今回は作らない。")
    lines.append(
        f"- close-to-close の絶対値が {CC_ABS_MAX:.0%} を超える日は分割・誤プリントとして"
        "**欠測**扱い(各単位が事前登録した誤プリント閾値と同じ)。実現ボラは窓 "
        f"{VOL_WINDOW} 標本に欠測があればその日も欠測。欠測日は当該 2 変数からのみ落ちる。")
    lines.append(
        "- 三分位の切り所は**分析対象標本そのもの**の分位点(全標本量)。"
        "記述目的にはこれで足りるが、そのぶんここでの差は検証済みではない。")
    lines.append(
        "- 開発セット CSV と封印期間 CSV の継ぎ目では、端点規則で落ちた 1 ペア分の"
        "close が抜けるため、その 1 日の close-to-close は 2 営業日分になる"
        "(系列ごとに 1 か所。継ぎ目の日付は `RUN.json` の `provenance.seam`)。")
    lines.append("")

    for unit, outs in results.items():
        spec = UNITS[unit]
        lines.append(f"## {unit} — {spec['title']}")
        lines.append("")
        if spec.get("note"):
            lines.append(f"{spec['note']}")
            lines.append("")
        lines.append(f"- 主集合の規則: {spec['main_filter_text']}")
        lines.append(f"- 費用: {spec['cost_text']}")
        lines.append(f"- 制度区分: {spec['regime_text']}")
        lines.append("")
        lines.append("| 系列 | 期間 | 全ペア | 主集合 n | 無条件グロス平均 [CI] | "
                     "無条件・保守費用後 [CI] | 同時置換の帰無 95 点 | 比較数 |")
        lines.append("|---|---|---:|---:|---|---|---:|---:|")
        for o in outs:
            lines.append(
                f"| {o['series']} | {o['span_main'][0]}..{o['span_main'][1]} | "
                f"{o['n_all_pairs']} | {o['n_main']} | "
                f"{fmt(o['uncond_mean'])} [{fmt(o['uncond_ci'][0])}, {fmt(o['uncond_ci'][1])}] | "
                f"{fmt(o['uncond_net_mean'])} [{fmt(o['uncond_net_ci'][0])}, "
                f"{fmt(o['uncond_net_ci'][1])}] | "
                f"{fmt(o['null_p95'])} | {o['params']['n_comparisons']} |")
        lines.append("")
        for o in outs:
            lines.append(f"### {unit} / {o['series']} — 3 行要約")
            lines.append("")
            lines.append(f"値 = {o['value_text']}。")
            lines.append("")
            lines.extend(summary_lines(o))
            lines.append("")
            cand = o["diff_table"][o["diff_table"]["verdict"] == STATE_VERDICT_CANDIDATE]
            if len(cand):
                lines.append("候補に達した差:")
                lines.append("")
                lines.append("| 変数 | 状態 A | 状態 B | n_A | n_B | 差(A−B) | 95% CI | "
                             "MDE | 帰無 95 点 |")
                lines.append("|---|---|---|---:|---:|---:|---|---:|---:|")
                for r in cand.itertuples():
                    lines.append(
                        f"| {r.variable} | {r.state_a} | {r.state_b} | {r.n_a} | {r.n_b} | "
                        f"{fmt(r.diff)} | [{fmt(r.ci_lo)}, {fmt(r.ci_hi)}] | "
                        f"{fmt(r.mde)} | {fmt(r.null_p95)} |")
                lines.append("")
            counts = o["diff_table"]["verdict"].value_counts()
            lines.append(
                "判定の内訳: "
                + " / ".join(f"{k} {int(counts.get(k, 0))}"
                             for k in (STATE_VERDICT_CANDIDATE, STATE_VERDICT_NO_DIFF,
                                       STATE_VERDICT_UNDECIDABLE))
                + "。")
            lines.append("")
        lines.append(f"出力: `{unit}_state_table.csv` / `{unit}_diff_table.csv` / "
                     f"`{unit}_null.csv`。")
        lines.append("")

    lines.append("## 次に何をするか(§6.4)")
    lines.append("")
    lines.append(
        "- 「候補」がある単位は、その状態を条件に置いた**条件付き仮説**として新規単位を"
        "事前登録し(探索面 N に加算)、まだ封印が残っている単位の封印か、"
        "フォワードで検証する。本書自体は検証ではない。")
    lines.append(
        "- 「候補」が無い単位について「状態によらず一様」と書いてはならない。"
        "帰無 95 点と MDE の両方が大きく、**見えていないだけ**の可能性が残る。")
    lines.append("")
    (out_dir / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--units", nargs="*", default=list(UNITS),
                    help="units to analyse (default: all three)")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[dict]] = {}
    run_meta: dict = {"generated": "2026-09-06", "block": BLOCK, "n_boot": N_BOOT,
                      "seed": SEED, "cc_abs_max": CC_ABS_MAX,
                      "vol_window": VOL_WINDOW,
                      "script": "scripts/phase2/g1_state_analysis.py",
                      "uses_external_market_data": False,
                      "descriptive_post_seal_only": True, "units": {}}

    for unit in args.units:
        spec = UNITS[unit]
        outs = []
        for series in spec["series"]:
            print(f"[{unit}] {series['name']} ...", flush=True)
            outs.append(analyse_series(unit, spec, series))
        results[unit] = outs

        pd.concat([o["state_table"] for o in outs], ignore_index=True).to_csv(
            out_dir / f"{unit}_state_table.csv", index=False)
        pd.concat([o["diff_table"] for o in outs], ignore_index=True).to_csv(
            out_dir / f"{unit}_diff_table.csv", index=False)
        pd.DataFrame([{
            "series": o["series"], "n_main": o["n_main"],
            "null_p95_bps": o["null_p95"],
            "n_variables": o["params"]["n_variables"],
            "n_comparisons": o["params"]["n_comparisons"],
            "block": BLOCK, "n_boot": N_BOOT, "seed": SEED,
            "uncond_mean_bps": o["uncond_mean"],
            "uncond_ci_lo_bps": o["uncond_ci"][0],
            "uncond_ci_hi_bps": o["uncond_ci"][1],
            "uncond_net_mean_bps": o["uncond_net_mean"],
            "uncond_net_ci_lo_bps": o["uncond_net_ci"][0],
            "uncond_net_ci_hi_bps": o["uncond_net_ci"][1],
        } for o in outs]).to_csv(out_dir / f"{unit}_null.csv", index=False)

        run_meta["units"][unit] = [{
            "series": o["series"], "provenance": o["provenance"],
            "n_main": o["n_main"], "value_col": o["value_col"],
            "null_p95_bps": o["null_p95"],
            "verdict_counts": {k: int(v) for k, v in
                               o["diff_table"]["verdict"].value_counts().items()},
        } for o in outs]

    write_results(results, out_dir)
    (out_dir / "RUN.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
