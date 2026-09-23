#!/usr/bin/env python3
"""Regenerate DEFINITIONS.md from `scenes.SCENES` (the single source of truth).

Run this after any edit to scenes.py:
    python3 tests/bt/battery/item_0/gen_definitions.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ITEM0_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_ITEM0_DIR))

from scenes import SCENES  # noqa: E402

_VIEWPOINT_TITLES = {
    1: "事象駆動アーキテクチャ",
    2: "事象型の網羅性",
    3: "時刻の精度",
    4: "ルックアヘッド防止の構造化",
    5: "同時刻事象の決定的順序",
    6: "戦略 API の完全性",
    7: "拡張口(モジュール性)",
}

_KIND_LABEL = {"known_answer": "既知解の場面", "capability": "能力の場面"}


def render() -> str:
    lines: list[str] = []
    lines.append("# 場面の定義 -- 項目0「核」(場面係、2026-09-23)")
    lines.append("")
    lines.append(
        "このファイルは `scenes.py` から自動生成される(`gen_definitions.py`)。"
        "場面を変えるときは `scenes.py` を編集してこのスクリプトを再実行すること -- "
        "手で書き足さない(2文書が食い違う最大の原因)。"
    )
    lines.append("")
    lines.append(
        "委任文 `docs/DATA/delegations/20260923_backtest_env_prompt.md` §3「場面集」の定義どおり、"
        "**既知解の場面**(合成の入力 + エンジンを見ずに手計算・閉じた式で出した正解。"
        "出し方を明記)と、**能力の場面**(「X ができるか」を実際に呼んで試す)"
        "の2種類のみを置く。**道具の名前は書かない**(場面はどの対象に対しても同一)。"
        "場面集の規則1(2026-09-23、監査役の指摘を受けて追加)により、**能力の場面にも"
        "「正解」がある**: 呼んだ結果を正解と突き合わせて判定し、「持っている」という申告"
        "だけでは数えない。"
    )
    lines.append("")
    lines.append(f"全 {len(SCENES)} 場面(観点別の内訳は下の見出し順)。")
    lines.append("")

    for vp in sorted(_VIEWPOINT_TITLES):
        vp_scenes = [s for s in SCENES if s.viewpoint == vp]
        if not vp_scenes:
            continue
        lines.append(f"## 観点{vp}: {_VIEWPOINT_TITLES[vp]}")
        lines.append("")
        for s in vp_scenes:
            lines.append(f"### `{s.id}` -- {s.title}({_KIND_LABEL[s.kind]})")
            lines.append("")
            lines.append(f"- **入力**: `{s.input}`")
            lines.append(f"- **期待**: `{s.expected}`")
            lines.append(f"- **正解の出し方**: {s.derivation}")
            lines.append(f"- **何を測るか**: {s.measures}")
            if s.notes:
                lines.append(f"- **注記**: {s.notes}")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    out_path = _ITEM0_DIR / "DEFINITIONS.md"
    out_path.write_text(render(), encoding="utf-8")
    print(f"wrote {out_path}")
