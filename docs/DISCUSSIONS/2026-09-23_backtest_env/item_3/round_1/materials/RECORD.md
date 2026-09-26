# 項目 3 第 1 周 資料係(表)の実行の記録

## どの表が何か(mapping.tsv と同じ)

| 表 | ファイル | 行 A | 行 B |
|---|---|---|---|
| current_1 | 表_ht9ekn.md | 新実装 | 当方の現状 |
| current_2 | 表_1u9a70.md | 当方の現状 | 新実装 |
| survey_1 | 表_pz6abh.md | 新実装 | 調査結果の側(寄せた行) |
| survey_2 | 表_fe76bx.md | 調査結果の側(寄せた行) | 新実装 |
| mutant_1 | 表_fc1pn4.md | 新実装 | 試金石 |
| mutant_2 | 表_4rkq83.md | 試金石 | 新実装 |

## 走らせたもの

- 対象 15 件(`targets_list.tsv` = 新実装・当方の現状・試金石・調査結果の側 12 件(道具 10 件 + 一次資料どおりの再現 2 件))を `run_all.sh` でそれぞれ 2 回走らせた(1 回目 = `runs/`、2 回目 = `runs_2/`)。1 回の実行の中で各場面を別々のプロセスで 2 回走らせる(`run_battery.py`)。開始・終わりの時刻・所要・実行の前後の HEAD は `run_log_part1.tsv`(HEAD の記録を足す前)・`run_log_part2.tsv`・`run_log_part3.tsv`。表に使ったのは part2(試金石・当方の現状・調査結果の側 12 件)と part3(新実装)の実行で、全部 HEAD が実行の前後で同じ(3fa92f9)。
- 相手の道具の結果の再利用はしていない: 第 1 周で前の周が無い。全対象をこの周で走らせた。場面集の指紋は `fingerprint.txt`(資料係が adapter の本体を書いた後)と `fingerprint_after.txt`(表を作った後)で同じ値 1e0c4681c5cab3a7809304f1ad247cc5700906c23ea1003ab99c87d2131887f6。
- 新実装の adapter の本体を資料係が書いた(`tests/bt/battery/item_3/adapters/new_impl.py`。書く前の口だけの版に対する差分は `new_impl_adapter.diff`)。呼ぶのは `bot.bt.validation`・`bot.bt.repro`・`bot.bt.report` が `__all__` で出している名前と、`scripts/dashboard.py` の `make_handler`(127.0.0.1 の空いた口で実際に HTTP で配り、配ったものを読んで止める)、配線の試験は新実装の `tests/bt/item_3/test_i3_dashboard_wiring.py`。新実装の例外(ValidationError とその子 SealedRefused・LedgerError、ReproError とその子 NotReproducibleError、ReportError)は新実装の拒否 = Refused にした。要求が開けたままの選択(embargo は行の形で渡す・ブロック・ブートストラップの方式 circular・trade_metrics の fees 0.0(規約の往復に費用の欄が無く、新実装の口は fees を必須にしている。場面の定義は費用 0)・markout の単位 price・データの宣言・walk_forward_eval の規則)は adapter の docstring に 1 か所で書いた。この選択は作業者の `tests/bt/item_3/i3_driver.py` の選択と同じ(同じ公開の口を読むと他に選びようが無かった)。場面ごとの特別扱い・正解の読み込みは無い。この adapter は 20:32:39Z のリードのコミット ae9eb44 に入っている(`git log -- tests/bt/battery/item_3/adapters/new_impl.py`。資料係はコミットしていない)。
- 試金石(`mutant.py`)は新実装の adapter を包むだけで、本体は変えていない。表の上で試金石は 2 場面(v2-purge-embargo・v2-cpcv-split)で「不一致」、ほかの 51 場面は新実装と同じ「正解と一致」。場面集の宣言(壊れるのはこの 2 場面だけ)どおり。
- 場面集と作業者の場面の試験: `pytest_item3_r1_shiryo.out`(`tests/bt/battery/item_3 tests/bt/item_3`、215 passed)。

## 退避した実行(discarded_head_changed/)

- 試金石の最初の 1 回目の実行(20:32:19Z〜20:32:48Z)の最中の 20:32:39Z にリードのコミット ae9eb44 が入り、場面 v19-warning-all-tabs の 1 回目と 2 回目の間で、ダッシュボードの「再現性」タブの本文に埋まった git の SHA・差分のハッシュと、実行の出力ファイルのハッシュが変わって、再現の欄が「2 回で違う」になった。違いの全行は `head_changed_diff.out`。
- 走行器(`run_battery.py` → `i3_judge.stable_view`)が札に置き換えるのは鍵(git_sha・diff_hash・run_id ほか)で拾った値だけで、ダッシュボードの観測のようにタブの本文の中にだけ現れる HEAD は置き換わらない。これは場面集の側の穴(資料係は場面集を変えない)。HEAD が動かない間に走らせ直した実行(part2)を表に使い、退避した実行は `discarded_head_changed/` に残した。以後の実行は台本で前後の HEAD を記録し、全部同じだったことを確かめた。
- 新実装の part1 の実行(20:31:22Z〜20:32:19Z)はコミットの前に終わっていて違いは無かったが、HEAD の記録の無い実行だったので part3 で走らせ直した(結果は同じ: 53/53)。

## 確かめたこと

- `compare_runs.out`: 15 対象 × 53 場面 = 795 行で、1 回の実行の中の 2 回の違い 0、1 回目と 2 回目の実行(runs と runs_2)の違い 0、場面係の survey_results との違い(正しさと観測の指紋)0(新実装と試金石は survey_results に無いので比べていない)。
- `recount.out`(make_tables.py を使わない、runs/*.tsv からの数え直し): 新実装 53 / 53 が正解と一致、53 / 53 が 2 回の実行で同じ。当方の現状 6 / 53(同じ 8)、試金石 51 / 53(同じ 53)、調査結果の側を寄せた行 11 / 53(同じ 18)。観点ごとの数も `table_counts.tsv` と一致。
- `recount_from_tables.out`(表の本文のセルから数え直し): 6 枚とも各観点と計の集計の行がセルと一致。
- `md5sum_pairs.txt`: 3 組とも 2 通りの表はバイト単位で違う(どの組も「同等」にはならない)。
- `check_names.out`: 6 枚の表に、道具の名前(対象の名・adapter の名・台帳の名の語・venv の名)・時刻・日付・commit の 16 進は 0 件。表の「不一致(…)」の本文も目で見た(値と正解の数・行番号だけ)。
- 道具ごと・場面ごとの結果と理由(道具の名前つき)は `survey_breakdown.tsv`。寄せた行でどの道具を選んだかは「picked」の列。
- 表_*.md はこの周の 6 枚のほかに無かった(round_1/ には materials/ だけがあった)。`materials/stale/` への移動は無し。
