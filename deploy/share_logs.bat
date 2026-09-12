@echo off
rem Copy the paper logs into paper_logs\ and push, so the Claude research
rem session can pull and analyse the raw files directly.
rem Safe while the bot is running: files are copied, never moved, and the
rem readers tolerate a partial last line. WS recordings (data\ws) are too
rem large for git - only a directory listing is shared. The executions
rem extracted from them into data\tape\*.csv.gz (scripts\extract_tape.py,
rem run by fetch_all.bat) are small and ARE shared below.
rem Order matters: COMMIT FIRST, sync after. Committing first keeps the
rem index clean for the rebase, and also self-heals a previous run that
rem staged files but failed to commit.
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs

rem A machine that has never committed needs an identity; set a repo-local
rem fallback only when none is configured anywhere.
git config user.name >nul 2>&1 || git config user.name "bot-operator"
git config user.email >nul 2>&1 || git config user.email "komekome3ai@gmail.com"

echo [share_logs] copying logs and data files
if not exist paper_logs mkdir paper_logs
copy /Y logs\bot.jsonl        paper_logs\ >nul 2>&1
copy /Y logs\status.json      paper_logs\ >nul 2>&1
rem nightly unattended restart (deploy\nightly_restart.bat, P4-N): the lead reads
rem this log the next morning instead of asking the owner (L-122 / L-125).
copy /Y logs\nightly_restart.log paper_logs\ >nul 2>&1
rem liquidation recorder log: the self-heal line ("不完全 -> ... へ退避") after a
rem restart is read from here (P14), so the owner never has to open it.
copy /Y logs\liquidations.out.log paper_logs\ >nul 2>&1
rem fetch_all / latency-probe logs, last 400 lines each: the lead diagnoses P11
rem (board_top10 backfill) and P13 (api probe) from these instead of asking (KA-30).
powershell -NoProfile -Command "if (Test-Path 'logs\fetch.out.log') { Get-Content 'logs\fetch.out.log' -Tail 400 | Set-Content 'paper_logs\fetch.out.tail.log' }" >nul 2>&1
rem the raw tail is swamped by repair_gz_listing output; also share the last 200 lines
rem that mention the P11/P12/P13 collectors so the lead can diagnose them (2026-09-12).
powershell -NoProfile -Command "if (Test-Path 'logs\fetch.out.log') { Select-String -Path 'logs\fetch.out.log' -Pattern 'extract_tape|board row|record_funding|probe_api|Traceback|Error' | Select-Object -Last 200 | ForEach-Object { $_.Line } | Set-Content 'paper_logs\fetch.out.collectors.log' }" >nul 2>&1
powershell -NoProfile -Command "if (Test-Path 'logs\latency_probe.out.log') { Get-Content 'logs\latency_probe.out.log' -Tail 400 | Set-Content 'paper_logs\latency_probe.out.tail.log' }" >nul 2>&1
copy /Y data\scalp_paper.jsonl paper_logs\ >nul 2>&1
copy /Y data\oi_snapshots.csv paper_logs\ >nul 2>&1
copy /Y data\spread_FX_BTC_JPY.csv paper_logs\ >nul 2>&1
copy /Y data\overlay_state.json paper_logs\ >nul 2>&1
copy /Y data\kill_switch.json paper_logs\ >nul 2>&1
rem ON1 forward paper ledger + its JPX source (small CSVs)
copy /Y data\paper_on1\ledger.csv paper_logs\on1_ledger.csv >nul 2>&1
copy /Y data\jpx_daily\nk225_sessions.csv paper_logs\nk225_sessions.csv >nul 2>&1
rem ONR forward paper ledger + status (small CSV/JSON)
copy /Y data\paper_onr\ledger.csv paper_logs\onr_ledger.csv >nul 2>&1
copy /Y data\paper_onr\status.json paper_logs\onr_status.json >nul 2>&1
rem S12 clock-burst status tile feed (n / fresh period / last day only)
copy /Y data\s12_status.json paper_logs\s12_status.json >nul 2>&1
dir /-C data\ws > paper_logs\ws_listing.txt 2>nul
rem This wildcard also carries the daily board_top10_YYYYMMDD.csv.gz files
rem (EXEC_FLOOR_PREREG.md sec7 row 1, owner L-098; extract_tape.py --board-top 10
rem in fetch_all.bat) alongside executions/ticker -- no separate copy line needed.
if not exist paper_logs\tape mkdir paper_logs\tape
if exist data\tape\*.csv.gz copy /Y data\tape\*.csv.gz paper_logs\tape\ >nul 2>&1
if not exist paper_logs\venues mkdir paper_logs\venues
if exist data\venues\*.csv.gz copy /Y data\venues\*.csv.gz paper_logs\venues\ >nul 2>&1
rem Binance daily metrics + USDJPY (dashboard G6 features / yen conversion)
if not exist paper_logs\binance_daily mkdir paper_logs\binance_daily
if exist data\binance_daily\*.csv copy /Y data\binance_daily\*.csv paper_logs\binance_daily\ >nul 2>&1
rem Round 17 board-round derived series (scripts\run_board_round.py output;
rem the 1GB data\ws raw recordings stay local, only the ~8MB derived series
rem and its coverage report are shared)
copy /Y data\board_round\series_5s.csv.gz paper_logs\board_round_series_5s.csv.gz >nul 2>&1
copy /Y data\board_round\coverage.json paper_logs\board_round_coverage.json >nul 2>&1
rem Funding rate history + FX/spot basis daily log (EXEC_FLOOR_PREREG.md
rem sec7 row 2, owner L-098; scripts\record_funding_basis.py in fetch_all.bat)
copy /Y data\funding_rate_history.csv paper_logs\funding_rate_history.csv >nul 2>&1
copy /Y data\basis_log.csv paper_logs\basis_log.csv >nul 2>&1
rem Order-ack latency probe, read-only (EXEC_FLOOR_PREREG.md sec7 row 3,
rem owner L-098; deploy\probe_latency.bat / scripts\probe_api_latency.py)
if not exist paper_logs\latency mkdir paper_logs\latency
if exist data\latency\api_probe.csv copy /Y data\latency\api_probe.csv paper_logs\latency\ >nul 2>&1

