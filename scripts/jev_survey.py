#!/usr/bin/env python3
"""調査班の報告 1 本から「対」と「項目」を code で切り出し、狭い問いを Jev へ投げる道具。

出所: `docs/JEV.md` §8 の U5(調査結果の仕分けと順位付け、**オーナーの例**)と
U6(主張 × 一次資料の引用の検証)、§6-3。料理本 E.1(引用検証)・E.5(再ランク)・
E.11(RAG の選別)の型をこの体制の言葉で使う。

**この道具は何も止めないし、何かを良しともしない**(オーナー逐語 L-218:
「**そもそも止めるとjev出させようとするのは間違った運用で、判断はLLMと私の役割である**」)。
出すのは確率と、**要確認の印(flag)**、そして code が重みで作った順位だけである。

  verify  … 対 = (主張, 引用)。裏付け / 矛盾 / 何も言っていない と、出典の記載の有無。
  triage  … 項目 = 「### 出典」表と「### 知見」表の行。一次/二次/共同体/宣伝、関連、
            在庫との重複、要プローブ。順位は **code** が重みで作る(Jev は順位を作らない)。

使い方:
  python3 scripts/jev_survey.py verify <報告.md> [--dry-run] [--summary] [--model ID]
  python3 scripts/jev_survey.py triage <報告.md> [--question "<問い>"] [--dry-run] [--summary]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.jev.client import JevClient, JevError  # noqa: E402
from scripts.jev.redact import RedactionError  # noqa: E402
# しきい値・伏せ字の作法・末尾 1 行は `jev_check` から import して使う(複製しない)。
from scripts.jev_check import (  # noqa: E402
    ATTENTION,
    PRESENCE,
    DEFAULT_MODEL,
    clean_state,
    flag_counts,
    summary_line,
    sections,
)

# ---------------------------------------------------------------------------
# 定数(しきい値は import した 1 箇所のまま。ここで数値を書き直さない)
# ---------------------------------------------------------------------------
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "survey"
MAX_FRAGMENT_CHARS = 2_000
QUOTE_MIN_CHARS = 20          # 「」で囲まれた引用として拾う最小の長さ(仕様)
URL_NEAR_LINES = 3            # コードブロックを引用とみなす URL の距離(仕様)
CLAIM_LOOKBACK_LINES = 3      # 引用の直前に主張の文を探す行数(仕様)
CITATION_FALLBACK_LINES = 10  # 見出しが無い文書で出典の記載を探す窓(上下)
MAX_INVENTORY_NAMES = 200     # state に入れる在庫名の上限

# 順位の重み(**code** が作る。Jev は順位を作らない)
RANK_WEIGHTS = {"relevance": 0.5, "primary": 0.3, "novelty": 0.2}

# このプロジェクトの問い(`--question` が無いときの既定)
DEFAULT_QUESTION = (
    "トレードにより実用的な収益基盤を構築するために、"
    "暗号資産(→ FX → 株)の自動取引 bot と自律 AI トレーダーの知見を深めたい。"
    "そのために使えるデータ・経路・機構はどれか。"
)

_URL_RE = re.compile(r"https?://\S+")
_QUOTE_JA_RE = re.compile(r"「([^「」]{%d,})」" % QUOTE_MIN_CHARS)
_FENCE_RE = re.compile(r"^\s*```")
_CITATION_HINT_RE = re.compile(r"https?://|取得日|取得方法|HTTP|http コード|ステータス|status")
_SEPARATOR_RE = re.compile(r":?-{2,}:?")

SOURCE_HEADING_RE = re.compile(r"出典")
FINDING_HEADING_RE = re.compile(r"知見")
CLAIM_HEADING_RE = re.compile(r"主張")


def _clip(text: str) -> str:
    return text.strip()[:MAX_FRAGMENT_CHARS]


# ---------------------------------------------------------------------------
# 引用の抽出(3 型)
# ---------------------------------------------------------------------------
def _fence_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """コード柵の範囲(1 始まり、両端を含む)。"""
    out: list[tuple[int, int]] = []
    start: int | None = None
    for i, line in enumerate(lines, start=1):
        if _FENCE_RE.match(line):
            if start is None:
                start = i
            else:
                out.append((start, i))
                start = None
    if start is not None:
        out.append((start, len(lines)))
    return out


def extract_quotes(text: str) -> list[dict]:
    """引用の候補。3 型(blockquote / 「」20 字以上 / URL の近くのコードブロック)。"""
    lines = text.splitlines()
    fences = _fence_ranges(lines)
    in_fence = {i for lo, hi in fences for i in range(lo, hi + 1)}
    quotes: list[dict] = []

    # (1) blockquote(`>` の連続)
    i = 0
    while i < len(lines):
        ln = i + 1
        if ln in in_fence or not lines[i].lstrip().startswith(">"):
            i += 1
            continue
        start = ln
        body: list[str] = []
        while i < len(lines) and lines[i].lstrip().startswith(">"):
            body.append(re.sub(r"^\s*>\s?", "", lines[i]))
            i += 1
        joined = "\n".join(body).strip()
        if joined:
            quotes.append({"type": "blockquote", "start": start, "end": i, "text": _clip(joined)})

    # (2) 「」で囲まれた 20 字以上
    for ln, line in enumerate(lines, start=1):
        if ln in in_fence:
            continue
        for m in _QUOTE_JA_RE.finditer(line):
            quotes.append({"type": "corner_quote", "start": ln, "end": ln,
                           "text": _clip(m.group(1))})

    # (3) URL が 3 行以内にあるコードブロック
    for lo, hi in fences:
        near = "\n".join(lines[max(0, lo - 1 - URL_NEAR_LINES):min(len(lines), hi + URL_NEAR_LINES)])
        if not _URL_RE.search(near):
            continue
        body = "\n".join(lines[lo:hi - 1]).strip()
        if body:
            quotes.append({"type": "code_block", "start": lo, "end": hi, "text": _clip(body)})

    return sorted(quotes, key=lambda q: (q["start"], q["type"]))


def _claim_section_body(text: str) -> str:
    for sec in sections(text):
        if CLAIM_HEADING_RE.search(sec["title"]):
            body = sec["body"].strip()
            if body:
                return _clip(body)
    return ""


def _claim_same_line(line: str, quote: str) -> str:
    """同じ行で引用の前にある文(`…こうある:「引用」` の型)。**これも「引用の直前」である。**"""
    head = line.split("「" + quote[:20])[0] if quote else ""
    head = head.strip().lstrip("#>-*+ ").strip()
    parts = [p.strip() for p in re.split(r"(?<=。)", head) if p.strip()]
    return _clip(parts[-1]) if parts else ""


def _claim_before(lines: list[str], start: int) -> str:
    """引用の直前 3 行以内の文(見出し・表・柵は主張にしない)。"""
    found: list[str] = []
    for ln in range(start - 1, max(0, start - 1 - CLAIM_LOOKBACK_LINES), -1):
        body = lines[ln - 1].strip()
        if not body:
            continue
        if body.startswith(("#", "|", ">", "```")):
            continue
        body = re.sub(r"^[-*+]\s+", "", body)
        parts = [p.strip() for p in re.split(r"(?<=。)", body) if p.strip()]
        if parts:
            found = parts
            break
    return _clip(found[-1]) if found else ""


def _citation_window(text: str, lines: list[str], start: int, end: int) -> tuple[int, int]:
    """出典の記載を探す範囲。引用のある節と、その 1 つ前の節(`## 一次資料` の型)。

    見出しが無い文書では前後 `CITATION_FALLBACK_LINES` 行にする。
    """
    secs = sections(text)
    for idx, sec in enumerate(secs):
        if sec["lineno"] <= start <= sec["end"]:
            lo = secs[idx - 1]["lineno"] if idx > 0 else sec["lineno"]
            return lo, min(len(lines), max(sec["end"], end))
    lo = max(1, start - CITATION_FALLBACK_LINES)
    return lo, min(len(lines), end + CITATION_FALLBACK_LINES)


def _citation_note(text: str, lines: list[str], start: int, end: int) -> str:
    lo, hi = _citation_window(text, lines, start, end)
    hits = [lines[i - 1].strip() for i in range(lo, hi + 1)
            if _CITATION_HINT_RE.search(lines[i - 1])]
    return _clip("\n".join(hits))


def extract_verify_pairs(text: str) -> list[dict]:
    """対 = (主張, 引用)。主張は `## 主張` 節の文、または引用の直前 3 行以内の文。"""
    lines = text.splitlines()
    section_claim = _claim_section_body(text)
    pairs: list[dict] = []
    for q in extract_quotes(text):
        same_line = (_claim_same_line(lines[q["start"] - 1], q["text"])
                     if q["type"] == "corner_quote" else "")
        claim = same_line or _claim_before(lines, q["start"]) or section_claim
        if not claim:
            continue  # 主張が見つからない引用は対にならない
        pairs.append({
            "kind": "citation_" + q["type"],
            "anchor": q["start"],
            "claim": claim,
            "state": {
                "claim": claim,
                "quoted_source": q["text"],
                "citation_note": _citation_note(text, lines, q["start"], q["end"]),
            },
        })
    return pairs


# ---------------------------------------------------------------------------
# 表の読み取り(triage)
# ---------------------------------------------------------------------------
def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in body.split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(_SEPARATOR_RE.fullmatch(c) for c in cells if c)


def read_tables(body: str, base_lineno: int) -> list[tuple[int, list[str], list[str]]]:
    """(行番号, 見出しの一覧, セルの一覧) を返す。"""
    lines = body.splitlines()
    out: list[tuple[int, list[str], list[str]]] = []
    i = 0
    while i < len(lines):
        if not lines[i].strip().startswith("|"):
            i += 1
            continue
        block_start = i
        block: list[str] = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            block.append(lines[i])
            i += 1
        if len(block) < 2:
            continue
        header = _cells(block[0])
        for offset, row in enumerate(block[1:], start=1):
            cells = _cells(row)
            if _is_separator(cells) or not any(cells):
                continue
            out.append((base_lineno + block_start + offset, header, cells))
    return out


def _col(header: list[str], cells: list[str], pattern: str) -> str:
    rx = re.compile(pattern)
    for idx, name in enumerate(header):
        if rx.search(name) and idx < len(cells):
            return cells[idx].strip()
    return ""


def extract_items(text: str) -> list[dict]:
    """項目 = 「### 出典」表の行(URL / 方法 / 取得日)と「### 知見」表の行。"""
    items: list[dict] = []
    for sec in sections(text):
        is_source = bool(SOURCE_HEADING_RE.search(sec["title"]))
        is_finding = bool(FINDING_HEADING_RE.search(sec["title"]))
        if not (is_source or is_finding):
            continue
        for lineno, header, cells in read_tables(sec["body"], sec["lineno"]):
            url = _col(header, cells, r"URL|url|所在|リンク")
            if not url:
                m = _URL_RE.search(" ".join(cells))
                url = m.group(0) if m else ""
            method = _col(header, cells, r"方法|取得方法|経路")
            date = _col(header, cells, r"取得日|確認日|日付")
            title = _col(header, cells, r"知見|見出し|題|内容") or cells[0]
            if not (url or title):
                continue
            items.append({
                "kind": "source_row" if is_source else "finding_row",
                "anchor": lineno,
                "claim": _clip(title or url),
                "item": {
                    "url": url,
                    "title_or_snippet": _clip(title),
                    "method": method,
                    "date": date,
                },
            })
    return items


