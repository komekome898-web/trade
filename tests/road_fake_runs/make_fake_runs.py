"""作り物の走らせを作る: 本物の FX_BTC_JPY の 1 分足(封印の前)に、作り物の戦略を道で走らせる。"""
import csv, gzip, importlib.util, importlib, json, os, sys, datetime as dt
SRC = sys.argv[1]; OUT = sys.argv[2]
sys.path.insert(0, SRC)
from bot.bt import pipeline as P
from bot.bt.core import BarEvent
HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = "bot.strategy.fake_road_demo"
SCENE = "bot.strategy.road_scene_test"
spec = importlib.util.spec_from_file_location(MODULE, os.path.join(HERE, "fake_road_demo.py"))
mod = importlib.util.module_from_spec(spec); sys.modules[MODULE] = mod; spec.loader.exec_module(mod)
spec2 = importlib.util.spec_from_file_location(SCENE, os.path.join(HERE, "road_scene_strategy.py"))
mod2 = importlib.util.module_from_spec(spec2); sys.modules[SCENE] = mod2; spec2.loader.exec_module(mod2)
REAL = "/home/user/trade/backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
_cache = {}
def real_rows(year):
    if year not in _cache:
        rows = []
        with gzip.open(f"{REAL}/candles_1m_{year}.csv.gz", "rt") as fh:
            for r in csv.DictReader(fh):
                if not r['open'] or not r['close']: continue
                t = int(dt.datetime.fromisoformat(r["ts"]).timestamp()) * 10**9
                rows.append((t, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"])))
        _cache[year] = rows
    return _cache[year]
def gen(seed, params):  # 作り物: 乱数でなく本物の足を読む(走らせの記録の generator の欄は random_walk のまま)
    year = dt.datetime.fromtimestamp(params["start_ns"] / 1e9, dt.timezone.utc).year
    rows = [r for r in real_rows(year) if r[0] >= params["start_ns"]][: params["n"]]
    out, ev = [], []
    for t, o, h, l, c, v in rows:
        out.append({"t_ns": t, "open": o, "high": h, "low": l, "close": c, "volume": v})
        ev.append(BarEvent(received_time_ns=t + params["step_ns"], start_time_ns=t, open=o, high=h, low=l, close=c, volume=v))
    return "bar", out, ev
P.GENERATORS["random_walk"] = gen
ZERO = {"kind": "constant", "ns": 0}
M = 60 * 10**9
def go(start, n, params, runs_dir, module=MODULE):
    t0 = int(dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc).timestamp()) * 10**9
    g = {"name": "random_walk", "seed": 1, "params": {"kind": "bar", "start_ns": t0, "step_ns": M, "n": n, "price0": 1.0, "step_pct": 0.0, "qty": 1.0}}
    sym = "FX_BTC_JPY"
    fill = {"optimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "same_bar"},
            "pessimistic": {"tier": 2, "bar_rule": "range_open", "attached_exit": "next_bar"}}
    plan = P.plan_pipeline(root=OUT, datasets=[{"name": "g", "generator": g}],
        instruments=[{"name": sym, "price": "g", "with": [], "product": {"symbol": sym, "venue": "bitflyer", "tick": 1.0, "min_qty": 0.001, "qty_step": 0.001, "quote_ccy": "JPY", "margin": True}, "rules": {"market_ref": "next_bar_open", "self_trade": "cancel_taker", "off_step": "round_down", "below_min_qty": "reject"}}],
        strategy={"kind": "module", "module": module, "factory": "pipeline_strategy", "params": {"quote_ccy": "JPY", **params}},
        fill=fill, latency={"feed": ZERO, "order": ZERO, "cancel": ZERO, "notice": ZERO},
        costs={"maker_rate": 0, "taker_rate": 0, "spread": 0, "source": "作り物: 0"},
        account={"currency": "JPY", "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None, "margin_check": "position_only"},
        purpose="動作確認", prereg=None, repo="/home/user/trade")
    res = P.run_pipeline(plan, runs_dir=runs_dir)
    print(res.run_dir)
    return res
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rd = os.path.join(OUT, "fake_runs")
    go("2020-03-11T00:00:00", 4320, {"levels": 3, "window": 40, "k": 1.5}, rd)
    go("2020-03-11T00:00:00", 4320, {"levels": 5, "window": 40, "k": 1.5}, rd)
    go("2020-03-11T00:00:00", 4320, {"levels": 3, "window": 50, "k": 1.3, "zero_every": 5, "with_exit": True}, rd)
    go("2020-03-11T00:00:00", 4320, {"quote_ccy": "JPY", "mode": "ladder", "levels": 2, "open_bar": 100, "close_bar": 400}, rd, module=SCENE)
