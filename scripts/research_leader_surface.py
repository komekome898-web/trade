"""EXPLORATION ONLY -- leader-momentum parameter SURFACE autopsy (no adoption).

================================================================================
PRE-REGISTRATION (frozen before the first run; research-protocol sec.1 + sec.10)
================================================================================

WHY THIS EXISTS
---------------
The main-BOT champion (xborder_momentum, k=30, thr=0.8%, exit=0.05%) was
REJECTED in report 22 (docs/RESEARCH_REPORT_2026-08-25w.md): 30 paper trades,
net -0.148%/trade, day-cluster CI [-0.243, +0.063] excluding the +0.15% bar.
That verdict kills ONE POINT.  research-protocol sec.10 requires that a
rejection report state the LEVEL of the death: "mechanism-level" (an arithmetic
no parameter can beat) or "point-level" (only the tested cell died).  To say
which, the whole Binance->bitFlyer leader-follow SURFACE must be measured.

This script is EXPLORATION on contaminated (already-seen) data.  It CANNOT and
DOES NOT adopt anything.  Its outputs are a map, plus at most 2 candidate cells
handed to the lead for possible future pre-registration on fresh data.

DATA (read-only; no network; deterministic)
-------------------------------------------
  bitFlyer traded leg : backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz
                        1m bars built from the 31d execution tape,
                        TRUNCATED to ts < 2026-08-20T08:22:17Z (FRESH_CUTOFF).
                        The fresh region (the paper-judgment period) is NEVER
                        read by this script.
  Binance leader      : data.binance.vision daily 1m klines BTCUSDT,
                        2026-07-23 .. 2026-08-19, already downloaded to
                        <scratchpad>/binance/BTCUSDT-1m-YYYY-MM-DD.zip.
                        Timestamps are MICROSECONDS (KNOWLEDGE sec.6).
  Long proxy          : data/binance_BTCUSDT_1m_full.csv (210d, 2026-01-22 ..
                        2026-08-20).  Binance is BOTH the traded leg and its own
                        leader there (same construction as
                        scripts/research_tournament.py:make_secondary), so it
                        measures MOMENTUM CONTINUATION, not cross-exchange lag.
                        Reported as a regime-dependency probe only.

CONFIGURATION FAMILY (enumerated; nothing added afterwards)
-----------------------------------------------------------
  signal cells        : k in {5, 10, 30, 60, 120} minutes
                        thr in {0.2, 0.4, 0.8, 1.2, 1.6} %            -> 25 cells
  entry delay         : d in {0, 1, 5, 15} minutes                    -> x4
  forward horizon     : h in {5, 15, 30, 60, 240} minutes             -> x5
  regimes             : all / calm / mid / storm (daily realized-vol
                        tertiles of bitFlyer 1m returns)              -> x4
  TOTAL MEASUREMENT CELLS = 25 * 4 * 5 * 4 = 2000 (reported in the output).

SIGNAL (identical to src/bot/strategy/xborder_momentum.py)
----------------------------------------------------------
  mom_t = log(leader_close[t] / leader_close[t-k])
  fire LONG  when mom_t >  thr/100
  fire SHORT when mom_t < -thr/100
  Both leader closes are COMPLETED bars at the moment bar t closes -> the
  entry timestamp is bar t's close; zero look-ahead by construction.
  An EVENT is the RISING EDGE of the firing condition per direction (the bot
  enters once and holds), and events are additionally de-overlapped by a
  position-occupancy rule in the exit simulation.

MEASURED QUANTITY (cost-free drift surface)
-------------------------------------------
  drift(d, h) = sign(mom) * (bf_close[i+d+h] / bf_close[i+d] - 1) * 100  [%]
  i = firing bar index on the joined bitFlyer/Binance frame.
  Reported with n, mean, median, and day-clustered bootstrap 95% CI
  (seed 20260825, 2000 resamples) for the principal cells.

COST LINES OVERLAID (KNOWLEDGE sec.1 / report 22)
--------------------------------------------------
  taker round trip      = 7.92 bps = 0.0792 %
  paper-measured charge = 13.0 bps = 0.13 %

EXIT COMPOSITION (top drift cells only)
---------------------------------------
  A) current champion exit : signal fade |mom| <= exit_pct (0.05%)
                             + 0.5% protective stop (intrabar high/low)
                             + 240-bar time cap
  B) time-only exit        : hold exactly H in {30, 60, 240} bars
  Both taker both legs, no position overlap, cost applied at 7.92 and 13.0 bps.

SANITY GATES (all must print PASS before results are read)
-----------------------------------------------------------
  S1 look-ahead zero      : signal window ends at the entry bar's close;
                            an explicit shift-by-one control must not change n.
  S2 epoch cross-check    : (idx - 1970-01-01)/1s round trip, per sec.6.
  S3 clock alignment      : bitFlyer vs Binance contemporaneous correlation is
                            the argmax over lags -3..+3 (bars align to the same
                            minute boundary => |offset| < 5 s).
  S4 determinism          : bootstrap seeded; re-run byte-identical.
  S5 fresh-data guard     : max(ts) < FRESH_CUTOFF asserted.

WHAT THIS SCRIPT MAY CONCLUDE
------------------------------
  Only: where on the surface the leader-follow edge lives, where it does not,
  and whether the champion's adoption-time +0.19..+0.36%/trade (n=15) sits at an
  ordinary or an extreme quantile of that surface.  ADOPTION IS OUT OF SCOPE.

Run:  PYTHONPATH=src python scripts/research_leader_surface.py
"""
from __future__ import annotations

import glob
import os
import sys
import zipfile

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Frozen constants
# ---------------------------------------------------------------------------
SEED = 20260825
N_BOOT = 2000

FRESH_CUTOFF = pd.Timestamp("2026-08-20T08:22:17Z")

KS = (5, 10, 30, 60, 120)
THRS = (0.2, 0.4, 0.8, 1.2, 1.6)
DELAYS = (0, 1, 5, 15)
HORIZONS = (5, 15, 30, 60, 240)
REGIMES = ("all", "calm", "mid", "storm")

CHAMPION_K, CHAMPION_THR = 30, 0.8
CHAMPION_EXIT_PCT = 0.05
CHAMPION_STOP_PCT = 0.5
MAX_HOLD = 240

