#!/usr/bin/env python3
"""分析の文書の「相方の検め」の節(骨組みの節 R)が、知見の文(D10)を書いた後に空のままでないかを見る検査。

経緯(オーナーの逐語): L-706「**3.y**」(案 `docs/DISCUSSIONS/2026-10-05_analysis_mechanism/PROPOSAL.md` §5 (3)
押し出しの門の (iii)「相方の節が空でない」への yes)/ L-711「**案1で**」(押し出しの門の (iii) もここで入れる)。

    python3 scripts/analysis/check_partner.py [ファイル ...]
    # 既定は docs/ANALYSIS/ の下の .md 全部(下の階層も。README.md を除く)

規則:
- 骨組みの節 R(`<!-- step:R -->`)がある文書だけを見る。無い文書は「R 節あり」に数えずに飛ばす。
  ただし「## R 」の見出しがあって `<!-- step:R -->` の印が無い文書は問題(R 節ありに数える)。
- R 節があって「### 当てたこと(D10)」の見出しが無い文書は問題(そのうえで下の (a)〜(c) も見る)。
- 「当てたこと(D10)」が埋まっていれば(「(未記入)」でない)、次を求める:
  (a)「当てたこと(R)」が「(未記入)」でない
  (b) 節 R の中に、見出し `| # | 時点 | 相方 | 渡し書き | 記録 | 応答 |` の表があり、その後の 1 列目が数字の行が
      1 行以上ある。数えない行: スキルの写し(<!-- step:R --> 〜 <!-- /step:R -->)・「>」で始まる行・``` と ~~~ の
      囲みの中・4 字以上(またはタブで)字下げした行・<!-- --> の注釈の中
  (c) 各行の「記録」の列:
      - 「無し(遡り」で始まる遡りの行は、時点の列が「(遡り)」で、かつ文書の名前の日付(先頭の YYYY-MM-DD)が
        2026-10-05 以前のときだけ通す(手順 R の前に書かれた文書だけ。リードの決定 2026-10-06)。それ以外は問題
      - それ以外は、バッククォートのパスが 1 つ以上あり、どれも、リポジトリの中(realpath が根の下)・通常のファイル・
        `docs/RESEARCH/partner/` の下・名前が `_reply.md` で終わる、の全部を満たすこと(リードの決定 2026-10-06)。
        パスが 1 つも無い(空・文だけ・パスでないバッククォートだけ)の行は問題
- 埋まり具合の判定は `partner_brief.py` の `is_filled` と同じ(骨組みの案内の行と空行を除いて何も無い、
  または「(未記入)」だけなら未記入)。

出力: 問題を 1 件 1 行、最後に「ファイル n・R 節あり m・問題 k」。問題が 1 つでもあれば終了コード 1。
渡したファイルが無ければ終了コード 2。

限界: セルの中の「|」(バッククォートの中を含む)は列を壊す。記録のファイルの中身(相方の出力の逐語か)は見ない。
注釈 <!-- と --> は行の頭と終わりで見る(行の途中に挟んだ注釈の外の文字は、その行ごと数えない)。
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GLOB = os.path.join(ROOT, "docs", "ANALYSIS", "**", "*.md")
HEADER = ["#", "時点", "相方", "渡し書き", "記録", "応答"]
AT, REC = HEADER.index("時点"), HEADER.index("記録")
RETRO = "無し(遡り"  # 「無し(遡り)」と「無し(遡り。理由…)」の両方を受ける(2026-10-06、9 枚の遡りの行の形)
RETRO_AT = "(遡り)"
RETRO_UNTIL = date(2026, 10, 5)  # 手順 R(コミット 14b8855e)より前に書かれた文書の日付の上限
PARTNER_DIR = ("docs", "RESEARCH", "partner")
REPLY_SUFFIX = "_reply.md"


def _load_pb():
    spec = importlib.util.spec_from_file_location("partner_brief", os.path.join(HERE, "partner_brief.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pb = _load_pb()


def cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def r_region(text: str) -> list[str]:
    """節 R の行: <!-- step:R --> の前の「## 」の見出しの次の行から、写しの閉じの後の次の「## 」の手前まで。
    写し・「>」の行・``` と ~~~ の囲み・4 字下げ(タブ)の行・<!-- --> の注釈の中は除く。"""
    lines = text.split("\n")
    i = lines.index("<!-- step:R -->")
    start = next((j + 1 for j in range(i, -1, -1) if lines[j].startswith("## ")), 0)
    out, in_quote, fence, comment = [], False, None, False
    for ln in lines[start:]:
        if ln.startswith("## "):
            break
        if ln == "<!-- step:R -->":
            in_quote = True
            continue
        if ln == "<!-- /step:R -->":
            in_quote = False
            continue
        if in_quote or ln.lstrip().startswith(">"):
            continue
        s = ln.lstrip()
        if fence is None and (s.startswith("```") or s.startswith("~~~")):
            fence = s[:3]
            continue
        if fence is not None:
            if s.startswith(fence):
                fence = None
            continue
        if comment:
            if "-->" in ln:
                comment = False
            continue
        if s.startswith("<!--"):
            comment = "-->" not in s[4:]
            continue
        if ln.startswith("    ") or ln.startswith("\t"):
            continue
        out.append(ln)
    return out


