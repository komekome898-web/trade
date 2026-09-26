"""Reproduction of survey candidate 15 `Mendl-Labs/BacktestingCore` -- `CandleSimulator::run` (the bar simulator) --
for the item 4 battery.  Not built here: a Rust workspace whose crates need credentials to fetch
(tests/bt/battery/item_3/opponents/CONSIDERED.md row 15; item 3 reproduced its validation parts:
tests/bt/battery/item_3/opponents/repro_15_backtestingcore.py).

Primary source (read only), commit f8d81ee0b4b65f6fbbf205d011ad2e815054fbc7:
  https://github.com/Mendl-Labs/BacktestingCore/blob/f8d81ee0b4b65f6fbbf205d011ad2e815054fbc7/backtest/src/candle_sim.rs
  https://github.com/Mendl-Labs/BacktestingCore/blob/f8d81ee0b4b65f6fbbf205d011ad2e815054fbc7/config/src/lib.rs
Rules taken (candle_sim.rs unless named):
- `run(signals, candles, stop_loss_pct, take_profit_pct, position_size_pct, ...)` (290-298) walks bars i = 0..n-1;
  on bar i it first checks the open position's stop loss / take profit on bar i (439-521), then the signal of bar i
  is filled at the NEXT bar's open, or at bar i's close when i is the last bar (523-530), booked in this same step.
- Stop loss: triggered when low <= entry x (1 - sl) (long; high >= entry x (1 + sl) short); its base price is the
  open when the open is already past the level, else the level (446-466).  Take profit: high >= entry x (1 + tp)
  (low <= entry x (1 - tp) short) at the level (468-479).  Both on one bar: with the default `RealismConfig`
  (intrabar_path: false, 170-184) the stop loss wins (the `if sl_triggered ... else if tp_triggered`, 484-521).
- BUY when the position is <= 0: close a short, then open a long; SELL when >= 0: close a long, then open a short
  (548-661, the tool has no switch that forbids shorts); CLOSE closes (662-676).  The size is equity x
  position_size_pct / fill price (565-592); the entry commission = size value x rate (593); the exit
  commission = exit value x rate, and each closed trade's PnL (exit PnL minus the exit commission) is pushed to
  trade_returns (close_position_with_commission 805-845).
- Fill prices move by the flat slippage in basis points (apply_fill_costs 758-795 with `SlippageModel::Flat`,
  config/src/lib.rs 270-302; market impact, range spread and adverse selection are 0 / off by default, 170-184).
- A fill is capped at fill_volume_fraction x bar volume (584-590, default 0.10 at 237); the scene's bars carry volume
  1, so the fraction is set with the tool's own `with_fill_volume_fraction` (254-257) to a value that does not bind.
- Funding: every 8-hour interval, position value x funding_rate_8h (382-395; `with_funding_rate` 259-263).  The
  scene's daily rate is handed as funding_rate_8h = daily / 3.
- Any open position is closed at the last close (704-720).  The equity curve is cash + margin + unrealized PnL at the
  close of every bar (680-690).
Observed here: `pnls` = the tool's trade_returns (each closed trade's PnL) and `equity` = its equity curve, both
outputs of the tool; `fills` are the simulator's internal fill prices and quantities (entry_price / position_qty at
each booking) -- the tool's result (CandleSimResult) has no fill list, so this is an instrumentation of the rewrite,
not an output of the tool.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i4_base import Base, adj, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

SRC = "backtest/src/candle_sim.rs(f8d81ee0)"


class BacktestingCore(Base):
    name = "opp_repro_15_backtestingcore"
    TOOL = "BacktestingCore CandleSimulator(f8d81ee0)(再現)"
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "take_profit_pct", "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct",
                "swap_daily_pct"}
    MISSING = {k: f"指値の注文が無い(合図は BUY / SELL / CLOSE / HOLD の 4 つで、約定は次の足の始値: {SRC} 525-530 行)"
               for k in ("execution", "exit_execution", "maker_tp_pct")}
    METRICS = "再現していない: CandleSimResult の指標(Sharpe は compute_sharpe 846 行)は 12 の指標と同じ形ではない"
    SPLIT = "行の割合で分ける口は candle_sim.rs に無い(walk-forward の crate は項目 3 で再現した)"
    PIPELINE = "再現は足の模擬器だけ"

    def extra_gate(self, inp):
        cfg = inp["config"]
        c = cfg["costs"]
        out = []
        if c["maker_fee_pct"] != c["taker_fee_pct"] and (cfg["take_profit_pct"]):
            out.append("手数料の率は commission_rate 1 つで、maker と taker に別の率を置く口が無い(232-247 行)")
        if "metrics" in set(inp.get("want") or []):
            out.append(self.METRICS)
        return out

    def bars(self, inp):
        cfg = inp["config"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        rate = cfg["costs"]["taker_fee_pct"] / 100
        bps = adj(cfg["costs"]) * 10000
        sl = cfg["stop_loss_pct"] / 100 if cfg["stop_loss_pct"] else None
        tp = cfg["take_profit_pct"] / 100 if cfg["take_profit_pct"] else None
        pct = cfg["order_notional"] / cfg["initial_equity"]
        f8 = cfg["swap_daily_pct"] / 100 / 3 if cfg["swap_daily_pct"] else 0.0
        interval_ns = 8 * 3600 * 10**9
        cash = cfg["initial_equity"]
        qty = 0.0
        entry = 0.0
        margin = 0.0
        last_funding = bars[0]["t_ns"]
        fills, pnls, equity = [], [], []
        # the strategy's own plan: signals mapped to the tool's four actions from its own view of the position
        plan = self.plan(cfg, bars, sig)

        def fill_px(p, buy):
            s = p * bps / 10000
            return p + s if buy else p - s

        def close_pos(fp, bar):
            nonlocal cash, qty, entry, margin
            q = abs(qty)
            com = q * fp * rate
            pnl = (fp - entry) * qty - com
            cash += margin + pnl
            fills.append({"bar": bar, "side": "CLOSE_LONG" if qty > 0 else "CLOSE_SHORT", "price": fp, "size": q})
            pnls.append(pnl)
            qty, entry, margin = 0.0, 0.0, 0.0

        def open_pos(base, bar, buy):
            nonlocal cash, qty, entry, margin
            eq = cash + margin + (qty * (base - entry) if qty else 0.0)
            size_value = eq * pct
            fp = fill_px(base, buy)
            q = size_value / fp
            com = size_value * rate
            cash -= size_value + com
            margin = size_value
            qty = q if buy else -q
            entry = fp
            fills.append({"bar": bar, "side": "OPEN_LONG" if buy else "OPEN_SHORT", "price": fp, "size": q})

        for i in range(n):
            b = bars[i]
            if qty != 0.0 and f8 > 0.0:
                el = b["t_ns"] - last_funding
                if el >= interval_ns:
                    periods = el // interval_ns
                    cash -= abs(qty) * b["close"] * f8 * periods
                    last_funding += periods * interval_ns
            if qty != 0.0:
                long_ = qty > 0
                slt = tpt = False
                if sl is not None:
                    lvl = entry * (1 - sl) if long_ else entry * (1 + sl)
                    if (b["low"] <= lvl) if long_ else (b["high"] >= lvl):
                        slb = b["open"] if (long_ and b["open"] < lvl) or (not long_ and b["open"] > lvl) else lvl
                        slt = True
                if tp is not None:
                    tlv = entry * (1 + tp) if long_ else entry * (1 - tp)
                    if (b["high"] >= tlv) if long_ else (b["low"] <= tlv):
                        tpt = True
                if slt:
                    close_pos(fill_px(slb, not long_), i)
                elif tpt:
                    close_pos(fill_px(tlv, not long_), i)
            a = plan.get(i)
            nb, fb = (i + 1, bars[i + 1]["open"]) if i + 1 < n else (i, b["close"])
            if a == "BUY" and qty <= 0.0:
                if qty < 0.0:
                    close_pos(fill_px(fb, True), nb)
                open_pos(fb, nb, True)
            elif a == "SELL" and qty >= 0.0:
                if qty > 0.0:
                    close_pos(fill_px(fb, False), nb)
                open_pos(fb, nb, False)
            elif a == "CLOSE" and qty != 0.0:
                close_pos(fill_px(fb, qty < 0), nb)
            equity.append(cash + margin + (qty * (b["close"] - entry) if qty else 0.0))
        if qty != 0.0:
            close_pos(fill_px(bars[-1]["close"], qty < 0), n - 1)
        return want(inp, {"fills": fills, "pnls": pnls, "equity": equity})

    @staticmethod
    def plan(cfg, bars, sig):
        """The signal array the strategy hands the tool (it is computed before the run, from bars 0..i and from the
        strategy's own signals: the tool's stop loss / take profit exits are not visible to it)."""
        out = {}
        pos, entry_bar, lvl = 0, None, None
        n = len(bars)
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        for i in range(n):
            s = sig.get(i)
            if pos and N is not None and i + 1 - entry_bar >= N:
                out[i] = "CLOSE"; pos = 0; continue
            if pos and lvl is not None and ((bars[i]["close"] < lvl) if pos > 0 else (bars[i]["close"] > lvl)):
                out[i] = "CLOSE"; pos = 0; continue
            if not s:
                continue
            if pos and (s == "CLOSE" or (s == "BUY") != (pos > 0)):
                out[i] = "CLOSE"; pos = 0; continue
            if pos or s == "CLOSE":
                continue
            if s == "SELL" and not cfg["allow_short"]:
                continue
            if cfg["entry_sides"] == "long" and s == "SELL" or cfg["entry_sides"] == "short" and s == "BUY":
                continue
            if cfg["entry_mask"] is not None and not cfg["entry_mask"][i]:
                continue
            out[i] = s
            pos = 1 if s == "BUY" else -1
            entry_bar = i + 1
            if W:
                win = bars[max(0, entry_bar - W):entry_bar]
                lvl = min(x["low"] for x in win) if pos > 0 else max(x["high"] for x in win)
            else:
                lvl = None
        return out


TARGET = BacktestingCore()
