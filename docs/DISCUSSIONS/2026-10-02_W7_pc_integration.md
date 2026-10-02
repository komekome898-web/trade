# PC への統合の手順(計画 第 5 版 W7、レーン L6)

- 調べた日時: 2026-10-02(金)14:00〜14:30 JST
- 進める先(作業ブランチの先端)= `cab6c20b`(調べている間に `ac8d6316` から 3 コミット進んだ。差は docs の 12 ファイルだけ)
- PC のブランチ = `origin/claude/bitflyer-trading-bot-hhxxaf` = `2807fdda`(`git ls-remote` で 14:2x JST に確認)
- 数は全部 `sh <scratch>/l6/pc_check.sh <SHA>` で出し直せる(読むだけで、リポジトリは変えない)。生の出力: `<scratch>/l6/pc_check_cab6c20b.out`
- `<scratch>` = `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/wf1`

---

## 0. 結論(先に書く)

**このまま PC のブランチを `cab6c20b` に進めると、PC の `git pull` が失敗して、PC には何も入らない。さらに毎朝のログ共有も止まる。**【推定(git の一次ソースによる。Windows で実行はしていない)】

- 作業ブランチには、名前に `:`(コロン)を含むファイルが **120 個**ある【事実】。PC のブランチには 0 個【事実】。
  - 112 個は `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_*/materials/runs*/`、8 個は `tests/bt/battery/item_0/survey_results/`。
  - 名前は 8 種類だけで、全部 `repro_lean52@tick+{second,minute,hour,daily}:{bar,trade}.tsv`(15 か所に同じ 8 個)。
- Windows 版 git はこの名前を扱えない。根拠:
  - git-for-windows の `compat/mingw.c` `is_valid_win32_path()` は、`core.protectNTFS` が真のとき `case ':'` を「illegal character」として 0 を返す。既定値は `PROTECT_NTFS_DEFAULT 1`(`environment.c`)【事実: 一次ソースを取得して読んだ】
  - `read-cache.c` は index に入れるときにこの検査を呼び、通らなければ `error: invalid path '%s'` で失敗させる(`add_index_entry_with_check`)【事実: 一次ソース】
  - したがって fast-forward(`git pull` は `--rebase` でも、PC 側にコミットが無いときは `merge --ff-only` で進める。`builtin/pull.c` の「we can fast-forward this without invoking rebase」)は `error: invalid path '...:bar.tsv'` で止まる【推定】
- その結果起きること【推定】:
  1. 毎晩 04:02 の `nightly_restart.bat` → `restart_all.bat` は [1/5] で止まり「FAILED: git pull」。bot は古いコードのまま動き続ける(この bat の設計では「安全な結果」なので、PC 側では誰も気づかない)。
  2. **毎朝 06:30 の `share_logs.bat` も止まる**。先に paper_logs をコミットし、その後の `git pull --rebase --autostash` が同じ理由で失敗して `exit /b 1` になり、push まで届かない。**研究環境にログが来なくなる。** こちらの方が実害が大きい。
- **つまり、ファイル名を直さないうちは PC のブランチを進めてはいけない。** 直すのはリードの判断(このレーンはファイルを変えない)。直す範囲は §2.1。

オーナーの「**バックテストの確認は未だにダッシュボードからできません**」との関係:
- PC のブランチの `scripts/dashboard.py` には「backtest」の文字が 0 回、`src/bot/monitoring/backtest_view.py` は存在しない【事実: `git show 2807fdda:scripts/dashboard.py | grep -c -i backtest` → 0】。PC のダッシュボードにバックテストのタブが無いのは、PC がまだこのコードを持っていないため。
- 統合が通ればタブは出る。ただし `cab6c20b` の時点では、タブが読む `backtest_runs/` に git が持つファイルは 0 個【事実: `git ls-files backtest_runs | wc -l` → 0】。**タブは出ても一覧は空になる**【推定】。走らせた結果を PC に届ける仕組みは、別のレーンが作業中(作業ツリーに未コミットの `scripts/share_backtest_runs.py` と `dashboard.py` の `BACKTEST_SHARED_DIR`)。それが入るまでは、オーナーの指摘には答えられていない。

