#!/bin/bash
# Item 2, round 1, table-maker: one at a time: re-create, run twice, remove (part 3; the disk had ~1.5GB free) that other roles
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
R=/home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/round_1/materials
runrm() {  # target, dir to remove afterwards
  $R/run_all.sh "$1" >> $R/run_log_part3.tsv 2>&1; echo "ran $1 (run_log_part3.tsv)"; rm -rf $2; echo "removed $2 free=$(free_mb)MB"
}
step zipline pipvenv $V/item_0/zipline-reloaded zipline-reloaded==3.1.1 && runrm opp_zipline_reloaded $V/item_0/zipline-reloaded
step c37 "clone_at https://github.com/ThePredictiveDev/Automated-Financial-Market-Trading-System.git $DL/c37 7482b3629a1d0abe81d4431fc51e195e0534c22e && pipvenv $V/item_0/c37 $DL/c37 && $V/item_0/c37/bin/python -c 'import trading_simulator; print(trading_simulator.__file__)'" && runrm opp_predictivedev_tradesim "$V/item_0/c37 $DL/c37"
step luczinsritter "clone_at https://github.com/Luczinsritter/event_driven_backtesting_engine.git $DL/luczinsritter 20929924806b5071dd92f9075c9bf97901e0011c && pipvenv $V/item_0/luczinsritter -r $DL/luczinsritter/requirements.txt && $V/item_0/luczinsritter/bin/pip install -q --no-cache-dir ipython && echo $DL/luczinsritter > $V/item_0/luczinsritter/lib/python3.11/site-packages/c16_src.pth && $V/item_0/luczinsritter/bin/python -c 'import backtest_engine; print(backtest_engine.__file__)'" && runrm opp_luczinsritter $V/item_0/luczinsritter
step c103 "uv python install 3.14.7 && rm -rf $V/item_2/c103 && uv venv -q --python 3.14.7 $V/item_2/c103 && uv pip install -q --python $V/item_2/c103/bin/python sortedcontainers==2.4.0 pydantic==2.13.5 && echo $V/item_2/src/c103/src > \$(ls -d $V/item_2/c103/lib/python3.14/site-packages)/c103_src.pth && $V/item_2/c103/bin/python -c 'import order_book_simulator; print(order_book_simulator.__file__)'" && $R/run_all.sh opp_isaaccheng_obsim >> $R/run_log_part3.tsv 2>&1
step c65 "pipvenv $V/item_0/c65 'aiostream>=0.3.1' 'matplotlib>2.2' 'numpy>=1.11.0' 'pandas>=0.24.1' 'perspective-python>=0.4.8' 'pybind11>=2' 'temporal-cache>=0.1.2' 'tornado>=6.0' 'traitlets>=4.3.3' && cd /tmp && PYTHONPATH=$V/item_2/src/c65 $V/item_0/c65/bin/python -c 'import aat, aat.binding; print(aat.__file__)'" && runrm opp_aat $V/item_0/c65
step c35 "clone_at https://github.com/thirupathikannan-ai/Optimal-Execution-And-Market-Impact-Simulator-.git $V/item_0/c35_run 794fa647f8c8168a6f30338ea0987d26124d6101 && cd $V/item_0/c35_run && mkdir -p src && for f in src\ *.py; do mv \"\$f\" \"src/\${f#src }\"; done && ls src && python3 -m venv --system-site-packages .venv && .venv/bin/pip install -q --no-cache-dir matplotlib && echo $V/item_0/c35_run > .venv/lib/python3.11/site-packages/c35_src.pth && cd /tmp && $V/item_0/c35_run/.venv/bin/python -c 'from src.execution import execute_order; print(execute_order)'" && runrm opp_thirupathikannan_execsim $V/item_0/c35_run
step c107 "clone_at https://github.com/Skelf-Research/sigc.git $DL/c107 aa5f616f && cd $DL/c107 && cargo build -p sigc --target-dir $V/item_0/_cargo_target107 && python3.11 -m venv $V/item_0/c107 && cp $V/item_0/_cargo_target107/debug/sigc $V/item_0/c107/bin/sigc && $V/item_0/c107/bin/sigc --help | head -3" && runrm opp_sigc "$V/item_0/c107 $V/item_0/_cargo_target107"
rm -rf $V/item_0/_cargo_target107 $DL/c107
echo "=== all done $(date -u +%FT%TZ) free=$(free_mb)MB"
