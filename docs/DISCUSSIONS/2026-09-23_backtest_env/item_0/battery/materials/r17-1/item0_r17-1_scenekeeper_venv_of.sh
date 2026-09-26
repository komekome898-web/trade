S=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
V=$S/venvs/item_0
V5F=/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/v5f
py_of() {
  base=${1%%@*}
  case "$base" in
    current_impl|new_impl|mutant|repro_*) echo python3 ;;
    opp_basana) echo $V/basana/bin/python ;; opp_ziplime) echo $V/ziplime/bin/python ;; opp_zipline_reloaded) echo $V/zipline-reloaded/bin/python ;;
    opp_lib_pybroker) echo $V/lib-pybroker/bin/python ;; opp_qf_lib) echo $V/qf-lib/bin/python ;; opp_backtrader) echo $V/backtrader/bin/python ;;
    opp_hftbacktest) echo $V/hftbacktest/bin/python ;; opp_rqalpha) echo $V/rqalpha/bin/python ;; opp_pybotters) echo $V/pybotters/bin/python ;;
    opp_backtesting) echo $V/backtesting/bin/python ;; opp_qstrader) echo $V/qstrader/bin/python ;; opp_quantcore) echo $V/quantcore/bin/python ;;
    opp_quanttrader) echo $V/quanttrader/bin/python ;; opp_pyalgotrade) echo $V/pyalgotrade/bin/python ;; opp_freqtrade) echo $V/freqtrade/bin/python ;;
    opp_vnpy) echo $V/vnpy/bin/python ;; opp_finmarketpy) echo $V/finmarketpy/bin/python ;; opp_luczinsritter) echo $V/luczinsritter/bin/python ;;
    opp_mihircoding_lob) echo $V/c98/bin/python ;; opp_nickgardi_orderbooksim) echo $V/c99/bin/python ;; opp_daniyalmlk_slippage) echo $V/c105/bin/python ;;
    opp_akurkar07_orderbook) echo $V/c101/bin/python ;; opp_3yit_lob) echo $V/c102/bin/python ;; opp_jxm35_lob) echo $V/c104/bin/python ;;
    opp_pysystemtrade) echo $V/c3/bin/python ;; opp_predictivedev_tradesim) echo $V/c37/bin/python ;; opp_sarthak_execsim) echo $V/c33/bin/python ;;
    opp_sigc) echo $V/c107/bin/python ;; opp_homerun) echo $V/c91/bin/python ;; opp_aat) echo $V/c65/bin/python ;; opp_gobacktest) echo $V/c69/bin/python ;;
    opp_pineforge) echo $V/c70/bin/python ;; opp_barter) echo $V/c61/bin/python ;; opp_pytrendfollow) echo $V/c87/bin/python ;;
    opp_isaaccheng_obsim) echo $V/c103/bin/python ;; opp_fast_trade) echo $V5F/bin/python ;; opp_thirupathikannan_execsim) echo $V/c35_run/.venv/bin/python ;;
    *) echo UNKNOWN ;;
  esac
}
