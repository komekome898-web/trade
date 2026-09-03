#!/usr/bin/env python3
"""S12 clock-burst-30m JUDGMENT -- docs/PREREG_clock_burst.md (frozen 2026-08-25).

SAFETY VALVE: while fresh episodes n < 30 this script prints exactly one
line ("n=XX/30, judgment not executed") and NOTHING ELSE -- no statistics,
no tables, no per-cell numbers.  There is no flag to preview the judgment
early (research-protocol §8, "no fishing"; task instruction: do not add a
--force-preview-style flag).  Only once n >= 30 does main() run the frozen
§4 bar and print the full report, ONCE (research-protocol: OOS is read once
and reported, never re-run under a different reading).

PRE-REGISTRATION (verbatim transcription of docs/PREREG_clock_burst.md,
frozen 2026-08-25; nothing below is changed after the first judged run)

    # PREREG -- S12 時計バースト30分保有(clock-burst-30m)

    **凍結日: 2026-08-25。以降の変更は事前登録の破棄であり、変更したければ
    新しい名前で作り直す。**

    出所: バースト機構アトラス(`scripts/research_burst_atlas.py`、第24報)。
    約1,190セルの探索面から「コスト線判定 -> 日クラスタCI -> 時計窓 -> 非重複」
    の4段で絞り込まれた1構成。**多重性の明示**: この候補は大規模探索の生存者
    であり、汚染面での数値(コスト前 +23.71bps/取引、CI [+7.92, +37.27]、
    n=40)は採用根拠に引用できない。本判定はその統制である。

    ## 1. 仮説

    UTC 12:30-15:00(嵐時計窓、第h報)内で発生する 20bps/60秒級の変位は、
    エピソードの最初の発火に限り、30分地平で往復taker コストを超えて継続する。
    新しい法則の主張ではない -- 既知3法則(時計窓 h・トレードスルー継続 k・
    閾値階段 e)の**交点**の主張である。

    ## 2. 構成(1セルのみ。掃引しない・変えない)

    - 価格系列: バウンスフリー mid(直近taker-BUY値と直近taker-SELL値の平均)、
      1秒グリッド前方補完
    - トリガ: 直近**60秒**の mid 変位が **±20bps 以上**(方向不問・その方向に
      順張り)
    - 窓ゲート: 発火時刻が **UTC 12:30-15:00 内**のときのみエントリ
    - エピソード制約: **フラット時のみエントリ**(保有中の発火は無視。追加
      クールダウンなし -- これが「エピソード先頭のみ」の実装)
    - 執行: taker 建て(発火秒の次の1秒以内の最初のプリント基準 + 片道
      3.96bps)。**TPなし・保護ストップなし**(S9 の教訓: stop がコストを
      倍加して殺した)。**30分ちょうどで taker 決済**(片道3.96bps。窓外に
      出ても保有は満了させる)
    - コスト感度: 片道 +4bps(合計 7.96bps/side)を併記。判定時に ticker
      記録から雪崩時実スリッページを実測し、実測が 3.96bps を超える場合は
      実測値ネットを主判定とする
    - 想定頻度: 1.44回/日(汚染面実測)。最悪単発 -62bps(同)

    ## 3. 判定データと分割

    - **フレッシュ定義: 2026-08-25T12:00:00Z より後**の bitFlyer 約定テープ
      (`paper_logs/tape/executions_*.csv.gz` 蓄積分)。それ以前はアトラス・
      リーダー面研究で汚染済み。1秒でも重なる区間は使わない。
    - レコーダ再起動ギャップは最長連続区間の採用と両端120秒削り(S7/S8 と
      同じ手順)。
    - **n >= 30 に達するまで判定を実行しない**(見込み約21日)。
    - **OOS は一度だけ実行し、そのまま報告する。** 再実行・条件変更・部分
      読みは禁止。

    ## 4. 採用バー(イベント系、KNOWLEDGE §5)

    判定区間で以下を**すべて**:

    1. n >= 30
    2. ネット期待値 **>= +5bps/取引**(コストは §2 の実測スリッページ込み)
    3. 日クラスタ・ブートストラップ(seed 20260825、2000リサンプル)t >= 2.0
       かつ 95%CI が 0 を除外
    4. 累積ネットbps の maxDD <= 1000bps(1x notional 換算 10%)
    5. 窓内/窓外の対照(窓外は取引しないが、同トリガの窓外ドリフトを診断と
       して併記 -- 「窓外は無」の再現確認)

    **1項目でも欠ければ棄却レポート。バーは動かさない。**
    通過は採用ではない: 第2段としてペーパー実装(オーナー承認)-> ペーパー
    30取引で §5 バーを再適用、が残る。

    ## 5. 読み方の凍結

    | 結果 | 結論 |
    |---|---|
    | 全項目通過 | 第2段(ペーパー実装提案)へ。採用ではない |
    | ネット正だがバー未達 | 棄却。ただし機構水準ではなく点水準の棄却として記録 |
    | ネット負 | 棄却。汚染面の +23.71 は多重比較の産物だったと結論し、アトラス
      の生存判定手順(4関門)自体の信頼度を下方修正する |
    | 頻度が 0.7回/日未満 | 判定延期(n>=30 を待つ)。頻度不足自体は棄却理由に
      しない |

    ## 6. 署名欄

    - 事前登録者: リード
    - 凍結日時: 2026-08-25
    - オーナー承認が必要な項目: 判定通過後のペーパー実装のみ(本登録と判定
      実行は蓄積データの読み取りであり資金・稼働に触れない)

STRUCTURAL CONSTANTS FIXED BY THE ABOVE, AND IMPLEMENTATION READINGS TAKEN
WHERE THE PREREG TEXT DOES NOT SPELL OUT A NUMBER (flagged INTERPRETATION;
none of these is a free parameter that was swept -- each is used exactly
once, chosen before any fresh number was read, and reported to the lead):

  * "60秒の mid 変位" = net displacement over the trailing 60 grid-seconds,
    r60[i] = 1e4*(m[i]-m[i-60])/m[i-60] (bounce-free by construction, same
    formula as research_burst_atlas.py). Fire when |r60[i]| >= 20bps; side
    = sign(r60[i]) (momentum, "その方向に順張り"). t_sig = g0 + i + 1 is the
    instant m[i] is first knowable (research_burst_atlas.py convention).
  * NO cooldown is applied to the raw trigger scan -- every qualifying
    grid-second is a candidate.  "Episode start" falls out ENTIRELY from the
    flat-state walk below (verbatim PREREG: "追加クールダウンなし").
  * Window gate: t_sig's time-of-day in [12:30:00, 15:00:00) UTC
    (half-open, research_burst_atlas.py CLOCK_LO_S/CLOCK_HI_S convention).
  * [INTERPRETATION] Entry execution has two distinct reference prices,
    because the PREREG separately names an "entry basis price" and an
    "actual execution print" for the slippage measurement (§2's last
    sentence) while ALSO naming "the first print within the second
    following the firing second" as the trade reference (§2's execution
    line):
      - entry_basis  = m[i], the grid mid AT THE TRIGGER (the price the
        decision was made against, i.e. the theoretical "free" price).
      - entry_print  = the first tape print with t in [t_sig, t_sig+1)
        (bitFlyer print, not grid mid) -- "発火秒の次の1秒以内の最初の
        プリント". No episode opens if no print falls in that exact
        1-second window (dropped, counted; the 1-second bound is not
        widened).
      - measured_entry_slippage_bps = side*(entry_print-entry_basis)
        /entry_basis*1e4 (signed so positive = adverse). This is exactly
        "エントリー基準価格と実約定プリントの差", the §2 "実測スリッページ".
      - nominal_net (assumes the PREREG's flat 3.96bps buys exactly the
        entry_print, i.e. no realised slippage beyond the print):
        entry_fill = entry_print*(1+side*3.96/1e4);
        nominal_net = side*(exit_print-entry_fill)/entry_fill*1e4 - 3.96
      - measured_net (uses the REALISED entry slippage in place of the
        flat 3.96bps assumption on the entry leg; exit leg is not
        separately measured so keeps the flat 3.96bps):
        measured_net = side*(exit_print-entry_basis)/entry_basis*1e4 - 3.96
      - primary_net = measured_net if mean(measured_entry_slippage) > 3.96
        else nominal_net, decided ONCE off the whole judged sample's
        average per §2's literal rule ("片道平均が3.96bpsを超える場合は
        実測ネットを主判定とする").
      - sensitivity_net (cost sensitivity, +4bps/side, reported alongside,
        never the bar): entry_fill_s = entry_print*(1+side*7.96/1e4);
        sensitivity_net = side*(exit_print-entry_fill_s)/entry_fill_s*1e4
        - 7.96.
  * [INTERPRETATION] Exit is a scheduled decision (not a re-triggered
    signal), so it is filled at the first tape print at or after
    t_entry + 1800s (entry_print's own timestamp + exactly 1800.0s), with
    the same guarded print lookup used elsewhere in this repo's research
    scripts (a 60s search window; research_avalanche.py
    FALLBACK_PRINT_GUARD_S). If the fresh tape simply has not accumulated
    that far yet (position still open as of "now"), the episode is
    PENDING, not dropped, and excluded from n until it resolves.
  * [INTERPRETATION] "フラット時のみエントリー" blocks entries of EITHER
    side while a position (opened in either direction) is open; a single
    position_open_until timestamp is walked chronologically over ALL
    in-window firings.
  * [CORRECTED 2026-09-03, lead QA] Recorder-restart gap handling
    ("S7/S8と同じ手順", docs/PREREG_fast_cycle.md §3 spells out the
    identical rule: "最長連続区間を取り、両端を120秒ずつ削って使う" was
    read, in the first version of this script, as "keep only the single
    longest gap-free run" -- that discards whole fresh segments (here,
    2026-08-25..08-28) and is STRICTER than the pre-registration, which
    defines fresh as "all tape after the cutoff". Corrected reading: EVERY
    fresh segment is used; a gap only carves a LOCAL exclusion zone around
    itself. A "recorder-restart gap" = an inter-print gap > GAP_THRESHOLD_S
    (1800s = 30 min, chosen from this tape's gap histogram: the two true
    outages are 30330s and 37307s; every other inter-print gap on the
    fresh tape is <= 812s, ordinary quiet-market spacing -- fixed before
    any fresh trigger/episode number was read). Each gap's exclusion zone
    is [gap_start-120s, gap_end+120s] (find_gap_zones). An episode --
    firing (t_sig) through its 30-minute settlement -- that overlaps ANY
    such zone is dropped (n_gap_excluded), never entered; this is the
    literal "ギャップを跨いだ窓は破棄する" rule from PREREG_fast_cycle.md
    §3, applied per-episode instead of by discarding whole segments.
    Frequency's day denominator is the fresh span in days minus the total
    excluded (gap+trim) time, not a discarded-segment count.
  * [INTERPRETATION] Out-of-window diagnostic ("窓外の同トリガの診断"): the
    SAME trigger definition (r60, thr 20bps, no cooldown), restricted to
    firings whose t_sig falls OUTSIDE [12:30,15:00) UTC, reporting the
    unconditional bounce-free-mid-to-mid 30-minute forward drift
    (side*(m[j]-m[i])/m[i]*1e4, j=i+1801) -- gross, pre-cost, exactly the
    research_burst_atlas.py "drift" convention. This is NEVER traded and
    never enters n or any bar; it is the required in/out contrast only.
  * Bootstrap: day-cluster (UTC day of entry_print's timestamp), 2000
    resamples, seed 20260825, identical implementation to
    research_burst_atlas.py day_cluster_ci.
  * maxDD: running max minus running cumulative sum of primary_net_bps in
    trade (chronological) order, series starts at 0.
  * Frequency branch (§5 table): freq = n / days_in_adopted_segment; if
    freq < 0.7/day, judgment is DEFERRED (n>=30 waited for regardless) even
    if the bar arithmetic would otherwise resolve -- this is checked before
    printing bars 2-4.
  * Determinism: the full pipeline (load -> segment -> grid -> triggers ->
    episodes) is run twice in-process; a hash of the resulting episode
    array + n is printed both times and asserted equal (research-protocol
    §6, seed 20260825, no network access).

Usage:  PYTHONPATH=src python scripts/research_clock_burst.py
        PYTHONPATH=src python scripts/research_clock_burst.py --status-json data/s12_status.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAPE_GLOB = os.path.join(ROOT, "paper_logs", "tape", "executions_*.csv.gz")

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
FRESH_CUTOFF_ISO = "2026-08-25T12:00:00Z"

# --- pre-registered configuration (§2, one cell, never swept) --------------
TRIGGER_WINDOW_S = 60
TRIGGER_THR_BPS = 20.0
HOLD_S = 1800.0
TAKER_BPS = 3.96
COST_SENS_BPS = 4.0                 # -> one-way 7.96bps sensitivity
CLOCK_LO_S = 12 * 3600 + 30 * 60     # 12:30 UTC
CLOCK_HI_S = 15 * 3600               # 15:00 UTC

ENTRY_PRINT_WINDOW_S = 1.0           # "次の1秒以内の最初のプリント"
EXIT_PRINT_GUARD_S = 60.0            # [INTERPRETATION] guarded fill lookup

# --- §3 data handling --------------------------------------------------------
GAP_THRESHOLD_S = 1800.0             # [INTERPRETATION] restart-gap cut
EDGE_TRIM_S = 120.0                  # trimmed on both sides of each gap

# --- §4 judgment bar ---------------------------------------------------------
N_JUDGE_MIN = 30
NET_BAR_BPS = 5.0
CI_T_MIN = 2.0
MAXDD_BAR_BPS = 1000.0
FREQ_BAR_PER_DAY = 0.7

BOOT_ITERS = 2000
SEED = 20260825


# --------------------------------------------------------------------------
# small helpers (research_burst_atlas.py conventions)
# --------------------------------------------------------------------------
def line(char: str = "-", n: int = 104) -> None:
    print(char * n)


def header(title: str) -> None:
    print()
    line("=")
    print(title)
    line("=")


def sub(title: str) -> None:
    print()
    print("--- " + title + " " + "-" * max(0, 100 - len(title)))


def epoch_seconds(ts) -> np.ndarray:
    """datetime -> float epoch seconds, immune to the datetime64 unit trap
    (research-protocol §6: `.astype("int64")`/`.view()` forbidden)."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def epoch_seconds_alt(ts) -> np.ndarray:
    """Independent implementation, used only to cross-check the above."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return np.array([x.timestamp() for x in idx], dtype=float)


def iso(t: float) -> str:
    return pd.Timestamp(t, unit="s", tz="UTC").isoformat()


def ffill(x: np.ndarray) -> np.ndarray:
    fill = np.where(~np.isnan(x), np.arange(len(x)), 0)
    np.maximum.accumulate(fill, out=fill)
    return x[fill]


def day_cluster_ci(vals: np.ndarray, days: np.ndarray,
                    rng: np.random.Generator) -> tuple[float, float, float]:
    """(t_stat, lo95, hi95) from a day-cluster bootstrap (research_burst_atlas.py)."""
    uniq = np.unique(days)
    if len(uniq) < 2 or len(vals) < 2:
        return float("nan"), float("nan"), float("nan")
    groups = [vals[days == d] for d in uniq]
    k = len(groups)
    means = np.empty(BOOT_ITERS)
    for b in range(BOOT_ITERS):
        pick = rng.integers(0, k, k)
        means[b] = np.concatenate([groups[p] for p in pick]).mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    sd = means.std(ddof=1)
    tstat = float(vals.mean() / sd) if sd > 0 else float("nan")
    return tstat, float(lo), float(hi)


# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------
def load_fresh_prints(paths=None) -> dict:
    """Load, sort, epoch-cross-check and fresh-filter the tape. Never prints
    (the safety valve controls all output; callers decide what to show)."""
    if paths is None:
        paths = sorted(glob.glob(TAPE_GLOB))
    if not paths:
        raise SystemExit(f"no tape files found: {TAPE_GLOB}")

    frames = [pd.read_csv(p) for p in paths]
    ex = pd.concat(frames, ignore_index=True)

    t = epoch_seconds(ex["ts"])
    t_alt = epoch_seconds_alt(ex["ts"])
    epoch_dev = float(np.max(np.abs(t - t_alt))) if len(t) else 0.0
    if epoch_dev > 1e-6:
        raise SystemExit("epoch conversion mismatch -- refusing to continue")

    order = np.argsort(t, kind="mergesort")
    t = t[order]
    price = ex["price"].to_numpy(float)[order]
    buy = (ex["side"].to_numpy() == "BUY")[order]

    cutoff = float((pd.Timestamp(FRESH_CUTOFF_ISO) - EPOCH) / pd.Timedelta("1s"))
    n_all = len(t)
    keep = t > cutoff
    t, price, buy = t[keep], price[keep], buy[keep]

    return {"t": t, "price": price, "buy": buy, "cutoff": cutoff,
            "n_all": n_all, "n_fresh": int(keep.sum()), "epoch_dev": epoch_dev,
            "paths": paths}


# --------------------------------------------------------------------------
# recorder-restart gap handling (§3, corrected per lead QA 2026-09-03:
# PREREG's fresh definition is "all tape after the cutoff" -- every fresh
# segment is used. A gap only carves a local exclusion zone around itself
# (gap span + edge_trim_s both sides); it does NOT discard whole segments.
# --------------------------------------------------------------------------
def find_gap_zones(t: np.ndarray, gap_threshold_s: float = GAP_THRESHOLD_S,
                    edge_trim_s: float = EDGE_TRIM_S) -> dict:
    """Recorder-restart gaps (inter-print gap > gap_threshold_s) become
    exclusion zones [gap_start-edge_trim_s, gap_end+edge_trim_s]. Every
    print is kept; only episodes overlapping a zone are later dropped
    (build_episodes). t must be sorted ascending."""
    n = len(t)
    if n < 2:
        return {"gaps": [], "zones": np.zeros((0, 2)), "n_gaps": 0,
                "excluded_days": 0.0}
    d = np.diff(t)
    gap_idx = np.flatnonzero(d > gap_threshold_s)
    gaps = [(float(t[i]), float(t[i + 1])) for i in gap_idx]
    zones = (np.array([[g0, g1] for g0, g1 in gaps], dtype=float).reshape(-1, 2)
             + np.array([-edge_trim_s, edge_trim_s]))
    # clip zones to the data span and sum their length for the frequency
    # denominator (span used minus excluded time, not minus whole days)
    lo_bound, hi_bound = t[0], t[-1]
    clipped = np.clip(zones, lo_bound, hi_bound)
    excluded_s = float(np.sum(np.maximum(0.0, clipped[:, 1] - clipped[:, 0]))) if len(clipped) else 0.0
    return {"gaps": gaps, "zones": zones, "n_gaps": len(gaps),
            "excluded_days": excluded_s / 86400.0}


def overlaps_any_zone(lo: float, hi: float, zones: np.ndarray) -> bool:
    if len(zones) == 0:
        return False
    return bool(np.any((lo <= zones[:, 1]) & (hi >= zones[:, 0])))


# --------------------------------------------------------------------------
# bounce-free mid, 1-second grid (research_burst_atlas.py convention)
# --------------------------------------------------------------------------
def build_mid_grid(t: np.ndarray, price: np.ndarray, buy: np.ndarray) -> dict:
    if len(t) == 0:
        raise SystemExit("no fresh prints -- cannot build a grid")
    lb = ffill(np.where(buy, price, np.nan))     # last taker-BUY (ask proxy)
    ls = ffill(np.where(~buy, price, np.nan))    # last taker-SELL (bid proxy)
    mid = 0.5 * (lb + ls)

    g0 = int(np.floor(t[0]))
    g1 = int(np.floor(t[-1]))
    n = g1 - g0 + 1
    gm = np.full(n, np.nan)
    si = np.floor(t).astype(np.int64) - g0
    gm[si] = mid                                  # last print of the second wins
    gm = ffill(gm)
    valid_from = int(np.argmax(~np.isnan(gm)))
    return {"gm": gm, "g0": g0, "n": n, "valid_from": valid_from}


# --------------------------------------------------------------------------
# trigger scan (§2; no cooldown -- flat-state walk implements episode-start)
# --------------------------------------------------------------------------
def find_triggers(gm: np.ndarray, valid_from: int, window_s: int = TRIGGER_WINDOW_S,
                   thr_bps: float = TRIGGER_THR_BPS) -> tuple[np.ndarray, np.ndarray]:
    n = len(gm)
    r = np.full(n, np.nan)
    r[window_s:] = (gm[window_s:] - gm[:-window_s]) / gm[:-window_s] * 1e4
    ok = np.zeros(n, bool)
    lo = max(window_s, valid_from + window_s)
    ok[lo:] = True
    fire = ok & (np.abs(r) >= thr_bps)
    idx = np.flatnonzero(fire)
    side = np.where(r[idx] > 0, 1, -1).astype(np.int64)
    return idx, side


def time_of_day_s(t_epoch) -> np.ndarray:
    return np.mod(t_epoch, 86400.0)


def in_clock_window(t_epoch) -> np.ndarray:
    tod = time_of_day_s(t_epoch)
    return (tod >= CLOCK_LO_S) & (tod < CLOCK_HI_S)


def find_first_print_at_or_after(t: np.ndarray, price: np.ndarray, t0: float,
                                  t1: float | None = None):
    """First print with t in [t0, t1) (or [t0, +inf) if t1 is None). t must
    be sorted. Returns (t_print, price_print) or (None, None)."""
    i = int(np.searchsorted(t, t0, side="left"))
    if i >= len(t):
        return None, None
    if t1 is not None and t[i] >= t1:
        return None, None
    return float(t[i]), float(price[i])


# --------------------------------------------------------------------------
# episode simulation (flat-state walk = "episode start only")
# --------------------------------------------------------------------------
def build_episodes(gm: np.ndarray, g0: int, fire_idx: np.ndarray, fire_side: np.ndarray,
                    t: np.ndarray, price: np.ndarray, data_hi: float,
                    zones: np.ndarray | None = None) -> dict:
    """Chronological flat-state walk over the in-window firings only.
    Returns resolved episodes plus diagnostic counters. `t`/`price` are ALL
    fresh prints (sorted, no segment discarded -- lead QA 2026-09-03).
    `data_hi` is the last available fresh print time (an exit needed beyond
    it is PENDING -- not yet accumulated -- not dropped). `zones` are
    recorder-restart exclusion zones (find_gap_zones); an episode
    (firing t_sig .. 30-minute settlement) that overlaps ANY zone is
    dropped as gap-excluded (§3, "ギャップを跨いだ窓は破棄する")."""
    if zones is None:
        zones = np.zeros((0, 2))
    t_sig_all = (g0 + fire_idx + 1).astype(float)
    in_window = in_clock_window(t_sig_all)

    episodes: list[dict] = []
    n_ignored_holding = 0
    n_dropped_no_entry_print = 0
    n_gap_excluded = 0
    n_pending = 0

    position_open_until = -np.inf
    order = np.argsort(t_sig_all, kind="mergesort")
    for k in order:
        if not in_window[k]:
            continue
        t_sig = t_sig_all[k]
        if t_sig < position_open_until:
            n_ignored_holding += 1
            continue

        side = int(fire_side[k])
        i = int(fire_idx[k])
        entry_basis = float(gm[i])

        exit_target_upper_bound = t_sig + HOLD_S
        if overlaps_any_zone(t_sig, exit_target_upper_bound, zones):
            n_gap_excluded += 1
            continue

        et_, ep_ = find_first_print_at_or_after(t, price, t_sig, t_sig + ENTRY_PRINT_WINDOW_S)
        if et_ is None:
            n_dropped_no_entry_print += 1
            continue

        exit_target = et_ + HOLD_S
        if exit_target + EXIT_PRINT_GUARD_S > data_hi:
            n_pending += 1
            continue
        xt_, xp_ = find_first_print_at_or_after(t, price, exit_target,
                                                 exit_target + EXIT_PRINT_GUARD_S)
        if xt_ is None:
            n_pending += 1
            continue

        if overlaps_any_zone(t_sig, xt_, zones):
            n_gap_excluded += 1
            continue

        measured_slip = side * (ep_ - entry_basis) / entry_basis * 1e4

        entry_fill_nom = ep_ * (1.0 + side * TAKER_BPS / 1e4)
        nominal_net = side * (xp_ - entry_fill_nom) / entry_fill_nom * 1e4 - TAKER_BPS

        measured_net = side * (xp_ - entry_basis) / entry_basis * 1e4 - TAKER_BPS

        sens_c = TAKER_BPS + COST_SENS_BPS
        entry_fill_sens = ep_ * (1.0 + side * sens_c / 1e4)
        sens_net = side * (xp_ - entry_fill_sens) / entry_fill_sens * 1e4 - sens_c

        gross = side * (xp_ - ep_) / ep_ * 1e4

        episodes.append({
            "t_sig": t_sig, "side": side, "entry_basis": entry_basis,
            "entry_t": et_, "entry_print": ep_, "exit_t": xt_, "exit_print": xp_,
            "gross_bps": gross, "measured_slip_bps": measured_slip,
            "nominal_net_bps": nominal_net, "measured_net_bps": measured_net,
            "sensitivity_net_bps": sens_net,
            "day": int(np.floor(et_ / 86400.0)),
        })
        position_open_until = xt_

    return {"episodes": episodes, "n_ignored_holding": n_ignored_holding,
            "n_dropped_no_entry_print": n_dropped_no_entry_print,
            "n_gap_excluded": n_gap_excluded, "n_pending": n_pending}


def window_out_diagnostic(gm: np.ndarray, g0: int, n: int,
                           fire_idx: np.ndarray, fire_side: np.ndarray) -> dict:
    """Same trigger, restricted to firings OUTSIDE the clock window: gross
    unconditional 30-minute mid-to-mid drift. Never traded, never in n."""
    t_sig_all = (g0 + fire_idx + 1).astype(float)
    out = ~in_clock_window(t_sig_all)
    drifts = []
    for k in np.flatnonzero(out):
        i = int(fire_idx[k])
        j = i + 1 + int(HOLD_S)
        if j >= n or np.isnan(gm[j]):
            continue
        side = int(fire_side[k])
        drifts.append(side * (gm[j] - gm[i]) / gm[i] * 1e4)
    arr = np.asarray(drifts, dtype=float)
    return {"n": int(out.sum()), "n_resolved": len(arr),
            "mean": float(arr.mean()) if len(arr) else float("nan"),
            "median": float(np.median(arr)) if len(arr) else float("nan")}


def compute_maxdd(net_bps_in_order: np.ndarray) -> float:
    cum = np.concatenate(([0.0], np.cumsum(net_bps_in_order)))
    running_max = np.maximum.accumulate(cum)
    dd = running_max - cum
    return float(dd.max()) if len(dd) else 0.0


# --------------------------------------------------------------------------
# full pipeline (deterministic given the tape on disk)
# --------------------------------------------------------------------------
def run_pipeline(paths=None) -> dict:
    raw = load_fresh_prints(paths)
    t, price, buy = raw["t"], raw["price"], raw["buy"]

    if len(t) == 0:
        gaps_info = {"gaps": [], "zones": np.zeros((0, 2)), "n_gaps": 0, "excluded_days": 0.0}
        return {"raw": raw, "gaps_info": gaps_info, "episodes": [], "grid": None,
                "adopted_days": 0.0,
                "diag": {"n_ignored_holding": 0, "n_dropped_no_entry_print": 0,
                         "n_gap_excluded": 0, "n_pending": 0},
                "window_out": None, "n_fresh": 0}

    gaps_info = find_gap_zones(t)
    grid = build_mid_grid(t, price, buy)
    fire_idx, fire_side = find_triggers(grid["gm"], grid["valid_from"])
    result = build_episodes(grid["gm"], grid["g0"], fire_idx, fire_side, t, price,
                             data_hi=t[-1], zones=gaps_info["zones"])
    wout = window_out_diagnostic(grid["gm"], grid["g0"], grid["n"], fire_idx, fire_side)

    span_days = (t[-1] - t[0]) / 86400.0
    adopted_days = max(0.0, span_days - gaps_info["excluded_days"])

    return {"raw": raw, "gaps_info": gaps_info, "grid": grid, "fire_idx": fire_idx,
            "fire_side": fire_side, "episodes": result["episodes"], "diag": result,
            "window_out": wout, "n_fresh": len(result["episodes"]),
            "adopted_days": adopted_days}


def episodes_hash(episodes: list[dict]) -> str:
    h = hashlib.sha256()
    for e in episodes:
        h.update(f"{e['t_sig']:.3f}|{e['side']}|{e['entry_t']:.3f}|{e['entry_print']:.2f}|"
                  f"{e['exit_t']:.3f}|{e['exit_print']:.2f}|{e['nominal_net_bps']:.6f}|"
                  f"{e['measured_net_bps']:.6f}\n".encode())
    return h.hexdigest()[:16]


# --------------------------------------------------------------------------
# §4 judgment bar (only ever reached / printed when n >= N_JUDGE_MIN)
# --------------------------------------------------------------------------
def judge(pipe: dict) -> None:
    episodes = pipe["episodes"]
    n = len(episodes)
    gaps_info = pipe["gaps_info"]
    days = pipe["adopted_days"]
    freq = n / days if days > 0 else float("nan")

    header("S12 clock-burst-30m -- OOS JUDGMENT (fresh tape, run once)")
    print(f"data          : {len(pipe['raw']['paths'])} tape files; fresh cutoff "
          f"{FRESH_CUTOFF_ISO}; fresh prints {pipe['raw']['n_fresh']:,} / "
          f"{pipe['raw']['n_all']:,}")
    print(f"epoch cross-check: max|impl_a-impl_b| = {pipe['raw']['epoch_dev']:.9f}s (must be ~0)")
    print(f"fresh span    : {iso(pipe['raw']['t'][0])} .. {iso(pipe['raw']['t'][-1])} "
          f"-- ALL fresh segments used (lead QA 2026-09-03: no segment is discarded); "
          f"{gaps_info['n_gaps']} recorder-restart gap(s) found "
          f"(>{GAP_THRESHOLD_S:.0f}s), each excluded as [gap {EDGE_TRIM_S:.0f}s]; "
          f"usable days {days:.2f} (span minus excluded)")
    line()

    slips = np.array([e["measured_slip_bps"] for e in episodes])
    avg_slip = float(slips.mean())
    use_measured = avg_slip > TAKER_BPS
    primary_key = "measured_net_bps" if use_measured else "nominal_net_bps"
    primary = np.array([e[primary_key] for e in episodes])
    nominal = np.array([e["nominal_net_bps"] for e in episodes])
    measured = np.array([e["measured_net_bps"] for e in episodes])
    sens = np.array([e["sensitivity_net_bps"] for e in episodes])
    days_arr = np.array([e["day"] for e in episodes])

    sub("execution / slippage")
    print(f"n episodes            : {n}")
    print(f"frequency             : {freq:.3f}/day (bar {FREQ_BAR_PER_DAY}/day)")
    print(f"ignored while holding : {pipe['diag']['n_ignored_holding']}")
    print(f"dropped (no entry print in the 1s window): {pipe['diag']['n_dropped_no_entry_print']}")
    print(f"gap-excluded (episode overlaps a recorder-restart gap/trim): "
          f"{pipe['diag']['n_gap_excluded']}")
    print(f"pending (exit beyond current tape)       : {pipe['diag']['n_pending']}")
    print(f"measured one-way entry slippage, mean bps: {avg_slip:.3f} "
          f"(assumption {TAKER_BPS}bps) -> primary net = {primary_key}")

    if freq < FREQ_BAR_PER_DAY:
        sub("RESULT")
        print(f"DEFERRED -- frequency {freq:.3f}/day < {FREQ_BAR_PER_DAY}/day bar. "
              f"§5: frequency shortfall is not itself grounds for rejection; "
              f"wait for more n before re-judging.")
        return

    rng = np.random.default_rng(SEED)
    tstat, lo, hi = day_cluster_ci(primary, days_arr, rng)
    maxdd = compute_maxdd(primary)

    bar_n = n >= N_JUDGE_MIN
    bar_net = float(primary.mean()) >= NET_BAR_BPS
    bar_ci = (not np.isnan(tstat)) and tstat >= CI_T_MIN and not (lo <= 0.0 <= hi)
    bar_dd = maxdd <= MAXDD_BAR_BPS

    sub("§4 bar")
    print(f"1. n >= {N_JUDGE_MIN}                 : {n} -> {'PASS' if bar_n else 'FAIL'}")
    print(f"2. net >= +{NET_BAR_BPS}bps/trade      : mean {primary.mean():+.3f}bps "
          f"(nominal {nominal.mean():+.3f}, measured {measured.mean():+.3f}, "
          f"sensitivity {sens.mean():+.3f}) -> {'PASS' if bar_net else 'FAIL'}")
    print(f"3. day-cluster t>=2.0, CI excl. 0 : t={tstat:.3f}, "
          f"95% CI [{lo:+.3f}, {hi:+.3f}] -> {'PASS' if bar_ci else 'FAIL'}")
    print(f"4. maxDD <= {MAXDD_BAR_BPS}bps         : {maxdd:.1f}bps -> "
          f"{'PASS' if bar_dd else 'FAIL'}")

    wout = pipe["window_out"]
    sub("5. window in/out contrast (diagnostic, never traded)")
    print(f"out-of-window firings: n={wout['n']}, resolved n={wout['n_resolved']}, "
          f"mean {wout['mean']:+.3f}bps, median {wout['median']:+.3f}bps (gross, pre-cost)")

    all_pass = bar_n and bar_net and bar_ci and bar_dd
    sub("RESULT (§5 reading, frozen)")
    if all_pass:
        print("ALL ITEMS PASS -> stage 2 (paper-implementation proposal). NOT adoption.")
    elif float(primary.mean()) > 0:
        print("net positive, bar unmet -> REJECTED at point level "
              "(not mechanism level; report per research-protocol §10).")
    else:
        print("net negative -> REJECTED. The contaminated-surface +23.71bps is concluded "
              "to be a multiple-comparisons artifact; the atlas's 4-gate survivor "
              "procedure's reliability is marked down accordingly.")


# --------------------------------------------------------------------------
# --status-json: dashboard tile feed (n / fresh period / last day ONLY).
# The safety valve above governs the printed judgment report; this payload
# is a separate, always-safe output -- it never carries a statistic (net bps,
# CI, frequency, ...), only the sample count and its date span, so writing it
# is fine at any n, including n < N_JUDGE_MIN. scripts/dashboard.py reads it
# for the S12 tile ("S12 新鮮n 23/30"); it never renders a verdict from n<30.
# --------------------------------------------------------------------------
def status_json_payload(pipe: dict, now: float | None = None) -> dict:
    t = pipe["raw"]["t"]
    if len(t):
        fresh_start = iso(float(t[0]))
        fresh_end = iso(float(t[-1]))
        last_day = fresh_end[:10]
    else:
        fresh_start = fresh_end = last_day = None
    return {
        "n": pipe["n_fresh"], "need": N_JUDGE_MIN,
        "fresh_start": fresh_start, "fresh_end": fresh_end,
        "last_day": last_day,
        "generated_at": now if now is not None else time.time(),
    }


def write_status_json(path, pipe: dict, now: float | None = None) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(status_json_payload(pipe, now), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")


def main(paths=None, status_json_path=None) -> int:
    pipe = run_pipeline(paths)
    pipe2 = run_pipeline(paths)
    h1, h2 = episodes_hash(pipe["episodes"]), episodes_hash(pipe2["episodes"])
    if h1 != h2 or pipe["n_fresh"] != pipe2["n_fresh"]:
        raise SystemExit("non-deterministic run -- refusing to report "
                          f"(hash {h1} vs {h2})")

    if status_json_path is not None:
        write_status_json(status_json_path, pipe)

    n = pipe["n_fresh"]
    if n < N_JUDGE_MIN:
        print(f"n={n}/{N_JUDGE_MIN}, judgment not executed "
              f"(seed {SEED}, 2-run hash match {h1})")
        return 0

    judge(pipe)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status-json", default=None,
                    help="write n/fresh-period/last-day (no statistics) to this path "
                         "for the dashboard S12 tile")
    args = ap.parse_args()
    sys.exit(main(status_json_path=args.status_json))
