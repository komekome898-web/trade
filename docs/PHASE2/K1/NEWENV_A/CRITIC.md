# K1 段階 A — 批評家(1 回)

委任文 `docs/DATA/delegations/20260927_k1_on_new_env.md` §3 の射程(逐語): 「**批評家(1 回、作業者のあと): 射程 = 正しさ(INTENT_MAP の ○ が実装と合うか、裁きが規則の文に立つか)・安全(封印の区間と新鮮データを読んでいないこと = データ層の記録で確かめる)・統合**」。
期限 08:30 UTC(着手 07:10 UTC)。git の操作はしていない。書いたのはこのファイルと `tests/test_k1_wick_critic.py` だけ。

## §0.1 の表

| やること | 委任文・リードの委任の該当語(逐語) |
|---|---|
| `k1_wick.py`・`k1_newenv_tables.py` が当時のスクリプトの算術を写していないかを、行を突き合わせて見る | 「**写していないか**」/ 委任文 §2-1「**算術を写さない(写すと環境の検査にならない)**」 |
| 表の平均が実行記録から作られているかを、表の生成側のコードと、私が別に書いた計算で確かめる | 「**一致の意味**」「**`k1_newenv_tables.py` が何を読んで平均を出しているかを確かめる**」 |
| 読んだファイルが BitMEX 2017〜2019 だけかを、`FOLD_MANIFEST.json` と全実行記録の `record.json`・`data_quality.json` で確かめる | 「**`FOLD_MANIFEST.json` の入力の一覧と、実行記録の `data_quality.json` で確かめる**」 |
| INTENT_MAP の ○ を 5 項以上抜き取って、実装と規則の文を突き合わせる | 「**INTENT_MAP の ○ を 5 項以上抜き取り**」 |
| 指定の 4 つの試験を私有の basetemp で回し、末尾の行を書く | 「**私有の basetemp …で回し、末尾の行を書く**」 |
| ENV_DEFECTS から 3 件以上を抜き取って、ファイル:行を確かめる | 「**3 件以上抜き取る**」 |
| 規則の文から書いた 2 つ目の実装と核の出力を突き合わせる試験を足す | 「**足すなら `tests/test_k1_wick_critic.py` だけ**」 |

## 指摘

### k1a-c-01 [直す] 正しさ — 「算術は写していない」という記述が一部で事実と合わない(ただし、環境の検査としての 234 升の一致は崩れない)

**事実(打ったコマンドと出力)**: 建玉の機械(`k1_wick.py: K1WickStrategy.on_event`、133 行〜)の注釈 4 本が、当時の `simulate()` の注釈と同じ文言である。どれも規則の文(`RESULT.md`・`PREREG.md`)には無い。
```
$ for p in "増し玉はしない。ラインだけ更新" "強弱を問わず新規" "強いシグナルはドテン" "足の色が建玉と反対のときだけ見る" "切り捨ててから比較(原典どおり)"; do grep -n "$p" docs/PHASE2/K1/RESULT.md docs/PHASE2/K1/PREREG.md scripts/measure_katsuo_effect.py src/bot/strategy/k1_wick.py; done
scripts/measure_katsuo_effect.py:204 / src/bot/strategy/k1_wick.py:149   (増し玉はしない。ラインだけ更新)
scripts/measure_katsuo_effect.py:209 / src/bot/strategy/k1_wick.py:155   (強弱を問わず新規)
scripts/measure_katsuo_effect.py:207 / src/bot/strategy/k1_wick.py:152   (強いシグナルはドテン)
scripts/measure_katsuo_effect.py:196 / src/bot/strategy/k1_wick.py:142   (足の色が建玉と反対のときだけ見る)
docs/PHASE2/K1/RESULT.md:60        / src/bot/strategy/k1_wick.py:76    (← これだけは規則の文にある)
```
分岐の形(`if pos == sig: 線だけ更新 / elif pos == -sig: 決済(REVERSED if strength == "strong" else OPPOSITE_WEAK)、強いなら建て直す / else: 新規`)も `simulate()` 203〜210 行と同じ順・同じ式である。
表の生成側 `k1_newenv_tables.py: block_bootstrap`(63〜73 行)は、区間の分位の添字 `means[int(0.025 * (len(means) - 1))]` が当時の 236〜237 行と同じで、乱数 1 本を「足 1→60、門、強さ」の順に消費する(12 行・148 行)。分位の取り方と消費の順は `RESULT.md` 1.5 の文に無い(1.5 は「入口の日でブロックに切り、日を復元抽出、200 回、種 20260909」だけ)。
これと食い違う記述:
- `INTENT_MAP.md` 冒頭の「**算術は写していない**: 実装は核の事象の口…の上に書き直し」と「当時のスクリプトは規則の読み取りにだけ開いた」。
- `DIFF.md` §0 の「乱数の消費順が当時と同じである保証は無い…算術を写さない以上確かめない」。実際には 234 升で `*` の食い違いが 0 升であり、そうなるのは当時の分位の添字と消費の順に合わせた場合だけである。

