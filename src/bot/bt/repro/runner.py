"""Runs and their records (item 3, old item 8: 「実行記録(git の SHA と差分のハッシュ・
設定・データの sha256・種・版)。実行 ID = 内容のハッシュ。同じ入力で 2 回回して一致を自動で
確かめる。成果物は `backtest_runs/<id>/`(gitignore)。事前登録のハッシュを実行記録に入れる」).

    plan = plan_run(root=, data=, config=, seed=, setup=, purpose=, prereg=None, repo=None)
    result = run(..., runs_dir=)              # executes twice, compares, keeps one
    check = check_reproducible(...)           # executes twice, compares, keeps nothing

`validation` (optional): plain JSON results of bot.bt.validation for this
run (walk-forward folds, DSR, MDE, ...); it is part of the identity and is
exported as validation.json (shown on the dashboard's 検証 tab).

The identity of a run is everything that decides its outputs: the config
(as canonical JSON: key order does not matter, values do), every data file's
sha256 and its declaration, the seed, the setup (name + sha256 of its
source), the code (git HEAD + diff hash of the code scope), the version
string, the purpose and the pre-registration's sha256. run_id = sha256 of
that identity. No clock and no random number enter it.

`purpose` is required: 動作確認 or 研究. A 研究 run needs a pre-registration
file (its sha256 goes into the record); without one it is refused.

Every execution writes the same set of files (record.json and the metric
exports, each carrying the purpose). `run` executes the input twice in two
fresh directories and compares every output file byte for byte; a
difference raises NotReproducibleError and keeps nothing. The kept run
directory gets `repro.json` (runs compared, identical, each file's sha256).
A run id that already has a directory is compared with it: the same bytes
keep it, different bytes are refused (the identity did not capture what
changed).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from ..core import CoreEngine
from ..data import DataError, load
from ..report import exports as X
from ..report import metrics as M
from ..report.trades import round_trips
from .code_state import REPO, code_state, version
from .errors import NotReproducibleError, ReproError

DEFAULT_RUNS_DIR = os.path.join(REPO, "backtest_runs")  # gitignored by the .gitignore run() writes into it
MARKOUT_HORIZONS_S = (60, 300)
QUANTILE_PROBS = (0.05, 0.25, 0.5, 0.75, 0.95)


def canonical(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReproError(f"not plain finite JSON: {exc}") from None


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass(frozen=True)
class DataInput:
    """One data file of a run: its path (relative to the run's root) and its
    declaration for the data layer (bot.bt.data.spec); `resolve` = the
    anomaly policies (bot.bt.data.anomalies) if the file has anomalies."""
    path: str
    spec: Mapping
    resolve: Optional[Mapping[str, str]] = None


@dataclass
class RunPlan:
    run_id: str
    identity: dict
    root: str
    data: tuple
    config: Any
    seed: int
    setup: Any
    purpose: str
    prereg: Optional[str]


@dataclass
class RunResult:
    run_id: str
    run_dir: str
    record: dict
    exports: dict  # file name -> purpose
    repro: dict


@dataclass
class ReproCheck:
    reproduced: bool
    runs: int
    differing: list = field(default_factory=list)
    sha256: dict = field(default_factory=dict)


def plan_run(*, root: str, data: Sequence[DataInput], config: Any, seed: int, setup: Any, purpose: Optional[str],
             prereg: Optional[str] = None, repo: Optional[str] = None,
             validation: Optional[Mapping] = None) -> RunPlan:
    if purpose is None:
        raise ReproError("purpose is required: 動作確認 or 研究 (a run without a purpose cannot be made)")
    p = X.check_purpose(purpose)
    if type(seed) is not int:
        raise ReproError(f"seed must be an int, got {seed!r}")
    if type(root) is not str or not os.path.isdir(root):
        raise ReproError(f"root must be an existing directory, got {root!r}")
    ds = tuple(data)
    if not ds or not all(isinstance(d, DataInput) for d in ds):
        raise ReproError("data must be a non-empty sequence of DataInput")
    cfg = json.loads(canonical(config))
    prereg_sha = None
    if prereg is not None:
        path = os.path.join(root, prereg)
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            raise ReproError(f"pre-registration {prereg!r} cannot be read: {exc}") from None
        if not raw.strip():
            raise ReproError(f"pre-registration {prereg!r} is empty")
        prereg_sha = _sha(raw)
    if p == X.RESEARCH and prereg_sha is None:
        raise ReproError("a 研究 run needs its pre-registration (prereg=...): its sha256 goes into the record")
    hashes = {}
    for d in ds:
        full = os.path.join(root, d.path)
        try:
            with open(full, "rb") as fh:
                hashes[d.path] = _sha(fh.read())
        except OSError as exc:
            raise ReproError(f"data {d.path!r} cannot be read: {exc}") from None
    code = code_state(repo)
    identity = {
        "config": cfg, "data": [{"path": d.path, "spec": json.loads(canonical(d.spec)),
                                 "resolve": json.loads(canonical(d.resolve)) if d.resolve else None} for d in ds],
        "data_sha256": hashes, "seed": seed, "setup": setup.identity(), "git_sha": code["git_sha"],
        "diff_hash": code["diff_hash"], "code_scope": code["code_scope"], "version": version(),
        "purpose": p, "prereg_sha256": prereg_sha,
        "validation": json.loads(canonical(validation)) if validation is not None else None,
    }
    return RunPlan(_sha(canonical(identity).encode()), identity, root, ds, config, seed, setup, p, prereg)


def _execute(plan: RunPlan, out_dir: str) -> None:
    """One execution of the plan, writing every output file into out_dir."""
    datasets = [{"name": f"d{i}", "paths": [d.path], "spec": dict(d.spec)} for i, d in enumerate(plan.data)]
    try:
        loaded = load(plan.root, datasets)
        streams = loaded.streams({f"d{i}": dict(d.resolve) for i, d in enumerate(plan.data) if d.resolve})
    except DataError as exc:
        raise ReproError(f"data: {type(exc).__name__}: {exc}") from None
    got = loaded.hashes()
    if got != plan.identity["data_sha256"]:
        raise ReproError(f"data changed between planning and execution: {got} vs {plan.identity['data_sha256']}")
    parts = plan.setup.build(plan.config, plan.seed)
    times = [e.exchange_time_ns for s in streams.values() for e in s]
    if not times:
        raise ReproError("the data has no event")
    eng = CoreEngine(parts.strategy, streams, parts.fill_model, parts.latency_model, parts.cost_model, parts.account,
                     time_span_ns=(min(times), max(times)))
    res = eng.run()
    rid = plan.run_id
    sides = {o.client_order_id: o.request.side for o in res.orders.values()}
    fills = [{"order_id": f.client_order_id, "t_ns": f.venue_time_ns, "side": f.side or sides[f.client_order_id],
              "px": f.price, "qty": f.size, "fee": f.fee, "liquidity": f.liquidity} for f in res.fills]
    orders = [{"id": o.client_order_id, "t_ns": o.sent_time_ns, "side": o.request.side, "type": o.request.order_type,
               "qty": o.request.size, "state": o.state.value if hasattr(o.state, "value") else str(o.state),
               "filled": o.filled_size} for o in res.orders.values()]
    trades = round_trips(fills, parts.exit_reasons)
    dist = M.trade_distribution(trades, QUANTILE_PROBS) if trades else {"n": 0, "per_trade_bp": []}
    equity, eq_t, cum = [0.0], [min(times)], 0.0
    for t in trades:
        cum += t["pnl"]
        equity.append(cum)
        eq_t.append(t["exit_t_ns"])
    trade_path = sorted((e.exchange_time_ns, e.price) for s in streams.values() for e in s if hasattr(e, "price"))
    fm = M.fill_metrics([{"id": o["id"], "qty": o["qty"]} for o in orders],
                        [{"order_id": f["order_id"], "t_ns": f["t_ns"], "qty": f["qty"]} for f in fills],
                        max(times)) if orders else None
    fees = {"maker": 0.0, "taker": 0.0}
    for f in fills:
        fees[f["liquidity"]] += f["fee"]
    metrics = {
        "trades": dist,
        "pnl_jpy": {"realized": cum, "fees": sum(fees.values())},
        "fills": fm,
        "markout": {"reference": "直前の約定の値(仲値のデータが無い実行)", "unit": "price",
                    "values": M.markout(fills, trade_path, list(MARKOUT_HORIZONS_S), unit="price") if fills else {}},
        "costs": {"maker_fee": fees["maker"], "taker_fee": fees["taker"],
                  "spread": None, "spread_note": "約定の時点の仲値がデータに無いので測れない",
                  "funding": 0.0, "funding_note": "設定の costs.funding = none"},
        "exit_reasons": M.exit_reasons(trades) if trades else {},
        "drawdown": {**M.drawdown(equity, eq_t), "max_dd_pct": None,
                     "pct_note": "資本が宣言されていないので率は出さない(額は累積の実現損益から)"},
        "equity": {"t_ns": eq_t, "realized_jpy": equity},
    }
    # the data layer's manifest without the absolute paths (root, real): the outputs of a run must not
    # depend on where its root lies, only on what it read (the paths as given and relative to the root)
    man = loaded.manifest()
    man.pop("root", None)
    man["files"] = [{k: v for k, v in f.items() if k != "real"} for f in man.get("files", [])]
    man["seal_records"] = {os.path.relpath(k, os.path.realpath(plan.root)): v
                           for k, v in man.get("seal_records", {}).items()}
    quality = {"manifest": man, "anomalies": {n: loaded.anomalies(n) for n in loaded.names()},
               "checks": {n: loaded.checks(n) for n in loaded.names()}}
    record = {
        "run_id": rid, **{k: plan.identity[k] for k in ("git_sha", "diff_hash", "code_scope", "config", "data",
                                                       "data_sha256", "seed", "setup", "version", "purpose",
                                                       "prereg_sha256")},
        "prereg": plan.prereg,
        "components": {"models": dict(res.models), "defaults_used": list(res.defaults_used), "notes": parts.notes},
        "engine": {"events_processed": res.events_processed, "source_events": res.source_events,
                   "delivery_digest": res.delivery_digest, "first_time_ns": res.first_time_ns,
                   "last_time_ns": res.last_time_ns},
    }
    with open(os.path.join(out_dir, "record.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(X.canonical_json(record) + "\n")
    outs = [("metrics", metrics), ("trades", trades), ("fills", fills), ("orders", orders), ("data_quality", quality)]
    if plan.identity["validation"] is not None:
        outs.append(("validation", plan.identity["validation"]))
    for kind, payload in outs:
        X.write_export(out_dir, kind, payload, purpose=plan.purpose, run_id=rid)


def _digests(d: str) -> dict:
    out = {}
    for name in sorted(os.listdir(d)):
        with open(os.path.join(d, name), "rb") as fh:
            out[name] = _sha(fh.read())
    return out


def _compare(a: dict, b: dict) -> list:
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def _twice(plan: RunPlan, base: str, runs: int) -> tuple[list[str], list[dict]]:
    os.makedirs(base, exist_ok=True)
    dirs, digs = [], []
    for k in range(runs):
        d = os.path.join(base, f".work-{plan.run_id[:16]}-{os.getpid()}-{k}")
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        dirs.append(d)
        try:
            _execute(plan, d)
        except BaseException:
            for x in dirs:
                shutil.rmtree(x, ignore_errors=True)
            raise
        digs.append(_digests(d))
    return dirs, digs


def check_reproducible(plan: RunPlan, *, work_dir: str, runs: int = 2) -> ReproCheck:
    if type(runs) is not int or runs < 2:
        raise ReproError("the check needs at least 2 executions")
    dirs, digs = _twice(plan, work_dir, runs)
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)
    differing = sorted({k for x in digs[1:] for k in _compare(digs[0], x)})
    return ReproCheck(not differing, runs, differing, digs[0])


def _ensure_runs_dir(runs_dir: str) -> None:
    os.makedirs(runs_dir, exist_ok=True)
    gi = os.path.join(runs_dir, ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w", encoding="utf-8") as fh:
            fh.write("# run outputs are not versioned (bot.bt.repro)\n*\n")


def run(*, runs_dir: str = DEFAULT_RUNS_DIR, runs: int = 2, **plan_args: Any) -> RunResult:
    if type(runs) is not int or runs < 2:
        raise ReproError("a run is executed at least twice (the automatic reproducibility check)")
    plan = plan_run(**plan_args)
    _ensure_runs_dir(runs_dir)
    dirs, digs = _twice(plan, runs_dir, runs)
    differing = sorted({k for x in digs[1:] for k in _compare(digs[0], x)})
    for d in dirs[1:]:
        shutil.rmtree(d, ignore_errors=True)
    if differing:
        shutil.rmtree(dirs[0], ignore_errors=True)
        raise NotReproducibleError(f"{runs} executions of run {plan.run_id} differ in {differing}", differing)
    final = os.path.join(runs_dir, plan.run_id)
    if os.path.isdir(final):
        old = {k: v for k, v in _digests(final).items() if k != "repro.json"}
        shutil.rmtree(dirs[0], ignore_errors=True)
        if old != digs[0]:
            raise ReproError(f"run {plan.run_id} already exists with different outputs {_compare(old, digs[0])}: "
                             "the identity did not capture what changed")
    else:
        os.replace(dirs[0], final)
    repro = {"runs": runs, "identical": True, "sha256": digs[0]}
    with open(os.path.join(final, "repro.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(X.canonical_json(repro) + "\n")
    with open(os.path.join(final, "record.json"), "r", encoding="utf-8") as fh:
        record = json.load(fh)
    exports = {}
    for name in sorted(os.listdir(final)):
        if name not in ("record.json", "repro.json"):
            exports[name] = X.read_export(os.path.join(final, name))["purpose"]
    return RunResult(plan.run_id, final, record, exports, repro)
