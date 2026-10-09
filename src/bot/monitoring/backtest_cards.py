"""The research cards in the dashboard's バックテスト tab: the manifest, the variants, the id "cards/<card>/<variant>".

The cards' display output is written by scripts/dashboard_cards/ into <runs dir>/cards/:

    cards/manifest.json                          {version, git_sha, total_bytes, variants: [row], excluded: [row]}
    cards/<card>/<variant>/trades.json.gz        the column form (version, t_unit, entry_t_ns, entry_px, exit_t_ns, ...)
    cards/<card>/<variant>/daily.csv             day, pnl_pct, n  (pnl_pct = the card's pnl rate in percent, written so
                                                 since L-920; exports from before hold pnl_bp = the rate x 1e4, read as
                                                 pnl_bp / 100, since bp names only a price-move rate)
    cards/<card>/<variant>/provenance.json       where the numbers come from and what was checked

This module only READS them (it never writes under cards/). What it decides:

  * The variants of a card are collected from the manifest, never listed by hand; the ledger (backtest_themes.CARD_THEMES)
    says what a card is and how a variant's NAME splits into axes.
  * A variant is selectable only when the manifest says display_ok is true AND its files are there and complete. A row with
    display_ok = true whose files are missing, whose sizes differ from the manifest's file_bytes, or whose gzip is broken
    is "準備中" (being written); a row with display_ok = false (not exported, or its check did not match) is listed with
    the manifest's reason and cannot be chosen; the manifest's `excluded` entries are listed with their reason.
  * The manifest is read again whenever its modification time or size changes (no restart), and a half-written
    manifest keeps the last good one. The state of a variant's files is cached by their (mtime, size).
  * The run id of a variant is "cards/<card>/<variant>". Only a pair the manifest holds, with display_ok true, is
    resolved; anything else (a pair not in the manifest, a name with a separator or a dot-dot, a path that leaves the
    cards directory) is refused as "not a run" (BacktestViewError, 404). Nothing is joined to a path before it is
    matched against the manifest's own strings.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import re
import threading
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from bot.monitoring import backtest_themes as T
from bot.monitoring import backtest_view as BV

CARD_PREFIX = "cards/"
FILES = ("trades.json.gz", "daily.csv", "provenance.json")
_SAFE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")
_LOCK = threading.RLock()


class CardPreparing(ValueError):
    """The variant is in the manifest with display_ok = true but its files are not complete yet."""


@dataclass
class Manifest:
    root: Path  # the cards directory
    rows: dict = field(default_factory=dict)  # (card, variant) -> row
    excluded: list = field(default_factory=list)
    git_sha: Optional[str] = None
    total_bytes: Optional[int] = None
    error: Optional[str] = None  # why this is the previous good read (or empty)


_MAN: dict = {}  # manifest path -> ((mtime_ns, size), Manifest)


def _parse_manifest(root: Path, doc: Any) -> Manifest:
    if not isinstance(doc, dict) or not isinstance(doc.get("variants"), list):
        raise ValueError("manifest.json の形が違う(variants の配列が無い)")
    rows: dict = {}
    for r in doc["variants"]:
        if isinstance(r, dict) and type(r.get("card")) is str and type(r.get("variant")) is str:
            rows.setdefault((r["card"], r["variant"]), r)
    exc = [e for e in (doc.get("excluded") or []) if isinstance(e, dict)]
    return Manifest(root, rows, exc, doc.get("git_sha"), doc.get("total_bytes"))


def load_manifest(cards_dir: Path) -> Optional[Manifest]:
    """The manifest of one cards directory, read again when its mtime or size changed. None when there is no manifest. A file
    that cannot be parsed (being rewritten) gives the last good read with `error` set, or an empty manifest with `error`."""
    p = Path(cards_dir) / "manifest.json"
    try:
        st = p.stat()
    except OSError:
        return None
    key = (st.st_mtime_ns, st.st_size)
    with _LOCK:
        hit = _MAN.get(str(p))
        if hit and hit[0] == key:
            return hit[1]
    try:
        with open(p, "r", encoding="utf-8") as fh:
            man = _parse_manifest(Path(cards_dir), json.load(fh))
    except (OSError, ValueError) as exc:
        with _LOCK:
            old = _MAN.get(str(p))
        if old:
            return Manifest(old[1].root, old[1].rows, old[1].excluded, old[1].git_sha, old[1].total_bytes,
                            f"manifest.json を読み直せなかった(書き足し中か)ので前の読みを使う: {type(exc).__name__}: {exc}")
        return Manifest(Path(cards_dir), error=f"manifest.json を読めない: {type(exc).__name__}: {exc}")
    with _LOCK:
        _MAN[str(p)] = (key, man)
    return man


def manifests(runs_dir: Any) -> list[Manifest]:
    out, seen = [], set()
    for root in BV._roots(runs_dir):
        d = Path(root) / "cards"
        real = os.path.realpath(d)
        if real in seen:
            continue
        seen.add(real)
        m = load_manifest(d)
        if m is not None:
            out.append(m)
    return out


# ---- the state of a variant -------------------------------------------------------------------------------------
_OK: dict = {}  # (path, mtime_ns, size) -> None (complete) or the reason it is not


def _gzip_complete(p: Path, st: os.stat_result) -> Optional[str]:
    key = (str(p), st.st_mtime_ns, st.st_size)
    with _LOCK:
        if key in _OK:
            return _OK[key]
    why = None
    try:
        with gzip.open(p, "rb") as fh:
            while fh.read(1 << 20):
                pass
    except (OSError, EOFError, zlib.error) as exc:
        why = f"{p.name} の gzip が壊れている(書きかけ): {type(exc).__name__}"
    with _LOCK:
        _OK[key] = why
        while len(_OK) > 400:
            _OK.pop(next(iter(_OK)))
    return why


def _json_complete(p: Path, st: os.stat_result) -> Optional[str]:
    """None when provenance.json parses and does not say display_ok = false; else why not ("書きかけ" or "display_ok が false")."""
    key = (str(p), st.st_mtime_ns, st.st_size)
    with _LOCK:
        if key in _OK:
            return _OK[key]
    why = None
    try:
        with open(p, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if isinstance(doc, dict) and doc.get("display_ok") is False:
            why = "BLOCKED:provenance.json の display_ok が false"
    except (OSError, ValueError) as exc:
        why = f"{p.name} を読めない(書きかけ): {type(exc).__name__}"
    with _LOCK:
        _OK[key] = why
    return why


def _daily_complete(p: Path, st: os.stat_result) -> Optional[str]:
    key = (str(p), st.st_mtime_ns, st.st_size)
    with _LOCK:
        if key in _OK:
            return _OK[key]
    why = None
    try:
        with open(p, "r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            why = "daily.csv が空(書きかけ)"
        for r in rows:
            _daily_pct(r)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        why = f"daily.csv を読めない(書きかけ): {type(exc).__name__}"
    with _LOCK:
        _OK[key] = why
    return why


def _variant_dir(man: Manifest, card: str, variant: str) -> Optional[Path]:
    """The directory of a (card, variant) the manifest holds, only when it stays under the cards directory."""
    if not (_SAFE.match(card) and _SAFE.match(variant)) or ".." in card or ".." in variant:
        return None
    d = man.root / card / variant
    root = os.path.realpath(man.root)
    real = os.path.realpath(d)
    return d if real == os.path.join(root, card, variant) or real.startswith(root + os.sep) else None


def variant_state(man: Manifest, row: dict, deep: bool = False) -> tuple[str, str]:
    """(state, reason): "ready" (selectable), "preparing" (display_ok but the files are not complete), "blocked" (display_ok
    is false: the manifest's reason is shown) or "not_exported" (the manifest says it was not exported).
    The list (catalog) asks with deep = False: only the manifest and the files' presence, sizes (against the manifest's file_bytes)
    and provenance.json (a few KB) are looked at, so listing 50 variants costs a few stat calls. Opening one variant asks with
    deep = True: its gzip is read to the end and daily.csv is parsed (the result is cached by path, mtime and size)."""
    if row.get("display_ok") is not True:
        if row.get("status") == "not_exported" and str(row.get("reason") or GENERIC_REASON) == GENERIC_REASON:
            return "not_exported", ""  # waiting for the measurement: not a failure
        if row.get("status") == "not_exported":
            return "blocked", str(row["reason"])
        return "blocked", str(row.get("reason") or "照合が一致しなかった(manifest の display_ok が false)")
    d = _variant_dir(man, row["card"], row["variant"])
    if d is None:
        return "blocked", "manifest の名前がパスとして安全でない"
    missing = [f for f in FILES if not (d / f).is_file()]
    if missing:
        return "preparing", f"出力のファイルがまだ無い({' / '.join(missing)})"
    want = row.get("file_bytes") if isinstance(row.get("file_bytes"), dict) else {}
    for f in FILES:
        st = (d / f).stat()
        if f in want and type(want[f]) is int and want[f] != st.st_size:
            return "preparing", f"{f} の大きさ({st.st_size} B)が manifest の記録({want[f]} B)と違う(書き足し中)"
    st = (d / "trades.json.gz").stat()
    why = _json_complete(d / "provenance.json", (d / "provenance.json").stat())
    if not why and deep:
        why = _gzip_complete(d / "trades.json.gz", st) or _daily_complete(d / "daily.csv", (d / "daily.csv").stat())
    if why and why.startswith("BLOCKED:"):
        return "blocked", why[len("BLOCKED:"):]
    if why:
        return "preparing", why
    return "ready", ""


# ---- a variant by id --------------------------------------------------------------------------------------------
@dataclass
class CardRef:
    man: Manifest
    row: dict
    card: str
    variant: str
    dir: Path

    @property
    def run_id(self) -> str:
        return f"{CARD_PREFIX}{self.card}/{self.variant}"


def card_id(card: str, variant: str) -> str:
    return f"{CARD_PREFIX}{card}/{variant}"


def resolve(runs_dir: Any, run_id: Any, require_ready: bool = True) -> Optional[CardRef]:
    """None when `run_id` is not the card form (the caller goes on with the 64-hex run id). A card-form id the manifest does
    not hold with display_ok = true is BacktestViewError (404). A held variant whose files are not complete is CardPreparing."""
    if type(run_id) is not str or not run_id.startswith(CARD_PREFIX):
        return None
    parts = run_id.split("/")
    if len(parts) != 3 or not _SAFE.match(parts[1]) or not _SAFE.match(parts[2]) or ".." in run_id:
        raise BV.BacktestViewError(f"not a run id: {run_id!r}")
    key = (parts[1], parts[2])
    for man in manifests(runs_dir):
        row = man.rows.get(key)
        if row is None:
            continue
        if row.get("display_ok") is not True:
            raise BV.BacktestViewError(f"card variant {run_id} is not displayable: {row.get('reason') or 'display_ok is false'}")
        d = _variant_dir(man, *key)
        if d is None:
            raise BV.BacktestViewError(f"not a run id: {run_id!r}")
        ref = CardRef(man, row, key[0], key[1], d)
        if require_ready:
            state, why = variant_state(man, row, deep=True)
            if state == "blocked":
                raise BV.BacktestViewError(f"card variant {run_id} is not displayable: {why}")
            if state != "ready":
                raise CardPreparing(f"準備中: {why}")
        return ref
    raise BV.BacktestViewError(f"no card variant {run_id}")


_PROV: dict = {}


def provenance(ref: CardRef) -> dict:
    p = ref.dir / "provenance.json"
    st = p.stat()
    key = (str(p), st.st_mtime_ns, st.st_size)
    with _LOCK:
        if key in _PROV:
            return _PROV[key]
    with open(p, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    with _LOCK:
        _PROV[key] = doc
        while len(_PROV) > 80:
            _PROV.pop(next(iter(_PROV)))
    return doc


def _iso_ns(s: Any) -> Optional[int]:
    if type(s) is not str:
        return None
    try:
        return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()) * 10**9
    except ValueError:
        return None


def record_of(ref: CardRef) -> dict:
    """A record shaped like a run's record.json for the parts of the tab that read one: the traded instrument (from the
    ledger), the period (from the manifest row, else provenance), no data entries (the card's own inputs are named in
    `_card.data_dirs_read`), no currency (the column form holds a rate only)."""
    prov = provenance(ref)
    per = ref.row.get("period") or prov.get("period") or [None, None]
    ct = T.card_theme(ref.card)
    return {"config": {"instrument": ct.get("instrument") if ct else None}, "data": [], "purpose": "研究のカード", "currency": None,
            "engine": {"first_time_ns": _iso_ns(per[0]), "last_time_ns": _iso_ns(per[1])},
            "_card": {"card": ref.card, "variant": ref.variant, "data_dirs_read": list(prov.get("data_dirs_read") or [])}}


def info(ref: CardRef, trades_cut: Optional[int] = None) -> dict:
    """What the page shows about where a card variant's numbers come from and how far they were checked (the manifest row
    and provenance.json, verbatim)."""
    prov = provenance(ref)
    row = ref.row
    ct = T.card_theme(ref.card)
    return {"card": ref.card, "variant": ref.variant, "card_title": ct["title"] if ct else ref.card,
            "owner_origin": bool(ct and ct.get("owner_origin")),
            "verified_items": list(row.get("verified_items") or prov.get("verified_items") or []),
            "not_verified": list(row.get("not_verified") if "not_verified" in row else prov.get("not_verified") or []),
            "display_ok_rule": prov.get("display_ok_rule"), "n_trades_manifest": row.get("n_trades"),
            "n_trades_cut": trades_cut, "trade_definition": prov.get("trade_definition"), "git_sha": prov.get("git_sha"),
            "manifest_git_sha": ref.man.git_sha, "seal": prov.get("seal"), "data_dirs_read": list(prov.get("data_dirs_read") or []),
            "research_cmd": (prov.get("script") or {}).get("research_cmd"), "export": (prov.get("script") or {}).get("export"),
            "rate_note": T.RATE_NOTE_LIMIT if ref.variant.startswith("limit_") else T.RATE_NOTE,
            "seconds": row.get("seconds"), "instrument": ct.get("instrument") if ct else None,
            "instrument_source": ct.get("instrument_source") if ct else None}


def _daily_pct(r: dict) -> float:
    """A daily.csv row's pnl rate in percent: the column pnl_pct, else the exported pnl_bp / 100 (see the module doc)."""
    if r.get("pnl_pct") not in (None, ""):
        return float(r["pnl_pct"])
    return float(r["pnl_bp"]) / 100


