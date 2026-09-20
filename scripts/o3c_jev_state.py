#!/usr/bin/env python3
"""Jev に渡す state を「トレーダーが言う英文の列」で組む道具 + 前半 200 件の下見(2026-09-20)。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §6
委任文: `docs/DATA/delegations/20260920_o3c_signal_jev_state_prompt.md`
手引き: `docs/JEV.md` §2・§4・§7
試作: `docs/DATA/probes/20260920_o3c_jev_state_proto.py`(帯の境界の計算。ここから定数を起こした)

**この道具がすること**
  (a) 帯の境界を**前半だけ**から計算して `config/o3c_jev_state_bands.yaml` に書く(五分位。1 か所の定数)。
  (b) `build_state_sentences(print_id) -> list[str]` = 設計 §6.2 の文の型 13 本(1 件目は
      材料 1・F3 の文(型2)の 1 件目の形だけで、型 3・4・8・9(連鎖の内側の文)を書かない)。
  (c) `build_state_raw(print_id) -> dict` = 前段(`o3c_signal_continue.py`)の
      `jev_state_for_print` から `price_path_bp_last_60s` を除いたもの(V3、生の数)。
  (d) `--stage preview`: 前半 200 件(前段と同じ層化抽出・種)に V1(英文 + criteria)・
      V2(英文、criteria 無し)・V3(生の数)を送り、答えを
      `data/jev/state_preview/answers.jsonl` に記録する(2 件/秒、`jev-1.13.0` 固定)。

**探索段なので判定語を 1 つも書かない。`paper_logs/` は開かない。後半には触れない。**
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

_spec_sc = importlib.util.spec_from_file_location(
    "o3c_signal_continue", _HERE / "o3c_signal_continue.py")
cont = importlib.util.module_from_spec(_spec_sc)
assert _spec_sc.loader is not None
_spec_sc.loader.exec_module(cont)

_spec_mats = importlib.util.spec_from_file_location(
    "o3c_signal_materials", _HERE / "o3c_signal_materials.py")
mats = importlib.util.module_from_spec(_spec_mats)
assert _spec_mats.loader is not None
_spec_mats.loader.exec_module(mats)

REPO_ROOT = _HERE.parent
NAN = float("nan")

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from jev.client import JevClient, JevError  # noqa: E402
from jev.redact import assert_clean  # noqa: E402

# ---------------------------------------------------------------------------
# 固定値(委任文・設計。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
DEFAULT_DATA_ROOT = cont.DEFAULT_DATA_ROOT
DEFAULT_ROWS_PRINTS = cont.DEFAULT_ROWS
DEFAULT_MATERIALS = (REPO_ROOT / "backtest_data" / "o3c_signal_materials_20260920"
                     / "rows_materials.csv.gz")
DEFAULT_CONTINUE_ROWS = (REPO_ROOT / "backtest_data" / "o3c_signal_continue_20260920"
                         / "rows_continue.csv.gz")
BANDS_PATH = REPO_ROOT / "config" / "o3c_jev_state_bands.yaml"
STATE_PREVIEW_DIR = REPO_ROOT / "data" / "jev" / "state_preview"
JEV_MODEL = "jev-1.13.0"
N_PREVIEW = 200
PREVIEW_SEED = 20260920
RATE_PER_SEC = 2.0

REQUIRED_MATERIALS_COLS = ("cand_R1", "cand_F5")

# 帯の五分位を取る量(前半だけ)。proto (`20260920_o3c_jev_state_proto.py`) と同じ量。
QUINTILE_SOURCES = {
    "notional": ("mat3_notional_raw", None),                 # 型1
    "chain_notional": ("cand_F3", "notna"),                   # 型2
    "last10s_notional": ("cand_F5", "positive"),               # 型4
    "oi_ahead_20bp": ("mat8_amt_20bp", "positive_covered"),    # 型11
    "trade_count_60s": ("cand_14", None),                      # 型13
    "vol_ratio_c4": ("cand_C4", None),                         # 型13
    "oi_slope_1h": ("mat10_oi_slope_and_funding", None),       # 型12
}

# --- ts 以前だけの窓(型7・10 の生の bp 値に要る) ---------------------------------
W_60S_MS = 60_000
W_10S_MS = 10_000
W_5S_MS = 5_000
N2_WINDOW_MS = 300_000        # N1・N2(設計 §7.2)の N2。直前 5 分。

# --- V4(設計 §7.1・§7.2。委任文 20260920_o3c_signal_v4_prompt.md 段1) ------------
# N1・N2 を V4 の 1 件目の文に足すかどうか(前半・組 A〈単発 対 多件の最初〉での
# 分かれ方 |分かれ方 − 0.5| ≥ 0.03、`compute_screen_n()` の実測 = `screen_N.csv`)。
# N1(= cand_C3 をそのまま流用): 分かれ方 0.5824(|差| 0.0824)→ 分かれる。
# N2(直前 5 分の値幅の位置): 分かれ方 0.5340(|差| 0.0340)→ 僅差だが分かれる。
N1_SEPARATES = True
N2_SEPARATES = True

# --- この道具が決めた定数(設計に無い判断。§4 に列挙・報告にも書く) -----------------
GAP_RATIO_EPS = 0.15          # 型3「間隔が縮まった/伸びた/変わらない」の判定幅
SIZE_RATIO_EPS = 0.15         # 型3「今回の想定元本が前回より大きい/小さい/同程度」の判定幅
IMBALANCE_TREND_EPS = 0.10    # 型10「押しが強まった/弱まった/変わらない」(proto から)
RECENT_EXTREME_S = 1.0        # 型6「極値の更新から 1 秒以内なら戻りは 0 bp 扱い」(proto から)
PULLBACK_EPS_BP = 0.05        # 型6・8「戻りが 0 とみなす」しきい値
DAY_EXTREME_EPS_BP = 0.05     # 型13「日の極値そのもの」とみなすしきい値

SIZE_BANDS = ["smallest fifth", "second-smallest fifth", "middle fifth",
              "second-largest fifth", "largest fifth"]
ACTIVITY_BANDS = ["quietest fifth", "second-quietest fifth", "middle fifth",
                  "second-busiest fifth", "busiest fifth"]
VOL_BANDS = ["much calmer", "calmer", "similar", "busier", "much busier"]
OI_TREND_BANDS = ["falling fast", "falling", "flat", "rising", "rising fast"]
DAY_EXTREME_BANDS = ["very close to", "close to", "some distance from", "far from"]
TIME_OF_DAY_UTC = {0: "00-06 UTC", 1: "06-12 UTC", 2: "12-18 UTC", 3: "18-24 UTC"}

SIDE_WORDS = {
    "SELL": {"extreme": "low", "prep": "below", "flow": "sells",
             "pos": "fell", "neg": "rose",
             "participle_pos": "fallen", "participle_neg": "risen"},
    "BUY": {"extreme": "high", "prep": "above", "flow": "buys",
            "pos": "rose", "neg": "fell",
            "participle_pos": "risen", "participle_neg": "fallen"},
}

check_no_banned = cont.check_no_banned
BANNED_WORDS = cont.BANNED_WORDS
price_at_or_before = cont.price_at_or_before
range_bp_window = cont.range_bp_window
load_window5 = cont.load_window5


def n2_position(times, prices, ts_ms: int, side: str, p_pre: float) -> float:
    """N2(設計 §7.2)。直前 5 分 `[ts-300000, ts)` の価格レンジの中で p_pre が
    どこにいるか(0 = 清算と逆向きの端、1 = 清算の向きの端)。ts 以前だけ(窓の右端
    `ts` は `searchsorted(..., side="left")` により排他 = 自分自身のプリントの
    約定は含まない、他の窓計算と同じ規則)。"""
    if times is None or times.size == 0 or p_pre is None or not (
            math.isfinite(p_pre) and p_pre > 0):
        return NAN
    lo, hi = ts_ms - N2_WINDOW_MS, ts_ms
    i0 = int(np.searchsorted(times, lo, side="left"))
    i1 = int(np.searchsorted(times, hi, side="left"))
    if i1 <= i0:
        return NAN
    seg = prices[i0:i1]
    seg_hi, seg_lo = float(seg.max()), float(seg.min())
    if seg_hi <= seg_lo:
        return NAN
    s = cont.REACT_SIGN[side]
    liq_end = seg_hi if s > 0 else seg_lo
    opp_end = seg_lo if s > 0 else seg_hi
    return (p_pre - opp_end) / (liq_end - opp_end)


# ===========================================================================
# 1. 帯の境界(前半だけの五分位。定数は 1 か所 = config/o3c_jev_state_bands.yaml)
# ===========================================================================
def _quintile_cuts(values: np.ndarray) -> list:
    v = values[np.isfinite(values)]
    if v.size == 0:
        return [NAN, NAN, NAN, NAN]
    return [float(np.quantile(v, q)) for q in (0.2, 0.4, 0.6, 0.8)]


def _select_subset(df_fh: pd.DataFrame, col: str, mode: str | None) -> np.ndarray:
    v = pd.to_numeric(df_fh[col], errors="coerce").to_numpy(float)
    if mode == "notna":
        v = v[np.isfinite(v)]
    elif mode == "positive":
        v = v[np.isfinite(v) & (v > 0)]
    elif mode == "positive_covered":
        cov = pd.to_numeric(df_fh.get("mat8_covered", 0), errors="coerce").to_numpy(float)
        v = v[np.isfinite(v) & np.isfinite(cov) & (cov > 0) & (v > 0)]
    return v


def compute_bands(df_fh: pd.DataFrame) -> dict:
    """前半 (`half == "前半"`) の行だけから五分位の境界を計算する。"""
    bands: dict = {}
    for key, (col, mode) in QUINTILE_SOURCES.items():
        bands[key] = _quintile_cuts(_select_subset(df_fh, col, mode))
    c3 = pd.to_numeric(df_fh["cand_C3"], errors="coerce").to_numpy(float)
    c3_pos = c3[np.isfinite(c3) & (c3 > DAY_EXTREME_EPS_BP)]
    bands["day_extreme_c3_quartiles"] = (
        [float(np.quantile(c3_pos, q)) for q in (0.25, 0.5, 0.75)]
        if c3_pos.size else [NAN, NAN, NAN])
    return bands


def write_bands_yaml(bands: dict, path: Path = BANDS_PATH) -> None:
    doc = {
        "_由来": ("scripts/o3c_jev_state.py の compute_bands()。前半だけの五分位。"
                "試作 docs/DATA/probes/20260920_o3c_jev_state_proto.py の cuts() と"
                "同じ計算(q=0.2,0.4,0.6,0.8)。C3 だけ 4 分位(q=0.25,0.5,0.75、"
                "日の極値そのものを除いた正の値だけ)"),
        "quintiles": bands,
        "thresholds": {
            "gap_ratio_eps": GAP_RATIO_EPS,
            "size_ratio_eps": SIZE_RATIO_EPS,
            "imbalance_trend_eps": IMBALANCE_TREND_EPS,
            "recent_extreme_s": RECENT_EXTREME_S,
            "pullback_eps_bp": PULLBACK_EPS_BP,
            "day_extreme_eps_bp": DAY_EXTREME_EPS_BP,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))


def load_bands_yaml(path: Path = BANDS_PATH) -> dict:
    doc = yaml.safe_load(path.read_text())
    return doc["quintiles"]


def band5_index(x: float, cuts: list) -> int | None:
    if x is None or not math.isfinite(x) or any(not math.isfinite(c) for c in cuts):
        return None
    return int(np.searchsorted(cuts, x, side="right"))


def band4_index(x: float, cuts: list) -> int | None:
    if x is None or not math.isfinite(x) or any(not math.isfinite(c) for c in cuts):
        return None
    return int(np.searchsorted(cuts[:3], x, side="right"))


# ===========================================================================
# 2. 秒・bp の書式(小さい値は小数 1 桁、大きい値は整数)
# ===========================================================================
def _secs(x: float) -> str:
    return f"{x:.1f}" if abs(x) < 10 else f"{x:.0f}"


def _bp(x: float) -> str:
    return f"{x:.1f}"


def _pct(x: float) -> int | None:
    """[-1, 1] の偏りを 0〜100% に変える(proto と同じ式)。"""
    if x is None or not math.isfinite(x):
        return None
    return int(round((1.0 + x) / 2.0 * 100.0))


# ===========================================================================
# 3. 文の型 1〜13(設計 §6.2 のまま。SELL の例で書き、BUY は側の語だけ入れ替える)
# ===========================================================================
def _sent1(row: dict, bands: dict) -> str:
    side = row["side"]
    idx = band5_index(row.get("mat3_notional_raw"), bands["notional"])
    size = SIZE_BANDS[idx] if idx is not None else "unknown"
    t_idx = row.get("cand_6")
    t_band = (TIME_OF_DAY_UTC.get(int(t_idx)) if t_idx is not None
              and not (isinstance(t_idx, float) and math.isnan(t_idx)) else "unknown")
    return f"{side} liquidation, among the {size} of prints, at {t_band}."


def _sent2_first() -> str:
    return "No same-side liquidation in the last 60 seconds."


def _sent2_nonfirst(row: dict, bands: dict) -> str:
    n = int(row["cand_1"]) + 1
    el = row.get("mat1_elapsed_since_burst_s")
    x = _secs(float(el)) if el is not None and math.isfinite(el) else "unknown"
    idx = band5_index(row.get("cand_F3"), bands["chain_notional"])
    band = SIZE_BANDS[idx] if idx is not None else "unknown"
    return (f"It is the {n}th same-side liquidation of a cascade that began "
            f"{x} seconds ago; the amount liquidated so far is among the "
            f"{band} of cascades.")


def _trend_word(ratio: float, eps: float, hi_word: str, lo_word: str, mid_word: str) -> str:
    if ratio is None or not math.isfinite(ratio) or ratio <= 0:
        return "unknown"
    if ratio > 1 + eps:
        return hi_word
    if ratio < 1 - eps:
        return lo_word
    return mid_word


def _sent3(row: dict, a: float | None, b: float | None) -> str:
    ratio2 = row.get("cand_2")
    ratio3 = row.get("cand_3")
    gap_word = _trend_word(ratio2, GAP_RATIO_EPS, "shorter", "longer", "about the same")
    size_word = _trend_word(ratio3, SIZE_RATIO_EPS, "larger", "smaller", "about the same")
    if a is None:
        return "unknown"
    if b is None:
        return (f"The previous same-side liquidation was {_secs(a)} seconds ago. "
                f"This print is {size_word} than the previous one.")
    return (f"The last two same-side liquidations were {_secs(a)} and {_secs(b)} "
            f"seconds ago; the gaps are {'getting ' + gap_word if gap_word != 'about the same' else gap_word}. This print is "
            f"{size_word} than the previous one.")


def _sent4(row: dict, bands: dict) -> str:
    f5 = row.get("cand_F5")
    if f5 is None or not math.isfinite(f5) or f5 <= 0:
        return "No same-side liquidation in the last 10 seconds."
    idx = band5_index(f5, bands["last10s_notional"])
    band = SIZE_BANDS[idx] if idx is not None else "unknown"
    return (f"Same-side liquidations in the last 10 seconds: among the "
            f"{band} (of prints that had any).")


def _sent5(row: dict, t_opp: float | None) -> str:
    k = row.get("cand_A9_count")
    if k is None or not math.isfinite(k) or int(k) <= 0:
        return "No opposite-side liquidation in the last 60 seconds."
    k = int(k)
    plural = "" if k == 1 else "s"
    if t_opp is None:
        return "unknown"
    return (f"{k} opposite-side liquidation{plural} in the last 60 seconds, "
            f"the last {_secs(t_opp)} seconds ago.")


def _sent6(row: dict) -> str:
    side = row["side"]
    w = SIDE_WORDS[side]
    a6 = row.get("cand_A6")
    if a6 is None or not math.isfinite(a6):
        return "unknown"
    if a6 <= RECENT_EXTREME_S:
        return (f"Price made a new 60-second {w['extreme']} {a6:.1f} seconds ago "
                f"and has not pulled back.")
    r1 = row.get("cand_R1")
    p = max(float(r1), 0.0) if r1 is not None and math.isfinite(r1) else None
    if p is None:
        return f"Price made a new 60-second {w['extreme']} {_secs(a6)} seconds ago."
    if p <= PULLBACK_EPS_BP:
        return (f"Price made a new 60-second {w['extreme']} {_secs(a6)} seconds ago "
                f"and has not pulled back.")
    return (f"Price made a new 60-second {w['extreme']} {_secs(a6)} seconds ago "
            f"and has pulled back {_bp(p)} bp since.")


def _sent7(row: dict, m60: float | None, m10: float | None, r60: float | None) -> str:
    side = row["side"]
    w = SIDE_WORDS[side]
    if m60 is None or m10 is None or r60 is None or not (
            math.isfinite(m60) and math.isfinite(m10) and math.isfinite(r60)):
        return "unknown"
    word60 = w["pos"] if m60 >= 0 else w["neg"]
    word10 = w["pos"] if m10 >= 0 else w["neg"]
    # 符号つきの数は方向が読めない(SELL の +4.6 は「下に 4.6」)。向きは語で書く(リードの直し、2026-09-20)
    return (f"Over the last 60 seconds price {word60} {_bp(abs(m60))} bp "
            f"(range {_bp(r60)} bp); over the last 10 seconds it {word10} {_bp(abs(m10))} bp.")


def _sent8(row: dict) -> str:
    a5 = row.get("cand_A5")
    if a5 is None or not math.isfinite(a5):
        return "unknown"
    return f"Since the previous same-side liquidation, the largest pullback was {_bp(max(a5, 0.0))} bp."


def _sent9(row: dict, m_cascade: float | None) -> str:
    """材料 A3(= 連鎖開始からの値動き ÷ F3)は CSV に 6 桁で丸めて保存されており、
    F3 が数百万〜数千万のときは A3 × F3 で復元すると丸め誤差が bp 単位に増幅される
    (実測: 大きな連鎖で A3 が 0.000000 に丸まり、積が常に 0 bp になった)。
    そのため生の値動き(`m_cascade`、価格の経路から直接計算)を別途渡してもらう
    (設計に無い判断。§4 参照)。"""
    side = row["side"]
    w = SIDE_WORDS[side]
    if m_cascade is None or not math.isfinite(m_cascade):
        return "unknown"
    word = w["participle_pos"] if m_cascade >= 0 else w["participle_neg"]
    return f"Since the cascade began, price has {word} {_bp(abs(m_cascade))} bp."


def _sent10(row: dict, m5: float | None) -> str:
    side = row["side"]
    w = SIDE_WORDS[side]
    mat9, mat13 = row.get("mat9_taker_imbalance_5s"), row.get("mat13_taker_imbalance_trend")
    pct5 = _pct(mat9)
    if pct5 is None or mat13 is None or not math.isfinite(mat13):
        return "unknown"
    pct30 = _pct(mat9 - mat13)
    if mat13 > IMBALANCE_TREND_EPS:
        trend = "more one-sided now"
    elif mat13 < -IMBALANCE_TREND_EPS:
        trend = "less one-sided now"
    else:
        trend = "about the same"
    if m5 is not None and math.isfinite(m5):
        m5_txt = f"Price {w['pos'] if m5 >= 0 else w['neg']} {_bp(abs(m5))} bp in the last 5 seconds."
    else:
        m5_txt = "Price move in the last 5 seconds: unknown."
    pct30_txt = pct30 if pct30 is not None else "unknown"
    return (f"Taker flow in the last 5 seconds: {pct5}% {w['flow']}; over 30 seconds: "
            f"{pct30_txt}% ({trend}). {m5_txt}")


def _sent11(row: dict, bands: dict) -> str:
    side = row["side"]
    w = SIDE_WORDS[side]
    covered = row.get("mat8_covered")
    if covered is None or not math.isfinite(covered) or covered <= 0:
        return f"Open interest {w['prep']} the current price: coverage unknown."
    amt20 = row.get("mat8_amt_20bp")
    amt5 = row.get("mat8_amt_5bp")
    if amt20 is None or not math.isfinite(amt20) or amt20 <= 0:
        oi_part = f"No open interest within 20 bp {w['prep']} the current price"
    else:
        idx = band5_index(amt20, bands["oi_ahead_20bp"])
        band = SIZE_BANDS[idx] if idx is not None else "unknown"
        oi_part = f"Open interest among the {band} within 20 bp {w['prep']} the current price"
    within5 = "some" if (amt5 is not None and math.isfinite(amt5) and amt5 > 0) else "none"
    d = row.get("cand_5p")
    d_part = (f"{abs(float(d)):.0f} bp away" if d is not None and math.isfinite(d)
              else "none within the mapped range")
    return (f"{oi_part}; within 5 bp: {within5} (coverage: yes). "
            f"Nearest liquidation level {w['prep']}: {d_part}.")


def _sent12(row: dict, bands: dict) -> str:
    slope = row.get("mat10_oi_slope_and_funding")
    idx = band5_index(slope, bands["oi_slope_1h"])
    oi_word = OI_TREND_BANDS[idx] if idx is not None else "unknown"
    fr = row.get("mat10_funding_rate")
    if fr is None or not math.isfinite(fr):
        fr_word = "unknown"
    elif fr > 0:
        fr_word = "positive"
    elif fr < 0:
        fr_word = "negative"
    else:
        fr_word = "zero"
    return f"Open interest over the last hour: {oi_word}. Funding: {fr_word}."


def _sent13(row: dict, bands: dict) -> str:
    side = row["side"]
    w = SIDE_WORDS[side]
    c3 = row.get("cand_C3")
    if c3 is None or not math.isfinite(c3):
        day_part = "unknown"
    elif c3 <= DAY_EXTREME_EPS_BP:
        day_part = f"at the day's {w['extreme']}"
    else:
        idx = band4_index(c3, bands["day_extreme_c3_quartiles"])
        word = DAY_EXTREME_BANDS[idx] if idx is not None else "unknown"
        day_part = f"{word} the day's {w['extreme']}"
    c4 = row.get("cand_C4")
    idx4 = band5_index(c4, bands["vol_ratio_c4"])
    vol_word = VOL_BANDS[idx4] if idx4 is not None else "unknown"
    n14 = row.get("cand_14")
    idx14 = band5_index(n14, bands["trade_count_60s"])
    act_word = ACTIVITY_BANDS[idx14] if idx14 is not None else "unknown"
    return (f"Price is {day_part}. Volatility now vs the last hour: {vol_word}. "
            f"Trading activity in the last 60 seconds: among the {act_word}.")


# ===========================================================================
# 3b. V4 だけの文(設計 §7.1 の決定表。1 つの文の型が複数の材料をまとめている場所で
#     材料ごとに「残す」「外す」が分かれた 3 箇所(型3・型6〈連鎖の中〉・型10〈1 件目〉)
#     だけ、外す側の材料を書かない版を別に用意する。他の型は決定表どおり材料が
#     全部「残す」側にまとまっている(または全部「外す」側で型ごと消える)ので、
#     元の型をそのまま使うか、丸ごと呼ばない。
# ===========================================================================
def _sent3_v4(row: dict, a: float | None, b: float | None) -> str:
    """連鎖の中 V4(型3): 間隔の比(材料2、決定表「残して向きを criteria に」)だけを
    使う。想定元本の比(材料3、決定表「外す」)の「larger/smaller than previous」は
    書かない。"""
    ratio2 = row.get("cand_2")
    gap_word = _trend_word(ratio2, GAP_RATIO_EPS, "shorter", "longer", "about the same")
    if a is None:
        return "unknown"
    if b is None:
        return f"The previous same-side liquidation was {_secs(a)} seconds ago."
    return (f"The last two same-side liquidations were {_secs(a)} and {_secs(b)} "
            f"seconds ago; the gaps are "
            f"{'getting ' + gap_word if gap_word != 'about the same' else gap_word}.")


def _sent6_v4(row: dict) -> str:
    """連鎖の中 V4(型6): 極値からの秒数(材料A6、決定表「残す」)だけを使う。
    戻りの大きさ(材料R1、決定表「外す」)の「pulled back / not pulled back」は
    書かない(1 件目は R1 も「残して向きを criteria に」なので元の `_sent6` を使う)。"""
    side = row["side"]
    w = SIDE_WORDS[side]
    a6 = row.get("cand_A6")
    if a6 is None or not math.isfinite(a6):
        return "unknown"
    return f"Price made a new 60-second {w['extreme']} {_secs(a6)} seconds ago."


def _sent10_v4(row: dict, m5: float | None) -> str:
    """1 件目 V4(型10): 成行の偏り 5 秒(材料9、決定表「残して向きを criteria に」)
    だけを使う。30 秒との変化(材料13、決定表「外す」)の「more/less one-sided」は
    書かない(連鎖の中は材料9・13 とも「外す」なので型10 自体を呼ばない)。"""
    side = row["side"]
    w = SIDE_WORDS[side]
    pct5 = _pct(row.get("mat9_taker_imbalance_5s"))
    if pct5 is None:
        return "unknown"
    if m5 is not None and math.isfinite(m5):
        m5_txt = f"Price {w['pos'] if m5 >= 0 else w['neg']} {_bp(abs(m5))} bp in the last 5 seconds."
    else:
        m5_txt = "Price move in the last 5 seconds: unknown."
    return f"Taker flow in the last 5 seconds: {pct5}% {w['flow']}. {m5_txt}"


def _sentN1(row: dict) -> str:
    """N1(設計 §7.2)。C3(その日の極値からの距離)の「距離 0」を言葉にしたもの。
    1 件目だけ(分かれれば V4 の 1 件目の文に足す)。"""
    side = row["side"]
    w = SIDE_WORDS[side]
    c3 = row.get("cand_C3")
    if c3 is None or not math.isfinite(c3):
        return "unknown"
    if c3 <= DAY_EXTREME_EPS_BP:
        return (f"This print is at or beyond a fresh day {w['extreme']}: price is "
                f"entering territory not yet traded today.")
    return f"Price is {_bp(c3)} bp short of a fresh day {w['extreme']}."


def _sentN2(row: dict, pos: float | None) -> str:
    """N2(設計 §7.2)。直前 5 分の値幅の中で今どこにいるか(3 段)。1 件目だけ。"""
    side = row["side"]
    w = SIDE_WORDS[side]
    if pos is None or not math.isfinite(pos):
        return "unknown"
    if pos >= 2.0 / 3.0:
        return f"Within the last 5 minutes, price is near the {w['extreme']} end of the range."
    if pos <= 1.0 / 3.0:
        return (f"Within the last 5 minutes, price is near the opposite end of the "
                f"range from the {w['extreme']}.")
    return "Within the last 5 minutes, price is near the middle of the range."


# ===========================================================================
# 4. 行(print_id)から state を組む
# ===========================================================================
class StateBuilder:
    """行データ・帯・約定を読み込み、`build_state_sentences` / `build_state_raw`
    を print_id だけで呼べるようにする(内部でキャッシュ)。"""

    def __init__(self, materials_path: Path = DEFAULT_MATERIALS,
                continue_path: Path = DEFAULT_CONTINUE_ROWS,
                rows_path: Path = DEFAULT_ROWS_PRINTS,
                data_root: Path = DEFAULT_DATA_ROOT,
                bands: dict | None = None,
                bands_path: Path = BANDS_PATH):
        m = pd.read_csv(materials_path, low_memory=False)
        for c in REQUIRED_MATERIALS_COLS:
            if c not in m.columns:
                raise SystemExit(
                    f"[止め] {materials_path} に {c} が無い(委任文の停止条件)")
        # 材料 1〜15 の生の列(V3・`jev_state_for_print` が要る)+ この道具が文の型に
        # 使う追加の生値(elapsed・notional・OI の bp 別・funding_rate)。
        c_cols = (["print_id"] + [cont.MAT_COL[n] for n in cont.MAT_NUMS]
                 + ["mat1_elapsed_since_burst_s", "mat3_notional_raw",
                    "mat8_amt_5bp", "mat8_amt_20bp", "mat8_covered",
                    "mat10_funding_rate"])
        c = pd.read_csv(continue_path, usecols=c_cols, low_memory=False)
        r = m.merge(c, on="print_id", how="left")
        self.rows = r.set_index("print_id", drop=False)
        self.rows_fh = r[r["half"] == "前半"]
        # 反証者7 D4 の直し: 帯は毎回再計算せず `bands_path`(既定は
        # `config/o3c_jev_state_bands.yaml`)を読む。ファイルが無いときだけ
        # 前半から計算して書く(後半にも同じ帯をそのまま使うため。引数 `bands` を
        # 明示的に渡したとき〈試験など〉はそちらを最優先する)。
        if bands is not None:
            self.bands = bands
        elif bands_path.exists():
            self.bands = load_bands_yaml(bands_path)
        else:
            self.bands = compute_bands(self.rows_fh)
            write_bands_yaml(self.bands, bands_path)

        self.pc = cont.PrintsCSV(rows_path)
        self.nb = cont.same_side_neighbors(self.pc)
        self.idx_of = {pid: i for i, pid in enumerate(self.pc.print_id.tolist())}
        self.all_ts = self.pc.all_ts_sorted()
        o = np.argsort(self.pc.ts, kind="stable")
        self.all_side = self.pc.side[o]
        self.all_notional = self.pc.notional[o]

        self.data_root = data_root
        # 2 つの別のキャッシュ(同じ dict を使い回すと衝突する): `_raw_trade_cache` は
        # `load_window5`(実体は `o3c_signal_explore5.load_window5`)が**単一暦日**
        # ごとに使う内部キャッシュ(1 日ぶんの (times, prices, qtys) を積む)。
        # `_window_cache` はこの道具が「プリントの日」ごとに持つ、逆算窓込みの
        # (times, prices) 1 組。どちらも鍵は暦日の文字列で同じ形をしており、
        # 同じ dict を渡すと後続の呼び出しで型の違う値を取り違えて壊れる
        # (実測: 2 件目以降のプリントで `ValueError: too many values to unpack`)。
        self._raw_trade_cache: dict = {}
        self._window_cache: dict = {}

    # -- 補助: 直前 60 秒の反対側で一番新しいものまでの秒数 -------------------------
    def _last_opposite_ago_s(self, i: int) -> float | None:
        ts = int(self.pc.ts[i])
        side = str(self.pc.side[i])
        lo = np.searchsorted(self.all_ts, ts - cont.SAME_SIDE_WINDOW_MS, side="left")
        hi = np.searchsorted(self.all_ts, ts, side="left")
        if hi <= lo:
            return None
        seg_side = self.all_side[lo:hi]
        seg_ts = self.all_ts[lo:hi]
        mask = seg_side != side
        if not bool(mask.any()):
            return None
        last_ts = int(seg_ts[mask].max())
        return (ts - last_ts) / 1000.0

    # -- 補助: 直前 2 件の同じ側清算までの秒数(型3) -------------------------------
    def _prev_gaps_s(self, i: int) -> tuple[float | None, float | None]:
        prev1_ts = int(self.nb["prev1_ts"][i])
        prev2_ts = int(self.nb["prev2_ts"][i])
        ts = int(self.pc.ts[i])
        a = (ts - prev1_ts) / 1000.0 if prev1_ts >= 0 else None
        b = (ts - prev2_ts) / 1000.0 if prev2_ts >= 0 else None
        return a, b

    # -- 補助: その日の約定(times, prices)を遅延読み込み ---------------------------
    def _trades_for_day(self, day: str):
        if day not in self._window_cache:
            times, prices, _q, _miss, _need = load_window5(
                self.data_root, day, self._raw_trade_cache, 400_000, 0)
            self._window_cache[day] = (times, prices)
        return self._window_cache[day]

    def _bp_moves(self, row: dict, i: int) -> dict:
        """型7・9・10 に要る m60・m10・m5・range60・cascade(生の bp)。ts 以前だけ。

        m60・m10・m5・range60 は `o3c_signal_continue.py: compute_layers` /
        `range_bp_window` と同じ式(`price_at_or_before` を ts 以前だけに使う)。
        cascade(型9)は `o3c_signal_materials.py: compute_new_candidates` の A3 と
        同じ式(`burst_start_ts` の直前の約定 → 今の p_pre)だが、比 ÷ F3 は取らない
        (CSV の 6 桁丸めで大きな F3 のとき精度を失うため。§4 参照)。
        """
        ts = int(row["ts_ms"])
        side = row["side"]
        s = cont.REACT_SIGN[side]
        day = str(row["day"])
        times, prices = self._trades_for_day(day)
        p_pre, _ = price_at_or_before(times, prices, ts - 1)
        out = {"m60": NAN, "m10": NAN, "m5": NAN, "r60": NAN, "cascade": NAN,
               "p_pre": p_pre}
        if not (p_pre == p_pre and p_pre > 0):
            return out
        for key, w_ms in (("m60", W_60S_MS), ("m10", W_10S_MS), ("m5", W_5S_MS)):
            p_w, _ = price_at_or_before(times, prices, ts - w_ms)
            if p_w == p_w and p_w > 0:
                out[key] = s * (p_pre - p_w) / p_w * 1e4
        out["r60"] = range_bp_window(times, prices, ts, p_pre, W_60S_MS)
        burst_start_ts = int(self.nb["burst_start_ts"][i])
        if burst_start_ts >= 0 and burst_start_ts != ts:
            p_start, _ = price_at_or_before(times, prices, burst_start_ts - 1)
            if p_start == p_start and p_start > 0:
                out["cascade"] = s * (p_pre - p_start) / p_start * 1e4
        return out

    def row_dict(self, print_id: str) -> dict:
        r = self.rows.loc[print_id]
        return r.to_dict()

    def build_state_sentences(self, print_id: str) -> list[str]:
        row = self.row_dict(print_id)
        i = self.idx_of[print_id]
        is_first = float(row["cand_1"]) == 0
        sentences = [_sent1(row, self.bands)]
        if is_first:
            sentences.append(_sent2_first())
        else:
            sentences.append(_sent2_nonfirst(row, self.bands))
            a, b = self._prev_gaps_s(i)
            sentences.append(_sent3(row, a, b))
            sentences.append(_sent4(row, self.bands))
        t_opp = self._last_opposite_ago_s(i)
        sentences.append(_sent5(row, t_opp))
        sentences.append(_sent6(row))
        mv = self._bp_moves(row, i)
        sentences.append(_sent7(row, mv["m60"], mv["m10"], mv["r60"]))
        if not is_first:
            sentences.append(_sent8(row))
            sentences.append(_sent9(row, mv["cascade"]))
        sentences.append(_sent10(row, mv["m5"]))
        sentences.append(_sent11(row, self.bands))
        sentences.append(_sent12(row, self.bands))
        sentences.append(_sent13(row, self.bands))
        return sentences

    def build_state_v4(self, print_id: str) -> list[str]:
        """V4(設計 §7.1 の決定表)。位置(1 件目か否か)は `cand_1 == 0` で code が
        決める(委任文【作るもの】1)。1 件目と連鎖の中で別の文の集合を返す。"""
        row = self.row_dict(print_id)
        i = self.idx_of[print_id]
        is_first = float(row["cand_1"]) == 0
        sentences: list[str] = []
        if is_first:
            sentences.append(_sent2_first())
            sentences.append(_sent6(row))                      # A6+R1 とも残す(型そのまま)
            mv = self._bp_moves(row, i)
            sentences.append(_sent7(row, mv["m60"], mv["m10"], mv["r60"]))  # 15+11 とも残す
            sentences.append(_sent10_v4(row, mv["m5"]))         # 9 残す・13 外す
            sentences.append(_sent11(row, self.bands))          # 8+5' 残す(向きは criteria)
            sentences.append(_sent13(row, self.bands))          # 14+C3+C4 とも残す
            if N1_SEPARATES:
                sentences.append(_sentN1(row))
            if N2_SEPARATES:
                pos = n2_position(*self._trades_for_day(str(row["day"])),
                                  int(row["ts_ms"]), row["side"], mv["p_pre"])
                sentences.append(_sentN2(row, pos))
        else:
            sentences.append(_sent2_nonfirst(row, self.bands))   # 1+F3 残す
            a, b = self._prev_gaps_s(i)
            sentences.append(_sent3_v4(row, a, b))                # 2 残す・3(想定元本)外す
            sentences.append(_sent4(row, self.bands))             # F5 残す
            sentences.append(_sent6_v4(row))                      # A6 残す・R1 外す
            mv = self._bp_moves(row, i)
            sentences.append(_sent7(row, mv["m60"], mv["m10"], mv["r60"]))  # 15+11 とも残す
            sentences.append(_sent11(row, self.bands))            # 8+5' 残す(criteria)
            sentences.append(_sent13(row, self.bands))            # 14+C3+C4 残す(C3 は反転)
        return sentences

    def build_state_raw(self, print_id: str) -> dict:
        """V3(前段 `jev_state_for_print` から `price_path_bp_last_60s` を除いたもの)。"""
        row = self.row_dict(print_id)
        day = str(row["day"])
        times, prices = self._trades_for_day(day)
        mat_row = {cont.MAT_COL[n]: row.get(cont.MAT_COL[n]) for n in cont.MAT_NUMS}
        state = cont.jev_state_for_print(print_id, self.pc, self.all_ts, self.all_side,
                                         self.all_notional, times, prices, mat_row)
        del state["price_path_bp_last_60s"]
        return state


# ===========================================================================
# 4b. N1・N2(設計 §7.2)の前半・組 A(単発 対 多件の最初)での分かれ方
# ===========================================================================
SCREEN_N_PATH = (REPO_ROOT / "backtest_data" / "o3c_signal_materials_20260920"
                 / "screen_N.csv")


def compute_screen_n(sb: StateBuilder) -> list[dict]:
    """N1(= cand_C3 をそのまま流用)・N2(n2_position)の前半・組 A だけでの
    分かれ方(`o3c_signal_materials.py: separation_prob`・`screen_rows` と同じ数え
    方。委任文【作るもの】2)。"""
    df_a = sb.rows_fh[sb.rows_fh["group"] == "A"].reset_index(drop=True)
    n1_vals = pd.to_numeric(df_a["cand_C3"], errors="coerce").to_numpy(float)
    n2_vals = np.full(len(df_a), NAN)
    for idx, r in df_a.iterrows():
        day = str(r["day"])
        ts = int(r["ts_ms"])
        side = str(r["side"])
        times, prices = sb._trades_for_day(day)
        p_pre, _ = price_at_or_before(times, prices, ts - 1)
        n2_vals[idx] = n2_position(times, prices, ts, side, p_pre)
    work = pd.DataFrame({"pos_label": df_a["pos_label"].to_numpy(object),
                         "cand_N1": n1_vals, "cand_N2": n2_vals})
    return mats.screen_rows(work, "A", ["N1", "N2"], "単発", "多件の最初")


# ===========================================================================
# 4c. V4 の問い(設計 §7.3。英文はそのまま。1 件目 / 連鎖の中で criteria が別)
# ===========================================================================
_V4_INSTRUCTIONS = ("Will another same-side liquidation print occur within the "
                    "next 60 seconds?")  # 設計 §7.3「1 件目: instructions は同じ」
JEV_QUESTIONS_V4_FIRST = {
    "next_print_within_60s": {
        "type": "noul",
        "instructions": _V4_INSTRUCTIONS,
        "criteria": {
            "yes": ("the tape is busy and volatility has picked up versus the last "
                    "hour; price is at or breaking the day's extreme and has just "
                    "set a fresh extreme; little or no open interest is mapped just "
                    "ahead (price is entering territory where positions have not "
                    "been built); the print is small relative to the recent range"),
            "no": ("a quiet tape, calm volatility, price well inside the day's "
                   "range, a large amount of open interest mapped just ahead, or "
                   "an extremely one-sided last 5 seconds on a quiet tape (an "
                   "isolated forced print)"),
        },
    }
}
JEV_QUESTIONS_V4_CHAIN = {
    "next_print_within_60s": {
        "type": "noul",
        "instructions": _V4_INSTRUCTIONS,
        "criteria": {
            "yes": ("same-side liquidations are coming faster and larger (more in "
                    "the last 10 seconds and in the cascade so far), the tape is "
                    "busy and volatility rising, price keeps setting fresh "
                    "extremes, near the day's extreme, gaps between prints not "
                    "lengthening"),
            "no": ("gaps between prints are lengthening, the last extreme was set "
                   "many seconds ago, price is well inside the day's range, or a "
                   "large amount of open interest sits just ahead"),
        },
    }
}


# ===========================================================================
# 5. 下見(前半 200 件、V1・V2・V3、2 件/秒)
# ===========================================================================
# 設計 §6.3(オーナー承認 L-309)の問い。V1 = 英文の列 + この criteria、V2 = 英文の列だけ(criteria 無し)、
# V3 = 前段の生の数 + 前段の問い(`cont.JEV_QUESTIONS`、比較の基準)。
JEV_QUESTIONS_V1 = {
    "next_print_within_60s": {
        "type": "noul",
        "instructions": ("Will another same-side liquidation print occur within the "
                         "next 60 seconds?"),
        "criteria": {
            "yes": ("there is still open interest or a liquidation level within reach "
                    "of the recent move, and the facts about the new extreme, the "
                    "pullback and the taker flow show the push still going"),
            "no": ("nothing within reach, or the pullback, the taker flow and "
                   "opposite-side liquidations show the other side absorbing the "
                   "forced flow"),
        },
    }
}
JEV_QUESTIONS_V2 = {
    "next_print_within_60s": {k: v for k, v in JEV_QUESTIONS_V1["next_print_within_60s"].items()
                              if k != "criteria"}
}
JEV_QUESTIONS_V3 = cont.JEV_QUESTIONS


def pick_preview_ids(sb: StateBuilder, n_sample: int = N_PREVIEW,
                     seed: int = PREVIEW_SEED) -> tuple[list, dict]:
    """前段 `run_jev_preview` と同じ層化抽出(側 × 材料1 の3群、種 20260920)。"""
    import random
    fh = sb.rows_fh
    mat1 = pd.to_numeric(fh["cand_1"], errors="coerce")
    lo, hi = cont.ex5.tertile_cuts(mat1.to_numpy(float))
    tert = np.where(mat1 <= lo, 1, np.where(mat1 <= hi, 2, 3))
    strata = [(s, t) for s in cont.SIDE_LIST for t in (1, 2, 3)]
    rng = random.Random(seed)
    per = n_sample // len(strata)
    extra = n_sample - per * len(strata)
    picked, strata_n = [], {}
    side_arr = fh["side"].to_numpy(object)
    pid_arr = fh["print_id"].to_numpy(object)
    for k, (s, t) in enumerate(strata):
        pool = pid_arr[(side_arr == s) & (tert == t)].tolist()
        n = per + (1 if k < extra else 0)
        rng.shuffle(pool)
        chosen = pool[:n]
        picked += chosen
        strata_n[f"{s}_{t}"] = len(chosen)
    return picked, strata_n


EXAMPLE_QUOTA = {"単発": 3, "多件の最初": 3, "途中": 2, "多件の最後": 2}  # 委任文【作るもの】4(3)


def _select_examples(picked: list, pos_label_of: dict, sentences_of: dict) -> list:
    """委任文の指定(単発3・多件の最初3・途中2・最後2)どおりに 10 件選ぶ。
    抽出順(`picked` の並び)の中で早く出てきたものを採る。"""
    quota = dict(EXAMPLE_QUOTA)
    out: list = []
    for pid in picked:
        label = pos_label_of.get(pid)
        if quota.get(label, 0) > 0:
            out.append({"print_id": pid, "pos_label": label, "sentences": sentences_of[pid]})
            quota[label] -= 1
        if not any(v > 0 for v in quota.values()):
            break
    return out, quota


def run_preview(sb: StateBuilder, out_dir: Path = STATE_PREVIEW_DIR,
                n_sample: int = N_PREVIEW, rate_per_sec: float = RATE_PER_SEC) -> dict:
    picked, strata_n = pick_preview_ids(sb, n_sample)
    pos_label_of = sb.rows_fh.set_index("print_id")["pos_label"].to_dict()
    out_dir.mkdir(parents=True, exist_ok=True)
    answers_path = out_dir / "answers.jsonl"
    client = JevClient(model=JEV_MODEL, log_dir=str(out_dir / "calls"))
    t_last = 0.0
    n_calls, n_err = 0, 0
    sentences_of: dict = {}
    with answers_path.open("w", encoding="utf-8") as fh_out:
        for pid in picked:
            sentences = sb.build_state_sentences(pid)
            sentences_of[pid] = sentences
            raw = sb.build_state_raw(pid)
            for version, state, questions in (
                    ("V1", sentences, JEV_QUESTIONS_V1),
                    ("V2", sentences, JEV_QUESTIONS_V2),
                    ("V3", raw, JEV_QUESTIONS_V3)):
                # 手引き §4-7: 送る前に伏せ字の検査。ただし V3(生の数)は
                # `jev_state_for_print` が組む固定の鍵(material の変数名。例:
                # "move_since_cascade_start_and_bounce" は 35 字でアンダースコアを
                # 含み、32 文字以上の英数字という「トークンらしさ」の検査に誤爆する)
                # だけの object で、値は数値・固定語彙の文字列(この道具が生成した
                # ものだけ)なので秘密情報が入り得ない。V1・V2(英文の列、値そのものが
                # 自由記述に近い)には検査をかける(設計に無い判断。§4 参照)。
                if version != "V3":
                    state_str = state if isinstance(state, str) else json.dumps(
                        state, ensure_ascii=False, sort_keys=True, default=str)
                    assert_clean(state_str)
                dt = time.time() - t_last
                if dt < 1.0 / rate_per_sec:
                    time.sleep(1.0 / rate_per_sec - dt)
                t_last = time.time()
                n_calls += 1
                rec = {"print_id": pid, "組": version}
                try:
                    resp = client.evaluate(state, questions)
                    usage = resp.get("usage") or {}
                    qid = next(iter(questions))   # 組ごとの問いの鍵(V1/V2: next_print_within_60s、V3: continue)
                    ans = resp.get("answers", {}).get(qid, {})
                    rec["prob"] = ans.get("noul")
                    rec["input_tokens"] = usage.get("input_tokens")
                    rec["model_answered"] = resp.get("model")
                except JevError as e:
                    n_err += 1
                    rec["error"] = str(e)
                fh_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    examples, quota_left = _select_examples(picked, pos_label_of, sentences_of)
    return {"呼び出し数": n_calls, "エラー数": n_err, "対象件数": len(picked),
            "層化の内訳": strata_n, "state の実物": examples,
            "実物の枠で埋まらなかった分(pos_label -> 残り)":
                {k: v for k, v in quota_left.items() if v > 0}}


# ===========================================================================
# 6. V4 の前半の確認(委任文【作るもの】5。1 件目 600 + 連鎖の中 300、V1・V4、
#    1,800 回まで、`keep_alive=True`、2 件/秒)
# ===========================================================================
V4_OUT_DIR = REPO_ROOT / "data" / "jev" / "v4"
V4_PREVIEW_SEED = 20260920
V4_PREVIEW_N_FIRST = 600
V4_PREVIEW_N_CHAIN = 300
V4_PREVIEW_DAY_CAP = 3   # 委任文「日を跨いで偏らないよう 1 日 3 件まで」


def pick_v4_preview_ids(sb: StateBuilder, seed: int = V4_PREVIEW_SEED) -> tuple[dict, dict]:
    """前半から 1 件目 600 + 連鎖の中 300(委任文【作るもの】5)。層化は前段
    (`pick_preview_ids`)と同じ側 × 材料1の3群の切り値を使い、その集団に実在する
    群だけを使う(1 件目は cand_1=0 が常に最小の帯に入るので、実質「側」だけの
    2 群になる)。1 日 3 件まで(**設計に無い判断**: 1件目・連鎖の中それぞれで
    独立に数える。両方合わせて 1 日 3 件にすると 900 件 ÷ 3 = 300 日分が要るが
    前半は 228 日しか無く、達成できないため)。"""
    import random
    fh = sb.rows_fh
    mat1_all = pd.to_numeric(fh["cand_1"], errors="coerce").to_numpy(float)
    lo, hi = cont.ex5.tertile_cuts(mat1_all)   # 前段(pick_preview_ids)と同じ切り値
    rng = random.Random(seed)
    picked: dict = {}
    strata_n: dict = {}
    for pool_name, pool_df, n_sample in (
            ("first", fh[fh["cand_1"] == 0], V4_PREVIEW_N_FIRST),
            ("chain", fh[fh["cand_1"] > 0], V4_PREVIEW_N_CHAIN)):
        mat1 = pd.to_numeric(pool_df["cand_1"], errors="coerce").to_numpy(float)
        tert = np.where(mat1 <= lo, 1, np.where(mat1 <= hi, 2, 3))
        side_arr = pool_df["side"].to_numpy(object)
        pid_arr = pool_df["print_id"].to_numpy(object)
        day_arr = pool_df["day"].to_numpy(object)
        strata = sorted(set(zip(side_arr.tolist(), tert.tolist())))
        per = n_sample // len(strata)
        extra = n_sample - per * len(strata)
        pool_picked: list = []
        day_count: dict = {}
        for k, (s, t) in enumerate(strata):
            mask = (side_arr == s) & (tert == t)
            idxs = np.nonzero(mask)[0].tolist()
            rng.shuffle(idxs)
            target = per + (1 if k < extra else 0)
            got = 0
            for ii in idxs:
                if got >= target:
                    break
                d = day_arr[ii]
                if day_count.get(d, 0) >= V4_PREVIEW_DAY_CAP:
                    continue
                pool_picked.append(pid_arr[ii])
                day_count[d] = day_count.get(d, 0) + 1
                got += 1
            strata_n[f"{pool_name}_{s}_{t}"] = got
        picked[pool_name] = pool_picked
    return picked, strata_n


def run_preview_v4(sb: StateBuilder, out_dir: Path = V4_OUT_DIR,
                   rate_per_sec: float = RATE_PER_SEC) -> dict:
    """V1(基準の全材料+基準 criteria)と V4(決定表で絞った材料+位置別 criteria)
    を同じ印刷(print)に当てる(委任文【作るもの】5)。`keep_alive=True`(L-323)。"""
    picked, strata_n = pick_v4_preview_ids(sb)
    out_dir.mkdir(parents=True, exist_ok=True)
    answers_path = out_dir / "preview_answers.jsonl"
    client = JevClient(model=JEV_MODEL, log_dir=str(out_dir / "calls"), keep_alive=True)
    t_last = 0.0
    n_calls, n_err = 0, 0
    strata_by_pool = {"first": [], "chain": []}
    with answers_path.open("w", encoding="utf-8") as fh_out:
        for pool_name, questions_v4 in (("first", JEV_QUESTIONS_V4_FIRST),
                                        ("chain", JEV_QUESTIONS_V4_CHAIN)):
            for pid in picked[pool_name]:
                sentences_v1 = sb.build_state_sentences(pid)
                sentences_v4 = sb.build_state_v4(pid)
                for version, state, questions in (
                        ("V1", sentences_v1, JEV_QUESTIONS_V1),
                        ("V4", sentences_v4, questions_v4)):
                    state_str = json.dumps(state, ensure_ascii=False, sort_keys=True,
                                           default=str)
                    assert_clean(state_str)
                    dt = time.time() - t_last
                    if dt < 1.0 / rate_per_sec:
                        time.sleep(1.0 / rate_per_sec - dt)
                    t_last = time.time()
                    n_calls += 1
                    rec = {"print_id": pid, "組": f"{pool_name}_{version}"}
                    t0c = time.time()
                    try:
                        resp = client.evaluate(state, questions)
                        rec["latency_s"] = round(time.time() - t0c, 3)
                        usage = resp.get("usage") or {}
                        qid = next(iter(questions))
                        ans = resp.get("answers", {}).get(qid, {})
                        rec["prob"] = ans.get("noul")
                        rec["input_tokens"] = usage.get("input_tokens")
                    except JevError as e:
                        n_err += 1
                        rec["latency_s"] = round(time.time() - t0c, 3)
                        rec["error"] = str(e)
                    fh_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    client.close()
    return {"呼び出し数": n_calls, "エラー数": n_err,
            "対象件数": {k: len(v) for k, v in picked.items()},
            "層化の内訳": strata_n}


# ===========================================================================
# 7. V4 の下見の表(`preview_answers.jsonl` を読むだけ。数値は data/jev/ にだけ置く)
# ===========================================================================
V4_LOGIT_OOF_PATH = V4_OUT_DIR / "logit_oof.json"
BOOT_N = 1000
BOOT_SEED = 20260920


def _bootstrap_sep_se(pos: np.ndarray, neg: np.ndarray, n_boot: int = BOOT_N,
                      seed: int = BOOT_SEED) -> float:
    """`separation_prob` のブートストラップ SE(復元抽出、両側とも)。"""
    if pos.size == 0 or neg.size == 0:
        return NAN
    rng = np.random.default_rng(seed)
    vals = np.empty(n_boot)
    for b in range(n_boot):
        p = rng.choice(pos, size=pos.size, replace=True)
        n = rng.choice(neg, size=neg.size, replace=True)
        vals[b] = mats.separation_prob(p, n)
    return float(np.nanstd(vals))


def _precision_at(prob: np.ndarray, y: np.ndarray, thr: float) -> tuple[float, int]:
    mask = prob >= thr
    n = int(mask.sum())
    if n == 0:
        return NAN, 0
    return float(y[mask].mean()), n


def build_v4_preview_tables(out_dir: Path = V4_OUT_DIR) -> str:
    """`preview_answers.jsonl`(委任文【作るもの】5)を読み、1 件目 / 連鎖の中
    それぞれの V1・V4 の順位分離(ブートストラップ SE つき)・0.05 刻みの分布・
    閾値ごとの適合率・logistic(out-of-fold)との比較・遅延の分位を md にする。"""
    answers_path = out_dir / "preview_answers.jsonl"
    recs = [json.loads(line) for line in answers_path.read_text().splitlines() if line]
    df = pd.DataFrame(recs)
    df[["pool", "version"]] = df["組"].str.split("_", n=1, expand=True)

    cont_df = pd.read_csv(DEFAULT_CONTINUE_ROWS, usecols=["print_id", "label_60"],
                          low_memory=False)
    label_of = cont_df.set_index("print_id")["label_60"].to_dict()
    df["label_60"] = df["print_id"].map(label_of)

    oof = {}
    if V4_LOGIT_OOF_PATH.exists():
        oof = json.loads(V4_LOGIT_OOF_PATH.read_text())
    oof_scene = {"first": oof.get("1件目", {}), "chain": oof.get("連鎖の中", {})}

    lines = ["# V4 前半の下見の表(数値は data/jev/ にだけ置く)", "",
            "委任文: `docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md` 段1",
            "設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §7.5", ""]

    lat = pd.to_numeric(df["latency_s"], errors="coerce").to_numpy(float)
    lat = lat[np.isfinite(lat)]
    lines += ["## 遅延(全呼び出し、p50/p90/p99、秒)", "",
             f"- p50 {np.percentile(lat, 50):.3f} / p90 {np.percentile(lat, 90):.3f} "
             f"/ p99 {np.percentile(lat, 99):.3f}(n={lat.size})", ""]

    for pool in ("first", "chain"):
        pool_label = "1件目" if pool == "first" else "連鎖の中"
        lines.append(f"## {pool_label}")
        lines.append("")
        for version in ("V1", "V4"):
            sub = df[(df["pool"] == pool) & (df["version"] == version)].copy()
            prob = pd.to_numeric(sub["prob"], errors="coerce").to_numpy(float)
            y = pd.to_numeric(sub["label_60"], errors="coerce").to_numpy(float)
            ok = np.isfinite(prob) & np.isfinite(y)
            prob_ok, y_ok = prob[ok], y[ok].astype(int)
            n_err = int((~np.isfinite(prob)).sum())
            sep = (mats.separation_prob(prob_ok[y_ok == 1], prob_ok[y_ok == 0])
                  if prob_ok.size else NAN)
            se = _bootstrap_sep_se(prob_ok[y_ok == 1], prob_ok[y_ok == 0])
            hit05 = (float(((prob_ok >= 0.5).astype(int) == y_ok).mean())
                    if prob_ok.size else NAN)
            bins = np.arange(0, 1.0001, 0.05)
            hist, _ = np.histogram(prob_ok, bins=bins)
            lines += [f"### {version}", "",
                     f"- 件数 {sub.shape[0]}(エラー・欠測 {n_err})",
                     f"- 順位分離(y=label_60) {sep:.4f} ± {se:.4f}(ブートストラップ SE、"
                     f"n_boot={BOOT_N})",
                     f"- 的中(閾値0.5) {hit05:.4f}", "",
                     "0.05 刻みの分布(件数): " + ", ".join(
                         f"[{b:.2f},{b+0.05:.2f})={int(c)}"
                         for b, c in zip(bins[:-1], hist)),
                     "", "| 閾値 | 適合率 | 件数 |", "|---|---|---|"]
            for thr in (0.6, 0.7, 0.8):
                prec, cnt = _precision_at(prob_ok, y_ok, thr)
                prec_s = f"{prec:.4f}" if prec == prec else "NaN"
                lines.append(f"| {thr} | {prec_s} | {cnt} |")
            lines.append("")

        # logistic(out-of-fold)との比較(このプールの前半サンプルに限る)
        oof_map = oof_scene[pool]
        if oof_map:
            sub_v4 = df[(df["pool"] == pool) & (df["version"] == "V4")]
            jev_prob = pd.to_numeric(sub_v4["prob"], errors="coerce").to_numpy(float)
            logit_prob = sub_v4["print_id"].map(oof_map).to_numpy(float)
            y = pd.to_numeric(sub_v4["label_60"], errors="coerce").to_numpy(float)
            ok = np.isfinite(jev_prob) & np.isfinite(logit_prob) & np.isfinite(y)
            if int(ok.sum()) >= 2:
                logit_sep = mats.separation_prob(logit_prob[ok][y[ok] == 1],
                                                  logit_prob[ok][y[ok] == 0])
                corr = float(np.corrcoef(jev_prob[ok], logit_prob[ok])[0, 1])
                lines += ["### logistic(out-of-fold、同じ印刷)との比較", "",
                         f"- logistic の順位分離(このサンプル、n={int(ok.sum())}) "
                         f"{logit_sep:.4f}",
                         f"- Jev(V4)の確率と logistic の相関係数 {corr:.4f}", ""]
    return "\n".join(lines)


# ===========================================================================
# main
# ===========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Jev state(英文の列)を組む道具 + 前半下見")
    ap.add_argument("--materials-path", type=Path, default=DEFAULT_MATERIALS)
    ap.add_argument("--continue-path", type=Path, default=DEFAULT_CONTINUE_ROWS)
    ap.add_argument("--rows-path", type=Path, default=DEFAULT_ROWS_PRINTS)
    ap.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    ap.add_argument("--stage", choices=("bands", "preview", "screen_n", "v4_preview", "all"),
                    default="all")
    ap.add_argument("--n-sample", type=int, default=N_PREVIEW)
    a = ap.parse_args(argv)

    t0 = time.time()
    m_fh_cols = pd.read_csv(a.materials_path, nrows=1).columns
    for c in REQUIRED_MATERIALS_COLS:
        if c not in m_fh_cols:
            raise SystemExit(f"[止め] {a.materials_path} に {c} が無い(委任文の停止条件)")

    sb = StateBuilder(a.materials_path, a.continue_path, a.rows_path, a.data_root)
    write_bands_yaml(sb.bands)
    print(f"帯の境界を書いた -> {BANDS_PATH}", flush=True)
    if a.stage == "bands":
        return 0

    if a.stage == "screen_n":
        rows = compute_screen_n(sb)
        cont.write_csv(SCREEN_N_PATH, rows)
        check_no_banned(SCREEN_N_PATH.read_text(), "screen_N.csv")
        print(f"screen_N を書いた -> {SCREEN_N_PATH}", flush=True)
        return 0

    if a.stage == "v4_preview":
        note = run_preview_v4(sb)
        note["経過秒"] = round(time.time() - t0, 1)
        (V4_OUT_DIR / "preview_notes.json").write_text(
            json.dumps(note, ensure_ascii=False, indent=2))
        print(f"V4 呼び出し {note['呼び出し数']} 件、エラー {note['エラー数']} 件、"
              f"{note['経過秒']}秒 -> {V4_OUT_DIR}", flush=True)
        return 0

    note = run_preview(sb, n_sample=a.n_sample)
    note["経過秒"] = round(time.time() - t0, 1)
    (STATE_PREVIEW_DIR / "preview_notes.json").write_text(
        json.dumps(note, ensure_ascii=False, indent=2))
    print(f"呼び出し {note['呼び出し数']} 件、エラー {note['エラー数']} 件、"
          f"{note['経過秒']}秒 -> {STATE_PREVIEW_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
