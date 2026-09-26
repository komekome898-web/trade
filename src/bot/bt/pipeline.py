"""The integrated run (item 4, old item 13: 「§1 の実データ ... を新エンジンに通し、実行記録・
指標の書き出し・ダッシュボードまで」): data files by their declarations -> the data
layer (bot.bt.data) -> one core engine per instrument (bot.bt.core) -> the
run record, the metric exports (bot.bt.report) and the run directory the
dashboard reads (bot.monitoring.backtest_view), in ONE call.

    plan = plan_pipeline(root=, datasets=, instruments=, strategy=, fill=, costs=, purpose=,
                         prereg=None, prereg_sha256=None, repo=None)
    result = run_pipeline(plan, runs_dir=)     # executes twice, compares, keeps one
    result = execute_once(plan, out_dir)       # one execution (the two-run check uses it)

Every asset goes through the same code: a dataset is declared (bot.bt.data.spec:
trades, quotes, books, bars, funding ...) and an instrument names the dataset
its fills are priced from (`price`) and the datasets that ride along (`with`,
delivered to the strategy, never used for a price). No reader or path per
market.

Declarations (every key required; nothing has a default):

  datasets     [{"name", "paths", "spec", "origin": "real" | "synthetic",
                 "resolve" (optional: the anomaly policies of bot.bt.data),
                 "range_ns" (optional: [lo, hi) -- the rows kept, bot.bt.data.load)}]
  instruments  [{"name", "price": dataset name, "with": [dataset names]}]
  strategy     {"kind": "schedule", "orders": [{"t_ns", "side", "qty"[, "instrument"]}]}
                 -- time only: an order without "instrument" goes to every
                    instrument, one with it to that instrument only
               {"kind": "seeded_random", "seed": int, "times": [t_ns, ...] (even), "qty"}
                 -- round trip k opens at times[2k] with a side drawn by
                    random.Random(seed) and closes at times[2k+1]
               {"kind": "price_rule", "buy_below", "sell_above", "qty"}
                 -- conditioned on prices: refused with real data under the
                    purpose 動作確認 (委任文 §4)
  fill         {"price": "first_observed_at_or_after", "trade": "px",
                "quote": {"buy": "ask", "sell": "bid"}, "bar": "open",
                "latency_ns": int >= 0}
               a market order fills in full at the first price the instrument's
               price dataset shows at or after the order's arrival: a trade's
               price, a quote's ask (buy) / bid (sell), a bar's open (the first
               bar starting at or after the arrival; the bar is known at its
               close, so the fill is booked then). The fill's `t_ns` is the
               time of that observation (for a bar, its start).
  costs        {"taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct"
                [, "source"]}: a non-zero cost needs its `source`; spread_pct
               applies to trade / bar prices (half per side) and must be 0
               for a quote-priced instrument (the quote has its spread).
  purpose      "動作確認" | "研究". A 研究 run needs its pre-registration
               (`prereg`: a file under root, or `prereg_sha256`). With any
               dataset of origin "real" and the purpose 動作確認, only the
               time-only strategies (schedule, seeded_random) are accepted.

Origin is decided from the data, not from the word (critic i4-r1-04): a
dataset IS real market data when a file of it lies in this environment's
market-data folders (MARKET_ROOTS under the repository: the data layer's
allowed roots) or has the same bytes (size and sha256) as a file there. The
declared `origin` can only add "real": a dataset declared "synthetic" whose
file is market data is refused (a false declaration), whatever the strategy
and the purpose. The plan and the run record carry the decided origin and
its evidence (`origin_evidence`: by "position" / "bytes" / None, the market
file matched, the declared word). Limits (not decided here): a market file
edited by even one byte -- or recompressed, decompressed, re-encoded, cut to
a part -- is another file by content; market data that exists only outside
this environment (the owner's PC) is not known.

The run id is the sha256 of the identity (declarations, data sha256, code
state, version, purpose, prereg hash); no clock enters it. The run directory
holds record.json, repro.json and the exports metrics / trades / fills /
orders / data_quality, each carrying the purpose (bot.bt.report.exports), in
the form bot.monitoring.backtest_view reads (its 10 tabs; under the purpose
動作確認 every tab carries 「動作確認の実行。相場の結論には使わない」).
"""
from __future__ import annotations