def daily_rows(ref: CardRef) -> list:
    with open(ref.dir / "daily.csv", "r", encoding="utf-8", newline="") as fh:
        return [(r["day"], _daily_pct(r)) for r in csv.DictReader(fh)]


def daily_drawdown_pct(ref: CardRef) -> float:
    """The research's maximum drawdown (scripts/w4_measure/light_b2.py extra_stats): the largest fall of the running sum of
    the daily profits (daily.csv, one row per day) below its running peak, the sum starting at 0."""
    s = 0.0
    peak = 0.0
    dd = 0.0
    for _, v in daily_rows(ref):
        s += v
        peak = max(peak, s)
        dd = max(dd, peak - s)
    return dd


def headline(ref: CardRef, stats: dict, n_after_cut: int) -> tuple[dict, dict]:
    """(stats with the card's headline numbers, what each came from). Trades count, win rate: the research's own values
    copied into provenance.json (checks["extra.trades"]["git"], from the research's extra.json) when there are some and no
    trade was cut at the seal boundary; else computed from the exported trades (their pnl_pct are rounded to 6 decimals (older
    exports: pnl_bp to 4 decimals, the same precision), so a tiny win can become 0: the small difference from the research). Maximum drawdown: from daily.csv by the research's
    definition (no trade cut), else from the trades one by one (not the research's definition)."""
    prov = provenance(ref)
    checks = prov.get("checks") or {}
    git_tr = (checks.get("extra.trades") or {}).get("git")
    git_dd = (checks.get("extra.drawdown") or {}).get("git")
    out = dict(stats)
    src: dict = {}
    n_exp = ref.row.get("n_trades")
    uncut = n_exp is None or n_after_cut == n_exp
    if uncut and isinstance(git_tr, dict) and type(git_tr.get("n")) is int and git_tr.get("win_rate") is not None and git_tr["n"] == stats["n"]:
        out["win_rate"] = float(git_tr["win_rate"])
        out["wins"] = int(round(out["win_rate"] * git_tr["n"]))
        src["win_rate"] = "研究の値(provenance に写した extra.json の trades。書き出しの丸めの影響を受けない)"
    else:
        src["win_rate"] = "書き出した取引から計算(書き出しの列 pnl_pct(損益の率 %)の小数 6 桁の丸め(L-920 より前の書き出しは pnl_bp(率 × 1 万)の小数 4 桁)で、微小な勝ちが 0 になり、研究の数とわずかにずれることがある)"
    if uncut:
        try:
            out["max_dd_pct"] = daily_drawdown_pct(ref)
            src["max_dd"] = "daily.csv から日ごとに計算(研究と同じ定義: 日ごとの損益の累計の、それまでの最高値からの最大の落ち込み)"
        except (OSError, ValueError, KeyError):
            src["max_dd"] = "取引ごとの累計から計算(研究の定義ではない)"
    else:
        src["max_dd"] = "取引ごとの累計から計算(封印の境で取引を切ったため daily.csv は使えない。研究の定義ではない)"
    src["n"] = "書き出した取引の数(封印の境で切った後)"
    # extra.json written after L-920 holds max_pct (percent); older ones hold max_bp (x 1e4), read as / 100
    _d = git_dd if isinstance(git_dd, dict) else {}
    if _d.get("max_pct") is not None:
        src["research_max_dd_pct"] = float(_d["max_pct"])
    else:
        _mb = _d.get("max_bp")
        src["research_max_dd_pct"] = None if _mb is None else float(_mb) / 100
    return out, src


