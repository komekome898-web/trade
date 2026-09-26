"""The integrated run (item 4, old item 13: 「§1 の実データ ... を新エンジンに通し、実行記録・
指標の書き出し・ダッシュボードまで」): data by their declarations -> the data
layer (bot.bt.data) -> one core engine per instrument (bot.bt.core) with the
execution models of item 2 in its sockets -> the run record, the metric
exports (bot.bt.report) and the run directory the dashboard reads
(bot.monitoring.backtest_view), in ONE call.

    plan = plan_pipeline(root=, datasets=, instruments=, strategy=, fill=, latency=, costs=, account=,
                         purpose=, prereg=None, repo=None)
    result = run_pipeline(plan, runs_dir=)     # executes twice, compares, keeps one
    result = execute_once(plan, out_dir)       # one execution (the two-run check uses it)

Every asset goes through the same code: a dataset is declared (bot.bt.data.spec:
trades, quotes, books, bars, funding ...) and an instrument names the dataset
its strategy is driven by (`price`) and the datasets that ride along (`with`).
Every market event of an instrument reaches its venue model. No reader or
path per market.

Declarations (every key required unless marked optional; nothing has a default):

  datasets     a file dataset: {"name", "paths", "spec", "origin": "real",
                 "resolve" (optional: the anomaly policies of bot.bt.data),
                 "range_ns" (optional: [lo, hi) -- the rows kept, bot.bt.data.load)}
               a generated (synthetic) dataset: {"name", "generator": {"name":
                 "random_walk", "seed": int, "params": {...}}} (GENERATORS). Synthetic
                 data is made ONLY here, from a seed; the generator's name,
                 version and seed go into the run record (finishing delegation
                 i4-r2-03). A file dataset cannot be declared "synthetic".
  instruments  [{"name", "price": dataset name, "with": [dataset names],
                 "product": {symbol, venue, tick, min_qty, qty_step, quote_ccy, margin}
                            (bot.bt.orders.Product),
                 "rules": {policy: value} (bot.bt.orders.VenueRules, string policies:
                            off_tick, below_min_qty, off_step, post_only, market_remainder,
                            self_trade, amend_qty_down, amend_price, market_ref, ...)}]
  strategy     {"kind": "schedule", "orders": [{"t_ns", "side", "qty"[, "instrument"]}]}
                 -- time only: an order without "instrument" goes to every
                    instrument, one with it to that instrument only
               {"kind": "seeded_random", "seed": int, "times": [t_ns, ...] (even), "qty"}
                 -- round trip k opens at times[2k] with a side drawn by
                    random.Random(seed) and closes at times[2k+1]
               {"kind": "price_rule", "buy_below", "sell_above", "qty"}
                 -- conditioned on prices: refused with real data under the
                    purpose 動作確認 (委任文 §4)
               Every order is a market order sent to the venue model.
  fill         {"optimistic": {FillSpec fields}, "pessimistic": {FillSpec fields}}
               (bot.bt.fill.FillRange: both sides required; tier 6's "impact" is a
               mapping of ImpactSpec fields; the L3 stances need a per-order feed,
               which is not declarable here). The run executes
               BOTH sides (item 2: 「楽観側と悲観側の両方を必ず回して幅で出す」) and
               records and exports both; there is no one-side entry.
  latency      {"feed", "order", "cancel", "notice"}: each a distribution
               {"kind": "constant", "ns"} | {"kind": "empirical", "samples_ns", "seed"}
               | {"kind": "seeded_uniform", "low_ns", "high_ns", "seed"}
               (bot.bt.latency). Each execution and each side builds fresh
               distributions from the declaration (the same seed, the same draws);
               the record carries the declaration and, per side, the draws and
               their sum per channel.
  costs        {"maker_rate", "taker_rate", "source"[, "spread", "funding": {"price": "event_mark"}]}
               (bot.bt.costs.CostSchedule: rates are fractions of the notional; spread
               is a price distance, the whole spread, half per side, for a market
               order with no book; funding charges FUNDING events riding along). A
               cost component the run meets and did not declare stops the run (swap
               and fee tables are not declarable here).
  account      {"currency", "cash", "leverage", "mark": "last_trade" | "mid",
                "liquidation": None | {"maint_ratio", "source"},
                "margin_check": "open_orders" | "position_only"}
               (bot.bt.portfolio.MarginAccount, one per instrument and side; the
               product's quote currency must be the account's currency: an FX
               table is not declarable here). The record carries each account's
               final state (position, realised, fees, equity, liquidation time).
  purpose      "動作確認" | "研究". A 研究 run needs its pre-registration FILE
               (`prereg`: a path under root; its sha256 is computed here and goes
               into the record, as bot.bt.repro.runner.plan_run does). A bare hash
               is not accepted (finishing delegation i4-r2-05). With any dataset of
               origin "real" and the purpose 動作確認, only the time-only
               strategies (schedule, seeded_random) are accepted.

Origin is decided from the ROWS (finishing delegation i4-r2-03): every file
dataset is real market data. Its rows, read through the data layer, are
compared with the rows of this environment's market-data files (MARKET_ROOTS,
the data layer's allowed roots under the repository) read through the data
layer with the SAME declaration: one row equal in time and values is the
evidence (`origin_evidence`: by "rows", the market file, rows matched / rows
read). A file dataset whose rows match no market file is still real (the
source is unknown: data from outside this environment, or every row edited);
its evidence says so (by "unmatched"). Only a generator makes synthetic data.
Limits of the evidence (never of the rule: a file is real either way): a
market file under a seal is compared only through the data layer, which
refuses its sealed rows (recorded as "sealed"); candidate files are narrowed
by their first and last data rows' times, so a market file whose rows are not
in time order may be missed as evidence; formats the data layer cannot read
(zip) are not compared.

The run id is the sha256 of the identity (declarations, data sha256, code
state, version, purpose, prereg hash); no clock enters it. The run directory
holds record.json, repro.json and the exports metrics / trades / fills /
orders / data_quality, each carrying the purpose (bot.bt.report.exports), in
the form bot.monitoring.backtest_view reads (its 10 tabs; under the purpose
動作確認 every tab carries 「動作確認の実行。相場の結論には使わない」). The exports'
headline numbers are those of the PESSIMISTIC side; metrics["range"] carries
both sides and every fill / trade / order row names its side.
"""
from __future__ import annotations

import fnmatch
import gzip
import hashlib
import inspect
import json
import os
import random
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from .core import Ack, BarEvent, BookSnapshotEvent, Canceled, ClockEvent, CoreEngine, Event, OrderFillEvent, \
    OrderRequest, Reject, Strategy, StrategyContext, TradeEvent
from .costs import CostSchedule, ScheduleCostModel
from .costs.schedule import FundingRule
from .data import DataError, load, parse_spec
from .data.allowlist import DEFAULT_ROOTS as _DATA_ROOTS
from .data.allowlist import MANDATORY_DENY as _NOT_MARKET
from .data.allowlist import SealRegistry
from .fill import FillRange, FillSpec, ImpactSpec, SimVenue
from .latency import Constant, Empirical, LatencyModel, SeededUniform
from .orders import FaultPlan, Product, VenueRules
from .orders.errors import ExecutionModelError
from .portfolio.account import LiquidationRule, MarginAccount
from .report import exports as X
from .report import metrics as M
from .report.trades import round_trips
from .repro.code_state import REPO, code_state, version

