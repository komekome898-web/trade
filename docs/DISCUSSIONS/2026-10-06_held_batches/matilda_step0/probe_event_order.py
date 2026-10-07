"""道の走らせで、足の閉じる時刻に戦略へ届く出来事の順を並べる(マチルダの委任文の「読んだ事実」の確かめ)。

1 分足の約定の決まりの試しの戦略(`tests/road/road_l769_strategy.py`、with_exit)に合成の足 8 本を流し、足ごとに同じ時刻の
タイマーを置いて、届いた出来事(種類・T0 からの秒・注文の番号かタグ)を楽観側の 1 回分だけ出す。tmp の根に書き、リポジトリの
市場のデータは読まない。使い方: `PYTHONPATH=src python3 docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/probe_event_order.py`
"""
import importlib.util
import os
import sys
import tempfile
from datetime import datetime, timezone

from bot.bt import pipeline as P
from bot.bt.core import BarEvent

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NAME = "bot.strategy.road_l769_probe"
spec = importlib.util.spec_from_file_location(NAME, os.path.join(ROOT, "tests", "road", "road_l769_strategy.py"))
mod = importlib.util.module_from_spec(spec)
sys.modules[NAME] = mod
spec.loader.exec_module(mod)
T0 = 1_699_999_800
SPEC = {"format": "csv", "header": True, "delimiter": ",", "compression": "none", "kind": "bar", "symbol": "FX_BTC_JPY",
        "asset": "crypto", "time": {"columns": ["start_ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
        "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}
root = tempfile.mkdtemp()
os.makedirs(os.path.join(root, "backtest_data", "m"))
with open(os.path.join(root, "prereg.md"), "w", encoding="utf-8") as fh:
    fh.write("# probe\n")
bars = [(7000400, 7000500, 7000400, 7000500), (7000500, 7000500, 7000400, 7000400)] * 3 + \
       [(7000400, 7000400, 7000000, 7000000), (7000000, 7000200, 6999900, 7000100)]
lines = ["start_ts,o,h,l,c,vol"] + [
    f"{datetime.fromtimestamp(T0 + i * 60, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')},{o},{h},{l},{c},1.0"
    for i, (o, h, l, c) in enumerate(bars)]
with open(os.path.join(root, "backtest_data", "m", "bars.csv"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
ZERO = {"kind": "constant", "ns": 0}
plan = P.plan_pipeline(
    root=root, datasets=[{"name": "b", "paths": ["backtest_data/m/bars.csv"], "spec": SPEC, "origin": "real"}],
    instruments=[{"name": "FX_BTC_JPY", "price": "b", "with": [],
                  "product": {"symbol": "FX_BTC_JPY", "venue": "bitflyer", "tick": 1.0, "min_qty": 0.001,
                              "qty_step": 0.001, "quote_ccy": "JPY", "margin": True},
                  "rules": {"market_ref": "next_bar_open"}}],
    strategy={"kind": "module", "module": NAME, "factory": "pipeline_strategy",
              "params": {"mode": "with_exit", "quote_ccy": "JPY", "levels": 2, "open_bar": 7, "limit_px": 7000050.0,
                         "exit_px": 7000150.0}},
    fill={"optimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "same_bar"},
          "pessimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "next_bar"}},
    latency={"feed": ZERO, "order": ZERO, "cancel": ZERO, "notice": ZERO},
    costs={"maker_rate": 0, "taker_rate": 0, "spread": 0, "source": "probe: 0"},
    account={"currency": "JPY", "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None,
             "margin_check": "position_only"},
    purpose="研究", prereg="prereg.md")
log = []
orig = mod.L769Strategy.step


def step(self, event, ctx):
    log.append((type(event).__name__, int(ctx.now_ns) // 10**9 - T0,
                getattr(event, "client_order_id", "") or getattr(event, "tag", "")))
    if isinstance(event, BarEvent):
        ctx.set_timer(int(ctx.now_ns), "decide")
    return orig(self, event, ctx)


mod.L769Strategy.step = step
out = os.path.join(root, "out")
os.makedirs(out)
P.execute_once(plan, out)
starts = [i for i, x in enumerate(log) if x == ("ClockEvent", 0, "")]
for x in log[:starts[1] if len(starts) > 1 else len(log)]:
    if x[1] >= 420:
        print(x)
