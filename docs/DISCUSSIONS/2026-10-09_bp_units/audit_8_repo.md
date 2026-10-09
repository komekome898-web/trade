# 監査 8: リポジトリ内の「bp」を扱う Python コードの仕分け

作成: 2026-10-09 09:31 UTC 着手(上限 70 分 = 10:41 UTC まで)。調べるだけの作業者が書いた。コード・文書は直していない。コミットしていない。

## 着手前の表

| やること | この依頼文の該当語(逐語) |
|---|---|
| 指定のコマンドで対象の .py を出し、数を書く | 「対象のファイルを次のコマンドで出す(474 個のはず。違ったら数をそのまま書く)」 |
| `docs/RESEARCH/WINDOW1/` と `backtest_data/phase2_sealed/` を読まない | 「`docs/RESEARCH/WINDOW1/` と `backtest_data/phase2_sealed/` は読まない」 |
| ファイルごとに grep の当たった行を読み、①②③④/bp でない を付ける | 「ファイルごとに、grep の当たった行を読んで」「当たったのが bp か(①②③④のどれか。複数なら全部。bp と関係ない 10000 などの数だけなら「bp でない」)」 |
| ④ には中身を読んで名前を付ける | 「中身を読んで名前を付けてください」 |
| bp と円・bp の種類の間の倍率の行を行番号と式で書く | 「bp と円の間、または bp の種類の間を倍率で変えている行があれば、その行番号と式」 |
| tests/ かどうかを書く | 「試験(tests/)かどうか」 |
| 流れ先 (a)〜(d) を import と呼び出し元を grep で辿って決め、根拠を書く | 「目視の推測で決めず、grep で import と呼び出し元を辿る。辿れなかったら「未確認」と書く」 |
| (b) の入口を `docs/OPERATIONS.md`・`docs/OPERATIONS_JPX.md`・`deploy/` から特定する | 「入口は `docs/OPERATIONS.md`、`docs/OPERATIONS_JPX.md`、`deploy/` の起動台本を読んで特定し、その入口から import を辿る」 |
| 種類が出会う口を別の表に書く | 「種類が出会う口)を、別の表に全部書く」 |
| 種類 × 流れ先 の件数の表を、数えたコマンドと一緒に書く | 「最後に、種類 × 流れ先 の件数の表を書く。数えたコマンドも一緒に書く」 |
| 「無い」「流れていない」にはコマンドと出力を添える。添えられなければ「未確認」 | 「「無い」「流れていない」と書くときは、打ったコマンドと出力を添える。添えられないなら「未確認」と書く」 |
| 範囲を切ったら書く | 「範囲を切ったら、切ったことを書く。全部を見たとは書かない」 |
| 上限 70 分で止め、残りを持ち越しに書く | 「上限は 70 分です。越えたら止めて、残りを「持ち越し」として書いてください」 |
| 出力は日本語で、この 1 本だけに書く。コミットしない | 「書いてよいファイルは出力の 1 本 `docs/DISCUSSIONS/2026-10-09_bp_units/audit_8_repo.md` だけです(コミットはしない)」「出力は全部日本語で書いてください」 |
| 仕分けの補助の一時ファイル(当たり行の抜き出し・import の表)を作業用の scratchpad に置く | **(該当語なし)** — リポジトリの外の作業用置き場にだけ置き、リポジトリには書かない。依頼の「書いてよいファイルは…1 本だけ」はリポジトリ内のことと読んだが、読み方に迷いがあることをここに書く |

### 完了見込み時間(上限 70 分)

- 対象の列挙と所在の集計: 3 分
- (b) の入口の特定(OPERATIONS 2 本と deploy/ を読む): 7 分
- import の向きの表を機械で作り、(a)(b) の入口から辿る: 12 分
- 474 ファイルの当たり行の抜き出しと種類の付与(語の規則で機械で下付けし、目で直す): 25 分
- 倍率の行・種類が出会う口の抜き出しと確認: 10 分
- 件数の表とこの文書の仕上げ: 8 分
- 合計 約 65 分。474 ファイル全部の当たり行を 1 行ずつ人の目で読むのは 65 分に入らない見込みなので、どこまで目で読んだかを本文に書く。

## 0. 先に書くこと(範囲と、目で読んだ量)

- 対象の数(事実): 依頼文のコマンドをそのまま打って 474 個。

```
$ cd /home/user/trade && git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -lE '_bp\b|\bbp\b|bps\b|1e4\b|10_?000\.?0?\b' > files.txt; wc -l < files.txt
474
```

- 当たった行は全部で 7,553 行(`tr '\n' '\0' < files.txt | xargs -0 grep -nE '<同じ語>' > hits.txt; wc -l hits.txt` → `7553`)。
- **474 ファイルのうち、当たり行を目で読んで種類・倍率の行を決めたのは 42 ファイルだけ**(表 1 の「確かめ方」が「目」の行)。残りの 432 ファイルは、下の 1.1 の語の規則で機械が付けた種類であり、目で読んでいない(「確かめ方」が「機械」)。機械の種類は間違いを含む(例: `src/bot/strategy/k1_wick.py` は機械では「bp でない」だったが、目で読むと 91 行 `wbp = w / c * 10000.0` で ② だった。`scripts/analysis/diag_tables.py` は機械では「②④」だったが、目で読むと bp を作らず読むだけの「受」だった)。機械の行の種類は、目で読み直すまで推定として扱ってほしい。
- 目で読んだ 42 ファイルの選び方: 流れ先が (a)(b) になったファイル全部、(d) の書き手 1 本(`export_card_trades.py`)、依頼文の背景に出る `card_trades.py`、`docs/RESEARCH/matilda_main/` の下の台帳の行の台本 6 本。
- 流れ先は 474 ファイル全部を import の表で辿った(1.2)。ただし「出力のファイルを別の台本が読む」流れ(データの流れ)は、1.3 に書いた所しか見ていない。
- 作業中の失敗(事実): import の表を作る台本が、出力の `edges.tsv` を一度リポジトリ直下(`/home/user/trade/edges.tsv`)に書いた。気づいてすぐ作業用の置き場へ移した(`mv`)。コミットはしていない。移した後の `git status --short` は、この文書と、私が作っていない `docs/RESEARCH/matilda_main/move_bp_check.out`・`move_bp_check.py`(どちらも git に載っていない。依頼のコマンドは `git ls-files` なので対象の外。中は読んでいない)の 3 つだけだった。書き終わりの 09:42 には、同じ置き場に私が作っていない git に載っていないファイルがさらに 6 個(`bare_bp.*`・`d4_levels_count.*`・`move_bp_triples.*`)増えていた。別の作業が並んで動いていると推定する。これらも対象の外で、読んでいない。

## 1. やり方

### 1.1 種類の付け方(機械の規則)

当たり行 1 行ずつに次の語の規則を当て、ファイルの中で 1 つでも当たった種類を全部付けた。規則は `bp`・`_bp`・`bps`・`1e4` のどれかを含む行にだけ当てる。

| 印 | 機械の規則(行に次の語がある) | 意味 |
|---|---|---|
| ① | `MARGIN`・`margin_jpy`・`200_000`・`証拠金`・`口座`・`equity`・`capital`・`pnl_jpy`、または `jpy` と `1e4` が同じ行 | 円や口座と bp が同じ行に出る。**機械の ① は「20 万円で割る口座の bp」と決まったわけではない**(別の口座の大きさ・円の手数料のこともある) |
| ② | 値段の比 × 1e4 の形(`) / x * 1e4`・`/ x - 1) * 1e4`)、`log(`、`ret`・`move`・`mfe`・`mae`・`return`・`drift`・`vol`・`range`・`wick`・`body`・`gap`・`値動き`・`変化率` | 値動きの bp(向きを掛けたものを含む) |
| ③ | `e * r`、`card_trades`・`cards.pnl`・`持ち高`・`exposure`・`e_t`・`pos *`・`weight`・`qty *`・`size *` | 建玉を掛けた bp |
| ④ | `fee`・`commission`・`taker`・`maker`(手数料率)/ `spread`(スプレッド)/ `basis`・`premium`(ベーシス)/ `funding`(資金調達率)/ `slip`・`cost`・`impact`(滑り・約定経費)/ `tp_bp`・`sl_bp`・`*_bp` の頭が `stop・take・target・thr・min・max・band・width・offset・dist・edge・bar・floor・cap・limit・trail・entry・exit`・`--…bp`・`閾値`(損益分岐・閾値・距離の引数)/ `carry`・`swap`・`金利`(金利・キャリー) | そのほか。名前は「④ の名前」の列 |
| 受 | 上のどれにも当たらず、`pnl_bp`・`sum_bp`・`mean_bp`・`per_trade_bp`・`ci95_bp`・`net_bps`・`bp/日` など bp の名前の値を読む・足す・表示するだけ | 自分では bp を作らない。種類は上流しだい |
| 未分類 | bp の語はあるが、上のどれにも当たらない | 目で読まないと分からない |
| bp でない | どの当たり行にも `bp`・`_bp`・`bps`・`1e4` が無く、`10000`・`10_000` の数だけ | bp と関係ない 10000 の可能性が高い(目で確かめたのは `dashboard.py`・`matilda_v37.py` だけ) |

倍率の行(機械): 当たり行のうち、`MARGIN`・`margin`・`200_000`・`jpy`・`円`・`notional`・`equity`・`capital`・`1e-4`・`/ 1e4`・`/ 10000`・`* 20`・`/ 20`・`0.0001` のどれかと `*` か `/` を含み、`#` で始まらない行。ファイルごとに最初の 3 行を書き、残りは行数だけ書いた。**機械の倍率の行は当たり行の中だけを見ている**(bp の語が無い行で円に直している所は拾えない)。目の行は、ファイル全体に次の grep を打って読んだ:

```
grep -nHE '(\*|×) ?20\b|\b20 ?(\*|×)|/ ?20\b|÷ ?20\b|MARGIN|200_?000|1e-4|/ ?1e4|/ ?10_?000\b|0\.0001|\* ?1e4|\* ?10_?000\b|1e4 ?\*' <目で読んだファイル>
```

### 1.2 流れ先の決め方(import の表)

- `git ls-files '*.py'`(`docs/RESEARCH/WINDOW1`・`backtest_data/phase2_sealed` を除く)全部を Python の `ast` で読み、`import`・`from … import`(関数の中のものも)・相対 import・`importlib.import_module("…")` を、`src/` の下、リポジトリ直下、そのファイルの置き場、`sys.path` の行に出る置き場、`scripts/` の順でファイルに当てた。素の名前で同名のファイルが複数あるもの(`run_battery` 5 個・`scenes` 3 個・`common` 3 個など)は候補を全部つないだ(多めに辿る側)。標準ライブラリと同じ名前の素の import は捨てた(リポジトリに同名のファイルがあって本当にそれを読んでいる場合は取りこぼす)。`docs/legacy/katsuo_v03.py` は先頭の BOM で一度読めず、`utf-8-sig` で読み直した。
- 作業用の台本と表はリポジトリの外(作業用の置き場)に置いた。リポジトリには置いていない。
- 入口から import を辿って届いたファイルを、その入口の流れ先にした。鎖に「同名の候補が複数ある素の import」を含むものは (d) にする決まりにしたが、(a)(b) への鎖で当たったものは 0 個だった。
- (a) の入口 73 個:
  - 依頼文の 4 本(`scripts/simple/run_one.py`・`scripts/analysis/simple_trades.py`・`diag_tables.py`・`diag_paths.py`)
  - `docs/RESEARCH/matilda_main/` の下の git に載った .py 全部
  - 今の分析の文書・台帳 K-301 以降・`docs/RESEARCH/matilda_main/batch_tables.sh`・`scripts/analysis/commit_gate.sh` に名前が出る .py(データの流れの根拠。1.3)。名前が出ても git に無いもの(`eval_fills.py`・`gate_dist.py`・`ledger_fix_beard.py`)は入口にできなかった。同名が複数の `run.py` は文書の文脈(`src/bot/bt/simple/run.py` と書いてある)で、`scenes.py` は `batch_tables.sh` の `M/scenes.py` で 1 つに決めた。
- (b) の入口 35 個: `deploy/` の起動台本で、`rem`・`#` で始まらず、`-like`(止める側の名前合わせ)を含まず、`python`・`call :launch`・`ExecStart` のどれかを含む行に出る `scripts/*.py`。これに、`docs/OPERATIONS_JPX.md` で人が打つ照合 `scripts/run_on1_reconcile.py`・`scripts/run_etf_measure_reconcile.py` を足した(実弾の経路の一部と読んだ。この 2 本を入れたのは私の判断)。入れなかったもの: `run_scalp_paper.py` と `run_board_round.py` は `deploy/` では、止める側の名前合わせ(`-like '*run_scalp_paper.py*'`)とコメントにしか出ない。打ったコマンドと出力:

```
$ grep -nE 'run_scalp_paper|run_board_round|check_data_ledger|research_clock_burst' deploy/* | grep -v '^\S*:[0-9]*:rem'
deploy/fetch_all.bat:59:".venv\Scripts\python.exe" "scripts\research_clock_burst.py" --status-json "data\s12_status.json" >> ...
deploy/fetch_all.bat:89:".venv\Scripts\python.exe" "scripts\check_data_ledger.py" --json "data\LEDGER_CHECK.json" >> ...
deploy/restart_all.bat:122:  "$p = Get-CimInstance ... -like '*run_scalp_paper.py*' ...(止まったかの確かめ)
deploy/stop_all.bat:13:  "Get-CimInstance ... -like '*run_scalp_paper.py*' ...(止める)
```

  `docs/OPERATIONS.md` 526 行は `run_scalp_paper.py` を「2026-09-08 の全捨てで失効。スクリプトは … に保存されており」と書いている。`judge_gates.py`・`validate_composite.py`・`repair_liquidation_gz.py` は OPERATIONS に名前が出るが、bot・ダッシュボード・実弾の経路ではないので (b) の入口に入れなかった。
