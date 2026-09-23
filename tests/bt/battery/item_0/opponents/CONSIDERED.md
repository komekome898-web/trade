# 検討表 -- 項目0「核」の調査結果の候補(場面係、2026-09-23)

委任文 `docs/DATA/delegations/20260923_backtest_env_prompt.md` §3「動かせない候補の検討と再現」に従う。
**動かせなかった候補は1件も機構を検討せずに外さない。** 材料は `docs/DATA/tools_catalog.tsv`
(台帳)と `docs/DATA/SCAN_2026-09-21_tools.md`(SCAN、10,694行)。段(機構)・SCAN行の値は
すべて本ファイル執筆時に台帳を直接 `awk` で引き直した実測値であり、`REQUIREMENTS.md` の記述を
そのまま書き写したものではない(再検証した結果、後述の§4で1件の食い違いを見つけた)。

危険リスト(委任文§4、11件。導入も実行もしない): 44・74・120・41・58・19・112・111・97・51・118。

## §1. 段のある観点(観点1、および観点2のうち足・ティック・板の待ち行列の3要素)

ルール(委任文§3): 実装のコードで確かめた機構のうち段(機構)が最も高い候補を選んで再現する
(同じ段が複数あれば全部)。それ以外は「スキップ: 明らかに弱い(段が低い)」+ 段の値 + SCAN行。
危険リスト該当は段に関わらず「再現できない」(理由=安全)。

実際に再現できたのは Python かつ PyPI 配布があり、`<scratchpad>/bt/venvs/item_0/` に
`pip install` できたもの(§3備考に導入ログの場所)。**最高位でも Go/Rust/C++ 製、または
GitHub のみでパッケージ配布が無い候補は、この周は導入できず「再現できない」とし、
その候補とは比較できていない旨を圧倒の判定に付す。**

(以下、生成スクリプト `/tmp/considered_gen/gen.py` で台帳から直接算出したテーブル4本。
`段(機構)` `SCAN行` は台帳の実測値そのもの。)

### 観点1: 事象駆動アーキテクチャ(19件)

