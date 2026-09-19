"""`scripts/jev_*.py` の CLI と、`src/bot` からの独立性を検査する。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _run(args, env=None, cwd=None):
    full_env = dict(**__import__("os").environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, *args], cwd=cwd or REPO, env=full_env,
        capture_output=True, text=True, timeout=60,
    )


def test_jev_prescreen_dry_run_works_without_key(tmp_path):
    artifact = tmp_path / "sample.md"
    artifact.write_text("これはテスト用の成果物です。秘密情報は含みません。", encoding="utf-8")

    env = dict(__import__("os").environ)
    env.pop("TYPESAFE_API_KEY", None)

    result = subprocess.run(
        [sys.executable, "scripts/jev_prescreen.py", str(artifact), "--dry-run"],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["state_chars"] > 0
    # P1..P16 + risk
    assert len(out["questions"]) == 17
    assert "risk" in out["questions"]
    assert out["truncated"] is False


def test_jev_prescreen_dry_run_truncates_long_artifact(tmp_path):
    artifact = tmp_path / "long.md"
    artifact.write_text("あ" * 70_000, encoding="utf-8")

    env = dict(__import__("os").environ)
    env.pop("TYPESAFE_API_KEY", None)

    result = subprocess.run(
        [sys.executable, "scripts/jev_prescreen.py", str(artifact), "--dry-run"],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["truncated"] is True
    assert out["state_chars"] <= 60_000


def test_jev_eval_build_runs_in_tmp_dir(tmp_path):
    out_dir = tmp_path / "eval_out"
    result = subprocess.run(
        [sys.executable, "scripts/jev_eval.py", "build", "--out", str(out_dir)],
        cwd=REPO, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) > 0
    labels_path = out_dir / "labels_template.csv"
    assert labels_path.is_file()
    header = labels_path.read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",")[:2] == ["file", "has_answer"]
    assert "P1" in header and "P16" in header
    # 少なくとも1件は before/answers が対応しないことを既に把握している
    # (HYGIENE_2026-09-11.md。件数そのものは実行環境の docs/AUDITOR に依存するので、
    # ここでは「対応なしが 0 件ではない」ことだけを検査する)
    n_no_answer = sum(1 for v in manifest.values() if v["answers_path"] is None)
    assert n_no_answer >= 1


def test_src_bot_does_not_import_jev():
    """`src/bot/` 配下のどのファイルも `jev` を import していない(grep で 0 件)。"""
    result = subprocess.run(
        ["grep", "-rl", "-E", r"^\s*(import|from)\s+.*\bjev\b", str(REPO / "src" / "bot")],
        capture_output=True, text=True,
    )
    # grep: マッチが無ければ returncode==1, stdout は空
    assert result.returncode == 1, f"src/bot が jev を import している: {result.stdout}"
    assert result.stdout.strip() == ""
