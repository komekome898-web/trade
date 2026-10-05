#!/usr/bin/env python3
"""分析の文書の D2〜D7 の表から、前半・後半の区間がどちらも 0 の同じ側にある行を拾う(後からの検め)。

目的: D9b で観察を手で挙げた後に、「両半分で同じ側」の行を手で読み落としていないかを機械で突き合わせる。
観察を挙げる道具ではない(拾った行を観察にするかは手で決める。カード 9 の D9b の突き合わせの使い方)。
経緯: オーナーの指示 L-705「**今日の分析方法(分析スキル・アドバイザーfableとの2人作業・なぜ分解と台帳記入)を
再利用可能な仕組み化してほしい。要件を詰めたいので案を出してください。**」と L-706「**1.y 2.y だが、
アドバイザー含め渡す情報はどうする？今回は何を渡した？ 3.y**」。案は
`docs/DISCUSSIONS/2026-10-05_analysis_mechanism/PROPOSAL.md` §4 案 A の 3(作業用の一時置き場の
`local_effects.py` を repo に移し、試験を付ける)。

    python3 scripts/analysis/local_effects.py <分析の文書.md> [...]

拾い方:
- 対象の節は「### 当てたこと(D2)」〜「### 当てたこと(D7)」だけ。
- 表の見出しの行 = 「|」で始まり、「前半」と「後半」の両方の語を含み、区間を含まない行。その表の列のうち、
  見出しが「前半」で始まる最初の列と「後半」で始まる最初の列を使う。
- 区間の書き方は「値 [下, 上]」(例 `+5.99 [+1.15, +10.38]`)。符号は + / - / −、桁区切りの「,」、末尾の % を読む。
- 拾う行 = 前半と後半の両方の列に区間があり、両方とも 下 > 0、または両方とも 上 < 0。区間が 0 を含む・端が
  ちょうど 0・片方の半分だけ同じ側の行は拾わない。

限界(一時置き場の版と同じ。拾えない行があるので、拾った数を「全部」と書かない):
- 縦長の表(前半・後半が列でなく行に並ぶ表。例: 「| 前半 | +1.2 [+0.3, +2.0] |」「| 後半 | … |」の 2 行)の
  半分は拾わない。
- D1 の表(年ごと・前半後半の全体の表)は拾わない。D8・D9・D9b・D10 も見ない。
- 見出しの行に「前半」「後半」の両方が無い表、区間が「値 [下, 上]」でない書き方(「下〜上」、括弧の無い区間など)は拾わない。
- 列の数が見出しと違う行は飛ばす(例: セルの中に縦棒 `|g|` を書いた行。カード 6 で列が壊れた形)。
- 前半・後半の列が 2 組以上ある表(2 本の区切りを並べた表など)は、最初の組しか見ない。
"""
from __future__ import annotations

import re
import sys

STEPS = ("D2", "D3", "D4", "D5", "D6", "D7")
SEC = re.compile(r"^### 当てたこと\(([^)]+)\)")
_N = r"[+\-−]?\d[\d,]*\.?\d*"
SEP = re.compile(r"^\|\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
IV = re.compile(rf"({_N})\s*%?\s*\[\s*({_N})\s*%?\s*,\s*({_N})\s*%?\s*\]")


def num(s: str) -> float:
    return float(s.replace("−", "-").replace(",", ""))


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def scan(text: str) -> tuple[int, list[tuple[str, str, str, str]]]:
    """(前半・後半の列がある表の行の数, [(節, 行の頭, 前半の区間, 後半の区間)])。"""
    sec: str | None = None
    hdr: list[str] | None = None
    n_rows = 0
    hits = []
    for line in text.split("\n"):
        m = SEC.match(line)
        if m:
            sec, hdr = m.group(1), None
            continue
        if line.startswith("## "):
            sec, hdr = None, None
            continue
        if sec not in STEPS:
            continue
        if not line.startswith("|"):
            hdr = None
            continue
        if "前半" in line and "後半" in line and not IV.search(line) and not SEP.match(line.strip()):
            hdr = _cells(line)
            continue
        if SEP.match(line.strip()) or hdr is None:
            continue
        cells = _cells(line)
        if len(cells) != len(hdr):
            continue
        fi = [i for i, h in enumerate(hdr) if h.startswith("前半")]
        se = [i for i, h in enumerate(hdr) if h.startswith("後半")]
        if not fi or not se:
            continue
        n_rows += 1
        a, b = IV.search(cells[fi[0]]), IV.search(cells[se[0]])
        if not a or not b:
            continue
        la, ha, lb, hb = num(a.group(2)), num(a.group(3)), num(b.group(2)), num(b.group(3))
        if (la > 0 and lb > 0) or (ha < 0 and hb < 0):
            hits.append((sec, " / ".join(cells[:3])[:110], a.group(0), b.group(0)))
    return n_rows, hits


def main(argv: list[str] | None = None) -> int:
    paths = sys.argv[1:] if argv is None else argv
    if not paths:
        print("使い方: local_effects.py <分析の文書.md> [...]", file=sys.stderr)
        return 2
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            n_rows, hits = scan(fh.read())
        print(f"== {p}: 前半・後半の列がある表の行 {n_rows}、両半分で同じ側 {len(hits)}")
        for s, head, a, b in hits:
            print(f"   {s} | {head} | 前半 {a} | 後半 {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
