"""Survey candidate 75 `Freqtrade` for the item 3 battery.

Install: venv item_3/freqtrade, freqtrade==2026.8 from PyPI (the same version item 0 inspected,
tests/bt/battery/item_0/survey_results/attempts/75.log); pre-install check and install log
venvs/item_3/logs/i3_r1_scenekeeper_install_freqtrade.log (item 0's venv had been removed for disk).
No exchange is contacted: only pure functions are called --
optimize.backtest_caching.get_strategy_run_id (the backtest's run id),
data.metrics.calculate_max_drawdown_from_balance, optimize.optimize_reports.generate_tag_metrics.
"""
from __future__ import annotations

import datetime as D
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import Base  # noqa: E402

import pandas as pd  # noqa: E402
from freqtrade.data.metrics import calculate_max_drawdown_from_balance  # noqa: E402
from freqtrade.optimize.backtest_caching import get_strategy_run_id  # noqa: E402
from freqtrade.optimize.optimize_reports.optimize_reports import generate_tag_metrics  # noqa: E402

NS = 1_000_000_000

# user code: the fixed run's strategy as a freqtrade strategy file (the legs come from the config)
STRATEGY_SRC = '''from freqtrade.strategy import IStrategy


class I3Fixed(IStrategy):
    """Item 3 battery: enter/exit at the legs given in config["i3"]["strategy"]["legs"]."""
    timeframe = "1m"
    minimal_roi = {"0": 100.0}
    stoploss = -0.99

    def populate_indicators(self, dataframe, metadata):
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        return dataframe
'''


class Freqtrade(Base):
    name = "opp_freqtrade"
    WHAT = "freqtrade は足の戦略の bot とそのバックテスト(OHLCV の足と取引所の接続が前提)。"
    NO = {
        "calendar_split": "日付で Train / Val / OOS に切る口が無い(backtesting の --timerange は 1 区間を選ぶだけ。当たりは tensorboard の記録)",
        "walk_forward": "walk-forward の口が無い(当たりは強化学習の模型と銘柄の選別の窓)",
        "purged_split": "当たり 11 ファイルは freqai の学習データの「purge_old_models」などの掃除で、ラベルの重なりで学習の行を除く口ではない",
        "run": "バックテストの結果の記録(optimize_reports/bt_storage.py の metadata)に git の SHA・データの sha256・種の欄が無い。"
               "足と取引所の設定の無い成行の約定の列(この要求の data)を読む口も無い",
        "auto_repro": "2 回回して比べる口が無い(当たりは freqai の乱数の種の設定)",
        "trade_metrics": "1 件ごとの損益の割合は取引の表にあるが、分位・負の割合・露出あたりを出す口が無い(当たりは trade_model.py と freqtradebot.py の"
                         "約定の割合の欄)",
        "fill_metrics": "当たりは約定の待ちの処理(freqtradebot.py)で、与えた注文と約定から約定率・取り逃しを出す口が無い",
        "cost_breakdown": "取引ごとの fee_open / fee_close と funding_fees は持つ(persistence/trade_model.py)が、maker / taker を分けた内訳と"
                          "スプレッドの費用の口が無い",
        "dashboard": "画面(freqUI)は別配布で、rpc/api_server/web_ui.py は組み立て済みの UI を配るだけ(この配布物に UI の本体は無い)。"
                     "バックテストの実行の一覧と項目別タブを起こせない",
    }

    def op_run_ids(self, inp):
        from freqtrade.resolvers import StrategyResolver  # noqa: F401  (import check only)
        sdir = os.path.join(inp["root"], "strategies")
        os.makedirs(sdir, exist_ok=True)
        spath = os.path.join(sdir, "i3_fixed.py")
        with open(spath, "w", encoding="utf-8") as fh:
            fh.write(STRATEGY_SRC)
        import importlib.util
        spec = importlib.util.spec_from_file_location("i3_fixed", spath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ids = []
        for run, pause in zip(inp["runs"], inp["sleep_before_s"]):
            time.sleep(pause)
            config = {"strategy": "I3Fixed", "timeframe": "1m", "stake_currency": "JPY",
                      "datadir": os.path.dirname(os.path.join(inp["root"], run["data"][0])),
                      "exchange": {"name": "bitflyer", "pair_whitelist": ["BTC/JPY"]},
                      "i3": run["config"]}  # the request's config as the strategy's own section, key order kept
            st = mod.I3Fixed(config)
            st.__file__ = spath
            ids.append(get_strategy_run_id(st))
        return {"ids": ids, "note": "設定に種の口は無い(種は設定に入らない)。データは datadir(置き場の場所)だけが設定に入る"}

    def op_drawdown(self, inp):
        df = pd.DataFrame({"date": pd.to_datetime(inp["t_ns"], unit="ns", utc=True), "total_quote": inp["equity"]})
        a = calculate_max_drawdown_from_balance(df, date_col="date", balance_col="total_quote", relative=False)
        r = calculate_max_drawdown_from_balance(df, date_col="date", balance_col="total_quote", relative=True)
        return {"max_dd_abs": float(a.drawdown_abs), "max_dd_pct": float(r.relative_account_drawdown) * 100.0}

    def op_exit_reasons(self, inp):
        t0 = D.datetime(2026, 1, 1, tzinfo=D.timezone.utc)
        df = pd.DataFrame({"exit_reason": [t["reason"] for t in inp["trades"]],
                           "profit_abs": [t["pnl"] for t in inp["trades"]],
                           "profit_ratio": [0.0] * len(inp["trades"]),     # not stated by the request; not read back
                           "trade_duration": [0] * len(inp["trades"])})    # not stated by the request; not read back
        rows = generate_tag_metrics("exit_reason", 1000.0, df, t0, t0 + D.timedelta(days=1))
        return {"by_reason": {r["key"]: {"n": int(r["trades"]), "pnl": float(r["profit_total_abs"])}
                              for r in rows if r["key"] != "TOTAL"},
                "note": "profit_ratio と trade_duration は要求に無いので 0 を渡した(読み戻すのは件数と損益だけ)"}


TARGET = Freqtrade()
