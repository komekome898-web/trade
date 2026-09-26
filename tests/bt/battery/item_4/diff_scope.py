"""The scene-keeper's own diff record, made by machine before returning (ROOTCAUSE_r2-2.md §3-1, family F1-F3).

The script's machine check (L-448, `checkBattery` in scripts/workflows/backtest_env.js) reads the scene-keeper's
returned `changed_files` = the output of `git diff --name-only HEAD`. This tool:
  * takes that output as git prints it (the lines to return, unchanged) and `git status --porcelain
    --untracked-files=all` (the untracked files, which `git diff` does not show and the check therefore never sees);
  * runs the script's own `checkBattery` with node, cut out of the script text the same way
    tests/workflows/backtest_env_logic.test.mjs does, so the scene-keeper never copies the check by hand;
  * lists the scene-keeper's records under docs/DISCUSSIONS/2026-09-23_backtest_env/item_<N>/battery/materials/ that
    HEAD holds and the work tree changed (records are append-only: a rerun goes to a new file);
  * prints the section to paste at the end of a ROOTCAUSE, with the sha256 of its body, so a hand edit is caught
    (test_battery_item4_diffscope.py::test_rootcause_diff_sections_are_machine_made).

Who wrote a line outside the battery is not derived here: git keeps no author for an uncommitted change and the work
tree is shared (the lead's hooks, a parallel worker, earlier scene-keepers). That is prose outside the section.

Round r2-3 (ROOTCAUSE_r2-3.md §3-1, family F4): a baseline of the work tree taken as the scene-keeper's first write
(`--baseline-out`), and, per line of `git diff --name-only HEAD`, whether it already differed from HEAD at the start
and whether its content changed during the run (`attribute`). That is derived; who wrote it is not.

    python3 tests/bt/battery/item_4/diff_scope.py --baseline-out <materials>/baseline_at_start.json   # first, before any write
    python3 tests/bt/battery/item_4/diff_scope.py --markdown --baseline <that file>                   # the section
    python3 tests/bt/battery/item_4/diff_scope.py --json [--baseline <that file>]                     # the raw report
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SCRIPT = REPO / "scripts" / "workflows" / "backtest_env.js"
_MAT = re.compile(r"docs/DISCUSSIONS/2026-09-23_backtest_env/item_[0-9]+/battery/materials/")
BEGIN = re.compile(r"^<!-- diff_scope:begin sha256=([0-9a-f]{64}) -->$")
END = "<!-- diff_scope:end -->"
BASE_LINE = re.compile(r"^基準: (\S+) sha256=([0-9a-f]{64})")

# The four classes of ROOTCAUSE_r2-3.md §3-1 (plus a line that `git status` does not list at all).
PRE_SAME = "着手時にすでに HEAD と違い、作業中に中身は変わっていない"
PRE_CHANGED = "着手時にすでに HEAD と違い、作業中に中身が変わった"
FRESH = "着手時は HEAD と同じで、作業中に変わった"
UNKNOWN = "判定できない(HEAD が作業中に変わった)"
NOT_IN_STATUS = "判定できない(今の git status に無い行)"


def MATERIALS_OF(item):
    return f"docs/DISCUSSIONS/2026-09-23_backtest_env/item_{item}/battery/materials/"


def git_lines(args, repo=REPO):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return [ln for ln in r.stdout.split("\n") if ln != ""]


def script_text():
    return SCRIPT.read_text(encoding="utf-8")


# The cut is the same algorithm as tests/workflows/backtest_env_logic.test.mjs (brace depth from the first "{").
_NODE = r"""
const fs = require('fs')
const inp = JSON.parse(fs.readFileSync(0, 'utf8'))
const src = inp.src
function cut(name) {
  const i = src.indexOf(`function ${name}(`)
  if (i < 0) throw new Error(`no function ${name} in the script`)
  const start = src.lastIndexOf('\n', i) + 1
  let depth = 0, j = src.indexOf('{', i)
  for (; j < src.length; j++) { if (src[j] === '{') depth++; else if (src[j] === '}') { depth--; if (depth === 0) break } }
  return src.slice(start, j + 1)
}
const checkBattery = new Function(`${cut('checkBattery')}; return checkBattery`)()
const out = inp.cases.map(c => checkBattery({ changed_files: c.changed_files, tests_passed: true, test_tail: '' },
  inp.n, [], c.item === null ? undefined : { id: c.item }).findings)