---

## 1. PC のブランチを進めたとき、PC で変わること(git の差から出した)

### 1.1 量
| 項目 | 値 | 出し方 |
|---|---|---|
| コミット数 | 1193 | `git rev-list --count 2807fdda..cab6c20b` |
| ファイル | 追加 3985 / 変更 66 / 削除 8 | `git diff --name-status` |
| 追加・変更されるファイルの中身の合計 | 326,891,023 バイト(約 327 MB) | `git ls-tree -l` の大きさの和 |
| うち docs/ | 2936 ファイル・256.7 MB | 同上 |
| うち backtest_data/ | 107 ファイル・50.5 MB(`.gitattributes` で `-text`、改行は変わらない) | 同上 |
| うち tests/ | 719 ファイル・17.0 MB | 同上 |
| うち src/ | 92 ファイル・1.1 MB | 同上 |
| うち scripts/ | 56 ファイル・1.3 MB | 同上 |
| うち mlruns/ と直下の `finmarketpy.log` | 120 ファイル・0.1 MB / 0 バイト | 同上 |
| git が持ってくる量(pack) | 82,887,947 バイト(約 83 MB) | `printf 'HEAD\n^2807fdda\n' \| git pack-objects --revs --thin --stdout \| wc -c`(`ac8d6316` で測定) |

大きいもの上位: `docs/DATA/probes/20260923_tools_8_run12.log` 45 MB、同 `run16.log` 28 MB、`backtest_data/k1_newenv_a_20260927/xbtusd_1m_2017_2019.csv.gz` 20 MB、`docs/DATA/SCAN_2026-09-23_tools_cat8.md` 20 MB。

