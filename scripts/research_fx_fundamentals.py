#!/usr/bin/env python3
"""FX Study S6 -- low-frequency fundamentals on USD/JPY (weekly horizon).

===============================================================================
WHY THIS STUDY EXISTS
===============================================================================
Studies S1..S5 in this repo attacked USD/JPY at the 1-minute / tick horizon and
produced zero adoptions.  The recurring verdict was not "no mechanism" but
"mechanism smaller than the cost floor": the round trip is 0.71bps
(KNOWLEDGE_FX.md sec.1) and a 1-minute move is ~0.6-0.8bps, so the tradable
residual after cost is a coin toss on a rounding error.

The weekly horizon inverts that arithmetic.  A typical weekly USD/JPY move is
~100bps.  0.71bps is then ~0.7% of the move -- cost is essentially free.  This
is the ONLY horizon in this market where a weak-but-real signal can survive.
It is also the horizon this project has never tested.  KNOWLEDGE_FX.md sec.4
lists "CFTC positioning / intervention proxies, low-frequency fundamentals" as
the last untouched attack line from phase B.

The flip side, stated up front so it is not discovered later: weekly decisions
buy ~52 observations per year.  Forty years of data is ~1,700 decisions.  That
is a small-n regime, so the bars below are on ANNUALIZED and RISK-ADJUSTED
quantities, not on bps/trade, and the t-statistic is the binding constraint.

===============================================================================
PRE-REGISTRATION -- fixed before a single number was computed
===============================================================================

-------------------------------------------------------------------------------
1. DATA (all snapshotted to backtest_data/ for offline reruns)
-------------------------------------------------------------------------------
(a) CFTC Commitments of Traders, LEGACY futures-only, via Socrata
    https://publicreporting.cftc.gov/resource/6dca-aqww.json
    contract  : cftc_contract_market_code = '097741'  (JAPANESE YEN)
    exchanges : 'JAPANESE YEN - INTERNATIONAL MONETARY MARKET' (1986-01-15 ..
                2000-08-22) and 'JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE'
                (2000-08-29 .. present).  These are the same contract under two
                exchange spellings; the ranges do not overlap.
    depth     : 1931 reports, 1986-01-15 .. 2026-08-18.  (The task brief
                expected ~2006-; the API in fact carries the full 40 years.)
    field     : NET NON-COMMERCIAL = noncomm_positions_long_all
                                   - noncomm_positions_short_all
                (contracts; each JPY future = 12,500,000 JPY.  Positive net =
                speculators are net LONG the yen = net SHORT USD/JPY.)
    cadence   : BI-WEEKLY until 1992-09-30, WEEKLY from 1992-10 onward
                (measured, not assumed: 162 gaps > 10 days, all but one before
                1992-10; the exception is the 11-day 2001-12-28 -> 2002-01-08
                holiday shift).  The trading families therefore run on the
                WEEKLY ERA ONLY (report_date >= 1992-10-01).  The full 1986-
                depth is used for the descriptive / IC section.

(b) FRED daily CSV (no key required, https://fred.stlouisfed.org/graph/fredgraph.csv)
    DEXJPUS  -- USD/JPY noon-ET buying rate, 1971-01-04 ..   (the price series)
    DGS2     -- US 2-year constant-maturity Treasury, 1976-06-01 ..
    VIXCLS   -- VIX close, 1990-01-02 ..   (descriptive only, NOT a family)

(c) Japan 2-year government bond yield -- MOF JGB constant-maturity daily
    https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv
    (history, 1974-09-24 ..) spliced with .../jgbcm.csv (current year).
    Japanese-era dates (S/H/R) are converted; '-' means not published.
    Fetched INDEPENDENTLY of study S5 by design (S5 coordinates constants, not
    data); the 2y differential used here is DGS2 - JGB_2Y.

(d) MOF foreign-exchange intervention, DAILY detail, 1991-04 ..
    https://www.mof.go.jp/english/policy/international_policy/reference/feio/
    foreign_exchange_intervention_operations.csv
    The daily file parses cleanly (Shift-JIS, quarter-total rows are separable
    because their Day column is empty), so the documented-episode fallback [T]
    in the brief is NOT needed.  Amounts are in 100 million JPY.
    PUBLICATION MODEL: MOF discloses a MONTHLY TOTAL on the last business day
    of month M covering (M-1)-27 .. M-26, and the daily breakdown only ~2
    months after quarter end.  F4 therefore keys off the MONTHLY DISCLOSURE
    date, never the intervention date.

-------------------------------------------------------------------------------
2. THE CLOCK -- publication lag, and why the brief's "Friday close" moves
-------------------------------------------------------------------------------
COT is stamped on a TUESDAY and RELEASED the following FRIDAY 15:30 ET.
DEXJPUS is a NOON-ET fixing.  Friday noon ET is 3.5 hours BEFORE the Friday
15:30 ET release, so "enter at Friday's close" as literally written in the
brief would be a look-ahead.  The pre-registered clock is therefore:

    pub_ts(report)      = FIRST FRIDAY STRICTLY AFTER report_date, 21:30 UTC
                          (15:30 ET under the EST offset = the LATER of the
                          two US offsets, i.e. the conservative one).  It is
                          "first Friday after", not "report_date + 3 days",
                          because 23 of the 1769 weekly-era reports are stamped
                          Mon/Wed/Fri by holiday shifts while the release still
                          happens on the Friday of that week -- a naive +3d
                          would have entered those 23 BEFORE the release.
    obs_ts(fx date D)   = D 16:00 UTC                       (noon ET, EDT
                          convention = the EARLIER, conservative)
    decision date d(r)  = first DEXJPUS observation with obs_ts > pub_ts(r)

which lands on MONDAY.  Position d(r) -> d(r+1); the weekly return is
log(P[d(r+1)] / P[d(r)]).  Total lag from the Tuesday the positioning was
measured to the entry print is 6 calendar days.

Residual risk: in a holiday week the CFTC release itself can slip to the
following Monday, which our Monday-noon entry would front-run by 3.5h on ~1%
of decisions.  A PARANOID variant is therefore also run and reported:
pub_ts + 3 days (the Monday after the release Friday), so entry lands Tuesday.
That variant cannot front-run any release under any holiday shift.  If primary
and paranoid disagree materially, the primary result is not trusted.

Yields (DGS2, JGB 2y) are same-evening publications; F3 uses the last yield
observation STRICTLY BEFORE the decision date.

-------------------------------------------------------------------------------
3. FAMILIES -- exactly these four.  No family is added after the fact.
-------------------------------------------------------------------------------
Sign convention throughout: pos = +1 is LONG USD/JPY (long dollar, short yen);
pos = -1 is SHORT USD/JPY (long yen).  net_nc > 0 = specs long yen.

F1  COT EXTREMES, CONTRARIAN.  4 configs, tested as ONE family.
    z_t = (net_t - mean(net over last 156 reports)) / sd(same window),
    window inclusive of t, so it uses only published data.
    Entry: z <= -thr  (crowded yen SHORTS) -> fade the crowd -> LONG yen  -> pos = -1
           z >= +thr  (crowded yen LONGS ) -> fade the crowd -> SHORT yen -> pos = +1
    Both directions belong to the same family (one symmetric rule).
    Axis A  threshold thr in {1.5, 2.0}
    Axis B  exit rule in {PULSE, PERSIST}
              PULSE   : flat whenever |z| < thr
              PERSIST : hold the fade until z crosses 0 (crowding unwound)
    -> 4 configs.

F2  COT FLOW MOMENTUM.  1 config.
    d4_t = net_t - net_{t-4}.  Trade WITH the flow: specs buying yen
    (d4 > 0) -> pos = -1; specs selling yen -> pos = +1.  Flat if d4 == 0.

F3  RATE-DIFFERENTIAL MOMENTUM.  1 config.
    diff_t = DGS2 - JGB_2Y (percentage points), sampled at the last
    observation strictly before the decision date.
    d13_t = diff_t - diff_{t-13 decisions}.  Trade WITH the widening:
    d13 > 0 (USD carry advantage widening) -> pos = +1.

F4  POST-INTERVENTION DRIFT.  MEASUREMENT ONLY -- no adoption possible, n is
    known to be ~20 by construction.  Event = a MOF monthly disclosure whose
    window contains JPY-BUYING intervention.  Event time = first decision date
    after the disclosure date.  Measure the 4 following weekly USD/JPY returns
    (cumulative) and report the mean with a bootstrap CI, so that
    "continuation of the yen rally" (negative USD/JPY drift) and "reversion"
    (positive) are distinguished by sign.  A calendar-matched placebo (all
    non-event decisions) is reported alongside.

-------------------------------------------------------------------------------
4. COSTS
-------------------------------------------------------------------------------
0.71bps ROUND TRIP (KNOWLEDGE_FX.md sec.1: GMO 0.5-sen spread 0.314bps +
0.002% API fee x2).  Charged on position CHANGE:
        cost_t = 0.355bps * |pos_t - pos_{t-1}|
so a full flip (+1 -> -1) costs 0.71bps and an exit to flat costs 0.355bps.
The final open position is unwound at the end of the sample at 0.355bps.
No swap/carry is modelled -- see CAVEATS.

-------------------------------------------------------------------------------
5. SPLIT AND SELECTION
-------------------------------------------------------------------------------
Chronological 60/40 over the weekly-era decision series.
  EXPLORATION = first 60% of decisions.  JUDGMENT = last 40%.
Selection rule, fixed in advance: within F1, take the config with the highest
EXPLORATION net Sharpe; tie-break on exploration net annualized return.
F2 and F3 have one config each, so there is nothing to select.
The judgment segment is run ONCE and reported as-is.  All four F1 configs are
printed on judgment for transparency, but only the exploration-selected one is
eligible for adoption; if the judgment winner differs from the exploration
winner that is recorded as a CONFIG SWITCHOVER = overfitting signal
(research-protocol sec.2).

-------------------------------------------------------------------------------
6. ADOPTION BARS -- all four must hold on the JUDGMENT segment
-------------------------------------------------------------------------------
  (i)   n >= 80 weekly decisions
  (ii)  net annualized return > 0 after costs
  (iii) weekly-clustered t >= 2.0 on the mean weekly net return
        (Newey-West HAC, 4 lags; a seeded stationary-bootstrap 95% CI is
         reported alongside and must also exclude zero)
  (iv)  net Sharpe >= 0.5 (annualized)

-------------------------------------------------------------------------------
7. ALSO REPORTED (diagnostics, never promoted to adoption)
-------------------------------------------------------------------------------
  * Spearman rank IC of each raw signal vs the NEXT week's USD/JPY return,
    full sample and per era.
  * Year-by-year net return for every family.
  * The 2022-2024 intervention era in isolation.
  * The paranoid-clock replication.
  * A look-ahead placebo: illegally shifting COT one report EARLIER must move
    the numbers (proof the pipeline is actually lag-bound).

===============================================================================
USAGE
===============================================================================
    python3 scripts/research_fx_fundamentals.py --fetch    # network, snapshots
    python3 scripts/research_fx_fundamentals.py            # offline, from snapshot
Deterministic: every bootstrap is seeded (SEED below); no network in the
default path.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# constants (pre-registered)
# --------------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[1]
SNAP = REPO / "backtest_data" / "fx_fundamentals_20260822"

SEED = 20260822
BOOT_REPS = 10000
BOOT_MEAN_BLOCK = 8.0          # stationary bootstrap mean block length (weeks)
HAC_LAGS = 4

ROUND_TRIP_BPS = 0.71          # KNOWLEDGE_FX.md sec.1
HALF_COST_BPS = ROUND_TRIP_BPS / 2.0

Z_WINDOW = 156                 # reports (~3 years) for the COT z-score
F1_THRESHOLDS = (1.5, 2.0)
F1_EXITS = ("PULSE", "PERSIST")
F2_LOOKBACK = 4                # reports
F3_LOOKBACK = 13               # decisions

WEEKLY_ERA_START = date(1992, 10, 1)
SPLIT_FRACTION = 0.60

PUB_EXTRA_DAYS_PRIMARY = 0     # release = first Friday strictly after the report date
PUB_EXTRA_DAYS_PARANOID = 3    # + the following Monday, immune to holiday slips

WEEKS_PER_YEAR = 52.0
F4_HORIZON = 4                 # weekly decisions after a disclosure

CFTC_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
CFTC_CODE = "097741"
CFTC_MARKETS = (
    "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
    "JAPANESE YEN - INTERNATIONAL MONETARY MARKET",
)
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FRED_SERIES = ("DEXJPUS", "DGS2", "VIXCLS")
JGB_HIST_URL = "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv"
JGB_CUR_URL = "https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv"
MOF_FEIO_URL = (
    "https://www.mof.go.jp/english/policy/international_policy/reference/feio/"
    "foreign_exchange_intervention_operations.csv"
)

FX_OBS_UTC_HOUR = 16           # DEXJPUS noon ET, EDT convention (conservative)
COT_PUB_UTC_HOUR = 21          # CFTC 15:30 ET, EST convention (conservative)
COT_PUB_UTC_MIN = 30


# ==========================================================================
# fetch layer
# ==========================================================================
def _http_get(url: str, params: dict | None = None, timeout: int = 180) -> bytes:
    import requests

    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def fetch_all() -> None:
    SNAP.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}

    # ---- CFTC COT -------------------------------------------------------
    where = "cftc_contract_market_code='%s' AND market_and_exchange_names in(%s)" % (
        CFTC_CODE,
        ",".join("'%s'" % m for m in CFTC_MARKETS),
    )
    params = {
        "$select": ",".join(
            [
                "report_date_as_yyyy_mm_dd",
                "market_and_exchange_names",
                "open_interest_all",
                "noncomm_positions_long_all",
                "noncomm_positions_short_all",
                "noncomm_postions_spread_all",
                "comm_positions_long_all",
                "comm_positions_short_all",
                "nonrept_positions_long_all",
                "nonrept_positions_short_all",
            ]
        ),
        "$where": where,
        "$order": "report_date_as_yyyy_mm_dd",
        "$limit": "50000",
    }
    raw = json.loads(_http_get(CFTC_URL, params).decode("utf-8"))
    rows = []
    for r in raw:
        rows.append(
            {
                "report_date": r["report_date_as_yyyy_mm_dd"][:10],
                "market": r["market_and_exchange_names"],
                "open_interest": r.get("open_interest_all"),
                "nc_long": r.get("noncomm_positions_long_all"),
                "nc_short": r.get("noncomm_positions_short_all"),
                "nc_spread": r.get("noncomm_postions_spread_all"),
                "comm_long": r.get("comm_positions_long_all"),
                "comm_short": r.get("comm_positions_short_all"),
                "nonrept_long": r.get("nonrept_positions_long_all"),
                "nonrept_short": r.get("nonrept_positions_short_all"),
            }
        )
    rows.sort(key=lambda x: x["report_date"])
    _write_csv(SNAP / "cot_jpy_legacy.csv", rows)
    manifest["cot_jpy_legacy.csv"] = {"source": CFTC_URL, "rows": len(rows)}

    # ---- FRED -----------------------------------------------------------
    for sid in FRED_SERIES:
        blob = _http_get(FRED_URL.format(sid=sid))
        path = SNAP / f"fred_{sid}.csv"
        path.write_bytes(blob)
        manifest[path.name] = {
            "source": FRED_URL.format(sid=sid),
            "rows": blob.count(b"\n"),
        }

    # ---- JGB ------------------------------------------------------------
    for name, url in (("jgb_hist.csv", JGB_HIST_URL), ("jgb_current.csv", JGB_CUR_URL)):
        blob = _http_get(url)
        (SNAP / name).write_bytes(blob)
        manifest[name] = {"source": url, "rows": blob.count(b"\n")}

    # ---- MOF intervention ----------------------------------------------
    blob = _http_get(MOF_FEIO_URL)
    (SNAP / "mof_feio_daily.csv").write_bytes(blob)
    manifest["mof_feio_daily.csv"] = {"source": MOF_FEIO_URL, "rows": blob.count(b"\n")}

    for name in list(manifest):
        p = SNAP / name
        manifest[name]["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        manifest[name]["bytes"] = p.stat().st_size
    (SNAP / "MANIFEST.json").write_text(
        json.dumps(
            {
                "fetched_utc": datetime.now(timezone.utc).isoformat(),
                "study": "FX S6 low-frequency fundamentals",
                "files": manifest,
            },
            indent=2,
        )
    )
    print(f"snapshot written to {SNAP}")
    for k, v in manifest.items():
        print(f"  {k:24s} {v['bytes']:>9,d} bytes  {v['rows']:>7,d} rows")


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise SystemExit(f"refusing to write empty {path}")
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# ==========================================================================
# load layer (offline)
# ==========================================================================
def _require_snapshot() -> None:
    if not (SNAP / "MANIFEST.json").exists():
        raise SystemExit(
            f"no snapshot at {SNAP}\n"
            "run once with --fetch (needs network), then rerun offline."
        )


def load_cot() -> pd.DataFrame:
    df = pd.read_csv(SNAP / "cot_jpy_legacy.csv", parse_dates=["report_date"])
    df["report_date"] = df["report_date"].dt.date
    for c in ("nc_long", "nc_short", "open_interest"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["nc_long", "nc_short"]).sort_values("report_date")
    if df["report_date"].duplicated().any():
        dups = df.loc[df["report_date"].duplicated(keep=False), "report_date"].tolist()
        raise SystemExit(f"duplicate COT report dates: {sorted(set(dups))[:5]}")
    df["net_nc"] = df["nc_long"] - df["nc_short"]
    return df.reset_index(drop=True)


def load_fred(sid: str) -> pd.Series:
    df = pd.read_csv(SNAP / f"fred_{sid}.csv")
    dcol, vcol = df.columns[0], df.columns[1]
    df[dcol] = pd.to_datetime(df[dcol]).dt.date
    df[vcol] = pd.to_numeric(df[vcol], errors="coerce")
    s = df.dropna(subset=[vcol]).set_index(dcol)[vcol]
    s.name = sid
    return s.sort_index()


_ERA_BASE = {"M": 1867, "T": 1911, "S": 1925, "H": 1988, "R": 2018}


def _jp_era_date(token: str) -> date | None:
    token = token.strip()
    if len(token) < 4 or token[0] not in _ERA_BASE:
        return None
    try:
        y, m, d = token[1:].split(".")
        return date(_ERA_BASE[token[0]] + int(y), int(m), int(d))
    except ValueError:
        return None


def load_jgb_2y() -> pd.Series:
    out: dict[date, float] = {}
    for name in ("jgb_hist.csv", "jgb_current.csv"):
        text = (SNAP / name).read_bytes().decode("shift_jis", errors="replace")
        header_col = None
        for row in csv.reader(io.StringIO(text)):
            if not row:
                continue
            if header_col is None:
                # header row: 基準日,1年,2年,...
                if len(row) > 3 and "2年" in row:
                    header_col = row.index("2年")
                continue
            dt = _jp_era_date(row[0])
            if dt is None or len(row) <= header_col:
                continue
            raw = row[header_col].strip()
            if raw in ("", "-", "*"):
                continue
            try:
                out[dt] = float(raw)
            except ValueError:
                continue
    s = pd.Series(out, name="JGB2Y").sort_index()
    if s.empty:
        raise SystemExit("JGB 2y parse produced no rows")
    return s


_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
}


def load_mof_interventions() -> pd.DataFrame:
    """Daily MOF intervention records.  Returns date, amount_oku_jpy, yen_side."""
    text = (SNAP / "mof_feio_daily.csv").read_bytes().decode("shift_jis", errors="replace")
    recs = []
    year = month = None
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 9:
            continue
        y_raw, m_raw, d_raw, amt_raw, en = (
            row[3].strip(),
            row[4].strip(),
            row[5].strip(),
            row[6].strip(),
            row[8].strip(),
        )
        if not d_raw.isdigit():
            continue                     # quarter-total / header / note rows
        if y_raw:
            if not y_raw.isdigit():
                continue
            year = int(y_raw)
        if m_raw:
            if m_raw[:3] not in _MONTHS:
                continue
            month = _MONTHS[m_raw[:3]]
        if year is None or month is None:
            continue
        try:
            amount = float(amt_raw.replace(",", ""))
        except ValueError:
            continue
        low = en.lower()
        if "japanese yen (bought)" in low:
            side = "JPY_BUY"
        elif "japanese yen (sold)" in low:
            side = "JPY_SELL"
        else:
            side = "OTHER"
        recs.append(
            {
                "date": date(year, month, int(d_raw)),
                "amount_oku_jpy": amount,
                "yen_side": side,
                "desc": en,
            }
        )
    df = pd.DataFrame(recs).sort_values("date").reset_index(drop=True)
    if df.empty:
        raise SystemExit("MOF intervention parse produced no rows")
    return df


# ==========================================================================
# clock: publication lag -> decision calendar
# ==========================================================================
def _fx_obs_ts(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, FX_OBS_UTC_HOUR, 0, tzinfo=timezone.utc)


def _cot_pub_ts(report_date: date, extra_days: int) -> datetime:
    """CFTC release: the first FRIDAY strictly after the report date, 15:30 ET."""
    p = report_date + timedelta(days=1)
    while p.weekday() != 4:                      # 4 = Friday
        p += timedelta(days=1)
    p += timedelta(days=extra_days)
    return datetime(p.year, p.month, p.day, COT_PUB_UTC_HOUR, COT_PUB_UTC_MIN, tzinfo=timezone.utc)


@dataclass
class Decisions:
    """One row per COT report that has a tradable decision date."""

    frame: pd.DataFrame       # report_date, net_nc, decision_date, px, next_date, ret
    lag_days: int


def build_decisions(cot: pd.DataFrame, fx: pd.Series, lag_days: int) -> Decisions:
    fx_dates = np.array(fx.index, dtype=object)
    fx_ts = np.array([_fx_obs_ts(d) for d in fx_dates], dtype=object)

    rows = []
    for _, r in cot.iterrows():
        rd: date = r["report_date"]
        pub = _cot_pub_ts(rd, lag_days)
        j = int(np.searchsorted(fx_ts, pub, side="right"))
        if j >= len(fx_dates):
            continue
        rows.append({"report_date": rd, "net_nc": float(r["net_nc"]), "decision_date": fx_dates[j]})
    df = pd.DataFrame(rows)

    # Collapse: if two consecutive reports map to the same decision date the
    # later report wins (it strictly dominates in information).
    df = df.drop_duplicates(subset="decision_date", keep="last").reset_index(drop=True)

    df["px"] = [float(fx.loc[d]) for d in df["decision_date"]]
    df["next_date"] = df["decision_date"].shift(-1)
    df["next_px"] = df["px"].shift(-1)
    df["ret"] = np.log(df["next_px"] / df["px"])            # log return, USD/JPY
    df["hold_days"] = [
        (b - a).days if isinstance(b, date) else np.nan
        for a, b in zip(df["decision_date"], df["next_date"])
    ]
    return Decisions(frame=df, lag_days=lag_days)


# ==========================================================================
# signals
# ==========================================================================
def add_signals(dec: pd.DataFrame, dgs2: pd.Series, jgb: pd.Series) -> pd.DataFrame:
    df = dec.copy()
    net = df["net_nc"]

    roll = net.rolling(Z_WINDOW, min_periods=Z_WINDOW)
    mu, sd = roll.mean(), roll.std(ddof=1)
    df["cot_z"] = (net - mu) / sd

    df["cot_d4"] = net - net.shift(F2_LOOKBACK)

    # rate differential sampled at the last yield obs STRICTLY BEFORE the
    # decision date (both legs), then differenced over 13 decisions.
    us = _asof_strictly_before(dgs2, df["decision_date"])
    jp = _asof_strictly_before(jgb, df["decision_date"])
    df["us2y"], df["jp2y"] = us, jp
    df["diff2y"] = us - jp
    df["diff_d13"] = df["diff2y"] - df["diff2y"].shift(F3_LOOKBACK)
    return df


def _asof_strictly_before(series: pd.Series, dates: pd.Series) -> np.ndarray:
    idx = np.array(series.index, dtype=object)
    vals = series.to_numpy(dtype=float)
    out = np.full(len(dates), np.nan)
    for i, d in enumerate(dates):
        j = int(np.searchsorted(idx, d, side="left")) - 1   # strictly before
        if j >= 0:
            out[i] = vals[j]
    return out


def positions_f1(z: np.ndarray, thr: float, exit_rule: str) -> np.ndarray:
    pos = np.zeros(len(z))
    state = 0
    for i, zi in enumerate(z):
        if np.isnan(zi):
            state = 0
            pos[i] = 0
            continue
        if exit_rule == "PULSE":
            state = -1 if zi <= -thr else (1 if zi >= thr else 0)
        else:  # PERSIST
            if state == 0:
                state = -1 if zi <= -thr else (1 if zi >= thr else 0)
            elif state == -1 and zi >= 0.0:
                state = 1 if zi >= thr else 0
            elif state == 1 and zi <= 0.0:
                state = -1 if zi <= -thr else 0
        pos[i] = state
    return pos


def positions_f2(d4: np.ndarray) -> np.ndarray:
    return np.where(np.isnan(d4), 0.0, -np.sign(d4))


def positions_f3(d13: np.ndarray) -> np.ndarray:
    return np.where(np.isnan(d13), 0.0, np.sign(d13))


# ==========================================================================
# P&L and statistics
# ==========================================================================
def pnl(pos: np.ndarray, ret: np.ndarray) -> np.ndarray:
    """Net log return per weekly decision, in bps, cost charged on turnover."""
    prev = np.concatenate([[0.0], pos[:-1]])
    cost = HALF_COST_BPS * np.abs(pos - prev)
    gross = pos * ret * 1e4
    out = gross - cost
    # unwind whatever is open on the final decision
    if len(out) and pos[-1] != 0.0:
        out[-1] -= HALF_COST_BPS * abs(pos[-1])
    return out


def hac_t(x: np.ndarray, lags: int = HAC_LAGS) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 8:
        return float("nan"), float("nan")
    m = x.mean()
    e = x - m
    s = float(e @ e) / n
    for j in range(1, min(lags, n - 1) + 1):
        g = float(e[j:] @ e[:-j]) / n
        s += 2.0 * (1.0 - j / (lags + 1.0)) * g
    if s <= 0:
        return m, float("nan")
    return m, m / np.sqrt(s / n)


def stationary_bootstrap_ci(
    x: np.ndarray, reps: int = BOOT_REPS, mean_block: float = BOOT_MEAN_BLOCK, seed: int = SEED
) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 10:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    p = 1.0 / mean_block
    starts = rng.integers(0, n, size=(reps, n))
    newblock = rng.random((reps, n)) < p
    idx = np.empty((reps, n), dtype=np.int64)
    idx[:, 0] = starts[:, 0]
    for t in range(1, n):
        cont = (idx[:, t - 1] + 1) % n
        idx[:, t] = np.where(newblock[:, t], starts[:, t], cont)
    means = x[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def boot_ci_iid(x: np.ndarray, reps: int = BOOT_REPS, seed: int = SEED) -> tuple[float, float]:
    """iid percentile bootstrap -- for the F4 event sample, whose episodes are
    months to years apart so there is no block structure to preserve."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 4:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, n, size=(reps, n))].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def simple_t(x: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 3:
        return (float(x.mean()) if n else float("nan")), float("nan")
    sd = float(np.std(x, ddof=1))
    m = float(x.mean())
    return m, (m / (sd / np.sqrt(n)) if sd > 0 else float("nan"))


