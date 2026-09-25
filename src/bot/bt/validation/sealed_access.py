"""Sealed windows (item 3, old item 7: 「封印区間は `load_sealed` の 4 門を通らない限り読めない」).

Two doors, and no third:

read_sealed(path, unit=, token=, root=)
    the ONLY way to the sealed rows: `bot.research.sealed.load_sealed`
    itself (its four gates: env PHASE2_FINAL_EVAL == unit, the owner's
    UNSEAL_APPROVED file, the confirmation token, and the audit record =
    the 4th gate in scripts/_research_audit_gate.py). The gates are called,
    not re-implemented; a refusal becomes `SealedRefused`.

read_table(root, path, time_column=, range_ns=None)
    the ordinary read of a table for a run. The path must pass the data
    layer's allow-list (bot.bt.data.allowlist), and a file a seal record
    covers (by path or by bytes, bot.bt.data.allowlist.SealRegistry) is read
    only with a `range_ns` [lo, hi) that ends at or before the seal's cutoff,
    and only when every kept row's value in the seal's time column is
    before the cutoff. Without such a range the read is refused -- this
    door never returns a sealed row.
"""
from __future__ import annotations

import hashlib
import io
from typing import Optional

import pandas as pd

from ..data.allowlist import DEFAULT_ALLOWLIST, AllowList, SealRegistry, seal_time_ns
from ..data.errors import DataError
from .errors import SealedRefused, ValidationError


def read_sealed(path: str, *, unit: str, token: str, root: str) -> pd.DataFrame:
    from bot.research.sealed import SealedDataError, load_sealed
    try:
        return load_sealed(path, unit, token, root=root)
    except SealedDataError as exc:
        raise SealedRefused(str(exc)) from None


def read_table(root: str, path: str, *, time_column: str, range_ns: Optional[tuple[int, int]] = None,
               allowlist: Optional[AllowList] = None) -> pd.DataFrame:
    allow = DEFAULT_ALLOWLIST if allowlist is None else allowlist
    if type(time_column) is not str or not time_column:
        raise ValidationError("time_column must be a non-empty str")
    try:
        cp = allow.check(root, path)
        with open(cp.real, "rb") as fh:
            raw = fh.read()
        seals = SealRegistry(root)
        ent = seals.match(cp.real, len(raw), hashlib.sha256(raw).hexdigest())
        if ent is not None:
            seals.check_range(ent, path, range_ns)
    except DataError as exc:
        raise SealedRefused(f"{type(exc).__name__}: {exc}") from None
    df = pd.read_csv(io.BytesIO(raw))
    if time_column not in df.columns:
        raise ValidationError(f"{path!r} has no column {time_column!r} (columns {list(df.columns)})")
    try:
        if range_ns is not None:
            lo, hi = range_ns
            keep = [lo <= seal_time_ns(v) < hi for v in df[time_column].astype(str)]
            df = df.loc[keep].reset_index(drop=True)
        if ent is not None:
            if ent.time_column not in df.columns:
                raise SealedRefused(f"{path!r} is sealed on column {ent.time_column!r}, which the table does not have")
            for v in df[ent.time_column].astype(str):
                if seal_time_ns(v) >= ent.cutoff_ns:
                    raise SealedRefused(f"{path!r}: a row at {v} is at or after the seal cutoff (unit {ent.unit})")
    except DataError as exc:
        raise SealedRefused(f"{type(exc).__name__}: {exc}") from None
    return df
