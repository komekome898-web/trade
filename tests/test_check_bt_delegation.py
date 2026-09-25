"""scripts/check_bt_delegation.py: mechanical pre-audit checks on the backtest-env delegation."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("cbd", Path(__file__).resolve().parents[1] / "scripts" / "check_bt_delegation.py")
cbd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cbd)

LOG = "| L-407 | d | k | 「**C 案1**」 | x |\n| L-418 | d | k | 「**案1 共有**」 | x |\n"
DOC = ("## 0. 表\n| a | L-407「**C 案1**」+ L-418「**案1 共有**」 |\n## 1. 材料\n"
       "**周回の数え方と止める条件(…)**: 本文\n**要件**: 通過の判定(§0 の L-407・L-418 の行)はオーナーだけが変える。\n")
VER = "### 監査役の出力(逐語)\n1. [直す] 全文。\n### リードの処置\n(…)\n"


def test_clean_document_passes():
    assert cbd.check(DOC, LOG, VER) == []


def test_missing_owner_row_and_non_verbatim_quote():
    errs = cbd.check(DOC.replace("L-418「**案1 共有**」", "L-419「**案1 共有**」"), LOG, VER)
    assert any("L-419" in e and "行が無い" in e for e in errs)
    errs = cbd.check(DOC.replace("案1 共有", "案1 共有する"), LOG, VER)
    assert any("逐語で無い" in e for e in errs)


def test_owner_only_list_must_be_in_section_0():
    errs = cbd.check(DOC.replace("L-407・L-418 の行", "L-407・L-418・L-420 の行"), LOG + "| L-420 | d | k | q | x |\n", VER)
    assert any("L-420" in e and "§0 の表に無い" in e for e in errs)


def test_single_definition_and_no_abbreviated_auditor_output():
    errs = cbd.check(DOC + "**周回の数え方と止める条件(再)**: 二重\n", LOG, VER)
    assert any("定義が 2 回" in e for e in errs)
    errs = cbd.check(DOC, LOG, "### 監査役の出力(逐語)\n1. [直す] 前半(…)後半\n")
    assert any("(…)" in e for e in errs)


def test_quoted_ellipsis_in_auditor_text_is_not_a_cut():
    assert cbd.check(DOC, LOG, "### 監査役の出力(逐語)\n1. [聞く] 記録が「(…)」で切られている。\n") == []


def test_every_agent_call_carries_its_own_roles_scrutiny_constant():
    good = ("const a = await agent(`作業 ${(args.lead_notes || {})[0]} ${SCRUTINY_FIX}`, { label: `作る:0#1`, model: M })\n"
            "const j = await agent(`判定 ${SCRUTINY_JUDGE}`, { label: `盲検:0#1:current0`, model: M })\n"
            "const au = await agent(`検査`, { label: `監査役(表):1`, agentType: 'owner-auditor', model: M })\n")
    assert cbd.check_script(good) == []
    missing = good + "const t = await agent(`表を作る`, { label: `表:1#1`, model: M })\n"
    assert any("表:1#1" in e and "SCRUTINY_TABLE" in e for e in cbd.check_script(missing))
    wrong = good + "const c = await agent(`批評 ${SCRUTINY_FIX}`, { label: `批評:1#1`, model: M })\n"
    errs = cbd.check_script(wrong)
    assert any("SCRUTINY_CRITIC が無い" in e for e in errs) and any("別の役" in e for e in errs)
    unknown = good + "const u = await agent(`x ${SCRUTINY_FIX}`, { label: `謎:1`, model: M })\n"
    errs = cbd.check_script(unknown)
    assert any("ROLE_SCRUTINY に無い" in e for e in errs) and not any("別の役" in e for e in errs)
    # audit 47's actual shape: the role's own constant is present and the fixing text is appended on top
    both = good + "const c = await agent(`批評 ${SCRUTINY_CRITIC}${SCRUTINY_FIX}`, { label: `批評:1#1`, model: M })\n"
    errs = cbd.check_script(both)
    assert errs == [e for e in errs if "別の役" in e and "SCRUTINY_FIX" in e] and len(errs) == 1


def test_lint_script_reports_undefined_names_the_way_run_7_died():
    import shutil
    if not shutil.which("eslint"):
        assert cbd.lint_script("const a = 1\n") and "eslint" in cbd.lint_script("const a = 1\n")[0]
        return
    ok = "export const meta = { name: 'x', description: 'y' }\nconst r = await agent(`p`)\nreturn { r }\n"
    assert cbd.lint_script(ok) == []
    bad = "export const meta = { name: 'x', description: 'y' }\nconst r = await agent(`${openFix}`)\nreturn { r }\n"
    assert any("openFix" in e and "no-undef" in e for e in cbd.lint_script(bad))


def test_lead_notes_must_reach_the_battery_auditors_and_fixers():
    ok = ("const a = await agent(`作業 ${(args.lead_notes || {})[0]} ${SCRUTINY_FIX}`, { label: `作る:0#1`, model: M })\n"
          "const au = await agent(`直す ${(args.lead_notes || {})[0]} ${SCRUTINY_FIX}`, { label: `場面の直し:0#1`, model: M })\n")
    assert cbd.check_script(ok) == []
    bad = ("const a = await agent(`作業 ${SCRUTINY_FIX}`, { label: `作る:0#1`, model: M })\n"
           "const au = await agent(`直す ${SCRUTINY_FIX}`, { label: `場面の直し:0#1`, model: M })\n")
    errs = cbd.check_script(bad)
    assert sum("lead_notes" in e for e in errs) == 2


def test_launch_args_are_checked_against_delegation_script_and_owner_log():
    import hashlib
    import json
    check_args = cbd.check_args
    deleg = "委任文の本文"
    sha = hashlib.sha256(deleg.encode("utf-8")).hexdigest()[:12]
    script = "const a = args.marker; const b = args.lead_notes; const c = args.prebuilt"
    log = "| L-436 | 案1 |\n"
    good = json.dumps({"marker": f"d.md@{sha}", "lead_notes": {"0": "L-436 のとおり"}, "prebuilt": {}})
    assert check_args(good, deleg, "d.md", script, log) == []
    bad = json.dumps({"marker": "d.md@000000000000", "lead_definitions": {}, "lead_notes": {"0": "L-999"}})
    errs = check_args(bad, deleg, "d.md", script, log)
    assert any("marker" in e for e in errs)
    assert any("lead_definitions" in e for e in errs)
    assert any("L-999" in e for e in errs)


def test_scene_keeper_write_destination_is_the_same_pair_everywhere():
    ok = "… 節「リードに聞くこと」 … lead_answer_changes …"
    assert cbd.check_destination(ok, ok, ok) == []
    errs = cbd.check_destination(ok, "台本に欄が無い", "lead_notes は questions_for_lead と書いた 節「リードに聞くこと」")
    assert any("台本" in e for e in errs) and any("引数" in e and "lead_answer_changes" in e for e in errs)


def test_no_touch_wiring_is_required_in_repair_and_audit_prompts():
    good = "async function repairBattery(a) {\n  x`触れない git diff --name-only HEAD changed_files`\n}\nfunction checkBattery(b) {\n  return b.changed_files.filter(x => !x.startsWith('tests/bt/battery/'))\n}\n"
    assert cbd.check_no_touch(good) == []
    bad = "async function repairBattery(a) {\n  x`直す`\n}\nfunction checkBattery(b) {\n  return []\n}\n"
    errs = cbd.check_no_touch(bad)
    assert any("repairBattery" in e for e in errs) and any("checkBattery" in e for e in errs)


def test_framework_fingerprint_changes_with_roles_stages_or_pass_rule_only():
    deleg = "| 通過の判定 = 両組で同等以上 |\n枠組みの指紋: 000000000000\n"
    script = "async function runItem(a) {\n agent(`x`, { label: `作る:${item.id}#1` })\n}\n"
    fp = cbd.framework_fingerprint(deleg, script)
    assert cbd.check_fingerprint(deleg, script) and "指紋が変わった" in cbd.check_fingerprint(deleg, script)[0]
    ok = deleg.replace("000000000000", fp)
    assert cbd.check_fingerprint(ok, script) == []
    assert cbd.framework_fingerprint(ok.replace("同等以上", "圧倒"), script) != fp   # pass rule changes it
    assert cbd.framework_fingerprint(ok + "\n文言の直し\n", script) == fp            # wording does not
    assert cbd.framework_fingerprint(ok, script.replace("作る:", "定義:")) != fp        # a role changes it


def test_framework_fingerprint_changes_when_a_decision_function_body_changes():
    deleg = "| 通過の判定 = x |\n"
    script = "function splitStops(a) { return a }\nfunction judgeRound(n, c, s) { return n === 1 }\nasync function runItem(i) {}\n"
    fp = cbd.framework_fingerprint(deleg, script)
    assert cbd.framework_fingerprint(deleg, script.replace("n === 1", "n === 2")) != fp
    assert cbd.framework_fingerprint(deleg, script.replace("return a", "return []")) != fp   # splitStops too (63-3)


def test_cut_function_ignores_braces_inside_strings_templates_and_comments():
    src = "function f(a) {\n  const s = `x ${a} }` // } comment\n  const q = '}'\n  return { k: 1 }\n}\nfunction g() { return 2 }\n"
    body = cbd._cut_function(src, "f")
    assert body.endswith("return { k: 1 }\n}") and "function g" not in body


def test_end_bound_number_must_match_the_script_default_and_args():
    row = "| 通過の判定 = x **終わりの上限:** 項目 1〜4 は 1 項目あたり最大 10 周 | L-407 |\n"
    assert cbd.check_bound(row, "const CAP = Number(args.round_cap) || 10", '{"round_cap": 10}') == []
    assert any("台本" in e for e in cbd.check_bound(row, "const CAP = Number(args.round_cap) || 5", '{"round_cap": 10}'))
    assert any("引数" in e for e in cbd.check_bound(row, "const CAP = Number(args.round_cap) || 10", '{"round_cap": 5}'))
    assert any("欄が無い" in e for e in cbd.check_bound("| 通過の判定 = x | L-407 |\n"))
