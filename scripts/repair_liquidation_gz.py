#!/usr/bin/env python3
"""清算 gzip の gzip メンバ境界破損からの回収(2026-09-12、L-121)。

**読み取り専用。** 入力ファイル(`data/` `paper_logs/` 配下の元データ)は一切
書き換えない・削除しない。開くのは読み取りモードのみ。回収結果は
`--out-dir`(既定 `data/liquidations_repaired/`)へ**別ファイル**として書く。

何を直すか: 旧 `Writer`(`gzip.open(path, "at")` を開いたまま保持)がハードキル
された結果、終端マーカーの無い gzip メンバの直後に、再起動した別プロセスが
新しいメンバのヘッダを継ぎ足した。これを素直に `gzip.open` で読むと、古いメンバの
続きのつもりで新しいメンバのヘッダバイトまで deflate として読み進めてしまい、
`zlib.error: invalid block type` などで**ファイル全体**が読めなくなる。

回収の手順(`bot.research.gz_members` に実装。このスクリプトと
`scripts/intake_ledger.py` のフォールバックで共有):
1. 生バイト列を gzip+deflate のマジック(`\\x1f\\x8b\\x08`)の出現位置で
   **展開する前に**分割する。これで、死んだメンバの範囲に次のメンバの
   ヘッダが混ざることがなくなる。
2. 各断片を個別の展開器で伸ばす。終端マーカーが無い断片は例外にならず、
   そこまでの内容がそのまま返る。
3. 展開できた行のうち、JSON オブジェクトとして読めるものだけを残す
   (書きかけの断片やヘッダの取りこぼしは「捨てた行」として数える)。
4. 残った行を 1 回の `gzip.compress()` で**単一の完結したメンバ**にまとめ、
   出力先へ書く。

Usage:
    python scripts/repair_liquidation_gz.py data/liquidations/*.jsonl.gz
    python scripts/repair_liquidation_gz.py data/liquidations paper_logs/liquidations
    python scripts/repair_liquidation_gz.py --dry-run data/liquidations
    python scripts/repair_liquidation_gz.py --out-dir /tmp/out data/liquidations/x.jsonl.gz

終了コードは、引数そのものが不正な場合(パス未指定など)以外は常に 0。
1 ファイルの読み取り失敗やパス不存在は、その行を報告して次のファイルへ進む。
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO / "data" / "liquidations_repaired"

sys.path.insert(0, str(REPO / "src"))
from bot.research.gz_members import recover_json_lines, is_cleanly_readable  # noqa: E402


def find_inputs(paths: list[str]) -> list[Path]:
    """与えられたパス(ファイル or ディレクトリ)から *.jsonl.gz を集める。
    存在しないパスは later で個別に報告するので、ここでは黙って無視しない
    ように残す(存在チェックは呼び出し側)。"""
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(p.rglob("*.jsonl.gz")))
        else:
            out.append(p)
    # 重複除去(同じファイルが複数の入力経路から来た場合)。順序は保つ。
    seen: set[Path] = set()
    deduped = []
    for p in out:
        rp = p.resolve() if p.exists() else p
        if rp in seen:
            continue
        seen.add(rp)
        deduped.append(p)
    return deduped


def _out_path(path: Path, out_dir: Path) -> Path:
    """出力先のパス。リポジトリ相対のディレクトリ構造(`data/liquidations/...`
    など)を out_dir の下にそのまま再現し、`data/liquidations/x.gz` と
    `paper_logs/liquidations/x.gz` のような同名衝突を避ける。"""
    try:
        rel = path.resolve().relative_to(REPO.resolve())
    except ValueError:
        rel = Path(path.parent.name) / path.name
    return out_dir / rel


def repair_one(path: Path, out_dir: Path, dry_run: bool) -> dict:
    rec: dict = {
        "path": str(path),
        "exists": path.exists(),
        "original_readable": None,
        "members_found": 0,
        "members_complete": 0,
        "lines_recovered": 0,
        "lines_discarded": 0,
        "wrote": None,
        "error": None,
    }
    if not rec["exists"]:
        rec["error"] = "not found"
        return rec
    try:
        data = path.read_bytes()          # 読み取りのみ。書き込み・削除はしない
    except OSError as exc:
        rec["error"] = f"read failed: {exc}"
        return rec

    rec["original_readable"] = is_cleanly_readable(data)

    result = recover_json_lines(data)
    rec["members_found"] = result.members_found
    rec["members_complete"] = result.members_complete
    rec["lines_recovered"] = len(result.lines)
    rec["lines_discarded"] = result.lines_discarded

    if dry_run:
        return rec

    out_path = _out_path(path, out_dir)
    if out_path.resolve() == path.resolve():
        rec["error"] = "refusing to write over the original path"
        return rec
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = ("\n".join(result.lines) + "\n").encode("utf-8") if result.lines else b""
    out_path.write_bytes(gzip.compress(body))   # 単一の完結したメンバ、1回の書き込み
    rec["wrote"] = str(out_path)
    return rec


def print_report(rec: dict) -> None:
    name = Path(rec["path"]).name
    if rec["error"] and not rec["exists"]:
        print(f"{name}: {rec['error']}")
        return
    if rec["error"]:
        print(f"{name}: 読めた内容はあるが書き出せなかった: {rec['error']}")
    readable = "yes" if rec["original_readable"] else "NO"
    print(
        f"{name}: members={rec['members_found']} "
        f"complete={rec['members_complete']} "
        f"recovered={rec['lines_recovered']} "
        f"discarded={rec['lines_discarded']} "
        f"original_readable_as_is={readable}"
        + (f" -> {rec['wrote']}" if rec["wrote"] else "")
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+",
                    help="*.jsonl.gz ファイル、またはそれらを含むディレクトリ")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR),
                    help=f"回収結果の出力先(既定: {DEFAULT_OUT_DIR})")
    ap.add_argument("--dry-run", action="store_true",
                    help="集計だけ表示し、何も書き出さない")
    args = ap.parse_args()

    out_dir = Path(args.out_dir).resolve()
    inputs = find_inputs(args.paths)
    if not inputs:
        print("repair_liquidation_gz: 対象の *.jsonl.gz が見つからない", file=sys.stderr)
        return 0

    total_recovered = 0
    total_discarded = 0
    for p in inputs:
        rec = repair_one(p, out_dir, args.dry_run)
        print_report(rec)
        total_recovered += rec["lines_recovered"] or 0
        total_discarded += rec["lines_discarded"] or 0

    mode = "dry-run(書き出しなし)" if args.dry_run else f"-> {out_dir}"
    print(f"\n{len(inputs)} ファイル、計 {total_recovered} 行回収、"
          f"{total_discarded} 行捨てた。{mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
