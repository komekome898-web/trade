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
rem ONR forward paper tracking: 1343 ETF (Yahoo) + TSE REIT index (kabutan) ->
rem overnight paper ledger (docs/PREREG_onr_forward.md)
".venv\Scripts\python.exe" "scripts\paper_onr.py" >> "logs\fetch.out.log" 2>&1
rem crowd-heat gauge series (Wikipedia/GDELT/F&G) for the dashboard tile
".venv\Scripts\python.exe" "scripts\fetch_attention.py" >> "logs\fetch.out.log" 2>&1
rem Binance daily futures metrics (G6 features / regime) + USDJPY (yen conversion)
".venv\Scripts\python.exe" "scripts\fetch_binance_daily.py" >> "logs\fetch.out.log" 2>&1
rem S12 clock-burst-30m status tile feed (n / fresh period / last day only;
rem the n<30 safety valve inside the script still applies to the full report)
".venv\Scripts\python.exe" "scripts\research_clock_burst.py" --status-json "data\s12_status.json" >> "logs\fetch.out.log" 2>&1
rem Retention pre-empt (docs/QA_PLAN_2026-09.md item 5): copy-only snapshots
rem of retention-limited sources (bitFlyer 31d, OKX OI/L-S) at half their
rem upstream window into backtest_data\auto_<source>_<date>\, before the
rem intake ledger below records them. Never overwrites, never touches the
rem original files; skips a source with no snapshot due yet.
".venv\Scripts\python.exe" "scripts\retention_snapshot.py" >> "logs\fetch.out.log" 2>&1
rem Data governance (docs/DATA_GOVERNANCE_PLAN.md, docs/QA_PLAN_2026-09.md):
rem intake ledger (data\INTAKE.jsonl append-only history + data\INTAKE_latest.json
rem materialized index of every file under data\, paper_logs\, backtest_data\,
rem data\archive\) MUST run before data_quality.py, which only reads that index
rem and never re-walks the filesystem itself. Both are read-only over the data
rem they inventory/check -- neither ever writes, moves or deletes a data file.
".venv\Scripts\python.exe" "scripts\intake_ledger.py" >> "logs\fetch.out.log" 2>&1
".venv\Scripts\python.exe" "scripts\data_quality.py" >> "logs\fetch.out.log" 2>&1
