# K1 段階 A — 環境の欠陥の直しの批評(第 1 回・第 2 回を合わせて、批評家 1 回)

- 委任文: `docs/DATA/delegations/20260927_k1_env_fixes.md`(§3 の批評家、§4 第 2 回)。作業者の記録 `docs/PHASE2/K1/NEWENV_A/FIXES.md`、返り値とリードの処置 `docs/AUDITOR/VERDICTS/2026-09-27_k1_env_fixes.md`。
- 委任文 §3 の批評家の射程(逐語): 「**射程 = 直しが根本か・試験が直しを外すと落ちるか・読んではいけないデータを読んでいないか**」。オーナー逐語(L-476)「**そこで出る欠陥を直す**」。
- 終わる条件と上限: リードの指示どおり 1 回、上限 2 時間(00:21 → 02:20 UTC)。00:18 に始め、00:5x に書き終えた。上限には達していない。
- 見た差分: 指示の範囲 `git diff 5f0342d4~3 00508e9c` の起点 `5f0342d4~3` は `bf44529a`(第 1 回の途中の WIP)で、それより前の第 1 回の変更(`stream.py` の新設、`venue.py`・`rules.py`・`bootstrap.py`・`backtest_view.py` など)が入らない。そのため `git diff bf44529a~1 00508e9c -- src scripts tests`(34 ファイル、+2153/−283)を読んだ。
- 守ったこと: `src/` は直していない。git commit / push はしていない。フック・`.claude/` は触っていない。試験を 1 本足した(§5)。変異はリポジトリの外の写し(スクラッチパッドに `src`・`tests/bt` などを写して git にしたもの)に当てた。重いプロセスは同時に最大 2 本。読んだデータは合成データだけ(下の全体の試験は門の下で回した)。
- ディスク: 全体の試験の実行中に空きが 100 MB まで減った(`df -h /` の出力「252G 37G 100M 100% /」)。basetemp を消して 668 MB に戻した。

## 1. 全体の試験をデータの門の下で(射程 3)

コマンド(00:19〜00:43 UTC。`critic_nodeid` はこの批評家の私有の pytest 部品で、門が止める `open` を、そのときの試験 id と一緒に記録するだけ。門より先に読み込むので、門が例外を出す前に記録できる。止める・通すは門だけが決める):

```
PYTHONPATH=<scratch>/critic:scripts:src K1FIX_DATAGATE_LOG=<scratch>/critic/refused.log CRITIC_NODEID_LOG=<scratch>/critic/refused_nodeid.log python -m pytest -p critic_nodeid -p k1_newenv_fix_datagate -p no:cacheprovider --basetemp=<scratch>/critic/bt -rfE
```

- 末尾の行(逐語): 「**93 failed, 20642 passed, 10 skipped, 3 warnings, 37 errors in 1353.39s (0:22:33)**」
- 門が止めた `open`: **98 件**(`refused.log` の行数 98、`refused_nodeid.log` も 98)。**`tests/bt` と `tests/test_k1_wick*.py` は 0 件**。98 件はすべて `tests/bt` の外の 19 ファイル。
- 失敗・エラー 130 件(試験 id の重複を除く)はすべて門による: 128 件は本文が `PermissionError: k1fix datagate: ...`。残る 2 件(`tests/test_etf_measure.py::test_40b_...`・`test_40c_...`)は、読む関数が `OSError` を飲み込んで空を返したための失敗(下の 1.2)。止めた試験 id 98 個と、失敗・エラーの試験 id 130 個の差 32 個は、同じモジュールの fixture の失敗が後の試験に及んだもの(`comm` の出力で、止めた id で失敗していないものは 0)。
- `tests/bt` の中の失敗・エラーは 0 件(`grep -c "tests/bt\|test_k1_wick" failed_ids.txt` → 0)。

### 1.1 ファイルごと(止めた回数、`[封印]` は 8 つの `SEALED.json` のどれかに載っているもの)