DEFAULT_RUNS_DIR = os.path.join(REPO, "backtest_runs")
ORIGINS = ("real",)  # a file dataset's only origin; synthetic data comes from GENERATORS
# this environment's market-data folders: the data layer's allowed roots under the repository (not the caller's root)
MARKET_ROOTS = tuple(os.path.join(REPO, r) for r in _DATA_ROOTS)
TIME_ONLY = ("schedule", "seeded_random")
STRATEGY_KINDS = TIME_ONLY + ("price_rule",)
SIDES = ("optimistic", "pessimistic")
LATENCY_CHANNELS = ("feed", "order", "cancel", "notice")
ACCOUNT_KEYS = ("currency", "cash", "leverage", "mark", "liquidation", "margin_check")
PRODUCT_KEYS = ("symbol", "venue", "tick", "min_qty", "qty_step", "quote_ccy", "margin")
QUANTILE_PROBS = (0.05, 0.25, 0.5, 0.75, 0.95)
MARKOUT_HORIZONS_S = (60, 300)
PIPELINE_VERSION = "bt-item4-pipeline-r3"
GENERATOR_VERSION = "random_walk-1"
_DAY_NS = 86_400 * 1_000_000_000
_PRICE_EVENT = {"trade": TradeEvent, "quote": BookSnapshotEvent, "book": BookSnapshotEvent, "bar": BarEvent}


class PipelineError(ValueError):
    """The integrated run refuses a declaration or cannot run it."""


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise PipelineError(msg)


