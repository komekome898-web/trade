#!/usr/bin/env python3
"""監査役の出力を対象にした 2 つの道具(`docs/JEV.md` §8 の U11 と U10)。

**この道具は何も判定しない。**出すのは確率と印と**候補**だけである(オーナー逐語 L-218:
「**判断はLLMと私の役割である**」)。「捕捉 / 部分 / 見逃し」も**候補**として出し、
確定はリードが行う(表の見出しにそう書く)。

  score-findings  U11 盲検評価の採点(捕捉 / 部分 / 見逃しの**候補**)
    監査役の出力から指摘を 1 件ずつ切り出し、`docs/AUDITOR/answers/<id>.md` の
    「何が誤りだったか」(訂正)と「オーナーの発言」を対にして、
    **訂正 × 指摘**の全組を Jev に聞く。合成(最大値・3 値化)は code。

  route-findings  U10 監査役の指摘の振り分け
    `docs/AUDITOR/VERDICTS/<file>.md` から指摘を 1 件ずつ切り出し、
    (a) スクリプトで完全に決められるか (b) どの既知解 KA と同型か を聞く。

規則(`docs/JEV.md` §4):
- 抽出も合成も **code**(決定論的)。state は code が組む。数える・比べるのは code。
- 問いは 1 判断 1 問・肯定形・criteria は具体例つき・英語(state の断片は日本語のまま)。
- 送信前に `redact_json` + `assert_clean`(`jev_check.clean_state` を再利用)。
- 版は既定 `jev-1.13.0` 固定。応答の `model` を記録する。
- しきい値はこのファイルの先頭に定数として 1 箇所だけ置く。**結果を見てから動かさない。**

使い方:
  python3 scripts/jev_audit_eval.py score-findings --auditor <監査役の出力.md|.json> \
      --answers docs/AUDITOR/answers/KA-01.md [--out data/jev/audit_eval/] \
      [--compare docs/AUDITOR/EVAL_2026-09-11b.md] [--dry-run] [--summary] [--model ID]
  python3 scripts/jev_audit_eval.py route-findings --verdict docs/AUDITOR/VERDICTS/<f>.md \
      [--known docs/AUDITOR/KNOWN_ANSWERS.md ...] [--out DIR] [--dry-run] [--summary]
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
# 抽出・伏せ字・表示は `jev_check` の部品をそのまま使う(同じ切り方・同じ検査を共有する)
from scripts.jev_check import (  # noqa: E402
    _clip as clip,
    clean_state,
    logical_lines,
    sections,
)

# ---------------------------------------------------------------------------
# 定数(しきい値はこの 1 箇所だけ)
# ---------------------------------------------------------------------------
PRESENCE = 0.50        # noul がこれ以上なら「その型である」側に置く(`jev_check` と同じ役割・同じ値)
KNOWN_CONFIDENT = 0.60  # choice の確信度がこれ未満なら既知解の名前を出さない(E.16「粗く答える」)
DEFAULT_MODEL = "jev-1.13.0"
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "audit_eval"
DEFAULT_KNOWN = (
    "docs/AUDITOR/KNOWN_ANSWERS.md",
    "docs/AUDITOR/KNOWN_ANSWERS_ADDENDUM.md",
)
KNOWN_ID_MAX = 35  # KA-36 は【提案・未承認】なので含めない(2026-09-19)   # 選択肢は KA-01…KA-28(仕様どおり。以降の KA-29… は選択肢に入れない)

# score の 3 段(E.10 entity alignment の型。合成は `round(score)`、しきい値は合わせ込まない)
SAME_DEFECT_LEVELS = [
    (
        "The finding points at a different defect from the one that was corrected. "
        "Example: the correction is that a holding period of h=1,2 silently removed an exit "
        "rule marked ○ in the intent map, and the finding is about a missing unit in a "
        "sensitivity table."
    ),
    (
        "The finding points at a part of the same defect, or at its surroundings, without "
        "naming the defect itself. Example: the correction is that a fixed holding period "
        "silently removed a rule marked ○ in the intent map, and the finding only asks "
        "whether the quoted excerpt of the intent map is complete."
    ),
    (
        "The finding points at the same defect that was corrected. Example: the correction "
        "is that \"the liquidation history cannot be obtained\" rested on one 404 at one "
        "venue, and the finding asks how many venues and routes were actually tried and "
        "which ones were not."
    ),
]
CANDIDATE_BY_LEVEL = {0: "見逃し候補", 1: "部分候補", 2: "捕捉候補"}
GRADE_WORDS = ("捕捉", "部分", "見逃し")  # リードが手で付けた採点の語(`--compare` が読む)

# ---------------------------------------------------------------------------
# 抽出(すべて決定論的。規則は報告に書く)
# ---------------------------------------------------------------------------
# 指摘 1 件の先頭行。次のすべての形に当たる:
#   `1. [止める] …`(k1_closure)    `> 1. [直す] …`(price_level の逐語)
#   `> 1. **[止める]** …`(reaction_prereg_r6 の逐語)  `### 1.[止める] …`(処置の見出し)
_FINDING_RE = re.compile(
    r"^(?P<quote>(?:>\s*)*)(?:#{1,6}\s+)?(?:\*\*)?(?:問い\s*)?(?P<num>\d{1,3})\s*[.)]\s*"
    r"(?:\*\*)?\s*\[\s*(?P<sev>止める|直す|聞く|通す)\s*\]"
)
# 表の形(rules_reduction / o3c_reframe_reading): `| 1 | 止める | 問い(要旨) | … |`
_FINDING_ROW_RE = re.compile(
    r"^\|\s*(?P<num>\d{1,3})\s*\|\s*(?P<sev>止める|直す|聞く|通す)\s*\|(?P<rest>.*)$"
)
_QUOTE_PREFIX_RE = re.compile(r"^(?:>\s?)+")

_CORRECTION_HEADING_RE = re.compile(r"何が誤りだったか|訂正コミットのメッセージ|何が起きたか")
_OWNER_WORDS_HEADING_RE = re.compile(r"オーナーの発言")
_PRINCIPLE_HEADING_RE = re.compile(r"原則")

_KA_HEADING_RE = re.compile(r"^(KA-\d{2})\b")
_KA_QUESTION_RE = re.compile(r"^-\s*\*\*監査役が出すべき問い\*\*\s*[:：]\s*(?P<q>.+)$")
_UNAPPROVED_RE = re.compile(r"提案・未承認")
_TABLE_SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|$")


def auditor_text(path: Path) -> str:
    """監査役の出力を文字列にする。`.json` は `result` / `content` から本文を取り出す。"""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() != ".json":
        return raw
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(data, dict):
        if isinstance(data.get("result"), str):
            return data["result"]
        content = data.get("content")
        if isinstance(content, list):
            parts = [c.get("text", "") for c in content if isinstance(c, dict)]
            if any(parts):
                return "\n".join(parts)
    return json.dumps(data, ensure_ascii=False, indent=2)


def split_findings(text: str) -> list[dict]:
    """監査役の出力から指摘を 1 件ずつ切り出す。

    規則(この順に当てる):
      1. `N. [止める|直す|聞く|通す]` で始まる行を指摘の先頭とする(引用符 `>`・見出し記号・
         `**` の有無は問わない)。本文は次の指摘の先頭行の直前まで。
      2. **引用(`>`)の中の先頭行が 1 つでもあれば、引用の中のものだけを使う**
         — 引用は監査役の逐語で、引用の外の同じ番号はリードの処置だからである。
      3. 1 件も当たらなければ、表の行 `| N | 止める | … |` を 1 件ずつの指摘とする。
    """
    lines = text.splitlines()
    starts: list[dict] = []
    for i, line in enumerate(lines):
        m = _FINDING_RE.match(line)
        if m:
            starts.append({"i": i, "quoted": bool(m.group("quote")),
                           "num": int(m.group("num")), "sev": m.group("sev")})
    if starts:
        quoted = [s for s in starts if s["quoted"]]
        chosen = quoted if quoted else [s for s in starts if not s["quoted"]]
        out: list[dict] = []
        for k, s in enumerate(chosen):
            end = chosen[k + 1]["i"] if k + 1 < len(chosen) else len(lines)
            body: list[str] = []
            for line in lines[s["i"]:end]:
                if s["quoted"]:
                    # 引用が途切れたらそこで終わり(監査役の逐語はそこまで)
                    if line.strip() and not line.lstrip().startswith(">"):
                        break
                    body.append(_QUOTE_PREFIX_RE.sub("", line))
                else:
                    body.append(line)
            out.append({
                "index": s["num"],
                "severity": s["sev"],
                "lineno": s["i"] + 1,
                "source": "quote" if s["quoted"] else "plain",
                "text": clip("\n".join(body)),
            })
        return out
    out = []
    q_idx: int | None = None
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.lstrip().startswith("|") and _TABLE_SEPARATOR_RE.match(nxt.strip()):
            head = [c.strip() for c in line.strip().strip("|").split("|")]
            hit = [j for j, c in enumerate(head) if "問い" in c or "指摘" in c]
            q_idx = hit[0] if hit else None
            continue
        m = _FINDING_ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # 指摘だけを取る(同じ行にあるリードの答え・処置の列は state に入れない)
        text = cells[q_idx] if (q_idx is not None and q_idx < len(cells)) else line.strip()
        out.append({
            "index": int(m.group("num")),
            "severity": m.group("sev"),
            "lineno": i + 1,
            "source": "table",
            "text": clip(text),
        })
    return out


def split_corrections(text: str) -> tuple[list[dict], str, bool]:
    """`answers/<id>.md` から (訂正の節, オーナーの発言, 代替を使ったか) を切り出す。

    訂正 = 見出しに「何が誤りだったか」「訂正コミットのメッセージ」「何が起きたか」を含む節。
    1 つも無ければ「原則」の節で代替し、その事実を返り値の 3 つ目で伝える(黙って代替しない)。
    """
    secs = sections(text)
    corrections = [s for s in secs if _CORRECTION_HEADING_RE.search(s["title"])]
    fallback = False
    if not corrections:
        corrections = [s for s in secs if _PRINCIPLE_HEADING_RE.search(s["title"])]
        fallback = bool(corrections)
    owner = [s for s in secs if _OWNER_WORDS_HEADING_RE.search(s["title"])]
    owner_words = clip("\n\n".join(s["body"] for s in owner))
    out = [{"title": s["title"], "lineno": s["lineno"], "text": clip(s["body"])}
           for s in corrections if s["body"].strip()]
    return out, owner_words, fallback


def known_answers(paths: list[str]) -> dict[str, str]:
    """既知解の一覧 {KA-01: 想定問いの 1 行}。KA-01…KA-{KNOWN_ID_MAX} だけを採る。"""
    out: dict[str, str] = {}
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = REPO / p
        if not p.is_file():
            print(f"[jev_audit_eval] 既知解の文書が無い: {p}", file=sys.stderr)
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for sec in sections(text):
            m = _KA_HEADING_RE.match(sec["title"])
            if not m or sec["level"] != 3:
                continue
            ka = m.group(1)
            if int(ka.split("-")[1]) > KNOWN_ID_MAX:
                continue
            if _UNAPPROVED_RE.search(sec["title"]):
                continue
            question = ""
            for _ln, body in logical_lines(sec["body"]):
                q = _KA_QUESTION_RE.match(body)
                if q:
                    question = q.group("q").strip()
                    break
            if question:
                out[ka] = question[:400]
    return dict(sorted(out.items()))


# ---------------------------------------------------------------------------
# 問い(1 判断 1 問・肯定形・criteria は具体例つき・英語)
# ---------------------------------------------------------------------------
def questions_for_pair() -> dict:
    """U11。`same_defect`(3 段)と `points_to_location`(noul)を 1 要求で聞く。"""
    return {
        "same_defect": {
            "type": "score",
            "instructions": (
                "`finding` is one item raised by a reviewer about a piece of work. "
                "`owner_correction` describes the defect that the owner of the project "
                "actually had corrected in that same piece of work, and `owner_words` quotes "
                "what the owner said. Rate how close `finding` is to that corrected defect."
            ),
            "criteria": SAME_DEFECT_LEVELS,
        },
        "points_to_location": {
            "type": "noul",
            "instructions": (
                "`finding` names where the problem is: a file path with a line number, a "
                "section number, or the exact number or sentence it is about."
            ),
            "criteria": {
                "true": (
                    "A location is given. Example: \"docs/PHASE2/O3C/SAMPLE_2026-09-17.md:54 "
                    "— the figure '19-48' does not match table.csv\", or \"section 3 of the "
                    "pre-registration, the line defining sd\"."
                ),
                "false": (
                    "Only a general concern is stated, with no file, no line, no section and "
                    "no quoted figure. Example: \"the report is not thorough enough about "
                    "data availability\"."
                ),
            },
        },
    }


def questions_for_finding(known: dict[str, str]) -> dict:
    """U10。`deterministic_checkable` / `known_answer` / `severity_kind` を 1 要求で聞く。"""
    criteria = dict(known)
    criteria["none"] = (
        "The finding does not match any of the listed known answers, or it matches none of "
        "them closely enough to name one."
    )
    return {
        "deterministic_checkable": {
            "type": "noul",
            "instructions": (
                "A script with no judgement model could decide this finding completely: by "
                "string matching, by counting and comparing counts, by checking that a file "
                "or a line exists, or by checking a schema or a numeric identity."
            ),
            "criteria": {
                "true": (
                    "A script can settle it. Example: \"the document says 758 zip files but "
                    "ls counts 944\" (count and compare), \"the symbol p_liq is defined twice "
                    "with different wording\" (string match), \"docs/DATA.md has no row for "
                    "this data source\" (file and line existence)."
                ),
                "false": (
                    "Settling it needs a judgement about meaning, intent or sufficiency. "
                    "Example: \"is this simplification silently dropping a rule the intent "
                    "map marked as implemented?\", or \"is this reasoning a mechanism or a "
                    "restatement of the result?\"."
                ),
            },
        },
        "known_answer": {
            "type": "choice",
            "instructions": (
                "Each option below is a question that a past owner intervention says the "
                "reviewer should ask. Pick the option whose question is the same kind of "
                "question as `finding`."
            ),
            "criteria": criteria,
        },
        "severity_kind": {
            "type": "choice",
            "instructions": (
                "Judge what `finding` asks the author to do."
            ),
            "criteria": {
                "止める": (
                    "It says the work must not go forward as it stands: a result, a decision "
                    "or a measurement is wrong or unsupported. Example: a figure presented as "
                    "a fact does not match the data file it came from."
                ),
                "直す": (
                    "It says a specific part of the text or the code should be corrected. "
                    "Example: the same symbol is defined twice with different meanings, or a "
                    "unit is missing from a printed value."
                ),
                "聞く": (
                    "It asks the author a question and waits for an answer, without saying "
                    "what the answer should be. Example: \"was this treated as out of scope, "
                    "or was it an omission?\"."
                ),
            },
        },
    }


# ---------------------------------------------------------------------------
# 合成(code。Jev は合成しない)
# ---------------------------------------------------------------------------
def candidate_for(score: float) -> str:
    """`round(score)` で 3 値化(E.10 と同じ。しきい値は合わせ込まない)。

    `round` は Python の規則(半数は偶数側)。0.5 → 0、1.5 → 2 になる。
    """
    level = int(round(score))
    level = max(0, min(len(SAME_DEFECT_LEVELS) - 1, level))
    return CANDIDATE_BY_LEVEL[level]


def best_for_correction(scores: list[float | None]) -> tuple[float | None, str | None]:
    """訂正 1 件について (全指摘の中の最大の期待値, 候補)。1 件も無ければ (None, None)。"""
    got = [s for s in scores if s is not None]
    if not got:
        return None, None
    top = max(got)
    return top, candidate_for(top)


def artifact_candidate(candidates: list[str]) -> str | None:
    """成果物単位の候補 = **最も低い訂正の候補**(1 件でも見逃し候補があればそれを出す)。

    仕様に無い判断なので報告に印を付ける(訂正が 1 件の答え集合では最大値と一致する)。
    """
    order = ["見逃し候補", "部分候補", "捕捉候補"]
    got = [c for c in candidates if c]
    if not got:
        return None
    return min(got, key=order.index)


# ---------------------------------------------------------------------------
# `--compare`(リードが手で付けた採点を code で読み取る。中身の解釈は書かない)
# ---------------------------------------------------------------------------
def read_manual_grades(path: Path) -> tuple[dict[str, str], str | None]:
    """`EVAL_*.md` の表から {KA-01: 捕捉|部分|見逃し} を読む。

    表の見出し行に「今回」があればその列、無ければ「判定」の列を読む(両方無い表は飛ばす)。
    根拠の列に同じ語が現れても拾わないための規則である。読めなければ (…, 理由) を返す。
    """
    if not path.is_file():
        return {}, f"読み取れない(ファイルが無い): {path}"
    grades: dict[str, str] = {}
    col: int | None = None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            col = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if _TABLE_SEPARATOR_RE.match(nxt.strip()):
            # 見出し行(次の行が `|---|---|`)。本文のセルに「今回」が出ても見出しと誤らない
            hit = [j for j, c in enumerate(cells) if "今回" in c]
            if not hit:
                hit = [j for j, c in enumerate(cells) if c == "判定"]
            col = hit[0] if hit else None
            continue
        if col is None or col >= len(cells):
            continue
        m = re.match(r"\**\s*(KA-\d{2})\b", cells[0])
        if not m:
            continue
        for word in GRADE_WORDS:
            if word in cells[col]:
                grades[m.group(1)] = word
                break
    if not grades:
        return {}, f"読み取れない(KA の行と判定の列が見つからない): {path}"
    return grades, None


def compare_counts(grades: dict[str, str], candidates: dict[str, str | None]) -> dict:
    """手の採点と候補の一致・不一致の**件数だけ**を返す(中身の解釈は書かない)。"""
    same = diff = missing = 0
    rows = []
    for ka, cand in sorted(candidates.items()):
        manual = grades.get(ka)
        if manual is None or cand is None:
            missing += 1
            state = "突き合わせ不可"
        elif cand == manual + "候補":
            same += 1
            state = "一致"
        else:
            diff += 1
            state = "不一致"
        rows.append({"id": ka, "manual": manual, "candidate": cand, "state": state})
    return {"same": same, "diff": diff, "unmatched": missing, "rows": rows}


# ---------------------------------------------------------------------------
# 送信
# ---------------------------------------------------------------------------
def _send(client, state: dict, questions: dict) -> tuple[dict | None, str | None]:
    """(応答, 未到達の理由)。伏せ字に掛かったら送らない。"""
    try:
        cleaned = clean_state(state)
    except RedactionError as e:
        return None, f"伏せ字の最終検査に掛かったので送っていない: {e}"
    try:
        return client.evaluate(state=cleaned, questions=questions), None
    except JevError as e:
        return None, str(e)


def _client_or_none(args) -> tuple[object | None, str | None]:
    if args.dry_run:
        return None, None
    try:
        return JevClient(model=args.model), None
    except JevError as e:
        return None, str(e)


def _write_jsonl(out_dir: Path, name: str, records: list[dict], summary: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------------------
# U11: score-findings
# ---------------------------------------------------------------------------
def summary_line_score(summary: dict) -> str:
    if summary.get("unreachable"):
        return f"jev: 未到達({summary['unreachable']})"
    tail = "(--dry-run: 1 件も送っていない)" if summary.get("dry_run") else ""
    cand = summary.get("artifact_candidate") or "候補なし"
    cmp_ = summary.get("compare")
    cmp_s = ""
    if cmp_:
        cmp_s = (f"、手の採点との一致 {cmp_['same']} 件 / 不一致 {cmp_['diff']} 件"
                 f" / 突き合わせ不可 {cmp_['unmatched']} 件") if "same" in cmp_ else \
                f"、比較: {cmp_.get('error')}"
    return (f"訂正 {summary['n_corrections']} 件 × 指摘 {summary['n_findings']} 件 = "
            f"{summary['n_pairs']} 組(送った要求 {summary['n_requests']})、"
            f"成果物単位の候補: {cand}{cmp_s}{tail}")


def cmd_score_findings(args) -> int:
    auditor = Path(args.auditor)
    answers = Path(args.answers)
    for p in (auditor, answers):
        if not p.is_file():
            print(f"[jev_audit_eval] ファイルが無い: {p}", file=sys.stderr)
            return 1

    findings = split_findings(auditor_text(auditor))
    corrections, owner_words, fallback = split_corrections(
        answers.read_text(encoding="utf-8", errors="replace"))
    ka_id = answers.stem

    client, unreachable = _client_or_none(args)
    records: list[dict] = []
    n_requests = 0
    scores: dict[int, list[float | None]] = {i: [] for i in range(len(corrections))}

    for ci, corr in enumerate(corrections):
        for finding in findings:
            rec = {
                "kind": "pair",
                "id": ka_id,
                "auditor": auditor.name,
                "answers": answers.name,
                "correction_index": ci,
                "correction_title": corr["title"],
                "finding_index": finding["index"],
                "finding_severity": finding["severity"],
                "finding_lineno": finding["lineno"],
                "finding_head": finding["text"].replace("\n", " ")[:80],
                "same_defect_score": None,
                "same_defect_candidate": None,
                "points_to_location": None,
                "sent": False,
            }
            if client is None:
                records.append(rec)
                scores[ci].append(None)
                continue
            state = {
                "finding": finding["text"],
                "owner_correction": corr["text"],
                "owner_words": owner_words,
            }
            resp, err = _send(client, state, questions_for_pair())
            if resp is None:
                unreachable = err
                print(f"[jev_audit_eval] 送信に失敗(訂正 {ci} × 指摘 {finding['index']}): {err}",
                      file=sys.stderr)
                records.append(rec)
                scores[ci].append(None)
                continue
            n_requests += 1
            ans = resp.get("answers") or {}
            score = ans.get("same_defect", {}).get("score")
            rec["same_defect_score"] = None if score is None else round(float(score), 4)
            rec["same_defect_candidate"] = (None if score is None
                                            else candidate_for(float(score)))
            rec["same_defect_confidence"] = ans.get("same_defect", {}).get("confidence")
            loc = ans.get("points_to_location", {}).get("noul")
            rec["points_to_location"] = None if loc is None else round(float(loc), 4)
            rec["points_to_location_flag"] = (None if loc is None
                                              else bool(float(loc) >= PRESENCE))
            rec["model"] = resp.get("model")
            rec["sent"] = True
            records.append(rec)
            scores[ci].append(None if score is None else float(score))

    per_correction: list[dict] = []
    for ci, corr in enumerate(corrections):
        top, cand = best_for_correction(scores[ci])
        per_correction.append({
            "kind": "correction",
            "id": ka_id,
            "correction_index": ci,
            "correction_title": corr["title"],
            "max_same_defect_score": None if top is None else round(top, 4),
            "candidate": cand,
        })
    records += per_correction
    art_cand = artifact_candidate([c["candidate"] for c in per_correction])

    compare: dict | None = None
    if args.compare:
        grades, err = read_manual_grades(Path(args.compare))
        if err:
            compare = {"error": err, "file": str(args.compare)}
        else:
            compare = compare_counts({ka_id: grades[ka_id]} if ka_id in grades else {},
                                     {ka_id: art_cand})
            compare["file"] = str(args.compare)
            compare["n_ids_read"] = len(grades)

    n_pairs = len(corrections) * len(findings)
    if args.dry_run or n_pairs == 0 or n_requests > 0:
        unreachable = None
    summary = {
        "kind": "_summary",
        "command": "score-findings",
        "id": ka_id,
        "auditor": auditor.name,
        "answers": answers.name,
        "n_findings": len(findings),
        "n_corrections": len(corrections),
        "n_pairs": n_pairs,
        "n_requests": n_requests,
        "artifact_candidate": art_cand,
        "correction_fallback_to_principle": fallback,
        "owner_words_found": bool(owner_words),
        "compare": compare,
        "dry_run": bool(args.dry_run),
        "unreachable": unreachable,
        "model": args.model,
        "thresholds": {"presence": PRESENCE},
    }
    out_path = _write_jsonl(Path(args.out), f"{ka_id}__{auditor.stem}", records, summary)

    if not args.summary:
        _print_score_table(records, per_correction, summary, out_path)
    print(summary_line_score(summary))
    return 0


def _print_score_table(records, per_correction, summary, out_path: Path) -> None:
    print(f"監査役の出力: {summary['auditor']}  指摘 {summary['n_findings']} 件"
          f"(切り出しの規則: 番号 + [止める|直す|聞く|通す]。引用の中を優先、"
          f"無ければ表の行)")
    print(f"訂正: {summary['answers']}  {summary['n_corrections']} 件"
          + ("(「何が誤りだったか」が無いので「原則」の節で代替)"
             if summary["correction_fallback_to_principle"] else "")
          + ("" if summary["owner_words_found"] else "  ※「オーナーの発言」の節が無い"))
    print("")
    print("【候補】捕捉 / 部分 / 見逃しは **候補** であり、**確定はリードが行う**"
          "(Jev は判定しない)")
    print(f"{'訂正':>4}{'指摘':>6}{'種別':>6}{'same_defect':>13}{'場所':>7}  候補 / 先頭")
    for rec in records:
        if rec["kind"] != "pair":
            continue
        s = rec["same_defect_score"]
        s_s = "-" if s is None else f"{s:.3f}"
        loc = rec["points_to_location"]
        loc_s = "-" if loc is None else f"{loc:.2f}"
        head = (rec["same_defect_candidate"] or "") + "  " + rec["finding_head"]
        print(f"{rec['correction_index']:>4}{rec['finding_index']:>6}"
              f"{rec['finding_severity']:>6}{s_s:>13}{loc_s:>7}  {head}")
    print("")
    for c in per_correction:
        top = c["max_same_defect_score"]
        print(f"訂正 {c['correction_index']}({c['correction_title']}): "
              f"最大 {('-' if top is None else f'{top:.3f}')} → {c['candidate'] or '候補なし'}")
    print(f"成果物単位の候補: {summary['artifact_candidate'] or '候補なし'}"
          "(訂正が複数なら最も低い候補を出す)")
    cmp_ = summary.get("compare")
    if cmp_:
        if "error" in cmp_:
            print(f"比較({cmp_['file']}): {cmp_['error']}")
        else:
            print(f"比較({cmp_['file']}、読めた KA {cmp_['n_ids_read']} 件): "
                  f"一致 {cmp_['same']} 件 / 不一致 {cmp_['diff']} 件 / "
                  f"突き合わせ不可 {cmp_['unmatched']} 件(**中身の解釈は書かない**)")
    print(f"書き出し: {out_path}")


# ---------------------------------------------------------------------------
# U10: route-findings
# ---------------------------------------------------------------------------
def summary_line_route(summary: dict) -> str:
    if summary.get("unreachable"):
        return f"jev: 未到達({summary['unreachable']})"
    tail = "(--dry-run: 1 件も送っていない)" if summary.get("dry_run") else ""
    return (f"指摘 {summary['n_findings']} 件: スクリプト化候補 {summary['n_scriptable']} 件 / "
            f"既知解に当たる {summary['n_known']} 件(低確信 {summary['n_low_confidence']} 件)"
            f"{tail}")


def cmd_route_findings(args) -> int:
    verdict = Path(args.verdict)
    if not verdict.is_file():
        print(f"[jev_audit_eval] ファイルが無い: {verdict}", file=sys.stderr)
        return 1
    findings = split_findings(auditor_text(verdict))
    known = known_answers(list(args.known))
    if not known:
        print("[jev_audit_eval] 既知解を 1 件も読めなかった", file=sys.stderr)
        return 1

    client, unreachable = _client_or_none(args)
    records: list[dict] = []
    n_requests = n_scriptable = n_known = n_low = n_sev_match = 0

    for finding in findings:
        rec = {
            "kind": "finding",
            "file": verdict.name,
            "finding_index": finding["index"],
            "finding_severity": finding["severity"],
            "finding_lineno": finding["lineno"],
            "finding_head": finding["text"].replace("\n", " ")[:80],
            "deterministic_checkable": None,
            "scriptable_candidate": None,
            "known_answer": None,
            "known_answer_confidence": None,
            "known_answer_reported": None,
            "severity_kind": None,
            "severity_matches_auditor": None,
            "sent": False,
        }
        if client is None:
            records.append(rec)
            continue
        state = {
            "finding": finding["text"],
            "known_answer_count": len(known),
        }
        resp, err = _send(client, state, questions_for_finding(known))
        if resp is None:
            unreachable = err
            print(f"[jev_audit_eval] 送信に失敗(指摘 {finding['index']}): {err}", file=sys.stderr)
            records.append(rec)
            continue
        n_requests += 1
        ans = resp.get("answers") or {}
        det = ans.get("deterministic_checkable", {}).get("noul")
        if det is not None:
            rec["deterministic_checkable"] = round(float(det), 4)
            rec["scriptable_candidate"] = bool(float(det) >= PRESENCE)
            n_scriptable += int(rec["scriptable_candidate"])
        ka = ans.get("known_answer", {})
        conf = ka.get("confidence")
        rec["known_answer"] = ka.get("choice")
        rec["known_answer_confidence"] = None if conf is None else round(float(conf), 4)
        if conf is not None and float(conf) >= KNOWN_CONFIDENT and ka.get("choice") != "none":
            rec["known_answer_reported"] = ka.get("choice")
            n_known += 1
        else:
            rec["known_answer_reported"] = "none"
            if ka.get("choice") not in (None, "none"):
                rec["known_answer_note"] = "低確信(名前を出さない)"
                n_low += 1
        sev = ans.get("severity_kind", {})
        rec["severity_kind"] = sev.get("choice")
        rec["severity_kind_confidence"] = sev.get("confidence")
        rec["severity_matches_auditor"] = (sev.get("choice") == finding["severity"]
                                           if sev.get("choice") else None)
        n_sev_match += int(bool(rec["severity_matches_auditor"]))
        rec["model"] = resp.get("model")
        rec["sent"] = True
        records.append(rec)

    if args.dry_run or not findings or n_requests > 0:
        unreachable = None
    summary = {
        "kind": "_summary",
        "command": "route-findings",
        "file": verdict.name,
        "n_findings": len(findings),
        "n_requests": n_requests,
        "n_known_answers": len(known),
        "n_scriptable": n_scriptable,
        "n_known": n_known,
        "n_low_confidence": n_low,
        "n_severity_match": n_sev_match,
        "dry_run": bool(args.dry_run),
        "unreachable": unreachable,
        "model": args.model,
        "thresholds": {"presence": PRESENCE, "known_confident": KNOWN_CONFIDENT},
    }
    out_path = _write_jsonl(Path(args.out), verdict.stem, records, summary)

    if not args.summary:
        _print_route_table(records, summary, out_path)
    print(summary_line_route(summary))
    return 0


def _print_route_table(records, summary, out_path: Path) -> None:
    print(f"監査記録: {summary['file']}  指摘 {summary['n_findings']} 件  "
          f"既知解の選択肢 {summary['n_known_answers']} 件 + none")
    print("【候補】スクリプト化の候補・同型の既知解は **候補** であり、"
          "**確定はリードが行う**(Jev は判定しない)")
    print(f"{'指摘':>4}{'種別':>6}{'決定的':>8}{'既知解':>10}{'確信':>7}{'種別(模型)':>12}  先頭")
    for rec in records:
        if rec["kind"] != "finding":
            continue
        det = rec["deterministic_checkable"]
        det_s = "-" if det is None else f"{det:.2f}"
        conf = rec["known_answer_confidence"]
        conf_s = "-" if conf is None else f"{conf:.2f}"
        print(f"{rec['finding_index']:>4}{rec['finding_severity']:>6}{det_s:>8}"
              f"{str(rec['known_answer_reported'] or '-'):>10}{conf_s:>7}"
              f"{str(rec['severity_kind'] or '-'):>12}  {rec['finding_head'][:44]}")
    print(f"(しきい値 presence={PRESENCE} / known_confident={KNOWN_CONFIDENT}。"
          f"監査役自身の種別と一致 {summary['n_severity_match']} 件 — **印には使わない**)")
    print(f"書き出し: {out_path}")


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="監査役の出力に狭い問いを当てる(U11 採点の候補 / U10 振り分け)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("score-findings", help="U11 盲検評価の採点(候補)")
    p1.add_argument("--auditor", required=True)
    p1.add_argument("--answers", required=True)
    p1.add_argument("--compare", default=None,
                    help="リードが手で付けた採点の表(件数だけを突き合わせる)")
    p1.set_defaults(func=cmd_score_findings)

    p2 = sub.add_parser("route-findings", help="U10 監査役の指摘の振り分け")
    p2.add_argument("--verdict", required=True)
    p2.add_argument("--known", nargs="+", default=list(DEFAULT_KNOWN))
    p2.set_defaults(func=cmd_route_findings)

    for p in (p1, p2):
        p.add_argument("--out", default=str(DEFAULT_OUT_DIR))
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--summary", action="store_true",
                       help="末尾の 1 行だけを出す")
        p.add_argument("--model", default=DEFAULT_MODEL)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
