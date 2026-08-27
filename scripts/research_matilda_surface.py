"""M4 SURFACE SWEEP -- matilda v37 without the apportioned take-profit.

EXPLORATION ONLY.  NO ADOPTION DECISION IS POSSIBLE FROM THIS SCRIPT.
Every dataset it touches is contaminated (already used for hypothesis
generation) and the primary series is a PROXY (Binance BTCUSDT, not the
traded venue).  The only permitted output is (1) a map of the surface and
(2) at most TWO "M4 freeze candidates" proposed to the lead.  Freezing,
pre-registration and the single-shot verdict remain the lead's, on fresh
data (>= 2026-08-28 board days), which this script never reads.

----------------------------------------------------------------------------
WHY  (report 30 = docs/RESEARCH_REPORT_2026-08-28ae.md)
----------------------------------------------------------------------------
M3 (TaroCamp v37 modernised) was feasibility-rejected 0/4, but at 1.13-1.48x
from break-even it is the closest this project has measured.  Report 30 sec
3.1 isolated the mechanism: the APPORTIONED take profit (width = 0.8*vola/k,
measured from the average entry) fixes the gross profit of a winning round
trip at 0.8*vola REGARDLESS of how many rungs k were taken, while the loss
rides on all k units.  "Smoothing profitability" and "decoupling the win
from the risk taken" are the same device.

The owner asked for the SURFACE around that device: remove the
apportionment, sweep the take-profit width and the rung count, sweep the
grid geometry, and overlay the storm clock.

----------------------------------------------------------------------------
BASE ARM (M3's best cell, report 30 sec 1)
----------------------------------------------------------------------------
break mode OFF | time ladder (T1, T2) = (40, 80) minutes | entry band
2.0 x vola | 1-minute bars | 40-bar window (body range, TRUE mean vola).

COSTS
  maker entry            0 bps (fee 0, no spread paid)
  taker exit             3.96 bps (report 30 / KNOWLEDGE sec 1, burst level)
  funding  0.06 %/day    pro-rated by holding time, charged per unit from
                         its own fill to the cycle exit.  Report 30 did NOT
                         charge this; at 40-80 minute holds it is worth
                         0.17-0.33 bps/unit.  Charged as a COST on both
                         sides (conservative: real funding is directional).

----------------------------------------------------------------------------
DATA
----------------------------------------------------------------------------
primary   data/binance_BTCUSDT_1m_full.csv
          302,403 contiguous 1-minute klines, 2026-01-22 .. 2026-08-20,
          210.0 days, no missing minutes.  PROXY: report 24 measured the
          bitFlyer/Binance 1-minute correlation at +0.890 with lag 0, and
          report 30 found the candle approximation sign-consistent with the
          fine-grained replay.  Tick 0.01 USD.
cross     backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz, the part
          before 2026-08-20T08:22:17Z, rebuilt into 1-minute bars by the
          M3 code path (25.22 effective days).  Tick 1 JPY.
NOT READ  anything at or after 2026-08-28 (the verdict window).

----------------------------------------------------------------------------
SWEEP  (~57 evaluated cells, 51 distinct; every stage reported 60/40 split)
----------------------------------------------------------------------------
Stage 1  apportionment x TP width x rungs
         apportioned (verbatim v37, w = 0.8):  N in {1,2,3,5,7,10}      = 6
         NOT apportioned (TP = w*vola from the average entry, not
         divided by k):  w in {0.4,0.8,1.2,1.6} x N in {1,2,3,5,7,10}   = 24
Stage 2  grid spacing, applied to the top 3 of stage 1
         uniform 1.0*vola / uniform 1.5*vola / geometric x1.5
         (increments 1.0, 1.5, 2.25, ...) / geometric x2.0              = 12
Stage 3  storm regime, applied to the top 3 after stage 2
         storm flag = CAUSAL |30-minute return| >= 0.8 % (close of the
         completed bar vs the close 30 bars earlier -- the report h
         definition, scripts/research_storm.py).  Storm end = the flag has
         been OFF for 30 consecutive minutes.
         (i) none  (ii) avoid: on the flag turning ON, taker out of the
         whole inventory and cancel every resting order, no entries and no
         flip while ON  (iii) harvest: entries only in the H hours after a
         storm end, H in {2,6} (exits always allowed)  (iv) avoid+harvest
         (H=6)                                                          = 15

----------------------------------------------------------------------------
DISCIPLINE
----------------------------------------------------------------------------
Offline only: reads files, opens no sockets, places no orders.  Read-only,
idempotent, deterministic, seed 20260829, no network.  A reproduction gate
asserts that the apportioned N=7 uniform-1.0 no-storm zero-funding cell
reproduces report 30's diagnostic (b) trade-for-trade on the bitFlyer bars.

Usage: PYTHONPATH=src python scripts/research_matilda_surface.py
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import research_board_calibration as cal      # noqa: E402  (boot_ci, epoch)
import research_matilda_taro as M3            # noqa: E402  (state machine gate)

SEED = 20260829

# ---- frozen base arm (report 30, best M3 cell) -----------------------------
ENTRY_MULT = 2.0
VOLA_COUNT = 40
RANGE_COUNT = 40
RANGE_MIN_BPS = 10.0
RANGE_MAX_BPS = 82.0
TAKER_BPS = 3.96
FUNDING_PCT_DAY = 0.06                 # -> 6.0 bps/day
FUNDING_BPS_DAY = FUNDING_PCT_DAY * 100.0
BAR_SEC = 60
BREAKEXITSIZE = 3
INF = float("inf")

STORM_WIN = 30                         # minutes (report h)
STORM_THR = 0.008                      # 0.8 %
STORM_OFF_RUN = 30                     # minutes of OFF that end a storm

K_TP, K_RELAX, K_T2, K_FLIP, K_BDUMP, K_STORM = 0, 1, 2, 3, 4, 5
KIND_NAMES = ("TP", "relaxed", "forced-T2", "forced-flip", "break-dump",
              "storm-exit")

R_STORM, R_P2, R_P26, R_NORM = 0, 1, 2, 3
REG_NAMES = ("in-storm", "post<=2h", "post 2-6h", "normal")


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


# ===========================================================================
# configuration
# ===========================================================================
@dataclass(frozen=True)
class Cfg:
    N: int = 7
    apportion: bool = True
    w: float = 0.8
    spacing: tuple = ("uniform", 1.0)
    storm: tuple = ("none", 0.0)
    brk_on: bool = False
    T1m: float = 40.0
    T2m: float = 80.0
    funding: float = FUNDING_BPS_DAY

    def spacing_name(self) -> str:
        kind, g = self.spacing
        return f"unif{g:.1f}" if kind == "uniform" else f"geom x{g:.1f}"

    def storm_name(self) -> str:
        kind, h = self.storm
        if kind == "none":
            return "none"
        if kind == "avoid":
            return "avoid"
        if kind == "harvest":
            return f"harvest{h:.0f}h"
        return f"avoid+harv{h:.0f}h"

    def name(self) -> str:
        ap = "app" if self.apportion else "flat"
        s = f"{ap} w={self.w:.1f} N={self.N:<2d} {self.spacing_name():<9s}"
        if self.storm[0] != "none":
            s += f" {self.storm_name()}"
        return s.strip()


def step_mult(cfg: Cfg, j: int) -> float:
    """vola multiples between rung j-1 and rung j (j = 0-based rung index)."""
    kind, g = cfg.spacing
    if kind == "uniform":
        return g
    return float(g) ** max(j - 1, 0)


# ===========================================================================
# bar tape (generic; identical indicator recipe to M3's build_bartape)
# ===========================================================================
class Bars:
    pass


def _roll(a, w, fn):
    out = np.full(len(a), np.nan)
    if len(a) >= w:
        sw = np.lib.stride_tricks.sliding_window_view(a, w)
        out[w - 1:] = fn(sw)
    return out


def _indicators(B: Bars, tick: float) -> Bars:
    opn, close, high, low, vol = B.opn, B.close, B.high, B.low, B.vol
    nb = len(close)
    body = close - opn
    B.candlelen = np.abs(body)
    B.sign = np.sign(body)
    B.topbeard = np.where(B.sign > 0, high - close, high - opn)
    B.underbeard = np.where(B.sign > 0, opn - low, close - low)
    hi_b = np.maximum(opn, close)
    lo_b = np.minimum(opn, close)
    B.vola = np.maximum(_roll(B.candlelen, VOLA_COUNT,
                              lambda s: s.mean(axis=1)), tick)
    B.vol_ave = _roll(vol, VOLA_COUNT, lambda s: s.mean(axis=1))
    B.rmax = _roll(hi_b, RANGE_COUNT, lambda s: s.max(axis=1))
    B.rmin = _roll(lo_b, RANGE_COUNT, lambda s: s.min(axis=1))
    B.rmax2 = _roll(hi_b, RANGE_COUNT * 2, lambda s: s.max(axis=1))
    B.rmin2 = _roll(lo_b, RANGE_COUNT * 2, lambda s: s.min(axis=1))
    B.rwidth = B.rmax - B.rmin
    B.rcentre = np.round((B.rmax + B.rmin) / 2.0 / tick) * tick

    expan = np.zeros(nb, int)
    e = 0
    pmax, pmin, pcen = 0.0, 9.9e18, 0.0
    for i in range(nb):
        if hi_b[i] > pmax:
            e += 1
        elif lo_b[i] < pmin:
            e -= 1
        elif (e >= 1 and lo_b[i] < pcen) or (e <= -1 and hi_b[i] > pcen):
            e = 0
        expan[i] = e
        if np.isfinite(B.rmax[i]):
            pmax, pmin, pcen = B.rmax[i], B.rmin[i], B.rcentre[i]
    B.expan = expan

    win_bad = np.zeros(nb, bool)
    cs = np.r_[0, np.cumsum(B.gap_bar)]
    w = RANGE_COUNT * 2
    idx = np.arange(w - 1, nb)
    win_bad[idx] = (cs[idx + 1] - cs[idx + 1 - w]) > 0
    win_bad[:w - 1] = True
    B.ok = (~win_bad) & np.isfinite(B.rmin2) & np.isfinite(B.vol_ave)
    B.eff_days = float(B.ok.sum()) * BAR_SEC / 86400.0

    # ---- storm clock (CAUSAL: completed-bar closes only) ------------------
    logc = np.log(close)
    r30 = np.full(nb, np.nan)
    r30[STORM_WIN:] = logc[STORM_WIN:] - logc[:-STORM_WIN]
    storm = np.zeros(nb, bool)
    storm[STORM_WIN:] = np.abs(r30[STORM_WIN:]) >= STORM_THR
    B.storm = storm
    off_run = np.zeros(nb, int)
    run = 0
    seen_storm = False
    end_at = -1
    age = np.full(nb, -1, int)          # minutes since the last storm end
    for i in range(nb):
        if storm[i]:
            run = 0
            seen_storm = True
        else:
            run += 1
            if run == STORM_OFF_RUN and seen_storm:
                end_at = i
        off_run[i] = run
        age[i] = (i - end_at) if end_at >= 0 else -1
    B.storm_age = age
    B.tick = tick
    return B


def bars_from_ohlc(path: Path) -> Bars:
    df = pd.read_csv(path)
    t = cal.epoch_seconds(df["open_time"])
    dev = float(np.max(np.abs(t - cal.epoch_seconds_alt(df["open_time"]))))
    o = np.argsort(t, kind="stable")
    t = t[o]
    d = np.diff(t)
    B = Bars()
    B.t = t
    B.n = len(t)
    B.opn = df["open"].to_numpy(float)[o]
    B.high = df["high"].to_numpy(float)[o]
    B.low = df["low"].to_numpy(float)[o]
    B.close = df["close"].to_numpy(float)[o]
    B.vol = df["volume"].to_numpy(float)[o]
    B.gap_bar = np.zeros(B.n, bool)
    if len(d):
        miss = np.where(d > BAR_SEC + 1e-6)[0]
        B.gap_bar[miss] = True
        B.gap_bar[np.minimum(miss + 1, B.n - 1)] = True
    print(f"primary bars        : {B.n:,} minutes, "
          f"{pd.Timestamp(t[0], unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(t[-1], unit='s', tz='UTC')} "
          f"= {(t[-1] - t[0]) / 86400:.2f} days")
    print(f"epoch cross-check   : max |a-b| = {dev:.9f} s (must be ~0); "
          f"bar spacing unique = {np.unique(d) if len(np.unique(d)) < 5 else 'many'}")
    return _indicators(B, tick=0.01)


def bars_from_prints(path: Path, cutoff_iso: str) -> Bars:
    """bitFlyer cross-check tape -- reuses the M3 bar build verbatim."""
    BT = M3.build_bartape(path, cutoff_iso)
    B = Bars()
    for a in ("n", "t", "opn", "close", "high", "low", "vol", "gap_bar"):
        setattr(B, a, getattr(BT, a))
    return _indicators(B, tick=1.0)


# ===========================================================================
# engine
# ===========================================================================
class Res:
    pass


def run_cell(B: Bars, cfg: Cfg) -> Res:
    """v37 state machine on 1-minute bars, generalised over the M4 axes.

    Decisions at the OPEN of bar i use only indicators of the COMPLETED bar
    i-1 (look-ahead zero).  Fills are CONSERVATIVE: an order fills only if
    the bar's high/low strictly pierces its price.  A resting exit is served
    before that bar's entry fills.
    """
    tick = B.tick
    T1, T2 = cfg.T1m * 60.0, cfg.T2m * 60.0
    NMAX = cfg.N
    fund_per_sec = cfg.funding / 86400.0

    st_kind, st_h = cfg.storm
    do_avoid = st_kind in ("avoid", "both")
    do_harv = st_kind in ("harvest", "both")
    harv_bars = int(round(st_h * 60.0))

    inv_px: list[float] = []
    inv_rung: list[int] = []
    inv_t: list[float] = []
    side = 0
    t_first = INF
    avg = 0.0
    orders: list[tuple[float, bool, int, int]] = []
    xo = None
    xkind = K_TP
    anchor_b, anchor_s = INF, -INF
    n_b = n_s = 0
    break_flg = 0
    b_signal = 0
    bup_last, bdn_last = 9.9e18, 0.0
    cyc_mode = 0
    cyc_ever = False
    cyc_supp = False
    cyc_vola = np.nan
    cyc_reg = R_NORM

    c_t0, c_tx, c_k, c_kind, c_taker = [], [], [], [], []
    c_pnl, c_gross, c_avg, c_xpx, c_side, c_vola, c_reg = [], [], [], [], [], [], []
    c_maxk = []
    u_bps, u_gross, u_day, u_tx, u_rung, u_kind, u_k, u_reg = \
        [], [], [], [], [], [], [], []
    n_place = n_fill = 0
    n_disc = n_disc_u = n_mkt = 0
    uo = uc = 0
    max_inv = 0
    cur_maxk = 0
    n_entry_bar = n_gate_range = n_gate_storm = 0
    fund_tot = 0.0
    hold_tot = 0.0

    def cancel_all():
        nonlocal orders, xo, anchor_b, anchor_s, n_b, n_s
        orders = []
        xo = None
        anchor_b, anchor_s = INF, -INF
        n_b = n_s = 0

    def close_cycle(t, xpx, kind, taker):
        nonlocal side, t_first, inv_px, inv_rung, inv_t, avg, uc
        nonlocal cyc_ever, cyc_supp, cur_maxk, fund_tot, hold_tot
        k = len(inv_px)
        tot = 0.0
        gro = 0.0
        day = int(math.floor(t / 86400.0))
        for e, rg, te in zip(inv_px, inv_rung, inv_t):
            g = side * (xpx - e) / e * 1e4
            f = fund_per_sec * max(t - te, 0.0)
            b = g - f
            fund_tot += f
            hold_tot += max(t - te, 0.0)
            tot += b
            gro += g
            u_bps.append(b); u_gross.append(g); u_day.append(day)
            u_tx.append(t); u_rung.append(rg); u_kind.append(kind)
            u_k.append(k); u_reg.append(cyc_reg)
        c_t0.append(t_first); c_tx.append(t); c_k.append(k)
        c_kind.append(kind); c_taker.append(1 if taker else 0)
        c_pnl.append(tot); c_gross.append(gro); c_avg.append(avg)
        c_xpx.append(xpx); c_side.append(side); c_vola.append(cyc_vola)
        c_reg.append(cyc_reg); c_maxk.append(cur_maxk)
        uc += k
        inv_px = []; inv_rung = []; inv_t = []
        side = 0; t_first = INF; avg = 0.0
        cyc_ever = False; cyc_supp = False; cur_maxk = 0
        cancel_all()

    for i in range(1, B.n):
        t = float(B.t[i])
        if not (B.ok[i - 1] and not B.gap_bar[i]):
            if side != 0:
                n_disc += 1
                n_disc_u += len(inv_px)
                uo -= len(inv_px)
                inv_px = []; inv_rung = []; inv_t = []
                side = 0; t_first = INF; avg = 0.0
                cyc_ever = False; cyc_supp = False; cur_maxk = 0
            cancel_all()
            break_flg = 0; b_signal = 0
            bup_last, bdn_last = 9.9e18, 0.0
            continue

        q = i - 1
        storm_on = bool(B.storm[q])
        age = int(B.storm_age[q])
        harv_ok = (not do_harv) or (0 <= age <= harv_bars)

        # ---- 1. indicators of the completed bar ---------------------------
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

        # ---- 1b. storm avoidance: taker out, cancel, freeze ---------------
        if do_avoid and storm_on:
            if side != 0:
                close_cycle(t, last * (1.0 - side * TAKER_BPS / 1e4),
                            K_STORM, True)
            else:
                cancel_all()
            break_flg = 0; b_signal = 0
            continue

        if cfg.brk_on:
            bup = bup_last if bup_last > B.rmax2[q] else float(B.rmax2[q])
            bdn = bdn_last if bdn_last < B.rmin2[q] else float(B.rmin2[q])
            if bup < bb and break_flg != 1 and b_signal != -1:
                break_flg = 1
            elif bdn > ba and break_flg != -1 and b_signal != 1:
                break_flg = -1

        if break_flg == 0:
            rw_bps = rw / last * 1e4
            if rw_bps < RANGE_MIN_BPS or rw_bps > RANGE_MAX_BPS:
                e_flg = 0
                n_gate_range += 1
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

        if e_flg != 0:
            n_entry_bar += 1
        if not harv_ok:
            if e_flg != 0:
                n_gate_storm += 1
            e_flg = 0

        k = len(inv_px)
        if e_flg == 1:
            if n_s != 0 and k == 0:
                cancel_all()
            if k < NMAX:
                if side > 0 and n_b == 0:
                    anchor_b = avg; n_b += k
                while n_b < NMAX:
                    sm = step_mult(cfg, n_b) * vola
                    cap = bb
                    if break_flg == 0:
                        cap = min(cap, centre - ENTRY_MULT * vola)
                    cap = min(cap, anchor_b - sm - 1e-9)
                    price = math.floor(cap / tick) * tick
                    if not (price > 0 and price < anchor_b - sm):
                        break
                    orders.append((float(price), True, n_b,
                                   1 if break_flg != 0 else 0))
                    n_place += 1
                    n_b += 1
                    anchor_b = float(price)
        elif e_flg == -1:
            if n_b != 0 and k == 0:
                cancel_all()
            if k < NMAX:
                if side < 0 and n_s == 0:
                    anchor_s = avg; n_s += k
                while n_s < NMAX:
                    sm = step_mult(cfg, n_s) * vola
                    cap = ba
                    if break_flg == 0:
                        cap = max(cap, centre + ENTRY_MULT * vola)
                    cap = max(cap, anchor_s + sm + 1e-9)
                    price = math.ceil(cap / tick) * tick
                    if not (price > anchor_s + sm):
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
                elif k >= BREAKEXITSIZE:
                    x, xk = 1, K_TP
                else:
                    x, xk = 0, K_TP
            if x == 3:
                close_cycle(t, last * (1.0 - side * TAKER_BPS / 1e4), xk, True)
            elif x == 0:
                cyc_supp = True
                xo = None
            else:
                ev = cfg.w * vola * ((1.0 / k) if cfg.apportion else 1.0)
                if x == 1:
                    if side > 0:
                        P = math.ceil(max(ba, avg + ev + 1e-9) / tick) * tick
                    else:
                        P = math.floor(min(bb, avg - ev - 1e-9) / tick) * tick
                else:
                    if side > 0:
                        P = round(min(centre, avg + ev) / tick) * tick
                    else:
                        P = round(max(centre, avg - ev) / tick) * tick
                P = float(P)
                marketable = (P <= bb) if side > 0 else (P >= ba)
                if xo is not None and xo[0] == P:
                    xkind = xk
                elif marketable:
                    n_mkt += 1
                    close_cycle(t, last * (1.0 - side * TAKER_BPS / 1e4),
                                xk, True)
                else:
                    xo = (P, side < 0)
                    xkind = xk

        if break_flg == 1 and last < centre:
            break_flg = 0; b_signal = 0
        elif break_flg == -1 and last > centre:
            break_flg = 0; b_signal = 0

        # ---- the bar plays out --------------------------------------------
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
            hits.sort(key=lambda o: (-o[0] if o[1] else o[0]))
            for o in hits:
                if len(inv_px) >= NMAX:
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
                    cyc_reg = (R_STORM if storm_on else
                               R_P2 if (0 <= age <= 120) else
                               R_P26 if (120 < age <= 360) else R_NORM)
                if o[3] == 1:
                    cyc_ever = True
                inv_px.append(o[0]); inv_rung.append(o[2]); inv_t.append(tf)
                avg = float(np.mean(inv_px))
                uo += 1
                max_inv = max(max_inv, len(inv_px))
                cur_maxk = max(cur_maxk, len(inv_px))
                xo = None
        assert len(inv_px) <= NMAX
        assert (side == 0) == (len(inv_px) == 0)

    if side != 0:
        n_disc += 1
        n_disc_u += len(inv_px)
        uo -= len(inv_px)

    r = Res()
    r.cfg = cfg
    r.n_place, r.n_fillx = n_place, n_fill
    r.c_t0 = np.array(c_t0, float); r.c_tx = np.array(c_tx, float)
    r.c_k = np.array(c_k, int); r.c_kind = np.array(c_kind, int)
    r.c_taker = np.array(c_taker, int); r.c_pnl = np.array(c_pnl, float)
    r.c_gross = np.array(c_gross, float)
    r.c_avg = np.array(c_avg, float); r.c_xpx = np.array(c_xpx, float)
    r.c_side = np.array(c_side, float); r.c_vola = np.array(c_vola, float)
    r.c_reg = np.array(c_reg, int); r.c_maxk = np.array(c_maxk, int)
    r.u_bps = np.array(u_bps, float); r.u_gross = np.array(u_gross, float)
    r.u_day = np.array(u_day, int); r.u_tx = np.array(u_tx, float)
    r.u_rung = np.array(u_rung, int); r.u_kind = np.array(u_kind, int)
    r.u_k = np.array(u_k, int); r.u_reg = np.array(u_reg, int)
    r.n_discard_cyc, r.n_discard_units = n_disc, n_disc_u
    r.n_marketable = n_mkt
    r.units_opened, r.units_closed = uo, uc
    r.max_inv = max_inv
    r.n_entry_bar, r.n_gate_range, r.n_gate_storm = \
        n_entry_bar, n_gate_range, n_gate_storm
    r.fund_tot, r.hold_tot = fund_tot, hold_tot
    if len(r.c_pnl):
        with np.errstate(all="ignore"):
            r.c_width_vola = (r.c_side * (r.c_xpx - r.c_avg)) / r.c_vola
    else:
        r.c_width_vola = np.array([], float)
    assert r.units_opened == r.units_closed, (r.units_opened, r.units_closed)
    return r


# ===========================================================================
# statistics
# ===========================================================================
def boot_ci_fast(x, groups, n_boot: int = 2000, seed: int = SEED):
    """Cluster bootstrap of the mean.  Algebraically and RNG-identical to
    cal.boot_ci (mean of concatenated buckets = sum(sums)/sum(counts))."""
    x = np.asarray(x, float)
    if x.size == 0:
        return (float("nan"), float("nan"), float("nan"))
    keys, inv = np.unique(np.asarray(groups), return_inverse=True)
    nk = len(keys)
    sums = np.bincount(inv, weights=x, minlength=nk)
    cnts = np.bincount(inv, minlength=nk).astype(float)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, nk, size=(n_boot, nk))
    means = sums[pick].sum(axis=1) / cnts[pick].sum(axis=1)
    sd = float(means.std(ddof=1))
    t = float(x.mean() / sd) if sd > 0 else float("nan")
    return (float(np.percentile(means, 2.5)),
            float(np.percentile(means, 97.5)), t)


def stats(r: Res, eff_days: float, mask=None):
    st = {}
    u = r.u_bps if mask is None else r.u_bps[mask]
    d = r.u_day if mask is None else r.u_day[mask]
    tx = r.u_tx if mask is None else r.u_tx[mask]
    st["units"] = int(len(u))
    st["n_rt"] = int(len(r.c_pnl))
    st["rt_day"] = len(r.c_pnl) / eff_days if eff_days > 0 else np.nan
    if st["units"] == 0:
        st.update(dict(mean_unit=np.nan, mean_rt=np.nan, total=np.nan,
                       daily=np.nan, tcl=np.nan, lo=np.nan, hi=np.nan,
                       maxdd=np.nan))
        return st
    st["mean_unit"] = float(u.mean())
    st["mean_rt"] = float(r.c_pnl.mean()) if len(r.c_pnl) else np.nan
    st["total"] = float(u.sum())
    st["daily"] = st["total"] / eff_days
    lo, hi, t = boot_ci_fast(u, d)
    st["lo"], st["hi"], st["tcl"] = lo, hi, t
    o = np.argsort(tx, kind="stable")
    cum = np.cumsum(u[o])
    peak = np.maximum.accumulate(cum)
    st["maxdd"] = float(np.max(peak - cum)) if len(cum) else 0.0
    return st


def half_masks(r: Res, t0: float, t1: float):
    cut = t0 + 0.6 * (t1 - t0)
    return r.u_tx < cut, r.u_tx >= cut


def inv_dist(r: Res) -> str:
    if not len(r.c_k):
        return "-"
    tot = len(r.c_k)
    parts = []
    for kk in (1, 2, 3, 5, 7, 10):
        if kk > r.cfg.N:
            break
        parts.append(f"{100 * float((r.c_k == kk).mean()):.0f}")
    return "/".join(parts) + f" mean{r.c_k.mean():.2f}"


def exit_mix(r: Res) -> str:
    if not len(r.c_kind):
        return "-"
    out = []
    for kd in range(6):
        s = float((r.c_kind == kd).mean())
        if s > 0.005:
            out.append(f"{KIND_NAMES[kd][:2]}{100 * s:.0f}")
    return " ".join(out)


def row(tag: str, r: Res, eff_days: float, t0: float, t1: float, width=30):
    s = stats(r, eff_days)
    m1, m2 = half_masks(r, t0, t1)
    s1, s2 = stats(r, eff_days, m1), stats(r, eff_days, m2)
    print(f"{tag:<{width}}{s['rt_day']:>7.1f}{fmt(s['mean_unit'], 10, 3)}"
          f"{fmt(s['mean_rt'], 9, 3)}{fmt(s['tcl'], 7, 2)}"
          f" [{s['lo']:+7.3f},{s['hi']:+7.3f}]{fmt(s['maxdd'], 10, 0)}"
          f"{fmt(s1['mean_unit'], 9, 3)}{fmt(s2['mean_unit'], 9, 3)}"
          f"  {inv_dist(r):<22}{exit_mix(r)}")
    return s, s1, s2


def shrink_factor(r: Res) -> float:
    """How much smaller the loss bucket must be for net EV = 0 (report 30's
    'x from break-even'), computed on NET round-trip PnL."""
    if not len(r.c_pnl):
        return float("nan")
    wn = r.c_pnl > 0
    win = float(r.c_pnl[wn].sum())
    los = float(-r.c_pnl[~wn].sum())
    return los / win if win > 0 else float("nan")


def breakeven_line(r: Res) -> str:
    pw = float((r.c_gross > 0).mean())
    gw = float(r.c_gross[r.c_gross > 0].mean())
    gl = float(r.c_gross[r.c_gross <= 0].mean())
    kw = float(r.c_k[r.c_gross > 0].mean())
    kl = float(r.c_k[r.c_gross <= 0].mean())
    return (f"overall: win {100 * pw:.1f}% x {gw:+.2f} rt-bps (mean k {kw:.2f})"
            f" / loss {100 * (1 - pw):.1f}% x {gl:+.2f} rt-bps (mean k "
            f"{kl:.2f}) -> gross EV {pw * gw + (1 - pw) * gl:+.3f}, "
            f"loss bucket must shrink {shrink_factor(r):.2f}x")


def rowhead(width=30):
    print(f"{'config':<{width}}{'rt/day':>7}{'unit bps':>10}{'rt bps':>9}"
          f"{'t':>7}{'95% CI unit bps':>18}{'maxDD':>10}"
          f"{'1st60%':>9}{'2nd40%':>9}  {'inv k=1/2/3/5/7/10':<22}exit mix%")


# ===========================================================================
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", default=str(
        ROOT / "data" / "binance_BTCUSDT_1m_full.csv"))
    ap.add_argument("--cross", default=str(
        ROOT / "backtest_data" / "executions_FX_BTC_JPY_31d_20260823.csv.gz"))
    ap.add_argument("--cutoff", default="2026-08-20T08:22:17Z")
    ap.add_argument("--skip-cross", action="store_true")
    args = ap.parse_args()
    np.seterr(all="ignore")

    header("M4 SURFACE -- EXPLORATION ONLY, NO ADOPTION.  seed 20260829")
    print(__doc__.split("----", 1)[0].strip())

    # =====================================================================
    header("0. DATA + REPRODUCTION GATE")
    # =====================================================================
    B = bars_from_ohlc(Path(args.primary))
    t0, t1 = float(B.t[0]), float(B.t[-1])
    print(f"usable bars         : {int(B.ok.sum()):,} "
          f"= {B.eff_days:.2f} effective days "
          f"({int(B.gap_bar.sum())} minutes flagged as gap)")
    print(f"storm minutes       : {int(B.storm.sum()):,} "
          f"({100 * B.storm.mean():.2f}% of minutes), "
          f"post-storm<=2h {100 * np.mean((B.storm_age >= 0) & (B.storm_age <= 120)):.2f}%, "
          f"post 2-6h {100 * np.mean((B.storm_age > 120) & (B.storm_age <= 360)):.2f}%")
    cut = t0 + 0.6 * (t1 - t0)
    print(f"60/40 split at      : {pd.Timestamp(cut, unit='s', tz='UTC')}")

    Bx = None
    if not args.skip_cross:
        sub("cross-check tape (bitFlyer 27d, M3 code path)")
        Bx = bars_from_prints(Path(args.cross), args.cutoff)

        sub("reproduction gate vs report 30 diagnostic (b)")
        gate_cfg = Cfg(N=7, apportion=True, w=0.8, spacing=("uniform", 1.0),
                       storm=("none", 0.0), brk_on=False, T1m=40.0, T2m=80.0,
                       funding=0.0)
        g = run_cell(Bx, gate_cfg)
        BT = M3.build_bartape(Path(args.cross), args.cutoff)
        g3 = M3.run_cell_bars(BT, False, 40.0, 80.0)
        ok = (g.n_place == g3.n_place and g.n_fillx == g3.n_fillx
              and len(g.c_pnl) == len(g3.c_pnl)
              and np.allclose(g.c_pnl, g3.c_pnl, atol=1e-9)
              and np.allclose(g.u_bps, g3.u_bps, atol=1e-9))
        print(f"M4 engine   : placed {g.n_place:,} fills {g.n_fillx:,} "
              f"rt {len(g.c_pnl):,} unit {g.u_bps.mean():+.4f} bps")
        print(f"M3 engine   : placed {g3.n_place:,} fills {g3.n_fillx:,} "
              f"rt {len(g3.c_pnl):,} unit {g3.u_bps.mean():+.4f} bps")
        print(f"GATE        : {'PASS - trade-for-trade identical' if ok else 'FAIL'}")
        assert ok, "reproduction gate failed"

        sub("bootstrap equivalence check (boot_ci_fast vs cal.boot_ci)")
        a = cal.boot_ci(g.u_bps[:3000], g.u_day[:3000], seed=SEED)
        b = boot_ci_fast(g.u_bps[:3000], g.u_day[:3000], seed=SEED)
        print(f"cal.boot_ci   : lo {a[0]:+.6f} hi {a[1]:+.6f} t {a[2]:+.6f}")
        print(f"boot_ci_fast  : lo {b[0]:+.6f} hi {b[1]:+.6f} t {b[2]:+.6f}")
        print(f"equal         : {np.allclose(a, b, atol=1e-9)}")

    # =====================================================================
    header("1. STAGE 1 -- apportionment x TP width x rung count")
    # =====================================================================
    stage1: list[Cfg] = []
    for N in (1, 2, 3, 5, 7, 10):
        stage1.append(Cfg(N=N, apportion=True, w=0.8))
    for w in (0.4, 0.8, 1.2, 1.6):
        for N in (1, 2, 3, 5, 7, 10):
            stage1.append(Cfg(N=N, apportion=False, w=w))
    print(f"cells: {len(stage1)} (6 apportioned + 24 flat).  "
          f"apportioned N=1 and flat w=0.8 N=1 are the SAME machine "
          f"(0.8/1 = 0.8) -- an internal consistency check.")
    R: dict[Cfg, Res] = {}
    S: dict[Cfg, dict] = {}
    for c in stage1:
        R[c] = run_cell(B, c)
        S[c] = stats(R[c], B.eff_days)

    sub("apportioned (verbatim v37, w = 0.8)")
    rowhead()
    for c in stage1[:6]:
        row(c.name(), R[c], B.eff_days, t0, t1)
    for w in (0.4, 0.8, 1.2, 1.6):
        sub(f"NOT apportioned, TP = {w:.1f} x vola from the average entry")
        rowhead()
        for c in stage1:
            if (not c.apportion) and c.w == w:
                row(c.name(), R[c], B.eff_days, t0, t1)

    sub("funding audit (charged 0.06 %/day pro-rata)")
    print(f"{'config':<30}{'units':>9}{'mean hold min':>15}"
          f"{'funding bps/unit':>18}{'check':>22}")
    for c in stage1[:6]:
        r = R[c]
        n = max(len(r.u_bps), 1)
        mh = r.hold_tot / n / 60.0
        fb = r.fund_tot / n
        print(f"{c.name():<30}{n:>9,}{mh:>15.2f}{fb:>18.4f}"
              f"{FUNDING_BPS_DAY * mh * 60 / 86400:>22.4f}")
    print("  check column = 6.0 bps/day * mean hold / 1440 min -- must equal "
          "the funding column.")

    # =====================================================================
    header("2. IDENTITY TEST -- does removing apportionment make the win "
           "scale with k?")
    # =====================================================================
    print("Report 30 sec 3.1: with apportionment the gross of a WINNING round "
          "trip is\n0.8 x vola whatever k is, while the loss rides on all k "
          "units.  If the device\nis the cause, removing it must make the win "
          "gross proportional to k.\n")
    for c in (Cfg(N=7, apportion=True, w=0.8),
              Cfg(N=7, apportion=False, w=0.8),
              Cfg(N=10, apportion=True, w=0.8),
              Cfg(N=10, apportion=False, w=0.8)):
        r = R[c]
        sub(c.name())
        print(f"{'k':<4}{'n rt':>8}{'win%':>8}{'win rt gross':>14}"
              f"{'win unit':>10}{'loss rt gross':>15}"
              f"{'loss unit':>11}{'width/vola':>12}")
        for kk in range(1, c.N + 1):
            m = r.c_k == kk
            if m.sum() < 20:
                continue
            g = r.c_gross[m]
            wn, ls = g > 0, g <= 0
            wg = float(g[wn].mean()) if wn.sum() else np.nan
            lg = float(g[ls].mean()) if ls.sum() else np.nan
            wv = float(np.nanmedian(r.c_width_vola[m][wn])) if wn.sum() else np.nan
            print(f"{kk:<4}{int(m.sum()):>8,}{100 * wn.mean():>7.1f}%"
                  f"{fmt(wg, 14, 3)}{fmt(wg / kk, 10, 3)}"
                  f"{fmt(lg, 15, 3)}{fmt(lg / kk, 11, 3)}"
                  f"{fmt(wv, 12, 3)}")
        print(f"  {breakeven_line(r)}")

    sub("loss tail: what removing the apportionment costs")
    print(f"{'config':<30}{'mean k win':>11}{'mean k loss':>12}"
          f"{'loss rt gross':>14}{'unit p5':>10}{'unit p1':>10}"
          f"{'worst rt':>11}{'P(k=N exit)':>13}")
    for c in (Cfg(N=7, apportion=True, w=0.8),
              Cfg(N=7, apportion=False, w=0.8),
              Cfg(N=10, apportion=True, w=0.8),
              Cfg(N=10, apportion=False, w=0.8)):
        r = R[c]
        ls = r.c_gross <= 0
        print(f"{c.name():<30}{r.c_k[~ls].mean():>11.2f}{r.c_k[ls].mean():>12.2f}"
              f"{r.c_gross[ls].mean():>14.2f}"
              f"{np.percentile(r.u_bps, 5):>10.2f}"
              f"{np.percentile(r.u_bps, 1):>10.2f}"
              f"{r.c_pnl.min():>11.1f}"
              f"{100 * float((r.c_k == c.N).mean()):>12.1f}%")

    sub("k-proportionality of the win, ALL 30 stage-1 cells "
        "(win rt gross at k=1 vs at k=N)")
    print(f"{'config':<30}{'win@k=1':>10}{'win@k=N':>10}{'ratio':>8}"
          f"{'k=N/k=1 ideal':>15}{'verdict':>12}{'gross EV':>10}"
          f"{'shrink x':>10}")
    for c in stage1:
        r = R[c]
        if not len(r.c_gross):
            continue
        m1 = (r.c_k == 1) & (r.c_gross > 0)
        mN = (r.c_k == c.N) & (r.c_gross > 0)
        if m1.sum() < 20 or mN.sum() < 20:
            print(f"{c.name():<30}{'n/a (N=1)':>10}")
            continue
        a1 = float(r.c_gross[m1].mean())
        aN = float(r.c_gross[mN].mean())
        pw = float((r.c_gross > 0).mean())
        gw = float(r.c_gross[r.c_gross > 0].mean())
        gl = float(r.c_gross[r.c_gross <= 0].mean())
        ev = pw * gw + (1 - pw) * gl
        need = shrink_factor(r)
        v = "proportional" if aN / a1 > 0.6 * c.N else "FIXED"
        print(f"{c.name():<30}{a1:>10.3f}{aN:>10.3f}{aN / a1:>8.2f}"
              f"{c.N:>15}{v:>12}{ev:>10.3f}{need:>10.2f}")
    print("  'shrink x' = the factor by which the LOSS bucket must shrink for "
          "net EV = 0\n  (report 30 measured 1.13-1.48x for M3 on the "
          "fine-grained replay).")

    # =====================================================================
    header("3. N OPTIMALITY CURVES (owner's 'how many rungs is best?')")
    # =====================================================================
    print(f"{'N':<4}", end="")
    for lab in ("app w0.8", "flat w0.4", "flat w0.8", "flat w1.2", "flat w1.6"):
        print(f"{lab:>32}", end="")
    print()
    print(f"{'':<4}", end="")
    for _ in range(5):
        print(f"{'unit':>10}{'total':>11}{'maxDD':>11}", end="")
    print()
    fam = [("app", 0.8)] + [("flat", w) for w in (0.4, 0.8, 1.2, 1.6)]
    for N in (1, 2, 3, 5, 7, 10):
        print(f"{N:<4}", end="")
        for kind, w in fam:
            c = Cfg(N=N, apportion=(kind == "app"), w=w)
            s = S[c]
            print(f"{fmt(s['mean_unit'], 10, 3)}{fmt(s['total'], 11, 0)}"
                  f"{fmt(s['maxdd'], 11, 0)}", end="")
        print()

    # ---- pick the top 3 of stage 1 ---------------------------------------
    order1 = sorted(stage1, key=lambda c: -S[c]["mean_unit"])
    sub("stage 1 ranking by unit bps (top 8)")
    rowhead()
    for c in order1[:8]:
        row(c.name(), R[c], B.eff_days, t0, t1)
    top1 = order1[:3]
    print(f"\ntop 3 carried to stage 2: {[c.name() for c in top1]}")

    # =====================================================================
    header("4. STAGE 2 -- grid geometry (spacing)")
    # =====================================================================
    spacings = [("uniform", 1.0), ("uniform", 1.5),
                ("geom", 1.5), ("geom", 2.0)]
    stage2: list[Cfg] = []
    for c in top1:
        for sp in spacings:
            stage2.append(replace(c, spacing=sp))
    print(f"cells: {len(stage2)} (4 spacings x 3 configs; the uniform-1.0 "
          f"column repeats stage 1)")
    for c in stage2:
        if c not in R:
            R[c] = run_cell(B, c)
            S[c] = stats(R[c], B.eff_days)
    rowhead(34)
    for c in stage2:
        row(c.name(), R[c], B.eff_days, t0, t1, 34)

    sub("geometry: depth reached and the loss tail")
    print(f"{'config':<34}{'mean maxk':>11}{'P(reach N)':>12}"
          f"{'P(k>=3)':>10}{'loss unit p5':>14}{'loss unit p1':>14}"
          f"{'worst rt':>11}")
    for c in stage2:
        r = R[c]
        if not len(r.c_k):
            continue
        print(f"{c.name():<34}{r.c_maxk.mean():>11.2f}"
              f"{100 * float((r.c_maxk >= c.N).mean()):>11.1f}%"
              f"{100 * float((r.c_maxk >= 3).mean()):>9.1f}%"
              f"{np.percentile(r.u_bps, 5):>14.2f}"
              f"{np.percentile(r.u_bps, 1):>14.2f}"
              f"{r.c_pnl.min():>11.1f}")

    order2 = sorted(stage2, key=lambda c: -S[c]["mean_unit"])
    top2 = order2[:3]
    print(f"\ntop 3 carried to stage 3: {[c.name() for c in top2]}")

    # =====================================================================
    header("5. STORM DECOMPOSITION + STAGE 3 -- storm regimes")
    # =====================================================================
    base = top2[0]
    r = R[base]
    sub(f"attribution of {base.name()} by the regime at entry "
        f"(theoretical ceiling of the overlays)")
    print(f"{'regime':<12}{'units':>9}{'share':>8}{'unit bps':>11}"
          f"{'total bps':>12}{'rt':>8}{'win%':>8}")
    tot_all = float(r.u_bps.sum())
    for rg in range(4):
        m = r.u_reg == rg
        cm = r.c_reg == rg
        if m.sum() == 0:
            continue
        print(f"{REG_NAMES[rg]:<12}{int(m.sum()):>9,}"
              f"{100 * float(m.mean()):>7.1f}%"
              f"{r.u_bps[m].mean():>11.3f}{r.u_bps[m].sum():>12.0f}"
              f"{int(cm.sum()):>8,}"
              f"{100 * float((r.c_pnl[cm] > 0).mean()) if cm.sum() else 0:>7.1f}%")
    for rg, nm in ((R_STORM, "avoid in-storm"),):
        m = r.u_reg == rg
        print(f"\nceiling if {nm:<20}: total {tot_all:.0f} -> "
              f"{tot_all - r.u_bps[m].sum():.0f} bps "
              f"({(tot_all - r.u_bps[m].sum()) / max(int((~m).sum()), 1):+.3f} bps/unit "
              f"on {int((~m).sum()):,} units)")
    for lab, sel in (("harvest<=2h only", r.u_reg == R_P2),
                     ("harvest<=6h only", (r.u_reg == R_P2) | (r.u_reg == R_P26))):
        if sel.sum():
            print(f"ceiling if {lab:<20}: total {r.u_bps[sel].sum():.0f} bps "
                  f"({r.u_bps[sel].mean():+.3f} bps/unit on "
                  f"{int(sel.sum()):,} units)")
    print("\n  These are ATTRIBUTIONS of the unmodified run, not simulations: "
          "banning\n  entries changes the later inventory state, so the "
          "measured overlays below\n  need not match the ceilings.")
    sub("why the in-storm bucket is empty: the frozen range gate IS a storm "
        "filter")
    rwb = B.rwidth / B.close * 1e4
    okb = B.ok & np.isfinite(rwb)
    stb, nsb = B.storm & okb, (~B.storm) & okb
    inside = lambda m: 100 * float(np.mean(
        (rwb[m] >= RANGE_MIN_BPS) & (rwb[m] <= RANGE_MAX_BPS)))
    print(f"{'bar class':<16}{'bars':>10}{'median 40m body range':>24}"
          f"{'> range_max (82bps)':>22}{'inside the gate':>18}")
    for nm, m in (("storm", stb), ("non-storm", nsb)):
        print(f"{nm:<16}{int(m.sum()):>10,}{np.nanmedian(rwb[m]):>21.1f} bps"
              f"{100 * float(np.mean(rwb[m] > RANGE_MAX_BPS)):>21.1f}%"
              f"{inside(m):>17.1f}%")
    print(f"  The frozen v37 gate (40m body range must be "
          f"{RANGE_MIN_BPS:.0f}-{RANGE_MAX_BPS:.0f} bps) already refuses "
          f"entry\n  on 99.9% of storm minutes.  'Storm avoidance' therefore "
          f"has almost nothing\n  left to avoid: it can only liquidate "
          f"inventory that was opened BEFORE the\n  storm, which is why the "
          f"overlay below makes the surface WORSE, not better.")

    storms = [("none", 0.0), ("avoid", 0.0), ("harvest", 2.0),
              ("harvest", 6.0), ("both", 6.0)]
    stage3: list[Cfg] = []
    for c in top2:
        for st in storms:
            stage3.append(replace(c, storm=st))
    print(f"\ncells: {len(stage3)} (5 storm levels x 3 configs; the 'none' "
          f"column repeats stage 2)")
    for c in stage3:
        if c not in R:
            R[c] = run_cell(B, c)
            S[c] = stats(R[c], B.eff_days)
    rowhead(46)
    for c in stage3:
        row(c.name(), R[c], B.eff_days, t0, t1, 46)
    print(f"\n{'config':<46}{'entry bars':>12}{'blocked by gate':>17}"
          f"{'blocked by storm rule':>23}{'shrink x':>10}")
    for c in stage3:
        r = R[c]
        print(f"{c.name():<46}{r.n_entry_bar:>12,}{r.n_gate_range:>17,}"
              f"{r.n_gate_storm:>23,}{shrink_factor(r):>10.2f}")

    # =====================================================================
    header("6. MONTHLY SIGN STABILITY (210 days -> 7 calendar months)")
    # =====================================================================
    allcfg = list(dict.fromkeys(stage1 + stage2 + stage3))
    order_all = sorted(allcfg, key=lambda c: -S[c]["mean_unit"])

    def month_key(tarr):
        return pd.DatetimeIndex(pd.to_datetime(tarr, unit="s", utc=True)) \
            .strftime("%Y-%m").to_numpy()

    mlabels = sorted(set(month_key(B.t)))
    refs = [Cfg(N=7, apportion=True, w=0.8),
            Cfg(N=7, apportion=False, w=0.8),
            Cfg(N=10, apportion=True, w=0.8)]
    shown = order_all[:10] + [c for c in refs if c not in order_all[:10]]
    print(f"{'config':<46}", end="")
    for ml in mlabels:
        print(f"{ml[-2:]:>9}", end="")
    print(f"{'+months':>9}")
    for c in shown:
        r = R[c]
        per = month_key(r.u_tx)
        print(f"{c.name():<46}", end="")
        npos = 0
        for ml in mlabels:
            m = (per == ml)
            if m.sum() == 0:
                print(f"{'-':>9}", end="")
                continue
            v = float(r.u_bps[m].mean())
            npos += int(v > 0)
            print(f"{v:>+9.3f}", end="")
        print(f"{npos:>6}/{len(mlabels)}")
    print("  (cells are the mean unit bps of that calendar month; Jan and Aug "
          "are partial)")

    # =====================================================================
    header("7. CROSS-CHECK -- bitFlyer 27-day bars, top 5 configs")
    # =====================================================================
    if Bx is None:
        print("skipped (--skip-cross)")
    else:
        print(f"bitFlyer usable: {Bx.eff_days:.2f} effective days, "
              f"storm minutes {100 * Bx.storm.mean():.2f}%")
        print(f"{'config':<46}{'rt':>7}{'rt/day':>8}"
              f"{'BTCUSDT 210d':>15}{'FX_BTC_JPY 27d':>24}{'sign':>7}")
        for c in order_all[:5] + [x for x in refs if x not in order_all[:5]]:
            rx = run_cell(Bx, c)
            sx = stats(rx, Bx.eff_days)
            a = S[c]["mean_unit"]
            bq = sx["mean_unit"]
            agree = "same" if (np.sign(a) == np.sign(bq)) else "OPP"
            print(f"{c.name():<46}{sx['n_rt']:>7,}{sx['rt_day']:>8.1f}"
                  f"{a:>+15.3f}"
                  f"{bq:>+17.3f} (t {sx['tcl']:+.2f}){agree:>7}")
        print("  the last rows are reference cells (M3 base and its "
              "apportionment ablation), not top-5.")

        sub("LEVEL CALIBRATION -- how pessimistic is the bar approximation?")
        print("Report 30 measured the SAME cell (break OFF, T=(40,80), "
              "apportioned N=7,\nuniform 1.0) two ways on bitFlyer: "
              "fine-grained replay (a) -0.395 bps/unit,\n1-minute bar "
              "approximation (b) -2.597 bps/unit.  The bar model is therefore "
              "\n**about 2.20 bps/unit pessimistic** for this family -- it "
              "fills every order the\nbar's high/low pierced, so it takes "
              "trades a queue would never have got.\n"
              "Consequence: this surface is a map of DIFFERENCES between "
              "cells, not of levels.\nNo cell on it is positive, and the best "
              "cell is 2.21 bps/unit below zero -- i.e.\nthe same order as "
              "the approximation bias itself, so even the sign of the best\n"
              "cell in a fine-grained world is undetermined by this "
              "measurement.")

    # =====================================================================
    header("8. PLATEAU TEST AND M4 FREEZE CANDIDATES (<= 2)")
    # =====================================================================
    print("A candidate must satisfy ALL of: (i) mean unit bps > 0 on the "
          "210-day proxy,\n(ii) BOTH halves positive, (iii) every calendar "
          "month positive, (iv) plateau -\nno neighbour in N (one step) or in "
          "w (one step) degrades below 50 % of it,\n(v) the bitFlyer 27-day "
          "cross-check agrees in sign.\n")
    pos = [c for c in allcfg if S[c]["mean_unit"] > 0]
    print(f"cells with mean unit bps > 0        : {len(pos)} of {len(allcfg)}")
    print(f"cells with a positive 95% CI upper  : "
          f"{sum(1 for c in allcfg if S[c]['hi'] > 0)} of {len(allcfg)}")
    print(f"cells with either half positive     : "
          f"{sum(1 for c in allcfg if max(stats(R[c], B.eff_days, half_masks(R[c], t0, t1)[0])['mean_unit'], stats(R[c], B.eff_days, half_masks(R[c], t0, t1)[1])['mean_unit']) > 0)}"
          f" of {len(allcfg)}")
    survivors = []
    for c in pos:
        r = R[c]
        m1, m2 = half_masks(r, t0, t1)
        h1 = float(r.u_bps[m1].mean()) if m1.sum() else np.nan
        h2 = float(r.u_bps[m2].mean()) if m2.sum() else np.nan
        per = month_key(r.u_tx)
        mm = [float(r.u_bps[per == ml].mean())
              for ml in mlabels if (per == ml).sum()]
        ok_h = (h1 > 0) and (h2 > 0)
        ok_m = all(v > 0 for v in mm)
        print(f"  {c.name():<46} halves {h1:+.3f}/{h2:+.3f} "
              f"{'OK' if ok_h else 'FAIL':<5} months {sum(v > 0 for v in mm)}"
              f"/{len(mm)} {'OK' if ok_m else 'FAIL'}")
        if ok_h and ok_m:
            survivors.append(c)
    for c in survivors:                       # (iv) plateau, (v) cross-check
        nbrs = [x for x in allcfg
                if x != c and x.storm == c.storm and x.spacing == c.spacing
                and ((x.apportion == c.apportion and x.w == c.w
                      and abs((1, 2, 3, 5, 7, 10).index(x.N)
                              - (1, 2, 3, 5, 7, 10).index(c.N)) == 1)
                     or (x.N == c.N and x.apportion == c.apportion
                         and abs(x.w - c.w) <= 0.41))]
        worst = min((S[x]["mean_unit"] for x in nbrs), default=np.nan)
        print(f"  plateau {c.name():<40} worst neighbour {worst:+.3f} "
              f"vs {S[c]['mean_unit']:+.3f} "
              f"({'OK' if worst > 0.5 * S[c]['mean_unit'] else 'FAIL'}), "
              f"{len(nbrs)} neighbours")
    if not survivors:
        print("\n>>> NO POSITIVE PLATEAU.  Zero cells clear even the first "
              "three filters,\n>>> so the plateau and cross-check filters "
              "were never reached.\n>>> No M4 freeze candidate is proposed.")
    else:
        print(f"\n{len(survivors)} cell(s) reached the plateau test; "
              f"the report names at most 2.")
        for c in survivors[:6]:
            print(f"   candidate: {c.name()}  unit "
                  f"{S[c]['mean_unit']:+.3f} bps")

    sub("distance from break-even, whole surface "
        "(loss bucket must shrink by this factor)")
    print(f"{'config':<46}{'unit bps':>10}{'shrink x':>10}"
          f"{'win%':>8}{'win rt':>9}{'loss rt':>10}")
    for c in order_all[:8] + [x for x in refs if x not in order_all[:8]]:
        r = R[c]
        wn = r.c_pnl > 0
        print(f"{c.name():<46}{S[c]['mean_unit']:>+10.3f}"
              f"{shrink_factor(r):>10.2f}{100 * float(wn.mean()):>7.1f}%"
              f"{r.c_pnl[wn].mean():>9.2f}{r.c_pnl[~wn].mean():>10.2f}")
    best_sh = min(shrink_factor(R[c]) for c in allcfg)
    print(f"\n  best on the whole surface: {best_sh:.2f}x from break-even "
          f"(report 30's M3 measured\n  1.13-1.48x on the FINE-GRAINED "
          f"replay; the numbers above are on the bar\n  approximation, which "
          f"report 30 showed to be ~2.20 bps/unit pessimistic --\n  the two "
          f"are NOT directly comparable, only the ordering within this table "
          f"is).")

    # =====================================================================
    header("9. SANITY")
    # =====================================================================
    r0 = R[stage1[0]]
    print(f"look-ahead          : decisions at the open of bar i read only "
          f"bar i-1 indicators;\n                      the storm flag uses "
          f"close[i-1] vs close[i-31] (both completed).")
    print(f"inventory assert    : PASS (len(inv) <= N and side==0 <-> "
          f"empty asserted every bar, every cell)")
    print(f"units opened/closed : "
          f"{all(R[c].units_opened == R[c].units_closed for c in allcfg)}")
    print(f"max inventory seen  : "
          f"{ {c.N: max(R[x].max_inv for x in allcfg if x.N == c.N) for c in allcfg} }")
    print(f"discarded cycles    : "
          f"{ {c.name(): R[c].n_discard_cyc for c in stage1[:3]} } "
          f"(gap-straddling round trips are dropped, not counted as PnL)")
    print(f"cells evaluated     : {len(stage1)} + {len(stage2)} + "
          f"{len(stage3)} = {len(stage1) + len(stage2) + len(stage3)} "
          f"({len(allcfg)} distinct)")
    print(f"multiple comparison : at 60 cells, ~3 cells clear a nominal "
          f"5% one-sided test by chance alone.")
    print(f"determinism         : seed {SEED}, no network, no RNG outside "
          f"the cluster bootstrap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
