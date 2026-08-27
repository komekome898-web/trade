#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 FINE-GRAINED LEVEL CHECK -- the top M4 surface cells re-measured on the
second-by-second bitFlyer replay (M3 engine, extended).

EXPLORATION ONLY.  Every byte read here is contaminated (reports 26/27/29/30
and the M4 surface already read this week).  The only permitted outputs are
(1) a level measurement of already-chosen cells and (2) at most a PROPOSAL to
the lead.  No freeze, no adoption, no verdict.  The VERDICT window
(>= 2026-08-28) is not touched by a single byte in this file.

================================================================================
TASK -- transcribed verbatim from the lead's instruction
================================================================================

あなたは /home/user/trade リポジトリの研究エージェントです。着手前に必読:
scripts/research_matilda_surface.py(M4面探索 — 上位セルの定義)、
scripts/research_matilda_taro.py(**細粒度リプレイエンジン — これを改修して使う**)、
直近の M4 面探索の帰結(次段落)、docs/RESEARCH_REPORT_2026-08-28ae.md、
.claude/skills/research-protocol/SKILL.md §10。

【背景】
M4 面探索(210日1分足プロキシ、51セル)は全セル負で終わったが、限界として
「candle近似は細粒度比 約2.2bps/unit 悲観(第30報の同一セル実測: 細粒度 −0.395 vs
近似 −2.597)。最良セル群はバイアスと同オーダーでゼロに近く、**水準は本測定では
決まらない**」と明記された。本タスクはその水準決定: **上位セルを細粒度リプレイで
再測する**。

【対象セル(5つ。追加しない)】
基底は M3 細粒度エンジン(ブレイクOFF・ラダー(40,80)分・entry band 2.0×vola・
1分足40分窓)に、M4 の該当変更を加える:
1. flat w=1.2 / N=10 / 等間隔1.5×vola / **嵐後刈り取りH=2h**(M4最良)
2. flat w=1.2 / N=10 / 等間隔1.5 / 刈り取りH=6h
3. flat w=1.2 / N=10 / 等間隔1.5 / 嵐ゲートなし
4. flat w=1.6 / N=10 / 等間隔1.5 / 刈り取りH=2h
5. (参照・バイアス測定用)app w=0.8 / N=7 / 等間隔1.0 / ゲートなし = M3細粒度の
   既測セル(−0.395)の再現 + 追加でファンディング課金版
仕様: flat = TP幅 w×vola を全在庫平均建値から(按分しない)。等間隔1.5 = グリッド
間隔1.5×vola。刈り取り = 因果的嵐フラグ(|30分リターン|≥0.8%、完結バー)終了
(30分連続OFF)後 H 時間のみ新規エントリ許可(決済は常時)。ファンディング
0.06%/日を保有按分で課金。

【データ】data/tape/ の ticker+executions+board_top5(2026-08-20〜27、汚染済み)。
M3 と同じギャップ規律(厳格マスク主・緩和マスク感度併記)。**判定区間(≥8/28)には
触れない。**

【実装】scripts/research_matilda_taro.py の状態機械を import/拡張した
`scripts/research_m4_finecheck.py`(docstring に本指示逐語、seed 20260829、
決定性2回一致、read-only)。**再現ゲート**: セル5(ファンディングなし版)が第30報の
−0.395 [−1.24,+0.25] を trade-for-trade で再現すること — 破れたら数値を読まずに停止。

【必須報告】
1. 5セル表: 往復・往復/日・unit bps・日次クラスタt/95%CI・maxDD・出口内訳・
   在庫分布(厳格/緩和マスク併記)
2. **candle近似バイアスの実測**: 同一セルの 細粒度 vs 1分足近似(M4実装で同週を回す)
   の差 — 2.2bps仮説の検証、セル別のバイアス
3. 嵐後刈り取りセルの n(4.6実効日で往復数が薄いはず — CI幅を正直に)
4. 逆選択・capture(校正との整合)
5. サニティ: ルックアヘッド0・在庫≤N・建玉整合・決定性・再現ゲート
6. **結論**: 細粒度水準で 点推定>0 かつ CI が意味を持つセルはあるか。あれば M4 凍結
   候補としての適格性(§10: 台地・多重性57セル台帳込み)をリードに提案、なければ
   「水準でも負」と書く
【規律】陰性は陰性のまま。凍結はリード。setsid nohup(scratchpad)。モデル名なし。
Do not commit / push.

================================================================================
WHAT THIS SCRIPT DOES
================================================================================
The M3 fine-grained replay (scripts/research_matilda_taro.py, report 30) is a
second-by-second state machine over the real tape: prints fill resting limit
orders through a queue-realistic model inside board_top5 and a strictly-through
model below it; the 1-minute indicator bar it reads is always the COMPLETED
previous minute.  Its constants are frozen v37 (apportioned TP, N=7, uniform
1.0*vola grid, no storm clock, no funding).

`run_cell_fine` below is that machine generalised over exactly the four M4 axes
(apportionment/TP width, rung count, grid spacing, storm clock) plus funding.
Everything else -- order placement order, requote rule, taker-requote
accounting, cancel policy (R8 literal), queue arrival at the end of the second,
gap discipline, cycle discard -- is carried over verbatim.  The reproduction
gate in section 0 asserts trade-for-trade identity with M3.run_cell on the base
configuration before any other number is computed; if it fails the script exits
without printing a single cell result.

COSTS: maker entry 0 bps; taker exit 3.96 bps (burst level, KNOWLEDGE 1);
funding 0.06 %/day pro-rated per unit from its own fill to the cycle exit,
charged as a cost on both sides (conservative).

