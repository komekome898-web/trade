# 未計測・非推奨定数の一覧と計測計画(DATA_QA_CHECKLIST item 8)

`config/constants.yaml` のうち `source_type: assumed`(`deprecated: true` を含む)または `value: null` の定数を列挙する。`src/bot/constants.py: require_source()` がこれらを判断に使おうとすると例外を出す(既定の仕組み)ので、下表はその対象一覧と、各々をいつ・どう実測できるかの計画。

生成日時(UTC): 2026-09-05T14:05:19.095276+00:00

## 一覧

| 定数 (group.name) | 現在値 | 単位 | source_type | deprecated | 参照元 (consumers) |
|---|---|---|---|---|---|
| `bitflyer_fx_btc_jpy.taker_round_trip_floor_bps_OLD` | [5.8, 7.9] | bps | assumed | True | `scripts/qa/pipeline_known_answer_taker.py` |
| `gmo_fx_usdjpy.fee_yen` | 0 | yen_per_trade | assumed | False | (参照箇所なし) |
| `gmo_fx_usdjpy.spread_sen` | 0.2 | sen (1/100 yen) | assumed | False | (参照箇所なし) |
| `jpx_cash_equity.etf_spread_bps` | None | bps | assumed | False | (参照箇所なし) |

## 各定数の計測計画

### `bitflyer_fx_btc_jpy.taker_round_trip_floor_bps_OLD`

- フラグ理由: assumed, deprecated
- 何を計測するか: 何も新規計測しない — この定数は廃止済み(deprecated)。後継値も 2026-09-08 の全捨てで失効した。**コストは新しい単位ごとに測り直す**。
- どのスクリプトで: 対応不要。使用箇所(`scripts/qa/pipeline_known_answer_taker.py`)は `require_source` がこの定数で例外を出すことを確認するテストであり、実際の値を消費してはいない。
- いつ可能か: 対応不要(既に測定済みの後継値に置き換え済み)。
- 定数側の notes: (旧記述は 2026-09-08 に削除。この定数は未計測として扱う)

### `gmo_fx_usdjpy.fee_yen`

- フラグ理由: assumed
- 何を計測するか: GMO ブランドの USDJPY FX の取引手数料(円/回)を一次資料から確認する(現在値 0 円はリテール FX の慣習からの仮定で、この銘柄固有の確認はしていない)。
- どのスクリプトで: 計測スクリプトではなく一次資料の確認作業。spread_sen と同じ疎通の壁に当たる。
- いつ可能か: spread_sen と同時に一次資料ページへ到達できた時点で確認可能。この定数も現在どの判断にも消費されていない。
- 定数側の notes: (旧記述は 2026-09-08 に削除。この定数は未計測として扱う)

### `gmo_fx_usdjpy.spread_sen`

- フラグ理由: assumed
- 何を計測するか: GMO ブランドの USDJPY FX スプレッド(sen 単位)を一次資料(公式手数料/スプレッドページ)から確認する。現在の値は過去の研究メモから引いた未確認の丸め数値。
- どのスクリプトで: 計測スクリプトではなく一次資料の確認作業。このセッションでは gmo-fx.jp への疎通が壁(プロキシ経由の TLS CONNECT 失敗)で確認できず、coin.z.com のページはクライアント側 JS 描画でスプレッド表を静的取得できなかった(`source_url`/`verified_on` 欄に記録済み)。ブラウザ経由の目視確認、または別ネットワークからの再取得が必要。
- いつ可能か: エグレス制限が無い環境(オーナー PC 等)で一次資料ページを開いた時点で可能。この定数は現在どの判断にも消費されていない(下表の consumers 参照)ため緊急度は低い。
- 定数側の notes: (旧記述は 2026-09-08 に削除。この定数は未計測として扱う)

### `jpx_cash_equity.etf_spread_bps`

- フラグ理由: assumed, null
- 何を計測するか: JPX 上場 ETF(1321/1306/1343/1591/2516 等、`config/on1_live.yaml` 対象銘柄)の板スプレッド(bps)を、kabuステーション PUSH 配信の板データから実測する。
- どのスクリプトで: 現在この値を録る録画スクリプトが存在しない(`notes` 参照)。`src/bot/jpx/kabu_client.py` の PUSH 配信を使い、`scripts/record_oi.py`(bitFlyer 側)と同種の録画スクリプトを新規作成する必要がある(例: `scripts/record_jpx_board.py`)。
- いつ可能か: kabuステーション API の板 PUSH 配信を受けられる時間帯(取引時間中)に、対象 ETF 全銘柄で複数日録れば実測可能。ON1 の発注前サニティに使う定数のため、ON1 実弾投入前に計測を完了させることが望ましい。
- 定数側の notes: (旧記述は 2026-09-08 に削除。この定数は未計測として扱う)

## 備考

- `require_source()` により、上記定数は明示的なキャッチなしでは判断(発注前チェック・バックテスト・レポートの結論)に使えない仕組みになっている(item 8 の「判定に使われない仕組み」)。
- 本書は `scripts/constants_inventory.py` の出力であり、手で数値を書き換えない。再生成すれば常に最新の consumers 一覧が反映される。
