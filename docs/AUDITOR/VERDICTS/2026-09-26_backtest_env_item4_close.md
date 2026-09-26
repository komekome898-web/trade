# 項目 4 を旧の軸なしで閉じる — 役の出力の逐語の記録(2026-09-26、L-474)

委任文: `docs/DATA/delegations/20260926_backtest_env_item4_close.md@c6eaee9f16a4(版 2。版 1 = ee6ae81633b4 に監査役(設計)の 2 件を反映)`。起動 16:28 UTC、上限 20:28 UTC(05:28 JST)。

役: 監査役(設計、起動の前に 1 回)→ 作業者 A(コードと試験)・作業者 B(設計と場面集)を並列 → 批評家 1 回 → 全試験の完走。

## 監査役(設計)の出力(逐語、16:35 UTC)

## 監査結果(項目 4 を旧の軸なしで閉じる — 起動前・設計検査)

1. **[止める]** `docs/DATA/delegations/20260926_backtest_env_item4_close.md:28`(条件 4)「新エンジン vs 独立の参照 `bar_sim.py` の格子(spec の規則だけ、**legacy の欄を除いた**全升)が一致」— 実測: `src/bot/bt/reference/bar_sim.py` 自体に文字列 `legacy` は 0 件だが、条件 2(26 行目)は「場面集 item_4 の答えを spec の 1 通りに(legacy の欄・2 出力の場面を消す)」としており、条件 2 が満たされた時点で「legacy の欄」は存在しないはずである。にもかかわらず条件 4 が「legacy の欄を除いた」という除外句を残しているのは、(i) 条件 2 の文言が古いまま更新されていないか、(ii) 実は場面集本体とは別に `bar_sim.py` 側のグリッド定義に旧規則ベースのセルがまだ残る計画があるか、のどちらかである。どちらであっても本文からは判別できない。条件 1(25 行目)の grep 検査(`legacy` が撤回注記以外に 0 件)の除外リストに `bar_sim.py` や scene 定義ファイルは入っておらず、「除いた全升」という除外操作自体が、消したはずの旧規則セルを検査対象から静かに外す抜け道になっていないか(P14 / A-10、L-470「完全上位互換かどうかなんて設計を満たした時点で確定する」との整合)。

2. **[止める]** 条件 1(25 行目)「旧の試験(`tests/test_backtest.py`・`test_maker_execution.py`・`test_max_hold.py`・`test_wick_stop.py` ほか `bot.backtest` を旧の挙動として試すもの)…を消す」— 実測(`grep -n "^def test_"`): これらのファイルには `test_strategy_never_sees_future_bars`(先読み禁止)・`test_ema_is_causal`・`test_rsi_bounds_and_warmup`・`test_split_is_chronological_and_disjoint`(walk-forward 分割)・`test_products_registry`・`test_risk_checker_product_rules`(商品レジストリ・リスクチェッカー、`tests/test_short_margin.py`)が含まれる。これらは「旧エンジン固有の挙動を旧の数で固定した試験」ではなく、規則の文で言い表せる一般性質(先読み禁止・指標の因果性・分割の時系列性・商品設定の妥当性)を検査するものに見える。委任文は `tests/bt/battery/item_4/DEFINITIONS.md` の R-* が wick stop・maker 執行・TP/SL の優先順位・max_hold はカバーしている(実測で確認)が、先読み禁止・EMA/RSI の因果性・walk-forward 分割・商品レジストリ・リスクチェッカーがどこで同等にカバーされるかは委任文のどこにも書かれていない。「ほか `bot.backtest` を旧の挙動として試すもの」という一括りの理由づけが、実際には旧エンジンに限らない一般規則の試験まで削除対象に含めている可能性がある(消すと検査が減る = A-10 の型、(f))。

