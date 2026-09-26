"""Merge the round r3-1 rows (the scenes added / changed) into survey_results/<target>.tsv in the scene order."""
import sys
from pathlib import Path
REPO = Path("/home/user/trade")
sys.path.insert(0, str(REPO / "tests/bt/battery/item_4"))
import i4_scenes as S
RES = REPO / "tests/bt/battery/item_4/survey_results"
RUNS = Path(sys.argv[1])
order = [s["id"] for s in S.SCENES]
for f in sorted(RUNS.glob("*.tsv")):
    old = RES / f.name
    if not old.exists():
        print("no old", f.name); continue
    ol = old.read_text(encoding="utf-8").splitlines()
    head, rows = ol[0], {ln.split("\t")[0]: ln for ln in ol[1:] if ln}
    nl = f.read_text(encoding="utf-8").splitlines()
    assert nl[0] == head, f.name
    for ln in nl[1:]:
        if ln:
            rows[ln.split("\t")[0]] = ln
    missing = [x for x in order if x not in rows]
    extra = [x for x in rows if x not in order]
    old.write_text("\n".join([head] + [rows[x] for x in order if x in rows]) + "\n", encoding="utf-8")
    print(f.name, "rows", len(rows), "missing", missing, "extra", extra)
