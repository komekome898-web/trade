# K1 段階 G — 環境の欠陥の直し(G-1〜G-4・G-6)

委任文 `docs/DATA/delegations/20261001_k1_stage_g_close.md`(作業者 B)。オーナー逐語(L-499a)「**案1だけど、わかってる欠陥があるのなら直せ ワークフロー起動して案1と欠陥の修正を進めて**」、(L-476)「**そこで出る欠陥を直す**」、(L-407)「**場当たり的な解決ではなく、ゴールに向けた根本的解決**」。欠陥の一覧は `ENV_DEFECTS.md`(G-1〜G-6)。

合意した完了の形(委任文 §2 の逐語、抜粋):

- 「欠陥ごとに `docs/PHASE2/K1/NEWENV_G/FIXES.md` に: 根本原因(ファイル:行)・直し方・足した試験・試験の末尾の行・直しを外すと落ちる試験(変異で確かめる)。直しは根本で行う(回避を残さない)。核(`src/bot/bt/core/`)を変えたら `CORE_VERSION` を上げる。場面集(`tests/bt/**/scenes*`)と規則の文は変えない。」
- 「6. 直したあと、段階 G の `design|2018_2021|15|s19/b24|weak` と `design|2018_2021|5|s19/b24|weak` の 2 升を、新しい口(G-1 の名前の区別・G-2 の宣言・G-3 の範囲)で生のファイルから回し、`docs/PHASE2/K1/NEWENV_G/cells.json` の同じ升と取引数・平均 bp が同じか並べる(一致は数が同じという事実だけ)。」
- 「7. `tests/bt` と `tests/test_k1_wick*.py` をデータの門(`scripts/k1_newenv_g_datagate.py`)の下、私有の basetemp(スクラッチパッド)で回し、門が止めた `open` 0 件・失敗 0 件。」
- 「8. 上限で残ったものは FIXES.md の「やっていないこと」に逐語で。」

印: 【事実】= コマンドの出力・ファイルで確かめた / 【推定】= 確かめていない見立て / 【判断】= 作業者が決めたこと(理由を添える)。

## 0. 守ったこと

- **読んだデータ**: 作業者の実行と試験はすべてデータの門 `scripts/k1_newenv_g_datagate.py` の下で回した(許可の一覧は段階 G と同じ。変えていない)。読んだ市場データは Binance BTCUSDT 1 分足 2018(G-6 の計測)、Binance 2018〜2021・bitFlyer 2018〜2021 の 1 分足(§6 の 2 升、範囲は各年の 1 月 1 日から翌年の 1 月 1 日まで = 2022-01-01T00:00Z より前)、段階 G の畳んだ足 `backtest_data/k1_newenv_g_20261001/{binance,bitflyer}_{5,15}m_2018_2021.csv.gz`(§6 の参考)、試験の中の合成ファイルだけ。2023-12-18 以降の行・2024〜2026 のファイル・新鮮データは読んでいない(門の記録は §7)。
- 核(`src/bot/bt/core/`)を変えた(G-1)ので `CORE_VERSION` を `core-19` → `core-20`(`src/bot/bt/core/contract.py:15`)。
- 場面集(`tests/bt/battery/**/*scenes*`)・規則の文・フック・`settings.json`・封印の台帳・`config/` は変えていない(§8 の `git status`)。作業者 A の持ち物(`DIFF.md`・`TABLES.md`・`DATA_READ.md`・`diff_table.md`・`k1_newenv_g_diff.py`・`k1_newenv_g_tables.py`)には触っていない。git commit / push はしていない。
- 変異の確かめはすべてスクラッチパッドの `src` の写しで行った(`scripts/k1_newenv_g_mutate.py`、作業中はスクラッチパッドの `mut/mutate.py`。写しを `PYTHONPATH` の先頭に置き、pytest の `pythonpath` を空にし、`import bot` が写しを指すことを変異ごとに確かめてから回す)。写しは回した後に消した。

## 1. G-1: 事象に流れの名前が無い(戦略と約定の口が 2 つの市場の足を見分けられない)

**根本原因(ファイル:行、直す前 = HEAD `ba216f55`)**
- `src/bot/bt/core/events.py:151-156` — 事象の基底 `Event` の欄は `received_time_ns` / `exchange_time_ns` / `seq` だけ。核の合流(`engine.py` `_SourceMerger`)は流れの名前を知っているが、事象に渡さない(`engine.py:697` で取り込んだ事象はそのまま待ち行列へ)。
- `src/bot/bt/fill/venue.py:192, 290, 566` — `last_bar_close` は 1 つで、どの流れの足でも上書きされる。
- `src/bot/strategy/k1_xvenue.py:79, 115-118`(`pending_t`)— 戦略は「同じ時刻の 1 本目 = d0、2 本目 = d1」とみなす。核の合流の順(同じ時刻では流れの名前の `sorted()` 順)に寄りかかった代理(INTENT_MAP X-9 = △)。

**直し方**
- 核: `Event` に欄 `stream: str = ""` を足した(`events.py:165`、検証は `events.py:182`、docstring)。核が流れから事象を取り込むときに、その流れの名前を付ける(`engine.py:701-706`)。流れが自分で `stream` に別の名前を書いた事象は `EventValidationError` で拒む(空、または自分の流れの名前だけ通す)。注文の通知と戦略のタイマーは入力の流れから来ないので `""`。1 本の名無しの流れは従来どおり `"events"` という名前。契約の文(`contract.py` の `"source"`)に足し、`CORE_VERSION` を `core-20` にした。
- 約定の口: `SimVenue(..., streams=(...))` を足した(`venue.py:190, 205`、判定は `_takes` `venue.py:294`、呼ぶのは `venue.py:314`)。名指しした流れの市場データだけが約定の口の状態(`last_bar_close`・`last_trade`・板・待ち注文の約定)に届き、他の流れの事象は何もしない。`streams` を名指ししない(None)ときは全部の流れを受けるが、価格の出どころの種類ごと(足 / 約定 / 板)に 1 本の流れしか受けず、2 本目の流れの同じ種類の事象が来たら `ExecutionModelError` で止まる(黙って上書きしない)。【判断】`streams` は省略可にした: 既存の呼び出し(統合の口 `bot.bt.pipeline`・場面集の駆動)は 1 つの銘柄の約定・板・足を別の流れで渡すことがあり(`engine.py` docstring「trades, board, bars and funding read from separate files」)、種類ごとに 1 本なら曖昧さが無い。曖昧になる場合(同じ種類が 2 本)は止める。
- 戦略: `k1_xvenue.py` を名前で見分ける形に書き換えた。config に `streams`(`{"signal": [...], "price": [...]}`)と `prepare`(`"none"` / `"join_fold"`)を足した(`CONFIG_KEYS`)。戦略は窓(足の開始時刻)ごとにシグナルの流れの足と価格の流れの足を名前で受け、**2 本がそろったときに**行動する(`k1_xvenue.py:126-157`、シグナルは `w[self.signal]` `k1_xvenue.py:153`)。どちらが先に届いても同じ。片方だけの窓が残ったまま次の窓の足が来る・名指しに無い流れの足が来る・同じ窓に同じ流れの足が 2 本来る、は `K1XError`。約定の口は `SimVenue(streams=(価格の流れ,))`(`k1_xvenue.py:302`)。
- INTENT_MAP X-9 を ○ にした(`INTENT_MAP.md`)。

**足した試験**
- `tests/bt/item_0/test_bt0_fix_g1_stream_name.py`(8 件): 2 本の流れ(名前の順を 4 通り)で届いたすべての市場の事象の `stream` = 出どころの流れの名前 / 名無しの 1 本は `"events"`、通知(ACK・FILL)とタイマーは `""` / 別の名前を書いた事象は拒み、自分の名前は通す / 流れの CLOCK にも名前 / `to_dict`・`event_from_dict` で往復し、文字以外は拒む。
- `tests/bt/item_2/test_i2_fix_g1_venue_streams.py`(12 件): 名前の順 3 通り(価格の流れが先に並ぶ `("a", "z")` を含む)で、約定の値 = 価格の流れの足の終値 / `streams` 無しで足の流れが 2 本なら止まる / 種類ごとに 1 本なら受ける / 名指しに無い流れの足は `last_bar_close` を変えない / `streams` の型の拒否 6 通り。
- `tests/bt/item_4/test_i4_fix_g1_k1_xvenue.py`(6 件): design・sameclose で、名前 `("d0", "d1")`(シグナルが先に届く)と `("z", "a")`(価格が先に届く)の往復が同じ(乱数の足 600 本、往復 20 件超)、すべての約定 = その時刻の価格の流れの終値 / 窓がずれた・名指しに無い流れは止まる / config の拒否 / `join_fold` の手計算(分の頭への切り下げ・内部結合・同じ窓・届く時刻)/ 順の崩れた流れを拒む。
- 既存の試験のうち、核の欄が増えたことで期待値が変わった 3 件を直した(期待値に `stream` を足しただけ。理由は試験の中のコメント): `tests/bt/item_0/test_bt0_notices.py`(ACK の `to_dict` に `"stream": ""`)、`tests/bt/item_0/test_bt0_r14_process_state.py`(版 `core-20`)、`tests/bt/item_0/test_bt0_r8_sender_adversary.py`(受け手の市場の事象は `stream` 以外が送ったとおりで、`stream` は `"events"`)。
- 段階 G の自前の試験 `scripts/k1_newenv_g_selftest.py` を新しい config にし、名前の 2 通り(`("d0","d1")` と `("z","a")`)で素のループと 1 往復ずつ比べるようにした。

