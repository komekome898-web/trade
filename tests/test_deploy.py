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


def test_restart_all_runs_the_five_steps_in_order():
    text = _text("restart_all.bat")
    steps = [text.index(m) for m in
             ("echo [1/5] git pull", "echo [2/5] pip install",
              "echo [3/5] stop_all.bat", "echo [4/5] verify components",
              "echo [5/5] start_all.bat")]
    assert steps == sorted(steps)
    # the update pair from docs/OPERATIONS.md 4.5, then the restart pair,
    # with the stopped-component check wedged between them
    assert "git pull" in text
    assert '"%PIP%" install -e ".[dev]"' in text
    assert 'call "%~dp0stop_all.bat"' in text      # reuses the existing bats
    assert 'call "%~dp0start_all.bat"' in text


def test_restart_all_aborts_before_restarting_on_a_failed_update():
    """A pull conflict or a pip failure must NOT reach stop_all: restarting
    into a half-updated tree is worse than staying on the old code."""
    text = _text("restart_all.bat")
    # every step is guarded, and every guard leaves the script
    assert text.count("if errorlevel 1 (") == 5
    # one exit per errorlevel guard, plus the two preconditions that are checked
    # before anything runs at all: no venv, and a merge left unfinished
    assert text.count("goto :aborted") == 7
    assert "if not exist \"%PIP%\"" in text        # no venv is a failure too
    stop = text.index('call "%~dp0stop_all.bat"')
    for guard in ("*** FAILED: git pull ***", "*** FAILED: pip install ***",
                  "*** BLOCKED: an earlier merge was never finished ***"):
        assert text.index(guard) < stop
    assert text.rstrip().endswith("exit /b 1")     # aborted path is the last
    assert ":aborted" in text and "exit /b 0" in text


def test_restart_all_names_the_way_out_of_an_unfinished_merge():
    """git's own error ("You have not concluded your merge") does not say how to
    get out, and on 2026-09-09 that stalled every pull and every restart until
    it was asked about. The file that hits the wall names the one command."""
    text = _text("restart_all.bat")
    assert 'if exist ".git\\MERGE_HEAD"' in text
    merge_guard = text.index("*** BLOCKED: an earlier merge was never finished ***")
    assert text.index("git commit --no-edit", merge_guard) > merge_guard
    # and it must be checked BEFORE the pull that it would otherwise break
    assert merge_guard < text.index("git pull --rebase")


def test_restart_all_verifies_components_are_gone_before_starting():
    """stop_all.bat's contract is only to ATTEMPT a stop (it always exits 0);
    a survivor must block start_all, not be started alongside a duplicate."""
    text = _text("restart_all.bat")
    stop = text.index('call "%~dp0stop_all.bat"')
    verify = text.index("echo [4/5] verify components")
    start = text.index('call "%~dp0start_all.bat"')
    assert stop < verify < start
    # re-runs the SAME four-process query stop_all.bat uses
    verify_block = text[verify:start]
    for needle in ("run_paper.py", "run_scalp_paper.py", "record_realtime.py",
                  "dashboard.py", "Get-CimInstance Win32_Process"):
        assert needle in verify_block
    assert "still running" in verify_block          # names the survivor(s)
    assert "*** FAILED: component" in verify_block
    assert "start_all.bat was NOT run" in verify_block
    assert text.index("*** FAILED: component") < start


def test_stop_all_reports_success_explicitly():
    """restart_all.bat aborts on a non-zero step, and stop_all's last command
    used to be `timeout`, whose exit code is not about stopping anything.
    stop_all's contract stays 'attempted' — verifying the stop actually took
    is restart_all's job (test_restart_all_verifies_components_are_gone)."""
    assert _text("stop_all.bat").rstrip().endswith("exit /b 0")


def test_restart_all_is_documented_as_the_recommended_update_path():
    ops = (Path(__file__).resolve().parents[1] / "docs" / "OPERATIONS.md"
           ).read_text(encoding="utf-8")
    section = ops.split("## 4.5")[1].split("## 5.")[0]
    assert "restart_all.bat" in section
    for step in ("git pull", 'pip install -e ".[dev]"', "stop_all.bat",
                 "start_all.bat"):
        assert step in section


def test_no_bare_parentheses_inside_bat_blocks():
    """cmd ends an `if (...) else (...)` block at the first unescaped `)`. An echo
    line such as `echo starting (168h, 30s interval)` inside a block therefore
    kills the batch with a syntax error before the block's real work runs -
    exactly how deploy/probe_latency.bat never launched the probe (L-133,
    2026-09-12). Inside a block, parentheses in echo text must be ^( ^)."""
    import re
    bad = []
    for bat in BATS:
        depth = 0
        for n, line in enumerate(bat.read_text(encoding="utf-8", errors="surrogateescape").splitlines(), 1):
            stripped = line.strip()
            if stripped.lower().startswith("rem "):
                continue
            if depth > 0 and stripped.lower().startswith("echo"):
                if re.search(r"(?<!\^)[()]", stripped[4:]):
                    bad.append(f"{bat.name}:{n}: {stripped}")
            # track block depth on the *command* part only (ignore quoted strings)
            unquoted = re.sub(r'"[^"]*"', "", stripped)
            unquoted = re.sub(r"\^.", "", unquoted)
            depth += unquoted.count("(") - unquoted.count(")")
            depth = max(depth, 0)
    assert not bad, "\n".join(bad)


