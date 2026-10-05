"""分析の文書の骨組み(`scripts/analysis/diag_skeleton.py`)と、骨組みの無い書き込みを止めるフック
(`.claude/hooks/analysis_skeleton_gate.sh`、L-694)の試験。

フックは一時の根(スキルの写しと `docs/ANALYSIS/` を置いたもの)を `CLAUDE_PROJECT_DIR` に渡して、PreToolUse の
入力(JSON)を標準入力で与えて走らせる。止める = 終了コード 2、通す = 0。
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOK = os.environ.get("GATE_HOOK") or os.path.join(ROOT, ".claude", "hooks", "analysis_skeleton_gate.sh")
SKILL = os.path.join(ROOT, ".claude", "skills", "analysis-lens", "SKILL.md")

spec = importlib.util.spec_from_file_location("diag_skeleton", os.path.join(ROOT, "scripts", "analysis", "diag_skeleton.py"))
ds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ds)


@pytest.fixture()
def root(tmp_path):
    d = tmp_path / ".claude" / "skills" / "analysis-lens"
    d.mkdir(parents=True)
    shutil.copy(SKILL, d / "SKILL.md")
    (tmp_path / "docs" / "ANALYSIS").mkdir(parents=True)
    return tmp_path


def run(root, tool, inp):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    p = subprocess.run(["sh", HOOK], input=json.dumps({"tool_name": tool, "tool_input": inp}),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


def doc(root, name="2026-10-05_x.md"):
    return str(root / "docs" / "ANALYSIS" / name)


def test_steps_in_skill_order():
    names = [n for n, _, _ in ds.skill_steps()]
    assert names[0] == "P" and names[-1] == "D10"
    assert names == ["P", "D0", "D8", "D1", "D1b", "D2", "D3", "D4", "D5", "D6", "D7", "D9", "D9b", "D10"]
    assert all(body for _, _, body in ds.skill_steps())


def test_skeleton_passes(root):
    rc, err = run(root, "Write", {"file_path": doc(root), "content": ds.new_doc("x", "2026-10-05")})
    assert rc == 0, err


def test_missing_step_is_stopped(root):
    text = ds.new_doc("x", "2026-10-05")
    a, b = text.index("<!-- step:P -->"), text.index("<!-- /step:P -->") + len("<!-- /step:P -->")
    rc, err = run(root, "Write", {"file_path": doc(root), "content": text[:a] + text[b:]})
    assert rc == 2 and "手順 P の節" in err


def test_free_text_document_is_stopped(root):
    rc, err = run(root, "Write", {"file_path": doc(root), "content": "# カード 5\n\n結論: 稼げる。\n"})
    assert rc == 2 and "手順 D10 の節" in err


def test_altered_copy_is_stopped(root):
    text = ds.new_doc("x", "2026-10-05")
    line = next(ln for ln in text.split("\n") if ln.startswith("> - 止めるもの: 前提を 1 文で書けないなら"))
    rc, err = run(root, "Write", {"file_path": doc(root), "content": text.replace(line, "> - 止めるもの: なし", 1)})
    assert rc == 2 and "手順 P の写しがスキルの本文と違う" in err


def test_wrong_order_is_stopped(root):
    text = ds.new_doc("x", "2026-10-05")
    blocks = {}
    for n in ("D0", "D8"):
        s = text.index(f"<!-- step:{n} -->")
        e = text.index(f"<!-- /step:{n} -->") + len(f"<!-- /step:{n} -->")
        blocks[n] = (s, e, text[s:e])
    (s0, e0, b0), (s8, e8, b8) = blocks["D0"], blocks["D8"]
    swapped = text[:s0] + b8 + text[e0:s8] + b0 + text[e8:]
    rc, err = run(root, "Write", {"file_path": doc(root), "content": swapped})
    assert rc == 2 and "順がスキルと違う" in err


def test_other_paths_pass(root):
    rc, _ = run(root, "Write", {"file_path": str(root / "docs" / "DISCUSSIONS" / "a.md"), "content": "自由"})
    assert rc == 0
    rc, _ = run(root, "Write", {"file_path": str(root / "docs" / "ANALYSIS" / "README.md"), "content": "説明"})
    assert rc == 0


def test_edit_filling_a_section_passes_and_removing_copy_is_stopped(root):
    p = doc(root)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(ds.new_doc("x", "2026-10-05"))
    rc, err = run(root, "Edit", {"file_path": p, "old_string": "### 当てたこと(P)\n\n打ったコマンドと出力の在処 / 当てないなら理由 / 分かれ道で止めたなら「止めた: <分かれ道>」\n\n(未記入)",
                                 "new_string": "### 当てたこと(P)\n\n前提: bitFlyer は 1 分遅れる。"})
    assert rc == 0, err
    rc, err = run(root, "Edit", {"file_path": p, "old_string": "<!-- step:D1 -->", "new_string": ""})
    assert rc == 2 and "手順 D1 の節" in err


def test_bash_writes_into_analysis_are_stopped(root):
    for cmd in ("echo x > docs/ANALYSIS/2026-10-05_x.md", "cat a.md | tee docs/ANALYSIS/y.md",
                "sed -i s/a/b/ docs/ANALYSIS/2026-10-05_x.md", "cp /tmp/a.md docs/ANALYSIS/z.md",
                "python3 -c \"open('docs/ANALYSIS/q.md','w').write('x')\""):
        rc, err = run(root, "Bash", {"command": cmd})
        assert rc == 2, cmd
    for cmd in ("python3 scripts/analysis/diag_skeleton.py --unit x", "cat docs/ANALYSIS/2026-10-05_x.md",
                "git add docs/ANALYSIS/2026-10-05_x.md", "ls docs/ANALYSIS 2>/dev/null", "echo hi > /tmp/a"):
        rc, err = run(root, "Bash", {"command": cmd})
        assert rc == 0, (cmd, err)


def test_refresh_keeps_filled_sections(root, monkeypatch):
    p = doc(root)
    text = ds.new_doc("x", "2026-10-05").replace("(未記入)", "前提: 書いた。", 1)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text.replace("> - 入力: カードの文書", "> - 入力: 古い版の文", 1))
    out = ds.refresh(p)
    assert "前提: 書いた。" in out and out == text


def _drop_step(text, name):
    """節 1 つ(見出しから次の見出しの手前まで)を消す = その節が無かった古い版の文書。"""
    a = text.index(f"<!-- step:{name} -->")
    a = text.rindex("\n## ", 0, a) + 1
    b = text.index("\n## ", text.index(f"<!-- /step:{name} -->")) + 1
    return text[:a] + text[b:]


def test_old_document_without_new_step_is_stopped_then_refresh_adds_it(root):
    """スキルに手順を足した後(L-702 の D9b)、その節が無い古い文書への書き込みは止まり、
    --refresh が無い節をスキルの順の位置に空の欄で足すと通る。書いた欄は残る。"""
    p = doc(root)
    full = ds.new_doc("x", "2026-10-05").replace("(未記入)", "前提: 書いた。", 1)
    old = _drop_step(full, "D9b")
    assert "<!-- step:D9b -->" not in old
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(old)
    rc, err = run(root, "Edit", {"file_path": p, "old_string": "前提: 書いた。", "new_string": "前提: 書き直した。"})
    assert rc == 2 and "手順 D9b の節" in err
    out = ds.refresh(p)
    assert out == full
    assert out.index("<!-- step:D9 -->") < out.index("<!-- step:D9b -->") < out.index("<!-- step:D10 -->")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(out)
    rc, err = run(root, "Edit", {"file_path": p, "old_string": "前提: 書いた。", "new_string": "前提: 書き直した。"})
    assert rc == 0, err


def test_refresh_adds_missing_last_and_first_steps(root):
    p = doc(root)
    full = ds.new_doc("x", "2026-10-05")
    for name in ("D10", "P"):
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(_drop_step(full, name) if name != "D10" else full[:full.rindex("\n## D10 ") + 1])
        assert ds.refresh(p) == full, name