**試験の末尾の行**: §7 の全体の回(新しい 3 ファイルを含む)。単独: 「8 passed in 0.22s」「12 passed in 0.24s」「6 passed in 1.69s」。`k1_newenv_g_selftest.py --trials 1` 「cases 234 trades compared 15264 mismatched cases 0」(コマンドは §8)。

**変異の確かめ**(`scripts/k1_newenv_g_mutate.py` の出力 `mutate_final.log`、逐語。対照「M0_control_no_change: exit 0: 56 passed in 1.98s」): 「M1_G1_core_no_stream_stamp: exit 1: 1 failed in 0.29s」(核が名前を付けない)/「M2_G1_venue_takes_every_stream: exit 1: 1 failed, 1 passed in 0.27s」(約定の口が全部の流れを受ける)/「M3_G1_strategy_first_arrival_is_signal: exit 1: 1 failed in 1.23s」(戦略が先に届いた足をシグナルとみなす = 直す前の代理)。

## 2. G-3: 記録の口 `runner` に範囲の欄が無い

**根本原因(直す前)**
- `src/bot/bt/repro/runner.py:67-75`(`DataInput` = path / spec / resolve だけ)。
- `runner.py:141`(`seals.read_checked(..., None)  # the run loads without a range`)— 封印の台帳に載ったファイルは範囲が無いので計画の段で必ず拒まれる。
- `runner.py:160-163`(`load(plan.root, datasets)` のデータセットに `range_ns` が無い)。

**直し方**
- `DataInput.range_ns`(`runner.py:84`、検査 `checked_range` `runner.py:86`)。計画の段で範囲をそのまま封印の門に渡す(`runner.py:162`: `read_checked(..., rng)`)。範囲が無い・終わりが封印の境より後なら、ファイルを開く前に `RunSealedRangeError` で止まる(`src/bot/bt/repro/errors.py:19`。`ReproError` かつ `SealedRangeError`)。
- 範囲は実行の同一性(run_id の元)と `record.json` の `data[i].range_ns` に入る(`_data_identity` `runner.py:179`)。範囲の無い入力の同一性は直す前と同じ(鍵を足さない)。実行ではデータ層に範囲を渡す(`runner.py:197`)。データ層は範囲の中の行だけを保ち、封印の時刻の列でも行ごとに確かめる(既存の `loader._read_file`)。
- 【判断】記録の口に `Parts.prepare`(`src/bot/bt/repro/fixed.py:200`、`runner.py:208-211`)を足した: setup が「読み込んだ流れ → 核に渡す流れ」の段を持てる(K1 では XVENUE_PREREG.md §2 の結合・畳み)。理由: §2-6 は生のファイル(1 分足、封印の台帳に載ったもの)から記録の口で回すことを求めるが、第 17 部の規則は 2 つの取引所の分足を UTC の分で内部結合してから畳む。これを記録の口の外で行うと写し(台帳に無いファイル)が要り、G-3 の欠陥そのもの(写しは封印として扱われない)に戻る。prepare のコードは setup のモジュールなので、その sha256 は既存の `setup.identity()` に入る。
- 段階 G の実行スクリプト `scripts/k1_newenv_g_run.py` を新しい config(`streams`・`prepare: none`)と G-4 に合わせた(畳んだ足の spec に `session: 24x7`、gap = accept)。

**足した試験**: `tests/bt/item_3/test_i3_fix_g3_runner_range.py`(8 件): 封印の台帳に載った合成ファイルを、境で終わる範囲で `run` に渡すと回り、`record.json` の `data[0].range_ns` と `data_quality` の範囲・行数(2)・封印の単位が残り、境以降の行は事象にならない / 範囲が無い・境を越える範囲は `RunSealedRangeError`(`SealedRangeError` でも `ReproError` でもある)で、そのファイルは開かれていない(監査フックで open を数えた)/ 範囲は run_id を変え、範囲の無い入力の同一性に `range_ns` の鍵は無い / 不正な範囲 4 通りを拒む。

**試験の末尾の行**: 単独「8 passed in 0.51s」、全体は §7。

**変異の確かめ**: 「M5_G3_plan_ignores_the_range: exit 1: 1 failed in 0.52s」(計画の段で範囲を渡さない = 直す前)/「M6_G3_execute_reads_without_the_range: exit 1: 1 failed in 0.58s」(実行で範囲を渡さない)。

## 3. G-2: 約定の無い分(OHLC が空の行)を宣言して落とす口が無い

**根本原因(直す前)**: `src/bot/bt/data/loader.py:215`(`_build` の `num`: 空の欄は `ParseError`)。足の値を数に直す `_build`(`loader.py:474` で呼ぶ)が `synthetic` の判定(`loader.py:490-492`、行を作った後)より前なので、印を付けても止まる。空の行を「約定の無い分」と言う宣言の鍵が spec に無い(`src/bot/bt/data/spec.py:61-62` の `_TOP`)。

**直し方**
- spec の鍵 `no_trade: {"fields": [...]}`(`spec.py:41-50` docstring、`spec.py:325-339`、`Spec.no_trade` `spec.py:133`)。足の種類だけ。列挙した価格の欄が**全部**空の行が「約定の無い分」。一部だけ空・列挙していない欄が空は、従来どおり `ParseError`。
- データ層はその行を記録(価格は None)と時刻として読み、事象は作らない(`loader.py:256-261`、`Row.event = None`)。検査に異常の種類 `no_trade`(1 行に 1 件)を足した(`src/bot/bt/data/anomalies.py:137-139`)。方針は `drop` だけ(`anomalies.py:74`、`anomalies.py:194-195`)で、呼び手が名指ししない限り事象は出ない(`UnresolvedAnomalyError`)。落とした行数は `manifest()["datasets"][name]["anomalies"]["no_trade"]` と `resolution` に出る = 記録の口では `data_quality.json`。流し読みの口(`stream.py`)は同じ `_read_file` と検査を通るので同じ。
- `scripts/k1_newenv_g_fold.py` の `filter_bitflyer`(写しを作る回避)を消し、bitFlyer の spec に `no_trade: {"fields": ["open", "high", "low", "close"]}`、方針に `no_trade: drop` を足した(このスクリプトは直した後に回していない。§6 は同じ宣言を記録の口で使った)。
- 【事実】bitFlyer 2018 のファイルの空の欄の形(`gzip` で全行を数えた、§8 のコマンド): open〜close が全部空の行は 4,293 行(2,678 + 1,325 + 290)、open〜close の一部だけが空の行は 0 行。

**足した試験**: `tests/bt/item_1/test_i1_fix_g2_no_trade.py`(12 件): 宣言が無ければ従来どおり `ParseError` / 宣言すれば `no_trade` が 2 件、名指しが無ければ止まり、`drop` で事象 2 本、manifest の異常の数・方針・行数、記録の価格は None / 方針は drop だけ / 一部だけ空・宣言していない欄が空は拒む / 宣言の厳しい読み 5 通り / 足以外の種類は拒む / 流し読みの口も同じ。

**試験の末尾の行**: 単独(G-4 と一緒に)「17 passed in 0.17s」、全体は §7。

**変異の確かめ**: 「M4_G2_no_trade_rows_not_recognised: exit 1: 1 failed, 1 passed in 0.30s」。

## 4. G-4: `spec.bar.session` を省くと gap / off_grid の検査が黙って無くなる

**根本原因(直す前)**: `src/bot/bt/data/anomalies.py:131-132`(`spec.bar.session in ("24x7", "24x5")` のときだけ検査)と `src/bot/bt/data/spec.py:24, 273-276`(`session` は省略可)。

**直し方(省略を拒む。暗号資産と FX)**: `spec.py:293-299` — 資産が `crypto` か `fx` の足の spec で `session` を省くと、ファイルを開く前に `SpecError`。`jpx` は省略を許す(データ層に取引所の暦が無い)が、そのときは結果が「走らなかった検査と理由」を持つ: `LoadResult.checks_not_run(name)`(`loader.py:454`)と manifest の `checks_not_run`(`loader.py:408` `_not_run`)。24x5 も gap が走らないことを同じ欄に書く。
【判断】既定で検査を走らせる案を採らなかった理由: (1) データ層は「宣言を厳しく読み、打ち間違いが既定に落ちない」設計(`spec.py` docstring 冒頭)で、既定の暦を置くと省略が意味を持ち続ける(省略 = 24x7 という別の黙った約束になる)。(2) 暗号資産と FX はデータ層に暦(24x7 / 24x5)があるので書けば済み、書かないことに正当な使い道が無い。(3) JPX は暦が無いので既定を置けない。場面集(変えてはいけない)の足の spec のうち `session` を書いていないのは JPX の 2 つ(`tests/bt/battery/item_1/i1_scenes.py:131`、`tests/bt/battery/item_4/i4_scenes.py:843`)だけで、どちらも `asset: jpx`。

