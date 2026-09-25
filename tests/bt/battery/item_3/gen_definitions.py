#!/usr/bin/env python3
"""Write tests/bt/battery/item_3/DEFINITIONS.md from the scenes (i3_scenes.py) and the review text.

    python3 tests/bt/battery/item_3/gen_definitions.py

The scene part is generated so that the document and the scenes can never disagree: every
scene's id, viewpoint, kind, what it measures, its input (small fields in full, long lists
by length, first and last values, and the sha256 of the whole input), its expected answer
and how that answer was derived come from the scene itself.  The header and the pre-delivery
review (提出前の吟味) are the fixed texts HEADER and REVIEW below.  No tool name is written.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import i3_scenes as S  # noqa: E402

HEADER = """# 項目 3「検証・再現・出力」の場面集 — 定義

場面係が書く(委任文 §3「場面集」「場面集の規則」1〜9)。この文書は `gen_definitions.py` が `i3_scenes.py` から作る。
場面の節は手で直さない(直すなら場面を直して作り直す)。道具の名前は書かない。

## 0. 何をどう比べるか

- 観点は固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/REQUIREMENTS.md` §2 の C3-1〜C3-19。場面は観点ごとに並べ、
  **どの観点にも値の場面を 1 つ以上**置いた(規則 3)。場面の数で観点の重みが決まらないよう、表は観点ごとに一致の数をまとめる。
- **値の場面** = その値が正しいか。合成の入力と、エンジンを見ずに閉じた式・手計算・入力の数え上げで出した正解。
  **能力の場面** = X ができるか。X を使ったときに出るはずの観測できる結果(正解)を決めておき、実際に呼んで突き合わせる(規則 1)。
  「持っている」という申告や、関数・欄の名前があることは数えない。
- 対照と変形: 「拒む」ことが正解の場面は、対照(正しく通るはずの要求)と変形(拒むのが正解の要求)の 2 つを出す。
  対照が正解と一致したときだけ変形を出し、変形の結果で場面の正しさを決める。対照を通せない対象は、変形を拒んでも正解にならない
  (何でも拒む対象が「正解」を取れないようにするため)。
- 振る舞いを見る(規則 2): 要求は宣言(入力の値と規則)だけを渡し、対象の関数の名前や作りを決めない。観測の形が 2 通りありうるもの
  (区分を行で返すか半開区間の境界で返すか)は両方を受け、判定の側が同じものに直して比べる。

## 1. 正しさと再現の欄(資料係の表のセル)

- **正しさ**(良い順。規則 5): 正解と一致 > 対応なし(対象が明示的に拒む・例外を出す)> 不一致(黙って違う値を返す)> 結果なし
  (対象に渡せなかった・欄が無い・時間切れ)。正解の欄が複数ある場面では、ある欄の値が違えば「不一致」(黙った誤りが最も悪い)、
  ある欄はすべて合っていて欠けた欄があれば「結果なし」。
- **再現**: 同じ場面を別のプロセスで 2 回走らせ、正しさの分類と、観測の要約(sha256 の頭 16 桁)が同じなら「2 回の実行で同じ」。
  要約の前に、2 回の間で正当に変わりうる値(リポジトリの HEAD の SHA・作業木の差分のハッシュ・実行 ID の文字列そのもの・
  1 回ごとの作業の置き場の path)を、出てきた順の札(`<git_sha0>`・`<run_id0>` など)に置き換える。等しさの関係(どれとどれが同じか)は
  札で保たれるので、実行 ID の決定性は v8-run-id の関係で見る。

## 2. 走らせ方

- `python3 tests/bt/battery/item_3/run_battery.py --target <対象> --out <表.tsv>`(対象の一覧は `--list-targets`)。
  場面ごとに新しい作業の置き場を作り、要求のファイルを書き、終わったら消す。1 場面の時間の上限 300 秒、1 回の実行の上限 3600 秒。
- 要求と観測の形は `i3_protocol.py`(op ごとの観測の欄)。新実装の adapter(`adapters/new_impl.py`)は口だけで、本体は資料係が毎周書く。
- 試金石: `mutant.py`(新実装を包み、1 か所だけ誤らせる。何を誤らせたかは MUTANT の文)。
- 配線の場面の壊し具: `wiring_break/sitecustomize.py`(環境変数 I3_WIRING_BREAK があるときだけ、標準の http.server の上で効く)。
- 場面にできない部分(批評家が見る): 作業木の差分が変わったときに差分のハッシュが変わること(リポジトリを書き換えないため)。
  画面の見た目(色・配置)。

## 3. 観点と場面の一覧

"""

REVIEW = """
## 提出前の吟味(場面係の最初の作り。委任文 §3「提出前の吟味」、L-433)

固定した要件 §2 の C3-1〜C3-19・場面集の規則 1〜9・比較の観点を読み直し、非常に厳しい監査役・批評家なら何を [止める] に
するかを観点ごとに列べ、返す前に潰した。潰せなかったものは最後に残りとして書く。

1. **規則 1(能力の場面も正解と突き合わせる)**: 能力の場面(a1・a2・a4・a6・a7・a9・a10・a15・a16・a17・a18)はすべて、
   呼んだ結果を決めておいた正解と比べる。「拒む」が正解の場面は対照と変形の組にし、対照を通せない対象は変形を拒んでも正解に
   しない(`run_battery.py` の classify)。能力の申告・関数の有無は数えない。→ 潰した。
2. **規則 2(振る舞いを試し、作りの形を試さない)**: 区分は行でも境界でも受け、判定の側で同じものに直す。実行記録は欄の値で見て、
   ファイルの形は問わない。画面は配った中身(HTML・API)から読むことを求め、関数の名前は決めない。→ 潰した。
   残る決め: 観測の欄の名前(i3_protocol.py)は場面係が決めた口で、adapter が対象の出力をその名前に入れ替える(値の計算はしない)。
3. **規則 3(観点ごとにまとめ、各観点に値の場面)**: `test_battery_item3.py` が C3-1〜C3-19 のそれぞれに値の場面が 1 つ以上あることを
   機械で確かめる。この試験が最初の版で C3-9 に値の場面が無いこと(a9 の能力の場面だけ)を見つけたので、種つきの乱数の実行が 2 回で
   一致すると判定されるかを値で見る v9-seeded-repro を足した。→ 潰した。
4. **規則 4(動かせた道具は全部の場面に通す)**: 動かせた道具と再現は全部の場面に通し(`survey_results/opp_*.tsv` はどれも全場面の行を持つ)、
   渡せない場面は adapter が「何を探し、どこに無かったか」(道具のコードの grep = `opponents/SEARCH.tsv` と、当たりが口でない理由の行)を
   注記に残す。時間の打ち切りは 1 件も無い(1 場面の最長は当方の現状の配線の試験の 7.5 秒。`survey_results/*.tsv` の secs の列)。
   途中でリードの容量の片付け(2026-09-25 18:28 UTC、commit 08aaad4)が調査結果の側の 2 件の実行ファイル・インタプリタを消した。
   どちらも道具を読み込まずに全部の要求が「口が無い」で終わる adapter なので、最後の走行は既定のインタプリタで行い、実行ファイルの方は
   消える前に打った使い方の出力を根拠にした(どの候補かは `opponents/RUNNABILITY.tsv`・`opponents/attempts/`)。→ 潰した(経緯は記録に残した)。
5. **規則 5(最も良い結果の順)**: 判定と表の順はこの文書 §1 のとおり。複数の欄の場面で、合っている欄と欠けた欄が混ざるときの扱いを
   決めた(ある欄が違えば不一致、合っている欄だけなら結果なし)。→ 潰した。
6. **規則 6・9(検討表)**: 動かせなかった候補は観点ごとに全部を `opponents/CONSIDERED.md` に載せ、`scripts/check_bt_considered.py --write`
   で誤り 0 件にした。一次資料が読めた候補は (b) で読んで判断した。→ 潰した。
7. **規則 7(置き場)**: 場面集の試験は `tests/bt/battery/item_3/` にだけ置いた。`src/` と他の項目のファイルに触れていない
   (`git status --short` で確かめる)。→ 潰した。
8. **根拠のない設定値(A-12)**: 許容はすべて出し方を場面に書いた。閉じた式の場面(MDE・DSR)は数値の実装の差だけを許す 1e-6。
   収益の系列の DSR は、論文どおりの実装が選びうる流儀(SR の標準偏差の ddof・歪度と尖度の補正)の 4 通りで値が動く幅を許容にした。
   ブロック・ブートストラップの帯(0.85〜1.15 倍、中点 0.25 標準誤差)は、再抽出 2000 回の乱数の揺れ(分散の相対の揺れ √(2/2000) ≈ 3%、
   標準誤差で約 1.6%)と、ブロックの作り方の違い(円環 / 端を切る / 長さを乱数で決める)の差(系列の長さに対するブロックの長さ
   20 / 2000 = 1% の桁)を覆い、1 点ずつの再抽出(正解の 0.54 倍)を確実に外す幅として置いた。最初の版で DSR に置いた許容 0.002 は
   根拠が無く、式の項を落とした実装を通してしまったので外した(この吟味で見つけた)。→ 潰した。
9. **新実装に有利な偏り**: 積率だけを渡す DSR(v5-dsr)は、収益の系列だけを受ける実装を測れない。系列を渡す v5-dsr-returns を足した。
   walk-forward は「学習 5 日・評価 2 日」の形だけだと等幅の窓しか持たない実装を測れないので、等幅の v1-wf-equal を足した。
   markout は向きが片方の実装を測れるよう、買いと売りを別の場面にした。→ 潰した。
10. **断定と範囲(O-2・O-3)**: adapter の「口が無い」の文は、打った grep のコマンドと当たりの数(`SEARCH.tsv`)か、行を引いて書いた。
    当方の現状の adapter の文の grep は打ち直して確かめ、`deflat` の当たり 5 件(gzip の deflate)と `overfitting` の当たり 2 件
    (説明文)を最初の版の「当たり 0」から直した。→ 潰した。
11. **再現の欄の機械(規則 5 の再現の欄)**: 2 回の間で正当に変わる値(HEAD・差分のハッシュ・実行 ID)を札に置き換える処理が、最初の版では
    観測を文字列にしてから置き換えていたため、短い値が鍵の名まで書き換えた。試験(test_stable_view_keeps_equality_of_run_ids)で見つけ、
    値と鍵を 1 つずつ置き換える形に直した。→ 潰した。
12. **試金石**: `mutant.py` は purge だけを外す(ラベルの終わりを行の始まりに潰す)。独立に書いた正しい実装を包んだとき、v2-purge-embargo と
    v2-cpcv-split だけが不一致になり、ほかの要求は変わらないことを試験で確かめた(test_mutant_breaks_exactly_the_declared_scenes)。→ 潰した。

残り(この周で潰せなかったもの。批評家に見てもらう):
- 画面の場面(v16〜v19・a16・a17)は、画面をスクリプトが描く作りだと、adapter がスクリプトを実行して描かれた文を読む必要がある。
  場面は「配った中身から読む」までを決め、読み方は adapter(資料係)に任せた。
- 差分のハッシュが作業木の変化で変わることは場面にしていない(§2)。
"""


def _short(v, depth=0):
    if isinstance(v, list):
        if len(v) > 8 or any(isinstance(x, (list, dict)) for x in v) and len(json.dumps(v, ensure_ascii=False)) > 300:
            return f"[{len(v)} 個: 最初 {json.dumps(v[0], ensure_ascii=False)[:80]}、最後 {json.dumps(v[-1], ensure_ascii=False)[:80]}]"
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_short(x, depth + 1)}" for k, x in v.items()) + "}"
    if isinstance(v, str) and len(v) > 120:
        return json.dumps(v[:60] + f"…({len(v)} 文字)", ensure_ascii=False)
    return json.dumps(v, ensure_ascii=False)


def _files(inp):
    out = []
    for f in inp.get("files", []):
        if "text" in f:
            out.append(f"`{f['path']}`({len(f['text'].encode('utf-8'))} バイト、sha256 {hashlib.sha256(f['text'].encode('utf-8')).hexdigest()[:16]}…)")
        else:
            out.append(f"`{f['path']}`(リポジトリの `{f['copy_from_repo']}` の写し)")
    return "、".join(out)


def _input_text(inp):
    fields = {k: v for k, v in inp.items() if k != "files"}
    digest = hashlib.sha256(json.dumps(inp, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    t = f"`{_short(fields)}`"
    if inp.get("files"):
        t += f"。ファイル: {_files(inp)}"
    return t + f"。要求全体の sha256 の頭 {digest}"


def _expect_text(sc):
    e = sc["expect"]
    c = e["check"]
    if c in ("parts", "folds"):
        body = {k: f"{len(v)} 行" for k, v in e["parts"].items()} if c == "parts" else [
            {k: f"{len(v)} 行(最初 {v[0] if v else '-'})" for k, v in f.items()} for f in e["folds"]]
        t = f"区分ごとの行: {json.dumps(body, ensure_ascii=False)}(行の時刻の列そのものが正解)"
    else:
        t = "`" + _short({k: v for k, v in e.items() if k != "check"}) + f"`(判定の規則: {c})"
    if "variant" in sc:
        t += f"。変形の要求: `{_short({k: v for k, v in sc['variant'].items() if k != 'files'})}`、変形の正解: `{_short(sc['variant_expect'])}`"
    return t


def main() -> int:
    lines = [HEADER]
    lines.append("| 観点 | 要件の語 | 値の場面 | 能力の場面 |")
    lines.append("|---|---|---|---|")
    for vp, name in S.VIEWPOINTS.items():
        vs = [s["id"] for s in S.SCENES if s["viewpoint"] == vp and s["kind"] == "値"]
        cs = [s["id"] for s in S.SCENES if s["viewpoint"] == vp and s["kind"] == "能力"]
        lines.append(f"| {vp} | {name} | {'・'.join(vs) or '—'} | {'・'.join(cs) or '—'} |")
    lines.append(f"\n場面は全部で {len(S.SCENES)}(値 {sum(s['kind'] == '値' for s in S.SCENES)}・能力 {sum(s['kind'] == '能力' for s in S.SCENES)})。\n")
    lines.append("## 4. 場面ごとの定義(入力 / 期待 / 何を測るか / 正解の出し方)\n")
    cur = None
    for s in S.SCENES:
        if s["viewpoint"] != cur:
            cur = s["viewpoint"]
            lines.append(f"### {cur} {S.VIEWPOINTS[cur]}\n")
        lines.append(f"#### {s['id']}({s['kind']}の場面)\n")
        lines.append(f"- **何を測るか**: {s['measures']}")
        lines.append(f"- **入力**: {_input_text(s['input'])}")
        lines.append(f"- **期待**: {_expect_text(s)}")
        lines.append(f"- **正解の出し方**: {s['how']}\n")
    lines.append(REVIEW)
    (HERE / "DEFINITIONS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"DEFINITIONS.md: {len(S.SCENES)} scenes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
