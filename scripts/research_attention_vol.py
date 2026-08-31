"""EXPLORATORY: does crowd attention correlate with short-horizon volatility?

Owner question (2026-08-31): 短期の値動きにも加熱度と相関があるのか(嵐との相関があればベスト).
Direction-prediction is already closed (SURVEY_ATTENTION_DATA + KNOWLEDGE §3);
this measures MAGNITUDE only — squarely inside our magnitude-not-direction law.

Honesty rules baked in:
- Publication lags are enforced: a Wikipedia z usable on day t is computed from
  data through t-2 (the API publishes at D-2); GDELT/F&G are same-day usable.
- The giant confounder is volatility clustering (yesterday's range predicts
  tomorrow's range all by itself).  Every predictive readout is therefore shown
  BOTH raw and inside trailing-vol terciles (two-way sort), so "attention adds
  nothing beyond vol clustering" is a visible outcome, not a hidden one.
- This is exploration on the full 2015-2026 panel: nothing here can be adopted;
  a positive finding feeds a NEW PREREG (vol-gate design), not a strategy.

Data: data/attention/attention.csv (daily OHLC + attention series).
Metrics: range_t = (high-low)/close in %, storm-day defs |ret|>=3% and range>=5%.
Seed-free (no resampling); Spearman rank correlations with a normal-approx t.
"""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "attention" / "attention.csv"

WP_LAG = 2      # Wikipedia publishes at D-2: z usable on day t is from day t-2
RT_LAG = 0      # GDELT timelinevol / F&G are same-day usable


def rolling_z(pts: list[tuple[str, float]], win: int = 365) -> dict[str, float]:
    out: dict[str, float] = {}
    vals = [v for _, v in pts]
    for i in range(win, len(pts)):
        w = vals[i - win:i]
        m = statistics.fmean(w)
        sd = statistics.stdev(w)
        if sd > 0:
            out[pts[i][0]] = (vals[i] - m) / sd
    return out


def spearman(x: list[float], y: list[float]) -> tuple[float, float]:
    n = len(x)
    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    sx, sy = statistics.stdev(rx), statistics.stdev(ry)
    rho = sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / ((n - 1) * sx * sy)
    t = rho * math.sqrt((n - 2) / max(1e-12, 1 - rho * rho))
    return rho, t


def tercile(v: float, cuts: tuple[float, float]) -> int:
    return 0 if v <= cuts[0] else (1 if v <= cuts[1] else 2)


