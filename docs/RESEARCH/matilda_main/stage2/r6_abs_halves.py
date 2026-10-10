"""L-964 の振り返り: 32 本それぞれの、基準との差ではなく本そのものの前半・後半の 1 日あたりの円(点の値、区間なし)。
日数は段 1 の分析と同じ(前半 1,469・後半 1,470 日)。半分の分けは合図の時刻。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/r6_abs_halves.py > docs/RESEARCH/matilda_main/stage2/r6_abs_halves.out
"""
import os
import pandas as pd

T = "backtest_runs_shared/matilda_main_trades"
CUT = "2019-12-09"
print("| 本 | 前半 円/日 | 後半 円/日 | 全期間 円/日 |")
print("|---|---|---|---|")
for r in sorted(os.listdir(T)):
    d = pd.read_csv(f"{T}/{r}/trades.csv.gz", usecols=["signal_t", "pnl_jpy"])
    late = d.signal_t.str[:10] >= CUT
    a, b = d[~late].pnl_jpy.sum() / 1469, d[late].pnl_jpy.sum() / 1470
    print(f"| {r} | {a:+.1f} | {b:+.1f} | {d.pnl_jpy.sum() / 2939:+.1f} |")