def daily_sum_pct(ref: CardRef) -> float:
    """Sum of daily.csv's pnl rate in percent (what the check "the daily file and the trades agree" compares to the
    trades' sum)."""
    with open(ref.dir / "daily.csv", "r", encoding="utf-8", newline="") as fh:
        return float(sum(_daily_pct(r) for r in csv.DictReader(fh)))


# ---- the catalog ------------------------------------------------------------------------------------------------
WAITING = "測定待ち(書き出し・照合がまだ)"
GENERIC_REASON = "未実行または失敗"  # what scripts/dashboard_cards writes for a variant it has not exported yet
STATE_LABEL = {"ready": "表示できる", "preparing": "準備中", "blocked": "表示できない(失敗: 照合が一致しない、または display_ok = false)",
               "not_exported": WAITING}


def _axes_of(ct: Optional[dict], variant: str) -> tuple[Optional[dict], dict]:
    return T.card_family_of(ct, variant) if ct else (None, {})


def _strategy(theme_title: str, card: str, fam_id: str, title: str, description: list, sources: list, axis_keys: list,
              items: list, excluded: list, default: Optional[str]) -> dict:
    ready = [i for i in items if i["state"] == "ready"]
    other = [i for i in items if i["state"] != "ready"]
    axes = []
    for k in axis_keys:
        vals = {i["tokens"].get(k) for i in ready}
        vals.discard(None)
        if not vals:
            continue
        spec = T.CARD_AXES.get(k, {})
        entries = []
        for v in sorted(vals, key=lambda v: T.card_axis_order(k, v)):
            lab, note = T.card_axis_label(k, v)
            entries.append({"value": v, "label": lab, "note": note})
        axes.append({"key": k, "label": spec.get("label", k), "source": spec.get("source", "台帳にこの軸の出所が無い"),
                     "values": entries, "fixed": len(entries) == 1, "secondary": False})
    order = {a["key"]: {e["value"]: i for i, e in enumerate(a["values"])} for a in axes}
    ready.sort(key=lambda i: (tuple(order[a["key"]].get(i["tokens"].get(a["key"]), 99) for a in axes), i["variant"]))
    runs = [{"run_id": i["run_id"], "group": f"cards/{card}", "variant": i["variant"], "state": "ready",
             "axes": {a["key"]: i["tokens"].get(a["key"], "—") for a in axes}, "n_trades": i["n_trades"], "period": i["period"]}
            for i in ready]
    unavailable = []
    for i in sorted(other, key=lambda i: (T.card_axis_order(axis_keys[0], i["tokens"].get(axis_keys[0], "")) if axis_keys else (0, 0.0, ""), i["variant"])):
        labs = [T.card_axis_label(k, i["tokens"][k])[0] for k in axis_keys if k in i["tokens"]]
        unavailable.append({"run_id": i["run_id"], "variant": i["variant"], "state": i["state"], "state_label": STATE_LABEL[i["state"]],
                            "reason": i["reason"], "axes_text": " / ".join(labs) or i["variant"]})
    pick = next((r for r in runs if r["variant"] == default), None) or (runs[0] if runs else None)
    return {"id": f"card:{card}" + ("" if fam_id == "main" else f":{fam_id}"), "kind": "card", "title": title, "description": description,
            "sources": sources, "groups": [f"cards/{card}"], "theme": theme_title, "axes": axes, "runs": runs, "n_runs": len(runs),
            "default_run_id": pick["run_id"] if pick else None, "unavailable": unavailable, "excluded": excluded, "card": card}


