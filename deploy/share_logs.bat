@echo off
rem Copy the paper logs into paper_logs\ and push, so the Claude research
rem session can pull and analyse the raw files directly.
rem Safe while the bot is running: files are copied, never moved, and the
rem readers tolerate a partial last line. WS recordings (data\ws) are too
rem large for git - only a directory listing is shared.
setlocal
cd /d "%~dp0.."

rem A machine that has never committed needs an identity; set a repo-local
rem fallback only when none is configured anywhere.
git config user.name >nul 2>&1 || git config user.name "bot-operator"
git config user.email >nul 2>&1 || git config user.email "komekome3ai@gmail.com"

rem Sync with the remote BEFORE pushing - the research session commits to
rem this branch too, so an un-pulled clone would be rejected as
rem non-fast-forward. Local runtime files are untouched by a pull.
git pull --rebase origin claude/bitflyer-trading-bot-hhxxaf
if errorlevel 1 (
  echo.
  echo *** git pull failed - fix the error above, then rerun. ***
  pause
  exit /b 1
)

if not exist paper_logs mkdir paper_logs
copy /Y logs\bot.jsonl        paper_logs\ >nul 2>&1
copy /Y logs\status.json      paper_logs\ >nul 2>&1
copy /Y data\scalp_paper.jsonl paper_logs\ >nul 2>&1
copy /Y data\oi_snapshots.csv paper_logs\ >nul 2>&1
copy /Y data\spread_FX_BTC_JPY.csv paper_logs\ >nul 2>&1
copy /Y data\overlay_state.json paper_logs\ >nul 2>&1
copy /Y data\kill_switch.json paper_logs\ >nul 2>&1
dir /-C data\ws > paper_logs\ws_listing.txt 2>nul

git add paper_logs
git commit -m "paper logs snapshot %date% %time%"
git push origin claude/bitflyer-trading-bot-hhxxaf
if errorlevel 1 (
  echo.
  echo *** git push failed - if a login window appeared, sign in and rerun. ***
  pause
  exit /b 1
)
echo.
echo Done. Tell Claude: "ログを上げました"
pause
