@echo off
rem ============================================================
rem  bitflyer-bot: nightly unattended update+restart (owner L-125).
rem  Task Scheduler runs this once a day at 04:02 JST, inside bitFlyer's
rem  daily maintenance window (04:00-04:10 JST), so the ~1 minute the
rem  recorders are down costs no data. It runs restart_all.bat with the
rem  pauses disabled and everything appended to logs\nightly_restart.log.
rem  Why a COPY of restart_all.bat is executed: cmd reads a .bat file
rem  incrementally by byte offset, and restart_all's own step [1/5] is a
rem  git pull that may rewrite restart_all.bat on disk mid-run. Running an
rem  untracked copy (deploy\_restart_all_copy.bat, gitignored) keeps the
rem  script being executed stable while the tracked file changes. The
rem  copy is refreshed from the tracked file on every run, so the NEXT
rem  night always runs the newest restart_all.bat. %~dp0 still points at
rem  deploy\, so stop_all.bat / start_all.bat resolve as usual.
rem  The `call` is the last statement for the same reason (this wrapper
rem  may itself be rewritten by the pull).
rem  Interplay with the two existing scheduled tasks (OPERATIONS.md 5):
rem  bitflyer-start-all (hourly) launching between our stop_all and
rem  start_all is harmless - start_all skips components that are already
rem  running, so the second launcher finds them and skips. bitflyer-fetch
rem  (15 min) landing inside the few seconds of git pull may see a
rem  half-updated tree and fail that one cycle; every fetch script is
rem  idempotent and the next cycle repeats it. Neither is prevented here.
rem  Register once (P4, cmd or PowerShell, no admin):
rem    schtasks /Create /TN "trade_nightly_restart" /TR "C:\Users\ryoma\trade\deploy\nightly_restart.bat" /SC DAILY /ST 04:02 /F
rem  ASCII only (cp932 console).
rem ============================================================
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
set TRADE_NONINTERACTIVE=1
rem Never wait on a credential prompt: unattended, a GUI/terminal prompt
rem would hang the task. With stored credentials nothing changes; without
rem them git pull fails fast and restart_all aborts (bot keeps old code).
set GIT_TERMINAL_PROMPT=0
set GCM_INTERACTIVE=never
rem Keep the log bounded: above ~5 MB roll it to .1 (one generation kept).
for %%A in ("logs\nightly_restart.log") do if %%~zA GTR 5000000 move /Y "logs\nightly_restart.log" "logs\nightly_restart.log.1" >nul
echo ============================================================>> "logs\nightly_restart.log"
echo nightly_restart start %DATE% %TIME%>> "logs\nightly_restart.log"
copy /Y "%~dp0restart_all.bat" "%~dp0_restart_all_copy.bat" >nul
if errorlevel 1 (
  echo nightly_restart: could not copy restart_all.bat - nothing run>> "logs\nightly_restart.log"
  exit /b 1
)
call "%~dp0_restart_all_copy.bat" >> "logs\nightly_restart.log" 2>&1
