# 委任先の報告(逐語、4 周目)— DELEGATION_record_form.md

## 4 周目の報告(委任文「## 4 周目」と、批評家 2 回目へのリードの応答の「(4 周目)」)

**結論【事実】:** 「(4 周目)」の項目は全部直り、試験として通りました。`tests/road tests/bt` も最終のコードで全部通りました。止めて持ち越した項目はありません。ただ、マチルダに進む前に見ていただきたい事実が 2 つあります(下の「止めたこと・見つけた事実」の 1 と 2)。

コミット・押し出し・`git add` はしていません。core・口座・取引所の模型・pipeline・フック・設定は変えていません。

### 変えたファイル(全項目で共通)
- `/home/user/trade/src/bot/bt/road/strategy.py`
- `/home/user/trade/src/bot/bt/road/tables.py`
- `/home/user/trade/src/bot/bt/road/check.py`
- `/home/user/trade/tests/road/road_scene_strategy.py`
- `/home/user/trade/tests/road/test_road_record.py`

`docs/AUDITOR/TRACE/…json` も変更ありと出ますが、私の変更ではありません。

### 項目ごと

**(1) 問 2: limits を全部の行で確かめ直し、決済の行の `quote_ccy` も確かめる**
- `tables.py`: SCHEMA の limits を書き直しました。全部の行の全部の欄を 1 欄ずつ書き換え、repro.json の指紋も合わせた場合に通る欄を列挙しています。
  - signals: kind・direction・end_reason、消えた合図の end_t_ns、注文の無い合図の signal_id・start_t_ns
  - orders: acked_t_ns、答えの無い cancel_sent_t_ns、cancel_rejected_t_ns・state_unknown_t_ns、表の順を崩さない placed_seq、約定の無い注文の closed_seq、close_reason
  - fills: notice_t_ns・notice_seq
  - fx: source と、使われていない行の t_ns・rate
- `check.py`: 値の形の確かめを足しました。
  - 決済の行も含め、値段の通貨が JPY / USD / USDT のどれかであること。
  - 決済の種類 `exit_kind` が決まった値であること。
  - flatten の行が成行であること。
- 試験:
  - `test_r4_sweep_every_row_forged[JPY|USD|LIMIT]`: 通る欄を行の番号つきで記録し、limits に書いてあることを確かめます。
  - `test_r4_quote_ccy_form_on_exit_rows`: 'JPYx' で (iii) が落ちます。

**(1) 問 4: `expired_t_ns` を `venue_closed_t_ns` に改名**
- 中身:
  - 説明に「期限切れはここに入る(今の取引所の模型には期限つきの注文が無い)」と、改名の経緯(O-7)を書きました。
  - SCHEMA の版は road-record-4 です。
  - `flatten_pending_at_send` も close と共通になったので、`exit_pending_at_send` に改名しました。これは私の判断です(O-7: flatten の語の意味を広げないため)。
- 試験: `test_r4_venue_closed_column_renamed`
- オーナーへの報告: この名前の変更を書いてください。

**(2) A: 決済の成行が拒否されたら止める**
- 中身:
  - 決済の成行が拒否されたら、`RoadStrategyError` で止めて出し直しません。文には閉じ方と理由を入れます。
  - 拒否のほかに「約定せずに閉じた」場合も止めます。理由は、同じ時刻の出し直しの繰り返しを防ぐためです。リードの答えは拒否だけなので、これは私の判断です(仮定)。
  - 決済の成行は `cancel` もできなくしました。
- 試験: `test_r4_rejected_flatten_stops`(拒否 off_tick と、refused_by_account の 2 通り)
  - これは偽の文脈の試験です。合成の足の走らせで決済の成行を拒ませる場面は作れませんでした。flatten が成行だけになったので、批評家の off_tick(指値)の場面は今は入口で止まります。

**(2) B: `flatten` を成行だけにし、`close` を足す**
- `flatten`:
  - 指値を渡すと「flatten: 成行だけ…指値で決済するときは close を使う」で止まります。
  - 引数は `flatten(合図, "market", None)` です(種類と値段は既定値)。
- `close(合図の番号 or 「無し」, 種類, 値段)`:
  - 量 = |送る時点の建玉 + 出ている決済の注文の残り|、売買は建玉の逆です。
  - 建玉が 0、または和が 0 か建玉と逆の向きなら、出さずに「量が 0 で出さない」の行を残します。
  - 成行も指値も出せ、取り消して置き直せます。
  - 検査 (v) は、決済の種類(close / flatten / flatten_call)ごとに、知らせの届いた約定から作り直します。
- 試験:
  - `test_r4_flatten_limit_is_refused`
  - `test_r4_close_moving_line_fills_and_flat`(マチルダの利確の形): 足ごとに取り消し、答えが届いたら線を動かして置き直し、最後に約定して建玉 0 になります。
    - 置き直した close はどれも量 = 建玉の全部・出ている決済 0 で、線は毎回違います。
    - この場面は約定(trade)の足・tier 3 で回しています。理由は下の「止めたこと・見つけた事実」1 です。
  - `test_r4_close_after_two_levels`: 手計算どおりです。
    - 0:03・0:04 に 0.014 ずつ買い、0:06 に close の成行 0.028 を出します。
    - 同じ足の 2 回目の close は、出ている決済で足りているので量 0 の行(出ていた決済 -0.028)になります。
    - 取引は閉じて、段 2・損益 "0" です。
  - `test_r4_close_partial_cancel_and_replace`: 約定の量は 1 つ 0.01、tier 4。手計算どおりです。
    - 0.028 の close → 0.01 だけ約定 → 取り消し → 0.018 で置き直し → 0.01 約定 → 0.008 で置き直し → 約定で建玉 0。
    - 損益 −140 円。

