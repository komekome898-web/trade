"""Mechanical checks on the backtest-env delegation before it goes to the auditor (L-433 提出前の吟味).

Checks, all against primary records:
1. Every owner decision cited as L-NNN in the delegation has a row in docs/OWNER_LOG.md.
2. Every bold quote written as L-NNN「**…**」 in the delegation appears verbatim in that L-NNN row of OWNER_LOG.
3. The L numbers listed in the 「オーナーだけが変える」 sentence all appear in §0's table (right column).
4. The definition heading 「周回の数え方と止める条件」 occurs exactly once as a definition and every other
   mention points at it.
5. No auditor output in the VERDICTS file is abbreviated with 「(…)」 inside a 「監査役の出力」 section (O-4).
6. Every agent(...) call in the workflow script (except owner-auditor calls) carries the scrutiny constant
   that matches its role (by label prefix) — L-433 提出前の吟味 wired into every role with the role's own text.

7. (optional 5th path) The launch args JSON: its `marker` names the delegation file at its current sha256[:12],
   every top-level key is read by the script as `args.<key>` (an unread key = a mechanism the script no longer
   has, as `lead_definitions` was after audit 54), and every L-NNN cited in its lead notes has a row in OWNER_LOG
   (audit 55-4: the args file was where the mismatches lived, and nothing checked it).

8. The scene keeper's write destination for changes to the lead's answer (audit 56-3 / 57-1) is the same pair in the
   delegation, the script's 定義 prompt and the args' lead notes: the phrase 節「リードに聞くこと」 and the field
   `lead_answer_changes` (not the worker's `questions_for_lead`) must appear in all of them.

9. The no-touch wiring (audit 60-3 / 61-7): the script's repairBattery text tells the scene keeper not to touch files
   outside the battery and to paste `git diff --name-only HEAD`, and the auditBattery text tells the auditor to check
   that diff itself.

10. The framework fingerprint (L-443 (1)): sha256[:12] of the script's role labels and function names plus the
    delegation's 「通過の判定」 row. The delegation carries the last audited value on a line `枠組みの指紋: <hex>`;
    a mismatch means the framework changed and the delegation must go to the auditor again (wording and record
    fixes do not change it, so they need no audit). Print the current value with `--fingerprint`.

Usage: python3 scripts/check_bt_delegation.py [delegation.md] [OWNER_LOG.md] [VERDICTS.md] [workflow.js] [args.json]
Exit 1 on any error.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

DEFAULTS = ("docs/DATA/delegations/20260925_backtest_env_prompt.md", "docs/OWNER_LOG.md",  # v2 (L-447/L-448); audit 64-3
            "docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_prompt.md",
            "scripts/workflows/backtest_env.js")

# ESLint flat config for the workflow script: the harness runs the body inside an async function with these
# globals, so the check wraps the body the same way (top-level `return` is legal there) and forbids undefined names.
ESLINT_CONFIG = """export default [{ files: ['**/*.js'], languageOptions: { ecmaVersion: 2022, sourceType: 'script',
  globals: { agent: 'readonly', parallel: 'readonly', pipeline: 'readonly', phase: 'readonly', log: 'readonly',
    args: 'readonly', budget: 'readonly', workflow: 'readonly', JSON: 'readonly', Math: 'readonly', Object: 'readonly',
    Array: 'readonly', Promise: 'readonly', Set: 'readonly', Map: 'readonly', Number: 'readonly', String: 'readonly',
    Boolean: 'readonly', Error: 'readonly', console: 'readonly', Date: 'readonly' } },
  rules: { 'no-undef': 'error', 'no-redeclare': 'error', 'no-dupe-keys': 'error', 'no-unused-vars': ['error', { args: 'none', varsIgnorePattern: '^meta$' }] } }]
