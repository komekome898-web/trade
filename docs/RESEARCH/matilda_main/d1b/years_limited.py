"""リードが書いた(数えるだけ)。D1b の前半・後半の差が、足の欠けの多い年(2015・2016・2023)で作られていないかの感度の記述。
前半を 2017〜2019 年・後半を 2020〜2022 年に限って、5 つの結果の割合の差と区間(台本の ratio_diff_ci、日はその年の評価した日)を出す。
年の境は結果を見てから切った(感度の記述。判定は見る前に決めた境 2019-12-09 のまま)。相方の D10 の指摘 2。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/d1b/years_limited.py > docs/RESEARCH/matilda_main/d1b/years_limited.out
入力 data/d1b/records.pkl(run_d1b.py が書いた。git の外)。"""
import pickle, sys
from collections import defaultdict
sys.path.insert(0, "scripts/analysis")
import d1b_matilda as d1b
res = pickle.load(open("data/d1b/records.pkl", "rb"))
recs, days = res["records"], res["days"]
A, B = ("2017", "2018", "2019"), ("2020", "2021", "2022")
da = [d for d in days if d[:4] in A]; db = [d for d in days if d[:4] in B]
def cnt(sel, lab=None):
    o = defaultdict(int)
    for r in sel:
        if lab is None or r["outcome"] == lab: o[r["day"]] += 1
    return o
for view in ("entry_open", "point_open", "entry_all", "point_all"):
    f = d1b._VIEW_FILTER[view]
    sa = [r for r in recs if f(r) and r["day"][:4] in A]; sb = [r for r in recs if f(r) and r["day"][:4] in B]
    print(f"{view}: 2017〜2019 年 {len(sa)} 本・2020〜2022 年 {len(sb)} 本")
    for lab in d1b.LABELS:
        c = d1b.ratio_diff_ci(da, cnt(sa, lab), cnt(sa), db, cnt(sb, lab), cnt(sb))
        pa = 100 * sum(r["outcome"] == lab for r in sa) / len(sa); pb = 100 * sum(r["outcome"] == lab for r in sb) / len(sb)
        print(f"  {lab}: {pa:.1f}% → {pb:.1f}%  差 {100*c['mean']:+.1f} [{100*c['lo']:+.1f}, {100*c['hi']:+.1f}] MDE {100*c['mde']:.1f} pt")
