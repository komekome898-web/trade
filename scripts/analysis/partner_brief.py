#!/usr/bin/env python3
"""分析の相方(advisor の道具、またはそれが無い会話での fable の相方)に渡す「渡し書き」を作る。

経緯(オーナーの逐語): L-705「**今日の分析方法(分析スキル・アドバイザーfableとの2人作業・なぜ分解と台帳記入)を
再利用可能な仕組み化してほしい。**」/ L-706「**アドバイザー含め渡す情報はどうする？**」/ L-707「**「夜の文書の読み」
この文を入れると、全ての夜の作業の読みが対象になって必要な情報が渡らない可能性があります。なくしてください。**」/
L-711「**案1で**」。渡す一覧は `docs/DISCUSSIONS/2026-10-05_analysis_mechanism/PROPOSAL.md` §6.2。

    python3 scripts/analysis/partner_brief.py --doc docs/ANALYSIS/<文書>.md --at {P,D9b,D10,push} \\
        --done "<この単位の完了の形(オーナーの逐語)>" [--out-dir docs/RESEARCH/partner]

書く先: <out-dir>/<文書の名前(拡張子なし)>/<通し番号 2 桁>_<at>_brief.md(通し番号 = その置き場の既存の渡し書きの数 + 1。
その番号のファイルが既にあれば空くまで 1 ずつ増やす。上書きしない)。標準出力に、書いたパス・行数・sha256 の先頭 12 字。

渡し書きの中身(この順):
 ① 依頼の文: `.claude/skills/analysis-lens/PARTNER_REQUEST.md` の「## 依頼」「## 返し方」の本文をファイルから写す
 ② 時点: --at ごとの「今ここで見てほしいこと」
 ③ 目的: `docs/PROJECT_GOAL.md` の最初の「最終目標」の段落、`docs/OWNER_STATUS.md` の「いまの位置」を含む行、--done の文
 ④ オーナーの観点(案 §6.2 ③): 時点の節のスキルの写し(文書の <!-- step:X --> 〜 <!-- /step:X --> の中。advisor でない
    相方にも手順の決まりが渡るように)と、指摘の資産の在処(パスだけ。中身は写さない)
 ⑤ 対象: 時点に合う節(P → P、D9b → D9b、D10 → D10、push → D9b と D10)の、スキルの写しの閉じ(<!-- /step:X -->)の後から
    次の「## 」の見出しの手前までをそのまま写す。その中のバッククォートのパスと有無、K 番号(K-数字 3 桁)ごとの
    知見台帳の行の全文
 ⑥ 手順の履歴: 文書の全部の節の埋まり具合と、`git log --oneline` の最近 20 行。案 §6.2 ⑤ の「この単位で打ったコマンドの
    一覧」は、この道具には集める手立てが無いので、git log で代える(打ったコマンドそのものは渡らない)
 ⑦ 渡さないもの: 封印の置き場(docs/RESEARCH/WINDOW1/・backtest_data/phase2_sealed/)と過去の検証結果

止めるもの(終了コード 1、理由を標準エラーに。何も書かない):
- 文書に骨組みの節(<!-- step:X -->)が 1 つも無い / 時点に要る節が無い / その節の「当てたこと」が「(未記入)」
- --done が空
- 封印(リードの決定 2026-10-06): 組み立てた渡し書きの全文(① の依頼の文と ⑦ の決まった文を除く。囲みの中・台帳の行・
  git log の件名を含む)を語に切り、「/」か「\\」を含む語ごとに、そのままの形と posixpath.normpath で畳んだ形
  (// ./ ../)を casefold して、`docs/research/window1` か `backtest_data/phase2_sealed` を含めば止める。
  ファイルの有無の確かめ(④ ⑤)は、この検めを通った後にだけ行う(封印の置き場のファイルには触れない)

限界: 語の切れ目は空白と括弧・句読点・バッククォート・「|」など。全角の「／」で書いたパスや、語の途中で改行したパスは
見ない。window1 で始まる別の名前(window10 など)も止める側に数える。① と ⑦ は決まった文なので検めない。
過去の検証結果(全捨て、L-019)は機械では見分けられないので、⑦ に書いて相方に頼むだけ。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import posixpath
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REQUEST = os.path.join(ROOT, ".claude", "skills", "analysis-lens", "PARTNER_REQUEST.md")
GOAL = os.path.join(ROOT, "docs", "PROJECT_GOAL.md")
STATUS = os.path.join(ROOT, "docs", "OWNER_STATUS.md")
LEDGER = os.path.join(ROOT, "docs", "RESEARCH", "FINDINGS_LEDGER.md")
OUT_DIR = os.path.join(ROOT, "docs", "RESEARCH", "partner")

EMPTY = "(未記入)"
# 骨組み(`diag_skeleton.step_block`)が「当てたこと」の見出しの下に置く案内の行。埋まり具合の判定では数えない。
GUIDE = "打ったコマンドと出力の在処 / 当てないなら理由 / 分かれ道で止めたなら「止めた: <分かれ道>」"

AT_STEPS = {"P": ["P"], "D9b": ["D9b"], "D10": ["D10"], "push": ["D9b", "D10"]}
AT_FOCUS = {
    "P": "P の後: 前提と、それを測る出力の固定",
    "D9b": "D9b の後: 観察の粒度と漏れ",
    "D10": "D10 の前: 知見の文の型と次の手",
    "push": "押し出す前: 検査と仮置き",
}
OWNER_VIEW = ("docs/AUDITOR/OWNER_MODEL_SOURCE.md", "docs/AUDITOR/KNOWN_ANSWERS.md",
              "docs/AUDITOR/KNOWN_ANSWERS_ADDENDUM.md")
SEALED = ("docs/research/window1", "backtest_data/phase2_sealed")  # casefold した形
REQUEST_SECTIONS = ("依頼", "返し方")
NOT_FOUND = "根からは見つからない(相対の書き方かもしれない)"

STEP_OPEN = re.compile(r"^<!-- step:(\S+) -->$")
KNUM = re.compile(r"(?<![A-Za-z0-9])K-\d{3}(?!\d)")
BACKTICK = re.compile(r"`([^`\n]+)`")
BRIEF_NAME = re.compile(r"^(\d{2,})_.+_brief\.md$")
WORD = re.compile(r"[^\s`'\"()（）「」『』【】、。，,;；|<>\[\]{}*]+")


class Stop(Exception):
    """渡し書きを作らずに止める理由。"""


# ---------------------------------------------------------------- 文書の読み(check_partner.py と共有)

def steps_in(text: str) -> list[str]:
    """文書にある骨組みの節の名前(<!-- step:X --> の順)。"""
    return [m.group(1) for ln in text.split("\n") for m in [STEP_OPEN.match(ln)] if m]


def step_quote(text: str, name: str) -> list[str] | None:
    """<!-- step:name --> 〜 <!-- /step:name --> の中の行(スキルの写し)。無ければ None。"""
    lines = text.split("\n")
    try:
        i = lines.index(f"<!-- step:{name} -->")
        j = lines.index(f"<!-- /step:{name} -->", i)
    except ValueError:
        return None
    return lines[i + 1:j]


def section_after_quote(text: str, name: str) -> list[str] | None:
    """節 name の、スキルの写しの閉じ(<!-- /step:name -->)の次の行から、次の「## 」の見出しの手前(または文書の
    終わり)までの行。写しの閉じが無ければ None。"""
    lines = text.split("\n")
    close = f"<!-- /step:{name} -->"
    try:
        i = lines.index(close)
    except ValueError:
        return None
    out = []
    for ln in lines[i + 1:]:
        if ln.startswith("## "):
            break
        out.append(ln)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def applied(text: str, name: str) -> list[str] | None:
    """「### 当てたこと(name)」の見出しの次の行から、次の「## 」の見出しの手前までの行。見出しが無ければ None。"""
    lines = text.split("\n")
    head = f"### 当てたこと({name})"
    try:
        i = lines.index(head)
    except ValueError:
        return None
    out = []
    for ln in lines[i + 1:]:
        if ln.startswith("## "):
            break
        out.append(ln)
    return out


