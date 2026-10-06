"""# 7 の読み口(TABLES.json だけから。値動きの足は読まない)。

1. 後半 − 前半: 前半と後半は重ならない日の集まりで、それぞれ日の塊で別に区間を作っているので、差の se を
   √(se_前半² + se_後半²) として 95% の区間を付ける(独立の 2 群の差。正規近似)。境の日をまたぐ塊の依存は入れていない。
2. 流れの分 δ: (前が上 → 続き) − (前が下 → 続き) の半分。流れが無ければ 0。窓・期間ごとの点(区間なし)。
3. 0.5 との位置: 主の量(流れを抜いた値)の区間の端を小数 4 桁で出す(表は 3 桁で丸めている)。
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "..", "TABLES.json")))
out = ["# # 7 の読み口(`half_diff.py`。TABLES.json から)", "",
       "後半 − 前半 の区間 = 点 ± 1.96 × √(se_前半² + se_後半²)(前半・後半は重ならない日。独立の 2 群の差の正規近似)。", "",
       "| 窓 | 帯 | 量 | 前半 [区間] | 後半 [区間] | 後半 − 前半 [区間] | 流れの分 δ 前半 / 後半 |", "|---|---|---|---|---|---|---|"]
def g(x, k): return x.get(k) if isinstance(x, dict) else None
for win, wd in d["windows"].items():
    for band, bd in wd["cont"].items():
        for qty in ("detrended", "cont"):
            a, b = bd.get("前半", {}), bd.get("後半", {})
            qa, qb = a.get(qty) or {}, b.get(qty) or {}
            if not qa or qa.get("est") is None or qb.get("est") is None or qa.get("se") is None or qb.get("se") is None:
                continue
            diff = qb["est"] - qa["est"]; se = math.sqrt(qa["se"] ** 2 + qb["se"] ** 2)
            def dl(x):
                u, dn = (x.get("after_up") or {}).get("est"), (x.get("after_down") or {}).get("est")
                return "—" if u is None or dn is None else f"{(u - dn) / 2:+.4f}"
            out.append(f"| {win} | {band} | {'流れを抜いた値' if qty == 'detrended' else 'そのまま'} | {qa['est']:.4f} [{qa['lo']:.4f}, {qa['hi']:.4f}] | "
                       f"{qb['est']:.4f} [{qb['lo']:.4f}, {qb['hi']:.4f}] | {diff:+.4f} [{diff - 1.96 * se:+.4f}, {diff + 1.96 * se:+.4f}] | {dl(a)} / {dl(b)} |")
# 4(監査役 1 回目の直す 4): 流れを抜いた値の 低い帯 − 高い帯。2 つの帯は同じ日を使うので、差の se の上限 se_低 + se_高 で
# 保守の区間を作る(差の se は √(se_低² + se_高² − 2 共分散) で、共分散が正でも負でも se_低 + se_高 を越えない)。
out += ["", "## 流れを抜いた値の 低い帯 − 高い帯(保守の区間: 差の se の上限 = se_低 + se_高)", "",
        "| 窓 | 期間 | 低い帯 | 高い帯 | 低 − 高 [保守の区間] | 台本のそのままの続きの割合の 低 − 高 |", "|---|---|---|---|---|---|"]
for win, wd in d["windows"].items():
    bands = [b for b in wd["cont"] if b != "全部"]
    lo_b, hi_b = bands[0], bands[-1]
    for per in ("全期間", "前半", "後半"):
        a = wd["cont"][lo_b].get(per, {}).get("detrended") or {}
        b = wd["cont"][hi_b].get(per, {}).get("detrended") or {}
        if a.get("se") is None or b.get("se") is None:
            continue
        diff = a["est"] - b["est"]; se = a["se"] + b["se"]
        orig = wd["diff_low_minus_high"].get(per, {})
        out.append(f"| {win} | {per} | {a['est']:.4f} | {b['est']:.4f} | {diff:+.4f} [{diff - 1.96 * se:+.4f}, {diff + 1.96 * se:+.4f}] | "
                   f"{orig.get('est', float('nan')):+.4f} [{orig.get('lo', float('nan')):+.4f}, {orig.get('hi', float('nan')):+.4f}] |")
open(os.path.join(HERE, "half_diff.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
