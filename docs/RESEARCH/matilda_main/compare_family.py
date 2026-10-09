"""マチルダ本測定の族の本を基準(base)と並べる読み台本(リードが書いた。試験は付けていない。相方の指摘 D10-3)。
K-312 の読み方: 損益の符号 = 利確で閉じる割合 − とんとんの割合(負け 1 本 ÷ (利確 1 本 + 負け 1 本)、負け = ブレイク + 成行)。
本ごと・前半/後半(境 2019-12-09、出の時刻の UTC の日。D1 と同じ)・全期間で、
取引の数・利確で閉じる割合・とんとんの割合・差(ポイント)・利確 1 本・ブレイク 1 本・成行 1 本(円)・
5 段(上限)まで足した取引の数と和・損益の和(円)を出し、基準との差を並べる。結果で決まる群なので記述だけ。
上限の段は本の引数の levels(levels の族では本ごとに違う)。

    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/compare_family.py <本の名前> [<本の名前> ...]
    (取引の行は backtest_runs_shared/matilda_main_trades/<本>/trades.csv.gz、引数は同じ置き場の summary.json)
"""
import csv
import gzip
import json
import sys

ROOT = "backtest_runs_shared/matilda_main_trades"
CUT = "2019-12-09"


def stats(name):
    with open(f"{ROOT}/{name}/summary.json", encoding="utf-8") as fh:
        lv = json.load(fh)["params"]["levels"]
    out = {}
    rows = list(csv.DictReader(gzip.open(f"{ROOT}/{name}/trades.csv.gz", "rt")))
    for half, sel in (("前半", lambda r: r["exit_t"][:10] < CUT), ("後半", lambda r: r["exit_t"][:10] >= CUT),
                      ("全期間", lambda r: True)):
        rs = [r for r in rows if sel(r)]
        g = {k: [float(r["pnl_jpy"]) for r in rs if r["exit_reason"] == k] for k in ("close", "break", "market")}
        loss = g["break"] + g["market"]
        aw = sum(g["close"]) / len(g["close"]) if g["close"] else 0.0
        al = -sum(loss) / len(loss) if loss else 0.0
        top = [float(r["pnl_jpy"]) for r in rs if int(r["levels"]) == lv]
        out[half] = {"本": len(rs), "勝つ割合": len(g["close"]) / len(rs), "とんとん": al / (aw + al) if aw + al else 0.0,
                     "利確1本": aw, "ブレイク1本": sum(g["break"]) / max(1, len(g["break"])),
                     "成行1本": sum(g["market"]) / max(1, len(g["market"])), "成行本": len(g["market"]),
                     "上限段の本": len(top), "上限段の和": sum(top), "和": sum(float(r["pnl_jpy"]) for r in rs)}
        out[half]["差pt"] = 100 * (out[half]["勝つ割合"] - out[half]["とんとん"])
    return lv, out


def main():
    names = ["base"] + [n for n in sys.argv[1:] if n != "base"]
    res = {n: stats(n) for n in names}
    for half in ("前半", "後半", "全期間"):
        print(f"\n### {half}\n")
        print("| 本 | 上限段 | 取引 | 利確で閉じる割合 | とんとんの割合 | 差(ポイント) | 利確 1 本(円) | ブレイク 1 本(円) | 成行 本 / 1 本(円) | 上限段の取引 本 / 和(円) | 損益の和(円) | 和の基準との差(円) |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|")
        b = res["base"][1][half]["和"]
        for n in names:
            lv, o = res[n][0], res[n][1][half]
            print(f"| {n} | {lv} | {o['本']:,} | {o['勝つ割合']:.4f} | {o['とんとん']:.4f} | {o['差pt']:+.2f} | {o['利確1本']:+.1f} | "
                  f"{o['ブレイク1本']:+.1f} | {o['成行本']:,} / {o['成行1本']:+.1f} | {o['上限段の本']:,} / {o['上限段の和']:+,.0f} | "
                  f"{o['和']:+,.0f} | {o['和'] - b:+,.0f} |")


if __name__ == "__main__":
    main()
