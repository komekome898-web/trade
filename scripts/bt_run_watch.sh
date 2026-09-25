#!/bin/sh
# Watch one backtest-environment Workflow run (owner decision L-458 "案A", 2026-09-26).
# Usage: sh scripts/bt_run_watch.sh <run transcript dir> [poll seconds] [max minutes] [since-file]
#   since-file: only agent transcripts newer than this file are checked for RELAY (a resumed run keeps
#   the old transcripts of its earlier launch in the same directory).
# Exits (so the lead is woken) as soon as one of these is seen:
#   RELAY   : an agent transcript carries the harness relay "[Workflow harness — user request]"
#             (the agent then obeys a message the lead did not write; the lead must stop the run)
#   FAILED  : the journal records an agent failure
#   STALL   : no agent/journal write for 90 minutes
#   DISK    : less than 200 MB free
# Limit (honest): this script only detects. Stopping the run is a tool call the lead makes on wake.
W="$1"; P="${2:-20}"; M="${3:-480}"; SINCE="${4:-}"
[ -d "$W" ] || { echo "no such dir: $W"; exit 2; }
i=0
while [ "$i" -lt "$((M*60/P))" ]; do
  sleep "$P"; i=$((i+1))
  J="$W/journal.jsonl"
  if [ -n "$SINCE" ]; then files=$(find "$W" -maxdepth 1 -name 'agent-*.jsonl' -newer "$SINCE" 2>/dev/null); else files=$(ls "$W"/agent-*.jsonl 2>/dev/null); fi
  r=$([ -n "$files" ] && grep -l 'Workflow harness — user request' $files 2>/dev/null)
  if [ -n "$r" ]; then echo "RELAY at $(date -u):"; echo "$r"; exit 3; fi
  [ -f "$J" ] || continue
  if grep -q '"type":"failed"' "$J"; then echo "FAILED at $(date -u):"; grep '"type":"failed"' "$J" | tail -2; exit 4; fi
  now=$(date +%s); m=$(ls -t "$W"/agent-*.jsonl "$J" 2>/dev/null | head -1 | xargs stat -c %Y)
  if [ $((now-m)) -gt 5400 ]; then echo "STALL: no write for $((now-m))s at $(date -u)"; exit 5; fi
  a=$(df --output=avail -m / | tail -1)
  if [ "$a" -lt 200 ]; then echo "DISK LOW: ${a}M at $(date -u)"; exit 6; fi
done
echo "watch timeout ${M}m at $(date -u)"
