"""Check a backtest battery's CONSIDERED.md (unrunnable-candidate review table).

Delegation docs/DATA/delegations/20260923_backtest_env_prompt.md §3
("動かせない候補の検討と再現", 場面集の規則 6 and 9) states the rules in prose;
this script checks the mechanically checkable part and writes the aggregate
block, so the counts are never typed by hand.

Format it expects:
- each viewpoint is a `### 観点...` heading;
- each viewpoint has a line `動かせた候補: N 件(12 名前, 34 名前)` naming the runnable candidates by their
  catalogue number (`動かせた候補: 0 件` when none), and either a table whose header
  has the columns 候補 / 機構 / 実装 / 判断 / 理由 (a 段 column is optional),
  or a line `候補 0 件:` followed by the search command in backticks;
- the aggregate block sits between `<!-- 集計ここから -->` and `<!-- 集計ここまで -->`.

Usage:
  python3 scripts/check_bt_considered.py <CONSIDERED.md>          # check, exit 1 on errors
  python3 scripts/check_bt_considered.py <CONSIDERED.md> --write  # rewrite the aggregate block, then check
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

VERDICTS = ("再現した", "持たないと確認した", "スキップ: 明らかに弱い", "再現できない")
BLANK = {"", "(空欄)", "（空欄）", "-", "—", "空欄"}
BEGIN, END = "<!-- 集計ここから -->", "<!-- 集計ここまで -->"


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse(text: str):
    sections, cur = [], None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            cur = None
            if ln.startswith("### 観点"):
                cur = {"title": ln[4:].strip(), "line": i + 1, "rows": [], "runnable": None,
                       "zero": False, "tables": 0, "runnable_ids": None}
                sections.append(cur)
            i += 1
            continue
        if cur is not None:
            m = re.search(r"動かせた候補[:：]\s*(\d+)\s*件(?:[(（]([^)）]*)[)）])?", ln)
            if m:
                cur["runnable"] = int(m.group(1))
                cur["runnable_ids"] = re.findall(r"(?:^|[,、，]\s*)(\d+)\s", (m.group(2) or "") + " ")
            if re.search(r"候補\s*0\s*件[:：]", ln) and "`" in ln:
                cur["zero"] = True
            if ln.startswith("|") and "判断" in ln and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1]):
                head = cells(ln)
                cur["tables"] += 1
                i += 2
                while i < len(lines) and lines[i].startswith("|"):
                    row = cells(lines[i])
                    cur["rows"].append((i + 1, dict(zip(head, row + [""] * (len(head) - len(row)))), head))
                    i += 1
                continue
        i += 1
    return sections


def col(head: list[str], key: str) -> str | None:
    for h in head:
        if key in h:
            return h
    return None


def check(path: Path, text: str) -> list[str]:
    errs = []
    secs = parse(text)
    if not secs:
        errs.append("`### 観点` の見出しが 1 つも無い")
    for s in secs:
        where = f"{path}:{s['line']} 「{s['title']}」"
        if s["runnable"] is None:
            errs.append(f"{where}: 「動かせた候補: N 件」の行が無い(割合を出せない)")
        elif s["runnable"] != len(s["runnable_ids"] or []):
            errs.append(f"{where}: 「動かせた候補: {s['runnable']} 件」の括弧に台帳の番号つきの名前が {len(s['runnable_ids'] or [])} 件しか無い(番号 名前 を , で並べる)")
        if not s["tables"] and not s["zero"]:
            errs.append(f"{where}: 判断の列を持つ表も、「候補 0 件:」と検索のコマンド(` で囲む)も無い")
        seen_heads = set()
        for ln, r, head in s["rows"]:
            w = f"{path}:{ln}"
            if tuple(head) not in seen_heads:
                seen_heads.add(tuple(head))
                for need in ("候補", "機構", "実装", "判断", "理由"):
                    if not col(head, need):
                        errs.append(f"{w}: 表の見出しに「{need}」の列が無い")
            cand = r.get(col(head, "候補") or "", "")
            num = re.match(r"\s*(\d+)", cand)
            if num and s["runnable_ids"] and num.group(1) in s["runnable_ids"]:
                errs.append(f"{w}: 動かせた候補 {cand} が検討表(動かせなかった候補の表)に載っている")
            j = r.get(col(head, "判断") or "", "")
            why = r.get(col(head, "理由") or "", "")
            dan = r.get(col(head, "段") or "", None) if col(head, "段") else None
            v = next((x for x in VERDICTS if j.startswith(x)), None)
            if v is None or not re.fullmatch(r"[(（][^)）]*[)）]", j[len(v):].strip() or "()"):
                errs.append(f"{w}: 判断「{j}」が 4 つ(再現した / 持たないと確認した / スキップ: 明らかに弱い / 再現できない)のどれでもない")
                continue
            if v == "スキップ: 明らかに弱い":
                if "段が低い" not in why and "上位互換" not in why:
                    errs.append(f"{w}: スキップの理由が「段が低い」でも「上位互換」でもない")
                if dan is not None and dan.strip() in BLANK and "上位互換" not in why and "実装で確かめた段" not in why:
                    errs.append(f"{w}: 段(機構)が空欄なのに段を理由にスキップしている(実装で確かめた段を書く = 規則 6)")
            if v == "再現できない" and "危険" not in why and not ("(a)" in why and "(b)" in why):
                errs.append(f"{w}: 再現できない理由に (a) 書き写しと (b) 一次資料の両方で足りなかったことが無い(導入できないことは理由にならない。再現は一次資料どおりの最小の書き直し)")
            if v == "再現した":
                m = re.search(r"opponents/[\w./-]+\.py", why)
                if not m:
                    errs.append(f"{w}: 再現したのに再現のファイル(opponents/…py)が理由に無い")
                elif not (path.parent / m.group(0).split("opponents/", 1)[1]).exists():
                    errs.append(f"{w}: 再現のファイル {m.group(0)} が無い")
            if v == "持たないと確認した" and not re.search(r"行|https?://", why):
                errs.append(f"{w}: 持たないと確認した根拠(書き写しの行か一次資料の URL)が無い")
    return errs


def aggregate(text: str) -> str:
    secs = parse(text)
    out = [BEGIN, "", "## 集計(`scripts/check_bt_considered.py --write` が書く。手で直さない)", "",
           "| 観点 | 動かせた | 動かせない(検討表の行) | 動かせない割合 | 再現した | 持たないと確認した | スキップ | 再現できない |",
           "|---|---|---|---|---|---|---|---|"]
    tot = [0] * 6
    missing = []
    for s in secs:
        n = len(s["rows"])
        c = [sum(1 for _, r, h in s["rows"] if r.get(col(h, "判断") or "", "").startswith(v)) for v in VERDICTS]
        run = s["runnable"] if s["runnable"] is not None else 0
        ratio = f"{n / (n + run):.0%}" if n + run else "—"
        out.append(f"| {s['title']} | {run} | {n} | {ratio} | " + " | ".join(map(str, c)) + " |")
        for k, x in enumerate([run, n] + c):
            tot[k] += x
        missing += [f"{s['title']}: {r.get(col(h, '候補') or '', '')}" for _, r, h in s["rows"]
                    if r.get(col(h, "判断") or "", "").startswith("再現できない")]
    ratio = f"{tot[1] / (tot[0] + tot[1]):.0%}" if tot[0] + tot[1] else "—"
    out.append(f"| 計(観点ごとの延べ) | {tot[0]} | {tot[1]} | {ratio} | " + " | ".join(map(str, tot[2:])) + " |")
    out += ["", "再現もできなかった候補(圧倒の判定では「その候補とは比べていない」と候補名を付けて報告する):", ""]
    out += [f"- {m}" for m in missing] or ["- なし"]
    out += ["", END]
    return "\n".join(out)


def main() -> int:
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    block = aggregate(text)
    if "--write" in sys.argv:
        if BEGIN in text and END in text:
            text = text[: text.index(BEGIN)] + block + text[text.index(END) + len(END):]
        else:
            text = text.rstrip("\n") + "\n\n" + block + "\n"
        path.write_text(text, encoding="utf-8")
    errs = check(path, text)
    if not (BEGIN in text and END in text):
        errs.append(f"{path}: 集計の区画が無い(--write で書く)")
    elif text[text.index(BEGIN): text.index(END) + len(END)] != block:
        errs.append(f"{path}: 集計の区画が表と合っていない(--write で書き直す)")
    for e in errs:
        print("NG", e)
    print(f"{'OK' if not errs else 'NG'} 誤り {len(errs)} 件")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