| 回数 | ファイル |
|---|---|
| 15 | `backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv` |
| 8 | `backtest_data/o3c_signal_continue_20260920/rows_continue.csv.gz` |
| 5 | `backtest_data/o3c_reaction_20260918_full/OPENED.txt` |
| 5 | `backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP/BTCUSD_PERP-liquidationSnapshot-2023-06-25.zip` |
| 4 | `backtest_data/o3c_signal_value_20260921/spread/spread_by_day.csv` |
| 4 | `backtest_data/o3c_signal_explore5_20260920/rows_prints.csv.gz` |
| 4 | `backtest_data/n225f_225labo_20260828/full_day_daily.csv.gz` **[封印 P2-04]** |
| 4 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2017.csv.gz` **[封印 P2-08]** |
| 3 | `backtest_data/o3c_reaction_20260918_sample/gap60_w8/table.csv` |
| 18 | `backtest_data/qa_known_answer_maker4_r2_20260905/micro/ticker_{a..i}.csv`(9 本、合計) |
| 2 | `backtest_data/o3c_signal_materials_20260920/rows_materials.csv.gz` |
| 2 | `backtest_data/o3c_signal_explore2_20260919/e1_delta.csv` |
| 2 | `backtest_data/jpx_etf_daily_20260906_topix_alt/1348.T.json` |
| 2 | `backtest_data/jpx_etf_daily_20260906_topix_alt/1348.T.csv` **[封印 P2-03b]** |
| 1 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2021.csv.gz` **[封印]** |
| 1 | `backtest_data/phase2_runs/P2-04/iter0_20260906/train_val.csv` |
| 19 | `backtest_data/o3c_signal_value_20260921/stage{1,2}_*/…`・`o3c_signal_policy_20260920/…`・`o3c_signal_materials_20260920/tables.md`・`o3c_signal_explore{3,5}_…`・`o3c_signal_continue_20260920/jev/selection_manifest.json`・`o3c_reaction_20260918_sample/gap60_w8/summary.json`(各 1 回) |

`paper_logs/` と BitMEX 2020〜2021 への `open` は 0 件。

### 1.2 試験ファイルごと(止めた回数)と、何を読もうとしたか(直していない)

| 回数 | 試験ファイル | 読もうとしたもの |
|---|---|---|
| 21 | `tests/test_o3c_signal_value.py` | O3C の研究の出力(`o3c_signal_value_20260921` の段 1・段 2 の表・要約、`o3c_signal_continue_20260920/rows_continue.csv.gz`、`o3c_signal_materials_…/rows_materials.csv.gz`、`o3c_signal_policy_…/cascades.csv.gz`) |
| 18 | `tests/test_qa_maker_fill_ref.py` | QA の既知解パケット `qa_known_answer_maker4_r2_20260905/micro/ticker_*.csv`(合成) |
| 11 | `tests/test_o3c_reaction.py` | `o3c_reaction_20260918_full/OPENED.txt`、`…_sample/gap60_w8/{table.csv,summary.json}`、Binance CM の清算スナップショット(2023-06-25 の zip) |
| 7 | `tests/test_o3c_signal_explore5.py` | `o3c_reaction_20260918_full/gap60_w8/table.csv`、清算 zip、`o3c_signal_explore5_…/summary.json` |
| 6 | `tests/test_o3c_signal_policy.py` | `o3c_signal_policy_20260920` の段 1・段 2、`o3c_signal_continue_…` |
| 5 | `tests/test_phase2_p2_04.py` | **`n225f_225labo_20260828/full_day_daily.csv.gz`[封印 P2-04](4 回)**、`phase2_runs/P2-04/iter0_20260906/train_val.csv` |
| 5 | `tests/test_o3c_signal_explore2.py` | `o3c_reaction_20260918_full/gap60_w8/table.csv`、`o3c_signal_explore2_…/e1_delta.csv` |
| 4 | `tests/test_o3c_signal_explore4.py` | 同上の table.csv、`o3c_signal_explore3_…/f2_retrace.csv` |
| 4 | `tests/test_k1_bitflyer_source.py` | **`bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2017.csv.gz`[封印 P2-08]** |
| 3 | `tests/test_o3c_signal_explore3.py` | table.csv、`e1_delta.csv` |
| 3 | `tests/test_o3c_signal_continue.py` | `o3c_signal_explore5_…/rows_prints.csv.gz` |
| 2 | `tests/test_phase2_p2_03_iter2.py` | **`jpx_etf_daily_20260906_topix_alt/1348.T.csv`[封印 P2-03b]** |
| 2 | `tests/test_o3c_signal_materials.py` | `o3c_signal_materials_…/tables.md`、`rows_prints.csv.gz` |
| 2 | `tests/test_etf_measure.py` | `jpx_etf_daily_20260906_topix_alt/1348.T.json`(配当のスナップショット) |
| 1 | `tests/test_xborder_p2_fast.py` | **`bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2021.csv.gz`[封印]** |
| 1 | `tests/test_o3c_signal_stage2.py` | `rows_materials.csv.gz` |
| 1 | `tests/test_o3c_reaction_r2.py` | `o3c_reaction_20260918_full/gap60_w8/table.csv` |
| 1 | `tests/test_o3c_reaction_judge.py` | `o3c_reaction_20260918_sample/gap60_w8/table.csv` |
| 1 | `tests/test_audit_gates_wired.py` | 同上 |

