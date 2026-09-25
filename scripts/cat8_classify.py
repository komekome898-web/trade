#!/usr/bin/env python3
"""Classify the hit lines of one cat8_search.py step by written rules, so a large `なし`
can be judged by rules that are checked against every line (round 13-14: rules applied by
hand by file were wrong for some lines, e.g. the colour name `darkgoldenrod` filed under a
golden-file test).

Usage: python3 scripts/cat8_classify.py --log <raw log> --step <line of that step in the log>
                                        --rules <rules.tsv> --candidate 8-NNN

rules.tsv: one rule per line, tab-separated: <rule id> <tab> <regex matched against the hit
line text> <tab> <what the word means in such lines and why it is not the element's
predicate>. Lines starting with # are comments.

Every hit line of the step is tested against the rules in order; the first rule whose regex
matches the line text (not the path) takes it. Prints the rules, the count per rule, and
every line no rule takes, as `unmatched\t<path>:<line>\t<text>`. Those lines must be judged
one by one in the report. Footer:
`cat8_classify: complete step=<log>:<line> hits=H matched=M unmatched=U rules=R candidate=8-NNN`
Stops with exit code 1 if the step is not a complete cat8_search.py step of that candidate,
if a rule's regex is invalid or empty, or if the hit lines counted differ from the step's
`hits=`.
"""
import argparse
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--log", required=True)
ap.add_argument("--step", required=True, type=int)
ap.add_argument("--rules", required=True)
ap.add_argument("--candidate", required=True)
a = ap.parse_args()
if not re.fullmatch(r"8-\d{3}", a.candidate):
    sys.exit("--candidate は 8-NNN の形: " + a.candidate)

lines = open(a.log, encoding="utf-8", errors="replace").read().split("\n")
k = min(a.step, len(lines)) - 1
while k >= 0 and not lines[k].startswith("--- "):
    k -= 1
e = k + 1
while e < len(lines) and not lines[e].startswith("--- "):
    e += 1
block = lines[k:e]
if len(block) < 2 or "cat8_search.py" not in block[1]:
    sys.exit("cat8_classify: the step is not a cat8_search.py step")
foot = [l for l in block if l.startswith("cat8_search: complete ")]
if not foot or ("candidate=%s" % a.candidate) not in foot[-1]:
    sys.exit("cat8_classify: the step has no complete footer for candidate " + a.candidate)
want = int(re.search(r" hits=(\d+)", foot[-1]).group(1))

rules = []
for n, ln in enumerate(open(a.rules, encoding="utf-8"), 1):
    ln = ln.rstrip("\n")
    if not ln.strip() or ln.startswith("#"):
        continue
    parts = ln.split("\t")
    if len(parts) != 3 or not all(p.strip() for p in parts):
        sys.exit("cat8_classify: rules line %d needs <id> TAB <regex> TAB <reason>" % n)
    try:
        rx = re.compile(parts[1])
    except re.error as err:
        sys.exit("cat8_classify: rules line %d has a bad regex: %s" % (n, err))
    rules.append((parts[0].strip(), rx, parts[2].strip()))
if not rules:
    sys.exit("cat8_classify: no rules")

hit_re = re.compile(r"^(/\S.*?):(\d+): (.*)$")
counts = {r[0]: 0 for r in rules}
unmatched, total = [], 0
end = block.index("== ファイルごとの当たった行の数") if "== ファイルごとの当たった行の数" in block else len(block)
for ln in block[2:end]:
    m = hit_re.match(ln)
    if not m:
        continue
    total += 1
    text = m.group(3)
    for rid, rx, _ in rules:
        if rx.search(text):
            counts[rid] += 1
            break
    else:
        unmatched.append((m.group(1), m.group(2), text))
if total != want:
    sys.exit("cat8_classify: counted %d hit lines but the step says hits=%d (output cut?)" % (total, want))

print("== 決まり")
for rid, rx, why in rules:
    print("%s\t%s\t%s\t%d" % (rid, rx.pattern, why, counts[rid]))
for p, no, text in unmatched:
    print("unmatched\t%s:%s\t%s" % (p, no, text[:300]))
print("cat8_classify: complete step=%s:%d hits=%d matched=%d unmatched=%d rules=%d candidate=%s" % (
    a.log.split("/")[-1], a.step, total, total - len(unmatched), len(unmatched), len(rules), a.candidate))
