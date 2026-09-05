# QA known-answer packet (generation 4, CODE-AS-CLAIM, maker fill model) -- claims for auditors

Method change from generation 3 (docs/QA/known_answer_results_2026-09-05.md §6,
docs/AUDIT_2026-09/PROTOCOL.md "Maker fill-model claims"): blind re-implementation of the fill
rule from prose alone was not reproducible across three auditors. For this packet, the fill
simulator CODE is part of the claim.

約定規則の実装は scripts/qa/maker_fill_ref_packet.py(監査者は閲覧可。これ以外の scripts/qa/ 配下は禁止)。そのファイル冒頭の RULE_DECISIONS がこのパケットにおける規則の確定版。

Your job (per PROTOCOL.md): (a) code review -- does scripts/qa/maker_fill_ref_packet.py implement
the rule text below and its own RULE_DECISIONS list; list every place it decides something the
rule text does not say; (b) verify the code on the 8 micro-tapes under
`backtest_data/qa_known_answer_maker4_20260905/micro/` (each exercises one decision; hand-computed
answers are in `expected_<letter>.json`, derived step by step in `HAND_DERIVATION_<letter>.md`
BEFORE running any code -- compute your own answer by hand first, then compare); (c) re-run the
code on the full tape (reused from `backtest_data/qa_known_answer_maker3_v3_20260905/`, unchanged)
and reproduce the numbers below; (d) an independent re-implementation is used only on the
micro-tapes.

## 約定規則(すべての主張に共通)

resting order joins the back of the displayed queue at insertion; it fills when cumulative
executions at its price on its side since insertion exceed queue-ahead + own size, or partially
per FIFO; cancelled and re-joined at the new best when the touch moves away; after our own fill,
the OPPOSITE-side exit order is a NEW order inserted at the back of the displayed queue AT THAT
MOMENT (queue-ahead = displayed size at insertion, minus own size, since the displayed size at
insertion already includes our own just-joined clip); each entry has its own exit order, there is
no netting across positions, and at most one open position per side at a time (a new entry quote
on a side is placed only when that side has no open position); ticker rows are written AFTER the
execution(s) at that same timestamp are applied (post-trade); positions = completed entry fills;
forced exits at the 300 s cap cross EXACTLY at the displayed public touch at exit time -- no
additional slippage is modelled.

own_size = 0.05, cap = 300 s, tick = 10.0 (same instrument/tape as generation 3 v3).

## QA4-1

母集団=S1(最良気配で対称的に両建て quote、300秒 cap)の完了建玉。上記の約定規則の下でネット =
+1.15bps/往復 (t=9.05)。正かつ有意である。

## QA4-2

母集団=S1と同じ建玉群だが、約定規則を『挿入後に自分の価格・サイドで最初に印字された執行を無条件に
約定とみなす(キュー先行量を無視)』に置き換えて PUBLIC テープを再生した場合、ネット =
+0.84bps/往復 (t=76.59) となる。これは上記の約定規則(正しい規則)の下でのネット +1.15bps/往復
(t=9.05) と比べて楽観的でもなければ、無条件に「取引可能なエッジ」を結論できるものでもない --
この母集団では素朴なキュー無視モデルはむしろ真のルールより悲観的である。

## QA4-3

母集団=S2(スプレッド2tick以上のとき最良気配より1tick内側に improve して両建て quote、それ以外は
最良気配、300秒 cap)の完了建玉。上記と同じ約定規則の下でネット = +0.77bps/往復 (t=4.15)。正かつ
有意である。

## QA4-4

母集団=S1(上記の約定規則)のエントリー約定(参入 leg のみ)。5秒地点の逆選択(adverse selection、
エントリー約定直後の mid の変化を符号調整したもの。符号規約: 正 = ポジションに有利な方向への変化。
scripts/qa/maker_fill_ref_packet.py の RULE_DECISIONS 参照)は -0.61bps (t=-21.36) であり、ゼロと明確に
区別できる(不利な方向)。

## QA4-5

母集団=S1(上記の約定規則)の完了建玉。300秒 cap に到達し taker として決済された(forced exit)
建玉の比率は 55.0% である。

## QA4-6

このシミュレータ(scripts/qa/maker_fill_ref_packet.py)の RULE_DECISIONS が確定させた規則の下で、v3 パケット
(backtest_data/qa_known_answer_maker3_v3_20260905/)の公開ファイルを再生した数値(QA4-1/3/5)は、
v3 自身が封印した数値(S1 net +0.30bps t2.79, forced 44.6%)と一致しない。これは規則の文章が
複数の(このパケットが明示的に決定した)解釈を許すことの直接証拠であり、両者の不一致自体は
バグではない(docs/QA/answers_sealed_maker4.json の comparison_to_v3_sealed_numbers 参照)。

## 既知の欠陥(この監査ラウンド用に意図的に混入)

scripts/qa/maker_fill_ref_packet.py には 1 行の意図的な欠陥がある(docs/QA/answers_sealed_maker4.json
の `planted_defect` に記録)。監査手順 (a)(b) で発見できるはずである。
