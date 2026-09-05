"""Inter-auditor agreement between the first audit (verdicts as tabulated in
docs/AUDIT_2026-09/99_master.md) and the second blind audit reports
docs/AUDIT_2026-09/<PACKET>2_second.md.

Usage: python scripts/qa/agreement.py H I U ...   (defaults to the 9 sampled packets)
Prints a per-claim table and two agreement rates:
  exact  = same verdict class
  conclusion = same after merging 再現 + 数値差異(結論維持) (both mean "conclusion holds")
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUD = ROOT / "docs" / "AUDIT_2026-09"
DEFAULT = ["H", "I", "U", "X", "AA", "AC", "AH", "AJ", "AO"]

CLASSES = ["再現", "数値差異", "結論変更", "未検証", "判定不能", "再計算不能"]


def norm(v: str) -> str:
    v = v.replace("*", "").strip()
    for c in CLASSES:
        if c in v:
            return "未検証" if c == "再計算不能" else c
    return "?"


def conclusion(v: str) -> str:
    return "維持" if v in ("再現", "数値差異") else v


def first_verdicts() -> dict[str, tuple[str, str]]:
    """claim -> (packets, verdict) from 99_master.md."""
    out = {}
    for line in (AUD / "99_master.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*([A-Z]+\d+)\s*\|\s*([A-Z, ]+?)\s*\|\s*([^|]+)\|", line)
        if m:
            out[m.group(1)] = (m.group(2).replace(" ", ""), norm(m.group(3)))
    return out


def second_verdicts(packet: str) -> dict[str, str]:
    path = AUD / f"{packet}2_second.md"
    if not path.exists():
        return {}
    out, cur = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        h = re.match(r"^#{1,4}\s+([A-Z]+\d+)\b", line)
        if h:
            cur = h.group(1)
            continue
        if cur and re.match(r"^\**\s*Verdict\s*[::]", line, re.I):
            out[cur] = norm(line.split(":", 1)[-1] if ":" in line else line.split(":", 1)[-1])
    return out


def main(packets: list[str]) -> None:
    first = first_verdicts()
    rows, exact, concl, n = [], 0, 0, 0
    for p in packets:
        sec = second_verdicts(p)
        claims = [c for c, (pk, _) in first.items() if p in pk.split(",")]
        for c in claims:
            v1 = first[c][1]
            v2 = sec.get(c, "(なし)")
            e = v1 == v2
            k = conclusion(v1) == conclusion(v2)
            if v2 != "(なし)":
                n += 1
                exact += e
                concl += k
            rows.append((p, c, v1, v2, "○" if e else ("△" if k else "×")))
    print("| packet | claim | 第1 | 第2 | 一致 |")
    print("|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(r) + " |")
    if n:
        print(f"\nclaims scored: {n}  exact: {exact}/{n} = {exact/n:.2f}  conclusion-level: {concl}/{n} = {concl/n:.2f}")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
