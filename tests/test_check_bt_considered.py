"""scripts/check_bt_considered.py: the review-table checker of the backtest battery."""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_bt_considered.py"

HEAD = "| 候補 | 段(機構) | 機構 | 実装で確かめたか | 判断 | 理由と根拠 |\n|---|---|---|---|---|---|\n"


def run(tmp_path, body, write=True):
    p = tmp_path / "opponents" / "CONSIDERED.md"
    p.parent.mkdir(exist_ok=True)
    (p.parent / "a_repro.py").write_text("# repro\n", encoding="utf-8")
    p.write_text(body, encoding="utf-8")
    if write:
        subprocess.run([sys.executable, str(SCRIPT), str(p), "--write"], capture_output=True, text=True)
    return subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)


def good():
    return ("### 観点1: 足\n\n動かせた候補: 2 件\n\n" + HEAD +
            "| 1 A | 6 | SCAN 10行 | はい | 再現した | 段 6 が最も高い。opponents/a_repro.py |\n"
            "| 2 B | 2 | SCAN 20行 | はい | スキップ: 明らかに弱い(段が低い) | 段が低い: 段 2 < 6(SCAN 20行) |\n"
            "| 3 C | (空欄) | SCAN 30行 | はい | スキップ: 明らかに弱い(段が低い) | 段が低い: 実装で確かめた段 = 1(SCAN 31行) |\n"
            "| 4 D | 44 | — | いいえ | 再現できない | 危険の 11 件 |\n"
            "\n### 観点2: 板の写真\n\n動かせた候補: 0 件\n\n候補 0 件: `grep -n 板の写真 docs/DATA/SCAN_2026-09-21_tools.md` の当たり 0 行\n")


def test_valid_table_passes_and_aggregate_is_written(tmp_path):
    r = run(tmp_path, good())
    assert r.returncode == 0, r.stdout
    text = (tmp_path / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    assert "| 観点1: 足 | 2 | 4 | 67% | 1 | 0 | 2 | 1 |" in text
    assert "- 観点1: 足: 4 D" in text


def test_blank_stage_cannot_be_skipped_on_stage(tmp_path):
    body = good().replace("段が低い: 実装で確かめた段 = 1(SCAN 31行)", "段が低い(空欄は最高位より低い)")
    r = run(tmp_path, body)
    assert r.returncode == 1 and "段(機構)が空欄" in r.stdout


def test_verdict_outside_the_four_is_rejected(tmp_path):
    r = run(tmp_path, good().replace("| はい | 再現した |", "| はい | 混在 |"))
    assert r.returncode == 1 and "判断「混在」" in r.stdout


def test_not_installable_is_not_a_reason_for_cannot_reproduce(tmp_path):
    r = run(tmp_path, good().replace("危険の 11 件", "Go 製で導入できない"))
    assert r.returncode == 1 and "(a)" in r.stdout


def test_hand_edited_aggregate_is_rejected(tmp_path):
    run(tmp_path, good())
    p = tmp_path / "opponents" / "CONSIDERED.md"
    p.write_text(p.read_text(encoding="utf-8").replace("| 67% |", "| 10% |"), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
    assert r.returncode == 1 and "集計の区画が表と合っていない" in r.stdout


def test_viewpoint_without_table_or_zero_line_is_rejected(tmp_path):
    r = run(tmp_path, good().replace("候補 0 件: `grep -n 板の写真 docs/DATA/SCAN_2026-09-21_tools.md` の当たり 0 行", "判断: 対象なし"))
    assert r.returncode == 1 and "判断の列を持つ表も" in r.stdout