**環境の検査として崩れない理由(推定ではなく、以下で確かめた)**: 写されたのは (a) 戦略の判断の分岐(規則の文 1.3・1.4 自体が擬似コードなので、書き直しても同じ形になる部分)と、(b) △ 印の付いた `*` の統計だけである。平均が通る経路は、次のとおりすべて新しいコードである。データ層の読み(`bot.bt.data.load`)→ 畳み(`bars_from_bars`。numpy の `reduceat` で、当時の Python の逐次ループとは別物)→ 核の事象の順序 → 約定の口 `BarCloseMarketFill` → `round_trips` → `trades.json` → 表の生成側の式。表の生成側は平均を `trades.json` から作っている(`k1_newenv_tables.py:78` `read_json(..., "trades.json")["data"]`、`entry_px`・`exit_px`・`side` から r を計算)。畳んだ足から直接は計算していない。確かめた内容は k1a-c-06 と k1a-c-07 に書いた。

**直し方**: INTENT_MAP 冒頭・S/P 節・T-5 と DIFF §0 を事実に合わせる。書く内容は次の 3 点。「建玉の機械の分岐と注釈は当時の `simulate()` の形に沿って書いた(規則の文 1.4 と同じ内容)」「`*` の区間は当時の分位の添字と乱数の消費順に合わせた代理である」「そのため 234 升の一致が確かめたのは環境の部品の経路であり、戦略の判断を規則の文から独立に読み直した結果ではない。後者は `tests/test_k1_wick.py` の 6 場面と `tests/test_k1_wick_critic.py` で見ている」。

### k1a-c-02 [注記] 安全 — 今回は封印の区間も新鮮データも読んでいない。ただし実行の段の許可の一覧は K1 の封印の区間を拒まない

**読んでいないことの根拠**(打ったコマンドの出力の要点):
- `FOLD_MANIFEST.json: inputs` は 1,095 件で、`rel_real` の年は `{'2017': 365, '2018': 365, '2019': 365}`、最小 `…/2017/20170101.csv.gz`、最大 `…/2019/20191231.csv.gz`。`rows_read` の合計 = `rows_kept` の合計 = 49,054,818。`given == rel_real` は 1,095/1,095(記号リンクを経由していない)。
- 許可の一覧は `roots = …/2017, …/2018, …/2019`、`deny` に `2020*`・`2021*` がある。`refusals_proven` は 2020-01-01・2021-12-31・`binance_BTCUSDT_1m.csv` の 3 つが拒まれたことを記録している。拒否はファイルを開く前に起きる(`loader.py:470-471`: 注釈「every path of every dataset is checked before any row is read」と `checked = [[allow.check(root, p) …]]` が、475 行の `open` より前にある)。
- `backtest_runs/k1_newenv_a/` の実行記録 253 件すべてについて、`record.json: data_sha256` が読んだのは畳んだ 6 ファイルだけで、その指紋は `FOLD_MANIFEST.json: outputs` と 253/253 で一致した(`bad []`)。`data_quality.json` に出るパスも、畳んだ 6 ファイルと封印の台帳 `phase2_sealed/P2-*/SEALED.json`(指紋の照合に読む台帳だけ)に限られる。
- 畳んだ 1 分足の先頭は `2017-01-01T00:00:00`、末尾は `2019-12-31T23:59:00`。核の `last_time_ns` = 1577836800 s(末尾の足の閉じる時刻 = 2020-01-01T00:00:00)。

