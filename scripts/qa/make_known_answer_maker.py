#!/usr/bin/env python3
"""Generation-2 sealed KNOWN-ANSWER QA packet targeting MAKER FILL-MODEL
claims — the area where the real blind audits actually disagreed (E vs E2,
docs/AUDIT_2026-09/E_cost_floor_maker.md / E2_cost_floor_maker_second.md).

Unlike make_known_answer.py (which plants effects statistically and then
recomputes them from the generated series), this module builds a SIMULATED
LIMIT ORDER BOOK from first principles: a single execution (print) stream
drives both (a) the tape files an auditor reads and (b) a `ReferenceQueue
Simulator` that replays the *exact same* stream to decide, order-by-order,
whether a resting maker order would have filled — fill happens only once
cumulative same-side prints at a price level exceed queue-ahead-size +
own-size before the level re-prices. The truth is therefore known BY
CONSTRUCTION: it is whatever the reference simulator computes, not a
statistical estimate of it.

Files written to backtest_data/qa_known_answer_maker_<date>/:
  ticker_qa_maker_tape.csv.gz      ts, best_bid, best_ask, best_bid_size, best_ask_size
  executions_qa_maker_tape.csv.gz  id, ts, price, size, side   (taker side)
  manifest.md                      (no planted numbers)

Sealed truth -> docs/QA/answers_sealed_maker.json (never shown to an auditor).
Claims       -> docs/QA/claims_for_auditors_maker.md (5 claims, deliberately
                mixed true/false, including a "naive fill-on-print" claim
                that ignores queue position and a claim about the magnitude
                of adverse selection).

Determinism: a single seed drives every draw (sub-streams via
np.random.default_rng(seed).spawn-style integer reseeding), so re-running
with the same --seed/--date reproduces byte-identical CSVs and identical
sealed numbers (only "generated_utc" changes).

Usage:
    python scripts/qa/make_known_answer_maker.py
    python scripts/qa/make_known_answer_maker.py --out-dir /tmp/x --answers-out /tmp/a.json \
        --claims-out /tmp/c.md --date 20260906 --seed 20260906
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED = 20260906

# --------------------------------------------------------------------- #
# market/process constants
# --------------------------------------------------------------------- #
TAPE_DAYS = 3
TAPE_START = "2026-07-06T00:00:00+00:00"
MID0 = 1_000_000.0

EXEC_MEAN_GAP_SEC = 8.0
QUOTE_MEAN_GAP_SEC = 5.0

HALF_SPREAD_BPS = 0.9          # quoted spread = 1.8bps, constant -> at-best capture = 0.9bps/leg
QUOTE_IMPROVE_BPS = 0.3        # 1-tick "inside the spread" price-improvement step
REPRICE_TICK_BPS = 9.0         # how far mid must drift before the touch re-prices
                                # (calibrated so the average level lifetime, ~370s, is
                                # comparable to CAP_SECONDS: too small and every resting
                                # order gets reset before it can ever accumulate a fill)
TICK_LOG = REPRICE_TICK_BPS / 1e4      # re-price threshold in log-mid units
TICK_BPS = QUOTE_IMPROVE_BPS   # backwards-compatible alias used by fill_price()

# Calibrated (by simulate-and-measure, not solved analytically) so the
# realized numbers land in the intended regime: a strongly negative,
# significant net for the correct at-best queue-position model; a small,
# insignificant net for the inside-spread model; a POSITIVE net for the
# naive (queue-blind) comparison model that overstates profitability; and
# an exit-forced-taker fraction in the ~20-30% range.
IMPACT_BPS_PER_UNIT_SIZE = 13.0  # permanent price impact per unit print size
NOISE_SIGMA_LOG = 0.00002        # small idiosyncratic log-price noise/print
P_CONTINUE = 0.66                # trade-sign momentum (Markov continuation prob)
PRINT_SIZE_MEAN_LOG, PRINT_SIZE_SIGMA_LOG = -2.5, 1.0   # matches gen-1 tape convention

QUEUE_SIZE_MEAN_LOG, QUEUE_SIZE_SIGMA_LOG = -1.8, 0.55  # background displayed size/level
OWN_SIZE = 0.85                  # our own resting clip size (own_size in queue units)
CAP_SECONDS = 300.0              # max time resting as maker before forced taker exit
MARKOUT_SECONDS = 5.0            # adverse-selection measurement horizon
TAKER_SLIPPAGE_BPS = 0.3         # extra cost when forced to cross the spread

CROSSED_BOOK_FRACTION = 0.001
N_POSITIONS = 900                # round trips simulated per scenario
POSITION_MEAN_GAP_SEC = (TAPE_DAYS * 86400) / (N_POSITIONS * 1.15)


def gzip_write(path: Path, text: str) -> None:
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
        f.write(text.encode("utf-8"))


def to_iso(sec: float, start: pd.Timestamp) -> str:
    return (start + pd.to_timedelta(sec, unit="s")).isoformat()


# --------------------------------------------------------------------- #
# (1) the ONE execution stream that drives everything: price, queue depth,
#     the CSV files, and the reference simulator's replay all derive from
#     this single array set.
# --------------------------------------------------------------------- #
@dataclass
class ExecStream:
    time: np.ndarray          # seconds from tape start
    side_buy: np.ndarray      # bool, True = taker BUY (hits ask)
    size: np.ndarray
    mid_log: np.ndarray       # cumulative log-mid AFTER this print
    level_id: np.ndarray      # increments each time mid re-prices by >=1 tick
    cum_buy_level: np.ndarray   # per-level cumulative BUY size (depletes ASK queue)
    cum_sell_level: np.ndarray  # per-level cumulative SELL size (depletes BID queue)
    level_ask_start: np.ndarray  # per-row: displayed ask size when this row's level began
    level_bid_start: np.ndarray  # per-row: displayed bid size when this row's level began

    def mid_at(self, t: float) -> float:
        """log-mid in effect at time t (piecewise-constant between prints)."""
        i = np.searchsorted(self.time, t, side="right") - 1
        return 0.0 if i < 0 else float(self.mid_log[i])


def make_exec_stream(rng: np.random.Generator, span_sec: float) -> ExecStream:
    n_est = int(span_sec / EXEC_MEAN_GAP_SEC * 1.3)
    gaps = rng.exponential(EXEC_MEAN_GAP_SEC, n_est)
    t = np.cumsum(gaps)
    t = t[t < span_sec]
    n = len(t)

    # trade-sign momentum: two-state Markov chain (this is what manufactures
    # genuine, mechanically-grounded adverse selection — a maker who gets
    # filled was, by definition, on the wrong side of a print, and momentum
    # means the NEXT few prints tend to continue that direction).
    side_buy = np.empty(n, dtype=bool)
    side_buy[0] = rng.random() < 0.5
    continue_draw = rng.random(n) < P_CONTINUE
    for i in range(1, n):
        side_buy[i] = side_buy[i - 1] if continue_draw[i] else (not side_buy[i - 1])

    size = rng.lognormal(PRINT_SIZE_MEAN_LOG, PRINT_SIZE_SIGMA_LOG, n)
    signed = np.where(side_buy, 1.0, -1.0) * size
    d_log = (IMPACT_BPS_PER_UNIT_SIZE / 1e4) * signed + NOISE_SIGMA_LOG * rng.standard_normal(n)
    mid_log = np.cumsum(d_log)

    # re-pricing: a new "level" starts whenever mid has drifted >=1 tick from
    # the level's anchor. Queue-ahead only ever resets on a level change.
    level_id = np.empty(n, dtype=np.int64)
    anchor = 0.0
    cur = 0
    for i in range(n):
        if abs(mid_log[i] - anchor) >= TICK_LOG:
            cur += 1
            anchor = mid_log[i]
        level_id[i] = cur

    df = pd.DataFrame({"side_buy": side_buy, "size": size, "level_id": level_id})
    df["cum_buy_level"] = np.where(df["side_buy"], df["size"], 0.0)
    df["cum_sell_level"] = np.where(~df["side_buy"], df["size"], 0.0)
    df["cum_buy_level"] = df.groupby("level_id")["cum_buy_level"].cumsum()
    df["cum_sell_level"] = df.groupby("level_id")["cum_sell_level"].cumsum()

    n_levels = int(level_id[-1]) + 1 if n else 0
    level_ask_draw = rng.lognormal(QUEUE_SIZE_MEAN_LOG, QUEUE_SIZE_SIGMA_LOG, n_levels)
    level_bid_draw = rng.lognormal(QUEUE_SIZE_MEAN_LOG, QUEUE_SIZE_SIGMA_LOG, n_levels)

    return ExecStream(
        time=t, side_buy=side_buy, size=size, mid_log=mid_log, level_id=level_id,
        cum_buy_level=df["cum_buy_level"].to_numpy(), cum_sell_level=df["cum_sell_level"].to_numpy(),
        level_ask_start=level_ask_draw[level_id], level_bid_start=level_bid_draw[level_id],
    )


# --------------------------------------------------------------------- #
# (2) reference queue simulator — THE ground truth. A resting maker order
#     fills only once cumulative same-side prints at its price level exceed
#     queue-ahead-size (the displayed size in front of it when it joined)
#     plus its own size, all measured against the SAME exec stream that
#     produced the tape files. A level re-price resets queue position
#     ("chase the touch"); the 300s cap forces a taker exit.
# --------------------------------------------------------------------- #
@dataclass
class LegResult:
    fill_time: float
    fill_type: str          # "maker" | "forced_taker"
    fill_mid_log: float      # log-mid AT fill (contemporaneous)
    quote_mid_log: float     # log-mid from the nearest preceding TICKER quote row
                             # (may differ from fill_mid_log -> the trap)


def _quote_mid_log_before(t: float, quote_times: np.ndarray, quote_mid_log: np.ndarray) -> float:
    i = np.searchsorted(quote_times, t, side="right") - 1
    return float(quote_mid_log[0]) if i < 0 else float(quote_mid_log[i])


class ReferenceQueueSimulator:
    """The auditable ground-truth fill model. `naive=True` switches to the
    flawed comparison model (fills at the very first matching print,
    ignoring queue-ahead entirely) used to demonstrate the naive-model bias."""

    def __init__(self, stream: ExecStream, quote_times: np.ndarray, quote_mid_log: np.ndarray,
                 naive: bool = False):
        self.s = stream
        self.quote_times = quote_times
        self.quote_mid_log = quote_mid_log
        self.naive = naive

    def simulate_leg(self, t0: float, side: str, price_improve_ticks: int) -> LegResult:
        """side: 'BID' (resting buyer) or 'ASK' (resting seller)."""
        s = self.s
        i0 = int(np.searchsorted(s.time, t0, side="left"))
        n = len(s.time)
        if i0 >= n:
            mlog = s.mid_log[-1] if n else 0.0
            return LegResult(t0, "forced_taker", mlog, _quote_mid_log_before(t0, self.quote_times, self.quote_mid_log))

        def displayed_ahead(i: int) -> float:
            if self.naive or price_improve_ticks > 0:
                return 0.0
            return s.level_bid_start[i] if side == "BID" else s.level_ask_start[i]

        join_level = s.level_id[i0]
        queue_ahead = displayed_ahead(i0)
        threshold = 0.0 if self.naive else (queue_ahead + OWN_SIZE)
        # per-level cumulative progress just BEFORE i0 (so we measure only
        # prints from i0 onward)
        prev_cum = 0.0
        if i0 > 0 and s.level_id[i0 - 1] == join_level:
            prev_cum = s.cum_sell_level[i0 - 1] if side == "BID" else s.cum_buy_level[i0 - 1]

        cap_time = t0 + CAP_SECONDS
        for i in range(i0, n):
            ti = s.time[i]
            if ti > cap_time:
                break
            if s.level_id[i] != join_level:
                join_level = s.level_id[i]
                queue_ahead = displayed_ahead(i)
                threshold = 0.0 if self.naive else (queue_ahead + OWN_SIZE)
                prev_cum = 0.0
            matches = (not s.side_buy[i]) if side == "BID" else s.side_buy[i]
            if not matches:
                continue
            cur_cum = s.cum_sell_level[i] if side == "BID" else s.cum_buy_level[i]
            progress = cur_cum - prev_cum
            if self.naive or progress >= threshold:
                return LegResult(ti, "maker", s.mid_log[i],
                                  _quote_mid_log_before(ti, self.quote_times, self.quote_mid_log))

        # timed out -> forced taker exit at the cap
        j = int(np.searchsorted(s.time, cap_time, side="right")) - 1
        mlog = s.mid_log[j] if j >= 0 else 0.0
        return LegResult(cap_time, "forced_taker", mlog,
                          _quote_mid_log_before(cap_time, self.quote_times, self.quote_mid_log))

    def fill_price(self, leg: LegResult, side: str, price_improve_ticks: int) -> float:
        mid = MID0 * math.exp(leg.fill_mid_log)
        if leg.fill_type == "maker":
            # maker BID buys BELOW mid, maker ASK sells ABOVE mid (capture).
            edge = (HALF_SPREAD_BPS - price_improve_ticks * TICK_BPS) / 1e4
            return mid * (1.0 - edge) if side == "BID" else mid * (1.0 + edge)
        # forced taker: CROSSES the spread — a resting BID that times out
        # must buy at the ASK (pay MORE than mid); a resting ASK must sell
        # at the BID (get LESS than mid). This is a genuine cost, not capture.
        edge = (HALF_SPREAD_BPS + TAKER_SLIPPAGE_BPS) / 1e4
        return mid * (1.0 + edge) if side == "BID" else mid * (1.0 - edge)

    def markout_bps(self, leg: LegResult, side: str) -> float | None:
        """Adverse-selection markout at MARKOUT_SECONDS after a MAKER fill,
        signed so positive = bad for the resting order."""
        if leg.fill_type != "maker":
            return None
        mid_fill = MID0 * math.exp(leg.fill_mid_log)
        mid_later = MID0 * math.exp(self.s.mid_at(leg.fill_time + MARKOUT_SECONDS))
        drift_bps = (mid_later - mid_fill) / mid_fill * 1e4
        # BID resting (we bought): adverse = price falling afterwards
        # ASK resting (we sold):   adverse = price rising afterwards
        return -drift_bps if side == "BID" else drift_bps


# --------------------------------------------------------------------- #
# (3) round-trip "positions": entry leg then exit leg, both through the
#     SAME reference simulator, for a given quoting style.
# --------------------------------------------------------------------- #
@dataclass
class RoundTrip:
    direction: str          # "long" | "short"
    entry: LegResult
    exit: LegResult
    net_bps: float
    capture_entry_bps: float
    capture_exit_bps: float
    markout_entry_bps: float | None
    markout_exit_bps: float | None
    exit_forced_taker: bool
    entry_forced_taker: bool


def simulate_positions(sim: ReferenceQueueSimulator, entry_times: np.ndarray,
                        directions: np.ndarray, price_improve_ticks: int) -> list[RoundTrip]:
    out = []
    for t0, direction in zip(entry_times, directions):
        entry_side = "BID" if direction == "long" else "ASK"
        exit_side = "ASK" if direction == "long" else "BID"
        entry = sim.simulate_leg(t0, entry_side, price_improve_ticks)
        entry_price = sim.fill_price(entry, entry_side, price_improve_ticks)
        exit_leg = sim.simulate_leg(entry.fill_time, exit_side, price_improve_ticks)
        exit_price = sim.fill_price(exit_leg, exit_side, price_improve_ticks)

        ref_mid = MID0 * math.exp(sim.s.mid_at(t0))
        pnl = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
        net_bps = pnl / ref_mid * 1e4

        cap_entry = (MID0 * math.exp(entry.fill_mid_log) - entry_price) / entry_price * 1e4
        cap_exit = (exit_price - MID0 * math.exp(exit_leg.fill_mid_log)) / exit_price * 1e4
        if direction == "short":
            cap_entry, cap_exit = -cap_entry, -cap_exit

        out.append(RoundTrip(
            direction=direction, entry=entry, exit=exit_leg, net_bps=net_bps,
            capture_entry_bps=cap_entry, capture_exit_bps=cap_exit,
            markout_entry_bps=sim.markout_bps(entry, entry_side),
            markout_exit_bps=sim.markout_bps(exit_leg, exit_side),
            exit_forced_taker=exit_leg.fill_type == "forced_taker",
            entry_forced_taker=entry.fill_type == "forced_taker",
        ))
    return out


def _mean_t(values: list[float]) -> tuple[float, float, int]:
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    n = arr.size
    if n < 2:
        return (float(arr.mean()) if n else float("nan")), float("nan"), n
    mean = float(arr.mean())
    se = float(arr.std(ddof=1) / math.sqrt(n))
    t = mean / se if se else float("nan")
    return mean, t, n


def summarize(trips: list[RoundTrip], label: str) -> dict:
    net_mean, net_t, n = _mean_t([r.net_bps for r in trips])
    # capture is a maker-fill-only diagnostic (forced-taker legs are a cost,
    # already reflected in net_bps, not a "capture")
    cap_mean, _, _ = _mean_t(
        [r.capture_entry_bps for r in trips if not r.entry_forced_taker] +
        [r.capture_exit_bps for r in trips if not r.exit_forced_taker]
    )
    mo_mean, mo_t, mo_n = _mean_t([r.markout_entry_bps for r in trips if r.markout_entry_bps is not None] +
                                   [r.markout_exit_bps for r in trips if r.markout_exit_bps is not None])
    exit_forced = sum(1 for r in trips if r.exit_forced_taker)
    entry_forced = sum(1 for r in trips if r.entry_forced_taker)
    # trap: net if positions whose exit never closed as maker are DROPPED
    kept = [r for r in trips if not r.exit_forced_taker]
    dropped_net_mean, _, dropped_n = _mean_t([r.net_bps for r in kept])
    return {
        "label": label, "n_positions": n,
        "net_bps_mean": round(net_mean, 4), "net_bps_t_stat": round(net_t, 3),
        "capture_bps_per_leg_mean": round(cap_mean, 4),
        "adverse_selection_bps_at_5s_mean": round(mo_mean, 4),
        "adverse_selection_t_stat": round(mo_t, 3), "adverse_selection_n_legs": mo_n,
        "exit_forced_taker_count": exit_forced,
        "exit_forced_taker_fraction": round(exit_forced / n, 4) if n else None,
        "entry_forced_taker_fraction": round(entry_forced / n, 4) if n else None,
        "biased_net_bps_mean_if_unclosed_positions_dropped": round(dropped_net_mean, 4),
        "n_positions_if_dropped": dropped_n,
    }


# --------------------------------------------------------------------- #
# (4) write the tape files an auditor actually reads
# --------------------------------------------------------------------- #
def write_tape_files(rng: np.random.Generator, stream: ExecStream, out_dir: Path) -> dict:
    start = pd.Timestamp(TAPE_START)
    n = len(stream.time)

    exec_id = 3_100_000_000 + np.arange(n)
    exec_price_mid = MID0 * np.exp(stream.mid_log)
    half = HALF_SPREAD_BPS / 1e4
    exec_price = np.where(stream.side_buy, exec_price_mid * (1 + half), exec_price_mid * (1 - half))
    exec_ts = start + pd.to_timedelta(stream.time, unit="s")
    execs = pd.DataFrame({
        "id": exec_id,
        "ts": exec_ts.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z",
        "price": exec_price, "size": stream.size,
        "side": np.where(stream.side_buy, "BUY", "SELL"),
    })
    efile = "executions_qa_maker_tape.csv.gz"
    gzip_write(out_dir / efile, execs.to_csv(index=False))

    # quote snapshots: independent Poisson stream, own timestamps distinct
    # from executions (this is what makes "quote-time mid" != "fill-time
    # mid" a genuine trap rather than a labeling accident).
    span_sec = TAPE_DAYS * 86400
    n_q_est = int(span_sec / QUOTE_MEAN_GAP_SEC * 1.3)
    gaps_q = rng.exponential(QUOTE_MEAN_GAP_SEC, n_q_est)
    t_q = np.cumsum(gaps_q)
    t_q = t_q[t_q < span_sec]
    n_q = len(t_q)

    idx = np.clip(np.searchsorted(stream.time, t_q, side="right") - 1, 0, n - 1)
    q_mid_log = np.where(idx >= 0, stream.mid_log[idx], 0.0)
    q_mid = MID0 * np.exp(q_mid_log)
    q_bid = q_mid * (1 - half)
    q_ask = q_mid * (1 + half)
    q_bid_size = np.maximum(stream.level_bid_start[idx] - stream.cum_sell_level[idx], 0.001)
    q_ask_size = np.maximum(stream.level_ask_start[idx] - stream.cum_buy_level[idx], 0.001)

    crossed = rng.random(n_q) < CROSSED_BOOK_FRACTION
    n_crossed = int(crossed.sum())
    if n_crossed:
        b = q_bid[crossed].copy()
        q_bid[crossed] = q_ask[crossed]
        q_ask[crossed] = b

    q_ts = start + pd.to_timedelta(t_q, unit="s")
    quotes = pd.DataFrame({
        "ts": q_ts.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z",
        "best_bid": q_bid, "best_ask": q_ask,
        "best_bid_size": q_bid_size, "best_ask_size": q_ask_size,
    })
    qfile = "ticker_qa_maker_tape.csv.gz"
    gzip_write(out_dir / qfile, quotes.to_csv(index=False))

    return {
        "quote_file": qfile, "execution_file": efile,
        "n_quote_rows": int(n_q), "n_execution_rows": int(n),
        "quoted_spread_bps": round(2 * HALF_SPREAD_BPS, 4),
        "tick_bps": TICK_BPS,
        "crossed_book_fraction_target": CROSSED_BOOK_FRACTION,
        "crossed_book_rows": n_crossed,
        "crossed_book_fraction_realized": round(n_crossed / n_q, 6) if n_q else None,
        "date_range_utc": [to_iso(0, start), to_iso(span_sec, start)],
        "_quote_times_sec": t_q, "_quote_mid_log": q_mid_log,  # internal use only
    }


# --------------------------------------------------------------------- #
# (5) mid-reference-inconsistency trap: quote-time mid (nearest preceding
#     ticker row) vs fill-time mid (from the execution stream itself)
# --------------------------------------------------------------------- #
def mid_reference_bias(trips: list[RoundTrip]) -> dict:
    diffs = []
    for r in trips:
        for leg, side in ((r.entry, "BID" if r.direction == "long" else "ASK"),
                           (r.exit, "ASK" if r.direction == "long" else "BID")):
            if leg.fill_type != "maker":
                continue
            fill_mid = MID0 * math.exp(leg.fill_mid_log)
            quote_mid = MID0 * math.exp(leg.quote_mid_log)
            diffs.append(abs(quote_mid - fill_mid) / fill_mid * 1e4)
    mean_bias, _, n = _mean_t(diffs)
    return {"mean_abs_bias_bps": round(mean_bias, 4), "n_maker_fills": n}


# --------------------------------------------------------------------- #
# (6) orchestration
# --------------------------------------------------------------------- #
def generate(out_dir: Path, seed: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    span_sec = TAPE_DAYS * 86400

    stream = make_exec_stream(np.random.default_rng(rng.integers(0, 2**63 - 1)), span_sec)
    tape_info = write_tape_files(np.random.default_rng(rng.integers(0, 2**63 - 1)), stream, out_dir)
    quote_times = tape_info.pop("_quote_times_sec")
    quote_mid_log = tape_info.pop("_quote_mid_log")

    pos_rng = np.random.default_rng(rng.integers(0, 2**63 - 1))
    gaps_p = pos_rng.exponential(POSITION_MEAN_GAP_SEC, int(N_POSITIONS * 1.4))
    entry_times = np.cumsum(gaps_p)
    entry_times = entry_times[entry_times < span_sec - CAP_SECONDS * 2][:N_POSITIONS]
    directions = np.where(pos_rng.random(len(entry_times)) < 0.5, "long", "short")

    sim_true = ReferenceQueueSimulator(stream, quote_times, quote_mid_log, naive=False)
    sim_naive = ReferenceQueueSimulator(stream, quote_times, quote_mid_log, naive=True)

    trips_at_best = simulate_positions(sim_true, entry_times, directions, price_improve_ticks=0)
    trips_inside = simulate_positions(sim_true, entry_times, directions, price_improve_ticks=1)
    trips_naive = simulate_positions(sim_naive, entry_times, directions, price_improve_ticks=0)

    summary_at_best = summarize(trips_at_best, "symmetric_maker_round_trip_at_best")
    summary_inside = summarize(trips_inside, "inside_spread_one_tick_improvement")
    summary_naive = summarize(trips_naive, "naive_fill_on_print_at_best")
    mid_ref_trap = mid_reference_bias(trips_at_best)

    reference_simulator = {
        "own_size": OWN_SIZE, "cap_seconds": CAP_SECONDS, "markout_seconds": MARKOUT_SECONDS,
        "half_spread_bps": HALF_SPREAD_BPS, "tick_bps": TICK_BPS,
        "taker_slippage_bps": TAKER_SLIPPAGE_BPS,
        "symmetric_maker_round_trip_at_best": summary_at_best,
        "inside_spread_one_tick_improvement": summary_inside,
        "naive_fill_on_print_at_best": summary_naive,
        "mid_reference_inconsistency_bias": mid_ref_trap,
    }

    manifest = build_manifest(tape_info, seed)
    (out_dir / "manifest.md").write_text(manifest)
    claims_md, claims = build_claims(reference_simulator)

    answers = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "dataset_dir": str(out_dir.relative_to(REPO_ROOT)) if out_dir.is_relative_to(REPO_ROOT) else str(out_dir),
        "tape": tape_info,
        "reference_simulator": reference_simulator,
        "traps": {
            "crossed_book_rows": {
                "file": tape_info["quote_file"], "fraction_target": CROSSED_BOOK_FRACTION,
                "n_rows": tape_info["crossed_book_rows"],
            },
            "unclosed_maker_positions_must_not_be_dropped": {
                "scenario": "symmetric_maker_round_trip_at_best",
                "fraction_never_closed_as_maker": summary_at_best["exit_forced_taker_fraction"],
                "correct_net_bps_all_positions": summary_at_best["net_bps_mean"],
                "biased_net_bps_if_dropped": summary_at_best["biased_net_bps_mean_if_unclosed_positions_dropped"],
            },
            "mid_reference_inconsistency": mid_ref_trap,
        },
        "claims": claims,
    }
    return {"manifest": manifest, "claims_md": claims_md, "answers": answers}


# --------------------------------------------------------------------- #
# manifest (no planted values) + claims
# --------------------------------------------------------------------- #
MANIFEST_TEMPLATE = """# QA known-answer packet (generation 2) — maker fill model — manifest

