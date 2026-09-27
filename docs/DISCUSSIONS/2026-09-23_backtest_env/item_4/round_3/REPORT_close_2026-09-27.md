# 項目 4 を旧の軸なしで閉じた報告(2026-09-27、L-474「承認するので進めろ」)

オーナーの原文(逐語): 「**(1) 項目 4 の要件と場面集から「旧の再現」を外す…(2) 旧のエンジン・旧の試験・golden・旧との比べ・全項目の「当方の現状」の adapter と組を消す、(3) 批評家 1 回・実データの動作確認・全試験の完走・監査役 1 回で項目 4 を閉じる。上限は作業者 1 回・批評家 1 回・監査役 1 回・4 時間**」(L-473 の回の文、L-474 で承認)。
委任文 `docs/DATA/delegations/20260926_backtest_env_item4_close.md@c6eaee9f16a4`。役の出力の逐語 `docs/AUDITOR/VERDICTS/2026-09-26_backtest_env_item4_close.md`。起動 16:28 UTC → 批評家の返り 18:17 UTC(上限 20:28 の前)。

## 1. 終わる条件(委任文 §2)の状態 — 5 つとも満たした

| 条件 | 根拠(打ったコマンドと末尾の行は VERDICTS) |
|---|---|
| 1 旧が中に無い | `src/bot/backtest/` 3 本 = import と `__all__` だけ(批評家が AST で検める試験を足した)。compat から `_old_arithmetic`・`run_backtest_as_old`・`evaluate_on_splits_as_old`・`route_of`・legacy の規則を消し `RULES = ("spec",)`。`tests/bt/compat/`・旧の写し 2 組・旧の模型の移設・全項目の `current_impl` の adapter と記録・台本の current の組を消した。旧の試験 7 本は関数ごとに分け、(a) 旧の数を固定 = 0 件、(b) 規則 R-* が覆う = 消した(規則の番号つきの表)、(c) 一般の性質(先読み禁止・指標の因果性・分割・商品・リスク・費用の性質)= 残して新エンジンで通した。批評家の数え: A・B・批評家の持ち物のコードで旧の語 0(検査の試験を除く) |
| 2 設計が旧を基準にしない | `item_4/REQUIREMENTS.md` の題と I4-8〜I4-20 を規則 R-* と場面集の正解を基準に書き直し、golden・置き換えと復元は撤回の注記。項目 0〜3 の要件・定義から「当方の現状」を消した(通過の条件は変えない)。item_4 の場面集は答えを spec の 1 通りに(2 出力の場面 12 を削除)、`DEFINITIONS.md` 再生成、`check_bt_considered` 誤り 0 |
| 3 呼び口 | 12 本の import 全部 ok(A と批評家がそれぞれ打った)。署名の試験 28 件。`scripts/run_backtest.py backtest_data/binance_XRPUSDT_4h.csv` を 1 回実行(動作確認のみ) |
| 4 正しさと再現 | 新エンジン vs 独立の参照(規則の文だけから書いた `bar_sim.py`): 格子 21 件 + 小数 1008 升 + spec_vs_ref 1008 升 = 全升一致。場面集 item_0〜4 `651 passed`。mutant `killed 34/34`。実データの動作確認は全試験に含む。**全試験の完走 `20598 passed, 10 skipped`(失敗 0・収集エラー 0、41 分)** |
| 5 批評家 1 回・監査役 1 回 | 批評家: **[止める] 0、[直す] 3**(全部当てた: 除外した記録の一覧を報告に / SPEC の mutant の数 / I4-7 の注記)。監査役(設計、起動の前): [止める] 2 → 委任文の版 2 に反映(上限 1 回のため再検査なし。**この報告は監査役を通していない**) |

## 2. 数えの開示(批評家 i4-c-01)

旧の語の検査で除外に加えた記録 11 本(過去の周の記録、変えない): `REPORT_2026-09-26.md` 14・`item_0/PASS.md` 2・`item_0/battery/AUDIT.md` 13・`tests/bt/battery/item_0/ROOTCAUSE_r8-1.md` 7・`r12-1` 2・`r13-1` 9・`r15-1` 2・`r16-1` 3・`item_4/ROOTCAUSE_r2-1.md` 38・`r3-1.md` 10・`survey_results/attempts/105.log` 2。別の意味の legacy(`docs/legacy/` の原典名・CFTC のファイル名・変数名)30、撤回の注記 11、SCAN で打った grep の語の記録 4、批評家の検査の試験そのもの 11。

## 3. 持ち越し(全部)

- `rules`・`arithmetic` の引数(受ける値は 1 つ)と `new_impl.py` の `model` の受け口を落とすこと(B の adapter と一緒に 1 回で。批評家 i4-c-04)。
- `entry_sides` と `allow_short=False` の同値の場面が無い(両規則は別々に固まっている。批評家 i4-c-06)。
- `survey_results/new_impl.tsv`・`mutant.tsv` は消した 12 場面の行を除いただけ(資料係の周で走らせ直す)。
- **項目 13 への帰結(枠組みの変更)**: L-432「項目 13 で測る」の盲検は「新実装 vs 当方の現状」の組を失い、「新実装 vs 調査結果の側」(L-405「調査結果以上」)だけになる。
- item_0 の凍結の正の定義 A から「当方の現状」の 2 句を消した(L-474 (2) の範囲としてリードが認めた。VERDICTS に記録)。
- PineForge(70)は比べていない(前の報告のまま)。

## 4. リードの逸脱

- 作業者 B が `git stash` を 1 回打った(段階の状態が外れた。内容の喪失なし)。
- 作業者 A が指示の一覧に無い `test_i4ref_ext_recorded.py` を消した(同根。リードが認めた)。