def _canon(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PipelineError(f"not plain finite JSON: {exc}") from None


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _num(v: Any, what: str) -> float:
    _need(type(v) in (int, float) and v == v and v not in (float("inf"), float("-inf")), f"{what} must be a finite number")
    return float(v)


# --------------------------------------------------------------------------- synthetic data: seeded generators only
def _gen_random_walk(seed: int, params: Mapping) -> tuple[str, list[dict], list[Event]]:
    """A seeded random walk: (kind, rows, events). params: kind (trade / bar / quote), start_ns, step_ns, n,
    price0, step_pct (the largest move per step, in %), qty; quote also spread_pct."""
    kind = params.get("kind")
    _need(kind in ("trade", "bar", "quote"), "generator random_walk: params.kind must be trade / bar / quote")
    keys = {"kind", "start_ns", "step_ns", "n", "price0", "step_pct", "qty"} | ({"spread_pct"} if kind == "quote" else set())
    _need(set(params) == keys, f"generator random_walk ({kind}): params must be exactly {sorted(keys)}")
    for k in ("start_ns", "step_ns", "n"):
        _need(type(params[k]) is int and params[k] > 0, f"generator random_walk: params.{k} must be an int > 0")
    p0, move, qty = _num(params["price0"], "price0"), _num(params["step_pct"], "step_pct"), _num(params["qty"], "qty")
    _need(p0 > 0 and 0 <= move < 50 and qty > 0, "generator random_walk: price0 > 0, 0 <= step_pct < 50, qty > 0")
    rng = random.Random(seed)
    t, px, rows, events = params["start_ns"], p0, [], []
    for _ in range(params["n"]):
        nxt = px * (1 + move / 100 * (2 * rng.random() - 1))
        if kind == "trade":
            side = rng.choice(("buy", "sell"))
            rows.append({"t_ns": t, "px": nxt, "qty": qty, "side": side})
            events.append(TradeEvent(received_time_ns=t, price=nxt, size=qty, side=side))
        elif kind == "bar":
            hi = max(px, nxt) * (1 + move / 200 * rng.random())
            lo = min(px, nxt) * (1 - move / 200 * rng.random())
            rows.append({"t_ns": t, "open": px, "high": hi, "low": lo, "close": nxt, "volume": qty})
            events.append(BarEvent(received_time_ns=t + params["step_ns"], start_time_ns=t, open=px, high=hi, low=lo,
                                   close=nxt, volume=qty))
        else:
            half = _num(params["spread_pct"], "spread_pct") / 200
            bid, ask = nxt * (1 - half), nxt * (1 + half)
            rows.append({"t_ns": t, "bid": bid, "ask": ask, "bid_qty": qty, "ask_qty": qty})
            events.append(BookSnapshotEvent(received_time_ns=t, bids=((bid, qty),), asks=((ask, qty),)))
        px, t = nxt, t + params["step_ns"]
    return kind, rows, events


GENERATORS = {"random_walk": _gen_random_walk}


def _generate(gen: Mapping) -> tuple[str, list[dict], list[Event]]:
    _need(isinstance(gen, Mapping) and set(gen) == {"name", "seed", "params"},
          "a generator is exactly {name, seed, params}")
    _need(gen["name"] in GENERATORS, f"generator must be one of {sorted(GENERATORS)}, got {gen['name']!r}")
    _need(type(gen["seed"]) is int, "generator.seed must be an int")
    _need(isinstance(gen["params"], Mapping), "generator.params must be a mapping")
    return GENERATORS[gen["name"]](gen["seed"], json.loads(_canon(dict(gen["params"]))))


# --------------------------------------------------------------------------- origin from the rows
_HEADER_CACHE: dict = {}  # (real, size, mtime_ns, spec) -> (fits, gzip?): the first line names every column used
_BOUNDS_CACHE: dict = {}  # (real, size, mtime_ns, spec) -> (t_min, t_max) of its first and last data rows, or None
_ROWS_CACHE: dict = {}  # (real, size, mtime_ns, spec, range) -> frozenset of row keys, or the refusal text


def _under(real: str, folder: str) -> bool:
    folder = os.path.realpath(folder)
    return real == folder or real.startswith(folder + os.sep)


def _named_not_market(real: str) -> bool:
    """A path the data layer names as not market data (its mandatory refusals: qa_* synthetic packets, o3c_*
    research intermediates, phase2_runs, phase2_sealed -- bot.bt.data.allowlist.MANDATORY_DENY)."""
    rel = os.path.relpath(real, os.path.realpath(REPO))
    return any(fnmatch.fnmatchcase(c.lower(), pat.lower()) for c in rel.split(os.sep) for pat, _ in _NOT_MARKET)


def _rec_time(rec: Mapping) -> int:
    """A normalised row's time: t_ns, or a bar's start_ns (bot.bt.data records)."""
    return rec["t_ns"] if "t_ns" in rec else rec["start_ns"]


def _row_key(rec: Mapping) -> str:
    return json.dumps(rec, sort_keys=True, separators=(",", ":"))


def _read_head_tail(path: str) -> Optional[tuple[bool, list[bytes]]]:
    """(gzip?, [first line, second line, last non-empty line]) of a file; None when unreadable."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        gz = raw[:2] == b"\x1f\x8b"
        if gz:
            raw = gzip.decompress(raw)
    except (OSError, EOFError, gzip.BadGzipFile, ValueError):
        return None
    lines = [ln for ln in raw.split(b"\n") if ln.strip()]
    if not lines:
        return None
    return gz, [lines[0], lines[1] if len(lines) > 1 else b"", lines[-1]]


def _first_line(path: str) -> Optional[tuple[bool, bytes]]:
    """(gzip?, the first line) of a file, reading only its start; None when unreadable."""
    try:
        with open(path, "rb") as fh:
            magic = fh.read(2)
            fh.seek(0)
            if magic == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=fh) as gz:
                    return True, gz.readline(1 << 16)
            return False, fh.readline(1 << 16)
    except (OSError, EOFError, gzip.BadGzipFile, ValueError):
        return None


_DATA_SUFFIXES = {"csv": (".csv", ".csv.gz", ".txt", ".txt.gz", ".tsv", ".tsv.gz", ".gz"),
                  "jsonl": (".jsonl", ".jsonl.gz", ".json", ".json.gz", ".ndjson", ".gz")}


def _market_candidates(spec: dict) -> list[tuple[str, str, bool, tuple]]:
    """Market files (real path, relative path, gzip?, cache key) whose first line fits the declaration: a CSV with
    a header names every column the declaration uses; a JSONL's first row has them as keys. The compression is
    read from the file (gzip magic), not from the declaration."""
    ps = parse_spec(spec)
    cols = ps.columns_used()
    skey = _canon({k: v for k, v in spec.items() if k != "compression"})
    suffixes = _DATA_SUFFIXES.get(ps.format, ())
    out = []
    for root in MARKET_ROOTS:
        root_real = os.path.realpath(root)
        if not os.path.isdir(root_real):
            continue
        for dirpath, dirnames, filenames in os.walk(root_real):
            dirnames.sort()
            for name in sorted(filenames):
                if not name.lower().endswith(suffixes):
                    continue
                cand = os.path.join(dirpath, name)
                try:
                    st = os.stat(cand)
                except OSError:
                    continue
                real = os.path.realpath(cand)
                key = (real, st.st_size, st.st_mtime_ns, skey)
                if key not in _HEADER_CACHE:
                    ok, gz = False, False
                    if os.path.isfile(real) and not _named_not_market(real):
                        fl = _first_line(real)
                        if fl is not None:
                            gz, line = fl
                            first = line.decode("utf-8", "replace").lstrip("\ufeff").strip()
                            if ps.format == "csv" and ps.header:
                                ok = set(cols) <= {c.strip() for c in first.split(ps.delimiter)}
                            elif ps.format == "jsonl":
                                try:
                                    ok = set(cols) <= set(json.loads(first))
                                except (ValueError, TypeError):
                                    ok = False
                    _HEADER_CACHE[key] = (ok, gz)
                ok, gz = _HEADER_CACHE[key]
                if ok:
                    out.append((real, os.path.relpath(real, os.path.realpath(REPO)), gz, key))
    return out


def _bounds(cands: list, spec: dict, seals: SealRegistry) -> None:
    """Fill _BOUNDS_CACHE for the candidates: the times of each file's first and last data rows, read through the
    data layer (one small file of those rows). A sealed file is not read here (None: compared only through the
    data layer's own read, which refuses sealed rows)."""
    ps = parse_spec(spec)
    todo = []
    for real, rel, gz, key in cands:
        if key in _BOUNDS_CACHE:
            continue
        try:
            with open(real, "rb") as fh:
                raw = fh.read()
        except OSError:
            _BOUNDS_CACHE[key] = None
            continue
        if seals.match(real, len(raw), _sha(raw)) is not None:
            _BOUNDS_CACHE[key] = "sealed"
            continue
        todo.append((real, key))
    if not todo:
        return
    header = ps.format == "csv" and ps.header
    small = {k: v for k, v in spec.items() if k != "compression"}
    small["compression"] = "none"
    with tempfile.TemporaryDirectory(prefix="bt_origin_") as tmp:
        os.makedirs(os.path.join(tmp, "data"))
        rels = []
        for n, (real, key) in enumerate(todo):
            _, lines = _read_head_tail(real)  # type: ignore[misc]
            body = [lines[0], lines[1], lines[2]] if header else [lines[0], lines[2]]
            rel = os.path.join("data", f"f{n}.txt")
            with open(os.path.join(tmp, rel), "wb") as fh:
                fh.write(b"\n".join(body) + b"\n")
            rels.append(rel)

        def one(idx: list[int]) -> None:
            try:
                got = load(tmp, [{"name": "x", "paths": [rels[k] for k in idx], "spec": small}])
            except DataError:
                if len(idx) == 1:
                    _BOUNDS_CACHE[todo[idx[0]][1]] = None
                    return
                for k in idx:  # one unreadable sample: read the others one by one
                    one([k])
                return
            ts: dict[str, list[int]] = {}
            for rec, (path, _line) in zip(got.records("x"), got.provenance("x")):
                ts.setdefault(path, []).append(_rec_time(rec))
            for k in idx:
                t = ts.get(rels[k])
                _BOUNDS_CACHE[todo[k][1]] = (min(t), max(t)) if t else None

        one(list(range(len(todo))))


def row_evidence(records: Sequence[Mapping], spec: dict) -> dict:
    """Evidence of real market data for rows read through the data layer with the declaration `spec`: the market
    file whose rows -- read through the data layer with the same declaration, kept in the rows' time span --
    contain the most of the rows (time and every value; at least one)."""
    rows = [_row_key(r) for r in records]
    base = {"by": "unmatched", "market_path": None, "rows_matched": 0, "rows_read": len(rows), "sealed_skipped": []}
    if not rows:
        return base
    ts = [_rec_time(r) for r in records]
    lo, hi = min(ts), max(ts)
    cands = _market_candidates(spec)
    seals = SealRegistry(REPO)
    _bounds(cands, spec, seals)
    for real, rel, gz, key in cands:
        b = _BOUNDS_CACHE.get(key)
        if b is None:
            continue
        if b != "sealed" and (b[1] < lo or b[0] > hi):
            continue
        rkey = key + (lo, hi)
        if rkey not in _ROWS_CACHE:
            sp = {**spec, "compression": "gzip" if gz else "none"}
            try:
                # a day's margin on both sides: the data layer's range of a bar may be read on another of its
                # times (start / end); rows outside the dataset's span cannot match it, so the margin adds no match
                got = load(REPO, [{"name": "m", "paths": [rel], "spec": sp,
                                   "range_ns": [lo - _DAY_NS, hi + _DAY_NS]}]).records("m")
                _ROWS_CACHE[rkey] = frozenset(_row_key(r) for r in got)
            except DataError as exc:
                _ROWS_CACHE[rkey] = f"{type(exc).__name__}"
        got = _ROWS_CACHE[rkey]
        if isinstance(got, str):
            if b == "sealed":
                base["sealed_skipped"].append(rel)
            continue
        n = sum(1 for r in rows if r in got)
        if n > base["rows_matched"]:  # the market file with the most rows equal (ties: the first in path order)
            base = {**base, "by": "rows", "market_path": rel, "rows_matched": n}
    return base


# --------------------------------------------------------------------------- declarations
def _check_strategy(st: Mapping) -> dict:
    _need(isinstance(st, Mapping) and st.get("kind") in STRATEGY_KINDS,
          f"strategy.kind must be one of {STRATEGY_KINDS}, got {st!r}")
    k = st["kind"]
    if k == "schedule":
        _need(set(st) == {"kind", "orders"}, "strategy schedule must be exactly {kind, orders}")
        legs = []
        for i, o in enumerate(st["orders"]):
            _need(isinstance(o, Mapping) and {"t_ns", "side", "qty"} <= set(o) <= {"t_ns", "side", "qty", "instrument"},
                  f"orders[{i}] must be {{t_ns, side, qty[, instrument]}}")
            _need(type(o["t_ns"]) is int, f"orders[{i}].t_ns must be an int (UTC ns)")
            _need(o["side"] in ("buy", "sell"), f"orders[{i}].side must be buy / sell")
            _need(_num(o["qty"], f"orders[{i}].qty") > 0, f"orders[{i}].qty must be > 0")
            _need(o.get("instrument") is None or type(o["instrument"]) is str, f"orders[{i}].instrument must be a name")
            legs.append({"t_ns": o["t_ns"], "side": o["side"], "qty": float(o["qty"]), "instrument": o.get("instrument")})
        _need(legs, "strategy.orders must not be empty")
        for name in {lg["instrument"] for lg in legs}:
            mine = [lg for lg in legs if lg["instrument"] in (name, None)]
            _need(all(mine[i]["t_ns"] < mine[i + 1]["t_ns"] for i in range(len(mine) - 1)),
                  "strategy.orders must be in strictly increasing time (per instrument)")
        return {"kind": k, "legs": legs}
    if k == "seeded_random":
        _need(set(st) == {"kind", "seed", "times", "qty"}, "strategy seeded_random must be exactly {kind, seed, times, qty}")
        _need(type(st["seed"]) is int, "strategy.seed must be an int")
        times = list(st["times"])
        _need(times and len(times) % 2 == 0 and all(type(t) is int for t in times), "strategy.times must be an even list of int ns")
        _need(all(times[i] < times[i + 1] for i in range(len(times) - 1)), "strategy.times must be increasing")
        qty = _num(st["qty"], "strategy.qty")
        _need(qty > 0, "strategy.qty must be > 0")
        rng = random.Random(st["seed"])
        legs = []
        for k2 in range(0, len(times), 2):
            side = rng.choice(("buy", "sell"))
            other = "sell" if side == "buy" else "buy"
            legs += [{"t_ns": times[k2], "side": side, "qty": qty}, {"t_ns": times[k2 + 1], "side": other, "qty": qty}]
        return {"kind": k, "legs": legs}
    _need(set(st) == {"kind", "buy_below", "sell_above", "qty"},
          "strategy price_rule must be exactly {kind, buy_below, sell_above, qty}")
    return {"kind": k, "buy_below": _num(st["buy_below"], "buy_below"), "sell_above": _num(st["sell_above"], "sell_above"),
            "qty": _num(st["qty"], "qty")}


def _delay(d: Any, where: str):
    _need(isinstance(d, Mapping) and d.get("kind") in ("constant", "empirical", "seeded_uniform"),
          f"latency.{where} must be {{kind: constant | empirical | seeded_uniform, ...}}")
    k = d["kind"]
    try:
        if k == "constant":
            _need(set(d) == {"kind", "ns"}, f"latency.{where} constant is exactly {{kind, ns}}")
            return Constant(d["ns"])
        if k == "empirical":
            _need(set(d) == {"kind", "samples_ns", "seed"}, f"latency.{where} empirical is exactly {{kind, samples_ns, seed}}")
            return Empirical(list(d["samples_ns"]), d["seed"])
        _need(set(d) == {"kind", "low_ns", "high_ns", "seed"},
              f"latency.{where} seeded_uniform is exactly {{kind, low_ns, high_ns, seed}}")
        return SeededUniform(d["low_ns"], d["high_ns"], d["seed"])
    except ExecutionModelError as exc:
        raise PipelineError(f"latency.{where}: {exc}") from None


def _latency_model(lat: Mapping) -> LatencyModel:
    """A fresh latency model from the declaration (fresh seeded generators: the same draws every time)."""
    return LatencyModel(**{ch: _delay(lat[ch], ch) for ch in LATENCY_CHANNELS})


def _check_latency(lat: Mapping) -> dict:
    _need(isinstance(lat, Mapping) and set(lat) == set(LATENCY_CHANNELS),
          f"latency must be exactly {list(LATENCY_CHANNELS)} (each a distribution; no default)")
    out = json.loads(_canon(dict(lat)))
    _latency_model(out)
    return out


def _fill_spec(d: Any, side: str) -> FillSpec:
    _need(isinstance(d, Mapping), f"fill.{side} must be a mapping of FillSpec fields")
    kw = dict(d)
    try:
        if kw.get("impact") is not None:
            _need(isinstance(kw["impact"], Mapping), f"fill.{side}.impact must be a mapping of ImpactSpec fields")
            kw["impact"] = ImpactSpec(**dict(kw["impact"]))
        return FillSpec(**kw)
    except TypeError as exc:
        raise PipelineError(f"fill.{side}: {exc}") from None
    except ExecutionModelError as exc:
        raise PipelineError(f"fill.{side}: {exc}") from None


def _check_fill(fill: Mapping) -> FillRange:
    _need(isinstance(fill, Mapping) and set(fill) == set(SIDES),
          f"fill must be exactly {list(SIDES)} (a range: both sides, item 2 「楽観側と悲観側の両方を必ず回して幅で出す」)")
    try:
        return FillRange(optimistic=_fill_spec(fill["optimistic"], "optimistic"),
                         pessimistic=_fill_spec(fill["pessimistic"], "pessimistic"))
    except ExecutionModelError as exc:
        raise PipelineError(f"fill: {exc}") from None


def _cost_schedule(c: Mapping) -> CostSchedule:
    kw = {k: c[k] for k in ("maker_rate", "taker_rate", "source")}
    if "spread" in c:
        kw["spread"] = c["spread"]
    try:
        if "funding" in c:
            _need(isinstance(c["funding"], Mapping) and set(c["funding"]) == {"price"},
                  "costs.funding must be {price} (bot.bt.costs.schedule.FundingRule)")
            kw["funding"] = FundingRule(c["funding"]["price"])
        return CostSchedule(**kw)
    except ExecutionModelError as exc:
        raise PipelineError(f"costs: {exc}") from None


def _check_costs(c: Mapping) -> dict:
    _need(isinstance(c, Mapping) and {"maker_rate", "taker_rate", "source"} <= set(c)
          <= {"maker_rate", "taker_rate", "source", "spread", "funding"},
          "costs must be {maker_rate, taker_rate, source[, spread, funding]} (bot.bt.costs.CostSchedule; no default)")
    out = json.loads(_canon(dict(c)))
    _cost_schedule(out)
    return {**out, "spread": out.get("spread"), "funding": out.get("funding"), "fee_table": None, "swap": None}


def _product(d: Any, where: str) -> Product:
    _need(isinstance(d, Mapping) and set(d) == set(PRODUCT_KEYS), f"{where}.product must be exactly {list(PRODUCT_KEYS)}")
    try:
        return Product(**{k: d[k] for k in PRODUCT_KEYS})
    except ExecutionModelError as exc:
        raise PipelineError(f"{where}.product: {exc}") from None


def _rules(d: Any, where: str) -> VenueRules:
    _need(isinstance(d, Mapping) and all(type(v) is str for v in d.values()),
          f"{where}.rules must be a mapping of string policies (bot.bt.orders.VenueRules)")
    try:
        return VenueRules(**dict(d))
    except TypeError as exc:
        raise PipelineError(f"{where}.rules: {exc}") from None
    except ExecutionModelError as exc:
        raise PipelineError(f"{where}.rules: {exc}") from None


def _check_account(acc: Mapping) -> dict:
    _need(isinstance(acc, Mapping) and set(acc) == set(ACCOUNT_KEYS), f"account must be exactly {list(ACCOUNT_KEYS)}")
    _need(acc["margin_check"] in ("open_orders", "position_only"), "account.margin_check must be open_orders / position_only")
    liq = acc["liquidation"]
    _need(liq is None or (isinstance(liq, Mapping) and set(liq) == {"maint_ratio", "source"}),
          "account.liquidation must be None or {maint_ratio, source}")
    return json.loads(_canon(dict(acc)))


@dataclass
class PipelinePlan:
    run_id: str
    identity: dict
    root: str
    datasets: list
    instruments: list
    strategy: dict
    fill: dict
    latency: dict
    costs: dict
    account: dict
    purpose: str
    prereg: Optional[str]


def plan_pipeline(*, root: str, datasets: Sequence[Mapping], instruments: Sequence[Mapping], strategy: Mapping,
                  fill: Mapping, costs: Mapping, purpose: Optional[str], latency: Optional[Mapping] = None,
                  account: Optional[Mapping] = None,
                  prereg: Optional[str] = None, prereg_sha256: Any = None, repo: Optional[str] = None) -> PipelinePlan:
    _need(purpose is not None, "purpose is required: 動作確認 or 研究")
    try:
        p = X.check_purpose(purpose)
    except ValueError as exc:
        raise PipelineError(str(exc)) from None
    _need(prereg_sha256 is None, "prereg_sha256 is not accepted: hand the pre-registration FILE (prereg=, a path "
                                 "under root); its sha256 is computed here (finishing delegation i4-r2-05)")
    _need(type(root) is str and os.path.isdir(root), f"root must be an existing directory, got {root!r}")
    pre_sha = None
    if prereg is not None:
        _need(type(prereg) is str and prereg != "", "prereg must be a path under root")
        try:
            with open(os.path.join(root, prereg), "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            raise PipelineError(f"pre-registration {prereg!r} cannot be read: {exc}") from None
        _need(raw.strip() != b"", f"pre-registration {prereg!r} is empty")
        pre_sha = _sha(raw)
    _need(not (p == X.RESEARCH and pre_sha is None),
          "a 研究 run needs its pre-registration file (prereg=): its sha256 goes into the record")
    ds = []
    names = set()
    for i, d in enumerate(datasets):
        _need(isinstance(d, Mapping) and type(d.get("name")) is str and d["name"] and d["name"] not in names,
              f"datasets[{i}].name must be a unique non-empty name")
        names.add(d["name"])
        if "generator" in d:
            _need(set(d) == {"name", "generator"}, f"datasets[{i}]: a generated dataset is exactly {{name, generator}}")
            kind, rows, _ = _generate(d["generator"])
            g = json.loads(_canon(dict(d["generator"])))
            ds.append({"name": d["name"], "generator": g, "kind": kind, "origin": "synthetic",
                       "origin_evidence": {"by": "generator", "generator": g["name"], "version": GENERATOR_VERSION,
                                           "seed": g["seed"]},
                       "rows_sha256": _sha(_canon(rows).encode()), "resolve": {}, "range_ns": None})
            continue
        _need({"name", "paths", "spec", "origin"} <= set(d) <= {"name", "paths", "spec", "origin", "resolve", "range_ns"},
              f"datasets[{i}] must be {{name, paths, spec, origin[, resolve, range_ns]}} or {{name, generator}}")
        _need(d["origin"] in ORIGINS,
              f"datasets[{i}].origin: a file dataset is real market data ({ORIGINS}); synthetic data is made only by a "
              f"seeded generator ({{name, generator}}), got {d['origin']!r}")
        rng = d.get("range_ns")
        _need(rng is None or (isinstance(rng, (list, tuple)) and len(rng) == 2 and all(type(x) is int for x in rng)
                              and rng[0] < rng[1]), f"datasets[{i}].range_ns must be [lo, hi) ints in ns")
        spec = json.loads(_canon(d["spec"]))
        ds.append({"name": d["name"], "paths": list(d["paths"]), "spec": spec, "kind": spec.get("kind"),
                   "origin": "real", "resolve": dict(d.get("resolve") or {}),
                   "range_ns": list(rng) if rng is not None else None})
    _need(ds, "datasets must not be empty")
    by_name = {d["name"]: d for d in ds}
    ins = []
    inames = set()
    for i, it in enumerate(instruments):
        _need(isinstance(it, Mapping) and set(it) == {"name", "price", "with", "product", "rules"},
              f"instruments[{i}] must be {{name, price, with, product, rules}}")
        _need(type(it["name"]) is str and it["name"] and it["name"] not in inames, f"instruments[{i}].name must be unique")
        inames.add(it["name"])
        _need(it["price"] in by_name, f"instruments[{i}].price names no dataset")
        kind = by_name[it["price"]]["kind"]
        _need(kind in _PRICE_EVENT, f"instruments[{i}]: a {kind!r} dataset cannot drive an instrument")
        w = list(it["with"])
        _need(all(x in by_name and x != it["price"] for x in w), f"instruments[{i}].with names an unknown dataset or the price one")
        for x in w:
            _need(_PRICE_EVENT.get(by_name[x]["kind"]) is not _PRICE_EVENT[kind],
                  f"instruments[{i}]: {x!r} has the same event type as the price dataset (its prices could not be told apart)")
        prod = _product(it["product"], f"instruments[{i}]")
        _rules(it["rules"], f"instruments[{i}]")
        ins.append({"name": it["name"], "price": it["price"], "with": w, "price_kind": kind,
                    "product": json.loads(_canon(dict(it["product"]))), "rules": dict(it["rules"])})
    _need(ins, "instruments must not be empty")
    _need(latency is not None, "latency is required (four delay distributions; no default)")
    _need(account is not None, "account is required (currency, cash, leverage, mark, liquidation, margin_check)")
    st = _check_strategy(strategy)
    for lg in st.get("legs", []):
        _need(lg.get("instrument") in (None, *inames), f"an order names the unknown instrument {lg.get('instrument')!r}")
    _check_fill(fill)
    lat = _check_latency(latency)
    cs = _check_costs(costs)
    acc = _check_account(account)
    for it in ins:
        _need(it["product"]["quote_ccy"] == acc["currency"],
              f"instrument {it['name']!r}: the product's quote currency {it['product']['quote_ccy']!r} is not the "
              f"account's currency (an FX table is not declarable in the integrated run)")
    hashes = {}
    file_ds = [d for d in ds if "paths" in d]
    for d in file_ds:
        for pth in d["paths"]:
            try:
                with open(os.path.join(root, pth), "rb") as fh:
                    hashes[pth] = _sha(fh.read())
            except OSError as exc:
                raise PipelineError(f"data {pth!r} cannot be read: {exc}") from None
    if file_ds:
        try:
            loaded = load(root, [{"name": d["name"], "paths": d["paths"], "spec": d["spec"],
                                  **({"range_ns": d["range_ns"]} if d["range_ns"] else {})} for d in file_ds])
        except DataError as exc:
            raise PipelineError(f"data: {type(exc).__name__}: {exc}") from None
        for d in file_ds:
            d["origin_evidence"] = row_evidence(loaded.records(d["name"]), d["spec"])
    for d in ds:
        if "generator" in d:
            hashes[f"generator:{d['name']}"] = d["rows_sha256"]
    real = any(d["origin"] == "real" for d in ds)
    _need(not (real and p == X.SMOKE and st["kind"] not in TIME_ONLY),
          f"a 動作確認 run on real data takes a time-only strategy {TIME_ONLY} (委任文 §4: no signal, no conditioning, "
          f"no optimisation); got {st['kind']!r}")
    code = code_state(repo)
    src = inspect.getsource(inspect.getmodule(plan_pipeline))
    identity = {
        "datasets": ds, "data_sha256": hashes, "instruments": ins, "strategy": json.loads(_canon(dict(strategy))),
        "fill": json.loads(_canon(dict(fill))), "latency": lat, "costs": cs, "account": acc, "purpose": p,
        "prereg_sha256": pre_sha, "git_sha": code["git_sha"], "diff_hash": code["diff_hash"],
        "code_scope": code["code_scope"], "version": f"{PIPELINE_VERSION}; {GENERATOR_VERSION}; {version()}",
        "setup": {"name": f"{__name__}:{st['kind']}", "source_sha256": _sha(src.encode())},
    }
    return PipelinePlan(_sha(_canon(identity).encode()), identity, root, ds, ins, st, identity["fill"], lat,
                        json.loads(_canon(dict(costs))), acc, p, prereg)


# --------------------------------------------------------------------------- the market-order rule of the run
BOOKLESS_TIERS = (1, 2)  # the fill tiers that price a market order from the last trade, not the displayed book


class ArrivalGate:
    """The fill-model socket of one instrument and one side: item 2's SimVenue behind the integrated run's rule for
    MARKET orders (the lead's rules I-1 .. I-5, finishing stage):

      I-1  a market order is priced at the FIRST observation of the instrument's price dataset at or after its
           arrival (a trade's price, a quote's book, a bar's open) -- not the last one before it;
      I-2  an order that arrives before the first observation fills at the first observation;
      I-3  an instrument priced from trades with a book riding along: the optimistic side's tier walks the book;
           a side whose tier is in BOOKLESS_TIERS (tier 1: price crosses) prices from the trade +- half the spread
           (the venue is not shown the book on that side);
      I-4  a bar instrument: the open of the first bar that STARTS at or after the order's arrival (+- half the
           spread);
      I-5  an instrument with neither book nor spread: both sides give the I-1 value.

    How: the gate holds a market order until that first observation, then hands it to the SimVenue right after
    the venue has applied the observation (trades: the venue's market_ref last_trade = that trade; quotes / books:
    the book of that observation; bars: the venue is told the order arrived just before the bar's start, so its
    market_ref next_bar_open takes that bar). Every other request and every other event goes to the venue as it
    comes. The venue's own rules (reduce-only, sizes, sessions ...) apply unchanged."""

    def __init__(self, venue: SimVenue, price_type: type, hide_book: bool,
                 account: Optional[DeferredMarginAccount] = None) -> None:
        self.venue = venue
        self.account = account
        self.price_type = price_type
        self.hide_book = hide_book
        self.held: list[tuple[OrderRequest, int]] = []
        self.last_obs_t: Optional[int] = None

    def open_orders(self):
        return self.venue.open_orders()

    def _release(self, order: OrderRequest, t: int, event: Optional[Event] = None) -> list:
        """Hand a held order to the venue. The gate acknowledged it at its arrival: the venue's Ack is dropped and a
        refusal by the venue's rules ends the order as Canceled with the venue's reason. A margin check the account
        deferred (I-2) is made now, after the account has seen the observation that prices the order."""
        if self.account is not None and order.client_order_id in self.account.deferred:
            if event is not None:
                self.account.observe(event, t)
            r = self.account.recheck(order, t)
            if r is not None:
                return [Canceled(order.client_order_id, f"refused_by_account: {r}")]
        out = []
        for rep in self.venue.on_order(order, t):
            if type(rep) is Ack:
                continue
            if type(rep) is Reject:
                out.append(Canceled(rep.client_order_id, f"rejected_by_venue: {rep.reason}"))
                continue
            out.append(rep)
        return out

    def on_market_event(self, event: Event, venue_time_ns: int):
        t = int(venue_time_ns)
        if self.hide_book and type(event) is BookSnapshotEvent:
            return ()
        if type(event) is BarEvent and self.price_type is BarEvent:
            out: list = []
            start = event.start_time_ns if event.start_time_ns is not None else t
            due = [(o, a) for o, a in self.held if start >= a]
            self.held = [(o, a) for o, a in self.held if start < a]
            for o, _ in due:
                out += self._release(o, start - 1, event)  # I-4: this bar starts after the order
            out += list(self.venue.on_market_event(event, t))
            return tuple(out)
        out = list(self.venue.on_market_event(event, t))
        if type(event) is self.price_type:
            if type(event) is BookSnapshotEvent and (not event.bids or not event.asks):
                return tuple(out)
            self.last_obs_t = t
            due = [(o, a) for o, a in self.held if t >= a]
            self.held = [(o, a) for o, a in self.held if t < a]
            for o, _ in due:
                out += self._release(o, t, event)
        return tuple(out)

    def on_order(self, order: OrderRequest, venue_time_ns: int):
        t = int(venue_time_ns)
        if order.order_type != "market":
            return self.venue.on_order(order, t)
        if self.price_type is not BarEvent and self.last_obs_t is not None and self.last_obs_t >= t:
            return self.venue.on_order(order, t)  # an observation at the arrival instant is "at or after" (I-1)
        self.held.append((order, t))
        return (Ack(order.client_order_id, f"gate-{order.client_order_id}"),)  # acknowledged now, priced later

    def on_cancel(self, request, venue_time_ns: int):
        coid = request.client_order_id
        if any(o.client_order_id == coid for o, _ in self.held):
            self.held = [(o, a) for o, a in self.held if o.client_order_id != coid]
            return (Canceled(coid, "canceled"),)
        return self.venue.on_cancel(request, venue_time_ns)


DEFERRABLE = ("no_price_for_margin_check", "no_mark_for_equity")


class DeferredMarginAccount:
    """The account socket: item 2's MarginAccount, with ONE change of timing for the lead's rule I-2 (answer (甲)):
    a market order the account cannot price at its arrival (no observation yet: DEFERRABLE refusals) is not refused
    there; its margin check is made when the ArrivalGate prices it, right after the account has seen that first
    observation, and a refusal then ends the order as Canceled with the account's reason. Every other check,
    every fill, every event goes to the MarginAccount unchanged. So that the check at pricing time sees the
    observation, the gate shows it to the account first (`observe`); the core's own delivery of the same event to
    this socket then returns what the account answered (each event reaches the MarginAccount once)."""

    def __init__(self, inner: MarginAccount) -> None:
        self.inner = inner
        self.deferred: set[str] = set()
        self._seen: Optional[tuple[int, int, tuple]] = None  # (id of the event, time, the account's answer)

    def check_order(self, order: OrderRequest, venue_time_ns: int):
        r = self.inner.check_order(order, venue_time_ns)
        if r in DEFERRABLE and order.order_type == "market":
            self.deferred.add(order.client_order_id)
            return None
        return r

    def observe(self, event: Event, venue_time_ns: int) -> None:
        if self._seen is None or self._seen[0] != id(event) or self._seen[1] != venue_time_ns:
            self._seen = (id(event), venue_time_ns, tuple(self.inner.on_market_event(event, venue_time_ns)))

    def recheck(self, order: OrderRequest, venue_time_ns: int):
        """The deferred margin check, at pricing time (None when the order was not deferred)."""
        if order.client_order_id not in self.deferred:
            return None
        self.deferred.discard(order.client_order_id)
        return self.inner.check_order(order, venue_time_ns)

    def on_market_event(self, event: Event, venue_time_ns: int):
        if self._seen is not None and self._seen[0] == id(event) and self._seen[1] == venue_time_ns:
            out, self._seen = self._seen[2], None
            return out
        self._seen = None
        return self.inner.on_market_event(event, venue_time_ns)

    def apply_fill(self, fill) -> None:
        self.inner.apply_fill(fill)

    def apply_funding(self, event) -> None:
        self.inner.apply_funding(event)

    def apply_liquidation(self, event) -> None:
        self.inner.apply_liquidation(event)

    def finish(self, end_ns: int):
        return self.inner.finish(end_ns)


# --------------------------------------------------------------------------- the strategies
class ScheduleStrategy(Strategy):
    """Time-only: one timer per leg, a market order when it fires."""

    def __init__(self, legs: Sequence[dict]) -> None:
        self.legs = list(legs)
        self.armed = False

    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        if not self.armed:
            self.armed = True
            for i, lg in enumerate(self.legs):
                _need(lg["t_ns"] >= ctx.now_ns, f"leg {i} at {lg['t_ns']} is before the run starts ({ctx.now_ns})")
                ctx.set_timer(lg["t_ns"], f"leg{i}")
        if type(event) is ClockEvent and event.tag.startswith("leg"):
            i = int(event.tag[3:])
            ctx.place_order(OrderRequest(side=self.legs[i]["side"], order_type="market", size=self.legs[i]["qty"],
                                         client_order_id=f"leg{i}"))


class PriceRuleStrategy(Strategy):
    """Conditioned on prices (accepted only for synthetic data or a 研究 run)."""

    def __init__(self, rule: dict, price_type: type) -> None:
        self.r = rule
        self.t = price_type
        self.pos = 0.0
        self.busy = False
        self.n = 0

    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        if type(event) is OrderFillEvent:
            self.pos += event.size if event.side == "buy" else -event.size
            self.busy = False
            return
        if type(event) is not self.t or self.busy:
            return
        if type(event) is BookSnapshotEvent and (not event.asks or not event.bids):
            return
        px = event.close if type(event) is BarEvent else event.price if type(event) is TradeEvent else \
            (event.asks[0][0] + event.bids[0][0]) / 2
        side = "buy" if self.pos == 0 and px < self.r["buy_below"] else \
            "sell" if self.pos > 0 and px > self.r["sell_above"] else None
        if side:
            self.n += 1
            self.busy = True
            ctx.place_order(OrderRequest(side=side, order_type="market", size=self.r["qty"] if side == "buy" else self.pos,
                                         client_order_id=f"rule{self.n}"))


# --------------------------------------------------------------------------- one execution
@dataclass
class InstrumentResult:
    name: str
    side: str
    fills: list
    trades: list
    orders: list
    events_read: dict
    engine: dict
    latency: dict
    account: dict


def _streams(plan: PipelinePlan, it: dict, loaded) -> dict:
    streams = {}
    by = {d["name"]: d for d in plan.datasets}
    try:
        for name in [it["price"]] + it["with"]:
            d = by[name]
            if "generator" in d:
                streams[name] = list(_generate(d["generator"])[2])
            else:
                streams[name] = list(loaded.events(name, d["resolve"] or None))
    except DataError as exc:
        raise PipelineError(f"data: {type(exc).__name__}: {exc}") from None
    return streams


def _run_instrument(plan: PipelinePlan, it: dict, loaded, side: str) -> InstrumentResult:
    price_type = _PRICE_EVENT[it["price_kind"]]
    streams = _streams(plan, it, loaded)
    times = [e.received_time_ns for s in streams.values() for e in s]
    starts = [e.start_time_ns if type(e) is BarEvent else e.exchange_time_ns for s in streams.values() for e in s]
    _need(times, f"instrument {it['name']!r} has no event")
    st = plan.strategy
    first = min(starts)
    if st["kind"] in TIME_ONLY:
        legs = [lg for lg in st["legs"] if lg.get("instrument") in (None, it["name"])]
        _need(legs, f"instrument {it['name']!r} has no order in the schedule")
        first = min(first, legs[0]["t_ns"])
        strat: Strategy = ScheduleStrategy(legs)
        reasons = {f"leg{i}": "fixed_schedule" for i in range(len(legs))}
    else:
        strat = PriceRuleStrategy(st, price_type)
        reasons = None
    streams["~clock"] = [ClockEvent(received_time_ns=first)]
    product = Product(**{k: it["product"][k] for k in PRODUCT_KEYS})
    costs = _cost_schedule(plan.costs)
    frange = _check_fill(plan.fill)
    spec = getattr(frange, side)
    venue = SimVenue(product=product, rules=VenueRules(**it["rules"]), fill=spec, costs=costs,
                     faults=FaultPlan(()), l3=None)
    acc = plan.account
    liq = LiquidationRule(acc["liquidation"]["maint_ratio"], acc["liquidation"]["source"]) if acc["liquidation"] else None
    account = DeferredMarginAccount(MarginAccount(
        product=product, currency=acc["currency"], cash=acc["cash"], leverage=acc["leverage"], liquidation=liq,
        mark=acc["mark"], costs=costs, fx=None, reference=None,
        open_orders=venue.open_orders if acc["margin_check"] == "open_orders" else None))
    gate = ArrivalGate(venue, price_type, hide_book=price_type is TradeEvent and spec.tier in BOOKLESS_TIERS,
                       account=account)
    latency = _latency_model(plan.latency)
    end = max(times)
    try:
        res = CoreEngine(strat, streams, gate, latency,
                         ScheduleCostModel(costs, product=product, account_currency=acc["currency"], fx=None), account,
                         time_span_ns=(first, end)).run()
    except ExecutionModelError as exc:
        raise PipelineError(f"instrument {it['name']!r} ({side}): {type(exc).__name__}: {exc}") from None
    snap = account.finish(end)
    sides = {o.client_order_id: o.request.side for o in res.orders.values()}
    fills = [{"order_id": f.client_order_id, "t_ns": f.venue_time_ns, "venue_t_ns": f.venue_time_ns,
              "side": f.side or sides[f.client_order_id], "px": f.price, "qty": f.size, "fee": f.fee,
              "liquidity": f.liquidity, "instrument": it["name"], "range": side} for f in res.fills]
    orders = [{"id": o.client_order_id, "t_ns": o.sent_time_ns, "side": o.request.side, "type": o.request.order_type,
               "qty": o.request.size, "state": o.state.value if hasattr(o.state, "value") else str(o.state),
               "filled": o.filled_size, "instrument": it["name"], "range": side} for o in res.orders.values()]
    if reasons is None:
        reasons = {f["order_id"]: "rule" for f in fills}
    trades = [dict(t, instrument=it["name"], range=side) for t in round_trips(fills, reasons)]
    read = {k: v for k, v in res.source_events_by_stream.items() if k != "~clock"}
    account_state = {"currency": snap.currency, "position": snap.position, "avg_px": snap.avg_px,
                     "realized": snap.realized, "unrealized": snap.unrealized, "fees": snap.fees,
                     "funding_paid": snap.funding_paid, "swap_paid": snap.swap_paid, "equity": snap.equity,
                     "exposure_ns": snap.exposure_ns, "liquidated_t": snap.liquidated_t,
                     "cash": acc["cash"], "leverage": acc["leverage"], "mark": acc["mark"],
                     "liquidation": acc["liquidation"], "margin_check": acc["margin_check"]}
    return InstrumentResult(it["name"], side, fills, trades, orders, read,
                            {"events_processed": res.events_processed, "source_events": res.source_events,
                             "delivery_digest": res.delivery_digest, "first_time_ns": res.first_time_ns,
                             "last_time_ns": res.last_time_ns, "models": dict(res.models),
                             "defaults_used": list(res.defaults_used), "fill_tier": venue.tier,
                             "fill_venue": type(venue).__qualname__, "book_shown_to_venue": not gate.hide_book,
                             "venue_used": dict(venue.used)},
                            {"draws": dict(latency.draws), "total_ns": dict(latency.total_ns)}, account_state)


def _summary(per: Mapping[str, InstrumentResult]) -> dict:
    out = {}
    for name, r in per.items():
        out[name] = {"num_trades": len(r.trades), "realized_pnl": sum(t["pnl"] for t in r.trades),
                     "num_fills": len(r.fills), "filled_qty": sum(f["qty"] for f in r.fills),
                     "fees": sum(f["fee"] for f in r.fills), "account": r.account}
    return out


def execute_once(plan: PipelinePlan, out_dir: str) -> dict:
    """One execution of the plan (both sides of the fill range), writing every output file into out_dir.
    Returns {"instruments": {name: InstrumentResult (pessimistic)}, "range": {side: {name: InstrumentResult}},
    "events_read": {dataset: n}}."""
    file_ds = [d for d in plan.datasets if "paths" in d]
    loaded = None
    if file_ds:
        specs = [{"name": d["name"], "paths": d["paths"], "spec": d["spec"],
                  **({"range_ns": list(d["range_ns"])} if d["range_ns"] else {})} for d in file_ds]
        try:
            loaded = load(plan.root, specs)
        except DataError as exc:
            raise PipelineError(f"data: {type(exc).__name__}: {exc}") from None
        _need(loaded.hashes() == {k: v for k, v in plan.identity["data_sha256"].items() if not k.startswith("generator:")},
              "data changed between planning and execution")
    both = {side: {it["name"]: _run_instrument(plan, it, loaded, side) for it in plan.instruments} for side in SIDES}
    per = both["pessimistic"]
    rid = plan.run_id
    fills = [f for side in SIDES for r in both[side].values() for f in r.fills]
    trades = [t for side in SIDES for r in both[side].values() for t in r.trades]
    orders = [o for side in SIDES for r in both[side].values() for o in r.orders]
    p_fills = [f for r in per.values() for f in r.fills]
    p_trades = [t for r in per.values() for t in r.trades]
    p_orders = [o for r in per.values() for o in r.orders]
    read: dict[str, int] = {}
    for r in per.values():
        for k, v in r.events_read.items():
            read[k] = read.get(k, 0) + v
    dist = M.trade_distribution(p_trades, QUANTILE_PROBS) if p_trades else {"n": 0, "per_trade_bp": []}
    eq, eq_t, cum = [0.0], [min(f["t_ns"] for f in p_fills) if p_fills else 0], 0.0
    for t in sorted(p_trades, key=lambda x: (x["exit_t_ns"], x["id"])):
        cum += t["pnl"]
        eq.append(cum)
        eq_t.append(t["exit_t_ns"])
    fees = {"maker": 0.0, "taker": 0.0}
    for f in p_fills:
        fees[f["liquidity"]] = fees.get(f["liquidity"], 0.0) + f["fee"]
    by_inst = {}
    for name, r in per.items():
        d = M.trade_distribution(r.trades, QUANTILE_PROBS) if r.trades else {"n": 0, "per_trade_bp": []}
        by_inst[name] = {"num_trades": len(r.trades), "realized_pnl": sum(t["pnl"] for t in r.trades),
                         "gross_sell_minus_buy": sum((f["px"] if f["side"] == "sell" else -f["px"]) * f["qty"]
                                                     for f in r.fills),
                         "fees": sum(f["fee"] for f in r.fills), "trades": d}
    fm = M.fill_metrics([{"id": f"{o['instrument']}/{o['id']}", "qty": o["qty"]} for o in p_orders],
                        [{"order_id": f"{f['instrument']}/{f['order_id']}", "t_ns": f["t_ns"], "qty": f["qty"]}
                         for f in p_fills], max(f["venue_t_ns"] for f in p_fills) if p_fills else 0) if p_orders else None
    metrics = {
        "side_note": "見出しの数は悲観側(fill.pessimistic)。両側は range",
        "range": {side: _summary(both[side]) for side in SIDES},
        "trades": dist, "by_instrument": by_inst,
        "pnl_jpy": {"realized": cum, "fees": sum(fees.values()),
                    "note": "銘柄ごとの通貨の額を足している(銘柄ごとの値は by_instrument)"},
        "fills": fm,
        "markout": {"reference": "測っていない(統合の実行は銘柄ごとに価格の単位が違う)", "unit": None, "values": {}},
        "costs": {"maker_fee": fees.get("maker", 0.0), "taker_fee": fees.get("taker", 0.0), "spread": plan.costs.get("spread"),
                  "spread_note": "宣言の spread(板の無い成行の値に半分ずつ含む)", "funding": 0.0,
                  "funding_note": "資金調達の事象を読んでいない", "source": plan.costs["source"]},
        "exit_reasons": M.exit_reasons(p_trades) if p_trades else {},
        "drawdown": {**M.drawdown(eq, eq_t), "max_dd_pct": None, "pct_note": "率は出さない(銘柄ごとの通貨の額を足しているため)"},
        "equity": {"t_ns": eq_t, "realized_jpy": eq},
        "latency": {side: {n: r.latency for n, r in both[side].items()} for side in SIDES},
        "events_read": read,
    }
    quality = {"origin": {d["name"]: d["origin"] for d in plan.datasets},
               "origin_evidence": {d["name"]: d["origin_evidence"] for d in plan.datasets}}
    if loaded is not None:
        man = loaded.manifest()
        man.pop("root", None)
        man["files"] = [{k: v for k, v in f.items() if k != "real"} for f in man.get("files", [])]
        man["seal_records"] = {os.path.relpath(k, os.path.realpath(plan.root)): v
                               for k, v in man.get("seal_records", {}).items()}
        quality.update({"manifest": man, "anomalies": {n: loaded.anomalies(n) for n in loaded.names()},
                        "checks": {n: loaded.checks(n) for n in loaded.names()}})
    ident = plan.identity
    record = {
        "run_id": rid, "git_sha": ident["git_sha"], "diff_hash": ident["diff_hash"], "code_scope": ident["code_scope"],
        "config": {"instrument": ", ".join(i["name"] for i in plan.instruments), "instruments": plan.instruments,
                   "strategy": ident["strategy"], "fill": ident["fill"], "latency": ident["latency"],
                   "costs": ident["costs"], "account": ident["account"]},
        "data": ([{"path": pth, "dataset": d["name"], "spec": d["spec"], "origin": d["origin"],
                   "origin_evidence": d["origin_evidence"]} for d in plan.datasets if "paths" in d for pth in d["paths"]]
                 + [{"path": None, "dataset": d["name"], "generator": d["generator"], "origin": d["origin"],
                     "origin_evidence": d["origin_evidence"]} for d in plan.datasets if "generator" in d]),
        "data_sha256": ident["data_sha256"],
        "seed": plan.strategy.get("seed") if isinstance(plan.strategy, dict) else None,
        "generators": {d["name"]: {"name": d["generator"]["name"], "version": GENERATOR_VERSION,
                                   "seed": d["generator"]["seed"]} for d in plan.datasets if "generator" in d},
        "setup": ident["setup"], "version": ident["version"], "purpose": plan.purpose,
        "prereg_sha256": ident["prereg_sha256"], "prereg": plan.prereg,
        "components": {"models": {side: {n: r.engine["models"] for n, r in both[side].items()} for side in SIDES},
                       "defaults_used": {side: {n: r.engine["defaults_used"] for n, r in both[side].items()}
                                         for side in SIDES},
                       "fill_range": ident["fill"],
                       "latency": {"declared": ident["latency"],
                                   "drawn": {side: {n: r.latency for n, r in both[side].items()} for side in SIDES}},
                       "account": {side: {n: r.account for n, r in both[side].items()} for side in SIDES},
                       "notes": {}},
        "engine": {side: {n: {k: v for k, v in r.engine.items() if k not in ("models", "defaults_used")}
                          for n, r in both[side].items()} for side in SIDES},
    }
    with open(os.path.join(out_dir, "record.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(X.canonical_json(record) + "\n")
    for kind, payload in (("metrics", metrics), ("trades", trades), ("fills", fills), ("orders", orders),
                          ("data_quality", quality)):
        X.write_export(out_dir, kind, payload, purpose=plan.purpose, run_id=rid)
    return {"instruments": per, "range": both, "events_read": read}


# --------------------------------------------------------------------------- the run (two executions)
@dataclass
class PipelineResult:
    run_id: str
    run_dir: str
    record: dict
    exports: dict  # file name -> purpose
    repro: dict
    instruments: dict = field(default_factory=dict)  # name -> InstrumentResult (pessimistic side, kept execution)
    range: dict = field(default_factory=dict)  # side -> name -> InstrumentResult
    events_read: dict = field(default_factory=dict)


def _digests(d: str) -> dict:
    out = {}
    for name in sorted(os.listdir(d)):
        with open(os.path.join(d, name), "rb") as fh:
            out[name] = _sha(fh.read())
    return out


def run_pipeline(plan: PipelinePlan, *, runs_dir: str = DEFAULT_RUNS_DIR, runs: int = 2) -> PipelineResult:
    _need(type(runs) is int and runs >= 2, "a run is executed at least twice (the automatic reproducibility check)")
    os.makedirs(runs_dir, exist_ok=True)
    gi = os.path.join(runs_dir, ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w", encoding="utf-8") as fh:
            fh.write("# run outputs are not versioned (bot.bt.pipeline)\n*\n")
    dirs, digs, outs = [], [], []
    try:
        for k in range(runs):
            d = os.path.join(runs_dir, f".work-{plan.run_id[:16]}-{os.getpid()}-{k}")
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d)
            dirs.append(d)
            outs.append(execute_once(plan, d))
            digs.append(_digests(d))
    except BaseException:
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)
        raise
    differing = sorted({k for x in digs[1:] for k in set(x) | set(digs[0]) if x.get(k) != digs[0].get(k)})
    for d in dirs[1:]:
        shutil.rmtree(d, ignore_errors=True)
    if differing:
        shutil.rmtree(dirs[0], ignore_errors=True)
        raise PipelineError(f"{runs} executions of run {plan.run_id} differ in {differing}")
    final = os.path.join(runs_dir, plan.run_id)
    if os.path.isdir(final):
        old = {k: v for k, v in _digests(final).items() if k != "repro.json"}
        shutil.rmtree(dirs[0], ignore_errors=True)
        _need(old == digs[0], f"run {plan.run_id} already exists with different outputs: the identity missed a change")
    else:
        os.replace(dirs[0], final)
    repro = {"runs": runs, "identical": True, "sha256": digs[0]}
    with open(os.path.join(final, "repro.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(X.canonical_json(repro) + "\n")
    with open(os.path.join(final, "record.json"), "r", encoding="utf-8") as fh:
        record = json.load(fh)
    exports = {n: X.read_export(os.path.join(final, n))["purpose"] for n in sorted(os.listdir(final))
               if n not in ("record.json", "repro.json")}
    return PipelineResult(plan.run_id, final, record, exports, repro, outs[0]["instruments"], outs[0]["range"],
                          outs[0]["events_read"])
