# 委任先の報告(逐語、3 周目)— DELEGATION_record_form.md

## 3 周目の報告(委任文「## 3 周目」と、批評家 1 回目へのリードの応答の「直す(3 周目)」)

**結論【事実】:** リードの応答の「直す」の項目は全部直し、試験として通りました。`tests/road tests/bt` も最終のコードで全部通りました。止めて持ち越した項目はありません(上限: この 1 周)。

- コミット・押し出し・`git add` はしていません。
- core・口座・取引所の模型・フック・設定・pipeline は変えていません。この周で pipeline.py の変更はありません。
- リードが入れた `VENUE_REJECT_PREFIXES`(refused_by_account も拒否に入れる)はそのまま使っています。

### この周で変えたファイル

- `/home/user/trade/src/bot/bt/road/strategy.py`
- `/home/user/trade/src/bot/bt/road/tables.py`
- `/home/user/trade/src/bot/bt/road/check.py`
- `/home/user/trade/scripts/road/check_outputs.py`(説明の文と、足の JSON に close を足したことだけ)
- `/home/user/trade/tests/road/road_scene_strategy.py`
- `/home/user/trade/tests/road/test_road_record.py`

`docs/AUDITOR/TRACE/2026-10-07_220780c0.json` も変更ありと出ますが、私の変更ではありません。

### 直した項目ごと(変えたファイル / 足した試験)

**問 1 (1) 証拠金と比率を検査の側の定数で縛る**
- 中身: 検査は 200,000 円・0.7 を検査の側の定数 `CHECK_MARGIN_JPY` / `CHECK_USE_RATIO` で持ち、sizing の値は読みません。
- 変えたファイル: `check.py`
- 試験: `test_r3_margin_patched_outside_fails`(probe.py margin_patch と同じ場面)。記録は margin 1000000・qty 0.14 で、(v) が落ちます。

**問 1 (2) 量の計算の値段を突き合わせる**
- 中身:
  - 「直近の足の終値」の行は、土台が受けた時刻以前に閉じた最後の 1 分足の終値と比べます。
  - 「指値」の行は、指値の値段と比べます。
  - そのため足の JSON に `close` が要るようになりました。
- 変えたファイル: `check.py`、試験の `_bars`
- 試験: `test_r3_fake_size_price_fails`(fake_px と同じ場面)。「終値 5000000.0 と違う」で落ちます。

**問 1 (3) 注文の量と約定の和を突き合わせる**
- 中身:
  - `orders.qty` を pipeline の `orders.json` の量(実際に送った量)と、売買・種類も合わせて比べます。
  - 注文ごとに、知らせの届いた約定の和 = `filled_qty`、全部の約定の和 ≤ 量 を見ます。
  - fills の各行も `fills.json` と突き合わせます。
- 変えたファイル: `check.py`
- 試験: `test_r3_edited_order_record_fails`(edit_records の注文の部分)。証拠金 100000、「約定の和 0.028 が注文の量 0.014 を超える」、「orders.json の量 '0.028'」で落ちます。

**問 1 (4) 注文の USDJPY を fx の表と突き合わせる**
- 中身: 注文の USDJPY を、fx の表で土台が受けた時刻以前の最後の相場と、時刻も含めて比べます。円建ては空であることを求めます。
- 変えたファイル: `check.py`
- 試験: `test_r3_compound_rewrites_fail` の (c)(d)。

**問 1 (5) 土台を通さない取り消しを止める**
- 中身: 土台の `cancel` を通っていない取り消しへの答え(取り消した・取り消しの拒否・状態不明)が届いたら、`RoadStrategyError` で走らせを止めます。
- 変えたファイル: `strategy.py`
- 試験: `test_r3_direct_cancel_stops_the_run`(dcancel.py と同じ場面)、`test_r3_cancel_answer_without_cancel_stops`。

