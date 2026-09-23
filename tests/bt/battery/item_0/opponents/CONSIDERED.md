# 検討表 -- 項目0「核」の調査結果の候補(場面係、2026-09-23 直し)

委任文 `docs/DATA/delegations/20260923_backtest_env_prompt.md` §3「動かせない候補の検討と再現」に従う。
**動かせなかった候補は1件も機構を検討せずに外さない。** 材料は `docs/DATA/tools_catalog.tsv`
(台帳)と `docs/DATA/SCAN_2026-09-21_tools.md`(SCAN、10,694行)。

**この回の直し(監査役の指摘 b1-1〜b1-10、根本原因は `ROOTCAUSE_1.md`)**: 旧版は候補の強弱を
`段(機構)`/`段(既定)`(台帳10・11列目)で判定していたが、`REQUIREMENTS.md`§3.2.1 が既に
明記しているとおり、その2列は「区分1-市場影響と約定の模型」(**項目3**の観点)専用であり、
項目0の観点1・観点2-足・観点2-ティックとは無関係の別軸だった(実測: `61 barter-rs` は
`段(機構)`が空欄だが`市場影響と約定の模型`列も空欄/×で、これは「段が測れていない」のではなく
「市場影響の模型という項目3の話がそもそも無い」ことを意味する)。この回、判定の軸を
**その観点で確認できる能力の有無(台帳の足/ティック/イベント駆動などの○列、または実行結果)**
に直し、スキップの理由はすべて**上位互換**(規則6・9)に統一した。あわせて、**候補1 `Basana`
を新規に導入した**(旧版は「言語がGo」としていたが誤りで、`pip show basana` の実測どおり
実際はPyPI配布のPython/asyncioパッケージであり、`<scratchpad>/bt/venvs/item_0/basana/` へ
`pip install basana` で導入できた。§3参照)。これにより、観点1・観点2-足で「最強候補と
比較できていない」としていた候補のうち1件(Basana)は、この回、実行による比較が実現した。

危険リスト(委任文§4、11件。導入も実行もしない): 44・74・120・41・58・19・112・111・97・51・118。

**この回の直し(監査役の指摘 b2-1〜b2-3、根本原因は `ROOTCAUSE_2.md`)**: (1) 全ての観点表から、
実際に動かせた5候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)自身の
行を削除した(この検討表に載るのは動かせなかった候補だけであり、動かせた候補の結果は資料係の
比較表 `gen_round1_tables.py` の側に置くべきだった。b2-1)。削除の結果、候補0件になった観点
(観点2-板の写真・観点6・観点4・観点5)は規則9の「候補0件:」形式に直すか、grepで見つかった
候補を新規の行として追加した。`gen_round1_tables.py` の `_OPP_TARGETS` に漏れていた
`opp_basana` も同時に追加し、実行し直した(同根の欠陥)。(2) 観点2-ティック(約定)の候補
プールを部分的に洗い直し、候補69 `gobacktest`(README「fill event」)を追加した(b2-3。
詳細は§1の該当観点、および`ROOTCAUSE_2.md`)。(3) b1-10で場面係が自分で答えた「観点2-板の
待ち行列」削除の当否は、この回、改めて「リードに聞くこと」に載せて確認を仰ぐ(b2-2。§4参照)。

## §1. 実装のコードで確かめられる能力ごとの検討(観点1・観点2-足・観点2-ティック)

**旧版の見出し「段のある観点」は撤回する**(上記のとおり、この3観点に段の軸は無い)。
規則(委任文§3): 実装のコードで確かめられる候補を全部再現する。「調査結果から明らかに弱い」
ことが調査報告の行で示せる候補、または「上位互換」(動かせた/再現した候補の機構が、スキップする
候補のその観点の能力を1つ残らず含む)候補はスキップしてよい(理由なしスキップ禁止)。
危険リスト該当は機構に関わらず「再現できない」(理由=安全)。

実際に再現できたのは Python かつ PyPI 配布があり、`<scratchpad>/bt/venvs/item_0/` に
`pip install` できたもの(§3備考に導入ログの場所)。**最高位でも Go/Rust/C++ 製、または
GitHub のみでパッケージ配布が無い候補は、この周は未導入。**そのうち`61 barter-rs`は
`opponents/barter_rs_repro.py`(一次資料どおりの最小の構造的書き直し。§3参照)で再現した。

### 観点1: 事象駆動アーキテクチャ(19件)

