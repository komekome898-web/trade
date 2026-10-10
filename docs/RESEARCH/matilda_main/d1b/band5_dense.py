"""リードが書いた(数えるだけ)。D1b の帯 5 の逆向き(観察 15・K-365)が、足の欠け(疎らさ)の癖かを分ける数え直し。相方の D9b の指摘 5。
帯の境は run_d1b.py と同じ(前半の起点の五分位)。帯 5 の前半の起点の年の内訳と、足の揃った起点(n_win ≥ 36)だけの前半・後半の i・iv。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/d1b/band5_dense.py > docs/RESEARCH/matilda_main/d1b/band5_dense.out
入力 data/d1b/records.pkl(run_d1b.py が書いた。git の外)。"""
import pickle, sys
from collections import Counter
import numpy as np
sys.path.insert(0, "scripts/analysis")
import d1b_matilda as d1b
res = pickle.load(open("data/d1b/records.pkl", "rb"))
recs = res["records"]
CUT = d1b.CUT
VARS = {"幅÷ボラ": lambda r: r["width"] / r["vola"],
        "ブレイクの線までの距離÷ボラ": lambda r: None if r["break_line"] is None else abs(r["break_line"] - r["c0"]) / r["vola"]}
sh = lambda s, l: 100 * sum(r["outcome"] == l for r in s) / len(s) if s else float("nan")
for view in ("entry_open", "point_open"):
    sel = [r for r in recs if d1b._VIEW_FILTER[view](r)]
    first = [r for r in sel if r["day"] < CUT]; second = [r for r in sel if r["day"] >= CUT]
    for name, fn in VARS.items():
        e4 = np.percentile([fn(r) for r in first if fn(r) is not None], 80)
        b5f = [r for r in first if fn(r) is not None and fn(r) >= e4]
        b5s = [r for r in second if fn(r) is not None and fn(r) >= e4]
        yrs = Counter(r["day"][:4] for r in b5f)
        df = [r for r in b5f if r["n_win"] >= 36]; ds = [r for r in b5s if r["n_win"] >= 36]
        print(f"{view} {name} 帯 5(境 {e4:.2f} 以上): 前半 {len(b5f)} 本の年 " + " ".join(f"{y}:{n}" for y, n in sorted(yrs.items())))
        print(f"  全部: 前半 i {sh(b5f,'i'):.1f} iv {sh(b5f,'iv'):.1f} / 後半 i {sh(b5s,'i'):.1f} iv {sh(b5s,'iv'):.1f}")
        print(f"  n_win≥36: 前半 {len(df)} 本 i {sh(df,'i'):.1f} iv {sh(df,'iv'):.1f} / 後半 {len(ds)} 本 i {sh(ds,'i'):.1f} iv {sh(ds,'iv'):.1f}")
        nf = [r for r in b5f if r["day"][:4] not in ("2015", "2016")]
        print(f"  2015・2016 年を除く前半: {len(nf)} 本 i {sh(nf,'i'):.1f} iv {sh(nf,'iv'):.1f}")
