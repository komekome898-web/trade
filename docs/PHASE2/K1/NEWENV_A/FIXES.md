# K1 段階 A — 環境の欠陥の直し(D-1〜D-4)

委任文 `docs/DATA/delegations/20260927_k1_env_fixes.md`。オーナー逐語(L-476)「**研究の最初の単位を回して、そこで出る欠陥を直す**」、(L-482)「**進めて**」。

合意した完了の形(委任文 §2 の逐語、抜粋):

- 「5 件それぞれについて `docs/PHASE2/K1/NEWENV_A/FIXES.md` に: 根本原因(ファイル:行)・直し方・足した試験・試験の末尾の行。直しは根本で行う(場当たりの回避を残さない)。核(`src/bot/bt/core/`)を変えたら `CORE_VERSION` を上げる。場面集(`tests/bt/**/scenes*`)と規則の文は変えない。」
- 「D-1 の確かめ: 60 分足 39 升を `bot.bt.pipeline` の口で回し、費用 0・遅延 0 の設定で、段階 A の実行記録(`backtest_runs/k1_newenv_a/`)と取引数・平均・約定の列が同じか。違えば升ごとに原因を書く(一致は数が同じという事実だけ)。」
- 「D-2 の確かめ: 1 秒バー 2017〜2019 を流し読みの口 1 回で 60 分足に畳み、`backtest_data/k1_newenv_a_20260927/` の 60 分足と byte で比べる。時間と最大 RSS を測る。」
- 「D-3 の確かめ: 60 分足 39 升の平均の 95% 区間を日ブロックで出し、`*` を段階 A の表の `*` と並べる(比べるだけで、どちらかを正解にしない)。」
- 「D-4: 試験で確かめる(XBTUSD の記録で画面に「円」が出ない)」
- 「上限(4 時間)で残ったものは「やっていないこと」として `FIXES.md` に逐語で書いて返る。」

**委任の変更(L-483、08:1x UTC)**: k1a-c-02(実行の段で BitMEX 2020〜2021 を拒む)はこの委任から外れた(オーナー逐語「**封印期間の拒否とか言ってますが、バックテスト環境の問題ではなくデータを与える側の問題ではないのですか？**」)。作業者はそれまでに入れていた k1a-c-02 のための変更(`allowlist.py` の `whole_file`・`match_path`・`check_range` の追加と docstring、`loader.py` の「開く前に封印をパスで照合する」部分)を戻した。`allowlist.py` はリードのチェックポイント `bf44529a` の一つ前(`bf44529a~1`)の中身に戻した(`git diff bf44529a~1 --stat -- src/bot/bt/data/allowlist.py` の出力は空)。封印の台帳に K1 の記録は足していない。k1a-c-02 のための試験は書く前だった。したがって「5 件」は 4 件(D-1〜D-4)になった。

## 0. 守ったこと(データ・メモリ・ディスク)と、その確かめ

- **読んだデータ**: BitMEX 1 秒バー 2017-01-01〜2019-12-31 と段階 A の畳んだ足(`backtest_data/k1_newenv_a_20260927/`)だけ。これを機械で守るため、作業者の実行と試験はすべて Python の監査フック `scripts/k1_newenv_fix_datagate.py`(作業中はスクラッチパッドの同じ中身 `k1fix_datagate.py`)の下で回した。データの置き場(`backtest_data` / `data` / `paper_logs`)のうち、上の 2 つと封印の台帳(`backtest_data/phase2_sealed/`、データではない)以外のファイルを `open` しようとすると、開く前に `PermissionError` で止め、そのパスを記録する。
  - 作業者の実行(流し読みの畳み、統合の口の 39 升、runner の 2 升、新しい試験・変異の試験)で止めた `open` は 0 件(記録ファイルが一度も作られなかった: `pipe_refused` / `fold_refused` / `runner1_refused` / `new_refused` / `k1_refused` / `fix_refused` / `mut_refused` すべて「no file」)。
  - 試験の全体(§6)では止めた `open` が 17,622 件(`after_refused.log` の行数)。止めたものは読まれていない。内訳と意味は §6・§8。
- **メモリ**: 1 分足は回していない。同時に走らせた重いプロセスは最大 3 本(流し読みの畳み 1 + 統合の口 1 + 試験 1)。統合の口は 1 升ずつ(`--workers 1`)。
- **ディスク**: 新しい実行記録は `backtest_runs/k1_env_fixes/`(`.gitignore` = `*`)に分け、升ごとに fills / orders / trades / metrics を gzip(`du -sh backtest_runs/k1_env_fixes` → 30M、流し読みの畳みの出力を除く)。`backtest_runs/k1_newenv_a/` には書いていない。試験の basetemp と変異の試験用の写しは消した。
- **1 つの出力先に 1 つの実行(E-12)**: `scripts/k1_newenv_fix_pipeline.py` は出力先に `.running` を `O_EXCL` で作り、あれば止まる。升の一覧は親だけが最後に 1 回書く。
- 核(`src/bot/bt/core/`)は 1 行も変えていない(`git diff bf44529a~1 --stat -- src/bot/bt/core` の出力は空)→ `CORE_VERSION` は据え置き。場面集(`tests/bt/battery/`)と規則の文は変えていない。git commit / push はしていない。

