"""L-972「なぜ年々下がっていくのか」: 損益を年ごとに分解する。
(1) 基準と I5 + I1 0.49 の年ごと: 取引の数・1 日あたり・利確/ブレイク/成行の本数と 1 本の円・ブレイクに届く割合・損益の分かれ目の利確の割合
(2) 基準の建ての時点の量の年ごとの中央値: ボラ ÷ 値段(bp)・幅 ÷ 値段(%)・建ての線の中心からの距離 ÷ 幅(4 ボラ ÷ 幅)・損の側のブレイクの線までの距離(ボラの何倍)
(3) 基準の、中心からの距離 ÷ 幅 の帯(境 = 全期間の分布の 0.35・0.42・0.49。標本の中)× 年: 帯ごとの取引の割合・1 本の円・ブレイクに届く割合
(4) 混ざり方と帯の中の変わり方の分け: 年ごとの 1 本の円を、2016-2018 の帯の割合にそろえた値(直接の標準化)と並べる
(5) 段数(5 段まで足した取引の割合と、その 1 本の円)
1 本の円は 1 段の量(2.8 万円 ÷ 値段)に比例するので、円を「1 段の量 × ボラ」で割った値(ボラ単位の損益 = pnl ÷ (qty1 × vola))も並べる。
建ての時点の量は r4_lines_dump.py・r7_snap_dump.py の書き出し(基準を同じコードで走らせ直したもの。保存済みの本と一致)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/year_decline.py <r4 base> <r7 base> > docs/RESEARCH/matilda_main/stage2/year_decline.out
"""
import sys
import numpy as np
import pandas as pd

T = "backtest_runs_shared/matilda_main_trades/"
MIN = 60_000_000_000
YEARS = list(range(2016, 2024))
DAYS = {y: (pd.Timestamp(f"{y}-12-31") - pd.Timestamp(f"{y}-01-01")).days + 1 for y in YEARS}
DAYS[2023] = (pd.Timestamp("2023-12-17") - pd.Timestamp("2023-01-01")).days + 1


def outcome(r):
    d = pd.read_csv(T + r + "/trades.csv.gz")
    d["y"] = d.exit_t.str[:4].astype(int)
    print(f"\n## {r}: 年ごとの損益の分解(出の UTC の年)\n")
    print("| 年 | 取引 | 円/日 | 利確 本 | 利確 1 本 | ブレイク 本 | ブレイク 1 本 | 成行 本 | 成行 1 本 | ブレイクに届く割合 | 分かれ目の利確の割合 = |ブレイク| ÷ (利確 + |ブレイク|) | 実際の利確の割合 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for y in YEARS:
        x = d[d.y == y]
        c, b, m = (x[x.exit_reason == k].pnl_jpy for k in ("close", "break", "market"))
        be = -b.mean() / (c.mean() - b.mean())
        print(f"| {y} | {len(x):,} | {x.pnl_jpy.sum() / DAYS[y]:+.0f} | {len(c):,} | {c.mean():+.1f} | {len(b):,} | {b.mean():+.1f} | {len(m):,} | {m.mean():+.1f} | "
              f"{len(b) / len(x):.2%} | {be:.2%} | {len(c) / len(x):.2%} |")
    return d


base = outcome("base")
outcome("exit_2_dev_0.49")

ln = pd.read_csv(sys.argv[1] + "/lines.csv", usecols=["start", "px", "width", "center", "bu", "bd"])
sn = np.load(sys.argv[2] + "/snaps.npz")
j = np.searchsorted(sn["end"], ln.start.to_numpy(), side="right") - 1
ln["vola"] = sn["vola"][j]
ln["entry_t"] = pd.to_datetime(ln.start + MIN, utc=True)
t = base.copy()
t["entry_t"] = pd.to_datetime(t.entry_t, utc=True)
t = t.merge(ln, on="entry_t", how="left")
t["dev"] = 4 * t.vola / t.width
line = np.where(t.side == 1, t.bd, t.bu)
t["ldist"] = t.side * (t.px - line) / t.vola
t["v_bp"] = t.vola / t.px * 1e4
t["w_pct"] = t.width / t.px * 100
t["pnl_v"] = t.pnl_jpy / (t.qty1 * t.vola)  # ボラ単位(1 段目の量 × 1 ボラ = 1)
print(f"\n結べた取引 {t.vola.notna().sum():,} / {len(t):,}")

print("\n## 基準: 建ての時点の量の年ごとの中央値と、ボラ単位の損益\n")
print("| 年 | ボラ ÷ 値段(bp) | 幅 ÷ 値段(%) | 4 ボラ ÷ 幅 | ブレイクの線まで(ボラの何倍) | 1 本の円 | 1 本のボラ単位の損益 | 利確 1 本(ボラ単位) | ブレイク 1 本(ボラ単位) | 5 段まで足した割合 | 5 段の 1 本の円 |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for y in YEARS:
    x = t[t.y == y]
    c, b = x[x.exit_reason == "close"], x[x.exit_reason == "break"]
    l5 = x[x.levels >= 5]
    print(f"| {y} | {x.v_bp.median():.2f} | {x.w_pct.median():.3f} | {x.dev.median():.3f} | {x.ldist.median():.1f} | {x.pnl_jpy.mean():+.2f} | {x.pnl_v.mean():+.3f} | "
          f"{c.pnl_v.mean():+.2f} | {b.pnl_v.mean():+.2f} | {len(l5) / len(x):.2%} | {l5.pnl_jpy.mean():+.1f} |")

E = [-np.inf, 0.35, 0.42, 0.49, np.inf]
L = ["〜0.35", "0.35〜0.42", "0.42〜0.49", "0.49〜"]
t["band"] = pd.cut(t.dev, E, labels=L, right=False)
print("\n## 基準: 4 ボラ ÷ 幅 の帯 × 年(帯の境は全期間の分布の点 = 標本の中)\n")
print("| 年 | " + " | ".join(f"{b} 割合 / 1 本の円 / ブレイク割合" for b in L) + " | 1 本の円(実際) | 1 本の円(帯の割合を 2016〜2018 にそろえた値) |")
print("|---|" + "---|" * (len(L) + 2))
ref = t[t.y.between(2016, 2018)].band.value_counts(normalize=True).reindex(L)
for y in YEARS:
    x = t[t.y == y]
    share = x.band.value_counts(normalize=True).reindex(L)
    per = x.groupby("band", observed=False).pnl_jpy.mean().reindex(L)
    brk = x.groupby("band", observed=False).apply(lambda g: (g.exit_reason == "break").mean(), include_groups=False).reindex(L)
    cells = [f"{share[b]:.0%} / {per[b]:+.2f} / {brk[b]:.1%}" for b in L]
    print(f"| {y} | " + " | ".join(cells) + f" | {x.pnl_jpy.mean():+.2f} | {(per * ref).sum():+.2f} |")
