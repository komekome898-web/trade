#!/usr/bin/env python3
"""分析の文書に残った仮置き(「ここに書き足す」「番号を書き足す」「後で書き足す」の類)を探す検査。

目的: 「この番号は後で書き足す」と書いた仮置きが 4 枚(カード 1・2・3・9 の D9b)に残り、最後に手で検索して
埋めた(`docs/DISCUSSIONS/2026-10-05_analysis_mechanism/PROPOSAL.md` §2、要件 R4「仮置きが残らない」)。
残ったままの文書をコミットしないよう、機械で止める(`scripts/analysis/commit_gate.sh` が呼ぶ)。
経緯: オーナーの指示 L-705「**今日の分析方法(分析スキル・アドバイザーfableとの2人作業・なぜ分解と台帳記入)を
再利用可能な仕組み化してほしい。要件を詰めたいので案を出してください。**」と L-706「**1.y 2.y だが、
アドバイザー含め渡す情報はどうする？今回は何を渡した？ 3.y**」。案 A の 3(仮置きの検索)。

    python3 scripts/analysis/check_placeholders.py [ファイル ...]
    # 既定は docs/ANALYSIS/ の下の .md 全部(下の階層も。この台本の置き場から解く)

終了コード 0 = 仮置き 0 件、1 = 1 件以上(「パス:行番号: 語 | 行」を 1 件 1 行で出す)、2 = 渡したファイルが無い。

仮置きと数えるもの(PATTERNS):
- 「書き足す・書き足します・書きたす・書きたします・埋める・埋めます・追記する・追記します」の前に、
  ここに / ここへ / 番号を / 番号は / 後で / あとで / 後ほど / のちほど が同じ文の中(句点までの 20 字以内)にあるもの。
  過去の形(「書き足した」「埋めた」「追記した」)は記録なので数えない。
- 「後で・あとで・後ほど・のちほど」のすぐ後(間は空白だけ)の「書く・書きます・追記」(「追記した」は数えない)。
  「書く」は離れていると説明の文(「D9b を書いた後で表を書く」)と区別できないので、すぐ後だけ。
- TODO・TBD・FIXME(大文字。前後が英字でないもの)。
- ファイルの終わりで ``` の囲みが開いたまま(閉じ忘れると、そこから後の仮置きが見えなくなる)。開いた行を出す。
「後で」だけ・「埋める」だけは数えない(スキルの写しに「崩れたと分かった後で」、手順の文に「✕ を埋める」がある)。

数えないところ:
- かぎ括弧「…」の中(引用された語。入れ子は深さで数える。閉じずに行が終わったら行末まで括弧の中)
- 引用の行(「>」で始まる行。スキルの本文の写し)
- ``` の囲みの中
限界: 語の一致で数える。上の語を使わずに書いた仮置き(「(未定)」「追って」など)と、前置きの語から 21 字以上
離れた動詞は数えない。二重かぎ括弧『…』の中の語は数える。字下げした ``` と ~~~ は囲みと見ない。骨組みの空の欄
「(未記入)」は数えない。
"""
from __future__ import annotations

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_GLOB = os.path.join(ROOT, "docs", "ANALYSIS", "**", "*.md")
_LEAD = r"(?:ここに|ここへ|番号を|番号は|後で|あとで|後ほど|のちほど)"
_LATER = r"(?:後で|あとで|後ほど|のちほど)"
_VERB = r"(?:書き[足た](?:す|します)|埋め(?:る|ます)|追記(?:する|します))"
PATTERNS = (
    re.compile(_LEAD + r"[^。\n]{0,20}?" + _VERB),
    re.compile(_LATER + r"\s*(?:書く|書きます|追記(?!し))"),
    re.compile(r"(?<![A-Za-z])(?:TODO|TBD|FIXME)(?![A-Za-z])"),
)
UNCLOSED = "``` の囲みが閉じていない(この行から終わりまで検査できない)"


def strip_quoted(line: str) -> str:
    """かぎ括弧「…」の中を空白に置き換えた行(列の位置は保つ)。"""
    out, depth = [], 0
    for ch in line:
        if ch == "「":
            depth += 1
            out.append(" ")
        elif ch == "」" and depth > 0:
            depth -= 1
            out.append(" ")
        else:
            out.append(" " if depth > 0 else ch)
    return "".join(out)


def find(text: str) -> list[tuple[int, str, str]]:
    """[(行番号, 当たった語, 行)]。"""
    hits = []
    fence = False
    opened = (0, "")
    for ln, line in enumerate(text.split("\n"), 1):
        if line.startswith("```"):
            fence = not fence
            opened = (ln, line)
            continue
        if fence or line.lstrip().startswith(">"):
            continue
        bare = strip_quoted(line)
        for pat in PATTERNS:
            for m in pat.finditer(bare):
                hits.append((ln, m.group(0), line))
    if fence:
        hits.append((opened[0], UNCLOSED, opened[1]))
    return sorted(hits, key=lambda h: h[0])


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    paths = args or sorted(glob.glob(DEFAULT_GLOB, recursive=True))
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        for p in missing:
            print(f"無い: {p}", file=sys.stderr)
        return 2
    n = 0
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            hits = find(fh.read())
        shown = os.path.relpath(p, ROOT) if os.path.abspath(p).startswith(ROOT + os.sep) else p
        for ln, word, line in hits:
            print(f"{shown}:{ln}: {word} | {line.strip()[:160]}")
        n += len(hits)
    print(f"ファイル {len(paths)}・仮置き {n}")
    return 1 if n else 0


if __name__ == "__main__":
    raise SystemExit(main())
