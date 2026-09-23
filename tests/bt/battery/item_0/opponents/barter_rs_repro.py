"""Minimal reproduction of 候補61 `barter-rs`'s 清算(liquidation)/注文通知(order_notice)
event models, from primary source (NOT the real crate -- barter-rs is Rust and this
venv-based battery only runs Python; per delegation doc `場面集の規則9`,
"再現" means "一次資料どおりの最小の書き直し", not "install the real package").

barter-rs itself cannot be pip-installed (Rust crate; `crates.io` API returns 403
from this proxy, re-confirmed 2026-09-23: `curl https://crates.io/api/v1/crates/barter`).
`raw.githubusercontent.com` IS reachable (re-confirmed 2026-09-23, 200), so the
field shapes below are copied verbatim (structure, not behaviour) from the real
source, fetched this round:

- `Liquidation { side, price, quantity, time }`
  https://raw.githubusercontent.com/barter-rs/barter-rs/main/barter-data/src/subscription/liquidation.rs
  (fetched 2026-09-23)
- `ApiError::OrderRejected(String)`
  https://raw.githubusercontent.com/barter-rs/barter-rs/main/barter-execution/src/error.rs
  (fetched 2026-09-23, line 95)

This is a STRUCTURAL reproduction only: it confirms the documented field/variant
shape can hold the scene's synthetic values without loss, exactly as barter-rs's own
struct declares them. It does NOT reproduce barter-rs's actual matching/dispatch
behaviour (unlike `basana_adapter.py`/`qf_lib_adapter.py`'s real event-loop runs),
because the primary source read this round did not include the surrounding
event-bus/dispatch code that would be needed for a behavioural reproduction, and that
additional read was judged out of this round's time budget (§4: 1件の実行は数分まで,
applied here to the reading budget for an uninstallable candidate).
"""
from __future__ import annotations

from dataclasses import dataclass
import datetime


@dataclass(frozen=True)
class Liquidation:
    """Field-for-field copy of barter-rs's `Liquidation` struct."""

    side: str
    price: float
    quantity: float
    time: datetime.datetime


class OrderRejected(Exception):
    """Field-for-field copy of barter-rs's `ApiError::OrderRejected(String)`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def build_liquidation_from_scene(sample: dict) -> dict:
    """Feed the scene's synthetic liquidation sample through `Liquidation` and read
    it back in the scene's own field names (ts_ns/price/qty/side), so the result is
    comparable to `Scene.expected` the same way the 5 installed adapters' `known`
    scenes are.
    """
    when = datetime.datetime.fromtimestamp(sample["ts_ns"] / 1e9, tz=datetime.timezone.utc)
    liq = Liquidation(side=sample["side"], price=sample["price"], quantity=sample["qty"], time=when)
    return {
        "ts_ns": round(liq.time.timestamp() * 1e9),
        "price": liq.price,
        "qty": liq.quantity,
        "side": liq.side,
    }


def order_notice_supported() -> bool:
    """barter-rs's `ApiError::OrderRejected(String)` exists (structural confirmation);
    raising/catching it here confirms the Python stand-in behaves like a rejection
    notice would (it does not confirm barter-rs's real dispatch wiring).
    """
    try:
        raise OrderRejected("synthetic-1")
    except OrderRejected as exc:
        return exc.reason == "synthetic-1"
