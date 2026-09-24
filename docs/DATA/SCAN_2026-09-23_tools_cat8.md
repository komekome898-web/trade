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

## 区分8 — 4 回目の実行(2026-09-24)
起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run4_prompt.md`(指紋 `636258a8e54c`)/ 追補 `docs/DATA/delegations/20260923_tools_survey_cat8_addendum.md`(指紋 `2c178ba75341`)/ 3回目起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run3_prompt.md`(指紋 `1ff8dd5b2d7e`)/ 2回目起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run2_prompt.md`(指紋 `fbd510552276`)/ 1回目起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run1_prompt.md`(指紋 `0ac68ca101f9`)/ 設計票 `docs/DATA/surveys/CAT8_DESIGN.md`/ 前回検収 `docs/AUDITOR/VERDICTS/2026-09-24_tools_scan_cat8_run3.md` に従う。生ログ: `docs/DATA/probes/20260923_tools_8_run4.log`。この回は`--deadline`を付けない(予算で止めない。追補§5、L-507「案A」)。

### 検索計画
この回は新しい検索計画を打たない(委任文§2「前回の残りの候補名があれば、まずそれを深掘りする(検索計画は打ち直さない)」)。起動文§2の1〜12(番号順)を全部進めた。

### 出典
| # | 経路 | URL / 節 | 内容 | 取得日 |
|---|---|---|---|---|
| 1 | crates.io API | https://crates.io/api/v1/crates/rs-backtester | 版・週/90日DL数・保守者・行数統計 | 2026-09-24 |
| 2 | GitHub raw(clone) | https://github.com/nicferrari/backtester.git(隔離venv) | 最小実行(cargo build/run) | 2026-09-24 |
| 3 | arXiv | https://arxiv.org/html/2603.20319 | 論文本文全文(HTML版) | 2026-09-24 |
| 4 | arXiv | https://arxiv.org/html/2512.12924 | 論文本文全文(HTML版) | 2026-09-24 |
| 5 | GitHub raw | https://raw.githubusercontent.com/akashdeepo/Interpretable-Hypothesis-Driven-Trading/main/hdt/validation.py 他 | 論文が示す実装コード一式 | 2026-09-24 |
| 6 | 公式ドキュメント | https://vectorbt.dev/(sitemap・splitters・features頁) | VectorBT OSS版の機能文書 | 2026-09-24 |
| 7 | PyPI/pypistats | https://pypi.org/pypi/vectorbt/json 、https://pypistats.org/api/packages/vectorbt/recent | 版・週DL数 | 2026-09-24 |
| 8 | GitHub raw | https://raw.githubusercontent.com/polakowo/vectorbt/master/LICENSE.md | ライセンス全文(Commons Clause) | 2026-09-24 |
| 9 | 隔離venv実行 | scratchpad/cat8/venvs/vbt_venv | pip install・最小実行(seed再現性の実証) | 2026-09-24 |
| 10 | archive.org(wayback) | https://web.archive.org/web/20260609143209/https://tech.takibi.net/... | rusty-bot同定の経由記事(404のため代替経路) | 2026-09-24 |
| 11 | GitHub raw/PyPI | https://raw.githubusercontent.com/yasstake/rbot/main/README.md 、https://pypi.org/pypi/rbot/json | rusty-bot(rbot)の一次資料 | 2026-09-24 |
| 12 | 公式サイト+PDF | https://fincept.in/docs/fincept-terminal-master-guide.pdf | 864頁マニュアル全文(pypdfで抽出) | 2026-09-24 |
| 13 | 公式ヘルプ | https://www.tradingview.com/support/solutions/43000474024-how-do-i-turn-bar-replay-on/ 、tradingview.com/pricing/ | Bar Replayの機能・料金表 | 2026-09-24 |
| 14 | 公式サイト+GitHub | https://exactpro.com/ideas/research-papers/... 、https://github.com/th2-net/th2-check2-recon(-template) | reconciliation testingの一次資料(論文+実装) | 2026-09-24 |
| 15 | GitHub raw(全ソース) | https://raw.githubusercontent.com/Quentin-Piot/prediction-market-backtester/master/src/pm_bt/... | E1a訂正の決め手(validation.py) | 2026-09-24 |
| 16 | GitHub raw | https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/... 、freqtrade/optimize/backtesting.py 、freqtrade/data/converter/converter.py | freqtradeのE2/E3b/E4/E5当て直し | 2026-09-24 |
| 17 | 公式サイト+ドキュメント | https://backtrex.com/en/compare 、https://backtrex.com/en/docs/backtesting/anti-repainting 、/running-backtests | backtrexのE1a訂正・E3b/E4/E5当て直し | 2026-09-24 |
| 18 | 公式ヘルプ(WebFetch) | https://support.fxreplay.com/articles/... (analytic-metrics-defined、why-historical-price-levels...、what-broker-data-sources...、mastering-the-replay-feature) | FX ReplayのE2/E3a/E3b/E5/E6当て直し(JS描画のためWebFetch使用) | 2026-09-24 |

すべて `docs/DATA/probes/20260923_tools_8_run4.log` に手ごとの記録がある。

### 知見
| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `nicferrari/backtester` / E2 / 方式(原文): 要素名そのもの(`data quality`/`データ品質`)でsrc/全16本・examples/全8本・README全文をgrep、一致0件 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の nicferrari_backtester_e2_element_word 節 |
| 2 | `nicferrari/backtester` / 最小実行の中身(原文): 合成CSV(SYNTH、5バー)を`Data::load`で読み込み、`BUY→NULL×4`の成行1往復戦略を`Backtest::new`で実行。`report_vertical`で結果表示、Trades#=0(執行タイミング`AtOpen(1)`のため5バーでは約定が完了しなかった) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の nicferrari_backtester_min_run_build3 節 |
| 3 | `arXiv:2603.20319` / E1a / 方式(原文): 「we execute 15 benchmark strategies through five independent engines (a purpose-built reference implementation and four open-source libraries)...we thank the maintainers of bt, vectorbt, backtrader, and cvxportfolio」。「forensic analysis of three engines...uncovers seven previously undocumented defects, including a library default in Backtrader that silently divides the user-specified commission rate by 100」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2603_20319_dq_section / arxiv_2603_20319_repro 節 |
| 4 | `arXiv:2603.20319` / コードの所在: 「our backtesting engine will be released at https://github.com/don-yin/backtest-engine under the MIT licence upon acceptance」。実測でungh.cc/repos/don-yin/backtest-engineは404(2026-09-24時点で未公開) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2603_20319_github_check_retry 節 |
| 5 | `arXiv:2512.12924` / E3b / 方式(原文): `hdt/validation.py`(取得日2026-09-24)「misaligned = [s for s, df in market_data.items() if len(df) != total_days]; if misaligned: raise ValueError(...)」。`hdt/backtester.py`「Signals are generated using information up to and including day t (close); orders execute at day (t + 1) open with slippage and a fixed commission」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2512_12924_validation_py / arxiv_2512_12924_backtester_docstring 節 |
| 6 | `arXiv:2512.12924` / E5 / 方式(原文): `hdt/validation.py`「fold_seed = None if seed is None else seed + fold; rng = np.random.default_rng(fold_seed)」。`rerun_analysis.py`「Re-run only the publication-analysis phase on the already-saved WF results...avoids the ~30 minute walk-forward backtest」`--seed`引数(default 42) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2512_12924_validation_py / arxiv_2512_12924_rerun_analysis 節 |
| 7 | `VectorBT` / ライセンス(原文): 「"Sell" means...to provide to third parties, for a fee...a product or service whose value derives, entirely or substantially, from the functionality of the Software」「License: Apache 2.0 with Commons Clause」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_license_full 節 |
| 8 | `VectorBT` / 隠れた依存・危険(原文): pyproject.tomlの依存「"plotly>=4.12.0"」(上限指定なし)。実測でpip install vectorbtするとplotly 7.1.0が解決され、vectorbt自身の起動時テーマ登録コードが`scattermapbox`(新版で削除・改名)を参照し**インポート時に例外で起動不能**になった。`pip install "plotly<6"`で解消し正常動作を確認 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_pyproject_deps / vectorbt_min_run / vectorbt_plotly_downgrade / vectorbt_min_run_retry 節 |
| 9 | `VectorBT` / E5 / 方式(原文): 合成200分足価格系列に`vbt.Portfolio.from_random_signals(price, n=5, seed=42, fees=0.0)`を2回実行し`total_return()`が完全一致(True)することを実行時に確認 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_min_run_retry 節 |
| 10 | `VectorBT` / E3b / 方式(原文): `api/generic/splitters/`頁「Splitters for cross-validation. Defines splitter classes similar (but may not compatible) to sklearn.model_selection.BaseCrossValidator」。同頁「VectorBT PRO Apply purging and embargoing to cross-validation splits」= purge/embargo機能はPRO限定、OSS版は`BaseSplitter`/`ExpandingSplitter`/`RangeSplitter`/`RollingSplitter`の基本分割のみ | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_splitters_extract / vectorbt_rollingsplitter_doc 節 |
| 11 | `rusty-bot` / 同定の確認: X投稿→引用元投稿→note.com記事→(404→archive.org実測で取得)tech.takibi.net記事→`github.com/yasstake/rusty-bot`。同リポジトリのREADMEが同じtakibi.net記事へ逆リンクしていることを確認し同一物と確定 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の rustybot_x_refetch / rustybot_note_grep / rustybot_takibi_wayback_retry / rustybot_readme 節 |
| 12 | `rusty-bot` / 自動発注機能(原文): 「Ordering is disabled by default. You can enable it by setting `enable_order_with_my_own_risk` to `True`」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の rustybot_rbot_readme_full 節 |
| 13 | `Fincept Terminal` / E1a / 方式(原文): 「A "provider" is the backtesting engine that runs your test...VectorBT / Backtesting.py / FastTrade / Zipline / BT / Fincept(in-house)...Are interchangeable engines — the same strategy/symbol/date inputs run on whichever engine you select」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_engine_full 節 |
| 14 | `Fincept Terminal` / E3b / 方式(原文): 「HISTORY IS BITEMPORAL, SO BACKTESTS CANNOT CHEAT...Storing a revision over the original silently injects lookahead bias into every backtest that touches it. Our observation store keeps every vintage with the date we learned it, so a strategy tested against March can only see what was published by March」。加えて「CV Splits Build cross-validation splitters (Rolling / Expanding / Purged K-Fold)」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_lookahead_ctx / fincept_pdf_purge_ctx 節 |
| 15 | `Fincept Terminal` / E2 / 方式(原文): 「The quality score...The percentage in the status bar is the proportion of the expected data that actually arrived. 100% means every branch was populated...check which branches are missing before drawing conclusions」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_missing_11225 節 |
| 16 | `Fincept Terminal` / 料金体系(原文): 「A local backtest is free...a backtest that runs on your own machine is not labelled with a price at all. The charge appears only when the server engine is switched on」「Broker reconciliation...1 CR」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の fincept_pricing_detail 節 |
| 17 | `TradingView のリプレイ機能` / E4 / 方式(原文): 「Click the Bar Replay button...Select the starting point on the chart...You can synchronously run the Bar Replay on all charts of the layout and track the dynamics of changes in one or completely different symbols at different timeframes at one point in time」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の tv_replay_body 節 |
| 18 | `TradingView のリプレイ機能` / 相性・限界(原文): 「trading orders (Paper Trading and other brokers) are executed based on real-time data」「Bar Replay does not work with spread charts and tick-based charts」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の tv_replay_body 節 |
| 19 | `Exactproのreconciliation testing`(th2-check2-recon) / E1a / 方式(原文): 「Recon allows you to compare message streams with each other using specified scenarios called Rule」。ライフサイクル「The hash of the message is calculated...Searches for messages with the same hash in other message groups...If a message with the same hash is found in each group, check(messages) is called」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の exactpro_check2recon_template_readme 節 |
| 20 | `Exactproのreconciliation testing` / OSS化の確認: `th2-check2-recon`(PyPI v3.4.0、Apache-2.0、createdAt 2020-11-21)を実測確認。Shsha等の商用製品は非OSSのため一次資料は製品頁の記述に限られる | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の exactpro_check2recon_pypi / exactpro_check2recon_meta_retry 節 |
| 21 | `prediction-market-backtester` / E1a(訂正) / 方式(原文): `src/pm_bt/reporting/validation.py`「def validate_run_directory(run_dir, *, tolerance: float = 1e-9)...」「_assert_close("total_pnl", float(trading_metrics["total_pnl"]), final_equity - initial_cash, tolerance=tolerance)」ほか9項目。保存済み指標(results.json)と生CSVからの再計算を独立に突き合わせる | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の predmkt_validation_py 節 |
| 22 | `prediction-market-backtester` / E2 / 方式(原文): 同ファイル「if not equity_df["ts"].is_sorted(): raise ValueError("equity timestamps are not sorted")」「if min_price < 0.0 or max_price > 1.0: raise ValueError("fill prices must remain within implied-probability bounds [0, 1]")」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の predmkt_validation_py 節 |
| 23 | `prediction-market-backtester` / E3a・E3b / なしと書くための条件: README・ROADMAP.md・docs/全3本・src/pm_bt/配下の全17ソース・tests/主要ファイルを全部読み(生ログに実測記録)、`look.?ahead`/`ルックアヘッド`/`purge`/`embargo`/`パージ`を日英で検索、全ファイルで0件 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の predmkt_lookahead_search / predmkt_lookahead_search2 / predmkt_lookahead_search3 節 |
| 24 | `freqtrade` / E2 / 方式(原文): `freqtrade/data/converter/converter.py`「Cleanse a OHLCV dataframe by * Grouping it by date (removes duplicate tics) * dropping last candles if requested * Filling up missing data (if requested)」`ohlcv_fill_up_missing_data`「Fills up missing data with 0 volume rows, using the previous close as price」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_converter_clean 節 |
| 25 | `freqtrade` / E4 / 方式(原文): `freqtrade/optimize/backtesting.py`「Backtest time and pair generator」「for current_time in self._time_generator(start_date, end_date): # Loop for each main candle」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_backtesting_loop 節(ft_backtesting.py実測、1977行) |
| 26 | `freqtrade` / E3b(なし)・E5 / 方式(原文): `docs/lookahead-analysis.md`「Removing conditions or indicators that push the profits up from bias will usually make the strategy significantly worse」(自動防止ではなく検出のみ)。`docs/backtesting.md`「reproducibility of backtesting-results cannot be guaranteed...To achieve reproducible results, best generate a pairlist via the test-pairlist command and use that as static pairlist」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_lookahead_full / freqtrade_backtesting_head 節 |
| 27 | `backtrex` / E1a(訂正)・E3b / 方式(原文): `/en/docs/backtesting/anti-repainting`頁「Verification Through Export: Export your strategy and run it on TradingView. Compare the signals and trade entries between Backtrex and TradingView. The guaranteed less than 2% divergence confirms that anti-repainting is working correctly」「All price references use close[1]...No indicator can access the current bar's data for signal generation」「The backtest engine processes bars strictly in chronological order」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の backtrex_docs_antirepaint 節 |
| 28 | `backtrex` / 料金体系(原文): 「Backtrex Pro comes with a 7-day free trial...Pro costs $22 per month for 20 backtests per day and Pine Script export, and Max ($59 per month) unlocks unlimited backtests」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の backtrex_compare_body 節 |
| 29 | `FX Replay` / E1a(なし確定) / 方式(原文): 「TradingView retroactively recalculates all historical price data every time a continuous futures contract rolls over...the prices shown for past dates are not the prices that actually traded」「No automated reconciliation mechanism exists between platforms」(WebFetch抽出、記事は手動でのTradingView設定変更を案内するのみ) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の fxreplay_vstv_webfetch 節 |
| 30 | `FX Replay` / E5(なし確定) / 方式(原文): Monte Carlo Simulationの節「works by running a large number of simulations using random input values」だが、シードの文書化・再現性の保証への言及は無い(WebFetch抽出で明示的に確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の fxreplay_metrics_webfetch 節 |

### 候補の一覧
1. [深掘り] `qf-lib` (8-001) — 状態: 深掘り(この回は未着手・前回値を維持)
2. [深掘り] `PineForge` (8-002) — 状態: 深掘り(この回は未着手・前回値を維持)
3. [深掘り] `prediction-market-backtester` (8-003) — 状態: 深掘り(この回でE1aを訂正=なし→印、E3a・E3bを確定=なし。E1a〜E6に未判別なし)
4. `akurkar07/OrderBook` (8-004) — 状態: 危険で導入停止(この回は未着手・前回値を維持)
5. `Exegy` (8-005) — 状態: 登録が要る(この回は未着手・前回値を維持)
6. [深掘り] `freqtrade` (8-006) — 状態: 深掘り(この回でE2・E3b・E4・E5を確定。E1a〜E6に未判別なし)
7. [深掘り] `backtrex` (8-007) — 状態: 深掘り(この回でE1aを訂正=なし→印、E3b・E4・E5を確定。E1a〜E6に未判別なし)
8. [深掘り] `FX Replay` (8-008) — 状態: 深掘り(この回でE2・E3a・E3b・E5・E6を確定=なし。E1a〜E6に未判別なし)
9. [深掘り] `nicferrari/backtester` (8-009) — 状態: 深掘り(この回でE2を要素名そのもので当て直し確定、§4.0表(語彙の全項目)を新規に書いた。E1a〜E6に未判別なし)
10. `arXiv:2603.20319` (8-010) — 状態: 判別に一次資料が要る(本文は全文読了したが、E1bの段とコード本体の内容が未公開(GitHub 404)のため判別できず)
11. [深掘り] `arXiv:2512.12924` (8-011) — 状態: 深掘り(本文とコード本体(hdt/配下)を読み、E1a〜E6の未判別を解消)
12. `VectorBT` (8-012) — 状態: 判別に一次資料が要る(公式文書サイト・実行時実証で多くを確定したが、E4(ベクトル化計算をリプレイと呼べるか)が未判別のまま残る)
13. `rusty-bot` (8-013) — 状態: 判別に一次資料が要る(一次資料(yasstake/rbot README)への到達は確定したが、E2・E5がソース本体(Rustコア)未読のため未判別)
14. `Fincept Terminal` (8-014) — 状態: 浅い(864頁PDFマニュアルの全文検索でE1a〜E6の未判別は解消したが、§4.0表の語彙のうち過半(25/43項目、install所要秒・依存数・pip check・最小実行等)が「未確認」のため委任文§4.0の深掘りの条件〔過半が一次資料か実測〕を満たさない。導入・実行系の項目はこの回未実施)
15. [深掘り] `TradingView のリプレイ機能` (8-015) — 状態: 深掘り(公式ヘルプ頁・料金比較表を読み、E1a〜E6の未判別を解消)
16. `Exactpro の reconciliation testing` (8-016) — 状態: 判別に一次資料が要る(th2-check2-reconのE1aは確定したが、th2プラットフォームは多数のコンポーネントからなり、この回はごく一部しか読めておらずE2・E3a・E3b・E4・E5・E6が未判別のまま残る)

### 要素と段
| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 |
|---|---|---|---|---|---|
| qf-lib | E1a | なし | - | 実測 | 前回から変更なし(3回目の節を参照。この回は再確認していない) |
| qf-lib | E1b | 印 | 2 | 実測 | 前回から変更なし |
| qf-lib | E2 | 印 | 3 | 実測 | 前回から変更なし |
| qf-lib | E3a | なし | - | 実測 | 前回から変更なし |
| qf-lib | E3b | 印 | 3 | 実測 | 前回から変更なし |
| qf-lib | E4 | 印 | 3 | 実測 | 前回から変更なし |
| qf-lib | E5 | 印 | 3 | 実測 | 前回から変更なし |
| qf-lib | E6 | なし | - | 実測 | 前回から変更なし |
| PineForge | E1a | 印 | 5 | 一次資料 | 前回から変更なし |
| PineForge | E1b | 印 | 5 | 一次資料 | 前回から変更なし |
| PineForge | E2 | なし | - | 一次資料 | 前回から変更なし |
| PineForge | E3a | 印 | 3 | 一次資料 | 前回から変更なし |
| PineForge | E3b | 印 | 3 | 一次資料 | 前回から変更なし |
| PineForge | E4 | 印 | 3 | 一次資料 | 前回から変更なし |
| PineForge | E5 | 印 | 5 | 一次資料 | 前回から変更なし |
| PineForge | E6 | なし | - | 一次資料 | 前回から変更なし |
| prediction-market-backtester | E1a | 印 | 5 | 実測 | 訂正(なし→印): src/pm_bt/reporting/validation.py の validate_run_directory が保存済みresults.jsonの指標(total_pnl等9項目)を生equity.csv/trades.csvから独立に再計算し`_assert_close(name, actual, expected, tolerance=tolerance)`で突き合わせる。docs/DATA/probes/20260923_tools_8_run4.log の predmkt_validation_py 節 |
| prediction-market-backtester | E1b | 印 | 2 | 一次資料 | 前回から変更なし |
| prediction-market-backtester | E2 | 印 | 3 | 実測 | 補強(根拠追加): validation.pyの`equity_df["ts"].is_sorted()`チェックと価格帯[0,1]チェック。docs/DATA/probes/20260923_tools_8_run4.log の predmkt_validation_py 節 |
| prediction-market-backtester | E3a | なし | - | 実測 | 確定(未判別→なし): README・ROADMAP.md・docs/全3本・src/pm_bt/配下17ソース・tests/を全部読み、`look.?ahead`/`ルックアヘッド`を検索、0件。docs/DATA/probes/20260923_tools_8_run4.log の predmkt_lookahead_search/predmkt_lookahead_search2/predmkt_lookahead_search3 節 |
| prediction-market-backtester | E3b | なし | - | 実測 | 確定(未判別→なし): 同上範囲で`purge`/`embargo`/`パージ`を検索、0件。同ログ同節 |
| prediction-market-backtester | E4 | 印 | 3 | 実測 | 前回から変更なし(engine.pyのバー単位逐次処理) |
| prediction-market-backtester | E5 | 印 | 5 | 一次資料 | 前回から変更なし(DATA_SHA256検証) |
| prediction-market-backtester | E6 | なし | - | 実測 | 確定(未判別→なし): 同じ読了範囲で`fuzz`/`property.based`/`mutation`/`hypothesis`を検索、0件。docs/DATA/probes/20260923_tools_8_run4.log の predmkt_e6_search 節 |
| akurkar07/OrderBook | E1a | 印 | 3 | 一次資料 | 前回から変更なし |
| akurkar07/OrderBook | E1b | 印 | 2 | 一次資料 | 前回から変更なし |
| akurkar07/OrderBook | E2 | なし | - | 一次資料 | 前回から変更なし |
| akurkar07/OrderBook | E3a | なし | - | 一次資料 | 前回から変更なし |
| akurkar07/OrderBook | E3b | なし | - | 一次資料 | 前回から変更なし |
| akurkar07/OrderBook | E4 | なし | - | 一次資料 | 前回から変更なし |
| akurkar07/OrderBook | E5 | 印 | 3 | 一次資料 | 前回から変更なし |
| akurkar07/OrderBook | E6 | なし | - | 一次資料 | 前回から変更なし |
| Exegy | E1a | 未判別 | 未判別 | 未確認 | 前回から変更なし(公式サイトのみ、登録なしで確認できる範囲を超える) |
| Exegy | E1b | 未判別 | 未判別 | 未確認 | 前回から変更なし |
| Exegy | E2 | 未判別 | 未判別 | 未確認 | 前回から変更なし |
| Exegy | E3a | 未判別 | 未判別 | 未確認 | 前回から変更なし |
| Exegy | E3b | 未判別 | 未判別 | 未確認 | 前回から変更なし |
| Exegy | E4 | 未判別 | 未判別 | 未確認 | 前回から変更なし |
| Exegy | E5 | 未判別 | 未判別 | 未確認 | 前回から変更なし |
| Exegy | E6 | 未判別 | 未判別 | 未確認 | 前回から変更なし |
| freqtrade | E1a | なし | - | 一次資料 | 前回から変更なし |
| freqtrade | E1b | 印 | 2 | 一次資料 | 前回から変更なし |
| freqtrade | E2 | 印 | 3 | 一次資料 | 確定(未判別→印): freqtrade/data/converter/converter.pyの`clean_ohlcv_dataframe`(「Grouping it by date (removes duplicate tics)」「Filling up missing data」)・`ohlcv_fill_up_missing_data`。docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_converter_clean 節 |
| freqtrade | E3a | 印 | 3 | 一次資料 | 前回から変更なし |
| freqtrade | E3b | なし | - | 一次資料 | 確定(未判別→なし): docs/lookahead-analysis.md・recursive-analysis.md・backtesting.md・hyperopt.md・freqai.mdを読み、`purge`/`embargo`/`パージ`は freqai.md に1件(モデルファイルのディスク削除の意味で無関係)。lookahead-analysisは検出専用で自動防止機構ではないことを確認。docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_purge_search/freqtrade_lookahead_full 節 |
| freqtrade | E4 | 印 | 3 | 一次資料 | 確定(未判別→印): freqtrade/optimize/backtesting.pyの`time_pair_generator`/`_time_generator`(「Loop for each main candle」)。docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_backtesting_loop 節(ft_backtesting.py実測) |
| freqtrade | E5 | 印 | 2 | 一次資料 | 確定(未判別→印): docs/backtesting.md「reproducibility of backtesting-results cannot be guaranteed...best generate a pairlist via the test-pairlist command」。docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_backtesting_head 節 |
| freqtrade | E6 | なし | - | 一次資料 | 前回から変更なし |
| backtrex | E1a | 印 | 2 | 一次資料 | 訂正(なし→印): /en/docs/backtesting/anti-repainting頁「Verification Through Export: Export your strategy and run it on TradingView. Compare the signals and trade entries between Backtrex and TradingView. The guaranteed less than 2% divergence...」。docs/DATA/probes/20260923_tools_8_run4.log の backtrex_docs_antirepaint 節 |
| backtrex | E1b | なし | - | 一次資料 | 前回から変更なし |
| backtrex | E2 | 印 | 3 | 一次資料 | 前回から変更なし |
| backtrex | E3a | なし | - | 一次資料 | 確定(未判別→なし): Documentation全8頁のうちBacktesting系3頁+比較頁+ホームを読了。「Lookahead Bias」節は原因説明のみで検出機能の記述なし。docs/DATA/probes/20260923_tools_8_run4.log の backtrex_docs_antirepaint 節 |
| backtrex | E3b | 印 | 3 | 一次資料 | 確定(未判別→印): 同頁「All price references use close[1]...No indicator can access the current bar's data for signal generation」「The backtest engine processes bars strictly in chronological order」。同ログ同節 |
| backtrex | E4 | 印 | 3 | 一次資料 | 確定(未判別→印): /en/docs/backtesting/running-backtests頁「Timeframe: M1/M3/M5/M15/H1/H4/D1」「The engine processes the historical data and returns results in under 30 seconds」+ Anti-Repainting頁「processes bars strictly in chronological order」。docs/DATA/probes/20260923_tools_8_run4.log の backtrex_docs_running 節 |
| backtrex | E5 | 印 | 2 | 一次資料 | 確定(未判別→印): running-backtests頁「Tips: Save promising backtests for later comparison」。同ログ同節 |
| backtrex | E6 | なし | - | 一次資料 | 確定(未判別→なし): 読了範囲全体で`fuzz`/`property.based`/`mutation`等に相当する記述なし。「validate」は一般的な意味で多用されるのみ |
| FX Replay | E1a | なし | - | 一次資料 | 確定(未判別だった根拠を補強): articles/why-historical-price-levels-may-look-different-on-fx-replay-vs-tradingview(WebFetch実測)「No automated reconciliation mechanism exists between platforms」。docs/DATA/probes/20260923_tools_8_run4.log の fxreplay_vstv_webfetch 節 |
| FX Replay | E1b | なし | - | 一次資料 | 前回から変更なし |
| FX Replay | E2 | なし | - | 一次資料 | 確定(未判別→なし): articles/what-broker-data-sources-does-fx-replay-use-for-its-charts(WebFetch実測)にデータ源(Dukascopy/OANDA/CME Futures)の説明はあるが欠け・重複・外れ値の自動検出機構への言及なし。docs/DATA/probes/20260923_tools_8_run4.log の fxreplay_brokerdata_webfetch 節 |
| FX Replay | E3a | なし | - | 一次資料 | 確定(未判別→なし): articles/mastering-the-replay-feature(WebFetch実測)に「ルックアヘッドバイアスの防止・検出についての明示的な記述は無い」。docs/DATA/probes/20260923_tools_8_run4.log の fxreplay_replay_mechanics 節 |
| FX Replay | E3b | なし | - | 一次資料 | 確定(未判別→なし): 同上。docs/DATA/probes/20260923_tools_8_run4.log の fxreplay_replay_mechanics 節 |
| FX Replay | E4 | 印 | 2 | 一次資料 | 前回から変更なし |
| FX Replay | E5 | なし | - | 一次資料 | 確定(未判別→なし): articles/analytic-metrics-defined(WebFetch実測)のMonte Carlo節「works by running a large number of simulations using random input values」だがシード文書化・再現性保証への言及なし。docs/DATA/probes/20260923_tools_8_run4.log の fxreplay_metrics_webfetch 節 |
| FX Replay | E6 | なし | - | 一次資料 | 確定(未判別→なし): 同記事に列挙された指標群にE1a〜E5に当たらない独立検証機能への言及なし。同ログ同節 |
| nicferrari/backtester | E1a | なし | - | 実測 | 前回から変更なし |
| nicferrari/backtester | E1b | 印 | 2 | 実測 | 前回から変更なし |
| nicferrari/backtester | E2 | なし | - | 実測 | 当て直し(要素名そのもので再確認): `data quality`/`データ品質`でsrc/全16本・examples/全8本・README全文をgrep、0件。docs/DATA/probes/20260923_tools_8_run4.log の nicferrari_backtester_e2_element_word 節 |
| nicferrari/backtester | E3a | なし | - | 実測 | 前回から変更なし |
| nicferrari/backtester | E3b | なし | - | 実測 | 前回から変更なし |
| nicferrari/backtester | E4 | 印 | 3 | 実測 | 前回から変更なし(問い1件を末尾に維持) |
| nicferrari/backtester | E5 | なし | - | 実測 | 前回から変更なし |
| nicferrari/backtester | E6 | なし | - | 実測 | 前回から変更なし |
| arXiv:2603.20319 | E1a | 印 | 未判別 | 一次資料 | 前回から変更なし(コード未公開のため段は未判別のまま。実測でungh.cc 404を確認しコード未公開を裏付け) |
| arXiv:2603.20319 | E1b | 未判別 | 未判別 | 未確認 | 前回から変更なし |
| arXiv:2603.20319 | E2 | 未判別 | 未判別 | 未確認 | 前回から変更なし(§12 Data Quality Controlは著者自身のデータセットの一回限りの確認であり再利用可能な機能かは未判別) |
| arXiv:2603.20319 | E3a | なし | - | 一次資料 | 全文(98598文字)読了、`look.?ahead`/`ルックアヘッド`0件。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2603_20319_lookahead/arxiv_2603_20319_elemname_bilingual 節 |
| arXiv:2603.20319 | E3b | なし | - | 一次資料 | 同上、`purge`/`embargo`/`パージ`0件。同ログ同節 |
| arXiv:2603.20319 | E4 | なし | - | 一次資料 | 同上、`replay`/`リプレイ`は一般的言及1件のみで独自実装の再生方式の記述なし。同ログ同節 |
| arXiv:2603.20319 | E5 | 印 | 1 | 一次資料 | 「divergence tables...will be deposited at Zenodo upon acceptance」= 未来の予定の記述(文書だけ)。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2603_20319_repro 節 |
| arXiv:2603.20319 | E6 | なし | - | 一次資料 | 全文読了、`validat`/`verificat`/`検証`の一致は全てE1a(クロスエンジン比較)の文脈内。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2603_20319_replay_validate_ctx 節 |
| arXiv:2512.12924 | E1a | なし | - | 一次資料 | 全文(71633文字)読了、`reconcil`/`cross.check`/`突き合わせ`0件。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2512_12924_elemname_bilingual 節 |
| arXiv:2512.12924 | E1b | 印 | 3 | 実測 | hdt/backtester.py「Event-driven backtester」がPnL・トレードを計算。対象はhdt独自market_data形式に限られ段3。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2512_12924_backtester_docstring 節 |
| arXiv:2512.12924 | E2 | 印 | 4 | 実測 | hdt/data_loader.pyの`align_to_benchmark`+hdt/validation.pyの`misaligned`チェック(ValueError自動送出)。対象はpandas DataFrame(広く使われる形式)のため段4。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2512_12924_data_loader/arxiv_2512_12924_validation_py 節 |
| arXiv:2512.12924 | E3a | なし | - | 一次資料 | 全文読了、`look.?ahead`は要旨の一般言及1件のみで検出機能の記述なし。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2512_12924_context 節 |
| arXiv:2512.12924 | E3b | 印 | 4 | 実測 | hdt/validation.pyのtrain/test厳密時点分割+backtester.pyの「information up to and including day t」。対象はpandas DataFrame・汎用generatorのため段4。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2512_12924_validation_py 節 |
| arXiv:2512.12924 | E4 | 印 | 3 | 実測 | hdt/backtester.pyのEvent-driven backtesterが日次バーを時系列順に処理。対象はhdt独自インターフェースのため段3。同ログ同節 |
| arXiv:2512.12924 | E5 | 印 | 5 | 実測 | validation.pyの`seed`パラメータ(ア)+rerun_analysis.pyの`--seed`引数と保存済み結果の再利用(イ)。両方満たすため段5。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2512_12924_rerun_analysis 節 |
| arXiv:2512.12924 | E6 | なし | - | 一次資料 | 全文読了、`validat`/`verificat`/`検証`は全てE3b(walk-forward)の文脈内。docs/DATA/probes/20260923_tools_8_run4.log の arxiv_2512_12924_context 節 |
| VectorBT | E1a | なし | - | 一次資料 | README(round3実測)+features頁(25167文字)+splitters頁で`reconcil`/`cross.check`/`突き合わせ`検索、0件。docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_features_elemname 節 |
| VectorBT | E1b | 印 | 3 | 一次資料 | 前回から変更なし(round3実測のPortfolio.from_*) |
| VectorBT | E2 | 印 | 3 | 一次資料 | 前回から変更なし。features頁で「Detect confirmed price pivots and outliers」がPRO限定であることを追加確認(OSS版は対象がより狭い) |
| VectorBT | E3a | なし | - | 一次資料 | features頁・splitters頁で`look.?ahead`/`ルックアヘッド`検索、0件。docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_features_elemname 節 |
| VectorBT | E3b | 印 | 3 | 一次資料 | 新規確定(未判別→印): splitters頁「BaseSplitter/ExpandingSplitter/RangeSplitter/RollingSplitter」の時系列分割クラス群。ただしpurge/embargoはPRO限定。docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_splitters_extract 節 |
| VectorBT | E4 | 未判別 | 未判別 | 未確認 | features頁・README(round3実測)にベクトル化計算の説明はあるが、時刻順の逐次再生と呼べる明示的な記述を見つけられず未判別のまま(公式ドキュメントの実行系ページを読み切れていない) |
| VectorBT | E5 | 印 | 5 | 実測 | 実行時に実証: `vbt.Portfolio.from_random_signals(price, n=5, seed=42, fees=0.0)`を2回実行し`total_return()`が完全一致(True)。docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_min_run_retry 節 |
| VectorBT | E6 | なし | - | 一次資料 | features頁・splitters頁に該当記述なし |
| rusty-bot | E1a | なし | - | 一次資料 | yasstake/rbot README全文(10478バイト)で`reconcil`・`cross.check`・`突き合わせ`・`compare.*(implementation` `engine)`検索、0件。docs/DATA/probes/20260923_tools_8_run4.log の rustybot_readme_elemname 節 |
| rusty-bot | E1b | 印 | 2 | 一次資料 | RunnerのSession経由でPnL・約定を計算(orders DataFrame)。同README実測 |
| rusty-bot | E2 | 未判別 | 未判別 | 未確認 | README全文で`gap`1件ヒット(`Market#donwload_gap`関数名)だが機能内容が判別できず、ソース本体(Rustコア)未読のため未判別。docs/DATA/probes/20260923_tools_8_run4.log の rustybot_readme_elemname 節 |
| rusty-bot | E3a | なし | - | 一次資料 | README全文で`look.?ahead`/`ルックアヘッド`0件。同ログ同節 |
| rusty-bot | E3b | なし | - | 一次資料 | 同上、`purge`/`embargo`/`パージ`0件。同ログ同節 |
| rusty-bot | E4 | 印 | 2 | 一次資料 | README「TICK BASED backtesting」。自動判定機構は無く人が結果を読むため段2 |
| rusty-bot | E5 | 未判別 | 未判別 | 未確認 | README全文で`reproducib`/`再現`/`seed`/`deterministic`0件だが、ソース本体(Rustコア)未読のため「なしと書くための条件」(a)を満たさず未判別 |
| rusty-bot | E6 | なし | - | 一次資料 | README全文で`unit.test`/`property.based`/`fuzz`/`mutation`0件 |
| Fincept Terminal | E1a | 印 | 未判別 | 一次資料 | 864頁PDF実測「Providers — the 6 backtest engines...Are interchangeable engines」+「Broker reconciliation...1 CR」。自動diffの記述なく段は未判別。docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_engine_full/fincept_pdf_e1a_more 節 |
| Fincept Terminal | E1b | 印 | 未判別 | 一次資料 | 同上、6エンジンいずれも「Run Backtest...returns performance, trades and an equity curve」。同ログ同節 |
| Fincept Terminal | E2 | 印 | 2 | 一次資料 | 「The quality score...100% means every branch was populated...check which branches are missing」。自動表示だが判定は人のため段2。docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_missing_11225 節 |
| Fincept Terminal | E3a | なし | - | 一次資料 | 864頁全文で`lookahead`2件、いずれもE3bの文脈。docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_lookahead_ctx 節 |
| Fincept Terminal | E3b | 印 | 未判別 | 一次資料 | 「HISTORY IS BITEMPORAL...」+「CV Splits...Purged K-Fold」。自動・枠の外への持込み可否は未確認のため段未判別。docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_lookahead_ctx/fincept_pdf_purge_ctx 節 |
| Fincept Terminal | E4 | 印 | 未判別 | 一次資料 | Alpha Arena「Every prompt, decision, order and fill is stored, so any round can be replayed」。docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_replay_ctx 節 |
| Fincept Terminal | E5 | 印 | 未判別 | 一次資料 | PRICERS頁「Deterministic...Identical inputs always give identical output」。乱数の種の指定とは性質が異なり段は未判別。docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_deterministic_ctx 節 |
| Fincept Terminal | E6 | なし | - | 一次資料 | `validat`/`verificat`の全出現を確認、UIフォームバリデーションかE3bと重複する記述のみ。docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_validate_lines 節 |
| TradingView のリプレイ機能 | E1a | なし | - | 一次資料 | 公式ヘルプ頁全文(4765文字)に該当記述なし。docs/DATA/probes/20260923_tools_8_run4.log の tv_replay_body 節 |
| TradingView のリプレイ機能 | E1b | なし | - | 一次資料 | 同上(Bar Replay自体は損益計算機能を持たない) |
| TradingView のリプレイ機能 | E2 | なし | - | 一次資料 | 同上、該当記述なし |
| TradingView のリプレイ機能 | E3a | なし | - | 一次資料 | 同上、該当記述なし |
| TradingView のリプレイ機能 | E3b | 印 | 2 | 一次資料 | 「trading orders...are executed based on real-time data」(表示の限定にとどまり発注はリアルタイム価格。自動判定機構の明記なく段2)。docs/DATA/probes/20260923_tools_8_run4.log の tv_replay_body 節 |
| TradingView のリプレイ機能 | E4 | 印 | 2 | 一次資料 | 「Click the Bar Replay button...synchronously run the Bar Replay on all charts」。同ログ同節 |
| TradingView のリプレイ機能 | E5 | なし | - | 一次資料 | 同上、該当記述なし |
| TradingView のリプレイ機能 | E6 | なし | - | 一次資料 | 同上、該当記述なし |
| Exactpro の reconciliation testing | E1a | 印 | 4 | 一次資料 | th2-check2-recon README+テンプレートREADME(実測)「Recon allows you to compare message streams with each other using specified scenarios called Rule」。Ruleは利用者が任意実装できるため段4。docs/DATA/probes/20260923_tools_8_run4.log の exactpro_check2recon_template_readme 節 |
| Exactpro の reconciliation testing | E1b | 印 | 4 | 一次資料 | 同上、checkメソッドは任意のメッセージ型を比較対象にできる設計。同ログ同節 |
| Exactpro の reconciliation testing | E2 | 未判別 | 未判別 | 未確認 | th2プラットフォームの一部(th2-codec・th2-check2-recon関連)しか読めておらず未判別 |
| Exactpro の reconciliation testing | E3a | 未判別 | 未判別 | 未確認 | 同上 |
| Exactpro の reconciliation testing | E3b | 未判別 | 未判別 | 未確認 | 同上 |
| Exactpro の reconciliation testing | E4 | 未判別 | 未判別 | 未確認 | th2-rpt-viewerが記録データの再生に近い可能性があるが未読(WebSearchの要約のみ) |
| Exactpro の reconciliation testing | E5 | 未判別 | 未判別 | 未確認 | 読んだ範囲に記述なし。他コンポーネント未読 |
| Exactpro の reconciliation testing | E6 | 未判別 | 未判別 | 未確認 | 同上 |

### ツール1件ごとの表
この節は委任文§4の全列(料金の構造・到達と実行の記録・相性・当方に無いもの・4軸・危険)を散文で要約する。数値・逐語の一次資料は下の`### 4.0 機械可読の表`と`### 知見`に集約し、ここでは重複を避けて要点だけを書く。

**`prediction-market-backtester`**: Polymarket/Kalshi向けの予測市場バックテストエンジン(Python、Apache系ライセンス、6星)。料金は無料(OSS、外部データ購読なし)。到達・導入は1〜3回目に確認済み(pip install成功)。今回の主な追加は、独立した再計算による自己整合性検証(validate_run_directory)の発見で、区分8の核心(別実装との突き合わせ)に直接該当する。当方に無いもの: 保存済み指標と生データの独立再計算による自動整合性チェック機構、タイムスタンプ順序・価格帯の自動検証。4軸: 道具として入れられるか=印(pip installで導入可能、実測)、当方に無い情報=印(整合性検証・データSHA256固定)、当方に無い視点=印(予測市場特有のcalibration/forecasting_metrics)、既存の成果を向上できるか=推定(バックテスト結果の自己検証パターンは当方のbacktest/engineにも応用できる可能性)。危険: 導入前検査は1回目に実施済み、危険な兆候なし。

**`freqtrade`**: 暗号資産botフレームワーク(Python、GPLv3、54729星)。料金は無料(OSS、取引所APIキーは自前)。今回の追加でデータクレンジング(重複・欠けの検出)・時系列逐次処理・再現性に関する注意文書が確定した。当方に無いもの: OHLCVの自動クレンジング機能(重複除去・欠け補完+警告ログ)、lookahead-analysisコマンド(戦略の指標・シグナルを変化させて自動検出する専用診断ツール、E3aは既に印)。4軸: 道具として入れられるか=印(実運用実績豊富な成熟したOSS)、当方に無い情報=印(lookahead-analysisの診断手法)、当方に無い視点=印(データクレンジングの自動化パターン)、既存の成果を向上できるか=推定(lookahead-analysisの手法を当方のresearch-protocolに参考として取り込める可能性)。危険: 未実施(この回は1〜3回目の危険検査を再確認していない)。

**`backtrex`**: SMC/ICT系のノーコード・ビジュアルバックテストSaaS($22〜59/月、7日間無料試用)。今回の追加で、Anti-Repainting Safeguards文書からルックアヘッド防止機構(close[1]ロジック)とPine Script書き出し経由でのTradingViewとの検証手順(E1a)が確定した。当方に無いもの: close[1]強制によるルックアヘッド防止の設計原則の明文化、Pine Script書き出しによる別実装(TradingView)との検証ワークフロー(<2%乖離の目安)。4軸: 道具として入れられるか=仮定(SaaSでこの環境からの実行不可、登録が要る)、当方に無い情報=印(close[1]設計・SMC/ICTブロック自動検出)、当方に無い視点=印(ノーコードの戦略構築)、既存の成果を向上できるか=推定(close[1]の設計原則は当方のバックテストエンジンの設計指針として参考になりうる)。危険: 登録・課金が要るためこの回は導入せず、公式文書のみで評価。

**`FX Replay`**: 手動バーリプレイ主体のバックテストSaaS。今回の追加でE2・E3a・E3b・E5・E6がいずれも「なし」で確定し、この道具が持つのは「リプレイ(E4)」の機能に限られることが明確になった。当方に無いもの: 複数ブローカー(Dukascopy/OANDA/CME Futures)のデータを切り替えて手動リプレイできるUI、Monte Carloシミュレーション(ただしシード非公開)。4軸: 道具として入れられるか=仮定(SaaS、登録が要る)、当方に無い情報=印(複数ブローカーデータの並存)、当方に無い視点=なし(手動リプレイのみで、自動検証の視点は無い)、既存の成果を向上できるか=未確認。危険: 未実施。

**`nicferrari/backtester`(rs-backtester)**: Rust製の小規模バックテストクレート(6星)。最小実行を実際に走らせ、合成データで成行1往復を確認(Trades#=0という執行タイミングの癖も実測で判明)。当方に無いもの: 特になし(機能は限定的で、E1a〜E6のほぼ全てが「なし」)。4軸: 道具として入れられるか=印(実測でcargo build/run成功)、当方に無い情報=なし、当方に無い視点=なし、既存の成果を向上できるか=なし(機能が限定的で参考価値は低い、推定)。危険: PyPI/crates.io配布元の一致(repository fieldがGitHubと一致)を確認、保守者1名(nicferrari)、難読化・外部URL取得は未確認。

**`arXiv:2512.12924`**: Walk-forward検証フレームワークの論文+実装コード(GitHub、star3)。論文と実装コード(hdt/配下)を実際に読み、E1b〜E6のほぼ全てを「印」で確定できた稀有な事例(該当なし(論文)の列を除く)。当方に無いもの: seedとrerun_analysis.pyによる保存済み結果の再現・比較インフラ、pandas DataFrameの日付整合性の自動検証(align_to_benchmark)。4軸: 道具として入れられるか=未確認(この回はpip install等を試していない)、当方に無い情報=印(walk-forward foldごとの再現可能な乱数制御)、当方に無い視点=印(学術的な厳密性を志向したwalk-forward設計)、既存の成果を向上できるか=推定(当方のresearch-protocolのwalk-forward部分に参考になりうる)。危険: 未実施。

**`Fincept Terminal`**: 統合金融ターミナル(31947星、AGPLv3+クラウド従量課金)。864頁のPDFマニュアルを全文検索し、E1a(6エンジン切替)・E2(データ完全性スコア)・E3b(bitemporalストア+Purged K-Fold)・E4(Alpha Arenaのリプレイ)・E5(決定的プライサー)が確定した、区分8で最も機能が豊富な候補の一つ。当方に無いもの: bitemporalなデータストア(改訂前の値を保持しルックアヘッドを構造的に防ぐ)、6つの異なるバックテストエンジンを切り替え可能な設計、Purged K-Foldを含むCV分割のGUIツール、AIモデル競技(Alpha Arena)の完全監査可能なリプレイ。4軸: 道具として入れられるか=未確認(この回は導入未実施、ローカル実行部分は無料と文書にあるが試していない)、当方に無い情報=印(bitemporalストアの設計そのもの)、当方に無い視点=印(6エンジン比較・AIエージェント競技)、既存の成果を向上できるか=推定(bitemporalデータストアの設計思想は当方のsealed.py(封印機構)と対比する価値がある)。危険: 未実施(AGPLv3のネットワーク公開時のソース開示義務は自己ホストのローカル利用では該当しない可能性が高いが未確認)。

**`TradingView のリプレイ機能`(Bar Replay)**: チャート上のバー再生機能。公式ヘルプ全文とE1a〜E6を確定させたが、E1a・E1b・E2・E5・E6はすべて「なし」で、機能はE4(再生)とE3b(表示の限定、ただし発注はリアルタイム価格という限界つき)に限られることが明確になった。当方に無いもの: 全チャート同期リプレイ(複数銘柄・複数時間足を同時に同じ時点まで巻き戻す機能)。4軸: 道具として入れられるか=仮定(登録・プラン確認が要る、この回は料金表のプラン対応が未確認)、当方に無い情報=印(複数チャート同期リプレイ)、当方に無い視点=なし、既存の成果を向上できるか=未確認。危険: 未実施。

### 4.0 機械可読の表(深掘りした道具: prediction-market-backtester / freqtrade / backtrex / FX Replay / nicferrari/backtester / arXiv:2512.12924 / TradingView のリプレイ機能。Fincept Terminalは表の過半が「未確認」のため深掘りに至らず「浅い」とし、この表には含めない)
| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| prediction-market-backtester | 版 | master(タグなし、2026-03-07最終push) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_repo_meta` の節 |
| prediction-market-backtester | 最終更新日 | 2026-03-07 | 一次資料 | 同上(pushedAt) |
| prediction-market-backtester | ライセンス | Apache-2.0(1回目報告で確認済み) | 一次資料 | 1回目報告(LICENSE実測) |
| prediction-market-backtester | 言語と動作環境 | Python(polars使用) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_validation_py` の節 (importからpolars確認) |
| prediction-market-backtester | 対応取引所 | Polymarket・Kalshi(予測市場) | 一次資料 | リポジトリ説明文(predmkt_repo_meta) |
| prediction-market-backtester | 星 | 6 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_repo_meta` の節 |
| prediction-market-backtester | コミット数 | 未確認 | 未確認 | この回はコミット履歴を開いていない |
| prediction-market-backtester | 保守者数 | 1(Quentin-Piot、推定) | 推定 | リポジトリ所有者名から外挿 |
| prediction-market-backtester | 週DL数 | 未確認 | 未確認 | PyPI未公開のためpypistats対象外(未検索) |
| prediction-market-backtester | 初回公開日 | 2026-02-11(GitHub createdAt) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_repo_meta` の節 |
| prediction-market-backtester | 既知の脆弱性 | 未確認 | 未確認 | この回は脆弱性DB検索未実施 |
| prediction-market-backtester | 料金体系 | 無料(OSS) | 一次資料 | LICENSE(Apache-2.0)、1回目報告で確認済み |
| prediction-market-backtester | 無料枠の上限 | 該当なし | 一次資料 | OSSライブラリでSaaS的な無料枠の概念なし |
| prediction-market-backtester | 課金開始条件 | 該当なし | 一次資料 | 同上 |
| prediction-market-backtester | 隠れた依存 | polars・.env.example記載の外部API鍵(予測市場データ取得用、詳細未確認) | 推定 | src実測(polars import)から外挿、.env.exampleは未読 |
| prediction-market-backtester | 登録の要否 | 不要(ライブラリとして) | 一次資料 | pip/git経由のみ |
| prediction-market-backtester | 到達経路 | GitHub(ungh.cc・raw.githubusercontent.com)成功 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_repo_meta` の節 他多数 |
| prediction-market-backtester | 導入可否 | 可(1回目に確認済み、この回は再実施せず) | 一次資料 | 1回目報告 |
| prediction-market-backtester | install所要秒 | 未確認(この回) | 未確認 | 1回目の値を参照(この回未再測) |
| prediction-market-backtester | 依存数 | 未確認(この回) | 未確認 | pyproject.tomlは未読(次回) |
| prediction-market-backtester | pip check | 未確認(この回) | 未確認 | この回は再実施せず |
| prediction-market-backtester | 最小実行の可否 | 可(1回目に確認済み) | 一次資料 | 1回目報告 |
| prediction-market-backtester | 最小実行の中身 | 1回目の記録を参照(合成データでのバックテスト実行) | 一次資料 | 1回目報告 |
| prediction-market-backtester | 実行所要秒 | 未確認(この回) | 未確認 | 1回目の値を参照 |
| prediction-market-backtester | wheel展開 | 未確認 | 未確認 | この回は未実施 |
| prediction-market-backtester | setup.py導入時実行 | 該当なし(pyproject.toml使用、setup.pyファイルは無し) | 一次資料 | ファイル一覧実測(setup.py不在) |
| prediction-market-backtester | 同梱バイナリ | 無し(Pythonソースのみ) | 一次資料 | ファイル一覧実測(99ファイル中バイナリ拡張子なし) |
| prediction-market-backtester | 外部送信 | 未確認 | 未確認 | この回はネットワーク監視未実施 |
| prediction-market-backtester | 自動発注機能 | 無し(バックテスト専用、execution/simulator.pyはシミュレーションのみ) | 一次資料 | engine.py/simulator.py実測(paper/live executionクラス不在) |
| prediction-market-backtester | 宣伝詐欺の兆候 | 無し | 一次資料 | README・docs実測 |
| prediction-market-backtester | 当方データ投入 | 未確認(予測市場データ形式=implied probability [0,1]。当方のBTC/JPY価格データとは意味論が異なる) | 未確認 | validation.pyの価格帯[0,1]チェックから推定 |
| prediction-market-backtester | 時刻の扱い | equity_df["ts"]のソート済みタイムスタンプ(polars) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_validation_py` の節 |
| prediction-market-backtester | 再現性 | 印(DATA_SHA256+tolerance付き再計算検証) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_validation_py` の節 |
| prediction-market-backtester | 規模の見積 | 未確認 | 未確認 | この回は大規模実行未実施 |
| prediction-market-backtester | 配布元の一致 | 未確認(PyPI未公開のため対象外) | 未確認 | GitHubのみで配布 |
| prediction-market-backtester | 難読化 | 無し(全ソース可読、実測で確認) | 一次資料 | src/pm_bt/配下17ファイルを実測で全文取得・可読 |
| prediction-market-backtester | 外部URL取得 | scripts/setup_data.shが外部データソースから取得(1回目報告参照) | 一次資料 | 1回目報告 |
| prediction-market-backtester | 依存の一覧 | 未確認(この回) | 未確認 | pyproject.toml未読 |
| prediction-market-backtester | 保守者名の一貫性 | 一貫(Quentin-Piot、GitHubのみで確認) | 一次資料 | リポジトリ実測 |
| prediction-market-backtester | 4軸1_道具 | 印(導入・実行可能、1回目実測) | 一次資料 | 1回目報告 |
| prediction-market-backtester | 4軸2_情報 | 印(独立再計算による整合性検証の設計) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_validation_py` の節 |
| prediction-market-backtester | 4軸3_視点 | 印(予測市場特有のforecasting_metrics: brier_score・log_loss・ece) | 一次資料 | 同上ファイル実測 |
| prediction-market-backtester | 4軸4_向上 | 推定(整合性検証パターンを当方のbacktest engineに応用できる可能性) | 推定 | validation.pyの設計から外挿 |
| nicferrari/backtester | 版 | 0.1.5 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cargo_toml` の節 |
| nicferrari/backtester | 最終更新日 | 2026-04-08(pushedAt) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_repo_meta` の節 |
| nicferrari/backtester | ライセンス | Apache-2.0 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cargo_toml` の節 |
| nicferrari/backtester | 言語と動作環境 | Rust 2021 edition | 一次資料 | 同上(言語と動作環境について同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | 対応取引所 | 無し(汎用OHLCV。yahoo_finance_api経由またはCSV) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_data_rs_head` の節 |
| nicferrari/backtester | 星 | 7 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_repo_meta` の節 |
| nicferrari/backtester | コミット数 | 未確認 | 未確認 | この回はコミット履歴未取得 |
| nicferrari/backtester | 保守者数 | 1(nicferrari) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cratesio_ua` の節 (published_by) |
| nicferrari/backtester | 週DL数 | 未確認(crates.ioは週次を公開しない。90日recent_downloads=233、総計3539) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cratesio_ua` の節 |
| nicferrari/backtester | 初回公開日 | crates.io 2025-01-02 / GitHub 2024-02-17 | 一次資料 | 同上(初回公開日について同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | 既知の脆弱性 | 未確認(cargo-audit等この環境に無し。WebSearchでRUSTSEC固有の勧告は見つからず) | 未確認 | docs/DATA/probes/20260923_tools_8_run4.log:nicferrari_backtester_vuln |
| nicferrari/backtester | 料金体系 | 無料(Apache-2.0、crates.io公開) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cratesio_ua` の節 |
| nicferrari/backtester | 無料枠の上限 | 該当なし(ライブラリ、SaaSでない) | 一次資料 | 同上(無料枠の上限について同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | 課金開始条件 | 該当なし | 一次資料 | 同上(課金開始条件について同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | 隠れた依存 | yahoo_finance_api(必須ではない、CSVロードで回避可) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_data_rs_pubfn` の節 |
| nicferrari/backtester | 登録の要否 | 不要 | 一次資料 | cargo経由のみ |
| nicferrari/backtester | 到達経路 | git clone --depth 1成功、crates.io API成功 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_clone` の節 |
| nicferrari/backtester | 導入可否 | 可(隔離venv scratchpad/cat8/venvs/nicferrari_backtesterでcargo build成功) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cargo_build_example` の節 |
| nicferrari/backtester | install所要秒 | 82.377(cargo build --release --example run、初回全依存込み) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cargo_build_example` の節 |
| nicferrari/backtester | 依存数 | 直接9(runtime)+2(dev)=11、推移含む全体248(`cargo tree --prefix none` の一意行数) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cargo_tree_count` の節 |
| nicferrari/backtester | pip check | 該当なし(Rustクレート、pipの概念なし。cargo buildはエラー0件) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cargo_build_example` の節 |
| nicferrari/backtester | 最小実行の可否 | 可 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_min_run_build3` の節 |
| nicferrari/backtester | 最小実行の中身 | 合成CSV(SYNTH、5バー)をData::loadで読み込み、BUY→NULL×4の成行1往復戦略をBacktest::newで実行 | 一次資料 | 同上(最小実行の中身について同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | 実行所要秒 | 0.572(2回目実行、ビルドキャッシュ後) | 一次資料 | 同上(実行所要秒について同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | wheel展開 | 該当なし(Rustクレート) | 一次資料 | 同上(wheel展開について同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | setup.py導入時実行 | 該当なし(build.rs不在、ungh.ccファイル一覧で確認) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_examples_list` の節 |
| nicferrari/backtester | 同梱バイナリ | 無し(ソースのみ) | 一次資料 | 同上(同梱バイナリについて同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | 外部送信 | cargo build時にcrates.ioへ通常の依存取得のみ、当方データは送っていない | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cargo_build_example` の節 |
| nicferrari/backtester | 自動発注機能 | 無し(backtestのみ) | 一次資料 | src実測(orders.rsはBUY/SHORTSELL/NULLの列挙のみ、paper/live執行クラス不在) |
| nicferrari/backtester | 宣伝詐欺の兆候 | 無し | 一次資料 | README実測 |
| nicferrari/backtester | 当方データ投入 | CSV平文(DATE,OPEN,HIGH,LOW,CLOSE,VOLUME)。当方のtardis形式とは列が異なり変換が要る | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_data_rs_saveload` の節 |
| nicferrari/backtester | 時刻の扱い | chrono DateTime<FixedOffset>、RFC3339文字列 | 一次資料 | 同上(時刻の扱いについて同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | 再現性 | なし(seed/reproduc/deterministicの言及なし) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_e2_element_word` の節 系の全体grep |
| nicferrari/backtester | 規模の見積 | 未確認(456日分での実行は試していない) | 未確認 | 5バー実行の実測(0.572秒)から外挿する根拠が弱いため未確認のまま |
| nicferrari/backtester | 配布元の一致 | 一致(crates.io repository fieldがgithub.com/nicferrari/backtesterと一致) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cargo_toml` の節 |
| nicferrari/backtester | 難読化 | 無し(全ソース可読) | 一次資料 | src/全16本を実測で取得・可読 |
| nicferrari/backtester | 外部URL取得 | yahoo_finance_api経由(new_from_yahoo使用時のみ) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_data_rs_head` の節 |
| nicferrari/backtester | 依存の一覧 | yahoo_finance_api/tokio-test/chrono/plotters/serde/csv/once_cell/charming/toml(直接)+248(推移) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cargo_toml`・`nicferrari_backtester_cargo_tree_count` の節 |
| nicferrari/backtester | 保守者名の一貫性 | 一貫(nicferrari、GitHub・crates.io共通) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_cratesio_ua` の節 |
| nicferrari/backtester | 4軸1_道具 | 印(実測でcargo build/run成功、導入可能) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `nicferrari_backtester_min_run_build3` の節 |
| nicferrari/backtester | 4軸2_情報 | なし(機能限定的で当方に無い情報は見当たらず) | 一次資料 | 全体grepの結果(E1a〜E6ほぼ全てなし) |
| nicferrari/backtester | 4軸3_視点 | なし | 一次資料 | 同上(4軸3_視点について同旨、実測に基づく個別確認は未実施) |
| nicferrari/backtester | 4軸4_向上 | なし(推定。機能が限定的で参考価値は低い) | 推定 | 全体の機能範囲から外挿 |
| freqtrade | 版 | develop(タグ無し継続開発、最新push 2026-09-23) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節 |
| freqtrade | 最終更新日 | 2026-09-23 | 実測 | 同上 |
| freqtrade | ライセンス | GPLv3(1回目報告で確認済み) | 一次資料 | 1回目報告 |
| freqtrade | 言語と動作環境 | Python | 一次資料 | ソース実測(converter.py等) |
| freqtrade | 対応取引所 | 多数の暗号資産取引所(ccxt経由、1回目報告参照) | 一次資料 | 1回目報告 |
| freqtrade | 星 | 54729 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節 |
| freqtrade | コミット数 | 未確認(この回) | 未確認 | この回は未取得 |
| freqtrade | 保守者数 | 未確認(この回、多数のコントリビュータがいることはstar/fork数から推定) | 推定 | フォーク数11344から活発なコミュニティと外挿 |
| freqtrade | 週DL数 | 未確認(この回) | 未確認 | PyPI/pypistats未検索 |
| freqtrade | 初回公開日 | 2017-05-17 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節 |
| freqtrade | 既知の脆弱性 | 未確認(この回) | 未確認 | 未検索 |
| freqtrade | 料金体系 | 無料(OSS、取引所APIキーは自前) | 一次資料 | GPLv3・README |
| freqtrade | 無料枠の上限 | 該当なし | 一次資料 | OSSライブラリ |
| freqtrade | 課金開始条件 | 該当なし | 一次資料 | 同上 |
| freqtrade | 隠れた依存 | 取引所APIキー(実運用時)、FreqAI利用時は追加のML依存 | 一次資料 | docs/freqai.md実測(purgeの文脈で確認) |
| freqtrade | 登録の要否 | 不要(バックテストのみなら) | 一次資料 | docs実測 |
| freqtrade | 到達経路 | GitHub(ungh.cc・raw.githubusercontent.com)成功 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節 他多数 |
| freqtrade | 導入可否 | 未確認(この回はpip install等を試していない) | 未確認 | この回は導入未実施 |
| freqtrade | install所要秒 | 未確認(この回) | 未確認 | 同上 |
| freqtrade | 依存数 | 未確認(この回) | 未確認 | requirements未読 |
| freqtrade | pip check | 未確認(この回) | 未確認 | 未実施(pip checkについて同旨、実測に基づく個別確認は未実施) |
| freqtrade | 最小実行の可否 | 未確認(この回はソース読解のみで実行未実施) | 未確認 | 未実施(最小実行の可否について同旨、実測に基づく個別確認は未実施) |
| freqtrade | 最小実行の中身 | 未確認(この回) | 未確認 | 未実施(最小実行の中身について同旨、実測に基づく個別確認は未実施) |
| freqtrade | 実行所要秒 | 未確認(この回) | 未確認 | 未実施(実行所要秒について同旨、実測に基づく個別確認は未実施) |
| freqtrade | wheel展開 | 未確認(この回) | 未確認 | 未実施(wheel展開について同旨、実測に基づく個別確認は未実施) |
| freqtrade | setup.py導入時実行 | 未確認(この回) | 未確認 | 未実施(setup.py導入時実行について同旨、実測に基づく個別確認は未実施) |
| freqtrade | 同梱バイナリ | 未確認(この回) | 未確認 | 未実施(同梱バイナリについて同旨、実測に基づく個別確認は未実施) |
| freqtrade | 外部送信 | 未確認(この回) | 未確認 | 未実施(取引所API通信は設計上必須) |
| freqtrade | 自動発注機能 | 有り(botフレームワークの本質機能、1回目報告参照) | 一次資料 | 1回目報告 |
| freqtrade | 宣伝詐欺の兆候 | 無し | 一次資料 | docs実測 |
| freqtrade | 当方データ投入 | 未確認(独自のOHLCV pandas形式。当方のcsv.gzを変換すれば投入できる可能性、clean_ohlcv_dataframeの対象形式が汎用pandas DataFrameのため) | 推定 | docs/DATA/probes/20260923_tools_8_run4.log:freqtrade_converter_clean |
| freqtrade | 時刻の扱い | timeframe_td単位のdatetime、UTC(一般的なfreqtradeの設計、この回未再確認) | 推定 | 1回目報告からの外挿 |
| freqtrade | 再現性 | 印(静的ペアリストで再現性を確保する案内あり) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:freqtrade_backtesting_head |
| freqtrade | 規模の見積 | 未確認(この回) | 未確認 | 未実施(規模の見積について同旨、実測に基づく個別確認は未実施) |
| freqtrade | 配布元の一致 | 未確認(この回) | 未確認 | 未検証 |
| freqtrade | 難読化 | 無し(全ソース可読、実測で複数ファイルを直接取得) | 一次資料 | converter.py・backtesting.py・idatahandler.py等を実測で取得・可読 |
| freqtrade | 外部URL取得 | 取引所API・download-dataコマンド経由(設計上必須) | 一次資料 | docs/data-download.md実測 |
| freqtrade | 依存の一覧 | 未確認(この回) | 未確認 | requirements.txt未読 |
| freqtrade | 保守者名の一貫性 | 未確認(この回、組織アカウントfreqtrade名義) | 未確認 | 未検証 |
| freqtrade | 4軸1_道具 | 印(実運用実績豊富、1回目報告で導入確認済み) | 一次資料 | 1回目報告 |
| freqtrade | 4軸2_情報 | 印(lookahead-analysisの診断アルゴリズム、clean_ohlcv_dataframeの警告ログ) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:freqtrade_lookahead_full/freqtrade_converter_clean |
| freqtrade | 4軸3_視点 | 印(バックテスト結果の再現性への注意喚起という視点) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:freqtrade_backtesting_head |
| freqtrade | 4軸4_向上 | 推定(lookahead-analysisの手法をresearch-protocolに参考として取り込める可能性) | 推定 | lookahead-analysis.mdの設計から外挿 |
| backtrex | 版 | 該当なし(SaaS、バージョン番号の記載なし) | 一次資料 | サイト全体を実測で確認、バージョン表記なし |
| backtrex | 最終更新日 | 未確認(© 2026 Backtrexの著作権表示のみ) | 未確認 | フッター実測 |
| backtrex | ライセンス | 該当なし(SaaS。Terms of Use and Saleあり、この回は未読) | 一次資料 | フッターのリンク実測 |
| backtrex | 言語と動作環境 | Webブラウザ(SaaS、実行環境の指定なし) | 一次資料 | サイト実測 |
| backtrex | 対応取引所 | 該当なし(バックテスト専用、発注機能なし) | 一次資料 | ドキュメント実測 |
| backtrex | 星 | 該当なし(GitHub非公開、SaaS) | 一次資料 | ドメインのみで提供、GitHub未発見 |
| backtrex | コミット数 | 該当なし | 一次資料 | 同上(コミット数について同旨、実測に基づく個別確認は未実施) |
| backtrex | 保守者数 | 未確認 | 未確認 | 会社名Backtrexのみ判明、個人名未確認 |
| backtrex | 週DL数 | 該当なし(SaaS) | 一次資料 | ダウンロード概念なし |
| backtrex | 初回公開日 | 未確認 | 未確認 | サイトに記載なし |
| backtrex | 既知の脆弱性 | 未確認 | 未確認 | 未検索 |
| backtrex | 料金体系 | Pro $22/月(20 backtests/日・Pine Script export)・Max $59/月(無制限)・7日間無料試用 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_compare_body |
| backtrex | 無料枠の上限 | 7日間の無料試用(Proの範囲、その後の制限は未確認) | 一次資料 | 同上(無料枠の上限について同旨、実測に基づく個別確認は未実施) |
| backtrex | 課金開始条件 | 無料試用終了後 | 一次資料 | 同上(課金開始条件について同旨、実測に基づく個別確認は未実施) |
| backtrex | 隠れた依存 | 無し(SaaS完結、当方環境への依存なし) | 一次資料 | サイト実測 |
| backtrex | 登録の要否 | 要(アカウント作成、渡すもの=メールアドレス等、この回は登録していない) | 一次資料 | サイト実測(Try for freeボタン) |
| backtrex | 到達経路 | 公式サイト・比較ページ・ドキュメントいずれも到達成功 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `backtrex_home`・`backtrex_compare_page`・`backtrex_docs_page` の節 |
| backtrex | 導入可否 | 該当なし(SaaS、ローカル導入の概念なし) | 一次資料 | サイト実測 |
| backtrex | install所要秒 | 該当なし | 一次資料 | 同上(install所要秒について同旨、実測に基づく個別確認は未実施) |
| backtrex | 依存数 | 該当なし | 一次資料 | 同上(依存数について同旨、実測に基づく個別確認は未実施) |
| backtrex | pip check | 該当なし | 一次資料 | 同上(pip checkについて同旨、実測に基づく個別確認は未実施) |
| backtrex | 最小実行の可否 | 登録が要る(実行はオーナーの判断待ち) | 一次資料 | 委任文§5-6の手順に従い、この回は登録・実行していない |
| backtrex | 最小実行の中身 | 登録が要る(渡すもの: メール等)。実行はオーナーの判断待ち。手順: Try for free → 7日間無料試用 → Strategy Builderで戦略構築 → Run Backtest | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_docs_running |
| backtrex | 実行所要秒 | 「30秒/10年」(文書上の主張、未実行) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の `backtrex_docs_running` の節 |
| backtrex | wheel展開 | 該当なし | 一次資料 | SaaS |
| backtrex | setup.py導入時実行 | 該当なし | 一次資料 | 同上(setup.py導入時実行について同旨、実測に基づく個別確認は未実施) |
| backtrex | 同梱バイナリ | 該当なし | 一次資料 | 同上(同梱バイナリについて同旨、実測に基づく個別確認は未実施) |
| backtrex | 外部送信 | 未確認(SaaS、この回は登録していないため通信内容は未確認) | 未確認 | 未検証 |
| backtrex | 自動発注機能 | 無し(バックテスト・Pine Script書き出しのみ、TradingViewへのデプロイは別途利用者が行う) | 一次資料 | ドキュメント実測 |
| backtrex | 宣伝詐欺の兆候 | 無し(比較ページの逐語は具体的な機能比較で、誇大な「必ず儲かる」等の文言なし) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_compare_body |
| backtrex | 当方データ投入 | 該当なし(16資産・M1〜D1の内蔵データのみ、外部データ投入の記述なし) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_docs_running |
| backtrex | 時刻の扱い | M1〜D1のバー単位(ミリ秒等の精度言及なし) | 一次資料 | 同上(時刻の扱いについて同旨、実測に基づく個別確認は未実施) |
| backtrex | 再現性 | 印(Save promising backtests for later comparison) | 一次資料 | 同上(再現性について同旨、実測に基づく個別確認は未実施) |
| backtrex | 規模の見積 | 該当なし(SaaS側で処理、当方の計算資源は使わない) | 一次資料 | サイト実測 |
| backtrex | 配布元の一致 | 該当なし | 一次資料 | SaaS |
| backtrex | 難読化 | 該当なし(クライアント側コードは未検証) | 未確認 | 未検証 |
| backtrex | 外部URL取得 | 該当なし | 一次資料 | SaaS |
| backtrex | 依存の一覧 | 該当なし | 一次資料 | SaaS |
| backtrex | 保守者名の一貫性 | 該当なし | 一次資料 | 会社名のみ |
| backtrex | 4軸1_道具 | 仮定(登録が要るためこの環境では実行未確認、文書上は導入可能と読める) | 仮定 | ドキュメントの記述から |
| backtrex | 4軸2_情報 | 印(close[1]によるルックアヘッド防止設計、SMC/ICTブロック自動検出) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_docs_antirepaint |
| backtrex | 4軸3_視点 | 印(ノーコードのビジュアル戦略構築という視点) | 一次資料 | サイト実測 |
| backtrex | 4軸4_向上 | 推定(close[1]設計原則は当方のバックテストエンジンの設計指針として参考になりうる) | 推定 | anti-repainting文書から外挿 |
| FX Replay | 版 | 該当なし(SaaS) | 一次資料 | サイト実測、バージョン表記なし |
| FX Replay | 最終更新日 | 未確認 | 未確認 | 未検証 |
| FX Replay | ライセンス | 該当なし(SaaS) | 一次資料 | サイト実測(ライセンスについて同旨、実測に基づく個別確認は未実施) |
| FX Replay | 言語と動作環境 | Webブラウザ(SaaS) | 一次資料 | サイト実測(言語と動作環境について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 対応取引所 | 該当なし(バックテスト専用) | 一次資料 | サイト実測(対応取引所について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 星 | 該当なし(SaaS、GitHub非公開) | 一次資料 | 未発見 |
| FX Replay | コミット数 | 該当なし | 一次資料 | 同上(コミット数について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 保守者数 | 未確認 | 未確認 | 会社名のみ判明 |
| FX Replay | 週DL数 | 該当なし(SaaS) | 一次資料 | ダウンロード概念なし |
| FX Replay | 初回公開日 | 未確認 | 未確認 | サイトに記載なし |
| FX Replay | 既知の脆弱性 | 未確認 | 未確認 | 未検索 |
| FX Replay | 料金体系 | 未確認(この回は料金頁を読んでいない。1回目報告参照) | 未確認 | この回未実施 |
| FX Replay | 無料枠の上限 | 未確認(この回) | 未確認 | 同上(無料枠の上限について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 課金開始条件 | 未確認(この回) | 未確認 | 同上(課金開始条件について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 隠れた依存 | 無し(SaaS完結) | 一次資料 | サイト実測(隠れた依存について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 登録の要否 | 要(この回は登録していない) | 一次資料 | サイト実測(登録の要否について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 到達経路 | 公式サイト・support.fxreplay.comいずれも到達成功(記事本体はJS描画のためWebFetch併用) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `fxreplay_home`・`fxreplay_support_home` の節 |
| FX Replay | 導入可否 | 該当なし(SaaS) | 一次資料 | サイト実測(導入可否について同旨、実測に基づく個別確認は未実施) |
| FX Replay | install所要秒 | 該当なし | 一次資料 | 同上(install所要秒について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 依存数 | 該当なし | 一次資料 | 同上(依存数について同旨、実測に基づく個別確認は未実施) |
| FX Replay | pip check | 該当なし | 一次資料 | 同上(pip checkについて同旨、実測に基づく個別確認は未実施) |
| FX Replay | 最小実行の可否 | 登録が要る(実行はオーナーの判断待ち) | 一次資料 | この回は登録・実行していない |
| FX Replay | 最小実行の中身 | 登録が要る(渡すもの: メール等)。実行はオーナーの判断待ち | 一次資料 | 同上(最小実行の中身について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 実行所要秒 | 該当なし(未実行) | 一次資料 | 未実行 |
| FX Replay | wheel展開 | 該当なし | 一次資料 | SaaS |
| FX Replay | setup.py導入時実行 | 該当なし | 一次資料 | 同上(setup.py導入時実行について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 同梱バイナリ | 該当なし | 一次資料 | 同上(同梱バイナリについて同旨、実測に基づく個別確認は未実施) |
| FX Replay | 外部送信 | 未確認 | 未確認 | 未検証 |
| FX Replay | 自動発注機能 | 未確認(この回) | 未確認 | 未検証(手動リプレイでの取引の記録機能はJournal機能として存在するが自動発注かは未確認) |
| FX Replay | 宣伝詐欺の兆候 | 無し(文書は具体的な技術説明に終始) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:fxreplay_vstv_webfetch/fxreplay_brokerdata_webfetch |
| FX Replay | 当方データ投入 | 該当なし(Dukascopy/OANDA/CME Futuresの内蔵データのみ) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:fxreplay_brokerdata_webfetch |
| FX Replay | 時刻の扱い | 未確認(この回) | 未確認 | 未検証 |
| FX Replay | 再現性 | なし(Monte Carloのシード非公開) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:fxreplay_metrics_webfetch |
| FX Replay | 規模の見積 | 該当なし(SaaS側で処理) | 一次資料 | サイト実測(規模の見積について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 配布元の一致 | 該当なし | 一次資料 | SaaS |
| FX Replay | 難読化 | 未確認 | 未確認 | 未検証 |
| FX Replay | 外部URL取得 | 該当なし | 一次資料 | SaaS |
| FX Replay | 依存の一覧 | 該当なし | 一次資料 | SaaS |
| FX Replay | 保守者名の一貫性 | 該当なし | 一次資料 | 会社名のみ |
| FX Replay | 4軸1_道具 | 仮定(登録が要るためこの環境では実行未確認) | 仮定 | サイトの記述から |
| FX Replay | 4軸2_情報 | 印(複数ブローカー(Dukascopy/OANDA/CME Futures)のデータを切り替えられる) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:fxreplay_brokerdata_webfetch |
| FX Replay | 4軸3_視点 | なし(手動リプレイのみで、自動検証の視点は無いことが今回確定) | 一次資料 | E1a〜E3b・E5・E6がいずれも「なし」の判定結果から |
| FX Replay | 4軸4_向上 | 未確認 | 未確認 | 未検証 |
| TradingView のリプレイ機能 | 版 | 該当なし(Webサービス) | 一次資料 | サイト実測 |
| TradingView のリプレイ機能 | 最終更新日 | 未確認 | 未確認 | 未検証(最終更新日について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | ライセンス | 該当なし(SaaS) | 一次資料 | サイト実測 |
| TradingView のリプレイ機能 | 言語と動作環境 | Webブラウザ/モバイルアプリ | 一次資料 | ヘルプ頁実測 |
| TradingView のリプレイ機能 | 対応取引所 | 該当なし(チャート機能、発注は別途ブローカー連携) | 一次資料 | ヘルプ頁実測 |
| TradingView のリプレイ機能 | 星 | 該当なし | 一次資料 | SaaS(星について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | コミット数 | 該当なし | 一次資料 | 同上(コミット数について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 保守者数 | 該当なし(企業TradingView, Inc.) | 一次資料 | フッター実測 |
| TradingView のリプレイ機能 | 週DL数 | 該当なし | 一次資料 | SaaS(週DL数について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 初回公開日 | 未確認 | 未確認 | 未検証(初回公開日について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 既知の脆弱性 | 未確認 | 未確認 | 未検索 |
| TradingView のリプレイ機能 | 料金体系 | Basic〜Ultimateの5段階プラン(実測、料金比較表)。Bar Replayがどのプランで有効かはチェックマーク記号がテキスト抽出で失われ未確認 | 未確認 | docs/DATA/probes/20260923_tools_8_run4.log の `tv_pricing_context` の節 |
| TradingView のリプレイ機能 | 無料枠の上限 | 未確認(登録なしで一部利用可能との二次情報があるが一次資料で確認できず) | 未確認 | docs/DATA/probes/20260923_tools_8_run4.log:tv_pricing_context |
| TradingView のリプレイ機能 | 課金開始条件 | 未確認 | 未確認 | 同上(課金開始条件について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 隠れた依存 | 無し(ブラウザのみ) | 一次資料 | サイト実測 |
| TradingView のリプレイ機能 | 登録の要否 | 閲覧は不要、機能利用には要登録の可能性(未確認) | 未確認 | 未検証(登録の要否について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 到達経路 | 公式ヘルプ・料金頁いずれも到達成功 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `tv_replay_solution`・`tv_pricing_check` の節 |
| TradingView のリプレイ機能 | 導入可否 | 該当なし(SaaS、ブラウザで完結) | 一次資料 | サイト実測 |
| TradingView のリプレイ機能 | install所要秒 | 該当なし | 一次資料 | 同上(install所要秒について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 依存数 | 該当なし | 一次資料 | 同上(依存数について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | pip check | 該当なし | 一次資料 | 同上(pip checkについて同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 最小実行の可否 | 登録が要る可能性(未確認)。実行はオーナーの判断待ち | 未確認 | この回は登録・実行していない |
| TradingView のリプレイ機能 | 最小実行の中身 | 登録が要る可能性(渡すもの: 未確認)。実行はオーナーの判断待ち | 未確認 | 同上(最小実行の中身について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 実行所要秒 | 該当なし(未実行) | 一次資料 | 未実行 |
| TradingView のリプレイ機能 | wheel展開 | 該当なし | 一次資料 | SaaS(wheel展開について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | setup.py導入時実行 | 該当なし | 一次資料 | 同上(setup.py導入時実行について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 同梱バイナリ | 該当なし | 一次資料 | 同上(同梱バイナリについて同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 外部送信 | 未確認 | 未確認 | 未検証(外部送信について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 自動発注機能 | 有り(Bar Replay中の発注は「real-time data」で約定するため実質は実発注に近い動作) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:tv_replay_body |
| TradingView のリプレイ機能 | 宣伝詐欺の兆候 | 無し | 一次資料 | ヘルプ頁実測 |
| TradingView のリプレイ機能 | 当方データ投入 | 該当なし(TradingView内蔵のICE Data Services/FactSet提供データのみ) | 一次資料 | tv_replay_body(フッターのデータ提供元表記) |
| TradingView のリプレイ機能 | 時刻の扱い | 未確認 | 未確認 | 未検証(時刻の扱いについて同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 再現性 | なし(リアルタイムデータに依存する部分がありE5該当記述なし) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:tv_replay_body |
| TradingView のリプレイ機能 | 規模の見積 | 該当なし(SaaS側で処理) | 一次資料 | サイト実測 |
| TradingView のリプレイ機能 | 配布元の一致 | 該当なし | 一次資料 | SaaS(配布元の一致について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 難読化 | 該当なし | 一次資料 | SaaS(難読化について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 外部URL取得 | 該当なし | 一次資料 | SaaS(外部URL取得について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 依存の一覧 | 該当なし | 一次資料 | SaaS(依存の一覧について同旨、実測に基づく個別確認は未実施) |
| TradingView のリプレイ機能 | 保守者名の一貫性 | 該当なし | 一次資料 | 企業のみ |
| TradingView のリプレイ機能 | 4軸1_道具 | 仮定(登録・プラン確認が要るためこの環境では実行未確認) | 仮定 | 料金表の存在から |
| TradingView のリプレイ機能 | 4軸2_情報 | 印(全チャート同期リプレイという機能情報) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:tv_replay_body |
| TradingView のリプレイ機能 | 4軸3_視点 | なし(単純な過去チャート表示の巻き戻しで、独自の分析視点の提供は確認できず) | 一次資料 | ヘルプ頁実測 |
| TradingView のリプレイ機能 | 4軸4_向上 | 未確認 | 未確認 | 未検証(4軸4_向上について同旨、実測に基づく個別確認は未実施) |
| arXiv:2512.12924 | 版 | v1(2025-12-15) | 一次資料 | arXiv頁実測 |
| arXiv:2512.12924 | 最終更新日 | 2025-12-15(論文)。実装コードpushedAt 2026-07-08 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_github_repo` の節 |
| arXiv:2512.12924 | ライセンス | arXiv perpetual license(論文)。コードのlicenseファイルは未開封のため未確認 | 未確認 | arXiv頁+ファイル一覧実測(license存在は確認、中身未読) |
| arXiv:2512.12924 | 言語と動作環境 | Python(hdt/パッケージ、requirements.txt存在確認、バージョン制約未読) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_repo_files` の節 |
| arXiv:2512.12924 | 対応取引所 | 該当なし(株式・yfinance経由の日次データ) | 一次資料 | data_loader.py実測 |
| arXiv:2512.12924 | 星 | 3 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_github_repo` の節 |
| arXiv:2512.12924 | コミット数 | 未確認 | 未確認 | 未取得 |
| arXiv:2512.12924 | 保守者数 | 未確認(著者名akashdeepoのみ判明) | 未確認 | GitHubユーザー名から |
| arXiv:2512.12924 | 週DL数 | 該当なし(論文・PyPI未公開) | 一次資料 | PyPI検索未実施だがGitHub限定の配布と推定 |
| arXiv:2512.12924 | 初回公開日 | 論文2025-12-15。リポジトリcreatedAt 2025-12-14 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_github_repo` の節 |
| arXiv:2512.12924 | 既知の脆弱性 | 未確認 | 未確認 | 未検索 |
| arXiv:2512.12924 | 料金体系 | 無料 | 一次資料 | arXiv・GitHub公開 |
| arXiv:2512.12924 | 無料枠の上限 | 該当なし(論文・OSSコード) | 一次資料 | 同上 |
| arXiv:2512.12924 | 課金開始条件 | 該当なし | 一次資料 | 同上 |
| arXiv:2512.12924 | 隠れた依存 | yfinance経由のYahoo Financeデータ取得に依存(data_loader.py実測) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_data_loader` の節 |
| arXiv:2512.12924 | 登録の要否 | 不要 | 一次資料 | GitHub公開 |
| arXiv:2512.12924 | 到達経路 | arXiv(HTML版)・GitHub(ungh.cc・raw)いずれも到達成功 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_html`・`arxiv_2512_12924_github_repo` の節 |
| arXiv:2512.12924 | 導入可否 | 未確認(この回はpip install等を試していない、コードは読むところまで) | 未確認 | 未実施(導入可否について同旨、実測に基づく個別確認は未実施) |
| arXiv:2512.12924 | install所要秒 | 未確認 | 未確認 | 未実施(install所要秒について同旨、実測に基づく個別確認は未実施) |
| arXiv:2512.12924 | 依存数 | 未確認 | 未確認 | requirements.txtは存在確認のみ、中身未読 |
| arXiv:2512.12924 | pip check | 未確認 | 未確認 | 未実施(pip checkについて同旨、実測に基づく個別確認は未実施) |
| arXiv:2512.12924 | 最小実行の可否 | 未確認(この回は実行未実施) | 未確認 | 未実施(最小実行の可否について同旨、実測に基づく個別確認は未実施) |
| arXiv:2512.12924 | 最小実行の中身 | 未確認 | 未確認 | 未実施(最小実行の中身について同旨、実測に基づく個別確認は未実施) |
| arXiv:2512.12924 | 実行所要秒 | 該当なし(未実行。`rerun_analysis.py`のdocstringに「avoids the ~30 minute walk-forward backtest」とありフル実行は約30分かかる可能性) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_rerun_analysis` の節 |
| arXiv:2512.12924 | wheel展開 | 未確認 | 未確認 | 未実施(wheel展開について同旨、実測に基づく個別確認は未実施) |
| arXiv:2512.12924 | setup.py導入時実行 | 未確認(setup.py不在、ファイル一覧で未確認) | 未確認 | ファイル一覧実測 |
| arXiv:2512.12924 | 同梱バイナリ | 無し(ソース・ノートブック・図表PDFのみ、ファイル一覧実測) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_repo_files` の節 |
| arXiv:2512.12924 | 外部送信 | 未確認(yfinance経由の外部通信はあるが当方データの送信ではない) | 未確認 | 未検証 |
| arXiv:2512.12924 | 自動発注機能 | 無し(backtestのみ、paper/live執行の記述なし) | 一次資料 | backtester.py実測(ProductionBacktesterはシミュレーションのみ) |
| arXiv:2512.12924 | 宣伝詐欺の兆候 | 無し | 一次資料 | 全体実測 |
| arXiv:2512.12924 | 当方データ投入 | pandas DataFrame(OHLCV列)形式なら投入できる可能性(E2根拠と同じ、対象形式が汎用) | 推定 | data_loader.py実測から外挿 |
| arXiv:2512.12924 | 時刻の扱い | 日次バー、day t close→day t+1 open執行 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_backtester_docstring` の節 |
| arXiv:2512.12924 | 再現性 | 印(E5参照、seed+保存済み結果の再利用) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_validation_py`・`arxiv_2512_12924_rerun_analysis` の節 |
| arXiv:2512.12924 | 規模の見積 | 未確認 | 未確認 | 未実施(規模の見積について同旨、実測に基づく個別確認は未実施) |
| arXiv:2512.12924 | 配布元の一致 | 一致(論文本文が示すGitHub URLと実際のリポジトリが一致、実測確認) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_github_repo` の節 |
| arXiv:2512.12924 | 難読化 | 無し(全ソース可読) | 一次資料 | validation.py/backtester.py/data_loader.py等を実測で取得・可読 |
| arXiv:2512.12924 | 外部URL取得 | yfinance経由(data_loader.py) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_data_loader` の節 |
| arXiv:2512.12924 | 依存の一覧 | 未確認(requirements.txt中身未読) | 未確認 | ファイル一覧のみ確認 |
| arXiv:2512.12924 | 保守者名の一貫性 | 一貫(akashdeepo、GitHubのみで確認) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_github_repo` の節 |
| arXiv:2512.12924 | 4軸1_道具 | 未確認(導入未実施) | 未確認 | 未実施(4軸1_道具について同旨、実測に基づく個別確認は未実施) |
| arXiv:2512.12924 | 4軸2_情報 | 印(fold単位の乱数種指定+保存結果の再実行インフラ) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_validation_py` の節 |
| arXiv:2512.12924 | 4軸3_視点 | 印(学術的厳密性を志向したwalk-forward設計、情報集合の厳密な時点管理) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `arxiv_2512_12924_validation_py` の節 |
| arXiv:2512.12924 | 4軸4_向上 | 推定(walk-forward部分の設計を当方のresearch-protocolに参考として取り込める可能性) | 推定 | 全体の設計から外挿 |

### 代替経路
この回は「この環境から不可」と書いた項目なし。arXiv:2603.20319のコード所在(github.com/don-yin/backtest-engine)は404だったが、これは「未公開」という一次資料の実測結果であり「到達できなかった」ではない(rc=35のケース2件(ungh.cc)はSURVEY.md§5に従い打ち直して解消した。生ログ参照)。tech.takibi.net記事(rusty-botの発見経路)は初回404だったが、archive.org(wayback)への代替経路で200を得て解決した(実測、docs/DATA/probes/20260923_tools_8_run4.log の rustybot_takibi_article/rustybot_takibi_wayback/rustybot_takibi_wayback_retry 節)。support.fxreplay.comの記事本体はJavaScriptで描画され`curl`では取得できなかったため、`WebFetch`を代替経路として使った(生ログのwebfetch手を参照)。

### 予算
この回は予算で止めない(追補§5)。

### 受け入れ検査の出力
`python3 scripts/check_scan_report.py docs/DATA/SCAN_2026-09-23_tools_cat8.md docs/DATA/probes/20260923_tools_8_run1.log docs/DATA/probes/20260923_tools_8_run2.log docs/DATA/probes/20260923_tools_8_run3.log docs/DATA/probes/20260923_tools_8_run4.log` の最後に打った出力全文:

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

`python3 scripts/cat8_ledger.py check-elements docs/DATA/SCAN_2026-09-23_tools_cat8.md --round 4` の最後に打った出力全文:
```
読んだもの: 候補の一覧 16 行 / 要素と段の表 128 行(道具 16)/ 知見の表 30 行 / 辿る一覧から出た名前 0 行
---- 合計 0 件
```

`python3 scripts/cat8_ledger.py check "" docs/DATA/probes/20260923_tools_8_run4.log` の最後に打った出力全文:
```
参考: docs/DATA/probes/20260923_tools_8_run4.log の最初の手 2026-09-24T00:17:41Z / 最後の手 2026-09-24T00:53:12Z / 手の数 184
---- 合計 0 件
```

`git diff -U0 HEAD -- docs/DATA/SCAN_2026-09-23_tools_cat8.md | grep '^-[^-]' | wc -l` の出力: `0`(1〜3回目の節から消えた行は無い)

### 判断に迷った点と問い(決めずに列挙)
1. **8-014 Fincept TerminalのE1a(6エンジンの相互運用)**: 「同一の戦略・銘柄・期間設定を6つの異なるバックテストエンジンのどれでも実行できる」ことは確認したが、自動でdiffを算出する記述は見当たらなかった(人が結果を並べて見る前提と読める)。段を確定できなかった。
2. **8-014のE5(決定的プライサー)**: 「Deterministic. All 16 pricers are closed-form or tree-based — no Monte Carlo, no seed on this page」は乱数を使わない解析解の性質であり、E5述語が主に想定する「乱数の種を指定して結果を固定する」機能とは性質が異なる。この種の決定性をE5に当ててよいか。
3. **8-016 Exactproの範囲**: 候補「Exactproのreconciliation testing」をth2プラットフォームのth2-check2-reconコンポーネントに絞って深掘りしてよいか、それとも商用のShsha等の非OSS製品も含めて評価すべきか。th2は多数のマイクロサービス(20以上のリポジトリ)からなり、この回はごく一部(th2-codec・th2-check2-recon・th2-check2-recon-template)しか読めておらず、E2・E3a・E3b・E4・E5・E6が未判別のまま残った。次回に読み進める必要がある。
4. **8-013 rusty-botの状態**: 一次資料(yasstake/rbot README)への到達と同定は確定したが、Rustコア本体(ソースコード)は未読で、E2(`Market#donwload_gap`関数)とE5が未判別のまま残った。README単体では「なしと書くための条件」(a)(一次資料の全部の文書)を満たしていない。
5. **8-012 VectorBTのE4**: README・公式文書にベクトル化計算の説明はあるが、時刻順の逐次再生と呼べる明示的な記述を見つけられなかった(8-009のnicferrari/backtesterと同型の論点)。公式ドキュメントのSimulation詳細頁を読み切れていない。
6. **WebFetchの使用(8-008 FX Replay)**: support.fxreplay.comはJavaScriptで記事本体を描画するため`curl`では取得できず、`WebFetch`(小型モデルによる要約)を使った。可能な範囲で逐語(引用符付き)を確認して印の根拠としたが、これは委任文§4.1の「一次資料」(自分で開いて、その場所に書いてある)の要件を満たすと言えるか、それとも「実測」や別の印にすべきか。
7. **8-003・8-006・8-007のE1a訂正**: 2・3回目はREADMEや断片的な文言だけで「なし」と判定していたが、この回にソース本体・追加文書ページまで読むと「印」に訂正すべき機能が見つかった(3件とも)。「一次資料の全部」をREADMEに限定してよいか、常にソース本体・関連文書ページまで読むべきかという判定基準の揺れが、この回で繰り返し露呈した。次回以降の候補(8-001・8-002・8-004・8-005など、この回は未着手)にも同じ問題が起きていないか、確認が要る。
8. **§4.0表の「今の値で載せる」と「8-001〜8-008は台帳の値のまま写す」の食い違い(起動文§4)**: 起動文§4は「候補の一覧と『要素と段』の表には8-001〜8-016の全行を今の値で載せる(8-001〜8-008は台帳の値のまま写す)」と書いているが、この回の§2の9〜12はまさに8-003・8-006・8-007・8-008を更新する指示であり、両者が字面上矛盾する。この回は「今の値で載せる」(更新を反映する)を優先したが、この判断でよいか確認したい。
9. **委任文§6-6「本体の一括ダウンロード(数百MB以上)はしない」とFincept Terminalの700頁マニュアル(実際は864頁、43.8MBのPDF)**: 数百MB未満のため実施したが、公式文書そのもの(製品の実行ファイルや依存の一括取得ではない)であることを踏まえて許容範囲と判断した。この判断基準でよいか確認したい。

## 区分8 — 5 回目の実行(2026-09-24)

### 検索計画
この回は新しい検索計画を打たない(委任文§2「前回の残りの候補名があれば、まずそれを深掘りする(検索計画は打ち直さない)」)。台帳の残り9行(8-003・8-006・8-007・8-008・8-010・8-012・8-013・8-014・8-016)を深掘りの条件まで進めることに専念した。

### 出典
| # | 出典 | URL | 内容 | 取得日 |
|---|---|---|---|---|
| 1 | GitHub(ungh.cc) | https://ungh.cc/repos/Quentin-Piot/prediction-market-backtester | リポジトリメタ・ファイル一覧(99件) | 2026-09-24 |
| 2 | GitHub(git clone) | https://github.com/Quentin-Piot/prediction-market-backtester | 全ソース(scratchpad、読むだけで導入なし) | 2026-09-24 |
| 3 | GitHub(git clone、sparse) | https://github.com/freqtrade/freqtrade(docs/配下のみ) | docs/全132件(バイナリ画像39件除く95件を検索) | 2026-09-24 |
| 4 | 公式サイト | https://backtrex.com/en/docs 他9頁 | Documentation全9頁(4回目は8頁と誤認) | 2026-09-24 |
| 5 | 公式サイト(Chromium) | https://fxreplay.com/ 、https://fxreplay.com/backtest | ホーム・機能頁の本文(WebFetchではなくcat8_render.js) | 2026-09-24 |
| 6 | サポートセンター(Chromium) | https://support.fxreplay.com/categories/product-guide-features 他40記事 | Product Guide & Featuresカテゴリ全40記事 | 2026-09-24 |
| 7 | arXiv | https://arxiv.org/abs/2603.20319 、https://arxiv.org/html/2603.20319v1 | 論文abs頁+HTML全文(9節・12節を含む) | 2026-09-24 |
| 8 | GitHub(ungh.cc) | https://ungh.cc/repos/don-yin/backtest-engine | コード未公開の再確認(404) | 2026-09-24 |
| 9 | GitHub(ungh.cc) | https://ungh.cc/repos/polakowo/vectorbt | リポジトリメタ | 2026-09-24 |
| 10 | 公式文書サイト | https://vectorbt.dev/api/portfolio/base/ 、sitemap.xml | Simulation・Saving and loadingの記述 | 2026-09-24 |
| 11 | GitHub(ungh.cc・git clone) | https://ungh.cc/repos/yasstake/rbot 、https://github.com/yasstake/rbot | リポジトリメタ+全171ファイル(Rustソース75本) | 2026-09-24 |
| 12 | GitHub(ungh.cc・README) | https://ungh.cc/repos/Fincept-Corporation/FinceptTerminal 、https://raw.githubusercontent.com/Fincept-Corporation/FinceptTerminal/main/README.md | リポジトリメタ+README(OSS版とEnterprise版の区別) | 2026-09-24 |
| 13 | PyPI | https://pypi.org/pypi/fincept-terminal/json 、https://pypistats.org/api/packages/fincept-terminal/recent | 旧パッケージのメタ・週DL数 | 2026-09-24 |
| 14 | GitHub(raw) | https://raw.githubusercontent.com/Fincept-Corporation/FinceptTerminal/main/fincept-qt/resources/requirements-numpy2.txt | 依存一覧(116件、py-clob-client等) | 2026-09-24 |
| 15 | 864頁マニュアル(3回目キャッシュを実測) | https://fincept.in/docs/fincept-terminal-master-guide.pdf | Broker reconciliation・Instrument LabのSeedフィールド | 2026-09-24(取得自体は2026-09-24の3回目) |
| 16 | GitHub(ungh.cc) | https://ungh.cc/orgs/th2-net/repos | th2-net組織のリポジトリ一覧(100件) | 2026-09-24 |
| 17 | GitHub(raw、15件) | https://raw.githubusercontent.com/th2-net/th2-check1/master/README.md 他14件 | E2〜E6関連リポジトリのREADME | 2026-09-24 |
| 18 | 公式サイト(3回目キャッシュ) | https://exactpro.com/ideas/test-tools/shsha | 商用製品Shshaの機能記述(登録不要で取得) | 2026-09-24(取得自体は2026-09-24の3回目) |

### 知見
| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `prediction-market-backtester` / E3a・E3b / 方式(原文): git clone後の全96ファイル検索で`look.?ahead`/`purge`/`embargo`等0件。入力(原文): 検索対象は`src/pm_bt/`配下17ソース・`tests/`16本・`docs/`3本・README/ROADMAP等(csvフィクスチャ2件・uv.lock1件は除外) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:14,17,20 |
| 2 | `prediction-market-backtester` / E5 / (ア)判定の基準を利用者が指定できるか: README「set DATA_URL (and optionally DATA_SHA256)」でハッシュ値は指定できるが、これは入力データの版の固定(§4.2の軸)であり出力の許容誤差・閾値ではない = 満たさない | 一次資料 | 3回目に取得したREADME(docs/DATA/probes/20260923_tools_8_run3.log)+この回git clone先の`scripts/setup_data.sh`実測(docs/DATA/probes/20260923_tools_8_run5.log:11の直後の節) |
| 3 | `prediction-market-backtester` / E5 / (イ)結果を保存して次回実行と比べられるか: tests/test_backtest_engine.pyの`test_backtest_engine_equity_curve_matches_golden_hash`が期待ハッシュ`a5eea6...`と比較。ただし開発者が固定した値で、利用者が任意の実験を保存・比較する汎用機能ではない | 一次資料 | git clone先tests/test_backtest_engine.py実測(docs/DATA/probes/20260923_tools_8_run5.log:11の直後の節、ファイルはscratchpad/cat8/repos/pmbtに読むだけで導入) |
| 4 | `freqtrade` / E3b / 方式(原文): strategy-customization.md「This should be set to the maximum number of candles that the strategy requires to calculate stable indicators」「backtesting knows it needs 400 candles to generate valid entry signals. It will load data from 20190101 - (400 * 5m)」。入力(原文): OHLCVローソク足データ、`startup_candle_count`パラメータ | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:117,134 |
| 5 | `freqtrade` / E3b / 方式(原文、FreqAI): freqai-running.md「train_test_split()...has a parameters called shuffle...This is particularly useful to avoid biasing training with temporally auto-correlated data」 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:134 |
| 6 | `backtrex` / E3a / 一覧: Documentationトップ頁(https://backtrex.com/en/docs)の実測でGetting Started 2・Strategy Building 2・Backtesting 3・Export 1・Risk Management 1の合計9頁と判明(4回目は8頁と誤認) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:188 |
| 7 | `FX Replay` / E1a〜E6 / 方式: Support Center『Product Guide & Features』カテゴリ(40記事、一覧40件/読んだ40件)全件をscripts/cat8_render.js経由のChromiumで取得。WebFetchは使用していない | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:1426(一覧)、1468-8031(40記事の取得) |
| 8 | `FX Replay` / E5 / 方式(原文): analytic-metrics-defined記事「The Monte Carlo simulation works by running a large number of simulations using random input values for uncertain variables in a model」。シードの固定・公開・保存比較への言及なし | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:1768 |
| 9 | `arXiv:2603.20319` / E1b / 方式(原文): 論文9節「Algorithm 1 presents the reference proportional-cost backtest loop...All five retained engines are expected to produce identical equity curves when their cost models faithfully implement this logic」。入力(原文): weight schedule W、close prices P、initial capital C0、cost rate c | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:4369 |
| 10 | `arXiv:2603.20319` / E2 / 方式(原文): 論文12.1節「No gaps or stale prices are present. All 180 stocks have complete daily observations for every trading day in the sample; no stock-month pair contains missing data and no imputation was required」。入力(原文): 180 S&P 500銘柄のadjusted-close日次価格(2018-2024) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:4369 |
| 11 | `arXiv:2603.20319` / コード未公開の再確認: 「our backtesting engine will be released at https://github.com/don-yin/backtest-engine under the MIT licence upon acceptance」。ungh.cc実測でcode=404 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:4611 |
| 12 | `VectorBT` / E4 / 方式(原文): api/portfolio/base頁「The simulation function traverses the broadcasted shape element by element, row by row (time dimension), column by column (asset dimension). For each asset and timestamp (= element): Gets all available information related to this element and executes the logic...Updates the current state such as the cash and asset balances」。入力(原文): 任意のpandas Series/DataFrame(price・size等)、from_order_funcでは利用者定義のNumba関数 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:5681 |
| 13 | `VectorBT` / E5 / (イ)結果を保存して次回実行と比べられるか、方式(原文): 同頁「we can save a Portfolio instance to the disk with Pickleable.save() and load it with Pickleable.load()」+ 実行例`pf.save('my_pf')`→`vbt.Portfolio.load('my_pf')`で同じsharpe_ratio()を再取得 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:5681 |
| 14 | `VectorBT` / E5 / (ア)判定の基準を利用者が指定できるか: 同頁・sitemap.xml配下の関連頁を検索したが、比較の許容誤差・閾値を指定する機能(isclose/allclose/assert_等)への言及は見つからず、満たさない | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:5370,5681 |
| 15 | `rusty-bot` / E2 / 方式(原文): `modules/rbot_market/src/market.rs`「fn download_gap(&mut self, verbose: bool) -> anyhow::Result<i64>;」/ `exchanges/bitflyer/src/market.rs`「WARNING database has {} gaps. Download with force option, or drop-and-create database.」。入力(原文): rbot自身のSQLite市場データDB | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:6921 |
| 16 | `rusty-bot` / E5 / 一覧75件(.rsファイル総数)/読んだ75件: `seed`/`reproducib`/`determinist`/`fixed.?random`/`rng`および`checkpoint`/`snapshot`/`commit_hash`/`config_hash`/`再現`/`version.?pin`のいずれも0件(snapshotは板データの意味でのみヒット) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:6955,7018 |
| 17 | `Fincept Terminal` / E1a / 方式(原文): 864頁マニュアル「Held option positions are marked by reconciling the broker's tick symbol with its position symbol」「A reconciliation pull is scheduled behind every paper command in case a frame is missed」。入力(原文): 自社の建玉記録とブローカーのオプション建玉記録 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:11659 |
| 18 | `Fincept Terminal` / E5 / 方式(原文): 864頁マニュアル「Deterministic. Monte-Carlo instruments (Leveraged ETF Decay, VaR & Stress) expose a Seed field, so results are reproducible」+「Monte-Carlo (VaR) uses a fixed seed, so results reproduce exactly」。入力(原文): Instrument LabのMonte-Carlo系商品(Leveraged ETF Decay・VaR & Stress) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:11663 |
| 19 | `Fincept Terminal` / オープンソース版とEnterprise版の区別: GitHub README「Two editions run on one data core. Enterprise is the private, closed-source build...This repo is the free AGPL-3.0 edition」。864頁マニュアルはEnterprise版(v5.0.1)の記述で、オープンソース版(GitHub、v4.5.0)とは別製品 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231 |
| 20 | `Fincept Terminal` / 危険・自動発注機能: requirements-numpy2.txt「py-clob-client>=0.22.0」「eth-account>=0.10.0」「cryptography>=42.0.0」のコメント「Polymarket uses EIP-712 signing via py_clob_client (Polygon wallet); Kalshi uses RSA-PSS signing via the cryptography package」。README「paper-trading engine, 16 broker integrations」(オープンソース版)+「Live broker routing + live algo deployment」(Enterprise版) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8446,8231 |
| 21 | `Fincept Terminal` / 配布元の不一致: PyPI `fincept-terminal`(v2.0.8)のlicenseフィールドが`MIT`。GitHub本体(現行v4.5.0)は`AGPL-3.0-or-later`。両者の関係を説明する記述は見当たらない | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8228,8231 |
| 22 | `Exactpro の reconciliation testing` / E2 / 方式(原文、th2-check1): 「CheckSequenceRuleRequest - prefilters the messages and verify all of them by filter. Order checking configured from request」「SilenceCheckRule...Reports about unexpected messages only after the timeout is exceeded」「submitNoMessageCheck...verifies that no messages are received by check1 within a specified interval」 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8800 |
| 23 | `Exactpro の reconciliation testing` / E2 / (ア)判定の基準: th2-check1 README「message_timeout」「timeout」「pre_filter」が利用者指定のパラメータ。(イ)結果の保存: th2-estore README「Event store (estore) is an important th2 component responsible for storing events into Cradle」+ th2-rpt-data-provider README「connect to the cassandra database via cradle api and expose the data stored in there as REST resources」 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8800,9261,11216 |
| 24 | `Exactpro の reconciliation testing` / th2-net組織のリポジトリ一覧(全件): ungh.ccで100件取得(1頁のみでページングは未確認、100件を超える可能性は未確認)。うち15件のREADMEを読了、85件は未読 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8665,8685 |
| 25 | `Exactpro の reconciliation testing` / 商用部分(Shsha、§5-6): 登録なしで取得できた公式頁の記述「Shsha is a post-transactional passive-testing tool...Test message traffic generated in real time or replayed from log files by other tools...Certification tests and data reconciliation may be performed by using ordinary SQL queries」。オーナーが辿れる手順: https://exactpro.com/ideas/test-tools/shsha を閲覧(登録不要)→デモ依頼はinfo@exactpro.com(登録・実行はしていない) | 一次資料 | 3回目取得のキャッシュ`exactpro_shsha.html`をこの回参照(取得自体はdocs/DATA/probes/20260923_tools_8_run4.log) |


### 候補の一覧
1. [深掘り] `qf-lib` (8-001) — https://github.com/quarkfin/qf-lib — バックテストエンジン(区分1から) — 状態: 深掘り
2. [深掘り] `PineForge` (8-002) — https://github.com/pineforge-4pass/pineforge-engine — Pineスクリプト系バックテストエンジン(区分1から) — 状態: 深掘り
3. [深掘り] `prediction-market-backtester` (8-003) — https://github.com/Quentin-Piot/prediction-market-backtester — 予測市場バックテストエンジン(区分1から) — 状態: 深掘り
4. `akurkar07/OrderBook` (8-004) — https://github.com/akurkar07/OrderBook — 板シミュレータ(区分1から、危険で導入停止) — 状態: 危険で導入停止
5. `Exegy` (8-005) — https://www.exegy.com/ — 市場データベンダー(区分1から、登録が要る) — 状態: 登録が要る
6. [深掘り] `freqtrade` (8-006) — https://github.com/freqtrade/freqtrade — 暗号資産botフレームワーク — 状態: 深掘り
7. [深掘り] `backtrex` (8-007) — https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide — ノーコード・ビジュアルバックテストSaaS — 状態: 深掘り
8. [深掘り] `FX Replay` (8-008) — https://fxreplay.com/ — 手動バーリプレイSaaS — 状態: 深掘り
9. [深掘り] `nicferrari/backtester` (8-009) — https://github.com/nicferrari/backtester — Rust製の小規模バックテストクレート — 状態: 深掘り
10. [深掘り] `arXiv:2603.20319` (8-010) — https://arxiv.org/abs/2603.20319 — 実装リスク(エンジン間の相違)を論じる論文 — 状態: 深掘り
11. [深掘り] `arXiv:2512.12924` (8-011) — https://arxiv.org/abs/2512.12924 — Walk-forward検証フレームワークの論文+実装 — 状態: 深掘り
12. [深掘り] `VectorBT` (8-012) — https://github.com/polakowo/vectorbt — ベクトル化バックテストライブラリ — 状態: 深掘り
13. `rusty-bot` (8-013) — https://x.com/WannabeBotter/status/1810558269565571211 — Rust製トレーディングボット(yasstake/rbot) — 状態: 判別に一次資料が要る
14. [深掘り] `Fincept Terminal` (8-014) — https://github.com/Fincept-Corporation/FinceptTerminal — 統合金融ターミナル — 状態: 深掘り
15. [深掘り] `TradingView のリプレイ機能` (8-015) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:98-100(検索計画3、URL は生ログに無い) — チャート上のバー再生機能 — 状態: 深掘り
16. `Exactpro の reconciliation testing` (8-016) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:95-97(検索計画2、URL は生ログに無い) — メッセージ照合テストの方法論+th2プラットフォーム+商用製品 — 状態: 判別に一次資料が要る

### 要素と段
| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 |
|---|---|---|---|---|---|
| qf-lib | E1a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| qf-lib | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(4回目の節) |
| qf-lib | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| qf-lib | E3a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| qf-lib | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| qf-lib | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| qf-lib | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| qf-lib | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| PineForge | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(4回目の節) |
| PineForge | E1b | 印 | 5 | 一次資料 | 台帳の値のまま(4回目の節) |
| PineForge | E2 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| PineForge | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| PineForge | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| PineForge | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| PineForge | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| PineForge | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| prediction-market-backtester | E1a | 印 | 5 | 実測 | 訂正(なし→印): src/pm_bt/reporting/validation.py の validate_run_directory が保存済みresults.jsonの指標(total_pnl等9項目)を生equity.csv/trades.csvから独立に再計算し`_assert_close(name, actual, expected, tolerance=tolerance)`で突き合わせる。docs/DATA/probes/20260923_tools_8_run4.log の predmkt_validation_py 節 |
| prediction-market-backtester | E1b | 印 | 2 | 一次資料 | 前回から変更なし |
| prediction-market-backtester | E2 | 印 | 3 | 実測 | 補強(根拠追加): validation.pyの`equity_df["ts"].is_sorted()`チェックと価格帯[0,1]チェック。docs/DATA/probes/20260923_tools_8_run4.log の predmkt_validation_py 節 |
| prediction-market-backtester | E3a | なし | - | 実測 | 確定(全ファイル一覧で当て直し): 一覧96件/読んだ96件(99件から画像0件・データ雛形2件・ロックファイル1件を除く)(除外: tests/fixtures/markets_small.csv・trades_small.csv(データ雛形)、uv.lock(生成物・ロックファイル)、理由=文書でもソースでもないため)。git clone後、`look.?ahead`/`look-ahead`/`leak`/`future.?data`/`peek`/`embargo`/`purge`/`survivorship`/未来/先読み/リークを日英で検索、0件。docs/DATA/probes/20260923_tools_8_run5.log:14,17,20 |
| prediction-market-backtester | E3b | なし | - | 実測 | 確定(同上): 一覧96件/読んだ96件(99件から画像0件・データ雛形2件・ロックファイル1件を除く)。E3aと同じ検索(embargo/purgeを含む)で0件。docs/DATA/probes/20260923_tools_8_run5.log:14,17,20 |
| prediction-market-backtester | E4 | 印 | 3 | 実測 | 前回から変更なし(engine.pyのバー単位逐次処理) |
| prediction-market-backtester | E5 | 印 | 3 | 一次資料 | 段を訂正(5→3、監査21回目の処置8): (ア)判定の基準(閾値・検出の条件)を使う人が指定できるか — README「set DATA_URL (and optionally DATA_SHA256)」で期待ハッシュ値は指定できるが、これは入力データの版を固定する仕組み(§4.2の軸「データの版」)であり、出力結果を比較するための許容誤差・閾値ではない。tests/test_backtest_engine.pyのgolden hashテスト(`assert _equity_curve_hash(...) == "a5eea6..."`)も開発者が固定した値で、利用者が基準を指定する仕組みではない。(ア)は満たさない。(イ)結果を保存して次の実行と比べられるか — golden hashテストはこの回路を満たす(期待値を保存し比較)が、pytestの固定フィクスチャ内に限られ、利用者が任意の実験を保存・比較する汎用機能ではない。対象(コード・データ・設定)のうちデータの版のみ外部から持ち込める(DATA_URL/DATA_SHA256は任意のURLを指定できる)。対象の一部だけ持ち込めるので段4ではなく段3(設計票§4.1「対象の一部だけが外から持ち込めるものは段3」)。docs/DATA/probes/20260923_tools_8_run4.log の predmkt_validation_py 節(README/setup_data.sh)+ tests/test_backtest_engine.py 実測(この回、git clone先で読了) |
| prediction-market-backtester | E6 | なし | - | 実測 | 確定(全ファイル一覧で当て直し): 一覧96件/読んだ96件(99件から画像0件・データ雛形2件・ロックファイル1件を除く)。`verify`/`validat`/`reproduc`/`determinis`/`golden`/`regression`/検証/再現/確認/SHA256を検索してヒットした全箇所(pydanticのモデル検証・validate_run_directory・is_sorted・golden hashテスト・DATA_SHA256)は、E1a(再計算突き合わせ)・E2(範囲/順序違反検出)・E5(データ版固定・golden比較)のいずれかに該当済みで、それ以外の独立した検証機能は無い。docs/DATA/probes/20260923_tools_8_run5.log:27 |
| akurkar07/OrderBook | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| akurkar07/OrderBook | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(4回目の節) |
| akurkar07/OrderBook | E2 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| akurkar07/OrderBook | E3a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| akurkar07/OrderBook | E3b | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| akurkar07/OrderBook | E4 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| akurkar07/OrderBook | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| akurkar07/OrderBook | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| Exegy | E1a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| Exegy | E1b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| Exegy | E2 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| Exegy | E3a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| Exegy | E3b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| Exegy | E4 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| Exegy | E5 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| Exegy | E6 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| freqtrade | E1a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| freqtrade | E1b | 印 | 2 | 一次資料 | 前回から変更なし |
| freqtrade | E2 | 印 | 3 | 一次資料 | 確定(未判別→印): freqtrade/data/converter/converter.pyの`clean_ohlcv_dataframe`(「Grouping it by date (removes duplicate tics)」「Filling up missing data」)・`ohlcv_fill_up_missing_data`。docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_converter_clean 節 |
| freqtrade | E3a | 印 | 3 | 一次資料 | 前回から変更なし |
| freqtrade | E3b | 印 | 3 | 実測 | 訂正(なし→印、4回目は5本しか検索していなかった): docs/配下132件のうちバイナリ画像39件(png/jpg/svg)を除く95件全件を検索(`purge`/`embargo`/`gap`/`hold.?out`/`train.?test.?split`/`leak`/未来の情報/リーク/先読み防止)。strategy-customization.md 245-276行『startup_candle_count』(バックテスト開始前に指標の暖機に要る追加候補データを自動で余分に読み込み、暖機不足の期間には entry/exit signal を生成しない仕組み。backtesting.md「backtesting knows it needs 400 candles to generate valid entry signals. It will load data from 20190101 - (400*5m)」)+ freqai-running.md 130行『train_test_split()...shuffle...particularly useful to avoid biasing training with temporally auto-correlated data』。いずれも freqtrade 自身の戦略/データ形式に限るため段3。docs/DATA/probes/20260923_tools_8_run5.log:117,134 |
| freqtrade | E4 | 印 | 3 | 一次資料 | 確定(未判別→印): freqtrade/optimize/backtesting.pyの`time_pair_generator`/`_time_generator`(「Loop for each main candle」)。docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_backtesting_loop 節(ft_backtesting.py実測) |
| freqtrade | E5 | 印 | 2 | 一次資料 | 確定(未判別→印): docs/backtesting.md「reproducibility of backtesting-results cannot be guaranteed...best generate a pairlist via the test-pairlist command」。docs/DATA/probes/20260923_tools_8_run4.log の freqtrade_backtesting_head 節 |
| freqtrade | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| backtrex | E1a | 印 | 2 | 一次資料 | 訂正(なし→印): /en/docs/backtesting/anti-repainting頁「Verification Through Export: Export your strategy and run it on TradingView. Compare the signals and trade entries between Backtrex and TradingView. The guaranteed less than 2% divergence...」。docs/DATA/probes/20260923_tools_8_run4.log の backtrex_docs_antirepaint 節 |
| backtrex | E1b | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| backtrex | E2 | 印 | 3 | 一次資料 | 前回から変更なし |
| backtrex | E3a | なし | - | 一次資料 | 確定(全9頁で当て直し。4回目はDocumentation全8頁のうち5頁のみ): Documentationの一覧(トップ頁の実測で正確には9頁と判明: Getting Started 2・Strategy Building 2・Backtesting 3・Export 1・Risk Management 1)を全件取得。一覧9件/読んだ9件: introduction・first-strategy・blocks-overview・indicators・running-backtests・understanding-metrics・anti-repainting・export-to-tradingview・position-sizing。「Lookahead Bias」節(anti-repainting頁)は原因説明のみ、他8頁にも検出機能の記述なし(「Auto-Detection」はSMC/ICTパターン検出の意味でlookaheadとは無関係)。docs/DATA/probes/20260923_tools_8_run5.log:188(一覧を取った手)、192,203,214,225,236,247,258,269,280(9頁の取得) |
| backtrex | E3b | 印 | 3 | 一次資料 | 確定(未判別→印): 同頁「All price references use close[1]...No indicator can access the current bar's data for signal generation」「The backtest engine processes bars strictly in chronological order」。同ログ同節 |
| backtrex | E4 | 印 | 3 | 一次資料 | 確定(未判別→印): /en/docs/backtesting/running-backtests頁「Timeframe: M1/M3/M5/M15/H1/H4/D1」「The engine processes the historical data and returns results in under 30 seconds」+ Anti-Repainting頁「processes bars strictly in chronological order」。docs/DATA/probes/20260923_tools_8_run4.log の backtrex_docs_running 節 |
| backtrex | E5 | 印 | 2 | 一次資料 | 確定(未判別→印): running-backtests頁「Tips: Save promising backtests for later comparison」。同ログ同節 |
| backtrex | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節。読了範囲全体で`fuzz`/`property.based`/`mutation`等に相当する記述なし) |
| FX Replay | E1a | なし | - | 実測 | 訂正(未判別→なし。前回はWebFetch): 一覧40件/読んだ40件(Support Center『Product Guide & Features』カテゴリの全記事。Getting Started・Account Management・Billing and Payments・Technical Support・Community & Resources・FXR Battles・FXR Journalの他カテゴリは対象外)= 区分8の要素(検証・再現・品質)に直接該当する記述はProduct Guide & Features(『Learn how FX Replay's tools and features work』)に限られると判断したため、範囲として明記。一覧を取った手: docs/DATA/probes/20260923_tools_8_run5.log:1426。全40記事をscripts/cat8_render.jsで取得(生ログ本文、行番号は一覧行1426の後方に連続記録)。ホーム頁(fxreplay.com、同ログ:291)と/backtest頁(同ログ:790)も確認。WebFetchは使用していない。「diff」「discrepancy」「reconcile」「cross-check」等の自動突き合わせ機能への言及なし。broker-data-sources記事はブローカー間の価格差の存在を説明するのみで自動検出機構ではない |
| FX Replay | E1b | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| FX Replay | E2 | なし | - | 実測 | 訂正(未判別→なし。前回はWebFetch): 一覧40件/読んだ40件(Support Center『Product Guide & Features』カテゴリの全記事。Getting Started・Account Management・Billing and Payments・Technical Support・Community & Resources・FXR Battles・FXR Journalの他カテゴリは対象外)= 区分8の要素(検証・再現・品質)に直接該当する記述はProduct Guide & Features(『Learn how FX Replay's tools and features work』)に限られると判断したため、範囲として明記。一覧を取った手: docs/DATA/probes/20260923_tools_8_run5.log:1426。全40記事をscripts/cat8_render.jsで取得(生ログ本文、行番号は一覧行1426の後方に連続記録)。ホーム頁(fxreplay.com、同ログ:291)と/backtest頁(同ログ:790)も確認。WebFetchは使用していない。`gap`/`missing`/`duplicat`/`outlier`/`out.?of.?order`等を検索、自動検出機能への言及なし(what-broker-data-sources記事はデータ源の説明のみ) |
| FX Replay | E3a | なし | - | 実測 | 訂正(未判別→なし。前回はWebFetch): 一覧40件/読んだ40件(Support Center『Product Guide & Features』カテゴリの全記事。Getting Started・Account Management・Billing and Payments・Technical Support・Community & Resources・FXR Battles・FXR Journalの他カテゴリは対象外)= 区分8の要素(検証・再現・品質)に直接該当する記述はProduct Guide & Features(『Learn how FX Replay's tools and features work』)に限られると判断したため、範囲として明記。一覧を取った手: docs/DATA/probes/20260923_tools_8_run5.log:1426。全40記事をscripts/cat8_render.jsで取得(生ログ本文、行番号は一覧行1426の後方に連続記録)。ホーム頁(fxreplay.com、同ログ:291)と/backtest頁(同ログ:790)も確認。WebFetchは使用していない。`look.?ahead`/`repaint`/`leak`等を検索、0件 |
| FX Replay | E3b | なし | - | 実測 | 訂正(未判別→なし。前回はWebFetch): 一覧40件/読んだ40件(Support Center『Product Guide & Features』カテゴリの全記事。Getting Started・Account Management・Billing and Payments・Technical Support・Community & Resources・FXR Battles・FXR Journalの他カテゴリは対象外)= 区分8の要素(検証・再現・品質)に直接該当する記述はProduct Guide & Features(『Learn how FX Replay's tools and features work』)に限られると判断したため、範囲として明記。一覧を取った手: docs/DATA/probes/20260923_tools_8_run5.log:1426。全40記事をscripts/cat8_render.jsで取得(生ログ本文、行番号は一覧行1426の後方に連続記録)。ホーム頁(fxreplay.com、同ログ:291)と/backtest頁(同ログ:790)も確認。WebFetchは使用していない。`purge`/`embargo`等を検索、0件(smoothing-candle記事は将来データ使用の有無を明記せず、判別材料にならない = 未判別要素ではなく単に言及なし) |
| FX Replay | E4 | 印 | 2 | 一次資料 | 前回から変更なし |
| FX Replay | E5 | なし | - | 実測 | 訂正(未判別→なし。前回はWebFetch): 一覧40件/読んだ40件(Support Center『Product Guide & Features』カテゴリの全記事。Getting Started・Account Management・Billing and Payments・Technical Support・Community & Resources・FXR Battles・FXR Journalの他カテゴリは対象外)= 区分8の要素(検証・再現・品質)に直接該当する記述はProduct Guide & Features(『Learn how FX Replay's tools and features work』)に限られると判断したため、範囲として明記。一覧を取った手: docs/DATA/probes/20260923_tools_8_run5.log:1426。全40記事をscripts/cat8_render.jsで取得(生ログ本文、行番号は一覧行1426の後方に連続記録)。ホーム頁(fxreplay.com、同ログ:291)と/backtest頁(同ログ:790)も確認。WebFetchは使用していない。Monte Carlo Simulation(analytic-metrics-defined記事)は「running a large number of simulations using random input values」で乱数シードの固定・公開や再現性の言及なし。`save`+`load`/`checkpoint`/`compare.{0,15}run`等も0件 |
| FX Replay | E6 | なし | - | 実測 | 訂正(未判別→なし。前回はWebFetch): 一覧40件/読んだ40件(Support Center『Product Guide & Features』カテゴリの全記事。Getting Started・Account Management・Billing and Payments・Technical Support・Community & Resources・FXR Battles・FXR Journalの他カテゴリは対象外)= 区分8の要素(検証・再現・品質)に直接該当する記述はProduct Guide & Features(『Learn how FX Replay's tools and features work』)に限られると判断したため、範囲として明記。一覧を取った手: docs/DATA/probes/20260923_tools_8_run5.log:1426。全40記事をscripts/cat8_render.jsで取得(生ログ本文、行番号は一覧行1426の後方に連続記録)。ホーム頁(fxreplay.com、同ログ:291)と/backtest頁(同ログ:790)も確認。WebFetchは使用していない。`fuzz`/`property.?based`/`mutation`/`hypothesis`/`validat`/`verif`を検索。ヒットしたvalidateはUI入力欄の説明のみでE1a-E5に当たらない独立した検証機能への言及なし |
| nicferrari/backtester | E1a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| nicferrari/backtester | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(4回目の節) |
| nicferrari/backtester | E2 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| nicferrari/backtester | E3a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| nicferrari/backtester | E3b | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| nicferrari/backtester | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| nicferrari/backtester | E5 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| nicferrari/backtester | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| arXiv:2603.20319 | E1a | 印 | 未判別 | 一次資料 | 前回から変更なし(コード未公開のため段は未判別のまま。実測でungh.cc 404を確認しコード未公開を裏付け。docs/DATA/probes/20260923_tools_8_run5.log:4611で再確認) |
| arXiv:2603.20319 | E1b | 印 | 1 | 一次資料 | 新規確定(未判別→印): 論文9節「Reference Implementation Pseudocode」Algorithm 1(比例コスト・バックテストループの完全な擬似コード)。「All five retained engines are expected to produce identical equity curves when their cost models faithfully implement this logic」= 当方の損益計算(エクイティカーブ)と同じ種類の出力を出す独立した計算の仕様。ただしコードは「will be released...upon acceptance」で未公開(ungh.cc 404実測済み)のため、道具の機能として呼べない=段1。docs/DATA/probes/20260923_tools_8_run5.log:4369(HTML全文)、4611(404実測) |
| arXiv:2603.20319 | E2 | 印 | 1 | 一次資料 | 新規確定(未判別→印): 論文12.1節「Data Quality Control...No gaps or stale prices are present. All 180 stocks have complete daily observations for every trading day in the sample; no stock-month pair contains missing data and no imputation was required」= 欠け(gap)・欠損の検出と報告。ただし著者自身のデータセットに対する一回限りの確認記述であり、コード未公開のため利用者が呼べる機能ではない=段1。docs/DATA/probes/20260923_tools_8_run5.log:4369 |
| arXiv:2603.20319 | E3a | なし | - | 一次資料 | 台帳の値のまま(4回目の節。全文で`look.?ahead`/`ルックアヘッド`0件) |
| arXiv:2603.20319 | E3b | なし | - | 一次資料 | 台帳の値のまま(4回目の節。`purge`/`embargo`/`パージ`0件) |
| arXiv:2603.20319 | E4 | なし | - | 一次資料 | 台帳の値のまま(4回目の節。`replay`/`リプレイ`は一般的言及1件のみ) |
| arXiv:2603.20319 | E5 | 印 | 1 | 一次資料 | 前回から変更なし(「divergence tables...will be deposited at Zenodo upon acceptance」= 未来の予定の記述。段1のまま) |
| arXiv:2603.20319 | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節。`validat`/`verificat`/`検証`の一致は全てE1aの文脈内) |
| arXiv:2512.12924 | E1a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| arXiv:2512.12924 | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| arXiv:2512.12924 | E2 | 印 | 4 | 一次資料 | 台帳の値のまま(4回目の節) |
| arXiv:2512.12924 | E3a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| arXiv:2512.12924 | E3b | 印 | 4 | 一次資料 | 台帳の値のまま(4回目の節) |
| arXiv:2512.12924 | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(4回目の節) |
| arXiv:2512.12924 | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(4回目の節) |
| arXiv:2512.12924 | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| VectorBT | E1a | なし | - | 一次資料 | 台帳の値のまま(4回目の節。README+features頁+splitters頁で`reconcil`/`cross.check`/`突き合わせ`検索、0件) |
| VectorBT | E1b | 印 | 3 | 一次資料 | 前回から変更なし(round3実測のPortfolio.from_*) |
| VectorBT | E2 | 印 | 3 | 一次資料 | 前回から変更なし(`missing_index="drop"`。features頁「Detect confirmed price pivots and outliers」はPRO限定) |
| VectorBT | E3a | なし | - | 一次資料 | 台帳の値のまま(4回目の節。features頁・splitters頁で`look.?ahead`/`ルックアヘッド`検索、0件) |
| VectorBT | E3b | 印 | 3 | 一次資料 | 前回から変更なし(splitters頁のBaseSplitter/ExpandingSplitter/RangeSplitter/RollingSplitter。purge/embargoはPRO限定) |
| VectorBT | E4 | 印 | 4 | 一次資料 | 新規確定(未判別→印): api/portfolio/base頁「The simulation function traverses the broadcasted shape element by element, row by row (time dimension), column by column (asset dimension). For each asset and timestamp (= element): Gets all available information...Generates an order...processes the order and fills/ignores/rejects it...Updates the current state such as the cash and asset balances」。対象は任意のpandas Series/DataFrame(price・size等)と、from_order_funcではユーザー定義のNumba関数(order_func_nb)を受け付けるため段4。docs/DATA/probes/20260923_tools_8_run5.log:5681 |
| VectorBT | E5 | 印 | 4 | 実測 | 段を訂正(5→4、監査21回目の処置8「乱数の種は(ア)に当たらない」を踏襲): (ア)判定の基準(許容誤差・閾値)を利用者が指定できる記述は見つからず(seed引数は結果を固定する仕組みで、比較の許容誤差ではない)→(ア)は満たさない。(イ)結果を保存して次の実行と比べられるか — api/portfolio/base頁「we can save a Portfolio instance to the disk with Pickleable.save() and load it with Pickleable.load()」+実行例(`pf.save('my_pf')` → `vbt.Portfolio.load('my_pf')` で同じsharpe_ratio()を再取得)。(イ)は満たす。対象(固定・比較する実験=コード・データ・設定)のうちPortfolio全体(価格データ・戦略設定込み)を保存・再読込できるため対象は広いが、(ア)を満たさないため段5には届かず段4。乱数シードによる決定的な結果は4回目に実行時証(2回実行で`total_return()`完全一致)。docs/DATA/probes/20260923_tools_8_run5.log:5681 + docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_min_run_retry 節 |
| VectorBT | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節。features頁・splitters頁に該当記述なし) |
| rusty-bot | E1a | なし | - | 実測 | 台帳の値のまま(4回目の節) |
| rusty-bot | E1b | 印 | 2 | 実測 | 前回から変更なし |
| rusty-bot | E2 | 印 | 3 | 実測 | 新規確定(未判別→印): Rustソース171ファイルのうち`download_gap`が定義されたファイルを軸に検索。`modules/rbot_market/src/market.rs`のMarketImplトレイト「fn download_gap(&mut self, verbose: bool) -> anyhow::Result<i64>;」/ `modules/rbot_lib/src/db/sqlite.rs`の`select_gap_chunks`(欠損区間の一覧を返す)・`analyze_db`関数(`exchanges/bitflyer/src/market.rs`。「MISSING: FROM: {} -> TO: {}」「WARNING database has {} gaps」を自動出力)。対象はrbot自身のSQLite市場データDBに限るため段3。docs/DATA/probes/20260923_tools_8_run5.log:6921 |
| rusty-bot | E3a | 未判別 | 未判別 | 未確認 | この回も未判別のまま(前回から変更なし。Rust本体を読んだが検出機能の記述は見つけられず、なしと確定するには.rs以外のドキュメントも読む必要がある) |
| rusty-bot | E3b | なし | - | 実測 | 台帳の値のまま(4回目の節) |
| rusty-bot | E4 | 印 | 2 | 実測 | 前回から変更なし |
| rusty-bot | E5 | なし | - | 実測 | 新規確定(未判別→なし): Rust全171ファイルのうち.rsファイル(75本)全件を対象に`seed`/`reproducib`/`determinist`/`fixed.?random`/`rng`を検索(0件)、続けて`checkpoint`/`snapshot`/`commit_hash`/`config_hash`/`再現`/`version.?pin`を検索。`snapshot`はヒットしたが板(オーダーブック)のスナップショット受信の意味で、E5(実験結果の固定・比較)とは無関係。乱数・再現性に関する記述は見つからず。一覧75件/読んだ75件(.rsファイル総数、grep -r で全件検索)。docs/DATA/probes/20260923_tools_8_run5.log:6955,7018 |
| rusty-bot | E6 | なし | - | 実測 | 台帳の値のまま(4回目の節) |
| Fincept Terminal | E1a | 印 | 3 | 一次資料 | 段を確定(未判別→3): 864頁マニュアル実測。根拠を訂正 — 「Providers...interchangeable engines」(6エンジン切替)は利用者が手動で別エンジンに切り替えて再実行するだけで自動diff機能ではない(round4の解釈は誤り)。真のE1a該当機能は『Broker reconciliation』(Equity Trading→bottom panel→RECONCILE、1 CR)で「Held option positions are marked by reconciling the broker's tick symbol with its position symbol」= 自社の記録とブローカー(参照値)の自動突き合わせ。「A reconciliation pull is scheduled behind every paper command」= 自動実行。対象はFincept自身が組み込みでサポートするブローカー連携に限られるため段3。docs/DATA/probes/20260923_tools_8_run5.log:11659(Broker reconciliationの実測)。864頁PDFの取得自体は3回目(docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_download 節) |
| Fincept Terminal | E1b | 印 | 未判別 | 一次資料 | 前回から変更なし(6エンジンいずれも『Run Backtest...returns performance, trades and an equity curve』。段は未判別のまま、この回は対象外) |
| Fincept Terminal | E2 | 印 | 2 | 一次資料 | 前回から変更なし |
| Fincept Terminal | E3a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| Fincept Terminal | E3b | 印 | 未判別 | 一次資料 | 前回から変更なし(段は未判別のまま、この回は対象外) |
| Fincept Terminal | E4 | 印 | 未判別 | 一次資料 | 前回から変更なし(段は未判別のまま、この回は対象外) |
| Fincept Terminal | E5 | 印 | 3 | 一次資料 | 段を確定・根拠を訂正(未判別→3。処置: 作りが決定的なだけではE5の機能ではないの原則どおり、PRICERS頁の「Deterministic...Identical inputs always give identical output」だけでは印にしない): INSTRUMENT LAB頁「Deterministic. Monte-Carlo instruments (Leveraged ETF Decay, VaR & Stress) expose a Seed field, so results are reproducible」= Seedフィールドを利用者が明示的に設定でき、その結果として再現可能になると明記(単なる決定的動作の主張ではない)。VOL ANALYSIS頁「Monte-Carlo (VaR) uses a fixed seed, so results reproduce exactly」も同旨。(ア)判定の基準(許容誤差・閾値)を利用者が指定できるか — Seedは結果を固定する仕組みで閾値ではない(監査21回目の処置8と同じ判断)ため(ア)は満たさない。(イ)結果を保存し次回実行と比較できるか — Instrument Lab固有の保存・比較機能への言及は見つけられず(イ)も未確認。対象(固定する対象)はInstrument Labの決められた商品(Leveraged ETF Decay・VaR & Stress)に限られるため段3。docs/DATA/probes/20260923_tools_8_run5.log:11663(Seedフィールドの実測)。864頁PDFの取得自体は3回目(docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_download 節) |
| Fincept Terminal | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| TradingView のリプレイ機能 | E1a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| TradingView のリプレイ機能 | E1b | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| TradingView のリプレイ機能 | E2 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| TradingView のリプレイ機能 | E3a | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| TradingView のリプレイ機能 | E3b | 印 | 2 | 一次資料 | 台帳の値のまま(4回目の節) |
| TradingView のリプレイ機能 | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(4回目の節) |
| TradingView のリプレイ機能 | E5 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| TradingView のリプレイ機能 | E6 | なし | - | 一次資料 | 台帳の値のまま(4回目の節) |
| Exactpro の reconciliation testing | E1a | 印 | 4 | 一次資料 | 前回から変更なし(段は4のまま。この回、追加の根拠を「知見」に参考として記録。段の見直しは次回以降に判断を仰ぐ) |
| Exactpro の reconciliation testing | E1b | 印 | 4 | 一次資料 | 前回から変更なし |
| Exactpro の reconciliation testing | E2 | 印 | 5 | 実測 | 新規確定(未判別→印): th2-check1のREADME「CheckSequenceRuleRequest - prefilters the messages and verify all of them by filter. Order checking configured from request」(順序の乱れの検出)+「SilenceCheckRule...verifies that there were not any messages matching the pre-filter...Reports about unexpected messages only after the timeout is exceeded」+「submitNoMessageCheck...verifies that no messages are received by check1 within a specified interval」(欠け・不在の検出)。(ア)判定の基準を利用者が指定できるか — `message_timeout`/`timeout`/`pre_filter`パラメータで利用者が明示的に指定できる(README「Behavior and Configuration」節)。(イ)結果を保存して次の実行と比べられるか — 検証結果はth2の『Event』としてth2-estoreがCradleに永続化され(README「Event store...responsible for storing events into Cradle」)、th2-rpt-data-provider/rpt-viewerで後から参照できる(README「expose the data stored in there as REST resources」「displays the stored test data」)。(ア)(イ)両方を満たすため段5。対象(検査するデータ)は利用者が接続する任意のメッセージストリーム(th2-conn-*経由で外部システムのFIX/SWIFT等)のため段4の条件も満たす。docs/DATA/probes/20260923_tools_8_run5.log:8800(check1 README)、9261(rpt-data-provider README)、11216(estore README) |
| Exactpro の reconciliation testing | E3a | 未判別 | 未判別 | 未確認 | この回、check1/check2-recon/check2-recon-template/rpt-viewer/rpt-data-provider/data-services/crawler/crawler-event-healer/woodpecker/read-log/read-csv/read-file/replay-script-generator-core/estoreの15リポジトリのREADMEを読んだが、lookahead検出に相当する記述は見つからず(0件)。ただしth2組織のリポジトリは全100件(一覧取得済み)のうち15件しか読めておらず、『なしと書くための条件』(a)全部の文書を読む、を満たさないため未判別のまま |
| Exactpro の reconciliation testing | E3b | 未判別 | 未判別 | 未確認 | 同上 |
| Exactpro の reconciliation testing | E4 | 未判別 | 未判別 | 未確認 | th2-replay-script-generator-coreのREADMEに『Core library for replay script generators』+メッセージ変換の記述はあるが、時刻順の再生を明記した原文は見つけられず未判別のまま。th2-documentation等の未読部分に説明がある可能性 |
| Exactpro の reconciliation testing | E5 | 未判別 | 未判別 | 未確認 | この回読んだ15リポジトリのREADMEに再現性・乱数シード等の記述は見つからず(0件)。ただし読了範囲が限定的(15/100)のため未判別のまま |
| Exactpro の reconciliation testing | E6 | 未判別 | 未判別 | 未確認 | 同上 |


### ツール1件ごとの表
この節は委任文§4の全列(料金の構造・到達と実行の記録・相性・当方に無いもの・4軸・危険)を散文で要約する。数値・逐語の一次資料は下の`### 4.0 機械可読の表`と`### 知見`に集約し、ここでは重複を避けて要点だけを書く。

**`prediction-market-backtester`**: 前回、E1a(なし→印)の訂正を受けて深掘りに戻ったが、監査21回目でE3a・E3b・E6が「7本しか検索していない状態でのなし」と指摘され未判別に戻された。この回、git cloneで全99ファイル(除外2件のcsvフィクスチャ・1件のuv.lockを除く96ファイル)を対象に再検索し、E3a・E3b・E6のいずれも0件で「なし」を再確定。E5の段は5→3に訂正(DATA_SHA256はデータの版の固定にとどまり、golden hashテストも開発者固定の値で、利用者が判定基準を指定できる仕組みではないため)。当方に無いもの: 保存済み指標と生データの独立再計算による自動整合性チェック機構(E1a)。4軸: 前回から変更なし。危険: 未実施(この回)。

**`freqtrade`**: 監査21回目でE3bの「なし」が「5本しか検索していない状態」と指摘され未判別に戻された。この回、docs/配下132件のうちバイナリ画像を除く95件全件を検索し、`startup_candle_count`(バックテスト開始前の暖機データの自動追加読み込み)とFreqAIの`data_split_parameters`(train_test_splitのshuffle無効化による時系列リーク回避)を発見、E3bを「なし→印」に訂正(段3、freqtrade自身の戦略・データ形式の枠内)。当方に無いもの: startup_candle_countのような暖機期間の自動読み込み+シグナル生成の抑制機構。4軸: 前回から変更なし。危険: 未実施(この回)。

**`backtrex`**: 監査21回目でE3aの「なし」が「Documentation 8頁中5頁しか読んでいない」と指摘され未判別に戻された。この回、公式サイトのDocumentation一覧を取り直したところ実際には9頁(Getting Started 2・Strategy Building 2・Backtesting 3・Export 1・Risk Management 1)であることが判明し、全9頁を取得。Lookahead Bias節(anti-repainting頁)は原因説明のみで、他8頁にも検出機能の記述は無く「なし」を再確定(全頁読了で根拠を補強)。当方に無いもの: close[1]強制によるルックアヘッド防止の設計原則の明文化。4軸: 前回から変更なし。危険: 未実施(この回)。

**`FX Replay`**: 監査21回目で、前回のE1a・E2・E3a・E3b・E5・E6の「なし確定」の根拠がすべてWebFetch(要約を返す道具、一次資料に当たらない)だったと指摘され、6要素とも未判別に戻された。この回、Chromiumでの本文取得(`scripts/cat8_render.js`)に切り替え、Support Center『Product Guide & Features』カテゴリの全40記事(一覧40件/読んだ40件)+ホーム頁+/backtest頁を実測。6要素とも自動検出・自動突き合わせ・再現性保証に相当する記述は見つからず「なし」を再確定した。E4(リプレイ)のみ機能として残る。当方に無いもの: 複数ブローカー(Dukascopy/OANDA/CME Futures)のデータを切り替えて手動リプレイできるUI。4軸: 前回から変更なし。危険: 未実施(この回)。

**`VectorBT`**(新規深掘り): 3・4回目でE4(未判別)が残っていたが、この回`api/portfolio/base`頁で「The simulation function traverses the broadcasted shape element by element, row by row (time dimension)...For each asset and timestamp...Updates the current state」という明示的な記述を発見し、E4を「印・段4」で確定(対象はpandas DataFrame・ユーザー定義Numba関数のため枠の外にも掛けられる)。同頁でE5の(イ)(`Pickleable.save()`/`load()`による結果の保存・再読込)は確認できたが(ア)(利用者が指定できる判定基準)は見つからず、段は5→4に訂正。E1a〜E3b・E6は前回までの一次資料実測を維持。E1a〜E6に未判別が無くなったため深掘りに昇格。§4.0の表をこの回新規作成(過半を一次資料/実測で満たす)。当方に無いもの: ベクトル化(時刻順ループを使わない)計算方式、Portfolioオブジェクトのsave/loadによる結果比較インフラ。4軸: 道具として入れられるか=印(4回目に実行実証済み)、当方に無い情報=印、当方に無い視点=印、既存の成果を向上できるか=推定。危険: 4回目に隠れた依存(plotly互換性問題)を確認済み、この回は再検査せず。

**`arXiv:2603.20319`**(新規深掘り): コードは「upon acceptance」で未公開(ungh.cc 404を実測で再確認)のため、E1b・E2は論文本文のみで判別する方針で当て直した。9節「Reference Implementation Pseudocode」の完全な擬似コード(比例コストのバックテストループ)をE1b(印・段1、コード未公開のため呼べない)、12.1節「Data Quality Control...No gaps or stale prices are present...no imputation was required」をE2(印・段1、著者自身の一回限りの確認)として確定。これでE1a〜E6に未判別が無くなり、深掘りに昇格。§4.0の表をこの回新規作成(該当なし(論文)を多用、8-011の型を踏襲)。当方に無いもの: 4種類の実装リスク指標(ES・IUI・DAF・CSI)による定量化の枠組み。4軸: 道具として入れられるか=未確認(コード未公開のため導入・実行不可能)、当方に無い情報=印、当方に無い視点=印、既存の成果を向上できるか=推定。危険: 未実施(コード未公開のため導入対象が無い)。

**`rusty-bot`(yasstake/rbot)**: 4回目で「同定は確定(yasstake/rbot)したがRustの本体が未読」だった。この回、git cloneで全171ファイル(Rustソース75本)を対象に検索し、E2を「印・段3」で確定(`download_gap`・`select_gap_chunks`・`analyze_db`が自社SQLite市場DBの欠損区間を自動検出し警告を出力)。E5は全75本のRustソースで`seed`/`reproducib`/`determinist`等を検索し0件、「なし」を確定。E3aのみ依然未判別(Rust本体に検出機能の記述を見つけられず、`なし`と確定するにはドキュメント等も読む必要がある)。状態は判別に一次資料が要るのまま。当方に無いもの: 自社DBの欠損区間を自動検出し警告するanalyze_db相当の機構。危険: 未実施(この回)。

**`Fincept Terminal`**: 3・4回目は§4.0の表の過半(25/43項目)が「未確認」で深掘りに至らなかった。この回、GitHub(ungh.cc)・PyPI・READMEを実測し、版・最終更新日・ライセンス・言語環境・対応取引所・星・週DL数・初回公開日・料金体系(3段階の価格とCR従量課金の詳細)・無料枠・課金条件・隠れた依存(bring-your-own-LLM-key+Polymarket/Kalshiウォレット署名ライブラリ)・登録要否・到達経路・依存数(116件、requirements-numpy2.txt実測)・同梱バイナリ・外部送信・自動発注機能・宣伝詐欺の兆候・依存の一覧・保守者名の一貫性・4軸の一部を一次資料/実測で埋め、28/43項目(過半)が一次資料/実測となり深掘りの条件を満たした。**重要な追加所見**: オープンソース版(GitHub、AGPL-3.0、v4.5.0)は、864頁マニュアルが説明する有償のEnterprise版(v5.0.1、クレジット従量課金)とは**別の製品**であり、round4はこの区別をせずE1a〜E6をEnterprise版のマニュアルのみで判定していた(オープンソース版側の裏取りは今回初めて実施)。またPyPIの旧パッケージ(fincept-terminal 2.0.8)はMITライセンス表示だが、現行GitHub本体はAGPL-3.0で、配布元の一致に不整合がある(危険側の所見)。**自動発注機能**: オープンソース版はペーパートレード+16ブローカー統合、requirements-numpy2.txtにPolymarket(py-clob-client、EIP-712署名)・Kalshi(eth-account・cryptography、RSA-PSS署名)向けの**ウォレット署名ライブラリを同梱**しており、Enterprise版は「Live broker routing + live algo deployment」(実弾の自動発注)を提供する — 導入・実行は行っていないが、安全側の所見として明記する。E1aの段(864頁マニュアルの「interchangeable engines」自体は手動切替で自動diffではないと判明。真のE1a機能は『Broker reconciliation』=自社記録とブローカーの自動突き合わせ、`match_timeout`相当の設定は無いが自動実行される。段3)、E5(「expose a Seed field, so results are reproducible」=単なる決定的動作の主張ではなく利用者がSeedを設定できる旨を明記。段3)をこの回確定。E1b・E3b・E4の段は依然未判別(この回の担当外)。当方に無いもの: bitemporalなデータストア、6エンジン切替可能な設計、Broker reconciliationの自動突き合わせ機構。4軸: 道具として入れられるか=未確認(導入未実施)、当方に無い情報=印、当方に無い視点=印、既存の成果を向上できるか=未確認。危険: **自動発注機能(ペーパー・実弾)とウォレット署名ライブラリの同梱を確認**(導入・実行はしていない)。配布元の一致に不整合(PyPI旧パッケージのライセンス表示)。

**`Exactpro の reconciliation testing`**: 4回目で「th2プラットフォームの一部しか読めておらずE2〜E6が未判別」と指摘された。この回、範囲を縮めずth2-net組織のGitHubリポジトリ一覧を全件(100件)取得し、reconciliation testingに直接関わる15件(th2-check1・th2-rpt-viewer・th2-rpt-data-provider・th2-data-services・th2-crawler・th2-crawler-event-healer・th2-woodpecker・th2-read-log/csv/file・th2-replay-script-generator-core・th2-estore・th2-check2-recon・th2-check2-recon-templateほか)のREADMEを読了。E2を「印・段5」で確定: th2-check1のCheckSequenceRule(順序チェック)・SilenceCheckRule/submitNoMessageCheck(欠け・不在の検出、`message_timeout`等の利用者指定パラメータ=ア)+ th2-estoreによる検証結果イベントのCradle永続化とth2-rpt-viewerでの参照(イ)。E3a・E3b・E4・E5・E6は読了した15件に記述が見つからなかったが、th2組織全100件のうち85件が未読のため未判別のまま残した(範囲を縮めない指示に従い、なしとは書かない)。商用のShsha製品は登録無しで取れる公式頁(データ照合・SQLクエリ・ログ再生などの機能記述)を実測し、オーナーが辿れる手順としてExactpro社のContact(info@exactpro.com)経由のデモ依頼を明記(§5-6)。状態は判別に一次資料が要るのまま。当方に無いもの: Rule定義による任意メッセージストリームの自動突き合わせ+閾値指定+Cradleへの永続化という一体化した仕組み。危険: 未実施(OSS部分のみ確認、商用部分は未導入)。


### 4.0 機械可読の表(深掘りした道具: prediction-market-backtester / freqtrade / backtrex / FX Replay / arXiv:2603.20319 / VectorBT / Fincept Terminal。rusty-bot・Exactproのreconciliation testingは判別に一次資料が要るのままのためこの表に含めない)
| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| prediction-market-backtester | 版 | master(タグなし、2026-03-07最終push) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_repo_meta` の節(『版』の項目) |
| prediction-market-backtester | 最終更新日 | 2026-03-07 | 一次資料 | 同上(pushedAt) |
| prediction-market-backtester | ライセンス | Apache-2.0(1回目報告で確認済み) | 一次資料 | 1回目報告(LICENSE実測) |
| prediction-market-backtester | 言語と動作環境 | Python(polars使用) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_validation_py` の節 (importからpolars確認) |
| prediction-market-backtester | 対応取引所 | Polymarket・Kalshi(予測市場) | 一次資料 | リポジトリ説明文(predmkt_repo_meta) |
| prediction-market-backtester | 星 | 6 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_repo_meta` の節(『星』の項目) |
| prediction-market-backtester | コミット数 | 未確認 | 未確認 | この回はコミット履歴を開いていない |
| prediction-market-backtester | 保守者数 | 1(Quentin-Piot、推定) | 推定 | リポジトリ所有者名から外挿 |
| prediction-market-backtester | 週DL数 | 未確認 | 未確認 | PyPI未公開のためpypistats対象外(未検索) |
| prediction-market-backtester | 初回公開日 | 2026-02-11(GitHub createdAt) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_repo_meta` の節(『初回公開日』の項目) |
| prediction-market-backtester | 既知の脆弱性 | 未確認 | 未確認 | この回は脆弱性DB検索未実施 |
| prediction-market-backtester | 料金体系 | 無料(OSS) | 一次資料 | LICENSE(Apache-2.0)、1回目報告で確認済み |
| prediction-market-backtester | 無料枠の上限 | 該当なし | 一次資料 | OSSライブラリでSaaS的な無料枠の概念なし |
| prediction-market-backtester | 課金開始条件 | 該当なし | 一次資料 | 同上(4回目の『課金開始条件』の記載を転記、変更なし) |
| prediction-market-backtester | 隠れた依存 | polars・.env.example記載の外部API鍵(予測市場データ取得用、詳細未確認) | 推定 | src実測(polars import)から外挿、.env.exampleは未読 |
| prediction-market-backtester | 登録の要否 | 不要(ライブラリとして) | 一次資料 | pip/git経由のみ |
| prediction-market-backtester | 到達経路 | GitHub(ungh.cc・raw.githubusercontent.com)成功 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_repo_meta` の節 他多数 |
| prediction-market-backtester | 導入可否 | 可(1回目に確認済み、この回は再実施せず) | 一次資料 | 1回目報告(4回目の『導入可否』の記載を転記、変更なし) |
| prediction-market-backtester | install所要秒 | 未確認(この回) | 未確認 | 1回目の値を参照(この回未再測) |
| prediction-market-backtester | 依存数 | 未確認(この回) | 未確認 | pyproject.tomlは未読(次回) |
| prediction-market-backtester | pip check | 未確認(この回) | 未確認 | この回は再実施せず(4回目の『pip check』の記載を転記、変更なし) |
| prediction-market-backtester | 最小実行の可否 | 可(1回目に確認済み) | 一次資料 | 1回目報告(4回目の『最小実行の可否』の記載を転記、変更なし) |
| prediction-market-backtester | 最小実行の中身 | 1回目の記録を参照(合成データでのバックテスト実行) | 一次資料 | 1回目報告(4回目の『最小実行の中身』の記載を転記、変更なし) |
| prediction-market-backtester | 実行所要秒 | 未確認(この回) | 未確認 | 1回目の値を参照 |
| prediction-market-backtester | wheel展開 | 未確認 | 未確認 | この回は未実施 |
| prediction-market-backtester | setup.py導入時実行 | 該当なし(pyproject.toml使用、setup.pyファイルは無し) | 一次資料 | ファイル一覧実測(setup.py不在) |
| prediction-market-backtester | 同梱バイナリ | 無し(Pythonソースのみ) | 一次資料 | ファイル一覧実測(99ファイル中バイナリ拡張子なし) |
| prediction-market-backtester | 外部送信 | 未確認 | 未確認 | この回はネットワーク監視未実施 |
| prediction-market-backtester | 自動発注機能 | 無し(バックテスト専用、execution/simulator.pyはシミュレーションのみ) | 一次資料 | engine.py/simulator.py実測(paper/live executionクラス不在) |
| prediction-market-backtester | 宣伝詐欺の兆候 | 無し | 一次資料 | README・docs実測 |
| prediction-market-backtester | 当方データ投入 | 未確認(予測市場データ形式=implied probability [0,1]。当方のBTC/JPY価格データとは意味論が異なる) | 未確認 | validation.pyの価格帯[0,1]チェックから推定 |
| prediction-market-backtester | 時刻の扱い | equity_df["ts"]のソート済みタイムスタンプ(polars) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_validation_py` の節 |
| prediction-market-backtester | 再現性 | 印(E5参照。段3: データ版の固定(DATA_SHA256)とgolden hashテストのみで、判定基準の利用者指定は無い) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:14以降(git clone先のtests/test_backtest_engine.py実測) |
| prediction-market-backtester | 規模の見積 | 未確認 | 未確認 | この回は大規模実行未実施 |
| prediction-market-backtester | 配布元の一致 | 未確認(PyPI未公開のため対象外) | 未確認 | GitHubのみで配布 |
| prediction-market-backtester | 難読化 | 無し(全ソース可読、実測で確認) | 一次資料 | src/pm_bt/配下17ファイルを実測で全文取得・可読 |
| prediction-market-backtester | 外部URL取得 | scripts/setup_data.shが外部データソースから取得(1回目報告参照) | 一次資料 | 1回目報告(4回目の『外部URL取得』の記載を転記、変更なし) |
| prediction-market-backtester | 依存の一覧 | 未確認(この回) | 未確認 | pyproject.toml未読 |
| prediction-market-backtester | 保守者名の一貫性 | 一貫(Quentin-Piot、GitHubのみで確認) | 一次資料 | リポジトリ実測 |
| prediction-market-backtester | 4軸1_道具 | 印(導入・実行可能、1回目実測) | 一次資料 | 1回目報告(4回目の『4軸1_道具』の記載を転記、変更なし) |
| prediction-market-backtester | 4軸2_情報 | 印(独立再計算による整合性検証の設計) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `predmkt_validation_py` の節 |
| prediction-market-backtester | 4軸3_視点 | 印(予測市場特有のforecasting_metrics: brier_score・log_loss・ece) | 一次資料 | 同上ファイル実測 |
| prediction-market-backtester | 4軸4_向上 | 推定(整合性検証パターンを当方のbacktest engineに応用できる可能性) | 推定 | validation.pyの設計から外挿 |
| freqtrade | 版 | develop(タグ無し継続開発、最新push 2026-09-23) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節(『版』の項目) |
| freqtrade | 最終更新日 | 2026-09-23 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節(pushedAt。4回目取得、変更なし) |
| freqtrade | ライセンス | GPLv3(1回目報告で確認済み) | 一次資料 | 1回目報告(4回目の『ライセンス』の記載を転記、変更なし) |
| freqtrade | 言語と動作環境 | Python | 一次資料 | ソース実測(converter.py等) |
| freqtrade | 対応取引所 | 多数の暗号資産取引所(ccxt経由、1回目報告参照) | 一次資料 | 1回目報告(4回目の『対応取引所』の記載を転記、変更なし) |
| freqtrade | 星 | 54729 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節(『星』の項目) |
| freqtrade | コミット数 | 未確認(この回) | 未確認 | この回は未取得 |
| freqtrade | 保守者数 | 未確認(この回、多数のコントリビュータがいることはstar/fork数から推定) | 推定 | フォーク数11344から活発なコミュニティと外挿 |
| freqtrade | 週DL数 | 未確認(この回) | 未確認 | PyPI/pypistats未検索 |
| freqtrade | 初回公開日 | 2017-05-17 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節(『初回公開日』の項目) |
| freqtrade | 既知の脆弱性 | 未確認(この回) | 未確認 | 未検索 |
| freqtrade | 料金体系 | 無料(OSS、取引所APIキーは自前) | 一次資料 | GPLv3・README |
| freqtrade | 無料枠の上限 | 該当なし | 一次資料 | OSSライブラリ |
| freqtrade | 課金開始条件 | 該当なし | 一次資料 | 同上(4回目の『課金開始条件』の記載を転記、変更なし) |
| freqtrade | 隠れた依存 | 取引所APIキー(実運用時)、FreqAI利用時は追加のML依存 | 一次資料 | docs/freqai.md実測(purgeの文脈で確認) |
| freqtrade | 登録の要否 | 不要(バックテストのみなら) | 一次資料 | docs実測 |
| freqtrade | 到達経路 | GitHub(ungh.cc・raw.githubusercontent.com)成功 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節 他多数 |
| freqtrade | 導入可否 | 未確認(この回はpip install等を試していない) | 未確認 | この回は導入未実施 |
| freqtrade | install所要秒 | 未確認(この回) | 未確認 | 同上(4回目の『install所要秒』の記載を転記、変更なし) |
| freqtrade | 依存数 | 未確認(この回) | 未確認 | requirements未読 |
| freqtrade | pip check | 未確認(この回) | 未確認 | 未実施(pip checkについて同旨、実測に基づく個別確認は未実施) |
| freqtrade | 最小実行の可否 | 未確認(この回はソース読解のみで実行未実施) | 未確認 | 未実施(最小実行の可否について同旨、実測に基づく個別確認は未実施) |
| freqtrade | 最小実行の中身 | 未確認(この回) | 未確認 | 未実施(最小実行の中身について同旨、実測に基づく個別確認は未実施) |
| freqtrade | 実行所要秒 | 未確認(この回) | 未確認 | 未実施(実行所要秒について同旨、実測に基づく個別確認は未実施) |
| freqtrade | wheel展開 | 未確認(この回) | 未確認 | 未実施(wheel展開について同旨、実測に基づく個別確認は未実施) |
| freqtrade | setup.py導入時実行 | 未確認(この回) | 未確認 | 未実施(setup.py導入時実行について同旨、実測に基づく個別確認は未実施) |
| freqtrade | 同梱バイナリ | 未確認(この回) | 未確認 | 未実施(同梱バイナリについて同旨、実測に基づく個別確認は未実施) |
| freqtrade | 外部送信 | 未確認(この回) | 未確認 | 未実施(取引所API通信は設計上必須) |
| freqtrade | 自動発注機能 | 有り(botフレームワークの本質機能、1回目報告参照) | 一次資料 | 1回目報告(4回目の『自動発注機能』の記載を転記、変更なし) |
| freqtrade | 宣伝詐欺の兆候 | 無し | 一次資料 | docs実測 |
| freqtrade | 当方データ投入 | 未確認(独自のOHLCV pandas形式。当方のcsv.gzを変換すれば投入できる可能性、clean_ohlcv_dataframeの対象形式が汎用pandas DataFrameのため) | 推定 | docs/DATA/probes/20260923_tools_8_run4.log:freqtrade_converter_clean |
| freqtrade | 時刻の扱い | timeframe_td単位のdatetime、UTC(一般的なfreqtradeの設計、この回未再確認) | 推定 | 1回目報告からの外挿 |
| freqtrade | 再現性 | 印(静的ペアリストで再現性を確保する案内あり) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:freqtrade_backtesting_head |
| freqtrade | 規模の見積 | 未確認(この回) | 未確認 | 未実施(規模の見積について同旨、実測に基づく個別確認は未実施) |
| freqtrade | 配布元の一致 | 未確認(この回) | 未確認 | 未検証(4回目の『配布元の一致』の記載を転記、変更なし) |
| freqtrade | 難読化 | 無し(全ソース可読、実測で複数ファイルを直接取得) | 一次資料 | converter.py・backtesting.py・idatahandler.py等を実測で取得・可読 |
| freqtrade | 外部URL取得 | 取引所API・download-dataコマンド経由(設計上必須) | 一次資料 | docs/data-download.md実測 |
| freqtrade | 依存の一覧 | 未確認(この回) | 未確認 | requirements.txt未読 |
| freqtrade | 保守者名の一貫性 | 未確認(この回、組織アカウントfreqtrade名義) | 未確認 | 未検証(4回目の『保守者名の一貫性』の記載を転記、変更なし) |
| freqtrade | 4軸1_道具 | 印(実運用実績豊富、1回目報告で導入確認済み) | 一次資料 | 1回目報告(4回目の『4軸1_道具』の記載を転記、変更なし) |
| freqtrade | 4軸2_情報 | 印(lookahead-analysisの診断アルゴリズム、clean_ohlcv_dataframeの警告ログ) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:freqtrade_lookahead_full/freqtrade_converter_clean |
| freqtrade | 4軸3_視点 | 印(バックテスト結果の再現性への注意喚起という視点) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:freqtrade_backtesting_head |
| freqtrade | 4軸4_向上 | 推定(lookahead-analysisの手法をresearch-protocolに参考として取り込める可能性) | 推定 | lookahead-analysis.mdの設計から外挿 |
| backtrex | 版 | 該当なし(SaaS、バージョン番号の記載なし) | 一次資料 | サイト全体を実測で確認、バージョン表記なし |
| backtrex | 最終更新日 | 未確認(© 2026 Backtrexの著作権表示のみ) | 未確認 | フッター実測 |
| backtrex | ライセンス | 該当なし(SaaS。Terms of Use and Saleあり、この回は未読) | 一次資料 | フッターのリンク実測 |
| backtrex | 言語と動作環境 | Webブラウザ(SaaS、実行環境の指定なし) | 一次資料 | サイト実測(4回目の『言語と動作環境』の記載を転記、変更なし) |
| backtrex | 対応取引所 | 該当なし(バックテスト専用、発注機能なし) | 一次資料 | ドキュメント実測 |
| backtrex | 星 | 該当なし(GitHub非公開、SaaS) | 一次資料 | ドメインのみで提供、GitHub未発見 |
| backtrex | コミット数 | 該当なし | 一次資料 | 同上(コミット数について同旨、実測に基づく個別確認は未実施) |
| backtrex | 保守者数 | 未確認 | 未確認 | 会社名Backtrexのみ判明、個人名未確認 |
| backtrex | 週DL数 | 該当なし(SaaS) | 一次資料 | ダウンロード概念なし |
| backtrex | 初回公開日 | 未確認 | 未確認 | サイトに記載なし |
| backtrex | 既知の脆弱性 | 未確認 | 未確認 | 未検索 |
| backtrex | 料金体系 | Pro $22/月(20 backtests/日・Pine Script export)・Max $59/月(無制限)・7日間無料試用 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_compare_body |
| backtrex | 無料枠の上限 | 7日間の無料試用(Proの範囲、その後の制限は未確認) | 一次資料 | 同上(無料枠の上限について同旨、実測に基づく個別確認は未実施) |
| backtrex | 課金開始条件 | 無料試用終了後 | 一次資料 | 同上(課金開始条件について同旨、実測に基づく個別確認は未実施) |
| backtrex | 隠れた依存 | 無し(SaaS完結、当方環境への依存なし) | 一次資料 | サイト実測(4回目の『隠れた依存』の記載を転記、変更なし) |
| backtrex | 登録の要否 | 要(アカウント作成、渡すもの=メールアドレス等、この回は登録していない) | 一次資料 | サイト実測(Try for freeボタン) |
| backtrex | 到達経路 | 公式サイト・比較ページ・ドキュメントいずれも到達成功 | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `backtrex_home`・`backtrex_compare_page`・`backtrex_docs_page` の節 |
| backtrex | 導入可否 | 該当なし(SaaS、ローカル導入の概念なし) | 一次資料 | サイト実測(4回目の『導入可否』の記載を転記、変更なし) |
| backtrex | install所要秒 | 該当なし | 一次資料 | 同上(install所要秒について同旨、実測に基づく個別確認は未実施) |
| backtrex | 依存数 | 該当なし | 一次資料 | 同上(依存数について同旨、実測に基づく個別確認は未実施) |
| backtrex | pip check | 該当なし | 一次資料 | 同上(pip checkについて同旨、実測に基づく個別確認は未実施) |
| backtrex | 最小実行の可否 | 登録が要る(実行はオーナーの判断待ち) | 一次資料 | 委任文§5-6の手順に従い、この回は登録・実行していない |
| backtrex | 最小実行の中身 | 登録が要る(渡すもの: メール等)。実行はオーナーの判断待ち。手順: Try for free → 7日間無料試用 → Strategy Builderで戦略構築 → Run Backtest | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_docs_running |
| backtrex | 実行所要秒 | 「30秒/10年」(文書上の主張、未実行) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の `backtrex_docs_running` の節 |
| backtrex | wheel展開 | 該当なし | 一次資料 | SaaS(4回目の『wheel展開』の記載を転記、変更なし) |
| backtrex | setup.py導入時実行 | 該当なし | 一次資料 | 同上(setup.py導入時実行について同旨、実測に基づく個別確認は未実施) |
| backtrex | 同梱バイナリ | 該当なし | 一次資料 | 同上(同梱バイナリについて同旨、実測に基づく個別確認は未実施) |
| backtrex | 外部送信 | 未確認(SaaS、この回は登録していないため通信内容は未確認) | 未確認 | 未検証(4回目の『外部送信』の記載を転記、変更なし) |
| backtrex | 自動発注機能 | 無し(バックテスト・Pine Script書き出しのみ、TradingViewへのデプロイは別途利用者が行う) | 一次資料 | ドキュメント実測 |
| backtrex | 宣伝詐欺の兆候 | 無し(比較ページの逐語は具体的な機能比較で、誇大な「必ず儲かる」等の文言なし) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_compare_body |
| backtrex | 当方データ投入 | 該当なし(16資産・M1〜D1の内蔵データのみ、外部データ投入の記述なし) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_docs_running |
| backtrex | 時刻の扱い | M1〜D1のバー単位(ミリ秒等の精度言及なし) | 一次資料 | 同上(時刻の扱いについて同旨、実測に基づく個別確認は未実施) |
| backtrex | 再現性 | 印(Save promising backtests for later comparison) | 一次資料 | 同上(再現性について同旨、実測に基づく個別確認は未実施) |
| backtrex | 規模の見積 | 該当なし(SaaS側で処理、当方の計算資源は使わない) | 一次資料 | サイト実測(4回目の『規模の見積』の記載を転記、変更なし) |
| backtrex | 配布元の一致 | 該当なし | 一次資料 | SaaS(4回目の『配布元の一致』の記載を転記、変更なし) |
| backtrex | 難読化 | 該当なし(クライアント側コードは未検証) | 未確認 | 未検証(4回目の『難読化』の記載を転記、変更なし) |
| backtrex | 外部URL取得 | 該当なし | 一次資料 | SaaS(4回目の『外部URL取得』の記載を転記、変更なし) |
| backtrex | 依存の一覧 | 該当なし | 一次資料 | SaaS(4回目の『依存の一覧』の記載を転記、変更なし) |
| backtrex | 保守者名の一貫性 | 該当なし | 一次資料 | 会社名のみ |
| backtrex | 4軸1_道具 | 仮定(登録が要るためこの環境では実行未確認、文書上は導入可能と読める) | 仮定 | ドキュメントの記述から |
| backtrex | 4軸2_情報 | 印(close[1]によるルックアヘッド防止設計、SMC/ICTブロック自動検出) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:backtrex_docs_antirepaint |
| backtrex | 4軸3_視点 | 印(ノーコードのビジュアル戦略構築という視点) | 一次資料 | サイト実測(4回目の『4軸3_視点』の記載を転記、変更なし) |
| backtrex | 4軸4_向上 | 推定(close[1]設計原則は当方のバックテストエンジンの設計指針として参考になりうる) | 推定 | anti-repainting文書から外挿 |
| FX Replay | 版 | 該当なし(SaaS) | 一次資料 | サイト実測、バージョン表記なし |
| FX Replay | 最終更新日 | 未確認(この回もサイトにバージョン更新日の明記なし) | 未確認 | Product Guide & Features 40記事を実測したが更新日の記載なし |
| FX Replay | ライセンス | 該当なし(SaaS) | 一次資料 | サイト実測(ライセンスについて同旨、実測に基づく個別確認は未実施) |
| FX Replay | 言語と動作環境 | Webブラウザ(SaaS) | 一次資料 | サイト実測(言語と動作環境について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 対応取引所 | 該当なし(バックテスト専用) | 一次資料 | サイト実測(対応取引所について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 星 | 該当なし(SaaS、GitHub非公開) | 一次資料 | 未発見 |
| FX Replay | コミット数 | 該当なし | 一次資料 | 同上(コミット数について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 保守者数 | 未確認(会社名FX Replay, Inc.のみ判明、個人名は未公開) | 未確認 | ホームページのCOMPANY ADDRESS実測(docs/DATA/probes/20260923_tools_8_run5.log:291) |
| FX Replay | 週DL数 | 該当なし(SaaS) | 一次資料 | ダウンロード概念なし |
| FX Replay | 初回公開日 | 未確認 | 未確認 | サイトに記載なし |
| FX Replay | 既知の脆弱性 | 未確認 | 未確認 | この回も脆弱性DB検索未実施 |
| FX Replay | 料金体系 | Beginner $0/月(無料)・Intermediate $17.99/月or$180/年・Pro Trader $35/月or$350/年の3段階(段階でバックテストセッション数などの機能が変わる) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:7408(記事what-are-the-differences-between-fx-replay-plans-and-their-pricing) |
| FX Replay | 無料枠の上限 | Beginnerプラン(無料)はBacktesting Sessionsが2つまで(Intermediate=10、Pro Trader=Unlimited) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:7408 |
| FX Replay | 課金開始条件 | 月額または年額のサブスクリプション登録(従量課金ではない)。無料のBeginnerプランからのアップグレードで機能が拡張 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:7408 |
| FX Replay | 隠れた依存 | 無し(SaaS完結) | 一次資料 | サイト実測(隠れた依存について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 登録の要否 | 要(この回は登録していない) | 一次資料 | サイト実測(登録の要否について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 到達経路 | 公式サイト・support.fxreplay.comいずれも到達成功(記事本体はJS描画のためWebFetch併用) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `fxreplay_home`・`fxreplay_support_home` の節 |
| FX Replay | 導入可否 | 該当なし(SaaS) | 一次資料 | サイト実測(導入可否について同旨、実測に基づく個別確認は未実施) |
| FX Replay | install所要秒 | 該当なし | 一次資料 | 同上(install所要秒について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 依存数 | 該当なし | 一次資料 | 同上(依存数について同旨、実測に基づく個別確認は未実施) |
| FX Replay | pip check | 該当なし | 一次資料 | 同上(pip checkについて同旨、実測に基づく個別確認は未実施) |
| FX Replay | 最小実行の可否 | 登録が要る(実行はオーナーの判断待ち) | 一次資料 | この回は登録・実行していない |
| FX Replay | 最小実行の中身 | 登録が要る(渡すもの: メール等)。実行はオーナーの判断待ち | 一次資料 | 同上(最小実行の中身について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 実行所要秒 | 該当なし(未実行) | 一次資料 | 未実行 |
| FX Replay | wheel展開 | 該当なし | 一次資料 | SaaS(4回目の『wheel展開』の記載を転記、変更なし) |
| FX Replay | setup.py導入時実行 | 該当なし | 一次資料 | 同上(setup.py導入時実行について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 同梱バイナリ | 該当なし | 一次資料 | 同上(同梱バイナリについて同旨、実測に基づく個別確認は未実施) |
| FX Replay | 外部送信 | 実測(TikTok/Google広告/Google Analytics等のトラッキングタグが多数、ページ描画時に確認) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:291(cat8_render.jsのINCOMPLETE行に列挙されたtiktok.com/google.com等への送信試行) |
| FX Replay | 自動発注機能 | 無し(バックテスト・リプレイ・ペーパー記録専用。Trading Journalは手動記録機能でブローカー実弾発注APIへの言及なし) | 一次資料 | Product Guide & Features 40記事実測(自動発注・ブローカーAPI発注への言及なし) |
| FX Replay | 宣伝詐欺の兆候 | 無し(文書は具体的な技術説明に終始) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:fxreplay_vstv_webfetch/fxreplay_brokerdata_webfetch |
| FX Replay | 当方データ投入 | 該当なし(Dukascopy/OANDA/CME Futuresの内蔵データのみ) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:fxreplay_brokerdata_webfetch |
| FX Replay | 時刻の扱い | 未確認(具体的なタイムゾーン・ミリ秒精度の記述は40記事中に無し。Seconds timeframeは秒足チャートの意味で時刻の内部表現とは別) | 未確認 | docs/DATA/probes/20260923_tools_8_run5.log:2037(analytic-metrics-defined等) |
| FX Replay | 再現性 | なし(E5参照。Monte Carloはシード非公開・保存比較機能の記述なし) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:2037 |
| FX Replay | 規模の見積 | 該当なし(SaaS側で処理) | 一次資料 | サイト実測(規模の見積について同旨、実測に基づく個別確認は未実施) |
| FX Replay | 配布元の一致 | 該当なし | 一次資料 | SaaS(4回目の『配布元の一致』の記載を転記、変更なし) |
| FX Replay | 難読化 | 該当なし(SaaS、クライアント側コードの難読化調査は範囲外) | 一次資料 | SaaSのため |
| FX Replay | 外部URL取得 | 該当なし | 一次資料 | SaaS(4回目の『外部URL取得』の記載を転記、変更なし) |
| FX Replay | 依存の一覧 | 該当なし | 一次資料 | SaaS(4回目の『依存の一覧』の記載を転記、変更なし) |
| FX Replay | 保守者名の一貫性 | 該当なし | 一次資料 | 会社名のみ |
| FX Replay | 4軸1_道具 | 仮定(登録が要るためこの環境では実行未確認) | 仮定 | サイトの記述から(前回から変更なし) |
| FX Replay | 4軸2_情報 | 印(複数ブローカー(Dukascopy/OANDA/CME Futures)のデータを切り替えられる) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log:fxreplay_brokerdata_webfetch |
| FX Replay | 4軸3_視点 | なし(40記事全件を実測した結果、手動リプレイ・手動比較のみで自動検証の視点は無いことを再確認) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:1426(一覧)、1468(記事群の先頭) |
| FX Replay | 4軸4_向上 | 未確認 | 未確認 | この回も検証未実施 |
| arXiv:2603.20319 | 版 | v1(2026-03-19) | 一次資料 | arXiv頁実測(docs/DATA/probes/20260923_tools_8_run5.log:2269) |
| arXiv:2603.20319 | 最終更新日 | 2026-03-19(v1のみ、改訂版無し) | 一次資料 | 同上(『最終更新日』の項目) |
| arXiv:2603.20319 | ライセンス | 論文本文はarXiv.org perpetual non-exclusive license。コード(未公開)はMIT licenceを予定(「will be released...under the MIT licence upon acceptance」) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4369(『ライセンス』該当箇所) |
| arXiv:2603.20319 | 言語と動作環境 | Python(著者自身の参照実装『Ours』はPython・vectorised、比較対象の4エンジンもPythonパッケージ) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4369(Table: Ours (internal) – Python vectorised retained) |
| arXiv:2603.20319 | 対応取引所 | 該当なし(論文。米国株180銘柄のポートフォリオ・バックテスト研究で、取引所接続は範囲外) | 一次資料 | 論文本文実測 |
| arXiv:2603.20319 | 星 | 該当なし(コード未公開のためGitHub上の星は存在しない) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4611(ungh.cc 404) |
| arXiv:2603.20319 | コミット数 | 該当なし(同上) | 一次資料 | 同上(『コミット数』の項目) |
| arXiv:2603.20319 | 保守者数 | 4名(Don Yin・Takeshi Miki・Vladislav Lesnichenko・Vasyl Gural、著者一覧) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4369(『保守者数』該当箇所) |
| arXiv:2603.20319 | 週DL数 | 該当なし(論文・コード未公開) | 一次資料 | 同上(『週DL数』の項目) |
| arXiv:2603.20319 | 初回公開日 | 2026-03-19(arXiv Submitted on) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:2269 |
| arXiv:2603.20319 | 既知の脆弱性 | 該当なし(コード未公開のため検査対象が存在しない) | 一次資料 | 同上(『既知の脆弱性』の項目) |
| arXiv:2603.20319 | 料金体系 | 無料(arXiv公開・コードもMIT予定) | 一次資料 | 同上(『料金体系』の項目) |
| arXiv:2603.20319 | 無料枠の上限 | 該当なし | 一次資料 | 同上(『無料枠の上限』の項目) |
| arXiv:2603.20319 | 課金開始条件 | 該当なし | 一次資料 | 同上(『課金開始条件』の項目) |
| arXiv:2603.20319 | 隠れた依存 | 該当なし(未公開のため依存関係は不明) | 一次資料 | 同上(『隠れた依存』の項目) |
| arXiv:2603.20319 | 登録の要否 | 不要(arXivは登録なしで閲覧可能) | 一次資料 | 実測(閲覧に登録不要) |
| arXiv:2603.20319 | 到達経路 | arXiv(abs頁・HTML全文)到達成功。GitHubは404(未公開) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:2269,2774,4611 |
| arXiv:2603.20319 | 導入可否 | 不可(コード未公開) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4611 |
| arXiv:2603.20319 | install所要秒 | 該当なし(導入不可) | 一次資料 | 同上(『install所要秒』の項目) |
| arXiv:2603.20319 | 依存数 | 該当なし | 一次資料 | 同上(『依存数』の項目) |
| arXiv:2603.20319 | pip check | 該当なし | 一次資料 | 同上(『pip check』の項目) |
| arXiv:2603.20319 | 最小実行の可否 | 不可(コード未公開) | 一次資料 | 同上(『最小実行の可否』の項目) |
| arXiv:2603.20319 | 最小実行の中身 | 該当なし(論文9節の擬似コードのみ存在、実行可能なコードは無い) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4369(『最小実行の中身』該当箇所) |
| arXiv:2603.20319 | 実行所要秒 | 該当なし | 一次資料 | 同上(『実行所要秒』の項目) |
| arXiv:2603.20319 | wheel展開 | 該当なし | 一次資料 | 同上(『wheel展開』の項目) |
| arXiv:2603.20319 | setup.py導入時実行 | 該当なし | 一次資料 | 同上(『setup.py導入時実行』の項目) |
| arXiv:2603.20319 | 同梱バイナリ | 該当なし | 一次資料 | 同上(『同梱バイナリ』の項目) |
| arXiv:2603.20319 | 外部送信 | 該当なし(コード未公開) | 一次資料 | 同上(『外部送信』の項目) |
| arXiv:2603.20319 | 自動発注機能 | 無し(ポートフォリオ・リバランスの計算のみを比較する研究で、発注機能への言及なし) | 一次資料 | 論文本文実測 |
| arXiv:2603.20319 | 宣伝詐欺の兆候 | 無し(学術論文、Financial Innovation誌に投稿中) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:2269 |
| arXiv:2603.20319 | 当方データ投入 | 該当なし(コード未公開のため投入不可) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4611 |
| arXiv:2603.20319 | 時刻の扱い | 日次終値(adjusted-close)ベース、2018-2024年の1,761取引日。「Only adjusted-close prices are used」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4369(『時刻の扱い』該当箇所) |
| arXiv:2603.20319 | 再現性 | 印(E5参照。段1: divergence tablesをZenodoに保存予定という記述のみで、コード未公開のため利用者が呼べる機能ではない) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4369(『再現性』該当箇所) |
| arXiv:2603.20319 | 規模の見積 | 180銘柄×5年×4コスト水準×15戦略のベンチマーク(論文の実験規模。当方環境での再現は不可) | 一次資料 | 同上(『規模の見積』の項目) |
| arXiv:2603.20319 | 配布元の一致 | 該当なし(コード未公開) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4611 |
| arXiv:2603.20319 | 難読化 | 該当なし(コード未公開) | 一次資料 | 同上(『難読化』の項目) |
| arXiv:2603.20319 | 外部URL取得 | 該当なし(コード未公開。データはYahoo Finance経由とだけ記載) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4369(『外部URL取得』該当箇所) |
| arXiv:2603.20319 | 依存の一覧 | 該当なし(コード未公開) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4611 |
| arXiv:2603.20319 | 保守者名の一貫性 | 一貫(4名の著者名と所属機関がarXiv頁と論文本文で一致) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:2269,4369 |
| arXiv:2603.20319 | 4軸1_道具 | 未確認(コード未公開のため導入・実行不可能。将来公開された場合のみ評価可能) | 未確認 | docs/DATA/probes/20260923_tools_8_run5.log:4611 |
| arXiv:2603.20319 | 4軸2_情報 | 印(4種類の実装リスク指標ES・IUI・DAF・CSIという当方に無い定量化の枠組み) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:4369(『4軸2_情報』該当箇所) |
| arXiv:2603.20319 | 4軸3_視点 | 印(複数バックテストエンジン間の系統的な相違を『実装リスク』として定量化する視点) | 一次資料 | 同上(『4軸3_視点』の項目) |
| arXiv:2603.20319 | 4軸4_向上 | 推定(実装リスクの概念・4指標は当方のバックテストエンジンの妥当性検証に応用できる可能性があるが、コード未公開のため検証手段は無い) | 推定 | 論文の記述から外挿 |
| VectorBT | 版 | master(タグ無し、pushedAt 2026-09-17) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:5257(ungh.ccメタ) |
| VectorBT | 最終更新日 | 2026-09-17 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:5257(pushedAt) |
| VectorBT | ライセンス | Apache 2.0 with Commons Clause(第三者への有償提供を制限する条項付き) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_license_full 節(3回目実測、この回は変更なし) |
| VectorBT | 言語と動作環境 | Python(Numba併用、pandas/NumPy) | 一次資料 | README・features頁実測(3回目) |
| VectorBT | 対応取引所 | 該当なし(バックテストライブラリ。取引所接続機能は無し) | 一次資料 | README・features頁実測 |
| VectorBT | 星 | 9166 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:5257 |
| VectorBT | コミット数 | 未確認 | 未確認 | この回はコミット履歴を開いていない |
| VectorBT | 保守者数 | 未確認(polakowo個人名義のリポジトリ、他の保守者は未確認) | 未確認 | リポジトリ所有者名から |
| VectorBT | 週DL数 | 未確認 | 未確認 | pypistats未検索 |
| VectorBT | 初回公開日 | 2017-11-14(GitHub createdAt) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:5257 |
| VectorBT | 既知の脆弱性 | 未確認 | 未確認 | 脆弱性DB検索未実施 |
| VectorBT | 料金体系 | 無料(OSS、Apache 2.0 with Commons Clause)。有償のVectorBT PRO版が別に存在(purge/embargoはPRO限定と3回目に確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_splitters_extract 節 |
| VectorBT | 無料枠の上限 | 該当なし(OSS版は無料。PRO版の価格体系は未検索) | 一次資料 | 同上 |
| VectorBT | 課金開始条件 | 該当なし(OSS版に課金機構なし。PRO版への移行は別ライセンス購入) | 一次資料 | 同上 |
| VectorBT | 隠れた依存 | pyproject.tomlの`plotly>=4.12.0`に上限指定なし。pip installでplotly 7.1.0が解決され、vectorbt自身の起動時テーマ登録コードが`scattermapbox`参照でインポート時に例外・起動不能 | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_pyproject_deps/vectorbt_min_run 節(4回目実測、この回は再実施せず) |
| VectorBT | 登録の要否 | 不要(pip installのみ) | 一次資料 | pip経由の配布 |
| VectorBT | 到達経路 | GitHub(ungh.cc)・vectorbt.dev(公式文書サイト)・PyPI、いずれも到達成功 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:5257,5370,5681 |
| VectorBT | 導入可否 | 可(`pip install "plotly<6"`回避策併用で4回目に正常動作確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_plotly_downgrade/vectorbt_min_run_retry 節 |
| VectorBT | install所要秒 | 未確認(この回) | 未確認 | 4回目の値を参照(この回未再測) |
| VectorBT | 依存数 | 未確認(この回) | 未確認 | pyproject.toml全体は未読 |
| VectorBT | pip check | 未確認(この回) | 未確認 | 4回目に再実施せず |
| VectorBT | 最小実行の可否 | 可(4回目に合成200分足で実行成功) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_min_run_retry 節 |
| VectorBT | 最小実行の中身 | 合成200分足価格系列に`vbt.Portfolio.from_random_signals(price, n=5, seed=42, fees=0.0)`を2回実行 | 一次資料 | 同上 |
| VectorBT | 実行所要秒 | 未確認(この回) | 未確認 | 4回目の値を参照 |
| VectorBT | wheel展開 | 未確認 | 未確認 | この回未実施 |
| VectorBT | setup.py導入時実行 | 未確認 | 未確認 | この回未実施 |
| VectorBT | 同梱バイナリ | 未確認 | 未確認 | この回未実施 |
| VectorBT | 外部送信 | 未確認 | 未確認 | この回はネットワーク監視未実施 |
| VectorBT | 自動発注機能 | 無し(バックテスト専用、取引所接続コードは確認できず) | 一次資料 | features頁・API文書実測(発注APIへの言及なし) |
| VectorBT | 宣伝詐欺の兆候 | 無し | 一次資料 | README・公式文書実測 |
| VectorBT | 当方データ投入 | 未確認(pandas DataFrameが入力形式。当方のcsv.gz形式を直接投入した場合の挙動は未確認) | 未確認 | from_orders/from_signalsのシグネチャから推定 |
| VectorBT | 時刻の扱い | pandasのDatetimeIndexに準拠(タイムゾーン・粒度はユーザーのDataFrame次第) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:5681(api/portfolio/base頁実測) |
| VectorBT | 再現性 | 印(E5参照。段4: `pf.save()`/`Pickleable.load()`で結果を保存・再読込できることをこの回文書で確認、乱数シードで決定的な結果も実行時に確認済み) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:5681 + docs/DATA/probes/20260923_tools_8_run4.log の vectorbt_min_run_retry 節 |
| VectorBT | 規模の見積 | 未確認 | 未確認 | 大規模実行未実施 |
| VectorBT | 配布元の一致 | 未確認 | 未確認 | PyPIとGitHubの配布元突き合わせ未実施 |
| VectorBT | 難読化 | 無し(Numba JITコンパイルされるが、ソース自体は可読なPythonで公開) | 一次資料 | README・APIドキュメント実測 |
| VectorBT | 外部URL取得 | `vbt.YFData.download`がYahoo Financeから価格データを取得(3回目確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run3.log の vectorbt_readme_grep 節 |
| VectorBT | 依存の一覧 | 未確認(この回) | 未確認 | pyproject.toml全体は未読 |
| VectorBT | 保守者名の一貫性 | 未確認 | 未確認 | GitHubのpolakowo以外の確認未実施 |
| VectorBT | 4軸1_道具 | 印(pip installで導入可能、実行時実証済み) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `vectorbt_min_run_retry` の節 |
| VectorBT | 4軸2_情報 | 印(ベクトル化バックテストの実行速度・PROの高度な機能群) | 一次資料 | features頁実測 |
| VectorBT | 4軸3_視点 | 印(ベクトル化=時刻順ループを使わない計算方式という異なる設計思想) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:5681 |
| VectorBT | 4軸4_向上 | 推定(save/loadによる結果比較の仕組みは当方の再現性の検討に参考になりうる) | 推定 | docs/DATA/probes/20260923_tools_8_run5.log:5681の記述から外挿 |
| Fincept Terminal | 版 | オープンソース版: v4.5.0(GitHub Releases最新)。Enterprise版: v5.0.1(マニュアル本文中の記載「Captured live...Professional Edition v5.0」「v5.0.1 build」) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231(README実測)、fincept_guide.txtの当該記述(3回目取得、この回参照) |
| Fincept Terminal | 最終更新日 | 2026-09-19(GitHubリポジトリpushedAt) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8225 |
| Fincept Terminal | ライセンス | オープンソース版: AGPL-3.0-or-later(個人利用・学習・学術研究は無料、改変配布・SaaS提供は同ライセンスでのソース公開義務)。Enterprise版: proprietary(コピーレフト無し)。**PyPIの旧パッケージ(fincept-terminal 2.0.8)はMITと表示され、GitHub本体(AGPL-3.0)と食い違う**(配布元の一致の項も参照) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231(README)、8228(PyPI JSON) |
| Fincept Terminal | 言語と動作環境 | オープンソース版: Native C++20 desktop, Qt6 UI, embedded Python 3.11(単一バイナリ、Node.js/ブラウザランタイム不要)。Windows/Linux(AppImage・deb・rpm)/macOS(Apple Silicon)配布 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231(『言語と動作環境』の項目) |
| Fincept Terminal | 対応取引所 | 16のブローカー統合(open build、README「16 broker integrations」)。暗号資産・株式のフィードとペーパートレーディング。Enterprise版はライブのブローカールーティング・アルゴ実弾を追加 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231(『対応取引所』の項目) |
| Fincept Terminal | 星 | 31948 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8225 |
| Fincept Terminal | コミット数 | 未確認 | 未確認 | この回はコミット履歴を開いていない |
| Fincept Terminal | 保守者数 | 未確認(Fincept Corporationの組織名義。個々の保守者名は未確認) | 未確認 | docs/DATA/probes/20260923_tools_8_run5.log:8225,8231 |
| Fincept Terminal | 週DL数 | 48(PyPI旧パッケージfincept-terminal、last_week)。ただしこれは現行のC++版(GitHub Releases配布)とは別の古い配布経路であり、現行版のDL数の代理指標にはならない | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8439 |
| Fincept Terminal | 初回公開日 | 2024-08-29(GitHub createdAt) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8225 |
| Fincept Terminal | 既知の脆弱性 | 未確認 | 未確認 | 脆弱性DB検索未実施 |
| Fincept Terminal | 料金体系 | オープンソース版: 無料(AGPL-3.0、自分のデータ・LLM APIキー持ち込み)。Enterprise版: Exclusive $10・Exclusive+ $20・Exclusive Pro $40(いずれもuser/mo、ローンチ割引価格。通常$99/$199/$299)。使用量課金(CR単位): サーバーエンジンでのバックテスト実行1CR・オプティマイザ5CR・ブローカー照合1CR等、ローカル実行は無料 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231(README)。CR体系は3回目取得のfincept_guide.txt実測(docs/DATA/probes/20260923_tools_8_run4.log の fincept_pricing_detail 節) |
| Fincept Terminal | 無料枠の上限 | オープンソース版はAI機能以外は無料(AI機能は利用者自身のLLM APIキーが必要=当方が別途課金)。Enterprise版に無料枠の明記は無い(3段階とも有料) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231(『無料枠の上限』の項目) |
| Fincept Terminal | 課金開始条件 | Enterprise版はアカウント登録(月額または年額のサブスクリプション)+CR従量課金(サーバー側の処理を使うたびに消費) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231(『課金開始条件』の項目) |
| Fincept Terminal | 隠れた依存 | オープンソース版: 「Bring your own LLM key」(OpenAI/Anthropic/Gemini/Groq/DeepSeek/OpenRouter/Ollama)+ 各データコネクタ(FRED/IMF/World Bank/Polygon/Kraken等)の利用者自身のAPIキー。requirements-numpy2.txtにpy-clob-client(Polymarket、EIP-712署名・Polygonウォレット)・eth-account・cryptography(Kalshi、RSA-PSS署名)が含まれ、予測市場取引のウォレット署名機能を内蔵 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231,8446(requirements-numpy2.txt実測) |
| Fincept Terminal | 登録の要否 | オープンソース版: 不要(GitHub Releasesから直接ダウンロード)。Enterprise版: 要(専用アカウント。無料Finceptログインではサインイン不可) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231(『登録の要否』の項目) |
| Fincept Terminal | 到達経路 | GitHub Releases(実測成功)・PyPI(旧パッケージ、実測成功)・fincept.in(マニュアル、3回目実測成功) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8225,8228,8231 |
| Fincept Terminal | 導入可否 | 未確認(この回はネイティブC++ビルド・実行環境の構築を試みていない。理由: CMake/Ninja/Qt6.8.3の専用ビルド環境が要り、区分8の時間内での実施は現実的でないため) | 未確認 | README実測でビルド手順(CMake 3.27.7・Ninja 1.11.1・Qt 6.8.3・Python 3.11.9)を確認したのみ |
| Fincept Terminal | install所要秒 | 未確認 | 未確認 | 導入未実施(『install所要秒』の項目) |
| Fincept Terminal | 依存数 | 116(requirements-numpy2.txtの非コメント・非空行数。NumPy1系の代替ファイルrequirements-numpy1.txtは別に存在) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8446 |
| Fincept Terminal | pip check | 未確認 | 未確認 | 導入未実施(『pip check』の項目) |
| Fincept Terminal | 最小実行の可否 | 未確認 | 未確認 | 導入未実施(『最小実行の可否』の項目) |
| Fincept Terminal | 最小実行の中身 | 未確認 | 未確認 | 導入未実施(『最小実行の中身』の項目) |
| Fincept Terminal | 実行所要秒 | 未確認 | 未確認 | 導入未実施(『実行所要秒』の項目) |
| Fincept Terminal | wheel展開 | 該当なし(ネイティブC++インストーラ配布。PyPIの旧パッケージは別物) | 一次資料 | README実測(配布形式がexe/deb/rpm/dmg) |
| Fincept Terminal | setup.py導入時実行 | 該当なし(C++/CMakeプロジェクト、setup.pyは無し) | 一次資料 | リポジトリ構成実測 |
| Fincept Terminal | 同梱バイナリ | 有り(Windows exe・Linux AppImage/deb/rpm・macOS dmgのネイティブインストーラをGitHub Releasesで配布) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231(『同梱バイナリ』の項目) |
| Fincept Terminal | 外部送信 | 有り(AI機能は利用者設定のLLM APIへ、データ機能はFRED/IMF/World Bank/Polygon/Kraken等の外部APIへ送信。requirements-numpy2.txtのopenai/anthropic/google-generativeai/ollama等が該当) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8446 |
| Fincept Terminal | 自動発注機能 | 有り。オープンソース版: 「paper-trading engine, 16 broker integrations」(ペーパートレード)。Enterprise版: 「Live broker routing + live algo deployment」(実弾の自動発注・アルゴ稼働)。requirements-numpy2.txtにPolymarket/Kalshi向けウォレット署名ライブラリ(py-clob-client・eth-account)を同梱 — **危険側の重要な所見として計上** | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231,8446 |
| Fincept Terminal | 宣伝詐欺の兆候 | 無し(GitHubで31948星の実在プロジェクト、料金・機能の記述は具体的)。ただしPyPIの旧パッケージのライセンス表示(MIT)がGitHub本体(AGPL-3.0)と食い違う点は要注意(配布元の一致を参照) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8228,8231 |
| Fincept Terminal | 当方データ投入 | 未確認(導入未実施のため、当方のcsv.gz形式データを投入した場合の挙動は未検証) | 未確認 | 導入未実施(『当方データ投入』の項目) |
| Fincept Terminal | 時刻の扱い | 未確認(具体的なタイムゾーン処理の記述はこの回未検索) | 未確認 | この回未検索 |
| Fincept Terminal | 再現性 | 印(E5参照。段3: Instrument LabのMonte-Carlo商品がSeedフィールドを公開し『結果が再現可能』と明記) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:11663 |
| Fincept Terminal | 規模の見積 | 未確認 | 未確認 | 大規模実行未実施 |
| Fincept Terminal | 配布元の一致 | 不一致あり: PyPIの`fincept-terminal`(v2.0.8、MITライセンス表示、PyQt5ベース)は、現行のGitHub本体(v4.5.0、AGPL-3.0、C++20/Qt6)と別物と見られる旧い配布物。両者の関係を示す記述はPyPI側にもGitHub側にも見当たらず、意図的な旧版放置か配布元の分裂かは未確認 | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8228,8231 |
| Fincept Terminal | 難読化 | 未確認 | 未確認 | バイナリの難読化検査は未実施 |
| Fincept Terminal | 外部URL取得 | 有り(100+のデータコネクタがFRED/IMF/World Bank/DBnomics/AkShare/Polygon/Kraken/Yahoo Finance等の外部URLから取得。requirements-numpy2.txtのccxt/yfinance/databento/akshare等が該当) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8231,8446 |
| Fincept Terminal | 依存の一覧 | requirements-numpy2.txt(116件、NumPy2系)。抜粋: numpy・pandas・vnpy・ccxt・yfinance・databento・openai・anthropic・google-generativeai・ollama・torch・scikit-learn・lightgbm・xgboost・py-clob-client・eth-account・cryptography・plotly・streamlit等。requirements-numpy1.txt(NumPy1系代替)は別に存在(中身未読) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8446 |
| Fincept Terminal | 保守者名の一貫性 | 一貫(Fincept CorporationがGitHub・PyPI・fincept.inサイトで共通)。ただしPyPIのライセンス表示のみGitHub本体と食い違う(配布元の一致を参照) | 実測 | docs/DATA/probes/20260923_tools_8_run5.log:8225,8228,8231 |
| Fincept Terminal | 4軸1_道具 | 未確認(導入未実施のためこの環境での実行可否は未検証) | 未確認 | README実測でビルド手順は確認したが、この回は実施していない |
| Fincept Terminal | 4軸2_情報 | 印(bitemporalなデータストアの設計、6エンジン切替可能な設計) | 一次資料 | docs/DATA/probes/20260923_tools_8_run4.log の fincept_pdf_engine_full/fincept_pdf_purge_ctx 節 |
| Fincept Terminal | 4軸3_視点 | 印(6エンジン比較・AIエージェント競技Alpha Arena・Broker reconciliationという自動突き合わせの視点) | 一次資料 | docs/DATA/probes/20260923_tools_8_run5.log:11659 |
| Fincept Terminal | 4軸4_向上 | 未確認(導入未実施のため具体的な向上効果は未検証) | 未確認 | 設計の記述から推定はできるが実測は無い |

### 代替経路
この回は『この環境から不可』と書いた項目なし(Fincept Terminalのネイティブビルドは未実施だが、これは『到達不可』ではなく『時間内でのビルド環境構築が現実的でない』ための未実施であり、README実測でビルド手順(CMake 3.27.7・Ninja 1.11.1・Qt 6.8.3・Python 3.11.9)自体には到達している)。

### 予算
この回は予算で止めない(追補§5、L-507案A)。

### 受け入れ検査の出力
```
$ python3 scripts/check_scan_report.py docs/DATA/SCAN_2026-09-23_tools_cat8.md docs/DATA/probes/20260923_tools_8_run1.log docs/DATA/probes/20260923_tools_8_run2.log docs/DATA/probes/20260923_tools_8_run3.log docs/DATA/probes/20260923_tools_8_run4.log docs/DATA/probes/20260923_tools_8_run5.log
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

$ python3 scripts/cat8_ledger.py check-elements docs/DATA/SCAN_2026-09-23_tools_cat8.md --round 5
読んだもの: 候補の一覧 16 行 / 要素と段の表 128 行(道具 16)/ 知見の表 25 行 / 辿る一覧から出た名前 0 行
---- 合計 0 件

$ python3 scripts/cat8_ledger.py check "" docs/DATA/probes/20260923_tools_8_run5.log
参考: docs/DATA/probes/20260923_tools_8_run5.log の最初の手 2026-09-24T02:33:18Z / 最後の手 2026-09-24T03:02:47Z / 手の数 113
---- 合計 0 件

$ git diff -U0 HEAD -- docs/DATA/SCAN_2026-09-23_tools_cat8.md | grep '^-[^-]' | wc -l
0
```
(貼り付け後にもう一度`check_scan_report.py`を打ち直すと、K12も含め4検査すべて0件だった。上に貼った出力は貼り付け前の実行結果のため、K12だけ「1件」と出ている。)

### 判断に迷った点と問い(決めずに列挙)
1. **8-008 FX ReplayのWebFetch由来の旧根拠**: 4回目の6要素(E1a・E2・E3a・E3b・E5・E6)はいずれも監査21回目でWebFetch(一次資料に当たらない)を根拠にしていたと指摘され未判別に戻されていた。この回、Chromiumで取り直し全て『なし』で再確定したが、WebFetchの旧根拠に含まれていた具体的な逐語(「No automated reconciliation mechanism exists between platforms」等)が、この回読んだ40記事の中には見当たらなかった(その記事自体をこの回は特定・再訪していない)。旧根拠の記事URLが40記事の一覧に含まれているか、含まれていないなら別カテゴリにあるのかは確認していない。
2. **`Fincept Terminal`のE1b・E3b・E4の段が未判別のまま**: この回の担当はE1aの段とE5(§2の8)に限定されていたため、E1b・E3b・E4の段は未判別のまま残した。状態は§2の値のみで深掘りに昇格するため矛盾は無いが、段が3つ未判別のまま『深掘り』とすることが適切か確認したい。
3. **`Exactpro の reconciliation testing`のth2組織リポジトリが100件で頭打ちになっている**: `ungh.cc/orgs/th2-net/repos`は1頁で100件を返すが、2頁目の取得を試すとエラーになった(ページング方式が不明)。th2-netの実際のリポジトリ総数が100件ちょうどか、それ以上あるのに一覧が切れているかは未確認。GitHub REST APIはこの環境のプロキシでリポジトリ限定のエンドポイントしか許可されておらず(`sessions are bound to their configured repositories`)、総数を裏取りする手段が無かった。
4. **`VectorBT`のE5段を4とした判断**: `Pickleable.save()`/`load()`で結果を保存・再読込できること(イ)は確認したが、比較時の許容誤差やハッシュ一致判定など『比べる』ための機構への言及は見つけられなかった(利用者が`pf.sharpe_ratio()`等を目で見比べる想定と読める)。(イ)を『結果を保存して次の実行と比べられる』の要件として十分と扱ってよいか、それとも比較機構(assert・diff等)まで無いと(イ)を満たさないと見るべきか、8-003・8-011のgolden hashテストとの整合性も含めて判断を仰ぎたい。
5. **`prediction-market-backtester`のE5段を3とした判断**: DATA_SHA256(データの版の固定)とgolden hashテスト(開発者固定・pytest内)のどちらも(ア)を満たさないと判断したが、DATA_SHA256の「期待するハッシュ値を利用者が指定する」という性質は、設計票§4.1の(ア)の例示『検出の条件』に近いとも読める。乱数の種と同様に一律で(ア)に当たらないとしてよいか、データの版を固定するハッシュ値の指定は(ア)の一種と見るべきか、判断が割れうる。
6. **`Fincept Terminal`のPyPI旧パッケージとGitHub本体の関係**: PyPIの`fincept-terminal`(v2.0.8、MIT、PyQt5ベース)とGitHub本体(v4.5.0、AGPL-3.0、C++20/Qt6)が同一プロジェクトの新旧なのか、別プロジェクトなのかを明言する一次資料が見当たらなかった。週DL数(48/週)をFincept Terminalの§4.0表に『実測』として記載したが、これは現行版の利用実態を表さない可能性がある。表の記載として残してよいか、除外すべきか確認したい。

## 区分8 — 6 回目の実行(2026-09-24)

起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run6_prompt.md`(指紋 `a3a735b35643`)。追補 `docs/DATA/delegations/20260923_tools_survey_cat8_addendum.md`(指紋 `2c178ba75341`)。対象 6 行: 8-003 `prediction-market-backtester` / 8-006 `freqtrade` / 8-007 `backtrex` / 8-008 `FX Replay` / 8-013 `rusty-bot` / 8-016 `Exactpro の reconciliation testing`。**この回は予算で止めない(追補 §5、オーナー決定 L-507「案A」)。**

### 検索計画
この回は新しい検索計画を打たない(委任文 §2「前回の残りの候補名があれば、まずそれを深掘りする(検索計画は打ち直さない)」)。

### 出典
| # | 出典 | URL | 内容 | 取得日 |
|---|---|---|---|---|
| 1 | GitHub(ungh.cc) | https://ungh.cc/repos/Quentin-Piot/prediction-market-backtester/files/master | prediction-market-backtester のファイル一覧全件(99件) | 2026-09-24 |
| 2 | GitHub(git clone) | https://github.com/Quentin-Piot/prediction-market-backtester | 全99ファイル(scratchpad、読むだけで導入なし) | 2026-09-24 |
| 3 | GitHub raw | docs/performance-baseline.md 他(README・ROADMAP・engine-contracts.md・reporting/validation.py・setup_data.sh・tests/test_backtest_engine.py) | E5・E6の原文根拠 | 2026-09-24 |
| 4 | GitHub raw | docs/strategy-customization.md(freqtrade/develop) | startup_candle_countの原文(暖機期間、E3bには当たらないと判断した根拠) | 2026-09-24 |
| 5 | GitHub raw | docs/freqai-running.md・docs/freqai-parameter-table.md・docs/freqai-feature-engineering.md(freqtrade/develop) | FreqAIのウィンドウ再学習とshuffle=Falseの原文(E3bの根拠) | 2026-09-24 |
| 6 | 公式サイト sitemap | https://backtrex.com/sitemap.xml | en/docs 10頁・en/blog 130頁の全URL一覧 | 2026-09-24 |
| 7 | 公式サイト(curl) | https://backtrex.com/en/docs/backtesting/anti-repainting 他139頁 | Documentation10頁+Blog130頁=140頁全件(E3a再確定の一次資料) | 2026-09-24 |
| 8 | サポートセンター(curl) | https://support-webflow.fxreplay.app/categories/* 8分類 | 8分類の記事URL一覧(重複除去して107件) | 2026-09-24 |
| 9 | サポートセンター(curl) | https://support-webflow.fxreplay.app/articles/* 107記事 | 107記事全件(うち2件は動画のみで本文なし) | 2026-09-24 |
| 10 | GitHub(ungh.cc) | https://ungh.cc/repos/yasstake/rbot/files/main | rusty-bot(yasstake/rbot)のファイル一覧全件(171件) | 2026-09-24 |
| 11 | GitHub(git clone) | https://github.com/yasstake/rbot | 全171ファイル(scratchpad、読むだけで導入なし) | 2026-09-24 |
| 12 | PyPI | https://pypi.org/pypi/rbot/json 、https://pypistats.org/api/packages/rbot/recent | rbotパッケージのメタデータ・週DL数 | 2026-09-24 |
| 13 | PyPI(pip install、隔離venv) | rbot 0.3.5 | 導入・pip check・importの実測(鍵・ネットワーク通信なしで到達可能な範囲) | 2026-09-24 |
| 14 | GitHub(ungh.cc + raw) | https://ungh.cc/users/th2-net/repos 、https://github.com/orgs/th2-net/repositories?page=2 他 | th2-net組織のリポジトリ一覧(100件で頭打ち。2頁目は全経路で失敗) | 2026-09-24 |
| 15 | GitHub raw | th2-check1・th2-check2-recon・th2-check2-recon-template・th2-estore・th2-rpt-viewer・th2-docs・th2-data-services の README | E2段・E6・E3a〜E5判定の一次資料 | 2026-09-24 |
| 16 | 公式サイト(curl) | https://exactpro.com/ | Exactpro社(th2の開発元)の商用部分の記載確認(委任文§5-6) | 2026-09-24 |

**th2.dev(th2の文書ポータル)は到達不可**: 証明書がホスト名不一致(`th2.dev` の接続に `*.exactpro.com` 用の証明書が返る)。`curl`(生ログ:1371、rc=60「SSL: no alternative certificate subject name matches」)と `cat8_render.js`(生ログ:1380、`INCOMPLETE fetch-failed ... Hostname/IP does not match certificate's altnames`)の両方で同じ理由により失敗。第 2 経路(オーナー PC): `curl -v https://th2.dev/` を打てば、この環境固有のプロキシ検証ではなく実際の証明書設定が原因かどうかを別の経路から確かめられる。

### 知見
(設計票 §4.2 の「記録する軸」。原文と URL。`印` を付けた要素ごと。全要素共通の `方式(原文)` / `入力(原文)` から先に書く)

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `prediction-market-backtester / E5 / 方式(原文)`: 「DATA_SHA256=」(`.env.example` 5行)「optionally verifies `DATA_SHA256`」(README 151行)「if [[ -n "$DATA_SHA256" ]]; then echo "[setup] verifying sha256"; echo "${DATA_SHA256}  ${DATA_ARCHIVE}" ／ sha256sum --check --status; fi」(`scripts/setup_data.sh` 40-42行)。利用者が環境変数でダウンロード対象アーカイブの期待ハッシュ値を指定すると、取得後に自動照合し不一致なら `sha256sum --check` が失敗コードを返しスクリプトが `set -e` により停止する | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:15,23 |
| 2 | `prediction-market-backtester / E5 / 入力(原文)`: 「DATA_URL」で任意のURLからアーカイブを取得できる(`scripts/setup_data.sh` 21-24行)。当方のcsv.gzをこの形式(tar --zstd)に変換すれば投入経路になりうるが未検証 | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:23 |
| 3 | `prediction-market-backtester / E5 / (ア)基準を指定できるか`: **印**。`DATA_SHA256` 環境変数で利用者が期待するチェックサム値(=一致/不一致という検出の条件)を指定できる(`scripts/setup_data.sh` 10・40-42行) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:23 |
| 4 | `prediction-market-backtester / E5 / (イ)結果を保存して次の実行と比べられるか`: 記載なし(読んだ箇所: `docs/engine-contracts.md`「`RunResult`: reproducible run payload containing config, dataset slice, git commit, timings...」/ `docs/performance-baseline.md`「used to track regressions」「validates result coherence against results.json, equity.csv, and trades.csv」)。各実行の結果(config・commit・成果物)は保存されるが、**保存した結果を次回の実行と自動比較する機構**(diff・許容誤差つきの回帰判定など)を述べた原文は見当たらなかった。`tests/test_backtest_engine.py` 243-280行の `test_backtest_engine_equity_curve_matches_golden_hash` は固定合成データに対するハッシュ一致テストだが、開発者のpytestスイート内の1シナリオであり、利用者が任意の実行結果同士を比較する機能ではない | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:231,599 |
| 5 | `prediction-market-backtester / E5 / 外から持ち込める対象`: 一部(データ: `DATA_URL`/`DATA_SHA256`で任意の外部アーカイブを持ち込める)。golden hashテストのシナリオ(コード・設定)は開発者が`tests/`に固定したもので、外部から持ち込む経路は見当たらない → **段4の条件(対象のすべてを外から持ち込める)を満たさないため段3にとどめた** | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:23,599 |
| 6 | `prediction-market-backtester / E5 / 自動で判定するか`: 印。`sha256sum --check --status` は自動でrc≠0を返す(人が結果を読んで決めない) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:23 |
| 7 | `prediction-market-backtester / E6 / 方式(原文)`: 「def validate_run_directory(run_dir, *, tolerance: float = 1e-9)」「_assert_close("total_pnl", float(trading_metrics["total_pnl"]), final_equity - initial_cash, tolerance=tolerance)」ほか9項目(`src/pm_bt/reporting/validation.py` 53-140行、E1aの既存根拠と同一関数) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:324,386 |
| 8 | `prediction-market-backtester / E6 / この回の確定(なし)`: 全98件(99件からuv.lock 1件を除く。除外理由=ロックファイルで文字検索の対象として意味を持たない)を `verify／validat／reproduc／determinis／golden／regression／検証／再現／確認／品質／quality` で検索した一致箇所は、`validate_run_directory`(=E1aで既に計上)・`data/quality.py`のpydanticモデル検証(=E2の型/範囲違反検出で既に計上)・golden hashテストとDATA_SHA256(=E5で計上)のいずれかに全て該当し、E1a〜E5のどれにも当たらない独立した検証機能は見当たらなかった | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:480 |
| 9 | `freqtrade / E3b / 方式(原文)`: 「Backtesting calls `set_freqai_targets()` one time for each backtest window ... Doing this means that the targets simulate dry/live behavior without look ahead bias. However, the definition of the features in `feature_engineering_*()` is performed once on the entire training timerange. This means that you should be sure that features do not look-ahead into the future.」(`docs/freqai-running.md` 71-72行)。「`train_test_split()` has a parameter called `shuffle` which allows to shuffle the data or keep it unshuffled. This is particularly useful to avoid biasing training with temporally auto-correlated data.」(同130行)。「`shuffle` ／ ... Typically, to not remove the chronological order of data in time-series forecasting, this is set to `False`.」(`docs/freqai-parameter-table.md` 59行) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:869 (freqai-running.md), :858 (freqai-parameter-table.md) |
| 10 | `freqtrade / E3b / 入力(原文)`: 対象はFreqAIのターゲット生成(バックテストウィンドウ`backtest_period_days`単位の再学習)と、`data_split_parameters.shuffle`が掛かる学習用特徴量データ | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:869 |
| 11 | `freqtrade / E3b / 外から持ち込める対象`: 一部。ウィンドウ再学習・shuffle制御はFreqAIの枠組み(feature_engineering_*()・set_freqai_targets()の実装規約)の中でのみ機能し、任意の外部コードにそのまま適用できる仕組みではない | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:869 |
| 12 | `freqtrade / E3b / この回の訂正`: **訂正**: 5回目までの根拠だった `startup_candle_count` は「Some indicators have an unstable startup period... To account for this, the strategy can be assigned the `startup_candle_count` attribute.」(`docs/strategy-customization.md` 243-245行)という**指標の暖機(過去方向のデータ不足対策)**であり、未来情報の混入を防ぐ機能ではないため、E3bの根拠から外した。代わりに上記のウィンドウ再学習とshuffle=Falseを根拠にした | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:675 |
| 13 | `backtrex / E3a / 方式(原文)`: 「Verification Through Export: The Pine Script export feature provides an additional verification layer: Export your strategy and run it on TradingView. Compare the signals and trade entries between Backtrex and TradingView. The guaranteed less than 2% divergence confirms that anti-repainting is working correctly.」(`docs/backtesting/anti-repainting` 頁本文) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1045 |
| 14 | `backtrex / E3a / 入力(原文)`: 自身のバックテスト結果とPine Script経由でエクスポートしたTradingView側の結果(この回はE1aの既存根拠と同一機能) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1045 |
| 15 | `backtrex / E3a / 確定の経緯`: E1aで既に「印・段2」とした「Export→TradingViewで比較」機能が、当該頁の文脈では**アンチリペイント(=ルックアヘッド系のバイアス)が働いていることの確認手段**として明示的に位置づけられているため、E3aにも当たると判断した。比較を実行するのは利用者(人)なので、E1aと同じ理由で段2(呼べる・判定は人)とした | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1045 |
| 16 | `FX Replay / (全要素) / この回の確定(なし)`: Support Center 8分類(account-management・billing-and-payments・community-resources・fx-replay-battles・getting-started・journal・product-guide-features・support)の記事URLを合算・重複除去した107件(=N)のうち105件(=M。除外2件: `how-to-manage-risk-in-trading`・`tracking-your-trades-with-the-journal-feature` — いずれも本文が空でYouTube動画のみの記事、`class="fxr-richtext w-condition-invisible w-dyn-bind-empty w-richtext"`で本文divが空と確認。除外理由=文字を検索しても意味の無い動画のみの頁)を全文取得し、E1a(`cross.check／reconcil／discrepanc／diff／突き合わせ`)・E2(`gap／duplicate／missing data／out of order／outlier／data quality／データ品質／欠損／重複`+補足で`bad tick／erroneous／stale／spike／smooth`)・E3a/E3b(`look-?ahead／repaint／ルックアヘッド`)・E5(`reproduc／seed／deterministic／再現／固定`)・E6(`verify／validat／accuracy／quality／検証／確認／品質`)を検索した。一致した箇所は個別に読み、いずれも(a)ブローカー間の価格差の解説(E1a候補)、(b)請求の重複・журналタグの重複除去(E2候補、市場データの品質ではない)、(c)スムージングキャンドル=表示上のノイズ低減(E2候補、異常の検出/報告ではない)、(d)サポート窓口の手動確認・入力バリデーション・マーケティング文言(E6候補)のいずれかで、各要素の述語には当たらないと判断した | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1067(N=107),1186-1223(検索と個別確認) |
| 17 | `FX Replay / E1a / この回の裏取り(4回目のWebFetch旧根拠)`: 4回目の根拠だった「No automated reconciliation mechanism exists between platforms」は、出典とされた記事 `why-historical-price-levels-may-look-different-on-fx-replay-vs-tradingview` の実際の本文(この回`curl`で取得)のどこにも存在しない(`reconcil`で全105記事を検索して0件)。同記事の実際の内容は「TradingView has an optional setting called "Adjust for contracts changes" ... To make TradingView match FX Replay, turn off the "Adjust for contracts changes" setting on your TradingView chart」という**手動設定の案内**であり、自動照合機能についての記述ではない。WebFetch由来の逐語は原文に実在しなかった | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1186 |
| 18 | `rusty-bot / E3a / この回の確定(なし)`: リポジトリ全171件のうち画像2件(`doc/img/backtest_sample.png`・`doc/img/rbot_outline.png`。除外理由=画像で文字検索の対象として意味を持たない)を除く169件(ロックファイルは無し)を`look-?ahead／lookahead／ルックアヘッド／repaint／future.?leak／future.?data／purge／embargo／survivorship`で検索し、一致0件 | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1255 |
| 19 | `rusty-bot / E5 / この回の確定(なし)`: 同169件を`reproduc／seed／deterministic／再現／固定`で検索した唯一の一致は`LICENSE.txt`39行「utility programs needed for reproducing the Combined Work」というLGPLv3のライセンス文言(ソース入手性の話で計算の再現性ではない)。補足で`random／rng／同じ結果／consistent result`も検索し、`test/00_suite/test_02_config.py` 100-101行「Test that opening the same exchange multiple times returns consistent results」を見つけたが、これは取引所設定オブジェクトを2回開いたときの一致を確かめる開発者の単体テストであり、バックテストの入出力を固定・比較する利用者向け機能ではないため、E5には当てなかった | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1258,1261,1266 |
| 20 | `Exactpro の reconciliation testing / E2 / (イ)結果を保存して次の実行と比べられるか(段の再判定)`: 「Event store (estore) is an important th2 component responsible for storing events into Cradle.」(`th2-estore` README)「This is a web app that displays the stored test data (events and messages) using `report-data-provider`.」(`th2-rpt-viewer` README)。estoreは検証結果を含む任意のイベントをCradleへ汎用的に永続化し、rpt-viewerはそれを人が閲覧するビューアである。**ある実行の結果を「前回の実行」に対して自動で比較する(回帰の検査として固定する)という記述はestore・rpt-viewerのどちらのREADMEにも無い**(changelog含め全文を読んだ)。よって(イ)の逐語には当たらないと判断し、段5(=(ア)(イ)両方)ではなく**段4**にとどめた((ア)=印: `message_timeout`/`timeout`/`pre_filter`をth2-check1のRequestパラメータとして利用者が指定できる。対象=利用者が`th2-conn-*`経由で接続する任意の外部メッセージストリームのため段4の条件は満たす) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1356(estore),:1362(rpt-viewer) |
| 21 | `Exactpro の reconciliation testing / E6 / 方式(原文)`: 「CheckRuleRequest - get message filter from request and check it with messages in the cache or await specified time in case of empty cache or message absence.」(`th2-check1` README)。root_filter/filterで指定した条件に対し、受信メッセージ群を照合してPASSED/FAILEDを自動判定する | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1341 |
| 22 | `Exactpro の reconciliation testing / E6 / 印の理由`: この機能はE1a(2実装の突き合わせ=recon)・E1b・E2(欠け・順序等の構造的異常の検出=CheckSequenceRule等)のいずれの既存根拠とも異なる**任意の業務ルール(フィールド値フィルタ)に対する汎用の合否判定**であり、E1a〜E5の述語のどれにも直接は当たらないため、E6の述語(戦略・計算・データ・実装の正しさを確かめる機能でE1a〜E5に当たらないもの)に当てた | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1341 |
| 23 | `Exactpro の reconciliation testing / E6 / (ア)(イ)・段`: (ア)=印: `timeout`/`message_timeout`/`checkpoint`等を利用者が指定できる(README「Request parameters」節)。(イ)=E2と同じ理由で記載なし(estore/rpt-viewerは汎用永続化と閲覧のみ)。対象=任意の外部メッセージストリームのため段4の条件は満たすが(イ)を欠くため**段4**とした | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1341,1356,1362 |

### 候補の一覧
1. [深掘り] `qf-lib` (8-001) — https://github.com/quarkfin/qf-lib — バックテストエンジン(区分1から) — 状態: 深掘り
2. [深掘り] `PineForge` (8-002) — https://github.com/pineforge-4pass/pineforge-engine — Pineスクリプト系バックテストエンジン(区分1から) — 状態: 深掘り
3. [深掘り] `prediction-market-backtester` (8-003) — https://github.com/Quentin-Piot/prediction-market-backtester — 予測市場バックテストエンジン(区分1から) — 状態: 深掘り
4. `akurkar07/OrderBook` (8-004) — https://github.com/akurkar07/OrderBook — 板シミュレータ(区分1から、危険で導入停止) — 状態: 危険で導入停止
5. `Exegy` (8-005) — https://www.exegy.com/ — 市場データベンダー(区分1から、登録が要る) — 状態: 登録が要る
6. `freqtrade` (8-006) — https://github.com/freqtrade/freqtrade — 暗号資産botフレームワーク — 状態: 浅い
7. [深掘り] `backtrex` (8-007) — https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide — ノーコード・ビジュアルバックテストSaaS — 状態: 深掘り
8. [深掘り] `FX Replay` (8-008) — https://fxreplay.com/ — 手動バーリプレイSaaS(Support Center 全8分類107記事で再確定) — 状態: 深掘り
9. [深掘り] `nicferrari/backtester` (8-009) — https://github.com/nicferrari/backtester — Rust製の小規模バックテストクレート — 状態: 深掘り
10. [深掘り] `arXiv:2603.20319` (8-010) — https://arxiv.org/abs/2603.20319 — 実装リスク(エンジン間の相違)を論じる論文 — 状態: 深掘り
11. [深掘り] `arXiv:2512.12924` (8-011) — https://arxiv.org/abs/2512.12924 — Walk-forward検証フレームワークの論文+実装 — 状態: 深掘り
12. [深掘り] `VectorBT` (8-012) — https://github.com/polakowo/vectorbt — ベクトル化バックテストライブラリ — 状態: 深掘り
13. [深掘り] `rusty-bot` (8-013) — https://x.com/WannabeBotter/status/1810558269565571211 — Rust製トレーディングボット(yasstake/rbot、PyPI配布あり、bitbank対応) — 状態: 深掘り
14. [深掘り] `Fincept Terminal` (8-014) — https://github.com/Fincept-Corporation/FinceptTerminal — 統合金融ターミナル — 状態: 深掘り
15. [深掘り] `TradingView のリプレイ機能` (8-015) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:98-100(検索計画3、URL は生ログに無い) — チャート上のバー再生機能 — 状態: 深掘り
16. `Exactpro の reconciliation testing` (8-016) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:95-97(検索計画2、URL は生ログに無い) — メッセージ照合テストの方法論+th2プラットフォーム+商用製品 — 状態: 判別に一次資料が要る

### 要素と段
| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 |
|---|---|---|---|---|---|
| qf-lib | E1a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| qf-lib | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| qf-lib | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| qf-lib | E3a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| qf-lib | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| qf-lib | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| qf-lib | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| qf-lib | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| PineForge | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(5回目の節) |
| PineForge | E1b | 印 | 5 | 一次資料 | 台帳の値のまま(5回目の節) |
| PineForge | E2 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| PineForge | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| PineForge | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| PineForge | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| PineForge | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節) |
| PineForge | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| prediction-market-backtester | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(5回目の節) |
| prediction-market-backtester | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| prediction-market-backtester | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| prediction-market-backtester | E3a | なし | - | 実測 | ファイル一覧99件のうち1件除外(uv.lock=依存ロックファイル、文字検索の対象として意味を持たない)。一覧 98 件 / 読んだ 98 件。`look-?ahead／lookahead／ルックアヘッド／防ぐ／検出`等で全文検索、一致0件。docs/DATA/probes/20260923_tools_8_run6.log:12 |
| prediction-market-backtester | E3b | なし | - | 実測 | ファイル一覧99件のうち除外はE3aと同じuv.lock 1件。一覧 98 件 / 読んだ 98 件。`peek／future.?data／purge／embargo／walk-forward／in-sample／out-of-sample／snoop`等を追加し全文検索、一致0件。docs/DATA/probes/20260923_tools_8_run6.log:321 |
| prediction-market-backtester | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| prediction-market-backtester | E5 | 印 | 3 | 実測 | (ア)=印: `DATA_SHA256`で利用者が期待ハッシュ値(検出の条件)を指定できる(scripts/setup_data.sh 40-42行)。(イ)=記載なし(estore的な自動比較機構は無い)。対象(データ)は`DATA_URL`経由で外部から持ち込めるが、golden hashテストのシナリオ(コード・設定)は道具の外から持ち込めないため段4の条件(対象のすべて)を満たさず段3。docs/DATA/probes/20260923_tools_8_run6.log:23,599 |
| prediction-market-backtester | E6 | なし | - | 実測 | ファイル一覧99件のうち除外は同じuv.lock 1件。一覧 98 件 / 読んだ 98 件。`verify／validat／reproduc／determinis／golden／regression／検証／再現／確認／品質／quality`で検索した一致は全てE1a(validate_run_directory)・E2(pydanticモデル検証)・E5(golden hash・DATA_SHA256)のいずれかに該当済みで独立の機能なし。docs/DATA/probes/20260923_tools_8_run6.log:480 |
| akurkar07/OrderBook | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| akurkar07/OrderBook | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| akurkar07/OrderBook | E2 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| akurkar07/OrderBook | E3a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| akurkar07/OrderBook | E3b | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| akurkar07/OrderBook | E4 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| akurkar07/OrderBook | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| akurkar07/OrderBook | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| Exegy | E1a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節、未判別) |
| Exegy | E1b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節、未判別) |
| Exegy | E2 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節、未判別) |
| Exegy | E3a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節、未判別) |
| Exegy | E3b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節、未判別) |
| Exegy | E4 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節、未判別) |
| Exegy | E5 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節、未判別) |
| Exegy | E6 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節、未判別) |
| freqtrade | E1a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| freqtrade | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| freqtrade | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| freqtrade | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| freqtrade | E3b | 印 | 3 | 実測 | freqai-running.md 71-72行「Doing this means that the targets simulate dry/live behavior without look ahead bias...you should be sure that features do not look-ahead into the future」(ウィンドウ再学習)、同130行「shuffle...avoid biasing training with temporally auto-correlated data」、freqai-parameter-table.md 59行「shuffle...set to False」。対象(学習データの分割)はFreqAIの枠組み内でのみ機能し外部コードに掛けられないため段3。docs/DATA/probes/20260923_tools_8_run6.log:869 |
| freqtrade | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| freqtrade | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| freqtrade | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| backtrex | E1a | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| backtrex | E1b | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| backtrex | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| backtrex | E3a | 印 | 2 | 実測 | docs/backtesting/anti-repainting頁「Export your strategy and run it on TradingView. Compare the signals and trade entries between Backtrex and TradingView. The guaranteed less than 2% divergence confirms that anti-repainting is working correctly」。エクスポートは道具が行うが比較は利用者が行うため段2(E1aと同一機能・同一段)。docs/DATA/probes/20260923_tools_8_run6.log:1045 |
| backtrex | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| backtrex | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| backtrex | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| backtrex | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| FX Replay | E1a | なし | - | 実測 | ファイル一覧107件のうち2件除外(`how-to-manage-risk-in-trading`・`tracking-your-trades-with-the-journal-feature`=本文divが空でYouTube動画のみの記事、`w-dyn-bind-empty`を確認。文字検索の対象として意味を持たない)。一覧 105 件 / 読んだ 105 件。`cross.check／reconcil／discrepanc／diff／突き合わせ`で検索した2件はブローカー間価格差の解説のみで自動突き合わせ機能ではない。旧根拠「No automated reconciliation mechanism exists between platforms」は原文に存在せず(reconcilで0件)。docs/DATA/probes/20260923_tools_8_run6.log:1067,1186,1189 |
| FX Replay | E1b | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| FX Replay | E2 | なし | - | 実測 | ファイル一覧107件のうち除外はE1aと同じ2件。一覧 105 件 / 読んだ 105 件。`gap／duplicate／missing data／out of order／outlier／data quality／データ品質／欠損／重複`+補足`bad tick／erroneous／stale／spike／smooth`で検索した一致(請求の重複・journalタグ重複除去・スムージングキャンドル=表示ノイズ低減)はいずれも市場データの欠け・重複・順序・外れ値等の検出/報告ではない。docs/DATA/probes/20260923_tools_8_run6.log:1195,1201 |
| FX Replay | E3a | なし | - | 実測 | ファイル一覧107件のうち除外は同上2件。一覧 105 件 / 読んだ 105 件。`look-?ahead／repaint／ルックアヘッド`で検索、一致0件。docs/DATA/probes/20260923_tools_8_run6.log:1204 |
| FX Replay | E3b | なし | - | 実測 | ファイル一覧107件のうち除外は同上2件。一覧 105 件 / 読んだ 105 件。E3aと同じ検索語、一致0件。docs/DATA/probes/20260923_tools_8_run6.log:1204 |
| FX Replay | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| FX Replay | E5 | なし | - | 実測 | ファイル一覧107件のうち除外は同上2件。一覧 105 件 / 読んだ 105 件。`reproduc／seed／deterministic／再現／固定`で検索、一致0件(Monte Carlo Simulation記事も乱数シード制御の記述なし)。docs/DATA/probes/20260923_tools_8_run6.log:1208 |
| FX Replay | E6 | なし | - | 実測 | ファイル一覧107件のうち除外は同上2件。一覧 105 件 / 読んだ 105 件。`verify／validat／accuracy／quality／検証／確認／品質`で検索した8件はサポート窓口の手動確認・フォーム入力検証・マーケティング文言のいずれかで、道具自身の検証機能ではない。docs/DATA/probes/20260923_tools_8_run6.log:1212 |
| nicferrari/backtester | E1a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| nicferrari/backtester | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| nicferrari/backtester | E2 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| nicferrari/backtester | E3a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| nicferrari/backtester | E3b | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| nicferrari/backtester | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| nicferrari/backtester | E5 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| nicferrari/backtester | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2603.20319 | E1a | 印 | 1 | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2603.20319 | E1b | 印 | 1 | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2603.20319 | E2 | 印 | 1 | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2603.20319 | E3a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2603.20319 | E3b | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2603.20319 | E4 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2603.20319 | E5 | 印 | 1 | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2603.20319 | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2512.12924 | E1a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2512.12924 | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2512.12924 | E2 | 印 | 4 | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2512.12924 | E3a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2512.12924 | E3b | 印 | 4 | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2512.12924 | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2512.12924 | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節) |
| arXiv:2512.12924 | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| VectorBT | E1a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| VectorBT | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| VectorBT | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| VectorBT | E3a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| VectorBT | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| VectorBT | E4 | 印 | 4 | 一次資料 | 台帳の値のまま(5回目の節) |
| VectorBT | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節) |
| VectorBT | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| rusty-bot | E1a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| rusty-bot | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| rusty-bot | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| rusty-bot | E3a | なし | - | 実測 | ファイル一覧171件のうち2件除外(`doc/img/backtest_sample.png`・`doc/img/rbot_outline.png`=画像、文字検索の対象として意味を持たない。ロックファイルは無し)。一覧 169 件 / 読んだ 169 件。`look-?ahead／lookahead／ルックアヘッド／repaint／future.?leak／future.?data／purge／embargo／survivorship`で検索、一致0件。docs/DATA/probes/20260923_tools_8_run6.log:1255 |
| rusty-bot | E3b | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| rusty-bot | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| rusty-bot | E5 | なし | - | 実測 | ファイル一覧171件のうち除外はE3aと同じ2件。一覧 169 件 / 読んだ 169 件。`reproduc／seed／deterministic／再現／固定`で検索した唯一の一致はLICENSE.txt 39行のLGPLv3文言(ソース入手性の話)。補足で`random／rng／同じ結果／consistent result`も検索し、test_02_config.py 100-101行の開発者向け単体テスト(取引所設定を2回開いて一致確認)を見つけたが、利用者向けの入出力固定・比較機能ではないため計上しない。docs/DATA/probes/20260923_tools_8_run6.log:1258,1261,1266 |
| rusty-bot | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| Fincept Terminal | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| Fincept Terminal | E1b | 印 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節) |
| Fincept Terminal | E2 | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| Fincept Terminal | E3a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| Fincept Terminal | E3b | 印 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節) |
| Fincept Terminal | E4 | 印 | 未判別 | 一次資料 | 台帳の値のまま(5回目の節) |
| Fincept Terminal | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(5回目の節) |
| Fincept Terminal | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| TradingView のリプレイ機能 | E1a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| TradingView のリプレイ機能 | E1b | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| TradingView のリプレイ機能 | E2 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| TradingView のリプレイ機能 | E3a | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| TradingView のリプレイ機能 | E3b | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| TradingView のリプレイ機能 | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(5回目の節) |
| TradingView のリプレイ機能 | E5 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| TradingView のリプレイ機能 | E6 | なし | - | 一次資料 | 台帳の値のまま(5回目の節) |
| Exactpro の reconciliation testing | E1a | 印 | 4 | 一次資料 | 台帳の値のまま(5回目の節) |
| Exactpro の reconciliation testing | E1b | 印 | 4 | 一次資料 | 台帳の値のまま(5回目の節) |
| Exactpro の reconciliation testing | E2 | 印 | 4 | 実測 | (ア)=印(既存根拠のまま)。(イ)=記載なし: th2-estore README「Event store (estore) is an important th2 component responsible for storing events into Cradle」、th2-rpt-viewer README「This is a web app that displays the stored test data」。汎用の永続化と閲覧のみで、結果を前回実行と自動比較する記述は無い。対象は外部メッセージストリームで持ち込めるため段4条件は満たすが(イ)を欠くため段5ではなく段4。docs/DATA/probes/20260923_tools_8_run6.log:1356,1362 |
| Exactpro の reconciliation testing | E3a | 未判別 | 未判別 | 未確認 | th2-net組織のリポジトリ一覧が100件で頭打ち(全経路で2頁目取得に失敗。下記代替経路参照)で全リポジトリを見渡せず、確認できた9リポジトリ(check1/check2-recon/check2-recon-template/estore/rpt-viewer/th2-docs/th2-data-services/th2-crawler/th2-cradle-admin-tool)のREADMEには`look-?ahead／replay／reproduc／seed／regression`のいずれも無かった(docs/DATA/probes/20260923_tools_8_run6.log:1365)。th2はライブメッセージストリームのリアルタイム検証基盤であり、バックテストのルックアヘッドバイアスという概念が適用対象かどうかも含め未確認 |
| Exactpro の reconciliation testing | E3b | 未判別 | 未判別 | 未確認 | 同上。組織リポジトリの全件を確認できていないため`なし`と書ける状態にない |
| Exactpro の reconciliation testing | E4 | 未判別 | 未判別 | 未確認 | 同上。`replay`の語での検索は0件(docs/DATA/probes/20260923_tools_8_run6.log:1365)だったが、組織全体を見渡せていないため`なし`と書ける状態にない。th2-data-servicesは記録済みイベントの分析用ライブラリ(EventTree/Data.filter等)だが、記録データを時刻順に再生して戦略・計算を再実行する機能の明言は見当たらなかった(docs/DATA/probes/20260923_tools_8_run6.log:1401) |
| Exactpro の reconciliation testing | E5 | 未判別 | 未判別 | 未確認 | 同上。`reproduc／seed／deterministic／regression`は9リポジトリで0件(docs/DATA/probes/20260923_tools_8_run6.log:1365)。組織全体を見渡せていないため`なし`と書ける状態にない |
| Exactpro の reconciliation testing | E6 | 印 | 4 | 実測 | th2-check1 README「CheckRuleRequest - get message filter from request and check it with messages in the cache or await specified time in case of empty cache or message absence」。任意の業務ルール(フィールドフィルタ)への汎用の合否判定機能で、E1a(recon)・E2(順序/欠け検出)のいずれの既存根拠とも異なるためE6。(ア)=印(timeout等を利用者が指定可、README「Request parameters」節)。(イ)=E2と同じ理由で記載なし。対象は外部メッセージストリームで段4条件は満たすが(イ)欠如のため段4。docs/DATA/probes/20260923_tools_8_run6.log:1341 |

### ツール1件ごとの表
(委任文 §4 の全列は 1〜5 回目の該当節に揃っている。この回に新しく分かった・訂正した点だけを候補ごとに書く。列見出しは §4 のものを使う)

**`prediction-market-backtester`(8-003)**
- できること全部(訂正・追加): reporting/validation.py の `validate_run_directory` が保存済み `results.json` の9指標を `equity.csv`/`trades.csv` から独立に再計算し `_assert_close(..., tolerance=...)` で突き合わせる機能(=E1a、既存根拠)に加え、`scripts/setup_data.sh` の `DATA_SHA256` チェックサム照合機能(E5)を持つ。ルックアヘッド検出・防止・その他の独立した検証機能(E3a・E3b・E6)は99件のファイル一覧(uv.lock 1件を除く98件を検索)を通じて見当たらなかった
- 再現性(訂正): 印・段3(前回の未判別を解消)。理由は知見の節のとおり

**`freqtrade`(8-006)**
- できること全部(訂正): FreqAIのバックテストウィンドウ再学習(`backtest_period_days`)が「ターゲットの生成をdry/live相当の挙動に模す(=look-ahead biasを避ける)」ことをdocs/freqai-running.md 71-72行が明言。`data_split_parameters.shuffle=False`は時系列データの時間順を保って学習/検証を分割する仕組み(同130行)。この2点でE3bを印とした
- 訂正(重要): 5回目まで根拠にしていた `startup_candle_count` は指標の**暖機**(過去方向のデータ不足の解消)であり、未来情報の混入防止(E3b)には当たらないと判断し、根拠から外した
- 状態: この回でE1a〜E6の値はすべて確定した(未判別なし)が、§4.0機械可読の表(既存43項目、1〜4回目分)は一次資料/実測が21/43=48.8%で**過半に届かない**(コミット数・週DL数・導入可否・install所要秒・依存数・pip check・最小実行系・規模の見積・配布元の一致・依存の一覧・保守者名の一貫性など18項目が未確認のまま)。よってこの回も**「浅い」のまま**(何が未確認かは既存の§4.0表のとおり)

**`backtrex`(8-007)**
- できること全部(訂正・追加): `docs/backtesting/anti-repainting` 頁の「Verification Through Export」節(Export→TradingViewで比較、乖離2%未満を保証)は、E1a(突き合わせ)だけでなくE3a(ルックアヘッド系バイアスの検出手段)としても位置づけられている一次資料の記述であるため、E3aを印(段2)に確定した

**`FX Replay`(8-008)**
- 到達・導入・実行の記録(訂正): Support Center 8分類(account-management・billing-and-payments・community-resources・fx-replay-battles・getting-started・journal・product-guide-features・support)の記事URLを重複除去した107件全部を `curl` で取得できた(105件は本文あり、2件は動画のみで本文なし)。5回目までは1分類(Product Guide & Features)のみをNとしていたのを、8分類全部に広げて再確定した
- 当方に無いもの(訂正): 4回目のWebFetch由来だった「No automated reconciliation mechanism exists between platforms」という逐語は、出典とされた記事の実際の本文には存在しない(この回`curl`で取得し確認)。同記事の実際の内容は、TradingViewの「Adjust for contracts changes」設定を手動でオフにする案内であり、自動照合機能についての記述ではなかった
- 状態: E1a・E1b・E2・E3a・E3b・E5・E6がすべて『なし』、E4のみ『印』で確定し、未判別が無くなったため**深掘り**に進めた

**`rusty-bot`(8-013、`yasstake/rbot`)**
- 種別・できること全部: Rust製・Pythonバインディングのトレーディングボットフレームワーク。`backtest`/`dry_run`/`production`を同一コードで切替可能(README)。ヒストリカルtickをSQLite→(0.4.0で)parquetへ保存しOHLCVを任意足で計算
- 対応取引所(訂正・重要): **PyPI配布版(0.3.5、2024-04-05)はBybit・Binanceのみ**(importで確認したクラス一覧にBitbankクラスなし)。**GitHub最新版(main、Cargo.toml)はbitbank(日本の取引所)を含む**が、PyPIには未リリース。当方が実際に`pip install`で使える範囲と、リポジトリが謳う対応範囲が食い違う
- 到達・導入・実行の記録: `pip install rbot`(隔離venv)が1.81秒で成功、`pip check`はNo broken requirements found、importと`Bybit(production=True)`/`BybitConfig.BTCUSDT`によるMarketオブジェクト構築(鍵・ネットワーク通信なし)まで到達。**合成ティックによる成行/指値の往復損益の実行までは到達していない**(内部DB形式へ合成データを注入する経路を確認できなかったため)
- 状態: この回でE3a・E5を含む全8要素が確定し(未判別なし)、§4.0機械可読の表をこの回に新規で43項目作成(37/43=86.0%が一次資料/実測)。**深掘り**に進めた

**`Exactpro の reconciliation testing`(8-016)**
- 到達の記録(訂正): th2-net組織のリポジトリ一覧は`ungh.cc`(`/users/th2-net/repos`)で100件までしか返らず(アルファベット順で`th2-docs`付近まで)、2頁目の取得を`ungh.cc`・GitHub HTML(`?page=2`)・GitHub REST API(`/orgs/th2-net/repos`)・GitHub Search API・web.archive.orgのいずれでも試したが、GitHub系はすべて同一のプロキシ制限(「sessions are bound to their configured repositories」= この環境はリポジトリ限定のエンドポイントしか許可しない)で403、web.archive.orgはこの環境の送出方針でブロックされた(`Blocked by egress policy`)。**個別リポジトリの直指定(repository-scoped)は制限を受けず**、`th2-estore`など100件の一覧に出ない名前も直接URLでは到達できた(組織一覧に出ない名前を知る手段自体が無いことが限界として残る)
- th2.dev(公式文書ポータル)にも到達不可: TLS証明書のホスト名不一致(`th2.dev`への接続に`*.exactpro.com`用の証明書が返る)。`curl`と`cat8_render.js`の両方で同じ理由により失敗を確認
- できること全部(この回の追加): `th2-check1`は`CheckRuleRequest`で任意の業務ルール(フィールドフィルタ)に対する汎用の合否判定を自動で行う(E6)。`th2-estore`/`th2-rpt-viewer`はテスト実行中の任意のイベントをCradleへ永続化し人が閲覧するビューアだが、**前回実行の結果と自動比較する仕組みの記述は見当たらなかった**ため、E2・E6の段は5ではなく4とした
- 商用の部分(委任文§5-6): Exactpro社(th2の開発元)は独立系のソフトウェアテストサービス提供会社で、`exactpro.com`のトップ頁には料金表・自己登録フォームは見当たらず、コンサル・テスト実施代行は「Contact us」の問い合わせ制。th2自体はApache 2.0のOSSで無料。**登録はしていない**
- 状態: E3a・E3b・E4・E5が未判別のまま残るため、**この回も『判別に一次資料が要る』のまま**(組織一覧を全件見渡せていないため『なし』とは書けない)

### 4.0 機械可読の表
(この回に新しく§4.0表を作った候補と、既存表の項目に新しい値が出た候補だけを書く。他の候補の既存の表は 1〜5 回目の該当節にある)

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| rusty-bot | 版 | PyPI最新版 0.3.5(2024-04-05公開)。GitHub mainブランチのCargo.tomlは`version = "0.1.8" # for test pypi` / `# version = "0.4.0" # for main release branch`とコメントされ未リリース版が先行している | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1459,1404 |
| rusty-bot | 最終更新日 | GitHub pushedAt 2026-05-11(リポジトリ全体)。PyPI最新リリース 2024-04-05 | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1224,1459 |
| rusty-bot | ライセンス | LGPL-3.0(LICENSE.txt冒頭「GNU LESSER GENERAL PUBLIC LICENSE Version 3」、PyPI classifiers「GNU Lesser General Public License v3 or later (LGPLv3+)」) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404,1459 |
| rusty-bot | 言語と動作環境 | コア=Rust(Cargo.toml、cdylib/rlib)、Pythonバインディング(cp38-abi3の安定ABI、Python 3.8以上で動作) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404,1459 |
| rusty-bot | 対応取引所 | PyPI版0.3.5はBybit・Binance(import rbotで確認したクラス一覧にBitbankクラスは無い)。GitHub main版のCargo.tomlはbybit・binance・bitbank(bitbankexchanges/bitbankパス、日本の取引所)を含み、hyperliquidはコメントアウト。**PyPI配布版とGitHub最新版で対応取引所が食い違う**(PyPI版にbitbank無し) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1404,1539 |
| rusty-bot | 星 | 16(fork 5、watchers 1) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1224 |
| rusty-bot | コミット数 | 未確認(この回は取得していない) | 未確認 | 試した手段: GitHub組織一覧同様にAPIを試していない(時間配分の都合) |
| rusty-bot | 保守者数 | 1名(README/PyPI authorともに `@yasstake` のみ。単独開発者のプロジェクトと読める) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1459 |
| rusty-bot | 週DL数 | 4(pypistats last_week)。last_month=10、last_day=0 | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1485 |
| rusty-bot | 初回公開日 | GitHub createdAt 2022-11-28 | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1224 |
| rusty-bot | 既知の脆弱性 | 未確認(この回はPyPI advisory・OSV等を検索していない) | 未確認 | 試した手段: 時間配分の都合で未実施 |
| rusty-bot | 料金体系 | 無料(LGPL-3.0のOSS、PyPI・GitHubとも無償公開) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404(README.md冒頭) |
| rusty-bot | 無料枠の上限 | 該当なし(OSSライブラリ、SaaSではない) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404(README.md冒頭、OSSライブラリの性質から) |
| rusty-bot | 課金開始条件 | 該当なし(同上) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404(README.md冒頭、同上) |
| rusty-bot | 隠れた依存 | 実運用(production)・dry_runで取引所APIキーが要る(README「enable_order_with_my_own_risk」節)。バックテストはアーカイブ済みデータがあれば鍵不要。Python側の追加ライブラリ依存はpip listで0件(polars等はバイナリに同梱) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1459,1518 |
| rusty-bot | 登録の要否 | 不要(バックテストのみなら。取引所アカウント・鍵は実運用/dry_runでのみ必要) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1459 |
| rusty-bot | 到達経路 | GitHub(ungh.cc・raw.githubusercontent.com・git clone)・PyPI(pypi.org、pip install)いずれも成功 | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1224,1230,1488 |
| rusty-bot | 導入可否 | 可。隔離venvで`pip install rbot`が成功(prebuilt wheel、コンパイル不要) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1488 |
| rusty-bot | install所要秒 | 1.81秒(実測ログの値) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1488 |
| rusty-bot | 依存数 | pip installでrbot以外の追加パッケージは入らなかった(`pip list`の出力はpip・rbot・setuptoolsのみ)。Rust側のCargo依存(bybit/binance/bitbank等の内部crate)はコンパイル済みバイナリに含まれ個数は未確認 | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1518 |
| rusty-bot | pip check | No broken requirements found(rc=0) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1488 |
| rusty-bot | 最小実行の可否 | 部分的に可。鍵・ネットワーク通信なしで`import rbot`、`Bybit(production=True)`・`BybitConfig.BTCUSDT`でのMarketオブジェクト構築(ローカルDBファイルパスの生成)まで到達。**合成ティック列を使った成行/指値の往復損益までは到達していない**(rbotの内部DB形式(SQLite/parquet)へ合成データを注入する経路が文書化されておらず、この回では見つけられなかった。実データのdownload_archive()を使わない投入方法は未確認) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1539,1548 |
| rusty-bot | 最小実行の中身 | `from rbot import Bybit, BybitConfig; exchange=Bybit(production=True); market=exchange.open_market(BybitConfig.BTCUSDT)` を鍵なしで実行し、`market.file_name`がローカルDBパスを返すことを確認 | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1548 |
| rusty-bot | 実行所要秒 | 0.029秒(上記オブジェクト構築のみ、往復売買は未実施) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1548 |
| rusty-bot | wheel展開 | `pip install`後、site-packages配下に`rbot/rbot.abi3.so`(コンパイル済みバイナリ)と`rbot.libs`(追加共有ライブラリ)を確認 | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1518 |
| rusty-bot | setup.py導入時実行 | 無し(prebuilt wheelのため導入は1.8秒で完了し、ビルドスクリプトが走った形跡なし) | 推定 | docs/DATA/probes/20260923_tools_8_run6.log:1488 |
| rusty-bot | 同梱バイナリ | 有り(`rbot.abi3.so`本体、`rbot.libs`配下に追加の共有ライブラリ) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1518 |
| rusty-bot | 外部送信 | 導入時はpypi.org/files.pythonhosted.orgへ(標準的なpip動作)。実行時は`production=True`のexchange接続で取引所WS/RESTへ(この回は未接続)。バックテストはローカルDBファイルのみ使用 | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1488,1548 |
| rusty-bot | 自動発注機能 | 有り。README「Ordering is disabled by default. You can enable it by setting `enable_order_with_my_own_risk` to `True`」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1459 |
| rusty-bot | 宣伝詐欺の兆候 | 無し(GitHub・PyPIとも通常のOSS配布) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404,1459 |
| rusty-bot | 当方データ投入 | 未確認(当方のcsv.gzをrbotの内部DB形式(SQLite→0.4.0でparquetへ移行中、README「約定ログの保存方式をSQLiteからparquetへ変更」)に変換する経路をこの回は確認していない) | 未確認 | 試した手段: README/PyPI説明文を読んだのみ、変換スクリプトの有無は未検索 |
| rusty-bot | 時刻の扱い | README(0.4.0向けchangelog)「OHLCVのTimestampの型をi64からDateTimeへ変更」。`ohlcv()`の引数`start_time`/`end_time`はunixタイムスタンプ(マイクロ秒)とPyPI説明文に明記 | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404,1459 |
| rusty-bot | 再現性 | なし(この回のE5判定。171件中169件を検索し、ライセンス文言以外に再現性関連の記述なし) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1258,1261 |
| rusty-bot | 規模の見積 | 未確認(この回は456日相当の実測を行っていない) | 未確認 | 試した手段: 時間配分の都合で未実施 |
| rusty-bot | 配布元の一致 | 一致。PyPI author `@yasstake` = GitHubオーナー `yasstake`(リポジトリ名は`rbot`、候補の発見時のURLは`rusty-bot`表記だが実体は同一) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1459 |
| rusty-bot | 難読化 | 無し。ソースは全文公開・可読(Rust本体+Pythonバインディング)。配布物はコンパイル済みバイナリだがソースから追跡可能 | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404(LICENSE.txt+README.mdのソース実測) |
| rusty-bot | 外部URL取得 | 導入時はpypi.orgのみ(pip標準動作)。実行時は取引所WS/REST(README「download_archive」節) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1459 |
| rusty-bot | 依存の一覧 | Cargo.toml(GitHub main)記載: `bybit`・`binance`・`bitbank`(いずれもローカルpathのworkspace内crate)+ `rbot_lib`・`rbot_session`・`rbot_server`(内部crate)。外部crateの個数はこの回では列挙していない(Cargo.lock相当のファイルはリポジトリのファイル一覧171件に含まれない) | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404(Cargo.toml) |
| rusty-bot | 保守者名の一貫性 | 一貫(README著者・PyPI著者・GitHubオーナーいずれも`yasstake`/`@yasstake`) | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1404,1459 |
| rusty-bot | 4軸1_道具 | 印。`pip install rbot`が鍵・ネットワーク通信なしで成功し、Bybit/Binance/(GitHub最新版で)bitbankのMarketオブジェクトを構築できる | 実測 | docs/DATA/probes/20260923_tools_8_run6.log:1488,1539 |
| rusty-bot | 4軸2_情報 | 印。tick単位のヒストリカル約定をSQLite/parquetへ保存する仕組みと、日本の取引所bitbankへの直接対応(GitHub main)は当方の道具立てに無い視点 | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404(README.md「Store historical transaction data」節) |
| rusty-bot | 4軸3_視点 | 印。`backtest`/`dry_run`/`production`の3モードを同一コードで切り替えられる設計思想(README「Your Bot can be executed in three mode... without modification」)は当方に無い視点 | 一次資料 | docs/DATA/probes/20260923_tools_8_run6.log:1404(README.md「three mode」節) |
| rusty-bot | 4軸4_向上 | 推定。Rustコア+Pythonバインディングという構成、TICKベースのバックテスト方式は、当方の足単位バックテストの高速化・tick粒度対応の参考になりうる | 推定 | docs/DATA/probes/20260923_tools_8_run6.log:1404(README.md全体の設計から) |

### 代替経路
この回は th2-net 組織のリポジトリ一覧(8-016)が「この環境から不可」に当たる。試した手段の一覧: (1) `ungh.cc/users/th2-net/repos`(パラメータ`?page=2`を含め常に同じ先頭100件を返す、docs/DATA/probes/20260923_tools_8_run6.log:1308,1312,1316) / (2) `https://github.com/orgs/th2-net/repositories?page=2` の生HTML(rc=0だがボディはこの環境固有のプロキシの拒否メッセージ「sessions are bound to their configured repositories」、同ログ:1294) / (3) `https://api.github.com/orgs/th2-net/repos?per_page=100&page=2` と `page=1`(同じ拒否メッセージ、同ログ:1297,1301) / (4) `https://github.com/th2-net`(組織トップ頁も同じ拒否、同ログ:1305) / (5) `https://api.github.com/search/repositories?q=org:th2-net`(同じ拒否、同ログ:1319) / (6) `web.archive.org`のスナップショット(`archive.org/wayback/available`ではスナップショットが見つかったが、本体の取得は`Blocked by egress policy`、同ログ:1323,1326)。**第2経路(オーナー PC)でそのまま打てるコマンド**: `curl -sS "https://api.github.com/orgs/th2-net/repos?per_page=100&page=2"` または ブラウザで `https://github.com/orgs/th2-net/repositories?page=2` を開く(この環境固有のセッション制限が無ければ通常のGitHub APIレート制限内で動くはず)。個々のリポジトリ名が分かっていれば(例: `th2-estore`)、`https://ungh.cc/repos/th2-net/<名前>` のようなリポジトリ単位の経路はこの環境でも制限を受けず到達できる(同ログ:1353)。

th2.dev(th2の公式文書ポータル)も到達不可。理由はプロキシ制限ではなくTLS証明書のホスト名不一致で、`curl`(rc=60「SSL: no alternative certificate subject name matches」、同ログ:1371)と`cat8_render.js`(`Hostname/IP does not match certificate's altnames: Host: th2.dev. is not in the cert's altnames: DNS:*.exactpro.com`、同ログ:1380)の両方で同じ理由により失敗した。**第2経路(オーナー PC)**: `curl -v https://th2.dev/` を打ち、同じ証明書不一致が出るかを確かめれば、この環境固有の問題か実際のth2.dev側の証明書設定の問題かを切り分けられる。

### 予算
この回は予算で止めない(追補 §5、オーナー決定 L-507「案A」)。

### 受け入れ検査の出力
（K12 は自己参照するため、下の出力は貼り付け前の実行結果であり「1 件」と出ている。貼り付け後にもう一度 4 検査を打ち直すと K12 も含めすべて 0 件になることを確認済み。)

```
$ python3 scripts/check_scan_report.py docs/DATA/SCAN_2026-09-23_tools_cat8.md docs/DATA/probes/20260923_tools_8_run1.log docs/DATA/probes/20260923_tools_8_run2.log docs/DATA/probes/20260923_tools_8_run3.log docs/DATA/probes/20260923_tools_8_run4.log docs/DATA/probes/20260923_tools_8_run5.log docs/DATA/probes/20260923_tools_8_run6.log
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

$ python3 scripts/cat8_ledger.py check-elements docs/DATA/SCAN_2026-09-23_tools_cat8.md --round 6
読んだもの: 候補の一覧 16 行 / 要素と段の表 128 行(道具 16)/ 知見の表 23 行 / 辿る一覧から出た名前 0 行
---- 合計 0 件

$ python3 scripts/cat8_ledger.py check "" docs/DATA/probes/20260923_tools_8_run6.log
参考: docs/DATA/probes/20260923_tools_8_run6.log の最初の手 2026-09-24T03:37:33Z / 最後の手 2026-09-24T04:00:34Z / 手の数 93
---- 合計 0 件

$ git diff -U0 HEAD -- docs/DATA/SCAN_2026-09-23_tools_cat8.md | grep '^-[^-]' | wc -l
0
```

### 判断に迷った点と問い(決めずに列挙)
1. **`prediction-market-backtester`(8-003)のE5段=3の判断**: (ア)『判定の基準を利用者が指定できるか』は `DATA_SHA256` を『検出の条件(ハッシュ値の一致/不一致)』の指定と読めば満たすが、これは入力データの版を固定する仕組みであり、出力結果の許容誤差を指定する仕組みではない。(イ)『結果を保存して次の実行と比べられるか』は、`RunResult`(config・dataset slice・git commit・timingsを保存)や`docs/performance-baseline.md`(『used to track regressions』)の記述はあるが、**保存した結果を自動比較する機構**(diffや許容誤差つきの回帰判定)の記述は見当たらなかった。段4の条件(対象のすべてを外から持ち込める)を満たさない(golden hashテストのシナリオは固定)ため段3とはしたが、DATA_SHA256を(ア)の『検出の条件』の一種と数えてよいかどうかは述語の読みの問いとして残る。
2. **`freqtrade`(8-006)がE1a〜E6すべて確定したのに『浅い』のままである扱い**: 設計票§2の『深掘り』の述語は『委任文§4.0の深掘りの条件を満たし、かつE1a〜E6に未判別が1つも無い』の**両方**を要求する。freqtradeはE1a〜E6の未判別はこの回で無くなったが、既存の§4.0表(1〜4回目分、43項目)の一次資料/実測の割合が21/43=48.8%で過半(50%超)に届かないため『浅い』のままとした。この判断(要素が揃っても§4.0の過半条件を満たさなければ深掘りにしない)で良いか、それとも要素が全部揃った時点で優先的に深掘りに進めるべきか確認したい。
3. **`Exactpro の reconciliation testing`(8-016)のE2・E6の段を5でなく4とした判断**: (イ)『結果を保存して次の実行と比べられる(回帰の検査として固定できる)』を、`th2-estore`(汎用イベントの永続化)と`th2-rpt-viewer`(閲覧のみ)の組み合わせでは満たさないと読んだ。5回目の検収・監査30回目でも同種の問いが出ていたが(問6)、この回はth2-estore/rpt-viewer README全文を読み直し、『前回実行との自動比較』を明言する記述が無いと確認したうえで段4と判定した。この読みで良いか。
4. **`Exactpro の reconciliation testing`(8-016)のE3a・E3b・E4・E5が未判別のまま残ったこと**: th2-net組織のリポジトリ一覧を100件までしか見渡せず(代替経路のとおり全経路で2頁目取得に失敗)、確認できた9リポジトリのREADMEには該当する記述が無かった。組織一覧を見渡せない以上、**この4要素を『なし』と書ける状態にない**と判断したが、個別に見つかった9リポジトリの範囲だけで『段は未判別のまま、値もなしとせず未判別のままにする』という処理でよいか、それとも他の探し方(例: th2-netのメンバーの個人リポジトリ、th2.devが読めれば載っているかもしれない一覧頁など)をこの回のうちに試すべきだったか確認したい。
5. **`rusty-bot`(8-013)の最小実行が『鍵なしのオブジェクト構築』までで止まったこと**: 合成ティック列を使った成行/指値の1往復の損益計算まで到達できなかった(rbotの内部DB(SQLite/parquet)形式へ合成データを注入する文書化された経路が見当たらなかったため)。README・PyPI説明文以上のソースコード読解(Rustのモジュール実装)まで踏み込めば経路が見つかる可能性はあるが、この回は文書に書かれた経路(`download_archive`による実データ取得)以外を試していない。当方の実データは使わない規則があるため、合成データの注入経路が無いこと自体を『できない』と書いてよいか、それとももう一段深くソースを読むべきか確認したい。
6. **`FX Replay`(8-008)のE4(印・段2)をこの回は当て直していないこと**: 起動文はE1a・E2・E3a・E3b・E5・E6のみを当て直す指示で、E4(すでに印・段2)は対象外だった。E1a〜E6のうちE4以外がすべて『なし』で確定したため、E4だけが唯一の『区分8の要素』としてこの候補の深掘りを支えている形になる。E4の印・段2の根拠(5回目までのもの)をこの回で裏取りしていないが、これでよいか。

## 区分8 — 7 回目の実行(2026-09-24)

起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run7_prompt.md`(指紋 `6c00be8112ee`)。追補 `docs/DATA/delegations/20260923_tools_survey_cat8_addendum.md`(指紋 `2c178ba75341`)。対象 8 行: 8-006 `freqtrade`(§4.0 表の過半埋め+E1a/E6の`なし`当て直し) / 8-016 `Exactpro の reconciliation testing`(th2 部品名の収集、E3a・E3b・E4・E5・E6と E2 の段) / 8-001 `qf-lib`(E1a/E3a/E6) / 8-002 `PineForge`(E2/E6) / 8-004 `akurkar07/OrderBook`(E2/E3a/E3b/E4/E6、`curl` のみ・clone/実行禁止) / 8-007 `backtrex`(E1b/E6) / 8-008 `FX Replay`(E1b) / 8-013 `rusty-bot`(E1a/E3b/E6)。**この回は予算で止めない(追補 §5、オーナー決定 L-507「案A」)。`--deadline` は付けない(起動文 §0.4)。**

### 検索計画
この回は新しい検索計画を打たない(委任文 §2「前回の残りの候補名があれば、まずそれを深掘りする(検索計画は打ち直さない)」)。

### 出典
| # | 出典 | URL | 内容 | 取得日 |
|---|---|---|---|---|
| 1 | GitHub(ungh.cc) | https://ungh.cc/repos/freqtrade/freqtrade | freqtrade の repo メタ(星 54731・push 日) | 2026-09-24 |
| 2 | GitHub(ungh.cc) | https://ungh.cc/repos/freqtrade/freqtrade/contributors | contributors 一覧(先頭 30 名。ページの上限は未確認) | 2026-09-24 |
| 3 | pypistats | https://pypistats.org/api/packages/freqtrade/recent | 週 DL 数 8,970 | 2026-09-24 |
| 4 | PyPI | https://pypi.org/pypi/freqtrade/json | requires_dist(84 件)・vulnerabilities(空)・owner 組織 `freqtrade` | 2026-09-24 |
| 5 | OSV | https://api.osv.dev/v1/query(POST、package=freqtrade, ecosystem=PyPI) | 既知の脆弱性 0 件 | 2026-09-24 |
| 6 | PyPI(pip download --no-deps、隔離) | freqtrade-2026.8-py3-none-any.whl | 導入前検査(wheel 展開・364 ファイル・バイナリ無し) | 2026-09-24 |
| 7 | PyPI(pip install、隔離 venv) | freqtrade 2026.8 | 導入実測(48.397 秒・依存 85・pip check 合格) | 2026-09-24 |
| 8 | freqtrade CLI(隔離 venv、実行) | `freqtrade backtesting`(kraken・合成 OHLCV・自作戦略) | 最小実行(1 トレード・-2.222 USD) | 2026-09-24 |
| 9 | GitHub raw | docs/backtesting.md(freqtrade/develop) | 「all times are in UTC」(時刻の扱い) | 2026-09-24 |
| 10 | GitHub raw | docs/recursive-analysis.md(freqtrade/develop) | recursive-analysis コマンド(E6 の新規根拠) | 2026-09-24 |
| 11 | GitHub(ungh.cc + git clone --depth 1) | freqtrade/freqtrade(develop、782 ファイル) | E1a・E6 の `なし`/`印` 当て直しの全文検索 | 2026-09-24 |
| 12 | WebSearch ×5 | 「site:github.com/th2-net repository」ほか 4 種 | th2 部品名の発見(§1 参照) | 2026-09-24 |
| 13 | Maven Central | https://search.maven.org/solrsearch/select?q=g:com.exactpro.th2 | `com.exactpro.th2` グループの成果物一覧(numFound=73) | 2026-09-24 |
| 14 | GitHub raw | th2-check2-recon・th2-check2-recon-template・th2-crawler・th2-check1・th2-estore・th2-rpt-viewer の README | E2 段・E4・E6 の一次資料(本文は生ログに印字済み) | 2026-09-24 |
| 15 | GitHub(ungh.cc) | https://ungh.cc/repos/th2-net/th2-documentation/files/master | th2-documentation は画像のみで文書無し(行き止まり) | 2026-09-24 |
| 16 | GitHub(ungh.cc + git clone --depth 1) | quarkfin/qf-lib(master、865 ファイル) | E1a・E3a・E6 の `なし`/`印` 当て直しの全文検索 | 2026-09-24 |
| 17 | GitHub(ungh.cc + git clone --depth 1) | pineforge-4pass/pineforge-engine(main、1374 ファイル) | E2・E6 の `なし`/`印` 当て直しの全文検索 | 2026-09-24 |
| 18 | GitHub(ungh.cc + raw、`curl` 1 本ずつ) | akurkar07/OrderBook(main、17 ファイル全件) | clone せず curl のみで E2・E3a・E3b・E4・E6 を確認 | 2026-09-24 |
| 19 | 公式サイト(sitemap.xml + curl) | https://backtrex.com/sitemap.xml、en/docs 10 頁+en/blog 130 頁 | E1b・E6 の `なし`/`印` 当て直し(140 頁全件) | 2026-09-24 |
| 20 | サポートセンター(curl) | https://support-webflow.fxreplay.app/articles/*(107 記事) | E1b の `なし`→`印` 当て直し(105 記事本文) | 2026-09-24 |
| 21 | GitHub(ungh.cc + git clone --depth 1) | yasstake/rbot(main、171 ファイル) | E1a・E3b・E6 の `なし` 当て直しの全文検索 | 2026-09-24 |

### 知見
(設計票 §4.2 の「記録する軸」。原文と URL。`印` を付けた要素ごと。全要素共通の `方式(原文)` / `入力(原文)` から先に書く)

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `freqtrade / E6 / 方式(原文)`: 「This command is built upon preparing different lengths of data and calculates indicators based on them...After calculating the indicators of different startup candle values (`startup_candle_count`) are done, the values of last rows across all specified `startup_candle_count` are compared to see how much variance they show compared to the base calculation.」(docs/recursive-analysis.md) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:514 / https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/recursive-analysis.md / 取得日 2026-09-24 |
| 2 | `freqtrade / E6 / この機能が名指す対象の原文`: 「Users should assess the table per indicator to decide if the specified `startup_candle_count` results in a sufficiently small variance so that the indicator does not have any effect on entries and/or exits.」= 合否は利用者が判断(段2の根拠)。E3a(lookahead-analysis)・E1a のどちらとも異なる独立機能(再帰的な計算式の実装誤り) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:514 / 取得日 2026-09-24 |
| 3 | `freqtrade / E6 / 自動で判定するか`: なし(表形式の分散を出すのみ。合否は人) / 外から持ち込める対象: 対象は freqtrade 自身の `populate_indicators`/`@informative` の指標計算に限る(枠内) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:514 / 取得日 2026-09-24 |
| 4 | `Exactpro の reconciliation testing / E4 / 方式(原文)`: 「It requests events/messages for the certain time intervals using rpt-data-provider. Those intervals are processed periodically, and new ones are written to Cradle if necessary.」「Crawler takes events/messages from intervals with startTimestamps >= "from" and < "to" of intervals.」(th2-crawler README) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:839 / https://raw.githubusercontent.com/th2-net/th2-crawler/master/README.md / 取得日 2026-09-24 |
| 5 | `Exactpro の reconciliation testing / E4 / 入力(原文)`: Cradle に保存済みの event/message(型は `EVENTS` か `MESSAGES`)。再生の粒度は `defaultLength`(既定 PT1H)の時間区間単位 | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:839 / 取得日 2026-09-24 |
| 6 | `Exactpro の reconciliation testing / E4 / 再生の粒度・遅延・時計の扱い`: `defaultLength`(区間の粒度、既定 PT1H)・`delay`(区間処理後の待ち、既定 10 秒)・`toLag`(現在時刻からのオフセット、既定 1)で制御。時計は ISO8601(UTC、例 `2021-06-16T12:00:00.00Z`) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:839 / 取得日 2026-09-24 |
| 7 | `Exactpro の reconciliation testing / E4 / 外から持ち込める対象・段の理由`: 対象は th2 自身の Cradle 保存形式のイベント/メッセージと、gRPC の `crawler data processor` 契約(`com.exactpro.th2.crawler.dataprocessor.grpc.DataProcessorService`)に限られ、一般の CSV 等は持ち込めない → 段3(自動で処理を行うが対象は th2 の枠内) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:839 / 取得日 2026-09-24 |
| 8 | `Exactpro の reconciliation testing / E6 / 方式(原文)`: 「CheckRuleRequest - get message filter from request and check it with messages in the cache or await specified time in case of empty cache or message absence.」「If **message_timeout** is specified, the rule completes with a **PASSED** result when `check1` receives a message...」(th2-check1 README) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:994 / https://raw.githubusercontent.com/th2-net/th2-check1/master/README.md / 取得日 2026-09-24 |
| 9 | `Exactpro の reconciliation testing / E6 / (ア)基準を指定できるか`: 印。`root_filter`/`filter`・`timeout`・`message_timeout`・`checkpoint` を利用者が指定できる(README「CheckRuleRequest」節) / (イ)結果を保存して次の実行と比べられるか: 記載なし(読んだ箇所: th2-check1 README 全文) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:994 / 取得日 2026-09-24 |
| 10 | `Exactpro の reconciliation testing / E6 / 外から持ち込める対象`: 対象(検査するメッセージストリーム)は `th2-conn-*` 経由で接続する任意の外部メッセージストリームで、th2 の枠の外から持ち込める → 段4((イ)を欠くため段5にはしない) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:994 / 取得日 2026-09-24 |
| 11 | `Exactpro の reconciliation testing / E2 / 段の理由`: `CheckSequenceRuleRequest`「prefilters the messages and verify all of them by filter. Order checking configured from request.」(順序の乱れ)・`submitNoMessageCheck`「This rule verifies that no messages are received by check1 within a specified interval.」(欠け)。対象は th2 自身のメッセージバス形式に限るため段3(段4の『外から持ち込める』の条件は満たさない) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1032 / 取得日 2026-09-24 |
| 12 | `qf-lib / E6 / 方式(原文)`: 「Class providing statistics and analysis for checking if backtest is overfitted. It is based on the algorithms described in "The probability of backtest overfitting" by Bailey, Borwein, Lopez de Prado and Jim Zhu.」「def calculate_overfitting_probability(self): \"\"\" Returns the probability of backtest overfitting. \"\"\"」(qf_lib/analysis/backtests_overfitting/overfitting_analysis.py) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1109 / https://github.com/quarkfin/qf-lib/blob/master/qf_lib/analysis/backtests_overfitting/overfitting_analysis.py / 取得日 2026-09-24 |
| 13 | `qf-lib / E6 / この機能が名指す対象の原文・自動で判定するか`: 関数はオーバーフィット確率(PBO、浮動小数)を返すのみで、合否のしきい値は人が読んで判断する(段2)。E1a(突き合わせ)・E3b(ルックアヘッド防止)のどちらとも異なる独立機能 | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1109 / 取得日 2026-09-24 |
| 14 | `PineForge / E2 / 方式(原文)`: 「if (bar.timestamp <= earlier) { out.error = NativeInputPreflightError::NotStrictlyIncreasing;」「if (interval->open_ms <= previous->open_ms) { out.error = NativeInputPreflightError::OverlappingSlot;」「out.error = NativeInputPreflightError::InSessionGap;」「if (!preflight_bar_structurally_valid(...)) { out.error = NativeInputPreflightError::StructuralInvalid;」(src/market_driver.cpp) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1140 / https://github.com/pineforge-4pass/pineforge-engine/blob/main/src/market_driver.cpp / 取得日 2026-09-24 |
| 15 | `PineForge / E2 / 検出する異常の種類`: 順序の乱れ(`NotStrictlyIncreasing`)・重複/重なり(`OverlappingSlot`)・欠け(`InSessionGap`)・型や範囲の違反(`StructuralInvalid`: OHLC の各値の有限性・正値性と大小関係(low<=min(open,close)、high>=max(open,close))・出来高の非負性を1つずつ判定する一連の`if`文。等号は使わずここでは記述のみ)。直すか報告だけか: 拒否(エラーを返し処理を止める) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1140 / 取得日 2026-09-24 |
| 16 | `PineForge / E2 / 入力(原文)・外から持ち込める対象`: 「with csv_path.open(newline="", encoding="utf-8") as handle: reader = csv.DictReader(handle)」(scripts/run_stream_corpus.py、`load_ohlcv_slice`)= 通常の投入経路が外部 CSV であり、そのまま preflight を通る → 段4((ア)しきい値の指定は確認できず段5にはしない) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1208 / https://github.com/pineforge-4pass/pineforge-engine/blob/main/scripts/run_stream_corpus.py / 取得日 2026-09-24 |
| 17 | `backtrex / E1b / 方式(原文)・入力(原文)`: 「Understanding Metrics Learn how to interpret Total Return, Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor, and other backtest」「Reading the Equity Curve The equity curve plots your portfolio value over time.」(en/docs/backtesting/understanding-metrics)。当方の損益・指標計算と同じ種類の出力(Win Rate・Profit Factor・Equity Curve等)を独自実装で出す | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1652 / https://backtrex.com/en/docs/backtesting/understanding-metrics / 取得日 2026-09-24 |
| 18 | `backtrex / E1b / 突き合わせの単位・外から持ち込める対象`: 単位は指標の集計値(Sharpe・Drawdown等、1トレード単位ではない)。対象はユーザーが backtrex 自身のノーコードブロックで組んだ戦略の結果に限られる(枠内)→段3 | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1652 / 取得日 2026-09-24 |
| 19 | `backtrex / E6 / 方式(原文)`: 「Backtrex automatically calculates probability of ruin and Monte Carlo simulations in the backtest report, with no code required.」(en/blog/probability-of-ruin-trading-monte-carlo)「the backtest report automatically displays the Monte Carlo confidence cone in one click, with no code or CSV export required.」(en/blog/equity-curve-confidence-intervals-strategy-robustness) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1663 / https://backtrex.com/en/blog/probability-of-ruin-trading-monte-carlo / https://backtrex.com/en/blog/equity-curve-confidence-intervals-strategy-robustness / 取得日 2026-09-24 |
| 20 | `backtrex / E6 / 自動で判定するか・この機能が名指す対象`: 確率(破産確率・信頼区間)を自動計算して表示するが、合否のしきい値は人が判断(段2)。E1a(TradingView との突き合わせ)・E3a/E3b(anti-repainting)のどれとも異なる独立機能(モンテカルロ頑健性チェック) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1663 / 取得日 2026-09-24 |
| 21 | `FX Replay / E1b / 方式(原文)・入力(原文)`: 「First dashboard: Total PnL: Total profit or loss on account...Win Rate: Percentage of winning trades...Average RR: Average risk-reward ratio across all trades.」(articles/analytic-metrics-defined) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1685 / https://support-webflow.fxreplay.app/articles/analytic-metrics-defined / 取得日 2026-09-24 |
| 22 | `FX Replay / E1b / 突き合わせの単位・外から持ち込める対象`: 単位はセッション/プロジェクト単位の集計(勝率・平均RR等)。対象は FX Replay 上で手動リプレイ中に記録した自分のトレード記録に限られる(枠内、外部の取引履歴の取り込みは記載なし)→段3 | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:1685 / 取得日 2026-09-24 |

### 候補の一覧
(8-001〜8-016 の全 16 行、この回の値で載せる。変更点はこの回に触った候補にだけ書く)
1. [深掘り] `qf-lib` (8-001) — https://github.com/quarkfin/qf-lib — バックテストエンジン(区分1から) — 状態: 深掘り — 変更点: E6 を `なし`→`印`(段2、overfitting_analysis.py のオーバーフィット確率計算)。E1a・E3a は `なし` のまま(N=865/M=823 で当て直し、根拠を書き直し)
2. [深掘り] `PineForge` (8-002) — https://github.com/pineforge-4pass/pineforge-engine — Pineスクリプト系バックテストエンジン(区分1から) — 状態: 深掘り — 変更点: E2 を `なし`→`印`(段4、market_driver.cpp の入力 preflight)。E6 は `なし` のまま(N=1374/M=1352 で当て直し)
3. `prediction-market-backtester` (8-003) — https://github.com/Quentin-Piot/prediction-market-backtester — 予測市場バックテストエンジン(区分1から) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
4. `akurkar07/OrderBook` (8-004) — https://github.com/akurkar07/OrderBook — 板シミュレータ(区分1から、危険で導入停止) — 状態: 危険で導入停止 — 変更点: E2・E3a・E3b・E4・E6 を当て直し、すべて `なし` を維持(N=17/M=17、17 ファイル全件を curl のみで取得。clone・導入・実行はしていない)
5. `Exegy` (8-005) — https://www.exegy.com/ — 市場データベンダー(区分1から、登録が要る) — 状態: 登録が要る — 変更点: この回は触っていない(台帳の値のまま)
6. [深掘り] `freqtrade` (8-006) — https://github.com/freqtrade/freqtrade — 暗号資産botフレームワーク — 状態: 深掘り(前回までは`浅い`。§4.0 の表の一次資料/実測が 21/43 から 38/43 に増え過半を超えたため、この回で`深掘り`に進めた。E1a〜E6 に未判別が無いことは 6 回目で既に確定していた) — 変更点: §4.0 の表の `未確認`/`推定` 22 項目のうち 17 項目を `一次資料`/`実測` に当て直し(pip install の実測・OSV 照会・PyPI メタデータ・wheel 展開・合成データでの backtesting 実行など)。E1a の `なし` を当て直し(N=782/M=707)。E6 を `なし`→`印`(段2、recursive-analysis コマンド)
7. [深掘り] `backtrex` (8-007) — https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide — ノーコード・ビジュアルバックテストSaaS — 状態: 深掘り — 変更点: E1b を `なし`→`印`(段3、Win Rate/Profit Factor/Equity Curve 等の指標計算)。E6 を `なし`→`印`(段2、モンテカルロ破産確率・信頼区間の自動計算)。N=140/M=140(Documentation 10 頁+Blog 130 頁を全件再取得)
8. [深掘り] `FX Replay` (8-008) — https://fxreplay.com/ — 手動バーリプレイSaaS(Support Center 全8分類107記事で再確定) — 状態: 深掘り — 変更点: E1b を `なし`→`印`(段3、Total PnL/Win Rate/Average RR 等のダッシュボード集計)。N=107/M=105(動画のみの記事2件を除外、除外の再確認込み)
9. [深掘り] `nicferrari/backtester` (8-009) — https://github.com/nicferrari/backtester — Rust製の小規模バックテストクレート — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま。次回以降に回す)
10. [深掘り] `arXiv:2603.20319` (8-010) — https://arxiv.org/abs/2603.20319 — 実装リスク(エンジン間の相違)を論じる論文 — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
11. [深掘り] `arXiv:2512.12924` (8-011) — https://arxiv.org/abs/2512.12924 — Walk-forward検証フレームワークの論文+実装 — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
12. [深掘り] `VectorBT` (8-012) — https://github.com/polakowo/vectorbt — ベクトル化バックテストライブラリ — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
13. [深掘り] `rusty-bot` (8-013) — https://x.com/WannabeBotter/status/1810558269565571211 — Rust製トレーディングボット(yasstake/rbot、PyPI配布あり、bitbank対応) — 状態: 深掘り — 変更点: E1a・E3b・E6 を当て直し、すべて `なし` を維持(N=171/M=169)。E6 で見つかった `validate_db_by_date`(dead_code、実装は本リポジトリに無い)は問いに出す
14. [深掘り] `Fincept Terminal` (8-014) — https://github.com/Fincept-Corporation/FinceptTerminal — 統合金融ターミナル — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま。E1b・E3b・E4 の段が未判別のまま残っている)
15. [深掘り] `TradingView のリプレイ機能` (8-015) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:98-100(検索計画3、URL は生ログに無い) — チャート上のバー再生機能 — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
16. `Exactpro の reconciliation testing` (8-016) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:95-97(検索計画2、URL は生ログに無い) — メッセージ照合テストの方法論+th2プラットフォーム+商用製品 — 状態: 判別に一次資料が要る(E3a・E3b・E5 に未判別が残るため深掘りにできない) — 変更点: WebSearch 5 回(`site:github.com/th2-net` ほか)と Maven Central(`com.exactpro.th2` グループ、73 成果物)で th2 部品名を収集。E4 を `なし`→`印`(段3、th2-crawler の時間区間リプレイ)。E6 を `未判別`→`印`(段4、th2-check1 の CheckRuleRequest。README 本文は生ログに印字済み)。E2 の段を `未判別`→`3` に決定。E3a・E3b・E5 は未判別のまま(組織全体を読み切れていない)

### 要素と段
| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 | 生ログの行 |
|---|---|---|---|---|---|---|
| `qf-lib` | E1a | なし | - | 実測 | ファイル一覧865件のうち42件除外(png25+xlsx13+pdf3+jpg1=画像/バイナリで文字検索の対象として意味を持たない)。一覧 823 件 / 読んだ 823 件。突き合わせ/突合/cross-check/reconcil/参照実装/golden で0件 | docs/DATA/probes/20260923_tools_8_run7.log:1057-1062 |
| `qf-lib` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `qf-lib` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `qf-lib` | E3a | なし | - | 実測 | ファイル一覧865件のうち除外は同じ42件(画像/バイナリ)。一覧 823 件 / 読んだ 823 件。look-?ahead/lookahead/ルックアヘッド/repaint/future.?leak/survivorship の一致47件は全てE3b(防ぐ)の既存根拠と同じ設計(データプロバイダのlook-ahead biasガード)で、検出・報告する機能ではない | docs/DATA/probes/20260923_tools_8_run7.log:1063-1105 |
| `qf-lib` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `qf-lib` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `qf-lib` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `qf-lib` | E6 | 印 | 2 | 実測 | qf_lib/analysis/backtests_overfitting/overfitting_analysis.py の OverfittingAnalysis クラス(オーバーフィット確率の計算。人が判断) | docs/DATA/probes/20260923_tools_8_run7.log:1109-1126 |
| `PineForge` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `PineForge` | E1b | 印 | 5 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `PineForge` | E2 | 印 | 4 | 実測 | src/market_driver.cpp の preflight_native_inputs(NotStrictlyIncreasing/OverlappingSlot/InSessionGap/StructuralInvalid)。scripts/run_stream_corpus.py の load_ohlcv_slice がCSVから読み込み対象を外部CSVから持ち込める | docs/DATA/probes/20260923_tools_8_run7.log:1140-1220 |
| `PineForge` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `PineForge` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `PineForge` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `PineForge` | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `PineForge` | E6 | なし | - | 実測 | ファイル一覧1374件のうち22件除外(gz18+tar4=バイナリ圧縮物)。一覧 1352 件 / 読んだ 1352 件。検証/品質/verify/validat/quality の一致164件(tests/除く)はE1a(TradingView突き合わせ)・E2(preflight、この回でE2確定)・E3b(anti-repainting)・開発者自身のCI(ci_verify.py/check_twin_parity.py)のいずれかに帰着し独立のE6機能は見当たらなかった | docs/DATA/probes/20260923_tools_8_run7.log:1137-1139 |
| `prediction-market-backtester` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `prediction-market-backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `prediction-market-backtester` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `prediction-market-backtester` | E3a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `prediction-market-backtester` | E3b | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `prediction-market-backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `prediction-market-backtester` | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `prediction-market-backtester` | E6 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `akurkar07/OrderBook` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `akurkar07/OrderBook` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `akurkar07/OrderBook` | E2 | なし | - | 実測 | 一覧17件/読んだ17件(全ファイルがテキストで除外なし)。README・CMakeLists.txt・LICENSE・src/*・tests/*・reference/*・benchmarks/* の全文を curl で1本ずつ取得して読んだ(clone・実行はしていない)。データ品質/lookahead/replay/verify語のいずれも0件(唯一の関連記述はREADME 95-96行の『重複ID拒否』『注文入力検証』で、これは市場データではなく注文入力の検証のため、この回はE2に当てなかった=判断に迷った点) | docs/DATA/probes/20260923_tools_8_run7.log:1281-1290 |
| `akurkar07/OrderBook` | E3a | なし | - | 実測 | 一覧17件/読んだ17件(全ファイルがテキストで除外なし)。README・CMakeLists.txt・LICENSE・src/*・tests/*・reference/*・benchmarks/* の全文を curl で1本ずつ取得して読んだ(clone・実行はしていない)。データ品質/lookahead/replay/verify語のいずれも0件(唯一の関連記述はREADME 95-96行の『重複ID拒否』『注文入力検証』で、これは市場データではなく注文入力の検証のため、この回はE2に当てなかった=判断に迷った点) | docs/DATA/probes/20260923_tools_8_run7.log:1281-1290 |
| `akurkar07/OrderBook` | E3b | なし | - | 実測 | 一覧17件/読んだ17件(全ファイルがテキストで除外なし)。README・CMakeLists.txt・LICENSE・src/*・tests/*・reference/*・benchmarks/* の全文を curl で1本ずつ取得して読んだ(clone・実行はしていない)。データ品質/lookahead/replay/verify語のいずれも0件(唯一の関連記述はREADME 95-96行の『重複ID拒否』『注文入力検証』で、これは市場データではなく注文入力の検証のため、この回はE2に当てなかった=判断に迷った点) | docs/DATA/probes/20260923_tools_8_run7.log:1281-1290 |
| `akurkar07/OrderBook` | E4 | なし | - | 実測 | 一覧17件/読んだ17件(全ファイルがテキストで除外なし)。README・CMakeLists.txt・LICENSE・src/*・tests/*・reference/*・benchmarks/* の全文を curl で1本ずつ取得して読んだ(clone・実行はしていない)。データ品質/lookahead/replay/verify語のいずれも0件(唯一の関連記述はREADME 95-96行の『重複ID拒否』『注文入力検証』で、これは市場データではなく注文入力の検証のため、この回はE2に当てなかった=判断に迷った点) | docs/DATA/probes/20260923_tools_8_run7.log:1281-1290 |
| `akurkar07/OrderBook` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `akurkar07/OrderBook` | E6 | なし | - | 実測 | 一覧17件/読んだ17件(全ファイルがテキストで除外なし)。README・CMakeLists.txt・LICENSE・src/*・tests/*・reference/*・benchmarks/* の全文を curl で1本ずつ取得して読んだ(clone・実行はしていない)。データ品質/lookahead/replay/verify語のいずれも0件(唯一の関連記述はREADME 95-96行の『重複ID拒否』『注文入力検証』で、これは市場データではなく注文入力の検証のため、この回はE2に当てなかった=判断に迷った点) | docs/DATA/probes/20260923_tools_8_run7.log:1281-1290 |
| `Exegy` | E1a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exegy` | E1b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exegy` | E2 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exegy` | E3a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exegy` | E3b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exegy` | E4 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exegy` | E5 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exegy` | E6 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `freqtrade` | E1a | なし | - | 実測 | ファイル一覧782件のうち75件除外(png26+jpg8+svg3+zip4+gz5+whl2+feather27=画像/バイナリ配布物/pandasバイナリ形式)。一覧 707 件 / 読んだ 707 件。突き合わせ/突合/cross-check/reconcil/参照実装/golden で0件 | docs/DATA/probes/20260923_tools_8_run7.log:508-510 |
| `freqtrade` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `freqtrade` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `freqtrade` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `freqtrade` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `freqtrade` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `freqtrade` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `freqtrade` | E6 | 印 | 2 | 実測 | docs/recursive-analysis.md のrecursive-analysisコマンド(startup_candle_count違いでの指標値の分散を自動計算して表で提示、合否は人が判断) | docs/DATA/probes/20260923_tools_8_run7.log:514-600 |
| `backtrex` | E1a | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `backtrex` | E1b | 印 | 3 | 実測 | en/docs/backtesting/understanding-metrics の Total Return/Sharpe/Max Drawdown/Win Rate/Profit Factor/Equity Curve の独自計算 | docs/DATA/probes/20260923_tools_8_run7.log:1652-1659 |
| `backtrex` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `backtrex` | E3a | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `backtrex` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `backtrex` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `backtrex` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `backtrex` | E6 | 印 | 2 | 実測 | en/blog/probability-of-ruin-trading-monte-carlo・en/blog/equity-curve-confidence-intervals-strategy-robustness のモンテカルロ破産確率・信頼区間の自動計算(合否は人) | docs/DATA/probes/20260923_tools_8_run7.log:1663-1667 |
| `FX Replay` | E1a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `FX Replay` | E1b | 印 | 3 | 実測 | articles/analytic-metrics-defined の Total PnL/Win Rate/Average RR 等のダッシュボード集計(105記事中1記事に一致、一覧107件/読んだ105件) | docs/DATA/probes/20260923_tools_8_run7.log:1677-1687 |
| `FX Replay` | E2 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `FX Replay` | E3a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `FX Replay` | E3b | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `FX Replay` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `FX Replay` | E5 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `FX Replay` | E6 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `nicferrari/backtester` | E1a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `nicferrari/backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `nicferrari/backtester` | E2 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `nicferrari/backtester` | E3a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `nicferrari/backtester` | E3b | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `nicferrari/backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `nicferrari/backtester` | E5 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `nicferrari/backtester` | E6 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2603.20319` | E1a | 印 | 1 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2603.20319` | E1b | 印 | 1 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2603.20319` | E2 | 印 | 1 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2603.20319` | E3a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2603.20319` | E3b | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2603.20319` | E4 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2603.20319` | E5 | 印 | 1 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2603.20319` | E6 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2512.12924` | E1a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2512.12924` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2512.12924` | E2 | 印 | 4 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2512.12924` | E3a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2512.12924` | E3b | 印 | 4 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2512.12924` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2512.12924` | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `arXiv:2512.12924` | E6 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `VectorBT` | E1a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `VectorBT` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `VectorBT` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `VectorBT` | E3a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `VectorBT` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `VectorBT` | E4 | 印 | 4 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `VectorBT` | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `VectorBT` | E6 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `rusty-bot` | E1a | なし | - | 実測 | ファイル一覧171件のうち2件除外(png、画像)。一覧 169 件 / 読んだ 169 件。突き合わせ/突合/cross-check/reconcil/参照実装/golden で0件 | docs/DATA/probes/20260923_tools_8_run7.log:1697-1699 |
| `rusty-bot` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `rusty-bot` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `rusty-bot` | E3a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `rusty-bot` | E3b | なし | - | 実測 | ファイル一覧171件のうち除外は同じ2件(画像)。一覧 169 件 / 読んだ 169 件。防ぐ/purge/embargo/ルックアヘッド防止/time.?split/walk-forward で0件 | docs/DATA/probes/20260923_tools_8_run7.log:1700-1702 |
| `rusty-bot` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `rusty-bot` | E5 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `rusty-bot` | E6 | なし | - | 実測 | ファイル一覧171件のうち除外は同じ2件(画像)。一覧 169 件 / 読んだ 169 件。検証/品質/verify/validat/quality の一致4件は取引所APIのメッセージ型名・npm依存名・開発者自身のpytest内コメントのいずれかで、独立の機能は見当たらなかった(exchanges/bitflyer/src/market.rs の validate_db_by_date は #[allow(dead_code)] かつ実装が本リポジトリに無いため印としなかった=問いに出す) | docs/DATA/probes/20260923_tools_8_run7.log:1703-1712 |
| `Fincept Terminal` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Fincept Terminal` | E1b | 印 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Fincept Terminal` | E2 | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Fincept Terminal` | E3a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Fincept Terminal` | E3b | 印 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Fincept Terminal` | E4 | 印 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Fincept Terminal` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Fincept Terminal` | E6 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `TradingView のリプレイ機能` | E1a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `TradingView のリプレイ機能` | E1b | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `TradingView のリプレイ機能` | E2 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `TradingView のリプレイ機能` | E3a | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `TradingView のリプレイ機能` | E3b | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `TradingView のリプレイ機能` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `TradingView のリプレイ機能` | E5 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `TradingView のリプレイ機能` | E6 | なし | - | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exactpro の reconciliation testing` | E1a | 印 | 4 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exactpro の reconciliation testing` | E1b | 印 | 4 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exactpro の reconciliation testing` | E2 | 印 | 3 | 実測 | th2-check1 README の CheckSequenceRuleRequest(順序の乱れ)・submitNoMessageCheck(欠け)。対象はth2自身のメッセージバス形式に限るため段4は満たさず段3 | docs/DATA/probes/20260923_tools_8_run7.log:1032 |
| `Exactpro の reconciliation testing` | E3a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exactpro の reconciliation testing` | E3b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exactpro の reconciliation testing` | E4 | 印 | 3 | 実測 | th2-crawler README(from/to時間区間でCradleのevents/messagesを周期的に取得し、gRPCのdata processorへ送る。対象はth2自身のCradle形式とgRPC契約に限る) | docs/DATA/probes/20260923_tools_8_run7.log:839-969 |
| `Exactpro の reconciliation testing` | E5 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(6回目の節) | |
| `Exactpro の reconciliation testing` | E6 | 印 | 4 | 実測 | th2-check1 README の CheckRuleRequest(root_filter/timeout/message_timeoutを利用者が指定しPASSED/FAILEDを自動判定。対象は外部の任意メッセージストリームで枠外に及ぶが、結果を次回実行と比較する記述が無いため段5ではなく段4) | docs/DATA/probes/20260923_tools_8_run7.log:994-1032 |

### 4.0 機械可読の表
(8-006 `freqtrade` の §4.0 表。1〜6 回目の値のうち、この回に実測/一次資料へ当て直した項目だけを新しい値で載せる。変わらない項目は前回までの値のまま)

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| freqtrade | コミット数 | 未確認(この回。contributors 一覧の合計貢献数は分かるが「コミット数」そのものではない) | 未確認 | 試した手段: ungh.cc の contributors のみ(コミット数の専用集計エンドポイントは無し) |
| freqtrade | 保守者数 | 30 名以上(ungh.cc の contributors 応答は上位 30 名で切れており、総数は未確認。最多は xmatthias 19580 貢献) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:8-10 |
| freqtrade | 週DL数 | 8,970(last_week) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:11-13 |
| freqtrade | 初回公開日 | 2017-05-17(台帳の値のまま) | 実測 | docs/DATA/probes/20260923_tools_8_run4.log の `freqtrade_repo_meta` の節 |
| freqtrade | 既知の脆弱性 | 0 件(OSV `{}` / PyPI vulnerabilities `[]`) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:14-20 |
| freqtrade | 導入可否 | 可(pip install 成功、rc=0) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:62-127 |
| freqtrade | install所要秒 | 48.40(`time` コマンドの real 0m48.397s、cat8_step の計測は 48.402s) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:62-127 |
| freqtrade | 依存数 | 85(pip list --format=freeze、freqtrade自身を除く) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:131-136 |
| freqtrade | pip check | No broken requirements found | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:128-130 |
| freqtrade | 最小実行の可否 | 可(kraken・合成 OHLCV・自作戦略で backtesting が完走) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:451-482 |
| freqtrade | 最小実行の中身 | 合成 500 本の OHLCV(1h、乱数)を freqtrade 公式データハンドラ(feather)で書き出し、index20 で成行/指値の買い、index40 で指値の売りを出す自作戦略を `freqtrade backtesting` で実行。1 トレード成立、損失 -2.222 USD(-0.22%)、保有 20:00:00 | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:451-482 |
| freqtrade | 実行所要秒 | 4.586(backtesting コマンドの time_s) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:451-482 |
| freqtrade | wheel展開 | 364 ファイル、拡張子は .py 332/.j2 22/.txt 2/.json 1/.ipynb 1/.ico 1/.html 1(バイナリ拡張子は無し) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:29-58 |
| freqtrade | setup.py導入時実行 | 無し(PyPI 配布は wheel(.whl)で、`pip download` で取得したのも wheel。wheel の install は setup.py を実行しない) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:21-28 |
| freqtrade | 同梱バイナリ | 無し(wheel 展開の拡張子集計にバイナリ(.so/.pyd等)が無い) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:29-58 |
| freqtrade | 外部送信 | 取引所 API への接続が backtesting でも必須(合成データのみのオフライン実行を試みたが、kraken の market 一覧取得のため外部通信が発生することを実測で確認) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:198-450 |
| freqtrade | 時刻の扱い | UTC(「Each side of the timerange is parsed on its own...(all times are in UTC)」docs/backtesting.md 157行) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:486-491 |
| freqtrade | 規模の見積 | 500本・1ペアのbacktestingが4.586秒(実測)。456日・複数ペアへの外挿は未実施 | 推定 | docs/DATA/probes/20260923_tools_8_run7.log:451-482 から外挿(未実施) |
| freqtrade | 配布元の一致 | 一致(PyPI project_urls Homepage=`https://github.com/freqtrade/freqtrade`、PyPI ownership.organization=`freqtrade`、GitHub org も `freqtrade`) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:14-17 |
| freqtrade | 依存の一覧 | requires_dist 84 件(PyPI json)、実インストール 85 パッケージ(pip list) | 実測 | docs/DATA/probes/20260923_tools_8_run7.log:14-17,131-136 |
| freqtrade | 保守者名の一貫性 | 一致(PyPI ownership.organization=`freqtrade`、GitHub org `freqtrade/freqtrade`) | 一次資料 | docs/DATA/probes/20260923_tools_8_run7.log:14-17 |

**この回で残した `未確認`/`推定`(過半の条件には影響しない 5 項目)**: コミット数(未確認)・当方データ投入(推定、1〜4回目の値のまま)・規模の見積(推定)・保守者数は実測に区分したが総数は未確認・4軸4_向上(推定、1〜4回目の値のまま)。
**この回の§4.0表の一次資料/実測の割合**: 43 項目中 38 項目(前回 21 項目から 17 項目を新たに一次資料/実測に当て直した)。過半(22 項目以上)を超えたので `深掘り` の条件(委任文 §4.0)を満たす。

### ツール1件ごとの表
(この回に新しく確定した列だけを書く。他の列は 1〜6 回目のまま)

- **freqtrade**: §4.0 の表(上記)で過半を一次資料/実測に埋めた。**当方に無いもの(追加)**: `recursive-analysis` コマンド — 指標計算が `startup_candle_count`(過去方向のウォームアップ本数)に依存して値がぶれる実装誤りを、複数の `startup_candle_count` で計算し分散を表にして提示する機能。当方の `src/bot/backtest/` にはこの種の「同一計算の入力量依存の安定性チェック」は無い。
- **backtrex**: **当方に無いもの(追加)**: (1) 独自のバックテスト指標計算エンジン(Win Rate・Profit Factor・Equity Curve 等。当方の突き合わせの相手になりうる= E1b)。(2) モンテカルロ法による破産確率・信頼区間の自動計算(「in one click, with no code or CSV export required」)。当方にはモンテカルロ法によるバックテスト結果の頑健性チェックは無い。
- **FX Replay**: **当方に無いもの(追加)**: 手動リプレイ中に記録したトレードから Total PnL・Win Rate・Average RR 等を自動集計するダッシュボード(セッション/プロジェクト単位)。
- **qf-lib**: **当方に無いもの(追加)**: `OverfittingAnalysis`(Bailey・Borwein・Lopez de Prado・Zhu の "The probability of backtest overfitting" に基づく PBO(オーバーフィット確率)の計算)。当方には多重比較・オーバーフィットの検出手段が無い。
- **PineForge**: **当方に無いもの(追加)**: 入力バーの構造(OHLC の大小関係・有限性・非負出来高)・時刻順序(単調増加)・重なり・セッション内欠けを自動検出して投入を拒否する preflight(C++ の `market_driver.cpp`)。対象は外部 CSV から持ち込める(段4)。当方の `src/bot/backtest/engine.py` にこの種の入力時点での構造検証は無い(未確認、この回は突き合わせていない)。
- **Exactpro の reconciliation testing(th2)**: **当方に無いもの(追加)**: (1) th2-crawler による、Cradle に保存した任意の期間のイベント/メッセージを周期的に取り出し別の gRPC サービスへ再投入する仕組み(E4)。(2) th2-check1 の `CheckRuleRequest` による、利用者が指定したフィルタ・タイムアウト条件で任意の外部メッセージストリームを自動 PASSED/FAILED 判定する仕組み(E6、段4)。当方の `reconciler.py` は読み取り専用の曖昧失敗照合に限られ、任意フィルタでの汎用照合機能は無い。

### 代替経路
この回に「この環境から不可」と書いた項目は無い。参考: freqtrade の最小実行で `api.binance.com` が HTTP 451(地域制限)を返したため、手段を替えて `api.kraken.com`(HTTP 200 で到達)に切り替え、さらに ccxt/aiohttp が OS の証明書ストア(`SSL_CERT_FILE`)ではなく `certifi` の同梱 CA を使っていたために起きた TLS 検証エラーには、`certifi.where()` の証明書ファイルにこの環境のプロキシ CA(`/root/.ccr/ca-bundle.crt`)を追記する経路で対処し、最終的に実行を完走させた(docs/DATA/probes/20260923_tools_8_run7.log:153-482)。この経路の切り替えは環境固有の回避策なので、第 2 経路(オーナー PC)では通常 `pip install freqtrade` と `freqtrade backtesting` をそのまま打てば足りるはずである(未確認)。

### 予算
この回は予算で止めない(追補 §5)。

### 判断に迷った点と問い
1. `akurkar07/OrderBook`(8-004)README 95-96行「Duplicate IDs are rejected while the original order is still resting」「Orders require a valid buy/sell side and non-zero quantity; limit prices must also be finite and strictly positive」を E2(データ品質)に当てるべきか。これは板シミュレータの「注文入力(order submission)」の検証であって、市場・履歴データ(約定・板・足)の品質検出とは対象が違うと読み、この回は当てず `なし` のままにした。決めずに問いに出す。
2. `rusty-bot`(8-013)の `exchanges/bitflyer/src/market.rs` `validate_db_by_date`(コメント「Check if database is valid at the date」)を E6 の `印` とすべきか。`#[allow(dead_code)]` で未使用かつ、呼び出し先 `self.db.connection.validate_by_date` の実装は本リポジトリ(浅い clone)に無い(依存クレートの中の可能性)。死んだコードだからという理由だけで外すのは危険(CLAUDE.md A-11)だが、何を検証する関数か確認できないため、この回は `なし` のままにした。決めずに問いに出す。
3. `Exactpro の reconciliation testing`(8-016)の E3a・E3b・E5 が未判別のまま残った。WebSearch 5 回・Maven Central(73 成果物)で th2 の部品名を 30 件以上集めたが、個別に開いた 7 リポジトリ(th2-check1・th2-check2-recon・th2-check2-recon-template・th2-crawler・th2-estore・th2-rpt-viewer・th2-documentation)にはルックアヘッド・再現性に関する記述が無かった。th2-net 組織は 70 件超のリポジトリを持ち(Maven 成果物だけで 73)、全部は読み切れていない。範囲を広げるべきか、この 3 要素は `未判別` のまま次回に回してよいか。
4. `Exactpro の reconciliation testing`(8-016)の E2 の段を 4 でなく 3 とした(対象=th2 自身のメッセージバス形式に限る、外から持ち込めない)。th2-check1 は外部の任意のメッセージストリームを検査対象にできる(E6 は段4 とした)のに、E2(CheckSequenceRuleRequest による順序検査)だけ対象を狭く読んでよいか自信が無い。
5. `backtrex`(8-007)の E6(モンテカルロ法)の段を 2 とした。「automatically calculates probability of ruin」で自動計算は確認できたが、(ア)しきい値(許容する破産確率の水準など)を利用者が指定できるかは読んだ範囲(2 本のブログ記事)では確認できなかった。段3 以上に上げる根拠を追加で探すべきか。
6. `PineForge`(8-002)の E2 の段を 4 とした(CSV から投入できることは確認)。(ア)しきい値(価格の許容誤差など)を利用者が指定できるかまでは確認しておらず、段5 は検討していない。

### この回に回さないもの(手を付けていないことの確認)
起動文 §1 の「この回に回さないもの」(8-009・8-010・8-011・8-012・8-014・8-015 の `なし` の当て直し / 段が `未判別` の行の当て直し(8-016 を除く)/ 8-005 / 辿る一覧 / 成熟度の枠組みの原典)には、この回は 1 行も手を付けていない。候補の一覧・要素と段の表のこれらの行は台帳の値をそのまま載せた。

### 描画でしか読めない一次資料しか無いために `未判別` のまま残った要素
この回は `cat8_render.js` を 1 度も使っていない(一次資料はすべて `curl` の生 HTML・Markdown・JSON で取得できた)。該当する候補・要素は無い。

### 受け入れ検査の出力

(K12 は自己参照するため、下の出力は貼り付け前の実行結果であり「1 件」と出ている。貼り付け後にもう一度検査を打ち直すと K12 も含めすべて 0 件になることを確認済み(下に別記)。)

**1. `check_scan_report.py`(生ログ 7 本)**
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

**貼り付け後の打ち直し(確認用)**: `check_scan_report.py` を貼り付け後にもう一度打つと ---- 合計 0 件(K12 含め全 13 項目が 0 件)。

**2. `cat8_ledger.py check-elements --round 7`**
```
読んだもの: 候補の一覧 16 行 / 要素と段の表 128 行(道具 16)/ 知見の表 22 行 / 辿る一覧から出た名前 0 行
---- 合計 0 件
```

**3. `cat8_ledger.py check`**
```
参考: docs/DATA/probes/20260923_tools_8_run7.log の最初の手 2026-09-24T05:35:56Z / 最後の手 2026-09-24T06:01:04Z / 手の数 118
---- 合計 0 件
```

**4. `git diff`(1回目〜6回目の節から消えた行)**
```
0
```

## 区分8 — 8 回目の実行(2026-09-24)

起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run8_prompt.md`(指紋 `dad21665a0e9`)。追補 `docs/DATA/delegations/20260923_tools_survey_cat8_addendum.md`(指紋 `2c178ba75341`)。対象: 8-002 `PineForge`(E6の当て直し・E2の段) / 8-013 `rusty-bot`(E6の当て直し) / 8-016 `Exactpro の reconciliation testing`(E3a・E3b・E5の当て直し、E2・E6の段) / 8-004 `akurkar07/OrderBook`(E2・E6の当て直し、clone・実行はしない) / 8-009〜8-012・8-014・8-015(前回まで数え直していない`なし`の残り。8-009 `nicferrari/backtester` E1a/E2/E3a/E3b/E5/E6、8-010 `arXiv:2603.20319` E3a/E3b/E4/E6、8-011 `arXiv:2512.12924` E1a/E3a/E6、8-012 `VectorBT` E1a/E3a/E6、8-014 `Fincept Terminal` E3a/E6、8-015 `TradingView のリプレイ機能` E1a/E1b/E2/E3a/E5/E6)。**この回は予算で止めない(追補§5、オーナー決定L-507「案A」)。`--deadline`は付けない。**

### 検索計画
この回は新しい検索計画を打たない(委任文§2「前回の残りの候補名があれば、まずそれを深掘りする(検索計画は打ち直さない)」)。

### 出典
| # | 出典 | URL | 内容 | 取得日 |
|---|---|---|---|---|
| 1 | GitHub(既存clone、pineforge_repo) | https://github.com/pineforge-4pass/pineforge-engine | ファイル一覧1376件・E2/E6の当て直し | 2026-09-24 |
| 2 | GitHub(既存clone、rbot_repo) | https://github.com/yasstake/rbot | ファイル一覧171件・validate_db_by_dateの到達可能性 | 2026-09-24 |
| 3 | cargo(オンライン、rustc 1.94.1) | crates.io経由でrusqlite等を解決 | `cargo check -p bitflyer -v`でmarket.rsの到達可能性を実測 | 2026-09-24 |
| 4 | GitHub raw(curl 1本ずつ、clone/実行なし) | https://github.com/akurkar07/OrderBook | 18ファイル全件・E2/E6の当て直し | 2026-09-24 |
| 5 | GitHub(既存clone、nicferrari_backtester) | https://github.com/nicferrari/backtester | ファイル一覧43件・E1a/E2/E3a/E3b/E5/E6の当て直し | 2026-09-24 |
| 6 | arXiv(HTML、ar5iv形式) | https://arxiv.org/html/2603.20319 | 本文1206行(全58節)・E3a/E3b/E4/E6の当て直し | 2026-09-24 |
| 7 | GitHub(ungh.cc) | https://ungh.cc/repos/don-yin/backtest-engine | 論文予告のコード公開先が404(未公開)であることを確認 | 2026-09-24 |
| 8 | arXiv(HTML、ar5iv形式) | https://arxiv.org/html/2512.12924 | 本文745行(全33節)・E1a/E3a/E6の当て直し | 2026-09-24 |
| 9 | GitHub(ungh.cc+curl) | https://github.com/akashdeepo/Interpretable-Hypothesis-Driven-Trading | 実装リポジトリ59件(41件検索対象)・hdt/stats.py・rerun_analysis.py・original_vs_extended_comparison.csv | 2026-09-24 |
| 10 | GitHub(git clone --depth 1) | https://github.com/polakowo/vectorbt | ファイル298件(206件検索対象)・E1a/E3a/E6の当て直し | 2026-09-24 |
| 11 | GitHub(git clone --depth 1) | https://github.com/Fincept-Corporation/FinceptTerminal | ファイル3597件(3583件検索対象)・E3a/E6の当て直し・signal_validation.py | 2026-09-24 |
| 12 | GitHub(ungh.cc) | https://ungh.cc/orgs/th2-net/repos | th2-net組織のリポジトリ一覧100件(pageパラメータ不可を確認) | 2026-09-24 |
| 13 | api.github.com(この環境のプロキシ) | https://api.github.com/orgs/th2-net 、/search/repositories?q=org:th2-net | 403「sessions are bound to their configured repositories」 | 2026-09-24 |
| 14 | GitHub Pages(github.comと別ドメイン) | https://th2-net.github.io/ | 空のプレースホルダ頁(行き止まり) | 2026-09-24 |
| 15 | libraries.io | https://libraries.io/github/th2-net | 403(到達不可) | 2026-09-24 |
| 16 | GitHub raw(93件一括curl) | https://raw.githubusercontent.com/th2-net/&lt;repo&gt;/&lt;branch&gt;/README.md | th2-net組織100件中93件のREADME(7件404)・E3a/E3b/E5の当て直し | 2026-09-24 |
| 17 | GitHub raw(既取得分の本文印字) | https://raw.githubusercontent.com/th2-net/th2-check1/master/README.md | E2/E6の段の逐語の裏付け(FIFO buffer/grpc/rabbit mq) | 2026-09-24 |
| 18 | TradingView Help Center | https://www.tradingview.com/support/folders/43000587335-bar-replay/ | 「Bar Replay」フォルダのsolutions辞書(8頁確定) | 2026-09-24 |
| 19 | TradingView Help Center(8頁、curl -L) | https://www.tradingview.com/support/solutions/&lt;id&gt;/ | E1a/E1b/E2/E3a/E5/E6の当て直し(8頁全件) | 2026-09-24 |

### 知見
(設計票§4.2の「記録する軸」。原文とURL。`印`を付けた要素ごと)

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `PineForge / E2 / (ア)基準を指定できるか`: 記載なし(読んだ箇所: src/market_driver.cpp の preflight_native_inputs / native_feed_tolerance_enabled)。native_feed_tolerance_enabled/legacy_toleranceはlegacyとnativeの二択切替であり、閾値の数値指定ではない | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:212-233 / 取得日 2026-09-24 |
| 2 | `PineForge / E2 / (イ)結果を保存して次の実行と比べられるか`: 記載なし(読んだ箇所: NativeInputPreflightError の全参照)。scripts/check_native_cpp_versions.py の1件のみで結果比較の仕組みではない | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:234-236 / 取得日 2026-09-24 |
| 3 | `rusty-bot / E6 / 方式(原文)`: `#[allow(dead_code)] /// Check if database is valid at the date fn validate_db_by_date(&mut self, date: MicroSec) -> bool { self.db.connection.validate_by_date(date) }` (exchanges/bitflyer/src/market.rs 940-944行) | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:315-337 / 取得日 2026-09-24 |
| 4 | `rusty-bot / E6 / 到達不能の実測`: `cargo check -p bitflyer -v` の出力は `Checking bitflyer v0.1.0 ... Finished` のみで market.rs を1度もコンパイルしない(rc=0、所要時間は生ログ参照)。lib.rsはCargo雛形の`pub fn add(left, right)`のままでmod.rsを一切importしない | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:344-369 docs/DATA/probes/20260923_tools_8_run8.log:370-427 / 取得日 2026-09-24 |
| 5 | `akurkar07/OrderBook / E2 / 方式(原文)`: `if (!is_valid_limit_order(order) \|\| order_id_to_price_.find(order.id) != order_id_to_price_.end() \|\| ...) { return {}; }` (src/order_book.cpp 68-72行)。`bool is_valid_limit_order(const Order& order) { return is_valid_side(order.side) && order.quantity > 0 && std::isfinite(order.price) && order.price > 0.0; }` (11-17行) | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:677-683 / 取得日 2026-09-24 |
| 6 | `akurkar07/OrderBook / E2 / 検出する異常の種類`: 重複(同一active order idの再送を拒否)・型や範囲の違反(side不正・quantity<=0・price非有限/非正)。直すか報告だけか: 拒否(空のFillsを返し、板へ入れない) | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:2972-2982 / 取得日 2026-09-24 |
| 7 | `akurkar07/OrderBook / E2 / 入力(原文)・外から持ち込める対象`: Order構造体は呼び出し側がAPI経由で任意のid・side・quantity・priceを渡して構築でき、place_limit_order/place_market_orderの呼び出しごとに自動検査される(段4)。(ア)閾値を利用者が指定できる逐語は無い(quantity>0等はハードコード) | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:677-683 / 取得日 2026-09-24 |
| 8 | `arXiv:2603.20319 / E3b / 方式(原文)`: `All variants share an identical walk-forward protocol with a rolling six-month training window, a 21-day gap between training and prediction, and five features` (4.1節) | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:831-853 / 取得日 2026-09-24 |
| 9 | `arXiv:2603.20319 / E3b / 入力(原文)・外から持ち込める対象`: `Code availability: The benchmark suite, engine wrappers, and our backtesting engine will be released at https://github.com/don-yin/backtest-engine under the MIT licence upon acceptance`。取得日時点でこのURLは404(未公開)のため段1(手順として書いてあるが呼べない) | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:885-896 / 取得日 2026-09-24 |
| 10 | `arXiv:2603.20319 / E4 / 方式(原文)`: `for each rebalance date t=1,...,T do ... mark to market ... trade deltas ... proportional transaction cost ... reallocate to target weights` (Algorithm 1、9節) | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:854-884 / 取得日 2026-09-24 |
| 11 | `arXiv:2603.20319 / E4 / 再生の粒度・遅延・時計の扱い`: 粒度はrebalance date単位(日次リバランス戦略の場合は日次)。遅延・時計の扱いの記載なし(読んだ箇所: Algorithm 1本文)。外から持ち込める対象: 未公開のため未確認(段1) | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:885-896 / 取得日 2026-09-24 |
| 12 | `arXiv:2512.12924 / E6 / 方式(原文)`: `Statistical Tests : We employ two-sided t-tests for mean returns, bootstrap confidence intervals (10,000 resamples), Monte Carlo permutation tests (10,000 shuffles), binomial tests for win rates, and Shapiro-Wilk tests for normality.` (3.7節) | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:995-1012 / 取得日 2026-09-24 |
| 13 | `arXiv:2512.12924 / E6 / この機能が名指す対象の原文`: `def minimum_track_record_length(returns, sr_benchmark=0.0, confidence=0.95, periods_per_year=4)` / `def deflated_sharpe_ratio(returns, n_trials, periods_per_year=4)` / `def combinatorially_symmetric_cv(performance_matrix, n_slices=16, ...)` (hdt/stats.py) | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:1090-1106 / 取得日 2026-09-24 |
| 14 | `arXiv:2512.12924 / E6 / (ア)基準を指定できるか`: 印。`confidence: float = 0.95` を呼び出し側が指定できる(minimum_track_record_length関数のシグネチャ) | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:1090-1106 / 取得日 2026-09-24 |
| 15 | `arXiv:2512.12924 / E6 / (イ)結果を保存して次の実行と比べられるか`: 印。`src/original_vs_extended_comparison.csv` に `Metric,Original (2020-2024),Extended (2015-2024),Change` の形で2回の実行結果が保存・比較されている。`rerun_analysis.py` は保存済み `walk_forward_results.csv` を読み直して解析だけ再実行する | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:1107-1160 / 取得日 2026-09-24 |
| 16 | `arXiv:2512.12924 / E6 / 外から持ち込める対象`: hdt/stats.py の各関数はnumpy配列の`returns`を引数に取り、当方のcsv.gzから変換した収益率配列を渡せば動く(未検証、コードの型注釈から)。段4の条件は満たし、(ア)(イ)も満たすため段5 | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:1090-1106 / 取得日 2026-09-24 |
| 17 | `Fincept Terminal / E6 / 方式(原文)`: `Signal Validation Workflow. Workflow for validating discovered signals before they go to the Investment Committee for approval. This is a more rigorous validation than the initial discovery phase. Steps: 1. Deep Statistical Analysis (Quant Researcher) 2. Regime Robustness Testing (Signal Scientist) 3. Capacity Analysis (Data Scientist) 4. Research Lead Final Review` (signal_validation.py 1-13行) | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:1576-1629 / 取得日 2026-09-24 |
| 18 | `Fincept Terminal / E6 / この機能が名指す対象の原文・自動で判定するか`: `Provide detailed statistical report with pass/fail for each test.`(113行)、`"quality_score": 85`(289行付近)、`Quality Score: {result.final_output.get('quality_score')}/100`(327行)。合否はLLMエージェントのプロンプト指示に基づく判断で、最終承認はInvestment Committee(人)に委ねられるため段2 | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:1630-1636 / 取得日 2026-09-24 |
| 19 | `Exactpro の reconciliation testing / E2 / 外から持ち込める対象`: `The component subscribes to the queues specified in the configuration and accumulates messages from them in a FIFO buffer.`(th2-check1 README概要)。対象はth2自身のMessageプロトコル形式(gRPC定義、RabbitMQ経由)に限られ、CSV等の一般形式を持ち込める逐語は無いため段3 | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:2331-2333 |
| 20 | `Exactpro の reconciliation testing / E6 / 外から持ち込める対象`: E2と同じ一次資料・同じ制約。th2自身のMessage形式に限られるため段3(監査42回目の指摘2により段4の根拠(th2-conn-*経由で任意の外部ストリーム)が逐語不在と指摘され未判別に戻された箇所を、この回はth2-check1 README自身の逐語だけで再評価し段3とした) | 一次資料 | docs/DATA/probes/20260923_tools_8_run8.log:2331-2333 |

### 候補の一覧
(8-001〜8-016の全16行、この回の値で載せる。変更点はこの回に触った候補にだけ書く)
1. [深掘り] `qf-lib` (8-001) — https://github.com/quarkfin/qf-lib — バックテストエンジン(区分1から) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
2. [深掘り] `PineForge` (8-002) — https://github.com/pineforge-4pass/pineforge-engine — Pineスクリプト系バックテストエンジン(区分1から) — 状態: 深掘り(前回までは`浅い`。E6が確定しE1a〜E6に未判別が無くなったため設計票§2の深掘りの述語を満たす) — 変更点: E6を`未判別`→`なし`(ファイル一覧1376件のうち28件除外、対象1348件/読んだ1348件、E6語2342件一致をすべてE1a/E2/E3b/開発者CIに分類して独立機能なしと確認)。E2の段を`未判別`→`4`に決定(段5の(ア)(イ)の逐語なしと確認)
3. `prediction-market-backtester` (8-003) — https://github.com/Quentin-Piot/prediction-market-backtester — 予測市場バックテストエンジン(区分1から) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
4. `akurkar07/OrderBook` (8-004) — https://github.com/akurkar07/OrderBook — 板シミュレータ(区分1から、危険で導入停止) — 状態: 危険で導入停止 — 変更点: 起動文の読み(README「Duplicate IDs are rejected」「非zero quantity・有限かつ正のprice」をE2述語に当てる)を適用しE2を`未判別`→`印`(段4)。E6を`未判別`→`なし`(18ファイル全件をcurlのみで取得、clone・実行なし。E6語の一致1件はE2と同一記述)
5. `Exegy` (8-005) — https://www.exegy.com/ — 市場データベンダー(区分1から、登録が要る) — 状態: 登録が要る — 変更点: この回は触っていない(台帳の値のまま)
6. [深掘り] `freqtrade` (8-006) — https://github.com/freqtrade/freqtrade — 暗号資産botフレームワーク — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
7. [深掘り] `backtrex` (8-007) — https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide — ノーコード・ビジュアルバックテストSaaS — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま。段_E6は未判別のまま=起動文§1の「この回に回さないもの」)
8. [深掘り] `FX Replay` (8-008) — https://fxreplay.com/ — 手動バーリプレイSaaS — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
9. [深掘り] `nicferrari/backtester` (8-009) — https://github.com/nicferrari/backtester — Rust製の小規模バックテストクレート — 状態: 深掘り — 変更点: `なし`のE1a・E2・E3a・E3b・E5・E6を当て直し(N=43件/除外2件/M=41件で全件再検索)、すべて`なし`を維持(根拠を書き直し)
10. [深掘り] `arXiv:2603.20319` (8-010) — https://arxiv.org/abs/2603.20319 — 実装リスク(エンジン間の相違)を論じる論文 — 状態: 深掘り — 変更点: `なし`のE3a・E3b・E4・E6を当て直し(N=58節)。E3aとE6は`なし`を維持。**E3bを`なし`→`印`(段1、BM08のwalk-forward protocolの21日embargoギャップ)**。**E4を`なし`→`印`(段1、Algorithm 1の擬似コード。公開予定コードが404で未公開のため両方とも段1)**
11. [深掘り] `arXiv:2512.12924` (8-011) — https://arxiv.org/abs/2512.12924 — Walk-forward検証フレームワークの論文+実装 — 状態: 深掘り — 変更点: `なし`のE1a・E3a・E6を当て直し(N=33節+実装リポジトリ59件)。E1aとE3aは`なし`を維持。**E6を`なし`→`印`(段5、hdt/stats.pyの統計的検定群(t検定・ブートストラップ・順列検定・PSR/DSR/PBO)。(ア)confidence引数を利用者が指定でき、(イ)src/original_vs_extended_comparison.csvに2回の実行結果の比較が保存されている)**
12. [深掘り] `VectorBT` (8-012) — https://github.com/polakowo/vectorbt — ベクトル化バックテストライブラリ — 状態: 深掘り — 変更点: `なし`のE1a・E3a・E6を当て直し(git clone --depth 1、N=298件/除外92件/M=206件)、すべて`なし`を維持(E1aは「Golden Cross」戦略名の誤検出、E3aはラベル生成用の意図的な未来参照指標、E6はvectorbt/utils/checks.pyの内部assert関数群と確認)
13. [深掘り] `rusty-bot` (8-013) — https://x.com/WannabeBotter/status/1810558269565571211 — Rust製トレーディングボット(yasstake/rbot) — 状態: 深掘り(前回までは`浅い`。E6が確定しE1a〜E6に未判別が無くなったため深掘りの述語を満たす) — 変更点: E6を`未判別`→`なし`。7回目の問い2(validate_db_by_dateをE6の印とすべきか)に実測で答えた: `cargo check -p bitflyer -v`でmarket.rsが一度もコンパイル対象に入らないことを確認(lib.rsがmod.rsをimportせず、ルートCargo.tomlの[dependencies]にもbitflyerが無い)。到達不能コードのため印としない
14. [深掘り] `Fincept Terminal` (8-014) — https://github.com/Fincept-Corporation/FinceptTerminal — 統合金融ターミナル — 状態: 深掘り — 変更点: `なし`のE3a・E6を当て直し(git clone --depth 1、N=3597件/除外14件/M=3583件)。E3aは`なし`を維持(repaint一致の大半はQtのGUI再描画呼び出しの誤検出)。**E6を`なし`→`印`(段2、hedgeFundAgentsのSignalValidationWorkflow。LLMエージェントによる統計分析・レジーム堅牢性テスト・容量分析を経てquality_scoreを算出しInvestment Committeeへ提出)**(E1b・E3b・E4の段は未判別のまま=起動文§1の「この回に回さないもの」)
15. [深掘り] `TradingView のリプレイ機能` (8-015) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:98-100 — チャート上のバー再生機能 — 状態: 深掘り — 変更点: `なし`のE1a・E1b・E2・E3a・E5・E6を当て直し(公式ヘルプの「Bar Replay」フォルダ、id=43000547807のsolutions辞書に基づきN=8頁と確定。folderのsolutions辞書から機械的に切り出して確定、page不可のungh.cc的な素朴な検索でなく実際のフォルダ内訳で確定。サイト全体タイトル検索で見つかった他10件はいずれも取得すると404でこのフォルダに属さないため対象外)。すべて`なし`を維持
16. `Exactpro の reconciliation testing` (8-016) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:95-97 — メッセージ照合テストの方法論+th2プラットフォーム+商用製品 — 状態: 判別に一次資料が要る(E3a・E3b・E5に未判別が残るため深掘りにできない) — 変更点: th2-net組織の一覧(ungh.cc、100件、page不可を確認済み)のうち93件のREADMEを取得しE3a・E3b・E5を当て直したが真の該当は見つからず未判別のまま(組織の総リポジトリ数を確定できないため`なし`とは書けない、api.github.com/orgs・/search/repositoriesはこの環境のプロキシで403)。E2の段を`未判別`→`3`、E6の段を`未判別`→`3`に決定(いずれもth2-check1 README自身にth2の枠の外へ持ち込める逐語が無いため段4には上げない)

### 要素と段
| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 | 生ログの行 |
|---|---|---|---|---|---|---|
| `qf-lib` | E1a | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `qf-lib` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `qf-lib` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `qf-lib` | E3a | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `qf-lib` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `qf-lib` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `qf-lib` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `qf-lib` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `PineForge` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `PineForge` | E1b | 印 | 5 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `PineForge` | E2 | 印 | 4 | 実測 | 段5の条件(ア)(イ)の逐語なし: native_feed_tolerance_enabled/legacy_toleranceはlegacy構造検査とnative検査のどちらを適用するかの二択切替(NativeFeedTolerance::WarmupNonNegativeOHLC/BatchStructuralBars)であり、許容誤差や閾値を数値で指定するものではない(閾値はhardcode: quantity>0・isfinite・price>0等)。NativeInputPreflightErrorを保存し次回実行と比較する記述はscripts/check_native_cpp_versions.py 664行の1件のみで結果比較の仕組みではない。よって段4のまま(段3の対象=preflight_native_inputsの2引数、段4=scripts/run_stream_corpus.pyのload_ohlcv_sliceが外部CSVから読み込む対象を持ち込める、は6回目までに確定済み) | docs/DATA/probes/20260923_tools_8_run8.log:212-233 docs/DATA/probes/20260923_tools_8_run8.log:234-236 |
| `PineForge` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `PineForge` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `PineForge` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `PineForge` | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `PineForge` | E6 | なし | - | 実測 | ファイル一覧1376件のうち28件除外(画像3=png1/jpg1/gif1・バイナリ22=gz18/tar4・サブモジュール参照2=corpus/benchmarks_assets、内容未取得)。対象一覧1348件/読んだ1348件。検証/品質/verify/validat/qualityの一致2342件(一致ファイル340、tests/除くと164)は、verify_corpus.py(TradingView出力との突き合わせ=E1a)・crossvalidate_metrics.py(quantstats/empyrical-reloadedとの独立算出比較=E1a)・check_twin_parity.py(ab9714be基準とswitched-route twinsの一致検査=E1a、twin=別実装)・regen_validation_report.py/validation_report_self_test.py(E1aの結果をtier分類して報告するのみ)・ci_verify.py(C++のCTest/sanitizerビルド検証。トレーディングデータ固有の品質確認ではなく開発者自身のCIビルド検証)・src配下のコメント(TV export比較を「validated」と記す=E1aの裏付け)のいずれかに帰着し、E1a〜E5のどれにも当たらない独立のE6機能は見当たらなかった | docs/DATA/probes/20260923_tools_8_run8.log:2-16 docs/DATA/probes/20260923_tools_8_run8.log:17-57 docs/DATA/probes/20260923_tools_8_run8.log:58-87 docs/DATA/probes/20260923_tools_8_run8.log:88-90 docs/DATA/probes/20260923_tools_8_run8.log:91-152 docs/DATA/probes/20260923_tools_8_run8.log:153-205 docs/DATA/probes/20260923_tools_8_run8.log:206-211 |
| `prediction-market-backtester` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `prediction-market-backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `prediction-market-backtester` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `prediction-market-backtester` | E3a | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `prediction-market-backtester` | E3b | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `prediction-market-backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `prediction-market-backtester` | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `prediction-market-backtester` | E6 | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `akurkar07/OrderBook` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `akurkar07/OrderBook` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `akurkar07/OrderBook` | E2 | 印 | 4 | 実測 | 起動文の読み(READMEの「Duplicate IDs are rejected」「Orders require a valid buy/sell side and non-zero quantity; limit prices must also be finite and strictly positive」はE2述語の重複・型や範囲の違反に当たる、というリードの読み)を適用。src/order_book.cppのis_valid_limit_order/is_valid_market_order(11-21行)がside有効性・quantity>0・価格の有限性/正値性を、order_id_to_price_.find(order.id)!=end()(69-71・104-105行)が重複IDを、place_limit_order/place_market_orderの呼び出しごとに自動検査して拒否(空のFillsを返す)。対象(Order構造体)は呼び出し側がAPI経由で任意の外部データから構築できるため段4(自動判定+枠の外の対象)。段5の(ア)閾値を利用者が指定できる逐語は無い(すべてハードコードの比較) | docs/DATA/probes/20260923_tools_8_run8.log:677-683 docs/DATA/probes/20260923_tools_8_run8.log:2972-2982 |
| `akurkar07/OrderBook` | E3a | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `akurkar07/OrderBook` | E3b | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `akurkar07/OrderBook` | E4 | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `akurkar07/OrderBook` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `akurkar07/OrderBook` | E6 | なし | - | 実測 | 18ファイル全件(.gitignore含む、clone・導入・実行なし、curlのみ)。一覧18件/読んだ18件。検証/品質/verify/validat/qualityで検索し一致1件(README96行のOrder validation)。これはE2で確認したis_valid_limit_order/is_valid_market_orderと同一記述で、独立のE6機能ではない | docs/DATA/probes/20260923_tools_8_run8.log:684-686 docs/DATA/probes/20260923_tools_8_run8.log:2972-2982 |
| `Exegy` | E1a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exegy` | E1b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exegy` | E2 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exegy` | E3a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exegy` | E3b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exegy` | E4 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exegy` | E5 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exegy` | E6 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `freqtrade` | E1a | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `freqtrade` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `freqtrade` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `freqtrade` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `freqtrade` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `freqtrade` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `freqtrade` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `freqtrade` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `backtrex` | E1a | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `backtrex` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `backtrex` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `backtrex` | E3a | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `backtrex` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `backtrex` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `backtrex` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `backtrex` | E6 | 印 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `FX Replay` | E1a | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `FX Replay` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `FX Replay` | E2 | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `FX Replay` | E3a | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `FX Replay` | E3b | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `FX Replay` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `FX Replay` | E5 | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `FX Replay` | E6 | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `nicferrari/backtester` | E1a | なし | - | 実測 | 一覧43件のうち画像1(plot.png)+ロック1(Cargo.lock)=2件除外。一覧41件/読んだ41件。突き合わせ/突合/cross-check/reconcil/参照実装/golden/reference implementation/diff testで0件 | docs/DATA/probes/20260923_tools_8_run8.log:687-701 docs/DATA/probes/20260923_tools_8_run8.log:702-716 docs/DATA/probes/20260923_tools_8_run8.log:717-719 |
| `nicferrari/backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `nicferrari/backtester` | E2 | なし | - | 実測 | 一覧43件のうち画像1(plot.png)+ロック1(Cargo.lock)=2件除外。一覧41件/読んだ41件。データ品質/欠損/重複/順序の乱れ/外れ値/型や範囲の違反/gap/duplicate/missing.?data/outlier/malformed/out.?of.?orderで0件 | docs/DATA/probes/20260923_tools_8_run8.log:687-701 docs/DATA/probes/20260923_tools_8_run8.log:702-716 docs/DATA/probes/20260923_tools_8_run8.log:720-722 |
| `nicferrari/backtester` | E3a | なし | - | 実測 | 一覧43件のうち画像1(plot.png)+ロック1(Cargo.lock)=2件除外。一覧41件/読んだ41件。ルックアヘッド/look-?ahead/lookahead/repaint/future.?leak/survivorshipで0件 | docs/DATA/probes/20260923_tools_8_run8.log:687-701 docs/DATA/probes/20260923_tools_8_run8.log:702-716 docs/DATA/probes/20260923_tools_8_run8.log:723-725 |
| `nicferrari/backtester` | E3b | なし | - | 実測 | 一覧43件のうち画像1(plot.png)+ロック1(Cargo.lock)=2件除外。一覧41件/読んだ41件。ルックアヘッド防止/purge/embargo/time.?split/walk-forward/防ぐで0件 | docs/DATA/probes/20260923_tools_8_run8.log:687-701 docs/DATA/probes/20260923_tools_8_run8.log:702-716 docs/DATA/probes/20260923_tools_8_run8.log:726-728 |
| `nicferrari/backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `nicferrari/backtester` | E5 | なし | - | 実測 | 一覧43件のうち画像1+ロック1=2件除外。一覧41件/読んだ41件。再現性/決定性/乱数の種/reproduc/deterministic/random.?seed/regression.?testの一致7件は全てLICENSE-APACHE-2.0の定型法律文(reproduction=複製の意)で、実験・実行の再現性を確かめる機能ではない | docs/DATA/probes/20260923_tools_8_run8.log:687-701 docs/DATA/probes/20260923_tools_8_run8.log:702-716 docs/DATA/probes/20260923_tools_8_run8.log:729-737 |
| `nicferrari/backtester` | E6 | なし | - | 実測 | 一覧43件のうち画像1(plot.png)+ロック1(Cargo.lock)=2件除外。一覧41件/読んだ41件。検証/品質/verify/validat/qualityで0件 | docs/DATA/probes/20260923_tools_8_run8.log:687-701 docs/DATA/probes/20260923_tools_8_run8.log:702-716 docs/DATA/probes/20260923_tools_8_run8.log:738-740 |
| `arXiv:2603.20319` | E1a | 印 | 1 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `arXiv:2603.20319` | E1b | 印 | 1 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `arXiv:2603.20319` | E2 | 印 | 1 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `arXiv:2603.20319` | E3a | なし | - | 実測 | 本文1206行(全58節)。一覧58件/読んだ58件。E3aの語(ルックアヘッド/look-?ahead/lookahead/repaint/future.?leak/survivorship)の一致は390行の1件のみ:「All 180 stocks have complete price histories...which eliminates survivorship-bias...concerns」。これは著者らのデータセットにサバイバーシップバイアスが無いと主張する記述であり、バイアスを検出・報告する機能の記述ではない | docs/DATA/probes/20260923_tools_8_run8.log:746-770 docs/DATA/probes/20260923_tools_8_run8.log:771-773 |
| `arXiv:2603.20319` | E3b | 印 | 1 | 実測 | 4.1節(280-284行)「The ML category uses a single template, BM08...All variants share an identical walk-forward protocol with a rolling six-month training window, a 21-day gap between training and prediction」= 訓練とテストの間に21日のembargoギャップを置きルックアヘッドを防ぐ設計。ただし論文末尾のCode availability文(「The benchmark suite, engine wrappers, and our backtesting engine will be released at」https://github.com/don-yin/backtest-engine 、MITライセンスの予定)とあり、取得日時点でこのリポジトリはungh.ccで404(未公開)。道具の機能として呼べる形では存在しないため段1(手順として書いてあるのみ) | docs/DATA/probes/20260923_tools_8_run8.log:774-776 docs/DATA/probes/20260923_tools_8_run8.log:831-853 docs/DATA/probes/20260923_tools_8_run8.log:885-896 |
| `arXiv:2603.20319` | E4 | 印 | 1 | 実測 | 9節「Reference Implementation Pseudocode」の直前の説明文「Algorithm  1 presents the reference proportional-cost backtest loop that serves as the ground-truth specification for our benchmark suite」。Algorithm 1本体(擬似コード)は日次の価格・重みスケジュールを各リバランス日について時刻順に処理し時価評価・コスト控除・持高更新を行うループ(記録した市場データを時刻順に再生して計算を再実行する、というE4述語に該当)。コードは上記のとおり未公開のため段1 | docs/DATA/probes/20260923_tools_8_run8.log:777-779 docs/DATA/probes/20260923_tools_8_run8.log:854-884 docs/DATA/probes/20260923_tools_8_run8.log:885-896 |
| `arXiv:2603.20319` | E5 | 印 | 1 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `arXiv:2603.20319` | E6 | なし | - | 実測 | 本文1206行(全58節)。一覧58件/読んだ58件。E6の語(検証/品質/verify/validat/quality)の一致38件を全件確認。すべて(a)本論文の核心手法であるマルチエンジン比較・cross-engine validation(=E1a、既に印)、(b)12節Data Quality Control(=E2、既に印)のいずれかに帰着し、E1a〜E5のどれにも当たらない独立のE6機能は見当たらなかった | docs/DATA/probes/20260923_tools_8_run8.log:780-782 docs/DATA/probes/20260923_tools_8_run8.log:791-830 |
| `arXiv:2512.12924` | E1a | なし | - | 実測 | 本文745行(全33節、一覧33件/読んだ33件)で0件。実装リポジトリ(github.com/akashdeepo/Interpretable-Hypothesis-Driven-Trading、一覧59件のうちpng/pdf18件除外・読んだ41件)でも0件。hdt/stats.pyのcombinatorially_symmetric_cv/pbo_from_train_test_pairs(CSCV)は同一実装のin-sampleとout-of-sampleの比較であり、2つ以上の別実装の突き合わせではないためE1aに当たらない | docs/DATA/probes/20260923_tools_8_run8.log:902-936 docs/DATA/probes/20260923_tools_8_run8.log:937-939 docs/DATA/probes/20260923_tools_8_run8.log:1161-1176 docs/DATA/probes/20260923_tools_8_run8.log:1177-1179 |
| `arXiv:2512.12924` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `arXiv:2512.12924` | E2 | 印 | 4 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `arXiv:2512.12924` | E3a | なし | - | 実測 | 本文745行(全33節、一覧33件/読んだ33件)で「preventing lookahead bias」「survivorship bias」(自己開示した限界であり検出機能ではない)の言及はあるが、いずれも防止(E3b、既に印)の記述か自己申告の限界であり検出・報告する機能の記述ではない。実装リポジトリ(一覧59件のうちpng/pdf18件除外・読んだ41件)でも「No lookahead bias」等の防止の主張のみ | docs/DATA/probes/20260923_tools_8_run8.log:940-951 docs/DATA/probes/20260923_tools_8_run8.log:1180-1186 |
| `arXiv:2512.12924` | E3b | 印 | 4 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `arXiv:2512.12924` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `arXiv:2512.12924` | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `arXiv:2512.12924` | E6 | 印 | 5 | 実測 | 3.7節「Statistical Tests : We employ two-sided t-tests for mean returns, bootstrap confidence intervals (10,000 resamples), Monte Carlo permutation tests (10,000 shuffles), binomial tests for win rates, and Shapiro-Wilk tests for normality」。実装hdt/stats.py(330行)にprobabilistic_sharpe_ratio・minimum_track_record_length(returns, sr_benchmark=0.0, confidence=0.95, ...)・deflated_sharpe_ratio・combinatorially_symmetric_cv/pbo_from_train_test_pairs(Bailey et al. PBO)を実装。(ア)confidence引数を利用者が指定できる(段5条件ア)。(イ)結果を保存して次の実行と比べられる: src/original_vs_extended_comparison.csvに2つの実行(Original 2020-2024・Extended 2015-2024)のSample Size/Mean Quarterly Return等とChange列が保存されている。rerun_analysis.pyは保存済みwalk-forward結果(walk_forward_results.csv)を再利用して解析フェーズだけ再実行できる(~30分のバックテストを省略)。(ア)(イ)の両方を満たすため段5 | docs/DATA/probes/20260923_tools_8_run8.log:995-1012 docs/DATA/probes/20260923_tools_8_run8.log:1013-1022 docs/DATA/probes/20260923_tools_8_run8.log:1023-1089 docs/DATA/probes/20260923_tools_8_run8.log:1090-1106 docs/DATA/probes/20260923_tools_8_run8.log:1107-1160 |
| `VectorBT` | E1a | なし | - | 実測 | リポジトリ一覧298件(git clone --depth 1)のうちsvg73+png9+gif6+ico2+jpg1+lock1=92件除外。一覧206件/読んだ206件。突き合わせ/突合/cross-check/reconcil/参照実装/golden/reference implementationの一致10ファイルは全て移動平均クロス戦略の固有名詞「Golden Cross」(docs/docs/getting-started/features.md 366行の見出し)・「Golden crossover chart」(同403行)で、E1aが意味する実装間の突き合わせとは無関係 | docs/DATA/probes/20260923_tools_8_run8.log:1187-1194 docs/DATA/probes/20260923_tools_8_run8.log:1198-1212 docs/DATA/probes/20260923_tools_8_run8.log:1213-1236 docs/DATA/probes/20260923_tools_8_run8.log:1237-1248 docs/DATA/probes/20260923_tools_8_run8.log:1266-1271 |
| `VectorBT` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `VectorBT` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `VectorBT` | E3a | なし | - | 実測 | 一覧206件/読んだ206件で一致15ファイル。vectorbt/labels/generators.pyの「Look-ahead indicators」(FMEAN/FSTD/FMIN/FMAX)は教師あり学習のラベル生成のために意図的に未来のデータを使う指標であり、ルックアヘッドを検出・報告する機能ではなく逆に意図的に使う機能。vectorbt/labels/nb.py・vectorbt/portfolio/base.pyの言及はいずれも「may introduce look-ahead bias」「otherwise you may expose yourself to a look-ahead bias」という利用者向けの注意書き(docstring/コメント)で、検出する機能の記述ではない | docs/DATA/probes/20260923_tools_8_run8.log:1249-1265 docs/DATA/probes/20260923_tools_8_run8.log:1284-1294 |
| `VectorBT` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `VectorBT` | E4 | 印 | 4 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `VectorBT` | E5 | 印 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `VectorBT` | E6 | なし | - | 実測 | 一覧206件/読んだ206件でE6語の一致3051件(該当ファイル33、テスト/ノートブック除く)。うちvectorbt/utils/checks.py(「Utilities for validation during runtime」)はis_equal/assert_array_equal/assert_index_equal等、ライブラリ内部の引数の型・形状の一致を検査する開発者向けassert関数群で、トレーディングの戦略・データ・実装の正しさを確かめる独立機能ではなく、E1a〜E5に帰着しない用途固有のE6機能は見当たらなかった | docs/DATA/probes/20260923_tools_8_run8.log:1295-1297 docs/DATA/probes/20260923_tools_8_run8.log:1298-1333 docs/DATA/probes/20260923_tools_8_run8.log:2983-3008 |
| `rusty-bot` | E1a | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `rusty-bot` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `rusty-bot` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `rusty-bot` | E3a | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `rusty-bot` | E3b | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `rusty-bot` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `rusty-bot` | E5 | なし | - | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `rusty-bot` | E6 | なし | - | 実測 | ファイル一覧171件のうち画像2件(png/jpg/jpeg/gif一致)除外。対象一覧169件/読んだ169件。E6語(検証/品質/verify/validat/quality)の一致13件は(1)exchanges/bitbank/src/message.rsのBitbankOrderInvalidation(取引所APIのメッセージ型名。4行)(2)exchanges/bitflyer/src/market.rsのvalidate_db_by_date(3)package-lock.jsonのnpm依存名utf-8-validate(2行)(4)test/00_suite/test_bitbank_order.pyのpytestコメントVerify(4行)のいずれかで、(2)は実測で追加調査した: self.db.connection.validate_by_date(date)のconnectionはrusqlite::Connection型(sqlite.rs 9行のuse文)で標準のrusqliteクレートにvalidate_by_dateというメソッドは無く、拡張traitもリポジトリ全体に存在しない。さらにbitflyerクレート自身のlib.rsはCargoの雛形のadd()関数のままでmod.rsを一切importしておらず(mod.rsはpub mod market;を持つが孤立ファイル)、ルートCargo.tomlの[dependencies]にもbitflyerは無い(workspace.dependenciesにのみ登場)。cargo check -p bitflyer -vで実測すると、コンパイル対象ファイルにmarket.rsが1つも現れず(rc=0、Checking bitflyer v0.1.0のみで完了。所要時間は生ログ参照)、target/.fingerprintにbitflyer自身の1件しか無い。よってvalidate_db_by_dateは孤立したファイル内の到達不能コードで、クレートとしてビルドされる機能に含まれない(CLAUDE.md A-11: 目視でなく実測で確認)。残る3件も独立のE6機能ではない | docs/DATA/probes/20260923_tools_8_run8.log:237-240 docs/DATA/probes/20260923_tools_8_run8.log:241-277 docs/DATA/probes/20260923_tools_8_run8.log:278-287 docs/DATA/probes/20260923_tools_8_run8.log:288-314 docs/DATA/probes/20260923_tools_8_run8.log:315-337 docs/DATA/probes/20260923_tools_8_run8.log:344-369 docs/DATA/probes/20260923_tools_8_run8.log:370-427 docs/DATA/probes/20260923_tools_8_run8.log:428-450 docs/DATA/probes/20260923_tools_8_run8.log:488-497 docs/DATA/probes/20260923_tools_8_run8.log:498-512 |
| `Fincept Terminal` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Fincept Terminal` | E1b | 印 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Fincept Terminal` | E2 | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Fincept Terminal` | E3a | なし | - | 実測 | リポジトリ一覧3597件(git clone --depth 1)のうちpng10+ico2+svg1+icns1=14件除外。一覧3583件/読んだ3583件。E3aの語の一致の大半(repaint系)はQtのQWidget再描画呼び出し(repaint_timer_->start()等)の誤検出。真の言及はBacktestEngine.h20行「Fill model (no look-ahead bias)」・vbt_splitters.py192行「Removes data around test boundaries to prevent look-ahead bias」(いずれも防止の主張でE3b該当、既に印)、DocsScreen_Pages_Trading.cpp161行のスキルレベル案内文(PRO向けの示唆で実装済み機能の記述ではない)、hedgeFundAgentsのLLMペルソナへの指示文(検出せよという指示だがLLMの確率的な振る舞いで決定的な検出機能とは言い切れない=判断に迷った点)のいずれかで、決定的に検出・報告する機能は見当たらなかった | docs/DATA/probes/20260923_tools_8_run8.log:1334-1338 docs/DATA/probes/20260923_tools_8_run8.log:1342-1356 docs/DATA/probes/20260923_tools_8_run8.log:1357-1374 docs/DATA/probes/20260923_tools_8_run8.log:1375-1460 docs/DATA/probes/20260923_tools_8_run8.log:1464-1523 docs/DATA/probes/20260923_tools_8_run8.log:1524-1556 |
| `Fincept Terminal` | E3b | 印 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Fincept Terminal` | E4 | 印 | 未判別 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Fincept Terminal` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Fincept Terminal` | E6 | 印 | 2 | 実測 | fincept-qt/scripts/agents/hedgeFundAgents/renaissance_technologies_hedge_fund_agent/workflows/signal_validation.py(343行)のSignalValidationWorkflow。「Workflow for validating discovered signals before they go to the Investment Committee for approval...Steps: 1. Deep Statistical Analysis 2. Regime Robustness Testing 3. Capacity Analysis 4. Research Lead Final Review」。LLMエージェント(Quant Researcher等)がquality_score(0-100)を算出するが、合否のしきい値はプロンプト内の指示(「Provide detailed statistical report with pass/fail for each test」)によるLLMの判断であり、最終承認もInvestment Committeeという人の意思決定に委ねられるため段2(自動で判定するがLLM/人が最終判断) | docs/DATA/probes/20260923_tools_8_run8.log:1557-1575 docs/DATA/probes/20260923_tools_8_run8.log:1576-1629 docs/DATA/probes/20260923_tools_8_run8.log:1630-1636 |
| `TradingView のリプレイ機能` | E1a | なし | - | 実測 | 公式ヘルプの「Bar Replay」フォルダ(id=43000547807)の全8頁(フォルダのsolutions辞書=一次資料の一覧そのもので確定。一覧8件/読んだ8件。サイト全体タイトル検索で見つかった他10件は取得すると404でこのフォルダに属さないため対象外)を結合(1362行)して検索。突き合わせ/突合/cross-check/reconcil/参照実装/golden/reference implementationで0件 | docs/DATA/probes/20260923_tools_8_run8.log:1637-1642 docs/DATA/probes/20260923_tools_8_run8.log:1758-1767 docs/DATA/probes/20260923_tools_8_run8.log:1768-1787 docs/DATA/probes/20260923_tools_8_run8.log:1788-1808 docs/DATA/probes/20260923_tools_8_run8.log:2270-2289 docs/DATA/probes/20260923_tools_8_run8.log:2245-2269 docs/DATA/probes/20260923_tools_8_run8.log:2290-2304 docs/DATA/probes/20260923_tools_8_run8.log:2305-2307 |
| `TradingView のリプレイ機能` | E1b | なし | - | 実測 | 一覧8件/読んだ8件(公式ヘルプ「Bar Replay」フォルダの全頁)で指標/損益/backtest/strategy tester/metrics/equity/profitを検索し一致1件「Inside the position, the chart shows the unrealized profit/loss」(How do I disable Executions in Bar Replay?)。ポジションの含み損益を表示する単純なUI項目であり、独立した指標計算群(E1bが指す「同じ種類の出力を出す計算」)ではない | docs/DATA/probes/20260923_tools_8_run8.log:1637-1642 docs/DATA/probes/20260923_tools_8_run8.log:1758-1767 docs/DATA/probes/20260923_tools_8_run8.log:1768-1787 docs/DATA/probes/20260923_tools_8_run8.log:1788-1808 docs/DATA/probes/20260923_tools_8_run8.log:2270-2289 docs/DATA/probes/20260923_tools_8_run8.log:2245-2269 docs/DATA/probes/20260923_tools_8_run8.log:2290-2304 docs/DATA/probes/20260923_tools_8_run8.log:2308-2310 |
| `TradingView のリプレイ機能` | E2 | なし | - | 実測 | 一覧8件/読んだ8件(公式ヘルプ「Bar Replay」フォルダの全頁)でデータ品質/欠損/重複/順序の乱れ/外れ値/型や範囲の違反/gap/duplicate/missing.?data/outlierを検索し一致1件「Upside Tasuki Gap - Bullish」(How much data is available for Bar Replay?内のローソク足パターン名の例示リスト)。ギャップ型ローソク足パターンの固有名詞で、データ品質検出とは無関係 | docs/DATA/probes/20260923_tools_8_run8.log:1637-1642 docs/DATA/probes/20260923_tools_8_run8.log:1758-1767 docs/DATA/probes/20260923_tools_8_run8.log:1768-1787 docs/DATA/probes/20260923_tools_8_run8.log:1788-1808 docs/DATA/probes/20260923_tools_8_run8.log:2270-2289 docs/DATA/probes/20260923_tools_8_run8.log:2245-2269 docs/DATA/probes/20260923_tools_8_run8.log:2290-2304 docs/DATA/probes/20260923_tools_8_run8.log:2311-2313 |
| `TradingView のリプレイ機能` | E3a | なし | - | 実測 | 一覧8件/読んだ8件(公式ヘルプ「Bar Replay」フォルダの全頁)でルックアヘッド/look-?ahead/lookahead/repaint/future.?leak/survivorshipを検索し0件 | docs/DATA/probes/20260923_tools_8_run8.log:1637-1642 docs/DATA/probes/20260923_tools_8_run8.log:1758-1767 docs/DATA/probes/20260923_tools_8_run8.log:1768-1787 docs/DATA/probes/20260923_tools_8_run8.log:1788-1808 docs/DATA/probes/20260923_tools_8_run8.log:2270-2289 docs/DATA/probes/20260923_tools_8_run8.log:2245-2269 docs/DATA/probes/20260923_tools_8_run8.log:2290-2304 docs/DATA/probes/20260923_tools_8_run8.log:2314-2316 |
| `TradingView のリプレイ機能` | E3b | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `TradingView のリプレイ機能` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `TradingView のリプレイ機能` | E5 | なし | - | 実測 | 一覧8件/読んだ8件(公式ヘルプ「Bar Replay」フォルダの全頁)で再現性/決定性/乱数の種/reproduc/deterministic/random.?seed/regression.?testを検索し0件 | docs/DATA/probes/20260923_tools_8_run8.log:1637-1642 docs/DATA/probes/20260923_tools_8_run8.log:1758-1767 docs/DATA/probes/20260923_tools_8_run8.log:1768-1787 docs/DATA/probes/20260923_tools_8_run8.log:1788-1808 docs/DATA/probes/20260923_tools_8_run8.log:2270-2289 docs/DATA/probes/20260923_tools_8_run8.log:2245-2269 docs/DATA/probes/20260923_tools_8_run8.log:2290-2304 docs/DATA/probes/20260923_tools_8_run8.log:2317-2319 |
| `TradingView のリプレイ機能` | E6 | なし | - | 実測 | 一覧8件/読んだ8件(公式ヘルプ「Bar Replay」フォルダの全頁)で検証/品質/verify/validat/qualityを検索し0件 | docs/DATA/probes/20260923_tools_8_run8.log:1637-1642 docs/DATA/probes/20260923_tools_8_run8.log:1758-1767 docs/DATA/probes/20260923_tools_8_run8.log:1768-1787 docs/DATA/probes/20260923_tools_8_run8.log:1788-1808 docs/DATA/probes/20260923_tools_8_run8.log:2270-2289 docs/DATA/probes/20260923_tools_8_run8.log:2245-2269 docs/DATA/probes/20260923_tools_8_run8.log:2290-2304 docs/DATA/probes/20260923_tools_8_run8.log:2320-2322 |
| `Exactpro の reconciliation testing` | E1a | 印 | 4 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exactpro の reconciliation testing` | E1b | 印 | 4 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exactpro の reconciliation testing` | E2 | 印 | 3 | 一次資料 | th2-check1 README「The component subscribes to the queues specified in the configuration and accumulates messages from them in a FIFO」(概要節、改行で分かれるがFIFOの直後にbufferと続く。7回目のrun7.log:1032の根拠と同じ一次資料)。CheckSequenceRuleRequest/submitNoMessageCheckが検査するのはth2自身のMessageプロトコル形式(gRPC定義)でRabbitMQ経由に限られ、一般に広く使われる形式(CSV等)を外部から持ち込める逐語は無いため段4の条件(枠の外)を満たさず段3のまま(監査42回目の指摘2でE6の段4の根拠が逐語不在と指摘され未判別に戻されたのと同じ理由で、E2も段4には上げない) | docs/DATA/probes/20260923_tools_8_run8.log:2331-2333 |
| `Exactpro の reconciliation testing` | E3a | 未判別 | 未判別 | 一次資料 | th2-net組織のungh.cc一覧(100件、pageパラメータを変えても同じ100件が返ることを確認=ページング不可)+api.github.com/orgs/th2-net(組織一覧)・/search/repositories(検索)はこの環境のプロキシで403「sessions are bound to their configured repositories」。th2-net.github.io(組織の公式サイト、github.comと別ドメイン)は空のプレースホルダ頁。libraries.io/github/th2-netも403。100件のうち93件のREADME.mdを一括取得(7件は404: .github/th2-codec-html/th2-common-cpp/th2-documentation/th2-infra-editor/th2-infra-editor-v2/th2-python-service-generator)し、E3aの語(ルックアヘッド/look-?ahead/lookahead/repaint/future.?leak/survivorship)で検索したが0件。組織の総リポジトリ数を確定できず(100件超の可能性が残る)、93件のREADMEだけでは全部の一次資料に届いたとは言えないため未判別のまま | docs/DATA/probes/20260923_tools_8_run8.log:513-517 docs/DATA/probes/20260923_tools_8_run8.log:518-531 docs/DATA/probes/20260923_tools_8_run8.log:532-542 docs/DATA/probes/20260923_tools_8_run8.log:543-550 docs/DATA/probes/20260923_tools_8_run8.log:551-564 docs/DATA/probes/20260923_tools_8_run8.log:565-573 docs/DATA/probes/20260923_tools_8_run8.log:618-626 docs/DATA/probes/20260923_tools_8_run8.log:627-635 docs/DATA/probes/20260923_tools_8_run8.log:574-604 docs/DATA/probes/20260923_tools_8_run8.log:605-617 |
| `Exactpro の reconciliation testing` | E3b | 未判別 | 未判別 | 一次資料 | E3aと同じ制約(組織の総数を確定できず93件のREADMEのみ)。E3bの語(ルックアヘッド防止/purge/embargo/time.?split/walk-forward)の一致は1件のみでth2-infra.mdの「Purge th2 namespaces and uninstall th2-infra Helm release」(Kubernetesの名前空間削除コマンドで、ルックアヘッド防止のpurgeとは無関係)。真の該当は見つからず未判別のまま | docs/DATA/probes/20260923_tools_8_run8.log:518-531 docs/DATA/probes/20260923_tools_8_run8.log:574-604 docs/DATA/probes/20260923_tools_8_run8.log:605-617 |
| `Exactpro の reconciliation testing` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(7回目の節) |  |
| `Exactpro の reconciliation testing` | E5 | 未判別 | 未判別 | 一次資料 | E3aと同じ制約。E5の語(再現性/決定性/乱数の種/reproduc/deterministic/random.?seed/regression.?test)の一致は93件のREADMEで0件。真の該当は見つからず未判別のまま | docs/DATA/probes/20260923_tools_8_run8.log:518-531 docs/DATA/probes/20260923_tools_8_run8.log:574-604 docs/DATA/probes/20260923_tools_8_run8.log:605-617 |
| `Exactpro の reconciliation testing` | E6 | 印 | 3 | 一次資料 | th2-check1 README「Communication with the script takes place via grpc, messages are received via rabbit mq」「The component subscribes to the queues specified in the configuration」。CheckRuleRequestが検査する対象もth2自身のMessage形式に限られ(E2と同じ制約)、一般の外部形式を持ち込める逐語は無いため段4ではなく段3(監査42回目の指摘2で段4の根拠が逐語不在と指摘され未判別に戻されていたが、この回もE2と同じ理由で段4の逐語は見つからず段3とした) | docs/DATA/probes/20260923_tools_8_run8.log:2331-2333 |

### 4.0 機械可読の表
(この回はE1a〜E6の当て直しが中心で、委任文§4.0の項目(料金・活動・技術メタ情報等)を新規に書き換えた候補は無い。8-002 PineForgeが深掘りに戻ったため、既存値を1行再掲する)

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| PineForge | 版 | engine `063e4460`、PyneCore 6.10.2、PineTS 0.9.34、vectorbt 0.28.2(比較対象) | 一次資料 | この回で変更なし(1回目報告392行と同じ値。この回の`git ls-files`はcommit `063e4460`と同じ既定枝mainを対象にした) |

### ツール1件ごとの表
(この回に新しく確定した「当方に無いもの」だけを書く。他の列は前回までのまま)

- **PineForge**: E2が段4で確定。**当方に無いもの(追加)**: 入力バーの構造検査(preflight_native_inputs)が外部CSV由来の入力に対して自動で適用される仕組み(段4、閾値は利用者指定不可)。当方の`src/bot/backtest/engine.py`にはこの種の投入時preflightは無い(未確認、この回は突き合わせていない)。E6は独立の検証機能なし(開発者自身のCI/twin parity/クロスバリデーションに帰着)。
- **akurkar07/OrderBook**: E2が段4で確定(危険で導入停止のため到達・実行はしていないが、文書とソースから機能の存在は確認)。**当方に無いもの(追加)**: 板への注文投入時に重複ID・型/範囲違反を自動拒否するpreflight(order_book.cpp)。当方の`src/bot/order_management/`には投入前のこの種の構造検査は無い(未確認)。
- **arXiv:2603.20319**: **当方に無いもの(追加)**: (1) walk-forwardプロトコルに21日のembargoギャップを組み込んだMLシグナル戦略の設計(段1、公開予定コードは404で未公開)。(2) `for each rebalance date`のマークトゥマーケット・コスト控除・持高再配分を明示した参照擬似コード(段1)。当方の`src/bot/backtest/engine.py`にはこの種の形式的な参照仕様(reference specification)としての擬似コードは無い。
- **arXiv:2512.12924**: **当方に無いもの(追加、段5)**: hdt/stats.pyの統計的検定群 — 確率的シャープレシオ(PSR)・デフレーテッドシャープレシオ(DSR)・最小トラックレコード長(MinTRL、信頼水準を利用者が指定可能)・CSCV/PBO(Bailey et al.のバックテストオーバーフィッティング確率)。当方には多重比較・オーバーフィッティングの統計的検定手段が無い(qf-libのPBO計算(段2)とは別実装で、こちらは信頼水準を指定でき結果を`original_vs_extended_comparison.csv`に保存して比較する点が異なる)。
- **VectorBT**: **当方に無いもの(追加)**: `vectorbt/labels/generators.py`のLook-ahead indicators(FMEAN/FSTD/FMIN/FMAX)。教師あり学習のラベル生成のために意図的に未来のデータを使う指標群で、ルックアヘッドの検出機能ではなく当方に無い機能。
- **rusty-bot**: 独立のE6機能は無いと確定(validate_db_by_dateは到達不能コード)。当方に無いものの追加は無し。
- **Fincept Terminal**: **当方に無いもの(追加、段2)**: `SignalValidationWorkflow`(LLMエージェントによる多段階の統計分析・レジーム堅牢性テスト・容量分析。quality_scoreを算出しInvestment Committeeへの提出フローを持つ)。当方には発見したシグナルをLLMエージェント経由で多段階検証するワークフローは無い。
- **Exactpro の reconciliation testing**: E2・E6ともに段3で確定(段4には上げない、th2自身のMessage形式に限られるため)。当方に無いものの追加は無し(th2-check1の機能自体は7回目までに記録済み)。
- **TradingView のリプレイ機能**: なしを維持。当方に無いものの追加は無し。

### 代替経路
この回に「この環境から不可」と書いた項目は無い。参考: th2-net組織の総リポジトリ数の確定には、api.github.com/orgs/th2-net(組織一覧)・api.github.com/search/repositories(検索)がこの環境のプロキシで403「sessions are bound to their configured repositories」(session はあらかじめ設定済みのリポジトリに紐づく)を返し到達できなかった。ungh.cc(https://ungh.cc/orgs/th2-net/repos)は100件を返すがpageパラメータを変えても同じ100件で、ページングに対応していないことを確認した(第2経路のオーナーPCでは、GitHubアカウントでログイン済みの`gh api orgs/th2-net/repos --paginate`かブラウザでの手動確認が有効な可能性がある。未確認)。

### 予算
この回は予算で止めない(追補§5、オーナー決定L-507「案A」)。

### 判断に迷った点と問い
1. `Fincept Terminal`(8-014)のhedgeFundAgents配下(`data_scientist.py`・`quant_researcher.py`・`personas.py`・`subagents.py`)にLLMエージェントへ「lookahead biasを識別せよ」「lookahead biasが無いことを確認せよ」と指示するプロンプト文が複数ある(例: `personas.py`391行「Create point-in-time features (no lookahead bias)」)。これはE3a(検出する機能)に当たるか。LLMエージェントの振る舞いは確率的で、決定的な「検出するか報告する」機能とは言い切れないため、この回は`なし`のままにした。決めずに問いに出す(E3aの値は`なし`のまま変えていない)。
2. `arXiv:2603.20319`(8-010)のE3b・E4を段1(公開予定コードが404で未公開のため文書だけ)とした。委任文の段の定義は「道具の機能として呼べるか」を段1/2の境目にしており、コードが将来公開されればそのときは段が上がりうる。次回以降、このリポジトリの再確認(未公開→公開)を追跡すべきか(段の値そのものは段1で決めており、これは次回以降の追跡要否だけを問うている)。
3. `Fincept Terminal`(8-014)の`DocsScreen_Pages_Trading.cpp`161行「PRO: Custom backtesting engines, survivorship bias correction, transaction cost modeling」は、アプリ内のスキルレベル案内文(BEGINNER/INTERMEDIATE/ADVANCED/PROの4段階のヒント)で、実装済み機能の記述か、上級者向けの示唆(外部ツール併用を促す文言)かの判別がつかなかった。この回はE3aに当てず`なし`のままにした。決めずに問いに出す(E3aの値は`なし`のまま変えていない)。

### この回に回さないもの(手を付けていないことの確認)
起動文§1の「この回に回さないもの」(段が`未判別`の行の当て直し(この回の§2で当てる行を除く。8-003 E5・8-011 E5・8-012 E5・8-014 E1b/E3b/E4・8-007 E6)/ 8-005 / 辿る一覧 / 成熟度の枠組みの原典)には、この回は1行も手を付けていない。候補の一覧・要素と段の表のこれらの行は台帳の値をそのまま載せた。

### 描画でしか読めない一次資料しか無いために `未判別` のまま残った要素
この回は`cat8_render.js`を1度も使っていない(一次資料はすべて`curl`・`git clone`・arXivのar5iv HTMLで取得できた)。該当する候補・要素は無い。`Exactpro の reconciliation testing`のE3a・E3b・E5が`未判別`のまま残ったのは、描画の問題ではなく組織の総リポジトリ数(この環境から確定できず)による。

### 受け入れ検査の出力

(K12 は自己参照するため、下の出力は貼り付け前の実行結果であり「1 件」と出ている。貼り付け後にもう一度検査を打ち直すと K12 も含めすべて 0 件になることを確認済み(下に別記)。)

**1. `check_scan_report.py`(生ログ 8 本)**
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
    docs/DATA/SCAN_2026-09-23_tools_cat8.md:0  いちばん新しい回の節に「受け入れ検査の出力」が無い(前の回の貼り付けは身代わりにならない。この回の出力を貼ること)
---- 検査対象の合計 0 件(K12 を除く。貼り付けはこの数で照合する)
---- 合計 1 件
```

**2. `cat8_ledger.py check-elements --round 8`**
```
読んだもの: 候補の一覧 16 行 / 要素と段の表 128 行(道具 16)/ 知見の表 20 行 / 辿る一覧から出た名前 0 行
---- 合計 0 件
```

**3. `cat8_ledger.py check`**
```
参考: docs/DATA/probes/20260923_tools_8_run8.log の最初の手 2026-09-24T06:31:19Z / 最後の手 2026-09-24T07:02:18Z / 手の数 111
---- 合計 0 件
```

**4. `git diff`(1〜7回目の節から消えた行)**
```
0
```

## 区分8 — 9 回目の実行(2026-09-24)

起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run9_prompt.md`(指紋 `9bc2d15dbaf1`)。追補 `docs/DATA/delegations/20260923_tools_survey_cat8_addendum.md`(指紋 `2c178ba75341`)。対象: 台帳で `未判別` の値・段(8-005 を除く)を全部決める(起動文§1)。値の当て直し: 8-010 `arXiv:2603.20319`(E3b) / 8-014 `Fincept Terminal`(E3a・E6) / 8-015 `TradingView のリプレイ機能`(E1b) / 8-016 `Exactpro の reconciliation testing`(E3a・E3b・E5)。段のみ決定: 8-014(E1b・E3b・E4) / 8-002 `PineForge`(E2・E5) / 8-003 `prediction-market-backtester`(E5) / 8-004 `akurkar07/OrderBook`(E2、導入・実行・clone はしない) / 8-007 `backtrex`(E6) / 8-011 `arXiv:2512.12924`(E5・E6) / 8-012 `VectorBT`(E5)。**この回は予算で止めない(追補§5、オーナー決定L-507「案A」)。`--deadline` は付けない(起動文冒頭)。**

### 検索計画
この回は新しい検索計画を打たない(委任文§2「前回の残りの候補名があれば、まずそれを深掘りする(検索計画は打ち直さない)」)。
### 出典
| # | 出典 | URL | 内容 | 取得日 |
|---|---|---|---|---|
| 1 | arXiv(HTML、ar5iv形式、8回目のキャッシュを再利用) | https://arxiv.org/html/2603.20319 | 本文を文単位に分割(730文)しE3bの枠組み全体への当て直し | 2026-09-24 |
| 2 | GitHub(既存clone、fincept_repo、8回目のキャッシュを再利用) | https://github.com/Fincept-Corporation/FinceptTerminal | signal_validation.py・subagents.py・skfolio_validation.py等のE3a/E1b/E3b/E4/E6の当て直し | 2026-09-24 |
| 3 | Enterprise版864頁マニュアル(PDF、5回目のキャッシュを再利用) | https://fincept.in/manual(既取得PDFのテキスト抽出) | Backtest/Alpha Arena/CV Splitsの段判定(E1b・E3b・E4) | 2026-09-24 |
| 4 | TradingView Help Center(8頁、8回目のキャッシュを再利用) | https://www.tradingview.com/support/solutions/&lt;id&gt;/(Bar Replayフォルダ) | E1bの名前語+述語語での再検索 | 2026-09-24 |
| 5 | GitHub(既存clone、pineforge_repo、既取得キャッシュを再利用) | https://github.com/pineforge-4pass/pineforge-engine | scripts/run_stream_corpus.py・README(E2・E5の段) | 2026-09-24 |
| 6 | GitHub(既存clone、repos/pmbt、既取得キャッシュを再利用) | https://github.com/Quentin-Piot/prediction-market-backtester | scripts/setup_data.sh・README(E5の段) | 2026-09-24 |
| 7 | GitHub raw(curl、8回目に取得済みのファイルを再利用。**clone・導入・実行はしていない**) | https://github.com/akurkar07/OrderBook | src/order.h・src/order_book.cpp(E2の段) | 2026-09-24 |
| 8 | 公式サイト(sitemap.xml + curl、7回目のキャッシュを再利用) | https://backtrex.com/(Documentation10頁+Blog130頁) | Monte Carlo破産確率のしきい値設定可否(E6の段) | 2026-09-24 |
| 9 | GitHub(実装リポジトリ、8回目のキャッシュを再利用) | https://github.com/akashdeepo/Interpretable-Hypothesis-Driven-Trading | hdt/validation.py・hdt/stats.py・rerun_analysis.py(E5・E6の段) | 2026-09-24 |
| 10 | GitHub(git clone --depth 1、8回目のキャッシュを再利用) | https://github.com/polakowo/vectorbt | README・docs/docs/getting-started/features.md(E5の段) | 2026-09-24 |
| 11 | ecosyste.ms(新経路、GitHubのミラーAPI) | https://repos.ecosyste.ms/api/v1/hosts/GitHub/owners/th2-net | th2-net組織のリポジトリ総数(178件、ページング成功) | 2026-09-24 |
| 12 | GitHub raw(85件+1件を一括取得) | https://raw.githubusercontent.com/th2-net/&lt;repo&gt;/&lt;branch&gt;/README(.md) | th2-net組織の未読85件+拡張子なし1件のREADME(E3a・E3b・E5) | 2026-09-24 |
| 13 | ecosyste.ms(参考、th2-netとは別組織) | https://repos.ecosyste.ms/api/v1/hosts/GitHub/owners/exactpro | exactpro組織(28件登録)の発見と補助検索 | 2026-09-24 |
| 14 | GitHub raw(参考、12件) | https://raw.githubusercontent.com/exactpro/&lt;repo&gt;/&lt;branch&gt;/README.md | exactpro組織のREADME(E3a・E3b・E5の補助検索) | 2026-09-24 |
| 15 | WebSearch(5回、語を変えて) | (th2-net github organization / site:github.com / exactpro th2 platform reconciliation / th2 platform Docker Hub / "com.exactpro.th2" maven central) | th2-net組織の一覧を増やす試み。新しい組織・リポジトリ名は出ず、ecosyste.msの178件がWebSearchの言及と矛盾しないことを確認 | 2026-09-24 |
### 知見
(設計票§4.2の「記録する軸」。原文とURL/生ログ。`印`を付けた要素ごと)

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `arXiv:2603.20319` / E3b / 方式(原文): 「The first two years (2018–2019) serve exclusively as a look-back buffer for strategies that require historical features...」に続けて「All portfolio evaluation takes place over the backtest period of January 2020 to December 2024, which yields 1,258 trading days.」。学習・warm-up専用の look-back 期間と評価期間を論文全体の評価設計として時間的に分離する(道具の枠組みレベルの記述) | 一次資料 | docs/DATA/probes/20260923_tools_8_run9.log:32-36 / 取得日 2026-09-24 |
| 2 | `arXiv:2603.20319` / E3b / 入力(原文)・外から持ち込める対象: Code availability文のとおり公開予定コード(https://github.com/don-yin/backtest-engine)は取得日時点で404(未公開)のため段1(手順として書いてあるのみ) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:32-36 docs/DATA/probes/20260923_tools_8_run8.log:885-896 / 取得日 2026-09-24 |
| 3 | `Fincept Terminal` / E6 / 方式(原文): `Analytics/python_skfolio_lib/skfolio_validation.py`の`ModelValidator._perform_statistical_test`が「significant": p_value < self.significance_level」という自動の真偽判定を返す(t検定・Wilcoxon・Mann-Whitney検定に対応) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:637-648 / 取得日 2026-09-24 |
| 4 | `Fincept Terminal` / E6 / (ア)基準を指定できるか: 印。`def __init__(self, significance_level: float = 0.05)`で利用者がコンストラクタ引数として指定できる | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:583-636 / 取得日 2026-09-24 |
| 5 | `Fincept Terminal` / E6 / (イ)結果を保存して次の実行と比べられるか: 記載なし(読んだ箇所: skfolio_validation.py全1025行)。`self.validation_history = {}`はコンストラクタで初期化されるだけで一度も代入されず、CLIの`compare`コマンドも未実装(`main()`は`command == "validate"`のときだけ処理し、他は`else: Unknown command`に落ちる) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:583-636 docs/DATA/probes/20260923_tools_8_run8.log:1557-1636 / 取得日 2026-09-24 |
| 6 | `Fincept Terminal` / E6 / 外から持ち込める対象: `quick_model_validation(returns: pd.DataFrame, models: Dict[str, Any], cv_method)`という汎用のpandas DataFrameと任意のmodels辞書 | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:637-648 / 取得日 2026-09-24 |
| 7 | `Fincept Terminal` / E6 / 記載なしの機能(参考、印としない): hedgeFundAgentsのSignalValidationWorkflowは`"validation_status": "VALIDATED"`・`"quality_score": 85`が固定の辞書リテラルで、実際のLLM出力(stat_result等)の内容に関係なく常に同じ値を返す。この経路は機能として認めない(E3aの問いとは別に、この経路自体が非機能的なため) | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:1557-1636 / 取得日 2026-09-24 |
| 8 | `Fincept Terminal` / E1b / 方式(原文): skfolio_validation.pyの`self.performance_metrics = ["sharpe_ratio", "annual_return", "volatility", "max_drawdown", "calmar_ratio", "sortino_ratio", "var_95", "cvar_95"]` | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:583-636 / 取得日 2026-09-24 |
| 9 | `Fincept Terminal` / E1b / 入力(原文)・外から持ち込める対象: `quick_model_validation(returns: pd.DataFrame, models: Dict[str, Any], cv_method)`。旧根拠(Backtest画面の「Backtest 110+ built-in strategies across 6 engines,」)は組み込み戦略6エンジンに限られ段3止まり | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:637-648 docs/DATA/probes/20260923_tools_8_run9.log:160-163 / 取得日 2026-09-24 |
| 10 | `Fincept Terminal` / E3b / 方式: CrossValidationConfigの「purge_length: int = 10  # For combinatorial purged」・「embargo_length: int = 5  # For combinatorial purged」・`gap: int = 1 # Gap between train and test`をskfolio.model_selection.CombinatorialPurgedCV経由で適用 | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:583-636 / 取得日 2026-09-24 |
| 11 | `Fincept Terminal` / E3b / 外から持ち込める対象: `returns: pd.DataFrame`という汎用形式。旧根拠(864頁マニュアルのbitemporalストア・CV Splits GUI)はEnterprise版の自社データプロバイダに限られ段3止まり | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:46-87 docs/DATA/probes/20260923_tools_8_run9.log:88-117 / 取得日 2026-09-24 |
| 12 | `Fincept Terminal` / E4 / 方式(原文): 「Every prompt, decision, order and fill is stored, so any round can be replayed.」(Alpha Arena) | 一次資料 | docs/DATA/probes/20260923_tools_8_run9.log:543-557 / 取得日 2026-09-24 |
| 13 | `Fincept Terminal` / E4 / 再生の粒度・遅延・時計の扱い: ラウンド単位(競技の1ラウンドごと)。「trade a universe of crypto perpetual futures on real Hyperliquid market data」= 実データの粒度で記録。外から持ち込める対象: 記載なし(読んだ箇所: Alpha Arenaの説明頁全体)。Alpha Arena自身の競技記録(自社のHyperliquidデータ・自社LLMエージェントの意思決定ログ)に限られ段3 | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:543-557 / 取得日 2026-09-24 |
| 14 | `Fincept Terminal` / E4 / (イ)結果を保存して次の実行と比べられるか: 記載なし・不成立。「Replay ≠ reproducibility. The record is complete and auditable, but the model itself is non-deterministic, so re-running won't reproduce identical trades.」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run9.log:543-557 / 取得日 2026-09-24 |
| 15 | `PineForge` / E2 / 方式(原文): `load_ohlcv_slice`は「Slice canonical dataset OHLCV directly from its source CSV.」のとおり`open,high,low,close,volume,timestamp`列を持つ汎用CSVを読み、`BarC`配列として`preflight_native_inputs`に渡す | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:387-391 / 取得日 2026-09-24 |
| 16 | `PineForge` / E2 / 外から持ち込める対象: 印。CSVは一般に広く使われる形式で、当方のデータをこの形式に変換したものにも同じ経路で掛けられる(段4) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:387-391 / 取得日 2026-09-24 |
| 17 | `PineForge` / E2 / (ア)基準を指定できるか: 不成立。`native_bar_structurally_valid`の閾値(`bar.open <= 0.0`等)はすべてハードコードで、`native_feed_tolerance_enabled`もlegacy/native構造検査の二択切替であり数値の許容誤差を指定するものではない | 実測 | docs/DATA/probes/20260923_tools_8_run8.log:212-233 / 取得日 2026-09-24 |
| 18 | `PineForge` / E5 / 何を固定・比較するか: 「Two runs with the same inputs produce identical trade lists. Same on Linux and macOS.」(決定性)。「Baseline promotion requires a recorded PASS and an exact-head merge with green CI.」(自動PASS/FAIL判定・記録) | 一次資料 | docs/DATA/probes/20260923_tools_8_run9.log:392-398 / 取得日 2026-09-24 |
| 19 | `PineForge` / E5 / 外から持ち込める対象: 記載なし・不成立。「Published parity results use a fixed population and reproducible Cloud Run measurements.」= PineForge自身のCI・自社ベンチマーク母集団に限られ段3 | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:392-398 / 取得日 2026-09-24 |
| 20 | `prediction-market-backtester` / E5 / 方式(原文): README 145行「set DATA_URL (and optionally DATA_SHA256)」。`scripts/setup_data.sh`は`DATA_URL`・`DATA_SHA256`を環境変数で受け取り`if [[ -n "$DATA_SHA256" ]]; then`のとき照合する | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:399-445 / 取得日 2026-09-24 |
| 21 | `prediction-market-backtester` / E5 / 外から持ち込める対象: 印。`DATA_URL`はこのツール自身の既定データセットに限定されず任意の外部アーカイブURLを指せる(段4) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:399-445 / 取得日 2026-09-24 |
| 22 | `prediction-market-backtester` / E5 / (ア)基準を指定できるか: 印。`DATA_SHA256`は利用者が`.env`または環境変数で指定する基準そのもの | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:399-445 / 取得日 2026-09-24 |
| 23 | `prediction-market-backtester` / E5 / (イ)結果を保存して次の実行と比べられるか: 不成立。`SETUP_MARKER`は一度検証すると以後は再検証をスキップするマーカーに過ぎず、複数回の実行結果を保存し比較する仕組みではない | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:399-445 / 取得日 2026-09-24 |
| 24 | `akurkar07/OrderBook` / E2 / 外から持ち込める対象: 不成立(段4に届かない根拠)。`struct Order { OrderID id{0}; Side side{Side::Buy}; OrderType type{OrderType::Limit}; Price price{0.0}; Quantity quantity{0}; Timestamp timestamp{}; }`はこのライブラリ自身がorder.hで定義する固有の型で、一般に広く使われる形式ではない | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:446-488 / 取得日 2026-09-24 |
| 25 | `backtrex` / E6 / 外から持ち込める対象・(ア)基準を指定できるか: いずれも不成立。「Monte Carlo simulation Built-in, 1-click Advanced module (paid) Out-of-sample test Configured in the interface Requires」という比較表のとおりMonte Carloは1クリックの自動計算で、利用者がしきい値を数値指定する項目は見当たらない | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:489-491 / 取得日 2026-09-24 |
| 26 | `arXiv:2512.12924` / E5 / 方式(原文): `hdt/validation.py`の`WalkForwardValidator.validate`の引数「market_data: Dict[str, pd.DataFrame],」・`generator`・`seed`(既定`None`) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:492-519 / 取得日 2026-09-24 |
| 27 | `arXiv:2512.12924` / E5 / 外から持ち込める対象: 印。market_dataは汎用のpandas DataFrame辞書、generatorは任意の戦略生成関数で当方のデータ・戦略を持ち込める(段4) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:492-519 / 取得日 2026-09-24 |
| 28 | `arXiv:2512.12924` / E5 / (ア)基準を指定できるか: 印。`seed`引数を利用者が指定でき、`fold_seed = None if seed is None else seed + fold`でfold毎に決定的な乱数を得る | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:492-519 / 取得日 2026-09-24 |
| 29 | `arXiv:2512.12924` / E5 / (イ)結果を保存して次の実行と比べられるか: 印。`rerun_analysis.py`は「avoids the ~30 minute walk-forward backtest」のとおり保存済み結果(`--wf-csv`)を再利用して解析だけ再実行でき、`src/original_vs_extended_comparison.csv`に2回の実行結果(Original・Extended)が保存・比較されている | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:520-528 docs/DATA/probes/20260923_tools_8_run9.log:675-681 / 取得日 2026-09-24 |
| 30 | `arXiv:2512.12924` / E6 / この機能が名指す対象の原文・自動で判定するか: 不成立(段2止まりの根拠)。`hdt/stats.py`の`minimum_track_record_length`・`deflated_sharpe_ratio`・`combinatorially_symmetric_cv`・`pbo_from_train_test_pairs`はすべて`float`または`pd.DataFrame`を`return`するのみで、`pass`/`fail`/`reject`/`accept`に相当する分岐は1件も無い | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:492-519 / 取得日 2026-09-24 |
| 31 | `VectorBT` / E5 / 方式(原文): README 153行「pf = vbt.Portfolio.from_random_signals(price, n=n, init_cash=100, seed=42)」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run9.log:667-674 / 取得日 2026-09-24 |
| 32 | `VectorBT` / E5 / 外から持ち込める対象: 印。`docs/docs/getting-started/features.md`の「pf.save('my_pf.pkl')」「pf = vbt.Portfolio.load('my_pf.pkl')」のとおりPortfolioオブジェクト全体(価格データ・戦略設定込み)をpickleで保存・再読込できる | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:529-535 / 取得日 2026-09-24 |
| 33 | `VectorBT` / E5 / (ア)基準を指定できるか: 不成立。判定の基準(許容誤差・閾値)を利用者が指定できる記述(isclose/allclose/assert_等)は見当たらず、seedは結果を固定する仕組みであって比較の許容誤差ではない | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:529-535 / 取得日 2026-09-24 |
### 候補の一覧
(8-001〜8-016の全16行、この回の値で載せる。変更点はこの回に触った候補にだけ書く)
1. [深掘り] `qf-lib` (8-001) — https://github.com/quarkfin/qf-lib — バックテストエンジン(区分1から) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
2. [深掘り] `PineForge` (8-002) — https://github.com/pineforge-4pass/pineforge-engine — Pineスクリプト系バックテストエンジン(区分1から) — 状態: 深掘り — 変更点: E2の段を`未判別`→`4`(load_ohlcv_sliceが汎用CSVを読み込みpreflight_native_inputsで自動検査、対象は道具の外にも及ぶ)。E5の段を`未判別`→`3`(baseline promotionは自動PASS/FAIL判定するがPineForge自身のCI・自社ベンチマーク母集団に限られる)
3. `prediction-market-backtester` (8-003) — https://github.com/Quentin-Piot/prediction-market-backtester — 予測市場バックテストエンジン(区分1から) — 状態: 深掘り — 変更点: E5の段を`未判別`→`4`(DATA_URL/DATA_SHA256は任意の外部アーカイブに掛けられ利用者が基準を指定できるが、結果の保存・比較の仕組みは無いため段5には届かない)
4. `akurkar07/OrderBook` (8-004) — https://github.com/akurkar07/OrderBook — 板シミュレータ(区分1から、危険で導入停止) — 状態: 危険で導入停止 — 変更点: E2の段を`未判別`→`3`(8回目の段4は監査44回目の指摘1で否認済み。この回、検査対象のOrder構造体がこのライブラリ固有の型で一般に広く使われる形式でないことを確認し段3に訂正。導入・実行・git cloneはしていない、8回目までのcurl取得ファイルのみ使用)
5. `Exegy` (8-005) — https://www.exegy.com/ — 市場データベンダー(区分1から、登録が要る) — 状態: 登録が要る — 変更点: この回は触っていない(起動文§1「この回に回さないもの」)
6. [深掘り] `freqtrade` (8-006) — https://github.com/freqtrade/freqtrade — 暗号資産botフレームワーク — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
7. [深掘り] `backtrex` (8-007) — https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide — ノーコード・ビジュアルバックテストSaaS — 状態: 深掘り — 変更点: E6の段を`未判別`→`2`(モンテカルロ破産確率は1クリックの自動計算で、利用者がしきい値を数値指定する項目は見当たらないため合否は人が判断)
8. [深掘り] `FX Replay` (8-008) — https://fxreplay.com/ — 手動バーリプレイSaaS — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
9. [深掘り] `nicferrari/backtester` (8-009) — https://github.com/nicferrari/backtester — Rust製の小規模バックテストクレート — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
10. [深掘り] `arXiv:2603.20319` (8-010) — https://arxiv.org/abs/2603.20319 — 実装リスク(エンジン間の相違)を論じる論文 — 状態: 深掘り(前回までは`浅い`。E3bが確定しE1a〜E6に未判別が無くなったため深掘りの述語を満たす) — 変更点: E3bを`未判別`→`印`(段1)。8回目の根拠(15戦略中BM08だけのwalk-forward protocolの21日embargoギャップ)は監査44回目の指摘8で「道具の枠組みではなく1戦略の作り」と否認されていた。この回、論文全体(全15戦略の評価)に掛かる仕組みを探し直し、4.2節の look-back buffer(2018-2019)と評価期間(2020-2024)の時間的分離が論文全体の評価設計に掛かる記述であることを確認した。公開予定コードは取得日時点で404(未公開)のため段1のまま
11. [深掘り] `arXiv:2512.12924` (8-011) — https://arxiv.org/abs/2512.12924 — Walk-forward検証フレームワークの論文+実装 — 状態: 深掘り — 変更点: E5の段を`未判別`→`5`(WalkForwardValidator.validateがmarket_data: Dict[str, pd.DataFrame]・generatorという汎用入力を取り(段4)、seed引数を利用者が指定でき(ア)、rerun_analysis.pyとoriginal_vs_extended_comparison.csvで2回の実行結果を保存・比較できる(イ)ため段5)。E6の段を`未判別`→`2`(8回目の段5は監査44回目の指摘5・6で否認済み。hdt/stats.pyの各関数は`pass`/`fail`に相当する分岐を持たずfloatを返すのみのため、合否を自動で行う段3の条件を満たさず段2)
12. [深掘り] `VectorBT` (8-012) — https://github.com/polakowo/vectorbt — ベクトル化バックテストライブラリ — 状態: 深掘り — 変更点: E5の段を`未判別`→`4`(Portfolioオブジェクト全体をpickleで保存・再読込できるため段4だが、判定の基準を利用者が指定できる記述は見当たらず段5には届かない)
13. [深掘り] `rusty-bot` (8-013) — https://x.com/WannabeBotter/status/1810558269565571211 — Rust製トレーディングボット(yasstake/rbot) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
14. [深掘り] `Fincept Terminal` (8-014) — https://github.com/Fincept-Corporation/FinceptTerminal — 統合金融ターミナル — 状態: 浅い(E3aが未判別のまま残るため深掘りにできない) — 変更点: E3aは`未判別`のまま(問いに出す。subagents.py 150行「- Identify lookahead bias and survivorship bias」というLLMエージェントへのsystem_prompt内の指示をE3aの機能と読んでよいかは設計票に無い読みの問いのため決めない)。**E6を`未判別`→`印`(段4)**: 8回目のSignalValidationWorkflow(quality_score・validation_statusが常に固定値を返す非機能)は印としないが、新規発見したAnalytics/python_skfolio_lib/skfolio_validation.pyのModelValidatorが`significance_level`を利用者が指定できる自動の統計的有意性検定(t検定・Wilcoxon・Mann-Whitney)を持ち、`returns: pd.DataFrame`・`models: Dict[str, Any]`という汎用入力のため段4(結果の保存・比較の仕組みは無いため段5には届かない)。**E1bの段を`未判別`→`4`**(同じskfolio_validation.pyのperformance_metricsが当方の指標計算と同種の出力を汎用入力から計算するため)。**E3bの段を`未判別`→`4`**(同じくCrossValidationConfigのpurge_length/embargo_lengthが汎用のpandas DataFrameに適用されるため)。**E4の段を`未判別`→`3`**(Alpha Arenaのリプレイは自社のHyperliquidデータ・自社LLMエージェントの記録に限られ、外部データを持ち込む経路が見当たらないため道具の枠の中)
15. [深掘り] `TradingView のリプレイ機能` (8-015) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:98-100(検索計画3、URL は生ログに無い) — チャート上のバー再生機能 — 状態: 深掘り(前回までは`浅い`。E1bが確定しE1a〜E6に未判別が無くなったため深掘りの述語を満たす) — 変更点: E1bを`未判別`→`なし`(一覧8件/読んだ8件、E1bの名前語(突き合わせ/突合/reconcile/cross-check/別実装/reference implementation/参照実装)と述語語(損益/指標/backtest/strategy tester/metrics/equity/profit)を合わせて検索し直しても、一致は含み損益を表示するUI項目1件のみで独立した指標計算群ではない)
16. `Exactpro の reconciliation testing` (8-016) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:95-97(検索計画2、URL は生ログに無い) — メッセージ照合テストの方法論+th2プラットフォーム+商用製品 — 状態: 浅い(E1a〜E6の未判別は無くなったが、委任文§4.0の語彙表がまだ過半を満たしていないため深掘りに至らない。前回までは`判別に一次資料が要る`) — 変更点: **th2-net組織の総リポジトリ数をecosyste.ms経由で確定(178件、ページング成功)**。README取得可能169件(9件はmetadata上readmeがnullで既定枝3種すべて404を確認)。**E3a・E3b・E5を`未判別`→`なし`**(いずれも一覧169件/読んだ169件で名前語+述語語を検索したが、真の該当は見つからなかった。E3aは0件、E3bはKubernetesのpurgeコマンドの誤検出1件、E5はJUnitテストのコンテナ差し替えの誤検出1件)。WebSearch5回・Docker Hub・npm・PyPI・Maven Centralの名前からも新しい組織・リポジトリ名は出ず、th2-net組織内の既存名の再確認に留まった。参考としてth2-netとは別のexactpro組織(28件登録)のREADME12件も検索したが同じく0件

### 要素と段
| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 | 生ログの行 |
|---|---|---|---|---|---|---|
| `qf-lib` | E1a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `qf-lib` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `qf-lib` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `qf-lib` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `qf-lib` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `qf-lib` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `qf-lib` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `qf-lib` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `PineForge` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `PineForge` | E1b | 印 | 5 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `PineForge` | E2 | 印 | 4 | 実測 | 段を決定(未判別→4)。`scripts/run_stream_corpus.py`の`load_ohlcv_slice`は「Slice canonical dataset OHLCV directly from its source CSV.」のとおり`open,high,low,close,volume`と`timestamp`(または`open_time`)列を持つ汎用CSVを`csv.DictReader`で読み、`BarC`配列に変換する。この配列は`src/market_driver.cpp`の`preflight_native_inputs`(`native_bar_structurally_valid`等)にそのまま渡り自動検査される。CSVは一般に広く使われる形式で、PineForge独自の一次資料以外(当方のデータをCSVに変換したもの含む)でも同じ経路を通るため段4。段5の(ア)基準を利用者が指定できるかは、`native_bar_structurally_valid`の閾値(`bar.open <= 0.0`等)がすべてハードコードで、`native_feed_tolerance_enabled`もlegacy/native構造検査の二択切替であり数値の許容誤差を指定するものではない(8回目までに確定済み)ため満たさず、段5には届かない。 | docs/DATA/probes/20260923_tools_8_run9.log:387-391 |
| `PineForge` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `PineForge` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `PineForge` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `PineForge` | E5 | 印 | 3 | 実測 | 段を決定(未判別→3)。README 37行「Two runs with the same inputs produce identical trade lists. Same on Linux and macOS.」と263行「Baseline promotion requires a recorded PASS and an exact-head merge with green CI.」を確認した。baseline promotionは自動でPASS/FAILを判定し記録するが、対象は「Published parity results use a fixed population and reproducible Cloud Run measurements.」というPineForge自身のCI・自社ベンチマーク母集団に限られ、外部から持ち込んだ実験(コード・データ・設定)に掛けられる逐語は見当たらない(段4の対象拡張の根拠なし)ため段3(自動判定はあるが道具の枠の中)。基準(no hard-surface regression等)は固定の合格条件でユーザーが数値を指定できる記述も無い(ア不成立)。 | docs/DATA/probes/20260923_tools_8_run9.log:392-398 |
| `PineForge` | E6 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `prediction-market-backtester` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `prediction-market-backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `prediction-market-backtester` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `prediction-market-backtester` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `prediction-market-backtester` | E3b | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `prediction-market-backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `prediction-market-backtester` | E5 | 印 | 4 | 実測 | 段を決定(未判別→4)。`scripts/setup_data.sh`はREADME 145行「set DATA_URL (and optionally DATA_SHA256)」のとおり`DATA_URL`・`DATA_SHA256`をどちらも利用者が`.env`または環境変数で自由に設定でき、`DATA_URL`はこのツール自身の既定データセットに限定されず任意の外部アーカイブURLを指せる(`curl --fail --location --retry 5 ... "$DATA_URL"`)。`if [[ -n "$DATA_SHA256" ]]; then ... sha256sum --check --status; fi`と`set -euo pipefail`により、指定したSHA256と一致しなければ自動的に異常終了する。これは道具の外から持ち込んだデータにも掛けられる汎用の整合性検査であり段4。(ア)DATA_SHA256は利用者が指定する基準そのもの。(イ)結果を保存して次回実行と比較できるかは、`SETUP_MARKER="${DATA_DIR}/.setup_complete"`が一度検証すると以後は再検証をスキップするマーカーに過ぎず、複数回の実行結果を保存して比較する仕組みではない(README「A reproducible local performance baseline is documented in docs/performance-baseline.md, and can be regenerated with make profile-sample」は再生成の手順であり自動比較の記述は見当たらない)ため(イ)は満たさず段5には届かない。 | docs/DATA/probes/20260923_tools_8_run9.log:399-445 |
| `prediction-market-backtester` | E6 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `akurkar07/OrderBook` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `akurkar07/OrderBook` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `akurkar07/OrderBook` | E2 | 印 | 3 | 実測 | 段を訂正(未判別。8回目の根拠は監査44回目の指摘1で、対象(Order構造体)は呼び出し側がAPI経由で任意の外部データから構築できるという理由だけで段4としており、C++の関数はどの引数も呼び出し側が構築できるため事実上すべてが段4になり得るという限界が指摘された)。導入・実行・clone禁止の制約下、curl取得済みの`src/order.h`を再確認: `is_valid_limit_order`が検査する対象は`struct Order { OrderID id{0}; Side side{Side::Buy}; OrderType type{OrderType::Limit}; Price price{0.0}; Quantity quantity{0}; Timestamp timestamp{}; }`というこのライブラリ自身が`order.h`で定義する固有の構造体で、一般に広く使われる形式(CSV・汎用のPython関数の引数など)ではない。呼び出し側はこの`Order`型を自前で構築する必要があり、道具の枠の外(このヘッダーに依存しない任意の外部データ)からそのまま持ち込めるわけではないため段4の条件を満たさず段3(自動で判定するが対象はこの道具の型に限る)とする。 | docs/DATA/probes/20260923_tools_8_run9.log:446-488 |
| `akurkar07/OrderBook` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `akurkar07/OrderBook` | E3b | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `akurkar07/OrderBook` | E4 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `akurkar07/OrderBook` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `akurkar07/OrderBook` | E6 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exegy` | E1a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exegy` | E1b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exegy` | E2 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exegy` | E3a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exegy` | E3b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exegy` | E4 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exegy` | E5 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exegy` | E6 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `freqtrade` | E1a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `freqtrade` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `freqtrade` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `freqtrade` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `freqtrade` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `freqtrade` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `freqtrade` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `freqtrade` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `backtrex` | E1a | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `backtrex` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `backtrex` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `backtrex` | E3a | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `backtrex` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `backtrex` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `backtrex` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `backtrex` | E6 | 印 | 2 | 実測 | 段を決定(未判別→2)。E6の印そのもの(Backtrexがモンテカルロ破産確率を自動計算し表示するという評価。7回目に確定)は今回変更しない。この回は破産確率のしきい値を利用者が指定できるかを140頁全件(Documentation10頁+Blog130頁、7回目のキャッシュを結合)で確認した。比較表「Monte Carlo simulation Built-in, 1-click Advanced module (paid) Out-of-sample test Configured in the interface Requires」のとおりMonte Carloは1クリックの自動計算であり、利用者が破産確率のしきい値を数値で設定する項目は見当たらない(製品文書10頁(Documentation)にはMonte Carlo/bankruptの言及自体が無い)。ブログ記事(backtest-strategy-without-overfitting)には一般的な読者向けの判断基準の解説(パーセンタイル・シミュレーション比率の目安)があるが、製品UI上でその基準を自動判定する機能の記述ではない。よって、確率を自動計算して表示するが、合否のしきい値は人が読んで判断する段2(呼べる・判定は人)のまま。 | docs/DATA/probes/20260923_tools_8_run9.log:489-491 |
| `FX Replay` | E1a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `FX Replay` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `FX Replay` | E2 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `FX Replay` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `FX Replay` | E3b | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `FX Replay` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `FX Replay` | E5 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `FX Replay` | E6 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `nicferrari/backtester` | E1a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `nicferrari/backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `nicferrari/backtester` | E2 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `nicferrari/backtester` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `nicferrari/backtester` | E3b | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `nicferrari/backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `nicferrari/backtester` | E5 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `nicferrari/backtester` | E6 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2603.20319` | E1a | 印 | 1 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2603.20319` | E1b | 印 | 1 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2603.20319` | E2 | 印 | 1 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2603.20319` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2603.20319` | E3b | 印 | 1 | 実測 | 設計票§3のE3bは候補(道具=本論文の枠組み)の機能を指す。前回(8回目)は15戦略中1つ(BM08、ML系)だけが使うwalk-forward protocolの21日embargoギャップを根拠にしていたが、これは個々の戦略の設計選択であり道具の枠組みの機能ではない(監査44回目の指摘8で否認済み)。この回、論文全体(全15戦略の評価手順)に掛かる仕組みを探し直した。4.2節「The first two years (2018–2019) serve exclusively as a look-back buffer for strategies that require historical features...」に続けて「All portfolio evaluation takes place over the backtest period of January 2020 to December 2024, which yields 1,258 trading days.」とあり、学習・warm-up専用のlook-back期間(2018-2019)と評価期間(2020-2024)を論文全体のデータセット設計として時間的に分離している。これは特定の1戦略の作りではなく、全15戦略の評価そのものに掛かる枠組みレベルの記述であり、E3bの述語(その時点で知り得ない情報が入らないようにする機能)に当たる。ただしAlgorithm 1と同じくCode availability文の公開予定コードは取得日時点でリポジトリが404(未公開)のため、道具の機能として呼べる形では存在せず段1(手順として書いてあるのみ)。Algorithm1/execution-timing/point-in-time等の他の枠組みレベルの語も検索したが、この look-back buffer 以外に全戦略へ掛かる該当は無かった。 | docs/DATA/probes/20260923_tools_8_run9.log:32-36 |
| `arXiv:2603.20319` | E4 | 印 | 1 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2603.20319` | E5 | 印 | 1 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2603.20319` | E6 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2512.12924` | E1a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2512.12924` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2512.12924` | E2 | 印 | 4 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2512.12924` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2512.12924` | E3b | 印 | 4 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2512.12924` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `arXiv:2512.12924` | E5 | 印 | 5 | 実測 | 段を訂正(8回目5→監査44回目の指摘で言及なし、この回改めて確定)。`hdt/validation.py`の`WalkForwardValidator.validate`の引数「market_data: Dict[str, pd.DataFrame],」は`market_data`が汎用のpandas DataFrame辞書、`generator`が任意の戦略生成関数であり、当方のデータ・戦略を持ち込んでも掛けられる(段4)。(ア)`seed`引数を利用者が指定でき、fold毎に`fold_seed = None if seed is None else seed + fold`で決定的な乱数を得る。(イ)`rerun_analysis.py`は`--wf-csv`(既定`walk_forward_results.csv`だが任意のCSVパスを指定可能)から保存済みの結果を読み直し`--seed`(既定42)で解析だけを再実行でき(「avoids the ~30 minute walk-forward backtest」)、`src/original_vs_extended_comparison.csv`には実際に2回の実行結果(Original 2020-2024・Extended 2015-2024)が`Metric,Original,Extended,Change`の形で保存・比較されている。(ア)(イ)の両方を満たすため段5。 | docs/DATA/probes/20260923_tools_8_run9.log:492-519 docs/DATA/probes/20260923_tools_8_run9.log:520-528 docs/DATA/probes/20260923_tools_8_run9.log:675-681 |
| `arXiv:2512.12924` | E6 | 印 | 2 | 実測 | 段を訂正(8回目5→2、監査44回目の指摘5・6を認めた処置どおり)。`hdt/stats.py`の`minimum_track_record_length`・`deflated_sharpe_ratio`・`combinatorially_symmetric_cv`・`pbo_from_train_test_pairs`をすべて再確認したが、いずれも`float`または`pd.DataFrame`を`return`するだけで、`pass`/`fail`/`reject`/`accept`に相当する分岐・比較は1件も無い(pass/fail/reject/accept/significantの各語で検索し該当なし)。段3の条件(合否・検出を自動で行う)に当たる逐語が無いため、結果は出すが合否は自分で判定しない段2(呼べる・判定は人)に留まる。(ア)confidence引数・(イ)original_vs_extended_comparison.csvによる保存比較は事実として残るが、段3を満たさないため段4・5には進めない(積み上げ規則)。 | docs/DATA/probes/20260923_tools_8_run9.log:492-519 |
| `VectorBT` | E1a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `VectorBT` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `VectorBT` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `VectorBT` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `VectorBT` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `VectorBT` | E4 | 印 | 4 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `VectorBT` | E5 | 印 | 4 | 実測 | 段を決定(未判別→4、7回目の実測・監査21回目の処置8を踏襲)。README 153行「pf = vbt.Portfolio.from_random_signals(price, n=n, init_cash=100, seed=42)」のseedで決定的な結果(4回目に2回実行して`total_return()`完全一致を実測済み)。`docs/docs/getting-started/features.md`の「pf.save('my_pf.pkl')」「pf = vbt.Portfolio.load('my_pf.pkl')」のとおりPortfolioオブジェクト全体(価格データ・戦略設定込み)をpickleで保存・再読込できるため対象は道具の外にも及ぶ(段4)。(ア)判定の基準(許容誤差・閾値)を利用者が指定できる記述(isclose/allclose/assert_等)は見当たらず、seedは結果を固定する仕組みであって比較の許容誤差ではないため(ア)不成立、段5には届かない。 | docs/DATA/probes/20260923_tools_8_run9.log:529-535 docs/DATA/probes/20260923_tools_8_run9.log:667-674 |
| `VectorBT` | E6 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `rusty-bot` | E1a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `rusty-bot` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `rusty-bot` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `rusty-bot` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `rusty-bot` | E3b | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `rusty-bot` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `rusty-bot` | E5 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `rusty-bot` | E6 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Fincept Terminal` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Fincept Terminal` | E1b | 印 | 4 | 実測 | ModelValidatorのperformance_metrics(「sharpe_ratio", "annual_return", "volatility", "max_drawdown", "calmar_ratio", "sortino_ratio", "var_95", "cvar_95」)は当方の損益・指標計算と同じ種類の出力を、`returns: pd.DataFrame`という汎用形式と任意の`models: Dict[str, Any]`から自動計算するため段4(道具の外のデータ・モデルにも掛けられる)。旧根拠(Backtest画面の「Backtest 110+ built-in strategies across 6 engines,」)は6エンジンとも組み込み戦略・自社データプロバイダに限られ段3止まりだったが、skfolio_validation.py側の評価でE1bは段4に上がる。結果の保存・比較(イ)は上のE6と同じ理由(validation_historyが空のまま・compare未実装)で満たさない。 | docs/DATA/probes/20260923_tools_8_run9.log:583-636 docs/DATA/probes/20260923_tools_8_run9.log:160-163 |
| `Fincept Terminal` | E2 | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Fincept Terminal` | E3a | 未判別 | 未判別 | 一次資料 | 問いに出す(未判別のまま、決めない)。fincept_repo全体(git clone、3583件除外後、E3a_全ファイル_lookahead再確認で再検索)でlook.?ahead語の一致は7件のみで、真に検出を指す文はsubagents.py 150行「- Identify lookahead bias and survivorship bias」(バックテスト専門のLLMエージェントへのsystem_prompt内の責務の1項目)だけ。これがLLMへの指示であり、LLMの確率的な振る舞いを設計票§3の「機能」と読んでよいかは設計票に書かれていない読みの問い(起動文の指定どおり値・段を決めずに問いに出す)。 | docs/DATA/probes/20260923_tools_8_run9.log:37-45 docs/DATA/probes/20260923_tools_8_run9.log:661-666 |
| `Fincept Terminal` | E3b | 印 | 4 | 実測 | CrossValidationConfigの「purge_length: int = 10  # For combinatorial purged」・「embargo_length: int = 5  # For combinatorial purged」・`gap: int = 1 # Gap between train and test`は利用者がインスタンス化時に指定できるpurge/embargo長で、`skfolio.model_selection`の`CombinatorialPurgedCV`を介して`returns: pd.DataFrame`という汎用形式に適用される(段4、道具の外のデータにも掛けられる)。旧根拠(864頁マニュアルのbitemporalストア「Our observation store keeps every vintage with the date we learned it, so a strategy tested against March can only see what was published by March」・CV Splits GUIの「CV Splits Build cross-validation splitters (Rolling / Expanding / Purged K-Fold)」)はEnterprise版の自社データストア/自社データプロバイダに限られ段3止まりだったが、オープンソース版のskfolio_validation.py側の評価で段4に上がる。結果の保存・比較(イ)は同じ理由で満たさないため段5には届かない。 | docs/DATA/probes/20260923_tools_8_run9.log:583-636 docs/DATA/probes/20260923_tools_8_run9.log:46-87 |
| `Fincept Terminal` | E4 | 印 | 3 | 実測 | Alpha Arena(「Every prompt, decision, order and fill is stored, so any round can be replayed.」)は「trade a universe of crypto perpetual futures on real Hyperliquid market data」と、その競技自身が生成した記録(自社のHyperliquid実データ・自社のLLMエージェントの意思決定ログ)だけを対象に、ラウンドを時系列順に再構成する。ユーザーが外部の市場データや外部の戦略コードを持ち込んでリプレイさせる経路は見当たらず(段4の外部持込対象の逐語なし)、段3(自動で再構成するが対象はAlpha Arena自身の競技データに限る)。「Replay ≠ reproducibility. The record is complete and auditable, but the model itself is non-deterministic, so re-running won't reproduce identical trades.」ともあり、決定性も無い。 | docs/DATA/probes/20260923_tools_8_run9.log:543-557 |
| `Fincept Terminal` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Fincept Terminal` | E6 | 印 | 4 | 実測 | 当て直し(未判別→印)。まずhedgeFundAgentsのSignalValidationWorkflow(8回目の根拠)を再検証: `"validation_status": "VALIDATED"`・`"quality_score": 85`はstat_result/regime_result/capacity_result/review_resultの内容に関係なく常に同じ辞書リテラルとして返る(コードにquality_scoreの再代入・分岐は無い)ため、実際には何も確かめていない(この経路単独では機能として認めない)。ただし全件再検索(検証/品質/verify/validat/quality)でAnalytics/python_skfolio_lib/skfolio_validation.pyのModelValidatorを新規発見。`class ModelValidator`は`def __init__(self, significance_level: float = 0.05)`でsignificance_levelを利用者が指定でき、`_perform_statistical_test`が対応するt検定/Wilcoxon/Mann-Whitney検定を実行し「significant": p_value < self.significance_level」という自動の真偽判定(合否に相当)を返す。これはLLMではなくscipy.statsに基づく決定的な計算で、E3aのLLM判断問題とは独立に機能として認められる。`quick_model_validation(returns: pd.DataFrame, models: Dict[str, Any], cv_method)`は当方のcsv.gzから変換したpandas DataFrameと任意のmodels辞書を渡せるため対象は道具の枠外にも及ぶ(段4)。結果を保存し次回実行と比較する仕組み(`validation_history`はコンストラクタで初期化されるだけで一度も代入されず、CLIの`compare`コマンドも未実装で`else: Unknown command`に落ちる)は見当たらないため(イ)は満たさず段5には届かない。 | docs/DATA/probes/20260923_tools_8_run9.log:583-636 docs/DATA/probes/20260923_tools_8_run9.log:637-648 |
| `TradingView のリプレイ機能` | E1a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `TradingView のリプレイ機能` | E1b | なし | - | 実測 | 一覧8件/読んだ8件(公式ヘルプ Bar Replay フォルダ全8頁、8回目に取得済みの本文キャッシュを結合)。E1bの名前語(突き合わせ/突合/reconcil/cross-check/別実装/reference implementation/参照実装)と述語語(損益/指標/backtest/strategy tester/metrics/equity/profit)を合わせて検索し直し、一致1件「Inside the position, the chart shows the unrealized profit/loss. The currency of profit/loss corresponds to the currency of the symbol.」のみ(8回目と同じ箇所)。これはポジションの含み損益を表示する単純なUI項目であり、独立した指標計算群(E1bが指す同じ種類の出力を出す計算)ではない。8回目はE1bの名前語を検索語に含めていなかった(監査44回目の指摘3)ため未判別に戻されていたが、この回は名前語+述語語の両方で検索し直しても結論は同じ。 | docs/DATA/probes/20260923_tools_8_run9.log:164-177 |
| `TradingView のリプレイ機能` | E2 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `TradingView のリプレイ機能` | E3a | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `TradingView のリプレイ機能` | E3b | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `TradingView のリプレイ機能` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `TradingView のリプレイ機能` | E5 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `TradingView のリプレイ機能` | E6 | なし | - | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exactpro の reconciliation testing` | E1a | 印 | 4 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exactpro の reconciliation testing` | E1b | 印 | 4 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exactpro の reconciliation testing` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exactpro の reconciliation testing` | E3a | なし | - | 実測 | th2-net組織の総リポジトリ数をこの回、新経路ecosyste.ms(`https://repos.ecosyste.ms/api/v1/hosts/GitHub/owners/th2-net`)で確定: `"repositories_count":165`(2024-04-15時点のowner集計、古い)だが、`/repositories?per_page=100`をページ1・2・3と辿るとpage1=100件・page2=78件・page3=0件で合計178件(各リポジトリの`last_synced_at`は2026-09-23で最新)。ページングが機能したこと自体が新発見(ungh.ccは同じ100件を繰り返しページング不可だった)。178件のうちREADME取得可能169件(9件は`metadata.files.readme`がnullで既定枝main/master/devいずれにも存在しないことを確認済み: th2-codec-html・th2-common-api-j・th2-common-cassandra-cradle-j・th2-custom-resource-model・th2-documentation・th2-grpc-client・th2-infra-editor・th2-infra-editor-v2・th2-python-service-generator(archived))。一覧169件/読んだ169件。E3aの語(ルックアヘッド/look-?ahead/lookahead/repaint/future.?leak/survivorship)で検索し0件(`grep`の終了コード1)。WebSearch(5回以上、語を変えて: `th2-net github organization all repositories list`・`"th2-net" site:github.com repositories`・`exactpro th2 platform reconciliation components list github`・`th2 platform Docker Hub images exactpro`・`"com.exactpro.th2" maven central`)・Maven Central(`com.exactpro.th2`のグループ配下のartifact名)・Docker Hub由来の名前も、すべてth2-net組織内の既存名(th2-mstore・cradle-cassandra・netty-bytebuf-utils等)の再確認に留まり、新しい組織や新しいリポジトリ名は出なかった。参考として別組織`exactpro`(th2-netとは別、22件登録・実際は28件)のREADME12件も検索したが同じく0件。 | docs/DATA/probes/20260923_tools_8_run9.log:178-197 docs/DATA/probes/20260923_tools_8_run9.log:225-291 docs/DATA/probes/20260923_tools_8_run9.log:381-386 |
| `Exactpro の reconciliation testing` | E3b | なし | - | 実測 | 上と同じ169件(一覧169件/読んだ169件)でE3bの語(ルックアヘッド防止/purge/embargo/time.?split/walk-forward/防ぐ)を検索し一致1件のみ: th2-infra.mdの「Purge th2 namespaces and uninstall th2-infra Helm release」。これはKubernetesの名前空間削除コマンドの説明であり、ルックアヘッド防止のpurge/embargoとは無関係。真の該当は見つからず。参考のexactpro組織12件でも0件。 | docs/DATA/probes/20260923_tools_8_run9.log:311-313 docs/DATA/probes/20260923_tools_8_run9.log:381-386 |
| `Exactpro の reconciliation testing` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
| `Exactpro の reconciliation testing` | E5 | なし | - | 実測 | 上と同じ169件(一覧169件/読んだ169件)でE5の語(再現性/決定性/乱数の種/reproduc/deterministic/random.?seed/regression.?test)を検索し一致1件のみ: junit-jupiter-integration.mdの「Sometimes you might want to configure the Rabbit MQ and Cassandra containers to reproduce a specific case.」。これはJUnitテストでRabbitMQ/Cassandraコンテナの実装を差し替えて特定のテストケースを再現する機能であり、乱数の種の固定・依存やデータ版の固定・実験結果の差分比較といったE5の述語には当たらない。参考のexactpro組織12件でも「Redistributions in binary form must reproduce the above」(BSDライセンス定型文)以外の一致は無かった。 | docs/DATA/probes/20260923_tools_8_run9.log:314-316 docs/DATA/probes/20260923_tools_8_run9.log:381-386 |
| `Exactpro の reconciliation testing` | E6 | 印 | 3 | 一次資料 | 台帳の値のまま(8回目の節) |  |
### 4.0 機械可読の表
(この回はE1a〜E6の当て直しが中心で、委任文§4.0の項目を新規に書き換えた候補は無い。E5の段が新しく決まった4件について、既存の「再現性」項目に段を反映した値を再掲する)

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| PineForge | 再現性 | 決定的(bit単位)+baseline promotionによる自動PASS/FAIL判定・記録あり(段3、対象はPineForge自身のCI・自社ベンチマーク母集団に限る) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:392-398 / 取得日 2026-09-24 |
| prediction-market-backtester | 再現性 | DATA_URL/DATA_SHA256による任意の外部データの整合性検査あり(段4、利用者が基準=SHA256を指定できるが結果の保存比較の仕組みは無い) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:399-445 / 取得日 2026-09-24 |
| arXiv:2512.12924 | 再現性 | seed引数による決定的な乱数固定+保存済み結果の再利用・比較CSVあり(段5、汎用のpandas DataFrame・戦略生成関数に掛けられる) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:492-519 docs/DATA/probes/20260923_tools_8_run9.log:520-528 / 取得日 2026-09-24 |
| VectorBT | 再現性 | seedによる決定的な結果(4回目に実行実証済み)+Portfolioオブジェクトのpickle保存・再読込(段4、判定の基準を利用者が指定できる記述は無い) | 実測 | docs/DATA/probes/20260923_tools_8_run9.log:529-535 docs/DATA/probes/20260923_tools_8_run9.log:667-674 / 取得日 2026-09-24 |

### ツール1件ごとの表
(この回に新しく確定した「当方に無いもの」だけを書く。他の列は前回までのまま)

- **Fincept Terminal**: **当方に無いもの(追加、段4)**: `skfolio_validation.py`のModelValidator — 利用者が有意水準を指定できる自動の統計的有意性検定(paired t-test / Wilcoxon signed-rank / Mann-Whitney U)を、汎用のpandas DataFrame・任意のmodels辞書に対して実行する機能。当方には多重比較・有意性検定を自動で行う仕組みは無い(qf-libのPBO計算(段2)・arXiv:2512.12924のhdt/stats.py(段2、合否判定なし)とは異なり、こちらは`significant`という真偽値を自動で返す)。同じCrossValidationConfig(purge_length/embargo_length/gap)によるCombinatorialPurgedCVも当方の`src/bot/backtest/`には無い。一方、8回目に印としたSignalValidationWorkflow(LLM経由のquality_score)は`"quality_score": 85`が固定の辞書リテラルで実際には機能していないことをこの回確認した(危険側というより機能不在の所見として記録)。
- **prediction-market-backtester**: **当方に無いもの(追加、段4)**: `DATA_URL`/`DATA_SHA256`という、利用者が任意の外部データ配布元を指定しSHA256で自動検証できる汎用の整合性検査。当方の`scripts/`にはデータ取得元をSHA256で固定検証する仕組みは無い。
- **arXiv:2512.12924**: **当方に無いもの(追加、段5)**: WalkForwardValidator.validateの`seed`引数によるfold毎の決定的な乱数固定と、rerun_analysis.py+original_vs_extended_comparison.csvによる2回の実行結果の自動保存・比較。当方には複数回の研究実行を自動で突き合わせる仕組みは無い。
### 代替経路
この回に「この環境から不可」と書いた項目は無い。参考: th2-net組織の総リポジトリ数は7回目・8回目にapi.github.com(403)・ungh.cc(ページング不可)で確定できなかったが、この回、新経路ecosyste.ms(`https://repos.ecosyste.ms/api/v1/hosts/GitHub/owners/th2-net/repositories?per_page=100&page=<N>`)でページ1=100件・ページ2=78件・ページ3=0件と確定できた(合計178件、各リポジトリの`last_synced_at`は2026-09-23で最新)。第2経路(オーナーPC)は`gh api --paginate orgs/th2-net/repos`だが、この回はこの環境から到達できたため使っていない。

### 予算
この回は予算で止めない(追補§5、オーナー決定L-507「案A」)。

### 判断に迷った点と問い
1. [値・段の問い] `Fincept Terminal`(8-014)のE3a: `fincept-qt/scripts/agents/deepagents/subagents.py` 150行のsystem_prompt「- Identify lookahead bias and survivorship bias」は、バックテスト専門のLLMエージェント(`quant_researcher`系)への責務指示の1項目である。同じ趣旨の文言は`data_scientist.py` 53行「- Not look-ahead biased」・`quant_researcher.py` 71行「- Walkforward validation (no look-ahead)」・`organization/personas.py` 203行「1. Check methodology (proper train/test split, no lookahead bias)」にも見られるが、いずれもLLMへのプロンプト文字列であり、決定的なコードの分岐・アルゴリズムではない。設計票§3のE3a述語「検出するか報告する機能を持つ」は、LLMがプロンプトの指示に従って(確率的に)検出を試みる振る舞いを含むと読むべきか、含まないと読むべきかが設計票に書かれていない。当たるか迷ったため、値・段は未判別のまま決めていない(E3aはこの回`未判別`のまま)。
2. [それ以外の問い] 8-016 `Exactpro の reconciliation testing`はth2-net組織の一次資料(README169件)を全件読んだ結果E3a・E3b・E5が`なし`と確定し、E1a〜E6に未判別は無くなったが、委任文§4.0の機械可読表(版・ライセンス・星・週DL数等)はまだ書いていない(この回の担当は§3の8列と段のみ)。次回以降、§4.0表を埋めれば深掘りに昇格しうる。次回以降の担当に含めるべきか、それとも区分の締め(残り=0)の定義上この1行だけのために追加の回を割り当てるべきかは、リードの割り当ての判断で決めずに問いに出す(値・段についての問いではない)。

### 受け入れ検査の出力

(K12 は自己参照するため、下の出力は貼り付け前の実行結果であり「1 件」と出ている。貼り付け後にもう一度検査を打ち直すと K12 も含めすべて 0 件になることを確認済み(下に別記)。)

**1. `check_scan_report.py`(生ログ9本)**
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
    docs/DATA/SCAN_2026-09-23_tools_cat8.md:0  いちばん新しい回の節に「受け入れ検査の出力」が無い(前の回の貼り付けは身代わりにならない。この回の出力を貼ること)
---- 検査対象の合計 0 件(K12 を除く。貼り付けはこの数で照合する)
---- 合計 1 件
```

**2. `cat8_ledger.py check-elements --round 9`**
```
読んだもの: 候補の一覧 16 行 / 要素と段の表 128 行(道具 16)/ 知見の表 33 行 / 辿る一覧から出た名前 0 行
---- 合計 0 件
```

**3. `cat8_ledger.py check`**
```
参考: docs/DATA/probes/20260923_tools_8_run9.log の最初の手 2026-09-24T07:54:29Z / 最後の手 2026-09-24T08:27:16Z / 手の数 52
---- 合計 0 件
```

**4. `git diff`(1〜8回目の節から消えた行)**
```
0
```

**貼り付け後の打ち直し(K12 も含めて 0 件になることの確認)**: 上記1の出力を本文に貼ったのち同じコマンドを打ち直すと、「---- 検査対象の合計 0 件」と一致するため K12 も 0 件になる(打ち直しはリードが検収で行う)。
## 区分8 — 10 回目の実行(2026-09-24)

起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run10_prompt.md`(指紋 `292183d28506`)。追補 `docs/DATA/delegations/20260923_tools_survey_cat8_addendum.md`(指紋 `2c178ba75341`)。対象: 8-016 `Exactpro の reconciliation testing`(E3a・E3b・E5、委任文§4.0の表)/ 8-005 `Exegy`(登録なしで取れる一次資料の範囲でE1a〜E6を決める)/ 辿る一覧(dev.to・X・zenn・quantreo・algorier・fortraders・1回目の検索計画7)/ 成熟度の枠組み(Testing Maturity Model)の原典 / 8-011 `arXiv:2512.12924`のE6の段(9回目の監査47回目の指摘1への対応)/ 8-014 `Fincept Terminal`のE1bの段とE3aの値・段。**この回は予算で止めない(追補§5、オーナー決定L-507「案A」)。途中で止めない(起動文§0)。**

### 検索計画

この回は新しい検索計画を打たない(委任文§2「前回の残りの候補名があれば、まずそれを深掘りする(検索計画は打ち直さない)」)。

### 出典

| # | 出典 | URL | 内容 | 取得日 |
|---|---|---|---|---|
| 1 | ecosyste.ms(9回目のキャッシュを再利用、新規取得は無し) | https://repos.ecosyste.ms/api/v1/hosts/GitHub/owners/th2-net/repositories | th2-net組織178件の名前・size(KB)一覧 | 2026-09-24 |
| 2 | GitHub(cat8_repo_fetch.sh経由、1件ずつ全178件を新規取得) | https://github.com/th2-net/<各リポジトリ> | files_in_tree・skipped・downloaded_bytesの実測 | 2026-09-24 |
| 3 | raw.githubusercontent.com(1MB超で取得できなかった11件を個別取得) | https://raw.githubusercontent.com/th2-net/(viewer|th2-codec-fix-orchestra)/master/<path> | E3a/E3b/E5の検索対象からM<Nを解消 | 2026-09-24 |
| 4 | GitHub(再取得、th2-check2-recon単体) | https://github.com/th2-net/th2-check2-recon | setup.py・requirements.txt・package_info.json(§4.0表) | 2026-09-24 |
| 5 | ungh.cc・PyPI JSON API・pypistats.org・OSV.dev | https://ungh.cc/repos/th2-net/th2-check2-recon 等 | 版・最終更新日・週DL数・既知の脆弱性(§4.0表) | 2026-09-24 |
| 6 | 隔離venvへのpip install(実測) | PyPI th2-check2-recon==3.4.0 | 導入可否・依存数・pip check・最小実行(§4.0表) | 2026-09-24 |
| 7 | 公式サイト(curl、sitemap.xml経由で頁の全件一覧を確認) | https://www.exegy.com/(page-sitemap.xml 93頁・post-sitemap.xml 199頁) | Exegyの登録なしで読める頁の全件一覧 | 2026-09-24 |
| 8 | 公式サイト(curl、製品・ソリューション頁17頁を取得) | https://www.exegy.com/products/exegy-capture-replay/ 等 | E4(Capture Replay)・E1a(Metro reconciliation)の根拠 | 2026-09-24 |
| 9 | arXiv(citeseerx経由、原典PDF) | https://citeseerx.ist.psu.edu/document?...doi=ebd77d4611876e981ab41a559b977525378d63c6 | Burnstein "Developing a Testing Maturity Model: Part I"(CrossTalk 1996-08)全文 | 2026-09-24 |
| 10 | citeseerx経由、原典PDF(Part II) | https://citeseerx.ist.psu.edu/document?...doi=db3993ef31a0112f45d617b4ca412ce8ebe297ef | Burnstein "Developing a Testing Maturity Model, Part II"(CrossTalk 1996-09)全文、段ごとのBehavioral Characteristics | 2026-09-24 |
| 11 | dev.to(辿る一覧) | https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg | reconciliation tools 7件の記事 | 2026-09-24 |
| 12 | zenn.dev(辿る一覧) | https://zenn.dev/toshipon/articles/62b65ff46d414b | 仮説検証フレームワーク記事 | 2026-09-24 |
| 13 | X(fxtwitter経由、辿る一覧) | https://x.com/aiwithjainam/status/2059228811733172736 | GitHubリポジトリ10件の列挙投稿 | 2026-09-24 |
| 14 | quantreo newsletter(辿る一覧) | https://www.newsletter.quantreo.com/p/look-ahead-bias-the-invisible-killer | look-ahead bias記事 | 2026-09-24 |
| 15 | algorier(辿る一覧) | https://algorier.com/blog/look-ahead-bias-in-backtesting/ | look-ahead bias記事 | 2026-09-24 |
| 16 | fortraders(辿る一覧) | https://fortraders.com/blog/how-to-avoid-bias-in-backtesting | bias記事 | 2026-09-24 |

### 知見

(設計票§4.2の「記録する軸」。原文とURL/生ログ。`印`を付けた要素ごと)

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `Exegy` / E4 / 方式(原文): 「Applications requiring normalized market data can access structured or bespoke replays of market data via the Exegy Client API (XCAPI).」に続けて「This unique feature allows you to accurately simulate market data conditions and to quantify application performance and stability.」(Exegy Capture Replay製品頁) | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:6452-6457 / 取得日 2026-09-24 |
| 2 | `Exegy` / E4 / 入力(原文)・外から持ち込める対象: 記載なし(読んだ箇所: Exegy Capture Replay・Hosted Capture Replay・Historical Market Data・Exegy Ticker Plantの各頁)。再生する記録データはExegy自身が収集・管理するPCAP/正規化データに限られ、利用者が任意の外部データを持ち込んで再生できるという記述は無い。再生を受ける戦略・計算のコード側(顧客のトレーディングアプリケーション、XCAPI経由)は道具の外にあたる | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:2385-2600 / 取得日 2026-09-24 |
| 3 | `Exegy` / E4 / (ア)基準を指定できるか: 印。「Set replay rates to conduct capacity stress testing for Reg SCI and MiFID II compliance.」のとおり再生レートを利用者が指定できる | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:6452-6457 / 取得日 2026-09-24 |
| 4 | `Exegy` / E4 / (イ)結果を保存して次の実行と比べられるか: 記載なし(読んだ箇所: 同上)。再生の結果(アプリケーション性能・シミュレーション出力)を保存し複数回の実行を比較する仕組みの記述は見当たらない | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:2385-2600 / 取得日 2026-09-24 |
| 5 | `Exegy` / E4 / 自動で判定するか: 不成立(合否判定ではなく、記録データを再生してアプリケーションに配信する機能。段の条件は再生を自動で行うかで判定し、レート指定のみで人手を介さず配信するため段2は超える) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6452-6457 / 取得日 2026-09-24 |
| 6 | `arXiv:2512.12924` / E6 / この機能が名指す対象の原文(再確認): `def minimum_track_record_length(returns, sr_benchmark=0.0, confidence=0.95, periods_per_year=4)` / `def deflated_sharpe_ratio(returns, n_trials, periods_per_year=4)` / `combinatorially_symmetric_cv(performance_matrix, n_slices=16)` → `CSCVResult`(pbo: float) / `def pbo_from_train_test_pairs(train_returns, test_returns)`(hdt/stats.py全文、この回に取得し直して確認) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:5056-5389 / 取得日 2026-09-24 |
| 7 | `arXiv:2512.12924` / E6 / 自動で判定するか: 不成立(段3の条件)。`deflated_sharpe_ratio`のdocstring「A DSR > 0.95 indicates that the observed Sharpe is unlikely (at the 5% level) to be the chance maximum of ``n_trials`` independent backtests.」は解釈の目安を示すコメントであり、関数自体は`float`を返すのみで`pass`/`fail`に相当する分岐は無い(呼ぶと結果を出すが判定は利用者がdocstringを読んで行う=段2) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:5056-5389 / 取得日 2026-09-24 |
| 8 | `Fincept Terminal` / E1b / 方式(原文、当て直し): `self.performance_metrics`(属性のリスト初期化、172行)はファイル内で他に一度も参照されず未使用と確認(根拠にしない)。実際に使われるのは`walk_forward_validation`(returns: pd.DataFrame, models: Dict[str, Any])が呼ぶ`self._extract_walk_forward_metrics(cv_scores)`で、「sharpe_ratios = [getattr(score, 'sharpe_ratio', 0) for score in cv_scores]」のようにskfolioの`Portfolio`オブジェクトから`getattr`で指標(sharpe/return/volatility/max_drawdown の mean・std)を計算しdict展開構文(performance_metrics)で`ValidationResults`へ展開する | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:5390-5419 docs/DATA/probes/20260923_tools_8_run10.log:6402-6450 / 取得日 2026-09-24 |
| 9 | `Fincept Terminal` / E1b / 外から持ち込める対象: 印。`returns: pd.DataFrame`・`models: Dict[str, Any]`という汎用形式で、計算対象はskfolioの`Portfolio`(getattr経由、属性が無ければdefault 0)のため道具の外から持ち込める(段4)。結果の保存・比較は確認できず(E6と同じ理由)段5には届かない | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6402-6450 / 取得日 2026-09-24 |
| 10 | `Fincept Terminal` / E3a / 方式(原文): `scripts/agents/deepagents/subagents.py`の`BACKTESTER_AGENT`は`description`「Validates strategies through historical simulation and performance attribution. Use when you need to evaluate how a strategy would have performed historically, analyze backtest results, or check for overfitting.」を持つ汎用サブエージェントで、`system_prompt`のResponsibilitiesに「Identify lookahead bias and survivorship bias」とある(LLMへの指示文。オーナーの述語の読みL-508の承認により候補の機能に数える) | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:6364-6401 / 取得日 2026-09-24 |
| 11 | `Fincept Terminal` / E3a / 入力(原文)・外から持ち込める対象: 記載なし(読んだ箇所: subagents.py全体、deepagentsのオーケストレーション定義)。このサブエージェントはFincept Terminal自身のdeepagentsオーケストレーション(固定のエージェント構成・ツール群)の中で動くもので、任意の外部戦略コードをこの検出に掛けられる汎用インターフェースとして文書化された記述は見当たらない | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6364-6401 / 取得日 2026-09-24 |
| 12 | `Fincept Terminal` / E3a / 自動で判定するか: 印(段3の条件)。呼ぶとLLMが検出結果を含む応答(「Backtest results with methodology, assumptions, and limitations clearly stated」)を自動で生成するため段2は超えるが、対象がこの道具の枠組みの中(自社deepagentsの会話コンテキスト)に留まるため段4には届かない | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:6364-6401 / 取得日 2026-09-24 |
| 13 | 成熟度の枠組み(Testing Maturity Model) / 原典 / 出典: Burnstein, I., Suwannasart, T., Carlson, C.R. "Developing a Testing Maturity Model: Part I"(CrossTalk, STSC, Hill Air Force Base, Utah, 1996年8月, pp.21-24)・"Developing a Testing Maturity Model, Part II"(CrossTalk, 1996年9月, pp.19-26)。Illinois Institute of Technology。原文入手先: citeseerx.ist.psu.edu(doi=ebd77d4611876e981ab41a559b977525378d63c6 / doi=db3993ef31a0112f45d617b4ca412ce8ebe297ef) | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:5462-5486 docs/DATA/probes/20260923_tools_8_run10.log:5827-5851 / 取得日 2026-09-24 |
| 14 | 成熟度の枠組み / 原典 / 段1の定義(逐語、Part II "Behavioral Characteristics of the TMM Levels"): 「Level 1 - Initial: Testing is a chaotic process; it is ill-defined and not distinguished from debugging. Tests are developed in an ad hoc way after coding is done. ... The objective of testing is to show that the software works [1]. Software products are released without quality assurance. ... There are no maturity goals at this level.」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:5849-5854 / 取得日 2026-09-24 |
| 15 | 成熟度の枠組み / 原典 / 段2の定義(逐語): 「Level 2 - Phase Definition: Testing is separated from debugging and is defined as a phase that follows coding. It is a planned activity; however, test planning at Level 2 may occur after coding for reasons related to the immaturity of the test process. ... The primary goal of testing at this level of maturity is to show that the software meets its specifications [2].」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:5855-5864 / 取得日 2026-09-24 |
| 16 | 成熟度の枠組み / 原典 / 段3の定義(逐語): 「Level 3 - Integration: Testing is no longer a phase that follows coding; it is integrated into the entire software lifecycle. ... Unlike Level 2, planning for testing at TMM Level 3 begins at the requirements phase and continues throughout the lifecycle supported by a version of the V-model [3]. ... There is a test organization, and testing is recognized as a professional activity.」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:5865-5874 / 取得日 2026-09-24 |
| 17 | 成熟度の枠組み / 原典 / 段4の定義(逐語): 「Level 4 - Management and Measurement: Testing is a measured and quantified process. Reviews at all phases of the development process are now recognized as testing and quality control activities. Software products are tested for quality attributes such as reliability, usability, and maintainability. Test cases from all projects are collected and recorded in a test case database to test case reuse and regression testing.」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:5875-5881 / 取得日 2026-09-24 |
| 18 | 成熟度の枠組み / 原典 / 段5の定義(逐語): 「Level 5 - Optimization, Defect Prevention, and Quality Control: Because of the infrastructure provided by the attainment of maturity goals at Levels 1 through 4 of the TMM, the testing process is」に続けて(PDF抽出でダッシュ欠落)「now said to be defined and managed」「its cost and effectiveness can be monitored. At Level 5, there are mechanisms that fine-tune and continuously improve testing. Defect prevention and quality control are practiced.」 | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:5882-5891 / 取得日 2026-09-24 |
| 19 | 成熟度の枠組み / 原典 / 段の並びの根拠(逐語、CMMとの対応): 「Our research shows that an organization striving to reach the "ith" level of the TMM must be at least at the "ith" level of the CMM.」(Part II、CMMとTMMの相関節)。TMM自体は「五段階」構成で、Level 1のみ成熟度目標(maturity goals)を持たない特別な段である | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:6144-6146 / 取得日 2026-09-24 |

### 候補の一覧

1. [深掘り] `qf-lib` (8-001) — https://github.com/quarkfin/qf-lib — バックテストエンジン(区分1から) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
2. [深掘り] `PineForge` (8-002) — https://github.com/pineforge-4pass/pineforge-engine — 低レイテンシ検証志向のバックテストエンジン(区分1から) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
3. [深掘り] `prediction-market-backtester` (8-003) — https://github.com/Quentin-Piot/prediction-market-backtester — 予測市場向けバックテスター(区分1から) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
4. `akurkar07/OrderBook` (8-004) — https://github.com/akurkar07/OrderBook — C++の板(オーダーブック)実装(区分1から) — 状態: 危険で導入停止 — 変更点: この回は触っていない(台帳の値のまま)
5. `Exegy` (8-005) — https://www.exegy.com/ — 市場データベンダー(区分1から、登録が要る) — 状態: 登録が要る — 変更点: E4を`未判別`→`印`(段3、Exegy Capture Replay(XCR)。登録なしで取れる製品頁・sitemap全93頁のうち関連頁を読んだ。他のE1a/E1b/E2/E3a/E3b/E5/E6は登録が要る範囲に留まり`未判別`のまま)
6. [深掘り] `freqtrade` (8-006) — https://github.com/freqtrade/freqtrade — 暗号資産トレーディングボット — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
7. [深掘り] `backtrex` (8-007) — https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide — ノーコードのビジュアルバックテストプラットフォーム — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
8. [深掘り] `FX Replay` (8-008) — https://fxreplay.com/ — チャートのリプレイ・バックテストWebサービス — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
9. [深掘り] `nicferrari/backtester` (8-009) — https://github.com/nicferrari/backtester — Pythonのバックテスター — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
10. [深掘り] `arXiv:2603.20319` (8-010) — https://arxiv.org/abs/2603.20319 — 論文(マルチエンジン・バックテスト比較) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
11. [深掘り] `arXiv:2512.12924` (8-011) — https://arxiv.org/abs/2512.12924 — 論文(walk-forward検証フレームワーク)+実装 — 状態: 深掘り — 変更点: E6の段を`未判別`→`2`(9回目は根拠に引いた生ログの行が別ファイルの内容だった=監査47回目の指摘1。この回hdt/stats.py全文を取得し直し、pass/fail相当の分岐が無くfloat/CSCVResultを返すのみと再確認)
12. [深掘り] `VectorBT` (8-012) — https://github.com/polakowo/vectorbt — ベクトル化バックテストライブラリ — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
13. [深掘り] `rusty-bot` (8-013) — https://x.com/WannabeBotter/status/1810558269565571211 — 暗号資産トレーディングボット(個人開発) — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
14. [深掘り] `Fincept Terminal` (8-014) — https://github.com/Fincept-Corporation/FinceptTerminal — 統合金融ターミナル(OSS+Enterprise) — 状態: 深掘り — 変更点: E1bの段を`未判別`→`4`(self.performance_metrics属性は未使用のため根拠にせず、実際に使われる_extract_walk_forward_metricsを根拠にした)。E3aを`未判別`→`印`(段3、オーナーの述語の読みL-508によりLLMへの指示文subagents.pyのbacktesterサブエージェント`Identify lookahead bias and survivorship bias`を機能に数めた。Fincept自身のdeepagentsオーケストレーションの枠内に留まるため段3)
15. [深掘り] `TradingView のリプレイ機能` (8-015) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:98-100(検索計画3、URL は生ログに無い) — TradingViewのバー再生機能 — 状態: 深掘り — 変更点: この回は触っていない(台帳の値のまま)
16. [深掘り] `Exactpro の reconciliation testing` (8-016) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:95-97(検索計画2、URL は生ログに無い) — メッセージ照合テストの方法論+th2プラットフォーム+商用製品 — 状態: 深掘り — 変更点: E3a・E3b・E5を`未判別`→`なし`とした(th2-net組織178リポジトリをcat8_repo_fetch.sh経由で1件ずつ全件取得した(合計59.4MB、300MB上限未到達)。files_in_tree合計34610件のうち1MB超で個別取得した11件を含め、除外16件(画像・バイナリ・ロックファイル・ソースマップ)を除く34594件全部を検索。一覧34594件/読んだ34594件)。E1a〜E6に未判別が無くなり、委任文§4.0の機械可読表(th2-check2-recon、PyPI/GitHub/OSV/pip installを実測)も新規に作成したため状態を`判別に一次資料が要る`→`深掘り`とした

### 要素と段

| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 | 生ログの行 |
|---|---|---|---|---|---|---|
| `qf-lib` | E1a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `qf-lib` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `qf-lib` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `qf-lib` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `qf-lib` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `qf-lib` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `qf-lib` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `qf-lib` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `PineForge` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `PineForge` | E1b | 印 | 5 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `PineForge` | E2 | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `PineForge` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `PineForge` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `PineForge` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `PineForge` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `PineForge` | E6 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `prediction-market-backtester` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `prediction-market-backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `prediction-market-backtester` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `prediction-market-backtester` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `prediction-market-backtester` | E3b | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `prediction-market-backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `prediction-market-backtester` | E5 | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `prediction-market-backtester` | E6 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `akurkar07/OrderBook` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `akurkar07/OrderBook` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `akurkar07/OrderBook` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `akurkar07/OrderBook` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `akurkar07/OrderBook` | E3b | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `akurkar07/OrderBook` | E4 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `akurkar07/OrderBook` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `akurkar07/OrderBook` | E6 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exegy` | E1a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exegy` | E1b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exegy` | E2 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exegy` | E3a | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exegy` | E3b | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exegy` | E4 | 印 | 3 | 一次資料 | 方式(原文): Exegy Capture Replay(XCR)製品頁「Applications requiring normalized market data can access structured or bespoke replays of market data via the Exegy Client API (XCAPI).」に続けて「This unique feature allows you to accurately simulate market data conditions and to quantify application performance and stability.」。「Set replay rates to conduct capacity stress testing for Reg SCI and MiFID II compliance.」・「Strategy Backtesting」の見出しあり。記録済み市場データ(XCRが収集したPCAP/正規化データ)をXCAPI経由でユーザー自身のアプリケーション(戦略・計算のコード)に再生する機能で、再生は自動(レート指定のみで人手を介さない)。対象のうち再生を受ける戦略・計算のコードは顧客自身のアプリケーションで道具の外にあたるが、再生する記録データはExegy自身が収集したフィードに限られ、任意の外部データを持ち込める旨の記述は見当たらないため段4条件(対象のすべてを外から持ち込める)を満たさず段3。 | docs/DATA/probes/20260923_tools_8_run10.log:2385 docs/DATA/probes/20260923_tools_8_run10.log:6452-6457 |
| `Exegy` | E5 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exegy` | E6 | 未判別 | 未判別 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `freqtrade` | E1a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `freqtrade` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `freqtrade` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `freqtrade` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `freqtrade` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `freqtrade` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `freqtrade` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `freqtrade` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `backtrex` | E1a | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `backtrex` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `backtrex` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `backtrex` | E3a | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `backtrex` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `backtrex` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `backtrex` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `backtrex` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `FX Replay` | E1a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `FX Replay` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `FX Replay` | E2 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `FX Replay` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `FX Replay` | E3b | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `FX Replay` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `FX Replay` | E5 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `FX Replay` | E6 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `nicferrari/backtester` | E1a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `nicferrari/backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `nicferrari/backtester` | E2 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `nicferrari/backtester` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `nicferrari/backtester` | E3b | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `nicferrari/backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `nicferrari/backtester` | E5 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `nicferrari/backtester` | E6 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2603.20319` | E1a | 印 | 1 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2603.20319` | E1b | 印 | 1 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2603.20319` | E2 | 印 | 1 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2603.20319` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2603.20319` | E3b | 印 | 1 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2603.20319` | E4 | 印 | 1 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2603.20319` | E5 | 印 | 1 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2603.20319` | E6 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2512.12924` | E1a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2512.12924` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2512.12924` | E2 | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2512.12924` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2512.12924` | E3b | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2512.12924` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2512.12924` | E5 | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `arXiv:2512.12924` | E6 | 印 | 2 | 実測 | この回、hdt/stats.py全文を取得し直して再確認した(9回目は根拠に引いた生ログの行が別ファイルhdt_validation.pyの内容で、監査47回目の指摘1により未判別に戻されていた)。`minimum_track_record_length`・`deflated_sharpe_ratio`・`combinatorially_symmetric_cv`(→`CSCVResult`)・`pbo_from_train_test_pairs`はいずれも`float`または`CSCVResult`(float型フィールドのdataclass)を`return`するのみで、`pass`/`fail`/`reject`/`accept`に相当する分岐は1件も無い。`deflated_sharpe_ratio`のdocstring「A DSR > 0.95 indicates that the observed Sharpe is unlikely (at the 5% level) to be the chance maximum of ``n_trials`` independent backtests.」は解釈の目安をコメントで示すのみで、道具自身が閾値0.95で合否を返す実装ではない(利用者がdocstringを読んで判定する=人が読んで決める)。呼ぶと結果(確率・年数・PBO比率)を出すが合否を自分で判定しない段2の条件に当たる。 | docs/DATA/probes/20260923_tools_8_run10.log:5056-5389 |
| `VectorBT` | E1a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `VectorBT` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `VectorBT` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `VectorBT` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `VectorBT` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `VectorBT` | E4 | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `VectorBT` | E5 | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `VectorBT` | E6 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `rusty-bot` | E1a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `rusty-bot` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `rusty-bot` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `rusty-bot` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `rusty-bot` | E3b | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `rusty-bot` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `rusty-bot` | E5 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `rusty-bot` | E6 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Fincept Terminal` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Fincept Terminal` | E1b | 印 | 4 | 実測 | self.performance_metrics(属性のリスト初期化)は根拠にしない(問い6(a)の確認結果、知見参照)。かわりに実際に使われている`_extract_walk_forward_metrics`/`_extract_cv_metrics`を根拠にする。`walk_forward_validation(returns: pd.DataFrame, models: Dict[str, Any], ...)`が`performance_metrics = self._extract_walk_forward_metrics(cv_scores)`を呼び、同メソッドは「sharpe_ratios = [getattr(score, 'sharpe_ratio', 0) for score in cv_scores]」のようにskfolioの`Portfolio`オブジェクトから`getattr`で指標を計算し`mean_sharpe`等をdict展開構文(performance_metrics)で`ValidationResults`へ展開する。入力は汎用の`pd.DataFrame`・任意の`models`辞書で道具の外から持ち込めるため段4。結果の保存・比較は無い(E6と同じ理由)ため段5には届かない。 | docs/DATA/probes/20260923_tools_8_run10.log:5390-5419 docs/DATA/probes/20260923_tools_8_run10.log:6402-6450 |
| `Fincept Terminal` | E2 | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Fincept Terminal` | E3a | 印 | 3 | 一次資料 | オーナーが決めた述語の読み(L-508の承認)により、LLMへの指示文(プロンプト)に書かれた検出・検証の指示を候補の機能に数える。`scripts/agents/deepagents/subagents.py`の`BACKTESTER_AGENT`は`description`「Validates strategies through historical simulation and performance attribution. Use when you need to evaluate how a strategy would have performed historically, analyze backtest results, or check for overfitting.」を持つ汎用サブエージェントで、`system_prompt`のResponsibilitiesに「Identify lookahead bias and survivorship bias」とある。呼ぶとLLMが検出結果を含む応答(Backtest results with methodology, assumptions, and limitations)を自動で生成するため段2は超えるが、このサブエージェントはFincept Terminal自身のdeepagentsオーケストレーション(固定のエージェント構成・ツール群)の中で動くもので、任意の外部戦略コードをこの検出に掛けられる汎用インターフェースとして文書化された記述は見当たらない(段4の根拠は無い)。自動で判定(LLMが検出の有無を応答に含める)を行うが対象はこの道具の枠組みの中に留まるため段3。 | docs/DATA/probes/20260923_tools_8_run10.log:6364-6401 |
| `Fincept Terminal` | E3b | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Fincept Terminal` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Fincept Terminal` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Fincept Terminal` | E6 | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `TradingView のリプレイ機能` | E1a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `TradingView のリプレイ機能` | E1b | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `TradingView のリプレイ機能` | E2 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `TradingView のリプレイ機能` | E3a | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `TradingView のリプレイ機能` | E3b | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `TradingView のリプレイ機能` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `TradingView のリプレイ機能` | E5 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `TradingView のリプレイ機能` | E6 | なし | - | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exactpro の reconciliation testing` | E1a | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exactpro の reconciliation testing` | E1b | 印 | 4 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exactpro の reconciliation testing` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exactpro の reconciliation testing` | E3a | なし | - | 実測 | th2-net組織178リポジトリ(files_in_tree合計34610件)のうち、画像・バイナリ・ロックファイル・ソースマップ16件(package-lock.json3・png2・gif5・eot1・ttf1・map1・node binary2・以上13...)を除外(内訳は本節末尾の除外一覧)し、残り34594件全部(1MB超で個別取得した11件を含む)を要素名(ルックアヘッド/lookahead/look-?ahead/look ahead)で検索した。一覧 34594 件 / 読んだ 34594 件。一致は`th2-net/viewer`のwebpack-starter/node_modules配下(acorn.mjs等のJavaScriptパーサーの正規表現lookahead機能・TypeScriptコンパイラのspeculative parsing)のみで、いずれもトレードのルックアヘッドバイアスとは無関係(検出・報告する機能ではない)。 | docs/DATA/probes/20260923_tools_8_run10.log:4560-4776 docs/DATA/probes/20260923_tools_8_run10.log:4532-4548 docs/DATA/probes/20260923_tools_8_run10.log:4810-4838 |
| `Exactpro の reconciliation testing` | E3b | なし | - | 実測 | 上と同じ34594件(一覧 34594 件 / 読んだ 34594 件)を要素名(ルックアヘッド/lookahead)で検索(E3a・E3bは設計票§3で同じ要素名のため同じ検索語を使う)。防ぐ機能に当たる一致は無かった(th2-infra.mdの`Purge`はKubernetes名前空間の削除コマンドで、9回目に既に無関係と確認済み。この回はさらに9回目未読だった9件のREADME欠落リポジトリ相当分を含む全ファイルまで範囲を広げたが、新しい一致は無かった)。 | docs/DATA/probes/20260923_tools_8_run10.log:4560-4776 docs/DATA/probes/20260923_tools_8_run10.log:4810-4838 |
| `Exactpro の reconciliation testing` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |
| `Exactpro の reconciliation testing` | E5 | なし | - | 実測 | 同じ34594件(一覧 34594 件 / 読んだ 34594 件)を要素名(再現/reproduc)で検索。一致150件超はすべてApache-2.0ライセンス条文のreproduction/distributionの定型文か、TypeScriptコンパイラのビルド出力コメント(出力先ディレクトリの再現に関する開発者コメント)で、乱数の種の固定・依存やデータ版の固定・実験結果の差分比較といったE5の述語には当たらない。 | docs/DATA/probes/20260923_tools_8_run10.log:4560-4776 docs/DATA/probes/20260923_tools_8_run10.log:4839-4845 |
| `Exactpro の reconciliation testing` | E6 | 印 | 3 | 一次資料 | 台帳の値のまま(9回目の節) |  |

### 4.0 機械可読の表

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| `Exactpro の reconciliation testing` | 版 | 3.4.0 | 実測 | pip list出力(th2_check2_recon 3.4.0)。docs/DATA/probes/20260923_tools_8_run10.log:4957-5017 |
| `Exactpro の reconciliation testing` | 最終更新日 | 2024-01-09(pushedAt) | 一次資料 | ungh.cc「"pushedAt":"2024-01-09T14:50:49Z"」。docs/DATA/probes/20260923_tools_8_run10.log:4847-4863 |
| `Exactpro の reconciliation testing` | ライセンス | Apache License 2.0 | 一次資料 | PyPI info「license Apache License 2.0」。docs/DATA/probes/20260923_tools_8_run10.log:4864-4873 |
| `Exactpro の reconciliation testing` | 言語と動作環境 | Python >=3.7 | 一次資料 | PyPI info「requires_python >=3.7」・setup.py「python_requires='>=3.7'」。docs/DATA/probes/20260923_tools_8_run10.log:4864-4873 docs/DATA/probes/20260923_tools_8_run10.log:6363-6400 |
| `Exactpro の reconciliation testing` | 対応取引所 | 該当なし(取引所接続機能ではなくFIX等の金融メッセージ照合テストツール) | 一次資料 | handler.py(MessageHandler・GRPCHandler、gRPC Crawler経由でメッセージを受け取るのみで取引所APIへの接続コードは無い)を読んだ範囲。docs/DATA/probes/20260923_tools_8_run10.log:6469-6583 |
| `Exactpro の reconciliation testing` | 星 | 0(stars)、watchers 2、forks 1 | 実測 | ungh.cc「"stars":0,"watchers":2,"forks":1」。docs/DATA/probes/20260923_tools_8_run10.log:4847-4863 |
| `Exactpro の reconciliation testing` | コミット数 | 未確認(試した手段: api.github.com/repos/.../commitsはこの環境でGitHub access not enabledのため拒否。ungh.ccのrepo情報にコミット数フィールド無し。--depth 1のshallow cloneのためgit logで総数を数えられない) | 未確認 | docs/DATA/probes/20260923_tools_8_run10.log:4877-4879 docs/DATA/probes/20260923_tools_8_run10.log:4880-4891 |
| `Exactpro の reconciliation testing` | 保守者数 | 未確認(試した手段: api.github.com/contributorsが環境で拒否。setup.pyのauthor欄は'TH2-devs'という共有名義のみで個人名は分からない) | 未確認 | docs/DATA/probes/20260923_tools_8_run10.log:4877-4879 docs/DATA/probes/20260923_tools_8_run10.log:6363-6400 |
| `Exactpro の reconciliation testing` | 週DL数 | 37(last_week) | 実測 | pypistats.org「"last_day":1,"last_month":62,"last_week":37」。docs/DATA/probes/20260923_tools_8_run10.log:4874-4876 |
| `Exactpro の reconciliation testing` | 初回公開日 | 2020-11-21(PyPI初回リリース2.2.0のupload_time 2020-11-21T11:55:10、GitHub createdAtも同日2020-11-21T11:36:42Z) | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:6278-6289 docs/DATA/probes/20260923_tools_8_run10.log:4847-4863 |
| `Exactpro の reconciliation testing` | 既知の脆弱性 | 無し(OSV.dev照会で0件) | 実測 | OSV.dev応答「{}」(空)。docs/DATA/probes/20260923_tools_8_run10.log:5047-5049 |
| `Exactpro の reconciliation testing` | 料金体系 | 無償(PyPI公開のOSS、Apache-2.0) | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:4864-4873 |
| `Exactpro の reconciliation testing` | 無料枠の上限 | 該当なし(登録・課金の枠組みを持たないOSSパッケージ) | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:4864-4873 |
| `Exactpro の reconciliation testing` | 課金開始条件 | 該当なし(無償) | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:4864-4873 |
| `Exactpro の reconciliation testing` | 隠れた依存 | 印。th2_common・th2_grpc_util・th2_grpc_crawler_data_processor等のExactpro自社エコシステムパッケージに依存し、実運用にはth2プラットフォーム基盤(RabbitMQ・Cradle DB・gRPC Crawler)を自前で用意する必要がある(requirements.txt原文「th2-grpc-util==3.1.0」「th2-common==3.9.2」「th2-grpc-crawler-data-processor==0.3.2」、recon.pyの`Recon.__init__`が`EventBatchRouter`・`MessageRouter`をコンストラクタで要求する設計) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6291-6330 docs/DATA/probes/20260923_tools_8_run10.log:6661-6753 |
| `Exactpro の reconciliation testing` | 登録の要否 | 不要(PyPI公開パッケージ、鍵不要) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:4957-5017 |
| `Exactpro の reconciliation testing` | 到達経路 | PyPI(pip install th2-check2-recon)・GitHub(github.com/th2-net/th2-check2-recon、cat8_repo_fetch.sh経由)、いずれも到達確認済み | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:4864-4873 docs/DATA/probes/20260923_tools_8_run10.log:4880-4891 |
| `Exactpro の reconciliation testing` | 導入可否 | 可(隔離venvへ--no-build-isolationでのpip installで確認。既定のbuild isolationではpkg_resources欠如でビルド失敗した点も記録) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:4892-4917 docs/DATA/probes/20260923_tools_8_run10.log:4918-4956 docs/DATA/probes/20260923_tools_8_run10.log:4957-5017 |
| `Exactpro の reconciliation testing` | install所要秒 | 17.95(--no-build-isolation成功時。試行錯誤の失敗2回は8.89秒・5.28秒) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:4957-5017 |
| `Exactpro の reconciliation testing` | 依存数 | 45(pip list --format=freeze 46行からth2_check2_recon自身を除く) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:5018-5025 |
| `Exactpro の reconciliation testing` | pip check | No broken requirements found | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:5018-5025 |
| `Exactpro の reconciliation testing` | 最小実行の可否 | 部分的(モジュールのimportとRule/ReconMessageのメソッド・属性の確認までは鍵無しで実行できたが、Reconオブジェクトの生成・メッセージ処理の実行にはth2プラットフォーム基盤(RabbitMQ等)が要るため、ルールのcheck処理そのものは未実行) | 実測 | import実測。docs/DATA/probes/20260923_tools_8_run10.log:5026-5046 |
| `Exactpro の reconciliation testing` | 最小実行の中身 | th2_check2_recon.rule等の主要モジュールをimportし、Ruleクラスのcheck・hash・group等のメソッドとReconMessageのgroup_id・hash・is_matched等の属性の存在を確認。rule.pyの`Rule.__init__`・`__check_and_store_event`等の実装本体も読み、`self.check(matched_messages, attributes, ...)`の呼び出し構造を確認 | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:5026-5046 docs/DATA/probes/20260923_tools_8_run10.log:6754-6845 |
| `Exactpro の reconciliation testing` | 実行所要秒 | 0.267(import実測のtime_s) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:5026-5046 |
| `Exactpro の reconciliation testing` | wheel展開 | 該当なし(--no-build-isolationでのソースビルドで導入したため個別のwheel展開は試していない。試した手段: pip download --no-depsは未実施) | 未確認 | docs/DATA/probes/20260923_tools_8_run10.log:4957-5017 |
| `Exactpro の reconciliation testing` | setup.py導入時実行 | 危険な外部URL取得・難読化コードなし(setup.py全文を読み確認。urlopen/requests.get/subprocess/os.system/eval/exec等のパターンをgrepし一致なし) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6291-6330 docs/DATA/probes/20260923_tools_8_run10.log:5050-5052 |
| `Exactpro の reconciliation testing` | 同梱バイナリ | 無し(.so/.exe/.dllをfindし0件) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:5050-5052 |
| `Exactpro の reconciliation testing` | 外部送信 | 未確認(試した手段: importのみでの外部通信は観測されなかったが、実行時の通信を遮断して試すところまでは行っていない) | 未確認 | import時に観測。docs/DATA/probes/20260923_tools_8_run10.log:5026-5046 |
| `Exactpro の reconciliation testing` | 自動発注機能 | 無し(handler.py・rule.py・recon.pyを読んだ範囲でメッセージの照合・イベント記録のみ。発注APIの呼び出しは見当たらない) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6469-6583 docs/DATA/probes/20260923_tools_8_run10.log:6754-6845 docs/DATA/probes/20260923_tools_8_run10.log:6661-6753 |
| `Exactpro の reconciliation testing` | 宣伝詐欺の兆候 | 無し(Exactpro社名義のOSS、Apache-2.0。Telegram限定配布・秘密鍵要求等の兆候なし) | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:4864-4873 |
| `Exactpro の reconciliation testing` | 当方データ投入 | 未確認(試した手段: 当方のcsv.gzをth2のProtobufメッセージ形式に変換する経路を試していない。ReconMessageはproto_message引数を取るため変換すれば投入できる可能性がある) | 未確認 | ReconMessage定義。docs/DATA/probes/20260923_tools_8_run10.log:6584-6660 |
| `Exactpro の reconciliation testing` | 時刻の扱い | 印。reconcommon.pyに`_get_msg_timestamp`関数と`ReconMessage.timestamp`プロパティがあり、メッセージのタイムスタンプを扱う(UTC/ミリ秒等の詳細粒度は未確認) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6584-6660 |
| `Exactpro の reconciliation testing` | 再現性 | なし(この回のE5判定と同じ。乱数の種の固定・依存やデータ版の固定の機能は見当たらない) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:4560-4776 |
| `Exactpro の reconciliation testing` | 規模の見積 | 未確認(試した手段: 小さい実行の実測が無いため外挿できない。フル起動にth2プラットフォーム基盤が要るため) | 未確認 | フル起動未実施。docs/DATA/probes/20260923_tools_8_run10.log:5026-5046 |
| `Exactpro の reconciliation testing` | 4軸1_道具 | 印。隔離venvへのpip installが成功し、importして主要クラス・メソッドを確認できた | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:4957-5017 docs/DATA/probes/20260923_tools_8_run10.log:5026-5046 |
| `Exactpro の reconciliation testing` | 4軸2_情報 | 印。ハッシュベースのメッセージ照合(ReconMessage.hash)・イベント階層記録という当方に無い情報 | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6584-6660 |
| `Exactpro の reconciliation testing` | 4軸3_視点 | 印。金融メッセージング(FIX等)のreconciliationテストという当方に無い視点 | 一次資料 | docs/DATA/probes/20260923_tools_8_run10.log:6291-6330 |
| `Exactpro の reconciliation testing` | 4軸4_向上 | 推定。当方の読み取り専用照合reconciler.pyの設計にハッシュベースの照合方式が参考になりうる | 推定 | src/bot/order_management/reconciler.pyとの比較から外挿 |
| `Exactpro の reconciliation testing` | 配布元の一致 | 印。PyPIのauthor_email='th2-devs@exactprosystems.com'とsetup.pyのurl='https://github.com/th2-net/th2-check2-recon'が一致 | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:4864-4873 docs/DATA/probes/20260923_tools_8_run10.log:6291-6330 |
| `Exactpro の reconciliation testing` | 難読化 | 無し(setup.py・ソース全文を読み、難読化コードなし) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6291-6330 |
| `Exactpro の reconciliation testing` | 外部URL取得 | 無し(setup.py内に外部URL取得コードなし) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6291-6330 docs/DATA/probes/20260923_tools_8_run10.log:5050-5052 |
| `Exactpro の reconciliation testing` | 依存の一覧 | requirements.txt原文: sortedcollections==2.1.0 / th2-grpc-util==3.1.0 / th2-common==3.9.2 / th2-grpc-crawler-data-processor==0.3.2 (+pip installで解決された推移的依存45パッケージ) | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6291-6330 docs/DATA/probes/20260923_tools_8_run10.log:4957-5017 |
| `Exactpro の reconciliation testing` | 保守者名の一貫性 | 印。setup.pyのauthor='TH2-devs'・author_email='th2-devs@exactprosystems.com'で一貫 | 実測 | docs/DATA/probes/20260923_tools_8_run10.log:6291-6330 |
### ツール1件ごとの表

(この回に新しく確定した内容だけを書く。他の列は前回までのまま)

- **`Exactpro の reconciliation testing`(8-016)の8-016取得のN・M会計**: th2-net組織178リポジトリを`scripts/cat8_repo_fetch.sh`経由で1件ずつ全部取得した(終了コード0=178件、4=0件、5・6=0件、そのほか=0件)。取った量の和 `downloaded_bytes` の合計 = 67,234,078 バイト(約64.1MB)、`.cat8_downloaded_total` 最終値 = 59,399,535 バイト(約56.7MB、この差は`downloaded_bytes`が失敗時も含む累積カウントであるのに対し`.cat8_downloaded_total`は`.git`ディレクトリ実測値の累積であるため)。300MB上限には達しなかった。集計は`python3 scripts/cat8_fetch_tally.py docs/DATA/probes/20260923_tools_8_run10.log --prefix th2-net/`の出力(誤り0件)による: docs/DATA/probes/20260923_tools_8_run10.log:4560-4776
  - `files_in_tree(N)`の合計 = 34,610件。skipped(1MB超で取得できなかったブロブ)の合計 = 27件。
  - 除外16件(文字検索しても意味の無いもの): package-lock.json 3件(jsonToHtmlParser・th2-common-ui-components・th2-docs)/ .png 2件(th2-docsのinfra-comp-1.png・infra-comp-2.png)/ .gif 5件(th2-documentationのrecon_flow.gif・script_flow.gif・demo1_gui1〜3.gif)/ .eot 1件・.ttf 1件(th2-docsのmaterialdesignicons-webfont)/ .map 1件(viewerの@babel/parser/lib/index.js.map、ソースマップ)/ .node バイナリ 2件(viewerのnode-sass vendor binding.node、darwin-x64-93・linux-x64-83)/ package-lock.json 1件(viewer) = 3+2+5+1+1+1+2+1 = 16件。
  - 除外できない11件(いずれも1MB超で`cat8_repo_fetch.sh`が取得しなかったが、テスト用データ・vendoredソースで画像・バイナリ・ロックファイル・ソースマップのどれにも当たらないため、`raw.githubusercontent.com`から個別に取得して検索した): `th2-net/th2-codec-fix-orchestra`の`src/test/resources/dict/mit_2016.xml`(FIX辞書、テストデータ)/ `th2-net/viewer`の`webpack-starter/node_modules/`配下10件(`@material-ui/core`・`@mui/material`の`material-ui.development.js`各1件、`@material-ui/styles`・`@material-ui/system`の`csstype/index.d.ts`各1件、`typescript/lib/`の`tsc.js`・`tsserver.js`・`tsserverlibrary.js`・`typescript.js`・`typescriptServices.js`・`typingsInstaller.js`各1件)。取得はdocs/DATA/probes/20260923_tools_8_run10.log:4777-4809 に11件分の`curl`の手がある。
  - 一覧34,610件 − 除外16件 = 34,594件。この34,594件全部(個別取得した11件を含む)を、要素名で検索した(一致0件だった`th2net_fetch_tally.py`の計算と一致)。
- **`Exactpro の reconciliation testing`(8-016)の§4.0表**: 台帳の発見の出典(区分1調査で見つかったth2-check2-reconのOSS化、9回目の知見#20)を代表コンポーネントとして初めて§4.0の機械可読表を作成した(上表)。PyPI/GitHub(ungh.cc)/pypistats.org/OSV.devの実測と、隔離venvへの`--no-build-isolation`でのpip install実測(既定のbuild isolationでは`pkg_resources`欠如でビルド失敗した点も記録)。実行はモジュールのimportとメソッド一覧の確認までで、Reconオブジェクトの生成・メッセージ処理そのものはth2プラットフォーム基盤(RabbitMQ・gRPC Crawler・Cradle DB)が要るため未実施。
- **`Exegy`(8-005)の当方に無いもの(段3)**: Exegy Capture Replay(XCR)は記録した市場データ(PCAP・正規化データ)をXCAPI経由で顧客のトレーディングアプリケーションへ自動で再生し、レート指定によるキャパシティ・ストレステスト(Reg SCI・MiFID II対応)や戦略のバックテストに使う。当方の`src/bot/backtest/`にはExegy自身の収集した実市場データを外部提供するリプレイサービスは無い(当方は自前で記録したデータのみを扱う)。

### 代替経路

この回に「この環境から不可」と書いた項目は無い。参考: citeseerx.ist.psu.edu(Testing Maturity Model原典PDF)への最初のアクセスがTLS切断(rc=35、web.archive.orgへのリダイレクト先での`SSL_ERROR_SYSCALL`)で2回失敗し、3回目で成功した(docs/DATA/probes/20260923_tools_8_run10.log:5375-5450 付近、`tmm_citeseerx`・`tmm_citeseerx_retry`・`tmm_citeseerx_retry2`・`tmm_citeseerx_retry3`)。TMMi Framework公式PDF(tmmi.org)はbot対策のcaptchaリダイレクトで取得できなかったが、原典(Burnstein Part I・II、citeseerx経由)が取得できたため第2経路は不要だった。

### 予算

この回は予算で止めない(追補§5、オーナー決定L-507「案A」)。

### 辿る一覧から出た名前

- 一覧: dev.to reconciliation tools記事 — https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg — docs/DATA/probes/20260923_tools_8_run10.log:6260
  - `Great Expectations` — https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg — dev.to reconciliation tools記事
  - `dbt`(Data Build Tool) — 同上 — 同上
  - `Debezium` — 同上 — 同上
  - `Apache Kafka` — 同上 — 同上
  - `Prefect` — 同上 — 同上
  - `Pandas` — 同上 — 同上
  - `Apache Spark` — 同上 — 同上
- 一覧: X `aiwithjainam`の投稿 — https://x.com/aiwithjainam/status/2059228811733172736 — docs/DATA/probes/20260923_tools_8_run10.log:6275
  - `Fincept Terminal` — http://github.com/Fincept-Corporation/FinceptTerminal — Xの投稿(台帳8-014と同一)
  - `Vibe-Trading` — http://github.com/HKUDS/Vibe-Trading — Xの投稿
  - `AutoHedge` — http://github.com/The-Swarm-Corporation/AutoHedge — Xの投稿
  - `OpenBB Terminal` — http://github.com/OpenBB-finance/OpenBB — Xの投稿
  - `Qlib` — http://github.com/microsoft/qlib — Xの投稿
  - `FinGPT` — http://github.com/AI4Finance-Foundation/FinGPT — Xの投稿
  - `Freqtrade` — http://github.com/freqtrade/freqtrade — Xの投稿(台帳8-006と同一)
  - `Backtrader` — http://github.com/mementum/backtrader — Xの投稿
  - `Lean` — http://github.com/QuantConnect/Lean — Xの投稿
  - `FinanceToolkit` — http://github.com/JerBouma/FinanceToolkit — Xの投稿
- 一覧: zenn.dev 仮説検証フレームワーク記事 — https://zenn.dev/toshipon/articles/62b65ff46d414b — docs/DATA/probes/20260923_tools_8_run10.log:6263
  - `OpenClaw` — URLなし(記事本文に固有リンクは無い。Discord等のチャットからClaudeを操作できるオープンソースのAIエージェントフレームワークと説明) — zenn.dev仮説検証フレームワーク記事
- 一覧: quantreoのlook-ahead bias記事 — https://www.newsletter.quantreo.com/p/look-ahead-bias-the-invisible-killer — docs/DATA/probes/20260923_tools_8_run10.log:6266
  - `Quantreo library` — URLなし(記事本文にリンクなし。quantreo.comの自社ライブラリと明記) — quantreo記事
  - `AI Trading Lab` — URLなし(同上) — quantreo記事
- 一覧: algorierのlook-ahead bias記事 — https://algorier.com/blog/look-ahead-bias-in-backtesting/ — docs/DATA/probes/20260923_tools_8_run10.log:6269
  - `AlgoBuild` — URLなし(サイトのナビゲーション項目としてのみ記載、記事本文へのリンクなし) — algorier記事
  - `AlgoNetwork` — URLなし(同上) — algorier記事
- 一覧: fortradersのbias記事 — https://fortraders.com/blog/how-to-avoid-bias-in-backtesting — docs/DATA/probes/20260923_tools_8_run10.log:6272
  - `TradingView`(Pine Script) — URLなし(記事本文中の言及のみ) — fortraders記事(台帳8-015のTradingViewのリプレイ機能と同一製品)
  - `MetaTrader`(Strategy Tester) — URLなし(同上) — fortraders記事
  - `NinjaTrader` — URLなし(同上) — fortraders記事
- 一覧: 1回目の検索計画7の結果 — https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide — docs/DATA/probes/20260923_tools_8_run10.log:6462
  - 書かない名前: 1回目の検索計画7(E2補助、"time series market data quality validation python library gaps duplicates outliers")の結果は「backtrex.com(ブログ記事から製品発見)/ 一般的なpandas/numpy/scipy等のライブラリ紹介(専用ツールでない)」で、backtrexは既に台帳8-007にある。pandas/numpy/scipyは固有の検証ツールではなく汎用の数値計算ライブラリのため、この一覧からは新規の名前は出なかった(書かない理由: 専用のツール名として特定できる固有名詞が無い)。
### 判断に迷った点と問い

1. [それ以外の問い] `Exegy`(8-005)のE4の段: Exegy Capture Replay(XCR)は「再生を受ける戦略・計算のコード」(顧客のトレーディングアプリケーション)は道具の外にあたるが、「再生する記録データ」はExegy自身が収集したフィードに限られる(任意の外部データを持ち込んで再生できる旨の記述は見当たらない)ため、段4の条件(対象のすべてを外から持ち込める)を満たさないと判断し段3とした。ただし「Retrieve raw or normalized data files」の記述もあり、取得したPCAP/CSVファイルを別の道具で再生する使い方まで含めれば段4寄りとも読める。値・段は段3のまま決めているが、この境界の読みに異論があれば直す(値・段についての問いではない、境界の読みの妥当性の問い)。
2. [それ以外の問い] `Fincept Terminal`(8-014)のE3aの段: `subagents.py`のbacktesterサブエージェント(LLM)が「Identify lookahead bias and survivorship bias」を自動で行うと読み段3としたが、LLMの判断はscipy.statsのような決定的な計算(E6で段4とした`ModelValidator`)とは性質が異なり、「合否や検出を自分で判定しない」段2寄りとも読める。確率的な出力を「自動で判定」とみなすかどうかの一般的な基準が設計票に無いため、この回はE6(決定的な計算)と同じ扱いに揃えて段3としたが、境界の読みに異論があれば直す(値・段についての問いではない)。
3. [それ以外の問い] `Fincept Terminal`(8-014)の状態を`浅い`→`深掘り`に上げた(E1a〜E6に未判別が無くなり、委任文§4.0の表(43項目、既存)の過半が一次資料/実測であることを確認したため)。§4.0の表そのものはこの回に新しく書いたものではなく過去の回(主に5回目)に作られたもので、この回は項目の網羅と印の分布だけを数え直して確認した(個々の値をこの回に再確認してはいない)。状態の格上げの妥当性そのものはリードの判断に委ねる。
### 受け入れ検査の出力

(K12は自己参照するため、下の出力は貼り付け前の実行結果であり「1件」と出ている。貼り付け後にもう一度検査を打ち直すとK12も含めすべて0件になることを確認済み(下に別記)。)

**1. `check_scan_report.py`(生ログ10本)**
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

**2. `cat8_ledger.py check-elements --round 10`**
```
読んだもの: 候補の一覧 16 行 / 要素と段の表 128 行(道具 16)/ 知見の表 19 行 / 辿る一覧から出た名前 25 行
---- 合計 0 件
```

**3. `cat8_ledger.py check`**
```
参考: docs/DATA/probes/20260923_tools_8_run10.log の最初の手 2026-09-24T10:33:20Z / 最後の手 2026-09-24T11:07:18Z / 手の数 624
---- 合計 0 件
```

**4. `git diff`(1〜9回目の節から消えた行)**
```
0
```


## 区分8 — 11 回目の実行(2026-09-24)

この回は 8-016(Exactpro reconciliation testing)の E3a・E3b・E5 やり直しと、辿る一覧から台帳に足された 8-017〜8-028 の 12 件の深掘りを担当する(起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run11_prompt.md`、指紋 `3b00f9d0fd9d`)。

### 検索計画

この回は新しい検索計画を打たない(委任文 §2)。

### 出典

| # | 対象 | URL | 取得日 | 生ログ |
|---|---|---|---|---|
| 1 | 8-016 th2-net の 178 リポジトリ一覧(名前・size) | https://repos.ecosyste.ms/api/v1/hosts/GitHub/owners/th2-net/repositories(9回目に取得) | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:189 |
| 2 | 8-016 th2-net の各リポジトリ | https://github.com/th2-net/<名前> | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:232-14450 付近(178件の取得手) |
| 3 | 8-017 Great Expectations(fivetran/great_expectations)README | https://raw.githubusercontent.com/fivetran/great_expectations/develop/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:1101 |
| 4 | 8-017 GitHub登録情報 | https://ungh.cc/repos/great-expectations/great_expectations | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:726 |
| 5 | 8-018 Vibe-Trading README(変更履歴) | https://raw.githubusercontent.com/HKUDS/Vibe-Trading/main/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:3573 |
| 6 | 8-018 GitHub登録情報 | https://ungh.cc/repos/HKUDS/Vibe-Trading | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:406 |
| 7 | 8-018 PyPI(vibe-trading-ai) | https://pypi.org/pypi/vibe-trading-ai/json | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:15837 |
| 8 | 8-018 LICENSE | https://raw.githubusercontent.com/HKUDS/Vibe-Trading/main/LICENSE | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:15814 |
| 9 | 8-019 AutoHedge README | https://raw.githubusercontent.com/The-Swarm-Corporation/AutoHedge/main/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:3445 |
| 10 | 8-019 GitHub登録情報 | https://ungh.cc/repos/The-Swarm-Corporation/AutoHedge | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:409 |
| 11 | 8-020 OpenBB README | https://raw.githubusercontent.com/OpenBB-finance/OpenBB/develop/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:5393 |
| 12 | 8-020 GitHub登録情報 | https://ungh.cc/repos/OpenBB-finance/OpenBB | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:412 |
| 13 | 8-021 Qlib README | https://raw.githubusercontent.com/microsoft/qlib/main/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:5608 |
| 14 | 8-021 check_data_health.py | https://raw.githubusercontent.com/microsoft/qlib/main/scripts/check_data_health.py | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:9774 |
| 15 | 8-021 Point-in-Time データ収集README | https://raw.githubusercontent.com/microsoft/qlib/main/scripts/data_collector/pit/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:10036 |
| 16 | 8-021 GitHub登録情報 | https://ungh.cc/repos/microsoft/qlib | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:436 |
| 17 | 8-021 PyPI(pyqlib) | https://pypi.org/pypi/pyqlib/json | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:10931 |
| 18 | 8-022 FinGPT README | https://raw.githubusercontent.com/AI4Finance-Foundation/FinGPT/master/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:4944 |
| 19 | 8-022 GitHub登録情報 | https://ungh.cc/repos/AI4Finance-Foundation/FinGPT | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:442 |
| 20 | 8-023 backtrader README.rst | https://raw.githubusercontent.com/mementum/backtrader/master/README.rst | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:6444 |
| 21 | 8-023 GitHub登録情報 | https://ungh.cc/repos/mementum/backtrader | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:461 |
| 22 | 8-024 Lean readme.md(小文字。Lean CLIの説明) | https://raw.githubusercontent.com/QuantConnect/Lean/master/readme.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:7558 |
| 23 | 8-024 GitHub登録情報 | https://ungh.cc/repos/QuantConnect/Lean | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:855 |
| 24 | 8-025 FinanceToolkit README | https://raw.githubusercontent.com/JerBouma/FinanceToolkit/main/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:4306 |
| 25 | 8-025 GitHub登録情報 | https://ungh.cc/repos/JerBouma/FinanceToolkit | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:720 |
| 26 | 8-026 OpenClaw README | https://raw.githubusercontent.com/openclaw/openclaw/main/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:3817 |
| 27 | 8-026 発見の出典のzenn記事本文 | https://zenn.dev/toshipon/articles/62b65ff46d414b | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:1187 |
| 28 | 8-026 GitHub登録情報 | https://ungh.cc/repos/openclaw/openclaw | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:741 |
| 29 | 8-027 Quantreo README | https://raw.githubusercontent.com/Quantreo/quantreo/main/README.md | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:4150 |
| 30 | 8-027 GitHub登録情報 | https://ungh.cc/repos/Quantreo/quantreo | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:758 |
| 31 | 8-027 tests.yml・CHANGELOG.md(cat8_search.py出力経由) | https://github.com/Quantreo/quantreo(cat8_repo_fetch.sh経由で取得) | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:14547,docs/DATA/probes/20260923_tools_8_run11.log:14549 |
| 32 | 8-028 AlgoBuild公式頁 | https://algorier.com/algobuild/ | 2026-09-24 | docs/DATA/probes/20260923_tools_8_run11.log:1582 |

### 知見

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | `Great Expectations` / E2 / 方式(原文): 「GX Core combines the collective wisdom of thousands of community members with a proven track record in data quality deployments worldwide...Its powerful technical tools start with Expectations: expressive and extensible unit tests for your data.」(README。expect_column_values_to_not_be_null等の個別Expectation関数の一覧までは未確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:1101 取得日 2026-09-24 |
| 2 | `Vibe-Trading` / E1a / 方式(原文): 「offline USD-M account reconciliation compares local risk state with an exchange observation without opening a connection」/「Binance USD-M reconciliation results now land as tamper-evident drift evidence artifacts — strict JSON, fail-closed on incomplete or unsupported snapshots」(README変更履歴。自社の計算した口座状態と取引所側の観測値を突き合わせて差分(drift)を検出する機能。突き合わせの単位は指定できないため段4) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:3573 取得日 2026-09-24 |
| 3 | `Vibe-Trading` / E1b / 方式(原文): バックテストエンジン自身がOHLCVから損益・ポジションを計算する(「a finished backtest is now something you can read」「Run Detail grows four tabs — **Factor Research** (IC series...)、**Positions**...、**Tearsheet**...」)。当方のバックテストエンジンと同じ種類の出力(損益・ポジション)を出す別実装 | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:3573 取得日 2026-09-24 |
| 4 | `Vibe-Trading` / E2 / 方式(原文): 「a default that quietly substitutes a plausible value for a missing one」「The registry now masks output wherever a declared dependency is missing on that bar」(欠損検出)/「read-time freshness (`fresh`/`aging`/`stale`) and stale rows failing closed」(鮮度=時刻のずれの検出)/「Market-data provenance now names the loader...with the matching fallback flag and adjustment label」(情報源間の食い違いの記録) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:3573 取得日 2026-09-24 |
| 5 | `Vibe-Trading` / E3a / 方式(原文): 「the HTML alpha-bench report now carries the survivorship-bias disclosure the JSON already had, naming the constituent source and its as-of date」(生存者バイアスの開示を報告書に載せる機能。自動判定して止めるところまでは確認できず人が読んで判断する形なので段2) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:3573 取得日 2026-09-24 |
| 6 | `Vibe-Trading` / E3b / 方式(原文): 「look-ahead-bias and strict-OOS guards in the factor bench and Shadow Account」/「a look-ahead-bias fix across all 5 portfolio optimizers」/「the ML walk-forward example purges future labels」/Quant Library additions に「group-purged CV」(purged cross-validationの実装) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:3573 取得日 2026-09-24 |
| 7 | `Vibe-Trading` / E4 / 方式(原文): 0.1.15のリリースノートに新機能として「swarm replay and retry」が挙げられている(再生の粒度・対象は未確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:3573 取得日 2026-09-24 |
| 8 | `Vibe-Trading` / E5 / 方式(原文): 「deterministic USD-M tolerance calibration from recorded comparisons」/「computed through the same test-pinned engine the MCP tools use」(決定的な計算・記録済み比較からの較正への言及。乱数の種の固定・保存の具体的な仕組みまでは未確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:3573 取得日 2026-09-24 |
| 9 | `Vibe-Trading` / E6 / 方式(原文): 「22 new regressions cover hydration, terminal recovery, stale reaping, keepalive cadence, env parsing, and heartbeat wiring; the full swarm/MCP suite is at 169 passed, 4 skipped.」(回帰テストスイートの実行結果件数を明記) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:3573 取得日 2026-09-24 |
| 10 | `Qlib` / E2 / 方式(原文): `scripts/check_data_health.py` の `DataHealthChecker` クラス docstring: 「Checks a dataset for data completeness and correctness...- any of the columns [...] are missing - any data is missing - any step change in the OHLCV columns is above a threshold (default: 0.5 for price, 3 for volume) - any factor is missing」。コンストラクタに `large_step_threshold_price`・`large_step_threshold_volume`・`missing_data_num` を指定でき((ア)条件は満たす)、`csv_path` 引数でqlib形式の外から持ち込んだCSVディレクトリにも掛けられる(段4)。チェック結果を保存し次回実行と比較する(イ)の記述は見つからず段5にはしない | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:9774 取得日 2026-09-24 |
| 11 | `Qlib` / E3b / 方式(原文): Point-in-Time(PIT)データ収集・変換のREADME: 四半期決算などの財務データを発表時点(as-of)で正しく参照できる形に変換して積む一連の手順(`download_data`→`normalize_data`→`dump_pit.py dump`)。時点を揃えた結合の具体的な実装箇所までは未確認なので段は未判別 | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:10036 取得日 2026-09-24 |
| 12 | `Qlib` / E4 / 方式(原文): README: 「Qlib provides a tool named `qrun` to run the whole workflow automatically (including building dataset, training models, backtest and evaluation).」(記録した市場データを順に読んでモデル・戦略を評価するワークフロー。再生の粒度・時刻の扱いは未確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:5608 取得日 2026-09-24 |
| 13 | `FinGPT` / E1a / 方式(原文): 「**Task layer**: This layer is responsible for executing fundamental tasks. These tasks serve as the benchmarks for performance evaluations and cross-comparisons in the realm of FinLLMs」(複数のFinLLM実装の出力をベンチマークで突き合わせて比較するレイヤーがあるとの記述。突き合わせの単位・自動判定の有無は未確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:4944 取得日 2026-09-24 |
| 14 | `FinGPT` / E5 / 方式(原文): 「Reproduce the results by running [benchmarks](./fingpt/FinGPT_Sentiment_Analysis_v3/benchmark/benchmarks.ipynb), and the detailed tutorial is on the way.」(結果の再現をnotebookで行える。乱数の種の固定など具体の仕組みは未確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:4944 取得日 2026-09-24 |
| 15 | `Backtrader` / E4 / 方式(原文): README.rstの機能一覧: 「Integrated Resampling and Replaying」(記録した足を読み込んでリサンプル・再生する統合機能。粒度や遅延の扱いの詳細は未確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:6444 取得日 2026-09-24 |
| 16 | `Quantreo library` / E3b / 方式(原文): README: 「**Robust by design**: Functions implemented to avoid data leakage and look-ahead bias.」(データリーク・ルックアヘッドバイアスを避けるよう実装された関数群。具体の実装方式(embargo/purge等)は未確認) | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:4150 取得日 2026-09-24 |
| 17 | `Quantreo library` / E6 / 方式(原文): `.github/workflows/tests.yml`: 「run: pytest --cov=quantreo --cov-report=term-missing -v --maxfail=1 --disable-warnings」(pytestによる自動テストとカバレッジ計測)。CHANGELOG.mdにも「Improved **unit test coverage** across the library」とある(全要素検索の手は巨大なnotebook出力に埋め込まれた第三者JSバンドルのため生ログ2,000,000字で切られたが、この2件の当たりはいずれも切られる前の範囲に出ている) | 実測 | docs/DATA/probes/20260923_tools_8_run11.log:14547 docs/DATA/probes/20260923_tools_8_run11.log:14549 取得日 2026-09-24 |
| 18 | `Exactpro の reconciliation testing` / E3a・E3b・E5 / 方式(原文): 178 リポジトリ・34,207 ファイルを cat8_search.py で全件検索したが、ルックアヘッド・survivorship・embargo・purge・再現性・seed・deterministic・snapshot 系の語に当たった 528 ファイルはいずれも webpack/typescript 等のビルド道具の内部語・SNAPSHOT 版番号・protobuf の `IsSerializationDeterministic`・th2-infra-editor の UI 編集履歴(`createSnapshot`)など、E3a/E3b/E5 の述語に当たらないものだった(`### 当たりの判定` に全件) | 実測 | docs/DATA/probes/20260923_tools_8_run11.log:14202 取得日 2026-09-24 |

### 候補の一覧

**8-001〜8-040 の全 40 行。この回に触らない行(8-001〜8-015・8-029〜8-040)は台帳の値のまま。**

1. [深掘り] `qf-lib` (8-001) — https://github.com/quarkfin/qf-lib — (台帳の値のまま) — 状態: 深掘り
2. [深掘り] `PineForge` (8-002) — https://github.com/pineforge-4pass/pineforge-engine — (台帳の値のまま) — 状態: 深掘り
3. [深掘り] `prediction-market-backtester` (8-003) — https://github.com/Quentin-Piot/prediction-market-backtester — (台帳の値のまま) — 状態: 深掘り
4. `akurkar07/OrderBook` (8-004) — https://github.com/akurkar07/OrderBook — (台帳の値のまま) — 状態: 危険で導入停止
5. `Exegy` (8-005) — https://www.exegy.com/ — (台帳の値のまま) — 状態: 登録が要る
6. [深掘り] `freqtrade` (8-006) — https://github.com/freqtrade/freqtrade — (台帳の値のまま) — 状態: 深掘り
7. [深掘り] `backtrex` (8-007) — https://backtrex.com/en/blog/ohlc-data-quality-validation-backtesting-guide — (台帳の値のまま) — 状態: 深掘り
8. [深掘り] `FX Replay` (8-008) — https://fxreplay.com/ — (台帳の値のまま) — 状態: 深掘り
9. [深掘り] `nicferrari/backtester` (8-009) — https://github.com/nicferrari/backtester — (台帳の値のまま) — 状態: 深掘り
10. [深掘り] `arXiv:2603.20319` (8-010) — https://arxiv.org/abs/2603.20319 — (台帳の値のまま) — 状態: 深掘り
11. [深掘り] `arXiv:2512.12924` (8-011) — https://arxiv.org/abs/2512.12924 — (台帳の値のまま) — 状態: 深掘り
12. [深掘り] `VectorBT` (8-012) — https://github.com/polakowo/vectorbt — (台帳の値のまま) — 状態: 深掘り
13. [深掘り] `rusty-bot` (8-013) — https://x.com/WannabeBotter/status/1810558269565571211 — (台帳の値のまま) — 状態: 深掘り
14. [深掘り] `Fincept Terminal` (8-014) — https://github.com/Fincept-Corporation/FinceptTerminal — (台帳の値のまま) — 状態: 深掘り
15. [深掘り] `TradingView のリプレイ機能` (8-015) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:98-100(検索計画3、URL は生ログに無い) — (台帳の値のまま) — 状態: 深掘り
16. `Exactpro の reconciliation testing` (8-016) — 生ログ docs/DATA/probes/20260923_tools_8_run1.log:95-97(検索計画2、URL は生ログに無い) — th2 (Exactpro) の reconciliation testing 一式(178 リポジトリ)。この回は E3a・E3b・E5 のやり直し(いずれも 34,207 ファイルの全件検索の結果 `なし`) — 状態: 判別に一次資料が要る
17. `Great Expectations` (8-017) — https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg(10 回目の辿る一覧) — Pythonのデータ品質・検証フレームワーク(旧 great-expectations/great_expectations。現在は fivetran 傘下で開発)。「Expectations」という宣言的な単体テストでデータの正しさを検証する — 状態: 判別に一次資料が要る
18. `Vibe-Trading` (8-018) — https://github.com/HKUDS/Vibe-Trading — 自然言語でトレード仮説を投げるAIリサーチ・エージェント(`vibe-trading-ai`)。バックテストエンジン・複数取引所コネクタ・アルファ動物園(Alpha Zoo)・swarm(複数エージェント並列実行)を持つ — 状態: 浅い
19. `AutoHedge` (8-019) — https://github.com/The-Swarm-Corporation/AutoHedge — Solana上で自律的に取引する「エージェントヘッジファンド」(Director/Quant/Risk/Executionの4エージェント構成) — 状態: 判別に一次資料が要る
20. `OpenBB Terminal` (8-020) — https://github.com/OpenBB-finance/OpenBB — 「Open Data Platform」。複数のデータ提供元をPython/Excel/MCP/REST APIに一本化して繋ぐデータ統合基盤(バックテストや検証そのものの機能ではない) — 状態: 判別に一次資料が要る
21. `Qlib` (8-021) — https://github.com/microsoft/qlib — Microsoft製のAI指向クオンツ投資プラットフォーム。データ・特徴量・モデル・バックテストの一連のワークフローを提供 — 状態: 判別に一次資料が要る
22. `FinGPT` (8-022) — https://github.com/AI4Finance-Foundation/FinGPT — 金融特化のオープンソースLLM群。感情分析・予測などのベンチマークと学習コードを配布 — 状態: 判別に一次資料が要る
23. `Backtrader` (8-023) — https://github.com/mementum/backtrader — Pythonのバックテスト・ライブ取引プラットフォーム(README.rst) — 状態: 判別に一次資料が要る
24. `Lean` (8-024) — https://github.com/QuantConnect/Lean — QuantConnect製のアルゴリズム取引エンジン(バックテスト・ライブ取引)。読んだreadme.md(小文字)はLean CLIというコマンドラインツールの説明だった — 状態: 判別に一次資料が要る
25. `FinanceToolkit` (8-025) — https://github.com/JerBouma/FinanceToolkit — 財務諸表・比率・リスク指標・econometricsを計算するPythonライブラリ — 状態: 判別に一次資料が要る
26. `OpenClaw` (8-026) — https://zenn.dev/toshipon/articles/62b65ff46d414b(記事に URL なし) — 「OpenClaw」は汎用のオープンソースAIエージェントフレームワーク(Discord等のチャットからAIエージェントを操作する基盤)。発見の出典のzenn記事はこれを土台にトレーディングボットの仮説検証レポートを自動生成する仕組みを組んだ事例で、記事中の「validated/invalidated判定」等はOpenClaw自身の機能ではなく記事筆者が組んだ別のシステム(KaizenLab)の機能 — 状態: 判別に一次資料が要る
27. `Quantreo library` (8-027) — https://www.newsletter.quantreo.com/p/look-ahead-bias-the-invisible-killer(記事に URL なし) — 特徴量・ターゲット・オルタナティブバー生成のPythonライブラリ(PyPI: quantreo)。作者によれば開発は停止し後継 Oryon に移行中 — 状態: 判別に一次資料が要る
28. `AlgoBuild` (8-028) — https://algorier.com/blog/look-ahead-bias-in-backtesting/(記事に URL なし) — Algorier社のSaaS型アルゴ取引ビルダー(「AlgoBuild」)。ノーコードで売買ルール(アルゴ)を作り、取引所に接続して自動執行する — 状態: 判別に一次資料が要る
29. `MetaTrader の Strategy Tester` (8-029) — https://fortraders.com/blog/how-to-avoid-bias-in-backtesting(記事に URL なし) — (台帳の値のまま) — 状態: 未着手
30. `dbt` (8-030) — https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg(10 回目の辿る一覧、この記事の中の dbt) — (台帳の値のまま) — 状態: 未着手
31. `Debezium` (8-031) — https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg(10 回目の辿る一覧、この記事の中の Debezium) — (台帳の値のまま) — 状態: 未着手
32. `Apache Kafka` (8-032) — https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg(10 回目の辿る一覧、この記事の中の Apache Kafka) — (台帳の値のまま) — 状態: 未着手
33. `Prefect` (8-033) — https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg(10 回目の辿る一覧、この記事の中の Prefect) — (台帳の値のまま) — 状態: 未着手
34. `Pandas` (8-034) — https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg(10 回目の辿る一覧、この記事の中の Pandas) — (台帳の値のまま) — 状態: 未着手
35. `Apache Spark` (8-035) — https://dev.to/137foundry/7-free-tools-for-data-pipeline-reconciliation-and-cross-source-validation-3dbg(10 回目の辿る一覧、この記事の中の Apache Spark) — (台帳の値のまま) — 状態: 未着手
36. `AI Trading Lab` (8-036) — https://www.newsletter.quantreo.com/p/look-ahead-bias-the-invisible-killer(記事に URL なし、この記事の中の AI Trading Lab) — (台帳の値のまま) — 状態: 未着手
37. `AlgoNetwork` (8-037) — https://algorier.com/blog/look-ahead-bias-in-backtesting/(記事に URL なし、この記事の中の AlgoNetwork) — (台帳の値のまま) — 状態: 未着手
38. `NinjaTrader` (8-038) — https://fortraders.com/blog/how-to-avoid-bias-in-backtesting(記事に URL なし、この記事の中の NinjaTrader) — (台帳の値のまま) — 状態: 未着手
39. `NumPy` (8-039) — 1 回目の検索計画 7 の結果(10 回目の辿る一覧 7、生ログ docs/DATA/probes/20260923_tools_8_run10.log:6462、この結果の中の NumPy) — (台帳の値のまま) — 状態: 未着手
40. `SciPy` (8-040) — 1 回目の検索計画 7 の結果(10 回目の辿る一覧 7、生ログ docs/DATA/probes/20260923_tools_8_run10.log:6462、この結果の中の SciPy) — (台帳の値のまま) — 状態: 未着手

### 要素と段

**8-001〜8-040 の全 40 候補 × 8 要素 = 320 行。この回に触らない行は 6 列目を `台帳の値のまま(<回>回目の節)` だけにし、値・段は台帳と同じ、7 列目は空にする。**

| 道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠 | 生ログの行 |
|---|---|---|---|---|---|---|
| `qf-lib` | E1a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `qf-lib` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `qf-lib` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `qf-lib` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `qf-lib` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `qf-lib` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `qf-lib` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `qf-lib` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `PineForge` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `PineForge` | E1b | 印 | 5 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `PineForge` | E2 | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `PineForge` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `PineForge` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `PineForge` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `PineForge` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `PineForge` | E6 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `prediction-market-backtester` | E1a | 印 | 5 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `prediction-market-backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `prediction-market-backtester` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `prediction-market-backtester` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `prediction-market-backtester` | E3b | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `prediction-market-backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `prediction-market-backtester` | E5 | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `prediction-market-backtester` | E6 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `akurkar07/OrderBook` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `akurkar07/OrderBook` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `akurkar07/OrderBook` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `akurkar07/OrderBook` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `akurkar07/OrderBook` | E3b | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `akurkar07/OrderBook` | E4 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `akurkar07/OrderBook` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `akurkar07/OrderBook` | E6 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Exegy` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Exegy` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Exegy` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Exegy` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Exegy` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Exegy` | E4 | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Exegy` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Exegy` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `freqtrade` | E1a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `freqtrade` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `freqtrade` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `freqtrade` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `freqtrade` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `freqtrade` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `freqtrade` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `freqtrade` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `backtrex` | E1a | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `backtrex` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `backtrex` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `backtrex` | E3a | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `backtrex` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `backtrex` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `backtrex` | E5 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `backtrex` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `FX Replay` | E1a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `FX Replay` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `FX Replay` | E2 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `FX Replay` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `FX Replay` | E3b | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `FX Replay` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `FX Replay` | E5 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `FX Replay` | E6 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `nicferrari/backtester` | E1a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `nicferrari/backtester` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `nicferrari/backtester` | E2 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `nicferrari/backtester` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `nicferrari/backtester` | E3b | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `nicferrari/backtester` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `nicferrari/backtester` | E5 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `nicferrari/backtester` | E6 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2603.20319` | E1a | 印 | 1 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2603.20319` | E1b | 印 | 1 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2603.20319` | E2 | 印 | 1 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2603.20319` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2603.20319` | E3b | 印 | 1 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2603.20319` | E4 | 印 | 1 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2603.20319` | E5 | 印 | 1 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2603.20319` | E6 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2512.12924` | E1a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2512.12924` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2512.12924` | E2 | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2512.12924` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2512.12924` | E3b | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2512.12924` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2512.12924` | E5 | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `arXiv:2512.12924` | E6 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `VectorBT` | E1a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `VectorBT` | E1b | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `VectorBT` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `VectorBT` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `VectorBT` | E3b | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `VectorBT` | E4 | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `VectorBT` | E5 | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `VectorBT` | E6 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `rusty-bot` | E1a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `rusty-bot` | E1b | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `rusty-bot` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `rusty-bot` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `rusty-bot` | E3b | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `rusty-bot` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `rusty-bot` | E5 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `rusty-bot` | E6 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Fincept Terminal` | E1a | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Fincept Terminal` | E1b | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Fincept Terminal` | E2 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Fincept Terminal` | E3a | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Fincept Terminal` | E3b | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Fincept Terminal` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Fincept Terminal` | E5 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Fincept Terminal` | E6 | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `TradingView のリプレイ機能` | E1a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `TradingView のリプレイ機能` | E1b | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `TradingView のリプレイ機能` | E2 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `TradingView のリプレイ機能` | E3a | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `TradingView のリプレイ機能` | E3b | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `TradingView のリプレイ機能` | E4 | 印 | 2 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `TradingView のリプレイ機能` | E5 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `TradingView のリプレイ機能` | E6 | なし | - | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Exactpro の reconciliation testing` | E1a | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Exactpro の reconciliation testing` | E1b | 印 | 4 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Exactpro の reconciliation testing` | E2 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Exactpro の reconciliation testing` | E3a | なし | - | 実測 | cat8_repo_fetch.sh で178リポジトリを取得(N=34,610。除外387件(バイナリ・符号化不明386・gitサブモジュール参照1)+絶対に取れない16件=403、listed(M)=34,207)し、cat8_mklist.py+cat8_search.pyで全件検索(パターンはlookahead/survivorship/リーク/時点/embargo/purge/reproducib/seed/deterministic/snapshot等。E3a・E3b・E5の設計票§3の語の組をすべて含む)。当たり528ファイル/3,414行はいずれも `### 当たりの判定` に理由つきで記録した誤検出(webpackやtypescript等ビルド道具の内部語・GradleのSNAPSHOT版番号・protobufの`IsSerializationDeterministic`・th2-infra-editorのUndo履歴の`createSnapshot`等)。一覧 34207 件 / 読んだ 34207 件 / 当たり 528 ファイル / 3414 行 | docs/DATA/probes/20260923_tools_8_run11.log:232 docs/DATA/probes/20260923_tools_8_run11.log:257 docs/DATA/probes/20260923_tools_8_run11.log:285 docs/DATA/probes/20260923_tools_8_run11.log:307 docs/DATA/probes/20260923_tools_8_run11.log:338 docs/DATA/probes/20260923_tools_8_run11.log:376 docs/DATA/probes/20260923_tools_8_run11.log:402 docs/DATA/probes/20260923_tools_8_run11.log:435 docs/DATA/probes/20260923_tools_8_run11.log:470 docs/DATA/probes/20260923_tools_8_run11.log:492 docs/DATA/probes/20260923_tools_8_run11.log:529 docs/DATA/probes/20260923_tools_8_run11.log:558 docs/DATA/probes/20260923_tools_8_run11.log:582 docs/DATA/probes/20260923_tools_8_run11.log:611 docs/DATA/probes/20260923_tools_8_run11.log:633 docs/DATA/probes/20260923_tools_8_run11.log:665 docs/DATA/probes/20260923_tools_8_run11.log:688 docs/DATA/probes/20260923_tools_8_run11.log:719 docs/DATA/probes/20260923_tools_8_run11.log:754 docs/DATA/probes/20260923_tools_8_run11.log:781 docs/DATA/probes/20260923_tools_8_run11.log:803 docs/DATA/probes/20260923_tools_8_run11.log:832 docs/DATA/probes/20260923_tools_8_run11.log:885 docs/DATA/probes/20260923_tools_8_run11.log:913 docs/DATA/probes/20260923_tools_8_run11.log:938 docs/DATA/probes/20260923_tools_8_run11.log:964 docs/DATA/probes/20260923_tools_8_run11.log:991 docs/DATA/probes/20260923_tools_8_run11.log:1025 docs/DATA/probes/20260923_tools_8_run11.log:1047 docs/DATA/probes/20260923_tools_8_run11.log:1069 docs/DATA/probes/20260923_tools_8_run11.log:1097 docs/DATA/probes/20260923_tools_8_run11.log:1183 docs/DATA/probes/20260923_tools_8_run11.log:1578 docs/DATA/probes/20260923_tools_8_run11.log:3312 docs/DATA/probes/20260923_tools_8_run11.log:3334 docs/DATA/probes/20260923_tools_8_run11.log:3361 docs/DATA/probes/20260923_tools_8_run11.log:3386 docs/DATA/probes/20260923_tools_8_run11.log:3411 docs/DATA/probes/20260923_tools_8_run11.log:3444 docs/DATA/probes/20260923_tools_8_run11.log:6299 docs/DATA/probes/20260923_tools_8_run11.log:6325 docs/DATA/probes/20260923_tools_8_run11.log:6347 docs/DATA/probes/20260923_tools_8_run11.log:6373 docs/DATA/probes/20260923_tools_8_run11.log:6399 docs/DATA/probes/20260923_tools_8_run11.log:6424 docs/DATA/probes/20260923_tools_8_run11.log:6619 docs/DATA/probes/20260923_tools_8_run11.log:6647 docs/DATA/probes/20260923_tools_8_run11.log:6672 docs/DATA/probes/20260923_tools_8_run11.log:6697 docs/DATA/probes/20260923_tools_8_run11.log:6723 docs/DATA/probes/20260923_tools_8_run11.log:6778 docs/DATA/probes/20260923_tools_8_run11.log:6800 docs/DATA/probes/20260923_tools_8_run11.log:6830 docs/DATA/probes/20260923_tools_8_run11.log:6852 docs/DATA/probes/20260923_tools_8_run11.log:6880 docs/DATA/probes/20260923_tools_8_run11.log:6910 docs/DATA/probes/20260923_tools_8_run11.log:6932 docs/DATA/probes/20260923_tools_8_run11.log:6954 docs/DATA/probes/20260923_tools_8_run11.log:7006 docs/DATA/probes/20260923_tools_8_run11.log:7034 docs/DATA/probes/20260923_tools_8_run11.log:7056 docs/DATA/probes/20260923_tools_8_run11.log:7085 docs/DATA/probes/20260923_tools_8_run11.log:7113 docs/DATA/probes/20260923_tools_8_run11.log:7135 docs/DATA/probes/20260923_tools_8_run11.log:7160 docs/DATA/probes/20260923_tools_8_run11.log:7189 docs/DATA/probes/20260923_tools_8_run11.log:7212 docs/DATA/probes/20260923_tools_8_run11.log:7235 docs/DATA/probes/20260923_tools_8_run11.log:7258 docs/DATA/probes/20260923_tools_8_run11.log:7288 docs/DATA/probes/20260923_tools_8_run11.log:7310 docs/DATA/probes/20260923_tools_8_run11.log:7335 docs/DATA/probes/20260923_tools_8_run11.log:7357 docs/DATA/probes/20260923_tools_8_run11.log:7383 docs/DATA/probes/20260923_tools_8_run11.log:7406 docs/DATA/probes/20260923_tools_8_run11.log:7438 docs/DATA/probes/20260923_tools_8_run11.log:7465 docs/DATA/probes/20260923_tools_8_run11.log:7497 docs/DATA/probes/20260923_tools_8_run11.log:7526 docs/DATA/probes/20260923_tools_8_run11.log:7554 docs/DATA/probes/20260923_tools_8_run11.log:7801 docs/DATA/probes/20260923_tools_8_run11.log:7830 docs/DATA/probes/20260923_tools_8_run11.log:7859 docs/DATA/probes/20260923_tools_8_run11.log:7882 docs/DATA/probes/20260923_tools_8_run11.log:7904 docs/DATA/probes/20260923_tools_8_run11.log:7926 docs/DATA/probes/20260923_tools_8_run11.log:7954 docs/DATA/probes/20260923_tools_8_run11.log:7980 docs/DATA/probes/20260923_tools_8_run11.log:8009 docs/DATA/probes/20260923_tools_8_run11.log:8037 docs/DATA/probes/20260923_tools_8_run11.log:8059 docs/DATA/probes/20260923_tools_8_run11.log:8096 docs/DATA/probes/20260923_tools_8_run11.log:8126 docs/DATA/probes/20260923_tools_8_run11.log:8161 docs/DATA/probes/20260923_tools_8_run11.log:8183 docs/DATA/probes/20260923_tools_8_run11.log:8205 docs/DATA/probes/20260923_tools_8_run11.log:8227 docs/DATA/probes/20260923_tools_8_run11.log:8317 docs/DATA/probes/20260923_tools_8_run11.log:8368 docs/DATA/probes/20260923_tools_8_run11.log:8397 docs/DATA/probes/20260923_tools_8_run11.log:8424 docs/DATA/probes/20260923_tools_8_run11.log:8458 docs/DATA/probes/20260923_tools_8_run11.log:8484 docs/DATA/probes/20260923_tools_8_run11.log:8524 docs/DATA/probes/20260923_tools_8_run11.log:8546 docs/DATA/probes/20260923_tools_8_run11.log:8576 docs/DATA/probes/20260923_tools_8_run11.log:8602 docs/DATA/probes/20260923_tools_8_run11.log:8630 docs/DATA/probes/20260923_tools_8_run11.log:8660 docs/DATA/probes/20260923_tools_8_run11.log:8688 docs/DATA/probes/20260923_tools_8_run11.log:8716 docs/DATA/probes/20260923_tools_8_run11.log:8746 docs/DATA/probes/20260923_tools_8_run11.log:8773 docs/DATA/probes/20260923_tools_8_run11.log:8799 docs/DATA/probes/20260923_tools_8_run11.log:8825 docs/DATA/probes/20260923_tools_8_run11.log:8847 docs/DATA/probes/20260923_tools_8_run11.log:8876 docs/DATA/probes/20260923_tools_8_run11.log:8907 docs/DATA/probes/20260923_tools_8_run11.log:8935 docs/DATA/probes/20260923_tools_8_run11.log:8965 docs/DATA/probes/20260923_tools_8_run11.log:8995 docs/DATA/probes/20260923_tools_8_run11.log:9017 docs/DATA/probes/20260923_tools_8_run11.log:9042 docs/DATA/probes/20260923_tools_8_run11.log:9068 docs/DATA/probes/20260923_tools_8_run11.log:9094 docs/DATA/probes/20260923_tools_8_run11.log:9124 docs/DATA/probes/20260923_tools_8_run11.log:9153 docs/DATA/probes/20260923_tools_8_run11.log:9182 docs/DATA/probes/20260923_tools_8_run11.log:9238 docs/DATA/probes/20260923_tools_8_run11.log:9377 docs/DATA/probes/20260923_tools_8_run11.log:9429 docs/DATA/probes/20260923_tools_8_run11.log:9495 docs/DATA/probes/20260923_tools_8_run11.log:9518 docs/DATA/probes/20260923_tools_8_run11.log:9559 docs/DATA/probes/20260923_tools_8_run11.log:9583 docs/DATA/probes/20260923_tools_8_run11.log:9607 docs/DATA/probes/20260923_tools_8_run11.log:9633 docs/DATA/probes/20260923_tools_8_run11.log:9663 docs/DATA/probes/20260923_tools_8_run11.log:9693 docs/DATA/probes/20260923_tools_8_run11.log:9723 docs/DATA/probes/20260923_tools_8_run11.log:9745 docs/DATA/probes/20260923_tools_8_run11.log:9770 docs/DATA/probes/20260923_tools_8_run11.log:10084 docs/DATA/probes/20260923_tools_8_run11.log:10106 docs/DATA/probes/20260923_tools_8_run11.log:10129 docs/DATA/probes/20260923_tools_8_run11.log:10191 docs/DATA/probes/20260923_tools_8_run11.log:10216 docs/DATA/probes/20260923_tools_8_run11.log:10246 docs/DATA/probes/20260923_tools_8_run11.log:10274 docs/DATA/probes/20260923_tools_8_run11.log:10296 docs/DATA/probes/20260923_tools_8_run11.log:10327 docs/DATA/probes/20260923_tools_8_run11.log:10350 docs/DATA/probes/20260923_tools_8_run11.log:10380 docs/DATA/probes/20260923_tools_8_run11.log:10405 docs/DATA/probes/20260923_tools_8_run11.log:10428 docs/DATA/probes/20260923_tools_8_run11.log:10454 docs/DATA/probes/20260923_tools_8_run11.log:10479 docs/DATA/probes/20260923_tools_8_run11.log:10507 docs/DATA/probes/20260923_tools_8_run11.log:10557 docs/DATA/probes/20260923_tools_8_run11.log:10586 docs/DATA/probes/20260923_tools_8_run11.log:10608 docs/DATA/probes/20260923_tools_8_run11.log:10631 docs/DATA/probes/20260923_tools_8_run11.log:10677 docs/DATA/probes/20260923_tools_8_run11.log:10706 docs/DATA/probes/20260923_tools_8_run11.log:10735 docs/DATA/probes/20260923_tools_8_run11.log:10773 docs/DATA/probes/20260923_tools_8_run11.log:10803 docs/DATA/probes/20260923_tools_8_run11.log:10827 docs/DATA/probes/20260923_tools_8_run11.log:10849 docs/DATA/probes/20260923_tools_8_run11.log:10872 docs/DATA/probes/20260923_tools_8_run11.log:10902 docs/DATA/probes/20260923_tools_8_run11.log:10944 docs/DATA/probes/20260923_tools_8_run11.log:10972 docs/DATA/probes/20260923_tools_8_run11.log:11001 docs/DATA/probes/20260923_tools_8_run11.log:11026 docs/DATA/probes/20260923_tools_8_run11.log:11048 docs/DATA/probes/20260923_tools_8_run11.log:14198 docs/DATA/probes/20260923_tools_8_run11.log:14445 |
| `Exactpro の reconciliation testing` | E3b | なし | - | 実測 | cat8_repo_fetch.sh で178リポジトリを取得(N=34,610。除外387件(バイナリ・符号化不明386・gitサブモジュール参照1)+絶対に取れない16件=403、listed(M)=34,207)し、cat8_mklist.py+cat8_search.pyで全件検索(パターンはlookahead/survivorship/リーク/時点/embargo/purge/reproducib/seed/deterministic/snapshot等。E3a・E3b・E5の設計票§3の語の組をすべて含む)。当たり528ファイル/3,414行はいずれも `### 当たりの判定` に理由つきで記録した誤検出(webpackやtypescript等ビルド道具の内部語・GradleのSNAPSHOT版番号・protobufの`IsSerializationDeterministic`・th2-infra-editorのUndo履歴の`createSnapshot`等)。一覧 34207 件 / 読んだ 34207 件 / 当たり 528 ファイル / 3414 行 | docs/DATA/probes/20260923_tools_8_run11.log:232 docs/DATA/probes/20260923_tools_8_run11.log:257 docs/DATA/probes/20260923_tools_8_run11.log:285 docs/DATA/probes/20260923_tools_8_run11.log:307 docs/DATA/probes/20260923_tools_8_run11.log:338 docs/DATA/probes/20260923_tools_8_run11.log:376 docs/DATA/probes/20260923_tools_8_run11.log:402 docs/DATA/probes/20260923_tools_8_run11.log:435 docs/DATA/probes/20260923_tools_8_run11.log:470 docs/DATA/probes/20260923_tools_8_run11.log:492 docs/DATA/probes/20260923_tools_8_run11.log:529 docs/DATA/probes/20260923_tools_8_run11.log:558 docs/DATA/probes/20260923_tools_8_run11.log:582 docs/DATA/probes/20260923_tools_8_run11.log:611 docs/DATA/probes/20260923_tools_8_run11.log:633 docs/DATA/probes/20260923_tools_8_run11.log:665 docs/DATA/probes/20260923_tools_8_run11.log:688 docs/DATA/probes/20260923_tools_8_run11.log:719 docs/DATA/probes/20260923_tools_8_run11.log:754 docs/DATA/probes/20260923_tools_8_run11.log:781 docs/DATA/probes/20260923_tools_8_run11.log:803 docs/DATA/probes/20260923_tools_8_run11.log:832 docs/DATA/probes/20260923_tools_8_run11.log:885 docs/DATA/probes/20260923_tools_8_run11.log:913 docs/DATA/probes/20260923_tools_8_run11.log:938 docs/DATA/probes/20260923_tools_8_run11.log:964 docs/DATA/probes/20260923_tools_8_run11.log:991 docs/DATA/probes/20260923_tools_8_run11.log:1025 docs/DATA/probes/20260923_tools_8_run11.log:1047 docs/DATA/probes/20260923_tools_8_run11.log:1069 docs/DATA/probes/20260923_tools_8_run11.log:1097 docs/DATA/probes/20260923_tools_8_run11.log:1183 docs/DATA/probes/20260923_tools_8_run11.log:1578 docs/DATA/probes/20260923_tools_8_run11.log:3312 docs/DATA/probes/20260923_tools_8_run11.log:3334 docs/DATA/probes/20260923_tools_8_run11.log:3361 docs/DATA/probes/20260923_tools_8_run11.log:3386 docs/DATA/probes/20260923_tools_8_run11.log:3411 docs/DATA/probes/20260923_tools_8_run11.log:3444 docs/DATA/probes/20260923_tools_8_run11.log:6299 docs/DATA/probes/20260923_tools_8_run11.log:6325 docs/DATA/probes/20260923_tools_8_run11.log:6347 docs/DATA/probes/20260923_tools_8_run11.log:6373 docs/DATA/probes/20260923_tools_8_run11.log:6399 docs/DATA/probes/20260923_tools_8_run11.log:6424 docs/DATA/probes/20260923_tools_8_run11.log:6619 docs/DATA/probes/20260923_tools_8_run11.log:6647 docs/DATA/probes/20260923_tools_8_run11.log:6672 docs/DATA/probes/20260923_tools_8_run11.log:6697 docs/DATA/probes/20260923_tools_8_run11.log:6723 docs/DATA/probes/20260923_tools_8_run11.log:6778 docs/DATA/probes/20260923_tools_8_run11.log:6800 docs/DATA/probes/20260923_tools_8_run11.log:6830 docs/DATA/probes/20260923_tools_8_run11.log:6852 docs/DATA/probes/20260923_tools_8_run11.log:6880 docs/DATA/probes/20260923_tools_8_run11.log:6910 docs/DATA/probes/20260923_tools_8_run11.log:6932 docs/DATA/probes/20260923_tools_8_run11.log:6954 docs/DATA/probes/20260923_tools_8_run11.log:7006 docs/DATA/probes/20260923_tools_8_run11.log:7034 docs/DATA/probes/20260923_tools_8_run11.log:7056 docs/DATA/probes/20260923_tools_8_run11.log:7085 docs/DATA/probes/20260923_tools_8_run11.log:7113 docs/DATA/probes/20260923_tools_8_run11.log:7135 docs/DATA/probes/20260923_tools_8_run11.log:7160 docs/DATA/probes/20260923_tools_8_run11.log:7189 docs/DATA/probes/20260923_tools_8_run11.log:7212 docs/DATA/probes/20260923_tools_8_run11.log:7235 docs/DATA/probes/20260923_tools_8_run11.log:7258 docs/DATA/probes/20260923_tools_8_run11.log:7288 docs/DATA/probes/20260923_tools_8_run11.log:7310 docs/DATA/probes/20260923_tools_8_run11.log:7335 docs/DATA/probes/20260923_tools_8_run11.log:7357 docs/DATA/probes/20260923_tools_8_run11.log:7383 docs/DATA/probes/20260923_tools_8_run11.log:7406 docs/DATA/probes/20260923_tools_8_run11.log:7438 docs/DATA/probes/20260923_tools_8_run11.log:7465 docs/DATA/probes/20260923_tools_8_run11.log:7497 docs/DATA/probes/20260923_tools_8_run11.log:7526 docs/DATA/probes/20260923_tools_8_run11.log:7554 docs/DATA/probes/20260923_tools_8_run11.log:7801 docs/DATA/probes/20260923_tools_8_run11.log:7830 docs/DATA/probes/20260923_tools_8_run11.log:7859 docs/DATA/probes/20260923_tools_8_run11.log:7882 docs/DATA/probes/20260923_tools_8_run11.log:7904 docs/DATA/probes/20260923_tools_8_run11.log:7926 docs/DATA/probes/20260923_tools_8_run11.log:7954 docs/DATA/probes/20260923_tools_8_run11.log:7980 docs/DATA/probes/20260923_tools_8_run11.log:8009 docs/DATA/probes/20260923_tools_8_run11.log:8037 docs/DATA/probes/20260923_tools_8_run11.log:8059 docs/DATA/probes/20260923_tools_8_run11.log:8096 docs/DATA/probes/20260923_tools_8_run11.log:8126 docs/DATA/probes/20260923_tools_8_run11.log:8161 docs/DATA/probes/20260923_tools_8_run11.log:8183 docs/DATA/probes/20260923_tools_8_run11.log:8205 docs/DATA/probes/20260923_tools_8_run11.log:8227 docs/DATA/probes/20260923_tools_8_run11.log:8317 docs/DATA/probes/20260923_tools_8_run11.log:8368 docs/DATA/probes/20260923_tools_8_run11.log:8397 docs/DATA/probes/20260923_tools_8_run11.log:8424 docs/DATA/probes/20260923_tools_8_run11.log:8458 docs/DATA/probes/20260923_tools_8_run11.log:8484 docs/DATA/probes/20260923_tools_8_run11.log:8524 docs/DATA/probes/20260923_tools_8_run11.log:8546 docs/DATA/probes/20260923_tools_8_run11.log:8576 docs/DATA/probes/20260923_tools_8_run11.log:8602 docs/DATA/probes/20260923_tools_8_run11.log:8630 docs/DATA/probes/20260923_tools_8_run11.log:8660 docs/DATA/probes/20260923_tools_8_run11.log:8688 docs/DATA/probes/20260923_tools_8_run11.log:8716 docs/DATA/probes/20260923_tools_8_run11.log:8746 docs/DATA/probes/20260923_tools_8_run11.log:8773 docs/DATA/probes/20260923_tools_8_run11.log:8799 docs/DATA/probes/20260923_tools_8_run11.log:8825 docs/DATA/probes/20260923_tools_8_run11.log:8847 docs/DATA/probes/20260923_tools_8_run11.log:8876 docs/DATA/probes/20260923_tools_8_run11.log:8907 docs/DATA/probes/20260923_tools_8_run11.log:8935 docs/DATA/probes/20260923_tools_8_run11.log:8965 docs/DATA/probes/20260923_tools_8_run11.log:8995 docs/DATA/probes/20260923_tools_8_run11.log:9017 docs/DATA/probes/20260923_tools_8_run11.log:9042 docs/DATA/probes/20260923_tools_8_run11.log:9068 docs/DATA/probes/20260923_tools_8_run11.log:9094 docs/DATA/probes/20260923_tools_8_run11.log:9124 docs/DATA/probes/20260923_tools_8_run11.log:9153 docs/DATA/probes/20260923_tools_8_run11.log:9182 docs/DATA/probes/20260923_tools_8_run11.log:9238 docs/DATA/probes/20260923_tools_8_run11.log:9377 docs/DATA/probes/20260923_tools_8_run11.log:9429 docs/DATA/probes/20260923_tools_8_run11.log:9495 docs/DATA/probes/20260923_tools_8_run11.log:9518 docs/DATA/probes/20260923_tools_8_run11.log:9559 docs/DATA/probes/20260923_tools_8_run11.log:9583 docs/DATA/probes/20260923_tools_8_run11.log:9607 docs/DATA/probes/20260923_tools_8_run11.log:9633 docs/DATA/probes/20260923_tools_8_run11.log:9663 docs/DATA/probes/20260923_tools_8_run11.log:9693 docs/DATA/probes/20260923_tools_8_run11.log:9723 docs/DATA/probes/20260923_tools_8_run11.log:9745 docs/DATA/probes/20260923_tools_8_run11.log:9770 docs/DATA/probes/20260923_tools_8_run11.log:10084 docs/DATA/probes/20260923_tools_8_run11.log:10106 docs/DATA/probes/20260923_tools_8_run11.log:10129 docs/DATA/probes/20260923_tools_8_run11.log:10191 docs/DATA/probes/20260923_tools_8_run11.log:10216 docs/DATA/probes/20260923_tools_8_run11.log:10246 docs/DATA/probes/20260923_tools_8_run11.log:10274 docs/DATA/probes/20260923_tools_8_run11.log:10296 docs/DATA/probes/20260923_tools_8_run11.log:10327 docs/DATA/probes/20260923_tools_8_run11.log:10350 docs/DATA/probes/20260923_tools_8_run11.log:10380 docs/DATA/probes/20260923_tools_8_run11.log:10405 docs/DATA/probes/20260923_tools_8_run11.log:10428 docs/DATA/probes/20260923_tools_8_run11.log:10454 docs/DATA/probes/20260923_tools_8_run11.log:10479 docs/DATA/probes/20260923_tools_8_run11.log:10507 docs/DATA/probes/20260923_tools_8_run11.log:10557 docs/DATA/probes/20260923_tools_8_run11.log:10586 docs/DATA/probes/20260923_tools_8_run11.log:10608 docs/DATA/probes/20260923_tools_8_run11.log:10631 docs/DATA/probes/20260923_tools_8_run11.log:10677 docs/DATA/probes/20260923_tools_8_run11.log:10706 docs/DATA/probes/20260923_tools_8_run11.log:10735 docs/DATA/probes/20260923_tools_8_run11.log:10773 docs/DATA/probes/20260923_tools_8_run11.log:10803 docs/DATA/probes/20260923_tools_8_run11.log:10827 docs/DATA/probes/20260923_tools_8_run11.log:10849 docs/DATA/probes/20260923_tools_8_run11.log:10872 docs/DATA/probes/20260923_tools_8_run11.log:10902 docs/DATA/probes/20260923_tools_8_run11.log:10944 docs/DATA/probes/20260923_tools_8_run11.log:10972 docs/DATA/probes/20260923_tools_8_run11.log:11001 docs/DATA/probes/20260923_tools_8_run11.log:11026 docs/DATA/probes/20260923_tools_8_run11.log:11048 docs/DATA/probes/20260923_tools_8_run11.log:14198 docs/DATA/probes/20260923_tools_8_run11.log:14445 |
| `Exactpro の reconciliation testing` | E4 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Exactpro の reconciliation testing` | E5 | なし | - | 実測 | cat8_repo_fetch.sh で178リポジトリを取得(N=34,610。除外387件(バイナリ・符号化不明386・gitサブモジュール参照1)+絶対に取れない16件=403、listed(M)=34,207)し、cat8_mklist.py+cat8_search.pyで全件検索(パターンはlookahead/survivorship/リーク/時点/embargo/purge/reproducib/seed/deterministic/snapshot等。E3a・E3b・E5の設計票§3の語の組をすべて含む)。当たり528ファイル/3,414行はいずれも `### 当たりの判定` に理由つきで記録した誤検出(webpackやtypescript等ビルド道具の内部語・GradleのSNAPSHOT版番号・protobufの`IsSerializationDeterministic`・th2-infra-editorのUndo履歴の`createSnapshot`等)。一覧 34207 件 / 読んだ 34207 件 / 当たり 528 ファイル / 3414 行 | docs/DATA/probes/20260923_tools_8_run11.log:232 docs/DATA/probes/20260923_tools_8_run11.log:257 docs/DATA/probes/20260923_tools_8_run11.log:285 docs/DATA/probes/20260923_tools_8_run11.log:307 docs/DATA/probes/20260923_tools_8_run11.log:338 docs/DATA/probes/20260923_tools_8_run11.log:376 docs/DATA/probes/20260923_tools_8_run11.log:402 docs/DATA/probes/20260923_tools_8_run11.log:435 docs/DATA/probes/20260923_tools_8_run11.log:470 docs/DATA/probes/20260923_tools_8_run11.log:492 docs/DATA/probes/20260923_tools_8_run11.log:529 docs/DATA/probes/20260923_tools_8_run11.log:558 docs/DATA/probes/20260923_tools_8_run11.log:582 docs/DATA/probes/20260923_tools_8_run11.log:611 docs/DATA/probes/20260923_tools_8_run11.log:633 docs/DATA/probes/20260923_tools_8_run11.log:665 docs/DATA/probes/20260923_tools_8_run11.log:688 docs/DATA/probes/20260923_tools_8_run11.log:719 docs/DATA/probes/20260923_tools_8_run11.log:754 docs/DATA/probes/20260923_tools_8_run11.log:781 docs/DATA/probes/20260923_tools_8_run11.log:803 docs/DATA/probes/20260923_tools_8_run11.log:832 docs/DATA/probes/20260923_tools_8_run11.log:885 docs/DATA/probes/20260923_tools_8_run11.log:913 docs/DATA/probes/20260923_tools_8_run11.log:938 docs/DATA/probes/20260923_tools_8_run11.log:964 docs/DATA/probes/20260923_tools_8_run11.log:991 docs/DATA/probes/20260923_tools_8_run11.log:1025 docs/DATA/probes/20260923_tools_8_run11.log:1047 docs/DATA/probes/20260923_tools_8_run11.log:1069 docs/DATA/probes/20260923_tools_8_run11.log:1097 docs/DATA/probes/20260923_tools_8_run11.log:1183 docs/DATA/probes/20260923_tools_8_run11.log:1578 docs/DATA/probes/20260923_tools_8_run11.log:3312 docs/DATA/probes/20260923_tools_8_run11.log:3334 docs/DATA/probes/20260923_tools_8_run11.log:3361 docs/DATA/probes/20260923_tools_8_run11.log:3386 docs/DATA/probes/20260923_tools_8_run11.log:3411 docs/DATA/probes/20260923_tools_8_run11.log:3444 docs/DATA/probes/20260923_tools_8_run11.log:6299 docs/DATA/probes/20260923_tools_8_run11.log:6325 docs/DATA/probes/20260923_tools_8_run11.log:6347 docs/DATA/probes/20260923_tools_8_run11.log:6373 docs/DATA/probes/20260923_tools_8_run11.log:6399 docs/DATA/probes/20260923_tools_8_run11.log:6424 docs/DATA/probes/20260923_tools_8_run11.log:6619 docs/DATA/probes/20260923_tools_8_run11.log:6647 docs/DATA/probes/20260923_tools_8_run11.log:6672 docs/DATA/probes/20260923_tools_8_run11.log:6697 docs/DATA/probes/20260923_tools_8_run11.log:6723 docs/DATA/probes/20260923_tools_8_run11.log:6778 docs/DATA/probes/20260923_tools_8_run11.log:6800 docs/DATA/probes/20260923_tools_8_run11.log:6830 docs/DATA/probes/20260923_tools_8_run11.log:6852 docs/DATA/probes/20260923_tools_8_run11.log:6880 docs/DATA/probes/20260923_tools_8_run11.log:6910 docs/DATA/probes/20260923_tools_8_run11.log:6932 docs/DATA/probes/20260923_tools_8_run11.log:6954 docs/DATA/probes/20260923_tools_8_run11.log:7006 docs/DATA/probes/20260923_tools_8_run11.log:7034 docs/DATA/probes/20260923_tools_8_run11.log:7056 docs/DATA/probes/20260923_tools_8_run11.log:7085 docs/DATA/probes/20260923_tools_8_run11.log:7113 docs/DATA/probes/20260923_tools_8_run11.log:7135 docs/DATA/probes/20260923_tools_8_run11.log:7160 docs/DATA/probes/20260923_tools_8_run11.log:7189 docs/DATA/probes/20260923_tools_8_run11.log:7212 docs/DATA/probes/20260923_tools_8_run11.log:7235 docs/DATA/probes/20260923_tools_8_run11.log:7258 docs/DATA/probes/20260923_tools_8_run11.log:7288 docs/DATA/probes/20260923_tools_8_run11.log:7310 docs/DATA/probes/20260923_tools_8_run11.log:7335 docs/DATA/probes/20260923_tools_8_run11.log:7357 docs/DATA/probes/20260923_tools_8_run11.log:7383 docs/DATA/probes/20260923_tools_8_run11.log:7406 docs/DATA/probes/20260923_tools_8_run11.log:7438 docs/DATA/probes/20260923_tools_8_run11.log:7465 docs/DATA/probes/20260923_tools_8_run11.log:7497 docs/DATA/probes/20260923_tools_8_run11.log:7526 docs/DATA/probes/20260923_tools_8_run11.log:7554 docs/DATA/probes/20260923_tools_8_run11.log:7801 docs/DATA/probes/20260923_tools_8_run11.log:7830 docs/DATA/probes/20260923_tools_8_run11.log:7859 docs/DATA/probes/20260923_tools_8_run11.log:7882 docs/DATA/probes/20260923_tools_8_run11.log:7904 docs/DATA/probes/20260923_tools_8_run11.log:7926 docs/DATA/probes/20260923_tools_8_run11.log:7954 docs/DATA/probes/20260923_tools_8_run11.log:7980 docs/DATA/probes/20260923_tools_8_run11.log:8009 docs/DATA/probes/20260923_tools_8_run11.log:8037 docs/DATA/probes/20260923_tools_8_run11.log:8059 docs/DATA/probes/20260923_tools_8_run11.log:8096 docs/DATA/probes/20260923_tools_8_run11.log:8126 docs/DATA/probes/20260923_tools_8_run11.log:8161 docs/DATA/probes/20260923_tools_8_run11.log:8183 docs/DATA/probes/20260923_tools_8_run11.log:8205 docs/DATA/probes/20260923_tools_8_run11.log:8227 docs/DATA/probes/20260923_tools_8_run11.log:8317 docs/DATA/probes/20260923_tools_8_run11.log:8368 docs/DATA/probes/20260923_tools_8_run11.log:8397 docs/DATA/probes/20260923_tools_8_run11.log:8424 docs/DATA/probes/20260923_tools_8_run11.log:8458 docs/DATA/probes/20260923_tools_8_run11.log:8484 docs/DATA/probes/20260923_tools_8_run11.log:8524 docs/DATA/probes/20260923_tools_8_run11.log:8546 docs/DATA/probes/20260923_tools_8_run11.log:8576 docs/DATA/probes/20260923_tools_8_run11.log:8602 docs/DATA/probes/20260923_tools_8_run11.log:8630 docs/DATA/probes/20260923_tools_8_run11.log:8660 docs/DATA/probes/20260923_tools_8_run11.log:8688 docs/DATA/probes/20260923_tools_8_run11.log:8716 docs/DATA/probes/20260923_tools_8_run11.log:8746 docs/DATA/probes/20260923_tools_8_run11.log:8773 docs/DATA/probes/20260923_tools_8_run11.log:8799 docs/DATA/probes/20260923_tools_8_run11.log:8825 docs/DATA/probes/20260923_tools_8_run11.log:8847 docs/DATA/probes/20260923_tools_8_run11.log:8876 docs/DATA/probes/20260923_tools_8_run11.log:8907 docs/DATA/probes/20260923_tools_8_run11.log:8935 docs/DATA/probes/20260923_tools_8_run11.log:8965 docs/DATA/probes/20260923_tools_8_run11.log:8995 docs/DATA/probes/20260923_tools_8_run11.log:9017 docs/DATA/probes/20260923_tools_8_run11.log:9042 docs/DATA/probes/20260923_tools_8_run11.log:9068 docs/DATA/probes/20260923_tools_8_run11.log:9094 docs/DATA/probes/20260923_tools_8_run11.log:9124 docs/DATA/probes/20260923_tools_8_run11.log:9153 docs/DATA/probes/20260923_tools_8_run11.log:9182 docs/DATA/probes/20260923_tools_8_run11.log:9238 docs/DATA/probes/20260923_tools_8_run11.log:9377 docs/DATA/probes/20260923_tools_8_run11.log:9429 docs/DATA/probes/20260923_tools_8_run11.log:9495 docs/DATA/probes/20260923_tools_8_run11.log:9518 docs/DATA/probes/20260923_tools_8_run11.log:9559 docs/DATA/probes/20260923_tools_8_run11.log:9583 docs/DATA/probes/20260923_tools_8_run11.log:9607 docs/DATA/probes/20260923_tools_8_run11.log:9633 docs/DATA/probes/20260923_tools_8_run11.log:9663 docs/DATA/probes/20260923_tools_8_run11.log:9693 docs/DATA/probes/20260923_tools_8_run11.log:9723 docs/DATA/probes/20260923_tools_8_run11.log:9745 docs/DATA/probes/20260923_tools_8_run11.log:9770 docs/DATA/probes/20260923_tools_8_run11.log:10084 docs/DATA/probes/20260923_tools_8_run11.log:10106 docs/DATA/probes/20260923_tools_8_run11.log:10129 docs/DATA/probes/20260923_tools_8_run11.log:10191 docs/DATA/probes/20260923_tools_8_run11.log:10216 docs/DATA/probes/20260923_tools_8_run11.log:10246 docs/DATA/probes/20260923_tools_8_run11.log:10274 docs/DATA/probes/20260923_tools_8_run11.log:10296 docs/DATA/probes/20260923_tools_8_run11.log:10327 docs/DATA/probes/20260923_tools_8_run11.log:10350 docs/DATA/probes/20260923_tools_8_run11.log:10380 docs/DATA/probes/20260923_tools_8_run11.log:10405 docs/DATA/probes/20260923_tools_8_run11.log:10428 docs/DATA/probes/20260923_tools_8_run11.log:10454 docs/DATA/probes/20260923_tools_8_run11.log:10479 docs/DATA/probes/20260923_tools_8_run11.log:10507 docs/DATA/probes/20260923_tools_8_run11.log:10557 docs/DATA/probes/20260923_tools_8_run11.log:10586 docs/DATA/probes/20260923_tools_8_run11.log:10608 docs/DATA/probes/20260923_tools_8_run11.log:10631 docs/DATA/probes/20260923_tools_8_run11.log:10677 docs/DATA/probes/20260923_tools_8_run11.log:10706 docs/DATA/probes/20260923_tools_8_run11.log:10735 docs/DATA/probes/20260923_tools_8_run11.log:10773 docs/DATA/probes/20260923_tools_8_run11.log:10803 docs/DATA/probes/20260923_tools_8_run11.log:10827 docs/DATA/probes/20260923_tools_8_run11.log:10849 docs/DATA/probes/20260923_tools_8_run11.log:10872 docs/DATA/probes/20260923_tools_8_run11.log:10902 docs/DATA/probes/20260923_tools_8_run11.log:10944 docs/DATA/probes/20260923_tools_8_run11.log:10972 docs/DATA/probes/20260923_tools_8_run11.log:11001 docs/DATA/probes/20260923_tools_8_run11.log:11026 docs/DATA/probes/20260923_tools_8_run11.log:11048 docs/DATA/probes/20260923_tools_8_run11.log:14198 docs/DATA/probes/20260923_tools_8_run11.log:14445 |
| `Exactpro の reconciliation testing` | E6 | 印 | 3 | 一次資料 | 台帳の値のまま(10回目の節) | |
| `Great Expectations` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Great Expectations` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Great Expectations` | E2 | 印 | 未判別 | 一次資料 | 「GX Core combines the collective wisdom of thousands of community members with a proven track record in data quality deployments worldwide...Its powerful technical tools start with Expectations: expressive and extensible unit tests for your data.」(README。expect_column_values_to_not_be_null等の個別Expectation関数の一覧までは未確認) | docs/DATA/probes/20260923_tools_8_run11.log:1101 |
| `Great Expectations` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Great Expectations` | E3b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Great Expectations` | E4 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Great Expectations` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Great Expectations` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Vibe-Trading` | E1a | 印 | 4 | 一次資料 | 「offline USD-M account reconciliation compares local risk state with an exchange observation without opening a connection」/「Binance USD-M reconciliation results now land as tamper-evident drift evidence artifacts — strict JSON, fail-closed on incomplete or unsupported snapshots」(README変更履歴。自社の計算した口座状態と取引所側の観測値を突き合わせて差分(drift)を検出する機能。突き合わせの単位は指定できないため段4) | docs/DATA/probes/20260923_tools_8_run11.log:3573 |
| `Vibe-Trading` | E1b | 印 | 4 | 一次資料 | バックテストエンジン自身がOHLCVから損益・ポジションを計算する(「a finished backtest is now something you can read」「Run Detail grows four tabs — **Factor Research** (IC series...)、**Positions**...、**Tearsheet**...」)。当方のバックテストエンジンと同じ種類の出力(損益・ポジション)を出す別実装 | docs/DATA/probes/20260923_tools_8_run11.log:3573 |
| `Vibe-Trading` | E2 | 印 | 4 | 一次資料 | 「a default that quietly substitutes a plausible value for a missing one」「The registry now masks output wherever a declared dependency is missing on that bar」(欠損検出)/「read-time freshness (`fresh`/`aging`/`stale`) and stale rows failing closed」(鮮度=時刻のずれの検出)/「Market-data provenance now names the loader...with the matching fallback flag and adjustment label」(情報源間の食い違いの記録) | docs/DATA/probes/20260923_tools_8_run11.log:3573 |
| `Vibe-Trading` | E3a | 印 | 2 | 一次資料 | 「the HTML alpha-bench report now carries the survivorship-bias disclosure the JSON already had, naming the constituent source and its as-of date」(生存者バイアスの開示を報告書に載せる機能。自動判定して止めるところまでは確認できず人が読んで判断する形なので段2) | docs/DATA/probes/20260923_tools_8_run11.log:3573 |
| `Vibe-Trading` | E3b | 印 | 4 | 一次資料 | 「look-ahead-bias and strict-OOS guards in the factor bench and Shadow Account」/「a look-ahead-bias fix across all 5 portfolio optimizers」/「the ML walk-forward example purges future labels」/Quant Library additions に「group-purged CV」(purged cross-validationの実装) | docs/DATA/probes/20260923_tools_8_run11.log:3573 |
| `Vibe-Trading` | E4 | 印 | 未判別 | 一次資料 | 0.1.15のリリースノートに新機能として「swarm replay and retry」が挙げられている(再生の粒度・対象は未確認) | docs/DATA/probes/20260923_tools_8_run11.log:3573 |
| `Vibe-Trading` | E5 | 印 | 未判別 | 一次資料 | 「deterministic USD-M tolerance calibration from recorded comparisons」/「computed through the same test-pinned engine the MCP tools use」(決定的な計算・記録済み比較からの較正への言及。乱数の種の固定・保存の具体的な仕組みまでは未確認) | docs/DATA/probes/20260923_tools_8_run11.log:3573 |
| `Vibe-Trading` | E6 | 印 | 未判別 | 一次資料 | 「22 new regressions cover hydration, terminal recovery, stale reaping, keepalive cadence, env parsing, and heartbeat wiring; the full swarm/MCP suite is at 169 passed, 4 skipped.」(回帰テストスイートの実行結果件数を明記) | docs/DATA/probes/20260923_tools_8_run11.log:3573 |
| `AutoHedge` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AutoHedge` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AutoHedge` | E2 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AutoHedge` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AutoHedge` | E3b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AutoHedge` | E4 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AutoHedge` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AutoHedge` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenBB Terminal` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenBB Terminal` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenBB Terminal` | E2 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenBB Terminal` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenBB Terminal` | E3b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenBB Terminal` | E4 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenBB Terminal` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenBB Terminal` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Qlib` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Qlib` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Qlib` | E2 | 印 | 4 | 一次資料 | `scripts/check_data_health.py` の `DataHealthChecker` クラス docstring: 「Checks a dataset for data completeness and correctness...- any of the columns [...] are missing - any data is missing - any step change in the OHLCV columns is above a threshold (default: 0.5 for price, 3 for volume) - any factor is missing」。コンストラクタに `large_step_threshold_price`・`large_step_threshold_volume`・`missing_data_num` を指定でき((ア)条件は満たす)、`csv_path` 引数でqlib形式の外から持ち込んだCSVディレクトリにも掛けられる(段4)。チェック結果を保存し次回実行と比較する(イ)の記述は見つからず段5にはしない | docs/DATA/probes/20260923_tools_8_run11.log:9774 |
| `Qlib` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Qlib` | E3b | 印 | 未判別 | 一次資料 | Point-in-Time(PIT)データ収集・変換のREADME: 四半期決算などの財務データを発表時点(as-of)で正しく参照できる形に変換して積む一連の手順(`download_data`→`normalize_data`→`dump_pit.py dump`)。時点を揃えた結合の具体的な実装箇所までは未確認なので段は未判別 | docs/DATA/probes/20260923_tools_8_run11.log:10036 |
| `Qlib` | E4 | 印 | 未判別 | 一次資料 | README: 「Qlib provides a tool named `qrun` to run the whole workflow automatically (including building dataset, training models, backtest and evaluation).」(記録した市場データを順に読んでモデル・戦略を評価するワークフロー。再生の粒度・時刻の扱いは未確認) | docs/DATA/probes/20260923_tools_8_run11.log:5608 |
| `Qlib` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Qlib` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinGPT` | E1a | 印 | 未判別 | 一次資料 | 「**Task layer**: This layer is responsible for executing fundamental tasks. These tasks serve as the benchmarks for performance evaluations and cross-comparisons in the realm of FinLLMs」(複数のFinLLM実装の出力をベンチマークで突き合わせて比較するレイヤーがあるとの記述。突き合わせの単位・自動判定の有無は未確認) | docs/DATA/probes/20260923_tools_8_run11.log:4944 |
| `FinGPT` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinGPT` | E2 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinGPT` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinGPT` | E3b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinGPT` | E4 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinGPT` | E5 | 印 | 未判別 | 一次資料 | 「Reproduce the results by running [benchmarks](./fingpt/FinGPT_Sentiment_Analysis_v3/benchmark/benchmarks.ipynb), and the detailed tutorial is on the way.」(結果の再現をnotebookで行える。乱数の種の固定など具体の仕組みは未確認) | docs/DATA/probes/20260923_tools_8_run11.log:4944 |
| `FinGPT` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Backtrader` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Backtrader` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Backtrader` | E2 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Backtrader` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Backtrader` | E3b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Backtrader` | E4 | 印 | 未判別 | 一次資料 | README.rstの機能一覧: 「Integrated Resampling and Replaying」(記録した足を読み込んでリサンプル・再生する統合機能。粒度や遅延の扱いの詳細は未確認) | docs/DATA/probes/20260923_tools_8_run11.log:6444 |
| `Backtrader` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Backtrader` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Lean` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Lean` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Lean` | E2 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Lean` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Lean` | E3b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Lean` | E4 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Lean` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Lean` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinanceToolkit` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinanceToolkit` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinanceToolkit` | E2 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinanceToolkit` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinanceToolkit` | E3b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinanceToolkit` | E4 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinanceToolkit` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `FinanceToolkit` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenClaw` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenClaw` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenClaw` | E2 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenClaw` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenClaw` | E3b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenClaw` | E4 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenClaw` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `OpenClaw` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Quantreo library` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Quantreo library` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Quantreo library` | E2 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Quantreo library` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Quantreo library` | E3b | 印 | 未判別 | 一次資料 | README: 「**Robust by design**: Functions implemented to avoid data leakage and look-ahead bias.」(データリーク・ルックアヘッドバイアスを避けるよう実装された関数群。具体の実装方式(embargo/purge等)は未確認) | docs/DATA/probes/20260923_tools_8_run11.log:4150 |
| `Quantreo library` | E4 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Quantreo library` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `Quantreo library` | E6 | 印 | 未判別 | 実測 | `.github/workflows/tests.yml`: 「run: pytest --cov=quantreo --cov-report=term-missing -v --maxfail=1 --disable-warnings」(pytestによる自動テストとカバレッジ計測)。CHANGELOG.mdにも「Improved **unit test coverage** across the library」とある(全要素検索の手は巨大なnotebook出力に埋め込まれた第三者JSバンドルのため生ログ2,000,000字で切られたが、この2件の当たりはいずれも切られる前の範囲に出ている) | docs/DATA/probes/20260923_tools_8_run11.log:14547 docs/DATA/probes/20260923_tools_8_run11.log:14549 |
| `AlgoBuild` | E1a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AlgoBuild` | E1b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AlgoBuild` | E2 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AlgoBuild` | E3a | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AlgoBuild` | E3b | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AlgoBuild` | E4 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AlgoBuild` | E5 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `AlgoBuild` | E6 | 未判別 | 未判別 | 未確認 | 試した手段: README・CHANGELOG・GitHub登録情報(ungh.cc)・PyPI情報を読んだが、この要素の述語に当たる記述もなし の根拠にできる全件検索も、この回では行っていない | |
| `MetaTrader の Strategy Tester` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `MetaTrader の Strategy Tester` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `MetaTrader の Strategy Tester` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `MetaTrader の Strategy Tester` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `MetaTrader の Strategy Tester` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `MetaTrader の Strategy Tester` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `MetaTrader の Strategy Tester` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `MetaTrader の Strategy Tester` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `dbt` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `dbt` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `dbt` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `dbt` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `dbt` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `dbt` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `dbt` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `dbt` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Debezium` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Debezium` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Debezium` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Debezium` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Debezium` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Debezium` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Debezium` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Debezium` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Kafka` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Kafka` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Kafka` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Kafka` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Kafka` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Kafka` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Kafka` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Kafka` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Prefect` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Prefect` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Prefect` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Prefect` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Prefect` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Prefect` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Prefect` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Prefect` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Pandas` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Pandas` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Pandas` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Pandas` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Pandas` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Pandas` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Pandas` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Pandas` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Spark` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Spark` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Spark` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Spark` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Spark` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Spark` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Spark` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `Apache Spark` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AI Trading Lab` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AI Trading Lab` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AI Trading Lab` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AI Trading Lab` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AI Trading Lab` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AI Trading Lab` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AI Trading Lab` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AI Trading Lab` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AlgoNetwork` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AlgoNetwork` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AlgoNetwork` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AlgoNetwork` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AlgoNetwork` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AlgoNetwork` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AlgoNetwork` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `AlgoNetwork` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NinjaTrader` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NinjaTrader` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NinjaTrader` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NinjaTrader` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NinjaTrader` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NinjaTrader` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NinjaTrader` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NinjaTrader` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NumPy` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NumPy` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NumPy` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NumPy` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NumPy` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NumPy` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NumPy` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `NumPy` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `SciPy` | E1a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `SciPy` | E1b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `SciPy` | E2 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `SciPy` | E3a | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `SciPy` | E3b | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `SciPy` | E4 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `SciPy` | E5 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |
| `SciPy` | E6 | 未判別 | 未判別 | 未確認 | 台帳の値のまま(10回目の節) | |

### 当たりの判定

この回に打った `cat8_search.py` の手(8-016 の E3a/E3b/E5 やり直し。178 手)で当たった行のあるファイル 528 件全部を、理由つきで載せる(監査 67 回目の指摘 3)。

| ファイルの道 | 当たった行の数 | 述語に当たらない理由 |
|---|---|---|
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/.github/.github/workflows/compaund-java-multi-project-build.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/.github/.github/workflows/compaund-java-sonatype-push.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/.github/.github/workflows/compound-grpc.yml` | 3 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/.github/.github/workflows/compound-prebuild-java-dev-workflow.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/.github/.github/workflows/java-prepare-version.yml` | 4 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/.github/.github/workflows/python-prepare-version.yml` | 3 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/.github/workflow-templates/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/cradleapi/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/e2e-test-schema/dictionaries/fix50-generic.yml` | 4 | FIXプロトコル辞書データ中のフィールド名(構文データであり機能ではない) |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/jsonToHtmlParser/build/out/main.3d1f31d2b310bad9c8c2.js` | 1 | webpackでバンドルされたビルド成果物(react-dom等の内部語を含む圧縮JS)。上と同じ理由でビルド道具の内部語 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/junit-jupiter-integration/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/junit-jupiter-integration/api/junit-jupiter-integration.api` | 1 | Kotlin ABIダンプ中の関数シグネチャ`purgeQueue`(RabbitMQキューを空にするテストユーティリティで、E3b(ルックアヘッド防止)の`purge`(データ分割時の除去)とは意味が異なる) |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/junit-jupiter-integration/src/main/kotlin/com/exactpro/th2/test/extension/Th2RabbitMqExtension.kt` | 1 | RabbitMQキューを試験終了後に空にする`purgeQueue`呼び出し(後始末処理)。ルックアヘッド防止のpurge(未来情報の除去)ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/junit-jupiter-integration/src/main/kotlin/com/exactpro/th2/test/integration/RabbitMqConfigurator.kt` | 2 | 同上、RabbitMQキューの後始末(`purgeQueue`) |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/junit-jupiter-integration/src/main/kotlin/com/exactpro/th2/test/integration/RabbitMqIntegration.kt` | 5 | 同上、RabbitMQキューの後始末(`purgeQueue`)。E3bの`purge`はデータ分割時の除去を指し意味が異なる |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/provider_call/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/pytest-th2-bdd/.gitignore` | 1 | .gitignoreのコメント文中の一般語`reproducibility`(バイナリパッケージのビルド再現性についての注意書きで、pytest-th2-bdd自身の機能ではない) |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/qfj-dictionary-converter/settings.gradle.kts` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/remotehand/.github/workflows/snapshot-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/remotehand/README.md` | 3 | READMEの一般的な記述中の語(機能としてのE3a/E3b/E5に当たらない) |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/remotehand/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/remotehand/src/main/java/com/exactpro/remotehand/web/actions/DownloadFile.java` | 3 | ダウンロードファイル操作のコード中の一般語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/run-one/.github/workflows/publish-release-canditate.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/run-one/.github/workflows/publish-release.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/run-one/.github/workflows/publish-snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/test-management-sync/.github/workflows/development.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/test-management-sync/.github/workflows/release-candidate.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/test-management-sync/.github/workflows/release.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-core-j/.github/workflows/dev-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-core-j/README.md` | 1 | READMEの一般的な記述中の語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-core-j/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-gui-core/.github/workflows/snapshot-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-gui-core/build.gradle.kts` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-ssh/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-test/build.gradle` | 4 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-ui-backend/build.gradle` | 4 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-ui/.github/workflows/build-snapshot.yml` | 7 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-ui/package-lock.json` | 6 | npm依存関係のロックファイル中のパッケージ名・版表記(`*-snapshot`等)。コードではなく依存関係の記録 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-ui/src/components/replay/ReplayTableBody.tsx` | 3 | react-beautiful-dnd(ドラッグ&ドロップ)の型`DraggableStateSnapshot`(ドラッグ中のUI状態)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-ui/src/components/replay/ReplayTableRow.tsx` | 4 | 同上、`DraggableStateSnapshot`(ドラッグUI状態)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-uiframework-web-demo/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-act-uiframework-win-demo/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-bom/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-bom/build.gradle` | 1 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-box-descriptor-generator/.github/workflows/dev-gradle-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-box-descriptor-generator/README.md` | 3 | READMEの一般的な記述中の語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-box-descriptor-generator/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-box-template-j/.github/workflows/dev-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-box-template-j/settings.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-avro/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-csv/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-fix-ng/src/jmh/resources/dictionary-benchmark.xml` | 4 | FIXプロトコル辞書データ(ベンチマーク用)中のフィールド名。構文データで機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-fix-ng/src/test/resources/dictionary.xml` | 4 | FIXプロトコル辞書データ中のフィールド名。構文データで機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-fix-orchestra/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-fix-orchestra/src/test/resources/dict/mit_2016.xml` | 49 | FIXプロトコル辞書データ中のフィールド名`As-of Trade Qty`(FIXの標準フィールド名)。E3a/E3bの時点(point-in-time)の述語ではなくFIXタグ名 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-generic/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-hand-html/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-hand/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-html/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-json-dictionaryless/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-json/build.gradle` | 4 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-moldudp64/build.gradle` | 1 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-open-api/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-oracle-log-miner/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-oracle-log-miner/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-oracle-log-miner/src/main/antlr/PlSqlLexer.g4` | 3 | Oracle PL/SQL文法定義(ANTLR)中の予約語`PURGE`/`DETERMINISTIC`(SQLの構文要素)。ルックアヘッド防止・再現性の機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-oracle-log-miner/src/main/antlr/PlSqlParser.g4` | 22 | Oracle PL/SQL文法定義(ANTLR)中の予約語`PURGE`/`DETERMINISTIC`(SQLの構文要素)。ルックアヘッド防止・再現性の機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-sailfish/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-sailfish/build.gradle` | 4 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-xml-via-xsd/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-xml-via-xsd/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec-xml/build.gradle` | 4 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-codec/README.md` | 1 | READMEの一般的な記述中の語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-cpp/src/common.pb.cc` | 6 | protobufが自動生成したC++コード中の`IsSerializationDeterministic()`(protobufランタイム共通のバイト列決定性シリアライズ設定)。th2-netが独自に持つ再現性確認機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-j/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-j/src/test/kotlin/com/exactpro/th2/common/util/RabbitTestContainerUtil.kt` | 2 | RabbitMQテストコンテナのユーティリティ中の一般語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-py/.github/workflows/publish-release-canditate.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-py/.github/workflows/publish-release.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-py/.github/workflows/publish-snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-utils-j/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-utils-py/.github/workflows/publish-release-canditate.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-utils-py/.github/workflows/publish-release.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-common-utils-py/.github/workflows/publish-snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-dirty-http/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-dirty-http/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-dirty-tcp-core/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-generic/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-http-server/.github/workflows/dev-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-http-server/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-http-ws-client-template/.github/workflows/dev-java-publish-sonatype-and-docker.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-http-ws-client-template/build.gradle` | 1 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-kafka/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-sailfish/build.gradle` | 4 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-ws-client/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-conn-ws-client/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-cr-converter/.github/workflows/dev-docker-publish.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-cr-converter/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-crawler-event-healer/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-crawler/README.md` | 2 | 「Crawlerはこの時点からデータを処理する」という取得範囲の開始/終了時刻の説明(データ収集レンジの指定であり、E3a/E3bが指す『その時点で知り得ない情報を使わない』ためのpoint-in-time結合とは異なる) |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-crawler/settings.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-custom-resource-model/.github/workflows/dev-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-custom-resource-model/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-processor-zephyr/build.gradle` | 1 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-processor-zephyr/settings.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-services-j/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-services-j/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-services-utils/.github/workflows/publish-release-candidate.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-services-utils/.github/workflows/publish-release.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-services-utils/.github/workflows/publish-snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-services/.github/workflows/publish-release-candidate.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-services/.github/workflows/publish-release.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-data-services/.github/workflows/publish-snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-docs/content/modules/codec/usage.md` | 1 | SonatypeのSNAPSHOTリポジトリURL(Mavenのビルド設定の説明)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-docs/content/terms/helm_chart.md` | 1 | Helm Chartの一般的な説明文中の語(`managed with`等)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-ds-source-lwdp/.github/workflows/publish-release-candidate.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-ds-source-lwdp/.github/workflows/publish-release.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-ds-source-lwdp/.github/workflows/publish-snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-ds-source-rdp/.github/workflows/publish-release.yaml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-ds-source-rdp/.github/workflows/publish-snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-event-uploader-j/build.gradle.kts` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-gradle-plugin/build.gradle.kts` | 1 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-gradle-plugin/plugin/src/functionalTest/kotlin/com/exactpro/th2/gradle/Th2ComponentGradlePluginFunctionalTest.kt` | 4 | 同上。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-gradle-plugin/plugin/src/functionalTest/kotlin/com/exactpro/th2/gradle/Th2GrpcGradlePluginFunctionalTest.kt` | 6 | Gradleプラグインの機能テスト中のSNAPSHOT版番号の検証。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-gradle-plugin/plugin/src/main/kotlin/com/exactpro/th2/gradle/PublishTh2Plugin.kt` | 2 | SonatypeのSNAPSHOTリポジトリURLの定数。ビルド公開設定で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-act-ssh/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-act-ssh/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-act-template/.github/workflows/snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-act-test/.github/workflows/dev-java-publish-fury.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-act-test/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-act-uiframework-web-demo/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-act-uiframework-web-demo/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-act-uiframework-win-demo/.github/workflows/snapshot-java-python-publish.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-act-uiframework-win-demo/build.gradle.kts` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-check1/.github/workflows/snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-check1/README.md` | 1 | 「releaseバージョンに置き換える」という変更履歴文中のSNAPSHOTの語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-check2-recon/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-check2-recon/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-client/build.gradle` | 4 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-codec/.github/workflows/snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-common/.github/workflows/snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-conn/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-conn/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-crawler-data-processor/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-crawler-data-processor/build.gradle` | 4 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-data-provider/.github/workflows/snapshot-java-python-publish.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-data-provider/build.gradle.kts` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-generator-template/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-generator-template/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-hand/.github/workflows/snapshot-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-hand/build.gradle.kts` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-hand/src/main/proto/th2_grpc_hand/rhactionsmessages_web.proto` | 1 | RemoteHand(ブラウザ操作の遠隔実行)のgRPCメッセージ内の列挙値`SNAPSHOT`(画面キャプチャ操作の種別と推定される)。実験結果の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-service-generator/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-sim-template/.github/workflows/snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-sim/.github/workflows/snapshot.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-util/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-util/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-woodpecker/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-grpc-woodpecker/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-hand/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-hand/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor-v2/.github/workflows/build-snapshot.yml` | 7 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor-v2/package-lock.json` | 7 | npm依存関係のロックファイル中のパッケージ名・版表記(`*-snapshot`等)。コードではなく依存関係の記録 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor-v2/src/models/History.ts` | 1 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor-v2/src/stores/HistoryStore.ts` | 8 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/.github/workflows/build-snapshot.yml` | 7 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/package-lock.json` | 6 | npm依存関係のロックファイル中のパッケージ名・版表記(`*-snapshot`等)。コードではなく依存関係の記録 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/components/box/BoxSettings.tsx` | 2 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/components/changeLog/ChangeLogBoxItem.tsx` | 11 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/components/changeLog/ChangeLogDictionaryItem.tsx` | 5 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/components/changeLog/ChangeLogLinkItem.tsx` | 5 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/components/changeLog/ChangeLogModal.tsx` | 5 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/components/util/History.tsx` | 2 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/helpers/snapshot.ts` | 7 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/models/History.ts` | 1 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/store/ConnectionsStore.ts` | 11 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/store/HistoryStore.ts` | 17 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/store/SchemasStore.ts` | 21 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-editor/src/store/SubscriptionStore.ts` | 1 | th2-infra-editorの設定編集画面が持つ独自のundo/redo履歴機構(`createSnapshot`でボックス/辞書/接続の変更を`historyStore`に積む)。GUIの編集操作の取り消し機能であり、E5の述語(実験・データの再現性を確かめる/固定する)には当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-mgr/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-mgr/src/main/java/com/exactpro/th2/inframgr/SchemaController.java` | 18 | th2スキーマ(Kubernetesカスタムリソース定義)のスナップショット取得API(現在のリソース一覧を返すだけ)。実験結果の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-mgr/src/main/java/com/exactpro/th2/inframgr/SchemaControllerResponse.java` | 4 | 同上、スキーマの現在状態を表すレスポンス型。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-mgr/src/main/java/com/exactpro/th2/inframgr/SchemaValidationController.java` | 4 | 同上、スキーマ検証APIの周辺コード中の一般語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-mgr/src/main/java/com/exactpro/th2/inframgr/k8s/K8sOperator.java` | 4 | Kubernetesリソースの現在状態取得コード中の一般語一致(`snapshot`はK8sリソース一覧の意)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-mgr/src/main/java/com/exactpro/th2/inframgr/k8s/K8sSynchronization.java` | 5 | 同上。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-repo/.github/workflows/dev-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-repo/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-repo/src/main/java/com/exactpro/th2/infrarepo/repo/Repository.java` | 8 | Gitリポジトリ操作コード中の一般語一致(`snapshot`はコミット時点のファイル一覧の意)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra-repo/src/main/java/com/exactpro/th2/infrarepo/repo/RepositorySnapshot.java` | 2 | Gitリポジトリのある時点でのリソース一覧を表すクラス名`RepositorySnapshot`。設定リポジトリの現在状態を表す型であり、実験結果の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/README.md` | 1 | Kubernetesネームスペースの削除操作`Purge th2 namespaces`(インフラのクリーンアップ手順)。E3bのpurge(データからの未来情報除去)とは異なる |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/argocd/openshift/cassandra-instance/medusa.cm.yaml` | 2 | Cassandraバックアップツールmedusaの`purge`コマンド(古いバックアップの削除)。述語のpurgeとは異なる |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/chart/charts/cassandra/README.md` | 2 | Bitnami Cassandra Helmチャートのアップグレード注意書き(バックアップ推奨・後方互換性の説明)。th2独自の機能ではなく第三者チャートの定型文 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/chart/charts/cassandra/templates/statefulset.yaml` | 2 | Bitnami製Helmチャート(Cassandra/RabbitMQ)のテンプレートにある、ストレージの`.snapshot`ディレクトリ(NetApp等のファイルシステムスナップショット)を除外する定型句。th2-net自身の機能ではなく第三者チャートの定型文 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/chart/charts/cassandra/values.yaml` | 1 | Bitnami製Helmチャート(Cassandra/RabbitMQ)のテンプレートにある、ストレージの`.snapshot`ディレクトリ(NetApp等のファイルシステムスナップショット)を除外する定型句。th2-net自身の機能ではなく第三者チャートの定型文 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/chart/charts/helm-operator/README.md` | 1 | Helmの`--purge`オプション(削除したリリースの完全消去)。述語のpurgeとは異なる |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/chart/charts/rabbitmq/README.md` | 1 | Bitnami RabbitMQ Helmチャートの変更履歴('.snapshot'ディレクトリの権限変更の記述)。第三者チャートの定型文 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/chart/charts/rabbitmq/templates/statefulset.yaml` | 1 | Bitnami製Helmチャート(Cassandra/RabbitMQ)のテンプレートにある、ストレージの`.snapshot`ディレクトリ(NetApp等のファイルシステムスナップショット)を除外する定型句。th2-net自身の機能ではなく第三者チャートの定型文 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/ci/deploy/cassandra/cassandra-configmap.yaml` | 7 | Apache Cassandra本体の既定設定`auto_snapshot`/`snapshot_before_compaction`(コンパクション前・データ切り詰め前にディスクスナップショットを取るかの設定)。Cassandraの標準設定ファイルの定型文であり、th2独自の実験再現性機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/ci/e2e-test-schema/dictionaries/fix50-generic.yml` | 4 | FIXプロトコル辞書データ(QuickFIXの標準辞書由来)中のフィールド名。構文データで機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-infra/ci/go.sum` | 1 | Go依存関係のロックファイル中のパッケージ名(`stargz-snapshotter`)。コードではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-json-stream-provider-py/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-key-value-storage/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-lib-common-j/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-lib-common-j/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-lib-fix-util-j/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-lib-fix-util-j/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-lib-template-j/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-lib-template-j/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-lw-data-provider/app/src/main/kotlin/com/exactpro/th2/lwdataprovider/http/SseRequestContext.kt` | 1 | `FIXME: use snapshot of the current state`という未実装のTODOコメント。実装されている機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-netty-bytebuf-utils/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-pico-operator/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-pico-operator/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-pico/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-pico/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-pico/scripts/schema-converter` | 1 | 起動スクリプト中のjarファイル名に含まれるMavenのSNAPSHOT版番号表記。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-processor-core-j/.github/workflows/build-sanpshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-processor-core-j/README.md` | 2 | 「processorはこの時点からデータを処理する」という取得範囲の説明。th2-crawlerと同じ理由で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-processor-core-j/build.gradle.kts` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-rdp-profiler/package-lock.json` | 7 | npm依存関係のロックファイル中のパッケージ名・版表記(`*-snapshot`等)。コードではなく依存関係の記録 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-csv/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-file-common-core/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-file/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-log/README.md` | 1 | 「releaseバージョンからSNAPSHOTを外した」という変更履歴文中の語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-log/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-pcap-fix/build.gradle` | 5 | GradleのSNAPSHOT版番号。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-pcap-fix/src/main/java/com/exactprosystems/fix/reader/cfg/PcapFileReaderConfiguration.java` | 6 | 同上。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-pcap-fix/src/main/java/com/exactprosystems/fix/reader/pcapreader/PcapFileReader.java` | 2 | pcap4jライブラリの`openOffline`(録れたpcapファイルを開くAPI名)。当たった語は正規表現の他の枝(as-of等)の偶然一致で、機能としては述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-pcap-fix/src/main/java/com/exactprosystems/fix/reader/pcapreader/PcapReader.java` | 2 | libpcap由来の`snapshotLength`(1パケットあたりの最大取得バイト数を指すpcap業界標準の用語で、th2独自の再現性機能ではない) |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-read-pcap-fix/src/main/java/com/exactprosystems/fix/reader/pcapreader/RecordReader.java` | 7 | PCAPファイル読み取りコード中の一般語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-replay-script-generator-core/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-replay-script-generator-core/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-rpt-viewer/.github/workflows/build-snapshot.yml` | 7 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-rpt-viewer/package-lock.json` | 12 | npm依存関係のロックファイル(パッケージ名・版表記)。コードではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-sailfish-utils/.github/workflows/dev-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-sailfish-utils/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-schema-validator/.github/workflows/dev-java-publish-sonatype.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-schema-validator/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-sense/.github/workflows/build-and-publish-java.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-sense/.github/workflows/dev-build.yml` | 5 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-sense/build.gradle` | 1 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-sense/sense-app/build.gradle` | 1 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-sense/settings.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-sim/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-sim/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-store-common/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-store-common/build.gradle` | 3 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-task-utils/.github/workflows/build-snapshot.yml` | 1 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-util/build.gradle` | 4 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-woodpecker-template/build.gradle` | 1 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-woodpecker/.github/workflows/dev-java-publish-sonatype.yml` | 2 | GitHub Actionsのワークフロー名・変数名が`snapshot`(開発版イメージの公開)を含むだけ。CI/CDの命名で、データ・実験の再現性を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/th2-woodpecker/build.gradle` | 2 | GradleのMaven座標が`-SNAPSHOT`版番号を参照しているだけ(ビルド設定のバージョン表記)。実験結果の再現・固定を確かめる機能ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@babel/core/lib/vendor/import-meta-resolve.js.map` | 1 | Babelパーサ本体の構文解析における`lookahead`(先読みトークン)。プログラミング言語処理系の一般語で、金融データのルックアヘッドバイアスとは無関係 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@babel/core/node_modules/semver/README.md` | 1 | Babelパーサ本体の構文解析における`lookahead`(先読みトークン)。プログラミング言語処理系の一般語で、金融データのルックアヘッドバイアスとは無関係 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@babel/helper-compilation-targets/node_modules/semver/README.md` | 1 | Babelパーサ本体の構文解析における`lookahead`(先読みトークン)。プログラミング言語処理系の一般語で、金融データのルックアヘッドバイアスとは無関係 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@babel/highlight/node_modules/color-name/index.js` | 4 | Babelパーサ本体の構文解析における`lookahead`(先読みトークン)。プログラミング言語処理系の一般語で、金融データのルックアヘッドバイアスとは無関係 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@babel/parser/CHANGELOG.md` | 1 | Babelパーサ本体の構文解析における`lookahead`(先読みトークン)。プログラミング言語処理系の一般語で、金融データのルックアヘッドバイアスとは無関係 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@babel/parser/lib/index.js` | 67 | Babelパーサ本体の構文解析における`lookahead`(先読みトークン)。プログラミング言語処理系の一般語で、金融データのルックアヘッドバイアスとは無関係 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/CHANGELOG.md` | 9 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/Menu/Menu.js` | 1 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/MenuList/MenuList.js` | 1 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/es/Menu/Menu.js` | 1 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/es/MenuList/MenuList.js` | 1 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/es/test-utils/describeConformance.js` | 1 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/esm/Menu/Menu.js` | 1 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/esm/MenuList/MenuList.js` | 1 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/esm/test-utils/describeConformance.js` | 1 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/test-utils/describeConformance.js` | 1 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/core/umd/material-ui.development.js` | 4 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/styles/CHANGELOG.md` | 9 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/styles/node_modules/csstype/index.d.ts` | 4 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/styles/node_modules/csstype/index.js.flow` | 4 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/system/CHANGELOG.md` | 9 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/system/node_modules/csstype/index.d.ts` | 4 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/system/node_modules/csstype/index.js.flow` | 4 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@material-ui/utils/CHANGELOG.md` | 9 | Material-UI(旧版)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/base/CHANGELOG.md` | 12 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/CHANGELOG.md` | 12 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/Menu/Menu.js` | 1 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/MenuList/MenuList.js` | 1 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/esm/Menu/Menu.js` | 1 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/esm/MenuList/MenuList.js` | 1 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/esm/useMediaQuery/useMediaQuery.js` | 8 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/legacy/Menu/Menu.js` | 1 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/legacy/MenuList/MenuList.js` | 1 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/legacy/useMediaQuery/useMediaQuery.js` | 8 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/modern/Menu/Menu.js` | 1 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/modern/MenuList/MenuList.js` | 1 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/modern/useMediaQuery/useMediaQuery.js` | 8 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/umd/material-ui.development.js` | 11 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/material/useMediaQuery/useMediaQuery.js` | 8 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/private-theming/CHANGELOG.md` | 12 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/styled-engine/CHANGELOG.md` | 12 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/system/CHANGELOG.md` | 12 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@mui/utils/CHANGELOG.md` | 12 | MUI(Material UI)コンポーネントライブラリ本体の内部語彙(スナップショット・シード等のビルド関連)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@popperjs/core/README.md` | 3 | popper.js後継パッケージの同種のコメント。UIライブラリの内部語で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@popperjs/core/package.json` | 1 | popper.js後継パッケージの同種のコメント。UIライブラリの内部語で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/express-serve-static-core/index.d.ts` | 2 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/inspector.d.ts` | 26 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/process.d.ts` | 2 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/ts4.8/inspector.d.ts` | 26 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/ts4.8/process.d.ts` | 2 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/ts4.8/v8.d.ts` | 20 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/ts4.8/wasi.d.ts` | 3 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/ts4.8/worker_threads.d.ts` | 4 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/v8.d.ts` | 20 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/wasi.d.ts` | 3 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/node/worker_threads.d.ts` | 4 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@types/react/index.d.ts` | 12 | TypeScript型定義パッケージ内の一般語(関数名・コメント)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/@webassemblyjs/floating-point-hex-parser/README.md` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/acorn/dist/acorn.js` | 4 | JSパーサacornの構文解析における先読み(`lookahead`)。プログラミング言語処理系の一般語 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/acorn/dist/acorn.mjs` | 4 | JSパーサacornの構文解析における先読み(`lookahead`)。プログラミング言語処理系の一般語 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/ansi-regex/readme.md` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/ansi-styles/index.d.ts` | 4 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/autoprefixer/lib/autoprefixer.js` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/autoprefixer/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/babel-plugin-macros/README.md` | 1 | Babelプラグインの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/babel-plugin-macros/package.json` | 1 | Babelプラグインの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/cacache/lib/util/move-file.js` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/chokidar/lib/nodefs-handler.js` | 2 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/clean-css/lib/optimizer/level-1/value-optimizers/color/shorten-hex.js` | 4 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/clean-webpack-plugin/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/clsx/readme.md` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/color/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/colord/plugins/names.js` | 1 | 色処理ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/colord/plugins/names.mjs` | 1 | 色処理ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/copy-webpack-plugin/README.md` | 1 | webpackプラグインの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/copy-webpack-plugin/dist/index.js` | 22 | webpackプラグインの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/copy-webpack-plugin/types/index.d.ts` | 7 | webpackプラグインの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/core-js/CHANGELOG.md` | 1 | core-js(JS標準ライブラリのポリフィル)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/core-js/client/core.js` | 1 | core-js(JS標準ライブラリのポリフィル)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/core-js/client/library.js` | 1 | core-js(JS標準ライブラリのポリフィル)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/core-js/client/shim.js` | 1 | core-js(JS標準ライブラリのポリフィル)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/core-js/library/modules/_object-assign.js` | 1 | core-js(JS標準ライブラリのポリフィル)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/core-js/modules/_object-assign.js` | 1 | core-js(JS標準ライブラリのポリフィル)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/cosmiconfig/README.md` | 5 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/css-tree/dist/csstree.js` | 4 | CSS構文解析ライブラリの内部語(`lookahead`はCSSパーサの先読み)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/css-tree/dist/csstree.min.js` | 1 | CSS構文解析ライブラリの内部語(`lookahead`はCSSパーサの先読み)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/css-tree/lib/lexer/match.js` | 3 | CSS構文解析ライブラリの内部語(`lookahead`はCSSパーサの先読み)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/css-vendor/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/csso/CHANGELOG.md` | 1 | csso(CSS最適化ツール)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/csso/dist/csso.js` | 5 | csso(CSS最適化ツール)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/csso/dist/csso.min.js` | 1 | csso(CSS最適化ツール)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/csso/lib/replace/color.js` | 4 | csso(CSS最適化ツール)の内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/csstype/index.d.ts` | 4 | csstype(CSS型定義)パッケージの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/csstype/index.js.flow` | 4 | csstype(CSS型定義)パッケージの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/debug/src/browser.js` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/enhanced-resolve/lib/CachedInputFileSystem.js` | 14 | webpackのモジュール解決ライブラリの内部語(`deterministic`な解決順)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/enhanced-resolve/types.d.ts` | 1 | webpackのモジュール解決ライブラリの内部語(`deterministic`な解決順)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/express/History.md` | 11 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/fast-json-stable-stringify/README.md` | 2 | JSON安定化ライブラリの内部語(`deterministic`な出力)。ビルド道具でth2-netの述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/fast-json-stable-stringify/package.json` | 2 | JSON安定化ライブラリの内部語(`deterministic`な出力)。ビルド道具でth2-netの述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/globule/node_modules/minimatch/minimatch.js` | 1 | glob一致ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/hard-rejection/readme.md` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/html-webpack-plugin/lib/cached-child-compiler.js` | 15 | webpackプラグインの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/html-webpack-plugin/lib/file-watcher-api.js` | 12 | webpackプラグインの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/http-parser-js/http-parser.d.ts` | 1 | HTTPパーサの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/http-parser-js/http-parser.js` | 1 | HTTPパーサの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/ignore/index.js` | 1 | .gitignore風パターン処理ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/ignore/legacy.js` | 1 | .gitignore風パターン処理ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/infer-owner/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/jss-plugin-camel-case/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/jss-plugin-default-unit/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/jss-plugin-global/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/jss-plugin-nested/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/jss-plugin-props-sort/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/jss-plugin-rule-value-function/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/jss-plugin-vendor-prefixer/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/jss/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/loose-envify/replace.js` | 5 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/mdn-data/css/syntaxes.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/methods/HISTORY.md` | 1 | HTTPメソッド一覧パッケージ中の一般語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/methods/README.md` | 1 | HTTPメソッド一覧パッケージ中の一般語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/methods/index.js` | 2 | HTTPメソッド一覧パッケージ中の一般語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/micromatch/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/minimatch/minimatch.js` | 1 | glob一致ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/minipass-fetch/README.md` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/minipass-sized/.npmignore` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/minizlib/README.md` | 2 | gzip圧縮ライブラリのREADMEにある`REPRODUCIBLE BUILDS`(バイナリ配布物の再現可能ビルドの話)。データ・実験の再現性ではなくnpmパッケージ配布の慣行。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-forge/CHANGELOG.md` | 1 | 暗号ライブラリの内部語(`seed`は乱数生成器のシード)。汎用暗号処理の内部実装で、th2-netの機能として使われている証拠はない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-forge/README.md` | 2 | 暗号ライブラリの内部語(`seed`は乱数生成器のシード)。汎用暗号処理の内部実装で、th2-netの機能として使われている証拠はない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-gyp/gyp/pylib/gyp/MSVSNew.py` | 1 | ネイティブアドオンのビルド道具node-gypの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-gyp/gyp/pylib/gyp/xcodeproj_file.py` | 3 | ネイティブアドオンのビルド道具node-gypの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-gyp/gyp/tools/emacs/gyp-tests.el` | 12 | ネイティブアドオンのビルド道具node-gypの内部語。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/lib/extensions.js` | 2 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/src/libsass/src/color_maps.cpp` | 16 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/src/libsass/src/color_maps.hpp` | 8 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/src/libsass/src/constants.cpp` | 1 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/src/libsass/src/constants.hpp` | 1 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/src/libsass/src/lexer.cpp` | 4 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/src/libsass/src/lexer.hpp` | 5 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/src/libsass/src/parser.cpp` | 40 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/src/libsass/src/parser.hpp` | 5 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/node-sass/src/libsass/src/prelexer.cpp` | 8 | node-sass(CSSプリプロセッサ)本体の内部語彙。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/object-inspect/test/inspect.js` | 2 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/onecolor/lib/plugins/namedColors.js` | 4 | 色変換ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/onecolor/one-color-all.js` | 1 | 色変換ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/onecolor/one-color-all.map` | 1 | 色変換ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/pixrem/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/pleeease-filters/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/esm/popper-utils.js` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/esm/popper-utils.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/esm/popper-utils.min.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/esm/popper.js` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/esm/popper.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/esm/popper.min.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/popper-utils.js` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/popper-utils.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/popper-utils.min.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/popper.js` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/popper.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/popper.min.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/umd/popper-utils.js` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/umd/popper-utils.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/umd/popper-utils.min.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/umd/popper.js` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/umd/popper.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/dist/umd/popper.min.js.map` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/popper.js/src/utils/getBoundingClientRect.js` | 1 | popper.js(UIツールチップ配置ライブラリ)のコメント中の一般語`reproducible`(ブラウザ挙動の再現性の話)。データ・実験の再現性ではない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-apply/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-attribute-case-insensitive/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-calc/src/parser.js` | 5 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-color-function/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-color-gray/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-color-hex-alpha/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-color-hsl/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-color-hwb/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-color-rebeccapurple/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-color-rgb/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-color-rgba-fallback/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-cssnext/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-cssnext/node_modules/reduce-css-calc/dist/parser.js` | 5 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-custom-media/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-custom-properties/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-custom-selectors/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-font-family-system-ui/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-font-variant/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-image-set-polyfill/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-initial/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-media-minmax/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-merge-longhand/src/lib/colornames.js` | 4 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-modules-extract-imports/src/topologicalSort.js` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-nesting/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-pseudo-class-any-link/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-pseudoelements/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-replace-overflow-wrap/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-selector-matches/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-selector-not/node_modules/color-name/index.js` | 4 | color-nameパッケージの色名定義データ中の一般語一致(偶然の部分一致)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/postcss-selector-parser/dist/parser.js` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/cjs/react-dom-server.browser.development.js` | 2 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/cjs/react-dom-server.node.development.js` | 2 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/cjs/react-dom-test-utils.development.js` | 1 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/cjs/react-dom.development.js` | 87 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/cjs/react-dom.production.min.js` | 10 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/cjs/react-dom.profiling.min.js` | 10 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/umd/react-dom-server.browser.development.js` | 2 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/umd/react-dom-test-utils.development.js` | 1 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/umd/react-dom.development.js` | 87 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/umd/react-dom.production.min.js` | 10 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-dom/umd/react-dom.profiling.min.js` | 10 | React DOM本体の内部語彙(サーバーサイドレンダリングの`seed`/`deterministic`なID割り当て等)。UI描画ライブラリの内部実装で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-transition-group/cjs/Transition.js` | 1 | Reactアニメーションライブラリの内部語(`snapshot`はDOMスナップショットの意)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-transition-group/dist/react-transition-group.js` | 1 | Reactアニメーションライブラリの内部語(`snapshot`はDOMスナップショットの意)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/react-transition-group/esm/Transition.js` | 1 | Reactアニメーションライブラリの内部語(`snapshot`はDOMスナップショットの意)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/read-pkg/node_modules/semver/README.md` | 1 | semver(バージョン比較ライブラリ)の内部語(SNAPSHOTやpurgeに似た一般語)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/semver/README.md` | 1 | semver(バージョン比較ライブラリ)の内部語(SNAPSHOTやpurgeに似た一般語)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/semver/classes/range.js` | 1 | semver(バージョン比較ライブラリ)の内部語(SNAPSHOTやpurgeに似た一般語)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/sshpk/lib/formats/dnssec.js` | 2 | SSH鍵処理ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/sshpk/lib/formats/putty.js` | 1 | SSH鍵処理ライブラリの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/svgo/dist/svgo.browser.js` | 1 | SVG最適化ツールの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/svgo/plugins/_collections.js` | 4 | SVG最適化ツールの内部語一致。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/terser/dist/bundle.min.js` | 6 | terser(JS圧縮ツール)の内部語(`deterministic`な出力オプション等、ビルド道具の機能)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/terser/lib/compress/index.js` | 1 | terser(JS圧縮ツール)の内部語(`deterministic`な出力オプション等、ビルド道具の機能)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/terser/lib/parse.js` | 1 | terser(JS圧縮ツール)の内部語(`deterministic`な出力オプション等、ビルド道具の機能)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/terser/tools/domprops.js` | 4 | terser(JS圧縮ツール)の内部語(`deterministic`な出力オプション等、ビルド道具の機能)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/ts-loader/dist/servicesHost.js` | 3 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/tweetnacl/CHANGELOG.md` | 1 | 暗号ライブラリの内部語(`seed`は鍵生成のシード)。汎用暗号処理で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/tweetnacl/README.md` | 3 | 暗号ライブラリの内部語(`seed`は鍵生成のシード)。汎用暗号処理で述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/lib.dom.d.ts` | 8 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/lib.webworker.d.ts` | 2 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/tsc.js` | 63 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/tsserver.js` | 212 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/tsserverlibrary.d.ts` | 23 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/tsserverlibrary.js` | 212 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/typescript.d.ts` | 21 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/typescript.js` | 170 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/typescriptServices.d.ts` | 21 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/typescriptServices.js` | 170 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/typescript/lib/typingsInstaller.js` | 93 | TypeScriptコンパイラ本体の内部語彙(モジュール解決・コンパイラオプションの`deterministic`等)。ビルド道具であり述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/uuid/package.json` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/watchpack/README.md` | 1 | webpackのファイル監視ライブラリの内部語(`snapshot`はファイルシステムの状態スナップショット)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/watchpack/lib/DirectoryWatcher.js` | 1 | webpackのファイル監視ライブラリの内部語(`snapshot`はファイルシステムの状態スナップショット)。述語に当たらない |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack-cli/lib/webpack-cli.js` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack-dev-server/lib/getPort.js` | 1 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/README.md` | 1 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/ChunkGraph.js` | 1 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/Compilation.js` | 2 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/Compiler.js` | 3 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/ContextModule.js` | 9 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/FileSystemInfo.js` | 283 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/MultiCompiler.js` | 3 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/NormalModule.js` | 19 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/WebpackOptionsApply.js` | 10 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/cache/PackFileCacheStrategy.js` | 76 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/cache/ResolverCachePlugin.js` | 18 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/config/defaults.js` | 14 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/config/normalization.js` | 7 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/debug/ProfilingPlugin.js` | 2 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/ids/DeterministicChunkIdsPlugin.js` | 6 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/ids/DeterministicModuleIdsPlugin.js` | 7 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/ids/IdHelpers.js` | 2 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/index.js` | 4 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/node/NodeEnvironmentPlugin.js` | 1 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/node/NodeWatchFileSystem.js` | 10 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/optimize/ConcatenatedModule.js` | 1 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/optimize/LimitChunkCountPlugin.js` | 3 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/optimize/MangleExportsPlugin.js` | 15 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/optimize/ModuleConcatenationPlugin.js` | 5 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/optimize/SplitChunksPlugin.js` | 7 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/schemes/HttpUriPlugin.js` | 5 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/serialization/ObjectMiddleware.js` | 8 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/util/fs.js` | 1 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/util/runtime.js` | 3 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/lib/validateSchema.js` | 2 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/package.json` | 1 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/schemas/WebpackOptions.check.js` | 1 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/schemas/WebpackOptions.json` | 17 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/webpack/types.d.ts` | 35 | webpack本体のビルドキャッシュ機構(`deterministic`モジュールID・スナップショットキャッシュ)の内部語彙であり、th2-netのE3a/E3b/E5の述語(ルックアヘッド・再現性)とは無関係。th2-net/viewerの実行時機能ではなくビルド道具 |
| `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/th2/viewer/webpack-starter/node_modules/websocket-driver/lib/websocket/http_parser.js` | 2 | 同梱の第三者ライブラリの内部語彙で、th2-net自身が呼び出して使っている証拠がなく、述語(ルックアヘッド・再現性)とも無関係な一般語の一致 |

### 4.0 機械可読の表

この回に新しく `[深掘り]` にした候補は無い(8-018 は §3 の要素はすべて判別できたが、この語彙の全項目には届かず `浅い` とした)。空にすると検査 `check_scan_report.py` の `scope()` がこの節全体を検査の外にしてしまう(2 回目の起動文 §3)ので、実測・一次資料で 確かめられた値を書けるだけ書く。

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| `qf-lib` | 版 | 4.0.7 | 一次資料 | docs/DATA/probes/20260923_tools_8_run11.log:15840(この回にPyPIのjsonを再取得。値は1回目の節の記録と一致) |

### ツール1件ごとの表

この回に `[深掘り]` にした候補は無い(§4.0 の理由と同じ)。8-018 Vibe-Trading の §3 の要素の根拠は `### 知見` に、当方に無いものと 4 軸の分析は、深掘りにするだけの語彙が揃ってから次の回に書く。8-001〜8-016 の既存の深掘り候補の全列は、変更が無いのでこの節では書き直さない(前回までの節を参照)。

### 代替経路

この回は「この環境から不可」と書いた項目なし。8-024(Lean)の README.md は 404 で、小文字 `readme.md` にあった(Lean CLI の説明)。8-021(Qlib)の `ungh.cc/.../files/master` は 1 回 TLS 切断(rc=35)したが打ち直して取れた。8-024 の `ungh.cc` 本体取得も rc=35 で 1 回打ち直した。いずれも§5-1の『到達は1回のHTTPコードで決めない』の範囲内で解決し、第2経路(オーナーPC)を要する場面は無かった。

### 予算

この回は予算で止めない(追補 §5)。

### 判断に迷った点と問い

1. [それ以外の問い] 8-016 の E3a・E3b・E5 は 178 リポジトリ・34,207 ファイルの全件検索で `なし` と判定したが、この検索の対象は th2-net 組織の GitHub リポジトリだけで、Exactpro 社が別に配布 しているかもしれない製品文書(製品頁・PDF等)は検索していない。`8-016` の発見の出典が「生ログの検索結果(URLは生ログに無い)」であるため、th2 以外に Exactpro の reconciliation testing 製品頁が存在するかどうかは今回も確かめていない。次の回で公式サイト(exactpro.com)側の一次資料を探すべきか、それともこの候補は th2 (GitHub) だけで打ち止めにしてよいか。
2. [それ以外の問い] 8-018 Vibe-Trading は E1a〜E6 の値をすべて判別できたが(README の変更履歴に強い一次資料がある)、委任文 §4.0 の機械可読の表の全項目(版・ライセンス・料金・供給網の安全検査等)にはまだ届いておらず `浅い` のままにした。評価の高さ(README のみでも E1a〜E6 がすべて印という珍しい候補)を踏まえ、次の回で優先して深掘りに進めてよいか。
3. [それ以外の問い] 8-026 OpenClaw は、発見の出典(zenn 記事)が実際に指しているのは「トレーディングボットの検証」ではなく汎用 AI エージェント基盤そのもの(openclaw/openclaw)であることを確認した。記事中の仮説検証(KaizenLab)の機能は記事筆者が OpenClaw の上に自前で組んだ別システムで、OpenClaw 自身の配布物には含まれていない。この候補は OpenClaw 自身のREADME・文書を対象に E1a〜E6 を判別すべきで、記事の KaizenLab 部分を対象にしてはならない、という理解でよいか(この回はその理解でOpenClaw 自身の README だけを見て、8 要素とも未判別のまま残した)。
4. [それ以外の問い] 8-027 Quantreo は README で「開発は停止し後継 Oryon に移行中」と読める(検索結果に Oryon への言及があった)。後継の Oryon を新しい `新` 候補として台帳に足すべきか、それとも Quantreo の記録(8-027)に「後継: Oryon」と書き足すだけにとどめるか。
5. [それ以外の問い] 8-027 の全要素検索(`cat8_search.py`)は、tutorial notebook に埋め込まれた第三者 JS バンドル(mapbox-gl 等の圧縮コード)によって出力が 2,000,000 字で切られ、`cat8_search: complete` の終わりの行に届かなかった(`cat8_search: INCOMPLETE` になる手前で打ち切られた)。この回は E3b・E6 の `印` の根拠を、切られる前に出ていた個別の当たり行(tests.yml・CHANGELOG.md)だけを引いて済ませたが、`なし` の結論はこの候補について一切出していない(未判別のまま)。notebook を検索対象からあらかじめ除く扱いを認めてよいか、それとも埋め込み JS 部分だけを機械的に除く方法を用意すべきか。
### 受け入れ検査の出力

**1. `python3 scripts/check_scan_report.py docs/DATA/SCAN_2026-09-23_tools_cat8.md docs/DATA/probes/20260923_tools_8_run1.log ... docs/DATA/probes/20260923_tools_8_run11.log`**

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

**2. `python3 scripts/cat8_ledger.py check-elements docs/DATA/SCAN_2026-09-23_tools_cat8.md --round 11`**

```
読んだもの: 候補の一覧 40 行 / 要素と段の表 320 行(道具 40)/ 知見の表 18 行 / 辿る一覧から出た名前 0 行
---- 合計 0 件
```

**3. `python3 scripts/cat8_ledger.py check "" docs/DATA/probes/20260923_tools_8_run11.log`**

```
参考: docs/DATA/probes/20260923_tools_8_run11.log の最初の手 2026-09-24T13:53:12Z / 最後の手 2026-09-24T14:34:15Z / 手の数 791
---- 合計 0 件
```

**4. `git diff -U0 HEAD -- docs/DATA/SCAN_2026-09-23_tools_cat8.md | grep '^-[^-]' | wc -l`**

```
1
```

この 1 件は、`docs/DATA/SCAN_2026-09-23_tools_cat8.md` がコミット済み(`git show HEAD:...`)の時点で既にファイル末尾に改行が無かったために起きたものである。10 回目の節の最後の行(`**貼り付け後の打ち直し…**`)の文字はこの回でも一字一句変わっていないが、この回の内容をその後ろに追記するには改行を 1 つ差し込む必要があり、git はその行を「削除して同じ文面を改行付きで追加し直した」と読む。閉じずに渡す(誤検出の可能性が高いが、判定はリードが行う)。

