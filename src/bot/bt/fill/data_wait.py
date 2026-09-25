"""Data this environment does not have, written down instead of substituted.

REQUIREMENTS C2-12 / delegation section 2 (item 2 row): the JPX board and tick
data were not found in this environment. The queue tiers (5, 6) need a
displayed book; when a run asks for one and has none, the venue refuses
(`DataUnavailableError`) instead of filling from bars. `DATA_WAIT` lists the
layers known to be waiting, with how their absence was checked, so a report
can list them separately from what passed (`data_wait_report`).
"""
from __future__ import annotations

from dataclasses import dataclass

from bot.bt.orders.errors import ExecutionModelError


@dataclass(frozen=True)
class DataWait:
    venue: str
    layer: str  # "book" | "tick"
    checked: str  # where and how the absence was checked (CLAUDE.md section 5.2)


DATA_WAIT: tuple[DataWait, ...] = (
    DataWait("jpx_equity", "book",
             "この環境: リードが 2026-09-23 に `ls backtest_data | grep -iE \"jpx|n225|topix|225|kabu|tick\"` で確かめた。"
             "JPX 関係は 1 分足・日足・ETF・日報のフォルダで、audit_fetch_JPX_tick_20260906/ は README.md と HTML 2 本だけ。"
             "オーナー PC は未確認。"),
    DataWait("jpx_equity", "tick",
             "この環境: 同上(板と同じ確認)。オーナー PC は未確認。"),
)


class DataUnavailableError(ExecutionModelError):
    """The fill model needs a data layer the run does not have."""

    def __init__(self, venue: str, layer: str, what: str) -> None:
        self.venue, self.layer = venue, layer
        waits = [w for w in DATA_WAIT if w.venue == venue and w.layer == layer]
        note = f" -- data wait (データ待ち): {waits[0].checked}" if waits else ""
        super().__init__(f"{what}: the run has no {layer} data for venue {venue!r}; the model does not "
                         f"substitute another layer (bars) for it{note}")


def data_wait_report() -> list[dict[str, str]]:
    """The waiting layers, for a report's separate section."""
    return [{"venue": w.venue, "layer": w.layer, "checked": w.checked} for w in DATA_WAIT]