Usage: PYTHONPATH=src python scripts/research_m4_finecheck.py
"""
from __future__ import annotations

import argparse
import hashlib
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import research_board_calibration as cal      # noqa: E402
import research_matilda_taro as M3            # noqa: E402  (fine engine)
import research_matilda_surface as M4         # noqa: E402  (M4 axes + bars)

SEED = 20260829

TAKER_BPS = M3.TAKER_BPS
MAX_RUNG_HARD = 10
INF = float("inf")

# report 30, section 1, cell "break=OFF T=(40,80)"
REPORT30_UNIT = -0.395
REPORT30_LO = -1.243
REPORT30_HI = 0.246

K_TP, K_RELAX, K_T2, K_FLIP, K_BDUMP = 0, 1, 2, 3, 4
KIND_NAMES = M3.KIND_NAMES

Cfg = M4.Cfg                    # frozen dataclass, reused unchanged
FUND = M4.FUNDING_BPS_DAY       # 6.0 bps/day

BASE = dict(brk_on=False, T1m=40.0, T2m=80.0)

CELLS = [
    ("1", Cfg(N=10, apportion=False, w=1.2, spacing=("uniform", 1.5),
              storm=("harvest", 2.0), funding=FUND, **BASE)),
    ("2", Cfg(N=10, apportion=False, w=1.2, spacing=("uniform", 1.5),
              storm=("harvest", 6.0), funding=FUND, **BASE)),
    ("3", Cfg(N=10, apportion=False, w=1.2, spacing=("uniform", 1.5),
              storm=("none", 0.0), funding=FUND, **BASE)),
    ("4", Cfg(N=10, apportion=False, w=1.6, spacing=("uniform", 1.5),
              storm=("harvest", 2.0), funding=FUND, **BASE)),
    ("5a", Cfg(N=7, apportion=True, w=0.8, spacing=("uniform", 1.0),
               storm=("none", 0.0), funding=0.0, **BASE)),
    ("5b", Cfg(N=7, apportion=True, w=0.8, spacing=("uniform", 1.0),
               storm=("none", 0.0), funding=FUND, **BASE)),
]
GATE_CFG = CELLS[4][1]


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


def cname(tag, cfg: Cfg) -> str:
    return f"{tag}. {cfg.name()}" + ("" if cfg.funding else " [no funding]")


# ===========================================================================
# storm clock  (identical recipe to M4._indicators; asserted in section 0)
# ===========================================================================
def storm_clock(close: np.ndarray, blind: np.ndarray | None = None):
    """Causal storm flag and 'minutes since the last storm end'.

    storm[i]   = |log close[i] - log close[i-30]| >= 0.8 %
    a storm ENDS after 30 consecutive OFF minutes; age[i] = i - end index
    (-1 before the first end).  Both are read only through the COMPLETED bar.

    `blind` (optional) marks bars whose 30-minute return window is not
    trustworthy (it straddles a recorder outage, so the flat forward-filled
    closes fake a calm).  Blind bars can neither raise a storm nor advance the
    OFF run that ends one; they freeze the clock.  Used only as a sensitivity.
    """
    n = len(close)
    logc = np.log(close)
    storm = np.zeros(n, bool)
    storm[M4.STORM_WIN:] = np.abs(
        logc[M4.STORM_WIN:] - logc[:-M4.STORM_WIN]) >= M4.STORM_THR
    if blind is not None:
        storm &= ~blind
    age = np.full(n, -1, int)
    run = 0
    seen = False
    end_at = -1
    for i in range(n):
        if blind is not None and blind[i]:
            pass                                  # clock frozen
        elif storm[i]:
            run = 0
            seen = True
        else:
            run += 1
            if run == M4.STORM_OFF_RUN and seen:
                end_at = i
        age[i] = (i - end_at) if end_at >= 0 else -1
    return storm, age


def gap_blind_bars(m) -> np.ndarray:
    """Bars whose 30-minute return window touches a recorder gap."""
    bar_start = (np.arange(m.nb) + m.b0) * float(M3.BAR_SEC)
    lo = bar_start - (M4.STORM_WIN - 1) * M3.BAR_SEC
    hi = bar_start + M3.BAR_SEC
    return cal.span_touches_gap(lo, hi, m.gs, m.ge)


# ===========================================================================
# the generalised fine-grained state machine  (M3.run_cell + the M4 axes)
# ===========================================================================
def run_cell_fine(m, cfg: Cfg, storm=None, age=None,
                  relaxed_gaps: bool = False):
    """M3.run_cell generalised over the M4 axes.

    Differences from M3.run_cell, and NOTHING else:
      * MAX_RUNGS      -> cfg.N
      * STEP_MULT      -> M4.step_mult(cfg, rung)          (grid geometry)
      * EXIT_MULT/k    -> cfg.w * (1/k if cfg.apportion)   (TP width)
      * break mode     -> cfg.brk_on ; ladder -> cfg.T1m, cfg.T2m
      * funding        -> cfg.funding bps/day, pro-rated per unit
      * storm harvest  -> entries (and therefore flips) suppressed unless the
                          completed bar is within H hours of a storm end
    """
    NMAX = cfg.N
    T1 = cfg.T1m * 60.0
    T2 = cfg.T2m * 60.0
    fund_per_sec = cfg.funding / 86400.0
    st_kind, st_h = cfg.storm
    do_harv = (st_kind == "harvest")
    harv_bars = int(round(st_h * 60.0))
    if storm is None:
        storm, age = m.storm, m.storm_age

    secs = m.secs.tolist()
    usable = (m.s_usable_relaxed if relaxed_gaps else m.s_usable).tolist()
    s_bid = m.s_bid.tolist(); s_ask = m.s_ask.tolist(); s_mid = m.s_mid.tolist()
    ex_lo = m.ex_lo.tolist(); ex_hi = m.ex_hi.tolist()
    t_ex = m.t_ex.tolist(); e_px = m.px.tolist()
    e_sz = m.sz.tolist(); e_buy = m.buy.tolist()
    jb = m.jb.tolist(); ib = m.ib.tolist()
    B = {k: (v.tolist() if isinstance(v, np.ndarray) else v)
         for k, v in m.bar.items()}
    st_l = storm.tolist(); age_l = age.tolist()
    bpx, bbz, apx, abz = m.bpx, m.bbz, m.apx, m.abz
    bpx5, apx5 = m.bpx5, m.apx5

    p_t0, p_px, p_side, p_mode, p_rung, p_fill = [], [], [], [], [], []
    f_t, f_px, f_side, f_rung, f_mode = [], [], [], [], []
    c_t0, c_tx, c_k, c_mode, c_ever, c_kind, c_taker = [], [], [], [], [], [], []
    c_pnl, c_gross, c_avg, c_xpx, c_side, c_vola, c_supp, c_reg = \
        [], [], [], [], [], [], [], []
    u_bps, u_gross, u_day, u_tx, u_rung, u_kind, u_k, u_mode, u_reg = \
        [], [], [], [], [], [], [], [], []

    inv_px: list[float] = []
    inv_rung: list[int] = []
    inv_t: list[float] = []
    side = 0
    t_first = INF
    avg = 0.0
    orders: list[M3.Order] = []
    xo = None
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
    cyc_reg = 0

    n_break_up = n_break_dn = n_break_off = 0
    n_discard_cyc = n_discard_units = 0
    n_marketable = 0
    n_supp_seconds = 0
    units_opened = units_closed = 0
    max_inv = 0
    break_seconds = 0
    n_entry_sec = n_gate_storm = 0
    n_harv_open = 0
    fund_tot = 0.0
    hold_tot = 0.0

    def retire(o, filled: bool):
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
        nonlocal side, t_first, inv_px, inv_rung, inv_t, avg, units_closed
        nonlocal cyc_ever, cyc_supp, cyc_mode, cyc_vola, fund_tot, hold_tot
        k = len(inv_px)
        tot = 0.0
        gro = 0.0
        day = int(math.floor(t / 86400.0))
        for e, rg, te in zip(inv_px, inv_rung, inv_t):
            g = side * (xpx - e) / e * 1e4
            hold = max(t - te, 0.0)
            f = fund_per_sec * hold
            fund_tot += f
            hold_tot += hold
            b = g - f
            tot += b
            gro += g
            u_bps.append(b); u_gross.append(g); u_day.append(day)
            u_tx.append(t); u_rung.append(rg); u_kind.append(kind)
            u_k.append(k); u_mode.append(cyc_mode); u_reg.append(cyc_reg)
        c_t0.append(t_first); c_tx.append(t); c_k.append(k)
        c_mode.append(cyc_mode); c_ever.append(1 if cyc_ever else 0)
        c_kind.append(kind); c_taker.append(1 if taker else 0)
        c_pnl.append(tot); c_gross.append(gro); c_avg.append(avg)
        c_xpx.append(xpx); c_side.append(side); c_vola.append(cyc_vola)
        c_supp.append(1 if cyc_supp else 0); c_reg.append(cyc_reg)
        units_closed += k
        inv_px = []; inv_rung = []; inv_t = []
        side = 0
        t_first = INF
        avg = 0.0
        cyc_ever = False
        cyc_supp = False
        cancel_all()

    def discard_cycle():
        nonlocal side, t_first, inv_px, inv_rung, inv_t, avg, units_opened
        nonlocal n_discard_cyc, n_discard_units, cyc_ever, cyc_supp
        n_discard_cyc += 1
        n_discard_units += len(inv_px)
        units_opened -= len(inv_px)
        inv_px = []; inv_rung = []; inv_t = []
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
                            q0 = jb[i]
                            a0 = age_l[q0]
                            cyc_reg = (M4.R_STORM if st_l[q0] else
                                       M4.R_P2 if (0 <= a0 <= 120) else
                                       M4.R_P26 if (120 < a0 <= 360) else
                                       M4.R_NORM)
                        if o.mode == 1:
                            cyc_ever = True
                        inv_px.append(o.price)
                        inv_rung.append(o.rung)
                        inv_t.append(tv)
                        avg = sum(inv_px) / len(inv_px)
                        units_opened += 1
                        max_inv = max(max_inv, len(inv_px))
                        assert len(inv_px) <= NMAX, "inventory cap"
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
        a_now = age_l[j]
        harv_ok = (not do_harv) or (0 <= a_now <= harv_bars)
        if harv_ok:
            n_harv_open += 1

        # ---------------- 3. break_judge (inside ently_judge) --------------
        if cfg.brk_on:
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
            if rw_bps < M3.RANGE_MIN_BPS or rw_bps > M3.RANGE_MAX_BPS:
                e_flg = 0
            elif last > centre + M3.ENTRY_MULT * vola:
                e_flg = -1
            elif last < centre - M3.ENTRY_MULT * vola:
                e_flg = 1
            else:
                e_flg = 0
        else:
            if break_flg == -b_signal or (b_signal == 0 and side == 0):
                e_flg = 0
            else:
                e_flg = break_flg

        if e_flg != 0:
            n_entry_sec += 1
        if not harv_ok:
            if e_flg != 0:
                n_gate_storm += 1
            e_flg = 0

        k = len(inv_px)
        # ---------------- 5. entry order management ------------------------
        if e_flg == 1:
            if n_s != 0 and k == 0:
                cancel_all()
            if k < NMAX:
                if side > 0 and n_b == 0:
                    anchor_b = avg
                    n_b += k
                if n_b < NMAX:
                    sm = M4.step_mult(cfg, n_b) * vola
                    cap = bb
                    if break_flg == 0:
                        cap = min(cap, centre - M3.ENTRY_MULT * vola)
                    cap = min(cap, anchor_b - sm - 1e-9)
                    price = math.floor(cap)
                    if price > 0 and price < anchor_b - sm:
                        o = M3.Order(float(price), True, s, n_b,
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
            if k < NMAX:
                if side < 0 and n_s == 0:
                    anchor_s = avg
                    n_s += k
                if n_s < NMAX:
                    sm = M4.step_mult(cfg, n_s) * vola
                    cap = ba
                    if break_flg == 0:
                        cap = max(cap, centre + M3.ENTRY_MULT * vola)
                    cap = max(cap, anchor_s + sm + 1e-9)
                    price = math.ceil(cap)
                    if price > anchor_s + sm:
                        o = M3.Order(float(price), False, s, n_s,
                                     1 if break_flg != 0 else 0, len(p_t0))
                        p_t0.append(s); p_px.append(float(price))
                        p_side.append(-1); p_mode.append(o.mode)
                        p_rung.append(n_s); p_fill.append(0)
                        orders.append(o)
                        n_s += 1
                        anchor_s = float(price)
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
                elif k >= M3.BREAKEXITSIZE:
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
                ev = cfg.w * vola * ((1.0 / k) if cfg.apportion else 1.0)
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
                    if marketable:
                        n_marketable += 1
                        xpx = last * (1.0 - side * TAKER_BPS / 1e4)
                        close_cycle(s, xpx, xk, True)
                    else:
                        xo = M3.Order(P, side < 0, s, -1, 0, -1)
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
            cand = list(orders)
            if xo is not None:
                cand.append(xo)
            for o in cand:
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

    if side != 0:
        discard_cycle()
    cancel_all()

    r = M3.Res()
    r.cfg = cfg
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
    r.c_gross = np.array(c_gross, float)
    r.c_avg = np.array(c_avg, float); r.c_xpx = np.array(c_xpx, float)
    r.c_side = np.array(c_side, float); r.c_vola = np.array(c_vola, float)
    r.c_supp = np.array(c_supp, int); r.c_reg = np.array(c_reg, int)
    r.u_bps = np.array(u_bps, float); r.u_gross = np.array(u_gross, float)
    r.u_day = np.array(u_day, int)
    r.u_tx = np.array(u_tx, float); r.u_rung = np.array(u_rung, int)
    r.u_kind = np.array(u_kind, int); r.u_k = np.array(u_k, int)
    r.u_mode = np.array(u_mode, int); r.u_reg = np.array(u_reg, int)
    r.n_break_up, r.n_break_dn, r.n_break_off = \
        n_break_up, n_break_dn, n_break_off
    r.n_discard_cyc, r.n_discard_units = n_discard_cyc, n_discard_units
    r.n_marketable = n_marketable
    r.n_supp_seconds = n_supp_seconds
    r.units_opened, r.units_closed = units_opened, units_closed
    r.max_inv = max_inv
    r.break_seconds = break_seconds
    r.n_entry_sec, r.n_gate_storm = n_entry_sec, n_gate_storm
    r.n_harv_open = n_harv_open
    r.fund_tot, r.hold_tot = fund_tot, hold_tot
    assert r.units_opened == r.units_closed, (r.units_opened, r.units_closed)
    assert r.max_inv <= cfg.N

    def mid_at(t):
        idx = np.searchsorted(m.t_tk, t, "right") - 1
        out = np.full(len(t), np.nan)
        good = idx >= 0
        out[good] = m.mid[idx[good]]
        return out

    if len(r.p_t0):
        m0 = mid_at(r.p_t0)
        m5 = mid_at(r.p_t0 + M3.MARKOUT)
        m60 = mid_at(r.p_t0 + M3.MARKOUT2)
        r.p_fwd5 = r.p_side * (m5 - m0) / m0 * 1e4
        r.p_fwd60 = r.p_side * (m60 - m0) / m0 * 1e4
    else:
        r.p_fwd5 = r.p_fwd60 = np.array([], float)
    if len(r.f_t):
        b0 = np.searchsorted(m.t_tk, r.f_t, "left") - 1
        mb = np.full(len(r.f_t), np.nan)
        g = b0 >= 0
        mb[g] = m.mid[b0[g]]
        m5 = mid_at(r.f_t + M3.MARKOUT)
        r.f_cap = r.f_side * (mb - r.f_px) / mb * 1e4
        r.f_adv = r.f_side * (m5 - mb) / mb * 1e4
    else:
        r.f_cap = r.f_adv = np.array([], float)
    if len(r.c_pnl):
        with np.errstate(all="ignore"):
            r.c_width_vola = (r.c_side * (r.c_xpx - r.c_avg)) / r.c_vola
    else:
        r.c_width_vola = np.array([], float)
    return r


# ===========================================================================
# statistics / rendering
# ===========================================================================
def stats(r, eff_days: float):
    st = {}
    st["n_place"] = int(len(r.p_fill))
    st["n_fill"] = int(r.p_fill.sum()) if len(r.p_fill) else 0
    st["f"] = float(r.p_fill.mean()) if len(r.p_fill) else np.nan
    st["n_rt"] = int(len(r.c_pnl))
    st["rt_day"] = len(r.c_pnl) / eff_days if eff_days > 0 else np.nan
    st["units"] = int(len(r.u_bps))
    if st["units"] == 0:
        st.update(dict(mean_unit=np.nan, mean_gross=np.nan, mean_rt=np.nan,
                       total=np.nan, tcl=np.nan, lo=np.nan, hi=np.nan,
                       maxdd=np.nan, ndays=0, days=np.array([]),
                       daily_arr=np.array([])))
        return st
    st["mean_unit"] = float(r.u_bps.mean())
    st["mean_gross"] = float(r.u_gross.mean())
    st["mean_rt"] = float(r.c_pnl.mean())
    st["total"] = float(r.u_bps.sum())
    lo, hi, t = cal.boot_ci(r.u_bps, r.u_day, seed=SEED)
    st["lo"], st["hi"], st["tcl"] = lo, hi, t
    days = np.unique(r.u_day)
    st["days"] = days
    st["daily_arr"] = np.array([r.u_bps[r.u_day == d].sum() for d in days])
    st["ndays"] = len(days)
    o = np.argsort(r.u_tx, kind="stable")
    cum = np.cumsum(r.u_bps[o])
    peak = np.maximum.accumulate(cum)
    st["maxdd"] = float(np.max(peak - cum)) if len(cum) else 0.0
    return st


def rowhead(width=44):
    print(f"{'cell':<{width}}{'place':>8}{'fills':>7}{'f':>7}{'rt':>6}"
          f"{'rt/day':>8}{'units':>7}{'unit bps':>10}{'gross':>9}"
          f"{'rt bps':>9}{'clus t':>8}{'95% CI (unit bps)':>21}{'maxDD':>9}")


def row(label, r, eff_days, width=44):
    s = stats(r, eff_days)
    if s["units"] == 0:
        print(f"{label:<{width}}{s['n_place']:>8,}{s['n_fill']:>7,}"
              f"{'-':>7}{0:>6}{'':>8}{0:>7}{'   no round trip':>10}")
        return s
    print(f"{label:<{width}}{s['n_place']:>8,}{s['n_fill']:>7,}"
          f"{100 * s['f']:>6.1f}%{s['n_rt']:>6,}{fmt(s['rt_day'], 8, 1)}"
          f"{s['units']:>7,}{fmt(s['mean_unit'], 10, 3)}"
          f"{fmt(s['mean_gross'], 9, 3)}{fmt(s['mean_rt'], 9, 2)}"
          f"{fmt(s['tcl'], 8, 2)}  [{s['lo']:+8.3f},{s['hi']:+8.3f}]"
          f"{fmt(s['maxdd'], 9, 1)}")
    return s


def arrhash(r) -> str:
    h = hashlib.sha256()
    for a in (r.c_t0, r.c_tx, r.c_pnl, r.c_xpx, r.u_bps, r.u_tx,
              r.p_px, r.p_t0):
        h.update(np.asarray(a, float).tobytes())
    h.update(np.asarray(r.c_k, np.int64).tobytes())
    return h.hexdigest()[:16]


# ===========================================================================
# 1-minute bar approximation of the SAME week (M4 engine)
# ===========================================================================
def ohlc_from_prints(t, px, sz):
    """prints -> 1-minute OHLCV + gap_bar, the M3.build_bartape recipe.

    Extracted so it can be applied to the 8/20-27 tape (many files); section 0
    asserts it reproduces M3.build_bartape on the 31-day file field by field.
    """
    o = np.argsort(t, kind="stable")
    t, px, sz = t[o], px[o], sz[o]
    b0 = int(np.floor(t[0] / M3.BAR_SEC))
    b1 = int(np.floor(t[-1] / M3.BAR_SEC))
    nb = b1 - b0 + 1
    bi = np.floor(t / M3.BAR_SEC).astype(np.int64) - b0
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

    B = M4.Bars()
    B.n = nb
    B.b0 = b0
    B.t = (np.arange(nb) + b0) * float(M3.BAR_SEC)
    B.opn, B.close, B.high, B.low = opn, close, high, low
    B.vol, B.gap_bar = vol, gap_bar
    return B


def week_prints(data_dir: Path):
    ex = pd.concat([pd.read_csv(p) for p in
                    sorted(data_dir.glob("executions_*.csv.gz"))],
                   ignore_index=True)
    t = cal.epoch_seconds(ex["ts"])
    return t, ex["price"].to_numpy(float), ex["size"].to_numpy(float)


# ===========================================================================
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "tape"))
    ap.add_argument("--diag", default=str(
        ROOT / "backtest_data" / "executions_FX_BTC_JPY_31d_20260823.csv.gz"))
    ap.add_argument("--cutoff", default="2026-08-20T08:22:17Z")
    args = ap.parse_args()
    np.seterr(all="ignore")

    header("M4 FINE-GRAINED LEVEL CHECK -- exploration only, no adoption")
    print("Re-measuring the top M4 surface cells with the M3 second-by-second\n"
          "replay, because the M4 surface was measured on a 1-minute candle\n"
          f"approximation whose bias is of the same order as its best cell.\n"
          f"seed {SEED}, read-only, no network.  "
          "Verdict window (>= 2026-08-28) untouched.")

    m = M3.build_market(Path(args.data))
    M3.build_seconds(m)

    # =====================================================================
    header("0. REPRODUCTION GATE (nothing is read before this passes)")
    # =====================================================================
    sub("0a. generalised engine vs M3.run_cell, trade for trade")
    ref = M3.run_cell(m, False, 40.0, 80.0)
    m.storm, m.storm_age = storm_clock(m.bar["close"])
    got = run_cell_fine(m, GATE_CFG)
    checks = [
        ("placements", len(ref.p_fill) == len(got.p_fill)),
        ("placement prices", np.array_equal(ref.p_px, got.p_px)),
        ("placement times", np.array_equal(ref.p_t0, got.p_t0)),
        ("fill flags", np.array_equal(ref.p_fill, got.p_fill)),
        ("fill times", np.array_equal(ref.f_t, got.f_t)),
        ("round trips", len(ref.c_pnl) == len(got.c_pnl)),
        ("cycle open times", np.array_equal(ref.c_t0, got.c_t0)),
        ("cycle exit times", np.array_equal(ref.c_tx, got.c_tx)),
        ("cycle exit prices", np.array_equal(ref.c_xpx, got.c_xpx)),
        ("cycle depth k", np.array_equal(ref.c_k, got.c_k)),
        ("exit kinds", np.array_equal(ref.c_kind, got.c_kind)),
        ("cycle pnl", np.allclose(ref.c_pnl, got.c_pnl, atol=1e-12)),
        ("unit bps", np.allclose(ref.u_bps, got.u_bps, atol=1e-12)),
        ("taker requotes", ref.n_marketable == got.n_marketable),
        ("discarded cycles", ref.n_discard_cyc == got.n_discard_cyc),
    ]
    for nm, okk in checks:
        print(f"    {nm:<22}{'PASS' if okk else 'FAIL'}")
    gate1 = all(o for _, o in checks)

    sub("0b. level vs report 30 section 1 (break=OFF, T=(40,80))")
    # report 30's CI was drawn with the M3 seed; reproduce it with the M3
    # statistic, then report this script's own seed alongside.
    s5m = M3.cell_stats(got, m.eff_days)
    s5 = stats(got, m.eff_days)
    print(f"    report 30           : unit {REPORT30_UNIT:+.3f} bps  "
          f"CI [{REPORT30_LO:+.3f}, {REPORT30_HI:+.3f}]  rt 1,167  rt/day 251")
    print(f"    this run (M3 seed)  : unit {s5m['mean_unit']:+.3f} bps  "
          f"CI [{s5m['lo']:+.3f}, {s5m['hi']:+.3f}]  "
          f"rt {s5m['n_rt']:,}  rt/day {s5m['rt_day']:.0f}")
    print(f"    this run (seed {SEED}): unit {s5['mean_unit']:+.3f} bps  "
          f"CI [{s5['lo']:+.3f}, {s5['hi']:+.3f}]   "
          f"(bootstrap seed moves only the CI ends)")
    gate2 = (abs(s5m["mean_unit"] - REPORT30_UNIT) < 0.001
             and abs(s5m["lo"] - REPORT30_LO) < 0.001
             and abs(s5m["hi"] - REPORT30_HI) < 0.001)
    print(f"    GATE           : {'PASS' if (gate1 and gate2) else 'FAIL'}")
    if not (gate1 and gate2):
        print("\n>>> REPRODUCTION GATE BROKEN.  Stopping before any cell "
              "number is computed.")
        return 1

    sub("0c. storm clock == M4._indicators recipe, and the bar-tape recipe")
    t_w, px_w, sz_w = week_prints(Path(args.data))
    Bw = ohlc_from_prints(t_w, px_w, sz_w)
    Bw = M4._indicators(Bw, tick=1.0)
    st_chk, age_chk = storm_clock(Bw.close)
    print(f"    storm flag equal to M4._indicators : "
          f"{bool(np.array_equal(st_chk, Bw.storm))}")
    print(f"    storm age  equal to M4._indicators : "
          f"{bool(np.array_equal(age_chk, Bw.storm_age))}")
    assert np.array_equal(st_chk, Bw.storm)
    assert np.array_equal(age_chk, Bw.storm_age)
    BT = M3.build_bartape(Path(args.diag), args.cutoff)
    dfd = pd.read_csv(args.diag)
    td = cal.epoch_seconds(dfd["exec_date"])
    keep = td < cal.epoch_seconds(pd.Series([args.cutoff]))[0]
    Bd = ohlc_from_prints(td[keep], dfd["price"].to_numpy(float)[keep],
                          dfd["size"].to_numpy(float)[keep])
    same = all(np.array_equal(getattr(Bd, a), getattr(BT, a))
               for a in ("t", "opn", "close", "high", "low", "vol", "gap_bar"))
    print(f"    ohlc_from_prints == M3.build_bartape on the 31d file : {same}")
    assert same

    # =====================================================================
    header("1. THE STORM CLOCK ON THIS WEEK (what 'harvest' can even see)")
    # =====================================================================
    blind = gap_blind_bars(m)
    m.storm_gapaware, m.storm_age_gapaware = storm_clock(m.bar["close"], blind)
    u = m.s_usable
    jbu = m.jb[u]
    for nm, stx, agx in (("verbatim M4 clock", m.storm, m.storm_age),
                         ("gap-aware clock", m.storm_gapaware,
                          m.storm_age_gapaware)):
        ends = int(np.sum((agx[1:] == 0)))
        print(f"  {nm:<20} storm minutes {int(stx.sum()):>5,} "
              f"({100 * stx.mean():>5.2f}% of the {m.nb:,} bars), "
              f"storm ends {ends:>3}")
        for H in (2.0, 6.0):
            hb = int(H * 60)
            openm = (agx[jbu] >= 0) & (agx[jbu] <= hb)
            print(f"      H={H:.0f}h -> {100 * openm.mean():>5.1f}% of the "
                  f"{int(u.sum()):,} usable seconds are entry-open "
                  f"= {openm.sum() / 86400:.3f} effective board-days")
    print("\n  A storm needs |30-minute return| >= 0.8 %.  The frozen v37 range\n"
          "  gate (40m body range 10-82 bps) already refuses entry on almost\n"
          "  every storm minute (M4 section 5), so 'harvest' is a clock, not a\n"
          "  filter: it deletes calendar time, and with it round trips.")

    # =====================================================================
    header("2. THE FIVE CELLS, FINE-GRAINED  (strict gap mask = primary)")
    # =====================================================================
    print(f"effective board-days: strict {m.eff_days:.3f} / "
          f"relaxed {m.eff_days_relaxed:.3f}\n")
    R, S = {}, {}
    for tag, cfg in CELLS:
        R[tag] = run_cell_fine(m, cfg)
        S[tag] = stats(R[tag], m.eff_days)
    rowhead()
    for tag, cfg in CELLS:
        row(cname(tag, cfg), R[tag], m.eff_days)
    print("\n  unit bps = mean per-unit round-trip return NET of funding; "
          "gross = before\n  funding; rt bps = mean per ROUND TRIP (sum of "
          "its k units).  cluster t / CI\n  = day-clustered bootstrap of the "
          f"mean per-unit bps (seed {SEED}, 2000 draws).\n  maxDD on the "
          "cumulative per-unit curve, in unit-bps.")

    sub("2b. relaxed gap mask (sensitivity, NEVER used for selection)")
    Rrel = {}
    rowhead()
    for tag, cfg in CELLS:
        Rrel[tag] = run_cell_fine(m, cfg, relaxed_gaps=True)
        row(cname(tag, cfg), Rrel[tag], m.eff_days_relaxed)

    sub("2c. harvest clock sensitivity (gap-aware storm clock)")
    rowhead()
    for tag, cfg in CELLS:
        if cfg.storm[0] == "none":
            continue
        rg = run_cell_fine(m, cfg, storm=m.storm_gapaware,
                           age=m.storm_age_gapaware)
        row(cname(tag, cfg) + " [gap-aware]", rg, m.eff_days)

    def exit_table(RR, label):
        sub(f"2d. exit breakdown ({label})")
        print(f"{'cell':<44}{'exit':<12}{'rt':>6}{'share':>8}{'taker%':>8}"
              f"{'units':>7}{'unit bps':>10}{'total bps':>11}{'of P&L':>9}")
        _exit_body(RR)

    def inv_table(RR, label):
        sub(f"2e. inventory distribution and holding time ({label})")
        print(f"{'cell':<44}{'units/rt':>9}{'maxk':>6}{'hold s p50':>11}"
              f"{'hold s p90':>11}"
              + "".join(f"{'k=' + str(j + 1):>6}"
                        for j in range(MAX_RUNG_HARD)))
        _inv_body(RR)

    def _exit_body(RR):
        for tag, cfg in CELLS:
            r = RR[tag]
            if not len(r.c_pnl):
                continue
            tot = r.u_bps.sum()
            for kd in range(5):
                cs = r.c_kind == kd
                us = r.u_kind == kd
                if cs.sum() == 0:
                    continue
                print(f"{cname(tag, cfg):<44}{KIND_NAMES[kd]:<12}"
                      f"{int(cs.sum()):>6,}{100 * cs.mean():>7.1f}%"
                      f"{100 * float(r.c_taker[cs].mean()):>7.1f}%"
                      f"{int(us.sum()):>7,}"
                      f"{fmt(float(r.u_bps[us].mean()), 10, 3)}"
                      f"{fmt(float(r.u_bps[us].sum()), 11, 1)}"
                      f"{fmt(100 * float(r.u_bps[us].sum()) / tot if tot else np.nan, 8, 1)}%")

    def _inv_body(RR):
        for tag, cfg in CELLS:
            r = RR[tag]
            if not len(r.c_k):
                continue
            hold = r.c_tx - r.c_t0
            sh = [100 * float((r.c_k == j + 1).mean())
                  for j in range(MAX_RUNG_HARD)]
            print(f"{cname(tag, cfg):<44}{fmt(float(r.c_k.mean()), 9, 2)}"
                  f"{r.max_inv:>6}"
                  f"{fmt(float(np.percentile(hold, 50)), 11, 1)}"
                  f"{fmt(float(np.percentile(hold, 90)), 11, 1)}"
                  + "".join(f"{v:>5.1f}%" for v in sh))

    exit_table(R, "strict mask")
    exit_table(Rrel, "relaxed mask")
    inv_table(R, "strict mask")
    inv_table(Rrel, "relaxed mask")

    sub("2f. daily totals of per-unit bps (the cluster the CI rests on)")
    all_days = sorted(set(int(d) for tag, _ in CELLS for d in S[tag]["days"]))
    print(f"{'cell':<44}" + "".join(
        f"{str(pd.Timestamp(d * 86400, unit='s', tz='UTC').date())[5:]:>10}"
        for d in all_days) + f"{'+days':>8}")
    for tag, cfg in CELLS:
        s = S[tag]
        dd = dict(zip(s["days"], s["daily_arr"]))
        npos = sum(1 for d in all_days if d in dd and dd[d] > 0)
        print(f"{cname(tag, cfg):<44}"
              + "".join(f"{dd[d]:>10.1f}" if d in dd else f"{'-':>10}"
                        for d in all_days)
              + f"{npos:>5}/{len(dd)}")

    sub("2g. funding audit (0.06 %/day pro-rata; check = 6 bps/day * hold)")
    print(f"{'cell':<44}{'units':>8}{'mean hold min':>15}"
          f"{'funding bps/unit':>18}{'check':>10}")
    for tag, cfg in CELLS:
        r = R[tag]
        nn = max(len(r.u_bps), 1)
        mh = r.hold_tot / nn / 60.0
        print(f"{cname(tag, cfg):<44}{len(r.u_bps):>8,}{mh:>15.2f}"
              f"{r.fund_tot / nn:>18.4f}"
              f"{M4.FUNDING_BPS_DAY * mh / 1440.0 if cfg.funding else 0.0:>10.4f}")

    # =====================================================================
    header("3. HOW THIN IS THE HARVEST?  (n, and what the CI can carry)")
    # =====================================================================
    print(f"{'cell':<44}{'entry-open s':>14}{'eff days open':>15}"
          f"{'entry secs':>12}{'blocked by clock':>18}{'rt':>6}"
          f"{'rt/open day':>13}")
    for tag, cfg in CELLS:
        r = R[tag]
        opend = r.n_harv_open / 86400.0
        print(f"{cname(tag, cfg):<44}{r.n_harv_open:>14,}{opend:>15.3f}"
              f"{r.n_entry_sec:>12,}{r.n_gate_storm:>18,}"
              f"{len(r.c_pnl):>6,}"
              f"{len(r.c_pnl) / opend if opend > 0 else np.nan:>13.1f}")
    print("\n  'entry-open s' counts usable seconds whose completed bar is "
          "inside the\n  harvest window; the no-gate cells are open on every "
          "usable second.")
    print(f"{'cell':<44}{'rt':>6}{'unit bps':>10}{'CI half-width':>15}"
          f"{'CI width / |point|':>20}{'days with rt':>14}")
    for tag, cfg in CELLS:
        s = S[tag]
        if s["units"] == 0:
            continue
        hw = (s["hi"] - s["lo"]) / 2.0
        print(f"{cname(tag, cfg):<44}{s['n_rt']:>6,}"
              f"{fmt(s['mean_unit'], 10, 3)}{hw:>15.3f}"
              f"{2 * hw / abs(s['mean_unit']) if s['mean_unit'] else np.nan:>20.1f}"
              f"{s['ndays']:>14}")

    sub("3b. is the harvest window where the money is?  Regime attribution "
        "of the\n    UNGATED cell (3), by the regime at the cycle's first "
        "fill.  This is an\n    attribution of one run, not a simulation: "
        "banning entries changes the\n    later inventory state, so the gated "
        "cells need not match it.")
    print(f"{'cell':<44}{'regime':<12}{'units':>8}{'share':>8}{'unit bps':>10}"
          f"{'total bps':>12}{'rt':>7}{'win%':>8}")
    for tag in ("3", "5a"):
        r = R[tag]
        cfg = dict(CELLS)[tag]
        for rg in range(4):
            mu = r.u_reg == rg
            mc = r.c_reg == rg
            if mu.sum() == 0:
                continue
            print(f"{cname(tag, cfg):<44}{M4.REG_NAMES[rg]:<12}"
                  f"{int(mu.sum()):>8,}{100 * float(mu.mean()):>7.1f}%"
                  f"{fmt(float(r.u_bps[mu].mean()), 10, 3)}"
                  f"{fmt(float(r.u_bps[mu].sum()), 12, 1)}{int(mc.sum()):>7,}"
                  f"{100 * float((r.c_pnl[mc] > 0).mean()) if mc.sum() else 0:>7.1f}%")
    r3 = R["3"]
    m2h = (r3.u_reg == M4.R_P2)
    if m2h.sum() and (~m2h).sum():
        lo1, hi1, t1 = cal.boot_ci(r3.u_bps[m2h], r3.u_day[m2h], seed=SEED)
        lo2, hi2, t2 = cal.boot_ci(r3.u_bps[~m2h], r3.u_day[~m2h], seed=SEED)
        print(f"\n  cell 3, entries <=2h after a storm end : "
              f"{r3.u_bps[m2h].mean():+.3f} bps/unit "
              f"[{lo1:+.3f},{hi1:+.3f}] on {int(m2h.sum()):,} units")
        print(f"  cell 3, all other entries             : "
              f"{r3.u_bps[~m2h].mean():+.3f} bps/unit "
              f"[{lo2:+.3f},{hi2:+.3f}] on {int((~m2h).sum()):,} units")
        d = r3.u_bps[m2h].mean() - r3.u_bps[~m2h].mean()
        print(f"  difference                            : {d:+.3f} bps/unit "
              f"-- the whole case for the harvest overlay, on 7 day clusters.")

    # =====================================================================
    header("4. CANDLE APPROXIMATION BIAS, MEASURED ON THE SAME WEEK")
    # =====================================================================
    print("Report 30 compared a fine-grained replay of 8/20-27 with a "
          "1-minute\napproximation of a DIFFERENT window (the 27 days before "
          "it) and read the\ndifference (-0.395 vs -2.597 = 2.20 bps/unit) as "
          "a method bias.  That number\nmixes method with window.  Below, the "
          "same cells are run through the M4 bar\nengine on THIS week, so the "
          "window is held fixed and only the method moves.")

    sub("4a. bar tape of 8/20-27 (same prints, two gap disciplines)")
    print(f"  native M4 gaps  : {int(Bw.ok.sum()):,} usable bars "
          f"= {Bw.eff_days:.3f} effective days "
          f"({int(Bw.gap_bar.sum()):,} bars inside a >=5-minute print gap)")
    Bm = ohlc_from_prints(t_w, px_w, sz_w)
    bs = Bm.t
    Bm.gap_bar = Bm.gap_bar | cal.span_touches_gap(
        bs, bs + M3.BAR_SEC, m.gs, m.ge)
    Bm = M4._indicators(Bm, tick=1.0)
    print(f"  fine-grained gap: {int(Bm.ok.sum()):,} usable bars "
          f"= {Bm.eff_days:.3f} effective days (ticker U board silence, "
          f"the M3 rule)")
    print(f"  fine replay     : {m.eff_days:.3f} effective board-days "
          f"(second grid)")

    for lab, BB in (("bar approx, native M4 gap rule", Bw),
                    ("bar approx, M3 gap rule", Bm)):
        sub(f"4b. {lab}")
        rowhead()
        for tag, cfg in CELLS:
            rb = M4.run_cell(BB, cfg)
            sb = M4.stats(rb, BB.eff_days)
            print(f"{cname(tag, cfg):<44}{rb.n_place:>8,}{rb.n_fillx:>7,}"
                  f"{100 * rb.n_fillx / max(rb.n_place, 1):>6.1f}%"
                  f"{sb['n_rt']:>6,}{fmt(sb['rt_day'], 8, 1)}"
                  f"{len(rb.u_bps):>7,}{fmt(sb['mean_unit'], 10, 3)}"
                  f"{fmt(float(rb.u_gross.mean()) if len(rb.u_gross) else np.nan, 9, 3)}"
                  f"{fmt(sb['mean_rt'], 9, 2)}{fmt(sb['tcl'], 8, 2)}"
                  f"  [{sb['lo']:+8.3f},{sb['hi']:+8.3f}]"
                  f"{fmt(sb['maxdd'], 9, 1)}")
            if BB is Bm:
                S[tag]["bar_unit"] = sb["mean_unit"]
                S[tag]["bar_rt"] = sb["n_rt"]
            else:
                S[tag]["barnat_unit"] = sb["mean_unit"]

    sub("4c. the bias itself (fine minus bar, same week, same cell)")
    print(f"{'cell':<44}{'fine unit':>11}{'bar (M3 gaps)':>15}"
          f"{'bias':>9}{'bar (M4 gaps)':>15}{'bias':>9}{'fine rt':>9}{'bar rt':>8}")
    biases = []
    for tag, cfg in CELLS:
        s = S[tag]
        b1 = s["mean_unit"] - s["bar_unit"]
        b2 = s["mean_unit"] - s["barnat_unit"]
        biases.append(b1)
        print(f"{cname(tag, cfg):<44}{fmt(s['mean_unit'], 11, 3)}"
              f"{fmt(s['bar_unit'], 15, 3)}{fmt(b1, 9, 3)}"
              f"{fmt(s['barnat_unit'], 15, 3)}{fmt(b2, 9, 3)}"
              f"{s['n_rt']:>9,}{s['bar_rt']:>8,}")
    print(f"\n  median same-week bias (M3 gap rule): "
          f"{np.median(biases):+.3f} bps/unit  "
          f"[min {min(biases):+.3f}, max {max(biases):+.3f}]")
    print("  report 30's cross-window figure was +2.20 bps/unit; the "
          "same-window\n  measurement above is the one that isolates the "
          "approximation.")

    sub("4d. decomposition of report 30's 2.20 (method vs window)")
    rd = M3.run_cell_bars(BT, False, 40.0, 80.0)
    sd = M4.stats(rd, BT.eff_days)
    print(f"  27-day bar approximation of the SAME cell (report 30 (b)) : "
          f"{sd['mean_unit']:+.3f} bps/unit over {sd['n_rt']:,} rt")
    print(f"  8/20-27 bar approximation of the same cell (M3 gap rule)  : "
          f"{S['5a']['bar_unit']:+.3f} bps/unit")
    print(f"  8/20-27 fine replay of the same cell                      : "
          f"{S['5a']['mean_unit']:+.3f} bps/unit")
    print(f"  => method (same week)  {S['5a']['mean_unit'] - S['5a']['bar_unit']:+.3f}"
          f"   window (bar engine, 27d -> this week) "
          f"{S['5a']['bar_unit'] - sd['mean_unit']:+.3f}")

    # =====================================================================
    header("5. ADVERSE SELECTION AND CAPTURE (report 26 consistency)")
    # =====================================================================
    print(f"{'cell':<44}{'fills':>7}{'capture bps':>13}{'adverse 5s':>12}"
          f"{'cap+adv':>9}{'placed fwd5':>13}{'placed fwd60':>14}")
    for tag, cfg in CELLS:
        r = R[tag]
        if not len(r.f_cap):
            continue
        print(f"{cname(tag, cfg):<44}{len(r.f_cap):>7,}"
              f"{fmt(float(np.nanmean(r.f_cap)), 13, 3)}"
              f"{fmt(float(np.nanmean(r.f_adv)), 12, 3)}"
              f"{fmt(float(np.nanmean(r.f_cap) + np.nanmean(r.f_adv)), 9, 3)}"
              f"{fmt(float(np.nanmean(r.p_fwd5)), 13, 3)}"
              f"{fmt(float(np.nanmean(r.p_fwd60)), 14, 3)}")
    print("\n  capture = (mid at the fill - our price), signed by our side; "
          "adverse 5s =\n  the mid's move against us in the 5 s after. "
          "Report 30 measured cap+adv in\n  -0.87..-0.97 for the M3 cells "
          "(report 26 calibration).  'placed fwd' is the\n  drift after a "
          "placement, filled or not -- the maker's counterfactual.")

    sub("5b. realised round-trip width vs design (w x vola)")
    print(f"{'cell':<44}{'design w':>10}{'median width/vola':>19}"
          f"{'p25':>8}{'p75':>8}{'win%':>8}{'win rt':>9}{'loss rt':>10}")
    for tag, cfg in CELLS:
        r = R[tag]
        if not len(r.c_width_vola):
            continue
        wv = r.c_width_vola[np.isfinite(r.c_width_vola)]
        wn = r.c_pnl > 0
        print(f"{cname(tag, cfg):<44}{cfg.w:>10.2f}"
              f"{float(np.median(wv)):>19.3f}"
              f"{float(np.percentile(wv, 25)):>8.3f}"
              f"{float(np.percentile(wv, 75)):>8.3f}"
              f"{100 * float(wn.mean()):>7.1f}%"
              f"{float(r.c_pnl[wn].mean()) if wn.sum() else np.nan:>9.2f}"
              f"{float(r.c_pnl[~wn].mean()) if (~wn).sum() else np.nan:>10.2f}")

    # =====================================================================
    header("6. SANITY")
    # =====================================================================
    print("look-ahead      : every decision at second s reads the COMPLETED "
          "minute bar\n                  floor(s/60)-1 and prints strictly "
          "before s; queue arrival is\n                  applied at the END "
          "of the second (M3 R10).  The storm flag is\n                  "
          "close[q] vs close[q-30], both completed bars.")
    print(f"inventory cap   : asserted len(inv) <= N every fill, every cell "
          f"-- max seen "
          f"{ {tag: R[tag].max_inv for tag, _ in CELLS} }")
    print(f"position ledger : units opened == units closed for every cell : "
          f"{all(R[t].units_opened == R[t].units_closed for t, _ in CELLS)}")
    print(f"one-sided       : opposite-side fill assert never fired")
    print(f"gap discipline  : cycles straddling a gap are DISCARDED, not "
          f"counted -- "
          f"{ {tag: R[tag].n_discard_cyc for tag, _ in CELLS} }")
    print(f"reproduction    : PASS (section 0, trade-for-trade + level)")
    print(f"determinism     : seed {SEED}; the only RNG is the cluster "
          f"bootstrap.  Result hashes:")
    for tag, cfg in CELLS:
        print(f"                  {tag:<3} {arrhash(R[tag])}")
    print(f"cells evaluated : {len(CELLS)} configurations x "
          f"(strict, relaxed, gap-aware) fine replays\n"
          f"                  + the same {len(CELLS)} on two bar tapes.  "
          f"No new axis was swept.")

    # =====================================================================
    header("7. WHAT THE LEVEL SAYS")
    # =====================================================================
    print(f"{'cell':<44}{'unit bps':>10}{'CI':>22}{'sign(CI lo)':>13}"
          f"{'point > 0':>11}{'relaxed sign':>14}")
    any_pos = False
    for tag, cfg in CELLS:
        s = S[tag]
        sr = stats(Rrel[tag], m.eff_days_relaxed)
        if s["units"] == 0:
            continue
        pos = s["mean_unit"] > 0
        any_pos = any_pos or pos
        print(f"{cname(tag, cfg):<44}{fmt(s['mean_unit'], 10, 3)}"
              f"  [{s['lo']:+8.3f},{s['hi']:+8.3f}]"
              f"{'excl 0' if s['lo'] > 0 else 'incl 0':>13}"
              f"{'YES' if pos else 'no':>11}"
              f"{fmt(sr['mean_unit'], 14, 3)}")
    print()
    if any_pos:
        print("At least one cell has a positive POINT estimate at the "
              "fine-grained level.\nWhether its CI is meaningful, and "
              "whether it survives the plateau and the\n57-cell multiplicity "
              "ledger, is judged in the report -- not here.")
    else:
        print("No cell is positive at the fine-grained level.  The M4 surface "
              "is negative\nin LEVEL as well as in ordering; the candle "
              "approximation was not what was\nkilling it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