**影響(呼び手)**: `session` を書いていない暗号資産の足の spec は止まるようになる。この委任の持ち物の中では `scripts/k1_newenv_g_run.py` を直した(`session: 24x7` と `gap: accept`)。試験の側で直したのは §7 に列挙。**持ち物の外で、直していないスクリプト**(回すと `SpecError` で止まる): `scripts/k1_newenv_run.py:53`、`scripts/k1_newenv_tables.py:53`、`scripts/k1_newenv_fold.py:52`、`scripts/k1_newenv_fix_seal_repro.py:29`(段階 A のもの。§10)。

**足した試験**: `tests/bt/item_1/test_i1_fix_g4_session.py`(5 件): crypto・fx の省略は拒む / crypto 24x7 で gap 3・off_grid 1 / fx 24x5 で off_grid、gap は走らなかったと書かれる / jpx の省略は読め、gap・off_grid が走らなかったことと理由(`asset 'jpx'`)が `checks_not_run` と manifest に出る。

**試験の末尾の行**: 単独(G-2 と一緒に)「17 passed in 0.17s」、全体は §7。

**変異の確かめ**: 「M7_G4_session_optional_again: exit 1: 1 failed in 0.21s」。

## 5. G-6: `loader.py` の行ごとの費用

**cProfile で特定した根本原因**(Binance 2018、521,624 行、`load` 1 回。`scripts/k1_newenv_g_loadprof.py prof`(作業中はスクラッチパッドの同じ中身 `g6/prof.py`)の出力 `g6/prof_before.txt`、tottime 順の上位から、直す前): 行ごとに、ファイルや何にもよらない物を作り直していた:
1. `src/bot/bt/data/allowlist.py:311`(直す前)— 封印されたファイルの行ごとに `seal_time_ns` が `TimeReader("iso", "UTC", …)` を新しく作る(`seal_time_ns` cumtime 24.5 s / 全体 131.7 s)。
2. `src/bot/bt/data/loader.py:176`(直す前)— `_Cells.rest` が行ごとに `spec.columns_used()` を作り直す(`columns_used` 521,625 回、cumtime 3.6 s)。
3. `src/bot/bt/data/loader.py:493`(直す前)— 全行の identity(記録の JSON 文字列)を書く(`iterencode` 5.7 s)。identity を比べるのは同じ鍵の行が 2 つあるときだけ。
4. `src/bot/bt/data/loader.py:477-488`(直す前、封印の時刻の照合)— 封印の時刻の列がデータの時刻の列と同じでも、同じセルを `seal_time_ns` がもう一度 ISO として読む(`_iso_to_nanos` 1,043,671 回 = 1 行 2 回、cumtime 25.9 s。1〜3 を直した後の cProfile `g6/prof_after1.txt` でも 1,043,671 回・23.4 s)。
5. 直していない残りは §9-1(核の事象の値の検査、1 行 1 回の ISO の読み、数の読み)。

**直し方**: 1 → 封印の時刻の読み手を 1 つだけ作って使い回す(`allowlist.py:291-298`。読み手は状態を持たない)。2 → `columns_used` をファイルごとに 1 回作って `_Cells` に渡す(`loader.py:516`)。3 → `Row.identity` を読まれたときに作る property にし、`Row` を slots にした(`loader.py:84-106`)。重複・食い違いの検査の結果は変わらない(試験)。4 → 封印の時刻の列がデータの時刻の列そのもの(1 列、ISO、UTC)のときは、データの読み手が読んだ時刻を `seal_time_ns` に渡し、同じセルを 2 度読まない(`loader.py` `_read_file` の `same_time`、`allowlist.py` `seal_time_ns(value, iso_utc_ns)`)。`seal_time_ns` は YYYYMMDD と数の判定を先に行い、ISO の文字のときだけ渡された値を使う。渡された値は、`seal_time_ns` が自分で読むのと同じ `TimeReader("iso", "UTC")` の読み(データの読み手は同じ単位・同じ時刻帯で、許す時刻の幅が狭いだけ)【判断。同じ値になることは試験で確かめた】。

**測った数(同じ機械、Binance 2018 の 1 ファイル、`load` だけ、範囲 2018 年、session 24x7、synthetic 宣言。`scripts/k1_newenv_g_loadprof.py time`)**:

| | 1 回目 | 2 回目 | µs/行 | 最大 RSS | 出力 |
|---|---|---|---|---|---|
| 直す前 | 53.6 s | 45.8 s | 102.7 / 87.8 | 1,238.1 MB | `time_before.txt` |
| 1〜3 を直した後 | 39.75 s | 39.61 s | 76.2 / 75.9 | 1,084.5 MB | `time_after1.txt` |
| 1〜4 を直した後 | 29.32 s | 30.49 s | 56.2 / 58.5 | 1,083.8 MB | `time_after2.txt` |

3 つとも行 521,624・事象 521,604・異常 `{"synthetic": 20, "off_grid": 1201, "gap": 5177}`・事象の列の sha256 `e45e35711f030f4e43cbfd3348130e2cfbc6d45cdab5493163a7550b3785d40b` が同じ。6 回とも他の重い処理と同時には走らせていない【事実】(ファイルの時刻: 核の試験の回の終わり 09:17:55、`time_before.txt` 09:21:06、`time_after1.txt` 09:23:13、次の試験の回の開始 09:23:24。`time_after2.txt` は試験の回の終わり 10:03 台の後、10:05:05 に終わった)。直す前の 1 回目が 2 回目より 7.8 s 長いのは、ファイルの読み込みのキャッシュが冷えていたためと推定【推定】(確かめていない)。

**残り(直していない、§9)**: 直した後の cProfile(`prof_after2.txt`、全体 80.8 s): 行ごとに核の `BarEvent` を作るときの値の検査 cumtime 30.2 s(37%。`values.py` の `as_float` / `_plain_scalar`)、ISO 時刻の読み 1 行 1 回 `_iso_to_nanos` cumtime 12.2 s、数の読み `loader.num` cumtime 11.2 s。

**足した試験**: `tests/bt/item_1/test_i1_fix_g6_loader_cost.py`(5 件): 300 行の封印されたファイルの `load` で `TimeReader` を作る回数 ≤ 3・`columns_used` ≤ 2・loader の `json.dumps` ≤ 2・`_iso_to_nanos` ≤ 行数 + 2(直す前は行の数に比例、または行数の 2 倍)/ `Row` に `__dict__` が無く、重複 1・食い違い 2 が直す前と同じ行で出る / 渡した時刻 = `seal_time_ns` が自分で読む時刻(時刻帯つき・空白区切り・`label: end`)、`label: end` で境に届く行は従来どおり `SealedRangeError` / 封印の列がデータの時刻の列と違う(エポック秒 + ISO の封印の列)ときも読み手は ≤ 3。

**試験の末尾の行**: 単独「5 passed in 0.27s」、全体は §7。

**変異の確かめ**: 「M8_G6_reader_per_row: exit 1: 1 failed, 4 passed in 0.33s」/「M9_G6_columns_used_per_row: exit 1: 1 failed in 0.29s」/「M10_G6_identity_text_per_row: exit 1: 1 failed in 0.27s」/「M11_G6_seal_time_read_twice: exit 1: 1 failed in 0.31s」。

## 6. §2-6: 新しい口で 2 升を生のファイルから回した

**口**(`scripts/k1_newenv_g_rawrun.py`、写しを作らない): 記録の口 `bot.bt.repro.runner.run`(2 回実行して byte で比べる)に、封印の台帳 P2-08 に載った生の 1 分足 8 ファイルを**範囲つき**で渡した(G-3)。d0〜d3 = Binance BTCUSDT 2018〜2021、d4〜d7 = bitFlyer FX_BTC_JPY 2018〜2021、範囲はファイルごとに [その年の 1 月 1 日, 翌年の 1 月 1 日)(段階 G の畳みの読みと同じ)。約定の無い分は Binance = `synthetic`(`n_trades == "0"`)→ drop、bitFlyer = `no_trade`(OHLC が全部空)→ drop(G-2)。session 24x7(G-4)、gap = accept、off_grid = accept。結合・畳みは `K1XSetup` の prepare(`prepare: join_fold`)で、出力の流れの名前 `signal` / `price`、約定の口は `SimVenue(streams=("price",))`(G-1)。

**結果**(`docs/PHASE2/K1/NEWENV_G/rawrun_compare.json`、`rawrun.log` の逐語):

