"""deploy\\*.bat conventions.

cmd.exe is not available here, so these are structural checks, not an
execution. They pin the two things that have actually broken on the Windows
box: non-ASCII output (the console is cp932 and prints mojibake) and a script
that carries on after a step failed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
BATS = sorted(DEPLOY.glob("*.bat"))


def _text(name: str) -> str:
    return (DEPLOY / name).read_text(encoding="utf-8")


def test_every_bat_starts_at_the_repo_root():
    """A bat is double-clicked from anywhere and from Task Scheduler, where the
    working directory is not the repo."""
    for bat in BATS:
        assert 'cd /d "%~dp0.."' in bat.read_text(encoding="utf-8"), bat.name


@pytest.mark.parametrize("name", ["restart_all.bat"])
def test_bat_output_is_ascii_only(name):
    """Non-ASCII output renders as mojibake under cp932. restart_all.bat is the
    one an operator reads line by line while it runs."""
    raw = (DEPLOY / name).read_bytes()
    bad = [(i, b) for i, b in enumerate(raw) if b > 127]
    assert not bad, f"{name}: non-ASCII byte at {bad[0][0]}"


def test_restart_all_runs_the_four_steps_in_order():
    text = _text("restart_all.bat")
    steps = [text.index(m) for m in
             ("echo [1/4] git pull", "echo [2/4] pip install",
              "echo [3/4] stop_all.bat", "echo [4/4] start_all.bat")]
    assert steps == sorted(steps)
    # the update pair from docs/OPERATIONS.md 4.5, then the restart pair
    assert "git pull" in text
    assert '"%PIP%" install -e ".[dev]"' in text
    assert 'call "%~dp0stop_all.bat"' in text      # reuses the existing bats
    assert 'call "%~dp0start_all.bat"' in text


def test_restart_all_aborts_before_restarting_on_a_failed_update():
    """A pull conflict or a pip failure must NOT reach stop_all: restarting
    into a half-updated tree is worse than staying on the old code."""
    text = _text("restart_all.bat")
    # every step is guarded, and every guard leaves the script
    assert text.count("if errorlevel 1 (") == 4
    assert text.count("goto :aborted") == 5        # 4 steps + the missing venv
    assert "if not exist \"%PIP%\"" in text        # no venv is a failure too
    stop = text.index('call "%~dp0stop_all.bat"')
    for guard in ("*** FAILED: git pull ***", "*** FAILED: pip install ***"):
        assert text.index(guard) < stop
    assert text.rstrip().endswith("exit /b 1")     # aborted path is the last
    assert ":aborted" in text and "exit /b 0" in text


def test_stop_all_reports_success_explicitly():
    """restart_all.bat aborts on a non-zero step, and stop_all's last command
    used to be `timeout`, whose exit code is not about stopping anything."""
    assert _text("stop_all.bat").rstrip().endswith("exit /b 0")


def test_restart_all_is_documented_as_the_recommended_update_path():
    ops = (Path(__file__).resolve().parents[1] / "docs" / "OPERATIONS.md"
           ).read_text(encoding="utf-8")
    section = ops.split("## 4.5")[1].split("## 5.")[0]
    assert "restart_all.bat" in section
    for step in ("git pull", 'pip install -e ".[dev]"', "stop_all.bat",
                 "start_all.bat"):
        assert step in section
