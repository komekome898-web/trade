# 批評家: W6b を窓の 10 日に広げる版(コミット e01795fa)(2026-10-04)

下位モデルの批評家の出力を逐語で貼る。

---

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| コミット e01795fa の `c4_w6b_order.py` と試験の差分を、5 問で批評する(読むだけ。コードを変えない・コミットしない) | L-630「**ア**」= 事前登録 `docs/RESEARCH/WINDOW1/PREREG.md` W6b「窓を開けた後に窓の 10 日で測る」 |
| 封印の前の 6 日で `--window` なしを一時の置き場に走らせ、コミット済みの出力と比べる | 同上(窓の 10 日を測る切り替えが、6 日の版を変えないことの確かめ。封印の前の 6 日は実データだが走らせてよい、と依頼文にある) |
| 合成の置き場だけで窓の口を確かめる | 同上 |

右が空の行はありません。

## 結論

5 問とも [問題なし] です。[止める] も [直す] もありません。

守ったこと:
- 環境変数 `W4_WINDOW1` は立てていません。合成の確かめでは `CM.WINDOW1_ENV` を別名 `CRITIC_SYN_ENV` に差し替えました。
- 2024 年の約定の記録と 2023-12-18 以後の足は開いていません。
- `--window` を実データに対して走らせていません。
- `backtest_data/phase2_sealed/P2-08/` の 3 ファイルは、前後で sha256 が同じでした(事実)。

試験の末尾の行:
```
43 passed in 2.34s
```
実行: `PYTHONPATH=src python -m pytest tests/research/test_c4_w6b_order.py`

## 問 1 [問題なし] O1〜O6 と `--window` なしの出力

- **O1〜O6**(事実): `git show e01795fa^` と `e01795fa` の 1〜8 行目を diff し、同一でした(DOCSTRING_SAME)。差分の hunk は 8 行目の `# 走らせ` のコメントから始まっており、docstring は触られていません。試験 `test_docstring_starts_with_the_reading_rules_verbatim` も、委任文 `DELEGATION_w6b_order.md` の O1〜O6 の逐語と一致しています。
- **`--window` なしの出力**(事実): 封印の前の 6 日で、次のコマンドを一時の置き場に走らせました(足 700746 本)。
  ```
  PYTHONPATH=src python3 scripts/w4_measure/c4_w6b_order.py --out $S/preseal_out
  ```
  `cmp` で `TABLES.md` と `w6b.json` がコミット済みの `W6B_PRESEAL/` と 1 バイトも違いませんでした。sha256 は TABLES.md が `501c23ca…7656`、w6b.json が `ec26f1dd…0bab` で、両方一致です。
- この走らせで `explore_access_log.jsonl` は増えていません(P2-08 の 3 ファイルの sha256 が走らせの前後で同じ)。既定の経路は窓の口を呼びません。
- `--out` の既定は `None` から `OUT_DEFAULT` に落ちる作りで、値は元と同じです。

## 問 2 [問題なし] 窓の口を通らない道

読んだこと:
- `main` で約定の記録を開く前に `window_guard` を 1 回呼びます(`day_of` と `day_ns` だけが先)。`read_trade_minutes`、`md5_check`、行数を数える `gzip.open` はすべてその後です。
- 足は、区切りの終わりが 2023-12-18 より後なら `window=True` で読みます。これで 2 回目と 3 回目の区切りは `load_bars` の中の `window_guard` を通ります。1 回目(〜2023-01-01)は既定の呼び方で、`check_end` が封印の境を越えると拒みます。
- CLI の引数は `--window` と `--out` だけです。範囲を広げる引数はありません。

合成の確かめ(`scratchpad/crit_win/e2e.py`):
- `ROOT` を持つ取り込み済みモジュールを列挙し、`sys.modules` の `scripts/w4_measure` 由来は `common` と `c4_w6b_order` の 2 つだけでした。`run_v2` は取り込まれていません。
- 両方の `ROOT` を合成の置き場に差し替えました。
- `builtins.open`、`gzip.open`、`io.open` に見張りを付け、実の `data/` と `backtest_data/` を開こうとしたら即失敗するようにしました。
- 3 通りの欠けを試しました。

  | 欠けたもの | 結果 | 開いたパス | 記録 |
  |---|---|---|---|
  | 環境変数も承認も無い | 拒否 | 空 | 書かれない |
  | 環境変数だけある | 拒否 | 空 | 書かれない |
  | 承認だけある | 拒否 | 空 | 書かれない |

- 門が揃う場合の確かめでは、`load_bars` を偽物に差し替えて本物の `window_guard` を通しました。記録は 3 行で、`script` は `c4_w6b_order.py` と呼び出し元の台本名、範囲は 2024-01-01〜2024-10-02 と 2023-01-01〜2024-01-01 と 2024-01-01〜2024-10-02 でした。実の置き場を開いた形跡はありません。

試験の差し替え:
- 試験 `_synthetic_root` は `CM.ROOT` と `w.ROOT` を差し替えます。`w` が取り込む場所は `common` だけなので、実の置き場には届きません。
- 試験の中で環境変数を立てるのは `monkeypatch` 経由です。立てた状態でも、約定の記録の読み出しを止める偽物で止まり、開く前に終わります。