3. **[聞く]** `tests/bt/critic/item_4/test_i4r1_compat_decimal_prices.py` の扱い(§3、35 行目「compat の口で成り立つ形に」)— 実測: このファイルは現状 `test_decimal_price_cells_match_the_live_old_engine` という名で「**LIVE old engine**」と直接突き合わせ、`tests/bt/compat/golden/compat_golden_scenes.py`・`compat_golden_run.py` を import している(docstring: "Runs only while the old engine is in src/bot/backtest/")。しかし条件 1(25 行目)は `tests/bt/compat/`(golden を含む)自体を消す対象にしており、このテストが依存する golden モジュールが同じ作業で消える。委任文はこの依存関係(削除対象のモジュールに依存したまま「口が成り立つ形に」変える指示だけを出している)を明示的に接続しておらず、「旧の数との一致」で書かれた現状のテストをどう書き換えるかの基準(旧の live 出力と一致させない、という条件)が本文に無い。§3 末尾の「旧の数との一致を根拠に書かない」という共通注記だけでこの具体ファイルの扱いが担保されているか。

4. **[聞く]** 条件 3(27 行目)「呼び口: 旧を import する 12 本(…)が変更なしに import できる(1 本ずつ `python -c "import ..."` の出力を返す)」— 検査は import の成否のみで、12 本のスクリプトが実際に呼び出す関数(同じ名前・引数の呼び口)が旧と同じシグネチャ・戻り値で正しく動作するかは検査対象に入っていない。(e) の懸念どおり、import は通るが実行時に呼び口の中身(移譲先の新エンジン API)が食い違って研究スクリプトが壊れる経路を、この条件は塞いでいない。

5. **[聞く]** §1 表(21 行目)「上限=作業者 1 回・批評家 1 回・監査役 1 回・**4 時間(起動 16:28 UTC → 上限 20:28 UTC = 05:28 JST)**」— `docs/OWNER_LOG.md` L-474 は「起動 **17:0x UTC**、上限 **21:0x UTC**(06:0x JST)」と記録しており、委任文の起動時刻(16:28 UTC)と食い違う。I-013 は「終わる条件と、その上限(周か時間)」を要求しており、起点がずれると 4 時間上限の実際の締切がどちらか不明になる。

6. **[聞く]** 条件 2(26 行目)「項目 0〜3 の要件・定義から『当方の現状』の行を消す」— L-472 で「当方の現状」との比較軸は項目 13(統合の三択盲検、L-431/L-432)の判定対象でもあると判明している。この委任文は項目 4 の範囲でのみ閉じるとしているが、項目 0〜3 の「当方の現状」比較軸を全体から外した後、項目 13 の盲検比較(現状 vs 新実装)を何と比較して測り直すかは本文に書かれていない。持ち越しとして明記されるべきではないか。

7. **[直す]** 条件 2(26 行目)「過去の委任文 3 本は本文を変えず、冒頭に『L-470 により旧の軸を撤回(この文書へ)』の注記 1 行だけ足す」— この行は目的の逐語(L-405/L-407/L-408/L-470)から直接は導けず、記録上の整合性維持という委任文自身の都合から来ている。§2(終わる条件)に手続き上の記帳行が混在している(a の観点で名指し)。

8. **[聞く]** §3 分担表の批評家欄(37 行目)「`tests/bt/critic/item_4/` ・ `round_3/CRITIC_close.md`」— 条件 5(29 行目)は「批評家 1 回(射程=正しさ・安全・統合+『旧が残っていないか』)」としているが、批評家自身が触るディレクトリに finding 1・3 で指摘した「legacy の欄」「LIVE old engine と突き合わせる compat テスト」が現状のままだと、批評家が検査する母体自体が旧を含んだままになる可能性がある。批評家着手前にこれらが解消されている前提かどうかの確認。

[止める] 2 件
他の項目(3・4・5・6・7・8)は [聞く]/[直す] として提示。

