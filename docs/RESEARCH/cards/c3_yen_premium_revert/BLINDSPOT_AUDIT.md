# リード盲点監査(カード 3: 円の上乗せの戻り)

## 1. 未検討の入手経路

【事実】PROCUREMENT.md §1・§2 で、以下の経路が【未確認】と明記:
- bitFlyer FX_BTC_JPY: Tardis など有料の履歴が 2017〜2022 年の 1 分足を持つか
- Binance BTCUSDT: 公開 REST klines、CryptoDataDownload、Tardis が【未確認】
- USDJPY: GMO FX 公開 API の遡り期間、HistData.com の入手可能性
- Coinbase BTC-USD / USDT-USD: 全経路【未確認】(リード答えで代理測定と決定済み)

**指摘**: PROCUREMENT.md の「経路の候補」にある Tardis について、手元に `tardis_sample_FX_BTC_JPY_2020-01-01_head1000.csv` と `tardis_sample_FX_BTC_JPY_2026-08-01_head1000.csv` が `backtest_data/audit_fetch_P2-08b_20260906/` に存在【事実】。Tardis が実際に 2017〜2022 年のデータを保有しているかは、サンプルの有無では確認できず。取得候補に「Tardis は要確認」と残すことが適切。

## 2. 期限切れの否定的事実

【事実】`docs/NEGATIVE_FACTS.md` 確認(2026-10-02 時点): N-001 から N-013 まで全て有効。期限切れなし。

## 3. PC と環境の二重構造

【事実】`paper_logs/tape/` に記録は存在するが、bitFlyer FX_BTC_JPY の 1 分足は無し。`paper_logs/tape/` には `board_top10_*.csv.gz`(板情報、2026 年 8 月末から)のみ。CARD.md で「自前の記録(`paper_logs/tape/`)— 2026 年の分だけ【推定】」と書かれるが、FX_BTC_JPY の足は backtest_data 置き場のみで、二重構造による差異確認の対象データが不在【事実】。

## 4. 問いの立て方の狭さ

【事実】INTENT_MAP.md §2 の対応表で I-4(容量)、I-5(速さ)、I-8(海外先行)、I-10(個人偏り)が未実装。ただし、リード答え(2026-10-02)により INTENT_MAP.md §4 に「測定の回に診断として出す」と記載済み【事実】。射程外の明記も完了。

---

**無し**: 測定の回に確認する手段が PROCUREMENT.md(USDJPY 時刻の相関確認)に準備済み【事実】。迷った点の全項にリード答え(2026-10-02)が記載【事実】。
