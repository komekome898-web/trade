@echo off
rem ============================================================
rem  ON1 entry job (docs/ON1_LIVE_PLAN.md L1): 15:40 market-on-
rem  close BUY of 1 Nikkei 225 micro contract.
rem  Task Scheduler: weekdays 15:35, "Run whether user is logged
rem  on or not". kabu STATION must be running and logged in on
rem  this PC; if it is not, the job records "order_not_sent" and
rem  stops (nothing is retried).
rem  Sends nothing at all unless the LIVE double gate is armed
rem  (config\on1_live.yaml enabled+live_ack AND env ON1_LIVE);
rem  otherwise the payload only goes to data\on1_live\events.jsonl.
rem  Emergency stop: create a KILL file in the repo root.
rem ============================================================
cd /d "%~dp0.."
if not exist logs mkdir logs
".venv\Scripts\python.exe" "scripts\run_on1_entry.py" >> "logs\on1.out.log" 2>&1
exit /b 0
