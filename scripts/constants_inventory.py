#!/usr/bin/env python3
"""Inventory of unsourced constants in config/constants.yaml (DATA_QA_CHECKLIST
item 8): every entry whose `source_type` is `assumed` (including
`deprecated: true` ones — a deprecated constant is by construction no longer
sourced for new judgments), or whose `value` is null.

For each flagged entry this prints a table (path, value, unit, source_type,
deprecated, consumers) and writes `docs/CONSTANTS_TODO.md` (Japanese) with a
measurement plan per entry. "Consumers" is a best-effort grep of src/ and
scripts/ (*.py, excluding __pycache__) for the constant's bare name and its
full "group.name" path — this only finds textual references (string literals
passed to `require_source`/`load_constants` lookups, or the bare name used as
a comment/identifier elsewhere); it cannot prove a constant feeds a live
judgment, only that the name appears somewhere in the code.

This script only reads config/constants.yaml and the src/scripts trees, and
only ever writes docs/CONSTANTS_TODO.md — nothing under data/, paper_logs/,
or backtest_data/ is touched.

Usage:
    python scripts/constants_inventory.py                 # table + write doc
    python scripts/constants_inventory.py --root /path
    python scripts/constants_inventory.py --out /path/to/CONSTANTS_TODO.md
    python scripts/constants_inventory.py --no-write       # table only
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from bot.constants import Constant, load_constants  # noqa: E402

CONSUMER_DIRS = ("src", "scripts")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_consumers(root: Path, path: str,
                    self_path: Path | None = None) -> list[str]:
    """Grep *.py under CONSUMER_DIRS (excluding __pycache__) for the
    constant's full "group.name" path (how it is actually referenced —
    `require_source("group.name", ...)` or a dict lookup on that string).
    Deliberately does NOT match on the bare `name` alone: several of these
    names (e.g. `fee_yen`) collide with unrelated identifiers elsewhere in
    the codebase and would misreport those files as consumers. Returns
    sorted repo-relative hits, excluding this script's own file (it names
    every flagged constant in its own strings, which would otherwise
    self-report as a consumer)."""
    needles = {path}
    hits: set[str] = set()
    for d in CONSUMER_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            if self_path is not None:
                try:
                    if p.resolve() == self_path.resolve():
                        continue
                except OSError:
                    pass
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(needle in text for needle in needles):
                try:
                    hits.add(str(p.relative_to(root)))
                except ValueError:
                    hits.add(str(p))
    return sorted(hits)


@dataclass
class FlaggedConstant:
    constant: Constant
    consumers: list[str]

    @property
    def path(self) -> str:
        return self.constant.path

    @property
    def flag_reasons(self) -> list[str]:
        reasons = []
        if self.constant.source_type == "assumed":
            reasons.append("assumed")
        if self.constant.deprecated:
            reasons.append("deprecated")
        if self.constant.value is None:
            reasons.append("null")
        return reasons


def flagged_constants(constants: dict[str, Constant], root: Path,
                       self_path: Path | None = None) -> list[FlaggedConstant]:
    out = []
    for path, c in sorted(constants.items()):
        if c.source_type == "assumed" or c.deprecated or c.value is None:
            consumers = find_consumers(root, path, self_path=self_path)
            out.append(FlaggedConstant(constant=c, consumers=consumers))
    return out


def print_table(flagged: list[FlaggedConstant]) -> None:
    print(f"{len(flagged)} flagged constants (assumed / deprecated / null) in config/constants.yaml\n")
    header = f"{'path':<48} {'value':<20} {'unit':<22} {'source_type':<12} {'deprecated':<10} consumers"
    print(header)
    print("-" * len(header))
    for f in flagged:
        c = f.constant
        consumers = ", ".join(f.consumers) if f.consumers else "(none found)"
        print(f"{f.path:<48} {str(c.value):<20} {str(c.unit):<22} {c.source_type:<12} "
              f"{str(c.deprecated):<10} {consumers}")


# Measurement plans: what data / which script / when feasible, per entry.
# Keyed by full "group.name" path. A constant not in this dict falls back to
# a generic template built from its `notes` field.
MEASUREMENT_PLANS: dict[str, dict[str, str]] = {
    "bitflyer_fx_btc_jpy.taker_round_trip_floor_bps_OLD": {
        "what": "何も新規計測しない — この定数は廃止済み(deprecated)。後継の実測値は "
                "`bitflyer_fx_btc_jpy.realized_round_trip_bps`(2.0〜2.6bps、E2 で測定済み)。",
        "script": "対応不要。使用箇所(`scripts/qa/pipeline_known_answer_taker.py`)は "
                   "`require_source` がこの定数で例外を出すことを確認するテストであり、"
                   "実際の値を消費してはいない。",
        "when": "対応不要(既に測定済みの後継値に置き換え済み)。",
    },
    "jpx_cash_equity.etf_spread_bps": {
        "what": "JPX 上場 ETF(1321/1306/1343/1591/2516 等、`config/on1_live.yaml` 対象銘柄)の"
                "板スプレッド(bps)を、kabuステーション PUSH 配信の板データから実測する。",
        "script": "現在この値を録る録画スクリプトが存在しない(`notes` 参照)。"
                   "`src/bot/jpx/kabu_client.py` の PUSH 配信を使い、"
                   "`scripts/record_oi.py`(bitFlyer 側)と同種の録画スクリプトを新規作成する必要がある"
                   "(例: `scripts/record_jpx_board.py`)。",
        "when": "kabuステーション API の板 PUSH 配信を受けられる時間帯(取引時間中)に、"
                "対象 ETF 全銘柄で複数日録れば実測可能。ON1 の発注前サニティに使う定数のため、"
                "ON1 実弾投入前に計測を完了させることが望ましい。",
    },
    "gmo_fx_usdjpy.spread_sen": {
        "what": "GMO ブランドの USDJPY FX スプレッド(sen 単位)を一次資料(公式手数料/スプレッド"
                "ページ)から確認する。現在の値は過去の研究メモから引いた未確認の丸め数値。",
        "script": "計測スクリプトではなく一次資料の確認作業。このセッションでは "
                   "gmo-fx.jp への疎通が壁(プロキシ経由の TLS CONNECT 失敗)で確認できず、"
                   "coin.z.com のページはクライアント側 JS 描画でスプレッド表を静的取得できなかった"
                   "(`source_url`/`verified_on` 欄に記録済み)。ブラウザ経由の目視確認、または"
                   "別ネットワークからの再取得が必要。",
        "when": "エグレス制限が無い環境(オーナー PC 等)で一次資料ページを開いた時点で可能。"
                "この定数は現在どの判断にも消費されていない(下表の consumers 参照)ため緊急度は低い。",
    },
    "gmo_fx_usdjpy.fee_yen": {
        "what": "GMO ブランドの USDJPY FX の取引手数料(円/回)を一次資料から確認する"
                "(現在値 0 円はリテール FX の慣習からの仮定で、この銘柄固有の確認はしていない)。",
        "script": "計測スクリプトではなく一次資料の確認作業。spread_sen と同じ疎通の壁に当たる。",
        "when": "spread_sen と同時に一次資料ページへ到達できた時点で確認可能。"
                "この定数も現在どの判断にも消費されていない。",
    },
}

GENERIC_PLAN = {
    "what": "notes 欄に記載の再測定方法に従う(下表参照)。",
    "script": "専用の計測スクリプトは未指定 — 新規作成が必要。",
    "when": "必要なデータが揃った時点。",
}


def render_todo_doc(flagged: list[FlaggedConstant]) -> str:
    lines = []
    lines.append("# 未計測・非推奨定数の一覧と計測計画(DATA_QA_CHECKLIST item 8)")
    lines.append("")
    lines.append(
        "`config/constants.yaml` のうち `source_type: assumed`(`deprecated: true` を含む)"
        "または `value: null` の定数を列挙する。`src/bot/constants.py: require_source()` が"
        "これらを判断に使おうとすると例外を出す(既定の仕組み)ので、下表はその対象一覧と、"
        "各々をいつ・どう実測できるかの計画。"
    )
    lines.append("")
    lines.append(f"生成日時(UTC): {_now_iso()}")
    lines.append("")
    lines.append("## 一覧")
    lines.append("")
    lines.append("| 定数 (group.name) | 現在値 | 単位 | source_type | deprecated | 参照元 (consumers) |")
    lines.append("|---|---|---|---|---|---|")
    for f in flagged:
        c = f.constant
        consumers = "、".join(f"`{x}`" for x in f.consumers) if f.consumers else "(参照箇所なし)"
        lines.append(f"| `{f.path}` | {c.value} | {c.unit} | {c.source_type} | {c.deprecated} | {consumers} |")
    lines.append("")
    lines.append("## 各定数の計測計画")
    lines.append("")
    for f in flagged:
        plan = MEASUREMENT_PLANS.get(f.path, GENERIC_PLAN)
        lines.append(f"### `{f.path}`")
        lines.append("")
        lines.append(f"- フラグ理由: {', '.join(f.flag_reasons)}")
        lines.append(f"- 何を計測するか: {plan['what']}")
        lines.append(f"- どのスクリプトで: {plan['script']}")
        lines.append(f"- いつ可能か: {plan['when']}")
        if f.constant.notes:
            lines.append(f"- 定数側の notes: {f.constant.notes}")
        lines.append("")
    lines.append(
        "## 備考\n\n"
        "- `require_source()` により、上記定数は明示的なキャッチなしでは判断(発注前チェック・"
        "バックテスト・レポートの結論)に使えない仕組みになっている(item 8 の「判定に使われない"
        "仕組み」)。\n"
        "- 本書は `scripts/constants_inventory.py` の出力であり、手で数値を書き換えない。"
        "再生成すれば常に最新の consumers 一覧が反映される。\n"
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(REPO_ROOT), help="repo root (default: this repo)")
    ap.add_argument("--out", default=None,
                     help="output doc path (default: <root>/docs/CONSTANTS_TODO.md)")
    ap.add_argument("--no-write", action="store_true", help="print table only, do not write the doc")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    constants = load_constants(root)
    flagged = flagged_constants(constants, root, self_path=Path(__file__).resolve())

    print_table(flagged)

    if not args.no_write:
        out_path = Path(args.out) if args.out else root / "docs" / "CONSTANTS_TODO.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_todo_doc(flagged), encoding="utf-8")
        print(f"\nwrote {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
