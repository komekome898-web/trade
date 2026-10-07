# 作業者の報告(逐語)— 1 分足の指値の約定の決まり 2 周目(委任文 DELEGATION_fill_scenario_L769_r2.md + L-783 の変更)

## 報告(委任文 DELEGATION_fill_scenario_L769_r2.md、途中で受けた変更 L-783 を含む)

直すもの 1〜11 を全部直しました。L-783 の変更(刻みは切り捨て、6 (a)(d) は今の作り、6 (b) は maker)も入れています。受け入れの試験は全部通りました。commit・push・git add はしていません。core・口座・フック・settings.json・githooks/ も変えていません。

先に、問いとして返すことと、試験で見つけたことを書きます。

**止めて問いにしたこと(どれも、この件の受け渡しは止めていません)**
1. **close の指値も切り捨てています。** L-783 の伝言が名指ししたのは place と place_with_exit(決済の値段も含む)です。「道からは刻みに乗った値段しか届かなくなります」に合わせて、close の指値にも切り捨てを当てました。close だけ外すかは決めてください。
2. **量の計算は、切り捨てる前の値段のままです。** size_px は戦略が計算した値段です。たとえば計算した値段 5,000,000.4 では、140,000 ÷ 2 ÷ 5,000,000.4 = 0.013999… を切り捨てて 0.013 になります。送った値段で量を計算するかは逐語に無く、今のままにしました。
3. **作る順 1 の古い置き場では、足の長さを推定しています。** この置き場には走らせの記録が無いので、足の JSON の「隣り合う足の始まりの間隔で一番多いもの」から決めます。最初は間隔の最小を使いましたが、ずらした足・重なった足の試験で 20 秒・40 秒が出て誤った失敗になったので、一番多い間隔に変えました。抜けた足ばかりの足の JSON なら誤ります。走らせの記録がある置き場は記録から読みます。
4. **止めるのは注文の遅れだけです。** 足の遅れ(feed)は今までどおり (iv) で落ちるので、走らせの止めは足していません。

**試験で見つけたこと**
- 合図が出た足で、決済が取引所に閉じられた場合の誤った失敗を、作る途中で見つけて直しました。楽観側で、決済が有効になった瞬間に self_trade で閉じられると、(vii) が「その足で約定していない」と誤って落としていました。取引所がその足で閉じた決済は見ないようにしています。試験は test_fix3_road_exit_closed_by_self_trade_on_entry_bar_passes_check です。この直しを外すとこの試験が落ち、戻すと通ることを確かめました(事実)。
- tests/bt の 3 つ目の束の 1 回目は 1 件落ちました(tests/bt/item_4/test_i4_pipeline.py::test_one_run_reaches_record_exports_and_dashboard_and_is_kept_once。同じ計画を 2 回走らせると repro.json の指紋が違うという失敗)。走らせている途中で私が check.py を書き換えていたためと推定しています。そのファイルだけ回し直すと全部 passed、束を丸ごと回し直すと全部 passed・EXIT 0 でした(事実)。

