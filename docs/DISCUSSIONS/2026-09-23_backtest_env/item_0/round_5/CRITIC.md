# 項目 0「核」第 5 周 — 批評家の記録

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`。起動文が示す指紋は `362bf666dfac`(コミット `ebbaf34` の版)。今の作業木の版は `c9e8800bf176`(コミット `9b42123`、`sha256sum | cut -c1-12` で確かめた)。全 159 行を読んだ。`git diff ebbaf34 HEAD -- docs/DATA/delegations/20260923_backtest_env_prompt.md` の差は、通過の判定の語(部品は「同等以上」、項目 13 は「圧倒」= L-431・L-432)と L-429 の注記で、批評家の格付けの基準(§3「批評家」)は「通過の判定は [止める] が 0 件かで決まる」の語が替わっただけで中身は同じ。食い違いはこの 1 点(起動文の指紋が古い版を指す)で、判断には効かないので今の版に従った。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`(`python3 tests/bt/battery/item_0/gen_definitions.py --check` → `OK`、場面 32)、検討表 `tests/bt/battery/item_0/opponents/CONSIDERED.md`(`python3 scripts/check_bt_considered.py …` → `OK 誤り 0 件`)、`mutant.py --check` → `changed scenes: ['p4-received-time']` / `OK`、作業者の `round_5/ROOTCAUSE.md`、場面係の `tests/bt/battery/item_0/ROOTCAUSE_r5-1.md`、この周の表 `round_5/表_*.md` と `materials/`。一時ファイルは scratchpad の `bt/item0_r5_critic_*`。

## 0. 構造の変化(前の周から)

あり。作業者の申告の 3 点を作業木の実物で確かめた(`git diff --stat HEAD -- src/bot/bt/core` → 6 ファイル、192 行追加 38 行削除、新しい部品 `values.py`)。
- (1) 位置の規則: `window.py:37-43` の表 `POSITION_RULE` と `_check_bound`(`window.py:46-55`)。`DeliveredEvents.__getitem__`(`window.py:72-84`)は形ごとの不等式を持たず、端の役で表を引くだけ。
- (2) 値: `values.py` の `freeze`/`thaw`、`OrderRequest.__post_init__` が `extra` を作る時に固める(`api.py:110`・`118-140`)、報告の文の欄を `isinstance(…, str)` で検める(`engine.py:235-241`、`events.py:125-130`)。
- (3) 実行の時刻の範囲: `CoreEngine(time_span_ns=…)`(`engine.py` の `_validate_time_span`・`_check_in_span`)、与えなければ `defaults_used` に `time_span`。

## 1. 前の周までの指摘を自分で確かめ直した結果

コマンド: `PYTHONPATH=src python3 -m pytest -p no:cacheprovider tests/bt/critic/item_0 tests/bt/item_0 tests/bt/battery/item_0` → この周の試験を足す前は `1 failed, 492 passed in 61.71s`。落ちたのは下の 1.1 の 1 件だけ。

### 1.1 批評家の試験の誤り(場面集の規則 8)

- `test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order`: 場面係が `ROOTCAUSE_r5-1.md` の「走らせた検め」で「約束事を変えたために落ちる」と報告した。**確かめた結果、試験自身の誤り。**第 4 周に書き直したこの試験は、adapter が出力に `stated_rule`・`predicted` を入れ、対象の名前なしで採点する形だった。この形は第 4 周の [直す] i0-r4-05(批評家自身の指摘)を受けて場面係が退役させた(規則は `stated_rules.py` に対象の名前で固定し、runner が当てる)。確かめたい性質(1 本の入力の順を守る対象は正解と一致、型の順で並べ直す対象は一致しない)は今の約束事でも成り立つ。**直した**: 場面集の側の単一入力の規則(`stated_rules.STATED_RULES` の `form == "single_input"`、今は `opp_hftbacktest` の `stable_by_time`)で採点する形に書き直し、adapter の出力から規則を外した。結果 `2 passed`。消した主張は無い。