試験 id ごとの全行は `<scratch>/critic/refused_nodeid.log`(98 行、試験 id と real path のタブ区切り)。

### 1.3 子プロセスの中の読み(門の射程の外を測った追加の回)

門は Python の監査フックなので、その pytest のプロセスの中の `open` しか見えない。試験が `subprocess` で起こす子の Python には掛からない(作業者の「止めた `open` 0 件」も同じ射程)。そこで、試験のうち子プロセスを起こす 26 ファイル(`git grep -l "subprocess\.\(run\|Popen\|check_output\|check_call\)\|os\.system" -- 'tests/*.py' 'tests/**/*.py'` のうち `test_*.py`)を、門を子にも入れる私有の `sitecustomize.py`(`<scratch>/critic/sitegate/`、子の Python も起動時に門を読み込む)の下で回した。子に門が入ることは別に確かめた(子の出力「child gate True」と、子の `open` が門の `PermissionError` で止まること)。

- 末尾の行(逐語): 「13 failed, 2477 passed, 2 warnings in 260.63s (0:04:20)」
- 止めた `open` 13 件はすべて親の pytest のプロセス(記録の argv が 13 件とも `pytest/__main__.py …`)。**子プロセスで止めた `open` は 0 件**。13 件の内訳は 1.2 の `tests/test_o3c_reaction*.py`・`tests/test_audit_gates_wired.py` と同じファイル。
- 射程: 環境変数を引き継がない子(`env=` で渡し直すもの)と、Python 以外の読み(C の拡張・外部コマンド)は測っていない。

## 2. 指摘

### [直す] C-1 統合の口の起源の証拠の探索が「パスで名指しの封印を開かない」ことを確かめる試験が無い((d)1 × (d)2)

- 場所: `src/bot/bt/pipeline.py:338`(`_market_candidates` の `if seals.by_path(real) is not None:` = 封印のファイルの先頭行を読まずに候補に残す)と `src/bot/bt/pipeline.py:373`(`_bounds` の `seals.read_checked(real, rel, None)` = 封印を開く前に拒む)。
- どちらの守りも、外しても既存の試験は 1 件も落ちない。変異(リポジトリの外の写しで、関係する 11 ファイル = `test_i1_fix_seal_read_before_refuse.py`・`test_i1_fix_stream.py`・`test_i1_seal_grid.py`・`test_i2_fix_last_bar_close.py`・`test_i3_fix_day_block_bootstrap.py`・`test_i3_fix_currency.py`・`test_i4_fix_k1_module.py`・`test_i4_r2_origin_from_data_grid.py`・`test_i4_r3_origin_by_rows_grid.py`・`tests/test_k1_wick.py`・`tests/test_k1_wick_critic.py` を `-x` で回した。出力の逐語):
  - 「X2_candidates_open_path_sealed: exit 0」(338 行を `if False:` に)
  - 「X3_bounds_plain_open: exit 0」(373 行を `open(real, 'rb').read()` に)
