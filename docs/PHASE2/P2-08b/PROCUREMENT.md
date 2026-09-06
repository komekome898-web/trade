# P2-08b 調達票 — Binance 先行を秒スケールで捕捉する(標準 `docs/PHASE2_TEMPLATES.md` §7)

作成 2026-09-06(UTC 22:45〜22:53 に全経路を実測)。単位の出所: `docs/PHASE2_TRIAGE.md` 28b 行(オーナー指示 L-011、P2-08 の分足棄却を受けて)。
到達確認は全て本環境(HTTPS プロキシ経由)からの実測。生レスポンスと約定テープの被覆走査結果は `backtest_data/audit_fetch_P2-08b_20260906/`(MD5SUMS つき、412 KB、未コミット)。
各主張の印: **事実** = 本日実測または一次文書の引用 / **推定** = 実測からの外挿 / **仮定** = 未確認。印の無い行は事実。
申込み・課金・発注は一切していない。

## 1. bitFlyer FX_BTC_JPY の秒スケール(約定または 1 秒足、できるだけ長期)

| 必要データ(市場・粒度・期間・最小 n) | 入手経路の候補 | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| **手元(自前記録)** WS 約定テープ `paper_logs/tape/executions_YYYYMMDD.csv.gz`(取引所刻印 μs、列 ts/price/size/side) | 自宅 PC の `record_realtime.py` → `extract_tape.py` → `share_logs.bat`(`docs/OPERATIONS.md` §「生テープ」) | 2026-09-06 全 18 ファイル走査: **2026-08-20 06:13:26 〜 2026-09-06 18:58:46 UTC、806,790 行**。5 分超の欠け: (a) 毎日 18:59〜19:12 UTC(bitFlyer 日次メンテ、取引所側) (b) **08-25 18:29 → 08-26 02:55(8.4 時間)** (c) **08-27 17:57 → 08-28 04:19(10.4 時間)** (d) 08-26 05:09–05:16、08-30 05:18–05:28、09-05 11:05–11:58 の 3 断続(5〜9 分) | (b)(c) は記録 PC 側の停止(推定)。REST 約定との重なり日で件数が **1.9% 少ない**(08-21: 101,052 vs 102,963、08-22: 45,432 vs 45,693)= WS 取りこぼしを既知欠陥として登録。継続収集は自宅 PC 単独(二重化なし、G2 §5・P2-08 盲点監査 #7 と同じ弱点) |
| **手元** 公式約定 31 日スナップショット `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz`(REST、取引所刻印 ms) | 公開 REST `/v1/getexecutions` の凍結コピー | 2026-09-06 走査: **2026-07-23 12:09:27 〜 2026-08-23 12:25:34 UTC、982,000 行**、id 2648328946〜2649902242。小数桁 3(ms)。テープと 08-20 06:13〜08-23 12:25 で重複 | これ以前の秒データは手元に無い。REST の 31 日窓は既に 08-06 まで後退(下記)ため **再取得不能** |
| **手元** `backtest_data/auto_bitflyer_executions_20260905/` | テープの日次スナップショット(manifest.json、MD5) | 2026-09-06: 内容は `paper_logs/tape/` の 08-20〜09-05 と同一 MD5(09-05 分のみ 25 KB の途中版)。独立ソースではない | 新規情報なし。長期保存先としてのみ使う |
| **手元** `data/ws/*.jsonl.gz`(WS 生記録: 板スナップ/差分・約定・ticker、受信時刻 `rts` 付き) | 本チェックアウトに残る分のみ | 2026-09-06: **4 ファイル、2026-08-20 05:07:59 〜 10:42:17 UTC のみ**(523 / 71,357 / 14,669 / 58,267 行) | 板を含む生記録は本環境には 5.6 時間分しか無い。自宅 PC の `data/ws` にはより長期がある(仮定、`share_logs.bat` は ws を転送しない= `docs/OPERATIONS.md` の記述) |
| **手元** 派生系列: `board_round_20260904/board_round_series_5s.csv.gz`(5 秒)、`paper_logs/tape/board_top5_*.csv.gz`(1 秒、**ローカル時計刻印**)、`ticker_*.csv.gz`(取引所刻印、気配変化のみ) | 同上 | 2026-09-06: board_round 5s = 08-20 06:13 〜 09-04 12:50(G2 §3)。board_top5 = **08-20 06:13:21 〜 08-26 19:01:55(7 日)**。ticker = 08-20 06:13:21 〜 09-06 19:00:56(18 日、上記 (b)(c) と同じ穴) | board_top5 はサブ秒用途不可(§3 の時計問題)。秒足の板側条件付けに使えるのは ticker(取引所刻印)のみ |
| **チャート系統** `lightchart.bitflyer.com/api/ohlc` の 1 分未満 period | `scripts/fetch_bitflyer_lightchart.py` と同じ非公式 API に period を変えて要求 | **2026-09-06 22:45 UTC 実測: period ∈ {s, 1s, 10s, S, 30s, 5s} は全て HTTP 400** `instance.period is not one of enum values: m,h,d`(サーバ側 OpenAPI enum)。period=m は 200(既知、h/d は 501 = `BITFLYER_HISTORY_SOURCES.md`) | **秒足は存在しない**(遡及確認は不要)。→ 否定的事実として新規登録を提案(N-008 案、賞味期限 180 日) |
| **公式 API** 公開 REST `/v1/getexecutions`(N-002 の再確認) | `before=<id>` で二分探索 | **2026-09-06 22:46 UTC 実測**: 最新 id 2650820842(22:45:43)。到達できる最古 ≈ id 2648987963 = **2026-08-06T04:00:45**、それ以前は HTTP 400。= 31.8 日 | **N-002 有効**(登録 2026-08、賞味期限 90 日 → 2026-11 頃失効。最終評価前に再確認、P2-08 盲点監査 #6 と同じ) |
| **ライブラリ** ccxt `fetchTrades` の `since` 遡及 | ccxt 4.5.77(検証用 venv、プロキシ CA 指定) | **2026-09-06 22:50 UTC 実測**: `has.fetchTrades=True`、`fetchOHLCV=None`(N-003 と一致)。`since=7 日前` も `since=60 日前` も **最新約定(22:50:40)を返す = since は無視される**。`params={'before': id}` は REST にそのまま渡り 08-06 境界で同じ壁 | ccxt 経由でも 31 日を越えない。→ 否定的事実 N-009 案 |
| **業者** Tardis.dev(bitFlyer 対応・開始日・価格) | `api.tardis.dev/v1/exchanges/bitflyer`(公開 JSON)、`docs.tardis.dev`、`tardis.dev` ホーム、無料サンプル `datasets.tardis.dev` | **2026-09-06 実測**: API 200 — `availableSince` **2019-08-30**、`FX_BTC_JPY`(perpetual)の dataTypes = trades / incremental_book_L2 / quotes / book_snapshot_5 / book_snapshot_25 / book_ticker、`availableTo` 2026-09-06。捕捉チャネル lightning_executions / board_snapshot / board / ticker。収集拠点は **2020-05-28 以降 GCP asia-northeast1(東京)、以前はロンドン**(docs)。価格(ホーム、`/pricing` は 404): **$350/月(四半期・年払いのみ)/ $700 / $1,000 / $3,000/月** の 4 段(どの段に bitFlyer が含まれるかは頁から判別不能 = 推定不可)。無料サンプル(各月 1 日、キー不要): `trades/2020/01/01/FX_BTC_JPY.csv.gz` 200・9.79 MB・1,077,696 行、`2019/09/01` 200・11.95 MB、`2026/08/01` 200・240 KB・17,194 行(初回 429 → 再試行で 200)。`2026/08/02` は 401(要キー)。列 `exchange,symbol,timestamp(μs 取引所刻印),local_timestamp(μs 受信),id,side,price,amount` | **bitFlyer 秒スケールを 2019-08-30 まで遡れる唯一の到達確認済み経路**(有料)。月 1 日の無料サンプルだけでも 2019-09〜2026-08 の **84 日分**(各月 1 日)が無料で取れる → 秒スケール判定の「長期の点検」用に使える(推定: 連続性は無いので執行検証には不向き)。申込みはオーナー判断 |
| **業者** Kaiko | `reference-data-api.kaiko.io/v1/exchanges`、`/v1/instruments?exchange_code=bfly`(公開 JSON)、`kaiko.com`、`docs.kaiko.com` | **2026-09-06 実測**: exchanges 200 → `bfly`(bitFlyer)。instruments 200(255 件): **perpetual-future `btc-jpy`(legacy `fxbtcjpy`)trade_start_time 2015-11-21T07:21:47Z**、trade_end なし。`kaiko.com/` 200(価格記載なし)、`/pricing` 404、docs は JS アプリで本文取得不能 | 参照データに存在=ティック保有(推定)。価格・粒度は未確認(仮定)。営業問合せ経路のみ |
| **業者** CoinAPI / CryptoTick(= CoinAPI flat files) | `coinapi.io`、`cryptotick.com`、`rest.coinapi.io` | **2026-09-06 実測**: `www.coinapi.io` と `/market-data-api/pricing` は HTTP 403(Cloudflare JS チャレンジ「Just a moment…」)、`cryptotick.com` は `coinapi.io/products/flat-files` へ転送後 403、`rest.coinapi.io/v1/exchanges/BITFLYER` 401(要キー)。WebFetch では `EGRESS_BLOCKED domain=www.coinapi.io` | **本環境から到達不能**(価格・開始日は未確認)。→ 否定的事実 N-010 案(賞味期限 90 日)。必要ならオーナーのブラウザで確認 |
| **公開データセット** Kaggle / GitHub の bitFlyer FX 秒データ | (前回調査 `BITFLYER_HISTORY_SOURCES.md`) | 2026-09-06 の前回調査で該当なし(分足ですら無い) | 再調査せず。分足で無いものが秒で存在する見込みは低い(推定) |

## 2. Binance BTCUSDT の秒スケール(信号側)

| 必要データ | 入手経路の候補 | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| **aggTrades**(全約定を集約、取引所刻印) | `data.binance.vision/data/spot/{daily,monthly}/aggTrades/BTCUSDT/` | **2026-09-06 22:46 UTC HEAD/GET**: daily 2026-09-05 **200・7,077,617 B**(展開 39.7 MB・458,828 行)、2026-09-04 200・14,460,955 B、**2019-06-01 200・5,255,509 B**(323,960 行)、**2017-08-17 200・51,003 B**。monthly 2019-06 206・217,235,916 B、2017-08 200・921,437 B、2026-07 206、**2026-08 は 404**(README: monthly は翌月第 1 月曜に公開) | 2026-08 は日次 31 本で代替(全 31 日 HEAD 200)。**`scripts/fetch_binance_vision.py` は URL が `klines` 固定で aggTrades 非対応**(要小改修: パス種別を引数化)。`scripts/fetch_aggtrades.py` は REST `/api/v3/aggTrades` 直叩き(報告 e 用、履歴一括には不向き) |
| **1s klines**(1 秒足) | 同上 `/klines/BTCUSDT/1s/` | 2026-09-06: daily 2026-09-05 **200・2,197,502 B**(86,400 行)、2019-06-01 200・2,662,190 B、**2017-08-17 200・480,298 B**。monthly 2019-06 200・85,870,206 B、2017-08 200・8,538,327 B、2026-08 404(同上) | `fetch_binance_vision.py --interval 1s` はそのまま動く(interval は自由文字列、`normalize_epoch` が μs を処理)。ただし monthly→daily フォールバックは 2026-08 のように月次未公開時のみ |
| 1 か月分の見込みサイズ | 2026-08 の日次 31 本の Content-Length 合計 | **aggTrades: 357,661,557 B = 0.36 GB(zip)**、展開比 5.6× → **約 2.0 GB CSV**。**1s klines: 68,367,300 B = 0.068 GB(zip)**、展開 ≈ 0.39 GB | 2 年分なら aggTrades ≈ 8.6 GB zip(推定、活況月は 2 倍)。1s klines なら 1.6 GB zip。信号計算に約定単位が要らなければ 1s klines で足りる |
| 刻印の定義(一次資料) | `github.com/binance/binance-public-data` README(raw、200) | 引用: 「**The timestamp for SPOT Data from January 1st 2025 onwards will be in microseconds.**」 実測一致: 2026-09-05 aggTrades の Timestamp は 16 桁(1788566400483577 = μs)、2019-06-01 は 13 桁(ms)。1s klines も open_time/close_time が μs(1788566400000000 / 1788566400999999) | 2024-12-31 以前は ms → 結合時に単位を揃える(`normalize_epoch` 済みの klines 経路に合わせる) |
| 開始日 | 同上 | **2017-08-17 の daily が aggTrades・1s とも 200**(BTCUSDT 上場日) | 欠けなし |

## 3. 時計の整合

| 系列 | 刻印の源 | 根拠(該当行の引用) | 既知の遅れ・対処 |
|---|---|---|---|
| `data/ws/*.jsonl.gz` | **受信時刻**(ローカル `time.time()`)を `rts` に付し、取引所刻印はメッセージ内(約定 `exec_date`、ticker `timestamp`)。板メッセージには取引所刻印が無い | `src/bot/market_data/realtime.py` L179: `self._buffer({"rts": time.time(), "m": json.loads(raw)})` | 板の時刻はローカル時計に依存 → 自宅 PC の時計問題を直接受ける |
| `paper_logs/tape/executions_*` | **取引所刻印**(`exec_date`、μs) | `scripts/extract_tape.py` docstring: 「ts exchange exec_date, ISO-8601 UTC, microsecond precision」。実測: 小数 7 桁が 90%(残りは末尾ゼロ落ち) | 時計問題なし。REST 版(ms)と結合する場合は ms に丸めて突合 |
| `paper_logs/tape/ticker_*` | **取引所刻印**(`lightning_ticker` の timestamp) | 同 docstring: 「ts is the exchange timestamp from the lightning_ticker message」 | **「bitFlyer の ticker 刻印は板更新より約0.20秒遅れる(チャネル対照で実測)— ticker 基準の遅延・サブ秒研究はこの分を補正すること」**(`docs/RESEARCH_REPORT_2026-08-28ah.md` §5-1)。`docs/KNOWLEDGE.md` L34 も同旨: 「**ticker刻印は板更新より約0.2秒遅い**」 |
| `paper_logs/tape/board_top5_*` | **ローカル受信秒**(`int(rts)`) | `scripts/extract_tape.py` L293: `sec = int(rts)` | **「自宅PCの時計は取引所比0.44秒以上遅れ、週内で0.8秒ドリフト(board_top5 のローカル刻印から特定)。PCのNTP同期を推奨 — これなしにはPC側のサブ秒研究・ログ法医学が成立しない。board_top5 の既存データはδ精度の用途に使えない」**(同 ah §5-2)。`KNOWLEDGE.md` L34: 「**自宅PC時計は0.44秒以上遅れ週内0.8秒ドリフト(NTP同期必須、既存board_top5はサブ秒用途不可)**」 |
| REST 31 日スナップショット | 取引所刻印 `exec_date`(ms) | 実測: 小数 3 桁が 67%、以下ゼロ落ち | 問題なし |
| Binance aggTrades / 1s klines | **取引所刻印**のみ(受信時刻は無い)。2024-12 まで ms、2025-01-01 以降 μs | §2 の README 引用と実測 | 取引所間の時計差は両者とも取引所刻印なので「取引所 A の刻印 vs 取引所 B の刻印」の比較になる。伝送遅延の参照値: Tardis の東京拠点で bitFlyer 約定の 受信−刻印 は **p50 0.052 s(p10 0.039 / p90 0.077、2026-08-01 サンプル 2 万行)**、ロンドン時代(2020-01-01)は p50 0.362 s。自環境 VM の WS 受信 p50 61 ms(ah 報告)と同桁 |
| 取引所側の欠け | bitFlyer 日次メンテ | テープの約定は毎日 18:59〜19:12 UTC が空、ticker は 19:04〜19:10 が空(`docs/OPERATIONS.md`: 04:00–04:10 JST = 19:00–19:10 UTC) | 窓またぎの信号・建玉は除外規則を事前登録に書く |

## 4. 既存の秒スケール研究の一次資料

| 報告 | 主題・結論(要点) | スクリプト | 一次データの所在(本チェックアウト) |
|---|---|---|---|
| e(第5報、2026-08-20) | 1 秒足で lag1 相関 +0.11〜+0.25、吸収 1〜2 秒。常時型スキャルは thr 3〜5bps で全窓ネット負 | `scripts/research_hft.py`、`scripts/fetch_aggtrades.py`(REST aggTrades) | Binance 1 秒足 4 窓 × 6 時間: `data/binance_BTCUSDT_1s_{hi2,lo1,lo2,hi1}.csv`(2026-07-31 11:00 / 08-08 12:00 / 08-15 12:00 / 08-19 12:00 UTC 起点、各 21,600 行)+ `data/binance_BTCUSDT_1s_today.csv`(08-20 06:35〜08:40)。bitFlyer 側は当時の `data/executions_FX_BTC_JPY.csv`(現在は `executions_FX_BTC_JPY_31d_20260823.csv.gz` が同区間を包含) |
| i(第9報、関連) | 嵐 16 件 × 2 時間の 1 秒足ライブラリ | `scripts/build_storm_library.py` | `backtest_data/storm_events_20260820/`(16 ファイル、2026-07-21 13:40 〜 08-20 09:37、G2 §3) |
| p(第16報、2026-08-21) | バーストスキャルパー PAPER 判定: 86 件 −3.83bps、CI [−9.24, −2.78] → 棄却 | `scripts/run_scalp_paper.py`、`scripts/research_scalp_exits.py` | `paper_logs/scalp_paper.jsonl`(510 行、2026-08-20 06:13 〜 08-21 12:30 UTC) |
| x(第23報、2026-08-25) | S10 雪崩追随(2 秒窓)は thr20 で 0.65 回/日、全 4 通り負 → 実現可能性で棄却。S11 も棄却 | `scripts/research_avalanche.py`、`scripts/research_signal_fade.py` | `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz`(2026-08-20T08:22:17Z より前のみ使用)。Binance 日次 1s/1m klines は **scratchpad のみで未保存**(報告本文の明記) |
| ah(第33報、2026-08-28) | エッジは最初の 0.2 秒に集中(−1bps/100ms)、λ=0 でも低閾値は開かず、経済線は費用と区別不能 → WS 化ライン棄却。副産物: ticker 0.2 秒遅れ・PC 時計 0.44 秒遅れ | `scripts/research_latency_grade.py`、`scripts/research_latency_paths.py`、`scripts/measure_ws_latency.py` | `paper_logs/tape/executions_*`・`ticker_*`(2026-08-20〜27)、`data/ws/FX_BTC_JPY_20260820_*.jsonl.gz`(4 本) |
| 関連ライブラリ | 平常バースト 99 窓 × 40 分(1 秒、bn/bf 併記) | `scripts/build_burst_library.py` | `backtest_data/burst_events_20260820/`(99 ファイル、2026-07-21 17:36 〜 08-20 06:47) |

## 5. 否定的事実の引用と新規登録の提案

- 引用(賞味期限内を本日確認): **N-002**(REST 31 日、2026-09-06 実測 08-06 まで = 有効。失効 2026-11 頃)、**N-003**(ccxt fetchOHLCV 未実装、本日 `has.fetchOHLCV=None` で再確認)、**N-004**(CryptoCompare 401・現物のみ、未再確認だが期限内)、**N-001/N-006**(bitflyer.com 到達不能 — 本票では api / lightchart のみ使用)。
- 新規登録の提案(リードが `docs/NEGATIVE_FACTS.md` に追記する場合の文案):
  - N-008: lightchart `api/ohlc` の period は `m,h,d` のみ(サーバ側 enum、HTTP 400)。秒足は無い。確認 curl 6 値、賞味期限 180 日。
  - N-009: ccxt `bitflyer.fetchTrades` は `since` を無視する(最新を返す)。`params.before` は REST 透過で 31 日の壁は同じ。賞味期限 180 日。
  - N-010: coinapi.io / cryptotick.com は本環境から 403(Cloudflare JS チャレンジ、WebFetch は EGRESS_BLOCKED)。賞味期限 90 日。

## 6. 結論(事実として 2 行)

- **bitFlyer 側で秒スケールの判定に使える連続窓は 2026-07-23 12:09 〜 2026-08-25 18:29 UTC(33.3 日、日次メンテ 19:00–19:12 UTC のみ欠け。07-23〜08-23 は REST ms 刻印、08-20 以降は WS μs 刻印)**。その後は 08-26 02:55〜08-27 17:57(1.6 日)と 08-28 04:19〜09-06 18:58(9.6 日、継続中)の 2 断片で、総被覆 44.5 日 / 期間 45.3 日。これより前の秒データは手元・無料経路には無く、遡るには Tardis(2019-08-30〜、有料、無料は各月 1 日のみ)か Kaiko(2015-11-21〜、価格未確認)だけ。
- **Binance 側は 2017-08-17〜(aggTrades・1s klines とも `data.binance.vision` で無料、2025-01-01 以降 μs 刻印)**。直近月は日次 zip、1 か月 ≈ aggTrades 0.36 GB zip / 1s klines 0.07 GB zip。
