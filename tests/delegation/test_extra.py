"""作業者が足した試験(委任文 DELEGATION_checker.md の「決めてよいこと」の 出力の置き場)。

- U16: この委任文そのものと事前の批評の記録 1〜4 を tmp に写して `check_delegation.py --require-approval` を当てると合格する。
- 2 本の道具の「共通の部品」(委任文の検め)が一字違わず同じ(check_report は委任文の検めを写しでやり直すため)。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(os.environ.get("DELEGATION_TOOLS_DIR", ROOT / "scripts" / "delegation"))
CD = TOOLS / "check_delegation.py"
CR = TOOLS / "check_report.py"
SKILL = ROOT / ".claude" / "skills" / "delegated-study"
DIR = ROOT / "docs" / "DISCUSSIONS" / "2026-10-07_delegation_redesign"
NAMES = ["DELEGATION_checker.md"] + [f"DELEGATION_checker_premortem{n}.md" for n in range(1, 5)]

pytestmark = pytest.mark.skipif(not (CD.exists() and CR.exists()), reason="道具がまだ無い(作る前)")


@pytest.mark.skipif(not all((DIR / n).is_file() for n in NAMES), reason="委任文か記録が無い")
def test_u16_real_delegation_passes(tmp_path):
    for n in NAMES:
        shutil.copyfile(DIR / n, tmp_path / n)
    r = subprocess.run([sys.executable, str(CD), str(tmp_path / NAMES[0]), "--owner-log", str(ROOT / "docs" / "OWNER_LOG.md"),
                        "--fixed", str(SKILL / "FIXED_CONSTRAINTS.md"), "--scenes", str(SKILL / "BREAK_SCENES.md"),
                        "--root", str(ROOT), "--require-approval"],
                       capture_output=True, text=True, timeout=60)
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 0, r.stdout
    assert (tmp_path / "DELEGATION_checker.stamp.json").is_file()  # 印は写しの横(tmp)に書かれる


def _shared(p: Path) -> str:
    s = p.read_text(encoding="utf-8")
    a = s.index("# ==== 共通の部品(ここから")
    b = s.index("# ==== 共通の部品(ここまで) ====")
    return s[a:b]


def test_shared_part_is_identical():
    assert _shared(CD) == _shared(CR)


def test_quote_outside_purpose_ignores_reading_column(tmp_path):
    """目的の節の外の引用も、OWNER_LOG の 4 列目だけと比べる(読みの列・「L-100 結果」の行には当てない)。
    test_spec の囮の場面は目的の節の中だけなので、目的の外の比べをここで見る(変異の表 U4)。"""
    import test_spec as S  # 名前で取り込まない(test_spec の試験を二重に集めないため)

    bad = []
    for name, quote in (("読みの列", "読みだけにある文"), ("「L-100 結果」の行", "結果の行にだけある文")):
        env = S.Env(tmp_path / name)
        env.edit("## 報告\n\n- 書く", f"## 報告\n\n- 書く(L-100「**{quote}**」)")
        r = env.cd()
        if r.returncode != 1 or "L-100" not in r.stdout:
            bad.append(f"{name}: {r.returncode}: {r.stdout.strip()[:200]}")
    assert not bad, "\n".join(bad)