Synthetic data generated by `scripts/qa/make_known_answer_maker.py` (fixed
seed) targeting MAKER FILL-MODEL claims — the area where the real blind
audits actually disagreed (see `docs/AUDIT_2026-09/E_cost_floor_maker.md`
and `E2_cost_floor_maker_second.md`). Nothing here is real market data.

Do not open `docs/QA/answers_sealed_maker.json` before completing an audit
of this packet.

## Synthetic tape (quotes + executions, {tape_days} days)

| file | columns | rows |
|---|---|---|
| `{quote_file}` | ts,best_bid,best_ask,best_bid_size,best_ask_size | {n_quote_rows} |
| `{execution_file}` | id,ts,price,size,side | {n_execution_rows} |

`side` is the TAKER's side (BUY/SELL); `best_bid_size`/`best_ask_size` are
the DISPLAYED sizes at the touch at quote time.

## Notes

- Fee: 0 bps maker and taker. Tick = 0.3 bps of price. Own order size for
  any maker strategy under test: 0.85 units.
- Quote rows and execution rows are separate update streams with their own
  timestamps.
- Generated: {generated_utc} (seed {seed}).
"""


def build_manifest(tape_info: dict, seed: int) -> str:
    return MANIFEST_TEMPLATE.format(
        tape_days=TAPE_DAYS, quote_file=tape_info["quote_file"],
        execution_file=tape_info["execution_file"],
        n_quote_rows=tape_info["n_quote_rows"], n_execution_rows=tape_info["n_execution_rows"],
        generated_utc=datetime.now(timezone.utc).isoformat(), seed=seed,
    )


def build_claims(ref: dict) -> tuple[str, list[dict]]:
    at_best = ref["symmetric_maker_round_trip_at_best"]
    inside = ref["inside_spread_one_tick_improvement"]
    naive = ref["naive_fill_on_print_at_best"]

    claims = [
        {
            "id": "QA-M1", "category": "maker_fill", "truth_class": "true_effect", "claim_correct": True,
            "text": (f"最良気配(best)で対称的に maker 発注する往復戦略(300秒 cap、キュー位置ベースの正しい約定"
                     f"モデル)は、ネットで{at_best['net_bps_mean']:.2f}bps/往復"
                     f"(t={at_best['net_bps_t_stat']:.2f})であり、コストを上回らない。"),
        },
        {
            "id": "QA-M2", "category": "maker_fill", "truth_class": "naive_model_bias", "claim_correct": False,
            "text": (f"同じ最良気配 maker 往復戦略は、テープに印字(prints)が立てば直ちに約定したとみなす"
                     f"検証で、ネット+{abs(naive['net_bps_mean']):.1f}bps/往復の収益機会がある"
                     f"(この数値は自前で再計算しても再現するが、キュー位置=自分の前に並ぶ表示数量を"
                     f"無視した約定仮定に依存する)。"),
        },
        {
            "id": "QA-M3", "category": "maker_fill", "truth_class": "correct_null", "claim_correct": True,
            "text": (f"最良気配より1tick 内側に improve した quote での往復は、ネット"
                     f"{inside['net_bps_mean']:+.2f}bps/往復(t={inside['net_bps_t_stat']:.2f})で、"
                     f"0 との有意差はない。"),
        },
        {
            "id": "QA-M4", "category": "maker_fill", "truth_class": "adverse_selection_magnitude",
            "claim_correct": False,
            "text": ("最良気配 maker 約定後 5 秒地点の逆選択(adverse selection)コストは 0 と統計的に"
                     "区別できない(情報優位のあるフローに selection されている証拠はない)。したがって"
                     "キュー位置を正しくモデル化しさえすれば、この往復戦略はネットでプラスに転じるはずである。"),
        },
        {
            "id": "QA-M5", "category": "maker_fill", "truth_class": "survivorship_and_reference_trap",
            "claim_correct": False,
            "text": ("最良気配 maker 往復戦略のネットは、maker では手仕舞えなかった建玉(300秒以内に"
                     "決済 quote が約定しなかったもの)を平均から除外し、かつ capture を「約定直前の"
                     "ticker quote 時点の mid」を基準に計算すると、ネットでプラスになる。"),
        },
    ]
    lines = ["# QA known-answer packet (maker fill model) — claims for auditors", "",
             "以下 5 件を PROTOCOL.md の 10 問に従って判定せよ。番号 (QA-M1..QA-M5) を報告の見出しに使うこと。", ""]
    for c in claims:
        lines.append(f"## {c['id']}\n\n{c['text']}\n")
    return "\n".join(lines), claims


# --------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--answers-out", default=None)
    ap.add_argument("--claims-out", default=None)
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "backtest_data" / f"qa_known_answer_maker_{args.date}"
    answers_out = Path(args.answers_out) if args.answers_out else REPO_ROOT / "docs" / "QA" / "answers_sealed_maker.json"
    claims_out = Path(args.claims_out) if args.claims_out else REPO_ROOT / "docs" / "QA" / "claims_for_auditors_maker.md"
    answers_out.parent.mkdir(parents=True, exist_ok=True)
    claims_out.parent.mkdir(parents=True, exist_ok=True)

    result = generate(out_dir, args.seed)
    answers_out.write_text(json.dumps(result["answers"], indent=2, ensure_ascii=False, sort_keys=False))
    claims_out.write_text(result["claims_md"])

    print(f"wrote dataset -> {out_dir}")
    print(f"wrote sealed answers -> {answers_out}")
    print(f"wrote claims -> {claims_out}")


if __name__ == "__main__":
    main()
