@echo off
rem ============================================================
rem  Kill-switch reset -- HUMAN-CONFIRMED, never automatic.
rem  Shows WHY the switch tripped, asks for an explicit YES, then
rem  stops every component, clears the persisted state, restarts.
rem
rem  The safety invariant (CLAUDE.md sec.1) stays intact: nothing
rem  in start_all.bat / restart_all.bat / the hourly watchdog ever
rem  clears a tripped switch. This file is the ONE sanctioned path
rem  and it only runs when a person double-clicks it and types YES
rem  after reading the trip reason. If the reason is unclear, run
rem  share_logs.bat first and ask Claude to diagnose before
rem  resetting -- especially for order_state_unknown.
rem ============================================================
setlocal
cd /d "%~dp0.."

if not exist data\kill_switch.json if not exist KILL (
  echo Kill switch is NOT tripped. Nothing to do.
  pause
  exit /b 0
)

echo ============================================
echo   KILL SWITCH IS TRIPPED
echo ============================================
if exist data\kill_switch.json (
  echo state file data\kill_switch.json:
  type data\kill_switch.json
  echo.
)
if exist KILL echo manual KILL file is present in the repo root.
echo.
echo Read the reason above. Reset only if you understand the cause.
echo If unsure: close this window, run share_logs.bat, ask Claude.
echo.
set "CONFIRM="
set /p CONFIRM=Type YES to stop all components, reset, and restart:
if /i not "%CONFIRM%"=="YES" (
  echo Aborted. Kill switch left tripped.
  pause
  exit /b 1
)

call "%~dp0stop_all.bat"
if errorlevel 1 (
  echo stop_all failed -- NOT resetting. Kill switch left tripped.
  pause
  exit /b 1
)

if exist data\kill_switch.json del data\kill_switch.json
if exist KILL del KILL
echo Kill switch state cleared.

call "%~dp0start_all.bat"
echo.
echo Reset complete. Check http://127.0.0.1:8300 -- kill_switch should be null.
pause
