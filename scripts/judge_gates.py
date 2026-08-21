#!/usr/bin/env python3
"""Judgment harness for every pre-registered PENDING gate (docs/KNOWLEDGE.md).

Read-only, idempotent, no network. It opens the files the running components
already write on the owner's machine — logs/bot.jsonl, data/scalp_paper.jsonl,
data/oi_snapshots.csv, data/ws/*.jsonl.gz, candle snapshots — and, for every
pending gate in KNOWLEDGE.md §4 / §5, prints four things side by side:

    the CURRENT SAMPLE SIZE, the MEASURED STATISTIC, the PRE-REGISTERED BAR,
    and a STATUS of PASS / FAIL / INSUFFICIENT (n=X of Y) / READY.

It ADOPTS NOTHING. A PASS here is arithmetic against a bar that was registered
before the data existed; turning a module on, switching a strategy or relaxing
a bar stays a human step (config/composite.yaml module gates require a written
report in docs/ AND owner approval). A FAIL is a rejection report, never an
argument for moving the bar (KNOWLEDGE.md §5).

Gates, with the text they are judged against:

  G1  MAIN BOT (champion)     §5 bar: >= 30 paper trades AND cost-inclusive
      expectancy >= +0.15%/trade AND max drawdown < 10%. Source: closed trades
      reconstructed from logs/bot.jsonl decision records (the log has no
      "closed trade" event; a close is an ORDER_SENT while a position is open,
      and its realized P&L is the step in the cumulative `PnL` field).
  G2  BURST SCALPER           §5 bar: >= 30 events AND net >= +5 bps/trade.
      TWO count restarts apply (§5): the armed-threshold reversion (8 -> 10)
      and the E2 exit switch. Only events after the LATER boundary count; the
      E2 boundary is detected as the first record carrying `exit_kind`.
  G3  ARMED vs UNARMED        §5 ("武装閾値の撤回"): keep logging radar_armed
      and compare inside-window vs outside-window AT EQUAL THRESHOLDS. No
      numeric expectancy bar is pre-registered for the split, so this reports
      the comparison and is READY / INSUFFICIENT only — never PASS/FAIL.
  G4a C2 radar_window subset  config/composite.yaml `radar_window.gate`:
  G4b C3 long_only subset     config/composite.yaml `long_only.gate` — the
      inside-window / long-only SUBSET of champion paper trades must show
      net >= +0.15%/trade AND maxDD < 10% on subset n >= 15 (a deliberate
      deviation from §5's 30, approved with the report), with an
      event-clustered CI excluding 0 and fresh-data confirmation.
  G5  TP VOL TILT             §4: re-judge at LIVE n >= 30 entries carrying
      sigma60_bps. Coverage + expectancy by volatility tercile; the paired
      TP30-vs-TP10 test itself is a separate study (report l).
  G6  OI PHASE-C              §4: judge when data/oi_snapshots.csv reaches
      30 days (~2,900 rows at 15 min). Coverage only.
  G7  BOARD DATA              §4: judge when the board recording reaches 1-2
      weeks (~0.5-1 GB). Coverage only.
  G8  FUNDING WINDOW          §4: re-test the 13:00 UTC post-settlement drift
      at 3x the original n=21, i.e. >= 63 usable settlement days. Coverage
      only (days whose candles cover 13:00-13:30 UTC).

Epoch handling (the part that is easy to get wrong):
  * G2/G3/G5 count only events after the scalper's count-restart boundaries,
    which are read out of the log itself, not assumed.
  * G1/G4 count champion trades from --since (UTC ISO-8601). logs/bot.jsonl
    does NOT record which strategy produced a decision, so a strategy switch
    (xborder_momentum -> composite) cannot be detected here: after a switch the
    owner MUST pass --since <switch time>, per §5's count-restart rule. The
    report says so every run.

Usage:
  PYTHONPATH=src python scripts/judge_gates.py [--root .] [--since ISO8601]
      [--equity JPY] [--bootstrap 2000] [--seed 20260821] [--json]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.radar import StormRadar  # noqa: E402

# ---- pre-registered constants (KNOWLEDGE.md; do not tune here) -------------
MAIN_TRADES_BAR = 30              # §5 main bot: paper trades
MAIN_NET_PCT_BAR = 0.15           # §5 main bot: net % per trade
MAIN_MAXDD_BAR = 10.0             # §5 main bot: max drawdown %
SCALP_EVENTS_BAR = 30             # §5 burst scalper: events
SCALP_NET_BPS_BAR = 5.0           # §5 burst scalper: net bps per trade
SUBSET_N_BAR = 15                 # composite.yaml C2/C3 subset deviation
VOL_TILT_N_BAR = 30               # §4 TP vol tilt: live entries with sigma60
OI_ROWS_BAR = 2900                # §4 OI phase C: ~30 days at 15 min
OI_DAYS_BAR = 30.0
BOARD_DAYS_BAR = 7.0              # §4 board data: 1-2 weeks
BOARD_BYTES_BAR = 500_000_000     # §4 board data: ~0.5-1 GB
FUNDING_N_BAR = 63                # §4 funding window: 3x the original n=21
FUNDING_ORIGINAL_N = 21
FUNDING_HOUR_UTC = 13             # settlement 05/13/21 UTC; 13:00 was measured
FUNDING_WINDOW_MIN = 30

PASS = "PASS"
FAIL = "FAIL"
INSUFFICIENT = "INSUFFICIENT"
READY = "READY"

NON_FILL_STATES = {"PENDING_SUBMIT", "SUBMITTED", "CANCELED", "REJECTED",
                   "STATE_UNKNOWN"}


# ---- result container ------------------------------------------------------
@dataclass
class GateResult:
    gate_id: str
    title: str
    source: str                      # where the bar is registered
    bar: str                         # the bar, as text
    status: str
    n: int = 0
    need: int | None = None
    statistic: str = "-"             # one-line headline number
    detail: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"gate": self.gate_id, "title": self.title, "source": self.source,
                "bar": self.bar, "status": self.status, "n": self.n,
                "need": self.need, "statistic": self.statistic,
                "detail": self.detail, "notes": self.notes,
                "values": self.values}


# ---- small robust readers --------------------------------------------------
def read_jsonl(path: Path, max_bytes: int = 256 * 1024 * 1024) -> tuple[list[dict], int]:
    """Every parseable JSON object in a .jsonl file, plus the bad-line count.

    A half-written last line (the collector is probably still running) and any
    corrupt line in the middle are skipped, never raised: a gate with unreadable
    data must report INSUFFICIENT, not crash the whole report.
    """
    records: list[dict] = []
    bad = 0
    try:
        size = path.stat().st_size
    except OSError:
        return [], 0
    try:
        with open(path, "rb") as f:
            if size > max_bytes:                     # keep the newest tail
                f.seek(size - max_bytes)
                f.readline()
                bad += 1
            for raw in f:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    bad += 1
                    continue
                if isinstance(obj, dict):
                    records.append(obj)
                else:
                    bad += 1
    except OSError:
        return records, bad
    return records, bad


def parse_ts(value: Any) -> float | None:
    """Unix seconds from a float, an ISO-8601 string, or None.

    Naive strings are read as UTC — every writer in this repo stamps UTC
    (bot.logging_setup uses datetime.now(timezone.utc).isoformat()).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _f(value: Any) -> float | None:
    """float() that returns None instead of raising (log fields can be null)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def utc_day(ts: float | None) -> str:
    if ts is None:
        return "unknown"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def iso(ts: float | None) -> str:
    if ts is None:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:                              # pragma: no cover
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:            # noqa: BLE001 - a broken config must not crash the report
        return {}
    return data if isinstance(data, dict) else {}


# ---- statistics ------------------------------------------------------------
def mean(values: Sequence[float]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def median(values: Sequence[float]) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def max_drawdown_pct(pnls: Sequence[float], equity0: float) -> float | None:
    """Peak-to-trough drawdown of the equity path, in percent.

    Equity, not the return series: the §5 bar is a drawdown of the account.
    """
    if equity0 is None or equity0 <= 0:
        return None
    equity = peak = float(equity0)
    worst = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        if peak > 0:
            worst = max(worst, (peak - equity) / peak * 100)
    return worst


def bootstrap_day_ci(samples_by_day: dict[str, list[float]], *, iters: int = 2000,
                     seed: int = 20260821, alpha: float = 0.05
                     ) -> tuple[float, float, int] | None:
    """Percentile CI of the mean, resampling WHOLE UTC DAYS with replacement.

    Trades inside one day share a regime and are not independent; the day is
    the cluster (research-protocol §4.3). Deterministic: fixed seed, no
    network, so a re-run of this harness reproduces the interval exactly.
    """
    days = [d for d, vals in samples_by_day.items() if vals]
    if len(days) < 2:
        return None
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(iters):
        pool: list[float] = []
        for _ in range(len(days)):
            pool.extend(samples_by_day[days[rng.randrange(len(days))]])
        if pool:
            means.append(sum(pool) / len(pool))
    if not means:
        return None
    means.sort()
    lo = means[max(0, int(alpha / 2 * len(means)))]
    hi = means[min(len(means) - 1, int((1 - alpha / 2) * len(means)))]
    return lo, hi, len(days)


def group_by_day(pairs: Iterable[tuple[float | None, float]]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for ts, value in pairs:
        out.setdefault(utc_day(ts), []).append(value)
    return out


def terciles(values: Sequence[float]) -> tuple[float, float] | None:
    vals = sorted(values)
    if len(vals) < 3:
        return None
    return (vals[len(vals) // 3], vals[2 * len(vals) // 3])


# ---- champion (main bot) trades from logs/bot.jsonl ------------------------
@dataclass
class ChampionTrade:
    entry_ts: float | None
    exit_ts: float | None
    side: str                        # LONG / SHORT
    entry_price: float | None
    size: float | None
    notional_jpy: float | None
    pnl_jpy: float | None
    pnl_pct: float | None
    exit_signal: str


def load_champion_trades(root: Path) -> tuple[list[ChampionTrade], dict[str, Any]]:
    """Reconstruct closed paper trades from the decision log.

    logs/bot.jsonl has no closed-trade event: bot.main.log_decision writes one
    record per completed candle with `decision`, `strategy_signal`,
    `order_size`, `order_price`, `execution_status` and the CUMULATIVE realized
    `PnL` (bot.logging_setup.log_decision, written after the fill is booked).
    So a trade is: an ORDER_SENT that opens a position, then the next
    ORDER_SENT (BUY/SELL/CLOSE/STOP_LOSS) while it is open, whose realized P&L
    is the step in `PnL` at that record.
    """
    path = root / "logs" / "bot.jsonl"
    records, bad = read_jsonl(path)
    meta: dict[str, Any] = {
        "path": str(path), "exists": path.exists(), "records": len(records),
        "bad_lines": bad, "decisions": 0, "open_at_end": False,
        "unresolved_orders": 0, "unmeasured_closes": 0,
    }
    trades: list[ChampionTrade] = []
    last_pnl: float | None = None
    open_trade: dict[str, Any] | None = None

    for rec in records:
        if rec.get("event") != "decision" and not rec.get("strategy_signal"):
            continue
        meta["decisions"] += 1
        ts = parse_ts(rec.get("timestamp"))
        pnl_now = _f(rec.get("PnL"))
        if rec.get("decision") != "ORDER_SENT":
            if pnl_now is not None:
                last_pnl = pnl_now if last_pnl is None else last_pnl
            continue
        state = rec.get("execution_status")
        signal = str(rec.get("strategy_signal") or "")
        price = _f(rec.get("order_price"))
        size = _f(rec.get("order_size"))
        filled = state is None or state not in NON_FILL_STATES

        if open_trade is None:
            if not filled:
                meta["unresolved_orders"] += 1
                if pnl_now is not None and last_pnl is None:
                    last_pnl = pnl_now
                continue
            if signal not in ("BUY", "SELL"):
                # a CLOSE/STOP_LOSS with no open position: nothing to pair
                if pnl_now is not None and last_pnl is None:
                    last_pnl = pnl_now
                continue
            if last_pnl is None:
                # baseline: the P&L already on the books when the log starts
                last_pnl = pnl_now if pnl_now is not None else 0.0
            open_trade = {"ts": ts, "side": "LONG" if signal == "BUY" else "SHORT",
                          "price": price, "size": size}
            continue

        # a position is open -> this order closes it
        delta = None if (pnl_now is None or last_pnl is None) else pnl_now - last_pnl
        if not filled and (delta is None or delta == 0.0):
            # ambiguous close (STATE_UNKNOWN and no realized step): the
            # position may still be open, so do not book a trade
            meta["unresolved_orders"] += 1
            continue
        notional = None
        if open_trade["price"] and open_trade["size"]:
            notional = open_trade["price"] * open_trade["size"]
        elif price and size:
            notional = price * size
        pnl_pct = None
        if delta is not None and notional:
            pnl_pct = delta / notional * 100
        if delta is None:
            meta["unmeasured_closes"] += 1
        trades.append(ChampionTrade(
            entry_ts=open_trade["ts"], exit_ts=ts, side=open_trade["side"],
            entry_price=open_trade["price"], size=open_trade["size"],
            notional_jpy=notional, pnl_jpy=delta, pnl_pct=pnl_pct,
            exit_signal=signal or "?"))
        open_trade = None
        if pnl_now is not None:
            last_pnl = pnl_now

    meta["open_at_end"] = open_trade is not None
    return trades, meta


# ---- scalper events from data/scalp_paper.jsonl ----------------------------
@dataclass
class ScalpTrade:
    entry_ts: float | None
    exit_ts: float | None
    side: str
    notional_jpy: float | None
    pnl_jpy: float | None
    bps: float | None
    radar_armed: bool | None
    thr_bps: float | None
    sigma60_bps: float | None
    v60_btc: float | None
    exit_kind: str | None


def load_scalp_trades(root: Path) -> tuple[list[ScalpTrade], dict[str, Any]]:
    """Completed scalper events, plus the count-restart boundaries.

    Event vocabulary (scripts/run_scalp_paper.py): `start` (the full arg set),
    `limit_placed` / `entry` (entry side, carrying radar_armed, thr_bps,
    sigma60_bps, v60_btc), `fill` (maker entry price/size), `missed`, `exit`
    (pnl_jpy and, since the E2 switch, exit_kind), `radar_state`.

    Boundaries returned in meta:
      e2_ts   — first record carrying `exit_kind` (the E2 exit switch, §5).
      thr_ts  — first `start` after the last session whose --thr-armed-bps
                differed from --thr-bps (the armed-threshold reversion, §5).
      epoch_ts — the LATER of the two: that is the one that binds.
    """
    path = root / "data" / "scalp_paper.jsonl"
    records, bad = read_jsonl(path)
    meta: dict[str, Any] = {
        "path": str(path), "exists": path.exists(), "records": len(records),
        "bad_lines": bad, "e2_ts": None, "thr_ts": None, "epoch_ts": None,
        "epoch_reason": "no count-restart boundary found in the log",
        "orphan_exits": 0, "session_thr_bps": None, "session_notional": None,
        "unequal_threshold_sessions": 0,
    }

    # ---- boundaries ----
    starts = [r for r in records if r.get("event") == "start"]
    last_unequal = None
    for rec in starts:
        thr = _f(rec.get("thr_bps"))
        thr_armed = _f(rec.get("thr_armed_bps"))
        if thr is not None and thr_armed is not None and thr_armed != thr:
            last_unequal = parse_ts(rec.get("ts"))
            meta["unequal_threshold_sessions"] += 1
        if thr is not None:
            meta["session_thr_bps"] = thr
        notional = _f(rec.get("notional"))
        if notional:
            meta["session_notional"] = notional
    if last_unequal is not None:
        for rec in starts:
            ts = parse_ts(rec.get("ts"))
            if ts is not None and ts > last_unequal:
                meta["thr_ts"] = ts
                break
        if meta["thr_ts"] is None:
            # every session in the log ran unequal thresholds
            meta["thr_ts"] = float("inf")
    for rec in records:
        if "exit_kind" in rec:
            meta["e2_ts"] = parse_ts(rec.get("ts"))
            break
    bounds = [(meta["e2_ts"], "E2 exit switch (first record carrying exit_kind)"),
              (meta["thr_ts"], "armed-threshold reversion (first start with "
                               "--thr-armed-bps == --thr-bps)")]
    bounds = [(ts, why) for ts, why in bounds if ts is not None]
    if bounds:
        ts, why = max(bounds, key=lambda pair: pair[0])
        meta["epoch_ts"] = ts
        meta["epoch_reason"] = why

    # ---- events ----
    trades: list[ScalpTrade] = []
    pending: dict[str, Any] | None = None       # entry-side features
    position: dict[str, Any] | None = None
    for rec in records:
        event = rec.get("event")
        ts = parse_ts(rec.get("ts"))
        if event in ("limit_placed", "entry"):
            pending = {
                "ts": ts, "side": str(rec.get("side") or "?"),
                "radar_armed": rec.get("radar_armed") if isinstance(
                    rec.get("radar_armed"), bool) else None,
                "thr_bps": _f(rec.get("thr_bps")),
                "sigma60_bps": _f(rec.get("sigma60_bps")),
                "v60_btc": _f(rec.get("v60_btc")),
            }
            if event == "entry":                # taker entry fills immediately
                price, size = _f(rec.get("price")), _f(rec.get("size"))
                position = dict(pending)
                position["notional"] = price * size if price and size else None
        elif event == "fill":
            price, size = _f(rec.get("price")), _f(rec.get("size"))
            position = dict(pending or {"ts": ts, "side": str(rec.get("side") or "?"),
                                        "radar_armed": None, "thr_bps": None,
                                        "sigma60_bps": None, "v60_btc": None})
            position["notional"] = price * size if price and size else None
            if position.get("ts") is None:
                position["ts"] = ts
        elif event == "missed":
            pending = None
        elif event == "exit":
            pnl = _f(rec.get("pnl_jpy"))
            pos = position or {}
            if not position:
                meta["orphan_exits"] += 1
            notional = pos.get("notional") or meta["session_notional"]
            bps = (pnl / notional * 1e4) if (pnl is not None and notional) else None
            trades.append(ScalpTrade(
                entry_ts=pos.get("ts"), exit_ts=ts,
                side=str(pos.get("side") or rec.get("side") or "?"),
                notional_jpy=notional, pnl_jpy=pnl, bps=bps,
                radar_armed=pos.get("radar_armed"), thr_bps=pos.get("thr_bps"),
                sigma60_bps=pos.get("sigma60_bps"), v60_btc=pos.get("v60_btc"),
                exit_kind=rec.get("exit_kind")))
            position, pending = None, None
    return trades, meta


def in_epoch(trades: list[ScalpTrade], epoch_ts: float | None) -> list[ScalpTrade]:
    """Events at or after the binding count-restart boundary.

    No boundary in the log means no E2-era evidence at all, not "count
    everything": the pre-E2 events belong to a retired exit rule (§5).
    """
    if epoch_ts is None:
        return []
    return [t for t in trades if t.exit_ts is not None and t.exit_ts >= epoch_ts]


# ---- gate 1: main bot ------------------------------------------------------
def _pct_stats(trades: Sequence[ChampionTrade], equity0: float, *, iters: int,
               seed: int) -> dict[str, Any]:
    pcts = [t.pnl_pct for t in trades if t.pnl_pct is not None]
    pnls = [t.pnl_jpy for t in trades if t.pnl_jpy is not None]
    ci = bootstrap_day_ci(group_by_day(
        [(t.entry_ts, t.pnl_pct) for t in trades if t.pnl_pct is not None]),
        iters=iters, seed=seed)
    return {
        "n": len(trades),
        "n_measured": len(pcts),
        "net_pct": mean(pcts),
        "median_pct": median(pcts),
        "win_rate": (sum(1 for p in pcts if p > 0) / len(pcts) * 100) if pcts else None,
        "total_pnl_jpy": sum(pnls) if pnls else 0.0,
        "max_dd_pct": max_drawdown_pct(pnls, equity0),
        "ci": ci,
    }


def _fmt(value: float | None, spec: str = ".4f") -> str:
    return "-" if value is None else format(value, spec)


def _ci_text(ci: tuple[float, float, int] | None, unit: str) -> str:
    if ci is None:
        return "CI n/a (needs >= 2 UTC day clusters)"
    lo, hi, days = ci
    return f"95% CI [{lo:+.4f}, {hi:+.4f}] {unit} over {days} day clusters"


def gate_main_bot(trades: list[ChampionTrade], meta: dict, equity0: float, *,
                  since: float | None, iters: int, seed: int) -> GateResult:
    res = GateResult(
        gate_id="G1", title="Main bot (champion) paper trades",
        source="KNOWLEDGE.md §5 adoption table (c, d, g)",
        bar=f">= {MAIN_TRADES_BAR} trades AND net >= +{MAIN_NET_PCT_BAR}%/trade "
            f"AND maxDD < {MAIN_MAXDD_BAR}%",
        status=INSUFFICIENT, need=MAIN_TRADES_BAR)
    if not meta["exists"]:
        res.statistic = "no logs/bot.jsonl"
        res.notes.append(f"{meta['path']} not found — the bot has not run here.")
        return res
    kept = [t for t in trades if since is None or (t.entry_ts or 0) >= since]
    st = _pct_stats(kept, equity0, iters=iters, seed=seed)
    res.n = st["n"]
    res.values = {k: v for k, v in st.items() if k != "ci"}
    res.values["ci"] = list(st["ci"]) if st["ci"] else None
    res.statistic = (f"net {_fmt(st['net_pct'])}%/trade, "
                     f"maxDD {_fmt(st['max_dd_pct'], '.2f')}%")
    res.detail = [
        f"trades {st['n']} (measured %: {st['n_measured']}), "
        f"median {_fmt(st['median_pct'])}%, win rate {_fmt(st['win_rate'], '.1f')}%",
        f"total realized {st['total_pnl_jpy']:+.1f} JPY on equity base "
        f"{equity0:,.0f} JPY; " + _ci_text(st["ci"], "%/trade"),
    ]
    if kept:
        res.detail.append(f"span {iso(kept[0].entry_ts)} .. {iso(kept[-1].exit_ts)}")
    if st["n"] < MAIN_TRADES_BAR:
        res.status = INSUFFICIENT
    elif (st["net_pct"] is not None and st["net_pct"] >= MAIN_NET_PCT_BAR
            and st["max_dd_pct"] is not None and st["max_dd_pct"] < MAIN_MAXDD_BAR):
        res.status = PASS
    else:
        res.status = FAIL
    res.notes.append(
        "COUNT RESTART: §5 restarts the 30-trade count at a strategy switch "
        "(strategy.name), and bot.jsonl records no strategy name — after a "
        "switch pass --since <switch UTC>. "
        + (f"Counting from --since {iso(since)}." if since else
           "No --since given: counting the whole log."))
    if meta["unresolved_orders"]:
        res.notes.append(f"{meta['unresolved_orders']} order record(s) in a "
                         "non-fill state (STATE_UNKNOWN etc.) were not booked "
                         "as trades.")
    if meta["unmeasured_closes"]:
        res.notes.append(f"{meta['unmeasured_closes']} close(s) had no PnL "
                         "field and are counted but not averaged.")
    if meta["open_at_end"]:
        res.notes.append("a position is still open at the end of the log; it "
                         "is not counted.")
    if meta["bad_lines"]:
        res.notes.append(f"{meta['bad_lines']} unparseable line(s) skipped.")
    return res


# ---- gate 2: scalper -------------------------------------------------------
def _bps_stats(trades: Sequence[ScalpTrade], *, iters: int, seed: int) -> dict[str, Any]:
    bps = [t.bps for t in trades if t.bps is not None]
    ci = bootstrap_day_ci(group_by_day(
        [(t.entry_ts or t.exit_ts, t.bps) for t in trades if t.bps is not None]),
        iters=iters, seed=seed)
    return {"n": len(trades), "n_measured": len(bps), "net_bps": mean(bps),
            "median_bps": median(bps),
            "win_rate": (sum(1 for b in bps if b > 0) / len(bps) * 100) if bps else None,
            "ci": ci}


def gate_scalper(trades: list[ScalpTrade], meta: dict, *, iters: int,
                 seed: int) -> GateResult:
    res = GateResult(
        gate_id="G2", title="Burst scalper (E2 exit) events",
        source="KNOWLEDGE.md §5 adoption table (e, i) + §5 count restarts",
        bar=f">= {SCALP_EVENTS_BAR} events AND net >= +{SCALP_NET_BPS_BAR} bps/trade",
        status=INSUFFICIENT, need=SCALP_EVENTS_BAR)
    if not meta["exists"]:
        res.statistic = "no data/scalp_paper.jsonl"
        res.notes.append(f"{meta['path']} not found — the scalper has not run here.")
        return res
    kept = in_epoch(trades, meta["epoch_ts"])
    st = _bps_stats(kept, iters=iters, seed=seed)
    res.n = st["n"]
    res.values = {k: v for k, v in st.items() if k != "ci"}
    res.values["ci"] = list(st["ci"]) if st["ci"] else None
    res.values["epoch_ts"] = meta["epoch_ts"]
    res.statistic = f"net {_fmt(st['net_bps'], '.2f')} bps/trade"
    res.detail = [
        f"events after the epoch {st['n']} of {len(trades)} in the log; "
        f"median {_fmt(st['median_bps'], '.2f')} bps, win rate "
        f"{_fmt(st['win_rate'], '.1f')}%",
        _ci_text(st["ci"], "bps/trade"),
    ]
    if st["n"] < SCALP_EVENTS_BAR:
        res.status = INSUFFICIENT
    elif st["net_bps"] is not None and st["net_bps"] >= SCALP_NET_BPS_BAR:
        res.status = PASS
    else:
        res.status = FAIL
    res.notes.append(
        "EPOCH: counting from " + iso(meta["epoch_ts"]) + " — "
        + meta["epoch_reason"] + ". E2 boundary "
        + (iso(meta["e2_ts"]) if meta["e2_ts"] else "not found")
        + "; armed-threshold boundary "
        + (iso(meta["thr_ts"]) if meta["thr_ts"] not in (None, float("inf"))
           else ("never restored in this log" if meta["thr_ts"] == float("inf")
                 else "not applicable (no unequal-threshold session logged)"))
        + ".")
    if meta["epoch_ts"] is None:
        res.notes.append("No record carries exit_kind: every event in this log "
                         "predates the E2 switch, so none of them count "
                         "toward the 30 (§5).")
    if meta["orphan_exits"]:
        res.notes.append(f"{meta['orphan_exits']} exit(s) had no matching "
                         "entry/fill in the log (truncated head); their "
                         "notional falls back to the session --notional.")
    if meta["bad_lines"]:
        res.notes.append(f"{meta['bad_lines']} unparseable line(s) skipped.")
    return res


# ---- gate 3: armed vs unarmed ---------------------------------------------
def gate_armed_split(trades: list[ScalpTrade], meta: dict, *, iters: int,
                     seed: int) -> GateResult:
    res = GateResult(
        gate_id="G3", title="Armed vs unarmed at EQUAL thresholds",
        source="KNOWLEDGE.md §5 (武装閾値の撤回, report i)",
        bar=f"comparison only — no expectancy bar registered; "
            f"read at >= {SCALP_EVENTS_BAR} events per arm",
        status=INSUFFICIENT, need=SCALP_EVENTS_BAR)
    if not meta["exists"]:
        res.statistic = "no data/scalp_paper.jsonl"
        res.notes.append(f"{meta['path']} not found — the scalper has not run here.")
        return res
    kept = [t for t in in_epoch(trades, meta["epoch_ts"])
            if t.radar_armed is not None and t.bps is not None]
    thr_ref = meta["session_thr_bps"]
    unarmed_thrs = {t.thr_bps for t in kept if t.radar_armed is False
                    and t.thr_bps is not None}
    if len(unarmed_thrs) == 1:
        thr_ref = next(iter(unarmed_thrs))
    eligible = [t for t in kept if t.thr_bps is None or thr_ref is None
                or t.thr_bps == thr_ref]
    dropped = len(kept) - len(eligible)
    armed = [t for t in eligible if t.radar_armed]
    unarmed = [t for t in eligible if not t.radar_armed]
    a = _bps_stats(armed, iters=iters, seed=seed)
    u = _bps_stats(unarmed, iters=iters, seed=seed)
    res.n = min(a["n"], u["n"])
    diff = None
    if a["net_bps"] is not None and u["net_bps"] is not None:
        diff = a["net_bps"] - u["net_bps"]
    res.statistic = (f"armed {_fmt(a['net_bps'], '.2f')} vs unarmed "
                     f"{_fmt(u['net_bps'], '.2f')} bps (diff {_fmt(diff, '+.2f')})")
    res.values = {"thr_ref_bps": thr_ref, "armed": a["n"], "unarmed": u["n"],
                  "armed_bps": a["net_bps"], "unarmed_bps": u["net_bps"],
                  "diff_bps": diff}
    res.detail = [
        f"armed n={a['n']} net {_fmt(a['net_bps'], '.2f')} bps, "
        f"win {_fmt(a['win_rate'], '.1f')}%; " + _ci_text(a["ci"], "bps"),
        f"unarmed n={u['n']} net {_fmt(u['net_bps'], '.2f')} bps, "
        f"win {_fmt(u['win_rate'], '.1f')}%; " + _ci_text(u["ci"], "bps"),
    ]
    res.status = READY if (a["n"] >= SCALP_EVENTS_BAR
                           and u["n"] >= SCALP_EVENTS_BAR) else INSUFFICIENT
    res.notes.append(
        f"equal-threshold filter: reference thr {_fmt(thr_ref, '.1f')} bps"
        + (f"; {dropped} event(s) at a different threshold excluded" if dropped
           else "") + ".")
    res.notes.append("This split is diagnostic. Lowering the armed threshold "
                     "was REJECTED (report i); nothing here re-adopts it.")
    return res


# ---- gate 4: C2 / C3 subsets ----------------------------------------------
def _subset_gate(gate_id: str, title: str, module: str, gate_text: str,
                 subset: list[ChampionTrade], equity0: float, *,
                 iters: int, seed: int, extra: list[str]) -> GateResult:
    res = GateResult(
        gate_id=gate_id, title=title,
        source=f"config/composite.yaml modules.{module}.gate (tournament T)",
        bar=f"subset n >= {SUBSET_N_BAR} AND net >= +{MAIN_NET_PCT_BAR}%/trade "
            f"AND maxDD < {MAIN_MAXDD_BAR}% AND day-clustered CI excludes 0",
        status=INSUFFICIENT, need=SUBSET_N_BAR)
    st = _pct_stats(subset, equity0, iters=iters, seed=seed)
    res.n = st["n"]
    res.values = {k: v for k, v in st.items() if k != "ci"}
    res.values["ci"] = list(st["ci"]) if st["ci"] else None
    res.statistic = (f"net {_fmt(st['net_pct'])}%/trade, "
                     f"maxDD {_fmt(st['max_dd_pct'], '.2f')}%")
    ci = st["ci"]
    ci_excludes_zero = ci is not None and (ci[0] > 0 or ci[1] < 0)
    res.detail = [
        f"subset n={st['n']}, median {_fmt(st['median_pct'])}%, win rate "
        f"{_fmt(st['win_rate'], '.1f')}%, realized {st['total_pnl_jpy']:+.1f} JPY",
        _ci_text(ci, "%/trade") + (" — excludes 0" if ci_excludes_zero
                                   else " — includes 0"),
    ]
    res.detail.extend(extra)
    if st["n"] < SUBSET_N_BAR:
        res.status = INSUFFICIENT
    elif (st["net_pct"] is not None and st["net_pct"] >= MAIN_NET_PCT_BAR
            and st["max_dd_pct"] is not None and st["max_dd_pct"] < MAIN_MAXDD_BAR
            and ci_excludes_zero):
        res.status = PASS
    else:
        res.status = FAIL
    res.notes.append(f"gate text: {gate_text}")
    res.notes.append("Numbers only. The module stays OFF until a written "
                     "docs/ report and OWNER APPROVAL — including approval of "
                     f"the n>={SUBSET_N_BAR} deviation from §5's 30 — plus "
                     "fresh-data confirmation, which this harness cannot check.")
    return res


def gates_subsets(trades: list[ChampionTrade], meta: dict, equity0: float, *,
                  since: float | None, radar: StormRadar, iters: int,
                  seed: int, composite: dict) -> list[GateResult]:
    modules = (composite.get("modules") or {}) if isinstance(composite, dict) else {}
    kept = [t for t in trades if since is None or (t.entry_ts or 0) >= since]
    inside = [t for t in kept if t.entry_ts is not None and radar.is_armed(t.entry_ts)]
    longs = [t for t in kept if t.side == "LONG"]
    c2 = _subset_gate(
        "G4a", "C2 radar_window subset (champion)", "radar_window",
        str((modules.get("radar_window") or {}).get("gate", "(gate text not "
                                                            "found in config/composite.yaml)")),
        inside, equity0, iters=iters, seed=seed,
        extra=[f"window {radar.window}; {len(inside)} of {len(kept)} champion "
               f"trades opened inside it"])
    c3 = _subset_gate(
        "G4b", "C3 long-only subset (champion)", "long_only",
        str((modules.get("long_only") or {}).get("gate", "(gate text not found "
                                                         "in config/composite.yaml)")),
        longs, equity0, iters=iters, seed=seed,
        extra=[f"{len(longs)} long of {len(kept)} champion trades "
               f"({len(kept) - len(longs)} short)"])
    for res in (c2, c3):
        if not meta["exists"]:
            res.statistic = "no logs/bot.jsonl"
            res.notes.insert(0, f"{meta['path']} not found.")
    return [c2, c3]


# ---- gate 5: TP vol tilt ---------------------------------------------------
def gate_vol_tilt(trades: list[ScalpTrade], meta: dict, *, iters: int,
                  seed: int) -> GateResult:
    res = GateResult(
        gate_id="G5", title="TP volatility tilt (sigma60 terciles)",
        source="KNOWLEDGE.md §4 (report l)",
        bar=f"re-judge at LIVE n >= {VOL_TILT_N_BAR} entries carrying sigma60_bps",
        status=INSUFFICIENT, need=VOL_TILT_N_BAR)
    if not meta["exists"]:
        res.statistic = "no data/scalp_paper.jsonl"
        res.notes.append(f"{meta['path']} not found — the scalper has not run here.")
        return res
    kept = [t for t in in_epoch(trades, meta["epoch_ts"])
            if t.sigma60_bps is not None and t.bps is not None]
    res.n = len(kept)
    cuts = terciles([t.sigma60_bps for t in kept])
    buckets: dict[str, list[ScalpTrade]] = {"low": [], "mid": [], "high": []}
    if cuts:
        lo_cut, hi_cut = cuts
        for t in kept:
            key = "low" if t.sigma60_bps < lo_cut else (
                "high" if t.sigma60_bps >= hi_cut else "mid")
            buckets[key].append(t)
    stats = {k: _bps_stats(v, iters=iters, seed=seed) for k, v in buckets.items()}
    res.values = {"cuts_bps": list(cuts) if cuts else None,
                  "buckets": {k: {"n": v["n"], "net_bps": v["net_bps"]}
                              for k, v in stats.items()}}
    high, low = stats["high"]["net_bps"], stats["low"]["net_bps"]
    tilt = None if (high is None or low is None) else high - low
    res.statistic = (f"high-low tilt {_fmt(tilt, '+.2f')} bps"
                     if tilt is not None else "-")
    res.detail = [
        (f"tercile cuts sigma60 {_fmt(cuts[0], '.2f')} / {_fmt(cuts[1], '.2f')} bps"
         if cuts else "not enough entries to form terciles"),
    ] + [f"{k:>4} n={stats[k]['n']:>3} net {_fmt(stats[k]['net_bps'], '+.2f')} bps"
         for k in ("low", "mid", "high")]
    res.status = READY if res.n >= VOL_TILT_N_BAR else INSUFFICIENT
    res.notes.append("Coverage + readout only. The pending hypothesis is the "
                     "PAIRED TP30-vs-TP10 comparison of report l; the paper "
                     "runner trades one TP, so reaching n only makes the "
                     "re-judgment (a separate study) possible.")
    return res


# ---- gate 6: OI phase C ----------------------------------------------------
def _csv_first_last_ts(path: Path, column: str = "ts_utc"
                       ) -> tuple[int, float | None, float | None, int]:
    """(rows, first ts, last ts, bad rows) for an append-only CSV."""
    rows = bad = 0
    first = last = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            header = f.readline().strip().split(",")
            try:
                idx = header.index(column)
            except ValueError:
                idx = 0
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) <= idx:
                    bad += 1
                    continue
                ts = parse_ts(parts[idx])
                if ts is None:
                    bad += 1
                    continue
                rows += 1
                first = ts if first is None else min(first, ts)
                last = ts if last is None else max(last, ts)
    except OSError:
        return 0, None, None, bad
    return rows, first, last, bad


def gate_oi(root: Path) -> GateResult:
    path = root / "data" / "oi_snapshots.csv"
    res = GateResult(
        gate_id="G6", title="OI phase-C coverage (oi_snapshots.csv)",
        source="KNOWLEDGE.md §4 (report h)",
        bar=f"~{OI_ROWS_BAR} rows / {OI_DAYS_BAR:.0f} days of own snapshots",
        status=INSUFFICIENT, need=OI_ROWS_BAR)
    if not path.exists():
        res.statistic = "file missing"
        res.notes.append(f"{path} not found — scripts/record_oi.py has not run here.")
        return res
    rows, first, last, bad = _csv_first_last_ts(path)
    span_days = (last - first) / 86400 if (first and last) else 0.0
    res.n = rows
    res.values = {"rows": rows, "span_days": span_days, "first": first, "last": last}
    res.statistic = f"{rows} rows, {span_days:.1f} d span"
    res.detail = [f"{iso(first)} .. {iso(last)} ({span_days:.2f} days, "
                  f"{rows} rows; 15-min cadence gives ~96/day)"]
    res.status = (READY if (rows >= OI_ROWS_BAR or span_days >= OI_DAYS_BAR)
                  else INSUFFICIENT)
    res.notes.append("Coverage only: the phase-C hypothesis test (OI surge / "
                     "OI-up-and-quiet / L-S extremes) is a separate "
                     "pre-registered study, not this harness.")
    if bad:
        res.notes.append(f"{bad} malformed row(s) skipped.")
    return res


# ---- gate 7: board data ----------------------------------------------------
_WS_STAMP = re.compile(r"(\d{8})_(\d{6})")


def _ws_file_start(path: Path) -> float | None:
    m = _WS_STAMP.search(path.name)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc).timestamp()


def gate_board(root: Path) -> GateResult:
    ws_dir = root / "data" / "ws"
    res = GateResult(
        gate_id="G7", title="Board-data readiness (data/ws)",
        source="KNOWLEDGE.md §4 (reports f, g)",
        bar=f">= {BOARD_DAYS_BAR:.0f} days recorded (1-2 weeks, ~0.5-1 GB)",
        status=INSUFFICIENT, need=int(BOARD_DAYS_BAR))
    files = sorted(ws_dir.glob("*.jsonl.gz")) if ws_dir.is_dir() else []
    if not files:
        res.statistic = "no recordings"
        res.notes.append(f"{ws_dir} is empty or missing — "
                         "scripts/record_realtime.py has not run here.")
        return res
    total = 0
    starts: list[float] = []
    ends: list[float] = []
    for f in files:
        try:
            st = f.stat()
        except OSError:
            continue
        total += st.st_size
        ends.append(st.st_mtime)
        starts.append(_ws_file_start(f) or st.st_mtime)
    if not starts:
        res.statistic = "unreadable"
        return res
    span_days = (max(ends) - min(starts)) / 86400
    res.n = int(span_days)
    res.values = {"files": len(files), "bytes": total, "span_days": span_days}
    res.statistic = f"{total / 1e9:.2f} GB, {span_days:.1f} d span"
    res.detail = [f"{len(files)} file(s), {total / 1e6:.1f} MB, "
                  f"{iso(min(starts))} .. {iso(max(ends))}",
                  "gaps are NOT measured here: span is first-file start to "
                  "last-file mtime, an upper bound on real coverage"]
    res.status = (READY if (span_days >= BOARD_DAYS_BAR
                            and total >= BOARD_BYTES_BAR) else INSUFFICIENT)
    res.notes.append("Coverage only: the spread-MM / imbalance-filter test "
                     "(power analysis in reports f, g) is a separate study.")
    return res


# ---- gate 8: funding window ------------------------------------------------
def _candle_days_covering(path: Path, hour: int, minutes: int) -> tuple[set[str], int]:
    """UTC days whose 1-minute candles cover [hour:00, hour:00+minutes]."""
    have_start: set[str] = set()
    have_end: set[str] = set()
    bad = 0
    end_h, end_m = divmod(hour * 60 + minutes, 60)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            header = f.readline().strip().split(",")
            idx = header.index("ts") if "ts" in header else 0
            for line in f:
                parts = line.split(",")
                if len(parts) <= idx:
                    bad += 1
                    continue
                ts = parse_ts(parts[idx])
                if ts is None:
                    bad += 1
                    continue
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                if dt.hour == hour and dt.minute == 0:
                    have_start.add(dt.strftime("%Y-%m-%d"))
                elif dt.hour == end_h and dt.minute == end_m % 60:
                    have_end.add(dt.strftime("%Y-%m-%d"))
    except OSError:
        return set(), bad
    return have_start & have_end, bad


def gate_funding(root: Path) -> GateResult:
    res = GateResult(
        gate_id="G8", title="Funding-window sample (13:00 UTC)",
        source="KNOWLEDGE.md §4 (report f: n=21, -8.2 bps, t~1.8)",
        bar=f">= {FUNDING_N_BAR} settlement days (3x the original "
            f"n={FUNDING_ORIGINAL_N})",
        status=INSUFFICIENT, need=FUNDING_N_BAR)
    snapshots = root / "backtest_data"
    sources = (sorted(snapshots.glob("candles_FX_BTC_JPY*.csv"))
               if snapshots.is_dir() else [])
    live = root / "data" / "candles_FX_BTC_JPY.csv"
    if live.exists():
        sources.append(live)
    if not sources:
        res.statistic = "no candle files"
        res.notes.append("no candles_FX_BTC_JPY*.csv in backtest_data/ or data/.")
        return res
    days: set[str] = set()
    per_source = []
    bad_total = 0
    for path in sources:
        found, bad = _candle_days_covering(path, FUNDING_HOUR_UTC, FUNDING_WINDOW_MIN)
        bad_total += bad
        per_source.append(f"{path.relative_to(root)}: {len(found)} day(s)")
        days |= found
    res.n = len(days)
    res.values = {"days": len(days), "sources": len(sources)}
    res.statistic = f"{len(days)} usable settlement days"
    res.detail = per_source + [
        f"union across sources: {len(days)} distinct UTC days with candles at "
        f"{FUNDING_HOUR_UTC:02d}:00 AND {FUNDING_HOUR_UTC:02d}:"
        f"{FUNDING_WINDOW_MIN:02d}"]
    res.status = READY if len(days) >= FUNDING_N_BAR else INSUFFICIENT
    res.notes.append("Coverage only. bitFlyer public history expires after 31 "
                     "days (§6), so reaching 3x n needs backtest_data/ "
                     "snapshots taken over time, not one long fetch.")
    if bad_total:
        res.notes.append(f"{bad_total} malformed candle row(s) skipped.")
    return res


# ---- driver ----------------------------------------------------------------
def judge_all(root: str | Path = ".", *, since: float | None = None,
              equity: float | None = None, iters: int = 2000,
              seed: int = 20260821) -> list[GateResult]:
    """Every gate, judged over the files under ``root``. Never raises."""
    root = Path(root)
    config = load_yaml(root / "config" / "config.yaml")
    composite = load_yaml(root / "config" / "composite.yaml")
    equity0 = equity if equity is not None else _f(
        config.get("paper_equity_jpy")) or 200000.0
    params = ((composite.get("modules") or {}).get("radar_window") or {}
              ).get("params") or {}
    radar = StormRadar(start=str(params.get("window_start_utc", "12:30")),
                       end=str(params.get("window_end_utc", "15:00")))

    champion, champ_meta = load_champion_trades(root)
    scalp, scalp_meta = load_scalp_trades(root)

    results = [gate_main_bot(champion, champ_meta, equity0, since=since,
                             iters=iters, seed=seed),
               gate_scalper(scalp, scalp_meta, iters=iters, seed=seed),
               gate_armed_split(scalp, scalp_meta, iters=iters, seed=seed)]
    results.extend(gates_subsets(champion, champ_meta, equity0, since=since,
                                 radar=radar, iters=iters, seed=seed,
                                 composite=composite))
    results.append(gate_vol_tilt(scalp, scalp_meta, iters=iters, seed=seed))
    results.append(gate_oi(root))
    results.append(gate_board(root))
    results.append(gate_funding(root))
    return results


def render(results: Sequence[GateResult], *, root: Path,
           since: float | None) -> str:
    lines: list[str] = []
    lines.append("=" * 92)
    lines.append("PENDING-GATE JUDGMENT — docs/KNOWLEDGE.md §4 / §5")
    lines.append(f"root {root.resolve()}   generated {iso(datetime.now(timezone.utc).timestamp())}")
    lines.append("read-only; adopts nothing. PASS = the pre-registered numbers "
                 "are met, not that anything is enabled.")
    lines.append("=" * 92)
    lines.append(f"{'GATE':<5}{'WHAT':<40}{'n / need':>12}  {'STATUS':<13}STATISTIC")
    lines.append("-" * 92)
    for r in results:
        need = "-" if r.need is None else str(r.need)
        lines.append(f"{r.gate_id:<5}{r.title[:39]:<40}{f'{r.n} / {need}':>12}  "
                     f"{r.status:<13}{r.statistic}")
    lines.append("-" * 92)
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    lines.append("summary: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    lines.append("")
    for r in results:
        lines.append(f"[{r.gate_id}] {r.title} — {r.status}")
        lines.append(f"      bar     : {r.bar}")
        lines.append(f"      source  : {r.source}")
        lines.append(f"      sample  : n={r.n}" + (f" of {r.need}" if r.need else ""))
        for d in r.detail:
            lines.append(f"      | {d}")
        for note in r.notes:
            lines.append(f"      ! {note}")
        lines.append("")
    lines.append("Nothing above enables anything. Module gates in "
                 "config/composite.yaml need a written docs/ report and owner")
    lines.append("approval; a FAIL is a rejection report, never a reason to "
                 "move a bar (KNOWLEDGE.md §5).")
    if since is not None:
        lines.append(f"Champion trades counted from --since {iso(since)}.")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Judge every pending gate against "
                                             "the accumulated paper logs.")
    ap.add_argument("--root", default=".", help="repo root holding logs/ and data/")
    ap.add_argument("--since", default=None,
                    help="UTC ISO-8601 epoch for CHAMPION trades (G1/G4). Pass "
                         "the strategy-switch time after changing "
                         "config/config.yaml strategy.name (KNOWLEDGE.md §5).")
    ap.add_argument("--equity", type=float, default=None,
                    help="paper equity base for drawdown (default: "
                         "config/config.yaml paper_equity_jpy)")
    ap.add_argument("--bootstrap", type=int, default=2000,
                    help="bootstrap iterations for the day-clustered CI")
    ap.add_argument("--seed", type=int, default=20260821, help="bootstrap seed")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    since = None
    if args.since:
        since = parse_ts(args.since)
        if since is None:
            print(f"--since: cannot parse {args.since!r} as UTC ISO-8601",
                  file=sys.stderr)
            return 2
    root = Path(args.root)
    results = judge_all(root, since=since, equity=args.equity,
                        iters=args.bootstrap, seed=args.seed)
    if args.json:
        print(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
                          "root": str(root.resolve()),
                          "since": since,
                          "gates": [r.as_dict() for r in results]},
                         ensure_ascii=False, indent=2))
    else:
        print(render(results, root=root, since=since))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
