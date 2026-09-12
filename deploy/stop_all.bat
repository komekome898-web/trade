@echo off
rem Stop all bitflyer-bot python components (main bot, scalper, WS recorder,
rem venue recorder, liquidation recorder, dashboard).
rem The list MUST match the :launch lines in start_all.bat - a component missing
rem here is never restarted by restart_all.bat and silently keeps running the old
rem code (that happened to the liquidation recorder, 2026-09-09). A test pins it.
rem Paper-only processes: hard stop is safe (state lives in files/sqlite).
cd /d "%~dp0.."
rem -ErrorAction SilentlyContinue: killing a parent python can take its child
rem down first, so a later Stop-Process may find the PID already gone — fine.
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -like '*run_paper.py*' -or $_.CommandLine -like '*run_scalp_paper.py*' -or $_.CommandLine -like '*record_realtime.py*' -or $_.CommandLine -like '*record_venues.py*' -or $_.CommandLine -like '*record_liquidations.py*' -or $_.CommandLine -like '*dashboard.py*' } | ForEach-Object { Write-Host ('stopping PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
rem The liquidation recorder holds a lock file so two copies can never append
rem to the same gzip. A force-killed recorder leaves it behind, and start_all
rem would then refuse to start - so the authority that killed it clears it.
if exist "data\liquidations.lock" del /q "data\liquidations.lock"
echo All bot components stopped.
timeout /t 5 >nul
rem Explicit success: stopping a process that was already gone is not a
rem failure, and restart_all.bat aborts on a non-zero step. Without this the
rem exit code is whatever `timeout` happened to return.
exit /b 0
