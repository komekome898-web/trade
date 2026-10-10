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


def insert_rows(md: str, rows_md: str, stamp: str) -> str:
    """下書き(`### §N` の見出しの下に表)を、docs/DATA.md の各節の終わり(次の `## ` の手前)に足す。"""
    blocks = re.findall(r"^### §(\d+)\s*\n(.*?)(?=^### |^## |\Z)", rows_md, re.M | re.S)
    for n, body in blocks:
        table = "\n".join(l for l in body.strip().splitlines() if l.startswith("|"))
        if not table:
            continue
        m = re.search(rf"^## {n}\.[^\n]*\n.*?(?=^## |\Z)", md, re.M | re.S)
        if not m:
            raise SystemExit(f"§{n} が docs/DATA.md に無い")
        add = f"\n#### 追記({stamp})\n\n{table}\n\n"
        md = md[:m.end()].rstrip("\n") + "\n" + add + md[m.end():]
    return md


def write_index(md: str, rows: list[str], stamp: str) -> str:
    head = (f"## 10. 置き場の一覧(機械が検める。`scripts/data_gates.py` の門 G2、{stamp})\n\n"
            "git に載ったデータの置き場ごとに、実物の最新の日付と、説明の行がある節。"
            "`python3 scripts/data_repair/registry_index.py --write` で作り直す(説明の行が無い置き場は節が空になり、門 G2 が止める)。\n\n"
            "| 置き場 | 最新の日付 | 説明の節 |\n|---|---|---|\n" + "\n".join(rows) + "\n")
    m = re.search(r"^## 10\. .*?(?=^## |\Z)", md, re.M | re.S)
    if m:
        return md[:m.start()] + head + ("\n" if m.end() < len(md) else "") + md[m.end():]
    return md.rstrip("\n") + "\n\n" + head


def main() -> int:
    base = dg.root()
    path = base / dg.DATA_MD
    md = path.read_text(encoding="utf-8")
    stamp = "2026-10-11、L-984"
    if "--insert" in sys.argv:
        rows_md = Path(sys.argv[sys.argv.index("--insert") + 1]).read_text(encoding="utf-8")
        md = insert_rows(md, rows_md, stamp)
        path.write_text(md, encoding="utf-8")
    secs = sections(md)
    only_missing = "--missing" in sys.argv
    rows = []
    for f, d in sorted(dg.families(dg.tracked_paths(base)).items()):
        name = f.split("/", 1)[1] if f.startswith("paper_logs/") else f
        hit = next((n for n, body in secs if name in body), "")
        if only_missing and hit:
            continue
        rows.append(f"| {f} | {d or '—'} | {('§' + hit) if hit else ''} |")
    if "--write" in sys.argv:
        path.write_text(write_index(md, rows, stamp), encoding="utf-8")
        print(f"§10 を書いた({len(rows)} 行、節が空 {sum(r.endswith('|  |') for r in rows)} 行)")
    else:
        print("\n".join(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
