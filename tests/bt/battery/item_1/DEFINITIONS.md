# 項目 1「データと時刻」— 場面集の定義

場面係が作り、作業者の 1 周目の前に固定する(委任文 §3「場面集」「場面集の規則」1〜9)。固定した要件は
`docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/REQUIREMENTS.md`(観点 V1〜V7)。この文書の「場面」の節は
`gen_definitions.py` が `i1_scenes.py` から書く(場面の中身と文書が食い違わないため。手で直さない)。

## 1. 場面の 2 種類

- **値の場面**: 合成の入力と、エンジンを見ずに決めた正解(手計算・閉じた式・定義どおりの素朴な数え)で、その値が正しいかを見る。
  正解の出し方は場面ごとの「正解の出し方」に書く。
- **能力の場面**: X ができるかを、X を使ったときに出るはずの結果(正解)で見る(規則 1)。「持っている」という申告・型や名前の有無は数えない。
- どの観点にも値の場面を 1 つ以上置く(規則 3)。場面は振る舞いを見て、作りの形を見ない(規則 2)。

## 2. 入力の形(adapter が受け取るもの)

`op` で 3 つに分かれる。runner は場面ごと・実行ごとに新しいフォルダ(`root`)を作り、`files` をそこに書き、`root` を足して渡す。

- `op = "load"`(V1〜V5): `files`(`path` = root からの相対パス、`text`、`gzip`(mtime 0 で圧縮)、または `symlink_to`)、
  `datasets`(`name`・`paths`(1 つのデータを成すファイル。2 本なら世代)・`spec`・任意の `range_ns` = [始まり, 終わり) の読む範囲)、
  `want`(`events` = 全部の欄 / `times` = 時刻の欄だけを判定 / `anomalies` / `hashes`)。
  `spec` = データの宣言: `format`(csv / jsonl = 1 行 1 つの JSON。jsonl の列の名は入れ子を . でつないだ道 = 例 raw.o.T)・`header`(見出しの有無。無ければ `names`)・`delimiter`・`compression`・
  `kind`(trade / quote / bar / book / funding / liquidation。book の `fields` は段ごとの列の名の列と `levels`)・`symbol`・`asset`・`time`(`columns` = 時刻の列(2 列なら `join` で合わせる)、
  `unit` = s / ms / us / ns / iso、`tz` = オフセットの無い時刻の時間帯)・`fields`(共通の欄 → 列の名)・`side_map`(列の値 → buy / sell / "")・
  `bar`(`interval_s`・`label` = 足の時刻は始まり・`session` = 24x7)・`key`(重複と食い違いのキー。id または足の始まり)。
- `op = "jpx"`(V6): `bars`(code・date・open・high・low・close・volume の日足)・`actions`(split / reverse_split の `ratio` と `ex_date`、
  code_change の `new_code` と `ex_date`)・`listings`(code・listed・delisted = 上場でなくなる最初の日、無しは null)・`as_of`・`universe_dates`。
- `op = "vector_vs_event"`(V7): `trades`(t_ns・px・qty・side・id)または `bars`(start_ns・OHLCV)・`interval_s`・`rule`・`want`。

adapter の決まり(`i1_protocol.py`): ファイルはパスで対象に渡し、spec を対象の公開の選択肢に置き換える。adapter はデータのファイルを
自分で開かない・解釈しない・書き換えない。対象が出さなかった値を計算しない。正解を読まない。場面の id で分けない。
構造化された入力(V6・V7)は、対象の API が取る入れ物(DataFrame・対象の事象の型)に入れ替えてよい(入れ物の変更で、計算ではない)。

## 3. 観測の形と判定の決まり(`i1_judge.py`)

記録: 約定 = t_ns・px・qty・side・id(文字列)/ 気配 = t_ns・bid・ask・bid_qty・ask_qty / 足 = start_ns・open・high・low・close・volume /
板の写真 = t_ns・bids・asks(良い段から [値段, 数量] の列。空欄の段は載せない)/ 資金調達 = t_ns・rate / 清算 = t_ns・px・qty・side。
時刻の欄は int(ナノ秒、UTC)でなければならない(float の時刻は不一致)。

- `events`: データごとに、同じ件数・同じ順で、正解の記録が名指す欄が全部一致する(整数と文字列は完全一致、浮動小数は完全一致。場面が `tol` を持てば相対の差 ≤ tol)。
- `anomalies`: データごとに (種類, 時刻) の多重集合が一致する。種類と時刻の定義:
  - `duplicate` = spec の `key` が同じで、全部の列が同じ行(時刻 = その行の時刻)。
  - `conflict` = `key` が同じで、値が違う行(時刻 = その行の時刻)。
  - `backward` = その行の時刻 < それより前の行の時刻の最大(時刻 = その行の時刻)。
  - `gap` = 足の間隔の格子で、最初の足と最後の足の間に行の無い始まりの時刻 1 つにつき 1 件(24x7)。
  異常の種類の一部しか持たない対象は、持つ種類の結果をそのまま返す(持たない種類を黙って見落とすと不一致になる =「黙って結合しない」)。
  異常を報せる口が全く無い対象は `anomalies` を返さない(= 不一致。口が無いことを adapter が名指せば「結果なし」)。
- `hashes`: 正解の全部のパスについて、ディスクに書いたバイト列(gzip は圧縮したままのバイト列)の sha256 が一致する。
- `adjusted`: 銘柄の集合が一致し、銘柄ごとに `events` と同じ決まり。`universe`: 日付ごとに銘柄の集合が一致する。
- `paths`: 事象駆動(`event`)と近道(`vector`)の両方が正解の全部の欄を持ち、それぞれが正解と一致し、**2 つの経路がビット単位で一致する**。
- `speed`: 名指す欄で 2 つの経路がビット単位で一致し、`timing.vector_s < timing.event_s`(adapter が両経路の呼び出しの前後で測った壁時計の秒)。
- 変形(`variant`)を持つ場面(V5): 対照が正解と一致し、かつ変形を対象が拒んだときだけ「正解と一致」。変形を拒まずに読めば「不一致」。

表のセル(資料係が作る): **正しさ** = 正解と一致 / 対応なし(対象が明示的に拒んだ・例外を出した)/ 不一致(黙って違う値を返した)/ 結果なし(走らせられず、結果が 1 つも無い。理由を注記に書く)。
**再現** = 2 回の実行で同じ(正しさの分類と観測の要約(時刻の秒を除く)が 2 回とも同じ)/ 2 回で違う(値)/ 結果なし。
runner は同じ場面を別のプロセスで 2 回走らせ、両方を記録する。

**「最も良い結果」の順**(規則 5): 正解と一致 > 対応なし > 不一致 > 結果なし。正しさが同じなら、2 回の実行で同じ を上に置く。

## 4. V7 の規則

- 足の作り方: 足 = [始まり, 始まり + interval) の約定。始値 = 最初、高値 = 最大、安値 = 最小、終値 = 最後、出来高 = 数量の和。約定の無い区間は足を作らない。
- 規則 `sma_long_flat`(n, init_cash, unit): sma_t = 直近 n 本の終値の平均(n 本に満たない足は無し = null)。
  position_t = unit(終値_t > sma_t のとき)/ 0。position_t は足 t の終値で決まり、足 t+1 の間持つ。費用なし。
  equity_t = init_cash + Σ_{s ≤ t} position_{s-1} × (終値_s − 終値_{s-1})。
- 規則(戦略)は adapter が対象の事象駆動の API と近道の API の上に書く(規則は戦略で、どの対象でも利用者の符号)。

## 5. 対象(表の行になるもの)

- 新実装 = `adapters/new_impl.py`(**口だけ**。本体は資料係が毎周、新実装の公開の API だけを呼んで書く)。
- 調査結果の側 = 要件のファイル §3 が名を挙げた候補のうち、隔離した venv で動いたものと、動かせない候補の再現(`opponents/`。一覧は `i1_targets.py`、
  導入の記録は `opponents/RUNNABILITY.tsv`、動かせない候補の検討は `opponents/CONSIDERED.md`)。場面ごとに、動いた対象のうち最も良い結果を 1 行に寄せる。
- 試金石 = `mutant.py`(新実装を包み、1 か所だけ誤らせる。何を誤らせたかは `mutant.py` の MUTANT)。

## 6. 場面にしていない・射程の外

- 要件のファイル §2 の射程外(執行の模型・検証の統計・実行記録の形そのもの)はこの場面集で測らない。V4 は「読んだファイルの sha256 を対象が記録して返すか」を見る(記録の置き場の形は項目 3)。
- 実データは使わない(全部合成)。JPX 個別株の分割・併合・上場廃止・コード変更は合成のデータだけで測る(この環境で JPX 個別株の調整の実データを探した方法と結果は要件のファイル §4)。
- V7 の速さは壁時計の比べなので、2 回の実行で分類が変わりうる(変われば「2 回で違う」と記録する)。

## 7. 場面(観点ごと)

### V1 全資産の読み込み(9 場面: 値 7・能力 2)

