#!/usr/bin/env python3
"""共有された清算記録を点検する — オーナーに何も聞かずに状態を知るための道具。

`paper_logs/liquidations/`(オーナー PC からコピーされた共有分)と
`data/liquidations/`(このマシンで走らせた場合)を読み、
**使えるデータかどうか**だけを出す。相場についての判断は一切しない。

読み方に注意が要る: 記録器が走っている最中にコピーされたファイルは
gzip の終端マーカーを持たないので、素直に開くと `EOFError` で落ちるか、
**中身があるのに 0 行に見える**。`bot.research.liquidations` の読み手を使う。

Usage:
    python scripts/liquidation_report.py
    python scripts/liquidation_report.py --dir paper_logs/liquidations
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bot.research.liquidations import read_rows, summarise  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DIRS = [REPO / "paper_logs" / "liquidations", REPO / "data" / "liquidations"]

# 「本物の清算メッセージ」の見分け方。制御メッセージ(購読応答・pong・
# BitMEX の空 partial)を数えないための最小限の判定。
IS_LIQUIDATION = {
    "binance_um": lambda m: m.get("e") == "forceOrder",
    "binance_cm": lambda m: m.get("e") == "forceOrder",
    "bybit": lambda m: str(m.get("topic", "")).startswith(("allLiquidation", "liquidation"))
    and m.get("data"),
    "okx": lambda m: m.get("arg", {}).get("channel") == "liquidation-orders" and m.get("data"),
    "bitmex": lambda m: m.get("table") == "liquidation"
    and m.get("action") in {"insert", "partial", "update"} and m.get("data"),
}


def count_liquidations(venue: str, path: Path) -> tuple[int, int]:
    """(清算メッセージ数, 全メッセージ数)。判定が無い venue は (-1, n)。

    点検ツールなので `strict=False`(破損があっても例外にせず読めた分を使う。
    破損そのものは `summarise()` 側の `truncated`/`error` で報告する)。
    """
    rows = read_rows(path, strict=False).rows
    pred = IS_LIQUIDATION.get(venue)
    if pred is None:
        return -1, len(rows)
    n = 0
    for r in rows:
        raw = r.get("raw")
        if isinstance(raw, dict):
            try:
                if pred(raw):
                    n += 1
            except Exception:  # noqa: BLE001 - 未知の形は清算でないとみなす
                pass
    return n, len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", action="append", default=None,
                    help="読む場所(複数可)。既定は paper_logs/liquidations と data/liquidations")
    ap.add_argument("--gap-sec", type=float, default=900.0,
                    help="この秒数以上メッセージが無い区間を欠測候補として挙げる")
    ap.add_argument("--json", action="store_true", help="機械可読で出す")
    args = ap.parse_args()

    dirs = [Path(d) for d in args.dir] if args.dir else DEFAULT_DIRS
    files = sorted({p for d in dirs if d.exists() for p in d.glob("*.jsonl.gz")})
    if not files:
        print(f"清算ファイルが見つかりません: {[str(d) for d in dirs]}", file=sys.stderr)
        return 1

    report = []
    per_venue: Counter = Counter()
    for path in files:
        s = summarise(path, gap_sec=args.gap_sec)
        liq, total = count_liquidations(s.venue or "", path)
        per_venue[s.venue or "?"] += max(liq, 0)
        report.append({
            "file": path.name, "venue": s.venue, "messages": s.rows,
            "liquidations": liq, "span_utc": s.span_utc,
            "bad_lines": s.bad_lines, "truncated_tail": s.truncated_tail,
            "truncated": s.truncated, "error": s.error,
            "backwards": s.backwards, "duplicate_recv_us": s.duplicate_recv_us,
            "gaps": [{"from_us": a, "sec": b} for a, b in s.gaps],
        })

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"{'file':34s} {'msgs':>7s} {'清算':>6s}  期間 (UTC)")
    for r in report:
        span = f"{r['span_utc'][0]} 〜 {r['span_utc'][1]}" if r["span_utc"] else "-"
        liq = "?" if r["liquidations"] < 0 else str(r["liquidations"])
        print(f"{r['file']:34s} {r['messages']:7d} {liq:>6s}  {span}")

    print("\n--- 健全性 ---")
    for r in report:
        notes = []
        if r["truncated"]:
            notes.append(f"**gzip 破損で読み切れていない({r['error']})**")
        if r["bad_lines"]:
            notes.append(f"**途中の壊れた行 {r['bad_lines']}**")
        if r["backwards"]:
            notes.append(f"**時刻の逆行 {r['backwards']}**")
        if r["duplicate_recv_us"]:
            notes.append(f"**recv_us 重複 {r['duplicate_recv_us']}**(二重書き込みの疑い)")
        if r["gaps"]:
            notes.append(f"欠測候補 {len(r['gaps'])} 件(最長 {max(g['sec'] for g in r['gaps'])}s)")
        if r["truncated_tail"]:
            notes.append("末尾が書きかけ(記録中のコピー = 正常)")
        print(f"  {r['file']:34s} {' / '.join(notes) if notes else 'ok'}")

    print("\n--- 取引所ごとの清算件数 ---")
    for v, n in sorted(per_venue.items()):
        print(f"  {v:12s} {n}")
    print("\n※ 欠測候補は「記録が止まっていた」証拠ではない(静かな時間帯かもしれない)。"
          "\n  どちらかは logs/liquidations.out.log の接続/切断でしか決まらない。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