COST_TAKER_PCT = 0.0792   # 7.92 bps round trip
COST_PAPER_PCT = 0.13     # paper-charged round trip

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX_GZ = os.path.join(REPO, "backtest_data", "candles_FX_BTC_JPY_31d_20260823.csv.gz")
PROXY_CSV = os.path.join(REPO, "data", "binance_BTCUSDT_1m_full.csv")
SCRATCH = os.environ.get(
    "LEADER_SCRATCH",
    "/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad",
)
BINANCE_DIR = os.path.join(SCRATCH, "binance")

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def epoch_seconds(idx: pd.DatetimeIndex) -> np.ndarray:
    """research-protocol sec.6: the only safe datetime64 -> seconds conversion."""
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def hdr(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_bitflyer() -> pd.DataFrame:
    df = pd.read_csv(FX_GZ, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()
    return df.loc[df.index < FRESH_CUTOFF]


def load_binance_daily() -> pd.Series:
    files = sorted(glob.glob(os.path.join(BINANCE_DIR, "BTCUSDT-1m-*.zip")))
    if not files:
        sys.exit(f"no Binance 1m archives under {BINANCE_DIR}")
    frames = []
    for path in files:
        with zipfile.ZipFile(path) as zf:
            frames.append(pd.read_csv(zf.open(zf.namelist()[0]), header=None))
    raw = pd.concat(frames, ignore_index=True)
    # column 0 is open_time in MICROSECONDS (KNOWLEDGE sec.6)
    ts = pd.to_datetime(raw[0] // 1_000_000, unit="s", utc=True)
    out = pd.Series(raw[4].to_numpy(dtype=float), index=ts, name="leader_close")
    return out.sort_index()


def load_proxy() -> pd.DataFrame:
    df = pd.read_csv(PROXY_CSV, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()[["open", "high", "low", "close"]].dropna()
    df["leader_close"] = df["close"]
    return df


def build_frame() -> pd.DataFrame:
    fx = load_bitflyer()
    lead = load_binance_daily()
    j = fx.join(lead, how="inner").dropna()
    return j


# ---------------------------------------------------------------------------
# Regime labelling
# ---------------------------------------------------------------------------
def day_regimes(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Daily realized vol (std of 1m log returns) -> tertile label per UTC day."""
    r = np.log(df["close"]).diff()
    day = df.index.floor("D")
    rv = r.groupby(day).std() * 1e4  # bps
    rv = rv.dropna()
    q1, q2 = rv.quantile([1 / 3, 2 / 3])
    lab = pd.Series(
        np.where(rv <= q1, "calm", np.where(rv <= q2, "mid", "storm")),
        index=rv.index, name="regime")
    return rv, lab


# ---------------------------------------------------------------------------
# Signal / events
# ---------------------------------------------------------------------------
def momentum(lead: np.ndarray, k: int) -> np.ndarray:
    m = np.full(lead.shape, np.nan)
    m[k:] = np.log(lead[k:] / lead[:-k])
    return m


def rising_edges(mom: np.ndarray, thr_pct: float) -> tuple[np.ndarray, np.ndarray]:
    """Indices of the FIRST bar of each firing run, and their signs (+1/-1)."""
    thr = thr_pct / 100.0
    up = mom > thr
    dn = mom < -thr
    up = np.nan_to_num(up, nan=False).astype(bool)
    dn = np.nan_to_num(dn, nan=False).astype(bool)
    up_edge = up & ~np.r_[False, up[:-1]]
    dn_edge = dn & ~np.r_[False, dn[:-1]]
    idx = np.flatnonzero(up_edge | dn_edge)
    sign = np.where(up_edge[idx], 1.0, -1.0)
    return idx, sign


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def day_cluster_ci(values: np.ndarray, days: np.ndarray,
                   n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    if len(values) == 0:
        return (np.nan, np.nan)
    uniq = np.unique(days)
    if len(uniq) < 2:
        return (np.nan, np.nan)
    buckets = [values[days == d] for d in uniq]
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    nd = len(buckets)
    for b in range(n_boot):
        pick = rng.integers(0, nd, nd)
        means[b] = np.concatenate([buckets[p] for p in pick]).mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# ---------------------------------------------------------------------------
# Sanity gates
# ---------------------------------------------------------------------------
def sanity(df: pd.DataFrame) -> None:
    hdr("SANITY GATES")
    ok = True

    # S5 fresh-data guard
    s5 = df.index.max() < FRESH_CUTOFF
    print(f"  S5 fresh-data guard      : max(ts)={df.index.max()} < {FRESH_CUTOFF} "
          f"-> {'PASS' if s5 else 'FAIL'}")
    ok &= s5

    # S2 epoch cross-check
    sec = epoch_seconds(df.index)
    back = pd.to_datetime(sec, unit="s", utc=True)
    s2 = bool((back == df.index).all()) and float(sec[1] - sec[0]) == 60.0
    print(f"  S2 epoch cross-check     : first={sec[0]:.0f}s ({back[0]}), "
          f"step={sec[1]-sec[0]:.0f}s -> {'PASS' if s2 else 'FAIL'}")
    ok &= s2

    # S3 clock alignment
    r_bf = np.log(df["close"]).diff()
    r_ld = np.log(df["leader_close"]).diff()
    cors = {lag: float(r_bf.corr(r_ld.shift(lag))) for lag in range(-3, 4)}
    best = max(cors, key=lambda x: cors[x])
    s3 = best == 0
    print("  S3 clock alignment       : " +
          " ".join(f"lag{lag:+d}={cors[lag]:+.4f}" for lag in sorted(cors)))
    print(f"                             argmax lag={best:+d} (bars share the same "
          f"minute boundary, |offset|<5s) -> {'PASS' if s3 else 'FAIL'}")
    ok &= s3

    # S1 look-ahead zero: the momentum at bar i uses only closes at i and i-k.
    lead = df["leader_close"].to_numpy(float)
    m = momentum(lead, CHAMPION_K)
    manual = np.log(lead[CHAMPION_K] / lead[0])
    s1a = abs(manual - m[CHAMPION_K]) < 1e-12
    # control: a deliberately shifted (future-peeking) signal must differ
    m_peek = np.r_[m[1:], np.nan]
    idx_a, _ = rising_edges(m, CHAMPION_THR)
    idx_b, _ = rising_edges(m_peek, CHAMPION_THR)
    s1b = not np.array_equal(idx_a, idx_b)
    shared = len(np.intersect1d(idx_a, idx_b))
    print(f"  S1 look-ahead zero       : mom[k] reconstructed from closes[0],[k] "
          f"-> {'PASS' if s1a else 'FAIL'}; peek-control shifts the event set "
          f"(n {len(idx_a)} vs {len(idx_b)}, only {shared} indices shared) "
          f"-> {'PASS' if s1b else 'FAIL'}")
    ok &= s1a and s1b

    # S4 determinism
    a = day_cluster_ci(np.arange(100.0), np.repeat(np.arange(10), 10))
    b = day_cluster_ci(np.arange(100.0), np.repeat(np.arange(10), 10))
    s4 = a == b
    print(f"  S4 determinism           : seeded bootstrap reproduces "
          f"{a[0]:.6f} -> {'PASS' if s4 else 'FAIL'}")
    ok &= s4

    print(f"  OVERALL: {'ALL PASS' if ok else 'FAILURE -- do not read results'}")
    if not ok:
        sys.exit(1)


# ---------------------------------------------------------------------------
# 1. Firing frequency surface
# ---------------------------------------------------------------------------
def firing_table(df: pd.DataFrame, reg_of_day: pd.Series) -> dict:
    hdr("1. FIRING FREQUENCY SURFACE (events/day, rising-edge de-duplicated)")
    lead = df["leader_close"].to_numpy(float)
    days = df.index.floor("D")
    n_days = days.nunique()
    day_counts = days.value_counts()
    reg_days = {r: int((reg_of_day == r).sum()) for r in ("calm", "mid", "storm")}
    print(f"  span {df.index[0]} .. {df.index[-1]}  bars={len(df)}  days={n_days}")
    print(f"  regime days: calm={reg_days['calm']} mid={reg_days['mid']} "
          f"storm={reg_days['storm']}")

    store = {}
    print("\n  events/day  (rows k, cols thr%)")
    print("    k \\ thr " + "".join(f"{t:>9.1f}" for t in THRS))
    for k in KS:
        m = momentum(lead, k)
        row = []
        for thr in THRS:
            idx, sign = rising_edges(m, thr)
            store[(k, thr)] = (idx, sign)
            row.append(len(idx) / n_days)
        print(f"    {k:>6d}  " + "".join(f"{v:>9.2f}" for v in row))

    print("\n  raw n of events (rows k, cols thr%)")
    print("    k \\ thr " + "".join(f"{t:>9.1f}" for t in THRS))
    for k in KS:
        print(f"    {k:>6d}  " +
              "".join(f"{len(store[(k,t)][0]):>9d}" for t in THRS))

    print("\n  events/day BY REGIME  (calm / mid / storm)")
    print("    k \\ thr " + "".join(f"{t:>20.1f}" for t in THRS))
    day_of = pd.Series(days, index=range(len(df)))
    for k in KS:
        cells = []
        for thr in THRS:
            idx, _ = store[(k, thr)]
            ev_day = day_of.iloc[idx].to_numpy()
            ev_reg = reg_of_day.reindex(pd.DatetimeIndex(ev_day)).to_numpy()
            c = [(ev_reg == r).sum() / max(reg_days[r], 1)
                 for r in ("calm", "mid", "storm")]
            cells.append(f"{c[0]:>6.2f}/{c[1]:>5.2f}/{c[2]:>6.2f}")
        print(f"    {k:>6d}  " + "".join(f"{c:>20}" for c in cells))
    return store


# ---------------------------------------------------------------------------
# 2. Forward-drift surface
# ---------------------------------------------------------------------------
def drift_values(close: np.ndarray, idx: np.ndarray, sign: np.ndarray,
                 d: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    a = idx + d
    b = idx + d + h
    keep = b < len(close)
    a, b, s = a[keep], b[keep], sign[keep]
    val = s * (close[b] / close[a] - 1.0) * 100.0
    return val, idx[keep]


def drift_surface(df: pd.DataFrame, store: dict, reg_of_day: pd.Series) -> dict:
    hdr("2. FORWARD-DRIFT SURFACE, PRE-COST (signed % per event; + = with signal)")
    close = df["close"].to_numpy(float)
    days = df.index.floor("D")
    print(f"  cost lines: taker round trip {COST_TAKER_PCT:.4f}% "
          f"| paper-charged {COST_PAPER_PCT:.4f}%")

    results = {}
    for d in DELAYS:
        print(f"\n  --- entry delay d = {d}m ---")
        print("    k   thr      n " +
              "".join(f"{'h=%dm' % h:>12}" for h in HORIZONS))
        for k in KS:
            for thr in THRS:
                idx, sign = store[(k, thr)]
                cells = []
                n_show = 0
                for h in HORIZONS:
                    val, kept = drift_values(close, idx, sign, d, h)
                    n_show = len(val)
                    mean = val.mean() if len(val) else np.nan
                    results[(k, thr, d, h, "all")] = (val, kept)
                    cells.append(mean)
                mark = "  <== champion" if (k == CHAMPION_K and thr == CHAMPION_THR) else ""
                print(f"    {k:>3d} {thr:>4.1f} {n_show:>6d} " +
                      "".join(f"{c:>+12.4f}" for c in cells) + mark)

    print("\n  MEDIAN (delay d=0), same layout")
    print("    k   thr      n " + "".join(f"{'h=%dm' % h:>12}" for h in HORIZONS))
    for k in KS:
        for thr in THRS:
            idx, sign = store[(k, thr)]
            cells, n_show = [], 0
            for h in HORIZONS:
                val, _ = drift_values(close, idx, sign, 0, h)
                n_show = len(val)
                cells.append(np.median(val) if len(val) else np.nan)
            print(f"    {k:>3d} {thr:>4.1f} {n_show:>6d} " +
                  "".join(f"{c:>+12.4f}" for c in cells))

    # day-cluster CI on the cells that clear the taker line at d=0
    hdr("2b. DAY-CLUSTER 95% CI FOR CELLS ABOVE THE TAKER LINE (d=0)")
    print(f"  bootstrap: {N_BOOT} resamples of UTC days, seed {SEED}")
    print("    k   thr    h      n        mean        median        95% CI"
          "            vs taker  vs paper")
    any_above = False
    for k in KS:
        for thr in THRS:
            idx, sign = store[(k, thr)]
            for h in HORIZONS:
                val, kept = drift_values(close, idx, sign, 0, h)
                if len(val) < 10:
                    continue
                if val.mean() <= COST_TAKER_PCT:
                    continue
                any_above = True
                ev_days = epoch_seconds(pd.DatetimeIndex(days[kept]))
                lo, hi = day_cluster_ci(val, ev_days)
                print(f"    {k:>3d} {thr:>4.1f} {h:>4d} {len(val):>6d} "
                      f"{val.mean():>+11.4f} {np.median(val):>+12.4f}  "
                      f"[{lo:>+8.4f},{hi:>+8.4f}]  "
                      f"{val.mean()-COST_TAKER_PCT:>+9.4f} "
                      f"{val.mean()-COST_PAPER_PCT:>+9.4f}")
    if not any_above:
        print("    (none)")
    return results


# ---------------------------------------------------------------------------
# 3. Regime decomposition
# ---------------------------------------------------------------------------
def regime_surface(df: pd.DataFrame, store: dict, reg_of_day: pd.Series) -> None:
    hdr("3. REGIME DECOMPOSITION OF THE DRIFT SURFACE (d=0, pre-cost, mean %)")
    close = df["close"].to_numpy(float)
    days = pd.DatetimeIndex(df.index.floor("D"))
    for h in HORIZONS:
        print(f"\n  --- horizon h = {h}m --- (calm / mid / storm ; n in parens)")
        print("    k \\ thr " + "".join(f"{t:>26.1f}" for t in THRS))
        for k in KS:
            cells = []
            for thr in THRS:
                idx, sign = store[(k, thr)]
                val, kept = drift_values(close, idx, sign, 0, h)
                ev_reg = reg_of_day.reindex(days[kept]).to_numpy()
                parts = []
                for r in ("calm", "mid", "storm"):
                    v = val[ev_reg == r]
                    parts.append(f"{v.mean():+.3f}" if len(v) else "  n/a ")
                parts.append(f"({len(val)})")
                cells.append("/".join(parts[:3]) + parts[3])
            print(f"    {k:>6d}  " + "".join(f"{c:>26}" for c in cells))


def regime_detail(df: pd.DataFrame, store: dict, reg_of_day: pd.Series,
                  k: int, thr: float) -> None:
    hdr(f"3b. REGIME DETAIL FOR THE ADOPTED POINT (k={k}, thr={thr}%)")
    close = df["close"].to_numpy(float)
    days = pd.DatetimeIndex(df.index.floor("D"))
    idx, sign = store[(k, thr)]
    print("    regime     h      n        mean      median         95% CI")
    for r in ("all", "calm", "mid", "storm"):
        for h in HORIZONS:
            val, kept = drift_values(close, idx, sign, 0, h)
            ev_reg = reg_of_day.reindex(days[kept]).to_numpy()
            sel = np.ones(len(val), bool) if r == "all" else (ev_reg == r)
            v = val[sel]
            if len(v) == 0:
                continue
            dd = epoch_seconds(days[kept][sel])
            lo, hi = day_cluster_ci(v, dd)
            print(f"    {r:>6} {h:>5d} {len(v):>6d} {v.mean():>+11.4f} "
                  f"{np.median(v):>+11.4f}  [{lo:>+8.4f},{hi:>+8.4f}]")


# ---------------------------------------------------------------------------
# 4. Where does the adopted point sit on the surface?
# ---------------------------------------------------------------------------
def point_placement(df: pd.DataFrame, store: dict) -> None:
    hdr("4. PLACEMENT OF THE ADOPTED POINT (k=30, thr=0.8) ON THE SURFACE")
    close = df["close"].to_numpy(float)
    rows = []
    for k in KS:
        for thr in THRS:
            idx, sign = store[(k, thr)]
            for d in DELAYS:
                for h in HORIZONS:
                    val, _ = drift_values(close, idx, sign, d, h)
                    if len(val) >= 10:
                        rows.append((k, thr, d, h, len(val), val.mean()))
    arr = pd.DataFrame(rows, columns=["k", "thr", "d", "h", "n", "mean"])
    print(f"  populated cells (n>=10): {len(arr)} of "
          f"{len(KS)*len(THRS)*len(DELAYS)*len(HORIZONS)}")
    print(f"  surface mean of cell means : {arr['mean'].mean():+.4f}%")
    print(f"  fraction of cells > 0      : {(arr['mean']>0).mean():.1%}")
    print(f"  fraction > taker line      : {(arr['mean']>COST_TAKER_PCT).mean():.1%}")
    print(f"  fraction > paper line      : {(arr['mean']>COST_PAPER_PCT).mean():.1%}")

    ch = arr[(arr.k == CHAMPION_K) & (arr.thr == CHAMPION_THR)]
    print("\n  champion cells and their percentile within the whole surface:")
    print("      d     h      n        mean    pctile-of-surface")
    for _, r in ch.iterrows():
        pct = (arr["mean"] < r["mean"]).mean() * 100
        print(f"    {int(r.d):>3d} {int(r.h):>5d} {int(r.n):>6d} "
              f"{r['mean']:>+11.4f}   {pct:>6.1f}%")

    print("\n  top 12 cells by mean drift (whole surface, n>=10):")
    print("      k   thr    d     h      n        mean")
    for _, r in arr.sort_values("mean", ascending=False).head(12).iterrows():
        print(f"    {int(r.k):>3d} {r.thr:>5.1f} {int(r.d):>4d} {int(r.h):>5d} "
              f"{int(r.n):>6d} {r['mean']:>+11.4f}")

    print("\n  bottom 6 cells by mean drift:")
    for _, r in arr.sort_values("mean").head(6).iterrows():
        print(f"    {int(r.k):>3d} {r.thr:>5.1f} {int(r.d):>4d} {int(r.h):>5d} "
              f"{int(r.n):>6d} {r['mean']:>+11.4f}")

    # where does +0.19..+0.36%/trade sit?
    hdr("4b. THE ADOPTION-TIME NUMBERS (+0.19% / +0.36% per trade, n=15) "
        "AGAINST THE SURFACE")
    idx, sign = store[(CHAMPION_K, CHAMPION_THR)]
    for h in HORIZONS:
        val, _ = drift_values(close, idx, sign, 0, h)
        if len(val) < 5:
            continue
        se = val.std(ddof=1) / np.sqrt(15)
        print(f"    h={h:>3d}m  n={len(val):>4d}  mean={val.mean():+.4f}%  "
              f"sd={val.std(ddof=1):.4f}%  ->  a random 15-event draw has "
              f"sd {se:.4f}%; +0.19% is {(0.19-val.mean())/se:+.2f} sigma, "
              f"+0.36% is {(0.36-val.mean())/se:+.2f} sigma")
    rng = np.random.default_rng(SEED)
    for h in (30, 60, 240):
        val, _ = drift_values(close, idx, sign, 0, h)
        if len(val) < 15:
            continue
        draws = np.array([rng.choice(val, 15, replace=True).mean()
                          for _ in range(20000)])
        print(f"    h={h:>3d}m  P(mean of 15 random events >= +0.19%) = "
              f"{(draws>=0.19).mean():.3f} ; >= +0.36% = {(draws>=0.36).mean():.3f}")


# ---------------------------------------------------------------------------
# 5. Long-horizon proxy surface (210d, Binance self-leader)
# ---------------------------------------------------------------------------
def proxy_surface() -> None:
    hdr("5. 210d PROXY SURFACE (Binance as its own leader -- momentum "
        "continuation, NOT cross-exchange lag)")
    if not os.path.exists(PROXY_CSV):
        print("  proxy file missing; skipped")
        return
    df = load_proxy()
    print(f"  span {df.index[0]} .. {df.index[-1]}  bars={len(df)}  "
          f"days={df.index.floor('D').nunique()}")
    close = df["close"].to_numpy(float)
    lead = df["leader_close"].to_numpy(float)
    n_days = df.index.floor("D").nunique()
    print("\n  events/day (rows k, cols thr%)")
    print("    k \\ thr " + "".join(f"{t:>9.1f}" for t in THRS))
    store = {}
    for k in KS:
        m = momentum(lead, k)
        row = []
        for thr in THRS:
            idx, sign = rising_edges(m, thr)
            store[(k, thr)] = (idx, sign)
            row.append(len(idx) / n_days)
        print(f"    {k:>6d}  " + "".join(f"{v:>9.2f}" for v in row))

    for d in (0, 1):
        print(f"\n  mean drift %, delay d={d}m (rows k, cols h)")
        print("    k   thr      n " + "".join(f"{'h=%dm' % h:>12}" for h in HORIZONS))
        for k in KS:
            for thr in THRS:
                idx, sign = store[(k, thr)]
                cells, n_show = [], 0
                for h in HORIZONS:
                    val, _ = drift_values(close, idx, sign, d, h)
                    n_show = len(val)
                    cells.append(val.mean() if len(val) else np.nan)
                mark = "  <== champion" if (k == CHAMPION_K and thr == CHAMPION_THR) else ""
                print(f"    {k:>3d} {thr:>4.1f} {n_show:>6d} " +
                      "".join(f"{c:>+12.4f}" for c in cells) + mark)

    # regime split on the proxy too
    r = np.log(df["close"]).diff()
    day = df.index.floor("D")
    rv = (r.groupby(day).std() * 1e4).dropna()
    q1, q2 = rv.quantile([1 / 3, 2 / 3])
    lab = pd.Series(np.where(rv <= q1, "calm", np.where(rv <= q2, "mid", "storm")),
                    index=rv.index)
    days_idx = pd.DatetimeIndex(day)
    print("\n  proxy regime split, d=0 (calm/mid/storm), h=60m and h=240m")
    print("    k   thr        h=60m                       h=240m")
    for k in KS:
        for thr in THRS:
            idx, sign = store[(k, thr)]
            out = []
            for h in (60, 240):
                val, kept = drift_values(close, idx, sign, 0, h)
                ev = lab.reindex(days_idx[kept]).to_numpy()
                parts = []
                for rr in ("calm", "mid", "storm"):
                    v = val[ev == rr]
                    parts.append(f"{v.mean():+.3f}" if len(v) else " n/a ")
                out.append("/".join(parts))
            print(f"    {k:>3d} {thr:>4.1f}  {out[0]:>26} {out[1]:>26}")


# ---------------------------------------------------------------------------
# 6. Exit composition on the top cells
# ---------------------------------------------------------------------------
def simulate_champion_exit(df: pd.DataFrame, k: int, thr: float,
                           exit_pct: float, stop_pct: float,
                           max_hold: int = MAX_HOLD) -> pd.DataFrame:
    """Champion exit policy: signal fade | 0.5% protective stop | time cap.

    No position overlap: a new event is skipped while a position is open.
    """
    close = df["close"].to_numpy(float)
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    lead = df["leader_close"].to_numpy(float)
    m = momentum(lead, k)
    idx, sign = rising_edges(m, thr)
    band = exit_pct / 100.0
    stop = stop_pct / 100.0
    rows = []
    busy_until = -1
    for i, s in zip(idx, sign):
        if i <= busy_until:
            continue
        entry = close[i]
        stop_px = entry * (1 - stop * s)
        out_j, out_px, reason = None, None, None
        for j in range(i + 1, min(i + 1 + max_hold, len(close))):
            hit = (low[j] <= stop_px) if s > 0 else (high[j] >= stop_px)
            if hit:
                out_j, out_px, reason = j, stop_px, "stop"
                break
            if not np.isnan(m[j]) and abs(m[j]) <= band:
                out_j, out_px, reason = j, close[j], "signal"
                break
        if out_j is None:
            out_j = min(i + max_hold, len(close) - 1)
            out_px, reason = close[out_j], "time"
        gross = s * (out_px / entry - 1.0) * 100.0
        rows.append((i, out_j, out_j - i, s, reason, gross))
        busy_until = out_j
    return pd.DataFrame(rows, columns=["i", "j", "hold", "sign", "reason", "gross"])


def simulate_time_exit(df: pd.DataFrame, k: int, thr: float,
                       hold: int) -> pd.DataFrame:
    close = df["close"].to_numpy(float)
    lead = df["leader_close"].to_numpy(float)
    m = momentum(lead, k)
    idx, sign = rising_edges(m, thr)
    rows = []
    busy_until = -1
    for i, s in zip(idx, sign):
        if i <= busy_until:
            continue
        j = i + hold
        if j >= len(close):
            break
        gross = s * (close[j] / close[i] - 1.0) * 100.0
        rows.append((i, j, hold, s, "time", gross))
        busy_until = j
    return pd.DataFrame(rows, columns=["i", "j", "hold", "sign", "reason", "gross"])


def report_sim(df: pd.DataFrame, tr: pd.DataFrame, label: str) -> None:
    if len(tr) == 0:
        print(f"    {label:<34} n=0")
        return
    days = pd.DatetimeIndex(df.index.floor("D"))[tr["i"].to_numpy()]
    dd = epoch_seconds(days)
    for cost, cname in ((COST_TAKER_PCT, "taker"), (COST_PAPER_PCT, "paper")):
        net = tr["gross"].to_numpy() - cost
        lo, hi = day_cluster_ci(net, dd)
        print(f"    {label:<34} cost={cname:<5} n={len(tr):>4d} "
              f"net={net.mean():>+8.4f}% med={np.median(net):>+8.4f}% "
              f"win={np.mean(net>0):>5.1%} CI[{lo:>+7.4f},{hi:>+7.4f}]")
    br = tr.groupby("reason")["gross"].agg(["count", "mean", "sum"])
    br = br.reindex(["signal", "stop", "time"]).dropna(how="all")
    parts = [f"{r}: n={int(v['count'])} mean={v['mean']:+.4f}% sum={v['sum']:+.3f}%"
             for r, v in br.iterrows()]
    print(f"      exit mix -> " + " | ".join(parts))


def exit_composition(df: pd.DataFrame, cells: list[tuple[int, float]]) -> None:
    hdr("6. EXIT COMPOSITION ON THE TOP CELLS (pre/post cost, no overlap)")
    print("  A = champion exit (fade 0.05% | stop 0.5% | 240-bar cap)")
    print("  B = time-only exit (hold 30 / 60 / 240 bars)")
    for k, thr in cells:
        print(f"\n  --- cell k={k}, thr={thr}% ---")
        a = simulate_champion_exit(df, k, thr, CHAMPION_EXIT_PCT, CHAMPION_STOP_PCT)
        report_sim(df, a, "A champion exit")
        for hold in (30, 60, 240):
            b = simulate_time_exit(df, k, thr, hold)
            report_sim(df, b, f"B time-only hold={hold}m")
        # stop-free variant of A to isolate the stop's contribution
        c = simulate_champion_exit(df, k, thr, CHAMPION_EXIT_PCT, 100.0)
        report_sim(df, c, "A' fade-only (stop disabled)")


# ---------------------------------------------------------------------------
# 7. Fishing / tail / stability diagnostics
# ---------------------------------------------------------------------------
def fishing_diagnostic(df: pd.DataFrame, store: dict) -> None:
    hdr("7. FISHING DIAGNOSTIC -- does the positive region of the surface "
        "coincide with the low-n region?")
    close = df["close"].to_numpy(float)
    rows = []
    for k in KS:
        for thr in THRS:
            idx, sign = store[(k, thr)]
            for d in DELAYS:
                for h in HORIZONS:
                    val, _ = drift_values(close, idx, sign, d, h)
                    if len(val) >= 10:
                        rows.append((k, thr, d, h, len(val), val.mean()))
    a = pd.DataFrame(rows, columns=["k", "thr", "d", "h", "n", "mean"])
    ln = np.log10(a["n"].to_numpy(float))
    r = float(np.corrcoef(ln, a["mean"])[0, 1])
    slope = float(np.polyfit(ln, a["mean"], 1)[0])
    print(f"  cells n>=10: {len(a)}")
    print(f"  corr(log10 n, cell mean drift) = {r:+.3f}   "
          f"slope = {slope:+.4f} %/decade of n")
    print("\n  mean cell drift by event-count bucket:")
    print("    n bucket        cells    mean of cell means   frac>taker line")
    for lo, hi, lab in ((0, 20, "10-19"), (20, 50, "20-49"), (50, 100, "50-99"),
                        (100, 400, "100-399"), (400, 10 ** 9, ">=400")):
        s = a[(a.n >= lo) & (a.n < hi)]
        if len(s) == 0:
            continue
        print(f"    {lab:<14} {len(s):>6d} {s['mean'].mean():>+19.4f} "
              f"{(s['mean']>COST_TAKER_PCT).mean():>17.1%}")
    print("\n  same, restricted to the well-populated cells only (n>=100):")
    s = a[a.n >= 100]
    print(f"    cells={len(s)}  mean of cell means={s['mean'].mean():+.4f}%  "
          f"frac>0={(s['mean']>0).mean():.1%}  "
          f"frac>taker={(s['mean']>COST_TAKER_PCT).mean():.1%}")


def tail_concentration(df: pd.DataFrame, store: dict,
                       cells: list[tuple[int, float]], h: int = 60) -> None:
    hdr(f"8. RIGHT-TAIL CONCENTRATION AND DAY-JACKKNIFE (d=0, h={h}m)")
    close = df["close"].to_numpy(float)
    days = pd.DatetimeIndex(df.index.floor("D"))
    print("      k   thr      n      mean   trimmed5%    median  "
          "top1 share  top3 share   worst-day-drop  best-day-drop")
    for k, thr in cells:
        idx, sign = store[(k, thr)]
        val, kept = drift_values(close, idx, sign, 0, h)
        if len(val) < 5:
            continue
        srt = np.sort(val)
        lo_i = int(len(val) * 0.05)
        trimmed = srt[lo_i:len(val) - lo_i].mean() if len(val) > 4 else np.nan
        tot = val.sum()
        top1 = srt[-1] / tot if tot != 0 else np.nan
        top3 = srt[-3:].sum() / tot if tot != 0 else np.nan
        dd = days[kept]
        uniq = pd.unique(dd)
        means = np.array([val[dd != u].mean() for u in uniq])
        print(f"    {k:>3d} {thr:>5.1f} {len(val):>6d} {val.mean():>+9.4f} "
              f"{trimmed:>+11.4f} {np.median(val):>+9.4f} "
              f"{top1:>11.1%} {top3:>11.1%}   {means.max():>+13.4f} "
              f"{means.min():>+13.4f}")
    print("  (worst/best-day-drop = mean after removing the single UTC day that "
          "helps/hurts most)")


def split_half(df: pd.DataFrame, store: dict,
               cells: list[tuple[int, float]]) -> None:
    hdr("9. WITHIN-WINDOW STABILITY (exploration window split 60/40 by time)")
    close = df["close"].to_numpy(float)
    cut = int(len(df) * 0.6)
    print(f"  cut bar {cut} -> {df.index[cut]}")
    print("      k   thr    h    n_first  mean_first    n_last   mean_last  "
          "sign flip?")
    for k, thr in cells:
        idx, sign = store[(k, thr)]
        for h in (30, 60, 240):
            val, kept = drift_values(close, idx, sign, 0, h)
            m1 = val[kept < cut]
            m2 = val[kept >= cut]
            if len(m1) < 3 or len(m2) < 3:
                print(f"    {k:>3d} {thr:>5.1f} {h:>4d} "
                      f"{len(m1):>10d} {'-':>11} {len(m2):>9d} {'-':>11}  "
                      f"(insufficient)")
                continue
            flip = "YES" if np.sign(m1.mean()) != np.sign(m2.mean()) else "no"
            print(f"    {k:>3d} {thr:>5.1f} {h:>4d} {len(m1):>10d} "
                  f"{m1.mean():>+11.4f} {len(m2):>9d} {m2.mean():>+11.4f}  {flip}")


def proxy_exit(cells: list[tuple[int, float]]) -> None:
    hdr("10. CHAMPION-EXIT SIMULATION ON THE 210d PROXY "
        "(momentum continuation only)")
    if not os.path.exists(PROXY_CSV):
        print("  proxy file missing; skipped")
        return
    df = load_proxy()
    for k, thr in cells:
        print(f"\n  --- cell k={k}, thr={thr}% (210d proxy) ---")
        a = simulate_champion_exit(df, k, thr, CHAMPION_EXIT_PCT,
                                   CHAMPION_STOP_PCT)
        report_sim(df, a, "A champion exit")
        b = simulate_time_exit(df, k, thr, 60)
        report_sim(df, b, "B time-only hold=60m")


def survivor_screen(df: pd.DataFrame, store: dict, reg_of_day: pd.Series) -> None:
    """Definitive 'is anything left on the surface' test.

    A cell survives only if ALL hold:
      n >= 30, mean drift > taker round trip, day-cluster 95% CI excludes 0,
      and the SAME (k, thr, d, h) cell has the same sign on the 210d proxy.
    Applied to every populated cell of the 2000-cell surface (all + 3 regimes).
    """
    hdr("11. SURVIVOR SCREEN OVER THE WHOLE SURFACE")
    print("  filters (all must hold): n>=30 | mean > taker 0.0792% | "
          "day-cluster 95% CI excludes 0 | same sign on the 210d proxy")
    close = df["close"].to_numpy(float)
    days = pd.DatetimeIndex(df.index.floor("D"))

    proxy_mean = {}
    if os.path.exists(PROXY_CSV):
        pdf = load_proxy()
        pclose = pdf["close"].to_numpy(float)
        plead = pdf["leader_close"].to_numpy(float)
        for k in KS:
            m = momentum(plead, k)
            for thr in THRS:
                pidx, psign = rising_edges(m, thr)
                for d in DELAYS:
                    for h in HORIZONS:
                        v, _ = drift_values(pclose, pidx, psign, d, h)
                        proxy_mean[(k, thr, d, h)] = v.mean() if len(v) else np.nan

    total, populated, pass_n, pass_cost, pass_ci, pass_proxy = 0, 0, 0, 0, 0, 0
    survivors = []
    for k in KS:
        for thr in THRS:
            idx, sign = store[(k, thr)]
            for d in DELAYS:
                for h in HORIZONS:
                    val, kept = drift_values(close, idx, sign, d, h)
                    ev_reg = reg_of_day.reindex(days[kept]).to_numpy()
                    for reg in REGIMES:
                        total += 1
                        sel = (np.ones(len(val), bool) if reg == "all"
                               else (ev_reg == reg))
                        v = val[sel]
                        if len(v) == 0:
                            continue
                        populated += 1
                        if len(v) < 30:
                            continue
                        pass_n += 1
                        if v.mean() <= COST_TAKER_PCT:
                            continue
                        pass_cost += 1
                        lo, hi = day_cluster_ci(v, epoch_seconds(days[kept][sel]))
                        if not (lo > 0):
                            continue
                        pass_ci += 1
                        pm = proxy_mean.get((k, thr, d, h), np.nan)
                        same_sign = (not np.isnan(pm)) and (np.sign(pm) ==
                                                            np.sign(v.mean()))
                        if not same_sign:
                            continue
                        pass_proxy += 1
                        survivors.append((k, thr, d, h, reg, len(v), v.mean(),
                                          lo, hi, pm))
    print(f"\n  surface cells examined      : {total}")
    print(f"  populated (n>=1)            : {populated}")
    print(f"  after n>=30                 : {pass_n}")
    print(f"  after mean > taker line     : {pass_cost}")
    print(f"  after day-cluster CI > 0    : {pass_ci}")
    print(f"  after 210d proxy sign match : {pass_proxy}")
    if survivors:
        print("\n      k   thr    d     h  regime      n        mean"
              "          95% CI        proxy mean")
        for s in survivors:
            print(f"    {s[0]:>3d} {s[1]:>5.1f} {s[2]:>4d} {s[3]:>5d} "
                  f"{s[4]:>7} {s[5]:>6d} {s[6]:>+11.4f}  "
                  f"[{s[7]:>+8.4f},{s[8]:>+8.4f}] {s[9]:>+13.4f}")
    else:
        print("\n  SURVIVORS: none.")

    # Also show what survives if the proxy filter is dropped (the weaker screen)
    print("\n  weaker screen (drop the proxy-sign filter) -- cells passing "
          "n>=30 + cost + CI:")
    shown = 0
    for k in KS:
        for thr in THRS:
            idx, sign = store[(k, thr)]
            for d in DELAYS:
                for h in HORIZONS:
                    val, kept = drift_values(close, idx, sign, d, h)
                    ev_reg = reg_of_day.reindex(days[kept]).to_numpy()
                    for reg in REGIMES:
                        sel = (np.ones(len(val), bool) if reg == "all"
                               else (ev_reg == reg))
                        v = val[sel]
                        if len(v) < 30 or v.mean() <= COST_TAKER_PCT:
                            continue
                        lo, hi = day_cluster_ci(v, epoch_seconds(days[kept][sel]))
                        if lo > 0:
                            pm = proxy_mean.get((k, thr, d, h), np.nan)
                            print(f"    k={k} thr={thr} d={d} h={h} reg={reg} "
                                  f"n={len(v)} mean={v.mean():+.4f} "
                                  f"CI[{lo:+.4f},{hi:+.4f}] "
                                  f"proxy={pm:+.4f} "
                                  f"(vs paper line {v.mean()-COST_PAPER_PCT:+.4f})")
                            shown += 1
    if shown == 0:
        print("    (none)")


def tradeability(df: pd.DataFrame, reg_of_day: pd.Series,
                 cells: list[tuple[int, float]]) -> None:
    """Turn the survivor cells into non-overlapping, cost-charged trade series.

    The drift surface allows unlimited overlap; a bot cannot.  This converts the
    surviving regions into what the engine would actually book.
    """
    hdr("12. TRADEABILITY OF THE SURVIVOR REGION "
        "(non-overlapping, cost charged)")
    proxy = load_proxy() if os.path.exists(PROXY_CSV) else None
    if proxy is not None:
        pr = np.log(proxy["close"]).diff()
        pday = proxy.index.floor("D")
        prv = (pr.groupby(pday).std() * 1e4).dropna()
        pq1, pq2 = prv.quantile([1 / 3, 2 / 3])
        plab = pd.Series(np.where(prv <= pq1, "calm",
                                  np.where(prv <= pq2, "mid", "storm")),
                         index=prv.index)
    for k, thr in cells:
        for hold in (60, 240):
            print(f"\n  --- k={k} thr={thr}% time-only hold={hold}m, "
                  f"no overlap ---")
            for label, frame, lab in (("31d window", df, reg_of_day),
                                      ("210d proxy", proxy,
                                       plab if proxy is not None else None)):
                if frame is None:
                    continue
                tr = simulate_time_exit(frame, k, thr, hold)
                if len(tr) == 0:
                    continue
                fdays = pd.DatetimeIndex(frame.index.floor("D"))
                ev_day = fdays[tr["i"].to_numpy()]
                ev_reg = lab.reindex(ev_day).to_numpy()
                n_days = frame.index.floor("D").nunique()
                for reg in ("all", "storm"):
                    sel = (np.ones(len(tr), bool) if reg == "all"
                           else (ev_reg == reg))
                    g = tr["gross"].to_numpy()[sel]
                    if len(g) < 10:
                        continue
                    dd = epoch_seconds(ev_day[sel])
                    nd = len(np.unique(dd))
                    for cost, cname in ((COST_TAKER_PCT, "taker"),
                                        (COST_PAPER_PCT, "paper")):
                        net = g - cost
                        lo, hi = day_cluster_ci(net, dd)
                        print(f"    {label:<11} {reg:<6} cost={cname:<5} "
                              f"n={len(g):>5d} trades/day={len(g)/max(nd,1):>5.2f} "
                              f"net={net.mean():>+8.4f}% med={np.median(net):>+8.4f}% "
                              f"win={np.mean(net>0):>5.1%} "
                              f"CI[{lo:>+7.4f},{hi:>+7.4f}]")


# ---------------------------------------------------------------------------
def main() -> None:
    print("EXPLORATION ONLY -- leader-momentum surface autopsy")
    print(f"seed={SEED}  fresh cutoff={FRESH_CUTOFF} (fresh region never read)")
    print(f"surface breadth: {len(KS)}k x {len(THRS)}thr x {len(DELAYS)}d x "
          f"{len(HORIZONS)}h x {len(REGIMES)}regimes = "
          f"{len(KS)*len(THRS)*len(DELAYS)*len(HORIZONS)*len(REGIMES)} "
          f"measurement cells ({len(KS)*len(THRS)} signal cells)")

    df = build_frame()
    sanity(df)
    rv, reg_of_day = day_regimes(df)
    hdr("0. REGIME DEFINITION (daily realized vol of bitFlyer 1m returns, bps)")
    print(f"  tertile cuts: calm <= {rv.quantile(1/3):.1f} bps < mid <= "
          f"{rv.quantile(2/3):.1f} bps < storm")
    for d, v in rv.items():
        print(f"    {d.date()}  rv={v:>6.1f} bps  {reg_of_day[d]}")

    store = firing_table(df, reg_of_day)
    drift_surface(df, store, reg_of_day)
    regime_surface(df, store, reg_of_day)
    regime_detail(df, store, reg_of_day, CHAMPION_K, CHAMPION_THR)
    point_placement(df, store)
    proxy_surface()

    # top cells chosen by d=0 drift at h=60 among cells with n>=20
    close = df["close"].to_numpy(float)
    ranked = []
    for k in KS:
        for thr in THRS:
            idx, sign = store[(k, thr)]
            val, _ = drift_values(close, idx, sign, 0, 60)
            if len(val) >= 20:
                ranked.append((val.mean(), k, thr))
    ranked.sort(reverse=True)
    top = [(k, thr) for _, k, thr in ranked[:3]]
    if (CHAMPION_K, CHAMPION_THR) not in top:
        top.append((CHAMPION_K, CHAMPION_THR))
    exit_composition(df, top)

    fishing_diagnostic(df, store)
    diag_cells = list(dict.fromkeys(
        top + [(CHAMPION_K, CHAMPION_THR), (10, 0.8), (30, 0.4), (60, 0.8),
               (30, 1.2), (120, 0.8)]))
    tail_concentration(df, store, diag_cells, h=60)
    tail_concentration(df, store, diag_cells, h=30)
    split_half(df, store, diag_cells)
    proxy_exit([(CHAMPION_K, CHAMPION_THR), (10, 0.8), (120, 1.2)])
    survivor_screen(df, store, reg_of_day)
    tradeability(df, reg_of_day, [(30, 0.2), (120, 1.2), (10, 0.4)])
    print("\nDONE (exploration only; nothing adopted).")


if __name__ == "__main__":
    main()
