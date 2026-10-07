#!/usr/bin/env python3
"""1 本道の検査(L-754・L-755)。本体は `bot.bt.road.check.check_outputs`。

    PYTHONPATH=src python3 scripts/road/check_outputs.py <置き場のディレクトリ> --bars <1 分足の JSON>

置き場が表の形(道の走らせの置き場の `road/`。SCHEMA.json と signals・orders・fills・fx・ledger_fills・trades・summary)
なら (i)〜(vi) を当てる(L-766・L-767、委任文 DELEGATION_record_form.md 4.・3 周目。中身は bot.bt.road.check の説明):
(i)   表と列が SCHEMA どおりそろっているか(欠けたら失敗)
(ii)  生の表 fills・fx から帳簿を作り直し、ledger_fills・trades・summary と 1 欄でも違えば失敗
(iii) 値の形・時刻の順・届いた順・つなぎ(どの約定にも注文、どの注文にも存在する合図か「無し」、発生 ≤ 消失)
(iv)  足の検査を約定と、合図の発生・消失の時刻に当てる(その分の足がある・分の区切り)。
      足の遅れ(feed の遅延)が 0 でない走らせでは、合図の時刻が分の区切りから外れるので必ず落ちる
(v)   注文の量 = 記録した量の計算の値から size_per_level で計算し直した量、証拠金 20 万円・比率 0.7、量の計算の値段を
      足の終値・指値と、USDJPY を fx と突き合わせる。決済(flatten)の行は、届いた約定の知らせまでの建玉から計算し直す
(vi)  road/ の指紋を ../repro.json と、約定・注文を ../fills.json・../orders.json(pipeline の書き出し)と突き合わせる
足の JSON は [{"t_ns": 足の始まり(ns), "high": 数, "low": 数, "close": 数}, ...](close は表の形の置き場の (v) で使う)。
それ以外の置き場(作る順 1 の road_fills.json / road_summary.json)には次を当てる:
(a) 置き場の約定の列からまとめ(約定の数・取引ごとの表を含む)を帳簿のツールで計算し直し、置き場に書かれたまとめと
    1 つでも違えば失敗。
(b) 約定ごとに、その分の 1 分足があるか・足の始まりが分の区切りにそろうか・値段が安値以上高値以下か。
データ層からの足の読み込みはこの段では作らない。

終了コード: 0 = 全部通った / 1 = 失敗した行がある(一覧を出す) / 2 = 引数・足のファイルが読めない。
出す文は全部日本語(O-1)。引数の読み取りは argparse を使わない(argparse の文は英語のため)。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from bot.bt.road.check import StoreError, check_outputs, load_json  # noqa: E402

USAGE = ("使い方: PYTHONPATH=src python3 scripts/road/check_outputs.py <置き場のディレクトリ> --bars <1 分足の JSON>\n"
         "  置き場: 道の走らせの置き場の road/(SCHEMA.json と 7 つの表)、または road_fills.json と road_summary.json がある置き場\n"
         "  --bars: 1 分足の JSON([{t_ns, high, low, close}, ...])")


def _parse(argv: list[str]) -> tuple[str, str] | str:
    """(置き場, 足のファイル)、または誤りの文(日本語)。"""
    run_dir = bars = None
    k = 0
    while k < len(argv):
        a = argv[k]
        if a == "--bars":
            if k + 1 >= len(argv):
                return "--bars の後に 1 分足の JSON のファイルが無い"
            if bars is not None:
                return "--bars が 2 回ある"
            bars = argv[k + 1]
            k += 2
            continue
        if a.startswith("--bars="):
            if bars is not None:
                return "--bars が 2 回ある"
            bars = a[len("--bars="):]
        elif a.startswith("-"):
            return f"知らない引数: {a}"
        elif run_dir is None:
            run_dir = a
        else:
            return f"置き場は 1 つだけ渡す(2 つ目: {a})"
        k += 1
    if run_dir is None:
        return "置き場のディレクトリが無い"
    if not bars:
        return "--bars(1 分足の JSON)が無い"
    return run_dir, bars


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if any(a in ("-h", "--help") for a in argv):
        print(USAGE)
        return 0
    parsed = _parse(argv)
    if isinstance(parsed, str):
        print(f"引数の誤り: {parsed}\n{USAGE}", file=sys.stderr)
        return 2
    run_dir, bars_path = parsed
    try:
        bars = load_json(bars_path, "1 分足")
    except StoreError as exc:
        print(f"足のファイルが読めない: {exc}", file=sys.stderr)
        return 2
    if not isinstance(bars, list):
        print(f"足のファイルが列でない: {bars_path}", file=sys.stderr)
        return 2
    try:
        res = check_outputs(run_dir, bars)
    except Exception as exc:  # 想定していない壊れ方の置き場でも、英語の文を出さずに失敗として止める(O-1)
        print(f"検査 失敗: {run_dir}(検査の途中で想定していない壊れ方に当たった: {type(exc).__name__})", file=sys.stderr)
        return 3
    if res.ok:
        print(f"検査 通過: {run_dir}")
        return 0
    print(f"検査 失敗: {run_dir}(失敗した行 {len(res.failures)})")
    for f in res.failures:
        print(f"  ({f['check']}) 行 {f['row']}: {f['reason']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