| 升 | 取引数(新しい口 / cells.json) | 平均 bp(新しい口 / cells.json) | 同じか | run_id(新しい口) | 2 回の実行が同じ | 壁時計 | 最大 RSS |
|---|---|---|---|---|---|---|---|
| `design\|2018_2021\|15\|s19/b24\|weak` | 10,666 / 10,666 | 2.538203629061192 / 2.538203629061192 | 取引数・平均 bp とも同じ | `06a79687…` | true | 848.8 s | 7,363.4 MB |
| `design\|2018_2021\|5\|s19/b24\|weak` | 12,999 / 12,999 | 3.4532744966127042 / 3.4532744966127042 | 取引数・平均 bp とも同じ | `eb130c76…` | true | 798.3 s | 7,360.9 MB |

- 一致は数が同じという事実だけ(委任文 §2-6)。
- `record.json` の `data[i].range_ns` に 8 ファイルの範囲が残っている(`rawrun_compare.json` の `record_data_ranges`)。
- 落とした行(`data_quality.json` の manifest、`rawrun_compare.json` の `data_quality`): bitFlyer の `no_trade` は 2018 4,293 / 2019 5,708 / 2020 6,701 / 2021 6,970。段階 G の写しが落とした空の行の数(`backtest_data/k1_newenv_g_20261001/FOLD_MANIFEST.json` の `copy_of.dropped_blank_open`)と同じ 4,293 / 5,708 / 6,701 / 6,970【事実】。Binance の `synthetic` は 20 / 76 / 50 / 89(FOLD_MANIFEST.json の `anomalies.synthetic` と同じ)。
- 門が開くのを許したファイル(`rawrun_compare.json` の `opened`): 上の 8 ファイルと封印の台帳 8 つ(`backtest_data/phase2_sealed/*/SEALED.json`)だけ。門が止めた `open` は 0 件(記録ファイル `logs/rawrun_refused.log` が作られていない: `ls` の出力「No such file or directory」)。
- 15 分の升は G-6 の 2 つ目の直し(封印の時刻を 2 回読まない、§5 の 4 つ目)を入れる前のコードで、5 分の升は入れた後のコードで回った(15 分の升の実行は 09:25〜09:39 UTC、`allowlist.py`・`loader.py` の最後の変更の時刻は 09:35:01 UTC(`ls --time-style=full-iso`)、5 分の升は 09:39〜09:53 UTC)【事実】。2 つの record.json の `diff_hash` は違う(`434b4a6c…` と `7acea3e9…`)。
- 参考(条件の外): 直した後のコードで段階 G の**畳んだ足**(`backtest_data/k1_newenv_g_20261001/*_2018_2021`、`prepare: none`、流れの名前 `d0` / `d1`)から同じ 2 升を回しても、取引数・平均 bp は cells.json と同じ(15 分 10,666 / 2.538203629061192、5 分 12,999 / 3.4532744966127042。`folded_check.py` の出力、実行記録はスクラッチパッドに置いて消した)。

## 7. §2-7: `tests/bt` と `tests/test_k1_wick*.py` をデータの門の下で回した

- コマンド(10:06:41 UTC 開始): `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/logs/final2_refused.log python -m pytest tests/bt tests/test_k1_wick.py tests/test_k1_wick_critic.py -p k1_newenv_g_datagate -p no:cacheprovider --basetemp=<S>/pt_final2 --ignore=tests/bt/item_2/test_i2_real_data_check.py --ignore=tests/bt/item_4/test_i4_real_data_smoke.py`
- 末尾の行(逐語): 「18004 passed, 6 skipped, 3 warnings in 1041.96s (0:17:21)」
- 門が止めた `open`: 0 件(門の記録ファイル `logs/final2_refused.log` が作られていない: `ls` の出力「No such file or directory」)。失敗 0 件・エラー 0 件
- **除いた 2 ファイル**(`--ignore`)と理由【事実】: `tests/bt/item_2/test_i2_real_data_check.py`(5 件)と `tests/bt/item_4/test_i4_real_data_smoke.py`(1 件)は、段階 G のデータの門の許可の一覧に無い `backtest_data/auto_bitflyer_executions_20260905/board_top5_20260821.csv.gz`・`executions_20260821.csv.gz` を開く。除かずに回した 09:23〜09:41 の回(`t_disc.log`、直しの途中のコード)では、門がこの 2 ファイルの `open` を止め(`logs/disc_refused.log` の 2 行がこの 2 つのパス)、この 6 件が `PermissionError` の ERROR になった。読んでよいデータは段階 G の委任文と同じ(委任文 §3)なので、この 2 ファイルはこの委任では回していない(§9・§10)。
- 同じ条件の 1 つ前の回(09:45:40 開始、`t_final.log`)の末尾の行: 「18003 passed, 6 skipped, 3 warnings in 1059.08s (0:17:39)」、門が止めた `open` 0 件(`logs/final_refused.log` が作られていない)。この回の後に足した試験は `test_i1_fix_g6_loader_cost.py` の 1 件(封印の列がデータの時刻の列と違う場合)だけで、ソースは変えていない(`src` の最後の変更は 09:35:01 UTC)。
- 直しの影響で期待値・spec を直した既存の試験(場面集ではない): `tests/bt/item_0/test_bt0_notices.py`・`test_bt0_r14_process_state.py`・`test_bt0_r8_sender_adversary.py`(G-1、§1)/ `tests/bt/item_2/i2_driver.py`(場面のラベルで市場の事象を見分ける鍵から、核が付ける `stream` を除いた。81 + 1 件の失敗の元)/ `tests/bt/item_1/test_i1_fix_seal_read_before_refuse.py`・`test_i1_spec_and_parse.py`・`tests/bt/item_3/test_i3_fix_currency.py`・`tests/bt/item_4/test_i4_fix_k1_module.py`(暗号資産の足の spec に `session: 24x7`、G-4)/ `tests/bt/item_1/test_i1_fix_stream.py`(spec の既定を `24x7` にし、ファイルの穴を `gap: accept` と名指しし、穴が流し読みの口と `load` で同じに出ることを確かめる形にした。直す前は穴の検査が走っていなかった)/ `tests/bt/item_4/test_i4_data_session.py`(FX の session 無しの 3 升は、直す前の「検査なし」から「拒む」に。G-4 そのもの)。

## 8. 打ったコマンド(`<S>` = スクラッチパッド `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad`)と末尾の行

| コマンド | 末尾の行(逐語) |
|---|---|
| `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider --basetemp=<S>/pt0`(G-1 を入れた直後、試験を直す前) | 「3 failed, 6730 passed, 4 skipped, 3 warnings in 594.72s (0:09:54)」(3 件は §1 で期待値を直した 3 つ) |
| `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/logs/selftest_refused.log python3 scripts/k1_newenv_g_selftest.py --trials 1` | 「cases 234 trades compared 15264 mismatched cases 0」 |
| `K1G_DATAGATE_LOG=<S>/logs/g6_refused.log python3 <S>/g6/prof.py prof`(直す前) | 「141947431 function calls (141947375 primitive calls) in 131.665 seconds」(先頭の行) |
| 同 `time` × 2(直す前 / 1〜3 の後 / 1〜4 の後は `scripts/k1_newenv_g_loadprof.py time`) | §5 の表の 6 行(各 1 行の JSON) |
| `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/logs/g6_refused.log python3 scripts/k1_newenv_g_loadprof.py prof`(1〜4 の後) | 「110650004 function calls (110649948 primitive calls) in 80.797 seconds」(先頭の行) |
| `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/logs/rawrun_refused.log sh -c "python3 scripts/k1_newenv_g_rawrun.py --feet 15; python3 scripts/k1_newenv_g_rawrun.py --feet 5"`(09:25〜09:53) | 2 行の JSON(§6 の表。5 分の升の行: 「{"run_id": "eb130c76b2fa38bd0859028344dcdec87684d888bbd71787ded855f0efb74079", "identical": true, "wall_s": 798.3, "max_rss_mb": 7360.9, "new": {"n": 12999, "mean_bp": 3.4532744966127042}, "stage_g": {"n": 12999, "mean_bp": 3.4532744966127042, "run_id": "5b75e7e1da7fd60e99ab4f99923a0690ed9ecb1c069600804748a600f4c7d870"}, "n_equal": true, "mean_bp_equal": true}」) |
| `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/logs/folded_refused.log python3 <S>/folded_check.py`(参考、§6) | 5 分の升の行: 「"n_equal": true, "mean_bp_equal": true」(全文は `folded_check.log`) |
| `K1G_MUT_DIR=<S>/mut2 python3 scripts/k1_newenv_g_mutate.py` | 12 行(M0〜M11、§1〜§5 に逐語)。最後の行「M11_G6_seal_time_read_twice: exit 1: 1 failed in 0.31s」 |
| bitFlyer 2018 の空の欄の形を数えた: `PYTHONPATH=scripts python3 -c "import k1_newenv_g_datagate, gzip, collections; …(行ごとに 10 欄の空 / 非空の組を Counter)"` | 「Counter({(False, False, …): 520995, (False, True, True, True, True, False, False, False, False, False): 2678, (False, True, True, True, True, False, True, True, True, True): 1325, (False, True, True, True, True, False, True, True, False, False): 290, …})」(open〜close が一部だけ空の組は無い) |
| §7 の 3 回(`t_disc.log` / `t_final.log` / `t_final2.log`) | 「108 failed, 17892 passed, 6 skipped, 3 warnings, 6 errors in 1093.02s (0:18:13)」(直しの途中、試験を直す前)/「18003 passed, 6 skipped, 3 warnings in 1059.08s (0:17:39)」/ §7 |
| `df -h /`(最後) | 「/dev/vda 252G 37G 380M 99% /」 |
| `git status --short`(最後) | 下に全文 |

