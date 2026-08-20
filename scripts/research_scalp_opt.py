#!/usr/bin/env python3
"""Burst-scalper optimisation study: entry style, hold time, entry frequency.

Answers three questions posed against the live paper scalper
(scripts/run_scalp_paper.py): Binance BTCUSDT moves >= thr bps in 5s ->
enter bitFlyer FX_BTC_JPY taker, hold a fixed 30s, exit taker.

  Q1  Is taker entry/exit wasteful versus resting a maker (limit) order?
  Q2  Is the fixed 30s hold optimal?
  Q3  Can entry frequency rise without losing win rate?

Data
----
today  : bitFlyer Realtime recording data/ws/FX_BTC_JPY_*.jsonl.gz -> real
         1s best_bid / best_ask (lightning_ticker) and 1s executions
         (lightning_executions, with taker side) + Binance 1s aggTrades
         (data/binance_BTCUSDT_1s_today.csv). This is the only dataset with
         REAL QUOTES, so it is the only one that can answer Q1 honestly.
hi1    : 2026-08-19 12:00-18:00 UTC "violent day" window.
         Binance data/binance_BTCUSDT_1s_hi1.csv + bitFlyer TRADE PRICES
         resampled from data/executions_FX_BTC_JPY.csv. No quotes exist for
         this window, so a flat assumed round-trip cost is applied instead.

Everything here is pure replay of files already on disk plus (optionally,
via scripts/fetch_aggtrades.py run separately) Binance public data. No
bitFlyer REST call is made.

Usage:
    PYTHONPATH=src python scripts/research_scalp_opt.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bot.research.board import iter_messages  # noqa: E402

DATA = ROOT / "data"
WS_DIR = DATA / "ws"

# --- cost model -------------------------------------------------------------
# Matches the live paper bot: 2 bps of slippage on top of the crossed quote,
# per side. With real quotes the spread cost is measured, not assumed.
SLIP_BPS = 2.0
# For trade-price-only datasets (hi1) there are no quotes, so the owner's
# stated all-in taker round trip is applied flat instead.
ASSUMED_RT_BPS = 6.35

HOLDS = [5, 10, 30, 60, 120, 300]
THRS = [6, 8, 10, 12, 16, 20]
GAPS = [3.0, 5.0, 8.0]
FILL_WINDOWS = [3, 5, 10]
WINDOW_SEC = 5
COOLDOWN_SEC = 30
LATENCY_SEC = 1          # signal at t -> act at t+1
SMALL_N = 15             # below this, a cell is statistically unreliable

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)


# =========================================================================
# loading
# =========================================================================
def load_today_bitflyer() -> pd.DataFrame:
    """1s bitFlyer series from the Realtime recordings.

    Columns: bid, ask, mid (from lightning_ticker, last value in the second)
    and last / sell_min / buy_max (from lightning_executions, where
    ``side`` is the TAKER side of the print).

    Quote columns are forward filled inside the session (the quote genuinely
    persists until the next tick); execution columns are NOT filled, because
    "no print in this second" is real information the maker-fill rule needs.
    """
    quotes: dict[int, tuple[float, float]] = {}
    ex_last: dict[int, float] = {}
    ex_sell_min: dict[int, float] = {}
    ex_buy_max: dict[int, float] = {}

    files = sorted(WS_DIR.glob("FX_BTC_JPY_*.jsonl.gz"))
    if not files:
        raise SystemExit("no data/ws/*.jsonl.gz recordings found")
    for path in files:
        for rts, channel, msg in iter_messages(path):
            bucket = int(rts)
            if channel.startswith("lightning_ticker_"):
                bid, ask = msg.get("best_bid"), msg.get("best_ask")
                if bid and ask:
                    quotes[bucket] = (float(bid), float(ask))
            elif channel.startswith("lightning_executions_"):
                for ex in msg if isinstance(msg, list) else [msg]:
                    price = float(ex["price"])
                    ex_last[bucket] = price
                    if ex.get("side") == "SELL":
                        ex_sell_min[bucket] = min(
                            ex_sell_min.get(bucket, price), price)
                    elif ex.get("side") == "BUY":
                        ex_buy_max[bucket] = max(
                            ex_buy_max.get(bucket, price), price)

    if not quotes:
        raise SystemExit("recording has no lightning_ticker messages")
    lo, hi = min(quotes), max(quotes)
    grid = np.arange(lo, hi + 1)
    idx = pd.to_datetime(grid, unit="s", utc=True)
    frame = pd.DataFrame(index=idx)
    frame.index.name = "ts"
    frame["bid"] = [quotes.get(b, (np.nan, np.nan))[0] for b in grid]
    frame["ask"] = [quotes.get(b, (np.nan, np.nan))[1] for b in grid]
    frame[["bid", "ask"]] = frame[["bid", "ask"]].ffill(limit=60)
    frame["mid"] = (frame["bid"] + frame["ask"]) / 2.0
    frame["last"] = [ex_last.get(b, np.nan) for b in grid]
    frame["sell_min"] = [ex_sell_min.get(b, np.nan) for b in grid]
    frame["buy_max"] = [ex_buy_max.get(b, np.nan) for b in grid]
    return frame


def load_hi1_bitflyer(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """1s bitFlyer TRADE-PRICE series for the hi1 window (no quotes exist)."""
    df = pd.read_csv(DATA / "executions_FX_BTC_JPY.csv")
    ts = pd.to_datetime(df["exec_date"], utc=True, format="ISO8601")
    df = df.assign(ts=ts).set_index("ts").sort_index()
    df = df.loc[(df.index >= start) & (df.index < end)]
    g = df["price"].resample("1s")
    out = pd.DataFrame({"last": g.last(), "n": g.count()})
    sell = df.loc[df["side"] == "SELL", "price"].resample("1s").min()
    buy = df.loc[df["side"] == "BUY", "price"].resample("1s").max()
    out["sell_min"] = sell.reindex(out.index)
    out["buy_max"] = buy.reindex(out.index)
    out["last"] = out["last"].ffill(limit=120)
    out["mid"] = out["last"]          # best available proxy for this window
    return out.dropna(subset=["last"])


def load_binance(label: str) -> pd.Series:
    path = DATA / f"binance_BTCUSDT_1s_{label}.csv"
    if not path.exists():
        raise SystemExit(f"missing {path}; run scripts/fetch_aggtrades.py first")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    s = df["price"]
    grid = pd.date_range(s.index.min(), s.index.max(), freq="1s", tz="UTC")
    return s.reindex(grid).ffill()


# =========================================================================
# dataset assembly
# =========================================================================
class Dataset:
    """A leader + follower pair aligned on a common 1s UTC grid."""

    def __init__(self, name: str, leader: pd.Series, follower: pd.DataFrame,
                 has_quotes: bool):
        start = max(leader.index.min(), follower.index.min())
        end = min(leader.index.max(), follower.index.max())
        grid = pd.date_range(start, end, freq="1s", tz="UTC")
        self.name = name
        self.has_quotes = has_quotes
        self.leader = leader.reindex(grid).ffill()
        self.f = follower.reindex(grid)
        for col in ("bid", "ask", "mid", "last"):
            if col in self.f:
                self.f[col] = self.f[col].ffill(limit=120)
        self.grid = grid
        self.ret5 = 1e4 * np.log(self.leader / self.leader.shift(WINDOW_SEC))
        ref = self.f["mid"] if has_quotes else self.f["last"]
        self.ref = ref
        self.bf_ret5 = 1e4 * np.log(ref / ref.shift(WINDOW_SEC))
        self.n_sec = len(grid)
        self.hours = self.n_sec / 3600.0

    @property
    def span(self) -> str:
        return (f"{self.grid[0]:%Y-%m-%d %H:%M} -> {self.grid[-1]:%Y-%m-%d %H:%M} UTC "
                f"({self.hours:.2f} h)")

    # -- signal ----------------------------------------------------------
    def events(self, thr: float, gap_min: float | None = None) -> pd.DataFrame:
        """Deduplicated signal events, exactly as the live bot would fire.

        The scan walks forward in time; a second qualifies when
        ``|leader_ret5| >= thr`` (and, when a gap filter is active, the
        leader has run at least ``gap_min`` bps further than bitFlyer in the
        signal direction). Accepting an event starts a ``COOLDOWN_SEC``
        blackout — the filter is applied BEFORE the cooldown, so a filter
        can promote a later event that a rejected one would have masked.
        That is what the live bot does, and it is the only ordering under
        which a filter can genuinely raise the trade count.
        """
        ret = self.ret5.to_numpy()
        gap_raw = (self.ret5 - self.bf_ret5).to_numpy()
        valid_entry = self._entry_valid()
        rows = []
        block_until = -1
        for i in range(WINDOW_SEC, self.n_sec):
            r = ret[i]
            if not np.isfinite(r) or abs(r) < thr:
                continue
            if i <= block_until:
                continue
            direction = 1 if r > 0 else -1
            gap = direction * gap_raw[i]
            if gap_min is not None and not (np.isfinite(gap) and gap >= gap_min):
                continue
            j = i + LATENCY_SEC
            if j >= self.n_sec or not valid_entry[j]:
                continue
            rows.append((i, j, direction, r, gap))
            block_until = i + COOLDOWN_SEC
        return pd.DataFrame(rows, columns=["i", "j", "dir", "ret5", "gap"])

    def _entry_valid(self) -> np.ndarray:
        if self.has_quotes:
            return (self.f["bid"].notna() & self.f["ask"].notna()).to_numpy()
        return self.f["last"].notna().to_numpy()


# =========================================================================
# execution simulation
# =========================================================================
def gross_move(ds: Dataset, ev: pd.DataFrame, hold: int) -> np.ndarray:
    """Follow-through in the signal direction, mid-to-mid, BEFORE any cost.

    Separates "there is no signal" from "there is a signal but the round
    trip eats it" — the two have completely different remedies.
    """
    ref = ds.ref.to_numpy()
    out = np.full(len(ev), np.nan)
    for k, (j, d) in enumerate(zip(ev["j"], ev["dir"])):
        x = j + hold
        if x >= ds.n_sec or not (np.isfinite(ref[j]) and np.isfinite(ref[x])):
            continue
        out[k] = d * 1e4 * math.log(ref[x] / ref[j])
    return out


def taker_capture(ds: Dataset, ev: pd.DataFrame, hold: int) -> np.ndarray:
    """Net bps per trade for taker-in / taker-out at ``hold`` seconds.

    With quotes: buy the ask, sell the bid, 2 bps of slippage each side —
    the spread is measured, never assumed. Without quotes: trade price at
    both ends minus the owner's stated ``ASSUMED_RT_BPS`` round trip.
    """
    out = np.full(len(ev), np.nan)
    n = ds.n_sec
    if ds.has_quotes:
        bid = ds.f["bid"].to_numpy()
        ask = ds.f["ask"].to_numpy()
        for k, (j, d) in enumerate(zip(ev["j"], ev["dir"])):
            x = j + hold
            if x >= n:
                continue
            if d > 0:
                entry, exit_ = ask[j] * (1 + SLIP_BPS / 1e4), bid[x] * (1 - SLIP_BPS / 1e4)
            else:
                entry, exit_ = bid[j] * (1 - SLIP_BPS / 1e4), ask[x] * (1 + SLIP_BPS / 1e4)
            if not (np.isfinite(entry) and np.isfinite(exit_)):
                continue
            out[k] = d * 1e4 * math.log(exit_ / entry)
    else:
        px = ds.f["last"].to_numpy()
        for k, (j, d) in enumerate(zip(ev["j"], ev["dir"])):
            x = j + hold
            if x >= n or not (np.isfinite(px[j]) and np.isfinite(px[x])):
                continue
            out[k] = d * 1e4 * math.log(px[x] / px[j]) - ASSUMED_RT_BPS
    return out


def fade_exit(ds: Dataset, ev: pd.DataFrame, cap: int = 300):
    """Momentum-fade exit: leave when leader_ret5 crosses 0 against us."""
    ret = ds.ret5.to_numpy()
    caps, holds = [], []
    for j, d in zip(ev["j"], ev["dir"]):
        x = min(j + cap, ds.n_sec - 1)
        for t in range(j + 1, min(j + cap, ds.n_sec)):
            if np.isfinite(ret[t]) and d * ret[t] <= 0:
                x = t
                break
        sub = pd.DataFrame({"j": [j], "dir": [d]})
        caps.append(taker_capture(ds, sub, int(x - j))[0])
        holds.append(x - j)
    return np.asarray(caps, float), np.asarray(holds, float)


def maker_sim(ds: Dataset, ev: pd.DataFrame, fill_window: int, hold: int,
              strict_through: bool = False):
    """Rest a limit at the near touch; exit taker ``hold`` s after the fill.

    Fill rule (needs real quotes plus per-print taker side):
      LONG  -> limit at the CURRENT best bid; filled when a taker SELL
               prints at or below that price within ``fill_window`` s.
      SHORT -> limit at the CURRENT best ask; filled when a taker BUY
               prints at or above it.
    ``strict_through`` requires the print to go strictly past the limit,
    which is the pessimistic reading of queue position (we are last in the
    queue at the touch, so a print merely AT our price may not reach us).
    The permissive touch rule is the optimistic bound; both are reported.

    The quote used for the limit price is the LAST one seen in second j, so
    the fill scan starts at j+1 — a print earlier in second j cannot fill an
    order priced off a quote from later in that same second.

    Entry pays no spread and no slippage; the exit is taker, so it pays
    the far quote plus SLIP_BPS. Unfilled orders are misses, capture 0.
    """
    n = ds.n_sec
    bid = ds.f["bid"].to_numpy()
    ask = ds.f["ask"].to_numpy()
    sell_min = ds.f["sell_min"].to_numpy()
    buy_max = ds.f["buy_max"].to_numpy()

    filled, cap, fill_lag = [], [], []
    for j, d in zip(ev["j"], ev["dir"]):
        limit = bid[j] if d > 0 else ask[j]
        if not np.isfinite(limit):
            filled.append(False); cap.append(np.nan); fill_lag.append(np.nan)
            continue
        hit = -1
        for t in range(j + 1, min(j + fill_window + 1, n)):
            if d > 0:
                p = sell_min[t]
                ok = np.isfinite(p) and (p < limit if strict_through else p <= limit)
            else:
                p = buy_max[t]
                ok = np.isfinite(p) and (p > limit if strict_through else p >= limit)
            if ok:
                hit = t
                break
        if hit < 0:
            filled.append(False); cap.append(0.0); fill_lag.append(np.nan)
            continue
        x = hit + hold
        if x >= n:
            filled.append(True); cap.append(np.nan); fill_lag.append(hit - j)
            continue
        exit_ = bid[x] * (1 - SLIP_BPS / 1e4) if d > 0 else ask[x] * (1 + SLIP_BPS / 1e4)
        if not np.isfinite(exit_):
            filled.append(True); cap.append(np.nan); fill_lag.append(hit - j)
            continue
        filled.append(True)
        cap.append(d * 1e4 * math.log(exit_ / limit))
        fill_lag.append(hit - j)
    return np.asarray(filled), np.asarray(cap, float), np.asarray(fill_lag, float)


# =========================================================================
# reporting helpers
# =========================================================================
def flag(n: int) -> str:
    return " *" if n < SMALL_N else ""


def stats(x: np.ndarray) -> dict:
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0, "mean": np.nan, "sd": np.nan, "win%": np.nan, "median": np.nan}
    return {"n": len(x), "mean": x.mean(), "sd": x.std(ddof=1) if len(x) > 1 else np.nan,
            "win%": 100.0 * (x > 0).mean(), "median": float(np.median(x))}


def show(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    print(df.to_string(index=False, float_format=lambda v: f"{v:8.2f}"))


def hr(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# =========================================================================
# analyses
# =========================================================================
def entry_cost_decomposition(ds: Dataset, ev: pd.DataFrame) -> pd.DataFrame:
    """Deterministic cost of getting IN, measured against the mid at entry.

    This is the part of the maker-vs-taker question that does not depend on
    what price does afterwards: crossing the spread costs half-spread +
    slippage, resting at the touch earns half-spread. Fill risk and adverse
    selection are what the rest of the analysis prices.
    """
    bid, ask, mid = (ds.f[c].to_numpy() for c in ("bid", "ask", "mid"))
    tk, mk = [], []
    for j, d in zip(ev["j"], ev["dir"]):
        if not np.isfinite(mid[j]):
            continue
        t_px = ask[j] * (1 + SLIP_BPS / 1e4) if d > 0 else bid[j] * (1 - SLIP_BPS / 1e4)
        m_px = bid[j] if d > 0 else ask[j]
        tk.append(d * 1e4 * math.log(t_px / mid[j]))    # >0 = paid away from mid
        mk.append(d * 1e4 * math.log(m_px / mid[j]))    # <0 = earned vs mid
    return pd.DataFrame([
        {"leg": "TAKER entry (cross + slip)", "n": len(tk), "cost vs mid bps": np.mean(tk)},
        {"leg": "MAKER entry (rest at touch)", "n": len(mk), "cost vs mid bps": np.mean(mk)},
        {"leg": "structural edge of maker entry", "n": len(tk),
         "cost vs mid bps": np.mean(tk) - np.mean(mk)},
    ])


def analysis_a(ds: Dataset, thrs=(12, 10, 8, 6)) -> None:
    hr(f"Q1  ENTRY STYLE — taker vs maker   [{ds.name}]  {ds.span}")
    print("Real bitFlyer quotes + per-print taker side. hold = 30s.")
    print("Taker: cross the spread + 2 bps slippage per side.")
    print("Maker: rest at the near touch, exit taker. Miss = 0 bps, counted in")
    print("       the per-EVENT mean so unfilled opportunity cost is visible.")

    show("Entry-cost decomposition (thr=12 events, before any price move)",
         entry_cost_decomposition(ds, ds.events(12)))

    print("\nthr=12 is the live setting; 10 / 8 / 6 are nested SUPERSETS of it,")
    print("shown only because 12 alone is small-n. They are not independent")
    print("samples — do not add them together.")
    for thr in thrs:
        ev = ds.events(thr)
        if len(ev) == 0:
            print(f"\nthr={thr}: no events")
            continue
        tk = taker_capture(ds, ev, 30)
        tk_s = stats(tk)
        rows = []
        rows.append({"style": "TAKER", "fill_win_s": np.nan, "events": len(ev),
                     "fills": int(np.isfinite(tk).sum()), "fill%": 100.0,
                     "bps/EVENT": tk_s["mean"], "bps/FILL": tk_s["mean"],
                     "win%": tk_s["win%"], "sd": tk_s["sd"]})
        for strict in (False, True):
            for fw in FILL_WINDOWS:
                fl, cp, _ = maker_sim(ds, ev, fw, 30, strict_through=strict)
                per_ev = stats(cp)
                per_fill = stats(cp[fl])
                rows.append({
                    "style": "MAKER-through" if strict else "MAKER-touch",
                    "fill_win_s": fw, "events": len(ev), "fills": int(fl.sum()),
                    "fill%": 100.0 * fl.mean(), "bps/EVENT": per_ev["mean"],
                    "bps/FILL": per_fill["mean"], "win%": per_fill["win%"],
                    "sd": per_fill["sd"]})
        show(f"thr={thr} bps, hold=30s, events={len(ev)}{flag(len(ev))}",
             pd.DataFrame(rows))

        # adverse selection: what the maker's MISSES would have paid as taker
        print("\n  adverse selection (maker fills vs the events maker missed,")
        print("  the missed leg valued at what a TAKER entry would have made):")
        adv = []
        for strict in (False, True):
            for fw in FILL_WINDOWS:
                fl, cp, lag = maker_sim(ds, ev, fw, 30, strict_through=strict)
                f_s = stats(cp[fl])
                m_s = stats(tk[~fl])
                adv.append({
                    "rule": "through" if strict else "touch", "fill_win_s": fw,
                    "n_fill": f_s["n"], "filled bps": f_s["mean"],
                    "n_miss": m_s["n"], "missed-as-taker bps": m_s["mean"],
                    "diff": f_s["mean"] - m_s["mean"],
                    "mean fill lag s": np.nanmean(lag) if np.isfinite(lag).any() else np.nan})
        show(f"  adverse-selection table (thr={thr})", pd.DataFrame(adv))

    # context: how wide is the spread we are paying?
    sp = 1e4 * (ds.f["ask"] - ds.f["bid"]) / ds.f["mid"]
    sp = sp[np.isfinite(sp)]
    print(f"\nSpread context [{ds.name}]: median {sp.median():.2f} bps, "
          f"mean {sp.mean():.2f}, p90 {sp.quantile(0.9):.2f} "
          f"(half-spread median {sp.median()/2:.2f} bps -> taker round trip "
          f"~{sp.median() + 2*SLIP_BPS:.2f} bps all-in)")


def independence_note(ds: Dataset, ev: pd.DataFrame) -> None:
    """How much of a long-hold result is one repeated bet on the drift.

    The 30s cooldown spaces entries ~50s apart. A 300s hold therefore keeps
    6+ overlapping positions open, and if the events also lean one way while
    the market trends, the "trades" at long holds are near-copies of a single
    directional bet — n overstates the real sample size badly.
    """
    j = ev["j"].to_numpy()
    d = ev["dir"].to_numpy()
    gaps = np.diff(j)
    px = ds.ref.dropna()
    drift = 1e4 * math.log(px.iloc[-1] / px.iloc[0])
    print(f"  independence: {len(ev)} events, {int((d > 0).sum())} long / "
          f"{int((d < 0).sum())} short, median {np.median(gaps):.0f}s apart; "
          f"span drift {drift:+.0f} bps")
    parts = []
    for h in HOLDS:
        ov = 100.0 * (gaps < h).mean() if len(gaps) else 0.0
        parts.append(f"{h}s:{ov:.0f}%")
    print("  overlapping consecutive positions by hold -> " + "  ".join(parts))
    print("  (high overlap + a directional event skew means long-hold cells")
    print("   measure the span's drift, not burst follow-through)")


def analysis_b(datasets: list[tuple[Dataset, list[int]]]) -> None:
    hr("Q2  HOLD TIME")
    for ds, thrs in datasets:
        cost = ("measured quotes + 2bps/side slippage" if ds.has_quotes
                else f"trade prices - {ASSUMED_RT_BPS} bps assumed round trip")
        print(f"\n[{ds.name}] {ds.span}   cost model: {cost}")
        for thr in thrs:
            ev = ds.events(thr)
            if len(ev) == 0:
                print(f"  thr={thr}: no events")
                continue
            rows = []
            for h in HOLDS:
                s = stats(taker_capture(ds, ev, h))
                g = stats(gross_move(ds, ev, h))
                rows.append({"hold_s": h, "n": s["n"], "gross bps": g["mean"],
                             "mean bps": s["mean"],
                             "median": s["median"], "sd": s["sd"], "win%": s["win%"],
                             "t-stat": (s["mean"] / (s["sd"] / math.sqrt(s["n"]))
                                        if s["n"] > 1 and s["sd"] else np.nan)})
            fc, fh = fade_exit(ds, ev)
            s = stats(fc)
            rows.append({"hold_s": -1, "n": s["n"], "gross bps": np.nan,
                         "mean bps": s["mean"],
                         "median": s["median"], "sd": s["sd"], "win%": s["win%"],
                         "t-stat": (s["mean"] / (s["sd"] / math.sqrt(s["n"]))
                                    if s["n"] > 1 and s["sd"] else np.nan)})
            tbl = pd.DataFrame(rows)
            show(f"{ds.name} thr={thr}  (hold_s=-1 is the momentum-fade exit, "
                 f"mean holding {np.nanmean(fh):.0f}s, capped 300s)"
                 f"  events={len(ev)}{flag(len(ev))}", tbl)
            fin = tbl[tbl["hold_s"] > 0].dropna(subset=["mean bps"])
            if len(fin):
                best = fin.loc[fin["mean bps"].idxmax()]
                at30 = fin.loc[fin["hold_s"] == 30, "mean bps"]
                msg = (f"  -> peak of the fixed-hold curve: {int(best['hold_s'])}s "
                       f"at {best['mean bps']:.2f} bps (t={best['t-stat']:.2f})")
                if len(at30):
                    msg += f"; 30s = {float(at30.iloc[0]):.2f} bps"
                sig = fin[fin["t-stat"].abs() >= 2.0]
                msg += ("; NO hold is significant at |t|>=2"
                        if len(sig) == 0 else
                        "; significant holds: " +
                        ", ".join(f"{int(h)}s" for h in sig["hold_s"]))
                print(msg)
            independence_note(ds, ev)


def analysis_c(datasets: list[Dataset], hold: int) -> None:
    hr(f"Q3  ENTRY FREQUENCY — threshold sweep and gap filter (hold={hold}s)")
    print("gap(t) = leader 5s return MINUS bitFlyer 5s return, signed by the")
    print("signal direction: how far the leader has run that bitFlyer has not.")
    print("The filter is applied BEFORE the 30s cooldown, so rejecting a weak")
    print("event frees the cooldown for a later, better one.")
    for ds in datasets:
        print(f"\n[{ds.name}] {ds.span}")
        rows = []
        for thr in THRS:
            for gmin in [None] + GAPS:
                ev = ds.events(thr, gap_min=gmin)
                cp = taker_capture(ds, ev, hold) if len(ev) else np.array([])
                s = stats(cp)
                rows.append({
                    "thr": thr, "gap>=": (np.nan if gmin is None else gmin),
                    "events": len(ev), "trades/h": len(ev) / ds.hours,
                    "n": s["n"], "mean bps": s["mean"], "win%": s["win%"],
                    "sd": s["sd"],
                    "EV/h bps": (s["mean"] * s["n"] / ds.hours
                                 if s["n"] else np.nan)})
        tbl = pd.DataFrame(rows)
        tbl["flag"] = ["small-n" if n < SMALL_N else "" for n in tbl["n"]]
        show(f"{ds.name}: frequency vs EV frontier", tbl)

        base = tbl[(tbl["thr"] == 12) & (tbl["gap>="].isna())]
        if len(base) and np.isfinite(base["mean bps"].iloc[0]):
            b_ev, b_n = float(base["mean bps"].iloc[0]), int(base["n"].iloc[0])
            cand = tbl[(tbl["thr"] < 12) & (tbl["gap>="].notna())
                       & (tbl["mean bps"] >= b_ev) & (tbl["n"] >= b_n)]
            print(f"  baseline thr=12 no filter: {b_ev:.2f} bps over {b_n} trades")
            if len(cand):
                print("  lower-threshold + gap-filter cells that match/beat it "
                      "on BOTH EV and trade count:")
                print(cand.to_string(index=False,
                                     float_format=lambda v: f"{v:8.2f}"))
            else:
                print("  no lower-threshold + gap-filter cell beats it on both "
                      "EV and trade count.")


# =========================================================================
def main() -> int:
    print("=" * 78)
    print("BURST SCALPER OPTIMISATION STUDY")
    print("=" * 78)

    today_bf = load_today_bitflyer()
    today = Dataset("today", load_binance("today"), today_bf, has_quotes=True)
    print(f"today  : {today.span}  quote seconds="
          f"{int(today.f['bid'].notna().sum())}/{today.n_sec} "
          f"({100*today.f['bid'].notna().mean():.1f}%), "
          f"seconds with a print={int(today.f['last'].notna().sum())}")

    bn_hi1 = load_binance("hi1")
    hi1_bf = load_hi1_bitflyer(bn_hi1.index.min(), bn_hi1.index.max())
    hi1 = Dataset("hi1", bn_hi1, hi1_bf, has_quotes=False)
    print(f"hi1    : {hi1.span}  seconds with a bitFlyer print="
          f"{int(hi1.f['n'].fillna(0).gt(0).sum())}/{hi1.n_sec} "
          f"({100*hi1.f['n'].fillna(0).gt(0).mean():.1f}%)")

    analysis_a(today)
    analysis_b([(hi1, [12, 20]), (today, [12, 8])])
    # 30s = the live setting; 60s = the shortest hold that is at or near the
    # peak of the Q2 curve on both datasets without running to 300s.
    for hold in (30, 60):
        analysis_c([today, hi1], hold=hold)

    print("\n" + "=" * 78)
    print("* = fewer than %d observations in the cell: unreliable." % SMALL_N)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
