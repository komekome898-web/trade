@echo off
rem ============================================================
rem  bitflyer-bot: start ALL paper components (idempotent).
rem  Already-running components are detected and skipped, so this
rem  file doubles as a watchdog: schedule it hourly and crashed
rem  components get relaunched while healthy ones are untouched.
rem  Safety stops survive relaunch: the main bot refuses to trade
rem  while the kill switch is tripped.
rem  2026-08-21: burst scalper RETIRED after its formal paper
rem  rejection (report #16, -3.83bps vs the +5bps bar). The script
rem  stays in scripts\run_scalp_paper.py; re-add a :launch line to
rem  revive it. stop_all.bat still covers a stray instance.
rem ============================================================
cd /d "%~dp0.."
if not exist logs mkdir logs

call :launch "main-bot"    "scripts\run_paper.py"       run_paper.py       "logs\run_paper.out.log"
call :launch "ws-recorder" "scripts\record_realtime.py" record_realtime.py "logs\recorder.out.log"
call :launch "venue-recorder" "scripts\record_venues.py" record_venues.py  "logs\venues.out.log"
call :launch "dashboard"   "scripts\dashboard.py"       dashboard.py       "logs\dashboard.out.log"

echo.
echo Done. Dashboard: http://127.0.0.1:8300
echo Logs: logs\run_paper.out.log / logs\recorder.out.log
timeout /t 5 >nul
exit /b 0

:launch
rem %1=name %2=script path %3=unique filename to detect %4=log file
powershell -NoProfile -Command "$m = Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -like '*%~3*' }; if ($m) { exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo [%~1] already running - skipped
) else (
    echo [%~1] starting...
    start "bitflyer-%~1" /min cmd /c ".venv\Scripts\python.exe %~2 >> %~4 2>&1"
)
exit /b 0
