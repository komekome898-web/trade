"""族 alert の D0・D3 の確かめ。(1)(2) 時間切れの成行で閉じた取引の保有の分(最初の約定の足の始まり signal_t から出の足の終わり exit_t まで)の
最小・中央値・最大を本ごとに出す。決まり(R10 ロ)は「最初の約定から 2 × alert_count 分を超えた足が閉じた時点で成行、次の足の始値で約定」。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/alert/alert_check.py
"""
import csv, gzip, statistics
from datetime import datetime
for r, ac in (("base", 20), ("alert_x1", 40), ("alert_x2", 80)):
    h = []
    for t in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{r}/trades.csv.gz", "rt")):
        if t["exit_reason"] == "market":
            h.append((datetime.fromisoformat(t["exit_t"]) - datetime.fromisoformat(t["signal_t"])).total_seconds() / 60)
    print(r, "alert_count", ac, "分 / 2 倍", 2 * ac, "分 | 成行", len(h), "本 | 保有の分 最小", min(h), "中央値", statistics.median(h), "最大", max(h))
# (2) 2 × alert_count 分より早い成行の本数(時間切れ以外の成行の候補)
for r, ac in (("base", 20), ("alert_x1", 40), ("alert_x2", 80)):
    n = 0
    for t in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{r}/trades.csv.gz", "rt")):
        if t["exit_reason"] == "market" and (datetime.fromisoformat(t["exit_t"]) - datetime.fromisoformat(t["signal_t"])).total_seconds() / 60 <= 2 * ac:
            n += 1
    print(r, "2 倍以内の成行", n, "本")
# (3) 出の理由ごとの本数と、20 分(基準の alert_count)を超えて持った取引の本数・和
from collections import Counter
for r in ("base", "alert_x1", "alert_x2"):
    c = Counter(); n20 = 0; s20 = 0.0; n = 0
    for t in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{r}/trades.csv.gz", "rt")):
        n += 1; c[t["exit_reason"]] += 1
        if (datetime.fromisoformat(t["exit_t"]) - datetime.fromisoformat(t["signal_t"])).total_seconds() / 60 > 20:
            n20 += 1; s20 += float(t["pnl_jpy"])
    print(r, "取引", n, "出の理由", dict(c), "| 20 分超", n20, f"({n20/n:.1%})", "和", round(s20))
# (3b) 20 分超の取引を 出の理由 × 本 で(本数と和)
for r in ("base", "alert_x1", "alert_x2"):
    c = Counter(); s = Counter()
    for t in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{r}/trades.csv.gz", "rt")):
        if (datetime.fromisoformat(t["exit_t"]) - datetime.fromisoformat(t["signal_t"])).total_seconds() / 60 > 20:
            c[t["exit_reason"]] += 1; s[t["exit_reason"]] += float(t["pnl_jpy"])
    print(r, "20 分超 出の理由別", {k: (c[k], round(s[k])) for k in sorted(c)})
# (4) 基準だけの取引の signal_t が、こちらの取引の建て〜出(signal_t 〜 exit_t)の間に入る本数(持ち高の違いで建たなかった合図)
import bisect
def load(r):
    return [(t["signal_t"], t["exit_t"], float(t["pnl_jpy"])) for t in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{r}/trades.csv.gz", "rt"))]
B = load("base")
for r in ("alert_x1", "alert_x2"):
    A = load(r); sa = {x[0] for x in A}
    iv = sorted((x[0], x[1]) for x in A); starts = [x[0] for x in iv]
    only = [x for x in B if x[0] not in sa]; inside = 0; s_in = s_out = 0.0
    for sig, _, p in only:
        i = bisect.bisect_right(starts, sig) - 1
        if i >= 0 and iv[i][0] < sig <= iv[i][1]:
            inside += 1; s_in += p
        else:
            s_out += p
    print(r, "基準だけ", len(only), "本 | こちらの建て〜出の間に入る", inside, "本・和", round(s_in), "| 入らない", len(only) - inside, "本・和", round(s_out))
# (5) 保有 625 分の取引と、その間の 1 分足の本数
from bot.bt.simple import read_bars
for t in csv.DictReader(gzip.open("backtest_runs_shared/matilda_main_trades/base/trades.csv.gz", "rt")):
    if t["exit_reason"] == "market" and (datetime.fromisoformat(t["exit_t"]) - datetime.fromisoformat(t["signal_t"])).total_seconds() / 60 == 625:
        y = t["signal_t"][:4]
        F = [f"backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_{y}.csv.gz"]
        n = sum(1 for b in read_bars(F, "2023-12-17T15:00:00+00:00") if t["signal_t"] <= b[0] < t["exit_t"])
        print("保有 625 分の取引", t["signal_t"], "→", t["exit_t"], "| その間の 1 分足", n, "本(欠けが無ければ 625 本)")