process.stdout.write(JSON.stringify(out))
"""


def run_check_many(cases, src_text=None, n="self"):
    """cases: [{"changed_files": [...], "item": int}] -> the script's checkBattery findings for each case
    (tests_passed is given as true, so only the diff part of the check speaks)."""
    payload = json.dumps({"src": src_text if src_text is not None else script_text(), "n": n, "cases": cases})
    r = subprocess.run(["node", "-e", _NODE], input=payload, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def outside_by_check(paths, item, src_text=None):
    """The lines the script's check stops on, asked one line at a time (no parsing of the finding's text)."""
    got = run_check_many([{"changed_files": [p], "item": item} for p in paths], src_text=src_text)
    return [p for p, f in zip(paths, got) if any(str(x.get("id", "")).endswith("-touch") for x in f)]


def parse_status_z(raw):
    """[(XY, path)] from `git status --porcelain -z`; a rename/copy record "R  new\0old" keeps the new path only."""
    recs = raw.split("\0")
    out, i = [], 0
    while i < len(recs):
        rec = recs[i]
        i += 1
        if not rec:
            continue
        code, path = rec[:2], rec[3:]
        out.append((code, path))
        if code[0] in "RC" or code[1] in "RC":
            i += 1  # the next record is the old path
    return out


def snapshot(repo=REPO):
    """The work tree's state: HEAD and, for every line of `git status --porcelain -z --untracked-files=all`, the
    status and the sha256 of the file's content (None when the file is not there)."""
    head = git_lines(["rev-parse", "HEAD"], repo)[0]
    raw = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "-z", "--untracked-files=all"],
                         capture_output=True, text=True, check=True).stdout
    entries = {}
    for code, path in parse_status_z(raw):
        f = Path(repo) / path
        entries[path] = {"status": code, "sha256": hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None}
    taken = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"taken_at_utc": taken, "head": head, "entries": entries}


def attribute(baseline, diff_lines, now):
    """[(line, class)] for each line of `git diff --name-only HEAD`, from the baseline and the snapshot now."""
    same_head = baseline["head"] == now["head"]
    out = []
    for p in diff_lines:
        n = now["entries"].get(p)
        b = baseline["entries"].get(p)
        if n is None:
            lab = NOT_IN_STATUS
        elif b is not None:
            lab = PRE_SAME if b["sha256"] == n["sha256"] else PRE_CHANGED
        elif same_head:
            lab = FRESH
        else:
            lab = UNKNOWN
        out.append((p, lab))
    return out


def load_baseline(path, sha256=None):
    """Read a baseline file; when sha256 is given the file must hash to it (the section names it)."""
    data = Path(path).read_bytes()
    if sha256 is not None and hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError(f"the baseline {path} does not hash to {sha256} (changed after the section was made)")
    return json.loads(data.decode("utf-8"))


def baseline_refs(text):
    """[(repo-relative baseline path, sha256)] named by the machine-made sections of a ROOTCAUSE text."""
    out, inside = [], False
    for ln in text.split("\n"):
        if BEGIN.match(ln):
            inside = True
        elif ln == END:
            inside = False
        elif inside:
            m = BASE_LINE.match(ln)
            if m:
                out.append((m.group(1), m.group(2)))
    return out


def is_materials(path):
    return bool(_MAT.match(path))


def materials_overwrites(diff_lines):
    """Lines of `git diff --name-only HEAD` that are scene-keeper records: HEAD holds them and the tree changed them."""
    return [p for p in diff_lines if is_materials(p)]


def quoted_lines(lines):
    return [p for p in lines if p.startswith('"')]


def _in_battery(path, item):
    allowed = [f"tests/bt/battery/item_{item}/"] + (["tests/bt/battery/item_0/"] if item == 4 else [])
    return any(path.startswith(a) for a in allowed)