#### `v1-bitflyer-rest`(値の場面)
- 何を測るか: bitFlyer の約定(REST の形: id,exec_date(Z なしの ISO、UTC),price,size,side。side が空の行を含む)を約定の事象にできるか
- 入力:
  - `backtest_data/bf_exec_synth_20260105/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_synth_20260105/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 期待: `{"events": {"bf_rest": [{"t_ns": 1767571200100000000, "px": 15000000.0, "qty": 0.01, "side": "buy", "id": "2900000001"}, {"t_ns": 1767571200250000000, "px": 15000005.0, "qty": 0.02, "side": "sell", "id": "2900000002"}, {"t_ns": 1767571201000000000, "px": 15000010.0, "qty": 0.5, "side": "", "id": "2900000003"}, {"t_ns": 1767571201999000000, "px": 14999995.5, "qty": 0.001, "side": "sell", "id": "2900000004"}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。

#### `v1-bitflyer-us-gz`(値の場面)
- 何を測るか: bitFlyer の約定(統合版の形: id,ts_us(マイクロ秒),side,price,size,source、gzip、id が空の行を含む)を約定の事象にできるか
- 入力:
  - `backtest_data/bf_exec_us_synth_20260105/executions_20260105.csv.gz`(gzip)(4 行):
    ```
    id,ts_us,side,price,size,source
    2900000010,1767571205000000,BUY,15000000,0.01,rest
    ,1767571205000500,SELL,15000001,0.25,ws
    2900000011,1767571206999999,BUY,15000002.5,1.5,rest
    ```
  - データ `bf_us`: paths = ['backtest_data/bf_exec_us_synth_20260105/executions_20260105.csv.gz']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["ts_us"], "unit": "us", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id", "compression": "gzip"}`
  - want = ['events']
- 期待: `{"events": {"bf_us": [{"t_ns": 1767571205000000000, "px": 15000000.0, "qty": 0.01, "side": "buy", "id": "2900000010"}, {"t_ns": 1767571205000500000, "px": 15000001.0, "qty": 0.25, "side": "sell", "id": ""}, {"t_ns": 1767571206999999000, "px": 15000002.5, "qty": 1.5, "side": "buy", "id": "2900000011"}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。

#### `v1-binance-aggtrades`(値の場面)
- 何を測るか: Binance aggTrades(見出しなし 8 列、ミリ秒、is_buyer_maker から攻め側の売買)を約定の事象にできるか
- 入力:
  - `backtest_data/binance_BTCUSDT_aggTrades_synth/BTCUSDT-aggTrades-2026-01-05.csv`(3 行):
    ```
    1001,96000.10,0.00100000,5001,5001,1767571207123,True,True
    1002,96000.20,0.25000000,5002,5004,1767571207124,False,True
    1003,95999.90,1.00000000,5005,5005,1767571208000,True,True
    ```
  - データ `binance`: paths = ['backtest_data/binance_BTCUSDT_aggTrades_synth/BTCUSDT-aggTrades-2026-01-05.csv']、spec = `{"format": "csv", "header": false, "names": ["agg_id", "price", "qty", "first_id", "last_id", "transact_time", "is_buyer_maker", "is_best_match"], "delimiter": ",", "kind": "trade", "symbol": "BTCUSDT", "asset": "crypto", "time": {"columns": ["transact_time"], "unit": "ms", "tz": "UTC"}, "fields": {"id": "agg_id", "px": "price", "qty": "qty", "side": "is_buyer_maker"}, "side_map": {"True": "sell", "False": "buy"}, "key": "id"}`
  - want = ['events']
- 期待: `{"events": {"binance": [{"t_ns": 1767571207123000000, "px": 96000.1, "qty": 0.001, "side": "sell", "id": "1001"}, {"t_ns": 1767571207124000000, "px": 96000.2, "qty": 0.25, "side": "buy", "id": "1002"}, {"t_ns": 1767571208000000000, "px": 95999.9, "qty": 1.0, "side": "sell", "id": "1003"}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。

#### `v1-fx-ticks`(値の場面)
- 何を測るか: FX のイベントティック(ts_utc,bid,ask,bidvol,askvol、空白区切りの ISO)を気配の事象にできるか
- 入力:
  - `backtest_data/fx_event_ticks_synth/NFP_20260109.csv`(4 行):
    ```
    ts_utc,bid,ask,bidvol,askvol
    2026-01-09 13:30:00.123,157.123,157.126,1.5,2.25
    2026-01-09 13:30:01.000,157.120,157.124,0.5,1
    2026-01-09 13:30:01.005,157.301,157.309,3,0.75
    ```
  - データ `fx`: paths = ['backtest_data/fx_event_ticks_synth/NFP_20260109.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "quote", "symbol": "USDJPY", "asset": "fx", "time": {"columns": ["ts_utc"], "unit": "iso", "tz": "UTC"}, "fields": {"bid": "bid", "ask": "ask", "bid_qty": "bidvol", "ask_qty": "askvol"}}`
  - want = ['events']
- 期待: `{"events": {"fx": [{"t_ns": 1767965400123000000, "bid": 157.123, "ask": 157.126, "bid_qty": 1.5, "ask_qty": 2.25}, {"t_ns": 1767965401000000000, "bid": 157.12, "ask": 157.124, "bid_qty": 0.5, "ask_qty": 1.0}, {"t_ns": 1767965401005000000, "bid": 157.301, "ask": 157.309, "bid_qty": 3.0, "ask_qty": 0.75}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。

#### `v1-jpx-1m`(値の場面)
- 何を測るか: JPX の 1 分足(date,time の 2 列、日本時間。朝 8:45 は UTC で前日)を足の事象にできるか
- 入力:
  - `backtest_data/n225f_synth_20260105/bars_1min.csv`(4 行):
    ```
    date,time,open,high,low,close,volume
    2026-01-05,08:45,38000,38010,37990,38005,120
    2026-01-05,08:46,38005,38020,38000,38015,85
    2026-01-05,12:30,38100,38105,38080,38090,40
    ```
  - データ `jpx_1m`: paths = ['backtest_data/n225f_synth_20260105/bars_1min.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "bar", "symbol": "N225F", "asset": "jpx", "time": {"columns": ["date", "time"], "join": " ", "unit": "iso", "tz": "Asia/Tokyo"}, "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}, "bar": {"interval_s": 60, "label": "start"}, "key": "start"}`
  - want = ['events']
- 期待: `{"events": {"jpx_1m": [{"start_ns": 1767570300000000000, "open": 38000.0, "high": 38010.0, "low": 37990.0, "close": 38005.0, "volume": 120.0}, {"start_ns": 1767570360000000000, "open": 38005.0, "high": 38020.0, "low": 38000.0, "close": 38015.0, "volume": 85.0}, {"start_ns": 1767583800000000000, "open": 38100.0, "high": 38105.0, "low": 38080.0, "close": 38090.0, "volume": 40.0}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。

#### `v1-bitflyer-board-top10`(値の場面)
- 何を測るか: bitFlyer の板の上位 10 段(ts と bid_px_1..10・bid_sz_1..10・ask_px_1..10・ask_sz_1..10、gzip。段が足りない行は空欄)を板の写真の事象にできるか(空欄の段を 0 や欠けた値にしない)
- 入力:
  - `backtest_data/bf_board_synth_20260105/board_top10_20260105.csv.gz`(gzip)(3 行):
    ```
    ts,bid_px_1,bid_px_2,bid_px_3,bid_px_4,bid_px_5,bid_px_6,bid_px_7,bid_px_8,bid_px_9,bid_px_10,bid_sz_1,bid_sz_2,bid_sz_3,bid_sz_4,bid_sz_5,bid_sz_6,bid_sz_7,bid_sz_8,bid_sz_9,bid_sz_10,ask_px_1,ask_px_2,ask_px_3,ask_px_4,ask_px_5,ask_px_6,ask_px_7,ask_px_8,ask_px_9,ask_px_10,ask_sz_1,ask_sz_2,ask_sz_3,ask_sz_4,ask_sz_5,ask_sz_6,ask_sz_7,ask_sz_8,ask_sz_9,ask_sz_10
    2026-01-05 00:00:10+00:00,15000000,14999995,14999990,14999985,14999980,14999975,14999970,14999965,14999960,14999955,0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1,15000010,15000015,15000020,15000025,15000030,15000035,15000040,15000045,15000050,15000055,0.02,0.04,0.06,0.08,0.1,0.12,0.14,0.16,0.18,0.2
    2026-01-05 00:00:11+00:00,15000000,14999990,14999900,,,,,,,,0.5,1.25,2,,,,,,,,15000020,15000100,,,,,,,,,0.75,3,,,,,,,,
    ```
  - データ `board`: paths = ['backtest_data/bf_board_synth_20260105/board_top10_20260105.csv.gz']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "book", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"}, "fields": {"levels": 10, "bid_px": ["bid_px_1", "bid_px_2", "bid_px_3", "bid_px_4", "bid_px_5", "bid_px_6", "bid_px_7", "bid_px_8", "bid_px_9", "bid_px_10"], "bid_sz": ["bid_sz_1", "bid_sz_2", "bid_sz_3", "bid_sz_4", "bid_sz_5", "bid_sz_6", "bid_sz_7", "bid_sz_8", "bid_sz_9", "bid_sz_10"], "ask_px": ["ask_px_1", "ask_px_2", "ask_px_3", "ask_px_4", "ask_px_5", "ask_px_6", "ask_px_7", "ask_px_8", "ask_px_9", "ask_px_10"], "ask_sz": ["ask_sz_1", "ask_sz_2", "ask_sz_3", "ask_sz_4", "ask_sz_5", "ask_sz_6", "ask_sz_7", "ask_sz_8", "ask_sz_9", "ask_sz_10"]}, "compression": "gzip"}`
  - want = ['events']
- 期待: `{"events": {"board": [{"t_ns": 1767571210000000000, "bids": [[15000000.0, 0.01], [14999995.0, 0.02], [14999990.0, 0.03], [14999985.0, 0.04], [14999980.0, 0.05], [14999975.0, 0.06], [14999970.0, 0.07], [14999965.0, 0.08], [14999960.0, 0.09], [14999955.0, 0.1]], "asks": [[15000010.0, 0.02], [15000015.0, 0.04], [15000020.0, 0.06], [15000025.0, 0.08], [15000030.0, 0.1], [15000035.0, 0.12], [15000040.0, 0.14], [15000045.0, 0.16], [15000050.0, 0.18], [15000055.0, 0.2]]}, {"t_ns": 1767571211000000000, "bids": [[15000000.0, 0.5], [14999990.0, 1.25], [14999900.0, 2.0]], "asks": [[15000020.0, 0.75], [15000100.0, 3.0]]}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。

#### `v1-funding-and-liquidations`(値の場面)
- 何を測るか: 資金調達の率(CSV、settlement_date の時刻)と清算の通知(JSON の 1 行 1 通、gzip、欄は入れ子の raw.o.T・raw.o.p・raw.o.q・raw.o.S)を、それぞれ資金調達と清算の事象にできるか(入れ子の欄を宣言で指せるか)
- 入力:
  - `backtest_data/funding_synth/funding_rate_history.csv`(3 行):
    ```
    calculation_date,settlement_date,rate
    2026-01-05T04:00:00,2026-01-05T12:00:00,0.0001
    2026-01-05T12:00:00,2026-01-05T20:00:00,-0.00005
    ```
  - `backtest_data/liquidations_synth/liquidations_20260105.jsonl.gz`(gzip)(2 行):
    ```
    {"venue":"binance_um","recv_us":1767571212395000,"raw":{"e":"forceOrder","o":{"s":"BTCUSDT","S":"SELL","p":"96000.5","q":"0.25","T":1767571212345}}}
    {"venue":"binance_um","recv_us":1767571213050000,"raw":{"e":"forceOrder","o":{"s":"BTCUSDT","S":"BUY","p":"96010","q":"1.5","T":1767571213000}}}
    ```
  - データ `funding`: paths = ['backtest_data/funding_synth/funding_rate_history.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "funding", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["settlement_date"], "unit": "iso", "tz": "UTC"}, "fields": {"rate": "rate"}}`
  - データ `liquidations`: paths = ['backtest_data/liquidations_synth/liquidations_20260105.jsonl.gz']、spec = `{"format": "jsonl", "compression": "gzip", "kind": "liquidation", "symbol": "BTCUSDT", "asset": "crypto", "time": {"columns": ["raw.o.T"], "unit": "ms", "tz": "UTC"}, "fields": {"px": "raw.o.p", "qty": "raw.o.q", "side": "raw.o.S"}, "side_map": {"SELL": "sell", "BUY": "buy"}}`
  - want = ['events']
- 期待: `{"events": {"funding": [{"t_ns": 1767614400000000000, "rate": 0.0001}, {"t_ns": 1767643200000000000, "rate": -5e-05}], "liquidations": [{"t_ns": 1767571212345000000, "px": 96000.5, "qty": 0.25, "side": "sell"}, {"t_ns": 1767571213000000000, "px": 96010.0, "qty": 1.5, "side": "buy"}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。

#### `v1-all-assets-one-call`(能力の場面)
- 何を測るか: 上の 8 つ(暗号資産の約定 3 形・板の上位 10 段・資金調達・清算・FX の気配・JPX の足)を 1 回の読み込みの呼び出しで渡し、全部を共通の事象の形で返せるか(資産ごとの別の読み口を使わない)
- 入力:
  - `backtest_data/bf_exec_synth_20260105/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - `backtest_data/bf_exec_us_synth_20260105/executions_20260105.csv.gz`(gzip)(4 行):
    ```
    id,ts_us,side,price,size,source
    2900000010,1767571205000000,BUY,15000000,0.01,rest
    ,1767571205000500,SELL,15000001,0.25,ws
    2900000011,1767571206999999,BUY,15000002.5,1.5,rest
    ```
  - `backtest_data/binance_BTCUSDT_aggTrades_synth/BTCUSDT-aggTrades-2026-01-05.csv`(3 行):
    ```
    1001,96000.10,0.00100000,5001,5001,1767571207123,True,True
    1002,96000.20,0.25000000,5002,5004,1767571207124,False,True
    1003,95999.90,1.00000000,5005,5005,1767571208000,True,True
    ```
  - `backtest_data/fx_event_ticks_synth/NFP_20260109.csv`(4 行):
    ```
    ts_utc,bid,ask,bidvol,askvol
    2026-01-09 13:30:00.123,157.123,157.126,1.5,2.25
    2026-01-09 13:30:01.000,157.120,157.124,0.5,1
    2026-01-09 13:30:01.005,157.301,157.309,3,0.75
    ```
  - `backtest_data/n225f_synth_20260105/bars_1min.csv`(4 行):
    ```
    date,time,open,high,low,close,volume
    2026-01-05,08:45,38000,38010,37990,38005,120
    2026-01-05,08:46,38005,38020,38000,38015,85
    2026-01-05,12:30,38100,38105,38080,38090,40
    ```
  - `backtest_data/bf_board_synth_20260105/board_top10_20260105.csv.gz`(gzip)(3 行):
    ```
    ts,bid_px_1,bid_px_2,bid_px_3,bid_px_4,bid_px_5,bid_px_6,bid_px_7,bid_px_8,bid_px_9,bid_px_10,bid_sz_1,bid_sz_2,bid_sz_3,bid_sz_4,bid_sz_5,bid_sz_6,bid_sz_7,bid_sz_8,bid_sz_9,bid_sz_10,ask_px_1,ask_px_2,ask_px_3,ask_px_4,ask_px_5,ask_px_6,ask_px_7,ask_px_8,ask_px_9,ask_px_10,ask_sz_1,ask_sz_2,ask_sz_3,ask_sz_4,ask_sz_5,ask_sz_6,ask_sz_7,ask_sz_8,ask_sz_9,ask_sz_10
    2026-01-05 00:00:10+00:00,15000000,14999995,14999990,14999985,14999980,14999975,14999970,14999965,14999960,14999955,0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1,15000010,15000015,15000020,15000025,15000030,15000035,15000040,15000045,15000050,15000055,0.02,0.04,0.06,0.08,0.1,0.12,0.14,0.16,0.18,0.2
    2026-01-05 00:00:11+00:00,15000000,14999990,14999900,,,,,,,,0.5,1.25,2,,,,,,,,15000020,15000100,,,,,,,,,0.75,3,,,,,,,,
    ```
  - `backtest_data/funding_synth/funding_rate_history.csv`(3 行):
    ```
    calculation_date,settlement_date,rate
    2026-01-05T04:00:00,2026-01-05T12:00:00,0.0001
    2026-01-05T12:00:00,2026-01-05T20:00:00,-0.00005
    ```
  - `backtest_data/liquidations_synth/liquidations_20260105.jsonl.gz`(gzip)(2 行):
    ```
    {"venue":"binance_um","recv_us":1767571212395000,"raw":{"e":"forceOrder","o":{"s":"BTCUSDT","S":"SELL","p":"96000.5","q":"0.25","T":1767571212345}}}
    {"venue":"binance_um","recv_us":1767571213050000,"raw":{"e":"forceOrder","o":{"s":"BTCUSDT","S":"BUY","p":"96010","q":"1.5","T":1767571213000}}}
    ```
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_synth_20260105/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - データ `bf_us`: paths = ['backtest_data/bf_exec_us_synth_20260105/executions_20260105.csv.gz']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["ts_us"], "unit": "us", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id", "compression": "gzip"}`
  - データ `binance`: paths = ['backtest_data/binance_BTCUSDT_aggTrades_synth/BTCUSDT-aggTrades-2026-01-05.csv']、spec = `{"format": "csv", "header": false, "names": ["agg_id", "price", "qty", "first_id", "last_id", "transact_time", "is_buyer_maker", "is_best_match"], "delimiter": ",", "kind": "trade", "symbol": "BTCUSDT", "asset": "crypto", "time": {"columns": ["transact_time"], "unit": "ms", "tz": "UTC"}, "fields": {"id": "agg_id", "px": "price", "qty": "qty", "side": "is_buyer_maker"}, "side_map": {"True": "sell", "False": "buy"}, "key": "id"}`
  - データ `fx`: paths = ['backtest_data/fx_event_ticks_synth/NFP_20260109.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "quote", "symbol": "USDJPY", "asset": "fx", "time": {"columns": ["ts_utc"], "unit": "iso", "tz": "UTC"}, "fields": {"bid": "bid", "ask": "ask", "bid_qty": "bidvol", "ask_qty": "askvol"}}`
  - データ `jpx_1m`: paths = ['backtest_data/n225f_synth_20260105/bars_1min.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "bar", "symbol": "N225F", "asset": "jpx", "time": {"columns": ["date", "time"], "join": " ", "unit": "iso", "tz": "Asia/Tokyo"}, "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}, "bar": {"interval_s": 60, "label": "start"}, "key": "start"}`
  - データ `board`: paths = ['backtest_data/bf_board_synth_20260105/board_top10_20260105.csv.gz']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "book", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"}, "fields": {"levels": 10, "bid_px": ["bid_px_1", "bid_px_2", "bid_px_3", "bid_px_4", "bid_px_5", "bid_px_6", "bid_px_7", "bid_px_8", "bid_px_9", "bid_px_10"], "bid_sz": ["bid_sz_1", "bid_sz_2", "bid_sz_3", "bid_sz_4", "bid_sz_5", "bid_sz_6", "bid_sz_7", "bid_sz_8", "bid_sz_9", "bid_sz_10"], "ask_px": ["ask_px_1", "ask_px_2", "ask_px_3", "ask_px_4", "ask_px_5", "ask_px_6", "ask_px_7", "ask_px_8", "ask_px_9", "ask_px_10"], "ask_sz": ["ask_sz_1", "ask_sz_2", "ask_sz_3", "ask_sz_4", "ask_sz_5", "ask_sz_6", "ask_sz_7", "ask_sz_8", "ask_sz_9", "ask_sz_10"]}, "compression": "gzip"}`
  - データ `funding`: paths = ['backtest_data/funding_synth/funding_rate_history.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "funding", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["settlement_date"], "unit": "iso", "tz": "UTC"}, "fields": {"rate": "rate"}}`
  - データ `liquidations`: paths = ['backtest_data/liquidations_synth/liquidations_20260105.jsonl.gz']、spec = `{"format": "jsonl", "compression": "gzip", "kind": "liquidation", "symbol": "BTCUSDT", "asset": "crypto", "time": {"columns": ["raw.o.T"], "unit": "ms", "tz": "UTC"}, "fields": {"px": "raw.o.p", "qty": "raw.o.q", "side": "raw.o.S"}, "side_map": {"SELL": "sell", "BUY": "buy"}}`
  - want = ['events']
- 期待: `{"events": {"bf_rest": [{"t_ns": 1767571200100000000, "px": 15000000.0, "qty": 0.01, "side": "buy", "id": "2900000001"}, {"t_ns": 1767571200250000000, "px": 15000005.0, "qty": 0.02, "side": "sell", "id": "2900000002"}, {"t_ns": 1767571201000000000, "px": 15000010.0, "qty": 0.5, "side": "", "id": "2900000003"}, {"t_ns": 1767571201999000000, "px": 14999995.5, "qty": 0.001, "side": "sell", "id": "2900000004"}], "bf_us": [{"t_ns": 1767571205000000000, "px": 15000000.0, "qty": 0.01, "side": "buy", "id": "2900000010"}, {"t_ns": 1767571205000500000, "px": 15000001.0, "qty": 0.25, "side": "sell", "id": ""}, {"t_ns": 1767571206999999000, "px": 15000002.5, "qty": 1.5, "side": "buy", "id": "2900000011"}], "binance": [{"t_ns": 1767571207123000000, "px": 96000.1, "qty": 0.001, "side": "sell", "id": "1001"}, {"t_ns": 1767571207124000000, "px": 96000.2, "qty": 0.25, "side": "buy", "id": "1002"}, {"t_ns …(全 2527 字。全文は i1_scenes.py の場面の定義)`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。 8 つの正解は上の場面と同じ。

#### `v1-generic-shape`(能力の場面)
- 何を測るか: 種(20260925 から 3 つ)で列の名前・並び・区切り文字(, ; タブ |)・見出しの有無・時刻の単位(s/ms/us/ns/iso)を引いた 3 つのファイルを、宣言(spec)だけで読めるか(形ごとの専用の読み口を書かずに読めること)
- 入力:
  - `backtest_data/generic_synth_20260925/trades.txt`(4 行):
    ```
    709250<TAB>1.36<TAB>15085031<TAB>1767572809<TAB>BUY
    709251<TAB>0.05<TAB>15758980<TAB>1767572812<TAB>SELL
    709252<TAB>3.06<TAB>15285732<TAB>1767572814<TAB>BUY
    709253<TAB>0.03<TAB>15222782<TAB>1767572818<TAB>BUY
    ```
  - `backtest_data/generic_synth_20260926/trades.txt`(5 行):
    ```
    c891716_p,c884431_s,c530167_q,c614767_i,c240161_t
    14473326,SELL,0.66,709260,1767573230874
    14649728,BUY,3.67,709261,1767573232611
    14342270,BUY,0.99,709262,1767573237324
    14526357,SELL,1.23,709263,1767573240677
    ```
  - `backtest_data/generic_synth_20260927/trades.txt`(5 行):
    ```
    c424124_s;c519164_q;c074760_t;c126312_i;c081282_p
    BUY;0.04;1767571961299000;709270;14532788
    BUY;3.89;1767571965146000;709271;15129199
    BUY;0.73;1767571967042000;709272;15058003
    SELL;3.96;1767571970251000;709273;15302265
    ```
  - `backtest_data/generic_synth_20260928/trades.txt`(4 行):
    ```
    15715613<TAB>SELL<TAB>1767574103523000000<TAB>0.17<TAB>709280
    15404661<TAB>SELL<TAB>1767574104789000000<TAB>3.53<TAB>709281
    15918755<TAB>SELL<TAB>1767574105848000000<TAB>0.97<TAB>709282
    15008723<TAB>SELL<TAB>1767574107091000000<TAB>3.23<TAB>709283
    ```
  - `backtest_data/generic_synth_20260929/trades.txt`(4 行):
    ```
    2.99|709290|SELL|15052631|2026-01-05T00:34:40.318Z
    2.30|709291|BUY|15049629|2026-01-05T00:34:44.773Z
    2.49|709292|SELL|14389767|2026-01-05T00:34:46.717Z
    3.26|709293|SELL|14532880|2026-01-05T00:34:48.908Z
    ```
  - データ `generic_20260925`: paths = ['backtest_data/generic_synth_20260925/trades.txt']、spec = `{"format": "csv", "header": false, "delimiter": "\t", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["c534966_t"], "unit": "s", "tz": "UTC"}, "fields": {"id": "c805376_i", "px": "c122963_p", "qty": "c452644_q", "side": "c593638_s"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id", "names": ["c805376_i", "c452644_q", "c122963_p", "c534966_t", "c593638_s"]}`
  - データ `generic_20260926`: paths = ['backtest_data/generic_synth_20260926/trades.txt']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["c240161_t"], "unit": "ms", "tz": "UTC"}, "fields": {"id": "c614767_i", "px": "c891716_p", "qty": "c530167_q", "side": "c884431_s"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - データ `generic_20260927`: paths = ['backtest_data/generic_synth_20260927/trades.txt']、spec = `{"format": "csv", "header": true, "delimiter": ";", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["c074760_t"], "unit": "us", "tz": "UTC"}, "fields": {"id": "c126312_i", "px": "c081282_p", "qty": "c519164_q", "side": "c424124_s"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - データ `generic_20260928`: paths = ['backtest_data/generic_synth_20260928/trades.txt']、spec = `{"format": "csv", "header": false, "delimiter": "\t", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["c875321_t"], "unit": "ns", "tz": "UTC"}, "fields": {"id": "c792964_i", "px": "c033498_p", "qty": "c224423_q", "side": "c993278_s"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id", "names": ["c033498_p", "c993278_s", "c875321_t", "c224423_q", "c792964_i"]}`
  - データ `generic_20260929`: paths = ['backtest_data/generic_synth_20260929/trades.txt']、spec = `{"format": "csv", "header": false, "delimiter": "|", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["c697948_t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "c304738_i", "px": "c485520_p", "qty": "c154160_q", "side": "c457293_s"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id", "names": ["c154160_q", "c304738_i", "c457293_s", "c485520_p", "c697948_t"]}`
  - want = ['events']
- 期待: `{"events": {"generic_20260925": [{"t_ns": 1767572809000000000, "px": 15085031.0, "qty": 1.36, "side": "buy", "id": "709250"}, {"t_ns": 1767572812000000000, "px": 15758980.0, "qty": 0.05, "side": "sell", "id": "709251"}, {"t_ns": 1767572814000000000, "px": 15285732.0, "qty": 3.06, "side": "buy", "id": "709252"}, {"t_ns": 1767572818000000000, "px": 15222782.0, "qty": 0.03, "side": "buy", "id": "709253"}], "generic_20260926": [{"t_ns": 1767573230874000000, "px": 14473326.0, "qty": 0.66, "side": "sell", "id": "709260"}, {"t_ns": 1767573232611000000, "px": 14649728.0, "qty": 3.67, "side": "buy", "id": "709261"}, {"t_ns": 1767573237324000000, "px": 14342270.0, "qty": 0.99, "side": "buy", "id": "709262"}, {"t_ns": 1767573240677000000, "px": 14526357.0, "qty": 1.23, "side": "sell", "id": "709263"}], "generic_20260927": [{"t_ns": 1767571961299000000, "px": 14532788.0, "qty": 0.04, "side": "buy",  …(全 1992 字。全文は i1_scenes.py の場面の定義)`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。 形は種から決まり、2 回の実行で同じ。

### V2 時刻の単位の正規化(3 場面: 値 3・能力 0)

#### `v2-same-instant-4-units`(値の場面)
- 何を測るか: 同じ 4 つの瞬間(小数部 0 / 0.5 秒 / 0.123456789 秒 / 23:59:59.999999999)を秒・ミリ・マイクロ・ナノの 10 進(小数部つき)と ISO(9 桁、Z)で書いた 5 ファイルが、全部同じ UTC の int64 ナノ秒になるか(浮動小数に落として桁を失わないか)
- 入力:
  - `backtest_data/units_synth/s.csv`(5 行):
    ```
    id,t,price,size,side
    1,1767571200,100,1,BUY
    2,1767571200.5,100,1,BUY
    3,1767571200.123456789,100,1,BUY
    4,1767657599.999999999,100,1,BUY
    ```
  - `backtest_data/units_synth/ms.csv`(5 行):
    ```
    id,t,price,size,side
    1,1767571200000,100,1,BUY
    2,1767571200500,100,1,BUY
    3,1767571200123.456789,100,1,BUY
    4,1767657599999.999999,100,1,BUY
    ```
  - `backtest_data/units_synth/us.csv`(5 行):
    ```
    id,t,price,size,side
    1,1767571200000000,100,1,BUY
    2,1767571200500000,100,1,BUY
    3,1767571200123456.789,100,1,BUY
    4,1767657599999999.999,100,1,BUY
    ```
  - `backtest_data/units_synth/ns.csv`(5 行):
    ```
    id,t,price,size,side
    1,1767571200000000000,100,1,BUY
    2,1767571200500000000,100,1,BUY
    3,1767571200123456789,100,1,BUY
    4,1767657599999999999,100,1,BUY
    ```
  - `backtest_data/units_synth/iso.csv`(5 行):
    ```
    id,t,price,size,side
    1,2026-01-05T00:00:00.000000000Z,100,1,BUY
    2,2026-01-05T00:00:00.500000000Z,100,1,BUY
    3,2026-01-05T00:00:00.123456789Z,100,1,BUY
    4,2026-01-05T23:59:59.999999999Z,100,1,BUY
    ```
  - データ `u_s`: paths = ['backtest_data/units_synth/s.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "s", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - データ `u_ms`: paths = ['backtest_data/units_synth/ms.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "ms", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - データ `u_us`: paths = ['backtest_data/units_synth/us.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "us", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - データ `u_ns`: paths = ['backtest_data/units_synth/ns.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "ns", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - データ `u_iso`: paths = ['backtest_data/units_synth/iso.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - want = ['times']
- 期待: `{"events": {"u_s": [{"t_ns": 1767571200000000000}, {"t_ns": 1767571200500000000}, {"t_ns": 1767571200123456789}, {"t_ns": 1767657599999999999}], "u_ms": [{"t_ns": 1767571200000000000}, {"t_ns": 1767571200500000000}, {"t_ns": 1767571200123456789}, {"t_ns": 1767657599999999999}], "u_us": [{"t_ns": 1767571200000000000}, {"t_ns": 1767571200500000000}, {"t_ns": 1767571200123456789}, {"t_ns": 1767657599999999999}], "u_ns": [{"t_ns": 1767571200000000000}, {"t_ns": 1767571200500000000}, {"t_ns": 1767571200123456789}, {"t_ns": 1767657599999999999}], "u_iso": [{"t_ns": 1767571200000000000}, {"t_ns": 1767571200500000000}, {"t_ns": 1767571200123456789}, {"t_ns": 1767657599999999999}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。 10 進の文字列は瞬間を単位で割った商と余りから正確に書いた(丸めなし)。

#### `v2-iso-offsets`(値の場面)
- 何を測るか: 同じ瞬間を 6 通りの ISO(Z / +09:00 / 空白区切り +00:00 / -05:00 / 9 桁 Z / コロンなし +0500)で書いた行が、全部同じナノ秒になるか
- 入力:
  - `backtest_data/iso_forms_synth/trades.csv`(7 行):
    ```
    id,t,price,size,side
    1,2026-01-05T00:00:01.5Z,100,1,SELL
    2,2026-01-05T09:00:01.5+09:00,100,1,SELL
    3,2026-01-05 00:00:01.500+00:00,100,1,SELL
    4,2026-01-04T19:00:01.500000-05:00,100,1,SELL
    5,2026-01-05T00:00:01.500000000Z,100,1,SELL
    6,2026-01-05T05:00:01.500+0500,100,1,SELL
    ```
  - データ `iso_forms`: paths = ['backtest_data/iso_forms_synth/trades.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - want = ['times']
- 期待: `{"events": {"iso_forms": [{"t_ns": 1767571201500000000}, {"t_ns": 1767571201500000000}, {"t_ns": 1767571201500000000}, {"t_ns": 1767571201500000000}, {"t_ns": 1767571201500000000}, {"t_ns": 1767571201500000000}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。 各行は同じ瞬間を、その行の時差の壁時計で書いた。

#### `v2-naive-local-tz`(値の場面)
- 何を測るか: オフセットの無い壁時計の時刻を、spec が宣言した Asia/Tokyo で UTC に直せるか(1 つ目は 1 列の ISO、2 つ目は date と time の 2 列。どちらも UTC の日付の境をまたぐ)
- 入力:
  - `backtest_data/local_synth/trades_jst.csv`(4 行):
    ```
    id,t,price,size,side
    1,2026-01-05 08:59:59.000,100,1,BUY
    2,2026-01-05 09:00:00.000,100,1,BUY
    3,2026-01-05 00:00:00.250,100,1,BUY
    ```
  - `backtest_data/local_synth/bars_jst.csv`(4 行):
    ```
    date,time,open,high,low,close,volume
    2026-01-05,08:59,10,10,10,10,1
    2026-01-05,09:00,10,10,10,10,1
    2026-01-06,00:00,10,10,10,10,1
    ```
  - データ `jst_trades`: paths = ['backtest_data/local_synth/trades_jst.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "Asia/Tokyo"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - データ `jst_bars`: paths = ['backtest_data/local_synth/bars_jst.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "bar", "symbol": "N225F", "asset": "jpx", "time": {"columns": ["date", "time"], "join": " ", "unit": "iso", "tz": "Asia/Tokyo"}, "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}, "bar": {"interval_s": 60, "label": "start"}, "key": "start"}`
  - want = ['times']
- 期待: `{"events": {"jst_trades": [{"t_ns": 1767571199000000000}, {"t_ns": 1767571200000000000}, {"t_ns": 1767538800250000000}], "jst_bars": [{"start_ns": 1767571140000000000}, {"start_ns": 1767571200000000000}, {"start_ns": 1767625200000000000}]}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。 正解は壁時計から 9 時間を引いた UTC。

### V3 重複・逆行・欠落・世代間の食い違いの検出(5 場面: 値 5・能力 0)

#### `v3-clean-control`(値の場面)
- 何を測るか: 異常の無いファイル(同じ時刻に id の違う 2 件を含む)で、異常を 0 件と返し、事象を全部返すか(何でも異常と言う対象を通さないための対照)
- 入力:
  - `backtest_data/v3_synth/clean.csv`(6 行):
    ```
    id,t,price,size,side
    1,2026-01-05T00:00:00.000Z,100,1,BUY
    2,2026-01-05T00:00:01.000Z,101,1,SELL
    3,2026-01-05T00:00:01.000Z,102,2,BUY
    4,2026-01-05T00:00:02.000Z,103,1,BUY
    5,2026-01-05T00:00:03.000Z,104,1,SELL
    ```
  - データ `clean`: paths = ['backtest_data/v3_synth/clean.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - want = ['events', 'anomalies']
- 期待: `{"events": {"clean": [{"t_ns": 1767571200000000000, "id": "1"}, {"t_ns": 1767571201000000000, "id": "2"}, {"t_ns": 1767571201000000000, "id": "3"}, {"t_ns": 1767571202000000000, "id": "4"}, {"t_ns": 1767571203000000000, "id": "5"}]}, "anomalies": {"clean": []}}`
- 正解の出し方: 合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形でファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。 異常の正解は空。

#### `v3-duplicate-and-conflict`(値の場面)
- 何を測るか: 同じ id の同じ行(重複)と、同じ id で値の違う行(食い違い)を仕込み、重複 1 件・食い違い 1 件を時刻つきで返すか(同じ時刻で id の違う正当な 2 件は異常にしない)
- 入力:
  - `backtest_data/v3_synth/dup.csv`(8 行):
    ```
    id,t,price,size,side
    1,2026-01-05T00:00:00.000Z,100,1,BUY
    2,2026-01-05T00:00:01.000Z,101,1,SELL
    3,2026-01-05T00:00:01.000Z,102,2,BUY
    2,2026-01-05T00:00:01.000Z,101,1,SELL
    4,2026-01-05T00:00:02.000Z,103,1,BUY
    4,2026-01-05T00:00:02.000Z,103.5,1,BUY
    5,2026-01-05T00:00:03.000Z,104,1,SELL
    ```
  - データ `dup`: paths = ['backtest_data/v3_synth/dup.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - want = ['anomalies']
- 期待: `{"anomalies": {"dup": [{"kind": "duplicate", "t_ns": 1767571201000000000}, {"kind": "conflict", "t_ns": 1767571202000000000}]}}`
- 正解の出し方: 仕込んだ行を定義(キー = spec の key。同じキーで全列が同じ = duplicate、同じキーで値が違う = conflict)に当てて数えた。

#### `v3-backward`(値の場面)
- 何を測るか: 時刻が前の行より戻る行を 2 つ(2 つ目は直前の行より後だが、それまでの最大より前)仕込み、逆行 2 件を時刻つきで返すか
- 入力:
  - `backtest_data/v3_synth/backward.csv`(8 行):
    ```
    id,t,price,size,side
    1,2026-01-05T00:00:00.000Z,100,1,BUY
    2,2026-01-05T00:00:01.000Z,100,1,BUY
    3,2026-01-05T00:00:02.000Z,100,1,BUY
    4,2026-01-05T00:00:01.500Z,100,1,BUY
    5,2026-01-05T00:00:03.000Z,100,1,BUY
    6,2026-01-05T00:00:02.500Z,100,1,BUY
    7,2026-01-05T00:00:04.000Z,100,1,BUY
    ```
  - データ `back`: paths = ['backtest_data/v3_synth/backward.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - want = ['anomalies']
- 期待: `{"anomalies": {"back": [{"kind": "backward", "t_ns": 1767571201500000000}, {"kind": "backward", "t_ns": 1767571202500000000}]}}`
- 正解の出し方: 逆行の定義 = その行の時刻 < それより前の行の時刻の最大。仕込んだ 2 行が当たる。

#### `v3-gap-bars`(値の場面)
- 何を測るか: 24 時間取引の 1 分足で 3 本(2 本続き + 1 本)が欠けたファイルで、欠落 3 件を欠けた足の始まりの時刻つきで返すか
- 入力:
  - `backtest_data/candles_synth/candles_gap.csv`(8 行):
    ```
    ts,open,high,low,close,volume
    2026-01-05 00:00:00+00:00,100,101,99,100,1
    2026-01-05 00:01:00+00:00,100,101,99,100,1
    2026-01-05 00:02:00+00:00,100,101,99,100,1
    2026-01-05 00:05:00+00:00,100,101,99,100,1
    2026-01-05 00:06:00+00:00,100,101,99,100,1
    2026-01-05 00:08:00+00:00,100,101,99,100,1
    2026-01-05 00:09:00+00:00,100,101,99,100,1
    ```
  - データ `gap`: paths = ['backtest_data/candles_synth/candles_gap.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "bar", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"}, "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}, "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}`
  - want = ['anomalies']
- 期待: `{"anomalies": {"gap": [{"kind": "gap", "t_ns": 1767571380000000000}, {"kind": "gap", "t_ns": 1767571440000000000}, {"kind": "gap", "t_ns": 1767571620000000000}]}}`
- 正解の出し方: 欠落の定義 = 最初の足から最後の足までの足の間隔(60 秒)の格子で、行の無い始まりの時刻 1 つにつき 1 件(24x7 なので休場は無い)。

#### `v3-generations`(値の場面)
- 何を測るか: 同じデータの 2 つの世代(分 0〜5 と 分 4〜9)を 1 つのデータとして読ませ、重なりの分 4(同じ値 = 重複)と分 5(値が違う = 食い違い)を返すか(黙ってどちらかを採って結合しない)
- 入力:
  - `backtest_data/candles_synth_gen1/candles.csv`(7 行):
    ```
    ts,open,high,low,close,volume
    2026-01-05 00:00:00+00:00,100,100,100,100,1
    2026-01-05 00:01:00+00:00,101,101,101,101,1
    2026-01-05 00:02:00+00:00,102,102,102,102,1
    2026-01-05 00:03:00+00:00,103,103,103,103,1
    2026-01-05 00:04:00+00:00,104,104,104,104,1
    2026-01-05 00:05:00+00:00,105,105,105,105,1
    ```
  - `backtest_data/candles_synth_gen2/candles.csv`(7 行):
    ```
    ts,open,high,low,close,volume
    2026-01-05 00:04:00+00:00,104,104,104,104,1
    2026-01-05 00:05:00+00:00,999,999,999,999,1
    2026-01-05 00:06:00+00:00,106,106,106,106,1
    2026-01-05 00:07:00+00:00,107,107,107,107,1
    2026-01-05 00:08:00+00:00,108,108,108,108,1
    2026-01-05 00:09:00+00:00,109,109,109,109,1
    ```
  - データ `gens`: paths = ['backtest_data/candles_synth_gen1/candles.csv', 'backtest_data/candles_synth_gen2/candles.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "bar", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"}, "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}, "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}`
  - want = ['anomalies']
- 期待: `{"anomalies": {"gens": [{"kind": "duplicate", "t_ns": 1767571440000000000}, {"kind": "conflict", "t_ns": 1767571500000000000}]}}`
- 正解の出し方: 重複と食い違いの定義(キー = 足の始まり)を、2 つのファイルの重なり 2 本に当てた。

### V4 sha256 の記録(2 場面: 値 1・能力 1)

#### `v4-sha256-values`(値の場面)
- 何を測るか: 読んだファイルごとの sha256(平文と gzip の 2 本。ディスクに置かれたバイト列のまま)を、実行の記録として返すか
- 入力:
  - `backtest_data/bf_exec_synth_20260105/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - `backtest_data/bf_exec_us_synth_20260105/executions_20260105.csv.gz`(gzip)(4 行):
    ```
    id,ts_us,side,price,size,source
    2900000010,1767571205000000,BUY,15000000,0.01,rest
    ,1767571205000500,SELL,15000001,0.25,ws
    2900000011,1767571206999999,BUY,15000002.5,1.5,rest
    ```
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_synth_20260105/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - データ `bf_us`: paths = ['backtest_data/bf_exec_us_synth_20260105/executions_20260105.csv.gz']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["ts_us"], "unit": "us", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id", "compression": "gzip"}`
  - want = ['times', 'hashes']
- 期待: `{"events": {"bf_rest": [{"t_ns": 1767571200100000000}, {"t_ns": 1767571200250000000}, {"t_ns": 1767571201000000000}, {"t_ns": 1767571201999000000}], "bf_us": [{"t_ns": 1767571205000000000}, {"t_ns": 1767571205000500000}, {"t_ns": 1767571206999999000}]}, "hashes": {"backtest_data/bf_exec_synth_20260105/executions_20260105.csv": "83a351d9d28f02e5e04a0ee2ed9fcd13d2145b7d915bb17c8feddd7323a335ff", "backtest_data/bf_exec_us_synth_20260105/executions_20260105.csv.gz": "4a3d638a7693b0800e0a50b0c2cf24267a2cabd47ff3cb25da27c3e53843ec7d"}}`
- 正解の出し方: 書いたバイト列そのものに hashlib.sha256 を当てた(gzip は mtime 0 で圧縮したバイト列)。

#### `v4-sha256-distinguishes`(能力の場面)
- 何を測るか: 中身が同じで場所の違うファイルに同じ sha256、1 バイトだけ違うファイルに違う sha256 を記録するか
- 入力:
  - `backtest_data/bf_exec_synth_20260105/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - `backtest_data/bf_exec_synth_copy/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - `backtest_data/bf_exec_synth_edit/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000006,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_synth_20260105/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - データ `copy`: paths = ['backtest_data/bf_exec_synth_copy/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - データ `edit`: paths = ['backtest_data/bf_exec_synth_edit/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['hashes']
- 期待: `{"hashes": {"backtest_data/bf_exec_synth_20260105/executions_20260105.csv": "83a351d9d28f02e5e04a0ee2ed9fcd13d2145b7d915bb17c8feddd7323a335ff", "backtest_data/bf_exec_synth_copy/executions_20260105.csv": "83a351d9d28f02e5e04a0ee2ed9fcd13d2145b7d915bb17c8feddd7323a335ff", "backtest_data/bf_exec_synth_edit/executions_20260105.csv": "cb4a3e0ab163cc325f630b79fc96b1a34e65136f51df73e8f35a4e4f4354db08"}}`
- 正解の出し方: 3 本のバイト列に hashlib.sha256 を当てた(元と写しは同じ値、1 バイト違いは違う値になる)。

### V5 合成・中間物・封印区間を拒む許可一覧(7 場面: 値 1・能力 6)

#### `v5-reject-qa`(能力の場面)
- 何を測るか: 合成(backtest_data/qa_*)の下のファイルを拒むか
- 入力:
  - `backtest_data/bf_exec_synth_20260105/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_synth_20260105/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 変形(拒むべき入力):
  - `backtest_data/qa_known_answer_synth/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/qa_known_answer_synth/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 期待: `{"events": {"bf_rest": [{"t_ns": 1767571200100000000, "px": 15000000.0}, {"t_ns": 1767571200250000000, "px": 15000005.0}, {"t_ns": 1767571201000000000, "px": 15000010.0}, {"t_ns": 1767571201999000000, "px": 14999995.5}]}}`
- 正解の出し方: 対照 = 許されるパスに置いた同じ中身(正解は V1 の bitflyer-rest と同じ事象)。変形 = 拒むべきパス。正解 = 対照を正しく読み、変形を拒む。

#### `v5-reject-o3c`(能力の場面)
- 何を測るか: 研究の中間物(backtest_data/o3c_*)を拒み、名前に o3c を含むだけの生データ(binance_cm_o3c_*)は読むか
- 入力:
  - `backtest_data/binance_cm_o3c_synth/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/binance_cm_o3c_synth/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 変形(拒むべき入力):
  - `backtest_data/o3c_signal_synth/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/o3c_signal_synth/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 期待: `{"events": {"bf_rest": [{"t_ns": 1767571200100000000, "px": 15000000.0}, {"t_ns": 1767571200250000000, "px": 15000005.0}, {"t_ns": 1767571201000000000, "px": 15000010.0}, {"t_ns": 1767571201999000000, "px": 14999995.5}]}}`
- 正解の出し方: 対照 = 許されるパスに置いた同じ中身(正解は V1 の bitflyer-rest と同じ事象)。変形 = 拒むべきパス。正解 = 対照を正しく読み、変形を拒む。

#### `v5-reject-phase2-runs`(能力の場面)
- 何を測るか: 研究の中間物(backtest_data/phase2_runs/)を拒むか
- 入力:
  - `backtest_data/bf_exec_synth_20260105/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_synth_20260105/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 変形(拒むべき入力):
  - `backtest_data/phase2_runs/unit_synth/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/phase2_runs/unit_synth/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 期待: `{"events": {"bf_rest": [{"t_ns": 1767571200100000000, "px": 15000000.0}, {"t_ns": 1767571200250000000, "px": 15000005.0}, {"t_ns": 1767571201000000000, "px": 15000010.0}, {"t_ns": 1767571201999000000, "px": 14999995.5}]}}`
- 正解の出し方: 対照 = 許されるパスに置いた同じ中身(正解は V1 の bitflyer-rest と同じ事象)。変形 = 拒むべきパス。正解 = 対照を正しく読み、変形を拒む。

#### `v5-reject-dotdot`(能力の場面)
- 何を測るか: 許されるフォルダから .. で拒むフォルダ(qa_*)へ抜けるパスを拒むか(文字列の頭だけを見ない)
- 入力:
  - `backtest_data/bf_exec_synth_20260105/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - `backtest_data/qa_known_answer_synth/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_synth_20260105/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 変形(拒むべき入力):
  - `backtest_data/bf_exec_synth_20260105/../qa_known_answer_synth/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - `backtest_data/qa_known_answer_synth/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_synth_20260105/../qa_known_answer_synth/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 期待: `{"events": {"bf_rest": [{"t_ns": 1767571200100000000, "px": 15000000.0}, {"t_ns": 1767571200250000000, "px": 15000005.0}, {"t_ns": 1767571201000000000, "px": 15000010.0}, {"t_ns": 1767571201999000000, "px": 14999995.5}]}}`
- 正解の出し方: 対照 = 許されるパスに置いた同じ中身(正解は V1 の bitflyer-rest と同じ事象)。変形 = 拒むべきパス。正解 = 対照を正しく読み、変形を拒む。

#### `v5-reject-symlink`(能力の場面)
- 何を測るか: 許される名前のフォルダが拒むフォルダ(qa_*)への symlink のとき、実体で拒むか
- 入力:
  - `backtest_data/bf_exec_synth_20260105/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - `backtest_data/qa_known_answer_synth/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - `backtest_data/bf_exec_link_synth` → symlink `qa_known_answer_synth`
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_synth_20260105/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 変形(拒むべき入力):
  - `backtest_data/qa_known_answer_synth/executions_20260105.csv`(5 行):
    ```
    id,exec_date,price,size,side
    2900000001,2026-01-05T00:00:00.100,15000000,0.01,BUY
    2900000002,2026-01-05T00:00:00.25,15000005,0.02,SELL
    2900000003,2026-01-05T00:00:01,15000010,0.5,
    2900000004,2026-01-05T00:00:01.999,14999995.5,0.001,SELL
    ```
  - `backtest_data/bf_exec_link_synth` → symlink `qa_known_answer_synth`
  - データ `bf_rest`: paths = ['backtest_data/bf_exec_link_synth/executions_20260105.csv']、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}`
  - want = ['events']
- 期待: `{"events": {"bf_rest": [{"t_ns": 1767571200100000000, "px": 15000000.0}, {"t_ns": 1767571200250000000, "px": 15000005.0}, {"t_ns": 1767571201000000000, "px": 15000010.0}, {"t_ns": 1767571201999000000, "px": 14999995.5}]}}`
- 正解の出し方: 対照 = 許されるパスに置いた同じ中身(正解は V1 の bitflyer-rest と同じ事象)。変形 = 拒むべきパス。正解 = 対照を正しく読み、変形を拒む。

#### `v5-seal-boundary`(値の場面)
- 何を測るか: 封印の境ちょうどの扱い: 範囲 [境の 1 時間前, 境) は境の直前の 1 行だけを返し、終わりを境の 1 ns 後にした範囲(境ちょうどの行 = 封印区間の最初の行を含む)は拒むか
- 入力:
  - `backtest_data/bf_exec_sealtest_20260105/trades.csv`(11 行):
    ```
    id,t,price,size,side
    1,2026-01-05T00:00:00.000Z,100,1,BUY
    2,2026-01-05T01:00:00.000Z,101,1,BUY
    3,2026-01-05T02:00:00.000Z,102,1,BUY
    4,2026-01-05T03:00:00.000Z,103,1,BUY
    5,2026-01-05T04:00:00.000Z,104,1,BUY
    6,2026-01-05T05:00:00.000Z,105,1,BUY
    7,2026-01-05T06:00:00.000Z,106,1,BUY
    …(残り 3 行)
    ```
  - `backtest_data/phase2_sealed/SYNTH-UNIT/SEALED.json`(12 行):
    ```
    {
     "unit": "SYNTH-UNIT",
     "sealed_at": "2026-02-04T00:00:00+00:00",
     "forward_start": "2026-02-04T00:00:00+00:00",
     "files": [
      {
       "path": "backtest_data/bf_exec_sealtest_20260105/trades.csv",
       "time_column": "t",
    …(残り 4 行)
    ```
  - データ `sealtest`: paths = ['backtest_data/bf_exec_sealtest_20260105/trades.csv']、range_ns = [1767592800000000000, 1767596400000000000]、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - want = ['events']
- 変形(拒むべき入力):
  - `backtest_data/bf_exec_sealtest_20260105/trades.csv`(11 行):
    ```
    id,t,price,size,side
    1,2026-01-05T00:00:00.000Z,100,1,BUY
    2,2026-01-05T01:00:00.000Z,101,1,BUY
    3,2026-01-05T02:00:00.000Z,102,1,BUY
    4,2026-01-05T03:00:00.000Z,103,1,BUY
    5,2026-01-05T04:00:00.000Z,104,1,BUY
    6,2026-01-05T05:00:00.000Z,105,1,BUY
    7,2026-01-05T06:00:00.000Z,106,1,BUY
    …(残り 3 行)
    ```
  - `backtest_data/phase2_sealed/SYNTH-UNIT/SEALED.json`(12 行):
    ```
    {
     "unit": "SYNTH-UNIT",
     "sealed_at": "2026-02-04T00:00:00+00:00",
     "forward_start": "2026-02-04T00:00:00+00:00",
     "files": [
      {
       "path": "backtest_data/bf_exec_sealtest_20260105/trades.csv",
       "time_column": "t",
    …(残り 4 行)
    ```
  - データ `sealtest`: paths = ['backtest_data/bf_exec_sealtest_20260105/trades.csv']、range_ns = [1767592800000000000, 1767596400000000001]、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - want = ['events']
- 期待: `{"events": {"sealtest": [{"t_ns": 1767592800000000000, "px": 106.0}]}}`
- 正解の出し方: 範囲は [始まり, 終わり) の半開区間、封印区間は seal_from_ts 以後(sealed.py の load_unsealed と同じ d < cutoff)。境の 1 時間前の行は範囲の中、境ちょうどの行は封印区間。

#### `v5-sealed-window`(能力の場面)
- 何を測るか: 封印の記録(backtest_data/phase2_sealed/<unit>/SEALED.json、load_sealed が守る形)に載ったファイルで、封印の境より前の範囲は読み、境をまたぐ範囲の読み込みを拒むか
- 入力:
  - `backtest_data/bf_exec_sealtest_20260105/trades.csv`(11 行):
    ```
    id,t,price,size,side
    1,2026-01-05T00:00:00.000Z,100,1,BUY
    2,2026-01-05T01:00:00.000Z,101,1,BUY
    3,2026-01-05T02:00:00.000Z,102,1,BUY
    4,2026-01-05T03:00:00.000Z,103,1,BUY
    5,2026-01-05T04:00:00.000Z,104,1,BUY
    6,2026-01-05T05:00:00.000Z,105,1,BUY
    7,2026-01-05T06:00:00.000Z,106,1,BUY
    …(残り 3 行)
    ```
  - `backtest_data/phase2_sealed/SYNTH-UNIT/SEALED.json`(12 行):
    ```
    {
     "unit": "SYNTH-UNIT",
     "sealed_at": "2026-02-04T00:00:00+00:00",
     "forward_start": "2026-02-04T00:00:00+00:00",
     "files": [
      {
       "path": "backtest_data/bf_exec_sealtest_20260105/trades.csv",
       "time_column": "t",
    …(残り 4 行)
    ```
  - データ `sealtest`: paths = ['backtest_data/bf_exec_sealtest_20260105/trades.csv']、range_ns = [1767571200000000000, 1767596400000000000]、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - want = ['events']
- 変形(拒むべき入力):
  - `backtest_data/bf_exec_sealtest_20260105/trades.csv`(11 行):
    ```
    id,t,price,size,side
    1,2026-01-05T00:00:00.000Z,100,1,BUY
    2,2026-01-05T01:00:00.000Z,101,1,BUY
    3,2026-01-05T02:00:00.000Z,102,1,BUY
    4,2026-01-05T03:00:00.000Z,103,1,BUY
    5,2026-01-05T04:00:00.000Z,104,1,BUY
    6,2026-01-05T05:00:00.000Z,105,1,BUY
    7,2026-01-05T06:00:00.000Z,106,1,BUY
    …(残り 3 行)
    ```
  - `backtest_data/phase2_sealed/SYNTH-UNIT/SEALED.json`(12 行):
    ```
    {
     "unit": "SYNTH-UNIT",
     "sealed_at": "2026-02-04T00:00:00+00:00",
     "forward_start": "2026-02-04T00:00:00+00:00",
     "files": [
      {
       "path": "backtest_data/bf_exec_sealtest_20260105/trades.csv",
       "time_column": "t",
    …(残り 4 行)
    ```
  - データ `sealtest`: paths = ['backtest_data/bf_exec_sealtest_20260105/trades.csv']、range_ns = [1767571200000000000, 1767603600000000001]、spec = `{"format": "csv", "header": true, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto", "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"}, "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}`
  - want = ['events']
- 期待: `{"events": {"sealtest": [{"t_ns": 1767571200000000000, "px": 100.0}, {"t_ns": 1767574800000000000, "px": 101.0}, {"t_ns": 1767578400000000000, "px": 102.0}, {"t_ns": 1767582000000000000, "px": 103.0}, {"t_ns": 1767585600000000000, "px": 104.0}, {"t_ns": 1767589200000000000, "px": 105.0}, {"t_ns": 1767592800000000000, "px": 106.0}]}}`
- 正解の出し方: 対照 = 範囲 [最初の行, seal_from_ts) の 7 行(正解は書いた行そのもの)。変形 = 範囲 [最初の行, 最後の行] = 封印区間の 3 行を含む。正解 = 変形を拒む。

### V6 JPX 個別株の分割・併合・上場廃止・コード変更の調整と、生存者の偏りを避ける銘柄集合(5 場面: 値 4・能力 1)

#### `v6-split`(値の場面)
- 何を測るか: 1:2 の株式分割(ex_date 1/8)を、それより前の足の値段 ÷2・出来高 ×2 に調整して返すか
- 入力:
  - bars = `[{"code": "1001", "date": "2026-01-05", "open": 1000, "high": 1020, "low": 980, "close": 1000, "volume": 3000}, {"code": "1001", "date": "2026-01-06", "open": 1010, "high": 1030, "low": 990, "close": 1010, "volume": 3100}, {"code": "1001", "date": "2026-01-07", "open": 1020, "high": 1040, "low": 1000, "close": 1020, "volume": 3200}, {"code": "1001", "date": "2026-01-08", "open": 510, "high": 520, "low": 500, "close": 512, "volume": 7000}, {"code": "1001", "date": "2026-01-09", "open": 512, "high": 522, "low": 502, "close": 514, "volume": 7100}]`
  - actions = `[{"code": "1001", "type": "split", "ex_date": "2026-01-08", "ratio": 2}]`、listings = `[{"code": "1001", "listed": "2000-01-04", "delisted": null}]`
  - as_of = 2026-01-09、universe_dates = []
- 期待: `{"adjusted": {"1001": [{"date": "2026-01-05", "open": 500.0, "high": 510.0, "low": 490.0, "close": 500.0, "volume": 6000.0}, {"date": "2026-01-06", "open": 505.0, "high": 515.0, "low": 495.0, "close": 505.0, "volume": 6200.0}, {"date": "2026-01-07", "open": 510.0, "high": 520.0, "low": 500.0, "close": 510.0, "volume": 6400.0}, {"date": "2026-01-08", "open": 510.0, "high": 520.0, "low": 500.0, "close": 512.0, "volume": 7000.0}, {"date": "2026-01-09", "open": 512.0, "high": 522.0, "low": 502.0, "close": 514.0, "volume": 7100.0}]}}`
- 正解の出し方: 後ろ向きの調整の定義(ex_date より前の足の値段 × 1/r、出来高 × r。as_of より後の ex_date は当てない、as_of より後の足は返さない)を分数で計算した(値段と出来高は割り切れる数に選んだ)。

#### `v6-reverse-split`(値の場面)
- 何を測るか: 5 株を 1 株にする株式併合(ex_date 1/7)を、それより前の足の値段 ×5・出来高 ÷5 に調整して返すか
- 入力:
  - bars = `[{"code": "1006", "date": "2026-01-05", "open": 200, "high": 204, "low": 198, "close": 202, "volume": 50000}, {"code": "1006", "date": "2026-01-06", "open": 202, "high": 206, "low": 200, "close": 204, "volume": 50500}, {"code": "1006", "date": "2026-01-07", "open": 1010, "high": 1025, "low": 1000, "close": 1015, "volume": 10100}, {"code": "1006", "date": "2026-01-08", "open": 1015, "high": 1030, "low": 1005, "close": 1020, "volume": 10200}, {"code": "1006", "date": "2026-01-09", "open": 1020, "high": 1035, "low": 1010, "close": 1025, "volume": 10300}]`
  - actions = `[{"code": "1006", "type": "reverse_split", "ex_date": "2026-01-07", "ratio": 5}]`、listings = `[{"code": "1006", "listed": "2000-01-04", "delisted": null}]`
  - as_of = 2026-01-09、universe_dates = []
- 期待: `{"adjusted": {"1006": [{"date": "2026-01-05", "open": 1000.0, "high": 1020.0, "low": 990.0, "close": 1010.0, "volume": 10000.0}, {"date": "2026-01-06", "open": 1010.0, "high": 1030.0, "low": 1000.0, "close": 1020.0, "volume": 10100.0}, {"date": "2026-01-07", "open": 1010.0, "high": 1025.0, "low": 1000.0, "close": 1015.0, "volume": 10100.0}, {"date": "2026-01-08", "open": 1015.0, "high": 1030.0, "low": 1005.0, "close": 1020.0, "volume": 10200.0}, {"date": "2026-01-09", "open": 1020.0, "high": 1035.0, "low": 1010.0, "close": 1025.0, "volume": 10300.0}]}}`
- 正解の出し方: 後ろ向きの調整の定義(ex_date より前の足の値段 × 1/r、出来高 × r。as_of より後の ex_date は当てない、as_of より後の足は返さない)を分数で計算した(値段と出来高は割り切れる数に選んだ)。

#### `v6-point-in-time`(値の場面)
- 何を測るか: 同じ分割のデータを as_of = 1/7(ex_date の前)で読ませたとき、まだ起きていない分割で過去を調整せず(先読みしない)、1/7 までの足だけを返すか
- 入力:
  - bars = `[{"code": "1001", "date": "2026-01-05", "open": 1000, "high": 1020, "low": 980, "close": 1000, "volume": 3000}, {"code": "1001", "date": "2026-01-06", "open": 1010, "high": 1030, "low": 990, "close": 1010, "volume": 3100}, {"code": "1001", "date": "2026-01-07", "open": 1020, "high": 1040, "low": 1000, "close": 1020, "volume": 3200}, {"code": "1001", "date": "2026-01-08", "open": 510, "high": 520, "low": 500, "close": 512, "volume": 7000}, {"code": "1001", "date": "2026-01-09", "open": 512, "high": 522, "low": 502, "close": 514, "volume": 7100}]`
  - actions = `[{"code": "1001", "type": "split", "ex_date": "2026-01-08", "ratio": 2}]`、listings = `[{"code": "1001", "listed": "2000-01-04", "delisted": null}]`
  - as_of = 2026-01-07、universe_dates = []
- 期待: `{"adjusted": {"1001": [{"date": "2026-01-05", "open": 1000.0, "high": 1020.0, "low": 980.0, "close": 1000.0, "volume": 3000.0}, {"date": "2026-01-06", "open": 1010.0, "high": 1030.0, "low": 990.0, "close": 1010.0, "volume": 3100.0}, {"date": "2026-01-07", "open": 1020.0, "high": 1040.0, "low": 1000.0, "close": 1020.0, "volume": 3200.0}]}}`
- 正解の出し方: 後ろ向きの調整の定義(ex_date より前の足の値段 × 1/r、出来高 × r。as_of より後の ex_date は当てない、as_of より後の足は返さない)を分数で計算した(値段と出来高は割り切れる数に選んだ)。

#### `v6-code-change`(値の場面)
- 何を測るか: 銘柄コードの変更(1002 → 1003、1/8 から)で、as_of 1/9 の 1003 の系列に変更前の 1002 の足をつないで返し、1002 を別の銘柄として残さないか。日付ごとの銘柄集合も 1/7 は 1002、1/8 は 1003 に切り替わるか
- 入力:
  - bars = `[{"code": "1002", "date": "2026-01-05", "open": 300, "high": 303, "low": 297, "close": 300, "volume": 1000}, {"code": "1002", "date": "2026-01-06", "open": 300, "high": 303, "low": 297, "close": 301, "volume": 1000}, {"code": "1002", "date": "2026-01-07", "open": 300, "high": 303, "low": 297, "close": 302, "volume": 1000}, {"code": "1003", "date": "2026-01-08", "open": 305, "high": 309, "low": 301, "close": 305, "volume": 1100}, {"code": "1003", "date": "2026-01-09", "open": 305, "high": 309, "low": 301, "close": 306, "volume": 1100}]`
  - actions = `[{"code": "1002", "type": "code_change", "ex_date": "2026-01-08", "new_code": "1003"}]`、listings = `[{"code": "1002", "listed": "2000-01-04", "delisted": null}]`
  - as_of = 2026-01-09、universe_dates = ['2026-01-07', '2026-01-08']
- 期待: `{"adjusted": {"1003": [{"date": "2026-01-05", "open": 300.0, "high": 303.0, "low": 297.0, "close": 300.0, "volume": 1000.0}, {"date": "2026-01-06", "open": 300.0, "high": 303.0, "low": 297.0, "close": 301.0, "volume": 1000.0}, {"date": "2026-01-07", "open": 300.0, "high": 303.0, "low": 297.0, "close": 302.0, "volume": 1000.0}, {"date": "2026-01-08", "open": 305.0, "high": 309.0, "low": 301.0, "close": 305.0, "volume": 1100.0}, {"date": "2026-01-09", "open": 305.0, "high": 309.0, "low": 301.0, "close": 306.0, "volume": 1100.0}]}, "universe": {"2026-01-07": ["1002"], "2026-01-08": ["1003"]}}`
- 正解の出し方: 定義: コード変更は同じ銘柄の名前の付け替え。as_of の時点のコードの下に、それ以前の全部の足(調整なし)を並べる。銘柄集合はex_date より前は古いコード、ex_date 以後は新しいコード。

#### `v6-universe-survivorship`(能力の場面)
- 何を測るか: 日付ごとの銘柄集合を、その日に上場していた銘柄で返すか(後で上場廃止になる 1005 を過去の日から落とさない = 生存者の偏りを避ける、後で上場する 1004 を前の日に入れない)
- 入力:
  - bars = `[]`
  - actions = `[]`、listings = `[{"code": "1001", "listed": "2000-01-04", "delisted": null}, {"code": "1004", "listed": "2026-01-06", "delisted": null}, {"code": "1005", "listed": "2010-06-01", "delisted": "2026-01-08"}]`
  - as_of = 2026-01-09、universe_dates = ['2026-01-05', '2026-01-06', '2026-01-07', '2026-01-08']
- 期待: `{"universe": {"2026-01-05": ["1001", "1005"], "2026-01-06": ["1001", "1004", "1005"], "2026-01-07": ["1001", "1004", "1005"], "2026-01-08": ["1001", "1004"]}}`
- 正解の出し方: 定義: 日付 d に上場 ⇔ listed ≤ d < delisted(delisted 無しは無限)。4 日について定義どおりに並べた。

### V7 足のベクトル化の近道(同じ足で事象駆動と一致)(4 場面: 値 3・能力 1)

#### `v7-bars-from-trades`(値の場面)
- 何を測るか: 同じ約定から、事象駆動の経路と近道(ベクトル化)の経路の両方で 1 分足を作り、両方が正解と一致し、互いにビット単位で一致するか(足の端ちょうど・端の 1 ns 前・約定の無い分を含む)
- 入力:
  - trades(8 件)= `[{"t_ns": 1767571200000000000, "px": 100.0, "qty": 0.5, "side": "buy", "id": "1"}, {"t_ns": 1767571220000000000, "px": 103.0, "qty": 0.25, "side": "buy", "id": "2"}, {"t_ns": 1767571259999999999, "px": 101.0, "qty": 0.125, "side": "buy", "id": "3"}, {"t_ns": 1767571260000000000, "px": 102.0, "qty": 1.0, "side": "buy", "id": "4"}, {"t_ns": 1767571290000000000, "px": 99.0, "qty": 0.5, "side": "buy", "id": "5"}, {"t_ns": 1767571380000000000, "px": 105.0, "qty": 0.25, "side": "buy", "id": "6"}, {"t_ns": 1767571450000000000, "px": 104.0, "qty": 0.5, "side": "buy", "id": "7"}, {"t_ns": 1767571499999999999, "px": 106.0, "qty": 0.75, "side": "buy", "id": "8"}]`
  - interval_s = 60、rule = `null`、want = ['bars']
- 期待: `{"paths": {"bars": [{"start_ns": 1767571200000000000, "open": 100.0, "high": 103.0, "low": 100.0, "close": 101.0, "volume": 0.875}, {"start_ns": 1767571260000000000, "open": 102.0, "high": 102.0, "low": 99.0, "close": 99.0, "volume": 1.5}, {"start_ns": 1767571380000000000, "open": 105.0, "high": 105.0, "low": 105.0, "close": 105.0, "volume": 0.25}, {"start_ns": 1767571440000000000, "open": 104.0, "high": 106.0, "low": 104.0, "close": 106.0, "volume": 1.25}]}}`
- 正解の出し方: 定義どおり: 足 = [始まり, 始まり+60 秒)、始値 = 最初、高値 = 最大、安値 = 最小、終値 = 最後、出来高 = 数量の和(2 進で割り切れる数量なので和は正確)、約定の無い分は足を作らない。

#### `v7-rule-integer`(値の場面)
- 何を測るか: 同じ足(終値が整数)に同じ規則(SMA3・終値 > SMA なら次の足を 1 単位の買い持ち・費用なし)を両方の経路で当て、SMA・建玉・資産の推移が正解と一致し、互いにビット単位で一致するか
- 入力:
  - bars(10 件)= `[{"start_ns": 1767571200000000000, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1.0}, {"start_ns": 1767571260000000000, "open": 103.0, "high": 104.0, "low": 102.0, "close": 103.0, "volume": 1.0}, {"start_ns": 1767571320000000000, "open": 106.0, "high": 107.0, "low": 105.0, "close": 106.0, "volume": 1.0}, {"start_ns": 1767571380000000000, "open": 101.0, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 1.0}, {"start_ns": 1767571440000000000, "open": 99.0, "high": 100.0, "low": 98.0, "close": 99.0, "volume": 1.0}, {"start_ns": 1767571500000000000, "open": 104.0, "high": 105.0, "low": 103.0, "close": 104.0, "volume": 1.0}, {"start_ns": 1767571560000000000, "open": 1 …(全 1096 字。全文は i1_scenes.py の場面の定義)`
  - interval_s = 60、rule = `{"type": "sma_long_flat", "n": 3, "init_cash": 1000000, "unit": 1}`、want = ['sma', 'position', 'equity']
- 期待: `{"paths": {"sma": [null, null, 103.0, 103.33333333333333, 102.0, 101.33333333333333, 103.66666666666667, 106.33333333333333, 106.0, 106.66666666666667], "position": [0, 0, 1, 0, 0, 1, 1, 1, 0, 1], "equity": [1000000.0, 1000000.0, 1000000.0, 999995.0, 999995.0, 999995.0, 999999.0, 999998.0, 999994.0, 999994.0]}}`
- 正解の出し方: V7 の規則の定義を分数で計算した(整数の和と 3 での割り算 1 回なので浮動小数でも丸めの順によらない)。

#### `v7-rule-fractional`(値の場面)
- 何を測るか: 終値が 10 進の小数(2 進で割り切れない)の足で同じ規則を当て、両方の経路が互いにビット単位で一致し、正解から相対 1e-9 以内か(浮動小数の丸めの順が経路で違えばビットの一致が崩れる)
- 入力:
  - bars(10 件)= `[{"start_ns": 1767571200000000000, "open": 100.7, "high": 100.7, "low": 100.7, "close": 100.7, "volume": 1.0}, {"start_ns": 1767571260000000000, "open": 101.8, "high": 101.8, "low": 101.8, "close": 101.8, "volume": 1.0}, {"start_ns": 1767571320000000000, "open": 101.7, "high": 101.7, "low": 101.7, "close": 101.7, "volume": 1.0}, {"start_ns": 1767571380000000000, "open": 100.4, "high": 100.4, "low": 100.4, "close": 100.4, "volume": 1.0}, {"start_ns": 1767571440000000000, "open": 101.1, "high": 101.1, "low": 101.1, "close": 101.1, "volume": 1.0}, {"start_ns": 1767571500000000000, "open": 102.9, "high": 102.9, "low": 102.9, "close": 102.9, "volume": 1.0}, {"start_ns": 1767571560000000000, "open …(全 1100 字。全文は i1_scenes.py の場面の定義)`
  - interval_s = 60、rule = `{"type": "sma_long_flat", "n": 3, "init_cash": 1000000, "unit": 1}`、want = ['sma', 'position', 'equity']
- 期待: `{"paths": {"sma": [null, null, 101.4, 101.3, 101.06666666666666, 101.46666666666667, 101.96666666666667, 102.10000000000001, 101.8, 101.76666666666667], "position": [0, 0, 1, 0, 1, 1, 0, 0, 1, 1], "equity": [1000000.0, 1000000.0, 1000000.0, 999998.7, 999998.7, 1000000.5, 999999.5, 999999.5, 999999.5, 999999.3]}}`(浮動小数は相対 1e-09 まで)
- 正解の出し方: V7 の規則の定義を、対象に渡す浮動小数(10 進の文字列を float にしたもの)の正確な値を分数にして計算し、最後に浮動小数にした。終値と SMA の差はどの足でも 0.033 以上(際どい比べが無い)。許す差は相対 1e-9(浮動小数の演算の順の違いの分)。経路の間は差を許さない。

#### `v7-speed`(能力の場面)
- 何を測るか: 2 万本の足(終値は整数)に同じ規則を当てる仕事で、近道の経路が事象駆動の経路より速く(壁時計)、両方の結果が正解と一致し、互いにビット単位で一致するか(近道の意味を成すか)
- 入力:
  - bars(20000 件)= `[{"start_ns": 1767571200000000000, "open": 15000014.0, "high": 15000014.0, "low": 15000014.0, "close": 15000014.0, "volume": 1.0}, {"start_ns": 1767571260000000000, "open": 14999842.0, "high": 14999842.0, "low": 14999842.0, "close": 14999842.0, "volume": 1.0}, {"start_ns": 1767571320000000000, "open": 15000223.0, "high": 15000223.0, "low": 15000223.0, "close": 15000223.0, "volume": 1.0}, {"start_ns": 1767571380000000000, "open": 15000079.0, "high": 15000079.0, "low": 15000079.0, "close": 15000079.0, "volume": 1.0}, {"start_ns": 1767571440000000000, "open": 15000165.0, "high": 15000165.0, "low": 15000165.0, "close": 15000165.0, "volume": 1.0}, {"start_ns": 1767571500000000000, "open": 1500015 …(全 1560 字。全文は i1_scenes.py の場面の定義)` …
  - interval_s = 60、rule = `{"type": "sma_long_flat", "n": 3, "init_cash": 100000000, "unit": 1}`、want = ['sma', 'position', 'equity', 'timing']
- 期待: `{"paths": {"sma": [null, null, 15000026.333333334, 15000048.0, 15000155.666666666, 15000134.0, 15000179.0, 15000258.0, 15000206.666666666, 15000059.0, 14999980.0, 14999977.0, 15000158.0, 15000205.333333334, 15000462.333333334, 15000688.666666666, 15000856.0, 15000971.0, 15001113.333333334, 15001168.333333334, 15001142.666666666, 15000861.666666666, 15000808.0, 15000711.0, 15000700.666666666, 15000687.0, 15000745.333333334, 15000764.0, 15000720.666666666, 15000715.666666666, 15000695.333333334, 15000697.333333334, 15000614.333333334, 15000649.0, 15000586.666666666, 15000409.0, 15000323.666666666, 15000199.333333334, 15000035.666666666, 14999672.666666666, 14999424.333333334, 14999306.0, 14999431.0, 14999393.666666666, 14999501.333333334, 14999497.333333334, 14999708.666666666, 14999840.333333334, 15000021.0, 15000145.333333334, 15000180.0, 15000210.0, 15000235.0, 15000467.333333334, 15000 …(全 663029 字。全文は i1_scenes.py の場面の定義)`
- 正解の出し方: SMA・建玉・資産の正解は V7 の規則の定義を分数で計算した(終値は種つきの乱数の整数の歩み)。速さは adapter が両経路の呼び出しの前後で測った秒で、近道の秒 < 事象駆動の秒 を正解とする。

## 8. 返す前の吟味(場面係の最初の作り。委任文 §3「提出前の吟味」、L-433)

固定した要件(REQUIREMENTS.md の V1〜V7)・場面集の規則 1〜9・比較の観点を読み直し、「非常に厳しい監査役・批評家なら何を [止める] にするか」を
観点ごとに列べ、返す前に潰した(潰せなかったものは「残り」に書く)。

| 観点・規則 | 止められうること | 潰した方法(ファイル・試験) |
|---|---|---|
| V1 | 「§1 の全資産」なのに約定と足だけ | bitFlyer の約定(REST・統合版 gzip)・Binance aggTrades(見出しなし)・FX のイベントティック・JPX の 1 分足(2 列・日本時間)・板の上位 10 段(空欄の段)・資金調達・清算(JSON 1 行 1 通・入れ子の欄)の 8 形を値の場面にし、1 回の呼び出しで全部の場面を足した(`v1-*`) |
| V1 | 「資産ごとに専用のパーサを書かない」を形で見ている(規則 2 違反) | 形ではなく振る舞いで見る: 種から列の名・並び・区切り・見出し・単位を引いた 5 ファイルを宣言だけで読ませる(`v1-generic-shape`)。専用の読み口を場面の形に合わせて書いた対象は通らない |
| V2 | 単位の変換を整数の秒だけで見ている | 小数部つきの 10 進(秒 9 桁・ミリ 6 桁・マイクロ 3 桁)とナノ秒の整数と 9 桁の ISO で同じ瞬間を書き、浮動小数に落とすと崩れる形にした。オフセット 6 通り・宣言した時間帯・日付の境・2 列の時刻(`v2-*`)。正解は試験で Fraction と数字の正規表現で読み直した(`test_v2_*`・`test_local_zone_*`) |
| V3 | 「件数が一致」だけで、何を 1 件と数えるかが無い | 種類ごとの定義(キー・全列・最大・格子)を §3 に書き、(種類, 時刻) の多重集合で比べる。同じ時刻で id の違う正当な行を対照に入れ、何でも異常と言う対象を通さない(`v3-clean-control`) |
| V3 | 一部の種類しか持たない相手を不当に「不一致」にしている | §3 に決まりとして書いた(持つ種類の結果をそのまま返す。持たない種類を黙って見落とすのが「黙って結合」)。要件の「黙って結合しない」をそのまま測るため |
| V4 | ハッシュを場面の側で計算して正解にしている(自己採点) | 正解は書いたバイト列そのものへの sha256(gzip は mtime 0 の圧縮後のバイト列)。1 バイト違い・同じ中身の別の場所も置いた(`v4-sha256-distinguishes`)。試験 `test_v4_expected_hash_is_of_the_written_bytes` |
| V5 | 拒むだけの対象(何でも拒む)が通る | どの場面も対照(許されるパスの同じ中身)を正しく読んだうえで変形を拒んだときだけ正解。名前に o3c を含むだけの生データは読む(`v5-reject-o3c`)。`..` と symlink で抜ける道(`v5-reject-dotdot`・`v5-reject-symlink`)、封印の境ちょうど(`v5-seal-boundary`)。変形の実体が拒むべき場所を指すことを試験で確かめた(`test_every_scene_materializes_*`) |
| V6 | 分割だけで、併合・コード変更・上場廃止・先読みが無い | 分割・併合・as_of が ex_date より前(先読みしない)・コード変更(系列と銘柄集合)・上場廃止と後の上場(銘柄集合)の 5 場面。値は割り切れる数で分数から出した(`test_v6_*`) |
| V7 | 「近道が事象駆動と一致」を丸めの出ない整数だけで見ている | 整数の場面に加え、10 進の小数の終値で経路の間のビット一致を求める場面(`v7-rule-fractional`)。正解は対象に渡す浮動小数の正確な値から分数で出した(最初の作りでは 10 進の文字列から出していて、際どい比べ(差 4.7e-15)で正解そのものが誤っていた。対象を走らせて見つけ、終値を選び直し、差が 0.033 以上であることを試験にした `test_v7_rule_on_the_exact_binary_values_and_no_near_tie`) |
| V7 | 速さを測っていない | 2 万本の足で両経路の秒を比べ、同時に値の正解とビットの一致も見る(`v7-speed`) |
| 規則 1 | 能力の場面が「動いた」で決まる | 能力の場面も全部、正解(結果)を持つ(`test_capability_scenes_are_judged_by_results_too`) |
| 規則 3 | 観点に値の場面が無い | 全観点に値の場面(`test_every_viewpoint_has_a_value_scene_*`)。最初の作りでは V5 に値の場面が無く、この試験で見つけて `v5-seal-boundary` を足した |
| 規則 4 | 動いた道具の一部の場面だけを走らせた | runner は対象ごとに全場面を 2 回ずつ別のプロセスで走らせる。動いた道具は全部、全場面に通した(記録は opponents/RUNNABILITY.tsv と survey_results/) |
| 規則 5 | 表の「最も良い結果」の順が無い | §3 に書いた |
| 規則 6・9 | 動かせない候補を検討せずに外した / 理由なしのスキップ | 13 候補 × 7 観点の全部を opponents/CONSIDERED.md に載せ、`scripts/check_bt_considered.py --write` で誤り 0 件。スキップは 0 件(段の無い観点なので「段が低い」は使えず、「上位互換」も使っていない)。機構を持つのに場面の形を取れない候補は、機構を導入済みのコードどおりに再現した |
| 規則 7 | 試験の置き場所 | 場面集の試験は tests/bt/battery/item_1/ だけ |
| 判定 | 判定器が甘い | 正解そのものは通り、1 ns のずれ・欄の欠け・時刻の float・id の int・1 ビット違いの経路・遅い近道・空欄の段を 0 で埋めた板・異常の 1 件の欠けを全部落とす(`test_judge_*`・`test_board_*`) |
| 試金石 | 不具合が場面に当たらない / 2 回で違う | 時間帯の宣言を無視する 1 か所だけ。当たる場面を mutant.py に名指しし、名指した場面だけが崩れることを試験にした(`test_mutant_breaks_exactly_the_scenes_it_names`)。決定的なので再現の欄は変わらない |
| adapter | adapter が値を作れば相手が強くも弱くもなる | adapter はファイルを開かない・正解を読まない(i1_protocol.py)。再現は「読み取りは再現の側の手段」と明記し、V3 の検査の機構にだけ使う(読み取りだけで V1・V2 の正解を取らないように、V3 以外の場面では結果を返さない) |

**残り(潰せなかったこと・未確認)**
- 調査結果の側の導入・再現の経緯(対象ごとの事情)は、審査員が読むこの文書には書かず、opponents/RUNNABILITY.tsv・opponents/attempts/・opponents/CONSIDERED.md に書いた(盲検のため)。
- 要件のファイル §3.4 の番号の並びの「5・7」と「その他」の読み方(CONSIDERED.md の冒頭)。
