"""リードが書いた(数えるだけ。委任・批評家を通していない。前例 both_halves.py)。前提の直接の測り(D1b)の全期間の走らせと、層に分けた比べ。

台本 `scripts/analysis/d1b_matilda.py`(委任で作った。L-929)の starts を全期間の足に当て、台本の出力(day_counts.csv・tables.md)を書いたうえで、
作り終えた後の批評家 1 回目(`docs/AUDITOR/VERDICTS/2026-10-10_matilda_d1b_critic1.md`)の応答のとおり、次を足す:
  1. 年ごとの足の数(読んだ・飛ばさない・評価した・ボラ ≤ 0)・ts が +00:00 でない行の数・起点の数と率・n_win の中央値
  2. tables.md の主な値(4 つの見方 × 前半・後半 × 5 つの結果の割合)を、起点の記録から独立に数え直した値との突き合わせ
  3. 層に分けた比べ: 外れの深さ(|c0 − 中心| ÷ ボラ)・幅 ÷ ボラ・ブレイクの線までの距離 ÷ ボラ の帯(境 = 前半の起点の五分位。前半で決めて後半に当てる)
     の中で、前半と後半の割合と差の区間(台本の ratio_diff_ci)。足の揃った起点(n_win ≥ 36)だけの前半・後半。
  4. 後半の割合を前半の帯の混ざり方にそろえた値(直接の標準化。記述、区間なし): 混ざり方の違い と 帯の中の戻り方の違い を分ける。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/d1b/run_d1b.py > docs/RESEARCH/matilda_main/d1b/run_d1b.out
封印の境(2023-12-17T15:00Z)より後の足は読まない(read_bars と台本の starts が境で止める)。2024 年以後のファイルは渡さない。
"""
import glob
import os
import pickle
import statistics
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, "scripts/analysis")
import d1b_matilda as d1b  # noqa: E402
from bot.bt.simple import read_bars  # noqa: E402

OUT = "docs/RESEARCH/matilda_main/d1b"
F = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz"))
F = [f for f in F if int(f[-11:-7]) <= 2023]
DENSE = 36  # 足の揃った起点: 40 分のうち 9 割以上の分に足がある(リードが決めた値。批評家の 2016 年の n_win の区分を見た後)
CUT = d1b.CUT

cnt = defaultdict(lambda: defaultdict(int))


class Counting(d1b.MatildaSimple):
    def decide(self, ev):
        r = super().decide(ev)
        y = ev["ts"][:4]
        cnt[y]["飛ばさない足"] += 1
        sn = self._snap
        if sn is not None:
            if sn["vola"] <= 0:
                cnt[y]["ボラ ≤ 0 の足"] += 1
            else:
                cnt[y]["評価した足"] += 1
        return r


d1b.MatildaSimple = Counting


def wrap(bars):
    for b in bars:
        y = b[0][:4]
        cnt[y]["読んだ足"] += 1
        if not b[0].endswith("+00:00"):
            cnt[y]["ts が +00:00 でない行"] += 1
        yield b


t0 = time.time()
print("ファイル:", " ".join(os.path.basename(f) for f in F))
res = d1b.starts(wrap(read_bars(F, d1b.SEAL)), d1b.base_params(), d1b.SEAL)
recs, days = res["records"], res["days"]
d1b.write_outputs(OUT, res)
os.makedirs("data/d1b", exist_ok=True)
with open("data/d1b/records.pkl", "wb") as fh:  # git の外(数え直し用)
    pickle.dump(res, fh)
print(f"走らせの時間 {time.time() - t0:.0f} 秒・起点 {len(recs)}・日 {len(days)}・最初の日 {days[0]}・最後の日 {days[-1]}")

