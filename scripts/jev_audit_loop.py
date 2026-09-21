#!/usr/bin/env python3
"""監査の巡ごとの指摘を並べ、**同じ指摘が何巡続いているか**を出す(`docs/JEV.md` §8 の U9)。

出所は I-011(オーナー逐語 L-206: 「**I-011は「監査無限ループにより10時間失った」です**」)。
段 A の走行前の監査は 10 巡まで膨らみ、オーナーが L-200 で打ち切った。

**この道具は何も判定しない。**出すのは「同じ指摘が N 巡続いている」という事実と確率だけで、
**打ち切りの判断は規則(L-200)とリード・オーナーが行う**(オーナー逐語 L-218:
「**判断はLLMと私の役割である**」)。出力に「止めるべき」の語は置かない(`docs/JEV.md` §4-1)。

  rounds <巡の記録.md>...   巡 k の指摘 1 件ごとに、巡 k−1 の指摘の一覧の中から
                            「同じ欠陥を指しているもの」を 1 つ選ばせる(choice + none)。
                            **前の巡だけと比べる**(全巡と比べると要求数が二乗で増えるため)。

規則(`docs/JEV.md` §4):
- 切り出しも合成も **code**(決定論的)。数える・連鎖を辿るのは code。Jev は「同じ欠陥か」だけ。
- state は code が組む(判定される側が書かない)。断片は日本語のまま、問いは英語・肯定形。
- 送信前に `redact_json` + `assert_clean`(`jev_check.clean_state` を再利用)。
- 版は既定 `jev-1.13.0` 固定(`jev_check.DEFAULT_MODEL`)。応答の `model` を記録する。
- しきい値はこのファイルの先頭に定数として 1 箇所だけ置く。**結果を見てから動かさない。**

使い方:
  python3 scripts/jev_audit_loop.py rounds docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg*.md \
      [--order args|rnumber] [--out data/jev/audit_loop/] [--dry-run] [--summary] [--model ID]
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
# 指摘の切り出しは `jev_audit_eval` のものをそのまま使う(同じ切り方を共有する)
from scripts.jev_audit_eval import auditor_text, split_findings  # noqa: E402
# 伏せ字の最終検査・版・未到達の 1 行は `jev_check` の部品をそのまま使う
from scripts.jev_check import (  # noqa: E402
    DEFAULT_MODEL,
    clean_state,
    summary_line as check_summary_line,
)

# ---------------------------------------------------------------------------
# 定数(しきい値はこの 1 箇所だけ)
# ---------------------------------------------------------------------------
SAME_CONFIDENT = 0.60   # choice の確信度がこれ未満なら「同じ」と数えない(E.16「粗く答える」)
PRESENCE = 0.50         # noul がこれ以上なら「その型である」側に置く(`jev_check` と同じ役割・同じ値)
PREV_HEAD_CHARS = 300   # 前の巡の指摘を選択肢の説明にするときの先頭の文字数(仕様どおり)
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "audit_loop"
NONE_OPTION = "none"

_R_NUMBER_RE = re.compile(r"_r(\d+)(?=\.[^.]+$|$)")


# ---------------------------------------------------------------------------
# 巡の順(決定論的。規則は報告に書く)
# ---------------------------------------------------------------------------
def r_number(path: Path) -> int:
    """ファイル名の末尾の `_r<数>` を巡の番号として読む。無ければ 1 巡目とする。

    `2026-09-18_reaction_prereg.md` → 1、`…_r2.md` → 2、`…_r10.md` → 10。
    """
    m = _R_NUMBER_RE.search(path.name)
    return int(m.group(1)) if m else 1


def order_paths(paths: list[Path], order: str) -> tuple[list[Path], bool]:
    """(並べ替えた一覧, 引数の順と r 番号の順が違うか)。

    `order="args"`(既定)= 引数の順をそのまま巡の順とする(仕様の第 1 文)。
    `order="rnumber"` = ファイル名の r 番号で並べ替える(仕様の第 2 文。殻の展開は
    `prereg.md, prereg_r10.md, prereg_r2.md…` の辞書順になるので、その順を直すため)。
    どちらでも**食い違いがあれば表示する**(黙って並べ替えない・黙って辞書順で進めない)。
    """
    by_r = sorted(paths, key=lambda p: (r_number(p), p.name))
    differs = [p.name for p in paths] != [p.name for p in by_r]
    return (by_r if order == "rnumber" else list(paths)), differs


# ---------------------------------------------------------------------------
# 読み込み(巡 → 指摘の一覧)
# ---------------------------------------------------------------------------
def load_rounds(paths: list[Path]) -> list[dict]:
    """各巡の指摘を切り出し、巡をまたいで一意な id を振る。

    id は `r<巡>#<指摘の番号>`。同じ巡に同じ番号が 2 回出たら `-2`, `-3` を足す
    (choice の選択肢は一意でなければ答えを鍵で読めないため)。
    """
    rounds: list[dict] = []
    for k, path in enumerate(paths, start=1):
        findings = split_findings(auditor_text(path))
        seen: dict[str, int] = {}
        items = []
        for pos, f in enumerate(findings, start=1):
            base = f"r{k}#{f['index']}"
            seen[base] = seen.get(base, 0) + 1
            fid = base if seen[base] == 1 else f"{base}-{seen[base]}"
            items.append({
                "id": fid,
                "round": k,
                "position": pos,
                "index": f["index"],
                "severity": f["severity"],
                "lineno": f["lineno"],
                "source": f["source"],
                "text": f["text"],
            })
        rounds.append({"round": k, "file": path.name, "path": str(path), "findings": items})
    return rounds


def head(text: str, n: int = PREV_HEAD_CHARS) -> str:
    """選択肢の説明・表示に使う先頭 n 文字(改行は空白に畳む)。"""
    one = " ".join(text.split())
    return one[:n]


# ---------------------------------------------------------------------------
# state と問い(1 判断 1 問・肯定形・英語。断片は日本語のまま)
# ---------------------------------------------------------------------------
def state_for(finding: dict, previous: list[dict]) -> dict:
    """巡 k の指摘 1 件と、巡 k−1 の指摘の一覧(id と先頭 300 字)。"""
    return {
        "finding": finding["text"],
        "previous_findings": [{"id": p["id"], "text": head(p["text"])} for p in previous],
    }


def questions_for(previous: list[dict]) -> dict:
    """`same_issue_as`(choice: 前の巡の id + none)と `resolved_then_reopened`(noul)。"""
    criteria = {p["id"]: head(p["text"]) for p in previous}
    criteria[NONE_OPTION] = (
        "None of the earlier items is about the same defect as `finding`, or none of them "
        "is close enough to name one. Example: every earlier item is about the sample size "
        "and `finding` is about a missing unit on a printed figure."
    )
    return {
        "same_issue_as": {
            "type": "choice",
            "instructions": (
                "`finding` is one item raised by a reviewer while reviewing a document. "
                "Each option below is one item the same reviewer raised in the previous "
                "round of review of that same document. Pick the option that is about the "
                "same defect as `finding`: the thing that has to be changed is the same one, "
                "even when the place, the section or the wording differ."
            ),
            "criteria": criteria,
        },
        "resolved_then_reopened": {
            "type": "noul",
            "instructions": (
                "`finding` says that an earlier fix brought the same defect back, or that "
                "an earlier fix did not remove it."
            ),
            "criteria": {
                "true": (
                    "It refers to a previous correction and says the defect is still there or "
                    "is there again. Example: \"the unit added in the previous round is now "
                    "missing again in the sensitivity table\", or \"this was said to be fixed, "
                    "but the same symbol is still defined twice\"."
                ),
                "false": (
                    "It raises the point without referring to any earlier fix. Example: "
                    "\"the figure 19-48 does not match table.csv\"."
                ),
            },
        },
    }


# ---------------------------------------------------------------------------
# 合成(code。Jev は合成しない)
# ---------------------------------------------------------------------------
def linked_id(choice: str | None, confidence: float | None, previous_ids: set[str]) -> tuple[str | None, str | None]:
    """(結び付けた先の id, 結び付けなかった理由)。

    `none` / 一覧に無い答え / 確信度 `SAME_CONFIDENT` 未満 は結び付けない(E.16)。
    """
    if choice is None:
        return None, "答えが無い"
    if choice == NONE_OPTION:
        return None, None
    if choice not in previous_ids:
        return None, "一覧に無い id を答えた"
    if confidence is None or float(confidence) < SAME_CONFIDENT:
        return None, "低確信(同じとは数えない)"
    return choice, None


def build_chains(rounds: list[dict], links: dict[str, str]) -> tuple[dict[str, int], list[list[str]]]:
    """(id → 連続の巡数, 連鎖の一覧)。`links[子] = 親` は巡 k → 巡 k−1 の 1 本。

    連鎖は「親を持たない指摘」から始めて、子を辿った道を全部出す(親 1 件に子が 2 件つく
    ことがあるので、道は枝分かれしうる)。連続の巡数 = その指摘までの道の長さ。
    """
    order = [f["id"] for r in rounds for f in r["findings"]]
    streak: dict[str, int] = {}
    for fid in order:
        parent = links.get(fid)
        streak[fid] = (streak.get(parent, 0) + 1) if parent else 1
    children: dict[str, list[str]] = {}
    for child, parent in links.items():
        children.setdefault(parent, []).append(child)
    for v in children.values():
        v.sort(key=order.index)
    chains: list[list[str]] = []

    def walk(fid: str, path: list[str]) -> None:
        path = path + [fid]
        kids = children.get(fid, [])
        if not kids:
            chains.append(path)
            return
        for kid in kids:
            walk(kid, path)

    for fid in order:
        if fid not in links:
            walk(fid, [])
    return streak, chains


def round_rows(rounds: list[dict], links: dict[str, str], streak: dict[str, int]) -> list[dict]:
    """巡ごとの: 指摘の数 / 前の巡と同じ N 件 / 新しい M 件 / 最長の連鎖。"""
    rows = []
    for r in rounds:
        ids = [f["id"] for f in r["findings"]]
        same = sum(1 for i in ids if i in links)
        rows.append({
            "kind": "round",
            "round": r["round"],
            "file": r["file"],
            "n_findings": len(ids),
            "n_same_as_previous": same,
            "n_new": len(ids) - same,
            "longest_streak": max([streak[i] for i in ids], default=0),
        })
    return rows


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
# rounds
# ---------------------------------------------------------------------------
def summary_line(summary: dict) -> str:
    """末尾の 1 行。**「止めるべき」は書かない**(事実だけを出す)。"""
    if summary.get("unreachable"):
        return check_summary_line(summary)  # 「jev: 未到達(…)」を他の道具と同じ文面で出す
    tail = "(--dry-run: 1 件も送っていない)" if summary.get("dry_run") else ""
    return (f"巡 {summary['n_rounds']}、指摘 {summary['n_findings']} 件"
            f"(要求 {summary['n_requests']} / 見込み {summary['n_requests_expected']})、"
            f"最長の連鎖 {summary['longest_chain']} 巡、"
            f"最後の巡で前と同じ {summary['n_same_in_last_round']} 件{tail}")


def cmd_rounds(args) -> int:
    given = [Path(p) for p in args.files]
    missing = [str(p) for p in given if not p.is_file()]
    if missing:
        print(f"[jev_audit_loop] ファイルが無い: {', '.join(missing)}", file=sys.stderr)
        return 1
    paths, order_differs = order_paths(given, args.order)
    rounds = load_rounds(paths)

    client, unreachable = _client_or_none(args)
    records: list[dict] = []
    links: dict[str, str] = {}
    n_requests = 0
    n_reopened = 0
    n_low_confidence = 0
    # 送る要求の見込み = 2 巡目以降の指摘の数(前の巡に指摘が 1 件も無い巡は送らない)
    n_requests_expected = sum(len(cur["findings"]) for prev, cur in zip(rounds, rounds[1:])
                              if prev["findings"])

    for k, r in enumerate(rounds):
        previous = rounds[k - 1]["findings"] if k > 0 else []
        prev_ids = {p["id"] for p in previous}
        for finding in r["findings"]:
            rec = {
                "kind": "finding",
                "id": finding["id"],
                "round": finding["round"],
                "file": r["file"],
                "index": finding["index"],
                "severity": finding["severity"],
                "lineno": finding["lineno"],
                "head": head(finding["text"], 80),
                "n_previous": len(previous),
                "same_issue_as": None,
                "same_issue_confidence": None,
                "linked_to": None,
                "link_note": None,
                "resolved_then_reopened": None,
                "resolved_then_reopened_flag": None,
                "sent": False,
            }
            if not previous:
                rec["link_note"] = "前の巡が無い" if k == 0 else "前の巡に指摘が 1 件も無い"
                records.append(rec)
                continue
            state = state_for(finding, previous)
            # state の大きさは送る前に分かる(`--dry-run` でも出す。本文は記録しない)
            rec["state_chars"] = len(json.dumps(state, ensure_ascii=False))
            if client is None:
                records.append(rec)
                continue
            resp, err = _send(client, state, questions_for(previous))
            if resp is None:
                unreachable = err
                print(f"[jev_audit_loop] 送信に失敗({finding['id']}): {err}", file=sys.stderr)
                records.append(rec)
                continue
            n_requests += 1
            ans = resp.get("answers") or {}
            same = ans.get("same_issue_as", {})
            conf = same.get("confidence")
            rec["same_issue_as"] = same.get("choice")
            rec["same_issue_confidence"] = None if conf is None else round(float(conf), 4)
            parent, note = linked_id(same.get("choice"), conf, prev_ids)
            rec["linked_to"] = parent
            rec["link_note"] = note
            if note == "低確信(同じとは数えない)":
                n_low_confidence += 1
            if parent:
                links[finding["id"]] = parent
            reop = ans.get("resolved_then_reopened", {}).get("noul")
            if reop is not None:
                rec["resolved_then_reopened"] = round(float(reop), 4)
                rec["resolved_then_reopened_flag"] = bool(float(reop) >= PRESENCE)
                n_reopened += int(rec["resolved_then_reopened_flag"])
            rec["model"] = resp.get("model")
            rec["sent"] = True
            records.append(rec)

    streak, chains = build_chains(rounds, links)
    rows = round_rows(rounds, links, streak)
    records += rows
    multi = sorted([c for c in chains if len(c) >= 2], key=len, reverse=True)
    records += [{"kind": "chain", "length": len(c), "ids": c} for c in multi]

    n_findings = sum(len(r["findings"]) for r in rounds)
    if args.dry_run or n_requests_expected == 0 or n_requests > 0:
        unreachable = None
    summary = {
        "kind": "_summary",
        "command": "rounds",
        "files": [r["file"] for r in rounds],
        "order": args.order,
        "order_differs_from_rnumber": order_differs,
        "n_rounds": len(rounds),
        "n_findings": n_findings,
        "n_requests": n_requests,
        "n_requests_expected": n_requests_expected,
        "n_linked": len(links),
        "n_low_confidence": n_low_confidence,
        "n_resolved_then_reopened": n_reopened,
        "longest_chain": max([len(c) for c in chains], default=0),
        "n_chains_2_or_more": len(multi),
        "n_same_in_last_round": rows[-1]["n_same_as_previous"] if rows else 0,
        "max_state_chars": max([r.get("state_chars") or 0 for r in records
                                if r["kind"] == "finding"], default=0),
        "dry_run": bool(args.dry_run),
        "unreachable": unreachable,
        "model": args.model,
        "thresholds": {"same_confident": SAME_CONFIDENT, "presence": PRESENCE,
                       "previous_head_chars": PREV_HEAD_CHARS},
    }
    name = f"{Path(rounds[0]['file']).stem}__{len(rounds)}rounds" if rounds else "empty"
    out_path = _write_jsonl(Path(args.out), name, records, summary)

    if not args.summary:
        _print_tables(rounds, records, rows, multi, streak, summary, out_path)
    print(summary_line(summary))
    return 0


def _print_tables(rounds, records, rows, chains, streak, summary, out_path: Path) -> None:
    print(f"巡の記録 {summary['n_rounds']} 本(順: "
          + ("引数の順" if summary["order"] == "args" else "ファイル名の r 番号")
          + ")。指摘の切り出しは `jev_audit_eval.split_findings`"
            "(番号 + [止める|直す|聞く|通す]。引用の中を優先)")
    if summary["order_differs_from_rnumber"]:
        print("※ 引数の順とファイル名の r 番号の順が食い違っている"
              "(--order rnumber で r 番号の順にできる)")
    print("【事実のみ】この道具は「同じ指摘が N 巡続いている」を出すだけで、"
          "**打ち切りの判断は規則(L-200)とリード・オーナーが行う**")
    print("")
    if summary["dry_run"]:
        print(f"※ --dry-run: 1 件も送っていないので「前と同じ」「最長」「連鎖」は**測っていない**"
              f"(送る要求の見込み {summary['n_requests_expected']} 件 = 2 巡目以降の指摘の数、"
              f"state の最大 {summary['max_state_chars']} 字)")
    print(f"{'巡':>3}  {'指摘':>4}{'前と同じ':>9}{'新しい':>7}{'最長':>6}  記録")
    for row in rows:
        print(f"{row['round']:>3}  {row['n_findings']:>4}{row['n_same_as_previous']:>9}"
              f"{row['n_new']:>7}{row['longest_streak']:>6}  {row['file']}")
    print("")
    if chains:
        print(f"連鎖({len(chains)} 本。長さ 2 以上):")
        for c in chains:
            print(f"  {len(c)} 巡: " + " → ".join(c))
    else:
        print("連鎖(長さ 2 以上): 0 本")
    reopened = [r for r in records
                if r["kind"] == "finding" and r.get("resolved_then_reopened_flag")]
    print(f"「直したはずのものが戻っている」と読める指摘: {len(reopened)} 件"
          f"(noul >= {PRESENCE})")
    for r in reopened:
        print(f"  {r['id']}  {r['head'][:60]}")
    print(f"(しきい値 same_confident={SAME_CONFIDENT} 未満は「同じ」と数えない。"
          f"低確信 {summary['n_low_confidence']} 件)")
    for r in records:
        if r["kind"] == "finding" and streak.get(r["id"], 0) >= 2:
            print(f"  {r['id']}: 同じ指摘が {streak[r['id']]} 巡続いている"
                  f"(前の巡の {r['linked_to']} と同じ、確信 {r['same_issue_confidence']})")
    print(f"書き出し: {out_path}")


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="監査の巡をまたいで同じ指摘の連鎖を数える(U9。判定はしない)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("rounds", help="巡の記録を古い順に並べて、前の巡との同一性を聞く")
    p1.add_argument("files", nargs="+", help="巡の記録(Markdown / JSON)。引数の順が巡の順")
    p1.add_argument("--order", choices=("args", "rnumber"), default="args",
                    help="巡の順の決め方(既定: 引数の順)")
    p1.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p1.add_argument("--dry-run", action="store_true")
    p1.add_argument("--summary", action="store_true", help="末尾の 1 行だけを出す")
    p1.add_argument("--model", default=DEFAULT_MODEL)
    p1.set_defaults(func=cmd_rounds)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
