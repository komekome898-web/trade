# 委任文: 委任文の検めと報告の受け取りの検めの道具を作る

種類: 作る

3 版目。受け入れを、リードが書いた実行できる試験 `tests/delegation/test_spec.py` に変えた版(1・2 版目は散文の受け入れで、事前の批評 2 回で指摘が 40 件 → 33 件と収束しなかった。記録は `DELEGATION_checker_premortem1.md`・`DELEGATION_checker_premortem2.md`)。受け入れの形を変えたので、事前の批評の回の数え直しをする(`PROPOSAL.md` §2 ②)。この版への事前の批評は `DELEGATION_checker_premortem3.md`。検める道具がまだ無いので、形の検め(①)はリードが手で行った(末尾)。

## 着手前の表

作業者は、着手の前に「やろうとすること × オーナーの原文の該当語(逐語)」の 2 列の表を出す(CLAUDE.md §0.1 のまま)。この委任文は、検めの後にオーナーの承認を受けてから渡す(L-793)。承認の逐語は末尾の `## オーナーの承認` にあり、委任文の中身はその承認に含まれるので、右の列には承認の逐語と、委任文の該当の文(節の名前つき)を書いてよい。委任文のどこにも書かれていないことをする行は右が空になり、その行は着手せず「問いとして返したこと」に書く。

## 目的(オーナーの逐語)

- L-791「**根本的な委任の出し方の改善案を考えてください。**」
- L-791「**アドバイザーと相談して「測定に限らず全ての委任において、委任のミスでやり直しが発生しない委任文の書き方と仕組み」ができるまでやってください。**」
- L-793「**委任文の検査が通ったのち、私に委任してよいか聞き、私の承認が得られてから委任すれば右の列は私の承認済のものになるでしょ。**」
- リードの設計(オーナーの逐語ではない): `docs/DISCUSSIONS/2026-10-07_delegation_redesign/PROPOSAL.md` の §2 ①・③・③'・④。この委任で作るのは、①(委任文の形の検め)・③の印・③'の承認の検め・④(報告の受け取りの検め)の道具。門(フック)はオーナーの許可が要るので、この委任の外。

## 作るもの

1. `scripts/delegation/check_delegation.py`
2. `scripts/delegation/check_report.py`
3. 必要なら `scripts/delegation/` の中の共通の部品のファイル(作業者が決めてよい)

決まりの正本は試験 `tests/delegation/test_spec.py`(リードが書いた)。口・終了コード・印の中身・事前の批評の sha256 の決まり・各検めの通る形と落ちる形は、全部その試験に書いてある。**試験は変えない。**試験どうし、または試験とこの委任文が食い違う・試験だけでは決まらない、と気づいたら、そこで止めて問いとして返す(それに依らない部分は続ける)。

試験に書ききれない決まり(下だけ):
- 委任文は `Path.read_bytes()` で 1 回だけ読み、そのバイトから sha256 と全部の検めを行う(試験 `test_reads_delegation_once` は `builtins.open`・`Path.read_bytes`・`Path.read_text` での読み込みを数える。ほかの読み方を使わない)。
- 開くのは、委任文・報告・事前の批評の記録・OWNER_LOG・FIXED_CONSTRAINTS・BREAK_SCENES・読んだ事実の確かめの欄の `パス:行` のパス・変異の表の試験のファイルだけ。封印の置き場の下かどうかは、開く・`exists`・`stat` などファイルに触れる前に、`--root` から解いて畳んだパスを小文字にして比べる。根の外に出るパスは失敗にする。
- 外の呼び出し(jev ほか)はしない。Python の標準ライブラリだけ。
- 既定のパス(`--owner-log`・`--fixed`・`--scenes`・`--root`)は、道具のファイルの置き場から 2 つ上をリポジトリの根として解く。
- どんな入力でも、捕まえない例外で終わらない(標準エラーに Traceback を出さない)。入力の誤りは終了コード 2。

## 読んだ事実

