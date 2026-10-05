"""カード 1 の D2: 前の日のボラの区分(vol_split_daily.classify、判断の時点で分かる)× 前半・後半。
入力: 保存済みの daily.csv(走らせ直さない)と、封印の門から読む bitFlyer FX の 1 分足(終値だけ)。
前半・後半の境は diag_tables と同じ(日数で 2 つ)。区間は diag_tables.mean_ci(日の塊 5 日・1,000 回・種 20261004)。"""
import json
import os
import sys

REPO = "/home/user/trade"
sys.path.insert(0, os.path.join(REPO, "scripts/analysis"))
sys.path.insert(0, os.path.join(REPO, "scripts/w4_measure"))
sys.path.insert(0, os.path.join(REPO, "src"))
import diag_tables as dt  # noqa: E402
import vol_split_daily as vs  # noqa: E402

daily = {}
for line in open(os.path.join(REPO, "docs/RESEARCH/cards/c1_xborder_mom/measure/default/daily.csv")).read().splitlines()[1:]:
    d, p, n = line.split(",")
    daily[d] = float(p)
days = sorted(daily)
half = len(days) // 2
first, second = set(days[:half]), set(days[half:])
cls = vs.classify(vs.daily_vol(vs.load_closes_by_day()))
out = {"half_edges": [days[0], days[half - 1], days[half], days[-1]], "rows": []}
for c in ("low", "mid", "high"):
    for name, part in (("全期間", set(days)), ("前半", first), ("後半", second)):
        x = [daily[d] for d in days if d in part and cls.get(d) == c]
        r = dt.mean_ci(x) if len(x) > 10 else {"n": len(x)}
        out["rows"].append({"class": c, "part": name, "days": len(x), **r})
no_cls = [d for d in days if d not in cls]
out["days_without_class"] = len(no_cls)
out["days_without_class_first_last"] = [no_cls[0], no_cls[-1]] if no_cls else None
json.dump(out, open(os.path.join(os.path.dirname(__file__), "d2_volsplit_halves.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# 追加(アドバイザーの指摘 2): 年 × 前の日の区分(日数・和・1 日あたり。区間なし)と、損益がちょうど 0 の日の数
import collections
yc = collections.defaultdict(list)
for d in days:
    yc[(d[:4], cls[d])].append(daily[d])
rows2 = []
for y in sorted({d[:4] for d in days}):
    for c in ("low", "mid", "high"):
        v = yc.get((y, c), [])
        rows2.append({"year": y, "class": c, "days": len(v), "sum": sum(v), "mean": (sum(v) / len(v)) if v else None,
                      "zero_days": sum(1 for x in v if x == 0)})
json.dump(rows2, open(os.path.join(os.path.dirname(__file__), "d2_year_class.json"), "w"), ensure_ascii=False, indent=1)
for r in rows2:
    print(r)
