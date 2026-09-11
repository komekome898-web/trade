@echo off
rem ============================================================
rem  bitflyer-bot: update and restart. One double-click:
rem    [1/5] git pull
rem    [2/5] .venv\Scripts\pip install -e ".[dev]"
rem    [3/5] stop_all.bat
rem    [4/5] verify the four components are actually gone
rem    [5/5] start_all.bat
rem  Steps 1 and 2 are the pair from docs\OPERATIONS.md 4.5: a
rem  pull without the install leaves a newly added dependency
rem  missing and the component dies seconds after start_all
rem  launches it.
rem  Step 4 exists because stop_all.bat's contract is only to
rem  ATTEMPT a stop (Stop-Process ... -ErrorAction
rem  SilentlyContinue never fails the step). A component that
rem  ignored the kill would otherwise sit there while start_all
rem  launches a second copy alongside it. So this file re-runs
rem  the same process query stop_all used and aborts, naming the
rem  survivor(s), instead of starting on top of them.
rem  ABORT ON FAILURE is the point of this file. If any step
rem  fails, nothing further runs: the bot keeps running the code
rem  it already had (or stays stopped) - the safe outcome.
rem  Restarting into a half-updated tree, or starting a second
rem  copy of a component, is not.
rem  TRADE_NONINTERACTIVE=1 (set by deploy\nightly_restart.bat, the
rem  scheduled nightly run) skips the two `pause` lines: under Task
rem  Scheduler a pause would wait forever for a key that never comes and
rem  the task would hang until the next day's run is skipped as a
rem  duplicate. Double-clicked by hand, the pauses still show the result.
rem  ASCII only - the console codepage is cp932 and non-ASCII
rem  output renders as mojibake.
rem ============================================================
setlocal
cd /d "%~dp0.."
set "PIP=.venv\Scripts\pip.exe"

echo ============================================================
echo  bitflyer-bot: update and restart
echo ============================================================
echo.

echo [1/5] git pull
rem --rebase: a local paper-logs commit that has not been pushed yet must
rem never open a merge-commit editor here (that looks like a freeze and,
rem when killed, leaves MERGE_HEAD behind and blocks every later pull).
rem A merge left unfinished by an EARLIER manual `git pull` blocks this step
rem too, and git's own message does not say how to get out. Name the fix
rem here rather than making the operator ask (happened 2026-09-09).
if exist ".git\MERGE_HEAD" (
  echo.
  echo *** BLOCKED: an earlier merge was never finished ***
  echo A previous `git pull` opened an editor for the merge message and
  echo it was closed without saving, so the merge is still half-done.
  echo Nothing was stopped - the bot is still running the old code.
  echo.
  echo Finish it with ONE command, then run this file again:
  echo.
  echo     git commit --no-edit
  echo.
  echo   --no-edit accepts the prepared message and opens no editor.
  echo   If it reports unmerged paths instead, run `git status` and
  echo   copy the output into the Claude chat.
  goto :aborted
)
rem --autostash: a rebase refuses to start on a dirty tree, and this machine
rem writes data files continuously. Anything uncommitted is set aside and put
rem back automatically instead of stopping the update.
git pull --rebase --autostash origin claude/bitflyer-trading-bot-hhxxaf
if errorlevel 1 (
  echo.
  echo *** FAILED: git pull ***
  echo Nothing was stopped - the bot is still running the old code.
  echo A conflict or a local edit blocks the pull; copy the lines
  echo above into the Claude chat.
  echo.
  echo If it says "unstaged changes", see which files with:
  echo.
  echo     git status --short
  echo.
  echo   A live data file that git is TRACKING is the usual cause - it is
  echo   being appended to right now, so it is never clean. Those belong in
  echo   paper_logs as copies, not tracked in place.
  goto :aborted
)
echo       ok
echo.

echo [2/5] pip install -e ".[dev]"
if not exist "%PIP%" (
  echo.
  echo *** FAILED: %PIP% not found ***
  echo Create the virtualenv first: python -m venv .venv
  echo See docs\OPERATIONS.md section 4.5.
  goto :aborted
)
"%PIP%" install -e ".[dev]"
if errorlevel 1 (
  echo.
  echo *** FAILED: pip install ***
  echo Nothing was stopped - the bot is still running the old code.
  echo Do NOT restart until this step passes: the new code may
  echo import a library that is not installed yet.
  goto :aborted
)
echo       ok
echo.

echo [3/5] stop_all.bat
call "%~dp0stop_all.bat"
if errorlevel 1 (
  echo.
  echo *** FAILED: stop_all.bat ***
  echo Components may still be running. Check Task Manager for
  echo python.exe before starting them again.
  goto :aborted
)
echo       ok
echo.

echo [4/5] verify components are stopped
powershell -NoProfile -Command ^
  "$p = Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -like '*run_paper.py*' -or $_.CommandLine -like '*run_scalp_paper.py*' -or $_.CommandLine -like '*record_realtime.py*' -or $_.CommandLine -like '*record_venues.py*' -or $_.CommandLine -like '*record_liquidations.py*' -or $_.CommandLine -like '*dashboard.py*' }; if ($p) { $p | ForEach-Object { Write-Host ('still running: PID ' + $_.ProcessId + ' ' + $_.CommandLine) }; exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo.
  echo *** FAILED: component^(s^) still running after stop_all.bat ***
  echo See the PID line^(s^) named above for the survivor^(s^).
  echo start_all.bat was NOT run - starting now would run a second
  echo copy alongside the one that would not stop. End it in Task
  echo Manager, or wait and re-run this file.
  goto :aborted
)
echo       ok
echo.

echo [5/5] start_all.bat
call "%~dp0start_all.bat"
if errorlevel 1 (
  echo.
  echo *** FAILED: start_all.bat ***
  echo See the lines above; the components are STOPPED.
  goto :aborted
)

echo.
echo ============================================================
echo  DONE - updated and restarted.
echo  Dashboard: http://127.0.0.1:8300
echo  Logs: logs\run_paper.out.log / logs\recorder.out.log
echo ============================================================
if not defined TRADE_NONINTERACTIVE pause
exit /b 0

:aborted
echo.
echo ============================================================
echo  ABORTED - the remaining steps were skipped.
echo ============================================================
if not defined TRADE_NONINTERACTIVE pause
exit /b 1
