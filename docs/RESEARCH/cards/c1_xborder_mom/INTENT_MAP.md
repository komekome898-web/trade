# カード 1(xborder_mom): 意図とロジックの突き合わせ(測る前に行う)

研究手順書 §0.5(L-043)の書式。手本は `docs/legacy/KATSUO_INTENT_MAP.md`。
W4 の仕様 `docs/DISCUSSIONS/2026-10-02_W4_spec.md` §2 の 2(意図の地図)と §2 の 5(今の bot のコードとの突き合わせ)。

- **このカードの目的**: 今の paper bot の戦略を、研究の口(`bot.research.cards`)に移す。研究のプログラムと本番のプログラムを同じにする要求(L-540)の最初の 1 枚(W4 の仕様 §1 の 1 行目)。だから「意図」は **今の bot の動き** そのものである。
- **意図の出所(原文)**: 次の 5 つ。逐語は CARD.md の「原文(逐語)」。
  - S1 `src/bot/strategy/xborder_momentum.py` の docstring(1〜11 行)
  - S2 `config/config.yaml` の設定と注記(3・4・13〜17・19〜21・23・30〜33・35〜37・39〜42 行)
  - S3 `docs/DISCUSSIONS/2026-10-02_W5_stage7_design.md` §5-1(今の動きの説明と、kind を出す理由)・§5-2 の T-A の場面
  - S4 `src/bot/market_data/external_feed.py` の docstring と `close_for` の docstring
  - S5 `src/bot/main.py` の注記(764 行「decide only on completed candles」、772 行「protective stop-loss overrides the strategy」)
- **ロジックの出所**: カード `src/bot/research/cards/library/c1_xborder_mom.py`(行番号はこのファイル)。突き合わせる相手 = 今の bot のコード `src/bot/strategy/xborder_momentum.py`(以下「bot の行」)。
- **印**: ○ 意図どおり / **△ 代理**(意図そのものではなく代理で実装)/ **✕ 未実装**(射程外と明記したものを含む)/ **＋ 意図に無い実装**
- **主張の印**: 【事実】= ファイル・出力で確かめた / 【推定】= 確かめていない読み / 【仮定】= 置いた前提。

> **この表全体に掛かる但し書き**: 研究手順書 §0.5 は「実装を見てから意図を書いてはならない」と定める。このカードの原文の一部は今の bot の**コードそのもの**なので、その規則を完全には守れない。そこで、意図(§1)は**文章の原文**(S1 の docstring・S2 の注記・S3 の説明・S4 の docstring・S5 の注記)だけから固定し、コードにしか無い動き(文章に書かれていない分岐・定数)は §4 のコード側の走査で ＋ として挙げた。

---

## 1. 意図(文章の原文から、1 項 = 1 主張。実装を見る前に固定)