## 1. D-1(E-3): 「その足の終値」で成行を約定する規則が統合の口に無い

**根本原因(ファイル:行、直す前 = `bf44529a~1`)**
- `src/bot/bt/orders/rules.py:45` — `market_ref` の値が `("last_trade", "next_bar_open")` だけで、「直前に届いた足の終値」を宣言できない。
- `src/bot/bt/fill/venue.py:554-567`(`_aggress_no_book`)— 板の無い成行の値は「最後の約定」か「次の足の始値」だけ。足の終値を覚えていない(`venue.py:283` で足は `_on_bar` に渡るだけ)。
- `src/bot/bt/pipeline.py:731`(門の規則 I-4)と `pipeline.py:801-808`(`ArrivalGate.on_order`)— 足の銘柄の成行は必ず保留され、次に**始まる**足で値が付く。
- `src/bot/bt/pipeline.py:140` — 戦略の種類が `schedule` / `seeded_random` / `price_rule` だけで、K1 のような戦略を統合の口に渡す口が無い。
- `src/bot/strategy/k1_wick.py:158`(`BarCloseMarketFill`)— 段階 A は約定の規則を戦略の側に書いていた(項目 2 の約定の模型を通っていない)。

**直し方**
- `rules.py:46`: `market_ref` に `"last_bar_close"` を足した(規則の文の docstring も)。
- `venue.py:192, 290, 566`: 会場が受けた足の終値を `last_bar_close` に覚え(その足自身の約定の処理のあと)、`market_ref = last_bar_close` の成行を「到着の時点で会場が最後に見た足の終値 ± 宣言の spread の半分」で全量 taker 約定。足がまだ無ければ Canceled `no_price_yet`(`last_trade` と同じ扱い)。
- `pipeline.py`: 門の規則 **I-6** を足した(`pipeline.py:784` の docstring、`pipeline.py:859` の分岐)— 足の銘柄で `market_ref = last_bar_close` の成行は保留せず、到着の時点で会場に渡す(口座が値の無さで先送りした証拠金の検査はその場でやり直す)。`last_bar_close` を足以外の銘柄に宣言すると計画の段で拒む(`pipeline.py:707`)。戦略の種類 `module` を足した(`{"kind": "module", "module": "bot.strategy.<名>", "factory", "params"}`: 工場関数が升・側・実行ごとに新しい `Strategy` を作る。`exit_reasons` を持たない戦略は拒む。モジュールの源の sha256 を実行の同一性に入れる。実データ + 動作確認では `price_rule` と同じく拒む)。`PIPELINE_VERSION` を `r3` → `r4`。
- `k1_wick.py`: 約定の口を項目 2 の `SimVenue`(`market_ref = last_bar_close`、spread 0)に置き換えた(`bar_close_venue()`、`k1_wick.py:176`)。runner の setup(`K1Setup`)も統合の口もこの規則を通る。統合の口の工場関数 `pipeline_strategy`(`k1_wick.py:189`)と宣言 `PIPELINE_PRODUCT` / `PIPELINE_RULES` を足した。**`BarCloseMarketFill` という名前は `bar_close_venue` の別名として残した**(`k1_wick.py:186`。理由は §7-1)。

**足した試験**
- `tests/bt/item_2/test_i2_fix_last_bar_close.py`(6 件): 規則の宣言と誤った値の拒否 / 足が無ければ `no_price_yet` / 最後に見た足の終値 ± spread/2(足と同じ時刻・後の時刻・新しい足)/ `next_bar_open` は次に始まる足まで待つが `last_bar_close` は到着で約定 / spread 未宣言・規則未宣言で止まる。
- `tests/bt/item_4/test_i4_fix_k1_module.py`(6 件): 手計算の場面(`tests/test_k1_wick.py` の SCENE_A)を統合の口で回し両側の約定が規則の文どおり / 規則を `next_bar_open` にすると建値が次の足の始値に動く / 乱数の足 600 本で全約定の値 = その時刻に会場が見た足の終値、かつ核に直接 `bar_close_venue` を差した経路と約定が同じ / `last_bar_close` は足の銘柄だけ / `module` は `bot.strategy.` の下だけ・無い工場は拒む・不正な params は実行で拒む / 実データ + 動作確認は拒む。試験は証拠の探索(`MARKET_ROOTS`)を空のフォルダに向け、リポジトリの市場ファイルを読まない。
- 変異の確かめ(スクラッチパッドの写しで): `venue.py` の値を `last_trade` に戻す → 1 failed / 門の I-6 を外す → 1 failed(`scripts` の外で打った `mutate.py` の出力「M1 venue: last_bar_close priced by last_trade: 1 failed, 2 passed」「M2 gate: no I-6 pass-through: 1 failed」。`-x` で最初の失敗で止めている)。

**試験の末尾の行**: 新しい 5 ファイル + `tests/test_k1_wick*.py` をまとめて「152 passed in 12.27s」(コマンドは §6)。

## 2. D-2(E-2): データ層に流し読みの口が無い

**根本原因**: `src/bot/bt/data/loader.py:459-511`(直す前)— `load` は全ファイルの全行を `Row`(記録・事象・JSON の identity)として `d.rows` に持ち(`loader.py:507`)、全行を揃えてから検査する(`loader.py:510` の `A.detect(d.spec, d.rows, len(d.paths))`)。行を捨てながら読む口が無い。

