# bitFlyer FX_BTC_JPY 複数年 1分足: データソース調査 (2026-09-06)

背景: 現行スナップショット `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz` は31日分(2026-07-23〜08-23)のみ。公開約定履歴は31日で消える(CLAUDE.md §2)ため、複数年バックテスト用の代替ソースを調査した。詳細な生レスポンスと手順は `backtest_data/audit_fetch_bitflyer_history_20260906/README.md`。

## ソース別まとめ

| ソース | 到達性 | 期間 | 粒度 | 商品 | 自スナップショットとの一致度 | 推奨 |
|---|---|---|---|---|---|---|
| bitFlyer lightchart (`lightchart.bitflyer.com/api/ohlc`) | ○ ブロックなし・認証不要 | 2015-11-30頃〜現在(未公式ドキュメント) | 1分(period=mのみ。h/dは501) | **FX_BTC_JPY**(指定通り) | REST 31dスナップショットと41,461分比較: OHLC完全一致89.5%、close差>0.5円が5.1%(出来高一致でも数千円ずれる少数の外れ値あり)。WS再構成テープ(08-23〜09-05)とも同水準(完全一致85.9%) | **第一候補**。非公式APIだがFX商品そのものが長期間取れる唯一のソース |
| ccxt (`ccxt.bitflyer()`) | ○ 到達可 | — | — | — | `has['fetchOHLCV'] is None` = 未実装。bitFlyer公式RESTにローソク足エンドポイントが無いため、ccxt経由でも不可 | 不採用 |
| CryptoCompare histominute | × HTTP 401(要有料APIキー、CoinDesk移管後に無料枠廃止) | 不明(未検証) | 1分 | **現物**BTC/JPY(FXではない) | 未検証 | 不採用(認証必要かつ現物のみ) |
| 公開データセット(GitHub/Kaggle) | 検索のみ、サンプル未取得 | 様々 | 様々 | いずれもBitstamp/Coinbase系または不明、bitFlyer FXなし | 未検証 | 不採用(該当なし)。Tardis.dev(有料)が2019-08-30以降のbitFlyer派生商品を保有 |

## lightchart 詳細

- URL: `https://lightchart.bitflyer.com/api/ohlc?symbol=FX_BTC_JPY&period=m&before=<epoch_ms>`。`before`は12時間UTCグリッド(00:00/12:00)に切り捨てられ301リダイレクト、1ページ最大720行(新しい順)。
- 出来高ゼロの分は独自スナップショットのような forward-fill ではなく **OHLC=null** で返る(欠測を正直に表現)。
- 列7-10(推定: ロング/ショート建玉っぽい数値、買い/売り出来高)は2017-07頃以前は null。**buy_volume+sell_volume=volume** は全サンプルで確認したが列7/8の意味はbitFlyer非公開で未確認 — `schema/bitflyer_lightchart_1m.json` に「推測・未確認」と明記。
- 本セッション内で実際にページネーションを実行し、`backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/` に生JSON・結合csv.gz・MD5SUMS・欠測(5分超ギャップ)一覧を保存(詳細は同ディレクトリのREADME.md)。取得は再開可能(`scripts/fetch_bitflyer_lightchart.py`、既存ページはスキップ)なため、より過去まで継続取得できる。

## 結論・推奨

1. **lightchart を正式な複数年ソースとして採用**を提案。非公式(未文書化)ゆえの継続性リスクはあるが、FX_BTC_JPYそのものを2015年末まで遡って取得できる唯一の候補。
2. 現行31dスナップショットとの差(約5%の分で close が有意にずれる)は「どちらかが誤り」ではなく、bitFlyer内部の2系統(REST candle vs. チャート用WS系)のバケット境界差と推定。バックテストで使う前に許容誤差を事前登録すること(research-protocol)。
3. ccxt・CryptoCompare・公開データセットはいずれも不採用(理由は表の通り)。
4. 本調査は実データを変更していない(read-only)。長期取得を続ける場合はオーナー承認の上で `scripts/fetch_bitflyer_lightchart.py` を継続実行(Windows PCでも同スクリプトが動作、`--dry-run`で確認可)。