- 作業者の `test_the_integrated_run_does_not_read_a_sealed_file_to_hash_it` は、実行のデータそのものを封印にしているので、データ層の読みで先に拒まれ、証拠の探索まで届かない。封印のファイルが `source` に宣言された場合(実行のデータは封印の外)を見る試験が無い。
- **批評家が足した試験**: `tests/bt/critic/item_1/test_k1fix_r2_evidence_does_not_open_a_sealed_source.py`(1 件、合成データだけ)。実行のデータは封印の境より前の 2 行だけのファイル、`source` に封印のファイルを宣言し、計画の段で封印のファイルが 1 度も開かれないこと、証拠が `sealed_skipped = [封印のファイル]`・`by: rows` になることを見る。いまのコードで「1 passed in 0.35s」、X2 で「1 failed in 0.36s」、X3 で「1 failed in 0.38s」。データの門の下で `test_i1_fix_seal_read_before_refuse.py` と合わせて「11 passed in 0.40s」、門が止めた `open` 0 件(記録ファイルが作られなかった)。直しは、この試験を入れること(コミットはリード)。

### [直す] C-2 批評家の試験 `test_i4r2_origin_survives_reencoding.py` は拒否の理由を名指ししていない(差し替えで残った)

- 場所: `tests/bt/critic/item_4/test_i4r2_origin_survives_reencoding.py:82`(`with pytest.raises(ValueError):`、`match=` なし)。
- 確かめ: 写しの `pipeline.py:709` の起源の規則(`_need(d["origin"] in ORIGINS, …)`)を `_need(True, …)` にすると、この試験の 6 件は通ったまま、同じ規則を見る `test_i4r1_origin_is_not_a_self_label.py` の 3 件は落ちる(出力の逐語「3 failed, 6 passed in 0.26s」、落ちたのは i4r1 の 3 件)。宣言の `instruments` が `{name, price, with}` だけで `product`・`rules` を欠くため、起源の規則が無くても「instruments[0] must be {name, price, with, product, rules}」で `ValueError` になる(批評家の再現の出力。`origin: "real"` にしても全件この理由で拒まれる)。
- 試験の差し替えで新たに落ちた性質ではない(差し替えの前も同じ宣言の形)。ただし作業者は同じ理由(§11.7-7「合成の環境に替えたので、拒否が別の理由で起きても通ってしまわないように」)で i4r1 と prereg の 2 本に `match=` を足しており、このファイルだけ残っている。直し: `match="origin"` を足す。

### [注記] C-3 門の規則 I-6 の「先送りした証拠金の検査をその場でやり直す」分岐は試験されていない

- 場所: `src/bot/bt/pipeline.py:900-903`。変異 X6(この分岐を外す)は 11 ファイルの試験を全部通った(「X6_I6_no_account_recheck: exit 0」)。
- 影響の範囲(コードを読んだ推定): 口座は会場の処理の中で、会場のすぐあとに足を受け(`src/bot/bt/core/engine.py:1212-1222`)、戦略への配信は会場のあと(I-6 の docstring `pipeline.py:822-825` と K1 の前提)なので、足を受けて出した注文は先送りにならない。先送りは最初の足より前の注文だけで、その場合は分岐があっても無くても約定しない(分岐あり = 口座の `Reject`、無し = 会場の `Canceled no_price_yet`)。違うのは取消の理由の文字だけと読める。測ってはいない。

### [注記] C-4 写しの見分けは「同じデータの根」の中だけ

