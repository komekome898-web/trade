"""リードが書いた。委任・批評家を通していない(数えるだけ)。基準の取引を、幅の門の本(range_lo_p10/p25/p50・range_hi_p75/p90)に
同じ合図の時刻の取引があるかで、直近 40 本の幅 ÷ 終値 の 6 帯(下 10% / 10〜25 / 25〜50 / 50〜75 / 75〜90 / 上 10%、全期間の分布の分位 = 標本の中)に分け、
前半・後半(境 2019-12-09、合図の UTC の日)ごとに本数・和(円)・1 日あたり(円/日、1,469・1,470 日)・1 本あたり(円)を出す。
帯の決め方は「その門の本で建たなかったか」なので、門の本で持ち高の違いから建たなかった合図も外側の帯に入る(こちらだけの取引の分の誤差。数えていない)。
相方の range_lo D9b の指摘 5。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/range_hi/six_bands.py
"""
import csv, gzip
CUT, DAYS = "2019-12-09", {"前半": 1469, "後半": 1470}
def sigs(n):
    return {r["signal_t"] for r in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{n}/trades.csv.gz", "rt"))}
lo = {k: sigs(f"range_lo_{k}") for k in ("p10", "p25", "p50")}
hi = {k: sigs(f"range_hi_{k}") for k in ("p75", "p90")}
def band(s):
    if s not in lo["p10"]: return "1 下 10%"
    if s not in lo["p25"]: return "2 10〜25%"
    if s not in lo["p50"]: return "3 25〜50%"
    if s in hi["p75"]: return "4 50〜75%"
    if s in hi["p90"]: return "5 75〜90%"
    return "6 上 10%"
acc = {}
for r in csv.DictReader(gzip.open("backtest_runs_shared/matilda_main_trades/base/trades.csv.gz", "rt")):
    h = "前半" if r["signal_t"][:10] < CUT else "後半"
    a = acc.setdefault((band(r["signal_t"]), h), [0, 0.0]); a[0] += 1; a[1] += float(r["pnl_jpy"])
print("| 幅の帯 | 前半 本 | 前半 和 円 | 前半 円/日 | 前半 1 本 円 | 後半 本 | 後半 和 円 | 後半 円/日 | 後半 1 本 円 |")
print("|---|---|---|---|---|---|---|---|---|")
for b in sorted({k[0] for k in acc}):
    cells = []
    for h in ("前半", "後半"):
        n, s = acc.get((b, h), [0, 0.0])
        cells += [f"{n:,}", f"{s:+,.0f}", f"{s / DAYS[h]:+.0f}", f"{s / n:+.1f}" if n else "—"]
    print(f"| {b[2:]} | " + " | ".join(cells) + " |")
