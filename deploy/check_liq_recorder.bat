@echo off
rem ============================================================
rem  bitflyer-bot: is the liquidation recorder actually recording?
rem
rem  Why this exists (P8 step 3): the liquidation stream is the one
rem  dataset whose past cannot be bought back. Every hour the recorder
rem  is down is a permanent hole in Binance and BitMEX. share_logs
rem  only runs once a day, so without this the answer takes 24 hours.
rem
rem  Read-only: prints process state, the tail of the log and the files
rem  written so far. Changes nothing, starts nothing.
rem ============================================================
setlocal
cd /d "%~dp0.."
chcp 65001 >nul

echo === 1. process ===
powershell -NoProfile -Command "$m = Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -like '*record_liquidations.py*' }; if ($m) { 'RUNNING  pid=' + ($m.ProcessId -join ',') } else { 'NOT RUNNING  <- deploy\start_all.bat で起動してください' }"

echo.
echo === 2. log (last 20 lines of logs\liquidations.out.log) ===
if exist "logs\liquidations.out.log" (
    powershell -NoProfile -Command "Get-Content 'logs\liquidations.out.log' -Tail 20"
) else (
    echo ログがありません = 一度も起動していません
)

echo.
echo === 3. files (data\liquidations) ===
if exist "data\liquidations" (
    powershell -NoProfile -Command "Get-ChildItem 'data\liquidations' | Sort-Object Name | Format-Table Name, @{n='KB';e={[math]::Round($_.Length/1KB,1)}}, LastWriteTime -AutoSize"
) else (
    echo data\liquidations がまだありません
)

echo.
echo この出力に秘密情報は含まれません。そのまま共有して構いません。
endlocal
pause
