@echo off
rem ============================================================
rem  ETF auction-fill measurement, ENTRY leg
rem  (docs/PHASE2/EXEC_MEASUREMENT/PREREG.md): 15:20 closing-
rem  auction BUY (FrontOrderType 16) of 1 trading unit of 1343
rem  and 1591, via SOR (Exchange 9).
rem  Task Scheduler: weekdays 15:20, "Run whether user is logged
rem  on or not". kabu STATION must be running and logged in on
rem  this PC; if it is not, the job records "order_not_sent" and
rem  stops (nothing is retried).
rem  Sends nothing at all unless the LIVE TRIPLE gate is armed
rem  (config\etf_measure.yaml enabled+live_ack AND env
rem  ETF_EXEC_LIVE); otherwise the payload only goes to
rem  data\etf_measure\events.jsonl. This gate is SEPARATE from
rem  ON1's: arming ON1 does not arm this measurement.
rem  Emergency stop: create a KILL file in the repo root.
rem ============================================================
cd /d "%~dp0.."
if not exist logs mkdir logs
".venv\Scripts\python.exe" "scripts\run_etf_measure_entry.py" >> "logs\etf_measure.out.log" 2>&1
exit /b 0