**直し方**
- `loader.py:459` `_read_file`: 1 ファイルの読み(bytes を 1 回、sha256、封印の照合、行の検証、範囲)を `load` から切り出した。`load` はこれを呼ぶだけで、動きは変えていない(試験の全体で確かめた、§6)。
- 新しい口 `src/bot/bt/data/stream.py`(`bot.bt.data.stream`): 1 つのデータセットをファイルごとに読み、`StreamChunk`(ファイルの記録・事象・異常・検査・解決)を 1 つずつ渡し、渡したファイルの行は持たない。同じ許可の一覧・同じ封印の台帳・同じ読み・同じ検査(`anomalies.detect`)を通る。**ファイルをまたぐ検査(重複・食い違い・世代の穴・重なり)は全行が要るので、代わりに「各ファイルの行はすべて前のファイルの行より後」を要求し、破れば `StreamOrderError`(`errors.py` に追加)で拒む**(そういうデータは `load` を使う)。24x7 / 24x5 の足は格子の検査を `load` と同じくストリームの最初の足に対して行い、24x7 ではファイルの境の穴も報告する。異常の種類に方針が名指しされていなければ拒む(`load` の `events` と同じ規則)。

**足した試験**: `tests/bt/item_1/test_i1_fix_stream.py`(8 件): 3 ファイルの事象・ファイルの記録・異常が `load` と同じで、データセットは行を持たない / ファイルごとの畳み = `load` の全体の畳み / 重なるファイルを拒む / 名指しの無い異常を拒み、名指しすれば `load` と同じ事象 / 24x7 の境の穴が `load` と同じ / 許可の無いパスは行を読む前に拒む / 封印のファイルを `load` と同じく拒み、境の前の範囲は読む / 2 度目の反復を拒む。変異の確かめ: 順序の検査を外す → 1 failed、境の穴を外す → 1 failed(`mutate.py` の出力「M3 … 1 failed, 2 passed」「M4 … 1 failed, 4 passed」)。

**確かめ(§2-3)**: 1 秒バー 2017〜2019 の日ファイル 1,095 本を 1 つのデータセットとして `stream` の 1 回の呼び出しで読み、60 分足に畳んだ(`scripts/k1_newenv_fix_stream_fold.py`。許可の一覧は段階 A と同じ = 根は 2017 / 2018 / 2019 のフォルダ、2020* / 2021* を拒む。畳みは段階 A と同じ `bars_from_bars` をファイルごとに、ファイルをまたぐ足は合わせる。書き出しも段階 A と同じ形)。
  - コマンド: `PYTHONPATH=<scratch>/datagate:src:scripts K1FIX_DATAGATE_LOG=<scratch>/logs/fold_refused.log python3 -c "import k1fix_datagate, runpy, sys; sys.argv=['k1_newenv_fix_stream_fold.py']; runpy.run_path('scripts/k1_newenv_fix_stream_fold.py', run_name='__main__')"`(08:06〜08:50 UTC。同じ時間に統合の口の実行 1 本と試験 1 本が走っていた)
  - 出力 `backtest_runs/k1_env_fixes/stream_fold/STREAM_FOLD.json` の値(逐語): `"files": 1095`、`"rows_1s": 49054818`、`"anomalies": 0`、`"bars_60m": 26276`、`"wall_s": 2608.5`、`"max_rss_mb": 257.0`、`"identical_csv_bytes": true`、`"identical_gz_bytes": false`、`"first_difference": null`。
  - **展開した bytes(CSV)は段階 A の 60 分足と全部同じ**(sha256 `3b5dfa54ab842e696f569d429aece539b1bbcdbdc5fcdbeffd269f1fe23ae4aa` が両方)。**gzip の bytes は違う**: 見出し(時刻・ファイル名)は同じで、先頭から 463,289 bytes が同じ、463,290 byte 目から違い、長さは段階 A 471,132 / 今回 471,126。原因は圧縮器への書き込みの切り方の違い(段階 A は 1 行ずつ文字の包みを通して書き、今回は 1 回で書いた)と推定(確かめていない)。
  - 時間と最大 RSS: 壁時計 2,608.5 秒(1 行あたり約 53 µs)、最大 RSS 257.0 MB(`ru_maxrss`、この 1 プロセス)。段階 A の日ファイルごとの `load` は 3 並列で 1,059.6 秒(`FOLD_MANIFEST.json` の `wall_s_total`)。1 本のプロセスで 3 年を読むので壁時計は長いが、メモリは 1 ファイル分で頭打ちになる(E-2 の推定「3 年で数十 GB」に対して 257.0 MB)。
  - 読んだファイルの数は 1,095、止めた `open` は 0(門の記録ファイルが作られていない)。

## 3. D-3(E-4): 検証の道具に日ブロックのブートストラップが無い

**根本原因**: `src/bot/bt/validation/bootstrap.py:64`(`block_bootstrap_ci`)— ブロックは固定長 `block_len`(`bootstrap.py:40`)だけで、日ごとに本数の違う「入口の日でブロック」を表せない。

