"""Round r8-1 (positive definition B): every line of every file the scene keeper writes, with a mark on the
lines that may state the content of scenes. Used by test_battery_item0.py.

The files: `git ls-files tests/bt/battery/item_0` and the untracked files the scene keeper wrote there, except
the runner's output (`survey_results/`, a source of truth itself). A line is MARKED when it names a scene id (or a scene family such as `p3-<型>`), a field of `Scene` in
backquotes, or counts scenes ("N 場面", "場面 N 件"). Every marked line must have a judgment in
`line_judgments.tsv` (keyed by the file and the line's text); an unmarked line is judged "印なし" here.
What the marks do not catch -- a line that states a scene's content without naming it -- is read by the critic
and the auditor (the machine guarantees only that every line is listed and every marked line is judged)."""
from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

EXCLUDED_DIRS = ("survey_results/",)  # the runner's output: a source of truth itself (positive definition B)
EXCLUDED_FILES: tuple = ()  # no file is left out by its type or name
JUDGMENTS = HERE / "line_judgments.tsv"
CATEGORIES = {
    "照合元": "scenes.py の値そのもの(場面の定義)",
    "生成物": "照合元から機械で作り、食い違えば試験が落ちる(DEFINITIONS.md は test_definitions_in_sync_with_scenes)",
    "コード": "場面 id を識別子・鍵・呼び出しの引数として使うコード(場面集のコードの振る舞い。場面の中身を述べる文ではない)",
    "参照だけ": "場面 id と欄を名指すだけで、照合元の値に依る言明を持たない",
    "試験が照らす": "試験がその文の名指す場面 id の今の照合元から作り直して一致を確かめる定型の文",
    "規則・読み": "機構の読み・一次資料の行・判断とその理由・場面集のコードの振る舞い(場面の中身ではない)",
}


def files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "--others", "--cached", "--exclude-standard", "."], cwd=HERE,
                         capture_output=True, text=True).stdout.split()
    return sorted(f for f in set(out) if not f.startswith(EXCLUDED_DIRS) and f not in EXCLUDED_FILES
                  and not f.endswith((".pyc",)) and "__pycache__" not in f)


def _mark_re():
    import scenes
    ids = sorted({s.id for s in scenes.SCENES}, key=len, reverse=True)
    fields = ["input", "expected", "derivation", "measures", "graded_from", "type_plan", "covers"]
    return re.compile("|".join(map(re.escape, ids)) + r"|\bp[1-7]-(?:\*|<)|`(?:" + "|".join(fields) + r")`"
                      r"|\d+ 場面|場面 \d+ 件")


def key(path: str, text: str) -> str:
    return hashlib.sha256(f"{path}\n{text}".encode("utf-8")).hexdigest()[:16]


def all_lines() -> list[tuple[str, int, str, bool]]:
    """(file, line number, text, marked) for every line of every file."""
    mk = _mark_re()
    out = []
    for f in files():
        try:
            text = (HERE / f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for i, line in enumerate(text.split("\n"), 1):
            out.append((f, i, line, bool(mk.search(line))))
    return out


def judgments() -> dict[str, tuple[str, str]]:
    out = {}
    if JUDGMENTS.exists():
        with JUDGMENTS.open(encoding="utf-8") as fh:
            for r in csv.reader(fh, delimiter="\t"):
                if r and not r[0].startswith("#"):
                    out[r[0]] = (r[2], r[3] if len(r) > 3 else "")
    return out


if __name__ == "__main__":
    lines = all_lines()
    j = judgments()
    marked = [x for x in lines if x[3]]
    missing = [x for x in marked if key(x[0], x[2]) not in j]
    print(f"files {len(files())}, lines {len(lines)}, marked {len(marked)}, judged {len(marked) - len(missing)}, "
          f"unmarked (印なし) {len(lines) - len(marked)}; judgments + 印なし = {len(marked) - len(missing) + len(lines) - len(marked)}")
    for f, i, t, _ in missing:
        print(f"MISSING\t{key(f, t)}\t{f}:{i}\t{t.strip()[:200]}")