# 1. 年ごとの数
print("\n## 1. 年ごとの足と起点")
print("| 年 | 読んだ足 | ts が +00:00 でない | 飛ばさない足 | 評価した足 | ボラ ≤ 0 | 起点(時点・全部) | 起点の率 | point_open | entry_open | n_win 中央値 |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
by_y = defaultdict(list)
for r in recs:
    by_y[r["day"][:4]].append(r)
for y in sorted(cnt):
    c, rs = cnt[y], by_y.get(y, [])
    po = sum(1 for r in rs if d1b._VIEW_FILTER["point_open"](r))
    eo = sum(1 for r in rs if d1b._VIEW_FILTER["entry_open"](r))
    rate = len(rs) / c["評価した足"] if c["評価した足"] else float("nan")
    med = statistics.median([r["n_win"] for r in rs]) if rs else float("nan")
    print(f"| {y} | {c['読んだ足']} | {c['ts が +00:00 でない行']} | {c['飛ばさない足']} | {c['評価した足']} | {c['ボラ ≤ 0 の足']} | {len(rs)} | {100*rate:.1f}% | {po} | {eo} | {med:g} |")

# 2. tables.md の主な値の突き合わせ
summ = d1b.summarize(recs, days)
worst = 0.0
for v, f in d1b._VIEW_FILTER.items():
    for per, keep in (("first", lambda d: d < CUT), ("second", lambda d: d >= CUT)):
        sel = [r for r in recs if f(r) and keep(r["day"])]
        for lab in d1b.LABELS:
            mine = sum(r["outcome"] == lab for r in sel) / len(sel)
            worst = max(worst, abs(mine - summ[v][per][lab]["share"]))
print(f"\n## 2. tables.md の割合と、起点の記録からの数え直しの差の最大: {worst:.3g}(0 なら一致)")


# 3・4. 層に分けた比べ
def dev(r):
    return abs(r["c0"] - r["center"]) / r["vola"]


def wv(r):
    return r["width"] / r["vola"]


def bkd(r):
    return None if r["break_line"] is None else abs(r["break_line"] - r["c0"]) / r["vola"]


VARS = (("外れの深さ |c0−中心|÷ボラ", dev), ("幅÷ボラ", wv), ("ブレイクの線までの距離÷ボラ", bkd))
fdays = [d for d in days if d < CUT]
sdays = [d for d in days if d >= CUT]


def per_day(sel, lab=None):
    out = defaultdict(int)
    for r in sel:
        if lab is None or r["outcome"] == lab:
            out[r["day"]] += 1
    return out


def share(sel, lab):
    return sum(r["outcome"] == lab for r in sel) / len(sel) if sel else float("nan")


def pct(x):
    return "-" if x is None or x != x else f"{100*x:.1f}"


for view in ("entry_open", "point_open"):
    f = d1b._VIEW_FILTER[view]
    sel = [r for r in recs if f(r)]
    first = [r for r in sel if r["day"] < CUT]
    second = [r for r in sel if r["day"] >= CUT]
    print(f"\n## 3. 層に分けた比べ — {view}({d1b.VIEW_NAMES[view]})。前半 {len(first)}・後半 {len(second)}")
    print(f"全体: 前半 i {pct(share(first,'i'))}% iii {pct(share(first,'iii'))}% iv {pct(share(first,'iv'))}% / "
          f"後半 i {pct(share(second,'i'))}% iii {pct(share(second,'iii'))}% iv {pct(share(second,'iv'))}%")
    for name, fn in VARS:
        fv = np.array([fn(r) for r in first if fn(r) is not None])
        edges = list(np.percentile(fv, [20, 40, 60, 80]))
        def band(r):
            x = fn(r)
            return None if x is None else int(np.searchsorted(edges, x, side="right"))
        print(f"\n### {name}(帯の境は前半の起点の五分位 = {', '.join(f'{e:.2f}' for e in edges)}。帯の境は前半で決めて後半に当てた)")
        print("| 帯 | 前半の数 | 後半の数 | 前半 i | 後半 i | i の差 [区間] | 前半 iii | 後半 iii | iii の差 [区間] | 前半 iv | 後半 iv | iv の差 [区間] |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|")
        fb = defaultdict(list); sb = defaultdict(list)
        for r in first:
            b = band(r)
            if b is not None: fb[b].append(r)
        for r in second:
            b = band(r)
            if b is not None: sb[b].append(r)
        for b in range(5):
            row = [f"{b+1}", str(len(fb[b])), str(len(sb[b]))]
            for lab in ("i", "iii", "iv"):
                dci = d1b.ratio_diff_ci(fdays, per_day(fb[b], lab), per_day(fb[b]), sdays, per_day(sb[b], lab), per_day(sb[b]))
                row += [pct(share(fb[b], lab)), pct(share(sb[b], lab)),
                        f"{pct(dci['mean'])} [{pct(dci['lo'])}, {pct(dci['hi'])}]" if dci["mean"] is not None else "-"]
            print("| " + " | ".join(row) + " |")
        # 4. 直接の標準化: 後半の帯ごとの割合を、前半の帯の混ざり方で重み付け
        nf = sum(len(fb[b]) for b in range(5)); ns = sum(len(sb[b]) for b in range(5))
        for lab in ("i", "iii", "iv"):
            std = sum(len(fb[b]) / nf * share(sb[b], lab) for b in range(5) if sb[b])
            print(f"- {lab}: 前半 {pct(share(sum((fb[b] for b in range(5)), []), lab))}% / 後半そのまま {pct(share(sum((sb[b] for b in range(5)), []), lab))}% / "
                  f"後半を前半の帯の混ざり方にそろえた値 {pct(std)}%(帯の中の違いだけが残る)。後半の帯の混ざり方: "
                  + " ".join(f"{100*len(sb[b])/ns:.0f}%" for b in range(5)))
    dense_f = [r for r in first if r["n_win"] >= DENSE]
    dense_s = [r for r in second if r["n_win"] >= DENSE]
    print(f"\n### 足の揃った起点だけ(n_win ≥ {DENSE}): 前半 {len(dense_f)}・後半 {len(dense_s)}")
    for lab in d1b.LABELS:
        dci = d1b.ratio_diff_ci(fdays, per_day(dense_f, lab), per_day(dense_f), sdays, per_day(dense_s, lab), per_day(dense_s))
        print(f"- {lab}: 前半 {pct(share(dense_f, lab))}% / 後半 {pct(share(dense_s, lab))}% / 差 {pct(dci['mean'])} [{pct(dci['lo'])}, {pct(dci['hi'])}] MDE {pct(dci['mde'])}")
print(f"\n全体の時間 {time.time() - t0:.0f} 秒")
