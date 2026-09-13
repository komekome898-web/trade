"""研究の関門が**呼ばれていること**を測る試験(2026-09-13、10 本目の監査、L-164)。

**なぜ指紋の台帳ではなくテストなのか。**
10 本目の監査の指摘: 共有部品 `scripts/_research_audit_gate.py` は指紋の台帳に載ったが、
**それを呼んでいる側**(`src/bot/research/sealed.py` / `scripts/phase2/p2_02_final.py` /
`scripts/judge_gates.py`)は載っていないので、呼び出しを消しても検知されない。指摘は正しい。

ただし、この 3 本は**研究のたびに手を入れる現役のコード**である。台帳に載せると
「オーナーの指示があったときだけ変更する」の対象になり、**普通の研究作業が止まる**。
(この非対称をどう扱うかはオーナーに出してある。台帳の範囲はオーナーが決めること。)

そこで、消したら**落ちる**ものを置く。指紋は「改変が差分に残る」ことしか保証しないが、
この試験は**関門が実際に呼ばれているか**を毎回の `pytest` で測る。
消せば赤くなり、赤いまま押し出せば行動の関門が止める。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def _audit_record(root: Path, unit: str, stage: str) -> None:
    log = root / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"> 指摘の本文 {i} 行目。これは監査役が書いた文である。" for i in range(1, 10))
    log.write_text(f"## 試験\n\n監査対象: {unit}/{stage}\n**監査役**: `owner-model-auditor`\n\n"
                   f"{body}\n\n判定: 通す\n", encoding="utf-8")


# --- 共有部品そのもの --------------------------------------------------------

def test_gate_refuses_when_no_record(tmp_path):
    from _research_audit_gate import find_audit
    ok, why = find_audit("U1", "結果", tmp_path)
    assert not ok and "読めない" in why


def test_gate_passes_with_a_record(tmp_path):
    from _research_audit_gate import find_audit
    _audit_record(tmp_path, "U1", "結果")
    ok, why = find_audit("U1", "結果", tmp_path)
    assert ok, why


def test_gate_refuses_when_the_last_verdict_is_stop(tmp_path):
    """判定は**行頭の「判定:」のうち最後のもの**だけを見る(引用を鍵にしない)。"""
    from _research_audit_gate import find_audit
    _audit_record(tmp_path, "U1", "結果")
    log = tmp_path / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.write_text(log.read_text(encoding="utf-8") + "\n判定: 止める\n", encoding="utf-8")
    ok, why = find_audit("U1", "結果", tmp_path)
    assert not ok and "止める" in why


def test_gate_refuses_a_thin_record(tmp_path):
    """見出しだけの空の追記では通さない。"""
    from _research_audit_gate import find_audit
    log = tmp_path / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.parent.mkdir(parents=True)
    log.write_text("## x\n\n監査対象: U1/結果\n`owner-model-auditor`\n\n判定: 通す\n",
                   encoding="utf-8")
    ok, why = find_audit("U1", "結果", tmp_path)
    assert not ok and "本文" in why


# --- 呼び出し口が生きているか(消したらここが落ちる)-------------------------

def test_load_sealed_calls_the_gate():
    """`bot.research.sealed.load_sealed` が 4 つ目の門を持っていること。"""
    import inspect
    from bot.research import sealed
    src = inspect.getsource(sealed.load_sealed)
    assert "_research_audit_gate" in src, "load_sealed から監査の門が消えている"
    assert "封印の開封" in src


def test_p2_02_check_guards_calls_the_gate():
    """`load_sealed` の二重実装にも同じ門があること(片方だけ塞がない)。"""
    text = (ROOT / "scripts" / "phase2" / "p2_02_final.py").read_text(encoding="utf-8")
    assert "_research_audit_gate" in text, "check_guards から監査の門が消えている"
    assert "封印の開封" in text


def test_judge_gates_requires_a_unit():
    """`judge_gates.py` に**関門を通らない経路が無い**こと。

    10 本目の監査の指摘: `--no-audit-gate` を消しても、`--unit` を省けば
    関門は呼ばれず結果が出ていた。旗の名前が消えただけで挙動は同じだった。
    """
    text = (ROOT / "scripts" / "judge_gates.py").read_text(encoding="utf-8")
    assert "--no-audit-gate" not in text.replace("`--no-audit-gate`", ""), \
        "関門を外す旗が復活している"
    assert 'ap.add_argument("--unit", required=True' in text, \
        "--unit が必須でないと、省くだけで関門を通らずに結果が出る"
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "judge_gates.py")],
                         capture_output=True, text=True, cwd=str(ROOT))
    assert out.returncode != 0
    assert "--unit" in out.stderr


@pytest.mark.parametrize("unit,stage", [("U1", "封印の開封"), ("U1", "結果")])
def test_require_audit_exits_with_2(tmp_path, unit, stage):
    from _research_audit_gate import require_audit
    with pytest.raises(SystemExit) as e:
        require_audit(unit, stage, tmp_path)
    assert e.value.code == 2
