"""P2-08 control 5 — the yen-converted leading signal (PREREG 対照 5 円換算).

The leading market's close is re-expressed in JPY, close_jpy(t) = BTCUSDT
close(t) × USDJPY close(t), and the SAME momentum rule m(t) = close(t) /
close(t−k) − 1 is applied to it, so the difference against the USD-only
signal isolates the FX contribution to the signal (盲点監査). Nothing about
the execution side (bitFlyer bars, costs, funding, gaps) changes.

USDJPY (Dukascopy 1-minute BID) has no rows when the FX market is closed
(weekends, holidays) and occasional missing weekdays; those Binance minutes
take the LAST USDJPY close at or before the minute (forward fill, "直前値で
埋める"). Minutes before the first USDJPY observation get NaN (no backward
fill). The fill count is returned so it can be reported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.research.xborder_p2 import _utc_index


def jpy_close(bn_close: pd.Series, usdjpy_close: pd.Series) -> tuple[pd.Series, dict]:
    """(bn_close × USDJPY close forward-filled onto bn_close's index, fill
    report). The report counts, over the Binance minutes: ``n_minutes``,
    ``n_usdjpy_exact`` (a USDJPY bar exists at that minute), ``n_filled``
    (taken from an earlier USDJPY bar), ``n_nan`` (before the first USDJPY
    bar → NaN product), ``max_fill_age_min`` (largest forward-fill distance)
    and ``n_filled_by_year``."""
    bn_idx = _utc_index(bn_close.index)
    bn = pd.Series(np.asarray(bn_close, dtype=float), index=bn_idx)
    fx_idx = _utc_index(usdjpy_close.index)
    fx = pd.Series(np.asarray(usdjpy_close, dtype=float), index=fx_idx).dropna()
    if len(fx) == 0:
        raise ValueError("usdjpy_close has no finite values")
    # position of the last USDJPY bar at or before each Binance minute (−1 = none)
    pos = np.searchsorted(fx.index.to_numpy(), bn_idx.to_numpy(), side="right") - 1
    has = pos >= 0
    fx_at = np.full(len(bn_idx), np.nan)
    fx_at[has] = fx.to_numpy()[pos[has]]
    exact = np.zeros(len(bn_idx), dtype=bool)
    exact[has] = fx.index.to_numpy()[pos[has]] == bn_idx.to_numpy()[has]
    filled = has & ~exact
    age = np.zeros(len(bn_idx), dtype=float)
    age[has] = (bn_idx.to_numpy()[has] - fx.index.to_numpy()[pos[has]]) / np.timedelta64(1, "m")
    out = pd.Series(bn.to_numpy() * fx_at, index=bn_idx, name="close_jpy")
    years = bn_idx.year.to_numpy()
    by_year = {int(y): int((filled & (years == y)).sum()) for y in np.unique(years)}
    report = {
        "n_minutes": int(len(bn_idx)),
        "n_usdjpy_exact": int(exact.sum()),
        "n_filled": int(filled.sum()),
        "n_nan": int((~has).sum()),
        "max_fill_age_min": float(age.max()) if len(age) else 0.0,
        "n_filled_by_year": by_year,
        "usdjpy_first": str(fx.index[0]),
        "usdjpy_last": str(fx.index[-1]),
    }
    return out, report