import fnmatch
import hashlib
import inspect
import json
import os
import random
import re
import shutil
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from .core import (Ack, BarEvent, BookSnapshotEvent, ClockEvent, CoreEngine, Event, Fill, NullAccount, OrderFillEvent,
                   OrderRequest, Reject, Strategy, StrategyContext, TradeEvent)
from .data import DataError, load
from .data.allowlist import DEFAULT_ROOTS as _DATA_ROOTS
from .data.allowlist import MANDATORY_DENY as _NOT_MARKET
from .report import exports as X
from .report import metrics as M
from .report.trades import round_trips
from .repro.code_state import REPO, code_state, version

DEFAULT_RUNS_DIR = os.path.join(REPO, "backtest_runs")
ORIGINS = ("real", "synthetic")
# this environment's market-data folders: the data layer's allowed roots under the repository (not the caller's root)
MARKET_ROOTS = tuple(os.path.join(REPO, r) for r in _DATA_ROOTS)
TIME_ONLY = ("schedule", "seeded_random")
STRATEGY_KINDS = TIME_ONLY + ("price_rule",)
FILL_RULE = {"price": "first_observed_at_or_after", "trade": "px", "quote": {"buy": "ask", "sell": "bid"}, "bar": "open"}
COST_KEYS = ("taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct")
QUANTILE_PROBS = (0.05, 0.25, 0.5, 0.75, 0.95)
MARKOUT_HORIZONS_S = (60, 300)
PIPELINE_VERSION = "bt-item4-pipeline-r2"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
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


# --------------------------------------------------------------------------- origin from the data
_MARKET_HASHES: dict = {}  # (real path, size, mtime_ns) -> sha256 of a market file (a file changed is hashed again)


def _file_sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _under(real: str, folder: str) -> bool:
    folder = os.path.realpath(folder)
    return real == folder or real.startswith(folder + os.sep)


def _named_not_market(real: str) -> bool:
    """A path the data layer names as not market data (its mandatory refusals: qa_* synthetic packets, o3c_*
    research intermediates, phase2_runs, phase2_sealed -- bot.bt.data.allowlist.MANDATORY_DENY)."""
    rel = os.path.relpath(real, os.path.realpath(REPO))
    return any(fnmatch.fnmatchcase(c.lower(), pat.lower()) for c in rel.split(os.sep) for pat, _ in _NOT_MARKET)


def market_evidence(real: str, sha256: str, market_roots: Sequence[str] = MARKET_ROOTS) -> dict:
    """Is the file at `real` (its real path) market data of this environment? By position (it lies in a
    market-data folder) or by bytes (a file there has the same size and sha256). A file the data layer names as
    not market data (qa_*, o3c_*, phase2_runs, phase2_sealed) is neither. Every file of the folders is listed each
    time (no stale listing); only files of the same size are hashed (cached by path, size, mtime)."""
    for root in market_roots:
        if _under(real, root) and not _named_not_market(real):
            return {"by": "position", "market_path": os.path.relpath(real, os.path.realpath(REPO))}
    size = os.path.getsize(real)
    for root in market_roots:
        root_real = os.path.realpath(root)
        if not os.path.isdir(root_real):
            continue
        for dirpath, dirnames, filenames in os.walk(root_real):
            dirnames.sort()
            for name in sorted(filenames):
                cand = os.path.join(dirpath, name)
                try:
                    st = os.stat(cand)
                except OSError:
                    continue
                if st.st_size != size or not os.path.isfile(cand) or _named_not_market(os.path.realpath(cand)):
                    continue
                key = (cand, st.st_size, st.st_mtime_ns)
                if key not in _MARKET_HASHES:
                    try:
                        _MARKET_HASHES[key] = _file_sha(cand)
                    except OSError:
                        continue
                if _MARKET_HASHES[key] == sha256:
                    return {"by": "bytes", "market_path": os.path.relpath(cand, os.path.realpath(REPO))}
    return {"by": None, "market_path": None}


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


