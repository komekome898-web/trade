"""Round r8-1 (positive definition D): every occurrence, in the files the scene keeper writes, of the terms that
ROOTCAUSE_r8-1.md gave a meaning of the scene keeper's own (its term table, the rows whose class is
「比べる範囲の中の既存の語」 or 「新しい語」), each with a judgment in `term_judgments.tsv`.

The terms are read from the term table by machine (never listed here by hand). The files are line_marks.files()
(every file the scene keeper writes but the runner's output) except ROOTCAUSE_r8-1.md itself, whose own uses are
checked by the scene keeper's self-check named in that file, and `term_judgments.tsv` (its term column names the
terms, it does not use them). A line holding a longer term is matched by the
longer term first (「設定つき対象の持つ型」 before 「設定つき対象」). Each (term, line) needs one judgment:
  表の意味   -- the term is used in the meaning of the term table (read by the scene keeper);
  写し       -- the line is a segment of a positive definition's paragraph (`def_axes/`) or text generated from
                those segments (DEFINITIONS.md's section of definition A's options): the defining text itself;
  別の意味: … -- another meaning (the test fails: a term of the table has one meaning; qualify it instead).
What the machine does not decide: whether a judgment is right (the critic and the auditor read the lines)."""
from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SOURCE = HERE / "ROOTCAUSE_r8-1.md"
JUDGMENTS = HERE / "term_judgments.tsv"
OWN_CLASSES = ("比べる範囲の中の既存の語", "新しい語")
MEANINGS = ("表の意味", "写し")


def terms() -> list[str]:
    """The terms of the term table whose class is one of OWN_CLASSES, longest first."""
    lines = SOURCE.read_text(encoding="utf-8").split("\n")
    start = lines.index("## 用語の表(正の定義 D をこのファイルに当てたもの)")
    out = []
    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            break
        if not ln.startswith("| ") or ln.startswith("| 語 ") or ln.startswith("|---"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if cells[2].startswith(OWN_CLASSES):
            out.append(cells[0])
    return sorted(out, key=len, reverse=True)


def key(term: str, path: str, text: str) -> str:
    return hashlib.sha256(f"{term}\n{path}\n{text}".encode("utf-8")).hexdigest()[:16]


def occurrences() -> list[tuple[str, str, int, str]]:
    """(term, file, line number, line text) for every line holding a term (one row per term per line)."""
    import line_marks
    ts = terms()
    out = []
    for f, i, text, _ in line_marks.all_lines():
        if f in (SOURCE.name, JUDGMENTS.name):  # the judgments' own term column is not a use of the term
            continue
        rest = text
        for t in ts:
            if t in rest:
                out.append((t, f, i, text))
                rest = rest.replace(t, "\0")
    return out


def judgments() -> dict[str, str]:
    out = {}
    if JUDGMENTS.exists():
        with JUDGMENTS.open(encoding="utf-8") as fh:
            for r in csv.reader(fh, delimiter="\t"):
                if r and not r[0].startswith("#"):
                    out[r[0]] = r[3]
    return out


def problems(j: dict | None = None) -> list:
    """What the test fails on: an occurrence without a judgment, a judgment that is not one of MEANINGS (another
    meaning of a term the table gives one meaning), a judgment left for a line that no longer holds the term."""
    occ = occurrences()
    j = judgments() if j is None else j
    keys = {key(t, f, text) for t, f, _, text in occ}
    out = [("判断なし", t, f"{f}:{i}") for t, f, i, text in occ if key(t, f, text) not in j]
    out += [("表の意味でない判断", k, v) for k, v in j.items() if v not in MEANINGS]
    out += [("出現の無い判断", k) for k in sorted(set(j) - keys)]
    return out


if __name__ == "__main__":
    occ = occurrences()
    j = judgments()
    missing = [o for o in occ if key(o[0], o[1], o[3]) not in j]
    print(f"terms {len(terms())}, occurrences {len(occ)}, judged {len(occ) - len(missing)}, missing {len(missing)}")
    for t, f, i, _ in missing[:40]:
        print(f"  missing: {t} {f}:{i}")