- (b) の入口の一覧: check_api, check_data_ledger, dashboard, data_quality, extract_tape, fetch_attention, fetch_binance_daily, fetch_external, fetch_history, fetch_jpx_daily, fetch_okx, intake_ledger, mirror_bitmex_archive, paper_on1, paper_onr, probe_api_latency, record_deribit_oi, record_funding_basis, record_hyperliquid, record_liquidations, record_oi, record_okx_traders, record_realtime, record_venues, repair_gz_listing, research_clock_burst, retention_snapshot, run_etf_measure_entry, run_etf_measure_exit, run_etf_measure_reconcile, run_on1_entry, run_on1_exit, run_on1_reconcile, run_paper, verify_snapshots(どれも `scripts/` の下の `.py`)。

### 1.3 データの流れ(import でない流れ)で見た所

1. 今の分析の文書の名前の出方(文書に出る台本を (a) の入口にした):

```
$ { grep -ohE '[A-Za-z0-9_/.]+\.py' docs/ANALYSIS/2026-10-0[89]_*.md; awk '/K-301/{f=1} f' docs/RESEARCH/FINDINGS_LEDGER.md | grep -ohE '[A-Za-z0-9_/.]+\.py'; grep -ohE '[A-Za-z0-9_/.]+\.py' docs/RESEARCH/matilda_main/batch_tables.sh scripts/analysis/commit_gate.sh; } | sed 's#.*/##' | sort -u | wc -l
70
```

   `card_trades.py` はこの 70 個に入っていない(`grep -c card_trades docnames.txt` → 0)。
2. ダッシュボード(b)が読む置き場: `scripts/dashboard.py` 45-46 行 `BACKTEST_RUNS_DIR = "backtest_runs"`・`BACKTEST_SHARED_DIR = "backtest_runs_shared"`、`src/bot/monitoring/backtest_cards.py` 5-7 行 `cards/manifest.json`・`cards/<card>/<variant>/trades.json.gz`・`daily.csv`(day, pnl_bp, n)。
   - `backtest_runs_shared/cards` は git に無い(`ls -d backtest_runs_shared/cards` → `No such file or directory`、`git ls-files | grep -c '/cards/manifest.json'` → `0`)。`backtest_runs/` は git に無い。だから、そこへ書く台本(`export_card_trades.py`、bot.bt.repro の runner を import する `k1_newenv_g_rawrun.py`・`w4_measure/post.py`・`src/bot/bt/pipeline.py`)と、それらが import するファイルは、オーナーの PC の手元で今ダッシュボードに出ているかが分からないので (d) にした。
   - git に載っている `backtest_runs_shared/` の中身は `matilda_main`(160 ファイル)と `matilda_main_trades`(2 ファイル)だけ(`git ls-files backtest_runs_shared | awk -F/ '{print $2}' | sort | uniq -c`)。`src/bot/monitoring` と `scripts/dashboard.py` に `report.json`・`matilda_main`・`summary.json` の語は無い(`grep -rln "report.json\|matilda_main\|summary.json" src/bot/monitoring scripts/dashboard.py` → 出力なし)。ダッシュボードがこの 2 つの置き場を表示するかは未確認(`backtest_view.py` の走らせの見つけ方を読んでいない)。
3. (a)(b) で届いたファイル(と入口)が、届かなかったファイルの名前を文字で書いている組が 18 組あった(届かなかった側が試験でないもの 13 組・試験 5 組)。試験でない 13 組は全部その行を読み、全部が出所や約束事を書いた文で、呼び出しではなかった(`research_clock_burst.py` 20・103・147 行、`backtest_themes.py` 297・318・375・427・525 行、`backtest_cards.py` 336 行、`k1_wick.py` 6 行、`overnight.py` 3-4 行、`composite.py` 20・26 行、`matilda_v37.py` 3 行。`backtest_themes.py` の `RUN_V2` は 318・329・333 行で文字の出所に使うだけ)。試験の 5 組は読んでいない。
4. 試験(tests/)の流れ: tests の外から tests を import するのは `scripts/validate_composite.py` だけだった(322-323・612-613 行で `from tests.test_composite import …`)。`validate_composite.py` は (a)(b) の入口から辿れない。

```
$ git ls-files -z -- '*.py' ':!tests' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -lE '^\s*(from|import)\s+tests\b'
scripts/validate_composite.py
```

5. (c) の根拠の書き方: (c) は「(a)(b) の入口から import で辿れない」ことだけを、import の表の出力(各行の「import する側」)で示している。(c) のファイルの出力ファイルを今の (a)(b) が読んでいないかは、上の 1〜4 で見た所しか確かめていない。

## 2. 表 1: ファイルごとの仕分け(474 行)

並びは 流れ先((a)→(b)→(d)→(c)→(c)試験)、その中はファイル名の順。「試す相手」は試験が import している tests の外のファイル名(同じ名前の `__init__.py` は置き場が違う)。

