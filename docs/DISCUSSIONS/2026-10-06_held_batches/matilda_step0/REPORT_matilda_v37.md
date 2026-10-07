<!-- 作業者の報告(直しの回)。委任文 DELEGATION_matilda_v37.md 5 版目・承認 L-810。作業者の返事の全文を、作業者の道具がファイルを書けないため、リードが写した(10-07 夜)。表の「落ちた試験」の欄は、作業者の返事の名前の並びを、リードが一字も変えずに写した(同じ並び・同じ区切り)。 -->

## 直した所(検めの指摘の 1〜4)

1. 変異の表の「落ちた試験」の欄を、全部の行で落ちた試験の名前を `tests/road/test_matilda_v37_spec.py::test_名前` の形で全部並べる書き方に直しました。区切りは「・」で、件数のまとめはやめました。
2. 着手前の表の最後の 2 行の 1 列目の文を、Q1・Q2 の行の文にそのまま入れました。
3. 委任文の「途中の決め」Q3・Q4 で足された試験に対して、U2「ボラの門を ≦ → <」と U8「bup を列の値だけにする」の 2 つの変異を、前と同じ当て方(tmp の写し)で当て直しました。2 つとも落ちたので、変異の表の 2 行を落ちた試験の名前に書き換えました。
4. `PYTHONPATH=src python -m pytest tests/road` を打ち直しました。結果は 315 passed です。

コードは直していません。commit・add・push もしていません。

## 着手前の表

右の列はどの行も、承認 L-810「**yes**」と、その行の根になる委任文の節です。

| やろうとすること | オーナーの原文の該当語(逐語)・委任文の節 |
|---|---|
| `src/bot/strategy/matilda_v37.py` を新しく作る(MatildaV37・pipeline_strategy・PARAM_KEYS・V37_ORIGINAL・entry_flag・exit_flag・exit_price) | L-810「**yes**」/「作るもの」1 |
| 17 の引数の鍵と型・範囲を確かめ、原典の値の表を持つ | L-810「**yes**」/「写し方の決まり」M1(L-776) |
| 1 分足を UTC の foot 分の窓に束ね、欠けがあれば前の窓を閉じる | L-810「**yes**」/ M2 |
| 足の知らせの後にタイマーを置き、その時に判定する。指標は閉じた窓まで、last は今の足の終値 | L-810「**yes**」/ M3 |
| 指標(ヒゲの切り落とし・expantion_flg・ボラ・レンジ・中心・ブレイクの線の列・出来高の平均・b_signal) | L-810「**yes**」/ M4(L-784) |
| 慣らし | L-810「**yes**」/ M5 |
| 玉の向きの変化と「全部取り消す」 | L-810「**yes**」/ M6(L-803) |
| ブレイクの判定と合図 b1… | L-810「**yes**」/ M7 |
| 建ての旗と合図 e1… | L-810「**yes**」/ M8 |
| 建てのはしご・段ごとの決済・置き直し・合図が消えたら全部取り消す | L-810「**yes**」/ M9(L-784・L-789・L-774・L-809) |
| 決済の旗 1・2・3、決済を置き直す向き、flatten | L-810「**yes**」/ M10(L-782・L-783・L-801) |
| ブレイクの解除 | L-810「**yes**」/ M10b |
| 土台の `place`・`place_with_exit` に `size_ref` を足し、モジュールの説明を書き足す | L-810「**yes**」/「作るもの」2・M11(L-781) |
| 検査 (v) に「取引の最初の段 <番号>」を足す | L-810「**yes**」/「作るもの」3・M11 |
| SCHEMA の size_px_source の説明の文を書き足す | L-810「**yes**」/「作るもの」4 |
| 受け入れの試験を、試験を変えずに通す | L-810「**yes**」/「受け入れ」 |
| 変異の表(tmp の写しに当てる) | L-810「**yes**」/「変異の表」 |
| H1〜H4 を確かめる | L-810「**yes**」/「変えないもの」 |
| ブレイクの旗が ±1 から ∓1 に直に変わったときの合図「ブレイク」の扱い | **(該当語なし)** → 振る舞いは選んでいない。その場面でコードが止まるようにしただけ。Q1 |
| 前の判定の取り消しの答えを待っている間に、次の判定が来たときの扱い | **(該当語なし)** → 振る舞いは選んでいない。その場面でコードが止まるようにしただけ。Q2 |