削除される 8 個: `.claude/agents/owner-auditor-candidate.md`、`.claude/agents/owner-model-auditor.md`、`.claude/hooks/owner_options_gate.sh`、`tests/test_engine_maker_exit.py`、`tests/test_maker_execution.py`、`tests/test_max_hold.py`、`tests/test_tp_sl.py`、`tests/test_wick_stop.py`。どれも PC で起動されるものではない【事実: deploy/*.bat の起動先に無い】。

### 1.2 起動される台本の差
- `deploy/` の差は **0**【事実: `git diff 2807fdda cab6c20b --stat -- deploy` が空】。起動されるもの・順番・タスクは変わらない。
- `pyproject.toml` の差は 0(依存は変わらない)【事実】。
- bat から起動される 31 本の台本のうち、中身が変わるのは 2 本【事実】:
  - `scripts/dashboard.py`(+100 行): バックテストのタブ(`/api/backtest/runs`・`/api/backtest/run/<id>`・`/backtest/run/<id>`)。読むのは `backtest_runs/`。
  - `scripts/retention_snapshot.py`: docstring の参照先の 1 行だけ。
- 起動される台本が読む `src/` の変更のうち、動きが変わるもの【事実: diff を読んだ】:
  - `src/bot/main.py`・`src/bot/market_data/feed.py`: **PAPER のときだけ、データの停滞はキルスイッチではなく一時停止になる**(建玉を最後の値段で決済 → 新しいデータだけの足が 1 本そろったら自動で再開。ファイルには書かないので再起動で解除。オーナー承認 L-544)。LIVE と他の異常は今までどおりキルスイッチ。
  - `feed.py`: **1 tick で 5% を超える値動きの検査を外した**(オーナー L-548「外す」)。
  - `src/bot/monitoring/status.py`: `status.json` に `data_stale_pause` の鍵が増える(`asdict` で全部の欄を書くので、停止していないときも `null` で出る)。
  - `src/bot/monitoring/decision_text.py`: 日本語の表示文 2 行の追加。
  - `src/bot/backtest/{engine,metrics,walk_forward}.py`: 中身を `src/bot/bt/compat/` に移した(`git grep "bot.backtest" cab6c20b -- scripts/run_paper.py scripts/dashboard.py src/bot/main.py scripts/record_*.py scripts/fetch_*.py` は 0 件【事実】。他の起動先の import は §3.2 の起動試験で通った)。
  - 新しい `src/bot/bt/`(81 ファイル)・`src/bot/strategy/k1_*.py`: バックテスト用。PC で常駐するものからは呼ばれない【推定】。

### 1.3 設定の差
- `config/config.yaml`: `market_data.max_price_jump_pct: 5.0` の 1 行が消える(上の検査を外したのに合わせたもの)【事実】。コードは `md.get(...)` で読まなくなったので、PC 側に残っていても害は無い【事実: `git grep max_price_jump cab6c20b -- src scripts config` は 0 件】。
- `config/` の他の 7 ファイルは jev・o3c の研究用(PC の常駐は読まない)【推定】。
- `.gitignore`: `!src/bot/bt/data/` と `backtest_data/k1_newenv_g_20261001/*` の除外が増える。PC の `data/` は今までどおり無視される【事実】。

### 1.4 データの量の差
- PC が作るデータ(`data/`・`logs/`・`paper_logs/`)の書き方は変わらない【事実: 記録器の台本に差が無い】。
- 増えるのはリポジトリ自体: 作業ツリー約 +327 MB、`.git` 約 +83 MB【事実(上の表)】。

### 1.5 他のレーンが作業中のもの(`cab6c20b` には入っていない。先にコミットされたら差が増える)
`git status` に、未コミットの `deploy/start_all.bat`・`deploy/fetch_all.bat`・`deploy/share_logs.bat`・`scripts/dashboard.py`・`src/bot/monitoring/{aggregate,backtest_view}.py` の変更と、未追跡の `scripts/record_{hyperliquid,okx_traders,deribit_oi}.py`・`scripts/share_backtest_runs.py` がある【事実: 14:2x JST 時点】。これが先に入ると次のことが起きる:
- `start_all.bat` が `record_hyperliquid.py --loop` と `record_okx_traders.py --loop 3600` を常駐で起動するようになる。**ところが `stop_all.bat` と `restart_all.bat` の [4/5] にはこの 2 つが無い**。毎晩の再起動でこの 2 つは止まらず、古いコードのまま動き続ける(2026-09-09 の清算記録器と同じ型)。今の作業ツリーで、既存の試験 `tests/test_record_liquidations.py::test_every_launched_component_is_also_stopped_and_verified` が **落ちる**【事実: `AssertionError: stop_all が record_hyperliquid.py を止めない`】。
- 未追跡の台本を入れずに `start_all.bat` だけをコミットすると、PC はない台本を 1 時間ごとに起動しようとして失敗し続ける【推定】。

---

## 2. Windows で壊れうる箇所(根拠つき)

| # | 箇所 | 判定 | 根拠 |
|---|---|---|---|
| 1 | **名前に `:` を含む 120 ファイル** | **壊れる。pull 自体が止まる**【推定・一次ソース】 | §0。`<>"\|?*\` は 0 個、`:` だけ |
| 2 | 予約名(CON・AUX・NUL・COM1 など)・末尾の `.` や空白 | 無い【事実】 | `pc_check.sh` → reserved 0 / trailing_dot_space 0 |
| 3 | 大文字小文字だけが違う名前 | 無い【事実】 | case_collision 0 |
| 4 | 長いパス | 大丈夫【事実+推定】 | 最長は 145 文字(`docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/before_old8_and_compat_at_HEAD_fa82126_first_try_without_schema_dir.log`)。PC の置き場所 `C:\Users\ryoma\trade\`(21 文字。`nightly_restart.bat` の登録例と `paper_logs/nightly_restart.log` の `file:///C:/Users/ryoma/trade` から)を足して 166 < 260 |
| 5 | 日本語のファイル名 | 大丈夫【事実+推定】 | 追加分に 249 個ある(例 `資料_甲.md`)。PC のブランチにも既に 19 個ある(例 `docs/DISCUSSIONS/2026-09-14_instruction_adherence/01_長文脈での指示追従の劣化.md`)【事実: `git ls-tree -r -z --name-only 2807fdda \| tr '\0' '\n' \| LC_ALL=C grep -c -P '[\x80-\xFF]'` → 19】。それを含む pull は PC で毎晩通っている【事実: `paper_logs/nightly_restart.log`】。249 個も同じ扱いになる【推定】 |
| 6 | シンボリックリンク | 無い【事実】 | mode 120000 が 0 |
| 7 | bat の行・文字コード | 差が無いので変わらない【事実】 | deploy/ の差 0。§1.5 の作業中の変更が入ると、`start_all.bat` の日本語の rem 行が 1 行 → 5 行になる(作業中の差分で 4 行増える【事実】)。既存の 1 行(「清算(強制決済)ストリーム…」)の直後の `[liq-recorder] starting...` は毎晩のログに出ているので、1 行では壊れていない【事実: `paper_logs/nightly_restart.log`】。増えた行での実績は無い【未確認】 |
| 8 | 新しい import | 新しい外部ライブラリは無い【事実】 | 変更された src と 2 本の台本の import を全部抜き出した結果、外は `numpy`・`pandas`・`requests` だけで、どれも依存に入っている |
| 9 | Python の版 | PC は Python 3.14【事実: `paper_logs/liquidations.out.log` の `C:\Users\ryoma\AppData\Local\Programs\Python\Python314\`】。3.14.0rc2 で試験と起動試験が通った(§3)【事実】。PC の 3.14 の細かい版は分からない【未確認】 |
| 10 | ファイル数 | +3985(合計 12130)。展開に時間がかかる・ウイルス対策が走る【推定。測っていない】。pull は stop_all より前なので、記録器が止まる時間は延びない【事実: restart_all.bat の順番】 |
| 11 | 改行 | `backtest_data/**` と `paper_logs/**` は `-text` で変換されない【事実: .gitattributes】。それ以外の新しい文書・試験は autocrlf の設定しだいで CRLF になるが、PC で動くものは読まない【推定】 |
| 12 | `core.protectNTFS false` で逃げる | **使ってはいけない**【推定】 | 検査を外すと NTFS は `a:b.tsv` を「ファイル a の代替データストリーム b.tsv」として作るので、中身が別物になる |
| 13 | sparse-checkout で逃げる | 効かない【推定】 | 検査は index に入れるときにかかり、作業ツリーに出すかどうかとは別(`add_index_entry_with_check`) |

### 2.1 #1 を直す範囲(リード向け。このレーンは直さない)
- 名前の出どころは `tests/bt/battery/item_0/opponents/repro_lean52.py:96` の `f"tick+{r.lower()}:{one}"`(変種の名前)。それが `repro_lean52@<変種>` という対象の名前になり、`f"{t}.tsv"` でファイル名になる【事実】。
- そのファイル名を作る・読む所(`git grep` で見つけたもの): `tests/bt/battery/item_0/test_battery_item0.py:362`、`tests/bt/critic/item_0/test_i0r5_battery_opponent_grading.py:46`、`tests/bt/battery/item_0/survey_counts.py:39`(glob なので名前には依存しない)。`run_battery.py` は `--out` で渡された名前に書くだけなので、ファイル名を決めているのは呼んだ側(手で打ったコマンド)【事実: 同ファイル 4〜7 行の使い方】。item_1〜4 の `gen_considered.py` にも同じ書き方があるが、item_0 の `repro_lean52` は読まない【推定】。
- 直し方の案(どちらにするかはリードが決める):
  - (a) 対象の名前はそのままにして、ファイル名にするときだけ `:` を別の文字に置き換える(書く側と読む側の 2〜3 か所)+ `tests/bt/battery/item_0/survey_results/` の 8 個を `git mv`。
  - (b) 変種の名前そのものから `:` を外す(`repro_lean52.py` の 8 個の鍵と、それを書いた文書・判定表も変わる)。
- `docs/DISCUSSIONS/` の 112 個は記録なので、名前を変えると記録の中の参照とずれる。名前を変えるか、git から外すかもリードの判断【推定】。
- 直したら `sh pc_check.sh <新しい SHA>` で `invalid_char 0` を確かめる。

---

## 3. 反映の前にここでできる確かめ(実際に回した)

### 3.1 やり方
- 作業ツリーには他のレーンの未コミットの変更があるので、そこでは回さなかった。`git archive cab6c20b`(src・scripts・tests(tests/bt/battery を除く)・config・deploy・docs・schema・pyproject.toml・.env.example ほか)を `<scratch>/l6/headtree` に展開し、そこに使い捨ての git を作って回した(`bot.bt.repro` が `git rev-parse HEAD` を呼ぶため)。
- Python は 2 通り: この環境の 3.11.15 と、PC に合わせた 3.14.0rc2(`uv python install 3.14`、`uv pip install -e ".[dev]"`。pandas 3.0.6・numpy 2.5.3 が入った)。

### 3.2 結果
| 確かめ | 3.11 | 3.14 |
|---|---|---|
| PC で動く部分の試験(下の 17 ファイル) | 全部通過(failed 0) | 全部通過(failed 0) |
| bat から起動される台本 31 本の起動試験(`runpy.run_path(p, run_name='_smoke_')` = 本体の `if __name__ == "__main__"` は走らせず、import と最上位の行だけ実行) | — | 31 本すべて ok |

選んだ試験: `tests/test_deploy.py`、`test_market_data.py`、`test_app_fx_integration.py`、`test_resilience.py`、`test_modes.py`、`test_paper_state.py`、`test_dashboard.py`、`test_backtest.py`、`test_composite.py`、`test_retention_snapshot.py`、`test_record_liquidations.py`、`test_record_liquidations_writer.py`、`test_record_venues.py`、`test_short_margin.py`、`test_orders.py`、`test_market_view.py`、`tests/bt/item_3/test_i3_dashboard_grid.py`(main.py の TradingApp・dashboard・deploy の bat・停滞の一時停止を触る試験を `git grep` で選んだ)。

コマンド(3.14):
```
cd <scratch>/l6/headtree
PYTHONPATH=src <scratch>/l6/venv314/bin/python -m pytest -p no:cacheprovider --basetemp=<scratch>/l6/tmp/t314 tests/test_deploy.py ... tests/bt/item_3/test_i3_dashboard_grid.py
```

最初の 1 回は、展開に docs と .env.example と .git を入れ忘れて落ちた試験があった(どれも「ファイルが無い」「git の外」で、コードの欠陥ではない)。入れて回し直して failed 0。

### 3.3 ここではできないこと
- Windows の git で実際に pull すること(この環境は Linux。Linux の git は `:` を拒まない)。§0 の判定はソースを読んだ推定。
- Windows の cmd で bat を動かすこと。

---

## 4. オーナーの手順(日本時間)

### 4.1 今のまま(ファイル名を直さずに)進めた場合
- **進めないこと**(リードへ)。進めると、オーナーが何もしなくても 10/03(土)04:02 の夜間更新で pull が失敗し、06:30 のログ共有も止まる【推定】。

### 4.2 ファイル名を直してから進めた場合
- **オーナーの作業は無い。** 10/03(土)04:02 に `nightly_restart.bat` が pull → pip install → 停止 → 起動を無人で行い、06:30 に `share_logs.bat` が結果を送ってくる(P4-N・P6。どちらも登録済みで、10/02 も動いている【事実: `paper_logs/nightly_restart.log` の `nightly_restart start 2026/10/02 4:02:04.46` と 07:13 の paper logs コミット】)。
- 早く入れたいときだけ(任意): P4 の `deploy\restart_all.bat` をダブルクリック → 終わったら `deploy\share_logs.bat`。
- 手順を出す前に、リードは次を確かめる:
  1. `sh pc_check.sh <進める SHA>` で `invalid_char 0` と `fast-forward: OK`(PC は毎朝 06:30 にログを push するので、その後は PC のブランチが先に進んでいて fast-forward できない。そのときは PC のブランチを作業ブランチに取り込み直してから進める)。
  2. §1.5 の作業中の変更が入っているなら、`stop_all.bat`・`restart_all.bat` に新しい常駐 2 本が入っていて、`tests/test_record_liquidations.py` が通ること。

### 4.3 次の共有で「入った」と分かる印(どれもここから機械で読める)
1. `paper_logs/nightly_restart.log` の 10/03 の [1/5] が `Already up to date.` ではなく `Updating 2807fdda..<SHA>` と `Fast-forward` になっている。
2. 10/03 の `paper logs snapshot` コミットの親が `<進めた SHA>` かそれより後(`git log --graph origin/claude/bitflyer-trading-bot-hhxxaf`)。
3. `paper_logs/status.json` に `"data_stale_pause"` の鍵がある(今は無い【事実: `grep -c data_stale_pause paper_logs/status.json` → 0】)。
4. [5/5] の起動行が今までと同じ並びで出て、`DONE - updated and restarted.` で終わっている。
5. ダッシュボード(http://127.0.0.1:8300)にバックテストのタブが出る。ただし §0 のとおり、一覧は空の見込み【推定】。ここはオーナーが見ないと分からないので、確認を頼むなら別の回にする。

失敗の印: [1/5] の後に `error: invalid path` → `*** FAILED: git pull ***`、かつ 10/03 06:30 の paper logs コミットが届かない。

---

## 5. 戻し方

### 5.1 pull が失敗した場合(§0 の状態)
- 取得(fetch)そのものは通るので、約 83 MB は PC の `.git` に入り `origin/...` も進む。毎晩くり返し失敗するのは作業ツリーへの反映だけで、取り直しは起きない【推定】。
- PC のコードは古いまま動いている。戻すものは無い【推定: `sequencer.c` の `checkout_onto` は失敗したら autostash を戻して状態を消す。ff の場合は `merge --ff-only` が中身を書く前に止まる】。
- やることは、作業ブランチでファイル名を直して PC のブランチを進め直すだけ。PC は次の夜間更新で拾う。
- ログ共有が止まっていた間の paper_logs のコミットは PC に溜まっていて、次に pull が通った時に rebase されて push される【推定】。
- 念のため見るもの: 次の共有で `paper_logs/nightly_restart.log` に `autostash` の行や `MERGE_HEAD`・`rebase-merge` の文言が無いこと。オーナーに頼む必要が出たら、`git stash list` と `git status` の出力を貼ってもらう(手順の番号はまだ無い)。

### 5.2 pull は通ったが、部品が落ちる・動きがおかしい場合
- **PC のブランチを過去の SHA に巻き戻して強制 push しない。** PC の手元は新しい先端にいるので、`pull --rebase` は 1193 コミットを「PC だけのコミット」と見て古い先端の上に積み直そうとする【推定】。
- 戻すときは「前に進めて戻す」: リードが作業ブランチの上で、PC で動く部分だけを前の中身に戻すコミットを作る(例: `git checkout 2807fdda -- src/bot/main.py src/bot/market_data/feed.py src/bot/monitoring scripts/dashboard.py config/config.yaml`、または該当コミットの `git revert`)。それを PC のブランチに fast-forward で進め、次の夜間更新(または P4 の restart_all)で入れる。
- その間の害: paper だけなので建玉・資金への影響は無い【事実: 安全不変条件。LIVE には env と config の両方とオーナー承認が要る】。メインの bot が起動直後に落ちる場合は、1 時間ごとの `bitflyer-start-all` が起動し直し続ける【推定】。記録器は台本に差が無いので影響を受けない【事実】。
- 緊急に止めたいときは、今までどおりリポジトリ直下に `KILL` を置く。

---

## 付録: このレーンで作ったもの(全部 scratch。リポジトリは変えていない)
- `<scratch>/l6/pc_check.sh`: 進める前の機械の確かめ(読むだけ)
- `<scratch>/l6/pc_check_cab6c20b.out`: その出力(無効なパス 120 個の一覧つき)
- `<scratch>/l6/headtree/`(325 MB)、`<scratch>/l6/venv314/`(352 MB)、`<scratch>/l6/uvpy/`、`<scratch>/l6/uvcache/`: 試験用。要らなければ消してよい
- 読んだ一次ソース: `<scratch>/l6/mingw.c`(git-for-windows main)、`read-cache.c`・`unpack-trees.c`・`sequencer.c`・`pull.c`(git master)
