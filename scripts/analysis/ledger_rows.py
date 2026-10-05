#!/usr/bin/env python3
"""行の定義ファイルから知見台帳(`docs/RESEARCH/FINDINGS_LEDGER.md`)に観察の行を足す道具。

目的: 分析の文書の D9b で挙げた観察を、台帳に手で写さず、試験つきの道具で足す。足した後の台帳に
台帳の検査(`scripts/check_findings_ledger.py`)を当て、問題が 1 件でもあれば台帳を書き換えない。
経緯: オーナーの指示 L-705「**今日の分析方法(分析スキル・アドバイザーfableとの2人作業・なぜ分解と台帳記入)を
再利用可能な仕組み化してほしい。要件を詰めたいので案を出してください。**」と L-706「**1.y 2.y だが、
アドバイザー含め渡す情報はどうする？今回は何を渡した？ 3.y**」。案は
`docs/DISCUSSIONS/2026-10-05_analysis_mechanism/PROPOSAL.md` §4 案 A の 3(作業用の一時置き場の
`ledger_add.py` を repo に移し、試験を付ける)。

    python3 scripts/analysis/ledger_rows.py <行の定義の .py> [--ledger PATH] [--date YYYY-MM-DD]

行の定義ファイル = 次の名前を持つ Python のファイル(実行して読む):
- ROWS: タプルの並び。1 つのタプルが 1 行で、順は
  (K 番号, 見出し, 対象, 観察, 出所, 大きさ, 否定を含む, 渡す先, 次の問い, なぜの仮説)
- SCOPE: 欄「射程」(全行で同じ)
- PRED: 欄「予言」(全行で同じ)
- DATA: 欄「確かめのデータ」(全行で同じ)
欄「測った日」は --date(既定は今日の日本時間の日付)。「確かさ: 未監査」「監査: なし」「状態: 開いている」は固定。

止めるもの(台帳は書き換えない。終了コード 1):
- 定義ファイルに ROWS・SCOPE・PRED・DATA が無い、タプルの長さが 10 でない、値が文字列でない、値に改行がある
  (改行があると台帳の `- 欄: 値` の 1 行の形が壊れ、検査が見逃す)
- K 番号の形が `K-数字 3 桁以上` でない、定義ファイルの中で同じ K 番号が 2 回ある、台帳に既にある
  (台帳にあるかは検査と同じ読み方で見る。`## 書式` の囲み ``` の中の見本は数えない)
- 台帳に `## カード` の見出しが無い(行は `## カード` の手前に足す)
- 足した後の台帳全体に台帳の検査が問題を 1 件でも出す。足す前から台帳にある問題でも止まる
  (台帳の検査が問題 0 の台帳にしか足さない)

書き方: 足した後の台帳の文を作って先に検査し、問題 0 のときだけ書く(一時ファイルに書いて置き換える)。
書いた後にファイルを読み直してもう一度検査し、問題があれば元の中身に戻して止める。
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import runpy
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = REPO / "docs" / "RESEARCH" / "FINDINGS_LEDGER.md"
CARD_MARK = "\n## カード\n"
ROW_LEN = 10
KID = re.compile(r"K-\d{3,}")

_spec = importlib.util.spec_from_file_location("check_findings_ledger", REPO / "scripts" / "check_findings_ledger.py")
cfl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfl)


class Refused(Exception):
    """足さずに止める理由。"""


def today_jst() -> str:
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")


def load_rows(path: str) -> dict:
    d = runpy.run_path(path)
    missing = [k for k in ("ROWS", "SCOPE", "PRED", "DATA") if k not in d]
    if missing:
        raise Refused(f"定義ファイルに {', '.join(missing)} が無い")
    for k in ("SCOPE", "PRED", "DATA"):
        if not isinstance(d[k], str) or "\n" in d[k]:
            raise Refused(f"{k} が 1 行の文字列でない")
    rows = list(d["ROWS"])
    if not rows:
        raise Refused("ROWS が空")
    for i, r in enumerate(rows, 1):
        if not isinstance(r, tuple) or len(r) != ROW_LEN:
            raise Refused(f"ROWS の {i} 番目が長さ {ROW_LEN} のタプルでない")
        for j, v in enumerate(r):
            if not isinstance(v, str):
                raise Refused(f"ROWS の {i} 番目の {j + 1} 個目が文字列でない")
            if "\n" in v:
                raise Refused(f"ROWS の {i} 番目({r[0]})の {j + 1} 個目に改行がある")
        if not KID.fullmatch(r[0]):
            raise Refused(f"ROWS の {i} 番目の K 番号「{r[0]}」が K-数字 3 桁以上の形でない")
    return {"ROWS": rows, "SCOPE": d["SCOPE"], "PRED": d["PRED"], "DATA": d["DATA"]}


def block(row: tuple, scope: str, pred: str, data: str, measured: str) -> str:
    kid, head, tgt, obs, src, size, neg, to, nq, why = row
    return "\n".join([
        f"### {kid} {head}",
        f"- 観察: {obs}",
        f"- 対象: {tgt}",
        f"- 出所: {src}",
        f"- 測った日: {measured}",
        f"- 射程: {scope}",
        f"- 大きさ: {size}",
        "- 確かさ: 未監査",
        "- 監査: なし",
        f"- 否定を含む: {neg}",
        f"- 渡す先: {to}",
        f"- 次の問い: {nq}",
        f"- なぜの仮説: {why}",
        f"- 予言: {pred}",
        f"- 確かめのデータ: {data}",
        "- 状態: 開いている",
        "",
    ])


def add_rows(ledger_text: str, d: dict, measured: str) -> str:
    """足した後の台帳の文を返す。止める理由があれば Refused。検査はしない。"""
    try:
        date.fromisoformat(measured)
    except ValueError:
        raise Refused(f"測った日「{measured}」が YYYY-MM-DD でない")
    obs, _, _ = cfl._parse(ledger_text)
    seen: set[str] = set()
    for r in d["ROWS"]:
        if r[0] in seen:
            raise Refused(f"{r[0]} が定義ファイルの中に 2 回ある")
        seen.add(r[0])
        if r[0] in obs:
            raise Refused(f"{r[0]} は台帳に既にある")
    if CARD_MARK not in ledger_text:
        raise Refused("台帳に「## カード」の見出しが無い(行はその手前に足す)")
    blocks = [block(r, d["SCOPE"], d["PRED"], d["DATA"], measured) for r in d["ROWS"]]
    return ledger_text.replace(CARD_MARK, "\n" + "\n".join(blocks) + CARD_MARK, 1)


def _write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".ledger_rows.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv: list[str] | None = None, repo: Path = REPO) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rows", help="行の定義の .py(ROWS・SCOPE・PRED・DATA)")
    ap.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    ap.add_argument("--date", default=None, help="欄「測った日」(既定は今日の日本時間の日付)")
    a = ap.parse_args(argv)
    measured = a.date or today_jst()
    with open(a.ledger, encoding="utf-8", newline="") as fh:
        original = fh.read()
    try:
        d = load_rows(a.rows)
        new = add_rows(original, d, measured)
    except Refused as e:
        print(f"止めた(台帳は変えていない): {e}", file=sys.stderr)
        return 1
    errs = cfl.check_ledger_text(new, repo=repo)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        print(f"止めた(台帳は変えていない): 足した後の台帳に検査の問題 {len(errs)}", file=sys.stderr)
        return 1
    _write(a.ledger, new)
    with open(a.ledger, encoding="utf-8", newline="") as fh:
        written = fh.read()
    errs = cfl.check_ledger_text(written, repo=repo)
    if written != new or errs:
        _write(a.ledger, original)
        for e in errs:
            print(e, file=sys.stderr)
        print("止めた: 書いた後の読み直しが合わない・検査に問題があるので、元の中身に戻した", file=sys.stderr)
        return 1
    obs, cards, _ = cfl._parse(written)
    print("足した:", ", ".join(r[0] for r in d["ROWS"]))
    print(f"観察の行 {len(obs)}・カードの節 {len(cards)}・問題 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