"""


def lint_script(script: str) -> list[str]:
    """Run ESLint (no-undef etc.) on the workflow script wrapped as the harness runs it. Returns errors;
    a missing eslint is reported as one error (the launch must not rely on an unchecked script)."""
    import shutil
    import subprocess
    import tempfile
    eslint = shutil.which("eslint")
    if not eslint:
        return ["台本: eslint が見つからないので未定義の名前の検査ができない(未確認のまま起動しない)"]
    body = re.sub(r"^export const meta", "const meta", script, count=1, flags=re.M)
    with tempfile.TemporaryDirectory() as td:
        cfg = os.path.join(td, "eslint.config.mjs")
        js = os.path.join(td, "workflow.js")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(ESLINT_CONFIG)
        with open(js, "w", encoding="utf-8") as f:
            f.write("(async () => {\n" + body + "\n})()\n")
        # cwd = the temp dir: ESLint ignores files outside its base path (silently, exit 0)
        r = subprocess.run([eslint, "--no-config-lookup", "--config", "eslint.config.mjs", "--format", "json",
                            "workflow.js"], capture_output=True, text=True, cwd=td)
    try:
        msgs = [m for f in json.loads(r.stdout) for m in f["messages"]]
    except (ValueError, KeyError):
        return ["台本: eslint の出力が読めない: " + (r.stdout + r.stderr).strip()[:400]]
    # the wrapper adds one line above the script; every message (warnings included) blocks the launch
    return [f"台本:{(m.get('line') or 1) - 1}:{m.get('column', 0)}: {m['message']} ({m.get('ruleId')})" for m in msgs]


# label prefix → the scrutiny constant that role must carry (delegation §3 提出前の吟味)
ROLE_SCRUTINY = (("要件:", "SCRUTINY_BUILD"), ("場面:", "SCRUTINY_BUILD"), ("場面の直し:", "SCRUTINY_FIX"), ("参照実装:", "SCRUTINY_BUILD"),
                 ("作る:", "SCRUTINY_FIX"), ("表:", "SCRUTINY_TABLE"), ("批評:", "SCRUTINY_CRITIC"),
                 ("盲検:", "SCRUTINY_JUDGE"), ("欠けているもの", "SCRUTINY_GAPS"))
# roles that must receive the lead's notes and the prior battery record (audit 49 #3 / audit 50 #2)
ROLE_NOTES = ("場面の直し:", "作る:")  # the 定義 roles are gone (L-443); 監査役(場面) is gone (L-448)
# roles that only write a fixed text to a file (no judgement, so no scrutiny text): audit 59-4 stop notice
ROLE_MECHANICAL = ("並行の直しの戻し:",)


def check_script(script: str) -> list[str]:
    """Each agent(`...`, {opts}) call must carry the scrutiny text unless it calls the owner-auditor."""
    errs = []
    for m in re.finditer(r"agent\(`", script):
        start = m.end()
        end = script.find("`,", start)
        if end < 0:
            errs.append(f"台本:{script[:start].count(chr(10)) + 1}: agent(` の閉じが見つからない")
            continue
        body = script[start:end]
        opts = script[end : script.find("})", end) + 2]  # the options object ends with "})"; labels may contain ")"
        label = re.search(r"label: `([^`]*)`", opts)
        name = label.group(1) if label else "?"
        line = script[:start].count(chr(10)) + 1
        if any(f"label: `{r}" in opts for r in ROLE_MECHANICAL):
            continue
        if "owner-auditor" in opts:
            if any(name.startswith(pre) for pre in ROLE_NOTES) and "lead_notes" not in body:
                errs.append(f"台本:{line}: agent 呼び出し {name} にリードの注記(args.lead_notes)が届いていない")
            continue
        want = next((c for pre, c in ROLE_SCRUTINY if name.startswith(pre)), None)
        if any(name.startswith(pre) for pre in ROLE_NOTES) and "lead_notes" not in body:
            errs.append(f"台本:{line}: agent 呼び出し {name} にリードの注記(args.lead_notes)が届いていない")
        if want is None:
            errs.append(f"台本:{line}: agent 呼び出し {name} の役が ROLE_SCRUTINY に無い")
        elif "${" + want + "}" not in body:
            errs.append(f"台本:{line}: agent 呼び出し {name} に役の吟味の定数 {want} が無い")
        others = [c for _, c in ROLE_SCRUTINY if want and c != want and "${" + c + "}" in body]
        if others:
            errs.append(f"台本:{line}: agent 呼び出し {name} に別の役の吟味の定数 {others} が入っている")
    return errs


def owner_rows(log: str) -> dict[str, str]:
    rows = {}
    for line in log.splitlines():
        m = re.match(r"\|\s*(L-\d{3})\s*\|", line)
        if m:
            rows[m.group(1)] = line
    return rows


def check(doc: str, log: str, verdicts: str) -> list[str]:
    errs: list[str] = []
    rows = owner_rows(log)
    cited = sorted(set(re.findall(r"L-\d{3}", doc)))
    for l in cited:
        if l not in rows:
            errs.append(f"{l}: 委任文が引いているが OWNER_LOG に行が無い")
    for m in re.finditer(r"(L-\d{3})「\*\*([^*]+?)\*\*」", doc):
        l, q = m.group(1), m.group(2)
        row = rows.get(l, "")
        if q not in row:
            errs.append(f"{l}: 太字の引用「{q[:40]}…」が OWNER_LOG の {l} の行に逐語で無い")
    sec0 = doc.split("## 1.", 1)[0]
    m = re.search(r"はオーナーだけが変える。", doc)
    if m:
        sent = doc[doc.rfind("**", 0, m.start()) : m.end()]
        for l in set(re.findall(r"L-\d{3}", sent)):
            if l not in sec0:
                errs.append(f"{l}: 「オーナーだけが変える」の一覧にあるが §0 の表に無い")
    else:
        errs.append("「はオーナーだけが変える。」の文が無い")
    defs = doc.count("**周回の数え方と止める条件(")
    if defs != 1:
        errs.append(f"「周回の数え方と止める条件」の定義が {defs} 回(1 回でなければならない)")
    in_audit = False
    for i, line in enumerate(verdicts.splitlines(), 1):
        if line.startswith("### "):
            in_audit = "監査役の出力" in line
        elif in_audit and re.search(r"(?<!「)\(…\)(?!」)", line):  # 「(…)」 quoted by the auditor itself is not a cut
            errs.append(f"VERDICTS:{i}: 監査役の出力の中に「(…)」= 切り詰めがある(O-4)")
    return errs


def check_args(args_text: str, delegation_text: str, delegation_name: str, script: str, owner_log: str) -> list[str]:
    """Check 7: the launch args against the delegation file, the script and OWNER_LOG."""
    import hashlib
    import json
    errs: list[str] = []
    try:
        args = json.loads(args_text)
    except ValueError as e:
        return [f"引数: JSON として読めない: {e}"]
    want = f"{delegation_name}@{hashlib.sha256(delegation_text.encode('utf-8')).hexdigest()[:12]}"
    if args.get("marker") != want:
        errs.append(f"引数: marker が委任文の今の版と違う: {args.get('marker')!r} != {want!r}")
    for key in args:
        if f"args.{key}" not in script:
            errs.append(f"引数: 台本が読まない鍵 {key!r}(台本に args.{key} が無い = 台本に無い機構)")
    notes = json.dumps(args.get("lead_notes", {}), ensure_ascii=False) + json.dumps(args.get("prior_battery_record", {}), ensure_ascii=False)
    for l in sorted(set(re.findall(r"L-\d{3}", notes))):
        if l not in owner_log:
            errs.append(f"引数: lead_notes が引く {l} が OWNER_LOG に無い")
    return errs


def framework_fingerprint(delegation_text: str, script: str) -> str:
    """Check 10: what counts as the framework — the roles (agent labels), the stages (async functions) and the pass rule."""
    import hashlib
    labels = sorted(set(re.findall(r"label: `([^`$:]+):", script)))
    funcs = sorted(set(re.findall(r"^async function (\w+)\(", script, flags=re.M)))
    rows = [ln for ln in delegation_text.splitlines() if ln.startswith("| 通過の判定")]
    # audit 62-3: the pure decision functions' bodies are part of the framework (a change of a judgement rule
    # without renaming anything must still change the fingerprint)
    bodies = [_cut_function(script, name) for name in DECISION_FUNCS]
    return hashlib.sha256(("\n".join(labels + funcs + rows + bodies)).encode("utf-8")).hexdigest()[:12]


DECISION_FUNCS = ("splitStops", "judgeRound")


def _cut_function(script: str, name: str) -> str:
    """The source of `function name(...) {...}`, braces counted outside string, template and comment text (audit 63-4)."""
    i = script.find(f"function {name}(")
    if i < 0:
        return f"{name}: missing"
    depth, j, quote = 0, script.find("{", i), None
    while j < len(script):
        ch = script[j]
        if quote:
            if ch == "\\":
                j += 1
            elif ch == quote:
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
        elif script.startswith("//", j):
            j = script.find("\n", j)
            if j < 0:
                break
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return script[i:j + 1]


def check_fingerprint(delegation_text: str, script: str) -> list[str]:
    want = framework_fingerprint(delegation_text, script)
    m = re.search(r"^枠組みの指紋: ([0-9a-f]{12})", delegation_text, flags=re.M)
    if not m:
        return [f"枠組み: 委任文に「枠組みの指紋: <12 桁>」の行が無い(今の値 {want})"]
    if m.group(1) != want:
        return [f"枠組み: 指紋が変わった {m.group(1)} → {want} = 役・段・通過の判定が変わったので監査に出し、通ったら行を更新する(L-443)"]
    return []


# L-448: the audit agent is gone; the machine check (checkBattery) must read the pasted diff against tests/bt/battery/
NO_TOUCH = (("repairBattery", ("git diff --name-only HEAD", "触れない", "changed_files")), ("checkBattery", ("tests/bt/battery/", "changed_files")))


def check_no_touch(script: str) -> list[str]:
    """Check 9: the repair and audit prompts carry the no-touch wiring."""
    errs: list[str] = []
    for fn, phrases in NO_TOUCH:
        i = script.find(f"async function {fn}(")
        if i < 0:
            i = script.find(f"\nfunction {fn}(")
        if i < 0:
            errs.append(f"台本: {fn} が無い")
            continue
        j = script.find("\nasync function", i + 1)
        j2 = script.find("\nfunction ", i + 1)
        if j2 > 0 and (j < 0 or j2 < j):
            j = j2
        body = script[i:j if j > 0 else len(script)]
        for ph in phrases:
            if ph not in body:
                errs.append(f"台本: {fn} の文に {ph!r} が無い(場面集の直しが実装に触れない配線 = 監査 60-3)")
    return errs


DEST_PHRASES = ("節「リードに聞くこと」", "lead_answer_changes")


def check_destination(delegation_text: str, script: str, args_text: str | None) -> list[str]:
    """Check 8: the scene keeper's write destination is stated with the same two tokens everywhere."""
    errs: list[str] = []
    places = {"委任文": delegation_text, "台本": script}
    if args_text is not None:
        places["引数の lead_notes"] = args_text
    for name, text in places.items():
        for ph in DEST_PHRASES:
            if ph not in text:
                errs.append(f"書き先: {name} に {ph!r} が無い(場面係がリードの答えを変えた点と理由の書き先が揃っていない)")
    return errs


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--fingerprint":
        d, w = Path(DEFAULTS[0]), Path(DEFAULTS[3])
        print(framework_fingerprint(d.read_text(encoding="utf-8"), w.read_text(encoding="utf-8")))
        return 0
    paths = [Path(argv[i]) if i < len(argv) else Path(DEFAULTS[i]) for i in range(4)]
    errs = check(*(p.read_text(encoding="utf-8") for p in paths[:3]))
    errs += check_fingerprint(paths[0].read_text(encoding="utf-8"), paths[3].read_text(encoding="utf-8") if paths[3].exists() else "")
    errs += check_no_touch(paths[3].read_text(encoding="utf-8") if paths[3].exists() else "")
    errs += check_destination(paths[0].read_text(encoding="utf-8"), paths[3].read_text(encoding="utf-8") if paths[3].exists() else "",
                              Path(argv[4]).read_text(encoding="utf-8") if len(argv) >= 5 else None)
    if len(argv) >= 5:
        errs += check_args(Path(argv[4]).read_text(encoding="utf-8"), paths[0].read_text(encoding="utf-8"), paths[0].name,
                           paths[3].read_text(encoding="utf-8") if paths[3].exists() else "", paths[1].read_text(encoding="utf-8"))
    if paths[3].exists():
        script = paths[3].read_text(encoding="utf-8")
        errs += check_script(script) + lint_script(script)
    else:
        errs.append(f"{paths[3]}: 台本が無い")
    for e in errs:
        print("NG", e)
    print(f"{'OK' if not errs else 'NG'} 誤り {len(errs)} 件")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
