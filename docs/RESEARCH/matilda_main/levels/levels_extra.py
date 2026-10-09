"""族 levels の D9b の足し(相方の D9b の指摘 1・2・3)。
(1) 損益がちょうど 0 円の取引を 出の理由 × 年 で数える(本ごと)
(2) 利確で閉じた取引を 保有 ≤ 20 分 / > 20 分 に分けた本数と和(本ごと、前半・後半)
(3) levels_7 で 7 段まで足した最初の取引の約定を、その足の高値・安値と突き合わせる
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/levels/levels_extra.py
"""
import csv, glob, gzip
from collections import Counter, defaultdict
from datetime import datetime
from bot.bt.simple import read_bars
CUT = "2019-12-09"
def mins(r):
    return (datetime.fromisoformat(r["exit_t"]) - datetime.fromisoformat(r["entry_t"])).total_seconds() / 60
for n in ("levels_1", "levels_3", "base", "levels_7"):
    rows = list(csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{n}/trades.csv.gz", "rt")))
    z = Counter((r["exit_reason"], r["exit_t"][:4]) for r in rows if float(r["pnl_jpy"]) == 0)
    print(n, "損益 0 円の取引", sum(z.values()), dict(sorted(Counter(k[0] for k in z.elements()).items())), "年", dict(sorted(Counter(k[1] for k in z.elements()).items())))
    for half, sel in (("前半", lambda r: r["exit_t"][:10] < CUT), ("後半", lambda r: r["exit_t"][:10] >= CUT)):
        c = [r for r in rows if sel(r) and r["exit_reason"] == "close"]
        a = [r for r in c if mins(r) <= 20]; b = [r for r in c if mins(r) > 20]
        print("  ", half, "利確 ≤20分", len(a), round(sum(float(r["pnl_jpy"]) for r in a)), "| >20分", len(b), round(sum(float(r["pnl_jpy"]) for r in b)),
              "| 2 段以上で閉じた利確", sum(1 for r in c if int(r["levels"]) >= 2))
# (3)
fills = []; pos = 0.0; cur = []
for f in csv.DictReader(gzip.open("backtest_runs_shared/matilda_main/levels_7/fills.csv.gz", "rt")):
    q = float(f["qty"]) * (1 if f["side"] == "buy" else -1)
    cur.append(f); pos += q
    if abs(pos) < 1e-9:
        if sum(1 for x in cur if x["kind"] in ("entry", "level")) == 7 and cur[0]["ts"] >= "2017":
            fills = cur; break
        cur = []
need = {f["ts"] for f in fills}
yr = fills[0]["ts"][:4]
bars = {}
for b in read_bars(sorted(glob.glob(f"backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_{yr}.csv.gz")), "2023-12-17T15:00:00+00:00"):
    if b[0] in need:
        bars[b[0]] = b
    if b[0] > max(need):
        break
prev = None
for f in fills:
    b = bars[f["ts"]]
    px = float(f["px"])
    print(f["ts"], f["kind"], f["side"], f["qty"], px, f["case"], "| 足 O H L C", b[1:5], "| 高安の中", b[3] <= px <= b[2],
          "| 前の段との差", None if prev is None or f["kind"] not in ("level",) else round(px - prev, 1))
    if f["kind"] in ("entry", "level"):
        prev = px
