#!/usr/bin/env python3
"""Write tests/bt/battery/item_4/DEFINITIONS.md from i4_scenes.py (the scenes are the source; this file only prints them)
plus the fixed prose below (rules, judge, table).  Usage: python3 gen_definitions.py  (then check git diff)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import i4_scenes as S  # noqa: E402

OUT = HERE / "DEFINITIONS.md"
TAIL = HERE / "definitions_review.md"  # 提出前の吟味 (hand-written; appended verbatim)

HEAD = """# 項目 4「統合と答え合わせ」— 場面集の定義

場面係が書く(委任文 §3「場面集」「場面集の規則」1〜9、`docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/REQUIREMENTS.md` §2 の観点 I4-1〜I4-20)。
**このファイルは `tests/bt/battery/item_4/gen_definitions.py` が `i4_scenes.py` から作る**(場面の入力と正解は `i4_scenes.py` が唯一の出所。手で直さない。
末尾の「提出前の吟味」だけは `definitions_review.md` を写す)。場面は全部合成で、実データから出た数は 1 つも無い。

- 場面は 2 種類: **値**(その値が正しいか。合成の入力と、対象を見ずに規則から手で出した正解)と **能力**(X ができるか。X を使ったときに出るはずの
  結果を正解として決め、実際に X を使って確かめる)。**どちらも、呼んだ結果を正解と突き合わせる**(規則 1)。「持っている」という申告は数えない。
- 観点ごとに値の場面を 1 つ以上置く(規則 3)。場面にできない観点(I4-7・I4-19・I4-20)は理由を書いて批評家に渡す(末尾の節)。
- 場面は振る舞いを試す(規則 2): 約定の足と値・損益・資産・指標・取り逃しの数・分け方の行・拒んだかどうか。作りの形(型・関数の名)は試さない。
- 各場面は 2 回、別のプロセスで走らせる(`run_battery.py`)。

## 入力の形

`i4_protocol.py` の docstring が全文。要点:

- **op "bars"**(足のバックテスト): `bars`(足の開始の時刻 UTC ns・始値・高値・安値・終値・出来高)、`bar_seconds`、`signals`
  (**戦略**: 足 i の終値の時点で、足 0..i だけを見て BUY / SELL / CLOSE を言う。書かれていない足は HOLD)、`config`(足の模型の選択肢を
  **全部**明示: 元本・発注額・費用 4 つ(taker・maker の手数料率、滑り、スプレッド、どれも %)・執行(taker / maker)・指値の寿命・ショートの可否・
  日率の持ち越し・逆指値 %・利確 %・保有の上限の本数・決済の執行(signal / maker_tp)・maker 利確 %・建てのマスク・建ての向き・逆指値の種類
  (fixed / wick_invalidation)・窓の本数。既定に頼らない)、`model: "spec"`(下の「足の模型の仕様」の結果)または `models: ["legacy", "spec"]`
  (1 つの戦略の記述から、互換の出力と仕様の出力の両方)、`reference: true`(本体と、本体とは別の参照実装の両方)、`want`(返す鍵)。
- **観測**: `fills`(約定ごとに 足・向き OPEN_LONG / OPEN_SHORT / CLOSE_LONG / CLOSE_SHORT・値・数量。取消は約定ではない)、`pnls`(往復ごとの
  実現損益、決済の順)、`equity`(各足の終値の時点の資産)、`metrics`(12 の指標)、`missed_fills`(約定せずに終わった待つ注文の数)。
- **op "metrics"**(決済ごとの損益・資産の列・手数料の合計・1 年の本数 → 12 の指標)、**op "split"**(足と学習・検証の割合 → 3 つの行の位置の列)、
  **op "pipeline"**(ファイルを宣言で 1 回の実行に通す統合の場面。下の「統合の場面」)。

## 足の模型の仕様(場面の正解はこの規則からの手の計算)

規則の文は、互換を求められている既存の足のバックテストの文書(`src/bot/backtest/engine.py` の docstring と注記、`metrics.py`・
`walk_forward.py` の注記)を規則として固定したもの。**正解は既存の実装の出力ではなく、この規則からの手の計算**(委任文 §3「項目 4 の場面」:
既存の実装自身の誤りを正解にしない)。規則の文と既存の実装の計算が違う所は「互換の計算」(L-*)に分けて書く。

