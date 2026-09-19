#!/usr/bin/env python3
"""委任先の報告 1 本の受領検査。code で検査できるものは code で、残りだけ Jev へ投げる道具。

出所: `docs/JEV.md` §8 の **U2(委任先の報告の受領検査)**。
検収の項目は `.claude/skills/delegated-study` §2 の【必須報告】7 項目と §6 の検収、
`.claude/skills/research-squad` §4・§5 の出力テンプレートと §6 の検収 5 項目から取った。

**この道具は何も止めないし、何かを良しともしない**(オーナー逐語 L-218:
「**そもそも止めるとjev出させようとするのは間違った運用で、判断はLLMと私の役割である**」)。
出すのは検査ごとの件数と確率、そして **要確認の印(flag)** だけである。
**「差し戻す」かどうかを決めるのはリードであって、この道具ではない。**

- 数える・見出しの有無・数値の突き合わせは **code**(`docs/JEV.md` §4-4)。
- Jev へ送るのは **狭い分類だけ**(対ごと・文ごとに 1 要求)。state は必ず code が組む(§4-2)。
- 問いは 1 判断 1 問・肯定形・criteria は具体例つき・英語(断片は日本語のまま)(§4-3)。
- しきい値(`ATTENTION` / `PRESENCE`)は `scripts/jev_check.py` の 1 箇所から import する。
- 送信前に `jev_check.clean_state`(`redact_json` + `assert_clean`)。落ちたら送らず終了コード 2。

使い方:
  python3 scripts/jev_report_intake.py check <報告.md> [--prompt <委任文.md>]
      [--kind research|survey|implementation] [--out DIR] [--dry-run] [--summary] [--model ID]
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
# しきい値・伏せ字の作法・印の合成・末尾 1 行・見出しの分解は `jev_check` から import して使う
# (複製しない。しきい値の在処は `jev_check` の 1 箇所のまま)。
from scripts.jev_check import (  # noqa: E402
    ATTENTION,
    DEFAULT_MODEL,
    PRESENCE,
    WHY_HEADING_RE,
    _NUMBER_RE,
    clean_state,
    decide_flag,
    extract_why_section,
    flag_counts,
    logical_lines,
    question_for,
    sections,
    summary_line,
    violation_probability,
)

# ---------------------------------------------------------------------------
# 定数(しきい値は import した 1 箇所のまま。ここで数値を書き直さない)
# ---------------------------------------------------------------------------
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "intake"
MAX_FRAGMENT_CHARS = 2_000
MAX_NUMBER_QUESTIONS = 30   # 出所の無い数値を Jev に聞く上限(仕様どおり)
MAX_VERDICT_QUESTIONS = 40  # 判定の語を含む文を Jev に聞く上限(`jev_check` の 40 に合わせた)
PROMPT_HEAD_CHARS = 4_000   # 委任文の先頭(仕様どおり)
CONCLUSION_CHARS = 1_500    # 最後の節の本文(仕様どおり)
CONTEXT_LINES = 3           # 数値・判定の語の「前後 3 行」(仕様どおり)

# 判定の語(仕様どおりの語をそのまま置く)
VERDICT_RE = re.compile(r"採用|棄却|合格|却下|不合格|有望|筋が悪い|効く|効かない")

_FENCE_RE = re.compile(r"^\s*```")
_TABLE_RE = re.compile(r"^\s*\|")
_QUOTE_LINE_RE = re.compile(r"^\s*>")

# 必須報告の見出し。語の一致は **見出しと節の先頭 2 行**だけで見る(この規則は出力に書く)。
HEADING_MATCH_RULE = "語の一致は見出しと節の先頭 2 行だけで見る(本文の奥は見ない)"
BODY_LINES_FOR_MATCH = 2

# (項目 ID, 表示名, 一致に使う語)
REQUIRED_ITEMS: dict[str, list[tuple[str, str, list[str]]]] = {
    # `delegated-study` §2 の【必須報告】7 項目
    "research": [
        ("grid", "探索区間の全構成表", ["全構成", "探索区間", "構成表"]),
        ("holdout", "判定区間の結果", ["判定区間", "判定の結果", "OOS"]),
        ("adverse", "逆選択の反実仮想", ["逆選択", "反実仮想"]),
        ("ablation", "アブレーション", ["アブレーション", "寄与分解"]),
        ("sanity", "サニティ", ["サニティ", "ルックアヘッド", "決定性"]),
        ("why", "なぜそうなるのかの理解", ["なぜ", "機構", "理解"]),
        ("limits", "注意点・限界", ["注意点", "限界", "射程"]),
    ],
    # `research-squad` §4・§5 の出力テンプレートの節
    "survey": [
        ("plan", "検索計画", ["検索計画", "クエリ", "width"]),
        ("sources", "出典", ["出典", "一次資料", "URL"]),
        ("findings", "知見", ["知見", "分かったこと"]),
        ("alt_route", "代替経路", ["代替経路", "到達できな", "別経路", "第2経路", "第 2 経路",
                                   "オーナー PC", "オーナーPC"]),
        ("candidates", "候補(提案。未マージ)", ["候補", "提案"]),
    ],
    # 実装の委任(報告に求める 4 項目)
    "implementation": [
        ("files", "作ったファイル", ["作ったファイル", "ファイルと行数", "新規ファイル",
                                     "変更したファイル", "差分"]),
        ("tests", "テストの末尾行", ["テスト", "pytest", "passed"]),
        ("off_spec", "仕様に無い判断", ["仕様に無い", "仕様にない", "仕様外", "独自の判断"]),
        ("mapping", "対応表", ["対応表", "原文"]),
    ],
}
KINDS = tuple(REQUIRED_ITEMS)
DEFAULT_KIND = "research"


def _clip(text: str, limit: int = MAX_FRAGMENT_CHARS) -> str:
    return text.strip()[:limit]


# ---------------------------------------------------------------------------
# 行の種類(すべて決定論的)
# ---------------------------------------------------------------------------
def fence_lines(text: str) -> set[int]:
    """コード柵の中(柵の行を含む)の行番号(1 始まり)。"""
    inside = False
    out: set[int] = set()
    for i, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(line):
            out.add(i)
            inside = not inside
            continue
        if inside:
            out.add(i)
    return out


def source_text_of(text: str) -> tuple[str, dict[str, int]]:
    """突き合わせ先(同じ報告の 表 / コードブロック / 引用)の本文と、その行数。

    `jev_check.extract_number_vs_source` は「同じディレクトリの csv/json/txt」を突き合わせ先に
    するが、委任先の報告は単体で届くので、**同じ文書の中の表・コードブロック・引用**を
    突き合わせ先にする(仕様どおり)。
    """
    fences = fence_lines(text)
    parts: list[str] = []
    counts = {"table": 0, "code": 0, "quote": 0}
    for i, line in enumerate(text.splitlines(), start=1):
        if i in fences:
            parts.append(line)
            counts["code"] += 1
        elif _TABLE_RE.match(line):
            parts.append(line)
            counts["table"] += 1
        elif _QUOTE_LINE_RE.match(line):
            parts.append(line)
            counts["quote"] += 1
    return "\n".join(parts), counts


def context_of(text: str, lineno: int, span: int = CONTEXT_LINES) -> str:
    """その行の前後 `span` 行(1 始まり)。"""
    lines = text.splitlines()
    lo = max(0, lineno - 1 - span)
    hi = min(len(lines), lineno + span)
    return _clip("\n".join(lines[lo:hi]))


# ---------------------------------------------------------------------------
# 1(a) 必須報告の見出しの有無(code)
# ---------------------------------------------------------------------------
def heading_scopes(text: str) -> list[str]:
    """見出しごとの「見出し + 本文の先頭 2 行」。語の一致はこの範囲だけで見る。"""
    out: list[str] = []
    for sec in sections(text):
        body = [ln for ln in sec["body"].splitlines() if ln.strip()][:BODY_LINES_FOR_MATCH]
        out.append("\n".join([sec["title"], *body]))
    return out


def check_required_items(text: str, kind: str) -> list[dict]:
    """必須項目ごとに (見つかったか, 当たった見出し) を返す。**code だけで決める。**"""
    scopes = heading_scopes(text)
    out: list[dict] = []
    for item_id, label, words in REQUIRED_ITEMS[kind]:
        hit = None
        for scope in scopes:
            if any(w in scope for w in words):
                hit = scope.splitlines()[0]
                break
        out.append({"item": item_id, "label": label, "words": words,
                    "found": hit is not None, "heading": hit})
    return out


# ---------------------------------------------------------------------------
# 1(b) 「なぜ」の節の有無(code)
# ---------------------------------------------------------------------------
def why_headings(text: str) -> list[str]:
    """見出しに「なぜ|機構|理解」を含む節の見出し(`jev_check.WHY_HEADING_RE` をそのまま使う)。"""
    return [s["title"] for s in sections(text) if WHY_HEADING_RE.search(s["title"])]


# ---------------------------------------------------------------------------
# 1(c) 判定の語を含む文の列挙(code)
# ---------------------------------------------------------------------------
def extract_verdict_sentences(text: str) -> list[dict]:
    """判定の語を含む文。コード柵の中は本文ではないので外す。"""
    fences = fence_lines(text)
    out: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for ln, body in logical_lines(text):
        if ln in fences:
            continue
        for part in re.split(r"(?<=。)", body):
            part = part.strip()
            if not part or not VERDICT_RE.search(part):
                continue
            key = (ln, part)
            if key in seen:
                continue
            seen.add(key)
            out.append({"kind": "verdict_sentence", "anchor": ln, "claim": _clip(part)})
    return out


# ---------------------------------------------------------------------------
# 1(d) 出所の無い数値(code)
# ---------------------------------------------------------------------------
def extract_unsourced_numbers(text: str) -> list[dict]:
    """本文の数値のうち、同じ報告の 表 / コードブロック / 引用 に文字列として現れないもの。

    作り(行ごとに `_NUMBER_RE` を当て、見出し行は外し、数値+単位で 1 件にまとめる)は
    `jev_check.extract_number_vs_source` と同じ。突き合わせ先だけを同じ文書の中に替えた。
    """
    source, counts = source_text_of(text)
    fences = fence_lines(text)
    found: dict[str, dict] = {}
    for i, line in enumerate(text.splitlines(), start=1):
        if i in fences or _TABLE_RE.match(line) or _QUOTE_LINE_RE.match(line):
            continue  # 突き合わせ先そのものは本文として数えない
        if line.lstrip().startswith("#"):
            continue
        for m in _NUMBER_RE.finditer(line):
            num, unit = m.group(1), (m.group(2) or "")
            if source and num in source:
                continue
            key = num + unit
            if key in found:
                continue
            found[key] = {
                "kind": "unsourced_number",
                "anchor": i,
                "number": key,
                "claim": _clip(line),
                "no_source_lines": not source,
            }
    for rec in found.values():
        rec["source_lines"] = dict(counts)
    return list(found.values())


# ---------------------------------------------------------------------------
# 2 Jev の問い(1 判断 1 問・肯定形・criteria は具体例つき・英語)
# ---------------------------------------------------------------------------
def questions_verdict() -> dict:
    """判定の語を含む文 1 件ずつ。**委任先は判定しない**(delegated-study「判定だけを返さない」)。"""
    return {
        "pronounces_verdict": {
            "type": "noul",
            "instructions": (
                "The sentence pronounces adoption, rejection or quality of a strategy or result, "
                "rather than reporting a measured value or a rule that applies."
            ),
            "criteria": {
                "true": (
                    "The sentence hands down a verdict of its own. Example: \"this family should "
                    "be adopted\", \"the hypothesis is rejected\", \"this idea is not promising\", "
                    "\"the edge works\"."
                ),
                "false": (
                    "The sentence reports a measured value, quotes a pre-registered rule, or "
                    "names the criterion without pronouncing on it. Example: \"the acceptance bar "
                    "is +5 bp per trade\", \"net was -1.2 bp over 340 trades\", \"the protocol "
                    "says a family is adopted only when t >= 2.0\"."
                ),
            },
        },
    }


def questions_prompt() -> dict:
    """委任文 × 報告(範囲の逸脱と、必須項目への対応)。同じ state への 2 問を 1 要求に並べる。"""
    return {
        "scope_widened": {
            "type": "noul",
            "instructions": (
                "The report does work, draws conclusions or makes proposals outside what the "
                "prompt asked."
            ),
            "criteria": {
                "true": (
                    "The report goes beyond the prompt. Example: the prompt asks for a count of "
                    "matching files and the report also rewrites the files; or the prompt asks to "
                    "measure one family and the report proposes a new strategy and a new budget."
                ),
                "false": (
                    "Everything in the report answers something the prompt asked for, including "
                    "the notes and the limits the prompt required. Example: the prompt asks for "
                    "counts and a list of limits, and the report gives the counts, the commands "
                    "that produced them, and the limits — and nothing else."
                ),
            },
        },
        "required_items_addressed": {
            "type": "noul",
            "instructions": (
                "Every numbered required item in the prompt has a corresponding section or "
                "explicit statement in the report."
            ),
            "criteria": {
                "true": (
                    "Each numbered item of the prompt can be pointed at in the report, either as "
                    "a section or as a sentence that answers it. Example: the prompt asks for "
                    "items 1-7 and the report has seven sections, or says \"item 3 does not apply "
                    "because no order was executed\"."
                ),
                "false": (
                    "At least one numbered item of the prompt is absent from the report with no "
                    "statement about it. Example: the prompt asks for an ablation and the report "
                    "never mentions one."
                ),
            },
        },
    }


def questions_origin() -> dict:
    """出所の無い数値 1 件ずつ。"""
    return {
        "origin_stated": {
            "type": "noul",
            "instructions": (
                "The sentence or its context says where the number comes from — a command, a "
                "file, a table, a calculation shown."
            ),
            "criteria": {
                "true": (
                    "The origin is named next to the number. Example: \"`git ls-files | wc -l` "
                    "-> 2130\", \"340 trades (the holdout rows of trades.csv)\", \"12% = 6/50, "
                    "the six rows of the table above\"."
                ),
                "false": (
                    "The number stands with no command, no file, no table and no calculation. "
                    "Example: \"about 16 cases are settled\", \"the cost is 5 bp\" with nothing "
                    "saying where either figure came from."
                ),
            },
        },
    }


# ---------------------------------------------------------------------------
# 印(**印であって判断ではない**)
# ---------------------------------------------------------------------------
def _noul(answers: dict, qid: str) -> float:
    return float((answers.get(qid) or {}).get("noul", 0.0))


def combine_verdict(answers: dict) -> dict:
    """判定の語: `pronounces_verdict >= PRESENCE` なら印(仕様どおり)。"""
    p = _noul(answers, "pronounces_verdict")
    return {"question": "pronounces_verdict", "violation_probability": round(p, 4),
            "flag": p >= PRESENCE, "reason": None}


def combine_prompt(answers: dict) -> tuple[dict, dict]:
    """委任文の対: 範囲逸脱(`>= PRESENCE`)と 必須項目の未対応(`1 - p >= ATTENTION`)の 2 件。"""
    widened = _noul(answers, "scope_widened")
    addressed = _noul(answers, "required_items_addressed")
    unaddressed = 1.0 - addressed
    flag, reason = decide_flag("prompt_required_items", unaddressed, None)
    return (
        {"question": "scope_widened", "violation_probability": round(widened, 4),
         "flag": widened >= PRESENCE, "reason": None},
        {"question": "required_items_addressed", "violation_probability": round(unaddressed, 4),
         "flag": bool(flag), "reason": reason},
    )


def combine_origin(answers: dict) -> dict:
    """出所の無い数値: `1 - origin_stated >= ATTENTION` なら印。"""
    stated = _noul(answers, "origin_stated")
    viol = 1.0 - stated
    flag, reason = decide_flag("unsourced_number", viol, None)
    return {"question": "origin_stated", "violation_probability": round(viol, 4),
            "flag": bool(flag), "reason": reason}


def combine_why(answers: dict) -> dict:
    """なぜ × 結果の対: `jev_check` の合成をそのまま使う(`contradicts` >= ATTENTION)。"""
    qid, viol = violation_probability("why_section", answers)
    flag, reason = decide_flag("why_section", viol, None)
    return {"question": qid, "violation_probability": round(viol, 4),
            "flag": bool(flag), "reason": reason,
            "relation_probabilities": (answers.get("relation") or {}).get("probabilities") or {},
            "relation_confidence": (answers.get("relation") or {}).get("confidence")}


# ---------------------------------------------------------------------------
# 本体
# ---------------------------------------------------------------------------
def build_jobs(text: str, prompt_text: str | None) -> list[dict]:
    """Jev へ送る仕事の一覧。state は **すべて code が組む**(判定される側が書かない)。"""
    jobs: list[dict] = []

    for pair in extract_why_section(text):
        jobs.append({
            "kind": "why_section",
            "anchor": pair["anchor"],
            "claim": _clip(pair["a"], 120),
            "questions": question_for("why_section", pair),
            "state": {
                "kind": pair["kind"],
                "fragment_a_role": pair["a_role"],
                "fragment_a": pair["a"],
                "fragment_b_role": pair["b_role"],
                "fragment_b": pair["b"],
            },
            "combine": combine_why,
        })

    for i, rec in enumerate(extract_verdict_sentences(text)):
        job = {"kind": "verdict_sentence", "anchor": rec["anchor"], "claim": rec["claim"]}
        if i >= MAX_VERDICT_QUESTIONS:
            job.update({"questions": None, "state": None, "combine": None,
                        "reason": "truncated"})
        else:
            job.update({
                "questions": questions_verdict(),
                "state": {"sentence": rec["claim"],
                          "nearby_context": context_of(text, rec["anchor"])},
                "combine": combine_verdict,
            })
        jobs.append(job)

    if prompt_text is not None:
        secs = sections(text)
        conclusion = _clip(secs[-1]["body"], CONCLUSION_CHARS) if secs else _clip(
            text, CONCLUSION_CHARS)
        jobs.append({
            "kind": "prompt_vs_report",
            "anchor": 1,
            "claim": "委任文 × 報告(範囲の逸脱 / 必須項目への対応)",
            "questions": questions_prompt(),
            "state": {
                "delegation_prompt": _clip(prompt_text, PROMPT_HEAD_CHARS),
                "report_headings": [s["title"] for s in secs],
                "report_conclusion": conclusion,
            },
            "combine": None,  # 1 要求から 2 件の記録を作るので run() 側で分ける
            "split": combine_prompt,
        })

    for i, rec in enumerate(extract_unsourced_numbers(text)):
        job = {"kind": "unsourced_number", "anchor": rec["anchor"], "claim": rec["claim"],
               "number": rec["number"]}
        if i >= MAX_NUMBER_QUESTIONS:
            job.update({"questions": None, "state": None, "combine": None,
                        "reason": "truncated"})
        else:
            job.update({
                "questions": questions_origin(),
                "state": {"sentence": rec["claim"],
                          "nearby_context": context_of(text, rec["anchor"])},
                "combine": combine_origin,
            })
        jobs.append(job)
    return jobs


def code_records(text: str, kind: str) -> list[dict]:
    """code だけで印が決まる記録(必須項目の欠け / なぜの節なし)。"""
    out: list[dict] = []
    for item in check_required_items(text, kind):
        out.append({
            "kind": "required_item",
            "anchor": 0,
            "claim": item["label"],
            "item": item["item"],
            "heading": item["heading"],
            "violation_probability": None,
            "flag": not item["found"],
            "reason": None if item["found"] else "missing",
            "sent": False,
        })
    whys = why_headings(text)
    out.append({
        "kind": "why_heading",
        "anchor": 0,
        "claim": "「なぜ」の節(見出しに なぜ|機構|理解)",
        "headings": whys,
        "violation_probability": None,
        "flag": not whys,
        "reason": None if whys else "missing",
        "sent": False,
    })
    return out


CHECK_LABELS = [
    ("required_item", "必須項目の欠け(code)"),
    ("why_heading", "なぜの節なし(code)"),
    ("why_section", "なぜ × 結果(jev)"),
    ("verdict_sentence", "判定の語(jev)"),
    ("prompt_vs_report", "範囲逸脱 / 必須項目の未対応(jev)"),
    ("unsourced_number", "出所なしの数値(jev)"),
]


def run(text: str, *, source: str, kind: str, prompt_text: str | None, out_dir: Path,
        model: str, dry_run: bool, summary_only: bool) -> tuple[int, dict]:
    records: list[dict] = code_records(text, kind)
    jobs = build_jobs(text, prompt_text)

    client = None
    unreachable: str | None = None
    if not dry_run:
        try:
            client = JevClient(model=model)
        except JevError as e:
            unreachable = str(e)

    n_requests = 0
    for job in jobs:
        base = {
            "source": source,
            "kind": job["kind"],
            "anchor": job["anchor"],
            "claim": job["claim"],
            "question": None,
            "violation_probability": None,
            "flag": False,
            "reason": job.get("reason"),
            "sent": False,
        }
        if "number" in job:
            base["number"] = job["number"]

        if job["questions"] is None or dry_run or client is None:
            if job["kind"] == "prompt_vs_report":
                records.append(dict(base, question="scope_widened"))
                records.append(dict(base, question="required_items_addressed"))
            else:
                records.append(base)
            continue

        try:
            state = clean_state(job["state"])
        except RedactionError as e:
            print(f"[jev_report_intake] 伏せ字の最終検査に掛かったので送信しない: {e}",
                  file=sys.stderr)
            return 2, {}
        try:
            resp = client.evaluate(state=state, questions=job["questions"])
        except JevError as e:
            unreachable = str(e)
            print(f"[jev_report_intake] 送信に失敗({job['kind']} @ {job['anchor']}): {e}",
                  file=sys.stderr)
            records.append(base)
            continue
        n_requests += 1
        answers = resp.get("answers") or {}
        if job["kind"] == "prompt_vs_report":
            for part in job["split"](answers):
                records.append(dict(base, **part, sent=True, model=resp.get("model")))
        else:
            records.append(dict(base, **job["combine"](answers), sent=True,
                                model=resp.get("model")))

    n_to_send = sum(1 for j in jobs if j["questions"] is not None)
    # 1 つも届かなかったときだけ「未到達」と言う(沈黙を「異常なし」と読ませない。§4-9)
    if dry_run or n_to_send == 0 or n_requests > 0:
        unreachable = None

    n_flag, by_kind = flag_counts(records)
    summary = {
        "file": source,
        "kind": "_summary",
        "report_kind": kind,
        "n_records": len(records),
        "n_jobs": len(jobs),
        "n_sent": sum(1 for r in records if r.get("sent")),
        "n_requests": n_requests,
        "n_flag": n_flag,
        "flag_by_kind": by_kind,
        "counts_by_check": {k: sum(1 for r in records if r["kind"] == k)
                            for k, _label in CHECK_LABELS},
        "prompt": bool(prompt_text is not None),
        "dry_run": bool(dry_run),
        "unreachable": unreachable,
        "threshold": {"attention": ATTENTION, "presence": PRESENCE},
        "heading_match_rule": HEADING_MATCH_RULE,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{Path(source).stem}.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")

    if not summary_only:
        _print_table(source, out_path, records, summary)
    print(summary_line(summary))
    return 0, summary


def _print_table(source: str, out_path: Path, records: list[dict], summary: dict) -> None:
    print(f"報告: {source}  種類: {summary['report_kind']}  記録の数: {summary['n_records']}  "
          f"送った要求の数: {summary['n_requests']}"
          + ("  (--dry-run: 1 件も送っていない)" if summary["dry_run"] else "")
          + ("" if summary["prompt"] else "  (--prompt 無し: 委任文との対は作っていない)"))
    print(f"見出しの一致の規則: {HEADING_MATCH_RULE}")
    print(f"{'検査':<32}{'件数':>6}{'印':>5}{'確率(最小〜最大)':>18}")
    for key, label in CHECK_LABELS:
        rows = [r for r in records if r["kind"] == key]
        probs = [r["violation_probability"] for r in rows
                 if r.get("violation_probability") is not None]
        span = f"{min(probs):.3f}〜{max(probs):.3f}" if probs else "-"
        n_flag = sum(1 for r in rows if r.get("flag"))
        print(f"{label:<32}{len(rows):>6}{n_flag:>5}{span:>18}")
    missing = [r["claim"] for r in records if r["kind"] == "required_item" and r["flag"]]
    if missing:
        print("欠けている必須項目: " + "、".join(missing))
    flagged = [r for r in records if r.get("flag") and r["kind"] not in
               ("required_item", "why_heading")]
    if flagged:
        print(f"{'印の付いた対':<22}{'行':>6}{'反する確率':>12}  先頭")
        for rec in flagged:
            p = rec.get("violation_probability")
            p_s = "-" if p is None else f"{p:.3f}"
            head = str(rec["claim"]).replace("\n", " ")[:56]
            print(f"{rec['kind']:<22}{rec['anchor']:>6}{p_s:>12}  {head}")
    print(f"(印のしきい値 attention={ATTENTION} / presence={PRESENCE}。"
          "**印であって判断ではない。差し戻すかを決めるのはリード**)")
    print(f"書いた先: {out_path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="委任先の報告を受領検査する(code の検査 + Jev の狭い分類)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("report")
    p.add_argument("--prompt", help="委任文(この報告を出させた指示)")
    p.add_argument("--kind", choices=KINDS, default=DEFAULT_KIND,
                   help=f"必須項目の一覧をどれで見るか(既定 {DEFAULT_KIND})")
    p.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--summary", action="store_true", help="末尾の 1 行だけを出す")
    p.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args(argv)

    report = Path(a.report)
    if not report.is_file():
        print(f"[jev_report_intake] 報告が無い: {report}", file=sys.stderr)
        return 1
    text = report.read_text(encoding="utf-8", errors="replace")

    prompt_text = None
    if a.prompt:
        prompt_path = Path(a.prompt)
        if not prompt_path.is_file():
            print(f"[jev_report_intake] 委任文が無い: {prompt_path}", file=sys.stderr)
            return 1
        prompt_text = prompt_path.read_text(encoding="utf-8", errors="replace")

    code, _summary = run(text, source=report.name, kind=a.kind, prompt_text=prompt_text,
                         out_dir=Path(a.out), model=a.model, dry_run=a.dry_run,
                         summary_only=a.summary)
    return code


if __name__ == "__main__":
    sys.exit(main())
