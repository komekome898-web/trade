# 項目 4 を閉じる — 批評家(1 回、§2 条件 5)の出力(2026-09-26)

委任文: `docs/DATA/delegations/20260926_backtest_env_item4_close.md@c6eaee9f16a4`(`sha256sum | cut -c1-12` で確認)。起こされた時刻 18:07 UTC(この環境の時計。リードの文では 18:10 UTC)、期限 19:30 UTC。git の操作はしていない。触ったのは `tests/bt/critic/item_4/` とこのファイルだけ。

合意した射程(委任文 §2 条件 5 の逐語): 「**批評家 1 回 [止める] 0(射程 = 正しさ・安全・統合 + 「旧が残っていないか」)**」

## 0. §0.1 の表(やること | 委任文の該当語の逐語)

| やろうとすること | 委任文の該当語(逐語) |
|---|---|
| A・B の主張をファイルとコマンドで確かめる(3 本の呼び口・compat・barmodel・場面集・要件・全試験のログ) | 「**批評家 1 回 [止める] 0(射程 = 正しさ・安全・統合 + 「旧が残っていないか」)**」§2-5 /「**役の返り値・批評家・監査役の出力は逐語で…写す**」§4 |
| A の (a)(b)(c) の分け方のうち (b) の「覆う規則」が場面で本当に検められているかを見る | 「**(b) 場面集 item_4 の規則 R-* が覆う挙動…の試験 = 消す(覆う規則の番号を返り値に書く)**」§2-1 |
| 9 語の数え(生きている設計・コード・試験。記録を除く) | 「**検査 = 生きている設計・コード・試験(記録…を除く)で `旧エンジン\|完全上位互換\|golden\|旧の試験\|旧と同じ\|旧の写し\|current_impl\|当方の現状\|legacy` の出現がこの文書の撤回の注記以外に 0**」§2-1 |
| 格子・署名・critic・battery item_4・旧 2 本・`ref_mutants.py` 34 件を私有の basetemp で回す | 「**組み直した格子の全升が一致。場面集 item_0〜4 が全部正解。批評家の試験(`tests/bt/critic/item_*`)が通る**」§2-4 / A の (c)「**`ref_mutants.py`(34 件)は回していない**」→ リードの答え「**批評家の周で回す**」 |
| 12 本の import と `run_backtest.py` の実行を自分で打つ | 「**旧を import する 12 本…が変更なしに import できる(1 本ずつ `python -c "import ..."` の出力を返す)**」「**`scripts/run_backtest.py` は小さな実データ…で 1 回実行して末尾の行を返す**」§2-3 |
| 自分の `test_i4r2_time_exit_at_the_open.py:17` の "legacy" の 1 文を消す / A が最小限で変えた `test_i4r1_pending_signal_before_intrabar_exit.py` の形を判断する | リードの答え(d)3「**批評家の周で批評家が検める**」(d)4「**批評家に消させる(検査の 0 に含める)**」 |
| 落ちる試験 + 対照を自分の試験として足す | 委任文 §3 批評家の持ち物「**`tests/bt/critic/item_4/`**」+ リードの起動文「落ちる試験 + 対照を自分の試験として足す(足したら回す)」 |

右が全部埋まっているので、擦り合わせずに着手した。

## 1. 指摘

### i4-c-01 [直す] 射程 = 旧が残っていないか / target = 核(リードの報告) / fix_files = リードの報告(オーナーへの報告の「測っていない範囲」の欄)

