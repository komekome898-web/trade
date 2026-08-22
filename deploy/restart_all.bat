@echo off
rem ============================================================
rem  bitflyer-bot: update and restart. One double-click:
rem    [1/4] git pull
rem    [2/4] .venv\Scripts\pip install -e ".[dev]"
rem    [3/4] stop_all.bat
rem    [4/4] start_all.bat
rem  Steps 1 and 2 are the pair from docs\OPERATIONS.md 4.5: a
rem  pull without the install leaves a newly added dependency
rem  missing and the component dies seconds after start_all
rem  launches it.
rem  ABORT ON FAILURE is the point of this file. If the pull or
rem  the install fails, nothing is stopped and nothing is
rem  restarted: the bot keeps running the code it already had,
rem  which is the safe outcome. Restarting into a half-updated
rem  tree is not.
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

echo [1/4] git pull
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

echo [2/4] pip install -e ".[dev]"
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

echo [3/4] stop_all.bat
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

echo [4/4] start_all.bat
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
