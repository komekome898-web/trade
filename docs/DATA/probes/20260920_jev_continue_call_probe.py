"""Jev の呼び出しの形と遅延の下見(2026-09-20、リード実測)。合成の状態で 3 回呼ぶ。実データは使わない。
結果(確率)は data/jev/probe/ にだけ残す(リポジトリに入れない)。ここには遅延とトークン数だけ書く。"""
import time, json, sys
sys.path.insert(0, 'scripts')
from jev.client import JevClient
c = JevClient(model="jev-1.13.0", log_dir="data/jev/probe")
state = {"side": "SELL", "prints_last_60s": [{"t_rel_s": -9.0, "notional_usd": 1.6e6}, {"t_rel_s": 0.0, "notional_usd": 2.3e8}],
         "price_path_bp_last_60s": [0, -1, -3, -8, -12, -15, -19, -22, -24, -25, -26, -28], "taker_imbalance_5s": -0.95, "taker_imbalance_30s": -0.6,
         "trade_count_60s": 480, "move_since_first_print_bp": -28, "burst_ratio_10s_over_60s": 0.55}
qs = {"continue": {"type": "noul", "instructions": "Given the state of a liquidation cascade on a perpetual futures market at the moment of a liquidation print, judge whether another same-side liquidation print will occur within the next 60 seconds.",
                   "criteria": {"yes": "the cascade is likely to continue: price momentum in the liquidation direction persists and more positions are likely to be liquidated within 60 seconds", "no": "the cascade is likely to stop: the move is exhausted or absorbed and no further same-side liquidation is likely within 60 seconds"}}}
lat = []
for i in range(3):
    t = time.time(); r = c.evaluate(state, qs); lat.append(round(time.time() - t, 2))
    if i == 0: print("usage", r.get("usage"), "answer keys", list(r.get("answers", {}).keys()))
print("latency_s", lat)