def _check_fill(fill: Mapping) -> int:
    _need(isinstance(fill, Mapping) and set(fill) == set(FILL_RULE) | {"latency_ns"},
          f"fill must be exactly {sorted(set(FILL_RULE) | {'latency_ns'})}")
    for k, v in FILL_RULE.items():
        _need(fill[k] == v, f"fill.{k} must be {v!r} (the one fill rule of the integrated run), got {fill[k]!r}")
    lat = fill["latency_ns"]
    _need(type(lat) is int and lat >= 0, "fill.latency_ns must be an int >= 0")
    return lat


def _check_costs(c: Mapping) -> dict:
    _need(isinstance(c, Mapping) and set(COST_KEYS) <= set(c) <= set(COST_KEYS) | {"source"},
          f"costs must have exactly {list(COST_KEYS)} (and optionally source)")
    out = {k: _num(c[k], f"costs.{k}") for k in COST_KEYS}
    if any(out.values()):
        _need(type(c.get("source")) is str and c["source"].strip() != "",
              "a non-zero cost needs costs.source (where the cost comes from)")
    out["source"] = c.get("source")
    return out


@dataclass
class PipelinePlan:
    run_id: str
    identity: dict
    root: str
    datasets: list
    instruments: list
    strategy: dict
    latency_ns: int
    costs: dict
    purpose: str
    prereg: Optional[str]


