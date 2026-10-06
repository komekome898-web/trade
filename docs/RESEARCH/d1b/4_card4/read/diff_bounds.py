"""前提の直接の測り # 4 の主の量(離れ − 対照)の差を、TABLES.json の各群の点と se から出す(2026-10-06、読みの段)。

出力に差の区間が無い(台本は群ごとの日の塊の区間だけを出した)ので、2 つの幅で並べる:
- 保守の幅: se の上限 = se(離れ) + se(対照)。2 つの群の相関がどうであっても sd(X − Y) ≤ sd(X) + sd(Y)。
- 独立の幅: se = √(se(離れ)² + se(対照)²)(同じ日の群どうしは正に相関しうるので、独立より狭いのが本当の幅に近い)。
区間 = 差 ± 1.96 × se。MDE = 2.8 × se。量: retA(中心へ戻る割合)・retB(建値から 0.8 × 平均実体戻る割合)・advA / advB(戻る前の一番深い不利な点の平均、bp)。

    python3 docs/RESEARCH/d1b/4_card4/read/diff_bounds.py
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "..", "TABLES.json"), encoding="utf-8"))
QS = (("retA", "中心へ戻る割合", 1), ("retB", "建値から 0.8 × 平均実体戻る割合", 1),
      ("advA", "戻る前の不利 A(bp)", 0), ("advB", "戻る前の不利 B(bp)", 0))


def f(x, pct):
    return f"{x * 100:+.2f} pt" if pct else f"{x:+.2f}"


def rows(src_a, src_b, label):
    out = []
    for per in ("全期間", "前半", "後半"):
        a, b = src_a[per], src_b[per]
        for k, name, pct in QS:
            d = a[k]["est"] - b[k]["est"]
            s_cons = a[k]["se"] + b[k]["se"]
            s_ind = math.hypot(a[k]["se"], b[k]["se"])
            va = f"{a[k]['est']:.3f}" if pct else f(a[k]["est"], 0)
            vb = f"{b[k]['est']:.3f}" if pct else f(b[k]["est"], 0)
            out.append(f"| {label} | {per} | {name} | {va} | {vb} | {f(d, pct)} | "
                       f"[{f(d - 1.96 * s_cons, pct)}, {f(d + 1.96 * s_cons, pct)}] | "
                       f"[{f(d - 1.96 * s_ind, pct)}, {f(d + 1.96 * s_ind, pct)}] | {f(2.8 * s_cons, pct)} |")
    return out


L = ["# # 4 の主の量: 離れ − 対照(TABLES.json の点と se から。`diff_bounds.py` が出した)", "",
     "| 群の比べ | 期間 | 量 | 離れ | 対照 | 離れ − 対照 | 区間(保守: se の和) | 区間(独立とみた) | MDE(保守) |",
     "|---|---|---|---|---|---|---|---|---|"]
L += rows(D["groups"]["離れ"], D["groups"]["対照(離れていない足)"], "全部")
rb = D["ratio_bins"]
for lab in [k for k in rb["離れ"].keys()]:
    if isinstance(rb["離れ"][lab], dict) and "全期間" in rb["離れ"][lab]:
        L += rows(rb["離れ"][lab], rb["対照(離れていない足)"][lab], f"比 {lab}")
out = os.path.join(HERE, "diff_bounds.md")
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print(out)
