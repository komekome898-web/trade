# 委任先の報告(逐語、2 周目)— DELEGATION_record_form.md

## 2 周目の報告(委任文 DELEGATION_record_form.md「## 2 周目」の (a)〜(g))

コミット・押し出し・`git add` はしていません。1 周目の作業ツリーの変更の上に重ねて直しました。core・口座・取引所の模型(`bot.bt.fill.venue`)・フック・設定も変えていません。

**結論【事実】:** 終わる条件の (b)(d)(e)(f) はどれも試験として通り、`tests/road tests/bt` も最終のコードで全部通りました。これで終わりです(上限: この周まで)。

### 直したこと(答えごと)

- **(a)【事実】** 答えどおり今のまま。合図の番号は extra に入れていません。変えたのはコードの注釈の文だけです。
- **(b) 拒否と期限切れを分けた【事実】**
  - 注文の表に「拒否された時刻」の列 `rejected_t_ns` を足しました。
  - 拒否の時刻に入れるもの: `OrderRejectEvent` と、`answers == "venue"` で理由が `rejected_by_venue` で始まるもの。
  - 期限切れの時刻に入れるもの: `answers == "venue"` でそれ以外の理由のものだけ。
  - 生の列 `close_kind` / `close_reason` は残しています。
- **(d) 決済の口 `flatten(合図の番号 or 「無し」, 種類, 値段)` を足した【事実】**
  - 量 = 送る時点の建玉の絶対値です。建玉は土台が約定の知らせから持ちます。売買は建玉の逆です。
  - 注文の表に、量の出所の列 `qty_source`(「量の計算」/「建玉」)と、送る時点の建玉の列 `position_at_send` を足しました。
  - 「建玉」の行では量の計算の列が空です。
  - 試験の「全部売り」はこの口に替えました。
  - 検査 (v) は「建玉」の行について、次を見ます:
    - 量 = 送る時刻以前の約定までで帳簿のツールが出す建玉の絶対値
    - 送る時点の建玉の列 = その建玉
    - 売買が建玉の逆で、量の計算の列が空
- **(e)【事実】** 検査は今のまま。足の遅れが 0 でない走らせで (iv) が必ず落ちることを、検査の説明の文(`check.py` のモジュールの説明と `scripts/road/check_outputs.py` の説明)に書きました。足の遅れ 1 秒で実際に (iv) が落ちる試験も足しました。
- **(f)【事実】** 合図・注文・約定のどれも無い (銘柄, 側) にも、`summary` に 0 の行(閉じた取引 0・損益 "0"・途中 0)を出します。
  - `summary.json` に走らせの組の一覧 `groups` を足しました。
  - 置き場が走らせの置き場の `road/` のときは、検査が `../record.json` の銘柄 × 側と突き合わせます。

### 2 周目で変えたファイル(絶対パス)

- `/home/user/trade/src/bot/bt/road/strategy.py`: (b) の分け方、`flatten`、`position()`、建玉の持ち方、注文の行の新しい列、説明の文。
- `/home/user/trade/src/bot/bt/road/tables.py`: SCHEMA の版を `road-record-2` に上げ、`orders` に `rejected_t_ns`・`qty_source`・`position_at_send` を足しました。summary の `groups` と全部の組の行、`RANGES` も足しました。
- `/home/user/trade/src/bot/bt/road/check.py`: (v) の「建玉」の行の検査、summary の groups の検査(record.json との突き合わせ)、(e) の説明。
- `/home/user/trade/scripts/road/check_outputs.py`: 説明の文だけ。
- `/home/user/trade/tests/road/road_scene_strategy.py`: 全部売りを `flatten` に替え、mode `ladder`・`flatten_empty`・`reject`・`nothing` を足しました。
- `/home/user/trade/tests/road/test_road_record.py`: 場面 1・5 の期待を `flatten` の形に直し、下の試験を足しました。

### 足した試験(`tests/road/test_road_record.py`)

- (d) `test_r2_flatten_on_moving_bars_returns_position_to_zero`
  - 値段が動く足で、0:03 と 0:04 の買いの量が違います(0.071 と 0.072)。
  - flatten の量 = その和で、最後の建玉は "0"、取引は閉じています。検査も通ります。
