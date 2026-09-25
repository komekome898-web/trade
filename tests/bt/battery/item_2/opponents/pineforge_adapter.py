"""Survey candidate 70 `PineForge` (github pineforge-4pass/pineforge-engine, commit 5e62602c; built here with its own
CMake -- install record venvs/item_2/logs/i2_r1_scenekeeper_install_70.log) for the item 2 battery, driven by a small C
program against the tool's native C API (venvs/item_2/drivers/i2drv70.c, built against the tool's static libraries):
`strategy_native_host_create_v1` (callbacks on_bar / on_applied), `strategy_configure_native_v1` (time frame, price
tick, capital, fee kind / value, close execution NEXT_ELIGIBLE_POINT), `strategy_native_run_v1` (the bars),
`strategy_native_submit_v1` (intent TRANSACT with signed units; trigger MARKET / LIMIT p1 / STOP p1) and
`strategy_native_cancel_v1` from inside on_bar, and the kernel's event history `strategy_native_events_v1`
(accepted 1 / rejected 2 / cancelled 5 / applied 10).

The tool takes OHLCV bars only (pf_bar_t, time = the bar's open in Unix milliseconds), each on a slot of the configured
time frame.  Bars come from i2_common.bar_rows; only scenes whose bars have a span (the scene's own bars or a tier-2
scene's declared bars) are run: a bar per trade print at the print's time was refused by the kernel when tried
("ERROR run rc=-11 native confirmed bar timestamp is not a canonical slot label", driver of item 0 with tf=1S and bars
at 0 / 10 / 20 ms).  Actions are submitted in the on_bar call of the bar chosen by i2_common.issue_schedule; a fill
is an on_applied record (the kernel's resolved price, opened units, and the point's effective time in ms).
Fill model: none / tier 2 -> the kernel's own bar matching.  Costs are not passed (the scenes it runs have none).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

TOOL = "PineForge(5e62602c) native C API"
EXE = "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_2/drivers/i2drv70"
TF = {1_000_000_000: "1S", 60_000_000_000: "1", 3_600_000_000_000: "60", 86_400_000_000_000: "1D"}
MS = 1_000_000


class Adapter:
    name = "opp_pineforge"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit", "stop", "cancel"), events=("book", "trade", "bar"),
               fill_models=C.bar_fill_models, costs=(), account=("cash",))
        bars, src = C.bar_rows(inp)
        spans = {b["span_ns"] for b in bars}
        if not bars or 0 in spans:
            raise NotExpressible(f"{TOOL}: 相場の入力は時間枠の区切りに乗った足だけで、約定 1 件ごとの足(約定の時刻)は核が拒む"
                                 "(ERROR run rc=-11 native confirmed bar timestamp is not a canonical slot label)")
        if len(spans) != 1 or next(iter(spans)) not in TF:
            raise NotExpressible(f"{TOOL}: 足の幅 {sorted(spans)} ns に当たる時間枠の文字が無い(使うのは {sorted(TF.values())})")
        span = next(iter(spans))
        sched = C.issue_schedule(bars, inp["actions"])
        args = [f"tf={TF[span]}", f"tick={inp['product']['tick']}", f"capital={inp['account']['cash']}"]
        idx = {}
        n = 0
        for k, acts in sorted(sched.items()):
            for a in acts:
                if a["op"] == "place":
                    trig, p1 = {"market": (0, 0.0), "limit": (1, a["px"]), "stop": (2, a["stop_px"])}[a["type"]]
                    args.append(f"act={k + 1}:{a['side'][0]}:{trig}:{p1}:0:{a['qty']}")
                    idx[n] = a
                    n += 1
                elif a["op"] == "cancel":
                    j = next(i for i, x in idx.items() if x["ref"] == a["ref"])
                    args.append(f"cxl={k + 1}:{j}")
                else:
                    raise NotExpressible(f"{TOOL}: 操作 {a['op']} の口が無い")
        args.append("--")
        args += [f"{(b['t'] - b['span_ns']) // MS}:{b['o']}:{b['h']}:{b['l']}:{b['c']}:{b['v']}" for b in bars]
        r = subprocess.run([EXE, *map(str, args)], capture_output=True, text=True, timeout=60)
        rows = [ln.split() for ln in r.stdout.splitlines() if ln.strip()]
        err = [" ".join(x) for x in rows if x[0] == "ERROR"]
        if r.returncode != 0 or err:
            raise Refused(f"rc={r.returncode} {' / '.join(err)} {r.stderr[-200:]}")
        kv = lambda row: dict(x.split("=", 1) for x in row if "=" in x)  # noqa: E731
        inc2ref = {}
        for x in rows:
            if x[0] == "SUBMIT":
                d = kv(x)
                if d["rc"] == "0":
                    inc2ref[d["inc"]] = idx[int(x[1])]["ref"]
                else:
                    inc2ref["rej" + x[1]] = idx[int(x[1])]["ref"]
        rec = {"orders": {}, "fills": []}
        for x in rows:
            if x[0] == "APPLIED":
                d = kv(x)
                ref = inc2ref.get(d["inc"])
                if ref:
                    rec["fills"].append({"ref": ref, "t": int(d["eff"]) * MS, "px": float(d["price"]),
                                         "qty": abs(float(d["opened"])), "liq": None})
        kinds = {}
        for x in rows:
            if x[0] == "EV":
                d = kv(x)
                if d["inc"] in inc2ref:
                    kinds.setdefault(inc2ref[d["inc"]], []).append(int(d["kind"]))
        for i, a in idx.items():
            ref = a["ref"]
            ks = kinds.get(ref, [])
            got = sum(f["qty"] for f in rec["fills"] if f["ref"] == ref)
            if 2 in ks or ref not in inc2ref.values():
                st = "rejected"
            elif abs(got - a["qty"]) <= 1e-12:
                st = "filled"
            elif 5 in ks:
                st = "canceled"
            else:
                st = "open"
            rec["orders"][ref] = {"status": st}
        return rec


TARGET = Adapter()