- `SealRegistry(root)` は渡された `root` の下の `backtest_data/phase2_sealed/` だけを読む(`allowlist.py:172`、`loader.py:512`)。合成で確かめた: 根 A に封印のファイルと台帳、同じ bytes の写しを根 A と根 B(台帳なし)に置き、`load` した出力「root A refused: SealedRangeError」「root B copy loaded rows: 3 [1577836800000000000]」(根 B では封印の境 2020-01-01 の行まで読まれる)。
- 第 2 回の前からの設計で、この直しが作ったものではない。モジュールの docstring(`allowlist.py:29-48`)は「別名の写しは bytes で見分ける」と書くが、「別の根に置いた写しは見分けない」とは書いていない。リポジトリの外の一時の根で実行する試験・script では台帳が効かない。

### [注記] C-5 大きさで絞る経路は、封印のファイルが変わっていなくても封印のファイルを開く

- `allowlist.py:247`(`copy_of` の `for cand in self._by_size.get(len(raw), ())`): md5 が台帳のどれとも違い、大きさが今の封印のファイルと同じなら、そのファイルが写しでなくても封印のファイルを開いて sha256 を取る(行には解かない)。`copy_of` の docstring「only for a sealed file of the same size now whose record digest differs」は、封印のファイルの中身が変わったかをコードが知っているように読めるが、コードは知らずに読む。FIXES.md §11.1 の書き方(「大きさが今の封印のファイルと同じときだけ」)はコードと合っている。

### [注記] C-6 パスで名指しの封印のファイルを境より前の範囲で読むと、境より後の行も解読してから捨てる

- `loader.py:474-475`: 全行を `_build` してから `_in_range` で捨てる。封印の区間の行は戦略にも記録にも渡らない(行ごとの封印の検査も残っている)。第 2 回の前からの形で、委任文 (d)1 の「読む量を最小にする」は写しの見分けについての指示と読める。

### [注記] C-7 試験の差し替えで落ちた・弱まった性質(射程 2)

1. `test_i4_real_data_smoke.py`: FX のイベントティック・TOPIX 先物 1 分足・USD/JPY 1 分足が合成になり、**この環境の実物の FX・JPX ファイルの形式が読めること**は確かめなくなった(作業者・リードとも記録済み)。
2. 同じ試験の bitFlyer: 一日分から 00:00〜05:59 UTC に切った。理由は板のファイルの 18 時台に ask 0.0 の行があり、データ層が板として拒むため。**実データの中の 1 行の異常な板で、データ層がそのファイル全体を拒むこと**を、この試験は避けて通るようになった(その扱いが正しいかはこの批評の射程の外)。
3. `test_i2_real_data_check.py`: 板の段数 10 → 5。不変条件が最良の段と約定だけを使う、という作業者の説明は確かめていない。
4. 起源の格子: **出所を宣言しない写しを、置き場のどこにあっても行で見つける**性質は無くなり、`source` の宣言が要るようになった。委任文 (d)2「実行に渡したデータ(とその出所として宣言されたもの)だけを見る」による設計の変更で、試験の不備ではない。なお起源の規則そのもの(ファイルは常に real)は証拠に依らないので、価格の規則の拒否は変わらない。
5. qa_* の除外の試験: 前はリポジトリの qa ファイル(無ければ skip)、いまは合成の環境の qa ファイル。性質は同じ。

### [注記] C-8 第 2 回のあと、D-2 の流し読みの畳み(byte の比べ)は打ち直されていない

作業者の記録(FIXES.md §11.8-2)のとおり。第 2 回で `_read_file` が `read_checked` を通るようになった(全ファイルの md5 を取る)。封印の外のファイルでは行は変わらないとコードからは読めるが、測っていない。

### [注記] C-9 `tests/bt` の外の試験が、普段の全体の試験(`PYTHONPATH=src python -m pytest`)で封印の台帳に載ったファイルを開く

1.2 の **[封印]** の 4 ファイル(P2-04・P2-08・P2-03b ほか)を、`tests/test_phase2_p2_04.py`・`tests/test_k1_bitflyer_source.py`・`tests/test_phase2_p2_03_iter2.py`・`tests/test_xborder_p2_fast.py` が門なしの実行では直接開く(データ層を通らない)。この委任の外なので直していない。リードの処置(VERDICTS 00:20「これまでの試験の実行が … 開いていた可能性」)の材料。