| # | 意図 | 原文の該当語(逐語) |
|---|---|---|
| I-1 | 持つ銘柄は bitFlyer の FX_BTC_JPY | S2 19〜20 行「follow Binance BTCUSDT moves on bitFlyer FX_BTC_JPY, long AND short.」/ S2 3 行「product_code: FX_BTC_JPY」 |
| I-2 | 信号を取る市場は Binance の BTCUSDT | S2 39〜42 行「Leader market feed for xborder_momentum (public Binance data, read-only)」「symbol: BTCUSDT」/ S1 1 行「follow strong moves on a leader market (Binance)」 |
| I-3 | 信号 = Binance の k 本前からの値動き(対数)mom | S3「Binance の k 本前からの値動き(対数)mom。」 |
| I-4 | k = 30(窓の本数) | S2 31 行「k: 30 # leader momentum window (bars)」/ S3「k = 30」 |
| I-5 | 1 本 = 1 分 | S2 4 行「candle_interval_sec: 60」 |
| I-6 | mom > 0.8% で「買い」 | S2 32 行「thr_pct: 0.8 # enter long above +thr, short below -thr (%)」/ S3「mom > 0.8% で「買い」」 |
| I-7 | mom < −0.8% で「売り」(売りからも入る) | S2 32 行(同上)/ S2 20 行「long AND short」/ S3「< −0.8% で「売り」」 |
| I-8 | \|mom\| ≤ 0.05% で「決済」 | S3「\|mom\| ≤ 0.05% で「決済」」/ S2 33 行「exit_pct: 0.05 # flatten when \|leader momentum\| fades below this (%)」 |
| I-9 | その間(0.05% < \|mom\| ≤ 0.8%)は「様子見」 | S3「その間は「様子見」」 |
| I-10 | Binance の値が無ければ「様子見」 | S3「Binance の値が無ければ「様子見」」/ S1 10〜11 行「missing/stale leader data yields HOLD.」/ S4「never trades on a stale or missing leader price.」 |
| I-11 | Binance の値の抜けは、最大 2 枠前まで遡って埋める。それより古ければ値が無い | S4 `close_for`「Close of the given interval, falling back to at most `max_age_intervals` earlier intervals; None when data is too stale.」/ S3 §5-2「Binance の値の抜け(2 枠前までの遡りと、それを超える抜け)」 |
| I-12 | ある足の Binance の値 = その足の区間の Binance の終わりの価格 | S4「The feed builds per-interval closes that main.py merges into the candles frame as a `leader_close` column.」 |
| I-13 | 判断は、足が完成したときだけ | S5 764 行「decide only on completed candles」 |
| I-14 | 判断の足 = bitFlyer の 1 分足(毎分) | S2 4 行「candle_interval_sec: 60」/ S5 764 行(同上) |
| I-15 | 持ち高 e = +1(買い)/ −1(売り)/ 0(決済)/ 前の足の e(様子見) | S3「**カード `xborder_mom`**: e = +1(買い)/ −1(売り)/ 0(決済)/ 前の足の e(様子見)。」 |
| I-16 | その足の信号の種類 kind(買い・売り・決済・様子見)を出す | S3「`kind` に「買い・売り・決済・様子見」を入れる。」 |
| I-17 | 損切り(含み損 0.5%)は bot の守りで、版の判断より先 | S3「損切り: 足が完成したときだけ、含み損が 0.5% 以上なら決済(版の判断より先)。」/ S2 35〜37 行「Protective stop: flatten any position losing more than this % of entry price.」「stop_loss_pct: 0.5」/ S5「protective stop-loss overrides the strategy」 |
| I-18 | 反対の信号では決済だけ(ドテンしない)。同じ向きなら何もしない(増し玉しない) | S3「売りを持っていれば**決済だけ**(ドテンしない。次の足でまだ「買い」なら買う)」「持っている向きと同じなら何もしない(増し玉しない)。」 |
| I-19 | 新しく建てる前に SFD の守りを通す | S3「持っていなければ、SFD の守りが通れば買う。」/ S2 13〜17 行「Basis-anomaly guard: refuse NEW CFD entries when \|CFD-spot\| divergence is abnormal.」「sfd_guard_pct: 4.5」 |

S1 4〜8 行の「Research basis」(過去の調べの数値)は、意図にもカードの根拠にも使わない(全捨て L-019)。CARD.md の「水準とその出所」も同じ。

## 2. 対応表(意図 → カードの実装)

