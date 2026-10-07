# 委任先の報告(逐語、5 周目)— DELEGATION_record_form.md

## 5 周目の報告(委任文「## 5 周目」と、批評家 3 回目へのリードの応答の「直す(5 周目)」2 件・(3) の説明の文 2 つ)

**結論【事実】:** 直す 2 件と説明の文 2 つは直り、試験として通りました。`tests/road tests/bt` も最終のコードで通りました。止めた項目はありません。

コミット・押し出し・`git add` はしていません。core・口座・取引所の模型・pipeline・フック・設定は変えていません。`docs/AUDITOR/TRACE/…json` が変更ありと出ますが、私の変更ではありません。

### (2-1) close と flatten を reduce_only で出す

**変えたファイル**
- `/home/user/trade/src/bot/bt/road/strategy.py`
  - `_send` に `reduce_only` を足し、close と flatten は `reduce_only=True` で出します。
  - 注文の行に `reduce_only` を記録します("true" / "false" / 出していない行は空)。
- `/home/user/trade/src/bot/bt/road/tables.py`: 列 `reduce_only` を足し、SCHEMA の版を road-record-5 にしました。
- `/home/user/trade/src/bot/bt/road/check.py`: (iii) で、決済の注文は true、place の注文は false、出していない行は空であることを確かめます。

**足した試験**(`/home/user/trade/tests/road/test_road_record.py`。場面は `/home/user/trade/tests/road/road_scene_strategy.py`)
- `test_r5_close_after_doten_does_not_open_reverse`(批評家の `close_run.py doten_after_close` と同じ形)
  - ledger は +0.014 → −0.014 で止まり、−0.028 になりません。
  - 取引は long 段 1 閉じた・short 段 1(最大 0.014)途中です。
  - close は reduce_only=true、約定 0、CANCELED、理由 "reduce_only" です。
- `test_r5_close_then_partial_exit_is_cut`(`place_sell_after_close` と同じ形)
  - close 0.028 は、取引所の模型が建玉の 0.014 に切って約定し、建玉 0 になります。
  - 取引は long 段 2 の 1 つだけで、空売りの取引はできません。
  - close の行は約定した量 0.014・CANCELED です。
- `test_r5_reduce_only_column`

### (2-5) 足で約定させた指値の約定を、約定させた足と比べる

**変えたファイル**: `check.py`
- 走らせの記録(`../record.json`)から、price のデータが bar の銘柄を読みます。
- その銘柄の maker の約定(足で約定させた指値)は、t_ns で閉じた足 [t − 60 秒, t) と比べます。比べるのは、分の区切りか、その足が 1 本だけあるか、安値以上高値以下か、です。
- 成行(taker)と、bar 以外の銘柄の約定は今のままです。

**足した試験**
- `test_r5_limit_fill_at_bar_high_passes[2|5]`(批評家の `limit_at.py` seed 2・5 hi と同じ形)
  - 約定は t_ns 0:07・maker で、値段は次の足(0:07)の高値より上です。
  - 前の検査はこれを落としていましたが、今は検査の失敗 0 件です。
- `test_r5_limit_fill_outside_the_filling_bar_fails[3-4960000.0|1-None]`(`limit_at.py 3 4960000.0` と、seed 1 below)
  - どちらも、検査 (iv) の「約定させた足(足 6、始まり …)の安値〜高値の外」の 2 件で落ちます(両側で 1 件ずつ)。

### (3) 説明の文 2 つ

**変えたファイル**: `strategy.py`(モジュールの説明の flatten の項)
1. 決済の成行が約定せずに閉じたら止めます。止める理由として「黙って出し直すより、止まって理由が出る方が測りを誤らない」と書きました。あわせて「1 分足の走らせでは門が成行を次の足まで預かるので、約定せずに閉じる形は起こせなかった。板の足の成行の残りなどで起これば走らせ全体が止まる」と書きました。
2. 「決済の成行は cancel できない(戦略が『出ている注文を全部取り消す』と書くと、決済の成行に当たったところで止まる。決済の途中かは is_flattening で読める)」と書きました。

