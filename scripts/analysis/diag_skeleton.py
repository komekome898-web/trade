#!/usr/bin/env python3
"""分析の文書の骨組みを作る(分析のスキル `.claude/skills/analysis-lens` の「呼び出したら最初にすること」、L-694)。

骨組み = スキル第 2 部の手順(P・D0・D8・D1・D1b・D2〜D7・D9・D10、スキルに書かれた順)ごとの節。各節の頭に、
その手順のスキルの本文をそのまま引用で写し、その下に「当てたこと」の欄を置く。手順をやる瞬間に手順の文が
書いている文書の中にあるようにするため。

分析の文書は `docs/ANALYSIS/<日付>_<単位>.md` にだけ置く。フック `.claude/hooks/analysis_skeleton_gate.sh`
が、この場所への書き込みで、手順の節が欠けた・写しがスキルの本文と違う内容を止める。

    python3 scripts/analysis/diag_skeleton.py --unit <単位の名前> [--date YYYY-MM-DD]
    python3 scripts/analysis/diag_skeleton.py --refresh docs/ANALYSIS/<ファイル>.md   # スキルの改訂の後、写しだけを今の本文に入れ替える

写しの抜き出し方(フックと同じ): スキルの `## P ` の見出しから `## 道具` の見出しの手前までを、`## ` の見出しで
区切る。手順の名前 = 見出しの最初の語。本文 = 見出しの次の行から次の見出しの手前まで(前後の空行は除く)。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL = os.path.join(ROOT, ".claude", "skills", "analysis-lens", "SKILL.md")
OUT_DIR = os.path.join(ROOT, "docs", "ANALYSIS")
EMPTY = "(未記入)"


def skill_steps(path: str = SKILL) -> list[tuple[str, str, list[str]]]:
    """[(手順の名前, 見出しの行, 本文の行)] をスキルに書かれた順で返す。"""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## P "))
    end = next(i for i, ln in enumerate(lines) if ln.startswith("## 道具"))
    steps, cur = [], None
    for ln in lines[start:end]:
        if ln.startswith("## "):
            if cur:
                steps.append(cur)
            cur = (ln[3:].split()[0], ln, [])
        elif cur:
            cur[2].append(ln)
    if cur:
        steps.append(cur)
    out = []
    for name, head, body in steps:
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        out.append((name, head, body))
    return out


def quote(body: list[str]) -> list[str]:
    return [("> " + ln) if ln.strip() else ">" for ln in body]


def step_block(name: str, head: str, body: list[str]) -> list[str]:
    return [head, "", f"<!-- step:{name} -->", *quote(body), f"<!-- /step:{name} -->", "",
            f"### 当てたこと({name})", "", "打ったコマンドと出力の在処 / 当てないなら理由 / 分かれ道で止めたなら「止めた: <分かれ道>」", "",
            EMPTY, ""]


def skill_state(path: str = SKILL) -> str:
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if ln.startswith("状態:"):
                return ln.strip()
    return "状態: 不明"


def new_doc(unit: str, date: str) -> str:
    now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")
    L = [f"# 診断 — {unit}", "",
         f"- 単位: {unit}(1 回のスキルの呼び出しで扱うのはこの 1 単位だけ。次の単位はスキルを呼び直してから)",
         f"- 骨組みを作った時刻: {now}(`scripts/analysis/diag_skeleton.py`)",
         f"- スキル: `.claude/skills/analysis-lens` の{skill_state()}",
         "- 各節の引用はスキルの本文の写し。手順は上から 1 つずつ、引用を読み直してから「当てたこと」を書く。",
         "  引用を消す・書き換える書き込みはフック `analysis_skeleton_gate.sh` が止める。", ""]
    for name, head, body in skill_steps():
        L += step_block(name, head, body)
    return "\n".join(L)


def refresh(path: str) -> str:
    """写し(<!-- step:X --> 〜 <!-- /step:X -->)を今のスキルの本文に入れ替える。当てたことの欄は残す。
    スキルに手順が足された後(L-702 の D9b など)、文書に無い節は、スキルの順の位置(次にある節の見出しの手前、
    次が無ければ文書の終わり)に、写しと空の「当てたこと」の欄で足す。"""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    steps = skill_steps()
    names = [s[0] for s in steps]
    for i, (name, head, body) in enumerate(steps):
        if f"<!-- step:{name} -->" in text:
            continue
        block = "\n".join(step_block(name, head, body))
        nxt = next((n for n in names[i + 1:] if f"<!-- step:{n} -->" in text), None)
        if nxt is None:
            text = text.rstrip("\n") + "\n\n" + block
            continue
        at = text.index(f"<!-- step:{nxt} -->")
        at = text.rindex("\n## ", 0, at) + 1
        text = text[:at] + block + "\n" + text[at:]
    for name, head, body in steps:
        pat = re.compile(rf"<!-- step:{re.escape(name)} -->\n.*?<!-- /step:{re.escape(name)} -->", re.S)
        text = pat.sub(lambda m: "\n".join([f"<!-- step:{name} -->", *quote(body), f"<!-- /step:{name} -->"]), text, count=1)
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--unit")
    g.add_argument("--refresh")
    ap.add_argument("--date", default=None)
    a = ap.parse_args(argv)
    if a.refresh:
        text = refresh(a.refresh)
        with open(a.refresh, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(a.refresh)
        return 0
    if not re.fullmatch(r"[0-9A-Za-z_\-]+", a.unit):
        print("単位の名前は英数字・_・- だけ(ファイル名に使う)", file=sys.stderr)
        return 1
    date = a.date or datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{date}_{a.unit}.md")
    if os.path.exists(out):
        print(f"既にある: {os.path.relpath(out, ROOT)}(続きはその文書に書く)", file=sys.stderr)
        return 1
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(new_doc(a.unit, date))
    print(os.path.relpath(out, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