# ---- forward-only recorders (spec r2, docs/DISCUSSIONS/2026-10-02_W2_recorders_spec_r2.md)
# record_hyperliquid.py / record_okx_traders.py (resident, start_all.bat) and
# record_deribit_oi.py (one-shot, fetch_all.bat). Start, stop, restart, share
# and fetch are one scope: the first version wired start_all only and the
# existing test_every_launched_component_is_also_stopped_and_verified failed.
import os  # noqa: E402
import re as _re  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

FIVE = ("start_all.bat", "stop_all.bat", "restart_all.bat", "share_logs.bat",
        "fetch_all.bat")
NEW_SOURCES = ("hyperliquid", "okx_traders", "deribit_options")


def test_start_all_launches_both_resident_recorders():
    start = _text("start_all.bat")
    assert ('call :launch "hl-recorder" "scripts\\record_hyperliquid.py --loop" '
            'record_hyperliquid.py "logs\\hyperliquid.out.log"') in start
    assert ('call :launch "okx-trader-recorder" "scripts\\record_okx_traders.py '
            '--loop 3600" record_okx_traders.py "logs\\okx_traders.out.log"') in start


def test_stop_all_stops_them_and_restart_all_checks_they_are_gone():
    """Also pinned for every launch line by
    test_record_liquidations.test_every_launched_component_is_also_stopped_and_verified;
    here the exact process match in both PowerShell queries."""
    stop = _text("stop_all.bat")
    restart = _text("restart_all.bat")
    verify = restart[restart.index("echo [4/5] verify components"):
                     restart.index('call "%~dp0start_all.bat"')]
    for script in ("record_hyperliquid.py", "record_okx_traders.py"):
        pattern = f"$_.CommandLine -like '*{script}*'"
        assert pattern in stop, script
        assert pattern in verify, script


def test_stop_all_clears_the_locks_of_the_recorders_it_killed():
    """A lock left by a force-killed copy counts as live for 180 s, so the
    copy that restart_all starts right after would exit (code 3)."""
    stop = _text("stop_all.bat")
    kill = stop.index("Stop-Process")
    for lock in ("data\\hyperliquid.lock", "data\\okx_traders.lock"):
        line = f'if exist "{lock}" del /q "{lock}"'
        assert line in stop and stop.index(line) > kill, lock


def test_fetch_all_runs_the_deribit_recorder_right_after_record_oi():
    fetch = _text("fetch_all.bat")
    line = ('".venv\\Scripts\\python.exe" "scripts\\record_deribit_oi.py" '
            '>> "logs\\fetch_all.out.log" 2>&1')
    assert line in fetch
    assert fetch.index("record_oi.py") < fetch.index(line) < fetch.index("fetch_history.py")


def _share_line() -> str:
    lines = [ln for ln in _text("share_logs.bat").splitlines()
             if ln.startswith("powershell") and all(s in ln for s in NEW_SOURCES)]
    assert len(lines) == 1, lines
    return lines[0]


def test_share_logs_copies_the_three_sources_by_finished_utc_day_only():
    """Structure of the one line that shares the three sources: today's UTC
    date, a name-day strictly before it, before the commit; and no blanket
    copy of the directories (that would commit today's half-written file and
    then the finished one, about 1.9x the volume)."""
    text = _text("share_logs.bat")
    line = _share_line()
    assert "(Get-Date).ToUniversalTime().ToString('yyyyMMdd')" in line
    assert "-match '_(\\d{8})\\.' -and $Matches[1] -lt $t" in line
    assert "foreach ($s in 'hyperliquid','okx_traders','deribit_options')" in line
    assert "$dst = 'paper_logs\\' + $s" in line and "$src = 'data\\' + $s" in line
    assert text.index(line) < text.index("git add paper_logs")
    for s in NEW_SOURCES:
        assert f"copy /Y data\\{s}\\" not in text, s


def _fake_tree(root: Path, today: str, yday: str) -> None:
    for s, names in {
        "hyperliquid": [f"positions_{today}.csv.gz", f"positions_{yday}.csv.gz",
                        f"positions_{yday}.trunc1.csv.gz",
                        f"positions_{today}.trunc1.csv.gz",
                        "sweeps_20260930.csv.gz", "notes.txt"],
        "okx_traders": [f"history_{yday}.csv.gz", f"history_{today}.csv.gz"],
        "deribit_options": [f"book_{today}.csv.gz", f"book_{yday}.csv.gz"],
    }.items():
        (root / "data" / s).mkdir(parents=True)
        for n in names:
            (root / "data" / s / n).write_text(n, encoding="utf-8")
    (root / "data" / "okx_traders.lock").write_text("x", encoding="utf-8")