def scope_report(item=4, repo=REPO, baseline_path=None):
    head = git_lines(["rev-parse", "HEAD"], repo)[0]
    diff = git_lines(["diff", "--name-only", "HEAD"], repo)
    status = git_lines(["status", "--porcelain", "--untracked-files=all"], repo)
    findings = run_check_many([{"changed_files": diff, "item": item}])[0]
    untracked = [ln[3:] for ln in status if ln.startswith("?? ")]
    extra = {}
    if baseline_path is not None:
        bp = Path(baseline_path).resolve()
        data = bp.read_bytes()
        base = json.loads(data.decode("utf-8"))
        extra = {"baseline": {"path": str(bp.relative_to(Path(repo).resolve())), "sha256": hashlib.sha256(data).hexdigest(),
                              "snap": base},
                 "attribution": attribute(base, diff, snapshot(repo))}
    return {**extra,
        "head": head, "diff": diff, "status": status, "findings": findings,
        "outside": outside_by_check(diff, item) if diff else [],
        "overwrites": materials_overwrites(diff),
        "untracked_outside": [p for p in untracked if not _in_battery(p, item)],
        "quoted": quoted_lines(diff + untracked),
    }


def _body(rep, item):
    def block(lines):
        return lines if lines else ["(無し)"]
    out = [f"HEAD: {rep['head']}", "", "$ git diff --name-only HEAD"] + block(rep["diff"])
    out += ["", "$ git status --porcelain --untracked-files=all"] + block(rep["status"])
    out += ["", f"台本の checkBattery(項目 {item}、node で台本の文から切り出して走らせた。tests_passed は真として渡す)の指摘:"]
    out += [json.dumps(f, ensure_ascii=False) for f in rep["findings"]] or ["(無し)"]
    out += ["", "検査が止める行(場面集の外):"] + block(rep["outside"])
    out += ["", "記録の上書き(HEAD にある materials の記録が変わっている = 追記だけの規則の破れ):"] + block(rep["overwrites"])
    out += ["", "未追跡で場面集の外(git diff に出ないので検査に見えない):"] + block(rep["untracked_outside"])
    out += ["", "引用符つきの path(git の引用の形。場面集の中でも検査は外と読む):"] + block(rep["quoted"])
    if rep.get("baseline") is not None:
        b = rep["baseline"]
        out += ["", f"基準: {b['path']} sha256={b['sha256']}",
                f"(取った時刻 {b['snap']['taken_at_utc']}、そのときの HEAD {b['snap']['head']}。場面係の最初の書き込みとして取った写し)",
                "", "差分の行ごとの帰属(基準と今の写しの sha256・HEAD から機械で分けた。書き手は git に記録が無いので出さない):"]
        out += [f"{lab}\t{p}" for p, lab in rep["attribution"]] or ["(無し)"]
        stop = set(rep["outside"])
        out += ["", "検査が止める行の帰属:"] + block([f"{lab}\t{p}" for p, lab in rep["attribution"] if p in stop])
    return "\n".join(out)


def section_markdown(rep, item=4):
    body = _body(rep, item)
    h = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return "\n".join([
        f"## `git diff --name-only HEAD` の節(`diff_scope.py` が作った。手で変えない)", "",
        f"<!-- diff_scope:begin sha256={h} -->", "```text", body, "```", END, ""])


def find_sections(text):
    """[(sha256 in the marker, whether the body between the fences hashes to it)] for each section in text."""
    lines = text.split("\n")
    out = []
    for i, ln in enumerate(lines):
        m = BEGIN.match(ln)
        if not m:
            continue
        try:
            j = lines.index(END, i + 1)
        except ValueError:
            out.append((m.group(1), False))
            continue
        inner = lines[i + 1:j]
        ok = len(inner) >= 2 and inner[0] == "```text" and inner[-1] == "```"
        body = "\n".join(inner[1:-1]) if ok else ""
        out.append((m.group(1), ok and hashlib.sha256(body.encode("utf-8")).hexdigest() == m.group(1)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", type=int, default=4)
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--baseline", help="the baseline file taken at the start (adds the attribution)")
    ap.add_argument("--baseline-out", help="write the baseline (the scene-keeper's first write) and stop")
    a = ap.parse_args(argv)
    if a.baseline_out:
        out = Path(a.baseline_out)
        if out.exists():
            raise SystemExit(f"{out} exists: records are append-only (take the baseline under a new name)")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(snapshot(), ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(out)
        return 0
    rep = scope_report(a.item, baseline_path=a.baseline)
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(section_markdown(rep, a.item))
    return 0


if __name__ == "__main__":
    sys.exit(main())