| # | 意図 | 実装(カードの行) | 印 | 備考 | 試験(`tests/research/cards/library/test_c1_xborder_mom.py`) |
|---|---|---|---|---|---|
| I-1 | 持つ銘柄 = FX_BTC_JPY | カードは銘柄を選ばない。走らせる足の系列(CARD.md「使うデータと遅れ」の bitFlyer lightchart FX_BTC_JPY 1 分足)で決まる | ○ | 研究の口は「1 本の銘柄の足の系列に 1 枚のカード」(W1 の仕様 C2) | — (測定の組み立ての側) |
| I-2 | 信号の市場 = Binance BTCUSDT | `LEADER`(61 行)、`requires`(98 行) | ○ | 系列の中身は CARD.md の Binance BTCUSDT 1 分足 | `test_defaults_are_the_bot_settings` |
| I-3 | Binance の k 本前からの値動き(対数) | 126〜132 行: `now` = 足の始まり s の分、`past` = s − k 分の分、`mom = np.log(now / past)` | ○ | 「k 本」を **Binance の k 分**として実装した(S3 の語「Binance の k 本前」)。bot のコードは bitFlyer の足の並びで k 個前(bot の行 38〜39)だが、bot は約定ではなく 5 秒ごとの気配から足を作るので(I-14 の備考の【事実】)、気配が取れている限り足は毎分でき、bot の実際の動きは「k 分前」である。**リードの答え(2026-10-02、差し戻し 1 回目の 2)**: 「あなたの読み(Binance の k 分前)でよい。理由: bot は気配から毎分足を作るので、bot の実際の動きは「k 分前」である。」。気配が 1 分まるごと取れなかった分だけ、bot の足の並びと k 分がずれる。違いは §6 | `test_window_is_k_binance_minutes`、`test_same_kinds_as_the_bot_code` |
| I-4 | k = 30 | `K = 30`(66 行)。出所は CARD.md「水準とその出所」 | ○ | | `test_defaults_are_the_bot_settings` |
| I-5 | 1 本 = 1 分 | `MINUTE_NS`(59 行)、`_leader` の枠の幅 | ○ | | `test_defaults_are_the_bot_settings` |
| I-6 | mom > 0.8% で買い | 133〜134 行(`>`、`thr = float(thr_pct) / 100` は 94 行。bot の行 30・46 と同じ作り) | ○ | | `test_buy_above_threshold` |
| I-7 | mom < −0.8% で売り | 135〜136 行 | ○ | | `test_sell_below_threshold` |
| I-8 | \|mom\| ≤ 0.05% で決済 | 137〜138 行(`<=`) | ○ | S2 の注記は「fades below this」(未満とも読める)、S3 とコード(bot の行 50)は「≤」。S3 とコードに合わせた(§5 B-1) | `test_close_and_hold_after_buy` |
| I-9 | その間は様子見 | 139 行 | ○ | | `test_close_and_hold_after_buy`、`test_hold_keeps_previous_exposure` |
| I-10 | Binance の値が無ければ様子見 | 129〜130 行(`now` か `past` が無い) | ○ | | `test_leader_fallback_two_minutes`、`test_past_side_fallback` |
| I-11 | 最大 2 枠前まで遡る | `_leader`(112〜120 行)、`MAX_AGE_INTERVALS = 2`(70 行) | ○ | `now` と `past` の両方に掛かる(bot も両方を `close_for` で作る。main.py 767〜771 行) | `test_leader_fallback_two_minutes`、`test_past_side_fallback` |
| I-12 | 足の区間の Binance の終わりの価格 | `_leader` は、区間 [s, s+1 分) の Binance の 1 分足の close(行の時刻 = s = 置き場の open_time。遅れ 60 秒で、足の終わり t = s + 1 分に使えるようになる)を読む(117 行) | **△ 代理** | bot の値は「その分の間に 5 秒ごとに取った最後の気配(`ticker/price`)」(external_feed.py 41〜42 行、config `poll.ticker_sec: 5`)。研究では Binance の 1 分足の close(その分の最後の約定)を使う。差は 1 分の終わりの数秒の値動きと、bot の時計のずれ【推定】。この代理の良し悪しは、paper の判断の記録(`indicator_values.leader_close`)と Binance の 1 分足の close を突き合わせれば切り分けられる(段 7 の T-B と同じ材料。期間は封印にかかるので、この回では測らない)。切り分けるまでは、陰性は「1 分足の close という代理では捉えられない」までしか言えない | `test_reads_the_minute_ending_at_t` |
| I-13 | 判断は足が完成したときだけ | 研究の口が足の終わり t に呼ぶ(`run.py`)。カードは `view.bars` で t までの足しか読まない | ○ | | `test_reads_the_minute_ending_at_t`(t より後の行を読まない) |
| I-14 | 判断の足 = 毎分 | 研究の口は**約定の有る足だけ**でカードを呼ぶ(`run.py` の「空の足では持ち高を取らない」)。lightchart は約定 0 の分を null にする | **△ 代理** | bot は約定ではなく気配から足を作る【事実】: `run_forever` が `ticker_sec`(config 46 行「ticker_sec: 5」)ごとに `step()` を呼び(main.py 1807・1856・1861 行)、`step()` は毎回 `poll_ticker()` で最終価格を取り(main.py 705 行)、`add_trade(tick.timestamp, tick.price, 0.0)` で足に入れる(main.py 757 行)。`tick.timestamp` は約定の時刻ではなく bot の時計(`src/bot/market_data/feed.py` 143 行 `timestamp=self._clock()`)、価格は `ltp`(同 141 行)。`CandleBuilder.add_trade` は、気配が 1 つでも入った分に足を作る(同 77〜99 行)。約定から足を作る道(`use_flow_candles`)は既定で使わず(main.py 175 行、既定 False)、config に設定が無い【事実: `grep -n use_flow_candles config/*.yaml` が何も返さない】。よって bot は、約定の無い分にも、気配が 1 回でも取れれば足を作って判断する【事実: コード】。気配が 1 分まるごと取れない分(通信の失敗など)には足ができない【事実: コード】。実際の運転で毎分そろっているかは【未確認】。研究では約定の無い分は判断しない。次の約定の有る足で同じ式を計算し直すので、その分の判断が遅れる(持ち高の変わり目がずれる)。約定の無い分のうち、5 分を超えて続く空きは 2017〜2023 年で年 312〜1,316 件(lightchart の README の表。5 分以下の空きの数は README に無い)【事実: README】 | `test_empty_bars_not_decided` |
| I-15 | e の写し(+1 / −1 / 0 / 前の e) | 141〜148 行。最初の e は 0(99 行) | ○ | | `test_hold_keeps_previous_exposure`、`test_initial_zero_and_insufficient_history` |
| I-16 | kind を出す | `last`(`Decision`: t・e・kind・理由・mom)と `kinds()`(呼ばれた順の全部)。149〜152 行 | ○ | `Card` の口は数を 1 つ返す形なので、kind はカードの持ち物として出す。合成器 X0 はここから読む【設計。段 7 の §5-1】 | `test_kind_log_matches_calls` |
| I-17 | 損切り 0.5% は bot の守り | 実装しない | **✕(射程外: カードの外)** | リードの委任文(この回の作業の指示。オーナーの逐語ではない)の「今の bot の損切り(含み損 0.5%)は bot の守りでありカードの外」と S3 の分け方(損切りは版の判断より先に bot が掛ける)。損切りのあと「様子見」なら持たないままでいる動きは、合成器 X0 が kind を見て再現する(S3「kind を出す理由」の (2))。研究の測定(段 2)の損益には損切りが入らない | — |
| I-18 | ドテンしない・増し玉しない | 実装しない | **✕(射程外: カードの外)** | S3 が合成器 X0(`legacy_xborder`)に分けた。カードは「買い」で e = +1 を出し、売りを持っているときに決済だけにするのは X0 の仕事。研究の測定では e がそのまま持ち高になるので、「売り → 買い」は 1 本でドテンした扱いになる【事実: W1 の仕様 C2 の損益の式】 | — |
| I-19 | SFD の守り | 実装しない | **✕(射程外: カードの外)** | bot の守り(main.py 1031〜1046 行 `_sfd_blocked`: FX と現物 BTC_JPY の最終価格の乖離が 4.5% 以上なら新しく建てない。現物の価格が取れなければ建てない)。カードの外。今の期間は全部 SFD の時代(W4 の仕様 §3)で、守りで止まる足を研究の側で再現するには bitFlyer の現物 BTC_JPY の価格が要る(この票の外。置き場 `backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906/` がある【事実: 封印の台帳に名前がある】が、この回は使わない)。測定には入れない(射程に書く) | — |