### 1.2 前の周の指摘

| id | 確かめ方 | 結果 |
|---|---|---|
| i0-r4-01(最新の次の位置から始まる区間が空) | 第 4 周の試験 `test_i0r4_open_slice_from_next_position.py` の 6 件が通る。加えて実装を見ずに書いた判定(添字 `i >= n`・前向きの始点 `>= n`・前向きの終点 `> n`・後ろ向きの始点と終点 `>= n` のどれかなら断る、断らなければ素のタプルと同じ値)と、長さ 0〜6・端 None と -9〜9・歩幅 None と ±1〜3 の総当たりで突き合わせた → `cases 19733 disagreements 0` | 直った |
| i0-r4-02(送った注文の `extra` を書き換えられる) | 第 4 周の試験 `test_i0r4_order_extra_mutated_in_flight.py` の 2 件が通る。ただし同じ原因が `extra` 以外の欄・列挙の値・通知の文の欄に残る → **i0-r5-01** | `extra` のリスト・辞書は直った。原因は残る |
| i0-r4-03(上位互換を中身の分からない能力に当てた) | 検討表は「能 N: 在る/無い」と出所の形になり、「在るとしても」は無くなった。一次資料 (b) を読んだ行の根拠を SCAN と抜き取りで突き合わせた(9153・8806・9011・4140・6812 行は表の記述どおり)。ただし「含む」の側に、走った候補が機構として持たない型を「Basana の `basana.Event` の子で運べる」で当てた行が 7 行ある → **i0-r5-04** | 形は直った。同じ原因が残る |
| i0-r4-04(16 を走らせず、54 を動かせなかったと載せた) | `opponents/RUNNABILITY.tsv` に 52 候補、走った 36 候補の `survey_results/*.tsv` は各 32 場面。16・54 は「走った」で、検討表の各観点の「動かせた候補」の行に載る | 直った |
| i0-r4-05(P0-5 の正解の列を adapter が書く) | `stated_rules.py` に対象ごとの規則と手書きの `FIXED_PREDICTED`、runner が場面の渡す順に当てる(`run_battery.py` の `_grade_stated_rule_once`・`_grade_hand_over`)。新実装の規則は `ORDERING_RULE["source_merge"]` を名前で引く | 直った |
| i0-r4-06(秒・ミリ秒の整数を黙って受ける) | 実行した: 範囲を与えた実行で秒 `1700006400`・ミリ秒 `1700006400000` の事象(取引所の時刻だけ秒の事象、時計の事象を含む)→ どれも `TimestampUnitError`。範囲を与えない実行は受けて `defaults_used` の末尾に `'time_span'` | 直った(与えない実行は記録に残る形。後から厳しくしないので [止める] にしない) |
| i0-r3-01(例外のあとも走る)・i0-r3-09(時計を先入れ先出しと書く) | 前の周の試験 `test_i0r3_resume_after_exception.py`・`test_i0r2_channels_random.py` ほかが通る | 直ったまま |
| i0-r3-02〜07・10・11 | i0-r3-05: `opponents/quantcore_adapter.py:48-49` は既定の上限のまま。i0-r3-11: `CONSIDERED.md:3` は起動文の指紋と作業木の版の両方を書く。ほかは前の周の確かめ(`round_4/CRITIC.md` §1.2)から場面集の該当部分が変わっていない | 直ったまま |
| i0-r1-*・i0-r2-* | 前の周までの批評家の試験がすべて通る(上のコマンド。1.1 の 1 件を除く) | 直ったまま |

## 2. この周の指摘

### i0-r5-01 [止める] 実装 — 路を渡る物が、`extra` の外で今も値になっていない(repeat_of: i0-r4-02)