**リードの処置(16:40 UTC、委任文の版 2 に反映)**: 1 = 条件 4 の「legacy の欄を除いた」を消し、格子と bar_sim の options から旧側の値を存在しなくする。grep の検査に bar_sim.py・SPEC.md・格子・場面の定義も含める。2 = 旧の試験 7 本は関数ごとに (a) 旧の数を固定 = 消す / (b) R-* が覆う = 消す(番号を書く)/ (c) 一般の性質 = 残して新エンジンの呼び口で通す、に分け一覧を返す。3 = 小数の試験は旧との一致ではなく独立の参照との一致に書き直す(golden の部品は消す)。4 = 呼び口の署名を要件と試験にし、run_backtest.py を小さな実データで 1 回実行する。5 = 起動 = 承認 16:28 UTC、上限 20:28 UTC に統一(OWNER_LOG L-474 の行を訂正)。6 = 項目 13 の盲検は調査結果の側とだけ、と委任文に書き報告で開示する。7 = 過去の委任文の注記の行を §2 から §4(記録)へ移す。8 = 批評家は A・B の両方が返ったあと、と明記。上限(監査役 1 回)によりこの版の再検査はしない。


## 作業者 B(設計と場面集)の返り値(逐語、17:01 UTC)

## 作業者 B の返り値(委任文 `docs/DATA/delegations/20260926_backtest_env_item4_close.md@c6eaee9f16a4`)

合意した完了の形(逐語): 「**I4-8〜I4-20 は「旧エンジンと同一」ではなく「`tests/bt/battery/item_4/DEFINITIONS.md` の規則 R-* の文と場面集の正解」を基準にした文になり、golden(I4-19)・置き換えと復元(I4-20)の行は撤回の注記だけを残す。項目 0〜3 の要件・定義から「当方の現状」の行を消す(通過の条件は変えない…)。場面集 item_4 の答えは spec の 1 通り(legacy の欄・2 出力の場面を消す)、`DEFINITIONS.md` を再生成、`CONSIDERED.md` の「現状」の列を消す**」(§2-2)/「**呼び口の署名(…)を `item_4/REQUIREMENTS.md` に呼び口の要件として書き**」(§2-3)。返した時刻 17:01 UTC(期限 18:45 UTC)。commit / push はしていない。

### (a) 変えた・消したファイル

**消した(9 本、`git rm` で削除を段階に載せた)**: `tests/bt/battery/item_{0,1,2,3,4}/adapters/current_impl.py`、`tests/bt/battery/item_{1,2,3,4}/survey_results/current_impl.tsv`(item_0 には元から無い)。

**item_4 の場面集**: `i4_scenes.py`(2 出力の場面 12 を消した: i4-13-two-models・i4-16-maker-mask-false-two-models・i4-16-same-side-two-models・i4-16-mask-false-opposite-two-models・i4-16-exit-same-side-two-models・i4-14-sides-opposite-two-models・i4-17-two-models・i4-18-two-models・i4-10-signal-first-two-models・i4-13-stop-on-time-bar-two-models・i4-13-time-first-two-models・i4-13-time-maker-tp-two-models。`ORDER_LEGACY`・`_HT_LEGACY`・`_closing_limit`/`exit_events`/`exit_fill` の `model` 引数・`bars_input` の `models` を消した。I4-19/I4-20 の `VIEWPOINTS`・`NOT_SCENES` を撤回の文にした。場面 79 → 67 の `add`、`len(SCENES)` 74)/ `adapters/new_impl.py`(`_legacy_bars`・`_legacy_split`・`models` の分岐・`run_backtest`/`CostModel`/`split_data` の import を消し、`run_bars(..., "spec")`・`split_rows(..., "decimal")` の 1 通りに)/ `i4_protocol.py`・`i4_judge.py`(`models`・`legacy`/`spec` の入れ子を消した)/ `gen_definitions.py`(「互換の計算 L-1〜L-8」の節と `models` の記述を消し、規則の文の出所の段落と R-O1 の ⑤→⑥→⑦ の理由から既存の実装への言及を消した)/ `DEFINITIONS.md`(再生成、911 行)/ `definitions_review.md`(当方の現状・L-*・2 出力を根拠にした文を消し、冒頭に撤回の注記)/ `gen_considered.py`・`opponents/CONSIDERED.md`(I4-19/I4-20 を撤回の文に。再生成 + `check_bt_considered.py --write` = 誤り 0 件)/ `opponents/_i4_base.py`(`NO_MODELS` と `models` の分岐を消した)/ `i4_targets.py`・`run_battery.py`(current_impl の対象と docstring)/ `survey_results/*.tsv`(41 本から消した 12 場面の行 = 各 12 行、計 492 行。`new_impl.tsv`・`mutant.tsv` は資料係が毎周作り直す物)/ `test_battery_item4.py`(`DEVIATIONS`・`test_stated_rules_and_existing_engine_agree_except_the_listed_deviations`・`test_legacy_answers_of_two_model_scenes_are_the_existing_engine` を消し、mutant と runner の試験は新実装の口を土台に)/ `test_battery_item4_claims.py`(F 族 `test_new_impl_legacy_goes_through_the_old_mouths`・`PROSE_LEGACY`・legacy の順の検査を消し、格子の観測は新実装の口から取り、R-M7 の mutant は置き直しの関数で書いた)/ `test_battery_item4_diffscope.py`(格子の path の例 `tests/bt/compat/golden/g.json` → `tests/bt/other/g.json`)。