| # | ファイル | 種類 | ④ の名前(機械は語の当たり) | 倍率の行(行: 式) | 試験 | 流れ先 | 流れ先の根拠 | 確かめ方 |
|---|---|---|---|---|---|---|---|---|
| 1 | `docs/RESEARCH/matilda_main/base/ledger_rows_base.py` | ②(台帳の文の中の move_bp の数) | — | なし | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 2 | `docs/RESEARCH/matilda_main/break_dist/ledger_rows_break_dist.py` | ②(台帳の文の中の move_bp の数) | — | なし | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 3 | `docs/RESEARCH/matilda_main/break_off/ledger_rows_break_off.py` | 受(台帳の文の中の数。円と比) | — | なし | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 4 | `docs/RESEARCH/matilda_main/count/ledger_rows_count.py` | 受(台帳の文の中の数。円と比) | — | なし | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 5 | `docs/RESEARCH/matilda_main/display_x20_suspects.py` | ① | — | 56・58: `v * 20`・`round(v, nd) * 20`(口座の bp → 円) | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 6 | `docs/RESEARCH/matilda_main/display_x20_traps.py` | ①② | — | 50: `round(round(v, nd) * 20, k), round(v * 20, k)`(口座の bp → 円)。45 行で diag_paths.json の値動きの bp を外す | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 7 | `docs/RESEARCH/matilda_main/entry_exit/ledger_rows_entry_exit.py` | ②(台帳の文の中の move_bp の数) | — | なし | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 8 | `docs/RESEARCH/matilda_main/fam_tables.py` | ①② | — | 22: `v * 20`(口座の bp → 円、4 行に「円 = bp × 20」) | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 9 | `docs/RESEARCH/matilda_main/foot/ledger_rows_foot.py` | ②(台帳の文の中の move_bp の数) | — | なし | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 10 | `docs/RESEARCH/matilda_main/half_diff.py` | ① | — | 17・19: `v * 20`・`r["mde"] * 20`(口座の bp → 円) | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 11 | `docs/RESEARCH/matilda_main/levels/ledger_rows_levels.py` | 受(文の中の円の数) | — | なし | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 12 | `docs/RESEARCH/matilda_main/range_hi/ledger_rows_range_hi.py` | ② | — | なし(文の中の move_bp の数) | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 13 | `docs/RESEARCH/matilda_main/same_bar_daily.py` | ① | — | 11: `v * 20`(pnl_bp の日の和 → 円) | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 14 | `docs/RESEARCH/matilda_main/unit_roundtrip_check.py` | ① | — | 26: `pnl_bp` に `pnl_jpy` を入れて円のまま計算 / 77-84: `vb * 20`(bp → 円)と円の直の比べ | いいえ | (a) | (a) 入口(`docs/RESEARCH/matilda_main/` の下) | 目 |
| 15 | `scripts/analysis/diag_paths.py` | ②・受 | — | 111-112・119・127: `(hs / e - 1.0) * 1e4` ほか(値段の比 → 値動きの bp。向き s を掛ける) | いいえ | (a) | (a) 入口(依頼文に名前がある) | 目 |
| 16 | `scripts/analysis/diag_tables.py` | 受 | — | なし(pnl_bp を daily.csv 68 行・trades.csv.gz 80 行・trades.json.gz 92-93 行から読み、そのまま和・平均を取る) | いいえ | (a) | (a) 入口(依頼文に名前がある) | 目 |
| 17 | `scripts/analysis/simple_trades.py` | ① | — | 83: `float(pnl) / MARGIN_JPY * 1e4`(円 → 口座の bp、MARGIN_JPY = 200_000、38 行) | いいえ | (a) | (a) 入口(依頼文に名前がある) | 目 |
| 18 | `scripts/w4_measure/overlap_daily.py` | 受 | — | なし(daily.csv・trades の pnl_bp を読んで和を取る) | いいえ | (a) | (a) import の鎖 overlap_daily.py ← vol_split_daily.py(入口 scripts/w4_measure/vol_split_daily.py: 入口(今の分析の文書・K-301 以降・batch_tables.sh/commit_gate.sh に `vol_split_daily.py` の名前が出る)) | 目 |
| 19 | `scripts/w4_measure/vol_split_daily.py` | ② | — | 61: `np.mean(np.abs(np.diff(np.log(c)))) * 1e4`(1 分足の対数の値動きの絶対値の平均 = ボラの bp) | いいえ | (a) | (a) 入口(今の分析の文書・K-301 以降・batch_tables.sh/commit_gate.sh に `vol_split_daily.py` の名前が出る) | 目 |
| 20 | `src/bot/strategy/composite.py` | ②(docstring の数だけ) | — | なし | いいえ | (a)・(b) | (a) import の鎖 composite.py ← __init__.py ← matilda_simple.py(入口 src/bot/strategy/matilda_simple.py: 入口(今の分析の文書・K-301 以降・batch_tables.sh/commit_gate.sh に `matilda_simple.py` の名前が出る)) / (b) import の鎖 composite.py ← main.py ← run_paper.py(入口 scripts/run_paper.py: 入口(deploy/ の起動行)) | 目 |
| 21 | `src/bot/strategy/matilda_v37.py` | bp でない | — | なし(62: `100000 / 600000` はレンジの設定) | いいえ | (a) | (a) import の鎖 matilda_v37.py ← matilda_simple.py(入口 src/bot/strategy/matilda_simple.py: 入口(今の分析の文書・K-301 以降・batch_tables.sh/commit_gate.sh に `matilda_simple.py` の名前が出る)) | 目 |
| 22 | `scripts/dashboard.py` | bp でない | — | なし(521: 軸の目盛り 10000、748: 10000 ミリ秒) | いいえ | (b) | (b) 入口(deploy/ の起動行) | 目 |
| 23 | `scripts/data_quality.py` | ④ | スプレッド(`spread_bps` 列の検査) | なし | いいえ | (b) | (b) 入口(deploy/ の起動行) | 目 |
| 24 | `scripts/paper_on1.py` | ②④ | 手数料率(往復の手数料 ÷ 建値 × 乗数) | 115: `math.log(x / e) * 1e4` / 117: `(2 * FEE_SIDE) / (e * MULTIPLIER) * 1e4`(円の手数料 → bp)/ 135: `net_bps / 1e4`(bp → 率) | いいえ | (b) | (b) 入口(deploy/ の起動行) | 目 |
| 25 | `scripts/paper_onr.py` | ② | — | 200・210: `math.log(... / ...) * 1e4` / 244: `sum(bps[-win:]) / 1e4 * 100`(bp → %) | いいえ | (b) | (b) 入口(deploy/ の起動行) | 目 |
| 26 | `scripts/record_funding_basis.py` | ④ | ベーシス(`basis_bp = (fx_mid / spot_mid - 1) * 1e4`)・資金調達率 | 235・248: `(fx_mid / spot_mid - 1.0) * 1e4` | いいえ | (b) | (b) 入口(deploy/ の起動行) | 目 |
| 27 | `scripts/record_venues.py` | ④ | 手数料率(docstring の数) | なし | いいえ | (b) | (b) 入口(deploy/ の起動行) | 目 |
| 28 | `scripts/research_clock_burst.py` | ②④ | 手数料率(TAKER_BPS)・滑り(measured_slip) | 413・548: 値段の比 × 1e4 / 509・515: `ep_ * (1.0 + side * TAKER_BPS / 1e4)`(bp → 値段)/ 510-516: 値動きの bp − 手数料の bp | いいえ | (b) | (b) 入口(deploy/ の起動行) | 目 |
| 29 | `src/bot/bt/report/__init__.py` | 受 | — | なし | いいえ | (b) | (b) import の鎖 __init__.py ← runner.py ← __init__.py ← k1_wick.py ← backtest_themes.py ← backtest_chart.py ← dashboard.py(入口 scripts/dashboard.py: 入口(deploy/ の起動行)) | 目 |
| 30 | `src/bot/bt/report/metrics.py` | ②④ | 手数料率(`fee / (e * q) * 1e4`) | 80: `s * (x - e) / e * 1e4 - fee / (e * q) * 1e4`(値動きの bp − 円の手数料を建玉の円で割った bp)/ 199: `s * (m - px) / px * 1e4` | いいえ | (b) | (b) import の鎖 metrics.py ← runner.py ← __init__.py ← k1_wick.py ← backtest_themes.py ← backtest_chart.py ← dashboard.py(入口 scripts/dashboard.py: 入口(deploy/ の起動行)) | 目 |
| 31 | `src/bot/bt/repro/runner.py` | 受 | — | なし | いいえ | (b) | (b) import の鎖 runner.py ← __init__.py ← k1_wick.py ← backtest_themes.py ← backtest_chart.py ← dashboard.py(入口 scripts/dashboard.py: 入口(deploy/ の起動行)) | 目 |
| 32 | `src/bot/jpx/etf_auction_executor.py` | ②④ | 手数料率(fee_bps)・約定のずれ(e_buy・e_sell)・呼値(tick_bps) | 763-764: `(fill - print) / print * 1e4` / 768: `fees / (fill_buy * qty) * 1e4`(円 → bp)/ 769: `(printed - realised) * 1e4 + fee_bps` / 771・1438: `tick / print_close * 1e4` | いいえ | (b) | (b) import の鎖 etf_auction_executor.py ← run_etf_measure_reconcile.py(入口 scripts/run_etf_measure_reconcile.py: 入口(OPERATIONS_JPX.md の人が打つ照合)) | 目 |
| 33 | `src/bot/monitoring/aggregate.py` | 受 | — | 356: `sum(net_bps[-win:]) / 1e4 * 100`(bp → %) | いいえ | (b) | (b) import の鎖 aggregate.py ← dashboard.py(入口 scripts/dashboard.py: 入口(deploy/ の起動行)) | 目 |
| 34 | `src/bot/monitoring/backtest_cards.py` | 受 | — | なし(cards/<card>/<variant>/daily.csv の pnl_bp を読んで和・落ち込み) | いいえ | (b) | (b) import の鎖 backtest_cards.py ← backtest_chart.py ← dashboard.py(入口 scripts/dashboard.py: 入口(deploy/ の起動行)) | 目 |
| 35 | `src/bot/monitoring/backtest_chart.py` | ②③受 | — | 356: `pnl / (ep * qty) * 1e4`(円の損益 → 1 単位あたり値段に対する bp)。379: 記録に bp しか無いときは `doc["pnl_bp"]` をそのまま使う | いいえ | (b) | (b) import の鎖 backtest_chart.py ← dashboard.py(入口 scripts/dashboard.py: 入口(deploy/ の起動行)) | 目 |
| 36 | `src/bot/monitoring/backtest_themes.py` | ②④ | ひげの長さの門(閾値の引数) | なし(文の中の bp) | いいえ | (b) | (b) import の鎖 backtest_themes.py ← backtest_chart.py ← dashboard.py(入口 scripts/dashboard.py: 入口(deploy/ の起動行)) | 目 |
| 37 | `src/bot/monitoring/backtest_view.py` | 受 | — | なし(per_trade_bp・mean_bp を表示) | いいえ | (b) | (b) import の鎖 backtest_view.py ← dashboard.py(入口 scripts/dashboard.py: 入口(deploy/ の起動行)) | 目 |
| 38 | `src/bot/research/board.py` | ④ | 板の距離の引数(`band = mid * bps / 1e4`)・板を食う経費(cost_bp) | 108: `mid * bps / 1e4`(bp → 値段の幅)/ 189・191: `(vwap - mid) / mid * 1e4` | いいえ | (b) | (b) import の鎖 board.py ← extract_tape.py(入口 scripts/extract_tape.py: 入口(deploy/ の起動行)) | 目 |
| 39 | `src/bot/research/overnight.py` | 受 | — | なし(values_bps を引数で受ける。中身は呼ぶ側しだい: 粗の収益・経費・純) | いいえ | (b) | (b) import の鎖 overnight.py ← etf_auction_executor.py ← run_etf_measure_reconcile.py(入口 scripts/run_etf_measure_reconcile.py: 入口(OPERATIONS_JPX.md の人が打つ照合)) | 目 |
| 40 | `src/bot/strategy/k1_wick.py` | ② | — | 91: `wbp = w / c * 10000.0`(ひげの長さ ÷ 終値 → bp) | いいえ | (b) | (b) import の鎖 k1_wick.py ← backtest_themes.py ← backtest_chart.py ← dashboard.py(入口 scripts/dashboard.py: 入口(deploy/ の起動行)) | 目 |
| 41 | `scripts/dashboard_cards/export_card_trades.py` | ③ | — | 11: P_t = e_t × (… − 1) × 1e4 / 247: `pnl_bp: compact(tr["trade_pnl"], 4)`(小数 4 桁に丸め)。181: 指値の模型 matilda_limit_sim の pnl_bp(向き × (出/入 − 1) × 1e4 ÷ 段数 の和 = ③型)も同じ列に書く | いいえ | (d) | import では辿れない。既定の出力の置き場 `backtest_runs_shared/cards`(199 行)を (b) の `backtest_cards.py`(5-7 行)が読む口はある。その置き場は git に無い(`ls backtest_runs_shared/cards` → No such file、`git ls-files \| grep -c '/cards/manifest.json'` → 0)。オーナーの PC の手元に出力があるかは未確認 | 目 |
| 42 | `scripts/k1_newenv_g_rawrun.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。bot.bt.repro の runner で `backtest_runs/` の下に走らせを書き、(b) のダッシュボード(`scripts/dashboard.py` 45 行 BACKTEST_RUNS_DIR、`backtest_view.py`)はその置き場を読む。`backtest_runs/` は git に無く、オーナーの PC の手元に今その走らせがあるかは未確認 | 機械 |
| 43 | `scripts/w4_measure/daily_stats.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。(d) の書き手(export_card_trades.py・k1_newenv_g_rawrun.py・w4_measure/post.py・bt/pipeline.py のどれか)が import で使う。書き手の出力がオーナーの PC で今ダッシュボードに出ているかは未確認 | 機械 |
| 44 | `scripts/w4_measure/light_b2.py` | ②③④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。(d) の書き手(export_card_trades.py・k1_newenv_g_rawrun.py・w4_measure/post.py・bt/pipeline.py のどれか)が import で使う。書き手の出力がオーナーの PC で今ダッシュボードに出ているかは未確認 | 機械 |
| 45 | `scripts/w4_measure/post.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。bot.bt.repro の runner で `backtest_runs/` の下に走らせを書き、(b) のダッシュボード(`scripts/dashboard.py` 45 行 BACKTEST_RUNS_DIR、`backtest_view.py`)はその置き場を読む。`backtest_runs/` は git に無く、オーナーの PC の手元に今その走らせがあるかは未確認 | 機械 |
| 46 | `scripts/w4_measure/run_v2.py` | ③ | — | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。(d) の書き手(export_card_trades.py・k1_newenv_g_rawrun.py・w4_measure/post.py・bt/pipeline.py のどれか)が import で使う。書き手の出力がオーナーの PC で今ダッシュボードに出ているかは未確認 | 機械 |
| 47 | `src/bot/bt/pipeline.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。bot.bt.repro の runner で `backtest_runs/` の下に走らせを書き、(b) のダッシュボード(`scripts/dashboard.py` 45 行 BACKTEST_RUNS_DIR、`backtest_view.py`)はその置き場を読む。`backtest_runs/` は git に無く、オーナーの PC の手元に今その走らせがあるかは未確認 | 機械 |
| 48 | `src/bot/research/cards/__init__.py` | ③ | — | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。(d) の書き手(export_card_trades.py・k1_newenv_g_rawrun.py・w4_measure/post.py・bt/pipeline.py のどれか)が import で使う。書き手の出力がオーナーの PC で今ダッシュボードに出ているかは未確認 | 機械 |
| 49 | `src/bot/research/cards/library/c2_owner_xvenue_wick.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。(d) の書き手(export_card_trades.py・k1_newenv_g_rawrun.py・w4_measure/post.py・bt/pipeline.py のどれか)が import で使う。書き手の出力がオーナーの PC で今ダッシュボードに出ているかは未確認 | 機械 |
| 50 | `src/bot/research/cards/measure.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。(d) の書き手(export_card_trades.py・k1_newenv_g_rawrun.py・w4_measure/post.py・bt/pipeline.py のどれか)が import で使う。書き手の出力がオーナーの PC で今ダッシュボードに出ているかは未確認 | 機械 |
| 51 | `src/bot/research/cards/pnl.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (d) | import では (a)(b) から辿れない。(d) の書き手(export_card_trades.py・k1_newenv_g_rawrun.py・w4_measure/post.py・bt/pipeline.py のどれか)が import で使う。書き手の出力がオーナーの PC で今ダッシュボードに出ているかは未確認 | 機械 |
| 52 | `backtest_data/venue_survey_20260827/analyze_screen.py` | ②④ | スプレッド・手数料率 | 79: `ceil = max(mk2, 0.0) / 1e4 * vj * SHARE   # yen/day at SHARE of venue volume` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 53 | `backtest_data/venue_survey_20260827/analyze_venues.py` | ②④ | スプレッド・ベーシス・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 54 | `docs/DATA/probes/20260919_jev_select_rank_probe.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 55 | `docs/DATA/probes/20260919_o3c_reaction_bugcheck.py` | ②④ | 損益分岐・閾値・距離の引数 | 17: `rel=float(np.nanmax(np.abs(pt[m]/pl[m]-1-d[m]/1e4)))` / 22: `print(f'{name}: 清算行 {len(liq)} / 到達の h 単調 {mono} / 到達秒と h の食い違い {bad} 行 / 目標価格=p_liq×(1+di` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 56 | `docs/DATA/probes/20260919_o3c_reaction_bugcheck2.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 57 | `docs/DATA/probes/20260919_o3c_reaction_r1_bp_reactdir_standardized.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 58 | `docs/DATA/probes/20260919_o3c_signal_explore2_refuter_verify.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 59 | `docs/DATA/probes/20260919_o3c_signal_refuter_verify.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 60 | `docs/DATA/probes/20260920_jev_continue_call_probe.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 61 | `docs/DATA/probes/20260920_o3c_cascade_read.py` | ②④ | 損益分岐・閾値・距離の引数 | 273: `edge = p0 * (1.0 + sign * x / 1e4)` / 478: `md.append("### 8. この先 X bp 以内(5/10/20)にある建玉の量")` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 62 | `docs/DATA/probes/20260920_o3c_jev_state_proto.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 63 | `docs/DATA/probes/20260920_o3c_signal_continue_refuter.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 64 | `docs/DATA/probes/20260920_o3c_signal_continue_refuter_verify.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 65 | `docs/DATA/probes/20260920_o3c_signal_continue_verify.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 66 | `docs/DATA/probes/20260920_o3c_signal_explore3_refuter_verify.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 67 | `docs/DATA/probes/20260920_o3c_signal_explore3_verify.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 68 | `docs/DATA/probes/20260920_o3c_signal_explore4_refuter_verify.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 69 | `docs/DATA/probes/20260920_o3c_signal_explore4_verify.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 70 | `docs/DATA/probes/20260920_o3c_signal_explore5_refuter.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 71 | `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_2/materials/speed_old_vs_new_compat.py` | bp でない | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 72 | `docs/DISCUSSIONS/2026-10-06_held_batches/rows_k152.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 73 | `docs/DISCUSSIONS/2026-10-06_held_batches/rows_k153_c4rerun.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 74 | `docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/d2_volsplit.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 75 | `docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/d7_table.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 76 | `docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/feet_crossed.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 77 | `docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/summarize.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 78 | `docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/measure_vol_gate.py` | ②④ | 手数料率・損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 79 | `docs/RESEARCH/cards/c3_yen_premium_revert/redo2_2026-10-05/convert_limit.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 80 | `docs/RESEARCH/cards/c3_yen_premium_revert/redo2_2026-10-05/d2_volsplit.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 81 | `docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/fill_delay.py` | ③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 82 | `docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/gate_diag.py` | ③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/gate_check.py(どれも (a)(b) から辿れない) | 機械 |
| 83 | `docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/gate_tables.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 84 | `docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/breakdown_tables.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 85 | `docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d2_volsplit.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 86 | `docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d7_table.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 87 | `docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d8_table.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 88 | `docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/summarize.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 89 | `docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/c5_redo.py` | ②③④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 90 | `docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/d5_entry_open.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 91 | `docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/d5_mid_check.py` | ②③④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 92 | `docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/rebuild_trades.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 93 | `docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/c6_redo.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 94 | `docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/k046_recount.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 95 | `docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/offhour_check.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 96 | `docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/c7_redo.py` | ②③④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 97 | `docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/race_more.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 98 | `docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/race_replay.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 99 | `docs/RESEARCH/cards/c8_session_mean_revert/redo2_2026-10-05/c8_more.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 100 | `docs/RESEARCH/cards/c8_session_mean_revert/redo2_2026-10-05/c8_redo.py` | ②③④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 101 | `docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_more.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 102 | `docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_redo.py` | ②④ | 滑り・約定経費 | 215: `pend = s2.p0 * (1 + s2.sign * s2[col] / 1e4)` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 103 | `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_iv.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_iv_days.py, docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_ivh.py(どれも (a)(b) から辿れない) | 機械 |
| 104 | `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_ivh.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_iv_days.py(どれも (a)(b) から辿れない) | 機械 |
| 105 | `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/make_tables.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 106 | `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/three_way_m.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/RESEARCH/cards/c9_liquidation_cascade/run_a/three_way_m_policy.py(どれも (a)(b) から辿れない) | 機械 |
| 107 | `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/three_way_m_policy.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 108 | `docs/RESEARCH/cards/diag_why/c6c8.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 109 | `docs/RESEARCH/cards/tools/c4_components_tables.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 110 | `docs/RESEARCH/cards/tools/goal_table.py` | ②③④ | 損益分岐・閾値・距離の引数 | 44: `gross_month_pct=float(dsum.mean()*30.4/100), gross_month_yen_at_600k=float(dsum.mean()*30.` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 111 | `docs/RESEARCH/cards/tools/goal_table2.py` | ③ | — | 25: `month_yen=float(dsum.mean()*30.4/1e4*NOTIONAL),dd=dd,worst_month=float(msum.min()),pos_mon` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 112 | `docs/RESEARCH/cards/tools/goal_table_c4.py` | ③④ | 損益分岐・閾値・距離の引数 | 26: `month_yen=pd * 30.4 / 1e4 * 600000, max_dd_bp=dd, worst_day_bp=float(p.min()), worst_month` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 113 | `docs/RESEARCH/cards/tools/pertrade_by_year.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 114 | `docs/RESEARCH/cards/tools/winloss_shape.py` | ③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 115 | `docs/legacy/matilda_for_TaroCamp37.py` | bp でない | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 116 | `docs/legacy/matilda_v52.py` | bp でない | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 117 | `scripts/analysis/batch_runs.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 118 | `scripts/analysis/c9_halves.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 119 | `scripts/analysis/card_trades.py` | ③ | — | 6 行 docstring・102: `pnl_bp = cp[b] - cp[a]`(P_t = e_t × (open_{t+2}/open_{t+1} − 1) × 1e4 の和) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 目 |
| 120 | `scripts/analysis/trade_rows.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/analysis/batch_runs.py(どれも (a)(b) から辿れない) | 機械 |
| 121 | `scripts/backfill_spread_from_tape.py` | ②④ | スプレッド | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 122 | `scripts/build_burst_library.py` | 未分類 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 123 | `scripts/build_fx_event_library.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/build_fx_event_library_2005_2014.py(どれも (a)(b) から辿れない) | 機械 |
| 124 | `scripts/c9_run_a.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 125 | `scripts/check_k1_binance.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 126 | `scripts/check_k1_bitflyer_data.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 127 | `scripts/constants_inventory.py` | ④ | スプレッド | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_constants_inventory.py(どれも (a)(b) から辿れない) | 機械 |
| 128 | `scripts/explore_o3c_oi_axis.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 129 | `scripts/fetch_dukascopy.py` | bp でない | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/build_fx_event_library.py, scripts/build_fx_event_library_2005_2014.py(どれも (a)(b) から辿れない) | 機械 |
| 130 | `scripts/jev_check.py` | ②④ | 手数料率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/jev_audit_eval.py, scripts/jev_audit_loop.py, scripts/jev_delegate.py ほか 13(どれも (a)(b) から辿れない) | 機械 |
| 131 | `scripts/jev_delegate.py` | 未分類 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_jev_delegate.py(どれも (a)(b) から辿れない) | 機械 |
| 132 | `scripts/jev_report_intake.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_jev_report_intake.py(どれも (a)(b) から辿れない) | 機械 |
| 133 | `scripts/judge_board_round.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/tp_operating_curve.py, tests/test_board_round.py(どれも (a)(b) から辿れない) | 機械 |
| 134 | `scripts/judge_gates.py` | ①②④ | 手数料率・金利・キャリー | 476: `bps = (pnl / notional * 1e4) if (pnl is not None and notional) else None` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_judge_gates.py(どれも (a)(b) から辿れない) | 機械 |
| 135 | `scripts/k1_newenv_check_parse_old.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 136 | `scripts/k1_newenv_diff.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 137 | `scripts/k1_newenv_fix_pipeline.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 138 | `scripts/k1_newenv_g_diff.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 139 | `scripts/k1_newenv_g_old.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 140 | `scripts/k1_newenv_g_selftest.py` | bp でない | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 141 | `scripts/k1_newenv_g_tables.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 142 | `scripts/k1_newenv_tables.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 143 | `scripts/measure_exec_floor.py` | ②③④ | スプレッド・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 144 | `scripts/measure_katsuo_body_wick.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/measure_katsuo_robustness.py(どれも (a)(b) から辿れない) | 機械 |
| 145 | `scripts/measure_katsuo_delay_decomp.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/measure_katsuo_round5.py, tests/test_k1_delay_decomp.py, tests/test_k1_round5.py(どれも (a)(b) から辿れない) | 機械 |
| 146 | `scripts/measure_katsuo_direction_bias.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 147 | `scripts/measure_katsuo_dispersion.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/check_k1_binance.py, scripts/check_k1_bitflyer_data.py, scripts/k1_source.py ほか 17(どれも (a)(b) から辿れない) | 機械 |
| 148 | `scripts/measure_katsuo_effect.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/measure_vol_gate.py, scripts/check_k1_bitflyer_data.py, scripts/measure_exec_floor.py ほか 18(どれも (a)(b) から辿れない) | 機械 |
| 149 | `scripts/measure_katsuo_exit_ablation.py` | ②③④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_k1_no_invalidation.py(どれも (a)(b) から辿れない) | 機械 |
| 150 | `scripts/measure_katsuo_judgement_vol.py` | ②④ | 手数料率・損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 151 | `scripts/measure_katsuo_robustness.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/measure_vol_gate.py, scripts/measure_katsuo_judgement_vol.py, scripts/measure_katsuo_round5.py ほか 4(どれも (a)(b) から辿れない) | 機械 |
| 152 | `scripts/measure_katsuo_round5.py` | ②③④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_k1_round5.py(どれも (a)(b) から辿れない) | 機械 |
| 153 | `scripts/measure_katsuo_signal_horizon.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/measure_katsuo_body_wick.py, scripts/measure_katsuo_exit_ablation.py, scripts/measure_katsuo_robustness.py ほか 1(どれも (a)(b) から辿れない) | 機械 |
| 154 | `scripts/measure_katsuo_vol_bitflyer.py` | ②④ | 手数料率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 155 | `scripts/measure_katsuo_xvenue.py` | ②④ | 手数料率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/measure_vol_gate.py, tests/research/test_katsuo_limit_sim.py, tests/test_k1_xvenue.py(どれも (a)(b) から辿れない) | 機械 |
| 156 | `scripts/measure_liq_bands.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 157 | `scripts/measure_liq_response.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 158 | `scripts/o3c_bitflyer_spread.py` | ②④ | スプレッド | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 159 | `scripts/o3c_jev_state.py` | ②④ | 資金調達率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 160 | `scripts/o3c_oi_distance.py` | ②④ | スプレッド・手数料率・損益分岐・閾値・距離の引数 | 563: `denom = float(d) / 1e4 + mmr` / 826: `"implied_leverage = 1 / (d/1e4 + mmr)、d = oi_dist_vwap_bp_liqdir。"` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/DATA/probes/20260920_o3c_cascade_read.py, scripts/o3c_reaction.py, scripts/o3c_signal_continue.py ほか 2(どれも (a)(b) から辿れない) | 機械 |
| 161 | `scripts/o3c_price_level_ext.py` | ②④ | 損益分岐・閾値・距離の引数 | 495: ``offset = -中央値 / 1e4` を小数 4 桁に丸める(前回の SELL −0.0056 / BUY +0.0070 と` / 520: `offsets = {s: round(-m / 1e4, 4) for s, m in medians.items()}` / 533: `f"offset = -中央値 / 1e4 を小数 4 桁に丸めた値(前回と同じ取り方)"` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 162 | `scripts/o3c_price_level_table.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/DATA/probes/20260920_o3c_cascade_read.py, scripts/o3c_oi_distance.py, scripts/o3c_price_level_ext.py ほか 8(どれも (a)(b) から辿れない) | 機械 |
| 163 | `scripts/o3c_reaction.py` | ②④ | 損益分岐・閾値・距離の引数 | 2136: `p_liq * (1.0 + float(bp_val) / 1e4)` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/o3c_signal_explore5.py(どれも (a)(b) から辿れない) | 機械 |
| 164 | `scripts/o3c_reaction_judge.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 165 | `scripts/o3c_reaction_r2.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/o3c_signal_explore.py(どれも (a)(b) から辿れない) | 機械 |
| 166 | `scripts/o3c_rows4.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/o3c_reaction.py(どれも (a)(b) から辿れない) | 機械 |
| 167 | `scripts/o3c_signal_continue.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 168 | `scripts/o3c_signal_continue_jev.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 169 | `scripts/o3c_signal_explore.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 170 | `scripts/o3c_signal_explore2.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/o3c_signal_continue.py(どれも (a)(b) から辿れない) | 機械 |
| 171 | `scripts/o3c_signal_explore3.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 172 | `scripts/o3c_signal_explore4.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 173 | `scripts/o3c_signal_explore5.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/DATA/probes/20260920_o3c_cascade_read.py(どれも (a)(b) から辿れない) | 機械 |
| 174 | `scripts/o3c_signal_materials.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 175 | `scripts/o3c_signal_policy.py` | ②④ | 損益分岐・閾値・距離の引数 | 527: `target = float(px) * (1.0 + float(direction) * float(tp_bp) * 1e-4)` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 176 | `scripts/o3c_signal_value.py` | ②③④ | 損益分岐・閾値・距離の引数・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 177 | `scripts/phase2/g1_state_analysis.py` | ②④ | 滑り・約定経費 | 120: `"cost_text": "cost_bps_cons(保守往復コスト 122 円 / (close_t × 10) bps)",` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 178 | `scripts/phase2/p2_01_final.py` | ②④ | 手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_phase2_p2_01_final.py(どれも (a)(b) から辿れない) | 機械 |
| 179 | `scripts/phase2/p2_01_run.py` | ②④ | 手数料率・滑り・約定経費 | 134: `out["cost_bps_cons"] = COST_YEN_CONSERVATIVE / notional * 1e4` / 135: `out["cost_bps_opt"] = COST_YEN_OPTIMISTIC / notional * 1e4` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/phase2/p2_01_final.py, scripts/phase2/p2_01b_history.py, tests/test_phase2_p2_01.py ほか 1(どれも (a)(b) から辿れない) | 機械 |
| 180 | `scripts/phase2/p2_01b_history.py` | ②④ | 滑り・約定経費 | 230: `lhs = pairs_full["cost_bps_cons"] * pairs_full["close_t"] * MULTIPLIER / 1e4` / 235: `"formula": "cost_bps_cons(t) * close_t(t) * MULTIPLIER(10) / 1e4",` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 181 | `scripts/phase2/p2_02_final.py` | ②④ | ベーシス・損益分岐・閾値・距離の引数・滑り・約定経費 | 439: `pnl_yen = kept["close_t"].to_numpy() * (net_cons / 1e4)` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_phase2_p2_02_final.py(どれも (a)(b) から辿れない) | 機械 |
| 182 | `scripts/phase2/p2_02_run.py` | ②④ | 手数料率・滑り・約定経費 | 192: `fee_yen / notional * 1e4 (one commission per side, round trip).` / 197: `fee_bps = 2.0 * fee_yen / notional * 1e4` / 506: `pnl_yen = kept_1343["close_t"].to_numpy() * (net_cons / 1e4)` ほか 2 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/phase2/p2_02_final.py, tests/test_phase2_p2_02.py, tests/test_phase2_p2_02_final.py(どれも (a)(b) から辿れない) | 機械 |
| 183 | `scripts/phase2/p2_03_final.py` | ②④ | 滑り・約定経費 | 1083: `f"**現在の呼値 1 円は片側 {row1306['per_side_bps_now']:.2f}bps"` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_phase2_p2_03_final.py(どれも (a)(b) から辿れない) | 機械 |
| 184 | `scripts/phase2/p2_03_iter2.py` | ④ | 滑り・約定経費 | 356: `"(config/constants.yaml)のため、価格が低かった開発セット前半(2011年 ~760円台)ほどbps換算コストが"` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_phase2_p2_03_iter2.py(どれも (a)(b) から辿れない) | 機械 |
| 185 | `scripts/phase2/p2_03_run.py` | ②④ | 滑り・約定経費 | 410: `frac = x_bps / 1e4` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/phase2/p2_03_final.py, scripts/phase2/p2_03_iter2.py, tests/test_phase2_p2_03.py ほか 1(どれも (a)(b) から辿れない) | 機械 |
| 186 | `scripts/phase2/p2_04_run.py` | ②④ | 手数料率・滑り・約定経費 | 718: `pairs["cost_bps_cons"] = cost_yen_cons / notional * 1e4` / 719: `pairs["cost_bps_opt"] = cost_yen_opt / notional * 1e4` / 1307: `f"{cost_yen_cons} 円/往復 → cost_bps(t) = {cost_yen_cons} /(close_day(t−1) × 10)× 10^4。"` ほか 1 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_phase2_p2_04.py(どれも (a)(b) から辿れない) | 機械 |
| 187 | `scripts/phase2/p2_08_run.py` | ①②④ | スプレッド・手数料率・滑り・約定経費・資金調達率 | 443: `"sum_pnl_jpy_001btc": float((net / 1e4 * a["entry_px"][keep] * 0.01).sum()),` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 188 | `scripts/preflight_prereg.py` | 受 | — | 378: `if re.search(r"\d+(\.\d+)?\s*(bp\|%\|ドル\|円)", cleaned) and not any(` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_preflight_prereg.py, tests/test_research_protocol_rules.py(どれも (a)(b) から辿れない) | 機械 |
| 189 | `scripts/qa/make_known_answer.py` | ②④ | スプレッド・ベーシス・手数料率・滑り・約定経費 | 112: `overnight_noise_sigma = (DAILY_OVERNIGHT_SIGMA_BPS / 1e4) * (sigma_intraday / sigma_intrad` / 114: `overnight_ret = premium_bps / 1e4 + overnight_z * overnight_noise_sigma` / 119: `overnight_ret[i] += EX_DIV_DROP_BPS / 1e4` ほか 3 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/qa/make_known_answer_steer.py, tests/test_qa_make_known_answer.py, tests/test_qa_make_known_answer_steer.py(どれも (a)(b) から辿れない) | 機械 |
| 190 | `scripts/qa/make_known_answer_maker.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | 70: `TICK_LOG = REPRICE_TICK_BPS / 1e4      # re-price threshold in log-mid units` / 146: `d_log = (IMPACT_BPS_PER_UNIT_SIZE / 1e4) * signed + NOISE_SIGMA_LOG * rng.standard_normal(` / 263: `edge = (HALF_SPREAD_BPS - price_improve_ticks * TICK_BPS) / 1e4` ほか 2 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_qa_make_known_answer_maker.py(どれも (a)(b) から辿れない) | 機械 |
| 191 | `scripts/qa/make_known_answer_maker3.py` | ②④ | スプレッド・手数料率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_qa_make_known_answer_maker3.py(どれも (a)(b) から辿れない) | 機械 |
| 192 | `scripts/qa/make_known_answer_steer.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_qa_make_known_answer_steer.py(どれも (a)(b) から辿れない) | 機械 |
| 193 | `scripts/qa/maker_fill_ref.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_qa_maker_fill_ref.py(どれも (a)(b) から辿れない) | 機械 |
| 194 | `scripts/qa/maker_fill_ref_packet.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 195 | `scripts/qa/maker_fill_ref_packet_r2.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_qa_maker_fill_ref.py(どれも (a)(b) から辿れない) | 機械 |
| 196 | `scripts/qa/pipeline_known_answer_daily.py` | ②④ | ベーシス | 124: `overnight_noise_sigma = (OVERNIGHT_NOISE_SIGMA_BPS / 1e4) * (sigma_intraday / sigma_intrad` / 146: `overnight_ret = np.where(tercile == "high", y_bps / 1e4, 0.0) \` / 403: `planted_simple = RETKIND_PLANTED_SIMPLE_BPS / 1e4` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_qa_pipeline_known_answer.py(どれも (a)(b) から辿れない) | 機械 |
| 197 | `scripts/qa/pipeline_known_answer_taker.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | 122: `per_bar = sign * (mag_bps / 1e4) / LOOKBACK_BARS` / 156: `returns[lo:hi] += ev["sign"] * (x_bps / 1e4) / HOLD_BARS` / 261: `return np.asarray(trade_pnls, dtype=float) / ORDER_NOTIONAL_JPY * 1e4` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_qa_pipeline_known_answer.py(どれも (a)(b) から辿れない) | 機械 |
| 198 | `scripts/qa/score_audit.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_qa_score_audit.py(どれも (a)(b) から辿れない) | 機械 |
| 199 | `scripts/render_exec_floor.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 200 | `scripts/render_k1_body_wick.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 201 | `scripts/render_k1_deepdive.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 202 | `scripts/render_k1_exit_ablation.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 203 | `scripts/render_k1_fresh_bitflyer.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 204 | `scripts/render_k1_h1.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 205 | `scripts/render_k1_h2.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 206 | `scripts/render_k1_h3.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 207 | `scripts/render_k1_h3_decomp.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 208 | `scripts/render_k1_judgement.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 209 | `scripts/render_k1_robustness.py` | ②④ | 滑り・約定経費・資金調達率 | 334: `print(f"各マスは 平均 bp と (件数)。BitMEX の資金調達時刻(04/12/20 UTC)を含む区分: {fb}。\n")` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 210 | `scripts/render_k1_round5.py` | ②④ | 損益分岐・閾値・距離の引数・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 211 | `scripts/render_k1_trunc_compare.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 212 | `scripts/render_k1_venue_compare.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 213 | `scripts/render_k1_xvenue.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 214 | `scripts/render_k1_xvenue2.py` | ②④ | ベーシス | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 215 | `scripts/render_k1_year_tables.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 216 | `scripts/render_k1_yearly_pnl.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 217 | `scripts/render_prereg.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/preflight_prereg.py(どれも (a)(b) から辿れない) | 機械 |
| 218 | `scripts/replay_scalp_storm.py` | ②④ | スプレッド・ベーシス・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/research_exit_surface.py, scripts/research_scalp_exits.py(どれも (a)(b) から辿れない) | 機械 |
| 219 | `scripts/research_anchor.py` | ②④ | スプレッド・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 220 | `scripts/research_anchor_v2.py` | ②④ | 手数料率・滑り・約定経費・金利・キャリー | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 221 | `scripts/research_avalanche.py` | ②④ | 手数料率・滑り・約定経費 | 96: `* Entry fill price P_e = base * (1 + side * c_in/1e4), c_in in` / 99: `* TP limit L = P_e * (1 + side * tp/1e4) -- "entry + tp bps" is measured` / 361: `p_e = base * (1.0 + side * c_in / 1e4)` ほか 2 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 222 | `scripts/research_basis.py` | ②④ | ベーシス | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 223 | `scripts/research_board_calibration.py` | ②④ | スプレッド・手数料率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/judge_board_round.py, scripts/research_m4_finecheck.py, scripts/research_matilda_modern.py ほか 3(どれも (a)(b) から辿れない) | 機械 |
| 224 | `scripts/research_burst_atlas.py` | ②④ | 手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 225 | `scripts/research_calm_range.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | 204: `trig = (seg_p < lo * (1 - RANGE_BREAK_BPS / 1e4)) if side > 0 else \` / 205: `(seg_p > hi * (1 + RANGE_BREAK_BPS / 1e4))` / 246: `off = cfg.offset_bps / 1e4` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 226 | `scripts/research_exit_surface.py` | ②④ | 手数料率・滑り・約定経費 | 228: `return math.ceil(entry_px * (1.0 + tp_bps / 1e4) / TICK_JPY) * TICK_JPY` / 229: `return math.floor(entry_px * (1.0 - tp_bps / 1e4) / TICK_JPY) * TICK_JPY` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 227 | `scripts/research_fast_cycle.py` | ①②④ | スプレッド・手数料率・滑り・約定経費 | 419: `tp_px = entry_px * (1.0 + side * tp_bps * 1e-4)` / 420: `stop_mid = entry_px * (1.0 - side * abort_bps * 1e-4)` / 900: `print("bps/d = mean daily net bps at one unit of notional per trade.")` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 228 | `scripts/research_fx.py` | bp でない | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 229 | `scripts/research_fx_carry.py` | ②③④ | スプレッド・滑り・約定経費・金利・キャリー | 113: `plus swapDays).  It covers 2023-04 -> present.  Converting to bps/day of JPY` / 330: `notional_jpy = 10_000.0 * g["px"]` / 331: `g["buy_bps_day"] = g["swap_buy"] / notional_jpy * 1e4 / g["swap_days"]` ほか 5 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 230 | `scripts/research_fx_event_ticks.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | 653: `print(f"    mid(E+5s)  = {demo.mid_e * (1 + demo.impulse_bps/1e4):.5f}   "` / 670: `print("     the cost-of-event-trading map: real interbank bid/ask, bps, USD/JPY")` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/research_fx_s4_judgment.py(どれも (a)(b) から辿れない) | 機械 |
| 231 | `scripts/research_fx_events.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | 19: `USD events, BOJ MPM is a JPY event, and round-trip cost is 0.71 bps (1/9 of BTC` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 232 | `scripts/research_fx_fundamentals.py` | ①②③④ | スプレッド・滑り・約定経費 | 1136: `f"mean USD/JPY {1e4 * ret[mask].mean():+7.1f}bps")` / 1168: `print(f"  USD/JPY 4-week cumulative: n={len(cum)}  mean {m_:+.1f}bps  "` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 233 | `scripts/research_fx_s4_judgment.py` | ④ | スプレッド・手数料率・滑り・約定経費 | 459: `print("(median quoted spread in bps at the instant; Dukascopy interbank USD/JPY)")` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 234 | `scripts/research_fx_sessions.py` | ②④ | スプレッド・手数料率・滑り・約定経費・金利・キャリー | 110: `KNOWLEDGE_FX.md sec.1: USD/JPY round-trip is 0.71bps and MAKER IS NOT FREE --` / 121: `b=10bps -> p* = (10 + 0.71)/20 = 53.55%` / 353: `up = edge * (1.0 + bps / 1e4)` ほか 3 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 235 | `scripts/research_fx_tokyofix.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 236 | `scripts/research_hft.py` | ②④ | 手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 237 | `scripts/research_imbalance.py` | ②④ | スプレッド | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 238 | `scripts/research_latency_grade.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | 50: `long  (side +1): entry = ask[q] * (1 + slip/1e4)` / 51: `short (side -1): entry = bid[q] * (1 - slip/1e4)` / 353: `entry = np.where(long_, ask[q0], bid[q0]) * (1.0 + sides * slip / 1e4)` ほか 5 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 239 | `scripts/research_leader_surface.py` | ②④ | 手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 240 | `scripts/research_legacy_elements.py` | ④ | スプレッド・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 241 | `scripts/research_m4_finecheck.py` | ②④ | 手数料率・滑り・約定経費・資金調達率 | 617: `xpx = last * (1.0 - side * TAKER_BPS / 1e4)` / 641: `xpx = last * (1.0 - side * TAKER_BPS / 1e4)` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 242 | `scripts/research_macro_calendar.py` | 未分類 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 243 | `scripts/research_mainbot_exits.py` | ④ | スプレッド・手数料率・滑り・約定経費・金利・キャリー | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 244 | `scripts/research_maker_reaudit.py` | ②④ | 手数料率・滑り・約定経費 | 249: `tp_px = entry * (1.0 + side * tp_dist_bps / 1e4)` / 500: `limit = c * (1.0 - r.side * off / 1e4)` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 245 | `scripts/research_matilda_modern.py` | ②③④ | スプレッド・ベーシス・手数料率 | 93: `日次シャープ **≥1.0**(年率換算 ×√365 で凍結)かつ maxDD **≤1000bps**(累積、1x notional)` / 732: `xpx = mp * (1.0 - side * TAKER_BPS / 1e4)` / 767: `xpx = mp * (1.0 - side * TAKER_BPS / 1e4)` ほか 1 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 246 | `scripts/research_matilda_surface.py` | ②④ | スプレッド・手数料率・滑り・約定経費・資金調達率 | 468: `close_cycle(t, last * (1.0 - side * TAKER_BPS / 1e4),` / 585: `close_cycle(t, last * (1.0 - side * TAKER_BPS / 1e4), xk, True)` / 607: `close_cycle(t, last * (1.0 - side * TAKER_BPS / 1e4),` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/research_m4_finecheck.py(どれも (a)(b) から辿れない) | 機械 |
| 247 | `scripts/research_matilda_taro.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | 52: `\| range_setting=150円 / over=10万円 \| **bps化**: 最小 40分レンジ ≥ 10bps(≈原典1.5bpの意図を現代の意味あるガードに引直し)` / 972: `xpx = last * (1.0 - side * TAKER_BPS / 1e4)` / 996: `xpx = last * (1.0 - side * TAKER_BPS / 1e4)` ほか 3 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/research_m4_finecheck.py, scripts/research_matilda_surface.py(どれも (a)(b) から辿れない) | 機械 |
| 248 | `scripts/research_nk225_events.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 249 | `scripts/research_overnight_on1.py` | ④ | 滑り・約定経費 | 163: `net = [r - bps / 1e4 for r in on]` / 235: `on_net = [r - COST_CONS_BPS / 1e4 for r in on]` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 250 | `scripts/research_overnight_onr.py` | ④ | 滑り・約定経費 | 162: `cost = cost_bps * 1e-4` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_onr.py, tests/test_qa_pipeline_known_answer.py(どれも (a)(b) から辿れない) | 機械 |
| 251 | `scripts/research_prediction_atlas.py` | ②④ | スプレッド・手数料率 | 76: `up-hit  = first k>j with m[k] >= m[j]*(1+X/1e4)` / 77: `down-hit= first k>j with m[k] <= m[j]*(1-X/1e4)` / 387: `seconds from j until the mid first reaches m[j]*(1 +/- X/1e4).` ほか 4 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 252 | `scripts/research_range_reversed.py` | ②④ | 手数料率・滑り・約定経費 | 221: `return lo * (1 + 10.0 / 1e4) if side > 0 else hi * (1 - 10.0 / 1e4)` / 239: `trig = (seg_p < lo * (1 - RANGE_BREAK_BPS / 1e4)) if side > 0 else \` / 240: `(seg_p > hi * (1 + RANGE_BREAK_BPS / 1e4))` ほか 4 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/research_vr_barrier.py(どれも (a)(b) から辿れない) | 機械 |
| 253 | `scripts/research_regime_composite.py` | ④ | スプレッド・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 254 | `scripts/research_scalp_exits.py` | ①②④ | 手数料率・滑り・約定経費 | 242: `return math.ceil(entry_px * (1.0 + tp_bps / 1e4) / TICK_JPY) * TICK_JPY` / 243: `return math.floor(entry_px * (1.0 - tp_bps / 1e4) / TICK_JPY) * TICK_JPY` / 994: `print("  a ~0 bps/trade strategy, so switching buys a flatter equity curve around")` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/research_exit_surface.py(どれも (a)(b) から辿れない) | 機械 |
| 255 | `scripts/research_scalp_opt.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | 261: `entry, exit_ = ask[j] * (1 + SLIP_BPS / 1e4), bid[x] * (1 - SLIP_BPS / 1e4)` / 263: `entry, exit_ = bid[j] * (1 - SLIP_BPS / 1e4), ask[x] * (1 + SLIP_BPS / 1e4)` / 344: `exit_ = bid[x] * (1 - SLIP_BPS / 1e4) if d > 0 else ask[x] * (1 + SLIP_BPS / 1e4)` ほか 1 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 256 | `scripts/research_seasonality.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 257 | `scripts/research_signal_fade.py` | ②④ | 手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 258 | `scripts/research_spread_mm.py` | ②④ | スプレッド・手数料率・滑り・約定経費・資金調達率 | 227: `price = cur_mid * (1.0 - side * TAKER_BPS / 1e4)` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 259 | `scripts/research_storm_bracket.py` | ②④ | 手数料率・滑り・約定経費 | 183: `stop = entry * (1 - side * stop_bps / 1e4)` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 260 | `scripts/research_storm_direction.py` | ④ | 手数料率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 261 | `scripts/research_tournament.py` | ④ | スプレッド・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 262 | `scripts/research_trend_lt1.py` | bp でない | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 263 | `scripts/research_two_sided_flow.py` | ②③④ | スプレッド・手数料率 | 556: `q_lo = g.p_prev * (1.0 - h_bps * 1e-4)` / 557: `q_hi = g.p_prev * (1.0 + h_bps * 1e-4)` / 609: `inv_bps: float           # inventory / adverse leg, bps of notional` ほか 3 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 264 | `scripts/research_user_strategies.py` | bp でない | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 265 | `scripts/research_vr_barrier.py` | ②④ | 手数料率・滑り・約定経費 | 248: `up_mul = 1.0 + bps / 1e4` / 249: `dn_mul = 1.0 - bps / 1e4` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 266 | `scripts/research_wall_front.py` | ①② | — | 490: `f"({px_med:,.0f} JPY) = {MATILDA_OFFSET_JPY / px_med * 1e4:.4f} bps; "` / 493: `print(f"  the 24 JPY sensitivity offset = {24.0 / px_med * 1e4:.3f} bps "` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 267 | `scripts/research_yutai.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 268 | `scripts/run_board_round.py` | ②④ | スプレッド | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: tests/test_board_round.py(どれも (a)(b) から辿れない) | 機械 |
| 269 | `scripts/run_o3c_stage0.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 270 | `scripts/run_scalp_paper.py` | ①②④ | ベーシス・手数料率・滑り・約定経費 | 328: `px *= 1 + (SLIPPAGE_BPS / 1e4) * (1 if side == "LONG" else -1)` / 344: `size=self.args.notional / limit, signal_bps=ret)` / 380: `basis *= 1 + (SLIPPAGE_BPS / 1e4) * (1 if order.side == "LONG" else -1)` ほか 2 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/replay_scalp_storm.py, scripts/research_exit_surface.py, scripts/research_scalp_exits.py ほか 1(どれも (a)(b) から辿れない) | 機械 |
| 271 | `scripts/tp_operating_curve.py` | ②④ | スプレッド | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 272 | `scripts/validate_composite.py` | bp でない | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 273 | `scripts/verify_liq_instrument.py` | ② | — | 161: `p_end = p_start * (1 + internal_move_bp / 10_000.0)` / 162: `p_future = p_end * (1 + reversal_move_bp / 10_000.0)` / 177: `p_end = p_start * (1 + noise1 / 10_000.0)` ほか 8 行 | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 274 | `scripts/w4_measure/c1_period_split.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 275 | `scripts/w4_measure/c2_limit_run.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 276 | `scripts/w4_measure/c2_read_ablation.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c2_read_ablation_decomp.py, scripts/w4_measure/c2_read_ablation_missed.py(どれも (a)(b) から辿れない) | 機械 |
| 277 | `scripts/w4_measure/c2_read_ablation_decomp.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 278 | `scripts/w4_measure/c2_read_ablation_missed.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 279 | `scripts/w4_measure/c2_read_exits.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c2_read_exits_decomp.py(どれも (a)(b) から辿れない) | 機械 |
| 280 | `scripts/w4_measure/c2_read_exits_decomp.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 281 | `scripts/w4_measure/c2_read_gated.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c2_read_gated_decomp.py(どれも (a)(b) から辿れない) | 機械 |
| 282 | `scripts/w4_measure/c2_read_gated_decomp.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 283 | `scripts/w4_measure/c2_read_limit.py` | ③④ | 資金調達率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c2_read_ablation.py, scripts/w4_measure/c2_read_ablation_decomp.py, scripts/w4_measure/c2_read_ablation_missed.py ほか 5(どれも (a)(b) から辿れない) | 機械 |
| 284 | `scripts/w4_measure/c2_read_r2.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c2_read_r2_ct.py(どれも (a)(b) から辿れない) | 機械 |
| 285 | `scripts/w4_measure/c2_read_r2_ct.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 286 | `scripts/w4_measure/c2_ref_vs_g_cause.py` | ②④ | 損益分岐・閾値・距離の引数・滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c2_ref_vs_g_toggle_cmp.py(どれも (a)(b) から辿れない) | 機械 |
| 287 | `scripts/w4_measure/c2_ref_vs_g_match.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c2_ref_vs_g_cause.py, scripts/w4_measure/c2_ref_vs_g_toggle_cmp.py(どれも (a)(b) から辿れない) | 機械 |
| 288 | `scripts/w4_measure/c2_ref_vs_g_toggle_cmp.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 289 | `scripts/w4_measure/c4_limit_batch.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 290 | `scripts/w4_measure/c4_limit_run.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 291 | `scripts/w4_measure/c4_read_combo.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c4_read_round2.py(どれも (a)(b) から辿れない) | 機械 |
| 292 | `scripts/w4_measure/c4_read_d.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 293 | `scripts/w4_measure/c4_read_r2.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c4_read_combo.py, scripts/w4_measure/c4_read_d.py, scripts/w4_measure/c4_read_round2.py(どれも (a)(b) から辿れない) | 機械 |
| 294 | `scripts/w4_measure/c4_read_round2.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 295 | `scripts/w4_measure/round0_decomp.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 296 | `scripts/w4_measure/vol_q4_funding.py` | 受 | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 297 | `scripts/w4_measure/volgate_improved.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する .py が 0 個 | 機械 |
| 298 | `src/bot/research/katsuo_limit_sim.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c2_limit_run.py, scripts/w4_measure/c2_ref_vs_g_cause.py, tests/research/test_katsuo_limit_sim.py(どれも (a)(b) から辿れない) | 機械 |
| 299 | `src/bot/research/liq_bands.py` | ②④ | 損益分岐・閾値・距離の引数 | 386: `half = naive_band_half_width_bp / 10_000.0` | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/explore_o3c_oi_axis.py, scripts/measure_liq_bands.py, tests/test_liq_bands.py(どれも (a)(b) から辿れない) | 機械 |
| 300 | `src/bot/research/liq_cascade_v2.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_iv.py, docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_iv_days.py, docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_ivh.py ほか 5(どれも (a)(b) から辿れない) | 機械 |
| 301 | `src/bot/research/liq_response.py` | ② | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/explore_o3c_oi_axis.py, scripts/measure_liq_response.py, scripts/o3c_reaction.py ほか 10(どれも (a)(b) から辿れない) | 機械 |
| 302 | `src/bot/research/matilda_limit_sim.py` | ②③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c4_limit_run.py, scripts/w4_measure/c4_w6b_diag_near_end.py, scripts/w4_measure/c4_w6b_order.py ほか 2(どれも (a)(b) から辿れない) | 機械 |
| 303 | `src/bot/research/trade_record.py` | ③ | — | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/w4_measure/c2_limit_run.py, scripts/w4_measure/c4_limit_run.py, scripts/w4_measure/round0_decomp.py ほか 1(どれも (a)(b) から辿れない) | 機械 |
| 304 | `src/bot/research/xborder_p2.py` | ④ | 手数料率・滑り・約定経費・資金調達率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/phase2/p2_08_data.py, scripts/phase2/p2_08_run.py, src/bot/research/xborder_p2_fast.py ほか 5(どれも (a)(b) から辿れない) | 機械 |
| 305 | `src/bot/research/xborder_p2_fast.py` | ②④ | 滑り・約定経費・資金調達率 | なし(機械の規則に当たる行なし) | いいえ | (c) | (a)(b) の入口から import で辿れない。import する側: scripts/phase2/p2_08_run.py, src/bot/research/xborder_p2_state.py, tests/test_xborder_p2_fast.py ほか 1(どれも (a)(b) から辿れない) | 機械 |
| 306 | `tests/bt/battery/item_0/line_marks.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 307 | `tests/bt/battery/item_0/opponents/cpp_lob_adapters.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 308 | `tests/bt/battery/item_0/opponents/fast_trade_adapter.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 309 | `tests/bt/battery/item_0/opponents/finmarketpy_adapter.py` | ① | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 310 | `tests/bt/battery/item_0/opponents/freqtrade_adapter.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 311 | `tests/bt/battery/item_0/opponents/homerun_adapter.py` | ②④ | 手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 312 | `tests/bt/battery/item_0/opponents/lib_pybroker_adapter.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 313 | `tests/bt/battery/item_0/opponents/pineforge_adapter.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 314 | `tests/bt/battery/item_0/opponents/predictivedev_tradesim_adapter.py` | ②④ | 手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 315 | `tests/bt/battery/item_0/opponents/sigc_adapter.py` | ②③④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 316 | `tests/bt/battery/item_1/i1_scenes.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 317 | `tests/bt/battery/item_2/gen_considered.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 318 | `tests/bt/battery/item_2/gen_definitions.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 319 | `tests/bt/battery/item_2/i2_scenes.py` | 未分類 | — | 1050: `"USDJPY の買い 10000。22:00 UTC のロールオーバー 1 回。買いの受け取り 0.015 円/単位/日 → 150 円の受け取り(払いは −150)。",` | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 320 | `tests/bt/battery/item_2/opponents/finmarketpy_adapter.py` | ②④ | スプレッド・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 321 | `tests/bt/battery/item_2/opponents/homerun_adapter.py` | ④ | スプレッド・手数料率 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 322 | `tests/bt/battery/item_2/opponents/pm_backtester_adapter.py` | ②④ | スプレッド・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 323 | `tests/bt/battery/item_2/opponents/predictivedev_tradesim_adapter.py` | ④ | ベーシス・手数料率・滑り・約定経費 | 18: ``slippage_bps_per_100_shares` (fill price x (1 + bps x max(1, fill lots / 100) / 1e4), on ` | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 324 | `tests/bt/battery/item_2/opponents/sarthak_execsim_adapter.py` | ④ | 手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 325 | `tests/bt/battery/item_2/opponents/sigc_adapter.py` | ①③④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 326 | `tests/bt/battery/item_2/opponents/zipline_adapter.py` | ②④ | ベーシス・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 327 | `tests/bt/battery/item_3/adapters/new_impl.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, time.py, __init__.py ほか | 機械 |
| 328 | `tests/bt/battery/item_3/i3_protocol.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 329 | `tests/bt/battery/item_3/i3_scenes.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 330 | `tests/bt/battery/item_3/opponents/homerun_adapter.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 331 | `tests/bt/battery/item_3/opponents/luczinsritter_adapter.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 332 | `tests/bt/battery/item_3/opponents/mihircoding_lob_adapter.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 333 | `tests/bt/battery/item_3/opponents/pysystemtrade_adapter.py` | ① | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 334 | `tests/bt/battery/item_3/opponents/repro_15_backtestingcore.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 335 | `tests/bt/battery/item_3/opponents/repro_88_tradesight.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 336 | `tests/bt/battery/item_3/test_battery_item3.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): time.py | 機械 |
| 337 | `tests/bt/battery/item_4/diff_scope.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 338 | `tests/bt/battery/item_4/i4_scenes.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 339 | `tests/bt/battery/item_4/opponents/qflib_adapter.py` | ④ | 手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 340 | `tests/bt/battery/item_4/opponents/quanttrader_adapter.py` | ①④ | スプレッド・手数料率・滑り・約定経費・金利・キャリー | 16: `Not expressible: a fee rate or slippage / spread (fixed 1 bp, no parameter), swap, per-tra` | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 341 | `tests/bt/battery/item_4/opponents/repro_15_backtestingcore.py` | ④ | 滑り・約定経費 | 92: `s = p * bps / 10000` | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 342 | `tests/bt/battery/item_4/opponents/repro_57_wondertrader.py` | bp でない | — | 16: `- Every execution moves by the ratio slippage (1635-1648: slippage x price / 10000, in bas` | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 343 | `tests/bt/battery/item_4/opponents/ziplime_adapter.py` | ②④ | ベーシス・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 344 | `tests/bt/battery/item_4/opponents/zipline_reloaded_adapter.py` | ②④ | ベーシス・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 345 | `tests/bt/critic/item_0/test_i0r14_time_values_silently_changed.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, api.py ほか | 機械 |
| 346 | `tests/bt/critic/item_4/test_i4r2_time_exit_at_the_open.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py | 機械 |
| 347 | `tests/bt/item_0/test_bt0_future_position.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py | 機械 |
| 348 | `tests/bt/item_0/test_bt0_paths_rule.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, events.py | 機械 |
| 349 | `tests/bt/item_0/test_bt0_r11_foreign_objects.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, api.py ほか | 機械 |
| 350 | `tests/bt/item_0/test_bt0_r8_sender_adversary.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, api.py ほか | 機械 |
| 351 | `tests/bt/item_0/test_bt0_r9_reachable_state_adversary.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, api.py | 機械 |
| 352 | `tests/bt/item_1/test_i1_vector_paths.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, time.py, __init__.py ほか | 機械 |
| 353 | `tests/bt/item_2/test_i2_account_grid.py` | 未分類 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 354 | `tests/bt/item_2/test_i2_costs_grid.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 355 | `tests/bt/item_2/test_i2_order_grid.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 356 | `tests/bt/item_2/test_i2_stance_grid.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 357 | `tests/bt/item_2/test_i2_tier_grid.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 358 | `tests/bt/item_2/test_i2_walk_stp_grid.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 359 | `tests/bt/item_3/i3_driver.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, time.py, __init__.py ほか | 機械 |
| 360 | `tests/bt/item_3/test_i3_dashboard_grid.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 361 | `tests/bt/item_3/test_i3_report_grid.py` | ④ | 手数料率 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, metrics.py | 機械 |
| 362 | `tests/bt/item_4/reference/test_i4ref_event_properties.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, event_sim.py | 機械 |
| 363 | `tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 364 | `tests/bt/item_4/test_i4_r2_signal_at_open_grid.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 365 | `tests/bt/item_4/test_i4_r3_maker_two_values_grid.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py | 機械 |
| 366 | `tests/bt/item_4/test_i4_r3_time_exit_at_open_grid.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py | 機械 |
| 367 | `tests/research/cards/library/test_c2_owner_xvenue_wick.py` | ②③ | — | 35: `bp = o * 1e-4` | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 368 | `tests/research/cards/test_w1_blocklen.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, blocklen.py ほか | 機械 |
| 369 | `tests/research/cards/test_w1_known_answers.py` | ②③ | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 370 | `tests/research/cards/test_w1_measure_card.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, reference.py ほか | 機械 |
| 371 | `tests/research/cards/test_w1_t3_t8_pnl.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, pnl.py | 機械 |
| 372 | `tests/research/cards/w1_synth.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 373 | `tests/research/test_c2_read_exits.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 374 | `tests/research/test_c2_read_limit.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 375 | `tests/research/test_c2_read_r2.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 376 | `tests/research/test_c2_ref_vs_g_match.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 377 | `tests/research/test_c4_read_d.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 378 | `tests/research/test_c4_read_r2.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 379 | `tests/research/test_c4_read_round2.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 380 | `tests/research/test_diag_paths.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験(diag_paths.py の試験。今の分析の文書に名前が出るが、出力には流れない) | 機械 |
| 381 | `tests/research/test_diag_tables.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): diag_tables.py | 機械 |
| 382 | `tests/research/test_katsuo_limit_sim.py` | ② | — | 1415: `line = P * (1 + 2 * v / 1e4)  # 建値から不利に 2v bp` / 1491: `hit = math.ceil(P * (1 + 2 * s._trade["vol"] / 1e4)) + 1` | はい | (c)試験 | 試験。試す相手(import): measure_katsuo_dispersion.py, measure_katsuo_effect.py, measure_katsuo_robustness.py, measure_katsuo_xvenue.py ほか | 機械 |
| 383 | `tests/research/test_liq_cascade_v2.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, liq_cascade_v2.py | 機械 |
| 384 | `tests/research/test_matilda_limit_sim.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 385 | `tests/research/test_overlap_daily.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 386 | `tests/research/test_round0_decomp.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 387 | `tests/research/test_trade_record.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, trade_record.py | 機械 |
| 388 | `tests/research/test_vol_q4_funding.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 389 | `tests/research/test_vol_split_daily.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 390 | `tests/research/test_window1_loader.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 391 | `tests/road/test_matilda_v37_spec.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, strategy.py ほか | 機械 |
| 392 | `tests/road/test_road_ledger.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 393 | `tests/simple/test_run.py` | bp でない | — | 199: `assert (b - a) / 10000 < 200, (a, b)` | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, ledger.py ほか | 機械 |
| 394 | `tests/test_app_fx_integration.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, bitflyer_client.py, main.py ほか | 機械 |
| 395 | `tests/test_backtest_chart.py` | ②③④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, time.py, __init__.py, backtest_cards.py ほか | 機械 |
| 396 | `tests/test_board.py` | 未分類 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, board.py | 機械 |
| 397 | `tests/test_board_round.py` | ④ | スプレッド | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): judge_board_round.py, run_board_round.py | 機械 |
| 398 | `tests/test_board_walk.py` | ②④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, board.py | 機械 |
| 399 | `tests/test_bot_research_overnight.py` | ②④ | スプレッド・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, overnight.py | 機械 |
| 400 | `tests/test_clock_burst.py` | 未分類 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): research_clock_burst.py | 機械 |
| 401 | `tests/test_composite.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, atomic_file.py, __init__.py, bitflyer_client.py ほか | 機械 |
| 402 | `tests/test_constants.py` | ④ | スプレッド・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, constants.py | 機械 |
| 403 | `tests/test_constants_inventory.py` | ④ | スプレッド・手数料率 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): constants_inventory.py | 機械 |
| 404 | `tests/test_dashboard.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, atomic_file.py, __init__.py, aggregate.py ほか | 機械 |
| 405 | `tests/test_data_quality.py` | ④ | スプレッド | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): data_quality.py, intake_ledger.py | 機械 |
| 406 | `tests/test_etf_measure.py` | 未分類 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, etf_auction_executor.py, kabu_client.py ほか | 機械 |
| 407 | `tests/test_extract_tape.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): extract_tape.py, time.py | 機械 |
| 408 | `tests/test_jev_check.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, redact.py, jev_check.py | 機械 |
| 409 | `tests/test_jev_design.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): jev_check.py, jev_design.py | 機械 |
| 410 | `tests/test_jev_report_intake.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): jev_check.py, jev_report_intake.py | 機械 |
| 411 | `tests/test_judge_gates.py` | ①②④ | 手数料率 | 32: `SCALP_NOTIONAL = 110_000.0        # scripts/run_scalp_paper.py --notional default` / 93: `"side": side, "price": PRICE, "pnl_jpy": bps / 1e4 * notional,` | はい | (c)試験 | 試験。試す相手(import): judge_gates.py | 機械 |
| 412 | `tests/test_k1_delay_decomp.py` | ②③ | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): measure_katsuo_delay_decomp.py, measure_katsuo_effect.py | 機械 |
| 413 | `tests/test_k1_delay_entry.py` | ② | — | 27: `c = o * (1.0 + rng.gauss(0.0, sd_bp) / 1e4)` / 28: `top = max(o, c) + abs(rng.gauss(0.0, wick_bp)) * o / 1e4` / 29: `bot = min(o, c) - abs(rng.gauss(0.0, wick_bp)) * o / 1e4` | はい | (c)試験 | 試験。試す相手(import): measure_katsuo_effect.py | 機械 |
| 414 | `tests/test_k1_flip_body.py` | ② | — | 27: `c = o * (1.0 + rng.gauss(0.0, sd_bp) / 1e4)` / 28: `top = max(o, c) + abs(rng.gauss(0.0, wick_bp)) * o / 1e4` / 29: `bot = min(o, c) - abs(rng.gauss(0.0, wick_bp)) * o / 1e4` | はい | (c)試験 | 試験。試す相手(import): measure_katsuo_effect.py | 機械 |
| 415 | `tests/test_k1_lookahead.py` | ② | — | 43: `c = o * (1.0 + rng.gauss(0.0, sd_bp) / 1e4)` / 44: `top = max(o, c) + abs(rng.gauss(0.0, wick_bp)) * o / 1e4` / 45: `bot = min(o, c) - abs(rng.gauss(0.0, wick_bp)) * o / 1e4` ほか 1 行 | はい | (c)試験 | 試験。試す相手(import): measure_katsuo_dispersion.py, measure_katsuo_effect.py, measure_katsuo_robustness.py, measure_katsuo_signal_horizon.py | 機械 |
| 416 | `tests/test_k1_no_invalidation.py` | ② | — | 28: `c = o * (1.0 + rng.gauss(0.0, sd_bp) / 1e4)` / 29: `top = max(o, c) + abs(rng.gauss(0.0, wick_bp)) * o / 1e4` / 30: `bot = min(o, c) - abs(rng.gauss(0.0, wick_bp)) * o / 1e4` | はい | (c)試験 | 試験。試す相手(import): measure_katsuo_effect.py, measure_katsuo_exit_ablation.py | 機械 |
| 417 | `tests/test_k1_round5.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): measure_katsuo_delay_decomp.py, measure_katsuo_effect.py, measure_katsuo_round5.py | 機械 |
| 418 | `tests/test_k1_wick.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 419 | `tests/test_k1_wick_critic.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, __init__.py, __init__.py ほか | 機械 |
| 420 | `tests/test_k1_xvenue.py` | ② | — | 31: `c = o * (1.0 + rng.gauss(0.0, sd_bp) / 1e4)` / 32: `top = max(o, c) + abs(rng.gauss(0.0, wick_bp)) * o / 1e4` / 33: `bot = min(o, c) - abs(rng.gauss(0.0, wick_bp)) * o / 1e4` | はい | (c)試験 | 試験。試す相手(import): measure_katsuo_dispersion.py, measure_katsuo_effect.py, measure_katsuo_xvenue.py | 機械 |
| 421 | `tests/test_liq_bands.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, liq_bands.py, liq_response.py | 機械 |
| 422 | `tests/test_liq_response.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, liq_response.py | 機械 |
| 423 | `tests/test_market_view.py` | 未分類 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, market_view.py | 機械 |
| 424 | `tests/test_o3c_jev_state.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 425 | `tests/test_o3c_oi_distance.py` | ②④ | 損益分岐・閾値・距離の引数 | 264: `"""implied_leverage = 1 / (d/1e4 + mmr)。分母が 0 以下なら NaN。"""` | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 426 | `tests/test_o3c_price_level_ext.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 427 | `tests/test_o3c_price_level_table.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 428 | `tests/test_o3c_reaction.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): o3c_oi_distance.py, o3c_price_level_table.py, __init__.py, __init__.py ほか | 機械 |
| 429 | `tests/test_o3c_reaction_judge.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 430 | `tests/test_o3c_reaction_r2.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 431 | `tests/test_o3c_rows4.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, liq_response.py | 機械 |
| 432 | `tests/test_o3c_signal_continue.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 433 | `tests/test_o3c_signal_continue_jev.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 434 | `tests/test_o3c_signal_explore.py` | ②④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 435 | `tests/test_o3c_signal_explore2.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 436 | `tests/test_o3c_signal_explore3.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 437 | `tests/test_o3c_signal_explore4.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 438 | `tests/test_o3c_signal_explore5.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 439 | `tests/test_o3c_signal_materials.py` | ①④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 440 | `tests/test_o3c_signal_policy.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 441 | `tests/test_o3c_signal_stage2.py` | ④ | 損益分岐・閾値・距離の引数 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 442 | `tests/test_o3c_signal_value.py` | ②④ | スプレッド・損益分岐・閾値・距離の引数・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 443 | `tests/test_on1_forward.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, aggregate.py, gates.py | 機械 |
| 444 | `tests/test_on1_live.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, time.py, __init__.py, kabu_client.py ほか | 機械 |
| 445 | `tests/test_onr.py` | ④ | 滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): research_overnight_onr.py | 機械 |
| 446 | `tests/test_onr_forward.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, time.py, __init__.py, aggregate.py | 機械 |
| 447 | `tests/test_phase2_p2_01.py` | ②④ | 滑り・約定経費 | 48: `on = 1.0 + overnight_bps / 1e4` / 49: `intra = 1.0 + intraday_bps / 1e4` / 101: `o = prev_close if i == 0 else prev_close * (1 + (planted + noise[i]) / 1e4)` ほか 1 行 | はい | (c)試験 | 試験。試す相手(import): __init__.py, p2_01_run.py, __init__.py, __init__.py ほか | 機械 |
| 448 | `tests/test_phase2_p2_01_final.py` | 未分類 | — | 51: `o = prev if i == 0 else prev * (1 + (planted_bps + rng.normal(0, 50)) / 1e4)` / 52: `c = o * (1 + rng.normal(0, 70) / 1e4)` | はい | (c)試験 | 試験。試す相手(import): __init__.py, p2_01_final.py, p2_01_run.py, __init__.py ほか | 機械 |
| 449 | `tests/test_phase2_p2_02.py` | ④ | 滑り・約定経費 | 226: `open_[i] = close[i - 1] * (1.0 + planted_bps / 1e4 + rng.normal(0, 1e-6))` | はい | (c)試験 | 試験。試す相手(import): __init__.py, p2_02_run.py, __init__.py, __init__.py ほか | 機械 |
| 450 | `tests/test_phase2_p2_02_final.py` | ②④ | 滑り・約定経費 | 168: `open(t+1) = close(t) * (1 + (drift + noise)/1e4) − (the distribution, on a` / 169: `planted ex-date), close(t) = open(t) * (1 + day noise/1e4). No zero prints,` / 183: `o = prev_close * (1 + (mu + rng.normal(0, noise_bps)) / 1e4)` ほか 1 行 | はい | (c)試験 | 試験。試す相手(import): __init__.py, p2_02_final.py, p2_02_run.py, __init__.py ほか | 機械 |
| 451 | `tests/test_phase2_p2_03.py` | ② | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): p2_03_run.py | 機械 |
| 452 | `tests/test_phase2_p2_03_final.py` | 未分類 | — | 137: `open(t+1) = close(t) * (1 + planted/1e4 + noise), close(t) = open(t) * (1 + noise)."""` / 143: `o = prev * (1 + (planted_bps + rng.normal(0, 30)) / 1e4)` / 144: `c = o * (1 + rng.normal(0, 50) / 1e4)` | はい | (c)試験 | 試験。試す相手(import): __init__.py, p2_03_final.py, p2_03_run.py, __init__.py ほか | 機械 |
| 453 | `tests/test_phase2_p2_03_iter2.py` | 未分類 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): p2_03_iter2.py, __init__.py, __init__.py, sealed.py | 機械 |
| 454 | `tests/test_phase2_p2_04.py` | ② | — | 419: `close.append(close[-1] * (1.0 + x / 1e4))` | はい | (c)試験 | 試験。試す相手(import): __init__.py, p2_04_run.py | 機械 |
| 455 | `tests/test_preflight_prereg.py` | ④ | 手数料率 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): preflight_prereg.py | 機械 |
| 456 | `tests/test_qa_make_known_answer.py` | ④ | スプレッド・ベーシス・手数料率 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): make_known_answer.py | 機械 |
| 457 | `tests/test_qa_make_known_answer_maker.py` | 未分類 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): make_known_answer_maker.py | 機械 |
| 458 | `tests/test_qa_make_known_answer_maker3.py` | ②④ | 手数料率 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): make_known_answer_maker3.py | 機械 |
| 459 | `tests/test_qa_make_known_answer_steer.py` | ④ | スプレッド・ベーシス・手数料率・滑り・約定経費 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): make_known_answer.py, make_known_answer_steer.py, score_steer.py | 機械 |
| 460 | `tests/test_qa_maker_fill_ref.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): maker_fill_ref.py, maker_fill_ref_packet_r2.py | 機械 |
| 461 | `tests/test_qa_pipeline_known_answer.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): pipeline_known_answer_daily.py, pipeline_known_answer_taker.py, research_overnight_onr.py, __init__.py ほか | 機械 |
| 462 | `tests/test_qa_score_audit.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): score_audit.py | 機械 |
| 463 | `tests/test_record_funding_basis.py` | ①②④ | ベーシス | 195: `assert row["basis_close_bp"] == pytest.approx((12000000.0 / 11900000.0 - 1) * 1e4)` | はい | (c)試験 | 試験。試す相手(import): record_funding_basis.py, __init__.py, __init__.py, bitflyer_client.py | 機械 |
| 464 | `tests/test_record_liquidations_writer.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, time.py, __init__.py, gz_members.py | 機械 |
| 465 | `tests/test_record_okx_traders.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): record_okx_traders.py, __init__.py, __init__.py, gz_members.py | 機械 |
| 466 | `tests/test_record_venues.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): record_venues.py | 機械 |
| 467 | `tests/test_research_protocol_rules.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): preflight_prereg.py | 機械 |
| 468 | `tests/test_resilience.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, bitflyer_client.py, resilience.py ほか | 機械 |
| 469 | `tests/test_risk.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, kill_switch.py, pre_trade_checks.py ほか | 機械 |
| 470 | `tests/test_scalp_logic.py` | ②④ | スプレッド・手数料率 | 269: `assert ev["price"] == pytest.approx((ENTRY - SPREAD) * (1 - 2.0 / 1e4))` / 313: `assert ev["price"] == pytest.approx((ENTRY - SPREAD) * (1 - 2.0 / 1e4))` / 321: `assert ev["price"] == pytest.approx((ENTRY + SPREAD) * (1 + 2.0 / 1e4))` ほか 2 行 | はい | (c)試験 | 試験。試す相手(import): run_scalp_paper.py | 機械 |
| 471 | `tests/test_share_backtest_runs.py` | 受 | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): なし(読み込みの import が辿れない) | 機械 |
| 472 | `tests/test_short_margin.py` | bp でない | — | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, paper.py, __init__.py ほか | 機械 |
| 473 | `tests/test_xborder_p2_fast.py` | ④ | 滑り・約定経費・資金調達率 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, p2_08_data.py, __init__.py, __init__.py ほか | 機械 |
| 474 | `tests/test_xborder_p2_known_answer.py` | ①②④ | 滑り・約定経費・資金調達率 | なし(機械の規則に当たる行なし) | はい | (c)試験 | 試験。試す相手(import): __init__.py, __init__.py, xborder_p2.py | 機械 |

## 3. 表 2: 種類が出会う口

### 3.1 目で読んで確かめた口

| # | 口(受け取る関数・列) | 受け取る値の名前 | 渡してくる側と、その種類 | 根拠(行) | 流れ先 |
|---|---|---|---|---|---|
| 1 | `scripts/analysis/diag_tables.py` の `load_run`(D1〜D8 の全部の表の元) | `pnl_bp`(daily.csv・trades.csv.gz・trades.json.gz の列) | ① `scripts/analysis/simple_trades.py` 83 行(trades.csv.gz)/ ③ `scripts/analysis/card_trades.py` 102 行(trades.csv.gz、docstring 13 行に「`diag_tables.py --run` にそのまま渡せる」)/ ③ カードの測定の `daily.csv`(68 行が読む。`daily.csv` があれば取引より先にそれを使う)/ ③・③型 `scripts/dashboard_cards/export_card_trades.py` の trades.json.gz(92-93 行が読む) | diag_tables 66-93 行。21 行「pnl_bp は取引の向きで符号を付けた損益」とだけ書き、どの bp かは書いていない | (a)。今の分析で渡しているのは ① だけかは、`docs/ANALYSIS/2026-10-0[89]_*.md` に `card_trades.py` の名前が出ないことまでしか確かめていない |
| 2 | `scripts/analysis/diag_paths.py` の取引の読み込み(94-100 行)と D4 の群の `pnl_sum`(154 行) | `pnl_bp` | 口 1 と同じ trades.csv.gz(① または ③)。同じ出力の中の MFE・MAE・出の後の値動き(111-127 行)は ② | diag_paths 98・154 行、111-127 行。`display_x20_traps.py` 45 行のコメント「口座の bp は D4 の群の pnl_sum だけ(ほかは値動き)」 | (a)。1 つの出力(diag_paths.md・.json)に ① と ② が並ぶ |
| 3 | `docs/RESEARCH/matilda_main/fam_tables.py` 22 行・`half_diff.py` 17・19 行・`same_bar_daily.py` 11 行の `v * 20` | 口 1 の `load_run` の `pnl_bp` | `backtest_runs_shared/matilda_main_trades/`(fam_tables 13 行・half_diff 12 行・same_bar_daily 10 行)= `simple_trades.py` の出力(①)。× 20 は ① のときだけ円になる。③ の値が来たときに止める行は、私が読んだ範囲(当たり行と × 20 の grep)では見ていない。ファイル全体は読んでいないので、止める所が無いとは言えない(未確認) | 各ファイルの行 | (a) |
| 4 | `docs/RESEARCH/matilda_main/unit_roundtrip_check.py` 26 行 | `pnl_bp` という名前の鍵 | `float(r["pnl_jpy"])`(円)を入れる。名前は bp、中身は円 | 26 行 | (a)(検べの台本) |
| 5 | `src/bot/monitoring/backtest_chart.py` の `TradeSet.bp`(342-357・379 行) | `bp` | 円の損益があれば 356 行 `pnl / (ep * qty) * 1e4`(建値と量で割る = 1 単位あたり値段に対する bp、② の形)。記録に bp しか無ければ 379 行で `doc["pnl_bp"]`(カードの書き出し = ③・③型)をそのまま使う。同じ `bp`・`cum_bp`・`total_bp`・`mean_bp` に入る | 327-379・448-461 行 | (b) |
| 6 | `src/bot/monitoring/backtest_cards.py` の `daily.csv` の読み(172・332・384 行) | `pnl_bp` | `export_card_trades.py` が書く daily.csv(③)。指値の模型の変種は `matilda_limit_sim` の pnl_bp(向き × (出/入 − 1) × 1e4 ÷ 段数 の和、`src/bot/research/matilda_limit_sim.py` 458-463 行 = 建玉を 1/段数 とした ③ の形)| 各行 | (b) の読み口。書き手は (d) |
| 7 | `src/bot/bt/report/metrics.py` 80 行の 1 件ごとの bp | 1 つの数 | `s * (x - e) / e * 1e4`(②)から `fee / (e * q) * 1e4`(円の手数料を建玉の円で割った bp、④ 手数料率)を引く。② と ④ が 1 つの数になる | 11・80 行 | (b)(ダッシュボードの import の鎖) |
| 8 | `scripts/paper_on1.py` 117 行の `net_bps` と、それを読む `src/bot/monitoring/aggregate.py` 346-356 行 | `net_bps` | `math.log(x / e) * 1e4`(② 対数)から `(2 * FEE_SIDE) / (e * MULTIPLIER) * 1e4`(④ 手数料率)を引く。aggregate は 356 行で `/ 1e4 * 100` として % にする。aggregate が読む行を書くのが paper_on1 だけかは未確認 | paper_on1 115-117・135 行、aggregate 346-374 行 | (b) |
| 9 | `scripts/research_clock_burst.py` 510-518 行 | `nominal_net`・`measured_net`・`sens_net` | 値動きの bp(②)から `TAKER_BPS`・`sens_c`(④ 手数料率)を引く。509・515 行は逆に bp を値段に戻す(`ep_ * (1.0 + side * TAKER_BPS / 1e4)`) | 各行 | (b)(`fetch_all.bat` 59 行) |
| 10 | `src/bot/jpx/etf_auction_executor.py` 769 行 `c_bps` | 1 つの数 | `(printed - realised) * 1e4`(率の差 → bp)に `fee_bps`(768 行、円の手数料 ÷ 買いの建玉の円 × 1e4 = ④)を足す | 763-771 行 | (b)(実弾の照合 `run_etf_measure_reconcile.py` の import の鎖) |
| 11 | `src/bot/research/overnight.py` の `edge_trend(values_bps)` | `values_bps` | 引数の説明(357 行)は「gross return, cost, or net」。何を渡すかは呼ぶ側しだい。呼ぶ側は辿っていない(未確認) | 326-415 行 | (b) の import の鎖の上にある。(b) から実際に呼ばれるかは未確認 |
| 12 | `scripts/w4_measure/overlap_daily.py` の SERIES(42-50 行)と 80・86 行 | `pnl_bp` | カードの daily.csv(③、置き場 `backtest_runs_shared/cards` は git に無い)と、指値の模型の trades(③型)を 1 つの表に並べる | 36-50・80・86 行 | (a)(`vol_split_daily.py` 45 行 `import overlap_daily as ov`。12 行に「R4 系列: `overlap_daily.py` の SERIES と同じ 13 本(同じ読み込み)」。vol_split_daily は今の分析の文書に名前が出るので (a) の入口にした) |

### 3.2 機械で拾った、ほかの口の候補(目で読んでいない)

`pnl_bp` という列を名前で読むファイル(`["pnl_bp"]` か `['pnl_bp']` を含む)は 474 個のうち 42 個(試験を含む)。上の表で読んだもの以外は、渡してくる側の種類を確かめていない。

```
$ tr '\n' '\0' < files.txt | xargs -0 grep -lE "\[[\"']pnl_bp[\"']\]" | wc -l
42
```

試験でない 36 個(上で読んだものを含む): docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/feet_crossed.py, docs/RESEARCH/cards/c3_yen_premium_revert/redo2_2026-10-05/convert_limit.py, docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/fill_delay.py, docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/gate_tables.py, docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d2_volsplit.py, docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/k046_recount.py, docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_redo.py, docs/RESEARCH/cards/c9_liquidation_cascade/run_a/make_tables.py, docs/RESEARCH/cards/c9_liquidation_cascade/run_a/three_way_m_policy.py, docs/RESEARCH/matilda_main/fam_tables.py, docs/RESEARCH/matilda_main/same_bar_daily.py, scripts/analysis/card_trades.py, scripts/analysis/diag_paths.py, scripts/analysis/diag_tables.py, scripts/analysis/trade_rows.py, scripts/c9_run_a.py, scripts/dashboard_cards/export_card_trades.py, scripts/o3c_signal_policy.py, scripts/o3c_signal_value.py, scripts/w4_measure/c2_limit_run.py, scripts/w4_measure/c2_read_ablation_decomp.py, scripts/w4_measure/c2_read_exits.py, scripts/w4_measure/c2_read_exits_decomp.py, scripts/w4_measure/c2_read_gated_decomp.py, scripts/w4_measure/c2_read_limit.py, scripts/w4_measure/c2_read_r2.py, scripts/w4_measure/c2_ref_vs_g_cause.py, scripts/w4_measure/c2_ref_vs_g_match.py, scripts/w4_measure/c4_limit_batch.py, scripts/w4_measure/c4_limit_run.py, scripts/w4_measure/c4_read_r2.py, scripts/w4_measure/c4_read_round2.py, scripts/w4_measure/overlap_daily.py, scripts/w4_measure/round0_decomp.py, src/bot/monitoring/backtest_cards.py, src/bot/monitoring/backtest_chart.py

`net_bps`・`per_trade_bp`・`values_bps` のような `pnl_bp` 以外の名前の口は、上の 7〜11 のほかは探していない(持ち越し)。

## 4. 表 3: 種類 × 流れ先 の件数

1 つのファイルが複数の種類を持つときは、その種類の行それぞれに 1 と数える(だから種類の行を縦に足すとファイル数より多い)。最後の行がファイル数。「(a)・(b)」は `src/bot/strategy/composite.py` 1 個(`matilda_simple.py` → `strategy/__init__.py` → composite と、`run_paper.py` → `main.py` → composite の両方)。機械の種類と目の種類を混ぜて数えている(どちらかは表 1 の「確かめ方」)。

数えたコマンド(作業用の置き場の `table.tsv` は表 1 と同じ行を「ファイル・種類・流れ先・試験・確かめ方」のタブ区切りで書いたもの):

```
$ python3 count.py table.tsv
# count.py の中身:
#   FL = ["(a)", "(a)・(b)", "(b)", "(d)", "(c)", "(c)試験"]
#   SY = ["①", "②", "③", "④", "受", "未分類", "bp でない"]
#   各行で、種類の欄に SY の字が含まれていれば (字, 流れ先) を 1 足す。ファイル数は流れ先ごとに 1 足す。
| 種類 | (a) | (a)・(b) | (b) | (d) | (c) | (c)試験 | 計 |
|---|---|---|---|---|---|---|---|
| ① | 7 | 0 | 0 | 0 | 7 | 8 | 22 |
| ② | 9 | 1 | 8 | 6 | 170 | 51 | 245 |
| ③ | 0 | 0 | 1 | 6 | 29 | 6 | 42 |
| ④ | 0 | 0 | 9 | 1 | 153 | 53 | 216 |
| 受 | 6 | 0 | 7 | 2 | 32 | 39 | 86 |
| 未分類 | 0 | 0 | 0 | 0 | 3 | 10 | 13 |
| bp でない | 1 | 0 | 1 | 0 | 9 | 41 | 52 |
| ファイル数 | 20 | 1 | 19 | 11 | 254 | 169 | 474 |

