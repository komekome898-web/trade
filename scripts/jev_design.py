#!/usr/bin/env python3
"""設計の段の判定(`jev_design`)。**Jev は決めない。**順位と依存の有無を返し、選ぶのはリード。

出所: オーナー逐語 L-242「**jev_design.pyを作ってください。あなた単体の設計よりもよっぽど
信頼できるので、設計の段階でjevの判定(もしくはその代替となるもの)がないと事前登録させないことを
監査役の仕事に加えてください。**」/ 手引き `docs/JEV.md` §10 / 実測 `docs/DATA/probes/20260919_jev_select_rank_probe.py`。

サブコマンド:
  rank-observables  意図(設計の意図マップの逐語)× 候補の量 を score で点数化し、意図ごとに順位を出す。
  rank-covariates   判定の量 × 変数 を noul で問い、対照で合わせるべき変数を並べる。
  record-substitute Jev に届かないときの代替(独立の下位モデル 2 名の記録)を同じ形の markdown にする。

規律:
  - **確率・期待値は `--out` の json にだけ**書く。リポジトリに入る markdown(`--md`)には
    **順位と語だけ**を書く(`docs/JEV.md` §7「数値の結果をリポジトリに書かないか」)。
  - しきい値は `scripts/jev_check.py` の `PRESENCE` を import して使う(新しい数値を置かない)。
  - 問いは 1 回の送信に全問まとめて入れる(probe と同じ)。
  - Jev に届かなければ `status: stopped` を返し、標準エラーにその旨を出す(判定を代わりにしない)。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.jev.client import JevClient, JevError  # noqa: E402
from scripts.jev_check import (  # noqa: E402
    DEFAULT_MODEL,
    PRESENCE,
    clean_state,
    extract_intent_rows,
)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
# probe(2026-09-19)と同じ 5 文。0 番から 4 番の 5 段階で、API の `score` は 0〜4 の期待値である。
SCORE_CRITERIA = [
    "does not express it, or only through an unrelated proxy",
    "weak proxy: related but its value is mostly determined by something else "
    "(e.g. a fixed reference level)",
    "partial: expresses one side (e.g. continuation only) or is undefined for many cases",
    "direct: its sign or value directly says what the intent asks",
    "direct and complete: it answers the intent and its size, defined for every case",
]
# 語の境目。数値は指示の逐語「直接(3 以上)/ 代理(2 台)/ 無関係(1 以下)」から取った(新設ではない)。
BAND_DIRECT = 3.0
BAND_PROXY = 2.0
LABEL_DIRECT = "直接(3 以上)"
LABEL_PROXY = "代理(2 台)"
LABEL_UNRELATED = "無関係(1 以下)"
# 変数の語。分かれ目は `jev_check.PRESENCE`(0.50)をそのまま使う。
LABEL_MATCH = "合わせる"
LABEL_NO_MATCH = "合わせなくてよい"

HEADING = "## 設計の段の判定(jev_design、{day}、モデル {model})"
NOT_DECIDED = ("この道具は判定の中身(どの量を選ぶか)を決めない。"
               "出すのは順位と語だけで、選ぶのはリードである。確率と期待値は json にだけ残す。")


# ---------------------------------------------------------------------------
# 入力
# ---------------------------------------------------------------------------
def load_candidates(path: Path) -> dict:
    """名前 → 定義(文)の辞書を yaml / json から読む。"""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml  # 遅延 import(json だけのときに依存を要求しない)

        obj = yaml.safe_load(text)
    else:
        obj = json.loads(text)
    if not isinstance(obj, dict) or not obj:
        raise ValueError(f"{path}: 名前 → 定義 の辞書ではない(空、または辞書でない)")
    for k, v in obj.items():
        if not isinstance(k, str) or not isinstance(v, str) or not v.strip():
            raise ValueError(f"{path}: `{k}` の定義が文(文字列)ではない")
    return {str(k): str(v) for k, v in obj.items()}


def design_intent_rows(design: Path, intent_ids: list[str] | None = None) -> list[dict]:
    """設計文書 **そのもの**の意図マップの ○ / △ / ✕ の行を取る。

    `jev_check.extract_intent_rows` は「成果物と同じディレクトリの意図マップ」を探す作りで、
    成果物そのものは除く。ここでは設計文書自身が意図マップなので、同じディレクトリに置いた
    実在しない札を成果物として渡し、出てきた行を設計文書のものだけに絞る。
    """
    sentinel = design.parent / "__jev_design_not_a_file__.md"
    rows = [r for r in extract_intent_rows(sentinel) if r.get("source") == design.name]
    if not rows:
        raise ValueError(
            f"{design}: 意図マップの行(○ / △ / ✕)が 1 行も取れない。"
            "ファイル名が `*DESIGN*.md` か `INTENT_MAP.md` に合致し、"
            "表に「原文の意図(逐語)」列と「印」列があるかを確かめること"
        )
    if intent_ids:
        want = {i.strip() for i in intent_ids if i.strip()}
        rows = [r for r in rows if _intent_id(r) in want]
        missing = want - {_intent_id(r) for r in rows}
        if missing:
            raise ValueError(f"{design}: 指定した意図が見つからない: {sorted(missing)}")
    return rows


def _intent_id(row: dict) -> str:
    return str(row.get("id", "")).strip().strip("*").strip()


# ---------------------------------------------------------------------------
# 問いの組み立て(1 回の送信に全問)
# ---------------------------------------------------------------------------
def qid_for(intent_id: str, name: str) -> str:
    return f"{intent_id}__{name}"


def build_observable_state(rows: list[dict], observables: dict) -> dict:
    return {
        "purpose_intents": {
            _intent_id(r): {
                "intent_verbatim": r.get("intent", ""),
                "mark": r.get("mark", ""),
                "source_row": r.get("row", ""),
            }
            for r in rows
        },
        "candidate_observables": observables,
    }


def build_observable_questions(rows: list[dict], observables: dict) -> dict:
    questions = {}
    for r in rows:
        iid = _intent_id(r)
        for name in observables:
            questions[qid_for(iid, name)] = {
                "type": "score",
                "instructions": (
                    f"How directly does `candidate_observables.{name}` express what "
                    f"`purpose_intents.{iid}.intent_verbatim` asks?"
                ),
                "criteria": list(SCORE_CRITERIA),
            }
    return questions


def build_covariate_state(quantity: str, covariates: dict) -> dict:
    return {"judgment_quantity": quantity, "covariates": covariates}


def build_covariate_questions(covariates: dict) -> dict:
    return {
        name: {
            "type": "noul",
            "instructions": (
                f"By construction of `judgment_quantity`, is its value strongly determined by "
                f"`covariates.{name}` regardless of the mechanism under study, so that a control "
                f"group must be matched on it for a fair comparison?"
            ),
            "criteria": {
                "true": "yes: the quantity's value depends mechanically on this covariate "
                        "(e.g. how far price must travel)",
                "false": "no: the covariate may correlate with the outcome but does not "
                         "determine it by construction",
            },
        }
        for name in covariates
    }


# ---------------------------------------------------------------------------
# 答えの読み(期待値)
# ---------------------------------------------------------------------------
def expected_value(answer: dict) -> float:
    """score の答えから期待値を出す。`probabilities`(0〜4 の段)があればそれで計算する。"""
    probs = answer.get("probabilities") if isinstance(answer, dict) else None
    if isinstance(probs, dict) and probs:
        total = sum(float(v) for v in probs.values())
        ev = sum(float(k) * float(v) for k, v in probs.items())
        return ev / total if total else ev
    score = answer.get("score") if isinstance(answer, dict) else None
    if isinstance(score, (int, float)):
        return float(score)
    raise ValueError(f"score の答えに probabilities も score も無い: {answer!r}")


def band(ev: float) -> str:
    if ev >= BAND_DIRECT:
        return LABEL_DIRECT
    if ev >= BAND_PROXY:
        return LABEL_PROXY
    return LABEL_UNRELATED


def noul_value(answer: dict) -> float:
    if not isinstance(answer, dict) or "noul" not in answer:
        raise ValueError(f"noul の答えが無い: {answer!r}")
    return float(answer["noul"])


# ---------------------------------------------------------------------------
# markdown(**確率と期待値は書かない**)
# ---------------------------------------------------------------------------
def _header(model: str, lines: list[str], day: str | None = None) -> list[str]:
    out = [HEADING.format(day=day or date.today().isoformat(), model=model), ""]
    out += lines
    out += ["", NOT_DECIDED, ""]
    return out


def render_observables_md(result: dict) -> str:
    lines = _header(
        result["model"],
        [
            f"- 設計文書: `{result['design']}`",
            f"- 候補ファイル: `{result['observables_file']}`",
            f"- 意図: {', '.join(result['intent_ids']) or '(全行)'}",
        ],
        result.get("generated"),
    )
    if result.get("status") == "stopped":
        lines += [f"**停止(stopped)**: Jev に届かなかった({result.get('reason', '')})。",
                  "`record-substitute` で代替の記録を出すこと。", ""]
        return "\n".join(lines) + "\n"
    for item in result["intents"]:
        lines += [f"### {item['id']} {item['intent']}(印 {item['mark']})", "",
                  "| 順位 | 量 | 語 |", "|---|---|---|"]
        for row in item["ranking"]:
            lines.append(f"| {row['rank']} | `{row['name']}` | {row['band']} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_covariates_md(result: dict) -> str:
    lines = _header(
        result["model"],
        [
            f"- 判定の量: {result['quantity']}",
            f"- 変数ファイル: `{result['covariates_file']}`",
            "- 意図: (この段は量と変数の対なので意図の番号は無い)",
        ],
        result.get("generated"),
    )
    if result.get("status") == "stopped":
        lines += [f"**停止(stopped)**: Jev に届かなかった({result.get('reason', '')})。",
                  "`record-substitute` で代替の記録を出すこと。", ""]
        return "\n".join(lines) + "\n"
    lines += ["### 対照で合わせる変数", "", "| 順位 | 変数 | 語 |", "|---|---|---|"]
    for row in result["ranking"]:
        lines.append(f"| {row['rank']} | `{row['name']}` | {row['label']} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_substitute_md(record_path: Path, body: str, day: str | None = None) -> str:
    lines = _header(
        "代替(下位モデル 2 名)",
        [f"- 記録: `{record_path}`", "- 設計文書・候補ファイル・意図の番号は記録の本文にある"],
        day,
    )
    lines += [f"### 代替(Jev 不達、記録 = {record_path})", "", body.rstrip(), ""]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 実行
# ---------------------------------------------------------------------------
def _write(out: Path | None, obj: dict) -> None:
    if out is None:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def _write_md(md: Path | None, text: str) -> None:
    if md is None:
        return
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(text, encoding="utf-8")


def _send(client, state: dict, questions: dict) -> tuple[dict | None, str | None]:
    try:
        return client.evaluate(clean_state(state), questions), None
    except JevError as e:
        print(f"jev_design: 未到達({e})。stopped — 判定は代わりに行わない。"
              "`record-substitute` で独立の下位モデル 2 名の記録を代替として出すこと",
              file=sys.stderr)
        return None, str(e)


def rank_observables(design: Path, observables_file: Path, *, intent_ids: list[str] | None = None,
                     model: str = DEFAULT_MODEL, out: Path | None = None,
                     md: Path | None = None) -> dict:
    rows = design_intent_rows(design, intent_ids)
    observables = load_candidates(observables_file)
    state = build_observable_state(rows, observables)
    questions = build_observable_questions(rows, observables)
    result = {
        "command": "rank-observables",
        "generated": date.today().isoformat(),
        "model": model,
        "design": str(design),
        "observables_file": str(observables_file),
        "intent_ids": [_intent_id(r) for r in rows] if not intent_ids else list(intent_ids),
        "n_questions": len(questions),
    }
    resp, reason = _send(JevClient(model=model), state, questions)
    if resp is None:
        result["status"] = "stopped"
        result["reason"] = reason
        _write(out, result)
        _write_md(md, render_observables_md(result))
        return result

    answers = resp.get("answers", {})
    intents = []
    for r in rows:
        iid = _intent_id(r)
        scored = []
        for name in observables:
            ans = answers.get(qid_for(iid, name), {})
            ev = expected_value(ans)
            scored.append({"name": name, "expected": ev, "band": band(ev),
                           "probabilities": ans.get("probabilities"),
                           "confidence": ans.get("confidence")})
        scored.sort(key=lambda d: (-d["expected"], d["name"]))
        for i, d in enumerate(scored, 1):
            d["rank"] = i
        intents.append({"id": iid, "intent": r.get("intent", ""), "mark": r.get("mark", ""),
                        "ranking": scored})
    result.update({"status": "ok", "model_answered": resp.get("model"),
                   "usage": resp.get("usage"), "intents": intents})
    _write(out, result)
    _write_md(md, render_observables_md(result))
    return result


def rank_covariates(quantity: str, covariates_file: Path, *, model: str = DEFAULT_MODEL,
                    out: Path | None = None, md: Path | None = None) -> dict:
    covariates = load_candidates(covariates_file)
    state = build_covariate_state(quantity, covariates)
    questions = build_covariate_questions(covariates)
    result = {
        "command": "rank-covariates",
        "generated": date.today().isoformat(),
        "model": model,
        "quantity": quantity,
        "covariates_file": str(covariates_file),
        "threshold_name": "PRESENCE",
        "n_questions": len(questions),
    }
    resp, reason = _send(JevClient(model=model), state, questions)
    if resp is None:
        result["status"] = "stopped"
        result["reason"] = reason
        _write(out, result)
        _write_md(md, render_covariates_md(result))
        return result

    answers = resp.get("answers", {})
    ranking = []
    for name in covariates:
        p = noul_value(answers.get(name, {}))
        ranking.append({"name": name, "noul": p,
                        "label": LABEL_MATCH if p >= PRESENCE else LABEL_NO_MATCH})
    ranking.sort(key=lambda d: (-d["noul"], d["name"]))
    for i, d in enumerate(ranking, 1):
        d["rank"] = i
    result.update({"status": "ok", "model_answered": resp.get("model"),
                   "usage": resp.get("usage"), "ranking": ranking})
    _write(out, result)
    _write_md(md, render_covariates_md(result))
    return result


def record_substitute(record: Path, md: Path) -> dict:
    body = record.read_text(encoding="utf-8")
    _write_md(md, render_substitute_md(record, body))
    return {"command": "record-substitute", "status": "substitute",
            "generated": date.today().isoformat(), "record": str(record), "md": str(md)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _split_intents(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def cmd_rank_observables(args) -> int:
    res = rank_observables(
        Path(args.purpose_from), Path(args.observables),
        intent_ids=_split_intents(args.intent), model=args.model,
        out=Path(args.out) if args.out else None,
        md=Path(args.md) if args.md else None,
    )
    print(f"jev_design: rank-observables {res['status']}(問い {res['n_questions']} 件)")
    return 0


def cmd_rank_covariates(args) -> int:
    res = rank_covariates(
        args.quantity, Path(args.covariates), model=args.model,
        out=Path(args.out) if args.out else None,
        md=Path(args.md) if args.md else None,
    )
    print(f"jev_design: rank-covariates {res['status']}(問い {res['n_questions']} 件)")
    return 0


def cmd_record_substitute(args) -> int:
    res = record_substitute(Path(getattr(args, "from")), Path(args.md))
    print(f"jev_design: record-substitute {res['status']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="設計の段の判定。Jev は決めない(順位と語だけ。選ぶのはリード)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("rank-observables")
    p1.add_argument("--purpose-from", required=True, dest="purpose_from")
    p1.add_argument("--intent", default=None, help="I-1,I-12 のように絞る(既定は全行)")
    p1.add_argument("--observables", required=True)
    p1.add_argument("--out", default=None)
    p1.add_argument("--md", default=None)
    p1.add_argument("--model", default=DEFAULT_MODEL)
    p1.set_defaults(func=cmd_rank_observables)

    p2 = sub.add_parser("rank-covariates")
    p2.add_argument("--quantity", required=True)
    p2.add_argument("--covariates", required=True)
    p2.add_argument("--out", default=None)
    p2.add_argument("--md", default=None)
    p2.add_argument("--model", default=DEFAULT_MODEL)
    p2.set_defaults(func=cmd_rank_covariates)

    p3 = sub.add_parser("record-substitute")
    p3.add_argument("--from", required=True, dest="from")
    p3.add_argument("--md", required=True)
    p3.set_defaults(func=cmd_record_substitute)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
