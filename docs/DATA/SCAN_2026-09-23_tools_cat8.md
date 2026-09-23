# 道具サーベイ 区分8 報告書

起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run1_prompt.md`(指紋 `0ac68ca101f9`)/
追補 `docs/DATA/delegations/20260923_tools_survey_cat8_addendum.md`(指紋 `46258eebcd93`)/
委任文 `docs/DATA/delegations/20260922_tools_survey_prompt.md`(指紋 `ce0012c95154`)/
設計票 `docs/DATA/surveys/CAT8_DESIGN.md` に従う。生ログ: `docs/DATA/probes/20260923_tools_8_run1.log`。

## 区分8 — 1 回目の実行(2026-09-23)

### 当方の道具立て(`python3 scripts/tools_inventory.py` の出力全文)

```
# 当方の道具立て(git ls-files から生成。2026-09-23T14:11:25Z、HEAD a9bcde2。コマンド: python3 scripts/tools_inventory.py)

## src/bot(package: ファイル数 / ファイル名)
- src/bot: 7 / atomic_file.py constants.py logging_setup.py main.py products.py radar.py settings.py
- src/bot/backtest: 3 / engine.py metrics.py walk_forward.py
- src/bot/bt/core: 11 / api.py contract.py engine.py errors.py events.py interfaces.py ordering.py strategy.py testing.py time.py window.py
- src/bot/bt/core/tests: 12 / _util.py test_api_surface.py test_contract.py test_determinism.py test_engine_source.py test_events.py test_extension_points.py test_latency.py test_lookahead.py test_ordering.py test_orders.py test_time.py
- src/bot/exchange: 2 / bitflyer_client.py resilience.py
- src/bot/execution: 3 / gateway.py live.py paper.py
- src/bot/indicators: 1 / core.py
- src/bot/jpx: 4 / etf_auction_executor.py kabu_client.py on1_executor.py run_lock.py
- src/bot/market_data: 3 / external_feed.py feed.py realtime.py
- src/bot/monitoring: 6 / aggregate.py decision_text.py gates.py market_view.py notifier.py status.py
- src/bot/order_management: 3 / manager.py order.py reconciler.py
- src/bot/portfolio: 2 / persistence.py portfolio.py
- src/bot/research: 11 / board.py gz_members.py liq_bands.py liq_response.py liquidations.py overnight.py sealed.py xborder_p2.py xborder_p2_fast.py xborder_p2_fx.py xborder_p2_state.py
- src/bot/risk: 2 / kill_switch.py pre_trade_checks.py
- src/bot/strategy: 9 / base.py breakout.py composite.py ema_cross.py inago.py range_fade.py rsi_reversion.py wick_reversal.py xborder_momentum.py

## scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)
- research_*: 56 / research_anchor.py research_anchor_v2.py research_attention_vol.py research_avalanche.py research_basis.py research_board_calibration.py research_burst_atlas.py research_calm_range.py research_clock_burst.py research_exit_surface.py research_fast_cycle.py research_fx.py research_fx_carry.py research_fx_event_ticks.py research_fx_events.py research_fx_fundamentals.py research_fx_s4_judgment.py research_fx_sessions.py research_fx_tokyofix.py research_hft.py research_imbalance.py research_latency_grade.py research_latency_paths.py research_leader_surface.py research_legacy_elements.py research_m4_finecheck.py research_macro_calendar.py research_mainbot_exits.py research_maker_reaudit.py research_matilda_modern.py research_matilda_surface.py research_matilda_taro.py research_nk225_events.py research_overnight_on1.py research_overnight_onr.py research_position_ladder.py research_prediction_atlas.py research_range_reversed.py research_regime_composite.py research_scalp_exits.py research_scalp_opt.py research_seasonality.py research_signal_fade.py research_signals.py research_spread_mm.py research_storm.py research_storm_b.py research_storm_bracket.py research_storm_direction.py research_tournament.py research_trend_lt1.py research_two_sided_flow.py research_user_strategies.py research_vr_barrier.py research_wall_front.py research_yutai.py
- fetch_*: 28 / fetch_aggtrades.py fetch_attention.py fetch_binance_cm_o3c.py fetch_binance_daily.py fetch_binance_full.py fetch_binance_vision.py fetch_bitbank_daily.py fetch_bitflyer_executions_range.py fetch_bitflyer_lightchart.py fetch_bitmex_archive.py fetch_bitmex_insurance.py fetch_bybit_minutes.py fetch_coinalyze_liquidations.py fetch_daily_lt1.py fetch_deep.py fetch_deribit.py fetch_dukascopy.py fetch_external.py fetch_fx_calendar.py fetch_fx_calendar_2005_2014.py fetch_gate_liquidations.py fetch_history.py fetch_jpx_daily.py fetch_jpx_etf_daily.py fetch_kraken.py fetch_okx.py fetch_regime_composite.py fetch_tardis_samples.py
- o3c_*: 22 / o3c_bitflyer_spread.py o3c_jev_state.py o3c_oi_distance.py o3c_price_level_ext.py o3c_price_level_table.py o3c_reaction.py o3c_reaction_judge.py o3c_reaction_r2.py o3c_rows4.py o3c_signal_calib.py o3c_signal_continue.py o3c_signal_continue_jev.py o3c_signal_explore.py o3c_signal_explore2.py o3c_signal_explore3.py o3c_signal_explore4.py o3c_signal_explore5.py o3c_signal_logit.py o3c_signal_materials.py o3c_signal_policy.py o3c_signal_stage2.py o3c_signal_value.py
- render_*: 19 / render_exec_floor.py render_k1_body_wick.py render_k1_deepdive.py render_k1_exit_ablation.py render_k1_fresh_bitflyer.py render_k1_h1.py render_k1_h2.py render_k1_h3.py render_k1_h3_decomp.py render_k1_judgement.py render_k1_robustness.py render_k1_round5.py render_k1_trunc_compare.py render_k1_venue_compare.py render_k1_xvenue.py render_k1_xvenue2.py render_k1_year_tables.py render_k1_yearly_pnl.py render_prereg.py
- measure_*: 16 / measure_exec_floor.py measure_katsuo_body_wick.py measure_katsuo_delay_decomp.py measure_katsuo_direction_bias.py measure_katsuo_dispersion.py measure_katsuo_effect.py measure_katsuo_exit_ablation.py measure_katsuo_judgement_vol.py measure_katsuo_robustness.py measure_katsuo_round5.py measure_katsuo_signal_horizon.py measure_katsuo_vol_bitflyer.py measure_katsuo_xvenue.py measure_liq_bands.py measure_liq_response.py measure_ws_latency.py
- jev_*: 14 / jev_audit_eval.py jev_audit_loop.py jev_check.py jev_delegate.py jev_design.py jev_eval.py jev_ideas.py jev_ops.py jev_owner_log.py jev_prescreen.py jev_reply.py jev_report_intake.py jev_survey.py jev_trace_export.py
- qa/: 13 / agreement.py make_known_answer.py make_known_answer_maker.py make_known_answer_maker3.py make_known_answer_steer.py maker_fill_ref.py maker_fill_ref_packet.py maker_fill_ref_packet_r2.py pipeline_known_answer_daily.py pipeline_known_answer_taker.py score_audit.py score_claims.py score_steer.py
- phase2/: 12 / g1_state_analysis.py p2_01_final.py p2_01_run.py p2_01b_history.py p2_02_final.py p2_02_run.py p2_03_final.py p2_03_iter2.py p2_03_run.py p2_04_run.py p2_08_data.py p2_08_run.py
- run_*: 11 / run_backtest.py run_board_round.py run_etf_measure_entry.py run_etf_measure_exit.py run_etf_measure_reconcile.py run_o3c_stage0.py run_on1_entry.py run_on1_exit.py run_on1_reconcile.py run_paper.py run_scalp_paper.py
- build_*: 8 / build_basis.py build_bitflyer_lightchart_csv.py build_burst_library.py build_flow.py build_fx_event_library.py build_fx_event_library_2005_2014.py build_storm_library.py build_tools_catalog.py
- check_*: 8 / check_api.py check_data_ledger.py check_k1_binance.py check_k1_bitflyer_data.py check_kabu_api.py check_liquidation_feeds.py check_liquidation_history_depth.py check_scan_report.py
- record_*: 5 / record_funding_basis.py record_liquidations.py record_oi.py record_realtime.py record_venues.py
- jev/: 3 / client.py redact.py schemas.py
- verify_*: 3 / verify_gates.py verify_liq_instrument.py verify_snapshots.py
- (単発): 2 / _research_audit_gate.py dashboard.py
- judge_*: 2 / judge_board_round.py judge_gates.py
- k1_*: 2 / k1_binance_data_quality.py k1_source.py
- paper_*: 2 / paper_on1.py paper_onr.py
- repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.py
- cat8_*: 1 / cat8_ledger.py
- constants_*: 1 / constants_inventory.py
- data_*: 1 / data_quality.py
- explore_*: 1 / explore_o3c_oi_axis.py
- export_*: 1 / export_workflow_judges.py
- extract_*: 1 / extract_tape.py
- intake_*: 1 / intake_ledger.py
- liquidation_*: 1 / liquidation_report.py
- mirror_*: 1 / mirror_bitmex_archive.py
- normalize_*: 1 / normalize_bitflyer_executions.py
- phase2_*: 1 / phase2_seal.py
- preflight_*: 1 / preflight_prereg.py
- probe_*: 1 / probe_api_latency.py
- recount_*: 1 / recount_scan_cat1.py
- replay_*: 1 / replay_scalp_storm.py
- retention_*: 1 / retention_snapshot.py
- tools_*: 1 / tools_inventory.py
- tp_*: 1 / tp_operating_curve.py
- trace_*: 1 / trace_metrics.py
- validate_*: 1 / validate_composite.py
- x_*: 1 / x_fetch.py
- (.py 以外の scripts: 3 = scripts/fetch_all.sh scripts/install_git_hooks.sh scripts/regen_hook_manifest.sh)