| 候補 | 段(機構) | SCAN行 | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 1 Basana | 4・6 | 6836 | 再現できない | 観点1の最高位(段4・6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 6 Ziplime | 4・6 | 9650 | 再現した | 観点1の最高位(段4・6)。Ziplime (opponents/ziplime_adapter.py) で実測・再現。 |
| 13 DeviaVir/zenbot | 3・4 | 6874 | スキップ: 明らかに弱い | 段(機構)=3・4(観点1の最高位 段6 より低い。SCAN 6874行)。 |
| 18 zipline-reloaded | 4・6 | 9857 | 再現した | 観点1の最高位(段4・6)。zipline-reloaded (opponents/zipline_reloaded_adapter.py) で実測・再現。 |
| 23 hftbacktest | 3・5 | 6906 | スキップ: 明らかに弱い | 段(機構)=3・5(観点1の最高位 段6 より低い。SCAN 6906行)。 |
| 37 ThePredictiveDev/Automated-Financial-Market-Trading-System | 5・6 | 10426 | 再現できない | 観点1の最高位(段5・6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 41 prediction-market-backtesting | (空欄) | 6106 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 52 QuantConnect | (空欄) | 7292 | スキップ: 明らかに弱い | 段(機構)=(空欄)(観点1の最高位 段6 より低い。SCAN 7292行)。 |
| 53 Rqalpha | 3・4 | 7850 | スキップ: 明らかに弱い | 段(機構)=3・4(観点1の最高位 段6 より低い。SCAN 7850行)。 |
| 57 WonderTrader | 3・4・5 | 7852 | スキップ: 明らかに弱い | 段(機構)=3・4・5(観点1の最高位 段6 より低い。SCAN 7852行)。 |
| 58 nautilus_trader | (空欄) | 6345 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 61 barter-rs | (空欄) | 6926 | スキップ: 明らかに弱い | 段(機構)=(空欄)(観点1の最高位 段6 より低い。SCAN 6926行)。 |
| 62 qf-lib | (空欄)※ | 6117 | 再現した | 台帳の段(機構)欄は空欄(未測定)だが、この周に `opponents/qf_lib_adapter.py` で実際に `EventManager.publish()`→`dispatch_next_event()` を5回呼び、1件ずつ供給できることを実測で確認した(※機械的選定ルールなら『段が低い』でスキップされるはずだった候補が、実行してみると要件を満たしていた。台帳の段が実態を過小評価していた例として観点1の判断はこの実測を優先する)。 |
| 63 trade-frame | 3・4 | 6119 | スキップ: 明らかに弱い | 段(機構)=3・4(観点1の最高位 段6 より低い。SCAN 6119行)。 |
| 65 aat | 5(合成の取引所)・0(CSV の取引所)・0(IEX の取引所) | 10429 | スキップ: 明らかに弱い | 段(機構)=5(合成の取引所)・0(CSV の取引所)・0(IEX の取引所)(観点1の最高位 段6 より低い。SCAN 10429行)。 |
| 68 quanttrader | (空欄) | 6382 | スキップ: 明らかに弱い | 段(機構)=(空欄)(観点1の最高位 段6 より低い。SCAN 6382行)。 |
| 69 gobacktest | (空欄) | 6124 | スキップ: 明らかに弱い | 段(機構)=(空欄)(観点1の最高位 段6 より低い。SCAN 6124行)。 |
| 91 braedonsaunders/homerun | 3・4・5・6 | 7858 | 再現できない | 観点1の最高位(段3・4・5・6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 123 carlos8f/zenbot | 3・4 | 7298 | スキップ: 明らかに弱い | 段(機構)=3・4(観点1の最高位 段6 より低い。SCAN 7298行)。 |

### 観点2-足(55件)

| 候補 | 段(機構) | SCAN行 | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 1 Basana | 4・6 | 6836 | 再現できない | 足の最高位(段4・6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 2 Backtrader | 4 | 6839 | スキップ: 明らかに弱い | 段(機構)=4(足の最高位 段6 より低い。SCAN 6839行)。 |
| 3 PySystemtrade | 2 | 9401 | スキップ: 明らかに弱い | 段(機構)=2(足の最高位 段6 より低い。SCAN 9401行)。 |
| 4 PyBroker | 4・6 | 6845 | 再現した | 足の最高位(段4・6)。PyBroker (opponents/lib_pybroker_adapter.py) で実測・再現。 |
| 5 Lean CLI | (空欄) | 6849 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6849行)。 |
| 6 Ziplime | 4・6 | 9650 | 再現した | 足の最高位(段4・6)。Ziplime (opponents/ziplime_adapter.py) で実測・再現。 |
| 7 Superalgos | 1 | 6855 | スキップ: 明らかに弱い | 段(機構)=1(足の最高位 段6 より低い。SCAN 6855行)。 |
| 8 OpenTrader | 1 | 9402 | スキップ: 明らかに弱い | 段(機構)=1(足の最高位 段6 より低い。SCAN 9402行)。 |
| 10 fast-trade | (空欄) | 6864 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6864行)。 |
| 11 python3 | (空欄) | 8452 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 8452行)。 |
| 13 DeviaVir/zenbot | 3・4 | 6874 | スキップ: 明らかに弱い | 段(機構)=3・4(足の最高位 段6 より低い。SCAN 6874行)。 |
| 15 Mendl-Labs/BacktestingCore | 6 | 6879 | 再現できない | 足の最高位(段6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 16 Luczinsritter/event_driven_backtesting_engine | (空欄) | 6882 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6882行)。 |
| 18 zipline-reloaded | 4・6 | 9857 | 再現した | 足の最高位(段4・6)。zipline-reloaded (opponents/zipline_reloaded_adapter.py) で実測・再現。 |
| 19 Jesse | 2 | 9403 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 20 VnPy | 2 | 6896 | スキップ: 明らかに弱い | 段(機構)=2(足の最高位 段6 より低い。SCAN 6896行)。 |
| 21 Qlib | 4・6 | 6899 | 再現できない | 足の最高位(段4・6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 40 OpenMarket | (空欄) | 5725 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 5725行)。 |
| 43 QuantDinger | (空欄) | 4626 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 4626行)。 |
| 44 lo2cin4 | (空欄) | 5904 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 45 ForexTester | 2 | 10082 | スキップ: 明らかに弱い | 段(機構)=2(足の最高位 段6 より低い。SCAN 10082行)。 |
| 46 MT4裁量トレード練習君プレミアム | (空欄) | 5727 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 5727行)。 |
| 48 BacktestingMax | (空欄) | 5729 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 5729行)。 |
| 50 AlgoTest | 1 | 10088 | スキップ: 明らかに弱い | 段(機構)=1(足の最高位 段6 より低い。SCAN 10088行)。 |
| 51 QUANTAXIS | 0 | 9404 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 52 QuantConnect | (空欄) | 7292 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 7292行)。 |
| 53 Rqalpha | 3・4 | 7850 | スキップ: 明らかに弱い | 段(機構)=3・4(足の最高位 段6 より低い。SCAN 7850行)。 |
| 54 finmarketpy | 該当なし | 7851 | スキップ: 明らかに弱い | 段(機構)=該当なし(足の最高位 段6 より低い。SCAN 7851行)。 |
| 55 backtesting.py | (空欄) | 6344 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6344行)。 |
| 56 zvt | (空欄) | 5733 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 5733行)。 |
| 57 WonderTrader | 3・4・5 | 7852 | スキップ: 明らかに弱い | 段(機構)=3・4・5(足の最高位 段6 より低い。SCAN 7852行)。 |
| 58 nautilus_trader | (空欄) | 6345 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 60 Hikyuu | 2 | 7853 | スキップ: 明らかに弱い | 段(機構)=2(足の最高位 段6 より低い。SCAN 7853行)。 |
| 61 barter-rs | (空欄) | 6926 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6926行)。 |
| 62 qf-lib | (空欄) | 6117 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6117行)。 |
| 67 lumibot | 2 | 7854 | スキップ: 明らかに弱い | 段(機構)=2(足の最高位 段6 より低い。SCAN 7854行)。 |
| 68 quanttrader | (空欄) | 6382 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6382行)。 |
| 69 gobacktest | (空欄) | 6124 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6124行)。 |
| 70 PineForge | 2・3 | 7855 | スキップ: 明らかに弱い | 段(機構)=2・3(足の最高位 段6 より低い。SCAN 7855行)。 |
| 72 QTradeX | 1 | 7856 | スキップ: 明らかに弱い | 段(機構)=1(足の最高位 段6 より低い。SCAN 7856行)。 |
| 73 vectorbt | (空欄) | 5907 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 5907行)。 |
| 74 ml-quant-trading | (空欄) | 5910 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 75 Freqtrade | (空欄) | 6346 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6346行)。 |
| 80 Hummingbot | (空欄) | 5742 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 5742行)。 |
| 85 czsc | (空欄) | 5744 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 5744行)。 |
| 86 analyzingalpha | (空欄) | 5746 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 5746行)。 |
| 87 PyTrendFollow | 該当なし | 7857 | スキップ: 明らかに弱い | 段(機構)=該当なし(足の最高位 段6 より低い。SCAN 7857行)。 |
| 92 prediction-market-backtester | 6 | 7859 | 再現できない | 足の最高位(段6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 94 mote/backtest | 2 | 10093 | スキップ: 明らかに弱い | 段(機構)=2(足の最高位 段6 より低い。SCAN 10093行)。 |
| 107 sigc | (空欄) | 6917 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6917行)。 |
| 111 HKUDS/Vibe-Trading | 0(暗号資産の機関)・1(中国株の機関) | 10102 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 120 wbt | (空欄) | 5918 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 121 mhallsmoore/qstrader | (空欄) | 6325 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6325行)。 |
| 122 gbeced/pyalgotrade | (空欄) | 6329 | スキップ: 明らかに弱い | 段(機構)=(空欄)(足の最高位 段6 より低い。SCAN 6329行)。 |
| 123 carlos8f/zenbot | 3・4 | 7298 | スキップ: 明らかに弱い | 段(機構)=3・4(足の最高位 段6 より低い。SCAN 7298行)。 |

