"""L-965「稼ぐところと損するところを明確にする」の材料。基準の取引を、建てる時点で分かる量(【建ての前に決まる群】)と、
閉じ方・段数(【結果で決まる群】)で分け、前半・後半の 1 日あたりの円と区間を出す。あわせて 35 本の、稼ぎ(利確の和)と損(ブレイク・成行の和)の 1 日あたり。
区間: 95%、日の塊(循環、5 日・1,000 回・種 20261004。分析のスキルの共通の決まりと同じ)。日 = 合図の UTC の日。日数 前半 1,469・後半 1,470。
建ての時点の量は r4_lines_dump.py の書き出し(1 段目の約定の直前の線)。帯の境は全期間の標本の中(印「標本の中」)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/earn_loss_map.py <base の lines.csv> > docs/RESEARCH/matilda_main/stage2/earn_loss_map.out
"""
import os
import sys
import numpy as np
import pandas as pd

T = "backtest_runs_shared/matilda_main_trades"
CUT = "2019-12-09"
DAYS = {"前半": pd.date_range("2015-12-01", "2019-12-08"), "後半": pd.date_range(CUT, "2023-12-17")}
rng = np.random.default_rng(20261004)


def ci(daily, days):
    """daily: 日 → 円 の Series。days: その半分の全部の日(取引の無い日は 0)。返すのは 1 日あたりの点と 95% 区間。"""
    v = daily.reindex(days.strftime("%Y-%m-%d"), fill_value=0).to_numpy()
    n, b = len(v), 5
    k = int(np.ceil(n / b))
    st = rng.integers(0, n, size=(1000, k))
    idx = (st[:, :, None] + np.arange(b)).reshape(1000, -1)[:, :n] % n
    m = v[idx].mean(axis=1)
    return v.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)


def fmt(x):
    p, lo, hi = x
    mark = "＋" if lo > 0 else ("－" if hi < 0 else "")
    return f"{p:+.1f} [{lo:+.1f}, {hi:+.1f}]{mark}"


t = pd.read_csv(f"{T}/base/trades.csv.gz")
t["entry_t"] = pd.to_datetime(t.entry_t, utc=True)
ln = pd.read_csv(sys.argv[1])
ln["entry_t"] = pd.to_datetime(ln.start + 60_000_000_000, utc=True)
t = t.merge(ln.drop(columns=["side"]), on="entry_t", how="left")
t["day"] = t.signal_t.str[:10]
t["half"] = np.where(t.day >= CUT, "後半", "前半")
t["w"] = t.width / t.px
t["wband"] = pd.cut(t.w, [0, 0.001857, 0.003010, 0.005133, 0.008844, 0.014995, 1],
                    labels=["幅 〜10%点", "幅 10〜25%", "幅 25〜50%", "幅 50〜75%", "幅 75〜90%", "幅 90%点〜"], right=False)
line = np.where(t.side == 1, t.bd, t.bu)
t["ldist"] = np.where(pd.isna(line), np.nan, (t.side * (t.px - line)) / t.width)
q = t.ldist.quantile([0.25, 0.5, 0.75]).to_list()
t["lband"] = pd.cut(t.ldist, [-np.inf] + q + [np.inf], labels=[f"線まで 〜{q[0]:.2f} 幅", f"{q[0]:.2f}〜{q[1]:.2f}", f"{q[1]:.2f}〜{q[2]:.2f}", f"{q[2]:.2f} 幅〜"])
t.loc[pd.isna(line), "lband"] = np.nan
t["lband"] = t.lband.cat.add_categories(["線なし(ブレイク中など)"]).fillna("線なし(ブレイク中など)") if hasattr(t.lband, "cat") else t.lband
t["dev"] = (t.side * (t.center - t.px)) / t.width  # 中心までの距離(幅の何倍。大きいほど深く外れて建った)
qd = t.dev.quantile([0.25, 0.5, 0.75]).to_list()
t["dband"] = pd.cut(t.dev, [-np.inf] + qd + [np.inf], labels=[f"中心まで 〜{qd[0]:.2f} 幅", f"{qd[0]:.2f}〜{qd[1]:.2f}", f"{qd[1]:.2f}〜{qd[2]:.2f}", f"{qd[2]:.2f} 幅〜"])
t["hour"] = ((t.entry_t.dt.hour + 9) % 24 // 4 * 4).map(lambda h: f"日本時間 {h:02d}〜{h + 4:02d} 時")
t["sidel"] = t.side.map({1: "買い", -1: "売り"})
t["lv"] = t.levels.map(lambda x: f"段 {x}" if x < 5 else "段 5(上限)")
t["why"] = t.exit_reason.map({"close": "利確", "break": "ブレイクの逆指値", "market": "成行(時間切れ・ブレイク後)"})


def table(col, title, kind):
    print(f"\n## {title}【{kind}】\n")
    print("| 群 | 前半 本 | 前半 円/日 [区間] | 後半 本 | 後半 円/日 [区間] | 1 本あたり 前半 / 後半 |")
    print("|---|---|---|---|---|---|")
    for g in t[col].dropna().unique().tolist() if not hasattr(t[col], "cat") else t[col].cat.categories:
        r = [str(g)]
        per = []
        for h in ("前半", "後半"):
            x = t[(t[col] == g) & (t.half == h)]
            r += [f"{len(x):,}", fmt(ci(x.groupby("day").pnl_jpy.sum(), DAYS[h]))]
            per.append(f"{x.pnl_jpy.mean():+.2f}" if len(x) else "—")
        print("| " + " | ".join(r) + f" | {per[0]} / {per[1]} |")


print("印: ＋ = 区間が 0 より上、－ = 0 より下。帯の境は標本の中。")
for h in ("前半", "後半"):
    print(f"\n基準 {h} 全体: {fmt(ci(t[t.half == h].groupby('day').pnl_jpy.sum(), DAYS[h]))} 円/日")
table("wband", "建てた時点の幅 ÷ 1 段目の約定値段(境 = 全期間の分布の 10・25・50・75・90% 点)", "建ての前に決まる群")
table("dband", "建てた時点の、1 段目の値段から中心までの距離 ÷ 幅(四分位)", "建ての前に決まる群")
table("lband", "建てた時点の、1 段目の値段から損の側のブレイクの線までの距離 ÷ 幅(四分位)", "建ての前に決まる群")
table("hour", "建てた時刻(日本時間 4 時間ごと)", "建ての前に決まる群")
table("sidel", "向き", "建ての前に決まる群")
table("lv", "足した段の数", "結果で決まる群")
table("why", "閉じ方", "結果で決まる群")

print("\n## 35 本の稼ぎ(利確の和)と損(ブレイクの逆指値・成行の和)の 1 日あたり(点の値)【結果で決まる群】\n")
print("| 本 | 前半 利確 | 前半 ブレイク | 前半 成行 | 後半 利確 | 後半 ブレイク | 後半 成行 | 後半 計 |")
print("|---|---|---|---|---|---|---|---|")
for r in sorted(os.listdir(T)):
    d = pd.read_csv(f"{T}/{r}/trades.csv.gz", usecols=["signal_t", "pnl_jpy", "exit_reason"])
    late = d.signal_t.str[:10] >= CUT
    c = []
    for h, m, n in (("前半", ~late, 1469), ("後半", late, 1470)):
        for e in ("close", "break", "market"):
            c.append(d[m & (d.exit_reason == e)].pnl_jpy.sum() / n)
    print(f"| {r} | " + " | ".join(f"{x:+.1f}" for x in c) + f" | {sum(c[3:]):+.1f} |")
