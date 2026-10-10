"""逆張りの期待値の指標(枠組み `docs/DISCUSSIONS/2026-10-10_reversion_index/FRAMING.md`、L-979〜L-981)の 1 件 = 起点 を作る。
`scripts/analysis/d1b_matilda.py` の starts を写し、次を変えた:
  - 外れの大きさ k(3・4・5。L-980)を引数に。建ての線 = 中心 ± k × ボラ、戻りの線 = 中心 ± (k − 1) × ボラ(k = 4 で今の測りと同じ 3 ボラ。どの k でも外れから 1 ボラ戻る線)
  - 記録するのは外れた最初の足(entry)だけ
  - 量を足す: 20 本前の時点のボラ・幅(ボラ加速度・レンジ加速度、L-981 で確定した定義 = 今 ÷ 20 本前)。戦略の窓(ヒゲの切り落とし後)からそのまま取る
足: bitFlyer FX_BTC_JPY(`backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/`)か Binance BTCUSDT 現物(`backtest_data/binance_BTCUSDT_1m_20170801_20231231/`。秒のずれた足は分に切り下げ)。封印の境 2023-12-17T15:00Z で止める。
    PYTHONPATH=src python3 docs/RESEARCH/reversion_index/ri_starts.py <bitflyer|binance> <k> <出力.pkl>
"""
import csv
import glob
import gzip
import pickle
import sys
import time
from collections import deque
from datetime import timedelta

sys.path.insert(0, "scripts/analysis")
import d1b_matilda as d1b  # noqa: E402
from bot.bt.simple import read_bars  # noqa: E402
from bot.strategy.matilda_simple import MatildaSimple  # noqa: E402

BF = sorted(f for f in glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz") if int(f[-11:-7]) <= 2023)
BN = sorted(glob.glob("backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_20[12][0-9].csv.gz"))


def binance_bars():
    last = None
    for f in BN:
        with gzip.open(f, "rt", newline="") as fh:
            r = csv.reader(fh)
            next(r)
            for row in r:
                ts = row[0].replace(" ", "T")
                if not ts.endswith(":00+00:00"):
                    ts = ts[:17] + "00+00:00"
                if last is not None and ts <= last:
                    continue
                last = ts
                yield (ts, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5]))


def starts(bars, p):
    seal_t = d1b._parse(d1b.SEAL)
    ex, W = p["exit_setting"], d1b.WINDOW
    st = MatildaSimple(p)
    pending, records = deque(), []
    prev = prev_side = last_t = end = None
    for bar in bars:
        t = d1b._parse(bar[0])
        if t >= seal_t:
            end = seal_t
            break
        last_t = t
        o, h, lo, c = bar[1], bar[2], bar[3], bar[4]
        if o == c and (prev is None or o == prev):
            continue
        prev = c
        while pending and (t - pending[0].t0) >= timedelta(minutes=W + 1):
            records.append(d1b._finish(pending.popleft()))
        for pd_ in pending:
            k = d1b._minutes(t, pd_.t0)
            pd_.kpath.append((k, h, lo))
            if 1 <= k <= W:
                pd_.n_win += 1
        st.decide({"kind": "close", "ts": bar[0], "price": c, "fills": [], "touched": [], "bar": bar})
        sn = st._snap
        if sn is None or sn["vola"] <= 0:
            continue
        side = -1 if c > sn["up"] else (1 if c < sn["lo"] else None)
        was, prev_side = prev_side, side
        if side is None or was == side:
            continue  # 外れた最初の足だけ
        wins = list(st._wins)
        old = wins[-60:-20]
        vola20 = sum(x["body"] for x in old) / len(old) if len(old) == 40 else None
        width20 = (max(x["h"] for x in old) - min(x["l"] for x in old)) if len(old) == 40 else None
        rec = {"ts": bar[0], "day": bar[0][:10], "side": side, "gate": bool(sn["gate"]), "brk": st._brk,
               "c0": c, "center": sn["center"], "vola": sn["vola"], "width": st.ind["width"], "vola20": vola20, "width20": width20,
               "tp_line": sn["center"] - side * ex * sn["vola"], "break_line": sn["bu"] if side == -1 else sn["bd"]}
        pending.append(d1b._Pending(rec, t))
    if end is None:
        end = last_t + timedelta(minutes=1)
    while pending:
        pd_ = pending.popleft()
        if pd_.t0 + timedelta(minutes=W + 1) <= end:
            records.append(d1b._finish(pd_))
    return records


venue, k, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
p = d1b.base_params()
p.update({"entry_setting": k, "exit_setting": k - 1})
if venue == "binance":
    p["beard_ignore"] = 0.01
    bars = binance_bars()
else:
    bars = read_bars(BF, d1b.SEAL)
t0 = time.time()
recs = starts(bars, p)
with open(out, "wb") as fh:
    pickle.dump(recs, fh)
print(f"{venue} k={k} 起点 {len(recs)} 時間 {time.time() - t0:.0f} 秒")
