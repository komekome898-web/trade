#!/usr/bin/env python3
"""単純な測りの道(`bot.bt.simple`)の約定の列 `fills.csv.gz` から、分析の読み口(`diag_tables.py`・`diag_paths.py`)が
読む取引の行 `trades.csv.gz` と `summary.json` を作る読み台本(リードが書いた。委任・批評家を通していない。
相方の指摘 P-7、`docs/RESEARCH/partner/2026-10-09_matilda_main_base/01_P_reply.md`)。

取引の区切り・損益・段の数は帳簿のツール `bot.bt.road.ledger.book` が出す(この台本は計算しない)。
建玉が 0 に戻るまでの約定を 1 つの塊として book に渡す(`bot.bt.simple.run.summarize` と同じ切り方)。
検め: 閉じた取引の数・途中の取引の数・損益の円の合計(文字列)が、走らせの `summary.json` と一致しなければ止まる。

出す列(1 行 = 閉じた取引 1 つ。途中の取引は出さない):
  signal_t   1 段目が約定した足の始まり(= 直前の足の終値で線を置いた時点。L-879 の 1 段目は足の途中で約定する)
  entry_t    1 段目が約定した足の終わり(signal_t + 1 分。diag_paths の「entry_t は約定した足の終わり」に合わせる)
  exit_t     最後の約定(建玉が 0 に戻った約定)の足の終わり
  side       +1 買い / −1 売り
  entry_price 1 段目の約定の値段
  pnl_jpy    損益(円、帳簿のツールの値。経費の前)
  exit_reason 最後の約定の kind(close = 利確の指値 / market = 時間切れの成行 / break = ブレイクの逆指値 / level・entry)
  levels     段の数(帳簿のツール)
  qty1       1 段目の量(BTC)
  late_levels 最初の約定から 20 分(alert_count)を越えて約定した段の数

    PYTHONPATH=src python3 scripts/analysis/simple_trades.py --run <走らせの置き場> --out <出力の置き場> [--alert-min 20]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from bot.bt.road.ledger import book
from bot.bt.simple.common import to_ns

MIN = 60 * 10**9


def _iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--alert-min", type=float, default=20.0)
    a = ap.parse_args()
    with open(os.path.join(a.run, "summary.json"), encoding="utf-8") as fh:
        want = json.load(fh)
    with open(os.path.join(a.run, "run.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    os.makedirs(a.out, exist_ok=True)
    closed = open_tr = 0
    total = Decimal(0)
    out_rows = []
    chunk, kinds = [], []
    pos = Decimal(0)

    def flush():
        nonlocal closed, open_tr, total
        if not chunk:
            return
        led = book(chunk)
        s = led.summary
        closed += s["closed_trades"]
        open_tr += s["open_trades"]
        total += Decimal(s["pnl_jpy"])
        # 塊は建玉 0 → 0 なので、ドテンが無ければ取引は 1 つ。ドテンがあれば止める(マチルダはドテンしない作り)
        if len(led.trades) != 1:
            raise SystemExit(f"止める: 1 つの塊に取引が {len(led.trades)} 個(ドテン)。この台本は扱わない")
        tr = led.trades[0]
        if tr["status"] == "closed":
            t0 = chunk[0]["t_ns"]
            side = 1 if tr["direction"] == "long" else -1
            pnl = Decimal(tr["pnl_jpy"])
            late = sum(1 for f, k in zip(chunk, kinds)
                       if k in ("level", "entry") and f["t_ns"] - t0 > a.alert_min * MIN)
            out_rows.append([_iso(t0), _iso(t0 + MIN), _iso(chunk[-1]["t_ns"] + MIN), side, chunk[0]["px"],
                             format(pnl, "f"), kinds[-1], tr["levels"], chunk[0]["qty"],
                             late])
        chunk.clear()
        kinds.clear()

    with gzip.open(os.path.join(a.run, "fills.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            q = Decimal(r["qty"])
            chunk.append({"t_ns": to_ns(r["ts"]), "side": r["side"], "qty": float(q), "px": float(r["px"]), "ccy": "JPY"})
            kinds.append(r["kind"])
            pos += q if r["side"] == "buy" else -q
            if pos == 0:
                flush()
    flush()
    got = {"closed_trades": closed, "open_trades": open_tr, "pnl_jpy": format(total.normalize(), "f") if total else "0"}
    for k, v in got.items():
        if str(want[k]) != str(v):
            raise SystemExit(f"止める: {k} が summary.json と違う(台本 {v} / summary.json {want[k]})")
    with gzip.open(os.path.join(a.out, "trades.csv.gz"), "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["signal_t", "entry_t", "exit_t", "side", "entry_price", "pnl_jpy", "exit_reason", "levels",
                    "qty1", "late_levels"])
        w.writerows(out_rows)
    seal = meta["seal"]
    p0 = datetime.fromisoformat(out_rows[0][0]).date().isoformat() + "T00:00:00Z"
    summ = {"source_run": a.run, "git": meta.get("git"), "params": meta.get("params"), "period": [p0, seal],
            "all": {"trades": len(out_rows), "sum_jpy": got["pnl_jpy"]},
            "check": {"closed_trades": closed, "open_trades": open_tr, "pnl_jpy": got["pnl_jpy"], "matches_summary": True}}
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summ, fh, ensure_ascii=False, indent=1)
    print(json.dumps(summ["check"], ensure_ascii=False))


if __name__ == "__main__":
    main()
