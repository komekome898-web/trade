@echo off
rem ============================================================
rem  bitflyer-bot: start the read-only API latency probe
rem  (EXEC_FLOOR_PREREG.md sec7 row 3, owner L-098; scripts\probe_api_latency.py).
rem
rem  Calls ONE authenticated read-only endpoint (getpermissions -- the
rem  same one check_api.py already uses) + one public endpoint
rem  (getticker FX_BTC_JPY) every 30s for 168h (1 week) and appends
rem  timing to data\latency\api_probe.csv. Read-only: sends NO order.
rem  Refuses to start under LIVE_MODE.
rem
rem  Idempotent: if it is already running, this is a no-op (like
rem  start_all.bat's launcher). Safe to double-click again after a
rem  reboot -- it just resumes appending to the same CSV.
rem
rem  To STOP it early: close the "bitflyer-latency-probe" window, or
rem    taskkill /FI "WINDOWTITLE eq bitflyer-latency-probe*"
rem
rem  ASCII only in this file - the console codepage is cp932.
rem ============================================================
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8:replace

powershell -NoProfile -Command "$m = Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -like '*probe_api_latency.py*' }; if ($m) { exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo [latency-probe] already running - skipped
    echo %DATE% %TIME% skipped-already-running>> logs\latency_probe.launch.log
) else (
    rem NOTE 2026-09-12: this echo used to contain bare parentheses "(168h, 30s interval)".
    rem Inside an if/else ( ... ) block cmd treats the first ")" as the end of the block,
    rem so the batch died on a syntax error before ever reaching `start` - the probe
    rem never launched and wrote nothing (owner report L-133). Parentheses in echo
    rem lines inside blocks must be escaped as ^( ^) (tests/test_deploy.py enforces it).
    echo [latency-probe] starting ^(168h, 30s interval^) -^> data\latency\api_probe.csv
    echo %DATE% %TIME% launch>> logs\latency_probe.launch.log
    start "bitflyer-latency-probe" /min cmd /c ".venv\Scripts\python.exe scripts\probe_api_latency.py %* >> logs\latency_probe.out.log 2>&1"
)
echo.
echo Check it is running:  type logs\latency_probe.out.log
echo Data so far:          data\latency\api_probe.csv
exit /b 0