| # | 事実 | 確かめ |
|---|---|---|
| データ | この委任は市場のデータを使わない | この委任には無い(市場のデータを読まない道具のため) |
| 既存の決まり | 受け入れの正本の試験(リードが書いた。今は道具が無いので全部飛ばしになる) | `PYTHONPATH=src python -m pytest tests/delegation/test_spec.py` → 121 skipped |
| 既存の決まり | 使い回せるのは `owner_rows` だけ。番号の式は `L-\d{3}` で、L-499a・L-D01 の形を拾わない | `scripts/check_bt_delegation.py:128-134` |
| 既存の決まり | `check()` はバックテストの委任に限った検めを含み、引用を空白をそろえずに比べる(使わない) | `scripts/check_bt_delegation.py:143-148` |
| 既存の決まり | jev を外す理由: plan は委任文が名指したファイルを開いて行数を数え、呼ぶたびに `data/jev/delegate/` に書き、今は 402 で届かない | `scripts/jev_delegate.py:105-119`・`scripts/jev_delegate.py:493-494` |
| 既存の決まり | 決まった制約の塊(1 行目は注釈、2 行目が見出し、3〜7 行目が 5 項目) | `.claude/skills/delegated-study/FIXED_CONSTRAINTS.md:1-7` |
| 既存の決まり | 壊す場面の名前の正本(6〜17 行目が 12 の場面) | `cat -n .claude/skills/delegated-study/BREAK_SCENES.md` → 6 行目「- 封印の境: …」〜17 行目「- 並行の変更: …」 |
| 列の意味 | OWNER_LOG の行は `| L-NNN | 日付 | 種類 | 「**逐語**」 | 読み |` の形。逐語の中に「•」とタブが入ることがある | `docs/OWNER_LOG.md:844` |
| 列の意味 | OWNER_LOG には 3 桁でない番号の行が 19 行、同じ番号の行が 2 つある番号(L-277)がある | `grep "^| L-" docs/OWNER_LOG.md \| grep -v "^| L-[0-9][0-9][0-9] " \| wc -l` → 19 |
| 列の意味 | この環境では作業者も root で、ファイルの権限を外しても読める(読めない入力はディレクトリか UTF-8 でないバイトで作る) | `id -u` → 0(事前の批評 2 回目の確かめ) |

## 決めてよいこと・決めてはいけないこと

| 選び | 決め |
|---|---|
| 出力の置き場 | 道具は `scripts/delegation/`。印は委任文と同じ置き場で、git に入れる。試験は `tests/delegation/test_spec.py`(リードのもの、変えない)。作業者が足したい試験は `tests/delegation/test_extra.py` に置いてよい |
| 分母・数え方 | この委任には無い(数を出す道具ではない) |
| 比べの方法 | 試験 `tests/delegation/test_spec.py` のとおり |
| 確かめ方 | 試験 `tests/delegation/test_spec.py` が、飛ばし 0 で全部通る |
| 依存 | Python の標準ライブラリだけ。`owner_rows` は写しても import してもよい(作業者が決めてよい) |
| 絞り方・選び方 | 試験 `tests/delegation/test_spec.py` のとおり。試験で決まらない拾い方は、作業者が決めてよい(決めたことを報告に書く) |
| 単位・通貨のそろえ方 | この委任には無い(数を扱わない) |
| 失敗の文の言い回し | 作業者が決めてよい(日本語。試験が求める語を含む) |

## 変えないもの

- H1: 既存の道具 `scripts/jev_delegate.py`・`scripts/jev_report_intake.py`・`scripts/check_bt_delegation.py` と、試験 `tests/delegation/test_spec.py` を変えない。確かめ: `git diff --stat` にこの 4 本が出ない。
- H2: 既存の試験が通る。確かめ: `PYTHONPATH=src python -m pytest tests/test_jev_delegate.py tests/test_jev_report_intake.py tests/test_check_bt_delegation.py` が全部 passed。
- H3: 試験・道具は `docs/` と `.claude/` を書き換えない。確かめ: 試験の前後で `git status --short docs .claude` が同じ。

## 壊す場面

