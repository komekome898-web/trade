# 委任の検めの試験のまとめ直し(L-794)

オーナーの逐語(L-794): 「**試験多すぎません？重複していたり過剰すぎたりしている内容をまとめて少なくする方法はありませんか？**」

## 数(打ったコマンドと出力)

| | 試験の関数 | 確かめる場面 | 数え方 |
|---|---|---|---|
| 前(コミット 971f5385) | 57 | 121(pytest の件数) | `git show 971f5385:tests/delegation/test_spec.py \| grep -c '^def test_'` → 57 |
| 後 | 11 | 表の行 94 + 18 + 11 = 123 と、表の外の確かめ | `grep -c '^def test_' tests/delegation/test_spec.py` → 11、`len(FORM_CASES), len(PM_CASES), len(REPORT_CASES)` → 94 18 11 |

- 減らしたのは関数の数(57 → 11)。確かめる場面は減らしていない(落とした場面は無い)。1 つの検めの場面を 1 つの表で回し、外れた場面を全部名前で出す形にした。
- 前の 121 は pytest の件数(1 つの関数の中で複数の場面を確かめるものは 1 件)、後の 123 は表の行の数で、数え方が違うので差をそのまま比べない。足した場面は、事前の批評 3 回目の指摘の 6 つ(読みの列の囮・「L-100 結果」の行の囮・点で始まるディレクトリと拡張子の無いファイル(既定の委任文に入れた)・ディレクトリ・名前付きパイプ・「落ちなかった」の行)。
- 本当に重なっていたもの(1 つにまとめた): `test_failure_removes_old_stamp` と `test_valid_passes_and_writes_stamp` / `test_print_hash_is_bare_64_hex_and_skips_checks` と `test_tool_hash_matches_literal` / `test_report_ok` と `test_report_param_test_name_ok` / `test_seal_names_in_fixed_section_do_not_fail` と既定の委任文の合格(既定の委任文の決まった制約の節に封印の名前がある)。
- 変えた場面: 引用の 1 字違いを「すぐに → すぐ」(頭からの一部なので含まれてしまう)から、真ん中の 1 字を変える形にした(3 回目の指摘)。

## 前 → 後

| 前の関数 | 後の関数 | 後の場面の名前 |
|---|---|---|
| test_valid_passes_and_writes_stamp・test_failure_removes_old_stamp | test_valid_passes_writes_stamp_and_failure_removes_it | — |
| test_input_error_exit_2_and_removes_stamp・test_all_failures_listed_together | test_input_errors_exit_2_and_all_failures_listed | — |
| test_print_hash_is_bare_64_hex_and_skips_checks・test_hash_rule_literal・test_tool_hash_matches_literal | test_hash_rule_and_print_hash | HASH_CASES 2 行 |
| test_kind_line_within_first_5・test_kind_line_bad | test_form_checks | 種類 … 5 行 |
| test_missing_heading | test_form_checks | 見出し … 11 行 |
| test_read_kind_needs_source_rule_not_make_sections・test_critic_kind_core_only | test_other_kinds | — |
| test_quote_whitespace_normalized_tab_and_fullwidth | test_valid_passes_…(既定の委任文が通る) | — |
| test_quote_mismatch・test_quote_reverse_direction_and_adjacent・test_unnumbered_quote_in_purpose_fails・test_unnumbered_quote_outside_purpose_ok | test_form_checks | 引用 … 9 行(囮 2 行を足した) |
| test_fact_cell・test_fact_cell_backtick_pipe_not_a_separator・test_fact_required_rows | test_form_checks | 事実 … 20 行(ディレクトリ・名前付きパイプを足した) |
| test_seal_path_fails_without_opening・test_seal_path_absolute_and_outside_root・test_seal_names_in_fixed_section_do_not_fail | test_form_checks・test_valid_passes_… | 封印 … 5 行・根の外 |
| test_decide_rows | test_form_checks | 決め … 14 行 |
| test_scene_row_missing・test_scene_cell_bad・test_scene_name_one_char_changed・test_scene_rows_out_of_order_fail・test_scene_u_reference_boundary | test_form_checks | 場面 … 19 行 |
| test_u_duplicate_fails_gap_ok・test_no_u_definitions_fails・test_h_none_line_ok_and_missing_fails | test_form_checks | U・H … 5 行 |
| test_fixed_one_char_changed_fails・test_fixed_line_removed_or_added_fails・test_fixed_trailing_space_and_blank_lines_ok | test_form_checks | 制約 … 4 行 |
| test_end_and_limit_words | test_form_checks | 上限の語が無い |
| test_premortem_missing_fails・test_premortem_hash_mismatch_after_body_edit・test_adding_midway_decision_keeps_premortem_valid・test_premortem_response_values・test_premortem_last_finding_at_end_of_file・test_second_round_is_last_and_cannot_say_fixed・test_next_version_response_needs_after_change_section・test_last_record_is_highest_number | test_premortem_checks | PM_CASES 18 行 |
| test_require_approval | test_require_approval_and_stamp_flag(印の approved を足した) | — |
| test_reads_delegation_once | test_reads_delegation_once(`^READS 1$` の行で見る) | — |
| test_report_ok・test_report_param_test_name_ok・test_report_mutation_table_bad・test_report_two_ids_in_one_cell・test_report_questions_need_midway_decisions・test_report_questions_section_required | test_report_checks | REPORT_CASES 11 行(「落ちなかった」を足した) |
| test_report_rechecks_delegation_not_stamp・test_report_forged_stamp_does_not_matter・test_report_does_not_write_stamp・test_report_input_error_exit_2 | test_report_stamp_and_delegation_recheck | — |
| test_report_read_kind_source_column | test_report_read_kind | — |