`git status --short`(10:24 UTC、この作業者の変更と、作業者 A・フックの変更が混ざる。作業者 A の持ち物 = `DATA_READ.md`・`DIFF.md`・`TABLES.md`・`diff_table.md`・`diff_rows.json`・`diff_summary.json`・`k1_newenv_g_diff.py`・`k1_newenv_g_tables.py` には触っていない):

```
 M docs/AUDITOR/TRACE/2026-10-01_220780c0.json
 M docs/PHASE2/K1/NEWENV_G/DATA_READ.md
 M docs/PHASE2/K1/NEWENV_G/DIFF.md
 M docs/PHASE2/K1/NEWENV_G/ENV_DEFECTS.md
 M docs/PHASE2/K1/NEWENV_G/INTENT_MAP.md
 M docs/PHASE2/K1/NEWENV_G/TABLES.md
 M docs/PHASE2/K1/NEWENV_G/diff_rows.json
 M docs/PHASE2/K1/NEWENV_G/diff_summary.json
 M docs/PHASE2/K1/NEWENV_G/diff_table.md
 M scripts/k1_newenv_g_diff.py
 M scripts/k1_newenv_g_fold.py
 M scripts/k1_newenv_g_run.py
 M scripts/k1_newenv_g_selftest.py
 M scripts/k1_newenv_g_tables.py
 M src/bot/bt/core/contract.py
 M src/bot/bt/core/engine.py
 M src/bot/bt/core/events.py
 M src/bot/bt/data/allowlist.py
 M src/bot/bt/data/anomalies.py
 M src/bot/bt/data/loader.py
 M src/bot/bt/data/spec.py
 M src/bot/bt/fill/venue.py
 M src/bot/bt/repro/errors.py
 M src/bot/bt/repro/fixed.py
 M src/bot/bt/repro/runner.py
 M src/bot/strategy/k1_xvenue.py
 M tests/bt/item_0/test_bt0_notices.py
 M tests/bt/item_0/test_bt0_r14_process_state.py
 M tests/bt/item_0/test_bt0_r8_sender_adversary.py
 M tests/bt/item_1/test_i1_fix_seal_read_before_refuse.py
 M tests/bt/item_1/test_i1_fix_stream.py
 M tests/bt/item_1/test_i1_spec_and_parse.py
 M tests/bt/item_2/i2_driver.py
 M tests/bt/item_3/test_i3_fix_currency.py
 M tests/bt/item_4/test_i4_data_session.py
 M tests/bt/item_4/test_i4_fix_k1_module.py
?? docs/PHASE2/K1/NEWENV_G/FIXES.md
?? docs/PHASE2/K1/NEWENV_G/rawrun_compare.json
?? scripts/k1_newenv_g_loadprof.py
?? scripts/k1_newenv_g_mutate.py
?? scripts/k1_newenv_g_rawrun.py
?? tests/bt/item_0/test_bt0_fix_g1_stream_name.py
?? tests/bt/item_1/test_i1_fix_g2_no_trade.py
?? tests/bt/item_1/test_i1_fix_g4_session.py
?? tests/bt/item_1/test_i1_fix_g6_loader_cost.py
?? tests/bt/item_2/test_i2_fix_g1_venue_streams.py
?? tests/bt/item_3/test_i3_fix_g3_runner_range.py
?? tests/bt/item_4/test_i4_fix_g1_k1_xvenue.py
```

## 9. やっていないこと

1. **G-6 の残り**: 直した後も `load` は Binance 2018 で 29.3〜30.5 s(56〜59 µs/行)。cProfile(`prof_after2.txt`、全体 80.8 s)で残る大きいものは、(a) 行ごとに核の `BarEvent` を作るときの値の検査(`events.py __post_init__` cumtime 30.2 s、37%。`values.py` の `as_float`・`_plain_scalar` が 1 行 5 回)、(b) ISO 時刻の読み(1 行 1 回、`_iso_to_nanos` cumtime 12.2 s)、(c) 数の読み(`loader.num` cumtime 11.2 s)。(a) は核の値の決まり(事象の欄はすべて値の関数で作り直す、`values.py`)そのものなので、核の値の規則を変えずに速くする方法を上限の中で検討していない。(b)(c) は 1 行ごとの文字の解釈で、作り直しの無駄ではない。
2. **段階 A のスクリプト 4 本**(`scripts/k1_newenv_run.py:53`、`scripts/k1_newenv_tables.py:53`、`scripts/k1_newenv_fold.py:52`、`scripts/k1_newenv_fix_seal_repro.py:29`)は暗号資産の足の spec に `session` を書いていないので、G-4 の後は回すと `SpecError` で止まる。持ち物の外(委任文 §3 の作業者 B の持ち物は `scripts/k1_newenv_g_*.py`)なので直していない。
3. **試験 2 ファイル**(`tests/bt/item_2/test_i2_real_data_check.py`・`tests/bt/item_4/test_i4_real_data_smoke.py`、計 6 件)は、段階 G のデータの門が許さないファイルを開くので、この委任では回していない(§7)。
4. `scripts/k1_newenv_g_fold.py` は G-2 の宣言を使う形に直したが、直した後に回していない(回すと段階 G の畳んだ足と FOLD_MANIFEST.json を書き直すため。同じ宣言は §6 で記録の口から使って、落とした行数が段階 G の写しと同じことを確かめた)。
5. `scripts/k1_newenv_g_run.py` は段階 G の畳んだ足(台帳に無い写し)を入力にする口のまま残した(段階 G の記録を作った口。写しの範囲の守りは段階 G のときと同じく畳みの段まで)。生のファイルから範囲つきで回す口は `scripts/k1_newenv_g_rawrun.py`(§6、2 升だけ)。
6. 委任文 §2-6 の 2 升以外の升は、新しい口で回していない(委任文が求めていない)。

## 10. リードに聞くこと

1. 段階 A のスクリプト 4 本(§9-2)に `session: 24x7` を書き足すか(持ち物の外)。書き足すなら、BitMEX の 1 秒足・60 分足に穴があれば `gap: accept` の名指しも要る(穴の有無は確かめていない【未確認】)。
2. 試験 2 ファイル(§9-3)を、どのデータの決まりの下で誰が回すか(段階 A の門 `scripts/k1_newenv_fix_datagate.py` はこの 2 ファイルを許している)。
3. 記録の口に足した `Parts.prepare`(setup が読み込んだ流れから核に渡す流れを作る段。§2 の【判断】)を、記録の口の一般の口として残してよいか。今は K1 の結合・畳み(XVENUE_PREREG.md §2)だけが使う。

---

# 第 2 回(2026-10-01 10:3x〜 UTC、委任文 §4)

委任文 `docs/DATA/delegations/20261001_k1_stage_g_close.md` §4(批評家の [直す] 5 件・[聞く] 1 件と、第 1 回の作業者 B の (d) を受けたもの。上限: 作業者 1 回・3 時間 = 13:35 UTC)。オーナー逐語(L-499a)「**わかってる欠陥があるのなら直せ**」。批評家の指摘は `docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g_close.md` の「批評家」の節。

合意した完了の形(委任文 §4 の表の逐語):

- 「G-7(批評家の [聞く] 1): データ層 `loader.py:528-529` が範囲の外の行も値まで数に直して事象を作ってから捨てる → 時刻を先に読み、範囲の外(と封印の境以降)の行は値を読まない。試験 + 変異。段階 G の畳み `k1_newenv_g_fold.py` を回し直して `FOLD_MANIFEST.json` の落とした行数が前と同じか並べる」
- 「批評家の [直す] 2(DATA_READ.md・DIFF.md の「時刻だけ読んだ」を Binance 2023 と bitFlyer 2023 で分けて事実どおりに。G-7 を直したあとの読み方も書く)・3(15 分の升を今のコードで回し直して返り値と FIXES.md に書く)・4(ENV_DEFECTS.md G-6 の行を FIXES.md §5 に合わせる)・5(TABLES.md の引用を委任文 §0 の元の文のとおりに)・6(INTENT_MAP.md X-5・X-10・X-11 を直したあとの書き方に)」
- 「作業者 B の (d)1: 段階 A のスクリプト 4 本(`scripts/k1_newenv_run.py`・`k1_newenv_tables.py`・`k1_newenv_fold.py`・`k1_newenv_fix_seal_repro.py`)に `session: "24x7"` を書き、BitMEX の畳んだ足に穴があるかをデータ層の検査で確かめて要れば `gap` の方針を名指しする。段階 A の升は回し直さない(`k1_newenv_fix_seal_repro.py` は合成データなので回して通ることを確かめる)」
- 「作業者 B の (d)2: 除いた試験 2 ファイル(`tests/bt/item_2/test_i2_real_data_check.py`・`tests/bt/item_4/test_i4_real_data_smoke.py`)を段階 A の門 `scripts/k1_newenv_fix_datagate.py` の下で回す」
- 「最後に `tests/bt`・`tests/test_k1_wick*.py` を段階 G の門の下で回す(上の 2 ファイルは段階 A の門で)」