| 場面 | 書いたこと |
|---|---|
| 封印の境 | U6 |
| 日・足・期間の境 | U5(行の番号がファイルの行の数ちょうど・1 多い)・U12(途中の決めが最後の節・最後に改行が無いときの sha256) |
| 等号 | U2(種類の行が 5 行目と 6 行目)・U5(理由がちょうど 1 字)・U9(U1 と U10 を取り違えない)・U15 |
| 欠け | U1・U3・U5・U7・U8・U9・U12・U15(節・行・欄・記録・印・入力が無い) |
| 参照の値が無い | U4(OWNER_LOG に番号の行が無い)・U5(確かめのパスが無い)・U15(試験の名前が無い) |
| 拒否・状態不明・届かない | U1(入力がディレクトリ・UTF-8 でない → 2) |
| 遅れ | この委任には無い(外の呼び出しも待ちも無い) |
| 交差と後からの変化 | U12(印の後に本文を直す・途中の決めを足す)・U14(1 回だけ読む)・U15(受け取りのときに委任文が変わっている・印を偽る) |
| 浮動小数・刻み・丸め | U4(全角の空白・タブ)・U10(行末の空白・空行)・U12(括弧の入れ子) |
| 慣らし | U1(印がまだ無いときに失敗しても例外にならない) |
| 宣言した値の書き換え | U8(場面の名前・並び)・U10(決まった制約)・U15(変異の表) |
| 並行の変更 | U14(読む途中で委任文が変わっても、検めたバイトと印が一致する: 1 回だけ読むことで守る) |

## 受け入れ

各項目は、試験 `tests/delegation/test_spec.py` の名前を挙げた試験が、試験を変えずに通ること。全体で飛ばし 0。

- U1: 合格と印・入力の誤り・失敗で古い印を消す・全部の失敗を出す・Traceback を出さない: `test_valid_passes_and_writes_stamp`・`test_failure_removes_old_stamp`・`test_input_error_exit_2_and_removes_stamp`・`test_all_failures_listed_together`
- U2: 種類の行: `test_kind_line_within_first_5`・`test_kind_line_bad`・`test_read_kind_needs_source_rule_not_make_sections`・`test_critic_kind_core_only`
- U3: 見出し: `test_missing_heading`
- U4: 引用: `test_quote_whitespace_normalized_tab_and_fullwidth`・`test_quote_mismatch`・`test_quote_reverse_direction_and_adjacent`・`test_unnumbered_quote_in_purpose_fails`・`test_unnumbered_quote_outside_purpose_ok`
- U5: 読んだ事実の確かめの欄: `test_fact_cell`・`test_fact_cell_backtick_pipe_not_a_separator`・`test_fact_required_rows`
- U6: 封印: `test_seal_path_fails_without_opening`・`test_seal_path_absolute_and_outside_root`・`test_seal_names_in_fixed_section_do_not_fail`
- U7: 決めてよいこと: `test_decide_rows`
- U8: 壊す場面: `test_scene_row_missing`・`test_scene_cell_bad`・`test_scene_name_one_char_changed`・`test_scene_rows_out_of_order_fail`・`test_scene_u_reference_boundary`
- U9: 番号: `test_u_duplicate_fails_gap_ok`・`test_no_u_definitions_fails`・`test_h_none_line_ok_and_missing_fails`
- U10: 決まった制約: `test_fixed_one_char_changed_fails`・`test_fixed_line_removed_or_added_fails`・`test_fixed_trailing_space_and_blank_lines_ok`
- U11: 終わる条件と上限: `test_end_and_limit_words`
- U12: 事前の批評の記録と sha256: `test_print_hash_is_bare_64_hex_and_skips_checks`・`test_hash_rule_literal`・`test_tool_hash_matches_literal`・`test_premortem_missing_fails`・`test_premortem_hash_mismatch_after_body_edit`・`test_adding_midway_decision_keeps_premortem_valid`・`test_premortem_response_values`・`test_premortem_last_finding_at_end_of_file`・`test_second_round_is_last_and_cannot_say_fixed`・`test_next_version_response_needs_after_change_section`・`test_last_record_is_highest_number`
- U13: 承認(L-793): `test_require_approval`
- U14: 1 回だけ読む: `test_reads_delegation_once`
- U15: 受け取りの検め: `test_report_ok`・`test_report_param_test_name_ok`・`test_report_mutation_table_bad`・`test_report_two_ids_in_one_cell`・`test_report_rechecks_delegation_not_stamp`・`test_report_forged_stamp_does_not_matter`・`test_report_does_not_write_stamp`・`test_report_questions_need_midway_decisions`・`test_report_questions_section_required`・`test_report_read_kind_source_column`・`test_report_input_error_exit_2`
- U16: この委任文そのもの(3 版目)と、その事前の批評の記録(`DELEGATION_checker_premortem1.md`〜`premortem3.md`)に、作った `check_delegation.py` を当てると合格する(確かめ: `python3 scripts/delegation/check_delegation.py docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md` → 終了コード 0。印は git に入れない作業者の写しの置き場で試し、`docs/` には書かない。写し方: 委任文と 3 つの記録を tmp に写し、`--root` をリポジトリの根にする)