- **R-T1**: 足 i の合図は、足 i+1 の始値で taker で約定する(先読みしない)。
- **R-T2**: 最後の足の合図は、次の足が無いので約定しない。
- **R-T3**: BUY は、売り建てがあれば買い戻し、建玉が無ければ買い建てる。SELL は、買い建てがあれば手仕舞い、建玉が無ければショートを許すときだけ
  売り建てる。CLOSE は建玉を閉じ、建玉が無ければ何もしない。建玉は 1 つだけ(反対の合図は閉じるだけで、同じ足で建て直さない)。
- **R-T4**: ショートを許さないとき、建玉の無い SELL は何もしない。
- **R-C1**: taker の約定値 = 基準の値 × (1 ± (スプレッド/2 + 滑り)/100)(買いは +、売りは −)。maker の約定値は指値そのもの(スプレッド・滑りなし)。
- **R-A1**: 数量 = 発注額 / 約定値(建てのとき)。決済は建ての数量。
- **R-A2**: 手数料 = 数量 × 約定値 × 率 / 100。taker の約定は taker の率、指値の約定(maker の建て・利確・maker の利確)は maker の率。
- **R-A3**: 往復の損益 = (決済値 − 建値) × 数量 × 向き − 決済の手数料 − 建ての手数料 − 持ち越し。
- **R-A4**: 足 i の資産 = 元本 + 足 i までに閉じた往復の損益 + 開いている建玉の (足 i の終値 − 建値) × 数量 × 向き − 建ての手数料 − 足 i までの持ち越し。
- **R-M1**(maker の建て): 合図の足の終値に指値を置く。後の足が指値を**厳密に通過**したとき(買いは安値 < 指値、売りは高値 > 指値)だけ、指値の値で
  約定する。触れただけ(安値 = 指値)では約定しない。置いた足では判定しない。
- **R-M2**: 指値は寿命の本数だけ待つ。置いた足 p から数えて p + 寿命 の足で約定しなければ、その足で取り消し、取り逃しに 1 を足す。
- **R-M3**: 待っている指値と反対向きの合図で新しい指値を置くとき、待っていた指値は約定せずに終わり、取り逃しに 1 を足す。
- **R-M4**: CLOSE は建玉を閉じる向きの指値を置く(建玉が無ければ何もしない)。
- **R-P1**(逆指値・利確): 水準は建値 ×(1 ∓ 率/100)(逆指値は不利な向き、利確は有利な向き)。
- **R-P2**: 建てた足では判定しない(建てた足の範囲は建てた時点で分からない)。
- **R-P3**: 逆指値は足の範囲が水準に届けば(買い建てなら安値 ≤ 水準)taker で約定する。値は min(始値, 水準)(買い建て。売り建ては max)を基準に R-C1。
  同じ足で逆指値と利確の両方に届くときは逆指値が先(保守側)。
- **R-P4**: 利確は厳密な通過(買い建てなら高値 > 水準)で、水準の値・maker の率で約定する。
- **R-X1**(maker の利確、exit_execution = maker_tp): 建値 ×(1 ± 率/100)に置いた指値が R-M1 と同じ厳密な通過で、水準の値・maker の率で約定する。
  水準は書かれた 10 進の値どおりに比べる。
- **R-X2**: 建てた足では判定しない。 **R-X3**: maker_tp を選んで率が 0 以下なら拒む。
- **R-W1**(構造的な逆指値、stop_mode = wick_invalidation): 水準 = 約定の足 b より前の完了した N 本(足 b−N〜b−1)の安値の最小(売り建ては高値の最大)。
  約定の足 b 自身は含めない。水準は建てた時に凍結し、動かさない。
- **R-W2**: ヒゲが水準を割っても、終値が割らなければ出ない。 **R-W3**: 終値が水準を越えた(買い建てなら終値 < 水準)足の次の足の始値で taker で出る。
  その足に待っていた合図は捨てる。 **R-W4**: 率の逆指値と重ねない(両方を与えたら拒む)。
- **R-H1**(保有の上限): 足 b で建てた建玉は、ちょうど足 b + N の始値で taker で閉じる。 **R-H2**: その足に待っていた合図は捨てる。
  **R-H3**: 同じ足 b + N で先に見るのは逆指値だけ(保守側)。利確は時間切れより先に取らない。
