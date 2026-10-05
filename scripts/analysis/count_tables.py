#!/usr/bin/env python3
"""分析の文書の「### 当てたこと(X)」の節ごとに、表の数と表の行の数を数える(D9b の「見た表の数と行の数」用)。

目的: D9b で「何枚の表の何行を見て観察を挙げたか」を手で数えずに道具で出す(手の数え間違いが
カード 4・カード 8 で起きた。`docs/DISCUSSIONS/2026-10-05_analysis_mechanism/PROPOSAL.md` §2)。
経緯: オーナーの指示 L-705「**今日の分析方法(分析スキル・アドバイザーfableとの2人作業・なぜ分解と台帳記入)を
再利用可能な仕組み化してほしい。要件を詰めたいので案を出してください。**」と L-706「**1.y 2.y だが、
アドバイザー含め渡す情報はどうする？今回は何を渡した？ 3.y**」。案 A の 3(作業用の一時置き場の
`count_tables.py` を repo に移し、試験を付ける)。

    python3 scripts/analysis/count_tables.py <分析の文書.md> [...]

数え方:
- 節 = 「### 当てたこと(X)」の見出しから、次の「### 当てたこと(…)」または「## 」の見出しの手前まで。
  それより前(手順の写し)の表は数えない。
- 表 = 「|」で始まる行が続く塊で、2 行目が区切りの行(`|---|`・`|:-|` のように「-」とその前後の「:」だけのセル)のもの。区切りの行の無い塊は表と
  数えない。行の数 = 塊の行数 − 2(見出しと区切り)。
- 引用(「>」で始まる行)の中の表は数えない(「>」の行は塊を切る)。``` の囲みの中も数えない。
限界: 表の中身(空の行・同じ行の重複)は見ない。「当てたこと」の節の外(前置き・D9b の外の注)にある表は数えない。
"""
from __future__ import annotations

import re
import sys

SEC = re.compile(r"^### 当てたこと\(([^)]+)\)")
SEP = re.compile(r"^\|\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def count(text: str) -> dict[str, tuple[int, int]]:
    """{節の名前: (表の数, 行の数)} を、文書に出た順で返す。表の無い節も 0 で入れる。"""
    agg: dict[str, list[int]] = {}
    sec: str | None = None
    cur: list[str] = []
    fence = False

    def close() -> None:
        nonlocal cur
        if sec is not None and len(cur) >= 2 and SEP.match(cur[1].strip()):
            agg[sec][0] += 1
            agg[sec][1] += len(cur) - 2
        cur = []

    for line in text.split("\n"):
        if line.startswith("```"):
            close()
            fence = not fence
            continue
        if fence:
            continue
        m = SEC.match(line)
        if m:
            close()
            sec = m.group(1)
            agg.setdefault(sec, [0, 0])
            continue
        if line.startswith("## "):
            close()
            sec = None
            continue
        if line.startswith("|"):
            cur.append(line)
        else:
            close()
    close()
    return {k: (v[0], v[1]) for k, v in agg.items()}


def main(argv: list[str] | None = None) -> int:
    paths = sys.argv[1:] if argv is None else argv
    if not paths:
        print("使い方: count_tables.py <分析の文書.md> [...]", file=sys.stderr)
        return 2
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            res = count(fh.read())
        print(f"== {p}")
        for s, (t, r) in res.items():
            print(f"{s}: 表 {t}・行 {r}")
        print(f"計: 表 {sum(t for t, _ in res.values())}・行 {sum(r for _, r in res.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