**(2) C: flatten は取り消しの答えを待ってから出す**
- 中身: flatten は、出ている注文(close も)を取り消し、答え(取り消した / 約定した / 取り消しの拒否)が全部届いてから |建玉 + 出ている決済の量| を成行で出します。答えを待っているかは、戦略の側の注文の見え方の `cancel_pending` で見ています。
- 試験: `test_r4_flatten_after_doten_waits[0|90 秒]`
  - ledger は +0.014 → −0.014 → 0 で、−0.028 を通りません。
  - 取引は long closed 段 1・short closed 段 1 です。
- 既存の `test_r3_quick_flatten_returns_to_zero` の期待も直しました。今は答えを待ってから 0.028 を 1 回で出し、呼んだ記録の行が 1 つ残ります。

**(2) D: flatten の呼び出しを必ず 1 行残す**
- 中身: flatten を呼んだときに注文を出さなければ(建玉 0、または答え待ち)、flatten_call の行を 1 つ残します。中身は「量が 0 で出さない」、呼んだ時刻と合図の番号です。
- 試験: `test_r4_flatten_cancel_only_leaves_a_row`(取り消しだけの flatten)

### 試験の結果【事実】

- `PYTHONPATH=src python -m pytest tests/road -p no:cacheprovider` → 全部 passed
- `tests/road tests/bt` は、これまでと同じく 4 つに分けて並べて流しました(範囲は同じ、最終のコード)。CLAUDE.md §3 に従い件数は書きません。
  - `PYTHONPATH=src python -m pytest tests/road tests/bt/item_4 tests/bt/item_3 -p no:cacheprovider` → EXIT 0
  - `… tests/bt/critic …` → EXIT 0
  - `… tests/bt/item_0 …` → EXIT 0
  - `… tests/bt/battery tests/bt/item_1 tests/bt/item_2 …` → EXIT 0
  - どれも FAILED / ERROR の行は 0 です。
- モデル名の grep(road・tests/road・scripts/road)→ 該当なし(exit 1)。

### 批評家の台本の結果【事実】

台本はどれも `cd /home/user/trade; PYTHONPATH=src python …/scratchpad/critic/<台本>` で流しました。

- `flat.py off_tick` / `limit_far` / `limit_far_then_place` / `limit_far_cancel`:
  - どれも exit 0 で、出力は「止まった: RoadStrategyError flatten: 成行だけ(種類 market・値段 None)。指値で決済するときは close を使う: 'limit'・…」です。
  - 2 回目の「終わらない走らせ」(off_tick)は起きません。
- `flat.py doten_then_flatten …`: `flat.py` は改名前の列名 `flatten_pending_at_send` を読むので KeyError で落ちます。
  - 批評家の台本は変えず、列名だけ直した写し `…/critic/flat_r4.py` で流しました。
  - 遅れ 0・90 秒・値段が動く足のどれも、ledger は `0.014 → -0.014 → 0`、trades は `[('0','long','closed',''), ('1','short','closed','')]`、検査の失敗は 0 件です。
  - flatten_call の行(0:06、量 0.0)と、答えの後の買い 0.014 が残ります。
- `flat_r4.py flat_with_resting_limit 0 / 90 秒` → 建玉 0、検査の失敗 0 件。
- `sweep2.py JPY forge` → 「書き換えても通った: 23」、`sweep2.py USD forge` → 「26」。
  - 中身は試験 `_FORGED_PASS_ALL` に記録した一覧と同じで、全部 SCHEMA の limits に書いた欄です。
  - 2 回目に漏れていた `orders[5].quote_ccy` は、もう通りません。

### 止めたこと・見つけた事実(リードに見ていただきたい点)

止めて持ち越した項目はありません。次の 2 つが、マチルダの委任の前に見ていただきたい事実です。

1. **【事実】1 分足・tier 2 では、足ごとに取り消して置き直す指値は約定しません。**
   - 取引所の模型は、指値が置かれた時刻より後に始まる足でしか指値を当てません(`src/bot/bt/fill/venue.py` 799〜800 行 `if o.rest_since is None or start <= o.rest_since: continue`)。
   - 足が届いた時刻(= 次の足の始まり)に置いた指値が当たるのは、次の次の足です。足ごとに置き直すと、その前に取り消すことになります。
   - 試しでは、seed 1・2・3 のどれも、close を 36 回置き直して一度も約定せず、取引は open のままでした。
   - このため、マチルダの利確の形の試験は、約定(trade)の足・tier 3 で回しました。マチルダを 1 分足・tier 2 で回すときの扱いは問いです。

2. **【事実】tier 2 では、相場より不利な側の指値(買いなら上、売りなら下)が、足の値幅の外の値段で約定します。**
   - 試し: 終値の 0.99 倍の売りの指値が、その指値の値段 4936698.0 で約定しました。足の安値は 4991097 なので、値幅の外です。
   - その結果、正直な記録が検査 (iv)「約定の値段 … がその分の足の安値〜高値の外」で落ちました。
   - 取引所の模型の扱いの問題で、試験ではこの形を避けました。

### 私が決めたこと(仮定)
- flatten の成行が約定せずに閉じた場合(拒否以外)も止めます。
- 決済の成行は取り消せません。
- 列名 `flatten_pending_at_send` を `exit_pending_at_send` に変えました。
- close を出せるのは決済の途中(flatten の後)以外のときだけです。

リードの言うとおり、新しく足した口 `close` は批評家にもう 1 回見せる対象です。