- **R-E1**(建ての向き): long なら SELL で売り建てない、short なら BUY で買い建てない。 **R-E2**(建てのマスク): 合図の足のマスクが False なら建てない。
  約定の足のマスクは見ない。 **R-E3**: どちらも手仕舞いは止めない。
- **R-S1**(持ち越し): 建玉の間、足 j ごとに |数量| × 足 j−1 の終値 × 日率/100 × (足の秒/86400) を持ち越しとして建玉の費用に足す。
  足 j は 建てた足 < j ≤ 閉じた足(閉じていなければ最後の足)。

## 指標の式(M-1〜M-12)

決済ごとの損益 p(n 件)と資産の列 e から: M-1 総損益 = Σp、M-2 回数 = n、M-3 勝率 = (p > 0 の数)/n × 100(n = 0 なら 0)、
M-4 PF = 勝ちの和 / 負けの和の絶対値(負けが 0 なら、勝ちがあれば無限大、無ければ 0)、M-5 シャープ = e の足ごとの変化率 r の平均 / r の標本標準偏差
(n−1 で割る)× √(1 年の本数)(r が 2 個以上で標準偏差 > 0 のとき。ほかは 0)。**1 年の本数は足の頻度で決まる = 365 × 86400 / 足の秒**
(op "metrics" では入力の periods_per_year)。M-6 最大下落 % = max((その時点までの最大 − e)/ その時点までの最大 × 100)、
M-7 最大連敗 = p < 0 の連続の最大(0 は連続を切る)、M-8 平均勝ち = p > 0 の平均(無ければ 0)、M-9 平均負け = p < 0 の平均(負の値。無ければ 0)、
M-10 RR = 平均勝ち / |平均負け|(平均負けが 0 なら 0)、M-11 期待値 = Σp / n(n = 0 なら 0)、M-12 手数料の合計 = 手数料と持ち越しの合計
(op "metrics" では入力の値そのまま)。

## 分け方(D-1・D-2)

- **D-1**: n 行を並べ替えず重ねず、学習 = 先頭 floor(n × 学習の割合) 行、検証 = そこから floor(n × (学習 + 検証の割合)) 行目まで、検証外 = 残り(末尾)。
  割合は書かれた 10 進の値どおりに計算する。
- **D-2**: 割合はどちらも (0, 1) にあり、和は 1 未満。外れたら拒む。

## 互換の計算(L-1〜L-4。「互換の出力」の場面の正解)

規則の文とは別に、既存の実装が計算している値。互換の口(旧と同じ名前・同じ引数で旧と同じ出力)が出すべき値として、2 つの出力の場面(`models`)の
「legacy」の正解に使う。

- **L-1**: 保有の上限の足 b + N で利確の水準も通るとき、利確を時間切れより先に取る(水準の値・maker の率)。
- **L-2**: 足のバックテストのシャープの年率化で、足の頻度を見ず 1 年 = 525600 本とする。
- **L-3**: 分け方の境を 2 進の浮動小数で計算する: 検証の終わり = int(n × (学習 + 検証))(0.7 + 0.2 = 0.8999999999999999)。
- **L-4**: 利確の水準を 2 進の浮動小数の積で置く(100 × 1.015 = 101.49999999999999)。

## 統合の場面(I4-5・I4-6)

- 合成のファイル 6 本を場面の root の下に書き、**宣言(spec)**と一緒に渡す(形は項目 1 の宣言の形): 暗号資産の約定(CSV・ISO の時刻)、同じ銘柄の板の
  上位 10 段(CSV)、aggTrades の形(見出し無し CSV・ms の時刻)、FX のイベントティック(気配の CSV)、JPX の 1 分足(日付と時刻の 2 列・Asia/Tokyo)、
  FX の 1 分足(UTC)。各データに `origin: "real"`(実データとして扱う)。
- 銘柄 5 つ(bf = 約定 + 板を添える、binance、fx_tick、jpx、fx_1m)を**1 回の実行**で通す。戦略は時刻だけで決まる固定の手順
  (2026-01-05 00:00 UTC に 1 単位買い、00:05 に売り、01:00 に買い、01:05 に売り)。費用は全部 0、遅れ 0。