def table_rows(region: list[str]) -> list[list[str]]:
    """見出しが HEADER の表の、1 列目が数字の行。"""
    rows, in_table = [], False
    for ln in region:
        if not ln.lstrip().startswith("|"):
            in_table = False
            continue
        c = cells(ln)
        if c == HEADER:
            in_table = True
            continue
        if in_table and re.fullmatch(r"\d+", c[0] or ""):
            rows.append(c)
    return rows


def doc_date(name: str | None) -> date | None:
    m = re.match(r"(\d{4}-\d{2}-\d{2})_", os.path.basename(name or ""))
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def record_problem(tok: str, repo: str) -> str | None:
    """記録のパスが通らない理由。通れば None。"""
    root = os.path.realpath(repo)
    real = os.path.realpath(pb.resolve(tok, repo))
    if os.path.commonpath([root, real]) != root:
        return "リポジトリの外"
    if not os.path.exists(real):
        return "無い"
    if not os.path.isfile(real):
        return "通常のファイルでない"
    rel = os.path.relpath(real, root).split(os.sep)
    if tuple(rel[:len(PARTNER_DIR)]) != PARTNER_DIR or len(rel) <= len(PARTNER_DIR):
        return "docs/RESEARCH/partner/ の下でない"
    if not rel[-1].endswith(REPLY_SUFFIX):
        return f"名前が {REPLY_SUFFIX} で終わらない"
    return None


def check_text(text: str, repo: str = ROOT, name: str | None = None) -> tuple[bool, list[str]]:
    """(R 節があるか, 問題の一覧)。name は文書のファイル名(遡りの行の日付を見る)。"""
    lines = text.split("\n")
    if "R" not in pb.steps_in(text):
        if any(ln.startswith("## R ") or ln == "## R" for ln in lines):
            return True, ["「## R 」の見出しがあるのに <!-- step:R --> の印が無い(骨組みの節でない)"]
        return False, []
    errs = []
    d10 = pb.is_filled(text, "D10")
    if d10 is None:
        errs.append("R 節があるのに「### 当てたこと(D10)」の見出しが無い")
    elif not d10:
        return True, []
    if not pb.is_filled(text, "R"):
        errs.append(f"D10 が埋まっているのに「当てたこと(R)」が{pb.EMPTY}(または見出しが無い)")
    rows = table_rows(r_region(text))
    if not rows:
        errs.append("節 R に相方の検めの表の行が無い(見出し `| " + " | ".join(HEADER) + " |` の後の、1 列目が数字の行)")
    dd = doc_date(name)
    for c in rows:
        rec = c[REC] if len(c) > REC else ""
        if rec.startswith(RETRO):
            at = c[AT] if len(c) > AT else ""
            if at != RETRO_AT:
                errs.append(f"表の行 {c[0]}: 遡りの行は時点の列が「{RETRO_AT}」のときだけ(「{at}」)")
            elif dd is None or dd > RETRO_UNTIL:
                errs.append(f"表の行 {c[0]}: 遡りの行は、文書の名前の日付が {RETRO_UNTIL} 以前の文書だけ(日付 {dd})")
            continue
        paths = [t.strip() for t in pb.BACKTICK.findall(rec) if pb.is_path(t.strip())]
        if not paths:
            errs.append(f"表の行 {c[0]}: 記録の列がバッククォートのパスでも「{RETRO}」で始まる文でもない(「{rec}」)")
        for tok in paths:
            why = record_problem(tok, repo)
            if why:
                errs.append(f"表の行 {c[0]}: 記録 `{tok}` が{why}(記録は docs/RESEARCH/partner/ の下の …{REPLY_SUFFIX})")
    return True, errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--repo", default=ROOT, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    paths = a.files or sorted(p for p in glob.glob(DEFAULT_GLOB, recursive=True)
                              if os.path.basename(p) != "README.md")
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        for p in missing:
            print(f"無い: {p}", file=sys.stderr)
        return 2
    m = k = 0
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            has_r, errs = check_text(fh.read(), a.repo, name=p)
        m += has_r
        for e in errs:
            print(f"{pb.shown(p)}: {e}")
        k += len(errs)
    print(f"ファイル {len(paths)}・R 節あり {m}・問題 {k}")
    return 1 if k else 0


if __name__ == "__main__":
    raise SystemExit(main())
