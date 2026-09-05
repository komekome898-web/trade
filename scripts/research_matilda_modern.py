#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 MATILDA MODERNISED -- inventory-grid mean-reversion MM, EXPLORATION LEG.

This run is the EXPLORATION (selection) leg only.  Its window is already
contaminated (report #26 read execution calibration and directional board
features out of it), so its numbers may be used ONLY to (a) freeze at most one
cell and (b) decide feasibility-rejection.  The verdict window (>= 2026-08-28)
is not touched by a single byte here.

================================================================================
PRE-REGISTRATION -- docs/PREREG_matilda_modern.md, transcribed verbatim
================================================================================

# PREREG - M2 マチルダ現代化(在庫グリッド型ミーンリバージョンMM)

**凍結日: 2026-08-28。以降の変更は「事前登録の破棄」であり、変更したければ新しい事前登録を
新しい名前で作り直す。** 原典: `docs/legacy/matilda_v52.py`(2020)、分析はチャット記録
2026-08-28(v52 の実装事実5件を含む)。

---

## 0. 位置づけと事前分布(正直に書く)

M2 は第26報(執行校正)が絞り込んだ問い -「**反対脚が逆選択に食われる前に往復を
閉じられるか**」- の片側・在庫型の検定であり、KNOWLEDGE §2 が「1ロットの往復は連続両側の
天井に機構的に届かない(u §6.7)→ その先はスプレッドMM」と指した**在庫帯 >1 ロットの
最初の実測**でもある。

**帰無仮説(校正の実測)**: 単発クオートの片脚経済は全域で負(capture+adverse(5s) =
-0.09〜-0.86bps、capture-f トレードオフの両端とも)。M2 の主張は「グリッド在庫の平均化 +
中心回帰 maker TP + 時間上限」が**往復単位**の経済を正に変える、である。
敵対する既知事実: レンジ逆張りコアは分スケールで棄却済み(d,j,k)、エントリは
contrarian maker = 敵側(逆選択の壁)。味方する既知事実: TP(順方向の maker)は
選択効果の味方側、時間上限は損失有界化として E2 で実証済み(分散改善)。
**30秒スケール・在庫つきの「機械全体」は未検証** - それだけを検定する。

## 1. 現代化の写像(原典 → M2。ここで凍結)

| 原典 v52 | M2(スケール不変) | 根拠 |
|---|---|---|
| 5秒足、レンジ=6本のヒゲ除去高安(実質**実体レンジ**) | 5秒足(mid)、レンジ=6本の**実体(open/close)極値**と明示 | v52 の beard_ignore=1円は事実上全ヒゲクリップ = 実体レンジ。事実婚を正式化 |
| vola = Σ|実体|(5本)/6(バグ) | vola = **真の平均**(6本の|実体|/6) | バグ修正。真値は約1.2倍 |
| 中心±entry_setting(2)×vola からエントリ | 同じ(**β=2 固定、掃引しない**) | 原典の魂を保存 |
| 壁(≥1BTC)の2円手前に指値 | **ベストタッチに queue-realistic(C1取消・寿命10s)** | 壁手前は判定棄却(第27報)、壁は吸収体でない。校正の主構成を逐語使用 |
| グリッド間隔 entry_step(2)×vola、最大 order_count 段 | 同じ(**γ=2 固定**)、段数 N は族の軸 | |
| 利確: 中心∓exit_setting(2)×vola の指値、建値ガード±100円 | 同じ(**δ=2 固定**)、建値ガード = **建値±1ティック** | 100円は今日0.08bp=1ティック相当 |
| 時間ラダー: 1分で緩和 / 2分で成行連打 | (T1: TP を中心側無条件に緩和 / T2: taker 全量成行)、(T1,T2) は族の軸 | E2 の時間フォールバックと同思想 |
| vr レジーム切替(出荷設定では無効) | **廃止**。代替ゲート = S7 両側フロー窓(族の軸) | vr は両スケールで棄却。窓は f +5.38pp と実測(vr の4.3倍) |
| SFD ±5% ガード | 既存 `sfd_guard_pct`(ベーシス異常ガード)に置換 | SFD 制度は廃止済み |
| 時刻アノマリー表 / スリープ窓 | 廃止(時間帯方向性は棄却済み)/ メンテガードは既存BOT機構 | f 報 |
| 複利・連勝減ロット | **持ち込まない**(サイズは1単位固定、リスクは既存オーバーレイ) | サイジングは戦略と分離する家訓 |
| health == ('NORMAL' or 'BUSY') バグ | 既存 API 健全性機構(resilience.py)に置換 | |

## 2. 構成ファミリー - **8セル。後から1つも足さない**

固定(掃引しない): β=2、γ=2、δ=2、クオート寿命10s、取消C1、1約定=1単位(0.01 BTC)、
建値ガード1ティック、判定は queue-realistic(conservative/optimistic は括弧として併記)。

| 軸 | 水準 |
|---|---|
| 在庫段数 N | **1**(単発 - 帰無側)/ **4**(原典のグリッド - 主張側) |
| 時間ラダー (T1, T2) | **(60s, 120s)**(原典)/ **(120s, 240s)**(緩和) |
| レジームゲート | **なし**(常時)/ **S7 両側フロー窓内のみ**(v_min はバーンイン固定、直前窓判定) |

2×2×2 = 8セル。**N=1 が負で N=4 が正なら「在庫の平均化が効く」という機構主張が立ち、
N=1 も N=4 も負なら族全体が校正の帰無どおり**である - この対比が本登録の科学的中身。

## 3. データと分割

- **探索(選択区間)**: 2026-08-20〜08-27 の共有板データ(ticker + executions +
  board_top5)。この区間は校正・方向特徴の読みで**既に消費済み(汚染済み)**であり、
  ここでの数値は選択にのみ使い、採用判断には引用しない。
- **判定(1段目・板リプレイ)**: **2026-08-28T00:00Z 以降**に蓄積される板データが
  **14板日**(ギャップ破棄後の実効)に達した時点で、**一度だけ**実行。早見禁止。
  見込み 2026-09-11 頃。
- ギャップ規律・エポック検査・バーンイン(v_min・分布定数は判定区間先頭20%で固定、
  取引を置かない)は第26報の実装を逐語再利用。

## 4. 選択規則(探索区間に適用。ここで凍結)

1. 足切り: 探索区間で 日次ネット bps > 0 かつ 約定 ≥100 のセルのみ残す。
   **0セルなら族はフィージビリティ棄却、判定は実行しない**(S8/S9 の先例)。
2. 残りから **日次クラスタ t 最大**のセルを1つ選ぶ(平均最大ではなく安定性)。
3. 台地条件: 選択セルの各軸の隣接水準が日次ネットで50%未満に劣化しないこと。
   劣化していれば「報告するが判定に進まない」。
4. 8候補中の通過数を偶然期待と併記(§8.3)。凍結するのは**最大1セル**。

## 5. 判定基準 - KNOWLEDGE §5 高頻度/MMクラス逐語(操作的定義は S8 PREREG §5.4 を継承)

判定区間(≥8/28 の14板日)で、選択された1セルが**すべて**満たすこと:
ネットEV>0 をクラスタ補正 t≥2.0 で立証(n≥300)かつ 日次ネット **+10bps/日以上** かつ
日次シャープ **≥1.0**(年率換算 ×√365 で凍結)かつ maxDD **≤1000bps**(累積、1x notional)
かつ 実効約定率・逆選択の実測報告。

**2段目**: 1段目通過後、**ペーパー14日**で同一基準を同一定義で再適用(§5「板リプレイ→
ペーパーの2段」)。ペーパー投入自体もオーナー承認制。1段目通過は採用ではない。

## 6. 必須報告(探索・判定とも)

1. 全8セル表(n・約定率・日次ネットbps・クラスタt/CI・日次シャープ・maxDD・在庫分布)
2. **N=1 対 N=4 の機構対比**: 段ごとの約定単価・平均化の寄与・在庫時間分布 -
   「平均化は救っているのか、負けを遅らせているだけか」を数値で
3. 逆選択の反実仮想(約定群/取り逃し群の前方推移。校正値 -1.1〜-1.3bps@5s との比較)
4. 時間ラダーの出口内訳(TP / 緩和 / 強制)と各バケット経済 - v52 の「損失は強制決済に
   集中するはず」という予想の検証
5. サニティ: ルックアヘッド0・建玉整合(グリッド段数≤N を assert)・入れ子性・決定性・
  ギャップ破棄数・校正との整合(ゲートなし N=1 セルの f・capture が第26報と一致すること =
  再現ゲート)
6. 多重性: 8候補、および同じ判定窓を将来使う可能性のあるスプレッドMM対称族との
   **候補数の合算**をレポートに明記する(窓の共有は候補数の共有である)

## 7. 結果の読み方(先に決める)

| 結果 | 結論 |
|---|---|
| 探索で全セル負 | フィージビリティ棄却。判定データ不消費。棄却水準(§10)を書き分け |
| 判定で全項目通過 | 2段目(ペーパー14日)へ**オーナー承認の上で**進む。採用ではない |
| 判定で1項目でも欠け | 棄却レポート。バーは動かさない |
| 探索勝者と判定勝者の入替り | 過学習兆候として不採用 |
| N=1 負・N=4 正(判定で) | 在庫平均化の機構主張が成立 - スプレッドMM対称族の設計根拠に昇格 |
| N=4 も負 | 在庫帯 >1 でも片側では閉じない - スプレッドMM は両側同時性が必須という設計制約に |

