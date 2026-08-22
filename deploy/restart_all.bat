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
git pull
if errorlevel 1 (
  echo.
  echo *** FAILED: git pull ***
  echo Nothing was stopped - the bot is still running the old code.
  echo A conflict or a local edit blocks the pull; copy the lines
  echo above into the Claude chat.
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
  "$p = Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -like '*run_paper.py*' -or $_.CommandLine -like '*run_scalp_paper.py*' -or $_.CommandLine -like '*record_realtime.py*' -or $_.CommandLine -like '*dashboard.py*' }; if ($p) { $p | ForEach-Object { Write-Host ('still running: PID ' + $_.ProcessId + ' ' + $_.CommandLine) }; exit 1 } else { exit 0 }"
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
pause
exit /b 0

:aborted
echo.
echo ============================================================
echo  ABORTED - the remaining steps were skipped.
echo ============================================================
pause
exit /b 1
