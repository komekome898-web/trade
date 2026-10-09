# リードが書いた。委任・批評家を通していない(数えるだけ)。L-916 の調べ(種類の書いていない「bp」)。
# 15 族の文書・台帳 K-301 以降・段 1 の表の「bp」の字(move_bp・pnl_bp の語の中のものを除く。引用の行を除く)を全部出し、
# 同じ文(「。」で区切る)の書き方で仕分ける:
#   口座(書いてある)= 文に「1 bp = 20」「口座」/ 口座(× 20 で円と書いてある)= 文に「× 20」/ 値動き(書いてある)= 文に「値動き」
#   種類の書き無し = どれも無い(1 つずつ読んで、どちらの bp かを .out の下に書く)
# 使い方(リポジトリの根から): python3 docs/RESEARCH/matilda_main/bare_bp.py > docs/RESEARCH/matilda_main/bare_bp.out
import re
from collections import Counter

A = "docs/ANAL" + "YSIS/"
FAMS = ["base", "levels", "foot", "count", "alert", "entry_exit", "step", "break_dist", "break_len_mult", "beard", "break_delay",
        "break_off", "range_lo", "range_hi", "vola_gate"]
files = [A + f"2026-10-09_matilda_main_{f}.md" for f in FAMS] + ["docs/RESEARCH/FINDINGS_LEDGER.md",
                                                                   "docs/DISCUSSIONS/2026-10-08_matilda_main/STAGE1_FAMILY_TABLES.md"]
bare = re.compile(r"(?<![A-Za-z_])bp(?![A-Za-z_])")
c = Counter()
rows = []
for p in files:
    L = open(p, encoding="utf-8").read().split("\n")
    st = next(i for i, l in enumerate(L) if l.startswith("### K-301")) if p.endswith("LEDGER.md") else 0
    for i in range(st, len(L)):
        l = L[i]
        if l.startswith(">"):
            continue
        s = l.replace("move_bp", "＿＿＿＿＿＿＿").replace("pnl_bp", "＿＿＿＿＿＿")
        for m in bare.finditer(s):
            sent = s[:m.start()].split("。")[-1] + s[m.start():].split("。")[0]
            if l.startswith("|"):
                sent = s
            if re.search(r"1 bp = 20|口座", sent):
                k = "口座(書いてある)"
            elif re.search(r"× 20", sent):
                k = "口座(× 20 で円と書いてある)"
            elif "値動き" in sent:
                k = "値動き(書いてある)"
            else:
                k = "種類の書き無し"
            c[k] += 1
            rows.append((p.split("/")[-1], i + 1, k, s[max(0, m.start() - 40):m.end() + 20].strip()))
print("| 仕分け | 数 |\n|---|---|")
for k, n in sorted(c.items()):
    print(f"| {k} | {n} |")
print(f"| 計 | {sum(c.values())} |\n")
print("| 文書 | 行 | 仕分け | 前後 |\n|---|---|---|---|")
for r in rows:
    print("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |")
