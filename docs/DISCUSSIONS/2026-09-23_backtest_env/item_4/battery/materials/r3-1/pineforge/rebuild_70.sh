#!/bin/sh
set -u
LOG=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_2/logs/i4_r3-1_scenekeeper_rebuild_70.log
{
echo "=== $(date -u +%FT%TZ) df before"; df -m / | tail -1
echo "=== $(date -u +%FT%TZ) git clone --depth 1 https://github.com/pineforge-4pass/pineforge-engine.git /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_2/src/c70"
rm -rf /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_2/src/c70
git clone --depth 1 https://github.com/pineforge-4pass/pineforge-engine.git /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_2/src/c70; echo rc=$?
cd /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_2/src/c70 && git log -1 --format='%H %cI %an'; du -sh .
echo "=== $(date -u +%FT%TZ) df after clone"; df -m / | tail -1
echo "=== $(date -u +%FT%TZ) cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DPINEFORGE_BUILD_TESTS=OFF && cmake --build build -j4"
timeout 600 sh -c 'cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DPINEFORGE_BUILD_TESTS=OFF > /dev/null && cmake --build build -j4 2>&1 | tail -5'; echo rc=$?
ls build build/lib
echo "=== $(date -u +%FT%TZ) df after build"; df -m / | tail -1
} > $LOG 2>&1