軽い所見(行動は求めません):
- 門は `main` にあり、`read_trade_minutes(name, table)` と `md5_check` 自体にはありません。別の台本が `table=TRADE_FILES_WINDOW` を渡して直接呼べば、門なしで開きます。今の CLI の道ではありません。
- `--out` は任意のパスを取ります。書くのは `TABLES.md` と `w6b.json` の 2 ファイルだけです。

## 問 3 [問題なし] 2024-10-02 より後・判定の期間

- 足の終わりは `WINDOW_BARS_END = 2024-10-02T00:00:00Z` の固定で、範囲は終わりを含みません。約定の記録は 2024 年の各月 1 日の 10 ファイルだけで、日の外の行があれば `read_trade_minutes` が拒みます。
- 窓の口の 3 つめの門(`hi_ns > WINDOW1[1]` で拒む)も効きます。判定の期間(2025-12-12 以後)は、道が無いうえに門でも止まります。
- 合成の確かめでは、偽の足に 2024-10-02T00:00 と 2024-12-01 を置きましたが、`lo <= t < hi` で入らず、10 日の外の足は 15 本のうち 10 日分しか数えられませんでした。
- 既存の仕組みとして、`candles_1m_2024.csv.gz` は年ごとのファイルで 2024-10-02 以後の行を含みます。`window_trim_report` が時刻の列だけを全行見て、2025-12-12 以後の行の数を記録に残します(値は見ません)。ファイルのバイトは gzip で全部展開されますが、値は範囲の外で読まれません。これはこのコミットが足した道ではありません。

## 問 4 [問題なし] 前後の小計

- `subtotals` は日ごとの `count_matches` の出力を `period_of(d)` で分け、`add_counts` で合計して作り直します。割合と Wilson は小計の数から作り直しています。これは O4 の合計(`add_counts(list(by_day.values()))`)と同じ関数です。
- `mismatch_subtotals` は O5 の日ごとの数の合計です。
- 前後は日付の比較(`day < "2024-03-28"`)で、10 日は前 3(1〜3 月)と後 7(4〜10 月)に分かれます。
- 試験で、前後の小計の合計が 10 日の合計と一致し、割合の平均ではなく数の合計であることを見ています。
- 合成の確かめ(1 日 1 件の決まらない足を 10 日分作った場合):
  - 合計は 10 で、前が 3、後が 7 でした。
  - 一致は 10 のうち 10 で、前が 3、後が 7 でした。
  - O5 の `both` は 10 で、前が 3、後が 7 でした。

## 問 5 [問題なし] 足を続けて流し、数えるのは 10 日だけ

- シミュレーターは区切りの外(ループの前)で 1 回だけ作ります。合成の確かめで `MatildaLimitSim` を差し替えて数えたところ、作られたのは 2 個(良い・悪い)だけでした。年の区切りでは作り直されません。
- `load_bars` の呼びは次の 3 回で、仕様どおり暦年の 3 区切りでした(事実)。
  - 2022-07-01〜2023-01-01 は `window=False`。
  - 2023-01-01〜2024-01-01 は `window=True`。
  - 2024-01-01〜2024-10-02 は `window=True`。
- 全部の足を、足の時刻の順に両方のシミュレーターへ `feed` します。`bars_6` に入るのは `in_days` の足だけです。`count_matches` と `count_mismatch` の数えも `in_day(i)` で絞られます。
- 合成では、`feed` に渡った足が 15 本(10 日の外の足を含む)でも、日ごとの決まらない足は各日 1 で、合計は 10 でした。10 日の外の足は流れますが数えられません。

## 付随の所見

- コミット e01795fa には `explore_access_log.jsonl` の 5 行が入っています。すべて 07:21〜07:22Z の `run_v2.py:72 ref_rows` による `load_reference` で、`binance_close/open/high/low/close` の 2025-12-11T23:30Z〜2025-12-12T00:00Z です。この台本の経路の記録ではなく、前の批評家か別の走らせの読みです。
- CLAUDE.md §7(I-001)に従い、窓を読んだ事実が `docs/OWNER_LOG.md` と `docs/OWNER_STATUS.md` に載っているかをリードが確かめてください。

## 変えた・出したファイル

`docs/RESEARCH/WINDOW1/` 以下を含め、リポジトリは変えていません。一時の置き場だけに書きました。

- `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/crit_win/e2e.py`
- `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/preseal_out/`
- `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/p208_before.sha`
- `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/ident.py`

`git status` に出る `docs/AUDITOR/TRACE/2026-10-04_220780c0.json` の変更は、私が書いたものではありません。

---

## リードの応答

- 止める・直す: なし。軽い所見(門が `main` にあり関数自体には無い)は、今の CLI の道ではないので直さない。
- 走らせた: `W4_WINDOW1=P2-08-explore PYTHONPATH=src python3 scripts/w4_measure/c4_w6b_order.py --window`(2 分 10 秒、足 1,112,194 本)。出力 `docs/RESEARCH/WINDOW1/W6B_WINDOW/`。窓の読みの記録に 7 行足された(計 12 行)。
- 付随の所見(窓を読んだ事実の記録): `docs/OWNER_STATUS.md` の L-630 の欄に追記する。