def is_filled(text: str, name: str) -> bool | None:
    """「当てたこと(name)」が埋まっているか。案内の行と空行を除いて何も無い、または「(未記入)」だけなら False。
    見出しが無ければ None。"""
    body = applied(text, name)
    if body is None:
        return None
    rest = [ln.strip() for ln in body if ln.strip() and ln.strip() != GUIDE]
    rest = [ln.replace("（", "(").replace("）", ")") for ln in rest]
    return not (not rest or rest == [EMPTY])


def backticks(lines: list[str]) -> list[str]:
    """``` の囲みの外の行の、バッククォートの中身(行ごとに拾う。囲みの中は数えない)。出た順、重複は除く。"""
    out, fence = [], False
    for ln in lines:
        if ln.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        for m in BACKTICK.finditer(ln):
            tok = m.group(1).strip()
            if tok and tok not in out:
                out.append(tok)
    return out


def is_path(tok: str) -> bool:
    if not tok or tok.startswith("-") or re.search(r"\s", tok):
        return False
    return "/" in tok or "\\" in tok or re.search(r"\.[A-Za-z0-9]{1,5}$", tok) is not None


def sealed_words(text: str) -> list[str]:
    """封印の置き場を指す語(「/」か「\\」を含む語を、そのままと normpath で畳んだ形の両方で casefold して見る)。"""
    hits = []
    for w in WORD.findall(text):
        if "/" not in w and "\\" not in w:
            continue
        raw = w.replace("\\", "/")
        forms = (raw.casefold(), posixpath.normpath(raw).casefold())
        if any(s in f for f in forms for s in SEALED) and w not in hits:
            hits.append(w)
    return hits


