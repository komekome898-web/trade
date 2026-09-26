# 委任文: 項目 4 を旧の軸なしで閉じる(2026-09-26、L-474「承認するので進めろ」)

親の委任文 `docs/DATA/delegations/20260925_backtest_env_prompt.md`(指紋 388d55cdeb32)と仕上げの委任文 `20260926_backtest_env_finish.md`(ec283fb43be1)は、**項目 4 の「旧エンジンとの互換」と全項目の「当方の現状」の軸について、この文書で撤回する**(L-470)。それ以外(記録の規則・§4 の安全の規則・提出前の吟味・場面集の規則 1〜9)は親のとおり。

## 0. 目的(オーナーの逐語。条件はここから導く。旧は基準にしない)

- L-405: 「**信頼できるバックテストが可能な環境を構築してほしい**」「**すべてが調査結果以上の信頼性と再現性に優れたものにすること**」
- L-453: 「**測定器の不具合やバックテストの条件付けに初歩的なミスが発覚し測定結果が信用できないことが判明→…知見を基にバックテスト環境構築**」
- L-407: 「**新しいエンジンはそもそも旧エンジンの完全上位互換になっていないと意味がない。確認できたら取り込まず消してよい**」/ L-408: 「**案2**」/ L-406: 「**2.案1**」(既存の研究スクリプトは触らない)
- L-470: 「**旧の話ばっかりしてる時点で、絶対あなたはどこかで旧を基準にします。完全上位互換かどうかなんて設計を満たした時点で確定するやろ。**」
- L-467 の基準(リードの語、オーナーの指摘から): 条件は「**結果を信用できるものにするか** = (1) 旧と無関係に正しさを確かめられる、(2) 同じ入力から同じ結果を再現できる、(3) 信用できない測定器・条件付けを中に含まない」で置く。数の一致は、相手が (1) を満たすときだけ根拠になる。

## 1. §0.1 の表(承認 L-474 = L-473 の回のリードの文の逐語)

| やろうとすること | オーナーの原文の該当語(逐語) | 信用できるものにするか((1)(2)(3)のどれ) |
|---|---|---|
| (1) 項目 4 の要件と場面集から「旧の再現」を外す(要件 I4-8〜I4-20 を規則の文と場面集の正解を基準にした文に、場面集の答えを spec の 1 通りに、barmodel の legacy 規則を消す) | 「**(1) 項目 4 の要件と場面集から「旧の再現」を外す…**」L-474 で承認 /「**完全上位互換かどうかなんて設計を満たした時点で確定するやろ**」L-470 | (1)(3) |
| (2) 旧のエンジン・旧の試験・golden・旧との比べ・全項目の「当方の現状」の adapter と組を消す | 「**(2) 旧のエンジン・旧の試験・golden・旧との比べ・全項目の「当方の現状」の adapter と組を消す**」L-474 /「**取り込まず消してよい**」L-407 | (3) |
| 研究のスクリプト 12 本が同じ名前・引数で新エンジンを呼べる呼び口を残す(スクリプトは触らない) | 「**2.案1**」L-406 /「**案2**」L-408 | (2) |
| (3) 批評家 1 回・実データの動作確認・全試験の完走・監査役 1 回で項目 4 を閉じる | 「**(3) 批評家 1 回・実データの動作確認・全試験の完走・監査役 1 回で項目 4 を閉じる**」L-474 | (1)(2) |
| 上限 = 作業者 1 回・批評家 1 回・監査役 1 回・4 時間(起動 = L-474 の承認 16:28 UTC = 01:28 JST → 上限 20:28 UTC = 05:28 JST) | 「**上限は作業者 1 回・批評家 1 回・監査役 1 回・4 時間**」L-474 /「**最小で回します**」L-454 | — |

## 2. 終わる条件(全部満たすまで。上限で残れば止めて逐語で報告)

