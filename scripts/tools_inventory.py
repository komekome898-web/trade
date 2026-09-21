#!/usr/bin/env python3
"""当方の道具立ての一覧を `git ls-files` から機械的に出す(手書きの列挙をやめる。2026-09-21、監査の指摘)。

出所: 調査班の委任文 `docs/DATA/delegations/20260921_tools_survey_prompt.md` §8 の比較基準を、
リードの手書き(3 回直して 3 回漏れた: scripts/qa・scripts/phase2・phase2_seal.py)から
この出力に置き換える。判定はしない。並びは決定的(ソート)。

使い方: python3 scripts/tools_inventory.py [--all-files]
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import re
import subprocess
import sys


def ls(*paths: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", *paths], capture_output=True, text=True, check=True).stdout
    return sorted(l for l in out.splitlines() if l.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-files", action="store_true", help="ファイル名を全部出す(既定は package / 接頭辞ごとの件数と名前)")
    a = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"# 当方の道具立て(git ls-files から生成。{now}、HEAD {head}。コマンド: python3 scripts/tools_inventory.py)")

    print("\n## src/bot(package: ファイル数 / ファイル名)")
    by_pkg: dict[str, list[str]] = collections.defaultdict(list)
    for f in ls("src/bot"):
        if not f.endswith(".py") or f.endswith("__init__.py"):
            continue
        parts = f.split("/")
        pkg = "/".join(parts[:-1])
        by_pkg[pkg].append(parts[-1])
    for pkg in sorted(by_pkg):
        print(f"- {pkg}: {len(by_pkg[pkg])} / {' '.join(sorted(by_pkg[pkg]))}")

    print("\n## scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)")
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for f in ls("scripts"):
        if not f.endswith(".py") or f.endswith("__init__.py"):
            continue
        parts = f.split("/")
        if len(parts) > 2:
            groups[parts[1] + "/"].append("/".join(parts[2:]))
        else:
            m = re.match(r"([A-Za-z0-9]+)_", parts[1])
            groups[(m.group(1) + "_*") if m else "(単発)"].append(parts[1])
    for g in sorted(groups, key=lambda k: (-len(groups[k]), k)):
        names = sorted(groups[g])
        shown = " ".join(names) if (a.all_files or len(names) <= 14) else " ".join(names[:14]) + f" …(+{len(names) - 14})"
        print(f"- {g}: {len(names)} / {shown}")
    non_py = [f for f in ls("scripts") if not f.endswith(".py")]
    print(f"- (.py 以外の scripts: {len(non_py)} = {' '.join(non_py)})")

    for label, paths in (("config", ["config"]), ("deploy", ["deploy"]), ("tests(ファイル)", ["tests"]),
                         (".claude/hooks", [".claude/hooks"]), (".claude/agents", [".claude/agents"]),
                         (".claude/skills", [".claude/skills"]), ("githooks", ["githooks"]), ("docs(.md)", ["docs"])):
        fs = ls(*paths)
        if label.startswith("docs"):
            fs = [f for f in fs if f.endswith(".md")]
        print(f"\n## {label}: {len(fs)}")
        if a.all_files or len(fs) <= 12:
            print("  " + " ".join(fs))
        else:
            print("  " + " ".join(fs[:12]) + f" …(+{len(fs) - 12})")
    print("\n## backtest_data(ディレクトリ数)")
    dirs = sorted({f.split("/")[1] for f in ls("backtest_data") if "/" in f})
    print(f"  {len(dirs)}: " + " ".join(dirs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