@dataclass
class Stats:
    n: int
    mean_bps: float
    t: float
    ci_lo: float
    ci_hi: float
    ann_pct: float
    sharpe: float
    turnover: float
    exposure: float
    hit: float
    n_live: int


def summarize(pos: np.ndarray, ret: np.ndarray, seed_off: int = 0) -> Stats:
    net = pnl(pos, ret)
    n = len(net)
    if n == 0:
        return Stats(0, *([float("nan")] * 8), 0)
    mean, t = hac_t(net)
    lo, hi = stationary_bootstrap_ci(net, seed=SEED + seed_off)
    sd = float(np.std(net, ddof=1)) if n > 1 else float("nan")
    ann = mean * 1e-4 * WEEKS_PER_YEAR * 100.0
    sharpe = (mean / sd) * np.sqrt(WEEKS_PER_YEAR) if sd and sd > 0 else float("nan")
    prev = np.concatenate([[0.0], pos[:-1]])
    live = net[pos != 0.0]
    return Stats(
        n=n,
        mean_bps=mean,
        t=t,
        ci_lo=lo,
        ci_hi=hi,
        ann_pct=ann,
        sharpe=sharpe,
        turnover=float(np.mean(np.abs(pos - prev))),
        exposure=float(np.mean(pos != 0.0)),
        hit=float(np.mean(live > 0)) if len(live) else float("nan"),
        n_live=int(len(live)),
    )


