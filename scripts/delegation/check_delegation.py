#!/usr/bin/env python3
"""委任文の形の検め(提案 PROPOSAL.md §2 の ①・③の印・③'の承認の検め)。

使い方:
  check_delegation.py <委任文> [--owner-log P] [--fixed P] [--scenes P] [--root DIR] [--require-approval] [--print-hash]

決まりの正本は試験 tests/delegation/test_spec.py の冒頭の注と表。
終了コード: 0 合格(委任文の横に <名前>.stamp.json を書く)/ 1 検めの失敗 / 2 入力の誤り。0 以外のときは古い印を消す。
失敗の行は全部、標準出力に日本語で出す。Python の標準ライブラリだけを使い、ほかのファイルを import しない。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

# ==== 共通の部品(ここから。check_report.py と一字違わず同じに保つ) ====

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OWNER_LOG = REPO_ROOT / "docs" / "OWNER_LOG.md"
DEFAULT_FIXED = REPO_ROOT / ".claude" / "skills" / "delegated-study" / "FIXED_CONSTRAINTS.md"
DEFAULT_SCENES = REPO_ROOT / ".claude" / "skills" / "delegated-study" / "BREAK_SCENES.md"

KINDS = ("作る", "読む", "批評")
CORE_HEADINGS = ("着手前の表", "目的(オーナーの逐語)", "読んだ事実", "決めてよいこと・決めてはいけないこと",
                 "変えないもの", "決まった制約", "終わる条件と上限", "報告")
KIND_HEADINGS = {"作る": ("壊す場面", "受け入れ", "変異の表"), "読む": ("出典の決まり",), "批評": ()}
FACT_KINDS = ("データ", "既存の決まり", "列の意味")
DECIDE = ("出力の置き場", "分母・数え方", "比べの方法", "確かめ方", "依存", "絞り方・選び方", "単位・通貨のそろえ方")
HASH_SKIP = ("## 途中の決め", "## オーナーの承認", "## 事前の批評の後の変更")
SEALED = ("docs/research/window1", "backtest_data/phase2_sealed")
RESPONSES = ("直した", "直さない", "オーナーに聞く", "次の版で直す")

LNUM = r"L-(?:\d{3}[a-z]?|D\d{2})"
RE_LNUM_FULL = re.compile(LNUM)
RE_LNUM_BEFORE = re.compile(r"(?<![A-Za-z0-9-])(" + LNUM + r")[ \t]*$")
RE_LNUM_AFTER = re.compile(r"^[ \t]*(" + LNUM + r")(?![0-9A-Za-z])")
RE_QUOTE = re.compile(r"「\*\*(.+?)\*\*」")
RE_BACKTICK = re.compile(r"`[^`]*`")
RE_BT_PATHLINE = re.compile(r"(\S*/\S*?):(\d+)(?:-(\d+))?")
RE_PATHLINE = re.compile(r"(?<![A-Za-z0-9._~+/-])([A-Za-z0-9._~+-]*/[A-Za-z0-9._~+/-]*):(\d+)(?:-(\d+))?(?![0-9])")
RE_CMD = re.compile(r"`[^`]+`.*?→\s*\S")
RE_NONE = re.compile(r"この委任には無い[(（].+[)）]")
RE_UREF = re.compile(r"(?<![A-Za-z0-9])U(\d+)(?!\d)")
RE_UDEF = re.compile(r"^- U(\d+):")
RE_HDEF = re.compile(r"^- H(\d+):")
RE_QDEF = re.compile(r"^- Q(\d+):")
RE_ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*(?:\*\*)?\[(直す|聞く|止める)\]")
RE_BR = re.compile(r"<br\s*/?>", re.I)
QUOTE_SEP = set(" 。！？!?•→")
QUOTE_END = set("。！？!?")
RE_MDHEAD = re.compile(r"^#{1,6}(?:\s|$)")
RE_RESP_ANY = re.compile(r"^応答\s*[:：]")
RE_RESP = re.compile(r"^応答: (" + "|".join(RESPONSES) + r")[(（](.+)[)）]$")
RE_PM_FIRST = re.compile(r"^委任文 sha256: ([0-9a-f]{64})\s*$")
RE_SEEN_ANY = re.compile(r"^見た版の sha256:")
RE_SEEN = re.compile(r"^見た版の sha256:\s*([0-9a-f]{64})\s*$")
RE_SEP_CELL = re.compile(r"^:?-+:?$")


class InputError(Exception):
    """入力の誤り(終了コード 2)。"""


def body_hash_of(text: str) -> str:
    """事前の批評の sha256: `## 途中の決め`・`## オーナーの承認`・`## 事前の批評の後の変更` の見出しの行から、
    次の `## ` の行の手前(無ければ終わり)までを除いたバイトの sha256。"""
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            skip = line.rstrip("\r\n").rstrip() in HASH_SKIP
        if not skip:
            out.append(line)
    return hashlib.sha256("".join(out).encode("utf-8")).hexdigest()


def decode_utf8(data: bytes, label: str, path: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise InputError(f"入力の誤り: {label} が UTF-8 でない: {path}")


def read_input_text(path: str, label: str) -> str:
    """委任文以外の入力(OWNER_LOG・FIXED・BREAK_SCENES・報告)を読む。ふつうのファイルでなければ開かない。"""
    p = Path(path)
    try:
        if not p.is_file():
            raise InputError(f"入力の誤り: {label} が無いか、ふつうのファイルでない: {path}")
        data = p.read_bytes()
    except OSError as e:
        raise InputError(f"入力の誤り: {label} を読めない: {path}({e.__class__.__name__})")
    return decode_utf8(data, label, path)


def read_delegation_bytes(path: str) -> bytes:
    """委任文を、渡されたパスのまま Path.read_bytes() で 1 回だけ読む。"""
    p = Path(path)
    try:
        if not p.is_file():
            raise InputError(f"入力の誤り: 委任文が無いか、ふつうのファイルでない: {path}")
        return p.read_bytes()
    except OSError as e:
        raise InputError(f"入力の誤り: 委任文を読めない: {path}({e.__class__.__name__})")


def text_lines(text: str) -> list[str]:
    if text.startswith("﻿"):
        text = text[1:]
    return text.splitlines()


def mask_backticks(line: str) -> str:
    """対になったバッククォートの中を NUL に置き換える(位置は保つ)。"""
    return RE_BACKTICK.sub(lambda m: "\0" * len(m.group(0)), line)


def split_row(line: str) -> list[str]:
    """表の行を、バッククォートの外の `|`(`\\|` は除く)で区切る。"""
    s = line.strip()
    masked = mask_backticks(s)
    cells, start = [], 0
    for i, ch in enumerate(masked):
        if ch == "|" and not (i > 0 and masked[i - 1] == "\\"):
            cells.append(s[start:i])
            start = i + 1
    cells.append(s[start:])
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and s.endswith("|") and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]


def table_rows(lines: list[str]) -> list[list[str]]:
    """見出しの行と区切りの行を除いた表の行。"""
    rows = [(i, split_row(l)) for i, l in enumerate(lines) if l.lstrip().startswith("|")]
    seps = {i for i, cells in rows if cells and all(RE_SEP_CELL.match(c) for c in cells)}
    return [cells for i, cells in rows if i not in seps and (i + 1) not in seps]


def parse_sections(lines: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """`## ` の見出しごとの本文(見出しの行を除く)と、出た見出しの並び(重なりを含む)。同じ見出しが 2 つ以上あれば本文をつなぐ。"""
    secs: dict[str, list[str]] = {}
    order: list[str] = []
    cur = None
    for l in lines:
        if l.startswith("## "):
            cur = l[3:].rstrip()
            if cur not in secs:
                secs[cur] = []
            order.append(cur)
            continue
        if cur is not None:
            secs[cur].append(l)
    return secs, order


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def norm_quote(s: str) -> str:
    """`<br>` を空白にし、空白の並びを 1 つの半角の空白にそろえる。"""
    return norm_space(RE_BR.sub(" ", s))


def parse_owner_log(text: str) -> dict[str, list[dict]]:
    """1 列目がちょうど番号の行を、番号ごとに全部集める。cell = 4 列目(オーナーの逐語の欄)、
    bound = 4 列目の「**・**」を空白にしたもの(区切りの検め用)、raw = 行全体。"""
    rows: dict[str, list[dict]] = {}
    for l in text_lines(text):
        if not l.lstrip().startswith("|"):
            continue
        cells = split_row(l)
        if len(cells) >= 4 and RE_LNUM_FULL.fullmatch(cells[0]):
            bound = norm_quote(cells[3].replace("「**", " ").replace("**」", " ")).strip()
            rows.setdefault(cells[0], []).append({"cell": norm_quote(cells[3]), "bound": bound, "raw": l})
    return rows


def parse_scene_names(text: str) -> list[str]:
    return [l[2:].split(":", 1)[0] for l in text_lines(text) if l.startswith("- ")]


def fixed_section(lines: list[str]) -> list[str] | None:
    out, inside = [], False
    for l in lines:
        if l.startswith("## "):
            if inside:
                break
            if l.rstrip() == "## 決まった制約":
                inside = True
        if inside:
            out.append(l)
    return out if inside else None


def squeeze(lines: list[str]) -> list[str]:
    return [l.rstrip() for l in lines if l.strip()]


def resolve_in_root(root: str, rel: str) -> tuple[str | None, str | None]:
    """文字の上だけでパスを解く(シンボリックリンクを解かない)。(解いたパス, 失敗の種類 '根の外'・'封印')。"""
    r = os.path.normpath(os.path.abspath(root))
    full = os.path.normpath(os.path.join(r, rel))
    try:
        relp = os.path.relpath(full, r)
    except ValueError:
        relp = None
    absl = full.replace(os.sep, "/").lower() + "/"
    rlow = relp.replace(os.sep, "/").lower() if relp is not None else ""
    for s in SEALED:
        if ("/" + s + "/") in absl or rlow == s or rlow.startswith(s + "/"):
            return full, "封印"
    if relp is None or relp == os.pardir or relp.startswith(os.pardir + os.sep):
        return full, "根の外"
    return full, None


def count_lines(data: bytes) -> int:
    """行の数 = 改行の数(最後の行に改行が無ければ 1 足す)。"""
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def contains_bounded(v: str, q: str) -> bool:
    """q が v の中に、区切りで始まり区切りで終わる所で含まれるか。"""
    start = 0
    while q:
        i = v.find(q, start)
        if i < 0:
            return False
        j = i + len(q)
        if (i == 0 or v[i - 1] in QUOTE_SEP) and (q[-1] in QUOTE_END or j == len(v) or v[j] in QUOTE_SEP):
            return True
        start = i + 1
    return False


def quote_rows(owner: dict[str, list[dict]], n: str, q: str, bounded: bool) -> list[dict]:
    """番号 n の行のうち、逐語の欄に引用 q を含む行。"""
    if bounded:
        return [r for r in owner.get(n, []) if contains_bounded(r["bound"], q)]
    return [r for r in owner.get(n, []) if q in r["cell"]]


def quote_groups(line: str) -> list[tuple[list[str], list[str]]]:
    """1 行の中のオーナーの引用の並び(バッククォートの外)を、(番号の一覧, 引用の一覧) で返す。"""
    masked = mask_backticks(line)
    groups: list[list[re.Match]] = []
    for m in RE_QUOTE.finditer(masked):
        if groups and re.fullmatch(r"[ \t]*", masked[groups[-1][-1].end():m.start()]):
            groups[-1].append(m)
        else:
            groups.append([m])
    out = []
    for g in groups:
        before = RE_LNUM_BEFORE.search(masked[:g[0].start()])
        after = RE_LNUM_AFTER.match(masked[g[-1].end():])
        nums: list[str] = []
        for x in (before, after):
            if x and x.group(1) not in nums:
                nums.append(x.group(1))
        out.append((nums, [norm_quote(m.group(1)).strip() for m in g]))
    return out


def judge_group(nums: list[str], quotes: list[str], owner: dict[str, list[dict]], bounded: bool,
                where: str, fails: list[str]) -> str | None:
    """番号の付いた引用の並びを比べる。通れば通った番号、通らなければ失敗の行を足して None。"""
    for n in nums:
        if all(quote_rows(owner, n, q, bounded) for q in quotes):
            return n
    for n in nums:
        if n not in owner:
            fails.append(f"引用: {where}の {n} は OWNER_LOG に 1 列目がちょうどその番号の行が無い")
    for q in quotes:
        if not any(quote_rows(owner, n, q, bounded) for n in nums):
            if bounded and any(quote_rows(owner, n, q, False) for n in nums):
                fails.append(f"引用: {where}の {'・'.join(nums)} の引用「{q[:30]}」は、逐語の欄の区切りで始まり区切りで"
                             f"終わる所に無い(語の途中で切っている。目的の節)")
            else:
                fails.append(f"引用: {where}の {'・'.join(nums)} の引用「{q[:30]}」が OWNER_LOG のその番号の行の"
                             f"逐語の欄に無い")
    return None


def check_quotes(lines: list[str], owner: dict[str, list[dict]], dname: str, dhash: str,
                 fails: list[str]) -> bool:
    """全部の節のオーナーの引用を OWNER_LOG と比べる。目的の節は番号の付いた引用が要り、区切りで比べる。
    `## オーナーの承認` に、OWNER_LOG のその番号の行で、逐語の欄に引用を含み、行のどこかに委任文の名前と
    今の事前の批評の sha256 を含む行がある引用があれば True を返す(L-796)。"""
    approved = False
    section = None
    purpose_numbered = 0
    for ln, line in enumerate(lines, 1):
        if line.startswith("## "):
            section = line[3:].rstrip()
        in_purpose = section == "目的(オーナーの逐語)"
        for nums, quotes in quote_groups(line):
            if not nums:
                if in_purpose:
                    fails.append(f"引用: {ln} 行目の引用「{quotes[0][:30]}」に番号(L-数字)が無い(目的の節)")
                continue
            if in_purpose:
                purpose_numbered += 1
            n = judge_group(nums, quotes, owner, in_purpose, f"{ln} 行目", fails)
            if n is not None and section == "オーナーの承認":
                for q in quotes:
                    if any(dname in r["raw"] and dhash in r["raw"] for r in quote_rows(owner, n, q, False)):
                        approved = True
    if purpose_numbered == 0:
        fails.append("目的: 「## 目的(オーナーの逐語)」の節に、番号の付いたオーナーの引用が 1 つも無い")
    return approved


def path_lines(cell: str) -> list[tuple[str, str, str | None]]:
    """確かめの欄の `パス:行` を全部拾う。(1) バッククォートの中身が丸ごと `<パス>:<行>`(日本語の名前も可)
    (2) それ以外の所(コマンドの中も)の「/ を含む ASCII の語」の直後の `:<行>`。"""
    found = []
    masked = cell
    for m in RE_BACKTICK.finditer(cell):
        mm = RE_BT_PATHLINE.fullmatch(m.group(0)[1:-1])
        if mm:
            found.append((mm.group(1), mm.group(2), mm.group(3)))
            masked = masked[:m.start()] + "\0" * len(m.group(0)) + masked[m.end():]
    for m in RE_PATHLINE.finditer(masked):
        found.append((m.group(1), m.group(2), m.group(3)))
    return found


def check_path_line(root: str, cell: str, fails: list[str]) -> bool:
    """確かめの欄の `パス:行` を全部見る。1 つでもあれば True。"""
    found = False
    for rel, sa, sb in path_lines(cell):
        found = True
        a, b = int(sa), int(sb or sa)
        tag = f"{rel}:{sa}" + (f"-{sb}" if sb else "")
        full, why = resolve_in_root(root, rel)
        if why == "根の外":
            fails.append(f"読んだ事実: 確かめの欄の {tag} は根の外のパス")
            continue
        if why == "封印":
            fails.append(f"読んだ事実: 確かめの欄の {tag} は封印の置き場の下のパス(開かない)")
            continue
        if not os.path.isfile(full):
            fails.append(f"読んだ事実: 確かめの欄の {tag} のパスが無いか、ふつうのファイルでない(開かない)")
            continue
        try:
            with open(full, "rb") as f:
                n = count_lines(f.read())
        except OSError as e:
            fails.append(f"読んだ事実: 確かめの欄の {tag} を読めない({e.__class__.__name__})")
            continue
        if a < 1 or b < a:
            fails.append(f"読んだ事実: 確かめの欄の {tag} の行の番号が 1 より小さいか、範囲が逆向き")
        elif b > n:
            fails.append(f"読んだ事実: 確かめの欄の {tag} の行の番号 {b} がファイルの行の数 {n} を超える")
    return found


def check_facts(body: list[str], root: str, fails: list[str]) -> None:
    rows = table_rows(body)
    firsts = {r[0] for r in rows if r}
    for k in FACT_KINDS:
        if k not in firsts:
            fails.append(f"読んだ事実: 1 列目が「{k}」の行が無い")
    for r in rows:
        cell = r[2] if len(r) >= 3 else ""
        label = f"読んだ事実: 行「{(r[0] if r else '')} | {(r[1] if len(r) > 1 else '')[:30]}」"
        if check_path_line(root, cell, fails):
            continue
        if RE_CMD.search(cell) or RE_NONE.search(cell):
            continue
        fails.append(f"{label} の確かめの欄が、パス:行・`コマンド` → 出力・この委任には無い(理由) のどの形でもない")


def check_decide(body: list[str], fails: list[str]) -> None:
    rows = table_rows(body)
    for k in DECIDE:
        vals = [r[1] if len(r) > 1 else "" for r in rows if r and r[0] == k]
        if not vals:
            fails.append(f"決めてよいこと: 1 列目が「{k}」の行が無い")
        elif any(v == "" for v in vals):
            fails.append(f"決めてよいこと: 「{k}」の行の 2 列目が空")


def check_scenes(body: list[str], scenes: list[str], udefs: set[int], fails: list[str]) -> None:
    rows = [r for r in table_rows(body) if r]
    names = [r[0] for r in rows]
    missing = [n for n in scenes if n not in names]
    unknown = [n for n in names if n not in scenes]
    for n in missing:
        fails.append(f"壊す場面: 場面「{n}」の行が無い(BREAK_SCENES の名前と一字違わず同じにする)")
    for n in unknown:
        fails.append(f"壊す場面: BREAK_SCENES に無い場面の名前「{n}」")
    if not missing and not unknown and names != scenes:
        fails.append("壊す場面: 場面の行の数か並びが BREAK_SCENES と違う")
    for r in rows:
        cell = r[1] if len(r) > 1 else ""
        refs = RE_UREF.findall(cell)
        if refs:
            bad = [f"U{x}" for x in refs if int(x) not in udefs]
            if bad:
                fails.append(f"壊す場面: 場面「{r[0]}」の欄の {'・'.join(bad)} が受け入れの節に無い")
        elif not RE_NONE.search(cell):
            fails.append(f"壊す場面: 場面「{r[0]}」の欄に、受け入れの U の参照も「この委任には無い(理由)」も無い")


def number_defs(body: list[str], rx: re.Pattern) -> list[int]:
    return [int(m.group(1)) for l in body if (m := rx.match(l))]


def check_premortem(delegation_path: str, text_body_hash: str, secs: dict[str, list[str]],
                    fails: list[str]) -> str | None:
    """事前の批評の記録を検める。最後の回の記録のパス(無ければ None)を返す。"""
    dp = Path(delegation_path)
    stem = dp.name[:-3] if dp.name.endswith(".md") else dp.name
    rx = re.compile(re.escape(stem) + r"_premortem(\d+)\.md")
    recs = []
    try:
        for p in dp.parent.iterdir():
            m = rx.fullmatch(p.name)
            if m:
                recs.append((int(m.group(1)), p.name, p))
    except OSError as e:
        fails.append(f"事前の批評: 記録の置き場を見られない({e.__class__.__name__})")
        return None
    if not recs:
        fails.append(f"事前の批評: 記録 {stem}_premortem<数字>.md が 1 つも無い")
        return None
    recs.sort()
    last_no, _, last_path = recs[-1]
    seen = [l for l in secs.get("事前の批評の後の変更", []) if RE_SEEN_ANY.match(l)]
    expect = text_body_hash
    if seen:
        vals = {m.group(1) for l in seen if (m := RE_SEEN.match(l))}
        if len(vals) != 1 or len(seen) != len([l for l in seen if RE_SEEN.match(l)]):
            fails.append("sha256: `## 事前の批評の後の変更` の「見た版の sha256:」の行が 1 つの 64 桁の 16 進(小文字)でない")
        else:
            expect = vals.pop()
    for no, name, p in recs:
        if not p.is_file():
            fails.append(f"事前の批評: 記録 {name} がふつうのファイルでない")
            continue
        try:
            with open(p, "rb") as f:
                t = f.read().decode("utf-8")
        except (OSError, UnicodeDecodeError) as e:
            fails.append(f"事前の批評: 記録 {name} を UTF-8 で読めない({e.__class__.__name__})")
            continue
        lines = text_lines(t)
        is_last = no == last_no and p == last_path
        if is_last:
            m = RE_PM_FIRST.match(lines[0]) if lines else None
            if not m:
                fails.append(f"sha256: 最後の回の記録 {name} の 1 行目が「委任文 sha256: <64 桁>」でない")
            elif m.group(1) != expect:
                fails.append(f"sha256: 最後の回の記録 {name} の 1 行目 {m.group(1)[:12]}… が、今の委任文の事前の批評の"
                             f" sha256 {expect[:12]}… と違う")
        items: list[tuple[int, list[str]]] = []
        cur = None
        for ln, l in enumerate(lines, 1):
            if RE_ITEM.match(l):
                cur = (ln, [])
                items.append(cur)
            elif RE_MDHEAD.match(l):
                cur = None
            elif cur is not None and RE_RESP_ANY.match(l.strip()):
                cur[1].append(l.strip())
        for ln, resps in items:
            if not resps:
                fails.append(f"応答: 記録 {name} の {ln} 行目の指摘に「応答: 」の行が無い")
                continue
            if len(resps) > 1:
                fails.append(f"応答: 記録 {name} の {ln} 行目の指摘に「応答: 」の行が 2 つ以上ある")
                continue
            m = RE_RESP.match(resps[0])
            if not m:
                fails.append(f"応答: 記録 {name} の {ln} 行目の指摘の応答が「{'・'.join(RESPONSES)}」に括弧で中身 1 字"
                             f"以上の形でない")
            elif is_last and no >= 2 and m.group(1) == "直した":
                fails.append(f"最後の回: 記録 {name}(番号 {no} の最後の回)の {ln} 行目の指摘の応答が「直した」"
                             f"(直しは委任文の `## 事前の批評の後の変更` に書く)")
    return str(last_path)


def approval_failure(delegation_path: str, body_sha256: str) -> str:
    return (f"承認: `## オーナーの承認` の節に、OWNER_LOG のその番号の行で、逐語の欄に引用を含み、行のどこかに委任文の名前"
            f" {Path(delegation_path).name} と今の事前の批評の sha256 {body_sha256[:12]}… を含む行がある引用が無い")


def check_delegation_text(delegation_path: str, data: bytes, text: str, owner: dict[str, list[dict]],
                          fixed_lines: list[str], scenes: list[str], root: str) -> tuple[list[str], dict]:
    """委任文の検めを全部行い、(失敗の行, 情報) を返す。"""
    fails: list[str] = []
    lines = text_lines(text)
    secs, order = parse_sections(lines)
    info: dict = {"kind": None, "udefs": [], "hdefs": [], "qdefs": [], "qlines": {}, "approved": False,
                  "premortem": None, "body_sha256": body_hash_of(text), "delegation_sha256": hashlib.sha256(data).hexdigest()}

    # 種類
    kl = [l for l in lines[:5] if l.startswith("種類: ")]
    kind = kl[0][len("種類: "):].strip() if len(kl) == 1 else None
    if len(kl) != 1:
        fails.append(f"種類: 5 行目までに行頭の「種類: 」の行がちょうど 1 つ要る({len(kl)} 個ある)")
    elif kind not in KINDS:
        fails.append(f"種類: 値「{kind}」は {'・'.join(KINDS)} のどれでもない")
        kind = None
    info["kind"] = kind

    # 見出し
    need = list(CORE_HEADINGS) + list(KIND_HEADINGS.get(kind, ()) if kind else ())
    for h in need:
        if h not in secs:
            fails.append(f"見出し: 「## {h}」が無い")
        elif order.count(h) > 1:
            fails.append(f"見出し: 「## {h}」が {order.count(h)} つある")
        elif not "".join(secs[h]).strip():
            fails.append(f"見出し: 「## {h}」の本文が空")

    # 引用(全部の節)・承認
    info["approved"] = check_quotes(lines, owner, Path(delegation_path).name, info["body_sha256"], fails)

    # 読んだ事実
    check_facts(secs.get("読んだ事実", []), root, fails)

    # 決めてよいこと
    check_decide(secs.get("決めてよいこと・決めてはいけないこと", []), fails)

    # 変えないもの
    hdefs = number_defs(secs.get("変えないもの", []), RE_HDEF)
    info["hdefs"] = hdefs
    if not hdefs:
        fails.append("変えないもの: 行頭の「- H数字:」が 1 つも無い")

    # 受け入れ・壊す場面(作る)
    if kind == "作る":
        udefs = number_defs(secs.get("受け入れ", []), RE_UDEF)
        info["udefs"] = udefs
        if not udefs:
            fails.append("受け入れ: 行頭の「- U数字:」が 1 つも無い")
        for u in sorted({u for u in udefs if udefs.count(u) > 1}):
            fails.append(f"受け入れ: U{u} が 2 つ以上ある")
        check_scenes(secs.get("壊す場面", []), scenes, set(udefs), fails)

    # 決まった制約
    mine = fixed_section(lines)
    if mine is None or squeeze(mine) != squeeze(fixed_lines):
        a, b = squeeze(mine or []), squeeze(fixed_lines)
        diff = next((i for i in range(max(len(a), len(b))) if i >= len(a) or i >= len(b) or a[i] != b[i]), None)
        where = f"(空行を除いて {diff + 1} 行目から違う)" if diff is not None else ""
        fails.append(f"決まった制約: 節が FIXED_CONSTRAINTS.md の「## 決まった制約」の節と一字違わず同じでない{where}")

    # 終わる条件と上限
    end_body = secs.get("終わる条件と上限", [])
    for w in ("終わる条件", "上限"):
        ls = [l for l in end_body if l.startswith(f"- {w}:")]
        if not ls:
            fails.append(f"終わる条件と上限: 行頭の「- {w}:」の行が無い")
        elif not any(l[len(w) + 3:].strip() for l in ls):
            fails.append(f"終わる条件と上限: 「- {w}:」の後が空")

    # 途中の決め
    mid = secs.get("途中の決め", [])
    info["qdefs"] = number_defs(mid, RE_QDEF)
    for l in mid:
        m = RE_QDEF.match(l)
        if m:
            info["qlines"].setdefault(int(m.group(1)), []).append(norm_space(l))

    # 事前の批評の記録(作る)
    if kind == "作る":
        info["premortem"] = check_premortem(delegation_path, info["body_sha256"], secs, fails)
    return fails, info


def load_references(owner_log: str, fixed: str, scenes: str, errors: list[str]):
    owner, fixed_lines, scene_names = {}, [], []
    try:
        owner = parse_owner_log(read_input_text(owner_log, "OWNER_LOG"))
    except InputError as e:
        errors.append(str(e))
    try:
        fl = fixed_section(text_lines(read_input_text(fixed, "FIXED_CONSTRAINTS")))
        if fl is None:
            errors.append(f"入力の誤り: FIXED_CONSTRAINTS に「## 決まった制約」の節が無い: {fixed}")
        else:
            fixed_lines = fl
    except InputError as e:
        errors.append(str(e))
    try:
        scene_names = parse_scene_names(read_input_text(scenes, "BREAK_SCENES"))
        if not scene_names:
            errors.append(f"入力の誤り: BREAK_SCENES に行頭の「- 」の場面の名前が無い: {scenes}")
    except InputError as e:
        errors.append(str(e))
    return owner, fixed_lines, scene_names


def parse_args(argv: list[str], options: tuple[str, ...], flags: tuple[str, ...]) -> tuple[list[str], dict]:
    pos: list[str] = []
    opts: dict = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            name, eq, val = a.partition("=")
            if name in flags and not eq:
                opts[name] = True
            elif name in options:
                if not eq:
                    if i + 1 >= len(argv):
                        raise InputError(f"入力の誤り: {name} の後に値が無い")
                    i += 1
                    val = argv[i]
                opts[name] = val
            else:
                raise InputError(f"入力の誤り: 知らない引数 {a}")
        else:
            pos.append(a)
        i += 1
    return pos, opts


def setup_stdout() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="backslashreplace")
        except Exception:
            pass

# ==== 共通の部品(ここまで) ====


USAGE = ("使い方: check_delegation.py <委任文> [--owner-log P] [--fixed P] [--scenes P] [--root DIR] "
         "[--require-approval] [--print-hash]")


def stamp_path_of(delegation_path: str) -> Path:
    dp = Path(delegation_path)
    stem = dp.name[:-3] if dp.name.endswith(".md") else dp.name
    return dp.parent / f"{stem}.stamp.json"


def remove_stamp(delegation_path: str | None) -> None:
    if not delegation_path:
        return
    try:
        sp = stamp_path_of(delegation_path)
        if sp.is_file() or sp.is_symlink():
            sp.unlink()
    except OSError:
        pass


def run(argv: list[str]) -> int:
    try:
        pos, opts = parse_args(argv, ("--owner-log", "--fixed", "--scenes", "--root"),
                               ("--require-approval", "--print-hash", "--help"))
    except InputError as e:
        print(e)
        print(USAGE)
        return 2
    if "--help" in opts:
        print(USAGE)
        return 0
    if len(pos) != 1:
        print("入力の誤り: 委任文のパスを 1 つだけ渡す")
        print(USAGE)
        return 2
    dpath = pos[0]

    if opts.get("--print-hash"):
        try:
            data = read_delegation_bytes(dpath)
            text = decode_utf8(data, "委任文", dpath)
        except InputError as e:
            print(e)
            return 2
        print(body_hash_of(text))
        return 0

    errors: list[str] = []
    data, text = b"", ""
    try:
        data = read_delegation_bytes(dpath)
        text = decode_utf8(data, "委任文", dpath)
    except InputError as e:
        errors.append(str(e))
    owner, fixed_lines, scenes = load_references(opts.get("--owner-log", str(DEFAULT_OWNER_LOG)),
                                                 opts.get("--fixed", str(DEFAULT_FIXED)),
                                                 opts.get("--scenes", str(DEFAULT_SCENES)), errors)
    if errors:
        remove_stamp(dpath)
        for e in errors:
            print(e)
        print(f"入力の誤り {len(errors)} 件(終了コード 2)")
        return 2

    root = opts.get("--root", str(REPO_ROOT))
    fails, info = check_delegation_text(dpath, data, text, owner, fixed_lines, scenes, root)
    if opts.get("--require-approval") and not info["approved"]:
        fails.append(approval_failure(dpath, info["body_sha256"]) + "(--require-approval)")
    if fails:
        remove_stamp(dpath)
        for f in fails:
            print(f)
        print(f"不合格: 失敗 {len(fails)} 件(終了コード 1)")
        return 1

    stamp = {"delegation_sha256": info["delegation_sha256"], "body_sha256": info["body_sha256"],
             "kind": info["kind"], "premortem": info["premortem"], "approved": bool(info["approved"])}
    sp = stamp_path_of(dpath)
    try:
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(stamp, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as e:
        remove_stamp(dpath)
        print(f"入力の誤り: 印 {sp} を書けない({e.__class__.__name__})")
        return 2
    print(f"合格: {dpath}(種類: {info['kind']}、承認: {'あり' if info['approved'] else '無し'})")
    print(f"印: {sp}")
    return 0


def main() -> int:
    setup_stdout()
    argv = sys.argv[1:]
    try:
        return run(argv)
    except Exception as e:  # どんな入力でも Traceback で終わらない
        try:
            pos, opts = parse_args(argv, ("--owner-log", "--fixed", "--scenes", "--root"),
                                   ("--require-approval", "--print-hash", "--help"))
            if len(pos) == 1 and not opts.get("--print-hash"):
                remove_stamp(pos[0])
        except Exception:
            pass
        print(f"入力の誤り: 道具の中で想定していない誤り({e.__class__.__name__}: {e})")
        return 2


if __name__ == "__main__":
    sys.exit(main())
