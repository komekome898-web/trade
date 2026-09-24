# 場面集への指摘ごとの根本原因と直し(項目 0、第 r6-1 回の直し、場面係、2026-09-24)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`。起動文の指紋は `4c4cfc6e4052`、作業木の版も `4c4cfc6e4052`(`sha256sum … | cut -c1-12`、全 162 行を読んだ)。
指摘の逐語: 起動文に貼られた 3 件(i0-r5-02・i0-r5-03・i0-r5-04)と、その全文 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_5/CRITIC.md` の §2。同じ記録の [示唆] i0-r5-06(場面集)も読んだ。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
当てた委任文の決まり: §3「根本的解決」(直す前に指摘ごとの根本原因と変える作りを書く / 指摘の文言だけに合わせない)、「場面集の規則」1・2・4・6・9、「調査結果の側の選び方」、「動かせない候補の検討と再現」(段の無い観点は、上位互換で 1 能力ずつ含むと示せない候補を再現する)、「提出前の吟味」(1)〜(5)。
この 3 件に [聞く] は無い。

**この節(根本原因と変える作り)は直す前に書いた。**直した結果と根拠は最後の「結果」の節に足す。

## 共通の根本原因

3 件とも、**場面が測るもの(事象の型・名指し方の網羅・含む側の機構)を、対象ではなく場面集の側の書き手(adapter の書き手、検討表の書き手 = どちらも場面係)が作れる形のまま残し、それを runner と試験が見分けられなかった**ことに行き着く。

1. 場面集の決まりに「測るものは対象のコードが出す。adapter が書いてよいのは測らない部分だけ」という線が無かった。adapter の約束事(`adapters/protocol.py`)は「公開の口と公開の差し込み口だけを使う」とだけ書き、**利用者が子 class を足せる基の class** も「公開の口」に読めた。i0-r5-02 の `Generic(bs.Event)` はこの読みから出た。
2. 出力の形が、測るものの**出所**を持たなかった。型の場面の出力は adapter が写した型の名前(`"funding"` などの文字列)だけで、戦略が受け取った物が何の class かを runner は見られない。P0-4 の名指しの試しは、試した分だけが記録され、**何を試すべきだったか**は場面集のどこにも固定されていなかった(場面の文の「当てはまる名指し方を全部」を、書き手がその都度に読んだ)。
3. 採点の向きが、試しや型を「少なく・緩く」書いた方に有利だった。P0-4 は試した読み出しの全部が止まれば正解なので、試しが少ない adapter ほど通りやすい。型の場面は adapter が作った型でも「届いた」になる。どちらも**場面集の書き手が手を抜くと相手(調査結果の側)が強く見える**向きで、それを止める機械が無かった。
4. 検討表の「上位互換」は、含む側の場面の結果を引いて裏付けにしていたが、その結果自身の出所(adapter が作った型)を確かめる所が無く、誤った結果の上に誤った「含む」が立った(i0-r5-04 は i0-r5-02 の上に立つ)。

同じ根から出た、指摘の外の欠陥(場面集の全体を探した結果。直す前に見つけたもの):

| # | どこ | 何が adapter の作ったものか | 見つけた方法 |
|---|---|---|---|
| A | P0-5 の p5-same-time-twice・p5-hand-over-order、98 mihircoding/limitOrderBook(正解と一致) | 道具は型を持たない(adapter 自身の説明「The tool has no event types」)。adapter が動作の閉包の中の `e["kind"]`(場面の辞書)を読み、型の名前として返していた | `survey_results/*.tsv` の型の場面で `status_1 = ok` の全セル(60 件)の detail と adapter を読んだ |
| B | P0-2 の p2-event-time-exact・p2-one-ns-apart、1 Basana | 約定を `Generic`(adapter の class)で運んでいた | 同上 |
| C | P0-4 の p4-visible-at-step、1 Basana・23 hftbacktest・34 QuantCore・20 VnPy・6 Ziplime(正解と一致) | 場面は「戦略が対象の公開の手段で読んだ過去の件数」を測る。5 件とも**戦略が自分で貯めた列**で答えていた(detail の逐語「戦略が受け取った BarEvent を戦略自身が貯めて数えた」「戦略が各回に data.current(close) を読んで貯めた」ほか) | 全 36 候補の p4-visible-at-step の正解と一致のセルの detail を読んだ |
| D | P0-2 の p2-iso-utc・p2-iso-offset、55 backtesting.py・10 fast-trade・54 finmarketpy・75 Freqtrade・4 PyBroker・16 Luczinsritter・62 qf-lib・121 QSTrader・68 quanttrader・53 Rqalpha・18 zipline-reloaded・6 Ziplime | 場面は「対象がデータを読むときに使う、対象自身の時刻の変換を使う」と書く。12 件は adapter が自分で `pd.Timestamp(iso)`・`pl.Series(...).str.to_datetime` を呼んだ値で答えていた(対象のデータの入口を通していない)。1 Basana は adapter が標準の `datetime.fromisoformat` を呼んでいた | 全候補の p2-iso-utc の detail を読んだ |
| E | P0-4 の p4-future-read-attempt、試しの形が対象ごとに違う | 列の位置の読み出しで添字 1 つ(`[len]`・`[4]`・`[i + 1]`・`[1]` ほか)だけを試し、開いた区間を試さない adapter が 10 件(当方の現状・backtesting.py・Backtrader・Freqtrade・hftbacktest・PyBroker・Luczinsritter・pyalgotrade・VnPy・ThePredictiveDev)、時刻の読み出しで 1 時刻だけ・区間の片側だけを試す adapter がある。新実装の adapter は位置の 9 通り(`[4]`・`[4:5]`・`[3:5]`・`[4:]`・`[4::2]`・`[4:4]`・`[4::-1]`・`[:4:-1]` と足の列の `[4]`) | 直す前の版(コミット c2a1223)の `git show c2a1223:<adapter> | grep -n 'att\.run' | grep '"position"'` の全行(全 adapter)。**直す前にこの行を「7 件」と書いたのは数え誤り**(Backtrader・Freqtrade・Luczinsritter を落としていた。結果の節で数え直した) |
| F | 検討表の P0-5 の 11 OctoBot の行 | 含む側を 1 Basana の source の priority と、その p5 の正解と一致で示していた。p5 の Basana の結果は資金調達と清算を `Generic` で運んだもの(i0-r5-02 と同じ)で、Basana はこの 2 型を持たない | 検討表の「含む:」の全行が引く場面の結果を、その場面の出所まで辿った |

## i0-r5-02 [止める] Basana に無い事象の型を、adapter が自分で書いた class で運び、正解と一致にしている

- **なぜ起きたか**:
  1. 固定した要件 P0-3 の測り方「型が無ければ『対応なし』」を、場面集の決まりに写していなかった。「型」が**対象の配布物が持つ型**であることを場面の定義にも adapter の約束事にも書かず、Basana の文書が基の class を「many different types of events」の親として示すのを、公開の口と読んだ。
  2. 型の場面の出力が、adapter の写した型の名前しか持たず、戦略が受け取った物の class(出所)を runner が見られなかった。runner は adapter が書いた `"funding"` の文字列と正解を比べるだけだった。
  3. 測るもの(型)と測らないもの(戦略の中身・差し込むダミー・時計の条件)の線が無く、adapter が書いてよい範囲が決まっていなかった。同じ根で A・B・C・D が起きた。
- **どの作りを変えるか**:
  1. **場面集の決まりに線を引く**(`scenes.py` の説明・`DEFINITIONS.md` の共通の決まり・`adapters/protocol.py`): 「その場面が測るもの(事象の型・時刻の変換・過去の読み出し・並び)は、対象の配布物のコードが出したものだけを数える。adapter と場面の戦略が書いてよいのは、(1) 対象の公開の手段を呼ぶこと、(2) 対象が利用者の実装を受けると公開している差し込み口に渡すダミー(P0-7 の模型・口座、時計を起こす条件)、(3) 対象が返した物を場面の語に写すこと、だけ。adapter が作った型(対象の基の class の子・基の class に欄を足した物・辞書や関数に型の印を付けた物)で事象を運ばない。戦略が自分で貯めた値・adapter が自分で呼んだ変換で答えない。対象がその型・口を持たないときは『対応なし』(何を確かめたかを書く)」。
  2. **出所を出力に持たせる**: 戦略が受け取った事象の列を返す場面(P0-1 の 3 場面・P0-2 の p2-event-time-exact と p2-one-ns-apart・P0-3 の市場の 7 場面・P0-5 の 3 場面)の出力に `carriers`(受け取った 1 件ごとに、その物の class の `模組.名前`。型を印で持つ対象はその印の物の名前。コンパイルした道具は driver が一致させた道具の型の名前)を必須にする。Python の対象では adapter の手書きではなく `common.carrier(受け取った物)` が物から作る。
  3. **runner が出所を検める**(`run_battery.py`): `carriers` が無い・列と長さが合わない・場面集の模組(`opponents`・`adapters` ほか)の class・1 つの carrier が 2 つの型の名前に写されている(= 型を adapter の欄が決めている)、のどれかなら、その場面は採点せず `結果なし` にし、理由を出力に残す(`provenance_error`)。**採点の前に弾くので、adapter が作った型は「正解と一致」になり得ない。**
  4. **試験**(`test_battery_item0.py`): 記録された全ての結果(`survey_results/*.tsv` と当方の現状)に `provenance_error` が 1 件も無いこと、対象ごとに全場面を通して 1 つの carrier が 1 つの型の名前にしか写されていないこと(場面をまたいで基の class を別の型に使い回すのを止める)、を見る。
  5. Basana の adapter を直す: 型は Basana の配布物の class で運ぶ(足 = `basana.core.bar.BarEvent`、約定・板の写真・板の差分 = 配布物にある `basana.external.binance` の `TradeEvent`・`PartialOrderBookEvent`・`OrderBookDiffEvent`)。資金調達と清算は、配布物の `basana.Event` の子の全部を `pkgutil.walk_packages` で列べて当たる class が無いことを出力に書き、`対応なし`。p1-merge-by-time・p3-mixed-one-run・p5 の 2 場面は資金調達か清算を含むので `対応なし`。A〜D も同じ決まりで直す(mihircoding の p5 は型が無いので `対応なし`、C は対象の公開の読み出しで読むか、無ければ `対応なし`、D は ISO の文字列を対象のデータの入口に渡す)。
  6. p4-visible-at-step は、ほかの採点の場面と同じ形(`graded_from`)にする: adapter は T0 + 4 日の呼び出しの中で対象の公開の手段で読んだ結果(`reads`: 手段の名前・返った終値の列)だけを返し、件数と最大の終値は runner が作る。
  7. p2-iso の 2 場面も同じ形にする: adapter は値と、値を出した対象の読み込みの関数(`reader`、`common.qualname(関数)` が関数の物から作る)を返し、runner は `reader` が対象の模組でない(pandas・polars・標準の datetime・場面集の模組)なら採点しない。

## i0-r5-03 [止める] hftbacktest の p4-future-read-attempt は、開いた区間を試さないまま正解と一致になっている

- **なぜ起きたか**:
  1. 場面の文「当てはまる名指し方を全部試し」の「全部」が、場面集のどこにも一覧として固定されていなかった。adapter の書き手が周ごと・対象ごとにその都度読み、第 4 周に `[4:]` が名指し方だと分かったとき(i0-r4-01)、足されたのは資料係の書く新実装の adapter だけで、場面係の持つ 36 候補と当方の現状の adapter は見直されなかった(E の 7 件)。
  2. 採点は「試した読み出しの全部が例外で止まったか」で、試しの数と形を検めない。試しが少ないほど正解になりやすく、**場面集の書き手の手抜きが相手を強く見せる**向きだった。
  3. 試しの記録(`common.Attempts`)は手段と名指し方の大分類(time / position)しか持たず、どの名指し方かが記録に残らないので、試験で網羅を検められなかった。
- **どの作りを変えるか**:
  1. **名指し方の一覧を場面に固定する**(`scenes.py` の p4-future-read-attempt の入力 `namings`、`DEFINITIONS.md` に出る): 位置の読み出し(添字と区間を受ける列)には、最新の次の位置 `n` を使う 8 通り `[n]`・`[n:]`・`[n:n+1]`・`[n-1:n+1]`・`[n::2]`・`[n:n]`・`[n::-1]`・`[:n:-1]`。時刻の読み出しは受ける引数の形ごとに: 1 時刻を受ける形は 5 本目の時刻、終わりだけを受ける形は 5 本目の時刻と 5 本目の 1 日後、始まりだけを受ける形は 5 本目の時刻と今の 1 ns 後、両端を受ける形は (最初, 5 本目)・(5 本目, 5 本目)・(今の 1 ns 後, 5 本目の 1 日後)・(5 本目, 端なし)。次の 1 件を返す呼び出し(覗く・次へ)はそのまま 1 回。
  2. **一覧を当てるのは共通の部品**(`common.try_position_namings(att, 手段, 列, n)`・`common.try_time_namings(att, 手段, 形, 読む関数, 時刻)`)で、adapter は手段と `n`(その対象の数え方での最新の次の位置)か時刻の形を渡すだけ。どの名指し方を試すかを adapter が選べない。記録の 1 件ごとに `shape`(position / time_at / time_until / time_since / time_range / next_call / no_means)と `naming` を持つ。
  3. **runner が網羅を検める**: 手段ごとに、その `shape` の一覧の名指し方が全部そろっていなければ、採点せず `結果なし`(`provenance_error`)。`no_means`(読み出しの手段を持たない対象が、戦略が書く呼び出しを書いて呼んだもの)は、名指す読み出しとして採点に数える(例外が出ずに値が返れば止まらなかった)。
  4. **試験**: 記録された全ての結果の p4-future-read-attempt に `provenance_error` が無いこと、新実装の adapter と当方の現状の adapter と全相手の adapter が共通の部品を通すこと(`test_battery_item0.py`)。
  5. 全 adapter(36 候補・当方の現状・新実装)の p4-future-read-attempt を共通の部品に移す。新実装の adapter は資料係の持ち物だが、runner の検めが全対象に同じに掛かるので、場面係が同じ部品に移し替える(試しの一覧は同じか多くなる。新実装に有利な向きの変更ではない)。

## i0-r5-04 [止める] 上位互換の「含む」を、Basana の汎用の基の class で当てている(repeat_of: i0-r4-03)

- **なぜ起きたか**:
  1. i0-r5-02 と同じ根。「利用者が子 class を足せる」を Basana の機構と読み、その子で運んだ場面の結果を裏付けにした。場面の結果が adapter の作った物だったので、裏付けが循環していた。
  2. i0-r4-03 の直しで入れた機械(`test_superset_and_absent_rows_answer_every_ability_with_a_source`)は、「能 N: 在る/無い」と出所と「含む: 番号」の**形**だけを見て、引いた場面の結果がその候補の今の記録で本当に正解と一致か、その結果が adapter の作った物でないかを見なかった。i0-r4-03 の根本原因に書いた「候補の中身を知らなくても判断が変わらない形を外す」を、含む側の機構の書き方には当てていなかった(「型の数に上限が無い」はどの候補の型にも当たる)。
  3. 含む候補が無い能力(11 OctoBot の資金調達の型)で、規則どおり再現に進む道を取らず、含む側を探し続けた。
- **どの作りを変えるか**:
  1. 検討表の決まり(読み方の節)に書く: 含む側に引けるのは、**走った候補のコードがその能力のために自分で行う機構**(その候補の型・口・並べ方)だけ。「利用者が子 class を足せる」「型の数に上限が無い」「handler の中で書ける」のような、利用者が書き足す余地は含む機構に数えない。含む候補が無い能力が 1 つでもある候補は上位互換にせず、規則どおり再現する((a)(b) で材料が足りなければ「再現できない」)。
  2. **機械で止める**(`test_battery_item0.py`): (i) 上位互換の行の「在る」の能力ごとに、`含む:` の候補が引く場面(`p… が正解と一致`)が、その候補の今の `survey_results/<対象>.tsv` で本当に正解と一致であること(記録から確かめる。文を信じない)、(ii) 引いた場面の出力に `provenance_error` が無いこと(上の runner の検めを通った結果だけ)、(iii) 含む側の文に「の子」「上限が無い」「で書ける」「で運べる」の語が無いこと。
  3. 7 行(P0-1 の 13・52・57・63・123、P0-3 の 11・57)と、同じ根の F(P0-5 の 11)を、直した Basana の結果と他の走った候補の自分の機構で 1 能力ずつ読み直す。11 OctoBot の資金調達(P0-3 の能 5)と同時刻の並び(P0-5 の能 1・2)は、走った候補に含む機構が無いので、配布物のコード(第 4 周に導入した venv の中の原文、(b))どおりに最小の書き直しで再現し(`opponents/repro_11_octobot.py`)、同じ場面集に通す。

## [示唆] i0-r5-06(読み出しの手段を持たない対象が p4-future-read-attempt で正解と一致になる)

固定した要件の P0-4 の測り方は「戦略側から未来時刻の事象を読もうとするコードが、実行時エラーか型エラーで止まるか」で、読み出しの手段を持たない対象の戦略が書く呼び出しは止まる。測り方を変えると後から厳しくすることになる(委任文 §3「要件と判定の固定」)ので、正解の決め方は変えない。代わりに、その試しを `shape = no_means` として記録させ、名指す読み出しとして採点に数える(値が返れば止まらなかった)。手段の有る対象と無い対象は記録の `shape` で分かれる(資料係と批評家が読める)。

## 直している途中で見つけた、同じ根の欠陥(直す前の表に無かったもの)

| # | どこ | 何が誤っていたか | 見つけた方法 |
|---|---|---|---|
| G | 検討表の観点の冒頭の文(P0-1・P0-2・P0-3・P0-5) | 「1 Basana は 3 場面とも正解と一致」「68 quanttrader … は 4 場面とも正解と一致」「1 Basana は 11 場面とも正解と一致」「1 Basana と 98 mihircoding/limitOrderBook は能 1〜3 の 3 場面とも正解と一致」。どれも直したあとの記録と合わない(quanttrader の p2-iso は D の直しで対応なしになった) | 検討表の「正解と一致」を名乗る全ての文を、`survey_results/*.tsv` の今の値と突き合わせた(下の「結果」の i0-r5-04 のコマンド) |
| H | 検討表の P0-3 の 11 OctoBot の行 | 能 3(板の差分)を「無い」としたまま、能 9(6 種を 1 回に混ぜる)を「在る」としていた。57 WonderTrader の行は同じ読み方で能 9 を「無い」としている(行ごとに読み方が違った) | 能 9 を持つ行を全部読み比べた |
| I | 検討表の P0-3 の 11 OctoBot の行 | 能 5(資金調達)・能 6(清算)を、型(`FundingChannel`・`LiquidationsChannel`)が配布物にあることで「在る」としていた。場面集の規則 1「型や名前があることは数えない」に反する。OctoBot の検証では、この 2 型を入力から流す物が無い(下の i0-r5-04 の結果) | 配布物の検証の経路(`octobot_trading/exchange_data/__init__.py` 126-147 行)を読んだ |

## 結果(直したあとに書いた)

合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」。この 3 件の直しで、調査結果の側の数え方が「adapter が作った物」を正解と一致に数えない形になり、新実装と当方の現状も同じ検めを通る。

### i0-r5-02(adapter が作った型で運んだ)

- adapter の class は消えた: `grep -n "class .*(bs\.Event)\|class Generic" opponents/*.py adapters/*.py` → 当たり 0 件。Basana の adapter は配布物の class(`basana.core.bar.BarEvent`・`basana.external.bitstamp.trades.TradeEvent`・`basana.external.binance.order_book.PartialOrderBookEvent`・`basana.external.binance.order_book_diff.OrderBookDiffEvent`)だけで運ぶ(`opponents/basana_adapter.py` 1-18 行の説明、`_event`)。
- 配布物の `basana.Event` の子の全部(Basana の調査の venv で `basana_adapter._EVENT_CLASSES`、pkgutil で辿った)の出力: `['basana.backtesting.order_mgr.OrderEvent', 'basana.core.bar.BarEvent', 'basana.core.event.Event', 'basana.core.event_sources.trading_signal.BaseTradingSignal', 'basana.core.event_sources.trading_signal.TradingSignal', 'basana.external.binance.order_book.PartialOrderBookEvent', 'basana.external.binance.order_book_diff.OrderBookDiffEvent', 'basana.external.binance.trades.TradeEvent', 'basana.external.binance.user_data.Event', 'basana.external.binance.user_data.OrderEvent', 'basana.external.bitstamp.order_book.OrderBookEvent', 'basana.external.bitstamp.orders.OrderEvent', 'basana.external.bitstamp.trades.TradeEvent']`。資金調達と清算の class は無い。`inspect.getsourcefile(basana.external.bitstamp.trades.TradeEvent)` → `…/basana/lib/python3.11/site-packages/basana/external/bitstamp/trades.py` の 75 行。
- 記録(`survey_results/opp_basana.tsv`)の P0-3: p3-trade・p3-book_snapshot・p3-book_delta は正解と一致(受けた物は上の配布物の class、`provenance_1` の carriers)、p3-funding・p3-liquidation・p3-mixed-one-run は対応なし。p1-merge-by-time・p5-same-time-twice・p5-hand-over-order も対応なし(入力に資金調達か清算がある)。
- runner の検め: `run_battery.py` の `provenance_problem` / `checked`。場面集の模組の class(`opponents` ほか)・1 つの class に 2 つの型・ISO を読んだのが対象の外の関数・戦略が貯めた値・名指しの一覧の欠け、のどれかで採点せず結果なし。試験 `test_provenance_check_refuses_an_adapter_made_carrier_and_a_shared_one`・`test_provenance_check_refuses_a_foreign_reader_and_a_strategy_kept_list`(adapter が作った `basana_adapter.Generic` を carrier にした結果は `error` になる)。
- 記録の全部に出所の検めの拒否が無い: `test_no_recorded_result_was_refused_by_the_provenance_check`(36 対象 × 32 場面)・`test_current_impl_passes_the_provenance_check`。対象ごとに全場面を通して 1 つの class が 1 つの型: `test_one_carrier_carries_one_kind_across_all_scenes_of_a_target`。
- 新実装と当方の現状も同じ検めを通る: `PYTHONPATH=src python3 run_battery.py --target new_impl` → `{'正解と一致': 32}; 2 回で違う=0`、`--target current_impl` → `{'対応なし': 23, '正解と一致': 8, '不一致': 1}; 2 回で違う=0`(どちらも出所の検めの拒否 0 件)。
- 批評家の試験 `test_funding_best_cell_of_the_survey_side_does_not_rest_only_on_an_adapter_made_type` は通る(p3-funding が正解と一致の相手は 0 件)。**`test_basana_is_not_credited_with_an_event_type_its_adapter_wrote` の 6 件は落ちる。試験自身の誤り(場面集の規則 8)と判断した理由**: (1) 60 行の `assert "class Generic(bs.Event)" in adapter` は、直す前の adapter の形を前提として固定しており、指摘どおり `Generic` を消すと直したかどうかに関わらず落ちる。(2) 残る判定「p3-trade・p3-book_snapshot・p3-book_delta は正解と一致でない」は、前提「Basana 1.11 の事象の class は `Event` と `BarEvent` だけ(`dir(basana)`)」に立つが、`dir(basana)` は最上位の名前だけで、上の pkgutil の一覧のとおり配布物は約定・板の写真・板の差分の class を `basana.external.*` に持つ。p3-funding・p3-liquidation・p3-mixed-one-run の 3 件は試験の期待どおり対応なしで、落ちるのは (1) の行だけが理由。
- Basana の外部の取引所の class を検証に使ってよいかの線: Basana の検証の入口は、事象の列を受ける公開の `FifoQueueEventSource(events=…)`(event.py 113 行)と `dispatcher.subscribe`(base.py 155 行)で、足の場面もこの入口を使う。配布物の class を配布物の公開の入口に渡しているので、測るもの(型)は対象のコードが出したもの。OctoBot の資金調達(下の i0-r5-04)は、配布物の検証の入口(取り込みの表と updater の一覧)がその型を流さないので「無い」とした。どちらも「対象の検証の公開の入口が、対象の class で流すか」の同じ線。

### i0-r5-03(hftbacktest の p4 の試し)

- 名指し方の一覧は場面に固定した(`scenes.py` の `POSITION_NAMINGS`・`TIME_NAMINGS`・`NAMING_SHAPES`、`DEFINITIONS.md` の p4-future-read-attempt の入力 `namings`)。当てるのは `common.try_position_namings` / `try_time_namings`(adapter は手段と `n` を渡すだけ)。
- 記録(`survey_results/opp_hftbacktest.tsv` の p4-future-read-attempt)は **不一致** に変わった。記録の detail の逐語(抜粋): `[position [n]] hbt.last_trades(0)[位置] の px IndexError: index 4 is out of bounds for axis 0 with size 4 ; [position [n:]] … -> [] ; [position [n:n+1]] … -> [] ; [position [n-1:n+1]] … -> [103.0] ; [position [n::2]] … -> [] ; [position [n:n]] … -> [] ; [position [n::-1]] … -> [103.0, 102.0, 101.0, 100.0] ; [position [:n:-1]] … -> []`。批評家が確かめた `[len:]` → `[]` と同じ振る舞いを、場面集の側の試しが拾う。批評家の試験 `test_hftbacktest_p4_cell_holds_when_the_open_slice_is_tried_too` は通る(記録が正解と一致でなくなったので確かめる対象が無い)。
- 同じ根の E(添字 1 つだけを試した 10 件)は全部、共通の部品に移した。記録の p4 の正しさ(36 対象): 正解と一致は 1 Basana・37 ThePredictiveDev・34 QuantCore の 3 件で、どれも読み出しの手段を持たない対象の書いた呼び出し(shape = no_means)が例外で止まったもの(i0-r5-06 の [示唆] の形。記録の `shape` で分かれる)。位置か時刻の読み出しを持つ対象は全部が不一致。
- runner の網羅の検め: `_attempts_problem`。試験 `test_p4_attempts_must_cover_the_fixed_namings_and_only_compiled_means_may_skip_one`(`[n]` だけの試しは結果なし、Python の手段が名指しを「書けない」とすると結果なし、`go:` の手段なら通る)・`test_every_python_adapter_names_the_future_through_the_common_helpers`。

### i0-r5-04(上位互換の「含む」を Basana の基の class で当てた)

- 7 行(P0-1 の 13・52・57・63・123、P0-3 の 11・57)と F(P0-5 の 11)の「含む」を、走った候補が自分で持つ機構で書き直した(`opponents/CONSIDERED.md`)。能 1(型を持つ事象を流す)= 1 Basana の配布物の class と 61 barter-rs の `DataKind`(barter-data/src/event.rs 124-130 行)、P0-3 の約定・板の写真 = 61 barter-rs の `DataKind::Trade`・`DataKind::OrderBook`、板の差分(57 の委託の明細)= 65 aat の注文の単位の事象 `EventType.OPEN`・`CANCEL`・`CHANGE`(aat/config/enums.py 39-42 行)。
- **直す前の計画(i0-r5-04 の「どの作りを変えるか」3)から変えたところ**: 11 OctoBot は再現しなかった。配布物の検証の経路を読むと、資金調達は入力から流さない(`octobot_trading/exchange_data/__init__.py` 146 行の注釈の逐語「trading_constants.FUNDING_CHANNEL: [backtesting_enums.ExchangeDataTables.FUNDING] only hard coded value for now」、`funding_updater_simulator.py` 39-50 行が設定の率 `backtesting_exchange_config.funding_rate`(`exchange_simulator.py` 193-194 行、既定 `constants.py` 200 行 0.00005)を 8 時間ごとに流す)。清算は検証で流す物の一覧(126-135 行)に無く、清算の channel を流すのは実の取引所の websocket の feed だけ(`constants.py` 265 行)。よって能 5・能 6 は「無い」(場面集の規則 1「型や名前があることは数えない」)で、含む候補の要らない能力になった。再現しても、場面 p3-funding の入力(資金調達 1 件)を渡す口が配布物に無いので、結果は対応なしで決まる。能 9 は H の直しで「無い」。残る在る能力(1・2・4・7・8)は全部、走った候補の機構で含む。
- P0-1 の能 3(時刻で合わせる)と P0-5 の 11 の能 1・2(同時刻の並びの規則・渡す順に依らない)の含む側は Basana が自分で持つ機構(`EventMultiplexer.peek_next_event_dt`、base.py 47-61 行 / source の `priority` と base.py 92 行のヒープの鍵)。場面の結果は、入力に Basana に無い資金調達・清算があるので対応なし。代わりに、同じ入力から Basana の配布物の型(約定と足)だけを残して同じ adapter の関数に通した試しを記録した(`survey_results/attempts/1.log` の「probe r6-1」、コード `survey_results/attempts/1_probe_r6-1.py`、Basana の調査の venv)。出力の逐語: `P1-MERGE handed_over_order [["trade", 1700179200000000000], ["trade", 1700438400000000000], ["bar", 1700092800000000000], ["bar", 1700352000000000000]]` → `P1-MERGE delivered [["bar", 1700092800000000000], ["trade", 1700179200000000000], ["bar", 1700352000000000000], ["trade", 1700438400000000000]] … EQUAL True`、`P5 hand_over ['trades', 'bars'] … FOLLOWS True`・`P5 hand_over ['bars', 'trades'] … FOLLOWS True`・`P5 distinct_orders_over_hand_overs 1`(carriers は `basana.core.bar.BarEvent`・`basana.external.bitstamp.trades.TradeEvent`、runner の `_carrier_problem` は None)。
- 機械で止める: `test_every_scene_a_containment_cites_as_correct_is_correct_in_the_records`(含む側の文が「p… が正解と一致」と書く場面を、同じ文が名指す走った候補の今の記録で 1 件ずつ確かめる。引いた試しの記録が在ること)と `test_no_containment_rests_on_what_a_user_could_add`(含む側の文に「の子」「上限が無い」「上限の無い」「で書ける」「で運べる」「書き足せ」が無い。P0-7 は能力そのものが利用者の実装を渡す口なので外した。理由は試験の説明に書いた)。直す前の検討表(`scratchpad/bt/r6/item0_r6-1_scenekeeper_CONSIDERED.before.md`)をこの 2 つの試験にかけると、`P0-1 13 DeviaVir/zenbot 能 3: p1-merge-by-time is cited as 正解と一致 but none of ['opp_hftbacktest', 'opp_basana'] has it in survey_results` と `('P0-1', '13 DeviaVir/zenbot', 1, 'の子', …)` で 2 件とも落ちる(直したあとの版では通る)。
- 批評家の試験 `test_no_superset_skip_rests_on_basanas_generic_event_carrier` は通る。
- G(冒頭の文)は、今の記録の数(`python3 survey_counts.py`)に合わせて書き直した。検討表の「p… が正解と一致」の文の全部について、その場面が正解と一致の走った候補が在ることも確かめた(0 件の場面を名乗る文は 0 件)。
- `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md --write` の最後の行: `OK 誤り 0 件`。

### 同じ根 A〜D の結果(記録の今の値。`survey_results/*.tsv`)

- A(98 mihircoding/limitOrderBook の p5): p5-same-time-twice・p5-hand-over-order は対応なし(detail「約定・足・資金調達・清算を型として持たない(MessageBus が配るのは動作(action)だけ…」)。
- B(Basana の p2): 約定は `basana.external.bitstamp.trades.TradeEvent` で運ぶ。p2-event-time-exact・p2-one-ns-apart が正解と一致の相手は 61 barter-rs・69 gobacktest・23 hftbacktest・37 ThePredictiveDev・34 QuantCore・68 quanttrader・33 SarthakDalmia1 の 7 件で、carriers はどれも対象の物(`rust:barter_data::event::DataKind::Trade`・`go:*gobacktest.Bar`・`hftbacktest.TRADE_EVENT`・`builtins.dict`(ThePredictiveDev の run_backtest が戦略に渡す辞書)・`quantcore._core.MarketDataEvent`・`quanttrader.data.tick_event.TickEvent`・`cpp:execution_simulator MarketData(Tick)`)。
- C(p4-visible-at-step): 正解と一致は 8 件で、どれも対象の読み出しの返り値から runner が作った値(`provenance_1` の reads: `self.data.Close`・`self.data.close.get(size=len(self.data))`・`go:Data().History()`・`hbt.last_trades(0)`・`ctx.close`・`getCloseDataSeries()`・`data_provider.get_price(…)`・`data_board.get_hist_price(…)`)。戦略が貯めた列で答えていた 1 Basana・34 QuantCore・20 VnPy・6 Ziplime は、件数と値を返す公開の読み出しが無い(Basana・QuantCore。VnPy の `load_bar` は過去の足を on_bar に流し直すだけ)ので対応なし、Ziplime は `data.history` を読んだ値が正解と合わず不一致。
- D(p2-iso-utc・p2-iso-offset): 正解と一致は 61 barter-rs・37 ThePredictiveDev・62 qf-lib・18 zipline-reloaded の 4 件で、reader は対象の読み込みの関数(`rust:barter_data::streams::consumer::MarketStreamEvent`(serde の Deserialize)・`trading_simulator.backtest.runner.run_backtest`・`qf_lib.data_providers.csv.csv_data_provider.CSVDataProvider`・`zipline.data.bundles.csvdir.csvdir_equities`)。adapter が自分で `pd.Timestamp` などを呼んでいた 10 件は、ISO の文字列を対象の入口に渡すと対応なし(入口が受けない)か、対象の値が正解と合わない。

## 提出前の吟味(委任文 §3「提出前の吟味」(1)〜(5))

1. 読み直したもの: 固定した要件(`REQUIREMENTS.md` の P0-1〜P0-7 の行と §2)、委任文の「場面集の規則」1〜9・「動かせない候補の検討と再現」・「要件と判定の固定」、第 5 周の批評家の指摘の全文(i0-r5-01〜07)、前の周の根本原因(`ROOTCAUSE_r4-1.md`・`ROOTCAUSE_r5-1.md`)。
2. 指摘ごとの根拠(ファイルと行・コマンドと出力)は上の「結果」の各節に書いた。
3. 同じ根を全体で直した: A〜I(表 2 つ)。見つけ方はそれぞれの行の「見つけた方法」の列。
4. 試験: 場面係の試験 `tests/bt/battery/item_0`、批評家の試験 `tests/bt/critic/item_0`、作業者の試験 `tests/bt/item_0`、全試験(下)。
5. 非常に厳しい批評家が止めそうなものと、その扱い:
   - 「Basana の約定・板の class は実の取引所(bitstamp・binance)の feed の class で、検証の型ではない」: 配布物の class を、配布物の公開の検証の入口(`FifoQueueEventSource`)に渡したもので、足と同じ入口。線は i0-r5-02 の結果の最後の段落に書いた。批評家の試験のうち 6 件がこれと食い違う(規則 8 の扱い、上に理由)。
   - 「含む側の裏付けが、場面集の runner の外の試し(`attempts/1.log`)」: 場面の入力に Basana に無い型があるため、場面の結果では裏付けられない。試しは同じ adapter の関数・同じ runner の検め(`checked`・`_carrier_problem`)・同じ規則(`stated_rules.predicted`)を通し、入力から資金調達と清算の入力を除いただけ。コードと出力を記録に残した。
   - **[判断] p1-merge-by-time・p5-same-time-twice・p5-hand-over-order の入力が資金調達・清算(P0-3 の能 5・能 6)を含み、走った候補に両方を持つものが無いので、調査結果の側の最良の行がこの 3 場面で対応なしになる**。場面の入力は変えなかった。理由: 固定した要件 §1 の核の事象の型に資金調達・清算が入っていて、P0-5 の測り方「同時刻に複数型の事象を仕込んだ入力」をこの核の型で作るのは要件どおりで、資金調達・清算を並べられないのは調査結果の道具の事実。直すなら場面の入力の型を約定と足に減らすことになり、並べ方の試しが 24 通りから 2 通りに弱まり、作業者の試験(`tests/bt/item_0/test_bt0_scene_set.py` の `test_hand_over_order_of_streams_does_not_matter_but_one_stream_keeps_its_order` は 24 通りを書いている)も変わる。含む側の判断には上の試しを使った。監査役・批評家が場面の偏りと読むなら、場面の入力の型を分ける(時刻で合わせる・同時刻の並びを、対象が持つ型で測る場面を足す)のが次の直し。
   - 「p4 で正解と一致の 3 件は、読み出しを持たない対象」: i0-r5-06 の [示唆] の形のまま(固定した測り方の範囲。後から厳しくしない)。記録の `shape = no_means` で読み出しを持つ対象と分かれる。
   - 再現できない・再現しなかった候補の数は変わらない(検討表の集計の区画、`check_bt_considered.py` が書く)。

## 試験の結果

- 場面係の試験: `PYTHONPATH=src python -m pytest tests/bt/battery/item_0` → `37 passed`(第 r6-1 回に足した 11 件を含む)。
- 批評家と作業者の試験: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 tests/bt/item_0` → `6 failed, 738 passed, 2 skipped`。落ちた 6 件は全部 `test_i0r5_battery_opponent_grading.py::test_basana_is_not_credited_with_an_event_type_its_adapter_wrote`(試験自身の誤り、理由は i0-r5-02 の結果の節。場面集の規則 8 により試験は変えていない)。
- 全試験(`setsid nohup … python -m pytest`、記録 `scratchpad/bt/pytest_item0_r6-1_scenekeeper.log`、2026-09-24T07:30:54Z 開始・07:39:06Z 終了): `6 failed, 3669 passed, 6 skipped, 1 warning in 491.23s (0:08:11)`。落ちたのは上の 6 件だけ(`grep ^FAILED` の全行)。
- mutant: `PYTHONPATH=src python3 mutant.py --check` → `changed scenes: ['p4-received-time']` / `OK`。
- 定義: `python3 gen_definitions.py` → `wrote … DEFINITIONS.md (32 scenes)`(`test_definitions_in_sync_with_scenes` が通る)。
