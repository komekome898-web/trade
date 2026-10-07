# 引き継ぎ: 新しい委任の仕組みで、マチルダの委任を試す(L-799)

新しい会話の最初に、下の「引き継ぎの文」をそのまま渡す。

## 引き継ぎの文

あなたはこのリポジトリのリードです。CLAUDE.md を先頭から読み、§0(オーナーとのやりとり)を守ってください。最初に `docs/OWNER_STATUS.md` と、`docs/OWNER_LOG.md` の L-779〜L-799 を読んでください。

**この会話でやること(オーナーの逐語)**
- L-791「**測定に限らず全ての委任において、委任のミスでやり直しが発生しない委任文の書き方と仕組み**」
- L-799「**直しが済んだら止まって、一旦クリアしてマチルダが上手くいくか試すわ**」

前の会話で、委任文の検めと報告の受け取りの検めの道具を作りました(`scripts/delegation/check_delegation.py`・`scripts/delegation/check_report.py`)。この会話では、その仕組みでマチルダの委任を 1 本出し、委任のミスでやり直しが起きないかを試します。

**仕組みの段取り(必ずこの順)**: `.claude/skills/delegated-study/SKILL.md` §1.4。
1. 委任文を書く(手本 `docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md`、決まりは `tests/delegation/test_spec.py` の冒頭の注)
2. 形の検め
3. 事前の批評(作る種類。`.claude/skills/delegated-study/PREMORTEM_REQUEST.md`。上限は受け入れの形ごとに 2 回)
4. オーナーの承認: 問いに委任文の名前と版の印(`--print-hash` の値)を入れ、答えと同じ OWNER_LOG の行に記録する(L-796)
5. `--require-approval` で検め直してから渡す
6. 報告は `check_report.py` が 0 になるまでコミットしない。作り終えた後の批評家を 1 回当てる

仕組みの設計と限界: `docs/DISCUSSIONS/2026-10-07_delegation_redesign/PROPOSAL.md`(§2 段取り、§3 完了の試験、§4 限界)。§3 の完了の試験 = 作り終えた後の批評家 1 回目の [止める]・[直す] のうち、委任文の側の誤りの型 (a)(b)(c)(e)(f) が 0 件(型の定義は `DELEGATION_classify.md`)。1 本目(道具そのもの)は 2 回とも不合格で、L-798「**案2**」で残りを限界にして、この 2 本目に進んだ。

**マチルダの委任の中身(PROPOSAL.md §3 の 2 本目)**: 「マチルダの道の戦略(v37 の全部の設定を引数で受ける)と、取引の中の段の量をそろえる口(L-781)」。オーナーの決めは OWNER_LOG の L-779〜L-789 と、次の文書にあります。
- `docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/INTENT.md`(原典の意図)
- 同 `FRAMING_V37.md`(測る形。§8 にオーナーの答え L-784〜L-789)
- 同 `BEHAVIOR_L784.md`・`S5_FAMILIES.md`
- 1 分足の約定の決まり(L-769・L-770・L-783): コード `src/bot/bt/fill/`・`src/bot/bt/road/`、報告 `docs/DISCUSSIONS/2026-10-06_held_batches/REPORT_fill_scenario_L769_r2.md`。その批評家 2 回目は途中で止まり、懸念 3 つ(未確認)を `docs/DISCUSSIONS/2026-10-06_held_batches/FILL_L769_CRITIC2_PARTIAL.md` に写した。マチルダの委任の前か中で確かめる。

**守ること(前の会話で決まったもの)**
- 封印の置き場 `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読まない。2023-12-17T15:00Z より後のデータを読まない。`git worktree add` をしない。
- フック・`.claude/settings.json`・`githooks/`・`.claude/agents/` はオーナーの指示があったときだけ変える。
- オーナーに見える文は全部日本語(O-1)。オーナーの言葉を受けたら、その回のうちに OWNER_LOG と OWNER_STATUS に書く(I-001)。
- 推測で着手しない。着手の前に「やろうとすること × オーナーの原文の該当語(逐語)」の表を出し、右が空の行はそこだけ聞く(CLAUDE.md §0.1)。
- 作業ブランチ `claude/jev-eval-001-production-fq5o7w` にコミットして押し出す。

**終わる条件と上限**: マチルダの委任 1 本が、承認・作業・受け取りの検め・作り終えた後の批評家 1 回まで進み、その批評家の指摘を型ごとに数えてオーナーに見せたら終わり。上限: 事前の批評は受け入れの形ごとに 2 回、作業者 1 周、批評家 1 回。上限に達したら止めて、残りを数えてオーナーに聞く。
