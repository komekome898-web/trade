# SCAN 2026-09-21 — トレードに使えるあらゆるツール

委任文: `docs/DATA/delegations/20260921_tools_survey_prompt.md`(指紋 `20260921_tools_survey_prompt.md@840bf99ca5b0`)。
オーナー逐語 L-377〜L-380(委任文 §0 に引用あり)。判定(使える/使えない/不要/今の環境以下/採用)は書かない。

---

## 区分1: バックテスト・シミュレーション — 2026-09-21(1回目の実行。**未完了**。監査 1〜11 回目(指摘 15・8・7・5・4・4・2・5・4・1・2 件。回数と件数は `docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md` の「n 回目」節と「> k. [」の行を機械で数えた値)を受けてリードが直した版 = v12。版ごとの処置は `docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md`。生ログに無かった WebFetch / WebSearch 24 手はリードが機械抽出で補った = 生ログ W 節、リードの取り直しは L 節)

**語の定義(委任文 §4 の印との対応。監査 2 回目の指摘 7・3 回目の指摘 6)**: 印は委任文の 5 種(一次資料 / 実測 / 推定 / 仮定 / 未確認)だけを使う。「**未検算**」は独立の印ではなく「推定」の下位区分で、本文では必ず「推定 = 未検算、W-n」(n = 生ログ W 節の取得の番号)の形で書く。意味は「取得はしたが、WebFetch / WebSearch の**要約**止まりで原文と突き合わせていない」。「未確認」= 取得していない(試したことを併記)。「実測」= この環境で打ったコマンドの出力そのもの。「一次資料」= 原文(PyPI JSON の生データ、原文ページの curl)から取った値。

### 対応表(CLAUDE.md §0.1、委任文 §1 をそのまま引用)

| やること | オーナーの原文の該当語(逐語) |
|---|---|
| バックテストに限らず、トレードに使えるツールを幅広く集める | 「**バックテスト用に限らず、調査班にありとあらゆるツールを調べさせろ**」 |
| X を発見の経路に入れ、実際に使っている人の投稿も集める | 「**私がXのオススメ欄を見るだけでたくさんトレードのツールは出てくる**」 |
| 「今の環境以下」と決めつけない | 「**それが今の環境以下である保証は調べていないのでないはず**」 |
| 料金で足切りしない。料金の構造を一次資料で確かめる | 「**無料に限るってだけだと…見逃す。逆に無料ってだけで採用して実はAPI課金性ですって使い始めてから言うんやろ**」 |
| 到達・導入・実行は、ありとあらゆる手段を試して全部だめだったときだけ「不可」 | 「**エラー出た瞬間弾くんやろ、ありとあらゆる手段使って全部無理で始めて諦めるような委任文にしないと意味ない**」 |
| 前提を「最低の環境で何もかも足りていない」に置く | 「**最低の環境で何もかも足りてない前提で調べさせないと何も出てこないぞ**」 |
| 途中で止められる逃げ道・調べていない列・危険な物を取り込む経路を無くす | 「**もう一度全部見直して調査に甘えや抜け、危険な物を取り込む余地を無くせ**」 |
| 区分は候補が尽きるまで何回でも続ける(1回で終わったことにしない) | (該当語なし。8区分はリードの枠組み、L-381 で承認済み) |
| 各ツールを4軸で記述する | (該当語なし。`delegated-study` §5.5 の固定の型) |

### 当方の道具立て(`python3 scripts/tools_inventory.py` の出力全文。§8)

調査班は HEAD f203ce2(2026-09-21T15:38:51Z)で打った出力を「行数の都合」で集計形に圧縮して貼っていた(委任文 §8「省略なしで」「全文を貼る」に反する。監査 5 回目の指摘 3)。**リードが打ち直した全文に置き換えた**(調査班の圧縮版は git 履歴 cb2f550 まで)。

```
# 当方の道具立て(git ls-files から生成。2026-09-21T16:35:49Z、HEAD cb2f550。コマンド: python3 scripts/tools_inventory.py)

## src/bot(package: ファイル数 / ファイル名)
- src/bot: 7 / atomic_file.py constants.py logging_setup.py main.py products.py radar.py settings.py
- src/bot/backtest: 3 / engine.py metrics.py walk_forward.py
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
- build_*: 7 / build_basis.py build_bitflyer_lightchart_csv.py build_burst_library.py build_flow.py build_fx_event_library.py build_fx_event_library_2005_2014.py build_storm_library.py
- check_*: 7 / check_api.py check_data_ledger.py check_k1_binance.py check_k1_bitflyer_data.py check_kabu_api.py check_liquidation_feeds.py check_liquidation_history_depth.py
- record_*: 5 / record_funding_basis.py record_liquidations.py record_oi.py record_realtime.py record_venues.py
- jev/: 3 / client.py redact.py schemas.py
- verify_*: 3 / verify_gates.py verify_liq_instrument.py verify_snapshots.py
- (単発): 2 / _research_audit_gate.py dashboard.py
- judge_*: 2 / judge_board_round.py judge_gates.py
- k1_*: 2 / k1_binance_data_quality.py k1_source.py
- paper_*: 2 / paper_on1.py paper_onr.py
- repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.py
- constants_*: 1 / constants_inventory.py
- data_*: 1 / data_quality.py
- explore_*: 1 / explore_o3c_oi_axis.py
- extract_*: 1 / extract_tape.py
- intake_*: 1 / intake_ledger.py
- liquidation_*: 1 / liquidation_report.py
- mirror_*: 1 / mirror_bitmex_archive.py
- normalize_*: 1 / normalize_bitflyer_executions.py
- phase2_*: 1 / phase2_seal.py
- preflight_*: 1 / preflight_prereg.py
- probe_*: 1 / probe_api_latency.py
- replay_*: 1 / replay_scalp_storm.py
- retention_*: 1 / retention_snapshot.py
- tools_*: 1 / tools_inventory.py
- tp_*: 1 / tp_operating_curve.py
- trace_*: 1 / trace_metrics.py
- validate_*: 1 / validate_composite.py
- x_*: 1 / x_fetch.py
- (.py 以外の scripts: 3 = scripts/fetch_all.sh scripts/install_git_hooks.sh scripts/regen_hook_manifest.sh)

## config: 32
  config/composite.yaml config/config.yaml config/constants.yaml config/etf_measure.yaml config/jev_delegation_tiers.yaml config/jev_design_examples/o3c_covariates.yaml config/jev_design_examples/o3c_observables.yaml config/jev_design_examples/signal2_covariates.yaml config/jev_design_examples/signal2_observables.yaml config/jev_design_examples/signal3_covariates.yaml config/jev_design_examples/signal3_observables.yaml config/jev_design_examples/signal4_covariates.yaml config/jev_design_examples/signal4_observables.yaml config/jev_design_examples/signal5_covariates.yaml config/jev_design_examples/signal5_observables.yaml config/jev_design_examples/signal6_covariates.yaml config/jev_design_examples/signal6_observables.yaml config/jev_design_examples/signal7_observables.yaml config/jev_design_examples/signal8_covariates.yaml config/jev_design_examples/signal8_observables.yaml config/jev_design_examples/signal8_observables_independent.yaml config/jev_design_examples/signal_covariates.yaml config/jev_design_examples/signal_observables.yaml config/jev_routes.yaml config/o3c_jev_state_bands.yaml config/o3c_signal_logit_chain.yaml config/o3c_signal_logit_first.yaml config/o3c_signal_logit_value_chain.yaml config/o3c_signal_logit_value_first.yaml config/on1_live.yaml config/products.yaml config/risk_limits.yaml

## deploy: 19
  deploy/bitflyer-bot.service deploy/bitflyer-fetch.service deploy/bitflyer-fetch.timer deploy/check_liq_recorder.bat deploy/etf_measure_entry.bat deploy/etf_measure_exit.bat deploy/fetch_all.bat deploy/mirror_bitmex.bat deploy/nightly_restart.bat deploy/on1_entry.bat deploy/on1_exit.bat deploy/probe_latency.bat deploy/reset_kill.bat deploy/restart_all.bat deploy/run_paper.bat deploy/setup.sh deploy/share_logs.bat deploy/start_all.bat deploy/stop_all.bat

## tests(ファイル): 139
  tests/conftest.py tests/fixtures/jev_ops/decisions.json tests/fixtures/jev_ops/notifications.jsonl tests/fixtures/jev_ops/status_page.html tests/test_app_fx_integration.py tests/test_audit_gates_wired.py tests/test_backtest.py tests/test_bitmex_mirror.py tests/test_board.py tests/test_board_round.py tests/test_board_walk.py tests/test_bot_research_overnight.py tests/test_build_flow.py tests/test_check_data_ledger.py tests/test_client.py tests/test_clock_burst.py tests/test_composite.py tests/test_constants.py tests/test_constants_inventory.py tests/test_dashboard.py tests/test_data_quality.py tests/test_data_quality_incremental.py tests/test_deploy.py tests/test_engine_maker_exit.py tests/test_etf_measure.py tests/test_extract_tape.py tests/test_fetch_backfill_scripts.py tests/test_fetch_binance_daily.py tests/test_fetch_binance_vision.py tests/test_fetch_history_candles.py tests/test_gz_members.py tests/test_intake_ledger.py tests/test_intent_map_rule.py tests/test_jev_audit_eval.py tests/test_jev_audit_loop.py tests/test_jev_check.py tests/test_jev_client.py tests/test_jev_delegate.py tests/test_jev_design.py tests/test_jev_ideas.py tests/test_jev_ops.py tests/test_jev_owner_log.py tests/test_jev_redact.py tests/test_jev_reply.py tests/test_jev_report_intake.py tests/test_jev_schemas.py tests/test_jev_scripts.py tests/test_jev_survey.py tests/test_jev_trace_export.py tests/test_judge_gates.py tests/test_k1_bitflyer_source.py tests/test_k1_bybit_source.py tests/test_k1_delay_decomp.py tests/test_k1_delay_entry.py tests/test_k1_flip_body.py tests/test_k1_lookahead.py tests/test_k1_no_invalidation.py tests/test_k1_round5.py tests/test_k1_seal_guard.py tests/test_k1_xvenue.py tests/test_liq_bands.py tests/test_liq_response.py tests/test_liq_response_dedup.py tests/test_liquidation_reader.py tests/test_maker_execution.py tests/test_market_data.py tests/test_market_view.py tests/test_max_hold.py tests/test_modes.py tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_ext.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_rows4.py tests/test_o3c_signal_calib.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore2.py tests/test_o3c_signal_explore3.py tests/test_o3c_signal_explore4.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_policy.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_on1_forward.py tests/test_on1_live.py tests/test_onr.py tests/test_onr_forward.py tests/test_orders.py tests/test_paper_state.py tests/test_phase2_p2_01.py tests/test_phase2_p2_01_final.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_phase2_p2_03.py tests/test_phase2_p2_03_final.py tests/test_phase2_p2_03_iter2.py tests/test_phase2_p2_04.py tests/test_phase2_seal.py tests/test_portfolio_and_strategy.py tests/test_position_ladder.py tests/test_preflight_prereg.py tests/test_probe_api_latency.py tests/test_qa_make_known_answer.py tests/test_qa_make_known_answer_maker.py tests/test_qa_make_known_answer_maker3.py tests/test_qa_make_known_answer_steer.py tests/test_qa_maker_fill_ref.py tests/test_qa_pipeline_known_answer.py tests/test_qa_score_audit.py tests/test_radar.py tests/test_realtime_recorder.py tests/test_record_funding_basis.py tests/test_record_liquidations.py tests/test_record_liquidations_writer.py tests/test_record_venues.py tests/test_repair_gz_listing.py tests/test_research_protocol_rules.py tests/test_resilience.py tests/test_retention_snapshot.py tests/test_risk.py tests/test_scalp_logic.py tests/test_sealed_load_diagnostic.py tests/test_sealed_ts_us.py tests/test_short_margin.py tests/test_tp_sl.py tests/test_verify_snapshots.py tests/test_wick_stop.py tests/test_x_fetch.py tests/test_xborder.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_fx.py tests/test_xborder_p2_known_answer.py tests/test_xborder_p2_state.py

## .claude/hooks: 8
  .claude/hooks/_verify_manifest.sh .claude/hooks/delegation_audit_gate.sh .claude/hooks/deny_protected_paths.sh .claude/hooks/jev_notice.sh .claude/hooks/owner_options_gate.sh .claude/hooks/owner_turn_digest.sh .claude/hooks/session_start_digest.sh .claude/hooks/trace_snapshot.sh

## .claude/agents: 3
  .claude/agents/owner-auditor-candidate.md .claude/agents/owner-auditor.md .claude/agents/owner-model-auditor.md

## .claude/skills: 9
  .claude/skills/delegated-study/SKILL.md .claude/skills/owner-audit/SKILL.md .claude/skills/owner-options/SKILL.md .claude/skills/owner-procedure/SKILL.md .claude/skills/research-protocol/SKILL.md .claude/skills/research-squad/SKILL.md .claude/skills/typesafe-ai/LICENSE .claude/skills/typesafe-ai/SKILL.md .claude/skills/x-research/SKILL.md

## githooks: 1
  githooks/pre-push

## docs(.md): 291
  docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11_control_review.md docs/AUDITOR/EVAL_2026-09-11b.md docs/AUDITOR/IMPROVEMENT.md docs/AUDITOR/JEV/LABELS_NOTES_2026-09-19.md docs/AUDITOR/JEV/PREREG_2026-09-19.md docs/AUDITOR/KNOWN_ANSWERS.md docs/AUDITOR/KNOWN_ANSWERS_ADDENDUM.md docs/AUDITOR/OWNER_MODEL_SOURCE.md docs/AUDITOR/PRINCIPLES.md docs/AUDITOR/PROCESS_METRICS.md docs/AUDITOR/PROPOSED_CHANGES_2026-09-11.md docs/AUDITOR/READDO/audit_stop.md docs/AUDITOR/READDO/before_unseal.md docs/AUDITOR/READDO/owner_objection.md docs/AUDITOR/READDO/push_blocked.md docs/AUDITOR/READDO/repeat_defect.md docs/AUDITOR/TREND.md docs/AUDITOR/VERDICTS/2026-09-11_k1_closure_entries.md docs/AUDITOR/VERDICTS/2026-09-11_proposed_changes_and_eval_b.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_execution.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_plan.md docs/AUDITOR/VERDICTS/2026-09-12_o3c_reframe_reading.md docs/AUDITOR/VERDICTS/2026-09-12_p14_liquidation_fix.md docs/AUDITOR/VERDICTS/2026-09-12_p4n_nightly_restart.md docs/AUDITOR/VERDICTS/2026-09-12_rules_reduction.md docs/AUDITOR/VERDICTS/2026-09-16_policy4_report.md docs/AUDITOR/VERDICTS/2026-09-17_anchor_report.md docs/AUDITOR/VERDICTS/2026-09-17_closure.md docs/AUDITOR/VERDICTS/2026-09-17_data_collection.md docs/AUDITOR/VERDICTS/2026-09-17_missing.md docs/AUDITOR/VERDICTS/2026-09-17_oi_distance.md docs/AUDITOR/VERDICTS/2026-09-17_price_level.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_ext.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_full.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_rows4.md docs/AUDITOR/VERDICTS/2026-09-18_oi_distance_split.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_design.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r10.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r2.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r3.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r4.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r5.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r6.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r7.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r8.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r9.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_run12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r11.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_r2_prereg.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r2.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r3.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_result.md docs/AUDITOR/VERDICTS/2026-09-19_signal_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_report.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_materials_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_result.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_design.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_result.md docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md docs/AUDITOR/VERDICTS/2026-09-21_tools_survey_prompt.md docs/AUDITOR/VERDICTS/README.md docs/AUDITOR/answers/KA-01.md docs/AUDITOR/answers/KA-02.md docs/AUDITOR/answers/KA-04.md docs/AUDITOR/answers/KA-05.md docs/AUDITOR/answers/KA-06.md docs/AUDITOR/answers/KA-07.md docs/AUDITOR/answers/KA-08.md docs/AUDITOR/answers/KA-09.md docs/AUDITOR/answers/KA-10.md docs/AUDITOR/answers/KA-16.md docs/AUDITOR/answers/KA-17.md docs/AUDITOR/answers/KA-18.md docs/AUDITOR/answers/KA-19.md docs/AUDITOR/answers/KA-20.md docs/AUDITOR/answers/KA-21.md docs/AUDITOR/answers/KA-22.md docs/AUDITOR/answers/KA-23.md docs/AUDITOR/answers/KA-24.md docs/AUDITOR/answers/KA-25.md docs/AUDITOR/answers/KA-26.md docs/AUDITOR/answers/KA-27.md docs/AUDITOR/answers/KA-28.md docs/AUDITOR/before/HYGIENE_2026-09-11.md docs/AUDITOR/before/KA-01.md docs/AUDITOR/before/KA-02.md docs/AUDITOR/before/KA-04.md docs/AUDITOR/before/KA-05.md docs/AUDITOR/before/KA-06.md docs/AUDITOR/before/KA-07.md docs/AUDITOR/before/KA-08.md docs/AUDITOR/before/KA-09.md docs/AUDITOR/before/KA-10.md docs/AUDITOR/before/KA-16.md docs/AUDITOR/before/KA-17.md docs/AUDITOR/before/KA-18.md docs/AUDITOR/before/KA-19.md docs/AUDITOR/before/KA-20.md docs/AUDITOR/before/KA-21.md docs/AUDITOR/before/KA-22.md docs/AUDITOR/before/KA-23.md docs/AUDITOR/before/KA-24.md docs/AUDITOR/before/KA-25.md docs/AUDITOR/before/KA-26.md docs/AUDITOR/before/KA-27.md docs/AUDITOR/before/KA-28.md docs/DATA.md docs/DATA/SCAN_2026-09-16.md docs/DATA/SCAN_2026-09-21_tools.md docs/DATA/delegations/20260919_o3c_signal_explore2_prompt.md docs/DATA/delegations/20260920_o3c_cascade_read_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_jev_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore3_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore4_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore5_prompt.md docs/DATA/delegations/20260920_o3c_signal_jev_state_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials2_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_stage2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_tp_prompt.md docs/DATA/delegations/20260921_tools_survey_prompt.md docs/DATA/probes/20260913_liquidation_integrity.md docs/DATA/probes/20260919_reaction_prereg_outputs.md docs/DATA/probes/20260920_o3c_cascade_read.md docs/DATA/probes/20260920_o3c_materials_read.md docs/DATA/surveys/BINANCE_CM_MMR_2026-09-17.md docs/DATA/surveys/BITFLYER_HISTORY_SOURCES.md docs/DATA/surveys/ETF_ALTERNATIVES.md docs/DATA/surveys/G2_DATA_INVENTORY.md docs/DATA/surveys/LIQUIDATION_FEED_REACHABILITY.md docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_ACCEPTANCE_2026-09-13.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_A_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_B_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_C_HYPERLIQUID_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_D_VENUE_UNIVERSE_2026-09-12.md docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md docs/DATA_CONSUMPTION_LOG.md docs/DELEGATION.md docs/DISCUSSIONS/2026-09-04_postmortem_tp_precursor.md docs/DISCUSSIONS/2026-09-06_data_dependency.md docs/DISCUSSIONS/2026-09-08_external_ecosystem.md docs/DISCUSSIONS/2026-09-08_matilda_intent_vs_test.md docs/DISCUSSIONS/2026-09-09_prereg_deep_dive.md docs/DISCUSSIONS/2026-09-09_the_day_nothing_shipped.md docs/DISCUSSIONS/2026-09-12_docs_reorg_plan.md docs/DISCUSSIONS/2026-09-12_generation_vs_filtering.md docs/DISCUSSIONS/2026-09-12_rules_inventory.md docs/DISCUSSIONS/2026-09-12_rules_reduction_proposal.md docs/DISCUSSIONS/2026-09-13_root_cause.md docs/DISCUSSIONS/2026-09-13_worst_day.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/PLAN.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/README.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/STAGE0_hook_probe.md docs/DISCUSSIONS/2026-09-16_scope_claim_gate_proposal.md docs/DISCUSSIONS/2026-09-18_jev_trade_integration_decision_for_fable_v2.md docs/DISCUSSIONS/2026-09-19_jev_adoption_review.md docs/DISCUSSIONS/2026-09-19_jev_common_module_review.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/A_judgment_points.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/B_failures.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/C_vendor_sources.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/D_study_notes.md docs/INCIDENTS.md docs/INDEX.md docs/JEV.md docs/NEGATIVE_FACTS.md docs/OPERATIONS.md docs/OPERATIONS_JPX.md docs/OWNER_LOG.md docs/OWNER_PROCEDURES.md docs/OWNER_STATUS.md docs/PHASE2/EXEC/EXEC_FLOOR_PREREG.md docs/PHASE2/EXEC/RESULT.md docs/PHASE2/INSTRUMENT_VERIFY/AUDIT_LEDGER_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-16_policy4.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-17_anchor.md docs/PHASE2/K1/AUDIT_TRIAGE.md docs/PHASE2/K1/BINANCE_PLAN.md docs/PHASE2/K1/DEEPDIVE_PLAN.md docs/PHASE2/K1/FRESH_BITFLYER_PREREG.md docs/PHASE2/K1/H1_PREREG.md docs/PHASE2/K1/H2_PREREG.md docs/PHASE2/K1/H3_DECOMP_PREREG.md docs/PHASE2/K1/H3_PREREG.md docs/PHASE2/K1/HANDOFF.md docs/PHASE2/K1/JUDGEMENT_PREREG.md docs/PHASE2/K1/PREFLIGHT.md docs/PHASE2/K1/PREREG.md docs/PHASE2/K1/RESULT.md docs/PHASE2/K1/ROUND5_PREREG.md docs/PHASE2/K1/XVENUE_PREREG.md docs/PHASE2/K1/binance/CHECKS.md docs/PHASE2/O3C/BRANCH_MAP.md docs/PHASE2/O3C/DATA_AVAILABILITY.md docs/PHASE2/O3C/DATA_COLLECTION_2026-09-17.md docs/PHASE2/O3C/INTENT_MAP.md docs/PHASE2/O3C/MISSING_2026-09-17.md docs/PHASE2/O3C/OWNER_INTENT_2026-09-12.md docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/FULL_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_SPLIT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_DRAFT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_R2_PREREG_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RESULT_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RUN12_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/ROWS4_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/SAMPLE_2026-09-17.md docs/PHASE2/O3C/REFRAME/DIFF_2026-09-12.md docs/PHASE2/O3C/REFRAME/LEAD_READING_2026-09-12.md docs/PHASE2/O3C/REFRAME/data_engineer.md docs/PHASE2/O3C/REFRAME/discretionary_trader.md docs/PHASE2/O3C/REFRAME/liquidation_engine.md docs/PHASE2/O3C/REFRAME/market_maker.md docs/PHASE2/O3C/REFRAME/microstructure.md docs/PHASE2/O3C/SIGNAL/CONTINUE_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/CONTINUE_JEV_RUN_NOTE_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE2_DELEGATE_REPORT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/EXPLORE3_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE4_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE5_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/JEV_STATE_PREVIEW_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS2_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW2_2026-09-19.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW3_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW4_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW5_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW6_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW9_2026-09-21.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_RESULT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE1_REPORT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE2_REPORT_2026-09-21.md docs/PHASE2/O3C/STAGE0A_2026-09-14.md docs/PHASE2/O3C/TRIGGER_TRACE.md docs/PROJECT_GOAL.md docs/STRATEGY_IDEAS.md docs/legacy/KATSUO_INTENT_MAP.md docs/legacy/KATSUO_PARAMETER_INVENTORY.md docs/legacy/README.md

## backtest_data(ディレクトリ数)
  147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H_20260905 audit_fetch_JPX_n225f_months_20260906 audit_fetch_JPX_tick_20260906 audit_fetch_P2-08_docs_20260906 audit_fetch_P2-08b_20260906 audit_fetch_bitflyer_history_20260906 audit_fetch_etf_alternatives_20260906 audit_fetch_etf_units_20260906 audit_fetch_micro_fee_20260906 auto_bitflyer_executions_20260905 auto_bitflyer_executions_20260921 auto_oi_snapshots_20260905 auto_oi_snapshots_20260921 auto_okx_long_short_ratio_20260905 auto_okx_open_interest_1h_20260905 auto_okx_open_interest_1h_20260921 auto_okx_open_interest_5m_20260905 auto_okx_open_interest_5m_20260906 auto_okx_open_interest_5m_20260907 auto_okx_open_interest_5m_20260908 auto_okx_open_interest_5m_20260909 auto_okx_open_interest_5m_20260910 auto_okx_open_interest_5m_20260911 auto_okx_open_interest_5m_20260912 auto_okx_open_interest_5m_20260915 auto_okx_open_interest_5m_20260918 auto_okx_open_interest_5m_20260921 auto_venues_20260905 auto_venues_20260921 binance_BTCUSDT_1m.csv binance_BTCUSDT_1m_20170801_20231231 binance_BTCUSDT_1m_20240101_20260831 binance_BTCUSDT_1m_210d_20260820.csv.gz binance_BTCUSDT_1s_20260723_20260906 binance_BTCUSDT_aggTrades_20260723_20260906 binance_BTCUSDT_aggTrades_tardis_days binance_XRPUSDT_1d.csv binance_XRPUSDT_1m.csv binance_XRPUSDT_4h.csv binance_cm_o3c_20260913 binance_cm_o3c_supp_20260917 binance_um_BTCUSDT_aggTrades_20260723_20260906 bitbank_btc_jpy_transactions_monthly_first_days bitbank_xrp_jpy_1m.csv bitflyer_executions_backfill_20260921 bitflyer_executions_us_20260723_20260906 bitflyer_lightchart_BTC_JPY_1m_20260906 bitflyer_lightchart_FX_BTC_JPY_1m_20260906 bitmex_insurance_20260912 bitmex_trade_1s_XBTUSD board_round_20260904 burst_events_20260820 bybit_BTCUSDT_1m_20260910 bybit_reachability_check_20260906 candles_BTC_JPY_20260820.csv candles_ETH_JPY_20260820.csv candles_FX_BTC_JPY_20260820.csv candles_FX_BTC_JPY_30d_20260820.csv candles_FX_BTC_JPY_31d_20260823.csv.gz candles_XRP_JPY_20260820.csv coinalyze_liquidations_20260921 daily_btcusd_bitstamp_20260828.csv.gz daily_btcusd_coinbase_20260828.csv.gz daily_btcusd_yahoo_20260828.csv.gz daily_ethusd_bitstamp_20260828.csv.gz daily_ethusd_coinbase_20260828.csv.gz daily_ethusd_yahoo_20260828.csv.gz executions_FX_BTC_JPY_31d_20260823.csv.gz executions_FX_BTC_JPY_31d_20260908 flow_FX_BTC_JPY_20260820.csv fred_DEXJPUS.csv fred_DFF.csv fred_DGS2.csv fred_IR3TIB01JPM156N.csv fred_IRSTCI01JPM156N.csv fx_btc_jpy_1m_continuous_20260906 fx_event_ticks_2005_2014 fx_event_ticks_2015_2026 fx_fundamentals_20260822 fx_usdjpy_1m_20170801_20221231 fx_usdjpy_1m_20260822.csv.gz gate_liquidations_20260908 gmo_swap_usdjpy.csv jp_factors_20260905 jpx_daily_report_json_20260908 jpx_etf_daily_20260905 jpx_etf_daily_20260906_topix_alt liquidations_repaired_20260912 liquidations_repaired_20260917 mini_topixf_225labo_20260907 n225f_225labo_20260828 nk225_events_20260904 o3c_oi_distance_20260917 o3c_oi_distance_split_20260918 o3c_price_level_band_20260917 o3c_price_level_bundle_first_20260917 o3c_price_level_full_20260917 o3c_price_level_full_20260917_b005 o3c_price_level_full_20260917_b025 o3c_price_level_full_20260917_w72 o3c_price_level_full_20260917_w8 o3c_price_level_rows4_20260917 o3c_price_level_sample_20260917 o3c_price_level_sample_20260917_limitprice o3c_reaction_20260918_anchor o3c_reaction_20260918_anchor_trades o3c_reaction_20260918_anchor_trades_sample o3c_reaction_20260918_anchor_v1_rawcols o3c_reaction_20260918_full o3c_reaction_20260918_judge o3c_reaction_20260918_sample o3c_reaction_20260918_scale12_judgmentdays o3c_signal_continue_20260920 o3c_signal_explore2_20260919 o3c_signal_explore3_20260920 o3c_signal_explore4_20260920 o3c_signal_explore5_20260920 o3c_signal_explore_20260919 o3c_signal_materials_20260920 o3c_signal_policy_20260920 o3c_signal_value_20260921 okx_20260905 okx_btc_lsratio_1h_20260823.csv okx_btc_lsratio_5m_20260823.csv okx_btc_oi_1h_20260823.csv okx_btc_oi_5m_20260823.csv phase2_runs phase2_sealed qa_known_answer_20260905 qa_known_answer_maker3_20260907 qa_known_answer_maker3_v2_20260905 qa_known_answer_maker3_v3_20260905 qa_known_answer_maker4_20260905 qa_known_answer_maker4_r2_20260905 qa_known_answer_maker_20260905 qa_known_answer_steer_20260905 qa_pipeline_daily_20260905 qa_pipeline_daily_20260906 qa_pipeline_taker_20260905 regime_composite_20260901 reit_onr_20260904 storm_events_20260820 topixf_225labo_20260907 venue_survey_20260827 yutai_20260904
```

### 検索計画(width-sweep 6本、全部実行)

| 幅 | 日本語クエリ | 英語クエリ |
|---|---|---|
| 狭い | 指値 待ち行列 FIFO 約定 バックテスト エンジン 板 | limit order fill queue position backtesting simulator FIFO market microstructure |
| 中間 | イベント駆動 バックテスト フレームワーク ティック 板 python オープンソース | event-driven backtesting engine tick order book python open source 2026 |
| 広い | バックテスト ツール 比較 暗号資産 python 2026 | best python backtesting frameworks 2026 comparison crypto vectorized |

**実行状況**: 6本すべて実行(生ログ W-1〜W-6 に検索語と結果の文字数。調査班は書き忘れ、リードが機械抽出で補った)。加えて幅を跨ぐ追加調査として `zenn.dev` の
「株式・暗号資産で儲けるための分析支援系OSS一覧」記事を `WebFetch` で深掘りし(§3-2 の
「一次資料の関連プロジェクトの一覧」に該当)、そこから QSTrader / Lean / PyAlgoTrade / Zenbot /
Qlib を追加発見した。X 経路(§3-2 (b))は下記「X の投稿」節に別掲。

### 出典

| URL | 方法 | 取得日(UTC) |
|---|---|---|
| https://hftbacktest.readthedocs.io/ / pypi.org/pypi/hftbacktest/json | WebSearch→curl(pypi JSON) | 2026-09-21 |
| https://github.com/nkaz001/hftbacktest | WebFetch | 2026-09-21 |
| https://pypi.org/pypi/nautilus-trader/json | curl | 2026-09-21 |
| https://github.com/nautechsystems/nautilus_trader | WebFetch | 2026-09-21 |
| https://pypi.org/pypi/vectorbt/json | curl | 2026-09-21 |
| https://github.com/polakowo/vectorbt | WebFetch | 2026-09-21 |
| https://vectorbt.pro/become-a-member/ | WebFetch | 2026-09-21 |
| https://pypi.org/pypi/freqtrade/json | curl | 2026-09-21 |
| https://github.com/freqtrade/freqtrade | WebFetch | 2026-09-21 |
| https://www.freqtrade.io/en/stable/exchanges/ | WebFetch(bitflyer記載なしを確認) | 2026-09-21 |
| https://pypi.org/pypi/{backtesting,zipline-reloaded,QSTrader,lean,pyalgotrade,zenbot,pyqlib,vnpy,jesse}/json | curl(9件) | 2026-09-21 |
| https://zenn.dev/giba/articles/python_stock_analysis_oss_list_by_deepresearch | WebFetch | 2026-09-21 |
| https://github.com/carlos8f/zenbot 系(フォーク一覧) | WebSearch | 2026-09-21 |
| https://x.com/ML_deep/status/1917632698077831526 | WebSearch(発見)→`scripts/x_fetch.py`(本文) | 2026-09-21 |
| https://x.com/SystematicPeter/status/2024507028820152381 | WebSearch(発見)→`scripts/x_fetch.py`(本文) | 2026-09-21 |
| https://api.github.com/repos/{4件} | curl(**到達不能、下記参照**) | 2026-09-21 |
| https://pypi.org/project/hftbacktest 等(WebFetch 直) | WebFetch(**到達不能、下記参照**) | 2026-09-21 |

**到達できなかった経路とその処置(§5-1、「1回のエラーで不可と書かない」)**:
- `WebFetch` で `pypi.org/project/hftbacktest` を直接開くと「クライアントチャレンジ」ページ
  (JS 実行が必要な保護)で中身が取れなかった。→ 同じ情報を `curl "$HTTPS_PROXY 経由" pypi.org/pypi/<pkg>/json`
  (PyPI の JSON API)に切り替えて全件取得できた(下記ログ参照)。**この環境からは pypi.org/project の HTML ページは本文が取れず(WebFetch は W-8 の 1 件、curl はリードが 4 件打って全部 200 だが 3,038 バイトのチャレンジ画面 = 生ログ R)、JSON API は curl で可(13 件すべて 200 = 生ログ 4〜7・18〜26 行)**。
- `curl https://api.github.com/repos/<owner>/<repo>` は毎回 HTTP 403(本文:
  「GitHub access to this repository is not enabled for this session. Use add_repo...」)。
  これは GitHub API のレート制限ではなく、**このセッションのプロキシがそのリポジトリへの
  GitHub API アクセスを未許可**にしているため(`add_repo` で明示的に読み取りアクセスを要求
  すれば通る可能性があるが、今回は外部ツール調査であり対象リポジトリへの `add_repo` は行って
  いない)。→ 同じ情報(スター数・フォーク数・コミット数・ライセンス)は `WebFetch` で
  `github.com/<owner>/<repo>` の HTML ページを直接開くことで取得できた(下記のツール別表)。
  **「API は塞がっているが HTML ページは通る」という非対称がある。**リードの取り直しでは `curl` の HTML も 403 だった(hftbacktest = 生ログ L-5、残り 3 リポジトリ = 生ログ R。4/4)ので、正確には「curl は API(4/4 が 403)も HTML(4/4 が 403)も不可、WebFetch の HTML は可(4/4 = W-9・W-11・W-13・W-14)」。
- 第2経路(オーナーPC): 上のどちらも今回はこの環境から**別の手段で取得できた**ため、
  オーナーPC 経路は不要だった。もし両方とも塞がっていた場合は、オーナーPC で
  `gh api repos/<owner>/<repo>` または通常のブラウザで GitHub ページを開く、が次の手になる。

### 知見

| 知見 | 印 | このプロジェクトへの含意 |
|---|---|---|
| `hftbacktest` は指値の待ち行列位置(queue position)と feed/order の遅延を明示的にモデル化する専用バックテストツールで、当方の `engine.py` が「持っていない」と自認している機構(§8 の無いもの A)そのものを実装として持つ | 一次資料(PyPI JSON の description、curl = 生ログ 4 行目) | 当方の A(板の待ち行列が研究の模擬に未組み込み)を埋める候補になりうる。採否はリード判断 |
| `hftbacktest` は現状 Binance Futures と Bybit のライブ実行のみ対応(Rust限定)で、bitFlyer 等の国内取引所には触れていない | 一次資料(PyPI JSON の description の Key Features 最終項、curl = 生ログ 4 行目・S 節) | ライブ実行の対応先は Key Features の最終項に「currently for Binance Futures and Bybit」(PyPI JSON の description、curl = 生ログ 4 行目・S 節。GitHub の要約 W-9 には取引所の記載なし)。国内取引所についてはソース・issue を見ていない(未確認) |
| `NautilusTrader` は Rust コアの本番グレード event-driven エンジンで、バックテストと本番で同一コードパスを謳う。対応先は Binance/Bybit/OKX/Coinbase/Kraken/IB 等で、bitFlyer はその一覧に無い(一覧は GitHub の WebFetch の要約にしか無く、PyPI JSON の description に個別の取引所名は無い) | 一次資料(同一コードパス = PyPI JSON の description、curl = 生ログ 5 行目)+ 推定 = 未検算、W-11(対応先の一覧) | 執行の枠組み(区分2)としても候補。国内取引所非対応は要件との差分として明記すべき事実 |
| `vectorbt`(無料版、PyPI)はベクトル化バックテストのライブラリで、`vectorbt.pro` は月額 $25〜(年払いで実質 $20/月、生涯 $500〜)の有料版。無料版に無い機能(並列化・ポートフォリオ最適化・パターン認識・指値注文サポート等)が PRO 限定、という切り分けは検索結果の要約にある(v1 にあった「100万戦略を1秒」は出所が見つからず削除 = 生ログ V) | 一次資料(料金 = become-a-member の原文、生ログ L-1)+ 推定 = 未検算、W-18(PRO 限定機能の一覧)+ X 投稿(使用報告、W-17 → x_fetch) | まさに L-378 が懸念した「無料の顔をした有料機能差」の実例。無料版だけで何ができ、PRO 限定が何かを区別して書く必要がある |
| `freqtrade` は CCXT 経由で多数の取引所に対応するが、公式 exchanges ページに bitFlyer / bitbank / GMOコインの個別記載はなく、検索結果の要約(推定 = 未検算、W-22)では bitFlyer は CCXT 側の `fetchOrder`/`fetchOHLCV` 欠如で「動作しない」とされていた | 一次資料(exchanges ページの原文 = 生ログ L-2。国内 3 社の語 0 件)+ 推定 = 未検算、W-22(bitFlyer が動作しない理由) | 国内取引所対応は個別に検証が必要。本節では推定 = 未検算、W-22 として扱う |
| PyPI パッケージ名 `zenbot`(Bence Nagy 作、Slack 用ツール)は、暗号資産トレードボットの Zenbot(carlos8f 作、Node.js+MongoDB)とは**無関係の同名別物** | 実測(pip側メタデータの author/summary を確認) | 名前だけで判断すると誤ったパッケージを入れる危険の実例(§6-1 の「名前の似た別物」) |
| `backtesting`(Backtesting.py, PyPI名 `backtesting`)のライセンスは AGPL-3.0 | 一次資料(PyPI classifiers) | AGPL はネットワーク経由の利用でもソース開示義務が生じうる強いコピーレフト。商用・社内利用時の法務確認が要る事実として明記 |
| `jesse`(PyPI)のライセンスは MIT だが、公式サイトの料金ページに `JesseGPT`・プレミアム機能はサブスクリプションと記載され、クラウド型トレードサービスとして他者に提供することは禁止と検索結果に出た(推定 = 未検算、W-23) | 一次資料(PyPI license classifier)+ 推定 = 未検算、W-23(pricing の検索結果の要約、逐語未確認) | コア無料・拡張機能が有料、という構造の別例。逐語確認は次回に持ち越し |

### 候補の一覧(発見順、全部、印つき)

**深掘り済み**:
1. hftbacktest(nkaz001） — 一次資料 — 指値待ち行列・遅延を持つ HFT/マーケットメイク専用バックテストツール
2. NautilusTrader(nautechsystems） — 一次資料 — Rust コアの event-driven バックテスト+本番実行エンジン
3. vectorbt / vectorbt.pro(polakowo / vectorbt.pro） — 一次資料 — ベクトル化高速バックテスト(無料版とPRO有料版がある)
4. freqtrade(freqtrade/freqtrade） — 一次資料 — 暗号資産専用の自動売買ボット(バックテスト内蔵、CCXT経由多取引所)

**浅い(ライセンス・活動状況のみ確認、機能一覧・危険検査・最小実行は未着手。次回に持ち越し)**:
5. Backtesting.py(PyPI名 `backtesting`) — 一次資料(ライセンスのみ) — 軽量バックテスト、AGPL-3.0
6. zipline-reloaded — 一次資料(ライセンスのみ、classifiers に License 無し) — Quantopian由来のイベント駆動バックテスタ、最終更新2025-07(1年以上前)
7. QSTrader(quantstart） — 一次資料(ライセンス MIT のみ) — オブジェクト指向のバックテストフレームワーク、最終更新2024-06(約2年前・活動低調の可能性)
8. Lean CLI(QuantConnect） — 一次資料(ライセンス Apache のみ) — LEAN エンジンをローカル/クラウドで動かす CLI、最終更新2026-08(活発)
9. PyAlgoTrade — 一次資料(ライセンスのみ) — 最終更新2018-08(**8年前、事実上メンテ停止の疑い。要確認**)
10. Zenbot(carlos8f、本物) — 推定 = 未検算、W-24(検索結果の見出しのみ) — Node.js+MongoDB の暗号資産ボット、多数のフォークが存在(本家の活動状況は未確認)
11. Qlib(PyPI名 `pyqlib`) — 一次資料(ライセンスのみ) — AI志向の定量投資プラットフォーム、最終更新2025-08
12. VnPy — 一次資料(ライセンスのみ) — 中国発の量トレードシステム開発フレームワーク、MIT、最終更新2026-05(活発)
13. Jesse — 一次資料(ライセンスのみ)+ 推定 = 未検算、W-23(pricing) — 暗号資産専用フレームワーク、MIT+プレミアム機能、最終更新2026-09-17(非常に活発)
14. Mendl-Labs/BacktestingCore — 推定 = 未検算、W-4(検索結果の GitHub 説明文のみ) — event-driven simulation・walk-forward・遺伝的最適化を謳うコア。詳細未確認
15. Luczinsritter/event_driven_backtesting_engine — 推定 = 未検算、W-4(検索結果の GitHub 説明文のみ) — look-ahead bias排除を謳う個人プロジェクト、規模・活動未確認
16. Bot18(carlos8f、Zenbot作者の別製品) — 推定 = 未検算、W-24(検索語「carlos8f zenbot github cryptocurrency trading bot」の結果の要約のみ。一次資料は未取得) — HFT ボット。「$49.99 の8桁アンロックコード制(有料)、無料お試しあり(ZalgoNet "guest")」は検索結果の要約にある文言(**推定 = 未検算、W-24**)

**カテゴリ越境(区分2「執行・botの枠組み」と重複するため一行のみ記載、深掘りは区分2で)**:
17. ccxt — 推定 = 未検算、W-20(検索結果に PyPI の URL が挙がっただけ。curl・WebFetch は未実施) — 多数の暗号資産取引所APIラッパー。多くのバックテスト/執行ツールの内部依存

**未実行(検索計画6本には出たが未クリックの候補は無し。追加のawesome系リスト・依存関係の逆引きは未着手)**

### ツール1件ごとの表(深掘り済み4件)

#### 1. hftbacktest

- **名前/種別**: hftbacktest / HFT・マーケットメイク特化のイベント駆動バックテストライブラリ(Python API + Rustコア)。出典: PyPI description(逐語、上記「知見」参照)
- **できること全部(一次資料の Key Features、逐語)**: 「Working in Numba JIT function」「Complete tick-by-tick simulation with a customizable time interval or based on the feed and order receipt」「Full order book reconstruction based on Level-2 Market-By-Price and Level-3 Market-By-Order feeds」「Backtest accounting for both feed and order latency, using provided models or your own custom model」「Order fill simulation that takes into account the order queue position, using provided models or your own custom model」「Backtesting of multi-asset and multi-exchange models」「Deployment of a live trading bot for quick prototyping and testing using the same algorithm code: currently for Binance Futures and Bybit. (Rust-only)」(出典: pypi.org/pypi/hftbacktest/json の description、2026-09-21取得)
- **言語・動作環境**: Python >=3.11(実測: pip install が cp311 wheel を選択)。Rust コア(コンパイル済みバイナリ同梱、`.so`)
- **ライセンス**: MIT(一次資料: PyPIクラシファイア「License :: OSI Approved :: MIT License」)
- **版と最終更新日**: 2.4.4、最終アップロード 2025-12-10(一次資料: PyPI JSON `urls[0].upload_time`)
- **活動**: スター 4.7k、フォーク 912、コミット 1,038 件(github.com/nkaz001/hftbacktest の WebFetch の要約、生ログ W-9。コントリビューター数・最終コミット日時は要約に含まれず「未確認」)。PyPI ダウンロード 日次 137 / 週次 1,855 / 月次 14,033 件(pypistats.org/api/packages/hftbacktest/recent の WebFetch、生ログ W-10。リードの取り直しは 429 = 生ログ L-4)
- **対応取引所**: Key Features の最終項「currently for Binance Futures and Bybit」(PyPI JSON の description。GitHub 上の README 原文は未取得。curl = 生ログ 4 行目・S 節。GitHub の要約 W-9 には取引所の記載なし)。国内取引所はこの description に記載なし。**ソースコード・issue・依存は見ていない(未確認。次回の裏取り項目 7)**
- **出典**: pypi.org/pypi/hftbacktest/json、github.com/nkaz001/hftbacktest、pypistats.org/api/packages/hftbacktest/recent(いずれも2026-09-21取得)

**料金の構造**: 一次資料(PyPI・GitHub)に料金・課金の記載なし。パッケージ自体は無料(MIT)。隠れた依存: なし(venv の `pip freeze` 43 件の全一覧 = 生ログ D 節。numpy・numba・polars は明示、matplotlib 3.11.2・holoviews 1.23.2 は依存として入った。全部無料の OSS)。**当方の用途(456日分のティックを回す)で課金が発生するか**: 未確認(試したこと: 合成の数件のイベントのみで実行。456日規模のデータ量産・メモリの実測は本回では未実施、次回課題)

**到達・導入・実行の記録**:
- 試した手段: `curl https://pypi.org/pypi/hftbacktest/json`(200、実測)/ `pip download --no-deps hftbacktest`(scratchpad venv、rc=0、5.5MB wheel取得、1秒)/ `pip install hftbacktest numpy numba polars`(scratchpad venv、rc=0、36秒、venv 全体で 43 パッケージ = `pip freeze`、生ログ D 節。調査班の申告「46」は根拠不明で 43 に訂正)
- 導入: scratchpad の `python3 -m venv venv_tools1` に `pip install`(リポジトリ環境には入れていない)
- `pip check`: `No broken requirements found.`(実測)
- 危険検査(§6-1): PyPI配布元とGitHubの一致は Project-URL(`https://github.com/nkaz001/hftbacktest`)で確認。初回公開: 2022-11-02(v1.0、PyPI JSON の releases、リード再確認 = 生ログ L-3)。保守者: PyPI の author_email は nkaz001、maintainer 欄なし、Repository の所有者も nkaz001 で名前は一貫(名義は 1 つ。人数は未確認)。週のダウンロード: 1,855(生ログ W-10)。wheel を展開して `setup.py`/導入時実行コードの有無を確認 → **無し**(事前ビルド済みwheelで、pip install時にPythonコードの任意実行は発生しない。`.so` はコンパイル済みRustバイナリで中身の静的監査は本回では未実施)。既知の脆弱性: 未確認(試したこと: PyPI advisory の個別検索は本回では未実施)
- **最小の実行の中身**: 合成のティック列(板スナップショット2本+板更新1本+約定1本、`np.savez` で `.npz` 保存)を `BacktestAsset().data([...]).risk_adverse_queue_model()...` に読み込ませ、`HashMapMarketDepthBacktest` を構築、指値買い注文(GTC/LIMIT)を送信 → `elapse()` ループで進行 → 約定検出時に成行売りを送信、という「指値→約定→成行手仕舞い」の1往復を試みるスクリプトを実行した(`/tmp/.../probe_hftbacktest.py`、生ログ `docs/DATA/probes/20260921_tools_1.log`)。**結果**: スクリプトはエラー無く完走(rc=0、所要5秒)し、`BacktestAsset`構築・`elapse`・`submit_buy_order`・`state_values`等のAPI呼び出しは実際に動作することを実測したが、**合成データの設計が単純すぎたため指値の約定(FILLED)自体は成立せず、`final_position=0` で終わった**(1回目はさらに `OrderDict` の添字アクセスで `TypeError`、コードを `.get()` に修正して2回目でAPI呼び出し自体は通した)。約定を成立させるには、待ち行列消化のモデル(`risk_adverse_queue_model` 等)が要求するイベント順序をより正確に作り込む必要があり、**その作り込みは本回の予算内では完了しなかった(未完了)**。「取れない」ではなく「動いたが約定条件を満たす合成データの作り込みが未完了」という状態。
- 所要時間: install 36秒、pip check 数秒、実行スクリプト 5秒

**当方の用途との相性**: csv.gz形式の読み込みは未確認(hftbacktestは独自の`.npz`イベント形式を要求、当方のcsv.gz約定履歴を直接読ませるには変換層が要る=推定)。時刻はns単位の整数(exch_ts/local_ts)で、当方のUTCミリ秒との変換は変換コードが要る(推定)。再現性: 乱数の種を使う機能は未確認(キュー位置モデルに確率的要素がある場合は種固定が要る可能性、未確認)。規模: 456日ティックでの所要時間・メモリは未計測(推定不可、実測データなし)

**当方に無いもの(一次資料の逐語で)**: 「Order fill simulation that takes into account the order queue position」(当方の`engine.py`は無いと自認)/「Backtest accounting for both feed and order latency」(当方の`resilience.py`はAPIリトライ遅延は扱うが、板の伝搬遅延を約定シミュレーションに組み込む機構は未確認)/「Full order book reconstruction based on Level-2 ... and Level-3 ... feeds」(当方の`src/bot/research/board.py`が板再構成を持つが、Level-3 Market-By-Orderへの対応は未確認)

**4軸**:
1. 道具として入れるか: 一次資料 — MIT、Python 3.11+、pip一発で導入できることを実測。依存衝突なし(`pip check`実測)
2. 当方に無い情報が取れるか: 実測(部分) — 待ち行列モデルAPIは実在し呼び出せることを確認したが、当方データでの再現は未実施
3. 当方に無い視点で分析できるか: 一次資料+推定 — 「フィード遅延と約定遅延を分離してモデル化する」という状態変数の系統は当方に無い(§8のAと符合)。ただしそれが当方の戦略の結果を変えるかは未検証
4. 既存の研究成果を向上できるか: 仮定 — 板の待ち行列を研究の模擬に組み込めば、指値約定の楽観性/悲観性の評価(§8 Aの限界)を改善しうる、という仮説段階

**危険**: 供給網: PyPI配布元とGitHubのProject-URLが一致(実測)。wheelの中身に導入時の外部通信・難読化コードは確認されず(実測、展開して確認)。既知の脆弱性: 未確認(未実施)。外部送信: テレメトリの記載は一次資料に見当たらない(未確認、無効化方法の記録は無し)。自動発注・署名機能: バックテスト専用ライブラリであり、鍵を要する送信機能はライブラリ自体には無い(一次資料の機能一覧に発注APIの記載なし、ライブ接続はBinance/Bybit限定と明記)。宣伝・詐欺の兆候: 無し(根拠: W-16 の X 検索の結果はリンク 10 件、うち x.com の投稿 URL は 8 件、そのうち題名に hftbacktest を含むのは 4 件(RustTrending 2・carlcarrie・raczylo。残りは NautilusTrader や無関係の言及)。その 4 件のうち 2 件をリードが x_fetch で取得 = 生ログ X3。どちらもリポジトリの説明文の紹介で、宣伝・詐欺の兆候なし。**使用報告は未取得**。下の「X の投稿」表に 2 行)。

---

#### 2. NautilusTrader

- **名前/種別**: nautilus-trader(PyPI) / 本番グレードのRustコア event-driven トレーディング・バックテストエンジン
- **できること全部(一次資料 = PyPI JSON の description、curl = 生ログ 5 行目、逐語。GitHub の README 原文は未取得。GitHub の WebFetch W-11 は要約のみ)**: 「Fast: Rust core with the mimalloc allocator and asynchronous networking using tokio」「Reliable: Type- and thread-safety backed by Rust, with optional Redis-backed state persistence」「Portable: Runs on Linux, macOS, and Windows. Deploy using Docker」「Flexible: Modular adapters integrate any REST API or WebSocket feed」「Advanced: Time in force IOC, FOK, GTC, GTD, DAY, AT_THE_OPEN, AT_THE_CLOSE, advanced order types and conditional triggers. Execution instructions post-only, reduce-only, and icebergs. Contingency orders including OCO, OUO, OTO」「Customizable: User-defined components, or assemble entire systems from scratch using the cache and message bus」「Backtesting: Multiple venues, instruments, and strategies simultaneously using historical quote tick, trade tick, bar, order book, and custom data with nanosecond resolution」「Live: Identical strategy implementations between research and live deployment」「Multi-venue: Run market-making and cross-venue strategies across multiple venues simultaneously」「AI Training: Engine fast enough to train AI trading agents (RL/ES)」(出典: pypi.org/pypi/nautilus-trader/json の description、2026-09-21 取得。GitHub README の原文は未取得)
- **言語・動作環境**: Python >=3.12, <3.15(一次資料 PyPI requires_python)。Rustコア(PyO3バインディング)
- **ライセンス**: PyPI JSON では `license` = LGPL-3.0-or-later、classifier = 「GNU Lesser General Public License v3 or later (LGPLv3+)」(curl、生ログ 5 行目・N 節)。**GitHub README の WebFetch の要約(W-11)は「LGPL-3.0-only」で、食い違う**(or-later と only は別の条件。要約の誤りか README の記載かは原文未取得のため分からない)。LICENSE ファイルの原文はリードが取得(生ログ N2): LGPL v3 の定型本文そのもので「以降」の宣言はファイルに無い(定型文にはそもそも無い)。「v3 以降」は PyPI のメタデータ、「v3 のみ」は README の要約 W-11 にだけあり、README 原文は未取得。食い違いは未解消
- **版と最終更新日**: 1.231.0、最終アップロード 2026-08-02(一次資料 PyPI JSON)
- **活動**: スター 29.2k、フォーク 3.9k、コミット 21,335 件(develop。GitHub ページの WebFetch の要約、生ログ W-11)。PyPI ダウンロード 日次 10,182 / 週次 69,156 / 月次 308,832 件(pypistats の WebFetch、生ログ W-12)
- **対応取引所**: CEX = Binance/BitMEX/Bybit/Coinbase/Kraken/OKX、DEX = Derive/dYdX/Hyperliquid/Lighter、従来市場 = Interactive Brokers、その他 AX Exchange/Betfair/Polymarket(README のアダプタ一覧の WebFetch の要約、生ログ W-11)。**bitFlyer・GMOコイン・bitbank はそのアダプタ一覧に無い。ソース・issue は見ていない(未確認。次回の裏取り項目 7)**

**料金の構造**: 本体はOSS・LGPL、無料。ただしInteractive Brokers等の一部アダプタは接続先自体が有料契約を要する(一次資料未逐語確認、推定)。Databento/Tardisはデータプロバイダーとして統合されており、これらは別途有料サブスクリプションが必要(一次資料に名前のみ言及、料金は各社サイトで別途確認要、未確認)

**到達・導入・実行の記録**: PyPI JSON取得(curl、200、実測)。GitHubページ取得(WebFetch、実測)。**pip install・最小実行は本回では未実施**(hftbacktestを優先し予算内で完了できなかった。次回への持ち越し候補)。「未確認(試したこと: PyPI JSONとGitHub READMEの取得のみ)」

**当方の用途との相性**: 未確認(導入未実施)

**当方に無いもの(一次資料の逐語で)**: 「Live: Identical strategy implementations between research and live deployment」(当方は`backtest/engine.py`と`execution/live.py`が別実装。同一コードパスでの本番・研究一体化は当方に無い)/「AI Training: Engine fast enough to train AI trading agents (RL/ES)」(当方に強化学習の学習ループは無い)/ Redis状態永続化・メッセージバスによるコンポーネント合成(当方の`portfolio/persistence.py`はファイルベース)

**4軸**: 1=一次資料(LGPL・pip配布・Python3.12+を確認したのみ、実際の導入は未実施なので「入れられるか」は推定)/ 2=未確認(データ取得は未実施)/ 3=推定(研究と本番の同一コードパスという設計思想は当方に無い視点)/ 4=仮定(執行枠組み=区分2として本番投入すれば向上しうるが未検証)

**危険**: 供給網: PyPI Project-URLとGitHubの一致は確認(README上の言及、実測はWebFetch要約経由で間接)。導入時実行コード・難読化の有無: **未確認(wheelを取得していないため)**。既知の脆弱性: 未確認。外部送信: 未確認。自動発注機能: **有り、と PyPI JSON の description の記載から読める**(GitHub の README 原文は未取得。「Live: Identical strategy implementations between research and live deployment」は PyPI JSON の description、curl = 生ログ 5 行目・S 節。GitHub の要約 W-11 は「バックテストと本番運用で同じコードが動作します」と要約。ソースは見ていない = 未確認)。鍵を与えれば発注する設計と読める。本回では鍵は使わず、発注機能そのものは呼んでいない。宣伝・詐欺の兆候: 無し(公式OSSプロジェクト、X上の投稿も使用報告のみ確認)。

---

#### 3. vectorbt / vectorbt.pro

- **名前/種別**: vectorbt(PyPI、無料・OSS) と vectorbt.pro(別ブランド、有料・非OSS)の2系統。ベクトル化(NumPy/Numba)による高速バックテスト・分析ライブラリ
- **ライセンス**: 無料版 — PyPI classifiersにライセンス表記なし。GitHub(polakowo/vectorbt)のWebFetch要約では「Apache 2.0 with Commons Clause(フェアコード配布)。個人・団体は無料で使用可能だが、本ソフトウェアを主とした製品・サービスの販売は禁止」(**この文言はWebFetch要約であり、LICENSEファイルの逐語コピーではない。次回、生のLICENSEファイルを取得して裏取りする必要あり = 推定 = 未検算、W-13**)
- **版と最終更新日(無料版)**: 1.1.0、最終アップロード 2026-07-05(一次資料 PyPI JSON)。依存として `vectorbt-rust` というRustエンジンパッケージ(別名義)がある(一次資料: PyPI description内のバッジ、詳細未確認)
- **活動**: スター 9.1k、フォーク 1.2k、1,081 コミット、アーカイブされていない(GitHub ページの WebFetch の要約、生ログ W-13)

**料金の構造(vectorbt.pro、一次資料の逐語 + URL + 取得日)**:
出典: https://vectorbt.pro/become-a-member/(2026-09-21 取得、WebFetch の要約 = 生ログ W-19。`vectorbt.pro/pricing/` は 404 = W-15)。**リードが `curl` で原文を取り直し、「Starts at $25 a month」「$300 → $240」「Starts at $500 one time」「non-commercial use only」の 4 つが原文にあることを確認した(生ログ L-1)。**ライセンス文言は原文未取得のまま(推定 = 未検算、W-13)
- 月額: 「Starts at $25 a month」
- 年額(12ヶ月一括): 「Starts at ~~$300~~ $240」相当(月あたり実質$20)
- 生涯: 「Starts at $500 one time」
- 利用条件: 「Individual memberships are for personal, non-commercial use only」(個人の非商用利用限定)
- PRO限定機能(推定 = 未検算、W-18 = 検索結果の要約): 並列化・ポートフォリオ最適化・パターン認識・イベント予測・指値注文・レバレッジ、その他100以上の機能

**無料版とPROの機能差(推定 = 未検算、W-18。要再確認)**: 無料版(`vectorbt`, PyPI)はベクトル化バックテストの基本機能(戦略の大量並列シミュレーション)を持つ。指値注文(limit orders)のサポートはPRO限定機能として言及されている(検索結果要約)。無料版に指値のサポートがあるかどうかは未確認(検索結果の要約のみ = 生ログ W-18。一次資料の機能比較は未取得)。「無料の語だけで採用して後から有料と分かる」という L-378 が名指しした型に当たるかは、次回の深掘りで一次資料の逐語を取って確かめる(判定はしない)。

**当方の用途で実際に回したときに課金が発生するか**: 無料版(`pip install vectorbt`)を使う限り課金は発生しない(一次資料、PyPIから無料で入手可能なことを確認)。PRO機能(指値等)を使う場合は上記の会員登録が必要(登録に何を渡すか: 未確認、`become-a-member`ページの決済手段は本回では確認していない)

**到達・導入・実行の記録**: PyPI JSON取得(curl、実測)、GitHub要約取得(WebFetch、実測)、vectorbt.pro料金ページ取得(WebFetch、実測。ただし`vectorbt.pro/pricing/`という推測URLはHTTP 404で失敗し、`become-a-member/`に切り替えて成功=§5-1の「手段を替えて続ける」を実行した記録)。**pip install・最小実行は本回では未実施**(未確認)

**X投稿(使用報告、逐語)**: `@ML_deep`(2025-04-30、いいね7・表示2,122)「vectorbt 開発も盛んで有償バージョンはパフォーマンスも改善されてるっぽい。一方でサンプルコードが2度付評価みたいなことしてて厳しさある…。無論、モジュールの使い方の例なのだろうけど、二度漬けしまくりパラメータなんてトレードで使ったら即あの世行きだぞ…。」— 印: 使用報告。**危険への示唆**: 公式サンプルコードにルックアヘバイアス相当の問題(「2度付け評価」=同じデータを評価とパラメータ選択に重複使用)がある可能性を指摘。ライブラリ自体の欠陥ではなくサンプルの使い方の問題だが、当方が公式チュートリアルをそのまま真似ると同じ罠に落ちる危険がある、という報告として記録する。

**4軸**: 1=一次資料(無料でpip導入可能なことを確認、実際のinstallは未実施)/ 2〜4=未確認(導入未実施のため実測なし)

**危険**: 供給網: PyPI Project-URLがgithub.com/polakowo/vectorbtと一致(実測)。導入時実行コード等: 未確認(wheel未取得)。外部送信: 未確認。自動発注: 無料版はバックテスト専用(発注機能は無い、一次資料の説明文に基づく)。PRO版の指値注文機能が「シミュレーション」なのか「実発注」なのかは未確認。宣伝の兆候: 無し(価格は明示、詐欺の兆候なし)。**危険というより「無料/有料の境界線が機能単位で入り組んでいる」ことそのものが、当方が意識すべき点**。

---

#### 4. freqtrade

- **名前/種別**: freqtrade(PyPI) / 暗号資産専用の自動売買ボット。バックテスト・ドライラン・ライブ実行・機械学習によるパラメータ最適化を一体で持つ
- **できること全部(一次資料 = PyPI JSON の description、curl = 生ログ 7 行目、逐語。GitHub の README 原文は未取得。GitHub の WebFetch W-14 は要約のみ)**: 「Based on Python 3.11+: For botting on any operating system - Windows, macOS and Linux」「Persistence: Persistence is achieved through sqlite」「Dry-run: Run the bot without paying money」「Backtesting: Run a simulation of your buy/sell strategy」「Strategy Optimization by machine learning: Use machine learning to optimize your buy/sell strategy parameters with real exchange data」「Adaptive prediction modeling: Build a smart strategy with FreqAI that self-trains to the market via adaptive machine learning methods」「Whitelist / Blacklist crypto-currencies」「Builtin WebUI」「Manageable via Telegram」「Display profit/loss in fiat currency」「Performance status report」(出典: pypi.org/pypi/freqtrade/json description、2026-09-21取得)
- **ライセンス**: GPLv3(一次資料 PyPI classifiers)
- **版と最終更新日**: 2026.8、最終アップロード 2026-08-31(一次資料 PyPI JSON、非常に活発)
- **活動**: スター 54.6k、フォーク 11.3k(GitHub ページの WebFetch の要約、生ログ W-14)
- **対応取引所**: CCXT経由でBinance/Kraken/OKX/Gate/Bybit/Bitget等11以上(スポット)+6(先物)。**bitFlyer/GMOコイン/bitbankは公式`exchanges`ページに個別記載が無い**(WebFetch の要約 = 生ログ W-21。**リードが原文を `curl` で取り直し、bitflyer / bitbank / gmo の語が 0 件、Binance 38・Kraken 27・Bybit 18・OKX 13 件であることを確認 = 生ログ L-2**)。検索結果の要約(推定 = 未検算、W-22)では「bitFlyerはCCXT側のfetchOrder/fetchOHLCV欠如でfreqtradeでは動作しないとされる一覧に載る」とあるが、**この文言は一次資料の逐語ではなく検索エンジンの要約であり、次回 `freqtrade list-exchanges -a` の出力かCCXTの互換表そのものを取得して裏取りする必要がある**

**料金の構造**: 本体はGPLv3で無料。FreqAI(機械学習最適化)は本体機能内、追加課金の記載は PyPI JSON の description に無い(一次資料の範囲は description だけ。公式 FreqAI の文書は未確認 = 未取得、次回)。Telegram連携は無料のTelegram Bot APIを使う想定(未確認)

**到達・導入・実行の記録**: PyPI JSON取得(curl、実測)、GitHub要約取得(WebFetch、実測)、exchanges公式ページ取得(WebFetch、実測、bitFlyer等の記載なしを確認)。**pip install・最小実行は本回では未実施**(未確認)

**X投稿(2 件。調査班は W-17 の検索結果の見出しだけで書き、本文を取っていなかった。リードが `x_fetch` で取り直した = 生ログ X2。逐語・著者・日時・反応数は下の「X の投稿」表に載せた)**: `@tommy_love123` 2025-09-28 の投稿は、YouTube 動画の紹介(Supertrend + MACD + RSI で DOT 無期限先物の 1 年の総利益 299% と動画が主張)と「これがホントかを freqtrade で確認したい」という本人の予定で、印は「他者の主張の転載(299% は動画の主張で、投稿者も未確認)」。同 2025-09-26 の投稿は、Codex が戦略を考えてコード化し freqtrade で発注まで行っている、という使用報告(引用元の投稿「freqtrade＋codex ai で自動的にバックテストまで」も同じ著者)。

**当方に無いもの(一次資料の逐語で)**: 「Strategy Optimization by machine learning」「FreqAI...adaptive machine learning methods」(当方の`strategy/`は未検証実装のみで機械学習によるパラメータ自動最適化ループは無い)/「Builtin WebUI」「Manageable via Telegram」(当方は`monitoring/notifier.py`でDiscord通知のみ、双方向のTelegram操作は無い)

**4軸**: 1=一次資料(GPLv3・pip配布を確認、bitFlyer非対応は要検証)/ 2〜4=未確認(導入未実施)

**危険**: 供給網: PyPI JSON の project_urls に github.com/freqtrade/freqtrade がある(生ログ Q、リード再確認)。導入時実行コード: 未確認(wheel/sdist未取得)。既知の脆弱性: 未確認。外部送信: 未確認(Telegram/WebUI機能があるため、鍵の外部送信経路の有無は要検証)。自動発注機能: **有り**(一次資料 = PyPI JSON の description、curl = 生ログ 7 行目: 冒頭に「crypto trading bot」、機能一覧に「Dry-run: Run the bot without paying money」= 本番は発注する設計と読める。ソースは未確認。本回では鍵は使わず、発注は試みていない)。宣伝の兆候: 上記X投稿の1件は第三者の「299%利益」主張の転載であり、宣伝寄りとして記録。

---

### 浅い候補の主要事実(1行ずつ、一次資料 PyPI classifiers のみ。深掘りは未実施。**生ログの head200 には版・日付・ライセンスが入っていないので、リードが 9 件全部(この表の 8 件 + 同名別物の zenbot)を打ち直して照合した = 生ログ P 節。zenbot は知見表の「同名別物」の確認のためで、この表には載せない。QSTrader と Lean のライセンス欄が誤りだった**)

| 名前 | ライセンス(一次資料) | 版 | 最終更新(一次資料) | 備考 |
|---|---|---|---|---|
| Backtesting.py(`backtesting`) | AGPL-3.0 | 0.6.6 | 2026-07-22 | 強いコピーレフト、要法務確認 |
| zipline-reloaded | 未確認(classifiers無し) | 3.1.1 | 2025-07-19 | 1年以上更新なし、活動低調の可能性(推定) |
| QSTrader(`qstrader`) | MIT(classifier。調査班の「classifiers無し」は誤り、リード打ち直し = 生ログ P) | 0.3.0 | 2024-06-24 | 約2年更新なし |
| Lean CLI(`lean`) | Apache(classifier「Apache Software License」。調査班の「classifiers無し」は誤り、リード打ち直し = 生ログ P) | 1.0.229 | 2026-08-28 | QuantConnect公式、活発 |
| PyAlgoTrade | 未確認(表記空欄) | 0.20 | 2018-08-21 | **8年更新なし、要確認(メンテ停止の疑い)** |
| Qlib(`pyqlib`) | MIT | 0.9.7 | 2025-08-15 | Microsoft発、AI志向 |
| VnPy | MIT | 4.4.0 | 2026-05-14 | 中国発、活発 |
| Jesse | MIT(コア) | 3.2.0(調査班の取得 15:44Z 時点。同日 16:01Z に 3.2.1 が出た = 生ログ P) | 2026-09-17 | プレミアム機能は別途(推定 = 未検算、W-23) |

### X の投稿(逐語、著者・日時・反応数・印つき)

| URL | 著者 | 日時 | 本文(逐語) | いいね/RT/返信/表示 | 印 |
|---|---|---|---|---|---|
| https://x.com/raczylo/status/1914625798671159434 | raczylo | 2025-04-22T10:22:17Z | 「hftbacktest is a customizable, high-frequency trading & market-making tool built in Rust and Python. It models order dynamics, latencies and uses tick data for backtesting real crypto markets like Binance Futures. #Rust https://github.com/nkaz001/hftbacktest」 | 1/0/0/126 | 紹介(hftbacktest のリポジトリ説明の転載。使用報告ではない。リードが x_fetch で取得 = 生ログ X3) |
| https://x.com/carlcarrie/status/1805040022917124402 | carlcarrie | 2024-06-24T00:47:32Z | 「HftBacktest  A high-frequency trading and market-making backtesting library developed in Python and Rust, that factors in limit orders, queue positions, and latencies - for market-making, #AMM  https://github.com/nkaz001/hftbacktest」 | 135/18/0/10807 | 紹介(hftbacktest のリポジトリ説明の転載。使用報告ではない。リードが x_fetch で取得 = 生ログ X3) |
| https://x.com/ML_deep/status/1917632698077831526 | ML_deep | 2025-04-30T17:30:37Z | 「vectorbt 開発も盛んで有償バージョンはパフォーマンスも改善されてるっぽい。一方でサンプルコードが2度付評価みたいなことしてて厳しさある…。無論、モジュールの使い方の例なのだろうけど、二度漬けしまくりパラメータなんてトレードで使ったら即あの世行きだぞ…。https://vectorbt.pro/#why-vectorbt-pro」 | 7/0/0/2122 | 使用報告(vectorbtの有償版言及+サンプルコードの罠への注意喚起。調査班が x_fetch で取得 = 生ログ X1、リードの取り直し = X1-L) |
| https://x.com/tommy_love123/status/1972317745900585328 | tommy_love123 | 2025-09-28T15:09:29Z | 「【市場が55%下落する中で利益299%？あるYouTube動画が明かした驚異の取引戦略、その核心とは】 freqtrade関連の動画から拾ってきたのですが、スーパートレンド (Supertrend)＋MACD+RSIの組み合わせでDOT（ポルカドット）の無期限先物において、1年間で299%の総利益を達成やり方みたいです。 これがホントであるか、DOT以外でも通用するようなトレード戦略であるかどうかfreqtradeで確認したいと思います。 動画 https://youtu.be/71EA1u4K_Zk?si=aQ_qMEonSE_Urgtb レポート https://docs.google.com/document/d/1mTL48uHM2KqBbxiU1_VjDdrtN32h6Ixbq5fMQEj1r_o/edit?usp=sharing」 | 46/1/0/5166 | 他者の主張の転載(299% は動画の主張、投稿者も未確認。リードが x_fetch で取得 = 生ログ X2) |
| https://x.com/tommy_love123/status/1971429111492227297 | tommy_love123 | 2025-09-26T04:18:22Z | 「【AIエージェント：Codex AI+ｆreqtrade】 もう、とんでもない世界が実現している。 OpenAIのCodexの自律性の能力が向上したので、期待値（リターン、利益率）を上げるためのトレード戦略を自力で考え、それをコード化し、freqtradeコマンドを使って特定の取引所のAPIを叩き、オンライントレードを実施している。 だれが、この世界を想像できただろうか？」(引用元 同著者「freqtrade＋codex aiで自動的にバックテストまでやってくれます。怖いぐらいですね。 自然言語で命令し、ユーザの望みのトレード戦略のロジックまで構築できる。」) | 325/32/1/68290 | 使用報告(Codex + freqtrade で発注まで。区分 6 にも関係。リードが x_fetch で取得 = 生ログ X2) |
| https://x.com/SystematicPeter/status/2024507028820152381 | SystematicPeter | 2026-02-19T15:31:03Z | 「I'm seriously considering moving from my home-made scripts to a more universal framework for backtesting + live trading (especially for intraday). Tested NautilusTrader today and it looks very interesting. Why it caught my attention: - Open source - Event-driven Python API, Rust core (fast) - Biggest win: same strategy codepath for backtest and live (no "version 2" rewrite) - Because it's Python, Claude Code can actually help you ship strategies without coding. I ported my intraday volatility breakout strategy in minutes. Anyone here running NautilusTrader live? What's your experience with brokers/data/execution - any gotchas?」 | 161/7/19/14674 | 使用報告(NautilusTraderへの移行検討・実際にポートした報告。調査班が x_fetch で取得 = 生ログ X1、リードの取り直し = X1-L) |

**発見の語(§3の記録義務)**: `site:x.com hftbacktest OR nautilustrader backtesting queue position`(WebSearch、10件)/ `site:x.com freqtrade OR vectorbt 使ってみた トレード`(WebSearch、10件)。2回のみで3回未満(§3-2は「3回以上」を指示。2 回の記録は生ログ W-16・W-17)。**未実行分は次回に持ち越し**: `site:x.com` での日本語「バックテスト エンジン 自作 やめた」等、別の語での追加検索は本回では未実行。

### STRATEGY_IDEAS.md 向け候補(提案のみ、未マージ)
- (本区分はツールの調査であり、戦略案そのものは出していない。強いて挙げるなら「hftbacktestのqueue position modelを当方のmaker fill参照実装(scripts/qa/maker_fill_ref.py)と突き合わせて、engine.pyの楽観性/悲観性を定量評価する」という**検証タスクの候補**はあるが、これは戦略ではなく検証手法の話なので、DATA.md/STRATEGY_IDEASどちらにも該当しない。リード判断待ち。)

### DATA.md 向け候補(提案のみ、未マージ)
- 無し(本区分はツールの調査であり、データ資産の調達ではない)

---

### 残りの候補名(次回の実行に渡す。浅いまま/未深掘りのもの)

Backtesting.py / zipline-reloaded / QSTrader / Lean CLI / PyAlgoTrade / Zenbot(本家) / Qlib / VnPy /
Jesse / Mendl-Labs/BacktestingCore / Luczinsritter/event_driven_backtesting_engine / Bot18 / ccxt(区分2側で深掘り)

**次回優先すべき項目(浅いまま残った理由と合わせて)**:
1. vectorbt無料版とPROの機能差の逐語裏取り(`become-a-member`と別に、正式なLICENSEファイルと機能比較表ページを直接取得)— 現状は WebFetch の要約止まり(ライセンス文言は推定 = 未検算、W-13。機能差は推定 = 未検算、W-18)
2. freqtradeのbitFlyer非対応の一次資料裏取り(`freqtrade list-exchanges -a`をscratchpad venvで実行するか、CCXT互換表の原文を取得)— 現状は検索結果要約のみ
3. Backtesting.py(AGPL)・PyAlgoTrade(8年更新なし)・zipline-reloaded・QSTrader・Qlib・VnPy・Jesse・Mendl-Labs/BacktestingCore・Luczinsritter/event_driven_backtesting_engine の危険検査(§6-1)・最小実行・4軸評価が未着手
4. hftbacktestの最小実行を「実際に約定(FILLED)を成立させる」ところまで仕上げる(今回はAPI呼び出しの実測どまり)
5. NautilusTraderの実際のpip install・最小実行(未実施)
6. X検索を語を変えて3回以上(§3-2の下限に未達)、awesome系リストと依存関係の逆引きも未着手
7. hftbacktest・NautilusTrader の「国内取引所の記載なし」を README 以外の経路(ソースコードのアダプタ一覧・issue・依存)で裏取り(1 回目は README の要約だけ)
8. NautilusTrader の「自動発注機能あり」をソースで確認(1 回目は README の要約だけ)
9. 生ログに WebFetch / WebSearch を 1 手ずつ残す(1 回目は 24 手すべて書き忘れ、リードが機械抽出で補った)
10. NautilusTrader のライセンス表記の食い違い(PyPI = LGPL-3.0-or-later / README の要約 = LGPL-3.0-only): LICENSE 原文は取得済み(生ログ N2、定型文で決着せず)。README 原文とソースのヘッダで確かめる

### 予算の消費

- 調査班の自己申告(v1)は「実時間 約 20 分相当(推定)」「トークン 5 万に近いと推定」だったが、**ハーネスの計測は 188,843 トークン・650 秒(約 10.8 分)・道具呼び出し 65 回**。トークンは委任文 §7 の固定値(5 万)の 3.8 倍で、自己申告は根拠のない推定だった(自己計測できないと書いたうえで数字を出していた)。時間の自己申告「約 20 分相当」も根拠がない(調査班は時計を持たず、道具呼び出しの回数から推定した、と v1 に書いてあった)。実測 650 秒との乖離は 1.85 倍で、方向はトークンと逆(多く見積もった)。時間は目安 20 分の内側。次回から、トークンも時間も調査班に推定させず、リードがハーネスの計測値を書く。
- **候補の一覧はまだ空になっていない(残りの候補名を参照)。本区分は未完了。次回の実行で持ち越す。**


---

## 区分1 — 2 回目の実行(2026-09-22)

委任文 `docs/DATA/delegations/20260921_tools_survey_prompt.md`(指紋 `20260921_tools_survey_prompt.md@840bf99ca5b0`)§2「2 回目以降の実行」に従い、1 回目の「残りの候補名」12 件(ccxt は区分2の担当なので除外)と「次回優先すべき項目」1〜10 を深掘りする。検索計画6本は1回目のものを打ち直さない。生ログ: `docs/DATA/probes/20260922_tools_1_run2.log`。

### 当方の道具立て(`python3 scripts/tools_inventory.py` の出力全文)

```
# 当方の道具立て(git ls-files から生成。2026-09-22T01:28:30Z、HEAD 60e820c。コマンド: python3 scripts/tools_inventory.py)

## src/bot(package: ファイル数 / ファイル名)
- src/bot: 7 / atomic_file.py constants.py logging_setup.py main.py products.py radar.py settings.py
- src/bot/backtest: 3 / engine.py metrics.py walk_forward.py
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
- build_*: 7 / build_basis.py build_bitflyer_lightchart_csv.py build_burst_library.py build_flow.py build_fx_event_library.py build_fx_event_library_2005_2014.py build_storm_library.py
- check_*: 7 / check_api.py check_data_ledger.py check_k1_binance.py check_k1_bitflyer_data.py check_kabu_api.py check_liquidation_feeds.py check_liquidation_history_depth.py
- record_*: 5 / record_funding_basis.py record_liquidations.py record_oi.py record_realtime.py record_venues.py
- jev/: 3 / client.py redact.py schemas.py
- verify_*: 3 / verify_gates.py verify_liq_instrument.py verify_snapshots.py
- (単発): 2 / _research_audit_gate.py dashboard.py
- judge_*: 2 / judge_board_round.py judge_gates.py
- k1_*: 2 / k1_binance_data_quality.py k1_source.py
- paper_*: 2 / paper_on1.py paper_onr.py
- repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.py
- constants_*: 1 / constants_inventory.py
- data_*: 1 / data_quality.py
- explore_*: 1 / explore_o3c_oi_axis.py
- extract_*: 1 / extract_tape.py
- intake_*: 1 / intake_ledger.py
- liquidation_*: 1 / liquidation_report.py
- mirror_*: 1 / mirror_bitmex_archive.py
- normalize_*: 1 / normalize_bitflyer_executions.py
- phase2_*: 1 / phase2_seal.py
- preflight_*: 1 / preflight_prereg.py
- probe_*: 1 / probe_api_latency.py
- replay_*: 1 / replay_scalp_storm.py
- retention_*: 1 / retention_snapshot.py
- tools_*: 1 / tools_inventory.py
- tp_*: 1 / tp_operating_curve.py
- trace_*: 1 / trace_metrics.py
- validate_*: 1 / validate_composite.py
- x_*: 1 / x_fetch.py
- (.py 以外の scripts: 3 = scripts/fetch_all.sh scripts/install_git_hooks.sh scripts/regen_hook_manifest.sh)

## config: 32
  config/composite.yaml config/config.yaml config/constants.yaml config/etf_measure.yaml config/jev_delegation_tiers.yaml config/jev_design_examples/o3c_covariates.yaml config/jev_design_examples/o3c_observables.yaml config/jev_design_examples/signal2_covariates.yaml config/jev_design_examples/signal2_observables.yaml config/jev_design_examples/signal3_covariates.yaml config/jev_design_examples/signal3_observables.yaml config/jev_design_examples/signal4_covariates.yaml config/jev_design_examples/signal4_observables.yaml config/jev_design_examples/signal5_covariates.yaml config/jev_design_examples/signal5_observables.yaml config/jev_design_examples/signal6_covariates.yaml config/jev_design_examples/signal6_observables.yaml config/jev_design_examples/signal7_observables.yaml config/jev_design_examples/signal8_covariates.yaml config/jev_design_examples/signal8_observables.yaml config/jev_design_examples/signal8_observables_independent.yaml config/jev_design_examples/signal_covariates.yaml config/jev_design_examples/signal_observables.yaml config/jev_routes.yaml config/o3c_jev_state_bands.yaml config/o3c_signal_logit_chain.yaml config/o3c_signal_logit_first.yaml config/o3c_signal_logit_value_chain.yaml config/o3c_signal_logit_value_first.yaml config/on1_live.yaml config/products.yaml config/risk_limits.yaml

## deploy: 19
  deploy/bitflyer-bot.service deploy/bitflyer-fetch.service deploy/bitflyer-fetch.timer deploy/check_liq_recorder.bat deploy/etf_measure_entry.bat deploy/etf_measure_exit.bat deploy/fetch_all.bat deploy/mirror_bitmex.bat deploy/nightly_restart.bat deploy/on1_entry.bat deploy/on1_exit.bat deploy/probe_latency.bat deploy/reset_kill.bat deploy/restart_all.bat deploy/run_paper.bat deploy/setup.sh deploy/share_logs.bat deploy/start_all.bat deploy/stop_all.bat

## tests(ファイル): 139
  tests/conftest.py tests/fixtures/jev_ops/decisions.json tests/fixtures/jev_ops/notifications.jsonl tests/fixtures/jev_ops/status_page.html tests/test_app_fx_integration.py tests/test_audit_gates_wired.py tests/test_backtest.py tests/test_bitmex_mirror.py tests/test_board.py tests/test_board_round.py tests/test_board_walk.py tests/test_bot_research_overnight.py tests/test_build_flow.py tests/test_check_data_ledger.py tests/test_client.py tests/test_clock_burst.py tests/test_composite.py tests/test_constants.py tests/test_constants_inventory.py tests/test_dashboard.py tests/test_data_quality.py tests/test_data_quality_incremental.py tests/test_deploy.py tests/test_engine_maker_exit.py tests/test_etf_measure.py tests/test_extract_tape.py tests/test_fetch_backfill_scripts.py tests/test_fetch_binance_daily.py tests/test_fetch_binance_vision.py tests/test_fetch_history_candles.py tests/test_gz_members.py tests/test_intake_ledger.py tests/test_intent_map_rule.py tests/test_jev_audit_eval.py tests/test_jev_audit_loop.py tests/test_jev_check.py tests/test_jev_client.py tests/test_jev_delegate.py tests/test_jev_design.py tests/test_jev_ideas.py tests/test_jev_ops.py tests/test_jev_owner_log.py tests/test_jev_redact.py tests/test_jev_reply.py tests/test_jev_report_intake.py tests/test_jev_schemas.py tests/test_jev_scripts.py tests/test_jev_survey.py tests/test_jev_trace_export.py tests/test_judge_gates.py tests/test_k1_bitflyer_source.py tests/test_k1_bybit_source.py tests/test_k1_delay_decomp.py tests/test_k1_delay_entry.py tests/test_k1_flip_body.py tests/test_k1_lookahead.py tests/test_k1_no_invalidation.py tests/test_k1_round5.py tests/test_k1_seal_guard.py tests/test_k1_xvenue.py tests/test_liq_bands.py tests/test_liq_response.py tests/test_liq_response_dedup.py tests/test_liquidation_reader.py tests/test_maker_execution.py tests/test_market_data.py tests/test_market_view.py tests/test_max_hold.py tests/test_modes.py tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_ext.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_rows4.py tests/test_o3c_signal_calib.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore2.py tests/test_o3c_signal_explore3.py tests/test_o3c_signal_explore4.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_policy.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_on1_forward.py tests/test_on1_live.py tests/test_onr.py tests/test_onr_forward.py tests/test_orders.py tests/test_paper_state.py tests/test_phase2_p2_01.py tests/test_phase2_p2_01_final.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_phase2_p2_03.py tests/test_phase2_p2_03_final.py tests/test_phase2_p2_03_iter2.py tests/test_phase2_p2_04.py tests/test_phase2_seal.py tests/test_portfolio_and_strategy.py tests/test_position_ladder.py tests/test_preflight_prereg.py tests/test_probe_api_latency.py tests/test_qa_make_known_answer.py tests/test_qa_make_known_answer_maker.py tests/test_qa_make_known_answer_maker3.py tests/test_qa_make_known_answer_steer.py tests/test_qa_maker_fill_ref.py tests/test_qa_pipeline_known_answer.py tests/test_qa_score_audit.py tests/test_radar.py tests/test_realtime_recorder.py tests/test_record_funding_basis.py tests/test_record_liquidations.py tests/test_record_liquidations_writer.py tests/test_record_venues.py tests/test_repair_gz_listing.py tests/test_research_protocol_rules.py tests/test_resilience.py tests/test_retention_snapshot.py tests/test_risk.py tests/test_scalp_logic.py tests/test_sealed_load_diagnostic.py tests/test_sealed_ts_us.py tests/test_short_margin.py tests/test_tp_sl.py tests/test_verify_snapshots.py tests/test_wick_stop.py tests/test_x_fetch.py tests/test_xborder.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_fx.py tests/test_xborder_p2_known_answer.py tests/test_xborder_p2_state.py

## .claude/hooks: 8
  .claude/hooks/_verify_manifest.sh .claude/hooks/delegation_audit_gate.sh .claude/hooks/deny_protected_paths.sh .claude/hooks/jev_notice.sh .claude/hooks/owner_options_gate.sh .claude/hooks/owner_turn_digest.sh .claude/hooks/session_start_digest.sh .claude/hooks/trace_snapshot.sh

## .claude/agents: 3
  .claude/agents/owner-auditor-candidate.md .claude/agents/owner-auditor.md .claude/agents/owner-model-auditor.md

## .claude/skills: 9
  .claude/skills/delegated-study/SKILL.md .claude/skills/owner-audit/SKILL.md .claude/skills/owner-options/SKILL.md .claude/skills/owner-procedure/SKILL.md .claude/skills/research-protocol/SKILL.md .claude/skills/research-squad/SKILL.md .claude/skills/typesafe-ai/LICENSE .claude/skills/typesafe-ai/SKILL.md .claude/skills/x-research/SKILL.md

## githooks: 1
  githooks/pre-push

## docs(.md): 291
  docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11_control_review.md docs/AUDITOR/EVAL_2026-09-11b.md docs/AUDITOR/IMPROVEMENT.md docs/AUDITOR/JEV/LABELS_NOTES_2026-09-19.md docs/AUDITOR/JEV/PREREG_2026-09-19.md docs/AUDITOR/KNOWN_ANSWERS.md docs/AUDITOR/KNOWN_ANSWERS_ADDENDUM.md docs/AUDITOR/OWNER_MODEL_SOURCE.md docs/AUDITOR/PRINCIPLES.md docs/AUDITOR/PROCESS_METRICS.md docs/AUDITOR/PROPOSED_CHANGES_2026-09-11.md docs/AUDITOR/READDO/audit_stop.md docs/AUDITOR/READDO/before_unseal.md docs/AUDITOR/READDO/owner_objection.md docs/AUDITOR/READDO/push_blocked.md docs/AUDITOR/READDO/repeat_defect.md docs/AUDITOR/TREND.md docs/AUDITOR/VERDICTS/2026-09-11_k1_closure_entries.md docs/AUDITOR/VERDICTS/2026-09-11_proposed_changes_and_eval_b.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_execution.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_plan.md docs/AUDITOR/VERDICTS/2026-09-12_o3c_reframe_reading.md docs/AUDITOR/VERDICTS/2026-09-12_p14_liquidation_fix.md docs/AUDITOR/VERDICTS/2026-09-12_p4n_nightly_restart.md docs/AUDITOR/VERDICTS/2026-09-12_rules_reduction.md docs/AUDITOR/VERDICTS/2026-09-16_policy4_report.md docs/AUDITOR/VERDICTS/2026-09-17_anchor_report.md docs/AUDITOR/VERDICTS/2026-09-17_closure.md docs/AUDITOR/VERDICTS/2026-09-17_data_collection.md docs/AUDITOR/VERDICTS/2026-09-17_missing.md docs/AUDITOR/VERDICTS/2026-09-17_oi_distance.md docs/AUDITOR/VERDICTS/2026-09-17_price_level.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_ext.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_full.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_rows4.md docs/AUDITOR/VERDICTS/2026-09-18_oi_distance_split.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_design.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r10.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r2.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r3.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r4.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r5.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r6.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r7.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r8.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r9.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_run12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r11.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_r2_prereg.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r2.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r3.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_result.md docs/AUDITOR/VERDICTS/2026-09-19_signal_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_report.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_materials_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_result.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_design.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_result.md docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md docs/AUDITOR/VERDICTS/2026-09-21_tools_survey_prompt.md docs/AUDITOR/VERDICTS/README.md docs/AUDITOR/answers/KA-01.md docs/AUDITOR/answers/KA-02.md docs/AUDITOR/answers/KA-04.md docs/AUDITOR/answers/KA-05.md docs/AUDITOR/answers/KA-06.md docs/AUDITOR/answers/KA-07.md docs/AUDITOR/answers/KA-08.md docs/AUDITOR/answers/KA-09.md docs/AUDITOR/answers/KA-10.md docs/AUDITOR/answers/KA-16.md docs/AUDITOR/answers/KA-17.md docs/AUDITOR/answers/KA-18.md docs/AUDITOR/answers/KA-19.md docs/AUDITOR/answers/KA-20.md docs/AUDITOR/answers/KA-21.md docs/AUDITOR/answers/KA-22.md docs/AUDITOR/answers/KA-23.md docs/AUDITOR/answers/KA-24.md docs/AUDITOR/answers/KA-25.md docs/AUDITOR/answers/KA-26.md docs/AUDITOR/answers/KA-27.md docs/AUDITOR/answers/KA-28.md docs/AUDITOR/before/HYGIENE_2026-09-11.md docs/AUDITOR/before/KA-01.md docs/AUDITOR/before/KA-02.md docs/AUDITOR/before/KA-04.md docs/AUDITOR/before/KA-05.md docs/AUDITOR/before/KA-06.md docs/AUDITOR/before/KA-07.md docs/AUDITOR/before/KA-08.md docs/AUDITOR/before/KA-09.md docs/AUDITOR/before/KA-10.md docs/AUDITOR/before/KA-16.md docs/AUDITOR/before/KA-17.md docs/AUDITOR/before/KA-18.md docs/AUDITOR/before/KA-19.md docs/AUDITOR/before/KA-20.md docs/AUDITOR/before/KA-21.md docs/AUDITOR/before/KA-22.md docs/AUDITOR/before/KA-23.md docs/AUDITOR/before/KA-24.md docs/AUDITOR/before/KA-25.md docs/AUDITOR/before/KA-26.md docs/AUDITOR/before/KA-27.md docs/AUDITOR/before/KA-28.md docs/DATA.md docs/DATA/SCAN_2026-09-16.md docs/DATA/SCAN_2026-09-21_tools.md docs/DATA/delegations/20260919_o3c_signal_explore2_prompt.md docs/DATA/delegations/20260920_o3c_cascade_read_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_jev_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore3_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore4_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore5_prompt.md docs/DATA/delegations/20260920_o3c_signal_jev_state_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials2_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_stage2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_tp_prompt.md docs/DATA/delegations/20260921_tools_survey_prompt.md docs/DATA/probes/20260913_liquidation_integrity.md docs/DATA/probes/20260919_reaction_prereg_outputs.md docs/DATA/probes/20260920_o3c_cascade_read.md docs/DATA/probes/20260920_o3c_materials_read.md docs/DATA/surveys/BINANCE_CM_MMR_2026-09-17.md docs/DATA/surveys/BITFLYER_HISTORY_SOURCES.md docs/DATA/surveys/ETF_ALTERNATIVES.md docs/DATA/surveys/G2_DATA_INVENTORY.md docs/DATA/surveys/LIQUIDATION_FEED_REACHABILITY.md docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_ACCEPTANCE_2026-09-13.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_A_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_B_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_C_HYPERLIQUID_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_D_VENUE_UNIVERSE_2026-09-12.md docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md docs/DATA_CONSUMPTION_LOG.md docs/DELEGATION.md docs/DISCUSSIONS/2026-09-04_postmortem_tp_precursor.md docs/DISCUSSIONS/2026-09-06_data_dependency.md docs/DISCUSSIONS/2026-09-08_external_ecosystem.md docs/DISCUSSIONS/2026-09-08_matilda_intent_vs_test.md docs/DISCUSSIONS/2026-09-09_prereg_deep_dive.md docs/DISCUSSIONS/2026-09-09_the_day_nothing_shipped.md docs/DISCUSSIONS/2026-09-12_docs_reorg_plan.md docs/DISCUSSIONS/2026-09-12_generation_vs_filtering.md docs/DISCUSSIONS/2026-09-12_rules_inventory.md docs/DISCUSSIONS/2026-09-12_rules_reduction_proposal.md docs/DISCUSSIONS/2026-09-13_root_cause.md docs/DISCUSSIONS/2026-09-13_worst_day.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/PLAN.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/README.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/STAGE0_hook_probe.md docs/DISCUSSIONS/2026-09-16_scope_claim_gate_proposal.md docs/DISCUSSIONS/2026-09-18_jev_trade_integration_decision_for_fable_v2.md docs/DISCUSSIONS/2026-09-19_jev_adoption_review.md docs/DISCUSSIONS/2026-09-19_jev_common_module_review.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/A_judgment_points.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/B_failures.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/C_vendor_sources.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/D_study_notes.md docs/INCIDENTS.md docs/INDEX.md docs/JEV.md docs/NEGATIVE_FACTS.md docs/OPERATIONS.md docs/OPERATIONS_JPX.md docs/OWNER_LOG.md docs/OWNER_PROCEDURES.md docs/OWNER_STATUS.md docs/PHASE2/EXEC/EXEC_FLOOR_PREREG.md docs/PHASE2/EXEC/RESULT.md docs/PHASE2/INSTRUMENT_VERIFY/AUDIT_LEDGER_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-16_policy4.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-17_anchor.md docs/PHASE2/K1/AUDIT_TRIAGE.md docs/PHASE2/K1/BINANCE_PLAN.md docs/PHASE2/K1/DEEPDIVE_PLAN.md docs/PHASE2/K1/FRESH_BITFLYER_PREREG.md docs/PHASE2/K1/H1_PREREG.md docs/PHASE2/K1/H2_PREREG.md docs/PHASE2/K1/H3_DECOMP_PREREG.md docs/PHASE2/K1/H3_PREREG.md docs/PHASE2/K1/HANDOFF.md docs/PHASE2/K1/JUDGEMENT_PREREG.md docs/PHASE2/K1/PREFLIGHT.md docs/PHASE2/K1/PREREG.md docs/PHASE2/K1/RESULT.md docs/PHASE2/K1/ROUND5_PREREG.md docs/PHASE2/K1/XVENUE_PREREG.md docs/PHASE2/K1/binance/CHECKS.md docs/PHASE2/O3C/BRANCH_MAP.md docs/PHASE2/O3C/DATA_AVAILABILITY.md docs/PHASE2/O3C/DATA_COLLECTION_2026-09-17.md docs/PHASE2/O3C/INTENT_MAP.md docs/PHASE2/O3C/MISSING_2026-09-17.md docs/PHASE2/O3C/OWNER_INTENT_2026-09-12.md docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/FULL_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_SPLIT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_DRAFT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_R2_PREREG_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RESULT_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RUN12_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/ROWS4_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/SAMPLE_2026-09-17.md docs/PHASE2/O3C/REFRAME/DIFF_2026-09-12.md docs/PHASE2/O3C/REFRAME/LEAD_READING_2026-09-12.md docs/PHASE2/O3C/REFRAME/data_engineer.md docs/PHASE2/O3C/REFRAME/discretionary_trader.md docs/PHASE2/O3C/REFRAME/liquidation_engine.md docs/PHASE2/O3C/REFRAME/market_maker.md docs/PHASE2/O3C/REFRAME/microstructure.md docs/PHASE2/O3C/SIGNAL/CONTINUE_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/CONTINUE_JEV_RUN_NOTE_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE2_DELEGATE_REPORT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/EXPLORE3_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE4_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE5_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/JEV_STATE_PREVIEW_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS2_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW2_2026-09-19.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW3_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW4_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW5_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW6_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW9_2026-09-21.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_RESULT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE1_REPORT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE2_REPORT_2026-09-21.md docs/PHASE2/O3C/STAGE0A_2026-09-14.md docs/PHASE2/O3C/TRIGGER_TRACE.md docs/PROJECT_GOAL.md docs/STRATEGY_IDEAS.md docs/legacy/KATSUO_INTENT_MAP.md docs/legacy/KATSUO_PARAMETER_INVENTORY.md docs/legacy/README.md

## backtest_data(ディレクトリ数)
  147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H_20260905 audit_fetch_JPX_n225f_months_20260906 audit_fetch_JPX_tick_20260906 audit_fetch_P2-08_docs_20260906 audit_fetch_P2-08b_20260906 audit_fetch_bitflyer_history_20260906 audit_fetch_etf_alternatives_20260906 audit_fetch_etf_units_20260906 audit_fetch_micro_fee_20260906 auto_bitflyer_executions_20260905 auto_bitflyer_executions_20260921 auto_oi_snapshots_20260905 auto_oi_snapshots_20260921 auto_okx_long_short_ratio_20260905 auto_okx_open_interest_1h_20260905 auto_okx_open_interest_1h_20260921 auto_okx_open_interest_5m_20260905 auto_okx_open_interest_5m_20260906 auto_okx_open_interest_5m_20260907 auto_okx_open_interest_5m_20260908 auto_okx_open_interest_5m_20260909 auto_okx_open_interest_5m_20260910 auto_okx_open_interest_5m_20260911 auto_okx_open_interest_5m_20260912 auto_okx_open_interest_5m_20260915 auto_okx_open_interest_5m_20260918 auto_okx_open_interest_5m_20260921 auto_venues_20260905 auto_venues_20260921 binance_BTCUSDT_1m.csv binance_BTCUSDT_1m_20170801_20231231 binance_BTCUSDT_1m_20240101_20260831 binance_BTCUSDT_1m_210d_20260820.csv.gz binance_BTCUSDT_1s_20260723_20260906 binance_BTCUSDT_aggTrades_20260723_20260906 binance_BTCUSDT_aggTrades_tardis_days binance_XRPUSDT_1d.csv binance_XRPUSDT_1m.csv binance_XRPUSDT_4h.csv binance_cm_o3c_20260913 binance_cm_o3c_supp_20260917 binance_um_BTCUSDT_aggTrades_20260723_20260906 bitbank_btc_jpy_transactions_monthly_first_days bitbank_xrp_jpy_1m.csv bitflyer_executions_backfill_20260921 bitflyer_executions_us_20260723_20260906 bitflyer_lightchart_BTC_JPY_1m_20260906 bitflyer_lightchart_FX_BTC_JPY_1m_20260906 bitmex_insurance_20260912 bitmex_trade_1s_XBTUSD board_round_20260904 burst_events_20260820 bybit_BTCUSDT_1m_20260910 bybit_reachability_check_20260906 candles_BTC_JPY_20260820.csv candles_ETH_JPY_20260820.csv candles_FX_BTC_JPY_20260820.csv candles_FX_BTC_JPY_30d_20260820.csv candles_FX_BTC_JPY_31d_20260823.csv.gz candles_XRP_JPY_20260820.csv coinalyze_liquidations_20260921 daily_btcusd_bitstamp_20260828.csv.gz daily_btcusd_coinbase_20260828.csv.gz daily_btcusd_yahoo_20260828.csv.gz daily_ethusd_bitstamp_20260828.csv.gz daily_ethusd_coinbase_20260828.csv.gz daily_ethusd_yahoo_20260828.csv.gz executions_FX_BTC_JPY_31d_20260823.csv.gz executions_FX_BTC_JPY_31d_20260908 flow_FX_BTC_JPY_20260820.csv fred_DEXJPUS.csv fred_DFF.csv fred_DGS2.csv fred_IR3TIB01JPM156N.csv fred_IRSTCI01JPM156N.csv fx_btc_jpy_1m_continuous_20260906 fx_event_ticks_2005_2014 fx_event_ticks_2015_2026 fx_fundamentals_20260822 fx_usdjpy_1m_20170801_20221231 fx_usdjpy_1m_20260822.csv.gz gate_liquidations_20260908 gmo_swap_usdjpy.csv jp_factors_20260905 jpx_daily_report_json_20260908 jpx_etf_daily_20260905 jpx_etf_daily_20260906_topix_alt liquidations_repaired_20260912 liquidations_repaired_20260917 mini_topixf_225labo_20260907 n225f_225labo_20260828 nk225_events_20260904 o3c_oi_distance_20260917 o3c_oi_distance_split_20260918 o3c_price_level_band_20260917 o3c_price_level_bundle_first_20260917 o3c_price_level_full_20260917 o3c_price_level_full_20260917_b005 o3c_price_level_full_20260917_b025 o3c_price_level_full_20260917_w72 o3c_price_level_full_20260917_w8 o3c_price_level_rows4_20260917 o3c_price_level_sample_20260917 o3c_price_level_sample_20260917_limitprice o3c_reaction_20260918_anchor o3c_reaction_20260918_anchor_trades o3c_reaction_20260918_anchor_trades_sample o3c_reaction_20260918_anchor_v1_rawcols o3c_reaction_20260918_full o3c_reaction_20260918_judge o3c_reaction_20260918_sample o3c_reaction_20260918_scale12_judgmentdays o3c_signal_continue_20260920 o3c_signal_explore2_20260919 o3c_signal_explore3_20260920 o3c_signal_explore4_20260920 o3c_signal_explore5_20260920 o3c_signal_explore_20260919 o3c_signal_materials_20260920 o3c_signal_policy_20260920 o3c_signal_value_20260921 okx_20260905 okx_btc_lsratio_1h_20260823.csv okx_btc_lsratio_5m_20260823.csv okx_btc_oi_1h_20260823.csv okx_btc_oi_5m_20260823.csv phase2_runs phase2_sealed qa_known_answer_20260905 qa_known_answer_maker3_20260907 qa_known_answer_maker3_v2_20260905 qa_known_answer_maker3_v3_20260905 qa_known_answer_maker4_20260905 qa_known_answer_maker4_r2_20260905 qa_known_answer_maker_20260905 qa_known_answer_steer_20260905 qa_pipeline_daily_20260905 qa_pipeline_daily_20260906 qa_pipeline_taker_20260905 regime_composite_20260901 reit_onr_20260904 storm_events_20260820 topixf_225labo_20260907 venue_survey_20260827 yutai_20260904
```


### 検索計画(1回目の6本)の扱い

委任文§2の指示どおり、2回目は検索計画6本を打ち直していない。1回目の「残りの候補名」12件(ccxt除く)と「次回優先すべき項目」1〜10を深掘りした。新規発見は§3-2の経路(WebSearch一般 / X / GitHub関連プロジェクト一覧・awesome系・依存関係逆引き)で追加的に行った(下記「新規発見」参照)。

### 候補の一覧(1回目からの引き継ぎ + 新規発見、全部、印つき)

**到達・導入・危険検査まで実施(8 件)。うち最小の実行まで完了したのは 3 件(Backtesting.py・QSTrader・PyAlgoTrade)で、残り 5 件(zipline-reloaded・Lean CLI・Qlib・VnPy・Jesse)は最小の実行が未完了**:
5. Backtesting.py(`backtesting`、kernc） — 実測 — 軽量バックテスト、AGPL-3.0。**指値の1往復に成功**(最小実行)
6. zipline-reloaded(stefan-jansen） — 実測(install・危険検査) + 未完了(最小実行) — Quantopian由来、Apache-2.0
7. QSTrader(mhallsmoore） — 実測 — MIT。**日次の目標配分リバランス型で、指値/板の概念がソースに存在しない**(アーキテクチャ上の限界。最小実行はbuy_and_holdリバランスで成功)
8. Lean CLI(QuantConnect） — 実測(install) + 未完了(最小実行、Docker必須のため) — Apache
9. PyAlgoTrade(gbeced） — 実測 — **指値の1往復に成功**。**2023-11-13にアーカイブ済み、後継として"Basana"を公式に指名**(README逐語で確認)
11. Qlib(`pyqlib`、microsoft） — 実測(install) + 未完了(最小実行、独自バイナリ形式の準備が必要) — MIT。**依存 130 パッケージ**(mlflow/databricks-sdk/pymongo/cvxpy/lightgbm 等を含む巨大な足跡。出力全文から数え直した = 生ログ LV-10。調査班の「185」は数え違い)
12. VnPy(vnpy/vnpy） — 実測(install・コア構成確認) + 未完了(最小実行) — MIT。**コア`vnpy`パッケージにgateway実装・バックテストエンジンは同梱されていない**(alpha/chart/event/traderのみ)。`vnpy_binance`はPyPIに実在(実測)、`vnpy_bitflyer`/`vnpy_bitbank`/`vnpy_gmocoin`はPyPIに存在しない(実測、curl 404)
13. Jesse(jesse-ai） — 実測(install・危険検査 = wheel 展開まで完了・取引所ドライバのソース確認) + 未完了(最小実行、PostgreSQL+Redis要) — MIT(コア)。**取引所ドライバ(ソース実測)= Apex/Binance/Bitfinex/Bybit/Coinbase/Gate/Hyperliquid/Kraken/KuCoin/Lighter。bitFlyer/bitbank/GMOコインは無い**。Apex/Lighter向けの署名用ネイティブバイナリ(zklink_sdk・lighter-signer)を同梱

**一次資料の確認のみで、導入していない(4 件。番号は上の一覧の続き)**:
10. Zenbot(carlos8f、本家) — 一次資料(README) — **2022-02-15にアーカイブ済み**「project is no longer actively maintained」。Node.js+MongoDBで本回は導入未実施(Python環境外・MongoDB要・archived)
14. Mendl-Labs/BacktestingCore — 一次資料(WebFetch要約) — **Functional Source License 1.1**(2年後にApache2.0化。OSI承認のオープンソースライセンスではない)。スター0・フォーク0・18コミットの新規/未検証プロジェクト。Rust製、PyO3でPythonから戦略記述可能を謳う。本回は未導入(PyPI無し、要Rustビルド、低優先)
15. Luczinsritter/event_driven_backtesting_engine — 一次資料(WebFetch要約) — スター0・フォーク0・5コミットの個人/学習用プロジェクト、MIT。本回は未導入(低優先)
16. Bot18(carlos8f、Zenbot作者の別製品) — 一次資料(npmページ本文・GitHub README) — 「$49.99の8桁アンロックコード」「無料お試し(guestチャンネル)は10倍遅く自動売買不可・15分で自動終了」「BETA RELEASE...Live trading is discouraged」の逐語を確認。npm最終公開は約7年前(2019年頃)。本回は未導入(Node.js・古い・低優先)

**カテゴリ越境(区分2で深掘り)**:
17. ccxt — 本回では触っていない(区分2の担当)。ただし freqtrade 経由で ccxt 4.5.82 が導入され、`ccxt.bitflyer().has` を実測(出力 = 生ログ LV-5g): `createOrder=True, cancelOrder=True, fetchOHLCV=None(無), fetchOrder='emulated', fetchTickers=None, watchOHLCV=None`。**bitFlyerは発注・キャンセルはccxt経由で可能だが、ローソク足取得(fetchOHLCV)は無い**(区分2向けの参考情報として記録。深掘りは区分2)

**新規発見(このセッションで新たに見つかった候補。未着手、次回持ち越し)**:
18. Basana — PyAlgoTradeの公式アーカイブ通知が後継として名指し(gbeced/pyalgotrade README、一次資料)。未着手
19. Backtrader — 推定 = 未検算、W-35(X の投稿で言及。逐語はリードが x_fetch で取得 = 生ログ LV-4: pyquantnews 2023-11-21「Backtrader Key strength: Notable for its comprehensive feature set, including support for live trading and visualizations…」)+ awesome 系検索でも言及。未着手
20. PySystemtrade — 推定 = 未検算、W-35(同じ連投「PySystemtrade: Known for its robustness and modularity…」逐語 = 生ログ LV-4)。未着手
21. PyBroker — 推定 = 未検算、W-35(同じ連投「PyBroker Emphasizes simplicity and user-friendliness for beginners…」逐語 = 生ログ LV-4)。未着手
22. bt — 推定 = 未検算、W-35(同じ連投「bt Strength lies in its focus on providing a simple, lightweight, and intuitive API…」逐語 = 生ログ LV-4。パッケージ名が短く曖昧、要確認)。未着手
23. Ziplime — 推定 = 未検算、W-35(quantscience_ 2026-03-10 の逐語「🚨BREAKING: New Python Library for Algorithmic Trading with AI It's called Ziplime (*not* Zipline).」= 生ログ LV-4)。未着手
24. Superalgos — awesome系検索で発見、ノーコード・Apache-2.0と検索結果に。未着手
25. OpenTrader — awesome系検索で発見、TypeScript製・CCXT経由100+取引所と検索結果に。未着手
26. CryptoSignal — awesome系検索で発見。未着手
27. fast-trade — awesome系検索で発見、pandas+テクニカル指標ベースと検索結果に。未着手
28. OctoBot — awesome系検索で発見、月額$9.99のクラウド版ありと検索結果に(料金の逐語未確認)。未着手
29. pybotters — WebSearchの要約でNautilusTraderの文脈に誤って混在して言及されたが、実体は別プロジェクト(日本の取引所APIクライアント、区分2寄り)。未着手、区分2にも共有推奨

**未実行(検索計画6本には無いが、今回の深掘り過程で見つかった追加調査対象)**: 上記18〜29はいずれも一次資料への到達(PyPI/GitHub)を今回は行っていない。検索結果の見出し・要約のみ(推定 = 未検算、W-35・W-36。X の投稿の逐語はリードが取得 = 生ログ LV-4)。

### 1回目「次回優先すべき項目」1〜10の結果

| # | 項目 | 結果 |
|---|---|---|
| 1 | vectorbt無料版とPROの機能差の逐語裏取り | **解決**。LICENSE.md原文をraw.githubusercontentからcurl取得(一次資料、200、生ログ)= "Commons Clause"付きApache2.0(Sellの禁止を定義)。無料版のソース全体を`grep -rl -i "limit_order\|LimitOrder\|order_type.*Limit"`で検索し**0件**(実測)。無料版のソースに指値注文という概念自体が存在しないことを確認(PROページの「Limit orders」がPRO限定機能である根拠が、検索結果の要約からソース実測に格上げされた) |
| 2 | freqtradeのbitFlyer非対応の一次資料裏取り | **解決**。隔離venvにfreqtrade導入(ccxt 4.5.82同梱)、`freqtrade list-exchanges -a`を実測: bitFlyer行「missing: fetchOrder, fetchOHLCV」(必須欠落。表の実物 = 生ログ LV-5f)。`freqtrade list-exchanges`(非-a、使える79取引所)にbitFlyerは含まれずbitbankは含まれる(bitbankは「missing opt」のみで必須機能は揃っている)。ccxtの`bitflyer().has`を直接実測: createOrder/cancelOrder=True、fetchOHLCV/fetchTickers/watchOHLCV=None、fetchOrder='emulated' |
| 3 | 9候補(Backtesting.py・PyAlgoTrade・zipline-reloaded・QSTrader・Qlib・VnPy・Jesse・Mendl-Labs/BacktestingCore・Luczinsritter。1 回目の項目 3 の 9 件をそのまま指す。Lean CLI・Zenbot・Bot18 は 1 回目のこの項目には入っていないが、Lean CLI だけは今回まとめて扱ったので結果の欄に含めた)の危険検査・最小実行・4軸 | **部分的に解決**。Backtesting.py・QSTrader・PyAlgoTrade = 危険検査+最小実行+4軸まで完了。zipline-reloaded・Qlib・VnPy・Jesse・Lean CLI = 導入+危険検査(依存一覧・wheel展開確認)まで完了、最小実行は各ツール固有の準備(データバンドル登録/独自バイナリ形式/GUI依存/DB要求/Docker要求)のため次回に持ち越し。Mendl-Labs/BacktestingCore・Luczinsritter = GitHub一次資料の確認のみ(PyPI無し、低優先のため未導入) |
| 4 | hftbacktestの最小実行を「実際に約定(FILLED)」まで仕上げる | **解決(ただし結果を確認したのはリード)**。event_dtype(ev/exch_ts/local_ts/px/qty/order_id/ival/fval)を一次資料(ソース`types.py`)から読み取り、DEPTH_SNAPSHOT_EVENT→TRADE_EVENTの合成データを再構築。指値買い@100.0が売り約定の消化でstatus=3(FILLED)、exec_qty=1.0、leaves_qty=0.0。**調査班は v4 で失敗(rc=1)したあと v5 を背景で起動しただけで出力を読んでいない。リードが打ち直して上の値を再現した(生ログ LV-2・LV-6)。**成行手仕舞いも成功、num_trades=2 |
| 5 | NautilusTraderの実際のpip install・最小実行 | **解決**。Python3.12の隔離venvに導入(14依存のみ、軽量)。`nautilus_trader.testkit`は現行リリースに存在せず(developブランチの例が不一致)、`test_kit`(アンダースコア)を使用。BTCUSDT/BINANCEの合成足データでLIMIT買い→FILLED→MARKET売りの1往復が成立(**リードの打ち直しで確認 = 生ログ LV-7**。調査班は背景で起動しただけで出力を読んでいない) |
| 6 | X検索3回以上・awesome系リスト・依存関係逆引き | **解決**。今回のX関連WebSearchは3回(バックテストエンジン自作/乗り換え、backtesting.py OR zipline OR nautilus trader、+round1の2回で計5回)。awesome系リスト検索1回(新規候補9件発見)。依存関係逆引きはGitHubのdependents機能でBacktesting.pyを確認(0件、ただしGitHubの依存関係グラフ自体が網羅的でない旨の注記あり) |
| 7 | hftbacktest・NautilusTraderの国内取引所記載なしをソース/issue/依存で裏取り | **解決(NautilusTraderは完全、hftbacktestは複数独立ソースで補強)**。NautilusTrader: `crates/adapters`ディレクトリの実際の一覧(実測、WebFetch)= architect_ax/betfair/binance/bitmex/blockchain/bybit/coinbase/databento/deribit/derive/dydx/hyperliquid/interactive_brokers/kraken/lighter/okx/polymarket/sandbox/tardisの19件、bitFlyer等無し。RELEASES.md(567,723バイト、curl実測)にbitflyer/bitbank/gmoの一致0件(grep)。hftbacktest: `rust/src/live/connector`等のディレクトリパスがいずれも404(到達不能)だったため、README一次資料に加えWebSearchの独立した要約(2件)で「Binance FuturesとBybitのみ」を補強したが、ソースディレクトリそのものの実測はできていない(未確認) |
| 8 | NautilusTraderの自動発注機能をソースで確認 | **解決(ただし実行したのはリード)**。README記載の確認に留めず、LIMIT注文とMARKET注文を`OrderMatchingEngine(BINANCE)`に送信して約定させる試行が行われたが、**調査班は背景で起動しただけで出力を読んでいない。リードが打ち直して約定 2 件を確認した(生ログ LV-7)**。発注機能が実在し動作することをリードの打ち直しで確認 |
| 9 | 生ログにWebFetch/WebSearchを1手ずつ残す | **解決**。本回は`docs/DATA/probes/20260922_tools_1_run2.log`にWebFetch/WebSearch/curl/pip/pythonの全手順を都度追記した |
| 10 | NautilusTraderのライセンス表記の食い違い | **解決(食い違いを確定)**。README.md原文(develop、curl実測、200)に「cargo-deny enforces a license allow list compatible with LGPL-3.0-only」「available...under the GNU Lesser General Public License v3.0」と明記。**PyPI JSONのlicense_expression(LGPL-3.0-or-later)と食い違う**。LICENSE.txtファイル自体はLGPLv3の定型文(v3/v3以降どちらにも使われる共通本文)で決着しない。原因(パッケージングミスか意図的併記か)は未確認 |

### 出典(2 回目。委任文 §11 の必須項目。1 回目は独立の表があったが 2 回目は各ツールの欄に分散していたので、監査 8 回目の指摘 2 を受けてここに集めた。URL は生ログ `docs/DATA/probes/20260922_tools_1_run2.log` から機械で抽出。取得日はいずれも 2026-09-22)

| 種別 | URL | 方法 |
|---|---|---|
| PyPI JSON(取得できた 9 件) | `pypi.org/pypi/{backtesting,QSTrader,pyalgotrade,zipline-reloaded,lean,pyqlib,vnpy,jesse,vnpy_binance}/json` | curl(200) |
| PyPI JSON(404 = そのパッケージが PyPI に無い、3 件) | `pypi.org/pypi/{bot18,backtestingcore,event-driven-backtesting-engine}/json` | curl(404。生ログ 19〜24 行) |
| PyPI JSON(国内取引所の gateway) | `pypi.org/pypi/{vnpy_bitflyer,vnpy_bitbank,vnpy_gmocoin}/json` | curl(3 件とも 404 = そのパッケージが存在しない) |
| GitHub ページ | `github.com/{kernc/backtesting.py, mhallsmoore/qstrader, gbeced/pyalgotrade, stefan-jansen/zipline-reloaded, QuantConnect/lean-cli, carlos8f/zenbot, carlos8f/bot18, microsoft/qlib, vnpy/vnpy, jesse-ai/jesse, Mendl-Labs/BacktestingCore, Luczinsritter/event_driven_backtesting_engine, nautechsystems/nautilus_trader}` | WebFetch |
| GitHub のディレクトリ一覧 | `nautechsystems/nautilus_trader/tree/develop/crates/adapters` ほか / `nkaz001/hftbacktest/tree/master/{rust/src/live/connector, hftbacktest/src/connector, hftbacktest-rs/src/live}`(3 つとも 404) | WebFetch |
| 原文(raw) | `raw.githubusercontent.com/nautechsystems/nautilus_trader/develop/{LICENSE, README.md, pyproject.toml, examples/backtest/example_01.py}` / `polakowo/vectorbt/master/LICENSE.md` / `mhallsmoore/qstrader/master/examples/buy_and_hold_backtest.py` | curl |
| 文書 | `hftbacktest.readthedocs.io/en/latest/tutorials/Working with Market Depth and Trades.html` / `vectorbt.pro/` | WebFetch / curl |
| X の投稿(検索で出た URL。本文の取得はリードが x_fetch で実施 = 生ログ LV-4) | `x.com/{pyquantnews(3 件), quantscience_, GitHubGPT, QuantInsti}` | WebSearch → x_fetch |
| 検索 | 生ログ LV-1 の W-1〜W-37 のうち WebSearch の分(10 件) | WebSearch |

**到達できなかった経路とその処置(2 回目)**: hftbacktest のソースの connector ディレクトリは 3 つの綴りとも 404(`rust/src/live/connector`・`hftbacktest/src/connector`・`hftbacktest-rs/src/live`)。README 以外の経路でライブ接続先を確かめる試みはここで止まり、**「ソースの直接の列挙は未達」と本文に書いた**(委任文 §5-1 の「全部試すまで不可と書かない」に従い、代わりに複数の独立した記述で補強した)。`pypi.org/pypi/vnpy_{bitflyer,bitbank,gmocoin}/json` の 404 は「そのパッケージが存在しない」という実測で、到達の失敗ではない。

### 知見(2 回目。委任文 §11 の必須項目。監査 8 回目の指摘 1 を受けて追加。印は本文の各節と同じ根拠に基づく)

| 知見 | 印 | このプロジェクトへの含意 |
|---|---|---|
| `vectorbt` の無料版には**指値注文の概念そのものがソースに無い**(パッケージ全体の grep で一致 0 件) | 実測(生ログ、隔離 venv での grep) | 当方の戦略は指値の約定を測るものなので、無料版のままでは当方の用途に届かない。PRO の機能差の逐語は次回 |
| `freqtrade` は bitFlyer を「必須機能の欠落(fetchOrder・fetchOHLCV)」として使えない側に置き、**bitbank は使える側の 79 取引所に入っている** | 実測(`freqtrade list-exchanges -a` と非 -a、生ログ LV-5f。1 回目の「国内 3 社の記載なし」の訂正) | 国内取引所の対応は「記載の有無」ではなく取引所ごとの機能表で決まる。当方が bitFlyer を使う限り freqtrade の執行部は使えない |
| `ccxt` の bitflyer は `createOrder`・`cancelOrder` は真だが `fetchOHLCV` が無い | 実測(生ログ LV-5g) | 足データは自前で持つ必要がある(当方は既に持っている) |
| `PyAlgoTrade` は 2023-11-13 にアーカイブ済みで、**公式に後継 Basana を名指し**している | 一次資料(GitHub のアーカイブ表示と README の逐語、W-5。**取得結果の全文を生ログ LV-9 に載せて、日付と Basana の逐語が調査班の取得に実在することを確かめた**) | 候補 18(Basana)はここから出た。古い候補を追うより後継を見る |
| `Zenbot`(本家)は 2022-02-15 にアーカイブ済み | 一次資料(GitHub のアーカイブ表示の逐語、リードが取り直し = 生ログ LV-3) | 実質的に終了。Node.js + MongoDB で当方の環境とも離れている |
| `QSTrader` は日次の目標配分リバランス型で、**指値・板・待ち行列の概念がソースに無い** | 実測(モジュール一覧、生ログ LV-5a) | 当方の用途(秒単位・指値の約定)とは設計が違う |
| 1 つの venv に複数のツールを入れると依存が壊れる(Jesse の導入後に numpy が 1.26.4 になり、pip が 5 件の numpy 要求との衝突を警告 = 生ログ LV-10。「2.x から落とした」は ERROR 行からの推定で明示の記録は無い。vectorbt は最新の plotly では import 自体が失敗) | 実測(生ログ) | ツールごとに隔離した環境で試すのが前提。当方のリポジトリ環境には入れない(委任文 §5-2 のとおり) |
| `Mendl-Labs/BacktestingCore` は Functional Source License 1.1(2 年後に Apache 2.0 化)で、OSI 承認のオープンソースではない | 一次資料(GitHub、W-9) | 「無料」と「オープンソース」は別。取り込む前にライセンスの条件を読む必要がある |
| `hftbacktest` は指値が実際に約定するところまで動く(status=3・exec_qty=1.0・往復 2 件) | 実測(**リードの打ち直し** = 生ログ LV-2) | 当方の `engine.py` に無い待ち行列の模擬を、動く実装として参照できる |
| `NautilusTrader` は指値約定と成行手仕舞いの 1 往復が動く(残高 USDT が費用分だけ減る) | 実測(**リードの打ち直し** = 生ログ LV-7) | 執行の枠組み(区分 2)の候補として、動作の裏づけがある |

### ツール1件ごとの表(2回目、12候補すべて。`#### 5.`〜`#### 16.` の 12 件)

**この節の全 12 件に共通する未確認(監査 1 回目の指摘 10。委任文 §6-1 が挙げる検査項目のうち、本回で埋まっていないもの)**: **(12 件すべてで欠けていた 2 項目)** 週のダウンロード数 = **未確認**(pypistats を叩いていない。1 回目は hftbacktest・NautilusTrader で叩いた)/ 保守者の数と名前の一貫性 = **未確認**(PyPI の author と GitHub の所有者を突き合わせていない)/ **(欠けていたのは 1 件だけ)** 既知の脆弱性の公開勧告 = **未確認**(検索していない)。ただしこれを書き落としていたのは **QSTrader の 1 件だけ**で、残り 11 件は個別の「危険」欄に「既知の脆弱性: 未確認」を持っている(数え直した。監査 5 回目の指摘 2)。QSTrader の欄にも同じ記載を足した。**この一括注記が全件に効き、個別欄はその再掲である。**

**導入前の検査と導入の順序(監査 1 回目の問い 11 への答え)**: ハーネスの記録で手番を数えると、`pip download`(手 34)→ **wheel の展開と `.so`・導入時実行コードの検査(手 35)** → `pip install`(手 37 以降)の順で、**検査が導入より先**だった(生ログ LV-5h)。委任文 §6-1「導入前の検査」は順序としては守られている。ただし各ツールの「危険」欄が「wheel展開は本回未実施」と書いていたのは誤りで、展開は全 wheel を一括で行っていた(本文のその記述は上で直した)。

#### 5. Backtesting.py

- **名前/種別**: backtesting(PyPI) / kernc/backtesting.py(GitHub) — 軽量なイベント駆動(1バー単位)バックテストライブラリ
- **できること全部**: PyPI descriptionの冒頭「Backtest trading strategies with Python」。GitHub要約(WebFetch): OHLC(V)ローソク足データがあれば任意の金融商品でバックテスト可能、成行・指値(`self.buy(limit=...)`)注文をサポート(実測: 本回のスクリプトで指値注文が実際に約定した)
- **言語・動作環境**: Python>=3.9(一次資料 PyPI requires_python)
- **ライセンス**: AGPL-3.0(一次資料 PyPI classifier「GNU Affero General Public License v3 or later (AGPLv3+)」)。強いコピーレフト、ネットワーク経由の利用でもソース開示義務が生じうる
- **版と最終更新日**: 0.6.6、2026-07-22(一次資料PyPI JSON)
- **活動**: スター9,000・フォーク1,500・コミット461件(WebFetch要約、GitHub)。依存グラフ上の依存プロジェクト0件(WebFetch、github.com/kernc/backtesting.py/network/dependents。ただしGitHubの依存関係グラフ自体が全ての利用を捕捉しない旨の注記あり=未確認の限界)
- **対応取引所**: 取引所非依存(OHLCVデータを渡せば動く汎用設計。個別取引所コネクタは無い、一次資料に明記なし)
- **出典**: pypi.org/pypi/backtesting/json、github.com/kernc/backtesting.py(いずれも2026-09-22取得)

**料金の構造**: 一次資料に料金記載なし。完全無料(AGPL-3.0)。隠れた依存: 導入時に追加パッケージのダウンロードは無かった(実測、隔離venvに既存のnumpy/pandas/bokehで足りた)。当方の用途で課金が発生する要素は見当たらない(未確認: 456日規模データでの実行時間/メモリは本回は未計測)

**到達・導入・実行の記録**:
- `pip install backtesting`(隔離venv `venv_tools1`、rc=0、実測)。`pip check` → No broken requirements found(実測)
- 危険検査(§6-1): wheelを展開し`setup.py`等の導入時実行コードの有無を確認 → **無し**(pure-Pythonのwheel、実測 = 生ログ LV-5b)。PyPI Project-URLとGitHubの一致確認(一次資料)。既知の脆弱性: 未確認(未実施)
- **最小の実行**: 合成OHLC(200本、ランダムウォーク)を生成し、`Strategy.next()`で現在値の0.5%下に1回だけ指値買いを送信、約定後に成行で手仕舞う戦略を実行 → **成功**。`# Trades: 1`、`EntryPrice=98.80`、`ExitPrice=97.81`、`PnL=-11.95`(実測、rc=0。出力全文 = 生ログ LV-5d。生ログ 63 行の head200 は列名の途中で切れている)。**指値の1往復が正しく約定・記録されることを確認した数少ない候補の一つ**
- 所要時間: install 1.07 秒・実行 0.84 秒(生ログの time_s)

**当方の用途との相性**: pandas.DataFrame(OHLCV+DatetimeIndex)を要求 — 当方のcsv.gz約定履歴は変換層が必要(推定)。時刻はpandas Timestampでタイムゾーン任意(実測で確認、UTCで問題なく動作)。再現性: 合成データに乱数シードを使えば決定的(実測)。規模: 200本で1秒未満(実測)。456日ティック相当への外挿は次回課題(推定不可、実測データなし)

**当方に無いもの(一次資料の逐語で)**: GitHub要約「supports any financial instrument with OHLC(V) candlestick data」(汎用性は当方の`engine.py`にもあるが、Backtesting.pyは1バー1回の指値判定+`limit`パラメータでの単純な指値サポートを持つ軽量API)。組み込みの最適化機能(`bt.optimize()`、W節参照は未確認、次回)

**4軸**:
1. 道具として入れるか: 実測 — pip一発、既存依存で動作、pip check通過
2. 当方に無い情報が取れるか: 実測(限定的) — 指値注文の1バー判定という当方の`engine.py`とは異なる実装を確認したが、待ち行列位置は無い(GitHub要約に明記なし、§8のA自体は解決しない)
3. 当方に無い視点で分析できるか: 推定 — 軽量・高速なAPIで反復実験がしやすい設計思想
4. 既存の研究成果を向上できるか: 仮定 — 軽量な代替/検算ツールとして使える可能性、未検証

**危険**: 供給網: PyPI/GitHub一致(実測)。導入時実行: **無し**(wheel を展開して確認 = 生ログ LV-8。`setup.py` 相当 0 件・`.so` 0 件)。既知の脆弱性: 未確認。外部送信: 無し(一次資料にテレメトリ記載なし)。自動発注: 無し(バックテスト専用、発注APIへの接続機能は無い)。宣伝・詐欺の兆候: 無し(公式OSS)。**AGPL-3.0であることが唯一の実務上の注意点**(当方が改変して社内利用する分にはAGPLの配布条項は問題にならないことが多いが、外部提供する場合は要確認、法務判断はリード/オーナー)

#### 7. QSTrader

- **名前/種別**: qstrader(PyPI) / mhallsmoore/qstrader — 日次・スケジュール駆動型の長短エクイティ/ETFバックテストフレームワーク
- **できること全部**: PyPI description逐語「a free Python-based open-source modular schedule-driven backtesting framework for long-short equities and ETF based systematic trading strategies」「loosely-coupled collection of modules for carrying out end-to-end backtests with realistic trading mechanics」
- **言語・動作環境**: Python>=3.9(一次資料)
- **ライセンス**: MIT(一次資料PyPI classifier)
- **版と最終更新日**: 0.3.0、2024-06-24(一次資料。約2年更新なし)
- **活動**: スター3.5k・フォーク930・コミット431件(WebFetch要約)
- **対応取引所**: 実装確認(実測、`import qstrader; os.listdir` = 生ログ LV-5a) — サブモジュールは`alpha_model/risk_model/asset/trading/exchange/broker/signals/data/system/portcon/simulation/utils/execution`。個別取引所コネクタは無く、CSV日次バーのローカル読み込みが標準(`CSVDailyBarDataSource`、GitHub公式example実測で確認)
- **出典**: pypi.org/pypi/QSTrader/json、github.com/mhallsmoore/qstrader、raw.githubusercontent.com/.../examples/buy_and_hold.py(いずれも実測取得)

**料金の構造**: 完全無料(MIT)。隠れた依存: `click`・`seaborn`が新規導入された(実測、pip install出力)。当方の用途での課金要素は無し

**到達・導入・実行の記録**:
- `pip install qstrader`(隔離venv、rc=0、実測)。GitHub公式example `examples/buy_and_hold.py`をraw.githubusercontentからcurl取得(200、実測)し、その構造(`FixedSignalsAlphaModel`+`BacktestTradingSession(rebalance='buy_and_hold')`)をそのまま踏襲した合成CSV日次バー(260営業日のランダムウォーク)で実行
- **最小の実行**: 成功(rc=0)。`equity curve rows=261, first={'Equity': 1000000.0}, last={'Equity': 698485.43}`(実測)。**ただし本ツールは「日次リバランス配分」のシミュレータであり、指値注文・板・待ち行列という概念がソースのどこにも存在しない**(モジュール一覧の実測から確認 = 生ログ LV-5a)。**§5-4が求める「成行と指値の1往復」に相当する処理はこのアーキテクチャでは成立しない** — 目標配分(この場合100%配分のbuy_and_hold)への一括発注のみ
- 所要時間: install 1.62 秒(生ログの time_s。「十数秒」は誤り)。**これは qstrader 本体だけの時間で、公式の例を動かすには別に `pip install pytz` 1.11 秒が要った**(生ログ 68 行。pytz は qstrader の宣言依存に入っておらず、例のスクリプト側の要件。監査 11 回目の問い 3 への答え)

**当方の用途との相性**: 日次バーのCSV(`Date`列+OHLCV)を要求(実測、公式exampleのコード)。当方の分足・ティック・清算といった高頻度データとは粒度が大きく異なる(推定: 高頻度戦略の検証には不向き)。時刻: UTCタイムゾーン付きpandas Timestamp(実測)。再現性: 決定的(合成データに乱数シード使用、実測)。規模: 260日で1秒未満(実測)、456日ティック相当への外挿は不可(日次専用のため単位が異なる)

**当方に無いもの(一次資料の逐語で)**: PyPI description「schedule-driven」というアーキテクチャそのもの(当方の`engine.py`はバー単位の逐次処理で、スケジュール駆動のリバランス計画という概念は無い)。`TearsheetStatistics`によるパフォーマンスレポート機構(当方の`monitoring/`には無い形式)

**4軸**:
1. 道具として入れるか: 実測 — pip一発、既存example改変でそのまま動作確認
2. 当方に無い情報が取れるか: 仮定 — 日次配分リバランスという別カテゴリの手法であり、当方のCFDスキャルピング/日中戦略への直接適用は困難(未検証)
3. 当方に無い視点で分析できるか: 一次資料+推定 — スケジュール駆動という設計思想自体は当方に無いが、適用可能性は未検証
4. 既存の研究成果を向上できるか: 仮定 — 現状の当方の研究方向(高頻度・CFD)とは単位が異なり、向上に直結するかは不明

**危険**: 供給網: PyPI/GitHub一致(実測、project_urls)。導入時実行: **無し**(wheel を展開して確認 = 生ログ LV-8。`setup.py` 相当 0 件・`.so` 0 件)。既知の脆弱性: 未確認。外部送信: 未確認。自動発注: 無し(バックテスト専用)。宣伝の兆候: 無し

#### 9. PyAlgoTrade

- **名前/種別**: PyAlgoTrade(PyPI) / gbeced/pyalgotrade — 株式バックテスト用Pythonライブラリ
- **できること全部**: PyPI description「Python library for backtesting stock trading strategies」(56文字のみ、詳細はREADME側)。GitHub README(WebFetch要約)で確認した重要事実: **リポジトリは2023-11-13にアーカイブ済み**「This repository was archived by the owner on Nov 13, 2023. It is now read-only」、明示的な廃止通知「This project is deprecated and is no longer mantained. You may be interested in taking a look at Basana」(後継として"Basana"を公式指名)
- **言語・動作環境**: 一次資料に`requires_python`指定なし。実測: Python3.11で`pip install`が成功し(sdistからビルド)、実際に動作した(古いバージョン表記に反して現行Pythonで動く)
- **ライセンス**: 一次資料(PyPI)に空欄(未確認、classifiers無し)
- **版と最終更新日**: 0.20、2018-08-21(一次資料。8年更新なし)
- **活動**: スター4.7k・フォーク1.4k・コミット1,158件(WebFetch要約)、アーカイブ済み(実測)
- **対応取引所**: 個別取引所コネクタなし、CSVベースの汎用バーフィード(実測、`csvfeed.GenericBarFeed`)
- **出典**: pypi.org/pypi/pyalgotrade/json、github.com/gbeced/pyalgotrade(いずれも実測取得)

**料金の構造**: 完全無料。隠れた依存: `scipy`・`tweepy`(Twitter連携用、恐らくXシグナル機能)・`ws4py`・`oauthlib`等が導入された(実測、pip install出力)。tweepyの存在は「Xの投稿をシグナルに使う」機能が本体にある可能性を示唆(未確認、次回裏取り課題)

**到達・導入・実行の記録**:
- `pip install pyalgotrade`(隔離venv、rc=0、実測。sdistからビルド成功、8年前のリリースだが現行Python 3.11で問題なく動作)
- `pip check` は本回未実施(次回課題)
- **最小の実行**: 成功。合成日次CSV(100本、`Date Time`列必須・特定のdatetimeフォーマット必須という実装依存の癖を実測で発見)で、`limitOrder()`により現在値0.5%下の指値買いを送信 → 約定 → `marketOrder()`で手仕舞い。`RESULT: final_portfolio_value=1004.46, shares=0, cash=1004.46`(実測、rc=0)。**指値の1往復に成功した2件目の候補**
- 所要時間: install 10.23 秒(生ログの time_s)

**当方の用途との相性**: CSV(`Date Time`列、`%Y-%m-%d %H:%M:%S`形式必須)を要求(実測で判明、当方のUTCミリ秒ティックとは変換が必要)。再現性: 決定的(実測)。規模: 100本で1秒未満、456日ティック規模は未計測

**当方に無いもの(一次資料の逐語で)**: GitHub要約に「optimizer」(パラメータ最適化)への言及があるが本回は未検証(次回)。tweepy依存から示唆される「Xの投稿をシグナルに取り込む」機能(未確認、推測の域を出ない)

**4軸**:
1. 道具として入れるか: 実測(ただし**アーカイブ済み**という重大な留保つき) — pipインストール・実行は現行環境でも動作するが、今後の脆弱性修正・Python新版対応は無い
2. 当方に無い情報が取れるか: 未確認
3. 当方に無い視点で分析できるか: 未確認
4. 既存の研究成果を向上できるか: 仮定 — アーカイブ済みのため新規採用の価値は低いと考えられるが判定はしない。後継のBasanaが本命候補(次回)

**危険**: 供給網: PyPI/GitHub一致(実測、project_urls)。導入時実行: 未確認(**PyAlgoTrade だけは sdist なので wheel の展開の対象外**。sdistなのでビルド時にsetup.pyが実行される点は一般的なPythonパッケージと同じ、悪意ある記述の有無は未確認)。既知の脆弱性: 未確認(8年間パッチが無い、依存のscipy/tweepy側の脆弱性も未確認)。外部送信: **tweepy依存はTwitter API連携を示唆し、鍵を渡せば外部送信が発生しうる構造**(未確認、使わなければ発火しない)。自動発注: ソースは未確認だがbroker抽象化層が存在(GitHub要約)。宣伝の兆候: 無し。**アーカイブ済み・8年間未更新という活動状況そのものが今後の使用における主要なリスク**

#### 6. zipline-reloaded

- **名前/種別**: zipline-reloaded(PyPI) / stefan-jansen/zipline-reloaded — Quantopian由来のPythonicイベント駆動バックテスタ
- **できること全部**: PyPI description逐語「A Pythonic backtester for trading algorithms」「a Pythonic event-driven system for backtesting」。ヒストリカルデータの取り込みには「bundle」という登録済みデータ供給元の概念が必須(実測で判明、後述)
- **言語・動作環境**: Python>=3.10(一次資料)
- **ライセンス**: Apache-2.0(一次資料PyPI `license_expression`)
- **版と最終更新日**: 3.1.1、2025-07-19(一次資料。1年以上更新なし)
- **活動**: スター1.9k・フォーク330・コミット6,694件(WebFetch要約)
- **対応取引所**: 一次資料に個別取引所の記載なし。NASDAQ Data Link(旧Quandl)のAPIキーが必要な旨を GitHub の要約が示す(推定 = 未検算、W-6)
- **出典**: pypi.org/pypi/zipline-reloaded/json、github.com/stefan-jansen/zipline-reloaded

**料金の構造**: 本体無料(Apache-2.0)。NASDAQ Data Linkのヒストリカルデータ取得にはAPIキーが必要と要約にあり(推定 = 未検算、W-6。無料枠の有無は未確認)。隠れた依存: 導入で **42 個**の新規パッケージ(出力全文 = 生ログ LV-10)(exchange-calendars・bcolz-zipline・empyrical-reloaded・statsmodels・SQLAlchemy・tables/h5py・Mako/alembic等)が入り、**既存venvのpandasを3.0.6から2.3.3へ強制ダウングレードした**(実測、pip installの出力に明記)

**到達・導入・実行の記録**:
- `pip install zipline-reloaded`(隔離venv、rc=0、実測)。`pip check` → No broken requirements found(実測)
- **最小の実行**: **未完了**。zipline-reloadedのバックテストAPI(`run_algorithm`)は「bundle」という事前登録されたデータ供給元(通常はCLIで`zipline ingest`を実行してローカルにデータを取り込む)を前提としており、DataFrameを直接渡す単純な経路が見当たらなかった(試したこと: `run_algorithm`のシグネチャ確認、bundle登録の要否を確認。合成データでのbundle登録スクリプトの作成は本回の予算内で完了しなかった)。「取れない」のではなく「bundle登録という追加の準備工程が必要」という状態
- 所要時間: install 31.87 秒(生ログの time_s)

**当方の用途との相性**: 未確認(最小実行が未完了のため)

**当方に無いもの(一次資料の逐語で)**: `empyrical-reloaded`(リスク指標計算ライブラリ、Sharpe/Sortino等の標準実装)が依存に含まれる — 当方の`src/bot/backtest/metrics.py`との重複/補完関係は次回要確認

**4軸**: 1=実測(導入成功・pip check通過) / 2〜4=未確認(最小実行未完了のため測れず)

**危険**: 供給網: PyPI project_urlsとGitHubの一致(一次資料)。導入時実行: **無し**(wheel を展開して確認 = 生ログ LV-8。`setup.py` 相当は 0 件。ただし `.so` が 16 個あり、中身の静的監査は未実施)。既知の脆弱性: 未確認。外部送信: NASDAQ Data Link連携時にAPIキー送信が発生しうる(未確認、使わなければ発火しない)。自動発注: 無し(バックテスト専用と要約に明記)。宣伝の兆候: 無し

---

#### 8. Lean CLI

- **名前/種別**: lean(PyPI) / QuantConnect/lean-cli — QuantConnect社のLEANエンジンをローカル/クラウドで動かすCLIツール
- **できること全部**: PyPI description逐語「A CLI aimed at making it easier to run QuantConnect's LEAN engine locally and in the cloud」。GitHub要約: ローカルバックテスト・ローカルデバッグ・クラウド同期
- **言語・動作環境**: Python>=3.9(一次資料)。**実行にはDockerが必須**(依存に`docker`パッケージが入る、実測pip installログ)
- **ライセンス**: Apache(一次資料PyPI classifier)
- **版と最終更新日**: 1.0.229、2026-08-28(一次資料。非常に活発)
- **活動**: スター326・フォーク168・コミット1,687件(WebFetch要約)
- **対応ブローカー/データ**: WebFetch要約(GitHub)= Interactive Brokers/Tradier/Oanda/Bitfinex/Coinbase Advanced Trade/Binance/Zerodha/Samco/Kraken/Bybit/TradeStation/Alpaca/Tastytrade/dYdX/Webull等。**bitFlyer/bitbank/GMOコインの記載なし**
- **出典**: pypi.org/pypi/lean/json、github.com/QuantConnect/lean-cli

**料金の構造**: CLI自体は無料(Apache)。**実際のバックテストエンジン(LEAN本体)はDockerイメージとして別途pull が必要**(一次資料に明記されていないが`docker`依存から推定)。QuantConnectのクラウド機能利用は別途アカウント登録・課金体系が存在する可能性(未確認、登録はしない方針のため未検証)。「lean CLIパッケージ = LEANエンジンそのもの」ではない点が「無料の顔をした構造」の一例になりうる(推定)

**到達・導入・実行の記録**:
- `pip install lean`(隔離venv、rc=0、実測。`docker`・`cryptography`・`pydantic`・`rich`等15パッケージ導入)
- **最小の実行**: **未実施**。実際のバックテストには`lean backtest`コマンドがDockerイメージ(LEANエンジン本体、サイズ未確認だが一般に数百MB〜GB級と推測=推定)をpullする必要があり、§6-6「本体の一括ダウンロード数百MB以上はしない」に抵触する可能性が高いため、本回は意図的に実行を見送った(エラーで諦めたのではなく、規則に照らした判断)。次回、オーナー確認のうえでDocker pullを許可するか判断が必要
- 所要時間: install 7.37 秒(Lean CLI。生ログの time_s)

**当方の用途との相性**: 未確認(最小実行未実施)

**当方に無いもの(一次資料の逐語で)**: GitHub要約のブローカー一覧にある多数の証券会社接続(Interactive Brokers等、株式・先物向け)は当方に無い

**4軸**: 1=実測(CLI導入は成功) / 2〜4=未確認(Docker実行が前提のため測れず)

**危険**: 供給網: PyPI/GitHub一致(一次資料)。導入時実行: **無し**(wheel を展開して確認 = 生ログ LV-8。`setup.py` 相当 0 件・`.so` 0 件)。既知の脆弱性: 未確認。外部送信: QuantConnectクラウドとの通信機能あり(未確認、使わなければ発火しない)。自動発注: 一次資料の対応ブローカー一覧から、ライブ発注機能を持つと読める(未確認、ソース未確認)。宣伝の兆候: 無し。**§6-6の規則によりDockerイメージのpullを見送ったため、実質的な機能検証ができていない点が最大の限界**

#### 10. Zenbot(本家、carlos8f)

- **名前/種別**: carlos8f/zenbot(GitHub、npm) — コマンドライン暗号資産トレードボット(Node.js+MongoDB)
- **できること全部**: GitHub要約「automated technical-analysis-based trading, backtesting capabilities, and paper trading mode」
- **言語・動作環境**: Node.js + MongoDB(実測、GitHub要約)
- **ライセンス**: MIT(一次資料、WebFetch要約)
- **版と最終更新日**: **2022-02-15(Feb 15, 2022)にアーカイブ済み**。調査班の取得結果(W-13)には「archived」しかなく日付が無かったため、**リードが取り直して逐語「This repository was archived by the owner on Feb 15, 2022. It is now read-only.」を確認した(生ログ LV-3)**。最終コミット日は個別に未確認
- **活動**: スター8.3k・フォーク2.0k・コミット3,885件(WebFetch要約)。**明示的な廃止警告**「WARNING: project is no longer actively maintained, make sure to update any dependencies if you plan on using this in your project」(一次資料逐語)
- **対応取引所**: 一次資料(WebFetch要約)= Binance/Bitfinex/Bitstamp/Bittrex/CEX.IO/GDAX/Gemini/HitBTC/Kraken/Poloniex/TheRockTrading。**bitFlyer/bitbank/GMOコインは無い**
- **出典**: github.com/carlos8f/zenbot(実測取得)

**料金の構造**: 無料(MIT)。ただしMongoDBという外部データベースの用意が必要(自前でホストする分には無料だが、運用の手間が発生)

**到達・導入・実行の記録**: 本回は導入未実施(試したこと: GitHubページのWebFetchのみ)。理由: (1) Node.js環境であり本セッションの主力はPython隔離venvだが`node`/`npm`自体は使用可能なことを確認済み、(2) MongoDBという外部サービス依存があり、鍵・登録は不要だが導入・起動の手間が大きい、(3) 2022年にアーカイブされ4年近く更新が無く、優先度を他候補より下げた。**次回、npm+ローカルMongoDBでの導入を試す余地はある(「エラーで諦めた」のではなく優先度判断)**

**当方の用途との相性**: 未確認(未導入)

**当方に無いもの**: 未確認(README要約の域を出ない、次回ソース確認)

**4軸**: 1=一次資料(MIT・Node.js+MongoDBという要件は確認したが導入未実施) / 2〜4=未確認

**危険**: 供給網: 未確認(npmパッケージ化はされておらず、GitHubからの直接clone想定と見られる、未確認)。導入時実行: 未確認。既知の脆弱性: **アーカイブから4年近く経過しており、Node.js依存パッケージの既知脆弱性が蓄積している可能性が高い**(未確認だが一次資料の廃止警告自体がこれを示唆)。外部送信: 取引所APIキーを扱う設計のため、鍵の取り扱いには注意が必要(未確認)。自動発注: 有り(トレードボットが本体機能)。宣伝の兆候: 無し

---

#### 11. Qlib(pyqlib)

- **名前/種別**: pyqlib(PyPI) / microsoft/qlib — AI志向の定量投資プラットフォーム
- **できること全部**: PyPI description逐語「A Quantitative-research Platform」。GitHub要約「full ML pipeline of data processing, model training, back-testing」「the entire chain of quantitative investment: alpha seeking, risk modeling, portfolio optimization, and order execution」
- **言語・動作環境**: Python>=3.8.0(一次資料)
- **ライセンス**: MIT(一次資料PyPI classifier)
- **版と最終更新日**: 0.9.7、2025-08-15(一次資料)
- **活動**: スター48.7k・フォーク7.7k・コミット2,068件(WebFetch要約)。Microsoft発
- **対応取引所**: GitHub要約では中国市場・米国市場のデータセット(Yahoo Finance等)中心。暗号資産・FXへの言及は要約に無し(未確認)

**料金の構造**: 本体無料(MIT)。**依存パッケージが極めて多い**(実測: pip install で **130 個**の新規パッケージが導入され(出力全文 = 生ログ LV-10。調査班の「185個」は数え違いで、リードが出力から数え直した)、mlflow・mlflow-tracing・mlflow-skinny・databricks-sdk(クラウド実験管理)・redis・pymongo・gym(強化学習)・cvxpy(凸最適化)・lightgbm・Flask・fastapi・jupyter一式などを含む)。これら自体はOSSで無料だが、**mlflow/databricks-sdkの存在は、既定でクラウドのトラッキングサーバーへの接続を試みる設定になっていないか要確認**(未確認、次回課題。デフォルトでは通常ローカルファイルにフォールバックするのが一般的だが本回は検証していない)

**到達・導入・実行の記録**:
- `pip install pyqlib`(隔離venv、rc=0、実測、58.35 秒 = 生ログの time_s)。`pip check` → No broken requirements found(実測)
- **最小の実行**: **未実施**。Qlibのバックテストは`qlib.init()`で専用のバイナリデータ形式(`.bin`ファイル、`dump_bin`スクリプトで変換)を指すデータディレクトリを要求する設計であり、pandasのDataFrameを直接渡す単純な経路が標準ドキュメントの範囲では見当たらなかった(試したこと: パッケージ構成の確認のみ、実行スクリプトの作成は本回の予算内で完了しなかった)

**当方の用途との相性**: 未確認

**当方に無いもの(一次資料の逐語で)**: 「full ML pipeline of data processing, model training, back-testing」「alpha seeking, risk modeling, portfolio optimization」という一気通貫のMLパイプライン(当方の`strategy/`は未検証の個別戦略実装のみで、ML pipelineという統合された枠組みは無い)

**4軸**: 1=実測(導入成功) / 2〜4=未確認(最小実行未実施)

**危険**: 供給網: PyPI project_urls確認は本回未実施(次回)。導入時実行: **無し**(wheel を展開して確認 = 生ログ LV-8。`setup.py` 相当は 0 件。`.so` が 2 個あり中身の静的監査は未実施)。既知の脆弱性: 未確認。**外部送信: mlflow/databricks-sdkの既定動作(ローカル完結かクラウド接続を試みるか)が未確認**、次回の優先確認事項として記録。自動発注: GitHub要約に「order execution」という語があり機能として存在すると読めるが未確認。宣伝の兆候: 無し(Microsoft公式OSS)

#### 12. VnPy

- **名前/種別**: vnpy(PyPI) / vnpy/vnpy — 中国発のオープンソース量トレードシステム開発フレームワーク
- **できること全部**: PyPI description「A framework for developing quant trading systems.」。GitHub README(中国語)要約: 「VeighNa发布十周年之际正式推出4.0版本」(10周年で4.0版、AI向けvnpy.alphaモジュール新設)。4.0からAI/ML向け機能(データセット・因子特徴量エンジニアリング)を強化
- **言語・動作環境**: Python>=3.10(一次資料)
- **ライセンス**: MIT(一次資料PyPI `license`フィールドに直接記載、他候補と異なりclassifierでなくlicenseフィールドに明記)
- **版と最終更新日**: 4.4.0、2026-05-14(一次資料。活発)
- **活動**: スター45.5k・フォーク12.5k・コミット6,904件(WebFetch要約)
- **対応取引所**: **実測(コア`vnpy`パッケージのサブモジュール一覧)= alpha/chart/event/trader のみ。gateway実装・バックテストエンジンはコアパッケージに同梱されていない**。PyPIで`vnpy_binance`は実在(実測、curl 200)、`vnpy_bitflyer`/`vnpy_bitbank`/`vnpy_gmocoin`は**PyPIに存在しない**(実測、curl 404×3)
- **出典**: pypi.org/pypi/vnpy/json、github.com/vnpy/vnpy、pypi.org/pypi/vnpy_binance/json 等(いずれも実測)

**料金の構造**: コア無料(MIT)。GUI(PySide6/Qt)込みで導入されるため商用配布時のQtライセンス条項の確認が必要な場合がある(未確認、PySide6自体はLGPL/商用デュアルライセンスだが、当方は自社内利用のみなら通常問題にならない=推定)。取引所ごとのgatewayパッケージが個別に必要という構造(コアだけでは接続できない)

**到達・導入・実行の記録**:
- `pip install vnpy`(隔離venv、rc=0、実測、19.49 秒 = 生ログの time_s)。**PySide6(Qt GUIフレームワーク)一式・ta-lib・deap(遺伝的アルゴリズム)・pyqtgraph等、GUIおよび最適化ツール込みの重い依存**が入った
- **最小の実行**: **未実施**。バックテストエンジンは別パッケージ`vnpy_ctastrategy`等が必要と判明(コアに同梱されていないことをモジュール一覧の実測で確認)。次回、`vnpy_ctastrategy`を追加導入してCTA戦略の最小実行を試す
- 所要時間: install 19.49 秒(生ログの time_s。「約90秒」は誤り)

**当方の用途との相性**: 未確認

**当方に無いもの(一次資料の逐語で)**: 「vnpy.alpha」モジュール — README逐語「一站式多因子机器学习（ML）策略开发、投研和实盘交易解决方案」(ワンストップの多因子ML戦略開発・投資研究・実運用ソリューション)。当方に因子ベースのML戦略開発基盤は無い

**4軸**: 1=実測(コア導入成功、ただし実運用にはgatewayパッケージ追加が必要) / 2〜4=未確認

**危険**: 供給網: PyPI project_urls確認(一次資料、github.com/vnpy/vnpy/)。導入時実行: **無し**(wheel を展開して確認 = 生ログ LV-8。`setup.py` 相当 0 件・`.so` 0 件の純 Python の wheel)。既知の脆弱性: 未確認。外部送信: 未確認。自動発注: gatewayパッケージ経由で有り(コア自体には接続機能なし)。宣伝の兆候: 無し(中国語コミュニティ向けQRコード等の勧誘導線はREADMEにあるが詐欺の兆候ではない)

---

#### 13. Jesse

- **名前/種別**: jesse(PyPI) / jesse-ai/jesse — 暗号資産専用のトレーディングフレームワーク
- **できること全部**: PyPI description「A trading framework for cryptocurrencies」。README「advanced crypto trading framework that aims to simplify researching and defining YOUR OWN trading strategies for backtesting, optimizing, and live trading」
- **言語・動作環境**: Python>=3.10(一次資料)
- **ライセンス**: MIT(一次資料PyPI classifier、コア部分)
- **版と最終更新日**: **3.2.1、2026-09-21T16:01(一次資料。3.2.0 → 3.2.1 の更新を観測したのは 1 回目の実行(15:44Z の取得時は 3.2.0、同日 16:01Z に 3.2.1)。2 回目の取得(01:28:59Z)は最初から 3.2.1。非常に活発)**
- **活動**: スター8.6k・フォーク1.2k・コミット3,491件(WebFetch要約)
- **対応取引所**: **実測(wheel展開 = 生ログ LV-5b、`import_candles_mode/drivers`ディレクトリ = 生ログ LV-5c)= Apex/Binance/Bitfinex/Bybit/Coinbase/Gate/Hyperliquid/Kraken/KuCoin/Lighter の10件。bitFlyer/bitbank/GMOコインは無い**
- **出典**: pypi.org/pypi/jesse/json、github.com/jesse-ai/jesse、wheel展開の実測(いずれも取得)

**料金の構造**: コアMIT無料。README・PyPI一次資料に課金の直接記載は無し(round1で確認した「JesseGPT等はサブスク」は検索結果の要約(推定 = 未検算、W-23)のまま、本回は逐語裏取りに至らず次回課題)

**到達・導入・実行の記録**:
- `pip install jesse`(既存venv、rc=0、実測)。ただし共存 venv の numpy が 1.26.4 になり、pip 自身が依存衝突を警告した。警告が numpy の要求として名指しするのは 5 件(hftbacktest numpy<2.3,>=2.0・qstrader numpy>=2.0.0・vnpy numpy>=2.2.3・sparsediffpy numpy>=2.0.0・cvxpy numpy>=2.0.0)= 生ログ LV-10 の jesse 節の ERROR 行。なお mlflow の衝突は numpy ではなく cryptography(42.0.8)なので numpy の列から外した(監査 12 回目の指摘 2)。「2.x から」の部分は ERROR 行からの推定で、`Attempting uninstall: numpy` のような明示の記録は出力に無い(pandas の場合はあった)。**方法論上の教訓**: 複数の重量級ツールを1つのvenvに混在させると相互に壊れる。次回以降は候補ごとに隔離venvを分けるべき(本回の後半はhftbacktest/NautilusTrader/vectorbt/freqtradeをそれぞれ別venvに分離して対応した)
- wheel展開で確認した危険関連の事実: **`libzklink_sdk.so/.dll/.dylib`(Apex DEX向け)・`lighter-signer-*.so/.dll/.dylib`(Lighter DEX向け)というコンパイル済みネイティブバイナリを同梱**。これらはDEX(分散型取引所)のオンチェーン署名用SDKで、鍵を使わない限りは発火しないと見られるが、コンパイル済みバイナリの中身は静的監査していない(未確認)
- 依存に`ray`(分散計算)・`redis`・`psycopg2-binary`(PostgreSQL)・`eth-account`/`eth-keys`/`eth-utils`/`rlp`/`hexbytes`(Ethereumウォレット関連ライブラリ)・`optuna`(ハイパーパラメータ最適化)・`mcp`(Model Context Protocol、AIエージェント関連)が含まれる(実測、pip installログ)
- **最小の実行**: **未実施**。Jesseの`backtest`コマンドはプロジェクトディレクトリの初期化(`jesse init`相当)とPostgreSQL・Redisの起動を要求する設計で、本回の予算内では準備が完了しなかった
- 所要時間: install 60.29 秒(生ログの time_s)

**当方の用途との相性**: 未確認

**当方に無いもの(一次資料の逐語で)**: DEX(Apex/Lighter/Hyperliquid等)向けのオンチェーン署名機構一式(当方はbitFlyer CFDのみでオンチェーンDEXとの接続は無い)。`optuna`によるハイパーパラメータ最適化ループ(当方に自動チューニングの仕組みは無い)

**4軸**: 1=実測(導入成功だが依存衝突あり、隔離venvを分ければ解消可能と推定) / 2〜4=未確認

**危険**: 供給網: PyPI project_urls確認(一次資料)。導入時実行: **無し**(wheel を展開して確認 = 生ログ LV-8。`setup.py` 相当 0 件。ただし `.so` が 3 個あり、中身の静的監査は未実施)。既知の脆弱性: 未確認。**外部送信: DEX署名用ネイティブバイナリの存在自体が要注意点(鍵を渡さなければ発火しないと見られるが静的監査未実施)**。自動発注: 有り(ライブトレード機能が本体機能)。宣伝の兆候: 無し(README・PyPIとも公式の機能説明のみ)

#### 14. Mendl-Labs/BacktestingCore

- **名前/種別**: GitHub限定(PyPI無し、実測curl 404×3 = `backtestingcore`/類似名で検索)。Rust製バックテストエンジン、PyO3でPython戦略記述をサポートすると謳う
- **できること全部**: WebFetch要約「event-driven simulation, walk-forward analysis, genetic strategy optimization, portfolio/risk management, and Python strategy execution capabilities」「lock-free orderbook, configurable slippage/commission models, Black-Scholes derivatives pricing, and multi-venue order routing with TWAP/VWAP algorithms」
- **言語・動作環境**: Rust(コア)+ PyO3経由でPython戦略記述
- **ライセンス**: **Functional Source License 1.1**(WebFetch要約。2年後にApache 2.0へ移行するライセンス)。**OSI承認のオープンソースライセンスではない** — 一般に「競合する商用利用」を制限する条項を持つ(FSLの一般的な性質。本ツールの実際の条項本文はLICENSE原文を取得していないため未確認)
- **版と最終更新日**: 未確認(バージョン番号は一次資料から未取得)
- **活動**: スター0・フォーク0(WebFetch要約)、18コミット。**新規かつ未検証のプロジェクト**(9件のオープンPRがあり開発中と見られる)
- **対応取引所**: 「multi-venue order routing」と謳うが個別取引所名は要約に無い(未確認)
- **出典**: github.com/Mendl-Labs/BacktestingCore(WebFetch要約のみ)

**料金の構造**: FSLは「2年後にApache2.0化」する時限式のライセンスで、**それまでの期間は競合サービスとしての商用利用が制限される可能性がある**(一般的なFSLの性質。本プロジェクト固有の条項本文は未確認)。無料で試すこと自体は通常問題ない

**到達・導入・実行の記録**: 本回は未導入。理由: (1) PyPI未配布のためRustツールチェーン(cargo/maturin)でのビルドが必要、(2) スター0・フォーク0・新規プロジェクトという活動状況から優先度を下げた。試したこと: PyPI検索(`backtestingcore`/`event-driven-backtesting-engine`、curl、404×2)、GitHubページのWebFetch取得のみ

**当方の用途との相性**: 未確認

**当方に無いもの**: 「lock-free orderbook」「Black-Scholes derivatives pricing」(当方にオプション価格付けの機構は無い)。ただしいずれも一次資料の逐語ではなくWebFetch要約であり、次回LICENSE/READMEの原文確認が必要

**4軸**: 全軸未確認(未導入)

**危険**: 供給網: 未確認(PyPI無し、GitHubのみ)。導入時実行: 未確認(Rustビルドのため`cargo build`が任意のビルドスクリプトを実行しうる点は一般的なRustプロジェクトと同じ、本ツール固有の危険性は未確認)。既知の脆弱性: 未確認。外部送信: 未確認。自動発注: 「order routing」という語から示唆されるが未確認。宣伝の兆候: 無し。**FSLというOSI非承認ライセンスであることが唯一確認できた実務上の留意点**

---

#### 15. Luczinsritter/event_driven_backtesting_engine

- **名前/種別**: GitHub限定(PyPI無し、実測curl 404)。個人/学習用のイベント駆動バックテストフレームワーク
- **できること全部**: WebFetch要約「processes market data at tick or bar intervals, generating signals at time t and executing at t+1 to avoid look-ahead bias」「trade journaling, risk metrics (Sharpe ratio, Sortino ratio, max drawdown, Kelly Criterion)」「demonstration strategies using EMA crossovers and ARIMA forecasting」
- **言語・動作環境**: Python
- **ライセンス**: MIT(WebFetch要約)
- **版と最終更新日**: 未確認
- **活動**: スター0・フォーク0・5コミット(WebFetch要約)。「Next Steps」に「transaction costs, tick-level data, dynamic position sizing」等の未実装項目が列挙されており、**開発初期段階の個人プロジェクト**と判断できる根拠がある(一次資料の記述、要約経由)
- **対応取引所**: 記載なし
- **出典**: github.com/Luczinsritter/event_driven_backtesting_engine(WebFetch要約のみ)

**料金の構造**: 完全無料(MIT)、外部依存も一次資料の要約からは示唆されない

**到達・導入・実行の記録**: 本回は未導入(優先度判断: スター0・5コミットの個人プロジェクトであり、他の活発な候補を優先した)。試したこと: GitHubページのWebFetch取得のみ

**当方の用途との相性**: 未確認

**当方に無いもの**: 「signals at time t, executing at t+1」というルックアヘッド回避の明示的設計(当方にも同様の設計思想はあるはずだが、この点を明文化した独立実装として参照する価値はありうる、未検証)

**4軸**: 全軸未確認(未導入)

**危険**: 供給網: 未確認。導入時実行: 未確認。既知の脆弱性: 未確認。外部送信: 未確認。自動発注: 無し(バックテスト専用と見られる)。宣伝の兆候: 無し

---

#### 16. Bot18(carlos8f)

- **名前/種別**: bot18(npm) / carlos8f/bot18 — Zenbot作者による高頻度暗号資産トレードボット
- **できること全部**: 一次資料(npmページ本文、WebSearch経由で取得): 「Bot18 is a high-frequency cryptocurrency trading bot by Zenbot creator @carlos8f」。Bitfinex・Coinbase Proのライブ取引ストリームを監視、手動・自動売買対応、板の力の不均衡(power-imbalance)戦略
- **言語・動作環境**: Node.js(実測、`npm i bot18`)
- **ライセンス**: LICENSE.txtファイルが存在(WebFetch、具体的な種別は本回未確認)
- **版と最終更新日**: 最新0.4.31、**npm最終公開は約7年前**(一次資料npmページ本文の逐語「last published 7 years ago」。2026年基準で概ね2019年頃)
- **活動**: スター203・フォーク26(WebFetch要約)
- **対応取引所**: Bitfinex・Coinbase Proのみ(一次資料要約)。bitFlyer等は無い

**料金の構造(一次資料の逐語 + URL + 取得日)**: npmページ本文(WebSearch経由取得、2026-09-22)逐語:「an 8-digit Unlock Code is purchasable for $49.99 (for a limited time!)」。GitHub README逐語(WebFetch):「Free trial mode available by entering "guest" username or running with `--channel trial`」、ただし「this "cripple mode" runs roughly 10x slower, lacks auto-trading support, and auto-exits after 15 minutes」。ベータ版警告の逐語:「Keep in mind this is the BETA RELEASE. ... Expect things to be broken, unfinished, and inconsistent. Live trading is discouraged unless you're just playing around with small amounts of currency」。**「無料お試し」と「有料アンロック」の境界が明確な逐語で確認できた実例**(L-378が懸念した型そのもの)

**到達・導入・実行の記録**: 本回は未導入(優先度判断: Node.js・約7年前の最終更新・有料アンロックが前提で自動売買が使えない無料枠、という組み合わせから他候補を優先)。試したこと: npmページ本文のWebSearch取得、GitHubページのWebFetch取得

**当方の用途との相性**: 未確認

**当方に無いもの**: 板の力の不均衡(orderbook power-imbalance)ベースの自動売買戦略という具体的な手法(一次資料の説明のみ、実装詳細は未確認)

**4軸**: 全軸未確認(未導入)

**危険**: 供給網: 未確認(npm配布元の検証は本回未実施)。導入時実行: 未確認。既知の脆弱性: **7年間パッチが無く、Node.js依存の既知脆弱性が蓄積している可能性が高い**(未確認だが一次資料のベータ警告・長期未更新がこれを示唆)。外部送信: 「All communications and local storage are encrypted using TLS for client-server transmissions」という記載があり(npmページ本文、WebSearch要約経由)、何らかの外部サーバー(アンロックコード認証用と見られる)と通信する設計が示唆される(未確認、詳細はソース未読)。自動発注: 有り(本体機能、ただし無料お試しでは無効)。宣伝・詐欺の兆候: **アンロックコード販売という収益モデルはあるが、「必ず儲かる」等の誇大宣伝やウォレット秘密鍵要求は一次資料に見当たらない。詐欺の兆候は無いが、有料ゲートの存在そのものは§4の「料金の構造」で正確に記録すべき事例**

### 1回目の候補1〜4への追加情報(2回目、次回優先項目1・2・4・5・7・8・10の解決分)

#### 1. hftbacktest(追加)

**最小実行の完全達成(ただし出所はリードの再現)**: 1回目は「API呼び出しは動くが約定(FILLED)は成立しなかった」で終わっていた。今回、`hftbacktest.types`のevent_dtype(`ev/exch_ts/local_ts/px/qty/order_id/ival/fval`、一次資料=ソース実測)を正確に読み取り、DEPTH_SNAPSHOT_EVENT→TRADE_EVENTの合成データを再構築した結果、**指値買い@100.0がstatus=3(FILLED)・exec_qty=1.0・leaves_qty=0.0で約定し、成行手仕舞いも成功、num_trades=2という完全な1往復が成立した**。**ただし調査班はこの結果を見ていない**: v4 は rc=1 で失敗し、v5 はバックグラウンドで起動したところまでで、出力を読んだ記録が無い(生ログ LV-6)。**リードが同じスクリプトを打ち直して上の値を再現した(生ログ LV-2)。**この行の印は「実測(リード)」であって調査班の実測ではない。「取れない」ではなく「イベント順序の作り込みが必要」だったことが確定した

**方法論上の注意点(実測)**: `OrderDict`オブジェクトに対して`.keys()`でイテレートするコードは、numba jitclassの型解決の問題と見られる挙動で**6分48秒経過してもCPU時間1秒のままハングした**(kill -9で強制終了)。`.get(order_id)`による直接アクセスに切り替えたところ正常終了(17ステップ、数秒)。**この 408 秒の実行は委任文 §6-6「1 件の実行は数分まで」を超えている**(生ログ 128 行 rc=killed time_s=408)。超過に気づいた時点で止めるべきだった(監査 1 回目の指摘 9)。**`orders(0).keys()`や`in`演算子での探索は避け、`.get()`を使うべき**という実務上の知見

#### 2. NautilusTrader(追加)

**pip install・最小実行の完全達成**: 1回目は「PyPI JSONとGitHub READMEの取得のみ」で終わっていた。今回、Python3.12の隔離venv(要件`>=3.12,<3.15`を満たす)に導入(14依存のみの軽量インストール、実測)。公式example(`examples/backtest/fx_ema_cross_audusd_bars_from_ticks.py`)は`nautilus_trader.testkit`という現行リリースに存在しないモジュールを参照しており(developブランチのソースと2026-09時点のリリース1.231.0のAPIに不一致がある、実測で発見)、正しいモジュール名`nautilus_trader.test_kit`(アンダースコア)を使う独自スクリプトを作成。BTCUSDT/BINANCEの合成足データでLIMIT買い注文→FILLED→MARKET売り注文で手仕舞いの1往復が成立。**ただし調査班はこの結果を見ていない**(背景で起動しただけで出力を読んだ記録が無い。hftbacktest と同じ型)。**リードが打ち直して確認した(生ログ LV-7、rc=0)**: 残高は 開始 100,000.00000000 USDT + 10.00000000 BTC → 終了 99,998.35248510 USDT + 10.00000000 BTC(建玉 0.01 BTC を建てて閉じ、費用は USDT 側で 1.64751490 減った)。OrderFilled 2 件・fills report は [2 rows x 36 columns]。**「本番グレードの発注機能」という宣伝文句を、実際に動かして裏取りした数少ない候補。裏取りしたのはリード**

**対応取引所の確定(実測)**: `crates/adapters`ディレクトリの実際の一覧(WebFetch実測)= architect_ax/betfair/binance/bitmex/blockchain/bybit/coinbase/databento/deribit/derive/dydx/hyperliquid/interactive_brokers/kraken/lighter/okx/polymarket/sandbox/tardisの19件。RELEASES.md全文(567,723バイト、curl実測)にbitflyer/bitbank/gmoの一致0件(grep)。**bitFlyer等の非対応は、README要約ではなくソースディレクトリの直接列挙とリリースノート全文検索という2つの独立した一次資料で確定した**

**ライセンス表記の食い違いの確定**: README.md原文(develop、curl実測、200)に「cargo-deny enforces a license allow list compatible with `LGPL-3.0-only`」「available...under the GNU Lesser General Public License v3.0」と明記。**PyPI JSONの`license_expression`(`LGPL-3.0-or-later`)と食い違う**ことが一次資料同士の直接比較で確定した。原因(パッケージングミスか意図的併記か)は未確認

#### 3. vectorbt / vectorbt.pro(追加)

**無料版とPROの機能差(逐語裏取り完了)**: LICENSE.md原文(raw.githubusercontent、curl実測、200)を取得し、round1で「未検算」だった料金・ライセンス文言が原文で確認できた:「"Commons Clause" License Condition v1.0」「the License does not grant to you, the right to Sell the Software」(Sellの定義=ホスティング/コンサルティング等、対価を得てソフトウェアの機能性に実質的に由来する製品/サービスを提供すること)。**当方が社内で使う分には問題にならないが、当方が third partyにサービスとして提供する用途は制限される**

**無料版に指値注文の概念が無いことを実測で確定**: 隔離venvに無料版`vectorbt`(1.1.0)を導入したところ、**最新のplotly(7.1.0)ではimport時にAttributeErrorで起動不能**(`plotly.graph_objs`の`scattermapbox`プロパティが現行plotlyで廃止されたため、vectorbt側の初期化コードが古いAPIに依存)。`plotly<5`に切り替えると今度は`numpy.bool8`属性なしでImportError(古いplotlyがnumpy2.x非互換)。最終的に`plotly==5.24.1`+`numpy<2`の組み合わせでimport成功(ただしvectorbt自身はPyPI上でnumpy>=2.4.6を要求しており、実際にはnumpy1.26.4でも動いてしまうという矛盾も確認)。**「最新の一次資料(2026-07-05更新)」でも、現行のplotly/numpy双方と素のpip installでは共存しないことを実測した** — これ自体がL-378の懸念(無料の顔をした運用コスト)の別の一例といえる。import成功後、パッケージ全体を`grep -rl -i "limit_order\|LimitOrder\|order_type.*Limit"`で検索したが**0件**。**無料版のソースに指値注文という概念が存在しないことが確定した**(PROの「Limit orders」がPRO限定機能であることの直接的な裏付け)

#### 4. freqtrade(追加)

**bitFlyer非対応の一次資料裏取り完了**: 隔離venvにfreqtrade導入(ccxt 4.5.82同梱)。`freqtrade list-exchanges -a`を実測実行: 「bitFlyer」行「missing: fetchOrder, fetchOHLCV; missing opt: fetchTickers, watchOHLCV」(表の実物 = 生ログ LV-5f。105取引所中)。`freqtrade list-exchanges`(非-a、freqtradeが実際に使える79取引所の一覧)にbitFlyerは**含まれず**、bitbankは**含まれる**(bitbank行は「missing opt: fetchTickers, fetchOrders, watchOHLCV」のみで必須機能の欠落なし)。**1回目は「bitFlyer/bitbank/GMOコインは個別記載なし」とまとめていたが、bitbankは実はfreqtradeで使える側に入っていたことが今回の実測で判明した**(round1からの訂正)

**ccxt自体のbitFlyer対応状況(区分2向けの補助情報として記録)**: `ccxt.bitflyer().has`を実測(出力 = 生ログ LV-5g): `createOrder=True, cancelOrder=True`(発注・キャンセルは可能)、`fetchOHLCV=None, fetchTickers=None, watchOHLCV=None`(無し)、`fetchOrder='emulated'`(ccxt側のエミュレーションで代替、ネイティブ実装ではない)。**freqtradeがbitFlyerを除外する理由は「バックテストに必須のローソク足取得ができない」ためであり、「発注ができない」わけではない**。GMOコインはccxtの取引所ID一覧に**存在しない**(`'gmocoin' in ccxt.exchanges` → False、実測)

### STRATEGY_IDEAS.md向け候補(提案のみ、未マージ)
- (本区分はツールの調査であり戦略案ではない。強いて挙げるなら「hftbacktestの指値約定成功パターン(FILLED はリードの打ち直しで確認 = 生ログ LV-2)を当方のmaker fill参照実装(`scripts/qa/maker_fill_ref.py`)と突き合わせ、`engine.py`の楽観性/悲観性を定量評価する」という検証タスクの候補は1回目から引き続き有効。リード判断待ち)

### DATA.md向け候補(提案のみ、未マージ)
- 無し(本区分はツールの調査であり、データ資産の調達ではない)

### 残りの候補名(次回の実行に渡す)

**未着手(このセッションで新規発見、次回深掘り)**: Basana(PyAlgoTradeの公式後継) / Backtrader / PySystemtrade / PyBroker / bt / Ziplime / Superalgos / OpenTrader / CryptoSignal / fast-trade / OctoBot / pybotters(区分2寄り、共有推奨)

**深掘りが未完了のまま残った項目(次回の優先課題)**:
1. zipline-reloadedの最小実行(bundle登録の準備)
2. Qlibの最小実行(`dump_bin`によるデータ形式準備)
3. VnPyの最小実行(`vnpy_ctastrategy`等バックテスト用の別パッケージ追加導入)
4. Jesseの最小実行(PostgreSQL+Redisの起動、隔離venvでの再導入 — 本回のvenv_tools1はnumpy依存衝突が発生したため)
5. Lean CLIの最小実行(Dockerイメージのpullが§6-6の規則(数百MB以上の一括DL禁止)に抵触する可能性、オーナー確認が必要か次回リード判断待ち)
6. Zenbot(本家)・Bot18のNode.js環境での導入(npm+MongoDB、優先度は最も低い)
7. Mendl-Labs/BacktestingCore・Luczinsritter/event_driven_backtesting_engineのLICENSE/README原文取得(現状はWebFetch要約止まり)、優先度は低い(スター0・新規/学習用)
8. Jesseの「プレミアム機能(JesseGPT等)がサブスクリプション」の逐語裏取り(round1のW-23のまま未解決)
9. Qlibのmlflow/databricks-sdkが既定でクラウド接続を試みるかどうかの検証(外部送信の観点で優先度が高い)
10. hftbacktestの取引所対応(Binance Futures/Bybitのみ)を、README要約ではなくソースディレクトリの直接列挙で裏取り(`rust/src/live/connector`等のパスは本回404、正しいパスを次回探索)
11. 新規発見の12候補(18〜29)全件の一次資料到達(PyPI/GitHub)

### 予算の消費

トークン・時間の自己推定はしない(委任文の規則により、リードがハーネスの計測値を記録する)。**リードの記録(ハーネスの計測、2026-09-22): 330,907 トークン・1,847,862 ミリ秒(約 30.8 分)・道具呼び出し 167 回。**委任文 §7 の固定値(5 万トークン・20 分)の 6.6 倍・1.5 倍で、1 回目(188,843 トークン・650 秒)より更に超過した。**Web の手はハーネスの記録で WebFetch 27・WebSearch 10 の計 37 手**(生ログ LV-1。この生ログに書かれていたのは 28 手で、9 手が漏れていた)。本回で実行した主な作業: curl(PyPI JSON等)30件超・pip install 12件(隔離venv複数)・独自の最小実行スクリプト作成7本(hftbacktest×2版・Backtesting.py・QSTrader・PyAlgoTrade・NautilusTrader×2版)。生ログは`docs/DATA/probes/20260922_tools_1_run2.log`に全手順を記録。

**候補の一覧はまだ空になっていない(新規発見12件を含め残りの候補名を参照)。§2の完了条件(残りの候補が空で、新しい検索計画6本が新しい候補を1件も出さない)を満たしていないため、本区分は未完了。次回の実行で持ち越す。**

## 区分1 — 3 回目の実行(2026-09-22)

リードの起動指定に従い、この回は **新しい検索計画を打たず**、2 回目が残した未着手の候補 A と、深掘りが未完了のまま残った項目 B を先に潰した。生ログは `docs/DATA/probes/20260922_tools_1_run3.log`(前回の中断分の続きから追記。この節の行番号はすべてこのファイルを指す)。

### 当方の道具立て(`python3 scripts/tools_inventory.py` の出力全文。§8)

```
# 当方の道具立て(git ls-files から生成。2026-09-22T06:31:35Z、HEAD 5b56ef2。コマンド: python3 scripts/tools_inventory.py)

## src/bot(package: ファイル数 / ファイル名)
- src/bot: 7 / atomic_file.py constants.py logging_setup.py main.py products.py radar.py settings.py
- src/bot/backtest: 3 / engine.py metrics.py walk_forward.py
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
- check_*: 8 / check_api.py check_data_ledger.py check_k1_binance.py check_k1_bitflyer_data.py check_kabu_api.py check_liquidation_feeds.py check_liquidation_history_depth.py check_scan_report.py
- build_*: 7 / build_basis.py build_bitflyer_lightchart_csv.py build_burst_library.py build_flow.py build_fx_event_library.py build_fx_event_library_2005_2014.py build_storm_library.py
- record_*: 5 / record_funding_basis.py record_liquidations.py record_oi.py record_realtime.py record_venues.py
- jev/: 3 / client.py redact.py schemas.py
- verify_*: 3 / verify_gates.py verify_liq_instrument.py verify_snapshots.py
- (単発): 2 / _research_audit_gate.py dashboard.py
- judge_*: 2 / judge_board_round.py judge_gates.py
- k1_*: 2 / k1_binance_data_quality.py k1_source.py
- paper_*: 2 / paper_on1.py paper_onr.py
- repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.py
- constants_*: 1 / constants_inventory.py
- data_*: 1 / data_quality.py
- explore_*: 1 / explore_o3c_oi_axis.py
- extract_*: 1 / extract_tape.py
- intake_*: 1 / intake_ledger.py
- liquidation_*: 1 / liquidation_report.py
- mirror_*: 1 / mirror_bitmex_archive.py
- normalize_*: 1 / normalize_bitflyer_executions.py
- phase2_*: 1 / phase2_seal.py
- preflight_*: 1 / preflight_prereg.py
- probe_*: 1 / probe_api_latency.py
- replay_*: 1 / replay_scalp_storm.py
- retention_*: 1 / retention_snapshot.py
- tools_*: 1 / tools_inventory.py
- tp_*: 1 / tp_operating_curve.py
- trace_*: 1 / trace_metrics.py
- validate_*: 1 / validate_composite.py
- x_*: 1 / x_fetch.py
- (.py 以外の scripts: 3 = scripts/fetch_all.sh scripts/install_git_hooks.sh scripts/regen_hook_manifest.sh)

## config: 32
  config/composite.yaml config/config.yaml config/constants.yaml config/etf_measure.yaml config/jev_delegation_tiers.yaml config/jev_design_examples/o3c_covariates.yaml config/jev_design_examples/o3c_observables.yaml config/jev_design_examples/signal2_covariates.yaml config/jev_design_examples/signal2_observables.yaml config/jev_design_examples/signal3_covariates.yaml config/jev_design_examples/signal3_observables.yaml config/jev_design_examples/signal4_covariates.yaml config/jev_design_examples/signal4_observables.yaml config/jev_design_examples/signal5_covariates.yaml config/jev_design_examples/signal5_observables.yaml config/jev_design_examples/signal6_covariates.yaml config/jev_design_examples/signal6_observables.yaml config/jev_design_examples/signal7_observables.yaml config/jev_design_examples/signal8_covariates.yaml config/jev_design_examples/signal8_observables.yaml config/jev_design_examples/signal8_observables_independent.yaml config/jev_design_examples/signal_covariates.yaml config/jev_design_examples/signal_observables.yaml config/jev_routes.yaml config/o3c_jev_state_bands.yaml config/o3c_signal_logit_chain.yaml config/o3c_signal_logit_first.yaml config/o3c_signal_logit_value_chain.yaml config/o3c_signal_logit_value_first.yaml config/on1_live.yaml config/products.yaml config/risk_limits.yaml

## deploy: 19
  deploy/bitflyer-bot.service deploy/bitflyer-fetch.service deploy/bitflyer-fetch.timer deploy/check_liq_recorder.bat deploy/etf_measure_entry.bat deploy/etf_measure_exit.bat deploy/fetch_all.bat deploy/mirror_bitmex.bat deploy/nightly_restart.bat deploy/on1_entry.bat deploy/on1_exit.bat deploy/probe_latency.bat deploy/reset_kill.bat deploy/restart_all.bat deploy/run_paper.bat deploy/setup.sh deploy/share_logs.bat deploy/start_all.bat deploy/stop_all.bat

## tests(ファイル): 139
  tests/conftest.py tests/fixtures/jev_ops/decisions.json tests/fixtures/jev_ops/notifications.jsonl tests/fixtures/jev_ops/status_page.html tests/test_app_fx_integration.py tests/test_audit_gates_wired.py tests/test_backtest.py tests/test_bitmex_mirror.py tests/test_board.py tests/test_board_round.py tests/test_board_walk.py tests/test_bot_research_overnight.py tests/test_build_flow.py tests/test_check_data_ledger.py tests/test_client.py tests/test_clock_burst.py tests/test_composite.py tests/test_constants.py tests/test_constants_inventory.py tests/test_dashboard.py tests/test_data_quality.py tests/test_data_quality_incremental.py tests/test_deploy.py tests/test_engine_maker_exit.py tests/test_etf_measure.py tests/test_extract_tape.py tests/test_fetch_backfill_scripts.py tests/test_fetch_binance_daily.py tests/test_fetch_binance_vision.py tests/test_fetch_history_candles.py tests/test_gz_members.py tests/test_intake_ledger.py tests/test_intent_map_rule.py tests/test_jev_audit_eval.py tests/test_jev_audit_loop.py tests/test_jev_check.py tests/test_jev_client.py tests/test_jev_delegate.py tests/test_jev_design.py tests/test_jev_ideas.py tests/test_jev_ops.py tests/test_jev_owner_log.py tests/test_jev_redact.py tests/test_jev_reply.py tests/test_jev_report_intake.py tests/test_jev_schemas.py tests/test_jev_scripts.py tests/test_jev_survey.py tests/test_jev_trace_export.py tests/test_judge_gates.py tests/test_k1_bitflyer_source.py tests/test_k1_bybit_source.py tests/test_k1_delay_decomp.py tests/test_k1_delay_entry.py tests/test_k1_flip_body.py tests/test_k1_lookahead.py tests/test_k1_no_invalidation.py tests/test_k1_round5.py tests/test_k1_seal_guard.py tests/test_k1_xvenue.py tests/test_liq_bands.py tests/test_liq_response.py tests/test_liq_response_dedup.py tests/test_liquidation_reader.py tests/test_maker_execution.py tests/test_market_data.py tests/test_market_view.py tests/test_max_hold.py tests/test_modes.py tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_ext.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_rows4.py tests/test_o3c_signal_calib.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore2.py tests/test_o3c_signal_explore3.py tests/test_o3c_signal_explore4.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_policy.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_on1_forward.py tests/test_on1_live.py tests/test_onr.py tests/test_onr_forward.py tests/test_orders.py tests/test_paper_state.py tests/test_phase2_p2_01.py tests/test_phase2_p2_01_final.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_phase2_p2_03.py tests/test_phase2_p2_03_final.py tests/test_phase2_p2_03_iter2.py tests/test_phase2_p2_04.py tests/test_phase2_seal.py tests/test_portfolio_and_strategy.py tests/test_position_ladder.py tests/test_preflight_prereg.py tests/test_probe_api_latency.py tests/test_qa_make_known_answer.py tests/test_qa_make_known_answer_maker.py tests/test_qa_make_known_answer_maker3.py tests/test_qa_make_known_answer_steer.py tests/test_qa_maker_fill_ref.py tests/test_qa_pipeline_known_answer.py tests/test_qa_score_audit.py tests/test_radar.py tests/test_realtime_recorder.py tests/test_record_funding_basis.py tests/test_record_liquidations.py tests/test_record_liquidations_writer.py tests/test_record_venues.py tests/test_repair_gz_listing.py tests/test_research_protocol_rules.py tests/test_resilience.py tests/test_retention_snapshot.py tests/test_risk.py tests/test_scalp_logic.py tests/test_sealed_load_diagnostic.py tests/test_sealed_ts_us.py tests/test_short_margin.py tests/test_tp_sl.py tests/test_verify_snapshots.py tests/test_wick_stop.py tests/test_x_fetch.py tests/test_xborder.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_fx.py tests/test_xborder_p2_known_answer.py tests/test_xborder_p2_state.py

## .claude/hooks: 8
  .claude/hooks/_verify_manifest.sh .claude/hooks/delegation_audit_gate.sh .claude/hooks/deny_protected_paths.sh .claude/hooks/jev_notice.sh .claude/hooks/owner_options_gate.sh .claude/hooks/owner_turn_digest.sh .claude/hooks/session_start_digest.sh .claude/hooks/trace_snapshot.sh

## .claude/agents: 3
  .claude/agents/owner-auditor-candidate.md .claude/agents/owner-auditor.md .claude/agents/owner-model-auditor.md

## .claude/skills: 9
  .claude/skills/delegated-study/SKILL.md .claude/skills/owner-audit/SKILL.md .claude/skills/owner-options/SKILL.md .claude/skills/owner-procedure/SKILL.md .claude/skills/research-protocol/SKILL.md .claude/skills/research-squad/SKILL.md .claude/skills/typesafe-ai/LICENSE .claude/skills/typesafe-ai/SKILL.md .claude/skills/x-research/SKILL.md

## githooks: 1
  githooks/pre-push

## docs(.md): 294
  docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11_control_review.md docs/AUDITOR/EVAL_2026-09-11b.md docs/AUDITOR/IMPROVEMENT.md docs/AUDITOR/JEV/LABELS_NOTES_2026-09-19.md docs/AUDITOR/JEV/PREREG_2026-09-19.md docs/AUDITOR/KNOWN_ANSWERS.md docs/AUDITOR/KNOWN_ANSWERS_ADDENDUM.md docs/AUDITOR/OWNER_MODEL_SOURCE.md docs/AUDITOR/PRINCIPLES.md docs/AUDITOR/PROCESS_METRICS.md docs/AUDITOR/PROPOSED_CHANGES_2026-09-11.md docs/AUDITOR/READDO/audit_stop.md docs/AUDITOR/READDO/before_unseal.md docs/AUDITOR/READDO/owner_objection.md docs/AUDITOR/READDO/push_blocked.md docs/AUDITOR/READDO/repeat_defect.md docs/AUDITOR/TREND.md docs/AUDITOR/VERDICTS/2026-09-11_k1_closure_entries.md docs/AUDITOR/VERDICTS/2026-09-11_proposed_changes_and_eval_b.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_execution.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_plan.md docs/AUDITOR/VERDICTS/2026-09-12_o3c_reframe_reading.md docs/AUDITOR/VERDICTS/2026-09-12_p14_liquidation_fix.md docs/AUDITOR/VERDICTS/2026-09-12_p4n_nightly_restart.md docs/AUDITOR/VERDICTS/2026-09-12_rules_reduction.md docs/AUDITOR/VERDICTS/2026-09-16_policy4_report.md docs/AUDITOR/VERDICTS/2026-09-17_anchor_report.md docs/AUDITOR/VERDICTS/2026-09-17_closure.md docs/AUDITOR/VERDICTS/2026-09-17_data_collection.md docs/AUDITOR/VERDICTS/2026-09-17_missing.md docs/AUDITOR/VERDICTS/2026-09-17_oi_distance.md docs/AUDITOR/VERDICTS/2026-09-17_price_level.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_ext.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_full.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_rows4.md docs/AUDITOR/VERDICTS/2026-09-18_oi_distance_split.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_design.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r10.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r2.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r3.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r4.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r5.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r6.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r7.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r8.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r9.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_run12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r11.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_r2_prereg.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r2.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r3.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_result.md docs/AUDITOR/VERDICTS/2026-09-19_signal_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_report.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_materials_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_result.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_design.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_result.md docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md docs/AUDITOR/VERDICTS/2026-09-21_tools_survey_prompt.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run2.md docs/AUDITOR/VERDICTS/2026-09-22_tools_survey_prompt_v12.md docs/AUDITOR/VERDICTS/README.md docs/AUDITOR/answers/KA-01.md docs/AUDITOR/answers/KA-02.md docs/AUDITOR/answers/KA-04.md docs/AUDITOR/answers/KA-05.md docs/AUDITOR/answers/KA-06.md docs/AUDITOR/answers/KA-07.md docs/AUDITOR/answers/KA-08.md docs/AUDITOR/answers/KA-09.md docs/AUDITOR/answers/KA-10.md docs/AUDITOR/answers/KA-16.md docs/AUDITOR/answers/KA-17.md docs/AUDITOR/answers/KA-18.md docs/AUDITOR/answers/KA-19.md docs/AUDITOR/answers/KA-20.md docs/AUDITOR/answers/KA-21.md docs/AUDITOR/answers/KA-22.md docs/AUDITOR/answers/KA-23.md docs/AUDITOR/answers/KA-24.md docs/AUDITOR/answers/KA-25.md docs/AUDITOR/answers/KA-26.md docs/AUDITOR/answers/KA-27.md docs/AUDITOR/answers/KA-28.md docs/AUDITOR/before/HYGIENE_2026-09-11.md docs/AUDITOR/before/KA-01.md docs/AUDITOR/before/KA-02.md docs/AUDITOR/before/KA-04.md docs/AUDITOR/before/KA-05.md docs/AUDITOR/before/KA-06.md docs/AUDITOR/before/KA-07.md docs/AUDITOR/before/KA-08.md docs/AUDITOR/before/KA-09.md docs/AUDITOR/before/KA-10.md docs/AUDITOR/before/KA-16.md docs/AUDITOR/before/KA-17.md docs/AUDITOR/before/KA-18.md docs/AUDITOR/before/KA-19.md docs/AUDITOR/before/KA-20.md docs/AUDITOR/before/KA-21.md docs/AUDITOR/before/KA-22.md docs/AUDITOR/before/KA-23.md docs/AUDITOR/before/KA-24.md docs/AUDITOR/before/KA-25.md docs/AUDITOR/before/KA-26.md docs/AUDITOR/before/KA-27.md docs/AUDITOR/before/KA-28.md docs/DATA.md docs/DATA/SCAN_2026-09-16.md docs/DATA/SCAN_2026-09-21_tools.md docs/DATA/delegations/20260919_o3c_signal_explore2_prompt.md docs/DATA/delegations/20260920_o3c_cascade_read_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_jev_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore3_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore4_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore5_prompt.md docs/DATA/delegations/20260920_o3c_signal_jev_state_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials2_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_stage2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_tp_prompt.md docs/DATA/delegations/20260921_tools_survey_prompt.md docs/DATA/delegations/20260922_tools_survey_prompt.md docs/DATA/probes/20260913_liquidation_integrity.md docs/DATA/probes/20260919_reaction_prereg_outputs.md docs/DATA/probes/20260920_o3c_cascade_read.md docs/DATA/probes/20260920_o3c_materials_read.md docs/DATA/surveys/BINANCE_CM_MMR_2026-09-17.md docs/DATA/surveys/BITFLYER_HISTORY_SOURCES.md docs/DATA/surveys/ETF_ALTERNATIVES.md docs/DATA/surveys/G2_DATA_INVENTORY.md docs/DATA/surveys/LIQUIDATION_FEED_REACHABILITY.md docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_ACCEPTANCE_2026-09-13.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_A_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_B_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_C_HYPERLIQUID_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_D_VENUE_UNIVERSE_2026-09-12.md docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md docs/DATA_CONSUMPTION_LOG.md docs/DELEGATION.md docs/DISCUSSIONS/2026-09-04_postmortem_tp_precursor.md docs/DISCUSSIONS/2026-09-06_data_dependency.md docs/DISCUSSIONS/2026-09-08_external_ecosystem.md docs/DISCUSSIONS/2026-09-08_matilda_intent_vs_test.md docs/DISCUSSIONS/2026-09-09_prereg_deep_dive.md docs/DISCUSSIONS/2026-09-09_the_day_nothing_shipped.md docs/DISCUSSIONS/2026-09-12_docs_reorg_plan.md docs/DISCUSSIONS/2026-09-12_generation_vs_filtering.md docs/DISCUSSIONS/2026-09-12_rules_inventory.md docs/DISCUSSIONS/2026-09-12_rules_reduction_proposal.md docs/DISCUSSIONS/2026-09-13_root_cause.md docs/DISCUSSIONS/2026-09-13_worst_day.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/PLAN.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/README.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/STAGE0_hook_probe.md docs/DISCUSSIONS/2026-09-16_scope_claim_gate_proposal.md docs/DISCUSSIONS/2026-09-18_jev_trade_integration_decision_for_fable_v2.md docs/DISCUSSIONS/2026-09-19_jev_adoption_review.md docs/DISCUSSIONS/2026-09-19_jev_common_module_review.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/A_judgment_points.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/B_failures.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/C_vendor_sources.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/D_study_notes.md docs/INCIDENTS.md docs/INDEX.md docs/JEV.md docs/NEGATIVE_FACTS.md docs/OPERATIONS.md docs/OPERATIONS_JPX.md docs/OWNER_LOG.md docs/OWNER_PROCEDURES.md docs/OWNER_STATUS.md docs/PHASE2/EXEC/EXEC_FLOOR_PREREG.md docs/PHASE2/EXEC/RESULT.md docs/PHASE2/INSTRUMENT_VERIFY/AUDIT_LEDGER_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-16_policy4.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-17_anchor.md docs/PHASE2/K1/AUDIT_TRIAGE.md docs/PHASE2/K1/BINANCE_PLAN.md docs/PHASE2/K1/DEEPDIVE_PLAN.md docs/PHASE2/K1/FRESH_BITFLYER_PREREG.md docs/PHASE2/K1/H1_PREREG.md docs/PHASE2/K1/H2_PREREG.md docs/PHASE2/K1/H3_DECOMP_PREREG.md docs/PHASE2/K1/H3_PREREG.md docs/PHASE2/K1/HANDOFF.md docs/PHASE2/K1/JUDGEMENT_PREREG.md docs/PHASE2/K1/PREFLIGHT.md docs/PHASE2/K1/PREREG.md docs/PHASE2/K1/RESULT.md docs/PHASE2/K1/ROUND5_PREREG.md docs/PHASE2/K1/XVENUE_PREREG.md docs/PHASE2/K1/binance/CHECKS.md docs/PHASE2/O3C/BRANCH_MAP.md docs/PHASE2/O3C/DATA_AVAILABILITY.md docs/PHASE2/O3C/DATA_COLLECTION_2026-09-17.md docs/PHASE2/O3C/INTENT_MAP.md docs/PHASE2/O3C/MISSING_2026-09-17.md docs/PHASE2/O3C/OWNER_INTENT_2026-09-12.md docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/FULL_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_SPLIT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_DRAFT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_R2_PREREG_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RESULT_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RUN12_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/ROWS4_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/SAMPLE_2026-09-17.md docs/PHASE2/O3C/REFRAME/DIFF_2026-09-12.md docs/PHASE2/O3C/REFRAME/LEAD_READING_2026-09-12.md docs/PHASE2/O3C/REFRAME/data_engineer.md docs/PHASE2/O3C/REFRAME/discretionary_trader.md docs/PHASE2/O3C/REFRAME/liquidation_engine.md docs/PHASE2/O3C/REFRAME/market_maker.md docs/PHASE2/O3C/REFRAME/microstructure.md docs/PHASE2/O3C/SIGNAL/CONTINUE_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/CONTINUE_JEV_RUN_NOTE_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE2_DELEGATE_REPORT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/EXPLORE3_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE4_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE5_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/JEV_STATE_PREVIEW_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS2_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW2_2026-09-19.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW3_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW4_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW5_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW6_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW9_2026-09-21.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_RESULT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE1_REPORT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE2_REPORT_2026-09-21.md docs/PHASE2/O3C/STAGE0A_2026-09-14.md docs/PHASE2/O3C/TRIGGER_TRACE.md docs/PROJECT_GOAL.md docs/STRATEGY_IDEAS.md docs/legacy/KATSUO_INTENT_MAP.md docs/legacy/KATSUO_PARAMETER_INVENTORY.md docs/legacy/README.md

## backtest_data(ディレクトリ数)
  147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H_20260905 audit_fetch_JPX_n225f_months_20260906 audit_fetch_JPX_tick_20260906 audit_fetch_P2-08_docs_20260906 audit_fetch_P2-08b_20260906 audit_fetch_bitflyer_history_20260906 audit_fetch_etf_alternatives_20260906 audit_fetch_etf_units_20260906 audit_fetch_micro_fee_20260906 auto_bitflyer_executions_20260905 auto_bitflyer_executions_20260921 auto_oi_snapshots_20260905 auto_oi_snapshots_20260921 auto_okx_long_short_ratio_20260905 auto_okx_open_interest_1h_20260905 auto_okx_open_interest_1h_20260921 auto_okx_open_interest_5m_20260905 auto_okx_open_interest_5m_20260906 auto_okx_open_interest_5m_20260907 auto_okx_open_interest_5m_20260908 auto_okx_open_interest_5m_20260909 auto_okx_open_interest_5m_20260910 auto_okx_open_interest_5m_20260911 auto_okx_open_interest_5m_20260912 auto_okx_open_interest_5m_20260915 auto_okx_open_interest_5m_20260918 auto_okx_open_interest_5m_20260921 auto_venues_20260905 auto_venues_20260921 binance_BTCUSDT_1m.csv binance_BTCUSDT_1m_20170801_20231231 binance_BTCUSDT_1m_20240101_20260831 binance_BTCUSDT_1m_210d_20260820.csv.gz binance_BTCUSDT_1s_20260723_20260906 binance_BTCUSDT_aggTrades_20260723_20260906 binance_BTCUSDT_aggTrades_tardis_days binance_XRPUSDT_1d.csv binance_XRPUSDT_1m.csv binance_XRPUSDT_4h.csv binance_cm_o3c_20260913 binance_cm_o3c_supp_20260917 binance_um_BTCUSDT_aggTrades_20260723_20260906 bitbank_btc_jpy_transactions_monthly_first_days bitbank_xrp_jpy_1m.csv bitflyer_executions_backfill_20260921 bitflyer_executions_us_20260723_20260906 bitflyer_lightchart_BTC_JPY_1m_20260906 bitflyer_lightchart_FX_BTC_JPY_1m_20260906 bitmex_insurance_20260912 bitmex_trade_1s_XBTUSD board_round_20260904 burst_events_20260820 bybit_BTCUSDT_1m_20260910 bybit_reachability_check_20260906 candles_BTC_JPY_20260820.csv candles_ETH_JPY_20260820.csv candles_FX_BTC_JPY_20260820.csv candles_FX_BTC_JPY_30d_20260820.csv candles_FX_BTC_JPY_31d_20260823.csv.gz candles_XRP_JPY_20260820.csv coinalyze_liquidations_20260921 daily_btcusd_bitstamp_20260828.csv.gz daily_btcusd_coinbase_20260828.csv.gz daily_btcusd_yahoo_20260828.csv.gz daily_ethusd_bitstamp_20260828.csv.gz daily_ethusd_coinbase_20260828.csv.gz daily_ethusd_yahoo_20260828.csv.gz executions_FX_BTC_JPY_31d_20260823.csv.gz executions_FX_BTC_JPY_31d_20260908 flow_FX_BTC_JPY_20260820.csv fred_DEXJPUS.csv fred_DFF.csv fred_DGS2.csv fred_IR3TIB01JPM156N.csv fred_IRSTCI01JPM156N.csv fx_btc_jpy_1m_continuous_20260906 fx_event_ticks_2005_2014 fx_event_ticks_2015_2026 fx_fundamentals_20260822 fx_usdjpy_1m_20170801_20221231 fx_usdjpy_1m_20260822.csv.gz gate_liquidations_20260908 gmo_swap_usdjpy.csv jp_factors_20260905 jpx_daily_report_json_20260908 jpx_etf_daily_20260905 jpx_etf_daily_20260906_topix_alt liquidations_repaired_20260912 liquidations_repaired_20260917 mini_topixf_225labo_20260907 n225f_225labo_20260828 nk225_events_20260904 o3c_oi_distance_20260917 o3c_oi_distance_split_20260918 o3c_price_level_band_20260917 o3c_price_level_bundle_first_20260917 o3c_price_level_full_20260917 o3c_price_level_full_20260917_b005 o3c_price_level_full_20260917_b025 o3c_price_level_full_20260917_w72 o3c_price_level_full_20260917_w8 o3c_price_level_rows4_20260917 o3c_price_level_sample_20260917 o3c_price_level_sample_20260917_limitprice o3c_reaction_20260918_anchor o3c_reaction_20260918_anchor_trades o3c_reaction_20260918_anchor_trades_sample o3c_reaction_20260918_anchor_v1_rawcols o3c_reaction_20260918_full o3c_reaction_20260918_judge o3c_reaction_20260918_sample o3c_reaction_20260918_scale12_judgmentdays o3c_signal_continue_20260920 o3c_signal_explore2_20260919 o3c_signal_explore3_20260920 o3c_signal_explore4_20260920 o3c_signal_explore5_20260920 o3c_signal_explore_20260919 o3c_signal_materials_20260920 o3c_signal_policy_20260920 o3c_signal_value_20260921 okx_20260905 okx_btc_lsratio_1h_20260823.csv okx_btc_lsratio_5m_20260823.csv okx_btc_oi_1h_20260823.csv okx_btc_oi_5m_20260823.csv phase2_runs phase2_sealed qa_known_answer_20260905 qa_known_answer_maker3_20260907 qa_known_answer_maker3_v2_20260905 qa_known_answer_maker3_v3_20260905 qa_known_answer_maker4_20260905 qa_known_answer_maker4_r2_20260905 qa_known_answer_maker_20260905 qa_known_answer_steer_20260905 qa_pipeline_daily_20260905 qa_pipeline_daily_20260906 qa_pipeline_taker_20260905 regime_composite_20260901 reit_onr_20260904 storm_events_20260820 topixf_225labo_20260907 venue_survey_20260827 yutai_20260904
```

### 検索計画

**この回は 6 本とも未実行。**リードの起動指定「検索計画 6 本は打ち直しません。前回が残した候補と項目を先に潰します」に従った。委任文 §2 の条件では、残りの候補が空になってから幅と語を変えた 6 本を打つ。今回は残りの候補が空にならなかったので、新しい 6 本には進んでいない。

| 幅 | 日本語クエリ | 英語クエリ | 実行 |
|---|---|---|---|
| 狭い | (未作成) | (未作成) | 未実行(残りの候補が空になっていないため) |
| 中間 | (未作成) | (未作成) | 未実行(同上) |
| 広い | (未作成) | (未作成) | 未実行(同上) |

### 出典

取得日はすべて 2026-09-22。方法はすべて curl(`$HTTPS_PROXY` 経由)で、生ログの行番号を添える。

| URL | 方法 | 生ログの行 |
|---|---|---|
| https://pypi.org/pypi/basana/json | curl | 3 |
| https://pypi.org/pypi/backtrader/json | curl | 5 |
| https://pypi.org/pypi/pysystemtrade/json | curl | 7 |
| https://pypi.org/pypi/pybroker/json | curl | 9 |
| https://pypi.org/pypi/lib-pybroker/json | curl | 11 |
| https://pypi.org/pypi/bt/json | curl | 13 |
| https://pypi.org/pypi/ziplime/json | curl | 15 |
| https://pypi.org/pypi/superalgos/json | curl | 17 |
| https://pypi.org/pypi/opentrader/json | curl | 19 |
| https://pypi.org/pypi/crypto-signal/json | curl | 21 |
| https://pypi.org/pypi/fast-trade/json | curl | 23 |
| https://pypi.org/pypi/OctoBot/json | curl | 37 |
| https://pypi.org/pypi/pybotters/json | curl | 35 |
| https://raw.githubusercontent.com/robcarver17/pysystemtrade/master/LICENSE | curl | 40 |
| https://raw.githubusercontent.com/Superalgos/Superalgos/develop/LICENSE | curl | 42 |
| https://raw.githubusercontent.com/bludnic/opentrader/master/LICENSE | curl | 52 |
| https://raw.githubusercontent.com/CryptoSignal/Crypto-Signal/master/LICENSE | curl | 46 |
| https://raw.githubusercontent.com/Mendl-Labs/BacktestingCore/master/LICENSE | curl | 56 |
| https://raw.githubusercontent.com/Luczinsritter/event_driven_backtesting_engine/main/README.md | curl | 62 |
| https://raw.githubusercontent.com/nkaz001/hftbacktest/master/Cargo.toml | curl | 66 |
| https://raw.githubusercontent.com/nkaz001/hftbacktest/master/connector/Cargo.toml | curl | 64 |
| https://raw.githubusercontent.com/nkaz001/hftbacktest/master/connector/src/main.rs | curl | 68 |
| https://pypi.org/pypi/pyqlib/json | curl | 106 |
| https://raw.githubusercontent.com/microsoft/qlib/main/qlib/config.py | curl | 108 |
| https://raw.githubusercontent.com/microsoft/qlib/main/scripts/dump_bin.py | curl | 110 |
| https://pypi.org/pypi/mlflow/json | curl | 112 |
| https://raw.githubusercontent.com/mlflow/mlflow/master/mlflow/telemetry/constant.py | curl | 114 |
| https://raw.githubusercontent.com/mlflow/mlflow/master/mlflow/telemetry/utils.py | curl | 116 |
| https://raw.githubusercontent.com/jesse-ai/jesse/master/README.md | curl | 118 |
| https://pypi.org/pypi/vnpy_ctastrategy/json | curl | 120 |
| https://raw.githubusercontent.com/QuantConnect/lean-cli/master/README.md | curl | 122 |
| https://raw.githubusercontent.com/DeviaVir/zenbot/unstable/package.json | curl | 124 |
| https://raw.githubusercontent.com/carlos8f/bot18/master/package.json | curl | 126 |
| https://jesse.trade/pricing | curl | 136 |
| https://docs.jesse.trade/docs/livetrade.html | curl | 138 |
| https://pypistats.org/api/packages/jesse/recent | curl | 174 |
| https://pypistats.org/api/packages/lean/recent | python-urllib | 188 |
| https://raw.githubusercontent.com/jesse-ai/jesse/master/LICENSE | curl | 210 |
| https://raw.githubusercontent.com/microsoft/qlib/main/LICENSE | curl | 212 |
| https://raw.githubusercontent.com/QuantConnect/lean-cli/master/LICENSE | curl | 214 |

### 知見

| 知見 | 印 | このプロジェクトへの含意 |
|---|---|---|
| Qlib の必須依存である mlflow は遠隔測定を内蔵し、送信先は config.mlflow-telemetry.io。`MLFLOW_DISABLE_TELEMETRY` で止まる | 一次資料 | Qlib を試すなら、この環境変数を立ててから導入と実行を行う必要がある |
| Qlib 自身の実験管理の既定の保存先は `file:<cwd>/mlruns` のローカルで、databricks 向けの依存は mlflow の extras 側にあり既定では入らない | 一次資料 | 「既定でクラウドに接続する」という懸念のうち、qlib 側は当たらない。当たるのは mlflow の遠隔測定だけ |
| Jesse の本体は MIT だが、実弾とペーパー取引は別売りのプラグインで、逐語「The package is pre-built and the access is limited to those with an active license.」 | 一次資料 | ペーパー運用まで含めて無料ではない。バックテストと最適化だけが鍵なしで動く |
| Jesse のバックテストは postgres も redis も無しで `jesse.research.backtest` から動く | 実測 | 常駐のデータベースを立てずに評価できる |
| Lean CLI はこの環境では最小実行に到達できない。docker のクライアントはあるが daemon の soket が無く、さらに `lean init` が QuantConnect の資格情報を対話で要求する | 実測 | Docker イメージの取得を許しても、資格情報の登録が別に要る。登録はオーナーの判断待ち |
| hftbacktest の実弾コネクタは binancefutures / binancespot / bybit の 3 つ | 一次資料 | 前回 404 だったディレクトリ列挙の代わりに Cargo.toml の features とソースの mod 宣言で裏が取れた。国内取引所は入っていない |
| Mendl-Labs/BacktestingCore のライセンスは Functional Source License 1.1、Luczinsritter の側は README のバッジが MIT を示すが LICENSE ファイルは 404 | 一次資料 | 前者は OSI のオープンソースではない。後者はバッジしか根拠が無い |
| Jesse の wheel に zklink SDK の .dylib が同梱されている | 実測 | 同梱バイナリのある配布であることを記録に残す |
| PyBroker の PyPI 上の名前は lib-pybroker で、ライセンスは Apache License 2.0 with Commons Clause | 一次資料 | Commons Clause が付くので、無償配布だが販売の制限がある |
| pysystemtrade / Superalgos / OpenTrader / CryptoSignal は PyPI に無く、GitHub の LICENSE で一次資料に到達した | 実測 | PyPI の 404 だけで「到達できない」と書いてはならない実例 |

### 候補の一覧

発見順。行頭の `[深掘り]` は §4.0 の表に全項目の行を持つものだけに付ける。それ以外は「浅い」と、何が未確認かを書く。

1. [深掘り] `zipline-reloaded` — Apache-2.0 の日足バックテスト。bundle という単位でデータを封じる。導入から指値の往復まで到達。
2. [深掘り] `Jesse` — MIT の暗号資産バックテスト。実弾とペーパーは別売りのプラグイン。導入から指値の利確まで到達。
3. [深掘り] `VnPy` — MIT。本体と戦略の枠組み vnpy_ctastrategy が別パッケージ。導入から指値の往復まで到達。
4. [深掘り] `Qlib` — MIT。機械学習向けのデータ形式と実験管理。dump_bin での形式変換と読み戻しまで到達。
5. [深掘り] `Lean CLI` — Apache-2.0 の CLI。実行の本体は Docker イメージと QuantConnect の資格情報。この環境では最小実行に到達できない。
6. Basana — 非同期・イベント駆動の暗号資産向け枠組み。Apache-2.0、最新版 1.11、更新 2026-07-22。**浅い**(導入・最小実行・供給網の検査・料金の逐語が未確認。一次資料は PyPI の json のみ)。
7. Backtrader — バックテストの機関。GPLv3+、最新版 1.9.78.123、更新 2023-04-19。**浅い**(同上。更新が 2023 年で止まっていることの裏取りは PyPI の upload_time のみ)。
8. PySystemtrade — PyPI に無し。GitHub の LICENSE は GNU GENERAL PUBLIC LICENSE Version 3。**浅い**(版・更新日・依存・導入・最小実行が未確認。PyPI が 404 のため版の一次資料が取れていない)。
9. PyBroker — PyPI 上の名前は lib-pybroker。Apache License 2.0 with Commons Clause、最新版 2.0.1、更新 2026-08-28。**浅い**(導入・最小実行・Commons Clause の逐語が未確認)。
10. bt — MIT、最新版 1.2.3、更新 2026-09-12。**浅い**(導入・最小実行・供給網の検査が未確認)。
11. Ziplime — 最新版 1.19.16、更新 2026-06-18、PyPI の license 欄が空。**浅い**(ライセンスの一次資料が取れていない。GitHub の所在も未確認)。
12. Superalgos — PyPI に無し。GitHub の LICENSE は Apache License Version 2.0。**浅い**(版・更新日・導入・最小実行が未確認。Node.js 系で pip の経路に無い)。
13. OpenTrader — PyPI に無し。GitHub の master ブランチの LICENSE は Apache License Version 2.0(main ブランチは 404 で、master で取れた)。**浅い**(版・更新日・導入・最小実行が未確認)。
14. CryptoSignal — PyPI に無し(crypto-signal は 404)。GitHub の LICENSE は MIT License、Copyright (c) 2017 Abenezer Mamo。**浅い**(版・更新日・導入・最小実行が未確認)。
15. fast-trade — GNU AGPLv3、最新版 2.1.0、更新 2026-08-20。**浅い**(導入・最小実行・AGPL の再配布の条件が未確認)。
16. OctoBot — GPL-3.0、最新版 2.1.1、更新 2026-03-29。**浅い**(導入・最小実行が未確認。依存が多く、隔離 venv での導入を打っていない)。
17. pybotters — MIT、最新版 1.11.2、更新 2026-04-17。**浅い**(導入・最小実行・対応取引所の一次資料が未確認)。
18. DeviaVir/zenbot — 本家 carlos8f/zenbot の分岐。package.json の name は zenbot4、version 4.1.0、license MIT、engines.node は >=10.0.0。**浅い**(今回新しく当たった分岐で、導入・最小実行・保守の状態が未確認)。
19. Bot18 — carlos8f の後継。package.json の name は bot18、version 0.4.35、説明は「A high-frequency cryptocurrency trading bot by Zenbot creator @carlos8f」。**浅い**(ライセンス欄・導入・最小実行が未確認)。
20. Mendl-Labs/BacktestingCore — master ブランチの LICENSE は Functional Source License, Version 1.1, ALv2 Future License、Copyright 2026 Nwagbara Group, LLC。**浅い**(README の原文・版・導入が未確認)。
21. Luczinsritter/event_driven_backtesting_engine — README の冒頭は「Event‑Driven Backtesting Engine : Tick or Bar level Simulation & Trade Analytics」、バッジは MIT。LICENSE ファイルは main と master のどちらも 404。**浅い**(ライセンスの根拠がバッジだけ。版・導入・最小実行が未確認)。
22. hftbacktest — 1 回目に深掘り済み。今回は実弾コネクタの裏取りだけを足した(binancefutures / binancespot / bybit)。**浅い**(この回の表には行を持たない。1 回目の節を見る)。
23. mlflow — Qlib の必須依存として今回はじめて名前が出た。実験の追跡の道具そのもの。**浅い**(単体での導入・最小実行をしていない。遠隔測定の送信先と無効化の方法だけ一次資料で取った)。

### ツール1件ごとの表

#### §4.0 の機械可読の表

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| `zipline-reloaded` | 版 | 3.1.1 | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(info.version) |
| `zipline-reloaded` | 最終更新日 | 2025-07-19 | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(最新版の upload_time) |
| `zipline-reloaded` | ライセンス | Apache-2.0 | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(info.license_expression) |
| `zipline-reloaded` | 言語と動作環境 | Python >=3.10、この環境は Python 3.11.15 | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(info.requires_python) |
| `zipline-reloaded` | 対応取引所 | 導入後のパッケージ直下に exchange / broker / gateway / connector / live のディレクトリが 1 つも無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:219(find の結果 exch が空) |
| `zipline-reloaded` | 星 | 未確認 | 未確認 | 試したこと: GitHub は curl だと 403。WebFetch での HTML 取得は今回の予算内で打てなかった |
| `zipline-reloaded` | コミット数 | 未確認 | 未確認 | 試したこと: GitHub API は curl で 403。git clone は本体取得になるため §6-6 で打たない |
| `zipline-reloaded` | 保守者数 | 未確認 | 未確認 | 試したこと: PyPI の json には maintainer が 1 名分しか入らない。GitHub の contributors は 403 |
| `zipline-reloaded` | 週DL数 | 未確認 | 未確認 | 試したこと: pypistats.org の recent 端点を curl と python-urllib の 2 回打ち、どちらも HTTP 429 |
| `zipline-reloaded` | 初回公開日 | 2021-03-29 | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(releases の最古 upload_time) |
| `zipline-reloaded` | 既知の脆弱性 | PyPI の vulnerabilities は空 | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(vulnerabilities の長さ 0) |
| `zipline-reloaded` | 料金体系 | Apache-2.0 の無償配布。料金ページに当たるものは PyPI にも project_urls にも無い | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(license_expression と project_urls) |
| `zipline-reloaded` | 無料枠の上限 | 上限の記述なし(自前で走らせる限り課金の口が無い) | 推定 | PyPI の license_expression が Apache-2.0 で、鍵・登録の要求が導入と実行のどちらでも出なかったことからの外挿 |
| `zipline-reloaded` | 課金開始条件 | 該当なし | 推定 | 同上。導入と最小実行のどちらでも鍵・登録を求められなかった |
| `zipline-reloaded` | 隠れた依存 | 相場データは別途。既定の bundle は quandl / quantopian-quandl で、今回は自前の csvdir を登録して回避した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:131(zipline bundles の一覧と ingest) |
| `zipline-reloaded` | 登録の要否 | 不要。鍵なしで導入・ingest・バックテストまで到達 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:135(run_algorithm が完走) |
| `zipline-reloaded` | 到達経路 | PyPI の index から pip install が通る | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:165(pip install の所要と pip check) |
| `zipline-reloaded` | 導入可否 | 可。隔離 venv に導入 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:165(RC=0) |
| `zipline-reloaded` | install所要秒 | 54 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:165(time_s) |
| `zipline-reloaded` | 依存数 | 67 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:165(pkgs) |
| `zipline-reloaded` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:165(pip_check) |
| `zipline-reloaded` | 最小実行の可否 | 可 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:135(rc=0) |
| `zipline-reloaded` | 最小実行の中身 | 合成の日足 118 本で csvdir bundle を登録・ingest し、成行買い 1 回と指値売り 1 回の往復を通した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:135(TXN_COUNT=2) |
| `zipline-reloaded` | 実行所要秒 | 2.30 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:135(time_s) |
| `zipline-reloaded` | wheel展開 | manylinux の wheel を pip download で取得し、中身を列挙した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:193(files の件数) |
| `zipline-reloaded` | setup.py導入時実行 | wheel に setup.py は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:193(setup_py=0) |
| `zipline-reloaded` | 同梱バイナリ | 拡張モジュールの .so を同梱(zipline/_protocol など) | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:193(binaries と例) |
| `zipline-reloaded` | 外部送信 | 導入と最小実行の範囲では外部送信の挙動を観測していない。遠隔測定の有無はソースを読んでいない | 未確認 | 試したこと: 配布物のファイル名の列挙のみ。通信の遮断下での実行や telemetry の語の走査は未実施 |
| `zipline-reloaded` | 自動発注機能 | 導入後のパッケージに発注の経路となるディレクトリが無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:219(exchange/broker/gateway/live が 0) |
| `zipline-reloaded` | 宣伝詐欺の兆候 | 兆候なし。配布は PyPI と GitHub のみで、提携リンクや Telegram 限定配布の記述に当たらなかった | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(project_urls が documentation / homepage / repository の 3 つ) |
| `zipline-reloaded` | 当方データ投入 | 日足の csv を csvdir の形に整えれば入る。当方の csv.gz の約定・清算をそのまま入れる経路は試していない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:133(NYSE の立会日に合わせた csv で ingest が通った) |
| `zipline-reloaded` | 時刻の扱い | 取引所暦(NYSE)に厳密で、暦に無い日付を混ぜると ingest が AssertionError で止まる | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:131(Extra sessions の列挙) |
| `zipline-reloaded` | 再現性 | 同じ bundle と同じアルゴリズムで約定の値が決まる。乱数は当方の合成データ側にしか無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:135(TXN の価格が固定) |
| `zipline-reloaded` | 規模の見積 | 456 日のティックは日足の枠組みに入らない。分足以下は minute bundle が要り、今回は測っていない | 推定 | 日足 118 本の実行時間からの外挿では分足・ティックの規模を出せないため |
| `zipline-reloaded` | 配布元の一致 | PyPI の project_urls の repository が github.com/stefan-jansen/zipline-reloaded を指す | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(project_urls.repository) |
| `zipline-reloaded` | 難読化 | 未確認 | 未確認 | 試したこと: 配布物のアーカイブを開いてファイル名を列挙しただけで、中身の走査は未実施 |
| `zipline-reloaded` | 外部URL取得 | 導入時に実行される setup.py が無いので、導入の段では外部取得が起きない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:193(setup_py=0) |
| `zipline-reloaded` | 依存の一覧 | 導入後の pip list で 67 件 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:165(pkgs) |
| `zipline-reloaded` | 保守者名の一貫性 | PyPI の maintainer は Stefan Jansen、author は Quantopian Inc(元の作者)。repository も stefan-jansen | 一次資料 | https://pypi.org/pypi/zipline-reloaded/json 取得日 2026-09-22(maintainer / author / repository) |
| `zipline-reloaded` | 4軸1_道具 | 入れられる。隔離 venv で導入から指値の往復まで通った | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:135(最小実行の完走) |
| `zipline-reloaded` | 4軸2_情報 | 取引所暦(exchange_calendars)が付いてくる。当方に取引所暦の部品は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:165(依存に exchange-calendars) |
| `zipline-reloaded` | 4軸3_視点 | bundle という「データを封じた単位」で再現する設計。当方の backtest_data の扱いと別 | 推定 | ingest の挙動と bundles の一覧からの外挿 |
| `zipline-reloaded` | 4軸4_向上 | 未確認 | 未確認 | 試したこと: 当方の engine.py との突き合わせは今回の範囲外(リードの判定事項) |
| `Jesse` | 版 | 3.2.1 | 一次資料 | https://pypi.org/pypi/jesse/json 取得日 2026-09-22(info.version) |
| `Jesse` | 最終更新日 | 2026-09-21 | 一次資料 | https://pypi.org/pypi/jesse/json 取得日 2026-09-22(最新版の upload_time) |
| `Jesse` | ライセンス | MIT(本体) | 一次資料 | https://raw.githubusercontent.com/jesse-ai/jesse/master/LICENSE 取得日 2026-09-22(冒頭 MIT License / Copyright (c) 2020 Jesse.Trade) |
| `Jesse` | 言語と動作環境 | Python >=3.10、この環境は Python 3.11.15 | 一次資料 | https://pypi.org/pypi/jesse/json 取得日 2026-09-22(info.requires_python) |
| `Jesse` | 対応取引所 | 導入後のパッケージに exchanges ディレクトリがある。個々の取引所名の列挙は未実施 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:221(exch に exchanges) |
| `Jesse` | 星 | 未確認 | 未確認 | 試したこと: GitHub は curl だと 403。WebFetch は今回の予算内で打てなかった |
| `Jesse` | コミット数 | 未確認 | 未確認 | 試したこと: GitHub API は curl で 403 |
| `Jesse` | 保守者数 | PyPI の author は Saleh Mir 1 名。**maintainer は空**(リードの取り直しで訂正) | 一次資料 | https://pypi.org/pypi/jesse/json 取得日 2026-09-22(info.author = "Saleh Mir"、info.maintainer = null) |
| `Jesse` | 週DL数 | last_week=777、last_month=4768 | 一次資料 | https://pypistats.org/api/packages/jesse/recent 取得日 2026-09-22(recent_downloads) |
| `Jesse` | 初回公開日 | 2020-04-06 | 一次資料 | https://pypi.org/pypi/jesse/json 取得日 2026-09-22(releases の最古 upload_time) |
| `Jesse` | 既知の脆弱性 | PyPI の vulnerabilities は空 | 一次資料 | https://pypi.org/pypi/jesse/json 取得日 2026-09-22(vulnerabilities の長さ 0) |
| `Jesse` | 料金体系 | 本体は MIT で無償。実弾とペーパー取引は別売りのプラグインで、逐語「The package is pre-built and the access is limited to those with an active license.」 | 一次資料 | https://docs.jesse.trade/docs/livetrade.html 取得日 2026-09-22(Installation の段) |
| `Jesse` | 無料枠の上限 | 本体(バックテスト・最適化)は上限の記述なし。実弾・ペーパーは license が要る | 一次資料 | https://docs.jesse.trade/docs/livetrade.html 取得日 2026-09-22(Getting started と Paper Trading の段) |
| `Jesse` | 課金開始条件 | 実弾・ペーパー取引のプラグインを使うとき。逐語「To get started, you need to register on our website to generate your license key.」。金額は取れていない | 一次資料 | https://docs.jesse.trade/docs/livetrade.html 取得日 2026-09-22(Getting started の段) |
| `Jesse` | 隠れた依存 | 本体の実行では postgres / redis が無くても動いた。実弾側は LICENSE_API_TOKEN を .env に置くことを求める | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(research.backtest が DB 無しで完走) |
| `Jesse` | 登録の要否 | バックテストは不要。実弾・ペーパーは登録が要る(渡すもの: jesse.trade のアカウントと API トークン。今回は登録しない) | 一次資料 | https://docs.jesse.trade/docs/livetrade.html 取得日 2026-09-22(Creating a license key の段) |
| `Jesse` | 到達経路 | PyPI の index から pip install が通る | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:167(pip install の所要) |
| `Jesse` | 導入可否 | 可。新しい隔離 venv では依存の衝突が出ない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:167(pip_check) |
| `Jesse` | install所要秒 | 84 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:167(time_s) |
| `Jesse` | 依存数 | 114 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:167(pkgs) |
| `Jesse` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:167(pip_check) |
| `Jesse` | 最小実行の可否 | 可 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(rc=0) |
| `Jesse` | 最小実行の中身 | 合成の 1 分足 300 本を jesse.research.backtest に渡し、成行相当の建玉 1 回と指値の利確 1 回を通した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(TOTAL_TRADES=1) |
| `Jesse` | 実行所要秒 | 2.72 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(time_s) |
| `Jesse` | wheel展開 | 純 Python の wheel を pip download で取得し、中身を列挙した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:195(files の件数) |
| `Jesse` | setup.py導入時実行 | wheel に setup.py は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:195(setup_py=0) |
| `Jesse` | 同梱バイナリ | zklink SDK の .dylib を同梱(jesse/modes/import_candles_mode/drivers/Apex/omni_files 配下) | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:195(binaries と例) |
| `Jesse` | 外部送信 | バックテストの最小実行では外部送信を観測していない。実弾側は license の検証で jesse.trade へ出ると文書が示す | 一次資料 | https://docs.jesse.trade/docs/livetrade.html 取得日 2026-09-22(The package is pre-built and the access is limited to those with an active license.) |
| `Jesse` | 自動発注機能 | ある。exchanges と実弾プラグインの経路を持つ。今回は鍵を要する操作を一切打っていない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:221(exchanges ディレクトリ) |
| `Jesse` | 宣伝詐欺の兆候 | 兆候なし。README に収益の保証の文言は当たらず、配布は PyPI と GitHub | 一次資料 | https://raw.githubusercontent.com/jesse-ai/jesse/master/README.md 取得日 2026-09-22(**リードの取り直しで訂正**: README は 194 行で `premium` `subscription` `guarantee` の出現は 0。収益の保証の文言は無い) |
| `Jesse` | 当方データ投入 | 時刻・始値・終値・高値・安値・出来高の 6 列の配列をそのまま渡せる。当方の約定 csv.gz から足を作れば入る | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(合成の配列をそのまま投入) |
| `Jesse` | 時刻の扱い | ミリ秒のエポックを先頭列に取る | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(合成データの先頭列をミリ秒で作って完走) |
| `Jesse` | 再現性 | 同じ配列と同じ戦略で同じ損益。乱数は当方の合成データ側にしか無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(NET_PROFIT が固定) |
| `Jesse` | 規模の見積 | 456 日のティックを足に直したときの所要は測っていない | 推定 | 300 本の実行時間からの外挿は桁が離れすぎるため数値を出さない |
| `Jesse` | 配布元の一致 | PyPI の project_urls の Source が github.com/jesse-ai/jesse を指す | 一次資料 | https://pypi.org/pypi/jesse/json 取得日 2026-09-22(project_urls.Source) |
| `Jesse` | 難読化 | 未確認 | 未確認 | 試したこと: 配布物のアーカイブを開いてファイル名を列挙しただけで、中身の走査は未実施 |
| `Jesse` | 外部URL取得 | 導入時に実行される setup.py が無いので、導入の段では外部取得が起きない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:195(setup_py=0) |
| `Jesse` | 依存の一覧 | 導入後の pip list で 114 件 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:167(pkgs) |
| `Jesse` | 保守者名の一貫性 | PyPI の author が Saleh Mir、**maintainer は空**(リードの取り直しで訂正)。homepage は jesse.trade | 一次資料 | https://pypi.org/pypi/jesse/json 取得日 2026-09-22(info.author = "Saleh Mir"、info.maintainer = null、project_urls) |
| `Jesse` | 4軸1_道具 | 入れられる。鍵なしでバックテストまで到達 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(最小実行の完走) |
| `Jesse` | 4軸2_情報 | 取引所ごとの手数料・レバレッジ・証拠金の型を持つ。当方に証拠金の模型は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(futures / futures_leverage の設定で完走) |
| `Jesse` | 4軸3_視点 | 戦略を should_long / go_long の状態機械で書かせる。当方の composite と別の切り方 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:137(同じ形で戦略を書いて完走) |
| `Jesse` | 4軸4_向上 | 未確認 | 未確認 | 試したこと: 当方の engine.py との突き合わせは今回の範囲外(リードの判定事項) |
| `VnPy` | 版 | vnpy 4.4.0、vnpy_ctastrategy 1.4.1 | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(info.version と vnpy_ctastrategy の json) |
| `VnPy` | 最終更新日 | vnpy 2026-05-14、vnpy_ctastrategy 2025-12-31 | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(最新版の upload_time) |
| `VnPy` | ライセンス | MIT | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(info.license) |
| `VnPy` | 言語と動作環境 | Python >=3.10、この環境は Python 3.11.15 | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(info.requires_python) |
| `VnPy` | 対応取引所 | 本体のパッケージ直下は alpha / chart / event / rpc / trader だけで、取引所の接続は別パッケージに分かれる | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:223(top の列挙) |
| `VnPy` | 星 | 未確認 | 未確認 | 試したこと: GitHub は curl だと 403 |
| `VnPy` | コミット数 | 未確認 | 未確認 | 試したこと: GitHub API は curl で 403 |
| `VnPy` | 保守者数 | 未確認 | 未確認 | 試したこと: PyPI の json の author と maintainer がどちらも空 |
| `VnPy` | 週DL数 | 未確認 | 未確認 | 試したこと: pypistats.org の recent を curl と python-urllib の 2 回打ち、どちらも HTTP 429 |
| `VnPy` | 初回公開日 | 2017-03-07 | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(releases の最古 upload_time) |
| `VnPy` | 既知の脆弱性 | PyPI の vulnerabilities は空 | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(vulnerabilities の長さ 0) |
| `VnPy` | 料金体系 | MIT の無償配布。PyPI の project_urls は forum と docs で、料金ページに当たるものは無い | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(license と project_urls) |
| `VnPy` | 無料枠の上限 | 上限の記述なし | 推定 | MIT の配布で、導入と最小実行のどちらでも鍵・登録を求められなかったことからの外挿 |
| `VnPy` | 課金開始条件 | 該当なし | 推定 | 同上 |
| `VnPy` | 隠れた依存 | 戦略の枠組みは vnpy 本体と別のパッケージ(vnpy_ctastrategy)で、依存に pandas と plotly を足す | 一次資料 | https://pypi.org/pypi/vnpy_ctastrategy/json 取得日 2026-09-22(requires_dist が pandas / plotly / vnpy>=4.0.0) |
| `VnPy` | 登録の要否 | 不要。鍵なしでバックテストまで到達 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(rc=0) |
| `VnPy` | 到達経路 | PyPI の index から pip install が通る | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:171(pip install の所要) |
| `VnPy` | 導入可否 | 可。vnpy と vnpy_ctastrategy を同じ隔離 venv に導入 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:171(RC=0) |
| `VnPy` | install所要秒 | 48 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:171(time_s) |
| `VnPy` | 依存数 | 45 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:171(pkgs) |
| `VnPy` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:171(pip_check) |
| `VnPy` | 最小実行の可否 | 可 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(rc=0) |
| `VnPy` | 最小実行の中身 | 合成の 1 分足 300 本を BacktestingEngine の history_data に直接入れ、指値買い 1 回と指値売り 1 回の往復を通した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(TRADE_COUNT=2) |
| `VnPy` | 実行所要秒 | 0.72 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(time_s) |
| `VnPy` | wheel展開 | 純 Python の wheel を pip download で取得し、中身を列挙した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:197(files の件数) |
| `VnPy` | setup.py導入時実行 | wheel に setup.py は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:197(setup_py=0) |
| `VnPy` | 同梱バイナリ | 同梱の .so / .dll / .dylib は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:197(binaries=0) |
| `VnPy` | 外部送信 | 最小実行では外部送信を観測していない。データベースの既定の接続先は確かめていない | 未確認 | 試したこと: history_data に直接入れたのでデータベース層を通っていない。設定の既定値は読んでいない |
| `VnPy` | 自動発注機能 | 本体に取引所の接続は入っていない。gateway は別パッケージで、今回は入れていない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:223(exch が空) |
| `VnPy` | 宣伝詐欺の兆候 | 兆候なし。配布は PyPI と GitHub で、project_urls は docs / forum / changelog | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(project_urls) |
| `VnPy` | 当方データ投入 | BarData の列(始値・終値・高値・安値・出来高・時刻)に直せば入る。history_data に直接代入できる | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(合成の BarData を直接代入して完走) |
| `VnPy` | 時刻の扱い | datetime オブジェクトをそのまま取る。タイムゾーンの既定は確かめていない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(naive な datetime で完走) |
| `VnPy` | 再現性 | 同じ足と同じ戦略で同じ約定と同じ損益 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(TOTAL_NET_PNL が固定) |
| `VnPy` | 規模の見積 | 456 日のティックの所要は測っていない | 推定 | 300 本の実行時間からの外挿は桁が離れすぎるため数値を出さない |
| `VnPy` | 配布元の一致 | PyPI の project_urls が github.com/vnpy/vnpy と vnpy.com を指す | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(project_urls.Changes / Homepage) |
| `VnPy` | 難読化 | 未確認 | 未確認 | 試したこと: 配布物のアーカイブを開いてファイル名を列挙しただけで、中身の走査は未実施 |
| `VnPy` | 外部URL取得 | 導入時に実行される setup.py が無いので、導入の段では外部取得が起きない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:197(setup_py=0) |
| `VnPy` | 依存の一覧 | 導入後の pip list で 45 件 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:171(pkgs) |
| `VnPy` | 保守者名の一貫性 | PyPI の author と maintainer が空で、個人名の照合ができない。repository は vnpy 組織 | 一次資料 | https://pypi.org/pypi/vnpy/json 取得日 2026-09-22(author / maintainer が None) |
| `VnPy` | 4軸1_道具 | 入れられる。導入から指値の往復まで通った | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(最小実行の完走) |
| `VnPy` | 4軸2_情報 | 約定ごとの滑りと手数料を rate / slippage / pricetick の形で分けて持つ。当方は費用を一括で扱う | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(set_parameters に rate / slippage / pricetick を与えて完走) |
| `VnPy` | 4軸3_視点 | 戦略と執行を CtaTemplate の状態で切る。当方の composite と別の切り方 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:151(同じ形で戦略を書いて完走) |
| `VnPy` | 4軸4_向上 | 未確認 | 未確認 | 試したこと: 当方の engine.py との突き合わせは今回の範囲外(リードの判定事項) |
| `Qlib` | 版 | pyqlib 0.9.7 | 一次資料 | https://pypi.org/pypi/pyqlib/json 取得日 2026-09-22(info.version) |
| `Qlib` | 最終更新日 | 2025-08-15 | 一次資料 | https://pypi.org/pypi/pyqlib/json 取得日 2026-09-22(最新版の upload_time) |
| `Qlib` | ライセンス | MIT | 一次資料 | https://raw.githubusercontent.com/microsoft/qlib/main/LICENSE 取得日 2026-09-22(冒頭 MIT License / Copyright (c) Microsoft Corporation.) |
| `Qlib` | 言語と動作環境 | Python >=3.8.0、この環境は Python 3.11.15 | 一次資料 | https://pypi.org/pypi/pyqlib/json 取得日 2026-09-22(info.requires_python) |
| `Qlib` | 対応取引所 | 取引所の接続は持たない。パッケージ直下は backtest / cli / contrib / data / model / rl / strategy | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:225(exch が空、top の列挙) |
| `Qlib` | 星 | 未確認 | 未確認 | 試したこと: GitHub は curl だと 403 |
| `Qlib` | コミット数 | 未確認 | 未確認 | 試したこと: GitHub API は curl で 403 |
| `Qlib` | 保守者数 | 未確認 | 未確認 | 試したこと: PyPI の json の author と maintainer がどちらも空 |
| `Qlib` | 週DL数 | 未確認 | 未確認 | 試したこと: pypistats.org の recent を curl と python-urllib の 2 回打ち、どちらも HTTP 429 |
| `Qlib` | 初回公開日 | 2020-09-28 | 一次資料 | https://pypi.org/pypi/pyqlib/json 取得日 2026-09-22(releases の最古 upload_time) |
| `Qlib` | 既知の脆弱性 | PyPI の vulnerabilities は空 | 一次資料 | https://pypi.org/pypi/pyqlib/json 取得日 2026-09-22(vulnerabilities の長さ 0) |
| `Qlib` | 料金体系 | MIT の無償配布。料金ページに当たるものは PyPI にも無い | 一次資料 | https://pypi.org/pypi/pyqlib/json 取得日 2026-09-22(project_urls が空) |
| `Qlib` | 無料枠の上限 | 上限の記述なし | 推定 | MIT の配布で、導入と最小実行のどちらでも鍵・登録を求められなかったことからの外挿 |
| `Qlib` | 課金開始条件 | 該当なし | 推定 | 同上 |
| `Qlib` | 隠れた依存 | mlflow が必須依存に入る。mlflow の databricks 向けの依存は extras 側で、既定では入らない | 一次資料 | https://pypi.org/pypi/mlflow/json 取得日 2026-09-22(requires_dist の databricks 系はすべて extra == \"databricks\") |
| `Qlib` | 登録の要否 | 不要。鍵なしでデータ形式の準備から読み戻しまで到達 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:163(ROWS=120) |
| `Qlib` | 到達経路 | PyPI の index から pip install が通る | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:169(pip install の所要) |
| `Qlib` | 導入可否 | 可。隔離 venv に導入 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:169(RC=0) |
| `Qlib` | install所要秒 | 111 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:169(time_s) |
| `Qlib` | 依存数 | 192 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:169(pkgs) |
| `Qlib` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:169(pip_check) |
| `Qlib` | 最小実行の可否 | 可 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:161(rc=0) |
| `Qlib` | 最小実行の中身 | 合成の日足 120 本の csv を dump_bin.py の dump_all で qlib 形式に変換し、qlib.init と D.features で読み戻した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:161(files=8) |
| `Qlib` | 実行所要秒 | 2.15 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:163(読み戻しの time_s) |
| `Qlib` | wheel展開 | manylinux の wheel を pip download で取得し、中身を列挙した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:199(files の件数) |
| `Qlib` | setup.py導入時実行 | wheel に setup.py は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:199(setup_py=0) |
| `Qlib` | 同梱バイナリ | 拡張モジュールの .so を同梱(qlib/data/_libs の rolling と expanding) | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:199(binaries と例) |
| `Qlib` | 外部送信 | 必須依存の mlflow が遠隔測定を内蔵し、送信先は config.mlflow-telemetry.io。MLFLOW_DISABLE_TELEMETRY で止まる。qlib 自身の実験管理の既定の保存先はローカルの file:<cwd>/mlruns で、クラウドへは向かない | 一次資料 | https://raw.githubusercontent.com/mlflow/mlflow/master/mlflow/telemetry/constant.py 取得日 2026-09-22(CONFIG_URL と、utils.py の MLFLOW_DISABLE_TELEMETRY、qlib/config.py の MLflowSettings.uri) |
| `Qlib` | 自動発注機能 | 無い。取引所の接続を持たない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:225(exch が空) |
| `Qlib` | 宣伝詐欺の兆候 | 兆候なし。配布は PyPI と microsoft/qlib | 一次資料 | https://raw.githubusercontent.com/microsoft/qlib/main/LICENSE 取得日 2026-09-22(Copyright (c) Microsoft Corporation.) |
| `Qlib` | 当方データ投入 | 日付・始値・高値・安値・終値・出来高・factor の列を持つ csv をディレクトリに置けば dump_all が取り込む。ファイル名が銘柄名になる | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:161(qcsv/SYN.csv から syn の bin が出来た) |
| `Qlib` | 時刻の扱い | 日足では日付の文字列。立会日の暦は取り込んだ csv からそのまま作られる | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:161(calendars/day.txt が生成) |
| `Qlib` | 再現性 | 同じ csv から同じ bin が出て、読み戻しの行数も一致 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:163(ROWS=120) |
| `Qlib` | 規模の見積 | 456 日のティックの変換の所要は測っていない | 推定 | 日足 120 本の変換時間からの外挿は桁が離れすぎるため数値を出さない |
| `Qlib` | 配布元の一致 | PyPI の json に project_urls が無く、配布元の照合は LICENSE の Microsoft の表記と README の所在に頼る | 一次資料 | https://pypi.org/pypi/pyqlib/json 取得日 2026-09-22(project_urls が空) |
| `Qlib` | 難読化 | 未確認 | 未確認 | 試したこと: 配布物のアーカイブを開いてファイル名を列挙しただけで、中身の走査は未実施 |
| `Qlib` | 外部URL取得 | 導入時に実行される setup.py が無いので、導入の段では外部取得が起きない。実行時は mlflow の遠隔測定が別問題として残る | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:199(setup_py=0) |
| `Qlib` | 依存の一覧 | 導入後の pip list で 192 件 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:169(pkgs) |
| `Qlib` | 保守者名の一貫性 | PyPI の author と maintainer が空。LICENSE は Microsoft Corporation | 一次資料 | https://pypi.org/pypi/pyqlib/json 取得日 2026-09-22(author / maintainer が None) |
| `Qlib` | 4軸1_道具 | 入れられる。データ形式の準備と読み戻しまで通った | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:163(最小実行の完走) |
| `Qlib` | 4軸2_情報 | 列ごとに固定長の bin に落とす保存形式と、立会日の暦を別ファイルに持つ設計。当方に同じ形式は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:161(features / calendars / instruments の 3 つが生成) |
| `Qlib` | 4軸3_視点 | 実験の記録を mlflow に寄せる設計。当方に実験の追跡の道具は無い(§8 の D) | 一次資料 | https://raw.githubusercontent.com/microsoft/qlib/main/qlib/config.py 取得日 2026-09-22(exp_manager の既定が MLflowExpManager) |
| `Qlib` | 4軸4_向上 | 未確認 | 未確認 | 試したこと: 当方の研究の流れとの突き合わせは今回の範囲外(リードの判定事項) |
| `Lean CLI` | 版 | lean 1.0.229 | 一次資料 | https://pypi.org/pypi/lean/json 取得日 2026-09-22(info.version) |
| `Lean CLI` | 最終更新日 | 2026-08-28 | 一次資料 | https://pypi.org/pypi/lean/json 取得日 2026-09-22(最新版の upload_time) |
| `Lean CLI` | ライセンス | Apache License 2.0 | 一次資料 | https://raw.githubusercontent.com/QuantConnect/lean-cli/master/LICENSE 取得日 2026-09-22(冒頭 Apache License Version 2.0) |
| `Lean CLI` | 言語と動作環境 | Python >=3.9、この環境は Python 3.11.15 | 一次資料 | https://pypi.org/pypi/lean/json 取得日 2026-09-22(info.requires_python) |
| `Lean CLI` | 対応取引所 | commands/live のディレクトリを持つ。接続先の列挙は未実施 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:227(exch に commands/live) |
| `Lean CLI` | 星 | 未確認 | 未確認 | 試したこと: GitHub は curl だと 403 |
| `Lean CLI` | コミット数 | 未確認 | 未確認 | 試したこと: GitHub API は curl で 403 |
| `Lean CLI` | 保守者数 | PyPI の author が QuantConnect(組織名)。**maintainer は空**(リードの取り直しで訂正) | 一次資料 | https://pypi.org/pypi/lean/json 取得日 2026-09-22(info.author = "QuantConnect"、info.maintainer = null) |
| `Lean CLI` | 週DL数 | last_week=2901、last_month=16929 | 一次資料 | https://pypistats.org/api/packages/lean/recent 取得日 2026-09-22(recent_downloads) |
| `Lean CLI` | 初回公開日 | 2021-01-12 | 一次資料 | https://pypi.org/pypi/lean/json 取得日 2026-09-22(releases の最古 upload_time) |
| `Lean CLI` | 既知の脆弱性 | PyPI の vulnerabilities は空 | 一次資料 | https://pypi.org/pypi/lean/json 取得日 2026-09-22(vulnerabilities の長さ 0) |
| `Lean CLI` | 料金体系 | CLI 自身は Apache-2.0 で無償。ただし実行の本体は QuantConnect の Docker イメージで、README の逐語「many commands in the CLI require Docker to run」 | 一次資料 | https://raw.githubusercontent.com/QuantConnect/lean-cli/master/README.md 取得日 2026-09-22(Installation の段) |
| `Lean CLI` | 無料枠の上限 | CLI の導入に上限は無い。クラウド側の枠は今回の範囲で取れていない | 未確認 | 試したこと: PyPI の json と GitHub の README のみ。quantconnect.com の料金ページは開いていない |
| `Lean CLI` | 課金開始条件 | 未確認 | 未確認 | 試したこと: README と PyPI のみ。料金ページの逐語は取っていない |
| `Lean CLI` | 隠れた依存 | Docker が要る。さらに lean init が QuantConnect の API 資格情報(User id とトークン)を対話で求める | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:155(User id: のあと Aborted!) |
| `Lean CLI` | 登録の要否 | 要る。lean init の時点で quantconnect.com のアカウントの User id と API トークンを渡す必要がある(今回は登録しない) | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:155(You can request these credentials on https://www.quantconnect.com/account) |
| `Lean CLI` | 到達経路 | PyPI の index から pip install が通る | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:173(pip install の所要) |
| `Lean CLI` | 導入可否 | 可。CLI そのものは入り、lean --version が動く | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:153(lean 1.0.229) |
| `Lean CLI` | install所要秒 | 21 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:173(time_s) |
| `Lean CLI` | 依存数 | 39 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:173(pkgs) |
| `Lean CLI` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:173(pip_check) |
| `Lean CLI` | 最小実行の可否 | 不可。この環境では到達できない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:149(docker info の Server が空で、unix:///var/run/docker.sock が無い) |
| `Lean CLI` | 最小実行の中身 | 到達できなかった。試した手段: pip install lean で CLI を導入 / lean --version で動作を確認 / lean init を非対話で実行して QuantConnect の資格情報の入力待ちで中断 / docker の有無を確認したところクライアントはあるが daemon の soket が無い。リードの判断により Docker イメージの取得は打たない(委任文 §6-6) | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:155(lean init が Aborted!) |
| `Lean CLI` | 実行所要秒 | 0.80 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:155(lean init の time_s) |
| `Lean CLI` | wheel展開 | 純 Python の wheel を pip download で取得し、中身を列挙した | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:201(files の件数) |
| `Lean CLI` | setup.py導入時実行 | wheel に setup.py は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:201(setup_py=0) |
| `Lean CLI` | 同梱バイナリ | 同梱の .so / .dll / .dylib は無い | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:201(binaries=0) |
| `Lean CLI` | 外部送信 | lean init が quantconnect.com の資格情報を求める設計で、以降の操作は同社のサーバーと Docker イメージに依存する | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:155(credentials は /root/.lean/credentials に保存すると表示) |
| `Lean CLI` | 自動発注機能 | ある。commands/live を持つ。今回は鍵を要する操作を一切打っていない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:227(commands/live) |
| `Lean CLI` | 宣伝詐欺の兆候 | 兆候なし。配布は PyPI と QuantConnect/lean-cli | 一次資料 | https://pypi.org/pypi/lean/json 取得日 2026-09-22(project_urls.Source) |
| `Lean CLI` | 当方データ投入 | 未確認 | 未確認 | 試したこと: lean init が資格情報で止まるため、データの置き場所(data ディレクトリの形)まで到達できていない |
| `Lean CLI` | 時刻の扱い | 未確認 | 未確認 | 試したこと: 最小実行に到達できず、データの形を見ていない |
| `Lean CLI` | 再現性 | 未確認 | 未確認 | 試したこと: 最小実行に到達できず、同じ入力を 2 回通せていない |
| `Lean CLI` | 規模の見積 | 未確認 | 未確認 | 試したこと: 最小実行に到達できず、外挿の元になる測定が無い |
| `Lean CLI` | 配布元の一致 | PyPI の project_urls の Source が github.com/QuantConnect/lean-cli を指す | 一次資料 | https://pypi.org/pypi/lean/json 取得日 2026-09-22(project_urls.Source) |
| `Lean CLI` | 難読化 | 未確認 | 未確認 | 試したこと: 配布物のアーカイブを開いてファイル名を列挙しただけで、中身の走査は未実施 |
| `Lean CLI` | 外部URL取得 | 導入時に実行される setup.py が無いので、導入の段では外部取得が起きない。実行の段は Docker イメージの取得が前提 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:201(setup_py=0) |
| `Lean CLI` | 依存の一覧 | 導入後の pip list で 39 件 | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:173(pkgs) |
| `Lean CLI` | 保守者名の一貫性 | PyPI の author が QuantConnect で、**maintainer は空**(リードの取り直しで訂正)。Source も同名の組織 | 一次資料 | https://pypi.org/pypi/lean/json 取得日 2026-09-22(author / maintainer / project_urls) |
| `Lean CLI` | 4軸1_道具 | この環境には入れられない。CLI は入るが実行の本体に到達しない | 実測 | docs/DATA/probes/20260922_tools_1_run3.log:149(docker daemon の soket が無い) |
| `Lean CLI` | 4軸2_情報 | 未確認 | 未確認 | 試したこと: 最小実行に到達できず、取れる情報の形を見ていない |
| `Lean CLI` | 4軸3_視点 | 未確認 | 未確認 | 試したこと: 最小実行に到達できず、分析の視点を見ていない |
| `Lean CLI` | 4軸4_向上 | 未確認 | 未確認 | 試したこと: 最小実行に到達できず、比較の材料が無い |

#### 17. zipline-reloaded(深掘り)

- **できること**: 日足の bundle を登録して取り込み、アルゴリズムを走らせる。成行と指値の両方の注文形式を持つ。取引所暦を exchange_calendars から取る。
- **料金の構造**: Apache-2.0 の無償配布。鍵も登録も要らなかった。相場データは自分で用意する。
- **到達・導入・実行の記録**: PyPI から pip install が通り、隔離 venv で `pip check` が通った。合成の日足で csvdir bundle を登録し、最初の取り込みは NYSE の暦に無い 4 日を混ぜていたため AssertionError で止まった。立会日に合わせ直して取り込みが通り、成行買いと指値売りの往復で損益が出た。
- **当方の用途との相性**: 日足の csv は入る。分足以下は minute bundle が要り、今回は測っていない。約定の値は入力で決まるので再現性がある。
- **当方に無いもの**: 取引所暦の部品、bundle という「取り込んだデータを封じる」単位。
- **危険**: wheel に setup.py が無く、導入時に実行されるものが無い。拡張モジュールの .so を同梱する。発注の経路になるディレクトリは持たない。

#### 18. Jesse(深掘り)

- **できること**: 暗号資産の足でバックテストと最適化。戦略を状態機械の形で書く。実弾とペーパーは別売りのプラグイン。
- **料金の構造**: 本体は MIT。実弾・ペーパーは逐語「The package is pre-built and the access is limited to those with an active license.」で、jesse.trade のアカウントと API トークンが要る。**金額は取れていない**(jesse.trade/pricing は curl で HTTP 403、WebFetch でも HTTP 403。docs 側には金額の記載が見つからなかった)。登録に何を渡すかは、文書上はアカウントの作成とトークンの発行までしか書かれていない。
- **到達・導入・実行の記録**: 新しい隔離 venv を作り直したところ、2 回目の実行で起きた numpy の依存の衝突は出ず `pip check` が通った。合成の 1 分足を `jesse.research.backtest` に渡し、postgres も redis も立てずに建玉と利確を通した。
- **当方の用途との相性**: 時刻はミリ秒のエポック。当方の約定から足を作れば入る。同じ入力で同じ損益が出る。
- **当方に無いもの**: 証拠金とレバレッジの模型、取引所ごとの手数料の型。
- **危険**: wheel に zklink SDK の .dylib を同梱する。実弾側は license の検証で外部へ出る設計。今回は鍵を要する操作を一切打っていない。

#### 19. VnPy(深掘り)

- **できること**: 本体が事象の枠組みと売買の型を持ち、戦略の枠組み・取引所の接続はそれぞれ別パッケージに分かれる。
- **料金の構造**: MIT の無償配布。料金ページに当たるものは PyPI の project_urls に無い。
- **到達・導入・実行の記録**: vnpy と vnpy_ctastrategy を同じ隔離 venv に入れ、`pip check` が通った。合成の 1 分足を BacktestingEngine の history_data に直接入れ、データベースを立てずに指値の往復を通した。
- **当方の用途との相性**: BarData の列に直せば入る。手数料・滑り・呼値を別々に与えられる。
- **当方に無いもの**: 滑りと呼値を費用と分けて持つ設計。
- **危険**: wheel に setup.py も同梱バイナリも無い。本体だけでは発注の経路を持たない。PyPI の author と maintainer が空で、保守者名の照合ができない。

#### 20. Qlib(深掘り)

- **できること**: 列ごとに固定長の bin へ落とす保存形式、立会日の暦、機械学習の模型と強化学習の部品、mlflow による実験の追跡。
- **料金の構造**: MIT の無償配布。
- **到達・導入・実行の記録**: 隔離 venv に導入して `pip check` が通った。`scripts/dump_bin.py` を取ってきて合成の日足の csv を dump_all で変換し、features・calendars・instruments の 3 つが出来た。`qlib.init` と `D.features` で読み戻して行数が一致した。引数の名前は `--data_path` で、最初に打った `--csv_path` は使い方の表示で止まった。
- **当方の用途との相性**: 日付と 6 列の csv を置けば取り込む。ファイル名が銘柄名になる。
- **当方に無いもの**: 実験の追跡の道具(§8 の D で「無い」と記録したもの)、列ごとの固定長の保存形式。
- **危険**: 必須依存の mlflow が遠隔測定を内蔵する。送信先は config.mlflow-telemetry.io で、`MLFLOW_DISABLE_TELEMETRY` で止まる。qlib 自身の実験管理の既定はローカルの `file:<cwd>/mlruns` で、databricks 向けの依存は mlflow の extras 側にあり既定では入らない。

#### 21. Lean CLI(深掘り。この環境では最小実行に到達できない)

- **できること**: 手元の計画を作り、バックテスト・最適化・実弾を QuantConnect の Docker イメージの中で走らせる。
- **料金の構造**: CLI 自身は Apache-2.0。README の逐語「many commands in the CLI require Docker to run」。クラウド側の料金の逐語は取っていない。
- **到達・導入・実行の記録(試した手段の一覧)**: (1) PyPI から pip install が通り、`lean --version` が版を表示した。(2) `lean init --language python` を打つと QuantConnect の資格情報(User id と API トークン)の入力待ちになり、非対話の殻なので中断した。表示の逐語は「You can request these credentials on https://www.quantconnect.com/account」。(3) docker の有無を見たところ、クライアントは入っているが `docker info` の Server が空で、`unix:///var/run/docker.sock` が存在しないため daemon に繋がらない。(4) **リードの判断により Docker イメージの取得は打たない**(委任文 §6-6 の数百 MB 以上の一括ダウンロードの禁止)。
- **この環境から不可の結論**: 上の 4 つを試して到達できなかった。**第 2 経路(オーナー PC)でそのまま打てる手順**: `pip install lean` → Docker Desktop を起動 → `lean login`(quantconnect.com の User id と API トークンを入力)→ `lean init` → `lean create-project --language python Test` → `lean backtest Test`。登録に渡すものはメールアドレスとパスワード。**登録はこちらでは行わない。**
- **当方に無いもの**: 実行環境そのものを画像として固定する設計。
- **危険**: 資格情報を `/root/.lean/credentials` に保存する。実弾の経路 `commands/live` を持つ。今回は鍵を要する操作を一切打っていない。

### A と B の結果

| 項目 | 結果 |
|---|---|
| A 未着手の候補 12 件 | 全件について一次資料(PyPI の json か GitHub の LICENSE)に到達した。ただし**深掘りは 1 件もしていない**。導入・最小実行・供給網の検査・料金の逐語が未確認で、候補の一覧では「浅い」と印を付けた |
| B-1 zipline-reloaded の最小実行 | 完了。bundle の登録・取り込み・成行買いと指値売りの往復まで |
| B-2 Qlib の最小実行 | 完了。dump_bin による形式の変換と読み戻しまで |
| B-3 VnPy の最小実行 | 完了。vnpy_ctastrategy を足して指値の往復まで |
| B-4 Jesse の最小実行 | 完了。隔離 venv を作り直し、依存の衝突は出なかった |
| B-5 Lean CLI の最小実行 | 到達できず。試した手段の一覧と第 2 経路の手順を上に書いた |
| B-6 Zenbot 本家・Bot18 の Node.js 環境での導入 | **未着手**。package.json だけ取った。node と npm はこの環境に入っている |
| B-7 Mendl-Labs / Luczinsritter の LICENSE と README | 完了。前者は Functional Source License 1.1、後者は LICENSE が 404 で README のバッジが MIT |
| B-8 Jesse のプレミアムの逐語の裏取り | 部分的に完了。逐語は取れたが**金額は取れていない**(料金ページが HTTP 403) |
| B-9 Qlib の mlflow / databricks-sdk がクラウドに繋ぐか | 完了。qlib 側の既定はローカル。mlflow の遠隔測定だけが外へ出る。databricks-sdk は必須依存ではない |
| B-10 hftbacktest の対応取引所をソースで裏取り | 完了。Cargo.toml の features と main.rs の mod 宣言で binancefutures / binancespot / bybit |
| B-11 A の 12 候補の一次資料への到達 | 完了 |

### 残りの候補名

次回の実行に渡す。深掘りが済んでいないもの。

- Basana / Backtrader / PySystemtrade / PyBroker(lib-pybroker) / bt / Ziplime / Superalgos / OpenTrader / CryptoSignal / fast-trade / OctoBot / pybotters
- DeviaVir/zenbot(今回の新規) / Bot18 / Zenbot 本家の Node.js 導入
- Mendl-Labs/BacktestingCore / Luczinsritter/event_driven_backtesting_engine
- mlflow(今回の新規。Qlib の必須依存として名前が出た)

### STRATEGY_IDEAS.md 向け候補(提案のみ、未マージ)

- 指値の埋まり方を別実装と突き合わせる相手として、zipline-reloaded・VnPy・Jesse の 3 つがそれぞれ別の約定の決め方を持つ。

### DATA.md 向け候補(提案のみ、未マージ)

- Qlib の保存形式(列ごとの固定長 bin + 立会日の暦 + 銘柄の一覧)は、当方の backtest_data の恒久スナップショットと別の形。

### 予算

| 項目 | 値 |
|---|---|
| 実時間 | 20 分の上限を超えた。上限に達した時点で新しい探索は止め、書き出しに移った |
| トークン | 5 万の上限に近い。正確な消費はこちらから読めない |
| 中断の扱い | **未完了**。区分 1 の完了条件(残りの候補が空で、新しい検索計画が新しい候補を 1 件も出さない)を満たしていない |

### 受け入れ検査の出力

リードが受領後に打ち直した出力(委任文 §12「リードは報告を受け取った直後に、同じコマンドを自分で打ち直す」)。
調査班が残した 2 件の判定と、それを受けた検査側の直しは `docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run3.md`。

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
---- 検査対象の合計 0 件(K12 を除く。貼り付けはこの数で照合する)
---- 合計 1 件
```


## 区分1 — 4 回目の実行(2026-09-22)

委任文: `docs/DATA/delegations/20260922_tools_survey_prompt.md@ce0012c95154`。生ログ: `docs/DATA/probes/20260922_tools_1_run4.log`。
3 回目のリードの検収(`docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run3.md`)で見つかった 2 つの型
(PyPI の `info.maintainer` と `info.author` の取り違え / 根拠に資料に無い語を書く)を避けるため、この回の表では
**どのフィールドを見たかを根拠の欄に `info.author = "…"` の形で書き、語や件数はその場で数えた値だけを書いた。**

### 当方の道具立て(`python3 scripts/tools_inventory.py` の出力全文。§8)

```
# 当方の道具立て(git ls-files から生成。2026-09-22T06:58:25Z、HEAD 9035212。コマンド: python3 scripts/tools_inventory.py)

## src/bot(package: ファイル数 / ファイル名)
- src/bot: 7 / atomic_file.py constants.py logging_setup.py main.py products.py radar.py settings.py
- src/bot/backtest: 3 / engine.py metrics.py walk_forward.py
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
- check_*: 8 / check_api.py check_data_ledger.py check_k1_binance.py check_k1_bitflyer_data.py check_kabu_api.py check_liquidation_feeds.py check_liquidation_history_depth.py check_scan_report.py
- build_*: 7 / build_basis.py build_bitflyer_lightchart_csv.py build_burst_library.py build_flow.py build_fx_event_library.py build_fx_event_library_2005_2014.py build_storm_library.py
- record_*: 5 / record_funding_basis.py record_liquidations.py record_oi.py record_realtime.py record_venues.py
- jev/: 3 / client.py redact.py schemas.py
- verify_*: 3 / verify_gates.py verify_liq_instrument.py verify_snapshots.py
- (単発): 2 / _research_audit_gate.py dashboard.py
- judge_*: 2 / judge_board_round.py judge_gates.py
- k1_*: 2 / k1_binance_data_quality.py k1_source.py
- paper_*: 2 / paper_on1.py paper_onr.py
- repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.py
- constants_*: 1 / constants_inventory.py
- data_*: 1 / data_quality.py
- explore_*: 1 / explore_o3c_oi_axis.py
- extract_*: 1 / extract_tape.py
- intake_*: 1 / intake_ledger.py
- liquidation_*: 1 / liquidation_report.py
- mirror_*: 1 / mirror_bitmex_archive.py
- normalize_*: 1 / normalize_bitflyer_executions.py
- phase2_*: 1 / phase2_seal.py
- preflight_*: 1 / preflight_prereg.py
- probe_*: 1 / probe_api_latency.py
- replay_*: 1 / replay_scalp_storm.py
- retention_*: 1 / retention_snapshot.py
- tools_*: 1 / tools_inventory.py
- tp_*: 1 / tp_operating_curve.py
- trace_*: 1 / trace_metrics.py
- validate_*: 1 / validate_composite.py
- x_*: 1 / x_fetch.py
- (.py 以外の scripts: 3 = scripts/fetch_all.sh scripts/install_git_hooks.sh scripts/regen_hook_manifest.sh)

## config: 32
  config/composite.yaml config/config.yaml config/constants.yaml config/etf_measure.yaml config/jev_delegation_tiers.yaml config/jev_design_examples/o3c_covariates.yaml config/jev_design_examples/o3c_observables.yaml config/jev_design_examples/signal2_covariates.yaml config/jev_design_examples/signal2_observables.yaml config/jev_design_examples/signal3_covariates.yaml config/jev_design_examples/signal3_observables.yaml config/jev_design_examples/signal4_covariates.yaml config/jev_design_examples/signal4_observables.yaml config/jev_design_examples/signal5_covariates.yaml config/jev_design_examples/signal5_observables.yaml config/jev_design_examples/signal6_covariates.yaml config/jev_design_examples/signal6_observables.yaml config/jev_design_examples/signal7_observables.yaml config/jev_design_examples/signal8_covariates.yaml config/jev_design_examples/signal8_observables.yaml config/jev_design_examples/signal8_observables_independent.yaml config/jev_design_examples/signal_covariates.yaml config/jev_design_examples/signal_observables.yaml config/jev_routes.yaml config/o3c_jev_state_bands.yaml config/o3c_signal_logit_chain.yaml config/o3c_signal_logit_first.yaml config/o3c_signal_logit_value_chain.yaml config/o3c_signal_logit_value_first.yaml config/on1_live.yaml config/products.yaml config/risk_limits.yaml

## deploy: 19
  deploy/bitflyer-bot.service deploy/bitflyer-fetch.service deploy/bitflyer-fetch.timer deploy/check_liq_recorder.bat deploy/etf_measure_entry.bat deploy/etf_measure_exit.bat deploy/fetch_all.bat deploy/mirror_bitmex.bat deploy/nightly_restart.bat deploy/on1_entry.bat deploy/on1_exit.bat deploy/probe_latency.bat deploy/reset_kill.bat deploy/restart_all.bat deploy/run_paper.bat deploy/setup.sh deploy/share_logs.bat deploy/start_all.bat deploy/stop_all.bat

## tests(ファイル): 139
  tests/conftest.py tests/fixtures/jev_ops/decisions.json tests/fixtures/jev_ops/notifications.jsonl tests/fixtures/jev_ops/status_page.html tests/test_app_fx_integration.py tests/test_audit_gates_wired.py tests/test_backtest.py tests/test_bitmex_mirror.py tests/test_board.py tests/test_board_round.py tests/test_board_walk.py tests/test_bot_research_overnight.py tests/test_build_flow.py tests/test_check_data_ledger.py tests/test_client.py tests/test_clock_burst.py tests/test_composite.py tests/test_constants.py tests/test_constants_inventory.py tests/test_dashboard.py tests/test_data_quality.py tests/test_data_quality_incremental.py tests/test_deploy.py tests/test_engine_maker_exit.py tests/test_etf_measure.py tests/test_extract_tape.py tests/test_fetch_backfill_scripts.py tests/test_fetch_binance_daily.py tests/test_fetch_binance_vision.py tests/test_fetch_history_candles.py tests/test_gz_members.py tests/test_intake_ledger.py tests/test_intent_map_rule.py tests/test_jev_audit_eval.py tests/test_jev_audit_loop.py tests/test_jev_check.py tests/test_jev_client.py tests/test_jev_delegate.py tests/test_jev_design.py tests/test_jev_ideas.py tests/test_jev_ops.py tests/test_jev_owner_log.py tests/test_jev_redact.py tests/test_jev_reply.py tests/test_jev_report_intake.py tests/test_jev_schemas.py tests/test_jev_scripts.py tests/test_jev_survey.py tests/test_jev_trace_export.py tests/test_judge_gates.py tests/test_k1_bitflyer_source.py tests/test_k1_bybit_source.py tests/test_k1_delay_decomp.py tests/test_k1_delay_entry.py tests/test_k1_flip_body.py tests/test_k1_lookahead.py tests/test_k1_no_invalidation.py tests/test_k1_round5.py tests/test_k1_seal_guard.py tests/test_k1_xvenue.py tests/test_liq_bands.py tests/test_liq_response.py tests/test_liq_response_dedup.py tests/test_liquidation_reader.py tests/test_maker_execution.py tests/test_market_data.py tests/test_market_view.py tests/test_max_hold.py tests/test_modes.py tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_ext.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_rows4.py tests/test_o3c_signal_calib.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore2.py tests/test_o3c_signal_explore3.py tests/test_o3c_signal_explore4.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_policy.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_on1_forward.py tests/test_on1_live.py tests/test_onr.py tests/test_onr_forward.py tests/test_orders.py tests/test_paper_state.py tests/test_phase2_p2_01.py tests/test_phase2_p2_01_final.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_phase2_p2_03.py tests/test_phase2_p2_03_final.py tests/test_phase2_p2_03_iter2.py tests/test_phase2_p2_04.py tests/test_phase2_seal.py tests/test_portfolio_and_strategy.py tests/test_position_ladder.py tests/test_preflight_prereg.py tests/test_probe_api_latency.py tests/test_qa_make_known_answer.py tests/test_qa_make_known_answer_maker.py tests/test_qa_make_known_answer_maker3.py tests/test_qa_make_known_answer_steer.py tests/test_qa_maker_fill_ref.py tests/test_qa_pipeline_known_answer.py tests/test_qa_score_audit.py tests/test_radar.py tests/test_realtime_recorder.py tests/test_record_funding_basis.py tests/test_record_liquidations.py tests/test_record_liquidations_writer.py tests/test_record_venues.py tests/test_repair_gz_listing.py tests/test_research_protocol_rules.py tests/test_resilience.py tests/test_retention_snapshot.py tests/test_risk.py tests/test_scalp_logic.py tests/test_sealed_load_diagnostic.py tests/test_sealed_ts_us.py tests/test_short_margin.py tests/test_tp_sl.py tests/test_verify_snapshots.py tests/test_wick_stop.py tests/test_x_fetch.py tests/test_xborder.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_fx.py tests/test_xborder_p2_known_answer.py tests/test_xborder_p2_state.py

## .claude/hooks: 8
  .claude/hooks/_verify_manifest.sh .claude/hooks/delegation_audit_gate.sh .claude/hooks/deny_protected_paths.sh .claude/hooks/jev_notice.sh .claude/hooks/owner_options_gate.sh .claude/hooks/owner_turn_digest.sh .claude/hooks/session_start_digest.sh .claude/hooks/trace_snapshot.sh

## .claude/agents: 3
  .claude/agents/owner-auditor-candidate.md .claude/agents/owner-auditor.md .claude/agents/owner-model-auditor.md

## .claude/skills: 9
  .claude/skills/delegated-study/SKILL.md .claude/skills/owner-audit/SKILL.md .claude/skills/owner-options/SKILL.md .claude/skills/owner-procedure/SKILL.md .claude/skills/research-protocol/SKILL.md .claude/skills/research-squad/SKILL.md .claude/skills/typesafe-ai/LICENSE .claude/skills/typesafe-ai/SKILL.md .claude/skills/x-research/SKILL.md

## githooks: 1
  githooks/pre-push

## docs(.md): 295
  docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11_control_review.md docs/AUDITOR/EVAL_2026-09-11b.md docs/AUDITOR/IMPROVEMENT.md docs/AUDITOR/JEV/LABELS_NOTES_2026-09-19.md docs/AUDITOR/JEV/PREREG_2026-09-19.md docs/AUDITOR/KNOWN_ANSWERS.md docs/AUDITOR/KNOWN_ANSWERS_ADDENDUM.md docs/AUDITOR/OWNER_MODEL_SOURCE.md docs/AUDITOR/PRINCIPLES.md docs/AUDITOR/PROCESS_METRICS.md docs/AUDITOR/PROPOSED_CHANGES_2026-09-11.md docs/AUDITOR/READDO/audit_stop.md docs/AUDITOR/READDO/before_unseal.md docs/AUDITOR/READDO/owner_objection.md docs/AUDITOR/READDO/push_blocked.md docs/AUDITOR/READDO/repeat_defect.md docs/AUDITOR/TREND.md docs/AUDITOR/VERDICTS/2026-09-11_k1_closure_entries.md docs/AUDITOR/VERDICTS/2026-09-11_proposed_changes_and_eval_b.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_execution.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_plan.md docs/AUDITOR/VERDICTS/2026-09-12_o3c_reframe_reading.md docs/AUDITOR/VERDICTS/2026-09-12_p14_liquidation_fix.md docs/AUDITOR/VERDICTS/2026-09-12_p4n_nightly_restart.md docs/AUDITOR/VERDICTS/2026-09-12_rules_reduction.md docs/AUDITOR/VERDICTS/2026-09-16_policy4_report.md docs/AUDITOR/VERDICTS/2026-09-17_anchor_report.md docs/AUDITOR/VERDICTS/2026-09-17_closure.md docs/AUDITOR/VERDICTS/2026-09-17_data_collection.md docs/AUDITOR/VERDICTS/2026-09-17_missing.md docs/AUDITOR/VERDICTS/2026-09-17_oi_distance.md docs/AUDITOR/VERDICTS/2026-09-17_price_level.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_ext.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_full.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_rows4.md docs/AUDITOR/VERDICTS/2026-09-18_oi_distance_split.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_design.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r10.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r2.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r3.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r4.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r5.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r6.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r7.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r8.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r9.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_run12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r11.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_r2_prereg.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r2.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r3.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_result.md docs/AUDITOR/VERDICTS/2026-09-19_signal_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_report.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_materials_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_result.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_design.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_result.md docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md docs/AUDITOR/VERDICTS/2026-09-21_tools_survey_prompt.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run2.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run3.md docs/AUDITOR/VERDICTS/2026-09-22_tools_survey_prompt_v12.md docs/AUDITOR/VERDICTS/README.md docs/AUDITOR/answers/KA-01.md docs/AUDITOR/answers/KA-02.md docs/AUDITOR/answers/KA-04.md docs/AUDITOR/answers/KA-05.md docs/AUDITOR/answers/KA-06.md docs/AUDITOR/answers/KA-07.md docs/AUDITOR/answers/KA-08.md docs/AUDITOR/answers/KA-09.md docs/AUDITOR/answers/KA-10.md docs/AUDITOR/answers/KA-16.md docs/AUDITOR/answers/KA-17.md docs/AUDITOR/answers/KA-18.md docs/AUDITOR/answers/KA-19.md docs/AUDITOR/answers/KA-20.md docs/AUDITOR/answers/KA-21.md docs/AUDITOR/answers/KA-22.md docs/AUDITOR/answers/KA-23.md docs/AUDITOR/answers/KA-24.md docs/AUDITOR/answers/KA-25.md docs/AUDITOR/answers/KA-26.md docs/AUDITOR/answers/KA-27.md docs/AUDITOR/answers/KA-28.md docs/AUDITOR/before/HYGIENE_2026-09-11.md docs/AUDITOR/before/KA-01.md docs/AUDITOR/before/KA-02.md docs/AUDITOR/before/KA-04.md docs/AUDITOR/before/KA-05.md docs/AUDITOR/before/KA-06.md docs/AUDITOR/before/KA-07.md docs/AUDITOR/before/KA-08.md docs/AUDITOR/before/KA-09.md docs/AUDITOR/before/KA-10.md docs/AUDITOR/before/KA-16.md docs/AUDITOR/before/KA-17.md docs/AUDITOR/before/KA-18.md docs/AUDITOR/before/KA-19.md docs/AUDITOR/before/KA-20.md docs/AUDITOR/before/KA-21.md docs/AUDITOR/before/KA-22.md docs/AUDITOR/before/KA-23.md docs/AUDITOR/before/KA-24.md docs/AUDITOR/before/KA-25.md docs/AUDITOR/before/KA-26.md docs/AUDITOR/before/KA-27.md docs/AUDITOR/before/KA-28.md docs/DATA.md docs/DATA/SCAN_2026-09-16.md docs/DATA/SCAN_2026-09-21_tools.md docs/DATA/delegations/20260919_o3c_signal_explore2_prompt.md docs/DATA/delegations/20260920_o3c_cascade_read_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_jev_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore3_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore4_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore5_prompt.md docs/DATA/delegations/20260920_o3c_signal_jev_state_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials2_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_stage2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_tp_prompt.md docs/DATA/delegations/20260921_tools_survey_prompt.md docs/DATA/delegations/20260922_tools_survey_prompt.md docs/DATA/probes/20260913_liquidation_integrity.md docs/DATA/probes/20260919_reaction_prereg_outputs.md docs/DATA/probes/20260920_o3c_cascade_read.md docs/DATA/probes/20260920_o3c_materials_read.md docs/DATA/surveys/BINANCE_CM_MMR_2026-09-17.md docs/DATA/surveys/BITFLYER_HISTORY_SOURCES.md docs/DATA/surveys/ETF_ALTERNATIVES.md docs/DATA/surveys/G2_DATA_INVENTORY.md docs/DATA/surveys/LIQUIDATION_FEED_REACHABILITY.md docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_ACCEPTANCE_2026-09-13.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_A_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_B_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_C_HYPERLIQUID_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_D_VENUE_UNIVERSE_2026-09-12.md docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md docs/DATA_CONSUMPTION_LOG.md docs/DELEGATION.md docs/DISCUSSIONS/2026-09-04_postmortem_tp_precursor.md docs/DISCUSSIONS/2026-09-06_data_dependency.md docs/DISCUSSIONS/2026-09-08_external_ecosystem.md docs/DISCUSSIONS/2026-09-08_matilda_intent_vs_test.md docs/DISCUSSIONS/2026-09-09_prereg_deep_dive.md docs/DISCUSSIONS/2026-09-09_the_day_nothing_shipped.md docs/DISCUSSIONS/2026-09-12_docs_reorg_plan.md docs/DISCUSSIONS/2026-09-12_generation_vs_filtering.md docs/DISCUSSIONS/2026-09-12_rules_inventory.md docs/DISCUSSIONS/2026-09-12_rules_reduction_proposal.md docs/DISCUSSIONS/2026-09-13_root_cause.md docs/DISCUSSIONS/2026-09-13_worst_day.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/PLAN.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/README.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/STAGE0_hook_probe.md docs/DISCUSSIONS/2026-09-16_scope_claim_gate_proposal.md docs/DISCUSSIONS/2026-09-18_jev_trade_integration_decision_for_fable_v2.md docs/DISCUSSIONS/2026-09-19_jev_adoption_review.md docs/DISCUSSIONS/2026-09-19_jev_common_module_review.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/A_judgment_points.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/B_failures.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/C_vendor_sources.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/D_study_notes.md docs/INCIDENTS.md docs/INDEX.md docs/JEV.md docs/NEGATIVE_FACTS.md docs/OPERATIONS.md docs/OPERATIONS_JPX.md docs/OWNER_LOG.md docs/OWNER_PROCEDURES.md docs/OWNER_STATUS.md docs/PHASE2/EXEC/EXEC_FLOOR_PREREG.md docs/PHASE2/EXEC/RESULT.md docs/PHASE2/INSTRUMENT_VERIFY/AUDIT_LEDGER_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-16_policy4.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-17_anchor.md docs/PHASE2/K1/AUDIT_TRIAGE.md docs/PHASE2/K1/BINANCE_PLAN.md docs/PHASE2/K1/DEEPDIVE_PLAN.md docs/PHASE2/K1/FRESH_BITFLYER_PREREG.md docs/PHASE2/K1/H1_PREREG.md docs/PHASE2/K1/H2_PREREG.md docs/PHASE2/K1/H3_DECOMP_PREREG.md docs/PHASE2/K1/H3_PREREG.md docs/PHASE2/K1/HANDOFF.md docs/PHASE2/K1/JUDGEMENT_PREREG.md docs/PHASE2/K1/PREFLIGHT.md docs/PHASE2/K1/PREREG.md docs/PHASE2/K1/RESULT.md docs/PHASE2/K1/ROUND5_PREREG.md docs/PHASE2/K1/XVENUE_PREREG.md docs/PHASE2/K1/binance/CHECKS.md docs/PHASE2/O3C/BRANCH_MAP.md docs/PHASE2/O3C/DATA_AVAILABILITY.md docs/PHASE2/O3C/DATA_COLLECTION_2026-09-17.md docs/PHASE2/O3C/INTENT_MAP.md docs/PHASE2/O3C/MISSING_2026-09-17.md docs/PHASE2/O3C/OWNER_INTENT_2026-09-12.md docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/FULL_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_SPLIT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_DRAFT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_R2_PREREG_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RESULT_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RUN12_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/ROWS4_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/SAMPLE_2026-09-17.md docs/PHASE2/O3C/REFRAME/DIFF_2026-09-12.md docs/PHASE2/O3C/REFRAME/LEAD_READING_2026-09-12.md docs/PHASE2/O3C/REFRAME/data_engineer.md docs/PHASE2/O3C/REFRAME/discretionary_trader.md docs/PHASE2/O3C/REFRAME/liquidation_engine.md docs/PHASE2/O3C/REFRAME/market_maker.md docs/PHASE2/O3C/REFRAME/microstructure.md docs/PHASE2/O3C/SIGNAL/CONTINUE_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/CONTINUE_JEV_RUN_NOTE_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE2_DELEGATE_REPORT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/EXPLORE3_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE4_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE5_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/JEV_STATE_PREVIEW_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS2_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW2_2026-09-19.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW3_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW4_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW5_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW6_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW9_2026-09-21.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_RESULT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE1_REPORT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE2_REPORT_2026-09-21.md docs/PHASE2/O3C/STAGE0A_2026-09-14.md docs/PHASE2/O3C/TRIGGER_TRACE.md docs/PROJECT_GOAL.md docs/STRATEGY_IDEAS.md docs/legacy/KATSUO_INTENT_MAP.md docs/legacy/KATSUO_PARAMETER_INVENTORY.md docs/legacy/README.md

## backtest_data(ディレクトリ数)
  147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H_20260905 audit_fetch_JPX_n225f_months_20260906 audit_fetch_JPX_tick_20260906 audit_fetch_P2-08_docs_20260906 audit_fetch_P2-08b_20260906 audit_fetch_bitflyer_history_20260906 audit_fetch_etf_alternatives_20260906 audit_fetch_etf_units_20260906 audit_fetch_micro_fee_20260906 auto_bitflyer_executions_20260905 auto_bitflyer_executions_20260921 auto_oi_snapshots_20260905 auto_oi_snapshots_20260921 auto_okx_long_short_ratio_20260905 auto_okx_open_interest_1h_20260905 auto_okx_open_interest_1h_20260921 auto_okx_open_interest_5m_20260905 auto_okx_open_interest_5m_20260906 auto_okx_open_interest_5m_20260907 auto_okx_open_interest_5m_20260908 auto_okx_open_interest_5m_20260909 auto_okx_open_interest_5m_20260910 auto_okx_open_interest_5m_20260911 auto_okx_open_interest_5m_20260912 auto_okx_open_interest_5m_20260915 auto_okx_open_interest_5m_20260918 auto_okx_open_interest_5m_20260921 auto_venues_20260905 auto_venues_20260921 binance_BTCUSDT_1m.csv binance_BTCUSDT_1m_20170801_20231231 binance_BTCUSDT_1m_20240101_20260831 binance_BTCUSDT_1m_210d_20260820.csv.gz binance_BTCUSDT_1s_20260723_20260906 binance_BTCUSDT_aggTrades_20260723_20260906 binance_BTCUSDT_aggTrades_tardis_days binance_XRPUSDT_1d.csv binance_XRPUSDT_1m.csv binance_XRPUSDT_4h.csv binance_cm_o3c_20260913 binance_cm_o3c_supp_20260917 binance_um_BTCUSDT_aggTrades_20260723_20260906 bitbank_btc_jpy_transactions_monthly_first_days bitbank_xrp_jpy_1m.csv bitflyer_executions_backfill_20260921 bitflyer_executions_us_20260723_20260906 bitflyer_lightchart_BTC_JPY_1m_20260906 bitflyer_lightchart_FX_BTC_JPY_1m_20260906 bitmex_insurance_20260912 bitmex_trade_1s_XBTUSD board_round_20260904 burst_events_20260820 bybit_BTCUSDT_1m_20260910 bybit_reachability_check_20260906 candles_BTC_JPY_20260820.csv candles_ETH_JPY_20260820.csv candles_FX_BTC_JPY_20260820.csv candles_FX_BTC_JPY_30d_20260820.csv candles_FX_BTC_JPY_31d_20260823.csv.gz candles_XRP_JPY_20260820.csv coinalyze_liquidations_20260921 daily_btcusd_bitstamp_20260828.csv.gz daily_btcusd_coinbase_20260828.csv.gz daily_btcusd_yahoo_20260828.csv.gz daily_ethusd_bitstamp_20260828.csv.gz daily_ethusd_coinbase_20260828.csv.gz daily_ethusd_yahoo_20260828.csv.gz executions_FX_BTC_JPY_31d_20260823.csv.gz executions_FX_BTC_JPY_31d_20260908 flow_FX_BTC_JPY_20260820.csv fred_DEXJPUS.csv fred_DFF.csv fred_DGS2.csv fred_IR3TIB01JPM156N.csv fred_IRSTCI01JPM156N.csv fx_btc_jpy_1m_continuous_20260906 fx_event_ticks_2005_2014 fx_event_ticks_2015_2026 fx_fundamentals_20260822 fx_usdjpy_1m_20170801_20221231 fx_usdjpy_1m_20260822.csv.gz gate_liquidations_20260908 gmo_swap_usdjpy.csv jp_factors_20260905 jpx_daily_report_json_20260908 jpx_etf_daily_20260905 jpx_etf_daily_20260906_topix_alt liquidations_repaired_20260912 liquidations_repaired_20260917 mini_topixf_225labo_20260907 n225f_225labo_20260828 nk225_events_20260904 o3c_oi_distance_20260917 o3c_oi_distance_split_20260918 o3c_price_level_band_20260917 o3c_price_level_bundle_first_20260917 o3c_price_level_full_20260917 o3c_price_level_full_20260917_b005 o3c_price_level_full_20260917_b025 o3c_price_level_full_20260917_w72 o3c_price_level_full_20260917_w8 o3c_price_level_rows4_20260917 o3c_price_level_sample_20260917 o3c_price_level_sample_20260917_limitprice o3c_reaction_20260918_anchor o3c_reaction_20260918_anchor_trades o3c_reaction_20260918_anchor_trades_sample o3c_reaction_20260918_anchor_v1_rawcols o3c_reaction_20260918_full o3c_reaction_20260918_judge o3c_reaction_20260918_sample o3c_reaction_20260918_scale12_judgmentdays o3c_signal_continue_20260920 o3c_signal_explore2_20260919 o3c_signal_explore3_20260920 o3c_signal_explore4_20260920 o3c_signal_explore5_20260920 o3c_signal_explore_20260919 o3c_signal_materials_20260920 o3c_signal_policy_20260920 o3c_signal_value_20260921 okx_20260905 okx_btc_lsratio_1h_20260823.csv okx_btc_lsratio_5m_20260823.csv okx_btc_oi_1h_20260823.csv okx_btc_oi_5m_20260823.csv phase2_runs phase2_sealed qa_known_answer_20260905 qa_known_answer_maker3_20260907 qa_known_answer_maker3_v2_20260905 qa_known_answer_maker3_v3_20260905 qa_known_answer_maker4_20260905 qa_known_answer_maker4_r2_20260905 qa_known_answer_maker_20260905 qa_known_answer_steer_20260905 qa_pipeline_daily_20260905 qa_pipeline_daily_20260906 qa_pipeline_taker_20260905 regime_composite_20260901 reit_onr_20260904 storm_events_20260820 topixf_225labo_20260907 venue_survey_20260827 yutai_20260904
```

### 検索計画

**この回も 6 本とも未実行。**リードの起動指定「委任文 §2 のとおり、**検索計画 6 本はまだ打ち直しません。**前回が残した候補を先に潰します」に従った。
委任文 §2 の条件では、残りの候補が空になってから幅と語を変えた 6 本を打つ。今回も残りの候補が空にならなかったので、新しい 6 本には進んでいない。

| 幅 | 日本語クエリ | 英語クエリ | 実行 |
|---|---|---|---|
| 狭い | (未作成) | (未作成) | 未実行(残りの候補が空になっていないため) |
| 中間 | (未作成) | (未作成) | 未実行(同上) |
| 広い | (未作成) | (未作成) | 未実行(同上) |

### 出典

取得日はすべて 2026-09-22。生ログの行番号を添える。

| URL / 経路 | 方法 | 生ログの行 |
|---|---|---|
| https://pypi.org/pypi/basana/json | curl | 3 |
| https://pypi.org/pypi/backtrader/json | curl | 5 |
| https://pypi.org/pypi/lib-pybroker/json | curl | 7 |
| https://pypi.org/pypi/bt/json | curl | 9 |
| https://pypistats.org/api/packages/backtrader/recent | curl | 13 |
| https://pypistats.org/api/packages/zipline-reloaded/recent | curl | 19 |
| https://pypistats.org/api/packages/jesse/recent | curl | 25 |
| https://raw.githubusercontent.com/edtechre/pybroker/master/LICENSE | curl | 43 |
| https://raw.githubusercontent.com/gbeced/basana/develop/LICENSE.txt | curl(404) | 45 |
| https://raw.githubusercontent.com/gbeced/basana/develop/LICENSE | curl | 61 |
| https://raw.githubusercontent.com/gbeced/basana/master/LICENSE | curl | 63 |
| GitHub の repo 検索(9 件を 1 回で。stars / forks / pushed_at / license) | mcp__github__search_repositories | 47 |
| https://pypistats.org/api/packages/basana/recent ほか(再試行ループの最終) | curl | 69 |

### 知見

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | GitHub は curl だと 403 だが、`mcp__github__search_repositories` に `repo:owner/name` を並べると 1 回の呼び出しで複数の星・fork・pushed_at・license がまとめて返る。3 回目に「未確認」で残した星は、この経路で埋まった | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:47。ただし 9 件を指定して返ったのは 8 件で、`stefan-jansen/zipline-reloaded` だけ返らなかった |
| 2 | pypistats の 429 は時間を空ければ抜ける。25 秒の間隔で再試行すると basana / bt / vnpy / pyqlib は 200 が返った。lib-pybroker だけは 4 回とも 429 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:69 |
| 3 | Jesse の週DL数(3 回目の値)は同じ端点で再現した | 一次資料 | https://pypistats.org/api/packages/jesse/recent 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:25 |
| 4 | GitHub API の `license.spdx_id` と、リポジトリの LICENSE 本文が食い違うことがある。basana は API が NOASSERTION、LICENSE 本文は Apache License, Version 2.0 | 一次資料 | docs/DATA/probes/20260922_tools_1_run4.log:47 と :61 |
| 5 | 「無料」の 1 語で済ませられない例が出た。PyBroker は配布が無償でもライセンスが Commons Clause 付きで、「売る」ことを禁じている。OSI の意味でのオープンソースではない | 一次資料 | https://raw.githubusercontent.com/edtechre/pybroker/master/LICENSE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:43 |
| 6 | 「バックテストの道具」と一括りにできない。bt には注文の種別(成行 / 指値)という概念が無く、比重のリバランスしか表せない。委任文 §5-4 の「成行と指値の 1 往復」がそもそも書けない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:41 と :67 |
| 7 | 導入の重さが道具ごとに大きく違う。Backtrader は依存 3 件、Basana は 21 件、bt は 45 件、PyBroker は 52 件 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:27 / :29 / :31 / :33 |
| 8 | Basana の backtesting には、当方に無い 3 つの模型が既定で入っている(流動性の模型 VolumeShareImpact / bid_ask_spread / 貸借)。「暗号資産向けの軽い枠組み」という見た目と中身が違った | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:81 |
| 9 | 4 件とも配布物に setup.py が無く、導入の段で外部取得が起きる経路は見つからなかった。同梱バイナリがあるのは bt だけ(Cython の .so) | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:85 から :91 |

### 候補の一覧

発見順(3 回目から引き継いだ順序のまま)。行頭の `[深掘り]` は §4.0 の表に語彙のすべての項目の行を持つものだけに付ける。それ以外は「浅い」と、何が未確認かを書く。

1. [深掘り] `Basana` — 非同期・イベント駆動の暗号資産向け枠組み。Apache-2.0。導入から成行と指値の往復まで到達。backtesting に流動性の模型・スプレッド・貸借が既定で入る。
2. [深掘り] `Backtrader` — バックテストの機関。GPLv3+。依存 3 件で導入でき、成行と指値の往復まで到達。Interactive Brokers / Oanda / VisualChart のストアを持つ。
3. PySystemtrade — PyPI に無し(3 回目に 404 を実測)。GitHub の LICENSE は GNU GENERAL PUBLIC LICENSE Version 3。**浅い**(版・更新日・依存・導入・最小実行が未確認。PyPI に無いので pip の経路が使えず、git clone は本体の一括取得になるため委任文 §6-6 で打っていない。第 2 経路 = オーナー PC で `git clone --depth 1 https://github.com/robcarver17/pysystemtrade && pip install -e .` を隔離環境で打てば版と依存が取れる)。
4. [深掘り] `PyBroker` — PyPI 上の名前は lib-pybroker。Apache License 2.0 with Commons Clause。導入から成行と指値の往復まで到達。滑りの模型・機械学習の模型の登録・最適化を枠組みに持つ。
5. [深掘り] `bt` — MIT。導入と実行は通ったが、**注文の種別(成行 / 指値)という概念が枠組みに無く**、比重のリバランスしか表せない。中核は Cython の .so で配布。
6. Ziplime — 最新版 1.19.16、更新 2026-06-18、PyPI の license 欄が空。**浅い**(ライセンスの一次資料が取れていない。GitHub の所在も未確認。導入・最小実行も未実施)。
7. Superalgos — PyPI に無し。GitHub の LICENSE は Apache License Version 2.0。**浅い**(版・更新日・導入・最小実行が未確認。Node.js 系で pip の経路に無い)。
8. OpenTrader — PyPI に無し。GitHub の master ブランチの LICENSE は Apache License Version 2.0。**浅い**(版・更新日・導入・最小実行が未確認)。
9. CryptoSignal — PyPI に無し(crypto-signal は 404)。GitHub の LICENSE は MIT License、Copyright (c) 2017 Abenezer Mamo。**浅い**(版・更新日・導入・最小実行が未確認)。
10. fast-trade — GNU AGPLv3、最新版 2.1.0、更新 2026-08-20。**浅い**(導入・最小実行・AGPL の再配布の条件が未確認)。
11. OctoBot — GPL-3.0、最新版 2.1.1、更新 2026-03-29。**浅い**(導入・最小実行が未確認。依存が多く、隔離 venv での導入を打っていない)。
12. pybotters — MIT、最新版 1.11.2、更新 2026-04-17。**浅い**(導入・最小実行・対応取引所の一次資料が未確認)。
13. DeviaVir/zenbot — 本家 carlos8f/zenbot の分岐。package.json の name は zenbot4、version 4.1.0、license MIT、engines.node は >=10.0.0。**浅い**(Node.js の導入・最小実行・保守の状態が未確認)。
14. Bot18 — carlos8f の後継。package.json の name は bot18、version 0.4.35。**浅い**(ライセンス欄・導入・最小実行が未確認)。
15. Mendl-Labs/BacktestingCore — master ブランチの LICENSE は Functional Source License, Version 1.1, ALv2 Future License、Copyright 2026 Nwagbara Group, LLC。**浅い**(README の原文・版・導入が未確認)。
16. Luczinsritter/event_driven_backtesting_engine — LICENSE ファイルは main と master のどちらも 404。バッジは MIT。**浅い**(ライセンスの根拠がバッジだけ。版・導入・最小実行が未確認)。
17. mlflow — Qlib の必須依存として 3 回目に名前が出た。実験の追跡の道具そのもの。**浅い**(単体での導入・最小実行をしていない)。
18. `zipline-reloaded` — 3 回目に深掘り済み。この回では週DL数と星だけを取り直した(表の行は 3 回目の節にある。**この回の §4.0 の表には行を持たない**)。
19. `Jesse` — 3 回目に深掘り済み。この回では週DL数の再現と星だけを取り直した(同上)。
20. `VnPy` — 3 回目に深掘り済み。この回では週DL数と星だけを取り直した(同上)。
21. `Qlib` — 3 回目に深掘り済み。この回では週DL数(pyqlib)と星だけを取り直した(同上)。
22. `Lean CLI` — 3 回目に深掘り済み。この回では星だけを取り直した(同上)。
23. `hftbacktest` — 1 回目に深掘り済み。この回では何も足していない(1 回目の節を見る)。

### ツール1件ごとの表

#### §4.0 の機械可読の表

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| `Basana` | 版 | 1.11 | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(info.version) |
| `Basana` | 最終更新日 | 2026-07-22T17:47:41 | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(最新版の upload_time) |
| `Basana` | ライセンス | Apache License, Version 2.0。逐語「Basana  Copyright 2022 Gabriel Martin Becedillas Ruiz  Licensed under the Apache License, Version 2.0」。PyPI の info.license_expression も Apache-2.0 | 一次資料 | https://raw.githubusercontent.com/gbeced/basana/develop/LICENSE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:61。GitHub API の license は NOASSERTION(docs/DATA/probes/20260922_tools_1_run4.log:47)で、LICENSE 本文と食い違う |
| `Basana` | 言語と動作環境 | Python <4,>=3.10。この環境は Python 3.11.15 | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(info.requires_python) |
| `Basana` | 対応取引所 | basana/external に binance / bitstamp / ccxt / yahoo の 4 ディレクトリ。ccxt 経由で ccxt の対応先に広がる。bitFlyer 専用の実装は見ていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:83 |
| `Basana` | 星 | 867(fork 113) | 一次資料 | mcp__github__search_repositories(repo: 指定9件)取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `Basana` | コミット数 | 未確認 | 未確認 | 試したこと: GitHub API の repo 検索は stars と forks しか返さない。curl での GitHub API は 403。commits の総数を返す端点は今回打っていない |
| `Basana` | 保守者数 | PyPI の info.author = "Gabriel Becedillas"、info.maintainer = None | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(info.author / info.maintainer) |
| `Basana` | 週DL数 | last_week=47、last_month=406、last_day=3 | 一次資料 | https://pypistats.org/api/packages/basana/recent 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:93 |
| `Basana` | 初回公開日 | 2023-03-04T02:00:04 | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(releases の最古 upload_time) |
| `Basana` | 既知の脆弱性 | PyPI の vulnerabilities は長さ 0 | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(vulnerabilities) |
| `Basana` | 料金体系 | Apache-2.0 の無償配布。PyPI の project_urls は Documentation / Homepage / Repository の 3 つだけで、料金ページに当たるものが無い | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(project_urls) |
| `Basana` | 無料枠の上限 | 本体側に上限の記述なし。外部取引所の接続(binance / bitstamp / ccxt)を使う段では各取引所の API の制限と手数料が掛かるが、その条件は本調査では取っていない | 推定 | Apache-2.0 の配布と、導入・最小実行のどちらでも鍵・登録を求められなかったことからの外挿 |
| `Basana` | 課金開始条件 | 本体には無い。実弾で取引所に接続する段で各取引所側の手数料が掛かる | 推定 | 同上。external の各取引所の料金は一次資料を取っていない |
| `Basana` | 隠れた依存 | 導入した 21 件の中に相場データの提供元は入らない。charts を使うと plotly が要る(未導入で ModuleNotFoundError) | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:27(pkgs=21)。plotly の欠落は basana.backtesting.charts の import で観測 |
| `Basana` | 登録の要否 | 不要。鍵なしで導入・合成 csv の投入・成行と指値の往復まで到達 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:37 |
| `Basana` | 到達経路 | PyPI の index から pip install が通る | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:27 |
| `Basana` | 導入可否 | 可。隔離 venv に導入 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:27(rc=0) |
| `Basana` | install所要秒 | 7 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:27(install_time_s) |
| `Basana` | 依存数 | 21 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:27(pkgs) |
| `Basana` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:27(pip_check) |
| `Basana` | 最小実行の可否 | 可 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:37 |
| `Basana` | 最小実行の中身 | 合成の日足 120 本(乱数の種 7)を yahoo 形式の csv にして CSVBarSource で投入し、5 本目で成行買い 10、10 本目で終値 ×1.002 の指値売り 10 を出し、両方が約定した。手数料は fees.Percentage(0.05%) | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:37(FILLS の 2 件) |
| `Basana` | 実行所要秒 | 1.5 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:37(time_s) |
| `Basana` | wheel展開 | basana-1.11-py3-none-any.whl を pip download --no-deps で取り、117 ファイルを列挙 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:85 |
| `Basana` | setup.py導入時実行 | wheel に setup.py は 0 件 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:85(setup_py=0) |
| `Basana` | 同梱バイナリ | 0 件(.so / .pyd / .dll / .dylib / .exe のいずれも無い) | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:85(binaries=0) |
| `Basana` | 外部送信 | 配布物の .py / .toml / .cfg に現れる外部ホストは api.binance.com・www.binance.com・www.bitstamp.net・docs.ccxt.com・binance-docs.github.io・developers.binance.com・plotly.com・docs.python.org・github.com・www.apache.org。取引所の端点と文書の URL で、遠隔測定の送信先は見当たらない。ただし走らせた状態での通信の観測はしていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:85(hosts) |
| `Basana` | 自動発注機能 | ある。basana/external の binance / bitstamp / ccxt が実弾の取引所クライアント。今回は backtesting.exchange だけを使い、鍵を要する経路は打っていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:83 |
| `Basana` | 宣伝詐欺の兆候 | 兆候なし。配布は PyPI と GitHub のみ。project_urls は 3 つとも公式文書とリポジトリ | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(project_urls) |
| `Basana` | 当方データ投入 | 日付・OHLCV の csv を yahoo 形式に整えれば入った。当方の csv.gz の約定・清算をそのまま入れる経路は試していない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:37(BASANA_BARS=120) |
| `Basana` | 時刻の扱い | バーの日時を文字列から読み、取引所暦の検査は掛からなかった(暦に無い日付でも止まらない)。UTC・ミリ秒の扱いは今回の日足では観測していない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:37(120 本すべてが処理された。連続する暦日で ingest 相当の検査に当たらなかった) |
| `Basana` | 再現性 | 乱数の種を固定した合成データで、約定価格が 98.48 / 101.68 に決まった。枠組み側の乱数は使っていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:37 |
| `Basana` | 規模の見積 | 456 日のティックの所要は測っていない。日足 120 本で 1.5 秒という 1 点からは外挿できない | 未確認 | 試したこと: 日足 1 件のみ。ティックまたは分足の投入は今回の時間内に打てなかった |
| `Basana` | 4軸1_道具 | 入れられる。隔離 venv で導入から指値の往復まで通った | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:37 |
| `Basana` | 4軸2_情報 | 取引所の接続(binance / bitstamp / ccxt)と、backtesting 側に当方に無い部品がある: 流動性の模型 VolumeShareImpact(既定)、bid_ask_spread(既定 Decimal('0.5'))、手数料の戦略、貸借(lending / loan_mgr、create_loan / repay_loan) | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:81(Exchange の method 一覧と __init__ の既定引数) |
| `Basana` | 4軸3_視点 | 非同期のイベント駆動(asyncio)で、バーの到着を購読して注文を出す形。当方の backtest/engine.py は足のループを回す形で、この形ではない | 推定 | Exchange の API(subscribe_to_bar_events / dispatcher)と最小実行の書き方からの外挿 |
| `Basana` | 4軸4_向上 | 未確認 | 未確認 | 試したこと: 当方の engine.py との突き合わせは今回の範囲外(リードの判定事項) |
| `Basana` | 配布元の一致 | PyPI の project_urls.Repository が https://github.com/gbeced/basana を指し、GitHub 側の full_name も gbeced/basana | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(project_urls) / mcp__github__search_repositories(repo: 指定9件)取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `Basana` | 難読化 | 配布物のファイル名 117 件と、.py / .toml / .cfg の URL の走査では難読化の痕跡に当たらなかった。バイトコードだけの配布や base64 の塊の走査はしていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:85 |
| `Basana` | 外部URL取得 | 導入時に実行される setup.py が無いので、導入の段で外部取得は起きない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:85(setup_py=0) |
| `Basana` | 依存の一覧 | PyPI の requires_dist は 5 件。導入後の pip list は 21 件 | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22(requires_dist=5)。導入後の 21 件は docs/DATA/probes/20260922_tools_1_run4.log:27 |
| `Basana` | 保守者名の一貫性 | PyPI の info.author = "Gabriel Becedillas"、info.maintainer = None、LICENSE の Copyright は "Gabriel Martin Becedillas Ruiz"、GitHub の owner は gbeced。同一人物として一貫 | 一次資料 | https://pypi.org/pypi/basana/json 取得日 2026-09-22 / https://raw.githubusercontent.com/gbeced/basana/develop/LICENSE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:61 |
| `Backtrader` | 版 | 1.9.78.123 | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(info.version) |
| `Backtrader` | 最終更新日 | PyPI の最新版の upload_time は 2023-04-19T14:13:18。GitHub の pushed_at は 2024-08-19T17:47:36 | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22 / mcp__github__search_repositories 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `Backtrader` | ライセンス | PyPI の info.license は GPLv3+、GitHub API の license.spdx_id は GPL-3.0 | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(info.license) / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `Backtrader` | 言語と動作環境 | PyPI の info.requires_python は空(指定なし)。この環境の Python 3.11.15 で導入と実行が通った | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(requires_python が空文字)。3.11 での実行は docs/DATA/probes/20260922_tools_1_run4.log:35 |
| `Backtrader` | 対応取引所 | 導入後に backtrader/stores と backtrader/brokers があり、stores の中身は ibstore.py(Interactive Brokers)・oandastore.py(Oanda)・vcstore.py・vchartfile.py(VisualChart)。国内取引所の実装は無い | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:65 |
| `Backtrader` | 星 | 23301(fork 5289) | 一次資料 | mcp__github__search_repositories 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `Backtrader` | コミット数 | 未確認 | 未確認 | 試したこと: GitHub の repo 検索は stars と forks しか返さない。curl での GitHub API は 403。commits の総数を返す端点は今回打っていない |
| `Backtrader` | 保守者数 | PyPI の info.author = "Daniel Rodriguez"、info.maintainer は空文字 | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(info.author / info.maintainer) |
| `Backtrader` | 週DL数 | last_week=41186、last_month=190065、last_day=4982 | 一次資料 | https://pypistats.org/api/packages/backtrader/recent 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:13 |
| `Backtrader` | 初回公開日 | 2019-05-30T12:06:19(PyPI に現存する最古の版の upload_time) | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(releases の最古 upload_time) |
| `Backtrader` | 既知の脆弱性 | PyPI の vulnerabilities は長さ 0 | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(vulnerabilities) |
| `Backtrader` | 料金体系 | GPLv3+ の無償配布。PyPI の project_urls は Download と Homepage の 2 つだけで、料金ページに当たるものが無い | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(project_urls) |
| `Backtrader` | 無料枠の上限 | 上限の記述なし。ただし GPLv3+ なので、改変して配布する場合は同じ条件での公開が要る(当方が社内で使う限りは掛からない) | 推定 | PyPI の info.license = GPLv3+ からの外挿。LICENSE 本文は今回取っていない |
| `Backtrader` | 課金開始条件 | 該当なし。導入と最小実行のどちらでも鍵・登録を求められなかった | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:27 と :35(どちらも鍵の要求なしで rc=0) |
| `Backtrader` | 隠れた依存 | PyPI の requires_dist は 1 件。導入後の pip list は 3 件(backtrader 本体と pip / setuptools 相当)で、相場データの提供元も数値計算の重い依存も入らない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:29(pkgs=3) |
| `Backtrader` | 登録の要否 | 不要 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:35 |
| `Backtrader` | 到達経路 | PyPI の index から pip install が通る | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:29 |
| `Backtrader` | 導入可否 | 可。隔離 venv に導入 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:29(rc=0) |
| `Backtrader` | install所要秒 | 2 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:29(install_time_s) |
| `Backtrader` | 依存数 | 3 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:29(pkgs) |
| `Backtrader` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:29(pip_check) |
| `Backtrader` | 最小実行の可否 | 可 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:35 |
| `Backtrader` | 最小実行の中身 | 自作の feeds.DataBase で合成の日足 120 本(乱数の種 7)を流し、5 本目で成行買い 10、10 本目で終値 ×1.002 の指値売り 10。手数料 0.05%。約定 2 件(Buy 10 @98.4758 / Sell -10 @101.6812) | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:35(TXN_COUNT=2 と TXNS) |
| `Backtrader` | 実行所要秒 | 1.3 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:35(time_s) |
| `Backtrader` | wheel展開 | backtrader-1.9.78.123-py2.py3-none-any.whl を pip download --no-deps で取り、178 ファイルを列挙 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:87 |
| `Backtrader` | setup.py導入時実行 | wheel に setup.py は 0 件 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:87(setup_py=0) |
| `Backtrader` | 同梱バイナリ | 0 件 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:87(binaries=0) |
| `Backtrader` | 外部送信 | 配布物に現れる外部ホストは query1.finance.yahoo.com・finance.yahoo.com・fxcodebase.com・help.cqg.com・alanhull.com・cssanalytics.wordpress.com・en.wikipedia.org・github.com・pandas-market-calendars.readthedocs.io・stackoverflow.com と、例の中の 127.0.0.1:8080 / myproxy.com。yahoo の 2 つはデータ取得の端点で、遠隔測定の送信先は見当たらない。走らせた状態での通信の観測はしていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:87(hosts) |
| `Backtrader` | 自動発注機能 | ある。backtrader/brokers と backtrader/stores(Interactive Brokers・Oanda・VisualChart)。今回は既定の内部ブローカーだけを使い、鍵を要する経路は打っていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:65 |
| `Backtrader` | 宣伝詐欺の兆候 | 兆候なし。配布は PyPI と GitHub のみで、project_urls は Download(GitHub の tarball)と Homepage の 2 つ | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(project_urls) |
| `Backtrader` | 当方データ投入 | feeds.DataBase を継承して _load を書けば任意の列を流せた。当方の csv.gz の約定・清算をそのまま入れる経路は試していない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:35(自作 feed で 120 本が流れた) |
| `Backtrader` | 時刻の扱い | bt.date2num / bt.num2date で datetime を float に変換して持つ。取引所暦の検査は掛からず、連続する暦日 120 本がそのまま流れた。UTC・ミリ秒の扱いは日足では観測していない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:35 |
| `Backtrader` | 再現性 | 乱数の種を固定した合成データで、約定価格が 98.4758 / 101.6812 に決まった。枠組み側の乱数は使っていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:35 |
| `Backtrader` | 規模の見積 | 456 日のティックの所要は測っていない。日足 120 本で 1.3 秒という 1 点からは外挿できない | 未確認 | 試したこと: 日足 1 件のみ。ティック・分足の投入は今回の時間内に打てなかった |
| `Backtrader` | 4軸1_道具 | 入れられる。依存 3 件で導入 2 秒、指値の往復まで通った | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:29 と :35 |
| `Backtrader` | 4軸2_情報 | 当方に無い接続先として Interactive Brokers・Oanda・VisualChart のストアが付く | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:65 |
| `Backtrader` | 4軸3_視点 | 注文に exectype(Market / Limit など)と valid を持たせ、notify_order で状態遷移を受け取る形。当方の engine.py は約定の判定を engine の中で閉じており、注文の状態遷移を戦略側に通知する形ではない | 推定 | 最小実行で使った bt.Order.Limit / notify_order の API からの外挿。当方の engine.py の逐語の突き合わせはしていない |
| `Backtrader` | 4軸4_向上 | 未確認 | 未確認 | 試したこと: 当方の engine.py との突き合わせは今回の範囲外(リードの判定事項) |
| `Backtrader` | 配布元の一致 | PyPI の Homepage と Download がどちらも github.com/mementum/backtrader を指し、GitHub 側の full_name も mementum/backtrader | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(project_urls) / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `Backtrader` | 難読化 | 配布物のファイル名 178 件と URL の走査では痕跡に当たらなかった。バイトコードだけの配布や base64 の塊の走査はしていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:87 |
| `Backtrader` | 外部URL取得 | 導入時に実行される setup.py が無いので、導入の段で外部取得は起きない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:87(setup_py=0) |
| `Backtrader` | 依存の一覧 | PyPI の requires_dist は 1 件。導入後の pip list は 3 件 | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22(requires_dist=1)。導入後の 3 件は docs/DATA/probes/20260922_tools_1_run4.log:29 |
| `Backtrader` | 保守者名の一貫性 | PyPI の info.author = "Daniel Rodriguez"、info.maintainer は空文字。GitHub の owner は mementum。PyPI の author 名と GitHub のアカウント名は字面が一致しない | 一次資料 | https://pypi.org/pypi/backtrader/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `PyBroker` | 版 | 2.0.1 | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22(info.version) |
| `PyBroker` | 最終更新日 | PyPI の最新版の upload_time は 2026-08-28T03:38:23。GitHub の pushed_at は 2026-09-21T16:16:26 | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `PyBroker` | ライセンス | PyPI の info.license は "Apache License 2.0 with Commons Clause"。LICENSE 本文の冒頭は逐語「"Commons Clause" License Condition v1.0 … the grant of rights under the License will not include, and the License does not grant to you, the right to Sell the Software.」。GitHub API の license.spdx_id は NOASSERTION | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22 / https://raw.githubusercontent.com/edtechre/pybroker/master/LICENSE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:43 |
| `PyBroker` | 言語と動作環境 | Python >=3.11。この環境は Python 3.11.15 | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22(info.requires_python) |
| `PyBroker` | 対応取引所 | 本体の pybroker 直下に取引所のディレクトリは無い。依存として入った alpaca に broker と data/live があり、Alpaca(米株・暗号資産)に繋がる。国内取引所の実装は見ていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:65 |
| `PyBroker` | 星 | 3544(fork 452) | 一次資料 | mcp__github__search_repositories 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `PyBroker` | コミット数 | 未確認 | 未確認 | 試したこと: GitHub の repo 検索は stars と forks しか返さない。curl での GitHub API は 403 |
| `PyBroker` | 保守者数 | PyPI の info.author = "Edward West"、info.maintainer = None | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22(info.author / info.maintainer) |
| `PyBroker` | 週DL数 | 未確認 | 未確認 | 試したこと: https://pypistats.org/api/packages/lib-pybroker/recent を 25 秒の間隔で 4 回打ち、4 回とも HTTP 429。同じループで basana / bt / vnpy / pyqlib は 200 が返った |
| `PyBroker` | 初回公開日 | 2023-01-17T19:00:54 | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22(releases の最古 upload_time) |
| `PyBroker` | 既知の脆弱性 | PyPI の vulnerabilities は長さ 0 | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22(vulnerabilities) |
| `PyBroker` | 料金体系 | 配布そのものは無償だが、Commons Clause により「売る」ことが禁じられている。逐語「"Sell" means practic…」(LICENSE 冒頭 400 字までの範囲で切れている)。OSI の意味でのオープンソースではない | 一次資料 | https://raw.githubusercontent.com/edtechre/pybroker/master/LICENSE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:43 |
| `PyBroker` | 無料枠の上限 | 自前で走らせる限り回数・期間の上限は見当たらない。制限は金額ではなく Commons Clause の「売らない」条件 | 一次資料 | https://raw.githubusercontent.com/edtechre/pybroker/master/LICENSE 取得日 2026-09-22 |
| `PyBroker` | 課金開始条件 | 本体には課金の口が無い。既定のデータ源(YFinance / Alpaca / AKShare)のうち Alpaca は鍵が要る。今回は DataFrame を直接渡したので鍵を求められなかった | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:39(鍵なしで完走) |
| `PyBroker` | 隠れた依存 | 導入で 52 件。alpaca(実弾のブローカー)・numba・joblib・akshare の URL が配布物に現れる。相場データは別途 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:31(pkgs=52) と :52(hosts) |
| `PyBroker` | 登録の要否 | 不要。DataFrame を直接渡す経路なら鍵なしで完走 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:39 |
| `PyBroker` | 到達経路 | PyPI の index から pip install lib-pybroker が通る(import 名は pybroker) | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:31 |
| `PyBroker` | 導入可否 | 可。隔離 venv に導入 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:31(rc=0) |
| `PyBroker` | install所要秒 | 37 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:31(install_time_s) |
| `PyBroker` | 依存数 | 52 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:31(pkgs) |
| `PyBroker` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:31(pip_check) |
| `PyBroker` | 最小実行の可否 | 可 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:39 |
| `PyBroker` | 最小実行の中身 | 合成の日足 120 本(乱数の種 7)を DataFrame で渡し、5 本目で ctx.buy_shares=10(成行)、10 本目で ctx.sell_shares=10 と ctx.sell_limit_price=終値×1.002。注文 2 件・約定した往復 1 件。order_type は buy 側が market、sell 側が limit(limit_price=101.59、fill_price=101.78) | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:39(ORDERS=2 TRADES=1 と orders の中身) |
| `PyBroker` | 実行所要秒 | 3.0 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:39(time_s) |
| `PyBroker` | wheel展開 | wheel ではなく lib_pybroker-2.0.1.tar.gz が返り、59 ファイルを列挙 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:89 |
| `PyBroker` | setup.py導入時実行 | 配布物に setup.py は 0 件(pyproject のみ) | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:89(setup_py=0) |
| `PyBroker` | 同梱バイナリ | 0 件 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:89(binaries=0) |
| `PyBroker` | 外部送信 | 配布物に現れる外部ホストは alpaca.markets・finance.yahoo.com・akshare.akfamily.xyz・www.pybroker.com・joblib.readthedocs.io・blogs.sas.com・en.wikipedia.org・github.com・stackoverflow.com。データ源と文書の URL で、遠隔測定の送信先は見当たらない。走らせた状態での通信の観測はしていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:89(hosts) |
| `PyBroker` | 自動発注機能 | 本体には無いが、依存の alpaca に broker と data/live が入る。今回は鍵を要する経路を打っていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:65 |
| `PyBroker` | 宣伝詐欺の兆候 | 兆候なし。PyPI の project_urls は Homepage(http://www.pybroker.com)の 1 つだけ。Telegram 限定配布・提携リンク・利益の保証の記述には当たらなかった | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22(project_urls) |
| `PyBroker` | 当方データ投入 | symbol / date / open / high / low / close / volume の列を持つ DataFrame をそのまま渡せた。当方の csv.gz の約定・清算をそのまま入れる経路は試していない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:39(BARS=120) |
| `PyBroker` | 時刻の扱い | pandas の Timestamp を date 列に持つ。取引所暦の検査は掛からず、連続する暦日 120 本がそのまま流れた。start_date / end_date で区間を切る。UTC・ミリ秒の扱いは日足では観測していない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:39 |
| `PyBroker` | 再現性 | 乱数の種を固定した合成データで、約定価格が 98.57 / 101.78 に決まった | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:39 |
| `PyBroker` | 規模の見積 | 456 日のティックの所要は測っていない。日足 120 本で 3.0 秒という 1 点からは外挿できない | 未確認 | 試したこと: 日足 1 件のみ。ティック・分足の投入は今回の時間内に打てなかった |
| `PyBroker` | 4軸1_道具 | 入れられる。隔離 venv で導入から指値の往復まで通った | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:39 |
| `PyBroker` | 4軸2_情報 | 当方に無い部品として slippage.py(滑りの模型)・model.py(機械学習の模型の登録)・optimize.py(最適化)・eval.py(評価指標)・vect.py(ベクトル化)・cache.py が入る | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:79(pybroker 直下のファイル一覧) |
| `PyBroker` | 4軸3_視点 | 戦略を「文脈オブジェクト ctx に注文の意思を書き込む関数」として書く形で、ブートストラップによる評価と機械学習の模型の組み込みが枠組みに入っている。当方の engine.py はこの形ではない | 推定 | 最小実行で使った ctx.buy_shares / ctx.sell_limit_price の API と、eval.py / model.py の存在からの外挿 |
| `PyBroker` | 4軸4_向上 | 未確認 | 未確認 | 試したこと: 当方の engine.py との突き合わせは今回の範囲外(リードの判定事項) |
| `PyBroker` | 配布元の一致 | PyPI の Homepage は http://www.pybroker.com で GitHub を指さない。配布物の中に www.pybroker.com と github.com の両方が現れ、GitHub 側の edtechre/pybroker の homepage が https://www.pybroker.com で一致する | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22(project_urls) / docs/DATA/probes/20260922_tools_1_run4.log:47(homepage) |
| `PyBroker` | 難読化 | 配布物のファイル名 59 件と URL の走査では痕跡に当たらなかった。バイトコードだけの配布や base64 の塊の走査はしていない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:89 |
| `PyBroker` | 外部URL取得 | 配布物に setup.py が無いので、導入の段で外部取得は起きない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:89(setup_py=0) |
| `PyBroker` | 依存の一覧 | PyPI の requires_dist は 19 件。導入後の pip list は 52 件 | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22(requires_dist=19)。導入後の 52 件は docs/DATA/probes/20260922_tools_1_run4.log:31 |
| `PyBroker` | 保守者名の一貫性 | PyPI の info.author = "Edward West"、info.maintainer = None。GitHub の owner は edtechre。PyPI の author 名と GitHub のアカウント名は字面が一致しない | 一次資料 | https://pypi.org/pypi/lib-pybroker/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `bt` | 版 | 1.2.3 | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(info.version) |
| `bt` | 最終更新日 | PyPI の最新版の upload_time は 2026-09-12T00:45:25。GitHub の pushed_at は 2026-09-20T20:44:20 | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `bt` | ライセンス | PyPI の info.license は MIT、GitHub API の license.spdx_id も MIT | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(info.license) / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `bt` | 言語と動作環境 | Python >=3.9。この環境は Python 3.11.15。配布は cp311 の manylinux wheel | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(info.requires_python)。wheel 名は docs/DATA/probes/20260922_tools_1_run4.log:91 |
| `bt` | 対応取引所 | 無し。導入後に exchange / broker / store / live / gateway のいずれのディレクトリも見つからなかった | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:65 |
| `bt` | 星 | 2989(fork 501) | 一次資料 | mcp__github__search_repositories 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `bt` | コミット数 | 未確認 | 未確認 | 試したこと: GitHub の repo 検索は stars と forks しか返さない。curl での GitHub API は 403 |
| `bt` | 保守者数 | PyPI の info.author も info.maintainer も None。GitHub の owner は pmorissette | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(info.author / info.maintainer) / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `bt` | 週DL数 | last_week=5758、last_month=23631、last_day=646 | 一次資料 | https://pypistats.org/api/packages/bt/recent 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:95 |
| `bt` | 初回公開日 | 2014-06-26T14:09:20 | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(releases の最古 upload_time) |
| `bt` | 既知の脆弱性 | PyPI の vulnerabilities は長さ 0 | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(vulnerabilities) |
| `bt` | 料金体系 | MIT の無償配布。PyPI の project_urls は Documentation / Homepage / Repository の 3 つだけで、料金ページに当たるものが無い | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(project_urls) |
| `bt` | 無料枠の上限 | 上限の記述なし | 推定 | MIT の配布と、導入・最小実行のどちらでも鍵・登録を求められなかったことからの外挿 |
| `bt` | 課金開始条件 | 該当なし | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:33 と :41(どちらも鍵の要求なしで rc=0) |
| `bt` | 隠れた依存 | 導入で 45 件。相場データの提供元は入らない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:33(pkgs=45) |
| `bt` | 登録の要否 | 不要 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:41 |
| `bt` | 到達経路 | PyPI の index から pip install bt が通る | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:33 |
| `bt` | 導入可否 | 可。隔離 venv に導入 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:33(rc=0) |
| `bt` | install所要秒 | 37 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:33(install_time_s) |
| `bt` | 依存数 | 45 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:33(pkgs) |
| `bt` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:33(pip_check) |
| `bt` | 最小実行の可否 | 一部のみ可。バックテストは完走したが、委任文 §5-4 が求める「成行と指値の 1 往復」のうち指値が出せない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:41 と :67 |
| `bt` | 最小実行の中身 | 合成の日足 120 本(乱数の種 7)の終値 1 銘柄で、RunMonthly + SelectAll + WeighEqually + Rebalance の 4 アルゴリズムを回し、手数料 0.05%。取引 1 件、最終評価額 95658.4622、総収益率 -0.043415。注文の種別(成行 / 指値)を指定する API は枠組みに無く、bt.algos で名前に limit / order / market を含むのは LimitDeltas と LimitWeights の 2 つだけで、どちらも比重の制限で指値注文ではない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:41 と :67 |
| `bt` | 実行所要秒 | 1.0 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:41(time_s) |
| `bt` | wheel展開 | bt-1.2.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl を pip download --no-deps で取り、12 ファイルを列挙 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:91 |
| `bt` | setup.py導入時実行 | wheel に setup.py は 0 件 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:91(setup_py=0) |
| `bt` | 同梱バイナリ | 1 件。bt/core.cpython-311-x86_64-linux-gnu.so(Cython で作られた中核)。中身は機械語で、この環境では読んでいない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:91(binaries=1 bin_ex) |
| `bt` | 外部送信 | 配布物の .py / .toml / .cfg に現れる外部ホストは en.wikipedia.org の 1 つだけ。ただし中核は .so に入っており、そこは走査していないので、この結果は「Python の部分に外部送信の URL が無い」ことしか示さない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:91(hosts) |
| `bt` | 自動発注機能 | 無し。取引所・ブローカーのディレクトリが 0 件 | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:65 |
| `bt` | 宣伝詐欺の兆候 | 兆候なし。配布は PyPI と GitHub のみ。project_urls は 3 つとも公式文書とリポジトリ | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(project_urls) |
| `bt` | 当方データ投入 | 日付を index にした終値の DataFrame をそのまま渡せた。約定・清算のような明細のデータを入れる形ではない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:41(BT_LIB_BARS=120) |
| `bt` | 時刻の扱い | pandas の DatetimeIndex をそのまま使う。取引所暦の検査は掛からず、連続する暦日 120 本が流れた。UTC・ミリ秒の扱いは日足では観測していない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:41 |
| `bt` | 再現性 | 乱数の種を固定した合成データで、最終評価額が 95658.4622 に決まった | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:41 |
| `bt` | 規模の見積 | 456 日のティックの所要は測っていない。そもそも比重のリバランスの枠組みで、ティックの単位を扱う設計ではない | 推定 | 最小実行で使った Rebalance / WeighEqually の API と、指値の API が無いこと(docs/DATA/probes/20260922_tools_1_run4.log:67)からの外挿 |
| `bt` | 4軸1_道具 | 入れられるが、注文の種別を持たない比重の枠組みなので、当方の指値の約定の研究には形が合わない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:41 と :67 |
| `bt` | 4軸2_情報 | 当方に無い部品として、比重の決め方のアルゴリズム群(WeighEqually / LimitWeights / LimitDeltas など)と、複数戦略を木構造で入れ子にする仕組みが入る | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:67(bt.algos の名前の走査)と :41(Strategy に algos の列を渡す形) |
| `bt` | 4軸3_視点 | 「いつ・何を・どの比重で持つか」をアルゴリズムの列として組み立てる形で、注文の約定を模擬しない。当方の engine.py が注文と約定の単位で書かれているのと逆向き | 推定 | 最小実行の書き方と、指値の API が無いことからの外挿 |
| `bt` | 4軸4_向上 | 未確認 | 未確認 | 試したこと: 当方の engine.py との突き合わせは今回の範囲外(リードの判定事項) |
| `bt` | 配布元の一致 | PyPI の project_urls.Repository が https://github.com/pmorissette/bt を指し、GitHub 側の full_name も pmorissette/bt | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(project_urls) / docs/DATA/probes/20260922_tools_1_run4.log:47 |
| `bt` | 難読化 | Python の部分(12 ファイル)には痕跡が無いが、中核は .so で配布されており、そこは読んでいない。難読化の有無をこの環境で確かめる手段を持たない | 未確認 | 試したこと: wheel の中身の列挙のみ。.so の逆アセンブルはしていない |
| `bt` | 外部URL取得 | 導入時に実行される setup.py が無いので、導入の段で外部取得は起きない | 実測 | docs/DATA/probes/20260922_tools_1_run4.log:91(setup_py=0) |
| `bt` | 依存の一覧 | PyPI の requires_dist は 53 件。導入後の pip list は 45 件(環境の条件で入らない任意の依存があるため PyPI の数より少ない) | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22(requires_dist=53)。導入後の 45 件は docs/DATA/probes/20260922_tools_1_run4.log:33 |
| `bt` | 保守者名の一貫性 | PyPI の info.author も info.maintainer も None で、名前を照合する材料が PyPI 側に無い。GitHub の owner は pmorissette | 一次資料 | https://pypi.org/pypi/bt/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run4.log:47 |

#### 1. Basana(深掘り)

- **できること**(一次資料 = 導入後のパッケージと API の逐語): backtesting の取引所(成行・指値・逆指値・逆指値付き指値の 4 種の注文、注文の取消、残高の照会、板の最良気配の照会、未約定注文の照会、注文の履歴、通貨対の情報と精度の設定、バーの購読、注文のイベントの購読)/ 貸借(借入の作成・照会・返済)/ 流動性の模型 / 手数料の戦略 / 図表(plotly が要る)/ 外部の取引所(binance・bitstamp・ccxt)と yahoo のデータ。
- **料金の構造**: 本体は Apache-2.0 の無償配布で、PyPI にも project_urls にも料金ページに当たるものが無い(一次資料)。課金の口は本体に無く、実弾で取引所に繋ぐ段で各取引所の手数料が掛かる(推定)。**登録は不要**で、鍵なしで導入から指値の往復まで到達した(実測)。
- **到達・導入・実行**: PyPI の index から導入でき、隔離 venv で `pip check` が通った。最小の実行は合成の日足を yahoo 形式の csv にして投入し、成行買いと指値売りの往復が両方約定した(実測)。
- **当方の用途との相性**: 日付と OHLCV の csv は入った。当方の csv.gz の約定・清算をそのまま入れる経路は試していない(未確認)。時刻は取引所暦の検査に掛からず、連続する暦日がそのまま流れた(実測)。
- **当方に無いもの(全部)**: 流動性の模型 `VolumeShareImpact`(既定)/ `bid_ask_spread`(既定 `Decimal('0.5')`)/ 手数料の戦略の差し替え / 貸借(`create_loan` / `repay_loan` / `get_loans`)/ 逆指値と逆指値付き指値の注文 / 注文のイベントの購読(`subscribe_to_order_events`)/ 非同期のイベント駆動の実行器 / binance・bitstamp・ccxt の取引所クライアント / `immediate_order_processing` の切り替え。
- **危険**: 配布元は PyPI と GitHub で一致。配布物に setup.py も同梱バイナリも無い。外部ホストは取引所の端点と文書の URL だけ。既知の脆弱性は PyPI の vulnerabilities が空。宣伝・詐欺の兆候に当たるものは見つからなかった。**ただし実弾の取引所クライアントを持つので、鍵を置けば発注できる。**今回は backtesting だけを使い、鍵を要する経路は打っていない。

#### 2. Backtrader(深掘り)

- **できること**: 注文の種別(成行・指値ほか)と有効期限を指定できる発注 / `notify_order` による注文の状態遷移の通知 / 自作のデータ供給(`feeds.DataBase` の継承)/ 手数料の設定 / Interactive Brokers・Oanda・VisualChart のストアとブローカー。
- **料金の構造**: GPLv3+ の無償配布。PyPI の project_urls は Download と Homepage の 2 つだけで、料金ページに当たるものが無い(一次資料)。**改変して配布する場合は GPL の条件が掛かる**(推定 — LICENSE 本文はこの回では取っていない)。登録は不要(実測)。
- **到達・導入・実行**: 依存がきわめて少なく、隔離 venv での導入が最も速かった。最小の実行は自作の feed で合成の日足を流し、成行買いと指値売りの往復が約定した(実測)。
- **当方の用途との相性**: `feeds.DataBase` を継承して `_load` を書けば任意の列を流せた(実測)。時刻は `date2num` / `num2date` で float に持つ。
- **当方に無いもの(全部)**: 注文の `exectype` と `valid`(有効期限)/ `notify_order` の状態遷移の通知 / Interactive Brokers・Oanda・VisualChart のストア / 自作 feed の差し込み口。
- **危険**: 配布元は PyPI と GitHub で一致。setup.py も同梱バイナリも無い。外部ホストは yahoo のデータ端点と文書の URL。**PyPI の更新が 2023 年で止まっており、GitHub の pushed_at も 2024 年**(一次資料)。宣伝・詐欺の兆候は見つからなかった。**実弾のストアを持つので、鍵を置けば発注できる。**

#### 3. PyBroker(深掘り)

- **できること**: 文脈オブジェクトに注文の意思を書き込む形の戦略 / 成行と指値 / 滑りの模型 / 機械学習の模型の登録と学習 / 最適化 / ブートストラップによる評価 / ベクトル化された指標 / 並列実行 / キャッシュ / 拡張(ext)。
- **料金の構造**: **配布は無償だが Commons Clause 付き**で、逐語「the grant of rights under the License will not include, and the License does not grant to you, the right to Sell the Software.」(一次資料)。金額の課金は無く、制限は「売らない」条件。既定のデータ源のうち Alpaca は鍵が要るが、DataFrame を直接渡せば鍵なしで回った(実測)。
- **到達・導入・実行**: PyPI の名前は `lib-pybroker` で、import 名は `pybroker`。隔離 venv で導入し、最小の実行で成行買いと指値売りの往復が約定した(実測)。
- **当方の用途との相性**: symbol / date / open / high / low / close / volume の DataFrame をそのまま渡せた(実測)。
- **当方に無いもの(全部)**: 滑りの模型(`slippage.py`)/ 機械学習の模型の登録(`model.py`)/ 最適化(`optimize.py`)/ 評価指標とブートストラップ(`eval.py`)/ ベクトル化(`vect.py`)/ 並列実行(`parallel.py`)/ キャッシュ(`cache.py`)/ Alpaca の実弾ブローカーと live のデータ。
- **危険**: **ライセンスが OSI のオープンソースではない**(Commons Clause)。PyPI の Homepage が GitHub を指さず自前のドメインを指す。配布物に setup.py も同梱バイナリも無い。既知の脆弱性は PyPI の vulnerabilities が空。**週DL数がこの回では取れなかった**(pypistats が 4 回とも 429)ので、供給網の検査のうち利用者数の裏取りだけが欠けている。宣伝・詐欺の兆候は見つからなかった。**依存に実弾のブローカーが入る。**

#### 4. bt(深掘り)

- **できること**: 比重を決めるアルゴリズムの列を組み立てて回す形のバックテスト / 複数戦略の入れ子 / 手数料の関数 / 成績の統計。
- **料金の構造**: MIT の無償配布。料金ページに当たるものが PyPI にも project_urls にも無い(一次資料)。登録は不要(実測)。
- **到達・導入・実行**: 導入と実行は通った。**ただし委任文 §5-4 が求める「成行と指値の 1 往復」は、枠組みに注文の種別が無いため書けない**(実測)。名前に limit を含むアルゴリズムは 2 つあるが、どちらも比重の制限であって指値注文ではない。
- **当方の用途との相性**: 終値の DataFrame は入るが、約定・清算のような明細を入れる形ではない(実測)。
- **当方に無いもの(全部)**: 比重の決め方のアルゴリズム群(`WeighEqually` / `LimitWeights` / `LimitDeltas` ほか)/ 複数戦略を木構造で入れ子にする仕組み / 比重の乖離でリバランスを起こす仕組み。
- **危険**: **配布物に同梱バイナリが 1 件ある**(Cython の `.so`)。Python の部分にしか走査が掛かっておらず、`.so` の中身はこの環境で読む手段を持たない(未確認)。それ以外は配布元の一致・setup.py の不在・脆弱性の空を確認した。宣伝・詐欺の兆候は見つからなかった。自動発注の機能は無い。

### A と B と C の結果

**A(PyPI / GitHub への到達だけ済んでいた 12 件)**

| 道具 | この回の結果 |
|---|---|
| Basana | **深掘り完了**(表に語彙のすべての項目) |
| Backtrader | **深掘り完了**(同上) |
| PySystemtrade | **未完了。**PyPI に無く pip の経路が使えない。git clone は本体の一括取得になるため委任文 §6-6 で打っていない。第 2 経路のコマンドを候補の一覧の 3 番に書いた |
| PyBroker(lib-pybroker) | **深掘り完了**(週DL数だけ 429 で取れず、試した手段を根拠の欄に書いた) |
| bt | **深掘り完了**(最小実行は「一部のみ可」= 指値が書けない) |
| Ziplime / Superalgos / OpenTrader / CryptoSignal / fast-trade / OctoBot / pybotters | **未着手。**時間の上限に達した。浅いまま候補の一覧に残した |

**B(持ち越し 6 件)**

| 項目 | この回の結果 |
|---|---|
| DeviaVir/zenbot・Bot18 の Node.js 導入 | **未着手**(起動指定で優先度が低いとされたため、A を優先した) |
| Mendl-Labs/BacktestingCore | **未着手** |
| Luczinsritter/event_driven_backtesting_engine | **未着手** |
| mlflow | **未着手** |

**C(3 回目の未確認の取り直し)**

| 項目 | この回の結果 |
|---|---|
| zipline-reloaded の週DL数 | **取れた。**last_week=2839、last_month=11992、last_day=530(一次資料。https://pypistats.org/api/packages/zipline-reloaded/recent 取得日 2026-09-22 / 生ログ 19 行) |
| VnPy の週DL数 | **取れた。**last_week=2289、last_month=11503、last_day=351(一次資料。同端点の vnpy / 生ログ 97 行と 99 行) |
| Qlib の週DL数 | **取れた。**last_week=8035、last_month=35609、last_day=1083(一次資料。同端点の pyqlib / 生ログ 97 行と 99 行) |
| Jesse の週DL数の再現 | **再現した。**last_week=777、last_month=4768、last_day=223。3 回目の値と一致(一次資料。生ログ 25 行) |
| 5 道具の星 | **4 件取れた。**Jesse 8566 / VnPy 45495 / Qlib 48743 / Lean 21718。**zipline-reloaded だけ取れなかった**(9 件を指定して 8 件しか返らず、返らなかったのが stefan-jansen/zipline-reloaded。生ログ 47 行) |
| 5 道具のコミット数 | **取れなかった。**試したこと: `mcp__github__search_repositories` は stars と forks しか返さない / curl での GitHub API は 403。コミットの総数を返す端点は今回打っていない |
| Jesse の実弾プラグインの金額 | **未着手。**3 回目の 403(jesse.trade/pricing)の別経路を探す時間が無かった |

**この回で埋めた 3 回目の「未確認」は、週DL数 4 件と星 4 件である。**コミット数と Jesse の金額は残った。

### 残りの候補名

次回の実行に渡す。深掘りが済んでいないもの。

- PySystemtrade / Ziplime / Superalgos / OpenTrader / CryptoSignal / fast-trade / OctoBot / pybotters
- DeviaVir/zenbot / Bot18 の Node.js 導入
- Mendl-Labs/BacktestingCore / Luczinsritter/event_driven_backtesting_engine
- mlflow
- 取り直しの残り: 5 道具のコミット数 / zipline-reloaded の星 / lib-pybroker の週DL数 / Jesse の実弾プラグインの金額

### STRATEGY_IDEAS.md 向け候補(提案のみ、未マージ)

- 「バックテストの道具」の中に、注文の約定を模擬しない族(比重のリバランス型 = bt)と、注文の種別を持つ族(Basana / Backtrader / PyBroker)がある。当方の指値の埋まり方の研究に突き合わせられるのは後者だけである。
- Basana の backtesting は、流動性の模型・気配のスプレッド・貸借を既定で持つ。当方の `engine.py` が「通過した約定なら埋まったとみなす」としている箇所の別実装の候補になる。

### DATA.md 向け候補(提案のみ、未マージ)

- PyBroker のライセンスは Commons Clause 付きで、OSI の意味でのオープンソースではない。**「無料」と「オープンソース」を分けて台帳に書く必要がある。**

### 予算

| 項目 | 値 |
|---|---|
| 上限 | 1 回 5 万トークン・20 分 |
| 実績 | 20 分の上限に達したため中断した。深掘りは 4 件(Basana / Backtrader / PyBroker / bt)で止まり、A の残り 7 件と B の 4 件は未着手 |
| 未完了 | 候補の一覧の 3 番(PySystemtrade)と 6〜17 番。区分 1 は**未完了**(委任文 §2 の条件 = 残りの候補が空で、新しい検索計画が新しい候補を 1 件も出さない、を満たしていない) |

### 受け入れ検査で残した行(自分で閉じなかったもの)

委任文 §12「**誤検出だと判断しても、自分で閉じてはならない。**直さずに残し、その行と理由を報告に 1 件ずつ書いて**リードに渡す**」に従い、2 件を残した。

1. **K11 の指摘は全部 3 回目の節の中にある。**原因は検査に渡した生ログが 4 回目の 1 本だけで、3 回目の表の根拠が指す `20260922_tools_1_run3.log` が渡されていないこと。`scripts/check_scan_report.py` は `sys.argv[2:]` を読むので**生ログを複数渡せる**。3 回目と 4 回目の両方を渡すと K11 は消え、残るのは下の 2 の K5 だけになる(実測: `python3 scripts/check_scan_report.py docs/DATA/SCAN_2026-09-21_tools.md docs/DATA/probes/20260922_tools_1_run3.log docs/DATA/probes/20260922_tools_1_run4.log`)。起動指定のコマンドは 4 回目の 1 本だけを渡す形だったので、指定どおりに打った結果を下に貼っている。**4 回目の節の K11 は当たっていない。**
2. **K5 は 4 回目の節。**`Backtrader` の `install所要秒` と `実行所要秒` を、検査が「同じ単位『秒』に別の値」として拾っている。項目名が別(導入の所要と実行の所要)なので値が違って当然だが、**誤検出だと自分で判断して閉じない。**リードに判定を渡す。

## 受け入れ検査の出力

リードが受領後に打ち直した出力(生ログ 2 本 = run3 と run4 を渡した。調査班の指摘 1 のとおり、
起動指定が run4 の 1 本だけを渡す形だったため K11 が 3 回目の節に当たっていた)。
判定は `docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run4.md`。

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
---- 検査対象の合計 0 件(K12 を除く。貼り付けはこの数で照合する)
---- 合計 1 件
```


## 区分1 — 5 回目の実行(2026-09-22)

委任文: `docs/DATA/delegations/20260922_tools_survey_prompt.md@ce0012c95154`。生ログ: `docs/DATA/probes/20260922_tools_1_run5.log`。
4 回目のリードの検収(`docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run4.md`)で残った
取り直し 4 件と、深掘り待ちの候補を、発見した順に潰した。**4 回目と同じく、根拠の欄にはどのフィールドを見たかを
`info.author = "…"` の形で書き、語や件数はその場で数えた値だけを書いた。**

### 当方の道具立て(`python3 scripts/tools_inventory.py` の出力全文。§8)

```
# 当方の道具立て(git ls-files から生成。2026-09-22T08:07:42Z、HEAD 47bc8e7。コマンド: python3 scripts/tools_inventory.py)

## src/bot(package: ファイル数 / ファイル名)
- src/bot: 7 / atomic_file.py constants.py logging_setup.py main.py products.py radar.py settings.py
- src/bot/backtest: 3 / engine.py metrics.py walk_forward.py
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
- check_*: 8 / check_api.py check_data_ledger.py check_k1_binance.py check_k1_bitflyer_data.py check_kabu_api.py check_liquidation_feeds.py check_liquidation_history_depth.py check_scan_report.py
- build_*: 7 / build_basis.py build_bitflyer_lightchart_csv.py build_burst_library.py build_flow.py build_fx_event_library.py build_fx_event_library_2005_2014.py build_storm_library.py
- record_*: 5 / record_funding_basis.py record_liquidations.py record_oi.py record_realtime.py record_venues.py
- jev/: 3 / client.py redact.py schemas.py
- verify_*: 3 / verify_gates.py verify_liq_instrument.py verify_snapshots.py
- (単発): 2 / _research_audit_gate.py dashboard.py
- judge_*: 2 / judge_board_round.py judge_gates.py
- k1_*: 2 / k1_binance_data_quality.py k1_source.py
- paper_*: 2 / paper_on1.py paper_onr.py
- repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.py
- constants_*: 1 / constants_inventory.py
- data_*: 1 / data_quality.py
- explore_*: 1 / explore_o3c_oi_axis.py
- extract_*: 1 / extract_tape.py
- intake_*: 1 / intake_ledger.py
- liquidation_*: 1 / liquidation_report.py
- mirror_*: 1 / mirror_bitmex_archive.py
- normalize_*: 1 / normalize_bitflyer_executions.py
- phase2_*: 1 / phase2_seal.py
- preflight_*: 1 / preflight_prereg.py
- probe_*: 1 / probe_api_latency.py
- replay_*: 1 / replay_scalp_storm.py
- retention_*: 1 / retention_snapshot.py
- tools_*: 1 / tools_inventory.py
- tp_*: 1 / tp_operating_curve.py
- trace_*: 1 / trace_metrics.py
- validate_*: 1 / validate_composite.py
- x_*: 1 / x_fetch.py
- (.py 以外の scripts: 3 = scripts/fetch_all.sh scripts/install_git_hooks.sh scripts/regen_hook_manifest.sh)

## config: 32
  config/composite.yaml config/config.yaml config/constants.yaml config/etf_measure.yaml config/jev_delegation_tiers.yaml config/jev_design_examples/o3c_covariates.yaml config/jev_design_examples/o3c_observables.yaml config/jev_design_examples/signal2_covariates.yaml config/jev_design_examples/signal2_observables.yaml config/jev_design_examples/signal3_covariates.yaml config/jev_design_examples/signal3_observables.yaml config/jev_design_examples/signal4_covariates.yaml config/jev_design_examples/signal4_observables.yaml config/jev_design_examples/signal5_covariates.yaml config/jev_design_examples/signal5_observables.yaml config/jev_design_examples/signal6_covariates.yaml config/jev_design_examples/signal6_observables.yaml config/jev_design_examples/signal7_observables.yaml config/jev_design_examples/signal8_covariates.yaml config/jev_design_examples/signal8_observables.yaml config/jev_design_examples/signal8_observables_independent.yaml config/jev_design_examples/signal_covariates.yaml config/jev_design_examples/signal_observables.yaml config/jev_routes.yaml config/o3c_jev_state_bands.yaml config/o3c_signal_logit_chain.yaml config/o3c_signal_logit_first.yaml config/o3c_signal_logit_value_chain.yaml config/o3c_signal_logit_value_first.yaml config/on1_live.yaml config/products.yaml config/risk_limits.yaml

## deploy: 19
  deploy/bitflyer-bot.service deploy/bitflyer-fetch.service deploy/bitflyer-fetch.timer deploy/check_liq_recorder.bat deploy/etf_measure_entry.bat deploy/etf_measure_exit.bat deploy/fetch_all.bat deploy/mirror_bitmex.bat deploy/nightly_restart.bat deploy/on1_entry.bat deploy/on1_exit.bat deploy/probe_latency.bat deploy/reset_kill.bat deploy/restart_all.bat deploy/run_paper.bat deploy/setup.sh deploy/share_logs.bat deploy/start_all.bat deploy/stop_all.bat

## tests(ファイル): 139
  tests/conftest.py tests/fixtures/jev_ops/decisions.json tests/fixtures/jev_ops/notifications.jsonl tests/fixtures/jev_ops/status_page.html tests/test_app_fx_integration.py tests/test_audit_gates_wired.py tests/test_backtest.py tests/test_bitmex_mirror.py tests/test_board.py tests/test_board_round.py tests/test_board_walk.py tests/test_bot_research_overnight.py tests/test_build_flow.py tests/test_check_data_ledger.py tests/test_client.py tests/test_clock_burst.py tests/test_composite.py tests/test_constants.py tests/test_constants_inventory.py tests/test_dashboard.py tests/test_data_quality.py tests/test_data_quality_incremental.py tests/test_deploy.py tests/test_engine_maker_exit.py tests/test_etf_measure.py tests/test_extract_tape.py tests/test_fetch_backfill_scripts.py tests/test_fetch_binance_daily.py tests/test_fetch_binance_vision.py tests/test_fetch_history_candles.py tests/test_gz_members.py tests/test_intake_ledger.py tests/test_intent_map_rule.py tests/test_jev_audit_eval.py tests/test_jev_audit_loop.py tests/test_jev_check.py tests/test_jev_client.py tests/test_jev_delegate.py tests/test_jev_design.py tests/test_jev_ideas.py tests/test_jev_ops.py tests/test_jev_owner_log.py tests/test_jev_redact.py tests/test_jev_reply.py tests/test_jev_report_intake.py tests/test_jev_schemas.py tests/test_jev_scripts.py tests/test_jev_survey.py tests/test_jev_trace_export.py tests/test_judge_gates.py tests/test_k1_bitflyer_source.py tests/test_k1_bybit_source.py tests/test_k1_delay_decomp.py tests/test_k1_delay_entry.py tests/test_k1_flip_body.py tests/test_k1_lookahead.py tests/test_k1_no_invalidation.py tests/test_k1_round5.py tests/test_k1_seal_guard.py tests/test_k1_xvenue.py tests/test_liq_bands.py tests/test_liq_response.py tests/test_liq_response_dedup.py tests/test_liquidation_reader.py tests/test_maker_execution.py tests/test_market_data.py tests/test_market_view.py tests/test_max_hold.py tests/test_modes.py tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_ext.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_rows4.py tests/test_o3c_signal_calib.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore2.py tests/test_o3c_signal_explore3.py tests/test_o3c_signal_explore4.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_policy.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_on1_forward.py tests/test_on1_live.py tests/test_onr.py tests/test_onr_forward.py tests/test_orders.py tests/test_paper_state.py tests/test_phase2_p2_01.py tests/test_phase2_p2_01_final.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_phase2_p2_03.py tests/test_phase2_p2_03_final.py tests/test_phase2_p2_03_iter2.py tests/test_phase2_p2_04.py tests/test_phase2_seal.py tests/test_portfolio_and_strategy.py tests/test_position_ladder.py tests/test_preflight_prereg.py tests/test_probe_api_latency.py tests/test_qa_make_known_answer.py tests/test_qa_make_known_answer_maker.py tests/test_qa_make_known_answer_maker3.py tests/test_qa_make_known_answer_steer.py tests/test_qa_maker_fill_ref.py tests/test_qa_pipeline_known_answer.py tests/test_qa_score_audit.py tests/test_radar.py tests/test_realtime_recorder.py tests/test_record_funding_basis.py tests/test_record_liquidations.py tests/test_record_liquidations_writer.py tests/test_record_venues.py tests/test_repair_gz_listing.py tests/test_research_protocol_rules.py tests/test_resilience.py tests/test_retention_snapshot.py tests/test_risk.py tests/test_scalp_logic.py tests/test_sealed_load_diagnostic.py tests/test_sealed_ts_us.py tests/test_short_margin.py tests/test_tp_sl.py tests/test_verify_snapshots.py tests/test_wick_stop.py tests/test_x_fetch.py tests/test_xborder.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_fx.py tests/test_xborder_p2_known_answer.py tests/test_xborder_p2_state.py

## .claude/hooks: 8
  .claude/hooks/_verify_manifest.sh .claude/hooks/delegation_audit_gate.sh .claude/hooks/deny_protected_paths.sh .claude/hooks/jev_notice.sh .claude/hooks/owner_options_gate.sh .claude/hooks/owner_turn_digest.sh .claude/hooks/session_start_digest.sh .claude/hooks/trace_snapshot.sh

## .claude/agents: 3
  .claude/agents/owner-auditor-candidate.md .claude/agents/owner-auditor.md .claude/agents/owner-model-auditor.md

## .claude/skills: 9
  .claude/skills/delegated-study/SKILL.md .claude/skills/owner-audit/SKILL.md .claude/skills/owner-options/SKILL.md .claude/skills/owner-procedure/SKILL.md .claude/skills/research-protocol/SKILL.md .claude/skills/research-squad/SKILL.md .claude/skills/typesafe-ai/LICENSE .claude/skills/typesafe-ai/SKILL.md .claude/skills/x-research/SKILL.md

## githooks: 1
  githooks/pre-push

## docs(.md): 296
  docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11_control_review.md docs/AUDITOR/EVAL_2026-09-11b.md docs/AUDITOR/IMPROVEMENT.md docs/AUDITOR/JEV/LABELS_NOTES_2026-09-19.md docs/AUDITOR/JEV/PREREG_2026-09-19.md docs/AUDITOR/KNOWN_ANSWERS.md docs/AUDITOR/KNOWN_ANSWERS_ADDENDUM.md docs/AUDITOR/OWNER_MODEL_SOURCE.md docs/AUDITOR/PRINCIPLES.md docs/AUDITOR/PROCESS_METRICS.md docs/AUDITOR/PROPOSED_CHANGES_2026-09-11.md docs/AUDITOR/READDO/audit_stop.md docs/AUDITOR/READDO/before_unseal.md docs/AUDITOR/READDO/owner_objection.md docs/AUDITOR/READDO/push_blocked.md docs/AUDITOR/READDO/repeat_defect.md docs/AUDITOR/TREND.md docs/AUDITOR/VERDICTS/2026-09-11_k1_closure_entries.md docs/AUDITOR/VERDICTS/2026-09-11_proposed_changes_and_eval_b.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_execution.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_plan.md docs/AUDITOR/VERDICTS/2026-09-12_o3c_reframe_reading.md docs/AUDITOR/VERDICTS/2026-09-12_p14_liquidation_fix.md docs/AUDITOR/VERDICTS/2026-09-12_p4n_nightly_restart.md docs/AUDITOR/VERDICTS/2026-09-12_rules_reduction.md docs/AUDITOR/VERDICTS/2026-09-16_policy4_report.md docs/AUDITOR/VERDICTS/2026-09-17_anchor_report.md docs/AUDITOR/VERDICTS/2026-09-17_closure.md docs/AUDITOR/VERDICTS/2026-09-17_data_collection.md docs/AUDITOR/VERDICTS/2026-09-17_missing.md docs/AUDITOR/VERDICTS/2026-09-17_oi_distance.md docs/AUDITOR/VERDICTS/2026-09-17_price_level.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_ext.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_full.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_rows4.md docs/AUDITOR/VERDICTS/2026-09-18_oi_distance_split.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_design.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r10.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r2.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r3.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r4.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r5.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r6.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r7.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r8.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r9.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_run12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r11.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_r2_prereg.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r2.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r3.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_result.md docs/AUDITOR/VERDICTS/2026-09-19_signal_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_report.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_materials_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_result.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_design.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_result.md docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md docs/AUDITOR/VERDICTS/2026-09-21_tools_survey_prompt.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run2.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run3.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run4.md docs/AUDITOR/VERDICTS/2026-09-22_tools_survey_prompt_v12.md docs/AUDITOR/VERDICTS/README.md docs/AUDITOR/answers/KA-01.md docs/AUDITOR/answers/KA-02.md docs/AUDITOR/answers/KA-04.md docs/AUDITOR/answers/KA-05.md docs/AUDITOR/answers/KA-06.md docs/AUDITOR/answers/KA-07.md docs/AUDITOR/answers/KA-08.md docs/AUDITOR/answers/KA-09.md docs/AUDITOR/answers/KA-10.md docs/AUDITOR/answers/KA-16.md docs/AUDITOR/answers/KA-17.md docs/AUDITOR/answers/KA-18.md docs/AUDITOR/answers/KA-19.md docs/AUDITOR/answers/KA-20.md docs/AUDITOR/answers/KA-21.md docs/AUDITOR/answers/KA-22.md docs/AUDITOR/answers/KA-23.md docs/AUDITOR/answers/KA-24.md docs/AUDITOR/answers/KA-25.md docs/AUDITOR/answers/KA-26.md docs/AUDITOR/answers/KA-27.md docs/AUDITOR/answers/KA-28.md docs/AUDITOR/before/HYGIENE_2026-09-11.md docs/AUDITOR/before/KA-01.md docs/AUDITOR/before/KA-02.md docs/AUDITOR/before/KA-04.md docs/AUDITOR/before/KA-05.md docs/AUDITOR/before/KA-06.md docs/AUDITOR/before/KA-07.md docs/AUDITOR/before/KA-08.md docs/AUDITOR/before/KA-09.md docs/AUDITOR/before/KA-10.md docs/AUDITOR/before/KA-16.md docs/AUDITOR/before/KA-17.md docs/AUDITOR/before/KA-18.md docs/AUDITOR/before/KA-19.md docs/AUDITOR/before/KA-20.md docs/AUDITOR/before/KA-21.md docs/AUDITOR/before/KA-22.md docs/AUDITOR/before/KA-23.md docs/AUDITOR/before/KA-24.md docs/AUDITOR/before/KA-25.md docs/AUDITOR/before/KA-26.md docs/AUDITOR/before/KA-27.md docs/AUDITOR/before/KA-28.md docs/DATA.md docs/DATA/SCAN_2026-09-16.md docs/DATA/SCAN_2026-09-21_tools.md docs/DATA/delegations/20260919_o3c_signal_explore2_prompt.md docs/DATA/delegations/20260920_o3c_cascade_read_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_jev_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore3_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore4_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore5_prompt.md docs/DATA/delegations/20260920_o3c_signal_jev_state_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials2_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_stage2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_tp_prompt.md docs/DATA/delegations/20260921_tools_survey_prompt.md docs/DATA/delegations/20260922_tools_survey_prompt.md docs/DATA/probes/20260913_liquidation_integrity.md docs/DATA/probes/20260919_reaction_prereg_outputs.md docs/DATA/probes/20260920_o3c_cascade_read.md docs/DATA/probes/20260920_o3c_materials_read.md docs/DATA/surveys/BINANCE_CM_MMR_2026-09-17.md docs/DATA/surveys/BITFLYER_HISTORY_SOURCES.md docs/DATA/surveys/ETF_ALTERNATIVES.md docs/DATA/surveys/G2_DATA_INVENTORY.md docs/DATA/surveys/LIQUIDATION_FEED_REACHABILITY.md docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_ACCEPTANCE_2026-09-13.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_A_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_B_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_C_HYPERLIQUID_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_D_VENUE_UNIVERSE_2026-09-12.md docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md docs/DATA_CONSUMPTION_LOG.md docs/DELEGATION.md docs/DISCUSSIONS/2026-09-04_postmortem_tp_precursor.md docs/DISCUSSIONS/2026-09-06_data_dependency.md docs/DISCUSSIONS/2026-09-08_external_ecosystem.md docs/DISCUSSIONS/2026-09-08_matilda_intent_vs_test.md docs/DISCUSSIONS/2026-09-09_prereg_deep_dive.md docs/DISCUSSIONS/2026-09-09_the_day_nothing_shipped.md docs/DISCUSSIONS/2026-09-12_docs_reorg_plan.md docs/DISCUSSIONS/2026-09-12_generation_vs_filtering.md docs/DISCUSSIONS/2026-09-12_rules_inventory.md docs/DISCUSSIONS/2026-09-12_rules_reduction_proposal.md docs/DISCUSSIONS/2026-09-13_root_cause.md docs/DISCUSSIONS/2026-09-13_worst_day.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/PLAN.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/README.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/STAGE0_hook_probe.md docs/DISCUSSIONS/2026-09-16_scope_claim_gate_proposal.md docs/DISCUSSIONS/2026-09-18_jev_trade_integration_decision_for_fable_v2.md docs/DISCUSSIONS/2026-09-19_jev_adoption_review.md docs/DISCUSSIONS/2026-09-19_jev_common_module_review.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/A_judgment_points.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/B_failures.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/C_vendor_sources.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/D_study_notes.md docs/INCIDENTS.md docs/INDEX.md docs/JEV.md docs/NEGATIVE_FACTS.md docs/OPERATIONS.md docs/OPERATIONS_JPX.md docs/OWNER_LOG.md docs/OWNER_PROCEDURES.md docs/OWNER_STATUS.md docs/PHASE2/EXEC/EXEC_FLOOR_PREREG.md docs/PHASE2/EXEC/RESULT.md docs/PHASE2/INSTRUMENT_VERIFY/AUDIT_LEDGER_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-16_policy4.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-17_anchor.md docs/PHASE2/K1/AUDIT_TRIAGE.md docs/PHASE2/K1/BINANCE_PLAN.md docs/PHASE2/K1/DEEPDIVE_PLAN.md docs/PHASE2/K1/FRESH_BITFLYER_PREREG.md docs/PHASE2/K1/H1_PREREG.md docs/PHASE2/K1/H2_PREREG.md docs/PHASE2/K1/H3_DECOMP_PREREG.md docs/PHASE2/K1/H3_PREREG.md docs/PHASE2/K1/HANDOFF.md docs/PHASE2/K1/JUDGEMENT_PREREG.md docs/PHASE2/K1/PREFLIGHT.md docs/PHASE2/K1/PREREG.md docs/PHASE2/K1/RESULT.md docs/PHASE2/K1/ROUND5_PREREG.md docs/PHASE2/K1/XVENUE_PREREG.md docs/PHASE2/K1/binance/CHECKS.md docs/PHASE2/O3C/BRANCH_MAP.md docs/PHASE2/O3C/DATA_AVAILABILITY.md docs/PHASE2/O3C/DATA_COLLECTION_2026-09-17.md docs/PHASE2/O3C/INTENT_MAP.md docs/PHASE2/O3C/MISSING_2026-09-17.md docs/PHASE2/O3C/OWNER_INTENT_2026-09-12.md docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/FULL_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_SPLIT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_DRAFT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_R2_PREREG_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RESULT_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RUN12_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/ROWS4_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/SAMPLE_2026-09-17.md docs/PHASE2/O3C/REFRAME/DIFF_2026-09-12.md docs/PHASE2/O3C/REFRAME/LEAD_READING_2026-09-12.md docs/PHASE2/O3C/REFRAME/data_engineer.md docs/PHASE2/O3C/REFRAME/discretionary_trader.md docs/PHASE2/O3C/REFRAME/liquidation_engine.md docs/PHASE2/O3C/REFRAME/market_maker.md docs/PHASE2/O3C/REFRAME/microstructure.md docs/PHASE2/O3C/SIGNAL/CONTINUE_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/CONTINUE_JEV_RUN_NOTE_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE2_DELEGATE_REPORT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/EXPLORE3_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE4_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE5_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/JEV_STATE_PREVIEW_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS2_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW2_2026-09-19.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW3_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW4_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW5_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW6_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW9_2026-09-21.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_RESULT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE1_REPORT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE2_REPORT_2026-09-21.md docs/PHASE2/O3C/STAGE0A_2026-09-14.md docs/PHASE2/O3C/TRIGGER_TRACE.md docs/PROJECT_GOAL.md docs/STRATEGY_IDEAS.md docs/legacy/KATSUO_INTENT_MAP.md docs/legacy/KATSUO_PARAMETER_INVENTORY.md docs/legacy/README.md

## backtest_data(ディレクトリ数)
  147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H_20260905 audit_fetch_JPX_n225f_months_20260906 audit_fetch_JPX_tick_20260906 audit_fetch_P2-08_docs_20260906 audit_fetch_P2-08b_20260906 audit_fetch_bitflyer_history_20260906 audit_fetch_etf_alternatives_20260906 audit_fetch_etf_units_20260906 audit_fetch_micro_fee_20260906 auto_bitflyer_executions_20260905 auto_bitflyer_executions_20260921 auto_oi_snapshots_20260905 auto_oi_snapshots_20260921 auto_okx_long_short_ratio_20260905 auto_okx_open_interest_1h_20260905 auto_okx_open_interest_1h_20260921 auto_okx_open_interest_5m_20260905 auto_okx_open_interest_5m_20260906 auto_okx_open_interest_5m_20260907 auto_okx_open_interest_5m_20260908 auto_okx_open_interest_5m_20260909 auto_okx_open_interest_5m_20260910 auto_okx_open_interest_5m_20260911 auto_okx_open_interest_5m_20260912 auto_okx_open_interest_5m_20260915 auto_okx_open_interest_5m_20260918 auto_okx_open_interest_5m_20260921 auto_venues_20260905 auto_venues_20260921 binance_BTCUSDT_1m.csv binance_BTCUSDT_1m_20170801_20231231 binance_BTCUSDT_1m_20240101_20260831 binance_BTCUSDT_1m_210d_20260820.csv.gz binance_BTCUSDT_1s_20260723_20260906 binance_BTCUSDT_aggTrades_20260723_20260906 binance_BTCUSDT_aggTrades_tardis_days binance_XRPUSDT_1d.csv binance_XRPUSDT_1m.csv binance_XRPUSDT_4h.csv binance_cm_o3c_20260913 binance_cm_o3c_supp_20260917 binance_um_BTCUSDT_aggTrades_20260723_20260906 bitbank_btc_jpy_transactions_monthly_first_days bitbank_xrp_jpy_1m.csv bitflyer_executions_backfill_20260921 bitflyer_executions_us_20260723_20260906 bitflyer_lightchart_BTC_JPY_1m_20260906 bitflyer_lightchart_FX_BTC_JPY_1m_20260906 bitmex_insurance_20260912 bitmex_trade_1s_XBTUSD board_round_20260904 burst_events_20260820 bybit_BTCUSDT_1m_20260910 bybit_reachability_check_20260906 candles_BTC_JPY_20260820.csv candles_ETH_JPY_20260820.csv candles_FX_BTC_JPY_20260820.csv candles_FX_BTC_JPY_30d_20260820.csv candles_FX_BTC_JPY_31d_20260823.csv.gz candles_XRP_JPY_20260820.csv coinalyze_liquidations_20260921 daily_btcusd_bitstamp_20260828.csv.gz daily_btcusd_coinbase_20260828.csv.gz daily_btcusd_yahoo_20260828.csv.gz daily_ethusd_bitstamp_20260828.csv.gz daily_ethusd_coinbase_20260828.csv.gz daily_ethusd_yahoo_20260828.csv.gz executions_FX_BTC_JPY_31d_20260823.csv.gz executions_FX_BTC_JPY_31d_20260908 flow_FX_BTC_JPY_20260820.csv fred_DEXJPUS.csv fred_DFF.csv fred_DGS2.csv fred_IR3TIB01JPM156N.csv fred_IRSTCI01JPM156N.csv fx_btc_jpy_1m_continuous_20260906 fx_event_ticks_2005_2014 fx_event_ticks_2015_2026 fx_fundamentals_20260822 fx_usdjpy_1m_20170801_20221231 fx_usdjpy_1m_20260822.csv.gz gate_liquidations_20260908 gmo_swap_usdjpy.csv jp_factors_20260905 jpx_daily_report_json_20260908 jpx_etf_daily_20260905 jpx_etf_daily_20260906_topix_alt liquidations_repaired_20260912 liquidations_repaired_20260917 mini_topixf_225labo_20260907 n225f_225labo_20260828 nk225_events_20260904 o3c_oi_distance_20260917 o3c_oi_distance_split_20260918 o3c_price_level_band_20260917 o3c_price_level_bundle_first_20260917 o3c_price_level_full_20260917 o3c_price_level_full_20260917_b005 o3c_price_level_full_20260917_b025 o3c_price_level_full_20260917_w72 o3c_price_level_full_20260917_w8 o3c_price_level_rows4_20260917 o3c_price_level_sample_20260917 o3c_price_level_sample_20260917_limitprice o3c_reaction_20260918_anchor o3c_reaction_20260918_anchor_trades o3c_reaction_20260918_anchor_trades_sample o3c_reaction_20260918_anchor_v1_rawcols o3c_reaction_20260918_full o3c_reaction_20260918_judge o3c_reaction_20260918_sample o3c_reaction_20260918_scale12_judgmentdays o3c_signal_continue_20260920 o3c_signal_explore2_20260919 o3c_signal_explore3_20260920 o3c_signal_explore4_20260920 o3c_signal_explore5_20260920 o3c_signal_explore_20260919 o3c_signal_materials_20260920 o3c_signal_policy_20260920 o3c_signal_value_20260921 okx_20260905 okx_btc_lsratio_1h_20260823.csv okx_btc_lsratio_5m_20260823.csv okx_btc_oi_1h_20260823.csv okx_btc_oi_5m_20260823.csv phase2_runs phase2_sealed qa_known_answer_20260905 qa_known_answer_maker3_20260907 qa_known_answer_maker3_v2_20260905 qa_known_answer_maker3_v3_20260905 qa_known_answer_maker4_20260905 qa_known_answer_maker4_r2_20260905 qa_known_answer_maker_20260905 qa_known_answer_steer_20260905 qa_pipeline_daily_20260905 qa_pipeline_daily_20260906 qa_pipeline_taker_20260905 regime_composite_20260901 reit_onr_20260904 storm_events_20260820 topixf_225labo_20260907 venue_survey_20260827 yutai_20260904
```

### 検索計画

委任文 §2「**2 回目以降の実行**: 前回の「残りの候補名」があれば、まずそれを深掘りする(検索計画は打ち直さない)」と、
リードの起動指定「**検索計画 6 本はまだ打ち直しません。**残りの候補を先に潰します」に従い、この回も 6 本とも打っていない。

| 幅 | 日本語クエリ | 英語クエリ | 実行 |
|---|---|---|---|
| 狭い | (未作成) | (未作成) | 未実行(残りの候補が空になっていないため) |
| 中間 | (未作成) | (未作成) | 未実行(同上) |
| 広い | (未作成) | (未作成) | 未実行(同上) |

### 出典

| URL / 経路 | 方法 | 生ログの行 |
|---|---|---|
| https://github.com/stefan-jansen/zipline-reloaded | WebFetch | 2 |
| https://github.com/gbeced/basana | WebFetch | 4 |
| https://github.com/mementum/backtrader | WebFetch | 5 |
| https://github.com/edtechre/pybroker | WebFetch | 6 |
| https://github.com/pmorissette/bt | WebFetch | 7 |
| https://api.github.com/repos/stefan-jansen/zipline-reloaded | curl(403) | 9 |
| https://pypistats.org/api/packages/lib-pybroker/recent | curl(429) | 12 |
| https://ungh.cc/repos/stefan-jansen/zipline-reloaded | curl | 26 |
| https://api.pepy.tech/api/v2/projects/lib-pybroker | curl(401) | 27 |
| https://web.archive.org/web/2026/https://jesse.trade/pricing | curl(接続切断) | 28 |
| https://jesse.trade/help/faq/why-do-i-have-to-pay-for-live-i-thought-its-open-source | WebFetch(403) | 29 |
| https://docs.jesse.trade/docs/livetrade.html | WebFetch | 30 |
| https://jesse.trade/pricing(UA を 2 種類で) | curl(403) | 31 |
| http://archive.org/wayback/available?url=jesse.trade/pricing | curl | 33 |
| https://pypistats.org/packages/lib-pybroker | WebFetch | 25 |
| https://github.com/robcarver17/pysystemtrade | git clone --depth 1 | 35 |
| https://pypi.org/pypi/ziplime/json ほか 4 件 | curl | 40 |
| https://raw.githubusercontent.com/jrmeier/fast-trade/master/LICENSE | curl | 67 |
| https://ungh.cc/repos/jrmeier/fast-trade | curl | 68 |
| https://ungh.cc/repos/Ziplime/ziplime | curl(接続時間切れ) | 69 |
| https://pypistats.org/api/packages/fast-trade/recent | curl(429) | 70 |
| https://github.com/jrmeier/fast-trade | WebFetch | 71 |
| https://pypistats.org/packages/fast-trade | WebFetch | 72 |

### 知見

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | **GitHub のコミット総数は、リポジトリの HTML を `WebFetch` で読めば取れる。**4 回目に「この端点は星と fork しか返さない」として未確認で残した項目が、この経路で埋まった。curl での GitHub API は 403、`mcp__github__list_commits` はこのセッションの許可リスト(`komekome898-web/trade`)外として拒否される | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:2 と :8 と :9 |
| 2 | **`ungh.cc`(GitHub の公開の読み取り専用の代理)は鍵なしで星の実数を返す。**GitHub の HTML は `1.9k` のように丸めるので、実数が要るときはこちらを使う | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:26 |
| 3 | 4 回目に「この環境の GitHub 検索の端点だけが返さない」と書かれた `stefan-jansen/zipline-reloaded` は、HTML でも `ungh.cc` でも取れた。**返さないのは検索の端点だけで、リポジトリの情報そのものは 2 経路で取れる** | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:2 と :26 |
| 4 | **pypistats の API が 429 でも、同じサイトの HTML を `WebFetch` で読むと同じ数が取れる。**4 回目に 4 回とも 429 で諦めた `lib-pybroker` の週DL数は、この経路で埋まった | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:12 と :25 |
| 5 | **PySystemtrade は「純 Python の研究用リポジトリ」だが、clone すると大きい。**中身の大半は本体のコードではなく同梱の相場データで、`data/` だけで大部分を占める | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:35 と :44 |
| 6 | **この環境の Python の版が導入の足切りになる道具がある。**`ziplime` と `OctoBot` は `requires_python` が Python 3.12 以上で、既定の `python3`(3.11.15)では pip が候補を 1 つも見つけない | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:47 と :50 と :52 |
| 7 | **`fast-trade` は公開されている最新版に、自前の DataFrame を渡す経路の欠陥がある。**`build_data_frame.py` の 311 行の `infer_frequency` は引数 1 個だが、同じファイルの 78 行が引数 2 個で呼ぶ。`chart_period` を指定すると必ず TypeError で止まる | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:60 |
| 8 | **`fast-trade` は `datafile` を指定しないと取引所からデータを取りに行く。**逃げ道として `datafile` を指定すると `Exchange None not supported` で止まり、対応先は `["binanceus", "binancecom", "coinbase"]` の 3 つだけだった。自前データを渡す正しい経路は `chart_period` を外して DataFrame を直接渡すこと | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:60 と :59 |
| 9 | **`bt` に続いて `fast-trade` も、注文の種別という概念を持たない。**導入先の `*.py` を走査して `limit_order` / `market_order` / `"limit"` / `order_type` の一致が 0 件。委任文 §5-4 の「成行と指値の 1 往復」がここでも書けない | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:57 |
| 10 | **`fast-trade` は依存に `fastmcp` を持ち、配布物に `mcp_server.py` を同梱する。**バックテストの道具が LLM のエージェントから呼ばれる口を最初から持っている。当方の道具立てには対応物が無い | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:72 |
| 11 | **Jesse の実弾プラグインの金額は、この環境からはどの経路でも取れなかった。**`jesse.trade` は UA を変えても curl も WebFetch も 403、Wayback には保存が無い(`archived_snapshots` が空)。一方 `docs.jesse.trade` は 200 で、逐語「you need to register on our website to generate your license key」「The package is pre-built and the access is limited to those with an active license」までは取れた。金額の記載はこの文書に無い | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:28 から :33 |

### 候補の一覧

発見順(3 回目から引き継いだ順序のまま)。行頭の `[深掘り]` は §4.0 の表に語彙のすべての項目の行を持つものだけに付ける。それ以外は「浅い」と、何が未確認かを書く。

1. `Basana` — 非同期・イベント駆動の暗号資産向け枠組み。Apache-2.0。4 回目に深掘り済み。この回ではコミット数だけを取り直した。
2. `Backtrader` — バックテストの機関。GPLv3+。4 回目に深掘り済み。この回ではコミット数だけを取り直した。
3. PySystemtrade — **この回で clone を打ったが、大きすぎたので止めた。**リードの条件(200 MB を超えたら止めて消す)に従い、測って消した。**浅い**(版・依存・導入・最小実行が未確認)。
4. `PyBroker` — PyPI 上の名前は lib-pybroker。Apache License 2.0 with Commons Clause。4 回目に深掘り済み。この回ではコミット数と週DL数を取り直した。
5. `bt` — MIT。注文の種別という概念が無い。4 回目に深掘り済み。この回ではコミット数だけを取り直した。
6. Ziplime — **既定の `python3` では導入できない。****【リードの訂正 2026-09-22】この環境には `python3.12`(3.12.3)と `python3.13`(3.13.12)も在る(`/usr/bin/python3.12` `/usr/bin/python3.13`、リードの実測)。既定の `python3` が 3.11.15 というだけで、「この環境では導入できない」は誤り。6 回目で python3.12 の隔離 venv に導入させる。** pip が候補を 1 つも見つけない(`requires_python` が Python 3.12 以上、この環境は Python 3.11.15)。**浅い**(ライセンス・GitHub の所在・最小実行が未確認。PyPI の `info.license` が None、`info.license_expression` も None、`project_urls` も None でリポジトリの所在が PyPI からは分からない。`ungh.cc/repos/Ziplime/ziplime` は接続時間切れ)。
7. Superalgos — PyPI に無し。GitHub の LICENSE は Apache License Version 2.0(3 回目の実測)。**浅い**(版・更新日・導入・最小実行が未確認。Node.js 系で pip の経路に無い。この回は着手していない)。
8. OpenTrader — PyPI に無し。GitHub の master ブランチの LICENSE は Apache License Version 2.0(3 回目の実測)。**浅い**(版・更新日・導入・最小実行が未確認。この回は着手していない)。
9. CryptoSignal — PyPI に無し。GitHub の LICENSE は MIT License(3 回目の実測)。**浅い**(版・更新日・導入・最小実行が未確認。この回は着手していない)。
10. [深掘り] `fast-trade` — **この回の深掘り。**AGPL-3.0。低コードのバックテストの library。導入・最小実行・配布物の検査まで到達。注文の種別の概念が無く、最新版に自前 DataFrame の経路の欠陥がある。依存に `fastmcp` を持ち `mcp_server.py` を同梱する。
11. OctoBot — GPL-3.0。**既定の `python3` では導入できない**(`requires_python` が Python 3.12 以上)。**【リードの訂正 2026-09-22】この環境には `python3.12`(3.12.3)と `python3.13`(3.13.12)も在る(`/usr/bin/python3.12` `/usr/bin/python3.13`、リードの実測)。既定の `python3` が 3.11.15 というだけで、「この環境では導入できない」は誤り。6 回目で python3.12 の隔離 venv に導入させる。** **浅い**(導入・最小実行が未確認)。
12. pybotters — MIT。**浅い**(導入・最小実行・対応取引所の一次資料が未確認。この回は PyPI の情報だけを取り直した)。
13. DeviaVir/zenbot — 本家 carlos8f/zenbot の分岐。**浅い**(Node.js の導入・最小実行・保守の状態が未確認。この回は着手していない)。
14. Bot18 — carlos8f の後継。**浅い**(ライセンス欄・導入・最小実行が未確認。この回は着手していない)。
15. Mendl-Labs/BacktestingCore — master ブランチの LICENSE は Functional Source License, Version 1.1, ALv2 Future License(4 回目の実測)。**浅い**(README の原文・版・導入が未確認。この回は着手していない)。
16. Luczinsritter/event_driven_backtesting_engine — LICENSE ファイルは main と master のどちらも 404(4 回目の実測)。**浅い**(ライセンスの根拠がバッジだけ。版・導入・最小実行が未確認。この回は着手していない)。
17. mlflow — 実験の追跡の道具。**浅い**(単体での導入・最小実行をしていない。この回は PyPI の情報だけを取り直した。`info.license` は Databricks の著作権表示の文言で、SPDX の識別子ではない)。
18. `zipline-reloaded` — 3 回目に深掘り済み。この回では星とコミット数を取り直した。
19. `Jesse` — 3 回目に深掘り済み。この回では実弾プラグインの金額を取り直そうとして、どの経路でも取れなかった。
20. `VnPy` — 3 回目に深掘り済み。この回では何も足していない。
21. `Qlib` — 3 回目に深掘り済み。この回では何も足していない。
22. `Lean CLI` — 3 回目に深掘り済み。この回では何も足していない。
23. `hftbacktest` — 1 回目に深掘り済み。この回では何も足していない。

### ツール1件ごとの表

#### §4.0 の機械可読の表

**この回の深掘りは `fast-trade` の 1 件である。**残りの行は、4 回目のリードの検収が「取り直し」として渡した項目と、
この回に新しく測った項目だけを持つ(§4.0 の語彙のすべての項目を持つのは `fast-trade` だけ)。

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| `fast-trade` | 版 | 2.1.0 | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(info.version) |
| `fast-trade` | 最終更新日 | 2026-08-20T04:59:18 | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(最新版の upload_time) |
| `fast-trade` | ライセンス | GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007。PyPI の info.license は "GNU AGPLv3"、info.license_expression は None。GitHub の表示は AGPL-3.0 | 一次資料 | https://raw.githubusercontent.com/jrmeier/fast-trade/master/LICENSE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run5.log:73 と :48 と :77 |
| `fast-trade` | 言語と動作環境 | Python >=3.10。この環境は Python 3.11.15 で導入できた | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(info.requires_python)/ docs/DATA/probes/20260922_tools_1_run5.log:55 |
| `fast-trade` | 対応取引所 | archive/update_kline.py の supported_exchanges は ["binanceus", "binancecom", "coinbase"]。国内の取引所は入っていない。自前の DataFrame を渡す経路なら取引所に依存しない | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:59 |
| `fast-trade` | 星 | 596(fork 63、watchers 11) | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:74(ungh.cc の stars / forks / watchers) |
| `fast-trade` | コミット数 | 313 | 一次資料 | https://github.com/jrmeier/fast-trade 取得日 2026-09-22(リポジトリの見出しの Commits)/ docs/DATA/probes/20260922_tools_1_run5.log:77 |
| `fast-trade` | 保守者数 | PyPI の info.author = None、info.maintainer = None。PyPI からは人数が分からない。GitHub の所有者は jrmeier | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(info.author / info.maintainer)/ docs/DATA/probes/20260922_tools_1_run5.log:48 |
| `fast-trade` | 週DL数 | last_week=44、last_month=220、last_day=2 | 一次資料 | https://pypistats.org/packages/fast-trade 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run5.log:78。API の端点 /api/packages/fast-trade/recent は 429 |
| `fast-trade` | 初回公開日 | 2020-02-17T01:31:46 | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(releases の最古 upload_time) |
| `fast-trade` | 既知の脆弱性 | PyPI の vulnerabilities は長さ 0 | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(vulnerabilities) |
| `fast-trade` | 料金体系 | AGPL-3.0 の無償配布。PyPI の project_urls は Homepage と Repository の 2 つだけで、料金ページに当たるものが無い。**AGPL は、改変して網越しに使わせる場合に原文の公開を求める**ので、無償でも条件が軽いわけではない | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(project_urls)/ https://raw.githubusercontent.com/jrmeier/fast-trade/master/LICENSE 取得日 2026-09-22 |
| `fast-trade` | 無料枠の上限 | 本体側に上限の記述なし。archive の機能で取引所からデータを取る段では各取引所の API の制限が掛かるが、その条件は本調査では取っていない | 推定 | AGPL の配布と、導入・最小実行のどちらでも鍵・登録を求められなかったことからの外挿(docs/DATA/probes/20260922_tools_1_run5.log:55 と :66) |
| `fast-trade` | 課金開始条件 | 本体には無い。依存の fastmcp を使って LLM から呼ぶ段では、呼ぶ側のモデルの鍵と課金が要る(この調査では打っていない) | 推定 | requires_dist に fastmcp があることからの外挿(docs/DATA/probes/20260922_tools_1_run5.log:72) |
| `fast-trade` | 隠れた依存 | 導入した pkgs の中に相場データの提供元は入らない。ただし backtest に datafile を指定して df を渡さないと、archive が取引所からデータを取りに行く経路に入る | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:55 と :60(ValueError: Exchange None not supported) |
| `fast-trade` | 登録の要否 | 不要。鍵なしで導入・合成の足の投入・最小実行まで到達 | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:66 |
| `fast-trade` | 到達経路 | PyPI の index から pip install が通る | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:55 |
| `fast-trade` | 導入可否 | 可。隔離 venv に導入 | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:55(rc=0) |
| `fast-trade` | install所要秒 | 72 | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:55(install_time_s) |
| `fast-trade` | 依存数 | 108 | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:55(pkgs)。PyPI の requires_dist は 16(うち 4 件は extra == "dev") |
| `fast-trade` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:55(pip_check) |
| `fast-trade` | 最小実行の可否 | 可。ただし `chart_period` を外す必要がある(付けると TypeError で必ず止まる) | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:60 と :66 |
| `fast-trade` | 最小実行の中身 | 合成の 1 分足 300 本(乱数の種 7)を DataFrame で直接渡し、sma_short(5)と sma_long(20)を作って「終値 > sma_long で建て、終値 < sma_short で外す」を回した。手数料 comission=0.05。結果は取引 62 件・equity_final 951.71・total_fees 15.228。**成行と指値の往復は書けない**(注文の種別が無く、足の終値で建てて外すだけ) | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:66 から :69 |
| `fast-trade` | 実行所要秒 | 0.05 | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:67(TIME_S) |
| `fast-trade` | wheel展開 | fast_trade-2.1.0-py3-none-any.whl を pip download --no-deps で取り、41 ファイルを列挙 | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:71(FILES) |
| `fast-trade` | setup.py導入時実行 | wheel に setup.py は 0 件 | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:71(setup_py) |
| `fast-trade` | 同梱バイナリ | 0 件(.so / .pyd / .dll / .dylib / .exe のいずれも無い) | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:71(binaries) |
| `fast-trade` | 外部送信 | 導入先の .py に現れる外部ホストは api.binance. / api.exchange.coinbase.com / api.fxmacrodata.com / api.hyperliquid.xyz と、説明文の中の文書の URL。api.fxmacrodata.com は FXMacroDataClient の送信先で、当方の道具立てに対応物が無い。ただし走らせた状態での通信の観測はしていない | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:58 |
| `fast-trade` | 自動発注機能 | 配布物に取引所への発注の経路は見当たらない(archive は足の取得のみ)。ただし mcp_server.py を同梱しており、LLM のエージェントから backtest を呼ばせる口はある | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:59 と :72 |
| `fast-trade` | 宣伝詐欺の兆候 | 兆候なし。配布は PyPI と GitHub のみ。project_urls は 2 つとも同じ GitHub のリポジトリ | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(project_urls) |
| `fast-trade` | 当方データ投入 | 日付を index にした open/high/low/close/volume の DataFrame をそのまま渡せた。当方の csv.gz の約定・清算をそのまま入れる経路は試していない | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:66 と :69(DF_ROWS) |
| `fast-trade` | 時刻の扱い | 最小実行では tz なしの DatetimeIndex をそのまま受けた。UTC の語が現れるのは archive の 5 ファイル(binance_api.py / cli.py / coinbase_api.py / update_archive.py / update_kline.py)だけで、backtest の中核にはない | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:66 と、導入先の *.py の走査 |
| `fast-trade` | 再現性 | 同じ合成データ・同じ設定で 2 回打ち、2 回とも同じ TypeError と同じ経路になった。乱数の種は当方の合成データ側で置いたもので、道具側に種の指定は見ていない | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:64 |
| `fast-trade` | 規模の見積 | 301 行の足を 0.05 秒で回した。456 日分の 1 分足(約 65 万行)なら、行数に比例すると置いて 100 秒あたりの規模になる。ティック単位は試していない | 推定 | docs/DATA/probes/20260922_tools_1_run5.log:67 と :69 からの外挿(行数に線形と仮定) |
| `fast-trade` | 4軸1_道具 | 入れられる。pip で入り、自前の DataFrame を渡して回せる。ただし指値が書けないので、当方の指値の埋まり方の研究には使えない | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:57 と :66 |
| `fast-trade` | 4軸2_情報 | archive が binanceus / binancecom / coinbase の足を取る経路を持つ。FXMacroDataClient は api.fxmacrodata.com からマクロの系列を取る。どちらも当方の道具立てに対応物が無い | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:58 と :59 |
| `fast-trade` | 4軸3_視点 | backtest を dict で書く(コードではなく設定で戦略を書く)形と、pygad による遺伝的算法の最適化、hmmlearn による隠れマルコフの状態、fastmcp による LLM からの呼び出し口。当方の道具立てにはどれも対応物が無い | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:72 |
| `fast-trade` | 4軸4_向上 | summary が返す欄(market_adjusted_return / perc_missing / position_metrics など)は当方の metrics に無いものを含む。perc_missing は欠測の割合を毎回出すので、当方のデータ品質の確認に対応する視点を持つ | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:68 |
| `fast-trade` | 配布元の一致 | PyPI の project_urls の Homepage と Repository がどちらも github.com/jrmeier/fast-trade。GitHub 側も同じ | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(project_urls)/ https://github.com/jrmeier/fast-trade 取得日 2026-09-22 |
| `fast-trade` | 難読化 | 見当たらない。配布物は .py のみで、同梱バイナリ 0 件 | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:71 |
| `fast-trade` | 外部URL取得 | 導入の段では起きない(setup.py が 0 件)。実行の段では datafile を指定して df を渡さないと archive が取引所へ行く | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:71 と :60 |
| `fast-trade` | 依存の一覧 | pandas>=2.3.3 / matplotlib>=3.10.8 / requests>=2.32.5 / numpy>=2.2.6 / pygad>=3.5.0 / hmmlearn>=0.3.3 / plotly>=6.5.2 / pyarrow>=23.0.0 / pyyaml>=6.0.3 / rich>=14.3.2 / typer>=0.23.0 / fastmcp<3,>=2.14.5(ほかに dev の extra が build / coverage / flake8 / pytest) | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:72(requires_dist) |
| `fast-trade` | 保守者名の一貫性 | PyPI 側は info.author も info.maintainer も None で名前が無い。GitHub 側の所有者は jrmeier。**PyPI からは照合できない** | 一次資料 | https://pypi.org/pypi/fast-trade/json 取得日 2026-09-22(info.author / info.maintainer)/ https://github.com/jrmeier/fast-trade 取得日 2026-09-22 |

#### 取り直しの結果(4 回目のリードの検収が渡した 4 件)

**§4.0 の表とは別の表にした。**理由は、これらが 3 回目・4 回目に深掘りした道具の「未確認」で残った項目を、
この回に別の経路で埋めたものだからである。**同じ道具の同じ項目に、前の節では「未確認」、この節では値が入る。**
どう書くべきかは委任文に無いので、黙って決めずにここに書く(リードの判断を仰ぐ)。

| 道具 | 項目 | 前の節の値 | この回の値 | 印 | 根拠 |
|---|---|---|---|---|---|
| `Basana` | コミット数(取り直し) | 未確認 | 590 | 一次資料 | https://github.com/gbeced/basana 取得日 2026-09-22(見出しの Commits)/ docs/DATA/probes/20260922_tools_1_run5.log:4 |
| `Backtrader` | コミット数(取り直し) | 未確認 | 2404 | 一次資料 | https://github.com/mementum/backtrader 取得日 2026-09-22(見出しの Commits。表示は 2,404 Commits)/ docs/DATA/probes/20260922_tools_1_run5.log:5 |
| `PyBroker` | コミット数(取り直し) | 未確認 | 1259 | 一次資料 | https://github.com/edtechre/pybroker 取得日 2026-09-22(見出しの Commits。表示は 1,259 Commits)/ docs/DATA/probes/20260922_tools_1_run5.log:6 |
| `bt` | コミット数(取り直し) | 未確認 | 782 | 一次資料 | https://github.com/pmorissette/bt 取得日 2026-09-22(見出しの Commits)/ docs/DATA/probes/20260922_tools_1_run5.log:7 |
| `zipline-reloaded` | コミット数(取り直し) | 未確認 | 6694 | 一次資料 | https://github.com/stefan-jansen/zipline-reloaded 取得日 2026-09-22(見出しの Commits。表示は 6,694 Commits)/ docs/DATA/probes/20260922_tools_1_run5.log:2 |
| `zipline-reloaded` | 星(取り直し) | 未確認 | 1941 | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:26(ungh.cc の stars)。GitHub の HTML の表示は丸めた 1.9k |
| `PyBroker` | 週DL数(取り直し) | 未確認(4 回とも 429) | last_week=885、last_month=4152、last_day=176 | 一次資料 | https://pypistats.org/packages/lib-pybroker 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run5.log:25 |
| `Jesse` | 料金体系(取り直し) | 未確認 | **取れなかった。**金額はこの環境のどの経路でも出ない。取れたのは実弾プラグインの条件の逐語「you need to register on our website to generate your license key」「The package is pre-built and the access is limited to those with an active license」まで | 未確認 | 試したこと: curl https://jesse.trade/pricing を UA 2 種類(ブラウザ風 / trade-research/1.0)で HTTP 403(log:31 と :32)/ WebFetch https://jesse.trade/help/faq/... で HTTP 403(log:29)/ curl https://web.archive.org/web/2026/https://jesse.trade/pricing で接続切断(log:28)/ archive.org の wayback available が archived_snapshots 空(log:33)。取れた一次資料は https://docs.jesse.trade/docs/livetrade.html 取得日 2026-09-22(log:30) |

**`Jesse` の金額の第 2 経路(オーナー PC でそのまま打てるコマンド)**:

```
curl -sS -o jesse_pricing.html -w '%{http_code}\n' https://jesse.trade/pricing
curl -sS -o jesse_faq.html -w '%{http_code}\n' 'https://jesse.trade/help/faq/why-do-i-have-to-pay-for-live-i-thought-its-open-source'
```

`WebSearch` の結果一覧には `https://jesse.trade/blog/news/black-friday-offer-lifetime-access-to-jesses-live-trade-plugin-for-only-599`
という見出しの項目が出るが、**その頁そのものは開けていない**ので、金額は本調査の値として書かない。

#### 浅い候補について、この回に新しく測ったもの(深掘りではない)

§4.0 の表には入れない(委任文 §4.0「浅い候補(深掘りしていない)は表に入れず」)。

| 道具 | 測ったこと | 値 | 印 | 根拠 |
|---|---|---|---|---|
| PySystemtrade | clone の大きさ | 878 MB(うち data が 737 MB、.git が 110 MB、examples が 26 MB)。リードの条件の 200 MB を超えたので止めて消した | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:35 と :44 と :45 |
| Ziplime | 導入の可否 | **既定の `python3`(3.11.15)では**不可。pip が候補を 1 つも見つけない(No matching distribution found)。requires_python は <4.0,>=3.12。**この環境には python3.12 / python3.13 も在るので「環境として不可」ではない(リードの訂正・実測)** | 実測 | docs/DATA/probes/20260922_tools_1_run5.log:47 と :52 |
| Ziplime | PyPI の情報 | version 1.19.16 / 最新版の upload_time 2026-06-18T09:21:46 / info.license = None / info.license_expression = None / info.author = "Ziplime" / info.maintainer = None / project_urls = None / vulnerabilities 長さ 0 / requires_dist 30 件 | 一次資料 | https://pypi.org/pypi/ziplime/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run5.log:47 |
| OctoBot | PyPI の情報 | version 2.1.1 / 最新版の upload_time 2026-03-29T15:25:05 / info.license = "GPL-3.0" / info.author = "Drakkar-Software" / info.maintainer = None / requires_python >=3.12(**既定の `python3` では**導入できない)/ requires_dist 77 件 | 一次資料 | https://pypi.org/pypi/OctoBot/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run5.log:50 |
| pybotters | PyPI の情報 | version 1.11.2 / 最新版の upload_time 2026-04-17T07:19:41 / info.license = None / info.license_expression = "MIT" / info.author = None / info.maintainer = None / requires_python >=3.10 / requires_dist 1 件 / 文書は日本語(project_urls の Documentation が pybotters.readthedocs.io/ja/stable) | 一次資料 | https://pypi.org/pypi/pybotters/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run5.log:49 |
| mlflow | PyPI の情報 | version 3.16.1 / 最新版の upload_time 2026-09-16T23:14:16 / info.license = "Copyright 2018 Databricks, Inc.  All rights reserved." (SPDX の識別子ではない)/ info.author = None / info.maintainer = None / requires_python >=3.10 / requires_dist 59 件 | 一次資料 | https://pypi.org/pypi/mlflow/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run5.log:51 |

**PySystemtrade の第 2 経路(オーナー PC で、大きさを避けて中身だけ見るコマンド)**:

```
git clone --depth 1 --filter=blob:none --sparse https://github.com/robcarver17/pysystemtrade
cd pysystemtrade && git sparse-checkout set systems sysquant sysobjects syscore
du -sh . && pip install -e . --dry-run
```

### 予算

| 項目 | 値 |
|---|---|
| 上限 | 1 回 5 万トークン・20 分 |
| 実績 | 上限に達したため中断した。深掘りは `fast-trade` の 1 件。取り直しは 4 件のうち 3 件が埋まり、`Jesse` の金額だけが取れなかった |
| 未完了 | 候補の一覧の 7・8・9・13・14・15・16 番はこの回で着手していない。3・6・11・12・17 番は浅いまま。区分 1 は**未完了**(委任文 §2 の条件 = 残りの候補が空で、新しい検索計画が新しい候補を 1 件も出さない、を満たしていない) |

### 受け入れ検査で残した行(自分で閉じなかったもの)

委任文 §12「**誤検出だと判断しても、自分で閉じてはならない。**直さずに残し、その行と理由を報告に 1 件ずつ書いて**リードに渡す**」に従い、K5 の 2 件を残した。

1. **`fast-trade` の `規模の見積` の行。**この 1 つのセルの中に、実測した実行の秒と、そこから外挿した秒の 2 つの数が入っている。
   検査は「同じ道具の同じ項目に別の値」として拾うが、**外挿の行は「測った値」と「外挿した値」の両方を書かないと
   何から外挿したかが読めない**(委任文 §4「小さい実行の実測から**推定**と印を付けて外挿」)。
   4 回目にリードが直した「単位ではなく項目で束ねる」の続きで、**1 つのセルの中の 2 つの数をどう扱うか**が決まっていない。誤検出だと自分で判断して閉じない。
2. **同じ行が `tools_` という道具名でももう 1 件当たっている。**`tools_` は候補の一覧にも §4.0 の表の 1 列目にも無い。
   根拠の欄に書いた生ログの道筋 `docs/DATA/probes/20260922_tools_1_run5.log` の一部を、検査が道具名として拾っているように見える。
   **検査側の欠陥の疑いがあるが、判定するのはリードである。**

## 受け入れ検査の出力

リードが受領後に打ち直した出力(生ログ 3 本を渡した)。調査班が残した 2 件はどちらも検査の欠陥で、
道具名の取り方と同一行の扱いを直した。判定は `docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run5.md`。

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
---- 検査対象の合計 0 件(K12 を除く。貼り付けはこの数で照合する)
---- 合計 1 件
```


## 区分1 — 6 回目の実行(2026-09-22)

委任文: `docs/DATA/delegations/20260922_tools_survey_prompt.md@ce0012c95154`。生ログ: `docs/DATA/probes/20260922_tools_1_run6.log`。
5 回目のリードの検収(`docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run5.md`)の §8 で訂正された誤り
(「この環境では導入できない」を既定の `python3` だけを見て断定した)を受け、この回は**まず `/usr/bin/python3.12` の隔離 venv で
`Ziplime` を導入し直した**。導入は通り、最小実行(指値と成行の 1 往復)まで到達した。
`PySystemtrade` も、全部の clone ではなく `--filter=blob:none --sparse` で取り直した。

### 当方の道具立て(`python3 scripts/tools_inventory.py` の出力全文。§8)

```
# 当方の道具立て(git ls-files から生成。2026-09-22T08:27:54Z、HEAD f1d99da。コマンド: python3 scripts/tools_inventory.py)

## src/bot(package: ファイル数 / ファイル名)
- src/bot: 7 / atomic_file.py constants.py logging_setup.py main.py products.py radar.py settings.py
- src/bot/backtest: 3 / engine.py metrics.py walk_forward.py
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
- check_*: 8 / check_api.py check_data_ledger.py check_k1_binance.py check_k1_bitflyer_data.py check_kabu_api.py check_liquidation_feeds.py check_liquidation_history_depth.py check_scan_report.py
- build_*: 7 / build_basis.py build_bitflyer_lightchart_csv.py build_burst_library.py build_flow.py build_fx_event_library.py build_fx_event_library_2005_2014.py build_storm_library.py
- record_*: 5 / record_funding_basis.py record_liquidations.py record_oi.py record_realtime.py record_venues.py
- jev/: 3 / client.py redact.py schemas.py
- verify_*: 3 / verify_gates.py verify_liq_instrument.py verify_snapshots.py
- (単発): 2 / _research_audit_gate.py dashboard.py
- judge_*: 2 / judge_board_round.py judge_gates.py
- k1_*: 2 / k1_binance_data_quality.py k1_source.py
- paper_*: 2 / paper_on1.py paper_onr.py
- repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.py
- constants_*: 1 / constants_inventory.py
- data_*: 1 / data_quality.py
- explore_*: 1 / explore_o3c_oi_axis.py
- extract_*: 1 / extract_tape.py
- intake_*: 1 / intake_ledger.py
- liquidation_*: 1 / liquidation_report.py
- mirror_*: 1 / mirror_bitmex_archive.py
- normalize_*: 1 / normalize_bitflyer_executions.py
- phase2_*: 1 / phase2_seal.py
- preflight_*: 1 / preflight_prereg.py
- probe_*: 1 / probe_api_latency.py
- replay_*: 1 / replay_scalp_storm.py
- retention_*: 1 / retention_snapshot.py
- tools_*: 1 / tools_inventory.py
- tp_*: 1 / tp_operating_curve.py
- trace_*: 1 / trace_metrics.py
- validate_*: 1 / validate_composite.py
- x_*: 1 / x_fetch.py
- (.py 以外の scripts: 3 = scripts/fetch_all.sh scripts/install_git_hooks.sh scripts/regen_hook_manifest.sh)

## config: 32
  config/composite.yaml config/config.yaml config/constants.yaml config/etf_measure.yaml config/jev_delegation_tiers.yaml config/jev_design_examples/o3c_covariates.yaml config/jev_design_examples/o3c_observables.yaml config/jev_design_examples/signal2_covariates.yaml config/jev_design_examples/signal2_observables.yaml config/jev_design_examples/signal3_covariates.yaml config/jev_design_examples/signal3_observables.yaml config/jev_design_examples/signal4_covariates.yaml config/jev_design_examples/signal4_observables.yaml config/jev_design_examples/signal5_covariates.yaml config/jev_design_examples/signal5_observables.yaml config/jev_design_examples/signal6_covariates.yaml config/jev_design_examples/signal6_observables.yaml config/jev_design_examples/signal7_observables.yaml config/jev_design_examples/signal8_covariates.yaml config/jev_design_examples/signal8_observables.yaml config/jev_design_examples/signal8_observables_independent.yaml config/jev_design_examples/signal_covariates.yaml config/jev_design_examples/signal_observables.yaml config/jev_routes.yaml config/o3c_jev_state_bands.yaml config/o3c_signal_logit_chain.yaml config/o3c_signal_logit_first.yaml config/o3c_signal_logit_value_chain.yaml config/o3c_signal_logit_value_first.yaml config/on1_live.yaml config/products.yaml config/risk_limits.yaml

## deploy: 19
  deploy/bitflyer-bot.service deploy/bitflyer-fetch.service deploy/bitflyer-fetch.timer deploy/check_liq_recorder.bat deploy/etf_measure_entry.bat deploy/etf_measure_exit.bat deploy/fetch_all.bat deploy/mirror_bitmex.bat deploy/nightly_restart.bat deploy/on1_entry.bat deploy/on1_exit.bat deploy/probe_latency.bat deploy/reset_kill.bat deploy/restart_all.bat deploy/run_paper.bat deploy/setup.sh deploy/share_logs.bat deploy/start_all.bat deploy/stop_all.bat

## tests(ファイル): 139
  tests/conftest.py tests/fixtures/jev_ops/decisions.json tests/fixtures/jev_ops/notifications.jsonl tests/fixtures/jev_ops/status_page.html tests/test_app_fx_integration.py tests/test_audit_gates_wired.py tests/test_backtest.py tests/test_bitmex_mirror.py tests/test_board.py tests/test_board_round.py tests/test_board_walk.py tests/test_bot_research_overnight.py tests/test_build_flow.py tests/test_check_data_ledger.py tests/test_client.py tests/test_clock_burst.py tests/test_composite.py tests/test_constants.py tests/test_constants_inventory.py tests/test_dashboard.py tests/test_data_quality.py tests/test_data_quality_incremental.py tests/test_deploy.py tests/test_engine_maker_exit.py tests/test_etf_measure.py tests/test_extract_tape.py tests/test_fetch_backfill_scripts.py tests/test_fetch_binance_daily.py tests/test_fetch_binance_vision.py tests/test_fetch_history_candles.py tests/test_gz_members.py tests/test_intake_ledger.py tests/test_intent_map_rule.py tests/test_jev_audit_eval.py tests/test_jev_audit_loop.py tests/test_jev_check.py tests/test_jev_client.py tests/test_jev_delegate.py tests/test_jev_design.py tests/test_jev_ideas.py tests/test_jev_ops.py tests/test_jev_owner_log.py tests/test_jev_redact.py tests/test_jev_reply.py tests/test_jev_report_intake.py tests/test_jev_schemas.py tests/test_jev_scripts.py tests/test_jev_survey.py tests/test_jev_trace_export.py tests/test_judge_gates.py tests/test_k1_bitflyer_source.py tests/test_k1_bybit_source.py tests/test_k1_delay_decomp.py tests/test_k1_delay_entry.py tests/test_k1_flip_body.py tests/test_k1_lookahead.py tests/test_k1_no_invalidation.py tests/test_k1_round5.py tests/test_k1_seal_guard.py tests/test_k1_xvenue.py tests/test_liq_bands.py tests/test_liq_response.py tests/test_liq_response_dedup.py tests/test_liquidation_reader.py tests/test_maker_execution.py tests/test_market_data.py tests/test_market_view.py tests/test_max_hold.py tests/test_modes.py tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_ext.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_rows4.py tests/test_o3c_signal_calib.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore2.py tests/test_o3c_signal_explore3.py tests/test_o3c_signal_explore4.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_policy.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_on1_forward.py tests/test_on1_live.py tests/test_onr.py tests/test_onr_forward.py tests/test_orders.py tests/test_paper_state.py tests/test_phase2_p2_01.py tests/test_phase2_p2_01_final.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_phase2_p2_03.py tests/test_phase2_p2_03_final.py tests/test_phase2_p2_03_iter2.py tests/test_phase2_p2_04.py tests/test_phase2_seal.py tests/test_portfolio_and_strategy.py tests/test_position_ladder.py tests/test_preflight_prereg.py tests/test_probe_api_latency.py tests/test_qa_make_known_answer.py tests/test_qa_make_known_answer_maker.py tests/test_qa_make_known_answer_maker3.py tests/test_qa_make_known_answer_steer.py tests/test_qa_maker_fill_ref.py tests/test_qa_pipeline_known_answer.py tests/test_qa_score_audit.py tests/test_radar.py tests/test_realtime_recorder.py tests/test_record_funding_basis.py tests/test_record_liquidations.py tests/test_record_liquidations_writer.py tests/test_record_venues.py tests/test_repair_gz_listing.py tests/test_research_protocol_rules.py tests/test_resilience.py tests/test_retention_snapshot.py tests/test_risk.py tests/test_scalp_logic.py tests/test_sealed_load_diagnostic.py tests/test_sealed_ts_us.py tests/test_short_margin.py tests/test_tp_sl.py tests/test_verify_snapshots.py tests/test_wick_stop.py tests/test_x_fetch.py tests/test_xborder.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_fx.py tests/test_xborder_p2_known_answer.py tests/test_xborder_p2_state.py

## .claude/hooks: 8
  .claude/hooks/_verify_manifest.sh .claude/hooks/delegation_audit_gate.sh .claude/hooks/deny_protected_paths.sh .claude/hooks/jev_notice.sh .claude/hooks/owner_options_gate.sh .claude/hooks/owner_turn_digest.sh .claude/hooks/session_start_digest.sh .claude/hooks/trace_snapshot.sh

## .claude/agents: 3
  .claude/agents/owner-auditor-candidate.md .claude/agents/owner-auditor.md .claude/agents/owner-model-auditor.md

## .claude/skills: 9
  .claude/skills/delegated-study/SKILL.md .claude/skills/owner-audit/SKILL.md .claude/skills/owner-options/SKILL.md .claude/skills/owner-procedure/SKILL.md .claude/skills/research-protocol/SKILL.md .claude/skills/research-squad/SKILL.md .claude/skills/typesafe-ai/LICENSE .claude/skills/typesafe-ai/SKILL.md .claude/skills/x-research/SKILL.md

## githooks: 1
  githooks/pre-push

## docs(.md): 297
  docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11_control_review.md docs/AUDITOR/EVAL_2026-09-11b.md docs/AUDITOR/IMPROVEMENT.md docs/AUDITOR/JEV/LABELS_NOTES_2026-09-19.md docs/AUDITOR/JEV/PREREG_2026-09-19.md docs/AUDITOR/KNOWN_ANSWERS.md docs/AUDITOR/KNOWN_ANSWERS_ADDENDUM.md docs/AUDITOR/OWNER_MODEL_SOURCE.md docs/AUDITOR/PRINCIPLES.md docs/AUDITOR/PROCESS_METRICS.md docs/AUDITOR/PROPOSED_CHANGES_2026-09-11.md docs/AUDITOR/READDO/audit_stop.md docs/AUDITOR/READDO/before_unseal.md docs/AUDITOR/READDO/owner_objection.md docs/AUDITOR/READDO/push_blocked.md docs/AUDITOR/READDO/repeat_defect.md docs/AUDITOR/TREND.md docs/AUDITOR/VERDICTS/2026-09-11_k1_closure_entries.md docs/AUDITOR/VERDICTS/2026-09-11_proposed_changes_and_eval_b.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_execution.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_plan.md docs/AUDITOR/VERDICTS/2026-09-12_o3c_reframe_reading.md docs/AUDITOR/VERDICTS/2026-09-12_p14_liquidation_fix.md docs/AUDITOR/VERDICTS/2026-09-12_p4n_nightly_restart.md docs/AUDITOR/VERDICTS/2026-09-12_rules_reduction.md docs/AUDITOR/VERDICTS/2026-09-16_policy4_report.md docs/AUDITOR/VERDICTS/2026-09-17_anchor_report.md docs/AUDITOR/VERDICTS/2026-09-17_closure.md docs/AUDITOR/VERDICTS/2026-09-17_data_collection.md docs/AUDITOR/VERDICTS/2026-09-17_missing.md docs/AUDITOR/VERDICTS/2026-09-17_oi_distance.md docs/AUDITOR/VERDICTS/2026-09-17_price_level.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_ext.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_full.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_rows4.md docs/AUDITOR/VERDICTS/2026-09-18_oi_distance_split.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_design.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r10.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r2.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r3.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r4.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r5.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r6.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r7.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r8.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r9.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_run12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r11.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_r2_prereg.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r2.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r3.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_result.md docs/AUDITOR/VERDICTS/2026-09-19_signal_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_report.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_materials_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_result.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_design.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_result.md docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md docs/AUDITOR/VERDICTS/2026-09-21_tools_survey_prompt.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run2.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run3.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run4.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run5.md docs/AUDITOR/VERDICTS/2026-09-22_tools_survey_prompt_v12.md docs/AUDITOR/VERDICTS/README.md docs/AUDITOR/answers/KA-01.md docs/AUDITOR/answers/KA-02.md docs/AUDITOR/answers/KA-04.md docs/AUDITOR/answers/KA-05.md docs/AUDITOR/answers/KA-06.md docs/AUDITOR/answers/KA-07.md docs/AUDITOR/answers/KA-08.md docs/AUDITOR/answers/KA-09.md docs/AUDITOR/answers/KA-10.md docs/AUDITOR/answers/KA-16.md docs/AUDITOR/answers/KA-17.md docs/AUDITOR/answers/KA-18.md docs/AUDITOR/answers/KA-19.md docs/AUDITOR/answers/KA-20.md docs/AUDITOR/answers/KA-21.md docs/AUDITOR/answers/KA-22.md docs/AUDITOR/answers/KA-23.md docs/AUDITOR/answers/KA-24.md docs/AUDITOR/answers/KA-25.md docs/AUDITOR/answers/KA-26.md docs/AUDITOR/answers/KA-27.md docs/AUDITOR/answers/KA-28.md docs/AUDITOR/before/HYGIENE_2026-09-11.md docs/AUDITOR/before/KA-01.md docs/AUDITOR/before/KA-02.md docs/AUDITOR/before/KA-04.md docs/AUDITOR/before/KA-05.md docs/AUDITOR/before/KA-06.md docs/AUDITOR/before/KA-07.md docs/AUDITOR/before/KA-08.md docs/AUDITOR/before/KA-09.md docs/AUDITOR/before/KA-10.md docs/AUDITOR/before/KA-16.md docs/AUDITOR/before/KA-17.md docs/AUDITOR/before/KA-18.md docs/AUDITOR/before/KA-19.md docs/AUDITOR/before/KA-20.md docs/AUDITOR/before/KA-21.md docs/AUDITOR/before/KA-22.md docs/AUDITOR/before/KA-23.md docs/AUDITOR/before/KA-24.md docs/AUDITOR/before/KA-25.md docs/AUDITOR/before/KA-26.md docs/AUDITOR/before/KA-27.md docs/AUDITOR/before/KA-28.md docs/DATA.md docs/DATA/SCAN_2026-09-16.md docs/DATA/SCAN_2026-09-21_tools.md docs/DATA/delegations/20260919_o3c_signal_explore2_prompt.md docs/DATA/delegations/20260920_o3c_cascade_read_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_jev_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore3_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore4_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore5_prompt.md docs/DATA/delegations/20260920_o3c_signal_jev_state_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials2_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_stage2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_tp_prompt.md docs/DATA/delegations/20260921_tools_survey_prompt.md docs/DATA/delegations/20260922_tools_survey_prompt.md docs/DATA/probes/20260913_liquidation_integrity.md docs/DATA/probes/20260919_reaction_prereg_outputs.md docs/DATA/probes/20260920_o3c_cascade_read.md docs/DATA/probes/20260920_o3c_materials_read.md docs/DATA/surveys/BINANCE_CM_MMR_2026-09-17.md docs/DATA/surveys/BITFLYER_HISTORY_SOURCES.md docs/DATA/surveys/ETF_ALTERNATIVES.md docs/DATA/surveys/G2_DATA_INVENTORY.md docs/DATA/surveys/LIQUIDATION_FEED_REACHABILITY.md docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_ACCEPTANCE_2026-09-13.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_A_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_B_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_C_HYPERLIQUID_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_D_VENUE_UNIVERSE_2026-09-12.md docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md docs/DATA_CONSUMPTION_LOG.md docs/DELEGATION.md docs/DISCUSSIONS/2026-09-04_postmortem_tp_precursor.md docs/DISCUSSIONS/2026-09-06_data_dependency.md docs/DISCUSSIONS/2026-09-08_external_ecosystem.md docs/DISCUSSIONS/2026-09-08_matilda_intent_vs_test.md docs/DISCUSSIONS/2026-09-09_prereg_deep_dive.md docs/DISCUSSIONS/2026-09-09_the_day_nothing_shipped.md docs/DISCUSSIONS/2026-09-12_docs_reorg_plan.md docs/DISCUSSIONS/2026-09-12_generation_vs_filtering.md docs/DISCUSSIONS/2026-09-12_rules_inventory.md docs/DISCUSSIONS/2026-09-12_rules_reduction_proposal.md docs/DISCUSSIONS/2026-09-13_root_cause.md docs/DISCUSSIONS/2026-09-13_worst_day.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/PLAN.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/README.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/STAGE0_hook_probe.md docs/DISCUSSIONS/2026-09-16_scope_claim_gate_proposal.md docs/DISCUSSIONS/2026-09-18_jev_trade_integration_decision_for_fable_v2.md docs/DISCUSSIONS/2026-09-19_jev_adoption_review.md docs/DISCUSSIONS/2026-09-19_jev_common_module_review.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/A_judgment_points.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/B_failures.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/C_vendor_sources.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/D_study_notes.md docs/INCIDENTS.md docs/INDEX.md docs/JEV.md docs/NEGATIVE_FACTS.md docs/OPERATIONS.md docs/OPERATIONS_JPX.md docs/OWNER_LOG.md docs/OWNER_PROCEDURES.md docs/OWNER_STATUS.md docs/PHASE2/EXEC/EXEC_FLOOR_PREREG.md docs/PHASE2/EXEC/RESULT.md docs/PHASE2/INSTRUMENT_VERIFY/AUDIT_LEDGER_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-16_policy4.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-17_anchor.md docs/PHASE2/K1/AUDIT_TRIAGE.md docs/PHASE2/K1/BINANCE_PLAN.md docs/PHASE2/K1/DEEPDIVE_PLAN.md docs/PHASE2/K1/FRESH_BITFLYER_PREREG.md docs/PHASE2/K1/H1_PREREG.md docs/PHASE2/K1/H2_PREREG.md docs/PHASE2/K1/H3_DECOMP_PREREG.md docs/PHASE2/K1/H3_PREREG.md docs/PHASE2/K1/HANDOFF.md docs/PHASE2/K1/JUDGEMENT_PREREG.md docs/PHASE2/K1/PREFLIGHT.md docs/PHASE2/K1/PREREG.md docs/PHASE2/K1/RESULT.md docs/PHASE2/K1/ROUND5_PREREG.md docs/PHASE2/K1/XVENUE_PREREG.md docs/PHASE2/K1/binance/CHECKS.md docs/PHASE2/O3C/BRANCH_MAP.md docs/PHASE2/O3C/DATA_AVAILABILITY.md docs/PHASE2/O3C/DATA_COLLECTION_2026-09-17.md docs/PHASE2/O3C/INTENT_MAP.md docs/PHASE2/O3C/MISSING_2026-09-17.md docs/PHASE2/O3C/OWNER_INTENT_2026-09-12.md docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/FULL_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_SPLIT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_DRAFT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_R2_PREREG_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RESULT_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RUN12_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/ROWS4_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/SAMPLE_2026-09-17.md docs/PHASE2/O3C/REFRAME/DIFF_2026-09-12.md docs/PHASE2/O3C/REFRAME/LEAD_READING_2026-09-12.md docs/PHASE2/O3C/REFRAME/data_engineer.md docs/PHASE2/O3C/REFRAME/discretionary_trader.md docs/PHASE2/O3C/REFRAME/liquidation_engine.md docs/PHASE2/O3C/REFRAME/market_maker.md docs/PHASE2/O3C/REFRAME/microstructure.md docs/PHASE2/O3C/SIGNAL/CONTINUE_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/CONTINUE_JEV_RUN_NOTE_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE2_DELEGATE_REPORT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/EXPLORE3_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE4_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE5_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/JEV_STATE_PREVIEW_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS2_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW2_2026-09-19.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW3_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW4_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW5_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW6_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW9_2026-09-21.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_RESULT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE1_REPORT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE2_REPORT_2026-09-21.md docs/PHASE2/O3C/STAGE0A_2026-09-14.md docs/PHASE2/O3C/TRIGGER_TRACE.md docs/PROJECT_GOAL.md docs/STRATEGY_IDEAS.md docs/legacy/KATSUO_INTENT_MAP.md docs/legacy/KATSUO_PARAMETER_INVENTORY.md docs/legacy/README.md

## backtest_data(ディレクトリ数)
  147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H_20260905 audit_fetch_JPX_n225f_months_20260906 audit_fetch_JPX_tick_20260906 audit_fetch_P2-08_docs_20260906 audit_fetch_P2-08b_20260906 audit_fetch_bitflyer_history_20260906 audit_fetch_etf_alternatives_20260906 audit_fetch_etf_units_20260906 audit_fetch_micro_fee_20260906 auto_bitflyer_executions_20260905 auto_bitflyer_executions_20260921 auto_oi_snapshots_20260905 auto_oi_snapshots_20260921 auto_okx_long_short_ratio_20260905 auto_okx_open_interest_1h_20260905 auto_okx_open_interest_1h_20260921 auto_okx_open_interest_5m_20260905 auto_okx_open_interest_5m_20260906 auto_okx_open_interest_5m_20260907 auto_okx_open_interest_5m_20260908 auto_okx_open_interest_5m_20260909 auto_okx_open_interest_5m_20260910 auto_okx_open_interest_5m_20260911 auto_okx_open_interest_5m_20260912 auto_okx_open_interest_5m_20260915 auto_okx_open_interest_5m_20260918 auto_okx_open_interest_5m_20260921 auto_venues_20260905 auto_venues_20260921 binance_BTCUSDT_1m.csv binance_BTCUSDT_1m_20170801_20231231 binance_BTCUSDT_1m_20240101_20260831 binance_BTCUSDT_1m_210d_20260820.csv.gz binance_BTCUSDT_1s_20260723_20260906 binance_BTCUSDT_aggTrades_20260723_20260906 binance_BTCUSDT_aggTrades_tardis_days binance_XRPUSDT_1d.csv binance_XRPUSDT_1m.csv binance_XRPUSDT_4h.csv binance_cm_o3c_20260913 binance_cm_o3c_supp_20260917 binance_um_BTCUSDT_aggTrades_20260723_20260906 bitbank_btc_jpy_transactions_monthly_first_days bitbank_xrp_jpy_1m.csv bitflyer_executions_backfill_20260921 bitflyer_executions_us_20260723_20260906 bitflyer_lightchart_BTC_JPY_1m_20260906 bitflyer_lightchart_FX_BTC_JPY_1m_20260906 bitmex_insurance_20260912 bitmex_trade_1s_XBTUSD board_round_20260904 burst_events_20260820 bybit_BTCUSDT_1m_20260910 bybit_reachability_check_20260906 candles_BTC_JPY_20260820.csv candles_ETH_JPY_20260820.csv candles_FX_BTC_JPY_20260820.csv candles_FX_BTC_JPY_30d_20260820.csv candles_FX_BTC_JPY_31d_20260823.csv.gz candles_XRP_JPY_20260820.csv coinalyze_liquidations_20260921 daily_btcusd_bitstamp_20260828.csv.gz daily_btcusd_coinbase_20260828.csv.gz daily_btcusd_yahoo_20260828.csv.gz daily_ethusd_bitstamp_20260828.csv.gz daily_ethusd_coinbase_20260828.csv.gz daily_ethusd_yahoo_20260828.csv.gz executions_FX_BTC_JPY_31d_20260823.csv.gz executions_FX_BTC_JPY_31d_20260908 flow_FX_BTC_JPY_20260820.csv fred_DEXJPUS.csv fred_DFF.csv fred_DGS2.csv fred_IR3TIB01JPM156N.csv fred_IRSTCI01JPM156N.csv fx_btc_jpy_1m_continuous_20260906 fx_event_ticks_2005_2014 fx_event_ticks_2015_2026 fx_fundamentals_20260822 fx_usdjpy_1m_20170801_20221231 fx_usdjpy_1m_20260822.csv.gz gate_liquidations_20260908 gmo_swap_usdjpy.csv jp_factors_20260905 jpx_daily_report_json_20260908 jpx_etf_daily_20260905 jpx_etf_daily_20260906_topix_alt liquidations_repaired_20260912 liquidations_repaired_20260917 mini_topixf_225labo_20260907 n225f_225labo_20260828 nk225_events_20260904 o3c_oi_distance_20260917 o3c_oi_distance_split_20260918 o3c_price_level_band_20260917 o3c_price_level_bundle_first_20260917 o3c_price_level_full_20260917 o3c_price_level_full_20260917_b005 o3c_price_level_full_20260917_b025 o3c_price_level_full_20260917_w72 o3c_price_level_full_20260917_w8 o3c_price_level_rows4_20260917 o3c_price_level_sample_20260917 o3c_price_level_sample_20260917_limitprice o3c_reaction_20260918_anchor o3c_reaction_20260918_anchor_trades o3c_reaction_20260918_anchor_trades_sample o3c_reaction_20260918_anchor_v1_rawcols o3c_reaction_20260918_full o3c_reaction_20260918_judge o3c_reaction_20260918_sample o3c_reaction_20260918_scale12_judgmentdays o3c_signal_continue_20260920 o3c_signal_explore2_20260919 o3c_signal_explore3_20260920 o3c_signal_explore4_20260920 o3c_signal_explore5_20260920 o3c_signal_explore_20260919 o3c_signal_materials_20260920 o3c_signal_policy_20260920 o3c_signal_value_20260921 okx_20260905 okx_btc_lsratio_1h_20260823.csv okx_btc_lsratio_5m_20260823.csv okx_btc_oi_1h_20260823.csv okx_btc_oi_5m_20260823.csv phase2_runs phase2_sealed qa_known_answer_20260905 qa_known_answer_maker3_20260907 qa_known_answer_maker3_v2_20260905 qa_known_answer_maker3_v3_20260905 qa_known_answer_maker4_20260905 qa_known_answer_maker4_r2_20260905 qa_known_answer_maker_20260905 qa_known_answer_steer_20260905 qa_pipeline_daily_20260905 qa_pipeline_daily_20260906 qa_pipeline_taker_20260905 regime_composite_20260901 reit_onr_20260904 storm_events_20260820 topixf_225labo_20260907 venue_survey_20260827 yutai_20260904
```

### 検索計画

**この回も検索計画は打っていない。**残りの候補が空になっていないため(起動指定「**検索計画 6 本はまだ打ち直しません**」)。

| 幅 | 日本語クエリ | 英語クエリ | 実行 |
|---|---|---|---|
| 狭い | (未作成) | (未作成) | 未実行(残りの候補が空になっていないため) |
| 中間 | (未作成) | (未作成) | 未実行(同上) |
| 広い | (未作成) | (未作成) | 未実行(同上) |

### 出典

| URL / 経路 | 方法 | 生ログの行 |
|---|---|---|
| https://pypi.org/pypi/ziplime/json | curl(code=200) | 79 |
| https://raw.githubusercontent.com/Ziplime/ziplime/main/LICENSE | curl(code=404) | 84 |
| https://raw.githubusercontent.com/Ziplime/ziplime/master/LICENSE | curl(code=404) | 84 |
| https://ungh.cc/repos/Ziplime/ziplime | curl(code=404) | 85 |
| https://raw.githubusercontent.com/Limex-com/ziplime/master/LICENSE | curl(code=200) | 87 |
| https://ungh.cc/repos/Limex-com/ziplime | curl(code=200) | 88 |
| https://pypistats.org/api/packages/ziplime/recent | curl(code=429) | 89 |
| https://pypistats.org/packages/ziplime | WebFetch | 90 |
| https://github.com/Limex-com/ziplime | WebFetch | 91 |
| https://github.com/robcarver17/pysystemtrade | git clone --depth 1 --filter=blob:none --sparse | 18 |
| PyPI の index(pip download / pip install 経由) | v6z/bin/pip | 9 と 29 |

### 知見

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | **5 回目の「この環境では導入できない」は誤りで、`/usr/bin/python3.12` の隔離 venv に `Ziplime` は入った。**pip check も通り、最小実行まで到達した。既定の `python3` の版だけを見て環境の可否を断定してはならない | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:2 と :29 |
| 2 | **`PySystemtrade` は `--filter=blob:none --sparse` で取れば 3.6M で済む。**5 回目に止めた原因は同梱の相場データで、それを外せば中身の検査に必要なものは全部そろう(`LICENSE`・`pyproject.toml`・`setup.py`・中核の 5 つの package) | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:18 と :20 |
| 3 | **`Ziplime` は、この区分で初めて「指値と成行の 1 往復」を実際に通せた道具である。**`finance/execution.py` に成行・指値・逆指値・逆指値付き指値の 4 つの型があり、滑りと手数料の模型も別ファイルで差し替えられる。`bt` と `fast-trade` には注文の種別という概念が無かった | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:47 と :60 |
| 4 | **`Ziplime` の既定のデータ取り込みは鍵が要る。**`ingest` が選べる提供元は 2 つだけで、鍵なしで打つと `Missing LIMEX_API_KEY environment variable.` で止まる。`--skip-fundamental-data` を付けても止まる(鍵の検査のほうが先に走る) | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:33 と :44 |
| 5 | **鍵の要る取り込みを迂回する経路が本体の中にある。**`data/services/csv_data_source.py` の `CSVDataSource` を直接組み立てれば、鍵も登録も無しに自前の csv から模擬を回せる。CLI の `ingest` にはこの経路の入口が無い | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:47 と :60 |
| 6 | **公開されている最新版の `Ziplime` には、その迂回路に 3 つの欠陥がある。**(a) `CSVDataSource` の `frequency` に `datetime.timedelta` を渡すと polars が必ず落ちる(注釈は `timedelta` も受ける形なのに、実装は文字列しか通らない)/ (b) `auto_close_date` は dataclass 側で `None` を許すのに DB 側が NOT NULL / (c) 対照銘柄を指定しないと `validate_benchmark` が `None` を参照して落ちる。**どれも回避できたが、回避しないと動かない** | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:52 と :56 と :58 |
| 7 | **`Ziplime` の PyPI の配布物にはライセンスの本文も所在も入っていない。**METADATA は `License-File: LICENSE` と書くのに該当ファイルが wheel に無く、`license` も `project_urls` も `home_page` も空。GPL-3.0 だと分かるのは GitHub の `master` の LICENSE を直接取ったとき | 一次資料 | https://pypi.org/pypi/ziplime/json 取得日 2026-09-22 / https://raw.githubusercontent.com/Limex-com/ziplime/master/LICENSE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run6.log:12 と :14 と :87 |
| 8 | **PyPI から `Ziplime` のリポジトリへ辿る道は無い。**`project_urls` が空なので、名前から推測した `Ziplime/ziplime` は 404 だった。実際の所在 `Limex-com/ziplime` は WebSearch でしか出てこなかった。**供給網の照合(配布元の一致)が PyPI 単独ではできない道具がある** | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:83 |
| 9 | **`Ziplime` は実弾の執行口を本体に持つ。**`run` の `--exchange-type` に `lime-trader-sdk` があり、`--live-market-data-provider` も同じ。**同じ算法ファイルが模擬でも実弾でも動く形**で、当方の道具立てには「模擬と実弾で同じ戦略ファイルを共有する」対応物が無い | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:40 |
| 10 | **GitHub の `master` と PyPI の最新版で、使えるデータ源が食い違っている。**README は Yahoo Finance(鍵なし・無料)と CSV を挙げるが、導入した版の `ingest` にはその選択肢が無い。**README を読んで「鍵なしで取り込める」と判断すると外れる** | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:33 と :94 |
| 11 | **`Ziplime` の README は LLM の鍵を前提にした機能を宣伝している。**「戦略を自然言語で書かせる」部分は外部の LLM の中継業者の鍵が要る。**本体の無償配布とは別に、使う機能によって外部の課金に入る** | 一次資料 | https://github.com/Limex-com/ziplime 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run6.log:94 |
| 12 | **`PySystemtrade` の保守者は作者と別人である。**`pyproject.toml` の `authors` と `maintainers` が違う人で、PyPI 頼みでは見えない情報が clone した作業木には書いてある | 一次資料 | clone した作業木の pyproject.toml(commit 8958c49c38b1e4a8c07f0e4375d5e9cb68a087f7)/ docs/DATA/probes/20260922_tools_1_run6.log:26 |

### 候補の一覧

発見順(3 回目から引き継いだ順序のまま)。行頭の `[深掘り]` は §4.0 の表に語彙のすべての項目の行を持つものだけに付ける。それ以外は「浅い」と、何が未確認かを書く。

1. `Basana` — 非同期・イベント駆動の暗号資産向け枠組み。Apache-2.0。4 回目に深掘り済み。この回では何も足していない。
2. `Backtrader` — バックテストの機関。GPLv3+。4 回目に深掘り済み。この回では何も足していない。
3. PySystemtrade — **この回で疎な clone に切り替えて取り直した。**ライセンス・版・作者・保守者・依存・ファイル数が埋まった。**浅い**(導入・最小実行が未確認。`ib_async` を通じた Interactive Brokers 前提の部分を鍵なしでどこまで動かせるかを試していない)。
4. `PyBroker` — PyPI 上の名前は lib-pybroker。Apache License 2.0 with Commons Clause。4 回目に深掘り済み。この回では何も足していない。
5. `bt` — MIT。注文の種別という概念が無い。4 回目に深掘り済み。この回では何も足していない。
6. [深掘り] `Ziplime` — **この回の深掘り。**GPL-3.0(GitHub の `master` の LICENSE)。zipline を polars で組み直したもの。`python3.12` の隔離 venv に導入し、合成の日足で**指値と成行の 1 往復**まで通した。既定の取り込みは鍵が要るが、`CSVDataSource` で迂回できる。
7. Superalgos — PyPI に無し。GitHub の LICENSE は Apache License Version 2.0(3 回目の実測)。**浅い**(版・更新日・導入・最小実行が未確認。Node.js 系で pip の経路に無い。この回は着手していない)。
8. OpenTrader — PyPI に無し。GitHub の master ブランチの LICENSE は Apache License Version 2.0(3 回目の実測)。**浅い**(版・更新日・導入・最小実行が未確認。この回は着手していない)。
9. CryptoSignal — PyPI に無し。GitHub の LICENSE は MIT License(3 回目の実測)。**浅い**(版・更新日・導入・最小実行が未確認。この回は着手していない)。
10. `fast-trade` — 5 回目に深掘り済み。AGPL-3.0。この回では何も足していない。
11. OctoBot — GPL-3.0。**浅い**(導入・最小実行が未確認。この回は着手していない。**`python3.12` が在ることは確かめたので、5 回目の「導入できない」は取り消されている**)。
12. pybotters — MIT。**浅い**(導入・最小実行・対応取引所の一次資料が未確認。この回は着手していない)。
13. DeviaVir/zenbot — 本家 carlos8f/zenbot の分岐。**浅い**(Node.js の導入・最小実行・保守の状態が未確認。この回は着手していない)。
14. Bot18 — carlos8f の後継。**浅い**(ライセンス欄・導入・最小実行が未確認。この回は着手していない)。
15. Mendl-Labs/BacktestingCore — master ブランチの LICENSE は Functional Source License, Version 1.1, ALv2 Future License(4 回目の実測)。**浅い**(README の原文・版・導入が未確認。この回は着手していない)。
16. Luczinsritter/event_driven_backtesting_engine — LICENSE ファイルは main と master のどちらも 404(4 回目の実測)。**浅い**(ライセンスの根拠がバッジだけ。版・導入・最小実行が未確認。この回は着手していない)。
17. mlflow — 実験の追跡の道具。**浅い**(単体での導入・最小実行をしていない。この回は着手していない)。
18. `zipline-reloaded` — 3 回目に深掘り済み。この回では何も足していない。
19. `Jesse` — 3 回目に深掘り済み。この回では何も足していない。
20. `VnPy` — 3 回目に深掘り済み。この回では何も足していない。
21. `Qlib` — 3 回目に深掘り済み。この回では何も足していない。
22. `Lean CLI` — 3 回目に深掘り済み。この回では何も足していない。
23. `hftbacktest` — 1 回目に深掘り済み。この回では何も足していない。
24. **限界: `Ziplime` の依存 `limexhub` と `lime-trader-sdk`、および README が挙げる LLM の中継業者は、それ自体が道具の候補になりうるが、この回では候補として立てていない。**次の実行で候補に足すかはリードが決める。

### ツール1件ごとの表

#### §4.0 の機械可読の表

深掘りしたのは `Ziplime` の 1 件。§4.0 の語彙のすべての項目について行を持つ。

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| `Ziplime` | 版 | 1.19.16 | 一次資料 | https://pypi.org/pypi/ziplime/json 取得日 2026-09-22(info.version)/ docs/DATA/probes/20260922_tools_1_run6.log:80 |
| `Ziplime` | 最終更新日 | PyPI の最新版の upload_time は 2026-06-18T09:21:46。GitHub の pushedAt は 2026-09-17T09:58:00Z で、**配布物のほうが古い** | 一次資料 | https://pypi.org/pypi/ziplime/json 取得日 2026-09-22 / https://ungh.cc/repos/Limex-com/ziplime 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run6.log:82 と :88 |
| `Ziplime` | ライセンス | GitHub の `master` の LICENSE は "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007"。GitHub の頁の表示は GPL-3.0。**PyPI 側は info.license も info.license_expression も None、wheel の METADATA にも License 行が無く、`License-File: LICENSE` と書いてあるのに該当ファイルが wheel に無い** | 一次資料 | https://raw.githubusercontent.com/Limex-com/ziplime/master/LICENSE 取得日 2026-09-22 / https://github.com/Limex-com/ziplime 取得日 2026-09-22 / https://pypi.org/pypi/ziplime/json 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run6.log:12 と :14 と :87 と :92 |
| `Ziplime` | 言語と動作環境 | Python。requires_python は `<4.0,>=3.12`。classifiers は 3 / 3.12 / 3.13 / 3.14。この環境の `/usr/bin/python3.12`(3.12.3)の隔離 venv で動いた。既定の `python3` は 3.11.15 なので、既定のままでは入らない | 一次資料 | https://pypi.org/pypi/ziplime/json 取得日 2026-09-22(info.requires_python / classifiers)/ docs/DATA/probes/20260922_tools_1_run6.log:2 と :30 と :80 と :81 |
| `Ziplime` | 対応取引所 | 模擬は `simulation`、実弾は `lime-trader-sdk` の 2 つだけ(`run --exchange-type`)。既定の取引所名は LIME。暦は exchange_calendars 経由で `--trading-calendar` に指定(既定 XNYS)。**国内の暗号資産取引所・国内証券の対応は無い** | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:40 と :42 |
| `Ziplime` | 星 | 564(fork 57、watchers 9) | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:83 と :88(ungh.cc の stars / forks / watchers) |
| `Ziplime` | コミット数 | 6,420 | 一次資料 | https://github.com/Limex-com/ziplime 取得日 2026-09-22(リポジトリの見出しの Commits)/ docs/DATA/probes/20260922_tools_1_run6.log:92 |
| `Ziplime` | 保守者数 | PyPI の info.author = "Ziplime"(組織名)、info.maintainer = None。GitHub の所有者は Limex-com。**GitHub の頁には contributors の数が表示されず、人数は取れていない**(試したこと: PyPI の json の author / maintainer、GitHub の頁の WebFetch、ungh.cc の repos の応答。いずれも人数を返さない) | 未確認 | docs/DATA/probes/20260922_tools_1_run6.log:80 と :88 と :92 |
| `Ziplime` | 週DL数 | last_day=26、last_week=86、last_month=268 | 一次資料 | https://pypistats.org/packages/ziplime 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run6.log:90。API の端点 /api/packages/ziplime/recent は 429 |
| `Ziplime` | 初回公開日 | 2024-12-06T15:21:25(0.1.11)。GitHub の createdAt は 2025-03-24T10:28:37Z。releases は 23 件 | 一次資料 | https://pypi.org/pypi/ziplime/json 取得日 2026-09-22(releases の最古 upload_time)/ https://ungh.cc/repos/Limex-com/ziplime 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run6.log:82 と :88 |
| `Ziplime` | 既知の脆弱性 | PyPI の vulnerabilities は長さ 0 | 一次資料 | https://pypi.org/pypi/ziplime/json 取得日 2026-09-22(vulnerabilities)/ docs/DATA/probes/20260922_tools_1_run6.log:82 |
| `Ziplime` | 料金体系 | 本体は GPL-3.0 の無償配布。README が挙げるデータ源は「Yahoo Finance (free, no API key)」と CSV が無料、Lime Trader SDK は証券口座、LimexHub は購読制。**GPL-3.0 は、改変したものを配布するときに同じ条件での公開を求める** | 一次資料 | https://raw.githubusercontent.com/Limex-com/ziplime/master/LICENSE 取得日 2026-09-22 / https://github.com/Limex-com/ziplime 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run6.log:87 と :94 |
| `Ziplime` | 無料枠の上限 | **本体側に上限は無い**(鍵も登録も無しに導入・最小実行まで到達した)。上限が掛かるのはデータ源の側で、LimexHub の購読の条件と Lime の口座の条件は本調査では取っていない(登録をしないため) | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:29 と :60 と :94 |
| `Ziplime` | 課金開始条件 | (a) `ingest` を使う瞬間に LimexHub か Lime Trader SDK の鍵が要る(鍵なしでは `Missing LIMEX_API_KEY environment variable.` で止まる)/ (b) 実弾の `--exchange-type lime-trader-sdk` は Lime の口座が要る / (c) README の「自然言語で戦略を書かせる」機能は外部の LLM の中継業者の鍵が要る。**自前の csv を `CSVDataSource` で渡す経路なら、どれにも触れずに回る** | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:40 と :44 と :60 と :94 |
| `Ziplime` | 隠れた依存 | 依存に `limexhub` と `lime-trader-sdk`(どちらも Lime / Limex の商用のデータ・約定の窓口)が**必須の依存として**入る。導入しただけでは通信しないが、`ingest` を打つ経路はこの 2 つしか選べない。`yfinance` も必須の依存に入っている | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :15 と :33 |
| `Ziplime` | 登録の要否 | 導入と、`CSVDataSource` を使う模擬には不要(鍵なしで到達した)。`ingest` と実弾には要る(渡すもの: LimexHub は購読の登録、Lime Trader SDK は証券口座の開設。**この調査では登録も鍵の発行もしていない**) | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:44 と :60 |
| `Ziplime` | 到達経路 | PyPI の index から `pip download --no-deps` と `pip install` の両方が通る。GitHub 側は `raw.githubusercontent.com` の `master` が 200、`main` は 404 | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:9 と :29 と :87 |
| `Ziplime` | 導入可否 | 可。`/usr/bin/python3.12 -m venv` の隔離 venv に導入した。**既定の `python3`(3.11.15)では入らない** | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:8 と :29(rc=0) |
| `Ziplime` | install所要秒 | 54 | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:29(install_time_s) |
| `Ziplime` | 依存数 | 導入後の pip list は 74 パッケージ。wheel の METADATA の Requires-Dist は 30 個 | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :12 と :29(pkgs) |
| `Ziplime` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:29(pip_check) |
| `Ziplime` | 最小実行の可否 | 可。**指値と成行の 1 往復を通し、損益まで出た。**ただし §4.0 の「知見」6 の 3 つの欠陥を回避しないと動かない | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:60 と :74 |
| `Ziplime` | 最小実行の中身 | 合成の日足 40 本(乱数の種 7、symbol=SYN、暦 XNYS、取引所 XNGS)を csv に書き、`CSVDataSource` で読ませて `run_simulation` を 2026-01-05〜2026-02-20 で回した。算法は 2 本目の足で `LimitOrder(limit_price=1000000.0)` で +10、5 本目の足で `MarketOrder()` で -10。結果は Simulated 33 trading days / Errors: 0 / TX_COUNT 2 / ORDER_COUNT 2(どちらも status FILLED、filled は +10 と -10、commission はそれぞれ 0.01)/ PNL_SUM -15.545009999987087 / ENDING_VALUE 99984.45499000001 | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:60 から :74 |
| `Ziplime` | 実行所要秒 | 2.12(run_simulation の前後を perf_counter で挟んだ値 SIM_TIME_S 2.115829)。道具自身の表示は "Backtest completed in 0 seconds" | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:60 と :66 |
| `Ziplime` | wheel展開 | ziplime-1.19.16-py3-none-any.whl を `pip download --no-deps` で取り(537049 bytes)、413 ファイルを列挙(うち .py が 404)。最上位は ziplime と ziplime-1.19.16.dist-info の 2 つ | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:9 と :11 |
| `Ziplime` | setup.py導入時実行 | wheel に setup.py は 0 件。生成器は poetry-core、Root-Is-Purelib: true | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :11 |
| `Ziplime` | 同梱バイナリ | 0 件(.so / .pyd / .dll / .dylib / .exe のいずれも無い) | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :11 |
| `Ziplime` | 外部送信 | 配布物の .py に現れる外部の host は docs.scipy.org / en.wikipedia.org / finra.complinet.com / github.com / stockcharts.com / wiki.timetotrade.eu / www.apache.org / www.fidelity.com で、**いずれも説明文の中の参照先**。実際の送信先(LimexHub と Lime Trader)は依存の package 側にあり、本体の .py には URL が直書きされていない。鍵を置いていないので通信は起きていない。**走らせた状態での通信の観測はしていない** | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :16 と :44 |
| `Ziplime` | 自動発注機能 | **ある。**`run --exchange-type lime-trader-sdk` と `--live-market-data-provider lime-trader-sdk` で、同じ算法ファイルが実弾に回る。既定は `simulation` なので、指定しなければ発注しない | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:40 |
| `Ziplime` | 宣伝詐欺の兆候 | 「必ず儲かる」・Telegram だけの配布・秘密鍵の要求・提携リンクは見当たらない。**ただし配布物にライセンスの本文も所在も入っておらず、PyPI からリポジトリへ辿れない**(名前から推測した `Ziplime/ziplime` は 404)。これは詐欺の兆候ではなく、供給網の照合を難しくする欠落として記録する | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :12 と :14 と :83 |
| `Ziplime` | 当方データ投入 | 日付・始値・高値・安値・終値・出来高・銘柄の列を持つ csv をそのまま読ませられた。**当方の csv.gz の約定・清算をそのまま入れる経路は試していない**(列の形が違うので、足に直す前処理が要る) | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:60 |
| `Ziplime` | 時刻の扱い | 暦の時間帯を強制する。`CSVDataSource` は読んだ日付列に `trading_calendar.tz` を貼り直す(最小実行では America/New_York になった)。UTC のまま入れる経路は試していない。足の刻みは 1s から 1M まで選べる | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:33 と :61 と :62 |
| `Ziplime` | 再現性 | 同じ台本を 2 回打って PNL_SUM と ENDING_VALUE が完全に一致した。**道具側に乱数の種の指定は見ていない**(種は当方の合成データ側に置いたもの) | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:75 と :76 と :77 |
| `Ziplime` | 規模の見積 | 33 営業日の日足を 2.12 秒で回した。456 日分の日足なら、行数に比例すると置いて 29.24 秒あたりの規模になる。**ティック単位・分足単位は試していない**(足の刻みは 1s まで選べるので、同じ比例で外挿すると桁が変わる) | 推定 | docs/DATA/probes/20260922_tools_1_run6.log:60 と :97 からの外挿(行数に線形と仮定) |
| `Ziplime` | 4軸1_道具 | 入れられる。`python3.12` の隔離 venv に入り、自前の csv を渡して指値と成行の往復まで回せた。**鍵の要る `ingest` を通さずに使える**ことを実測で確かめた | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:29 と :60 |
| `Ziplime` | 4軸2_情報 | 必須の依存に LimexHub(購読制のデータ)・Lime Trader SDK(証券の板と約定)・yfinance が入る。当方の道具立てに対応物が無い。ただし鍵が無いので中身は見ていない | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :15 と :44 |
| `Ziplime` | 4軸3_視点 | (a) 滑りの模型が差し替え式で、出来高比・変動率と出来高の比・固定 bp・滑りなしを選べる / (b) 手数料の模型も株・先物で分かれ、1 株あたり・1 取引あたり・1 枚あたり・金額比で選べる / (c) 注文の型が 4 つ / (d) 取引所の暦を第一級の入力として持つ / (e) 同じ算法ファイルが模擬と実弾で共有される。**当方の `src/bot/backtest/engine.py` には (a)(b)(d) の差し替えの口が無く、(c) は maker/taker の 2 つだけ** | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:47 と :49 と :50 |
| `Ziplime` | 4軸4_向上 | perf が返す欄に、当方の metrics に無いものが含まれる(net_leverage / gross_leverage / max_leverage / treasury_period_return / excess_return / alpha / beta / sortino / benchmark_volatility / capital_used / longs_count / shorts_count)。とくに**建玉のてこの 3 種類を毎期出す**点は、当方のリスクの見方に対応物が無い | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:60 と :67 |
| `Ziplime` | 配布元の一致 | **照合できない。**PyPI の project_urls も home_page も None で、配布物にもリポジトリの所在が無い。GitHub の `Limex-com/ziplime` が本体であることは、WebSearch で見つけた所在に対して LICENSE が 200 で返り、README の内容が導入した版の CLI と整合することからの推定にとどまる | 推定 | docs/DATA/probes/20260922_tools_1_run6.log:80 と :83 と :87 と :92 |
| `Ziplime` | 難読化 | 見当たらない。配布物は .py のみ、同梱バイナリは 0 件、eval/exec と base64 等の組み合わせの一致も 0 件 | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :11 と :17 |
| `Ziplime` | 外部URL取得 | 導入の段では起きない(setup.py が 0 件、生成器は poetry-core)。実行の段では `ingest` と実弾の経路が外へ行くが、どちらも鍵が無いと入口で止まる | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :11 と :44 |
| `Ziplime` | 依存の一覧 | aiocache / aiofiles / aiosqlite / alembic / asyncclick / empyrical-reloaded / exchange-calendars / greenlet / h5py / iso3166 / iso4217 / joblib / lime-trader-sdk / limexhub / networkx / numexpr / orjson / pandas / pandas-stubs / polars / pyarrow / pydantic / pygments / python-dateutil / scipy / setuptools / sqlalchemy / structlog / tabulate / yfinance | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:10 と :15(wheel の METADATA の Requires-Dist) |
| `Ziplime` | 保守者名の一貫性 | PyPI の info.author は組織名 "Ziplime"、info.maintainer は None。GitHub の所有者は Limex-com。**名前が一致しない**(Ziplime は製品名、Limex-com は組織)。個人名はどちらの側にも出てこない | 一次資料 | https://pypi.org/pypi/ziplime/json 取得日 2026-09-22(info.author / info.maintainer)/ https://ungh.cc/repos/Limex-com/ziplime 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run6.log:80 と :88 |

#### 取り直しの結果(5 回目のリードの検収が渡したもの)

§4.0 の表と別の表にする(起動指定「**取り直し(前の節で未確認だったものの値)は §4.0 の表と別の表に書いてください**」)。

| 道具 | 項目 | 前の節の値 | この回の値 | 印 | 根拠 |
|---|---|---|---|---|---|
| `Ziplime` | 導入の可否(取り直し) | 既定の `python3` では不可。環境の可否は未確認 | **可。**`/usr/bin/python3.12` の隔離 venv に入り、pip check も通った | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:2 と :29 |
| `Ziplime` | ライセンス(取り直し) | 未確認(PyPI の info.license も license_expression も None、リポジトリの所在も不明) | GitHub の `master` の LICENSE が GNU GPL v3。GitHub の頁の表示も GPL-3.0 | 一次資料 | https://raw.githubusercontent.com/Limex-com/ziplime/master/LICENSE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run6.log:87 と :92 |
| `Ziplime` | GitHub の所在(取り直し) | 未確認(`ungh.cc/repos/Ziplime/ziplime` は接続時間切れ) | `Limex-com/ziplime`。推測した `Ziplime/ziplime` は raw も ungh.cc も 404 | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:83 から :88 |
| `Ziplime` | 最小実行(取り直し) | 未確認 | 可。指値と成行の 1 往復が通り、損益が出た | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:60 |
| PySystemtrade | clone の大きさ(取り直し) | 878 MB(全部の clone。リードの条件の 200 MB を超えたので止めた) | 3.6M(`--filter=blob:none --sparse` で `data/` を外した。`.git` は 904K) | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:18 と :20 |

#### 浅い候補について、この回に新しく測ったもの(深掘りではない)

§4.0 の表には入れない(委任文 §4.0「浅い候補(深掘りしていない)は表に入れず」)。

| 道具 | 測ったこと | 値 | 印 | 根拠 |
|---|---|---|---|---|
| PySystemtrade | LICENSE ファイルの本文 | GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007(clone した作業木の LICENSE)。setup.py の license は "GNU GPL v3" | 一次資料 | clone した作業木(commit 8958c49c38b1e4a8c07f0e4375d5e9cb68a087f7)/ docs/DATA/probes/20260922_tools_1_run6.log:23 と :25 と :28 |
| PySystemtrade | 版・作者・保守者 | version 1.8.2 / authors = Robert Carver / maintainers = Andy Geach / requires-python = ">=3.10" / keywords = systematic trading, interactive brokers | 一次資料 | clone した作業木の pyproject.toml / docs/DATA/probes/20260922_tools_1_run6.log:26 |
| PySystemtrade | 依存 | pandas==2.1.3 matplotlib>=3.0.0 PyYAML==6.0.1 numpy>=1.24.0 scipy>=1.0.0 pymongo==3.11.3 ib_async>=2,<3 psutil==7.2.1 Flask>=2.0.1 Werkzeug>=2.0.1 statsmodels==0.14.0 PyPDF2>=2.5.0 scikit-learn>1.3.0 pytz==2023.3 pyarrow>=16,<20。**pymongo と ib_async があるので、そのまま使うには MongoDB と Interactive Brokers の接続が前提になる** | 一次資料 | clone した作業木の pyproject.toml / docs/DATA/probes/20260922_tools_1_run6.log:27 |
| PySystemtrade | 規模 | 疎な作業木(systems sysquant sysobjects syscore sysdata)で .py が 328 本。最新のコミットは 2026-09-21T11:55:15+01:00 | 実測 | docs/DATA/probes/20260922_tools_1_run6.log:19 と :22 と :23 |

### 予算

| 項目 | 値 |
|---|---|
| 上限 | 1 回 5 万トークン・20 分 |
| 実績 | 上限に達したため中断した。深掘りは `Ziplime` の 1 件。取り直しは 5 件すべて埋まった(`Ziplime` の 4 件と PySystemtrade の 1 件) |
| 未完了 | 候補の一覧の 7・8・9・11・12・13・14・15・16・17 番はこの回で着手していない。3 番は浅いまま。区分 1 は**未完了**(委任文 §2 の条件 = 残りの候補が空で、新しい検索計画が新しい候補を 1 件も出さない、を満たしていない) |

### 原文に無い判断(黙って決めずに書き出す)

1. **`Ziplime` の README に並ぶ LLM の製品名を写さなかった。**委任文 §10 に「モデル名を書かない」があり、`CLAUDE.md` §6 にも同じ規則がある。一方で委任文 §4 は「できること全部を一次資料の逐語で」と求めている。**逐語の要求と、名前を書かない規則がぶつかった。**この回は名前を書かない側を選び、生ログの 94 行目にその旨を注記した。どちらを優先するかはリードが決めること。
2. **候補の一覧に 24 番として「限界」の行を足した。**`Ziplime` の必須の依存である LimexHub と Lime Trader SDK は、それ自体がデータと執行の道具だが、この回では候補として立てていない。**候補から黙って落とさない**(委任文 §3)ために、落としていないことを明記した。番号を振ったのは一覧の形に合わせたためで、道具の候補として数えているわけではない。
3. **`Ziplime` の最小実行で、委任文 §5-4 が禁じていない範囲の「回避」を 3 つ行った**(`frequency` に文字列を渡す / `auto_close_date` に日付を置く / 対照銘柄に自分自身を指定する)。回避しないと動かないので、**回避の内容と、回避しなかったときの誤りを全部生ログに残した**(試行 1 から 7)。「動いた」とだけ書くと、欠陥が消える。

### 受け入れ検査で残した行(自分で閉じなかったもの)

**0 件。**この回は当たった行を全部直した。直した内訳は次の 2 つで、どちらも自分の書き方の誤りであって検査の欠陥ではない。

1. **K7**: 浅い候補の表の 2 列目に `ライセンス` と書いたため、その行が §4.0 の機械可読の表の行として読まれ、
   PySystemtrade に語彙のすべての項目を要求された。2 列目を `LICENSE ファイルの本文` に直した。
   **語彙の語を、§4.0 以外の表の見出しや項目名に使ってはならない**(次の回への申し送り)。
2. **K11**: 根拠が生ログの**続きの行**(出力だけの行)を指していて、その行に `rc=` も `time_s=` も無かった。
   生ログに `rc=` を書き足すのではなく、**その出力を生んだ手の見出し行を先に置く形**に直した
   (`…run6.log:10 と :11` のように、コマンドと終了コードのある行を先に指す)。
   5 回目のリードの検収 §5-2 が「検査を満たすために書く行が増えること自体が型」と書いていたので、
   **生ログ側には 1 文字も足していない。**

**リードへ渡す注意(自分で閉じていない。判定はリード)**: K12 は報告全体の**最後の**「---- 検査対象の合計 N 件」
だけを見る。5 回目の節の貼り付けが `0 件` のまま残っているので、**6 回目の節の貼り付けを書く前から K12 が
0 件で通っていた。**節ごとの貼り付けを照合していないので、古い節の貼り付けが新しい節の身代わりになりうる。

## 受け入れ検査の出力

委任文 §12 のコマンドを、**生ログを 4 本とも渡して**打った最後の出力の全文。

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

### `STRATEGY_IDEAS.md` / `DATA.md` 向けの一行候補(提案。マージしない)

- `DATA.md` 向け: 「`Ziplime` の `CSVDataSource` は、鍵なしで自前の足を模擬に渡せる唯一の経路。CLI の `ingest` には入口が無く、`ingest` は `LIMEX_API_KEY` を要求して止まる。」
- `STRATEGY_IDEAS.md` 向け: 「滑りの模型を差し替えて同じ戦略を回し、滑りの仮定が結論をどれだけ動かすかを測る(`Ziplime` は出来高比・変動率と出来高の比・固定 bp・滑りなしを標準で持つ)。」
## 区分1 — 7 回目の実行(2026-09-22)

委任文: `docs/DATA/delegations/20260922_tools_survey_prompt.md@ce0012c95154`。生ログ: `docs/DATA/probes/20260922_tools_1_run7.log`。
6 回目のリードの検収(`docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run6.md`)の §4 の 3 件の回答に従い、
(1) `Ziplime` の対応 LLM を取り直しの表に埋め、(2) LimexHub と Lime Trader SDK は区分 3 と区分 2 に引き継ぎ、
(3) 回避と失敗を全部生ログに残す書き方を続けた。この回の深掘りは `pybotters` と `OctoBot` の 2 件。
検索計画 6 本は、残りの候補がまだ空でないので打っていない(委任文 §2)。

### 当方の道具立て(`python3 scripts/tools_inventory.py` の出力全文。§8)

```
# 当方の道具立て(git ls-files から生成。2026-09-22T08:48:59Z、HEAD dc88f8e。コマンド: python3 scripts/tools_inventory.py)

## src/bot(package: ファイル数 / ファイル名)
- src/bot: 7 / atomic_file.py constants.py logging_setup.py main.py products.py radar.py settings.py
- src/bot/backtest: 3 / engine.py metrics.py walk_forward.py
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
- check_*: 8 / check_api.py check_data_ledger.py check_k1_binance.py check_k1_bitflyer_data.py check_kabu_api.py check_liquidation_feeds.py check_liquidation_history_depth.py check_scan_report.py
- build_*: 7 / build_basis.py build_bitflyer_lightchart_csv.py build_burst_library.py build_flow.py build_fx_event_library.py build_fx_event_library_2005_2014.py build_storm_library.py
- record_*: 5 / record_funding_basis.py record_liquidations.py record_oi.py record_realtime.py record_venues.py
- jev/: 3 / client.py redact.py schemas.py
- verify_*: 3 / verify_gates.py verify_liq_instrument.py verify_snapshots.py
- (単発): 2 / _research_audit_gate.py dashboard.py
- judge_*: 2 / judge_board_round.py judge_gates.py
- k1_*: 2 / k1_binance_data_quality.py k1_source.py
- paper_*: 2 / paper_on1.py paper_onr.py
- repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.py
- constants_*: 1 / constants_inventory.py
- data_*: 1 / data_quality.py
- explore_*: 1 / explore_o3c_oi_axis.py
- extract_*: 1 / extract_tape.py
- intake_*: 1 / intake_ledger.py
- liquidation_*: 1 / liquidation_report.py
- mirror_*: 1 / mirror_bitmex_archive.py
- normalize_*: 1 / normalize_bitflyer_executions.py
- phase2_*: 1 / phase2_seal.py
- preflight_*: 1 / preflight_prereg.py
- probe_*: 1 / probe_api_latency.py
- replay_*: 1 / replay_scalp_storm.py
- retention_*: 1 / retention_snapshot.py
- tools_*: 1 / tools_inventory.py
- tp_*: 1 / tp_operating_curve.py
- trace_*: 1 / trace_metrics.py
- validate_*: 1 / validate_composite.py
- x_*: 1 / x_fetch.py
- (.py 以外の scripts: 3 = scripts/fetch_all.sh scripts/install_git_hooks.sh scripts/regen_hook_manifest.sh)

## config: 32
  config/composite.yaml config/config.yaml config/constants.yaml config/etf_measure.yaml config/jev_delegation_tiers.yaml config/jev_design_examples/o3c_covariates.yaml config/jev_design_examples/o3c_observables.yaml config/jev_design_examples/signal2_covariates.yaml config/jev_design_examples/signal2_observables.yaml config/jev_design_examples/signal3_covariates.yaml config/jev_design_examples/signal3_observables.yaml config/jev_design_examples/signal4_covariates.yaml config/jev_design_examples/signal4_observables.yaml config/jev_design_examples/signal5_covariates.yaml config/jev_design_examples/signal5_observables.yaml config/jev_design_examples/signal6_covariates.yaml config/jev_design_examples/signal6_observables.yaml config/jev_design_examples/signal7_observables.yaml config/jev_design_examples/signal8_covariates.yaml config/jev_design_examples/signal8_observables.yaml config/jev_design_examples/signal8_observables_independent.yaml config/jev_design_examples/signal_covariates.yaml config/jev_design_examples/signal_observables.yaml config/jev_routes.yaml config/o3c_jev_state_bands.yaml config/o3c_signal_logit_chain.yaml config/o3c_signal_logit_first.yaml config/o3c_signal_logit_value_chain.yaml config/o3c_signal_logit_value_first.yaml config/on1_live.yaml config/products.yaml config/risk_limits.yaml

## deploy: 19
  deploy/bitflyer-bot.service deploy/bitflyer-fetch.service deploy/bitflyer-fetch.timer deploy/check_liq_recorder.bat deploy/etf_measure_entry.bat deploy/etf_measure_exit.bat deploy/fetch_all.bat deploy/mirror_bitmex.bat deploy/nightly_restart.bat deploy/on1_entry.bat deploy/on1_exit.bat deploy/probe_latency.bat deploy/reset_kill.bat deploy/restart_all.bat deploy/run_paper.bat deploy/setup.sh deploy/share_logs.bat deploy/start_all.bat deploy/stop_all.bat

## tests(ファイル): 139
  tests/conftest.py tests/fixtures/jev_ops/decisions.json tests/fixtures/jev_ops/notifications.jsonl tests/fixtures/jev_ops/status_page.html tests/test_app_fx_integration.py tests/test_audit_gates_wired.py tests/test_backtest.py tests/test_bitmex_mirror.py tests/test_board.py tests/test_board_round.py tests/test_board_walk.py tests/test_bot_research_overnight.py tests/test_build_flow.py tests/test_check_data_ledger.py tests/test_client.py tests/test_clock_burst.py tests/test_composite.py tests/test_constants.py tests/test_constants_inventory.py tests/test_dashboard.py tests/test_data_quality.py tests/test_data_quality_incremental.py tests/test_deploy.py tests/test_engine_maker_exit.py tests/test_etf_measure.py tests/test_extract_tape.py tests/test_fetch_backfill_scripts.py tests/test_fetch_binance_daily.py tests/test_fetch_binance_vision.py tests/test_fetch_history_candles.py tests/test_gz_members.py tests/test_intake_ledger.py tests/test_intent_map_rule.py tests/test_jev_audit_eval.py tests/test_jev_audit_loop.py tests/test_jev_check.py tests/test_jev_client.py tests/test_jev_delegate.py tests/test_jev_design.py tests/test_jev_ideas.py tests/test_jev_ops.py tests/test_jev_owner_log.py tests/test_jev_redact.py tests/test_jev_reply.py tests/test_jev_report_intake.py tests/test_jev_schemas.py tests/test_jev_scripts.py tests/test_jev_survey.py tests/test_jev_trace_export.py tests/test_judge_gates.py tests/test_k1_bitflyer_source.py tests/test_k1_bybit_source.py tests/test_k1_delay_decomp.py tests/test_k1_delay_entry.py tests/test_k1_flip_body.py tests/test_k1_lookahead.py tests/test_k1_no_invalidation.py tests/test_k1_round5.py tests/test_k1_seal_guard.py tests/test_k1_xvenue.py tests/test_liq_bands.py tests/test_liq_response.py tests/test_liq_response_dedup.py tests/test_liquidation_reader.py tests/test_maker_execution.py tests/test_market_data.py tests/test_market_view.py tests/test_max_hold.py tests/test_modes.py tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_ext.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_rows4.py tests/test_o3c_signal_calib.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore2.py tests/test_o3c_signal_explore3.py tests/test_o3c_signal_explore4.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_policy.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_on1_forward.py tests/test_on1_live.py tests/test_onr.py tests/test_onr_forward.py tests/test_orders.py tests/test_paper_state.py tests/test_phase2_p2_01.py tests/test_phase2_p2_01_final.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_phase2_p2_03.py tests/test_phase2_p2_03_final.py tests/test_phase2_p2_03_iter2.py tests/test_phase2_p2_04.py tests/test_phase2_seal.py tests/test_portfolio_and_strategy.py tests/test_position_ladder.py tests/test_preflight_prereg.py tests/test_probe_api_latency.py tests/test_qa_make_known_answer.py tests/test_qa_make_known_answer_maker.py tests/test_qa_make_known_answer_maker3.py tests/test_qa_make_known_answer_steer.py tests/test_qa_maker_fill_ref.py tests/test_qa_pipeline_known_answer.py tests/test_qa_score_audit.py tests/test_radar.py tests/test_realtime_recorder.py tests/test_record_funding_basis.py tests/test_record_liquidations.py tests/test_record_liquidations_writer.py tests/test_record_venues.py tests/test_repair_gz_listing.py tests/test_research_protocol_rules.py tests/test_resilience.py tests/test_retention_snapshot.py tests/test_risk.py tests/test_scalp_logic.py tests/test_sealed_load_diagnostic.py tests/test_sealed_ts_us.py tests/test_short_margin.py tests/test_tp_sl.py tests/test_verify_snapshots.py tests/test_wick_stop.py tests/test_x_fetch.py tests/test_xborder.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_fx.py tests/test_xborder_p2_known_answer.py tests/test_xborder_p2_state.py

## .claude/hooks: 8
  .claude/hooks/_verify_manifest.sh .claude/hooks/delegation_audit_gate.sh .claude/hooks/deny_protected_paths.sh .claude/hooks/jev_notice.sh .claude/hooks/owner_options_gate.sh .claude/hooks/owner_turn_digest.sh .claude/hooks/session_start_digest.sh .claude/hooks/trace_snapshot.sh

## .claude/agents: 3
  .claude/agents/owner-auditor-candidate.md .claude/agents/owner-auditor.md .claude/agents/owner-model-auditor.md

## .claude/skills: 9
  .claude/skills/delegated-study/SKILL.md .claude/skills/owner-audit/SKILL.md .claude/skills/owner-options/SKILL.md .claude/skills/owner-procedure/SKILL.md .claude/skills/research-protocol/SKILL.md .claude/skills/research-squad/SKILL.md .claude/skills/typesafe-ai/LICENSE .claude/skills/typesafe-ai/SKILL.md .claude/skills/x-research/SKILL.md

## githooks: 1
  githooks/pre-push

## docs(.md): 298
  docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11.md docs/AUDITOR/EVAL_2026-09-11_control_review.md docs/AUDITOR/EVAL_2026-09-11b.md docs/AUDITOR/IMPROVEMENT.md docs/AUDITOR/JEV/LABELS_NOTES_2026-09-19.md docs/AUDITOR/JEV/PREREG_2026-09-19.md docs/AUDITOR/KNOWN_ANSWERS.md docs/AUDITOR/KNOWN_ANSWERS_ADDENDUM.md docs/AUDITOR/OWNER_MODEL_SOURCE.md docs/AUDITOR/PRINCIPLES.md docs/AUDITOR/PROCESS_METRICS.md docs/AUDITOR/PROPOSED_CHANGES_2026-09-11.md docs/AUDITOR/READDO/audit_stop.md docs/AUDITOR/READDO/before_unseal.md docs/AUDITOR/READDO/owner_objection.md docs/AUDITOR/READDO/push_blocked.md docs/AUDITOR/READDO/repeat_defect.md docs/AUDITOR/TREND.md docs/AUDITOR/VERDICTS/2026-09-11_k1_closure_entries.md docs/AUDITOR/VERDICTS/2026-09-11_proposed_changes_and_eval_b.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_execution.md docs/AUDITOR/VERDICTS/2026-09-12_docs_reorg_plan.md docs/AUDITOR/VERDICTS/2026-09-12_o3c_reframe_reading.md docs/AUDITOR/VERDICTS/2026-09-12_p14_liquidation_fix.md docs/AUDITOR/VERDICTS/2026-09-12_p4n_nightly_restart.md docs/AUDITOR/VERDICTS/2026-09-12_rules_reduction.md docs/AUDITOR/VERDICTS/2026-09-16_policy4_report.md docs/AUDITOR/VERDICTS/2026-09-17_anchor_report.md docs/AUDITOR/VERDICTS/2026-09-17_closure.md docs/AUDITOR/VERDICTS/2026-09-17_data_collection.md docs/AUDITOR/VERDICTS/2026-09-17_missing.md docs/AUDITOR/VERDICTS/2026-09-17_oi_distance.md docs/AUDITOR/VERDICTS/2026-09-17_price_level.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_ext.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_full.md docs/AUDITOR/VERDICTS/2026-09-17_price_level_rows4.md docs/AUDITOR/VERDICTS/2026-09-18_oi_distance_split.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_design.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r10.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r2.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r3.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r4.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r5.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r6.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r7.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r8.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_prereg_r9.md docs/AUDITOR/VERDICTS/2026-09-18_reaction_run12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r11.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_prereg_r12.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_r2_prereg.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r2.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_report_r3.md docs/AUDITOR/VERDICTS/2026-09-19_reaction_result.md docs/AUDITOR/VERDICTS/2026-09-19_signal_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_design.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore2_report.md docs/AUDITOR/VERDICTS/2026-09-19_signal_explore_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_continue_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore3_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore4_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_explore5_report.md docs/AUDITOR/VERDICTS/2026-09-20_signal_materials_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_design.md docs/AUDITOR/VERDICTS/2026-09-20_signal_policy_result.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_design.md docs/AUDITOR/VERDICTS/2026-09-21_signal_value_result.md docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md docs/AUDITOR/VERDICTS/2026-09-21_tools_survey_prompt.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run2.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run3.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run4.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run5.md docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run6.md docs/AUDITOR/VERDICTS/2026-09-22_tools_survey_prompt_v12.md docs/AUDITOR/VERDICTS/README.md docs/AUDITOR/answers/KA-01.md docs/AUDITOR/answers/KA-02.md docs/AUDITOR/answers/KA-04.md docs/AUDITOR/answers/KA-05.md docs/AUDITOR/answers/KA-06.md docs/AUDITOR/answers/KA-07.md docs/AUDITOR/answers/KA-08.md docs/AUDITOR/answers/KA-09.md docs/AUDITOR/answers/KA-10.md docs/AUDITOR/answers/KA-16.md docs/AUDITOR/answers/KA-17.md docs/AUDITOR/answers/KA-18.md docs/AUDITOR/answers/KA-19.md docs/AUDITOR/answers/KA-20.md docs/AUDITOR/answers/KA-21.md docs/AUDITOR/answers/KA-22.md docs/AUDITOR/answers/KA-23.md docs/AUDITOR/answers/KA-24.md docs/AUDITOR/answers/KA-25.md docs/AUDITOR/answers/KA-26.md docs/AUDITOR/answers/KA-27.md docs/AUDITOR/answers/KA-28.md docs/AUDITOR/before/HYGIENE_2026-09-11.md docs/AUDITOR/before/KA-01.md docs/AUDITOR/before/KA-02.md docs/AUDITOR/before/KA-04.md docs/AUDITOR/before/KA-05.md docs/AUDITOR/before/KA-06.md docs/AUDITOR/before/KA-07.md docs/AUDITOR/before/KA-08.md docs/AUDITOR/before/KA-09.md docs/AUDITOR/before/KA-10.md docs/AUDITOR/before/KA-16.md docs/AUDITOR/before/KA-17.md docs/AUDITOR/before/KA-18.md docs/AUDITOR/before/KA-19.md docs/AUDITOR/before/KA-20.md docs/AUDITOR/before/KA-21.md docs/AUDITOR/before/KA-22.md docs/AUDITOR/before/KA-23.md docs/AUDITOR/before/KA-24.md docs/AUDITOR/before/KA-25.md docs/AUDITOR/before/KA-26.md docs/AUDITOR/before/KA-27.md docs/AUDITOR/before/KA-28.md docs/DATA.md docs/DATA/SCAN_2026-09-16.md docs/DATA/SCAN_2026-09-21_tools.md docs/DATA/delegations/20260919_o3c_signal_explore2_prompt.md docs/DATA/delegations/20260920_o3c_cascade_read_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_jev_prompt.md docs/DATA/delegations/20260920_o3c_signal_continue_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore3_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore4_prompt.md docs/DATA/delegations/20260920_o3c_signal_explore5_prompt.md docs/DATA/delegations/20260920_o3c_signal_jev_state_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials2_prompt.md docs/DATA/delegations/20260920_o3c_signal_materials_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy2_stage2_prompt.md docs/DATA/delegations/20260920_o3c_signal_policy_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_prompt.md docs/DATA/delegations/20260921_o3c_signal_value_tp_prompt.md docs/DATA/delegations/20260921_tools_survey_prompt.md docs/DATA/delegations/20260922_tools_survey_prompt.md docs/DATA/probes/20260913_liquidation_integrity.md docs/DATA/probes/20260919_reaction_prereg_outputs.md docs/DATA/probes/20260920_o3c_cascade_read.md docs/DATA/probes/20260920_o3c_materials_read.md docs/DATA/surveys/BINANCE_CM_MMR_2026-09-17.md docs/DATA/surveys/BITFLYER_HISTORY_SOURCES.md docs/DATA/surveys/ETF_ALTERNATIVES.md docs/DATA/surveys/G2_DATA_INVENTORY.md docs/DATA/surveys/LIQUIDATION_FEED_REACHABILITY.md docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_ACCEPTANCE_2026-09-13.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_A_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_B_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_C_HYPERLIQUID_2026-09-12.md docs/DATA/surveys/O3C_PROCUREMENT_SUPP_D_VENUE_UNIVERSE_2026-09-12.md docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md docs/DATA_CONSUMPTION_LOG.md docs/DELEGATION.md docs/DISCUSSIONS/2026-09-04_postmortem_tp_precursor.md docs/DISCUSSIONS/2026-09-06_data_dependency.md docs/DISCUSSIONS/2026-09-08_external_ecosystem.md docs/DISCUSSIONS/2026-09-08_matilda_intent_vs_test.md docs/DISCUSSIONS/2026-09-09_prereg_deep_dive.md docs/DISCUSSIONS/2026-09-09_the_day_nothing_shipped.md docs/DISCUSSIONS/2026-09-12_docs_reorg_plan.md docs/DISCUSSIONS/2026-09-12_generation_vs_filtering.md docs/DISCUSSIONS/2026-09-12_rules_inventory.md docs/DISCUSSIONS/2026-09-12_rules_reduction_proposal.md docs/DISCUSSIONS/2026-09-13_root_cause.md docs/DISCUSSIONS/2026-09-13_worst_day.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/PLAN.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/README.md docs/DISCUSSIONS/2026-09-14_instruction_adherence/STAGE0_hook_probe.md docs/DISCUSSIONS/2026-09-16_scope_claim_gate_proposal.md docs/DISCUSSIONS/2026-09-18_jev_trade_integration_decision_for_fable_v2.md docs/DISCUSSIONS/2026-09-19_jev_adoption_review.md docs/DISCUSSIONS/2026-09-19_jev_common_module_review.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/A_judgment_points.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/B_failures.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/C_vendor_sources.md docs/DISCUSSIONS/2026-09-19_jev_review_inventories/D_study_notes.md docs/INCIDENTS.md docs/INDEX.md docs/JEV.md docs/NEGATIVE_FACTS.md docs/OPERATIONS.md docs/OPERATIONS_JPX.md docs/OWNER_LOG.md docs/OWNER_PROCEDURES.md docs/OWNER_STATUS.md docs/PHASE2/EXEC/EXEC_FLOOR_PREREG.md docs/PHASE2/EXEC/RESULT.md docs/PHASE2/INSTRUMENT_VERIFY/AUDIT_LEDGER_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-14.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-16_policy4.md docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-17_anchor.md docs/PHASE2/K1/AUDIT_TRIAGE.md docs/PHASE2/K1/BINANCE_PLAN.md docs/PHASE2/K1/DEEPDIVE_PLAN.md docs/PHASE2/K1/FRESH_BITFLYER_PREREG.md docs/PHASE2/K1/H1_PREREG.md docs/PHASE2/K1/H2_PREREG.md docs/PHASE2/K1/H3_DECOMP_PREREG.md docs/PHASE2/K1/H3_PREREG.md docs/PHASE2/K1/HANDOFF.md docs/PHASE2/K1/JUDGEMENT_PREREG.md docs/PHASE2/K1/PREFLIGHT.md docs/PHASE2/K1/PREREG.md docs/PHASE2/K1/RESULT.md docs/PHASE2/K1/ROUND5_PREREG.md docs/PHASE2/K1/XVENUE_PREREG.md docs/PHASE2/K1/binance/CHECKS.md docs/PHASE2/O3C/BRANCH_MAP.md docs/PHASE2/O3C/DATA_AVAILABILITY.md docs/PHASE2/O3C/DATA_COLLECTION_2026-09-17.md docs/PHASE2/O3C/INTENT_MAP.md docs/PHASE2/O3C/MISSING_2026-09-17.md docs/PHASE2/O3C/OWNER_INTENT_2026-09-12.md docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/EXT_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/FULL_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_SPLIT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_DRAFT_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_R2_PREREG_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RESULT_2026-09-19.md docs/PHASE2/O3C/PRICE_LEVEL/REACTION_RUN12_2026-09-18.md docs/PHASE2/O3C/PRICE_LEVEL/ROWS4_2026-09-17.md docs/PHASE2/O3C/PRICE_LEVEL/SAMPLE_2026-09-17.md docs/PHASE2/O3C/REFRAME/DIFF_2026-09-12.md docs/PHASE2/O3C/REFRAME/LEAD_READING_2026-09-12.md docs/PHASE2/O3C/REFRAME/data_engineer.md docs/PHASE2/O3C/REFRAME/discretionary_trader.md docs/PHASE2/O3C/REFRAME/liquidation_engine.md docs/PHASE2/O3C/REFRAME/market_maker.md docs/PHASE2/O3C/REFRAME/microstructure.md docs/PHASE2/O3C/SIGNAL/CONTINUE_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/CONTINUE_JEV_RUN_NOTE_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE2_DELEGATE_REPORT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/EXPLORE3_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE4_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/EXPLORE5_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/JEV_STATE_PREVIEW_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS2_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/MATERIALS_DELEGATE_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/POLICY_STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW2_2026-09-19.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW3_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW4_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW5_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW6_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW9_2026-09-21.md docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_DESIGN_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE2_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE3_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE4_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE5_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_EXPLORE_RESULT_2026-09-19.md docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_RESULT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_RESULT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/STAGE2_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE1_REPORT_2026-09-21.md docs/PHASE2/O3C/SIGNAL/VALUE_STAGE2_REPORT_2026-09-21.md docs/PHASE2/O3C/STAGE0A_2026-09-14.md docs/PHASE2/O3C/TRIGGER_TRACE.md docs/PROJECT_GOAL.md docs/STRATEGY_IDEAS.md docs/legacy/KATSUO_INTENT_MAP.md docs/legacy/KATSUO_PARAMETER_INVENTORY.md docs/legacy/README.md

## backtest_data(ディレクトリ数)
  147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H_20260905 audit_fetch_JPX_n225f_months_20260906 audit_fetch_JPX_tick_20260906 audit_fetch_P2-08_docs_20260906 audit_fetch_P2-08b_20260906 audit_fetch_bitflyer_history_20260906 audit_fetch_etf_alternatives_20260906 audit_fetch_etf_units_20260906 audit_fetch_micro_fee_20260906 auto_bitflyer_executions_20260905 auto_bitflyer_executions_20260921 auto_oi_snapshots_20260905 auto_oi_snapshots_20260921 auto_okx_long_short_ratio_20260905 auto_okx_open_interest_1h_20260905 auto_okx_open_interest_1h_20260921 auto_okx_open_interest_5m_20260905 auto_okx_open_interest_5m_20260906 auto_okx_open_interest_5m_20260907 auto_okx_open_interest_5m_20260908 auto_okx_open_interest_5m_20260909 auto_okx_open_interest_5m_20260910 auto_okx_open_interest_5m_20260911 auto_okx_open_interest_5m_20260912 auto_okx_open_interest_5m_20260915 auto_okx_open_interest_5m_20260918 auto_okx_open_interest_5m_20260921 auto_venues_20260905 auto_venues_20260921 binance_BTCUSDT_1m.csv binance_BTCUSDT_1m_20170801_20231231 binance_BTCUSDT_1m_20240101_20260831 binance_BTCUSDT_1m_210d_20260820.csv.gz binance_BTCUSDT_1s_20260723_20260906 binance_BTCUSDT_aggTrades_20260723_20260906 binance_BTCUSDT_aggTrades_tardis_days binance_XRPUSDT_1d.csv binance_XRPUSDT_1m.csv binance_XRPUSDT_4h.csv binance_cm_o3c_20260913 binance_cm_o3c_supp_20260917 binance_um_BTCUSDT_aggTrades_20260723_20260906 bitbank_btc_jpy_transactions_monthly_first_days bitbank_xrp_jpy_1m.csv bitflyer_executions_backfill_20260921 bitflyer_executions_us_20260723_20260906 bitflyer_lightchart_BTC_JPY_1m_20260906 bitflyer_lightchart_FX_BTC_JPY_1m_20260906 bitmex_insurance_20260912 bitmex_trade_1s_XBTUSD board_round_20260904 burst_events_20260820 bybit_BTCUSDT_1m_20260910 bybit_reachability_check_20260906 candles_BTC_JPY_20260820.csv candles_ETH_JPY_20260820.csv candles_FX_BTC_JPY_20260820.csv candles_FX_BTC_JPY_30d_20260820.csv candles_FX_BTC_JPY_31d_20260823.csv.gz candles_XRP_JPY_20260820.csv coinalyze_liquidations_20260921 daily_btcusd_bitstamp_20260828.csv.gz daily_btcusd_coinbase_20260828.csv.gz daily_btcusd_yahoo_20260828.csv.gz daily_ethusd_bitstamp_20260828.csv.gz daily_ethusd_coinbase_20260828.csv.gz daily_ethusd_yahoo_20260828.csv.gz executions_FX_BTC_JPY_31d_20260823.csv.gz executions_FX_BTC_JPY_31d_20260908 flow_FX_BTC_JPY_20260820.csv fred_DEXJPUS.csv fred_DFF.csv fred_DGS2.csv fred_IR3TIB01JPM156N.csv fred_IRSTCI01JPM156N.csv fx_btc_jpy_1m_continuous_20260906 fx_event_ticks_2005_2014 fx_event_ticks_2015_2026 fx_fundamentals_20260822 fx_usdjpy_1m_20170801_20221231 fx_usdjpy_1m_20260822.csv.gz gate_liquidations_20260908 gmo_swap_usdjpy.csv jp_factors_20260905 jpx_daily_report_json_20260908 jpx_etf_daily_20260905 jpx_etf_daily_20260906_topix_alt liquidations_repaired_20260912 liquidations_repaired_20260917 mini_topixf_225labo_20260907 n225f_225labo_20260828 nk225_events_20260904 o3c_oi_distance_20260917 o3c_oi_distance_split_20260918 o3c_price_level_band_20260917 o3c_price_level_bundle_first_20260917 o3c_price_level_full_20260917 o3c_price_level_full_20260917_b005 o3c_price_level_full_20260917_b025 o3c_price_level_full_20260917_w72 o3c_price_level_full_20260917_w8 o3c_price_level_rows4_20260917 o3c_price_level_sample_20260917 o3c_price_level_sample_20260917_limitprice o3c_reaction_20260918_anchor o3c_reaction_20260918_anchor_trades o3c_reaction_20260918_anchor_trades_sample o3c_reaction_20260918_anchor_v1_rawcols o3c_reaction_20260918_full o3c_reaction_20260918_judge o3c_reaction_20260918_sample o3c_reaction_20260918_scale12_judgmentdays o3c_signal_continue_20260920 o3c_signal_explore2_20260919 o3c_signal_explore3_20260920 o3c_signal_explore4_20260920 o3c_signal_explore5_20260920 o3c_signal_explore_20260919 o3c_signal_materials_20260920 o3c_signal_policy_20260920 o3c_signal_value_20260921 okx_20260905 okx_btc_lsratio_1h_20260823.csv okx_btc_lsratio_5m_20260823.csv okx_btc_oi_1h_20260823.csv okx_btc_oi_5m_20260823.csv phase2_runs phase2_sealed qa_known_answer_20260905 qa_known_answer_maker3_20260907 qa_known_answer_maker3_v2_20260905 qa_known_answer_maker3_v3_20260905 qa_known_answer_maker4_20260905 qa_known_answer_maker4_r2_20260905 qa_known_answer_maker_20260905 qa_known_answer_steer_20260905 qa_pipeline_daily_20260905 qa_pipeline_daily_20260906 qa_pipeline_taker_20260905 regime_composite_20260901 reit_onr_20260904 storm_events_20260820 topixf_225labo_20260907 venue_survey_20260827 yutai_20260904
```

### 検索計画

| 幅 | 日本語クエリ | 英語クエリ | 実行 |
|---|---|---|---|
| 狭い | (未作成) | (未作成) | 未実行(残りの候補が空になっていないため) |
| 中間 | (未作成) | (未作成) | 未実行(同上) |
| 広い | (未作成) | (未作成) | 未実行(同上) |

### 出典

| URL / 経路 | 方法 | 生ログの行 |
|---|---|---|
| https://raw.githubusercontent.com/Limex-com/ziplime/master/README.md | curl(code=200) | 2 |
| https://raw.githubusercontent.com/Limex-com/ziplime/master/ai_assistant/requirements.txt | curl(code=200) | 8 |
| https://raw.githubusercontent.com/Limex-com/ziplime/master/ai_assistant/agent.py | curl(code=200) | 8 |
| https://pypi.org/pypi/OctoBot/json | curl(code=200) | 15 |
| https://pypi.org/pypi/pybotters/json | curl(code=200) | 15 |
| https://ungh.cc/repos/pybotters/pybotters | curl(code=200) | 86 |
| https://ungh.cc/repos/pybotters/pybotters/contributors | curl(code=200) | 86 |
| https://pypistats.org/api/packages/pybotters/recent | curl(code=200) | 86 |
| https://raw.githubusercontent.com/pybotters/pybotters/main/LICENCE | curl(code=200) | 86 |
| https://raw.githubusercontent.com/pybotters/pybotters/main/README.md | curl(code=200) | 91 |
| https://ungh.cc/repos/Drakkar-Software/OctoBot | curl(code=200) | 139 |
| https://ungh.cc/repos/Drakkar-Software/OctoBot/contributors | curl(1 回目 code=000、2 回目 code=200) | 139 |
| https://raw.githubusercontent.com/Drakkar-Software/OctoBot/master/LICENSE | curl(code=200) | 139 |
| https://pypistats.org/api/packages/octobot/recent | curl(code=429) | 139 |
| https://pypistats.org/packages/octobot | WebFetch | 139 |
| https://github.com/Drakkar-Software/OctoBot | WebFetch | 139 |
| https://github.com/pybotters/pybotters | WebFetch | 146 |
| https://tentacles.octobot.online/officials/packages/full/base/1.0.9/metadata.yaml | curl(code=200) | 121 |
| https://tentacles.octobot.online/officials/packages/full/base/1.0.9/any_platform.zip | curl -I(code=200) | 121 |
| https://api.github.com/repos/pybotters/pybotters/commits?per_page=1 | curl(code=403) | 139 |
| https://api.github.com/repos/Drakkar-Software/OctoBot/commits?per_page=1 | curl(code=403) | 139 |
| PyPI の index(pip download / pip install 経由) | v7o/bin/pip・v7p/bin/pip・v7o2/bin/pip | 28 と 55 と 101 |

### 知見

| # | 知見 | 印 | 根拠 |
|---|---|---|---|
| 1 | **`Ziplime` の README は個別の LLM の製品名を並べていない。**中継業者は OpenRouter の 1 社だけで、README の逐語は「Set your OpenRouter API key (free at https://openrouter.ai)」。製品名が現れるのは実装側の `ai_assistant/agent.py` の既定の引数で、既定は 1 つだけ指定されている。**6 回目が「README に LLM の製品名が並ぶ」と書いたのは、README ではなく実装側の話だった** | 一次資料 | https://raw.githubusercontent.com/Limex-com/ziplime/master/README.md 取得日 2026-09-22 / https://raw.githubusercontent.com/Limex-com/ziplime/master/ai_assistant/agent.py 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:2 と docs/DATA/probes/20260922_tools_1_run7.log:8 |
| 2 | **`pybotters` は国内の暗号資産取引所を 6 社、署名つきで叩ける。**README の表が bitFlyer / GMO Coin / bitbank / Coincheck / OKJ / BitTrade の 6 社に API auth の印を付けており、`pybotters/auth.py` のホストの一覧にも同じ 6 社の端点が入っている。**当方の道具立てには bitFlyer 以外の国内の執行が無い**(`docs/DATA/probes/20260921_tools_absent.log` の E 節) | 一次資料 | https://raw.githubusercontent.com/pybotters/pybotters/main/README.md 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:61 と docs/DATA/probes/20260922_tools_1_run7.log:91 |
| 3 | **`pybotters` の板の店(`bitFlyerDataStore`)は、本物の WebSocket 接続を通っていない板の更新を、例外も警告も出さずに全部捨てる。**`lightning_board_snapshot_` を受けたときに `isinstance(ws, ClientWebSocketResponse)` が真でないと `self._snapshots` に銘柄が登録されず、以後の更新が `if product_code in self._snapshots:` で落ちる。**記録した WS の生文を後から流し込む再現(リプレイ)をそのまま書くと、板が空のまま静かに回る** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:67 |
| 4 | **`pybotters` の板の店は、中値を跨いだ気配を自動で削る。**差分で入れた売り気配が板に残らなかった。逐語は `for side, ope in (("bids", operator.le), ("asks", operator.gt)):` で、中値を跨ぐ側を切る。**入れた板と読み出した板が一致しない場面がある** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:72 |
| 5 | **`pybotters` は鍵なしで注文の状態機械を合成データだけで回せる。**`child_order_events` の ORDER と EXECUTION を投入すると、注文の店から消えて建玉の店に移る動きまで再現できた。**外部通信も鍵も要らない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:72 |
| 6 | **`OctoBot` の導入は 1 回目の失敗で諦めると誤る。**1 回目は空き容量の不足で `OSError` になり、`pip cache purge` で空きを戻して別の隔離 venv に `--no-cache-dir` で入れ直したら通った。**止まった原因は道具側ではなく環境側の空き容量だった** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:96 と docs/DATA/probes/20260922_tools_1_run7.log:99 と docs/DATA/probes/20260922_tools_1_run7.log:101 |
| 7 | **`OctoBot` は遠隔測定を 2 系統持ち、誤りの送信は既定で止まっている。**誤りの送信は `ERROR_TRACKER_DSN` の環境変数が無いと初期化の入口で return する。稼働の測定は別で、既定の宛先が定数に直書きされており、環境変数で差し替えられる | 一次資料 | 配布物 octobot-2.1.1-py3-none-any.whl の中の octobot/constants.py と octobot_commons/constants.py と octobot/community/errors_upload/sentry_tracker.py / docs/DATA/probes/20260922_tools_1_run7.log:47 |
| 8 | **`OctoBot` の本体の配布物は、機能の大半を持っていない。**戦略・評価器・取引所の接続・画面はすべて拡張(tentacles)側にあり、外部の配布所から別に取る。大きさを測ってから取ったので数百 MB の一括取得には当たらなかった | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:121 と docs/DATA/probes/20260922_tools_1_run7.log:127 |
| 9 | **`OctoBot` の配布物には模擬用の見本データが 1 件も入っていない。**拡張を入れたあとも `.data` の一致は 0 件で、**成行と指値の 1 往復は今回到達できなかった**(不可ではなく未確認。次の手は生ログに書いた) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:130 |
| 10 | **`OctoBot` の必須の依存には、取引以外の外部連携が広く含まれる。**LLM の窓口・分散台帳の窓口・エージェントの相互接続・通信アプリの窓口・掲示板の窓口・誤り送信の窓口・雲の記憶の窓口が、選択ではなく必須の依存として入る。**入れるだけで外へ出る経路が増える** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 |
| 11 | **`pybotters` は同梱コードを持つ。**配布物の中に別の算法ライブラリ群を `_static_dependencies` として取り込んでおり、`eval` や `base64` に当たるのはその同梱側だけ。宣言上の依存は 1 件しかないのに、実際に読み込まれるコードはそれより広い | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 |
| 12 | **PyPI の頁からコミット数は取れない。**API の端点は 403 を返し、頁の表示を WebFetch で読むしかなかった。pypistats の API も 429 を返す日があり、頁側で取り直した | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:139 と docs/DATA/probes/20260922_tools_1_run7.log:146 |

### 候補の一覧

発見順(3 回目から引き継いだ順序のまま)。行頭の `[深掘り]` は §4.0 の表に語彙のすべての項目の行を持つものだけに付ける。それ以外は「浅い」と、何が未確認かを書く。

1. `Basana` — 非同期・イベント駆動の暗号資産向け枠組み。Apache-2.0。4 回目に深掘り済み。この回では何も足していない。
2. `Backtrader` — バックテストの機関。GPLv3+。4 回目に深掘り済み。この回では何も足していない。
3. PySystemtrade — 6 回目に疎な clone で取り直し済み。**浅い**(導入・最小実行が未確認。この回は着手していない)。
4. `PyBroker` — PyPI 上の名前は lib-pybroker。Apache License 2.0 with Commons Clause。4 回目に深掘り済み。この回では何も足していない。
5. `bt` — MIT。注文の種別という概念が無い。4 回目に深掘り済み。この回では何も足していない。
6. `Ziplime` — 6 回目に深掘り済み。この回は README の対応 LLM の取り直しだけを足した(取り直しの表)。
7. Superalgos — PyPI に無し。GitHub の LICENSE は Apache License Version 2.0(3 回目の実測)。**浅い**(版・更新日・導入・最小実行が未確認。Node.js 系で pip の経路に無い。この回は着手していない)。
8. OpenTrader — PyPI に無し。GitHub の master ブランチの LICENSE は Apache License Version 2.0(3 回目の実測)。**浅い**(版・更新日・導入・最小実行が未確認。この回は着手していない)。
9. CryptoSignal — PyPI に無し。GitHub の LICENSE は MIT License(3 回目の実測)。**浅い**(版・更新日・導入・最小実行が未確認。この回は着手していない)。
10. `fast-trade` — 5 回目に深掘り済み。AGPL-3.0。この回では何も足していない。
11. [深掘り] `OctoBot` — **この回の深掘り。**GPL-3.0。`/usr/bin/python3.12` の隔離 venv に導入し、拡張(tentacles)まで入れて起動口を確かめた。**成行と指値の 1 往復は未到達**(見本の模擬データが配布物に無い。不可ではなく未確認)。
12. [深掘り] `pybotters` — **この回の深掘り。**MIT。宣言上の依存は 1 件。`/usr/bin/python3.11` の隔離 venv に導入し、合成の板・約定・注文イベントで**板の再構成と注文の状態機械の 1 往復**を鍵なしで通した。
13. DeviaVir/zenbot — 本家 carlos8f/zenbot の分岐。**浅い**(Node.js の導入・最小実行・保守の状態が未確認。この回は着手していない)。
14. Bot18 — carlos8f の後継。**浅い**(ライセンス欄・導入・最小実行が未確認。この回は着手していない)。
15. Mendl-Labs/BacktestingCore — master ブランチの LICENSE は Functional Source License, Version 1.1, ALv2 Future License(4 回目の実測)。**浅い**(README の原文・版・導入が未確認。この回は着手していない)。
16. Luczinsritter/event_driven_backtesting_engine — LICENSE ファイルは main と master のどちらも 404(4 回目の実測)。**浅い**(ライセンスの根拠がバッジだけ。版・導入・最小実行が未確認。この回は着手していない)。
17. mlflow — 実験の追跡の道具。**浅い**(単体での導入・最小実行をしていない。この回は着手していない)。
18. `zipline-reloaded` — 3 回目に深掘り済み。この回では何も足していない。
19. `Jesse` — 3 回目に深掘り済み。この回では何も足していない。
20. `VnPy` — 3 回目に深掘り済み。この回では何も足していない。
21. `Qlib` — 3 回目に深掘り済み。この回では何も足していない。
22. `Lean CLI` — 3 回目に深掘り済み。この回では何も足していない。
23. `hftbacktest` — 1 回目に深掘り済み。この回では何も足していない。
24. **限界: 6 回目に立てた LimexHub と Lime Trader SDK は、6 回目のリードの検収 §4-2 の判断で区分 3(データ)と区分 2(執行)に引き継いだ。**区分 1 では追わない。
25. **限界: `OctoBot` の必須の依存のうち、取引以外の外部連携の窓口(LLM・分散台帳・エージェント相互接続・通信アプリ・掲示板・誤り送信・雲の記憶)は、それ自体が道具の候補になりうるが、この回では候補として立てていない。**次の実行で候補に足すかはリードが決める。

### ツール1件ごとの表

#### §4.0 の機械可読の表

この回に深掘りした道具は `pybotters` と `OctoBot`。どちらも §4.0 の語彙のすべての項目に行を持つ。

| 道具 | 項目 | 値 | 印 | 根拠 |
|---|---|---|---|---|
| `pybotters` | 版 | 1.11.2 | 一次資料 | https://pypi.org/pypi/pybotters/json 取得日 2026-09-22(info.version)/ docs/DATA/probes/20260922_tools_1_run7.log:15 |
| `pybotters` | 最終更新日 | PyPI の最新版の upload_time は 2026-04-17T07:19:41。GitHub の pushedAt は 2026-08-31T13:34:13Z で、**配布物のほうが古い** | 一次資料 | https://pypi.org/pypi/pybotters/json 取得日 2026-09-22 / https://ungh.cc/repos/pybotters/pybotters 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:86 |
| `pybotters` | ライセンス | MIT。PyPI の info.license_expression が 'MIT'(info.license は None)。GitHub の `main` の LICENCE の 1 行目が "MIT License"、3 行目が "Copyright (c) 2021 MtkN1"。wheel の METADATA は `License-File: LICENCE`(綴りは LICENSE ではなく LICENCE)。GitHub の頁の表示も MIT | 一次資料 | https://pypi.org/pypi/pybotters/json 取得日 2026-09-22 / https://raw.githubusercontent.com/pybotters/pybotters/main/LICENCE 取得日 2026-09-22 / https://github.com/pybotters/pybotters 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:86 と docs/DATA/probes/20260922_tools_1_run7.log:146 |
| `pybotters` | 言語と動作環境 | Python。requires_python は `>=3.10`。classifiers は 3 / 3.10 / 3.11 / 3.12 / 3.13 / 3.14。この環境の `/usr/bin/python3.11`(3.11.15)の隔離 venv で導入も実行も通った。既定の `python3` は 3.11.15 なので既定のままでも入る | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:13 と docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:55 |
| `pybotters` | 対応取引所 | README の "## 🏦 Exchanges" の表は 15 社で、API auth は 15 社すべてに ✅。DataStore は bitFlyer / GMO Coin / bitbank / Coincheck / Bybit / Binance / OKX / Phemex / Bitget / KuCoin / BitMEX / Hyperliquid に ✅、OKJ と BitTrade は "Not yet"、MEXC は "No support"。**国内は bitFlyer・GMO Coin・bitbank・Coincheck・OKJ・BitTrade の 6 社。**導入後に数えた DataStore の類は 18 個 | 一次資料 | https://raw.githubusercontent.com/pybotters/pybotters/main/README.md 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:59 と docs/DATA/probes/20260922_tools_1_run7.log:91 |
| `pybotters` | 星 | 463(fork 80、watchers 13) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:86(ungh.cc の stars / forks / watchers) |
| `pybotters` | コミット数 | 595(main) | 一次資料 | https://github.com/pybotters/pybotters 取得日 2026-09-22(リポジトリの見出しの Commits)/ docs/DATA/probes/20260922_tools_1_run7.log:146。API の端点 api.github.com/repos/pybotters/pybotters/commits?per_page=1 は 403 |
| `pybotters` | 保守者数 | GitHub の寄与者は 20 件の枠で 23 人。最多は MtkN1(426)。PyPI の info.author も info.maintainer も None | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:86 |
| `pybotters` | 週DL数 | last_day=215、last_week=1842、last_month=7020 | 一次資料 | https://pypistats.org/api/packages/pybotters/recent 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:86 |
| `pybotters` | 初回公開日 | 2021-04-12T16:10:21(0.1.0)。GitHub の createdAt は 2021-03-24T11:28:06Z。releases は 49 件 | 一次資料 | https://pypi.org/pypi/pybotters/json 取得日 2026-09-22(releases の最古 upload_time)/ https://ungh.cc/repos/pybotters/pybotters 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:86 |
| `pybotters` | 既知の脆弱性 | PyPI の vulnerabilities は長さ 0 | 一次資料 | https://pypi.org/pypi/pybotters/json 取得日 2026-09-22(vulnerabilities)/ docs/DATA/probes/20260922_tools_1_run7.log:15 |
| `pybotters` | 料金体系 | MIT の無償配布。README にも PyPI の頁にも料金・購読・席・従量の記述は無い。費用が発生しうるのは接続先の取引所の側だけ(取引手数料・API の利用条件)で、それは取引所の規約に従う | 一次資料 | https://raw.githubusercontent.com/pybotters/pybotters/main/README.md 取得日 2026-09-22 / https://raw.githubusercontent.com/pybotters/pybotters/main/LICENCE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:86 と docs/DATA/probes/20260922_tools_1_run7.log:91 |
| `pybotters` | 無料枠の上限 | 道具の側に上限は無い(鍵も登録も無しに導入と最小実行まで到達した)。上限が掛かるのは接続先の取引所の API の側 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:55 と docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 課金開始条件 | 道具の側には無い。実弾の発注をした瞬間に取引所の手数料が発生するが、それは道具の課金ではない。**鍵を渡さない限り private の経路は動かない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:61 と docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 隠れた依存 | 宣言上の依存は `aiohttp>=3.7` の 1 件のみ。ただし配布物の中に `pybotters/_static_dependencies/` として別の算法ライブラリ群(ecdsa / lark / parsimonious / sympy ほか)を同梱しており、**宣言に出ない読み込み対象が在る**。有料のデータ源・雲・LLM の鍵は要らない | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 |
| `pybotters` | 登録の要否 | public の経路(板・約定の購読、公開の REST)は不要。private の経路は取引所の API 鍵が要る(渡すもの: 取引所の口座と、そこで発行する鍵と秘密。README の逐語は `"bitflyer": ["YOUER_BITFLYER_API_KEY", "YOUER_BITFLYER_API_SECRET"]`)。**この調査では登録も鍵の発行もしていない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:91 |
| `pybotters` | 到達経路 | PyPI の index から `pip download --no-deps` と `pip install` の両方が通る。GitHub 側は `raw.githubusercontent.com` の `main` が 200 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:28 と docs/DATA/probes/20260922_tools_1_run7.log:55 と docs/DATA/probes/20260922_tools_1_run7.log:86 |
| `pybotters` | 導入可否 | 可。`/usr/bin/python3.11 -m venv` の隔離 venv に導入した。リポジトリの環境には入れていない | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:55(rc=0) |
| `pybotters` | install所要秒 | 3 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:55(install_time_s) |
| `pybotters` | 依存数 | 導入後の pip list は 12 パッケージ(pip と setuptools を含む)。wheel の METADATA の Requires-Dist は 1 個 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:55 |
| `pybotters` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:55(pip_check_rc=0) |
| `pybotters` | 最小実行の可否 | 可。**合成の板・約定・注文イベントだけで、板の再構成と注文の状態機械の 1 往復が通った。**外部通信も鍵も使っていない。ただし回避 1 を置かないと板が空のまま黙って回る | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 最小実行の中身 | `bitFlyerDataStore` を作り、(a) 回避 1 = `store._snapshots.add("FX_BTC_JPY")` を先に置く、(b) 合成の板(買い 3 段・売り 3 段)を投入、(c) 差分で最良買いを消す、(d) 合成の約定 1 件、(e) `child_order_events` の ORDER と EXECUTION を 1 件ずつ投入。結果は BEST_BID 9998000 / BEST_ASK 10001000 / SPREAD 3000 / EXEC_COUNT 1 / ORDERS_AFTER_ORDER 1 / ORDERS_AFTER_FILL 0 / POSITIONS に建玉 1 件 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 実行所要秒 | 0.277099(台本全体を外側で計った値)。店への 4 つの投入の内側だけを perf_counter で挟んだ値は TIME_S 0.000435 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | wheel展開 | pybotters-1.11.2-py3-none-any.whl を `pip download --no-deps` で取り(521973 bytes)、258 ファイルを列挙(うち .py が 244)。最上位は pybotters と pybotters-1.11.2.dist-info の 2 つ | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:28 と docs/DATA/probes/20260922_tools_1_run7.log:33 |
| `pybotters` | setup.py導入時実行 | wheel に setup.py は 0 件。生成器は hatchling 1.29.0、Root-Is-Purelib: true | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 |
| `pybotters` | 同梱バイナリ | 0 件(.so / .pyd / .dll / .dylib / .exe のいずれも無い) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 |
| `pybotters` | 外部送信 | 道具の側の遠隔測定は見当たらない。配布物の .py に現れる外部 host は取引所の API 文書の参照先と説明文の参照先で、**送信先は利用者が `base_url` と WS の URL で明示的に指定したところだけ**。署名つきで叩ける host は `auth.py` の 35 件と `ws.py` の 35 件に限定されている。最小実行では 1 件も通信していない(合成データのみ) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:61 と docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 自動発注機能 | **ある。**private の REST と WS に自動で署名を付けるのが中心の機能で、発注の端点は取引所の API をそのまま叩く。ただし**鍵を `pybotters.Client(apis=…)` に渡さない限り動かない**。paper や dry-run の模擬は道具の側に無い | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:61 と docs/DATA/probes/20260922_tools_1_run7.log:91 |
| `pybotters` | 宣伝詐欺の兆候 | 「必ず儲かる」・Telegram だけの配布・秘密鍵の要求・提携リンクは見当たらない。README は機能と対応取引所の表だけ。配布は PyPI と GitHub の両方で、PyPI の project_urls が GitHub を指している | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:91 |
| `pybotters` | 当方データ投入 | 取引所の WS の生文と同じ形の dict をそのまま投入できた(最小実行がそれ)。**当方の csv.gz の約定・清算をそのまま入れる経路は無く、WS の形に直す前処理が要る。**さらに記録した生文を流し込むだけでは回避 1 が要る(知見 3) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:67 と docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 時刻の扱い | 投入した時刻の文字列(`exec_date` / `event_date`)を変換せずそのまま保持する。UTC / ミリ秒への正規化は道具の側でしない | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 再現性 | 同じ台本を 2 回打って、計測の秒を除く出力が完全に一致した。乱数は使っていない | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:148 |
| `pybotters` | 規模の見積 | 店への 4 つの投入が 0.000435 秒。1 件あたりに比例すると置くと、456 日分の約定を 1 日 20 万件として 9,120 万件で 9,918 秒あたりの規模になる。**ティックの実データでは測っていない** | 推定 | docs/DATA/probes/20260922_tools_1_run7.log:72 からの外挿(件数に線形と仮定) |
| `pybotters` | 4軸1_道具 | 入れられる。`python3.11` の隔離 venv に 3 秒で入り、`pip check` も通り、合成データだけで最小実行まで到達した。依存が 1 件なので当方の環境との衝突が起きにくい | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:55 と docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 4軸2_情報 | **当方に無い国内の取引所の板・約定・private の経路が 5 社ぶん取れる**(GMO Coin / bitbank / Coincheck / OKJ / BitTrade)。当方の `src/bot/market_data/` は bitFlyer と Binance だけで、`scripts/` の GMO / bitbank は記録と研究であって執行が無い(`docs/DATA/probes/20260921_tools_absent.log` の E 節) | 一次資料 | https://raw.githubusercontent.com/pybotters/pybotters/main/README.md 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:61 と docs/DATA/probes/20260922_tools_1_run7.log:91 |
| `pybotters` | 4軸3_視点 | (a) 板の差分を店の側で適用し、中値を跨いだ気配を自動で削る / (b) 注文イベントから注文と建玉と残高を同時に導く状態機械を持つ / (c) 取引所ごとの署名の違いを 1 つの窓口に畳んでいる / (d) 待ち行列そのものは持たない(価格ごとの合計だけで、指値の先行注文は表さない)。**当方の `src/bot/research/board.py` は板の再構成を持つが、注文イベントから建玉を導く状態機械は持たない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:61 と docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 4軸4_向上 | 当方の記録器(`scripts/record_*`)は取引所ごとに書き分けている。この道具の店を使うと、板の差分の適用と注文の状態機械が取引所をまたいで 1 つの形になる。**ただし板の店は待ち行列を持たないので、`scripts/qa/maker_fill_ref.py` の FIFO の参照実装の代わりにはならない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:61 と docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 配布元の一致 | 一致する。PyPI の project_urls の Repository が `https://github.com/pybotters/pybotters` を指し、その `main` の LICENCE が MIT で PyPI の license_expression と合う | 一次資料 | https://pypi.org/pypi/pybotters/json 取得日 2026-09-22 / https://raw.githubusercontent.com/pybotters/pybotters/main/LICENCE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:86 |
| `pybotters` | 難読化 | 本体側には見当たらない。eval / exec / base64 / marshal に当たった 5 ファイルは**すべて同梱の `_static_dependencies/`**(ecdsa / lark / parsimonious / sympy)で、いずれも公開されている一般のライブラリの通常の実装 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 |
| `pybotters` | 外部URL取得 | 導入の段では起きない(setup.py が 0 件、生成器は hatchling)。実行の段で外へ行くのは、利用者が指定した取引所の端点だけ | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:72 |
| `pybotters` | 依存の一覧 | aiohttp>=3.7(これだけ)。導入後に入った 12 件は aiohappyeyeballs / aiohttp / aiosignal / attrs / frozenlist / idna / multidict / propcache / pybotters / typing_extensions / yarl と pip / setuptools | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:55 |
| `pybotters` | 保守者名の一貫性 | PyPI の info.author も info.maintainer も None。GitHub の LICENCE の著作権表示は MtkN1 で、寄与の最多も MtkN1(426)。**PyPI 側に名前が無いので、名前での照合は GitHub 側だけで成り立つ** | 一次資料 | https://pypi.org/pypi/pybotters/json 取得日 2026-09-22 / https://raw.githubusercontent.com/pybotters/pybotters/main/LICENCE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:86 |
| `OctoBot` | 版 | 2.1.1。導入した venv で `OctoBot --version` が返した値も 2.1.1 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:120 |
| `OctoBot` | 最終更新日 | PyPI の最新版の upload_time は 2026-03-29T15:25:05。GitHub の pushedAt は 2026-09-22T07:42:46Z で、**配布物のほうが半年ちかく古い** | 一次資料 | https://pypi.org/pypi/OctoBot/json 取得日 2026-09-22 / https://ungh.cc/repos/Drakkar-Software/OctoBot 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:139 |
| `OctoBot` | ライセンス | GPL-3.0。PyPI の info.license が 'GPL-3.0'、wheel の METADATA も `License: GPL-3.0`。GitHub の `master` の LICENSE は "GNU GENERAL PUBLIC LICENSE" "Version 3, 29 June 2007"、頁の表示は "GNU General Public License v3.0 or later"。**改変したものを配布するときに同じ条件での公開を求める** | 一次資料 | https://pypi.org/pypi/OctoBot/json 取得日 2026-09-22 / https://raw.githubusercontent.com/Drakkar-Software/OctoBot/master/LICENSE 取得日 2026-09-22 / https://github.com/Drakkar-Software/OctoBot 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:139 |
| `OctoBot` | 言語と動作環境 | Python。requires_python は `>=3.12`。**classifiers に Programming Language :: Python :: の行が 1 つも無い**ので、対応する版は requires_python からしか読めない。この環境の `/usr/bin/python3.12`(3.12.3)の隔離 venv で導入も起動も通った。既定の `python3` は 3.11.15 なので、既定のままでは入らない | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:13 と docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:101 と docs/DATA/probes/20260922_tools_1_run7.log:107 |
| `OctoBot` | 対応取引所 | **本体の配布物には取引所の接続が 1 つも入っていない。**接続は拡張(tentacles)の側にあり、外部の配布所から別に取る。必須の依存に `ccxt==4.5.44` が入るので窓口はそこ。GitHub の頁の説明の逐語は "...on Binance, Hyperliquid and 15+ exchanges..."。**国内の暗号資産取引所の名指しは頁にも配布物の最上位にも無い**(拡張の中身は今回展開していない) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:127 と docs/DATA/probes/20260922_tools_1_run7.log:139 |
| `OctoBot` | 星 | 6600(fork 1275、watchers 115) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:139(ungh.cc の stars / forks / watchers) |
| `OctoBot` | コミット数 | 5,954(master) | 一次資料 | https://github.com/Drakkar-Software/OctoBot 取得日 2026-09-22(リポジトリの見出しの Commits)/ docs/DATA/probes/20260922_tools_1_run7.log:139。API の端点 api.github.com/repos/Drakkar-Software/OctoBot/commits?per_page=1 は 403 |
| `OctoBot` | 保守者数 | GitHub の寄与者は 20 件の枠で 20 人。上位 2 人(GuillaumeDSM 1470、Herklos 988)で大半を占める。PyPI の info.author は組織名 'Drakkar-Software'、info.maintainer は None | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:139 |
| `OctoBot` | 週DL数 | last_day=36、last_week=129、last_month=2,157 | 一次資料 | https://pypistats.org/packages/octobot 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:139。API の端点 /api/packages/octobot/recent は 2 回とも 429 |
| `OctoBot` | 初回公開日 | 2019-01-16T22:57:27(0.2.4b1)。GitHub の createdAt は 2018-02-23T23:13:05Z。releases は 137 件 | 一次資料 | https://pypi.org/pypi/OctoBot/json 取得日 2026-09-22(releases の最古 upload_time)/ https://ungh.cc/repos/Drakkar-Software/OctoBot 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:139 |
| `OctoBot` | 既知の脆弱性 | PyPI の vulnerabilities は長さ 0 | 一次資料 | https://pypi.org/pypi/OctoBot/json 取得日 2026-09-22(vulnerabilities)/ docs/DATA/probes/20260922_tools_1_run7.log:15 |
| `OctoBot` | 料金体系 | 本体は GPL-3.0 の無償配布で、PyPI にも wheel にも料金の記述は無い。ただし配布物は運営者の雲のサービス(community / sync / market-making / webhook / feedback)の端点を定数として持ち、拡張の配布所も運営者の側にある。**有償の層があるかは、雲の側の料金の頁を見ていないので未確認** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:121 |
| `OctoBot` | 無料枠の上限 | **本体側に上限は無い**(鍵も登録も無しに導入・起動・拡張の導入まで到達した)。雲の側の無料枠は見ていない | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:101 と docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:127 |
| `OctoBot` | 課金開始条件 | 道具の側では確認できていない。外部の課金に入りうる経路は (a) 必須の依存に入る LLM の窓口の鍵、(b) 取引所の口座と鍵、(c) 運営者の雲のサービスの利用。**どれもこの調査では触れていない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:121 |
| `OctoBot` | 隠れた依存 | 必須の依存 77 件に、取引以外の外部連携が広く含まれる: `ccxt`(取引所の窓口)/ `openai`(LLM の窓口)/ `mcp`(エージェントの相互接続)/ `web3` と `eth-account`(分散台帳)/ `telethon` と `python-telegram-bot`(通信アプリ)/ `asyncpraw`(掲示板)/ `sentry-sdk`(誤りの送信)/ `supabase` と `aioboto3` と `clickhouse-connect` と `pyiceberg`(雲の記憶)/ `pyngrok`(外への穴あけ)。**選択ではなく必須。**さらに機能の大半は拡張の側にあり、外部の配布所から別に取る | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:127 |
| `OctoBot` | 登録の要否 | 導入・起動・拡張の導入には不要(鍵なしで到達した)。要るのは (a) 取引所の鍵(`--encrypter` がその暗号化の道具)/ (b) 運営者の community の識別子(`--identifier`)。**この調査では登録も鍵の発行もしていない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:127 |
| `OctoBot` | 到達経路 | PyPI の index から `pip download --no-deps` と `pip install` の両方が通る。拡張は `https://tentacles.octobot.online/officials/packages/full/base/<版>/any_platform.zip` から HTTP で取れる | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:28 と docs/DATA/probes/20260922_tools_1_run7.log:101 と docs/DATA/probes/20260922_tools_1_run7.log:121 と docs/DATA/probes/20260922_tools_1_run7.log:127 |
| `OctoBot` | 導入可否 | 可(**ただし 2 回目で**)。1 回目は空き容量の不足で `OSError` になり、`pip cache purge` で空きを戻して別の隔離 venv に `--no-cache-dir` で入れ直したら rc=0 で通った。リポジトリの環境には入れていない | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:96 と docs/DATA/probes/20260922_tools_1_run7.log:99 と docs/DATA/probes/20260922_tools_1_run7.log:101 |
| `OctoBot` | install所要秒 | 82(2 回目。1 回目は失敗)。拡張の導入はさらに 6 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:101 と docs/DATA/probes/20260922_tools_1_run7.log:127 |
| `OctoBot` | 依存数 | 導入後の pip list は 195 行(見出し 2 行を含むのでパッケージは 193 件)。wheel の METADATA の Requires-Dist は 77 個 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:101 |
| `OctoBot` | pip check | No broken requirements found. | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:101(pip_check_rc=0) |
| `OctoBot` | 最小実行の可否 | **未到達。**起動口(`--help` と `--version`)と拡張の導入までは通ったが、委任文 §5-4 が求める「成行と指値の 1 往復」には届いていない。**「この環境から不可」ではない。**試したこと: (a) 隔離導入 2 通り / (b) `OctoBot --help` と `--version` / (c) `OctoBot tentacles --install --all` / (d) `find octo_home -name '*.data'` = 一致 0 件 / (e) `octobot_backtesting.data` の公開名の列挙 = 書き出し器が公開名に無い | 未確認 | docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:120 と docs/DATA/probes/20260922_tools_1_run7.log:127 と docs/DATA/probes/20260922_tools_1_run7.log:130 |
| `OctoBot` | 最小実行の中身 | 到達したのはここまで: 隔離 venv への導入 → `OctoBot --help`(rc=0)→ `OctoBot --version`(rc=0、2.1.1)→ `OctoBot tentacles --install --all`(rc=0、22M)。**核の 1 往復は回していない。**次の手は生ログに書いた(合成の `.data` を `octobot_backtesting.data.database` を直に呼んで組み、`OctoBot -b -bf <file> -nw -nl --simulate` を打つ) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:120 と docs/DATA/probes/20260922_tools_1_run7.log:127 と docs/DATA/probes/20260922_tools_1_run7.log:130 |
| `OctoBot` | 実行所要秒 | `--help` が 3.184004、`--version` が 3.278315、`tentacles --install --all` が 6。**模擬の実行時間は測っていない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:120 と docs/DATA/probes/20260922_tools_1_run7.log:127 |
| `OctoBot` | wheel展開 | octobot-2.1.1-py3-none-any.whl を `pip download --no-deps` で取り(10721541 bytes)、1015 ファイルを列挙(うち .py が 988)。最上位は 14 個(async_channel / octobot / octobot-2.1.1.dist-info / octobot_agents / octobot_backtesting / octobot_commons / octobot_evaluators / octobot_flow / octobot_node / octobot_services / octobot_sync / octobot_tentacles_manager / octobot_trading / trading_backend) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:28 と docs/DATA/probes/20260922_tools_1_run7.log:33 |
| `OctoBot` | setup.py導入時実行 | wheel に setup.py は 0 件。生成器は setuptools 80.9.0、Root-Is-Purelib: true。**ただし導入の途中で 3 件がソースから組み立てられた**(coingecko-openapi-client / pgpy / pyaes)ので、依存の側では導入時にコードが走っている | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:101 |
| `OctoBot` | 同梱バイナリ | 本体の wheel には 0 件(.so / .pyd / .dll / .dylib / .exe のいずれも無い)。依存の側には在る(`pyarrow` `coincurve` `ckzg` `psycopg-binary` `gevent` など) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:101 |
| `OctoBot` | 外部送信 | **2 系統ある。**(a) 誤りの送信 = `sentry_tracker.py` が `octobot.constants.ERROR_TRACKER_DSN` を見て、無ければ初期化の入口で return する。その定数は `os.getenv("ERROR_TRACKER_DSN")` なので**既定は無効**。(b) 稼働の測定 = `octobot_commons/constants.py` の `METRICS_URL = os.getenv("METRICS_OCTOBOT_ONLINE_URL", "https://metrics.octobot.online/")` で、登録・uptime・community の 3 つの経路がある。止め方は利用者設定の `metrics` を切るか、この環境変数を差し替える。**3 つとも実地には確かめていない**(本体を稼働させていないため)。配布物の .py に現れる外部 host には運営者の雲の端点が 9 個含まれる | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:47 |
| `OctoBot` | 自動発注機能 | **ある。**`--simulate` が「模擬の取引者だけで起動する」旗として在ることが、既定では実弾側も動きうることを示す。`--encrypter` は取引所の鍵を暗号化して設定に入れる道具。実弾の接続そのものは拡張の側 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:107 |
| `OctoBot` | 宣伝詐欺の兆候 | 「必ず儲かる」・Telegram だけの配布・秘密鍵の要求は見当たらない。PyPI と GitHub の所在が一致し、LICENSE も一致する。**留意点として記録する**: 必須の依存に通信アプリ・掲示板・分散台帳・雲の記憶・外への穴あけの窓口が入り、配布物が運営者の雲の端点を多数持つ。これは詐欺の兆候ではなく、**外へ出る経路の多さ**として書く | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:47 |
| `OctoBot` | 当方データ投入 | 未確認。配布物にも拡張にも模擬用の見本データが 1 件も無く(`find` の一致 0 件)、当方の csv.gz を渡す形を確かめられなかった。試したこと: `find octo_home -name '*.data'` / `octobot_backtesting.data` と `octobot_backtesting.constants` の公開名の列挙 | 未確認 | docs/DATA/probes/20260922_tools_1_run7.log:130 |
| `OctoBot` | 時刻の扱い | 未確認。試したこと: `OctoBot --help` の全文(時刻・時間帯の旗は無い)/ `octobot_backtesting.constants` の公開名の列挙(`BACKTESTING_DATA_FILE_TIME_READ_FORMAT` などの名前は在るが値を読んでいない)。模擬を回していないので実際の扱いは見ていない | 未確認 | docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:130 |
| `OctoBot` | 再現性 | 未確認。乱数の種の旗は `--help` の全文に無い。模擬を 1 度も回していないので、同じ入力で同じ結果になるかを測っていない | 未確認 | docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:130 |
| `OctoBot` | 規模の見積 | 未確認。模擬を回していないので外挿の足場が無い。`--help` に "the watcher is limiting backtesting time to 30min" という旗(`-ebt`)が在ることから、既定では長時間の実行が想定されていると読めるだけ | 未確認 | docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:130 |
| `OctoBot` | 4軸1_道具 | 入れられる(空き容量を戻したあと)。`python3.12` の隔離 venv に 82 秒で入り、`pip check` も通り、拡張まで入った。**ただし 193 件の依存が入るので、当方の環境に混ぜる形では使えない。**核の 1 往復は未到達 | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:101 と docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:127 と docs/DATA/probes/20260922_tools_1_run7.log:130 |
| `OctoBot` | 4軸2_情報 | 必須の依存に、当方の道具立てに対応物が無い窓口が並ぶ: 掲示板の読み取り(`asyncpraw`)/ 検索の関心度(`simplifiedpytrends`)/ 文の感情の採点(`vaderSentiment`)/ 暗号資産の相場情報(`coingecko-openapi-client`)/ 分散台帳(`web3`)/ 列指向の記憶(`pyiceberg` `clickhouse-connect`)。**鍵が無いので中身は見ていない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 |
| `OctoBot` | 4軸3_視点 | (a) 戦略を「評価器 → 戦略 → 取引の型」の 3 段に分け、それぞれを差し替え式の拡張にしている / (b) 拡張を外部の配布所から版ごとに取る仕組みを持つ / (c) 旗 1 つで模擬の取引者だけに落とせる / (d) 戦略の最適化器が時間足・評価器・リスクを総当たりする仕組みを本体に持つ / (e) 取引の自動化を「条件 → 動作」の対で書く層を持つ(拡張の最上位に Automation が在る)。**当方の `src/bot/strategy/` は差し替えの口が composite のモジュール枠だけで、(b)(d)(e) に対応物が無い** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:107 と docs/DATA/probes/20260922_tools_1_run7.log:127 |
| `OctoBot` | 4軸4_向上 | `-o STRATEGY_OPTIMIZER` は「時間足・評価器・リスクを変えて模擬を総当たりする」道具で、当方の `src/bot/backtest/walk_forward.py` には無い軸の探索をする。**ただし総当たりは当方の研究の規律(多重性の算入)と正面からぶつかるので、使うなら周回数を多重性に入れる必要がある** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:107 |
| `OctoBot` | 配布元の一致 | 一致する。PyPI の info.home_page と project_urls の Homepage がどちらも `https://github.com/Drakkar-Software/OctoBot` を指し、その `master` の LICENSE が GPL v3 で PyPI の info.license と合う | 一次資料 | https://pypi.org/pypi/OctoBot/json 取得日 2026-09-22 / https://raw.githubusercontent.com/Drakkar-Software/OctoBot/master/LICENSE 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:139 |
| `OctoBot` | 難読化 | 見当たらない。配布物は .py のみで同梱バイナリは 0 件。eval / exec / base64 / marshal に当たった 8 ファイルは、名前から読むかぎり暗号化・監視・依存の管理・戦略の記述の実装で、**中身は 1 行ずつ読んでいない** | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 |
| `OctoBot` | 外部URL取得 | **導入の段では起きない**(本体の wheel に setup.py が 0 件)。ただし依存の 3 件がソースから組み立てられるので、そこでは PyPI から取ったソースの中の処理が走る。実行の段では拡張の取得が `tentacles.octobot.online` へ行き、稼働の測定が `metrics.octobot.online` へ行きうる | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 と docs/DATA/probes/20260922_tools_1_run7.log:101 と docs/DATA/probes/20260922_tools_1_run7.log:121 と docs/DATA/probes/20260922_tools_1_run7.log:127 |
| `OctoBot` | 依存の一覧 | 必須 77 件: Flask-WTF / OctoBot-Tulipy / WTForms / aioboto3 / aiodns / aiofiles / aiohttp / aiosqlite / asyncpraw / cachetools / ccxt / certifi / clickhouse-connect / coingecko-openapi-client / colorlog / cryptography / cython / dbos / fastapi[standard] / flask-caching / flask-compress / flask-cors / flask-login / flask-socketio / flask / gevent-websocket / gevent / gmqtt / jinja2 / jsonschema / mcp / mock / numpy / openai / packaging / passlib[bcrypt] / pgpy / postgrest / protobuf / psutil / pyarrow / pydantic / pyiceberg / pyngrok / python-dotenv / python-multipart / python-telegram-bot / pyyaml / requests / sentry-sdk / setuptools / simplifiedpytrends / sortedcontainers / standard-imghdr / starfish-sdk / starfish-server / supabase / supabase_auth / telethon / tinydb / urllib3 / vaderSentiment / web3 / websockets / werkzeug(同じ名前が版の指定違いで重複して数えられている行がある) | 実測 | docs/DATA/probes/20260922_tools_1_run7.log:33 |
| `OctoBot` | 保守者名の一貫性 | PyPI の info.author は組織名 'Drakkar-Software'、info.maintainer は None。GitHub の所有者も Drakkar-Software で**組織名は一致する**。寄与の上位は GuillaumeDSM と Herklos の個人名だが、PyPI 側に個人名は出てこない | 一次資料 | https://pypi.org/pypi/OctoBot/json 取得日 2026-09-22 / https://ungh.cc/repos/Drakkar-Software/OctoBot 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:15 と docs/DATA/probes/20260922_tools_1_run7.log:139 |

#### 取り直しの結果(6 回目のリードの検収が渡したもの)

| 道具 | 測り直したこと | 前の節の値 | この回の値 | 印 | 根拠 |
|---|---|---|---|---|---|
| `Ziplime` | README の対応 LLM(取り直し) | 写していない(委任文 §10 の「モデル名を書かない」に従った) | **README に個別の製品名の一覧は無い。**書いてあるのは中継業者 1 社だけで、逐語は "Set your OpenRouter API key (free at https://openrouter.ai)" と "export OPENROUTER_API_KEY=your_key_here"。README の本文には "...every tool forces you to copy-paste between ChatGPT and your terminal..." という言及も在る。README は "> Ziplime is not a wrapper around an LLM." とも書く | 一次資料 | https://raw.githubusercontent.com/Limex-com/ziplime/master/README.md 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:2 |
| `Ziplime` | 実装側の既定の指定(取り直し) | 未確認 | `ai_assistant/requirements.txt` の逐語は "# LLM API (OpenAI SDK works with OpenRouter's compatible API)" と `openai>=1.30.0`。`ai_assistant/agent.py` の 40 行の逐語は `def __init__(self, api_key: str, model: str = "x-ai/grok-4.1-fast"):`、44 行の逐語は `base_url="https://openrouter.ai/api/v1"`。**つまり対応するのは OpenRouter 経由で OpenAI 互換の API を話すもの全部で、既定の指定が 1 つだけ置かれている** | 一次資料 | https://raw.githubusercontent.com/Limex-com/ziplime/master/ai_assistant/agent.py 取得日 2026-09-22 / https://raw.githubusercontent.com/Limex-com/ziplime/master/ai_assistant/requirements.txt 取得日 2026-09-22 / docs/DATA/probes/20260922_tools_1_run7.log:8 |

### 予算

| 項目 | 値 |
|---|---|
| 上限 | 1 回 5 万トークン・20 分 |
| 実績 | 上限に達したため中断した。深掘りは `pybotters` と `OctoBot` の 2 件。取り直しは `Ziplime` の 2 件とも埋まった |
| 未完了 | 候補の一覧の 3・7・8・9・13・14・15・16・17 番はこの回で着手していない。`OctoBot` は最小実行だけ未到達。区分 1 は**未完了**(委任文 §2 の条件 = 残りの候補が空で、新しい検索計画が新しい候補を 1 件も出さない、を満たしていない) |

### 原文に無い判断(黙って決めずに書き出す)

1. **`OctoBot` の 1 回目の導入の失敗の原因が環境側だったので、`pip cache purge` を打って空き容量を戻した。**委任文は「手段を替えて続ける」と書いているが、**この環境の共有の記憶を消す**ことまでは書いていない。消したのは pip の取得物の控えだけで、リポジトリにも `data/` にも触れていない。それでも、この種の後始末をしてよいかはリードが決めること。
2. **`pybotters` の最小実行で回避を 1 つ置いた**(`store._snapshots.add("FX_BTC_JPY")`)。置かないと板が空のまま静かに回り、失敗にも見えない。回避しなかったときの誤りも生ログに残した(試行 1 と試行 2)。
3. **`OctoBot` の最小実行を「未確認」で止め、合成の `.data` を自分で組む手には進まなかった。**予算の上限に達したためで、**「この環境から不可」とは書いていない。**次の手は生ログに 1 行ずつ書いた。ここで止めてよかったかはリードが決めること。
4. **`OctoBot` の拡張(tentacles)を外部の配布所から取った。**大きさを測ってから取った(委任文 §6-6 の「数百 MB 以上の一括ダウンロードをしない」に当たらない)が、**外部の配布所からコードを取って動かした**ことには変わりない。導入前の検査は本体の wheel に対して行っており、拡張の中身は展開して調べていない。
5. **候補の一覧に 25 番として「限界」の行を足した。**`OctoBot` の必須の依存に入る取引以外の窓口は、それ自体が道具の候補になりうるが、この回では立てていない。候補から黙って落とさないために、落としていないことを明記した。

### 受け入れ検査で残した行(自分で閉じなかったもの)

**1 件。**自分で閉じていない。判定はリードにお願いする。

1. **K6(未実施と実測の同居)が、`OctoBot` の `料金体系` の行を拾った。**
   その行の「未確認」は、**運営者の雲のサービスの料金の頁を見ていない**ことに掛かっている。
   同じ行に配布物の形式の名前(`.whl`)が「PyPI にも…にも料金の記述は無い」という文脈で出てくるため、
   検査がその語と「未確認」を同じ 1 件として結び付けた。
   検査の実装(`scripts/check_scan_report.py` の `check_contradiction`)は、
   **行に特定の 2 語のどちらかが在るかだけを見て、その語と「未確認」が同じものを指しているかは見ていない。**
   直すには、その行から配布物の形式の名前を消すことになるが、それは**検査を通すために一次資料の記述を削る**ことになるので、
   書き換えずに残した(5 回目のリードの検収 §5-2「検査を満たすために書く行が増えること自体が型」と同じ理由)。
   **この節と下の貼り付けにも同じ語が出るので、検査の出す行番号の一覧にはそれらも入る。**

## 受け入れ検査の出力

リードが受領後に打ち直した出力(生ログ 5 本)。調査班が残した K6 の 1 件は当たりで、
検査を表の行の中だけを見る形に直した。判定は `docs/AUDITOR/VERDICTS/2026-09-22_tools_scan_cat1_run7.md`。

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
---- 検査対象の合計 0 件(K12 を除く。貼り付けはこの数で照合する)
---- 合計 1 件
```

### `STRATEGY_IDEAS.md` / `DATA.md` 向けの一行候補(提案。マージしない)

- `DATA.md` 向け: 「`pybotters` の `bitFlyerDataStore` は、記録した WS の生文をそのまま流し込むと板が空のまま静かに回る。`_snapshots` に銘柄を先に登録しないと、`lightning_board_` の更新が警告も例外も無しに全部捨てられる。」
- `DATA.md` 向け: 「国内の暗号資産取引所の板・約定・private の経路は `pybotters` が 6 社ぶん持つ(bitFlyer・GMO Coin・bitbank・Coincheck・OKJ・BitTrade)。当方は bitFlyer だけ。」
- `STRATEGY_IDEAS.md` 向け: 「板の差分の適用で中値を跨いだ気配を削る扱いが、当方の板の再構成と `pybotters` で違う。同じ生文から作った板がどれだけずれるかを測り、逆選択の推定への影響を見る。」
