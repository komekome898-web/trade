#!/usr/bin/env python3
"""成果物 1 件から「対」を code で切り出し、対ごとに狭い問いを Jev へ投げる道具。

設計の出所: `docs/DISCUSSIONS/2026-09-19_jev_common_module_review.md` §1・§5(監査の行)。
**Jev は「code が並べた 2 つの断片に狭い問いを投げる」1 つの型としてだけ使う。**

**この道具は何も止めないし、何かを良しともしない**(オーナー逐語 L-218:
「**そもそも止めるとjev出させようとするのは間違った運用で、判断はLLMと私の役割である**」)。
出すのは対ごとの確率と、**要確認の印(flag)**だけである。

- 抽出は **code(決定論的)**。state は必ず code が組む(設計文書 §1 の逐語:
  「**判定される側(リード)が state を書く形 → 置かない**」)。
- 数える・日付・数値の突き合わせは **code**(`number_vs_source` は Jev へ送らない)。
- 問いは 1 判断 1 問・肯定形・criteria は具体例つき・英語(state の断片は日本語のまま)。
- 送信前に `redact_json` + `assert_clean`。落ちたら送らず終了コード 2。

使い方:
  python3 scripts/jev_check.py audit <成果物.md> [--out DIR] [--dry-run] [--summary] [--model ID]
  python3 scripts/jev_check.py score --labels <labels.csv> --dir data/jev/check/ [--controls DIR|FILE...]

**数値の解釈や結論はこの道具は書かない。**
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.jev.client import JevClient, JevError  # noqa: E402
from scripts.jev.redact import RedactionError, assert_clean, redact_json  # noqa: E402

# ---------------------------------------------------------------------------
# 定数(しきい値はこの 1 箇所だけ)
# ---------------------------------------------------------------------------
ATTENTION = 0.35  # これ以上なら「要確認」の印を付ける(印を付けるだけで、何も止めない)
PRESENCE = 0.50   # 「そもそも不在の主張か」の分かれ目(negative_claim の 2 問目)
MAX_NEGATIVE_PAIRS = 40  # 1 文書あたりの negative_claim の対の上限(超えた分は切る)
MAX_DEFS_PER_SYMBOL = 8  # 同じ記号の定義文は最初の 1 件と後続 (最大 8 件) の対にする(全 2 点組は大きい文書で爆発する: 2026-09-19 実測 79,001 対)
DEFAULT_MODEL = "jev-1.13.0"
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "check"
MAX_FRAGMENT_CHARS = 2_000
SOURCE_SUFFIXES = (".csv", ".json", ".txt")

# 抽出のパターン(仕様どおりの語をそのまま置く)
NEGATIVE_RE = re.compile(r"取れない|無い|ない|できない|存在しない|不可|見当たらない|提供していない")
VERIFICATION_RE = re.compile(r"確認した|読んだ|検証した|実測した|突き合わせた|数え直した|走らせた|実行した")
UNIVERSAL_RE = re.compile(r"全て|すべて|全件|全部|網羅|漏れなく|残らず|一つも|1 つも")
SCOPE_HEADING_RE = re.compile(r"射程|範囲|測らない|言えないこと")
# 射程の宣言(「言えないこと」)は可用性の断定ではないので negative_claim から外す。
# そこは scope_vs_bar の側で見る(2026-09-19、対照で見えた誤検出の型 1)。
SCOPE_EXCLUDE_HEADING_RE = re.compile(r"射程|言えない|範囲|限界")
BAR_HEADING_RE = re.compile(r"判定|採用|基準|バー|合否")
MEASURED_HEADING_RE = re.compile(r"測定対象|測るもの|対象")
WHY_HEADING_RE = re.compile(r"なぜ|機構|理解")
RESULT_HEADING_RE = re.compile(r"結果|判定")

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_BACKTICK_RE = re.compile(r"`([^`\n]{1,40})`")
_DEF_HINT_RE = re.compile(r"([^\s、。「」`|*]{1,20})\s*(?:とは|[=＝])")
_NUMBER_RE = re.compile(r"(?<![0-9A-Za-z_.])(\d+(?:\.\d+)?)\s*(%|bp)?")
_INTENT_OK_RE = re.compile(r"○")


# ---------------------------------------------------------------------------
# Markdown の分解(すべて決定論的)
# ---------------------------------------------------------------------------
def _clip(text: str) -> str:
    return text.strip()[:MAX_FRAGMENT_CHARS]


_QUOTE_RE = re.compile(r"^(?:>\s*)+")
_BLOCK_START_RE = re.compile(r"^(?:\||[-*+]\s|#{1,6}\s|\d+[.)]\s|```)")


def _strip_quote(line: str) -> str:
    return _QUOTE_RE.sub("", line).strip()


def logical_lines_by_paragraph(text: str) -> list[tuple[int, list[tuple[int, str]]]]:
    """段落ごとの「論理行」。折り返された散文は 1 本につなぐ(日本語なので空白は入れない)。

    表の行・箇条書き・見出し・コード柵は、次の行につなげない。
    """
    out: list[tuple[int, list[tuple[int, str]]]] = []
    for start, lines in paragraphs(text):
        joined: list[tuple[int, str]] = []
        for offset, line in enumerate(lines):
            body = _strip_quote(line)
            if not body:
                continue
            ln = start + offset
            prev = joined[-1][1] if joined else ""
            if (joined and not _BLOCK_START_RE.match(body)
                    and not prev.startswith(("#", "|", "```"))
                    and not prev.endswith(("。", "|", ":", "："))):
                sep = " " if (prev[-1:].isascii() and prev[-1:].isalnum()
                              and body[:1].isascii() and body[:1].isalnum()) else ""
                joined[-1] = (joined[-1][0], prev + sep + body)
            else:
                joined.append((ln, body))
        if joined:
            out.append((start, joined))
    return out


def logical_lines(text: str) -> list[tuple[int, str]]:
    return [pair for _s, lines in logical_lines_by_paragraph(text) for pair in lines]


def sentences(text: str) -> list[tuple[int, str]]:
    """(行番号, 文) の一覧。句点「。」で切る。折り返しは論理行にまとめてから切る。"""
    out: list[tuple[int, str]] = []
    for ln, body in logical_lines(text):
        for part in re.split(r"(?<=。)", body):
            if part.strip():
                out.append((ln, part.strip()))
    return out


def paragraphs(text: str) -> list[tuple[int, list[str]]]:
    """(先頭行番号, 行の一覧)。空行で区切る。"""
    out: list[tuple[int, list[str]]] = []
    buf: list[str] = []
    start = 0
    for i, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            if not buf:
                start = i
            buf.append(line.strip())
        elif buf:
            out.append((start, buf))
            buf = []
    if buf:
        out.append((start, buf))
    return out


def sections(text: str) -> list[dict]:
    """見出しごとの節。本文は「同じか上の階層の次の見出し」まで。"""
    lines = text.splitlines()
    heads: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))
    out: list[dict] = []
    for idx, (i, level, title) in enumerate(heads):
        end = len(lines)
        for j, lvl, _t in heads[idx + 1:]:
            if lvl <= level:
                end = j
                break
        body = "\n".join(lines[i + 1:end]).strip()
        out.append({"lineno": i + 1, "level": level, "title": title, "body": body,
                    "end": end})  # end = 節の最後の行番号(1 始まり)
    return out


def scope_declaration_ranges(text: str) -> list[tuple[int, int]]:
    """見出しに「射程|言えない|範囲|限界」を含む節の行の範囲(1 始まり、両端を含む)。"""
    return [(s["lineno"], s["end"]) for s in sections(text)
            if SCOPE_EXCLUDE_HEADING_RE.search(s["title"])]


# ---------------------------------------------------------------------------
# 抽出器(対を作る)
# ---------------------------------------------------------------------------
def extract_negative_claims(text: str) -> list[dict]:
    pairs = []
    scope_ranges = scope_declaration_ranges(text)
    for _start, lines in logical_lines_by_paragraph(text):
        for ln, body in lines:
            if any(lo <= ln <= hi for lo, hi in scope_ranges):
                continue  # 射程の宣言であって可用性の断定ではない
            for part in re.split(r"(?<=。)", body):
                part = part.strip()
                if not part or not NEGATIVE_RE.search(part):
                    continue
                rest = "\n".join(b for l, b in lines if l != ln) or body
                pairs.append({
                    "kind": "negative_claim",
                    "anchor": ln,
                    "a": _clip(part),
                    "b": _clip(rest),
                    "a_role": "the sentence carrying the negative claim",
                    "b_role": "the rest of the same paragraph",
                })
    return pairs


def _following_code_block(text: str, last_lineno: int) -> str:
    """段落の直後(空行を挟んでよい)にコード柵があれば、その中身を柵ごと返す。無ければ空。"""
    lines = text.splitlines()
    i = last_lineno  # last_lineno は 1 始まりなので、これがそのまま「次の行」の添字
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not _strip_quote(lines[i]).startswith("```"):
        return ""
    out = [lines[i]]
    i += 1
    while i < len(lines):
        out.append(lines[i])
        if _strip_quote(lines[i]).startswith("```"):
            break
        i += 1
    return "\n".join(out)


def _claim_pairs(text: str, kind: str, pattern: re.Pattern,
                 a_role: str, b_role: str) -> list[dict]:
    """「…と主張する文」と「同じ段落の残り + 直後のコードブロック」の対。"""
    raws = paragraphs(text)
    logs = dict(logical_lines_by_paragraph(text))
    pairs = []
    for start, raw_lines in raws:
        lines = logs.get(start)
        if not lines:
            continue
        code = _following_code_block(text, start + len(raw_lines) - 1)
        for ln, body in lines:
            for part in re.split(r"(?<=。)", body):
                part = part.strip()
                if not part or not pattern.search(part):
                    continue
                rest = "\n".join(b for l, b in lines if l != ln)
                b = "\n".join(x for x in (rest, code) if x).strip() or body
                pairs.append({
                    "kind": kind,
                    "anchor": ln,
                    "a": _clip(part),
                    "b": _clip(b),
                    "a_role": a_role,
                    "b_role": b_role,
                })
    return pairs


def extract_verification_claims(text: str) -> list[dict]:
    return _claim_pairs(
        text, "verification_claim", VERIFICATION_RE,
        "the sentence claiming that a check, reading, run or comparison was performed",
        "the rest of the same paragraph and the code block right after it, if any",
    )


def extract_universal_claims(text: str) -> list[dict]:
    return _claim_pairs(
        text, "universal_claim", UNIVERSAL_RE,
        "the sentence claiming completeness",
        "the rest of the same paragraph and the code block right after it, if any",
    )


def _definition_patterns(term: str) -> list[re.Pattern]:
    t = re.escape(term)
    return [
        re.compile(rf"`?{t}`?\s*とは"),
        # `X = 値` で値が数値だけのものは代入であって定義ではないので外す(説明文が続くものだけ)
        re.compile(rf"`?{t}`?\s*[=＝]\s*(?![-+]?\d+(?:\.\d+)?\s*(?:%|bp)?\s*(?:[|、。)\]]|$))"),
        re.compile(rf"`?{t}`?\s*(?:は|が|を|の)?[^。]{{0,60}}?(?:を指す|である|とする|と呼ぶ|のこと)"),
    ]


def extract_symbol_definitions(text: str) -> list[dict]:
    terms: set[str] = set()
    for m in _BACKTICK_RE.finditer(text):
        t = m.group(1).strip()
        if t and not t.isdigit():
            terms.add(t)
    for m in _DEF_HINT_RE.finditer(text):
        t = m.group(1).strip().strip("`*")
        if t and not t.isdigit():
            terms.add(t)

    # 表の行と見出し行は定義候補から外す(表のセル `h=1` を定義と読まない)
    sents = [(ln, sent) for ln, body in logical_lines(text)
             if not body.startswith(("|", "#"))
             for sent in (p.strip() for p in re.split(r"(?<=。)", body)) if sent]
    pairs = []
    for term in sorted(terms):
        pats = _definition_patterns(term)
        uniq: list[tuple[int, str]] = []
        seen: set[tuple[int, str]] = set()
        for ln, s in sents:
            if not any(p.search(s) for p in pats):
                continue
            if (ln, s) in seen:
                continue
            seen.add((ln, s))
            uniq.append((ln, s))
        if len(uniq) < 2:
            continue
        # 最初の定義 × 後続の定義(先頭 MAX_DEFS_PER_SYMBOL 件)。全 2 点組にしない。
        first = uniq[0]
        for (ln_a, s_a), (ln_b, s_b) in ((first, other) for other in uniq[1:1 + MAX_DEFS_PER_SYMBOL]):
            pairs.append({
                "kind": "symbol_definition",
                "anchor": ln_a,
                "term": term,
                "a": _clip(s_a),
                "b": _clip(s_b),
                "a_role": f"a definition of `{term}` (line {ln_a})",
                "b_role": f"another definition of `{term}` (line {ln_b})",
            })
    return pairs


def _section_cross(text: str, left_re: re.Pattern, right_re: re.Pattern,
                   kind: str, left_role: str, right_role: str) -> list[dict]:
    secs = sections(text)
    lefts = [s for s in secs if left_re.search(s["title"])]
    rights = [s for s in secs if right_re.search(s["title"])]
    pairs = []
    for a in lefts:
        for b in rights:
            if a["lineno"] == b["lineno"]:
                continue
            pairs.append({
                "kind": kind,
                "anchor": a["lineno"],
                "a": _clip(f"{a['title']}\n{a['body']}"),
                "b": _clip(f"{b['title']}\n{b['body']}"),
                "a_role": left_role,
                "b_role": right_role,
            })
    return pairs


def extract_scope_vs_bar(text: str) -> list[dict]:
    return _section_cross(
        text, SCOPE_HEADING_RE, BAR_HEADING_RE, "scope_vs_bar",
        "the section stating the scope of this unit (what it does and does not answer)",
        "the section stating the acceptance bar / the decision criteria",
    )


def extract_why_section(text: str) -> list[dict]:
    return _section_cross(
        text, WHY_HEADING_RE, RESULT_HEADING_RE, "why_section",
        "the section that is supposed to explain why (the mechanism)",
        "the section carrying the results / the verdict",
    )


def extract_intent_vs_measured(text: str, artifact: Path) -> list[dict]:
    intent_map = artifact.parent / "INTENT_MAP.md"
    if not intent_map.is_file():
        return []
    intent_text = intent_map.read_text(encoding="utf-8", errors="replace")
    ok_rows = [(i, line.strip()) for i, line in enumerate(intent_text.splitlines(), start=1)
               if _INTENT_OK_RE.search(line)]
    measured = [s for s in sections(text) if MEASURED_HEADING_RE.search(s["title"])]
    pairs = []
    for ln, row in ok_rows:
        for sec in measured:
            pairs.append({
                "kind": "intent_vs_measured",
                "anchor": sec["lineno"],
                "a": _clip(row),
                "b": _clip(f"{sec['title']}\n{sec['body']}"),
                "a_role": f"a row marked ○ (implemented as intended) in INTENT_MAP.md (line {ln})",
                "b_role": "the section of the artifact listing what is actually measured",
            })
    return pairs


def extract_number_vs_source(text: str, artifact: Path) -> list[dict]:
    """本文の数値のうち、同じディレクトリの csv/json/txt のどれにも文字列として現れないもの。

    **Jev へは送らない**(数値の突き合わせは code の仕事)。
    """
    source_files = sorted(
        p for p in artifact.parent.iterdir()
        if p.is_file() and p.suffix.lower() in SOURCE_SUFFIXES
    )
    source_text = ""
    for p in source_files:
        try:
            source_text += p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

    found: dict[str, dict] = {}
    for i, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        for m in _NUMBER_RE.finditer(line):
            num, unit = m.group(1), (m.group(2) or "")
            if source_files and num in source_text:
                continue
            key = num + unit
            if key in found:
                continue
            found[key] = {
                "kind": "number_vs_source",
                "anchor": i,
                "a": _clip(line),
                "b": _clip("突き合わせ先: " + (", ".join(p.name for p in source_files) or "(なし)")),
                "a_role": "the line carrying the number",
                "b_role": "the sibling data files consulted",
                "number": key,
                "no_source_files": not source_files,
            }
    return list(found.values())


def cap_negative_claims(pairs: list[dict]) -> tuple[list[dict], int]:
    """`negative_claim` の対が `MAX_NEGATIVE_PAIRS` を超えたら先頭だけ残す。

    正規表現は広く拾う方針のまま(選ぶのは Jev の `is_unavailability_claim`)なので、
    1 文書あたりの要求数だけを頭打ちにする。戻り値は (残した対, 落とした件数)。
    """
    kept: list[dict] = []
    n_neg = 0
    n_dropped = 0
    for pair in pairs:
        if pair["kind"] != "negative_claim":
            kept.append(pair)
            continue
        n_neg += 1
        if n_neg <= MAX_NEGATIVE_PAIRS:
            kept.append(pair)
        else:
            n_dropped += 1
    return kept, n_dropped


def extract_pairs(text: str, artifact: Path) -> list[dict]:
    pairs: list[dict] = []
    pairs += extract_negative_claims(text)
    pairs += extract_verification_claims(text)
    pairs += extract_universal_claims(text)
    pairs += extract_symbol_definitions(text)
    pairs += extract_scope_vs_bar(text)
    pairs += extract_intent_vs_measured(text, artifact)
    pairs += extract_why_section(text)
    pairs += extract_number_vs_source(text, artifact)
    return pairs


# ---------------------------------------------------------------------------
# 問い(1 判断 1 問・肯定形・criteria は具体例つき・英語)
# ---------------------------------------------------------------------------
def question_for(kind: str, pair: dict) -> dict:
    if kind == "verification_claim":
        # O-3 の族(実行したコマンドと出力を同じ返答に出す)。presence を別の問いに分ける。
        return {
            "evidence_attached": {
                "type": "noul",
                "instructions": (
                    "The command that was run and its output, or the file and line that was read, "
                    "appear in `fragment_a` or `fragment_b`."
                ),
                "criteria": {
                    "true": (
                        "The command and its output are shown, or the exact source is named. "
                        "Example: \"git ls-files | xargs grep -c ... -> 12\" with the output pasted "
                        "underneath, or \"read docs/DATA.md lines 40-52\"."
                    ),
                    "false": (
                        "Only the conclusion of the check is given. Example: \"I checked every "
                        "entry and they all match\" with no command, no output and no source named."
                    ),
                },
            },
            "is_verification_claim": {
                "type": "noul",
                "instructions": (
                    "`fragment_a` asserts that the author personally performed a check, reading, "
                    "run or comparison — as opposed to describing a plan or a rule."
                ),
                "criteria": {
                    "true": (
                        "The sentence reports something the author already did. Example: "
                        "\"I read all 34 findings\", \"the counts were re-run\", "
                        "\"the two tables were compared\"."
                    ),
                    "false": (
                        "The sentence states a plan, a rule or someone else's action. Example: "
                        "\"the auditor must read every finding\", \"this will be measured later\", "
                        "\"the procedure says to re-count\"."
                    ),
                },
            },
        }
    if kind == "universal_claim":
        return {
            "enumeration_attached": {
                "type": "noul",
                "instructions": (
                    "A count, a listing, or command output that enumerates the set appears in "
                    "`fragment_a` or `fragment_b`."
                ),
                "criteria": {
                    "true": (
                        "The set is enumerated or counted. Example: a table with one row per item "
                        "and a total, or \"git ls-files | wc -l -> 2130\" with the output shown."
                    ),
                    "false": (
                        "Completeness is asserted with no enumeration and no count. Example: "
                        "\"this is the whole set of the owner's corrections\" with nothing listing "
                        "or counting them."
                    ),
                },
            },
            "is_universal_claim": {
                "type": "noul",
                "instructions": (
                    "`fragment_a` claims completeness — that a set is entire, that every item was "
                    "covered, or that nothing was left out."
                ),
                "criteria": {
                    "true": (
                        "The sentence asserts that nothing is missing. Example: \"these 16 are all "
                        "of the owner's interventions\", \"every route was tried\", "
                        "\"no case was left out\"."
                    ),
                    "false": (
                        "The word for 'all' applies to something else, or the sentence does not "
                        "claim a complete set. Example: \"all of this is explained below\", "
                        "\"treating every one of them as blocking is excessive\"."
                    ),
                },
            },
        }
    if kind == "negative_claim":
        return {
            "scope_and_method_attached": {
                "type": "noul",
                "instructions": (
                    "`fragment_a` states that something cannot be obtained, does not exist, is not "
                    "possible, or was not found. Judge whether that claim is accompanied, in "
                    "`fragment_a` or `fragment_b`, by the range that was actually checked (which "
                    "venues, which routes, which environment) and by the method used to check it."
                ),
                "criteria": {
                    "true": (
                        "The range and the method are both written down. Example: \"Binance Vision, "
                        "Gate.io, OKX and ccxt were each requested with GET, and only Gate.io returned "
                        "data\", or \"checked on the owner's PC with the reachability probe script\"."
                    ),
                    "false": (
                        "The claim stands with no range, or with no method, or generalises one "
                        "observation to everything. Example: \"no venue publishes a free liquidation "
                        "archive\" backed only by one 404 on one file at one venue, or \"the data does "
                        "not exist\" with nothing said about what was tried."
                    ),
                },
            },
            # presence は別の問いに分ける(ベンダー: 「use a separate presence judgment when it is
            # independently useful」)。同じ state への独立した問いなので 1 要求にまとめる。
            "is_unavailability_claim": {
                "type": "noul",
                "instructions": (
                    "`fragment_a` asserts that some data, route, resource or action is unavailable, "
                    "nonexistent, unobtainable or impossible (as opposed to an ordinary negated "
                    "statement such as 'does not apply', 'is not used', 'did not change')."
                ),
                "criteria": {
                    "true": (
                        "The sentence says something cannot be had or does not exist. Example: "
                        "\"no free liquidation archive exists anywhere\", or \"OKX open-interest "
                        "history cannot be obtained\"."
                    ),
                    "false": (
                        "The sentence merely negates an ordinary statement, or it is a declaration of "
                        "what this report does not claim or cannot say (a scope statement such as "
                        "\"言えないこと: ...\", \"射程外\", \"未測定\"). Example: \"this rule does "
                        "not apply to 30-minute bars\", \"the value did not change\", \"we do not "
                        "use the taker side\", or \"what this unit cannot say: whether it works on "
                        "unseen data\"."
                    ),
                },
            },
        }
    if kind == "symbol_definition":
        term = pair.get("term", "")
        return {
            "same_meaning": {
                "type": "noul",
                "instructions": (
                    f"`fragment_a` and `fragment_b` are two sentences from the same document that each "
                    f"define the symbol or term `{term}`. Judge whether both sentences give that symbol "
                    "the same meaning: the same quantity, over the same population, with the same sign "
                    "convention and the same unit."
                ),
                "criteria": {
                    "true": (
                        "Both sentences define the same quantity, or the second merely restates the "
                        "first. Example: \"sd is the standard deviation of the h-bar forward return\" "
                        "and \"sd is that same forward-return standard deviation, in bp\"."
                    ),
                    "false": (
                        "The two sentences attach the symbol to different quantities. Example: `sd` is "
                        "introduced as the unsigned market noise over all candles, and elsewhere used as "
                        "the signed per-trade result of the strategy."
                    ),
                },
            }
        }
    # scope_vs_bar / intent_vs_measured / why_section
    return {
        "relation": {
            "type": "choice",
            "instructions": (
                "`fragment_a` and `fragment_b` come from the same piece of work; `fragment_a_role` and "
                "`fragment_b_role` say what each one is. Judge how `fragment_b` relates to `fragment_a`."
            ),
            "criteria": {
                "consistent": (
                    "`fragment_b` stays inside what `fragment_a` allows or requires. Example: the scope "
                    "says execution cost is out of scope and the acceptance bar is expressed purely as "
                    "signal strength; or the section names which part of the mechanism produced the "
                    "result."
                ),
                "contradicts": (
                    "`fragment_b` does something `fragment_a` rules out, or omits something "
                    "`fragment_a` requires. Example: the scope says \"profit and loss including "
                    "execution is out of scope\" while the acceptance bar is a round-trip fee of +5 bp; "
                    "or an item marked ○ in the intent map is absent from what is measured; or the "
                    "results are stated with no mechanism given."
                ),
                "unrelated": (
                    "`fragment_b` does not speak to `fragment_a` at all: different subject matter, so "
                    "neither agreement nor conflict can be read from it."
                ),
            },
        }
    }


# presence を別の問いに分ける種類: kind -> (presence の問い ID, 「添えられているか」の問い ID)
PRESENCE_QIDS = {
    "negative_claim": ("is_unavailability_claim", "scope_and_method_attached"),
    "verification_claim": ("is_verification_claim", "evidence_attached"),
    "universal_claim": ("is_universal_claim", "enumeration_attached"),
}


def violation_probability(kind: str, answers: dict) -> tuple[str, float]:
    """(問い ID, 「反する」側の確率)。

    noul の問いは肯定形(「添えられている」「同じ意味である」)で書くので、**「反する」側の
    確率は code 側で `1 - noul` として出す**(ベンダー: 否定形・二重否定の問いは精度が落ちる)。
    choice は `contradicts` の確率をそのまま使う。
    """
    if kind in PRESENCE_QIDS:
        qid = PRESENCE_QIDS[kind][1]
        return qid, 1.0 - float(answers[qid]["noul"])
    if kind == "symbol_definition":
        return "same_meaning", 1.0 - float(answers["same_meaning"]["noul"])
    probs = answers["relation"].get("probabilities") or {}
    return "relation", float(probs.get("contradicts", 0.0))


def flag_for(p: float) -> bool:
    """「反する」側の確率が `ATTENTION` 以上なら要確認の印。**印であって結論ではない。**"""
    return p >= ATTENTION


def presence_qid(kind: str) -> str | None:
    """その種類の presence の問い ID(無ければ None)。"""
    pair = PRESENCE_QIDS.get(kind)
    return pair[0] if pair else None


def presence_probability(kind: str, answers: dict) -> float | None:
    """presence の問い(そもそもその型の主張か)の確率。持たない種類では None。"""
    qid = presence_qid(kind)
    if qid is None:
        return None
    return float(answers[qid]["noul"])


def decide_flag(kind: str, viol: float, presence: float | None) -> tuple[bool, str | None]:
    """(印, 印を付けなかった理由)。

    presence を持つ種類は **presence と「添えられているか」の両方**を満たしたときだけ印を付ける
    (presence >= `PRESENCE` かつ 反する側 >= `ATTENTION`)。
    presence が足りない対も**捨てず**に理由付きで残す。
    """
    qid = presence_qid(kind)
    if qid is not None:
        if presence is None or presence < PRESENCE:
            return False, "not_" + qid.removeprefix("is_")
        return flag_for(viol), None
    return flag_for(viol), None


def flag_counts(records: list[dict]) -> tuple[int, dict[str, int]]:
    """(印の付いた対の件数, 種類ごとの内訳)。"""
    by_kind: dict[str, int] = {}
    total = 0
    for rec in records:
        if rec.get("flag"):
            total += 1
            by_kind[rec["kind"]] = by_kind.get(rec["kind"], 0) + 1
    return total, by_kind


# ---------------------------------------------------------------------------
# 送信前の伏せ字
# ---------------------------------------------------------------------------
def clean_state(state: dict) -> dict:
    """`redact_json` を当ててから、全文字列に `assert_clean`。落ちたら `RedactionError`。"""
    cleaned = redact_json(state)

    def walk(obj):
        if isinstance(obj, str):
            assert_clean(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                walk(v)

    walk(cleaned)
    return cleaned


def state_for(pair: dict) -> dict:
    state = {
        "kind": pair["kind"],
        "fragment_a_role": pair["a_role"],
        "fragment_a": pair["a"],
        "fragment_b_role": pair["b_role"],
        "fragment_b": pair["b"],
    }
    if "term" in pair:
        state["term"] = pair["term"]
    return state


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------
def cmd_audit(args) -> int:
    artifact = Path(args.artifact)
    if not artifact.is_file():
        print(f"[jev_check] 成果物が無い: {artifact}", file=sys.stderr)
        return 1
    text = artifact.read_text(encoding="utf-8", errors="replace")
    pairs, n_truncated = cap_negative_claims(extract_pairs(text, artifact))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{artifact.stem}.jsonl"

    client = None
    unreachable: str | None = None
    if not args.dry_run:
        try:
            client = JevClient(model=args.model)
        except JevError as e:
            unreachable = str(e)

    records: list[dict] = []
    n_requests = 0
    for pair in pairs:
        rec = {
            "file": artifact.name,
            "kind": pair["kind"],
            "anchor": pair["anchor"],
            "a": pair["a"],
            "b": pair["b"],
            "question": None,
            "probability": None,
            "violation_probability": None,
            "presence_probability": None,
            "flag": False,
            "reason": None,
            "sent": False,
        }
        if "term" in pair:
            rec["term"] = pair["term"]

        if pair["kind"] == "number_vs_source":
            # code だけで印を付ける(Jev へ送らない)。突き合わせ先が 1 件も無いときは
            # 比較が成立しないので印を付けず、その事実を記録する。
            rec["number"] = pair["number"]
            rec["no_source_files"] = pair["no_source_files"]
            rec["flag"] = not pair["no_source_files"]
            records.append(rec)
            continue

        if args.dry_run or client is None:
            records.append(rec)
            continue

        questions = question_for(pair["kind"], pair)
        try:
            state = clean_state(state_for(pair))
        except RedactionError as e:
            print(f"[jev_check] 伏せ字の最終検査に掛かったので送信しない: {e}", file=sys.stderr)
            return 2
        try:
            resp = client.evaluate(state=state, questions=questions)
        except JevError as e:
            unreachable = str(e)
            print(f"[jev_check] 送信に失敗({pair['kind']} @ {pair['anchor']}): {e}",
                  file=sys.stderr)
            records.append(rec)
            continue
        n_requests += 1
        answers = resp.get("answers") or {}
        qid, viol = violation_probability(pair["kind"], answers)
        presence = presence_probability(pair["kind"], answers)
        rec["question"] = qid
        rec["probability"] = answers.get(qid)
        rec["violation_probability"] = round(viol, 4)
        if presence is not None:
            rec["presence_probability"] = round(presence, 4)
            rec["presence_answer"] = answers.get(presence_qid(pair["kind"]))
        rec["flag"], rec["reason"] = decide_flag(pair["kind"], viol, presence)
        rec["sent"] = True
        rec["model"] = resp.get("model")
        records.append(rec)

    n_to_send = sum(1 for p in pairs if p["kind"] != "number_vs_source")
    # 1 つも届かなかったときだけ「未到達」と言う(沈黙を「異常なし」と読ませない)
    if args.dry_run or n_to_send == 0 or n_requests > 0:
        unreachable = None

    n_flag, by_kind = flag_counts(records)
    summary = {
        "file": artifact.name,
        "kind": "_summary",
        "n_pairs": len(pairs),
        "n_sent": sum(1 for r in records if r["sent"]),
        "n_requests": n_requests,
        "n_flag": n_flag,
        "flag_by_kind": by_kind,
        "truncated_pairs": n_truncated,
        "dry_run": bool(args.dry_run),
        "unreachable": unreachable,
        "threshold": {"attention": ATTENTION},
    }

    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")

    if not args.summary:
        _print_table(artifact, records, summary)
    print(summary_line(summary))
    return 0


def summary_line(summary: dict) -> str:
    """末尾の 1 行。Stop フックはこの 1 行をそのまま表示に使う。"""
    if summary.get("unreachable"):
        return f"jev: 未到達({summary['unreachable']})"
    by_kind = summary.get("flag_by_kind") or {}
    detail = "、".join(f"{k} {v} 件" for k, v in sorted(by_kind.items())) or "内訳なし"
    tail = "(--dry-run: 1 件も送っていない)" if summary.get("dry_run") else ""
    return f"印 {summary.get('n_flag', 0)} 件({detail}){tail}"


def _print_table(artifact: Path, records: list[dict], summary: dict) -> None:
    print(f"成果物: {artifact.name}  対の数: {summary['n_pairs']}  "
          f"送った要求の数: {summary['n_requests']}"
          + (f"  切った negative_claim: {summary['truncated_pairs']} 件"
             if summary.get("truncated_pairs") else "")
          + ("  (--dry-run: 1 件も送っていない)" if summary["dry_run"] else ""))
    counts: dict[str, int] = {}
    for rec in records:
        counts[rec["kind"]] = counts.get(rec["kind"], 0) + 1
    if counts:
        print("種類ごとの件数: " + " / ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"{'対の種類':<20}{'行':>6}{'反する確率':>12}{'印':>4}  先頭")
    for rec in records:
        p = rec["violation_probability"]
        p_s = "-" if p is None else f"{p:.3f}"
        head = rec["a"].replace("\n", " ")[:60]
        mark = "要確認" if rec["flag"] else ""
        print(f"{rec['kind']:<20}{rec['anchor']:>6}{p_s:>12}{mark:>4}  {head}")
    print(f"(印のしきい値 attention={ATTENTION}。**印であって判断ではない**)")


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------
def _load_summaries(out_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(out_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get("kind") == "_summary":
                    out[d["file"]] = d
    return out


def _control_files(paths: list[str]) -> list[str]:
    """`--controls` に渡された dir / ファイルを、成果物名(ファイル名)の一覧に展開する。"""
    names: list[str] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            names += [f.name for f in sorted(p.glob("*.md"))]
        elif p.is_file():
            names.append(p.name)
        else:
            print(f"[jev_check] 対照が見つからない: {p}", file=sys.stderr)
    seen: set[str] = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def cmd_score(args) -> int:
    summaries = _load_summaries(Path(args.dir))
    detected_n = missed_n = false_n = ok_n = 0
    n_unevaluated = 0

    with Path(args.labels).open(encoding="utf-8", newline="") as fh:
        label_rows = list(csv.DictReader(fh))

    # 対照(オーナーの訂正が無かった成果物)は has_answer=0 の行として足す。
    # ラベルに同じ名前があればラベルを優先する(二重に数えない)。
    labeled = {r["file"] for r in label_rows}
    rows = [(r["file"], int((r.get("has_answer") or "0").strip() or 0)) for r in label_rows]
    n_controls = 0
    for name in _control_files(getattr(args, "controls", None) or []):
        if name in labeled:
            print(f"[jev_check] 対照 {name} はラベルにもあるのでラベルを使う", file=sys.stderr)
            continue
        rows.append((name, 0))
        n_controls += 1

    print(f"{'成果物':<28}{'has_answer':>12}{'印の件数':>10}{'突き合わせ':>12}")
    for fname, has_answer in rows:
        summary = summaries.get(fname)
        # 送っていない回(--dry-run)と、1 つも届かなかった回は「未評価」に置く。
        # 印が 0 件なのは「無かった」からではないので、見逃しに数えない。
        if (summary is None or summary.get("n_flag") is None
                or summary.get("dry_run") or summary.get("unreachable")):
            n_unevaluated += 1
            print(f"{fname:<28}{has_answer:>12}{'-':>10}{'未評価':>12}")
            continue
        n_flag = summary["n_flag"]
        detected = n_flag > 0
        if has_answer == 1 and detected:
            verdict = "検出"
            detected_n += 1
        elif has_answer == 1:
            verdict = "見逃し"
            missed_n += 1
        elif detected:
            verdict = "誤検出"
            false_n += 1
        else:
            verdict = "該当なし"
            ok_n += 1
        print(f"{fname:<28}{has_answer:>12}{n_flag:>10}{verdict:>12}")

    print("")
    print(f"検出 {detected_n} 件 / 見逃し {missed_n} 件 / 誤検出 {false_n} 件 / "
          f"該当なし・印なし {ok_n} 件 / 未評価 {n_unevaluated} 件"
          + (f"(うち対照 {n_controls} 件)" if n_controls else ""))
    print(f"しきい値: attention={ATTENTION}(印が 1 つでも付けば検出)")
    return 0


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="成果物から対を code で切り出し、対ごとに狭い問いを Jev へ投げる")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit")
    p_audit.add_argument("artifact")
    p_audit.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p_audit.add_argument("--dry-run", action="store_true")
    p_audit.add_argument("--summary", action="store_true",
                         help="末尾の 1 行だけを出す(Stop フックの表示用)")
    p_audit.add_argument("--model", default=DEFAULT_MODEL)
    p_audit.set_defaults(func=cmd_audit)

    p_score = sub.add_parser("score")
    p_score.add_argument("--labels", required=True)
    p_score.add_argument("--dir", required=True)
    p_score.add_argument("--controls", nargs="+", default=[],
                         help="オーナーの訂正が無かった成果物(dir かファイル)。has_answer=0 として採点に入れる")
    p_score.set_defaults(func=cmd_score)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