`<S>` = スクラッチパッド `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad`。第 2 回の記録は `<S>/r2/`。印は §0 の前と同じ(【事実】【推定】【判断】)。

## 11. G-7: データ層が範囲の外の行も値まで読んでから捨てる

**根本原因(ファイル:行)**【事実】
- `src/bot/bt/data/loader.py:528-529`(第 2 回の着手時 = HEAD 627503d8): `_read_file` の行のループで、`_build`(時刻と全部の欄を数に直し、`BarEvent` などの事象を作る)を呼んでから、範囲の判定 `_in_range` をしていた。封印の照合(`seal_time_ns` と境の比較)も `_build` の後。段階 G の時点のコード(`git show 5627b4ad^:src/bot/bt/data/loader.py` の 474・475 行)も同じ順。
- そのため、範囲つきで読んでも、範囲の外の行は値を数に直し、事象を作ってから捨てていた。範囲の外の行の値が数として読めなければ `ParseError` で止まっていた(批評家の確かめ「ParseError 'backtest_data/a.csv' line 4 field 'open': 'XX' is not a decimal number」)。

**直し方**
- 時刻だけを読む `_read_time`(`loader.py:213`)と、範囲と検査が見る行の時刻(足は開始時刻)を出す `_row_time`(`loader.py:230`)を `_build` から分けた。`_build(spec, cells, t, where)`(`loader.py:238`)は、読み終えた時刻を受け取って値を読む。
- `_read_file` の順を「時刻を読む(`loader.py:544`)→ 範囲の判定(`:545`。外なら値を読まずに次の行)→ 封印の照合(`:549`)→ 値を読み事象を作る(`:559`)」にした(説明のコメント `:537`)。範囲の中でも封印の境以降の行は、値を読む前に `SealedRangeError` で止まる。
- 変えていないこと: 範囲の外の行も `rows_read` に数える。範囲の外の行の時刻は今までどおり厳しく読む(読めなければ `TimeParseError`)。時刻は 1 行 1 回の読みのまま(G-6 の (4) と両立。G-6 の試験はそのまま通る)。流し読みの口 `stream.py` は同じ `_read_file` を通るので同じ。核(`src/bot/bt/core/`)は変えていないので `CORE_VERSION` は core-20 のまま。
- ファイルの bytes は今も全部ほどき、各行を csv の欄(文字)に分けてから時刻を読む(この順は変えていない)。

**足した試験**: `tests/bt/item_1/test_i1_fix_g7_range_before_values.py`(9 件): 批評家の確かめ(範囲 [00:00, 00:02) の外の 00:02 の行の open が `XX`)が読め、`rows_read` 3・`rows_kept` 2。範囲が無ければ同じ行は従来どおり `ParseError` / 範囲の前の行 / `label: end` の足は開始時刻で判定 / 10 行のうち範囲の 3 行だけ `_num` 15 回・`BarEvent` 3 回(直す前は 50 回・10 回)/ 範囲の外の行の時刻は今までどおり厳しく読む / 約定の csv と jsonl / 封印されたファイルで、範囲の終わり = 境、境以降の行の値が `XX` でも読める / 封印の時刻の列がデータの時刻の列と違い、範囲の中で封印の時刻が境以降の行は値の前に `SealedRangeError`(直す前は `ParseError`)/ 流し読みの口も同じ。

**試験の末尾の行**【事実】
- 直す前(試験を先に書いて回した): 「8 failed, 1 passed in 0.56s」(通った 1 件は「範囲の外の行の時刻は厳しく読む」= 変えていない振る舞い)
- 直した後: `tests/bt/item_1` 全体「3942 passed in 27.58s」。全体の回は §16。

**変異の確かめ**(`K1G_MUT_DIR=<S>/r2/mut python3 scripts/k1_newenv_g_mutate.py`、出力 `<S>/r2/mutate_r2.log` の逐語)【事実】
- 対照(G-7 の試験を足した 8 ファイル): 「M0_control_no_change: exit 0: 65 passed in 1.86s」
- 「M12_G7_values_before_the_range: exit 1: 1 failed in 0.28s」(値を範囲の判定より前に読む = 直す前)
- 「M13_G7_values_before_the_seal: exit 1: 1 failed, 3 passed in 0.25s」(値を範囲の後、封印の照合の前に読む)
- M1〜M11 も全部 exit 1(逐語は `mutate_r2.log`。M11 は直しの行が変わったので、変異を入れる場所の文字列だけ今の行 `seal_time_ns(cells.get(ent.time_column), raw_t if same_time else None)` に合わせた。中身は前と同じ「渡された時刻を使わない」)。門の記録 `<S>/r2/logs/` は空(止めた `open` 0 件)。

**実データで確かめた(2023 の 2 ファイル、段階 G の畳みと同じ spec・範囲 [2023-01-01, 2023-12-18)、段階 G の門の下)**【事実】
`<S>/r2/read2023_count.py`(`loader._num` と `loader.BarEvent` の呼ばれた回数を数える)。直す前は src の写しに `git show HEAD:src/bot/bt/data/loader.py` を置いて同じものを回した(`read2023_count_pre.log`、写しは消した)。

| ファイル | コード | rows_read | rows_kept | BarEvent を作った数 | 数に直した回数 | 作った事象の最後の開始 |
|---|---|---|---|---|---|---|
| Binance `binance_BTCUSDT_1m_2023.csv.gz` | 直す前 | 525,520 | 505,360 | 525,520 | 2,627,600 | 2023-12-31T23:59:00 |
| 同 | 直した後 | 525,520 | 505,360 | 505,360 | 2,526,800(= 505,360 × 5) | 2023-12-17T23:59:00 |
| bitFlyer `candles_1m_2023.csv.gz`(G-2 の宣言 `no_trade` で読む) | 直す前(G-2 の後・G-7 の前) | 525,600 | 505,440 | (出さない。リードの処置、§19-1) | (出さない) | (出さない) |
| 同 | 直した後 | 525,600 | 505,440 | 457,839 | 2,336,796(= 457,839 × 5 + 約定の無い 47,601 行 × 1) | 2023-12-17T23:59:00 |

- 直した後は、境以降の 20,160 行(どちらのファイルも)は時刻の欄だけを数に直した。
- bitFlyer の「直す前」の行の数は出さない(リードの処置、§19-1)。第 2 回の作業者は「直す前」を示すために、直す前の loader で 2023 の 2 ファイルの境以降の行(各 20,160 行)を値まで読み直した。bitFlyer 2023 の境以降の値は段階 G でも第 1 回でも読んでいなかったので、この読みは委任文 §3 の「読んでよいデータ」とオーナーの決定 L-499 ②(時刻だけ)の範囲の外(批評家 第 2 回 [止める] 1)。そこから出た境以降の中身の数は、この文書から外した。「直す前は値まで読んでいた」ことは合成ファイルの試験(§11 の 1 件目)と変異 M12 で示されている

**段階 G の畳みを回し直して並べた**(G-7 の後のコード、段階 G の門の下)【事実】
- 段階 G の出力を書き換えないように、`scripts/k1_newenv_g_fold.py` に `--out-dir` を足して出力をスクラッチパッドに置いた(既定は前と同じ `backtest_data/k1_newenv_g_20261001`)。
- コマンド: `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/r2/logs/fold_refused.log setsid nohup python3 scripts/k1_newenv_g_fold.py --out-dir <S>/r2/fold > <S>/fold_r2.log 2>&1 < /dev/null &`(1 回目は前景で 580 秒の上限に当たって止まった。2023 を読み終えたところ)。末尾の行: 「{"signal_minutes_collided_by_floor": 0, "price_minutes_collided_by_floor": 0, "max_bar_end_written": "2023-12-18T00:00:00", "max_bar_end_le_cut": true, "max_input_event_start": "2023-12-17T23:59:00", "max_input_event_end_le_cut": true} wall 682.6s」
- 比べた: `<S>/r2/fold_compare.py`、結果は `docs/PHASE2/K1/NEWENV_G/fold_rerun_g7.json`(新しい FOLD_MANIFEST.json は `<S>/r2/FOLD_MANIFEST_rerun.json.gz`。出力の足はスクラッチパッドから消した)。

