#!/usr/bin/env python3
"""PC の共有(既定ブランチ)を作業ブランチに合流させる前の照合の表(L-984・L-986、門 G1 の取り込みの道具)。

オーナーの問い(2026-10-11): 「**ほんまに取り込む日合ってんのか？照合したんか？**」

読むのは git の木(`git ls-tree`)と、PC が共有に書いた在庫の一覧(`paper_logs/ws_listing.txt`)だけ。データの中身は開かない。
出すもの(Markdown):
  1. 置き場ごとに: 作業ブランチの日付の範囲 / 共有の日付の範囲 / 共有で新しく入る日 / 共有で中身が変わるファイル /
     共有で消えるファイル / 両方を合わせた範囲の中で抜けている日
  2. PC の生の WS 記録(`data/ws`、ws_listing.txt)がある日のうち、共有の tape(約定・ticker・板)が無い日

Usage:
    python3 scripts/share_reconcile.py [--out <md>]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_gates as dg  # noqa: E402

DATE8 = re.compile(r"(?<!\d)(20\d{6})(?!\d)")


def tree(ref: str, base: Path) -> dict[str, str]:
    """道 → blob の指紋(backtest_data・paper_logs)。"""
    out = subprocess.run(["git", "ls-tree", "-r", ref, "--", "backtest_data", "paper_logs"], cwd=base,
                         capture_output=True, text=True, check=True).stdout
    res = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        res[path] = meta.split()[2]
    return res


def day_of(path: str) -> date | None:
    """ファイル名(道の最後)の日付。置き場の名前の日付(取得日)とは分けて見る。"""
    m = DATE8.findall(path.rsplit("/", 1)[-1])
    if not m:
        m = DATE8.findall(path)
    if not m:
        return None
    d = m[-1]
    try:
        return date(int(d[:4]), int(d[4:6]), int(d[6:]))
    except ValueError:
        return None


def fmt_range(ds: set[date]) -> str:
    if not ds:
        return "—"
    return f"{min(ds).isoformat()}〜{max(ds).isoformat()}({len(ds)} 日)"


def missing_days(ds: set[date]) -> list[date]:
    if not ds:
        return []
    out = []
    d = min(ds)
    while d <= max(ds):
        if d not in ds:
            out.append(d)
        d += timedelta(days=1)
    return out


def compress(days: list[date]) -> str:
    if not days:
        return "なし"
    runs, s, p = [], days[0], days[0]
    for d in days[1:]:
        if d == p + timedelta(days=1):
            p = d
            continue
        runs.append((s, p))
        s = p = d
    runs.append((s, p))
    return "・".join(a.isoformat() if a == b else f"{a.isoformat()}〜{b.isoformat()}" for a, b in runs)


def snapshot_interval(base: Path, fam: str, share: dict[str, str]):
    """auto_<流れ>_<日付>/manifest.json の window.interval_days(一番新しい置き場の)。"""
    import json
    ms = sorted(p for p in share if p.endswith("/manifest.json") and dg.family_of(p) == fam)
    if not ms:
        return None
    raw = subprocess.run(["git", "show", f"{dg.SHARE_REF}:{ms[-1]}"], cwd=base, capture_output=True, text=True).stdout
    try:
        return (json.loads(raw).get("window") or {}).get("interval_days")
    except ValueError:
        return None


def ws_days(base: Path) -> set[date]:
    out = subprocess.run(["git", "show", f"{dg.SHARE_REF}:paper_logs/ws_listing.txt"], cwd=base,
                         capture_output=True).stdout.decode("cp932", errors="replace")
    ds = set()
    for m in re.finditer(r"FX_BTC_JPY_(20\d{6})_\d{6}\.jsonl\.gz", out):
        d = m.group(1)
        ds.add(date(int(d[:4]), int(d[4:6]), int(d[6:])))
    return ds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    base = dg.root()
    head = tree("HEAD", base)
    share = tree(dg.SHARE_REF, base)

    mb = subprocess.run(["git", "merge-base", "HEAD", dg.SHARE_REF], cwd=base, capture_output=True,
                        text=True, check=True).stdout.strip()

    def changes(a: str, b: str) -> dict[str, str]:
        out = subprocess.run(["git", "diff", "--name-status", "--no-renames", a, b, "--", "backtest_data", "paper_logs"],
                             cwd=base, capture_output=True, text=True, check=True).stdout
        return {ln.split("\t", 1)[1]: ln.split("\t", 1)[0] for ln in out.splitlines() if "\t" in ln}

    in_share = changes(mb, dg.SHARE_REF)   # 合流で入る変化(A 新しい / M 変わる / D 消える)
    in_head = changes(mb, "HEAD")          # 作業ブランチ側で同じファイルを変えていれば衝突しうる

    by_fam: dict[str, dict] = defaultdict(lambda: {"head": set(), "share": set(), "new": set(),
                                                   "changed": [], "removed": [], "conflict": [],
                                                   "kinds": defaultdict(set)})
    for path in set(head) | set(share):
        fam = dg.family_of(path)
        if fam is None:
            continue
        r = by_fam[fam]
        d = day_of(path)
        # tape のような流れは、ファイルの種類(executions / ticker / board_top10 …)ごとに日を見る
        kind = re.sub(r"_?20\d{6}.*$", "", path.rsplit("/", 1)[-1]) if fam.startswith("paper_logs/") else ""
        if path in head and d:
            r["head"].add(d)
        if path in share and d:
            r["share"].add(d)
            r["kinds"][kind].add(d)
        st = in_share.get(path)
        if st == "A" and d:
            r["new"].add(d)
        elif st == "A":
            r["changed"].append(path)
        if st == "M":
            r["changed"].append(path)
        if st == "D":
            r["removed"].append(path)
        if st and path in in_head:
            r["conflict"].append(path)

    lines = [f"# 共有の照合の表(作業ブランチ HEAD と既定ブランチ {dg.SHARE_REF})", ""]
    lines.append(f"合流の基点: {mb[:10]}。「新しく入る・変わる・消える」は基点から既定ブランチへの変化。")
    lines.append("")
    lines.append("| 置き場 | 作業ブランチの日付 | 共有の日付 | 共有で新しく入る日 | 変わるファイル | 消えるファイル | 両方で変えたファイル | 共有の範囲の中で抜けている日 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    touched = 0
    for fam in sorted(by_fam):
        r = by_fam[fam]
        if not (r["new"] or r["changed"] or r["removed"] or r["conflict"]):
            continue
        touched += 1
        miss = []
        interval = snapshot_interval(base, fam, share) if fam.startswith("auto_") else None
        if fam.startswith("auto_") and interval != 1:
            miss.append(f"取得の間隔 {interval} 日(毎日ではないので抜けとは数えない)")
        elif r["kinds"]:
            for kind, ds in sorted(r["kinds"].items()):
                m = missing_days(ds)
                if m:
                    miss.append(f"{kind or '(名前)'}: {compress(m)}")
        lines.append(f"| {fam} | {fmt_range(r['head'])} | {fmt_range(r['share'])} | {compress(sorted(r['new']))} | "
                     f"{len(r['changed'])} | {len(r['removed'])} | {len(r['conflict'])} | {'; '.join(miss) or 'なし'} |")
    lines += ["", f"共有で変わる置き場: {touched}"]

    ws = ws_days(base)
    tape = by_fam.get("paper_logs/tape", {"kinds": {}})["kinds"]
    lines += ["", "## PC の生の WS 記録(data/ws)がある日のうち、共有の tape が無い日", "",
              f"PC の WS 記録の日: {fmt_range(ws)}", ""]
    for kind in ("executions", "ticker", "board_top10"):
        have = tape.get(kind, set())
        lack = sorted(d for d in ws if d not in have)
        lines.append(f"- {kind}: 共有 {fmt_range(have)}、WS があって共有に無い日: {compress(lack)}")

    changed = [p for r in by_fam.values() for p in r["changed"]]
    removed = [p for r in by_fam.values() for p in r["removed"]]
    lines += ["", "## 中身が変わるファイル(合流で上書きされる)", ""] + [f"- `{p}`" for p in sorted(changed)[:60]]
    if len(changed) > 60:
        lines.append(f"- ほか {len(changed) - 60} 本")
    lines += ["", "## 消えるファイル", ""] + ([f"- `{p}`" for p in sorted(removed)] or ["- なし"])
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