## 3. カードの外に置いた、bot の殻の動き(§1 の意図項に当たらない分を含む)

S3 の分け方(カード / 合成器 X0 / bot)に従って外した。どれも持ち高の向きを決める**信号の中核ではない**(中核の I-3〜I-11 は全部入れた。A-9)。

| 動き | 場所(bot) | 外した理由 |
|---|---|---|
| 損切り(含み損 0.5%) | main.py 772〜790 行、config 37 行 | I-17 |
| 反対の信号で決済だけ / 増し玉しない | main.py 804〜821 行 | I-18 |
| SFD の守り | main.py `_sfd_blocked`、config 17 行 | I-19 |
| 売りが許される銘柄か(`product.shortable`) | main.py 815 行 | 銘柄の性質。FX_BTC_JPY は売れる(config 3 行の注記「shortable」) |
| 注文の量・仮想の資金 | config 11 行ほか | 研究の口は 1 単位あたりで測る(W1 の仕様 C2) |
| キルスイッチ・データの古さで止まる・事前の検査(日次の損失など) | main.py 759〜762 行ほか | bot の運用の守り。カードの外(段 7 の §3-3) |
| 止まったあと足の履歴を捨てる(再開後は k + 2 本たまるまで判断しない) | main.py 1693〜1705 行 | bot の運用。研究のデータには止まりが無い |
| 部品の門(`gate_entry`、composite) | main.py 793〜801 行 | 今の設定は `name: xborder_momentum`(config 23 行)で、門は掛かっていない【事実】 |