def main() -> None:
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    days = [r["date"] for r in rows]
    idx = {d: i for i, d in enumerate(days)}

    z = {}
    for key, lag in (("wp_ja", WP_LAG), ("wp_en", WP_LAG), ("gdelt_vol", RT_LAG)):
        pts = [(r["date"], math.log(float(r[key]) + 1.0)) for r in rows if r.get(key)]
        raw = rolling_z(pts)
        # shift by publication lag: usable_z[t] = raw z of day t-lag
        z[key] = {}
        for d, v in raw.items():
            i = idx.get(d)
            if i is not None and i + lag < len(days):
                z[key][days[i + lag]] = v

    rng, ret = {}, {}
    for r in rows:
        if r.get("btc_high") and r.get("btc_low") and r.get("btc_usd"):
            c = float(r["btc_usd"])
            rng[r["date"]] = (float(r["btc_high"]) - float(r["btc_low"])) / c * 100
    for a, b in zip(rows, rows[1:]):
        if a.get("btc_usd") and b.get("btc_usd"):
            ret[b["date"]] = (float(b["btc_usd"]) / float(a["btc_usd"]) - 1) * 100

    # trailing 5-day mean range (through t) = the vol-clustering control
    trail = {}
    for i, d in enumerate(days):
        w = [rng[days[j]] for j in range(max(0, i - 4), i + 1) if days[j] in rng]
        if len(w) == 5:
            trail[d] = statistics.fmean(w)

    print("=" * 96)
    print("EXPLORATORY -- attention z vs short-horizon volatility (2015-2026 daily panel)")
    print("=" * 96)
    print(f"days with range: {len(rng)}, publication lags enforced: WP D-{WP_LAG}, GDELT/F&G D-{RT_LAG}")

    for key in ("wp_ja", "wp_en", "gdelt_vol"):
        shared0 = [d for d in days if d in z[key] and d in rng]
        rho0, t0 = spearman([z[key][d] for d in shared0], [rng[d] for d in shared0])
        # predictive: z usable on t vs range on t+1
        shared1 = [d for d in days if d in z[key] and idx[d] + 1 < len(days)
                   and days[idx[d] + 1] in rng and d in trail]
        zs = [z[key][d] for d in shared1]
        nx = [rng[days[idx[d] + 1]] for d in shared1]
        rho1, t1 = spearman(zs, nx)
        print(f"\n[{key}] same-day rho {rho0:+.3f} (t={t0:+.1f}, n={len(shared0)})   "
              f"next-day rho {rho1:+.3f} (t={t1:+.1f}, n={len(shared1)})")

        # two-way sort: trailing-vol terciles x z terciles -> mean next-day range
        tv = sorted(trail[d] for d in shared1)
        zv = sorted(zs)
        tcuts = (tv[len(tv) // 3], tv[2 * len(tv) // 3])
        zcuts = (zv[len(zv) // 3], zv[2 * len(zv) // 3])
        cells: dict[tuple[int, int], list[float]] = {}
        for d, zval, nxt in zip(shared1, zs, nx):
            cells.setdefault((tercile(trail[d], tcuts), tercile(zval, zcuts)), []).append(nxt)
        print("  next-day range %% by trailing-vol tercile (rows) x attention-z tercile (cols):")
        print("             z-low   z-mid  z-high   (n per cell)")
        for tv_i, label in enumerate(("vol-low ", "vol-mid ", "vol-high")):
            vals = [cells.get((tv_i, zi), []) for zi in range(3)]
            means = "  ".join(f"{statistics.fmean(v):6.2f}" if v else "     -" for v in vals)
            ns = "/".join(str(len(v)) for v in vals)
            print(f"    {label} {means}   ({ns})")

        # storm-day lift within the calm regime (the tradable question)
        for sd_label, storm_days in (("|ret|>=3%", {d for d in ret if abs(ret[d]) >= 3}),
                                     ("range>=5%", {d for d in rng if rng[d] >= 5})):
            calm = [d for d in shared1 if tercile(trail[d], tcuts) == 0]
            if not calm:
                continue
            base = statistics.fmean(1.0 if days[idx[d] + 1] in storm_days else 0.0 for d in calm)
            hot = [d for d in calm if tercile(z[key][d], zcuts) == 2]
            p_hot = statistics.fmean(1.0 if days[idx[d] + 1] in storm_days else 0.0 for d in hot) if hot else float("nan")
            print(f"  P(storm {sd_label} tomorrow | calm regime): base {base:.1%} vs z-high {p_hot:.1%} (n={len(hot)})")

    # lead-lag: does attention lead vol or follow it?  corr(range_t, rawz_{t+k})
    print("\nlead-lag (gdelt_vol, no usable-lag shift): rho(range_t, z_{t+k})")
    raw_g = rolling_z([(r["date"], math.log(float(r["gdelt_vol"]) + 1.0))
                       for r in rows if r.get("gdelt_vol")])
    for k in (-5, -2, -1, 0, 1, 2, 5):
        shared = [d for d in days if d in rng and idx[d] + k < len(days)
                  and idx[d] + k >= 0 and days[idx[d] + k] in raw_g]
        rho, t = spearman([rng[d] for d in shared], [raw_g[days[idx[d] + k]] for d in shared])
        print(f"  k={k:+d}: rho {rho:+.3f} (t={t:+.1f}, n={len(shared)})")

    print("\nEXPLORATION ONLY: nothing above is adopted; a surviving effect needs a new PREREG.")


if __name__ == "__main__":
    main()