def _expected_copies(today: str, yday: str) -> set[str]:
    return {f"paper_logs/hyperliquid/positions_{yday}.csv.gz",
            f"paper_logs/hyperliquid/positions_{yday}.trunc1.csv.gz",
            "paper_logs/hyperliquid/sweeps_20260930.csv.gz",
            f"paper_logs/okx_traders/history_{yday}.csv.gz",
            f"paper_logs/deribit_options/book_{yday}.csv.gz"}


def test_share_selection_rule_keeps_todays_files_out():
    """The line's own rule (its regex and comparison, read from the bat)
    applied to a listing: finished days and their renamed files go, today's
    files never do. Executed for real by the next test when PowerShell is
    installed."""
    line = _share_line()
    rx = _re.search(r"-match '([^']+)' -and \$Matches\[1\] -lt \$t", line).group(1)
    today = "20261002"
    names = ["positions_20261002.csv.gz", "positions_20261001.csv.gz",
             "positions_20261001.trunc1.csv.gz", "positions_20261002.trunc2.csv.gz",
             "book_20260930.csv.gz", "leaderboard.csv.gz"]
    chosen = [n for n in names
              if (m := _re.search(rx, n)) and m.group(1) < today]
    assert chosen == ["positions_20261001.csv.gz", "positions_20261001.trunc1.csv.gz",
                      "book_20260930.csv.gz"]


def _pwsh() -> str | None:
    return os.environ.get("PWSH") or shutil.which("pwsh") or shutil.which("powershell")


@pytest.mark.skipif(_pwsh() is None, reason="PowerShell is not installed here")
def test_share_line_runs_in_powershell_and_copies_finished_days_only(tmp_path):
    line = _share_line()
    cmd = line[len('powershell -NoProfile -Command "'):line.rindex('" >nul 2>&1')]
    now = datetime.now(timezone.utc)
    today, yday = now.strftime("%Y%m%d"), (now - timedelta(days=1)).strftime("%Y%m%d")
    _fake_tree(tmp_path, today, yday)
    # an earlier share already copied one file with the same size: skipped
    (tmp_path / "paper_logs" / "okx_traders").mkdir(parents=True)
    kept = tmp_path / "paper_logs" / "okx_traders" / f"history_{yday}.csv.gz"
    kept.write_text("o" * len(f"history_{yday}.csv.gz"), encoding="utf-8")
    old_bytes = kept.read_bytes()
    env = dict(os.environ, DOTNET_SYSTEM_GLOBALIZATION_INVARIANT="1")
    r = subprocess.run([_pwsh(), "-NoProfile", "-Command", cmd], cwd=tmp_path,
                       capture_output=True, text=True, timeout=120, env=env)
    if datetime.now(timezone.utc).strftime("%Y%m%d") != today:
        pytest.skip("the UTC day changed while the test ran")
    assert r.returncode == 0, r.stderr
    got = {p.relative_to(tmp_path).as_posix()
           for p in (tmp_path / "paper_logs").rglob("*") if p.is_file()}
    assert got == _expected_copies(today, yday)
    assert kept.read_bytes() == old_bytes


def _cp932_eaten_line_ends(data: bytes) -> list[int]:
    """1-based numbers of the lines whose line end cmd.exe (cp932) would read
    as the second byte of a double-byte character -- that joins the next
    line onto a rem and it never runs (first critic, 2026-10-02)."""
    eaten, line, i = [], 1, 0
    while i < len(data):
        b = data[i]
        if 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC:
            nxt = data[i + 1] if i + 1 < len(data) else None
            if nxt in (0x0A, 0x0D):
                eaten.append(line)
            if nxt == 0x0A:
                line += 1
            i += 2
            continue
        if b == 0x0A:
            line += 1
        i += 1
    return eaten


def test_cp932_check_finds_a_line_end_eaten_by_a_lead_byte():
    assert _cp932_eaten_line_ends("rem ok\nrem 側\nrun\n".encode("utf-8")) == []
    ch = next(c for c in map(chr, range(0x3000, 0x9FFF))
              if 0x81 <= c.encode("utf-8")[-1] <= 0x9F)
    assert _cp932_eaten_line_ends(f"rem {ch}\nrun\n".encode("utf-8")) == [1]


@pytest.mark.parametrize("name", FIVE)
def test_no_line_end_of_the_five_bats_is_eaten_under_cp932(name):
    assert _cp932_eaten_line_ends((DEPLOY / name).read_bytes()) == [], name


# Non-ASCII rem lines that were in these files before 2026-10-02 (left as they
# were; each passes the cp932 check above). Any other rem line must be ASCII.
_OLD_NON_ASCII_REMS = {
    "rem 清算(強制決済)ストリーム。履歴が買えない唯一のデータなので止めない (L-026)",
    "rem down first, so a later Stop-Process may find the PID already gone — fine.",
    'rem liquidation recorder log: the self-heal line ("不完全 -> ... へ退避") after a',
}


@pytest.mark.parametrize("name", FIVE)
def test_rem_lines_are_ascii(name):
    bad = [ln for ln in _text(name).splitlines()
           if ln.strip().lower().startswith("rem") and not ln.isascii()
           and ln.strip() not in _OLD_NON_ASCII_REMS]
    assert not bad, bad
