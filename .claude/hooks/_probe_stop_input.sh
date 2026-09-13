#!/bin/sh
# 調査用: Stop フックが受け取る JSON を 1 回だけ記録する。
# 「返答に関門を掛けられるか」を断定せず実測するため(2026-09-13)。
mkdir -p /tmp/hookprobe
cat > /tmp/hookprobe/stop_input.json
exit 0
