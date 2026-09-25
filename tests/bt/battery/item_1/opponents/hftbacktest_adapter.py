"""hftbacktest (catalogue 23, SCAN 6906 行; installed by item 0 in venv item_0/hftbacktest).

Read in the installed code:
- file readers are per-venue converters with FIXED input shapes
  (hftbacktest/data/utils/tardis.py:56 `convert` = Tardis trades / incremental_book_L2 CSV,
  binancefutures.py / bybit.py / databento.py / hyperliquid.py / mexc.py = their own feeds);
  there is no argument for a column map, a time unit or a time zone;
- hftbacktest/data/validation.py: `correct_local_timestamp` (:16), `correct_event_order` (:54)
  and `validate_event_order` (:139) work on the tool's own event array (exch_ts / local_ts
  order) -- no duplicate / gap / generation report, and they need a converted array;
- one event-driven simulation path (tick by tick); no vector path, no bars from trades,
  no corporate actions.
"""
from __future__ import annotations

from _i1_base import ReasonTarget

import hftbacktest  # noqa: F401
from hftbacktest.data.utils import tardis  # noqa: F401


class T(ReasonTarget):
    name = "opp_hftbacktest"
    reasons = {
        "load": "hftbacktest のファイルの読み口は取引所・業者ごとに形が固定の変換器(tardis.convert は Tardis の trades / incremental_book_L2 の CSV)で、列の対応・時刻の単位・時間帯の引数が無い。"
                "検査(data/validation.py の correct_event_order・validate_event_order)は変換後の自前の事象の配列にだけ掛かる",
        "jpx": "hftbacktest に分割・併合・コード変更の調整と日付ごとの銘柄集合の口が無い(ティックと板の模擬器)",
        "vector_vs_event": "hftbacktest の模擬はティックごとの事象駆動の 1 経路だけで、近道(ベクトル化)の経路も約定から足を作る口も無い",
    }


TARGET = T()
