"""# 8 の読み口(TABLES.json だけから。値動きの足は読まない)。

1. 本体 − 対照(一致の割合): 本体と対照は同じ日を使うので、差の se の上限 se_本体 + se_対照 で保守の区間を作る
   (差の se は √(se² + se² − 2 共分散) で、se_本体 + se_対照 を越えない)。対照は 24 時間前・24 時間後と、その平均
   (平均の se の上限 = 2 つの se の平均)。
2. 主の量(区切り 15・15 分・約定・1 分目を除く)の 後半 − 前半: 前半・後半は重ならない日なので、
   各半分の 本体 − 対照平均 の保守の se を √(a² + b²) で合わせる。
3. 区切り 24 通り × 時間 4 の 本体 − 対照平均(約定・1 分目を除く。H=1 は「含む」しか無いので含む)の全期間・前半・後半。
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "..", "TABLES.json")))
C = d["cells"]
def cell(h, H, st, first, ctl, per):
    k = f"h{h}_H{H}_{st}_{first}_{ctl}"
    return C.get(k, {}).get(per, {}).get("agree")
def contrast(h, H, st, first, per):
    b = cell(h, H, st, first, "本体", per); a = cell(h, H, st, first, "24 時間前", per); f = cell(h, H, st, first, "24 時間後", per)
    if not (b and a and f):
        return None
    cm = (a["est"] + f["est"]) / 2; cse = (a["se"] + f["se"]) / 2
    out = {"b": b["est"], "pre": a["est"], "post": f["est"]}
    for nm, ce, cs in (("pre", a["est"], a["se"]), ("post", f["est"], f["se"]), ("avg", cm, cse)):
        dd = b["est"] - ce; se = b["se"] + cs
        out[nm + "_d"] = (dd, dd - 1.96 * se, dd + 1.96 * se, se)
    return out
def f4(t): return f"{t[0]:+.4f} [{t[1]:+.4f}, {t[2]:+.4f}]"
out = ["# # 8 の読み口(`contrast.py`。TABLES.json から)", "",
       "本体 − 対照 の区間は保守(差の se の上限 = se_本体 + se_対照)。対照平均 = (24 時間前 + 24 時間後) ÷ 2。", "",
       "## 1. 区切り 15 時(日本時間の日)の全部の形", "",
       "| 時間 | 起点 | 1 分目 | 期間 | 本体 | 24h 前 | 24h 後 | 本体 − 24h 前 | 本体 − 24h 後 | 本体 − 対照平均 |", "|---|---|---|---|---|---|---|---|---|---|"]
for H in (1, 5, 15, 60):
    for st in ("約定", "中ほど"):
        for first in ("含む", "除く"):
            for per in ("全期間", "前半", "後半"):
                c = contrast(15, H, st, first, per)
                if c is None:
                    continue
                out.append(f"| {H} | {st} | {first} | {per} | {c['b']:.4f} | {c['pre']:.4f} | {c['post']:.4f} | {f4(c['pre_d'])} | {f4(c['post_d'])} | {f4(c['avg_d'])} |")
out += ["", "## 2. 主の量の 後半 − 前半(区切り 15・15 分・約定・1 分目を除く)", ""]
a = contrast(15, 15, "約定", "除く", "前半")["avg_d"]; b = contrast(15, 15, "約定", "除く", "後半")["avg_d"]
dd = b[0] - a[0]; se = math.hypot(a[3], b[3])
out.append(f"後半 − 前半 = {dd:+.4f} [{dd - 1.96 * se:+.4f}, {dd + 1.96 * se:+.4f}](各半分の保守の se を √(a² + b²) で合わせた)")
out += ["", "## 3. 区切り 24 通り × 時間 4 の 本体 − 対照平均(約定。H = 1 は 1 分目を含む、ほかは除く)", "",
        "| 区切り(UTC 時) | 時間 | 全期間 | 前半 | 後半 |", "|---|---|---|---|---|"]
for h in range(24):
    for H in (1, 5, 15, 60):
        first = "含む" if H == 1 else "除く"
        cs = [contrast(h, H, "約定", first, per) for per in ("全期間", "前半", "後半")]
        if None in cs:
            continue
        out.append(f"| {h} | {H} | " + " | ".join(f4(c["avg_d"]) for c in cs) + " |")
open(os.path.join(HERE, "contrast.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out[:60]))

# 4. 主の量(区切り 15・15 分・約定・1 分目を除く)の年ごと(一致の割合と相関)
out2 = ["", "## 4. 主の量の年ごと(区切り 15・15 分・約定・1 分目を除く)", "",
        "年ごとは TABLES.json に区間が無い(点と日数だけ)。記述だけ。", "", "| 年 | 量 | 本体 | 24h 前 | 24h 後 | 本体 − 対照平均 | 日数 |", "|---|---|---|---|---|---|---|"]
base = "h15_H15_約定_除く_"
yrs = sorted(C[base + "本体"]["years"].keys())
for y in yrs:
    for q in ("agree", "corr"):
        b = C[base + "本体"]["years"][y].get(q); a = C[base + "24 時間前"]["years"].get(y, {}).get(q); f = C[base + "24 時間後"]["years"].get(y, {}).get(q)
        if not (b and a and f):
            continue
        dd = b["est"] - (a["est"] + f["est"]) / 2
        out2.append(f"| {y} | {'一致の割合' if q == 'agree' else '相関'} | {b['est']:+.4f} | {a['est']:+.4f} | {f['est']:+.4f} | {dd:+.4f} | {b.get('days', '')} |")
# 5. 主の量の相関(全期間・前半・後半)
out2 += ["", "## 5. 主の量の相関(全期間・前半・後半)", "", "| 期間 | 本体 | 24h 前 | 24h 後 | 本体 − 対照平均(保守) |", "|---|---|---|---|---|"]
for per in ("全期間", "前半", "後半"):
    b = C[base + "本体"][per]["corr"]; a = C[base + "24 時間前"][per]["corr"]; f = C[base + "24 時間後"][per]["corr"]
    cm = (a["est"] + f["est"]) / 2; se = b["se"] + (a["se"] + f["se"]) / 2; dd = b["est"] - cm
    out2.append(f"| {per} | {b['est']:+.4f} [{b['lo']:+.4f}, {b['hi']:+.4f}] | {a['est']:+.4f} | {f['est']:+.4f} | {dd:+.4f} [{dd - 1.96 * se:+.4f}, {dd + 1.96 * se:+.4f}] |")
# 6. 交差(区切り 15)
out2 += ["", "## 6. セッションの平均を値段が横切った割合と横切るまでの分(区切り 15)", "", "| 期間 | 数 | 横切った割合 | 分の四分位 25/50/75/90/99 |", "|---|---|---|---|"]
for per in ("全期間", "前半", "後半"):
    x = d["cross"]["15"][per]
    out2.append(f"| {per} | {x['n']} | {x['crossed_share']:.4f} | " + "/".join(f"{x['q'][k]:.0f}" for k in ("25", "50", "75", "90", "99")) + " |")
with open(os.path.join(HERE, "contrast.md"), "a") as fh:
    fh.write("\n".join(out2) + "\n")
print("\n".join(out2))

# 7. 区切りの間・半分の間・1 分目の有無・起点の違い(15 分・約定。保守の区間)
def avgd(h, H, st, first, per):
    return contrast(h, H, st, first, per)["avg_d"]
out3 = ["", "## 7. 比べ(15 分。本体 − 対照平均 どうし)", ""]
allpos = all(contrast(h, H, "約定", "含む" if H == 1 else "除く", per)["avg_d"][1] > 0
             for h in range(24) for H in (1, 5, 15, 60) for per in ("全期間", "前半", "後半"))
out3.append(f"- 区切り 24 × 時間 4 × 期間 3 = 288 行で、本体 − 対照平均 の保守の区間の下の端が全部 0 より上: {allpos}")
vals = sorted(((avgd(h, 15, "約定", "除く", "全期間")[0], h) for h in range(24)))
lo_h, hi_h = vals[0][1], vals[-1][1]
a, b = avgd(hi_h, 15, "約定", "除く", "全期間"), avgd(lo_h, 15, "約定", "除く", "全期間")
dd = a[0] - b[0]; se = a[3] + b[3]
out3.append(f"- 区切りの間(全期間): 一番大きい区切り {hi_h} 時 {a[0]:+.4f} − 一番小さい区切り {lo_h} 時 {b[0]:+.4f} = {dd:+.4f} [{dd - 1.96 * se:+.4f}, {dd + 1.96 * se:+.4f}](同じ日を使うので se の和。一番大きいと小さいは結果を見て選んだ)")
out3 += ["", "| 区切り(UTC 時) | 後半 − 前半(15 分・約定・除く。√(a² + b²)) |", "|---|---|"]
for h in range(24):
    p, q = avgd(h, 15, "約定", "除く", "前半"), avgd(h, 15, "約定", "除く", "後半")
    dd = q[0] - p[0]; se = math.hypot(p[3], q[3])
    out3.append(f"| {h} | {dd:+.4f} [{dd - 1.96 * se:+.4f}, {dd + 1.96 * se:+.4f}] |")
out3.append("")
for per in ("全期間", "前半", "後半"):
    inc, exc = avgd(15, 15, "約定", "含む", per), avgd(15, 15, "約定", "除く", per)
    mid = avgd(15, 15, "中ほど", "除く", per)
    d1 = inc[0] - exc[0]; s1 = inc[3] + exc[3]; d2 = mid[0] - exc[0]; s2 = mid[3] + exc[3]
    out3.append(f"- {per}: 1 分目を含む − 除く = {d1:+.4f} [{d1 - 1.96 * s1:+.4f}, {d1 + 1.96 * s1:+.4f}] / 起点 中ほど − 約定 = {d2:+.4f} [{d2 - 1.96 * s2:+.4f}, {d2 + 1.96 * s2:+.4f}](区切り 15・15 分。同じ分を使うので se の和。保守)")
# 対照そのものの 0.5 からの離れ
out3 += ["", "## 8. 対照そのものと本体の 0.5 からの離れ(区切り 15・15 分・約定・除く。各セルの台本の区間)", "", "| 期間 | 本体 − 0.5 | 24h 前 − 0.5 | 24h 後 − 0.5 |", "|---|---|---|---|"]
for per in ("全期間", "前半", "後半"):
    cs = [cell(15, 15, "約定", "除く", c, per) for c in ("本体", "24 時間前", "24 時間後")]
    out3.append(f"| {per} | " + " | ".join(f"{c['est'] - 0.5:+.4f} [{c['lo'] - 0.5:+.4f}, {c['hi'] - 0.5:+.4f}]" for c in cs) + " |")
with open(os.path.join(HERE, "contrast.md"), "a") as fh:
    fh.write("\n".join(out3) + "\n")

# 9. 相関の本体と対照(区切り 15・約定。時間 1 は 1 分目を含む、ほかは除く。各セルの台本の区間)
out4 = ["", "## 9. 相関の本体と 2 つの対照(区切り 15・約定。戻るなら負。各セルの台本の区間)", "",
        "| 時間 | 期間 | 本体 | 24h 前 | 24h 後 |", "|---|---|---|---|---|"]
for H in (1, 5, 15, 60):
    first = "含む" if H == 1 else "除く"
    for per in ("全期間", "前半", "後半"):
        cs = [C[f"h15_H{H}_約定_{first}_{c}"][per]["corr"] for c in ("本体", "24 時間前", "24 時間後")]
        out4.append(f"| {H} | {per} | " + " | ".join(f"{x['est']:+.4f} [{x['lo']:+.4f}, {x['hi']:+.4f}]" for x in cs) + " |")
with open(os.path.join(HERE, "contrast.md"), "a") as fh:
    fh.write("\n".join(out4) + "\n")

# 10. 一致の割合の対照 − 0.5 の時間ごと(区切り 15・約定。時間 1 は 1 分目を含む、ほかは除く)
out5 = ["", "## 10. 一致の割合の対照 − 0.5 の時間ごと(区切り 15・約定。各セルの台本の区間)", "",
        "| 時間 | 対照 | 全期間 | 前半 | 後半 |", "|---|---|---|---|---|"]
for H in (1, 5, 15, 60):
    first = "含む" if H == 1 else "除く"
    for c in ("24 時間前", "24 時間後"):
        xs = [cell(15, H, "約定", first, c, p) for p in ("全期間", "前半", "後半")]
        out5.append(f"| {H} | {c} | " + " | ".join(f"{x['est'] - 0.5:+.4f} [{x['lo'] - 0.5:+.4f}, {x['hi'] - 0.5:+.4f}]" for x in xs) + " |")
with open(os.path.join(HERE, "contrast.md"), "a") as fh:
    fh.write("\n".join(out5) + "\n")