1. **旧が中に無い**: `src/bot/backtest/` の 3 本は新エンジンの呼び口への委譲だけ(旧の算術は 1 行も無い)。`src/bot/bt/compat/` に `_old_arithmetic`・`run_backtest_as_old`・`evaluate_on_splits_as_old`・`route_of`・legacy の規則が無い。`tests/bt/compat/`(golden・旧の試験を通す・旧の写しとの格子)、旧の試験 7 本(`tests/test_backtest.py`・`test_maker_execution.py`・`test_max_hold.py`・`test_wick_stop.py`・`test_engine_maker_exit.py`・`test_short_margin.py`・`test_tp_sl.py`)は**関数 1 つずつ読んで 3 つに分ける**: (a) 旧の数を固定した試験 = 消す、(b) 場面集 item_4 の規則 R-* が覆う挙動(wick stop・maker 執行・TP/SL の優先・max_hold)の試験 = 消す(覆う規則の番号を返り値に書く)、(c) 一般の性質の試験(先読み禁止 `test_strategy_never_sees_future_bars`・指標の因果性 `test_ema_is_causal`・`test_rsi_bounds_and_warmup`・分割の時系列性 `test_split_is_chronological_and_disjoint`・商品 `test_products_registry`・リスク `test_risk_checker_product_rules` など)= **残して新エンジンの呼び口で通す**(旧の数を期待していれば期待を規則の文から導いた値に直し、その根拠を書く)。分けた一覧(関数名・(a)(b)(c)・理由)を返り値に。`tests/bt/item_4/reference/ext_bar_modes.py` とその試験、`materials/replace/` の旧の写し 2 組、全項目(0〜4)の `adapters/current_impl.py` と `survey_results/current_impl.tsv`、台本の `current_1`/`current_2` の組、`run_battery.py` の `current_impl` の対象を消す。検査 = 生きている設計・コード・試験(記録 `docs/AUDITOR/`・`docs/OWNER_LOG.md`・`docs/DISCUSSIONS/*/item_*/round_*`・`_run*`・過去の委任文を除く)で `旧エンジン|完全上位互換|golden|旧の試験|旧と同じ|旧の写し|current_impl|当方の現状|legacy` の出現がこの文書の撤回の注記以外に **0**(別の意味の legacy = `research_legacy_elements.py`・`liq_response.py`・`kaiko_*.json`・`SCAN_*`・`PHASE2/K1` は対象外。一覧をそのまま返す)。
2. **設計が旧を基準にしない**: `item_4/REQUIREMENTS.md` の I4-8〜I4-20 は「旧エンジンと同一」ではなく「`tests/bt/battery/item_4/DEFINITIONS.md` の規則 R-* の文と場面集の正解」を基準にした文になり、golden(I4-19)・置き換えと復元(I4-20)の行は撤回の注記だけを残す。項目 0〜3 の要件・定義から「当方の現状」の行を消す(通過の条件は変えない: 場面集の全部正解 + 調査結果の側との比較)。場面集 item_4 の答えは spec の 1 通り(legacy の欄・2 出力の場面を消す)、`DEFINITIONS.md` を再生成、`CONSIDERED.md` の「現状」の列を消す。**項目 13 への帰結(枠組みの変更、報告で開示)**: L-432「項目 13 で測る」の盲検は「新実装 vs 当方の現状」の組を失い、「新実装 vs 調査結果の側」(L-405「調査結果以上」)だけになる。
3. **呼び口**: 旧を import する 12 本(`scripts/research_*.py`・`run_backtest.py`・`validate_composite.py`・`qa/pipeline_known_answer_taker.py`)が変更なしに import できる(1 本ずつ `python -c "import ..."` の出力を返す)。加えて、呼び口の署名(`run_backtest`・`CostModel`・`BacktestResult`・`compute_metrics`・`Metrics`・`split_data`・`evaluate_on_splits` の名前・引数・戻り値の型)を `item_4/REQUIREMENTS.md` に呼び口の要件として書き、`tests/bt/item_4/` に署名の試験を置く。`scripts/run_backtest.py` は小さな実データ(`backtest_data/` の既存ファイル)で 1 回実行して末尾の行を返す(研究の 9 本は import と署名の試験だけ。実行は研究の周で行う)。
4. **正しさと再現**: 新エンジン vs 独立の参照 `bar_sim.py` の格子 `tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py` を **spec の規則だけで組み直す**(規則の欄の旧側の値・`legacy` の宣言を格子からも `bar_sim.py` の options からも消す。除外句で外すのではなく、存在しなくする)。条件 1 の grep の検査は `bar_sim.py`・`SPEC.md`・格子の試験・場面の定義ファイルも対象に含む。組み直した格子の全升が一致。場面集 item_0〜4 が全部正解。批評家の試験(`tests/bt/critic/item_*`)が通る。実データの動作確認 `tests/bt/item_4/test_i4_real_data_smoke.py` が今の版で通る。**全試験を完走**(`PYTHONPATH=src python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=none --basetemp=<私有>`。`-q` を重ねない)して失敗 0(収集エラー 0)。
5. **批評家 1 回 [止める] 0**(射程 = 正しさ・安全・統合 + 「旧が残っていないか」)。**監査役 1 回 [止める] 0**(この委任文の設計に対して、起動の前)。