## 作ったファイル・直したファイル

- 作った: `/home/user/trade/src/bot/strategy/matilda_v37.py`
- 直した: `/home/user/trade/src/bot/bt/road/strategy.py`
  - `place(..., size_ref=None)`・`place_with_exit(..., size_ref=None)` を足した。
  - 元の行の確かめは `_size_root` に置いた(元の注文があるか・量の計算で出した指値の place の行か・元が写した行でないか・段数が同じか・今の注文が指値か)。外れたら RoadStrategyError で止まる。
  - 定数 `SIZE_REF_PREFIX`・`SIZE_REF_COLS` を足し、モジュールの説明に「量をそろえる口」を書き足した。
- 直した: `/home/user/trade/src/bot/bt/road/check.py`
  - (v) に `_check_size_ref` を足した。M11 の決まりのとおり、同じ銘柄・側、placed_seq が同じか小さい、road-N の N が小さい、元が量の計算で「取引の最初の段」で始まらない、写した 7 列が同じ、を確かめる。
  - 量の計算し直しは前のまま(写した値から)。モジュールの説明の (v) も書き足した。
- 直した: `/home/user/trade/src/bot/bt/road/tables.py`
  - size_px_source の説明の文だけ。列は変えていない。
- `git status --short src tests`(直しの回に打った出力):
```
 M src/bot/bt/road/check.py
 M src/bot/bt/road/strategy.py
 M src/bot/bt/road/tables.py
?? src/bot/strategy/matilda_v37.py
```
- TRACE の json は、着手する前の `git status` で既に変更済みでした。作業者は触っていません。
- commit・add・push・worktree はしていません。

## 試験のコマンドと出力

```
$ PYTHONPATH=src python -m pytest tests/road
315 passed in 30.42s
```
- 直しの回に打ち直しました。リードの試験 2 か所の追加(コミット 5831af98)の後です。
- 飛ばしは 0 です。作る前は `7 failed, 221 passed, 85 skipped` でした。
- `tests/road` の外の試験は全部は回せていません(未確認)。`tests/bt` は 580 秒で打ち切られました。
  - fill・core・pipeline は変えていません。
  - 土台の変更は、size_ref を渡さない呼び出しでは前と同じ道を通ります。

## H1〜H4 の確かめ

```
$ git diff --stat tests/
(出力なし。直しの回にも打った)
$ PYTHONPATH=src python -m pytest tests/road
315 passed in 30.42s
$ PYTHONPATH=src python -c "from bot.bt.road.tables import SCHEMA; import json; print({k: [c[0] for c in v['columns']] for k, v in SCHEMA['tables'].items()})" | md5sum
作る前 2a0f50cdead0023589b414f8ecda14db / 作った後 2a0f50cdead0023589b414f8ecda14db(cmp で同じ)
$ git diff --stat src/bot/bt/fill src/bot/bt/core src/bot/bt/pipeline.py
(出力なし)
```

## 変異の表

当て方(事実):
- 1 行ごとに `src/`・`tests/`・`pyproject.toml` を scratchpad に写し、1 か所だけ壊して、`python -m pytest tests/road/test_matilda_v37_spec.py` を写しの根で走らせました。本物は変えていません。最後に `git status` で確かめています。
- 走らせの記録 `bot.bt.repro.code_state` は git の HEAD を読みます。写しは git の置き場ではないので、写しの `code_state.py` の `REPO` だけを `/home/user/trade` に向けました。使うのは読むだけの rev-parse・diff・ls-files で、ふだんの試験と同じ命令です。
- 行ごとに import された `matilda_v37`・`road/strategy`・`road/check` が写しの方であることを出力で確かめました(全部の行で写し)。
- 壊さない写しは、前の回が `92 passed`、直しの回が `94 passed` でした。
- U2 のボラの門の行と U8 の bup の行は、直しの回にリードの追加後の試験で当て直しました。結果は 1 failed, 93 passed と 1 failed, 93 passed です。
- ほかの行は前の回(試験の追加の前の版)の結果です。

