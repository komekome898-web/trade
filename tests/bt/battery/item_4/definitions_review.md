## 提出前の吟味(場面係の最初の作り。第 r2-1 回の直しで変わった所は各項に書いた。直しの吟味の全部は ROOTCAUSE_r2-1.md)

作る役(場面係)が、批評家が [止める] を出しそうな所を先に探した結果。**終わる条件: この吟味は 1 回だけ行い(上限 1 周)、見つけて直せなかった物は「持ち越し」として下に残す。**数は全部 survey_results/*.tsv と `python3 scripts/check_bt_considered.py` の出力から写した(手で数えていない)。

### 観点ごとに先に探した [止める] の芽と、この版での扱い

- **I4-1(独立参照実装)**: 場面は本体と参照実装の両方の出力を手の計算と突き合わせるだけで、参照実装が本体の写しかどうか(同じコードを共有していないか)は場面では見えない(規則 2「振る舞いを試し、作りの形を試さない」)。独立であることは批評家が差分で見るしかない。**限界として残す。**当方の現状(旧エンジン)は参照実装の口を持たないので 2 場面とも「結果なし」。調査結果の側も 0 件(口が無い)。
- **I4-2(性質の試験)**: (第 r2-1 回で作り直した。i4-r1-06)taker だけの正解つきの格子(30 の場合)に加え、足の模型の全ての選択肢を乱数でオンにする正解なしの格子(i4-2-grid-all、24 の場合 + 先頭の部分)と、経路ごとの格子 7 つ(逆指値・利確・maker・maker の利確・持ち越し・保有の上限・構造的な逆指値、各 8 の場合 + 先頭の部分)を置き、不変条件 I1〜I12 と先頭の部分の規則で判定する。当方の現状と新実装は全部の格子で一致、何もしない対象・観測を 1 箇所ずつ壊した対象は全部の格子で不一致(試験 test_invariants_catch_each_perturbation)。試金石(maker の寿命の 1 本ずれ)は i4-2-grid-all でも不一致になる(survey_results/mutant.tsv)。
- **I4-3・I4-4(正解つきの場面・外部との突き合わせ)**: 正解は手の計算で、当方の現状と突き合わせて一致を確かめた(第 r2-1 回の版で食い違うのは下の L-1〜L-5 の 13 場面だけ)。第 r2-1 回で I4-3 に核の粒度(op delivery、2 場面)と参照実装の粒度(i4-3-ref-signal-first)の値の場面を足した(i4-r1-07)。i4-4-plain は動いた 21 対象のうち 6、i4-4-fee は 17 のうち 3 が正解と一致。**外部の道具の「不一致」の多くは、場面の戦略が次の足の始値を見られないので数量を合図の足の終値で決めた(adapter の各冒頭に書いた)ことによる数量の差で、道具の約定の規則の差とは限らない。**判定は数量も比べるので、この差も「不一致」に数えている。
- **I4-5・I4-6(統合・動作確認)**: 当方の現状(旧エンジン)にも調査結果の側にも口が無く、動かせた対象は 0。正解は 6 本の合成ファイル(項目 1 の仕様の形)から手で出し、試験(test_pipeline_expected_fills_match_the_files・test_pipeline_sha256_are_the_files_own)がファイルを読み直して確かめる。**場面の正解がどの実装とも突き合わせられていないことは、この 2 観点の限界として残す。**
- **I4-8〜I4-18(旧エンジンの足の挙動)**: 仕様の規則(R-*)と旧エンジンが食い違う所は互換の計算 L-1〜L-5 として別に書き、当方の現状が「不一致」になる場面は第 r2-1 回の版で 13(r1 の 7 つ + L-5 の 6 つ: i4-10-signal-first・i4-10-signal-first-short・i4-10-signal-first-two-models・i4-13-time-first・i4-13-time-first-two-models・i4-13-time-maker-tp-two-models)で、試験 test_stated_rules_and_existing_engine_agree_except_the_listed_deviations がこの 13 以外の一致を毎回確かめる。同じ足の中の順は R-O1 で固め、起きうる 20 組の全部を場面が固める(試験 test_every_order_pair_is_pinned・test_swapping_any_pair_of_the_order_breaks_a_scene。i4-r1-02)。i4-11-refuse-stack・i4-12-refuse(組み合わせを拒む)を拒んだ外部の道具は 0。
- **mutant**: 新しい実装の口(adapters/new_impl.py)を包み、maker_timeout_bars を 1 つ増やす欠陥を 1 つだけ植える。第 r2-1 回の走行の表(survey_results/mutant.tsv)では 67 場面のうち 4 場面(i4-1-ref-maker・i4-2-grid-all・i4-3-e2e-maker・i4-16-missed)が不一致、ほかは新実装と同じ。欠陥が場面で捕まることは、試験 test_mutant_plants_one_defect_and_breaks_its_scenes が当方の現状を土台にして確かめる(i4-16-missed・i4-3-e2e-maker が不一致になり、i4-8-next-open は一致のまま)。

### 調査結果の側で先に探した [止める] の芽

- **再現(opponents/repro_*.py、13 候補)**: 規則は一次資料の行を 1 対 1 で書き写し、共通の部分(注文の並び・建玉・場面の戦略)は _repro_bars.py に置いた。**読んでいない部分に依る場面は「再現していない」「読んでいない」「読んだ範囲に無い」と理由に書き、検討表では「再現できない」に数えた**(第 r2-1 回で gen_considered.py の judge_row に機械で入れた。それまでは「読んでいない」「読んだ範囲に無い」を「持たないと確認した」に数えていた = i4-r1-08)(OctoBot の手数料の率、LEAN の持ち越しと資産、Hikyuu の空売り、WonderTrader の資産など)。**LEAN の同じ足の上の複数の注文の走査の順は読んでいない(未確認)**ので、I4-10 の i4-10-priority の LEAN の結果はその仮定(送った順)に依る。BacktestingCore と Hummingbot の再現の `fills` は道具の出力ではなく書き直しの中の値(道具の結果に約定の列が無い)で、各ファイルの冒頭にそう書いた。
- **この役の走行で測った道具の挙動**: qf-lib の分足では時刻 t の戦略の注文が t+1 の始値で約定する(合図の足から 2 本後。調べた走行は opponents/qflib_adapter.py の冒頭)。quanttrader は待つ注文(指値・逆指値)があると次の足で自分の辞書の作り直しが例外になる(backtest_brokerage.py 125 行)。zipline-reloaded は次の分の終値で約定する。
- **他の役の容量の片付けで消えた物**: item_3/_dl/c16・item_1/_dl/c3・c87 の clone を同じ commit で取り直した(記録は venvs/item_4/i4_r1_scenekeeper_reclone_*.log)。**PineForge(70)は項目 2 の clone・構築物・C の driver の source が消えていて、この役の最初の走行では走ったが最後の走行では呼べない。その走行の表は最後の走行で上書きされて残っていない。構築し直しは持ち越し。**
- **導入のために venv に足した物**: qf-lib に PyJWT・oauthlib・requests-oauthlib(宣言されていない依存)、quanttrader に numpy 1.23.5・pandas 1.5.3・matplotlib 3.7.5(道具のコードが np.str と DataFrame.append を使う)、finmarketpy に plotly<6。どれも隔離した venv の中だけで、記録は venvs/item_4/ の各ログ。

### 持ち越し(この周で直していない物)

1. PineForge(70)の構築し直しと C の driver の書き直し。
2. OctoBot(11)の模擬の手数料の率、LEAN(52)の持ち越し・資産・同じ足の注文の走査の順、Hikyuu(60)の空売りの経路、WonderTrader(57)の資産: 一次資料のその部分を読んで再現を足す。
3. barter-rs(61)・gobacktest(69)・sigc(107)の構築し直し(容量)。今の版は 61・69 を一次資料から再現し、107 は一次資料で口が無いことを確かめた。
4. I4-5・I4-6 の場面の正解を突き合わせられる実装が、当方にも調査結果の側にも無い(新しい実装を待つ)。

### 第 r3-1 回(仕上げの第 1 段)で変えた所(上の r2-1 の数は当時の版。今の版の数はこの節)

- **同じ足の中の順(i4-r2-02)**: R-O1 の ② から「範囲の逆指値」を外し、R-H3 を「始値の出来事(時間切れ・待っていた決済の合図)は範囲の逆指値より先。『先に見るのは逆指値だけ』は始値より後の範囲の中での順」に直した(仕上げの委任文 §1 i4-r2-02 の決め)。時間切れの足の逆指値を別の出来事(旧 `stop@time`)に分けていたのをやめ、範囲の逆指値 1 つにした。起きうる組は 16 組(`i4_scenes.order_pairs`)。i4-13-stop-on-time-bar・i4-13-stop-on-time-bar-maker の正解は始値の時間切れ 101。2 出力の場面 i4-13-stop-on-time-bar-two-models を足した(互換 98 = L-5、仕様 101)。
- **maker の建ての経路(i4-r2-08)**: R-E4(マスク False の合図は指値を置かない・取り逃しに数えない)と R-M6(同じ向きの合図は指値を置き直さない)を足し(値は仕上げの委任文 §1 i4-r2-08 の決め)、互換の計算 L-6・L-7 を足した。場面 i4-14-maker-mask-false・i4-16-maker-mask-false-not-missed・i4-16-maker-mask-false-two-models・i4-16-same-side-keeps-limit・i4-16-same-side-two-models を足した。互換の答え(L-6・L-7)は当方の現状を実際に呼んで一致を確かめた(試験 test_legacy_answers_of_two_model_scenes_are_the_existing_engine)。
- 当方の現状が「不一致」になる場面は 22(r2-1 の 13 + i4-r2-02 の 3 + i4-r2-08 の 4 + リードの答え (2) の 2 = R-E4 の補いと L-8)。試験 test_stated_rules_and_existing_engine_agree_except_the_listed_deviations がこの 22 以外の一致を毎回確かめる。
- 足した・直した 10 場面(リードの答え (2) の 2 場面を含む)は、動かせた道具・再現の全部(一覧は `run_battery.py --list-targets`)に通した(場面集の規則 4)。PineForge(70)は比べていない(理由は opponents/CONSIDERED.md の 70 の行と survey_results/opp_pineforge.tsv の理由。最初に取れた版 0d76a099 は検査していない版で、リードの指示で消した。検査した版 5e62602c を取り直したが、構築・実行へ進む操作をこの環境の許可の判定が止めた)。
- 根本原因・主張の表・提出前の吟味は ROOTCAUSE_r3-1.md。

### 第 r3-1 回の第 2 段(リードの指示: 参照実装の役が字義どおりに読んだ点 U1〜U8 を規則の文にする。参照を bar_sim に切り替える)

- 規則の文に R-W5(U1: 窓の足が足りなければ有る分で)・R-M7(U2: 決済の指値と同じ向きの合図は置き直さない)・R-W6(U3: 建てた足の終値も構造的な
  逆指値の判定に入れる)・R-E5(U4: 向き・空売り不可で止められた合図は待っている建ての指値を残す)・R-V1(U5: 始値・終値を囲まない足を拒む)・
  R-V2(U6: 使わない = null、0 以下の率・本数は拒む)・R-V3(U7: 負の費用を受ける)・R-V4(U8: 寿命 0 を拒む)を足した。入力の形にも「使わない物は null」を書いた。
- 場面 11 を足した(値 9・2 出力 2): i4-11-wick-short-history・i4-11-wick-entry-bar-close・i4-16-exit-same-side-keeps-limit(+ two-models)・
  i4-14-blocked-opposite-keeps-limit・i4-14-sides-opposite-keeps-limit(+ two-models)・i4-8-refuse-bad-bar・i4-10-zero-rate-refused・i4-8-negative-fee・
  i4-16-zero-timeout-refused。拒む物(U5・U6・U8)は、対照の値の答えと拒む変形の組で置いた。
- 参照実装の粒度の場面(I4-1 の 2 つと i4-3-ref-signal-first)の参照は、独立の参照 `src/bot/bt/reference/bar_sim.py` の `run_bars` にした
  (`adapters/new_impl.py:_run_reference`。undecided = wick_short_history: use_available・same_side_exit_signal: keep)。参照は指標の式を持たない
  (SPEC.md §4)ので、I4-1 の参照の側は約定・損益・資産・取り逃しを判定し、指標は本体の側と I4-17 で判定する。3 場面とも新実装は「正解と一致」。
- 当方の現状が「不一致」になる場面は 26(第 1 段の 22 + R-M7 の 2 + R-E5 の向きの 2)。拒む物 3 場面は、当方の現状が対照では一致し、変形を
  拒まない(試験 test_stated_rules… は対照だけを見る。走行の表では「不一致」)。
- 第 2 段の時点で新実装が「不一致」の場面は 4: i4-14-sides-opposite-keeps-limit・i4-14-sides-opposite-two-models(R-E5)・i4-10-zero-rate-refused(R-V2)・
  i4-16-zero-timeout-refused(R-V4)。委任文 §1 の条件 2 のとおり、新実装の側で直す物。