def resolve(tok: str, repo: str) -> str:
    p = tok.split("#")[0]
    p = re.sub(r":\d+(?:[-–]\d+)?$", "", p)
    return p if os.path.isabs(p) else os.path.join(repo, p)


# ---------------------------------------------------------------- 渡し書きの部品

def _load_cfl():
    path = os.path.join(ROOT, "scripts", "check_findings_ledger.py")
    spec = importlib.util.spec_from_file_location("check_findings_ledger", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ledger_rows(ledger_text: str, kids: list[str]) -> dict[str, list[str] | None]:
    """K 番号ごとの台帳の行の全文(見出しの行から、次の「#」で始まる行の手前まで)。台帳に無ければ None。
    行の見分けは台帳の検査(`scripts/check_findings_ledger.py` の `_parse`)と同じ(書式の見本の囲みは数えない)。"""
    obs, _, _ = _load_cfl()._parse(ledger_text)
    lines = ledger_text.splitlines()
    out: dict[str, list[str] | None] = {}
    for k in kids:
        row = obs.get(k)
        if row is None:
            out[k] = None
            continue
        start = row["_line"] - 1
        block = [lines[start]]
        for ln in lines[start + 1:]:
            if ln.startswith("#"):
                break
            block.append(ln)
        while block and not block[-1].strip():
            block.pop()
        out[k] = block
    return out


def request_sections(path: str) -> dict[str, list[str]]:
    """PARTNER_REQUEST.md の「## 依頼」「## 返し方」の本文(見出しの次の行から次の「## 」の手前まで、前後の空行を除く)。"""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    out = {}
    for name in REQUEST_SECTIONS:
        head = f"## {name}"
        if head not in lines:
            raise Stop(f"依頼の文のファイル {path} に「{head}」の見出しが無い")
        i = lines.index(head)
        body = []
        for ln in lines[i + 1:]:
            if ln.startswith("## "):
                break
            body.append(ln)
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        out[name] = body
    return out


def goal_paragraph(path: str) -> list[str] | None:
    """最初に「最終目標」を含む行。見出しなら見出しの直後の段落、見出しでなければその行を含む段落。無ければ None。"""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    idx = next((i for i, ln in enumerate(lines) if "最終目標" in ln), None)
    if idx is None:
        return None
    if lines[idx].startswith("#"):
        j = idx + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        start = j
    else:
        start = idx
        while start > 0 and lines[start - 1].strip() and not lines[start - 1].startswith("#"):
            start -= 1
    para = []
    for ln in lines[start:]:
        if not ln.strip() or ln.startswith("#"):
            break
        para.append(ln)
    return para or None


def status_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        return [ln.rstrip("\n") for ln in fh if "いまの位置" in ln]


def git_log(doc: str) -> list[str]:
    d = os.path.dirname(os.path.abspath(doc))
    try:
        p = subprocess.run(["git", "log", "--oneline", "-n", "20", "--", os.path.abspath(doc)], cwd=d,
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return [f"git の記録が無い({type(e).__name__})"]
    if p.returncode != 0:
        msg = (p.stderr.strip().splitlines() or ["理由不明"])[0]
        return [f"git の記録が無い(git log の終了コード {p.returncode}: {msg})"]
    out = p.stdout.rstrip("\n").split("\n") if p.stdout.strip() else []
    return out or ["git の記録が無い(この文書はまだコミットされていない)"]


def shown(path: str) -> str:
    a = os.path.abspath(path)
    return os.path.relpath(a, ROOT) if a.startswith(ROOT + os.sep) else path


# ---------------------------------------------------------------- 組み立て

class _Exists:
    """ファイルの有無を、封印の検めの後まで確かめずに置いておく印。"""

    def __init__(self):
        self.items: list[tuple[str, str]] = []

    def mark(self, path: str, missing: str) -> str:
        self.items.append((path, missing))
        return f"\x00有無{len(self.items) - 1}\x00"

    def fill(self, text: str) -> str:
        for i, (path, missing) in enumerate(self.items):
            text = text.replace(f"\x00有無{i}\x00", "有る" if os.path.exists(path) else missing)
        return text


def build(doc: str, at: str, done: str, *, ledger: str = LEDGER, request: str = REQUEST, goal: str = GOAL,
          status: str = STATUS, repo: str = ROOT) -> str:
    if at not in AT_STEPS:
        raise Stop(f"--at は {', '.join(AT_STEPS)} のどれか(渡された: {at})")
    if not done or not done.strip():
        raise Stop("--done(この単位の完了の形、オーナーの逐語)が空")
    with open(doc, encoding="utf-8") as fh:
        text = fh.read()
    names = steps_in(text)
    if not names:
        raise Stop(f"{shown(doc)} に骨組みの節(<!-- step:X -->)が無い(`scripts/analysis/diag_skeleton.py` で作った文書だけを渡す)")
    sections: dict[str, list[str]] = {}
    quotes: dict[str, list[str]] = {}
    for s in AT_STEPS[at]:
        if s not in names:
            raise Stop(f"{shown(doc)} に節 {s} が無い(時点 {at} に要る)")
        f = is_filled(text, s)
        if f is None:
            raise Stop(f"{shown(doc)} の節 {s} に「### 当てたこと({s})」の見出しが無い")
        if not f:
            raise Stop(f"{shown(doc)} の「当てたこと({s})」が{EMPTY}(時点 {at} の渡し書きは、この節が埋まってから)")
        body = section_after_quote(text, s)
        q = step_quote(text, s)
        if body is None or q is None:
            raise Stop(f"{shown(doc)} の節 {s} に写しの閉じ <!-- /step:{s} --> が無い")
        sections[s] = body
        quotes[s] = q

    all_lines = [ln for b in sections.values() for ln in b]
    toks = backticks(all_lines)
    kids = []
    for ln in all_lines:
        for k in KNUM.findall(ln):
            if k not in kids:
                kids.append(k)
    with open(ledger, encoding="utf-8") as fh:
        rows = ledger_rows(fh.read(), kids)

    req = request_sections(request)
    para = goal_paragraph(goal)
    st = status_lines(status)
    now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")
    ex = _Exists()

    head = [f"# 渡し書き — {os.path.splitext(os.path.basename(doc))[0]} — 時点 {at}", "",
            f"- 文書: `{shown(doc)}`",
            f"- 時点: {at}",
            f"- 作った時刻: {now}(`scripts/analysis/partner_brief.py`)", ""]

    first = ["## ① 依頼の文", "", f"出所: `{shown(request)}` の「## 依頼」「## 返し方」(ファイルから写した)", ""]
    for name in REQUEST_SECTIONS:
        first += [f"### {name}", "", *req[name], ""]

    M = ["## ② 時点", "", f"今ここで見てほしいこと: {AT_FOCUS[at]}", ""]

    M += ["## ③ 目的", "", f"最終目標(`{shown(goal)}` の最初の「最終目標」の段落):", ""]
    M += [*(para if para else ["見つからない"]), ""]
    M += [f"いまの計画の段(`{shown(status)}` の「いまの位置」を含む行):", ""]
    M += [*(st if st else ["見つからない"]), ""]
    M += ["この単位の完了の形(オーナーの逐語、--done):", "", done.strip(), ""]

    M += ["## ④ オーナーの観点", ""]
    for s, q in quotes.items():
        M += [f"### 時点の節のスキルの写し({s}、文書の <!-- step:{s} --> 〜 <!-- /step:{s} --> の中)", "",
              "````markdown", *q, "````", ""]
    M += ["### 指摘の資産の在処(中身は写さない。必要なところを読む)", ""]
    for p in OWNER_VIEW:
        M.append(f"- `{p}`({ex.mark(os.path.join(repo, p), '無い')})")
    M.append("")

    M += ["## ⑤ 対象", ""]
    for s, body in sections.items():
        M += [f"### 節 {s}(スキルの写しの後から次の「## 」の見出しの手前まで、そのまま)", "", "````markdown", *body,
              "````", ""]
    M += ["### 節の中のバッククォートのパス", ""]
    paths = [t for t in toks if is_path(t)]
    if paths:
        M += [f"- `{t}`: {ex.mark(resolve(t, repo), NOT_FOUND)}" for t in paths]
    else:
        M.append("無い")
    M += ["", "### 節の中の K 番号の台帳の行", "", f"台帳: `{shown(ledger)}`", ""]
    if not kids:
        M += ["K 番号は無い", ""]
    for k in kids:
        r = rows[k]
        M += [f"#### {k}", ""]
        M += (["````markdown", *r, "````"] if r else ["台帳に無い"]) + [""]

    M += ["## ⑥ 手順の履歴(案 §6.2 ⑤ の「この単位で打ったコマンドの一覧」は集める手立てが無いので、git log で代える)", "",
          "| 節 | 当てたこと |", "|---|---|"]
    for n in names:
        f = is_filled(text, n)
        M.append(f"| {n} | {'埋まっている' if f else ('見出しが無い' if f is None else EMPTY)} |")
    M += ["", f"`git log --oneline -n 20 -- {shown(doc)}`:", "", "```", *git_log(doc), "```", ""]

    last = ["## ⑦ 渡さないもの・読まないもの", "",
            "- 封印の置き場: `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/`",
            "- 過去の検証結果(全捨て、L-019)", ""]

    # 封印: ① と ⑦ の決まった文を除く全文を、有無を確かめる前に検める
    checked = "\n".join(head + M)
    hits = sealed_words(checked)
    if hits:
        raise Stop("封印の置き場を指す語がある(写さずに止める): " + " / ".join(hits))
    return ex.fill("\n".join(head + first + M + last))


def next_path(out_dir: str, doc: str, at: str) -> str:
    d = os.path.join(out_dir, os.path.splitext(os.path.basename(doc))[0])
    existing = [f for f in os.listdir(d) if BRIEF_NAME.match(f)] if os.path.isdir(d) else []
    n = len(existing) + 1
    while True:
        p = os.path.join(d, f"{n:02d}_{at}_brief.md")
        if not os.path.exists(p) and not any(BRIEF_NAME.match(f).group(1) == f"{n:02d}" for f in existing):
            return p
        n += 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doc", required=True)
    ap.add_argument("--at", required=True, choices=list(AT_STEPS))
    ap.add_argument("--done", required=True)
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--ledger", default=LEDGER, help=argparse.SUPPRESS)
    ap.add_argument("--request", default=REQUEST, help=argparse.SUPPRESS)
    ap.add_argument("--goal", default=GOAL, help=argparse.SUPPRESS)
    ap.add_argument("--status", default=STATUS, help=argparse.SUPPRESS)
    ap.add_argument("--repo", default=ROOT, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if not os.path.isfile(a.doc):
        print(f"文書が無い: {a.doc}", file=sys.stderr)
        return 1
    try:
        brief = build(a.doc, a.at, a.done, ledger=a.ledger, request=a.request, goal=a.goal, status=a.status,
                      repo=a.repo)
    except Stop as e:
        print(f"止めた: {e}", file=sys.stderr)
        return 1
    out = next_path(a.out_dir, a.doc, a.at)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    data = (brief.rstrip("\n") + "\n").encode("utf-8")
    with open(out, "xb") as fh:
        fh.write(data)
    nl = data.count(b"\n")
    print(shown(out))
    print(f"行数 {nl}")
    print(f"sha256 {hashlib.sha256(data).hexdigest()[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