| 番号 | 壊した変更 | 落ちた試験 |
|---|---|---|
| U1 | M1: b_signal の真偽の型の確かめを外す | tests/road/test_matilda_v37_spec.py::test_u1_bad_params_refused[真偽の引数に数] |
| U1 | M1: 原典の値 exit_setting を 0.8 → 0.5 | tests/road/test_matilda_v37_spec.py::test_u1_param_keys_and_original_values |
| U1 | M1: 整数の鍵に数を通す(levels=2.0 を受ける) | tests/road/test_matilda_v37_spec.py::test_u1_bad_params_refused[段数が整数でない] |
| U2 | M8: 買いの線を `<` → `<=` | tests/road/test_matilda_v37_spec.py::test_u2_entry_flag_table[ちょうど線の上(買いの線)→ 0(v37:995 は厳しい <)]・tests/road/test_matilda_v37_spec.py::test_u10_close_on_the_line_no_signal[7000050] |
| U2 | M8: ボラの門を `≦` → `<` | tests/road/test_matilda_v37_spec.py::test_u2_entry_flag_table[ボラの門ちょうど(ボラ = 比 × last)→ 閉じる] |
| U2 | M10: 2 倍の時間を `>` → `>=` | tests/road/test_matilda_v37_spec.py::test_u2_exit_flag_table[買い玉・ちょうど 2 倍 → 2(v37:1010 は厳しい >)]・tests/road/test_matilda_v37_spec.py::test_u7_time_exits |
| U2 | M10: ブレイク中の「b_signal 0 → 1」の枝を外す | tests/road/test_matilda_v37_spec.py::test_u2_exit_flag_table[ブレイク・b_signal 0 → 1] |
| U2 | M10 exit_price: 買い玉の旗 2 を min → max | tests/road/test_matilda_v37_spec.py::test_u2_exit_price_table[買い玉・2 → 中心 と 建値 + ボラ × step_exit ÷ 段数 の低い方(v37:912)・建値の側]・tests/road/test_matilda_v37_spec.py::test_u2_exit_price_table[買い玉・2・中心の側]・tests/road/test_matilda_v37_spec.py::test_u7_time_exits |
| U3 | M11: 2 段目からも size_ref を渡さない | tests/road/test_matilda_v37_spec.py::test_u3_range_entry_ladder_exit_and_size・tests/road/test_matilda_v37_spec.py::test_u3_size_ref_tampering_fails_check・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat・tests/road/test_matilda_v37_spec.py::test_u9_foot5_built_from_minutes_and_decided_every_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_missing_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_first_bar_off_grid |
| U3 | M11 検査 (v): 元の行との突き合わせを外す | tests/road/test_matilda_v37_spec.py::test_u3_size_ref_tampering_fails_check |
| U3 | M9: 段ごとの決済を付けない(いつも place) | tests/road/test_matilda_v37_spec.py::test_u3_range_entry_ladder_exit_and_size・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[売り]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[買い]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[売り]・tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u7_time_exits・tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat・tests/road/test_matilda_v37_spec.py::test_u9_foot5_built_from_minutes_and_decided_every_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_missing_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_first_bar_off_grid・tests/road/test_matilda_v37_spec.py::test_u9_foot1_missing_minute_counts_bars_present・tests/road/test_matilda_v37_spec.py::test_u12_no_ladder_left_after_signal_off |
| U4 | M11 土台: size_ref の段数の確かめを外す | tests/road/test_matilda_v37_spec.py::test_u4_size_ref_refused[段数が違う] |
| U4 | M11 土台: 元が写した行かの確かめを外す | tests/road/test_matilda_v37_spec.py::test_u4_size_ref_refused[元が写した行] |
| U4 | M11 土台: place_with_exit が size_ref を place に渡さない | tests/road/test_matilda_v37_spec.py::test_u3_range_entry_ladder_exit_and_size・tests/road/test_matilda_v37_spec.py::test_u3_size_ref_tampering_fails_check・tests/road/test_matilda_v37_spec.py::test_u4_place_with_exit_size_ref・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat・tests/road/test_matilda_v37_spec.py::test_u9_foot5_built_from_minutes_and_decided_every_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_missing_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_first_bar_off_grid |
| U4 | M11 土台: 写した行の size_px_source を「指値」に | tests/road/test_matilda_v37_spec.py::test_u3_range_entry_ladder_exit_and_size・tests/road/test_matilda_v37_spec.py::test_u4_size_ref_copies_first_level・tests/road/test_matilda_v37_spec.py::test_u4_size_ref_refused[元が写した行]・tests/road/test_matilda_v37_spec.py::test_u4_place_with_exit_size_ref・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[売り]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[買い]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[売り]・tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u8_break_switches・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat・tests/road/test_matilda_v37_spec.py::test_u8_break_off_when_back_to_center・tests/road/test_matilda_v37_spec.py::test_u9_foot5_built_from_minutes_and_decided_every_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_missing_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_first_bar_off_grid・tests/road/test_matilda_v37_spec.py::test_u9_foot1_missing_minute_counts_bars_present・tests/road/test_matilda_v37_spec.py::test_u11_levels_fixed_across_trades・tests/road/test_matilda_v37_spec.py::test_u12_no_ladder_left_after_signal_off |
| U5 | M9 旗 0: 玉があれば段を残す(4 版目の形) | tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[売り]・tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u12_no_ladder_left_after_signal_off |
| U5 | M6 全部取り消す: 建てを先に、決済を後に | tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[売り]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[買い]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[売り]・tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat・tests/road/test_matilda_v37_spec.py::test_u12_no_ladder_left_after_signal_off |
| U5 | M6 全部取り消す: 段の数えを空にしない | tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[買い]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[売り]・tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u7_time_exits・tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat・tests/road/test_matilda_v37_spec.py::test_u11_levels_fixed_across_trades |
| U6 | M10: 相場から遠ざかる向きでも置き直す | tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u7_time_exits |
| U7 | M10: 玉の向きが変わってからの分をいつも 0 に | tests/road/test_matilda_v37_spec.py::test_u7_time_exits |
| U7 | M10 旗 3: flatten をしない | tests/road/test_matilda_v37_spec.py::test_u7_time_exits |
| U8 | M9: ブレイク中の 1 段目を last でなく lsp に | tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat |
| U8 | M9: 玉なしの置き直し(v37:851-853)を外す | tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat |
| U8 | M10b: ブレイクの解除を外す | tests/road/test_matilda_v37_spec.py::test_u8_break_off_when_back_to_center |
| U8 | M7: bup = max(列, 2 倍の高値) を「列だけ」に | tests/road/test_matilda_v37_spec.py::test_u8_break_line_uses_max_with_double_range |
| U8 | M4: b_signal の寄せで、出来高が平均を超える条件を外す | tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit |
| U9 | M2: 窓の区切りを最初の足から数える | tests/road/test_matilda_v37_spec.py::test_u3_range_entry_ladder_exit_and_size・tests/road/test_matilda_v37_spec.py::test_u3_size_ref_tampering_fails_check・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[売り]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[買い]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[売り]・tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u7_time_exits・tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u8_break_switches・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat・tests/road/test_matilda_v37_spec.py::test_u8_break_off_when_back_to_center・tests/road/test_matilda_v37_spec.py::test_u9_foot5_built_from_minutes_and_decided_every_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_missing_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_first_bar_off_grid・tests/road/test_matilda_v37_spec.py::test_u9_foot1_missing_minute_counts_bars_present・tests/road/test_matilda_v37_spec.py::test_u10_center_is_python_round_half_even・tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[1-7000300-7000200]・tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[None-7000400-7000100]・tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[200-7000400-7000100]・tests/road/test_matilda_v37_spec.py::test_u10_close_on_the_line_no_signal[7000050]・tests/road/test_matilda_v37_spec.py::test_u10_close_on_the_line_no_signal[7000450]・tests/road/test_matilda_v37_spec.py::test_u10_no_decision_before_warm・tests/road/test_matilda_v37_spec.py::test_u11_levels_fixed_across_trades・tests/road/test_matilda_v37_spec.py::test_u12_no_ladder_left_after_signal_off |
| U9 | M2: 欠けたときに前の窓を閉じない | tests/road/test_matilda_v37_spec.py::test_u9_foot5_missing_minute |
| U9 | M2: 束ねた高値を最後の足の高値に(最大でなく) | tests/road/test_matilda_v37_spec.py::test_u9_foot5_missing_minute |
| U10 | M4: 中心を四捨五入に(偶数への丸めでなく) | tests/road/test_matilda_v37_spec.py::test_u10_center_is_python_round_half_even |
| U10 | M4: ヒゲを切らない | tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[1-7000300-7000200] |
| U10 | M5: 慣らしを 1 本少なく | tests/road/test_matilda_v37_spec.py::test_u10_no_decision_before_warm |
| U10 | M4: ボラの割る数を vola_count に戻す | tests/road/test_matilda_v37_spec.py::test_u3_range_entry_ladder_exit_and_size・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[売り]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[買い]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[売り]・tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u7_time_exits・tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u8_break_switches・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat・tests/road/test_matilda_v37_spec.py::test_u9_foot5_built_from_minutes_and_decided_every_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_missing_minute・tests/road/test_matilda_v37_spec.py::test_u9_foot5_first_bar_off_grid・tests/road/test_matilda_v37_spec.py::test_u9_foot1_missing_minute_counts_bars_present・tests/road/test_matilda_v37_spec.py::test_u10_center_is_python_round_half_even・tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[1-7000300-7000200]・tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[None-7000400-7000100]・tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[200-7000400-7000100]・tests/road/test_matilda_v37_spec.py::test_u10_close_on_the_line_no_signal[7000050]・tests/road/test_matilda_v37_spec.py::test_u10_close_on_the_line_no_signal[7000450]・tests/road/test_matilda_v37_spec.py::test_u11_levels_fixed_across_trades・tests/road/test_matilda_v37_spec.py::test_u12_no_ladder_left_after_signal_off |
| U10 | M3: 指標に今の 1 分足を含める | tests/road/test_matilda_v37_spec.py::test_u3_range_entry_ladder_exit_and_size・tests/road/test_matilda_v37_spec.py::test_u3_size_ref_tampering_fails_check・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[売り]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[買い]・tests/road/test_matilda_v37_spec.py::test_u5_flat_ladder_canceled_when_signal_off[売り]・tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u7_time_exits・tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u8_break_switches・tests/road/test_matilda_v37_spec.py::test_u8_break_chase_when_flat・tests/road/test_matilda_v37_spec.py::test_u8_break_off_when_back_to_center・tests/road/test_matilda_v37_spec.py::test_u9_foot1_missing_minute_counts_bars_present・tests/road/test_matilda_v37_spec.py::test_u10_center_is_python_round_half_even・tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[1-7000300-7000200]・tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[None-7000400-7000100]・tests/road/test_matilda_v37_spec.py::test_u10_beard_cut[200-7000400-7000100]・tests/road/test_matilda_v37_spec.py::test_u10_no_decision_before_warm・tests/road/test_matilda_v37_spec.py::test_u11_levels_fixed_across_trades・tests/road/test_matilda_v37_spec.py::test_u12_no_ladder_left_after_signal_off |
| U11 | M6: 0 に戻ったら段数の上限を +1(fukuri の枝の形) | tests/road/test_matilda_v37_spec.py::test_u8_break_entries_and_exit・tests/road/test_matilda_v37_spec.py::test_u11_levels_fixed_across_trades |
| U12 | M9 旗 0: 玉があれば段を残す | tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[買い]・tests/road/test_matilda_v37_spec.py::test_u5_signal_off_cancels_ladder_even_with_position[売り]・tests/road/test_matilda_v37_spec.py::test_u6_exit_kept_when_new_price_is_further・tests/road/test_matilda_v37_spec.py::test_u12_no_ladder_left_after_signal_off |
| U12 | M10: 決済が close 1 つのとき、近づく向きでも置き直さない | tests/road/test_matilda_v37_spec.py::test_u7_time_exits・tests/road/test_matilda_v37_spec.py::test_u12_no_ladder_left_after_signal_off |
| H1 | `git diff --stat tests/` | 出力なし(試験のファイルは変わっていない) |
| H2 | `PYTHONPATH=src python -m pytest tests/road` | 315 passed |
| H3 | SCHEMA の列名の一覧の md5 | 前後とも 2a0f50cdead0023589b414f8ecda14db |
| H4 | `git diff --stat src/bot/bt/fill src/bot/bt/core src/bot/bt/pipeline.py` | 出力なし |

