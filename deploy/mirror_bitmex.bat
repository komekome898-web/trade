@echo off
rem ============================================================
rem  bitflyer-bot: mirror the BitMEX public archive before the
rem  exchange closes.
rem
rem  DEADLINE (from BitMEX's own announcement API, read 2026-09-09):
rem    2026-09-16 12:00 UTC  XBTUSD and friends delist and settle
rem    2026-09-23            the exchange itself closes
rem  The archive already stopped updating on 2025-02-22 and nothing
rem  says it outlives the exchange.
rem
rem  Downloads about 246 GB (trades 48 GB + quotes 198 GB) into
rem  data\archive\bitmex\ , which git ignores. Nothing else is touched:
rem  no orders, no config, no running component.
rem
rem  SAFE TO STOP AND RERUN. Files already on disk are skipped by size,
rem  a part-downloaded file is never left behind, and it halts by itself
rem  if free space drops below 20 GB. Closing the window is fine.
rem
rem  Progress is written to paper_logs\bitmex_mirror_status.json, which
rem  share_logs.bat shares - so the research side can read how far it got
rem  without anyone having to paste anything.
rem
rem  ASCII only in this file - the console codepage is cp932.
rem ============================================================
setlocal
cd /d "%~dp0.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8:replace
if not exist logs mkdir logs

echo ============================================================
echo  BitMEX archive mirror
echo  Target: data\archive\bitmex   (about 246 GB, hours to days)
echo  Safe to close this window; rerun to continue where it stopped.
echo ============================================================
echo.

".venv\Scripts\python.exe" "scripts\mirror_bitmex_archive.py" %* 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath 'logs\bitmex_mirror.log' -Append"

echo.
echo ============================================================
echo  Stopped. If it says files remain, run this file again.
echo  Log: logs\bitmex_mirror.log
echo ============================================================
pause
