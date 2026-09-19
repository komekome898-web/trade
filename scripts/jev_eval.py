#!/usr/bin/env python3
"""Jev の私的評価集合(`docs/AUDITOR/before/` × `answers/`)を作り、動かし、採点する。

サブコマンド:
  build  <成果物一覧を突き合わせて labels_template.csv / manifest.json を書く>
  run    <before/ の各ファイルを prescreen と同じ処理に掛けて predictions.jsonl に書く>
  score  <labels.csv と predictions.jsonl を突き合わせて原則ごとの捕捉率を表にする>

**score の結果は `docs/` に書かない**(`docs/DISCUSSIONS/2026-09-19_jev_adoption_review.md` §7、
MCA §2.3(f))。出力先は `data/jev/eval/`(gitignore 済)。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.jev.client import JevClient, JevError  # noqa: E402
from scripts.jev.redact import assert_clean, redact  # noqa: E402
from scripts.jev.schemas import principle_screen, risk_route  # noqa: E402

BEFORE_DIR = REPO / "docs" / "AUDITOR" / "before"
ANSWERS_DIR = REPO / "docs" / "AUDITOR" / "answers"
MAX_CHARS = 60_000
PRINCIPLE_IDS = [f"P{n}" for n in range(1, 17)]


def _corresponding_answer(before_file: Path) -> Path | None:
    """before/ と answers/ の対応は**同名ファイル**で付ける(両ディレクトリの実物を見て決めた。
    23 件中 22 件が同名で揃っており、`HYGIENE_2026-09-11.md` だけ answers/ に対応が無い)。"""
    cand = ANSWERS_DIR / before_file.name
    return cand if cand.is_file() else None


def cmd_build(args) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    before_files = sorted(BEFORE_DIR.glob("*.md"))
    manifest: dict[str, dict] = {}
    rows = []
    n_matched = 0
    for bf in before_files:
        text = bf.read_text(encoding="utf-8", errors="replace")
        sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        ans = _corresponding_answer(bf)
        has_answer = ans is not None
        if has_answer:
            n_matched += 1
        manifest[bf.name] = {
            "sha256": sha256,
            "chars": len(text),
            "answers_path": str(ans.relative_to(REPO)) if ans else None,
        }
        rows.append({"file": bf.name, "has_answer": int(has_answer),
                      **{p: "" for p in PRINCIPLE_IDS}})

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    labels_path = out_dir / "labels_template.csv"
    with labels_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "has_answer", *PRINCIPLE_IDS])
        w.writeheader()
        for row in rows:
            w.writerow(row)

    print(f"[jev_eval build] before/ {len(before_files)} 件、対応あり {n_matched} 件、"
          f"対応なし {len(before_files) - n_matched} 件")
    print(f"[jev_eval build] 書いた: {manifest_path}")
    print(f"[jev_eval build] 書いた: {labels_path}")
    return 0


def _build_questions() -> dict:
    q = {}
    q.update(principle_screen())
    q.update(risk_route())
    return q


def cmd_run(args) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / "predictions.jsonl"

    before_files = sorted(BEFORE_DIR.glob("*.md"))
    questions = _build_questions()

    client = None
    if not args.dry_run:
        try:
            client = JevClient(model=args.model)
        except JevError as e:
            print(f"[jev_eval run] Jev クライアントを作れない: {e}", file=sys.stderr)
            return 1

    with pred_path.open("w", encoding="utf-8") as fh:
        for bf in before_files:
            raw = bf.read_text(encoding="utf-8", errors="replace")
            truncated = False
            if len(raw) > MAX_CHARS:
                raw = raw[:MAX_CHARS]
                truncated = True
            text, redaction_hits = redact(raw)
            assert_clean(text)
            sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()

            if args.dry_run:
                fh.write(json.dumps({
                    "file": bf.name, "sha256": sha256,
                    "n_questions": len(questions), "state_chars": len(text),
                    "truncated": truncated,
                }, ensure_ascii=False) + "\n")
                continue

            t0 = time.monotonic()
            try:
                resp = client.evaluate(state=text, questions=questions)
            except JevError as e:
                print(f"[jev_eval run] {bf.name} の評価に失敗: {e}", file=sys.stderr)
                continue
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            fh.write(json.dumps({
                "file": bf.name, "sha256": sha256,
                "model": resp.get("model"), "answers": resp.get("answers"),
                "usage": resp.get("usage"), "latency_ms": latency_ms,
                "redaction_hits": redaction_hits, "truncated": truncated,
            }, ensure_ascii=False) + "\n")

    print(f"[jev_eval run] {len(before_files)} 件処理。書いた: {pred_path}")
    return 0


def _load_labels(path: Path) -> dict[str, dict]:
    out = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["file"]] = row
    return out


def _load_predictions(path: Path) -> dict[str, dict]:
    out = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out[d["file"]] = d
    return out


def cmd_score(args) -> int:
    labels = _load_labels(Path(args.labels))
    preds = _load_predictions(Path(args.pred))
    threshold = args.threshold

    print(f"{'原則':<6}{'該当あり':>8}{'検出(TP)':>10}{'見逃し(FN)':>12}"
          f"{'誤検出(FP)':>12}{'見逃し率':>10}")
    for pid in PRINCIPLE_IDS:
        n_pos = tp = fn = fp = 0
        for fname, label_row in labels.items():
            raw_label = (label_row.get(pid) or "").strip()
            if raw_label == "":
                continue  # ラベル未記入は集計に含めない
            label = int(raw_label)
            pred_row = preds.get(fname)
            if pred_row is None:
                continue
            answers = pred_row.get("answers") or {}
            ans = answers.get(pid) or {}
            score = ans.get("noul")
            pred = 1 if (score is not None and score >= threshold) else 0
            if label == 1:
                n_pos += 1
                if pred == 1:
                    tp += 1
                else:
                    fn += 1
            else:
                if pred == 1:
                    fp += 1
        miss_rate = f"{fn / n_pos:.3f}" if n_pos else "-"
        print(f"{pid:<6}{n_pos:>8}{tp:>10}{fn:>12}{fp:>12}{miss_rate:>10}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("--out", default=str(REPO / "data" / "jev" / "eval"))
    p_build.set_defaults(func=cmd_build)

    p_run = sub.add_parser("run")
    p_run.add_argument("--model")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--out", default=str(REPO / "data" / "jev" / "eval"))
    p_run.set_defaults(func=cmd_run)

    p_score = sub.add_parser("score")
    p_score.add_argument("--labels", required=True)
    p_score.add_argument("--pred", required=True)
    p_score.add_argument("--threshold", type=float, default=0.5)
    p_score.set_defaults(func=cmd_score)

    a = ap.parse_args()
    if a.cmd == "run" and not a.dry_run and not a.model:
        ap.error("run には --model か --dry-run のどちらかが要る")
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