## 合成の乱歩で走らせて見えた事実(試験の外)

受け入れの試験と同じ走らせの形(self_trade は宣言しない、遅れ 0、range_open)で走らせました。
- 足: 合成の乱歩の 1 分足 1500 本。始値 7,000,000 から、終値の差は gauss(0, σ)。
- 乱数: `random.Random(seed)`、seed は 0〜2。
- 引数(σ は 3000 か 300):
  - V37_ORIGINAL
  - V37_ORIGINAL で b_signal=False
  - BASE で break_delay=1・b_signal=True・beard_ignore=50・alert_count=5
  - BASE で levels=3・foot=3・break_delay=2・b_signal=True・range_setting=1e-6
- 書いた置き場は scratchpad だけです。市場のデータは読んでいません。

結果(出力の行):
```
orig 0 ok … failures 0
orig 1 STOP PipelineError … RuleNotDeclaredError: the venue rule 'self_trade' decides this situation and the run did not declare it
orig 2 ok … failures 0 / orig_b0 0〜2 ok … failures 0
small 0 STOP … RuleNotDeclaredError: … 'self_trade' …
small 1 STOP RoadStrategyError ブレイクの旗が 1 から -1 に直に変わった(…)
small 2 STOP RoadStrategyError ブレイクの旗が -1 から 1 に直に変わった(…)
small2 0・1 ok … failures 0 / small2 2 STOP … 'self_trade' …
```

