"""L-972: 基準の取引を年ごと × 保有の長さ(1 段目の足の終わりから出まで。20 分以内 / 20 分超 = 利確を緩めた後)で分け、本数の割合・1 本の円・和の 1 日あたりを出す。
保有の長さは結果で決まる群(記述だけ)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/year_hold.py > docs/RESEARCH/matilda_main/stage2/year_hold.out
"""
import pandas as pd

d = pd.read_csv("backtest_runs_shared/matilda_main_trades/base/trades.csv.gz")
d["y"] = d.exit_t.str[:4].astype(int)
d["hold"] = (pd.to_datetime(d.exit_t) - pd.to_datetime(d.entry_t)).dt.total_seconds() / 60
DAYS = {y: (366 if y in (2016, 2020) else 365) for y in range(2016, 2024)}
DAYS[2023] = 351
print("| 年 | 20 分以内に閉じた割合 | 20 分以内 1 本の円 | 20 分以内 円/日 | 20 分超の割合 | 20 分超 1 本の円 | 20 分超 円/日 | 20 分超の利確 1 本の円 | 20 分超のブレイク 1 本の円 |")
print("|---|---|---|---|---|---|---|---|---|")
for y in range(2016, 2024):
    x = d[d.y == y]
    a, b = x[x.hold <= 20], x[x.hold > 20]
    print(f"| {y} | {len(a) / len(x):.1%} | {a.pnl_jpy.mean():+.2f} | {a.pnl_jpy.sum() / DAYS[y]:+.0f} | {len(b) / len(x):.1%} | {b.pnl_jpy.mean():+.2f} | {b.pnl_jpy.sum() / DAYS[y]:+.0f} | "
          f"{b[b.exit_reason == 'close'].pnl_jpy.mean():+.1f} | {b[b.exit_reason == 'break'].pnl_jpy.mean():+.1f} |")