- (d) `test_r2_flatten_without_position_leaves_a_zero_row`: 建玉 0 での flatten は出さず、「量が 0 で出さない」の行だけを残します。この扱いは答えに無く、place の決まりに合わせた私の判断です(仮定)。
- (d) `test_r2_check_v_fails_when_flatten_qty_is_not_the_position`: 決済の量を 0.029 に書き換えると、(v) が「建玉 0.028 の絶対値 '0.028'」と違うとして落ちます。
- (b) `test_r2_rejections_go_to_rejected_not_expired`
  - 最小の量 0.1 の銘柄に、成行と指値を出します。
  - 成行は門経由の `rejected_by_venue`、指値は `OrderRejectEvent` になります。
  - どちらも拒否の列に入り、期限切れの列は空です。
- (b) `test_r2_close_notice_columns`: 知らせ 5 通りの分け方を見ます。
  - venue と理由 expired → 期限切れ
  - venue と理由 rejected_by_venue → 拒否
  - Reject → 拒否
  - cancel → 取り消し
  - new → どの列にも入らない
- (e) `test_r2_feed_latency_fails_signal_bar_check`
- (f) `test_r2_summary_rows_for_groups_with_nothing`: 0 の行が 2 つ出ます。走らせの置き場を写して組を 1 つ消すと、(ii) が record.json と違うとして落ちます。

### 試験の結果【事実】

`PYTHONPATH=src python -m pytest tests/road/test_road_record.py -p no:cacheprovider -vv -k "r2 or scene1_signal or scene5_usd"` を流し、上の試験と場面 1・5 は全部 PASSED でした。

`tests/road tests/bt` は 1 周目と同じく、コア 4 つで xdist が無いため 4 つに分けて並べて流しました。範囲は同じで、最終のコードで流しています。CLAUDE.md §3 に従い件数は書きません。
- `PYTHONPATH=src python -m pytest tests/road tests/bt/item_4 tests/bt/item_3 -p no:cacheprovider` → EXIT 0
- `PYTHONPATH=src python -m pytest tests/bt/critic -p no:cacheprovider` → EXIT 0
- `PYTHONPATH=src python -m pytest tests/bt/item_0 -p no:cacheprovider` → EXIT 0(numpy の RuntimeWarning のみ)
- `PYTHONPATH=src python -m pytest tests/bt/battery tests/bt/item_1 tests/bt/item_2 -p no:cacheprovider` → EXIT 0

どれも FAILED / ERROR の行は無しです。

モデル名の検索: `grep -rniE 'claude|opus|sonnet|haiku|anthropic|gpt' src/bot/bt/road tests/road scripts/road src/bot/bt/pipeline.py --include=*.py` → 該当なし(exit 1)。

### 止めたこと・残したこと

- **(c) USDT【事実】:** この周では直していません。口座が `currency must be a 3-letter code, got 'USDT'` で止めるため、道の走らせで USDT は回せません。
- **(g) 口座の強制の注文(`forced-`)の試験【事実】:** この周では足していません。記録の口はありますが、試験はしていません。
- **(b) の決まりの帰結【事実】:** 門が口座の確かめで止めたもの(理由 `refused_by_account: …`、`answers=venue`)は、答えの決まりどおり期限切れの列に入ります。
- **(d) の検査が落ちる場合【推定】:**
  - 検査 (v) の「建玉」の行は、注文を受けた時刻以前で、この注文より前に出した注文の約定から建玉を作ります。道の約定の時刻(値を決めた観測の時刻)が注文を受けた時刻と同じになることがあるので、こう決めました。
  - そのため、約定の知らせが戦略に届く前に flatten を出す走らせ(知らせの遅れがある場合)では、土台の建玉と帳簿の建玉がずれて (v) に落ちえます。説明の文に書きました。
- **作業ツリーの別の変更:** `docs/AUDITOR/TRACE/2026-10-07_220780c0.json` が変更ありと出ますが、私の変更ではありません。
