"""JPX individual stocks: split / reverse split / code change adjustment,
and the point-in-time listed universe (no survivorship bias).

Inputs are plain data (the layer does not invent a corporate-action table):

  bars      [{"code", "date" (YYYY-MM-DD), "open", "high", "low", "close",
              "volume"}, ...]  -- daily bars as traded (unadjusted)
  actions   [{"code", "type": "split", "ex_date", "ratio"},          r > 0:
                 1 share becomes r (prices before ex_date x 1/r, volume x r)
             {"code", "type": "reverse_split", "ex_date", "ratio"},  r > 0:
                 r shares become 1 (prices before ex_date x r, volume x 1/r)
             {"code", "type": "code_change", "ex_date", "new_code"}] the
                 same company trades under new_code from ex_date on
  listings  [{"code", "listed", "delisted" (the first day it is no longer
              listed; null = still listed)}]  -- `code` is the code on the
              listing date

`adjust_daily(bars, actions, listings, as_of)` -- backward adjustment AS
KNOWN ON `as_of`: only actions with ex_date <= as_of apply, only bars dated
<= as_of are returned (no look-ahead: an announced-later split never
reaches back). Each company is returned under its code on `as_of` (its last
code, if it was delisted before), with the bars it traded under every
earlier code joined in date order. Delisted companies are returned too.
Values are computed exactly (fractions) and made floats once at the end.

`Universe(listings, actions).on(date)` / `universe(...)` -- the codes listed
on a date: listed <= date < delisted, each under the code it had that day.
A company that is delisted later is still in the universe before its
delisting (survivorship), one listed later is not in it before its listing.

Inconsistent inputs are refused (`CorporateActionError`): two bars for one
code and date, a bar under a code the company did not have that day, a bar
outside its listing, an action for an unknown code, two code changes of one
company on one day, a non-positive ratio, a malformed date.

Data (CLAUDE.md section 5.2, "無い・取れない"): in this environment
`ls backtest_data | grep -iE "split|action|delist|corporate|listing"`
(2026-09-25) lists no folder named for individual-stock corporate actions
or listings: the hits are audit_fetch_1306_split_20260906 (named for an ETF
1306 split audit; its content was not examined here), one o3c_* research
intermediate, and names matching "action" inside "transactions" /
"reaction". Only folder names were searched; the owner's PC is not checked.
This module is exercised with synthetic inputs only.
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal
from fractions import Fraction
from typing import Any, Iterable, Mapping, Optional

from .errors import CorporateActionError

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PRICE = ("open", "high", "low", "close")


def _date(value: Any, where: str) -> str:
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value.isoformat()
    if type(value) is not str or not _DATE.match(value):
        raise CorporateActionError(f"{where}: {value!r} is not a YYYY-MM-DD date")
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise CorporateActionError(f"{where}: {value!r}: {exc}") from None
    return value


def _code(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise CorporateActionError(f"{where}: code must be a non-empty str, got {value!r}")
    return value


def _exact(value: Any, where: str) -> Fraction:
    t = type(value)
    try:
        if t is bool:
            raise TypeError
        if t is int or t is Fraction:
            return Fraction(value)
        if t is float:
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError
            return Fraction(value)  # the value the float holds
        if t is str or t is Decimal:
            return Fraction(Decimal(value.strip() if t is str else value))
    except (TypeError, ValueError, ArithmeticError):
        pass
    raise CorporateActionError(f"{where}: {value!r} is not a finite number")


class _Company:
    def __init__(self, first_code: str) -> None:
        self.first_code = first_code
        self.changes: list[tuple[str, str]] = []  # (ex_date, new_code), sorted

    def code_on(self, day: str, known_on: Optional[str] = None) -> str:
        code = self.first_code
        for ex, new in self.changes:
            if ex <= day and (known_on is None or ex <= known_on):
                code = new
        return code

    def codes(self) -> set[str]:
        return {self.first_code, *(n for _, n in self.changes)}


class _Registry:
    """Companies built from listings and code changes."""

    def __init__(self, listings: Iterable[Mapping], actions: Iterable[Mapping], bar_codes: Iterable[str] = ()) -> None:
        self.listings: dict[str, tuple[str, Optional[str]]] = {}
        for i, l in enumerate(listings or ()):
            code = _code(l.get("code"), f"listings[{i}]")
            listed = _date(l.get("listed"), f"listings[{i}].listed")
            dl = l.get("delisted")
            delisted = None if dl is None else _date(dl, f"listings[{i}].delisted")
            if delisted is not None and delisted <= listed:
                raise CorporateActionError(f"listings[{i}]: delisted {delisted} is not after listed {listed}")
            if code in self.listings:
                raise CorporateActionError(f"listings: code {code!r} listed twice")
            self.listings[code] = (listed, delisted)
        self.splits: list[tuple[str, str, Fraction, Fraction]] = []  # (code, ex, price factor, volume factor)
        changes: list[tuple[str, str, str]] = []
        for i, a in enumerate(actions or ()):
            where = f"actions[{i}]"
            if not isinstance(a, Mapping):
                raise CorporateActionError(f"{where} must be a mapping")
            typ = a.get("type")
            code = _code(a.get("code"), where)
            ex = _date(a.get("ex_date"), f"{where}.ex_date")
            if typ in ("split", "reverse_split"):
                r = _exact(a.get("ratio"), f"{where}.ratio")
                if r <= 0:
                    raise CorporateActionError(f"{where}.ratio must be > 0, got {a.get('ratio')!r}")
                pf, vf = (1 / r, r) if typ == "split" else (r, 1 / r)
                self.splits.append((code, ex, pf, vf))
            elif typ == "code_change":
                new = _code(a.get("new_code"), f"{where}.new_code")
                if new == code:
                    raise CorporateActionError(f"{where}: new_code equals code {code!r}")
                changes.append((ex, code, new))
            else:
                raise CorporateActionError(f"{where}.type must be split / reverse_split / code_change, got {typ!r}")
        # companies: chain code changes in date order
        self.companies: list[_Company] = []
        by_code: dict[str, _Company] = {}
        # a company is known from its listing or from its bars (under its first code);
        # an action names a known company's code, never creates one
        firsts = set(self.listings) | set(bar_codes)
        targets = {n for _, _, n in changes}
        for code in sorted(firsts - targets):
            comp = _Company(code)
            self.companies.append(comp)
            by_code[code] = comp
        for ex, old, new in sorted(changes):
            comp = by_code.get(old)
            if comp is None:
                raise CorporateActionError(f"code_change {old!r} -> {new!r} on {ex}: {old!r} is not a known company's code")
            if comp.changes and comp.changes[-1][0] == ex:
                raise CorporateActionError(f"two code changes of one company on {ex}")
            if comp.changes and comp.changes[-1][0] > ex:
                raise CorporateActionError(f"code changes of {comp.first_code!r} are out of order")
            if comp.code_on(ex) != old:
                raise CorporateActionError(f"code_change {old!r} -> {new!r} on {ex}: the company is {comp.code_on(ex)!r} then")
            if new in by_code and by_code[new] is not comp:
                raise CorporateActionError(f"code_change to {new!r} on {ex}: {new!r} is another company's code")
            comp.changes.append((ex, new))
            by_code[new] = comp
        for code in self.listings:
            if code in targets and code not in {c.first_code for c in self.companies}:
                raise CorporateActionError(f"listing under {code!r}, which is the new code of a code change; list the company under its code on its listing date")
        self.by_code = by_code

    def owner(self, code: str, day: str, where: str) -> _Company:
        """The company that traded under `code` on `day`."""
        hits = [c for c in self.companies if c.code_on(day) == code]
        if len(hits) != 1:
            raise CorporateActionError(f"{where}: no company traded under {code!r} on {day}" if not hits
                                       else f"{where}: two companies under {code!r} on {day}")
        return hits[0]

    def listing(self, comp: _Company) -> Optional[tuple[str, Optional[str]]]:
        return self.listings.get(comp.first_code)


def adjust_daily(bars: Iterable[Mapping], actions: Iterable[Mapping], listings: Optional[Iterable[Mapping]],
                 as_of: Any) -> dict[str, list[dict]]:
    as_of = _date(as_of, "as_of")
    bars = list(bars or ())
    parsed = []
    for i, b in enumerate(bars):
        if not isinstance(b, Mapping):
            raise CorporateActionError(f"bars[{i}] must be a mapping")
        code = _code(b.get("code"), f"bars[{i}]")
        day = _date(b.get("date"), f"bars[{i}].date")
        vals = {k: _exact(b.get(k), f"bars[{i}].{k}") for k in (*_PRICE, "volume")}
        parsed.append((code, day, vals))
    reg = _Registry(listings, actions, {c for c, _, _ in parsed})
    seen: set = set()
    per: dict[int, list] = {}
    for i, (code, day, vals) in enumerate(parsed):
        if (code, day) in seen:
            raise CorporateActionError(f"bars[{i}]: a second bar for {code!r} on {day}")
        seen.add((code, day))
        if day > as_of:
            continue
        comp = reg.owner(code, day, f"bars[{i}]")
        lst = reg.listing(comp)
        if lst is not None and (day < lst[0] or (lst[1] is not None and day >= lst[1])):
            raise CorporateActionError(f"bars[{i}]: {code!r} on {day} is outside its listing {lst}")
        per.setdefault(id(comp), [comp, []])[1].append((day, code, vals))
    splits_by_comp: dict[int, list] = {}
    for code, ex, pf, vf in reg.splits:
        if ex > as_of:
            continue  # not known on as_of
        comp = None
        for day in (ex, (dt.date.fromisoformat(ex) - dt.timedelta(days=1)).isoformat()):
            hits = [c for c in reg.companies if c.code_on(day) == code]
            if len(hits) == 1:
                comp = hits[0]
                break
        if comp is None:
            raise CorporateActionError(f"split / reverse split of {code!r} on {ex}: no company has that code then")
        splits_by_comp.setdefault(id(comp), []).append((ex, pf, vf))
    out: dict[str, list[dict]] = {}
    for key, (comp, rows) in per.items():
        name = comp.code_on(as_of, known_on=as_of)
        if name in out:
            raise CorporateActionError(f"two companies end under {name!r} on {as_of}")
        adj = []
        for day, _code_then, vals in sorted(rows, key=lambda x: x[0]):
            pf = vf = Fraction(1)
            for ex, p, v in splits_by_comp.get(key, ()):
                if day < ex:
                    pf *= p
                    vf *= v
            adj.append({"date": day, **{k: float(vals[k] * pf) for k in _PRICE}, "volume": float(vals["volume"] * vf)})
        out[name] = adj
    return out


class Universe:
    """Point-in-time listed universe."""

    def __init__(self, listings: Iterable[Mapping], actions: Iterable[Mapping] = ()) -> None:
        self._reg = _Registry(listings, actions)

    def on(self, day: Any) -> list[str]:
        day = _date(day, "date")
        out = []
        for comp in self._reg.companies:
            lst = self._reg.listing(comp)
            if lst is None:
                continue
            listed, delisted = lst
            if listed <= day and (delisted is None or day < delisted):
                out.append(comp.code_on(day))
        return sorted(out)


def universe(listings: Iterable[Mapping], actions: Iterable[Mapping], dates: Iterable[Any]) -> dict[str, list[str]]:
    u = Universe(listings, actions)
    return {_date(d, "dates[]"): u.on(d) for d in dates}
