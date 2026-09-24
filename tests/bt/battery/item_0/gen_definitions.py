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
- **型の組を設定つき対象の持つ型から決める場面(L-438 (2)、第 r8-1 回)**: {L438}。この {N438} 場面だけが入力に `type_rule` を持つ。入力の事象の型の組は、下の「設定の操作と設定つき対象」の設定つき対象ごとに、その設定つき対象の持つ型から規則(各場面の入力の `type_rule`)で runner が決め、期待は型の組から式(各場面の「正解の出し方」)で出す。規則と式は対象の出力を読まない。定義に載せた入力と期待は 6 種を全部持つ設定つき対象のもの。ほかの場面の入力の型の組は対象から決めない(場面の入力に書いた型、または入力の note が名指す選び方)。
- **設定の操作と設定つき対象(第 r8-1 回)**: 場面の結果を対象に帰すのは、その実行の中で利用者が対象の公開の手段で行った設定の操作(データの購読・事象の型の組・解像度・同時刻の並びの引数・差し込む模型と口座を作り、足し、替える操作。実行の途中の操作も入る)の列の下で出た物だけである。どの設定の操作も、実行の前に利用者が知りうる物(場面が名指す銘柄と事象の型・その設定つき対象の選ぶ値・対象の公開の既定)と、その操作までに戦略が受けた物だけから決まる。まだ届いていない入力の値・時刻・順・件数に合わせて決めた設定(例: 場面の事象の最初と最後の時刻に合わせた実行の窓)の下で出た結果は採点しない(結果なし、理由を残す)。設定つき対象 = 対象 × 選ぶ値(設定の操作のうち場面の入力が決めない部分、つまり利用者が選ぶ値の全部の組み合わせ)。1 つの設定つき対象の場面は全部同じ選ぶ値で走らせ、設定つき対象ごとに別々の結果にする。比較の表の「調査結果の側」は場面ごとに走らせた設定つき対象の最良を寄せる(どのセルも 1 つの設定つき対象の実際の実行の結果)。
- 当方の注文が埋まる場面では、市場の約定は 1 件 100 単位(注文は 1 単位)。対象の出来高の上限で結果が決まらないようにするため。
- 対象に事象を渡す側は、場面が書いた順・まとまりのまま渡す。並べ替え・結合・間引きをしない(それを測っている)。
- 「受け取った値」は、戦略が呼び出しの中でその場で記録した値。実行の後に結果から読んだ値ではない(場面が別に書いたときを除く)。
- 対象の公開の手段と公開の差し込み口だけを使う。対象のコードを書き換えない・実行中に差し替えない。
- **場面が測るもの(事象の型・時刻の変換・過去の読み出し・並び)は、対象の配布物のコードが出したものだけを数える。**対象に事象を渡す側と場面の戦略が書いてよいのは、(1) 対象の公開の手段を呼ぶこと、(2) 対象が利用者の実装を受けると公開している差し込み口に渡すダミー(P0-7 の模型・口座、時計を起こす条件)、(3) 対象が返したものを場面の語に写すこと(型の名前を `kind` に、状態を通知の種類に)、だけ。事象を渡す側が作った型(対象の基の class の子、欄を足した基の class、型の印を付けた辞書や関数)で事象を運ばない。戦略が自分で貯めた値、渡す側が自分で呼んだ変換で答えない。対象がその型・手段を持たないときは「対応なし」(何を確かめたかを書く)。

## 判定(資料係の表の 2 つの欄。対象の側は判定しない)

