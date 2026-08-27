#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 MATILDA TaroCamp v37 -- asymmetric range/break two-mode machine.

EXPLORATION (selection) LEG ONLY.  The window replayed here (2026-08-20..27
fine-grained tape, and the 27-day 1-minute diagnostic that ends where that
tape begins) is already contaminated: reports #26/#27/#29 read execution
calibration, board features and the M2 family out of it.  Its numbers may be
used ONLY to (a) propose at most one frozen cell or (b) declare a feasibility
rejection.  The VERDICT window (>= 2026-08-28T00:00Z) is not touched by a
single byte in this file.

================================================================================
PRE-REGISTRATION -- docs/PREREG_matilda_taro.md, transcribed verbatim
================================================================================

# PREREG - M3 マチルダ TaroCamp v37 現代化(非対称レンジ/ブレイク2モード機)

**凍結日: 2026-08-28。以降の変更は「事前登録の破棄」。** 原典:
`docs/legacy/matilda_for_TaroCamp37.py`(2019/09/04、オーナーが本来意図した系統)。
M2(`PREREG_matilda_modern.md`、v52系5秒スケール)は探索棄却済み(第29報)であり、
本登録はその**未掃引と明記された方向(β≠δ)の実物**を独立に登録するもの。

---

## 0. 位置づけと事前分布

- **M2 の棄却機構は本機に適用されない**: v37 は entry=2.0 / exit=0.8 の**非対称**で、
  利益単位 = (2.0−0.8)×vola40m は設計上コスト床の上に存在する(原典コメント
  「この差分が利益になるからね」)。
- **事前分布は依然負**: レンジモードの芯(移動中心からの乖離フェード・maker建て)は
  アンカー乖離/穏やか+指値(g, j)の棄却族の親戚。M2 の2教訓(時間緩和=takerの別名/
  平均化は集計悪化)は20分緩和・7段グリッドにそのまま掛かる。
- **味方する既知事実**: ブレイクモードの符号反転(レンジ端で順張りへ)は継続則
  (61.4%、k/o/s)と整合する方向。按分TP(在庫が重いほど近くで降りる)は
  M2 で測った「平均化+2.4〜3.5bps/unit」を取りにいく形。
- 検定対象は「**非対称+按分+符号反転という v37 の機械全体**」であり、部品single ではない。

## 1. 現代化の写像(原典 → M3。ここで凍結)

| 原典 v37 | M3 | 根拠 |
|---|---|---|
| 1分足(CryptoWatch) | 1分足(自前: テープ/ticker mid から構成。CW はサービス終了) | データソース死亡 |
| vola=40分の平均|実体|(39本/40のバグ) | **真の平均**(40本/40) | バグ修正 |
| レンジ=40分ヒゲ除去高安(beard=1円→実質実体レンジ) | 40分の**実体極値**と明示(range2=80分も同様) | 事実婚の正式化 |
| エントリ 中心±2.0×vola、グリッド間隔1.0×vola、最大7段(0.01/段) | 同じ(**2.0 / 1.0 / 7 固定**) | 原典の魂 |
| TP 幅 0.8×vola×(sizemin/mybtc)(按分) | 同じ(**0.8 固定、按分維持**)。exit_flg=2 は max/min(中心, 建値∓按分幅) | 同上 |
| 壁(0.1BTC)の2円手前に設置 | **グリッド価格に直接指値**。約定は: 価格が board_top5 内なら queue-realistic(C1相当は不要 — グリッド指値は据置)、top5 より深ければ conservative(厳密突き抜け) | 壁手前は判定棄却(ab)。2円=0.0016bp |
| ブレイク: bid が range_max+width/2 越え(40m極値≠80m極値の鮮度条件+delay=1)で順張りナンピンへ反転、3段までTP抑制、b_signal(出来高つき逆行ヒゲ)2ストライクで全投げ、中心回帰で解除 | **逐語移植**(価格・幅は全て vola/レンジ比で元々スケール不変) | 原典の魂 |
| 時間ラダー: 20分緩和 / 40分成行全投げ、建値が中心より不利なら即緩和 | 同じ構造(水準は族の軸) | |
| SFD±5%(上乖離ショート農業モード) | **廃止**。既存 `sfd_guard_pct`(ベーシス異常で新規停止、対称)に置換 | SFD制度消滅 |
| range_setting=150円 / over=10万円 | **bps化**: 最小 40分レンジ ≥ 10bps(≈原典1.5bpの意図を現代の意味あるガードに引直し)/ 最大 ≥82bps(原典10万円の今日の実効値を保存) | スケール腐敗 |
| スリープ窓・複利・通知 | 廃止(メンテガード・サイジングは既存機構) | 分離の家訓 |
| priprint 二重定義(WHURL_r 未定義) | リプレイでは非該当。記録のみ | |

## 2. 構成ファミリー — **4セル。追加禁止**

固定: 上記写像の全定数(entry 2.0 / exit 0.8 / 間隔1.0 / 7段 / breakexitsize 3 /
b_signal 2ストライク / delay 1)。

| 軸 | 水準 |
|---|---|
| ブレイクモード | **ON(原典)** / **OFF**(レンジモード単独 — 符号反転モジュールの寄与を分離) |
| 時間ラダー (T1, T2) | **(20分, 40分)(原典)** / **(40分, 80分)**(M2 の「緩和=taker」教訓への感度) |

原典セル = ON × (20,40)。**多重性台帳: 本4候補 + M2 の8候補 = 判定窓の累計12候補**
(スプレッドMM対称族を同窓で登録する場合はさらに合算)。

## 3. データと分割

- **探索(選択)**: (a) 主 = 2026-08-20〜27 の ticker+executions+board_top5(汚染済み、
  細粒度リプレイ)。(b) 診断 = 31日テープ(7/23〜8/20、汚染済み)上の1分足近似リプレイ
  (約定は conservative 近似)— 40分スケールの独立エピソード数を補う**参考値**であり
  選択には (a) のみを使う。
- **判定**: 2026-08-28T00:00Z 以降の板データが実効 **14板日**に達した時点で一度だけ
  (M2 と同一窓、9/11頃)。早見禁止。バーンイン・ギャップ規律は第26報実装を逐語再利用。

## 4. 選択規則(凍結)

1. 足切り: 細粒度探索で 往復 ≥50 かつ ネット(unit bps)> 0。0セルなら
   **フィージビリティ棄却・判定不消費**(診断(b)が正でも規則は覆らない — その場合は
   乖離を報告し棄却水準を「点水準」に留める)。
2. 日次クラスタ t 最大のセルを1つ。台地条件(各軸の隣接水準が50%未満に劣化しない)。
3. 凍結は最大1セル。

## 5. 判定基準(再監査系クラス、KNOWLEDGE §5)

判定区間で: 往復 **≥100** かつ ネット **≥ +2bps/unit** かつ 日次クラスタ **t ≥ 2.0**
(CI が0を除外)かつ maxDD **≤ 1000 unit-bps**(累積)。
通過時は **2段目 = ペーパー14日**(同一基準、オーナー承認制)。1段目通過は採用ではない。

## 6. 必須報告

1. 全4セル表(往復・往復/日・unit bps・日次クラスタt/CI・maxDD・在庫分布・出口内訳)
2. **モード別分解**: レンジモード損益 vs ブレイクモード損益(符号反転は稼いだか)・
   ブレイク発生頻度・b_signal 撤退の economics・breakexitsize の「走らせた勝ち」の実測
3. **非対称の検証**: 利益単位(実現した往復幅)の分布 vs 設計値 1.2×vola、
   按分TPの在庫段別効果(M2 §2.3 との比較)
4. 逆選択の反実仮想・時間ラダーのバケット経済(M2 の「緩和=taker」が本機でも成るか)
5. 診断(b): 27日1分足近似の同4セル(参考、選択不可と明記)
6. サニティ: ルックアヘッド0・在庫≤7段/建玉整合 assert・決定性・ギャップ規律・
   再現ゲート(ブレイクOFF×原典ラダーのレンジ部が M2 のレンジ機構と整合的に比較可能なこと)
7. 多重性(累計12候補)と偶然期待

## 7. 結果の読み方(先に決める)

| 結果 | 結論 |
|---|---|
| 探索全セル負 | フィージビリティ棄却(§10 で機構/点水準を書き分け)。判定不消費 |
| 判定通過 | ペーパー14日へ(オーナー承認)。採用ではない |
| 判定1項目欠け | 棄却。バー不動 |
| ブレイクON>OFF が明確 | 符号反転モジュールの寄与として §2 継続則に接続して記録 |
| 探索勝者≠判定勝者 | 過学習兆候として不採用 |

## 8. オーナー承認が必要な項目

1. 本4セル族と選択規則の凍結
2. 判定窓の共有(M2 と同一、累計12候補)
3. 1段目通過時のペーパー投入(その時点で再確認)

署名: リード(M3設計)。凍結日時: 2026-08-28。
実装: `scripts/research_matilda_taro.py`(本文書を docstring に逐語、第26報実装を再利用、
seed 20260828)。

================================================================================
IMPLEMENTATION RESOLUTIONS -- fixed before the first run, never tuned after
================================================================================
The PREREG fixes the mechanism; a state machine needs statements the prose
leaves implicit.  Each resolution below is settled toward the LITERAL v37
source (docs/legacy/matilda_for_TaroCamp37.py) except where the PREREG §1
mapping replaces it, and each is written so a reader can audit it.

R1  SUBSTRATE (a).  ticker_*.csv.gz (event best bid/ask + sizes),
    executions_*.csv.gz (taker side, price, size) and board_top5_*.csv.gz
    (1 Hz five-deep ladder).  Unlike M2, M3 places its grid AWAY from the
    touch, so depth is a load-bearing observable and board_top5 is consumed.
    board_top5 stops at 2026-08-26T19:01:55Z while the ticker runs to 08-27
    11:57Z; board silence > GAP_SEC is therefore treated as a recorder gap
    exactly like ticker silence (union of the two gap sets), so every fill in
    the primary run is resolved by ONE fill model.  Cost: ~17 h of tape.

