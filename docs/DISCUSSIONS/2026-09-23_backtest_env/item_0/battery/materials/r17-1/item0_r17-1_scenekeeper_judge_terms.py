"""Round r17-1: judgments for the term occurrences without one, and removal of the judgments whose line this round
changed (出現の無い判断). 写し = the frozen paragraph of definition C (DEFINITIONS.md's 「正の定義 C:」 line and
gen_definitions.py's FROZEN_DEFINITIONS['C'] line) and the segments of a definition's paragraph (def_axes/); every
other occurrence was read in this round's listing and uses the term table's meaning (表の意味)."""
import sys
sys.path.insert(0, "/home/user/trade/tests/bt/battery/item_0")
import term_marks as T


def meaning(f, text):
    if f.startswith("def_axes/") or (f == "DEFINITIONS.md" and text.startswith("正の定義 C: ")) \
            or (f == "gen_definitions.py" and text.lstrip().startswith("'C': ")):
        return "写し"
    return "表の意味"


occ = T.occurrences()
j = T.judgments()
add = [f"{T.key(t, f, text)}\t{t}\t{f}:{i}\t{meaning(f, text)}" for t, f, i, text in occ if T.key(t, f, text) not in j]
stale = {p[1] for p in T.problems() if p[0] == "出現の無い判断"}
rows = T.JUDGMENTS.read_text(encoding="utf-8").rstrip("\n").split("\n")
removed = [r for r in rows if not r.startswith("#") and r.split("\t")[0] in stale]
keep = [r for r in rows if r.startswith("#") or r.split("\t")[0] not in stale]
print("add", len(add), "(写し", sum(1 for a in add if a.endswith("写し")), ") remove", len(removed))
if "--write" in sys.argv:
    T.JUDGMENTS.write_text("\n".join(keep + add) + "\n", encoding="utf-8")
    print("written")