def catalog_themes(runs_dir: Any) -> tuple[list[dict], int, list[str]]:
    """(themes, number of selectable variants, notes) of the cards in the manifest(s). A card of the ledger appears when the
    manifest holds a row or an excluded entry for it; a card the ledger does not know, and a variant no family pattern
    splits, are listed too (the tab hides nothing)."""
    mans = manifests(runs_dir)
    if not mans:
        return [], 0, []
    rows: dict = {}
    excluded: list = []
    notes: list[str] = []
    for m in mans:
        for k, r in m.rows.items():
            rows.setdefault(k, (m, r))
        excluded += m.excluded
        if m.error:
            notes.append(m.error)
    cards = [ct["card"] for ct in T.CARD_THEMES] + sorted({c for c, _ in rows if T.card_theme(c) is None}
                                                         | {e["card"] for e in excluded if type(e.get("card")) is str and T.card_theme(e["card"]) is None})
    themes, n_ready = [], 0
    for card in cards:
        ct = T.card_theme(card)
        crows = {v: mr for (c, v), mr in rows.items() if c == card}
        cexc = [e for e in excluded if e.get("card") == card]
        if not crows and not cexc:
            continue
        title = ct["title"] if ct else card
        fams = T.card_families(ct) if ct else []
        buckets: dict[str, list] = {f["id"]: [] for f in fams}
        buckets[T.OTHER_FAMILY] = []
        for variant, (man, row) in sorted(crows.items()):
            fam, tokens = _axes_of(ct, variant)
            state, why = variant_state(man, row)
            fid = fam["id"] if fam else T.OTHER_FAMILY
            if fam is None:
                tokens = {"variant": variant}
            buckets[fid].append({"variant": variant, "run_id": card_id(card, variant), "tokens": tokens, "state": state, "reason": why,
                                 "n_trades": row.get("n_trades"), "period": row.get("period")})
        exc_by: dict[str, list] = {f["id"]: [] for f in fams}
        exc_by[T.OTHER_FAMILY] = []
        for e in cexc:
            raw = str(e.get("variant", ""))
            fid = next((f["id"] for f in fams if f.get("prefix") and raw.startswith(f["prefix"])), fams[0]["id"] if fams else T.OTHER_FAMILY)
            exc_by[fid].append({"variant": raw, "reason": str(e.get("reason") or ""), "status": str(e.get("status") or "excluded")})
        strategies = []
        for f in fams:
            if buckets[f["id"]] or exc_by[f["id"]]:
                strategies.append(_strategy(title, card, f["id"], f["title"], f["description"], f["sources"], f["axes"], buckets[f["id"]],
                                            exc_by[f["id"]], f.get("default")))
        if buckets[T.OTHER_FAMILY] or exc_by[T.OTHER_FAMILY]:
            strategies.append(_strategy(
                title, card, T.OTHER_FAMILY, f"{title}: {T.OTHER_TITLE}" if ct else title,
                ["このカードの変種のうち、名前の分解の規則が台帳に無いもの。変種名のまま並べる(manifest.json の行)。",
                 "分解の規則と日本語のラベルは backtest_themes.CARD_THEMES に足すまで無い。", "選べるのは manifest の display_ok が true で、出力が揃ったものだけ。"],
                ["backtest_runs_shared/cards/manifest.json の variants と excluded"], ["variant"], buckets[T.OTHER_FAMILY], exc_by[T.OTHER_FAMILY], None))
        n_ready += sum(s["n_runs"] for s in strategies)
        themes.append({"id": f"card:{card}", "title": title,
                       "summary": ct["summary"] if ct else "台帳に載っていないカード(manifest にだけある)",
                       "sources": ct["sources"] if ct else [], "owner_origin": bool(ct and ct.get("owner_origin")), "strategies": strategies,
                       "is_card": True})
    return themes, n_ready, notes