**問 1 の限界(戦略が合図の記録を書き換える場合)**
- 中身: 落とせません。SCHEMA の `limits` に書きました。
- 試験: `test_r3_edited_signal_times_are_not_caught`。発生 0:02・消失 0:07 に書き換えても検査の失敗は 0 件で、落ちないことを記録しています。

**問 2 値の形・時刻の順・fx の組・repro の指紋**
- 値の形:
  - 売買・種類・状態・閉じ方・量の出所・出所・liquidity が決まった値の中にあるか。
  - `value_json` が JSON として読めるか。
- 時刻の順:
  - 受けた時刻 = 出した時刻 ≤ 受け付けられた時刻 ≤ 閉じた時刻。
  - 取り消しを出した時刻 ≤ 取り消した時刻。
  - 取引所での時刻 ≤ 届いた時刻。
- 届いた順: 通し番号の順を見ます。
- fx の行が走らせの組に無ければ、黙って捨てずに落とします。
- 置き場は走らせの置き場の `road/` であることを求めます。`road/` の指紋を `../repro.json` と比べます(新しい印 (vi))。
- 変えたファイル: `check.py`、`tables.py`
- 試験:
  - `test_r3_sweep_every_field[JPY|USD|LIMIT]`(sweep.py と同じ書き換え)。repro.json を合わせない書き換えは、全部の欄で落ちます。
  - repro.json の指紋も合わせて書き換えた場合に通る欄を、そのまま試験に記録しました。SCHEMA の limits にも列挙しています。
    - signals の kind・direction・end_t_ns・end_reason
    - orders の acked_t_ns・cancel_sent_t_ns・cancel_rejected_t_ns・state_unknown_t_ns・close_reason
    - 約定の無い注文の placed_seq・closed_seq
    - どの計算にも使われていない fx の行の t_ns・rate・source
  - `test_r3_compound_rewrites_fail`(compound.py の (a)(c)(d) を、指紋を合わせた場合と合わせない場合の両方で)。どれも落ちます。
  - `test_r3_fx_row_in_unknown_group_fails`、`test_r3_store_outside_run_dir_fails`

**問 3 (1) FIFO の数え方の注意を SCHEMA.json に書く**
- 中身: SCHEMA.json に `read_from` を足しました(pipeline の trades.json・metrics の取引の数は FIFO の数え方で、道の数え方ではない)。
- 変えたファイル: `tables.py`
- 試験: `test_r3_schema_texts`

**問 4 (1)(2)(5) SCHEMA の説明の文**
- 中身:
  - 拒否の列の説明をコードに合わせました(refused_by_account・post_only_would_take を含む)。
  - 期限切れの列は「取引所が自分で閉じた時刻(期限切れ・成行の残り・reduce_only など)」としました。
  - 受け付けの列に「門の受け付けは取引所の受け付けではない」と書きました。
- 変えたファイル: `tables.py`、`strategy.py` の説明
- 試験: `test_r3_schema_texts`

**問 4 (3) 取り消しの拒否と状態不明の時刻の列**
- 中身: `cancel_rejected_t_ns`・`state_unknown_t_ns` の列を足しました。
- 変えたファイル: `strategy.py`、`tables.py`
- 試験: `test_r3_cancel_rejected_time_is_recorded`(走らせで cancel を 2 回)、`test_r3_notice_columns`

**問 4 (4) answers=new で中身が拒否のもの**
- 中身: `post_only_would_take` などを拒否の列に入れます。
- 変えたファイル: `strategy.py`
- 試験: `test_r3_notice_columns`

**問 5 flatten を決済の意図にする**
- 中身:
  - flatten は、出ている注文を取り消し、知っている建玉を決済し、後から届いた約定の知らせのぶんも、建玉 0 で注文が残らなくなるまで決済を出し続けます。
  - 決済の途中は place と flatten を止めます(`is_flattening()` で読めます)。
  - 届いた順を記録するため、土台に届いた出来事の通し番号の列を足しました:
    - `orders.placed_seq`・`closed_seq`・`flatten_pending_at_send`
    - `fills.notice_t_ns`・`notice_seq`
  - 検査 (v) は、決済の注文を受けた時の通し番号までに知らせが届いた約定で建玉を作り直します。出ていた決済の量も合わせて量を計算し直します。量の計算の行の、受けた時点の建玉も見ます。
