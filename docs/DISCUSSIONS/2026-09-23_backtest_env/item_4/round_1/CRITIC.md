# 項目 4「統合と答え合わせ」第 1 周 批評家の記録

委任文 `docs/DATA/delegations/20260925_backtest_env_prompt.md`(指紋 `388d55cdeb32`、`sha256sum` で確かめた)を全部読み、その §3「批評家」「格付けの基準」「場面集の規則」1〜9 に従った。新しく起こされた批評家で、前の周(項目 4 の批評家)は無い。一時ファイルは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/i4_r1_critic_*`。

## 0. 自分で確かめたこと(申告の裏取り)

| 確かめたこと | 打ったもの | 結果 |
|---|---|---|
| 資料係の申告 new_impl_correct=40/40 | `awk -F'\t' 'NR>1{n++; if($4=="正解と一致")c1++; if($7=="正解と一致")c2++} END{...}' materials/runs/new_impl.tsv`(資料係の recount.py を使わずに数えた) | 行 40、1 回目の正解と一致 40、2 回目 40、両方一致かつ「2 回の実行で同じ」40。**40/40 で申告と一致** |
| その表が今のコードで出るか | `run_battery.py --target new_impl / mutant / current_impl` を自分で走らせ、materials の表と場面ごとに class・digest・repro を突き合わせた | new_impl 40/40、mutant 37/40、current_impl 26/40 で資料係と同じ。digest が違ったのは i4-5-outputs・i4-6-label の 2 場面だけで、ダッシュボードの本文の実行 ID(git の作業木の状態を含む内容のハッシュ。作業木の TRACE の変更で変わる)の違い。class は同じ |
| 場面集の外の変更 | `git diff --name-only HEAD` / `git status --short` | `docs/AUDITOR/TRACE/2026-09-26_220780c0.json` だけ(場面係の直しはこの周の前に無い = 第 1 周) |
| 場面集・作業者の試験 | `PYTHONPATH=src python -m pytest tests/bt/battery/item_4 tests/bt/item_4 tests/bt/compat` | `904 passed, 2 skipped`(skip 2 は `test_i4_core_carryover.py:56` の作れない格子点 = set に 2**41 回の hash が要る。理由は試験に書いてある) |
| 項目 0 の場面集の試験 | `PYTHONPATH=src python -m pytest tests/bt/battery/item_0` | `320 passed` |
| 検討表の機械の検査 | `python3 scripts/check_bt_considered.py tests/bt/battery/item_4/opponents/CONSIDERED.md` | `OK 誤り 0 件`(形と語だけ。中身は下の i4-r1-05・08 で読んだ) |
| 全試験(I4-7) | `setsid nohup env PYTHONPATH=src python -m pytest -p no:cacheprovider > scratchpad/bt/pytest_item4_r1_critic.log`(07:54:45 UTC 開始。批評家の試験を足す前に集めた回) | 末尾の行は §4 |

前の周の批評家の試験(`tests/bt/critic/item_4/`)は無かった(この周が初め)。「試験自身の誤り」の報告も無い。

この周で足した批評家の試験(`tests/bt/critic/item_4/`、4 ファイル。壊れた試験は残し、作業者・場面係が直す): `PYTHONPATH=src python -m pytest -p no:cacheprovider tests/bt/critic/item_4` の末尾 `40 failed, 24 passed in 157.88s`。落ちる 40 = i4-r1-01 の 24(spec 12・規則の参照実装 12)+ i4-r1-04 の 3 + 場面集の 13(i4-r1-02 の 1・05 の 6・06 の 6)。通る 24 = 対照 6・互換 6・場面集 5・互換の口の 10 進の値の格子 7(`test_i4r1_compat_decimal_prices.py`: 旧エンジンと新しい互換の口が 1008 升目 × 0.1 刻みの値でバイト単位に一致。作業者の golden の格子が外した「0.5 刻み以外の値」「利確と maker 利確の併用」を足した。**欠陥は見つからなかった**)。

## 1. 指摘(格付けは委任文 §3「格付けの基準」どおり。迷ったものは重い方)

### i4-r1-01 [止める] 実装 — 本来の模型(spec)が、前の足の合図による始値の決済を捨てて、その足の範囲の逆指値・利確で決済する(R-T1 に反する。利確では楽観側の値を黙って返す)

- 規則(DEFINITIONS.md「足の模型の仕様」): R-T1「足 i の合図は、足 i+1 の始値で taker で約定する」。旧エンジン自身の docstring も「a signal at bar i executes at bar i+1's OPEN」(`src/bot/backtest/engine.py:5-6`)。足 j の始値は足 j の範囲(高値・安値)より先に来るので、足 j-1 の合図で始値に閉じた建玉に、足 j の逆指値・利確は掛からない。
- 実装: `src/bot/bt/compat/barmodel.py:388-427` は、足 j で先に逆指値・利確・maker の利確(足の範囲)を見て、当たれば「an exit drops whatever signal was pending for this bar」で合図を捨てる(docstring 30-32 行も同じ)。spec と legacy で分けていない。
- 再現(批評家の試験 `tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py`、打ったもの `PYTHONPATH=src python -m pytest -p no:cacheprovider tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py`): `24 failed, 12 passed`。spec の 12 件(逆指値・利確・maker 利確 × 買い・売り × 反対の合図・CLOSE)が全部落ちる。対照(合図なしなら水準で出る)6 件と、互換(legacy が旧エンジンと同じ)6 件は通る。
- 例(`scratchpad/bt/i4_r1_critic_probe2.py` の出力): 買い建て 100、足 3 で SELL、足 4 の始値 101・高値 110、利確 3%(103)→ spec の出力 `[(2, 100.0), (4, 103.0)]`・損益 90。R-T1 の答えは足 4 の始値 101・損益 30。高値は始値より後の情報で、それを使って始値より良い値で出している(楽観側)。逆指値では始値 105 の決済が 98 になる(悲観側)。
- 格付け: 場面の規則(R-T1)と合わない振る舞い + 黙って誤った値を返す(信頼性)= [止める]。

### i4-r1-02 [止める] 場面集 — 規則の文が「足 j の始値に待つ合図」と「足 j の範囲の逆指値・利確」の順を決めておらず、それを固める場面が無い

- DEFINITIONS.md の R-P3・R-P4・R-X1・R-T1 のどれも、この重なりの順を書いていない(R-H2・R-W3 は時間切れと構造的な逆指値についてだけ「待っていた合図は捨てる」と書く。どちらも始値の決済なので順の問題が起きない)。規則の参照実装を書いた作業者自身が `src/bot/bt/reference/bar_rules.py:22-26` に「taken for the stop and take-profits too」(旧の振る舞いを借りた)と書いている。
- 委任文 §3「項目 4 の場面」は「旧エンジンが自分の仕様から外れる場面(正解は仕様どおりの手計算。互換の口は旧に合わせ、本来の模型は正解を出す)」を求めている。旧の docstring の R-T1 と旧の計算が違うのはまさにこの場面。
- 再現: `tests/bt/critic/item_4/test_i4r1_scene_set_coverage.py::test_a_scene_pins_a_pending_signal_against_an_intrabar_exit` が落ちる(全場面の期待の約定・合図・水準から機械で探して 0 件)。
- 直す先: 規則の文(R-T1 と R-P3・R-P4・R-X1 の順)を足し、legacy と spec の 2 つの出力の場面と spec の値の場面を置く。

### i4-r1-03 [止める] 実装 — I4-1 の場面が使う参照実装 `bar_rules.py` は、核と新エンジンを読んだ作業者が書いたもの(「核を見ずに別の作業者が書く」に当たらない)

- 成果物の記載(自己申告ではなく成果物の文): `src/bot/bt/reference/bar_rules.py:7-12`「Who wrote it: the item-4 worker (not the reference role ...)」、`src/bot/bt/reference/SPEC.md:164`「書いた作業者は核と新エンジンのコードを読んでいる」。新実装の adapter は `reference: true` をこの `run_rules` で答える(`tests/bt/battery/item_4/adapters/new_impl.py:102-107`)。よって表の I4-1 の 2/2 は「別の作業者」の突き合わせではない。
- 独立でないことの害が実際に出ている: i4-r1-01 の欠陥を bar_rules も同じ形で持つ(同じ試験の reference の 12 件が落ちる)。本体と参照が同じ誤りを共有し、突き合わせが一致してしまう = 委任文が参照実装の分離で防ごうとしたもの(要件 §1「核のバグをそのまま模倣してしまう」)。
- 参照実装の役の成果物(`bar_sim.py`・`event_sim.py`・`num.py`・`SPEC.md`、`tests/bt/item_4/reference/`)は、核のモジュールの import が無い(`grep -n "import\|from " src/bot/bt/reference/*.py tests/bt/item_4/reference/*.py`)。核の class・def の名 253 個(`grep -ohE "^(class|def) [A-Za-z_]+" src/bot/bt/core/*.py`)を参照実装の側で探すと、当たりは `Event`・`Fill`・`Strategy`・`_levels` だけで、`Event` は別の欄(`t_exch`・`t_recv`・`seq`)、`_levels` は引数の順(`raw, name, descending` 対 核の `name, raw, descending`)・数量の条件(> 0 対 核の ≥ 0)・例外の型が違う。**写しの形は見当たらない**(判断の根拠はこの 3 点。agent の記録は読めないので成果物の形だけで判断した)。問題は bar_rules.py だけ。
- 直す先: 規則の文(R-*・M-*)の参照実装を参照実装の役に書かせる(要件の行「参照実装:4」)。

### i4-r1-04 [止める] 実装 — 実データの規則(委任文 §4)が呼び手の書く `origin` の一語に依っている

- `src/bot/bt/pipeline.py:228`(`origin` は呼び手が書く「real」/「synthetic」)、`:255`(`real = any(d["origin"] == "real" ...)`)。この環境の市場データのファイルを `origin: "synthetic"` と書けば、値で条件づけた戦略(`price_rule`)が目的「動作確認」で走る。
- 再現: `tests/bt/critic/item_4/test_i4r1_origin_is_not_a_self_label.py`(fx_1m・jpx_1m・fx_ticks の 3 ファイル)が 3 件とも `Failed: DID NOT RAISE ValueError`。`scratchpad/bt/i4_r1_critic_probe5.py` の出力「ACCEPTED: price_rule on a real file labelled synthetic ... fills: True」。
- 要件 I4-6「実データを通す実行の戦略が時刻だけ…に限られ、信号・条件付け・最適化を持ち込んでいないか」を構造で満たしていない。データ層は `qa_*` などを合成・中間物として知っている(`src/bot/bt/data/allowlist.py:55-56`)ので、出所はデータ層の側で決められる。場面 i4-6-signal-refused にも、この偽の一語の変形が無い(場面集の側でも足す)。

### i4-r1-05 [止める] 場面集 — 観点の本題でない条件(足 0 の合図、I4-10 の maker と taker の手数料の違い)で、強い足の道具が「結果なし」になり、検討表がそれを「持たないと確認した」と書く(偏り + 規則 6)

- 場面: I4-10・I4-12・I4-13・I4-15・I4-17 は、値の場面の**全部**が足 0 に合図を置く。I4-10 の唯一の値の場面 i4-10-priority は maker 0.02%・taker 0.1% を分ける。再現: `test_i4r1_scene_set_coverage.py` の `test_a_value_scene_without_a_bar_0_signal[I4-10/12/13/15/17]` と `test_the_stop_priority_viewpoint_has_a_scene_with_one_fee_rate` が落ちる。
- 害(materials/survey_breakdown.tsv・runs/opp_*.tsv): i4-10-priority で Backtrader・backtesting.py・vectorbt・VnPy・PyBroker・zipline-reloaded の理由は「maker と taker で違う手数料」(backtesting.py はさらに「足 0 の合図」)だけ。I4-10 は「逆指値が先か」の観点で、手数料は観点でない。backtesting.py は I4-12・I4-13・I4-14・I4-15 でも「足 0 の合図」で結果なし。調査結果の側の I4-10 は 0/1(最良は予測市場の道具が値の範囲 [0,1] で断った「対応なし」)になり、新実装が勝つ観点が場面の作りで増えている(委任文 §3「場面が新実装に有利な範囲に偏っていないか」)。
- 規則 6: 検討表は、これらを I4-10 の「持たないと確認した」に置き、理由は別の能力(手数料の数・足 0)の欠け(`opponents/CONSIDERED.md:179`・`180`・`182`・`191`・`194`・`207`・`219`、I4-12 の `295`・`309`、I4-13 の `347`・`361`、I4-15 の `452`・`468`)。規則 6 が求めるのは「その能力に当たる口」を探した結果で、観点の能力(逆指値の先・時間切れ・持ち越し)の口ではない。

### i4-r1-06 [止める] 場面集 — I4-2 の性質の場面が taker だけの格子で、不変条件が正解の一致から自動で従う(観点を覆っていない)

- `tests/bt/battery/item_4/i4_scenes.py:257-318`: 30 の場合は全部 `taker_rule`(逆指値・利確・maker・持ち越し・時間切れ・構造的な逆指値なし)。`i4_judge.py:114-155` の不変条件も taker の手数料だけで式を立てる。約定・損益・資産を正解と完全に突き合わせたうえで検める不変条件は、正解が満たす式なので新しく何も捕まえない。
- 要件 I4-2「実装の場合分けから入力を作らない敵対的な入力の格子で、数量保存・PnL の恒等式…」に対し、恒等式が壊れやすい経路(逆指値の値の選び・maker の手数料・持ち越し・取り逃し)が格子の外。再現: `test_i4r1_scene_set_coverage.py::test_the_property_grid_reaches_the_path[...]` 6 件が落ちる。性質の場面は正解を要さずに不変条件だけで判定できる(正解が手で出せない経路こそ性質で見る)。

### i4-r1-07 [止める] 場面集 — I4-3 の「核・参照実装・新エンジン全体のそれぞれの粒度」のうち、核の粒度の値の場面が無く、理由も書かれていない

- 要件 §2 I4-3 の文。場面は i4-3-e2e-taker・i4-3-e2e-maker(エンジン全体)と i4-1-*(参照実装)だけ(`grep -n 'id="i4-' tests/bt/battery/item_4/i4_scenes.py`)。DEFINITIONS.md「場面にできない観点」は I4-7・I4-19・I4-20 だけで、I4-3 の核の粒度を外した理由が無い(A-10「説明なく縮める」の形)。

### i4-r1-08 [止める] 場面集 — 検討表が「読んでいない」「読んだ範囲に無い」を「持たないと確認した」に数えている(規則 6)

- `opponents/CONSIDERED.md` で、判断が「持たないと確認した」かつ理由に「読んでいない」か「読んだ範囲に無い」がある行: 151(I4-9 Hikyuu)・446・449・470・472・483(I4-15)・529(I4-16)・563・566・582・586・587・589・600(I4-17)・624・627・643・647・648・650・651・653(I4-18)。打ったもの: `awk '/^### 観点/{vp=$3} /\| 持たないと確認した \|/ && /読んでいない|読んだ範囲に無い/{print NR, vp}' CONSIDERED.md`。
- 規則 6:「持たないと確認した」と書けるのは「その能力の口が無いことを行を引いて示したとき」。例: 582 行(I4-17 QuantConnect)の理由は「統計の出力(Statistics)は読んでいない」。読んでいないものは「無い」の根拠にならない(O-2)。DEFINITIONS.md 末尾の吟味は「読んでいない部分に依る場面は…検討表では「再現できない」に数えた」と書いており、表と食い違う。

### i4-r1-09 [直す] 場面集 — 変形の能力の場面が、断りの理由を見ずに「正解と一致」にする(i4-6 の 2 場面で、規則を持たない対象と見分けられない)

- `tests/bt/battery/item_4/run_battery.py:141-146`: 変形を断れば理由を問わず「正解と一致」。i4-6-signal-refused の変形は `price_rule` への差し替えだけで、`price_rule` を一切走らせられない対象も断れば満点になる(合成と宣言したデータで `price_rule` が通る対照が無い)。i4-6-research-refused も「研究」を一切作れない対象と見分けない(事前登録つきの「研究」が通る対照が無い)。新実装は両方の対照を満たす(probe5 の結果)ので、今の表の値は変わらない。規則 1(能力は結果で)の穴として直す。

### i4-r1-10 [直す] 場面集 — 新実装の adapter が互換の出力を旧の名前の口(`run_backtest`)ではなく `run_bars(rules="legacy")` から取る

- 委任文 §3「項目 4 の場面」: 旧 14 の部分の「新実装」は「互換の口(旧と同じ名前・同じ引数で旧と同じ出力)と新エンジン本来の模型の両方を持つもの全体」。`adapters/new_impl.py:86-99` は `bot.bt.compat.run_bars` を直接呼ぶ。自分で確かめた影響: 全場面の足の入力 56 件を `bot.bt.compat.engine.run_backtest`(旧の名前・旧の引数)と adapter の legacy で走らせて 0 件の違い(`scratchpad` の一回きりの確かめ、出力「compared 56 differ 0」)。今の値は変わらないが、表の legacy が互換の口を通っていない。

### i4-r1-11 [直す] 場面集 — lumibot(67)・Hikyuu(60)・zvt(56)は導入を試さず、依存の数(320・104・57 件)を理由に再現へ置き換えた

- `opponents/RUNNABILITY.tsv` の 56・60・67 行。委任文 §3「調査結果の側の選び方」は「§4 の安全の規則で scratchpad の venv に入れて動かせるものを全部」通す。依存の数は §4 の検査の項目(PyPI と GitHub の一致・公開日・ダウンロード数・保守者・難読化・導入時の実行・外部送信)に無い。再現の忠実さは抜き取りで確かめ、弱められていなかった: lumibot の `order.py` 776-808 行(子の注文は LIMIT が先、`dependent_order`)と LEAN の `FillModel.cs` 347-400・697-760 行(逆指値は `prices.Low < StopPrice` で `Math.Min(StopPrice, prices.Current - slip)`、指値は `Low < limit` で `Math.Min(High, limit)`、置いた足で判定しない)を一次資料(読むだけ、`scratchpad/bt/i4_r1_critic_lumibot_order.py`・`i4_r1_critic_lean_FillModel.cs`)で読み、再現のコードと一致。導入の試み(容量が足りなければその実測)を記録に足す。

### i4-r1-12 [直す] 実装 — 互換の口が、旧エンジンが計算していた入力(高値 < 安値の行、NaN の行)を断る(「完全上位互換」との関係をリードに上げる)

- `src/bot/bt/compat/engine.py:18-21`(「One difference from the old engine, on purpose」)、`tests/bt/compat/test_compat_golden.py` の最後の試験がそれを固める。要件の I4-8〜I4-18 の列挙には無い振る舞いで、信頼性の向き(黙って計算しない)だが、L-407「完全上位互換」の語と食い違いうる。旧を import する 12 本が実データでこの行に当たるかは測っていない。作業者の報告の「リードに聞くこと」に載っているかを確かめ、無ければ載せる。

### i4-r1-13 [直す] 場面集(項目 0)— 第 16 周の [示唆] i0-r16-05 が未処置で、場面の導き方の文が範囲を書かない「作れない」を言う

- `tests/bt/battery/item_0/scenes.py:376-386`(p2-us-float-held の導き方):「「持つ値にナノ秒より細かい端数がある」float はマイクロ秒では作れない」。これは 2^50〜2^51 の範囲でだけ正しい。小さい時刻では作れる: `to_nanos(1.0000001, 'us')` の入力は 1.0000001000000000583867… マイクロ秒を持つ(打ったもの `PYTHONPATH=src python3 -c "from bot.bt.core import to_nanos; ..."`)。核は正しく断る(TimestampUnitError)ので実装の欠陥ではないが、P0-2 の単位の場面に us の float-subns の形が欠けている(s・ms にはある)。
- 項目 0 の通過の記録 `item_0/PASS.md` の「並行して直すもの」の i0-r16-05。i0-r16-04(NO_INT の 5 場面の断りと入口なしの見分け)の直しは、`scenes.py:306-392` と `run_battery.py:705-771`(断りの記録で対象の入口の断りかを確かめ、確かめた断りだけを正解に数える)を読んで、向きが正しいことを確かめた(独立の確認が無かった点)。

### i4-r1-14 [直す] 実装 — 実データの動作確認の試験の文と手順が違い、「答えた」の判定が緩い

- `tests/bt/item_4/test_i4_real_data_smoke.py:6` は「hh:00 に買い、hh:05 に売る」、109-110 行の手順は hh:20・hh:25。138 行は注文の状態が `OPEN`・`ACKED` でも「答えた」に数える(約定しないまま残った注文を見分けない)。

## 2. 射程の外として [示唆] にしたもの

無し(この周で、戦略が Python のプロセス自体を書き換える形の反例は探していない)。

## 3. リードへの注記(指摘ではない)

- 要件のファイル §1(b)「この周の批評家の [止める] が 0 件になったとき」だけ最後の段(旧の 3 本の置き換え)をしてよい、とある。L-451 以後は批評家の [止める] が通過を止めないので、[止める] が残る限り最後の段(I4-20)は起きない。要件の固定はリードの持ち物なので、書き換えるかはリードが決める。
- I4-19(golden): `tests/bt/compat/golden/old_engine_golden.json` が在り、旧の 3 本の sha256 と一致する試験が通る。I4-20(最後の段): この周では行われていない(条件の手前)。測っていない。

## 4. 全試験(I4-7)

`setsid nohup env PYTHONPATH=src python -m pytest -p no:cacheprovider`(07:54:45 UTC 開始、ログ `scratchpad/bt/pytest_item4_r1_critic.log`)の末尾: `19941 passed, 10 skipped, 4 warnings in 1464.59s (0:24:24)`。落ちた試験 0。この回は批評家の試験を足す前に集めた(批評家の試験 4 ファイルは入っていない。入れた回の結果は §0 の `40 failed, 24 passed`)。I4-7 は、批評家の試験を除けば満たしている。

## 5. 提出前の吟味(批評家の文)

- 指摘ごとの根拠の再現: 01・02・04・05・06 は批評家の試験を自分で走らせ、落ち方(DID NOT RAISE・期待の約定との食い違い)を見た。03・07・08・10・11・12・13・14 はファイル:行と打ったコマンドの出力を上に写した。
- 格付けの見直し: 01(規則との不一致 + 楽観側の誤った値)・03(要件の行)・04(要件 I4-6)・02・05・06・07・08(場面集の規則 6 と観点の網羅)は [止める] の基準に当たる。09・10 は今の表の値を変えないことを自分で確かめたので [直す]。11 は再現が一次資料どおりと抜き取りで確かめたので [直す]。12 は要件の列挙の外で信頼性の向きなので [直す](リードの判断が要る)。13 は核が正しく断ることを確かめたので [直す]。14 は文と判定の緩さで [直す]。
- 相手の付け違い: fix_files に `src/bot/bt/` を含むのは 01・03・04・12(実装)。14 は作業者の試験 `tests/bt/item_4/` なので実装。場面集の側は全部 `tests/bt/battery/` の下だけ。
- 前の周の指摘: 項目 4 の前の周は無い。項目 0 の持ち越しは 13 で扱った。
- 場当たりの直し(場面の特別扱い): `grep -rn "i4-[0-9]" src/bot/bt/ --include=*.py` は 0 件、adapter は場面の id・正解を読まない(`adapters/new_impl.py` の全文を読んだ)。patchwork の指摘は無い。
- 終わる条件: この記録は 1 回で書き、上限(1 周)で止める。見つけて確かめきれなかった物: I4-5 の実データの統合の数値の中身(委任文 §4 で数値を人の読む文書に入れないため、形だけ見た)。
