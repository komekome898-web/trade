"""Cost/market constants registry with provenance (config/constants.yaml).

Every constant used for a trading judgment (a cost floor, a tick size, a fee
used in a go/no-go decision) must trace to config/constants.yaml, which
records value + unit + source_type + provenance for each one. This module
is a thin, typed loader over that file plus a guard — `require_source` —
that raises when a caller tries to use an `assumed` (unsourced, or
deprecated) constant in a judgment context without saying so explicitly.

See docs/QA_PLAN_2026-09.md §1-2 item 4 and CLAUDE.md §5 (research
discipline: no bare-value constants).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_FIELDS = ("value", "unit", "source_type")
VALID_SOURCE_TYPES = ("primary_document", "measured", "assumed")


class ConstantsError(Exception):
    """Raised on a malformed constants.yaml or an unsourced-constant use."""


class AssumedConstantError(ConstantsError):
    """Raised by require_source() for an assumed/deprecated constant."""


@dataclass(frozen=True)
class Constant:
    group: str
    name: str
    value: Any
    unit: str
    source_type: str
    source_url: str | None = None
    verified_on: str | None = None
    measured_by: str | None = None
    notes: str | None = None
    deprecated: bool = False
    reason: str | None = None

    @property
    def path(self) -> str:
        return f"{self.group}.{self.name}"

    @property
    def is_sourced(self) -> bool:
        """True if this constant traces to a primary document or a measurement."""
        return self.source_type in ("primary_document", "measured") and not self.deprecated


def _is_entry(node: Any) -> bool:
    return isinstance(node, dict) and "value" in node and "unit" in node and "source_type" in node


def load_constants(root: str | Path = ".") -> dict[str, Constant]:
    """Load config/constants.yaml into a flat {"group.name": Constant} dict.

    Raises ConstantsError if any leaf entry is missing a required field or
    carries an unrecognized source_type.
    """
    path = Path(root) / "config" / "constants.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    out: dict[str, Constant] = {}
    for group, entries in raw.items():
        if not isinstance(entries, dict):
            raise ConstantsError(f"{group}: expected a mapping of constant names, got {type(entries)!r}")
        for name, entry in entries.items():
            if not _is_entry(entry):
                raise ConstantsError(
                    f"{group}.{name}: missing one of {REQUIRED_FIELDS} — bare-value "
                    "constants are forbidden (CLAUDE.md §5 / QA_PLAN_2026-09.md §1-2.4)"
                )
            source_type = entry["source_type"]
            if source_type not in VALID_SOURCE_TYPES:
                raise ConstantsError(
                    f"{group}.{name}: invalid source_type {source_type!r}, "
                    f"expected one of {VALID_SOURCE_TYPES}"
                )
            out[f"{group}.{name}"] = Constant(
                group=group,
                name=name,
                value=entry["value"],
                unit=entry["unit"],
                source_type=source_type,
                source_url=entry.get("source_url"),
                verified_on=entry.get("verified_on"),
                measured_by=entry.get("measured_by"),
                notes=entry.get("notes"),
                deprecated=bool(entry.get("deprecated", False)),
                reason=entry.get("reason"),
            )
    return out


def require_source(name: str, constants: dict[str, Constant] | None = None, *, root: str | Path = ".") -> Constant:
    """Fetch a constant by "group.name" and raise if it is unsourced.

    Use this at the point a constant feeds a judgment (a go/no-go decision,
    a pre-registered gate, a reported cost floor) — NOT at every read. A
    constant that is `assumed` or `deprecated: true` raises
    AssumedConstantError so the caller must consciously catch it (and cite
    a reason) rather than silently building a verdict on an unsourced or
    superseded number.
    """
    table = constants if constants is not None else load_constants(root)
    if name not in table:
        raise ConstantsError(f"unknown constant {name!r} (not in config/constants.yaml)")
    c = table[name]
    if c.deprecated:
        raise AssumedConstantError(
            f"{name} is deprecated ({c.reason or 'no reason recorded'}) — "
            "do not use it in a new judgment; see its `notes` for the replacement."
        )
    if c.source_type == "assumed":
        raise AssumedConstantError(
            f"{name} is source_type=assumed (not a primary document or a "
            "measurement) — do not use it in a judgment context without "
            "re-measuring or sourcing it first."
        )
    return c