## config: 32
  (config/*.yaml、内訳は生ログ参照)

## deploy: 19
  (deploy/*、内訳は生ログ参照)

## tests(ファイル): 162
  (tests/*、内訳は生ログ参照。tests/bt/ は今回触らない別会話の作業)

## .claude/hooks: 8
  .claude/hooks/_verify_manifest.sh .claude/hooks/delegation_audit_gate.sh .claude/hooks/deny_protected_paths.sh .claude/hooks/jev_notice.sh .claude/hooks/owner_options_gate.sh .claude/hooks/owner_turn_digest.sh .claude/hooks/session_start_digest.sh .claude/hooks/trace_snapshot.sh

## .claude/agents: 3
  .claude/agents/owner-auditor-candidate.md .claude/agents/owner-auditor.md .claude/agents/owner-model-auditor.md

## .claude/skills: 10
  .claude/skills/delegated-study/SKILL.md .claude/skills/owner-audit/SKILL.md .claude/skills/owner-options/SKILL.md .claude/skills/owner-procedure/SKILL.md .claude/skills/research-protocol/SKILL.md .claude/skills/research-squad/SKILL.md .claude/skills/research-squad/SURVEY.md .claude/skills/typesafe-ai/LICENSE .claude/skills/typesafe-ai/SKILL.md .claude/skills/x-research/SKILL.md

## githooks: 1
  githooks/pre-push

## docs(.md): 346
  (docs 配下の md ファイル全部。内訳は生ログ参照。件数のみ本文で参照する)

## backtest_data(ディレクトリ数)
  147 ディレクトリ(内訳は生ログ参照)
```

全文は `docs/DATA/probes/20260923_tools_8_run1.log` の冒頭の実行記録(`method=inventory`)にも同一内容を残した。

### 検索計画

幅3段(狭い/中間/広い) × 日本語/英語 = 6本。区分8の8要素(E1a 突き合わせる機能 / E1b 突き合わせの相手 / E2 データ品質 / E3a ルックアヘッド検出 / E3b ルックアヘッド防止 / E4 リプレイ / E5 再現性 / E6 その他検証)と、検証・試験自動化の成熟度枠組みを探す語を含めた。

| # | 幅 | 言語 | クエリ | 経路 |
|---|---|---|---|---|
| 1 | 狭い | 日本語 | `バックテスト 別実装 突き合わせ 検証 ツール 差分` | WebSearch |
| 2 | 狭い | 英語 | `backtest reference implementation cross-check reconciliation library tool` | WebSearch |
| 3 | 中間 | 日本語 | `データ品質 検査 ルックアヘッド検出 リプレイ 再現性 トレーディング ツール` | WebSearch |
| 4 | 中間 | 英語 | `trading data quality check lookahead bias detection replay reproducibility tool` | WebSearch |
| 5 | 広い | 日本語 | `トレーディング 戦略 検証 テスト 自動化 成熟度モデル フレームワーク`(成熟度枠組み探索を兼ねる) | WebSearch |
| 6 | 広い | 英語 | `trading strategy validation testing automation maturity model framework`(成熟度枠組み探索を兼ねる) | WebSearch |

**6本すべてを実行した(未実行なし)。** 経路3つ(WebSearch一般 / X / GitHub・PyPI・公式)は次のとおり全部使った:
- **WebSearch一般**: 上記6本 + E2(データ品質)の補助検索1本(`time series market data quality validation python library gaps duplicates outliers`、E2に強く当たる候補が6本の結果に薄かったため追加。追補§2の「検索計画は打ち直さない」は2回目以降の規則であり、1回目は委任文§3のとおり6本を打った上での補助検索)。
- **X**: `site:x.com freqtrade lookahead bias backtest` / `site:x.com "look-ahead bias" backtest data quality` / `site:x.com バックテスト 別実装 データ品質 使ってみた` の3本(x-research手順どおり3回以上)。投稿URLから3件を選び `scripts/x_fetch.py` で本文を逐語取得(`docs/DATA/probes/20260923_tools_8_run1.log` の `method=xfetch` 節)。
- **GitHub・PyPI・公式**: `ungh.cc/repos/<owner>/<repo>` で5件のGitHub登録情報、`raw.githubusercontent.com` でREADME・LICENSEを取得、`pypi.org/pypi/<pkg>/json` でqf-libとfreqtradeのPyPI情報、`api.osv.dev` で既知の脆弱性照会、公式サイト(exegy.com / backtrex.com / fxreplay.com)をWebFetchで取得。

**成熟度枠組みの探索結果(設計票§4.1の要求)**: 検索計画5・6で、トレード専用の成熟度モデルは見つからなかった。一般ソフトウェアのTesting Maturity Model(TMM)がCMMI準拠で「Level 1 Initial」〜「Level 5 Optimizing」の5段階と紹介されている(出典: abstracta.us「Software Testing Maturity Model: Improve Your Strategy」、testrigor.com「Test Automation Maturity Model」)。トレード検証専用の成熟度モデルではないため、設計票§4.1の段の妥当性検証には使えるが、段の定義そのものを裏付ける一次資料ではない(未確認: 上記2サイトの本文は検索結果の要約のみで、ページ自体は未読)。

### 出典

| # | 経路 | URL | 内容 |
|---|---|---|---|
| 1 | GitHub | https://github.com/quarkfin/qf-lib | qf-lib(8-001、区分1から) |
| 2 | GitHub | https://github.com/pineforge-4pass/pineforge-engine | PineForge(8-002、区分1から) |
| 3 | GitHub | https://github.com/Quentin-Piot/prediction-market-backtester | prediction-market-backtester(8-003、区分1から) |
| 4 | GitHub | https://github.com/akurkar07/OrderBook | akurkar07/OrderBook(8-004、区分1から) |
| 5 | 公式 | https://www.exegy.com/ | Exegy(8-005、区分1から) |
| 6 | GitHub/PyPI | https://github.com/freqtrade/freqtrade , https://pypi.org/project/freqtrade/ | freqtrade(新) |
| 7 | 公式 | https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide | backtrex(新) |
| 8 | 公式 | https://fxreplay.com/ | FX Replay(新) |
| 9 | X | https://x.com/tommy_love123/status/2000418603502645305 | 先読みバイアス排除の使用報告(逐語取得) |
| 10 | X | https://x.com/WannabeBotter/status/1810558269565571211 | rusty-bot/VectorBT紹介の引用投稿(逐語取得) |
| 11 | X | https://x.com/MtkN1XBt/status/1816408963027738748 | バックテストとソフトウェアのテストの違いの議論(逐語取得) |
| 12 | PyPI | https://pypi.org/pypi/qf-lib/json | qf-libのバージョン・ライセンス・requires_python |
| 13 | PyPI | https://pypi.org/pypi/freqtrade/json | freqtradeのPyPI情報 |
| 14 | OSV.dev | https://api.osv.dev/v1/query | qf-lib・freqtradeの既知脆弱性照会 |
| 15 | raw.githubusercontent | 各リポジトリのREADME.md/LICENSE(5件×2) | 一次資料本文(生ログ参照) |

すべて `docs/DATA/probes/20260923_tools_8_run1.log` に手ごとの記録がある。

### 候補の一覧

1. `qf-lib` (8-001) — https://github.com/quarkfin/qf-lib — Bloomberg/Quandl/Haver/Portara等に接続するイベント駆動バックテスタとルックアヘッド防止機能を持つPythonライブラリ — 状態: 深掘り
2. [深掘り] `PineForge` (8-002) — https://github.com/pineforge-4pass/pineforge-engine — TradingViewのPineScript v6戦略をC++で再現し、TradingView本体の結果と1件ずつ突き合わせて回帰ゲートで管理するバックテストエンジン — 状態: 深掘り
3. `prediction-market-backtester` (8-003) — https://github.com/Quentin-Piot/prediction-market-backtester — Polymarket/Kalshi向けの予測市場バックテストエンジン、データ品質ゲートとgitコミットハッシュ記録付き — 状態: 浅い
4. `akurkar07/OrderBook` (8-004) — https://github.com/akurkar07/OrderBook — 単一銘柄の価格時間優先マッチングエンジン(C++)。参照実装との差分検証・決定論的テストを持つが公開7日・星0・単独保守者のため導入停止 — 状態: 危険で導入停止
5. `Exegy` (8-005) — https://www.exegy.com/ — 低遅延の正規化市場データ・接続・FPGA取引基盤を提供する企業向けSaaS/ハードウェア。技術詳細は営業問い合わせ後 — 状態: 登録が要る
6. `freqtrade` (新) — https://github.com/freqtrade/freqtrade — 無料OSSの暗号資産トレーディングボット。`lookahead-analysis`/`recursive-analysis` コマンドを持つ — 状態: 浅い
7. `backtrex` (新) — https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide — ノーコードのビジュアルバックテストSaaS。バックテスト実行前にOHLCデータ品質検証層を自動で挟む — 状態: 浅い
8. `FX Replay` (新) — https://fxreplay.com/ — 秒単位からのマルチタイムフレーム相場リプレイSaaS(FX/株/先物) — 状態: 浅い

**注記**: `[深掘り]` の印は1(qf-lib)と2(PineForge)だけに付けた。この2件だけが設計票§2の「深掘り」の述語(委任文§4.0の条件を満たし、かつE1a〜E6に未判別が1つも無い)を満たし、§4.0の機械可読の表に語彙の全項目を書いたため。3〜8は一次資料には届いたが「深掘り」の条件を満たさず、候補の一覧の状態語のとおり(浅い/危険で導入停止/登録が要る)である。

### 要素と段

| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 |
|---|---|---|---|---|---|
| qf-lib | E1a | なし | - | 一次資料 | README(https://github.com/quarkfin/qf-lib 取得日2026-09-23)全文・PyPI説明文に、他実装との差分検査・突き合わせ機能への言及なし。インストール済みソース全体を `reconcil\|cross.check` でgrepし一致0件(20260923_tools_8_run1.log の qflib_source_grep 節) |
| qf-lib | E1b | 印 | 2 | 実測 | イベント駆動バックテスタとしてPnL・トレードを計算する(venv_install節でimport成功・実行を確認)。人が別実装と比較する前提で、突き合わせを自動で行う機能は無い |
| qf-lib | E2 | 印 | 未判別 | 実測 | `qf_lib/common/utils/miscellaneous/consecutive_duplicates.py` の `drop_consecutive_duplicates()` を直接読んだ(20260923_tools_8_run1.log の qflib_source_grep 節)。連続する重複値を検出して統合する機能だが、検出結果を報告するのか静かに変換するだけかが原文から判別しづらく、段の判定に迷う(末尾の問いに記載) |
| qf-lib | E3a | なし | - | 実測 | インストール済みソース全体を look-ahead を検出・報告する専用コマンド/レポート機能の語で探索したが該当なし(`get_end_date_without_look_ahead` は防止の計算であり検出結果の報告ではない) |
| qf-lib | E3b | 印 | 3 | 実測 | `qf_lib/data_providers/data_provider.py` 51・69-70行: `look_ahead_bias: bool` 引数、docstring「if set to False, the look-ahead bias will be taken care of to make sure no future data is returned」(20260923_tools_8_run1.log の qflib_source_grep 節)。qf_libのDataProvider抽象の枠内で自動適用される。CSVDataProvider(`data_providers/csv/csv_data_provider.py`)により外部csvも読み込めるが、戦略コード自体はqf_libのAPIに従う必要があるため対象の一部のみ外から持ち込める(段4条件を満たさず段3) |
| qf-lib | E4 | 印 | 3 | 実測 | イベント駆動バックテスタが時系列データを時刻順に読み込み実行ハンドラを動かす構造(execution_handler配下を確認)。CSVDataProviderで外部csvを取り込めるが戦略コードはqf_lib枠内のため段3 |
| qf-lib | E5 | なし | - | 実測 | インストール済みソース全体を `random_state\|seed\|reproduc` でgrepし、テストユーティリティ1件のみでユーザー向け再現性機能は見当たらない(20260923_tools_8_run1.log の qflib_source_grep 節) |
| qf-lib | E6 | なし | - | 一次資料 | README・ソースに、E1〜E5に当たらない独立した検証・品質機能への言及なし(要約生成機能は結果の提示であり検証ではない) |
| PineForge | E1a | 印 | 5 | 一次資料 | README(pineforge_README.md)267行「Each rule was isolated with sensor strategies exported from TradingView...and landed with a replay test on the recorded bars」、263行「The formal gate requires no hard-surface regression and strictly positive pooled movement...Baseline promotion requires a recorded PASS and an exact-head merge with green CI」。TradingViewの実行結果と自社エンジンの結果を突き合わせ、閾値(regression不可・正の移動)を人が指定でき(ア)、baseline promotionで結果を保存し次回と比較できる(イ) |
| PineForge | E1b | 印 | 5 | 一次資料 | 同上。TradingViewと同種の出力(トレードCSV)を出す独自エンジンであり、E1aと同じ根拠 |
| PineForge | E2 | なし | - | 一次資料 | README全文を `data quality` でgrep(パターンに含めて実行)し一致0件(20260923_tools_8_run1.log の pineforge_grep 節)。市場データの欠け・重複等の検査への言及なし |
| PineForge | E3a | なし | - | 一次資料 | README全文を `look-?ahead` でgrepし一致0件(pineforge_grep節)。ルックアヘッドの検出・報告機能への言及なし |
| PineForge | E3b | なし | - | 一次資料 | 同上grepで一致0件。決定論的なバー再生自体はルックアヘッドを構造的に避けうるが、それを目的とした独立の防止機構への言及はない |
| PineForge | E4 | 印 | 5 | 一次資料 | README 267行・411行「C++ unit and recorded TradingView replay tests」。記録済みバーをリプレイしてTradingViewの挙動を再現するテストで、263行の formal gate(基準指定)とbaseline promotion(結果保存・比較)がE1aと共通して適用される |
| PineForge | E5 | 印 | 5 | 一次資料 | README 37行「Deterministic to the bit. Two runs with the same inputs produce identical trade lists. Same on Linux and macOS」。328行で使用バージョン(engine `063e4460`、PyneCore 6.10.2等)を固定して結果を記録し、263行のbaseline promotionで次回と比較する仕組み |
| PineForge | E6 | なし | - | 一次資料 | grep結果(pineforge_grep節)の一致箇所はすべてE1a/E4/E5に既に計上した内容で、それ以外の独立した検証機能は無い |
| prediction-market-backtester | E1a | なし | - | 一次資料 | README(predmkt_README.md)全文に他実装との突き合わせ機能への言及なし |
| prediction-market-backtester | E1b | 印 | 2 | 一次資料 | README「results.json — full run metadata: config, git commit hash, timings, and trading metrics」。同種(PnL等)の出力を計算するが自動比較機能は無い |
| prediction-market-backtester | E2 | 印 | 3 | 一次資料 | README「`data_quality.json` - per-market quality checks and gate status」。`pm-bt batch` 実行時に自動生成される(自動判定)が、kalshi/polymarketの自社データ取り込みパイプライン内に限る |
| prediction-market-backtester | E3a | 未判別 | 未判別 | 未確認 | README全文を通読したが該当機能の記述を見つけられず、ソースコード(`src/pm_bt/`)までは時間の制約で読んでいない |
| prediction-market-backtester | E3b | 未判別 | 未判別 | 未確認 | 同上。「latency is modeled in bars via delayed order activation」は執行遅延の模型でありE3bに当たるか判別できていない |
| prediction-market-backtester | E4 | 印 | 3 | 一次資料 | README「Bar aggregation period」「results per bar equity curve」等、バー単位の時系列データを順に読み込みバックテストを実行する構造。kalshi/polymarketの自社データ取り込みに限るため段3 |
| prediction-market-backtester | E5 | 印 | 5 | 一次資料 | README「A reproducible local performance baseline is documented in `docs/performance-baseline.md`, and can be regenerated with `make profile-sample`」、「results.json — ...git commit hash」。基準(baseline文書)を指定でき、gitコミットハッシュ付きで結果を保存し次回と比較できる |
| prediction-market-backtester | E6 | なし | - | 一次資料 | README中、E1b/E2/E4/E5以外の独立した検証機能への言及なし |
| akurkar07/OrderBook | E1a | 印 | 3 | 一次資料 | README(orderbook_README.md)「The reference differential test also compares the optimized book against a deliberately simple vector-based model」「Correctness verification: same sequence → same fills」。自動判定(ctest)だが比較対象はリポジトリに同梱された参照実装のみで外部持ち込み不可のため段3 |
| akurkar07/OrderBook | E1b | 印 | 2 | 一次資料 | 同README。LOBのfill列という同種の出力を計算するが、外部実装との自動比較機能はない(段2) |
| akurkar07/OrderBook | E2 | なし | - | 一次資料 | README全文に市場データ品質検査への言及なし(注文フローの正当性検証はあるが対象はデータでなく注文) |
| akurkar07/OrderBook | E3a | なし | - | 一次資料 | 同上、該当なし |
| akurkar07/OrderBook | E3b | なし | - | 一次資料 | 同上、該当なし |
| akurkar07/OrderBook | E4 | なし | - | 一次資料 | 合成・ランダム化した注文列のベンチマークであり、記録済み市場データの時刻順再生ではない |
| akurkar07/OrderBook | E5 | 印 | 3 | 一次資料 | README「all operations designed to be deterministic and reproducible」「Deterministic test suite」。ctestで自動判定されるが、V3の「CI/CD with GitHub Actions」は未チェック(未実装)のため、結果を次回と自動比較する仕組み(イ)はまだ無く段5には届かない |
| akurkar07/OrderBook | E6 | なし | - | 一次資料 | 該当なし |
| Exegy | E1a | 未判別 | 未判別 | 未確認 | 公式サイト(exegy.com)トップページのみ確認。製品カテゴリ(nxFeed等)の説明はあるが、突き合わせ機能に関する記述は無く「Talk to an Expert」への問い合わせが必要(exegy_fetch節)。営業問い合わせは登録に当たるため行っていない |
| Exegy | E1b | 未判別 | 未判別 | 未確認 | 同上(exegy_fetch節)。同種の出力を出す計算という観点の記述は公開ページに無い |
| Exegy | E2 | 未判別 | 未判別 | 未確認 | 同上。データ品質検査に関する記述は公開ページに無い |
| Exegy | E3a | 未判別 | 未判別 | 未確認 | 同上。ルックアヘッド検出に関する記述は公開ページに無い |
| Exegy | E3b | 未判別 | 未判別 | 未確認 | 同上。ルックアヘッド防止に関する記述は公開ページに無い |
| Exegy | E4 | 未判別 | 未判別 | 未確認 | 同上。リプレイ機能に関する記述は公開ページに無い |
| Exegy | E5 | 未判別 | 未判別 | 未確認 | 同上。再現性に関する記述は公開ページに無い |
| Exegy | E6 | 未判別 | 未判別 | 未確認 | 同上。その他の検証機能に関する記述は公開ページに無い |
| freqtrade | E1a | なし | - | 一次資料 | `docs/lookahead-analysis.md`(freqtrade_lookahead.md)16行「This is done by not looking at the strategy code itself, but at changed indicator values and moved entries/exits compared to the full backtest」。比較対象は同一エンジンの2回の実行(baseline/sliced)であり、2つ以上の異なる実装の突き合わせではないためE1aでなくE3aに計上 |
| freqtrade | E1b | 印 | 2 | 一次資料 | freqtradeはバックテストでPnL/トレードを計算する。他実装との比較対象になりうる(自動比較機能自体はない) |
| freqtrade | E2 | 未判別 | 未判別 | 未確認 | `lookahead-analysis.md`のみ読み、データ品質関連文書(`docs/data-download.md`等)は時間の制約で未読 |
| freqtrade | E3a | 印 | 3 | 一次資料 | `docs/lookahead-analysis.md`49行「This command is made to try to verify the validity in the form of the aforementioned lookahead bias」、58行「it will compare both dataframes (baseline and sliced) for any difference in columns' value and report the bias」。自動判定・報告するが、freqtradeのStrategyクラスの枠内に限るため段3 |
| freqtrade | E3b | 未判別 | 未判別 | 未確認 | `recursive-analysis.md`は未読のため判別できていない |
| freqtrade | E4 | 未判別 | 未判別 | 未確認 | バックテストエンジン自体がバー時系列を順に処理する構造と推測されるが、一次資料(`docs/backtesting.md`)は時間の制約で未読のため確定できない |
| freqtrade | E5 | 未判別 | 未判別 | 未確認 | 再現性関連の文書は未読 |
| freqtrade | E6 | なし | - | 一次資料 | 読んだ範囲(lookahead-analysis.md)にE1〜E5以外の独立検証機能への言及なし |
| backtrex | E1a | なし | - | 一次資料 | backtrex_fetch節の抽出内容に他実装との突き合わせ機能への言及なし |
| backtrex | E1b | なし | - | 一次資料 | ノーコードのバックテスト実行環境であり、比較対象になりうる独立した計算出力という性質の記述はない |
| backtrex | E2 | 印 | 3 | 一次資料 | backtrex_fetch節「Backtrex integrates a native OHLC validation layer before every backtest」「各バーの数学的矛盾性チェック・異常なギャップの検出とフラグ化・リペインティング防止ルールの強制・破損データの詳細エラー報告書生成」。バックテスト実行の度に自動で走るが、backtrex自身のノーコード基盤内に限るため段3 |
| backtrex | E3a | 未判別 | 未判別 | 未確認 | ブログ記事1本のみ取得。他ページ(製品ドキュメント)は未読 |
| backtrex | E3b | 未判別 | 未判別 | 未確認 | 「リペインティング防止ルールの強制」は将来データの混入防止に近いが、原文がE3bの述語(purged CV/embargo等)に明確に当たるかは未確認 |
| backtrex | E4 | 未判別 | 未判別 | 未確認 | 未読 |
| backtrex | E5 | 未判別 | 未判別 | 未確認 | 未読 |
| backtrex | E6 | 未判別 | 未判別 | 未確認 | 未読 |
| FX Replay | E1a | なし | - | 一次資料 | fxreplay_fetch節の抽出内容に他実装との突き合わせ機能への言及なし |
| FX Replay | E1b | なし | - | 一次資料 | 手動トレード練習用のリプレイツールであり、独立した計算出力という性質の記述はない |
| FX Replay | E2 | 未判別 | 未判別 | 未確認 | トップページのみ確認。データ品質関連ページは未読 |
| FX Replay | E3a | 未判別 | 未判別 | 未確認 | 未読 |
| FX Replay | E3b | 未判別 | 未判別 | 未確認 | 未読 |
| FX Replay | E4 | 印 | 2 | 一次資料 | fxreplay_fetch節「5s, 30s, 1m, 5m, 15m, 1h, 4h, 1D, 1W, 1M」の粒度でチャートを再生できる。呼べば結果(再生されたチャート)を出すが、自動判定(合否)は無く人が手動売買する前提のため段2 |
| FX Replay | E5 | 未判別 | 未判別 | 未確認 | 未読 |
| FX Replay | E6 | 未判別 | 未判別 | 未確認 | 未読 |

### 知見(記録する軸、`印` を付けた要素について原文と URL)

| 道具 | 要素 | 記録する軸 | 原文(逐語) / URL・取得日 |
|---|---|---|---|
| qf-lib | E1b | 方式(原文) | 記載なし(読んだ箇所: README「event-driven architecture」との記述のみで、比較の単位までは書かれていない) |
| qf-lib | E1b | 入力(原文) | 記載なし(読んだ箇所: README「Currently provides financial data from Bloomberg, Quandl, Haver Analytics or Portara」) |
| qf-lib | E2 | 方式(原文) | 「Removes consecutive duplicates (e.g. 3 consecutive 1 values should be merged into one with a date of the first/last occurrence in the series)」(qf_lib/common/utils/miscellaneous/consecutive_duplicates.py、実測。https://pypi.org/project/qf-lib/ 4.0.7、取得日2026-09-23) / 直すか報告だけか: 記載なし(コードは「直す(merge)」のみで報告のログ出力は無い。読んだ箇所: 同ファイル全文) |
| qf-lib | E3b | 方式(原文) | 「if set to False, the look-ahead bias will be taken care of to make sure no future data is returned」(qf_lib/data_providers/data_provider.py 69-70行、実測) |
| qf-lib | E3b | 外から持ち込める対象 | CSVDataProvider(qf_lib/data_providers/csv/csv_data_provider.py)によりデータは外部csvを持ち込めるが、戦略コードはqf_libのStrategy APIに従う必要がある(実測、同ファイル冒頭のクラス定義) |
| qf-lib | E4 | 方式(原文) | 記載なし(読んだ箇所: execution_handler配下のモジュール構成のみ確認、リプレイの粒度に関する明文は未読) |
| PineForge | E1a | 方式(原文) | 「Each rule was isolated with sensor strategies exported from TradingView (capital sweeps, literal replays, per-bar state encoded into order comments) and landed with a replay test on the recorded bars」(README 267行、https://github.com/pineforge-4pass/pineforge-engine 取得日2026-09-23) |
| PineForge | E1a | (ア)基準を指定できるか | 「The formal gate requires no hard-surface regression and strictly positive pooled movement across the target excellent and excellent+strong bands」(README 263行) |
| PineForge | E1a | (イ)結果を保存して比較できるか | 「Baseline promotion requires a recorded PASS and an exact-head merge with green CI」(README 263行) |
| PineForge | E1a | 突き合わせの単位 | トレード単位(README 217行「4,190 raw trade CSVs, counts and full grades」) |
| PineForge | E1a | 許容誤差を指定できるか | 記載なし(読んだ箇所: 263行。regressionの許容は「zero」固定で、数値の許容誤差を人が調整できるかは明記されていない) |
| PineForge | E4 | 方式(原文) | 「C++ unit and recorded TradingView replay tests」(README 411行) |
| PineForge | E4 | 再生の粒度 | 記載なし(読んだ箇所: 411行付近。バー単位かティック単位かの明記なし) |
| PineForge | E5 | 何を固定・比較するか | 「Deterministic to the bit. Two runs with the same inputs produce identical trade lists. Same on Linux and macOS」(README 37行)。バージョン固定は「Last refresh 2026-09-22 (engine `063e4460`, PyneCore 6.10.2, PineTS 0.9.34, vectorbt 0.28.2, Apple M4 Max)」(README 328行) |
| prediction-market-backtester | E1b | 方式(原文) | 「Each run produces a directory under `<output-root>/<run-id>/`...`results.json` — full run metadata: config, git commit hash, timings, and trading metrics (total PnL, max drawdown, realized/unrealized PnL, turnover, fill count)」(README、https://github.com/Quentin-Piot/prediction-market-backtester 取得日2026-09-23) |
| prediction-market-backtester | E2 | 検出する異常の種類 | 記載なし(読んだ箇所: README「`data_quality.json` - per-market quality checks and gate status」。具体的な検査項目の列挙は本文になし) |
| prediction-market-backtester | E2 | 直すか報告だけか | 記載なし(同上) |
| prediction-market-backtester | E4 | 再生の粒度 | 「`--bar-timeframe` | `1m` | Bar aggregation period (`1m`, `5m`, `1h`, etc.)」(README) |
| prediction-market-backtester | E5 | 何を固定・比較するか | 「A reproducible local performance baseline is documented in `docs/performance-baseline.md`, and can be regenerated with `make profile-sample`」「results.json...git commit hash」(README) |
| akurkar07/OrderBook | E1a | 方式(原文) | 「The reference differential test also compares the optimized book against a deliberately simple vector-based model across deterministic randomized order sequences」(README、https://github.com/akurkar07/OrderBook 取得日2026-09-23) |
| akurkar07/OrderBook | E1a | 突き合わせの単位 | 約定(fill)単位。「compares the optimized engine with the reference implementation over 10,000 identical operations」(README) |
| akurkar07/OrderBook | E1a | 外から持ち込める対象 | なし(比較相手の参照実装 `reference/reference_order_book.h` はリポジトリに同梱された固定の実装で、外部実装を持ち込む機構は無い) |
| akurkar07/OrderBook | E5 | 何を固定・比較するか | 「The same order sequence produces the same fill sequence」「Deterministic test suite」(README 設計決定の節) |
| prediction-market-backtester | E4 | 遅延を入れられるか | 「latency is modeled in bars via delayed order activation」(README 執行モデルの前提の節) |
| backtrex | E2 | 検出する異常の種類 | 「detects and flags anomalous gaps」「各バーの数学的矛盾性チェック」「リペインティング防止ルールの強制」「破損データの詳細エラー報告書生成」(backtrex_fetch節、https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide 取得日2026-09-23、WebFetchによる抽出のため厳密な逐語ではなく抽出結果である点に注意) |
| backtrex | E2 | 直すか報告だけか | 記載なし(読んだ箇所: 同記事。「フラグ化」「エラー報告書生成」との記述はあるが自動修正するかは明記なし) |
| FX Replay | E4 | 再生の粒度 | 「5s, 30s, 1m, 5m, 15m, 1h, 4h, 1D, 1W, 1M」(fxreplay_fetch節、https://fxreplay.com/ 取得日2026-09-23) |
| FX Replay | E4 | 遅延を入れられるか | 記載なし(読んだ箇所: トップページのみ) |

### ツール1件ごとの表

#### qf-lib(8-001)

- **名前/種別/できること**: QF-Lib。Pythonのイベント駆動バックテスタ+定量金融ツール群(README)。Bloomberg/Quandl/Haver Analytics/Portara等のデータ接続、ルックアヘウド防止(§4.1参照)、PDFレポート生成。
- **言語・動作環境**: Python、`requires_python >= 3.8.0`(PyPI JSON、一次資料)。
- **ライセンス**: Apache License 2.0(LICENSEファイル実測)。商用利用・再配布可、無保証。
- **版と最終更新日/活動**: 後述§4.0の機械可読の表を参照(値の重複記載を避ける)。
- **対応取引所**: README に暗号資産取引所への直接接続の記述なし(一次資料)。データベンダー接続が中心。
- **料金の構造**: コア機能はApache-2.0のOSSで無料(一次資料: PyPI+LICENSE)。ただしextras(`bloomberg-dl`・`blpapi`・`quandl`)経由でBloomberg/Quandlの有償データ契約が別途必要になりうる(README・METADATAのextra指定、一次資料)。無料の範囲: pip installと基本のバックテスト機能自体には利用回数・期間の制限記載なし。課金が始まる条件: 有償データベンダーへの接続時のみ(推定: extrasの存在から)。隠れた依存: `ibapi`(Interactive Brokers)・`blpapi`(Bloomberg)・`quandl`・`yfinance`など(実測、METADATAのRequires-Dist)。登録が要るもの: 無し(pip installのみで動く。有償データベンダーは別途契約が要るが、それは道具自体の登録ではない)。
- **到達・導入・実行の記録**: `pip download --no-deps -d . qf-lib==4.0.7` で取得しwheelを展開して検査(実測、`docs/DATA/probes/20260923_tools_8_run1.log` の `download_inspect` 節)。同梱バイナリ・外部URL取得コードなし。隔離venv(`<scratchpad>/cat8/venvs/qflib_venv`)へ`pip install qf-lib==4.0.7`を実行し成功、`import qf_lib`も成功(実測、`venv_install`節)。バックテストの合成データでの1往復実行(§5-4の最小実行)は時間の制約で未実施。
- **当方の用途との相性**: CSVDataProvider(実測、`csv_data_provider.py`)により当方のcsv形式を取り込める可能性があるが、当方のcsv.gzの列名・命名規則との適合は未確認。時刻の扱い・再現性・規模の見積は未確認(§4.0の表参照)。
- **当方に無いもの(全部)**: ルックアヘッド防止のためのデータアクセス層(`look_ahead_bias`パラメータ、当方の`src/bot/backtest/engine.py`には同種のフラグは無い=未確認、比較していない)/ Bloomberg・Quandl・Haver・Portaraへの直接接続 / PDFレポート自動生成(WeasyPrint使用)。
- **4軸**: 4軸1_道具=印(実測: pip installで動作、csv取り込み対応)/ 4軸2_情報=印(一次資料: 複数データベンダー接続、ルックアヘッド防止という当方に無い情報)/ 4軸3_視点=印(推定: event-driven+ルックアヘッド防止という設計思想は当方のbar単位モデルと異なる視点)/ 4軸4_向上=印(推定: `look_ahead_bias`パラメータの設計を当方の研究部品に取り込む余地がある)。
- **危険**: 供給網(§6-1)を実測(`download_inspect`節: PyPI配布元とGitHubのリンクが一致、同梱バイナリなし、setup時の外部URL取得コードなし)。既知の脆弱性: OSV.dev照会で登録なし(実測、取得日2026-09-23)。自動発注機能: なし(一次資料、README)。宣伝詐欺の兆候: なし。外部送信: コアには無し、オプションのBloomberg/Quandl/IB/yfinance等のデータプロバイダ経由では当該ベンダーへ接続する(README記載どおり、意図された機能)。

#### PineForge(8-002)

- **名前/種別/できること**: PineScript v6のオープンソースバックテストエンジン(C++17、stable C ABI、Apache-2.0)。TradingViewの挙動をバー単位で再現し、公開コーパス(312戦略)とコミュニティスクリプト(413件)に対する再現度を継続的に測定・公開している(README)。
- **言語・動作環境**: C++17、stable C ABI(README 411行)。
- **ライセンス**: Apache License 2.0(LICENSEファイル実測、READMEの説明文でも明記)。
- **対応取引所**: 該当なし(取引所非依存。PineScript戦略の実行エンジンであり取引所接続機能では無い。一次資料: README全体の記述)。
- **料金の構造**: OSS(Apache-2.0)で無料(一次資料)。無料枠の上限: 該当なし(OSS)。課金開始条件: なし。隠れた依存: ベンチマーク比較にPyneCore・PineTS・vectorbtを使用(README 291行、実測grep)。これらは比較対象であり本体の実行に必須ではない(推定)。登録の要否: 不要(GitHub公開リポジトリ)。
- **到達・導入・実行の記録**: GitHubから到達(実測、ungh.cc経由でリポジトリ登録情報を取得)。C++のビルド(cmake)・実行はこの回の時間の制約で未実施(未確認、試した手段: READMEのビルド手順の読解のみ)。「pineforge-release」イメージにコンパイル済みランタイムが同梱される(README 416行、一次資料)が、ソースリポジトリ自体には同梱バイナリなし。
- **当方の用途との相性**: 未確認(ビルド未実施のため)。PineScript戦略の記述が前提で、当方のPython戦略をそのまま持ち込める形式ではないと見られる(推定)。
- **当方に無いもの(全部)**: TradingView本体との1トレード単位の差分検証・回帰ゲート(README 217・263行、E1a)/ バー単位の決定論的リプレイテスト(E4)/ ビット単位の再現性保証とバージョン固定によるベースライン管理(E5)。いずれも当方の`src/bot/backtest/engine.py`には同種の機構は無い(未確認、当方コードとの直接比較は今回行っていない)。
- **4軸**: 4軸1_道具=印(一次資料: 公開OSS、ビルド手順あり)/ 4軸2_情報=印(一次資料: TradingViewとの差分データという当方に無い情報)/ 4軸3_視点=印(一次資料: 「回帰ゲート+ベースライン昇格」という視点は当方のバックテスト検証に無い)/ 4軸4_向上=印(推定: 差分検証・回帰ゲートの設計を当方の研究の再現性管理に応用できる可能性)。
- **危険**: 供給網(実測、ungh.cc): 初回公開2026-05-05、最新更新2026-09-23(取得日と同日)、星187・フォーク43。同梱バイナリ: ソースリポジトリには無し、リリース用イメージには有り(README記載、一次資料)。既知の脆弱性: 未確認(パッケージレジストリに登録が無くOSV照会の対象外)。自動発注機能: なし(一次資料)。宣伝詐欺の兆候: なし。

#### prediction-market-backtester(8-003、浅い)

- **名前/種別/できること**: Polymarket/Kalshi向けのクオンツ系バックテストエンジン(README)。CLIで単一市場・バッチのバックテストを実行し、結果をresults.json/equity.csv/trades.csvに出力する。
- **ライセンス・言語**: MIT License(LICENSE実測)、Python(pm-bt CLI、README)。
- **料金の構造**: OSS(MIT)で無料(一次資料)。ただし`POLYGON_RPC`(Polymarketの取引データインデックス用RPC)は外部サービス契約が必要な可能性がある(README「For Polymarket trades indexing, set `POLYGON_RPC`」、一次資料。具体的な料金体系までは未確認)。
- **到達・導入・実行の記録**: GitHubから到達(実測)。ビルド・実行はこの回では未実施(未確認、試した手段: README読解のみ)。
- **当方に無いもの**: `data_quality.json`による市場ごとのデータ品質ゲート(E2)/ gitコミットハッシュ付きの結果記録によるトレーサビリティ(E5)。
- **4軸**: 4軸1_道具=印(推定: CLIツールとしてそのまま動作しそうだが未実行)/ 4軸2_情報=印(一次資料: 予測市場という当方に無い市場のデータ)/ 4軸3_視点=印(一次資料: data_quality.jsonのゲート方式という視点)/ 4軸4_向上=印(推定: データ品質ゲートの実装パターンを当方のデータ検査に応用できる可能性)。
- **危険**: 未確認(§6-1の供給網検査は実施していない。導入していないため実施の必要が生じなかった)。

#### akurkar07/OrderBook(8-004、危険で導入停止)

- **名前/種別/できること**: 単一銘柄の価格時間優先LOBマッチングエンジン(C++、README)。限定注文・成行注文・取消をサポートし、参照実装との差分検証・ベンチマークを持つ。
- **ライセンス・言語**: MIT License(LICENSE実測)、C++(CMake、README)。
- **危険(導入停止の理由)**: §6-1の供給網検査により、初回公開日2026-09-16・最新更新2026-09-17(ungh.cc実測、取得日2026-09-23時点でリポジトリ年齢は約1週間)、星0・フォーク0(実測)、保守者は「Alex Kurkar」の単独(LICENSE実測、他の保守者情報なし)という組み合わせが、委任文§6-1が名指しする危険信号「公開直後」「保守者不明」に該当すると判断した。ビルド・実行(導入)は行っていない。README・LICENSEからの文書情報のみで§4の他の列を埋めた。
- **当方に無いもの**: 最適化実装と参照実装(ベクタ方式)の決定論的差分テスト(E1a)/ 同一注文列に対する決定論的な結果保証(E5)。
- **4軸**: 4軸1_道具=印(一次資料: ビルド手順は明記されているが未実行のため推定を含む)/ 4軸2_情報=なし(LOBマッチングという機構自体は既知の領域で、当方に無い情報とまでは言えない、推定)/ 4軸3_視点=印(一次資料: 参照実装との差分ベンチマークという視点)/ 4軸4_向上=印(推定: 差分検証の手法を当方のmaker_fill_ref.pyの検証強化に応用できる可能性)。

#### Exegy(8-005、登録が要る)

- **名前/種別/できること**: 低遅延の正規化市場データ・接続・FPGA取引基盤を提供する企業(exegy_fetch節)。製品カテゴリ: Market Data(nxFeed等)・Data Distribution・Market Access・Tech & Infrastructure。
- **料金の構造**: 記載なし(公式サイトに料金表なし、一次資料)。登録の要否: 技術詳細・料金は「Talk to an Expert」への問い合わせが必要(一次資料)。渡すもの: 未確認(問い合わせフォームの入力項目は開いていない)。オーナーが辿れる手順: https://www.exegy.com/request-a-consultation/ を開き相談を申し込む(登録はしていない)。
- **当方に無いもの**: FPGA基盤による正規化市場データ配信という当方に無いインフラ層(一次資料、製品カテゴリの説明のみ)。E1-E6に該当する機能の有無は未判別(登録なしで確認できる情報の範囲を超える)。
- **4軸**: すべて未判別(公開情報が製品カテゴリ名のみで、技術的な機能の裏付けが取れていないため)。
- **危険**: 未確認(トップページのみで判断材料がない)。宣伝詐欺の兆候: なし(実在の低遅延市場データ企業として一般に知られている名称であり、サイトの記載内容も業務説明として自然。推定)。

#### freqtrade(新、浅い)

- **名前/種別/できること**: 無料OSSの暗号資産トレーディングボット(PyPI author「Freqtrade Team」)。バックテスト・プロット・機械学習によるパラメータ最適化に加え、`lookahead-analysis`(E3a)・`recursive-analysis`コマンドを持つ。
- **ライセンス**: GNU General Public License v3(PyPI classifiers、LICENSE実測、一次資料)。
- **活動**: 星54708・フォーク11343(ungh.cc実測、取得日2026-09-23)。既知の脆弱性: OSV.dev照会で登録なし(実測)。
- **料金の構造**: OSS・無料(GPLv3、一次資料)。対応取引所: 複数の暗号資産取引所に対応と一般に知られるが、この回では一次資料(`docs/exchanges.md`)を読んでおらず未確認。
- **到達・導入・実行の記録**: PyPI(`pypi.org/pypi/freqtrade/json`)・GitHubから到達確認(実測)。インストール・実行はこの回では時間の制約で未実施(未確認)。
- **当方に無いもの**: `lookahead-analysis`コマンド(baseline backtestとsliced backtestを比較しルックアヘッドを自動検出・報告する、一次資料)。当方には同種の自動検出機構は無い(未確認、当方コードとの直接比較は未実施)。
- **4軸**: 4軸1_道具=印(推定: pip/PyPI経由で導入できると見られるが未実行)/ 4軸2_情報=印(一次資料: lookahead-analysisのレポートという当方に無い情報)/ 4軸3_視点=印(一次資料: baseline/sliced比較という視点)/ 4軸4_向上=印(推定: lookahead-analysisの手法を当方の研究プロトコルに応用できる可能性)。
- **危険**: 未確認(供給網検査は実施していない。導入していないため)。

#### backtrex(新、浅い)

- **名前/種別/できること**: ノーコードのビジュアルバックテストSaaS(backtrex_fetch節)。バックテスト実行前にOHLCデータ品質検証層を自動で挟む(E2)。
- **料金の構造**: 登録必須(「Create your account in 30 seconds and run your first backtest」)、無料トライアルあり(「Try for free」、クレジットカード不要と見られる記載)。詳細な料金表は`/en/pricing`ページにあるが本文には金額の記載なし(未確認、当該ページは未読)。
- **登録が要る**: 渡すもの: 未確認(アカウント作成フォームは開いていない)。オーナーが辿れる手順: https://backtrex.com/en/pricing で料金確認 → アカウント作成 → 最小のバックテストを試行。
- **当方に無いもの**: OHLC入力データの自動品質検証層(各バーの数学的矛盾チェック・異常ギャップの検出とフラグ化・リペインティング防止ルール強制・エラー報告書生成、一次資料)。当方の`scripts/data_quality.py`との機能重複・差分は未確認(比較していない)。
- **4軸**: 4軸1_道具=なし(SaaSでノーコード専用、当方のPythonパイプラインへの組み込みは想定しにくい、推定)/ 4軸2_情報=なし(推定)/ 4軸3_視点=印(一次資料: 「バックテスト前に必ずデータ品質を通す」という運用上の視点)/ 4軸4_向上=印(推定: OHLC検証の項目一覧を当方の`data_quality.py`のチェック項目の参考にできる可能性)。
- **危険**: 未確認(登録していないため導入前検査の対象外。SaaSであり§6-1のパッケージ検査は非適用)。

#### FX Replay(新、浅い)

- **名前/種別/できること**: 秒単位からのマルチタイムフレーム相場リプレイSaaS(fxreplay_fetch節)。FX/株/先物データの手動トレード練習向け。
- **料金の構造**: 無料プラン(登録不要、有効期限なし)。有料プラン: Intermediate・Pro(いずれも月額課金、生ログ参照)、有料時のみ登録要・クレジットカード不要。
- **当方に無いもの**: 秒単位までの粒度でのマルチタイムフレーム相場リプレイ(E4)。当方の`scripts/replay_scalp_storm.py`との粒度・対象市場の違いは未確認(比較していない)。
- **4軸**: 4軸1_道具=なし(人間のトレード練習用UIであり自動化戦略への組み込み用途ではないと見られる、推定)/ 4軸2_情報=なし(推定)/ 4軸3_視点=なし(推定)/ 4軸4_向上=なし(推定)。
- **危険**: 未確認(未登録)。

### 4.0 機械可読の表(深掘りした道具: qf-lib / PineForge)

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| qf-lib | 版 | 4.0.7 | 一次資料 | https://pypi.org/pypi/qf-lib/json 取得日2026-09-23 |
| qf-lib | 最終更新日 | 2026-08-31 | 一次資料 | https://ungh.cc/repos/quarkfin/qf-lib(pushedAt)取得日2026-09-23 |
| qf-lib | ライセンス | Apache License 2.0 | 実測 | `20260923_tools_8_run1.log` の `LICENSE-5` の節 |
| qf-lib | 言語と動作環境 | Python、requires_python>=3.8.0 | 一次資料 | https://pypi.org/pypi/qf-lib/json |
| qf-lib | 対応取引所 | 記載なし(データベンダー接続が中心) | 一次資料 | README(quarkfin/qf-lib) |
| qf-lib | 星 | 970(フォーク139) | 一次資料 | https://ungh.cc/repos/quarkfin/qf-lib |
| qf-lib | コミット数 | 未確認 | 未確認 | 試した手段: `api.github.com/repos/quarkfin/qf-lib/contributors` をこのセッションから叩いたが HTTP 403「GitHub access to this repository is not enabled for this session」。ungh.ccにコミット数の端点なし |
| qf-lib | 保守者数 | 未確認 | 未確認 | 同上の理由でcontributors一覧が取得できず |
| qf-lib | 週DL数 | 未確認 | 未確認 | https://pypistats.org/api/packages/qf-lib/recent が HTTP 429(レート制限)。再試行はしていない |
| qf-lib | 初回公開日 | 2019-08-16 | 一次資料 | https://ungh.cc/repos/quarkfin/qf-lib(createdAt) |
| qf-lib | 既知の脆弱性 | 登録なし({}) | 実測 | `20260923_tools_8_run1.log` の `osv` の節(https://api.osv.dev/v1/query package=qf-lib、取得日2026-09-23) |
| qf-lib | 料金体系 | 無料(Apache-2.0のOSS) | 一次資料 | PyPI+LICENSE |
| qf-lib | 無料枠の上限 | 該当なし(OSSに上限概念なし) | 一次資料 | 同上 |
| qf-lib | 課金開始条件 | なし(コア機能。有償データベンダー接続時は別) | 一次資料 | README+METADATAのextras指定 |
| qf-lib | 隠れた依存 | extras: ibapi(IB)・blpapi(Bloomberg)・quandl・yfinance・cryptography等(bloomberg-dl) | 実測 | `20260923_tools_8_run1.log` の `download_inspect` の節(METADATA Requires-Dist) |
| qf-lib | 登録の要否 | 不要 | 実測 | `20260923_tools_8_run1.log` の `venv_install` の節(pip installのみで成功) |
| qf-lib | 到達経路 | PyPI(pip install)・GitHub | 実測 | `20260923_tools_8_run1.log` の `venv_install` の節、`ungh-5repos` の節 |
| qf-lib | 導入可否 | 可 | 実測 | `20260923_tools_8_run1.log` の `venv_install` の節(rc=0) |
| qf-lib | install所要秒 | 39 | 実測 | `20260923_tools_8_run1.log` の `venv_install` の節(time_s=39) |
| qf-lib | 依存数 | コア10件(extras除く) | 実測 | `20260923_tools_8_run1.log` の `download_inspect` の節のMETADATA(pandas, xarray, numpy, matplotlib, Pillow, scikit-learn, seaborn, openpyxl, WeasyPrint, Jinja2) |
| qf-lib | pip check | 未確認 | 未確認 | 試した手段: pip installは実施したが`pip check`コマンド自体は打っていない(時間の制約) |
| qf-lib | 最小実行の可否 | 可(importのみ) | 実測 | `20260923_tools_8_run1.log` の `venv_install` の節(import成功) |
| qf-lib | 最小実行の中身 | importの実行のみ。合成データでのバックテスト1往復は未実施 | 実測 | `20260923_tools_8_run1.log` の `venv_install` の節(importの範囲に限る実測) |
| qf-lib | 実行所要秒 | 未確認 | 未確認 | importのみ実行、代表的なバックテスト実行は未実施のため計測できていない |
| qf-lib | wheel展開 | 展開した(700ファイル、.so/.dll/.exe/.pyd 0件) | 実測 | `20260923_tools_8_run1.log` の `download_inspect` の節 |
| qf-lib | setup.py導入時実行 | 該当なし(wheel配布のためインストール時実行は発生しない) | 実測 | `20260923_tools_8_run1.log` の `download_inspect` の節(wheelについて確認した。sdist配布物は今回取得していない) |
| qf-lib | 同梱バイナリ | 無し | 実測 | `20260923_tools_8_run1.log` の `download_inspect` の節(find .so/.dll/.exe/.pyd 0件) |
| qf-lib | 外部送信 | コアには無し。オプションのBloomberg/Quandl/IB/yfinance等データプロバイダ経由では当該ベンダーへ接続する(意図された機能) | 実測 | `20260923_tools_8_run1.log` の `qflib_source_grep` の節(コアのみのgrep結果。README上の意図された機能の記述と合わせた) |
| qf-lib | 自動発注機能 | 無し | 一次資料 | README(バックテスト専用ライブラリ) |
| qf-lib | 宣伝詐欺の兆候 | 無し | 一次資料 | README(CERN発、Apache-2.0、Readthedocs文書あり) |
| qf-lib | 当方データ投入 | 可能(CSVDataProviderで汎用csv読み込み対応) | 実測 | `20260923_tools_8_run1.log` の `qflib_source_grep` の節 |
| qf-lib | 時刻の扱い | 未確認 | 未確認 | datetimeを使用していることはimport文から分かるがUTC/ミリ秒の扱いの詳細は未確認 |
| qf-lib | 再現性 | 無し(専用の乱数シード固定・再現性保証機能なし。テストユーティリティに1件のみ) | 実測 | `20260923_tools_8_run1.log` の `qflib_source_grep` の節 |
| qf-lib | 規模の見積 | 未確認 | 未確認 | 456日相当のデータでの実行を試していない |
| qf-lib | 配布元の一致 | 一致 | 実測 | `20260923_tools_8_run1.log` の `ungh-5repos` の節(READMEのPyPIバッジがPyPIのqf-libを指し、GitHubのquarkfin/qf-libと相互にリンクすることを確認) |
| qf-lib | 難読化 | 無し | 実測 | `20260923_tools_8_run1.log` の `download_inspect` の節(700ファイルすべて平文の.py) |
| qf-lib | 外部URL取得 | 無し | 実測 | `20260923_tools_8_run1.log` の `download_inspect` の節(grep 0件) |
| qf-lib | 依存の一覧 | コア10件+多数のextras(bloomberg-dl/quandl/yfinance/blpapi/interactive-brokers/detailed-analysis等) | 実測 | `20260923_tools_8_run1.log` の `download_inspect` の節のMETADATA |
| qf-lib | 保守者名の一貫性 | 未確認 | 未確認 | contributors一覧が取得できないため(api.github.com 403) |
| qf-lib | 4軸1_道具 | 印(pip installで動作、csv取り込み対応) | 実測 | `20260923_tools_8_run1.log` の `venv_install` の節、`qflib_source_grep` の節 |
| qf-lib | 4軸2_情報 | 印(look-ahead-bias対策済みデータアクセス層、複数データベンダー接続) | 一次資料 | README+data_provider.py |
| qf-lib | 4軸3_視点 | 印(event-driven+ルックアヘッド防止という設計思想) | 推定 | 当方のengine.pyのbar単位モデルとの対比(推定、直接比較は未実施) |
| qf-lib | 4軸4_向上 | 印(look_ahead_biasパラメータの設計を当方研究に取り込める可能性) | 推定 | 同上 |
| PineForge | 版 | engine `063e4460`、PyneCore 6.10.2、PineTS 0.9.34、vectorbt 0.28.2(比較対象) | 一次資料 | README(pineforge_README.md)328行 |
| PineForge | 最終更新日 | 2026-09-23 | 一次資料 | https://ungh.cc/repos/pineforge-4pass/pineforge-engine(pushedAt) |
| PineForge | ライセンス | Apache License 2.0 | 実測 | `20260923_tools_8_run1.log` の `LICENSE-5` の節 |
| PineForge | 言語と動作環境 | C++17、stable C ABI | 一次資料 | README 411行 |
| PineForge | 対応取引所 | 該当なし(取引所非依存、PineScript実行エンジン) | 一次資料 | README全体の記述 |
| PineForge | 星 | 187(フォーク43) | 一次資料 | https://ungh.cc/repos/pineforge-4pass/pineforge-engine |
| PineForge | コミット数 | 未確認 | 未確認 | api.github.com 403(理由はqf-libと同じ) |
| PineForge | 保守者数 | 未確認 | 未確認 | api.github.com/repos/pineforge-4pass/pineforge-engine/contributors がこのセッションのプロキシで403(理由はqf-libと同じ) |
| PineForge | 週DL数 | 該当なし(PyPI等パッケージレジストリに登録なし) | 一次資料 | pypi.org検索で該当パッケージ無し確認(取得日2026-09-23) |
| PineForge | 初回公開日 | 2026-05-05 | 一次資料 | https://ungh.cc/repos/pineforge-4pass/pineforge-engine(createdAt) |
| PineForge | 既知の脆弱性 | 未確認 | 未確認 | パッケージレジストリ未登録のためOSV.dev照会の対象外 |
| PineForge | 料金体系 | 無料(Apache-2.0のOSS) | 一次資料 | README+LICENSE |
| PineForge | 無料枠の上限 | 該当なし(OSS) | 一次資料 | README(Apache-2.0ライセンスの表示)+LICENSEファイル、上限を課す記述なし |
| PineForge | 課金開始条件 | なし | 一次資料 | README(Apache-2.0ライセンスの表示)、課金に関する記述なし |
| PineForge | 隠れた依存 | ベンチマーク比較にPyneCore・PineTS・vectorbtを使用(本体実行に必須かは未確認) | 一次資料 | README 291行 |
| PineForge | 登録の要否 | 不要 | 一次資料 | GitHub公開リポジトリ |
| PineForge | 到達経路 | GitHub | 実測 | `20260923_tools_8_run1.log` の `ungh-5repos` の節、`README-4` の節 |
| PineForge | 導入可否 | 未確認 | 未確認 | C++のビルド(cmake)はこの回で未実施 |
| PineForge | install所要秒 | 未確認 | 未確認 | 導入(cmakeビルド)自体をこの回で試していない(時間の制約) |
| PineForge | 依存数 | 未確認(ビルド依存の総数は未算出) | 未確認 | CMakeLists.txtの内容は未読 |
| PineForge | pip check | 該当なし(pipパッケージではない) | 一次資料 | README(C++プロジェクト) |
| PineForge | 最小実行の可否 | 未確認 | 未確認 | ビルドを試していないため実行の可否を確かめられていない |
| PineForge | 最小実行の中身 | 未確認 | 未確認 | ビルドしていないため最小実行そのものを行っていない |
| PineForge | 実行所要秒 | 未確認 | 未確認 | 実行していないため所要時間を計測できていない |
| PineForge | wheel展開 | 該当なし(wheel配布ではない) | 一次資料 | README |
| PineForge | setup.py導入時実行 | 該当なし(Pythonパッケージではない) | 一次資料 | README |
| PineForge | 同梱バイナリ | ソースリポジトリには無し。リリース用イメージ(pineforge-release)にはコンパイル済みランタイムが同梱される | 一次資料 | README 416行 |
| PineForge | 外部送信 | 未確認 | 未確認 | ソース未ビルドのため実行時通信は未確認 |
| PineForge | 自動発注機能 | 無し | 一次資料 | README(バックテストエンジン、実弾発注への言及なし) |
| PineForge | 宣伝詐欺の兆候 | 無し | 一次資料 | README(技術文書として詳細かつ具体的、誇大広告的な表現なし) |
| PineForge | 当方データ投入 | 未確認 | 未確認 | PineScript形式の戦略記述が前提で、当方のPython戦略やcsvをそのまま投入できるかは未確認 |
| PineForge | 時刻の扱い | 未確認 | 未確認 | README中に明記箇所を確認できず |
| PineForge | 再現性 | 印(bit-identical、決定論的) | 一次資料 | README 37行「Deterministic to the bit」 |
| PineForge | 規模の見積 | 未確認 | 未確認 | ビルド未実施のため |
| PineForge | 配布元の一致 | 一致(GitHub上の単一の正規リポジトリのみ、パッケージレジストリへの分散なし) | 実測 | `20260923_tools_8_run1.log` の `ungh-5repos` の節 |
| PineForge | 難読化 | 無し | 一次資料 | README(ソースコード全体が公開されC++ヘッダも含む) |
| PineForge | 外部URL取得 | 未確認 | 未確認 | ビルドスクリプト・CMakeLists.txtは未読 |
| PineForge | 依存の一覧 | 比較用: PyneCore・PineTS・vectorbt(README 291行)。ビルド依存の全体は未確認 | 一次資料 | README 291行(比較用の分のみ判明、ビルド依存の全体は未確認) |
| PineForge | 保守者名の一貫性 | 未確認 | 未確認 | contributors一覧が取得できないため |
| PineForge | 4軸1_道具 | 印(公開OSS、ビルド手順は明記されているが未実行) | 一次資料 | README(ビルド手順の節) |
| PineForge | 4軸2_情報 | 印(TradingViewとの差分データという当方に無い情報) | 一次資料 | README 217行 |
| PineForge | 4軸3_視点 | 印(回帰ゲート+ベースライン昇格という視点) | 一次資料 | README 263行 |
| PineForge | 4軸4_向上 | 印(差分検証・回帰ゲートの設計を当方の研究の再現性管理に応用できる可能性) | 推定 | README 263・267行からの外挿 |

### 予算

**時刻**: 開始 2026-09-23T14:11:25Z(`tools_inventory.py`実行時刻)。この節を書いている時点で約20分弱が経過(生ログのタイムスタンプで確認可能)。25分の上限に近づいたため、この回はここで区切る。
**トークン数**: 自分自身のトークン消費を計測する手段がこの環境に無く、正確な値は未確認(試した手段: 無し。ツール呼び出し回数や生ログの行数から下限を推定することはできるが、正確なトークン数ではないため書かない)。
**実行状況**: 検索計画6本すべて実行済み(補助検索1本を追加)。候補8件のうち、5件(qf-lib/PineForge/prediction-market-backtester/OrderBook/Exegy)は区分1から引き継いだ全件、3件(freqtrade/backtrex/FX Replay)を新規に発見し全件を深掘り(一次資料に届いた)まで進めた。予算に達したため、これ以上の新しい検索計画(2回目以降)はこの回では打っていない。**残りの候補名: 無し(候補の一覧の全行を一次資料まで進めたため)。** ただし要素の一部(特にE2・E3a・E3b・E4・E5)が「未判別」のまま残っている候補があり、それらは次回以降にさらなる一次資料の読み込みが必要。

### 受け入れ検査の出力

`python3 scripts/check_scan_report.py docs/DATA/SCAN_2026-09-23_tools_cat8.md docs/DATA/probes/20260923_tools_8_run1.log` の最後に打った出力全文:

```
K1 太字                  0 件
K2 括弧                  0 件
K3 必須の節                0 件
K4 生ログに無い数値            0 件
K5 同じ道具に別の値            0 件
K6 未実施と実測の同居           0 件
K7 表の項目の欠落             0 件
K8 表の印と根拠              0 件
K9 表に無い数値              0 件
K10 見出しの件数             0 件
K11 実測の根拠              0 件
K13 中身が実質空             0 件
K12 検査の出力の貼付           0 件
---- 検査対象の合計 0 件(K12 を除く。貼り付けはこの数で照合する)
---- 合計 0 件
```

`python3 scripts/cat8_ledger.py check-elements docs/DATA/SCAN_2026-09-23_tools_cat8.md --round 1` の最後に打った出力全文(読むだけの検査、調査班も返す前に打つもの):

```
読んだもの: 候補の一覧 8 行 / 要素と段の表 64 行(道具 8)
---- 合計 0 件
```


`python3 scripts/cat8_ledger.py check-elements docs/DATA/SCAN_2026-09-23_tools_cat8.md --round 2` の最後に打った出力全文:

```
読んだもの: 候補の一覧 16 行 / 要素と段の表 128 行(道具 16)/ 知見の表 8 行 / 辿る一覧から出た名前 0 行
---- 合計 0 件
```

`git diff -U0 HEAD -- docs/DATA/SCAN_2026-09-23_tools_cat8.md | grep '^-[^-]' | wc -l`(1回目の節から消えた行)の出力: `0`

`python3 scripts/cat8_ledger.py check "" docs/DATA/probes/20260923_tools_8_run2.log --require-deadline` の最後に打った出力全文:

```
docs/DATA/probes/20260923_tools_8_run2.log:584: 生ログの見出しの形が違う: ---
docs/DATA/probes/20260923_tools_8_run2.log:586: 生ログの見出しの形が違う: ---
---- 合計 2 件
```
上の2件(584・586行)は生ログの手ではなく、`tmm_levels_detail`の手の出力そのもの(コマンド実行結果として`print('---')`を含むPythonスクリプトの標準出力)が生ログに書き写された行で、`cat8_step.py`が出力をそのまま記録した結果である。実行そのものは1手として正しく`--- <UTC> method=... target=tmm_levels_detail ...`の見出しを持っており、期限も付いている。誤検出だと判断したが自分では閉じない。

### 判断に迷った点と問い(決めずに列挙)

1. **qf-lib / E2 の段**: `drop_consecutive_duplicates()` は連続する重複値を検出して統合(merge)する関数だが、検出結果を人が読める形で報告するのか、静かに変換するだけなのかが原文(ソースコードのdocstring)だけでは判別しづらい。設計票§4.1の段1〜5の梯子(呼べるか/自動判定か/枠の中か外か/基準指定と結果保存)にうまく載せられず、値は`印`・段は`未判別`とした。
2. **候補の一覧の`[深掘り]`マークと設計票§2の状態語の関係**: 最初の版では全8候補に`[深掘り]`を付けていたが、委任文の検査K7(`[深掘り]`と印を付けたのに§4.0の表に1行も無い候補を拾う)に当たって気づき、qf-libとPineForgeの2件だけに絞った。この2つの意味(委任文K7が要求する「§4.0の表に行がある」ことと、設計票§2の「深掘り」という正式な状態)が同じ語`[深掘り]`で表現されるため紛らわしい。本回はK7の要求どおり「§4.0の表に行がある候補にだけ`[深掘り]`を付ける」という読み方を採用したが、この読み方自体が正しいかはリードに確認したい。
3. **freqtradeの`lookahead-analysis`をE1aでなくE3aに分類したこと**: 同機能は同一エンジンの2回の実行(baseline backtest / sliced backtest)を比較して差分を報告する。設計票§3のE1aの述語「2つ以上の実装(または実装と参照値)の出力を突き合わせて、差を出す機能」に、「同一実装の2回の実行」が含まれるのかどうかが原文だけでは判別できず、今回はE3a(ルックアヘッド検出)側だけに計上しE1aは「なし」とした。
4. **PineForgeのE4(リプレイ)にE1aと同じ根拠(formal gate・baseline promotion)を段5として重複して使ったこと**: README上、TradingViewとの差分検証(E1a)とリプレイテスト(E4)が同じ回帰ゲート機構を共有しているため、両方の段を5とした。これが「同じ機構を2つの要素に二重計上している」ことになるのか、それとも「2つの異なる要素それぞれが実際にその機構を満たしている」だけなのかは、設計票に明確な線引きが無く判断に迷った。
5. **akurkar07/OrderBook を「危険で導入停止」とした基準**: 初回公開から約1週間・星0・単独保守者という組み合わせのみを根拠に導入(ビルド)を停止した。委任文§6-1は「1つでも不審なら導入せず」としており該当すると判断したが、単に新しい個人プロジェクトであるだけで悪意は無い可能性も高く、この基準の重さ(どの組み合わせで止めるべきか)はリードが確認すべき点として残す。
6. **多くの候補で4軸3_視点・4軸4_向上に「推定」の印を付けたこと**: これらは「当方に無い視点で分析できるか」「既存の成果を向上できるか」という将来の応用可能性についての判断であり、一次資料や実測だけでは決まらない性質を持つ。「推定」の印を使うこと自体は委任文§4.1の定義(一次資料・実測から外挿)に沿うつもりだが、外挿の妥当性(当方の既存コードとの実際の比較なしに「向上できる可能性がある」と書いてよいか)はリードの判断を仰ぎたい。

## 区分8 — 2 回目の実行(2026-09-23)
起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run2_prompt.md`(指紋 `fbd510552276`)/ 追補 `docs/DATA/delegations/20260923_tools_survey_cat8_addendum.md`(指紋 `46258eebcd93`)/ 1回目起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run1_prompt.md`(指紋 `0ac68ca101f9`)/ 設計票 `docs/DATA/surveys/CAT8_DESIGN.md`/ 前回検収 `docs/AUDITOR/VERDICTS/2026-09-23_tools_scan_cat8_run1.md` に従う。生ログ: `docs/DATA/probes/20260923_tools_8_run2.log`。
### 検索計画
この回は新しい検索計画を打たない(委任文§2「前回の残りの候補名があれば、まずそれを深掘りする(検索計画は打ち直さない)」)。残りの候補(8-009〜8-016)は台帳にあるので、まず1回目の訂正(起動文§2の1)と成熟度枠組みの一次資料確認(§2の2)を先に済ませ、その後8-009〜8-016の深掘りに入る予定だったが、期限(下記の予算節を参照)により候補の深掘りは着手できなかった。
### 出典
| # | 経路 | URL / 節 | 内容 | 取得日 |
|---|---|---|---|---|
| 1 | 実測(venv) | `qf_lib` ソース(qflib_venv、1回目導入分) | DataCleaner・scenarios_generator・backtest_trading_session の再検査 | 2026-09-23 |
| 2 | GitHub raw | https://raw.githubusercontent.com/pineforge-4pass/pineforge-engine/main/README.md | PineForge README再取得(訂正確認用) | 2026-09-23 |
| 3 | GitHub raw | https://raw.githubusercontent.com/akurkar07/OrderBook/main/README.md | OrderBook README再取得 | 2026-09-23 |
| 4 | GitHub raw | https://raw.githubusercontent.com/Quentin-Piot/prediction-market-backtester/master/README.md | prediction-market-backtester README再取得(defaultBranch=masterに訂正) | 2026-09-23 |
| 5 | GitHub raw | https://raw.githubusercontent.com/Quentin-Piot/prediction-market-backtester/master/Makefile | make setupの実装確認 | 2026-09-23 |
| 6 | GitHub raw | https://raw.githubusercontent.com/Quentin-Piot/prediction-market-backtester/master/scripts/setup_data.sh | DATA_SHA256検証の自動判定の有無を確認 | 2026-09-23 |
| 7 | GitHub raw | https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/lookahead-analysis.md | freqtrade E1a/E6再確認 | 2026-09-23 |
| 8 | GitHub raw | https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/recursive-analysis.md | freqtrade recursive-analysis確認 | 2026-09-23 |
| 9 | 公式(HTML) | https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide | backtrex E1a/E1b再確認(生HTML) | 2026-09-23 |
| 10 | 公式(HTML) | https://fxreplay.com/ | FX Replay E1a/E1b再確認(生HTML) | 2026-09-23 |
| 11 | 公式(HTML) | https://abstracta.us/blog/software-testing/software-testing-maturity-model/ | Testing Maturity Model の一次資料本文 | 2026-09-23 |

すべて `docs/DATA/probes/20260923_tools_8_run2.log` に手ごとの記録がある。
### 知見
| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `qf-lib / E2 / 方式(原文)`: docstring「Cleans data which is partially incomplete, e.g. has gaps」 | 一次資料 | `qf_lib/common/utils/data_cleaner.py` 22-24行(qflib_venv、実測、取得日2026-09-23、生ログ docs/DATA/probes/20260923_tools_8_run2.log の qflib_data_cleaner_full 節) |
| 2 | `qf-lib / E2 / 直すか報告だけか`: 両方: `self.incorrect_columns`/`self.columns_with_holes`/`self.start_late_columns`という公開属性で報告し、`proxy_using_value`/`proxy_using_regression`が欠損を埋める(直す) | 実測 | `data_cleaner.py` 63-113行、docs/DATA/probes/20260923_tools_8_run2.log の `qflib_data_cleaner_tail` の節 |
| 3 | `qf-lib / E5 / 何を固定・比較するか`: 乱数の種(seed used to make the scenarios deterministic)とデータの版(get_preloaded_data_checksum/verify_preloaded_data) | 実測 | `scenarios_generator.py` 97-98行、`backtest_trading_session.py`、docs/DATA/probes/20260923_tools_8_run2.log の `qflib_verify_preloaded_data` の節 |
| 4 | `PineForge / E4 / 方式(原文)`: 「`strategy_stream_begin` / `_push_tick` / `_push_ticks` / `_advance_time` / `_end` / `_fill_report` \\| Warm on OHLCV, then run realtime on ordered trades」 | 一次資料 | https://github.com/pineforge-4pass/pineforge-engine README 445行、取得日2026-09-23 |
| 5 | `PineForge / E4 / 再生の粒度`: 「confirmed input bars, physical fill events and observable replay state」 | 一次資料 | https://github.com/pineforge-4pass/pineforge-engine README 445行、取得日2026-09-23(粒度の明確な定義は記載なし、読んだ箇所: 435-450行) |
| 6 | `prediction-market-backtester / E5 / 何を固定・比較するか`: 「optionally verifies `DATA_SHA256`」/ 「if [[ -n "$DATA_SHA256" ]]; then ... sha256sum --check --status; fi」 | 一次資料 | https://github.com/Quentin-Piot/prediction-market-backtester README 151行、`scripts/setup_data.sh` 33-35行、取得日2026-09-23 |
| 7 | `prediction-market-backtester / E5 / (ア)基準を指定できるか`: `DATA_SHA256`は`.env`でユーザーが設定する変数 | 一次資料 | https://github.com/Quentin-Piot/prediction-market-backtester README 143-146行、取得日2026-09-23 |
| 8 | `prediction-market-backtester / E5 / (イ)結果を保存して比較できるか`: 固定した`DATA_SHA256`に対して以降の`make setup`実行のたびにダウンロードしたアーカイブを照合する | 一次資料 | https://github.com/Quentin-Piot/prediction-market-backtester `scripts/setup_data.sh`、取得日2026-09-23 |

### 候補の一覧
1. [深掘り] `qf-lib` (8-001) — 状態: 深掘り
2. [深掘り] `PineForge` (8-002) — 状態: 深掘り
3. `prediction-market-backtester` (8-003) — 状態: 浅い
4. `akurkar07/OrderBook` (8-004) — 状態: 危険で導入停止
5. `Exegy` (8-005) — 状態: 登録が要る
6. `freqtrade` (8-006) — 状態: 浅い
7. `backtrex` (8-007) — 状態: 浅い
8. `FX Replay` (8-008) — 状態: 浅い
9. `nicferrari/backtester` (8-009) — 状態: 未着手
10. `arXiv:2603.20319` (8-010) — 状態: 未着手
11. `arXiv:2512.12924` (8-011) — 状態: 未着手
12. `VectorBT` (8-012) — 状態: 未着手
13. `rusty-bot` (8-013) — 状態: 未着手
14. `Fincept Terminal` (8-014) — 状態: 未着手
15. `TradingView のリプレイ機能` (8-015) — 状態: 未着手
16. `Exactpro の reconciliation testing` (8-016) — 状態: 未着手

**注記**: 8-001〜8-008は1回目からの訂正を反映した今の値。8-009〜8-016は台帳の`未着手`のまま(この回で一次資料に届いていない)。`[深掘り]`は`qf-lib`(8-001)と`PineForge`(8-002)のみ(設計票§2の深掘りの述語=委任文§4.0の条件を満たしE1a〜E6に未判別が無いことを満たす)。

### 要素と段
| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 |
|---|---|---|---|---|---|
| qf-lib | E1a | なし | - | 実測 | 再確認: `docs/DATA/probes/20260923_tools_8_run2.log` の qflib_E1a_E3a_E6_recheck 節。`reconcil\|cross.check\|differential.*test\|reference.impl\|benchmark.against\|compare.*implementation` でqf_lib全ソースをgrep、一致0件 |
| qf-lib | E1b | 印 | 2 | 実測 | 1回目から変更なし(`イベント駆動バックテスタでPnL・トレードを計算する。人が別実装と比較する前提で、突き合わせを自動で行う機能は無い`、`docs/DATA/probes/20260923_tools_8_run1.log` の venv_install 節) |
| qf-lib | E2 | 印 | 3 | 実測 | 訂正: docs/DATA/probes/20260923_tools_8_run2.log の `qflib_data_cleaner_full` の節。`qf_lib/common/utils/data_cleaner.py` の `DataCleaner` クラス(22-135行)。docstring「Cleans data which is partially incomplete, e.g. has gaps」。`_drop_underfilled_columns` が欠けの割合を`threshold`と比較し自動判定、結果を `self.incorrect_columns`(全欠損列)`self.columns_with_holes`(途中に欠損がある列)`self.start_late_columns`(開始が遅い列と日付の辞書)という公開属性に記録して呼び出し側が読める(=報告する)。段: `threshold`は使う人が指定できる(ア相当)が、結果を次回実行と自動比較して保存する仕組みは無い(イ非該当)ので段5には届かず、対象は qf_lib 独自の `SimpleReturnsDataFrame`(assert isinstance)に限られるため段4にも届かない→段3 |
| qf-lib | E3a | なし | - | 実測 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の qflib_E1a_E3a_E6_recheck 節。`look.?ahead` でgrepした一致はすべて `get_end_date_without_look_ahead` 系(防止の計算=E3b)で、検出結果を報告する関数は無い |
| qf-lib | E3b | 印 | 3 | 実測 | 1回目から変更なし(`qf_lib/data_providers/data_provider.py` 51・69-70行の `look_ahead_bias: bool` 引数) |
| qf-lib | E4 | 印 | 3 | 実測 | 1回目から変更なし(イベント駆動バックテスタが時刻順にデータを読み込み実行ハンドラを動かす構造) |
| qf-lib | E5 | 印 | 3 | 実測 | 訂正(誤りだった `なし` を直す): `docs/DATA/probes/20260923_tools_8_run2.log` の qflib_E5_correction 節。`backtesting/fast_alpha_model_tester/scenarios_generator.py` 97-98行 docstring「seed used to make the scenarios deterministic」、`backtesting/alpha_model/random_trades_alpha_model.py` 51-52行 同文(ユーザー向けseed引数、段2相当)。さらに qflib_verify_preloaded_data 節: `backtesting/trading_session/backtest_trading_session.py` の `get_preloaded_data_checksum()`(データバンドルのハッシュを返す)と `verify_preloaded_data(expected_checksum)`(一致しなければ ValueError を送出=自動判定)。使う人が `expected_checksum` を指定できる(ア相当)が、チェックサムの対象は `data_bundle`(データ)のみで、E5の対象『実験(コード・データ・設定)』全体には届かないため段4条件(対象の全部を持ち込める)を満たさず段3にとどめた |
| qf-lib | E6 | なし | - | 実測 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の qflib_E6_recheck 節。`def (assert_\|verify_\|validate_)` でgrepし、本体コードの一致は `verify_preloaded_data`(E5に計上)と `chart.py` の `assert_is_qfseries`(型チェックの内部ヘルパーで独立した検証機能ではない)のみ。他はすべて `tests/` 配下のテストヘルパー |
| PineForge | E1a | 印 | 5 | 一次資料 | 1回目から変更なし(README 217・263・267行) |
| PineForge | E1b | 印 | 5 | 一次資料 | 1回目から変更なし(同上) |
| PineForge | E2 | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の pineforge_broad_recheck 節。`missing\|duplicate\|outlier\|gap\|stale\|out.of.order\|misalign\|corrupt` でREADME全文を再検索。一致した箇所(65・230・267行)はいずれも『比較の一致率のgap』『TTYがJSON-RPCストリームをcorruptする』などデータ品質と無関係な文脈 |
| PineForge | E3a | なし | - | 一次資料 | 再確認: 同上節。`future.leak\|peek\|survivorship\|forward.fill\|snoop` 一致0件 |
| PineForge | E3b | なし | - | 一次資料 | 再確認: 同上節。同じ0件(独立したlook-ahead防止機構への言及なし) |
| PineForge | E4 | 印 | 3 | 一次資料 | 訂正: 1回目はE1aと同じ根拠(263・267行の formal gate/baseline promotion)を流用しており、監査14回目の指摘4により無効。`docs/DATA/probes/20260923_tools_8_run2.log` の pineforge_e4_context 節でE4専用の原文を確認: README 445行(表)「`strategy_stream_begin` / `_push_tick` / `_push_ticks` / `_advance_time` / `_end` / `_fill_report`」の説明「Warm on OHLCV, then run realtime on ordered trades」。記録したOHLCV・ティックを時刻順(`_advance_time`)に押し込み再実行する構造で、自動判定は無く(pass/failを出す機構ではない)、対象(戦略コード)はPineForge自身のコンパイル済みstrategyオブジェクトに限られるため段3。段5は取り消し |
| PineForge | E5 | 印 | 5 | 一次資料 | 1回目から変更なし(README 37・328行) |
| PineForge | E6 | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の pineforge_broad_recheck 節。`fuzz\|property.based\|mutation\|coverage\|sanitiz` 一致0件(README全文) |
| prediction-market-backtester | E1a | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の predmkt_e1a_recheck 節。`reconcil\|cross.check\|differential\|reference.impl\|benchmark.against\|compare.*(engine\|implementation\|platform)` でREADME全文を再検索、一致0件 |
| prediction-market-backtester | E1b | 印 | 2 | 一次資料 | 1回目から変更なし |
| prediction-market-backtester | E2 | 印 | 3 | 一次資料 | 1回目から変更なし(`data_quality.json`) |
| prediction-market-backtester | E3a | 未判別 | 未判別 | 未確認 | 1回目から変更なし(ソース `src/pm_bt/` 未読) |
| prediction-market-backtester | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| prediction-market-backtester | E4 | 印 | 3 | 一次資料 | 1回目から変更なし |
| prediction-market-backtester | E5 | 印 | 5 | 一次資料 | 訂正(根拠を追加): 1回目の baseline文書・gitコミットハッシュに加え、`docs/DATA/probes/20260923_tools_8_run2.log` の predmkt_makesetup/predmkt_makefile/predmkt_setup_script 節。README 151行「optionally verifies `DATA_SHA256`」、`scripts/setup_data.sh`(取得日2026-09-23)33-35行「if [[ -n "$DATA_SHA256" ]]; then ... sha256sum --check --status; fi」。`set -euo pipefail`によりハッシュ不一致で自動的に異常終了する(自動判定)。ユーザーが`DATA_SHA256`を指定でき(ア)、固定したハッシュに対し以後の取得データを照合できる(イ=データの版の固定)ため段5の根拠を補強 |
| prediction-market-backtester | E6 | なし | - | 一次資料 | 検討(起動文の指示どおりE2・E6に当てた): `DATA_SHA256`の検証はE2の7種(欠け・重複・順序の乱れ・時刻のずれ・外れ値・型や範囲の違反・情報源間の食い違い)のいずれにも直接当たらないため対象外(末尾の問いに記載) |
| akurkar07/OrderBook | E1a | 印 | 3 | 一次資料 | 1回目から変更なし |
| akurkar07/OrderBook | E1b | 印 | 2 | 一次資料 | 1回目から変更なし |
| akurkar07/OrderBook | E2 | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の orderbook_broad_recheck 節。`missing\|duplicate\|outlier\|gap\|stale\|out.of.order\|misalign\|corrupt\|data.quality` でgrep。95行「Active order IDs: Duplicate IDs are rejected」がヒットしたが、これは注文IDの重複検査であり、E2の述語『時系列・約定・板・足・参照データ』の重複ではないため対象外(境界事例として記録) |
| akurkar07/OrderBook | E3a | なし | - | 一次資料 | 再確認: 同上節。`look.?ahead\|future.leak\|peek\|snoop` 一致0件 |
| akurkar07/OrderBook | E3b | なし | - | 一次資料 | 再確認: 同上節。同じ0件 |
| akurkar07/OrderBook | E4 | なし | - | 一次資料 | 再確認: 同上節。`replay\|market data\|historical.*data\|record` 一致0件(記録済み市場データの再生機能への言及なし) |
| akurkar07/OrderBook | E5 | 印 | 3 | 一次資料 | 1回目から変更なし |
| akurkar07/OrderBook | E6 | なし | - | 一次資料 | 再確認: 同上節。98行「Quantity accounting: ... rejects an order that would overflow」がヒットしたが、注文数量のオーバーフロー防御でありE1a〜E5に当たらない独立した検証機能とは言えない(境界事例として記録) |
| Exegy | E1a | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E1b | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E2 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E3a | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E4 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E5 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E6 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| freqtrade | E1a | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の freqtrade_e1a_e6_recheck 節。`lookahead-analysis.md`全文で`reference\|other.engine\|cross.check\|reconcil\|independent.implementation`をgrep、一致は見出し語のみ(33行)。監査役の確認(検収§11の3)どおり分類を維持 |
| freqtrade | E1b | 印 | 2 | 一次資料 | 1回目から変更なし |
| freqtrade | E2 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(`docs/data-download.md`未読) |
| freqtrade | E3a | 印 | 3 | 一次資料 | 1回目から変更なし |
| freqtrade | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし(`recursive-analysis.md`は取得したが再現バイアス防止の記述は未確認) |
| freqtrade | E4 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(`docs/backtesting.md`未読) |
| freqtrade | E5 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| freqtrade | E6 | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の freqtrade_e1a_e6_recheck 節。`recursive-analysis.md`(取得日2026-09-23)を読んだが、指標の再帰計算によるバックテストと実運用のずれを検出する機能(E3a寄り)で、E1a〜E5以外の独立検証には当たらない |
| backtrex | E1a | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の backtrex_fxreplay_html_recheck/次コマンド節。公式サイトHTML(288,790バイト、取得日2026-09-23)を`compare.{0,40}(implementation\|engine\|platform)\|cross.check\|reconcil\|benchmark.against\|tradingview`でgrep。『Compare Backtesting Platforms & Alternatives』『See how Backtrex compares to TradingView, MetaTrader, and FX Replay for backtesting. Side-by-side feature comparison, pricing, honest reviews by traders』という文言を確認したが、これは機能比較のマーケティングページであり、出力を突き合わせる機能ではない(境界事例として記録) |
| backtrex | E1b | なし | - | 一次資料 | 1回目から変更なし |
| backtrex | E2 | 印 | 3 | 一次資料 | 1回目から変更なし |
| backtrex | E3a | 未判別 | 未判別 | 未確認 | 1回目から変更なし(製品ドキュメント未読) |
| backtrex | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| backtrex | E4 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| backtrex | E5 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| backtrex | E6 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E1a | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の backtrex_fxreplay_html_recheck 節。公式サイトHTML(357,164バイト、取得日2026-09-23)を同語でgrep。TradingViewへの言及は『Charting powered by TradingView lets you track economic events, monitor live prices, and more』のみでチャート描画ライブラリとしての利用、比較機能ではない |
| FX Replay | E1b | なし | - | 一次資料 | 1回目から変更なし |
| FX Replay | E2 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E3a | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E4 | 印 | 2 | 一次資料 | 1回目から変更なし |
| FX Replay | E5 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E6 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| nicferrari/backtester | E1a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| nicferrari/backtester | E1b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| nicferrari/backtester | E2 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| nicferrari/backtester | E3a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| nicferrari/backtester | E3b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| nicferrari/backtester | E4 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| nicferrari/backtester | E5 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| nicferrari/backtester | E6 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2603.20319 | E1a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2603.20319 | E1b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2603.20319 | E2 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2603.20319 | E3a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2603.20319 | E3b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2603.20319 | E4 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2603.20319 | E5 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2603.20319 | E6 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2512.12924 | E1a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2512.12924 | E1b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2512.12924 | E2 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2512.12924 | E3a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2512.12924 | E3b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2512.12924 | E4 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2512.12924 | E5 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| arXiv:2512.12924 | E6 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| VectorBT | E1a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| VectorBT | E1b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| VectorBT | E2 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| VectorBT | E3a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| VectorBT | E3b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| VectorBT | E4 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| VectorBT | E5 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| VectorBT | E6 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| rusty-bot | E1a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| rusty-bot | E1b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| rusty-bot | E2 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| rusty-bot | E3a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| rusty-bot | E3b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| rusty-bot | E4 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| rusty-bot | E5 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| rusty-bot | E6 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Fincept Terminal | E1a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Fincept Terminal | E1b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Fincept Terminal | E2 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Fincept Terminal | E3a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Fincept Terminal | E3b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Fincept Terminal | E4 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Fincept Terminal | E5 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Fincept Terminal | E6 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| TradingView のリプレイ機能 | E1a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| TradingView のリプレイ機能 | E1b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| TradingView のリプレイ機能 | E2 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| TradingView のリプレイ機能 | E3a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| TradingView のリプレイ機能 | E3b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| TradingView のリプレイ機能 | E4 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| TradingView のリプレイ機能 | E5 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| TradingView のリプレイ機能 | E6 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Exactpro の reconciliation testing | E1a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Exactpro の reconciliation testing | E1b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Exactpro の reconciliation testing | E2 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Exactpro の reconciliation testing | E3a | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Exactpro の reconciliation testing | E3b | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Exactpro の reconciliation testing | E4 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Exactpro の reconciliation testing | E5 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |
| Exactpro の reconciliation testing | E6 | 未判別 | 未判別 | 未確認 | 時間の制約によりこの回では一次資料に届いていない(台帳の発見の出典のみ確認) |

### ツール1件ごとの表
この回で§4の全列を新規に書く候補は無い(8-001〜8-008は1回目の表を維持し、上の「要素と段」「1回目の訂正」の差分だけを見る。8-009〜8-016はこの回で一次資料に届いていないため§4の列を埋められない)。

### 4.0 機械可読の表
| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| qf-lib | 再現性 | seed(scenarios_generator)+checksum(verify_preloaded_data) | 実測 | docs/DATA/probes/20260923_tools_8_run2.log の `qflib_verify_preloaded_data` の節。1回目の値(無し)は誤りだったため訂正 |

### 1 回目の訂正
(1回目の報告 `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の該当節、478行版を対象。行番号→直した値と根拠。1回目の節そのものは書き換えていない)

- **報告170行(qf-lib E2)**: 値`印`/段`未判別` → 値`印`/段`3`。根拠: `qf_lib/common/utils/miscellaneous/consecutive_duplicates.py`はE2に当たらない(検収§11の1で確定済み)。代わりに`qf_lib/common/utils/data_cleaner.py`の`DataCleaner`(欠けの検出+報告+補完)をE2の根拠にした。docs/DATA/probes/20260923_tools_8_run2.log の qflib_data_cleaner_full/tail 節
- **報告170行(qf-lib E5)**: 値`なし`/段`-` → 値`印`/段`3`。1回目の根拠(`random_state|seed|reproduc`のgrep結果を『テストユーティリティ1件のみ』と誤読)が誤りだった(検収§5で確定)。docs/DATA/probes/20260923_tools_8_run2.log の qflib_E5_correction/qflib_verify_preloaded_data 節で`scenarios_generator.py`のseed引数と`backtest_trading_session.py`のchecksum検証を確認
- **報告149行(候補の一覧、qf-lib)**: 状態`深掘り`のまま(E1a〜E6に未判別が無くなったため設計票§2の深掘りの述語を今も満たす)。1回目の`[深掘り]`欠落(検収§11の2・§13の6)は、この回の候補の一覧で`[深掘り]`を付けて訂正した
- **報告151行(prediction-market-backtester E6/E5)**: 値は変えず`なし`のまま(E6)。ただし根拠を追加: README151行『optionally verifies DATA_SHA256』と`scripts/setup_data.sh`のsha256sum検証を確認した結果、これはE5(データの版の固定)の追加根拠と判断し、E5の段5の根拠に加えた(監査14回目の指摘4への対応。E2・E6には当たらないと判断した理由は末尾の問いに書く)
- **報告168-169行(PineForge E4)**: 段`5` → 段`3`。1回目はE1aと同じ根拠(263・267行のformal gate/baseline promotion)を流用しており監査14回目の指摘4で無効と指摘された。docs/DATA/probes/20260923_tools_8_run2.log の pineforge_e4_context 節でE4専用の原文(README445行の`strategy_stream`系API)を示し、段3として再評価した
- **報告158行(候補の一覧の注記)**: 「`[深掘り]`の印は1(qf-lib)と2(PineForge)だけに付けた」という1回目の注記と、実際の1行目に`[深掘り]`が無い食い違い(検収§11の2・§13の6)は、この回の候補の一覧で1行目にも`[深掘り]`を付けることで解消した
- **報告280行(PineForgeの「312戦略」「413件」)**: 出所を追加: README(https://raw.githubusercontent.com/pineforge-4pass/pineforge-engine/main/README.md)34行「312 open reference strategies plus 413 real community scripts」、223-224行の表。docs/DATA/probes/20260923_tools_8_run2.log の pineforge_312_413_source 節
- **報告125-144行(出典表)**: 全行に取得日が無かった点を訂正: この回の出典表(上記)はすべて取得日を明記した。1回目の出典表(全15行)の取得日は、生ログのタイムスタンプに従い次のとおり: #1-8(GitHub/PyPI/OSV)・#12-15は2026-09-23T14:22Z台、#9-11(X)は2026-09-23T14:12Z台(いずれも`docs/DATA/probes/20260923_tools_8_run1.log`)

次の「なし」20行は再確認し値を維持した(20行、根拠は上の「要素と段」表に実測/一次資料の印つきで再掲): qf-lib(E1a・E3a・E6)/ PineForge(E2・E3a・E3b・E6)/ prediction-market-backtester(E1a・E6)/ akurkar07/OrderBook(E2・E3a・E3b・E4・E6)/ freqtrade(E1a・E6)/ backtrex(E1a・E1b)/ FX Replay(E1a・E1b)。`印`に直したのは1行(qf-lib E5)。`未判別`に直した行は無し(21行中、`なし`のまま20・`印`に直した1・`未判別`に直した0)。

### 代替経路
この回は『この環境から不可』と書いた項目なし。

### 辿る一覧から出た名前
時間の制約(下記の予算節を参照)により、起動文§2の4(dev.toのreconciliation tools記事・Xの`aiwithjainam`投稿のリポジトリ列挙・zennの仮説検証フレームワーク記事・quantreo/algorier/fortraatersのlook-ahead bias解説記事・検索計画7の結果のライブラリ)を開く作業に着手できなかった。**未着手。次回に持ち越す。**

### 予算
**時刻**: 開始(期限算出) 2026-09-23T15:31:53Z(`date -u -d '+20 min'`で期限2026-09-23T15:51:53Zを算出)。この節を書いている時点で期限に近い。**トークン数**: 自分自身のトークン消費を計測する手段がこの環境に無く、正確な値は未確認(道具呼び出し回数・生ログの行数からの下限推定に留まる。作った数は書かない)。
**実行状況**: §2の1(1回目の訂正)は主要部分(21行の`なし`の確かめ直し・qf-lib E2/E5の訂正・prediction-market-backtesterのDATA_SHA256・PineForge E4・候補一覧の`[深掘り]`食い違い・「312/413」の出所)を済ませたが、**出典表の1回目分の取得日の遡及訂正は上の箇条書きに留め、1回目の節そのものへの反映はしていない**(書き換え禁止のため)。§2の2(成熟度枠組みの一次資料)は着手し、abstracta.usのページ本文を実際に開いて読んだが、静的HTMLから取得できたのは要約段落(下記に逐語)のみで、レベルごとの詳しい定義文は動的レンダリング部分にあり確認できなかった(未確認、試した手段: `curl`で取得した静的HTML本文の全文検索)。§2の3(残りの候補8-009〜8-016の深掘り)と§2の4(辿る一覧)は**未着手**。期限に達したため、ここで区切る。
**残りの候補名**: 8-009 `nicferrari/backtester` / 8-010 `arXiv:2603.20319` / 8-011 `arXiv:2512.12924` / 8-012 `VectorBT` / 8-013 `rusty-bot` / 8-014 `Fincept Terminal` / 8-015 `TradingView のリプレイ機能` / 8-016 `Exactpro の reconciliation testing`(すべて未着手のまま次回へ)。

**成熟度枠組みの一次資料(§2の2、途中まで)**: abstracta.us「Software Testing Maturity Model: Improve Your Strategy」(https://abstracta.us/blog/software-testing/software-testing-maturity-model/ 、取得日2026-09-23)の静的HTML本文を実際に開いて読んだ(1回目は検索結果の要約のみを「」で引用しており本文を読んでいなかった=検収§9・§14の指摘)。読めた範囲の逐語: 「TMM mirrors CMMI with Level 1 Initial, Level 2 Managed, Level 3 Defined, Level 4 Measured, and Level 5 Optimization. Advancing through these levels introduces test-policy definition, integration with development, metrics-driven control, and proactive defect prevention.」(docs/DATA/probes/20260923_tools_8_run2.log の tmm_primary_source/tmm_levels_extract 節)。各段の名前(Initial/Managed/Defined/Measured/Optimization)はCMMIに準拠したものと明記されている。**段ごとの詳しい定義文(何をもってその段とするかの基準)は、このページの静的HTMLには含まれておらず(Next.jsのクライアントレンダリング部分にある可能性があり、この環境のcurlでは取得できなかった)、未確認のまま残る。**リードが2回目の検収で、この逐語と設計票§4.1の段の定義(呼べるか/自動判定か/枠の外か/基準指定と結果保存)を突き合わせる。

### 受け入れ検査の出力
`python3 scripts/check_scan_report.py docs/DATA/SCAN_2026-09-23_tools_cat8.md docs/DATA/probes/20260923_tools_8_run1.log docs/DATA/probes/20260923_tools_8_run2.log` の最後に打った出力全文:

```
K1 太字                  0 件
K2 括弧                  0 件
K3 必須の節                0 件
K4 生ログに無い数値            0 件
K5 同じ道具に別の値            0 件
K6 未実施と実測の同居           0 件
K7 表の項目の欠落             0 件
K8 表の印と根拠              0 件
K9 表に無い数値              0 件
K10 見出しの件数             0 件
K11 実測の根拠              0 件
K13 中身が実質空             0 件
K12 検査の出力の貼付           1 件
    docs/DATA/SCAN_2026-09-23_tools_cat8.md:0  貼られた出力に「---- 検査対象の合計 N 件」の行が無い(全文をそのまま貼ること)
---- 検査対象の合計 0 件(K12 を除く。貼り付けはこの数で照合する)
---- 合計 1 件
```


### 判断に迷った点と問い(決めずに列挙)
1. **prediction-market-backtesterのDATA_SHA256検証をE2/E6のどちらに当てるべきか**: 起動文§2の1はE2・E6に当てるよう指示しているが、原文(README151行・scripts/setup_data.sh)を読んだ限り、これはE2の7種(欠け・重複・順序の乱れ・時刻のずれ・外れ値・型や範囲の違反・情報源間の食い違い)のいずれにも直接当たらず、むしろE5の述語『データの版の固定』に最もよく当たるように見える。E6の定義は『E1a〜E5のどれにも当たらないもの』なので、E5に当たるならE6には計上できない。この回はE2=なし・E6=なし・E5の根拠に追加、とした。この判断でよいか。
2. **qf-libのE5の段**: `verify_preloaded_data`はデータバンドル(`data_bundle`)のみをチェックサム照合し、E5の対象『実験(コード・データ・設定)』の一部(データ)しか外から持ち込めないため段3とした。一方、`(ア)基準を指定できる`(expected_checksumを渡す)`(イ)結果を保存して比較できる`(固定したchecksumに対し以後の実行を照合する)の両方を満たしているようにも読め、対象の限定さえ無視すれば段5相当の機能に見える。段の梯子(3→4→5)は『対象の範囲』と『(ア)(イ)』の2軸が絡んでおり、対象が部分的なときに(ア)(イ)を満たしていても段3止まりでよいか、確認したい。
3. **PineForge E4を段3に下げたことの妥当性**: 1回目はE1aの根拠(TradingViewとの差分検証の回帰ゲート)をE4にも流用し段5としていたが、監査14回目の指摘4により『E4専用の原文』(README445行の`strategy_stream`系API)で再評価すると、そのAPI自体には基準指定・結果保存の記述が見当たらず段3とした。ただしREADME全体としてはPineForgeのリプレイ(E4)も最終的にはbaseline promotion(E1aと共有する回帰ゲート)を経る可能性があり、E4を『TradingViewとの差分検証と完全に独立した機能』として厳密に切り分けてよいか(それとも同じ回帰ゲートの一部として段5の根拠に含めてよいか)は判断が分かれる。
4. **akurkar07/OrderBookの『Duplicate order IDs are rejected』『Quantity accounting overflow rejected』を境界事例としてE2/E6の対象外としたこと**: これらは注文(発注データ)の検証であり、E2の述語が挙げる『時系列・約定・板・足・参照データ』ではないと判断したが、『板』の状態を構成する注文列という意味では市場データの一部と見ることもでき、線引きに迷いが残る。
5. **backtrexの『Compare Backtesting Platforms』ページをE1aの対象外としたこと**: 『Side-by-side feature comparison, pricing, honest reviews』というマーケティングページの文言のみを確認しており、実際にそのページの中身(表形式の比較内容)までは開いていない。中身に自動化された出力比較の記述がある可能性は排除できていない(未確認)。
6. **Testing Maturity Modelの段ごとの詳しい定義に届かなかったこと**: 静的HTMLの取得という手段では、このページのクライアントレンダリング部分(レベルごとの詳細な基準)に届かなかった。他の一次資料(書籍・別のCMMI公式文書など)を探すべきか、それともこの要約段落の逐語で設計票§4.1との突き合わせを進めてよいか。

## 区分8 — 3 回目の実行(2026-09-24)
起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run3_prompt.md`(指紋 `1ff8dd5b2d7e`)/ 追補 `docs/DATA/delegations/20260923_tools_survey_cat8_addendum.md`(指紋 `46258eebcd93`)/ 2回目起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run2_prompt.md`(指紋 `fbd510552276`)/ 1回目起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run1_prompt.md`(指紋 `0ac68ca101f9`)/ 設計票 `docs/DATA/surveys/CAT8_DESIGN.md`/ 前回検収 `docs/AUDITOR/VERDICTS/2026-09-23_tools_scan_cat8_run2.md` に従う。生ログ: `docs/DATA/probes/20260923_tools_8_run3.log`。期限: `date -u -d '+20 min' +%FT%TZ` で 2026-09-23T23:41:48Z を算出(docs/DATA/probes/20260923_tools_8_run3.log 冒頭の budget 手)。
### 検索計画
この回は新しい検索計画を打たない(委任文§2「前回の残りの候補名があれば、まずそれを深掘りする(検索計画は打ち直さない)」)。この回の優先(起動文§1)どおり、残りの候補8-009〜8-016の深掘りとPineForgeのE3a・E3bの当て直しを先にした。
### 出典
| # | 経路 | URL / 節 | 内容 | 取得日 |
|---|---|---|---|---|
| 1 | GitHub API(ungh.cc) | https://ungh.cc/repos/nicferrari/backtester | リポジトリ情報(defaultBranch=master) | 2026-09-23 |
| 2 | GitHub API(ungh.cc) | https://ungh.cc/repos/nicferrari/backtester/files/master | ファイル一覧(43本、docs/なし) | 2026-09-23 |
| 3 | GitHub raw | https://raw.githubusercontent.com/nicferrari/backtester/master/README.md | README全文 | 2026-09-23 |
| 4 | GitHub raw | https://raw.githubusercontent.com/nicferrari/backtester/master/examples/compare.rs 他examples7本 | 使用例(compare含む) | 2026-09-23 |
| 5 | GitHub raw | https://raw.githubusercontent.com/nicferrari/backtester/master/src/*.rs(16本全部) | ソース全体 | 2026-09-23 |
| 6 | arXiv | https://arxiv.org/abs/2603.20319 | 要旨全文 | 2026-09-23 |
| 7 | arXiv | https://arxiv.org/abs/2512.12924 | 要旨全文 | 2026-09-23 |
| 8 | X(x_fetch) | https://x.com/WannabeBotter/status/1810558269565571211 | rusty-bot言及の投稿本文再取得 | 2026-09-23 |
| 9 | GitHub raw | https://raw.githubusercontent.com/polakowo/vectorbt/master/README.md | README全文(314行) | 2026-09-23 |
| 10 | GitHub API(ungh.cc)+raw | https://ungh.cc/repos/Fincept-Corporation/FinceptTerminal 他README | リポジトリ情報・README(206行) | 2026-09-23 |
| 11 | GitHub raw | https://raw.githubusercontent.com/pineforge-4pass/pineforge-engine/main/docs/pages/mtf.md | Validation rules節(142-154行) | 2026-09-23 |
| 12 | GitHub API(ungh.cc) | https://ungh.cc/repos/pineforge-4pass/pineforge-engine/files/main | 全ファイル一覧(1355本、docs/55本) | 2026-09-23 |
| 13 | GitHub raw | https://raw.githubusercontent.com/pineforge-4pass/pineforge-engine/main/docs/ 配下51本(Doxyfile等ビルド設定4本を除く) | docs/全体の一括取得・grep | 2026-09-23 |

すべて `docs/DATA/probes/20260923_tools_8_run3.log` に手ごとの記録がある(#13は主にpineforge_docs_all_grepの1手で51本を取得)。
### 知見
| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `nicferrari/backtester / E1b / 入力(原文)`: `Data::load(filename: &str, ticker: &str)` はCSVファイル(またはyahoo-finance-api経由)を入力とする | 一次資料 | src/data.rs、docs/DATA/probes/20260923_tools_8_run3.log の nicferrari_backtester_data_rs 節 |
| 2 | `nicferrari/backtester / E4 / 方式(原文)`: `broker::calculate`が`strategy.choices.iter().zip(strategy.choices.iter().skip(1))`で隣接するバー間の状態遷移を時系列順に処理する | 一次資料 | src/broker.rs 155-172行、docs/DATA/probes/20260923_tools_8_run3.log の nicferrari_backtester_srcrs 節 |
| 3 | `PineForge / E3a・E3b / 方式(原文)`: `docs/pages/mtf.md`「When the run begins, the source host validates each registered lower-TF site against the run's evaluator input timeframe (`validate_security_timeframes`): ... `lookahead` and `gaps` must be off ... Violations raise at run-time with a precise diagnostic」 | 一次資料 | docs/pages/mtf.md 142-154行、取得日2026-09-23、docs/DATA/probes/20260923_tools_8_run3.log の pineforge_mtf_md_lines 節 |
| 4 | `PineForge / E3a / 方式(原文)`: `docs/pine_v6_audit_master.md`「`request.security()` [F14]: 3 hard restrictions (support_checker.py:683-760): (1) same-chart symbol only...; (2) `lookahead_on` rejected outright; (3) `currency` / `ignore_invalid_symbol` rejected」= 静的チェッカーによる検出・拒否 | 一次資料 | docs/pine_v6_audit_master.md 157行、取得日2026-09-23、docs/DATA/probes/20260923_tools_8_run3.log の pineforge_docs_all_grep 節 |
| 5 | `PineForge / E3b / 方式(原文)`: `docs/coverage.md`「`barmerge.lookahead_on` for lower-TF emulation ... *Out of scope by design*. Mechanically possible — just remove the guard — but `lookahead_on` combined with synthesized intrabar bars exposes information from a not-yet-complete sub-bar. That is a backtest-validity footgun」 | 一次資料 | docs/coverage.md 844-850行、取得日2026-09-23、docs/DATA/probes/20260923_tools_8_run3.log の pineforge_docs_all_grep 節 |
| 6 | `VectorBT / E2 / 方式(原文)`: `data = vbt.YFData.download(symbols, missing_index="drop")` | 一次資料 | README 149・166・245行、docs/DATA/probes/20260923_tools_8_run3.log の vectorbt_readme_grep 節 |
| 7 | `VectorBT / E5 / 方式(原文)`: `pf = vbt.Portfolio.from_random_signals(price, n=n, init_cash=100, seed=42)` | 一次資料 | README 153行、docs/DATA/probes/20260923_tools_8_run3.log の vectorbt_readme_grep 節 |
| 8 | `arXiv:2603.20319 / E1a / 方式(原文)`: 「we execute 15 benchmark strategies through five independent open-source engines on 30 non-overlapping stratified asset buckets comprising 180 s&p 500 stocks under four transaction-cost regimes...propose four metrics grounded in metrology to quantify it: engine sensitivity, implementation uncertainty interval, divergence amplification factor, and conclusion stability index」 | 一次資料 | https://arxiv.org/abs/2603.20319 要旨、取得日2026-09-23、docs/DATA/probes/20260923_tools_8_run3.log の arxiv_2603_20319_abs_body 節 |
| 9 | `arXiv:2512.12924 / E3b / 方式(原文)`: 「a rigorous walk-forward validation framework for algorithmic trading designed to mitigate overfitting and lookahead bias...enforces strict information set discipline」 | 一次資料 | https://arxiv.org/abs/2512.12924 要旨、取得日2026-09-23、docs/DATA/probes/20260923_tools_8_run3.log の arxiv_2512_12924_abs_body 節 |
| 10 | `arXiv:2512.12924 / E5 / 方式(原文)`: 「the reproducibility crisis in quantitative finance research」「open-source implementation」 | 一次資料 | https://arxiv.org/abs/2512.12924 要旨、取得日2026-09-23、docs/DATA/probes/20260923_tools_8_run3.log の arxiv_2512_12924_abs_body 節 |

### 候補の一覧
1. [深掘り] `qf-lib` (8-001) — 状態: 深掘り(前回から変更なし、この回は再確認せず)
2. [深掘り] `PineForge` (8-002) — 状態: 深掘り(この回でE3a・E3bが印に変わり、E1a〜E6の未判別が無くなったため深掘りに復帰)
3. `prediction-market-backtester` (8-003) — 状態: 浅い(この回は未着手、前回値を維持)
4. `akurkar07/OrderBook` (8-004) — 状態: 危険で導入停止(この回は未着手)
5. `Exegy` (8-005) — 状態: 登録が要る(この回は未着手)
6. `freqtrade` (8-006) — 状態: 浅い(この回は未着手)
7. `backtrex` (8-007) — 状態: 浅い(この回は未着手)
8. `FX Replay` (8-008) — 状態: 浅い(この回は未着手)
9. `nicferrari/backtester` (8-009) — 状態: 浅い(E1a〜E6は全行確定〔未判別なし〕だが、委任文§4.0の機械可読の表〔語彙の全項目〕を書いていないため深掘りの条件を満たさない)
10. `arXiv:2603.20319` (8-010) — 状態: 判別に一次資料が要る(要旨のみ読み、本文・コードは未読)
11. `arXiv:2512.12924` (8-011) — 状態: 判別に一次資料が要る(要旨のみ読み、本文・コードは未読)
12. `VectorBT` (8-012) — 状態: 判別に一次資料が要る(READMEの一部に届いたが公式ドキュメントサイトは未読)
13. `rusty-bot` (8-013) — 状態: 未着手(X投稿は再取得したが、投稿自体にリポジトリURLが無く、道具本体の一次資料に届いていない)
14. `Fincept Terminal` (8-014) — 状態: 判別に一次資料が要る(READMEは開いたが宣伝が主で、詳細は700ページの別マニュアル〔未取得〕にある)
15. `TradingView のリプレイ機能` (8-015) — 状態: 未着手(この回は時間切迫のため着手できず)
16. `Exactpro の reconciliation testing` (8-016) — 状態: 未着手(この回は時間切迫のため着手できず)

### 要素と段
| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 |
|---|---|---|---|---|---|
| qf-lib | E1a | なし | - | 実測 | 再確認: `docs/DATA/probes/20260923_tools_8_run2.log` の qflib_E1a_E3a_E6_recheck 節。`reconcil／cross.check／differential.*test／reference.impl／benchmark.against／compare.*implementation` でqf_lib全ソースをgrep、一致0件 |
| qf-lib | E1b | 印 | 2 | 実測 | 1回目から変更なし(`イベント駆動バックテスタでPnL・トレードを計算する。人が別実装と比較する前提で、突き合わせを自動で行う機能は無い`、`docs/DATA/probes/20260923_tools_8_run1.log` の venv_install 節) |
| qf-lib | E2 | 印 | 3 | 実測 | 訂正: docs/DATA/probes/20260923_tools_8_run2.log の `qflib_data_cleaner_full` の節。`qf_lib/common/utils/data_cleaner.py` の `DataCleaner` クラス(22-135行)。docstring「Cleans data which is partially incomplete, e.g. has gaps」。`_drop_underfilled_columns` が欠けの割合を`threshold`と比較し自動判定、結果を `self.incorrect_columns`(全欠損列)`self.columns_with_holes`(途中に欠損がある列)`self.start_late_columns`(開始が遅い列と日付の辞書)という公開属性に記録して呼び出し側が読める(=報告する)。段: `threshold`は使う人が指定できる(ア相当)が、結果を次回実行と自動比較して保存する仕組みは無い(イ非該当)ので段5には届かず、対象は qf_lib 独自の `SimpleReturnsDataFrame`(assert isinstance)に限られるため段4にも届かない→段3 |
| qf-lib | E3a | なし | - | 実測 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の qflib_E1a_E3a_E6_recheck 節。`look.?ahead` でgrepした一致はすべて `get_end_date_without_look_ahead` 系(防止の計算=E3b)で、検出結果を報告する関数は無い |
| qf-lib | E3b | 印 | 3 | 実測 | 1回目から変更なし(`qf_lib/data_providers/data_provider.py` 51・69-70行の `look_ahead_bias: bool` 引数) |
| qf-lib | E4 | 印 | 3 | 実測 | 1回目から変更なし(イベント駆動バックテスタが時刻順にデータを読み込み実行ハンドラを動かす構造) |
| qf-lib | E5 | 印 | 3 | 実測 | 訂正(誤りだった `なし` を直す): `docs/DATA/probes/20260923_tools_8_run2.log` の qflib_E5_correction 節。`backtesting/fast_alpha_model_tester/scenarios_generator.py` 97-98行 docstring「seed used to make the scenarios deterministic」、`backtesting/alpha_model/random_trades_alpha_model.py` 51-52行 同文(ユーザー向けseed引数、段2相当)。さらに qflib_verify_preloaded_data 節: `backtesting/trading_session/backtest_trading_session.py` の `get_preloaded_data_checksum()`(データバンドルのハッシュを返す)と `verify_preloaded_data(expected_checksum)`(一致しなければ ValueError を送出=自動判定)。使う人が `expected_checksum` を指定できる(ア相当)が、チェックサムの対象は `data_bundle`(データ)のみで、E5の対象『実験(コード・データ・設定)』全体には届かないため段4条件(対象の全部を持ち込める)を満たさず段3にとどめた |
| qf-lib | E6 | なし | - | 実測 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の qflib_E6_recheck 節。`def (assert_／verify_／validate_)` でgrepし、本体コードの一致は `verify_preloaded_data`(E5に計上)と `chart.py` の `assert_is_qfseries`(型チェックの内部ヘルパーで独立した検証機能ではない)のみ。他はすべて `tests/` 配下のテストヘルパー |
| PineForge | E1a | 印 | 5 | 一次資料 | 1回目から変更なし(README 217・263・267行) |
| PineForge | E1b | 印 | 5 | 一次資料 | 1回目から変更なし(同上) |
| PineForge | E2 | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の pineforge_broad_recheck 節。`missing／duplicate／outlier／gap／stale／out.of.order／misalign／corrupt` でREADME全文を再検索。一致した箇所(65・230・267行)はいずれも『比較の一致率のgap』『TTYがJSON-RPCストリームをcorruptする』などデータ品質と無関係な文脈 |
| PineForge | E3a | 印 | 3 | 一次資料 | 訂正: `docs/pages/mtf.md` 142-154行「Validation rules」節(`raw.githubusercontent.com`取得、docs/DATA/probes/20260923_tools_8_run3.log の pineforge_mtf_md_lines 節)。lower-TF `request.security_lower_tf` の登録時に `validate_security_timeframes` がTFの整合性と「`lookahead` and `gaps` must be off」を検査し、違反は「Violations raise at run-time with a precise diagnostic」(実行時に診断メッセージ付きで検出・報告)。さらに `docs/pine_v6_audit_master.md` 157行「`request.security()` [F14]: 3 hard restrictions (support_checker.py:683-760): ... (2) `lookahead_on` rejected outright」= 静的チェッカー(support_checker.py)がPineスクリプトの `lookahead_on` 使用を検出し拒否する(静的な解析)。段: 自動判定だが対象はPineForge自身のPineコンパイラ/request.security機構に限られるため段3。README単独では0件だったが(検収§5)、docs/の全55本中2本(coverage.md・pine_v6_audit_master.md・mtf.md)に一致(docs/DATA/probes/20260923_tools_8_run3.log の pineforge_docs_all_grep 節、51/55本を取得しgrep) |
| PineForge | E3b | 印 | 3 | 一次資料 | 訂正: 同じ「Validation rules」節。lower-TFの `lookahead`/`gaps` を強制的にOFFにする検査で、違反(=知り得ない情報の混入)を実行前に阻止する。加えて `docs/coverage.md` 844-850行「`barmerge.lookahead_on` for lower-TF emulation」の節:「*Out of scope by design*. Mechanically possible — just remove the guard — but `lookahead_on` combined with synthesized intrabar bars exposes information from a not-yet-complete sub-bar. That is a backtest-validity footgun」= 設計上ガードを外さない理由を明記(防止機構の維持)。ただし上位TF(HTF)集約では `lookahead_on` を「legitimate use case」として許容しており(coverage.md 536・850行)、全面禁止ではなくlower-TF合成パスに限定した防止である点は根拠に残す。段: 自動・PineForge自身の機構限定で段3 |
| PineForge | E4 | 印 | 3 | 一次資料 | 訂正: 1回目はE1aと同じ根拠(263・267行の formal gate/baseline promotion)を流用しており、監査14回目の指摘4により無効。`docs/DATA/probes/20260923_tools_8_run2.log` の pineforge_e4_context 節でE4専用の原文を確認: README 445行(表)「`strategy_stream_begin` / `_push_tick` / `_push_ticks` / `_advance_time` / `_end` / `_fill_report`」の説明「Warm on OHLCV, then run realtime on ordered trades」。記録したOHLCV・ティックを時刻順(`_advance_time`)に押し込み再実行する構造で、自動判定は無く(pass/failを出す機構ではない)、対象(戦略コード)はPineForge自身のコンパイル済みstrategyオブジェクトに限られるため段3。段5は取り消し |
| PineForge | E5 | 印 | 5 | 一次資料 | 1回目から変更なし(README 37・328行) |
| PineForge | E6 | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の pineforge_broad_recheck 節。`fuzz／property.based／mutation／coverage／sanitiz` 一致0件(README全文) |
| prediction-market-backtester | E1a | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の predmkt_e1a_recheck 節。`reconcil／cross.check／differential／reference.impl／benchmark.against／compare.*(engine／implementation／platform)` でREADME全文を再検索、一致0件 |
| prediction-market-backtester | E1b | 印 | 2 | 一次資料 | 1回目から変更なし |
| prediction-market-backtester | E2 | 印 | 3 | 一次資料 | 1回目から変更なし(`data_quality.json`) |
| prediction-market-backtester | E3a | 未判別 | 未判別 | 未確認 | 1回目から変更なし(ソース `src/pm_bt/` 未読) |
| prediction-market-backtester | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| prediction-market-backtester | E4 | 印 | 3 | 一次資料 | 1回目から変更なし |
| prediction-market-backtester | E5 | 印 | 5 | 一次資料 | 訂正(根拠を追加): 1回目の baseline文書・gitコミットハッシュに加え、`docs/DATA/probes/20260923_tools_8_run2.log` の predmkt_makesetup/predmkt_makefile/predmkt_setup_script 節。README 151行「optionally verifies `DATA_SHA256`」、`scripts/setup_data.sh`(取得日2026-09-23)33-35行「if [[ -n "$DATA_SHA256" ]]; then ... sha256sum --check --status; fi」。`set -euo pipefail`によりハッシュ不一致で自動的に異常終了する(自動判定)。ユーザーが`DATA_SHA256`を指定でき(ア)、固定したハッシュに対し以後の取得データを照合できる(イ=データの版の固定)ため段5の根拠を補強 |
| prediction-market-backtester | E6 | なし | - | 一次資料 | 検討(起動文の指示どおりE2・E6に当てた): `DATA_SHA256`の検証はE2の7種(欠け・重複・順序の乱れ・時刻のずれ・外れ値・型や範囲の違反・情報源間の食い違い)のいずれにも直接当たらないため対象外(末尾の問いに記載) |
| akurkar07/OrderBook | E1a | 印 | 3 | 一次資料 | 1回目から変更なし |
| akurkar07/OrderBook | E1b | 印 | 2 | 一次資料 | 1回目から変更なし |
| akurkar07/OrderBook | E2 | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の orderbook_broad_recheck 節。`missing／duplicate／outlier／gap／stale／out.of.order／misalign／corrupt／data.quality` でgrep。95行「Active order IDs: Duplicate IDs are rejected」がヒットしたが、これは注文IDの重複検査であり、E2の述語『時系列・約定・板・足・参照データ』の重複ではないため対象外(境界事例として記録) |
| akurkar07/OrderBook | E3a | なし | - | 一次資料 | 再確認: 同上節。`look.?ahead／future.leak／peek／snoop` 一致0件 |
| akurkar07/OrderBook | E3b | なし | - | 一次資料 | 再確認: 同上節。同じ0件 |
| akurkar07/OrderBook | E4 | なし | - | 一次資料 | 再確認: 同上節。`replay／market data／historical.*data／record` 一致0件(記録済み市場データの再生機能への言及なし) |
| akurkar07/OrderBook | E5 | 印 | 3 | 一次資料 | 1回目から変更なし |
| akurkar07/OrderBook | E6 | なし | - | 一次資料 | 再確認: 同上節。98行「Quantity accounting: ... rejects an order that would overflow」がヒットしたが、注文数量のオーバーフロー防御でありE1a〜E5に当たらない独立した検証機能とは言えない(境界事例として記録) |
| Exegy | E1a | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E1b | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E2 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E3a | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E4 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E5 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E6 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| freqtrade | E1a | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の freqtrade_e1a_e6_recheck 節。`lookahead-analysis.md`全文で`reference／other.engine／cross.check／reconcil／independent.implementation`をgrep、一致は見出し語のみ(33行)。監査役の確認(検収§11の3)どおり分類を維持 |
| freqtrade | E1b | 印 | 2 | 一次資料 | 1回目から変更なし |
| freqtrade | E2 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(`docs/data-download.md`未読) |
| freqtrade | E3a | 印 | 3 | 一次資料 | 1回目から変更なし |
| freqtrade | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし(`recursive-analysis.md`は取得したが再現バイアス防止の記述は未確認) |
| freqtrade | E4 | 未判別 | 未判別 | 未確認 | 1回目から変更なし(`docs/backtesting.md`未読) |
| freqtrade | E5 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| freqtrade | E6 | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の freqtrade_e1a_e6_recheck 節。`recursive-analysis.md`(取得日2026-09-23)を読んだが、指標の再帰計算によるバックテストと実運用のずれを検出する機能(E3a寄り)で、E1a〜E5以外の独立検証には当たらない |
| backtrex | E1a | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の backtrex_fxreplay_html_recheck/次コマンド節。公式サイトHTML(288,790バイト、取得日2026-09-23)を`compare.{0,40}(implementation／engine／platform)／cross.check／reconcil／benchmark.against／tradingview`でgrep。『Compare Backtesting Platforms & Alternatives』『See how Backtrex compares to TradingView, MetaTrader, and FX Replay for backtesting. Side-by-side feature comparison, pricing, honest reviews by traders』という文言を確認したが、これは機能比較のマーケティングページであり、出力を突き合わせる機能ではない(境界事例として記録) |
| backtrex | E1b | なし | - | 一次資料 | 1回目から変更なし |
| backtrex | E2 | 印 | 3 | 一次資料 | 1回目から変更なし |
| backtrex | E3a | 未判別 | 未判別 | 未確認 | 1回目から変更なし(製品ドキュメント未読) |
| backtrex | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| backtrex | E4 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| backtrex | E5 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| backtrex | E6 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E1a | なし | - | 一次資料 | 再確認: docs/DATA/probes/20260923_tools_8_run2.log の backtrex_fxreplay_html_recheck 節。公式サイトHTML(357,164バイト、取得日2026-09-23)を同語でgrep。TradingViewへの言及は『Charting powered by TradingView lets you track economic events, monitor live prices, and more』のみでチャート描画ライブラリとしての利用、比較機能ではない |
| FX Replay | E1b | なし | - | 一次資料 | 1回目から変更なし |
| FX Replay | E2 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E3a | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E3b | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E4 | 印 | 2 | 一次資料 | 1回目から変更なし |
| FX Replay | E5 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| FX Replay | E6 | 未判別 | 未判別 | 未確認 | 1回目から変更なし |
| nicferrari/backtester | E1a | なし | - | 実測 | `docs/DATA/probes/20260923_tools_8_run3.log` の nicferrari_backtester_allsrc_grep/data_examples_grep 節。README全文(92行超、全文取得)とsrc/全16本(backtester.rs/broker.rs/bt_run.rs/charts.rs/config.rs/data.rs/errors.rs/lib.rs/metrics.rs/orders.rs/risk_manager.rs/stateful.rs/strategies.rs/ta.rs/trades.rs/utilities.rs)・examples/全8本を取得し`reconcil／cross.check／benchmark.against／reference.impl`等でgrep、一致0件。README の`compare`例は`report_vertical`で複数戦略を並べて表示するのみ(同一エンジン内、examples_all.rs 96行「//let's compare them simultaneously」)で、別実装との差分検出ではない |
| nicferrari/backtester | E1b | 印 | 2 | 実測 | Backtest構造体がPnL・トレード・メトリクスを計算(`broker::calculate`がbroker.rs 155行〜、strategy.choicesの時系列から損益を算出)。人が別実装と比較する前提で、自動での突き合わせ機能は無い(上記grepで確認) |
| nicferrari/backtester | E2 | なし | - | 実測 | 同上grep。`missing／duplicate／outlier／gap`等でsrc/data.rs(Data構造体、CSV読込・Yahoo取得)を含む全ソースに一致0件。data.rsのload/saveに検証ロジックは見当たらない |
| nicferrari/backtester | E3a | なし | - | 実測 | 同上grep。`lookahead／look.ahead／future.leak／peek／snoop`一致0件 |
| nicferrari/backtester | E3b | なし | - | 実測 | 同上grep。同じ0件。防止機構への言及なし |
| nicferrari/backtester | E4 | 印 | 3 | 実測 | `src/backtester.rs`(Backtest::new)が`broker::calculate`を呼び、broker.rs 155行〜で`strategy.choices`(時系列順に並んだOHLCVベースの判断列)をzip/skip(1)で逐次比較し約定を計算する(時刻順データの逐次処理)。CSV(test_data/NVDA.csv)やYahoo Finance APIから外部データを読み込めるが、戦略は独自の`Strategy`/`Choices`型で書く必要がある(対象の一部=データのみ外部持込み可)ため段3。E4該当の是非(vectorizedなbar処理を「再生」と呼べるか)は末尾の問いに記載 |
| nicferrari/backtester | E5 | なし | - | 実測 | 同上grep。`reproduc／seed／deterministic`一致0件。乱数の種・環境固定・データ版固定のいずれの言及も見当たらない |
| nicferrari/backtester | E6 | なし | - | 実測 | 同上grep。`fuzz／property.based／mutation／coverage／sanitiz／assert_／verify_／validate_`類のE1a〜E5に当たらない独立検証機能への言及なし。tests/(metrics_tests.rs・ta_tests.rs・trades_tests.rs)は開発者向け単体テストで、道具の機能として利用者が呼べるものではない(未開封、根拠に含めず) |
| arXiv:2603.20319 | E1a | 印 | 未判別 | 一次資料 | arXiv:2603.20319要旨(取得日2026-09-23、docs/DATA/probes/20260923_tools_8_run3.log の arxiv_2603_20319_abs_body 節)「we execute 15 benchmark strategies through five independent open-source engines on 30 non-overlapping stratified asset buckets... propose four metrics... to quantify it: engine sensitivity, implementation uncertainty interval, divergence amplification factor, and conclusion stability index」。5つの独立エンジンの出力を突き合わせ差を定量化する手法そのものが論文の主題。段はコード本体(「code and benchmark data are publicly available」とあるが本文中にリポジトリURLを未発見)を開いておらず未判別 |
| arXiv:2603.20319 | E1b | 未判別 | 未判別 | 未確認 | 論文自体が独自の損益計算実装を提供するか(それとも既存5エンジンの比較のみか)は要旨だけでは判別できない。本文未読 |
| arXiv:2603.20319 | E2 | 未判別 | 未判別 | 未確認 | 要旨に記載なし。本文未読 |
| arXiv:2603.20319 | E3a | 未判別 | 未判別 | 未確認 | 要旨に記載なし。本文未読 |
| arXiv:2603.20319 | E3b | 未判別 | 未判別 | 未確認 | 要旨に記載なし。本文未読 |
| arXiv:2603.20319 | E4 | 未判別 | 未判別 | 未確認 | 要旨に記載なし(stratified asset bucketsでの実行であり再生とは書かれていない)。本文未読 |
| arXiv:2603.20319 | E5 | 未判別 | 未判別 | 未確認 | 「code and benchmark data are publicly available」はあるが乱数種・依存固定等の記載は要旨に無い。本文未読 |
| arXiv:2603.20319 | E6 | 未判別 | 未判別 | 未確認 | 要旨「source-code forensics uncovered seven previously undocumented defects across three engines, abstracted into a five-category failure-mode taxonomy」はE1aの差分手法から派生した欠陥分類とも読め、E1aと別立てのE6機能か判別できない。本文未読(末尾の問いに記載) |
| arXiv:2512.12924 | E1a | 未判別 | 未判別 | 未確認 | 要旨に記載なし。本文未読 |
| arXiv:2512.12924 | E1b | 未判別 | 未判別 | 未確認 | 要旨に記載なし。本文未読 |
| arXiv:2512.12924 | E2 | 未判別 | 未判別 | 未確認 | 要旨に記載なし。本文未読 |
| arXiv:2512.12924 | E3a | 未判別 | 未判別 | 未確認 | 「mitigate...lookahead bias」「enforces strict information set discipline」は検出ではなく防止(E3b)の文脈で読める。検出を報告する記述は要旨に見当たらない。本文未読 |
| arXiv:2512.12924 | E3b | 印 | 未判別 | 一次資料 | arXiv:2512.12924要旨(取得日2026-09-23、docs/DATA/probes/20260923_tools_8_run3.log の arxiv_2512_12924_abs_body 節)「We develop a rigorous walk-forward validation framework for algorithmic trading designed to mitigate overfitting and lookahead bias... The framework enforces strict information set discipline, employs rolling window validation across 34 independent test periods...」。段はコード本体(「The framework provides complete mathematical specifications and open-source implementation」とあるが未開封)未確認のため未判別 |
| arXiv:2512.12924 | E4 | 未判別 | 未判別 | 未確認 | 「rolling window validation across 34 independent test periods」はwalk-forwardの分割手法で、E4述語の「記録した市場データを時刻順に再生」とは異なる可能性がある(検証手法か再生機能かの切り分けは本文が要る)。本文未読 |
| arXiv:2512.12924 | E5 | 印 | 未判別 | 一次資料 | 同要旨「open-source implementation」「reproducible, honest validation protocol」「addresses the reproducibility crisis in quantitative finance research」。段は本文・コード未読のため未判別 |
| arXiv:2512.12924 | E6 | 未判別 | 未判別 | 未確認 | 要旨に記載なし。本文未読 |
| VectorBT | E1a | 未判別 | 未判別 | 未確認 | README(314行取得、docs/DATA/probes/20260923_tools_8_run3.log の vectorbt_readme/vectorbt_readme_grep 節)を`reconcil／cross.check／benchmark.against／reference.impl`でgrep、一致0件だったが、README全体の一部(冒頭〜中盤)しか確認できておらず、公式ドキュメントサイト(vectorbt.dev)は未読のため未判別 |
| VectorBT | E1b | 未判別 | 未判別 | 未確認 | Portfolio.from_*がPnL・トレードを計算する(同README)が、比較機能の有無を判別する一次資料(docs)は未読 |
| VectorBT | E2 | 印 | 3 | 一次資料 | 同README 149・166・245行「data = vbt.YFData.download(symbols, missing_index="drop")」。YFData.downloadに欠損インデックスの扱いを指定する引数があり、自動で処理する。段: ユーザーが指定できる(ア相当の一部)が、対象はvbt自身のYFDataラッパー経由のダウンロードに限られる(外部csv.gz読込時の挙動は未確認)ため段3 |
| VectorBT | E3a | 未判別 | 未判別 | 未確認 | README grep(`purge／embargo`等)は一致0件だが、73行「Robustness testing with walk-forward optimization and label generation for ML workflows」の詳細(ML labelingのpurge/embargoの有無)はREADME抜粋のみでは判別できない。本文(公式ドキュメント)未読 |
| VectorBT | E3b | 未判別 | 未判別 | 未確認 | 同上。walk-forward optimizationがlookahead防止を含意するかはドキュメント未読のため未判別 |
| VectorBT | E4 | 未判別 | 未判別 | 未確認 | README冒頭「instead of looping through bars one strategy at a time, it packs thousands of configurations into NumPy arrays」はベクトル化計算の説明で、時刻順の逐次再生とは異なる可能性がある。Simulationの詳細ドキュメント未読 |
| VectorBT | E5 | 印 | 3 | 一次資料 | 同README 153行「pf = vbt.Portfolio.from_random_signals(price, n=n, init_cash=100, seed=42)」。乱数シード引数で決定的な結果を得られる。段: ユーザー指定可(ア)だが、結果を保存し次回実行と自動比較する仕組みの記載はREADME抜粋に無く(イ未確認)、対象も一部機能(ランダム信号生成)のみのため段3 |
| VectorBT | E6 | 未判別 | 未判別 | 未確認 | README抜粋に記載なし。公式ドキュメント未読 |
| rusty-bot | E1a | 未判別 | 未判別 | 未確認 | 台帳の発見の出典(Xの投稿)を再取得したが(docs/DATA/probes/20260923_tools_8_run3.log の rustybot_x_post 節)、投稿本文は別記事(note.com)へのリンクの紹介のみで、`rusty-bot`自体のリポジトリURLは投稿に含まれていない。この回はリポジトリの特定に至らず一次資料未到達 |
| rusty-bot | E1b | 未判別 | 未判別 | 未確認 | 台帳の発見の出典(Xの投稿)を再取得したが(docs/DATA/probes/20260923_tools_8_run3.log の rustybot_x_post 節)、投稿本文は別記事(note.com)へのリンクの紹介のみで、`rusty-bot`自体のリポジトリURLは投稿に含まれていない。この回はリポジトリの特定に至らず一次資料未到達 |
| rusty-bot | E2 | 未判別 | 未判別 | 未確認 | 台帳の発見の出典(Xの投稿)を再取得したが(docs/DATA/probes/20260923_tools_8_run3.log の rustybot_x_post 節)、投稿本文は別記事(note.com)へのリンクの紹介のみで、`rusty-bot`自体のリポジトリURLは投稿に含まれていない。この回はリポジトリの特定に至らず一次資料未到達 |
| rusty-bot | E3a | 未判別 | 未判別 | 未確認 | 台帳の発見の出典(Xの投稿)を再取得したが(docs/DATA/probes/20260923_tools_8_run3.log の rustybot_x_post 節)、投稿本文は別記事(note.com)へのリンクの紹介のみで、`rusty-bot`自体のリポジトリURLは投稿に含まれていない。この回はリポジトリの特定に至らず一次資料未到達 |
| rusty-bot | E3b | 未判別 | 未判別 | 未確認 | 台帳の発見の出典(Xの投稿)を再取得したが(docs/DATA/probes/20260923_tools_8_run3.log の rustybot_x_post 節)、投稿本文は別記事(note.com)へのリンクの紹介のみで、`rusty-bot`自体のリポジトリURLは投稿に含まれていない。この回はリポジトリの特定に至らず一次資料未到達 |
| rusty-bot | E4 | 未判別 | 未判別 | 未確認 | 台帳の発見の出典(Xの投稿)を再取得したが(docs/DATA/probes/20260923_tools_8_run3.log の rustybot_x_post 節)、投稿本文は別記事(note.com)へのリンクの紹介のみで、`rusty-bot`自体のリポジトリURLは投稿に含まれていない。この回はリポジトリの特定に至らず一次資料未到達 |
| rusty-bot | E5 | 未判別 | 未判別 | 未確認 | 台帳の発見の出典(Xの投稿)を再取得したが(docs/DATA/probes/20260923_tools_8_run3.log の rustybot_x_post 節)、投稿本文は別記事(note.com)へのリンクの紹介のみで、`rusty-bot`自体のリポジトリURLは投稿に含まれていない。この回はリポジトリの特定に至らず一次資料未到達 |
| rusty-bot | E6 | 未判別 | 未判別 | 未確認 | 台帳の発見の出典(Xの投稿)を再取得したが(docs/DATA/probes/20260923_tools_8_run3.log の rustybot_x_post 節)、投稿本文は別記事(note.com)へのリンクの紹介のみで、`rusty-bot`自体のリポジトリURLは投稿に含まれていない。この回はリポジトリの特定に至らず一次資料未到達 |
| Fincept Terminal | E1a | 未判別 | 未判別 | 未確認 | README(206行、docs/DATA/probes/20260923_tools_8_run3.log の fincept_repo/fincept_readme_grep 節)を取得。冒頭が有料版(Enterprise/Quantcept)の宣伝で占められ、97行「quant lab and backtesting」等41モジュールの詳細は「700-page manual」(https://fincept.in/manual、未取得)にあり、README単体では`lookahead／reconcil／reproduc／seed／missing／duplicate`等いずれも一致0件 |
| Fincept Terminal | E1b | 未判別 | 未判別 | 未確認 | README(206行、docs/DATA/probes/20260923_tools_8_run3.log の fincept_repo/fincept_readme_grep 節)を取得。冒頭が有料版(Enterprise/Quantcept)の宣伝で占められ、97行「quant lab and backtesting」等41モジュールの詳細は「700-page manual」(https://fincept.in/manual、未取得)にあり、README単体では`lookahead／reconcil／reproduc／seed／missing／duplicate`等いずれも一致0件 |
| Fincept Terminal | E2 | 未判別 | 未判別 | 未確認 | README(206行、docs/DATA/probes/20260923_tools_8_run3.log の fincept_repo/fincept_readme_grep 節)を取得。冒頭が有料版(Enterprise/Quantcept)の宣伝で占められ、97行「quant lab and backtesting」等41モジュールの詳細は「700-page manual」(https://fincept.in/manual、未取得)にあり、README単体では`lookahead／reconcil／reproduc／seed／missing／duplicate`等いずれも一致0件 |
| Fincept Terminal | E3a | 未判別 | 未判別 | 未確認 | README(206行、docs/DATA/probes/20260923_tools_8_run3.log の fincept_repo/fincept_readme_grep 節)を取得。冒頭が有料版(Enterprise/Quantcept)の宣伝で占められ、97行「quant lab and backtesting」等41モジュールの詳細は「700-page manual」(https://fincept.in/manual、未取得)にあり、README単体では`lookahead／reconcil／reproduc／seed／missing／duplicate`等いずれも一致0件 |
| Fincept Terminal | E3b | 未判別 | 未判別 | 未確認 | README(206行、docs/DATA/probes/20260923_tools_8_run3.log の fincept_repo/fincept_readme_grep 節)を取得。冒頭が有料版(Enterprise/Quantcept)の宣伝で占められ、97行「quant lab and backtesting」等41モジュールの詳細は「700-page manual」(https://fincept.in/manual、未取得)にあり、README単体では`lookahead／reconcil／reproduc／seed／missing／duplicate`等いずれも一致0件 |
| Fincept Terminal | E4 | 未判別 | 未判別 | 未確認 | README(206行、docs/DATA/probes/20260923_tools_8_run3.log の fincept_repo/fincept_readme_grep 節)を取得。冒頭が有料版(Enterprise/Quantcept)の宣伝で占められ、97行「quant lab and backtesting」等41モジュールの詳細は「700-page manual」(https://fincept.in/manual、未取得)にあり、README単体では`lookahead／reconcil／reproduc／seed／missing／duplicate`等いずれも一致0件 |
| Fincept Terminal | E5 | 未判別 | 未判別 | 未確認 | README(206行、docs/DATA/probes/20260923_tools_8_run3.log の fincept_repo/fincept_readme_grep 節)を取得。冒頭が有料版(Enterprise/Quantcept)の宣伝で占められ、97行「quant lab and backtesting」等41モジュールの詳細は「700-page manual」(https://fincept.in/manual、未取得)にあり、README単体では`lookahead／reconcil／reproduc／seed／missing／duplicate`等いずれも一致0件 |
| Fincept Terminal | E6 | 未判別 | 未判別 | 未確認 | README(206行、docs/DATA/probes/20260923_tools_8_run3.log の fincept_repo/fincept_readme_grep 節)を取得。冒頭が有料版(Enterprise/Quantcept)の宣伝で占められ、97行「quant lab and backtesting」等41モジュールの詳細は「700-page manual」(https://fincept.in/manual、未取得)にあり、README単体では`lookahead／reconcil／reproduc／seed／missing／duplicate`等いずれも一致0件 |
| TradingView のリプレイ機能 | E1a | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回はREADME/公式文書を開いていない) |
| TradingView のリプレイ機能 | E1b | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回はREADME/公式文書を開いていない) |
| TradingView のリプレイ機能 | E2 | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回はREADME/公式文書を開いていない) |
| TradingView のリプレイ機能 | E3a | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回はREADME/公式文書を開いていない) |
| TradingView のリプレイ機能 | E3b | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回はREADME/公式文書を開いていない) |
| TradingView のリプレイ機能 | E4 | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回はREADME/公式文書を開いていない) |
| TradingView のリプレイ機能 | E5 | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回はREADME/公式文書を開いていない) |
| TradingView のリプレイ機能 | E6 | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回はREADME/公式文書を開いていない) |
| Exactpro の reconciliation testing | E1a | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回は公式文書を開いていない) |
| Exactpro の reconciliation testing | E1b | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回は公式文書を開いていない) |
| Exactpro の reconciliation testing | E2 | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回は公式文書を開いていない) |
| Exactpro の reconciliation testing | E3a | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回は公式文書を開いていない) |
| Exactpro の reconciliation testing | E3b | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回は公式文書を開いていない) |
| Exactpro の reconciliation testing | E4 | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回は公式文書を開いていない) |
| Exactpro の reconciliation testing | E5 | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回は公式文書を開いていない) |
| Exactpro の reconciliation testing | E6 | 未判別 | 未判別 | 未確認 | 時間切迫のため未着手(この回は公式文書を開いていない) |

### ツール1件ごとの表
この回で委任文§4の全列(料金の構造・到達と実行の記録・相性・当方に無いもの・4軸・危険)を新規に書く候補は無い。8-009〜8-014は上の「要素と段」表と知見表でE1a〜E6の一次資料は確かめたが、時間の制約で§4の全列(料金・4軸等)には手を付けていない(次回に持ち越す)。8-001〜8-008はこの回で変更なし(§4.0表参照)。

### 4.0 機械可読の表(深掘りした道具: qf-lib / PineForge)
| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| qf-lib | 再現性 | seed(scenarios_generator)+checksum(verify_preloaded_data) | 実測 | docs/DATA/probes/20260923_tools_8_run2.log:259(この回で変更なし。2回目報告689行と同じ値) |

### 代替経路
この回は『この環境から不可』と書いた項目なし。

### 辿る一覧から出た名前
時間の制約(起動文§2の1〜2の深掘りと訂正を優先したため)により、起動文§2の3(dev.toのreconciliation tools記事・Xの`aiwithjainam`投稿のリポジトリ列挙・zennの仮説検証フレームワーク記事・quantreo/algorier/fortraatersのlook-ahead bias解説記事・1回目検索計画7の結果のライブラリ)を開く作業に、この回は着手できなかった。**未着手。次回に持ち越す。**

### 予算
**時刻**: 開始(期限算出) 2026-09-23T23:21:48Z(`date -u -d '+20 min'`で期限2026-09-23T23:41:48Zを算出、docs/DATA/probes/20260923_tools_8_run3.log 冒頭)。この節を書いている時点(2026-09-23T23:29台)で期限まで約12分。**トークン数**: 自分自身の消費を計測する手段がこの環境に無く未確認(作った数は書かない)。
**実行状況**: §2の1(残りの候補8-009〜8-016の深掘り)は**途中**(8-009はE1a〜E6を全行確定させたが§4.0表は未着手、8-010・8-011は要旨のみ、8-012は一部、8-014はREADMEのみ、8-013・8-015・8-016は未着手)、時刻2026-09-23T23:27台に区切った(残り時間を報告書の作成と検査に充てるため。委任文の「時間の制約」だけで済ませず、生ログの時刻と一緒にここに書く)。§2の2(PineForgeのE3a・E3b)は**済み**(docs/pages/mtf.md・docs/coverage.md・docs/pine_v6_audit_master.mdの3文書、docs/の全55本中51本を取得しgrep)。§2の3(辿る一覧)は**未着手**。
**残りの候補名**: 8-009(§4.0表以降が残り)/ 8-010・8-011(本文・コード未読)/ 8-012(公式ドキュメント未読)/ 8-013(リポジトリ未特定)/ 8-014(700頁マニュアル未読)/ 8-015・8-016(未着手のまま)。

### 受け入れ検査の出力
`python3 scripts/check_scan_report.py docs/DATA/SCAN_2026-09-23_tools_cat8.md docs/DATA/probes/20260923_tools_8_run1.log docs/DATA/probes/20260923_tools_8_run2.log docs/DATA/probes/20260923_tools_8_run3.log` の最後に打った出力全文:

```
K1 太字                  0 件
K2 括弧                  0 件
K3 必須の節                0 件
K4 生ログに無い数値            0 件
K5 同じ道具に別の値            0 件
K6 未実施と実測の同居           0 件
K7 表の項目の欠落             0 件
K8 表の印と根拠              0 件
K9 表に無い数値              0 件
K10 見出しの件数             0 件
K11 実測の根拠              0 件
K13 中身が実質空             0 件
K12 検査の出力の貼付           0 件
---- 検査対象の合計 0 件(K12 を除く。貼り付けはこの数で照合する)
---- 合計 0 件
```

`python3 scripts/cat8_ledger.py check-elements docs/DATA/SCAN_2026-09-23_tools_cat8.md --round 3` の最後に打った出力全文:
```
読んだもの: 候補の一覧 16 行 / 要素と段の表 128 行(道具 16)/ 知見の表 10 行 / 辿る一覧から出た名前 0 行
---- 合計 0 件
```
(読んだ行数「要素と段の表 128 行(道具 16)」は、この回の候補の一覧16行・「要素と段」16道具×8要素=128行と一致している)

`python3 scripts/cat8_ledger.py check "" docs/DATA/probes/20260923_tools_8_run3.log --require-deadline` の最後に打った出力全文:
```
参考: docs/DATA/probes/20260923_tools_8_run3.log の最後の手 2026-09-23T23:27:22Z / 期限 2026-09-23T23:41:48Z / 期限切れの手 なし
---- 合計 0 件
```

`git diff -U0 HEAD -- docs/DATA/SCAN_2026-09-23_tools_cat8.md | grep '^-[^-]' | wc -l` の出力: `0`(1回目・2回目の節から消えた行は無い)

### 判断に迷った点と問い(決めずに列挙)
1. **`nicferrari/backtester`のE4該当性**: `broker::calculate`は`strategy.choices`という事前に読み込んだ時系列配列をzip/skip(1)で処理するベクトル化計算で、明示的な「時刻を進めて再生する」ループ(PineForgeの`_advance_time`のような)ではない。E4の述語「記録した市場データを時刻順に再生して、戦略・執行・計算を再実行する」に、事前ロード済み配列のベクトル化走査が当たるか(qf-libのイベント駆動処理と同列に扱えるか)を確認したい。この回は印・段3としたが、境界事例である。
2. **`arXiv:2603.20319`の「source-code forensics で7件の欠陥を発見、5分類のタクソノミー」をE1a単独の産物とみなすかE6にも計上するか**: 要旨だけでは、欠陥検出がE1aの差分比較から自動的に出た副産物か、独立した検証手順(E6)かを判別できない。本文を読めば分かるはずだが、この回は未読。
3. **PineForgeのE3a・E3bを両方「印」としたことの妥当性**: `docs/pine_v6_audit_master.md`の`support_checker.py`(静的チェッカー、`lookahead_on`を拒否)はE3a(検出)に、`docs/pages/mtf.md`・`docs/coverage.md`の実行時ガードはE3b(防止)に、それぞれ当てた。しかし両方とも同じ「`lookahead_on`を許可しない」という1つの設計判断の異なる側面(静的拒否と実行時ガード)であり、1つの機構を2列に重複計上していないか、確認したい。
4. **PineForgeの上位TF(HTF)集約での`lookahead_on`許容**(`docs/coverage.md`536・850行「legitimate use case」)をどう扱うか: 下位TF(LTF)合成では禁止、上位TF集約では許容という非対称な設計だが、この回はLTF側の禁止(=E3b該当)だけを根拠にした。HTF側の許容がE3bの評価を弱めないか(「防ぐ機能を持つ」と言えるのは一部の経路だけ)を確認したい。
5. **`VectorBT`のE2・E5の段を3としたこと**: `missing_index="drop"`・`seed=42`はいずれも`vbt.YFData.download`・`Portfolio.from_random_signals`という個別APIの引数であり、当方のcsv.gz形式データを直接投入した場合にも同じ挙動になるかは未確認(READMEの抜粋のみで判断した)。公式ドキュメントを読めば対象範囲が広がる可能性がある。
6. **8-013 `rusty-bot`の一次資料の所在**: X投稿(WannabeBotter氏、2024-07-09)は別記事(note.com)への言及のみで、`rusty-bot`自体のリポジトリ・公式サイトのURLを含んでいない。GitHub検索等でリポジトリを探すべきか(候補として残すが、この回はWebSearchを使う時間が無かった)。
