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
rem The console codepage is cp932. A log line containing a character cp932
rem cannot encode (an em dash, for one) raises UnicodeEncodeError inside
rem print() and KILLS the component - that is how the liquidation recorder
rem died on its first disconnect (2026-09-09). UTF-8 mode plus errors=replace
rem makes output incapable of raising, for every script launched here.
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8:replace

call :launch "main-bot"    "scripts\run_paper.py"       run_paper.py       "logs\run_paper.out.log"
call :launch "ws-recorder" "scripts\record_realtime.py" record_realtime.py "logs\recorder.out.log"
call :launch "venue-recorder" "scripts\record_venues.py" record_venues.py  "logs\venues.out.log"
rem 清算(強制決済)ストリーム。履歴が買えない唯一のデータなので止めない (L-026)
call :launch "liq-recorder" "scripts\record_liquidations.py" record_liquidations.py "logs\liquidations.out.log"
rem read-only API latency probe (P13, L-098). 168h then exits; the guard above
rem relaunches it on the next start_all, so the nightly restart keeps it alive
rem without anyone double-clicking probe_latency.bat (L-132 / KA-30).
call :launch "latency-probe" "scripts\probe_api_latency.py" probe_api_latency.py "logs\latency_probe.out.log"
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