- 変えたファイル: `strategy.py`、`tables.py`、`check.py`
- 試験: `test_r3_quick_flatten_returns_to_zero[0|90000000000]`(批評家の quick_flatten と同じ場面。知らせの遅れ 0 と 90 秒)
  - 結果: 建玉が "0" に戻り、取引は closed、段は 2、検査の失敗は 0 件です。
  - 買いの約定の知らせは 1 つずつ届くので、決済は 0.014 を 2 回出す形になります。この形は試験に書いてあります。
- 既存の試験 `test_r2_check_v_fails_when_flatten_qty_is_not_the_position` は、新しい文に合わせて期待の文だけ直しました。

**試験の書き換え前の置き場の扱い**
- 中身: 置き場の書き換えの試験(場面 4 など)は、走らせの置き場ごと写し、指紋を合わせる形(`_copy`・`_forge_repro`)に替えました。指紋の突き合わせの後ろにある検査が落ちることを見るためです。

### 批評家の台本での確かめ【事実】

`PYTHONPATH=src python …/scratchpad/critic/probe.py <名前>` ほかを、今のコードで流した結果です。
- margin_patch → 検査の失敗 2 件(v、証拠金)
- fake_px → 2 件(v、終値)
- edit_records → 6 件(v・vi。合図の時刻の書き換えだけは落ちず、限界のとおり)
- quick_flatten → 知らせの遅れ 0 でも 90 秒でも trades `('0', 'closed', '')`、検査の失敗 0 件
- dcancel.py → `RoadStrategyError 土台を通さずに出した取り消し…` で止まる
- compound.py
  - (a): 6 件
  - (b): 11 件
  - (c): 3 件(v を含む)
  - (d): 5 件
  - (e): 7 件(ii・v・vi)

### 試験の結果【事実】

- `PYTHONPATH=src python -m pytest tests/road -p no:cacheprovider` → 全部 passed
- `tests/road tests/bt` は、これまでと同じく 4 つに分けて並べて流しました(範囲は同じ、最終のコード)。CLAUDE.md §3 に従い件数は書きません。
  - `PYTHONPATH=src python -m pytest tests/road tests/bt/item_4 tests/bt/item_3 -p no:cacheprovider` → EXIT 0
  - `PYTHONPATH=src python -m pytest tests/bt/critic -p no:cacheprovider` → EXIT 0
  - `PYTHONPATH=src python -m pytest tests/bt/item_0 -p no:cacheprovider` → EXIT 0
  - `PYTHONPATH=src python -m pytest tests/bt/battery tests/bt/item_1 tests/bt/item_2 -p no:cacheprovider` → EXIT 0
  - どれも FAILED / ERROR の行は 0 です。
- モデル名の検索: `grep -rniE 'claude|opus|sonnet|haiku|anthropic|gpt' src/bot/bt/road tests/road scripts/road src/bot/bt/pipeline.py --include=*.py` → 該当なし(exit 1)。

### 止めたこと・私が決めたこと

**止めたこと:** ありません。リードの応答で直さないとした項目(問 1 の戦略の源の走査、問 3)は、問 3 (1) の文を除いて触っていません。

**仕様に無く、私が決めたこと(仮定):**
- 決済の途中に place / flatten を呼ぶと止めます。
- 指値の flatten が約定しないと、決済の途中が終わりません。今は意図をやめる口が無く、place も止まったままになります。
- 検査は、出した時刻 = 土台が受けた時刻を求めます(土台は同じ時に出す作りのため)。

**限界(SCHEMA の limits に書いたもの):**
- 量の計算の値段のうち、出所が「直近の約定の値段」「直近の板の仲値」のものは、検査に渡る記録が無いので突き合わせません。
- repro.json も書き換えられるので、最後の錨は押し出しの関門です(L-755、次の段)。