**直し方**: `bootstrap.py:116` `label_block_bootstrap_ci`(値ごとのラベルでブロック)と `bootstrap.py:147` `day_block_bootstrap_ci`(ラベル = `t_ns` の UTC 日)を足し、`bot.bt.validation` から公開した。規則(モジュールの docstring): 日の数だけ日を復元抽出し、引いた日の値を全部入れた平均(値の多い日ほど重い)。区間は numpy の線形の分位、乱数は `numpy.random.default_rng(seed)` だけ(このモジュールの既存の決まりに合わせた)。ブロックが 1 つしかない・ラベルの数が合わない・`t_ns` が int でない・抽出が 2 回未満は拒む。

**足した試験**: `tests/bt/item_3/test_i3_fix_day_block_bootstrap.py`(4 件): 2 日の手計算(取りうる平均は 1 / 1.75 / 4 だけ、UTC の日の境 `DAY-1` と `DAY`)/ 本数の違う日で、規則の文から書いた別実装と区間・標準誤差が一致し、同じ種で同じ結果 / 同じ値でも日の分け方が違えば区間が違う / 拒否。変異の確かめ: 日でなく 1 値 1 ブロックにする → 1 failed(「M5 bootstrap: one value per block: 1 failed」)。

**確かめ(§2-4)**: 60 分足 39 升すべてで取引は 30 件以上(`fixes_pipeline.json` の `ci_day_block` が 39 升とも null でない)。統合の口の悲観側の取引で、ブロック = 入口の足の始まりの UTC 日、200 回・種 20260909・alpha 0.05(RESULT.md 1.5 の回数と種)で区間を出した。**`*` が段階 A の表と同じ升は 35 / 39、違う升は 4**(`60|s-/b24|strong`、`60|s10/b24|strong`、`60|s30/b-|strong` は段階 A だけ `*`、`60|soff/b40|strong` はこちらだけ `*`)。出力の末尾の行: 「star equal 35/39」。
- 2 つの区間の出し方の違い(事実。どちらが正しいかは書かない): 段階 A の表(`scripts/k1_newenv_tables.py: block_bootstrap`)は `random.Random(20260909)` 1 つを K1 の升の順(足 1→60、門、強さ)で全 234 升に通して使い、分位は `int(0.025 × (200−1))` 番目と `int(0.975 × (200−1))` 番目。今回の道具は升ごとに `default_rng(20260909)` を新しく作り、分位は numpy の線形補間。違う 4 升は、どちらかの区間の端が 0 の近く(|端| ≤ 0.97 bp)にある(下の表)。
- 表(平均は段階 A と統合の口で同じ値。区間は統合の口の悲観側。段階 A の区間と `*` は `docs/PHASE2/K1/NEWENV_A/cells.json`):