- 事実: orig の seed 1 を `rules={"market_ref": "next_bar_open", "self_trade": "cancel_both"}` で走らせ直すと、楽観側で self_trade で閉じた注文は次の 3 つでした。
```
road-1477 buy 6857090.0 0.012 close 出した分 962 CANCELED self_trade 無し
road-1478 sell 6852846.333333333 0.002 建て 出した分 964 CANCELED self_trade e96
road-1479 buy 6856926.0 0.002 with_entry road-1478 出した分 964 REJECTED attached_parent_closed_unfilled e96
```
- 推定(仕組み):
  1. 売り玉が負けていて、決済の旗 2 で買いの close が max(中心, 建値 − x) = 中心(建値より上)に出ていた。
  2. そこへ新しい売りの合図 e96 が出た。
  3. M9 のとおり、玉があるので建値 + step からはしごを足し、その売りの段が出ている買いの close より下に出て交差した。
- 委任文の M10 の交差の行にある「リードの見立てでは、L-809 の形では起きない」は、この場面では当たっていません。U12 が見ているのは、合図が消えた後に段が残る場面だけです。
- 原典の値で測るには、走らせに self_trade の決まりの宣言が要ります。どの決まりで測るかは、委任文の M10 のとおり測る委任でオーナーに見せることになります。
- 作業者のコードは M9・M10 の文のとおりに動いていて、これは誤りではないと見ています(推定)。

