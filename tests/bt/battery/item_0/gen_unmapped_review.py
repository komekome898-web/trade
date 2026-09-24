#!/usr/bin/env python3
"""Write the review of the grep hits gen_pool.py could not map to a candidate
into opponents/CONSIDERED.md (between the two markers), one row per
(viewpoint, SCAN line). Round r4-1, critic i0-r1-17 / i0-r2-09 / i0-r3-07:
those lines were never looked at.

The kind of each line is decided by where it sits in SCAN, by fixed rules:
  * under a `## src/bot` / `## scripts` / `## tests` / `## docs` /
    `## backtest_data` heading: SCAN's inventory of THIS repository (the
    grep word hit one of our own file names);
  * otherwise the line is listed in READ below with what it is about, read
    by hand from the line and the lines around it (the SCAN line numbers of
    the evidence are in the text).

Usage: python3 gen_unmapped_review.py   (rewrites the block; the test
`test_every_unmapped_line_is_reviewed_in_the_table` checks the rows).
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCAN = ROOT / "docs/DATA/SCAN_2026-09-21_tools.md"
TABLE = HERE / "opponents" / "CONSIDERED.md"
BEGIN, END = "<!-- 写せなかった行ここから -->", "<!-- 写せなかった行ここまで -->"
INVENTORY = ("## src/bot", "## scripts", "## tests", "## docs", "## backtest_data")

BT = ("道具 `bt` の行(SCAN 1618 行「5. [深掘り] `bt`」の節)。`bt` は道具台帳に番号が無い"
      "(`awk -F'\\t' '$2==\"bt\"' docs/DATA/tools_catalog.tsv | wc -l` → 0)ので、候補の集まり(台帳の番号で数える)に入らない。"
      "行の中身は「終値の DataFrame は入るが、約定・清算のような明細を入れる形ではない」= P0-3 の型のうち足しか受けない。"
      "候補にしたとしても、足を受ける能力は 1 Basana の p3-bar が正解と一致(`survey_results/opp_basana.tsv`)で上位互換。"
      "台帳から抜けていることはリードに返す")
READ = {
    ("P0-3", 1803): BT,
    ("P0-3", 1849): BT,
    ("P0-3", 6850): BT + "(6850 行は 1848・1849 行の逐語の引用)",
    ("P0-5", 563): "調査の手順の文(導入前の検査と導入の順序。語「順序」に当たった)。道具の機構を書いていない",
    ("P0-5", 1612): "SCAN の候補の一覧の並べ方の説明(「発見順」。語「順序」に当たった)。道具を指さない",
    ("P0-5", 2100): "同上(1612 行と同じ文。次の回の候補の一覧の頭)",
    ("P0-5", 2412): "同上(1612 行と同じ文)",
    ("P0-5", 2721): "同上(1612 行と同じ文)",
    ("P0-5", 2980): "同上(1612 行と同じ文)",
    ("P0-5", 5015): "調査の回の起動の指定の引用(「委任文 §2 の順序のとおり」。語「順序」に当たった)。道具を指さない",
    ("P0-5", 5022): "同上(5015 行と同じ引用)",
    ("P0-7", 7520): "段の表の書き方の規則(「段(機構) = 差し替えれば届く高さ」。語「差し替え」に当たった)。道具を指さない",
    ("P0-7", 7532): "段(機構)に数える条件の定義(語「差し替え」に当たった)。道具を指さない",
}


def unmapped() -> list[tuple[str, int, str]]:
    seen, out = set(), []
    for ln in (HERE / "pool.tsv").read_text(encoding="utf-8").splitlines():
        if ln.startswith("# P0-"):
            vp, n, head = ln[2:].split("\t", 2)
            if (vp, int(n)) not in seen:
                seen.add((vp, int(n)))
                out.append((vp, int(n), head))
    return sorted(out, key=lambda x: (x[0], x[1]))


def heading_of(lines: list[str], n: int) -> str:
    for i in range(n - 1, -1, -1):
        if lines[i].startswith("## "):
            return lines[i]
    return ""


def render() -> str:
    lines = SCAN.read_text(encoding="utf-8").splitlines()
    rows = []
    for vp, n, head in unmapped():
        h = heading_of(lines, n)
        if (vp, n) in READ:
            kind, why = ("道具の行(台帳の外)" if READ[(vp, n)] is BT or READ[(vp, n)].startswith(BT) else "調査の手順・規則の文"), READ[(vp, n)]
        elif h.startswith(INVENTORY):
            kind = "当方のリポジトリの一覧"
            why = (f"SCAN が当方の道具立てを数えた一覧の行(見出し「{h[3:].strip()}」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない")
        else:
            raise SystemExit(f"{vp} {n}: not in READ and not under an inventory heading; read it and add it to READ")
        cell = head.replace("|", "\\|")[:60]
        rows.append(f"| {vp} | {n} | {cell} | {kind} | {why} |")
    out = [BEGIN, "",
           "`gen_unmapped_review.py` が書く(手で直さない)。`pool.tsv` の「# unmapped」の行を、観点と SCAN の行の組ごとに 1 行ずつ(同じ行が語の違う grep で 2 度当たったものは 1 行)。",
           "",
           "| 観点 | SCAN の行 | 行の頭 | 種類 | 扱いと理由 |",
           "|---|---|---|---|---|", *rows, "", END]
    return "\n".join(out)


def main() -> None:
    text = TABLE.read_text(encoding="utf-8")
    block = render()
    if BEGIN in text and END in text:
        text = text[: text.index(BEGIN)] + block + text[text.index(END) + len(END):]
    else:
        raise SystemExit(f"markers {BEGIN} / {END} are missing in {TABLE}")
    TABLE.write_text(text, encoding="utf-8")
    print(f"wrote {len(unmapped())} rows")


if __name__ == "__main__":
    main()
