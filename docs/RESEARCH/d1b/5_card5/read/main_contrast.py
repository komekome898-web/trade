"""前提の直接の測り # 5 の主の量(朝の窓の一致の割合 − ほかの 23 窓の一致の割合の平均)を、TABLES.json から出す(2026-10-06、読みの段)。

台本は窓ごとの差(朝の窓 − 窓 k、同じ日の抽き直しで両方を作った区間)を出したが、23 窓の平均との差は出していない。
- 点 = 23 本の差の点の平均(= 朝の窓 − 23 窓の割合の平均。各窓の割合は日 × 分 をまとめた割合)。
- se の上限 = 23 本の差の se の平均(平均の sd は sd の平均を越えない。差どうしの相関によらない保守の幅)。
- 区間 = 点 ± 1.96 × se の上限。MDE = 2.8 × se の上限。r̄ の差も同じ形で並べる。
窓の並び(各窓の一致の割合と r̄)も、時刻の関数として 1 行ずつ写す。

    python3 docs/RESEARCH/d1b/5_card5/read/main_contrast.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "..", "TABLES.json"), encoding="utf-8"))
PER = ("全期間", "前半", "後半")
KS = [str(k) for k in range(1, 24)]

L = ["# # 5 の主の量: 朝の窓 − ほかの 23 窓の平均(`main_contrast.py` が出した)", "",
     "| 量 | 期間 | 点 | 区間(保守: 差の se の平均) | MDE(保守) | 窓ごとの差で 0 より上 / 含む / 下 の数 |", "|---|---|---|---|---|---|"]
for q, name in (("agree", "一致の割合"), ("corr_tmean", "r̄")):
    for per in PER:
        ds = [D["diff_morning_minus_k"][k][per][q] for k in KS]
        pt = sum(x["est"] for x in ds) / len(ds)
        se = sum(x["se"] for x in ds) / len(ds)
        up = sum(1 for x in ds if x["lo"] > 0)
        dn = sum(1 for x in ds if x["hi"] < 0)
        L.append(f"| {name} | {per} | {pt:+.4f} | [{pt - 1.96 * se:+.4f}, {pt + 1.96 * se:+.4f}] | {2.8 * se:.4f} | {up} / {len(ds) - up - dn} / {dn} |")
L += ["", "## 窓の並び(日本時間の始まりの時刻 k 時。各窓の一致の割合 と r̄、区間は TABLES.md)", "",
      "| k | 全期間 一致 | 前半 一致 | 後半 一致 | 全期間 r̄ | 前半 r̄ | 後半 r̄ |", "|---|---|---|---|---|---|---|"]
for k in range(24):
    s = D["shifts"][str(k)]
    L.append(f"| {k} | " + " | ".join(f"{s[p]['agree']['est']:.3f}" for p in PER) + " | "
             + " | ".join(f"{s[p]['corr_tmean']['est']:+.3f}" for p in PER) + " |")
out = os.path.join(HERE, "main_contrast.md")
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print(out)


def extra():
    """相方 01 の指摘 1・3(2026-10-06): 朝の窓と分を共有しない 5 窓(k = 10〜14)との差と、年ごとの窓の並び。"""
    L2 = ["", "## 朝の窓と分を共有しない窓(k = 10〜14)との差(相方 01 の指摘 1)", "",
          "k = 1〜9 は同じ日の朝の窓と、k = 15〜23 は翌日の朝の窓と分を共有する。共有しないのは k = 10〜14 の 5 窓だけ。", "",
          "| 量 | 期間 | 5 窓の平均との差の点 | 区間(保守: 差の se の平均) | 5 本のうち 0 より上 / 含む / 下 |", "|---|---|---|---|---|"]
    ks = [str(k) for k in range(10, 15)]
    for q, name in (("agree", "一致の割合"), ("corr_tmean", "r̄")):
        for per in PER:
            ds = [D["diff_morning_minus_k"][k][per][q] for k in ks]
            pt = sum(x["est"] for x in ds) / len(ds)
            se = sum(x["se"] for x in ds) / len(ds)
            up = sum(1 for x in ds if x["lo"] > 0)
            dn = sum(1 for x in ds if x["hi"] < 0)
            L2.append(f"| {name} | {per} | {pt:+.4f} | [{pt - 1.96 * se:+.4f}, {pt + 1.96 * se:+.4f}] | {up} / {len(ds) - up - dn} / {dn} |")
    years = sorted(D["shifts"]["0"]["years"].keys())
    L2 += ["", "## 年ごとの一致の割合(24 窓の点。相方 01 の指摘 3)", "",
           "| 年 | 24 窓の平均 | 最小 | 最大 | 0.5 より上の窓の数 | 朝の窓 |", "|---|---|---|---|---|---|"]
    for y in years:
        vs = [D["shifts"][str(k)]["years"][y]["agree"]["est"] if isinstance(D["shifts"][str(k)]["years"][y].get("agree"), dict)
              else D["shifts"][str(k)]["years"][y]["agree"] for k in range(24)]
        L2.append(f"| {y} | {sum(vs) / 24:.3f} | {min(vs):.3f} | {max(vs):.3f} | {sum(1 for v in vs if v > 0.5)} | {vs[0]:.3f} |")
    with open(os.path.join(HERE, "main_contrast.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(L2) + "\n")


extra()
