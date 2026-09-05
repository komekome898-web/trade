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
rem Commit only when there is something staged (quiet no-op otherwise).
git diff --cached --quiet || git commit -m "paper logs snapshot %date% %time%"

rem Sync with the remote BEFORE pushing - the research session commits to
rem this branch too, so an un-pulled clone would be rejected as
rem non-fast-forward. paper_logs is written only from this machine, so
rem the rebase cannot conflict on it.
echo [share_logs] git pull --rebase
git pull --rebase origin claude/bitflyer-trading-bot-hhxxaf
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