- 根拠: 委任文 §2-1 の検査は「記録 `docs/AUDITOR/`・`docs/OWNER_LOG.md`・`docs/DISCUSSIONS/*/item_*/round_*`・`_run*`・過去の委任文を除く」と除外を**名指し**している。打った数え(§3)で、その除外に**名が無い**ファイルに 9 語が残る: `docs/DISCUSSIONS/2026-09-23_backtest_env/REPORT_2026-09-26.md`(14。例: 31 行「旧の golden とビット単位で一致」、93 行「「完全上位互換」(L-407)の例外を認めるか」)・`item_0/PASS.md`(2)・`item_0/battery/AUDIT.md`(13)・`tests/bt/battery/item_0/ROOTCAUSE_r{8,12,13,15,16}-1.md`(7+2+9+2+3)・`tests/bt/battery/item_4/ROOTCAUSE_r2-1.md`(38)・`ROOTCAUSE_r3-1.md`(10)・`item_0/survey_results/attempts/105.log`(2)。B が (c)1 で「記録」と書き、リードが 17:05 UTC に「変えない(過去の周の記録、A-5b)」と決めた。
- 判断: 中身は過去の周の報告・監査・根本原因の記録である。生きている試験がこれらを扱う箇所を打って確かめた(`grep -rl 'ROOTCAUSE_r\|REPORT_2026-09-26\|PASS\.md\|AUDIT\.md' src tests/bt/item_4 tests/bt/critic tests/bt/battery/item_4/*.py` → 6 本。**最初に「0」と書きかけたが打ったら 6 本あった**ので直した): うち 5 本(`test_i4_core_carryover.py`・critic item_0 の 2 本・`diff_scope.py`・`test_battery_item4_claims.py`)は docstring で名を挙げるだけで中身を読まない(`grep -n 'read_text\|open('` で確認)。読むのは 2 本: `tests/bt/battery/item_0/test_battery_item0.py` 1501 行が `ROOTCAUSE_r8-1.md` を読み、撤回 2 句の置換 `WITHDRAWN_FROM_A` を当てたあとの文と照らす。`tests/bt/battery/item_4/test_battery_item4_diffscope.py` 236〜244 行 `test_rootcause_diff_sections_are_machine_made` が `ROOTCAUSE_r3-1.md` を読み、機械が作った差分の節が**手で編集されていない**ことを検める(= この記録を書き換えると試験が落ちる。記録を凍結する仕組みが既にある)。どちらも旧の語を根拠にした判定ではない。よって [止める] ではない。**ただし条件 1 の文面「撤回の注記以外に 0」は、この 11 本を除外に加えない限り字義どおりには満たされていない。**報告に「除外に加えた記録 11 本(ファイル名と件数)」を書く。書かずに「0」と報告すれば A-10(範囲を説明なく縮める)。

### i4-c-02 [直す] 射程 = 正しさ / target = A / fix_files = `src/bot/bt/reference/SPEC.md` §6(120 行)・§8(183 行)

- 根拠: SPEC.md 120 行「mutant: … 事象 8 件・この版 26 件(2026-09-26 の第 1 段の実測では 40 件中 40 件が落ちた。閉じる周で第 1 周の模型の 6 件を消した)」、183 行「40 件中 40 件が落ちた(§6)」。A の (c)「`ref_mutants.py`(34 件)は回していない」。今の 34 件の実測が文書に無い。
- 私の実測(src と tests を私有の複製 `scratchpad/mut_copy/` に写して回した。mutant は `src/` を書き換えて戻すので、他の試験と並走させないため): `cd mut_copy && python3 tests/bt/item_4/reference/ref_mutants.py` → 末尾 `killed 34/34`(m00〜m33 全部 `KILLED`。ログ `scratchpad/ref_mutants_critic.log`)。
- 直し: §6・§8 の「40 件中 40 件」を「この版 34 件(事象 8 + 足 26)中 34 件が落ちた(2026-09-26 閉じる周、批評家の実測)」に。数は 34/34 の実測に合わせる。

### i4-c-03 [直す] 射程 = 統合(設計と実装の食い違い) / target = B / fix_files = `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/REQUIREMENTS.md` 40 行(I4-7)

- 根拠: I4-7「`PYTHONPATH=src python -m pytest` が全件通るか。**既存の試験を落とさない・消さない・飛ばさないか**」が書き直しのあとも残っている。一方、委任文 §2-1(L-474 の (2))は旧の試験 5 本を丸ごと消し、`test_backtest.py`・`test_short_margin.py` から (b) の関数を消した(A の表。§2 で確かめた)。同じ要件ファイルの中で I4-7 の「消さない」と §1 の「(2) 旧の試験…を消す」が矛盾する。
- 直し: I4-7 に注記 1 行「2026-09-26(L-474)で旧の試験 (a)(b) を消した。残した (c) の試験と新エンジンの試験(`tests/bt/`)を落とさない・飛ばさない」。通過の条件は変えない。

