#!/bin/bash
# Item 0, round 3, materials person: one more attempt to install the survey
# tool whose venv is missing (finmarketpy), from the wheel already fetched and
# checked by the scene keeper, into its isolated scratchpad venv, with a disk
# guard (the disk is shared): pip is killed when free space on / falls below
# 150 MB, and the partial venv and the pip temp dirs this run created are removed.
# Usage (from the repo root): bash docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_3/materials/finmarketpy_attempt.sh
set -u
M=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_3/materials
V=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_0
B=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
LOG=$M/logs/finmarketpy_attempt.log
PIPOUT=$B/item0_r3_materials_finmarketpy_pip.out
MARK=$B/item0_r3_materials_finmarketpy.mark
: > "$LOG"
touch "$MARK"
free() { df -m / | tail -1 | awk '{print $4}'; }
echo "=== $(date -u +%FT%TZ) start; free $(free) MB" >> "$LOG"
python3 -m venv "$V/finmarketpy"; echo "venv rc=$?" >> "$LOG"
START=$(date +%s)
"$V/finmarketpy/bin/pip" install --no-cache-dir "$V/_dl/finmarketpy/finmarketpy-0.11.19-py3-none-any.whl" "plotly==5.24.1" "pandas<3" > "$PIPOUT" 2>&1 &
PID=$!
MINFREE=999999
while kill -0 $PID 2>/dev/null; do
  F=$(free); [ "$F" -lt "$MINFREE" ] && MINFREE=$F
  if [ "$F" -lt 150 ]; then echo "$(date -u +%FT%TZ) free ${F}MB < 150MB: stopping pip" >> "$LOG"; kill $PID; break; fi
  if [ $(( $(date +%s) - START )) -gt 300 ]; then echo "$(date -u +%FT%TZ) over 300 s: stopping pip" >> "$LOG"; kill $PID; break; fi
  sleep 1
done
wait $PID; RC=$?
echo "pip rc=$RC elapsed=$(( $(date +%s) - START ))s min_free=${MINFREE}MB" >> "$LOG"
grep -iE "error|Successfully installed" "$PIPOUT" | tail -5 >> "$LOG"
if [ "$RC" -ne 0 ]; then
  rm -rf "$V/finmarketpy"
  N=$(find /tmp -maxdepth 1 -name 'pip-*' -newer "$MARK" | wc -l)
  find /tmp -maxdepth 1 -name 'pip-*' -newer "$MARK" -exec rm -rf {} +
  echo "$(date -u +%FT%TZ) removed partial venv and this run's $N pip temp dirs; free $(free) MB" >> "$LOG"
fi
echo "=== $(date -u +%FT%TZ) end; free $(free) MB" >> "$LOG"
cat "$LOG"
