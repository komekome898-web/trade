"""Survey candidate 70 `PineForge` (github pineforge-4pass/pineforge-engine, commit 5e62602c; built in item 2 with its own
CMake, install record venvs/item_2/logs/i2_r1_scenekeeper_install_70.log) for the item 4 battery, driven by item 2's C
program against the tool's native C API (venvs/item_2/drivers/i2drv70, source i2drv70.c next to it):
`strategy_native_host_create_v1` (on_bar / on_applied), `strategy_configure_native_v1` (time frame, price tick, capital,
fee kind / value, close execution NEXT_ELIGIBLE_POINT, both directions), `strategy_native_run_v1` (the bars),
`strategy_native_submit_v1` (intent TRANSACT with signed units, trigger MARKET) from inside on_bar, and the on_applied
records (the kernel's resolved price, opened units, effective time).

The driver takes its requests on its command line (act=CALL:SIDE:TRIG:P1:P2:QTY), so the strategy's requests are fixed
before the run: the adapter decides them bar by bar from the script and from what the strategy itself sent (a
market request sent at call k is filled by the kernel at the next eligible point, so the strategy's own position is
known from its own requests); an entry is sized with the decision bar's close (qty = notional / close[k]).  A request
whose effect depends on a fill the strategy has not seen (a resting limit, a stop at the entry's fill price) cannot
be put on the command line: execution "maker", stop_loss, take_profit and maker_tp are NotExpressible for this driver
(the tool's C API itself has LIMIT / STOP triggers: pf_native_trigger_t, used by item 2).  Also not expressible: slippage /
spread (the run spec has fee kind / value only), a maker fee different from the taker fee, swap, per-trade PnL (the report
gives each trade's entry, quantity and commission, not the exit), per-bar equity, missed fills, metrics, op metrics /
split / pipeline, reference, models.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible, Refused, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

EXE = "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_2/drivers/i2drv70"
NO_REACT = ("この driver は要求を走らせる前に決めるので、約定を見てから置く注文(待つ指値・約定値からの逆指値・利確)を渡せない"
            "(道具の C API には LIMIT / STOP の trigger がある: 項目 2 の driver が使った)")


class PineForgeAdapter(Base):
    name = "opp_pineforge"
    TOOL = "PineForge (commit 5e62602c, native C API)"
    SUPPORTS = {"allow_short", "taker_fee_pct", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars"}
    MISSING = {"slippage_pct": "滑りの口を探したが無い(run spec は fee kind / value だけ: i2drv70.c 80-85 行)",
               "spread_pct": "スプレッドの口を探したが無い", "maker_fee_pct": NO_REACT, "execution": NO_REACT,
               "stop_loss_pct": NO_REACT, "take_profit_pct": NO_REACT, "exit_execution": NO_REACT, "maker_tp_pct": NO_REACT,
               "swap_daily_pct": "持ち越しの口を探したが無い"}
    METRICS = "12 の指標を出す口を探したが無い(report は取引の一覧)"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = "入力は足(pf_bar_t)の列だけで、約定・気配・板・ファイルの宣言・目的つきの書き出し・ダッシュボードの口が無い"

    def extra_gate(self, inp):
        out = []
        w = set(inp.get("want") or [])
        for k, why in (("pnls", "決済ごとの損益の口を探したが無い(report の取引は entry・qty・commission)"),
                       ("equity", "足ごとの資産の推移の口を探したが無い"), ("missed_fills", NO_REACT), ("metrics", self.METRICS)):
            if k in w:
                out.append(why)
        if int(inp["bar_seconds"]) not in (60, 3600):
            out.append("足の幅: 1 分・1 時間だけを渡す")
        return out

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        acts, tags = [], []
        pos, entry_bar, level = 0.0, None, None

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            return mask is None or bool(mask[db])

        for k in range(n - 1):  # a request at the last bar has no next point
            cl = bars[k]["close"]
            act = None
            if pos and entry_bar is not None:
                if (N is not None and k + 1 - entry_bar >= N) or \
                        (level is not None and k >= entry_bar and ((cl < level) if pos > 0 else (cl > level))):
                    act = ("s" if pos > 0 else "b", abs(pos), "CLOSE_LONG" if pos > 0 else "CLOSE_SHORT")
            s = sig.get(k)
            if act is None and s:
                if s == "CLOSE" or (s == "BUY" and pos < 0) or (s == "SELL" and pos > 0):
                    if pos:
                        act = ("s" if pos > 0 else "b", abs(pos), "CLOSE_LONG" if pos > 0 else "CLOSE_SHORT")
                elif pos == 0 and entry_ok(k, s) and (s == "BUY" or cfg["allow_short"]):
                    q = cfg["order_notional"] / cl
                    act = ("b" if s == "BUY" else "s", q, "OPEN_LONG" if s == "BUY" else "OPEN_SHORT")
            if act is None:
                continue
            side, q, tag = act
            acts.append(f"act={k + 1}:{side}:0:0:0:{q!r}")
            tags.append(tag)
            if tag.startswith("OPEN"):
                pos = q if side == "b" else -q
                entry_bar = k + 1
                if W is not None:
                    lo = max(0, entry_bar - W)
                    level = (min(bars[j]["low"] for j in range(lo, entry_bar)) if pos > 0 else
                             max(bars[j]["high"] for j in range(lo, entry_bar))) if entry_bar > lo else None
            else:
                pos, entry_bar, level = 0.0, None, None
        if len(acts) > 16:
            raise NotExpressible(f"{self.TOOL}: driver は要求を 16 まで受ける(i2drv70.c 13 行 MAXA)。この入力は {len(acts)}")
        tf = "1" if int(inp["bar_seconds"]) == 60 else "60"
        args = [EXE, f"tf={tf}", f"capital={float(cfg['initial_equity'])!r}", "tick=1e-8", "fee_kind=0",
                f"fee_value={float(c['taker_fee_pct'])!r}"] + acts + ["--"] + \
               [f"{b['t_ns'] // 10**6}:{b['open']!r}:{b['high']!r}:{b['low']!r}:{b['close']!r}:{b['volume']!r}" for b in bars]
        import os
        if not os.path.exists(EXE):
            raise NotExpressible(f"{self.TOOL}: 項目 2 の driver({EXE})と道具の clone(venvs/item_2/src/c70)が scratchpad から消えていて"
                                 "(他の役の容量の片付け。この役は消していない)、道具を呼べない。構築し直しはこの周の持ち越し")
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=120)
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from exc
        out = r.stdout.splitlines()
        err = [ln for ln in out if ln.startswith("ERROR")]
        if err:
            raise Refused(" / ".join(err)[:400])
        inc2act = {}
        for ln in out:
            if ln.startswith("SUBMIT"):
                p = ln.split()
                i = int(p[1]); d = dict(x.split("=") for x in p[2:])
                if d.get("rc") != "0":
                    raise Refused(f"submit rc={d.get('rc')} reject={d.get('reject')}")
                inc2act[d["inc"]] = i
        ms2k = {b["t_ns"] // 10**6: k for k, b in enumerate(bars)}
        fills = []
        for ln in out:
            if ln.startswith("APPLIED"):
                d = dict(x.split("=") for x in ln.split()[1:])
                i = inc2act.get(d["inc"])
                fills.append({"bar": ms2k.get(int(d["eff"])), "side": tags[i] if i is not None else None,
                              "price": float(d["price"]), "size": abs(float(d["opened"])) if float(d["opened"]) else None})
        # the size of a close is the quantity the request carried (opened units are 0 for a close)
        for f, i in zip(fills, [inc2act.get(dict(x.split("=") for x in ln.split()[1:])["inc"]) for ln in out if ln.startswith("APPLIED")]):
            if f["size"] is None and i is not None:
                f["size"] = abs(float(acts[i].split(":")[-1]))
        fills.sort(key=lambda f: (f["bar"] if f["bar"] is not None else -1, 0 if str(f["side"]).startswith("CLOSE") else 1))
        return want(inp, {"fills": fills})


TARGET = PineForgeAdapter()