## 試験で決まらず作業者が決めた内部の形

1. M9 の「段が出ていれば」は「段の数え ≠ 0」と読みました(原典の `obc != 0`)。
2. 判定は、M3 のとおり窓に足す前の指標で行います。注文の動きは生成器で書き、「全部取り消す」や決済の取り消しの後は、答えが全部届いてから同じ時刻に続けます。
   - 委任文に書かれた箇所(M9 の置き直し、旗 0 の後の利確、旗 3、旗 1・2)に加えて、M6 の全部取り消しの後と、M9 旗 ±1 の「反対の段を取り消す」の後も、答えを待ってから建てます。
3. 「答えが届いた」は、注文の状態が開いていない、または土台の取り消し待ちの印 `_cancel_pending` が消えた、としました。flatten と同じ見方です(土台の内部の印を読んでいます)。
4. 建値は、約定の知らせから平均の原価法(帳簿のツールと同じ方法、分数)で持ち、`round`(偶数への丸め)した値です。
   - 段ごとの決済の仮の建値は、`round((今の玉の段数 × 建値 + 出す段の値段の和) ÷ 段数の和)` です。建値には M10 の round した値を使いました。
5. 合図「ブレイク」の値は `{close, center}` にしました(委任文に中身の定めがありません)。
6. 本数が足りない窓でも、ボラと出来高の平均の割る数は vola_count − 1 のままです。判定は慣らしの後だけなので、合図や注文には出ません。
7. exit_price は、x(持つ段数で割る分)が要る枝で持つ段数が 1 より少ないと ValueError で止まります。レンジ中の旗 1 では止まりません。
8. 1 分足に start_time_ns が無いとき、足が窓の終わりを越えるとき、足の時刻が戻ったときは、RoadStrategyError で止まります。
9. 長い走らせで重くならないよう、判定ごとに閉じた注文を持ち物から外します。
10. 判定のタイマーのタグは `matilda_v37_decide` です。タグが空の拍子の ClockEvent は無視します。
11. 土台の size_ref について:
    - 元の注文の量が 0(量が 0 で出さなかった行)でも受けます。写した行も量 0 で出しません。
    - 元の行の決済の種類(exit_kind)が空であることも確かめています。
