"""Round r17-1: compare, per configured target, the survey_results at HEAD with this round's runs on every scene:
correctness, reproducibility and status of run 1 (printed per difference), and the graded output of run 1 (counted per
scene family, printed for scenes outside the P0-2 unit scenes, whose graded output gained the key refused_by_entry)."""
import csv, sys
from collections import Counter
from pathlib import Path
csv.field_size_limit(1 << 30)
sys.path.insert(0, "/home/user/trade/tests/bt/battery/item_0")
import scenes
OLD = Path("/home/user/trade/tests/bt/battery/item_0/survey_results")
NEW = Path(sys.argv[1])
def rows(p):
    with p.open(encoding="utf-8") as f:
        return {r["scene_id"]: r for r in csv.DictReader(f, delimiter="\t")}
same = diff = 0
out_only = Counter()
for p in sorted(NEW.glob("*.tsv")):
    old = OLD / p.name
    if not old.exists():
        print("NO_OLD", p.name); continue
    a, b = rows(old), rows(p)
    if set(a) != set(b):
        print("SCENES_DIFFER", p.name, sorted(set(a) ^ set(b)))
    for sid in sorted(set(a) & set(b)):
        ka = (a[sid]["correctness"], a[sid]["reproducibility"], a[sid]["status_1"])
        kb = (b[sid]["correctness"], b[sid]["reproducibility"], b[sid]["status_1"])
        if ka != kb:
            diff += 1
            print("DIFF", p.name, sid, ka, "->", kb, "|", b[sid]["output_1"][:160])
        else:
            same += 1
            if a[sid]["output_1"] != b[sid]["output_1"]:
                fam = "unit" if sid in scenes.UNIT_SCENES else sid
                out_only[fam] += 1
                if fam != "unit":
                    print("OUTPUT_ONLY", p.name, sid, a[sid]["output_1"][:100], "->", b[sid]["output_1"][:100])
print("same grade", same, "grade differs", diff, "output-only differences by family", dict(out_only))