- **正しさ**: 正解と一致 / 対応なし(対象が明示的に拒否した・その口が無いことを実際に呼んで確かめた)/ 不一致(黙って違う結果を返した)/ 結果なし(例外で結果が出なかった)。期待が辞書のときは、期待に書いた鍵がすべて同じ値で出ていれば一致(出力の余分な鍵は見ない)。
- **採点に使う値を出力から作る場面**(「採点に使う値」の行がある場面): 対象の側(adapter)は観測したもの(届いた列・試しの結果・対象が明記した規則とその出所)だけを出し、採点に使う値は runner が書いたとおりに作る。対象の側が「できた」と書いた値では採点しない(場面集の規則 1)。
- **出所の検め**(採点の前。runner が行う): 戦略が受け取った事象の列を返す場面では、受け取った 1 件ごとの物を、p2-iso-* では ISO の文字列を読んだ対象の関数を、p4-visible-at-step では件数と終値を読んだ読み出しを、p4-future-read-attempt では手段ごとの試しを、対象の側が出所として返す。**出所は、場面集の共通の部品(`adapters/common.py`)が物から作った記録だけを受ける**(手で書いた名前・辞書は採点しない)。**「対象の物」と数えるのは、出所のファイルが対象の配布物の置き場所の中にあると示せたときだけ**(置き場所は runner が対象ごとに持つ表 `TARGET_DISTS` から、その対象の環境の import の探索で決める。場面集の名前でないことからは決めない)。示し方は、**型**と**届いた道**の 2 つを別々に示す(型は「対象がその型を持つ」ことしか示さず、「この物を対象が戦略に届けた」ことは示さないため。第 r6-3 回): (a) 型: 物の型を定義したファイル(numpy の行はその dtype、札の付いた物は札の型か札の定数を持つモジュールも)が置き場所にある。`dict`・関数・`datetime`・`DataFrame` のような誰でも作れる型の物は、場面集の側が対象に渡した物・場面集の側が持っている物と同じ物でないこと(対象が作った物)で示す。(b) 届いた道(型を問わず、対象の class の物にも当てる): **対象のコードが戦略の呼び出しに引数として渡した**か、**そうして渡した物の中にあった**(場面集の側の物の属性を通る道は数えない)か、**対象の母語(C・C++ など)のコードが戦略を呼んで渡した**(runner が場面ごとに `sys.setprofile` で走っている母語の関数を記録する)か、**戦略が対象の関数を呼んで返ってきた**(`common.read`・property の読み `common.attr`・反復 `common.iterate`/`common.aiterate`。戦略の呼び出しの中の読みに限る: 読んだ時点の呼び出しの列で、場面集の側の一番外の枠を呼んだのが対象のコードか対象の母語のコードであるか、利用者が自分の回しで対象を動かす対象では adapter の `common.user_loop_call` の塊の中であることを `common.call_context` が記録し、runner がそれを見る。実行が終わってから読んだ物は数えない。第 r8-1 回)か、のどれかが置き場所のコードである。場面の入力を adapter が対象の class で組んで対象に渡し、対象が届けた物は数える(どの対象も場面の入力は adapter が対象の入口の形に直して渡す。記録には `input` と残す)。戦略の呼び出しの中で場面集の側が対象の class を組んだ物・adapter が持つだけで対象に渡していない物は数えない。(c) 読み出しと試しは、戦略の呼び出しの中で行い((b) の読みと同じ記録。第 r8-1 回)、その間に対象のコードが走った(`sys.setprofile` で記録)か、読んだ物が (a)(b) で対象の物か、手段が対象のコードの関数・method、(d) 翻訳した道具(Rust・Go・C・C++)は driver が物から名付けた型・関数の名前が対象の名前の頭で始まる。出所が無い・示せない・場面集の側の型・1 つの型に 2 つの `kind` を写した・読み出しと答えが食い違う・名指し方の一覧が欠ける・名指しの試しの例外が場面集の側の `raise` 文で起きた、のどれかなら、その場面は採点せず「結果なし」にし、理由を残す。
- **再現**: 2 回の実行で同じ / 2 回で違う / 結果なし。
- 良い順(場面集の規則 5): 正解と一致 > 対応なし > 不一致 > 結果なし。正しさが同じなら「2 回の実行で同じ」が上。

## 資料係への申し送り(第 r8-1 回。正の定義 A)

- runner の出力(`survey_results/<設定つき対象>.tsv`)は設定つき対象ごとに 1 つ。ファイルの名の `@` の後ろと `choose` の表の列が選ぶ値、`settings_1` の表の列がその実行の設定の操作の列、`types_1` の表の列が型の組を対象から決める {N438} 場面({L438})でその設定つき対象の持つ型から選んだ型の組。資料係の表を作るスクリプトは、設定つき対象ごとの選ぶ値と型の組をこれらの表の列から materials に写す。
- 比較の表の行「調査結果の側」は、場面ごとに、走らせた設定つき対象の最良を寄せる。新実装・当方の現状・試金石の比較の表の行は、実行の前に決めた 1 つの設定つき対象だけから作る。
- 審査員が読める表の注記に、次の 1 文を必ず出す: 「型の組は対象の持つ型から規則で決めた」。

## 数える物の選択肢(正の定義 A)

{DEF_A}

## 場面にしていない観点・側面