12. `tables.py` の limits の文(「量の計算の値段は、出所が…と突き合わせる」)は、作るもの 4 の範囲外なので触っていません。新しい出所も書き足すかはリードが決めてください。

## 問いとして返したこと

- Q1: ブレイクの旗が ±1 から ∓1 に直に変わったときの合図「ブレイク」の扱い。
  - ブレイクの旗が ±1 から ∓1 に直に変わる場面(v37:943 の elif では起こりうる)で、合図「ブレイク」をどう扱いますか。
  - M7 が決めているのは 0 → ±1 の場面だけです。今のコードはこの場面で RoadStrategyError で止まります。
  - 合成の乱歩で実際に起きました(small の seed 1・2。出力は上)。答えが出るまで、range_count や break_delay の小さい族は走りきれません。
  - 作業者の案(オーナーの言葉ではありません): b_k を消し、新しい向きで b_{k+1} を出す。消す理由の文は決めてもらう。
  - 委任文の「途中の決め」Q1 で決めが出ています。この周ではコードを直していません。
- Q2: 前の判定の取り消しの答えを待っている間に、次の判定が来たときの扱い。
  - この扱いが委任文に無いため、今は止めています。
  - 遅れ 0 の走らせでは起きず、合成の乱歩でも起きていません。遅れのある走らせで使うときに決めてください。
  - 委任文の「途中の決め」Q2 で「止めるままでよい」と決まっています。
- Q3: 変異の表の U2「ボラの門を `≦` → `<`」は、試験が落ちませんでした。
  - 試験の行は vola_setting=2e-5・1e-5 だけで、ボラ = 比 × last ちょうどの行がありません。等号は委任文の「比べの方法」どおり `≦` で実装してあります。
  - 「途中の決め」Q3 でリードが試験に行を足しました。当て直すと、tests/road/test_matilda_v37_spec.py::test_u2_entry_flag_table[ボラの門ちょうど(ボラ = 比 × last)→ 閉じる] が落ちました。
- Q4: 変異の表の U8「bup = max(列の後ろから break_delay 番目, 2 倍の高値) を列の値だけにする」は、試験が落ちませんでした。
  - M7 の 2 倍の高値との max を見分ける場面が試験にありません。実装は M7 のとおり max です。
  - 「途中の決め」Q4 でリードが試験を足しました。当て直すと、tests/road/test_matilda_v37_spec.py::test_u8_break_line_uses_max_with_double_range が落ちました。
- Q5: M4 の expantion_flg の「→ +1」「→ −1」は、引いた原典の行 v37:592-594 の `+= 1`・`-= 1`(足し引き)として実装しました。
  - 「→ 0」は代入です。読みの確かめをお願いします。
  - 試験では見分けられません。ただ、b_signal を 0 に戻す条件(expantion_flg = 0)が変わるので、測った結果に効きます。
  - 「途中の決め」Q5 で、足し引きで正しいと決まっています。