def spearman(a: np.ndarray, b: np.ndarray) -> tuple[float, float, int]:
    m = ~(np.isnan(a) | np.isnan(b))
    a, b = a[m], b[m]
    n = len(a)
    if n < 10:
        return float("nan"), float("nan"), n
    ra = np.array(pd.Series(a).rank().to_numpy(), dtype=float, copy=True)
    rb = np.array(pd.Series(b).rank().to_numpy(), dtype=float, copy=True)
    ra -= ra.mean()
    rb -= rb.mean()
    denom = np.sqrt((ra @ ra) * (rb @ rb))
    if denom == 0:
        return float("nan"), float("nan"), n
    r = float((ra @ rb) / denom)
    tstat = r * np.sqrt(max(n - 2, 1) / max(1e-12, 1 - r * r))
    return r, tstat, n


# ==========================================================================
# reporting helpers
# ==========================================================================
def hdr(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def sub(title: str) -> None:
    print()
    print("-" * 78)
    print(title)
    print("-" * 78)


STAT_HEAD = (
    f"{'config':<26s}{'n':>6s}{'net bps/wk':>12s}{'t(HAC)':>9s}"
    f"{'ann%':>8s}{'Sharpe':>8s}{'expo':>7s}{'turn':>7s}{'hit%':>7s}{'n_live':>8s}"
)


def stat_line(name: str, s: Stats) -> str:
    return (
        f"{name:<26s}{s.n:>6d}{s.mean_bps:>12.2f}{s.t:>9.2f}"
        f"{s.ann_pct:>8.2f}{s.sharpe:>8.2f}{s.exposure:>7.2f}"
        f"{s.turnover:>7.2f}{100 * s.hit:>7.1f}{s.n_live:>8d}"
    )


# ==========================================================================
# main
# ==========================================================================
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="download + snapshot, then exit")
    args = ap.parse_args()
    if args.fetch:
        fetch_all()
        return 0

    _require_snapshot()
    np.set_printoptions(suppress=True)

    manifest = json.loads((SNAP / "MANIFEST.json").read_text())
    cot_all = load_cot()
    fx = load_fred("DEXJPUS")
    dgs2 = load_fred("DGS2")
    vix = load_fred("VIXCLS")
    jgb = load_jgb_2y()
    mof = load_mof_interventions()

    hdr("FX STUDY S6 -- LOW-FREQUENCY FUNDAMENTALS ON USD/JPY (WEEKLY)")
    print(f"snapshot        : {SNAP}")
    print(f"snapshot fetched: {manifest['fetched_utc']}")
    print(f"cost model      : {ROUND_TRIP_BPS} bps round trip "
          f"({HALF_COST_BPS} per unit of |position change|)")
    print(f"seed            : {SEED}   bootstrap reps: {BOOT_REPS}   HAC lags: {HAC_LAGS}")

    sub("DATA INVENTORY")
    print(f"COT JPY (legacy futures-only): {len(cot_all):5d} reports  "
          f"{cot_all['report_date'].iloc[0]} .. {cot_all['report_date'].iloc[-1]}")
    print(f"DEXJPUS                      : {len(fx):5d} obs      {fx.index[0]} .. {fx.index[-1]}")
    print(f"DGS2 (US 2y)                 : {len(dgs2):5d} obs      {dgs2.index[0]} .. {dgs2.index[-1]}")
    print(f"JGB 2y (MOF)                 : {len(jgb):5d} obs      {jgb.index[0]} .. {jgb.index[-1]}")
    print(f"VIXCLS (descriptive)         : {len(vix):5d} obs      {vix.index[0]} .. {vix.index[-1]}")
    print(f"MOF intervention (daily)     : {len(mof):5d} records  "
          f"{mof['date'].iloc[0]} .. {mof['date'].iloc[-1]}")
    byside = mof.groupby("yen_side")["amount_oku_jpy"].agg(["count", "sum"])
    for side, row in byside.iterrows():
        print(f"    {side:<9s} n={int(row['count']):4d}  total={row['sum']:>12,.0f} oku JPY")

    # ---- cadence check, pre-registered weekly-era boundary ---------------
    d = cot_all["report_date"].to_numpy()
    gaps = np.array([(b - a).days for a, b in zip(d[:-1], d[1:])])
    big = [(d[i], d[i + 1], int(g)) for i, g in enumerate(gaps) if g > 10]
    print(f"\nCOT cadence: gaps>10d = {len(big)}; last one "
          f"{big[-1][0]} -> {big[-1][1]} ({big[-1][2]}d). "
          f"weekly-era boundary fixed at {WEEKLY_ERA_START}")
    cot = cot_all[cot_all["report_date"] >= WEEKLY_ERA_START].reset_index(drop=True)
    print(f"weekly-era COT: {len(cot)} reports "
          f"{cot['report_date'].iloc[0]} .. {cot['report_date'].iloc[-1]}")

    # ==================================================================
    # SANITY BLOCK  (run before any result is read)
    # ==================================================================
    hdr("SANITY -- publication lag, look-ahead, determinism")

    dec_p = build_decisions(cot, fx, PUB_EXTRA_DAYS_PRIMARY)
    dec_x = build_decisions(cot, fx, PUB_EXTRA_DAYS_PARANOID)
    dfp = add_signals(dec_p.frame, dgs2, jgb)
    dfx = add_signals(dec_x.frame, dgs2, jgb)

    # S1 every entry strictly after the release timestamp
    bad = 0
    for _, r in dfp.iterrows():
        if _fx_obs_ts(r["decision_date"]) <= _cot_pub_ts(r["report_date"], PUB_EXTRA_DAYS_PRIMARY):
            bad += 1
    assert bad == 0, f"{bad} decisions precede their COT release"
    lagd = np.array([(r["decision_date"] - r["report_date"]).days for _, r in dfp.iterrows()])
    wd = pd.Series([r["decision_date"].weekday() for _, r in dfp.iterrows()]).value_counts()
    print(f"S1 entry-vs-release  : 0 violations of obs_ts > pub_ts over {len(dfp)} decisions")
    print(f"   lag Tue-report -> entry print: min {lagd.min()}d  median {np.median(lagd):.0f}d  "
          f"max {lagd.max()}d")
    print(f"   entry weekday histogram (0=Mon): "
          f"{ {int(k): int(v) for k, v in sorted(wd.items())} }")

    # S2 the z-score window never reaches forward
    zi = dfp["cot_z"].to_numpy()
    k = int(np.argmax(~np.isnan(zi)))
    net_s = dfp["net_nc"].to_numpy()
    manual = (net_s[k] - net_s[k - Z_WINDOW + 1 : k + 1].mean()) / net_s[
        k - Z_WINDOW + 1 : k + 1
    ].std(ddof=1)
    print(f"S2 z-window          : first non-nan z at i={k} "
          f"(needs {Z_WINDOW}); recomputed from the trailing {Z_WINDOW} reports "
          f"= {manual:+.6f} vs pipeline {zi[k]:+.6f}")
    assert abs(manual - zi[k]) < 1e-9

    # S3 yields strictly precede the decision date
    viol = 0
    for _, r in dfp.iterrows():
        if np.isnan(r["us2y"]):
            continue
        j = int(np.searchsorted(np.array(dgs2.index, dtype=object), r["decision_date"], "left")) - 1
        if j >= 0 and dgs2.index[j] >= r["decision_date"]:
            viol += 1
    print(f"S3 yield as-of       : {viol} violations of yield_date < decision_date")
    assert viol == 0

    # S4 look-ahead placebo -- illegally use next week's COT
    z_legal = dfp["cot_z"].to_numpy()
    z_cheat = np.concatenate([z_legal[1:], [np.nan]])
    ret_all = dfp["ret"].to_numpy()
    ok = ~np.isnan(ret_all)
    s_legal = summarize(positions_f1(z_legal, 2.0, "PERSIST")[ok], ret_all[ok])
    s_cheat = summarize(positions_f1(z_cheat, 2.0, "PERSIST")[ok], ret_all[ok])
    print(f"S4 look-ahead placebo: legal z  ann {s_legal.ann_pct:+.2f}%  t {s_legal.t:+.2f}")
    print(f"                       cheat z  ann {s_cheat.ann_pct:+.2f}%  t {s_cheat.t:+.2f}")
    print("   (the two MUST differ; identical numbers would mean the lag is inert)")
    assert abs(s_legal.ann_pct - s_cheat.ann_pct) > 1e-9

    # S5 determinism of the bootstrap
    a = stationary_bootstrap_ci(ret_all[ok] * 1e4)
    b = stationary_bootstrap_ci(ret_all[ok] * 1e4)
    print(f"S5 bootstrap rerun   : {a[0]:+.4f}/{a[1]:+.4f} == {b[0]:+.4f}/{b[1]:+.4f}  "
          f"{'OK' if a == b else 'NON-DETERMINISTIC'}")
    assert a == b

    # S6 return sanity
    r_bps = ret_all[ok] * 1e4
    print(f"S6 weekly returns    : n={len(r_bps)}  mean {r_bps.mean():+.1f}bps  "
          f"sd {r_bps.std(ddof=1):.1f}bps  |median| {np.median(np.abs(r_bps)):.1f}bps")
    print(f"   cost {ROUND_TRIP_BPS}bps is {100 * ROUND_TRIP_BPS / np.median(np.abs(r_bps)):.2f}% "
          f"of a median weekly move")
    hold = dfp["hold_days"].dropna().to_numpy()
    print(f"S7 holding period    : median {np.median(hold):.0f}d  "
          f"n(>10d)={int((hold > 10).sum())}  max {hold.max():.0f}d")
    print("S8 time types        : every timestamp here is a python date/datetime, "
          "never a")
    print("                       pandas datetime64 -- the ns/us/s unit trap in "
          "research-")
    print("                       protocol sec.6 cannot arise in this pipeline.")

    # ==================================================================
    # tradable universe + split
    # ==================================================================
    work = dfp[~dfp["ret"].isna()].reset_index(drop=True)
    n = len(work)
    cut = int(round(SPLIT_FRACTION * n))
    expl = slice(0, cut)
    judg = slice(cut, n)
    hdr("SPLIT (chronological 60/40, fixed before any result was read)")
    print(f"all tradable decisions : n={n}  "
          f"{work['decision_date'].iloc[0]} .. {work['decision_date'].iloc[-1]}")
    print(f"EXPLORATION            : n={cut}  "
          f"{work['decision_date'].iloc[0]} .. {work['decision_date'].iloc[cut - 1]}")
    print(f"JUDGMENT               : n={n - cut}  "
          f"{work['decision_date'].iloc[cut]} .. {work['decision_date'].iloc[-1]}")

    ret = work["ret"].to_numpy()
    z = work["cot_z"].to_numpy()
    d4 = work["cot_d4"].to_numpy()
    d13 = work["diff_d13"].to_numpy()

    configs: dict[str, np.ndarray] = {}
    for thr in F1_THRESHOLDS:
        for ex in F1_EXITS:
            configs[f"F1 z{thr} {ex}"] = positions_f1(z, thr, ex)
    configs["F2 COT flow d4"] = positions_f2(d4)
    configs["F3 rate-diff d13"] = positions_f3(d13)
    bh = np.ones(n)     # reference only, never a candidate
    configs["(ref) long USD/JPY"] = bh

    # ==================================================================
    # EXPLORATION
    # ==================================================================
    hdr("EXPLORATION SEGMENT -- selection happens here and only here")
    print(STAT_HEAD)
    expl_stats = {}
    for i, (name, pos) in enumerate(configs.items()):
        s = summarize(pos[expl], ret[expl], seed_off=i)
        expl_stats[name] = s
        print(stat_line(name, s))

    f1_names = [k for k in configs if k.startswith("F1")]
    winner = max(
        f1_names, key=lambda k: (
            expl_stats[k].sharpe if not np.isnan(expl_stats[k].sharpe) else -9e9,
            expl_stats[k].ann_pct,
        )
    )
    print(f"\nF1 selection rule (exploration Sharpe, tie-break ann%): -> {winner}")
    print("F2 and F3 are single-config families; nothing is selected.")

    # ==================================================================
    # JUDGMENT -- run once
    # ==================================================================
    hdr("JUDGMENT SEGMENT -- run once, reported as-is")
    print(STAT_HEAD)
    judg_stats = {}
    for i, (name, pos) in enumerate(configs.items()):
        s = summarize(pos[judg], ret[judg], seed_off=100 + i)
        judg_stats[name] = s
        mark = "  <- selected" if name == winner else ""
        print(stat_line(name, s) + mark)

    j_winner = max(
        f1_names, key=lambda k: (
            judg_stats[k].sharpe if not np.isnan(judg_stats[k].sharpe) else -9e9,
            judg_stats[k].ann_pct,
        )
    )
    if j_winner != winner:
        print(f"\n*** CONFIG SWITCHOVER: exploration winner {winner} != judgment winner "
              f"{j_winner} -> overfitting signal (research-protocol sec.2)")
    else:
        print(f"\nno config switchover: {winner} wins in both segments")

    sub("BOOTSTRAP 95% CI ON MEAN WEEKLY NET (bps), JUDGMENT")
    for name in list(f1_names) + ["F2 COT flow d4", "F3 rate-diff d13", "(ref) long USD/JPY"]:
        s = judg_stats[name]
        excl = "excludes 0" if (s.ci_lo > 0 or s.ci_hi < 0) else "includes 0"
        print(f"  {name:<26s} mean {s.mean_bps:+7.2f}  CI [{s.ci_lo:+7.2f}, {s.ci_hi:+7.2f}]  {excl}")

    # ---- verdict table --------------------------------------------------
    sub("ADOPTION BARS (judgment segment) -- n>=80, ann>0, t>=2.0, Sharpe>=0.5")
    print("n_live = weeks actually holding a position; the bar is on n (decisions),")
    print("but n_live is what the t-statistic really has to work with.")
    print(f"{'family/config':<26s}{'n':>6s}{'n_live':>8s}{'n>=80':>7s}{'ann>0':>7s}"
          f"{'t>=2':>7s}{'Sh>=.5':>8s}{'VERDICT':>10s}")
    verdicts = {}
    for name in [winner, "F2 COT flow d4", "F3 rate-diff d13"]:
        s = judg_stats[name]
        c1, c2 = s.n >= 80, s.ann_pct > 0
        c3 = (not np.isnan(s.t)) and s.t >= 2.0
        c4 = (not np.isnan(s.sharpe)) and s.sharpe >= 0.5
        allok = c1 and c2 and c3 and c4
        verdicts[name] = allok
        print(f"{name:<26s}{s.n:>6d}{s.n_live:>8d}{str(c1):>7s}{str(c2):>7s}"
              f"{str(c3):>7s}{str(c4):>8s}{'ADOPT' if allok else 'REJECT':>10s}")

    # ==================================================================
    # PARANOID CLOCK
    # ==================================================================
    # ==================================================================
    # ABLATION 1 -- is the cost floor the binding constraint at this horizon?
    # ==================================================================
    hdr("ABLATION A -- cost decomposition on the JUDGMENT segment")
    print("The whole premise of S6 is that 0.71bps stops mattering at weekly range.")
    print("This table settles whether cost or signal is what kills each family.")
    print(f"{'config':<26s}{'gross ann%':>12s}{'cost ann%':>11s}{'net ann%':>10s}"
          f"{'cost share of |gross|':>24s}")
    for name, pos in configs.items():
        p_, r_ = pos[judg], ret[judg]
        prev = np.concatenate([[0.0], p_[:-1]])
        gross = float(np.mean(p_ * r_ * 1e4))
        cost = float(np.mean(HALF_COST_BPS * np.abs(p_ - prev)))
        ga = gross * 1e-4 * WEEKS_PER_YEAR * 100
        ca = cost * 1e-4 * WEEKS_PER_YEAR * 100
        share = 100 * cost / abs(gross) if gross else float("nan")
        print(f"{name:<26s}{ga:>12.2f}{-ca:>11.2f}{ga - ca:>10.2f}{share:>23.1f}%")

    # ==================================================================
    # ABLATION 2 -- does the timing beat simply being long the dollar?
    # ==================================================================
    hdr("ABLATION B -- paired difference vs the passive long-USD/JPY benchmark")
    print("A weekly USD/JPY rule that is in the market ~100% of the time must be")
    print("compared against holding the dollar, not against zero (research-protocol")
    print("sec.4: pair comparisons, not standalone means).")
    bench = pnl(configs["(ref) long USD/JPY"][judg], ret[judg])
    print(f"{'config':<26s}{'diff bps/wk':>13s}{'t(HAC)':>9s}{'CI95':>24s}")
    for name in list(f1_names) + ["F2 COT flow d4", "F3 rate-diff d13"]:
        d_ = pnl(configs[name][judg], ret[judg]) - bench
        m_, t_ = hac_t(d_)
        lo_, hi_ = stationary_bootstrap_ci(d_, seed=SEED + 400)
        print(f"{name:<26s}{m_:>13.2f}{t_:>9.2f}   [{lo_:+7.2f}, {hi_:+7.2f}]")

    hdr("PARANOID CLOCK REPLICATION (entry one extra business day later)")
    workx = dfx[~dfx["ret"].isna()].reset_index(drop=True)
    nx = len(workx)
    cutx = int(round(SPLIT_FRACTION * nx))
    retx = workx["ret"].to_numpy()
    cfgx = {}
    for thr in F1_THRESHOLDS:
        for ex in F1_EXITS:
            cfgx[f"F1 z{thr} {ex}"] = positions_f1(workx["cot_z"].to_numpy(), thr, ex)
    cfgx["F2 COT flow d4"] = positions_f2(workx["cot_d4"].to_numpy())
    cfgx["F3 rate-diff d13"] = positions_f3(workx["diff_d13"].to_numpy())
    lagx = np.array([(r["decision_date"] - r["report_date"]).days for _, r in workx.iterrows()])
    print(f"entry lag: median {np.median(lagx):.0f}d (primary {np.median(lagd):.0f}d);  "
          f"judgment n={nx - cutx}")
    print(STAT_HEAD)
    for i, (name, pos) in enumerate(cfgx.items()):
        print(stat_line(name, summarize(pos[cutx:nx], retx[cutx:nx], seed_off=200 + i)))

    # ==================================================================
    # YEARLY + INTERVENTION-ERA BREAKDOWN
    # ==================================================================
    hdr("YEAR-BY-YEAR NET RETURN (%, full weekly-era sample; SEG marks E/J)")
    yrs = np.array([d.year for d in work["decision_date"]])
    show = [winner, "F2 COT flow d4", "F3 rate-diff d13", "(ref) long USD/JPY"]
    print(f"{'year':<6s}{'seg':>4s}{'n':>5s}" + "".join(f"{s:>20s}" for s in show))
    for y in sorted(set(yrs)):
        m = yrs == y
        seg = "E" if np.mean(np.where(m)[0] < cut) > 0.5 else "J"
        cells = ""
        for name in show:
            v = pnl(configs[name][m], ret[m]).sum() * 1e-4 * 100
            cells += f"{v:>20.2f}"
        print(f"{y:<6d}{seg:>4s}{int(m.sum()):>5d}{cells}")

    sub("2022-2024 INTERVENTION ERA IN ISOLATION")
    m = (yrs >= 2022) & (yrs <= 2024)
    print(f"n = {int(m.sum())} weekly decisions "
          f"({work['decision_date'][m].iloc[0]} .. {work['decision_date'][m].iloc[-1]})")
    print(STAT_HEAD)
    for i, name in enumerate(list(configs)):
        print(stat_line(name, summarize(configs[name][m], ret[m], seed_off=300 + i)))

    # ==================================================================
    # IC DIAGNOSTICS
    # ==================================================================
    hdr("IC DIAGNOSTICS -- Spearman rank correlation of signal vs NEXT-week USD/JPY return")
    print("(descriptive only; never promoted to adoption.  Expected sign for a")
    print(" profitable rule: F1 z POSITIVE (crowded yen longs -> USD/JPY up),")
    print(" F2 d4 NEGATIVE (specs buying yen -> USD/JPY down),")
    print(" F3 d13 POSITIVE (US carry widening -> USD/JPY up).)")
    sigs = {"F1 cot_z": z, "F2 cot_d4": d4, "F3 diff_d13": d13, "cot net level": work["net_nc"].to_numpy()}
    print(f"\n{'signal':<16s}{'segment':<14s}{'n':>7s}{'rho':>9s}{'t':>8s}")
    segs = {"full": slice(0, n), "exploration": expl, "judgment": judg}
    for sname, sv in sigs.items():
        for segname, sl in segs.items():
            r, t, nn = spearman(sv[sl], ret[sl])
            print(f"{sname:<16s}{segname:<14s}{nn:>7d}{r:>9.4f}{t:>8.2f}")

    # full 1986- depth for the COT level/z IC (bi-weekly era included)
    dec_full = build_decisions(cot_all, fx, PUB_EXTRA_DAYS_PRIMARY)
    dff = add_signals(dec_full.frame, dgs2, jgb)
    dff = dff[~dff["ret"].isna()]
    r, t, nn = spearman(dff["cot_z"].to_numpy(), dff["ret"].to_numpy())
    print(f"\nfull COT depth ({dff['decision_date'].iloc[0]} .. {dff['decision_date'].iloc[-1]}, "
          f"bi-weekly era included, holds are NOT all 1 week):")
    print(f"  cot_z vs next-period return: n={nn}  rho={r:+.4f}  t={t:+.2f}")

    sub("VIX CONDITIONING (descriptive)")
    vx = _asof_strictly_before(vix, work["decision_date"])
    have = ~np.isnan(vx)
    q = np.nanpercentile(vx[have], [33, 67])
    for label, mask in (
        ("VIX low   (<%.1f)" % q[0], have & (vx < q[0])),
        ("VIX mid", have & (vx >= q[0]) & (vx <= q[1])),
        ("VIX high  (>%.1f)" % q[1], have & (vx > q[1])),
    ):
        r_, t_, nn_ = spearman(z[mask], ret[mask])
        print(f"  {label:<20s} n={nn_:5d}  cot_z rho={r_:+.4f} (t {t_:+.2f})  "
              f"mean USD/JPY {1e4 * ret[mask].mean():+7.1f}bps")

    # ==================================================================
    # F4 -- POST-INTERVENTION DRIFT (measurement only)
    # ==================================================================
    hdr("F4 -- POST-INTERVENTION DRIFT (MEASUREMENT ONLY, underpowered by design)")
    print("Caveat fixed in advance: the MOF MONTHLY release states the total")
    print("intervention AMOUNT; the currency pair is officially confirmed only with")
    print("the QUARTERLY daily breakdown.  All three clocks are therefore reported.")
    events, disclosures = f4_events(mof, work, "monthly")
    print(f"\nMOF JPY-BUYING disclosure windows inside the weekly era: {len(disclosures)}")
    for dd, amt, days in disclosures:
        print(f"  disclosed {dd}  total {amt:>10,.0f} oku JPY  on {days}")

    base = _all_4w(work)
    blo, bhi = stationary_bootstrap_ci(base * 1e4, mean_block=4.0, seed=SEED + 901)
    print(f"\nunconditional 4-week USD/JPY baseline: n={len(base)}  "
          f"mean {1e4 * base.mean():+.1f}bps  CI [{blo:+.0f}, {bhi:+.0f}]")

    for ci, clock in enumerate(("monthly", "quarterly", "sameday")):
        evs, _ = f4_events(mof, work, clock)
        sub(f"F4 clock = {clock.upper()}   (n = {len(evs)} events)")
        if not evs:
            print("  no usable events")
            continue
        cum = np.array([e["cum4"] for e in evs]) * 1e4
        lo, hi = boot_ci_iid(cum, seed=SEED + 900 + ci)
        m_, t_ = simple_t(cum)
        print(f"{'event decision':<16s}{'w1':>9s}{'w2':>9s}{'w3':>9s}{'w4':>9s}{'cum4 bps':>11s}")
        for e in evs:
            wk = "".join(f"{1e4 * x:>9.0f}" for x in e["weeks"])
            print(f"{str(e['date']):<16s}{wk}{1e4 * e['cum4']:>11.0f}")
        print(f"  USD/JPY 4-week cumulative: n={len(cum)}  mean {m_:+.1f}bps  "
              f"t {t_:+.2f}  iid-bootstrap CI [{lo:+.0f}, {hi:+.0f}] bps  "
              f"(baseline mean {1e4 * base.mean():+.1f})")
        print(f"  -> the SHORT-USD/JPY continuation trade the brief asks about earns "
              f"{-m_:+.1f}bps gross per event")
        print(f"  -> the sign says "
              f"{'REVERSION (USD/JPY rises back)' if m_ > 0 else 'CONTINUATION (yen keeps rallying)'}")
    print("\n  VERDICT: measurement only.  n is an order of magnitude below the n>=80")
    print("           bar; nothing here is eligible for adoption under any clock.")
    events = events or []

    # ==================================================================
    hdr("SUMMARY")
    for name in [winner, "F2 COT flow d4", "F3 rate-diff d13"]:
        s = judg_stats[name]
        print(f"  {name:<26s} judgment n={s.n:4d} ann {s.ann_pct:+6.2f}%  t {s.t:+5.2f}  "
              f"Sharpe {s.sharpe:+5.2f}  -> {'ADOPT' if verdicts[name] else 'REJECT'}")
    print(f"  F4 post-intervention drift : measurement only (n={len(events)})")
    print(f"\nadoptions: {sum(verdicts.values())}")
    return 0