作業者の根本原因 B は「路を渡る物は、作った時点で中身まで値である」を型の構造にすると書き、`values.py` の説明は「関数(呼ばれた時に送り手の今の状態を読める)・任意のオブジェクト…は断る」、`api.py` の保証は「What was sent cannot be changed afterwards」と書く。実際に固めたのは `extra` だけで、次の 3 つが残る。
1. `OrderRequest` の他の欄は、渡された物をそのまま持つ。`size`・`price`・`trigger_price` は `_require_positive`(`api.py:151-155`)で `numbers.Real` の子なら受け、`float` に直さない。`side` は `in`(`api.py:99`)、`order_type`・`client_order_id` は `isinstance(…, str)`(`api.py:101`・`108`)で、`float`・`str` の子を受ける。
2. `freeze` は `.value` が素の値なら**どの `Enum` の要素も**受ける(`values.py:109`)。要素の class は戦略が書いた class で、自分の method を持つ。
3. 逆向きの路の文の欄の検査は `isinstance(…, str)`(`engine.py:235-241`、`events.py:129`)で、`str` の子が通る。**作業者が根本原因 B で「同じ根の別の穴」として塞いだと書いた例(拒否の理由が取引所の側の時刻に合わせて変わる)が、`str` の子にするだけでそのまま再現する。**

確かめた出力(`scratchpad/bt/item0_r5_critic_probe_values.py`・`…_probe_reason.py`、注文の遅れ 10 秒、戦略が変えるのは送った次の呼び出しの自分の変数だけ):
- 送った時: `size*100 = 100.0 type==market False` → 届いた時の取引所の側: `{'notional': 50000.0, 'float_size': 500.0, 'is_market': True, 'extra_eq_changed': True}`
- 拒否の理由を戦略が読んだ値: `(0, 'OrderRejectEvent', 'none', False)` … `(4, 'TradeEvent', 'none', False)` → `(5, 'TradeEvent', 'venue secret at T0+5s', True)`(通知は 1 つも届いていない)

批評家の試験 `tests/bt/critic/item_0/test_i0r5_fields_crossing_a_path_stay_live.py` の 4 件が落ちる(`4 failed`)。作業者の試験 (f)「核が作る全部の事象型の欄がハッシュの取れる値」は `str` の子もハッシュが取れるので通り、この穴を見つけられない。信頼性(送ったあとに送り手の状態が遅れを飛び越えて相手に届く)を崩すので [止める]。

### i0-r5-02 [止める] 場面集 — Basana に無い事象の型を、adapter が自分で作った class で運び、「正解と一致」にしている

固定した要件 P0-3 の測り方は「型ごとに 1 件ずつ投入し、核が拒否せず対応する事象として保持するかを見る(**型が無ければ「対応なし」**)」。Basana 1.11 の事象の class は基の `Event` と `BarEvent` だけ(調査の venv で `import basana as bs; [n for n in dir(bs) if 'Event' in n]` → `['BarEvent', 'Event', 'EventDispatcher', 'EventSource', 'FifoQueueEventSource']`)。adapter は `class Generic(bs.Event)`(`opponents/basana_adapter.py:35`、`kind` の文字列と `fields` の辞書を持つ)を自分で書き、約定・板の写真・板の差分・資金調達・清算をそれで運ぶ。adapter 自身の記録: 「足は BarEvent、それ以外は basana.Event の子(Basana に無い型)で渡した」(`opponents/basana_adapter.py:233`)。この記録の場面が `survey_results/opp_basana.tsv` で全部「正解と一致」。**p3-funding・p3-mixed-one-run・p1-merge-by-time で「正解と一致」の相手は Basana だけ**(`survey_results/*.tsv` を数えた)なので、調査結果の側の最良の行はこの 3 場面を adapter の class から取っている。能力を対象ではなく adapter が作ったもので数えるのは場面集の規則 1 と固定した測り方に反する。表は今、調査結果の組が左右で同じ(`materials/md5sum_pairs.txt` の `survey: identical`)なので L-422 で「同等」として審査員にかけずに通る形になっており、この誤りは組の扱いそのものを変える。批評家の試験 `test_i0r5_battery_opponent_grading.py` の `test_basana_is_not_credited_with_an_event_type_its_adapter_wrote`(6 件)と `test_funding_best_cell_of_the_survey_side_does_not_rest_only_on_an_adapter_made_type` が落ちる。