### 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 1. bar_rule の走らせで注文の遅れが 0 でなければ走らせる前に拒む。検査は「受け付けた時刻 ≠ 置いた時刻」を落とす | L-769「**合図が出るのはcloseのタイミング(前の足) 指値は合図の次の足で出して**」(止め方は (あ)。リードの決め) |
| 2. 指値を銘柄の刻みに切り捨てて送る。計算した値段と送った値段の両方を残す。検査は切り捨てを確かめ、約定は送った値段で判定する | L-783「**間違えそうやから小数点以下は切り捨ててください**」 |
| 2'. close の指値にも切り捨てを当てる | **(該当語なし)**。伝言の「道からは刻みに乗った値段しか届かなくなります」からの読み → 問い 1 |
| 2''. 量の計算は計算した値段のまま | **(該当語なし)** → 問い 2 |
| 2'''. 列は sent_limit_px(送った値段)にする。取引所が持つ値段は書き出しで突き合わせ、列にはしない | **(該当語なし)**。委任文の「丸めた後の値段の列」を L-783 で置き換えた形 |
| 3. 決済が有効になるときも self_trade で突き合わせる | L-776「**間違った前提で組んだ確かめが通ってしまったら、後続が全て間違いになり結局全捨てになります。**」(直すのはリードの決め) |
| 4. 閉じた理由の名前を中身に合わせる | L-776(同上) |
| 5. record.json の指紋を見る。印があって決まりが無ければ落とす | L-776(同上) |
| 6. 両側の組み合わせを検査で掛け直す。約定の行に印の列を足す | L-769「**指値決済の良い側はその足内で指値があれば通り、悪い側は次の足内から**」(良い側 = 楽観側の対応はリードの言葉) |
| 7. liquidity を決まりから決めて突き合わせる。始値の約定は maker | L-783「**maker**」 |
| 8. 約定するはずなのに約定していない記録を落とす | L-769「**highからlowの範囲内であれば約定**」 |
| 9. 足を「n 本目」(1 から)と時刻で書く | **(該当語なし)**。O-7 からのリードの決め |
| 10. 足の長さを記録から読む(1 分の決め打ちをやめる) | **(該当語なし)**。リードの決め |
| 10'. 古い置き場は足の JSON の間隔から推定する | **(該当語なし)** → 問い 3 |
| 11. bar_rule の走らせで逆指値を出したら止める | **(該当語なし)**。問 6 (c) へのリードの決め |
| 損の側の決済も、良い側では同じ足で約定させる(今の作りのまま) | L-783「**今の作り**」 |

### 変えたファイル(全部 /home/user/trade の下)
- src/bot/bt/fill/venue.py、src/bot/bt/fill/spec.py
- src/bot/bt/pipeline.py
- src/bot/bt/road/strategy.py、src/bot/bt/road/tables.py(SCHEMA の版は road-record-7)、src/bot/bt/road/check.py
- tests/road/test_road_fill_l769_r2.py(新規)
- tests/road/road_l769_strategy.py(試験用の mode with_exit_and_buy を追加)
- tests/road/test_road_fill_l769.py(1 周目の試験を、名前・指紋・SCHEMA の版に合わせて直した)
- tests/road/test_road_record.py(文が「足 6」から「足の JSON の 7 本目(始まり…)」に変わったのに合わせた 1 行。わざと変えた文)
- docs/AUDITOR/TRACE/2026-10-07_220780c0.json はフックが書き換えたもので、私は触っていません。

### 直すもの 1〜11(試験は全部 tests/road/test_road_fill_l769_r2.py)
1. **注文の遅れ**
   - 直し方: pipeline に `_check_bar_rule_latency` を足しました。plan_pipeline と `_run_instrument` から呼びます。constant 0・empirical の全部が 0・seeded_uniform 0〜0 以外は PipelineError で止めます。検査の (vii) は、bar_rule の側で acked_venue_t_ns ≠ placed_t_ns なら落とします。
   - 試験: test_fix1_*。1 ns・1 秒・empirical [0,1]・seeded_uniform 0〜5 は止まります。止めを外して遅れ 1 秒で走らせると、約定は 0:05 で、両側の建てが (vii) で 2 件落ちます。
2. **刻み(L-783)**
   - 直し方: strategy の `_send` で指値を `_floor_to_tick` で切り捨てます。刻みは pipeline が `set_price_tick` で渡し、渡されていなければ止めます。注文の表に sent_limit_px の列を足し、limit_px は計算した値段のまま残します。書き出しの側は、取引所が持つ値段 = sent_limit_px かを確かめます。check の (vii) は、record.json の刻みで `_floor_px` を計算し直して突き合わせ、範囲の判定も切り捨てた値段で行います。取引所の off_tick の決まりは変えていません。
   - 試験(test_fix2_*):
     - 刻み 1 円で買い 5,000,000.4・売り 5,000,000.6 → どちらも 5000000.0 で送り、0:04 に約定。量は 0.013。
     - 批評家の WALK、5,007,987.4 → 5007987.0 で約定し、検査を通ります。
     - 刻み 0.5 → 5,002,792.546… が 5002792.5 になります。
     - sent_limit_px を書き換えると、指紋を合わせても (vii) で落ちます。
3. **自分の注文との交差**
   - 直し方: venue の `_feed_children` で、決済が有効になるときに `_activate_limit` と同じ突き合わせ(`_aggress`)を通します。
   - 試験: test_fix3_*。
     - self_trade を宣言しない走らせは RuleNotDeclaredError で止まります。
     - cancel_maker では [Fill e 100, Canceled e2 self_trade]。
     - cancel_taker では [Fill e 100, Canceled x self_trade]。
     - 道の走らせでも、合図の次の足で閉じた決済が検査を通ります。
4. **閉じた理由の名前**
   - 直し方: `attached_parent_part_filled` を `attached_exit_above_entry_filled` に変えました。
   - 試験: test_fix4_*。決済 2.0・建て 1.0 → 1.0 約定した後、この理由で閉じます。
5. **record.json の指紋**
   - 直し方: (vi) で record.json の指紋を repro.json と突き合わせます。(vii) は、印のある約定があって宣言に bar_rule が無ければ落とします。
   - 試験: test_fix5_*。指紋を合わせなければ (vi) で落ち、合わせても (vii) で 4 件落ちます。
6. **側の組み合わせ**
   - 直し方: (vii) で、record.json から「両側で同じ bar_rule・楽観側 = same_bar・悲観側 = next_bar」を掛け直します。venue が `fill_marks` に印を残し、約定の表の fill_rule・fill_exit_rule・fill_case の列に書きます。
   - 試験: test_fix6_*。側を入れ替えた走らせも、両側 same_bar の走らせも (vii) で落ちます。印の中身:
     - 楽観側: 決済は 0:04 に entry_bar。
     - 悲観側: 決済は 0:05 に range。
     - 始値の約定: open・maker。
7. **liquidity**
   - 直し方: 印のある約定が maker でなければ (vii) で落とします。SCHEMA には「オーナーの決定 L-783「**maker**」」と書きました。
   - 試験: test_fix7_*。maker → taker に書き換えると、指紋を合わせても (vii) で落ちます。
8. **約定しなかった記録**
   - 直し方: (vii) で、有効だった足のうち約定していたはずの足を見ます。約定していない注文も見ます。足の範囲は次のとおりです。
     - 取り消しの時刻に閉じた足までは含めます。
     - 取引所が自分で閉じた時刻に閉じた足は含めません。
     - 閉じていなければ、足の JSON の終わりまで見ます。
   - 試験: test_fix8_*。批評家の「決済を当てない模型」では、楽観側は 4 本目・悲観側は 5 本目で落ちます。範囲の内なのに取り消された close も落ちます。
9. **足の番号**
   - 直し方: 文は「足の JSON の n 本目(始まり UTC・閉じた時刻 UTC)」の形にしました。
   - 試験: test_fix9_*。例:「4 本目(始まり 2023-11-14T22:17:00Z・閉じた時刻 22:18:00Z)」。
10. **足の長さ**
    - 直し方: `MINUTE_NS` をやめ、record.json(generator.params.step_ns か spec.bar.interval_s)から読みます。古い置き場は問い 3 のとおりです。
    - 試験: test_fix10_*。5 分足の走らせでは T5+20 分に約定し、検査を通ります。足を抜くと、5 分の足で落ちます。
11. **逆指値**
    - 直し方: venue の on_order で、bar_rule の走らせに stop・stop_limit が来たら FillSpecError で止めます。
    - 試験: test_fix11_*。bar_rule の無い走らせは今のまま Ack です。

L-783 の 6 (a)(d) と (b) は、SCHEMA と docstring を「オーナーの決定 L-783」の書き方に変えました。損の側の決済が同じ足で約定することは test_loss_side_exit_on_entry_bar_kept で確かめています。

### 批評家の試しの場面
試しの台本の写しと出力は /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/l769_r2/ にあります。
- 遅れ 1 ns・1 秒 → 走らせを始める前に止まります(test_fix1)。probe_road.py の問 0 は、この止めのため pipeline では回りません。止まること自体が答えです。
- 刻みの外の値段 → 刻みに切り捨てて送り、正しく通ります。書き換えれば落ちます(test_fix2)。
- 自分の注文との交差 → 走らせが止まります(probe_cross.out の最後の行が RuleNotDeclaredError ... 'self_trade')。
- bar_rule を消した record.json → (vi)、指紋を合わせても (vii) で落ちます。
- 側の入れ替え → (vii) で落ちます。
- liquidity の書き換え → (vii) で落ちます。
- 約定しなかった決済 → (vii) で落ちます。

### 全部の試験の結果(件数は書きません)
- 指紋(fuzz_default.out。tier 0・2・3 は 1 回目と同じ。事実)。コマンドは `PYTHONPATH=src python …/l769_r2/fuzz_default.py now <tier>`:
  - tier 0: 473d7973d5c3bebe2a51643f30b9c7bd7bb7555ef2481d7d6dc37dfcfa342283
  - tier 2: 5e3fa02a960729989627f145934304bae7a8cf9ab088a066e4942cc8d5e11bf4
  - tier 3: 5723062f2d5f26b0b7b400a4df16f6dbe64a43317d0dffe3376d9998c11d45c7
- `PYTHONPATH=src python -m pytest tests/road` → 全部 passed(1 周目の場面 1〜6 の test_road_fill_l769.py を含む)
- `PYTHONPATH=src python -m pytest tests/bt/battery tests/bt/critic` → 全部 passed(skipped あり)、EXIT 0(pt_bt_a.txt)
- `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/item_1` → 全部 passed(skipped・warnings あり)、EXIT 0(pt_bt_b.txt)
- `PYTHONPATH=src python -m pytest tests/bt/item_2 tests/bt/item_3 tests/bt/item_4` → 回し直しで全部 passed(skipped あり)、EXIT 0(pt_bt_c2.txt。1 回目の pt_bt_c.txt は上に書いた 1 件の失敗)

### 範囲の外で、変えずに残したところ
`scripts/road/check_outputs.py` の使い方の文は「1 分足の JSON」「(i)〜(vi)」のままです。1 周目と同じく範囲の外としました(事実)。

---

## リードの検収(2026-10-07)
- `PYTHONPATH=src python -m pytest tests/road` → 221 passed(リードが打った。件数はこの行の出力の写し)。
- 指紋: `PYTHONPATH=src python …/l769_r2/fuzz_default.py now 0|2|3` → 473d7973…・5e3fa02a…・5723062f…(1 回目と同じ。リードが打った)。
- 問い 1(close も切り捨て): 採る。オーナーの「**小数点以下は切り捨ててください**」(L-783)は注文の値段全部についての言葉と読む(リードの読み)。
- 問い 2(量は切り捨て前の値段): 道の戦略を作る委任(S4、L-781 の量の口)で、量の計算に使う値段を送った値段にそろえる(リードの決め。差は 0.001 BTC の切り捨ての中に入る大きさ)。
- 問い 3(古い置き場の足の長さの推定): 採る。走らせの記録がある置き場は記録から読む。
- 次: 批評家 2 回目。
