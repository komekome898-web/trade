"""本 × 保有の帯(0 分 / 0 分超)× 前半・後半 × 出の理由(利確 close / ブレイク break / 成行 market)× 段の数(1 段 / 2 段以上)の
本数・1 取引あたりの損益(円)を数える(境 2019-12-09、出の UTC の日)。数えるだけ(区間なし)。相方の step D9b の指摘 2・3。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/levels_reason.py <本> [...]
"""
import csv, gzip, sys
CUT = "2019-12-09"
print("| 本 | 帯 | 区切り | 出の理由 | 1 段 本 / 1 取引あたり 円 | 2 段以上 本 / 1 取引あたり 円 | 全部 本 / 1 取引あたり 円 |")
print("|---|---|---|---|---|---|---|")
for name in sys.argv[1:]:
    acc = {}
    for r in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{name}/trades.csv.gz", "rt")):
        band = "0 分" if r["exit_t"] <= r["entry_t"] else "0 分超"
        half = "前半" if r["exit_t"][:10] < CUT else "後半"
        why = r["exit_reason"] if r["exit_reason"] in ("close", "break", "market") else "その他"
        lv = "1" if int(r["levels"]) == 1 else "2+"
        for k in ((band, half, why, lv), (band, half, why, "all")):
            a = acc.setdefault(k, [0, 0.0]); a[0] += 1; a[1] += float(r["pnl_jpy"])
    f = lambda k: "—" if k not in acc else f"{acc[k][0]:,} / {acc[k][1] / acc[k][0]:+.1f}"
    for band in ("0 分", "0 分超"):
        for half in ("前半", "後半"):
            for why in ("close", "break", "market", "その他"):
                if (band, half, why, "all") in acc:
                    print(f"| {name} | {band} | {half} | {why} | {f((band, half, why, '1'))} | {f((band, half, why, '2+'))} | {f((band, half, why, 'all'))} |")
