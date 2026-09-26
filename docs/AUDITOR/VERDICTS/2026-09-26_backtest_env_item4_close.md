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


## 作業者 A(コードと試験)の返り値(逐語、18:08 UTC)

## 作業者 A の返り値(委任文 `20260926_backtest_env_item4_close.md@c6eaee9f16a4`)

合意した「完了の形」の逐語(§2-1): 「**`src/bot/backtest/` の 3 本は新エンジンの呼び口への委譲だけ(旧の算術は 1 行も無い)。`src/bot/bt/compat/` に `_old_arithmetic`・`run_backtest_as_old`・`evaluate_on_splits_as_old`・`route_of`・legacy の規則が無い**」/ §2-4「**組み直した格子の全升が一致**」「**全試験を完走…して失敗 0(収集エラー 0)**」。

補足(事実): リードが 17:12 UTC 前後に私の途中の編集をチェックポイントとして commit した(61ffd04「checkpoint of A's in-flight edits」)。私自身は commit / push していない。**未 commit で残っているのは `tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py` の 1 本だけ**((a) の最後の行)。

### (a) 変えた・消したファイル

**書き直し(src)**
- `/home/user/trade/src/bot/backtest/engine.py`・`metrics.py`・`walk_forward.py` — import 行と `__all__` だけ(`bot.bt.compat.*` への委譲。関数・クラスの定義は 0。試験 `test_bot_backtest_holds_no_arithmetic` が検める)
- `/home/user/trade/src/bot/bt/compat/barmodel.py` — `BarRules`・`LEGACY`・`RULES` の 2 通り・`rules_of` の分岐・`LEGACY_PERIODS_PER_YEAR`・欄 9 つ(`tp_before_time_exit`/`level_arithmetic`/`sharpe_periods`/`negative_carry`/`signal_at_open`/`time_exit_at_open`/`maker_mask_at_signal`/`maker_same_side_keeps`/`refuse_non_positive`)を消し、spec の規則を直に書いた(水準は 10 進で比べる・始値の出来事が範囲より先・時間切れは始値・R-E4/E5・R-M7・R-S1 は符号条件なし・R-V2/V4 の拒否は `BarOptions.check` に統合)。`SPEC = "spec"`、`RULES = ("spec",)` の **1 通りだけ**。`run_bars(events, decide, options, rules, *, start=0)` の `rules` は "spec" だけ受ける((d)-1)
- `/home/user/trade/src/bot/bt/compat/engine.py` — `_old_arithmetic`・`run_backtest_as_old`・`evaluate_on_splits_as_old`・`route_of`・`_PendingLimit`・`_core_takes_*`・`_on_core` を消し、`run_backtest` は SPEC で `run_bars` を呼び `Metrics(**res.metrics)`(M-5 の年率化 = 365·86400/bar_seconds)を返す
- `/home/user/trade/src/bot/bt/compat/metrics.py` — `LEGACY_PERIODS_PER_YEAR` → `PERIODS_PER_YEAR_60S`(既定 bar_seconds=60 の M-5 の値)。算術は変えていない
- `/home/user/trade/src/bot/bt/compat/walk_forward.py` — `"binary"` の算術を消し、`DECIMAL` の 1 通り。`split_data` も 10 進(D-1)
- `/home/user/trade/src/bot/bt/compat/__init__.py`・`/home/user/trade/src/bot/bt/__init__.py` — legacy の宣言・文言を消した
- `/home/user/trade/src/bot/bt/reference/SPEC.md` — §4 末尾・§5(撤回の注記に置換)・§6・§8-3・§9・§10・§0 の表・§1 から旧エンジン/golden/ext の記述を消した(`grep` の当たり 0)

**消した**
- `tests/bt/compat/`(7 ファイル全部: golden 3 + json + 試験 3)
- `tests/bt/item_4/reference/ext_bar_modes.py`・`test_i4ref_extmodes_properties.py`・`test_i4ref_extmodes_scenes.py`・`ext_backtesting_compare.py`・`ext_results/backtesting_py_0.6.6.json`・**`test_i4ref_ext_recorded.py`**(指示に無いが `ext_backtesting_compare` と `ext_results` を import する同根のファイル。消さないと収集エラー)
- `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/`(5)・`replaced_version_reverted/`(3)
- 旧の試験 5 本を丸ごと: `tests/test_maker_execution.py`・`test_max_hold.py`・`test_wick_stop.py`・`test_engine_maker_exit.py`・`test_tp_sl.py`(内訳は下の表)

**書き直し・編集(tests)**
- `/home/user/trade/tests/bt/item_4/i4_option_grid.py`(新規 = 旧 `compat_golden_scenes.py` の場面生成器の移設。golden の語を消し `GRID_SEED` に改名。中身の乱数・格子は同じ。`test_i4_barmodel_on_core.py`・`test_i4_spec_vs_reference_grid.py`・critic の小数の試験が使う)
- `/home/user/trade/tests/bt/item_4/test_i4_mouth_signature.py`(新規、28 件: 7 つの名前が compat のものであること / `bot.backtest` に定義が無いこと / `run_backtest` の引数 19 個と既定値と keyword-only / `CostModel` の欄 4 つと R-C1・R-A2 / `BacktestResult`・`Metrics`・`Splits` の欄と型 / 既定 = 明示 / 拒否 16 通りが全部 ValueError / 核が取れない足の拒否 / M-5 の年率化 / D-1 の分け方 70/20/10・30/10/10)
- `/home/user/trade/tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py` — 変更なし(既に spec の規則だけ・旧側の値なし。回した = (b))
- `/home/user/trade/tests/bt/critic/item_4/test_i4r1_compat_decimal_prices.py` — 書き直し: 小数の値(0.1 刻み、0.3/0.7/1.1 %)の 1008 升を **compat の口(`run_backtest`+`CostModel`+`Strategy`)と独立の参照 `bar_sim.py`** で比べる(場面集の許容 1e-9。golden・旧に依存しない)+ 空でない検査
- `/home/user/trade/tests/bt/item_4/test_i4_barmodel_on_core.py`(`"legacy"` のパラメータを消し、生成器を差し替え)・`test_i4_spec_vs_reference_grid.py`(生成器)・`test_i4_r2_signal_at_open_grid.py`(`run_old`・`test_legacy_keeps_the_old_engine_bit_for_bit`・docstring (3) を消した)・`test_i4_r3_maker_two_values_grid.py`・`test_i4_r3_time_exit_at_open_grid.py`(docstring の legacy の 1 文)・`i4w_drive.py`(`models`/legacy の分岐)・`conftest.py`(golden のパス)・`reference/ref_mutants.py`(旧の模型の mutant 6 件を消し 8+26=34 件)
- `/home/user/trade/tests/test_backtest.py`・`/home/user/trade/tests/test_short_margin.py` — (c) だけ残した(下の表)
- **`/home/user/trade/tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py`(批評家の持ち物。未 commit)** — 全試験を回すと `from new_impl import TARGET` が **item_0 の adapter の `new_impl`** に束縛されて収集エラーになった(全項目の adapter が同名。critic だけ・item_0+critic だけの収集では起きず、全体の順で起きる)。指示 8「収集エラーは直す」により、item_4 の adapter をパスで読む形に変え(`importlib.util.spec_from_file_location`)、`current_impl` と `"legacy"` に依存する `test_the_legacy_rule_set_keeps_the_old_engines_result`(6 件、B が current_impl を消した後は import で落ちる)を消した。残り 30 件は通る。**批評家の持ち物なので、これで良いかは (d)-3。**

**旧の試験 7 本の関数ごとの分け方**

| ファイル / 関数 | 分 | 理由(覆う規則) |
|---|---|---|
| test_backtest: test_costs_reduce_pnl_on_flat_market / test_zero_cost_flat_market_is_breakeven | (c) | 一般の性質(費用で損・費用 0 で損益 0)。残す |
| test_backtest: test_execution_delayed_to_next_bar_open | (b) | R-T1 |
| test_backtest: test_strategy_never_sees_future_bars | (c) | 先読み禁止。残す |
| test_backtest: test_split_is_chronological_and_disjoint | (c) | 分割の時系列性。60/20/20 は D-1(floor(100·0.6)、floor(100·0.8))から導かれる値と注記 |
| test_backtest: test_metrics_full_set | (c) | 期待値は M-1〜M-12 の定義から手で導いた値(2/4・25/10・12.5・−5・2.5・15/4)。注記を足して残す |
| test_backtest: test_ema_is_causal / test_rsi_bounds_and_warmup / test_donchian_excludes_current_bar | (c) | 指標の因果性。残す |
| test_maker_execution: buy_fills_only_when_traded_through / no_same_bar_fill | (b) | R-M1 |
| test_maker_execution: timeout_cancels_and_counts_missed_fill | (b) | R-M2 |
| test_maker_execution: sell_fill_and_fee_only_cost | (b) | R-M1・R-A2 |
| test_maker_execution: taker_path_unchanged_by_maker_addition | (b) | R-T1 |
| test_max_hold: long_force_closed… / short…symmetrically / time_exit_still_applies… | (b) | R-H1 |
| test_max_hold: no_effect_when_none | (b) | R-V2(None = 使わない) |
| test_max_hold: stop_loss_fires_first_when_hit_earlier | (b) | R-P3・R-O1 |
| test_max_hold: force_close_overrides_pending_signal | (b) | R-H2 |
| test_max_hold: invalid_max_hold_bars_rejected(0) | (b) | R-V2(署名の試験の拒否 16 通りにも含む) |
| test_wick_stop: long/short level…・window_size…・window_never_reaches…・level_is_frozen… | (b) | R-W1 |
| test_wick_stop: a_wick_through…not_an_exit / close_exactly_at_the_level | (b) | R-W2 |
| test_wick_stop: entry_bars_own_close_can_arm | (b) | R-W2/W3(SPEC.md U3) |
| test_wick_stop: wick_stop_exit_pays_taker_costs | (b) | R-W3・R-C1 |
| test_wick_stop: overrides_a_pending_signal / signal_exit_still_works / time_exit_still_applies_in_wick_mode | (b) | R-W3 / R-T1・T3 / R-H1 |
| test_wick_stop: wick_mode_actually_changes_the_outcome | (b) | R-W1〜W3(格子の `test_the_grid_reaches_every_exit_reason` が wick_stop の到達を検める) |
| test_wick_stop: invalid_options_are_rejected(5 通り) | (c) | 口の拒否 = ValueError。署名の試験 `test_every_option_refusal_is_a_value_error` に移設(R-W4・R-V2 の 2 通りは (b) でもある) |
| test_wick_stop / test_engine_maker_exit: defaults_are_bit_identical_to_passing_nothing | (c) | 「既定 = 明示」の一般の性質。署名の試験 `test_defaults_equal_the_same_values_passed_explicitly` に移設(「以前とビット一致」の旧の枠は捨てた) |
| test_engine_maker_exit: long/short maker_tp fills…・touching_not_a_fill・signal_exit_still_works_as_taker_fallback | (b) | R-X1(・R-T1) |
| test_engine_maker_exit: maker_tp_pays_no_spread… | (b) | R-C1・R-A2 |
| test_engine_maker_exit: never_fills_on_the_entry_bar | (b) | R-X2 |
| test_engine_maker_exit: stop_loss_wins_when_both… | (b) | R-O1 |
| test_engine_maker_exit: maker_tp_matches_take_profit_pct… | (b) | R-P4・R-X1 |
| test_engine_maker_exit: entry_mask_blocks…・read_at_decision_bar・masked_entry_does_not_block_exiting | (b) | R-E2・R-E3 |
| test_engine_maker_exit: entry_sides_long_only…(2 件) | (b) | R-E1・R-T4 |
| test_engine_maker_exit: invalid_options_are_rejected(6 通り) | (c) | 署名の試験に移設(R-X3 の 2 通りは (b) でもある) |
| test_short_margin: short_profits_when_price_falls / close_signal_flattens… / close_signal_when_flat | (b) | R-T3・R-T4・R-A3 |
| test_short_margin: sell_without_short_permission_is_noop | (b) | R-T4 |
| test_short_margin: swap_carry_reduces_pnl | (b) | R-S1 |
| test_short_margin: portfolio_short_round_trip / portfolio_short_loss… / paper_margin_short_round_trip / paper_margin_leverage_cap / risk_checker_product_rules / products_registry | (c) | エンジン外(建玉・PAPER・リスク・商品)。残す |
| test_tp_sl: 5 件全部 | (b) | R-P1・R-P3(gap は min(始値, 水準))・R-P4・R-O1 |

(a) 旧の数を固定した試験 = 該当 0(旧エンジンの出力を写した数はどのファイルにも無かった。手計算の数はすべて (b) の規則の場面か (c))。

### (b) 打ったコマンドと末尾の行(全部 `PYTHONPATH=src`、basetemp は私有)

- 格子: `python -m pytest ... tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py -x` → `21 passed in 15.98s`(12 種 × 60 升 + 接頭辞 + 出口の到達 + 拒否: 全升一致)
- 署名・旧 2 本・critic item_4(直す前): `... tests/bt/item_4/test_i4_mouth_signature.py tests/test_backtest.py tests/test_short_margin.py tests/bt/critic/item_4` → `7 failed, 119 passed`(7 = 署名の空データの私の補助関数の誤り 1 + 批評家の `test_the_legacy_rule_set_keeps_the_old_engines_result` 6 = `No module named 'current_impl'`)
- 署名(直した後): `... tests/bt/item_4/test_i4_mouth_signature.py` → `28 passed in 0.58s`
- 批評家の pending_signal(直した後): → `30 passed in 0.54s`
- tests/bt/item_4 全部: `... tests/bt/item_4` → `1379 passed, 2 skipped in 1145.47s (0:19:05)`(ログ `scratchpad/item4_close.log`。critic item_4 の小数の試験は上の 119 passed に含まれる = 8 チャンク + 1)
- 12 本の import(`sys.path.insert(0,'scripts'); importlib.import_module(m)`): research_anchor / research_anchor_v2 / research_basis / research_fx / research_legacy_elements / research_mainbot_exits / research_signals / research_tournament / research_user_strategies / run_backtest / validate_composite / qa.pipeline_known_answer_taker → **12 本とも `import ok`**
- `python scripts/run_backtest.py backtest_data/binance_XRPUSDT_4h.csv`(4380 本の実データ、`--help` は無く引数は位置の CSV 1 つ)→ 末尾:
  ```
  === wick_reversal ===
    [training] pnl=+663 trades=191 win=38% PF=1.08 sharpe=6.75 maxDD=25.0% expectancy=+3.5/trade fees=1723
    [validation] pnl=-1147 trades=68 win=32% PF=0.66 sharpe=-24.00 maxDD=27.7% expectancy=-16.9/trade fees=611
    [out_of_sample] pnl=-1214 trades=62 win=24% PF=0.46 sharpe=-30.52 maxDD=22.7% expectancy=-19.6/trade fees=562
  === range_fade ===  (3 分割とも trades=0)
  Reminder: only OOS results count. Suspect overfitting when training >> OOS.
  ```
  (動作確認のみ。相場の結論には使わない)
- 収集: `... --collect-only tests` → `20608 tests collected in 5.02s`(収集エラー 0。直す前は `ERROR collecting tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py … cannot import name 'TARGET' from 'new_impl' (…/battery/item_0/adapters/new_impl.py)`)
- **全試験**: `python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=none --basetemp=<scratchpad>/pt_close_A tests` → **`20598 passed, 10 skipped, 4 warnings in 2466.25s (0:41:06)`**(失敗 0・収集エラー 0。ログ `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/full_close_A.log`)
- 検査(`{git ls-files; 未追跡} -- src tests scripts | grep -oE '旧エンジン|完全上位互換|golden|旧の試験|旧と同じ|旧の写し|current_impl|当方の現状|legacy' | cut -d: -f1 | uniq -c`、合計 125、うち私の持ち物 **0**)。`tests/bt/battery/`(B、数えただけ)以外の当たりの一覧そのまま:
  - 別の意味の legacy: `scripts/data_quality.py`(1、schema の旧挙動)/ `scripts/research_fx_fundamentals.py`(4、CFTC の `cot_jpy_legacy.csv`)/ `scripts/research_legacy_elements.py`(6、ファイル名と docs/legacy)/ `scripts/research_matilda_modern.py`(1)・`research_matilda_taro.py`(2)・`research_vr_barrier.py`(2)・`research_wall_front.py`(1)(いずれも `docs/legacy/` の原典)/ `scripts/run_scalp_paper.py`(3、`--exit taker` の "legacy hold")/ `src/bot/exchange/resilience.py`(1、docs/legacy)/ `src/bot/research/liq_response.py`(6、変数名)/ `tests/test_intent_map_rule.py`(1、docs/legacy)/ `tests/test_scalp_logic.py`(2、legacy taker exit)
  - 台本(B): `scripts/workflows/backtest_env.js`(3: 「当方の現状」の撤回の注記)/ `tests/workflows/backtest_env_logic.test.mjs`(1: 同)
  - 批評家: `tests/bt/critic/item_4/test_i4r2_time_exit_at_the_open.py`(1: docstring「The legacy rule set is not tested here …」。**触っていない**)
  - 検査時点で私の持ち物にあった `src/bot/bt/compat/engine.py`(L-408 の引用「旧と同じ…」)と `test_i4_r3_*` 2 本の docstring は消して 0 にした(引用は L-408 の番号だけ残した)

### (c) 満たせなかった条件と理由
- なし(§2-1 のコードと試験の部分・§2-3・§2-4 の私の担当は全部通った)。ただし `ref_mutants.py`(34 件)は**回していない**(第 1 段の実測 40/40 落ちのうち消した 6 件を除く。時間の都合。SPEC.md §6 にそう書いた)。

### (d) リードに聞くこと
1. `run_bars(..., rules, ...)` の `rules` と `split_rows(..., arithmetic)` の `arithmetic` は、B の `new_impl.py` が位置引数で `"spec"`・`"decimal"` を渡し続ける(B のファイルを触れないため)ので、**受ける値を 1 つだけにして引数は残した**(`RULES = ("spec",)`、`ARITHMETICS = ("decimal",)`)。1 通りしか無い引数を落とすなら、B の adapter・`i4w_drive.py`・`test_i4_*` の呼び出しと一緒に 1 回で変える。落とすか。
2. `tests/bt/item_4/reference/test_i4ref_ext_recorded.py`(指示の一覧に無い)を消した。良いか。
3. 批評家の持ち物 `test_i4r1_pending_signal_before_intrabar_exit.py` を「収集エラーは直す」により最小限で変えた(上記)。批評家の周で戻す・別の直し方にするか。
4. `test_i4r2_time_exit_at_the_open.py:17` の docstring の "legacy" の 1 文(批評家の持ち物、触っていない)を検査の 0 に含めるか。

### (e) 提出前の吟味
- 場当たりの直し: 収集エラーの直しは同名 adapter の根(全項目 `adapters/new_impl.py`)に対しパスで読む形。署名の試験の失敗 1 件は試験の補助関数(空の ndarray の添字)で、口を変えていない。
- 同じ根の全箇所: legacy の欄 9 つ → barmodel の分岐を全部消した(`grep -c legacy` = 0)。`"binary"` は walk_forward・i4w_drive・spec_vs_ref から全部消した(`grep '"binary"'` の当たり 0)。`compat_golden`/`tests/bt/compat`/`ext_bar_modes`/`BarRules`/`LEGACY` の参照は src/tests/scripts に 0(battery を除く)。
- **旧の数との一致を根拠に書いていない**: 正しさの根拠は独立の参照 `bar_sim.py` との一致(0.5 刻みの格子 21 件 + 小数の 1008 升 + spec_vs_ref 1008 升 + 場面集)だけ。(c) で残した期待値は規則の文(D-1・M-*・R-A3)から導いた値で、注記を足した。
- 核 `src/bot/bt/core/` は触っていない(`git diff HEAD~2 HEAD --stat -- src/bot/bt/core` = 空、CORE_VERSION 据え置き)。B の持ち物(場面集・要件・委任文・台本)は触っていない。

**リードの答え(18:12 UTC)**: (d)1 `rules`・`arithmetic` の引数(受ける値 1 つ)= 今は残す(落とすのは B の adapter と一緒に 1 回で行う持ち越し。1 通りしか無いことは `RULES = ("spec",)` で固定されている)。(d)2 `test_i4ref_ext_recorded.py` の削除 = 認める(同根)。(d)3 批評家の持ち物の最小限の変更 = 批評家の周で批評家が検める。(d)4 批評家の docstring の "legacy" の 1 文 = 批評家に消させる(検査の 0 に含める)。(c) `ref_mutants.py` 34 件は批評家の周で回す。


## 批評家(1 回)の出力(逐語、18:17 UTC。全文 round_3/CRITIC_close.md)

# 批評家の返り値(項目 4 を閉じる、委任文 `20260926_backtest_env_item4_close.md@c6eaee9f16a4`)

記録: `/home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/CRITIC_close.md`(同じ内容)。git の操作はしていない。触ったのは `tests/bt/critic/item_4/`(2 本の整備 + 1 本の追加)とこの記録だけ。

合意した射程(逐語): 「**批評家 1 回 [止める] 0(射程 = 正しさ・安全・統合 + 「旧が残っていないか」)**」

## §0.1 の表(右が全部埋まったので擦り合わせずに着手)

| やろうとすること | 委任文の該当語(逐語) |
|---|---|
| A・B の主張をファイルとコマンドで確かめる | 「**批評家 1 回 [止める] 0(射程 = 正しさ・安全・統合 + 「旧が残っていないか」)**」§2-5 |
| (b) の「覆う規則」が場面で検められているか | 「**(b) 場面集 item_4 の規則 R-* が覆う挙動…= 消す(覆う規則の番号を返り値に書く)**」§2-1 |
| 9 語の数え(記録を除く) | 「**検査 = 生きている設計・コード・試験(記録…を除く)で `旧エンジン\|…\|legacy` の出現がこの文書の撤回の注記以外に 0**」§2-1 |
| 格子・署名・critic・battery item_4・旧 2 本・mutant 34 件を回す | 「**組み直した格子の全升が一致…批評家の試験…が通る**」§2-4 / リードの答え「**批評家の周で回す**」 |
| 12 本の import と `run_backtest.py` を自分で打つ | 「**1 本ずつ `python -c "import ..."` の出力を返す**」「**小さな実データ…で 1 回実行して末尾の行を返す**」§2-3 |
| 自分の docstring の "legacy" を消す / A の最小限の変更を判断する | リードの答え (d)3「**批評家の周で批評家が検める**」(d)4「**批評家に消させる**」 |

## 指摘

- **i4-c-01 [直す]** 旧が残っていないか / target 核(リードの報告): 委任文 §2-1 の除外リストに**名が無い**記録に 9 語が残る — `REPORT_2026-09-26.md` 14・`item_0/PASS.md` 2・`item_0/battery/AUDIT.md` 13・`tests/bt/battery/item_0/ROOTCAUSE_r{8,12,13,15,16}-1.md` 7/2/9/2/3・`item_4/ROOTCAUSE_r2-1.md` 38・`r3-1.md` 10・`attempts/105.log` 2。リードは 17:05 に「変えない(A-5b)」と決めた。打って確かめた: 生きている試験でこれらを**読む**のは `test_battery_item0.py:1501`(撤回 2 句の置換後に照合)と `test_battery_item4_diffscope.py:236-244`(ROOTCAUSE の差分の節が手で編集されていないことを検める = 記録を書き換えると落ちる)の 2 本だけで、旧の語を根拠にした判定は無い。よって [止める] ではないが、**報告に「除外に加えた記録 11 本(名と件数)」を書く**こと。書かずに「0」と報告すれば A-10。
- **i4-c-02 [直す]** 正しさ / target A / `src/bot/bt/reference/SPEC.md` 120・183 行: 「40 件中 40 件」は第 1 段の数で、今の 34 件は A が回していない。私の実測(私有の複製で): `python3 tests/bt/item_4/reference/ref_mutants.py` → **`killed 34/34`**。SPEC §6・§8 をこの数に直す。
- **i4-c-03 [直す]** 統合 / target B / `item_4/REQUIREMENTS.md:40` I4-7「既存の試験を落とさない・**消さない**・飛ばさないか」が、同じファイルの §1「(2) 旧の試験…を消す」と矛盾したまま残っている。L-474 で (a)(b) を消したことと、残した (c) と `tests/bt/` を落とさない旨の注記 1 行。
- **i4-c-04 [注記]** target B(持ち越し): `adapters/new_impl.py` の `inp.get("model","spec") != "spec"` の受け口(撤回した 2 出力の選択子)。`rules`・`arithmetic` の引数を落とす周に一緒に。
- **i4-c-05 [注記]** 安全: 呼び口は `sealed.py`・事前登録を通らない(`grep sealed|prereg` in compat = 0)が、書き換え前と同じで迂回の経路は増えていない。`tests/test_audit_gates_wired.py` → `12 passed`。`run_backtest.py` は書き込み無し。
- **i4-c-06 [注記]** (b) の検査は減っていない: 表の規則は全部 `DEFINITIONS.md` 38〜103 行にあり場面が引く(R-T1 12・R-P3 12・R-M2 7・R-S1 5・R-W1 4 …)。個別に読んだ: wick の凍結は参照が水準を約定時に 1 回だけ置き(`bar_sim.py:307`)格子が追随を落とす / gap の始値 = R-P3 / `entry_sides`=`allow_short=False` の**同値**だけは場面に無い(両規則は別々に固まる)/ `defaults_are_bit_identical` は署名の試験 122 行に移設済み。(a)=0 は A と一致。
- **i4-c-07 [注記]** 自分の持ち物: A のパス読みの形は**それでよい**(根 = 全項目の adapter が同名。改名は B の持ち物)。docstring の旧エンジンの 3 文と `model` 引数を落とし、`test_i4r2…:17` の 1 文を消した。足した `test_i4r3_no_old_axis_remains.py`(4 件: 生きている項目 4 の木に 9 語が無い / 対照 = 植えた語を拾う / `RULES==("spec",)`・`ARITHMETICS==("decimal",)` と他の名の拒否 / `bot.backtest` 3 本は AST で import と `__all__` のみ)。この 1 本自身が検査の語として 11 出現を持つ(数えに別立て)。

## 確かめたこと・回した試験(末尾の行)

- `src/bot/backtest/` 3 本 = docstring・import・`__all__` のみ(11/9/9 行)。compat に `_old_arithmetic` 等 0。`barmodel.py:98-105` `RULES=(SPEC,)`。`walk_forward.py:28-29` `ARITHMETICS=(DECIMAL,)`。`bar_sim.py` の options に旧側の鍵無し。核 `git diff 09b4733 HEAD --stat -- src/bot/bt/core` = 空。A の全試験ログ 306 行目 `20598 passed, 10 skipped, 4 warnings in 2466.25s`。
- 12 本の import: **12 本とも `import ok`**(自分で打った)。`scripts/run_backtest.py backtest_data/binance_XRPUSDT_4h.csv` → exit 0、23.3 秒、末尾 `range_fade` 3 分割 trades=0 と `Reminder: only OOS results count…`(動作確認のみ)。
- `critic item_4 + 格子 + 署名 + test_backtest + test_short_margin` → `141 passed in 37.63s` / `tests/bt/battery/item_4` → `169 passed in 3.29s` / `tests/bt/critic/item_4`(整備後)→ `82 passed in 21.69s` / `--collect-only tests` → `20612 tests collected`(20608 + 4)/ mutant → `killed 34/34`。

## 集計

**[止める] 0 件、[直す] 3 件**、[注記] 4 件。

旧の語の数え(ファイルごと、全文は記録 §4): `src tests scripts` 合計 129(別の意味の legacy 30・撤回の注記 11・SCAN の語 4・私の検査の試験 11・除外に名が無い記録 73)、docs の範囲 58。**A・B・批評家の持ち物のコード(`src/bot/backtest`・`compat`・`reference`・`tests/bt/item_4`・`tests/bt/critic/item_4`)は検査の試験を除き 0。**

時間が来て読めなかった範囲: なし(18:07〜18:16 UTC)。回していないもの: `tests/bt/item_4` の全部(A の 19 分)、場面集 item_0〜3(B の 651 は item_0〜4 合計、私は item_4 の 169 だけ)。

**リードの処置(18:20 UTC)**: [止める] 0。[直す] 3 件は機械的なのでリードが当てる: i4-c-01 = 報告に「除外に加えた記録 11 本(名と件数)」を書く。i4-c-02 = SPEC.md の mutant の数を 34/34(批評家の実測 `killed 34/34`)に直す。i4-c-03 = item_4/REQUIREMENTS.md の I4-7 に注記 1 行(旧の試験 (a)(b) は L-474 で消し、(c) と tests/bt/ は落とさない)。[注記] 4 件は報告に写す(持ち越し: `model` の受け口・`rules`/`arithmetic` の引数を落とす周、`entry_sides` = `allow_short=False` の同値の場面)。