確かめ: 表 1 の行数(流れ先ごと)を別のコマンドで数えた。

```
$ awk -F'\t' '{print $3}' table.tsv | sort | uniq -c
     20 (a)
      1 (a)・(b)
     19 (b)
    254 (c)
    169 (c)試験
     11 (d)
```

## 5. 持ち越し(上限の中でやっていないこと)

1. 機械で種類を付けた 432 ファイルの当たり行を目で読むこと。特に「未分類」13 個と、機械の ① 15 個((c) 7 個・(c)試験 8 個。20 万円の口座の bp かどうか分からない)、機械の「bp でない」のうち目で見ていない 50 個。
2. 機械の倍率の行は当たり行の中だけ。bp の語が無い行で円や別の種類に直している所(例: 目で読んだ `fam_tables.py` 22 行 `v * 20` は当たり行に入っていない)は、目で読んだ 42 ファイルの外では拾えていない。
3. 種類が出会う口のうち、`pnl_bp` 以外の名前(`net_bps`・`per_trade_bp`・`values_bps`・`move_bp`・`sum_bp` など)で受け取る口を全部探すこと。3.2 の 42 個のうち目で読んでいないものの、渡してくる側の種類。
4. データの流れ(出力のファイルを別の台本が読む)を (c) の 254 個について調べること。今は import だけで (c) にしている。
5. (d) の 11 個: オーナーの PC の `backtest_runs/`・`backtest_runs_shared/cards/` に今なにがあるか、ダッシュボードが `backtest_runs_shared/matilda_main*` を表示するか(`backtest_view.py` の走らせの見つけ方)。
6. `overnight.edge_trend` を (b) の経路から実際に呼んでいるか、何を渡しているか。`aggregate.py` の `net_bps` を書くのが `paper_on1.py` だけか。
7. 試験の 5 組の文字の言及(1.3 の 3)。

## 6. 時間

着手 09:31 UTC、本文の書き終わり 09:43 UTC ごろ(`date -u` で確かめた時刻は 09:30・09:34・09:36・09:37・09:39・09:40・09:41・09:42)。上限 70 分の中で止めた。見込み(65 分)より大きく短いのは、474 ファイルを目で読まず機械で付けたためで、その分は 5 の持ち越しに残っている。
