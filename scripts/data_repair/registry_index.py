#!/usr/bin/env python3
"""docs/DATA.md §10(置き場の一覧)の下書きを出す(門 G2 を直す道具。L-984「DATA.MDを最新の状態に更新して」)。

git に載った置き場ごとに、実物の最新の日付と、docs/DATA.md のどの節がその名前を書いているかを並べる。
名前を書いた節が無い置き場は「説明の節」を空にして出す(そこは手で説明の行を書く)。

Usage:
    python3 scripts/data_repair/registry_index.py            # 表の行を出す
    python3 scripts/data_repair/registry_index.py --missing  # 説明の節が無いものだけ
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import data_gates as dg  # noqa: E402


def sections(md: str) -> list[tuple[str, str]]:
    """(節の番号, 本文)。§10 は除く。"""
    out = []
    for m in re.finditer(r"^## (\d+)\.[^\n]*\n(.*?)(?=^## |\Z)", md, re.M | re.S):
        if m.group(1) != "10":
            out.append((m.group(1), m.group(0)))
    return out


def main() -> int:
    base = dg.root()
    md = (base / dg.DATA_MD).read_text(encoding="utf-8")
    secs = sections(md)
    only_missing = "--missing" in sys.argv
    for f, d in sorted(dg.families(dg.tracked_paths(base)).items()):
        name = f.split("/", 1)[1] if f.startswith("paper_logs/") else f
        hit = next((n for n, body in secs if name in body), "")
        if only_missing and hit:
            continue
        print(f"| {f} | {d or '—'} | {('§' + hit) if hit else ''} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