def inventory_names(repo: Path = REPO) -> list[str]:
    """在庫の名前。`docs/DATA.md` の表の 1 列目と `docs/STRATEGY_IDEAS.md` の見出し。"""
    names: list[str] = []
    data_md = repo / "docs" / "DATA.md"
    if data_md.is_file():
        for line in data_md.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = _cells(line)
            if not cells or _is_separator(cells):
                continue
            first = re.sub(r"[`*]", "", cells[0]).strip()
            if first and len(first) <= 80:
                names.append(first)
    ideas = repo / "docs" / "STRATEGY_IDEAS.md"
    if ideas.is_file():
        for line in ideas.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^#{2,6}\s+(.*\S)\s*$", line)
            if m:
                names.append(re.sub(r"[`*]", "", m.group(1)).strip())
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out[:MAX_INVENTORY_NAMES]


# ---------------------------------------------------------------------------
# 問い(1 判断 1 問・肯定形・criteria は具体例つき・英語。断片は日本語のまま)
# ---------------------------------------------------------------------------
def questions_verify() -> dict:
    """E.1(引用検証)の文言を基にした 2 問。1 要求にまとめる。"""
    return {
        "relation": {
            "type": "choice",
            "instructions": "How does `quoted_source` relate to `claim`?",
            "criteria": {
                "confirms": (
                    "The quoted passage states the claim or directly implies that it is true. "
                    "Example: the claim is \"the public trade history is kept for 31 days\" and "
                    "the quote says \"Executions are available for the last 31 days\"."
                ),
                "contradicts": (
                    "The quoted passage states the opposite of the claim or implies it is false. "
                    "Example: the claim is \"the endpoint needs no key\" and the quote says "
                    "\"This endpoint requires authentication\"."
                ),
                "says_nothing": (
                    "The quoted passage does not address what the claim asserts, either way. "
                    "Example: the claim is about the retention period and the quote only "
                    "describes the rate limit."
                ),
            },
        },
        "scope_stated": {
            "type": "noul",
            "instructions": (
                "URL, retrieval date and HTTP status are recorded for the quote, in "
                "`citation_note`."
            ),
            "criteria": {
                "true": (
                    "All three are written down. Example: \"URL: https://... / 取得日: "
                    "2026-09-19 / HTTP 200\"."
                ),
                "false": (
                    "At least one of URL, retrieval date or HTTP status is missing. Example: the "
                    "note carries only a URL, or only \"公式ドキュメントより\" with no URL, no "
                    "date and no status."
                ),
            },
        },
    }


