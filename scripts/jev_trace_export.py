#!/usr/bin/env python3
"""会話の記録(JSONL)から、Jev に読ませられる「秘密情報を落とした道具呼び出しの列」を作る。

道具呼び出し・結果の取り出し方は `scripts/trace_metrics.py` と同じ解釈を再利用する
(`_text_of` / `_has_tool_result` / `NOT_OWNER` を import する)。

使い方:
  python3 scripts/jev_trace_export.py <会話の記録.jsonl> --out data/jev/trace/<名前>.jsonl
  python3 scripts/jev_trace_export.py <会話の記録.jsonl> --out data/jev/trace/<名前>.jsonl \
      --review --model <版付きID>

`--review` を付けない限り Jev へは何も送らない(影。既存の挙動は変えない)。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.trace_metrics import NOT_OWNER, _has_tool_result, _text_of  # noqa: E402
from scripts.jev.client import JevClient, JevError  # noqa: E402
from scripts.jev.redact import assert_clean, redact  # noqa: E402
from scripts.jev.schemas import trace_review  # noqa: E402

ARGS_MAX = 300
RESULT_MAX = 200
TEXT_MAX = 2000


def _redact_head(text: str, limit: int) -> str:
    red, _ = redact(text)
    return red[:limit]


def _result_text(content) -> str:
    """user メッセージの tool_result ブロックから、表示用のテキストを取り出す。"""
    if not isinstance(content, list):
        return ""
    parts = []
    for b in content:
        if not isinstance(b, dict) or b.get("type") != "tool_result":
            continue
        c = b.get("content")
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):
            for item in c:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
    return "\n".join(parts)


def extract_events(path: Path) -> list[dict]:
    """1 行 1 事象のイベント列を作る。手(move)の境界は user_text で分かる。"""
    events: list[dict] = []
    i = 0
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            msg = d.get("message") or {}
            role = msg.get("role")
            content = msg.get("content")

            if role == "user":
                if _has_tool_result(content):
                    rtext = _result_text(content)
                    if rtext.strip():
                        events.append({
                            "i": i, "kind": "tool_result",
                            "result_head": _redact_head(rtext, RESULT_MAX),
                        })
                        i += 1
                    continue
                text = _text_of(content)
                if text and not text.lstrip().startswith(NOT_OWNER):
                    events.append({
                        "i": i, "kind": "user_text",
                        "text": _redact_head(text, TEXT_MAX),
                    })
                    i += 1
                continue

            if role != "assistant":
                continue

            text = _text_of(content)
            if text.strip():
                events.append({
                    "i": i, "kind": "assistant_text",
                    "text": _redact_head(text, TEXT_MAX),
                })
                i += 1

            for b in (content or []):
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                name = b.get("name", "")
                inp = b.get("input") or {}
                args_json = json.dumps(inp, ensure_ascii=False)
                events.append({
                    "i": i, "kind": "tool_call", "tool": name,
                    "args_summary": _redact_head(args_json, ARGS_MAX),
                })
                i += 1

    return events


def split_moves(events: list[dict]) -> list[list[dict]]:
    """user_text で区切って「手」の列を作る(trace_metrics の move 分割と同じ考え方)。"""
    moves: list[list[dict]] = []
    cur: list[dict] = []
    for ev in events:
        if ev["kind"] == "user_text":
            if cur:
                moves.append(cur)
            cur = [ev]
        else:
            if not cur:
                cur = []
            cur.append(ev)
    if cur:
        moves.append(cur)
    return moves


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record", help="会話の記録(JSONL)")
    ap.add_argument("--out", required=True, help="出力先 JSONL")
    ap.add_argument("--review", action="store_true", help="手ごとに trace_review を送る(影)")
    ap.add_argument("--model", help="--review のときは必須(版付き ID)")
    a = ap.parse_args()

    record_path = Path(a.record)
    if not record_path.is_file():
        print(f"[jev_trace_export] 記録が見つからない: {record_path}", file=sys.stderr)
        return 2

    events = extract_events(record_path)

    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"[jev_trace_export] 事象 {len(events)} 件を書いた: {out_path}")

    if not a.review:
        return 0

    if not a.model:
        print("[jev_trace_export] --review には --model が必須", file=sys.stderr)
        return 2

    try:
        client = JevClient(model=a.model)
    except JevError as e:
        print(f"[jev_trace_export] Jev クライアントを作れない: {e}", file=sys.stderr)
        return 1

    moves = split_moves(events)
    review_path = out_path.with_name(out_path.stem + "_review" + out_path.suffix)
    questions = trace_review()
    with review_path.open("w", encoding="utf-8") as fh:
        for idx, move in enumerate(moves, start=1):
            state_json = json.dumps(move, ensure_ascii=False)
            assert_clean(state_json)  # 送信直前の最終検査(二重に確かめる)
            try:
                resp = client.evaluate(state=move, questions=questions)
            except JevError as e:
                print(f"[jev_trace_export] 手 {idx} の評価に失敗: {e}", file=sys.stderr)
                continue
            fh.write(json.dumps({
                "move": idx,
                "model": resp.get("model"),
                "answers": resp.get("answers"),
                "usage": resp.get("usage"),
            }, ensure_ascii=False) + "\n")
    print(f"[jev_trace_export] 手 {len(moves)} 件のレビューを書いた: {review_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
