# 監査役 2 回目 — カード 8 の門を Binance で確かめた単位の読み(関門 ②、2026-10-06、逐語)

対象: 1 回目の直しの後の版(コミット f73385b7)。前回の記録 `docs/AUDITOR/VERDICTS/2026-10-06_c8_binance_gate_read_audit1.md`。
上限 2 回の 2 回目。直しは前回の「止める」(0 件)と読みを変える「直す」に絞る決まり(L-605・L-607・L-608)。

## 監査役の出力(逐語)






他 0 件省略

前回の「止める」はありませんでした(0 件)。今回、直しで新しく入った「止める」級もありません。設計の段の判定(item 9)は、代替の記録 `/home/user/trade/docs/RESEARCH/design_substitute/c8bn_2026-10-06_judgment.md` が存在し、見出しもあります。

関連ファイル
- /home/user/trade/docs/ANALYSIS/2026-10-06_card8_binance_gate.md
- /home/user/trade/docs/RESEARCH/cards/c8_session_mean_revert/binance_gate/PREREG.md
- /home/user/trade/docs/RESEARCH/cards/c8_session_mean_revert/binance_gate/gate/GATE_READ.md
- /home/user/trade/docs/RESEARCH/cards/c8_session_mean_revert/binance_gate/read/audit1_checks.md

## リードの応答(1 件ずつ)

- 指摘 2: 直した: 「大部分は値幅の違い」を外し、「値幅の違いが入る。割る前と割った後は単位が違い、割合は測っていない。分かるのは前半は値幅だけで説明できる余地があるまで」と書いた(D2・D10 の知見の文 2・D9 の組み合わせ・D9b の観察 1・K-159・K-032)。D9 の「+17.04 の側で見積もる」は「値幅をそろえた量で P から見積もり直す」に直した
- 指摘 3: 直した: G10b を超えることから「年の違いだけでは作られていない」と書いた所を、「年の違いだけではない公算【推定】。G10b は事前登録が言い過ぎる側と認めた作り方で、G10a は年と区分を分ける対照ではないので、年の偏りを除いたとは言えない」に弱めた(D7・D9・D9b・D10・K-159)
- 指摘 4: 直した: 「Binance の低の日が bitFlyer ほど負けないため」を外し、「Binance の低の日の平均が 0 を含む大きさのため。bitFlyer の低の日(K-032)とは期間が違い区間も重なるので、どちらが負けないかは言えない」に直した
- 指摘 5: 直した: 区間の上端を桁を足して出した(+0.00033、`diag_tables.mean_ci` の hi = 0.0003299…)。D7 の表に写し、「A は約定の置き方で 0 を含む側にも 0 より下の側にも出る(1 通りは境目)」と書いた

「止める」0 件・「直す」5 件(全部直した)。上限の 2 回に達したので 3 回目は呼ばない。2 回目の直しは監査役が確かめていない(報告にそう書く)。
