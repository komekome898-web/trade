"""基準(base)の D2: 前の日のボラの三分位(`scripts/w4_measure/vol_split_daily.py` の daily_vol・classify。先読みなし、
2017 年から)で日を分け、場面ごと・場面 × 前半/後半 の 1 日あたりの損益(円)と 95% 区間(5 日の塊、class_mean_ci)。
日 = 日本時間の暦日(classify と同じ)。取引の損益は出の時刻の日に入れる。取引の無い日は 0 円。
前半/後半の境は D1 の読み口と同じ 2019-12-09(UTC の日で決めた境を、日本時間の日にそのまま当てた)。
    PYTHONPATH=src:scripts/w4_measure python3 docs/RESEARCH/matilda_main/base/d2_scenes.py
"""
import csv, glob, gzip
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import numpy as np
from bot.bt.simple import read_bars
from vol_split_daily import daily_vol, classify, class_mean_ci

JST = timezone(timedelta(hours=9))
def jday(iso):
    return datetime.fromisoformat(iso).astimezone(JST).date().isoformat()

FILES = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz"))
FILES = [x for x in FILES if int(x[-11:-7]) <= 2023]
closes = defaultdict(list)
for b in read_bars(FILES, "2023-12-17T15:00:00+00:00"):
    closes[jday(b[0])].append(b[4])
vol = daily_vol(closes)
cls = classify(vol)
pnl = defaultdict(float)
for r in csv.DictReader(gzip.open("backtest_runs_shared/matilda_main_trades/base/trades.csv.gz", "rt")):
    pnl[jday(r["exit_t"])] += float(r["pnl_jpy"])
days = sorted(d for d in cls if d <= "2023-12-17")
CUT = "2019-12-09"
print("場面 | 区切り | 日数 | 1 日あたり 円 [区間]")
for k in ("low", "mid", "high"):
    for name, sel in (("全部(2017〜)", lambda d: True), ("前半(〜2019-12-08)", lambda d: d < CUT), ("後半(2019-12-09〜)", lambda d: d >= CUT)):
        x = np.array([pnl.get(d, 0.0) for d in days if cls[d] == k and sel(d)])
        m, lo, hi = class_mean_ci(x)
        print(k, name, len(x), f"{m:+.0f} [{lo:+.0f}, {hi:+.0f}]")