def questions_triage() -> dict:
    """E.5(再ランク)と E.11(RAG の選別)の型。4 問を 1 要求にまとめる。"""
    return {
        "source_type": {
            "type": "choice",
            "instructions": "What kind of source is `item`?",
            "criteria": {
                "primary": (
                    "The operator of the thing itself publishes it: an exchange's own API "
                    "reference or status page, a regulator's filing, the paper that reports the "
                    "experiment, the vendor's own specification of behaviour. Example: "
                    "https://lightning.bitflyer.com/docs, an SEC filing, an arXiv paper."
                ),
                "secondary": (
                    "A third party reports on a primary source: a news article, an aggregator, a "
                    "textbook, a market-data company's summary."
                ),
                "community": (
                    "An individual or a community writes from their own use: a blog post, a "
                    "GitHub issue, a forum thread, a social-media post."
                ),
                "vendor_marketing": (
                    "The seller promotes its own product: a landing page, a launch announcement, "
                    "a benchmark the seller ran on itself."
                ),
                "unknown": "The item does not say enough to place it in any of the above.",
            },
        },
        "relevance": {
            "type": "noul",
            "instructions": "`item` bears on `our_question`.",
            "criteria": {
                "true": (
                    "The item supplies data, a route, a mechanism or a constraint that the "
                    "question needs. Example: the question asks which venues publish liquidation "
                    "history and the item is a venue's liquidation endpoint."
                ),
                "false": (
                    "The item is about something else. Example: the question is about crypto "
                    "market microstructure and the item is a press release about a token listing "
                    "on an unrelated chain."
                ),
            },
        },
        "duplicate_of_inventory": {
            "type": "noul",
            "instructions": "`item` is already covered by one of `inventory_names`.",
            "criteria": {
                "true": (
                    "The same dataset, endpoint or idea is already in the inventory under another "
                    "wording. Example: the item is \"Binance Vision daily trades\" and the "
                    "inventory already lists \"Binance の公開約定(Vision)\"."
                ),
                "false": (
                    "No inventory entry covers it. Example: the item is an exchange whose name "
                    "does not appear in the list at all."
                ),
            },
        },
        "needs_probe": {
            "type": "noul",
            "instructions": (
                "`item` asserts that data or an endpoint is available, and that assertion should "
                "be tested by making a request."
            ),
            "criteria": {
                "true": (
                    "The item claims something can be fetched, and no status code or byte count "
                    "shows it was fetched. Example: \"OKX publishes open-interest history via "
                    "/api/v5/rubik/stat\" with no HTTP status recorded."
                ),
                "false": (
                    "The item is an opinion, a mechanism, or an availability claim already backed "
                    "by a recorded request. Example: \"HTTP 200, 4,412 bytes, 2026-09-19\"."
                ),
            },
        },
    }