### i4-c-04 [注記] 射程 = 旧が残っていないか / target = B(持ち越し)/ fix_files = `tests/bt/battery/item_4/adapters/new_impl.py`

- `NewImpl.run` は `inp.get("model", "spec") != "spec"` で `NotExpressible` を投げる(撤回した「2 出力」の選択子 `model` の受け口が残る)。受けるのは `"spec"` だけで、答えは 1 通りなので [止める] ではない。リードが (d)1 で持ち越した `run_bars(..., rules)`・`split_rows(..., arithmetic)` の引数を落とす周に、この `model` も一緒に落とす。

### i4-c-05 [注記] 射程 = 安全 / target = 核 / fix_files = なし

- 呼び口 `bot.bt.compat.engine.run_backtest` は `sealed.py` の 4 つの門・事前登録を通らない(`grep -n 'sealed\|prereg' src/bot/bt/compat/*.py src/bot/backtest/*.py` = 0)。これは書き換えの前の `bot.backtest.engine.run_backtest` と同じで、研究の関門は `src/bot/research/sealed.py` と `scripts/judge_gates.py` にある(CLAUDE.md §5.0)。関門が呼ばれていることの試験 `tests/test_audit_gates_wired.py` → `12 passed in 0.48s`(私の実測)。この作業で迂回の経路は増えていない。**実データ**: `scripts/run_backtest.py` は `backtest_data/` の恒久スナップショットを読むだけで、書き込みはしない(§4 で実行)。

### i4-c-06 [注記] 射程 = 正しさ(検査が減っていないか) / target = A / fix_files = なし

A の表の (b) の「覆う規則」を `tests/bt/battery/item_4/DEFINITIONS.md` 38〜103 行の規則の文と、`i4_scenes.py` が規則を引く回数(`grep -oE 'R-[A-Z]+[0-9]+' i4_scenes.py | sort | uniq -c`)で突き合わせた。表に出る規則は全部が DEFINITIONS.md にあり、場面が引いている: R-T1(12)・R-T3(4)・R-T4(5)・R-C1(3)・R-A2(3)・R-A3(3)・R-M1(12)・R-M2(7)・R-P1(8)・R-P3(12)・R-P4(2)・R-X1(7)・R-X2(1)・R-W1(4)・R-W2(1)・R-W3(5)・R-H1(5)・R-H2(1)・R-E1(3)・R-E2(1)・R-E3(2)・R-S1(5)・R-O1(26)・R-V2(2)。消した試験の中で場面と形が違うものを個別に読んだ(`git show 09b4733:tests/...`):
- `test_level_is_frozen_and_never_trails`(wick の水準が建てたあとの安値で動かない): R-W1 の文「約定の足 b より前の完了した N 本」が凍結を含意し、独立の参照は水準を約定時に 1 回だけ置く(`bar_sim.py` 307 行 `t.wick_level = …`)。格子 `test_i4_engine_vs_independent_bar_sim.py` は乱歩の足 × wick N∈{1,2,3} でエンジンと参照を比べるので、追随する実装は落ちる。減っていない。
- `test_gap_open_beyond_stop_fills_at_open`: R-P3「値は min(始値, 水準)」、場面 12 件。減っていない。
- `test_swap_carry_reduces_pnl`(6 時間足・3 日の持ち越し): R-S1 に足の秒が入り、場面 5 件 + 格子の bar_seconds∈{60, 3600}。減っていない。
- `test_entry_sides_long_only_equals_allow_short_false_for_a_flat_book`: 2 つの設定の**同値**を見る試験。場面は R-E1(3)と R-T4(5)を別々に固め、同値そのものは固めていない。両方の規則の答えが場面で固まっているので、規則の検査は減っていない(同値の検査だけが無い。[注記])。
- `test_taker_path_unchanged_by_maker_addition`: 中身は「taker で足 2 の合図が足 3 の始値 100 で約定」= R-T1。名前が「maker を足す前と変わらない」という旧の枠だが、検めている挙動は R-T1。減っていない。
- `test_defaults_are_bit_identical_to_passing_nothing`(2 本)→ `test_i4_mouth_signature.py:122 test_defaults_equal_the_same_values_passed_explicitly` に移設されているのを確認。
- (a)「旧の数を固定した試験 = 0」: 消した 7 本の関数名と本体を読み、旧の出力を写した数は見当たらなかった(手計算の数だけ)。A の主張と一致。

