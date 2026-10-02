# カード 1(xborder_mom): 調達票

研究手順書 §14 の表。到達確認は、データの置き場の目録(README・`*_index.json`・MD5SUMS)を読むことで行った(2026-10-02)。**データのファイルの中身は開いていない**(封印の中も、封印の外の 2023-12-17 までの行も。測定はまだ)。
主張の印: 【事実】= ファイル・出力で確かめた / 【推定】= 確かめていない読み / 【未確認】= この回に確かめていない。

## 1. 必要データ

| 必要データ | 市場 | 粒度 | 期間 | 最小 n |
|---|---|---|---|---|
| D1 持つ銘柄の足 | bitFlyer FX_BTC_JPY | 1 分足(始値・終値・出来高。始値は損益、出来高は空の足の判定) | 2017-08-17 15:00 〜 2023-12-17 15:00 UTC(日本時間の 2017-08-18 〜 2023-12-17。CARD.md「測る期間」) | 置かない。W1 の C5 の e で、その n で検出できる最小の平均(MDE)を出す。期間の長さは 3,330,720 分(2,313 日)【事実: 開始と終了の差の計算】。約定の有る分はこれより少ない |
| D2 信号の系列 | Binance BTCUSDT(現物) | 1 分足の close(と、その分の始まりの時刻) | 同上 + 窓の分(開始の 32 分前まで。Binance の行は 2017-08-17 04:00 UTC からあるので届く) | 同上 |

## 2. 調達票

| 必要データ | 入手経路の候補 | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| D1 bitFlyer FX_BTC_JPY 1 分足 | ① チャート系統: lightchart.bitflyer.com の `api/ohlc`(取得済み `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/`)② 公式 API: bitFlyer の公開 REST の約定履歴(`getexecutions`)から足を作る ③ 業者: 約定・板の履歴を売る業者(Tardis.dev・Kaiko など)④ 自前記録: paper の約定の記録(`paper_logs/tape/`)⑤ ccxt の `fetchOHLCV` | ① **到達**。2026-10-02、README・`candles_1m_index.json`・MD5SUMS を読んだ。README「5,662,046 rows, timestamp range 2015-11-28 04:54 UTC .. 2026-09-06 00:00 UTC」。年ごとの行数(index): 2017 525,596 / 2018 525,600 / 2019 525,600 / 2020 526,668 / 2021 525,600 / 2022 525,600 / 2023 525,600(null の行を含む)。7 ファイルの md5 は index と MD5SUMS で一致【事実: 両方を読んで突き合わせた】 ② 期間に届かない: 約定履歴は約 31 日分だけ(`docs/NEGATIVE_FACTS.md` N-002、2026-08 記録・賞味期限 90 日で有効)③ 【未確認】(この回は調べていない。有料なので収益の算段が立つまで提案しない、A-3)④ 期間に届かない: 2026-08 以降だけ(`backtest_data/fx_btc_jpy_1m_continuous_20260906/README.md`「part B ... 2026-08-23 12:26 .. 2026-09-05 13:47」)⑤ 使えない: ccxt の bitflyer は fetchOHLCV 未実装(N-003、2026-09-06 記録・賞味期限 180 日で有効) | (a) **約定 0 の分**は null の行(README「294,741 rows are null-OHLC」、全期間)。研究の口は空の足でカードを呼ばない(I-14 △)(b) **5 分を超える空き**は 2017〜2023 年で年 312〜1,316 件(README の表。2023 年が 1,316 件で最多、原因は README で未調査)(c) 毎日 19:00〜19:10 UTC の保守の時間(README「maintenance_window」)(d) 1 分の値動きが 10% を超える行 27 件(README、うち約 15 件が 2017〜2018 年)。除かない(README「flag-only」)(e) lightchart は bitFlyer の公式の文書が無い経路(README「NOT a documented API」)。他の bitFlyer の系列との一致は分の 85〜90%(README)。対処: 測る前に何も除かない。空き・保守の時間は場面の変数(時間帯)で読める(W1 の C4) |
| D2 Binance BTCUSDT 1 分足 | ① 公開データセット: Binance Vision の月次の 1 分足(取得済み `backtest_data/binance_BTCUSDT_1m_20170801_20231231/`)② 公式 API: Binance の公開 REST `/api/v3/klines` ③ 業者: Tardis.dev・Kaiko・CryptoDataDownload など ④ 自前記録: paper の判断の記録の `indicator_values.leader_close`(bot が取った Binance の値) | ① **到達**。2026-10-02、README・`binance_1m_index.json`・MD5SUMS を読んだ。README「3,343,519 rows, span 2017-08-17 04:00:00 UTC .. 2023-12-31 23:59:00 UTC」「77/77 passed」(Binance の SHA-256 の照合)。年ごとの行数(index): 2017 196,544 / 2018 521,624 / 2019 523,836 / 2020 525,788 / 2021 524,607 / 2022 525,600 / 2023 525,520。7 ファイルの md5 は index と MD5SUMS で一致【事実】 ② 【未確認】(この回はネットワークに出ていない。①で足りる)③ 【未確認】(有料。A-3)④ 期間に届かない: paper は 2026-08 から(段 7 の設計 §5-2 の T-B の注) | (a) **行の抜け**: README「35 inter-row gaps where the step between consecutive rows is not exactly 60 seconds」。カードは 2 分前まで遡って埋め、それより長い抜けは「様子見」(I-10・I-11。bot と同じ)(b) 静かな分は出来高 0 の行で入っている(README「one row per minute with 0 volume rather than a missing row」)ので抜けにならない (c) 系列の始まり 2017-08-17 04:00 UTC より前は無い(README「2017-07 does not exist」)。測る期間の開始(15:00 UTC)より 11 時間前なので、窓の分は届く (d) 行の時刻は `open_time`(分の始まり)のまま、遅れ 60 秒で読む(CARD.md「測定の設定」。INTENT_MAP.md §9 の 1)(e) bot が使う値(5 秒ごとの気配の最後)とは違う(I-12 △) |

## 3. 封印との関係

- 封印の台帳 `backtest_data/phase2_sealed/P2-08/SEALED.json` に、bitFlyer FX の 1 分足 2017〜2026 の各ファイルと、Binance の 1 分足 2017〜2023 の各ファイルが、境 `seal_from_ts` = 2023-12-18T00:00:00+00:00 で載っている【事実: 台帳を読んだ。データのファイルは開いていない】。
- 測る期間の終わり 2023-12-17 15:00 UTC は境の 9 時間前で、境より後にかからない(`python scripts/check_card.py docs/RESEARCH/cards/c1_xborder_mom/CARD.md` → 「通る」)【事実】。

## 4. この票に入れていないもの

- リード盲点監査(研究手順書 §14。安い監査者 1 名、≤ 15 ツール呼び出し)は、W4 の仕様 §2 の 6 でリードが掛ける。この回の作業者は掛けていない。
- 経費(手数料・滑り・SFD・資金調達)のデータは段 5 の仕事で、段 2 の測定(経費前)には要らない(W1 の仕様 §0)。
