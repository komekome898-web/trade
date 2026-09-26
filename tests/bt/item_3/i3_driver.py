"""Test helper (not a test module): drive one item-3 battery request
(tests/bt/battery/item_3/i3_protocol.py) through the new implementation's
PUBLIC API only -- bot.bt.validation, bot.bt.repro, bot.bt.report,
bot.monitoring.backtest_view and scripts/dashboard.py -- and return the
observation in the battery's forms.

It computes no value the API did not produce: it calls the API, renames
containers, and writes the user code a request names (the walk-forward
rule; the fixed run's declaration of its tape). A refusal of the API
propagates as its own exception.

Choices this helper makes for requests that leave them open (each stated):
  purged_split / cpcv  the request gives the embargo both as rows and as ns;
                       the row form is passed (the API takes exactly one).
  block_bootstrap      method "circular" (the request names a block length,
                       not a scheme).
  run data             the tape's declaration: csv with header, t_ns in ns,
                       px, qty (the tape's columns as the protocol writes them).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BATTERY = REPO / "tests" / "bt" / "battery" / "item_3"
WIRING_TEST = Path(__file__).resolve().parent / "test_i3_dashboard_wiring.py"

from bot.bt import validation as V  # noqa: E402
from bot.bt.report import metrics as M  # noqa: E402
from bot.bt.repro import DataInput, FixedSetup, check_reproducible, plan_run, run as bt_run  # noqa: E402

TAPE_SPEC = {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY",
             "asset": "crypto", "time": {"columns": ["t_ns"], "unit": "ns"}, "fields": {"px": "px", "qty": "qty"}}


def dashboard_module():
    spec = importlib.util.spec_from_file_location("i3_new_dashboard", REPO / "scripts" / "dashboard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plan_args(root: str, spec: dict) -> dict:
    return {"root": root, "data": [DataInput(p, TAPE_SPEC) for p in spec["data"]], "config": spec["config"],
            "seed": spec["seed"], "setup": FixedSetup(spec["strategy"]), "purpose": spec.get("purpose"),
            "prereg": spec.get("prereg")}


def _run(root: str, spec: dict):
    return bt_run(runs_dir=os.path.join(root, spec["runs_dir"]), **_plan_args(root, spec))


def _serve(runs_dir: str):
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", 0), dashboard_module().make_handler(runs_dir))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv


def _get(port: int, path: str) -> bytes:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=20) as r:
        return r.read()


def _external(text: str) -> list[str]:
    return re.findall(r"""(?:src|href)\s*=\s*["'](https?://[^"']+)|@import\s+(?:url\()?["']?(https?://[^"')]+)|url\(\s*["']?(https?://[^"')]+)""",
                      text)