# ---------------------------------------------------------------------------
# 合成(印と順位。**印であって判断ではない**)
# ---------------------------------------------------------------------------
def _probs(answers: dict, qid: str) -> dict:
    return (answers.get(qid) or {}).get("probabilities") or {}


def combine_verify(answers: dict) -> dict:
    probs = _probs(answers, "relation")
    contradicts = float(probs.get("contradicts", 0.0))
    says_nothing = float(probs.get("says_nothing", 0.0))
    scope = float((answers.get("scope_stated") or {}).get("noul", 0.0))
    scope_viol = 1.0 - scope
    relation_flag = max(contradicts, says_nothing) >= ATTENTION
    scope_flag = scope_viol >= ATTENTION
    return {
        "violation_probability": round(max(contradicts, says_nothing), 4),
        "contradicts_probability": round(contradicts, 4),
        "says_nothing_probability": round(says_nothing, 4),
        "scope_stated_probability": round(scope, 4),
        "scope_violation_probability": round(scope_viol, 4),
        "relation_flag": relation_flag,
        "scope_flag": scope_flag,
        "flag": bool(relation_flag or scope_flag),
        "relation_probabilities": probs,
        "relation_confidence": (answers.get("relation") or {}).get("confidence"),
    }


def combine_triage(answers: dict) -> dict:
    relevance = float((answers.get("relevance") or {}).get("noul", 0.0))
    duplicate = float((answers.get("duplicate_of_inventory") or {}).get("noul", 0.0))
    needs_probe = float((answers.get("needs_probe") or {}).get("noul", 0.0))
    probs = _probs(answers, "source_type")
    primary = float(probs.get("primary", 0.0))
    novelty = 1.0 - duplicate
    rank = (RANK_WEIGHTS["relevance"] * relevance
            + RANK_WEIGHTS["primary"] * primary
            + RANK_WEIGHTS["novelty"] * novelty)
    return {
        "relevance_probability": round(relevance, 4),
        "primary_probability": round(primary, 4),
        "duplicate_probability": round(duplicate, 4),
        "novelty": round(novelty, 4),
        "needs_probe_probability": round(needs_probe, 4),
        "rank_score": round(rank, 4),
        "source_type": (max(probs, key=probs.get) if probs else None),
        "source_type_probabilities": probs,
        "source_type_confidence": (answers.get("source_type") or {}).get("confidence"),
        "flag": needs_probe >= PRESENCE,
        "reason": None if needs_probe >= PRESENCE else "needs_probe_below_presence",
    }


