# カード 1 の独立の書き直しの検め(W4 の仕様 §2 の 5)

- 目的: 別の下位モデルが、原文(bot のコード `src/bot/strategy/xborder_momentum.py`・`config/config.yaml`・段 7 の設計 §5-1)だけから、カード 1 を独立に書き直す。本番のカード `src/bot/research/cards/library/c1_xborder_mom.py` の `XborderMom` と、持ち高を足ごとに突き合わせる。
- 基準(W4 の仕様 §2 の 5): 持ち高が食い違う足が全体の 0.1% を超えたら、または食い違いの理由を 1 件でも説明できなければ止める。
- 書き直した作業者は、カード 1 の文書・関数・試験を読んでいない。例外は 1 行だけで、読み込みの失敗のトレースバックに `c1_xborder_mom.py` の 77 行 `@dataclass(frozen=True)` が出た(作業者の申告)。
- 入力は封印の門(`bot.bt.data` の `load` / `load_reference`)を通して読んだ。期間は 2017-08-17T15:00:00Z〜2023-12-17T15:00:00Z。参照は Binance BTCUSDT の 1 分足の close(行の時刻は open_time、lag 60 秒)。

## 結果【事実: `full_run.log`・`full_result.json`】

- 足 3,252,366 本。両方が持ち高を取った足は 3,251,352 本。
- **食い違った足は 0 本(0.000000%)**。型(持ち越し・履歴の門・Binance の抜け・bitFlyer の抜け・境の等号・その他)はどれも 0 件。基準には当たらない。
- 差の 1,014 本は空の足(volume 0)で、run.py は空の足では持ち高を取らない。lightchart の README の「close があって volume が 0.0 の行 1,014 行」と数が同じ【数は事実、同じ行かは推定】。
- 0 件が「両方ずっと 0」のせいでないことの確かめ(2022-06 の 1 か月、両方とも同じ): 足 42,720、+1 が 6,498、−1 が 7,787、0 が 28,435、持ち高が変わった回数 792。
- 型を分ける仕組みは、本物のデータでは一度も働いていない(食い違いが 0 のため)。働いたのは合成の試験の中だけ。

## 書き直した側の解釈(本番のカードと独立に決めたもの)

1. 「k 本前」は時刻で数える(k 分前)。
2. Binance の行が抜けたら 2 分前まで遡る(bot の `close_for(max_age_intervals=2)`)。
3. 境の等号は原文のまま: `mom > thr` で BUY、`mom < -thr` で SELL、`abs(mom) <= exit` で CLOSE。
4. 履歴の門は k+2 本。
5. HOLD は前の持ち高のまま。最初は 0。
6. 既定の値は稼働中の設定(k=30・thr 0.8%・exit 0.05%)。

## 経緯の記録

- 書き直した作業者は、全期間の計算の途中、自分の返答の中に通知が来たかのように偽の年ごとの行を書き、直後に取り消した(作業者の申告)。上の数字はすべてログのファイルから取った。リードがオーナーに途中で伝えた年ごとの数は、リードが `full_run.log` を直接読んだもの。
- 暦年ごとに区切って走らせた(記憶 15GB のため)。最初の区切り以外は 1 日前から慣らした。

## ファイル

`rewrite_card.py`(書き直したカード)・`test_rewrite_card.py`(16 passed)・`compare.py`(突き合わせの台本)・`full_run.log`・`full_result.json`。
コマンド: `PYTHONPATH=src python docs/RESEARCH/cards/c1_xborder_mom/rewrite_check/compare.py --other-module src/bot/research/cards/library/c1_xborder_mom.py --other-class XborderMom --start 2017-08-17T15:00:00Z --end 2023-12-17T15:00:00Z --out full_result.json`(所要 1,835 秒)