### i4-c-07 [注記] 射程 = 統合 / target = 批評家(自分) / fix_files = `tests/bt/critic/item_4/`(下)

- A が最小限で変えた `test_i4r1_pending_signal_before_intrabar_exit.py`(item_4 の adapter をパスで読む `_item4_adapter()`)は**その形でよい**と判断した: 根は全項目の adapter が同名 `new_impl` で、全体の収集順で item_0 の adapter に束縛されること。別の直し方は B の adapter を改名することで、A の持ち物の外。A が消した 6 件は `current_impl` と `"legacy"` に依存し、条件 1 で消える物に依存する試験なので、消すのが正しい。
- 私が整備した(自分の持ち物): 同ファイルの docstring から旧エンジン・互換の規則の 3 文を消し、`_fills(inp, model)` の `model` 引数(2 出力の軸の名残)を落とした。`test_i4r2_time_exit_at_the_open.py:17` の "legacy" の 1 文を消した(リードの答え (d)4)。
- 足した試験: `tests/bt/critic/item_4/test_i4r3_no_old_axis_remains.py`(4 件)— (1) 生きている項目 4 の木(`src/bot/backtest`・`src/bot/bt/compat`・`src/bot/bt/reference`・`tests/bt/item_4`・`tests/bt/critic/item_4`)に 9 語が無い、(2) 対照 = 植えた語を走査が拾う、(3) `RULES == ("spec",)`・`ARITHMETICS == ("decimal",)` で `rules_of`・`split_bounds` が他の名を `ValueError` で拒む、(4) `bot.backtest` の 3 本は AST で docstring・import・`__all__` 以外の文を持たず、`__all__` の名が `bot.bt.compat` の同じオブジェクト。**この試験ファイル自身が 9 語を検査の語として含む(11 出現 = 正規表現の行と植える語)。**§3 の数えではこの 1 本を「検査の語」として別に数える。
- 回した: `tests/bt/critic/item_4` → `82 passed in 21.69s`(整備の前は `81 passed` + 私の対照の 1 件が `tmp_path` の相対パスで落ち、直して通した)。全体の収集 → `20612 tests collected in 5.52s`(A の 20608 + 4)。

## 2. 確かめたこと(主張ではなくファイルとコマンド)