- **F-1**(約定の規則): 注文の時刻以後に最初に観測した値で約定する。約定は約定の値、気配は買いなら ask・売りなら bid、足はその足の始値。
- 観測: `fills`(銘柄ごとに 時刻 t_ns・向き・値・数量)、`pnl`(銘柄ごとの 売り − 買い の和)、`events_read`(データごとの読んだ事象の数)、
  `run_record`(目的・読んだファイルの sha256 を場面の path ごと)、`export`(目的・銘柄ごとの往復の数)、`dashboard`(その実行の表示の全タブを
  {"label", "text"} で)。
- 目的「動作確認」の実行では、指標の書き出しに目的が載り、ダッシュボードの**全タブ**に注記「動作確認の実行。相場の結論には使わない」が出る(委任文 §4)。
  値で条件づけた戦略を目的「動作確認」で実データに通す実行と、目的「研究」を事前登録のハッシュ無しで作る実行は拒む(委任文 §4)。

## 判定の決まり(`i4_judge.py`)

- 数は |a − b| ≤ 1e-9 × max(1, |a|, |b|) で等しいとする(計算の順の違いで最後の桁が違うことがある)。無限大は無限大とだけ等しい。整数は完全一致。
- fills: 件数と順が同じで、判定する欄(足と向きは完全一致、値と数量は数として)が全部等しい。pnls・equity: 長さが同じで要素ごとに等しい。
  metrics: 12 の鍵が全部あり等しい。missed_fills: 整数が等しい。splits: 3 つの行の位置の列が等しい。
- 統合の場面: 銘柄ごとの約定が時刻(完全一致)・向き・値・数量で等しい。pnl は数として、events_read は整数で等しい。run_record は目的が等しく、
  正解の path ごとの sha256 が等しい(ほかの path があってもよい)。export は目的と往復の数が等しい。dashboard は正解のタブの名それぞれで
  **始まる**タブがちょうど 1 つあり、**全タブ**の本文に注記の文がある。
- engine / reference / legacy / spec の入れ子は、それぞれを同じ決まりで判定する。
- 性質の場面(I4-2)は、30 の場合それぞれを上の決まりで判定し、さらに不変条件(建てと決済が交互・決済の数量 = 建ての数量・向きが同じ・損益の
  恒等式 R-A3・資産の恒等式 R-A4・約定の前の足に合図がある)を観測した約定から式で検める。1 つでも崩れたら不一致。
- 変形(`variant`)のある能力の場面: 対照が正解と一致し、**かつ**変形を対象が拒んだとき「正解と一致」。変形を通したら「不一致」。

## 表の作り(資料係)

- セルは 2 つの欄: **正しさ** = 正解と一致 / 対応なし(対象が拒んだ・例外を出した)/ 不一致(値)/ 結果なし(渡す口が無い・走らなかった)、
  **再現** = 2 回の実行で同じ / 2 回で違う(値)/ 結果なし。
- **「最も良い結果」の順**(規則 5): 正解と一致 > 対応なし > 不一致 > 結果なし。正しさが同じなら「2 回の実行で同じ」を上に置く。調査結果の側は
  場面ごとに、動かせた道具(と再現)のうち最も良い結果を 1 行に寄せる。
- 観点ごとに一致の数を出し(規則 3)、審査員には観点ごとに比べさせる。