# ---------------------------------------------------------------------------
# 本体
# ---------------------------------------------------------------------------
def _send(client, state: dict, questions: dict) -> tuple[dict | None, str | None]:
    try:
        cleaned = clean_state(state)
    except RedactionError as e:
        return None, f"redaction:{e}"
    try:
        return client.evaluate(state=cleaned, questions=questions), None
    except JevError as e:
        return None, str(e)


def _write(out_dir: Path, stem: str, records: list[dict], summary: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return out_path


def cmd_verify(args) -> int:
    artifact = Path(args.artifact)
    if not artifact.is_file():
        print(f"[jev_survey] 報告が無い: {artifact}", file=sys.stderr)
        return 1
    text = artifact.read_text(encoding="utf-8", errors="replace")
    pairs = extract_verify_pairs(text)

    client, unreachable = None, None
    if not args.dry_run:
        try:
            client = JevClient(model=args.model)
        except JevError as e:
            unreachable = str(e)

    records: list[dict] = []
    n_requests = 0
    for pair in pairs:
        rec = {"file": artifact.name, "kind": pair["kind"], "anchor": pair["anchor"],
               "claim": pair["claim"], "flag": False, "reason": None, "sent": False}
        if args.dry_run or client is None:
            records.append(rec)
            continue
        resp, err = _send(client, pair["state"], questions_verify())
        if resp is None:
            if err and err.startswith("redaction:"):
                print(f"[jev_survey] 伏せ字の最終検査に掛かったので送信しない: {err}",
                      file=sys.stderr)
                return 2
            unreachable = err
            print(f"[jev_survey] 送信に失敗({pair['kind']} @ {pair['anchor']}): {err}",
                  file=sys.stderr)
            records.append(rec)
            continue
        n_requests += 1
        rec.update(combine_verify(resp.get("answers") or {}))
        rec["sent"] = True
        rec["model"] = resp.get("model")
        records.append(rec)

    if args.dry_run or not pairs or n_requests > 0:
        unreachable = None
    n_flag, by_kind = flag_counts(records)
    summary = {"file": artifact.name, "kind": "_summary", "mode": "verify",
               "n_pairs": len(pairs), "n_sent": sum(1 for r in records if r["sent"]),
               "n_requests": n_requests, "n_flag": n_flag, "flag_by_kind": by_kind,
               "dry_run": bool(args.dry_run), "unreachable": unreachable,
               "threshold": {"attention": ATTENTION, "presence": PRESENCE}}
    out_path = _write(Path(args.out), artifact.stem + "_verify", records, summary)

    if not args.summary:
        print(f"報告: {artifact.name}  対(主張 × 引用)の数: {len(pairs)}  "
              f"送った要求の数: {n_requests}"
              + ("  (--dry-run: 1 件も送っていない)" if args.dry_run else ""))
        counts: dict[str, int] = {}
        for rec in records:
            counts[rec["kind"]] = counts.get(rec["kind"], 0) + 1
        if counts:
            print("引用の型ごとの件数: " + " / ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        print(f"{'引用の型':<22}{'行':>6}{'反する確率':>12}{'記載欠け':>10}{'印':>6}  主張の先頭")
        for rec in records:
            p = rec.get("violation_probability")
            s = rec.get("scope_violation_probability")
            print(f"{rec['kind']:<22}{rec['anchor']:>6}"
                  f"{('-' if p is None else f'{p:.3f}'):>12}"
                  f"{('-' if s is None else f'{s:.3f}'):>10}"
                  f"{('要確認' if rec['flag'] else ''):>6}  "
                  f"{str(rec['claim']).replace(chr(10), ' ')[:50]}")
        print(f"(印のしきい値 attention={ATTENTION}。**印であって判断ではない**)")
        print(f"書いた先: {out_path}")
    print(summary_line(summary))
    return 0


def cmd_triage(args) -> int:
    artifact = Path(args.artifact)
    if not artifact.is_file():
        print(f"[jev_survey] 報告が無い: {artifact}", file=sys.stderr)
        return 1
    text = artifact.read_text(encoding="utf-8", errors="replace")
    items = extract_items(text)
    names = inventory_names()
    question = args.question or DEFAULT_QUESTION

    client, unreachable = None, None
    if not args.dry_run:
        try:
            client = JevClient(model=args.model)
        except JevError as e:
            unreachable = str(e)

    records: list[dict] = []
    n_requests = 0
    for item in items:
        rec = {"file": artifact.name, "kind": item["kind"], "anchor": item["anchor"],
               "claim": item["claim"], "item": item["item"], "flag": False,
               "reason": None, "sent": False, "rank_score": None}
        if args.dry_run or client is None:
            records.append(rec)
            continue
        state = {"item": item["item"], "our_question": question, "inventory_names": names}
        resp, err = _send(client, state, questions_triage())
        if resp is None:
            if err and err.startswith("redaction:"):
                print(f"[jev_survey] 伏せ字の最終検査に掛かったので送信しない: {err}",
                      file=sys.stderr)
                return 2
            unreachable = err
            print(f"[jev_survey] 送信に失敗({item['kind']} @ {item['anchor']}): {err}",
                  file=sys.stderr)
            records.append(rec)
            continue
        n_requests += 1
        rec.update(combine_triage(resp.get("answers") or {}))
        rec["sent"] = True
        rec["model"] = resp.get("model")
        records.append(rec)

    if args.dry_run or not items or n_requests > 0:
        unreachable = None
    ranked = sorted(records, key=lambda r: (-(r.get("rank_score") or 0.0), r["anchor"]))
    n_flag, by_kind = flag_counts(records)
    summary = {"file": artifact.name, "kind": "_summary", "mode": "triage",
               "n_items": len(items), "n_sent": sum(1 for r in records if r["sent"]),
               "n_requests": n_requests, "n_flag": n_flag, "flag_by_kind": by_kind,
               "inventory_names": len(names), "our_question": question,
               "rank_weights": RANK_WEIGHTS,
               "dry_run": bool(args.dry_run), "unreachable": unreachable,
               "threshold": {"attention": ATTENTION, "presence": PRESENCE}}
    out_path = _write(Path(args.out), artifact.stem + "_triage", ranked, summary)

    if not args.summary:
        print(f"報告: {artifact.name}  項目の数: {len(items)}  在庫名: {len(names)} 件  "
              f"送った要求の数: {n_requests}"
              + ("  (--dry-run: 1 件も送っていない)" if args.dry_run else ""))
        print(f"問い: {question}")
        print(f"順位の重み: {RANK_WEIGHTS}(順位は code が作る。Jev は順位を作らない)")
        print(f"{'順':>3} {'点':>7} {'型':<16}{'行':>6}{'要プローブ':>12}  項目")
        for i, rec in enumerate(ranked, start=1):
            score = rec.get("rank_score")
            probe = rec.get("needs_probe_probability")
            print(f"{i:>3} {('-' if score is None else f'{score:.3f}'):>7} "
                  f"{str(rec.get('source_type') or rec['kind']):<16}{rec['anchor']:>6}"
                  f"{('-' if probe is None else f'{probe:.3f}'):>12}  "
                  f"{str(rec['claim']).replace(chr(10), ' ')[:56]}")
        print(f"(印 = needs_probe >= {PRESENCE}。**印であって判断ではない**)")
        print(f"書いた先: {out_path}")
    print(summary_line(summary) + f" / 項目 {len(items)} 件")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="調査班の報告から対と項目を code で切り出し、狭い問いを Jev へ投げる")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_v = sub.add_parser("verify")
    p_v.add_argument("artifact")
    p_v.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p_v.add_argument("--dry-run", action="store_true")
    p_v.add_argument("--summary", action="store_true")
    p_v.add_argument("--model", default=DEFAULT_MODEL)
    p_v.set_defaults(func=cmd_verify)

    p_t = sub.add_parser("triage")
    p_t.add_argument("artifact")
    p_t.add_argument("--question", default=None, help="このプロジェクトの問い")
    p_t.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p_t.add_argument("--dry-run", action="store_true")
    p_t.add_argument("--summary", action="store_true")
    p_t.add_argument("--model", default=DEFAULT_MODEL)
    p_t.set_defaults(func=cmd_triage)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