動かせた候補: 5 件(§3で実際に導入した5件全部をこの観点の場面にも通した。規則4「動かせた道具は全部の場面に通す」)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 13 DeviaVir/zenbot | イベント駆動=○のみ(SCAN 6874行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 6874行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 23 hftbacktest | イベント駆動=○のみ(SCAN 6906行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 6906行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 37 ThePredictiveDev/Automated-Financial-Market-Trading-System | イベント駆動=○のみ(SCAN 10426行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 10426行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 41 prediction-market-backtesting | (SCAN 6106行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 52 QuantConnect | イベント駆動=○のみ(SCAN 7292行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 7292行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 53 Rqalpha | イベント駆動=○のみ(SCAN 7850行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 7850行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 57 WonderTrader | イベント駆動=○のみ(SCAN 7852行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 7852行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 58 nautilus_trader | (SCAN 6345行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 61 barter-rs | イベント駆動=○のみ(SCAN 6926行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 6926行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 63 trade-frame | イベント駆動=○のみ(SCAN 6119行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 6119行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 65 aat | イベント駆動=○のみ(SCAN 10429行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 10429行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 68 quanttrader | イベント駆動=○のみ(SCAN 6382行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 6382行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 69 gobacktest | イベント駆動=○のみ(SCAN 6124行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 6124行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 91 braedonsaunders/homerun | イベント駆動=○のみ(SCAN 7858行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 7858行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 123 carlos8f/zenbot | イベント駆動=○のみ(SCAN 7298行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はイベント駆動=○のみ(SCAN 7298行)。実際に再現した候補(1 Basana・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |

### 観点2-足(55件)

動かせた候補: 5 件(§3で実際に導入した5件全部をこの観点の場面にも通した。規則4「動かせた道具は全部の場面に通す」)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 2 Backtrader | 足=○のみ(SCAN 6839行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6839行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 3 PySystemtrade | 足=○のみ(SCAN 9401行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 9401行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 5 Lean CLI | 足=○のみ(SCAN 6849行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6849行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 7 Superalgos | 足=○のみ(SCAN 6855行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6855行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 8 OpenTrader | 足=○のみ(SCAN 9402行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 9402行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 10 fast-trade | 足=○のみ(SCAN 6864行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6864行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 11 python3 | 足=○のみ(SCAN 8452行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 8452行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 13 DeviaVir/zenbot | 足=○のみ(SCAN 6874行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6874行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 15 Mendl-Labs/BacktestingCore | 足=○のみ(SCAN 6879行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6879行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 16 Luczinsritter/event_driven_backtesting_engine | 足=○のみ(SCAN 6882行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6882行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 19 Jesse | (SCAN 9403行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 20 VnPy | 足=○のみ(SCAN 6896行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6896行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 21 Qlib | 足=○のみ(SCAN 6899行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6899行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 40 OpenMarket | 足=○のみ(SCAN 5725行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 5725行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 43 QuantDinger | 足=○のみ(SCAN 4626行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 4626行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 44 lo2cin4 | (SCAN 5904行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 45 ForexTester | 足=○のみ(SCAN 10082行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 10082行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 46 MT4裁量トレード練習君プレミアム | 足=○のみ(SCAN 5727行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 5727行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 48 BacktestingMax | 足=○のみ(SCAN 5729行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 5729行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 50 AlgoTest | 足=○のみ(SCAN 10088行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 10088行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 51 QUANTAXIS | (SCAN 9404行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 52 QuantConnect | 足=○のみ(SCAN 7292行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7292行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 53 Rqalpha | 足=○のみ(SCAN 7850行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7850行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 54 finmarketpy | 足=○のみ(SCAN 7851行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7851行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 55 backtesting.py | 足=○のみ(SCAN 6344行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6344行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 56 zvt | 足=○のみ(SCAN 5733行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 5733行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 57 WonderTrader | 足=○のみ(SCAN 7852行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7852行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 58 nautilus_trader | (SCAN 6345行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 60 Hikyuu | 足=○のみ(SCAN 7853行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7853行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 61 barter-rs | 足=○のみ(SCAN 6926行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6926行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 67 lumibot | 足=○のみ(SCAN 7854行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7854行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 68 quanttrader | 足=○のみ(SCAN 6382行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6382行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 69 gobacktest | 足=○のみ(SCAN 6124行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6124行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 70 PineForge | 足=○のみ(SCAN 7855行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7855行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 72 QTradeX | 足=○のみ(SCAN 7856行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7856行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 73 vectorbt | 足=○のみ(SCAN 5907行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 5907行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 74 ml-quant-trading | (SCAN 5910行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 75 Freqtrade | 足=○のみ(SCAN 6346行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6346行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 80 Hummingbot | 足=○のみ(SCAN 5742行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 5742行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 85 czsc | 足=○のみ(SCAN 5744行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 5744行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 86 analyzingalpha | 足=○のみ(SCAN 5746行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 5746行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 87 PyTrendFollow | 足=○のみ(SCAN 7857行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7857行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 92 prediction-market-backtester | 足=○のみ(SCAN 7859行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7859行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 94 mote/backtest | 足=○のみ(SCAN 10093行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 10093行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 107 sigc | 足=○のみ(SCAN 6917行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6917行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 111 HKUDS/Vibe-Trading | (SCAN 10102行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 120 wbt | (SCAN 5918行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 121 mhallsmoore/qstrader | 足=○のみ(SCAN 6325行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6325行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 122 gbeced/pyalgotrade | 足=○のみ(SCAN 6329行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 6329行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 123 carlos8f/zenbot | 足=○のみ(SCAN 7298行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は足=○のみ(SCAN 7298行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |

### 観点2-ティック(約定)(19件)

動かせた候補: 5 件(§3で実際に導入した5件全部をこの観点の場面にも通した。規則4「動かせた道具は全部の場面に通す」)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 13 DeviaVir/zenbot | ティック=○のみ(SCAN 6874行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 6874行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 20 VnPy | ティック=○のみ(SCAN 6896行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 6896行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 23 hftbacktest | ティック=○のみ(SCAN 6906行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 6906行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 31 Ros522/backtestlob | ティック=○のみ(SCAN 4614行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 4614行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 41 prediction-market-backtesting | (SCAN 6106行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 45 ForexTester | ティック=○のみ(SCAN 10082行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 10082行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 52 QuantConnect | ティック=○のみ(SCAN 7292行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 7292行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 53 Rqalpha | ティック=○のみ(SCAN 7850行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 7850行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 57 WonderTrader | ティック=○のみ(SCAN 7852行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 7852行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 58 nautilus_trader | (SCAN 6345行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 59 PandoraTrader | ティック=○のみ(SCAN 6126行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 6126行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 61 barter-rs | ティック=○のみ(SCAN 6926行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 6926行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 63 trade-frame | ティック=○のみ(SCAN 6119行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 6119行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 68 quanttrader | ティック=○のみ(SCAN 6382行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 6382行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 90 Oddpool/PredictionMarketBench | ティック=○のみ(SCAN 10432行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 10432行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 91 braedonsaunders/homerun | ティック=○のみ(SCAN 7858行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 7858行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 95 sacha9214/polymarket-fill-model | ティック=○のみ(SCAN 10435行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 10435行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 119 peernagy/lob_bench | ティック=○のみ(SCAN 9405行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 9405行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 123 carlos8f/zenbot | ティック=○のみ(SCAN 7298行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力はティック=○のみ(SCAN 7298行)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)がこの能力を実行で確認済み(§3導入ログ・round_check/opp_*_r1.tsv)。ゆえに上位互換(段(機構)は本観点と無関係の別軸で使えない。REQUIREMENTS.md§3.2.1: 段は区分1-市場影響と約定の模型=項目3専用の列)。 |
| 69 gobacktest | README逐語「data event, signal event, order event and fill event」(SCAN 6068行) | いいえ | スキップ: 明らかに弱い | `fill event`という型はREADMEの列挙止まり(SCAN 6068行、未確認)。実際に再現した候補(1 Basana・4 PyBroker・6 Ziplime・18 zipline-reloaded・62 qf-lib)が約定の受理を実行で確認済み(§3導入ログ)。ゆえに上位互換(この行はb2-3を受け、`grep -noE ".{0,40}(TradeEvent\|FillEvent\|trade event\|fill event\|execution report\|約定イベント\|約定通知\|trade_event\|fill_event)." docs/DATA/SCAN_2026-09-21_tools.md` で新規に見つけた候補。旧版の`ティック`列基準の候補プールには含まれていなかった=`ROOTCAUSE_2.md` b2-3)。 |

**注記(2026-09-23、場面係。b2-3の直しを反映)**: この観点の候補一覧は元々カタログの`ティック`列
(高頻度/tick粒度データの対応)を流用したものだったが、`ティック`列は「tick粒度の市場データを
扱えるか」という別の(より狭い)能力を指しており、P0-3が求める『約定という事象型を1件受理
できるか』とは軸が違う(b1-4と同じ、無関係の列を流用した形の誤り)。この回、SCANを
`約定/fill event/trade event`の語で直接grepし直し(コマンドは上表69番の行、およびROOTCAUSE_2.md
b2-3)、旧`ティック`列の候補プールに無かった**候補69 `gobacktest`**を新規に見つけて追加した
(README逐語「…order event and fill event」、SCAN 6068行)。13・123(zenbot系)は`ティック`列
でも`trade event`のgrepでも両方拾われ、一次資料での「約定の到着を事象として受ける」実測
(SCAN 8125行台、`eventBus.on('trade', queueTrade)`)がある。**残る旧`ティック`列由来の候補
(2 Backtrader等、この表の69・13・123を除く行)については、それぞれが個別に約定/fillの
一次資料の裏付けを持つかをこの回のgrepの範囲では確認しきれていない(未確認、CLAUDE.md
§0.2 A-18により安全側に丸めず「未確認」のまま報告する)。全件の洗い直しは次の周の宿題として
残る(部分的に実施済み、`ROOTCAUSE_2.md` b2-3参照)。
### (撤去) 観点2-板の待ち行列 -- 項目0の観点から外す(この回の場面係、範囲の訂正)

旧版はこの表(19件)を「段のある観点」として持っていたが、`REQUIREMENTS.md`§3.2.1 が明記する
とおり `段(機構)`/`段(既定)` は「区分1-市場影響と約定の模型」(**項目3**の観点)専用であり、
項目0の8事象型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知。
`REQUIREMENTS.md`§1)のどれにも「板の待ち行列」という型は無い。板の待ち行列(注文の列内での
順位を追う執行の模型)は**項目3の話であって項目0の核の観点(P0-1〜P0-7)には無い**。よって
この表は項目0のCONSIDERED.mdの範囲外と判断し、削除する(要件`REQUIREMENTS.md`のP0-1〜P0-7
自体は変えていない -- §3「要件と判定の固定」が禁じるのは固定した観点を緩める/厳しくする
ことで、範囲外だった重複表を外すことはそれに当たらない、とこの回の場面係は判断した。異論が
あれば聞く)。この表で挙げていた候補(`33 SarthakDalmia1/backtesting_execution_simulator`・
`37 ThePredictiveDev`・`91 braedonsaunders/homerun` など)のうち、観点1(イベント駆動)の
候補プールに含まれるものは§1の観点1表で引き続き検討している。

## §2. 段の無い観点の候補(観点2の残り: 板の写真・板の差分・資金調達・清算・時計・注文通知)

規則(委任文§3): 実装のコードで確かめられる候補を全部再現する。ただし
「調査結果から明らかに弱い」ことが調査報告の行で示せる候補、または「動かせた/再現した候補の
機構が、その候補の能力を1つ残らず含む」(上位互換)候補はスキップしてよい(理由なしスキップ禁止)。

### 観点2-板の写真

動かせた候補: 5 件(§3で導入した5件全部をこの場面にも通した。規則4)。

`REQUIREMENTS.md`§3.2.2 のとおり、動かせた5候補を除く候補固有の一次資料の記述はこの回の
SCAN grepの範囲では取れなかった(**未確認**、`grep -n "snapshot\|板の写真" docs/DATA/SCAN_2026-09-21_tools.md`
の当たりはデータファイル名の雑音のみ)。板の写真を独立した事象型として持つ非導入候補を、
この周は1件も特定できていない。

候補 0 件: `grep -n "book snapshot\|order book snapshot\|板の写真" docs/DATA/SCAN_2026-09-21_tools.md`

### 観点2-板の差分

**旧版はこの節を欠いていた**(項目0の8事象型の1つ「板の差分」の検討表が無かった。この回、追加した)。

動かせた候補: 5 件(§3で導入した5件全部をこの場面にも通した。規則4)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 41 prediction-market-backtesting | README逐語「Book replay order book deltas with trade ticks」(SCAN 6070行) | いいえ | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |

候補0件(上記1件と、動かせた5候補を除く): `grep -n "order book snapshot\|depth update\|incremental\|板の差分" docs/DATA/SCAN_2026-09-21_tools.md`

### 観点2-資金調達

動かせた候補: 5 件(§3で導入した5件全部をこの場面にも通した。規則4)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 40 OpenMarket | サイトの謳い文句のみ(SCAN 5694行) | いいえ | 再現できない | (a) SCAN(5694行)はサイトの謳い文句のみで機構の記述が無く、(b) 一次資料(GitHub取得は可能・PyPI名`openmarket`は404で存在せず)のコード自体はこの周は未取得。両方で材料が再現に足りない。 |
| 41 prediction-market-backtesting | 「清算・資金調達の無い場」と明記(=持たない側の記録、SCAN 4112行) | いいえ | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |

### 観点2-清算

動かせた候補: 5 件(§3で導入した5件全部をこの場面にも通した。規則4)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 61 barter-rs | `Liquidation{side,price,quantity,time}`(一次資料。`https://raw.githubusercontent.com/barter-rs/barter-rs/main/barter-data/src/subscription/liquidation.rs` 取得日2026-09-23) | いいえ(barter-rsの実クレートではなく、構造の最小再現) | 再現した | `opponents/barter_rs_repro.py`(この回に場面係が新規作成)。フィールド形(side/price/quantity/time)は一次資料どおりに保持できることを実測したが、`time`はPythonの`datetime`(マイクロ秒止まり)を使うため既知解のns精度は往復しない(実測: 入力ts_ns 1700000000123456789 → 復元 1700000000123457024、差235ns)。**構造は再現、精度は不一致**として記録する。 |

### 観点2-時計

動かせた候補: 5 件(§3で導入した5件全部をこの場面にも通した。規則4)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 11(索引名OctoBot、台帳名`python3`) | `time_updater` という時計機構(SCAN 4153行) | いいえ | 再現できない | (a) SCANの記載(候補11、時計機構ありと記録)は索引名と台帳名が食い違ったまま同定に使えず、(b) 一次資料(PyPI名`octobot`は200で存在確認したが、それが同一実体かはこの周は未確認)でも同定できなかった。両方で材料が同定・再現に足りない(誤同定のリスクを避けるため導入もしない)。 |

### 観点2-注文の受付/拒否/約定の通知

動かせた候補: 5 件(§3で導入した5件全部をこの場面にも通した。規則4)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 61 barter-rs | `ApiError::OrderRejected(String)`(一次資料。`https://raw.githubusercontent.com/barter-rs/barter-rs/main/barter-execution/src/error.rs` 取得日2026-09-23、95行) | いいえ(構造の最小再現) | 再現した | `opponents/barter_rs_repro.py` の `order_notice_supported()` を実行、`OrderRejected("synthetic-1")` を送出・捕捉して理由文字列が保たれることを確認した(実測 True)。 |
| 58 nautilus_trader | `OrderFilled`(実測、SCAN 898行) | いいえ | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |
| 69 gobacktest | README「order event, fill event」等の4種(SCAN 6068行、README止まり) | いいえ | 再現できない | (a) SCAN(6068行)はREADMEの列挙止まりで挙動の記述が無く、(b) 一次資料(Go製、`go install`等のビルドはこの周の時間予算外と判断し未取得)。両方で材料が再現に足りない。 |

### 観点3(時刻の精度)

**旧版はこの観点をSCAN grepのみの narrative で済ませていた(規則9違反 = b1-7)。この回、§3で
導入した5候補全部を実際に実行した表に直す。**

動かせた候補: 5 件(§3で導入した5件全部をこの場面にも通した。規則4)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 44 lo2cin4 | 契約スキーマの`const`で`unit=nanosecond`/`time_standard=UTC`を固定(一次資料、SCAN 5889行) | いいえ | 再現できない | 危険リスト該当(委任文§4)。導入も実行もしない。 |

### 観点6(戦略API: 事象ごとの呼び出し・発注・取消)

動かせた候補: 5 件(§3で導入した5件全部をこの場面にも通した。規則4)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 13 DeviaVir/zenbot | `eventBus.on('trade', queueTrade)`(一次資料、SCAN 8125行台)。発注・取消の専用APIの記述なし | いいえ | スキップ: 明らかに弱い | 確認できる能力はイベントコールバック(trade事象の受信)のみ(SCAN 8125行台)。発注(`place`相当)・取消(`cancel`相当)のAPIの記述はREQUIREMENTS.md§3.2.6のgrep範囲に無い。実際に再現した候補(1 Basana)が`create_market_order`/`create_limit_order`/`cancel_order`の3つを実行で確認済み(§3導入ログ)。ゆえに上位互換。 |

### 観点7(他項目の差し込み口: 約定模型・遅延模型・費用・口座)

動かせた候補: 5 件(§3で導入した5件全部をこの場面にも通した。規則4)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 52 QuantConnect | 「約定の模型を差し替えながら」イベント駆動で回す(SCAN 6151行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は約定模型の差し替え可能性のみ(SCAN 6151行、README相当・未確認)。実際に再現した候補(1 Basana)がこの能力(fill_model差し込み口)を一次資料+実行で確認済み(§3導入ログ)。ゆえに上位互換。 |
| 23 hftbacktest | 「列の模型を差し替えられる形」(SCAN 9234行) | いいえ | スキップ: 明らかに弱い | カタログで確認できる能力は列の模型差し替えのみ(SCAN 9234行、未確認)。実際に再現した候補(1 Basana)が同種の差し込み口(fill_model)を確認済み。ゆえに上位互換。 |

**観点4(ルックアヘッド禁止の構造性)・観点5(同時刻事象の決定的順序)について(この周は未完了、そのまま報告する)**

**この回の直し(b2-1)**: 旧版はこの2観点を1つの表に混在させ、委任文§3規則3「表は観点ごとに
まとめる」に反していた。同時に、その1つの表にqf-libの結果(動かせた候補=検討表に載る資格が
無い)を2行(観点4用・観点5用)載せてもいた(b2-1と同じ欠陥のもう一つの現れ)。観点ごとに
`### 観点4`・`### 観点5`の2つの見出しに分け、qf-libの2行は削除した(qf-libの結果は資料係の
比較表 `gen_round1_tables.py` の側で扱う)。

**動かせた候補: 5 件を実際に実行したが、v4/v5の場面固有のハンドラは戦略側の足場(strategyオブジェクト/
複数事象型の同時投入)を要し、この周は `no_record`(結果なし)で終わった(round_check参照)。**
`結果なし`は規則6の4判断のどれにも当たらない。動かせた5候補(1 Basana・4 PyBroker・6 Ziplime・
18 zipline-reloaded・62 qf-lib)は「まだ比べていない」とそのまま報告する(A-18: 安全側に丸めない。
規則の言葉で言えば「動かなかった」ではなく「この周は行っていない」。動かせた候補自身の行は
この検討表には置かない=b2-1)。**観点4・観点5とも、5候補全部が「まだ比べていない」。圧倒の
判定にはこの5候補×2観点=10件を「比較していない」と候補名付きで報告する(ROOTCAUSE_1.md
のb1-10の回答、および本ファイル§4)。**

### 観点4(ルックアヘッド禁止の構造性)

動かせた候補: 5 件(v4の場面固有ハンドラはこの周いずれも`no_record`。「まだ比べていない」として上で報告済み)。

`REQUIREMENTS.md`§3.2.4のgrep(`grep -n "先読み\|未来の情報\|将来の情報\|データスヌーピング\|data snooping\|peek" docs/DATA/SCAN_2026-09-21_tools.md`)
の当たりは候補62 qf-lib(動かせた候補、この検討表には置かない)と、候補番号を特定できない
記述(SCAN 3166行、区分1-足系の候補)の2件のみだった。候補番号が無く検討表の行として引用
できないため、この観点の検討表は候補0件として扱う。

候補 0 件: `grep -n "先読み\|未来の情報\|将来の情報\|データスヌーピング\|data snooping\|peek" docs/DATA/SCAN_2026-09-21_tools.md`(候補番号を特定できた非導入候補が無い)

### 観点5(同時刻事象の決定的順序)

動かせた候補: 5 件(v5の場面固有ハンドラはこの周いずれも`no_record`。「まだ比べていない」として上で報告済み)。

| 候補 | 機構 | 実装(実装のコードで確かめたか) | 判断 | 理由と根拠 |
|---|---|---|---|---|
| 44 lo2cin4 | 契約スキーマ`"same_timestamp_lifecycle_order_is_data_derived_signal_order_fill"`(一次資料、SCAN 5890行) | いいえ | 再現できない | 危険リスト該当(委任文§4、道具台帳§3の11件)。導入も実行もしない。 |
| 101 akurkar07/OrderBook | 「deterministic tests」(SCAN 4881行)。実測(SCAN 5418行)では時間優先は決定的だが`timestamp`が実時計のため再現には順序依存 | いいえ | スキップ: 明らかに弱い | カタログ/SCANで確認できる根拠はテスト名の言及止まり(SCAN 4881行)で、実測(SCAN 5418行)は同時刻の複数事象型をまたぐ順序規則の明示的な保証を示していない。実際に再現した候補(62 qf-lib、動かせた候補として実行で確認済み)の`EventManager`(`queue.Queue`のFIFO、`dispatch_next_event`が型で振り分け)は構造上の決定性を持つ(§2の旧版該当行、round_check参照)。ゆえに上位互換。 |

## §3. 導入ログ(実際にscratchpad venvへ入れたもの)

| 候補 | venv | 結果 | ログ |
|---|---|---|---|
| Basana (id 1) | `<scratchpad>/bt/venvs/item_0/basana/`(python3.11) | 成功(basana 1.11) | `<scratchpad>/bt/venvs/item_0/basana_install.log` |
| Ziplime (id 6) | `<scratchpad>/bt/venvs/item_0/ziplime/`(python3.12。3.11では`Requires-Python>=3.12`で拒否された実測あり) | 成功(ziplime 1.19.16) | `<scratchpad>/bt/venvs/item_0/ziplime_install.log` |
| zipline-reloaded (id 18) | `<scratchpad>/bt/venvs/item_0/zipline-reloaded/`(python3.11) | 成功(zipline-reloaded 3.1.1) | `<scratchpad>/bt/venvs/item_0/zipline-reloaded_install.log` |
| PyBroker (id 4, PyPI名`lib-pybroker`) | `<scratchpad>/bt/venvs/item_0/lib-pybroker/` | 成功(lib-pybroker 2.0.1) | `<scratchpad>/bt/venvs/item_0/lib-pybroker_install.log` |
| qf-lib (id 62) | `<scratchpad>/bt/venvs/item_0/qf-lib/` | 成功(qf-lib 4.0.7) | `<scratchpad>/bt/venvs/item_0/qf-lib_install.log` |

**この回、Basana(id 1)を新規に導入した**(2026-09-23、場面係)。旧版は「言語がPythonでない(Go)」
として §3(未導入)に分類していたが、これは誤りだった -- `pip show basana` の実測どおり、Basana は
PyPI配布のPython(asyncio)パッケージ(Summary「A Python async and event driven framework for
algorithmic trading」、Author gabriel.becedillas@gmail.com、GitHub `gbeced/basana`)であり、
`python3 -m venv basana && ./basana/bin/pip install basana` で問題なく導入できた(実測、上表)。

安全の規則(委任文§4、道具サーベイ委任文§5・§6-1〜§6-4・§6-6): 5件とも PyPI の配布であり
`pip install` はPyPI公式インデックスのみを参照。実行はいずれも「import + hasattr/inspect +
引数無しの軽い呼び出し、または合成データのみを使った短い実行」に限り、外部ネットワークへの
送信・鍵の登録・支払いは一切行っていない(5アダプタのコードは `opponents/*.py` に全て残って
おり、何を呼んだかは各 `detail` 文字列に記録済み)。`basana` の `basana.backtesting.exchange`
は取引所クライアント(binance/bitstamp/ccxt)を持つが、このバッテリーでは `backtesting.*` の
合成イベント経路のみを使い、実弾の取引所クライアントは一切呼んでいない(§3導入ログの実測どおり)。

**この回、`61 barter-rs`(Rust製、`crates.io`APIは403でこのプロキシから到達不能。実測:
`curl https://crates.io/api/v1/crates/barter` → 403、2026-09-23再確認)について、
`raw.githubusercontent.com` は到達できる(実測: 200)ことを確認し、そこから2ファイルを取得して
`opponents/barter_rs_repro.py` を書いた**(規則9「再現は一次資料どおりの最小の書き直しで、
導入できないことは理由にならない」への対応)。取得した一次資料:
- `https://raw.githubusercontent.com/barter-rs/barter-rs/main/barter-data/src/subscription/liquidation.rs`(取得日2026-09-23)
- `https://raw.githubusercontent.com/barter-rs/barter-rs/main/barter-execution/src/error.rs`(取得日2026-09-23)

**未導入(試したが入れられなかった、または今回の時間予算内で試さなかったもの)**:
- **言語がPythonでない**(pip/venvの手順が成立しない、実クレート/バイナリとしては導入せず):
  ThePredictiveDev(id37, 言語未確認だがGitHub限定配布)・homerun(id91, GitHub限定)・
  barter-rs(id61, Rust。ただし清算/注文通知は`opponents/barter_rs_repro.py`で構造のみ再現)・
  gobacktest(id69, Go)・SarthakDalmia1/backtesting_execution_simulator(id33, C++)。
  crates.io APIはプロキシから403(実測、再確認)で、cargoでの導入検証も未実施。
- **PyPI未配布(GitHub限定のスクリプト集)**: Mendl-Labs/BacktestingCore(id15)・
  Qlib(id21, PyPI名`qlib`自体は到達可能だが依存が機械学習系で重量級と判断しこの周は見送り)・
  prediction-market-backtester(id92)・lob_bench(id119)・OpenMarket(id40)。
- **識別が未確定で誤同定の危険がある**: 候補11(索引名OctoBotだが台帳名`python3`)。同定できるまで導入しない。
- **危険リスト該当(委任文§4)**: 44・74・120・41・58・19・112・111・97・51・118 -- 導入も実行もしない(§1・§2の各表を参照)。

## §4. この周に見つけた `REQUIREMENTS.md` との食い違い・限界(リードへの報告事項)

1. **観点1・観点2-足・観点2-ティックで台帳の`段(機構)`/`段(既定)`列を使っていたのは誤りだった**
   (この回に訂正。根本原因は `ROOTCAUSE_1.md` b1-4)。`REQUIREMENTS.md`§3.2.1は既にこの2列が
   「区分1-市場影響と約定の模型」(項目3)専用と明記しており、`REQUIREMENTS.md`自体の記述は
   誤っていない。誤りは旧版のCONSIDERED.mdが観点1/足/ティックにこの列を流用したことにある。
2. **候補1 `Basana` の言語分類が誤っていた**(この回に訂正)。旧版「言語がGo」は誤りで、実際は
   PyPI配布のPythonパッケージ。導入し、観点1・観点2-足で実行による比較を実現した(§3)。
3. **観点2-板の差分の検討表が旧版に無かった**(この回に追加、§2)。項目0の8事象型の1つが
   検討表から漏れていた。
4. **観点2-板の待ち行列の表は項目0の観点(P0-1〜P0-7)に無い軸だったため削除した**
   (この回、範囲の訂正。`part_scope_note.md`参照)。`REQUIREMENTS.md`のP0-1〜P0-7自体は
   変えていない。
5. **観点4(ルックアヘッド)・観点5(同時刻順序)は、§3で導入した5候補全部についてこの周は
   比較できていない**(この回、qf-libの行も検討表からは削除した=b2-1。qf-libのEventManager
   のFIFO性とlook-ahead-bias試験モジュールの実在という実行結果自体は、観点5の候補101への
   「上位互換」判断の根拠として引用している=§1観点5参照)。**圧倒の判定にはこの10件
   (5候補×2観点)を「比較していない」と候補名を付けて報告する。**動的な実行にはstrategy
   オブジェクト/複数事象型の同時投入という足場が要り、この周の時間予算では作らなかった
   (実測ではなく設計判断であり、A-18=安全側に丸めてはいないつもりだが、「比較していない」
   という不明を、判定なしの陰性と混同しないよう、そのまま書く)。
6. **観点2-ティック(約定)の候補プールは、カタログの`ティック`列(高頻度/tick粒度データ対応)を
   流用したままだった**(§1参照)。この回、b2-3を受けてSCANを`約定/fill event/trade event`の
   語で直接grepし直し、旧`ティック`列プールに無かった候補69`gobacktest`を追加した(部分的な
   洗い直し)。残る候補(69・13・123を除く)については個別の一次資料裏付けの確認が
   この回のgrepの範囲では取れておらず、**未確認**のまま候補プールの全件洗い直しは次の周の
   宿題として残る(§1参照)。
7. **CONSIDERED.mdの§1・§2の全観点表が、実際に動かせた5候補(1 Basana・4 PyBroker・
   6 Ziplime・18 zipline-reloaded・62 qf-lib)自身の行を含んでいた**(この回、監査役b2-1で
   指摘され訂正。根本原因は`ROOTCAUSE_2.md`)。検討表に載るのは動かせなかった候補だけであり、
   動かせた候補の結果は資料係の比較表(`gen_round1_tables.py`)の側に置くべきだった。同根の
   欠陥として、`gen_round1_tables.py`の`_OPP_TARGETS`に`opp_basana`が漏れていたことも見つけ、
   直した(この回、`round1_opp_basana.tsv`を生成し直し、round_1の6表を再生成した)。
8. **b1-10で場面係が自分で答えた「観点2-板の待ち行列」削除の当否について**(監査役b2-2)、
   この回、判断そのものは取り消さないが、要件の解釈に関わる判断である以上、改めて
   下記「リードに聞くこと」に載せてリードの確認を仰ぐことにした(自己回答で完結させない)。

これらは場面係の権限では要件表(`REQUIREMENTS.md`)を書き換えず、検討表にのみ記録した
(委任文§3「要件と観点の誤りを直すのはリード」)。

## §5. リードに聞くこと(b2-2を受けて追加)

- **観点2-板の待ち行止行(板の待ち行列)を項目0の検討表から削除した判断(`ROOTCAUSE_1.md`
  b1-10で場面係が自答、この回`ROOTCAUSE_2.md` b2-2で自答の根拠を再検証)は、これでよいか。**
  場面係の見立ては「`REQUIREMENTS.md`のP0-1〜P0-7のどの観点にも板の待ち行列という軸が無い
  ため、削除は要件を緩めたのではなく検討表を要件に合わせて正しくした側」というものだが、
  検討表の族(観点)を丸ごと外す判断であり、委任文53行「対応表に無い判断」に当たる可能性を
  場面係自身は否定しきれない。取り消す/このまま進めるの判断をリードに仰ぐ。
- **観点2-ティック(約定)の候補プールの全件洗い直しは、この回は部分的(候補69の追加のみ)
  にしか行っていない。**残り候補の個別確認まで今周で行うべきか、次の周の宿題のままでよいか。

<!-- 集計ここから -->

## 集計(`scripts/check_bt_considered.py --write` が書く。手で直さない)

| 観点 | 動かせた | 動かせない(検討表の行) | 動かせない割合 | 再現した | 持たないと確認した | スキップ | 再現できない |
|---|---|---|---|---|---|---|---|
| 観点1: 事象駆動アーキテクチャ(19件) | 5 | 15 | 75% | 0 | 0 | 13 | 2 |
| 観点2-足(55件) | 5 | 50 | 91% | 0 | 0 | 43 | 7 |
| 観点2-ティック(約定)(19件) | 5 | 20 | 80% | 0 | 0 | 18 | 2 |
| 観点2-板の写真 | 5 | 0 | 0% | 0 | 0 | 0 | 0 |
| 観点2-板の差分 | 5 | 1 | 17% | 0 | 0 | 0 | 1 |
| 観点2-資金調達 | 5 | 2 | 29% | 0 | 0 | 0 | 2 |
| 観点2-清算 | 5 | 1 | 17% | 1 | 0 | 0 | 0 |
| 観点2-時計 | 5 | 1 | 17% | 0 | 0 | 0 | 1 |
| 観点2-注文の受付/拒否/約定の通知 | 5 | 3 | 38% | 1 | 0 | 0 | 2 |
| 観点3(時刻の精度) | 5 | 1 | 17% | 0 | 0 | 0 | 1 |
| 観点6(戦略API: 事象ごとの呼び出し・発注・取消) | 5 | 1 | 17% | 0 | 0 | 1 | 0 |
| 観点7(他項目の差し込み口: 約定模型・遅延模型・費用・口座) | 5 | 2 | 29% | 0 | 0 | 2 | 0 |
| 観点4(ルックアヘッド禁止の構造性) | 5 | 0 | 0% | 0 | 0 | 0 | 0 |
| 観点5(同時刻事象の決定的順序) | 5 | 2 | 29% | 0 | 0 | 1 | 1 |
| 計(観点ごとの延べ) | 70 | 99 | 59% | 2 | 0 | 78 | 19 |

再現もできなかった候補(圧倒の判定では「その候補とは比べていない」と候補名を付けて報告する):

- 観点1: 事象駆動アーキテクチャ(19件): 41 prediction-market-backtesting
- 観点1: 事象駆動アーキテクチャ(19件): 58 nautilus_trader
- 観点2-足(55件): 19 Jesse
- 観点2-足(55件): 44 lo2cin4
- 観点2-足(55件): 51 QUANTAXIS
- 観点2-足(55件): 58 nautilus_trader
- 観点2-足(55件): 74 ml-quant-trading
- 観点2-足(55件): 111 HKUDS/Vibe-Trading
- 観点2-足(55件): 120 wbt
- 観点2-ティック(約定)(19件): 41 prediction-market-backtesting
- 観点2-ティック(約定)(19件): 58 nautilus_trader
- 観点2-板の差分: 41 prediction-market-backtesting
- 観点2-資金調達: 40 OpenMarket
- 観点2-資金調達: 41 prediction-market-backtesting
- 観点2-時計: 11(索引名OctoBot、台帳名`python3`)
- 観点2-注文の受付/拒否/約定の通知: 58 nautilus_trader
- 観点2-注文の受付/拒否/約定の通知: 69 gobacktest
- 観点3(時刻の精度): 44 lo2cin4
- 観点5(同時刻事象の決定的順序): 44 lo2cin4

<!-- 集計ここまで -->
