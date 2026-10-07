"""1 本道の計算のツールと検査(L-754、作る順 1: `docs/DISCUSSIONS/2026-10-06_held_batches/ONE_ROAD_PROPOSAL.md` §4)と、
道の記録の形(L-766・L-767: `docs/DISCUSSIONS/2026-10-06_held_batches/RECORD_FORM_L766.md`)。

- `sizing.size_per_level`: 1 段の量(BTC)。20 万円 × 70% ÷ 段数 ÷ 値段、0.001 BTC 未満切り捨て(L-745・L-746・L-756)。
  `sizing.size_detail` は切り捨て前の量も返す
- `ledger.book`: 約定の列 → 平均の原価法を分数で計算(口座と突き合わせ)→ 約定ごとの表・取引ごとの表・まとめ
  (L-741・L-749・L-750・L-755・L-756。損益は 10 進の文字列。使った USDJPY の値と相場の時刻も約定・取引の行に出す)
- `strategy.RoadStrategy`: 道の戦略の土台。合図(`signal_start`・`signal_end`)と注文(`place`: 量は土台が決める)を受け、
  合図の発生・消失、注文の量の計算に使った値と注文の一生を記録する
- `tables`: 道の記録の表(signals・orders・fills・fx・ledger_fills・trades・summary と SCHEMA.json)を書く・読む。
  道の走らせ(`bot.bt.pipeline`)が走らせの置き場の `road/` に書く
- `check.check_outputs`: 置き場の検査。表の形の置き場は (i)〜(v)、作る順 1 の置き場は (a)(b)。
  CLI は `scripts/road/check_outputs.py`
試験: `tests/road/`。
"""
from .check import (CheckResult, StoreError, check_bars, check_outputs, check_summary, check_tables, load_json,
                    read_store, write_store)
from .ledger import SUMMARY_KEYS, TRADE_KEYS, Ledger, LedgerError, book, dec_str
from .sizing import MARGIN_JPY, USE_RATIO, SizingError, size_detail, size_per_level
from .strategy import DATA_END, NO_SIGNAL, ZERO_QTY_STATE, RoadStrategy, RoadStrategyError
from .tables import ROAD_DIR, SCHEMA, TableError, write_road_store

__all__ = ["CheckResult", "DATA_END", "Ledger", "LedgerError", "MARGIN_JPY", "NO_SIGNAL", "ROAD_DIR", "RoadStrategy",
           "RoadStrategyError", "SCHEMA", "SUMMARY_KEYS", "SizingError", "StoreError", "TRADE_KEYS", "TableError",
           "USE_RATIO", "ZERO_QTY_STATE", "book", "check_bars", "check_outputs", "check_summary", "check_tables",
           "dec_str", "load_json", "read_store", "size_detail", "size_per_level", "write_road_store", "write_store"]