"""


def fmt(x):
    if isinstance(x, float):
        r = repr(x)
        return r
    return json.dumps(x, ensure_ascii=False)


def bars_block(bars):
    rows = [f"{i}: {b['open']:g} / {b['high']:g} / {b['low']:g} / {b['close']:g}" for i, b in enumerate(bars)]
    return "足(番号: 始値 / 高値 / 安値 / 終値)= " + "; ".join(rows)


def cfg_nondefault(c):
    base = S.cfg()
    out = {k: v for k, v in c.items() if v != base[k]}
    return json.dumps(out, ensure_ascii=False)


def describe_input(inp):
    op = inp["op"]
    if op == "bars":
        parts = [f"op bars、足の秒 {inp['bar_seconds']}", bars_block(inp["bars"]),
                 "合図 = " + (", ".join(f"{s['signal']}@{s['bar']}" for s in inp["signals"]) or "なし"),
                 "config(既定との違いだけ。場面は全部の鍵を明示して渡す)= " + cfg_nondefault(inp["config"]),
                 f"返す鍵 = {inp['want']}"]
        if "models" in inp:
            parts.append(f"models = {inp['models']}")
        if inp.get("reference"):
            parts.append("reference = true")
        return "<br>".join(parts)
    if op == "metrics":
        return f"op metrics、損益 = {inp['trade_pnls']}、資産 = {inp['equity']}、手数料の合計 = {inp['total_fees']}、1 年の本数 = {inp['periods_per_year']}"
    if op == "split":
        s = f"op split、{len(inp['bars'])} 行、学習 {inp['train_frac']}・検証 {inp['val_frac']}"
        return s + (f"、models = {inp['models']}" if "models" in inp else "")
    if op == "pipeline":
        files = "; ".join(f"{f['path']}({f['text'].count(chr(10))} 行)" for f in inp["files"])
        return (f"op pipeline、ファイル = {files}、銘柄 = {[i['name'] for i in inp['instruments']]}、戦略 = {json.dumps(inp['strategy'], ensure_ascii=False)}、"
                f"目的 = {inp['purpose']}、事前登録のハッシュ = {inp['prereg_sha256']}、返す鍵 = {inp['want']}")
    return json.dumps(inp, ensure_ascii=False)


def describe_expect(exp, depth=0):
    if isinstance(exp, dict) and ("legacy" in exp or "engine" in exp):
        return "<br>".join(f"**{k}**: " + describe_expect(v, depth + 1) for k, v in exp.items())
    parts = []
    for k, v in exp.items():
        if k == "fills" and isinstance(v, list):
            parts.append("約定 = " + ("; ".join(f"足 {f['bar']} {f['side']} 値 {fmt(f['price'])} 数量 {fmt(f['size'])}" for f in v) or "なし"))
        elif k == "fills" and isinstance(v, dict):
            parts.append("約定 = " + "; ".join(f"{inst}: " + ", ".join(f"{f['side']} t_ns {f['t_ns']} 値 {fmt(f['px'])}" for f in fl)
                                             for inst, fl in v.items()))
        elif k == "metrics":
            parts.append("指標 = " + ", ".join(f"{m} {fmt(x)}" for m, x in v.items()))
        else:
            parts.append(f"{k} = {json.dumps(v, ensure_ascii=False, default=str) if not isinstance(v, float) else fmt(v)}")
    return "<br>".join(parts)


def main():
    lines = [HEAD]
    lines.append("## 観点ごとの場面\n")
    for vp, title in S.VIEWPOINTS.items():
        sc = [s for s in S.SCENES if s["viewpoint"] == vp]
        lines.append(f"### 観点 {vp} {title}\n")
        if not sc:
            lines.append(f"場面にできない観点: {S.NOT_SCENES[vp]}\n")
            continue
        for s in sc:
            lines.append(f"#### {s['id']}({s['kind']})\n")
            lines.append(f"- **何を測るか**: {s['what']}")
            lines.append(f"- **正解の出し方**: {s['how']}")
            if "cases" in s:
                c0 = s["cases"][0]
                lines.append(f"- **入力**: {len(s['cases'])} の場合(`i4_scenes.grid_cases(seed=20260926, n=30)` が引く)。例: 場合 0 = "
                             + describe_input(c0).replace("<br>", " / "))
                lines.append(f"- **期待**: 各場合の約定・損益・資産が R-T1〜R-T4・R-A の計算と一致し、不変条件が 1 つも崩れない。例: 場合 0 = "
                             + describe_expect(s["expect"][0]).replace("<br>", " / "))
            else:
                lines.append("- **入力**: " + describe_input(s["input"]).replace("<br>", " / "))
                lines.append("- **期待**: " + describe_expect(s["expect"]).replace("<br>", " / "))
                if "variant" in s:
                    lines.append("- **変形(拒むのが正解)**: " + describe_input(s["variant"]).replace("<br>", " / "))
            lines.append(f"- **判定する鍵**: {json.dumps(s['judge'], ensure_ascii=False)}")
            lines.append("")
    lines.append("## 場面にできない観点(批評家が見る)\n")
    for vp, why in S.NOT_SCENES.items():
        lines.append(f"- **{vp} {S.VIEWPOINTS[vp]}**: {why}")
    lines.append("")
    if TAIL.exists():
        lines.append(TAIL.read_text(encoding="utf-8"))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({sum(1 for _ in OUT.open(encoding='utf-8'))} lines)")


if __name__ == "__main__":
    main()
