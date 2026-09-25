# 項目 1 第 1 周 資料係(表)の実行の記録

## どの表が何か(mapping.tsv と同じ)

| 表 | ファイル | 行 A | 行 B |
|---|---|---|---|
| current_1 | 表_t3iayt.md | 新実装 | 当方の現状 |
| current_2 | 表_e7a6km.md | 当方の現状 | 新実装 |
| survey_1 | 表_daka83.md | 新実装 | 調査結果の側(寄せた行) |
| survey_2 | 表_v1fm0q.md | 調査結果の側(寄せた行) | 新実装 |
| mutant_1 | 表_z7pngl.md | 新実装 | 試金石 |
| mutant_2 | 表_n4uatt.md | 試金石 | 新実装 |

## 走らせたもの

- 対象 17 件(`targets_list.tsv`)を、`run_all.sh` でそれぞれ 2 回走らせた(1 回目 = `runs/`、2 回目 = `runs_2/`)。1 回の実行の中で各場面を別々のプロセスで 2 回走らせる(`run_battery.py`)。開始・終わりの時刻と所要は `run_log.tsv`。
- 相手の道具の結果の再利用はしていない: 第 1 周で前の周が無い。全対象をこの周で走らせた。
- 新実装の adapter の本体を資料係が書いた(`tests/bt/battery/item_1/adapters/new_impl.py`。差分は `new_impl_adapter.diff`)。呼ぶのは `bot.bt.data` の `load`・`adjust_daily`・`universe` と `bot.bt.vector` の公開の関数だけ。`DataError` を `Refused` にする。
- 最初の実行(`logs/first_attempt_relative_root/`)は `--out` を相対 path で渡したため場面の root が相対になり、adapter が root と場面の path を結んだ相対 path をデータ層がもう一度 root に結んで、新実装の読み込みの場面 26 件が PathRefused(対応なし)になった。adapter で root を `os.path.abspath` にし(記号的な正規化だけで symlink は解かない)、全対象を絶対 path の `--out` で走らせ直した。表はこの走らせ直しから作った。
- 調査結果の側の venv のうち 4 件(item_0/backtesting・qstrader・vnpy・c105)が消えていたので、前の導入の記録と同じ版で入れ直した(`logs/reinstall_item_1_round_1_shiryo.log`: backtesting 0.6.6 / qstrader 0.3.0 / vnpy 4.4.0 / slippage は git の 6985edb124b737b0979e3f4fd49fb65ffb2bfaf3 に合わせた)。入れた道具に渡したのは場面集の合成データだけ。
- 道具ごと・場面ごとの結果と理由(道具の名前つき)は `survey_breakdown.tsv`。表の寄せた行でどの道具を選んだかは「picked」の列。

## 確かめたこと

- `compare_runs.out`: 17 対象 × 35 場面 = 595 行で、1 回の実行の中の 2 回の違い 0、1 回目と 2 回目の実行(runs と runs_2)の違い 0、場面係の survey_results との違い(正しさと要約)0(新実装と試金石は survey_results に無いので比べていない)。
- `recount.out`(make_tables.py を使わない数え直し): 新実装 35 / 35 が正解と一致。
- `recount_from_tables.out`(表の本文のセルから数え直し): 各表の集計の行と一致。
- `recount_survey.out`(寄せた行を make_tables.py を使わずに作り直した数え): 正解と一致 4、2 回の実行で同じ 10。表と一致。
- `md5sum_pairs.txt`: 3 組とも 2 通りの表はバイト単位で違う。
- `check_names.out`: 6 枚の表に道具を特定できる語・時刻は 0 件。
- `fingerprint.txt`: 場面集の指紋(委任文 §3 の式)。
- `pytest_item1_r1_shiryo.out`: 場面集の試験 79 passed / 1 failed。落ちたのは `test_new_impl_is_the_mouth_only`(adapter の本体が空であることを確かめる試験で、資料係が本体を書くと必ず落ちる。場面集の試験は資料係が変えない)。
