#!/usr/bin/env python3
"""1 本道の検査(L-754・L-755)。本体は `bot.bt.road.check.check_outputs`。

    PYTHONPATH=src python3 scripts/road/check_outputs.py <置き場のディレクトリ> --bars <1 分足の JSON>

(a) 置き場の約定の列からまとめを帳簿のツールで計算し直し、置き場に書かれたまとめと 1 つでも違えば失敗。
(b) 約定ごとに、その分の 1 分足があるか・足の始まりが分の区切りにそろうか・値段が安値以上高値以下か。
足の JSON は [{"t_ns": 足の始まり(ns), "high": 数, "low": 数}, ...]。データ層からの読み込みはこの段では作らない。

終了コード: 0 = 全部通った / 1 = 失敗した行がある(一覧を出す) / 2 = 引数・足のファイルが読めない。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from bot.bt.road.check import check_outputs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="1 本道の検査: まとめの計算し直しと、約定が 1 分足の上にあるか")
    ap.add_argument("run_dir", help="走らせの置き場(road_fills.json と road_summary.json がある)")
    ap.add_argument("--bars", required=True, help="1 分足の JSON([{t_ns, high, low}, ...])")
    a = ap.parse_args(argv)
    try:
        with open(a.bars, "r", encoding="utf-8") as fh:
            bars = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"足のファイルが読めない: {a.bars}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(bars, list):
        print(f"足のファイルが列でない: {a.bars}", file=sys.stderr)
        return 2
    res = check_outputs(a.run_dir, bars)
    if res.ok:
        print(f"検査 通過: {a.run_dir}")
        return 0
    print(f"検査 失敗: {a.run_dir}(失敗した行 {len(res.failures)})")
    for f in res.failures:
        print(f"  ({f['check']}) 行 {f['row']}: {f['reason']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
