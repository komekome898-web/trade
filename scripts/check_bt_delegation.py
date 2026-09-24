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

Usage: python3 scripts/check_bt_delegation.py [delegation.md] [OWNER_LOG.md] [VERDICTS.md] [workflow.js]
Exit 1 on any error.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

DEFAULTS = ("docs/DATA/delegations/20260923_backtest_env_prompt.md", "docs/OWNER_LOG.md",
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
ROLE_SCRUTINY = (("要件:", "SCRUTINY_BUILD"), ("場面:", "SCRUTINY_BUILD"), ("場面の直し:", "SCRUTINY_FIX"), ("定義:", "SCRUTINY_BUILD"),
                 ("作る:", "SCRUTINY_FIX"), ("表:", "SCRUTINY_TABLE"), ("批評:", "SCRUTINY_CRITIC"),
                 ("盲検:", "SCRUTINY_JUDGE"), ("欠けているもの", "SCRUTINY_GAPS"))
# roles that must receive the lead's notes and the prior battery record (audit 49 #3 / audit 50 #2)
ROLE_NOTES = ("監査役(場面):", "監査役(定義):", "定義:", "場面の直し:", "作る:")


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


def main(argv: list[str]) -> int:
    paths = [Path(argv[i]) if i < len(argv) else Path(DEFAULTS[i]) for i in range(4)]
    errs = check(*(p.read_text(encoding="utf-8") for p in paths[:3]))
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