**注記**: 実行の段(`runner._execute`、`runner.py:156` `load(plan.root, datasets)`)は許可の一覧を渡さないので、既定の `roots = [backtest_data, data, paper_logs/tape]`、`deny = [qa_*, o3c_*, phase2_runs, phase2_sealed]` で動く(`data_quality.json: manifest.allowlist`)。K1 の封印の区間(BitMEX 2020〜2021)はデータ層の封印の台帳(`phase2_sealed` の P2-*)に無い(`grep -n "bitmex\|2020" src/bot/bt/data/*.py` の結果は 0 件)。今回は畳みの段で止めてあり、実行は畳んだファイルしか読まないので安全である。ただし、次の段(G など)で秒バーを実行の段から直接読む場合は、機械では止まらない。止める場所を畳みのスクリプトから実行の段(またはデータ層の台帳)に移すかどうかは、リードが判断する。

### k1a-c-03 [直す] 正しさ(数の出所)— DIFF §2 の「11 件」は収集される件数と合わない
`DIFF.md:20` には「`tests/test_k1_wick.py`、11 件すべて通過」とあるが、次の実測では 8 件である。
```
$ PYTHONPATH=src python -m pytest tests/test_k1_wick.py --collect-only -p no:cacheprovider | tail -1
8 tests collected in 0.30s
```

### k1a-c-04 [直す] ENV_DEFECTS の場所と数の傷(7 件を抜き取った。5 件は合い、2 件に傷がある)
- 合ったもの: E-2 `loader.py:459-511`(`def load` は 459 行、`json.dumps(rec, sort_keys=True)` は 507 行)/ E-3 `venue.py:554-567`(`_aggress_no_book`。`next_bar_open` は `bar_open` に回し、`last_trade is None` なら `no_price_yet` で閉じる)と `venue.py:734-748`(`_on_bar`。`bar_open` の注文を `ev.open` ± 半スプレッドで約定させる)/ E-4 `bootstrap.py:64`(`block_bootstrap_ci(x, *, block_len, …)`)/ E-11 `k1_newenv_run.py:179-186`(`Pool` と `imap_unordered`)/ E-10 の「円」の直書き(実際は `backtest_view.py:117, 128-130, 134, 145-147`。書かれた 147-149 は 2 行ずれている)。INTENT_MAP D-6 の根拠 `BarEvent._validate` も `events.py:265-269` の `_positive`(値 ≤ 0 を拒む。116-120 行)で合った。
- 傷 1: E-7・E-8 の「`runner.py:261-275`(`_twice`)」。`_twice` は 245〜260 行で、261〜275 行は `check_reproducible`(263 行)と `_ensure_runs_dir`(273 行)である(`grep -n "^def " src/bot/bt/repro/runner.py`)。
- 傷 2: 数の代わりに置き場所の名前が書かれている。E-2 は「**`FOLD_MANIFEST.json: wall_s_total`** 秒」(実際の値は 1059.6)、E-7 は「1 回 **PERFORMANCE.md の値** 秒」(値が無い)。E-9 の推定(1 分足の 1 升で約 9 GB)は、実測(`PERFORMANCE.md` §3 の最大 RSS 4,619.9 MB)に置き換わっていない。E-5 の「コミットはしない = 作業木の差分として残す」は、現状と合わない(`git status --short` の差分は TRACE の 1 件だけで、`pipeline.py` は `457dcef4~1` と差が無い。削除はリードのチェックポイントのコミットに入っている)。