| 升 | 取引数(段階 A / 統合の口 悲観 / 楽観) | 平均 bp(段階 A = 統合の口) | 日ブロック 95% 区間(統合の口) | 日数 | `*` 日ブロック | 段階 A の表の区間 | `*` 段階 A |
|---|---|---|---|---|---|---|---|
| `60\|s-/b-\|both` | 6,236 / 6,236 / 6,236 | -6.197 | [-9.756, -2.700] | 1093 | * | [-9.862, -2.845] | * |
| `60\|s-/b-\|strong` | 3,723 / 3,723 / 3,723 | -5.749 | [-11.705, +0.475] | 1066 |  | [-12.197, +0.750] |  |
| `60\|s-/b-\|weak` | 3,339 / 3,339 / 3,339 | -2.919 | [-8.980, +3.557] | 1081 |  | [-9.315, +2.175] |  |
| `60\|s-/b24\|both` | 7,635 / 7,635 / 7,635 | -3.744 | [-6.849, -0.829] | 1093 | * | [-7.081, -0.858] | * |
| `60\|s-/b24\|strong` | 4,764 / 4,764 / 4,764 | -5.495 | [-10.601, +0.292] | 1078 |  | [-10.572, -0.333] | * |
| `60\|s-/b24\|weak` | 4,390 / 4,390 / 4,390 | -0.841 | [-5.214, +3.664] | 1090 |  | [-5.744, +3.400] |  |
| `60\|s-/b40\|both` | 7,066 / 7,066 / 7,066 | -3.064 | [-6.514, +0.152] | 1094 |  | [-6.709, +0.288] |  |
| `60\|s-/b40\|strong` | 4,282 / 4,282 / 4,282 | -4.791 | [-10.563, +1.043] | 1074 |  | [-9.959, +0.684] |  |
| `60\|s-/b40\|weak` | 3,960 / 3,960 / 3,960 | +1.910 | [-2.931, +6.820] | 1087 |  | [-4.519, +7.473] |  |
| `60\|s10/b-\|both` | 6,011 / 6,011 / 6,011 | -6.057 | [-9.894, -2.566] | 1087 | * | [-9.868, -1.994] | * |
| `60\|s10/b-\|strong` | 3,585 / 3,585 / 3,585 | -5.682 | [-12.156, +0.246] | 1052 |  | [-12.700, +1.344] |  |
| `60\|s10/b-\|weak` | 3,235 / 3,235 / 3,235 | -2.693 | [-8.426, +4.399] | 1073 |  | [-9.230, +3.719] |  |
| `60\|s10/b24\|both` | 7,414 / 7,414 / 7,414 | -3.606 | [-7.330, -0.351] | 1087 | * | [-7.228, -0.071] | * |
| `60\|s10/b24\|strong` | 4,627 / 4,627 / 4,627 | -5.441 | [-10.142, +0.224] | 1066 |  | [-11.098, -0.353] | * |
| `60\|s10/b24\|weak` | 4,286 / 4,286 / 4,286 | -0.616 | [-6.413, +4.775] | 1082 |  | [-6.013, +4.219] |  |
| `60\|s10/b40\|both` | 6,842 / 6,842 / 6,842 | -2.868 | [-6.570, +0.286] | 1087 |  | [-6.232, +0.388] |  |
| `60\|s10/b40\|strong` | 4,145 / 4,145 / 4,145 | -4.720 | [-10.503, +0.141] | 1061 |  | [-10.963, +0.651] |  |
| `60\|s10/b40\|weak` | 3,860 / 3,860 / 3,860 | +2.378 | [-3.148, +8.001] | 1080 |  | [-3.284, +7.220] |  |
| `60\|s19/b-\|both` | 5,296 / 5,296 / 5,296 | -5.448 | [-9.796, -1.269] | 1064 | * | [-8.734, -1.408] | * |
| `60\|s19/b-\|strong` | 3,150 / 3,150 / 3,150 | -4.675 | [-11.602, +2.972] | 1007 |  | [-12.480, +2.789] |  |
| `60\|s19/b-\|weak` | 2,872 / 2,872 / 2,872 | -2.396 | [-10.142, +6.275] | 1020 |  | [-9.893, +5.429] |  |
| `60\|s19/b24\|both` | 6,726 / 6,726 / 6,726 | -2.763 | [-6.653, +0.602] | 1070 |  | [-6.554, +1.083] |  |
| `60\|s19/b24\|strong` | 4,197 / 4,197 / 4,197 | -4.739 | [-9.550, +1.254] | 1030 |  | [-10.300, +1.343] |  |
| `60\|s19/b24\|weak` | 3,950 / 3,950 / 3,950 | -0.696 | [-6.308, +5.702] | 1044 |  | [-6.523, +4.972] |  |
| `60\|s19/b40\|both` | 6,139 / 6,139 / 6,139 | -1.651 | [-5.426, +1.523] | 1068 |  | [-5.496, +1.527] |  |
| `60\|s19/b40\|strong` | 3,711 / 3,711 / 3,711 | -3.760 | [-9.976, +1.659] | 1017 |  | [-10.467, +2.957] |  |
| `60\|s19/b40\|weak` | 3,502 / 3,502 / 3,502 | +2.860 | [-2.902, +8.970] | 1035 |  | [-3.247, +8.872] |  |
| `60\|s30/b-\|both` | 4,313 / 4,313 / 4,313 | -7.285 | [-12.122, -3.304] | 1026 | * | [-11.608, -1.933] | * |
| `60\|s30/b-\|strong` | 2,538 / 2,538 / 2,538 | -9.583 | [-17.733, +0.296] | 914 |  | [-16.877, -0.968] | * |
| `60\|s30/b-\|weak` | 2,365 / 2,365 / 2,365 | -2.143 | [-11.588, +6.384] | 946 |  | [-11.322, +6.639] |  |
| `60\|s30/b40\|both` | 5,178 / 5,178 / 5,178 | -2.369 | [-6.692, +2.505] | 1027 |  | [-6.400, +1.987] |  |
| `60\|s30/b40\|strong` | 3,105 / 3,105 / 3,105 | -7.053 | [-14.829, +0.603] | 933 |  | [-13.918, +1.614] |  |
| `60\|s30/b40\|weak` | 3,023 / 3,023 / 3,023 | +3.642 | [-3.205, +10.052] | 973 |  | [-3.272, +10.484] |  |
| `60\|soff/b24\|both` | 6,291 / 6,291 / 6,291 | -3.055 | [-7.216, +1.016] | 1062 |  | [-6.738, +0.626] |  |
| `60\|soff/b24\|strong` | 3,882 / 3,882 / 3,882 | -4.715 | [-10.572, +1.171] | 996 |  | [-10.887, +0.960] |  |
| `60\|soff/b24\|weak` | 3,747 / 3,747 / 3,747 | -0.395 | [-6.040, +6.069] | 1030 |  | [-6.140, +6.057] |  |
| `60\|soff/b40\|both` | 4,465 / 4,465 / 4,465 | -1.089 | [-6.452, +4.919] | 974 |  | [-6.380, +3.915] |  |
| `60\|soff/b40\|strong` | 2,625 / 2,625 / 2,625 | -7.859 | [-16.537, -0.330] | 849 | * | [-17.231, +1.663] |  |
| `60\|soff/b40\|weak` | 2,651 / 2,651 / 2,651 | +4.420 | [-2.826, +11.812] | 919 |  | [-1.921, +12.190] |  |

## 4. D-4(E-10): 画面の通貨の札が「円」固定

**根本原因**
- `src/bot/monitoring/backtest_view.py:117, 128-130, 134, 145-147`(直す前)— 札の文字列に「(円)」が直書き。
- `src/bot/bt/repro/runner.py:193, 203, 218`(直す前)— runner の実行記録に通貨の欄が無く、指標の鍵が `pnl_jpy` / `realized_jpy`(円と決め打ちの名前)。`src/bot/bt/repro/fixed.py:186-193`(`Parts`)にも通貨が無い。

