# 批評家の記録(項目 0「核」、第 8 周。新しく起こされた批評家)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `9ef8d697ad0a`。`sha256sum … | cut -c1-12` で確かめた)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`(§1 の行・§2 の P0-1〜P0-7・§3 の調査結果の行)、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`、作業者の報告 `round_8/REPORT.md`、リードの設計 `round_7/LEAD_DESIGN.md` §3・§7。
`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt`。

## 指摘

### i0-r8-01 [止める](相手: 実装、repeat_of: i0-r7-02)

**注文の口(`api._OrderPort`)の状態を、戦略が API の外から書き換えられ、核はその状態を信じて結果を作り、取引所への送りの関門にも使う。**
文脈から属性をたどるだけで(契約 `CORE_CONTRACT["visibility"]["scope"]` が「文脈と、そこから属性で届く物の全部」を保証の範囲に入れている所)、口の 2 つの状態 = 出口の箱(`_outbox`)と注文の台帳(`_registry`、ただの dict)に届く。第 8 周は出口の箱だけに関門を足した(`engine.py` 895-899 行: 箱の中身が「口が入れた物」かを `port.knows(coid)` で問う)が、`knows`(`api.py` 347 行)が読むのは、同じ戦略が同じように書ける台帳である。そのため:

1. 台帳に書き込んだ注文の見え方を、呼び手の結果がそのまま「戦略の注文」として返す(`engine.py` 789 行 `orders={coid: _copied_view(v) for coid, v in self._port._registry.items()}`)。送っていない注文 `ghost` が FILLED・約定 1.0・手数料 -50.0 で結果に載る(約定の記録 `fills` は空、`order_requests` に `ghost` は無い)。黙って誤った値を返す。
2. 台帳への書き込み + 出口の箱への 1 件で、`place_order` が断る注文(口座の強制注文に取っておいた id の頭 `forced-`)が取引所に着く。関門は台帳を信じて通す。結果の `order_requests` には `forced-1` が戦略の注文として載り、強制注文との見分けが id では付かなくなる。
3. 同じ根で、`ctx.order()` / `ctx.open_orders()` が戦略に返す見え方は台帳の物そのもの(写しではない)。戦略がそれを `object.__setattr__` で変えると、結果の `orders` に届く(`filled_size` 123.0・`venue_order_id` 'FORGED'、約定は 0 件)。契約の `channel_payloads.ownership` は「every receiver (…, the strategy, the caller's result, order views included) gets a copy of its own … so what one receiver changes in its copy reaches no sender, no other receiver and not the core」と書くが、戦略の受け取る見え方は写しではない。

作業者の「この周で変えた構造」(「受け手(… 戦略・結果)には、呼ぶたびにその受け手だけの写し」)と契約の文が、戦略の側の口の状態には当たっていない。**同じ根の全箇所の探し漏れ**であり、提出前の吟味 (6) の格子も欠けている: 作業者の敵対者の試験 `tests/bt/item_0/test_bt0_r8_sender_adversary.py` は、出口の箱に偽の項目を入れる形(783-800 行。台帳は触らない)と、戦略が見え方を**結果を取った後に**変える形(755-770 行)だけで、台帳への書き込みと「結果を取る前の変更」を列べていない。前の族(i0-r4-02 → i0-r5-01 → i0-r7-02)と同じ機構 = 「核が、他の者が API を通さずに変えられる物を持ち続け、後でそれを読む」の別の形なので repeat_of を i0-r7-02 とした(直した族の鎖を 0 から数えるかは台本が決める。批評家は族の同定だけを書く)。場当たりの直しの定義(試験だけの特別扱い・閾値や既定値をずらす・文言合わせ・機能を外す)には当たらないので patchwork は付けない。ただし関門が症状の形(台帳に無い id)だけを見ていて、状態の持ち主を変えていない。

根拠:
- 試験 `tests/bt/critic/item_0/test_i0r8_order_port_state_written_around_api.py`(属性をたどって台帳と箱を見つけるので、私的な名前を仮定しない。届かなくする・書き込みを断る・偽の項目を断る(CoreError)のどの直しでも通る)→ `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r8_order_port_state_written_around_api.py -p no:cacheprovider` → `2 failed`。出力の逐語: `AssertionError: the caller's result reports order 'ghost' as OrderState.FILLED with filled_size 1.0 and fees -50.0, although it was never sent (order_requests ['real'], fills [])` / `AssertionError: an order with the reserved forced-order id 'forced-1' reached the venue (['real', 'forced-1'])`。
- 試し `<S>/item0_r8_critic_probe_port_registry_write.py` → `place_order refused: OrderApiError` / `result orders['ghost']: (<OrderState.FILLED: 'FILLED'>, 1.0, 1.0, -50.0)` / `result fills: [] order_requests: ['forced-1']` / `venue saw: ['forced-1'] venue states: {'forced-1': 'LIVE'}`(`<S>/item0_r8_critic_probe_port_registry_write.out`)。
- 試し `<S>/item0_r8_critic_probe_orderview_shared.py` → `same object as open_orders()[0]: True` / `result orders['a']: filled_size 123.0 venue_order_id 'FORGED' state OrderState.OPEN` / `result fills []`(`<S>/item0_r8_critic_probe_orderview_shared.out`)。
- `src/bot/bt/core/api.py` 281-363 行(`_OrderPort`: `_registry` は dict、`order()`・`open_orders()` は台帳の物をそのまま返す)、`engine.py` 789・842・895-899 行、`contract.py` 106-114 行。

### i0-r8-02 [直す](相手: 実装、repeat_of: null)

**`history.DeliveredList` が「変更を断る」と契約に書いたのに、断っていない変え方が 2 つある。**`__init__`(`history.py` 71-72 行の断る一覧に入っていない)で中身を丸ごと入れ替えられ、`dropped` の slot(45 行)には素の代入ができる。契約 `contract.py` 55-58 行は「the core's lists behind them, reachable through a window's private attribute (history.DeliveredList: [], index(); changing one is refused)」。入れ替えた呼び出しの中では、窓の件数(`_end`)と列の長さがずれ、`visible_events()` が例外なしに短い答えを返す(3 件届いているのに 1 件)。影響は戦略自身の見え方に留まり(未来は入らない。結果・取引所・配達の要約には届かない。要約は呼び出しの前に取る、`engine.py` 849-850 行)、要件 P0-4 の未来の読み出しでもないので [直す] とした。ただし契約の文と振る舞いが食い違うので、断るか、契約の文を振る舞いに合わせるかを直す。

根拠: 試し `<S>/item0_r8_critic_probe_deliveredlist_change.py` → `append -> TypeError` / `__setitem__ -> TypeError` / `__init__ -> accepted; list now len 1 dropped 0` / `dropped = -> accepted; list now len 1 dropped 7` / `visible_events() after: [0]`(`<S>/item0_r8_critic_probe_deliveredlist_change.out`)。`src/bot/bt/core/history.py` 45・71-72 行、`window.py` 342-344 行(`_range` は `_end` を信じて列を切る)。

### i0-r8-03 [直す](相手: 実装、repeat_of: null)

**リードの答え(`round_7/LEAD_DESIGN.md` §7.2 の 14)「`[-k:]` の代わりが `visible_events(n=k)` であることは契約の同じ箇所に書く」が、契約に無い。**第 8 周で、答えの最も古い事象より前へはみ出す負の区間の境界(届いた件数が k より少ないときの `[-k:]`)を断るようになった(作業者の報告「振る舞いの変化」(1))。後の項目の戦略がこの書き方で止まったときの手引きが契約に無い。リードの答えは作業者の返り値の後に出たので、この周の作業者の落ち度ではなく、次の周で直す物として挙げる。

根拠: `grep -rn 'n=k\|\[-k:\]\|visible_events(n' src/bot/bt/core/` → 出力なし。`contract.py` 34-62 行(visibility・position_rule)。

## 前の周の指摘の直りを確かめた記録(直ったものは上に挙げない)

| 前の指摘 | 確かめたこと(コマンドと出力) | 結論 |
|---|---|---|
| i0-r7-01(後ろ向きの答えの負の区間の境界) | 前の周の試し `<S>/item0_r7_critic_probe_backward_negslice.py` を打ち直した → `r[-6:-5] -> FuturePositionError`・`r[-6:-4] -> FuturePositionError`・`r[-5::-1] -> FuturePositionError`・`r[-6:-5:-1] -> FuturePositionError`、`r[:-5:-1]` は届いた 4 件を全部返す(最も古いまで読む後ろ向きの終わり c = -1。はみ出さない)。前の周の神託 `item0_r7_critic_probe_kind_oracle_keptcoords.py` seed 1〜3 → wrong 0。**私の独立の神託** `<S>/item0_r8_critic_probe_semantic_oracle.py`(表 `POSITION_RULE` を使わず、切り詰めない数列の上で読みが訪れる位置で判定。答え・窓 `EventWindow`・背後の列 `DeliveredList` の 3 つ、前向き・後ろ向き・歩幅 ±1〜3 の答えの鎖、`index(value, start, stop)` を含む)seed 1〜6、計 801,600 回の名指し → `SILENT 0 / WRONG 0 / UNDER 0 / IDX_SILENT 0`(`<S>/item0_r8_critic_probe_semantic_oracle.out`)。批評家の試験 `test_i0r7_backward_answer_negative_bounds.py` は通る | 直った |
| i0-r7-02(`extra` の Fraction が生きたまま路を渡る) | 批評家の試験 `test_i0r7_fraction_in_extra_stays_live.py` は通る(`5 passed`、i0-r7-01 の試験と合わせて)。`values.py` 83-146 行: 受け付ける型の表 `BUILD` は全部新しい物を作る(Fraction は slot 記述子で読んで作り直す、115 行)。送り手が渡した後に自分の list を変える試し `<S>/item0_r8_critic_probe_source_mutation.py`(板の写真、配達は 5 秒後)→ `[(5, ((100.0, 1.0),))]`(変更は届かない) | 送り手の側は直った。**同じ族の別の形(戦略の側の口の状態)が残る = i0-r8-01** |
| i0-r7-03(LEAN の再現の購読の組の根拠) | `opponents/repro_lean52.py` 25-60 行: 購読は場面集が型から作るのをやめ、`AddCryptoFuture` に渡す解像度(利用者が選ぶ値)から、書き直した LEAN のコード(`DataManager.Add` → `LookupSubscriptionConfigDataTypes` → `LeanData.GetDataType`)が決める。Tick と足の同時の購読は、同じ銘柄に 2 回 `AddCryptoFuture` を呼ぶ利用者の操作として書き、既存の銘柄を使い回す根拠を QCAlgorithm.Universe.cs 580-650 行で注釈に書いている。`survey_results/repro_lean52@*.tsv` は設定つき対象ごとに別々(13 本) | 直った |
| i0-r7-04(検討表 15 行の古い前提) | `sed -n 15p opponents/CONSIDERED.md` → 「3 場面は資金調達か清算を含む」の文は、直した旨の括弧書きの中にだけ残り、今の文は `types_1`・`detail_1` の欄と `survey_results/attempts/<番号>.log` を引く形 | 直った |
| i0-r7-05(通知の「受け取れた時刻 ≤ 今」の場面が無い) | リードの答え `LEAD_DESIGN.md` §7 の 2 で「場面にしない」(固定した測り方の外。要件を広げるかはオーナーの判断)。`DEFINITIONS.md` P0-4 の升目の通知・時計の行が「場面にしない / 理由11」で、理由11 がその答えを引く(673 行) | リードの決定で閉じた。[止める] に付け直さない(下の「付け直しの見直し」) |

### 付け直しの見直し(前の周の [直す]・[示唆])

前の周の [直す] は i0-r7-03・i0-r7-04・i0-r7-05 の 3 件。03・04 は直った。05 は、固定した要件 §1 の行が「戦略は「受け取れた時刻 ≤ 今」の事象しか見られない」を通知にも掛けるので [止める] の基準(「固定した要件の行…を満たさない」)に当たるかを見直した。新実装そのものは通知でもこの行を満たす(前の周の試し、`api.py` 50-54 行: 見え方は通知が届いたときにだけ動く)。欠けは場面集の覆いであり、固定した測り方の外なのでリードが「場面にしない」と決めて記録した。要件の範囲を変えるのはオーナーだけ(委任文 §3「要件と判定の固定」)なので、批評家は付け直さない。

### 規則 8(作業者が「試験自身の誤り」と報告した批評家の試験)

作業者の報告は「該当なし」。前の周までの批評家の試験は全部通る: `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider` → `938 passed, 2 skipped in 125.82s`(この周の私の試験を足す前。ログ `<S>/pytest_item0_r8_critic_core.log`)。skip の 2 件は `test_bt0_carriers.py` 144 行(bool の子は作れない)と `test_i0r5_battery_opponent_grading.py` 130 行(調査の venv がこの環境に無い)。取り下げる試験は無い。

## 場面集の側で見たこと(指摘なし)

- 場面集の試験: `PYTHONPATH=src python -m pytest tests/bt/battery/item_0 -p no:cacheprovider` → `75 passed in 21.81s`(`<S>/pytest_item0_r8_critic_battery.log`)。
- 検討表の機械の検め: `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md` → `OK 誤り 0 件`。スキップの行(P0-1 の 13・57・63・123)は、観点の能力ごとに「在る/無い」と出所の行(一次資料の版つき URL と行、SCAN の行)を書いている。再現できない(危険)の行(41・44・58)は道具台帳 §3 の 11 件に入る。
- 規則 1(申告で数えない): P0-5 の 2 場面は対象が明記した規則を場面集の側に固定し、届いた列を runner がその規則と照らす形で、対象の申告の列を採点しない(`DEFINITIONS.md` 859・867 行の `stated_rule`)。P0-4 の試しは例外の名前と返った値で採点し、「止められる」という申告を使わない。
- 再現の弱め: LEAN の再現で、Tick と足を同時に購読する設定つき対象では資金調達が 2 回届いて「不一致」になり(`survey_results/repro_lean52@tick+minute:trade.tsv` の p3-funding)、Tick の約定は向きの欄を持たないので p3-trade が「不一致」になる。どちらも他の設定つき対象(`@daily`・`@tick` の p3-funding、`opp_aat` の p3-trade)が「正解と一致」なので、比較の表の「調査結果の側」の行(場面ごとの最良 `materials/survey_best.tsv`)は変わらない。表の結果を変えないので指摘にしない。
- 新実装の adapter(`adapters/new_impl.py`)は、約定の模型を持たない核に対し、公開の差し込み口 `FillModel` に場面集の側のダミー(`_ArrivalFill`)を渡している(場面の共通の決まり (2) の範囲)。調査結果の側の最良は P0-6 の 3 場面とも「正解と一致」で、この差し込みが新実装だけを有利にして表の勝敗を決めている場面は無い。
- 覆い: 固定した要件 §2 の P0-1〜P0-7 の全観点に値の場面が 1 つ以上ある(`DEFINITIONS.md` 683-946 行。P0-3 は p3-mixed-one-run、P0-4 は p4-visible-at-step・p4-received-time、P0-6 は p6-place-then-cancel、P0-7 は p7-cost-per-unit)。

## 構造の変化

前の周から構造は変わった(`structural_change_since_prev = true`): 名指しの位置を答えの座標に置いてから役ごとの範囲の表で検める作り(`window.py` 59-205 行、`history.py` 36-75 行の新設の `DeliveredList`)と、「そのまま渡してよい型の一覧」を捨てて受け取った所で作り直し、受け手ごとに写しを渡す作り(`values.py` 83-146・470-543 行、`engine.py` 319-338・491-500・878-913・1007-1019 行)。どちらもコードで確かめた。

## 提出前の吟味(批評家の文: 指摘ごとに根拠を自分で再現し、格付けを基準に照らし、前の周の指摘の直りを自分で確かめ、相手の付け違いが無いか確かめる)

| 指摘 | 根拠を自分で再現したか | 格付けを基準に照らした結果 | 相手 |
|---|---|---|---|
| i0-r8-01 | 試験 2 本を打ち直して 2 failed、試し 2 本の出力を上に逐語で写した | 「黙って誤った値を返す」(送っていない注文が FILLED で結果に載る)と「API が断る注文が取引所に着く」は信頼性を崩す = [止める]。契約が保証の範囲に入れた「属性で届く物」での書き込みなので、範囲の外とは読めない | 実装(`src/bot/bt/core/`)。場面集の場面は結果の `orders` を読まず、場面の正解とは関係しない |
| i0-r8-02 | 試しを打ち直し、出力を上に写した | 影響が戦略自身の見え方に留まり、未来の読み出しでも他の受け手への到達でもないので [止める] の基準のどれにも当たらない。契約の文と振る舞いの食い違い = [直す] | 実装 |
| i0-r8-03 | grep を打ち直して出力なし | 振る舞いは要件を満たし、欠けは契約の手引きの文 = [直す] | 実装(契約は `src/bot/bt/core/contract.py`) |

前の周の指摘 5 件は、上の表で 1 件ずつ自分で確かめ直した(直ったものは指摘に挙げていない)。