### [注記] C-10 `tests/test_etf_measure.py` の 2 件の失敗が示す、読めない配当スナップショットの扱い

`src/bot/jpx/etf_auction_executor.py:209-216` の `ex_dates_from_yahoo_snapshot` は、ファイルが無い・読めない(`OSError`)と空の集合を返す。門で読めなくしたところ、権利落ちの前夜に「skip」のはずの判断が「ordered」になった(`AssertionError: assert 'ordered' == 'skip'`)。この委任の外。ON1 系の発注の判断に効く箇所なので、リードに知らせるだけにする。

### [注記] C-11 細かい点

- `src/bot/bt/compat/metrics.py` に `total_pnl_jpy` が残る(旧形の互換の口。委任文 (d)5 の名指しは統合の口の指標の鍵なので、範囲の外と読める)。
- `pipeline.py:1210` の `drawdown.pct_note`「銘柄ごとの通貨の額を足しているため」は、新しい `pnl.note`「どの銘柄の建値通貨も口座の通貨と同じ」と言い方が食い違う。

## 3. 項目ごとの見立て(射程 1)

| 項目 | 根本で直っているか | 外すと落ちる試験 | 根拠 |
|---|---|---|---|
| D-1 `last_bar_close` | 直っている。規則の値(`rules.py:46`)・会場の値付け(`venue.py:290, 566`)・門の I-6(`pipeline.py:897-904`)・計画の段の拒否(`pipeline.py:748-750`)。`BarCloseMarketFill` は消えた(`git grep -ln BarCloseMarketFill` → `k1_wick.py`(docstring)と、消えたことを見る試験だけ)。`BarEvent` の時刻は足の終わり(`core/events.py:262`)なので先読みにはならない | あり(X7「FAILED …test_last_bar_close_only_for_a_bar_instrument」、作業者の M1・M2)。I-6 の証拠金の分岐は無し(C-3)。会場で足の終値を覚える順(`_on_bar` の前か後か)を入れ替える変異 X13 は落ちないが、`_on_bar` は `market_ref` で値を付けないので同じ動きになる変異(差が出ない) | 変異の出力 §4 |
| D-2 流し読み | 直っている。ファイルをまたぐ検査は「後のファイルの行はすべて前より後」で置き換え、破れば拒む(`stream.py`)。24x5 は `load` でも穴の検査をしない(`anomalies.py:30-31`)ので食い違いではない | あり(X4「FAILED …test_overlapping_files_are_refused」、X11「FAILED …test_24x7_grid_is_checked_across_files」) | C-8 |
| D-3 日ブロック | 直っている | あり(X5「FAILED …test_matches_the_oracle_on_uneven_days」) | — |
| D-4・(d)5 通貨・鍵 | 直っている(runner と統合の口の記録、画面) | あり(X8「FAILED …test_jpy_and_integrated_records」、作業者の M6) | C-11 |
| (d)1 開く前に拒む・写し | パスで名指しは開く前に拒む。データ層の口は `read_checked` 1 つで、`loader`・`stream`・`sealed_access`・`runner` の計画・統合の口の計画と証拠が通る(`src/bot/bt` の `open(` を grep し、ほかにデータを開く箇所が無いことを見た) | データ層・runner・`read_table` はあり(X1「FAILED …test_a_byte_copy_is_refused_undecoded_without_opening_the_sealed_file」、X10「FAILED …test_read_table_uses_the_same_door」、作業者の M1〜M4)。統合の口の証拠は無かった → C-1 で足した | C-1, C-4, C-5, C-6 |
| (d)2 探索を絞る | 直っている(`os.walk` は無くなった。`pipeline.py` に `os.walk`・`glob` は 0 件) | あり(X12「FAILED …test_origin_is_decided_from_the_data[copy_backtest_data-fx_ticks-real-schedule-動作確認]」、作業者の M5・M8) | C-7-4 |
| (d)3 試験の差し替え | `tests/bt` は門の下で止めた `open` 0 件(§1) | 変異ではなく門で確かめるもの | C-2, C-7 |

