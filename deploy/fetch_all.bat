@echo off
rem Periodic data collection for Windows Task Scheduler (bitFlyer + external).
cd /d "%~dp0.."
if not exist logs mkdir logs
".venv\Scripts\python.exe" "scripts\fetch_history.py" >> "logs\fetch.out.log" 2>&1
".venv\Scripts\python.exe" "scripts\fetch_external.py" --days 2 --swing-days 30 >> "logs\fetch.out.log" 2>&1
".venv\Scripts\python.exe" "scripts\record_oi.py" >> "logs\fetch.out.log" 2>&1
rem Best-effort: turns data\ws WS recordings into compact daily tape CSVs
rem (data\tape) that share_logs.bat can carry past the 31-day API limit.
".venv\Scripts\python.exe" "scripts\extract_tape.py" >> "logs\fetch.out.log" 2>&1
rem ON1 forward paper tracking: JPX daily report (published T+1 09:00 JST) ->
rem session prints -> paper ledger (docs/PREREG_on1_forward.md)
".venv\Scripts\python.exe" "scripts\fetch_jpx_daily.py" >> "logs\fetch.out.log" 2>&1
".venv\Scripts\python.exe" "scripts\paper_on1.py" >> "logs\fetch.out.log" 2>&1
rem crowd-heat gauge series (Wikipedia/GDELT/F&G) for the dashboard tile
".venv\Scripts\python.exe" "scripts\fetch_attention.py" >> "logs\fetch.out.log" 2>&1
