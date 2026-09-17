#!/usr/bin/env python3
"""`docs/DATA.md`(データ登録簿)と実物の食い違いを機械で数える。**読み取り専用**。

オーナー決定 L-190(2026-09-17)。案の全文は
`docs/PHASE2/O3C/DATA_COLLECTION_2026-09-17.md` §C(3)(案 A・案 C)。
このスクリプトは**何も書き換えない**(`--json` で出力ファイルを 1 個作るだけ)。

出す食い違いは 4 つ。

案 C(相互参照)
  (i)   `backtest_data/` 直下の単位のうち、`docs/DATA.md` の「所在」列の
        どの行にもパスとして現れないもの(= 台帳に行が無い単位)。
        単位の定義は `scripts/verify_snapshots.py: discover_units` に合わせる
        (各サブディレクトリ + 直下のファイル。直下ファイルの塊だけは、台帳が
        ファイル名で書いているので 1 ファイル = 1 単位に開く)。
  (ii)  「所在」列に書かれたローカルパス(バッククォート内で
        `backtest_data/` `data/` `paper_logs/` で始まるもの)が実在しない行。
        URL・オーナー PC の `data\\...` 形式・他のディレクトリは対象外。
        `*` `?` `[...]` を含むパスは glob として扱い、1 個でも当たれば実在とみなす。
  (iii) 受領台帳(`INTAKE_latest.json`)に無い `backtest_data/` 配下のファイルを
        単位ごとに数える(= `intake_ledger.py` を経由せずに置かれたファイル)。
        台帳は `paper_logs/` 側と `data/` 側の**新しい方**を使い、どちらを
        使ったかを出力に書く(`bot.monitoring.gates.shared_or_local` と同じ考え方)。

案 A(鮮度)
  (iv)  「最終確認日」列が `--max-age-days`(既定 14)より古い行。

表の読み方: ヘッダ行が
`| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |`
の表だけを案 A の対象にする。ヘッダの違う表(§0 の仕組み表・§6・§8・§9 など)は
**飛ばして、飛ばした表の行番号を出力に書く**。(ii) は「所在」列さえあれば見る。
セル数がヘッダと合わない行は飛ばし、その行番号も出力に書く(実物の表は節ごとに
形が揺れているので、パーサは寛容にして落ちないことを優先する)。

終了コード: 食い違いがあっても **0**(`deploy/fetch_all.bat` の後続処理を止めない。
`verify_snapshots.py` の非ゼロ終了を bat 側で無視しているのと同じ方針)。
`--strict` を付けたときだけ、食い違いがあれば 1 を返す。

Usage:
    python scripts/check_data_ledger.py
    python scripts/check_data_ledger.py --max-age-days 7
    python scripts/check_data_ledger.py --json data/LEDGER_CHECK.json
    python scripts/check_data_ledger.py --strict
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import verify_snapshots as vs  # noqa: E402 -- discover_units の定義を共有する

# 案 A を当てる表のヘッダ(この並びのものだけ見る)
STANDARD_HEADER = ["資産", "所在", "範囲", "状態", "最終確認日",
                   "プローブのログ", "使った単位"]

# 「所在」列から拾うローカルパスの接頭辞
LOCAL_PREFIXES = ("backtest_data/", "data/", "paper_logs/")

GLOB_CHARS = set("*?[")
DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
BACKTICK_RE = re.compile(r"`([^`]+)`")


# --------------------------------------------------------------------------
# docs/DATA.md のパーサ(寛容に。落ちないことを優先する)
# --------------------------------------------------------------------------

def _cells(line: str) -> list[str]:
    """`| a | b |` -> ["a", "b"]。

    **バッククォートの中の `|` ではセルを割らない。**`docs/DATA.md:96` は
    所在のセルに `` `ls ... | wc -l` `` を含んでいて、素朴に割ると 8 セルになり
    行ごと落ちる(= その単位が「台帳に行が無い」と誤検出される)。ここは
    表の見た目ではなく相互参照が目的なので、書いてあるとおりに読む。
    """
    s = line.strip()
    if not s.startswith("|"):
        return []
    inner = s[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    cells: list[str] = []
    buf: list[str] = []
    in_code = False
    for ch in inner:
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
        elif ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    cells.append("".join(buf).strip())
    return cells


def _is_separator(line: str) -> bool:
    cs = _cells(line)
    return bool(cs) and all(re.fullmatch(r":?-{2,}:?", c) for c in cs)


def _norm_header(cell: str) -> str:
    return cell.replace("*", "").strip()


class Table:
    """1 つの Markdown 表。行番号は 1 始まり。"""

    def __init__(self, header_lineno: int, header: list[str]) -> None:
        self.header_lineno = header_lineno
        self.header = [_norm_header(h) for h in header]
        self.rows: list[tuple[int, list[str]]] = []      # (行番号, セル)
        self.bad_rows: list[int] = []                    # セル数が合わない行

    @property
    def is_standard(self) -> bool:
        return self.header == STANDARD_HEADER

    def col(self, name: str) -> Optional[int]:
        try:
            return self.header.index(name)
        except ValueError:
            return None


def parse_tables(text: str) -> list[Table]:
    """Markdown 本文から表を拾う。ヘッダ行 + 区切り行 + 本文行 の並びだけ表と見る。"""
    lines = text.splitlines()
    tables: list[Table] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|") and i + 1 < len(lines) and _is_separator(lines[i + 1]):
            table = Table(i + 1, _cells(line))
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cs = _cells(lines[i])
                if _is_separator(lines[i]):
                    pass  # 区切りが二重にある表があっても落ちない
                elif len(cs) != len(table.header):
                    table.bad_rows.append(i + 1)
                else:
                    table.rows.append((i + 1, cs))
                i += 1
            tables.append(table)
            continue
        i += 1
    return tables


def local_paths_in(cell: str) -> list[str]:
    """セルのバッククォート内から、ローカルパスらしいものだけ取り出す。"""
    out = []
    for span in BACKTICK_RE.findall(cell):
        s = span.strip()
        if s.startswith(LOCAL_PREFIXES):
            out.append(s)
    return out


def path_exists(root: Path, rel: str) -> bool:
    """`rel` が実在するか。glob 文字を含むなら 1 個でも当たれば実在とみなす。"""
    rel = rel.rstrip("/")
    if not rel:
        return False
    if any(ch in GLOB_CHARS for ch in rel):
        try:
            return any(True for _ in root.glob(rel))
        except (ValueError, OSError):
            return False
    return (root / rel).exists()


# --------------------------------------------------------------------------
# 単位の列挙(verify_snapshots.discover_units と同じ定義)
# --------------------------------------------------------------------------

def list_units(bt_root: Path) -> list[tuple[str, list[Path]]]:
    """(単位名, その単位のファイル) の一覧。

    `verify_snapshots.discover_units` をそのまま呼ぶ。ただし「直下ファイルを
    まとめた 1 単位」だけは、台帳の「所在」列がファイル名で書かれているので
    1 ファイル = 1 単位に開く。
    """
    if not bt_root.is_dir():
        return []
    out: list[tuple[str, list[Path]]] = []
    for unit_dir, _label, files in vs.discover_units(bt_root):
        if unit_dir == bt_root:
            for f in files:
                out.append((f.name, [f]))
        else:
            out.append((unit_dir.relative_to(bt_root).as_posix(), files))
    return sorted(out)


def mentioned_units(root: Path, location_cells: list[str]) -> set[str]:
    """「所在」列に現れる `backtest_data/` の単位名の集合。

    glob(`backtest_data/qa_known_answer*_2026090[5-7]*/` など)は実物へ
    展開してから単位名を取る。素の文字列としての一致も見る。
    """
    named: set[str] = set()
    bt_root = root / "backtest_data"
    for cell in location_cells:
        for rel in local_paths_in(cell):
            if not rel.startswith("backtest_data/"):
                continue
            tail = rel[len("backtest_data/"):].strip("/")
            if not tail:
                continue
            first = tail.split("/", 1)[0]
            if any(ch in GLOB_CHARS for ch in first):
                if bt_root.is_dir():
                    try:
                        for hit in bt_root.glob(first):
                            named.add(hit.name)
                    except (ValueError, OSError):
                        pass
            else:
                named.add(first)
    return named


# --------------------------------------------------------------------------
# 受領台帳
# --------------------------------------------------------------------------

def pick_intake_ledger(root: Path) -> tuple[Optional[Path], str]:
    """使う `INTAKE_latest.json` を決める。両方あれば mtime の新しい方。"""
    shared = root / "paper_logs" / "INTAKE_latest.json"
    local = root / "data" / "INTAKE_latest.json"
    if shared.exists() and local.exists():
        if shared.stat().st_mtime >= local.stat().st_mtime:
            return shared, "両方あり、新しい paper_logs/ 側を使った"
        return local, "両方あり、新しい data/ 側を使った"
    if shared.exists():
        return shared, "paper_logs/ 側のみ"
    if local.exists():
        return local, "data/ 側のみ"
    return None, "受領台帳が見つからない(この検査は飛ばした)"


def load_ledger_paths(path: Optional[Path]) -> tuple[set[str], str]:
    if path is None:
        return set(), "未読込"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return set(), f"読めない: {type(exc).__name__}: {exc}"
    if isinstance(data, dict):
        return set(data.keys()), "読込済"
    if isinstance(data, list):     # 形が変わっても落ちない
        keys = {d.get("path") for d in data if isinstance(d, dict) and d.get("path")}
        return keys, "読込済(リスト形式)"
    return set(), f"想定外の形式: {type(data).__name__}"


# --------------------------------------------------------------------------
# 本体
# --------------------------------------------------------------------------

def run(root: Path, max_age_days: int, today: date) -> dict[str, Any]:
    data_md = root / "docs" / "DATA.md"
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_md": "docs/DATA.md",
        "max_age_days": max_age_days,
        "today": today.isoformat(),
        "skipped_tables": [],
        "malformed_rows": [],
        "units_without_ledger_row": [],
        "missing_paths": [],
        "files_not_in_intake": [],
        "intake_ledger": {},
        "stale_rows": [],
        "undated_rows": [],
    }
    if not data_md.exists():
        report["error"] = "docs/DATA.md が無い"
        report["ok"] = False
        return report

    tables = parse_tables(data_md.read_text(encoding="utf-8"))

    location_cells: list[str] = []
    for t in tables:
        report["malformed_rows"].extend(
            {"line": ln, "table_header_line": t.header_lineno} for ln in t.bad_rows)

        loc = t.col("所在")
        asset = t.col("資産")
        if loc is not None:
            for lineno, cells in t.rows:
                location_cells.append(cells[loc])
                for rel in local_paths_in(cells[loc]):
                    if not path_exists(root, rel):
                        report["missing_paths"].append({
                            "line": lineno,
                            "asset": cells[asset] if asset is not None else "",
                            "path": rel,
                        })

        # --- 案 A: 鮮度。ヘッダが標準形の表だけ ---
        if not t.is_standard:
            report["skipped_tables"].append({
                "header_line": t.header_lineno,
                "header": " | ".join(t.header),
                "row_count": len(t.rows),
            })
            continue
        last_col = t.col("最終確認日")
        for lineno, cells in t.rows:
            raw = cells[last_col]
            m = DATE_RE.search(raw)
            if m is None:
                report["undated_rows"].append({
                    "line": lineno,
                    "asset": cells[asset] if asset is not None else "",
                    "cell": raw,
                })
                continue
            try:
                seen = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                report["undated_rows"].append({
                    "line": lineno,
                    "asset": cells[asset] if asset is not None else "",
                    "cell": raw,
                })
                continue
            age = (today - seen).days
            if age > max_age_days:
                report["stale_rows"].append({
                    "line": lineno,
                    "asset": cells[asset] if asset is not None else "",
                    "last_checked": seen.isoformat(),
                    "age_days": age,
                })

    # --- 案 C (i): 台帳に行が無い単位 ---
    bt_root = root / "backtest_data"
    units = list_units(bt_root)
    named = mentioned_units(root, location_cells)
    joined = "\n".join(location_cells)
    for unit, files in units:
        if unit in named:
            continue
        if f"backtest_data/{unit}" in joined:   # バッククォート外の記載も拾う
            continue
        report["units_without_ledger_row"].append({
            "unit": unit, "file_count": len(files),
        })

    # --- 案 C (iii): 受領台帳に無いファイル ---
    ledger_path, how = pick_intake_ledger(root)
    keys, state = load_ledger_paths(ledger_path)
    report["intake_ledger"] = {
        "path": str(ledger_path.relative_to(root)) if ledger_path is not None else None,
        "selection": how,
        "state": state,
        "entry_count": len(keys),
    }
    if ledger_path is not None and keys:
        for unit, files in units:
            absent = [f for f in files
                      if f.relative_to(root).as_posix() not in keys]
            if absent:
                report["files_not_in_intake"].append({
                    "unit": unit,
                    "not_in_ledger": len(absent),
                    "file_count": len(files),
                    "examples": [f.relative_to(root).as_posix() for f in absent[:3]],
                })

    report["summary"] = {
        "unit_count": len(units),
        "units_without_ledger_row": len(report["units_without_ledger_row"]),
        "missing_paths": len(report["missing_paths"]),
        "units_with_files_not_in_intake": len(report["files_not_in_intake"]),
        "files_not_in_intake": sum(r["not_in_ledger"] for r in report["files_not_in_intake"]),
        "stale_rows": len(report["stale_rows"]),
        "undated_rows": len(report["undated_rows"]),
        "skipped_tables": len(report["skipped_tables"]),
        "malformed_rows": len(report["malformed_rows"]),
    }
    s = report["summary"]
    report["ok"] = (s["units_without_ledger_row"] == 0 and s["missing_paths"] == 0
                    and s["files_not_in_intake"] == 0 and s["stale_rows"] == 0)
    return report


def print_report(report: dict[str, Any]) -> None:
    if "error" in report:
        print(f"check_data_ledger: {report['error']}")
        return
    s = report["summary"]
    print(f"check_data_ledger: docs/DATA.md と実物の相互参照 "
          f"(基準日 {report['today']}、鮮度のしきい {report['max_age_days']} 日)")
    print(f"  単位 {s['unit_count']} 件 / "
          f"台帳に行が無い単位 {s['units_without_ledger_row']} 件 / "
          f"所在が実在しない行 {s['missing_paths']} 件 / "
          f"受領台帳に無いファイル {s['files_not_in_intake']} 個 "
          f"({s['units_with_files_not_in_intake']} 単位) / "
          f"最終確認日が古い行 {s['stale_rows']} 件")

    lg = report["intake_ledger"]
    print(f"\n受領台帳: {lg['path']}({lg['selection']}、{lg['state']}、"
          f"{lg['entry_count']} 行)")

    if report["skipped_tables"]:
        print(f"\n[飛ばした表] ヘッダが標準形でないので鮮度検査の対象外 "
              f"({len(report['skipped_tables'])} 表)")
        for t in report["skipped_tables"]:
            print(f"  {t['header_line']} 行目: {t['header']}({t['row_count']} 行)")
    if report["malformed_rows"]:
        print(f"\n[飛ばした行] セル数がヘッダと合わない "
              f"({len(report['malformed_rows'])} 行)")
        print("  行番号: " + ", ".join(str(r["line"]) for r in report["malformed_rows"]))

    print(f"\n(i) 台帳に行が無い単位 — {len(report['units_without_ledger_row'])} 件")
    if report["units_without_ledger_row"]:
        print("  | 単位 | ファイル数 |")
        for r in report["units_without_ledger_row"]:
            print(f"  | backtest_data/{r['unit']} | {r['file_count']} |")

    print(f"\n(ii) 所在のパスが実在しない行 — {len(report['missing_paths'])} 件")
    if report["missing_paths"]:
        print("  | 行 | 資産 | パス |")
        for r in report["missing_paths"]:
            print(f"  | {r['line']} | {r['asset'][:40]} | {r['path']} |")

    print(f"\n(iii) 受領台帳に無い backtest_data/ 配下のファイル — "
          f"{s['files_not_in_intake']} 個 / {s['units_with_files_not_in_intake']} 単位")
    if report["files_not_in_intake"]:
        print("  | 単位 | 台帳に無い | 単位のファイル数 | 例 |")
        for r in report["files_not_in_intake"]:
            print(f"  | backtest_data/{r['unit']} | {r['not_in_ledger']} | "
                  f"{r['file_count']} | {', '.join(r['examples'])} |")

    print(f"\n(iv) 最終確認日が {report['max_age_days']} 日より古い行 — "
          f"{len(report['stale_rows'])} 件")
    if report["stale_rows"]:
        print("  | 行 | 資産 | 最終確認日 | 経過日数 |")
        for r in report["stale_rows"]:
            print(f"  | {r['line']} | {r['asset'][:40]} | {r['last_checked']} | "
                  f"{r['age_days']} |")

    if report["undated_rows"]:
        print(f"\n(参考) 最終確認日が読めない行 — {len(report['undated_rows'])} 件")
        for r in report["undated_rows"]:
            print(f"  | {r['line']} | {r['asset'][:40]} | {r['cell'][:40]} |")

    print(f"\n食い違い: {'無し' if report['ok'] else 'あり'}")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(REPO_ROOT), help="リポジトリの根(既定: このリポジトリ)")
    ap.add_argument("--max-age-days", type=int, default=14,
                    help="「最終確認日」がこれより古い行を出す(既定 14)")
    ap.add_argument("--today", default=None,
                    help="基準日 YYYY-MM-DD(既定: 今日。テスト用)")
    ap.add_argument("--json", dest="json_path", default=None,
                    help="この JSON へ結果を書く(既定: 書かない)")
    ap.add_argument("--strict", action="store_true",
                    help="食い違いがあれば終了コード 1(既定は常に 0)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if args.today:
        m = DATE_RE.fullmatch(args.today.strip())
        if not m:
            print("--today は YYYY-MM-DD で指定する", file=sys.stderr)
            return 2
        today = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    else:
        today = datetime.now(timezone.utc).date()

    report = run(root, args.max_age_days, today)
    print_report(report)

    if args.json_path:
        out = Path(args.json_path)
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {out}")

    if args.strict and not report.get("ok", False):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
