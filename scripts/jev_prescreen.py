#!/usr/bin/env python3
"""成果物 1 件を Jev の原則スクリーン(P1〜P16)+ 危険度分類に掛ける(前段)。

使い方:
  python3 scripts/jev_prescreen.py <成果物.md> --model <版付きID> [--out PATH] [--dry-run]

`--dry-run` は鍵が無くても動く(送らずに質問と文字数だけ出す)。
**監査役の判定そのものを置き換えない**(`CLAUDE.md` §5.0 の 2)。前段の分類結果を
`owner-audit` の手順に足す材料として使う。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.jev.client import JevClient, JevError  # noqa: E402
from scripts.jev.redact import assert_clean, redact  # noqa: E402
from scripts.jev.schemas import principle_screen, risk_route  # noqa: E402

MAX_CHARS = 60_000
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "prescreen"


def build_questions() -> dict:
    q = {}
    q.update(principle_screen())
    q.update(risk_route())
    return q


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact", help="評価する成果物(Markdown 等のテキストファイル)")
    ap.add_argument("--model", required=False, help="版付き ID(--dry-run 以外は必須)")
    ap.add_argument("--out", help="出力先(既定: data/jev/prescreen/<sha256先頭16>.json)")
    ap.add_argument("--dry-run", action="store_true", help="送らずに質問と文字数だけ出す")
    a = ap.parse_args()

    path = Path(a.artifact)
    if not path.is_file():
        print(f"[jev_prescreen] 成果物が見つからない: {path}", file=sys.stderr)
        return 2

    raw = path.read_text(encoding="utf-8", errors="replace")
    truncated = False
    if len(raw) > MAX_CHARS:
        raw = raw[:MAX_CHARS]
        truncated = True

    text, redaction_hits = redact(raw)
    assert_clean(text)

    questions = build_questions()

    if a.dry_run:
        out = {
            "state_chars": len(text),
            "redaction_hits": redaction_hits,
            "questions": list(questions.keys()),
            "truncated": truncated,
        }
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    if not a.model:
        print("[jev_prescreen] --dry-run 以外では --model が必須", file=sys.stderr)
        return 2

    t0 = time.monotonic()
    try:
        client = JevClient(model=a.model)
        resp = client.evaluate(state=text, questions=questions)
    except JevError as e:
        print(f"[jev_prescreen] Jev 呼び出しに失敗: {e}", file=sys.stderr)
        return 1
    latency_ms = round((time.monotonic() - t0) * 1000, 1)

    sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    out_path = Path(a.out) if a.out else DEFAULT_OUT_DIR / f"{sha256[:16]}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "artifact": str(path),
        "sha256": sha256,
        "model": resp.get("model"),
        "answers": resp.get("answers"),
        "usage": resp.get("usage"),
        "latency_ms": latency_ms,
        "redaction_hits": redaction_hits,
        "truncated": truncated,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[jev_prescreen] 書いた: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