### k1a-c-05 [注記] 統合 — 実行記録の置き場に索引の外の記録と作業ディレクトリの残骸がある。重複した升の中身は一致した
- `backtest_runs/k1_newenv_a/` には 253 件の実行記録があり、そのうち `runs_index.json`(234 升、run_id も 234 通り)の外に 19 件ある。ほかに `.work-*` の残骸が 6 個あり、うち 1 個(`.work-a6ccbc45…-0`)は `record.json` を持つが `repro.json` を持たない。
- 16 升は 2〜4 回、別々のコミット(`685b0f93`・`8430ddc5`・`14580fc9`・`350d9181`・`7295906d` ほか)で回されていた。`trades.json` の `data` 部分の sha256 は 16 升すべてで同じである(`Counter({'same': 16})`。ファイル全体の sha が違うのは `run_id` を含むため)。setup の指紋はすべて `4435c3fd6089…`、核は `core-19` である。
- 残骸の片付けは作業者またはリードの判断に任せる(私は消していない)。

### k1a-c-06 [注記] 正しさ — 規則の文から書いた 2 つ目の計算で 4 升を突き合わせ、実行記録と一致した(一致の意味の確認)
`/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/indep.py` を使った(リポジトリの外)。畳んだ足ファイルは `csv` で読み(データ層を通さない)、`RESULT.md` 1.3・1.4 を自分で書いたループで回し、それを実行記録の `trades.json` と `cells.json`・当時の値と並べた。
```
60|s19/b24|both  indep n 6726  mean -2.763 hold 2 | run trades n 6726  mean -2.763 | cells 6726 -2.763 2 | RESULT -2.76, n 6726 / 2 | px not at bar close 0
15|soff/b40|weak indep n 4363  mean  2.579 hold 4 | run trades n 4363  mean  2.579 | cells 4363  2.579 4 | RESULT +2.58            | px not at bar close 0
30|s-/b-|strong  indep n 6698  mean -0.525 hold 3 | run trades n 6698  mean -0.525 | cells 6698 -0.525 3 | RESULT -0.53            | px not at bar close 0
5|s30/b40|both   indep n 10519 mean -1.780 hold 4 | run trades n 10519 mean -1.780 | cells 10519 -1.78 4 | RESULT -1.78, n 10519 / 4 | px not at bar close 0
```
「px not at bar close 0」は、全取引の建値と決済値が、閉じる時刻 = 約定時刻の足の終値と一致したという意味である(INTENT_MAP P-7 の確認)。ただし、この 2 つ目の計算も規則の文(擬似コード)に沿うので、形は当時と似る。独立なのは読みの経路と約定の経路である。

### k1a-c-07 [注記] 正しさ — 核の上の K1 と、規則の文の 2 つ目の読みを突き合わせる試験を足した
`tests/test_k1_wick_critic.py` を足した。種つきの乱数の足(0.5 ドル刻み、同値の足、切り捨て後のヒゲの同長を含む)400 本 × 種 3 × 門 13 × 強さ 3 = 117 件で、往復ごとに(向き、建値、決済値、建てた足、決済の足、理由)が一致することを確かめる。2 つ目の読みは `signal_of_bar` を呼ばない(ヒゲは `h − max(o, c)` / `min(o, c) − l` の形で別に書いた)。
- 結果: `117 passed in 10.03s`。
- この試験が違いを検出できるかも確かめた。`signal_of_bar` を「`int()` で切り捨てない」ものに差し替えると、39 升中 23 升で不一致になる(`mutant (no int truncation): cells differing 23 / 39`)。

### k1a-c-08 [注記] 射程外で目に入ったもの
`PERFORMANCE.md` §3 の本文には「1 分足の『時間の記録がある升』が 19/38」とあるが、同じ節の表には「39 升 / 20」とある。

## INTENT_MAP の ○ の抜き取り(10 項。すべて実装と規則の文が合った)

