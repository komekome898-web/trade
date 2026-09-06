# P2-08b 盲点監査(調達票 2026-09-06 版が対象、監査日 2026-09-07 UTC 00:xx、ツール呼び出し 15 回以内)

区分: **致命** = 直さないと単位が成立しない / **要修正** = 第 2 稿で直す / **提案** = 任意。印: 事実 = 本監査の実測または一次文書の引用、推定 = 実測からの外挿、仮定 = 未確認。生取得物は scratchpad のみ(`backtest_data` には置いていない — #3 参照)。

## A. 調達票が見落とした入手経路

### 1(要修正)bitbank の日付指定約定履歴 = 円建て市場の秒データが無料で 9 年分ある
`GET https://public.bitbank.cc/btc_jpy/transactions/YYYYMMDD` はキー不要で当該日の全約定(ms 取引所刻印・tid・side)を返す。実測: 2017-03-01 58 行(上場直後)/ 2018-01-01 11,043 / 2019-01-01 36,677 / 2019-09-01 10,437 / 2020-03-01 11,784 / 2022-03-01 20,530 / 2024-03-01 16,261(同日の bitFlyer Tardis 14,475 と同規模)/ 2025-03-01 13,157 / 2026-08-01 4,781 / 2026-09-05 3,416 行、全て HTTP 200【事実】。
調達票は「受け手 = bitFlyer」に問いを狭めたためこれを探していない。bitFlyer CFD が円市場の価格発見側で bitbank は追随側・床 24bps(KNOWLEDGE (ac))なので**執行先にはならない**が、「Binance→円市場の伝播時間分布の長期変化」を毎日・9 年・無料で測る計測器になる(#7)。GMO は `page` 遡及でも直近数万件のみ(page=100 で 2026-09-06 16:56)、Coincheck は `starting_after/ending_before` が「now unavailable parameter」(HTTP 400)= 最新 100 件のみ【事実】。手元にも `backtest_data/auto_venues_20260905/`(bitbank・GMO 約定 15〜30 秒ポーリング、2026-08-27〜09-05)と `venue_survey_20260827/` があり調達票に未記載。

### 2(要修正)Tardis 無料サンプル: 数は 84 日で正しいが、疎さ・拠点差・板系の欠落を票に書く
実測 3 日: 2021-06-01 219,795 行(2.9 MB)/ 2024-03-01 14,475 行 / 2026-06-01 40,165 行(初回 2 回 429、8 秒待ちで 200)。列は票どおり 8 列、`timestamp` 16 桁 μs 取引所刻印(1.1% は μs 末尾 000 = ms 精度)、`local_timestamp` は **Tardis 拠点の受信時刻**(自宅 PC でも本環境でもない)【事実】。2019-08-30・2019-09-02・2026-07-01・2026-09-01 は 404(1 日以外は無く、9 月分は本日時点で未公開)、docs が掲げる `quotes`/`incremental_book_L2`/`book_snapshot_5` の bitflyer サンプルと binance/binance-futures の BTCUSDT サンプルも本日は全て 404 → **板系と Binance 側は Tardis 無料では取れない**(推定: 有料域。再試行 1 回は要)【事実】。
疎さ: 約定が 1 件以上ある秒は 55.0%(2021)/ 9.1%(2024)/ 18.4%(2026)で、2024-03-01 にはメンテ以外に 21:33・21:45 UTC に 6〜13.5 分の無約定【事実】→ 「約定なし秒」の扱いを事前登録(#9)。受信遅延 p50/p90 は 0.104/0.304 s(2021、既に東京拠点)→ 0.052/0.112(2024)→ 0.042/0.066(2026)で年々短縮【事実】。

### 3(致命)Tardis 利用規約: 生データの再配布禁止 — `backtest_data` は git 管理下(2,290 ファイル)なので置けない
`docs.tardis.dev/legal/terms-of-service` 引用: 「Permitted Use: internal business, research, educational or personal use by the Customer and Customer Users only」、Clause 9.2「the Customer shall not: … redistribute or resell the Data … except for reselling or redistributing aggregated and calculated Derived Data, including OHLC or OHLCV candles, at a resolution of 10 minutes or longer, where no raw Data is exposed」、「Derived Data does not include Data that has merely been reformatted, filtered, sampled」【事実】。1 秒足・約定表はいずれも 10 分未満 = 再配布不可。対処: Tardis 由来はコミット対象外の場所(`data/` 配下、gitignore 済)に置き、SEALED.json には MD5 とパスのみ載せる。無料サンプルの提供条件は docs の「Historical datasets for the first day of each month are available to download without API key」のみで、サンプルに別ライセンスは無い(仮定: 本規約が適用)。

### 4(提案)bitFlyer Realtime API に過去チャネルは無い(票の結論を追認)
`bf-lightning-api.readme.io/docs/realtime-api`(200)の Public Channels は「板情報のスナップショット / 板情報の差分 / Ticker / 約定」の 4 つのみで、履歴・リプレイの記述なし【事実】。REST 31 日(N-002)が唯一の遡及経路で変わらない。

### 5(要修正)Binance 先物(USDT 無期限)の aggTrades は `data.binance.vision` で到達可 — 現物との先行差は未探索
`/data/futures/um/daily/aggTrades/BTCUSDT/` 2019-12-31・2026-09-05、`monthly/.../2020-01` すべて 200(fapi REST は 451 だが Vision は届く。`bookTicker` daily は 404)【事実】。`docs/` に「先物が現物に先行するか」の知見は無い(grep で該当なし)【事実】。信号源を現物 / 先物のどちらにするかは探索面に載せて N0 に数えるか、事前に片方に固定する。

### 6(提案)代替信号源: Bybit 公開 csv は無料で到達可、対照(海外一般か Binance 固有か)に使える
`public.bybit.com/trading/BTCUSDT/`(無期限、日次 csv.gz、2026-09-05 200)と `spot/BTCUSDT/` 200【事実】。先行信号を Bybit に置換して差が消えれば「海外先行一般」、残れば「Binance 固有」と読める対照。CoinGecko は集計指標のみで棄却済(`DATA_TOOLS_REEVAL_2026-09.md`)、CryptoCompare は N-004(401)、Coinbase は Tardis ToS §23 に追加制限。OKX は未確認【仮定】。

## B. 既存の秒スケール研究との重複・矛盾・未探索

### 7(要修正)問いを (e)(x)(ah) と区別しないと同じ棄却の反復になる
既存: (e) 1 秒足 lag1 +0.11〜0.25・吸収 1〜2 秒・通常規模はコスト負け・20bps 級のみ正(4 窓 × 6 時間、2026-07/08)/ (p) バーストスキャルパー PAPER 86 件 −3.83bps / (x) S10 雪崩追随 thr20 0.65 回/日で棄却 / (ah) エッジは最初の 0.2 秒・−1bps/100ms・経済閉鎖。TRIAGE #9/#13/#17 は自市場・板が情報源で格子が違い重複しない【事実】。
本単位が thr 階段 × δ 曲線を同じ 2026-07〜08 窓で再測するなら (ah) と重複。未探索で本単位固有なのは 3 つ: (i) **分内分解** — P2-08 資源 R11(b) の「1 分先読みで +10〜+29bps」を 0〜5 / 5〜15 / 15〜60 秒に分解し、どこに価値が集中するか(ah の 0.2 秒と整合するか); (ii) **条件の向き** — P2-08 は低ボラ三分位(60 分 σ<5.7bps)でのみ正、(e) は 20bps 級の高ボラのみ正 = 逆向きの条件付け。両方を状態変数に事前登録して秒スケールでどちらが残るかを 1 回で見る; (iii) **伝播時間分布の長期変化** — 既存は 2 か月分のみ。Tardis 84 日 + bitbank 9 年(#1)で年別の交差相関ピーク秒を出す。

### 8(提案)信号側はこれまで 1s klines(e)のみ — aggTrades μs 単位の検証は未実施
(e) の Binance 側は `data/binance_BTCUSDT_1s_*.csv`。2025-01 以降 μs 刻印の aggTrades で「Binance 約定 → bitFlyer 約定」の到達秒を約定単位で測った研究は無い【事実】。1s klines で足りるかは分内分解(#7-i)の粒度次第なので、事前登録で粒度を固定する。

## C. 時計・刻印

### 9(要修正)刻印系統の混在と「約定なし秒」の扱いを既知欠陥として登録
開発窓は REST ms(07-23〜08-23)、以後は WS μs、Tardis は Tardis 受信、Binance は取引所刻印のみ(受信なし)、2024-12 以前は ms【事実】。対処: (a) 08-20〜08-23 の REST/WS 重複を id で突合し 1 秒足の一致率と欠け率(0.6〜1.9%)の**時間分布**(バースト時に集中するか)を測って登録 — 集中するなら発火時ほど執行価格が楽観に偏る; (b) Tardis 2026-08-01 と REST 31 日スナップショット(08-01 を含む)を id 突合して Tardis 側の取りこぼしも推定; (c) 約定のある秒は 9〜55%(#2)なので 1 秒足の「約定なし秒」= 前値継承か除外かを固定; (d) メンテ 18:59〜19:12 UTC と非メンテ無約定 5 分超をまたぐ信号・建玉は印付け。

### 10(要修正)λ(受信遅れ)は Binance 側に受信時刻が無いので自前で置く — 自宅 PC 経路は別扱い
Binance 刻印 t の情報を bitFlyer で使えるのは t+λ で、λ は本環境 WS p50 61 ms(ah)または Tardis 東京 p50 42〜52 ms(#2)を**測定値として事前登録**し、λ ∈ {0, 50, 100, 200 ms} を探索面ではなく感度表に置く。自宅 PC は時計 0.44 秒遅れ・週 0.8 秒ドリフト(ah)で PAPER のサブ秒評価に使えない → フォワードは NTP 同期を前提条件として `OWNER_PROCEDURES` に手順化、ticker 条件付けは 0.2 秒補正(ah)。

## D. 経済の天井

### 11(致命)経済停止条件を主検定より前に置く
(ah): 長期頻度 0.84 回/日 × 板厚上限 0.02 BTC → 最良 +27 円/日 vs サーバ費 33〜50 円/日【事実】。本単位でも主指標を「1 取引 bps」ではなく **日次円 = 頻度 × 板厚(BTC) × 価格 × bps** にし、停止条件「開発セット最良構成の日次円の 95% CI 上限 < サーバ費上限 50 円/日 × 2 なら封印を開けずに棄却」を事前登録。板厚 0.02 BTC・サーバ費 33〜50 円/日は `constants.yaml` に source_type=measured/primary_document で登録し(現状は報告文中の値)、板厚は発火時 best-ask 厚を秒データで再測する。

## E. 封印

### 12(要修正)45 日窓に暦 70/30 を当てると刻印系統で割れ、封印側の n が検出力ゼロ
`calendar_seal_boundary` は暦日 span の後ろ 30%(floor)【事実】: 07-23〜09-06(45 日)→ 境界 **08-23 00:00 UTC**。開発 07-23〜08-22 は REST ms、封印 08-23〜09-06(14.5 日)は WS μs で、08-25〜28 に 18.8 時間の穴。thr20 級なら封印 n ≈ 0.84 × 14.5 ≈ 12 件、開発でも ≈ 26 件【推定】→ 封印で判定する設計は成立しない。対処: 最終評価の主戦場をフォワード(forward_start = 凍結日、PC 収集の継続が生命線 = P2-08 監査 #7)にし、「フォワード n ≥ X 到達時に 1 回評価」と書く。n の X は頻度別 MDE から事前に出す。

### 13(要修正)Tardis 84 日は 45 日窓と同じ SEALED.json に入れない
P2-02 の rule「unit-wide boundary … applied to every file」のとおり主系列(45 日窓)の 08-23 が全ファイルに適用され、Tardis 84 日は 2026-08-01 まで全部が開発側になる【事実】。案: (a) Tardis と bitbank 長期は「診断専用(選択に使わない)」と宣言して封印対象外にし、#7-(iii) の記述統計のみに使う; (b) 選択に使うなら別 primary で暦順 70/30(2019-09〜2024-07 開発 59 日 / 2024-08〜2026-08 封印 25 日)。奇偶月交互や日内分割は封印の意図(時間外挿)に反するので不可。月初 1 日のみの偏り(月末ロール・資金調達)は仮定として明記し、bitbank 全日で補正。

## 事前登録に載せるべき項目
1. 問いの明文化: (e)(x)(ah) との差 = 分内分解 / 条件の向き / 伝播の長期変化(#7)。同じ thr×δ 面の再測は行わない。
2. データ節: bitbank 日次約定(9 年)・Tardis 84 日・Bybit・Binance 先物の扱い(選択に使う/診断のみ)と保管場所(Tardis は gitignore 域、#3)。
3. 信号源の固定(現物 / 先物 / 1s klines / aggTrades)と、Bybit 置換対照(#5・#6・#8)。
4. 既知欠陥: 刻印系統の混在、WS 欠け 0.6〜1.9% の時間分布、約定なし秒の扱い、メンテ窓と無約定 5 分超の印付け(#9)。
5. λ の測定値と感度表、自宅 PC の NTP 前提、ticker 0.2 秒補正(#10)。
6. 主指標 = 日次円(頻度 × 板厚 × bps)、経済停止条件、`constants.yaml` の板厚・サーバ費(#11)。
7. 状態変数: 実現ボラ三分位(低ボラ側も高ボラ側も)、直前 N 秒の bitFlyer 約定有無、年代(Tardis/bitbank の年)(#7)。
8. 封印: 45 日窓の境界 08-23 と刻印系統の対応表、フォワード n ≥ X の到達規則、長期系列の封印方針(#12・#13)。
9. 否定的事実の追加: Coincheck 履歴ページング不可(400)、GMO `page` 遡及は直近のみ、Tardis 無料に板系・Binance 側なし(要再試行 1 回)、bitFlyer Realtime に過去チャネルなし(#1・#2・#4)。N-002 は最終評価前に再確認(P2-08 監査 #6 と同じ)。
