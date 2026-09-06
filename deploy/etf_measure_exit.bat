@echo off
rem ============================================================
rem  ETF auction-fill measurement, EXIT leg
rem  (docs/PHASE2/EXEC_MEASUREMENT/PREREG.md): 08:40 opening-
rem  auction SELL (FrontOrderType 13) of the single long in each
rem  of 1343 and 1591, via SOR (Exchange 9).
rem  Task Scheduler: weekdays 08:40, "Run whether user is logged
rem  on or not". Deliberately 5 minutes after the ON1 exit task
rem  (08:35) so two jobs never hit kabu STATION in the same
rem  minute. kabu STATION force-logs-out early in the morning,
rem  so the API token is re-issued by the job itself.
rem  Sends nothing at all unless the LIVE TRIPLE gate is armed
rem  (config\etf_measure.yaml enabled+live_ack AND env
rem  ETF_EXEC_LIVE).
rem  If the account does not hold exactly the expected 1 trading
rem  unit, the job records an alert and orders NOTHING.
rem  Emergency stop: create a KILL file in the repo root.
rem ============================================================
cd /d "%~dp0.."
if not exist logs mkdir logs
".venv\Scripts\python.exe" "scripts\run_etf_measure_exit.py" >> "logs\etf_measure.out.log" 2>&1
exit /b 0
