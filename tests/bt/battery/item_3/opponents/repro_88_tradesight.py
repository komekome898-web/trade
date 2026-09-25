"""Reproduction of survey candidate 88 `TradeSight` for the item 3 battery.

The catalogue has 88 as 未到達 (tools_catalog.tsv 88; SCAN 4672 has only the list's one-line description).
The primary source was reached through the list the survey took it from (39 = awesome-systematic-trading,
its README line 182 links https://github.com/rmbell09-lang/tradesight) and read without executing:
    https://github.com/rmbell09-lang/tradesight  commit 8b2de128b5180d05e87a51a191685298e2e888e6
    (git clone --depth 1 on 2026-09-25; log scratchpad/bt/i3_r1_scenekeeper/read/i3_r1_scenekeeper_read.log)
It is not installed (a single unknown maintainer and no package index entry to cross-check = tools survey §6-1).
The only mechanism of this battery's scenes the source has is the backtest engine's running maximum drawdown,
transcribed below; the others are in NO with the lines that show what the source has instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import Base  # noqa: E402

SRC = "https://github.com/rmbell09-lang/tradesight/blob/8b2de128b5180d05e87a51a191685298e2e888e6/"


# --- src/strategy_lab/backtest.py L80-L82 (peak = initial balance, max_drawdown = 0), L149-L164 (the running
#     maximum of (peak - equity) / peak, the peak updated before the drawdown), L467-L468 (both fields = x 100)
def max_drawdown_pct(equity):
    peak = equity[0]  # initial balance (L80-L81); the scene's first equity value is the starting balance
    mdd = 0.0
    for eq in equity:
        if eq > peak:  # L159-L160
            peak = eq
        dd = (peak - eq) / peak  # L162
        if dd > mdd:  # L163-L164
            mdd = dd
    return mdd * 100  # L467-L468


class TradeSight(Base):
    name = "opp_repro_88"
    SEARCH_AS = "read_88"
    WHAT = "候補 88 の再現(一次資料 " + SRC + " を読むだけで書き写した)。"
    NO = {
        "walk_forward": "walk_forward_validation(src/strategy_lab/backtester.py L78-L152)は行を n_folds の重ならない塊に分け、塊の中を行の割合"
                        "(train_ratio 0.7)で学習と評価に分けるだけで、日数の窓を転がす口が無い。塊は 100 行未満で拒む(L103-L104)",
        "walk_forward_eval": "同上(窓は重ならない塊の中の割合)",
        "calendar_split": "日付で Train / Val / OOS に切る口が無い(当たりは walk-forward の塊と自動化の文)",
        "block_bootstrap": "再抽出は取引の結果の 1 件ずつの復元抽出(backtester.py L162-L181 rng.choice)で、ブロックの口が無い",
        "dsr": "deflated の当たりは改善 − 多重検定の罰の差(scripts/overnight_strategy_evolution.py L1152)で、DSR の確率の式ではない",
        "dsr_returns": "同上",
        "trade_metrics": "分位は乱数の再抽出の合計の損益の分位(backtester.py L207-L210)で、1 件ごとの bp の分位・負の割合・露出あたりの口が無い",
        "run": "当たり(accounting_truth.py・verify_canonical_source.py)は配布物の同一性の確かめで、実行の記録の口ではない",
        "auto_repro": "約定の模型は乱数の揺らぎを足す(src/strategy_lab/slippage.py L68)。2 回回して比べる口は無い",
        "exit_reasons": "exit_reason は取引ごとの欄(src/trading/trade_logger.py L50・L97)で、画面は取引の表に出すだけ(src/web/dashboard.py L143)。理由ごとの集計の口が無い",
        "dashboard": "画面(src/web/dashboard.py、Flask)は取引と口座の画面で、実行の一覧と要件の 10 のタブを持たず、Chart.js を CDN から読む(L29)",
        "wiring_test": "画面の配線の試験の口が無い(同上の画面)",
    }

    def op_drawdown(self, inp):
        return {"max_dd_pct": max_drawdown_pct(inp["equity"]), "note": "backtest.py の max_drawdown と max_drawdown_pct はどちらも % (L467-L468)。額の口は無い"}


TARGET = TradeSight()