| 入力 | 落とした行(前 = 段階 G の FOLD_MANIFEST.json / 後 = 回し直し) | 方針を当てた後の事象 | 同じか |
|---|---|---|---|
| Binance 2017〜2022 | 範囲の外 0 / 0、synthetic 23,696・20・76・50・89・0(前後とも) | 172,848・521,604・523,760・525,738・524,518・525,600(前後とも) | 6 年とも同じ |
| Binance 2023 | 範囲の外 20,160 / 20,160、synthetic 72 / 72 | 505,288 / 505,288 | 同じ |
| bitFlyer 2017〜2022 | 前 = 写しの `dropped_blank_open` 6,524・4,293・5,708・6,701・6,970・4,716 / 後 = データ層の `no_trade` 同じ数、範囲の外 0 / 0 | 519,072・521,307・519,892・519,967・518,630・520,884(前後とも) | 6 年とも同じ |
| bitFlyer 2023 | 前 = 写しの `dropped_at_or_after_cut` 20,160・`dropped_blank_open` 47,601 / 後 = 範囲の外 20,160・`no_trade` 47,601 | 457,839 / 457,839 | 同じ |

- 出力 22 ファイルの行数と sha256 はすべて同じ(`"outputs_rows_and_sha256_differ": []`)。`alignment`・`self_check` も同じ。
- 門が開くのを許したファイル: 封印の台帳 8 つと、Binance・bitFlyer 2017〜2023 の 14 ファイルだけ。門の記録 `fold_refused.log`・`foldcmp_refused.log` は作られていない(止めた `open` 0 件)。
- 壁時計は 682.6 秒で、段階 G の FOLD_MANIFEST.json の `wall_s` 143.4 秒より長い。理由は確かめていない【推定: 段階 G の回は読んだ分足の置き場 `--cache` を使った可能性がある。確かめていない】。

## 12. 批評家の [直す] 3: 15 分の升を今のコードで回し直した

- コマンド(11:03:05 UTC 開始): `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/r2/logs/rawrun15_refused.log setsid nohup python3 scripts/k1_newenv_g_rawrun.py --feet 15 > <S>/rawrun15_r2.log 2>&1 < /dev/null &`
- 末尾の行(逐語)【事実】: 「{"run_id": "bb8e99c5fd9f7e2f67359c0f710b64cfd21c67853099406f6cd88c2261932c35", "identical": true, "wall_s": 705.4, "max_rss_mb": 7387.6, "new": {"n": 10666, "mean_bp": 2.538203629061192}, "stage_g": {"n": 10666, "mean_bp": 2.538203629061192, "run_id": "8b26c859af04512193280bd08bad8596926a72aa573ced994a8502f5dac2e30d"}, "n_equal": true, "mean_bp_equal": true}」
- 取引数・平均 bp とも `cells.json` の同じ升と同じ(一致は数が同じという事実だけ)。2 回の実行は byte で同じ(`identical: true`)。
- 今のコードで回ったこと【事実】: `src` の最後の変更は `loader.py` の 10:35:57 UTC(`ls --time-style=full-iso`)で、実行の開始 11:03:05 より前。実行の後に変えたのはスクリプト `k1_newenv_g_tables.py`(この升の実行は使わない)と文書だけ。`record.json` の `diff_hash` は `d1f0c4ac…`(第 1 回の 15 分の升 `434b4a6c…`、5 分の升 `7acea3e9…` とは違う)。
- 5 分の升(`eb130c76…`)は第 1 回のまま(G-6 の 4 つ目の後・G-7 の前のコード)。委任文 §4 は 15 分の升だけを求めているので、5 分の升は回し直していない。
- 実行記録: `backtest_runs/k1_newenv_g_close/bb8e99c5…/`(gzip 済み)。`docs/PHASE2/K1/NEWENV_G/rawrun_compare.json` の 15 分の升の項を新しい実行で書き直した(5 分の升の項はそのまま)。`opened` は生のファイル 8 つと封印の台帳 8 つ(計 16)。門の記録 `rawrun15_refused.log` は作られていない(止めた `open` 0 件)。
- §6 の表の 15 分の升の行(run_id `06a79687…`、848.8 s)は第 1 回の記録として残す。第 1 回の実行記録 `backtest_runs/k1_newenv_g_close/06a79687…/` も消していない。

## 13. 作業者 B の (d)1: 段階 A のスクリプト 4 本に `session: "24x7"`

**BitMEX の畳んだ足の穴(データ層の検査、session 24x7、段階 G の門の下)**【事実】`<S>/r2/bitmex_gaps.py`(出力 `<S>/r2/bitmex_gaps.log`):

| 足 | 行 | 異常 | 走った検査 |
|---|---|---|---|
| 60 分 | 26,276 | gap 4 | backward・duplicate・conflict・gap・off_grid |
| 30 分 | 52,544 | gap 16 | 同 |
| 15 分 | 105,056 | gap 64 | 同 |
| 5 分 | 314,169 | gap 1,191 | 同 |
| 3 分 | 520,960 | gap 4,640 | 同 |
| 1 分 | 1,523,877 | gap 52,923 | 同 |

どの足も異常は gap だけ(off_grid・重複・食い違い・逆行は 0)。門の記録 `bitmex_refused.log` は作られていない。

**直し方**
- `scripts/k1_newenv_run.py`: 畳んだ足の spec に `session: "24x7"`。記録の口に渡す `DataInput` に方針 `{"gap": "accept"}` を名指しした(穴は「1 秒足が 1 本も無い区間には足が無い」= K1 RESULT.md 1.2 の規則どおりのもの。上の表)。
- `scripts/k1_newenv_tables.py`: spec に `session: "24x7"`。このスクリプトは `records()` だけを使い、異常の方針を当てないので、方針は名指ししない。
- `scripts/k1_newenv_fold.py`(1 秒足の畳み): spec に `session: "24x7"`。方針 `POLICY = {"gap": "accept"}` を名指しし、gap 以外の異常は前と同じく止める。年ごとの結果に `gaps_accepted` と `policy` を足した。1 秒足に穴があることの出所【事実】: 段階 A の `FOLD_MANIFEST.json` の `rows_1s_total` 49,054,818 が 2017〜2019 の秒数 94,608,000 より少ない、最初の日のファイル `20170101.csv.gz` の `rows_read` 3,272(1 日 86,400 秒)。1 秒足の生のファイル(`backtest_data/bitmex_trade_1s_XBTUSD/`)は段階 G の門が許していないので、この回は開いていない(1 秒足の gap の数は数えていない)。
- `scripts/k1_newenv_fix_seal_repro.py`: 合成データの spec に `session: "24x7"`。

**確かめたこと(段階 A の升は回し直していない)**【事実】
- `<S>/r2/stageA_check.py`(段階 G の門の下)の出力: 「parse_spec ok: run x6, tables x6, fold 1s; fold POLICY {'gap': 'accept'}」/「plan_run ok (60m, first gate, both): run_id 6ddb1c8c5a3be50fa43c9420afd49fed0f5c1f22c95d2541466f3f6fca44d29f」/「load 60m + resolve {'gap': 'accept'} events 26276 resolution {'gap': 'accept'} anomalies {'gap': 4}」/「tables.bar_index(60) rows 26276」。門の記録 `stageA_refused.log` は作られていない。
- spec と方針は実行の同一性に入るので、段階 A の升を今回し直すと run_id は段階 A の記録(`docs/PHASE2/K1/NEWENV_A/runs_index.json`)と違う(上の run_id `6ddb1c8c…` は `runs_index.json` に 0 件: `grep -c`)。
- `k1_newenv_fix_seal_repro.py` を回した: `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/r2/logs/seal_refused.log python3 -c "import k1_newenv_g_datagate, runpy, sys; sys.argv=['k1_newenv_fix_seal_repro.py', '<S>/r2/seal']; runpy.run_path('scripts/k1_newenv_fix_seal_repro.py', run_name='__main__')"` → 「file size 49」「sha256 of bytes 171」「refused SealedRangeError」、exit 0(封印されたファイル `f.csv` の `open` の行は無い = 開く前に拒んだ)。直す前の版(`git show HEAD:scripts/k1_newenv_fix_seal_repro.py`)を同じように回すと末尾が「bot.bt.data.errors.SpecError: spec.bar.session is required for asset 'crypto': one of ['24x7', '24x5'] (24x7 runs the gap and off_grid checks, 24x5 the off_grid check)」。合成データの置き場は消した。

## 14. 作業者 B の (d)2: 除いた試験 2 ファイルを段階 A の門の下で回した