def run(inp: dict) -> dict:
    op, root = inp["op"], inp.get("root", "")
    if op == "calendar_split":
        cs = V.calendar_split(inp["rows"], tz=inp["tz"], train_end=inp["train_end"], val_end=inp["val_end"])
        return {"parts": {k: [inp["rows"][i] for i in p.idx] for k, p in cs.parts().items()}}
    if op in ("walk_forward", "walk_forward_eval"):
        folds = V.walk_forward(inp["rows"], tz=inp["tz"], train_days=inp["train_days"], test_days=inp["test_days"],
                               step_days=inp["step_days"], mode=inp["mode"])
        if op == "walk_forward":
            return {"folds": [{"train": {"bounds": list(f.train.bounds)}, "test": {"bounds": list(f.test.bounds)}}
                              for f in folds]}
        ev = V.walk_forward_eval(folds, inp["columns"],
                                 fit=lambda c: "a" if sum(c["a"]) >= sum(c["b"]) else "b",
                                 evaluate=lambda ch, c: sum(c[ch]))
        return {"folds": [{"choice": e.choice, "test_score": e.score} for e in ev]}
    if op == "purged_split":
        p = V.purged_train(inp["rows"], inp["label_end"], inp["test_rows"], embargo_rows=inp["embargo_rows"])
        return {"train_idx": list(p.train)}
    if op in ("cpcv", "cpcv_paths"):
        c = V.cpcv(inp["rows"], inp["label_end"], n_groups=inp["n_groups"], n_test_groups=inp["n_test_groups"],
                   embargo_rows=inp["embargo_rows"])
        if op == "cpcv_paths":
            return {"paths": [[{"split": list(s), "group": g} for s, g in path] for path in c.paths()]}
        return {"n_splits": c.n_splits, "n_paths": c.n_paths, "train_idx": list(c.split_for(inp["want_train_for"]).purged.train)}
    if op == "block_bootstrap":
        b = V.block_bootstrap_ci(inp["x"], block_len=inp["block_len"], n_resamples=inp["n_resamples"], seed=inp["seed"],
                                 alpha=inp["alpha"], method="circular", statistic=inp["statistic"])
        return {"ci": [b.lo, b.hi]}
    if op == "mde":
        return {"mde": V.mde(n=inp["n"], sd=inp["sd"], alpha=inp["alpha"], power=inp["power"], sides=inp["sides"],
                             approx=inp["approx"])}
    if op == "verdict":
        return {"verdicts": [V.verdict(estimate=c["estimate"], se=c["se"], interest=c["interest"], n=c.get("n"),
                                       sd=c.get("sd"), alpha=inp["alpha"], power=inp["power"], sides=inp["sides"],
                                       approx="normal").label for c in inp["cases"]]}
    if op == "dsr":
        return {"dsr": V.deflated_sharpe(sr=inp["sr"], T=inp["T"], skew=inp["skew"], kurtosis=inp["kurtosis"],
                                         n_trials=inp["n_trials"], var_trials=inp["var_trials"]).dsr}
    if op == "dsr_returns":
        return {"dsr": V.deflated_sharpe_of_returns(inp["returns"], n_trials=inp["n_trials"],
                                                    var_trials=inp["var_trials"]).dsr}
    if op == "pbo":
        return {"pbo": V.pbo(inp["matrix"], n_blocks=inp["n_blocks"], metric=inp["metric"]).pbo}
    if op == "iter_ledger":
        d = os.path.join(root, inp["ledger_dir"])
        led = V.IterLedger(d)
        for t in inp["first"]:
            led.add(**t)
        counts = [led.count(), V.IterLedger(d).count()]
        led2 = V.IterLedger(d)
        for t in inp["more"]:
            led2.add(**t)
        return {"counts": counts + [led2.count()]}
    if op == "iter_dsr":
        led = V.IterLedger(os.path.join(root, inp["ledger_dir"]))
        for t in inp["trials"]:
            led.add(**t)
        b = inp["best"]
        return {"dsr": V.deflated_sharpe_from_ledger(led, sr=b["sr"], T=b["T"], skew=b["skew"], kurtosis=b["kurtosis"],
                                                     var_trials=inp["var_trials"]).dsr}
    if op == "sealed_read":
        os.environ.pop("PHASE2_FINAL_EVAL", None)
        os.environ.update(inp["env"])
        df = V.read_sealed(os.path.join(root, inp["path"]), unit=inp["unit"], token=inp["token"], root=root)
        return {"v": [int(x) for x in df["v"].tolist()]}
    if op == "data_read":
        df = V.read_table(root, inp["path"], time_column=inp["time_column"])
        return {"v": [int(x) for x in df["v"].tolist()]}
    if op == "run":
        res = [_run(root, inp["run"]) for _ in range(inp.get("repeat", 1))]
        obs = {"run_id": res[0].run_id, "record": res[0].record, "exports": res[0].exports}
        if "repeat" in inp:
            obs["records"] = [r.record for r in res]
        return obs
    if op == "run_ids":
        ids = []
        for spec, wait in zip(inp["runs"], inp["sleep_before_s"]):
            time.sleep(wait)
            ids.append(_run(root, spec).run_id)
        return {"ids": ids}
    if op == "auto_repro":
        spec = inp["run"]
        chk = check_reproducible(plan_run(**_plan_args(root, spec)), work_dir=os.path.join(root, spec["runs_dir"]))
        return {"reproduced": chk.reproduced, "runs": chk.runs}
    if op == "trade_metrics":
        trades = [dict(t, fees=0.0) for t in inp["trades"]]  # the scenes state 費用 0
        dist = M.trade_distribution(trades, inp.get("quantile_probs", (0.05, 0.25, 0.5, 0.75, 0.95)))
        full = {"per_trade_bp": dist["per_trade_bp"], "quantiles": dist["quantiles"], "neg_frac": dist["neg_frac"],
                "exposure_hours": dist["trade_hours"], "bp_per_hour": dist["bp_per_hour"]}
        return {k: full[k] for k in inp["want"]}
    if op == "fill_metrics":
        orders = [{"id": o["id"], "qty": o["qty"]} for o in inp["orders"]]
        r = M.fill_metrics(orders, inp["fills"], inp["end_t_ns"])
        return {"fill_rate": r["fill_rate"], "missed": r["missed"]}
    if op == "markout":
        return {"markout": M.markout(inp["fills"], inp["mids"], inp["horizons_s"], unit="price")}
    if op == "cost_breakdown":
        return {"costs": M.cost_breakdown(inp["fills"], inp["funding"], inp["rates"])}
    if op == "exit_reasons":
        return {"by_reason": M.exit_reasons(inp["trades"])}
    if op == "drawdown":
        d = M.drawdown(inp["equity"], inp["t_ns"])
        return {"max_dd_pct": d["max_dd_pct"], "max_dd_abs": d["max_dd_abs"]}
    if op == "dashboard":
        runs_dir = os.path.join(root, "runs")
        ids = {}
        for spec in inp["runs"]:
            s = {k: v for k, v in spec.items() if k != "key"}
            ids[spec["key"]] = _run(root, dict(s, runs_dir="runs")).run_id
        srv = _serve(runs_dir)
        try:
            port = srv.server_address[1]
            page = _get(port, "/").decode("utf-8")
            nav = re.search(r'<nav class="tabs">(.*?)</nav>', page, re.S)
            top = re.findall(r"<button[^>]*>([^<]*)</button>", nav.group(1)) if nav else []
            lst = [r["run_id"] for r in json.loads(_get(port, "/api/backtest/runs"))["runs"]]
            run_tabs, tab_text, values, ext = {}, {}, {}, _external(page)
            for rid in lst:
                v = json.loads(_get(port, f"/api/backtest/run/{rid}"))
                run_tabs[rid] = [t["label"] for t in v["tabs"]]
                tab_text[rid] = {t["label"]: t["text"] for t in v["tabs"]}
                values[rid] = v["values"]
                ext += _external("".join(t["html"] for t in v["tabs"]))
                ext += _external(_get(port, f"/backtest/run/{rid}").decode("utf-8"))
        finally:
            srv.shutdown()
            srv.server_close()
        return {"run_ids": ids, "top_tabs": top, "run_list": lst, "run_tabs": run_tabs, "tab_text": tab_text,
                "external_refs": ["".join(x) for x in ext], "values": values}
    if op == "wiring_test":
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(BATTERY / "wiring_break"), str(REPO / "src"), env.get("PYTHONPATH", "")])
        env.pop("I3_WIRING_BREAK", None)
        if inp.get("break"):
            env["I3_WIRING_BREAK"] = inp["break"]
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(WIRING_TEST)],
                           cwd=str(REPO), env=env, capture_output=True, text=True, timeout=240)
        return {"passed": r.returncode == 0}
    raise ValueError(f"unknown op {op!r}")