rem Data governance: the intake ledger and quality report are produced by
rem fetch_all.bat (unattended, scheduled). This interactive script only
rem COPIES whatever ledger/report exists -- it never runs Python, so it
rem finishes in seconds and cannot look frozen.
echo [share_logs] copying ledger / quality report (if present)
if exist data\INTAKE_latest.json copy /Y data\INTAKE_latest.json paper_logs\ >nul 2>&1
if exist data\INTAKE.jsonl       copy /Y data\INTAKE.jsonl       paper_logs\ >nul 2>&1
if exist data\QUALITY.json       copy /Y data\QUALITY.json       paper_logs\ >nul 2>&1
if exist data\WS_GZ_LISTING.json copy /Y data\WS_GZ_LISTING.json paper_logs\ >nul 2>&1
if exist data\SNAPSHOT_VERIFY.json copy /Y data\SNAPSHOT_VERIFY.json paper_logs\ >nul 2>&1
rem data\archive\ (owner PC only, git-excluded) is too large to share by
rem content -- share a LISTING only (QA_PLAN_2026-09.md section 1-2 item 7).
if exist data\archive dir /-C data\archive > paper_logs\archive_listing.txt 2>nul

echo [share_logs] git add / commit
git add paper_logs
rem Permanent retention snapshots (scripts\retention_snapshot.py, run by
rem fetch_all.bat) land in backtest_data\auto_<source>_<date>\ and were
rem never committed here, so the research environment never received them
rem (incident I-002). git does not expand wildcards itself, so loop the
rem matching directories one by one.
echo [share_logs] adding retention snapshots (backtest_data\auto_*)
for /d %%D in (backtest_data\auto_*) do git add "%%D"

rem Liquidation stream: cannot be bought back, so it must not stay as one copy
rem on this PC (L-026). COPY it like everything else above - do NOT `git add -f`
rem the live directory. The recorder appends to those .gz files continuously, so
rem tracking them makes the working tree permanently dirty and `git pull
rem --rebase` can then never run: restart_all.bat died on exactly that
rem (2026-09-09). Copying leaves data\ untracked and the tree clean.
echo [share_logs] copying liquidation stream (data\liquidations)
if not exist paper_logs\liquidations mkdir paper_logs\liquidations
if exist data\liquidations\*.jsonl.gz copy /Y data\liquidations\*.jsonl.gz paper_logs\liquidations\ >nul 2>&1
git add paper_logs\liquidations
rem Commit only when there is something staged (quiet no-op otherwise).
git diff --cached --quiet || git commit -m "paper logs snapshot %date% %time%"

rem Sync with the remote BEFORE pushing - the research session commits to
rem this branch too, so an un-pulled clone would be rejected as
rem non-fast-forward. paper_logs is written only from this machine, so
rem the rebase cannot conflict on it.
echo [share_logs] git pull --rebase
rem --autostash: same reason as restart_all.bat - this machine writes tracked
rem files continuously, and a rebase refuses to start on a dirty tree. Without
rem it every nightly share since 2026-09-09 could fail here and nothing reached
rem the research session (found 2026-09-12, L-128).
git pull --rebase --autostash origin claude/bitflyer-trading-bot-hhxxaf
if errorlevel 1 (
  echo.
  echo *** git pull failed - copy the error above into the Claude chat. ***
  exit /b 1
)

echo [share_logs] git push
git push origin claude/bitflyer-trading-bot-hhxxaf
if errorlevel 1 (
  echo.
  echo *** git push failed - if a login window appeared, sign in and rerun. ***
  exit /b 1
)
echo.
echo [share_logs] Done. Tell Claude that the logs are up.