## 4. コード側からの走査

### 4-1 bot のコード(`src/bot/strategy/xborder_momentum.py`)の分岐と定数を全部

| bot の行 | 分岐・定数 | 当たる意図 | カードでの扱い | 印 |
|---|---|---|---|---|
| 26 | `min_history = k + 2` | 無し(文章の原文に「履歴が足りない」は無い) | 残した(123〜125 行)。系列の始まりの 31 分だけに効く。k + 1 本あれば計算できるのに k + 2 本を待つ理由は原文に無い。新旧を同じにするため残す | **＋** |
| 29〜31 | コードの既定値 k = 10、thr 0.8、exit 0.1 | 無し | 外した。動いている値は config(k 30、exit 0.05)で、既定値は使われない。カードの既定値は config の値 | **＋(外した)** |
| 33〜34 | `leader_close` の列が無ければ様子見 | I-10 に近い | 不要。研究の口は `requires` の系列が渡されなければ走らせない(`run_card` が拒む) | ○(口が担う) |
| 35〜36 | 履歴が足りなければ様子見 | 26 行と同じ | 123〜125 行 | **＋** |
| 38〜39 | `iloc[-1]`・`iloc[-1 - k]`(bitFlyer の足の並びで k 個前) | I-3 | Binance の k 分前として実装(§6) | ○ |
| 40 | NaN なら様子見 | I-10 | 129 行(値が無い = None) | ○ |
| 40 | `leader_past <= 0` なら様子見 | 無し | 残した(129 行)。値段が 0 以下になることは無いので、実際には効かない【推定】 | **＋** |
| 43 | `np.log(leader_now / leader_past)` | I-3 | 132 行。同じ式。`leader_now` が 0 なら −inf で「売り」、負なら NaN で「様子見」になるのも同じ(131 行の `np.errstate` は警告を消すだけで、値は変えない) | **＋**(0 以下の値の扱い。意図に無い) |
| 44〜45 | 記録用の `ind`(mom・Binance の値・終値) | 無し | 記録だけ。カードは `Decision.mom` を残す(150 行)。持ち高には効かない | **＋** |
| 46〜52 | 4 つの分岐と理由の文 | I-6〜I-9 | 133〜139 行。理由の文は短い符号に変えた(記録だけ) | ○ |

### 4-2 bot の周り(`external_feed.py`・`main.py`)

| 場所 | 分岐・定数 | 当たる意図 | カードでの扱い | 印 |
|---|---|---|---|---|
| external_feed.py 41〜42 行 | 気配を取った時刻の分の始まりを鍵にして、最後の値を残す | I-12 | Binance の 1 分足の close で代える | △(I-12) |
| external_feed.py 50 行 | `max_age_intervals = 2` | I-11 | 70 行 | ○ |
| external_feed.py 44〜47 行 | 3,000 枠より古い値を捨てる | 無し | 不要。k + 2 = 32 枠より十分大きいので判断に効かない【事実: 3000 > 32】 | (効かない) |
| main.py 767〜771 行 | 各足の始まり `c.start` で `close_for` を引く | I-12 | 117 行: 足の始まり s の分の行(行の時刻 s = open_time)を引く | ○ |
| main.py 757 行 | 足は気配(約定の量 0)から作る | I-14 | 研究の足は約定から作った lightchart | △(I-14) |

### 4-3 カードのコードの分岐と定数を全部

