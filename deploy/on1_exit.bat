@echo off
rem ============================================================
rem  ON1 exit job (docs/ON1_LIVE_PLAN.md L1): 8:40 market SELL
rem  (close) of the single Nikkei 225 micro long.
rem  Task Scheduler: weekdays 08:35, "Run whether user is logged
rem  on or not". kabu STATION must be running and logged in on
rem  this PC (it force-logs-out early in the morning, so the API
rem  token is re-issued by the job itself).
rem  Sends nothing at all unless the LIVE double gate is armed
rem  (config\on1_live.yaml enabled+live_ack AND env ON1_LIVE).
rem  If the account does not hold exactly the expected 1 long, the
rem  job records an alert and orders NOTHING (fail-close).
rem  Emergency stop: create a KILL file in the repo root.
rem ============================================================
cd /d "%~dp0.."
if not exist logs mkdir logs
".venv\Scripts\python.exe" "scripts\run_on1_exit.py" >> "logs\on1.out.log" 2>&1
exit /b 0
