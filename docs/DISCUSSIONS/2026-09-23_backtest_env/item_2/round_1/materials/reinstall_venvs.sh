#!/bin/bash
# Item 2, round 1, table-maker: re-create the survey venvs that other roles
# removed (tests/bt/battery/item_2/opponents/RUNNABILITY.tsv says which), with
# the same versions / commits as the install records. Isolated venvs under the
# scratchpad only; only synthetic scene data is ever given to these tools.
V=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs
DL=$V/item_0/_dl
mkdir -p $DL
free_mb() { df -Pm /tmp | awk 'NR==2{print $4}'; }
step() {  # name, command...
  local n=$1; shift
  echo "=== start $(date -u +%FT%TZ) $n free=$(free_mb)MB : $*"
  local s=$(date +%s)
  ( eval "$@" ) > /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/i2_r1_shiryo_install_$n.log 2>&1 &
  local pid=$!
  while kill -0 $pid 2>/dev/null; do
    if [ "$(free_mb)" -lt 1200 ]; then kill -TERM -$pid $pid 2>/dev/null; pkill -P $pid; echo "KILLED: free space below 1200MB"; fi
    if [ $(( $(date +%s) - s )) -gt 600 ]; then kill $pid; pkill -P $pid; echo "KILLED: over 600s"; fi
    sleep 2
  done
  wait $pid; local rc=$?
  echo "=== end $(date -u +%FT%TZ) $n rc=$rc elapsed=$(( $(date +%s) - s ))s free=$(free_mb)MB"
  tail -3 /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/i2_r1_shiryo_install_$n.log | cut -c1-300
}
clone_at() {  # url dir commit
  [ -d "$2/.git" ] || git clone -q "$1" "$2" || return 1
  git -C "$2" checkout -q "$3" && git -C "$2" log -1 --format='%H %cI' && git -C "$2" rev-parse HEAD | grep -q "^$3"
}
pipvenv() {  # dir, pip args...
  local d=$1; shift
  python3.11 -m venv $d && $d/bin/pip install -q --no-cache-dir "$@"
}
# c3 / c87: item 1's table-maker re-cloned the same commits into item_1 venvs (item_1/c3_c87_reclone.log)
ln -sfn $V/item_1/c3 $V/item_0/c3 && echo "link item_0/c3 -> item_1/c3"
ln -sfn $V/item_1/c87 $V/item_0/c87 && echo "link item_0/c87 -> item_1/c87"
step backtrader  pipvenv $V/item_0/backtrader backtrader==1.9.78.123
step quantcore   pipvenv $V/item_0/quantcore quantcore==1.0.0
step fast-trade  pipvenv $V/item_0/fast-trade-r17 fast-trade==2.1.0
step rqalpha     pipvenv $V/item_0/rqalpha rqalpha==6.4.0
step lib-pybroker pipvenv $V/item_0/lib-pybroker lib-pybroker==2.0.1
step zipline     pipvenv $V/item_0/zipline-reloaded zipline-reloaded==3.1.1
step c37 "clone_at https://github.com/ThePredictiveDev/Automated-Financial-Market-Trading-System.git $DL/c37 7482b3629a1d0abe81d4431fc51e195e0534c22e && pipvenv $V/item_0/c37 $DL/c37 && $V/item_0/c37/bin/python -c 'import trading_simulator; print(trading_simulator.__file__)'"
step luczinsritter "clone_at https://github.com/Luczinsritter/event_driven_backtesting_engine.git $DL/luczinsritter 20929924806b5071dd92f9075c9bf97901e0011c && pipvenv $V/item_0/luczinsritter -r $DL/luczinsritter/requirements.txt && $V/item_0/luczinsritter/bin/pip install -q --no-cache-dir ipython && echo $DL/luczinsritter > $V/item_0/luczinsritter/lib/python3.11/site-packages/c16_src.pth && $V/item_0/luczinsritter/bin/python -c 'import backtest_engine; print(backtest_engine.__file__)'"
step c103 "uv python install 3.14.7 && rm -rf $V/item_2/c103 && uv venv -q --python 3.14.7 $V/item_2/c103 && uv pip install -q --python $V/item_2/c103/bin/python sortedcontainers==2.4.0 pydantic==2.13.5 && echo $V/item_2/src/c103/src > \$(ls -d $V/item_2/c103/lib/python3.14/site-packages)/c103_src.pth && $V/item_2/c103/bin/python -c 'import sys; print(sys.version)'"
echo "=== all done $(date -u +%FT%TZ) free=$(free_mb)MB"