**item_0**: `run_battery.py`(`_module_path`・`load_adapter`・`TARGET_DISTS["current_impl"]`・`--list-targets`・docstring)/ `grid_c.py`・`test_battery_r15_unplaced.py`(組「新実装・当方の現状・試金石」→「新実装・試金石」)/ `test_battery_r13_claims.py`(`test_the_current_implementations_requests_are_within_the_field` を消した)/ `test_battery_item0.py`(`test_current_impl_runs_every_scene_twice_identically`・`test_current_impl_passes_the_provenance_check` を消し、`test_no_adapter_reports_a_rule_or_a_predicted_order` の current_impl だけを走らせていた後半を消し、凍結の正の定義 A の記録との照合に撤回 2 句の置換 `WITHDRAWN_FROM_A` を足した)/ `gen_definitions.py`(凍結の正の定義 A の 2 句と申し送りの 2 行から「当方の現状」を消した)/ `def_axes/jA.tsv`(切片 116・178「当方の現状」の 2 行を消し、118 の条件を直し、番号を振り直した: 187 → 185 切片)/ `test_battery_def_grids.py`(格子 A の大きさ 3120635156889600000 → 2080423437926400000、走らせる升目 73 → 71)/ `line_judgments.tsv`(直した行の判断を新しい文に写した 6 行を末尾に足した)/ `term_judgments.tsv`(直した行の語の判断 76 件を新しい文に写し、無くなった行の 76 件を消した = `term_marks.problems()` の「出現の無い判断」の規則)/ `DEFINITIONS.md`(再生成)。

**item_1・3**: `gen_definitions.py`・`DEFINITIONS.md`(再生成)・`i{1,3}_targets.py`・`run_battery.py`・`test_battery_item{1,3}.py`(runner の試験の対象を new_impl に)。**item_2**: `i2_targets.py`・`run_battery.py`。

**設計**: `item_4/REQUIREMENTS.md`(題・§1・I4-8〜I4-20・I4-21 の追加・射程外・§3.0/3.3/3.4・§4・§5 の 2/6/7/9)、`item_{0,1,2,3}/REQUIREMENTS.md`(§4「当方の現状」を撤回の注記に、それを根拠にした吟味の項を撤回に)、`LEAD_DESIGN_items_1-12.md`(項目 4 の行)。

**台本**: `scripts/workflows/backtest_env.js`(`current_1`/`current_2`・`identical.current`・`trio('current')`・`winsC`/`lossC`/`eqC`/`okC`・`lossStreak.current`・prompt の「当方の現状」を消し、`passCandidate(item, okS, stopsImpl, table, critic)` に)。**持ち物の外 1 本**: `tests/workflows/backtest_env_logic.test.mjs`(`passCandidate` の呼び出しの引数 `okC` を落とした 11 箇所。台本の関数の署名を変えたので試験が `stopsImpl.filter is not a function` で落ちた。委任文の持ち物には無いファイルで、A の「触らない」にも入っていない)。

