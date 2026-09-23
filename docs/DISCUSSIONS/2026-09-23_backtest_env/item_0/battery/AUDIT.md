# 場面集の監査と直し(項目 0、作業者の前。Workflow の記録から逐語で書き出し)

監査役(場面):N#k = k 回目の監査、場面の直し:N#k = k 回目の直し(その前の監査の指摘を受けたもの)。

## 監査役(場面):0#1(agent a2a40f606f2ba2742)

- [聞く] tests/bt/battery/item_0/ROOTCAUSE.md 全文(旧 ROOTCAUSE_2.md の内容は消えており、現ディレクトリに ROOTCAUSE_2.md は存在しない) — 前回の場面係は『板の待ち行列』観点(観点2の一区分)を検討表から丸ごと外す判断について『この判断が要件の解釈に関わる以上…改めて明記し、リードの確認を仰ぐ』と約束していた。今回作り直した成果物一式(DEFINITIONS.md・scenes.py・opponents/CONSIDERED.md・docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md §1〜§6)を grep しても『リードに聞くこと』『聞くこと』に類する見出しは 1 件も無く、REQUIREMENTS.md の 8 種の事象型(P0-3)にも『板の待ち行列』は入っていない(candidates 37 ThePredictiveDev・91 homerun の『板の待ち行列』の強みは今回も比較の観点から外れたまま)。約束した確認は今回のどの成果物で果たされたか、それとも今回もリードに提示されないまま次段(作業者1周目後の REPORT.md)へ進むのか。
- [聞く] tests/bt/battery/item_0/opponents/CONSIDERED.md の複数行(候補52 QuantConnect・57 WonderTrader・63 trade-frame・69 gobacktest ほか)— これらの『スキップ: 明らかに弱い(上位互換)』の理由は、スキップする候補自身の機構の『実装』欄がいずれも『確かめていない(README だけ)』であり、SCAN 自身も該当候補を『浅い(README からの確定)』と記す。委任文 §3 の材料順は『(a) SCAN の書き写しで足りないときは (b) 一次資料を読みに行く』だが、これらの行は (a) が自ら『未確認』と明記した機構claimのまま (b) に進まず『上位互換』の根拠に使っている(危険リスト11件には含まれないため (b) をしない理由は無い)。README の記載は実際の実装能力を過小評価している可能性もあり、その場合『上位互換』の判定(Basana 等がその能力を包含する)が崩れうる。この読み(スキップ判定はスキップ対象自身の機構の実装確認を要さず、被覆候補側の実測だけで足りる)は委任文のどの行から確定できるか。
- [聞く] tests/bt/battery/item_0/adapters/protocol.py:72 `missing = [method_name(s.id) for s in SCENES if not hasattr(cls, method_name(s.id))]` — 場面集の規則2『場面は振る舞いを試し、作りの形を試さない』の直後の指摘(前回の0#5-2、ROOTCAUSE.md 11〜15行)で能力の場面の採点から hasattr を除いたが、この行は今も hasattr でアダプタが全場面のメソッドを実装しているかを検査している。これは各対象の『採点』には使われず、アダプタの完全性チェック(実装漏れの検出)にとどまる、という理解でよいか(run_battery.py の correctness/reproducibility 関数は hasattr を使っていないことは確認済み)。
