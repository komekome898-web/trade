# 単一の真実 — 直読み棚卸し(DATA_QA_CHECKLIST #10)

`gates.shared_or_local`(または同等の解決器)を経由せずに `data/`・`paper_logs/`・`logs/`
配下を直接開いている箇所の棚卸しと、研究側読み手への対応。範囲: `scripts/`・`src/`。
書き込みは一切行っていない(データファイルは無変更)。コミットもしていない。

## 1. 対応済み(研究側読み手 → shared_or_local 経由に変更)

| path:function | 読む対象 | 対応前 | 対応後 |
|---|---|---|---|
| scripts/research_position_ladder.py:main | data/oi_snapshots.csv | 直読み(DEFAULT_CSV) | `shared_or_local`。`--write-prices` はローカルのみ書込み(paper_logs は無変更) |
| scripts/paper_on1.py:load_sessions | data/jpx_daily/nk225_sessions.csv | 直読み(IN_CSV) | `shared_or_local(shared_name="nk225_sessions.csv")` |
| scripts/research_board_calibration.py:main | data/tape/{ticker,executions}_*.csv.gz | 直読み(`--data` 既定) | 新規 `default_tape_dir()`(`shared_or_local_dir`) |
| scripts/research_wall_front.py:main | 同上 | 直読み | `default_tape_dir()` を board_calibration から再利用 |
| scripts/research_m4_finecheck.py:main | 同上 | 直読み | `cal.default_tape_dir()` |
| scripts/research_matilda_taro.py:main | 同上 | 直読み | `cal.default_tape_dir()` |
| scripts/research_matilda_modern.py:main | 同上 | 直読み | `cal.default_tape_dir()` |
| scripts/research_spread_mm.py:main | 同上 | 直読み(`cal.load(ROOT/"data"/"tape")`) | `cal.default_tape_dir()` |
| scripts/research_latency_grade.py(モジュール定数 TAPE) | 同上 | 直読み | `shared_or_local_dir` |
| scripts/research_latency_paths.py(モジュール定数 TAPE) | 同上 | 直読み | `shared_or_local_dir`(WS_DIRは対象外、下記) |
| scripts/research_clock_burst.py(モジュール定数 TAPE_GLOB) | 同上 | `paper_logs/tape` に固定(ローカルへのフォールバック無し) | `shared_or_local_dir` で新しい方を選択 |

全11件、実行して読み込んだコピーの絶対パスを起動直後に1回 `[data] ... :` として標準出力に印字するようにした
(実行確認: 上記11本を実際に実行し、いずれも `paper_logs/tape` または `paper_logs/oi_snapshots.csv` /
`paper_logs/nk225_sessions.csv` を選択・完走することを確認)。

新設ヘルパー: `src/bot/monitoring/gates.py:shared_or_local_dir(root, rel, shared_name=None)` —
`shared_or_local` のディレクトリ版(1日単位のファイル集合を持つ `data/tape/` 用。ディレクトリ内の
最新mtimeファイルで比較)。`judge_board_round.py` の手書き `venues_dir()` と同じ発想。

## 2. 既に shared_or_local / 同等の解決器を経由(対応不要)

| path | 対象 | 経路 |
|---|---|---|
| scripts/judge_gates.py (G1/G4/G6) | logs/bot.jsonl, data/scalp_paper.jsonl, data/oi_snapshots.csv | `shared_or_local` |
| scripts/judge_gates.py:gate_board (G7) | data/ws | `gates._ws_span`(listing方式の同等解決器) |
| scripts/judge_gates.py:gate_funding (G8) | data/candles_FX_BTC_JPY.csv | paper_logs に鏡写しが存在しないため backtest_data+data/ を単純結合。対応不要 |
| scripts/judge_board_round.py | data/board_round/{series_5s.csv.gz,coverage.json} | `shared_or_local` |
| scripts/judge_board_round.py:venues_dir | data/venues | 手書きの同等解決器(mtimeでなく日数優先) |
| scripts/retention_snapshot.py | data/oi_snapshots.csv | `shared_or_local`。venues は両方を意図的に走査(スナップショット用途で網羅性が目的、単一化は不要) |
| scripts/tp_operating_curve.py | 既定は backtest_data の恒久スナップショット | `judge_board_round.load_series` 経由・凍結済みデータなので鮮度リスクなし |
| scripts/research_signal_fade.py | 既定は backtest_data の恒久スナップショット(TAPE定数) | 同上。bot.jsonl は docstring内の比較対象の記述のみで実際には読んでいない |
| scripts/research_leader_surface.py | backtest_data 内 zip / data/binance_BTCUSDT_1m_full.csv | paper_logs に鏡写しが無い系列。対応不要 |
| src/bot/research/board.py, sealed.py | 呼び出し元が渡す明示パス / backtest_data の封印スナップショット | パス決定はしていない(呼び出し元責務)。sealed.py は phase2 封印の強制側そのもの |

## 3. 収集・記録スクリプト(ローカル書込みが設計、対象外・列挙のみ)

`fetch_*.py`(20本: aggtrades/attention/binance_daily/binance_full/daily_lt1/deep/deribit/
dukascopy/external/fx_calendar(2本)/history/jpx_daily/kraken/okx/regime_composite ほか)、
`record_oi.py`・`record_realtime.py`・`record_venues.py`、`extract_tape.py`、
`build_*.py`(6本: basis/burst_library/flow/fx_event_library(2本)/storm_library)。
いずれも `data/` 配下に一次データを書く収集側であり、`share_logs.bat`/`fetch_all.bat` が
その後 `paper_logs/` へ共有する片方向の起点。自身の既存ファイルを自己修復のため読むもの
(例: `fetch_binance_daily.py` の metrics.csv/usdjpy.csv 差分更新)を含め、直読みは仕様どおり。

## 4. 監視・建玉・本体側(研究側読み手ではないため対象外・列挙のみ)

`scripts/dashboard.py`・`src/bot/monitoring/{aggregate,market_view,decision_text}.py` —
稼働中プロセスの最新ローカル状態を見せるダッシュボード(オペレータPCではローカルが正)。
`src/bot/{risk/kill_switch,portfolio/persistence,strategy/composite,logging_setup,main,atomic_file}.py`、
`src/bot/jpx/{on1_executor,run_lock}.py` — BOT本体・ON1実行機自身が書く/読む状態ファイル
(kill_switch.json・overlay_state.json・status.json・bot.jsonl 等)。これらは「生成元」なので
shared_or_local の対象ではない(むしろ shared_or_local はこれらの出力を研究側が読むときに使う側)。
`scripts/paper_onr.py` — 入力の `data/onr/{etf_1343_daily.csv,reit_index_daily.csv}` は
paper_logs に鏡写しが無く(出力側の `onr_ledger.csv`/`onr_status.json` のみ共有対象)、対応不要。

## 5. まとめ

- 直読み棚卸し対象(研究側読み手): 11件検出 → 11件を `shared_or_local`/`shared_or_local_dir`
  経由に修正し、読んだコピーのパスを標準出力に印字。
- 既に対応済み(shared_or_local または同等の解決器): 9件。
- 対象外(収集/記録・本体/監視・鏡写し無し): 収集系 約30本 + 本体/監視系 約11本 + 鏡写し無し2本。
- データファイルの変更・コミットは行っていない。テストは `PYTHONPATH=src python -m pytest -q` を実行
  (結果は作業ログ参照)。