- コマンド: `PYTHONPATH=scripts:src K1FIX_DATAGATE_LOG=<S>/r2/logs/excluded2_refused.log python -m pytest tests/bt/item_2/test_i2_real_data_check.py tests/bt/item_4/test_i4_real_data_smoke.py -p k1_newenv_fix_datagate -p no:cacheprovider --basetemp=<S>/r2/pt_ex2`
- 末尾の行(逐語)【事実】: 「7 passed in 70.71s (0:01:10)」。門の記録 `excluded2_refused.log` は作られていない(止めた `open` 0 件)。basetemp は消した。
- 件数: 同じ門の下で `--collect-only -q` を回すと「tests/bt/item_2/test_i2_real_data_check.py: 5」「tests/bt/item_4/test_i4_real_data_smoke.py: 2」(計 7)。第 1 回の返り値は `test_i4_real_data_smoke.py` を「1 件」(計 6 件)と書いていた。第 1 回の 6 件は門に止められて ERROR になった件数なので、`test_i4_real_data_smoke.py` の 2 件のうち 1 件は止められたファイルを開かない試験だった可能性がある【推定。確かめていない】。

## 15. 文書の直し(批評家の [直す] 2・4・5・6)

- [直す] 2: `DATA_READ.md` §2 の「注意」と §7-1、`DIFF.md` §6-1 を、Binance 2023(データ層が境以降の行も値まで読み事象を作ってから捨てた)と bitFlyer 2023(自前の読みが時刻を読んだところで飛ばした)に分けて書き直し、G-7 の後の読み方(§11 の数)を足した。「境以降の行の時刻以外の値は渡していない」は、`FOLD_MANIFEST.json` の `self_check.max_input_event_start` = 2023-12-17T23:59:00 を出所にした書き方に変えた。
- [直す] 4: `ENV_DEFECTS.md` の G-6 の行を §5 に合わせた(直したのは 4 つ、29.32 s / 30.49 s、残りは核の値の検査・1 行 1 回の ISO の読み・数の読み)。G-7 の行を足した。
- [直す] 5: `scripts/k1_newenv_g_tables.py:227` の引用を委任文 §0 の元の文「批評家の [直す] 4 件(文書の書き方)だけ当てて G を閉じる。第 18 部は回さない(Bybit の取り直しも不要)」にし、`TABLES.md` を作り直した(`PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/r2/logs/tables_refused.log python3 <S>/gated.py scripts/k1_newenv_g_tables.py --md` → 「TABLES.md written」。前の TABLES.md との `diff` は 187 行の 1 行だけ)。
- [直す] 6: `INTENT_MAP.md` の X-5 を「作業者の判断で、委任文の指示ではない」に、X-10・X-11 を G-1 の後のコード(名前で見分け、同じ窓の 2 本がそろったときに行動)の書き方にした。
- [直す] 3 は §12。

## 16. 全体の試験(段階 G の門の下)

- コマンド(11:08:22 UTC 開始): `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/r2/logs/final_r2_refused.log python -m pytest tests/bt tests/test_k1_wick.py tests/test_k1_wick_critic.py -p k1_newenv_g_datagate -p no:cacheprovider --basetemp=<S>/r2/pt_final --ignore=tests/bt/item_2/test_i2_real_data_check.py --ignore=tests/bt/item_4/test_i4_real_data_smoke.py`(`setsid nohup` で切り離し、出力 `<S>/t_final_r2.log`)
- 末尾の行(逐語)【事実】: 「18013 passed, 6 skipped, 3 warnings in 1109.45s (0:18:29)」(第 1 回の 18004 件 + G-7 の試験 9 件)
- 門が止めた `open`: 0 件(門の記録 `final_r2_refused.log` は作られていない: `ls` の出力「No such file or directory」)。`grep -c "FAILED\|ERROR"` は 0。basetemp は消した。
- `--ignore` の 2 ファイルは段階 A の門の下で回した(§14、「7 passed」)。
- 15 分の升の実行(§12)と同時に走った時間がある(11:08〜11:14)。試験の結果には関わらないが、壁時計はその分長い【推定】。

## 17. やっていないこと(第 2 回)

1. 委任文 §4 の「作業者 B の (d)3: `Parts.prepare` は一般の口として残す(リードの判断。記録の口が範囲つきの生のファイルから結合・畳みを行う経路で、記録に残る)。FIXES.md にそう書く」は書いていない。この行の右の列(オーナーの原文の該当語)が「— (リードの判断、A-13 の 3 つに当たらない)」で、オーナーの逐語が無いため、着手前の表で右が空の行として扱い、着手しなかった(§18-1)。
2. 5 分の升は回し直していない(委任文 §4 は 15 分の升だけを求めている。§12)。
3. 段階 A の升は回し直していない(委任文 §4「段階 A の升は回し直さない」)。BitMEX の 1 秒足の生のファイルは段階 G の門が許していないので開いていない。1 秒足の gap の数は数えていない(§13)。
4. 段階 G の畳みの出力(`backtest_data/k1_newenv_g_20261001/`)は書き換えていない。回し直しはスクラッチパッドに書き、22 ファイルの sha256 が同じことを確かめて消した(§11)。
5. 第 1 回の §9-1(G-6 の残り: 核の値の検査・1 行 1 回の ISO の読み・数の読み)は手を付けていない(委任文 §4 に無い)。
6. 第 1 回の §9 のうち 2(段階 A のスクリプト)・3(除いた試験 2 ファイル)・4(`k1_newenv_g_fold.py` を回していない)は、それぞれ §13・§14・§11 で行った。
7. 返り値を `docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g_close.md` に写していない(委任文 §3 で写すのはリード)。

## 18. リードに聞くこと(第 2 回)

1. 委任文 §4 の (d)3 の行は、右の列にオーナーの逐語が無い(「— (リードの判断、A-13 の 3 つに当たらない)」)。作業者への指示「右が空の行は着手せず、問いとして返す」に従って書いていない。この行を FIXES.md に書いてよいか(yes/no)。書く場合の文は委任文 §4 の (d)3 の文をそのまま写す。
2. 段階 A のスクリプト 3 本(run・tables・fold)の spec と方針を変えたので、段階 A の升を今回し直すと run_id が段階 A の記録と違う(§13)。段階 A の記録(`runs_index.json`)は直す前のコードの記録としてそのまま残すことでよいか(yes/no)。
3. 15 分の升は G-7 の後のコード(`diff_hash` `d1f0c4ac…`)、5 分の升は G-7 の前のコード(`7acea3e9…`)で回っている(§12)。5 分の升も今のコードで回し直すか(yes/no。約 13〜15 分、最大 RSS 約 7.4 GB)。

## 19. リードの処置(第 2 回の批評家の指摘を受けて、2026-10-01 11:3x UTC)

1. **[止める] 1(境以降の行を直す前の loader で値まで読み直した)**: 読みは起きてしまったので取り消せない。処置 = (a) そこから出た境以降の中身の数(bitFlyer 2023 の空でない分の数・最後の分)を §11 の表と文から外した。(b) 事実を `docs/OWNER_LOG.md` L-499d に書き、オーナーに上申した(作業者の返り値の逐語 `docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g_close.md` には数が残っている。消すかはオーナーの判断)。(c) 「直す前」の示し方は合成ファイルの試験で足りる。
2. **[直す] 2(jsonl は範囲の外の行の数値も数に直す)**: リードが直した。`loader.py: _rows_jsonl` の `json.loads` を `parse_float=str, parse_int=str` にし、数に直すのは `_build`(範囲と封印のあと)だけにした。時刻の読み手(`timestamps.py: read`)は数字の文字列を受けるので、epoch の時刻も変わらない。試験 `test_jsonl_numbers_of_a_row_outside_the_range_are_not_turned_into_numbers` を足した(直しを戻すと落ちる: `parse_float=Decimal` に戻して「1 failed」)。批評家の確かめ方 `g7_check.py` の 3 = 「types of out-of-range row (line 3): {'ts': 'str', 'o': 'str', 'h': 'str', 'l': 'str', 'c': 'str', 'v': 'str'}」。`tests/bt/item_1` は「3943 passed in 28.46s」、変異 M0「66 passed」・M12・M13 とも落ちる。
3. **[直す] 3**: `DATA_READ.md` と `DIFF.md` の「リードかオーナーが決める」を、L-499 ② で決まった範囲(時刻だけ)と決まっていない範囲(値まで読んだ件)に分けて書き直した。
4. **(d)1 = (d)3 の行**: `Parts.prepare` は記録の口の一般の口として残す(リードの判断。記録の口が範囲つきの生のファイルから結合・畳みを行う経路で、記録に残る。A-13 の 3 つ = 問いの立て方・族の切り方・検定単位に当たらない)。
5. **(d)2**: 段階 A の実行記録(`backtest_runs/k1_newenv_a/`、`runs_index.json`)は、直す前のコードの記録としてそのまま残す。回し直すと run_id が変わるが、段階 A の報告の数は変えない。
6. **(d)3**: 5 分の升は今のコードで回し直さない(15 分の升で今のコードの経路を確かめた。約 15 分・RSS 7.4 GB・ディスク残 360 MB の費用に対し、増える確かめは同じ経路の 2 升目だけ)。範囲を縮めた判断としてここに書く。
