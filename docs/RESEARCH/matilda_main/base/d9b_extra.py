"""基準(base)の D9b の足し(相方の指摘 D9b-1・2・4・6)。取引の行だけを読む。記述(結果で決まる群)。
(1) 前半・後半ごとの 利確で閉じた割合・利確 1 本あたり・ブレイクと成行 1 本あたり・とんとんの割合
    (とんとん = 負け 1 本あたり ÷ (利確 1 本あたり + 負け 1 本あたり)、負け = ブレイク + 成行)
(2) 利確で閉じた取引を 保有(1 段目の約定の足の始まり → 最後の約定の足の始まり)≤ 20 分 / > 20 分 に分ける
(4) 保有 3 分以内 / 3 分超 の本数と和
(6) 5 段の取引の群の和(前半・後半)
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/d9b_extra.py
"""
import csv, gzip
from datetime import datetime
rows = list(csv.DictReader(gzip.open("backtest_runs_shared/matilda_main_trades/base/trades.csv.gz", "rt")))
CUT = "2019-12-09"
def mins(r):
    return (datetime.fromisoformat(r["exit_t"]) - datetime.fromisoformat(r["entry_t"])).total_seconds() / 60
for half, sel in (("前半", lambda r: r["exit_t"][:10] < CUT), ("後半", lambda r: r["exit_t"][:10] >= CUT), ("全期間", lambda r: True)):
    rs = [r for r in rows if sel(r)]
    w = [float(r["pnl_jpy"]) for r in rs if r["exit_reason"] == "close"]
    l = [float(r["pnl_jpy"]) for r in rs if r["exit_reason"] in ("break", "market")]
    aw, al = sum(w) / len(w), -sum(l) / len(l)
    print(half, "本", len(rs), "利確の割合", f"{len(w)/len(rs):.4f}", "利確 1 本", f"{aw:+.1f}", "負け(ブレイク+成行)1 本", f"{-al:+.1f}",
          "とんとんの割合", f"{al/(aw+al):.4f}", "差(ポイント)", f"{100*(len(w)/len(rs)-al/(aw+al)):+.2f}")
    c20 = [r for r in rs if r["exit_reason"] == "close" and mins(r) <= 20]
    c40 = [r for r in rs if r["exit_reason"] == "close" and mins(r) > 20]
    print("  利確 保有≤20分", len(c20), round(sum(float(r["pnl_jpy"]) for r in c20)), "| 保有>20分", len(c40), round(sum(float(r["pnl_jpy"]) for r in c40)),
          "1 本", round(sum(float(r["pnl_jpy"]) for r in c40) / max(1, len(c40)), 1))
    s3 = [r for r in rs if mins(r) <= 3]; l3 = [r for r in rs if mins(r) > 3]
    print("  保有≤3分", len(s3), round(sum(float(r["pnl_jpy"]) for r in s3)), "| >3分", len(l3), round(sum(float(r["pnl_jpy"]) for r in l3)))
    f5 = [r for r in rs if r["levels"] == "5"]
    print("  5 段の取引", len(f5), round(sum(float(r["pnl_jpy"]) for r in f5)))