| 項 | 規則の文 | 実装 | 結果 |
|---|---|---|---|
| S-3 | 1.3 `int(top) > int(under)` → 売り(w = top, lc = h)、逆 → 買い、同値 → 無し | `k1_wick.py:77-82` | 合う。k1a-c-07 の差し替えでも効いていることを確かめた |
| S-5 | 小門 = `s != off` かつ (`s` 無し または `wbp ≥ s`) かつ `w > |candle|` | `k1_wick.py:85` | 合う |
| S-6 | 大門 = `b` あり かつ `wbp ≥ b` | `k1_wick.py:86` | 合う |
| P-2・P-3 | 1.4 行動対象でない足: 足の色が建玉と反対のときだけ終値と lcline を比べる | `k1_wick.py:140-146` | 合う |
| P-5 | 反対向き → 決済。強いなら同じ足の終値でドテン、弱いなら建て直さない | `k1_wick.py:150-153` | 合う(k1a-c-01 のとおり形は当時の `simulate()` と同じ) |
| P-7 | 建値も決済値も「その足の終値」 | `BarCloseMarketFill`、核の順序(`ordering.py:23-24`「venue acts first (market data, then the requests arriving at that instant…), then deliveries reach the strategy」) | 合う。4 升の全取引で約定値 = その足の終値(k1a-c-06) |
| F-2・F-3 | 1.2 始値 = 最初の `o`、高値 = 最大、安値 = 最小、終値 = 最後の `c`、約定の無い区間は足を作らない | `bars.py:102-116` | 合う |
| D-4 | 2020〜2021 は 1 行も読まない | k1a-c-02 | 合う |
| D-6 | `c ≤ 0` の足は飛ばす(当時) | `events.py:266-269` `_positive` | データ層が拒むので、分岐自体が起きない。合う |
| T-2 | 保有本数の中央値 | `k1_newenv_tables.py` `idx[exit] − idx[entry]`、`sorted(holds)[n // 2]` | 合う(4 升で 2 つ目の計算と一致) |

**裁きが規則の文に立つか**: 違いのあった升が 0 なので、「環境の欠陥・当時の誤り・不明」の裁きは 1 件も無い。「一致」を正しさの根拠に使っていない点は `DIFF.md` §0・§3 で守られている。§3 の「確かめていないもの」(約定の模型の項目 2・費用・口座・検証の部品は通っていない)も事実どおりである(`record.json: components.models.fill_model = bot.strategy.k1_wick.BarCloseMarketFill`)。

## 核とパイプラインの差分(統合)
```
$ git diff --stat 457dcef4~1 HEAD -- src/bot/bt/pipeline.py src/bot/bt/core/     → 差分なし
$ git diff --stat 457dcef4~1 HEAD -- src/bot/bt                                  → vector/__init__.py 5 行・vector/bars.py +39 行だけ
CORE_VERSION = "core-19"(src/bot/bt/core/contract.py:15)
```
u1_range_center.py と test_i4_module_strategy.py は存在しない(E-5 のとおり)。

## 回した試験(私有の basetemp)
```
PYTHONPATH=src python -m pytest tests/test_k1_wick.py tests/bt/item_1/test_i1_bars_from_bars.py tests/bt/item_4 tests/bt/critic/item_4 --basetemp=/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/pt_k1a_critic -p no:cacheprovider
```
末尾の行: `1472 passed, 2 skipped in 1076.02s (0:17:56)`(終了コード 0)

```
PYTHONPATH=src python -m pytest tests/test_k1_wick_critic.py -p no:cacheprovider --basetemp=/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/pt_k1a_critic2
117 passed in 10.03s
```

## まとめ
[止める] 0 件、[直す] 3 件(k1a-c-01・k1a-c-03・k1a-c-04)、[注記] 5 件(k1a-c-02・05・06・07・08)。

## 読めなかった範囲
- 画面(`dashboard/*.png`・`CHECK.md`)と `PERFORMANCE.md` の数は射程外として読んでいない(k1a-c-08 は目に入った 1 点だけ)。
- 234 升のうち、2 つ目の計算で突き合わせたのは 4 升だけ。残りの 230 升は、表の生成側のコードを読んだうえで `diff_table.md` の比較に頼った。
- `k1_newenv_diff.py: parse_old` が当時の表を正しく読んでいるかは、表 2.1 の `s19/b24` の行と k1a-c-06 の 4 升だけで確かめた。
- `tests/bt/critic` と `tests/bt/battery` の全体(作業者が回した範囲)は回していない。指定の 4 つだけを回した。
- ENV_DEFECTS の E-1・E-6・E-8・E-9・E-12 は、場所の突き合わせだけで、再現はしていない。
