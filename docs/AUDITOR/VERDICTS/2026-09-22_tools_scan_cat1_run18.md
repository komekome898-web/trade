# 区分 1 の 18 回目 — リードの検収(2026-09-22)

対象: `docs/DATA/SCAN_2026-09-21_tools.md` の「区分1 — 18 回目の実行」節(169 行追加)/ 生ログ `docs/DATA/probes/20260922_tools_1_run18.log`
委任文: `docs/DATA/delegations/20260922_tools_survey_prompt.md@ce0012c95154`

## 1. 既存の節が書き換わっていないか(機械)

`git diff --numstat` = **172 行追加 / 3 行削除**。削除の 3 行は全部出した:

```
-2. [深掘り] `3yit/Limit-Order-Book-Simulator`(102 番) — 状態: **構築して動かした。C++ と Python の両方。**
-   C++ の構築 24.98 秒、Python の束縛の構築 14.05 秒(ただし `-DCMAKE_POSITION_INDEPENDENT_CODE=ON` を足した後)。
-4. [深掘り] `jxm35/LimitOrderBook-MatchingEngine`(104 番) — 状態: **`lib/OrderBook` の範囲で構築して動かした。**構築 2.12 秒 + 最小実行 3.78 秒。
```

差分の塊は 3 つで、うち 2 つが 5587〜5592 行(17 回目の節 = 起動の指定が許した 2 箇所)、
残り 1 つが 5654 行からの追加(18 回目の節)。**許した 2 箇所以外は 1 文字も動いていない。判定: 合。**

## 2. 受け入れ検査(機械)

```
$ python3 scripts/check_scan_report.py docs/DATA/SCAN_2026-09-21_tools.md docs/DATA/probes/20260922_tools_1_run*.log
K1 太字 0 / K2 括弧 0 / K3 必須の節 0 / K4 生ログに無い数値 0 / K5 同じ道具に別の値 0 / K6 未実施と実測の同居 0
K7 表の項目の欠落 0 / K8 表の印と根拠 0 / K9 表に無い数値 0 / K10 見出しの件数 0 / K11 実測の根拠 0
K13 中身が実質空 0 / K12 検査の出力の貼付 0
---- 合計 0 件
```

生ログは 17 本すべて渡した(`ls docs/DATA/probes/20260922_tools_1_run*.log | wc -l` = 17)。**判定: 合。**

## 3. 中身の抜き取り(リードが原典を自分で打ち直した)

一次資料 5 行・実測 3 行・「無い / できない」の主張を全部。

| 検めた主張 | リードが打ったもの | 結果 |
|---|---|---|
| 知見 9・10(候補 63 `trade-frame` の 3 要素と「板の列ではない」) | `SimulateOrderExecution.hpp` を取得(145 行)。`m_dtQueueDelay`「used to simulate network / handling delays」・`m_lOrderDelay`「all orders put in delay queue, taken out then processed as limit or market or stop」・`SetOrderDelay`・`CalculateCommission`・`ProcessDelayQueue`・`ProcessLimitOrders( const Quote& )` / `( const Trade& )` を確認。`position` の語は 0 件 | **当たり** |
| 知見 15(候補 80 `Hummingbot` の既定が 1 分・ベクトル化ではない) | 原典を取得(727 行)。`backtesting_resolution: str = "1m"`(224 行)・`interval=self.backtesting_resolution`(263・458 行)・`for i, row in processed_features.iterrows():`(282 行)・`backtesting_candles["reference_price"] = backtesting_candles["close_bt"]`(462 行) | **当たり** |
| 知見 16(候補 85 の検証の本体が別の配布物) | `czsc/traders/__init__.py` を取得(53 行)。`from wbt import WeightBacktest`(28 行)・`from czsc._native import (`(30 行)・「`WeightBacktest` ：从外部 `wbt` 包再次导出」(13 行)・「均来自 `czsc._native`（Rust 扩展）」(12 行) | **当たり** |
| 知見 20(候補 95 の粒度が約定 1 本) | README を取得。「A queue-aware fill model」(3 行)・「tracks **queue position** at the best bid and consumes it with the **real trade tape**」(23 行) | **当たり** |
| 知見 21・22(候補 119 `LOB-Bench`) | README を取得(159 行)。「Ready‑made score functions, distance metrics, and impact‑response analysis.」(21 行)・「Works out‑of‑the‑box with LOBSTER CSVs, yet fully extensible.」(22 行)・`pip install lob_bench`(74 行)・「Requires Python ≥ 3.9 plus `numpy`, `pandas`, `scipy`, `matplotlib`.」(76 行)・「Impact‑Response Evaluation」(見出し) | **当たり** |
| 知見 19(候補 86 の README が git-lfs の指し先) | `candlestick-patterns/README.md` を取得 → 「version https://git-lfs.github.com/spec/v1」「oid sha256:b18bb5d9…」「size 258」。**本文ではなく指し先である**ことを別の経路で再現 | **当たり**(報告の oid・size は別の README のもの。どちらも指し先) |
| 知見 12(候補 64 `QuantFabric` が検証の実装を持たない) | 既定枝を `ungh.cc` で確認(`"defaultBranch":"master"`)→ `master` の README(17,711 バイト)を取得 → `回测\|backtest\|模拟\|simulat` の当たり **0 件** | **当たり** |
| 知見 6(候補 49 の 4 経路が塞がっている) | `/backtest` → **404**、`/backtesting` → **404**、`backtest.goatfundedtrader.com` → **000**。当方でも同じ | **当たり** |
| 知見 25(許諾の有無) | `ungh.cc` の追跡ファイル一覧を自分で叩いた。zvt = `LICENSE` 在り / QuantFabric = `LICENSE` 在り / PandoraTrader = **無し** / lob_bench = **無し** / trade-frame = `LICENSE.txt`(報告どおり別名) | **当たり**(Hummingbot は当方の取得が時間切れ。生ログの取得で代える) |

