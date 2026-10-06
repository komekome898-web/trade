"""1 本道の計算のツールと検査(L-754、作る順 1: `docs/DISCUSSIONS/2026-10-06_held_batches/ONE_ROAD_PROPOSAL.md` §4)。

- `sizing.size_per_level`: 1 段の量(BTC)。20 万円 × 70% ÷ 段数 ÷ 値段、0.001 BTC 未満切り捨て(L-745・L-746・L-756)
- `ledger.book`: 約定の列 → 平均の原価法を分数で計算(口座と突き合わせ)→ 約定ごとの表・取引ごとの表・まとめ
  (L-741・L-749・L-750・L-755・L-756。損益は 10 進の文字列)
- `check.check_outputs`: 置き場のまとめの計算し直しと、約定が 1 分足の上にあるかの検査。CLI は `scripts/road/check_outputs.py`
試験: `tests/road/`。
"""
from .check import CheckResult, StoreError, check_bars, check_outputs, check_summary, load_json, read_store, write_store
from .ledger import SUMMARY_KEYS, TRADE_KEYS, Ledger, LedgerError, book, dec_str
from .sizing import MARGIN_JPY, USE_RATIO, SizingError, size_per_level

__all__ = ["CheckResult", "Ledger", "LedgerError", "MARGIN_JPY", "SUMMARY_KEYS", "SizingError", "StoreError", "TRADE_KEYS",
           "USE_RATIO", "book", "check_bars", "check_outputs", "check_summary", "dec_str", "load_json", "read_store",
           "size_per_level", "write_store"]
