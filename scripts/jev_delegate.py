#!/usr/bin/env python3
"""委任文 1 本から state を code で組み、狭い問いを Jev へ投げて**段の候補と印**だけを出す道具。

出所: `docs/JEV.md` §8 の U8(委任時のモデル選定)。オーナー逐語 L-220「**あなたが委任すると
きのモデル選定など、まだ有効活用できる用途はあります**」、L-221「**順次着手していってください**」。

**この道具は何も選ばないし、何も止めない**(オーナー逐語 L-218:
「**そもそも止めるとjev出させようとするのは間違った運用で、判断はLLMと私の役割である**」)。
U8 の逐語どおり「**Jev が選ぶのではなく、規則の表を当てるための分類**」であり、
Jev が出すのは分類の確率だけ、段は code が `config/jev_delegation_tiers.yaml` の規則で当てる。
**どの段で委任するかを決めるのはリードとオーナーである。**

- state は必ず code が組む(`docs/JEV.md` §4-2。判定される側が書かない)。
- 数える(パスの数・行数・必須報告の項目数)・保護パスの判定は **code**(§4-4)。
- 問いは 1 判断 1 問・肯定形・criteria は具体例つき・英語(断片は日本語のまま。§4-3)。
- 送信前に `clean_state`(`redact_json` + `assert_clean`)を通す(§4-7)。

使い方:
  python3 scripts/jev_delegate.py plan --prompt <委任文のファイル> [--dry-run] [--summary]
  python3 scripts/jev_delegate.py calibrate --transcript <会話記録.jsonl> [--dry-run]

`calibrate` は「正解」を測らない。**リードが実際に選んだモデルとの一致件数**を数えるだけで、
食い違いがどちらの誤りかは書かない(解釈は人がする)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from scripts.jev.client import JevClient, JevError  # noqa: E402
from scripts.jev.redact import RedactionError  # noqa: E402
# しきい値・伏せ字の作法・末尾 1 行は `jev_check` から import して使う(複製しない。
# しきい値の在処は `jev_check` の 1 箇所のまま)。
from scripts.jev_check import (  # noqa: E402
    ATTENTION,
    PRESENCE,
    DEFAULT_MODEL,
    clean_state,
    flag_counts,
    summary_line,
)

# ---------------------------------------------------------------------------
# 定数(しきい値は import した 1 箇所のまま。ここで数値を書き直さない)
# ---------------------------------------------------------------------------
TIERS_PATH = REPO / "config" / "jev_delegation_tiers.yaml"
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "delegate"
MAX_TASK_CHARS = 6_000      # 委任文の全文はここまで(仕様)
KIND_CONFIDENT = 0.60       # 選択の確信度がこれ未満なら粗い答えに落とす(資料 E.16)
PROMPT_HEAD_CHARS = 60      # calibrate の一覧に出す委任文の先頭の長さ

# しきい値の名前 -> 値(config の規則から引く)
THRESHOLD_BY_NAME = {"attention": ATTENTION, "presence": PRESENCE,
                     "kind_confident": KIND_CONFIDENT}

# 保護パス(仕様どおりの語をそのまま置く)。**判定は code**。
PROTECTED_RE = re.compile(r"\.claude/hooks|settings\.json|githooks|src/bot/|config/risk_limits")

# 委任文に現れるパスを拾う(ディレクトリを含む形と、拡張子つきの単体)
_DIR_PATH_RE = re.compile(r"/?(?:\.?[A-Za-z0-9_][A-Za-z0-9_.\-]*/)+[A-Za-z0-9_.\-]*")
_BARE_FILE_RE = re.compile(
    r"(?<![A-Za-z0-9_./\-])[A-Za-z0-9_][A-Za-z0-9_.\-]*"
    r"\.(?:py|md|ya?ml|json|jsonl|sh|txt|csv|bat|toml|cfg|ini)(?![A-Za-z0-9_])"
)

# 必須報告の節の始まり(仕様どおりの語)と、節の終わり(次の【…】の見出し)
REQUIRED_HEAD_RE = re.compile(r"【必須報告】|報告\s*[:：]")
_NEXT_BRACKET_RE = re.compile(r"【[^】]*】")
_NUM_LINE_RE = re.compile(r"(?m)^\s*(\d{1,2})[.)]\s")
_NUM_PAREN_RE = re.compile(r"[(（](\d{1,2})[)）]")

# 禁止文(仕様どおりの語: 「Do not commit」「実送信はしない」「〜しない」)
STOP_RE = re.compile(r"Do not commit|Do not push|実送信はしない|しない|禁止")


# ---------------------------------------------------------------------------
# state(すべて code が組む)
# ---------------------------------------------------------------------------
def extract_paths(text: str) -> list[str]:
    """委任文に現れるパスらしき文字列(重複を除き、出た順)。"""
    found: list[str] = []
    seen: set[str] = set()
    for m in list(_DIR_PATH_RE.finditer(text)) + list(_BARE_FILE_RE.finditer(text)):
        raw = m.group(0).rstrip(".")
        if not raw or raw in seen:
            continue
        # `http://…` のような綴りと、数字だけの断片は除く
        if raw.startswith(("http:", "https:")) or re.fullmatch(r"[\d./]+", raw):
            continue
        seen.add(raw)
        found.append(raw)
    return found


def file_entry(path: str) -> dict:
    """1 つのパスについて、実在と行数を code で調べる。"""
    p = Path(path)
    if not p.is_absolute():
        p = REPO / path
    entry: dict = {"path": path, "exists": False, "lines": 0}
    try:
        if p.is_file():
            entry["exists"] = True
            entry["lines"] = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
        elif p.is_dir():
            entry["exists"] = True
            entry["is_dir"] = True
    except OSError:
        pass
    return entry


def count_required_outputs(text: str) -> int:
    """「【必須報告】」「報告:」以下の番号付き項目の数(code)。"""
    m = REQUIRED_HEAD_RE.search(text)
    if not m:
        return 0
    rest = text[m.end():]
    nxt = _NEXT_BRACKET_RE.search(rest)
    region = rest[:nxt.start()] if nxt else rest
    nums = {int(x) for x in _NUM_LINE_RE.findall(region)}
    nums |= {int(x) for x in _NUM_PAREN_RE.findall(region)}
    return len(nums)


def build_state(text: str) -> dict:
    """委任文から state を組む。**判定される側は 1 文字も書かない。**"""
    paths = extract_paths(text)
    files = [file_entry(p) for p in paths]
    return {
        "task_text": text.strip()[:MAX_TASK_CHARS],
        "files_named": files,
        "n_files": len(files),
        "total_lines": sum(f["lines"] for f in files),
        "touches_protected": any(PROTECTED_RE.search(f["path"]) for f in files),
        "required_outputs": count_required_outputs(text),
        "has_stop_condition": bool(STOP_RE.search(text)),
    }


# ---------------------------------------------------------------------------
# 問い(1 判断 1 問・肯定形・criteria は具体例つき・英語)
# ---------------------------------------------------------------------------
def questions() -> dict:
    """1 要求に 5 問。同じ state への独立した問いなのでまとめて投げる(fan-out)。"""
    return {
        "task_kind": {
            "type": "choice",
            "instructions": (
                "What kind of work does `task_text` ask its recipient to do? Judge the main body "
                "of the work, not the reporting and formatting instructions that every prompt in "
                "this team carries."
            ),
            "criteria": {
                "implementation": (
                    "Writing or changing code that later work will run: a new script, a change to "
                    "an existing module, the tests that go with it. Example: \"write "
                    "scripts/foo.py with the subcommands plan and calibrate, put the rules in "
                    "config/foo.yaml, add tests/test_foo.py\"."
                ),
                "measurement_or_execution": (
                    "Running something that already exists and reporting what came out. Example: "
                    "\"run the sweep over the 12 configurations and report n, net bps and t for "
                    "each\", \"fetch the last 30 days of public trades and save a snapshot\"."
                ),
                "extraction_or_inventory": (
                    "Reading material that already exists and listing what is in it, verbatim or "
                    "as a table, without adding conclusions. Example: \"list every place in docs/ "
                    "where this term appears, with file and line\", \"pull the vendor's own "
                    "wording for each limitation from these pages\"."
                ),
                "judgment_or_design": (
                    "Choosing between options, setting the frame of a study, or deciding what "
                    "counts as success. Example: \"decide which of these three hypotheses to run "
                    "first\", \"set the adoption bar and the family split for this unit\", "
                    "\"decide whether this finding is a false alarm\"."
                ),
                "writing": (
                    "Producing prose for people to read out of material that is already settled. "
                    "Example: \"write the body of the report from this table of results\", "
                    "\"rewrite this section so the owner's wording is quoted verbatim\"."
                ),
                "other": (
                    "The work is none of the kinds above. Example: the text is a question to be "
                    "answered in a sentence, or an instruction about how to behave rather than a "
                    "piece of work to carry out."
                ),
            },
        },
        "needs_cross_file_reasoning": {
            "type": "noul",
            "instructions": (
                "The task requires holding several files' contents together and reasoning about "
                "their relations, not just reading each one."
            ),
            "criteria": {
                "true": (
                    "The result depends on how the files fit together. Example: \"make the new "
                    "script import the thresholds and the redaction helper from the existing one "
                    "so the constant stays in one place\"; \"check that the value the config "
                    "stores is the one the caller reads\"; \"match each line of the owner's log "
                    "to the rule in the handbook that cites it\"."
                ),
                "false": (
                    "Each file can be handled on its own, or only one file matters. Example: "
                    "\"count the lines of each of these files\"; \"add a docstring to every "
                    "script in this directory\"; \"summarise this one page\"."
                ),
            },
        },
        "is_mechanical": {
            "type": "noul",
            "instructions": (
                "A script, a regular expression or a shell one-liner would complete the task with "
                "no model at all."
            ),
            "criteria": {
                "true": (
                    "The whole result comes out of running a fixed command. Example: \"count how "
                    "many files contain this word and list them\"; \"rename this symbol "
                    "everywhere\"; \"list the files changed in the last commit\"; \"convert this "
                    "CSV to JSON\"."
                ),
                "false": (
                    "Some step needs reading and judgement that no fixed command produces. "
                    "Example: \"work out why the measurement dropped 80% of the liquidations and "
                    "say which mechanism explains it\"; \"write questions whose criteria carry "
                    "concrete examples\"."
                ),
            },
        },
        "needs_owner_approval": {
            "type": "noul",
            "instructions": (
                "The task changes something the owner reserved for themselves: live trading, "
                "capital, accounts, risk limits, hooks, settings, the auditor's definition, or "
                "git history. `touches_protected` reports whether a path of that kind is named."
            ),
            "criteria": {
                "true": (
                    "Carrying out the task alters one of those. Example: \"turn on live_mode in "
                    "the config\"; \"raise the position cap in config/risk_limits.yaml\"; "
                    "\"rewrite the hook under .claude/hooks\"; \"rebase and force-push the "
                    "branch\"; \"change what the auditor is defined to check\"."
                ),
                "false": (
                    "The task stays inside what is delegated. Example: \"write a research script "
                    "that only reads data\"; \"run the test suite\"; \"add a document under "
                    "docs/\"; \"call the order path with --dry-run and send nothing\"."
                ),
            },
        },
        "is_bounded": {
            "type": "noul",
            "instructions": (
                "The prompt states what \"done\" looks like and what must not be done. "
                "`required_outputs` counts the numbered items demanded in the report section and "
                "`has_stop_condition` reports whether a prohibition is written."
            ),
            "criteria": {
                "true": (
                    "Both the finished shape and the boundary are written down. Example: \"report "
                    "(1) the files and their line counts, (2) the command you ran and its output, "
                    "(3) the last line of the test run; do not commit, do not push, send nothing "
                    "for real\"."
                ),
                "false": (
                    "The finished shape or the boundary is missing. Example: \"look into the "
                    "delegation tooling and improve what you can\" with no list of outputs and no "
                    "prohibition."
                ),
            },
        },
    }


# ---------------------------------------------------------------------------
# 合成(code。段は `config/jev_delegation_tiers.yaml` の規則で当てる)
# ---------------------------------------------------------------------------
def load_tiers(path: Path = TIERS_PATH) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in ("tiers", "rules", "default_tier", "marks", "model_to_tier"):
        if key not in data:
            raise SystemExit(f"[jev_delegate] 段の表に {key} が無い: {path}")
    return data


def _threshold(name) -> float:
    """しきい値の名前(attention / presence / kind_confident)か、数値そのもの。"""
    if isinstance(name, (int, float)):
        return float(name)
    if name not in THRESHOLD_BY_NAME:
        raise SystemExit(f"[jev_delegate] 知らないしきい値の名前: {name}")
    return THRESHOLD_BY_NAME[name]


def _noul(answers: dict, qid: str) -> float:
    return float((answers.get(qid) or {}).get("noul", 0.0))


def kind_answer(answers: dict) -> tuple[str | None, float, dict]:
    """(最尤の種類, 確信度, 種類ごとの確率)。"""
    a = answers.get("task_kind") or {}
    probs = a.get("probabilities") or {}
    top = max(probs, key=probs.get) if probs else None
    return top, float(a.get("confidence") or 0.0), probs


def _rule_matches(rule: dict, kind: str | None, confident: bool, answers: dict) -> bool:
    if rule.get("require_kind_confidence") and not confident:
        return False
    if "kind" in rule and kind != rule["kind"]:
        return False
    if "kind_in" in rule and kind not in rule["kind_in"]:
        return False
    for qid, thr in (rule.get("noul_at_least") or {}).items():
        if _noul(answers, qid) < _threshold(thr):
            return False
    for qid, thr in (rule.get("noul_complement_at_least") or {}).items():
        if 1.0 - _noul(answers, qid) < _threshold(thr):
            return False
    return True


def decide_tier(answers: dict, config: dict) -> dict:
    """段の**候補**を当てる。**選ぶのはリードとオーナーで、この関数ではない。**"""
    kind, confidence, probs = kind_answer(answers)
    confident = confidence >= KIND_CONFIDENT
    tier_id = config["default_tier"]
    rule_id = "default"
    for rule in config["rules"]:
        if _rule_matches(rule, kind, confident, answers):
            tier_id = rule["tier"]
            rule_id = rule.get("id", rule["tier"])
            break
    tier = config["tiers"][tier_id]
    return {
        "task_kind": kind,
        "task_kind_probabilities": probs,
        "task_kind_confidence": round(confidence, 4),
        "kind_confident": confident,
        "tier_id": tier_id,
        "tier_label": tier["label"],
        "tier_model_tier": tier.get("model_tier"),
        "rule": rule_id,
    }


def decide_marks(answers: dict, config: dict) -> list[dict]:
    """印(段とは別)。**印であって判断ではない。**"""
    out: list[dict] = []
    for mark in config["marks"]:
        if not _rule_matches(mark, None, True, answers):
            continue
        # 印が付いた側の確率を記録する(「反する側」で付いた印には 1 - noul を載せる)
        direct = mark.get("noul_at_least") or {}
        complement = mark.get("noul_complement_at_least") or {}
        if direct:
            qid = next(iter(direct))
            value = _noul(answers, qid)
        elif complement:
            qid = next(iter(complement))
            value = 1.0 - _noul(answers, qid)
        else:
            qid, value = None, None
        out.append({"id": mark["id"], "label": mark["label"], "question": qid,
                    "probability": round(value, 4) if value is not None else None})
    return out


def combine(answers: dict, config: dict) -> dict:
    """1 本の委任文についての、段の候補・印・問いごとの確率。"""
    rec = decide_tier(answers, config)
    marks = decide_marks(answers, config)
    rec["marks"] = marks
    rec["mark_labels"] = [m["label"] for m in marks]
    rec["nouls"] = {qid: round(_noul(answers, qid), 4)
                    for qid in ("needs_cross_file_reasoning", "is_mechanical",
                                "needs_owner_approval", "is_bounded")}
    # `flag_counts` と `summary_line` を使い回すため、印の有無を `flag` として持つ
    rec["flag"] = bool(marks)
    return rec


def compares_as(tier_id: str, config: dict) -> str:
    return config["tiers"][tier_id].get("compares_as", tier_id)


# ---------------------------------------------------------------------------
# 送信
# ---------------------------------------------------------------------------
def _client_or_none(model: str, dry_run: bool) -> tuple[JevClient | None, str | None]:
    if dry_run:
        return None, None
    try:
        return JevClient(model=model), None
    except JevError as e:
        return None, str(e)


def ask(client: JevClient, state: dict) -> dict:
    """伏せ字を通してから 1 要求送る。伏せ字に掛かったら `RedactionError`。"""
    return client.evaluate(state=clean_state(state), questions=questions())


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------
def _write_jsonl(out_dir: Path, name: str, records: list[dict], summary: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / name
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return out_path


def cmd_plan(args) -> int:
    path = Path(args.prompt)
    if not path.is_file():
        print(f"[jev_delegate] 委任文のファイルが無い: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")
    config = load_tiers()
    state = build_state(text)

    client, unreachable = _client_or_none(args.model, args.dry_run)
    rec: dict = {
        "source": path.name,
        "kind": "delegation_plan",
        "n_files": state["n_files"],
        "total_lines": state["total_lines"],
        "touches_protected": state["touches_protected"],
        "required_outputs": state["required_outputs"],
        "has_stop_condition": state["has_stop_condition"],
        "files_named": [f["path"] for f in state["files_named"]],
        "tier_id": None,
        "tier_label": None,
        "marks": [],
        "flag": False,
        "sent": False,
    }
    n_requests = 0
    if client is not None:
        try:
            resp = ask(client, state)
        except RedactionError as e:
            print(f"[jev_delegate] 伏せ字の最終検査に掛かったので送信しない: {e}", file=sys.stderr)
            return 2
        except JevError as e:
            unreachable = str(e)
            print(f"[jev_delegate] 送信に失敗: {e}", file=sys.stderr)
        else:
            n_requests = 1
            answers = resp.get("answers") or {}
            rec.update(combine(answers, config))
            rec["sent"] = True
            rec["model"] = resp.get("model")

    if args.dry_run or n_requests > 0:
        unreachable = None

    n_flag, by_kind = flag_counts([rec])
    if rec["flag"]:
        by_kind = {m["id"]: 1 for m in rec["marks"]}
        n_flag = len(rec["marks"])
    summary = {
        "file": path.name,
        "kind": "_summary",
        "n_pairs": 1,
        "n_sent": 1 if rec["sent"] else 0,
        "n_requests": n_requests,
        "n_flag": n_flag,
        "flag_by_kind": by_kind,
        "tier_id": rec["tier_id"],
        "tier_label": rec["tier_label"],
        "dry_run": bool(args.dry_run),
        "unreachable": unreachable,
        "threshold": {"attention": ATTENTION, "presence": PRESENCE,
                      "kind_confident": KIND_CONFIDENT},
    }
    out_path = _write_jsonl(Path(args.out),
                            datetime.now().strftime("plan_%Y%m%d_%H%M%S.jsonl"),
                            [rec], summary)

    if not args.summary:
        _print_plan(path.name, out_path, state, rec, summary)
    print(_plan_summary_line(summary))
    return 0


def _plan_summary_line(summary: dict) -> str:
    """末尾の 1 行(`summary_line` をそのまま使い、段の候補を足す)。"""
    label = summary.get("tier_label") or "未評価"
    return f"{summary_line(summary)} 段の候補: {label}"


def _p(value) -> str:
    return "-" if value is None else f"{float(value):.3f}"


def _print_plan(source: str, out_path: Path, state: dict, rec: dict, summary: dict) -> None:
    print(f"委任文: {source}  拾ったパス: {state['n_files']}  総行数: {state['total_lines']}  "
          f"必須報告: {state['required_outputs']} 項目  "
          f"禁止文: {'あり' if state['has_stop_condition'] else 'なし'}  "
          f"保護パス: {'当たる' if state['touches_protected'] else '当たらない'}"
          + ("  (--dry-run: 1 件も送っていない)" if summary["dry_run"] else ""))
    if state["files_named"]:
        print("拾ったパス: " + " / ".join(
            f"{f['path']}({f['lines']} 行)" if f["exists"] and not f.get("is_dir")
            else f"{f['path']}({'ディレクトリ' if f.get('is_dir') else '不在'})"
            for f in state["files_named"]))
    print(f"{'問い':<28}{'型':<8}{'確率':>10}  補足")
    probs = rec.get("task_kind_probabilities") or {}
    top = rec.get("task_kind")
    print(f"{'task_kind':<28}{'choice':<8}{_p(probs.get(top) if top else None):>10}  "
          f"{top or '-'}(確信度 {_p(rec.get('task_kind_confidence'))}"
          f"{'' if (rec.get('kind_confident') or not rec.get('sent')) else f' < {KIND_CONFIDENT} なので粗い答え'})")
    for qid in ("needs_cross_file_reasoning", "is_mechanical",
                "needs_owner_approval", "is_bounded"):
        print(f"{qid:<28}{'noul':<8}{_p((rec.get('nouls') or {}).get(qid)):>10}")
    print(f"段の候補: {rec.get('tier_label') or '-'}"
          f"({rec.get('tier_model_tier') or '-'}、当たった規則 {rec.get('rule') or '-'})")
    print("印: " + ("、".join(f"{m['label']}({_p(m['probability'])})" for m in rec["marks"])
                    or "なし"))
    print(f"(しきい値 attention={ATTENTION} / presence={PRESENCE} / "
          f"kind_confident={KIND_CONFIDENT}。**段の候補と印であって判断ではない。"
          "選ぶのはリードとオーナーである**)")
    print(f"書いた先: {out_path}")


# ---------------------------------------------------------------------------
# calibrate
# ---------------------------------------------------------------------------
def extract_delegations(record: Path) -> list[dict]:
    """会話の記録から `Agent` の道具呼び出し(prompt と model)を **code で全部**抜く。"""
    out: list[dict] = []
    with record.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            msg = d.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if block.get("name") != "Agent":
                    continue
                inp = block.get("input") or {}
                prompt = inp.get("prompt")
                if not isinstance(prompt, str) or not prompt.strip():
                    continue
                out.append({
                    "index": len(out) + 1,
                    "model": inp.get("model"),
                    "subagent_type": inp.get("subagent_type"),
                    "description": inp.get("description"),
                    "prompt": prompt,
                    "prompt_head": prompt.strip().replace("\n", " ")[:PROMPT_HEAD_CHARS],
                    "prompt_chars": len(prompt),
                })
    return out


def cmd_calibrate(args) -> int:
    record = Path(args.transcript)
    if not record.is_file():
        print(f"[jev_delegate] 会話の記録が無い: {record}", file=sys.stderr)
        return 1
    config = load_tiers()
    calls = extract_delegations(record)
    client, unreachable = _client_or_none(args.model, args.dry_run)

    records: list[dict] = []
    n_requests = 0
    n_match = n_mismatch = n_unmapped = n_unevaluated = 0
    for call in calls:
        chosen_tier = config["model_to_tier"].get(call["model"])
        rec = {
            "source": record.name,
            "kind": "delegation_calibrate",
            "index": call["index"],
            "model": call["model"],
            "subagent_type": call["subagent_type"],
            "prompt_head": call["prompt_head"],
            "prompt_chars": call["prompt_chars"],
            "chosen_tier": chosen_tier,
            "chosen_tier_label": (config["tiers"][chosen_tier]["label"]
                                  if chosen_tier else None),
            "tier_id": None,
            "tier_label": None,
            "agreement": None,
            "flag": False,
            "sent": False,
        }
        if client is not None:
            state = build_state(call["prompt"])
            try:
                resp = ask(client, state)
            except RedactionError as e:
                print(f"[jev_delegate] 伏せ字の最終検査に掛かったので送信しない: {e}",
                      file=sys.stderr)
                return 2
            except JevError as e:
                unreachable = str(e)
                print(f"[jev_delegate] 送信に失敗(委任 {call['index']}): {e}", file=sys.stderr)
            else:
                n_requests += 1
                rec.update(combine(resp.get("answers") or {}, config))
                rec["sent"] = True
                rec["model_answered"] = resp.get("model")

        if not rec["sent"]:
            rec["agreement"] = "未評価"
            n_unevaluated += 1
        elif chosen_tier is None:
            rec["agreement"] = "対応表に無い"
            n_unmapped += 1
        elif compares_as(rec["tier_id"], config) == compares_as(chosen_tier, config):
            rec["agreement"] = "一致"
            n_match += 1
        else:
            rec["agreement"] = "不一致"
            n_mismatch += 1
        records.append(rec)

    if args.dry_run or n_requests > 0 or not calls:
        unreachable = None

    summary = {
        "file": record.name,
        "kind": "_summary",
        "n_delegations": len(calls),
        "n_sent": sum(1 for r in records if r["sent"]),
        "n_requests": n_requests,
        "n_match": n_match,
        "n_mismatch": n_mismatch,
        "n_unmapped": n_unmapped,
        "n_unevaluated": n_unevaluated,
        "n_flag": sum(1 for r in records if r["flag"]),
        "flag_by_kind": {},
        "dry_run": bool(args.dry_run),
        "unreachable": unreachable,
        "threshold": {"attention": ATTENTION, "presence": PRESENCE,
                      "kind_confident": KIND_CONFIDENT},
    }
    out_path = _write_jsonl(Path(args.out),
                            datetime.now().strftime("calibrate_%Y%m%d_%H%M%S.jsonl"),
                            records, summary)

    if not args.summary:
        _print_calibrate(record.name, out_path, records, summary)
    print(_calibrate_summary_line(summary))
    return 0


def _calibrate_summary_line(summary: dict) -> str:
    if summary.get("unreachable"):
        return f"jev: 未到達({summary['unreachable']})"
    tail = "(--dry-run: 1 件も送っていない)" if summary.get("dry_run") else ""
    return (f"委任 {summary['n_delegations']} 件: 一致 {summary['n_match']} 件 / "
            f"不一致 {summary['n_mismatch']} 件 / 対応表に無い {summary['n_unmapped']} 件 / "
            f"未評価 {summary['n_unevaluated']} 件{tail}")


def _print_calibrate(source: str, out_path: Path, records: list[dict],
                     summary: dict) -> None:
    print(f"会話の記録: {source}  抜けた委任: {summary['n_delegations']} 件  "
          f"送った要求の数: {summary['n_requests']}"
          + ("  (--dry-run: 1 件も送っていない)" if summary["dry_run"] else ""))
    print(f"{'#':>3} {'model':<10}{'リードの段':<14}{'推奨の段':<22}{'突き合わせ':<12}先頭 "
          f"{PROMPT_HEAD_CHARS} 字")
    for rec in records:
        print(f"{rec['index']:>3} {str(rec['model']):<10}"
              f"{str(rec['chosen_tier_label'] or '対応表に無い'):<14}"
              f"{str(rec['tier_label'] or '-'):<22}{str(rec['agreement']):<12}"
              f"{rec['prompt_head']}")
    mismatched = [r for r in records if r["agreement"] == "不一致"]
    if mismatched:
        print("\n不一致の一覧:")
        for rec in mismatched:
            print(f"  #{rec['index']} リード={rec['chosen_tier_label']} / "
                  f"推奨={rec['tier_label']}(規則 {rec.get('rule')}、"
                  f"種類 {rec.get('task_kind')} 確信度 {_p(rec.get('task_kind_confidence'))})"
                  f"  {rec['prompt_head']}")
    print("\n(これは正解との一致ではなく、**リードの選択との一致**である。"
          "どちらが誤りかはこの道具は書かない)")
    print(f"書いた先: {out_path}")


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="委任文から state を code で組み、段の候補と印を出す(選ぶのは人)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--prompt", required=True, help="委任文が入ったファイル")
    p_plan.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p_plan.add_argument("--dry-run", action="store_true")
    p_plan.add_argument("--summary", action="store_true", help="末尾の 1 行だけを出す")
    p_plan.add_argument("--model", default=DEFAULT_MODEL)
    p_plan.set_defaults(func=cmd_plan)

    p_cal = sub.add_parser("calibrate")
    p_cal.add_argument("--transcript", required=True, help="会話の記録(JSONL)")
    p_cal.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p_cal.add_argument("--dry-run", action="store_true")
    p_cal.add_argument("--summary", action="store_true", help="末尾の 1 行だけを出す")
    p_cal.add_argument("--model", default=DEFAULT_MODEL)
    p_cal.set_defaults(func=cmd_calibrate)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
