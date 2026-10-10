"""L-973 次の手 1: K-378 の測り(前提の直接の測り D1b。`scripts/analysis/d1b_matilda.py` の starts)を Binance BTCUSDT 現物の 1 分足に当てる。
足: `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_YYYY.csv.gz`(2017-08-17〜)、封印の境 2023-12-17T15:00Z で止める(starts の門)。
引数: 基準(5 段・建て 4・利確 3)と同じ。ただしヒゲの切り落とし beard_ignore は bitFlyer の 1 円(= 呼値 1 つ)に合わせ、Binance BTCUSDT の呼値 0.01 USDT にした(リードの選択)。
幅の門(range_setting 0.025%・over_range 16.7%)は値段に対する割合なので、そのまま。
出力: <out>/day_counts.csv・tables.md(starts の write_outputs)と <out>/records.pkl(git の外の置き場に)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/stage2/d1b_binance.py <out>
"""
import csv
import glob
import gzip
import os
import pickle
import sys
import time

sys.path.insert(0, "scripts/analysis")
import d1b_matilda as d1b  # noqa: E402

F = sorted(glob.glob("backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_20[12][0-9].csv.gz"))


SKEW = {"秒のずれた足": 0, "同じ分の 2 本目を捨てた": 0}


def bars():
    """2017-12〜2018-02 に、取引所の保守の後で始まりの時刻が秒ずれした足がある(2017 年 20,401 本・2018 年 1,201 本)。
    分に切り下げ、同じ分になった 2 本目以降は捨てる(数を SKEW に数える)。"""
    last = None
    for f in F:
        with gzip.open(f, "rt", newline="") as fh:
            r = csv.reader(fh)
            next(r)
            for row in r:
                ts = row[0].replace(" ", "T")
                if not ts.endswith(":00+00:00"):
                    SKEW["秒のずれた足"] += 1
                    ts = ts[:17] + "00+00:00"
                if last is not None and ts <= last:
                    SKEW["同じ分の 2 本目を捨てた"] += 1
                    continue
                last = ts
                yield (ts, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5]))


out = sys.argv[1]
os.makedirs(out, exist_ok=True)
p = d1b.base_params()
p["beard_ignore"] = 0.01
t0 = time.time()
res = d1b.starts(bars(), p, d1b.SEAL)
d1b.write_outputs(out, res)
with open(os.path.join(out, "records.pkl"), "wb") as fh:
    pickle.dump(res, fh)
print(SKEW)
print(f"ファイル {' '.join(os.path.basename(f) for f in F)}")
print(f"走らせの時間 {time.time() - t0:.0f} 秒・起点 {len(res['records'])}・日 {len(res['days'])}・最初の日 {res['days'][0]}・最後の日 {res['days'][-1]}")
