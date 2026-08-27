#!/usr/bin/env python3
"""SM spread-MM symmetric family -- EXPLORATION run (selection only).

PREREG: docs/PREREG_spread_mm.md (frozen 2026-08-29). Family = 4 cells:
gate {S7 two-sided window only, window UNION post-storm 2h} x inventory
band K {1, 3}. Structural constants (verbatim from PREREG section 1):

  * one unit (0.01 BTC) quoted at best bid AND best ask simultaneously;
  * follow-requote: when the best moves more than one tick (1 JPY) away
    from our price, requote to the touch, joining the BACK of the queue
    (q_ahead = best size on that ticker row) -- queue-realistic per
    report #26 section 4, punch-through close included;
  * |inv| < K: both sides quoted.  |inv| = K: the increasing side is
    pulled entirely; reducing side only.  No price skew;
  * exits happen ONLY via opposite-side fills.  After the gate closes
    (window ends or storm flag ignites) with inventory open, only the
    reducing side keeps quoting at the touch; if inventory survives
    120 s of gate-off, taker-flatten the lot at 3.96 bps;
  * causal storm flag: |30-minute return| >= 0.8% on COMPLETED 1-minute
    bars built from the ticker mid;
  * S7 window, verbatim: W = 30 s absolute epoch grid, two-sided iff
    both taker sides >= v_min and |B-S|/(B+S) <= 0.30, v_min = p50 of
    the pooled one-side volume over the leading-20% burn-in (strictly
    positive floor), decisions read the PREVIOUS fully-observed window
    only.  Post-storm 2h = the 2 hours following 30 consecutive minutes
    of storm-flag OFF after an ON spell;
  * costs: maker 0, taker 3.96 bps, funding 0.06%/day pro-rated on
    inventory-seconds.  Accounting in unit bps; a round trip (cycle) is
    inventory leaving zero until it next touches zero.

Same-second processing rule (fixed here, as the PREREG requires the
implementation to state one): events are processed in tape order --
ticker rows before prints carrying the same timestamp (quotes update,
then fills are tested against strictly-later prints); prints at equal
timestamps are processed in file order, so a reducing-side fill that
appears earlier on the tape simply reduces inventory first.

Data: exploration window 2026-08-20..27 shared tape (data/tape).  The
judgment region (>= 2026-08-28T00:00Z) is not present in these files and
is not read.  Gap discipline, S7 grid, bootstrap and epoch handling are
imported from scripts/research_board_calibration.py (no re-implementation).

Selection rule (PREREG section 4): keep cells with completed round trips
>= 100 AND net unit bps > 0; if none survive the family is REJECTED AT
FEASIBILITY and the judgment window is not consumed.  Otherwise pick the
max daily-cluster-t cell, subject to the plateau condition; freeze <= 1.

Deterministic: seed 20260829, no network, byte-identical reruns.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "cal", ROOT / "scripts" / "research_board_calibration.py")
cal = importlib.util.module_from_spec(_spec)
sys.modules["cal"] = cal
_spec.loader.exec_module(cal)

SEED = 20260829
TICK = 1.0                     # FX_BTC_JPY price tick, JPY
TAKER_BPS = 3.96
FUND_BPS_DAY = 6.0             # 0.06%/day
BACKSTOP_SEC = 120.0
STORM_RET = 0.008              # |30m return| threshold (causal, 1m bars)
STORM_OFF_MIN = 30             # minutes of OFF to end a storm spell
HARVEST_SEC = 2 * 3600.0
W = cal.W
CUTOFF = pd.Timestamp("2026-08-28T00:00:00Z").timestamp()

CELLS = [("win", 1), ("win", 3), ("union", 1), ("union", 3)]


# --------------------------------------------------------------------------
# causal storm flag + post-storm harvest windows, from 1-minute mid bars
# --------------------------------------------------------------------------
def storm_series(t_tk: np.ndarray, mid: np.ndarray):
    m0 = int(np.floor(t_tk[0] / 60.0))
    m1 = int(np.floor(t_tk[-1] / 60.0))
    n = m1 - m0 + 1
    close = np.full(n, np.nan)
    mi = (np.floor(t_tk / 60.0) - m0).astype(np.int64)
    close[mi] = mid                                   # last mid of the minute
    idx = cal.ffill_idx(np.isfinite(close))
    close = close[np.maximum(idx, 0)]
    # flag for minute m is known at the END of minute m (uses completed bar m)
    flag = np.zeros(n, bool)
    ok = np.arange(n) >= 30
    with np.errstate(invalid="ignore"):
        r = np.abs(close / np.roll(close, 30) - 1.0)
    flag[ok] = r[ok] >= STORM_RET
    # harvest starts: first minute where the flag has been OFF for
    # STORM_OFF_MIN consecutive minutes following an ON spell
    starts = []
    off_run, seen_on = 0, False
    for i in range(n):
        if flag[i]:
            seen_on, off_run = True, 0
        else:
            off_run += 1
            if seen_on and off_run == STORM_OFF_MIN:
                starts.append((m0 + i + 1) * 60.0)   # known at end of minute i
                seen_on = False
    return m0, flag, np.array(starts, float)


def storm_flag_at(m0: int, flag: np.ndarray, t: float) -> bool:
    """Causal read: the flag decided on the last COMPLETED minute."""
    m = int(np.floor(t / 60.0)) - 1 - m0
    if m < 0:
        return False
    return bool(flag[min(m, len(flag) - 1)])


def in_harvest(starts: np.ndarray, t: float) -> bool:
    j = np.searchsorted(starts, t, "right") - 1
    return j >= 0 and (t - starts[j]) <= HARVEST_SEC


# --------------------------------------------------------------------------
# the symmetric quoting engine (event-driven, one pass)
# --------------------------------------------------------------------------
class Cell:
    pass


def run_cell(D, gate_kind: str, K: int) -> Cell:
    (t_tk, bid, ask, bsz, asz, mid, t_ex, px, sz, buy,
     win_ok, g_k0, m0, sflag, hstarts, gs, ge, burn_end) = D

    n_tk, n_ex = len(t_tk), len(t_ex)
    itk = 0
    # quote state per side: price, queue ahead, placed time, active
    qb = dict(p=np.nan, q=0.0, t=np.inf, on=False)
    qa = dict(p=np.nan, q=0.0, t=np.inf, on=False)
    inv = 0
    legs = []            # open legs FIFO: (t, price, side, mid, capture_bps)
    cyc_legs = []        # all legs of the current cycle
    cyc_cash = 0.0
    cyc_t0 = np.nan
    cyc_inv_sec = 0.0
    last_ev_t = np.nan
    gate_off_t = np.nan  # when quoting-allowed turned off with inventory open
    pairs = []           # (tau, cap_in, cap_out, drift_bps, kind)
    cycles = []          # dict per completed cycle
    n_backstop = 0
    n_gap_drop = 0

    cur_bid = cur_ask = cur_mid = np.nan
    gap_j = 0

    def allowed_now(t: float) -> bool:
        if t < burn_end:
            return False
        if storm_flag_at(m0, sflag, t):
            return False
        w = int(np.floor(t / W)) - 1 - g_k0          # previous window
        okw = 0 <= w < len(win_ok) and bool(win_ok[w])
        if gate_kind == "union":
            return okw or in_harvest(hstarts, t)
        return okw

    def requote(side_dict, price, q, t):
        side_dict["p"], side_dict["q"], side_dict["t"], side_dict["on"] = \
            price, q, t, True

    def cancel(side_dict):
        side_dict["on"] = False

    def tick_accrue(t):
        nonlocal cyc_inv_sec, last_ev_t
        if inv != 0 and np.isfinite(last_ev_t):
            cyc_inv_sec += abs(inv) * max(t - last_ev_t, 0.0)
        last_ev_t = t

    def close_cycle(t, taker=False):
        nonlocal cyc_cash, cyc_legs, cyc_t0, cyc_inv_sec, legs
        n_pairs = sum(1 for L in cyc_legs if L[2] > 0)     # buys == sells
        if n_pairs == 0:
            cyc_legs, cyc_cash, cyc_inv_sec, cyc_t0 = [], 0.0, 0.0, np.nan
            legs = []
            return
        ref = cyc_legs[0][3]
        pnl_bps = cyc_cash / ref * 1e4
        fund = FUND_BPS_DAY * cyc_inv_sec / 86400.0
        unit = (pnl_bps - fund) / n_pairs
        day = int(np.floor(cyc_t0 / 86400.0))
        bad = bool(cal.span_touches_gap(np.array([cyc_t0]), np.array([t]),
                                        gs, ge)[0])
        cycles.append(dict(t0=cyc_t0, t1=t, unit=unit, pairs=n_pairs,
                           day=day, taker=taker, gap=bad,
                           maxk=max(abs(sum(l[2] for l in cyc_legs[:i + 1]))
                                    for i in range(len(cyc_legs)))))
        cyc_legs, cyc_cash, cyc_inv_sec, cyc_t0 = [], 0.0, 0.0, np.nan
        legs = []

    def on_fill(t, price, side):
        """side +1 = our bid bought, -1 = our ask sold."""
        nonlocal inv, cyc_cash, cyc_t0, gate_off_t
        tick_accrue(t)
        cap = (cur_mid - price) / cur_mid * 1e4 * side
        if inv == 0:
            cyc_t0 = t
        reducing = (inv > 0 and side < 0) or (inv < 0 and side > 0)
        if reducing and legs:
            t_in, p_in, s_in, m_in, c_in = legs.pop(0)     # FIFO
            drift = (cur_mid - m_in) / m_in * 1e4 * s_in
            pairs.append((t - t_in, c_in, cap, drift, "maker"))
        else:
            legs.append((t, price, side, cur_mid, cap))
        inv += side
        cyc_cash += -side * price
        cyc_legs.append((t, price, side, cur_mid))
        if inv == 0:
            close_cycle(t)

    def taker_flat(t):
        nonlocal inv, cyc_cash, n_backstop
        tick_accrue(t)
        side = -1 if inv > 0 else 1
        price = cur_mid * (1.0 - side * TAKER_BPS / 1e4)
        n_backstop += 1
        while inv != 0:
            cap = (cur_mid - price) / cur_mid * 1e4 * side
            if legs:
                t_in, p_in, s_in, m_in, c_in = legs.pop(0)
                drift = (cur_mid - m_in) / m_in * 1e4 * s_in
                pairs.append((t - t_in, c_in, cap, drift, "taker"))
            inv += side
            cyc_cash += -side * price
            cyc_legs.append((t, price, side, cur_mid))
        close_cycle(t, taker=True)

    def reset_state():
        nonlocal inv, cyc_cash, cyc_legs, cyc_t0, cyc_inv_sec, legs, \
            n_gap_drop, gate_off_t
        if inv != 0 or cyc_legs:
            n_gap_drop += 1
        inv, cyc_cash, cyc_legs, cyc_t0, cyc_inv_sec, legs = \
            0, 0.0, [], np.nan, 0.0, []
        cancel(qb); cancel(qa)
        gate_off_t = np.nan

    def manage_quotes(t):
        nonlocal gate_off_t
        ok = allowed_now(t)
        if inv == 0 and not ok:
            cancel(qb); cancel(qa)
            gate_off_t = np.nan
            return
        # sides: increasing side allowed only if ok and |inv| < K
        want_b = (ok and inv < K) or inv < 0        # bid reduces short inv
        want_a = (ok and inv > -K) or inv > 0       # ask reduces long inv
        if inv != 0 and not ok:                     # reduce-only regime
            want_b, want_a = inv < 0, inv > 0
            if not np.isfinite(gate_off_t):
                gate_off_t = t
            elif t - gate_off_t >= BACKSTOP_SEC:
                taker_flat(t)
                gate_off_t = np.nan
                cancel(qb); cancel(qa)
                return
        else:
            gate_off_t = np.nan
        for want, q, best, size in ((want_b, qb, cur_bid, cur_bsz),
                                    (want_a, qa, cur_ask, cur_asz)):
            if not want:
                cancel(q)
            elif (not q["on"]) or abs(best - q["p"]) > TICK:
                requote(q, best, size, t)

    # ---- event loop ------------------------------------------------------
    cur_bsz = cur_asz = 0.0
    for iex in range(n_ex):
        te = t_ex[iex]
        # advance ticker to the last row at time <= te (ticker first on ties)
        while itk < n_tk and t_tk[itk] <= te:
            cur_bid, cur_ask = bid[itk], ask[itk]
            cur_bsz, cur_asz = bsz[itk], asz[itk]
            cur_mid = mid[itk]
            # gap reset: a jump in the ticker means the recorder was down
            if gap_j < len(gs) and t_tk[itk] > gs[gap_j]:
                reset_state()
                while gap_j < len(gs) and t_tk[itk] > gs[gap_j]:
                    gap_j += 1
            manage_quotes(t_tk[itk])
            itk += 1
        if not np.isfinite(cur_mid):
            continue
        # backstop can also expire between ticker rows
        if inv != 0 and np.isfinite(gate_off_t) and \
                te - gate_off_t >= BACKSTOP_SEC:
            taker_flat(te)
            manage_quotes(te)
        p, s, b = px[iex], sz[iex], buy[iex]
        # our bid is hit by taker SELL prints strictly after placement
        if qb["on"] and (not b) and te > qb["t"]:
            if p < qb["p"] - 1e-9:
                on_fill(te, qb["p"], +1); cancel(qb); manage_quotes(te)
            elif abs(p - qb["p"]) <= 1e-9:
                qb["q"] -= s
                if qb["q"] < 0:
                    on_fill(te, qb["p"], +1); cancel(qb); manage_quotes(te)
        if qa["on"] and b and te > qa["t"]:
            if p > qa["p"] + 1e-9:
                on_fill(te, qa["p"], -1); cancel(qa); manage_quotes(te)
            elif abs(p - qa["p"]) <= 1e-9:
                qa["q"] -= s
                if qa["q"] < 0:
                    on_fill(te, qa["p"], -1); cancel(qa); manage_quotes(te)
        assert abs(inv) <= K, (inv, K)
    # end: discard any open cycle (unterminated at tape end)
    if inv != 0 or cyc_legs:
        n_gap_drop += 1

    c = Cell()
    c.gate, c.K = gate_kind, K
    c.cycles = [x for x in cycles if not x["gap"]]
    c.n_gap_drop = n_gap_drop + sum(1 for x in cycles if x["gap"])
    c.pairs = pairs
    c.n_backstop = n_backstop
    return c


# --------------------------------------------------------------------------
def cell_stats(c: Cell, eff_days: float, day_all: np.ndarray):
    u = np.array([x["unit"] for x in c.cycles])
    d = np.array([x["day"] for x in c.cycles])
    npairs = np.array([x["pairs"] for x in c.cycles])
    st = dict(n=len(u), per_day=len(u) / eff_days if eff_days else np.nan)
    if len(u) == 0:
        return st, u, d
    st["unit"] = float(np.average(u, weights=npairs))
    lo, hi, t = cal.boot_ci(np.repeat(u, npairs), np.repeat(d, npairs))
    st["ci"], st["t"] = (lo, hi), t
    daily = {dd: 0.0 for dd in day_all}
    for uu, dd, kk in zip(u, d, npairs):
        daily[dd] = daily.get(dd, 0.0) + uu * kk
    dv = np.array([daily[k] for k in sorted(daily)])
    st["sharpe"] = float(dv.mean() / dv.std() * np.sqrt(365)) \
        if dv.std() > 0 else np.nan
    cum = np.cumsum(np.repeat(u, npairs))
    peak = np.maximum.accumulate(np.r_[0.0, cum])
    st["maxdd"] = float(np.max(peak[1:] - cum)) if len(cum) else 0.0
    st["taker_pct"] = 100.0 * np.mean([x["taker"] for x in c.cycles])
    st["maxk_mean"] = float(np.mean([x["maxk"] for x in c.cycles]))
    return st, u, d


def main() -> int:
    rng = np.random.default_rng(SEED)                      # noqa: F841
    cal.header("SM SPREAD-MM SYMMETRIC FAMILY -- EXPLORATION "
               "(selection only; contaminated week)")
    (t_tk, bid, ask, bsz, asz, mid, spread_bps,
     t_ex, px, sz, buy, span) = cal.load(ROOT / "data" / "tape")
    assert t_tk[-1] < CUTOFF and t_ex[-1] < CUTOFF, "judgment region present!"
    gs, ge = cal.find_gaps(t_tk, t_ex)
    g = cal.build_grid(t_ex, sz, buy, t_tk, gs, ge)
    burn_end = t_tk[0] + 0.20 * (t_tk[-1] - t_tk[0])
    burn_w = g.usable & (g.start < burn_end)
    pool = np.concatenate([g.vbuy[burn_w], g.vsell[burn_w]])
    v_min = max(float(np.percentile(pool, 50)), 1e-9)
    win_ok = cal.two_sided_mask(g, v_min) & g.usable
    print(f"v_min (burn-in p50) : {v_min:.6f} BTC   "
          f"two-sided duty {100 * win_ok[g.usable].mean():.2f}% of usable "
          f"windows")
    m0, sflag, hstarts = storm_series(t_tk, mid)
    print(f"storm flag          : {int(sflag.sum())} storm minutes, "
          f"{len(hstarts)} post-storm harvest windows")
    lost = float((ge - gs).sum())
    eff_days = ((t_tk[-1] - t_tk[0]) - lost) / 86400.0 * \
        (1 - 0.20)                                        # ex-burn-in approx
    print(f"effective days      : {eff_days:.3f} (ex burn-in, ex gaps)")

    D = (t_tk, bid, ask, bsz, asz, mid, t_ex, px, sz, buy,
         win_ok, g.k0, m0, sflag, hstarts, gs, ge, burn_end)

    day_all = np.unique(np.floor(
        t_tk[t_tk > burn_end] / 86400.0).astype(np.int64))

    cal.header("cells")
    print(f"{'cell':<14}{'cycles':>7}{'cyc/day':>9}{'unit bps':>10}"
          f"{'t':>7}  {'95% CI':<20}{'Sharpe':>8}{'maxDD':>8}"
          f"{'taker%':>7}{'maxK':>6}")
    results = {}
    for gate, K in CELLS:
        c = run_cell(D, gate, K)
        st, u, d = cell_stats(c, eff_days, day_all)
        results[(gate, K)] = (c, st)
        nm = f"{gate}/K={K}"
        if st["n"]:
            print(f"{nm:<14}{st['n']:>7}{st['per_day']:>9.1f}"
                  f"{st['unit']:>10.3f}{st['t']:>7.2f}  "
                  f"[{st['ci'][0]:+.3f},{st['ci'][1]:+.3f}]"
                  f"{st['sharpe']:>8.2f}{st['maxdd']:>8.0f}"
                  f"{st['taker_pct']:>7.1f}{st['maxk_mean']:>6.2f}")
        else:
            print(f"{nm:<14}{st['n']:>7}")

    cal.header("pair anatomy (the scientific payload)")
    for (gate, K), (c, st) in results.items():
        if not c.pairs:
            continue
        tau = np.array([p[0] for p in c.pairs])
        ci_ = np.array([p[1] for p in c.pairs])
        co_ = np.array([p[2] for p in c.pairs])
        dr_ = np.array([p[3] for p in c.pairs])
        mk = np.array([p[4] == "maker" for p in c.pairs])
        print(f"\n[{gate}/K={K}] pairs {len(tau)}  "
              f"(maker-closed {100 * mk.mean():.1f}%, "
              f"backstop events {c.n_backstop}, "
              f"gap-dropped cycles {c.n_gap_drop})")
        line = "  P(opposite fill <= tau | first fill): "
        line += "  ".join(f"{int(x)}s {100 * np.mean(tau[mk] <= x):.1f}%"
                          for x in (5, 15, 60, 300)) if mk.any() else "n/a"
        print(line)
        print(f"  three-term (mean bps): capture_in {ci_.mean():+.3f}  "
              f"capture_out {co_.mean():+.3f}  drift {dr_.mean():+.3f}  "
              f"sum {ci_.mean() + co_.mean() + dr_.mean():+.3f}")
        print(f"  maker pairs only    : capture_in {ci_[mk].mean():+.3f}  "
              f"capture_out {co_[mk].mean():+.3f}  drift {dr_[mk].mean():+.3f}"
              if mk.any() else "")
        print(f"  tau p50 {np.median(tau[mk]):.1f}s  p90 "
              f"{np.percentile(tau[mk], 90):.1f}s" if mk.any() else "")

    cal.header("reproduction cross-check vs report #26 (in-window legs)")
    for (gate, K), (c, st) in results.items():
        if gate != "win" or not c.pairs:
            continue
        ci_ = np.array([p[1] for p in c.pairs])
        print(f"[win/K={K}] mean capture of entering legs {ci_.mean():+.3f} "
              f"bps  (#26 in-window touch capture +0.60; requote-follow "
              f"engine differs by construction -- see limitations)")

    cal.header("selection rule (PREREG section 4)")
    passing = [(k, v[1]) for k, v in results.items()
               if v[1]["n"] >= 100 and v[1].get("unit", -1) > 0]
    if not passing:
        print("cells with >=100 cycles AND net > 0: NONE")
        print("=> FAMILY REJECTED AT FEASIBILITY. The judgment window "
              "(>= 2026-08-28) is NOT consumed.")
    else:
        best = max(passing, key=lambda kv: kv[1]["t"])
        print(f"passing cells: {len(passing)} of 4 "
              f"(chance expectation under zero edge ~2)")
        print(f"max-t cell: {best[0]}  unit {best[1]['unit']:+.3f}  "
              f"t {best[1]['t']:.2f}")
        print("plateau + freeze decision belongs to the lead.")
    print("\nmultiplicity ledger: 12 prior + 4 SM = 16 candidates on the "
          "shared judgment window.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
