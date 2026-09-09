"""事前登録の**数値を手で書かせない**。測定出力から生成する。

**なぜ(2026-09-09、L-054)**: 2 回の独立監査で出た欠陥のうち、最も多い型は
**「文書に書いた数値が、測定と食い違う」**だった。

- 「全面差し替え」と書いた表の 3 列中 2 列が差し替えられていなかった(I-005 の訂正漏れ)
- 「9 割減る」が、決済ルールの片枝を実装していない旧測定の残骸だった
- 保有分布の表が、**族の中で最も門が緩い 1 セル**の数字だった(どのセルか書いていない)
- 上限到達率の射程が、11 通りの門のうち 1 通りしか見ていなかった

**個別に直しても、直した端から新しい数値が手で書かれる。**
そこで**数値を書ける場所そのものを無くす**: テンプレートに参照だけを書き、
生成器が測定出力から埋める。**「文書と測定がずれる」が構造的に表現不能になる。**

    PYTHONPATH=src python scripts/render_prereg.py                 # 生成
    PYTHONPATH=src python scripts/render_prereg.py --check         # ずれていないか検査

**PREREG.md は生成物であり、手で編集してはならない。** 編集するのは `.tmpl` の方。
`--check` は出荷前検査(C8)から呼ばれる。

## 参照の書き方

    {{cell:15|s19/b24|both.sd_trade_bp}}   セルの値
    {{exit:15|invalid|colour=1.hold_median}} 決済ルール分解の値
    {{family.size}} {{family.feet}} {{family.gates}} {{family.strengths}}
    {{stat.min_n}} {{stat.median_n}} {{stat.max_n}} {{stat.max_capped_share}}
    {{stat.argmin_n}} {{stat.argmax_capped_share}}   ← **どのセルか**も参照で出す

数値は `,` 区切り、割合は `%` に整形される。**参照がセル名を含むので、
「どのセルの数字か書いていない」という欠陥も起こせない。**
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_TMPL = REPO / "docs" / "PHASE2" / "K1" / "PREREG.md.tmpl"
DEFAULT_OUT = REPO / "docs" / "PHASE2" / "K1" / "PREREG.md"
DEFAULT_DATA = REPO / "docs" / "PHASE2" / "K1" / "dispersion.json"

REF = re.compile(r"\{\{([^}]+)\}\}")


class RefError(Exception):
    pass


def _fmt(value, field: str) -> str:
    if isinstance(value, float):
        if field.endswith("_share"):
            return f"{value:.1%}"
        return f"{value:g}"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, list):
        return " / ".join(str(x) for x in value)
    return str(value)


def resolve(ref: str, data: dict) -> str:
    """1 つの参照を解決する。**解決できない参照は例外**(黙って空にしない)。"""
    ref = ref.strip()
    cells = data.get("cells", {})
    exits = data.get("exit_variants", {})
    fam = data.get("family", {})

    if ref.startswith("cell:") or ref.startswith("exit:"):
        kind, rest = ref.split(":", 1)
        key, _, field = rest.rpartition(".")
        table = cells if kind == "cell" else exits
        if key not in table:
            raise RefError(f"{kind} `{key}` が測定出力に無い")
        if field not in table[key]:
            raise RefError(f"{kind} `{key}` に項目 `{field}` が無い")
        return _fmt(table[key][field], field)

    if ref.startswith("family."):
        what = ref.split(".", 1)[1]
        if what == "size":
            return f"{len(fam['feet']) * len(fam['gates']) * len(fam['strengths']):,}"
        if what in fam:
            return _fmt(fam[what], what)
        raise RefError(f"family に `{what}` が無い")

    if ref.startswith("stat."):
        what = ref.split(".", 1)[1]
        if not cells:
            raise RefError("cells が空で stat を出せない")
        ns = sorted(v["n"] for v in cells.values())
        if what == "min_n":
            return f"{ns[0]:,}"
        if what == "median_n":
            return f"{ns[len(ns) // 2]:,}"
        if what == "max_n":
            return f"{ns[-1]:,}"
        if what == "argmin_n":
            return min(cells.items(), key=lambda kv: kv[1]["n"])[0]
        if what == "max_capped_share":
            return f"{max(v['capped_share'] for v in cells.values()):.1%}"
        if what == "argmax_capped_share":
            return max(cells.items(), key=lambda kv: kv[1]["capped_share"])[0]
        if what == "cells_over_10pct_capped":
            return str(sum(1 for v in cells.values() if v["capped_share"] > 0.10))
        raise RefError(f"stat に `{what}` が無い")

    raise RefError(f"参照の形式が不明: `{ref}`")


def render(tmpl_text: str, data: dict) -> tuple[str, list[str]]:
    """テンプレートを埋める。解決できなかった参照は errors に集める。"""
    errors: list[str] = []

    def sub(m: re.Match) -> str:
        try:
            return resolve(m.group(1), data)
        except RefError as e:
            errors.append(str(e))
            return m.group(0)

    return REF.sub(sub, tmpl_text), errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tmpl", default=str(DEFAULT_TMPL))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--check", action="store_true",
                    help="生成せず、出力が最新かだけ見る(出荷前検査 C8 が使う)")
    args = ap.parse_args()

    tmpl, out, datafile = Path(args.tmpl), Path(args.out), Path(args.data)
    if not tmpl.exists():
        print(f"テンプレートが無い: {tmpl}")
        return 1
    data = json.loads(datafile.read_text(encoding="utf-8"))
    text, errors = render(tmpl.read_text(encoding="utf-8"), data)

    if errors:
        print(f"**解決できない参照 {len(errors)} 件**:")
        for e in dict.fromkeys(errors):
            print(f"  - {e}")
        return 1

    if args.check:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != text:
            print(f"**{out.name} が {tmpl.name} + 測定出力と一致しない。**")
            print("  PREREG.md は生成物である。手で編集していないか確認し、")
            print("  `python scripts/render_prereg.py` で作り直すこと。")
            cur_lines, new_lines = current.splitlines(), text.splitlines()
            for i, (a, b) in enumerate(zip(cur_lines, new_lines), 1):
                if a != b:
                    print(f"  最初の相違 {i} 行目:\n    現在: {a[:100]}\n    生成: {b[:100]}")
                    break
            else:
                print(f"  行数が違う(現在 {len(cur_lines)} / 生成 {len(new_lines)})")
            return 1
        print(f"{out.name} は {tmpl.name} + 測定出力と一致している")
        return 0

    out.write_text(text, encoding="utf-8")
    print(f"{tmpl.name} + {datafile.name} → {out.name}({len(REF.findall(tmpl.read_text(encoding='utf-8')))} 参照を解決)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
