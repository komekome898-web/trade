"""# 11 の読み口: 年で層に分けた low − high の点(区間なし)を、TABLES.md の年ごとの表と COUNTS.md の区分ごとの日数から。

区分の境は前の暦年の 3 分位なので、区分の日は年に偏る(COUNTS.md)。全期間の low − high は「区分」と「年」が混ざる。
年ごとの low − high を、重み w_y = n_low・n_high ÷ (n_low + n_high)(n = その年の区分の日数。COUNTS.md)で平均する。
low と high の両方が 10 日以上ある年だけ。前半 = 2017〜2019 年・後半 = 2020〜2023 年(暦年で切る。事前登録の境 2019-12-07/08 とは 2019 年 12 月の 24 日分ずれる)。日ごとの値が無いので区間は出せない(点だけ。カード 7 の形は c7_records.py §4 に区間つき)。
重みは暦の日の数で、形ごとの分母(朝の窓は平日だけ、など)とは違う(近似)。
"""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
T = open(os.path.join(HERE, "..", "TABLES.md")).read().split("\n")
Cn = open(os.path.join(HERE, "..", "COUNTS.md")).read().split("\n")
days = {}
for l in Cn:
    m = re.match(r"\| (20\d\d) \| \d+ \| \d+ \| (\d+) \| (\d+) \| (\d+) \|", l)
    if m:
        days[int(m.group(1))] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
rows = {}
for l in T:
    m = re.match(r"\| (.+?) \| (20\d\d) \| ([+\-][\d.]+) \| ([+\-][\d.]+) \| ([+\-][\d.]+) \|", l)
    if m:
        rows.setdefault(m.group(1), {})[int(m.group(2))] = (float(m.group(3)), float(m.group(5)))
out = ["# # 11 年で層に分けた low − high の点(`strat_points.py`。区間なし)", "",
       "| 形 | 期間 | 使った年 | 年ごとの low − high | 層に分けた low − high(点) |", "|---|---|---|---|---|"]
for form, ys in rows.items():
    for pn, rng in (("全期間", range(2017, 2024)), ("前半", range(2017, 2020)), ("後半", range(2020, 2024))):
        use = [y for y in rng if y in ys and days[y][0] >= 10 and days[y][2] >= 10]
        num = den = 0.0; per = []
        for y in use:
            nl, nh = days[y][0], days[y][2]; w = nl * nh / (nl + nh); d = ys[y][0] - ys[y][1]
            num += w * d; den += w; per.append(f"{y} {d:+.3f}")
        out.append(f"| {form} | {pn} | {','.join(map(str, use))} | {' / '.join(per)} | {num / den:+.3f} |")
open(os.path.join(HERE, "strat_points.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