### i0-r5-03 [止める] 場面集 — hftbacktest の p4-future-read-attempt は、開いた区間を試さずに「正解と一致」

場面は「対象が戦略に渡す公開の読み出しの手段ごとに、当てはまる名指し方を全部試し」と書く。新実装の adapter はこの周に `[4:]`・`[4::2]`・`[4:4]`・`[4::-1]`・`[:4:-1]` を足して 11 の名指しを試す(`adapters/new_impl.py:407-416`)。hftbacktest の adapter は同じ種類の読み出し(届いた約定の配列 `last_trades`)で添字 `[len]` だけを試す(`opponents/hftbacktest_adapter.py:348`)。調査の venv で、同じ呼び出しの中に `hbt.last_trades(0)[len:]` を 1 つ足した写しを走らせた(`scratchpad/bt/item0_r5_critic_hft_openslice.py`)→ `position None [] | hbt.last_trades(0)[len:]`、runner の採点 `{'every_attempt_stopped_by_error': False, 'future_value_obtained': False}`。記録の表は「正解と一致」(`survey_results/opp_hftbacktest.tsv`、`CONSIDERED.md` の集計で 23 hftbacktest の P0-4 が 3/3)。第 4 周に新実装で [止める] にした形(i0-r4-01)が、相手では試されずに素通りしている。対象ごとに試しの数と形が違い、正解と合わない「正解と一致」が表にある。調査結果の側の最良の行はこの場面を Basana から取るので行の値は変わらないが、表のセルと集計は誤り。批評家の試験 `test_hftbacktest_p4_cell_holds_when_the_open_slice_is_tried_too` が落ちる(venv の無い所では飛ばす)。

### i0-r5-04 [止める] 場面集 — 上位互換の「含む」を、Basana の汎用の基の class(利用者が型を足せること)で当てている(repeat_of: i0-r4-03)

委任文 §3 の上位互換は「動かせた候補か再現した候補の**機構**が、スキップする候補のその観点の能力を 1 つ残らず含む」。検討表の 7 行(P0-1 の 13・52・57・63・123、P0-3 の 11・57)は、含む側の機構を「1 Basana の `basana.Event` の子(型の数に上限が無い、event.py 54 行)」と書く。これは Basana が持つ機構ではなく、利用者が基の class から型を足せることで、i0-r5-02 の adapter の `Generic` そのものである。この理屈は、どの候補のどの型も読まずに「含む」にできる(場面係の根本原因が i0-r4-03 で外すと書いた「候補の中身を知らなくても判断が変わらない」形と同じ)。具体の害: **11 OctoBot の P0-3 の能 5(資金調達、`FundingChannel`、funding.py 61 行)は、走った候補のどれも自分の型として持たない**(p3-funding が正解と一致の相手は Basana の adapter の class だけ、i0-r5-02)。含む候補が無いので上位互換にできず、段の無い観点の規則(「実装のコードで確かめられる候補を全部再現する」)で再現するか、(a)(b) で材料が足りない理由を書く対象になる。L-413「**動かせないからと言って機構を検討せず無視することを避ける**」に当たる。能 6(清算)は 61 barter-rs が自分の型 `Liquidation` で持つ(`survey_results/opp_barter.tsv`)ので、そちらを引けば含められる。批評家の試験 `test_no_superset_skip_rests_on_basanas_generic_event_carrier` が落ちる。

### i0-r5-05 [直す] 実装 — 区間を切った答え(過去)の外を名指すと、「まだ届いていない」と言って `LookAheadError` の子で断る

