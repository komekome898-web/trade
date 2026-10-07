"""Test helper (not a test module): write a small road run (record.json, repro.json, road/ with the seven tables of
road-record-7) for the バックテスト tab's tests. The tables are made from a list of trades the test states, so the
numbers can be counted by hand. The column lists come from the SCHEMA.json of the fake runs in tests/road_fake_runs."""
from __future__ import annotations

import csv
import glob
import gzip
import io
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAKE = HERE / "road_fake_runs"
NS = 10**9
QTY = 0.1


def schema() -> dict:
    p = sorted(glob.glob(str(FAKE / "runs" / "*" / "road" / "SCHEMA.json")))[0]
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _gz_csv(path: Path, cols: list, rows: list) -> None:
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c, "") for c in cols])
    with gzip.GzipFile(filename="", mode="wb", fileobj=open(path, "wb"), mtime=0) as fh:
        fh.write(buf.getvalue().encode("utf-8"))


def trade(et, xt, ep, xp, side="buy", signal=None):
    """A round trip stated in seconds: entry time, exit time, prices, side (the position's direction)."""
    return {"et": et, "xt": xt, "ep": ep, "xp": xp, "side": side, "signal": signal}


def write_road_run(root: Path, rid: str, trades=(), group: str = "g", instrument: str = "XBTUSD", first: int = 0, last: int = 0,
                   params=None, module: str = "bot.strategy.fake_road_demo", kind: str = "bar", version: str = "road-record-7",
                   drop: str = None, data=None, ranges=("pessimistic", "optimistic"), canceled: int = 0, zero: int = 0,
                   shared: str = "backtest_runs_shared") -> str:
    """Write <root>/<shared>/<group>/<rid>/ and return the runs dir. `first` / `last` in seconds."""
    d = Path(root) / shared / group / rid
    (d / "road").mkdir(parents=True)
    sch = schema()
    sch["version"] = version
    cols = {t: [c[0] for c in sch["tables"][t]["columns"]] for t in sch["tables"]}
    tabs = {t: [] for t in ("signals", "orders", "fills", "fx", "ledger_fills", "trades")}
    summary = []
    for rg in ranges:
        ir = {"instrument": instrument, "range": rg}
        cum, fid, oid = 0.0, 0, 0
        for i, t in enumerate(trades):
            sgn = 1 if t["side"] == "buy" else -1
            sid = t["signal"] or f"s{i}"
            tabs["signals"].append({**ir, "signal_id": sid, "kind": "線の外", "direction": "long" if sgn > 0 else "short",
                                    "value_json": json.dumps({"close": t["ep"]}), "start_t_ns": (t["et"] - 60) * NS,
                                    "end_t_ns": t["xt"] * NS, "end_reason": "戻った"})
            for leg, (tt, px, sd) in enumerate([(t["et"], t["ep"], "buy" if sgn > 0 else "sell"), (t["xt"], t["xp"], "sell" if sgn > 0 else "buy")]):
                o = f"road-{oid}"
                oid += 1
                tabs["orders"].append({**ir, "order_id": o, "origin": "土台", "signal_id": sid if leg == 0 else "無し", "side": sd,
                                       "order_type": "limit", "limit_px": px, "sent_limit_px": px, "qty": QTY, "placed_t_ns": (tt - 60) * NS,
                                       "sent_t_ns": (tt - 60) * NS, "acked_t_ns": (tt - 60) * NS, "state": "FILLED", "filled_qty": QTY,
                                       "levels": 1, "exit_kind": "" if leg == 0 else "close"})
                tabs["fills"].append({**ir, "fill_id": fid, "order_id": o, "signal_id": sid if leg == 0 else "無し", "t_ns": tt * NS,
                                      "venue_t_ns": tt * NS, "side": sd, "qty": QTY, "px": px, "ccy": "JPY", "fee": 0.0, "liquidity": "maker",
                                      "fill_rule": "range_open", "fill_exit_rule": "same_bar", "fill_case": "range"})
                pnl = 0.0 if leg == 0 else (t["xp"] - t["ep"]) * QTY * sgn
                cum += pnl
                tabs["ledger_fills"].append({**ir, "fill_id": fid, "t_ns": tt * NS, "side": sd, "qty": QTY, "px": px, "ccy": "JPY",
                                             "position_after": QTY * sgn if leg == 0 else 0, "avg_px_after": t["ep"] if leg == 0 else "",
                                             "pnl_quote": pnl, "usdjpy": 1, "pnl_jpy": pnl, "pnl_jpy_cum": cum, "trade_id": i,
                                             "opens_trade_id": i if leg == 0 else ""})
                fid += 1
            tabs["trades"].append({**ir, "trade_id": i, "signal_id": sid, "first_fill_id": fid - 2, "fill_count": 2, "first_t_ns": t["et"] * NS,
                                   "last_t_ns": t["xt"] * NS, "direction": "long" if sgn > 0 else "short", "levels": 1, "max_position": QTY,
                                   "hold_ns": (t["xt"] - t["et"]) * NS, "pnl_jpy": (t["xp"] - t["ep"]) * QTY * sgn, "usdjpy": 1, "status": "closed"})
        for k in range(canceled):  # an order that was never filled: placed, then canceled
            tt = (first or 0) + 30 + k
            tabs["orders"].append({**ir, "order_id": f"road-c{k}", "origin": "土台", "signal_id": "無し", "side": "buy", "order_type": "limit",
                                   "limit_px": 1.0, "sent_limit_px": 1.0, "qty": QTY, "placed_t_ns": tt * NS, "sent_t_ns": tt * NS,
                                   "canceled_t_ns": (tt + 60) * NS, "close_kind": "cancel", "close_reason": "canceled", "state": "CANCELED",
                                   "filled_qty": 0, "levels": 1})
        for k in range(zero):
            tt = (first or 0) + 40 + k
            tabs["orders"].append({**ir, "order_id": f"road-z{k}", "origin": "土台", "signal_id": "無し", "side": "buy", "order_type": "limit",
                                   "limit_px": 1.0, "qty": 0, "placed_t_ns": tt * NS, "state": "量が 0 で出さない", "levels": 200})
        summary.append({**ir, "fill_count": 2 * len(trades), "closed_trades": len(trades),
                        "pnl_jpy": repr(round(cum, 10)), "open_trades": 0})
    for t, rows in tabs.items():
        if t == drop:
            continue
        _gz_csv(d / "road" / sch["tables"][t]["file"], cols[t], rows)
    if drop != "summary":
        (d / "road" / "summary.json").write_text(json.dumps({"groups": [[instrument, r] for r in sorted(ranges)], "rows": summary,
                                                           "version": version}), encoding="utf-8")
    (d / "road" / "SCHEMA.json").write_text(json.dumps(sch, ensure_ascii=False), encoding="utf-8")
    eng = {r: {instrument: {"first_time_ns": first * NS, "last_time_ns": last * NS}} for r in ranges}
    rec = {"config": {"instrument": instrument, "instruments": [{"name": instrument}],
                      "strategy": {"kind": "module", "module": module, "factory": "pipeline_strategy",
                                   "module_source_sha256": "a" * 64, "params": params or {"levels": 3}}},
           "data": data if data is not None else [], "engine": eng, "git_sha": "a" * 40, "diff_hash": "b" * 64, "purpose": "動作確認",
           "setup": {"name": "bot.bt.pipeline:module"}}
    (d / "record.json").write_text(json.dumps(rec), encoding="utf-8")
    (d / "repro.json").write_text("{}", encoding="utf-8")
    return str(Path(root) / shared)