**過去の委任文 3 本**: 題の直後に注記 1 行(本文は変えていない)。

**A の物(私は触っていない)**: `git status` に出る `docs/DISCUSSIONS/…/item_4/round_3/materials/replace/` の削除 8 本、`tests/bt/item_4/i4_option_grid.py`(A)、`tests/bt/item_4/test_i4_mouth_signature.py`(?? = A)、`src/`・`tests/test_*.py` の差分。

### (b) 打ったコマンドと末尾の行

- `PYTHONPATH=src python -m pytest tests/bt/battery/item_0 tests/bt/battery/item_1 tests/bt/battery/item_2 tests/bt/battery/item_3 tests/bt/battery/item_4 -p no:cacheprovider -o tmp_path_retention_policy=none --basetemp=<私有>/final_basetemp` → **`651 passed in 128.70s (0:02:08)`**(17:01 UTC。A の src の今の状態の上で)。
- `python3 tests/bt/battery/item_4/gen_definitions.py` → `wrote …/DEFINITIONS.md (911 lines)`。`python3 tests/bt/battery/item_4/gen_considered.py && python3 scripts/check_bt_considered.py tests/bt/battery/item_4/opponents/CONSIDERED.md --write` → `OK 誤り 0 件`。
- `node --test tests/workflows/backtest_env_logic.test.mjs` → `# pass 12` `# fail 0`。`node --check scripts/workflows/backtest_env.js` → 通る。
- 9 語の数え(範囲を切った: `docs/DISCUSSIONS/2026-09-23_backtest_env`(round_*・_run*・battery/materials を除く)・`tests/bt/battery`・`scripts/workflows`。コマンド `git ls-files -z -- <範囲> | grep -zvE 'round_|_run|battery/materials' | xargs -0 grep -oE '<9 語>' | cut -d: -f1 | uniq -c`): 出現の合計 145、ファイルごとの内訳は上の出力のとおり。**残るものの逐語と理由**:
  - 撤回の注記(私が書いた): `item_4/REQUIREMENTS.md` 3・20・22・23(L-474 の表の行の逐語引用)・202、`item_{0,1,2,3}/REQUIREMENTS.md` 各 2(§4 の注記)、`LEAD_DESIGN` 67、`backtest_env.js` 300・383・387、`test_battery_item0.py` 1492-1493(記録と照らすための撤回 2 句の逐語)・1508、`test_battery_def_grids.py` 57、`line_judgments.tsv` 666、`item_4/DEFINITIONS.md` 864 = `definitions_review.md` 3。
  - 別の意味: `item_4/REQUIREMENTS.md` 54(`research_legacy_elements.py` = 呼び口の 12 本の名。委任文が対象外と明記)、同 91・208 と `gen_considered.py` 44・46・`CONSIDERED.md` 16・32(§3.1 で実際に打った SCAN の grep 語 `golden (test|file|output)` の記録。変えると打ったコマンドの記録が偽になる)。
  - 記録(除外の語に当たらないが記録の性質のもの。触っていない): `REPORT_2026-09-26.md` 14、`item_0/PASS.md` 2、`item_0/battery/AUDIT.md` 13、`tests/bt/battery/item_0/ROOTCAUSE_r{8,12,13,15,16}-1.md`・`item_4/ROOTCAUSE_r2-1.md`(38)・`ROOTCAUSE_r3-1.md`(10)、`item_0/survey_results/attempts/105.log`。

### (c) 満たせなかった条件と理由

1. 「撤回の注記以外に 0」は、上の「別の意味」(SCAN の grep 語 golden の記録 7 件、`research_legacy_elements.py` 1 件)と「記録」(REPORT・PASS・AUDIT・ROOTCAUSE・log)を除いて 0。記録のファイルは委任文の除外の列に名が無いが、過去の周の記録なので変えなかった(A-5b)。
2. `survey_results/new_impl.tsv`・`mutant.tsv` は消した 12 行を除いただけで、今の版の新実装で走らせ直していない(資料係の周の仕事。走らせ直せば全部の行が変わる)。