`visible_events(BAR, until_ns=T0+2日)` の答え(2 本)に `[2]`・`[2:]` を当てると、`FuturePositionError`(`LookAheadError` の子)で「names a position after the last event of this answer … an answer that ends at the newest delivered event has nothing after it but events not delivered yet」(`window.py:53`)と断る。4 日目の呼び出しで、位置 2 は 3 日目の足(届いた過去)。値は黙って返さないので正解・信頼性は崩さないが、名前と文が事実と違い、先読みの誤りを捕まえる戦略の側の検出を誤らせる。確かめた出力: `answer until day 2: [101.0, 102.0] all delivered: 4` / `-> FuturePositionError | … LookAheadError [2]: the index 2 names a position after the last event of this answer`。

### i0-r5-06 [示唆] 場面集 — 読み出しの手段を持たない対象が、p4-future-read-attempt で「正解と一致」になる

Basana・QuantCore・ThePredictiveDev は、存在しない呼び方(`exchange.get_bid_ask(pair, 5 本目の時刻)` の引数の数の誤り、`Bar` への添字)で出た `TypeError`・`KeyError` で「止まった」と数えられる(場面の定義が許す形。`survey_results/opp_basana.tsv` ほか)。過去を読む口を持たない対象と、読む口を構造で守る対象が同じ「正解と一致」に並び、この場面は両者を分けない。固定した測り方の範囲なので [止める] にしない。

### i0-r5-07 [示唆] 実装 — 戦略の時計は実行の時刻の範囲の外でも届く

`time_span_ns=(T0-1日, T0+1日)` の実行で、戦略が `set_timer(T0+10日)` を頼むと、10 日後の時計の事象が届いた(`cb ClockEvent 864000.0`)。範囲の検査は入力の流れにだけ当たる(`engine.py` の `_SourceMerger._pull`)。範囲を「この実行の時刻の範囲」と書くなら、時計にも当てるかを契約に書く。

## 3. 場面集が要件の観点を覆っているか・adapter の公平さ

- 観点 P0-1〜P0-7 はすべて場面がある(各観点に値の場面 1 つ以上)。P0-2 の拒否の側は `DEFINITIONS.md` の「場面にしていない観点・側面」に理由つきで書かれ、実装の振る舞いは 1.2 の i0-r4-06 で確かめた。
- 新実装の adapter: この周の差分(`materials/logs/new_impl_adapter.diff`)は p4 の試しを 4 つ足しただけで、足した試しは新実装に不利な向き(試しが増える)。`time_span_ns` は渡していない(実行は前と同じ)。新実装だけ有利になる呼び方は見つからなかった。逆向きの不揃い(相手の試しが少ない、相手の型を adapter が作る)が i0-r5-02・i0-r5-03。
- 再現: この周は「再現した」が 0 件(`CONSIDERED.md` の集計)。前の周の再現 `repro_33` は道具そのものを走らせる形に替わり退役(`survey_results/stale/`)。弱めた再現は無い。
- 前の周の [直す]・[示唆] を [止める] の基準で見直した: i0-r4-05・i0-r4-06・i0-r4-07 はどれも直っており、付け直すものは無い。

## 4. 試験

- 足した批評家の試験: `tests/bt/critic/item_0/test_i0r5_fields_crossing_a_path_stay_live.py`(4 件、実装)、`tests/bt/critic/item_0/test_i0r5_battery_opponent_grading.py`(9 件、場面集)。全部落ちる(`4 failed`・`9 failed`)。壊れた試験は残し、作業者(実装)と場面係(場面集)が直す。
- 書き直した批評家の試験: `test_i0r2_battery_p5_grading.py` の 1 件(1.1)。
- 全試験: `setsid nohup … python3 -m pytest` の記録 `scratchpad/bt/pytest_item0_r5_critic.log`(末尾の行は下に追記)。
- 全試験の結果(2026-09-24T05:12:02Z に開始、05:20 に終了): `13 failed, 3380 passed, 4 skipped, 1 warning in 492.73s (0:08:12)`。落ちた 13 件は上で足した批評家の試験の 13 件だけ(`grep FAILED` の全行がこの 2 ファイル)。それ以外の既存の試験は全部通る。