**直し方**
- `fixed.py:196`: `Parts.currency`(商品の建値通貨。None = setup が言っていない)。K1 の setup は `"USD"`(`k1_wick.py:246`、`PIPELINE_PRODUCT["quote_ccy"]`)。
- `runner.py:164-166, 196, 206, 222`: 実行記録に `"currency"`、指標を `"pnl": {"currency", "realized", "fees"}` と `"equity": {"t_ns", "realized", "currency"}` に(空文字などは拒む)。
- `backtest_view.py:106-121`: `run_currency(rec)` が記録だけから通貨を読む(runner の記録の `currency`、無ければ統合の口の記録の `config.account.currency`、どちらも無ければ None)。札は JPY → 「(円)」、それ以外 → 「(USD)」など、None → 「(通貨の記録なし)」。損益の値は `pnl`(D-4 より前の記録は `pnl_jpy`)から読む。

**足した試験**: `tests/bt/item_3/test_i3_fix_currency.py`(3 件): K1 の setup で XBTUSD の 6 本の場面を runner で回し、記録の通貨が USD、指標に `pnl_jpy` が無く `pnl.currency = USD`、実現損益 = 2 往復の値幅の和、**画面の全タブの文字と HTML に「円」が 1 字も無く**「実現損益(USD)」「損益(USD)」「maker 手数料(USD)」が出る / 通貨の無い古い形の記録は「(通貨の記録なし)」で「円」が出ない / JPY の記録は「(円)」、統合の口の記録は口座の通貨。変異の確かめ: 札を「(円)」に戻す → 1 failed、記録の通貨を None にする → 1 failed(「M6 view: yen label fixed: 1 failed」「M7 runner: no currency in the record: 1 failed」)。

## 5. D-1 の確かめ(§2-2): 60 分足 39 升を統合の口で回し、段階 A の実行記録と比べた

- コマンド: `PYTHONPATH=<scratch>/datagate:src K1FIX_DATAGATE_LOG=… python3 -c "import k1fix_datagate, runpy, sys; sys.argv=['k1_newenv_fix_pipeline.py','--workers','1']; runpy.run_path('scripts/k1_newenv_fix_pipeline.py', run_name='__main__')"`(08:14〜08:36 UTC、壁時計 1,376.6 秒、1 升 25.4〜49.5 秒、最大 RSS 177.1〜315.8 MB(ログ `pipeline39.txt` の各行の `wall_s` と `max_rss_mb`))。
- 宣言: データ = 段階 A の 60 分足 / 商品 XBTUSD(USD、建玉 1 単位)/ 規則 `market_ref = last_bar_close` / 約定 tier 2 を両側(K1 は成行だけなので tier は効かない)/ 遅延 4 経路とも定数 0 / 費用 maker 0・taker 0・spread 0 / 口座 USD・現金 1e9・レバレッジ 1・清算なし / 目的 研究・事前登録 `docs/PHASE2/K1/PREREG.md`(段階 A と同じ)。
- 出力の末尾の行(逐語): 「cells 39; both sides equal to stage A: {'same_n_trades': 39, 'same_mean_bp': 39, 'same_fill_columns': 39, 'same_trade_columns': 39}; star equal 35/39; reproduced 39/39 -> /home/user/trade/docs/PHASE2/K1/NEWENV_A/fixes_pipeline.json」
- 意味: 39 升すべてで、悲観側・楽観側の両方について、段階 A の実行記録(`backtest_runs/k1_newenv_a/<run_id>/`)と**取引数が同じ**、**1 件ごとの bp の平均が同じ値**(浮動小数の `==`)、**約定の列(注文 id・時刻・向き・値・数量・流動性)が全行同じ**、**往復の列(向き・数量・建値・決済値・建てた時刻・閉じた時刻・決済理由)が全行同じ**。2 回の実行の byte 一致は 39 / 39。違う升が 0 なので、升ごとの原因の欄は無い。**一致は数が同じという事実だけで、正しさの根拠にはしない**(段階 A も同じ K1 の規則の実装を通っている。約定の値付けが戦略側の `BarCloseMarketFill` から会場の模型に移ったことの確かめにはなるが、規則の読み違いがあれば両方に同じく入る)。
- 起源の証拠(`record.data[0].origin_evidence`)は 39 升とも `by: rows`・`market_path = backtest_data/k1_newenv_a_20260927/xbtusd_60m_2017_2019.csv.gz`(探索先をこの 1 ファイルに絞ったため。§7-2)。
- 追加(runner の経路): K1 の setup の約定の口を `SimVenue` に替えたので、runner の口でも 2 升(`60|s19/b24|both`、`60|soff/b40|strong`)を回し直し、段階 A と比べた。出力(逐語)「runner 60|s19/b24|both: trades 6726 vs 6726, trade cols equal True, fill cols equal True, currency USD, identical True」「runner 60|soff/b40|strong: trades 2625 vs 2625, trade cols equal True, fill cols equal True, currency USD, identical True」。この 2 升の記録は消した(スクラッチパッドの一時フォルダ)。

## 6. 関係する試験(§2-6)

コマンド(直した後、08:19〜08:34 UTC):

```
PYTHONPATH=<scratch>/datagate:src K1FIX_DATAGATE_LOG=<scratch>/logs/after_refused.log python -m pytest tests/bt tests/test_k1_wick.py tests/test_k1_wick_critic.py -p k1fix_datagate -p no:cacheprovider --basetemp=<scratch>/pt_after -rfE
```