### (d) リードに聞くこと

1. `tests/workflows/backtest_env_logic.test.mjs` を 1 箇所(11 呼び出しの引数)変えた。持ち物の外なので、戻すなら言ってほしい(戻すと `node --test` が落ちる)。
2. item_0 の凍結の正の定義 A(監査役(定義)が通した文、`ROOTCAUSE_r8-1.md` に 1 字違わず照らす試験)から「当方の現状」の 2 句を消し、試験は記録に撤回 2 句の置換を当ててから照らす形にした。凍結の文を変える判断は委任文 §2-2「定義から「当方の現状」の行を消す」に読んだが、凍結の解除を別に承認するなら記録に足してほしい。
3. **私の誤り(報告)**: `node --test` が私の変更の前から落ちていたかを見るために `git stash` / `git stash pop` を 1 度打った(作業木全体を約 1 秒退避)。中身は戻ったが、段階に載せた削除(私の `git rm`)が「未段階の削除」に戻り、`git ls-files` が消した adapter を返して item_0 の試験 1 件が落ちた → `git rm --cached` で載せ直して通した。A の段階の状態も同じく外れている可能性がある(内容は失われていない。`git status` の "A tests/bt/item_4/i4_option_grid.py" は残っている)。リードがコミットするとき `git add -A` で拾えば影響は無い。
4. `test_battery_item4.py` の mutant・runner の試験と `test_battery_item4_claims.py` の格子の観測は、当方の現状の代わりに新実装の口(`adapters/new_impl.py`)を土台にした。新実装が場面で落ちればこれらも落ちる(通過の条件と同じ物なので独立の弱点にはならないが、A の変更と連動する)。

### (e) 提出前の吟味

- 場当たりの直しが無いこと: 消したのは軸そのもの(adapter・組・2 出力の場面・legacy の順・互換の計算の節)で、除外句で隠した所は無い。`_closing_limit` の legacy 分岐は関数から無くし、R-M7 の mutant は試験の側の関数に置いた。
- 同じ根の全箇所: item_0〜4 の adapter・tsv・targets・runner・grid の組・試験・定義・検討表・台本・node の試験・opponents の共通部品(`_i4_base.py` の `models` 分岐)・survey_results の消した場面の行まで当てた。grep で確かめた(上の数え)。
- 旧の数との一致を根拠に書いていないこと: 要件 I4-8〜I4-18 は規則 R-*・M-*・D-* と場面集の正解だけを基準に書いた。`test_battery_item4.py` から「既存の実装と一致する」試験を消し、`definitions_review.md` の「当方の現状と突き合わせて確かめた」の文を消した。この返り値にも旧の数は 1 つも無い。
- 通過の条件を変えていないこと: 項目 0〜3 の要件・定義は「当方の現状」の行を消しただけで、場面集の全部正解 + 調査結果の側との比較(審査員 3 体中 2 体)はそのまま(§4 の注記に逐語で残した)。台本は `okC` を落とし、`okS`(対調査)だけで判定する形にした(項目 13 への帰結 = 委任文 §2-2 の開示のとおり)。

**リードの答え(17:05 UTC)**: (d)1 `tests/workflows/backtest_env_logic.test.mjs` の変更 = そのまま(台本の署名を変えた帰結。戻さない)。(d)2 item_0 の凍結の正の定義 A から「当方の現状」の 2 句を消したこと = L-474 の (2)「全項目の「当方の現状」の adapter と組を消す」の範囲として認める。凍結の解除はこの記録で行う(監査役(定義)が通した文のうち、撤回した 2 句だけ。L-470 が根拠)。(d)3 `git stash` の 1 回 = 記録した。段階の状態はリードが `git add -A` で拾う。(d)4 = 認める(通過の条件と同じ土台)。(c)1 の「記録」のファイルは変えない(過去の周の記録、A-5b)。

