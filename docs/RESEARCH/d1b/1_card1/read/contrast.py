"""# 1 の読み口(result.json だけから。値動きの足は読まない)。

1. 3 つの量(持つ先 bitFlyer・Binance・差)の 後半 − 前半(重ならない日なので √(a² + b²))。
2. 差 − 対照平均((24 時間前 + 24 時間後)÷ 2)。実と対照は同じ日を使うので se の上限 se_実 + (se_前 + se_後)÷ 2 の保守の区間。
   全期間・前半・後半・年ごと(年ごとも台本の区間がある)。
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "..", "result.json")))["損益(bp/日)"]
Q = ("bitFlyer", "Binance", "bitFlyer − Binance")
out = ["# # 1 の読み口(`contrast.py`。result.json から)", "", "単位 bp/日(持ち高 1 単位、経費の前)。", "",
       "## 1. 後半 − 前半(√(a² + b²))", "", "| 量 | 前半 | 後半 | 後半 − 前半 |", "|---|---|---|---|"]
for q in Q:
    a, b = d["実"][q]["前半"], d["実"][q]["後半"]
    dd = b["estimate"] - a["estimate"]; se = math.hypot(a["se"], b["se"])
    out.append(f"| {q} | {a['estimate']:+.2f} | {b['estimate']:+.2f} | {dd:+.2f} [{dd - 1.96 * se:+.2f}, {dd + 1.96 * se:+.2f}] |")
out += ["", "## 2. 実 − 対照平均(保守の区間)", "", "| 量 | 区切り | 実 | 24h 前 | 24h 後 | 実 − 対照平均 |", "|---|---|---|---|---|---|"]
def cell(c, q, per):
    x = d[c][q]
    return x[per] if per in x else x["年ごと(記述)"][per]
for q in Q:
    for per in ["全期間", "前半", "後半"] + [str(y) for y in range(2017, 2024)]:
        r, a, f = cell("実", q, per), cell("24 時間前", q, per), cell("24 時間後", q, per)
        cm = (a["estimate"] + f["estimate"]) / 2; se = r["se"] + (a["se"] + f["se"]) / 2; dd = r["estimate"] - cm
        out.append(f"| {q} | {per} | {r['estimate']:+.2f} | {a['estimate']:+.2f} | {f['estimate']:+.2f} | {dd:+.2f} [{dd - 1.96 * se:+.2f}, {dd + 1.96 * se:+.2f}] |")
open(os.path.join(HERE, "contrast.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
