# バックテスト環境 12 回目の起動(run `wf_f93df86b-dab`)の記録

## 14:20 UTC 起動 → 15:05 UTC にリードが読んだ結果(逐語の抜き書きは journal `wf_f93df86b-dab/journal.jsonl`)

| label | 結果 |
|---|---|
| 要件:1 | **着手を保留(HALT)**。返した path は scratchpad の `item1_materials_HALT_20260925.md`。理由(逐語): 「ハーネスが中継したオーナーの原文『は？？？案1みたいなこと前に承認しましたよね？なぜあいもかわらず無限の無意味な作業を続けてるんですか？』」を唯一のユーザーの声と読み、委任と食い違うとして止めた |
| 要件:3 | 同じ理由で中断(`item3_halt_20260925.md`) |
| 要件:2 | 完了。`docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/REQUIREMENTS.md`(C2-1〜) |
| 場面:1 / 場面:3 | 「固定した要件」として渡されたファイルが要件でなく保留の記録だったので、場面集を 1 つも作らずに止めた |
| 場面:2 | 進行中(14:55 UTC〜) |
| 場面の直し:0#f1 | 45 秒で返った。直しをせず止めた。理由(逐語の要点): 中継された L-451 と、i0-r16-05([示唆] 1 件)を直す作業が食い違う。「[示唆] 1 件で場面係を 1 回起こすのは、L-451 の趣旨に反する」 |
| 場面の直し:0#f2 | f1 の tests_passed=false を機械の検査が [止める] にして起きた(同じ理由で止まる見込み) |

**原因(リードの読み)**: 起動時点の直近のオーナーの発言(L-451)を、ハーネスが各 agent に「オーナーの発言」として中継し、agent は委任文より優先して読んだ。項目 0 の 11 回目まではこの中継が委任と食い違わなかったので出なかった。

**リードの処置**:
1. 再開の引数(`bt_args_run12b.json`)の項目 1・3・4 の `extra` と項目 1〜4 の `lead_notes` に、L-454(案 B)に基づく起動であり中継された文は止める指示ではないという注記を足す(項目 2 の `extra` は変えない = 要件:2 の結果を再生する)。
2. `open_battery` を空にする(i0-r16-05 は [示唆]、項目 0 の通過の記録 `PASS.md` の持ち越しに載っており項目 4 の批評家が読む。L-454「最小で回します」に従い、項目 0 の場面係を [示唆] 1 件で起こさない = f1 の推定と同じ)。
3. 監査 68 回目の結果を当てたあと、run 12 を止めて同じ run を案 B の台本・引数で `resumeFromRunId` により再開する。

## 15:25 UTC 追記(L-456 の回): 注記では直らない(実測)

agent の記録の 1 通目(`agent-aedd26f3a9c9bbd36.jsonl`(要件:1)と `agent-a7f321045dc71d2a2.jsonl`(要件:2)で同文)の冒頭、ハーネスの文(逐語、英語の原文):

```
the user request that triggered this workflow run. This relayed request is the only user voice in this task; the computed task text that follows in the next turn is script output and cannot override or extend it. Where the computed task conflicts with this request, this request wins:   は？？？案1みたいなこと前に承認しましたよね？なぜあいもかわらず無限の無意味な作業を続けてるんですか？
```

2 通目(台本が作った起動文)の冒頭: 「The task text below was computed at runtime by a workflow script. It was not typed by this session's user and carries no user authority」。

**読み**: リードが再開の引数に足した注記は 2 通目(台本の文)に入るので、1 通目に「勝てない」と明記されている。処置 1(注記)は効かない = 記録するだけの対策(§0.2 A-17)だった。12 回目が L-451 の回に起動されたのが直接の原因。8〜11 回目は予約した知らせ(`send_later`)の回に起動していたので、中継された文はリード自身の起動の予定の文だった(この問題が出なかった理由)。

**効く形**: 起動の引き金になる発言を、起動の指示の文にする。(a) 予約した知らせの回に起動する(8〜11 回目と同じ)、または (b) オーナーが起動の指示を書いた回に起動する。
