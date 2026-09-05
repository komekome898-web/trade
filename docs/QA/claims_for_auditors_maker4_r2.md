# QA known-answer packet (generation 4, CODE-AS-CLAIM, maker fill model) -- round 2 -- claims for auditors

Method (docs/AUDIT_2026-09/PROTOCOL.md "Maker fill-model claims"): the fill simulator CODE is part
of the claim.

約定規則の実装は scripts/qa/maker_fill_ref_packet_r2.py(監査者は閲覧可。これ以外の scripts/qa/ 配下は禁止)。そのファイル冒頭の RULE_DECISIONS がこのパケットにおける規則の確定版。

Your job (per PROTOCOL.md): (a) code review -- does scripts/qa/maker_fill_ref_packet_r2.py implement
the rule text below and its own RULE_DECISIONS list; list every place it decides something the
rule text does not say; (b) verify the code on the 9 micro-tapes under
`backtest_data/qa_known_answer_maker4_r2_20260905/micro/` (each exercises one decision; hand-computed
answers are in `expected_<letter>.json`, derived step by step in `HAND_DERIVATION_<letter>.md`
BEFORE running any code -- compute your own answer by hand first, then compare); (c) re-run the
code on the full tape (reused from `backtest_data/qa_known_answer_maker3_v3_20260905/`, unchanged)
and reproduce the numbers below; (d) an independent re-implementation is used only on the
micro-tapes.

## 約定規則(すべての主張に共通)

resting order joins the back of the displayed queue at insertion; it fills when cumulative
executions at its price on its side since insertion exceed queue-ahead + own size, or partially
per FIFO; cancelled and re-joined at the new best when the touch moves away, with cumulative
progress reset to zero on rejoin; after our own fill, the OPPOSITE-side exit order is a NEW order
inserted at the back of the displayed queue AT THAT MOMENT (queue-ahead = displayed size at
insertion, minus own size, since the displayed size at insertion already includes our own
just-joined clip); each entry has its own exit order, there is no netting across positions, and at
most one open position per side at a time (a new entry quote on a side is placed only when that
side has no open position); ticker rows are written AFTER the execution(s) at that same timestamp
are applied (post-trade); positions = completed entry fills; forced exits at the 300 s cap are a
TAKER cross that closes out at the touch on the position's own (unfavourable) side -- a long
force-sells into the bid, a short force-buys into the ask -- no additional slippage is modelled.

own_size = 0.05, cap = 300 s, tick = 10.0 (same instrument/tape as generation 3 v3).

## QA4R2-1

母集団=S1(最良気配で対称的に両建て quote、300秒 cap)の完了建玉、n=952。上記の約定規則の下でネット =
+0.17bps/往復 (t=1.42)。符号は正だが、有意水準でゼロと明確に区別できるとは言えない(t<2)。

## QA4R2-2

母集団=S1と同じ quoting ロジックだが、約定規則を『挿入後に自分の価格・サイドで最初に印字された執行を
無条件に約定とみなす(キュー先行量を無視)』に置き換えて同じ PUBLIC テープを再生した場合の完了建玉
(naive)。これは S1 とは**別の母集団**である: naive の完了建玉数は n=11,936、S1 は n=952(12.5倍)。
naive のネットは +0.84bps/往復 (t=76.59)。1 往復あたりの平均だけを見ると近い値に見えるが、この母集団
では試行回数が全く異なるため、5 日間の集計エッジ(建玉数 × 平均)で比較すると naive は S1 のおよそ 61
倍に達する。すなわち naive(キュー無視)モデルは S1 の正しい規則よりも**楽観的**であり、悲観的でも
中立でもない。

## QA4R2-3

母集団=S2(スプレッド2tick以上のとき最良気配より1tick内側に improve して両建て quote、それ以外は
最良気配、300秒 cap)の完了建玉、n=370。上記と同じ約定規則の下でネット = −0.16bps/往復 (t=−0.87)。
符号は負だが、S1 同様、有意水準でゼロと明確に区別できるとは言えない。

## QA4R2-4

母集団=S1(上記の約定規則)のエントリー約定(参入 leg のみ)、n=952。5秒地点の逆選択(adverse
selection、エントリー約定直後の mid の変化を符号調整したもの。符号規約: 正 = ポジションに有利な方向
への変化。scripts/qa/maker_fill_ref_packet_r2.py の RULE_DECISIONS 参照)は −0.61bps (t=−21.93) で
あり、ゼロと明確に区別できる(不利な方向)。

## QA4R2-5

母集団=S1(上記の約定規則)の完了建玉、n=952。300秒 cap に到達し taker として決済された(forced
exit)建玉の比率は 46.6% (444/952) である。
