"""Round 22 phase-2/3 analysis of the venue recordings (read-only, deterministic).

Method is ported from report aa (board calibration) and e (cost calibration):
  * spread distribution in bps of mid, best-size medians, top-5 depth
  * trade frequency / notional per minute, 1-minute realised vol
  * virtual touch quote: place at best bid and best ask at each book snapshot,
    lifetime L seconds, fill ONLY on a print that trades THROUGH the level
    (strict traded-through = the repo's conservative maker rule),
    capture = (mid_fill - P)/mid, adverse(5s) = (mid_{fill+5} - mid_fill)/mid
  * cross-venue basis vs bitFlyer FX_BTC_JPY and lead-lag on a 5s grid
Sanity: UTC normalisation cross-check, gap ledger, no look-ahead (fills use
prints strictly after the snapshot time).
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "run1")
L_LIFE = 10.0
ADV_H = 5.0
GRID = 5.0

BOOKS = {
    "bf_fxbtc": ("bitFlyer CFD", "FX_BTC_JPY", 2.0),
    "bf_btc": ("bitFlyer spot", "BTC_JPY", 5.0),
    "bf_xrp": ("bitFlyer spot", "XRP_JPY", 4.0),
    "bb_btc": ("bitbank", "BTC_JPY", 2.0),
    "bb_xrp": ("bitbank", "XRP_JPY", 2.0),
    "bb_eth": ("bitbank", "ETH_JPY", 4.0),
    "gmo_btc": ("GMO spot", "BTC", 3.0),
    "gmo_btclev": ("GMO lev", "BTC_JPY", 3.0),
    "cc_btc": ("Coincheck", "BTC_JPY", 3.0),
    "okj_btc": ("OKJ", "BTC-JPY", 3.0),
    "bt_btc": ("BitTrade", "btcjpy", 3.0),
}
# maker fee in bps (negative fee = positive rebate credit), taker fee in bps
FEES = {  # (maker_fee_bps, taker_fee_bps)  fee>0 = you pay
    "bf_fxbtc": (0.0, 0.0),
    "bf_btc": (15.0, 15.0),
    "bf_xrp": (15.0, 15.0),
    "bb_btc": (0.0, 10.0),
    "bb_xrp": (-2.0, 12.0),
    "bb_eth": (-2.0, 12.0),
    "gmo_btc": (-1.0, 5.0),
    "gmo_btclev": (0.0, 0.0),
    "cc_btc": (0.0, 0.0),
    "okj_btc": (7.0, 14.0),
    "bt_btc": (0.0, 10.0),
}
TICK = {  # quote increment in JPY (from each venue's published product spec)
    "bf_fxbtc": 1.0, "bf_btc": 1.0, "bf_xrp": 0.001,
    "bb_btc": 1.0, "bb_xrp": 0.001, "bb_eth": 1.0,
    "gmo_btc": 1.0, "gmo_btclev": 1.0, "cc_btc": 1.0, "okj_btc": 1.0, "bt_btc": 1.0,
}
SLIP = 2.0  # repo-measured slippage assumption, bps one way
ADV_PRIOR = 1.2  # bps
BAS1M = {}  # adverse-selection prior, bps (report aa: adv(5s) = -1.32 at the touch)


def load_books(job):
    p = os.path.join(OUT, job + "_book.jsonl")
    if not os.path.exists(p):
        return None
    t, bp, bq, ap, aq, dep = [], [], [], [], [], []
    tv = []
    with open(p) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except Exception:
                continue
            if not r["b"] or not r["a"]:
                continue
            t.append(r["t"]); tv.append(r["tv"] if r["tv"] else np.nan)
            bp.append(r["b"][0][0]); bq.append(r["b"][0][1])
            ap.append(r["a"][0][0]); aq.append(r["a"][0][1])
            dep.append(sum(x[0] * x[1] for x in r["b"][:5]) + sum(x[0] * x[1] for x in r["a"][:5]))
    if len(t) < 10:
        return None
    d = {k: np.asarray(v, dtype=float) for k, v in
         dict(t=t, tv=tv, bp=bp, bq=bq, ap=ap, aq=aq, dep=dep).items()}
    o = np.argsort(d["t"])
    for k in d:
        d[k] = d[k][o]
    d["mid"] = (d["bp"] + d["ap"]) / 2.0
    d["spr"] = (d["ap"] - d["bp"]) / d["mid"] * 1e4
    return d


def load_trades(job):
    """Merge the first-pass tape with the supplementary *_trade2 tape, dedup by venue id."""
    paths = [os.path.join(OUT, job + "_trade.jsonl"), os.path.join(OUT, job + "_trade2.jsonl")]
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return None
    seen = set()
    ts, px, qq, sd = [], [], [], []
    for p in paths:
        with open(p) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("ts") is None:
                    continue
                k = r["id"]
                if k in seen:
                    continue
                seen.add(k)
                ts.append(r["ts"]); px.append(r["p"]); qq.append(r["q"]); sd.append(r.get("side", ""))
    if len(ts) < 10:
        return None
    a = {k: np.asarray(v) for k, v in dict(ts=ts, px=px, q=qq).items()}
    a["ts"] = a["ts"].astype(float); a["px"] = a["px"].astype(float); a["q"] = a["q"].astype(float)
    o = np.argsort(a["ts"])
    for k in a:
        a[k] = a[k][o]
    a["side"] = np.asarray(sd)[o]
    return a


def q(x, p):
    return float(np.percentile(x, p))


def gridify(d, t0, t1):
    """last-observation-carried-forward mid on a GRID-second grid."""
    g = np.arange(math.ceil(t0 / GRID) * GRID, t1, GRID)
    idx = np.searchsorted(d["t"], g, side="right") - 1
    ok = idx >= 0
    out = np.full(len(g), np.nan)
    stale = np.full(len(g), np.inf)
    out[ok] = d["mid"][idx[ok]]
    stale[ok] = g[ok] - d["t"][idx[ok]]
    out[stale > 3 * GRID] = np.nan
    return g, out


def virtual_quotes(bk, tr, mid_t, mid_v):
    """Touch quotes: fill only on a strict traded-through print within L_LIFE."""
    res = {"n_placed": 0, "n_fill": 0, "cap": [], "adv": [], "tf": []}
    tts, tpx = tr["ts"], tr["px"]
    for side in ("bid", "ask"):
        P = bk["bp"] if side == "bid" else bk["ap"]
        for i in range(len(bk["t"])):
            t0 = bk["t"][i]
            res["n_placed"] += 1
            lo = np.searchsorted(tts, t0, side="right")
            hi = np.searchsorted(tts, t0 + L_LIFE, side="right")
            if hi <= lo:
                continue
            seg_p = tpx[lo:hi]
            through = seg_p < P[i] if side == "bid" else seg_p > P[i]
            w = np.flatnonzero(through)
            if w.size == 0:
                continue
            tf = tts[lo + w[0]]
            m_f = np.interp(tf, mid_t, mid_v, left=np.nan, right=np.nan)
            m_a = np.interp(tf + ADV_H, mid_t, mid_v, left=np.nan, right=np.nan)
            if tf + ADV_H > mid_t[-1]:
                continue
            if not np.isfinite(m_f) or not np.isfinite(m_a):
                continue
            sgn = 1.0 if side == "bid" else -1.0
            res["n_fill"] += 1
            res["cap"].append(sgn * (m_f - P[i]) / m_f * 1e4)
            res["adv"].append(sgn * (m_a - m_f) / m_f * 1e4)
            res["tf"].append(tf)
    return res


def block_boot(vals, times, block=60.0, nb=2000, seed=20260827):
    """Moving-block bootstrap over 60s time blocks (fills inside a block are correlated)."""
    vals = np.asarray(vals, dtype=float)
    times = np.asarray(times, dtype=float)
    if len(vals) < 10:
        return (np.nan, np.nan)
    key = np.floor((times - times.min()) / block).astype(int)
    groups = [vals[key == k] for k in np.unique(key)]
    groups = [g for g in groups if len(g)]
    if len(groups) < 5:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    n = len(groups)
    means = np.empty(nb)
    for i in range(nb):
        pick = rng.integers(0, n, n)
        means[i] = np.concatenate([groups[j] for j in pick]).mean()
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def ci95(x):
    x = np.asarray(x, dtype=float)
    if len(x) < 5:
        return (np.nan, np.nan)
    se = x.std(ddof=1) / math.sqrt(len(x))
    return (x.mean() - 1.96 * se, x.mean() + 1.96 * se)


def main():
    rows = {}
    books, trades = {}, {}
    t0g, t1g = -np.inf, np.inf
    for job in BOOKS:
        b = load_books(job)
        if b is None:
            continue
        books[job] = b
        trades[job] = load_trades(job)
        t0g = max(t0g, b["t"][0]); t1g = min(t1g, b["t"][-1])
    print(f"# common window UTC {t0g:.0f}..{t1g:.0f}  = {(t1g-t0g)/3600:.2f} h")
    import datetime as dt
    print("# sanity  local-clock:", dt.datetime.now(dt.timezone.utc).isoformat())

    grids = {}
    for job, b in books.items():
        gt, gm = gridify(b, t0g, t1g)
        grids[job] = (gt, gm)

    print("\n## per venue/pair  (spread in bps of mid; tick_p50 = median spread in ticks)")
    hdr = ("job", "n", "gaps", "sp_p10", "sp_p50", "sp_p90", "spr_tick", "lock%",
           "bestJPY", "dep5JPY", "trd/min", "JPY/min", "vol1m", "eff_hsp", "clk_s")
    print(" | ".join(f"{h:>9s}" for h in hdr))
    for job, b in books.items():
        nom = BOOKS[job][2]
        dt_ = np.diff(b["t"])
        gaps = int((dt_ > 3 * nom).sum())
        bestjpy = float(np.median(np.concatenate([b["bq"] * b["bp"], b["aq"] * b["ap"]])))
        tick = TICK[job]
        nticks = (b["ap"] - b["bp"]) / tick
        lockpct = 100.0 * float((nticks <= 1.5).mean())
        tr = trades.get(job)
        span_min = (b["t"][-1] - b["t"][0]) / 60.0
        eff = float("nan")
        if tr is not None:
            m = (tr["ts"] >= b["t"][0]) & (tr["ts"] <= b["t"][-1])
            tpm = float(m.sum()) / span_min
            jpm = float((tr["px"][m] * tr["q"][m]).sum()) / span_min
            if m.sum() > 20:  # realised half-spread from the tape (report aa method)
                mm_ = np.interp(tr["ts"][m], b["t"], b["mid"])
                eff = float(np.median(np.abs(tr["px"][m] - mm_) / mm_ * 1e4))
        else:
            tpm = jpm = float("nan")
        gt, gm = grids[job]
        step = int(60 / GRID)
        r = np.diff(np.log(gm[::step]))
        r = r[np.isfinite(r)]
        v1 = float(np.std(r) * 1e4) if len(r) > 5 else float("nan")
        clk = float(np.nanmedian(b["t"] - b["tv"])) if np.isfinite(b["tv"]).any() else float("nan")
        print(f"{job:>9s} | {len(b['t']):>9d} | {gaps:>9d} | "
              f"{q(b['spr'],10):>9.3f} | {q(b['spr'],50):>9.3f} | {q(b['spr'],90):>9.3f} | "
              f"{float(np.median(nticks)):>9.1f} | {lockpct:>8.1f}% | {bestjpy:>9.0f} | "
              f"{float(np.median(b['dep'])):>9.0f} | {tpm:>9.2f} | {jpm:>9.0f} | {v1:>9.2f} | "
              f"{eff:>9.3f} | {clk:>9.2f}")
        rows[job] = dict(n=len(b["t"]), gaps=gaps, p10=q(b["spr"], 10), p50=q(b["spr"], 50),
                         p90=q(b["spr"], 90), tick_p50=float(np.median(nticks)), lock=lockpct,
                         best=bestjpy, dep=float(np.median(b["dep"])),
                         tpm=tpm, jpm=jpm, v1=v1, eff_hsp=eff, clk=clk,
                         maker_fee=FEES[job][0], taker_fee=FEES[job][1])

    print("\n## virtual touch quotes (traded-through, L=%.0fs, adv=%.0fs)" % (L_LIFE, ADV_H))
    print(f"{'job':>10s} | {'placed':>7s} | {'fills':>6s} | {'f%':>6s} | {'cap':>7s} | {'adv5':>7s} | {'cap+adv':>8s} | {'CI95':>18s} | {'+rebate':>8s}")
    for job, b in books.items():
        tr = trades.get(job)
        if tr is None:
            continue
        r = virtual_quotes(b, tr, b["t"], b["mid"])  # raw book mid, finer than the 5s grid
        if r["n_fill"] < 5:
            print(f"{job:>10s} | {r['n_placed']:>7d} | {r['n_fill']:>6d} |    n/a")
            continue
        cap = np.array(r["cap"]); adv = np.array(r["adv"]); tot = cap + adv
        lo, hi = block_boot(tot, r["tf"])
        reb = -FEES[job][0]
        print(f"{job:>10s} | {r['n_placed']:>7d} | {r['n_fill']:>6d} | "
              f"{100*r['n_fill']/r['n_placed']:>5.1f}% | {cap.mean():>7.3f} | {adv.mean():>7.3f} | "
              f"{tot.mean():>8.3f} | [{lo:>7.3f},{hi:>7.3f}] | {tot.mean()+reb:>8.3f}")
        rows[job].update(cap=float(cap.mean()), adv=float(adv.mean()), tot=float(tot.mean()),
                         ci=(float(lo), float(hi)), f=100 * r["n_fill"] / r["n_placed"],
                         nfill=r["n_fill"])

    print("\n## basis vs bitFlyer FX_BTC_JPY (bps, 5s grid) + lead-lag")
    ref = "bf_fxbtc"
    gt, gref = grids[ref]
    lr_ref = np.diff(np.log(gref))
    print(f"{'job':>10s} | {'n':>6s} | {'mean':>8s} | {'sd':>7s} | {'AR1rho':>7s} | {'half-life':>10s} | lag corr (venue leads bfFX at negative lag)")
    for job in books:
        if job == ref or "btc" not in job.lower():
            continue
        _, gv = grids[job]
        bas = (gv - gref) / gref * 1e4
        m = np.isfinite(bas)
        if m.sum() < 50:
            continue
        bb = bas[m]
        x0, x1 = bb[:-1], bb[1:]
        rho = float(np.corrcoef(x0 - x0.mean(), x1 - x1.mean())[0, 1])
        hl = GRID * math.log(0.5) / math.log(rho) / 60.0 if 0 < rho < 1 else float("nan")
        # 1-minute grid AR(1) as well, to be comparable with report f (1m data, HL 9.1min)
        b1 = bas[::int(60 / GRID)]
        b1 = b1[np.isfinite(b1)]
        hl1 = float("nan")
        if len(b1) > 30:
            r1 = float(np.corrcoef(b1[:-1] - b1[:-1].mean(), b1[1:] - b1[1:].mean())[0, 1])
            if 0 < r1 < 1:
                hl1 = math.log(0.5) / math.log(r1)
        BAS1M[job] = (float(bb.mean()), float(bb.std()), hl1)
        lrv = np.diff(np.log(gv))
        cs = []
        for lag in (-2, -1, 0, 1, 2):
            if lag < 0:
                a, c = lrv[:lag], lr_ref[-lag:]
            elif lag > 0:
                a, c = lrv[lag:], lr_ref[:-lag]
            else:
                a, c = lrv, lr_ref
            mm = np.isfinite(a) & np.isfinite(c)
            cs.append(float(np.corrcoef(a[mm], c[mm])[0, 1]) if mm.sum() > 50 else float("nan"))
        print(f"{job:>10s} | {int(m.sum()):>6d} | {bb.mean():>8.2f} | {bb.std():>7.2f} | "
              f"{rho:>7.4f} | {hl:>8.2f}m | " + "  ".join(f"L{l:+d}:{c:+.3f}" for l, c in zip((-2, -1, 0, 1, 2), cs)))

    # XRP cross-venue
    if "bb_xrp" in grids and "bf_xrp" in grids:
        _, a = grids["bb_xrp"]; _, c = grids["bf_xrp"]
        la, lc = np.diff(np.log(a)), np.diff(np.log(c))
        print("\n## XRP_JPY bitbank vs bitFlyer spot lead-lag (5s grid)")
        for lag in (-2, -1, 0, 1, 2):
            if lag < 0:
                x, y = la[:lag], lc[-lag:]
            elif lag > 0:
                x, y = la[lag:], lc[:-lag]
            else:
                x, y = la, lc
            mm = np.isfinite(x) & np.isfinite(y)
            print(f"  lag {lag:+d} (bitbank leads if <0): corr={np.corrcoef(x[mm],y[mm])[0,1]:+.3f} n={mm.sum()}")

    print("\n## basis on a 1-minute grid (comparable with report f: HL 9.1 min)")
    for j, (m, sd, hl) in BAS1M.items():
        print(f"  {j:>10s}  mean {m:+7.2f} bps  sd {sd:5.2f}  AR1 half-life {hl:6.2f} min")

    print("\n## fee-vs-spread substitution check (taker fee bps vs measured spread p50 bps)")
    xs = [FEES[j][1] for j in rows]
    ys = [rows[j]["p50"] for j in rows]
    if len(xs) > 4:
        print(f"  corr(taker_fee, spread_p50) = {np.corrcoef(xs, ys)[0,1]:+.3f}  n={len(xs)} venues/pairs")
    btc = [j for j in rows if j.endswith("btc") or j in ("bf_fxbtc", "gmo_btclev", "bb_btc")]
    xs2 = [FEES[j][1] for j in btc]; ys2 = [rows[j]["p50"] for j in btc]
    if len(xs2) > 4:
        print(f"  BTC/JPY only:               {np.corrcoef(xs2, ys2)[0,1]:+.3f}  n={len(xs2)}")

    print("\n## report-f basis re-audit: is a CFD-vs-spot convergence trade reachable now?")
    print("  report f rejected it with a spot leg costing 55bps round trip (taker 0.15% + 0.15% spread).")
    print("  Below: the spot leg re-priced at today's fees, judged against report f's MEASURED")
    print("  gross convergence (+2.7bps = spot +5.5 catch-up minus CFD +2.8 co-drift), NOT the sd.")
    print("  'total best' assumes ALL FOUR legs fill as maker - which the repo's sign law says")
    print("  cannot happen on the side the price is moving toward. It is an optimistic bound.")
    print(f"  {'spot venue':>10s} | {'basis sd':>8s} | {'2sd move':>8s} | {'spot taker RT':>13s} | "
          f"{'spot maker RT(meas)':>19s} | {'CFD leg RT':>10s} | {'total taker':>11s} | {'total best':>10s} | vs f +2.7bps")
    F_GROSS = 2.7  # bps, report f: spot +5.5 catch-up minus CFD +2.8 same-direction drift
    cfd_t = rows["bf_fxbtc"]["cost_floor"] if "cost_floor" in rows.get("bf_fxbtc", {}) else \
        2 * FEES["bf_fxbtc"][1] + rows["bf_fxbtc"]["p50"] + 2 * SLIP
    cfd_m = -2.0 * rows["bf_fxbtc"].get("tot", float("nan"))  # cost of two maker legs
    for job in ("bb_btc", "gmo_btc", "cc_btc", "bt_btc", "okj_btc"):
        if job not in rows or job not in BAS1M:
            continue
        sd = BAS1M[job][1]
        tk = 2 * FEES[job][1] + rows[job]["p50"] + 2 * SLIP
        mk = -2.0 * (rows[job].get("tot", float("nan")) - FEES[job][0])
        tot_t = tk + cfd_t
        tot_b = mk + cfd_m
        # report f measured the ACTUAL gross convergence, not the sd: at rich deviations the
        # spot leg rose +5.5bps while the CFD drifted +2.8bps the same way => +2.7bps gross.
        # 2sd is the size of the wiggle, NOT the edge; comparing to it would be the classic
        # "confuse volatility with profit" error. Bar = report f's +2.7bps gross.
        v = "reachable" if F_GROSS > tot_b else "dead"
        print(f"  {job:>10s} | {sd:>8.2f} | {2*sd:>8.2f} | {tk:>13.2f} | {mk:>19.2f} | "
              f"{cfd_m:>10.2f} | {tot_t:>11.2f} | {tot_b:>10.2f} | {v}")

    print("\n## PHASE 3 efficiency-gap map")
    print(f"{'job':>10s} | {'m/t fee bps':>12s} | {'spr p50':>8s} | {'COSTFLOOR':>9s} | "
          f"{'maker_raw':>9s} | {'maker_meas':>10s} | {'JPY/min':>9s} | {'dep5JPY':>9s}")
    print("  COSTFLOOR = 2*taker_fee + spread_p50 + 2*slip ;  "
          "maker_raw = 0.5*half_spread + rebate - 1.2 ;  maker_meas = cap+adv(5s) + rebate")
    for job, r in rows.items():
        mk, tk = FEES[job]
        floor = 2 * tk + r["p50"] + 2 * SLIP
        raw = 0.5 * (r["p50"] / 2.0) - mk - ADV_PRIOR
        meas = (r["tot"] - mk) if "tot" in r else float("nan")
        r["cost_floor"] = floor; r["maker_raw"] = raw; r["maker_meas"] = meas
        print(f"{job:>10s} | {mk:>5.1f}/{tk:<6.1f} | {r['p50']:>8.3f} | {floor:>9.2f} | "
              f"{raw:>9.2f} | {meas:>10.2f} | {r['jpm']:>9.0f} | {r['dep']:>9.0f}")

    print("\n## first-half / second-half stability (the repo's 前後半 rule)")
    tmid = 0.5 * (t0g + t1g)
    print(f"{'job':>10s} | {'spr p50 H1':>10s} | {'spr p50 H2':>10s} | {'cap+adv H1':>10s} | {'cap+adv H2':>10s} | {'fill H1/H2':>12s}")
    for job, b in books.items():
        tr = trades.get(job)
        h1 = b["t"] <= tmid
        s1 = float(np.median(b["spr"][h1])) if h1.sum() > 10 else float("nan")
        s2 = float(np.median(b["spr"][~h1])) if (~h1).sum() > 10 else float("nan")
        c1 = c2 = float("nan"); n1 = n2 = 0
        if tr is not None:
            r = virtual_quotes(b, tr, b["t"], b["mid"])
            if r["n_fill"] > 10:
                tf = np.asarray(r["tf"]); tot = np.asarray(r["cap"]) + np.asarray(r["adv"])
                m1 = tf <= tmid
                n1, n2 = int(m1.sum()), int((~m1).sum())
                if n1 > 5: c1 = float(tot[m1].mean())
                if n2 > 5: c2 = float(tot[~m1].mean())
        print(f"{job:>10s} | {s1:>10.3f} | {s2:>10.3f} | {c1:>10.3f} | {c2:>10.3f} | {n1:>5d}/{n2:<6d}")

    print("\n## cross-asset lead-lag on the 5s grid (report b re-test: does BTC still lead XRP?)")
    pairs = [("bf_fxbtc", "bb_xrp"), ("bf_fxbtc", "bb_eth"), ("bb_btc", "bb_xrp"),
             ("bf_fxbtc", "bf_xrp"), ("bf_fxbtc", "bb_btc")]
    for lead, foll in pairs:
        if lead not in grids or foll not in grids:
            continue
        la = np.diff(np.log(grids[lead][1])); lf = np.diff(np.log(grids[foll][1]))
        line = []
        for lag in (0, 1, 2, 3):
            x = la[:-lag] if lag else la
            y = lf[lag:] if lag else lf
            mm = np.isfinite(x) & np.isfinite(y)
            line.append(f"lag{lag}:{np.corrcoef(x[mm], y[mm])[0,1]:+.3f}")
        print(f"  {lead:>10s} -> {foll:<10s} " + "  ".join(line) + f"   n={int(mm.sum())}")

    with open(os.path.join(OUT, "summary.json"), "w") as fh:
        json.dump(rows, fh, indent=1, default=float)


if __name__ == "__main__":
    main()