- 末尾の行(直した後): 「7 failed, 17731 passed, 6 skipped, 3 warnings, 177 errors in 907.48s (0:15:07)」
- 同じコマンドを直す前に打った(08:02〜08:18、ただし 08:05 以降に編集を始めたので、途中から一部の源を読んだ可能性がある): 「7 failed, 17704 passed, 6 skipped, 3 warnings, 177 errors in 944.22s (0:15:44)」
- failed の 7 件の試験 id は前後で同じ(`diff` の出力が空)。errors の見出し 177 行も前後で同じ(`diff` の出力が空)。passed の差 27 = 新しい試験 27 件(6 + 6 + 8 + 4 + 3)。
- **7 failed と 177 errors は全部、作業者のデータの門が止めた `open` による**: 失敗・エラーの本文 22 節すべてに `k1fix datagate` の `PermissionError` がある(`re.split` で節に分けて数えた出力「sections 22 with datagate refusal 22」)。該当する試験は、許されていないデータを読む試験: `tests/bt/item_2/test_i2_real_data_check.py`(5 errors)、`tests/bt/item_4/test_i4_r2_origin_from_data_grid.py`(108 errors)、`tests/bt/item_4/test_i4_r3_origin_by_rows_grid.py`(64 errors)、`tests/bt/critic/item_4/test_i4r2_origin_survives_reencoding.py`(6 failed)、`tests/bt/item_4/test_i4_real_data_smoke.py`(1 failed)。**これらはこの委任のデータの決まりの下では回せていない**(§9)。
- 全体で止めた `open` は 17,622 件。多くは統合の口の起源の証拠の探索(`pipeline._market_candidates` / `_bounds`)が、試験の中でデータの置き場の全ファイルの先頭行を読もうとしたもの(`bitmex_trade_1s_XBTUSD` の 2020・2021 年の日ファイルに 5,117 件 = 直す前の全体の記録、`paper_logs/tape` に 702 件、`auto_bitflyer_executions_20260921` に 651 件ほか。数は直す前の記録 `base_refused.log` の集計)。呼び出し元を 1 件ずつは確かめていない。

## 7. 自分で決めたこと(原文に無い判断。理由つき)

1. **`BarCloseMarketFill` の名前を消さず、`bar_close_venue` の別名として残した。** 値付けの中身は会場の模型に移したので戦略側の約定の実装は消えた。名前を消すと `tests/test_k1_wick.py` と批評家の `tests/test_k1_wick_critic.py` を書き換えることになり、この 2 つは作業者の持ち物(委任文 §3)に入っていないため。消すかはリードに聞く(§9)。
2. **統合の口の確かめの実行で、証拠の探索先 `MARKET_ROOTS` を 60 分足 1 本へのリンクだけのフォルダに差し替えた**(`scripts/k1_newenv_fix_pipeline.py` の `plan`)。そのままだと探索がデータの置き場の全ファイルを開こうとし(§6 の数)、読んではいけないデータに触れ、さらに 1 分足の畳んだファイル(1,523,877 本)を証拠のために丸ごと読み込むため。記録の証拠は「この 1 ファイルと行が一致」になる。
3. **作業者の実行と試験をデータの門(監査フック)の下で回した**(§0)。委任文は「試験は `tests/bt/` を回す」と「読んでよいデータはこれだけ」の両方を言っており、試験の一部は許されていないデータ(2026-08-28 以降のファイルを含む)を読むため、両方を満たす形として、読もうとしたら開く前に止めて失敗として見えるようにした。
4. 統合の口の戦略の口 `module` は `bot.strategy.` の下のモジュールだけを受ける(宣言から任意のモジュールを読み込ませないため)。
5. 確かめの宣言の値: 口座の現金 1e9 USD・レバレッジ 1・清算なし(K1 の規則に資本が無く、口座が 1 単位の注文を断らないため。断れば取引数に出る)/ 約定 tier 2(成行だけなので効かない)/ 商品の tick 0.5(K1 は成行だけで tick を使わない。BitMEX の XBTUSD の呼値として置いたが、一次資料では確かめていない。`k1_wick.py` の注記にも書いた)/ spread 0。
6. `Parts.currency` の既定を None(= 言っていない)にした。`FixedSetup`(bitFlyer 用の試験の setup)は通貨を言わないので、その記録の画面は「(通貨の記録なし)」になる(以前は「円」と決め打ち)。runner の指標の鍵 `pnl_jpy` / `realized_jpy` は `pnl` / `realized` に改名した(統合の口の `pnl_jpy` は変えていない。§9)。
7. 流し読みの口は、ファイルをまたぐ検査を「時刻の順に並んだ重ならないファイル」の要求で置き換えた(全行を持たずにできる形)。
8. 日ブロックの道具は、このモジュールの既存の決まり(`default_rng(seed)`、線形の分位)に合わせた。段階 A の表の出し方(1 つの `random.Random` を升の順に通す・切り捨ての添字)には合わせていない。
9. 流し読みの畳みの出力の gzip の見出しの時刻を段階 A のファイルの見出しの時刻にそろえた(圧縮後の bytes も比べられるように。gzip は見出しに書いた時刻を持つ)。

