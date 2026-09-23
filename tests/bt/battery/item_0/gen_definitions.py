#!/usr/bin/env python3
"""Render scenes.py into DEFINITIONS.md (the one document of scene
definitions). `python3 gen_definitions.py` writes it; `--check` exits 1 if
the file on disk differs (the pytest in this directory runs the check)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenes  # noqa: E402

HEAD = """# 項目 0「核」の場面集 — 定義

**この文書は `scenes.py` から `gen_definitions.py` で作る。手で直さない**(`test_battery_item0.py` が食い違いを落とす)。
固定した要件: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`。観点は §2 の P0-1〜P0-7。

## 共通の決まり(すべての場面の入力の一部)

- 時刻は 1970-01-01T00:00:00Z からのナノ秒の整数。`T0` = 1,700,006,400,000,000,000(2023-11-15T00:00:00Z、水曜日の 0 時)、`S` = 1 秒 = 1,000,000,000、`DAY` = 1 日 = 86,400 秒。
- 事象の間隔は、時刻そのものを測る場面(P0-2、P0-5 の同時刻、ミリ秒の遅延の場面)を除いて 1 日。暦の上の日足しか受けない対象でも、それ以外の場面を測れるようにするため。
- 事象は `kind`(trade = 約定 / book_snapshot = 板の写真 / book_delta = 板の差分 / bar = 足 / funding = 資金調達 / liquidation = 清算)と `ts_ns`(取引所の時刻)を持つ。`recv_ns`(当方が受け取れる最初の時刻)は書いていなければ `ts_ns` と同じ。足の `ts_ns` は足が閉じた時刻。
- 入力に `"any_type": true` がある場面は、事象の型以外を測る場面である。約定を受けない対象では、各約定を、同じ時刻(受け取れる時刻も同じ)で 始値=高値=安値=終値=その約定の価格 の足に代えてよい(代えたことを記録に書く)。
- 当方の注文が埋まる場面では、市場の約定は 1 件 100 単位(注文は 1 単位)。対象の出来高の上限で結果が決まらないようにするため。
- 対象に事象を渡す側は、場面が書いた順・まとまりのまま渡す。並べ替え・結合・間引きをしない(それを測っている)。
- 「受け取った値」は、戦略が呼び出しの中でその場で記録した値。実行の後に結果から読んだ値ではない(場面が別に書いたときを除く)。
- 対象の公開の手段と公開の差し込み口だけを使う。対象のコードを書き換えない・実行中に差し替えない。

## 判定(資料係の表の 2 つの欄。対象の側は判定しない)

- **正しさ**: 正解と一致 / 対応なし(対象が明示的に拒否した・その口が無いことを実際に呼んで確かめた)/ 不一致(黙って違う結果を返した)/ 結果なし(例外で結果が出なかった)。期待が辞書のときは、期待に書いた鍵がすべて同じ値で出ていれば一致(出力の余分な鍵は見ない)。
- **再現**: 2 回の実行で同じ / 2 回で違う / 結果なし。
- 良い順(場面集の規則 5): 正解と一致 > 対応なし > 不一致 > 結果なし。正しさが同じなら「2 回の実行で同じ」が上。

## 場面にしていない観点

なし。要件の §2 の 7 観点はすべて場面にした(振る舞いでない形の観点は無い)。
"""


def fmt(v) -> str:
    return "`" + json.dumps(v, ensure_ascii=False) + "`"


def render() -> str:
    out = [HEAD]
    for vp, title in scenes.VIEWPOINTS.items():
        ss = [s for s in scenes.SCENES if s.viewpoint == vp]
        n_val = sum(1 for s in ss if s.kind == "value")
        out.append(f"\n## {vp} {title}\n\n場面 {len(ss)} 件(値の場面 {n_val} / 能力の場面 {len(ss) - n_val})\n")
        for s in ss:
            kind = "値の場面" if s.kind == "value" else "能力の場面"
            out.append(f"\n### `{s.id}` — {s.title}({kind})\n")
            out.append(f"- **入力**: {fmt(s.input)}")
            out.append(f"- **期待(正解)**: {fmt(s.expected)}")
            out.append(f"- **正解の出し方**: {s.derivation}")
            out.append(f"- **何を測るか**: {s.measures}")
    out.append(f"\n## 件数\n\n場面 {len(scenes.SCENES)} 件。\n")
    return "\n".join(out)


def main() -> int:
    path = HERE / "DEFINITIONS.md"
    text = render()
    if "--check" in sys.argv:
        if path.read_text(encoding="utf-8") != text:
            print("DEFINITIONS.md differs from scenes.py; run gen_definitions.py")
            return 1
        print("OK")
        return 0
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path} ({len(scenes.SCENES)} scenes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
