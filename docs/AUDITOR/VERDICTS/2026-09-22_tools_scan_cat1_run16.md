# 区分 1 の 16 回目の報告 — リードの検収

対象: `docs/DATA/SCAN_2026-09-21_tools.md` の「## 区分1 — 16 回目の実行(2026-09-22)」(5009 行目以降、344 行)
生ログ: `docs/DATA/probes/20260922_tools_1_run16.log`(新規。復帰文字 0 個)

## 0. 無改変・検査

既存の 5008 行は **無改変**。生ログ 14 本を渡して打ち直し、**13 本すべて 0 件**(3 回連続で最初から 0 件)。閉じ残し 0 件。

## 1. この回の最大の成果 — **当方の模型の楽観を、外から測れる道具が見つかった**

**当方の `src/bot/backtest/engine.py:45-53` の逐語**(リードが読み直した。報告より長く引く):

> 1m-bar approximation (**optimistic, stated for the record**): on a 1-minute bar we only know that the level
> traded through somewhere inside the minute, not that our specific resting order was reached in the queue …
> **Real fills also depend on queue position; this model grants the fill on any strict through-trade.**
> **Treat maker-TP results as an upper bound, not a promise.**

**候補 95 `sacha9214/polymarket-fill-model` は、まさにこの差を測る道具である。**
リードが README を取り直して確認した逐語:

- 「**Would my resting order actually have been filled?** A queue-aware fill model」
- 「A fill simulator that tracks **queue position** at the best bid and consumes it with the **real trade tape**」
- 「**Cancellations ahead of us are invisible**, so we never move up the queue」(自分で限界を書いている)
- **楽観の大きさを金額で出している**: 「Optimistic — I move up the queue whenever it shortens | **+28.51 $/day** | too optimistic」

**調査班の実測**: 同じ合成の板・同じ合成の約定列で、**待ち行列を数えると埋まり 1 件、数えないと 2 件。**
`ignore_queue=True` が**当方の模型と同じ立場**である。

**これは区分 1 で最も当方に効く発見である。**当方の engine が「上限であって約束ではない」と自分で書いている
その上限の大きさを、外の実装で測れる。

## 2. リードが取り直したその他 — **一致**

| 主張 | 取り直した結果 |
|---|---|
| PyPI の `slippage` は候補 105 とは別物 | **一致。**版 0.0.1、summary が「slippage - Coming soon.」、`project_urls` が `null`。**`pip install slippage` ではこの道具は入らない** |

## 3. 確定した状態(14 件)

**最小実行まで通した 4 件**: 95(待ち行列を数える)/ 98(取り消しが位置を保つ。IOC・FOK・STP・遅延も同じ経路)/
99(先行の 50 枚が先に食われ当方の 10 枚が残る)/ 105(市場影響。**一時と恒久を分ける**。線形・べき乗則・平方根則の 3 本立て)。
**危険で止めた 2 件**: 100(**構築済みバイナリ 2 本を同梱**)/ 106(**許諾の食い違い + 配布元の一致が取れない**)。
**別物だった 1 件**: 96(104 の複製。sha が同じファイル 68 本)。**浅い 7 件。**

**105 の市場影響の逐語**: 恒久 `gamma`「Permanent impact, in price per share.」/ 一時 `eta`「Temporary impact,
in price per (share per unit time).」。**較正が効かないと言う経路も持つ**(「exponent standard error 0.84 exceeds
0.25; the data cannot distinguish a square-root law from a linear one」)。**「分からない」を出力できる道具は珍しい。**

**隠し玉は 95・98・99 のどれも持たない。**当方に無いのは「先行注文量」であって「隠し玉」ではないことが確定した。

## 4. 安全の所見(調査班の 4 件。リードも同意)

1. **候補 100 は構築済みバイナリを同梱** → §6-1 で止めた。正しい。
2. **候補 96 は 104 の複製で、上流の 104 に `LICENSE` が無く、複製の側が足している。**
   96 の README が自分でそう書いている(「Preserve the upstream license/attribution when redistributing.」)。
   **上流に許諾が無いものに複製が許諾を足す形**は、再配布の条件が不確かなので、どちらも導入しないのが正しい。
3. **98・99 は許諾の記載が無い**(`LICENSE` も README の語も無し、grep rc=1)。**最小実行は通したが、使うなら条件が不明。**
4. **候補 97 の配布物に作業者向けの指示の文章が同梱。**ファイル名の逐語が
   `attached_assets/Pasted-Extend-the-existing-file-to-add-a-LIVE-market-data-mode_....txt` で、**ファイル名自体が命令形**。
   §6-3 のとおり従わず、**本文も取らなかった。**→ **正しい。**「従わない」の最も安全な形である。

## 5. 調査班が渡してきた判断への回答

1. **K11 のために `rc=` の行を根拠に置き、元の行番号を括弧で併記した → 受け入れる。**
   生ログは打った手をそのまま記録しており、元の行も読み手に届く。**打ち直した実行の記録であって、後付けの書き足しではない。**
   **ただし、検査が書き方を動かしている例であることは記録しておく。**受け皿はリードの抜き取りである。
2. **難読化の検査の当たり 1 件を閉じずに残した → リードが閉じる。誤検出である。**
   正規表現の `compile` が語に当たっただけで難読化ではない。**自分で閉じなかったのは正しい扱い。**
3. **候補 97 の指示の本文を取らなかった → 正しい。**§6-3 は「従わない」だが、**取らないほうが安全**である。以後もそうする。
4. **C++ の 6 件を構築しなかった → 次の回で構築してよい。**ただし条件を付ける:
   **§6-1 の検査を先に通す / `time` で測る / 1 件が 5 分を超えたら止めて「時間を超えた」と書く。**
   「できない」と書かなかったのは正しい。

## 6. 6 要素の残り

足 16 / ティック 2 / **板の待ち行列 8**(11 → 8)/ イベント駆動 8 / ベクトル化 3 / **市場影響と約定の模型 2**(4 → 2)。
**区分 1 は未完了。**この回は検索計画を打っていないので新しい候補は 0 件。
