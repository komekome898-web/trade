"""# 9 の読み口(result_coinm.json・result_spot.json だけから。値動きの足は読まない)。

清算 − 対照 (ii): 清算と対照は別の時刻の集まりだが同じ日を使うので、差の se の上限 se_清算 + se_対照 で保守の区間を作る
(日ごとの値は保存されていない)。後半 − 前半 は重ならない日なので √(a² + b²)。量は Binance・bitFlyer・bitFlyer − Binance、
時間 1・5・15・60 分。値は bp、清算の向き(対照は直前の勢いの向き)に正。
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
out = ["# # 9 の読み口(`contrast.py`。result_*.json から)", "",
       "清算 − 対照 (ii) の区間は保守(差の se の上限 = se_清算 + se_対照)。単位 bp、清算の向きに正。", ""]
for name in ("coinm", "spot"):
    t = json.load(open(os.path.join(HERE, "..", f"result_{name}.json")))["表"]
    out += [f"## Binance = {name}", "", "| 時間 | 量 | 期間 | 清算 | 対照 (ii) | 清算 − 対照 |", "|---|---|---|---|---|---|"]
    halves = {}
    for H in (1, 5, 15, 60):
        for q in ("Binance", "bitFlyer", "bitFlyer − Binance"):
            for per in ("全期間", "前半", "後半"):
                a = t[f"清算|{H}分|{q}"][per]; c = t[f"対照 (ii)|{H}分|{q}"][per]
                d = a["estimate"] - c["estimate"]; se = a["se"] + c["se"]
                halves[(H, q, per)] = (d, se)
                out.append(f"| {H} | {q} | {per} | {a['estimate']:+.2f} [{a['ci'][0]:+.2f}, {a['ci'][1]:+.2f}] | {c['estimate']:+.2f} | {d:+.2f} [{d - 1.96 * se:+.2f}, {d + 1.96 * se:+.2f}](MDE {2.8 * se:.2f}) |")
    out += ["", "| 時間 | 量 | 清算 − 対照 の 後半 − 前半(√(a² + b²)) |", "|---|---|---|"]
    for H in (1, 5, 15, 60):
        for q in ("Binance", "bitFlyer", "bitFlyer − Binance"):
            (d1, s1), (d2, s2) = halves[(H, q, "前半")], halves[(H, q, "後半")]
            dd, se = d2 - d1, math.hypot(s1, s2)
            out.append(f"| {H} | {q} | {dd:+.2f} [{dd - 1.96 * se:+.2f}, {dd + 1.96 * se:+.2f}] |")
    out.append("")
open(os.path.join(HERE, "contrast.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