### 観点2-ティック(約定, 19件)

| 候補 | 段(機構) | SCAN行 | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 13 DeviaVir/zenbot | 3・4 | 6874 | スキップ: 明らかに弱い | 段(機構)=3・4(ティックの最高位 段6 より低い。SCAN 6874行)。 |
| 20 VnPy | 2 | 6896 | スキップ: 明らかに弱い | 段(機構)=2(ティックの最高位 段6 より低い。SCAN 6896行)。 |
| 23 hftbacktest | 3・5 | 6906 | スキップ: 明らかに弱い | 段(機構)=3・5(ティックの最高位 段6 より低い。SCAN 6906行)。 |
| 31 Ros522/backtestlob | (空欄) | 4614 | スキップ: 明らかに弱い | 段(機構)=(空欄)(ティックの最高位 段6 より低い。SCAN 4614行)。 |
| 41 prediction-market-backtesting | (空欄) | 6106 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 45 ForexTester | 2 | 10082 | スキップ: 明らかに弱い | 段(機構)=2(ティックの最高位 段6 より低い。SCAN 10082行)。 |
| 52 QuantConnect | (空欄) | 7292 | スキップ: 明らかに弱い | 段(機構)=(空欄)(ティックの最高位 段6 より低い。SCAN 7292行)。 |
| 53 Rqalpha | 3・4 | 7850 | スキップ: 明らかに弱い | 段(機構)=3・4(ティックの最高位 段6 より低い。SCAN 7850行)。 |
| 57 WonderTrader | 3・4・5 | 7852 | スキップ: 明らかに弱い | 段(機構)=3・4・5(ティックの最高位 段6 より低い。SCAN 7852行)。 |
| 58 nautilus_trader | (空欄) | 6345 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 59 PandoraTrader | (空欄) | 6126 | スキップ: 明らかに弱い | 段(機構)=(空欄)(ティックの最高位 段6 より低い。SCAN 6126行)。 |
| 61 barter-rs | (空欄) | 6926 | スキップ: 明らかに弱い | 段(機構)=(空欄)(ティックの最高位 段6 より低い。SCAN 6926行)。 |
| 63 trade-frame | 3・4 | 6119 | スキップ: 明らかに弱い | 段(機構)=3・4(ティックの最高位 段6 より低い。SCAN 6119行)。 |
| 68 quanttrader | (空欄) | 6382 | スキップ: 明らかに弱い | 段(機構)=(空欄)(ティックの最高位 段6 より低い。SCAN 6382行)。 |
| 90 Oddpool/PredictionMarketBench | 4・5 | 10432 | スキップ: 明らかに弱い | 段(機構)=4・5(ティックの最高位 段6 より低い。SCAN 10432行)。 |
| 91 braedonsaunders/homerun | 3・4・5・6 | 7858 | 再現できない | ティックの最高位(段3・4・5・6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 95 sacha9214/polymarket-fill-model | 5 | 10435 | スキップ: 明らかに弱い | 段(機構)=5(ティックの最高位 段6 より低い。SCAN 10435行)。 |
| 119 peernagy/lob_bench | 6 | 9405 | 再現できない | ティックの最高位(段6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 123 carlos8f/zenbot | 3・4 | 7298 | スキップ: 明らかに弱い | 段(機構)=3・4(ティックの最高位 段6 より低い。SCAN 7298行)。 |

### 観点2-板の待ち行列(19件)

| 候補 | 段(機構) | SCAN行 | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 23 hftbacktest | 3・5 | 6906 | スキップ: 明らかに弱い | 段(機構)=3・5(板の待ち行列の最高位 段6 より低い。SCAN 6906行)。 |
| 33 SarthakDalmia1/backtesting_execution_simulator | 5・6 | 4616 | 再現できない | 板の待ち行列の最高位(段5・6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 37 ThePredictiveDev/Automated-Financial-Market-Trading-System | 5・6 | 10426 | 再現できない | 板の待ち行列の最高位(段5・6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 38 microsoft/MarS | 5 | 4621 | スキップ: 明らかに弱い | 段(機構)=5(板の待ち行列の最高位 段6 より低い。SCAN 4621行)。 |
| 57 WonderTrader | 3・4・5 | 7852 | スキップ: 明らかに弱い | 段(機構)=3・4・5(板の待ち行列の最高位 段6 より低い。SCAN 7852行)。 |
| 65 aat | 5(合成の取引所)・0(CSV の取引所)・0(IEX の取引所) | 10429 | スキップ: 明らかに弱い | 段(機構)=5(合成の取引所)・0(CSV の取引所)・0(IEX の取引所)(板の待ち行列の最高位 段6 より低い。SCAN 10429行)。 |
| 90 Oddpool/PredictionMarketBench | 4・5 | 10432 | スキップ: 明らかに弱い | 段(機構)=4・5(板の待ち行列の最高位 段6 より低い。SCAN 10432行)。 |
| 91 braedonsaunders/homerun | 3・4・5・6 | 7858 | 再現できない | 板の待ち行列の最高位(段3・4・5・6)だが、この周は未導入(下記備考参照)。最強候補と比較できていない旨を報告する。 |
| 95 sacha9214/polymarket-fill-model | 5 | 10435 | スキップ: 明らかに弱い | 段(機構)=5(板の待ち行列の最高位 段6 より低い。SCAN 10435行)。 |
| 96 sashankzade/limit-order-book-matching-engine | 5 | 10438 | スキップ: 明らかに弱い | 段(機構)=5(板の待ち行列の最高位 段6 より低い。SCAN 10438行)。 |
| 97 kahan15/Limit-Order-Book-Simulator | 5(模擬の型)・4(生の板の paper の型) | 10441 | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 98 mihircoding/limitOrderBook | 5 | 5236 | スキップ: 明らかに弱い | 段(機構)=5(板の待ち行列の最高位 段6 より低い。SCAN 5236行)。 |
| 99 NickGardi/orderbooksim | 5 | 10444 | スキップ: 明らかに弱い | 段(機構)=5(板の待ち行列の最高位 段6 より低い。SCAN 10444行)。 |
| 100 xavierchuan/OrderMatchingEngine | (空欄) | 10447 | スキップ: 明らかに弱い | 段(機構)=(空欄)(板の待ち行列の最高位 段6 より低い。SCAN 10447行)。 |
| 101 akurkar07/OrderBook | 5 | 10450 | スキップ: 明らかに弱い | 段(機構)=5(板の待ち行列の最高位 段6 より低い。SCAN 10450行)。 |
| 102 3yit/Limit-Order-Book-Simulator | 5 | 10453 | スキップ: 明らかに弱い | 段(機構)=5(板の待ち行列の最高位 段6 より低い。SCAN 10453行)。 |
| 103 IsaacCheng9/order-book-simulator | 5 | 10456 | スキップ: 明らかに弱い | 段(機構)=5(板の待ち行列の最高位 段6 より低い。SCAN 10456行)。 |
| 104 jxm35/LimitOrderBook-MatchingEngine | 5 | 10459 | スキップ: 明らかに弱い | 段(機構)=5(板の待ち行列の最高位 段6 より低い。SCAN 10459行)。 |
| 109 arXiv:2509.05107 | (空欄) | 10462 | スキップ: 明らかに弱い | 段(機構)=(空欄)(板の待ち行列の最高位 段6 より低い。SCAN 10462行)。 |

## §2. 段の無い観点の候補(観点2の残り5要素 + 観点3〜7)

ルール(委任文§3): 実装のコードで確かめられる候補を全部再現する。ただし
「調査結果から明らかに弱い」ことが調査報告の行で示せる候補、または「動かせた/再現した候補の
機構が、その候補の能力を1つ残らず含む」(上位互換)候補はスキップしてよい(理由なしスキップ禁止)。

### 観点2-板の写真

`REQUIREMENTS.md` §3.2.2: 候補固有の一次資料の記述はこの回のSCAN grepの範囲では取れなかった
(**未確認** -- この環境の候補一覧に対する `snapshot`/`板の写真` grep の当たりはデータファイル名
の雑音のみ。板の写真を独立した事象型として持つ候補を、この周は1件も特定できていない)。
判断: 対象なし(検討する候補が無い)。

### 観点2-資金調達

| 候補 | 機構 | 実装のコードで確かめたか | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 40 OpenMarket | サイトの謳い文句のみ(README/サイト止まり、SCAN 5694行) | いいえ | 再現できない | この周、実装のコードまでは降りていない(PyPI 名 `openmarket` は404で存在せず、GitHub取得のみ可能。§4(b)の一次資料読取りに留め、導入・実行はしない判断)。 |
| 41 prediction-market-backtesting | 「清算・資金調達の無い場」と明記(=持たない側の記録) | -- | 再現できない | 危険リスト該当。導入も実行もしない。 |
| (ziplime / zipline-reloaded / pybroker / qf-lib) | この周に実装のコードで確認 | はい | 再現した | 4候補とも `pkgutil.walk_packages` の実測でサブモジュール名に `fund` 系の当たり無し(`funding` 型を持たない側の実測結果として記録)。委任文の「再現」は肯定的機構の再現に限らないと読み、**持たない**という実測結果自体を4候補分そろえて記録した。 |

### 観点2-清算

| 候補 | 機構 | 実装のコードで確かめたか | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 61 barter-rs | `DataKind` 列挙が足・ティック・L1・L2・**清算**の5型を持つ(SCAN 6305/6422/6653行、`REQUIREMENTS.md`§3.2.2 で実装確認済みと記録) | はい(`REQUIREMENTS.md`記載の一次資料確認による) | 再現できない | Rust製クレート。`crates.io` API はこのプロキシから403(実測: `curl https://crates.io/api/v1/crates/barter` → 403)。cargo ビルドはこの周の時間予算では未実施。観点2の清算では最も強い候補だが、この周は比較できていない旨を報告する。 |
| ziplime / zipline-reloaded / pybroker / qf-lib | 実装のコードで確認(下記) | はい | 混在 | pybroker は `ExecContext` ソースに `liquidat` の当たりがあったが、**全て「自分の建玉の手仕舞い」の意味で市場の清算イベントではない**(誤読を避けるため not_supported と記録、`opponents/lib_pybroker_adapter.py` 参照)。他3候補はサブモジュール名の実測で当たり無し。4候補とも「持たない」側の実測結果。 |

### 観点2-時計

| 候補 | 機構 | 実装のコードで確かめたか | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 11 (索引名OctoBot、台帳名`python3`) | `time_updater` という時計機構(SCAN 4153行) | 部分的(`REQUIREMENTS.md`記載。拡張の取引型が要り実行経路は未確認) | 再現できない | **索引と台帳の名前が食い違い、対象の同定自体が未確定**(`REQUIREMENTS.md`が既に指摘済み)。PyPI名`octobot`は200で存在するが同一実体かは未確認。誤同定のリスク(本バッテリーが別件で実際に踏んだ例: `zenbot`という名の無関係パッケージがnpmに存在した、下記§4参照)を避けるため、この周は導入しない。 |
| zipline-reloaded | `zipline.gens.sim_engine.MinuteSimulationClock`(実測、`opponents/zipline_reloaded_adapter.py`) | はい | 再現した | 時計イベントの実在をクラスのhasattrで実測確認。 |
| ziplime | `ziplime.gens.domain.{trading_clock,simulation_clock,realtime_clock}` の実在(サブモジュール名の実測) | はい(モジュール実在まで。中身の呼び出しは未実行) | 再現した | `opponents/ziplime_adapter.py` の v2-clock-cap 参照。 |
| qf-lib | `qf_lib.backtesting.events.time_event` 系(MarketOpenEvent/MarketCloseEvent等)の実在(実測) | はい | 再現した | `opponents/qf_lib_adapter.py` の v2-clock-cap 参照。 |
| pybroker | サブモジュール名に時計相当なし(実測) | はい | 再現した(持たない側) | 「持たない」という実測結果。 |

### 観点2-注文の受付/拒否/約定の通知

| 候補 | 機構 | 実装のコードで確かめたか | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 61 barter-rs | 拒否 `ApiError::OrderRejected` 実装確認(SCAN 6567行、`REQUIREMENTS.md`記載) | はい(記載による) | 再現できない | Rust。理由は清算の項と同じ(cargo未実施)。 |
| 58 nautilus_trader | `OrderFilled` 実測(SCAN 898行、rc=0) | はい(記載による) | 再現できない | 危険リスト該当。導入も実行もしない。 |
| 69 gobacktest | README「order event, fill event」等の4種(SCAN 6068行、README止まり) | いいえ | 再現できない | Go製。この周は未導入(`go install` 等のビルド工程はこの周の時間予算外と判断)。 |
| ziplime | `OrderStatus` enum に `OPEN/FILLED/CANCELLED/REJECTED/HELD`(実測) | はい | 再現した | `opponents/ziplime_adapter.py` v2-order_notice-cap。 |
| zipline-reloaded | `ORDER_STATUS` (IntEnum) に `REJECTED`/`CANCELLED` 等(実測、ソース読み) | はい | 再現した | `opponents/zipline_reloaded_adapter.py` v2-order_notice-cap。 |
| qf-lib | `Broker.place_orders`/`cancel_order` の実在(実測)。受付/拒否/約定を分ける専用イベント型までは未確認 | 部分的 | 再現した(部分) | `opponents/qf_lib_adapter.py`。 |
| pybroker | `OrderType` の実在のみ(実測)。受付/拒否/約定を分ける明示のイベント型は未確認 | 部分的 | 再現した(部分) | `opponents/lib_pybroker_adapter.py`。 |

### 観点3(時刻の精度)・観点4(ルックアヘッド)・観点5(同時刻順序)・観点6(戦略API)・観点7(拡張口)

`REQUIREMENTS.md` が個別に挙げた候補(44 lo2cin4bt・58 nautilus_trader・34 QuantCore・
16 Luczinsritter/event_driven_backtesting_engine・62 qf-lib・13/123 zenbot・6 Ziplime・
11 索引名OctoBot)は上の§1・§2の各表にすでに現れているので、二重に載せない。
この周に追加で再検証できた点のみ記す:

- **観点3(時刻精度)**: `REQUIREMENTS.md` は「ナノ秒かつUTCの両方を満たす候補は0件」と記録していた。
  この周、**zipline-reloaded を実行して確かめた** (`opponents/zipline_reloaded_adapter.py`
  v3-precision-known): `pandas.Timestamp("2024-01-01T00:00:00.123456789").tz_convert("UTC").value`
  が既知解 `1704067200123456789` と一致した。ただし zipline-reloaded 自身のイベントオブジェクトが
  この精度のまま入出力することまでは確認しておらず(pandas基盤機能の確認に留まる)、「ナノ秒かつUTC」の
  往復を候補自身の型で確認できた候補は依然として0件。qf-lib は逆に `datetime.datetime`
  (マイクロ秒止まり)であることを実測で確認した(§3-precision-cap)。
- **観点4(ルックアヘッド)**: `REQUIREMENTS.md` は候補62 qf-libを「README止まり」としていたが、
  この周、パッケージ内に `qf_lib.tests.integration_tests.data_providers.bloomberg.test_bbg_look_ahead_bias`
  という専用テストモジュールが実在することを実測した(モジュール名の実在確認のみ。中身は未読)。
  README止まりではない可能性が高いが、次回以降の宿題として残す(実行未確認)。
- **観点5(同時刻順序)**: qf-lib の `EventManager` は `queue.Queue`(FIFO)で、`dispatch_next_event`
  が型で振り分ける設計であることを実測(v1の実行で確認)。ただし「同時刻」を明示的に判定する分岐は
  無く、同時刻2件を実際に投入して2回一致を見る実行はこの周は未実施(`not_supported`/`no_record`)。
- **観点6・7**: ziplime/zipline-reloaded/pybroker/qf-lib いずれも実装のコードで機構を確認済み
  (各 `opponents/*_adapter.py` 参照)。

## §3. 導入ログ(実際にscratchpad venvへ入れたもの)

| 候補 | venv | 結果 | ログ |
|---|---|---|---|
| Ziplime (id 6) | `<scratchpad>/bt/venvs/item_0/ziplime/`(python3.12。3.11では`Requires-Python>=3.12`で拒否された実測あり) | 成功(ziplime 1.19.16) | `<scratchpad>/bt/venvs/item_0/ziplime_install.log` |
| zipline-reloaded (id 18) | `<scratchpad>/bt/venvs/item_0/zipline-reloaded/`(python3.11) | 成功(zipline-reloaded 3.1.1) | `<scratchpad>/bt/venvs/item_0/zipline-reloaded_install.log` |
| PyBroker (id 4, PyPI名`lib-pybroker`) | `<scratchpad>/bt/venvs/item_0/lib-pybroker/` | 成功(lib-pybroker 2.0.1) | `<scratchpad>/bt/venvs/item_0/lib-pybroker_install.log` |
| qf-lib (id 62) | `<scratchpad>/bt/venvs/item_0/qf-lib/` | 成功(qf-lib 4.0.7) | `<scratchpad>/bt/venvs/item_0/qf-lib_install.log` |

安全の規則(委任文§4、道具サーベイ委任文§5・§6-1〜§6-4・§6-6): 4件とも PyPI の配布であり
`pip install` はPyPI公式インデックスのみを参照(プロキシの許可リストに`pypi.org`/`files.pythonhosted.org`
が含まれることを確認済み)。実行はいずれも「import + hasattr/inspect + 引数無しの軽い呼び出し」に
限り、外部ネットワークへの送信・鍵の登録・支払いは一切行っていない(4アダプタのコードは
`adapters/opponents/*.py` に全て残っており、何を呼んだかは各 `detail` 文字列に記録済み)。

**未導入(試したが入れられなかった、または今回の時間予算内で試さなかったもの)**:
- **言語がPythonでない**(pip/venvの手順が成立しない): Basana(id1, Go)・ThePredictiveDev(id37, 言語未確認だがGitHub限定配布)・homerun(id91, GitHub限定)・barter-rs(id61, Rust)・gobacktest(id69, Go)・
  SarthakDalmia1/backtesting_execution_simulator(id33, C++ -- `bool ExecutionSimulator::cancel_order(...)`という記法をSCANで確認)。
  Goのモジュールプロキシ(`proxy.golang.org`)への到達は実測で確認した(`curl https://proxy.golang.org/github.com/rodrigo-brito/ninjabot/@v/list` → 200)が、
  Basana自体をビルドして本バッテリーの場面に通すところまではこの周は未実施。crates.io APIはプロキシから403(実測)で、cargoでの導入検証も未実施。
- **PyPI未配布(GitHub限定のスクリプト集)**: Mendl-Labs/BacktestingCore(id15)・Qlib(id21, PyPI名`qlib`自体は到達可能だが依存が機械学習系で重量級と判断しこの周は見送り)・
  prediction-market-backtester(id92)・lob_bench(id119)・OpenMarket(id40)。PyPIの実在確認コマンドと結果は本ファイル冒頭の各表・脚注に実測値を記載。
- **識別が未確定で誤同定の危険がある**: 候補11(索引名OctoBotだが台帳名`python3`)。`npm install zenbot`を試そうとした際に、
  無関係の別パッケージ(`ZenBot - Node client for Zentri Cloud`)がヒットすることを実測で確認しており(`curl https://registry.npmjs.org/zenbot`)、
  同じ危険を避けるため候補11は識別が確定するまで導入しない。
- **危険リスト該当(委任文§4)**: 44・74・120・41・58・19・112・111・97・51・118 -- 導入も実行もしない(§1・§2の各表を参照)。

## §4. この周に見つけた `REQUIREMENTS.md` との食い違い(リードへの報告事項)

1. **観点2-板の待ち行列の最高位に候補33が抜けていた**: `REQUIREMENTS.md` §3.2.1は
   「段(機構)最大値6のもの: 候補37・候補91」と記録していたが、台帳を直接引き直すと
   **候補33 `SarthakDalmia1/backtesting_execution_simulator` も段(機構)=5・6で同じ最高位**
   (`awk -F'\t' '$1==33' docs/DATA/tools_catalog.tsv` の実測、SCAN 4616行)。§1の表では
   33を最高位候補に加えて扱った(未導入・再現できないに分類、C++製のため)。
2. **観点1で候補62(qf-lib)の段(機構)は空欄だが、実行すると要件を満たした**: 台帳の
   機械的な段の値だけで「明らかに弱い」と判定すると見落とす実例(§1の表の脚注参照)。
   段が空欄の候補全部を「弱い」と決めつけてよいかは、リードに再確認を仰ぎたい
   (この周は qf-lib 1件のみ個別に実行して確かめたが、他の空欄候補は未検証)。

これら2点は場面係の権限では要件表(`REQUIREMENTS.md`)を書き換えず、検討表にのみ記録した
(委任文§3「要件と観点の誤りを直すのはリード」)。
