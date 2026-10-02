#!/usr/bin/env python3
"""カードの説明(docs/RESEARCH/cards/<id>/CARD.md)の欄の検査(W1 の仕様 C6)。

    python scripts/check_card.py docs/RESEARCH/cards/<id>/CARD.md [--root <データの根>]

通れば終了コード 0、拒めば 1(拒んだ理由を 1 行ずつ出す)。

欄は `## <欄の名前>` の見出しで書く(見出しの名前の後ろに「(逐語)」などを足してよい)。
本文が空白だけの欄は、無い欄と同じに扱う。同じ欄の見出しが 2 つあれば拒む。欄の読み方は
`bot.research.cards.cardmd`(測定の入口 `measure_card` と同じ読み方)。

確かめ(拒むとき):
- 欄 10 個(cardmd.FIELDS: 仕様 C6 の 9 つと「測定の設定」): 欄が無い・空・2 つある
- 測る期間: `## 測る期間` に `- 開始: <ISO 時刻>` と `- 終了: <ISO 時刻>` が無い・読めない・
  開始 >= 終了。時刻は UTC からのずれ(`Z` か `+09:00`)つき。期間は [開始, 終了)
- 使うデータのパス: `## 使うデータと遅れ` に、行頭の `- ` の直後に `` `パス` `` で書いたパスが無い
- 測定の設定: vr_q_bars・day_zone が無い、値が読めない、どれかの行(参照の系列の宣言を含む)に
  出所が無い
- 市場: データのパスが、データの根の外にある、または下の表のどの市場にも当たらない
  (どの市場か分からないものは通さない)
- 封印: 測る期間が、その市場の封印の境より後にかかる。台帳が読めない・台帳のファイルが表の
  どの市場にも当たらないときも拒む

封印は、ファイルではなく「市場 × 期間」に掛かるものとして扱う(リードの答え、2026-10-02)。
市場ごとの境 = 台帳(`backtest_data/phase2_sealed/*/SEALED.json`)のうち、その市場に当たる全ファイルの
min(seal_from_ts, forward_start) の最も早いもの(1 ファイルの境の読み方はデータ層
`bot.bt.data.allowlist.SealRegistry` と同じ)。測る期間 [開始, 終了) が重なる = 終了 > 境。
UNSEAL_APPROVED のある単位(開封済み)も、データ層と同じく封印として扱う。

パスは比べる前に、データの根からの実パス(シンボリックリンク・`..`・`./`・絶対パスを解いたもの)に
そろえる(`normalize`)。市場の表 `MARKETS` はパスの型(fnmatch の型。`*` は `/` もまたぐ)で書く。
1 つのパスが 2 つの市場に当たれば拒む。

`CHECKS` は確かめの一覧。壊した版の試験(tests/research/cards/test_w1_t7_check_card.py)は、ここから
1 つずつ外した一覧で、対応する説明が通ってしまうことを確かめる。
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from typing import Callable, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bot.bt.core.errors import TimestampUnitError  # noqa: E402
from bot.bt.core.time import to_nanos  # noqa: E402
from bot.bt.data.allowlist import SealRegistry  # noqa: E402
from bot.bt.data.errors import SealedRangeError  # noqa: E402
from bot.research.cards.cardmd import (DATA, FIELDS, PERIOD, SETTINGS, Card, body, parse,  # noqa: E402,F401
                                       settings)

# 市場の名前 -> そのデータのパスの型(データの根からの実パス)。新しい置き場は、ここに足すまで拒まれる。
MARKETS: dict = {
    "bitflyer:FX_BTC_JPY": ("backtest_data/bitflyer_lightchart_FX_BTC_JPY_*/*",
                            "backtest_data/fx_btc_jpy_1m_continuous_*/*",
                            "backtest_data/executions_FX_BTC_JPY_*",
                            "backtest_data/bitflyer_executions_us_*/*",
                            "paper_logs/tape/*"),
    "bitflyer:BTC_JPY": ("backtest_data/bitflyer_lightchart_BTC_JPY_*/*",),
    "binance:BTCUSDT": ("backtest_data/binance_BTCUSDT_*/*",),
    "binance_um:BTCUSDT": ("backtest_data/binance_um_BTCUSDT_*/*",),
    "bitmex:XBTUSD": ("backtest_data/bitmex_XBTUSD_1m_from1s_*/*",),
    "fx:USDJPY": ("backtest_data/fx_usdjpy_*/*",),
    "jpx:n225_futures": ("backtest_data/n225f_225labo_*/*", "paper_logs/nk225_sessions.csv",
                         "paper_logs/on1_ledger.csv"),
    "jpx:cash": ("backtest_data/jpx_etf_daily_*/*", "backtest_data/reit_onr_*/*", "backtest_data/nk225_events_*/*"),
}

_PATH = re.compile(r"^\s*[-*]\s+`([^`]+)`")
_START = re.compile(r"^\s*[-*]\s*開始\s*[:：]\s*(\S+)\s*$")
_END = re.compile(r"^\s*[-*]\s*終了\s*[:：]\s*(\S+)\s*$")


def period(card: Card) -> tuple[Optional[tuple[int, int]], Optional[str]]:
    text, why = body(card, PERIOD)
    if why:
        return None, why
    starts = [m.group(1) for ln in text.splitlines() if (m := _START.match(ln))]
    ends = [m.group(1) for ln in text.splitlines() if (m := _END.match(ln))]
    if len(starts) != 1 or len(ends) != 1:
        return None, f"欄「{PERIOD}」に「- 開始: <時刻>」と「- 終了: <時刻>」が 1 行ずつ無い"
    try:
        lo, hi = int(to_nanos(starts[0], "iso")), int(to_nanos(ends[0], "iso"))
    except TimestampUnitError as exc:
        return None, f"欄「{PERIOD}」の時刻が読めない: {exc}"
    if not re.search(r"(Z|[+-]\d{2}:?\d{2})$", starts[0]) or not re.search(r"(Z|[+-]\d{2}:?\d{2})$", ends[0]):
        return None, f"欄「{PERIOD}」の時刻に UTC からのずれ(Z / +09:00 など)が無い"
    if lo >= hi:
        return None, f"欄「{PERIOD}」の開始 {starts[0]} が終了 {ends[0]} より前でない"
    return (lo, hi), None


def data_paths(card: Card) -> tuple[list[str], Optional[str]]:
    text, why = body(card, DATA)
    if why:
        return [], why
    paths = [m.group(1).strip() for ln in text.splitlines() if (m := _PATH.match(ln))]
    if not paths:
        return [], f"欄「{DATA}」に、行頭の「- 」の直後に `パス` で書いたデータのパスが無い"
    return paths, None


def normalize(path: str, root: str) -> Optional[str]:
    """The path relative to the real data root, every symlink, `..`, `./` and absolute form resolved
    (`/` as separator); None when it lies outside the root."""
    root_real = os.path.realpath(root)
    real = os.path.realpath(os.path.join(root_real, path.replace("\\", "/")))
    rel = os.path.relpath(real, root_real)
    if rel == ".." or rel.startswith(".." + os.sep) or os.path.isabs(rel):
        return None
    return rel.replace(os.sep, "/")


def market_of(rel: str, markets: dict) -> list[str]:
    """Every market whose path pattern the path (or, for a directory, a file in it) matches."""
    return sorted(m for m, pats in markets.items()
                  if any(fnmatch.fnmatchcase(rel, p) or fnmatch.fnmatchcase(rel + "/_", p) for p in pats))


def boundaries(root: str, markets: dict) -> tuple[dict, list[str]]:
    """(market -> earliest seal boundary ns, problems). Fails closed on an unreadable ledger or a ledger file
    no market matches."""
    try:
        seals = SealRegistry(root)
    except SealedRangeError as exc:
        return {}, [f"封印の台帳が読めない(読めなければ拒む): {exc}"]
    out: dict = {}
    problems = []
    for ent in seals.entries:
        rel = normalize(ent.path, root)
        ms = market_of(rel, markets) if rel is not None else []
        if len(ms) != 1:
            problems.append(f"台帳のファイル {ent.path}(単位 {ent.unit})が市場の表の 1 つの市場に当たらない "
                            f"({ms});表を直すまで拒む")
            continue
        out[ms[0]] = min(out.get(ms[0], ent.cutoff_ns), ent.cutoff_ns)
    return out, problems


Check = Callable[[Card, str], list]


def _field_check(name: str) -> Check:
    def check(card: Card, root: str) -> list:
        _b, why = body(card, name)
        return [why] if why else []
    check.__name__ = f"field:{name}"
    return check


def _period_check(card: Card, root: str) -> list:
    _r, why = period(card)
    return [why] if why else []


def _data_check(card: Card, root: str) -> list:
    if body(card, DATA)[1]:
        return []  # a missing / empty / doubled field is the field check's to report
    _p, why = data_paths(card)
    return [why] if why else []


def _settings_check(card: Card, root: str) -> list:
    return settings(card)[1]  # a missing field is the field check's to report


def _markets_check(card: Card, root: str, markets: Optional[dict] = None) -> list:
    markets = MARKETS if markets is None else markets
    out = []
    for p in data_paths(card)[0]:
        rel = normalize(p, root)
        if rel is None:
            out.append(f"データのパス {p} がデータの根の外にある")
            continue
        ms = market_of(rel, markets)
        if len(ms) != 1:
            out.append(f"データのパス {p}({rel})が市場の表の 1 つの市場に当たらない({ms});どの市場か分からない"
                       f"データは通さない")
    return out


def _seal_check(card: Card, root: str, markets: Optional[dict] = None) -> list:
    markets = MARKETS if markets is None else markets
    rng, why_p = period(card)
    paths, why_d = data_paths(card)
    if why_p or why_d:
        return []  # reported by the period / data-path checks
    bounds, problems = boundaries(root, markets)
    out = list(problems)
    for p in paths:
        rel = normalize(p, root)
        ms = market_of(rel, markets) if rel is not None else []
        if len(ms) != 1:
            continue  # reported by the market check
        b = bounds.get(ms[0])
        if b is not None and rng[1] > b:
            out.append(f"測る期間の終了が、{p} の市場 {ms[0]} の封印の境 {b} ns より後(封印の期間に重なる)")
    return out


_period_check.__name__ = "period"
_data_check.__name__ = "data_paths"
_settings_check.__name__ = "settings"
_markets_check.__name__ = "markets"
_seal_check.__name__ = "seal"

CHECKS: tuple = tuple(_field_check(n) for n in FIELDS) + (_period_check, _data_check, _settings_check,
                                                         _markets_check, _seal_check)


def problems(text: str, root: str, checks: tuple = CHECKS) -> list[str]:
    card = parse(text)
    out: list[str] = []
    for c in checks:
        out.extend(c(card, root))
    return out


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="カードの説明の欄と封印の期間を検査する")
    ap.add_argument("card", help="docs/RESEARCH/cards/<id>/CARD.md")
    ap.add_argument("--root", default=ROOT, help="データの根(封印の台帳 backtest_data/phase2_sealed がある所)")
    a = ap.parse_args(argv)
    with open(a.card, encoding="utf-8") as fh:
        text = fh.read()
    found = problems(text, a.root)
    if found:
        print(f"拒む: {a.card}")
        for p in found:
            print(f"- {p}")
        return 1
    print(f"通る: {a.card}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