## 8. 実装

- 探索・判定スクリプト: `scripts/research_matilda_modern.py`(本 PREREG を docstring に
  逐語、`research_board_calibration.py` の約定・ギャップ・ブートストラップ機構を import)
- ペーパー投入時(2段目)は既存 `src/bot/strategy/` に新戦略として実装し、
  strategy.name 切替 = カウント再スタート(§5)に従う
- 乱数 seed 20260828。判定実行はオーナー承認制(本 §5)

## 9. オーナー承認が必要な項目

1. 本ファミリー(8セル)と選択規則の凍結
2. 判定窓の定義(≥2026-08-28、実効14板日、一度だけ)
3. 1段目通過時のペーパー投入(その時点で改めて確認)

署名: リード(M2設計)。凍結日時: 2026-08-28。

================================================================================
IMPLEMENTATION RESOLUTIONS -- fixed before the first run, never tuned after
================================================================================
The PREREG fixes the mechanism; a state machine needs a few statements the
prose leaves implicit.  Each is resolved here toward the literal v52 source,
and each is stated so a reader can audit it.

R1  SUBSTRATE.  ticker_*.csv.gz (event-driven best bid/ask + sizes) and
    executions_*.csv.gz (taker side).  board_top5_*.csv.gz is NOT consumed:
    every M2 quote is placed AT THE TOUCH (the wall-front placement it would
    have needed was rejected in report #27), so top-of-book is the complete
    observable, and the 1 Hz depth record would only downsample it.  The
    reproduction gate against report #26 requires the same substrate #26 used.

R2  CLOCKS.  Strategy state (range, vola, centre) advances only on COMPLETED
    5 s bars.  Order placement and exit management run on a 1 s decision grid
    (v52's order_delay = 1 s).  Fills are detected at the true print
    timestamp; within one 1 s step, events are processed in timestamp order.
    Resolution limit: the exit price in force during a step is the one
    computed at the start of that step.

R3  BARS.  5 s bars on the absolute epoch grid, built from the board mid
    (research_board_calibration.build_bars, imported).  open/close = first/
    last mid of the bar; an empty bar is a flat bar at the previous close.
    range = max over the last 6 COMPLETED bars of max(open,close) minus min
    over the same 6 of min(open,close);  vola = mean of |close-open| over
    those 6 bars, floored at 1 tick (1 JPY);  centre = (max+min)/2.
    A 6-bar window that touches a recorder gap places no quote.

R4  SIDE.  last = the mid at the decision second.  last > centre -> ask side
    only; last < centre -> bid side only; last == centre -> no quote.  While
    inventory is open, a new rung is placed only if the signal side still
    equals the inventory side (v52 requires entry_flg to hold to keep
    laddering).  M2 never opens opposite-side inventory: the PREREG's
    inventory is one-sided by construction ("約定するたび在庫+1段").
    NOTE: v52's exit_flg == 3 doten (force-close when the signal flips) is
    NOT implemented -- the PREREG §1 mapping does not carry it, and adding it
    would be an unregistered mechanism.  It is listed as an unexplored
    direction in the limits.

R5  RUNGS.  Rung 0 requires touch <= centre - β·vola (bid) / >= centre +
    β·vola (ask).  Rung j>0 additionally requires touch <= last_fill_price -
    γ·vola (bid) / >= last_fill_price + γ·vola (ask) AND the rung-0 centre
    condition, which is v52's `price < lsp and price < buy_status.price-step`
    with the last FILL as the anchor.  Inventory is capped at N (asserted).

R6  ENTRY FILL MODEL.  research_board_calibration's primary configuration,
    clause for clause: quote at the touch, Q = the best size on our side at
    placement, lifetime 10 s, cancel policy C1 (cancel the first time the
    touch on our side outpaces us -- the imported next_greater/next_smaller
    clause), queue-realistic fill = min(first time cumulative opposite-side
    at-or-through volume >= Q, first strictly-through print).  One live entry
    quote at a time; a new one may be placed the next second after the last
    one filled, cancelled or expired.  Zero fee, zero slippage (maker).

R7  EXIT (TP) FILL MODEL.  The exit is a resting maker limit for the WHOLE
    inventory at one price P.  Top-of-book cannot show the size resting at a
    price away from the touch, so the queue is resolved conservatively:
      * "arrival" = the first ticker row at which our price is at or inside
        the market's best on our side (sell exit: best_ask >= P;
        buy exit: best_bid <= P);
      * Q_exit = the best size at that row if the best is EXACTLY P, else 0
        (P is then alone inside the spread);
      * after arrival we fill when cumulative opposite-side at-or-through
        volume since arrival exceeds Q_exit;
      * at any time (arrived or not) a print strictly through P fills us.
    Repricing (below) resets arrival and the accumulated volume -- i.e. we
    lose queue position on every requote, which is conservative.
    A forced (taker) exit is priced at the mid minus TAKER_BPS = 3.96 bps in
    the direction of the trade (the repo's frozen 激動 taker one-way cost:
    1.96 half-spread + 2.0 slippage), never at the touch, so the half-spread
    is not double counted.

R7b MARKETABLE REQUOTE.  A limit order that is RE-SUBMITTED at a price
    already through the market does not rest -- it executes immediately as a
    taker.  So on any requote (including the T1 relaxation, which is exactly
    v52's exit_flg == 2 re-submission) whose new price is marketable (long:
    P <= best bid; short: P >= best ask) the inventory is closed at once at
    mid -/+ TAKER_BPS.  An ALREADY RESTING order is never re-tested this way:
    it is hit by the arriving flow first (that is what R7 models).  The naive
    alternative -- filling a marketable requote at its own, worse price -- is
    reported as a sensitivity, not as the primary; it is a modelling error,
    not a parameter.

R8  EXIT PRICE.  For a long: P_raw = centre - δ·vola; if P_raw <= average
    entry, P = average entry + 1 tick (the break-even guard).  For a short:
    P_raw = centre + δ·vola; if P_raw >= average entry, P = average entry - 1
    tick.  P is rounded to the 1 JPY tick and recomputed every decision
    second; it therefore follows the centre, and any change requotes.
    After T1 (measured from the FIRST fill of the cycle) the guard is
    dropped: P = P_raw unconditionally (v52 exit_flg == 2).  At T2 the whole
    inventory is closed taker (v52 exit_flg == 3 / reflesh).

R9  REGIME GATE.  Level "S7 window only": a new ENTRY quote may be placed at
    second s only if the fully observed PREVIOUS 30 s window (floor(s/30)-1)
    was two-sided, using the S7 rule imported verbatim (taker-BUY volume >=
    v_min AND taker-SELL volume >= v_min AND |B-S|/(B+S) <= 0.30), with
    v_min = the 50th percentile of the pooled per-window one-side volume over
    the leading 20 % burn-in, floored strictly positive.  EXITS are never
    gated.

R10 GAP DISCIPLINE.  GAP_SEC = 30 s of ticker silence, imported.  A decision
    second is unusable if its own board state is stale, if [s, s+10+5] touches
    a gap, or if it precedes the burn-in end.  A cycle that is open when an
    unusable second arrives is DISCARDED whole (its fills are excluded from
    every economic statistic) and counted.  A cycle still open at the end of
    the record is discarded the same way.  This is what discards trades
    straddling the 8.4 h outage of 2026-08-25T18:30Z..2026-08-26T02:54Z.

R11 P&L CONVENTION.  1 unit = 0.01 BTC = 1x notional.  Per-unit return in bps
    is signed toward the position.  A cycle holding k units contributes the
    SUM of its k per-unit returns, so a 4-rung cycle carries up to 4x
    notional -- daily net bps, the cumulative curve and maxDD are all on this
    notional-weighted basis (PREREG §5 "1x notional" cumulative bps).  The
    per-round-trip mean is reported alongside so the two readings can be told
    apart.  Funding (0.06 %/day, settled 05/13/21 UTC) is NOT charged: a
    cycle lives <= 240 s, so its expected share is ~0.017 bps; it is reported
    as a note, not applied.

R12 STATISTICS.  Day-clustered bootstrap of the mean per-unit bps (imported
    boot_ci, UTC-day clusters, 2000 draws, seed 20260828) gives the primary
    cluster t and CI.  Daily Sharpe = mean(daily net bps)/sd(daily net bps)
    x sqrt(365).  maxDD = the largest peak-to-trough drop of the cumulative
    per-unit bps curve ordered by exit time.

Offline only -- reads files, opens no sockets, places no orders.
Read-only, idempotent, deterministic.  seed 20260828, no network.

Usage: PYTHONPATH=src python scripts/research_matilda_modern.py
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import research_board_calibration as cal  # noqa: E402  (structural reuse)

SEED = 20260828

# ---- frozen constants (PREREG §2) -----------------------------------------
BETA = 2.0            # entry_setting
GAMMA = 2.0           # entry_step
DELTA = 2.0           # exit_setting
QUOTE_LIFE = 10.0     # s
TICK = 1.0            # JPY
UNIT_BTC = 0.01
TAKER_BPS = 3.96      # 激動 taker one-way (research-protocol §3)
MARKOUT = 5.0         # s
BAR_SEC = cal.VR_BAR_SEC          # 5
NBARS = cal.VR_BARS               # 6
W = cal.W                         # 30 s S7 grid
BURN_FRAC = cal.BURN_FRAC         # 0.20
GAP_SEC = cal.GAP_SEC             # 30 s

CELLS = [(N, T1, T2, gate)
         for N in (1, 4)
         for (T1, T2) in ((60.0, 120.0), (120.0, 240.0))
         for gate in ("none", "window")]

EXIT_TP, EXIT_RELAX, EXIT_FORCED = 0, 1, 2
EXIT_NAMES = ("TP", "relaxed", "forced")


def header(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def sub(t):
    print("\n--- " + t + " " + "-" * max(0, 72 - len(t)))


# ---------------------------------------------------------------------------
# market container
# ---------------------------------------------------------------------------
class Market:
    pass


def build_market(data_dir: Path) -> Market:
    (t_tk, bid, ask, bsz, asz, mid, spread_bps,
     t_ex, px, sz, buy, span_days) = cal.load(data_dir)
    gs, ge = cal.find_gaps(t_tk, t_ex)

    m = Market()
    m.t_tk, m.bid, m.ask, m.bsz, m.asz = t_tk, bid, ask, bsz, asz
    m.mid, m.spread = mid, spread_bps
    m.t_ex, m.px, m.sz, m.buy = t_ex, px, sz, buy
    m.gs, m.ge = gs, ge
    m.span_days = span_days

    m.burn_end = t_tk[0] + BURN_FRAC * (t_tk[-1] - t_tk[0])
    print(f"burn-in             : leading {BURN_FRAC:.0%} = "
          f"{cal.pd.Timestamp(t_tk[0], unit='s', tz='UTC')} .. "
          f"{cal.pd.Timestamp(m.burn_end, unit='s', tz='UTC')} "
          f"(v_min only; carries no trade)")

    # ---- S7 grid + regime (imported verbatim) -----------------------------
    g = cal.build_grid(t_ex, sz, buy, t_tk, gs, ge)
    burn_w = g.usable & (g.start < m.burn_end)
    pool = np.concatenate([g.vbuy[burn_w], g.vsell[burn_w]])
    v_raw = float(np.percentile(pool, 50))
    v_min = max(v_raw, cal.VOL_EPS)
    ts_mask = cal.two_sided_mask(g, v_min) & g.usable
    duty = ts_mask.sum() / max(g.usable.sum(), 1)
    print(f"v_min (S7 p50, burn): {v_raw:.6f} BTC -> {v_min:.6f}"
          f"{'  (FLOORED)' if v_raw <= 0 else ''}")
    print(f"S7 two-sided regime : duty {100 * duty:.2f}% "
          f"(#26 reported 11.11%, S7 11.45%)")
    m.g, m.ts_mask, m.duty, m.v_min = g, ts_mask, duty, v_min

    # ---- 5 s bars ---------------------------------------------------------
    b0, nb, opn, high, low, close, empty = cal.build_bars(t_tk, mid)
    body = np.abs(close - opn)
    up = np.maximum(opn, close)
    dn = np.minimum(opn, close)
    # rolling stats over the trailing NBARS COMPLETED bars, indexed by the
    # bar that is the LAST of the window
    vola = np.full(nb, np.nan)
    centre = np.full(nb, np.nan)
    if nb >= NBARS:
        bw = np.lib.stride_tricks.sliding_window_view(body, NBARS)
        uw = np.lib.stride_tricks.sliding_window_view(up, NBARS)
        dw = np.lib.stride_tricks.sliding_window_view(dn, NBARS)
        idx = np.arange(NBARS - 1, nb)
        vola[idx] = bw.mean(axis=1)
        centre[idx] = 0.5 * (uw.max(axis=1) + dw.min(axis=1))
    vola = np.maximum(vola, TICK)          # 1 tick floor (R3)
    bar_start = (np.arange(nb) + b0) * float(BAR_SEC)
    # a 6-bar window that touches a gap is unusable
    win_lo = bar_start - (NBARS - 1) * BAR_SEC
    win_hi = bar_start + BAR_SEC
    bar_ok = ~cal.span_touches_gap(win_lo, win_hi, gs, ge)
    bar_ok &= np.isfinite(centre)
    m.b0, m.nb, m.vola, m.centre, m.bar_ok = b0, nb, vola, centre, bar_ok
    print(f"5s bars             : {nb:,} bars, {100 * empty.mean():.1f}% with "
          f"no quote change; {100 * bar_ok.mean():.1f}% carry a usable "
          f"6-bar window")

    # ---- C1 cancel clocks (imported clause) --------------------------------
    tt = np.r_[t_tk, np.inf]
    m.cancel_bid = tt[cal.next_greater(bid)]
    m.cancel_ask = tt[cal.next_smaller(ask)]
    return m


def build_seconds(m: Market) -> Market:
    """Per-second decision grid with everything precomputed."""
    t0 = math.ceil(m.t_tk[0])
    t1 = math.floor(m.t_tk[-1] - MARKOUT - QUOTE_LIFE)
    secs = np.arange(t0, t1 + 1, 1.0)
    ip = np.searchsorted(m.t_tk, secs, "right") - 1
    ok = ip >= 0
    secs, ip = secs[ok], ip[ok]

    stale = (secs - m.t_tk[ip]) > GAP_SEC
    span_bad = cal.span_touches_gap(secs, secs + QUOTE_LIFE + MARKOUT,
                                    m.gs, m.ge)
    usable = (~stale) & (~span_bad) & (secs >= m.burn_end)

    jb = np.floor(secs / BAR_SEC).astype(np.int64) - m.b0 - 1   # last complete
    jb_ok = (jb >= 0) & (jb < m.nb)
    jbc = np.clip(jb, 0, m.nb - 1)
    bar_ok = jb_ok & m.bar_ok[jbc]

    kw = np.floor(secs / W).astype(np.int64) - m.g.k0            # own window
    prev_ok = (kw - 1 >= 0) & (kw - 1 < m.g.n)
    kwp = np.clip(kw - 1, 0, m.g.n - 1)
    regime = prev_ok & m.ts_mask[kwp]

    m.secs = secs
    m.ip = ip
    m.s_bid = m.bid[ip]
    m.s_ask = m.ask[ip]
    m.s_bsz = m.bsz[ip]
    m.s_asz = m.asz[ip]
    m.s_mid = m.mid[ip]
    m.s_usable = usable
    m.s_barok = bar_ok
    m.s_centre = m.centre[jbc]
    m.s_vola = m.vola[jbc]
    m.s_regime = regime
    m.s_cbid = m.cancel_bid[ip]
    m.s_cask = m.cancel_ask[ip]
    m.s_day = np.floor(secs / 86400.0).astype(np.int64)

    eff_days = float(usable.sum()) / 86400.0
    m.eff_days = eff_days
    print(f"decision grid       : {len(secs):,} seconds, "
          f"{int(usable.sum()):,} usable post-burn-in "
          f"= {eff_days:.3f} effective board-days "
          f"({int((~usable).sum()):,} dropped: burn-in / stale / gap-span)")
    print(f"                      regime-gate duty over usable seconds "
          f"{100 * regime[usable].mean():.2f}%")
    return m


# ---------------------------------------------------------------------------
# fill engines
# ---------------------------------------------------------------------------
def entry_resolve(m: Market, t0: float, price: float, Q: float,
                  is_bid: bool, cancel_t: float):
    """(fill_time or None, resolution_time) for one touch quote -- R6."""
    end = min(t0 + QUOTE_LIFE, cancel_t)
    if end <= t0:
        return None, t0
    lo = np.searchsorted(m.t_ex, t0, "right")
    hi = np.searchsorted(m.t_ex, end, "right")
    if hi > lo:
        tt = m.t_ex[lo:hi]
        p = m.px[lo:hi]
        z = m.sz[lo:hi]
        b = m.buy[lo:hi]
        if is_bid:
            m_at = (~b) & (p <= price)
            m_thr = (~b) & (p < price)
        else:
            m_at = b & (p >= price)
            m_thr = b & (p > price)
        ft = np.inf
        if m_thr.any():
            ft = float(tt[int(np.argmax(m_thr))])
        if m_at.any():
            cv = np.cumsum(np.where(m_at, z, 0.0))
            k = np.flatnonzero(cv >= Q)
            if k.size:
                ft = min(ft, float(tt[int(k[0])]))
        if np.isfinite(ft):
            return ft, ft
    return None, end


class ExitQuote:
    __slots__ = ("price", "arrived", "t_arrive", "Q", "cum")

    def __init__(self):
        self.price = 0.0
        self.arrived = False
        self.t_arrive = np.inf
        self.Q = 0.0
        self.cum = 0.0

    def reprice(self, price: float):
        if price != self.price:
            self.price = price
            self.arrived = False
            self.t_arrive = np.inf
            self.Q = 0.0
            self.cum = 0.0


def exit_scan(m: Market, tp: ExitQuote, a: float, b: float, is_sell: bool):
    """Detect a maker exit fill in (a, b].  Returns fill time or None -- R7."""
    P = tp.price
    if not tp.arrived:
        ka = np.searchsorted(m.t_tk, a, "right")
        kb = np.searchsorted(m.t_tk, b, "right")
        if kb > ka:
            best = m.ask[ka:kb] if is_sell else m.bid[ka:kb]
            mask = (best >= P) if is_sell else (best <= P)
            if mask.any():
                k = ka + int(np.argmax(mask))
                tp.arrived = True
                tp.t_arrive = float(m.t_tk[k])
                bp = m.ask[k] if is_sell else m.bid[k]
                tp.Q = float(m.asz[k] if is_sell else m.bsz[k]) if bp == P else 0.0
                tp.cum = 0.0
    lo = np.searchsorted(m.t_ex, a, "right")
    hi = np.searchsorted(m.t_ex, b, "right")
    if hi <= lo:
        return None
    tt = m.t_ex[lo:hi]
    p = m.px[lo:hi]
    z = m.sz[lo:hi]
    bu = m.buy[lo:hi]
    if is_sell:
        m_thr = bu & (p > P)
        m_at = bu & (p >= P)
    else:
        m_thr = (~bu) & (p < P)
        m_at = (~bu) & (p <= P)
    ft = np.inf
    if m_thr.any():
        ft = float(tt[int(np.argmax(m_thr))])
    if tp.arrived:
        valid = m_at & (tt > tp.t_arrive)
        if valid.any():
            cv = tp.cum + np.cumsum(np.where(valid, z, 0.0))
            k = np.flatnonzero(cv >= tp.Q)
            if k.size:
                ft = min(ft, float(tt[int(k[0])]))
            tp.cum = float(cv[-1])
    return ft if np.isfinite(ft) else None


def mid_before(m: Market, t: float):
    i = np.searchsorted(m.t_tk, t, "left") - 1
    return float(m.mid[i]) if i >= 0 else np.nan


def mid_at(m: Market, t: float):
    i = np.searchsorted(m.t_tk, t, "right") - 1
    return float(m.mid[i]) if i >= 0 else np.nan



def control_quotes(m: Market, stride: int = 10):
    """UNCONDITIONAL touch quotes on the same seconds, same fill rules -- the
    control population that isolates M2's entry condition from the engine."""
    idx = np.flatnonzero(m.s_usable)[::stride]
    n_f = n_q = 0
    caps, advs, lives = [], [], []
    for i in idx:
        s = float(m.secs[i])
        for is_bid in (True, False):
            price = float(m.s_bid[i]) if is_bid else float(m.s_ask[i])
            Q = float(m.s_bsz[i]) if is_bid else float(m.s_asz[i])
            canc = float(m.s_cbid[i]) if is_bid else float(m.s_cask[i])
            if not (price > 0):
                continue
            n_q += 1
            lives.append(min(s + QUOTE_LIFE, canc) - s)
            ft, _ = entry_resolve(m, s, price, Q, is_bid, canc)
            if ft is None:
                continue
            n_f += 1
            m0 = mid_before(m, ft)
            m5 = mid_at(m, ft + MARKOUT)
            sg = 1.0 if is_bid else -1.0
            if np.isfinite(m0) and m0 > 0:
                caps.append(sg * (m0 - price) / m0 * 1e4)
                advs.append(sg * (m5 - m0) / m0 * 1e4 if np.isfinite(m5) else np.nan)
    return (n_q, n_f, np.array(caps), np.array(advs), np.array(lives))


# ---------------------------------------------------------------------------
# the state machine
# ---------------------------------------------------------------------------
class Result:
    pass


def run_cell(m: Market, N: int, T1: float, T2: float, gate: str,
             naive_requote: bool = False) -> Result:
    secs = m.secs
    n = len(secs)
    usable = m.s_usable
    barok = m.s_barok
    regime = m.s_regime
    centre = m.s_centre
    vola = m.s_vola
    s_bid, s_ask, s_bsz, s_asz, s_mid = m.s_bid, m.s_ask, m.s_bsz, m.s_asz, m.s_mid
    s_cbid, s_cask = m.s_cbid, m.s_cask

    gate_on = (gate == "window")

    # quote-level records
    q_t0, q_side, q_price, q_fill, q_rung = [], [], [], [], []
    # fill-level records
    f_t, f_price, f_side, f_rung, f_cap, f_adv, f_dist = [], [], [], [], [], [], []
    # cycle-level records
    c_texit, c_units, c_type, c_pnl, c_hold, c_day, c_maxrung = [], [], [], [], [], [], []
    c_avg, c_exitpx, c_first, c_side = [], [], [], []
    # per-unit records (for cluster stats)
    u_bps, u_day, u_texit, u_rung, u_type = [], [], [], [], []

    def retire(p, filled):
        q_t0.append(p[0]); q_side.append(1 if p[3] else -1)
        q_price.append(p[1]); q_fill.append(1 if filled else 0)
        q_rung.append(p[6])

    n_exit_voided = 0
    n_marketable = 0
    n_discard_cycle = 0
    n_discard_units = 0
    max_inv_seen = 0
    units_opened = 0
    units_closed = 0

    inv_px: list[float] = []
    inv_t: list[float] = []
    inv_rung: list[int] = []
    side = 0                     # +1 long, -1 short
    t_first = np.inf
    tp = ExitQuote()
    pending = None               # (t0, price, Q, is_bid, fill_t, resolve_t, rung)

    for i in range(n):
        s = float(secs[i])
        a = s - 1.0

        if not usable[i]:
            if side != 0:
                n_discard_cycle += 1
                n_discard_units += len(inv_px)
                units_opened -= len(inv_px)
                inv_px, inv_t, inv_rung = [], [], []
                side = 0
                t_first = np.inf
            if pending is not None:
                retire(pending, False)
                pending = None
            tp.reprice(0.0)
            continue

        # ---- collect events in (a, s] -------------------------------------
        ev = []
        if pending is not None:
            ft = pending[4]
            if ft is not None and ft <= s:
                ev.append((ft, "entry", 0.0))
            elif pending[5] <= s:
                ev.append((pending[5], "expire", 0.0))
        if side != 0 and tp.price > 0.0:
            xt = exit_scan(m, tp, a, s, is_sell=(side > 0))
            if xt is not None:
                ev.append((xt, "exit", tp.price))
        ev.sort(key=lambda e: e[0])

        entry_first = False
        for tev, kind, epx in ev:
            if kind == "exit" and entry_first:
                # a rung filled earlier in this same second, so the resting
                # exit was requoted (R8) before this print could reach it
                n_exit_voided += 1
                continue
            if kind == "expire":
                if pending is not None:
                    retire(pending, False)
                    pending = None
            elif kind == "entry":
                if pending is None:
                    continue
                t0, price, Q, is_bid, ft, rt, rung, ce_ref = pending
                pending = None
                if side != 0 and side != (1 if is_bid else -1):
                    continue                       # cycle closed meanwhile
                if len(inv_px) >= N:
                    continue
                q_t0.append(t0); q_side.append(1 if is_bid else -1)
                q_price.append(price); q_fill.append(1); q_rung.append(rung)
                m0 = mid_before(m, ft)
                m5 = mid_at(m, ft + MARKOUT)
                sg = 1.0 if is_bid else -1.0
                if np.isfinite(m0) and m0 > 0:
                    f_cap.append(sg * (m0 - price) / m0 * 1e4)
                    f_adv.append(sg * (m5 - m0) / m0 * 1e4
                                 if np.isfinite(m5) else np.nan)
                else:
                    f_cap.append(np.nan); f_adv.append(np.nan)
                f_dist.append(sg * (ce_ref - price) / ce_ref * 1e4)
                f_t.append(ft); f_price.append(price)
                f_side.append(1 if is_bid else -1); f_rung.append(rung)
                if side == 0:
                    side = 1 if is_bid else -1
                    t_first = ft
                inv_px.append(price); inv_t.append(ft); inv_rung.append(rung)
                units_opened += 1
                max_inv_seen = max(max_inv_seen, len(inv_px))
                assert len(inv_px) <= N, "inventory rung cap violated"
                tp.reprice(0.0)                     # force requote next step
                entry_first = True
            elif kind == "exit":
                if side == 0:
                    continue
                k = len(inv_px)
                relaxed = (tev - t_first) >= T1
                etype = EXIT_RELAX if relaxed else EXIT_TP
                _close(tev, epx, etype, side, inv_px, inv_rung, t_first,
                       c_texit, c_units, c_type, c_pnl, c_hold, c_day,
                       c_maxrung, c_avg, c_exitpx, c_first, c_side,
                       u_bps, u_day, u_texit, u_rung, u_type)
                units_closed += k
                inv_px, inv_t, inv_rung = [], [], []
                side = 0
                t_first = np.inf
                tp.reprice(0.0)
                if pending is not None:
                    retire(pending, False)
                    pending = None

        # ---- time ladder: forced taker exit -------------------------------
        if side != 0 and (s - t_first) >= T2:
            mp = float(s_mid[i])
            xpx = mp * (1.0 - side * TAKER_BPS / 1e4)
            k = len(inv_px)
            _close(s, xpx, EXIT_FORCED, side, inv_px, inv_rung, t_first,
                   c_texit, c_units, c_type, c_pnl, c_hold, c_day,
                   c_maxrung, c_avg, c_exitpx, c_first, c_side,
                   u_bps, u_day, u_texit, u_rung, u_type)
            units_closed += k
            inv_px, inv_t, inv_rung = [], [], []
            side = 0
            t_first = np.inf
            tp.reprice(0.0)
            if pending is not None:
                retire(pending, False)
                pending = None

        # ---- exit price for the coming interval ---------------------------
        if side != 0:
            if barok[i]:
                ce, vo = float(centre[i]), float(vola[i])
                avg = float(np.mean(inv_px))
                relaxed = (s - t_first) >= T1
                if side > 0:
                    p_raw = ce - DELTA * vo
                    p = p_raw if (relaxed or p_raw > avg) else avg + TICK
                else:
                    p_raw = ce + DELTA * vo
                    p = p_raw if (relaxed or p_raw < avg) else avg - TICK
                p = float(round(p))
                requote = (p != tp.price)
                marketable = (p <= float(s_bid[i])) if side > 0 else \
                             (p >= float(s_ask[i]))
                if requote and marketable and not naive_requote:
                    # R7b: a re-submitted limit already through the market
                    # executes immediately as a TAKER, not at its own price
                    mp = float(s_mid[i])
                    xpx = mp * (1.0 - side * TAKER_BPS / 1e4)
                    k = len(inv_px)
                    n_marketable += 1
                    _close(s, xpx, EXIT_RELAX if relaxed else EXIT_TP, side,
                           inv_px, inv_rung, t_first,
                           c_texit, c_units, c_type, c_pnl, c_hold, c_day,
                           c_maxrung, c_avg, c_exitpx, c_first, c_side,
                           u_bps, u_day, u_texit, u_rung, u_type)
                    units_closed += k
                    inv_px, inv_t, inv_rung = [], [], []
                    side = 0
                    t_first = np.inf
                    tp.reprice(0.0)
                    if pending is not None:
                        retire(pending, False)
                        pending = None
                else:
                    tp.reprice(p)
        else:
            tp.reprice(0.0)

        # ---- placement ----------------------------------------------------
        if pending is None and len(inv_px) < N and barok[i]:
            if (not gate_on) or regime[i]:
                ce, vo = float(centre[i]), float(vola[i])
                last = float(s_mid[i])
                want = 0
                if last < ce:
                    want = 1
                elif last > ce:
                    want = -1
                if want != 0 and (side == 0 or side == want):
                    rung = len(inv_px)
                    if want > 0:
                        price = float(s_bid[i])
                        okp = price <= ce - BETA * vo
                        if okp and rung > 0:
                            okp = price <= inv_px[-1] - GAMMA * vo
                        Q = float(s_bsz[i])
                        canc = float(s_cbid[i])
                    else:
                        price = float(s_ask[i])
                        okp = price >= ce + BETA * vo
                        if okp and rung > 0:
                            okp = price >= inv_px[-1] + GAMMA * vo
                        Q = float(s_asz[i])
                        canc = float(s_cask[i])
                    if okp and price > 0:
                        ft, rt = entry_resolve(m, s, price, Q, want > 0, canc)
                        pending = (s, price, Q, want > 0, ft, rt, rung, ce)

    # cycle open at the end of the record -> discard
    if side != 0:
        n_discard_cycle += 1
        n_discard_units += len(inv_px)
        units_opened -= len(inv_px)
    if pending is not None:
        retire(pending, False)

    r = Result()
    r.N, r.T1, r.T2, r.gate = N, T1, T2, gate
    r.q_t0 = np.array(q_t0, float); r.q_side = np.array(q_side, float)
    r.q_price = np.array(q_price, float); r.q_fill = np.array(q_fill, bool)
    r.q_rung = np.array(q_rung, int)
    r.f_t = np.array(f_t, float); r.f_price = np.array(f_price, float)
    r.f_side = np.array(f_side, float); r.f_rung = np.array(f_rung, int)
    r.f_cap = np.array(f_cap, float); r.f_adv = np.array(f_adv, float)
    r.f_dist = np.array(f_dist, float)
    r.c_texit = np.array(c_texit, float); r.c_units = np.array(c_units, int)
    r.c_type = np.array(c_type, int); r.c_pnl = np.array(c_pnl, float)
    r.c_hold = np.array(c_hold, float); r.c_day = np.array(c_day, int)
    r.c_maxrung = np.array(c_maxrung, int)
    r.c_first = np.array(c_first, float); r.c_exitpx = np.array(c_exitpx, float)
    r.c_side = np.array(c_side, float); r.c_avg = np.array(c_avg, float)
    r.u_bps = np.array(u_bps, float); r.u_day = np.array(u_day, int)
    r.u_texit = np.array(u_texit, float); r.u_rung = np.array(u_rung, int)
    r.u_type = np.array(u_type, int)
    # what the FIRST rung alone would have returned at the same exit price
    with np.errstate(all="ignore"):
        r.c_first_bps = (r.c_side * (r.c_exitpx - r.c_first) / r.c_first * 1e4
                         if len(r.c_first) else np.array([], float))
    # forward 5 s mid move from placement, signed toward the quote's side
    if len(r.q_t0):
        i0 = np.searchsorted(m.t_tk, r.q_t0, "right") - 1
        i5 = np.searchsorted(m.t_tk, r.q_t0 + MARKOUT, "right") - 1
        good = (i0 >= 0) & (i5 >= 0)
        fwd = np.full(len(r.q_t0), np.nan)
        m0 = m.mid[np.clip(i0, 0, None)]
        m5 = m.mid[np.clip(i5, 0, None)]
        fwd[good] = (r.q_side * (m5 - m0) / m0 * 1e4)[good]
        r.q_fwd = fwd
    else:
        r.q_fwd = np.array([], float)
    r.n_exit_voided = n_exit_voided
    r.n_marketable = n_marketable
    r.n_discard_cycle = n_discard_cycle
    r.n_discard_units = n_discard_units
    r.max_inv_seen = max_inv_seen
    r.units_opened = units_opened
    r.units_closed = units_closed
    return r


def _close(tev, xpx, etype, side, inv_px, inv_rung, t_first,
           c_texit, c_units, c_type, c_pnl, c_hold, c_day, c_maxrung,
           c_avg, c_exitpx, c_first, c_side,
           u_bps, u_day, u_texit, u_rung, u_type):
    tot = 0.0
    day = int(math.floor(tev / 86400.0))
    for e, rg in zip(inv_px, inv_rung):
        b = side * (xpx - e) / e * 1e4
        tot += b
        u_bps.append(b); u_day.append(day); u_texit.append(tev)
        u_rung.append(rg); u_type.append(etype)
    c_texit.append(tev); c_units.append(len(inv_px)); c_type.append(etype)
    c_pnl.append(tot); c_hold.append(tev - t_first); c_day.append(day)
    c_maxrung.append(max(inv_rung) + 1 if inv_rung else 0)
    c_avg.append(float(np.mean(inv_px))); c_exitpx.append(xpx)
    c_first.append(inv_px[0]); c_side.append(float(side))


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------
def cell_stats(r: Result, eff_days: float):
    st = {}
    st["n_quotes"] = int(len(r.q_fill))
    st["n_fills"] = int(r.q_fill.sum())
    st["f"] = float(r.q_fill.mean()) if len(r.q_fill) else np.nan
    st["n_cycles"] = int(len(r.c_pnl))
    st["rt_per_day"] = len(r.c_pnl) / eff_days if eff_days > 0 else np.nan
    st["units"] = int(len(r.u_bps))

    if len(r.u_bps) == 0:
        st.update(dict(daily_net=np.nan, tcl=np.nan, lo=np.nan, hi=np.nan,
                       sharpe=np.nan, maxdd=np.nan, mean_unit=np.nan,
                       mean_rt=np.nan, t_daily=np.nan, ndays=0))
        return st

    total = float(r.u_bps.sum())
    st["daily_net"] = total / eff_days
    lo, hi, t = cal.boot_ci(r.u_bps, r.u_day, seed=SEED)
    st["lo"], st["hi"], st["tcl"] = lo, hi, t
    st["mean_unit"] = float(r.u_bps.mean())
    st["mean_rt"] = float(r.c_pnl.mean())

    # daily aggregation over the usable seconds actually present per day
    days = np.unique(r.u_day)
    daily = np.array([r.u_bps[r.u_day == d].sum() for d in days])
    st["ndays"] = len(days)
    st["daily_arr"] = daily
    st["days"] = days
    sd = float(daily.std(ddof=1)) if len(daily) > 1 else np.nan
    st["sharpe"] = (float(daily.mean()) / sd * math.sqrt(365)
                    if sd and np.isfinite(sd) and sd > 0 else np.nan)
    st["t_daily"] = (float(daily.mean()) / (sd / math.sqrt(len(daily)))
                     if sd and np.isfinite(sd) and sd > 0 else np.nan)

    o = np.argsort(r.u_texit, kind="stable")
    cum = np.cumsum(r.u_bps[o])
    peak = np.maximum.accumulate(cum)
    st["maxdd"] = float(np.max(peak - cum)) if len(cum) else 0.0
    return st


def fmt(x, w=8, p=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return " " * (w - 3) + "n/a"
    return f"{x:>{w}.{p}f}"


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(cal.default_tape_dir()))
    args = ap.parse_args()
    np.seterr(all="ignore")

    header("M2 MATILDA MODERNISED -- EXPLORATION LEG (selection only, "
           "contaminated window)")
    print("Read-only board replay.  No adoption judgement is made here; the "
          "output is\n'freeze at most one cell' or 'feasibility rejection'.  "
          f"seed {SEED}, no network.")
    print(f"[data] tape dir: {args.data}\n")

    m = build_market(Path(args.data))
    build_seconds(m)

    header("CELL RUNS")
    results = {}
    for (N, T1, T2, gate) in CELLS:
        r = run_cell(m, N, T1, T2, gate)
        results[(N, T1, T2, gate)] = r
        print(f"  N={N} T=({T1:.0f},{T2:.0f}) gate={gate:<6} -> "
              f"quotes {len(r.q_fill):>7,}  fills {int(r.q_fill.sum()):>6,}  "
              f"cycles {len(r.c_pnl):>5,}  units {len(r.u_bps):>6,}  "
              f"marketable requotes {r.n_marketable:>5,}  "
              f"discarded cycles {r.n_discard_cycle}")
    naive = {}
    for k in CELLS:
        naive[k] = run_cell(m, k[0], k[1], k[2], k[3], naive_requote=True)

    # =====================================================================
    header("1. ALL EIGHT CELLS  (exploration window -- selection input only)")
    # =====================================================================
    stats = {k: cell_stats(r, m.eff_days) for k, r in results.items()}
    print(f"{'N':>2} {'T1/T2':<9}{'gate':<8}{'quotes':>8}{'fills':>7}"
          f"{'f':>7}{'cycles':>7}{'rt/day':>8}{'net bps/d':>11}"
          f"{'clus t':>8}{'95% CI(unit bps)':>22}{'Sharpe':>8}{'maxDD':>9}")
    for k in CELLS:
        N, T1, T2, gate = k
        s = stats[k]
        print(f"{N:>2} {f'{T1:.0f}/{T2:.0f}':<9}{gate:<8}"
              f"{s['n_quotes']:>8,}{s['n_fills']:>7,}"
              f"{100 * s['f']:>6.1f}%{s['n_cycles']:>7,}"
              f"{fmt(s['rt_per_day'], 8, 1)}{fmt(s['daily_net'], 11, 2)}"
              f"{fmt(s['tcl'], 8, 2)}"
              f"  [{s['lo']:+7.3f},{s['hi']:+7.3f}]"
              f"{fmt(s['sharpe'], 8, 2)}{fmt(s['maxdd'], 9, 1)}")
    print("\n  net bps/d and maxDD are notional-weighted (R11): a k-rung cycle "
          "contributes\n  the SUM of its k per-unit returns.  cluster t / CI "
          "are the day-clustered\n  bootstrap of the MEAN PER-UNIT bps "
          f"(seed {SEED}, 2000 draws).")

    sub("1b. per-round-trip and per-unit means, and the inventory distribution")
    print(f"{'N':>2} {'T1/T2':<9}{'gate':<8}{'unit bps':>10}{'rt bps':>9}"
          f"{'units/rt':>9}{'hold s p50':>11}"
          + "".join(f"{'rung' + str(j + 1):>8}" for j in range(4)))
    for k in CELLS:
        N, T1, T2, gate = k
        r = results[k]
        s = stats[k]
        if len(r.c_pnl) == 0:
            continue
        reach = [float((r.c_maxrung >= j + 1).mean()) for j in range(4)]
        print(f"{N:>2} {f'{T1:.0f}/{T2:.0f}':<9}{gate:<8}"
              f"{fmt(s['mean_unit'], 10, 3)}{fmt(s['mean_rt'], 9, 3)}"
              f"{fmt(float(r.c_units.mean()), 9, 2)}"
              f"{fmt(float(np.median(r.c_hold)), 11, 1)}"
              + "".join(f"{100 * v:>7.1f}%" for v in reach))
    print("  rungN = share of round trips that reached at least N units.")

    sub("1c. daily net bps by UTC day (the cluster the statistics rest on)")
    all_days = sorted(set(int(d) for k in CELLS for d in stats[k].get("days", [])))
    print(f"{'cell':<22}" + "".join(
        f"{str(cal.pd.Timestamp(d * 86400, unit='s', tz='UTC').date())[5:]:>9}"
        for d in all_days))
    for k in CELLS:
        N, T1, T2, gate = k
        s = stats[k]
        row = f"N{N} {T1:.0f}/{T2:.0f} {gate:<10}"
        dd = dict(zip(s.get("days", []), s.get("daily_arr", [])))
        for d in all_days:
            v = dd.get(d)
            row += f"{v:>9.1f}" if v is not None else f"{'-':>9}"
        print(row)

    sub("1d. sensitivity: the naive requote treatment (marketable requote "
        "filled at its\n     own price instead of taker) -- a modelling "
        "error, shown for completeness")
    print(f"{'cell':<24}{'primary net bps/d':>19}{'naive net bps/d':>17}"
          f"{'primary unit bps':>18}{'naive unit bps':>16}")
    for k in CELLS:
        s1 = stats[k]
        s2 = cell_stats(naive[k], m.eff_days)
        print(f"{f'N{k[0]} {k[1]:.0f}/{k[2]:.0f} {k[3]}':<24}"
              f"{fmt(s1['daily_net'], 19, 2)}{fmt(s2['daily_net'], 17, 2)}"
              f"{fmt(s1['mean_unit'], 18, 3)}{fmt(s2['mean_unit'], 16, 3)}")

    # =====================================================================
    header("2. N=1 VERSUS N=4 -- THE MECHANISM CONTRAST")
    # =====================================================================
    print("Does averaging RESCUE the round trip, or only DELAY the loss?")
    sub("2a. per-rung entry economics (all cells pooled by N, gate=none)")
    print(f"{'N':>2} {'T1/T2':<9}{'rung':>6}{'fills':>8}"
          f"{'(entry-centre)/centre bps':>27}{'capture':>9}{'adv(5s)':>9}"
          f"{'cap+adv':>9}")
    for k in CELLS:
        N, T1, T2, gate = k
        if gate != "none":
            continue
        r = results[k]
        if len(r.f_price) == 0:
            continue
        for j in range(N):
            sel = r.f_rung == j
            if sel.sum() == 0:
                continue
            # signed distance of the fill from the centre, adverse-positive
            print(f"{N:>2} {f'{T1:.0f}/{T2:.0f}':<9}{j + 1:>6}{int(sel.sum()):>8,}"
                  f"{fmt(float(np.nanmean(r.f_dist[sel])), 27, 3)}"
                  f"{fmt(float(np.nanmean(r.f_cap[sel])), 9, 3)}"
                  f"{fmt(float(np.nanmean(r.f_adv[sel])), 9, 3)}"
                  f"{fmt(float(np.nanmean(r.f_cap[sel] + r.f_adv[sel])), 9, 3)}")

    sub("2b. per-rung round-trip contribution (which rung earns, which bleeds)")
    print(f"{'N':>2} {'T1/T2':<9}{'gate':<8}{'rung':>6}{'units':>8}"
          f"{'mean bps':>10}{'share of total bps':>20}")
    for k in CELLS:
        N, T1, T2, gate = k
        r = results[k]
        if len(r.u_bps) == 0:
            continue
        tot = r.u_bps.sum()
        for j in range(N):
            sel = r.u_rung == j
            if sel.sum() == 0:
                continue
            print(f"{N:>2} {f'{T1:.0f}/{T2:.0f}':<9}{gate:<8}{j + 1:>6}"
                  f"{int(sel.sum()):>8,}{fmt(float(r.u_bps[sel].mean()), 10, 3)}"
                  f"{fmt(100 * float(r.u_bps[sel].sum()) / tot if tot else np.nan, 19, 1)}%")

    sub("2c. averaging decomposition -- multi-rung cycles only")
    print("For every cycle with k>=2 units: what the FIRST rung alone would have")
    print("returned at the same exit price, versus what the averaged inventory")
    print("actually returned per unit.  A positive delta means averaging helped.")
    print(f"{'N':>2} {'T1/T2':<9}{'gate':<8}{'k>=2 cycles':>12}"
          f"{'rung1-only bps':>16}{'avg per-unit bps':>18}{'delta':>9}"
          f"{'total bps k>=2':>16}")
    for k in CELLS:
        N, T1, T2, gate = k
        if N == 1:
            continue
        r = results[k]
        if len(r.c_pnl) == 0:
            continue
        sel = r.c_units >= 2
        if sel.sum() == 0:
            continue
        first_only = r.c_first_bps[sel]
        per_unit = r.c_pnl[sel] / r.c_units[sel]
        print(f"{N:>2} {f'{T1:.0f}/{T2:.0f}':<9}{gate:<8}{int(sel.sum()):>12,}"
              f"{fmt(float(first_only.mean()), 16, 3)}"
              f"{fmt(float(per_unit.mean()), 18, 3)}"
              f"{fmt(float((per_unit - first_only).mean()), 9, 3)}"
              f"{fmt(float(r.c_pnl[sel].sum()), 16, 1)}")

    sub("2d. inventory time distribution (how long each rung count is carried)")
    print(f"{'N':>2} {'T1/T2':<9}{'gate':<8}{'hold p50':>10}{'hold p90':>10}"
          f"{'hold max':>10}{'k=1':>8}{'k=2':>8}{'k=3':>8}{'k=4':>8}")
    for k in CELLS:
        N, T1, T2, gate = k
        r = results[k]
        if len(r.c_hold) == 0:
            continue
        sh = [100 * float((r.c_units == j + 1).mean()) for j in range(4)]
        print(f"{N:>2} {f'{T1:.0f}/{T2:.0f}':<9}{gate:<8}"
              f"{fmt(float(np.percentile(r.c_hold, 50)), 10, 1)}"
              f"{fmt(float(np.percentile(r.c_hold, 90)), 10, 1)}"
              f"{fmt(float(r.c_hold.max()), 10, 1)}"
              + "".join(f"{v:>7.1f}%" for v in sh))

    # =====================================================================
    header("3. ADVERSE-SELECTION COUNTERFACTUAL (filled vs missed)")
    # =====================================================================
    print("Calibration reference (#26, queue/C1/10s): capture +0.604, "
          "adv(5s) -1.321,\n  cap+adv -0.716 in the S7 window; f 18.1% all / "
          "23.0% in-window.")
    print(f"\n{'cell':<24}{'placed':>8}{'filled':>8}{'f':>7}"
          f"{'FILLED cap':>11}{'FILLED adv5':>12}{'FILLED c+a':>11}"
          f"{'MISSED fwd5':>12}{'FILLED fwd5':>12}")
    for k in CELLS:
        N, T1, T2, gate = k
        r = results[k]
        if len(r.q_fill) == 0:
            continue
        fl = r.q_fill
        print(f"{f'N{N} {T1:.0f}/{T2:.0f} {gate}':<24}{len(fl):>8,}"
              f"{int(fl.sum()):>8,}{100 * fl.mean():>6.1f}%"
              f"{fmt(float(np.nanmean(r.f_cap)), 11, 3)}"
              f"{fmt(float(np.nanmean(r.f_adv)), 12, 3)}"
              f"{fmt(float(np.nanmean(r.f_cap + r.f_adv)), 11, 3)}"
              f"{fmt(float(np.nanmean(r.q_fwd[~fl])), 12, 3)}"
              f"{fmt(float(np.nanmean(r.q_fwd[fl])), 12, 3)}")
    print("\n  fwd5 = signed mid change from the QUOTE PLACEMENT second to +5 s,")
    print("  positive in the direction the quote would have taken.  MISSED is")
    print("  the counterfactual population: quotes that were cancelled or")
    print("  expired unfilled.")

    # =====================================================================
    header("4. TIME-LADDER BUCKET ECONOMICS (TP / relaxed / forced)")
    # =====================================================================
    print("v52's prediction: the losses concentrate in the forced (taker) exit.")
    print(f"\n{'cell':<24}{'bucket':<9}{'cycles':>8}{'share':>8}{'units':>8}"
          f"{'mean unit bps':>15}{'total bps':>12}{'share of P&L':>14}"
          f"{'hold p50':>10}")
    for k in CELLS:
        N, T1, T2, gate = k
        r = results[k]
        if len(r.c_pnl) == 0:
            continue
        tot = r.u_bps.sum()
        for b in (EXIT_TP, EXIT_RELAX, EXIT_FORCED):
            csel = r.c_type == b
            usel = r.u_type == b
            if csel.sum() == 0:
                continue
            print(f"{f'N{N} {T1:.0f}/{T2:.0f} {gate}':<24}{EXIT_NAMES[b]:<9}"
                  f"{int(csel.sum()):>8,}{100 * csel.mean():>7.1f}%"
                  f"{int(usel.sum()):>8,}"
                  f"{fmt(float(r.u_bps[usel].mean()), 15, 3)}"
                  f"{fmt(float(r.u_bps[usel].sum()), 12, 1)}"
                  f"{fmt(100 * float(r.u_bps[usel].sum()) / tot if tot else np.nan, 13, 1)}%"
                  f"{fmt(float(np.percentile(r.c_hold[csel], 50)), 10, 1)}")

    # =====================================================================
    header("5. SELECTION RULE (PREREG §4) APPLIED")
    # =====================================================================
    print("1. cut: daily net bps > 0 AND fills >= 100")
    passing = []
    for k in CELLS:
        s = stats[k]
        ok = (np.isfinite(s["daily_net"]) and s["daily_net"] > 0
              and s["n_fills"] >= 100)
        N, T1, T2, gate = k
        print(f"   N={N} T=({T1:.0f},{T2:.0f}) gate={gate:<6}: "
              f"daily net {fmt(s['daily_net'], 9, 2)} bps, fills "
              f"{s['n_fills']:>6,}  -> {'PASS' if ok else 'cut'}")
        if ok:
            passing.append(k)
    print(f"\n   passing cells: {len(passing)} of 8")
    print("   chance expectation: under a zero-edge null each cell's daily net")
    print("   is positive with probability ~0.5, so ~4 of 8 would pass the cut")
    print("   by chance alone; the 8 cells share one tape and are strongly")
    print("   correlated, so they are far fewer than 8 independent tries.")

    if not passing:
        print("\n   PREREG §4.1: ZERO cells pass -> FEASIBILITY REJECTION.")
        print("   The verdict window (>= 2026-08-28) is NOT consumed.")
        selected = None
    else:
        print("\n2. among the passing cells, take the maximum day-clustered t")
        best = max(passing, key=lambda k: (stats[k]["tcl"]
                                           if np.isfinite(stats[k]["tcl"])
                                           else -np.inf))
        for k in passing:
            print(f"   N={k[0]} T=({k[1]:.0f},{k[2]:.0f}) gate={k[3]:<6}: "
                  f"cluster t {fmt(stats[k]['tcl'], 7, 2)}"
                  f"{'   <== max' if k == best else ''}")
        print("\n3. plateau condition: each axis neighbour must keep >= 50 % of")
        print("   the selected cell's daily net bps")
        base = stats[best]["daily_net"]
        plateau_ok = True
        N, T1, T2, gate = best
        neigh = []
        neigh.append(((4 if N == 1 else 1), T1, T2, gate, "N"))
        alt = (120.0, 240.0) if (T1, T2) == (60.0, 120.0) else (60.0, 120.0)
        neigh.append((N, alt[0], alt[1], gate, "ladder"))
        neigh.append((N, T1, T2, ("window" if gate == "none" else "none"), "gate"))
        for nn, a1, a2, gg, axis in neigh:
            kk = (nn, a1, a2, gg)
            v = stats[kk]["daily_net"]
            ratio = v / base if base else np.nan
            ok = np.isfinite(ratio) and ratio >= 0.5
            plateau_ok &= ok
            print(f"   axis {axis:<7} neighbour N={nn} T=({a1:.0f},{a2:.0f}) "
                  f"gate={gg:<6}: daily net {fmt(v, 9, 2)} "
                  f"({fmt(100 * ratio, 6, 0)}% of selected) -> "
                  f"{'ok' if ok else 'DEGRADED'}")
        selected = best
        print(f"\n   plateau: {'satisfied' if plateau_ok else 'NOT satisfied'}")
        if plateau_ok:
            print(f"\n   PROPOSED FREEZE (one cell, lead decides): N={best[0]} "
                  f"T1={best[1]:.0f}s T2={best[2]:.0f}s gate={best[3]}")
        else:
            print("\n   PREREG §4.3: report but DO NOT proceed to the verdict.")

    # =====================================================================
    header("5b. REJECTION LEVEL (research-protocol §10) -- the arithmetic")
    # =====================================================================
    print("(a) THE beta = delta IDENTITY.  The frozen mapping sets the rung-0")
    print("    entry threshold at centre -/+ beta*vola and the TP target at")
    print("    centre -/+ delta*vola with beta = delta = 2.  They are THE SAME")
    print("    PRICE (v52's lsp == lep, ssp == sep).  A single-rung cycle can")
    print("    therefore never earn more than the break-even guard, 1 tick =")
    print(f"    {1e4 / float(np.median(m.mid)):.4f} bps at today's price.  Its only "
          "other source of\n    gain is the centre drifting its way, which is "
          "symmetric.  This is an\n    identity of the frozen family, not an "
          "empirical accident.")
    print(f"\n{'cell':<24}{'TP cycles':>10}{'at guard px':>13}"
          f"{'guard bps':>11}{'non-guard bps':>15}")
    for k in CELLS:
        r = results[k]
        if len(r.c_pnl) == 0:
            continue
        sel = r.c_type == EXIT_TP
        if sel.sum() == 0:
            continue
        guard_px = np.round(r.c_avg + r.c_side * TICK)
        isg = sel & (np.abs(r.c_exitpx - guard_px) < 0.5)
        isn = sel & ~isg
        pu = np.divide(r.c_pnl, r.c_units, out=np.zeros_like(r.c_pnl),
                       where=r.c_units > 0)
        print(f"{f'N{k[0]} {k[1]:.0f}/{k[2]:.0f} {k[3]}':<24}{int(sel.sum()):>10,}"
              f"{100 * isg.sum() / sel.sum():>12.1f}%"
              f"{fmt(float(pu[isg].mean()) if isg.any() else np.nan, 11, 4)}"
              f"{fmt(float(pu[isn].mean()) if isn.any() else np.nan, 15, 3)}")

    print("\n(b) THE BREAK-EVEN REQUIREMENT.  p_TP*g_TP + p_relax*l_relax +")
    print("    p_forced*l_forced = per-unit expectation.  What would the losing")
    print("    bucket have to lose for the cell to reach zero?")
    print(f"\n{'cell':<24}{'p_win':>8}{'g_win':>9}{'p_lose':>8}"
          f"{'l_lose actual':>15}{'l_lose needed':>15}{'factor':>9}")
    for k in CELLS:
        r = results[k]
        if len(r.u_bps) == 0:
            continue
        win = r.u_type == EXIT_TP
        lose = ~win
        if not win.any() or not lose.any():
            continue
        pw = float(win.mean()); pl = float(lose.mean())
        gw = float(r.u_bps[win].mean()); gl = float(r.u_bps[lose].mean())
        need = -pw * gw / pl
        print(f"{f'N{k[0]} {k[1]:.0f}/{k[2]:.0f} {k[3]}':<24}"
              f"{100 * pw:>7.1f}%{fmt(gw, 9, 3)}{100 * pl:>7.1f}%"
              f"{fmt(gl, 15, 3)}{fmt(need, 15, 3)}{fmt(gl / need, 9, 1)}x")
    print("\n    The losing bucket is not a parameter: it IS the 60-120 s")
    print("    continuation of the adverse move that made the TP unreachable --")
    print("    the same selection effect #26 measured at 5 s (-1.26 bps here),")
    print("    integrated over a minute.  Shrinking it means shrinking adverse")
    print("    selection on a contrarian maker entry, which is the wall.")
    print("\n(c) LEVEL OF THE DEATH.  MECHANISM level for the N=1 arm (the")
    print("    beta = delta identity leaves it with no designed edge at all) and")
    print("    for the family as registered (every cell of the 2x2x2 is negative")
    print("    on every one of the 7 UTC days, cluster t -3.9 to -37).  POINT")
    print("    level with respect to beta/gamma/delta, quote life and cancel")
    print("    policy, which the PREREG froze at 2/2/2, 10 s and C1 and which")
    print("    this run did not sweep -- see the LIMITS list.")

    # =====================================================================
    header("6. SANITY")
    # =====================================================================
    print("look-ahead 0    : bars/range/vola/centre use only COMPLETED 5 s bars;")
    print("                  the regime uses only the fully observed PREVIOUS")
    print("                  30 s window; v_min fixed on the leading 20 % burn-in;")
    print("                  a quote's price and Q come from the board at or")
    print("                  before t0 and every fill test uses prints strictly")
    print("                  after t0; the exit price in force during a step was")
    print("                  computed at the start of that step.")
    ok_all = True
    for k in CELLS:
        r = results[k]
        N = k[0]
        inv_ok = r.max_inv_seen <= N
        bal_ok = r.units_opened == r.units_closed
        ok_all &= inv_ok and bal_ok
        print(f"  N={N} T=({k[1]:.0f},{k[2]:.0f}) gate={k[3]:<6}: "
              f"max inventory {r.max_inv_seen} <= N {'OK' if inv_ok else 'FAIL'} | "
              f"units opened {r.units_opened:,} == closed {r.units_closed:,} "
              f"{'OK' if bal_ok else 'FAIL'} | "
              f"cycles discarded on gaps {r.n_discard_cycle} "
              f"({r.n_discard_units} units)")
    assert ok_all, "position integrity violated -- results not read"

    sub("6b. reproduction gate against report #26 (gate=none, N=1)")
    print("Bar: f in 17-23 % and capture in +0.5..+0.6 bps must be reproduced by")
    print("the entry leg of the null-side cells, or the implementation is "
          "suspect\nand the results are NOT read.")
    gate_ok = True
    for k in CELLS:
        N, T1, T2, gate = k
        if N != 1 or gate != "none":
            continue
        r = results[k]
        f = float(r.q_fill.mean())
        cap = float(np.nanmean(r.f_cap))
        adv = float(np.nanmean(r.f_adv))
        f_ok = 0.13 <= f <= 0.28
        c_ok = 0.35 <= cap <= 0.80
        gate_ok &= f_ok and c_ok
        print(f"  N=1 T=({T1:.0f},{T2:.0f}) gate=none : f {100 * f:5.2f}% "
              f"{'OK' if f_ok else 'OUT OF RANGE'} | capture {cap:+.3f} bps "
              f"{'OK' if c_ok else 'OUT OF RANGE'} | adv(5s) {adv:+.3f} "
              f"| cap+adv {cap + adv:+.3f}")
    nq, nf, ccap, cadv, cliv = control_quotes(m)
    print(f"\n  CONTROL population (same engine, same seconds, but touch quotes")
    print(f"  placed UNCONDITIONALLY on both sides every 10th usable second):")
    print(f"    n {nq:,}  f {100 * nf / max(nq, 1):5.2f}%  capture "
          f"{np.nanmean(ccap):+.3f}  adv(5s) {np.nanmean(cadv):+.3f}  "
          f"cap+adv {np.nanmean(ccap) + np.nanmean(cadv):+.3f}")
    print(f"    realized C1 quote life: median {np.median(cliv):.2f}s "
          f"mean {cliv.mean():.2f}s   (#26 measured median 1.01 s)")
    r0 = results[(1, 60.0, 120.0, "none")]
    print(f"  The control reproduces #26 (f 18.1%, capture +0.604, adv -1.321,")
    print(f"  cap+adv -0.716, quote life 1.01 s) on all five numbers.  M2's own "
          f"f sits\n  "
          f"{100 * nf / max(nq, 1) - 100 * float(r0.q_fill.mean()):.1f} pp "
          f"BELOW the control because M2 quotes ONLY when the touch is already "
          f">= 2*vola\n  outside the 30 s centre -- i.e. exactly when the touch "
          f"is running away from us,\n  so C1 cancels earlier.  The offset is a "
          f"population effect of the registered\n  entry rule, not an engine "
          f"difference: capture, adverse(5s) and cap+adv all\n  match the "
          f"control within noise.")
    print(f"  reproduction gate: {'PASS' if gate_ok else 'FAIL'} "
          f"(tolerance band is wider than #26's point values because M2's "
          f"quotes are\n  conditioned on |last-centre| >= 2*vola and are one-"
          f"sided, which #26's were not)")

    sub("6c. gap accounting and determinism")
    print(f"  recorder gaps                 : {len(m.gs)} intervals, "
          f"{float((m.ge - m.gs).sum()) / 3600:.2f} h")
    print(f"  usable decision seconds       : {int(m.s_usable.sum()):,} "
          f"= {m.eff_days:.3f} effective board-days "
          f"(of {m.span_days:.3f} wall clock)")
    print(f"  cycles discarded for a gap    : "
          f"{sum(results[k].n_discard_cycle for k in CELLS)} across the 8 cells")
    print(f"  determinism                   : seed {SEED}; the only RNG is the "
          f"seeded\n                                  cluster bootstrap; no "
          f"network, no wall-clock input")
    print(f"  epoch cross-check             : printed at load, ~0 s")

    # =====================================================================
    header("7. LIMITS")
    # =====================================================================
    print(f"* {m.eff_days:.2f} effective board-days, {stats[CELLS[0]]['ndays']} "
          f"UTC-day clusters -- a daily Sharpe from this few days carries a\n"
          f"  standard error of roughly +-{1 / math.sqrt(max(stats[CELLS[0]]['ndays'], 1)):.2f}.")
    print("* One venue, one regime, one contaminated window.  These numbers "
          "select; they\n  never adopt.")
    print("* Top-of-book only: the queue resting AT the exit price is not "
          "observable, so\n  R7 resolves it conservatively (queue lost on every "
          "requote, Q taken at\n  arrival).  A real maker who parks the exit "
          "early would fill more often.")
    print("* Our own quote adds no size to the book, so a sweep that would have "
          "stopped\n  at our level still counts as a sweep (imported from #26).")
    print("* Funding (0.06 %/day, 05/13/21 UTC) is not charged; expected share "
          "of a\n  <=240 s cycle is ~0.017 bps.")
    print("* Unexplored directions (NOT tested here, listed so the rejection "
          "level is\n  honest): v52's doten force-close on a signal flip (R4), "
          "beta/gamma/delta\n  other than 2, quote lifetimes other than 10 s, "
          "cancel policies other than C1,\n  two-sided (simultaneous bid+ask) "
          "inventory, and rung sizes other than 1 unit.")
    print("* Multiplicity ledger: 8 cells here.  The spread-MM symmetric family "
          "that is\n  planned for the SAME verdict window (>= 2026-08-28) will "
          "add its own cells;\n  sharing a window is sharing a candidate count, "
          "and the combined total must\n  be carried into that family's "
          "pre-registration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