**リード自身の誤りを 2 件出す**(調査班の誤りではない):
1. 候補 64 を検めるとき、既定枝を確かめずに `main` を叩いて 404 / 14 バイトを受け取り、「README が空だ」と一度読み違えた。
   **既定枝は `master`。**「`code=000` を 404 と同じに扱った」(14 回目)と同じ型を、今度はリードがやった。
2. 候補 119 の逐語 3 つが当たらないので「逐語が原典に無い」と一度読んだが、原典が**非分割ハイフン `‑`(U+2011)**を
   使っているのが原因で、当方の検索が半角 `-` だった。**逐語は原典どおりである。**

→ 19 回目への申し送り: **原典が `‑`(U+2011)などの字形違いを使っている箇所は、報告にその旨を 1 行添える。**
読む側が半角で検索して当たらず、逐語の捏造を疑う(当方が実際にそうなった)。

## 4. 調査班が挙げた 5 件の判断 — リードの回答

**(1) 候補 64・66・71 から `判別に一次資料が要る` を外し、`区分2 へ` だけを残してよいか → よい。**
この印は「決めるのに一次資料が要る」という**係属の印**であって、分類の印ではない。一次資料に到達して決まった以上、
残すほうが「まだ決まっていない」という嘘になる。**外すのが正しい。**

**(2) 候補 49 `GFT Backtest Software` を到達不能で閉じるか、オーナー PC の経路として残すか → どちらでもない。**
塞いでいるのは**地域でも環境でもなく、登録という関門**である。オーナー PC に移しても同じ関門が立つので、
「オーナー PC の経路」と書くのは**関門の性質を言い換えて先送りするだけ**になる。書くべき状態は:

> **登録の内側にあり、当方は登録しない。したがって区分 1 の 6 要素は 6 つとも未確認のままである。**

**印は付けない。「該当しない」とも書かない**(調べずに「無い」と断定しないこと = §0.2 O-2)。
登録するかはオーナーが決めることなので、**区分 1 の完了報告に「オーナーの判断が要る 1 件」として名指しで出す。**
案 A'(オーナー逐語「**一次資料に到達した候補が尽きること**」)に照らすと、この 1 件は**到達できていない**ので、
完了の報告で黙って数に入れてはならない。`docs/NEGATIVE_FACTS.md` にも範囲と方法つきで登録する。

**(3) 候補 63 に印を 3 つ付けてよいか → よい。上限は無い。**
委任文 §2 は「またがるものは両方に書く」であって件数を縛っていない。3 要素それぞれに別の逐語が出ている。
**むしろこの回で一番重い成果である。**理由: `trade-frame` は**自分の注文の遅延の列**(`m_dtQueueDelay`、50〜100ms)を持つが
**価格帯の先行注文の列は持たない**。候補 104 の `queuePosition`(先行注文の列)と、候補 95 の「約定の列で食わせる」とで、
**指値の埋まり方の模型が 3 つとも別の立て方**であることが揃った。当方の `engine.py:45-53` が自ら「楽観的」と書いている
「通り抜けた約定でいつでも埋まる」は、この 3 つのどれとも違う 4 つ目である。**この対比は区分 1 の主目的そのもの。**

**(4) 候補 85 `czsc` に区分 1 の印を付けてよいか → 付けてよい。ただし `wbt` を別の候補として立てる。**
疑いの筋は正しい。検証の本体が `wbt` に在るなら、**区分 1 の要素を実装しているのは `wbt` のほうである。**
`czsc` の印(`区分1-足`)は、`BarGenerator(base_freq='1分钟', …)` が `czsc` 側の逐語なので残す。
**`wbt` を 120 番として立て、区分 1 の一次資料はそちらで取る。**これは範囲の拡大ではなく、
「要素を実装しているものに印を付ける」という §2 の当て方どおり。
「取り込むものが変わりうる型」(§6-1)の所見は**そのまま残す** — 使う段でオーナーに出す。

**(5) 番号を 118+1 = 119 にしたこと → よい。**現に使っている採番規則そのもの。

## 5. 判定

**受け取る。**機械の検査 13 本が 0 件、既存の節は許した 2 箇所以外不変、抜き取りは 9 件とも原典に当たった。
「無い / できない」の主張は 4 件とも当方が打ち直して再現した。**差し戻す点は無い。**

## 6. 19 回目の起動の指定

1. **最優先: `区分1-ベクトル化` の 3 件(73・74・44)。**18 回目の起動の指定 (4) が未着手のまま残っている。
2. **`wbt` を 120 番として立て、一次資料を取る**(上の (4))。`czsc` の節は書き換えない。
3. 余力があれば `区分1-市場影響と約定の模型` の残り(106・116)。**`区分1-足` の 23 件には手を付けない**(最後に回す)。
4. **新しい検索計画は打たない。**候補を増やすのは (2) の 1 件だけ。
5. 候補 49 は**触らない。**上の (2) の書き方に直す 1 箇所だけ、既存の節への書き換えを許す。
6. 原典の字形違い(`‑` など)を使った逐語には、その旨を 1 行添える(上の §3)。
