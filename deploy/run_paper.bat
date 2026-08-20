@echo off
rem Paper-trading bot launcher for Windows Task Scheduler.
rem Changes to the repo root itself, so the task's "Start in" field can be empty.
rem All output (including startup errors) goes to logs\run_paper.out.log.
cd /d "%~dp0.."
if not exist logs mkdir logs
echo [%date% %time%] launcher start >> "logs\run_paper.out.log"
".venv\Scripts\python.exe" "scripts\run_paper.py" >> "logs\run_paper.out.log" 2>&1
echo [%date% %time%] bot exited with code %errorlevel% >> "logs\run_paper.out.log"