def plan_pipeline(*, root: str, datasets: Sequence[Mapping], instruments: Sequence[Mapping], strategy: Mapping,
                  fill: Mapping, costs: Mapping, purpose: Optional[str], prereg: Optional[str] = None,
                  prereg_sha256: Optional[str] = None, repo: Optional[str] = None) -> PipelinePlan:
    _need(purpose is not None, "purpose is required: 動作確認 or 研究")
    try:
        p = X.check_purpose(purpose)
    except ValueError as exc:
        raise PipelineError(str(exc)) from None
    _need(type(root) is str and os.path.isdir(root), f"root must be an existing directory, got {root!r}")
    pre_sha = None
    if prereg is not None:
        try:
            with open(os.path.join(root, prereg), "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            raise PipelineError(f"pre-registration {prereg!r} cannot be read: {exc}") from None
        _need(raw.strip() != b"", f"pre-registration {prereg!r} is empty")
        pre_sha = _sha(raw)
    if prereg_sha256 is not None:
        _need(type(prereg_sha256) is str and _HEX64.match(prereg_sha256) is not None,
              "prereg_sha256 must be 64 lowercase hex digits")
        _need(pre_sha is None or pre_sha == prereg_sha256, "prereg and prereg_sha256 disagree")
        pre_sha = prereg_sha256
    _need(not (p == X.RESEARCH and pre_sha is None),
          "a 研究 run needs its pre-registration (prereg or prereg_sha256): its sha256 goes into the record")
    ds = []
    names = set()
    for i, d in enumerate(datasets):
        _need(isinstance(d, Mapping) and {"name", "paths", "spec", "origin"} <= set(d)
              <= {"name", "paths", "spec", "origin", "resolve", "range_ns"},
              f"datasets[{i}] must be {{name, paths, spec, origin[, resolve, range_ns]}}")
        rng = d.get("range_ns")
        _need(rng is None or (isinstance(rng, (list, tuple)) and len(rng) == 2 and all(type(x) is int for x in rng)
                              and rng[0] < rng[1]), f"datasets[{i}].range_ns must be [lo, hi) ints in ns")
        _need(d["origin"] in ORIGINS, f"datasets[{i}].origin must be one of {ORIGINS} (stated, no default)")
        _need(type(d["name"]) is str and d["name"] and d["name"] not in names, f"datasets[{i}].name must be unique")
        names.add(d["name"])
        ds.append({"name": d["name"], "paths": list(d["paths"]), "spec": json.loads(_canon(d["spec"])),
                   "origin": d["origin"], "resolve": dict(d.get("resolve") or {}),
                   "range_ns": list(rng) if rng is not None else None})
    _need(ds, "datasets must not be empty")
    by_name = {d["name"]: d for d in ds}
    ins = []
    inames = set()
    for i, it in enumerate(instruments):
        _need(isinstance(it, Mapping) and set(it) == {"name", "price", "with"}, f"instruments[{i}] must be {{name, price, with}}")
        _need(type(it["name"]) is str and it["name"] and it["name"] not in inames, f"instruments[{i}].name must be unique")
        inames.add(it["name"])
        _need(it["price"] in by_name, f"instruments[{i}].price names no dataset")
        kind = by_name[it["price"]]["spec"].get("kind")
        _need(kind in _PRICE_EVENT, f"instruments[{i}]: a {kind!r} dataset cannot price fills")
        w = list(it["with"])
        _need(all(x in by_name and x != it["price"] for x in w), f"instruments[{i}].with names an unknown dataset or the price one")
        for x in w:
            _need(_PRICE_EVENT.get(by_name[x]["spec"].get("kind")) is not _PRICE_EVENT[kind],
                  f"instruments[{i}]: {x!r} has the same event type as the price dataset (its prices could not be told apart)")
        ins.append({"name": it["name"], "price": it["price"], "with": w, "price_kind": kind})
    _need(ins, "instruments must not be empty")
    st = _check_strategy(strategy)
    for lg in st.get("legs", []):
        _need(lg.get("instrument") in (None, *inames), f"an order names the unknown instrument {lg.get('instrument')!r}")
    lat = _check_fill(fill)
    cs = _check_costs(costs)
    for it in ins:
        _need(not (it["price_kind"] == "quote" and cs["spread_pct"] != 0),
              f"instrument {it['name']!r} is priced from quotes, which carry their spread: spread_pct must be 0")
    hashes = {}
    for d in ds:
        found = []
        for pth in d["paths"]:
            full = os.path.join(root, pth)
            try:
                with open(full, "rb") as fh:
                    hashes[pth] = _sha(fh.read())
            except OSError as exc:
                raise PipelineError(f"data {pth!r} cannot be read: {exc}") from None
            ev = market_evidence(os.path.realpath(full), hashes[pth])
            if ev["by"] is not None:
                found.append(ev)
        declared = d["origin"]
        if found and declared == "synthetic":
            raise PipelineError(f"dataset {d['name']!r} is declared synthetic but its file is market data of this "
                                f"environment ({found[0]['market_path']}, by {found[0]['by']}): the origin is decided "
                                f"from the data, not the word")
        d["origin"] = "real" if found or declared == "real" else "synthetic"
        d["origin_evidence"] = {"declared": declared, "by": found[0]["by"] if found else None,
                                "market_path": found[0]["market_path"] if found else None}
    real = any(d["origin"] == "real" for d in ds)
    _need(not (real and p == X.SMOKE and st["kind"] not in TIME_ONLY),
          f"a 動作確認 run on real data takes a time-only strategy {TIME_ONLY} (委任文 §4: no signal, no conditioning, "
          f"no optimisation); got {st['kind']!r}")
    code = code_state(repo)
    src = inspect.getsource(inspect.getmodule(plan_pipeline))
    identity = {
        "datasets": ds, "data_sha256": hashes, "instruments": ins, "strategy": json.loads(_canon(dict(strategy))),
        "fill": json.loads(_canon(dict(fill))), "costs": cs, "purpose": p, "prereg_sha256": pre_sha,
        "git_sha": code["git_sha"], "diff_hash": code["diff_hash"], "code_scope": code["code_scope"],
        "version": f"{PIPELINE_VERSION}; {version()}",
        "setup": {"name": f"{__name__}:{st['kind']}", "source_sha256": _sha(src.encode())},
    }
    return PipelinePlan(_sha(_canon(identity).encode()), identity, root, ds, ins, st, lat, cs, p, prereg)


# --------------------------------------------------------------------------- the sockets of one instrument
class FirstObservedFill:
    """Fill model: a market order fills in full at the first observation of
    the price event type at or after its arrival (see the module docstring)."""

    def __init__(self, price_type: type, costs: dict) -> None:
        self.price_type = price_type
        self.c = costs
        self.pending: list[tuple[OrderRequest, int]] = []
        self.last: Optional[tuple[int, Event]] = None  # (observation time, event)
        self.obs_time: dict[str, int] = {}

    def _obs(self, ev: Event) -> tuple[int, float, float]:
        """(observation time, buy price, sell price) before slippage / spread."""
        if type(ev) is BarEvent:
            return ev.start_time_ns, ev.open, ev.open
        if type(ev) is TradeEvent:
            return ev.exchange_time_ns, ev.price, ev.price
        if not ev.asks or not ev.bids:
            return ev.exchange_time_ns, float("nan"), float("nan")
        return ev.exchange_time_ns, ev.asks[0][0], ev.bids[0][0]

    def _price(self, side: str, ev: Event) -> float:
        _, buy, sell = self._obs(ev)
        adj = self.c["slippage_pct"] + (0.0 if type(ev) is BookSnapshotEvent else self.c["spread_pct"] / 2)
        return buy * (1 + adj / 100) if side == "buy" else sell * (1 - adj / 100)

    def _fill(self, order: OrderRequest, ev: Event) -> list:
        px = self._price(order.side, ev)
        if not (px == px and px > 0):
            return []  # this observation has no price on the order's side (an empty book side): keep waiting
        self.obs_time[order.client_order_id] = self._obs(ev)[0]
        return [Fill(order.client_order_id, px, order.size, "taker")]

    def on_market_event(self, event: Event, venue_time_ns: int):
        if type(event) is not self.price_type:
            return ()
        t = self._obs(event)[0]
        self.last = (t, event)
        out, keep = [], []
        for order, arrival in self.pending:
            if t >= arrival:
                got = self._fill(order, event)
                if got:
                    out += got
                    continue
            keep.append((order, arrival))
        self.pending = keep
        return tuple(out)

    def on_order(self, order: OrderRequest, venue_time_ns: int):
        if order.order_type != "market":
            return (Reject(order.client_order_id, "the integrated run's fill rule takes market orders only"),)
        out = [Ack(order.client_order_id, f"p-{order.client_order_id}")]
        if self.last is not None and self.last[0] >= venue_time_ns:
            got = self._fill(order, self.last[1])  # an observation at the arrival instant is "at or after"
            if got:
                return tuple(out + got)
        self.pending.append((order, venue_time_ns))
        return tuple(out)

    def on_cancel(self, request, venue_time_ns: int):
        from .core import Canceled
        self.pending = [(o, a) for o, a in self.pending if o.client_order_id != request.client_order_id]
        return (Canceled(request.client_order_id),)


class _Latency:
    def __init__(self, ns: int) -> None:
        self.ns = ns

    def feed_delay_ns(self, event) -> int:
        return self.ns

    def order_delay_ns(self, order, sent_time_ns: int) -> int:
        return self.ns

    def cancel_delay_ns(self, request, sent_time_ns: int) -> int:
        return self.ns

    def notice_delay_ns(self, report, venue_time_ns: int) -> int:
        return self.ns


class _Fee:
    def __init__(self, costs: dict) -> None:
        self.c = costs

    def cost(self, fill) -> float:
        pct = self.c["taker_fee_pct"] if fill.liquidity == "taker" else self.c["maker_fee_pct"]
        return abs(fill.price * fill.size) * pct / 100


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
    fills: list
    trades: list
    orders: list
    events_read: dict
    engine: dict


def _run_instrument(plan: PipelinePlan, it: dict, loaded) -> InstrumentResult:
    price_type = _PRICE_EVENT[it["price_kind"]]
    streams = {}
    resolve = {d["name"]: d["resolve"] for d in plan.datasets if d["resolve"]}
    try:
        for name in [it["price"]] + it["with"]:
            streams[name] = list(loaded.events(name, resolve.get(name)))
    except DataError as exc:
        raise PipelineError(f"data: {type(exc).__name__}: {exc}") from None
    times = [e.exchange_time_ns for s in streams.values() for e in s]
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
    fm = FirstObservedFill(price_type, plan.costs)
    res = CoreEngine(strat, streams, fm, _Latency(plan.latency_ns), _Fee(plan.costs), NullAccount(),
                     time_span_ns=(first, max(times))).run()
    sides = {o.client_order_id: o.request.side for o in res.orders.values()}
    fills = [{"order_id": f.client_order_id, "t_ns": fm.obs_time[f.client_order_id], "venue_t_ns": f.venue_time_ns,
              "side": f.side or sides[f.client_order_id], "px": f.price, "qty": f.size, "fee": f.fee,
              "liquidity": f.liquidity, "instrument": it["name"]} for f in res.fills]
    orders = [{"id": o.client_order_id, "t_ns": o.sent_time_ns, "side": o.request.side, "type": o.request.order_type,
               "qty": o.request.size, "state": o.state.value if hasattr(o.state, "value") else str(o.state),
               "filled": o.filled_size, "instrument": it["name"]} for o in res.orders.values()]
    if reasons is None:
        reasons = {f["order_id"]: "rule" for f in fills}
    trades = [dict(t, instrument=it["name"]) for t in round_trips(fills, reasons)]
    read = {k: v for k, v in res.source_events_by_stream.items() if k != "~clock"}
    return InstrumentResult(it["name"], fills, trades, orders, read,
                            {"events_processed": res.events_processed, "source_events": res.source_events,
                             "delivery_digest": res.delivery_digest, "first_time_ns": res.first_time_ns,
                             "last_time_ns": res.last_time_ns, "models": dict(res.models),
                             "defaults_used": list(res.defaults_used)})


def execute_once(plan: PipelinePlan, out_dir: str) -> dict:
    """One execution of the plan, writing every output file into out_dir.
    Returns {"instruments": {name: InstrumentResult}, "events_read": {dataset: n}}."""
    specs = [{"name": d["name"], "paths": d["paths"], "spec": d["spec"],
              **({"range_ns": list(d["range_ns"])} if d["range_ns"] else {})} for d in plan.datasets]
    try:
        loaded = load(plan.root, specs)
    except DataError as exc:
        raise PipelineError(f"data: {type(exc).__name__}: {exc}") from None
    _need(loaded.hashes() == plan.identity["data_sha256"], "data changed between planning and execution")
    per = {it["name"]: _run_instrument(plan, it, loaded) for it in plan.instruments}
    rid = plan.run_id
    fills = [f for r in per.values() for f in r.fills]
    trades = [t for r in per.values() for t in r.trades]
    orders = [o for r in per.values() for o in r.orders]
    read: dict[str, int] = {}
    for r in per.values():
        for k, v in r.events_read.items():
            read[k] = read.get(k, 0) + v
    dist = M.trade_distribution(trades, QUANTILE_PROBS) if trades else {"n": 0, "per_trade_bp": []}
    eq, eq_t, cum = [0.0], [min(f["t_ns"] for f in fills) if fills else 0], 0.0
    for t in sorted(trades, key=lambda x: (x["exit_t_ns"], x["id"])):
        cum += t["pnl"]
        eq.append(cum)
        eq_t.append(t["exit_t_ns"])
    fees = {"maker": 0.0, "taker": 0.0}
    for f in fills:
        fees[f["liquidity"]] += f["fee"]
    by_inst = {}
    for name, r in per.items():
        d = M.trade_distribution(r.trades, QUANTILE_PROBS) if r.trades else {"n": 0, "per_trade_bp": []}
        by_inst[name] = {"num_trades": len(r.trades), "realized_pnl": sum(t["pnl"] for t in r.trades),
                         "gross_sell_minus_buy": sum((f["px"] if f["side"] == "sell" else -f["px"]) * f["qty"]
                                                     for f in r.fills),
                         "fees": sum(f["fee"] for f in r.fills), "trades": d}
    fm = M.fill_metrics([{"id": f"{o['instrument']}/{o['id']}", "qty": o["qty"]} for o in orders],
                        [{"order_id": f"{f['instrument']}/{f['order_id']}", "t_ns": f["t_ns"], "qty": f["qty"]}
                         for f in fills], max(f["venue_t_ns"] for f in fills) if fills else 0) if orders else None
    metrics = {
        "trades": dist, "by_instrument": by_inst,
        "pnl_jpy": {"realized": cum, "fees": sum(fees.values()),
                    "note": "銘柄ごとの通貨の額を足している(銘柄ごとの値は by_instrument)"},
        "fills": fm,
        "markout": {"reference": "測っていない(統合の実行は銘柄ごとに価格の単位が違う)", "unit": None, "values": {}},
        "costs": {"maker_fee": fees["maker"], "taker_fee": fees["taker"], "spread": None,
                  "spread_note": "宣言の spread_pct(約定の値に含む)", "funding": 0.0, "funding_note": "資金調達の事象を読んでいない"},
        "exit_reasons": M.exit_reasons(trades) if trades else {},
        "drawdown": {**M.drawdown(eq, eq_t), "max_dd_pct": None, "pct_note": "資本が宣言されていないので率は出さない"},
        "equity": {"t_ns": eq_t, "realized_jpy": eq},
        "events_read": read,
    }
    man = loaded.manifest()
    man.pop("root", None)
    man["files"] = [{k: v for k, v in f.items() if k != "real"} for f in man.get("files", [])]
    man["seal_records"] = {os.path.relpath(k, os.path.realpath(plan.root)): v for k, v in man.get("seal_records", {}).items()}
    quality = {"manifest": man, "anomalies": {n: loaded.anomalies(n) for n in loaded.names()},
               "checks": {n: loaded.checks(n) for n in loaded.names()},
               "origin": {d["name"]: d["origin"] for d in plan.datasets}}
    ident = plan.identity
    record = {
        "run_id": rid, "git_sha": ident["git_sha"], "diff_hash": ident["diff_hash"], "code_scope": ident["code_scope"],
        "config": {"instrument": ", ".join(i["name"] for i in plan.instruments), "instruments": plan.instruments,
                   "strategy": ident["strategy"], "fill": ident["fill"], "latency_ns": plan.latency_ns,
                   "costs": plan.costs},
        "data": [{"path": pth, "dataset": d["name"], "spec": d["spec"], "origin": d["origin"],
                  "origin_evidence": d["origin_evidence"]} for d in plan.datasets for pth in d["paths"]],
        "data_sha256": ident["data_sha256"], "seed": plan.strategy.get("seed") if isinstance(plan.strategy, dict) else None,
        "setup": ident["setup"], "version": ident["version"], "purpose": plan.purpose,
        "prereg_sha256": ident["prereg_sha256"], "prereg": plan.prereg,
        "components": {"models": {n: r.engine["models"] for n, r in per.items()},
                       "defaults_used": {n: r.engine["defaults_used"] for n, r in per.items()}, "notes": {}},
        "engine": {n: {k: v for k, v in r.engine.items() if k not in ("models", "defaults_used")} for n, r in per.items()},
    }
    with open(os.path.join(out_dir, "record.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(X.canonical_json(record) + "\n")
    for kind, payload in (("metrics", metrics), ("trades", trades), ("fills", fills), ("orders", orders),
                          ("data_quality", quality)):
        X.write_export(out_dir, kind, payload, purpose=plan.purpose, run_id=rid)
    return {"instruments": per, "events_read": read}


# --------------------------------------------------------------------------- the run (two executions)
@dataclass
class PipelineResult:
    run_id: str
    run_dir: str
    record: dict
    exports: dict  # file name -> purpose
    repro: dict
    instruments: dict = field(default_factory=dict)  # name -> InstrumentResult (of the kept execution)
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
    return PipelineResult(plan.run_id, final, record, exports, repro, outs[0]["instruments"], outs[0]["events_read"])