- `src/bot/backtest/engine.py`(11 行)・`metrics.py`(9 行)・`walk_forward.py`(9 行): docstring・`from bot.bt.compat.* import …`・`__all__` だけ。`__init__.py` は 0 行。
- `src/bot/bt/compat/engine.py`(144 行): `_old_arithmetic`・`run_backtest_as_old`・`evaluate_on_splits_as_old`・`route_of` は無い(`grep` 0)。`run_backtest` は `run_bars(events, decide, opts, SPEC, start=strategy.min_history)` → `Metrics(**res.metrics)`。
- `src/bot/bt/compat/barmodel.py` 98〜105 行: `SPEC = "spec"`、`RULES = (SPEC,)`、`rules_of` は `RULES` 以外を `BarModelError`。`grep -nE 'legacy|LEGACY|binary'` = 0。
- `src/bot/bt/compat/walk_forward.py` 28〜29 行: `DECIMAL = "decimal"`、`ARITHMETICS = (DECIMAL,)`。`"binary"` 無し。
- `src/bot/bt/reference/bar_sim.py` の options(33〜36 行 `OPTION_KEYS`、40〜45 行 `UNDECIDED`): 旧側の値・`legacy`・`model` の鍵は無い。
- `tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py`(179 行): 格子は spec の 1 通り(`run_bars(..., "spec", ...)`)、旧側の欄無し。12 種 × 60 升 + 接頭辞 + 出口の到達 + 拒否。
- `src/bot/bt/core/`: `git diff 09b4733 HEAD --stat -- src/bot/bt/core` = 空(核は触られていない)。
- A の全試験のログ `scratchpad/full_close_A.log` 306 行目: `20598 passed, 10 skipped, 4 warnings in 2466.25s (0:41:06)`(A の主張と同じ)。
- 12 本の import(自分で 12 本とも打った。`PYTHONPATH=src python -c "import sys, importlib; sys.path.insert(0,'scripts'); importlib.import_module('<m>')"`): research_anchor / research_anchor_v2 / research_basis / research_fx / research_legacy_elements / research_mainbot_exits / research_signals / research_tournament / research_user_strategies / run_backtest / validate_composite / qa.pipeline_known_answer_taker → **12 本とも `import ok`**。12 本が `bot.backtest` から取る名は `CostModel`・`run_backtest`・`split_data`・`evaluate_on_splits` の 4 つ(`grep -n 'from bot\.backtest'`)で、署名の試験 `test_i4_mouth_signature.py`(13 関数、28 件)が覆う。
- `PYTHONPATH=src python scripts/run_backtest.py backtest_data/binance_XRPUSDT_4h.csv`(23.3 秒、exit 0)末尾:
  ```
  === range_fade ===
    [training] pnl=+0 trades=0 win=0% PF=0.00 sharpe=0.00 maxDD=0.0% expectancy=+0.0/trade fees=0
    [validation] pnl=+0 trades=0 win=0% PF=0.00 sharpe=0.00 maxDD=0.0% expectancy=+0.0/trade fees=0
    [out_of_sample] pnl=+0 trades=0 win=0% PF=0.00 sharpe=0.00 maxDD=0.0% expectancy=+0.0/trade fees=0

  Reminder: only OOS results count. Suspect overfitting when training >> OOS.
  ```
  (動作確認のみ。相場の結論には使わない。A の返り値の `wick_reversal` の行と同じ実行の別の節。)
- 要件 `item_4/REQUIREMENTS.md` の 19 出現: 3・20・22・23・202 行 = 撤回の注記と L-474 の表の逐語引用、54 行 = 呼び口 12 本の名 `research_legacy_elements.py`、91・208 行 = §3.1 で打った SCAN の grep 語 `golden (test|file|output)`。I4-8〜I4-18 は R-*・M-*・D-* と場面集の正解を基準にした文(§1 の I4-7 だけ i4-c-03)。I4-19・I4-20 は撤回の注記のみ。
- 台本 `scripts/workflows/backtest_env.js` 300・383・387 行、`tests/workflows/backtest_env_logic.test.mjs` 111 行 = 撤回の注記。`tests/bt/battery/item_0/test_battery_item0.py` 1492・1493・1508 行 = 記録と照らすための撤回 2 句、`test_battery_def_grids.py` 57 行・`line_judgments.tsv` 666 行・`item_4/DEFINITIONS.md` 864 行・`definitions_review.md` 3 行 = 撤回の注記。`gen_considered.py` 44・46 行・`opponents/CONSIDERED.md` 16・32 行 = SCAN の grep 語(打ったコマンドの記録)。

## 3. 回した試験の末尾の行(全部 `PYTHONPATH=src python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=none --basetemp=<scratchpad>/pt_critic_close/runN`)

| 対象 | 末尾の行 |
|---|---|
| `tests/bt/critic/item_4 tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py tests/bt/item_4/test_i4_mouth_signature.py tests/test_backtest.py tests/test_short_margin.py`(整備の前) | `141 passed in 37.63s` |
| `tests/bt/battery/item_4` | `169 passed in 3.29s` |
| `tests/bt/critic/item_4`(整備 + 4 件を足したあと) | `82 passed in 21.69s` |
| `tests/test_audit_gates_wired.py` | `12 passed in 0.48s` |
| `--collect-only tests` | `20612 tests collected in 5.52s` |
| `python3 tests/bt/item_4/reference/ref_mutants.py`(私有の複製で) | `killed 34/34`(m00〜m33 全部 KILLED) |

