"""リードが書いた(数えるだけ)。both_halves.out の 31 本を、前半・後半それぞれの区間で 正(下限 > 0)/ 負(上限 < 0)/ 含む に分けて数える。段 2 の材料(docs/DISCUSSIONS/2026-10-08_matilda_main/STAGE2_MATERIALS.md)。
    python3 docs/RESEARCH/matilda_main/both_halves_states.py > docs/RESEARCH/matilda_main/both_halves_states.out
"""
import re
from collections import Counter
rows = [l.strip() for l in open("docs/RESEARCH/matilda_main/both_halves.out") if l.strip()]
st = lambda lo, hi: "正" if lo > 0 else ("負" if hi < 0 else "含む")
c = Counter()
for l in rows:
    v = [float(x) for x in re.findall(r"[-+]\d+", l.split("|", 1)[1])]
    a, b = st(v[1], v[2]), st(v[4], v[5]); c[(a, b)] += 1
    print(l.split(" |")[0], "|", a, "→", b)
print("本数", len(rows))
for k, n in c.most_common():
    print(f"{k[0]} → {k[1]}: {n}")
