@echo off
rem Periodic data collection for Windows Task Scheduler (bitFlyer + external).
cd /d "%~dp0.."
if not exist logs mkdir logs
rem The console codepage is cp932. A log line containing a character cp932
rem cannot encode (an em dash, for one) raises UnicodeEncodeError inside
rem print() and KILLS the component - that is how the liquidation recorder
rem died on its first disconnect (2026-09-09). UTF-8 mode plus errors=replace
rem makes output incapable of raising, for every script launched here.
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8:replace
rem Time-critical, cheap collector FIRST (DATA_QA_TRIAGE: the 2026-08-31 2.9h OI gap
rem was a stalled earlier step in this sequential batch, not an outage). Nothing
rem network-heavy runs before it.
".venv\Scripts\python.exe" "scripts\record_oi.py" >> "logs\fetch.out.log" 2>&1
".venv\Scripts\python.exe" "scripts\fetch_history.py" >> "logs\fetch.out.log" 2>&1
".venv\Scripts\python.exe" "scripts\fetch_external.py" --days 2 --swing-days 30 >> "logs\fetch.out.log" 2>&1
rem OKX open interest + long/short ratio history (30d / 2-3d API windows; the
rem retention snapshot halves those windows). Was missing here until 2026-09-05.
".venv\Scripts\python.exe" "scripts\fetch_okx.py" >> "logs\fetch.out.log" 2>&1
rem Best-effort: turns data\ws WS recordings into compact daily tape CSVs
rem (data\tape) that share_logs.bat can carry past the 31-day API limit.
rem --board-top 10 (EXEC_FLOOR_PREREG.md sec7 row 1, owner L-098) additionally
rem reconstructs the order book to 1-second top-10 depth samples
rem (data\tape\board_top10_YYYYMMDD.csv.gz, ~5-7MB/day estimated from the
rem top-5 on-demand baseline of ~2.7MB/day avg -- see docs/OWNER_PROCEDURES.md
rem P11). Manifest-tracked and incremental like the executions/ticker output.
".venv\Scripts\python.exe" "scripts\extract_tape.py" --board-top 10 >> "logs\fetch.out.log" 2>&1
rem Funding rate + FX/spot basis daily log (EXEC_FLOOR_PREREG.md sec7 row 2,
rem owner L-098): public endpoints only, idempotent (dedup by settlement
rem time) -- safe to run every 15 minutes on this schedule. See
rem docs/OWNER_PROCEDURES.md P12.
".venv\Scripts\python.exe" "scripts\record_funding_basis.py" >> "logs\fetch.out.log" 2>&1
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
rem Data governance (docs/DATA.md section 0, formerly DATA_GOVERNANCE_PLAN.md):
rem intake ledger (data\INTAKE.jsonl append-only history + data\INTAKE_latest.json
rem materialized index of every file under data\, paper_logs\, backtest_data\,
rem data\archive\) MUST run before data_quality.py, which only reads that index
rem and never re-walks the filesystem itself. Both are read-only over the data
rem they inventory/check -- neither ever writes, moves or deletes a data file.
".venv\Scripts\python.exe" "scripts\intake_ledger.py" >> "logs\fetch.out.log" 2>&1
rem Snapshot integrity (docs/DATA.md section 0): verifies every MD5SUMS
rem under backtest_data\ against the files on disk, creates a new MD5SUMS
rem for any snapshot dir that lacks one, and cross-checks against the intake
rem ledger above -> data\SNAPSHOT_VERIFY.json. Read-only over data files;
rem the only write is a brand-new MD5SUMS. Non-zero exit on any mismatch is
rem intentionally ignored here so the rest of fetch_all still runs.
".venv\Scripts\python.exe" "scripts\verify_snapshots.py" >> "logs\fetch.out.log" 2>&1
rem Read-only listing of every data\ws recording (member count, complete?, recoverable
rem rows) -> data\WS_GZ_LISTING.json; shared by share_logs.bat (docs/DATA.md section 0).
".venv\Scripts\python.exe" "scripts\repair_gz_listing.py" --json "data\WS_GZ_LISTING.json" >> "logs\fetch.out.log" 2>&1
".venv\Scripts\python.exe" "scripts\data_quality.py" >> "logs\fetch.out.log" 2>&1