| カードの行 | 分岐・定数 | 当たる意図 | 印 |
|---|---|---|---|
| 59 `MINUTE_NS` | 1 分 | I-5 | ○ |
| 61 `LEADER`、62 `LAG_NS = MINUTE_NS`(60 秒) | 系列の名前と遅れ | I-2、CARD.md「測定の設定」 | ○ |
| 66〜68 `K`・`THR_PCT`・`EXIT_PCT` | 30・0.8・0.05 | I-4・I-6〜I-8 | ○ |
| 70 `MAX_AGE_INTERVALS` | 2 | I-11 | ○ |
| 73 `KINDS` | 買い・売り・決済・様子見 | I-16 | ○ |
| 91〜102 `__init__` | 引数で水準を変えられる | 無し(既定値が bot の設定。試験と、別の版を登録するときのため) | **＋**(既定値以外で測るなら別の版として記録する) |
| 99 `self._e = 0.0` | 最初の e | I-15 | ○ |
| 112〜120 `_leader` | 行の時刻 = 分の始まり(open_time)、2 枠前まで | I-11・I-12 | ○ / △ |
| 123〜125 | 履歴が k + 2 本に満たなければ様子見 | bot の行 26・35 | **＋** |
| 126 | 足の始まり s を、いま閉じた足から取る | I-3・I-13 | ○ |
| 129 | 値が無い、または past ≤ 0 なら様子見 | I-10 / bot の行 40 | ○ / **＋** |
| 131 | `np.errstate`(0 や負の値での警告を消す) | 無し | **＋**(値は変えない) |
| 133〜139 | 4 つの分岐 | I-6〜I-9 | ○ |
| 141〜148 | e の写し | I-15 | ○ |
| 149〜152 | kind・時刻・mom の記録 | I-16 | ○ |
| 150 | mom が NaN なら記録は None | 無し | **＋**(記録だけ) |

## 5. 原文どうしの食い違いとバグ(直すか原典のままかを先に決める)

| # | 箇所 | 中身 | 決めたこと |
|---|---|---|---|
| B-1 | I-8 の境 | config の注記は「fades below this」、S3 とコードは「≤」 | **原典(コード)のまま「≤」**。S3 も「≤」と書いている。境ちょうどの値は浮動小数でほぼ起きない【推定】 |
| B-2 | 値段が 0 以下 | docstring は「missing/stale leader data yields HOLD」。コードは `leader_now = 0` で −inf →「売り」 | **原典のまま**。値段 0 は「無い値」ではなく、実際に起きない【推定】。新旧の突き合わせを汚さないため |
| B-3 | コードの既定値 | k 10・exit 0.1 と config の k 30・exit 0.05 が違う | 動いている値(config)を使う。既定値は使わない |
| B-4 | 損切りのあとの e | bot は損切りのあと「様子見」なら持たないが、カードの e は前の e(±1)のまま | **原典の分け方のまま**(S3: カードの外、合成器 X0 が kind で再現する)。研究の測定の e は損切りの無い持ち高 |

## 6. 別の作り手が原文だけから書き直したときに、食い違うと予想される箇所

W4 の仕様 §2 の 5(持ち高が食い違う足が全体の 0.1% を超えたら止める)のために、先に書く。

1. **「k 本前」の数え方**(I-3)。このカードは Binance の k 分前(S3 の語)。bot のコードの字面(`iloc[-1 - k]`)どおりに **研究の足の並びで k 個前** と書くと、bitFlyer に約定の無い分(lightchart の null の分、研究の口では届かない)が窓の中にあるたびに、窓が k 分より長くなり、その後の k 本の判断が食い違う。2017〜2023 年の bitFlyer の 5 分超の空きは年 312〜1,316 件(lightchart の README の表)【事実: README】なので、0.1% を超える見込み【推定】。食い違ったら、まずこの理由かを足ごとに確かめる。
2. **行の時刻の決め方**(I-12)。このカードは、Binance の行を置き場の `open_time`(分の始まり)のまま遅れ 60 秒で読み、t で終わる分の行を行の時刻 t − 60 秒で引く(リードの答え、§9 の 1)。書き直しが行の時刻を分の終わりにずらして遅れ 0 にした場合、遅れの宣言が違うので `run_card` が拒む(食い違いの前に止まる)。書き直しが分の始まりのまま遅れ 0 で読むと、close を 1 分早く読む(未来を読む)ので、全部の足で 1 分ずれる。
3. **履歴の門**(bot の行 26 の k + 2)。書き直しが k + 1 にすると、系列の始まりの 1 本だけ食い違う。

## 7. 読み直しの記録(提出の前に、原文と突き合わせた)