## 4. 変異の確かめ(批評家が当てたもの)

写し(`<scratch>/critic/mut`、`src`・`tests/bt`・`tests/test_k1_wick*.py`・`tests/conftest.py`・`pyproject.toml`・門を写して git にしたもの)に 1 つずつ当て、§2 C-1 の 11 ファイルを `-x` で回した(`<scratch>/critic/mutate_critic.py`)。出力(逐語、最初に落ちた試験):

```
X0_control: exit 0
X1_copy_md5_lookup_off: exit 1 | FAILED tests/bt/item_1/test_i1_fix_seal_read_before_refuse.py::test_a_byte_copy_is_refused_undecoded_without_opening_the_sealed_file
X2_candidates_open_path_sealed: exit 0
X3_bounds_plain_open: exit 0
X4_stream_equal_time_across_files: exit 1 | FAILED tests/bt/item_1/test_i1_fix_stream.py::test_overlapping_files_are_refused
X5_bootstrap_mean_of_day_means: exit 1 | FAILED tests/bt/item_3/test_i3_fix_day_block_bootstrap.py::test_matches_the_oracle_on_uneven_days
X6_I6_no_account_recheck: exit 0
X7_plan_allows_last_bar_close_on_non_bar: exit 1 | FAILED tests/bt/item_4/test_i4_fix_k1_module.py::test_last_bar_close_only_for_a_bar_instrument
X8_view_no_account_currency_fallback: exit 1 | FAILED tests/bt/item_3/test_i3_fix_currency.py::test_jpy_and_integrated_records
X10_read_table_opens_first: exit 1 | FAILED tests/bt/item_1/test_i1_fix_seal_read_before_refuse.py::test_read_table_uses_the_same_door
X11_stream_no_border_gap: exit 1 | FAILED tests/bt/item_1/test_i1_fix_stream.py::test_24x7_grid_is_checked_across_files
X12_evidence_ignores_declared_source: exit 1 | FAILED tests/bt/item_4/test_i4_r2_origin_from_data_grid.py::test_origin_is_decided_from_the_data[copy_backtest_data-fx_ticks-real-schedule-動作確認]
X13_venue_close_before_bar_fills: exit 0
```

X1 = 写しを台帳の md5 で見ない(大きさの経路だけ残す)/ X2・X3 = C-1 / X4 = ファイルの境で同じ時刻を許す / X5 = 日の平均の平均にする / X6 = C-3 / X7 = 足以外の銘柄に `last_bar_close` を許す / X8 = 統合の口の記録の口座の通貨を読まない / X10 = `read_table` が先に開く / X11 = ファイルの境の穴を出さない / X12 = 宣言の `source` を探さない / X13 = 足の終値を `_on_bar` の前に覚える(差が出ない変異、§3)。

## 5. 統合(射程 4)

- `CORE_VERSION` は `core-19` のまま(`src/bot/bt/core/contract.py:15`)。`git diff --stat bf44529a~1 00508e9c -- src/bot/bt/core tests/bt/battery 'tests/bt/**/scenes*' '**/stated_rules*' docs/PHASE2/K1/PREREG.md docs/PHASE2/K1/RESULT.md '**/DEFINITIONS.md'` の出力は空。`src/bot/bt/core` の最後の変更 `5e0c26d8` は `bf44529a~1` の祖先(`git merge-base --is-ancestor` が真)。
- 規則の値の追加は `src/bot/bt/orders/rules.py`(`market_ref` に `last_bar_close`)だけで、委任文 D-1 の指示どおり。場面集の規則の文・K1 の規則の文(PREREG・RESULT)は変わっていない。
- 足した・変えたファイル(この批評): `tests/bt/critic/item_1/test_k1fix_r2_evidence_does_not_open_a_sealed_source.py`(新規)とこの `CRITIC_FIXES.md`。ほかは触っていない。

## 6. 数

**[止める] 0 件、[直す] 2 件**(C-1、C-2)。[注記] 9 件(C-3〜C-11)。
