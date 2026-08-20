@echo off
rem ============================================================
rem  bitflyer-bot: start ALL paper components (idempotent).
rem  Already-running components are detected and skipped, so this
rem  file doubles as a watchdog: schedule it hourly and crashed
rem  components get relaunched while healthy ones are untouched.
rem  Safety stops survive relaunch: the main bot refuses to trade
rem  while the kill switch is tripped, and the scalper refuses to
rem  restart on a day whose daily loss cap was already hit.
rem ============================================================
cd /d "%~dp0.."
if not exist logs mkdir logs

call :launch "main-bot"    "scripts\run_paper.py"       run_paper.py       "logs\run_paper.out.log"
call :launch "scalp-paper" "scripts\run_scalp_paper.py" run_scalp_paper.py "logs\scalp.out.log"
call :launch "ws-recorder" "scripts\record_realtime.py" record_realtime.py "logs\recorder.out.log"

echo.
echo Done. Logs: logs\run_paper.out.log / logs\scalp.out.log / logs\recorder.out.log
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