あわせて、reduce_only で出すことと、取引所の模型が切った分は約定した量・状態・閉じ方に出ることも書きました。

- 試験: `test_r5_flatten_doc_texts`

### 試験の結果【事実】

- `PYTHONPATH=src python -m pytest tests/road -p no:cacheprovider` → 全部 passed
- `tests/road tests/bt` は、これまでと同じく 4 つに分けて並べて流しました(範囲は同じ、最終のコード)。CLAUDE.md §3 に従い件数は書きません。
  - `PYTHONPATH=src python -m pytest tests/road tests/bt/item_4 tests/bt/item_3 -p no:cacheprovider` → EXIT 0
  - `PYTHONPATH=src python -m pytest tests/bt/critic -p no:cacheprovider` → EXIT 0
  - `PYTHONPATH=src python -m pytest tests/bt/item_0 -p no:cacheprovider` → EXIT 0
  - `PYTHONPATH=src python -m pytest tests/bt/battery tests/bt/item_1 tests/bt/item_2 -p no:cacheprovider` → EXIT 0
  - どれも FAILED / ERROR の行は 0 です。
- モデル名の grep(road・tests/road・scripts/road)→ 該当なし(exit 1)。

### 批評家の台本の結果【事実】

台本はどれも `cd /home/user/trade; PYTHONPATH=src python …/scratchpad/critic/<台本>` で流しました。

**`close_run.py`**
- `doten_after_close`
  - ledger: `[('buy','0.014','0:03','0.014'), ('sell','0.028','0:05','-0.014')]`
  - trades: `[('long','1','0.014','closed'), ('short','1','0.014','open')]`
  - close は CANCELED・約定 0、検査の失敗 0
- `place_sell_after_close`
  - ledger の最後: `('sell','0.014','0:09','0')`
  - trades: `[('long','2','0.028','closed')]`
  - close は CANCELED・約定 0.014、検査の失敗 0
- `close_then_place_same_bar`: 3 回目と同じで、失敗 0
- `close_latency`: 3 回目と同じで、量 0 の行が残り、建玉は残ります。(2-2) は答えどおり今のままで、失敗 0 です。

**`limit_at.py`**

| 引数 | 約定(t_ns) | 検査の失敗 |
|---|---|---|
| `2 hi` | 5024297.5(0:07) | 0 |
| `5 hi` | 5015440.0(0:07) | 0 |
| `1 hi`・`3 hi`・`4 hi` | — | 0 |
| `3 4960000.0` | — | 2(iv、約定させた足 6 の安値 4967307.0…〜高値の外) |
| `1 below`・`2 below`・`3 below` | — | それぞれ 2(iv、約定させた足の値幅の外) |

批評家の「事実 2」(相場より不利な側の指値が値幅の外で約定する)は、検査が安定して落とすようになりました。

### 止めたこと
ありません。

### 残っている点
- (2-2) と (4) 事実 1(1 分足・tier 2 で足ごとに置き直す指値が約定しない)は、リードの答えどおり手を付けていません。
- reduce_only で取引所の模型が close を切ったり閉じたりしたときの理由("reduce_only"・"reduce_only_size_cut_filled")は、`venue_closed_t_ns`(取引所が自分で閉じた時刻)の列に入ります。

---

## リードの確かめ(10-07)

`PYTHONPATH=src python -m pytest tests/road -p no:cacheprovider` → 151 passed。批評家の台本を今のコードで流した: `close_run.py doten_after_close` → ledger +0.014 → −0.014、取引 long 段 1 閉じた・short 段 1 途中、検査の失敗 0 / `close_run.py place_sell_after_close` → 取引 long 段 2 の 1 つ、建玉 0、失敗 0 / `limit_at.py 2 hi` → 失敗 0(前は正直な記録が落ちた)/ `limit_at.py 3 4960000.0`・`1 below` → (iv)「約定させた足の安値〜高値の外」で各 2 件落ちる。