## 4. 旧の語の数え(ファイルごと。範囲 = `src tests scripts`(追跡 + 未追跡)と `docs/DISCUSSIONS/2026-09-23_backtest_env`(round_*・_run*・battery/materials を除く)。コマンド: `{ git ls-files -z -- src tests scripts; git ls-files -z --others --exclude-standard -- src tests scripts; } | sort -zu | xargs -0 grep -oE '<9 語>' | cut -d: -f1 | uniq -c` と `git ls-files -z -- docs/DISCUSSIONS/2026-09-23_backtest_env | grep -zvE 'round_|_run|battery/materials' | xargs -0 grep -oE '<9 語>' | cut -d: -f1 | uniq -c`。合計 `src tests scripts` = 129(うち私の検査の試験 11)、docs の範囲 = 58)

| 分類 | ファイル: 件数 |
|---|---|
| 別の意味の legacy(委任文が対象外) | `scripts/data_quality.py` 1 / `research_fx_fundamentals.py` 4 / `research_legacy_elements.py` 6 / `research_matilda_modern.py` 1 / `research_matilda_taro.py` 2 / `research_vr_barrier.py` 2 / `research_wall_front.py` 1 / `run_scalp_paper.py` 3 / `src/bot/exchange/resilience.py` 1 / `src/bot/research/liq_response.py` 6 / `tests/test_intent_map_rule.py` 1 / `tests/test_scalp_logic.py` 2 |
| 撤回の注記(§2 で 1 行ずつ読んだ) | `scripts/workflows/backtest_env.js` 3 / `tests/workflows/backtest_env_logic.test.mjs` 1 / `tests/bt/battery/item_0/test_battery_item0.py` 3 / `test_battery_def_grids.py` 1 / `line_judgments.tsv` 1 / `item_4/DEFINITIONS.md` 1 / `definitions_review.md` 1 / `docs/…/LEAD_DESIGN_items_1-12.md` 2 / `item_{0,1,2,3}/REQUIREMENTS.md` 各 2 / `item_4/REQUIREMENTS.md` 19(うち 3 = SCAN の語と呼び口の名) |
| SCAN の grep 語の記録 | `tests/bt/battery/item_4/gen_considered.py` 2 / `opponents/CONSIDERED.md` 2 |
| 検査の語(私の試験) | `tests/bt/critic/item_4/test_i4r3_no_old_axis_remains.py` 11 |
| **除外に名が無い記録(i4-c-01)** | `docs/…/REPORT_2026-09-26.md` 14 / `item_0/PASS.md` 2 / `item_0/battery/AUDIT.md` 13 / `tests/bt/battery/item_0/ROOTCAUSE_r8-1.md` 7・`r12-1` 2・`r13-1` 9・`r15-1` 2・`r16-1` 3 / `item_4/ROOTCAUSE_r2-1.md` 38・`r3-1.md` 10 / `item_0/survey_results/attempts/105.log` 2 |
| A・B・批評家の持ち物のコード(`src/bot/backtest`・`src/bot/bt/compat`・`src/bot/bt/reference`・`tests/bt/item_4`・`tests/bt/critic/item_4` の検査の試験以外) | **0** |

## 5. 集計

**[止める] 0 件、[直す] 3 件**(i4-c-01 報告の除外の明記 / i4-c-02 SPEC.md §6・§8 の mutant の数 / i4-c-03 I4-7 の「消さない」の注記)、[注記] 4 件。

時間が来て読めなかった範囲: なし(18:07〜18:13 UTC で終えた。`tests/bt/item_4` 全部(A の 19 分の実測)は回していない — 格子・署名の 2 本と reference(mutant の中で 34 回)だけ。場面集 item_0〜3 は回していない(B の `651 passed` は item_0〜4 の合計で、私は item_4 の `169 passed` だけ)。
