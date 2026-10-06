"""# 6 の起点の側の確かめ(分析のスキル D8「成行の約定の側も仮定」、分析の文書 P の (1) 跳ね返り)。

btc の g の終点と 1 時間の動き m の起点は、同じ値(週明けの行 r の bitFlyer の足 = 始まり r の 1 分足の終値)。
この値を、同じ足の中ほどの値(高値と安値の平均)に替えて g' = g + d、m' = m − d(d = ln(中ほど ÷ 終値)、bp)とし、
主の量(重み付きの戻りの割合 本体 − 対照)を作り直す。対照は起点が g の終点でないので替えない。
足は scripts/w4_measure/common.py の load_bars(封印の門を通る)で 2017-08〜2022-12 だけ読む。
区間 = 週を 1 件として選び直す(iid、1,000 回、種 20261006)。
"""
import csv, gzip, math, os, sys, datetime as dt
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../scripts/w4_measure"))
import common

HERE = os.path.dirname(os.path.abspath(__file__))
NS = 10**9
rows = list(csv.DictReader(gzip.open(os.path.join(HERE, "..", "weeks.csv.gz"), "rt")))
def ns(s): return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()) * NS
rt = np.array([ns(r["r"]) for r in rows], dtype=np.int64)
d = np.full(len(rows), np.nan)
years = sorted({dt.datetime.utcfromtimestamp(t / NS).year for t in rt})
for y in years:
    lo = int(dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc).timestamp()) * NS
    hi = int(dt.datetime(y + 1, 1, 1, tzinfo=dt.timezone.utc).timestamp()) * NS
    bars, _, _ = common.load_bars(common.FX_DIR, "FX_BTC_JPY", lo, hi)
    by = {int(b.start_time_ns): b for b in bars}
    for i, t in enumerate(rt):
        if lo <= t < hi and t in by:
            b = by[t]
            d[i] = math.log((float(b.high) + float(b.low)) / 2 / float(b.close)) * 1e4
g = np.array([float(r["g_btc_bp"]) for r in rows]); m = np.array([float(r["m_btc_bp"]) for r in rows])
cr = np.array([float(r["ctrl_ratio_btc"]) for r in rows])
ok = np.isfinite(d) & np.isfinite(cr) & (g != 0)
g2, m2 = g + d, m - d
def wr(gg, mm, i): return (-mm * np.sign(gg))[i].sum() / np.abs(gg[i]).sum()
def ctrl(gg, i):  # 対照の分子は g の符号と |g| に依る: ctrl_ratio × |g| は g で作った値なので、g' では −m_c·sign g' = ctrl_ratio·g·sign g'
    return (cr * g * np.sign(gg))[i].sum() / np.abs(gg[i]).sum()
half = np.arange(len(rows)) >= len(rows) // 2
rng0 = 20261006
out = ["# # 6 起点の側の確かめ(`mid_start.py`)", "",
       f"起点の足が見つかった週: {int(np.isfinite(d).sum())} / {len(rows)}。d = ln(中ほど ÷ 終値) の分位 5/25/50/75/95 % = "
       + " / ".join(f"{x:+.2f}" for x in np.nanpercentile(d, [5, 25, 50, 75, 95])) + " bp。|d| の平均 ÷ |g| の平均 = "
       + f"{np.nanmean(np.abs(d)) / np.mean(np.abs(g)):.4f}。", "",
       "| 期間 | 起点 | 本体 | 対照 | 本体 − 対照 |", "|---|---|---|---|---|"]
for p, mask in {"全期間": np.ones(len(rows), bool), "前半": ~half, "後半": half}.items():
    idx = np.where(mask & ok)[0]
    for name, gg, mm in (("終値(台本)", g, m), ("中ほど", g2, m2)):
        rng = np.random.default_rng(rng0)
        def st(i): return (wr(gg, mm, i), ctrl(gg, i), wr(gg, mm, i) - ctrl(gg, i))
        est = st(idx)
        bs = np.array([st(rng.choice(idx, len(idx))) for _ in range(1000)])
        lo, hi = np.percentile(bs, 2.5, axis=0), np.percentile(bs, 97.5, axis=0)
        out.append(f"| {p} | {name} | " + " | ".join(f"{est[k]:+.3f} [{lo[k]:+.3f}, {hi[k]:+.3f}]" for k in range(3)) + " |")
open(os.path.join(HERE, "mid_start.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