## 8. 見つけたが直していないもの(リードの指示 (3) による)

**台帳に載った封印のファイルの中身(bytes)を、拒む前に環境が読んでいる**(再現した)。

- 場所: `src/bot/bt/data/loader.py:475-480`(直す前。今は `_read_file` の `loader.py:461-466`)— ファイルを開いて全 bytes を読み、sha256 を取ってから台帳と照合し(`seals.match`)、そのあとで `check_range` が拒む。
- 再現の手順(合成のデータだけ): `PYTHONPATH=src python3 scripts/k1_newenv_fix_seal_repro.py <スクラッチの置き場>` — 一時の置き場に 49 bytes の CSV と、それを 2020-01-01 から封印する台帳 `backtest_data/phase2_sealed/U/SEALED.json` を作り、範囲なしで `load` を呼ぶ。監査フックでそのファイルの `open` を、`hashlib.sha256` の差し替えで読んだ bytes の長さを記録する。
- 出力(逐語):
  ```
  file size 49
  sha256 of bytes 171
  open backtest_data/x/f.csv
  sha256 of bytes 49
  refused SealedRangeError
  ```
  (171 bytes は台帳の記録そのものの sha256。封印のファイルが開かれ、49 bytes 全部が読まれて sha256 を取られたあとに `SealedRangeError` で拒まれた。行の解読の前には拒んでいる。)
- 関連の観察(再現ではない): 試験の全体で、データの門が止めた `open` 17,622 件のうち 882 件(異なるファイル 126)が台帳に載ったファイルだった。どのコードが開こうとしたかは確かめていない。

## 9. リードに聞くこと

1. §8 の「台帳の封印のファイルを拒む前に bytes を読む」を直すか(直すなら、パスで照合できるものは開く前に拒み、別名の写しは bytes で照合する形になる)。作業者は直していない(指示どおり)。
2. 統合の口の起源の証拠の探索(`pipeline._market_candidates` / `_bounds` / `row_evidence`)は、データの置き場の全ファイルを開いて先頭行・先頭と末尾の行を読み、見出しの合う市場ファイルを証拠のために丸ごと読み込む。これは「新鮮データ・封印の区間を読まない」決まりと、1 分足の畳んだファイルのような大きなファイルとぶつかる。今回は確かめの実行で探索先を差し替えて避けた(§7-2)。探索の範囲を環境の側で決めるか。
3. 試験の 5 ファイル(§6: 7 failed + 177 errors)は許されていないデータを読むので、この委任の下では回していない。別に回すか(誰が・どのデータの決まりで)。
4. `BarCloseMarketFill` の別名を消し、`tests/test_k1_wick.py` と `tests/test_k1_wick_critic.py` を `bar_close_venue` に書き換えるか(§7-1)。
5. 統合の口の指標の鍵 `pnl_jpy` / `realized_jpy`(`pipeline.py` の metrics。銘柄ごとの通貨の額を足している)も改名するか。画面は記録の口座の通貨から札を出すので「円」固定ではなくなったが、鍵の名前は円のまま(§7-6)。
6. 日ブロックの区間の `*` が段階 A の表と 4 升で違う(§3)。どちらを正解ともしていない。段階 G で使う区間の出し方(道具の `default_rng`・線形の分位か、当時の形か)を決めるか。

## 10. やっていないこと

なし。委任文 §2 の 1〜6(k1a-c-02 を外したあとの D-1〜D-4)は上限(11:55 UTC)の前、08:5x UTC に終えた。批評家の回はこの作業者の外。

## 付録: 変えた・作ったファイル

- 変えた: `src/bot/bt/orders/rules.py`、`src/bot/bt/fill/venue.py`、`src/bot/bt/pipeline.py`、`src/bot/bt/data/loader.py`、`src/bot/bt/data/errors.py`、`src/bot/bt/data/__init__.py`、`src/bot/bt/validation/bootstrap.py`、`src/bot/bt/validation/__init__.py`、`src/bot/bt/repro/fixed.py`、`src/bot/bt/repro/runner.py`、`src/bot/monitoring/backtest_view.py`、`src/bot/strategy/k1_wick.py`。`src/bot/bt/data/allowlist.py` は k1a-c-02 のための変更を戻し、`bf44529a~1` と同じ。
- 作った: `src/bot/bt/data/stream.py`、`tests/bt/item_1/test_i1_fix_stream.py`、`tests/bt/item_2/test_i2_fix_last_bar_close.py`、`tests/bt/item_3/test_i3_fix_day_block_bootstrap.py`、`tests/bt/item_3/test_i3_fix_currency.py`、`tests/bt/item_4/test_i4_fix_k1_module.py`、`scripts/k1_newenv_fix_pipeline.py`、`scripts/k1_newenv_fix_stream_fold.py`、`scripts/k1_newenv_fix_datagate.py`、`scripts/k1_newenv_fix_seal_repro.py`、`docs/PHASE2/K1/NEWENV_A/fixes_pipeline.json`、この `FIXES.md`、`backtest_runs/k1_env_fixes/`(`.gitignore`、`pipeline/` 39 升、`stream_fold/`)。
- リードのチェックポイント `bf44529a`(08:12 UTC、作業途中の写し)が作業中に入った。上の差分はその一つ前 `bf44529a~1` との比べ。