{GRID}
"""


def fmt(v) -> str:
    return "`" + json.dumps(v, ensure_ascii=False) + "`"


def grid_section() -> str:
    """The table of every cell of every viewpoint's range (positive definition C), made by grid_c.py."""
    import grid_c
    rows = grid_c.table(scenes.SCENES)
    ev, see, extra = grid_c.axes()
    reasons: dict[tuple, str] = {}
    lines = ["観点ごとの範囲の升目の全部を、固定した要件(REQUIREMENTS.md)の §1 の要件の表の行と §2 の要件の表の各行の文を切片に切って"
             "書き出した軸(`grid_c.py`・`grid_c_judgments.tsv`)から作った。升目 = 事象 × 見る道(× その観点の追加の軸)。"
             "各升目は「場面にした」(その升目を `covers` に持つ場面)か、「場面にしない」(その観点の測り方の文の外れる語、"
             "またはその升目を名指すリードの決定)か、「未決」(測り方の文の語で決まらない。リードに上げた)のどれか 1 つ。",
             "",
             f"- 事象の軸({len(ev)}): " + " / ".join(ev),
             f"- 見る道({len(see)}): " + " / ".join(see)]
    for (vp, ax), vals in extra.items():
        lines.append(f"- {vp} の {ax}({len(vals)}): " + " / ".join(vals))
    for vp in grid_c.VIEWPOINTS:
        mine = [r for r in rows if r["viewpoint"] == vp]
        counts = {v: sum(1 for r in mine if r["verdict"] == v) for v in ("場面にした", "場面にしない", "未決")}
        lines += ["", f"### {vp}(升目 {len(mine)}: 場面にした {counts['場面にした']} / 場面にしない {counts['場面にしない']} / "
                      f"未決 {counts['未決']})", "", f"測り方の文: 「{grid_c.measure_text(vp)}」", "",
                  "| 事象 | 見る道 | 追加の軸 | 判断 | 場面 / 理由 |", "|---|---|---|---|---|"]
        for r in mine:
            if r["verdict"] == "場面にした":
                what = ", ".join(f"`{i}`" for i in r["scenes"])
            else:
                key = (r["quote"], r["reason"])
                code = reasons.setdefault(key, f"理由{len(reasons) + 1}")
                what = code
            lines.append(f"| {r['event']} | {r['see']} | {r['extra'] or '—'} | {r['verdict']} | {what} |")
    lines += ["", "理由(表の「理由N」):", ""]
    for (q, r), code in reasons.items():
        lines.append(f"- {code}: 引いた語「{q}」。{r}")
    out_axes = sorted({c[0] for s in scenes.SCENES for c in s.covers} - set(ev))
    for k in out_axes:
        lines.append(f"- 軸の外の升目を覆う場面がある: {k}({scenes.OUTSIDE_AXES[k]})。場面: "
                     + ", ".join(f"`{s.id}`" for s in scenes.SCENES if any(c[0] == k for c in s.covers)))
    return "\n".join(lines)


def def_a_section() -> str:
    """The options of positive definition A (ROOTCAUSE_r8-1.md), from the one data both this text and the test grid
    use (`def_axes/jA.tsv` through def_grids.derive; test_battery_def_grids.py runs the grid)."""
    import def_grids
    axes, pairs, problems = def_grids.derive("A")
    assert not problems, problems
    lines = ["場面の結果を対象に帰すかの決まり(ROOTCAUSE_r8-1.md の正の定義 A)を、その段落の切片ごとの判断(`def_axes/jA.tsv`)から"
             "`def_grids.py` が書き出した軸と値。「通る」の値だけからなり、下の条件を全部満たす実行の結果だけを対象に帰す。"
             "同じ物から `test_battery_def_grids.py` が試験の升目を作り、機械(runner と `adapters/common.py`)の答えと照らす。", ""]
    for ax, vals in axes.items():
        lines.append(f"- {ax}: " + " / ".join(f"{v}({e})" for v, e in vals))
    if pairs:
        lines += ["", "条件(満たさなければ落ちる):", ""]
        for a, av, b, bv in pairs:
            lines.append(f"- {a} が {'・'.join(av)} ならば、{b} は {'・'.join(bv)}")
    return "\n".join(lines)


def render() -> str:
    out = [HEAD.replace("{L438}", "・".join(scenes.L438_2_SCENES)).replace("{N438}", str(len(scenes.L438_2_SCENES)))
           .replace("{DEF_A}", def_a_section()).replace("{GRID}", grid_section())]
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
