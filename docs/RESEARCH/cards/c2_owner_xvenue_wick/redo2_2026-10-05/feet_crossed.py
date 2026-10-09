"""カード 2 の D0(アドバイザーの指摘 5、L-659): 合図が分かった時刻 signal_t から建ての時刻 entry_t までに閉じた
海外の足の本数(= floor((entry_t − signal_t) / 足の長さ)。足の長さは走らせの引数 foot_min で、置いた値ではない)の
帯 0・1・2・3 以上ごとの、取引の数・損益の和・1 取引あたり。区間なし(記述)。
signal_t のある trades.csv.gz の走らせだけ(le_cx・ce_lx・close 系・gate・rgate)。
    python3 docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/feet_crossed.py
出力: このフォルダの FEET_CROSSED.md
"""
import csv
import gzip
import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "limit_sim", "runs")


def ns(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def main():
    out = ["# 合図 → 建てまでに閉じた海外の足の本数(帯ごと)", "",
           "本数 = floor((建ての時刻 − 合図が分かった時刻) / 足の長さ)。損益は %(損益の率。L-920 で bp は値動き率だけの名前。前の出力の pnl_bp は / 100)、経費の前。区間なし(記述)。良い側の走らせだけ(csv があるもの)。", "",
           "| 走らせ | 足(分) | 0 本: 取引・和・1 取引 | 1 本 | 2 本 | 3 本以上 |", "|---|---|---|---|---|---|"]
    for d in sorted(os.listdir(RUNS)):
        p = os.path.join(RUNS, d, "trades.csv.gz")
        if d.startswith("READ") or not os.path.exists(p):
            continue
        foot = json.load(open(os.path.join(RUNS, d, "run_record.json")))["params"]["foot_min"]
        rows = list(csv.DictReader(gzip.open(p, "rt")))
        if not rows or not rows[0].get("signal_t"):
            continue
        b = {0: [0, 0.0], 1: [0, 0.0], 2: [0, 0.0], 3: [0, 0.0]}
        for r in rows:
            if not r["signal_t"]:
                continue
            k = min(3, int((ns(r["entry_t"]) - ns(r["signal_t"])) // (foot * 60)))
            b[k][0] += 1
            b[k][1] += float(r["pnl_pct"]) if r.get("pnl_pct") not in (None, "") else float(r["pnl_bp"]) / 100
        cell = lambda k: f"{b[k][0]}・{b[k][1]:+,.2f}・{(b[k][1] / b[k][0]):+.4f}" if b[k][0] else "0"
        out.append(f"| {d} | {foot} | {cell(0)} | {cell(1)} | {cell(2)} | {cell(3)} |")
    open(os.path.join(HERE, "FEET_CROSSED.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