## 変異の表

作業者が作り、報告に付ける。U1〜U16 と H1〜H3 の番号ごとに 1 行以上: 「道具をわざと壊す変更(例: 見出しの検めの一覧から 1 つ消す)」と「それで落ちた試験の名前(`tests/delegation/test_spec.py::test_名前`)」。壊した変更は、道具を `DELEGATION_TOOLS_DIR` が指す写しの置き場に置いて当て、本物の道具は壊さない(試験は `--owner-log`・`--fixed`・`--scenes`・`--root` を全部渡すので、写しの置き場から根を決められなくても動く)。壊した変更で試験が 1 つも落ちなかったら、その行は「落ちなかった」と書き、問いとして返す。H の行は、確かめのコマンドと結果の 1 行の要約。

形: `| 番号 | 壊した変更 | 落ちた試験 |`

## 決まった制約
- 封印の置き場 `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読まない。2023-12-17T15:00Z より後のデータを読まない。
- `git worktree add` をしない。Do not commit. Do not push. git add もしない。
- フック・`.claude/settings.json`・`githooks/`・`.claude/agents/` を変えない。
- コード・コメント・ログ・文書にモデル名を書かない。出す文は日本語。
- 委任文に書かれていない選びが出たら、選ばずに問いとして返す(委任文の「決めてよいこと」に書かれたものだけは自分で決めてよい)。

## 終わる条件と上限

- 終わる条件: `tests/delegation/test_spec.py` が飛ばし 0 で全部通り、U16 と H1〜H3 が通り、変異の表の全部の行で壊した変更が試験を落とした。
- 上限: 作り直しは 2 周まで、または 3 時間。試験が食い違う・決まらないと分かったら、その件は止めて問いとして返し、それに依らない部分は続ける。

## 報告

- 着手前の表
- 作ったファイルの一覧
- 試験のコマンドと出力(`PYTHONPATH=src python -m pytest tests/delegation`)
- U16・H1〜H3 の確かめのコマンドと出力
- `## 変異の表`(上の形)
- 試験で決まらず作業者が決めた拾い方の一覧
- `## 問いとして返したこと`(行頭を `- Q1:` から番号にする。無ければ「問いとして返したことは無い」と書く)
- 日本語で。

## 途中の決め

(まだ無い。作業者の問いにリードが答えたら、ここに `- Q数字:` の行で足し、印を取り直す)

## 手の検め(リード。この 1 本だけ)

道具がまだ無いので、①の 1〜9 をリードが手で見た(使い捨ての検め `handcheck/handcheck_v2.py`)。結果は下の記録。

### 手の検めの記録(3 版目)

コマンド: `python3 docs/DISCUSSIONS/2026-10-07_delegation_redesign/handcheck/handcheck_v2.py docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md` → 出力:
- 1 種類の行: 3 行目 / 2 欠けた見出し: 無し / 3 番号の付いた太字の引用: 3(L-791 の 2 つ・L-793)、不一致: 無し
- 4 確かめの欄の `パス:行` 6 か所すべて実在し行の数以下(例: `scripts/jev_delegate.py` 494 ≤ 735、`docs/OWNER_LOG.md` 844 ≤ 853)。1 列目に データ・既存の決まり・列の意味 がある
- 5 決めてよいこと: 7 行全部 / 6 壊す場面: 12 の名前が一致、U の定義 16・重なり 0 / 7 H: H1・H2・H3 / 8 決まった制約: 一致 / 9 終わる条件と上限: ある
- 使い捨ての検めは、事前の批評の記録(検め 10)と、確かめの欄のコマンドの「→」の形は見ていない。