def f4_events(mof: pd.DataFrame, work: pd.DataFrame, clock: str = "monthly"):
    """MOF JPY-buying episodes + the 4 weekly returns that follow.

    clock:
      "monthly"   -- MOF monthly total, last business day of the disclosure
                     month M covering (M-1)-27 .. M-26.  PRIMARY.
      "quarterly" -- the DAILY breakdown, which is what officially confirms the
                     currency pair.  Published early in the second month after
                     quarter end; approximated as quarter_end + 40 days.
      "sameday"   -- the intervention day itself.  Not a disclosure: it assumes
                     the trader recognised the intervention live from the tape.
                     Reported as an informative upper bound only.
    """
    buys = mof[mof["yen_side"] == "JPY_BUY"].copy()

    def window_month(d: date) -> tuple[int, int]:
        if d.day >= 27:
            return (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
        return d.year, d.month

    buys["wy"], buys["wm"] = zip(*[window_month(d) for d in buys["date"]])
    grp = buys.groupby(["wy", "wm"]).agg(
        amount=("amount_oku_jpy", "sum"), days=("date", lambda s: sorted(s))
    )

    dates = np.array(list(work["decision_date"]), dtype=object)
    rets = work["ret"].to_numpy()
    disclosures, events, seen = [], [], set()
    for (y, m), row in grp.iterrows():
        first_day = row["days"][0]
        if clock == "monthly":
            avail = _last_business_day(y, m)
        elif clock == "quarterly":
            qend_m = ((first_day.month - 1) // 3 + 1) * 3
            qend = _last_business_day(first_day.year, qend_m)
            avail = qend + timedelta(days=40)
        else:                                   # sameday
            avail = first_day
        disclosures.append((avail, row["amount"], ", ".join(str(x) for x in row["days"])))
        if avail < dates[0]:
            continue
        j = int(np.searchsorted(dates, avail, side="right"))
        if j >= len(dates) or j + F4_HORIZON > len(rets):
            continue
        if dates[j] in seen:                    # two disclosures, one decision
            continue
        weeks = rets[j : j + F4_HORIZON]
        if np.isnan(weeks).any():
            continue
        seen.add(dates[j])
        events.append({"date": dates[j], "weeks": weeks, "cum4": float(np.sum(weeks))})
    disclosures.sort()
    disclosures = [d for d in disclosures if d[0] >= dates[0]]
    return events, disclosures


def _last_business_day(y: int, m: int) -> date:
    d = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _all_4w(work: pd.DataFrame) -> np.ndarray:
    r = work["ret"].to_numpy()
    out = [np.sum(r[i : i + F4_HORIZON]) for i in range(len(r) - F4_HORIZON + 1)]
    return np.array([x for x in out if not np.isnan(x)])


if __name__ == "__main__":
    sys.exit(main())