R2  CLOCKS.  Indicator state (vola, range, range2, centre, break prices,
    b_signal, expantion_flg) advances ONLY on COMPLETED 1-minute bars, as in
    v37 (get_candle runs once a minute).  At decision second s the newest bar
    used is the one ending at or before floor(s/60)*60, i.e. bar index
    floor(s/60)-1; no look-ahead.  Order placement / exit management run on a
    1 s decision grid (v37's loop is 0.6 s).  The exit price in force during
    (s-1, s] is the one computed at the end of second s-1.  Fills inside a
    second are processed in true print-timestamp order.

R3  BARS.  1-minute bars on the absolute epoch grid, built from the ticker
    mid with the imported research_board_calibration.build_bars mechanism
    (bar length overridden to 60 s).  open/close = first/last mid of the bar;
    an empty bar is a flat bar at the previous close.  Vol = sum of execution
    sizes in the bar.  topbeard / underbeard are the RAW wick lengths of v37
    (computed per candleSign before clipping); High/Low are then replaced by
    the BODY extremes max(open,close) / min(open,close), which is the PREREG
    §1 formalisation of v37's beard_ignore = 1 JPY.

R4  INDICATORS.  vola = TRUE mean of |body| over the last 40 COMPLETED bars
    (PREREG bug fix; v37 summed 39 and divided by 40), floored at 1 JPY.
    vol_ave = mean of Vol over the same 40 bars (the same 39/40 slip is
    repaired the same way; the PREREG names only vola, and the choice is
    stated here rather than hidden).  range_max/min = body extremes over 40
    bars, range_max2/min2 over 80, range_width = max-min, range_center =
    round((max+min)/2).  expantion_flg follows v37's get_candle branch
    verbatim, comparing the NEW bar against the PREVIOUS bar's range values.

R5  BREAK PRICES.  break_up_price = range_max + range_width/2 is APPENDED to
    its list only when (range_max != range_max2 or break_flg != 0) -- v37's
    freshness condition; likewise down.  break_delay = 1 means the effective
    level is the last appended value, floored/capped by range_max2/range_min2
    exactly as v37's pripara/break_judge compute it.  The lists start at
    9999999 / 0, so no break can fire before the first append.  break_judge
    compares against the TOUCH (best bid for up, best ask for down).

R6  SIDE AND ENTRY GATE (range mode).  last = the ticker mid at the decision
    second.  entry_flg = -1 when last > centre + 2.0*vola, +1 when last <
    centre - 2.0*vola, else 0; and 0 whenever the 40-minute range is outside
    [10, 82] bps of the mid (PREREG's bps-ification of range_setting /
    over_range_setting).  The SFD branch is deleted (PREREG).  No sleep
    window.

R7  ENTRY PLACEMENT.  v37 walks the book from the touch outward to the first
    level larger than bigvol and quotes 2 JPY in front of it, subject to
    price < last_placed_price - 1.0*vola and obc < order_count.  The PREREG
    deletes the wall (report #27/ab) and quotes the GRID PRICE directly, so
    the walk collapses to: the first price at or worse than the touch that
    satisfies every registered constraint --
        BUY : price = floor(min(best_bid, [centre - 2*vola if range mode],
                                 anchor - 1.0*vola))   (strictly < anchor-step)
        SELL: price = ceil (max(best_ask, [centre + 2*vola if range mode],
                                 anchor + 1.0*vola))
    where anchor is v37's buy_status/sell_status price: +/-inf after a cancel,
    the average entry price when a position exists and the counter is 0
    (v37 seeds obc with mybtc//sizemin there), else the last placed price.
    In BREAK mode there is no centre band (v37 sets entry_flg = break_flg
    regardless of centre) -- only the grid spacing applies.  One order per
    decision second (v37 places one per loop), 1 unit = 0.01 BTC each, at most
    7 placements per cycle and at most 7 units of inventory.
    Entry orders REST until filled or cancelled (v37 never re-quotes them);
    there is no 10 s lifetime and no C1 cancel clock -- that is the M2 entry
    model, not this one.

R8  CANCELS.  v37's run loop cancels ALL child orders when
        entry_flg == 1 and osc != 0 and mybtc == 0,
        entry_flg == -1 and obc != 0 and mybtc == 0,
        entry_flg == 0 and (obc != 0 or (osc != 0 and mybtc == 0)),
    and whenever posside changes to 'None'.  The third line is transcribed
    with Python's real precedence, i.e. with the operator-precedence asymmetry
    the 2019 source actually has (a resting SELL grid survives entry_flg == 0
    while short, a resting BUY grid does not while long).  It is reproduced
    because the PREREG mapping does not list it as a repair; a symmetric-
    cancel SENSITIVITY is run and reported so the asymmetry is visible and
    cannot silently drive the answer.  A cancel voids the resting exit too
    (v37 cancels everything); the exit is re-placed the same second at
    whatever price the exit rule then gives, losing its queue position.

R9  EXIT PRICE (v37 order_exit, PREREG §1).  exit_vola = 0.8 * vola *
    (sizemin / mybtc) = 0.8*vola/k -- the apportioned TP.  With entry_price
    the average entry and k the inventory in units:
      exit_flg == 1: the first board-side price beyond the target, i.e.
        long  : P = ceil (max(best_ask, entry_price + exit_vola))
        short : P = floor(min(best_bid, entry_price - exit_vola))
        (v37 scans the book outward for the first level past the target; with
        the wall deleted that is the tick just past it, or the touch when the
        touch is already past it.)
      exit_flg == 2: long  P = min(centre, entry_price + exit_vola)
                     short P = max(centre, entry_price - exit_vola)   (v37).
      exit_flg == 3: taker, whole inventory, at mid -/+ TAKER_BPS.
      exit_flg == 0: NO resting exit (break-mode TP suppression).  v37 merely
        skips order_exit, leaving a stale order resting; the PREREG §1 and the
        v37 changelog both state the mechanism as "no TP order until
        breakexitsize", so suppression is implemented as suppression.  This is
        the one place where documented intent is preferred to the literal
        control flow, and it is the mechanism the PREREG registers.
    P is rounded to the 1 JPY tick and recomputed every decision second; any
    change is a requote and resets the queue.

R10 FILL MODEL (a).  Every resting order is resolved against the tape:
      * "arrival" = the first 1 Hz board snapshot at which our price is within
        the visible five-deep ladder on our side (bid: P >= bid_px_5;
        ask: P <= ask_px_5).  Q = the size shown AT P if P is one of the five
        prices, else 0 (P sits in a hole in the ladder, so nothing is ahead of
        us).  Arrival is evaluated at the END of each second, using a snapshot
        at or before that second, and applies to prints strictly after it.
      * after arrival we fill when the cumulative at-or-through volume of
        opposite-side prints since arrival reaches Q (queue-realistic);
      * at any time, arrived or not, a print strictly THROUGH P fills us
        (conservative -- this is the only channel for a price deeper than the
        visible ladder).
    Maker fills print at P exactly, zero fee.  A requote resets arrival, Q and
    the accumulated volume (queue position is lost), which is conservative.

R11 MARKETABLE REQUOTE = TAKER (inherited from M2 R7b, report #29 §2.2).  A
    limit order SUBMITTED at a price already through the market does not rest;
    it executes immediately as a taker.  So any exit requote whose new price
    is marketable (long: P <= best bid; short: P >= best ask) closes the
    inventory at once at mid -/+ TAKER_BPS = 3.96 bps (the repo's frozen 激動
    one-way cost, 1.96 half-spread + 2.0 slippage).  An ALREADY RESTING order
    is never re-tested this way.  The naive alternative (marketable requote
    filled at its own price) is reported as a sensitivity, not as primary.
    This is the channel through which v37's exit_flg == 2 "throw the position
    away" (b_signal strike, or an entry worse than the centre) becomes taker.

R12 GAP DISCIPLINE.  GAP_SEC = 30 s, imported.  Gaps = ticker silence UNION
    board silence (R1).  A decision second is unusable if its board state is
    stale, if it falls in a gap, or if the 80-bar (range2) indicator window
    ending at its newest completed bar touches a gap.  A cycle open when an
    unusable second arrives is DISCARDED WHOLE (every fill of it is excluded
    from every economic statistic) and counted; so is a cycle still open at
    the end of the record.  The machine's break state resets on a discard.

R13 P&L CONVENTION.  1 unit = 0.01 BTC = 1x notional.  Per-unit return in bps
    is signed toward the position.  A cycle holding k units contributes the
    SUM of its k per-unit returns, so a 7-rung cycle carries up to 7x notional
    -- daily totals, the cumulative curve and maxDD are all on this notional-
    weighted basis.  The per-round-trip mean and the mean per unit are both
    reported so the readings cannot be confused.  Funding (0.06 %/day) is not
    charged: it is reported as a note against the realised holding times.

R14 STATISTICS.  Day-clustered bootstrap of the mean per-unit bps (imported
    boot_ci, UTC-day clusters, 2000 draws, seed 20260828) gives the cluster t
    and 95 % CI.  maxDD = largest peak-to-trough drop of the cumulative
    per-unit bps curve ordered by exit time.  Effective board-days = usable
    decision seconds / 86400.

R15 DIAGNOSTIC (b).  The same state machine on 1-minute OHLC bars built from
    backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz restricted to
    exec_date < 2026-08-20T08:22:17Z (so it cannot overlap the primary tape).
    Decisions are taken at the OPEN of bar i on the indicators of the COMPLETED
    bar i-1, which is the only alignment that lets a break fire at all: v37
    compares the LIVE touch against a range window that does not contain it,
    and bar i-1's own close is inside bar i-1's range by construction.
    No book: last = best_bid = best_ask = the bar open.  Orders then rest
    through bar i and fill only when the bar's RAW high/low STRICTLY penetrates
    their price (conservative on the queue, generous on participation); taker
    exits price at the decision open -/+ TAKER_BPS.  Within a bar the resting
    exit is resolved before entries, and a bar that closes the cycle cancels
    that bar's entry fills -- a convention that favours the strategy, stated so
    it is not mistaken for a measurement.  Placement may add several rungs in
    one bar (a bar is 60 of v37's decision cycles).  Gaps = >= 5 minutes
    without a print.  (b) IS A PARTICIPATION-INFLATED APPROXIMATION AND IS
    NEVER USED FOR SELECTION (PREREG §3).

Offline only -- reads files, opens no sockets, places no orders.  Read-only,
idempotent, deterministic.  seed 20260828, no network.

Usage: PYTHONPATH=src python scripts/research_matilda_taro.py
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import research_board_calibration as cal  # noqa: E402  (structural reuse)

SEED = 20260828

# ---- frozen constants (PREREG §1/§2) ---------------------------------------
ENTRY_MULT = 2.0        # entry_setting
STEP_MULT = 1.0         # step_setting  (grid spacing)
EXIT_MULT = 0.8         # step_exit     (apportioned TP)
MAX_RUNGS = 7           # pos_count / order_count
BREAKEXITSIZE = 3
BREAK_DELAY = 1
VOLA_COUNT = 40         # minutes
RANGE_COUNT = 40        # minutes  (range2 = 80)
RANGE_MIN_BPS = 10.0
RANGE_MAX_BPS = 82.0
TICK = 1.0
UNIT_BTC = 0.01
TAKER_BPS = 3.96
BAR_SEC = 60
GAP_SEC = cal.GAP_SEC   # 30 s
MARKOUT = 5.0
MARKOUT2 = 60.0
INF = float("inf")

CELLS = [(brk, T1, T2)
         for brk in (True, False)
         for (T1, T2) in ((20.0, 40.0), (40.0, 80.0))]

# exit kinds
K_TP, K_RELAX, K_T2, K_FLIP, K_BDUMP = 0, 1, 2, 3, 4
KIND_NAMES = ("TP", "relaxed", "forced-T2", "forced-flip", "break-dump")


def header(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def sub(t):
    print("\n--- " + t + " " + "-" * max(0, 72 - len(t)))


def fmt(x, w=8, p=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return " " * max(0, w - 3) + "n/a"
    return f"{x:>{w}.{p}f}"


def cellname(c):
    brk, T1, T2 = c
    return f"break={'ON ' if brk else 'OFF'} T=({T1:.0f},{T2:.0f})"


# ===========================================================================
# data
# ===========================================================================
def build_bars(t, mid, sec):
    """cal.build_bars with the bar length overridden (R3)."""
    old = cal.VR_BAR_SEC
    cal.VR_BAR_SEC = sec
    try:
        return cal.build_bars(t, mid)
    finally:
        cal.VR_BAR_SEC = old


def merge_gaps(gs_list, ge_list):
    if not gs_list:
        return np.array([], float), np.array([], float)
    gs = np.concatenate(gs_list)
    ge = np.concatenate(ge_list)
    o = np.argsort(gs, kind="stable")
    gs, ge = gs[o], ge[o]
    out_s, out_e = [], []
    cs, ce = gs[0], ge[0]
    for a, b in zip(gs[1:], ge[1:]):
        if a <= ce:
            ce = max(ce, b)
        else:
            out_s.append(cs); out_e.append(ce)
            cs, ce = a, b
    out_s.append(cs); out_e.append(ce)
    return np.array(out_s, float), np.array(out_e, float)


class Market:
    pass


def load_board(data_dir: Path):
    paths = sorted(data_dir.glob("board_top5_*.csv.gz"))
    if not paths:
        raise SystemExit(f"no board_top5 files under {data_dir}")
    bd = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    t = cal.epoch_seconds(bd["ts"])
    o = np.argsort(t, kind="stable")
    bd = bd.iloc[o].reset_index(drop=True)
    t = t[o]
    bpx = bd[[f"bid_px_{i}" for i in range(1, 6)]].to_numpy(float)
    bsz = bd[[f"bid_sz_{i}" for i in range(1, 6)]].to_numpy(float)
    apx = bd[[f"ask_px_{i}" for i in range(1, 6)]].to_numpy(float)
    asz = bd[[f"ask_sz_{i}" for i in range(1, 6)]].to_numpy(float)
    ok = np.isfinite(bpx).all(1) & np.isfinite(apx).all(1)
    print(f"board_top5 rows     : {len(t):,} snapshots kept "
          f"({int((~ok).sum())} dropped for missing levels), "
          f"{pd.Timestamp(t[0], unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(t[-1], unit='s', tz='UTC')}")
    return t[ok], bpx[ok], bsz[ok], apx[ok], asz[ok]


def build_market(data_dir: Path) -> Market:
    (t_tk, bid, ask, bsz, asz, mid, spread_bps,
     t_ex, px, sz, buy, span_days) = cal.load(data_dir)
    gs_tk, ge_tk = cal.find_gaps(t_tk, t_ex)
    t_bd, bpx, bbz, apx, abz = load_board(data_dir)

    d = np.diff(t_bd)
    kk = np.flatnonzero(d > GAP_SEC)
    gs_bd, ge_bd = t_bd[kk], t_bd[kk + 1]
    print(f"board gaps          : {len(gs_bd)} intervals of depth silence "
          f"> {GAP_SEC:.0f}s, {(ge_bd - gs_bd).sum() / 3600:.2f} h")

    t_end = min(t_tk[-1], t_bd[-1])
    t_start = max(t_tk[0], t_bd[0])
    # everything after the depth record stops is a gap (R1)
    gs_all, ge_all = merge_gaps(
        [gs_tk, gs_bd, np.array([t_end], float)],
        [ge_tk, ge_bd, np.array([t_tk[-1] + 1.0], float)])
    print(f"union gaps          : {len(gs_all)} intervals, "
          f"{(np.minimum(ge_all, t_tk[-1]) - gs_all).sum() / 3600:.2f} h "
          f"(ticker U depth; the tape past "
          f"{pd.Timestamp(t_end, unit='s', tz='UTC')} carries no depth and "
          f"is dropped whole)")

    m = Market()
    m.t_tk, m.bid, m.ask, m.mid = t_tk, bid, ask, mid
    m.bsz_t, m.asz_t = bsz, asz
    m.t_ex, m.px, m.sz, m.buy = t_ex, px, sz, buy
    m.t_bd, m.bpx, m.bbz, m.apx, m.abz = t_bd, bpx, bbz, apx, abz
    m.bpx5 = bpx[:, 4].tolist()
    m.apx5 = apx[:, 4].tolist()
    m.gs, m.ge = gs_all, ge_all
    m.span_days = span_days
    m.t_start, m.t_end = t_start, t_end

    # ---- 1-minute bars -----------------------------------------------------
    b0, nb, opn, high, low, close, empty = build_bars(t_tk, mid, BAR_SEC)
    bar_start = (np.arange(nb) + b0) * float(BAR_SEC)
    vol = np.zeros(nb)
    vidx = np.floor(t_ex / BAR_SEC).astype(np.int64) - b0
    inside = (vidx >= 0) & (vidx < nb)
    np.add.at(vol, vidx[inside], sz[inside])

    body = close - opn
    candlelen = np.abs(body)
    sign = np.sign(body)
    topbeard = np.where(sign > 0, high - close, high - opn)
    underbeard = np.where(sign > 0, opn - low, close - low)
    hi_b = np.maximum(opn, close)          # body extremes (PREREG §1)
    lo_b = np.minimum(opn, close)

    def roll(a, w, fn):
        out = np.full(len(a), np.nan)
        if len(a) >= w:
            sw = np.lib.stride_tricks.sliding_window_view(a, w)
            out[w - 1:] = fn(sw)
        return out

    vola = roll(candlelen, VOLA_COUNT, lambda s: s.mean(axis=1))
    vola = np.maximum(vola, TICK)
    vol_ave = roll(vol, VOLA_COUNT, lambda s: s.mean(axis=1))
    rmax = roll(hi_b, RANGE_COUNT, lambda s: s.max(axis=1))
    rmin = roll(lo_b, RANGE_COUNT, lambda s: s.min(axis=1))
    rmax2 = roll(hi_b, RANGE_COUNT * 2, lambda s: s.max(axis=1))
    rmin2 = roll(lo_b, RANGE_COUNT * 2, lambda s: s.min(axis=1))
    rwidth = rmax - rmin
    rcentre = np.round((rmax + rmin) / 2.0)

    # expantion_flg -- v37 get_candle, comparing against the PREVIOUS bar's
    # range values (R4).  Break-independent, so precomputed once.
    expan = np.zeros(nb, int)
    e = 0
    pmax, pmin, pcen = 0.0, 9999999.0, 0.0
    for i in range(nb):
        if hi_b[i] > pmax:
            e += 1
        elif lo_b[i] < pmin:
            e -= 1
        elif (e >= 1 and lo_b[i] < pcen) or (e <= -1 and hi_b[i] > pcen):
            e = 0
        expan[i] = e
        if np.isfinite(rmax[i]):
            pmax, pmin, pcen = rmax[i], rmin[i], rcentre[i]

    win_lo = bar_start - (RANGE_COUNT * 2 - 1) * BAR_SEC
    win_hi = bar_start + BAR_SEC
    bar_ok = ~cal.span_touches_gap(win_lo, win_hi, gs_all, ge_all)
    fin = np.isfinite(rmin2) & np.isfinite(vol_ave)
    bar_ok &= fin
    bar_ok1 = (~cal.span_touches_gap(bar_start, win_hi, gs_all, ge_all)) & fin

    m.b0, m.nb = b0, nb
    m.bar = dict(opn=opn, close=close, vol=vol, candlelen=candlelen,
                 sign=sign, topbeard=topbeard, underbeard=underbeard,
                 vola=vola, vol_ave=vol_ave, rmax=rmax, rmin=rmin,
                 rmax2=rmax2, rmin2=rmin2, rwidth=rwidth, rcentre=rcentre,
                 expan=expan, ok=bar_ok, ok1=bar_ok1)
    print(f"1-minute bars       : {nb:,} bars, {100 * empty.mean():.1f}% with "
          f"no quote change, {100 * bar_ok.mean():.1f}% carry a gap-free "
          f"80-bar window")
    return m


def build_seconds(m: Market) -> Market:
    t0 = math.ceil(m.t_start)
    t1 = math.floor(m.t_end)
    secs = np.arange(t0, t1 + 1, 1.0)
    ip = np.searchsorted(m.t_tk, secs, "right") - 1
    ib = np.searchsorted(m.t_bd, secs, "right") - 1
    ok = (ip >= 0) & (ib >= 0)
    secs, ip, ib = secs[ok], ip[ok], ib[ok]

    stale = ((secs - m.t_tk[ip]) > GAP_SEC) | ((secs - m.t_bd[ib]) > GAP_SEC)
    ingap = cal.span_touches_gap(secs, secs, m.gs, m.ge)
    jb = np.floor(secs / BAR_SEC).astype(np.int64) - m.b0 - 1
    jb_ok = (jb >= 0) & (jb < m.nb)
    jbc = np.clip(jb, 0, m.nb - 1)
    barok = jb_ok & m.bar["ok"][jbc]
    usable = (~stale) & (~ingap) & barok
    # sensitivity mask: only the NEWEST completed bar must be gap-free, so the
    # 40/80-bar windows may span a recorder outage (indicators are then built
    # on forward-filled flat bars, which biases vola DOWN -- reported, never
    # used for selection).
    usable_relaxed = (~stale) & (~ingap) & jb_ok & m.bar["ok1"][jbc]

    m.secs = secs
    m.ip, m.ib, m.jb = ip, ib, jbc
    m.s_bid = m.bid[ip]
    m.s_ask = m.ask[ip]
    m.s_mid = m.mid[ip]
    m.s_usable = usable
    m.s_usable_relaxed = usable_relaxed
    m.eff_days_relaxed = float(usable_relaxed.sum()) / 86400.0
    m.ex_lo = np.searchsorted(m.t_ex, secs - 1.0, "right")
    m.ex_hi = np.searchsorted(m.t_ex, secs, "right")
    m.s_day = np.floor(secs / 86400.0).astype(np.int64)
    m.eff_days = float(usable.sum()) / 86400.0
    days, cnt = np.unique(m.s_day[usable], return_counts=True)
    m.usable_days = days
    m.usable_secs_per_day = cnt
    print(f"decision grid       : {len(secs):,} seconds, "
          f"{int(usable.sum()):,} usable = {m.eff_days:.3f} effective "
          f"board-days over {len(days)} UTC days")
    print("                      dropped: "
          f"{int(stale.sum()):,} stale / {int(ingap.sum()):,} in-gap / "
          f"{int((~barok).sum()):,} without a gap-free 80-bar window")
    print(f"                      relaxed-gap sensitivity mask would keep "
          f"{int(usable_relaxed.sum()):,} s = "
          f"{m.eff_days_relaxed:.3f} board-days (NOT used for selection)")
    return m


# ===========================================================================
# the state machine (a) -- fine-grained replay
# ===========================================================================
class Order:
    __slots__ = ("price", "is_bid", "t0", "arrived", "Q", "cum", "rung",
                 "mode", "idx")

    def __init__(self, price, is_bid, t0, rung, mode, idx):
        self.price = price
        self.is_bid = is_bid
        self.t0 = t0
        self.arrived = False
        self.Q = 0.0
        self.cum = 0.0
        self.rung = rung
        self.mode = mode          # 0 range, 1 break
        self.idx = idx


class Res:
    pass


def run_cell(m: Market, brk_on: bool, T1m: float, T2m: float,
             naive_requote: bool = False, symmetric_cancel: bool = False,
             breakexit: int = BREAKEXITSIZE,
             relaxed_gaps: bool = False) -> Res:
    T1 = T1m * 60.0
    T2 = T2m * 60.0
    secs = m.secs.tolist()
    usable = (m.s_usable_relaxed if relaxed_gaps else m.s_usable).tolist()
    s_bid = m.s_bid.tolist(); s_ask = m.s_ask.tolist(); s_mid = m.s_mid.tolist()
    ex_lo = m.ex_lo.tolist(); ex_hi = m.ex_hi.tolist()
    t_ex = m.t_ex.tolist(); e_px = m.px.tolist()
    e_sz = m.sz.tolist(); e_buy = m.buy.tolist()
    jb = m.jb.tolist(); ib = m.ib.tolist()
    B = {k: (v.tolist() if isinstance(v, np.ndarray) else v)
         for k, v in m.bar.items()}
    bpx, bbz, apx, abz = m.bpx, m.bbz, m.apx, m.abz
    bpx5, apx5 = m.bpx5, m.apx5

    # placement-level records
    p_t0, p_px, p_side, p_mode, p_rung, p_fill = [], [], [], [], [], []
    # fill-level records
    f_t, f_px, f_side, f_rung, f_mode = [], [], [], [], []
    # cycle-level records
    c_t0, c_tx, c_k, c_mode, c_ever, c_kind, c_taker = [], [], [], [], [], [], []
    c_pnl, c_avg, c_xpx, c_side, c_vola, c_supp = [], [], [], [], [], []
    # unit-level records
    u_bps, u_day, u_tx, u_rung, u_kind, u_k, u_mode = [], [], [], [], [], [], []

    inv_px: list[float] = []
    inv_rung: list[int] = []
    side = 0
    t_first = INF
    avg = 0.0
    orders: list[Order] = []
    xo: Order | None = None          # resting exit
    xkind = K_TP
    anchor_b, anchor_s = INF, -INF
    n_b = n_s = 0
    break_flg = 0
    b_signal = 0
    bup_last, bdn_last = 9999999.0, 0.0
    last_bar = -1
    cyc_mode = 0
    cyc_ever = False
    cyc_supp = False
    cyc_vola = np.nan

    n_break_up = n_break_dn = n_break_off = 0
    n_discard_cyc = n_discard_units = 0
    n_marketable = 0
    n_supp_seconds = 0
    units_opened = units_closed = 0
    max_inv = 0
    break_seconds = 0

    def retire(o: Order, filled: bool):
        p_fill[o.idx] = 1 if filled else 0

    def cancel_all():
        nonlocal orders, xo, anchor_b, anchor_s, n_b, n_s
        for o in orders:
            retire(o, False)
        orders = []
        xo = None
        anchor_b, anchor_s = INF, -INF
        n_b = n_s = 0

    def close_cycle(t, xpx, kind, taker):
        nonlocal side, t_first, inv_px, inv_rung, avg, units_closed
        nonlocal cyc_ever, cyc_supp, cyc_mode, cyc_vola
        k = len(inv_px)
        tot = 0.0
        day = int(math.floor(t / 86400.0))
        for e, rg in zip(inv_px, inv_rung):
            b = side * (xpx - e) / e * 1e4
            tot += b
            u_bps.append(b); u_day.append(day); u_tx.append(t)
            u_rung.append(rg); u_kind.append(kind); u_k.append(k)
            u_mode.append(cyc_mode)
        c_t0.append(t_first); c_tx.append(t); c_k.append(k)
        c_mode.append(cyc_mode); c_ever.append(1 if cyc_ever else 0)
        c_kind.append(kind); c_taker.append(1 if taker else 0)
        c_pnl.append(tot); c_avg.append(avg); c_xpx.append(xpx)
        c_side.append(side); c_vola.append(cyc_vola)
        c_supp.append(1 if cyc_supp else 0)
        units_closed += k
        inv_px = []; inv_rung = []
        side = 0
        t_first = INF
        avg = 0.0
        cyc_ever = False
        cyc_supp = False
        cancel_all()

    def discard_cycle():
        nonlocal side, t_first, inv_px, inv_rung, avg, units_opened
        nonlocal n_discard_cyc, n_discard_units, cyc_ever, cyc_supp
        n_discard_cyc += 1
        n_discard_units += len(inv_px)
        units_opened -= len(inv_px)
        inv_px = []; inv_rung = []
        side = 0
        t_first = INF
        avg = 0.0
        cyc_ever = False
        cyc_supp = False

    n = len(secs)
    for i in range(n):
        s = secs[i]
        if not usable[i]:
            if side != 0:
                discard_cycle()
            cancel_all()
            break_flg = 0
            b_signal = 0
            bup_last, bdn_last = 9999999.0, 0.0
            last_bar = -1
            continue

        # ---------------- 1. fills from prints in (s-1, s] -----------------
        lo = ex_lo[i]; hi = ex_hi[i]
        if hi > lo and (orders or xo is not None):
            for kk in range(lo, hi):
                if not orders and xo is None:
                    break
                p = e_px[kk]
                tb = e_buy[kk]
                z = e_sz[kk]
                tv = t_ex[kk]
                # --- exit first is impossible to collide with an entry: an
                # exit sits on the side opposite to the inventory, and one
                # print has one taker side.
                if xo is not None:
                    hit = False
                    if xo.is_bid and not tb:
                        if p < xo.price:
                            hit = True
                        elif p <= xo.price and xo.arrived:
                            xo.cum += z
                            hit = xo.cum >= xo.Q
                    elif (not xo.is_bid) and tb:
                        if p > xo.price:
                            hit = True
                        elif p >= xo.price and xo.arrived:
                            xo.cum += z
                            hit = xo.cum >= xo.Q
                    if hit:
                        close_cycle(tv, xo.price, xkind, False)
                        continue
                if orders:
                    done = None
                    for o in orders:
                        if o.is_bid and not tb:
                            if p < o.price:
                                done = o
                            elif p <= o.price and o.arrived:
                                o.cum += z
                                if o.cum >= o.Q:
                                    done = o
                        elif (not o.is_bid) and tb:
                            if p > o.price:
                                done = o
                            elif p >= o.price and o.arrived:
                                o.cum += z
                                if o.cum >= o.Q:
                                    done = o
                        if done is not None:
                            break
                    if done is not None:
                        o = done
                        orders.remove(o)
                        retire(o, True)
                        osd = 1 if o.is_bid else -1
                        assert side == 0 or side == osd, \
                            "opposite-side fill -- one-sided invariant broken"
                        if side == 0:
                            side = osd
                            t_first = tv
                            cyc_mode = o.mode
                            cyc_ever = (o.mode == 1)
                            cyc_vola = B["vola"][jb[i]]
                        if o.mode == 1:
                            cyc_ever = True
                        inv_px.append(o.price)
                        inv_rung.append(o.rung)
                        avg = sum(inv_px) / len(inv_px)
                        units_opened += 1
                        max_inv = max(max_inv, len(inv_px))
                        assert len(inv_px) <= MAX_RUNGS, "inventory cap"
                        f_t.append(tv); f_px.append(o.price)
                        f_side.append(osd); f_rung.append(o.rung)
                        f_mode.append(o.mode)
                        xo = None            # possize changed -> requote

        j = jb[i]
        # ---------------- 2. bar update -----------------------------------
        if j != last_bar:
            last_bar = j
            if B["rmax"][j] != B["rmax2"][j] or break_flg != 0:
                bup_last = B["rmax"][j] + B["rwidth"][j] / 2.0
            if B["rmin"][j] != B["rmin2"][j] or break_flg != 0:
                bdn_last = B["rmin"][j] - B["rwidth"][j] / 2.0
            if B["vol"][j] > B["vol_ave"][j] and break_flg != 0:
                tbd = B["topbeard"][j]
                ubd = B["underbeard"][j]
                cl = B["candlelen"][j]
                sg = B["sign"][j]
                if tbd > ubd and tbd > cl:
                    if break_flg == 1 and b_signal >= 0:
                        b_signal -= 1
                    elif break_flg == -1:
                        b_signal = -1
                elif ubd > tbd and ubd > cl:
                    if break_flg == -1 and b_signal <= 0:
                        b_signal += 1
                    elif break_flg == 1:
                        b_signal = 1
                elif sg < 0:
                    if break_flg == 1 and b_signal >= 0:
                        b_signal -= 1
                    elif break_flg == -1:
                        b_signal = -1
                elif sg > 0:
                    if break_flg == -1 and b_signal <= 0:
                        b_signal += 1
                    elif break_flg == 1:
                        b_signal = 1
            elif b_signal != 0 and B["expan"][j] == 0:
                b_signal = 0

        centre = B["rcentre"][j]
        vola = B["vola"][j]
        rw = B["rwidth"][j]
        rmax2 = B["rmax2"][j]
        rmin2 = B["rmin2"][j]
        bb = s_bid[i]; ba = s_ask[i]; last = s_mid[i]

        # ---------------- 3. break_judge (inside ently_judge) --------------
        if brk_on:
            bup = bup_last if bup_last > rmax2 else rmax2
            bdn = bdn_last if bdn_last < rmin2 else rmin2
            if bup < bb and break_flg != 1 and b_signal != -1:
                break_flg = 1
                n_break_up += 1
            elif bdn > ba and break_flg != -1 and b_signal != 1:
                break_flg = -1
                n_break_dn += 1
        if break_flg != 0:
            break_seconds += 1

        # ---------------- 4. ently_judge ----------------------------------
        if break_flg == 0:
            rw_bps = rw / last * 1e4
            if rw_bps < RANGE_MIN_BPS or rw_bps > RANGE_MAX_BPS:
                e_flg = 0
            elif last > centre + ENTRY_MULT * vola:
                e_flg = -1
            elif last < centre - ENTRY_MULT * vola:
                e_flg = 1
            else:
                e_flg = 0
        else:
            if break_flg == -b_signal or (b_signal == 0 and side == 0):
                e_flg = 0
            else:
                e_flg = break_flg

        k = len(inv_px)
        # ---------------- 5. entry order management ------------------------
        if e_flg == 1:
            if n_s != 0 and k == 0:
                cancel_all()
            # order_buy
            if k < MAX_RUNGS:
                if side > 0 and n_b == 0:
                    anchor_b = avg
                    n_b += k
                if n_b < MAX_RUNGS:
                    cap = bb
                    if break_flg == 0:
                        cap = min(cap, centre - ENTRY_MULT * vola)
                    cap = min(cap, anchor_b - STEP_MULT * vola - 1e-9)
                    price = math.floor(cap)
                    if price > 0 and price < anchor_b - STEP_MULT * vola:
                        o = Order(float(price), True, s, n_b,
                                  1 if break_flg != 0 else 0, len(p_t0))
                        p_t0.append(s); p_px.append(float(price))
                        p_side.append(1); p_mode.append(o.mode)
                        p_rung.append(n_b); p_fill.append(0)
                        orders.append(o)
                        n_b += 1
                        anchor_b = float(price)
        elif e_flg == -1:
            if n_b != 0 and k == 0:
                cancel_all()
            if k < MAX_RUNGS:
                if side < 0 and n_s == 0:
                    anchor_s = avg
                    n_s += k
                if n_s < MAX_RUNGS:
                    cap = ba
                    if break_flg == 0:
                        cap = max(cap, centre + ENTRY_MULT * vola)
                    cap = max(cap, anchor_s + STEP_MULT * vola + 1e-9)
                    price = math.ceil(cap)
                    if price > anchor_s + STEP_MULT * vola:
                        o = Order(float(price), False, s, n_s,
                                  1 if break_flg != 0 else 0, len(p_t0))
                        p_t0.append(s); p_px.append(float(price))
                        p_side.append(-1); p_mode.append(o.mode)
                        p_rung.append(n_s); p_fill.append(0)
                        orders.append(o)
                        n_s += 1
                        anchor_s = float(price)
        else:
            if symmetric_cancel:
                trigger = (n_b != 0 or n_s != 0) and k == 0
            else:
                trigger = (n_b != 0) or (n_s != 0 and k == 0)   # R8, literal
            if trigger:
                cancel_all()

        # ---------------- 6. exit management ------------------------------
        k = len(inv_px)
        if k >= 1:
            if break_flg == 0:
                if side < 0:
                    if e_flg == 1:
                        x, xk = 3, K_FLIP
                    elif (s - t_first) > T2:
                        x, xk = 3, K_T2
                    elif (s - t_first) > T1 or avg < centre:
                        x, xk = 2, K_RELAX
                    else:
                        x, xk = 1, K_TP
                else:
                    if e_flg == -1:
                        x, xk = 3, K_FLIP
                    elif (s - t_first) > T2:
                        x, xk = 3, K_T2
                    elif (s - t_first) > T1 or avg > centre:
                        x, xk = 2, K_RELAX
                    else:
                        x, xk = 1, K_TP
            else:
                if (side > 0 and e_flg == -1) or (side < 0 and e_flg == 1):
                    x, xk = 3, K_FLIP
                elif b_signal == 0:
                    x, xk = 1, K_TP
                elif break_flg == -b_signal:
                    x, xk = 2, K_BDUMP
                elif k >= breakexit:
                    x, xk = 1, K_TP
                else:
                    x, xk = 0, K_TP

            if x == 3:
                xpx = last * (1.0 - side * TAKER_BPS / 1e4)
                close_cycle(s, xpx, xk, True)
            elif x == 0:
                cyc_supp = True
                n_supp_seconds += 1
                xo = None
            else:
                ev = EXIT_MULT * vola * (1.0 / k)
                if x == 1:
                    if side > 0:
                        P = float(math.ceil(max(ba, avg + ev + 1e-9)))
                    else:
                        P = float(math.floor(min(bb, avg - ev - 1e-9)))
                else:
                    if side > 0:
                        P = float(round(min(centre, avg + ev)))
                    else:
                        P = float(round(max(centre, avg - ev)))
                if xo is not None and xo.price == P:
                    xkind = xk
                else:
                    marketable = (P <= bb) if side > 0 else (P >= ba)
                    if marketable and not naive_requote:
                        n_marketable += 1
                        xpx = last * (1.0 - side * TAKER_BPS / 1e4)
                        close_cycle(s, xpx, xk, True)
                    elif marketable and naive_requote:
                        close_cycle(s, P, xk, False)
                    else:
                        xo = Order(P, side < 0, s, -1, 0, -1)
                        xkind = xk

        # ---------------- 7. break_off_judge ------------------------------
        if break_flg == 1 and last < centre:
            break_flg = 0
            b_signal = 0
            n_break_off += 1
        elif break_flg == -1 and last > centre:
            break_flg = 0
            b_signal = 0
            n_break_off += 1

        # ---------------- 8. queue arrival (end of second, R10) -----------
        if orders or xo is not None:
            q = ib[i]
            pb5 = bpx5[q]; pa5 = apx5[q]
            for o in orders:
                if o.arrived:
                    continue
                if o.is_bid:
                    if o.price >= pb5:
                        o.arrived = True
                        o.Q = 0.0
                        row = bpx[q]
                        for zz in range(5):
                            if row[zz] == o.price:
                                o.Q = float(bbz[q, zz])
                                break
                        o.cum = 0.0
                else:
                    if o.price <= pa5:
                        o.arrived = True
                        o.Q = 0.0
                        row = apx[q]
                        for zz in range(5):
                            if row[zz] == o.price:
                                o.Q = float(abz[q, zz])
                                break
                        o.cum = 0.0
            o = xo
            if o is not None and not o.arrived:
                if o.is_bid:
                    if o.price >= pb5:
                        o.arrived = True
                        o.Q = 0.0
                        row = bpx[q]
                        for zz in range(5):
                            if row[zz] == o.price:
                                o.Q = float(bbz[q, zz])
                                break
                        o.cum = 0.0
                else:
                    if o.price <= pa5:
                        o.arrived = True
                        o.Q = 0.0
                        row = apx[q]
                        for zz in range(5):
                            if row[zz] == o.price:
                                o.Q = float(abz[q, zz])
                                break
                        o.cum = 0.0

    if side != 0:
        discard_cycle()
    cancel_all()

    r = Res()
    r.cell = (brk_on, T1m, T2m)
    r.p_t0 = np.array(p_t0, float); r.p_px = np.array(p_px, float)
    r.p_side = np.array(p_side, float); r.p_mode = np.array(p_mode, int)
    r.p_rung = np.array(p_rung, int); r.p_fill = np.array(p_fill, bool)
    r.f_t = np.array(f_t, float); r.f_px = np.array(f_px, float)
    r.f_side = np.array(f_side, float); r.f_rung = np.array(f_rung, int)
    r.f_mode = np.array(f_mode, int)
    r.c_t0 = np.array(c_t0, float); r.c_tx = np.array(c_tx, float)
    r.c_k = np.array(c_k, int); r.c_mode = np.array(c_mode, int)
    r.c_ever = np.array(c_ever, int); r.c_kind = np.array(c_kind, int)
    r.c_taker = np.array(c_taker, int); r.c_pnl = np.array(c_pnl, float)
    r.c_avg = np.array(c_avg, float); r.c_xpx = np.array(c_xpx, float)
    r.c_side = np.array(c_side, float); r.c_vola = np.array(c_vola, float)
    r.c_supp = np.array(c_supp, int)
    r.u_bps = np.array(u_bps, float); r.u_day = np.array(u_day, int)
    r.u_tx = np.array(u_tx, float); r.u_rung = np.array(u_rung, int)
    r.u_kind = np.array(u_kind, int); r.u_k = np.array(u_k, int)
    r.u_mode = np.array(u_mode, int)
    r.n_break_up, r.n_break_dn, r.n_break_off = n_break_up, n_break_dn, n_break_off
    r.n_discard_cyc, r.n_discard_units = n_discard_cyc, n_discard_units
    r.n_marketable = n_marketable
    r.n_supp_seconds = n_supp_seconds
    r.units_opened, r.units_closed = units_opened, units_closed
    r.max_inv = max_inv
    r.break_seconds = break_seconds

    # markouts (vectorised afterwards -- no look-ahead: these are diagnostics)
    def mid_at(t):
        idx = np.searchsorted(m.t_tk, t, "right") - 1
        out = np.full(len(t), np.nan)
        good = idx >= 0
        out[good] = m.mid[idx[good]]
        return out

    if len(r.p_t0):
        m0 = mid_at(r.p_t0)
        m5 = mid_at(r.p_t0 + MARKOUT)
        m60 = mid_at(r.p_t0 + MARKOUT2)
        r.p_fwd5 = r.p_side * (m5 - m0) / m0 * 1e4
        r.p_fwd60 = r.p_side * (m60 - m0) / m0 * 1e4
    else:
        r.p_fwd5 = r.p_fwd60 = np.array([], float)
    if len(r.f_t):
        b0 = np.searchsorted(m.t_tk, r.f_t, "left") - 1
        mb = np.full(len(r.f_t), np.nan)
        g = b0 >= 0
        mb[g] = m.mid[b0[g]]
        m5 = mid_at(r.f_t + MARKOUT)
        r.f_cap = r.f_side * (mb - r.f_px) / mb * 1e4
        r.f_adv = r.f_side * (m5 - mb) / mb * 1e4
    else:
        r.f_cap = r.f_adv = np.array([], float)
    # realised round-trip width in units of vola at cycle open
    if len(r.c_pnl):
        with np.errstate(all="ignore"):
            r.c_width_vola = (r.c_side * (r.c_xpx - r.c_avg)) / r.c_vola
            r.c_first_bps = r.c_side * (r.c_xpx - r.c_avg) / r.c_avg * 1e4
    else:
        r.c_width_vola = np.array([], float)
        r.c_first_bps = np.array([], float)
    return r


# ===========================================================================
# statistics
# ===========================================================================
def cell_stats(r: Res, eff_days: float):
    st = {}
    st["n_place"] = int(len(r.p_fill))
    st["n_fill"] = int(r.p_fill.sum()) if len(r.p_fill) else 0
    st["f"] = float(r.p_fill.mean()) if len(r.p_fill) else np.nan
    st["n_rt"] = int(len(r.c_pnl))
    st["rt_day"] = len(r.c_pnl) / eff_days if eff_days > 0 else np.nan
    st["units"] = int(len(r.u_bps))
    if st["units"] == 0:
        st.update(dict(mean_unit=np.nan, mean_rt=np.nan, total=np.nan,
                       daily=np.nan, tcl=np.nan, lo=np.nan, hi=np.nan,
                       maxdd=np.nan, ndays=0, days=np.array([]),
                       daily_arr=np.array([])))
        return st
    st["mean_unit"] = float(r.u_bps.mean())
    st["mean_rt"] = float(r.c_pnl.mean())
    st["total"] = float(r.u_bps.sum())
    st["daily"] = st["total"] / eff_days
    lo, hi, t = cal.boot_ci(r.u_bps, r.u_day, seed=SEED)
    st["lo"], st["hi"], st["tcl"] = lo, hi, t
    days = np.unique(r.u_day)
    daily = np.array([r.u_bps[r.u_day == d].sum() for d in days])
    st["days"], st["daily_arr"], st["ndays"] = days, daily, len(days)
    o = np.argsort(r.u_tx, kind="stable")
    cum = np.cumsum(r.u_bps[o])
    peak = np.maximum.accumulate(cum)
    st["maxdd"] = float(np.max(peak - cum)) if len(cum) else 0.0
    return st


# ===========================================================================
# diagnostic (b) -- 1-minute OHLC approximation
# ===========================================================================
class BarTape:
    pass


def build_bartape(path: Path, cutoff_iso: str) -> BarTape:
    df = pd.read_csv(path)
    t = cal.epoch_seconds(df["exec_date"])
    cut = cal.epoch_seconds(pd.Series([cutoff_iso]))[0]
    keep = t < cut
    t = t[keep]
    px = df["price"].to_numpy(float)[keep]
    sz = df["size"].to_numpy(float)[keep]
    o = np.argsort(t, kind="stable")
    t, px, sz = t[o], px[o], sz[o]
    print(f"(b) 31d prints      : {len(t):,} kept before {cutoff_iso}  "
          f"({pd.Timestamp(t[0], unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(t[-1], unit='s', tz='UTC')}, "
          f"{(t[-1] - t[0]) / 86400:.2f} days)")

    b0 = int(np.floor(t[0] / BAR_SEC))
    b1 = int(np.floor(t[-1] / BAR_SEC))
    nb = b1 - b0 + 1
    bi = np.floor(t / BAR_SEC).astype(np.int64) - b0
    high = np.full(nb, -np.inf); low = np.full(nb, np.inf)
    np.maximum.at(high, bi, px)
    np.minimum.at(low, bi, px)
    close = np.full(nb, np.nan); close[bi] = px
    opn = np.full(nb, np.nan); opn[bi[::-1]] = px[::-1]
    vol = np.zeros(nb); np.add.at(vol, bi, sz)
    empty = ~np.isfinite(close)
    fi = cal.ffill_idx(~empty)
    close = close[fi]
    opn = np.where(empty, close, opn)
    high = np.where(np.isfinite(high), high, close)
    low = np.where(np.isfinite(low), low, close)

    body = close - opn
    candlelen = np.abs(body)
    sign = np.sign(body)
    topbeard = np.where(sign > 0, high - close, high - opn)
    underbeard = np.where(sign > 0, opn - low, close - low)
    hi_b = np.maximum(opn, close)
    lo_b = np.minimum(opn, close)

    def roll(a, w, fn):
        out = np.full(len(a), np.nan)
        if len(a) >= w:
            sw = np.lib.stride_tricks.sliding_window_view(a, w)
            out[w - 1:] = fn(sw)
        return out

    vola = np.maximum(roll(candlelen, VOLA_COUNT, lambda s: s.mean(axis=1)), TICK)
    vol_ave = roll(vol, VOLA_COUNT, lambda s: s.mean(axis=1))
    rmax = roll(hi_b, RANGE_COUNT, lambda s: s.max(axis=1))
    rmin = roll(lo_b, RANGE_COUNT, lambda s: s.min(axis=1))
    rmax2 = roll(hi_b, RANGE_COUNT * 2, lambda s: s.max(axis=1))
    rmin2 = roll(lo_b, RANGE_COUNT * 2, lambda s: s.min(axis=1))
    rwidth = rmax - rmin
    rcentre = np.round((rmax + rmin) / 2.0)

    expan = np.zeros(nb, int)
    e = 0
    pmax, pmin, pcen = 0.0, 9999999.0, 0.0
    for i in range(nb):
        if hi_b[i] > pmax:
            e += 1
        elif lo_b[i] < pmin:
            e -= 1
        elif (e >= 1 and lo_b[i] < pcen) or (e <= -1 and hi_b[i] > pcen):
            e = 0
        expan[i] = e
        if np.isfinite(rmax[i]):
            pmax, pmin, pcen = rmax[i], rmin[i], rcentre[i]

    # gaps: >= 5 consecutive minutes without a print
    gap_bar = np.zeros(nb, bool)
    run = 0
    for i in range(nb):
        if empty[i]:
            run += 1
        else:
            if run >= 5:
                gap_bar[i - run:i] = True
            run = 0
    if run >= 5:
        gap_bar[nb - run:] = True
    win_bad = np.zeros(nb, bool)
    cs = np.r_[0, np.cumsum(gap_bar)]
    w = RANGE_COUNT * 2
    idx = np.arange(w - 1, nb)
    win_bad[idx] = (cs[idx + 1] - cs[idx + 1 - w]) > 0
    win_bad[:w - 1] = True
    ok = (~win_bad) & np.isfinite(rmin2) & np.isfinite(vol_ave)

    B = BarTape()
    B.n = nb
    B.b0 = b0
    B.t = (np.arange(nb) + b0) * float(BAR_SEC)
    B.opn, B.close, B.high, B.low = opn, close, high, low
    B.vol, B.candlelen, B.sign = vol, candlelen, sign
    B.topbeard, B.underbeard = topbeard, underbeard
    B.vola, B.vol_ave = vola, vol_ave
    B.rmax, B.rmin, B.rmax2, B.rmin2 = rmax, rmin, rmax2, rmin2
    B.rwidth, B.rcentre, B.expan, B.ok = rwidth, rcentre, expan, ok
    B.gap_bar = gap_bar
    B.eff_days = float(ok.sum()) * BAR_SEC / 86400.0
    print(f"(b) bars            : {nb:,} minutes, {int(ok.sum()):,} usable "
          f"= {B.eff_days:.2f} effective days "
          f"({int(gap_bar.sum()):,} minutes inside a >=5 min print gap)")
    return B


def run_cell_bars(B: BarTape, brk_on: bool, T1m: float, T2m: float,
                  breakexit: int = BREAKEXITSIZE) -> Res:
    T1 = T1m * 60.0
    T2 = T2m * 60.0
    inv_px: list[float] = []
    inv_rung: list[int] = []
    side = 0
    t_first = INF
    avg = 0.0
    orders: list[tuple[float, bool, int, int]] = []   # px, is_bid, rung, mode
    xo = None
    xkind = K_TP
    anchor_b, anchor_s = INF, -INF
    n_b = n_s = 0
    break_flg = 0
    b_signal = 0
    bup_last, bdn_last = 9999999.0, 0.0
    cyc_mode = 0
    cyc_ever = False
    cyc_supp = False
    cyc_vola = np.nan

    c_t0, c_tx, c_k, c_mode, c_ever, c_kind, c_taker = [], [], [], [], [], [], []
    c_pnl, c_avg, c_xpx, c_side, c_vola, c_supp = [], [], [], [], [], []
    u_bps, u_day, u_tx, u_rung, u_kind, u_k, u_mode = [], [], [], [], [], [], []
    n_place = n_fill = 0
    n_break_up = n_break_dn = n_break_off = 0
    n_disc = n_disc_u = n_mkt = 0
    uo = uc = 0
    max_inv = 0

    def cancel_all():
        nonlocal orders, xo, anchor_b, anchor_s, n_b, n_s
        orders = []
        xo = None
        anchor_b, anchor_s = INF, -INF
        n_b = n_s = 0

    def close_cycle(t, xpx, kind, taker):
        nonlocal side, t_first, inv_px, inv_rung, avg, uc, cyc_ever, cyc_supp
        k = len(inv_px)
        tot = 0.0
        day = int(math.floor(t / 86400.0))
        for e, rg in zip(inv_px, inv_rung):
            b = side * (xpx - e) / e * 1e4
            tot += b
            u_bps.append(b); u_day.append(day); u_tx.append(t)
            u_rung.append(rg); u_kind.append(kind); u_k.append(k)
            u_mode.append(cyc_mode)
        c_t0.append(t_first); c_tx.append(t); c_k.append(k)
        c_mode.append(cyc_mode); c_ever.append(1 if cyc_ever else 0)
        c_kind.append(kind); c_taker.append(1 if taker else 0)
        c_pnl.append(tot); c_avg.append(avg); c_xpx.append(xpx)
        c_side.append(side); c_vola.append(cyc_vola); c_supp.append(1 if cyc_supp else 0)
        uc += k
        inv_px = []; inv_rung = []
        side = 0; t_first = INF; avg = 0.0
        cyc_ever = False; cyc_supp = False
        cancel_all()

    for i in range(1, B.n):
        # decisions are taken at the OPEN of bar i on the indicators of the
        # COMPLETED bar i-1; orders then rest through bar i (R15).
        t = float(B.t[i])
        if not (B.ok[i - 1] and not B.gap_bar[i]):
            if side != 0:
                n_disc += 1
                n_disc_u += len(inv_px)
                uo -= len(inv_px)
                inv_px = []; inv_rung = []
                side = 0; t_first = INF; avg = 0.0
                cyc_ever = False; cyc_supp = False
            cancel_all()
            break_flg = 0; b_signal = 0
            bup_last, bdn_last = 9999999.0, 0.0
            continue

        q = i - 1                    # the newest COMPLETED bar
        # ---- 1. indicators of bar i-1 ------------------------------------
        if B.rmax[q] != B.rmax2[q] or break_flg != 0:
            bup_last = float(B.rmax[q] + B.rwidth[q] / 2.0)
        if B.rmin[q] != B.rmin2[q] or break_flg != 0:
            bdn_last = float(B.rmin[q] - B.rwidth[q] / 2.0)
        if B.vol[q] > B.vol_ave[q] and break_flg != 0:
            tbd, ubd = float(B.topbeard[q]), float(B.underbeard[q])
            cl, sg = float(B.candlelen[q]), float(B.sign[q])
            if tbd > ubd and tbd > cl:
                if break_flg == 1 and b_signal >= 0:
                    b_signal -= 1
                elif break_flg == -1:
                    b_signal = -1
            elif ubd > tbd and ubd > cl:
                if break_flg == -1 and b_signal <= 0:
                    b_signal += 1
                elif break_flg == 1:
                    b_signal = 1
            elif sg < 0:
                if break_flg == 1 and b_signal >= 0:
                    b_signal -= 1
                elif break_flg == -1:
                    b_signal = -1
            elif sg > 0:
                if break_flg == -1 and b_signal <= 0:
                    b_signal += 1
                elif break_flg == 1:
                    b_signal = 1
        elif b_signal != 0 and B.expan[q] == 0:
            b_signal = 0

        centre = float(B.rcentre[q]); vola = float(B.vola[q])
        rw = float(B.rwidth[q]); last = float(B.opn[i])
        bb = ba = last

        if brk_on:
            bup = bup_last if bup_last > B.rmax2[q] else float(B.rmax2[q])
            bdn = bdn_last if bdn_last < B.rmin2[q] else float(B.rmin2[q])
            if bup < bb and break_flg != 1 and b_signal != -1:
                break_flg = 1; n_break_up += 1
            elif bdn > ba and break_flg != -1 and b_signal != 1:
                break_flg = -1; n_break_dn += 1

        if break_flg == 0:
            rw_bps = rw / last * 1e4
            if rw_bps < RANGE_MIN_BPS or rw_bps > RANGE_MAX_BPS:
                e_flg = 0
            elif last > centre + ENTRY_MULT * vola:
                e_flg = -1
            elif last < centre - ENTRY_MULT * vola:
                e_flg = 1
            else:
                e_flg = 0
        else:
            if break_flg == -b_signal or (b_signal == 0 and side == 0):
                e_flg = 0
            else:
                e_flg = break_flg

        k = len(inv_px)
        if e_flg == 1:
            if n_s != 0 and k == 0:
                cancel_all()
            if k < MAX_RUNGS:
                if side > 0 and n_b == 0:
                    anchor_b = avg; n_b += k
                while n_b < MAX_RUNGS:
                    cap = bb
                    if break_flg == 0:
                        cap = min(cap, centre - ENTRY_MULT * vola)
                    cap = min(cap, anchor_b - STEP_MULT * vola - 1e-9)
                    price = math.floor(cap)
                    if not (price > 0 and price < anchor_b - STEP_MULT * vola):
                        break
                    orders.append((float(price), True, n_b,
                                   1 if break_flg != 0 else 0))
                    n_place += 1
                    n_b += 1
                    anchor_b = float(price)
        elif e_flg == -1:
            if n_b != 0 and k == 0:
                cancel_all()
            if k < MAX_RUNGS:
                if side < 0 and n_s == 0:
                    anchor_s = avg; n_s += k
                while n_s < MAX_RUNGS:
                    cap = ba
                    if break_flg == 0:
                        cap = max(cap, centre + ENTRY_MULT * vola)
                    cap = max(cap, anchor_s + STEP_MULT * vola + 1e-9)
                    price = math.ceil(cap)
                    if not (price > anchor_s + STEP_MULT * vola):
                        break
                    orders.append((float(price), False, n_s,
                                   1 if break_flg != 0 else 0))
                    n_place += 1
                    n_s += 1
                    anchor_s = float(price)
        else:
            if (n_b != 0) or (n_s != 0 and k == 0):
                cancel_all()

        k = len(inv_px)
        if k >= 1:
            if break_flg == 0:
                if side < 0:
                    if e_flg == 1:
                        x, xk = 3, K_FLIP
                    elif (t - t_first) > T2:
                        x, xk = 3, K_T2
                    elif (t - t_first) > T1 or avg < centre:
                        x, xk = 2, K_RELAX
                    else:
                        x, xk = 1, K_TP
                else:
                    if e_flg == -1:
                        x, xk = 3, K_FLIP
                    elif (t - t_first) > T2:
                        x, xk = 3, K_T2
                    elif (t - t_first) > T1 or avg > centre:
                        x, xk = 2, K_RELAX
                    else:
                        x, xk = 1, K_TP
            else:
                if (side > 0 and e_flg == -1) or (side < 0 and e_flg == 1):
                    x, xk = 3, K_FLIP
                elif b_signal == 0:
                    x, xk = 1, K_TP
                elif break_flg == -b_signal:
                    x, xk = 2, K_BDUMP
                elif k >= breakexit:
                    x, xk = 1, K_TP
                else:
                    x, xk = 0, K_TP
            if x == 3:
                close_cycle(t, last * (1.0 - side * TAKER_BPS / 1e4), xk, True)
            elif x == 0:
                cyc_supp = True
                xo = None
            else:
                ev = EXIT_MULT * vola * (1.0 / k)
                if x == 1:
                    if side > 0:
                        P = float(math.ceil(max(ba, avg + ev + 1e-9)))
                    else:
                        P = float(math.floor(min(bb, avg - ev - 1e-9)))
                else:
                    if side > 0:
                        P = float(round(min(centre, avg + ev)))
                    else:
                        P = float(round(max(centre, avg - ev)))
                marketable = (P <= bb) if side > 0 else (P >= ba)
                if xo is not None and xo[0] == P:
                    xkind = xk
                elif marketable:
                    n_mkt += 1
                    close_cycle(t, last * (1.0 - side * TAKER_BPS / 1e4), xk, True)
                else:
                    xo = (P, side < 0)
                    xkind = xk

        if break_flg == 1 and last < centre:
            break_flg = 0; b_signal = 0; n_break_off += 1
        elif break_flg == -1 and last > centre:
            break_flg = 0; b_signal = 0; n_break_off += 1

        # ---- the bar plays out: resting exit first, then the entry grid ---
        tf = float(B.t[i]) + BAR_SEC
        hi_raw = float(B.high[i]); lo_raw = float(B.low[i])
        closed = False
        if xo is not None and side != 0:
            P, is_bid = xo
            if (is_bid and lo_raw < P) or ((not is_bid) and hi_raw > P):
                close_cycle(tf, P, xkind, False)
                closed = True
        if not closed and orders:
            hits = [o for o in orders
                    if (o[1] and lo_raw < o[0]) or ((not o[1]) and hi_raw > o[0])]
            # deterministic: the rung nearest the market fills first
            hits.sort(key=lambda o: (-o[0] if o[1] else o[0]))
            for o in hits:
                if len(inv_px) >= MAX_RUNGS:
                    break
                if side != 0 and side != (1 if o[1] else -1):
                    continue
                orders.remove(o)
                n_fill += 1
                osd = 1 if o[1] else -1
                if side == 0:
                    side = osd
                    t_first = tf
                    cyc_mode = o[3]
                    cyc_ever = (o[3] == 1)
                    cyc_vola = vola
                if o[3] == 1:
                    cyc_ever = True
                inv_px.append(o[0]); inv_rung.append(o[2])
                avg = float(np.mean(inv_px))
                uo += 1
                max_inv = max(max_inv, len(inv_px))
                xo = None

    if side != 0:
        n_disc += 1
        n_disc_u += len(inv_px)
        uo -= len(inv_px)

    r = Res()
    r.cell = (brk_on, T1m, T2m)
    r.p_fill = np.array([], bool)
    r.p_t0 = np.array([], float)
    r.f_cap = r.f_adv = np.array([], float)
    r.n_place, r.n_fillx = n_place, n_fill
    r.c_t0 = np.array(c_t0, float); r.c_tx = np.array(c_tx, float)
    r.c_k = np.array(c_k, int); r.c_mode = np.array(c_mode, int)
    r.c_ever = np.array(c_ever, int); r.c_kind = np.array(c_kind, int)
    r.c_taker = np.array(c_taker, int); r.c_pnl = np.array(c_pnl, float)
    r.c_avg = np.array(c_avg, float); r.c_xpx = np.array(c_xpx, float)
    r.c_side = np.array(c_side, float); r.c_vola = np.array(c_vola, float)
    r.c_supp = np.array(c_supp, int)
    r.u_bps = np.array(u_bps, float); r.u_day = np.array(u_day, int)
    r.u_tx = np.array(u_tx, float); r.u_rung = np.array(u_rung, int)
    r.u_kind = np.array(u_kind, int); r.u_k = np.array(u_k, int)
    r.u_mode = np.array(u_mode, int)
    r.n_break_up, r.n_break_dn, r.n_break_off = n_break_up, n_break_dn, n_break_off
    r.n_discard_cyc, r.n_discard_units = n_disc, n_disc_u
    r.n_marketable = n_mkt
    r.units_opened, r.units_closed = uo, uc
    r.max_inv = max_inv
    if len(r.c_pnl):
        with np.errstate(all="ignore"):
            r.c_width_vola = (r.c_side * (r.c_xpx - r.c_avg)) / r.c_vola
    else:
        r.c_width_vola = np.array([], float)
    return r


# ===========================================================================
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "tape"))
    ap.add_argument("--diag", default=str(
        ROOT / "backtest_data" / "executions_FX_BTC_JPY_31d_20260823.csv.gz"))
    ap.add_argument("--cutoff", default="2026-08-20T08:22:17Z")
    ap.add_argument("--skip-diag", action="store_true")
    args = ap.parse_args()
    np.seterr(all="ignore")

    header("M3 MATILDA TaroCamp v37 -- EXPLORATION LEG "
           "(selection only, contaminated window)")
    print("Read-only replay of a frozen pre-registration.  The output is "
          "'propose at most\none frozen cell' or 'feasibility rejection'.  "
          "No adoption judgement is made here.\n"
          f"seed {SEED}, no network.  Verdict window (>= 2026-08-28) "
          "untouched.\n")

    m = build_market(Path(args.data))
    build_seconds(m)

    header("0. SCALE CHECK -- what the frozen v37 constants mean on this tape")
    u = m.s_usable
    jbu = m.jb[u]
    midu = m.s_mid[u]
    vol_u = m.bar["vola"][jbu]
    rw_u = m.bar["rwidth"][jbu]
    rwb = rw_u / midu * 1e4
    print(f"{'pct':>5}{'vola (JPY)':>12}{'vola bps':>10}{'40m range bps':>15}"
          f"{'entry band 2*vola':>19}{'designed cycle gain 0.8*vola':>30}")
    for q in (10, 25, 50, 75, 90):
        print(f"{'p' + str(q):>5}{np.percentile(vol_u, q):>12,.0f}"
              f"{np.percentile(vol_u / midu * 1e4, q):>10.2f}"
              f"{np.percentile(rwb, q):>15.2f}"
              f"{np.percentile(2 * vol_u / midu * 1e4, q):>16.2f} bps"
              f"{np.percentile(EXIT_MULT * vol_u / midu * 1e4, q):>27.2f} bps")
    print(f"\n  range gate [{RANGE_MIN_BPS:.0f}, {RANGE_MAX_BPS:.0f}] bps blocks "
          f"{100 * float(((rwb < RANGE_MIN_BPS) | (rwb > RANGE_MAX_BPS)).mean()):.2f}% "
          f"of usable seconds:\n  "
          f"{100 * float((rwb < RANGE_MIN_BPS).mean()):.2f}% below the floor, "
          f"{100 * float((rwb > RANGE_MAX_BPS).mean()):.2f}% above the ceiling.  "
          "v37's 150 JPY floor is INERT at\n  today's price (a 40-minute range "
          "is 24-106 bps = 26k-116k JPY); only the\n  100k JPY ceiling, "
          "carried across as 82 bps, actually binds.")
    print("  Maker entry costs nothing, so the designed gain (a few bps per "
          "cycle) sits\n  well above any cost floor -- unlike M2, this family "
          "is not killed by costs.")

    header("CELL RUNS  (a) fine-grained replay")
    results, naive, symm = {}, {}, {}
    for c in CELLS:
        r = run_cell(m, *c)
        results[c] = r
        print(f"  {cellname(c)} -> placements {len(r.p_fill):>7,}  "
              f"fills {int(r.p_fill.sum()):>6,}  round trips {len(r.c_pnl):>5,}  "
              f"units {len(r.u_bps):>6,}  taker-requotes {r.n_marketable:>5,}  "
              f"discarded cycles {r.n_discard_cyc}")
    relax = {}
    for c in CELLS:
        naive[c] = run_cell(m, *c, naive_requote=True)
        symm[c] = run_cell(m, *c, symmetric_cancel=True)
        relax[c] = run_cell(m, *c, relaxed_gaps=True)
    # counterfactual for PREREG §6.2: breakexitsize = 1 (no TP suppression)
    nosupp = {c: run_cell(m, *c, breakexit=1) for c in CELLS if c[0]}

    stats = {c: cell_stats(r, m.eff_days) for c, r in results.items()}

    # =====================================================================
    header("1. ALL FOUR CELLS  (exploration -- selection input only)")
    # =====================================================================
    print(f"{'cell':<24}{'place':>8}{'fills':>7}{'f':>7}{'rt':>7}{'rt/day':>8}"
          f"{'unit bps':>10}{'rt bps':>9}{'total':>11}{'clus t':>8}"
          f"{'95% CI (unit bps)':>21}{'maxDD':>10}")
    for c in CELLS:
        s = stats[c]
        print(f"{cellname(c):<24}{s['n_place']:>8,}{s['n_fill']:>7,}"
              f"{100 * s['f']:>6.1f}%{s['n_rt']:>7,}{fmt(s['rt_day'], 8, 1)}"
              f"{fmt(s['mean_unit'], 10, 3)}{fmt(s['mean_rt'], 9, 3)}"
              f"{fmt(s['total'], 11, 1)}{fmt(s['tcl'], 8, 2)}"
              f"  [{s['lo']:+8.3f},{s['hi']:+8.3f}]{fmt(s['maxdd'], 10, 1)}")
    print("\n  unit bps = mean per-unit round-trip return; rt bps = mean per "
          "ROUND TRIP\n  (the sum of its k units, i.e. notional-weighted, "
          "R13).  total = sum of all\n  per-unit bps.  cluster t / CI = "
          f"day-clustered bootstrap of the mean per-unit\n  bps (seed {SEED}, "
          "2000 draws).  maxDD on the cumulative per-unit curve.")

    sub("1b. inventory distribution and exit breakdown")
    print(f"{'cell':<24}{'units/rt':>9}{'hold s p50':>11}{'hold s p90':>11}"
          + "".join(f"{'k=' + str(j + 1):>7}" for j in range(7)))
    for c in CELLS:
        r = results[c]
        if not len(r.c_k):
            continue
        hold = r.c_tx - r.c_t0
        sh = [100 * float((r.c_k == j + 1).mean()) for j in range(7)]
        print(f"{cellname(c):<24}{fmt(float(r.c_k.mean()), 9, 2)}"
              f"{fmt(float(np.percentile(hold, 50)), 11, 1)}"
              f"{fmt(float(np.percentile(hold, 90)), 11, 1)}"
              + "".join(f"{v:>6.1f}%" for v in sh))

    print(f"\n{'cell':<24}{'exit':<13}{'rt':>7}{'share':>8}{'taker%':>8}"
          f"{'units':>8}{'unit bps':>11}{'total bps':>12}{'of P&L':>9}")
    for c in CELLS:
        r = results[c]
        if not len(r.c_pnl):
            continue
        tot = r.u_bps.sum()
        for kd in range(5):
            cs = r.c_kind == kd
            us = r.u_kind == kd
            if cs.sum() == 0:
                continue
            print(f"{cellname(c):<24}{KIND_NAMES[kd]:<13}{int(cs.sum()):>7,}"
                  f"{100 * cs.mean():>7.1f}%"
                  f"{100 * float(r.c_taker[cs].mean()):>7.1f}%"
                  f"{int(us.sum()):>8,}{fmt(float(r.u_bps[us].mean()), 11, 3)}"
                  f"{fmt(float(r.u_bps[us].sum()), 12, 1)}"
                  f"{fmt(100 * float(r.u_bps[us].sum()) / tot if tot else np.nan, 8, 1)}%")

    sub("1c. daily totals of per-unit bps (the cluster the statistics rest on)")
    all_days = sorted(set(int(d) for c in CELLS for d in stats[c]["days"]))
    print(f"{'cell':<24}" + "".join(
        f"{str(pd.Timestamp(d * 86400, unit='s', tz='UTC').date())[5:]:>10}"
        for d in all_days))
    for c in CELLS:
        s = stats[c]
        dd = dict(zip(s["days"], s["daily_arr"]))
        print(f"{cellname(c):<24}"
              + "".join(f"{dd[d]:>10.2f}" if d in dd else f"{'-':>10}"
                        for d in all_days))
    print(f"{'usable seconds/day':<24}"
          + "".join(f"{int(m.usable_secs_per_day[list(m.usable_days).index(d)]):>10,}"
                    if d in list(m.usable_days) else f"{'-':>10}"
                    for d in all_days))

    sub("1d. sensitivities (neither is a candidate cell)")
    print(f"{'cell':<24}{'primary unit bps':>18}{'naive-requote':>15}"
          f"{'symmetric-cancel':>18}{'primary rt':>12}{'symm rt':>10}")
    for c in CELLS:
        s1 = stats[c]
        s2 = cell_stats(naive[c], m.eff_days)
        s3 = cell_stats(symm[c], m.eff_days)
        print(f"{cellname(c):<24}{fmt(s1['mean_unit'], 18, 3)}"
              f"{fmt(s2['mean_unit'], 15, 3)}{fmt(s3['mean_unit'], 18, 3)}"
              f"{s1['n_rt']:>12,}{s3['n_rt']:>10,}")
    print("  naive-requote = a marketable exit requote filled at its OWN price "
          "instead of\n  taker (a modelling error, R11).  symmetric-cancel = "
          "R8's operator-precedence\n  asymmetry repaired.  Both are reported "
          "so neither can silently drive the answer.")
    print(f"\n{'cell':<24}{'registered gap rule':>21}{'rt':>7}"
          f"{'relaxed gap rule':>19}{'rt':>7}{'board-days reg/relax':>22}")
    for c in CELLS:
        s1 = stats[c]
        s4 = cell_stats(relax[c], m.eff_days_relaxed)
        print(f"{cellname(c):<24}{fmt(s1['mean_unit'], 21, 3)}{s1['n_rt']:>7,}"
              f"{fmt(s4['mean_unit'], 19, 3)}{s4['n_rt']:>7,}"
              f"{f'{m.eff_days:.2f} / {m.eff_days_relaxed:.2f}':>22}")
    print("  The registered rule (report #26, reused verbatim) drops every "
          "second whose\n  80-bar indicator window touches an outage; at a "
          "40-80 minute scale that is\n  expensive.  The relaxed rule keeps "
          "those seconds, with indicators computed\n  across forward-filled "
          "flat bars (which biases vola DOWN and participation UP).\n  It is a "
          "sensitivity on the sample, never a candidate cell.")

    # =====================================================================
    header("2. MODE DECOMPOSITION -- did the sign reversal earn?")
    # =====================================================================
    print(f"{'cell':<24}{'mode':<9}{'rt':>7}{'units':>8}{'unit bps':>11}"
          f"{'rt bps':>10}{'total bps':>12}{'win%':>8}")
    for c in CELLS:
        r = results[c]
        if not len(r.c_pnl):
            continue
        for md, nm in ((0, "range"), (1, "break")):
            cs = r.c_mode == md
            us = r.u_mode == md
            if cs.sum() == 0:
                continue
            print(f"{cellname(c):<24}{nm:<9}{int(cs.sum()):>7,}"
                  f"{int(us.sum()):>8,}{fmt(float(r.u_bps[us].mean()), 11, 3)}"
                  f"{fmt(float(r.c_pnl[cs].mean()), 10, 3)}"
                  f"{fmt(float(r.u_bps[us].sum()), 12, 1)}"
                  f"{100 * float((r.c_pnl[cs] > 0).mean()):>7.1f}%")
    print("  mode = the mode the cycle was OPENED in (the entry order's mode).")

    sub("2b. break-mode incidence and the b_signal exit")
    print(f"{'cell':<24}{'break-ups':>10}{'break-dns':>10}{'break-offs':>11}"
          f"{'sec in break':>14}{'% of usable':>12}{'cycles ever break':>19}")
    for c in CELLS:
        r = results[c]
        ev = int(r.c_ever.sum()) if len(r.c_ever) else 0
        print(f"{cellname(c):<24}{r.n_break_up:>10,}{r.n_break_dn:>10,}"
              f"{r.n_break_off:>11,}{r.break_seconds:>14,}"
              f"{100 * r.break_seconds / max(int(m.s_usable.sum()), 1):>11.2f}%"
              f"{ev:>19,}")
    print(f"\n{'cell':<24}{'b_signal dumps':>15}{'units':>8}{'unit bps':>11}"
          f"{'taker%':>8}{'total bps':>12}")
    for c in CELLS:
        r = results[c]
        if not len(r.c_pnl):
            continue
        cs = r.c_kind == K_BDUMP
        us = r.u_kind == K_BDUMP
        if cs.sum() == 0:
            print(f"{cellname(c):<24}{0:>15}{'-':>8}{'-':>11}{'-':>8}{'-':>12}")
            continue
        print(f"{cellname(c):<24}{int(cs.sum()):>15,}{int(us.sum()):>8,}"
              f"{fmt(float(r.u_bps[us].mean()), 11, 3)}"
              f"{100 * float(r.c_taker[cs].mean()):>7.1f}%"
              f"{fmt(float(r.u_bps[us].sum()), 12, 1)}")

    sub("2c. breakexitsize = 3 -- what the TP suppression actually bought")
    print("Counterfactual: the same cells with breakexitsize = 1 (a TP is "
          "quoted from the\nfirst unit, so no cycle is ever let run).  "
          "DIAGNOSTIC, not a candidate cell.")
    print(f"\n{'cell':<24}{'supp. cycles':>13}{'their unit bps':>16}"
          f"{'their rt bps':>14}{'cell total':>12}{'no-supp total':>15}"
          f"{'delta':>10}")
    for c in CELLS:
        if not c[0]:
            continue
        r = results[c]
        rn = nosupp[c]
        if not len(r.c_pnl):
            continue
        sp = r.c_supp == 1
        tot = float(r.u_bps.sum())
        totn = float(rn.u_bps.sum()) if len(rn.u_bps) else np.nan
        us = np.isin(np.arange(len(r.u_bps)), []) if sp.sum() == 0 else None
        if sp.sum():
            # per-unit bps of the units belonging to suppressed cycles
            idx = np.repeat(sp, r.c_k)
            mu = float(r.u_bps[idx].mean())
            mrt = float(r.c_pnl[sp].mean())
        else:
            mu = mrt = np.nan
        print(f"{cellname(c):<24}{int(sp.sum()):>13,}{fmt(mu, 16, 3)}"
              f"{fmt(mrt, 14, 3)}{fmt(tot, 12, 1)}{fmt(totn, 15, 1)}"
              f"{fmt(tot - totn, 10, 1)}")
    print("  delta > 0 means the suppression (letting the break run to 3 units "
          "before\n  quoting a TP) EARNED, delta < 0 means it cost.")

    # =====================================================================
    header("3. THE ASYMMETRY -- realised round-trip width vs the design value")
    # =====================================================================
    print("PREREG §0 reads the v37 asymmetry as a profit unit of "
          "(2.0-0.8)*vola = 1.2*vola.\nThe v37 SOURCE does not implement that: "
          "`exit_setting = 0.8` is never referenced;\n`step_exit = 0.8` is, and "
          "order_exit measures the TP from the AVERAGE ENTRY,\nnot from the "
          "centre: exit_vola = 0.8*vola*(sizemin/mybtc) = 0.8*vola/k.  So the\n"
          "DESIGNED width is 0.8*vola/k per unit -- and because it is "
          "apportioned, the\nwhole cycle's designed gross gain is 0.8*vola of "
          "price REGARDLESS of k, while\nthe notional at risk grows linearly "
          "with k.  Measured below against both.")
    print(f"\n{'cell':<24}{'k':>4}{'rt':>7}{'width/vola p50':>16}"
          f"{'p25':>9}{'p75':>9}{'design 0.8/k':>14}{'unit bps':>10}"
          f"{'rt bps':>9}")
    for c in CELLS:
        r = results[c]
        if not len(r.c_pnl):
            continue
        for kk in range(1, 8):
            cs = r.c_k == kk
            if cs.sum() < 5:
                continue
            w = r.c_width_vola[cs]
            us = r.u_k == kk
            print(f"{cellname(c):<24}{kk:>4}{int(cs.sum()):>7,}"
                  f"{fmt(float(np.nanpercentile(w, 50)), 16, 3)}"
                  f"{fmt(float(np.nanpercentile(w, 25)), 9, 3)}"
                  f"{fmt(float(np.nanpercentile(w, 75)), 9, 3)}"
                  f"{fmt(EXIT_MULT / kk, 14, 3)}"
                  f"{fmt(float(r.u_bps[us].mean()), 10, 3)}"
                  f"{fmt(float(r.c_pnl[cs].mean()), 9, 3)}")
    print("\n  width/vola = (exit price - average entry) signed toward the "
          "position, divided\n  by the vola in force when the cycle opened.  "
          "Design = 0.8/k (apportioned TP);\n  the PREREG's 1.2 is the value "
          "the mapping BELIEVED it had frozen.")

    sub("3b. apportionment by rung (compare M2 report #29 §2.3: averaging "
        "gave\n     +2.4..+3.5 bps/unit but a 1.7x notional and a worse total)")
    print(f"{'cell':<24}{'rung':>6}{'units':>8}{'unit bps':>11}"
          f"{'share of total':>16}")
    for c in CELLS:
        r = results[c]
        if not len(r.u_bps):
            continue
        tot = r.u_bps.sum()
        for j in range(MAX_RUNGS):
            us = r.u_rung == j
            if us.sum() < 5:
                continue
            print(f"{cellname(c):<24}{j + 1:>6}{int(us.sum()):>8,}"
                  f"{fmt(float(r.u_bps[us].mean()), 11, 3)}"
                  f"{fmt(100 * float(r.u_bps[us].sum()) / tot if tot else np.nan, 15, 1)}%")
    sub("3c. the apportionment identity -- the cycle's gross win does not "
        "scale with\n     the risk the cycle took on")
    print("cycle gross in PRICE units of vola = (width/vola) * k.  If the "
          "apportioned TP\nis the binding exit, this is 0.8 for EVERY k: the "
          "cycle wins 0.8*vola of price\nwhether it is carrying 1 unit or 7.  "
          "The loss, when the TP is never reached, is\ntaken on all k units.")
    print(f"\n{'cell':<24}{'k':>4}{'rt':>7}{'median gross/vola':>19}"
          f"{'mean gross/vola':>17}{'design':>9}")
    for c in CELLS:
        r = results[c]
        if not len(r.c_pnl):
            continue
        for kk in range(1, 8):
            cs = r.c_k == kk
            if cs.sum() < 5:
                continue
            g = r.c_width_vola[cs] * kk
            print(f"{cellname(c):<24}{kk:>4}{int(cs.sum()):>7,}"
                  f"{fmt(float(np.nanmedian(g)), 19, 3)}"
                  f"{fmt(float(np.nanmean(g)), 17, 3)}{EXIT_MULT:>9.3f}")
    print(f"\n{'cell':<24}{'winning rt':>11}{'mean rt bps':>13}{'mean k':>8}"
          f"{'hold p50':>10}{'losing rt':>11}{'mean rt bps':>13}{'mean k':>8}"
          f"{'hold p50':>10}")
    for c in CELLS:
        r = results[c]
        if not len(r.c_pnl):
            continue
        hold = r.c_tx - r.c_t0
        lo_ = r.c_pnl < 0
        hi_ = ~lo_
        print(f"{cellname(c):<24}{int(hi_.sum()):>11,}"
              f"{fmt(float(r.c_pnl[hi_].mean()), 13, 2)}"
              f"{fmt(float(r.c_k[hi_].mean()), 8, 2)}"
              f"{fmt(float(np.percentile(hold[hi_], 50)), 10, 0)}"
              f"{int(lo_.sum()):>11,}"
              f"{fmt(float(r.c_pnl[lo_].mean()), 13, 2)}"
              f"{fmt(float(r.c_k[lo_].mean()), 8, 2)}"
              f"{fmt(float(np.percentile(hold[lo_], 50)), 10, 0)}")
    print("  The machine wins small on a LIGHT book and loses big on a HEAVY "
          "one.  That is\n  not a parameter: it is what "
          "`exit_vola = 0.8*vola*(sizemin/mybtc)` says.  The\n  device the "
          "PREREG expected to harvest M2's averaging gain is the same device\n"
          "  that caps the win at a level independent of the risk taken to "
          "earn it.")

    print(f"\n{'cell':<24}{'k>=2 rt':>9}{'rung1-only bps':>16}"
          f"{'avg per-unit bps':>18}{'delta (averaging)':>19}")
    for c in CELLS:
        r = results[c]
        if not len(r.c_pnl):
            continue
        cs = r.c_k >= 2
        if cs.sum() == 0:
            continue
        # rung-1-only counterfactual: the first unit alone at the same exit px
        first = []
        pos = 0
        for idx in range(len(r.c_k)):
            if cs[idx]:
                first.append(r.u_bps[pos])
            pos += r.c_k[idx]
        first = np.array(first, float)
        per_unit = r.c_pnl[cs] / r.c_k[cs]
        print(f"{cellname(c):<24}{int(cs.sum()):>9,}"
              f"{fmt(float(first.mean()), 16, 3)}"
              f"{fmt(float(per_unit.mean()), 18, 3)}"
              f"{fmt(float((per_unit - first).mean()), 19, 3)}")

    # =====================================================================
    header("4. ADVERSE SELECTION AND THE TIME LADDER")
    # =====================================================================
    print("Calibration reference (#26, queue/C1/10 s touch quotes): capture "
          "+0.604,\n  adverse(5 s) -1.321, cap+adv -0.716 bps; #29 measured "
          "filled -1.4..-1.8 vs\n  missed +0.2..+0.4 bps at 5 s.")
    print(f"\n{'cell':<24}{'placed':>8}{'filled':>8}{'f':>7}{'cap':>9}"
          f"{'adv(5s)':>9}{'cap+adv':>9}{'FILLED fwd5':>12}{'MISSED fwd5':>12}"
          f"{'FILLED fwd60':>13}{'MISSED fwd60':>13}")
    for c in CELLS:
        r = results[c]
        if not len(r.p_fill):
            continue
        fl = r.p_fill
        print(f"{cellname(c):<24}{len(fl):>8,}{int(fl.sum()):>8,}"
              f"{100 * fl.mean():>6.1f}%"
              f"{fmt(float(np.nanmean(r.f_cap)), 9, 3)}"
              f"{fmt(float(np.nanmean(r.f_adv)), 9, 3)}"
              f"{fmt(float(np.nanmean(r.f_cap + r.f_adv)), 9, 3)}"
              f"{fmt(float(np.nanmean(r.p_fwd5[fl])), 12, 3)}"
              f"{fmt(float(np.nanmean(r.p_fwd5[~fl])), 12, 3)}"
              f"{fmt(float(np.nanmean(r.p_fwd60[fl])), 13, 3)}"
              f"{fmt(float(np.nanmean(r.p_fwd60[~fl])), 13, 3)}")
    print("\n  cap = (mid just before the fill - our price) signed toward the "
          "position;\n  adv(5 s) = mid drift over the 5 s after the fill, "
          "signed the same way;\n  fwd5/fwd60 = mid drift from PLACEMENT, "
          "signed toward the quote's side -- the\n  counterfactual population "
          "is the placements that were cancelled unfilled.")

    sub("4b. time-ladder bucket economics -- is 'relax' another word for "
        "'taker'?")
    print(f"{'cell':<24}{'bucket':<13}{'rt':>7}{'maker rt':>10}{'taker rt':>10}"
          f"{'maker unit bps':>16}{'taker unit bps':>16}")
    for c in CELLS:
        r = results[c]
        if not len(r.c_pnl):
            continue
        uk_taker = np.repeat(r.c_taker.astype(bool), r.c_k)
        for kd in (K_TP, K_RELAX, K_BDUMP, K_T2, K_FLIP):
            cs = r.c_kind == kd
            if cs.sum() == 0:
                continue
            us = r.u_kind == kd
            mk = us & ~uk_taker
            tk = us & uk_taker
            print(f"{cellname(c):<24}{KIND_NAMES[kd]:<13}{int(cs.sum()):>7,}"
                  f"{int((cs & (r.c_taker == 0)).sum()):>10,}"
                  f"{int((cs & (r.c_taker == 1)).sum()):>10,}"
                  f"{fmt(float(r.u_bps[mk].mean()) if mk.any() else np.nan, 16, 3)}"
                  f"{fmt(float(r.u_bps[tk].mean()) if tk.any() else np.nan, 16, 3)}")

    sub("4c. break-even arithmetic: what would the losing bucket have to lose?")
    print(f"{'cell':<24}{'p_win':>8}{'g_win':>10}{'p_lose':>8}"
          f"{'l_lose actual':>15}{'l_lose needed':>15}{'factor':>9}")
    for c in CELLS:
        r = results[c]
        if not len(r.u_bps):
            continue
        win = r.u_bps > 0
        lose = ~win
        if not win.any() or not lose.any():
            continue
        pw, pl = float(win.mean()), float(lose.mean())
        gw, gl = float(r.u_bps[win].mean()), float(r.u_bps[lose].mean())
        need = -pw * gw / pl
        print(f"{cellname(c):<24}{100 * pw:>7.1f}%{fmt(gw, 10, 3)}"
              f"{100 * pl:>7.1f}%{fmt(gl, 15, 3)}{fmt(need, 15, 3)}"
              f"{fmt(gl / need, 8, 2)}x")

    # =====================================================================
    header("5. DIAGNOSTIC (b) -- 27-day 1-minute approximation "
           "(REFERENCE ONLY, NOT SELECTION)")
    # =====================================================================
    if args.skip_diag:
        print("skipped by --skip-diag")
    else:
        B = build_bartape(Path(args.diag), args.cutoff)
        print("PREREG §3: (b) supplies independent 40-minute episodes but its "
              "fills are a\nconservative bar approximation on TRADE prices "
              "with no book; §4's selection\nrule uses (a) ONLY.  If (b) and "
              "(a) disagree the rule is not overturned.\n")
        bres = {c: run_cell_bars(B, *c) for c in CELLS}
        bst = {c: cell_stats(r, B.eff_days) for c, r in bres.items()}
        print(f"{'cell':<24}{'placed':>8}{'fills':>8}{'rt':>7}{'rt/day':>8}"
              f"{'unit bps':>10}{'rt bps':>9}{'total':>11}{'clus t':>8}"
              f"{'95% CI (unit bps)':>21}{'maxDD':>10}")
        for c in CELLS:
            r, s = bres[c], bst[c]
            print(f"{cellname(c):<24}{r.n_place:>8,}{r.n_fillx:>8,}"
                  f"{s['n_rt']:>7,}{fmt(s['rt_day'], 8, 1)}"
                  f"{fmt(s['mean_unit'], 10, 3)}{fmt(s['mean_rt'], 9, 3)}"
                  f"{fmt(s['total'], 11, 1)}{fmt(s['tcl'], 8, 2)}"
                  f"  [{s['lo']:+8.3f},{s['hi']:+8.3f}]{fmt(s['maxdd'], 10, 1)}")
        print(f"\n{'cell':<24}{'exit':<13}{'rt':>7}{'share':>8}{'taker%':>8}"
              f"{'unit bps':>11}{'total bps':>12}")
        for c in CELLS:
            r = bres[c]
            if not len(r.c_pnl):
                continue
            for kd in range(5):
                cs = r.c_kind == kd
                us = r.u_kind == kd
                if cs.sum() == 0:
                    continue
                print(f"{cellname(c):<24}{KIND_NAMES[kd]:<13}{int(cs.sum()):>7,}"
                      f"{100 * cs.mean():>7.1f}%"
                      f"{100 * float(r.c_taker[cs].mean()):>7.1f}%"
                      f"{fmt(float(r.u_bps[us].mean()), 11, 3)}"
                      f"{fmt(float(r.u_bps[us].sum()), 12, 1)}")
        print(f"\n{'cell':<24}{'mode':<9}{'rt':>7}{'unit bps':>11}"
              f"{'total bps':>12}{'break-ups':>11}{'break-dns':>11}")
        for c in CELLS:
            r = bres[c]
            if not len(r.c_pnl):
                continue
            for md, nm in ((0, "range"), (1, "break")):
                cs = r.c_mode == md
                us = r.u_mode == md
                if cs.sum() == 0:
                    continue
                print(f"{cellname(c):<24}{nm:<9}{int(cs.sum()):>7,}"
                      f"{fmt(float(r.u_bps[us].mean()), 11, 3)}"
                      f"{fmt(float(r.u_bps[us].sum()), 12, 1)}"
                      f"{r.n_break_up:>11,}{r.n_break_dn:>11,}")
        print("\n  (b) participation is INFLATED relative to (a): a bar model "
              "fills any order\n  the bar's high/low touched through, with no "
              "queue ahead of it.  Read the\n  SIGN and the mode split, never "
              "the level.")

    # =====================================================================
    header("6. SANITY")
    # =====================================================================
    print("look-ahead 0    : indicators use only COMPLETED 1-minute bars "
          "(bar floor(s/60)-1);\n                  a quote's price uses the "
          "board at or before its placement second;\n                  every "
          "fill test uses prints strictly after the order existed; queue\n"
          "                  arrival is evaluated at the END of a second and "
          "applies to later\n                  prints; the exit price in force "
          "during (s-1,s] was set at s-1.")
    ok_all = True
    for c in CELLS:
        r = results[c]
        inv_ok = r.max_inv <= MAX_RUNGS
        bal_ok = r.units_opened == r.units_closed
        ok_all &= inv_ok and bal_ok
        print(f"  {cellname(c)}: max inventory {r.max_inv} <= 7 "
              f"{'OK' if inv_ok else 'FAIL'} | units opened {r.units_opened:,}"
              f" == closed {r.units_closed:,} {'OK' if bal_ok else 'FAIL'} | "
              f"cycles discarded on gaps {r.n_discard_cyc} "
              f"({r.n_discard_units} units)")
    assert ok_all, "position integrity violated -- results not read"

    sub("6b. reproduction gate -- is the break-OFF range mechanism comparable "
        "with M2?")
    print("The PREREG asks that the break-OFF cell's range machine be "
          "COMPARABLE with the\nM2 range machine of report #29.  The two are "
          "the same family but not the same\nmechanism; the differences are "
          "enumerated so the comparison is honest:\n")
    print(f"  {'axis':<26}{'M2 (report #29)':<28}{'M3 break-OFF'}")
    for a, b_, c_ in (
            ("bar / window", "5 s bars, 6-bar window", "60 s bars, 40-bar window"),
            ("entry threshold", "centre -/+ 2.0*vola", "centre -/+ 2.0*vola  (same)"),
            ("grid spacing", "2.0*vola", "1.0*vola"),
            ("max inventory", "1 or 4 units", "7 units"),
            ("TP target", "centre -/+ 2.0*vola (beta=delta)",
             "avg entry -/+ 0.8*vola/k"),
            ("beta = delta identity", "YES -- no designed edge",
             "NO -- edge = 0.8*vola/k"),
            ("entry order life", "10 s, cancel policy C1", "rests until cancelled"),
            ("entry price", "at the touch", "grid price (>= 2*vola off centre)"),
            ("time ladder", "60/120 s or 120/240 s", "20/40 min or 40/80 min"),
            ("forced exit", "taker at T2", "taker at T2 or on signal flip")):
        print(f"  {a:<26}{b_:<28}{c_}")
    print("\n  So M2's mechanism-level death (report #29 §2.1, the beta=delta "
          "identity that\n  leaves a single-rung cycle no source of gain above "
          "a 1-tick guard) DOES NOT\n  transfer: M3's TP is measured from the "
          "entry, not the centre, so a designed\n  width of 0.8*vola/k exists. "
          " That is the whole point of registering M3, and it\n  is the gate "
          "this section certifies.  Measured entry economics of the range\n"
          "  machine (for comparison with #26/#29's touch-quote numbers):\n")
    print(f"  {'cell':<24}{'range fills':>12}{'cap':>9}{'adv(5s)':>9}"
          f"{'cap+adv':>9}{'f':>8}")
    for c in CELLS:
        r = results[c]
        if not len(r.f_cap):
            continue
        sel = r.f_mode == 0
        if sel.sum() == 0:
            continue
        psel = r.p_mode == 0
        print(f"  {cellname(c):<24}{int(sel.sum()):>12,}"
              f"{fmt(float(np.nanmean(r.f_cap[sel])), 9, 3)}"
              f"{fmt(float(np.nanmean(r.f_adv[sel])), 9, 3)}"
              f"{fmt(float(np.nanmean(r.f_cap[sel] + r.f_adv[sel])), 9, 3)}"
              f"{100 * float(r.p_fill[psel].mean()):>7.1f}%")
    print("\n  capture is LARGE compared with #26's +0.604 bps because M3 does "
          "not quote at\n  the touch: the grid price sits >= 2*vola away from "
          "the centre and is reached\n  only by a move that comes to it.  That "
          "is the registered difference, not an\n  engine difference -- the "
          "fill engine is the imported one (queue-realistic\n  inside the "
          "visible ladder, strict traded-through outside it).")

    sub("6c. gap accounting, determinism, funding")
    print(f"  recorder gaps (union)         : {len(m.gs)} intervals")
    print(f"  usable decision seconds       : {int(m.s_usable.sum()):,} = "
          f"{m.eff_days:.3f} effective board-days of "
          f"{m.span_days:.3f} wall-clock")
    print(f"  cycles discarded for a gap    : "
          f"{sum(results[c].n_discard_cyc for c in CELLS)} across the 4 cells")
    hold_all = np.concatenate([results[c].c_tx - results[c].c_t0
                               for c in CELLS if len(results[c].c_tx)])
    if len(hold_all):
        print(f"  holding time p50 / p90 / max  : "
              f"{np.percentile(hold_all, 50):.0f} / "
              f"{np.percentile(hold_all, 90):.0f} / {hold_all.max():.0f} s")
        print(f"  funding not charged; at 0.06 %/day the p90 hold implies "
              f"{0.06e4 / 100 * np.percentile(hold_all, 90) / 86400:.3f} bps")
    print(f"  determinism                   : seed {SEED}; the only RNG is the "
          f"seeded cluster\n                                  bootstrap; no "
          f"network, no wall-clock input")

    # =====================================================================
    header("7. SELECTION RULE (PREREG §4) APPLIED")
    # =====================================================================
    print("1. cut: round trips >= 50 AND net (unit bps) > 0")
    passing = []
    for c in CELLS:
        s = stats[c]
        ok = (s["n_rt"] >= 50 and np.isfinite(s["mean_unit"])
              and s["mean_unit"] > 0)
        print(f"   {cellname(c)}: round trips {s['n_rt']:>6,}  "
              f"net {fmt(s['mean_unit'], 9, 3)} bps/unit  -> "
              f"{'PASS' if ok else 'cut'}")
        if ok:
            passing.append(c)
    print(f"\n   passing cells: {len(passing)} of 4")
    print("   chance expectation: under a zero-edge null each cell's net is "
          "positive with\n   probability ~0.5, so ~2 of 4 would pass by chance "
          "alone; the 4 cells share\n   one tape and are strongly correlated, "
          "so they are far fewer than 4\n   independent tries.")
    if not passing:
        print("\n   PREREG §4.1: ZERO cells pass -> FEASIBILITY REJECTION.")
        print("   The verdict window (>= 2026-08-28) is NOT consumed.")
    else:
        best = max(passing, key=lambda c: (stats[c]["tcl"]
                                           if np.isfinite(stats[c]["tcl"])
                                           else -np.inf))
        print("\n2. among the passing cells, the maximum day-clustered t")
        for c in passing:
            print(f"   {cellname(c)}: cluster t {fmt(stats[c]['tcl'], 7, 2)}"
                  f"{'   <== max' if c == best else ''}")
        print("\n3. plateau: each axis neighbour must keep >= 50 % of the "
              "selected cell's net")
        base = stats[best]["mean_unit"]
        plateau = True
        brk, T1, T2 = best
        alt_l = (40.0, 80.0) if (T1, T2) == (20.0, 40.0) else (20.0, 40.0)
        for nb_, axis in (((not brk, T1, T2), "break"),
                          ((brk, alt_l[0], alt_l[1]), "ladder")):
            v = stats[nb_]["mean_unit"]
            ratio = v / base if base else np.nan
            ok = np.isfinite(ratio) and ratio >= 0.5
            plateau &= ok
            print(f"   axis {axis:<7} neighbour {cellname(nb_)}: net "
                  f"{fmt(v, 9, 3)} ({fmt(100 * ratio, 6, 0)}% of selected) -> "
                  f"{'ok' if ok else 'DEGRADED'}")
        print(f"\n   plateau: {'satisfied' if plateau else 'NOT satisfied'}")
        if plateau:
            print(f"\n   PROPOSED FREEZE (one cell, the LEAD decides): "
                  f"{cellname(best)}")
        else:
            print("\n   PREREG §4.2/4.3: report but DO NOT proceed to the "
                  "verdict.")

    # =====================================================================
    header("8. MULTIPLICITY AND LIMITS")
    # =====================================================================
    print("* Multiplicity ledger for the shared verdict window (>= 2026-08-28):")
    print("    M2 matilda-modern   8 candidate cells  (spent, report #29)")
    print("    M3 matilda-taro     4 candidate cells  (this run)")
    print("    running total      12 candidates.  A spread-MM symmetric family "
          "registered\n    against the SAME window must carry 12 forward and "
          "add its own.")
    print("* Diagnostics run here that are NOT candidates and were never "
          "eligible for\n  selection: naive-requote (4), symmetric-cancel (4), "
          "relaxed-gap sample (4),\n  breakexitsize=1 (2), and "
          "the 27-day 1-minute approximation (4).  "
          "They are sensitivities and mechanism\n  measurements, reported "
          "beside the family, never in place of it.")
    print(f"* {m.eff_days:.2f} effective board-days and "
          f"{stats[CELLS[0]]['ndays']} UTC-day clusters on a 40-80 minute "
          f"machine:\n  the number of INDEPENDENT 40-minute episodes is small, "
          "which is exactly why\n  the PREREG added diagnostic (b).")
    print("* One venue, one regime, one contaminated window.  These numbers "
          "select; they\n  never adopt.")
    print("* Depth beyond five levels is unobservable, so an order deeper than "
          "the visible\n  ladder can only be filled by a strictly-through "
          "print (conservative).")
    print("* Our own order adds no size to the book, so a sweep that would "
          "have stopped at\n  our level still counts as a sweep (imported "
          "from #26).")
    print("* Unexplored (so the rejection level stays honest): entry 2.0 / "
          "exit 0.8 / step\n  1.0 / 7 rungs / breakexitsize 3 / delay 1 / "
          "b_signal 2 strikes are all FROZEN\n  by the PREREG and were not "
          "swept; the range gate [10, 82] bps was not swept;\n  the SFD arm is "
          "deleted by the mapping; rung size is 1 unit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