- §1 の 19 項を、CARD.md の原文の逐語と 1 項ずつ突き合わせた。S3 の箇条(k・閾値・決済の帯・様子見・Binance の値が無いとき・買いのときの扱い・損切り・e の写し・kind)は全部どこかの項に当たる。S2 の注記(k・thr・exit・stop_loss・leader・sfd_guard・product_code・candle_interval_sec・long AND short)も全部当たる。
- ○ の各項に、試験が 1 つ以上ある(§2 の右端)。加えて、bot のコード(`XborderMomentumStrategy.on_candles`)と同じ入力で 3,000 足を並べ、kind が全部の足で一致することを試験にした(`test_same_kinds_as_the_bot_code`。Binance の行の抜け 154 か所、うち 4 分続く抜け 1 か所を含む。bitFlyer の足は毎分そろえた)。
- 外した ✕ の 3 項(I-17〜I-19)は、どれも信号の中核ではなく、S3 がカードの外に分けたもの。○ や △ の巻き添えは無い(§0.5 の「外す作業の点検」): I-3〜I-11 の分岐は bot のコードと同じ形で全部残っている。

## 8. 数

| 印 | 数 | 項 |
|---|---|---|
| ○ | 14 | I-1〜I-11、I-13、I-15、I-16 |
| △ 代理 | 2 | I-12(Binance の値 = 1 分足の close)、I-14(判断は約定の有る分だけ) |
| ✕ | 3 | I-17 損切り、I-18 ドテンしない・増し玉しない、I-19 SFD の守り(3 つとも射程外: カードの外) |
| ＋ | 7 | 履歴の門 k + 2(bot の行 26・35)/ past ≤ 0 で様子見 / 0 以下の値での −inf・NaN の扱い(bot の行 43)/ `np.errstate` / 記録(`ind`・`Decision.mom`・None)/ `__init__` で水準を変えられること / コードの既定値(外した) |

## 9. 迷った点と、リードの答え(2026-10-02、差し戻し 1 回目)

初稿の迷った点 1〜6 に、リードが次のとおり答えた(リードの決定。オーナーの逐語ではない)。このファイルと CARD.md・関数・試験はこの答えに合わせて直した。

1. **Binance の行の時刻と遅れ** → 「行の時刻 = 置き場の open_time のまま(1 分の始まり)、lag_ns = 60 秒」。カードは t で終わる分の行を `ref_at(name, t − 60 秒)` で読む。理由(リード): 置き場の値をずらさないので、ずらし忘れが起きない。遅れの宣言が違えば run_card が拒む。
   - 直したところ: 関数の `LAG_NS = MINUTE_NS`(62 行)と `_leader` の行の時刻(117 行: 足の始まり s − 遡りの枠)。試験の系列の宣言(遅れ 60 秒、行の時刻 = 分の始まり)。`test_other_lag_is_refused` は、遅れ 0 の宣言(open_time の行では未来を読む宣言)を拒むことを確かめる形に変えた。CARD.md の「使うデータと遅れ」「測定の設定」。
2. **「k 本前」の数え方** → 初稿の読み(Binance の k 分前)でよい。理由は §2 の I-3 の備考に書いた。
3. **測る期間の端** → 日本時間の日の境にそろえる。始まりは系列がそろう最初の日本時間の 0 時、終わりは 2023-12-17T15:00:00Z(日本時間の 12-18 の 0 時。封印の境の前)。CARD.md の「測る期間」を直した。
4. **＋ を残すこと** → 残してよい。研究手順書 §0.5 の「＋ は第 1 周では外す」からそれる理由: このカードの目的は、動いている bot の移植と新旧の一致(L-552 で決まった段 7 の橋の案 A。W4 の仕様 §1 の 1 行目の (a))であり、bot のコードにある ＋(履歴の門 k + 2・past ≤ 0・0 以下の値の扱い)を外すと、新旧の突き合わせ(段 7 の T-A)で食い違う。外した版は測らない。
5. **kind の出し方** → 今の形(カードの持ち物 `last`・`kinds()`)でよい。
6. **I-12・I-14 の射程** → 今の書き方でよい。I-14 の「bot は約定の無い分にも足を作る」は、`src/bot/market_data/feed.py` と `src/bot/main.py` で確かめて【事実】(行番号つき)にした(§2 の I-14 の備考)。射程: このカードの陰性は「1 分足の close で、約定の有る分だけ判断したときには見えない」までしか言えない。
