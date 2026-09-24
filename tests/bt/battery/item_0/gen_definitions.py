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
- **型を測らない観点の場面の型(第 r7-1 回)**: P0-3 以外の観点の場面は、使う事象の型を場面の側で決め打ちにしない。型を持つかは P0-3 が型ごとに測るので、ほかの観点の場面の結果が型の有無で決まらないようにする。複数の型が要る場面(入力に `type_rule` がある p1-merge-by-time・p1-typed-events・p5-same-time-twice・p5-hand-over-order)は、対象の型を固定した要件 §1 の型の順(約定・板の写真・板の差分・足・資金調達・清算)に並べたものから runner が型を決め、入力と期待を作る(各場面の `type_rule` と「正解の出し方」。定義に載せた入力と期待は 6 種を全部持つ対象のもの)。対象の型 = 同じ実行の p3-<型> の場面で、対象がその型の事象を戦略に届けた型(出所の検めを通り、受けた列が空でなく、受けた型が全部その型)。型が場面の最低の数に足りない対象は、runner がその場面を「対応なし」にし、理由に p3 の結果を書く。1 つの型で足りる場面は「対象が受ける型を 1 つ選んでよい」(p1-one-call-per-event・P0-2 の 2 場面・p5-same-stream-order。型は採点しない)か、約定と足のどちらか(`any_type` の場面と P0-4 の 2 場面)。
- 当方の注文が埋まる場面では、市場の約定は 1 件 100 単位(注文は 1 単位)。対象の出来高の上限で結果が決まらないようにするため。
- 対象に事象を渡す側は、場面が書いた順・まとまりのまま渡す。並べ替え・結合・間引きをしない(それを測っている)。
- 「受け取った値」は、戦略が呼び出しの中でその場で記録した値。実行の後に結果から読んだ値ではない(場面が別に書いたときを除く)。
- 対象の公開の手段と公開の差し込み口だけを使う。対象のコードを書き換えない・実行中に差し替えない。
- **場面が測るもの(事象の型・時刻の変換・過去の読み出し・並び)は、対象の配布物のコードが出したものだけを数える。**対象に事象を渡す側と場面の戦略が書いてよいのは、(1) 対象の公開の手段を呼ぶこと、(2) 対象が利用者の実装を受けると公開している差し込み口に渡すダミー(P0-7 の模型・口座、時計を起こす条件)、(3) 対象が返したものを場面の語に写すこと(型の名前を `kind` に、状態を通知の種類に)、だけ。事象を渡す側が作った型(対象の基の class の子、欄を足した基の class、型の印を付けた辞書や関数)で事象を運ばない。戦略が自分で貯めた値、渡す側が自分で呼んだ変換で答えない。対象がその型・手段を持たないときは「対応なし」(何を確かめたかを書く)。

## 判定(資料係の表の 2 つの欄。対象の側は判定しない)

- **正しさ**: 正解と一致 / 対応なし(対象が明示的に拒否した・その口が無いことを実際に呼んで確かめた)/ 不一致(黙って違う結果を返した)/ 結果なし(例外で結果が出なかった)。期待が辞書のときは、期待に書いた鍵がすべて同じ値で出ていれば一致(出力の余分な鍵は見ない)。
- **採点に使う値を出力から作る場面**(「採点に使う値」の行がある場面): 対象の側(adapter)は観測したもの(届いた列・試しの結果・対象が明記した規則とその出所)だけを出し、採点に使う値は runner が書いたとおりに作る。対象の側が「できた」と書いた値では採点しない(場面集の規則 1)。
- **出所の検め**(採点の前。runner が行う): 戦略が受け取った事象の列を返す場面では、受け取った 1 件ごとの物を、p2-iso-* では ISO の文字列を読んだ対象の関数を、p4-visible-at-step では件数と終値を読んだ読み出しを、p4-future-read-attempt では手段ごとの試しを、対象の側が出所として返す。**出所は、場面集の共通の部品(`adapters/common.py`)が物から作った記録だけを受ける**(手で書いた名前・辞書は採点しない)。**「対象の物」と数えるのは、出所のファイルが対象の配布物の置き場所の中にあると示せたときだけ**(置き場所は runner が対象ごとに持つ表 `TARGET_DISTS` から、その対象の環境の import の探索で決める。場面集の名前でないことからは決めない)。示し方は、**型**と**届いた道**の 2 つを別々に示す(型は「対象がその型を持つ」ことしか示さず、「この物を対象が戦略に届けた」ことは示さないため。第 r6-3 回): (a) 型: 物の型を定義したファイル(numpy の行はその dtype、札の付いた物は札の型か札の定数を持つモジュールも)が置き場所にある。`dict`・関数・`datetime`・`DataFrame` のような誰でも作れる型の物は、場面集の側が対象に渡した物・場面集の側が持っている物と同じ物でないこと(対象が作った物)で示す。(b) 届いた道(型を問わず、対象の class の物にも当てる): **対象のコードが戦略の呼び出しに引数として渡した**か、**そうして渡した物の中にあった**(場面集の側の物の属性を通る道は数えない)か、**対象の母語(C・C++ など)のコードが戦略を呼んで渡した**(runner が場面ごとに `sys.setprofile` で走っている母語の関数を記録する)か、**戦略が対象の関数を呼んで返ってきた**(`common.read`・property の読み `common.attr`・反復 `common.iterate`/`common.aiterate`)か、のどれかが置き場所のコードである。場面の入力を adapter が対象の class で組んで対象に渡し、対象が届けた物は数える(どの対象も場面の入力は adapter が対象の入口の形に直して渡す。記録には `input` と残す)。戦略の呼び出しの中で場面集の側が対象の class を組んだ物・adapter が持つだけで対象に渡していない物は数えない。(c) 読み出しと試しは、その間に対象のコードが走った(`sys.setprofile` で記録)か、読んだ物が (a)(b) で対象の物か、手段が対象のコードの関数・method、(d) 翻訳した道具(Rust・Go・C・C++)は driver が物から名付けた型・関数の名前が対象の名前の頭で始まる。出所が無い・示せない・場面集の側の型・1 つの型に 2 つの `kind` を写した・読み出しと答えが食い違う・名指し方の一覧が欠ける・名指しの試しの例外が場面集の側の `raise` 文で起きた、のどれかなら、その場面は採点せず「結果なし」にし、理由を残す。
- **再現**: 2 回の実行で同じ / 2 回で違う / 結果なし。
- 良い順(場面集の規則 5): 正解と一致 > 対応なし > 不一致 > 結果なし。正しさが同じなら「2 回の実行で同じ」が上。

## 場面にしていない観点・側面

- 観点: なし。要件の §2 の 7 観点はすべて場面にした(振る舞いでない形の観点は無い)。
- 側面: P0-2 の「他の単位(秒・ミリ・ISO 文字列)が核の内部表現に混入しないこと」の**拒否の側**(秒の整数や小数の時刻を事象の時刻として渡したとき、止めるか黙って受けるか)は場面にしていない。固定した測り方(REQUIREMENTS.md §2 P0-2「既知の時刻を投入し、核が保持する値が同じ int64 ナノ秒と一致するか」)は受け入れの側の一致だけを求め、拒否の場面を足すと測り方より厳しくなる(委任文 §3「後から厳しくもしない」)。この側面は審査員ではなく批評家が見る(委任文 §3「場面にできない観点は場面係が記録し、審査員ではなく批評家が見る」)。
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
            if s.graded_from:
                out.append(f"- **採点に使う値**: {s.graded_from}")
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
