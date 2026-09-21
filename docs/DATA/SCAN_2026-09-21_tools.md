# SCAN 2026-09-21 — トレードに使えるあらゆるツール

委任文: `docs/DATA/delegations/20260921_tools_survey_prompt.md`(指紋 `20260921_tools_survey_prompt.md@840bf99ca5b0`)。
オーナー逐語 L-377〜L-380(委任文 §0 に引用あり)。判定(使える/使えない/不要/今の環境以下/採用)は書かない。

---

## 区分1: バックテスト・シミュレーション — 2026-09-21(1回目の実行。**未完了**。監査 1〜10 回目(指摘 15・8・7・5・4・4・2・5・4・1 件。回数と件数は `docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md` の「n 回目」節と「> k. [」の行を機械で数えた値)を受けてリードが直した版 = v11。版ごとの処置は `docs/AUDITOR/VERDICTS/2026-09-21_tools_scan_cat1.md`。生ログに無かった WebFetch / WebSearch 24 手はリードが機械抽出で補った = 生ログ W 節、リードの取り直しは L 節)

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

**危険**: 供給網: PyPI配布元とGitHubのProject-URLが一致(実測)。wheelの中身に導入時の外部通信・難読化コードは確認されず(実測、展開して確認)。既知の脆弱性: 未確認(未実施)。外部送信: テレメトリの記載は一次資料に見当たらない(未確認、無効化方法の記録は無し)。自動発注・署名機能: バックテスト専用ライブラリであり、鍵を要する送信機能はライブラリ自体には無い(一次資料の機能一覧に発注APIの記載なし、ライブ接続はBinance/Bybit限定と明記)。宣伝・詐欺の兆候: 無し(根拠: W-16 の X 検索に hftbacktest への言及が 8 URL、うち 2 件をリードが x_fetch で取得 = 生ログ X3。どちらもリポジトリの説明文の紹介で、宣伝・詐欺の兆候なし。**使用報告は未取得**。下の「X の投稿」表に 2 行)。

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
| https://x.com/ML_deep/status/1917632698077831526 | ML_deep | 2025-04-30T17:30:37Z | 「vectorbt 開発も盛んで有償バージョンはパフォーマンスも改善されてるっぽい。一方でサンプルコードが2度付評価みたいなことしてて厳しさある…。無論、モジュールの使い方の例なのだろうけど、二度漬けしまくりパラメータなんてトレードで使ったら即あの世行きだぞ…。https://vectorbt.pro/#why-vectorbt-pro」 | 7/0/0/2122 | 使用報告(vectorbtの有償版言及+サンプルコードの罠への注意喚起) |
| https://x.com/tommy_love123/status/1972317745900585328 | tommy_love123 | 2025-09-28T15:09:29Z | 「【市場が55%下落する中で利益299%？あるYouTube動画が明かした驚異の取引戦略、その核心とは】 freqtrade関連の動画から拾ってきたのですが、スーパートレンド (Supertrend)＋MACD+RSIの組み合わせでDOT（ポルカドット）の無期限先物において、1年間で299%の総利益を達成やり方みたいです。 これがホントであるか、DOT以外でも通用するようなトレード戦略であるかどうかfreqtradeで確認したいと思います。 動画 https://youtu.be/71EA1u4K_Zk?si=aQ_qMEonSE_Urgtb レポート https://docs.google.com/document/d/1mTL48uHM2KqBbxiU1_VjDdrtN32h6Ixbq5fMQEj1r_o/edit?usp=sharing」 | 46/1/0/5166 | 他者の主張の転載(299% は動画の主張、投稿者も未確認。リードが x_fetch で取得 = 生ログ X2) |
| https://x.com/tommy_love123/status/1971429111492227297 | tommy_love123 | 2025-09-26T04:18:22Z | 「【AIエージェント：Codex AI+ｆreqtrade】 もう、とんでもない世界が実現している。 OpenAIのCodexの自律性の能力が向上したので、期待値（リターン、利益率）を上げるためのトレード戦略を自力で考え、それをコード化し、freqtradeコマンドを使って特定の取引所のAPIを叩き、オンライントレードを実施している。 だれが、この世界を想像できただろうか？」(引用元 同著者「freqtrade＋codex aiで自動的にバックテストまでやってくれます。怖いぐらいですね。 自然言語で命令し、ユーザの望みのトレード戦略のロジックまで構築できる。」) | 325/32/1/68290 | 使用報告(Codex + freqtrade で発注まで。区分 6 にも関係。リードが x_fetch で取得 = 生ログ X2) |
| https://x.com/SystematicPeter/status/2024507028820152381 | SystematicPeter | 2026-02-19T15:31:03Z | 「I'm seriously considering moving from my home-made scripts to a more universal framework for backtesting + live trading (especially for intraday). Tested NautilusTrader today and it looks very interesting. Why it caught my attention: - Open source - Event-driven Python API, Rust core (fast) - Biggest win: same strategy codepath for backtest and live (no "version 2" rewrite) - Because it's Python, Claude Code can actually help you ship strategies without coding. I ported my intraday volatility breakout strategy in minutes. Anyone here running NautilusTrader live? What's your experience with brokers/data/execution - any gotchas?」 | 161/7/19/14674 | 使用報告(NautilusTraderへの移行検討・実際にポートした報告) |

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

