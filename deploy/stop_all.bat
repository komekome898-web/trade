@echo off
rem Stop all bitflyer-bot python components (main bot, scalper, WS recorder).
rem Paper-only processes: hard stop is safe (state lives in files/sqlite).
cd /d "%~dp0.."
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -like '*run_paper.py*' -or $_.CommandLine -like '*run_scalp_paper.py*' -or $_.CommandLine -like '*record_realtime.py*' } | ForEach-Object { Write-Host ('stopping PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force }"
echo All bot components stopped.
timeout /t 5 >nul
