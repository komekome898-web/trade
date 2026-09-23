#!/usr/bin/env python3
"""Extract the survey-side candidate pool for item 0, mechanically.

Delegation doc §3 "調査結果の側の選び方": candidates are every catalogue row
that carries a mark in the element column, and for viewpoints without a
column, every candidate hit by the grep words the fixed requirements file
(docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md §3) states.
Nobody adds or removes candidates by hand; this script is the pool.

Mapping a SCAN line to catalogue numbers (fixed rules, applied in order):
  1. explicit numbers in the line: `候補 N`, `N 番`, a table row starting
     `| N ` + backtick (a list item's own `N.` is NOT used: SCAN numbers its
     lists per section, e.g. `5. \`qf-lib\`(62 番)`);
  2. catalogue names (and the aliases the catalogue index gives, e.g.
     `11 OctoBot`) appearing in the line; names shorter than 5 characters
     must match as a whole word, longer ones case-insensitively as a
     substring; the catalogue names `python3` and `info.license` are only
     matched by number (they are a program name and a metadata field that
     occur in many lines about other things);
  3a. an indented continuation line of a numbered list item (`N. ...`) also
     takes the candidates of that list item (rules 1 and 2 on the item line);
  3. otherwise, the nearest preceding `#### ` heading, by rule 2 only (SCAN's
     own heading numbers are per-run and are not catalogue numbers).
A repo part of a name (`owner/REPO` -> `REPO`) counts in rule 2 only as a
whole backticked word (some repo parts are common words or path parts, e.g.
`mote/backtest`), and not inside a full `owner/REPO` name already matched;
in a heading (rule 3) it counts as a whole word.
Lines that map to nothing are listed as unmapped with the reason.

Usage: python3 gen_pool.py [--out pool.tsv]
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCAN = ROOT / "docs/DATA/SCAN_2026-09-21_tools.md"
CATALOG = ROOT / "docs/DATA/tools_catalog.tsv"
INDEX = ROOT / "docs/DATA/TOOLS_CATALOG.md"

# The grep words are copied from REQUIREMENTS.md §3 (fixed file) verbatim.
GREPS: dict[str, list[str]] = {
    "P0-2": [r"ナノ秒\|nanosecond\|マイクロ秒\|microsecond"],
    "P0-3": [r"資金調達\|funding rate\|funding_rate",
             r"清算\|liquidation",
             r"板の差分\|板スナップショット\|板の写真\|order book snapshot\|depth update\|incremental"],
    "P0-4": [r"先読み\|未来の情報\|将来の情報\|データスヌーピング\|data snooping\|peek"],
    "P0-5": [r"決定的\|deterministic\|同時刻\|tie.break\|順序"],
    "P0-6": [r"on_bar\|on_tick\|コールバック\|callback\|戦略 API\|strategy interface\|プラガブル\|差し替え可能\|モジュール式\|pluggable"],
    "P0-7": [r"差し替え\|プラガブル\|モジュール式\|pluggable"],
}
NUMBER_ONLY = {"python3", "info.license"}


def load_catalog() -> dict[int, dict]:
    rows = {}
    with CATALOG.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows[int(r["番号"])] = r
    return rows


def aliases(cat: dict[int, dict]) -> list[tuple[str, int, bool]]:
    """(alias, number, is_repo_part). A repo part (`owner/REPO`) alone is
    matched only in backticks or right after `/` (rule 2) because some are
    common words (`mote/backtest` -> `backtest`)."""
    out: list[tuple[str, int, bool]] = []
    for n, r in cat.items():
        name = r["名前"].strip()
        if name in NUMBER_ONLY:
            continue
        out.append((name, n, False))
        if "/" in name:
            out.append((name.split("/", 1)[1], n, True))
    for m in re.finditer(r"(\d+) `([^`]+)`", INDEX.read_text(encoding="utf-8")):
        n, nm = int(m.group(1)), m.group(2)
        if n in cat and nm not in NUMBER_ONLY and (nm, n, False) not in out:
            out.append((nm, n, False))
    return out


def names_in(text: str, al: list[tuple[str, int, bool]], heading: bool = False) -> set[int]:
    found = set()
    low = text.lower()
    # full names first; their text is removed before repo parts are tried,
    # so `3yit/Limit-Order-Book-Simulator` does not also match the repo part
    # of `kahan15/Limit-Order-Book-Simulator`.
    rest = text
    for nm, n, repo_part in al:
        if not repo_part and "/" in nm and nm.lower() in low:
            rest = re.sub(re.escape(nm), " ", rest, flags=re.I)
    for nm, n, repo_part in al:
        if repo_part and not heading:
            if re.search(r"`" + re.escape(nm) + r"`", rest, re.I):
                found.add(n)
            continue
        if repo_part or len(nm) < 5:
            if re.search(r"(?<![\w-])" + re.escape(nm) + r"(?![\w-])", text, re.I):
                found.add(n)
        elif nm.lower() in low:
            found.add(n)
    return found


def numbers_in(text: str, cat: dict[int, dict]) -> set[int]:
    nums = set()
    for pat in (r"候補\s*(\d+)", r"(\d+)\s*番", r"^\|\s*(\d+)\s+`"):
        for m in re.finditer(pat, text):
            v = int(m.group(1))
            if v in cat:
                nums.add(v)
    return nums


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("pool.tsv"))
    args = ap.parse_args()
    cat = load_catalog()
    al = aliases(cat)
    lines = SCAN.read_text(encoding="utf-8").splitlines()
    heading_at: list[str] = []
    list_item_at: list[str] = []
    cur, item = "", ""
    for ln in lines:
        if ln.startswith("#"):
            cur = ln if ln.startswith("#### ") else ("" if ln.startswith("## ") or ln.startswith("### ") else cur)
            item = ""
        elif re.match(r"^\d+\.\s", ln):
            item = ln
        elif not ln.startswith("   "):
            item = ""
        heading_at.append(cur)
        list_item_at.append(item)

    rows: list[dict] = []
    # P0-1: the catalogue's event-driven column (column 7), mark ○.
    for n, r in sorted(cat.items()):
        if r["イベント駆動"].strip() == "○":
            rows.append({"viewpoint": "P0-1", "cand": n, "name": r["名前"], "rule": "台帳 7 列目 = ○",
                         "scan_lines": r["報告書の最後の記載の行"], "pattern": "awk -F'\\t' 'NR==1{next} $7==\"○\"{print $1\"\\t\"$2}' docs/DATA/tools_catalog.tsv"})
    unmapped: list[tuple[str, int, str]] = []
    for vp, pats in GREPS.items():
        hits: dict[int, list[tuple[int, str]]] = {}
        for pat in pats:
            res = subprocess.run(["grep", "-n", pat, str(SCAN)], capture_output=True, text=True)
            for hl in res.stdout.splitlines():
                ln_no = int(hl.split(":", 1)[0])
                text = lines[ln_no - 1]
                c = numbers_in(text, cat)
                rule = "1"
                if not c:
                    c = names_in(text, al)
                    rule = "2"
                if text.startswith("   ") and list_item_at[ln_no - 1]:
                    item = list_item_at[ln_no - 1]
                    extra = numbers_in(item, cat) or names_in(item, al)
                    if extra - c:
                        c = c | extra
                        rule = rule + "+3a"
                if not c and heading_at[ln_no - 1]:
                    c = names_in(heading_at[ln_no - 1], al, heading=True)
                    rule = "3"
                if not c:
                    unmapped.append((vp, ln_no, text[:80]))
                    continue
                for n in c:
                    hits.setdefault(n, []).append((ln_no, rule))
        for n in sorted(hits):
            ls = sorted(set(hits[n]))
            rows.append({"viewpoint": vp, "cand": n, "name": cat[n]["名前"],
                         "rule": ",".join(sorted({r for _, r in ls})),
                         "scan_lines": " ".join(str(l) for l, _ in ls),
                         "pattern": " / ".join(pats)})
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["viewpoint", "cand", "name", "rule", "scan_lines", "pattern"], delimiter="\t")
        w.writeheader()
        w.writerows(rows)
        f.write("\n# unmapped grep hits (viewpoint, SCAN line, head of the line)\n")
        for vp, ln_no, t in unmapped:
            f.write(f"# {vp}\t{ln_no}\t{t}\n")
    by_vp: dict[str, int] = {}
    for r in rows:
        by_vp[r["viewpoint"]] = by_vp.get(r["viewpoint"], 0) + 1
    print("pool:", by_vp, "unmapped:", len(unmapped), "->", args.out)


if __name__ == "__main__":
    main()