## 3. 役と分担(並列 2 人 = 作業者 1 回。ファイルを分ける)

| 役 | 持ち物 | 触らない |
|---|---|---|
| 作業者 A(コードと試験) | `src/bot/backtest/`・`src/bot/bt/compat/`・`src/bot/bt/reference/SPEC.md`(legacy の記述)・`tests/bt/compat/`(消す)・`tests/test_backtest.py` ほか旧の試験(消す)・`tests/bt/item_4/`(格子を spec だけに、`reference/ext_bar_modes*` を消す)・`tests/bt/critic/item_4/test_i4r1_compat_decimal_prices.py`(今は「生きている旧エンジン」と golden の部品に依存する。**旧との一致ではなく**、小数の値の入力で compat の口の答えが独立の参照 `bar_sim.py` の答えと一致することを検める形に書き直す。golden の部品は消す)・`materials/replace/` の旧の写し(消す)・全試験の完走 | 場面集・要件・委任文・台本 |
| 作業者 B(設計と場面集) | `docs/DISCUSSIONS/2026-09-23_backtest_env/item_*/REQUIREMENTS.md`・`tests/bt/battery/item_0〜4/`(adapter・記録・定義・場面・試験・検討表・runner の current_impl)・`scripts/workflows/backtest_env.js`(current の組)・過去の委任文 3 本の冒頭の注記・`LEAD_DESIGN_items_1-12.md` | `src/`・`tests/bt/item_*`・`tests/bt/critic/*` |
| 批評家 | `tests/bt/critic/item_4/`・`round_3/CRITIC_close.md` | 他の役のファイル |

共通: git commit / push をしない(リードが行う)。私有の basetemp。返り値は (a) 変えた・消したファイル、(b) 打ったコマンドと末尾の行、(c) 満たせなかった条件と理由、(d) リードに聞くこと、(e) 提出前の吟味(場当たりの直しが無いこと、同じ根の全箇所)。旧の数との一致を根拠に書かない。

## 4. 上限と記録

- 作業者 A・B は 1 回(戻しなし)。返す期限 18:45 UTC(全試験の完走は A が背景で続け、終わり次第末尾の行を返す。上限 20:28 UTC)。批評家は A・B が返ったあと 1 回(期限 19:30 UTC)。批評家の [止める] は A・B に 1 回だけ戻す(委任文 §4 の型)。
- 過去の委任文 3 本は本文を変えず、冒頭に「L-470 により旧の軸を撤回(この文書へ)」の注記 1 行だけ足す(記録の整合。終わる条件ではない)。
- 批評家は作業者 A・B の両方が返ったあとに起こす(旧が消えた母体を検査する)。
- 監査役(設計)は 16:35 UTC に 1 回行い、[止める] 2 件([直す]1・[聞く]5)をこの版に反映した。上限(監査役 1 回)によりこの版の再検査はしない。
- 役の返り値・批評家・監査役の出力は逐語で `docs/AUDITOR/VERDICTS/2026-09-26_backtest_env_item4_close.md` に写す(O-4)。抜き出しの機械は SubagentHandback の欄を読む(前回の欠陥)。
- 上限で残ったものは「測っていない範囲・持ち越し」として逐語で報告する。
