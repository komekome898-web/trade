# 委任文: 読み口 diag_paths の足し — 24 時間前の対照と、合図の前半・後半(分析の持ち越しの 2・3)

種類: 作る

1 版目。読み口 `scripts/analysis/diag_paths.py`(分析のスキルの D4・D5 の表を出す)に 2 つを足す: (1) D5 の対照に「24 時間前の同じ時刻」を足す (2) 引数 `--cut` で、D5 の各群を合図の UTC の日で前半・後半に分けた表を足す。受け入れはリードが書いた実行できる試験 `tests/research/test_diag_paths_cut.py`(読み口の口と決まりは、試験の頭の注にある)。既存の試験 `tests/research/test_diag_paths.py` も変えずに通す。35 本の出力の作り直しとほかの門の値の走らせは、リードが受け取りの後にする(この委任では走らせない)。

## 着手前の表

作業者は、着手の前に「やろうとすること × オーナーの原文の該当語(逐語)」の 2 列の表を出す(CLAUDE.md §0.1 のまま)。この委任文は、検めと事前の批評の後にオーナーの承認を受けてから渡す(L-793「**委任文の検査が通ったのち、私に委任してよいか聞き、私の承認が得られてから委任すれば右の列は私の承認済のものになるでしょ。**」)。承認の逐語は末尾の `## オーナーの承認` の節にある。右の列には、承認の逐語を L-番号を引用の直前に間に何も挟まずに付けた形で書き、その行の根になる委任文の節の名前(例: 24 時間前の対照を足す行は「作るもの」の 1、試験を通す行は「受け入れ」)を添える。委任文のどこにも書かれていないことをする行は右が空になり、その行は着手せず「問いとして返したこと」に書く。表の下に完了見込み時間を、内訳(何を・何回・それぞれ何分)と一緒に書き、報告にその見込みとかかった時間を書く(L-844「**内訳を書くようにしましょう。 委任先にも同じことをさせてください。**」)。

## 目的(オーナーの逐語)

- L-909「**次の私の「進めてください」の合図で順次始めてください。**」・L-927「**進めてください**」
- リードの読み(オーナーの逐語ではない。OWNER_LOG の L-909・L-927 の行の解釈の欄): L-909 は持ち越しの 2 件(24 時間前の対照・門で外した合図の読みを前半・後半に分けることとほかの門の値)の狙いと中身を問い、L-927 で持ち越し 5 件を順に始める合図を出した。この委任はそのうち 2・3 の読み口の足し。
- リードの設計(オーナーの逐語ではない): 分析のスキル(`.claude/skills/analysis-lens`)の D5「対照が中立かを確かめる」は「24 時間前の対照も並べ、本体を先に読み、対照との差は後に読む」と決めているが、読み口に口が無い。門で外した合図の読みは、門の族の分析で前半・後半に分けずに読んでいた。足すのは表を出す口だけで、読み方は変えない。

## 作るもの

1. `d5` の各 h の dict に鍵 "control_24h_before" を足す(試験の頭の注のとおり。既にある鍵は変えない)。
2. 新しい関数 `d5_halves(signals, bars, days, cut)`(試験の頭の注のとおり)。
3. `render` に列「対照(24 時間前の同じ時刻)[区間]」を足し、res に "d5_halves" があれば前半・後半の表を足す(試験の頭の注のとおり)。
4. `main` に引数 `--cut YYYY-MM-DD` を足す。渡したときは D5 の全部の群について d5_halves を作り、res["d5_halves"]・res["cut"] に入れて md と json に書く。渡さないときの出力は、24 時間前の対照の列が増えるほかは今までと同じ。
5. ファイルの頭の docstring の D5 の説明に、24 時間前の対照と `--cut` を書き足す。

## 読んだ事実

| # | 事実 | 確かめ |
|---|---|---|
| データ | この委任は市場のデータを読まない。試験は合成の 1 分足(2019-12-01 からの 16 日、封印の境より前)だけで走る | `tests/research/test_diag_paths_cut.py:36`(T0 = 2019-12-01)・`grep -n "NDAYS = 16" tests/research/test_diag_paths_cut.py` → 1 行 |
| 既存の決まり | D5 の今の作り(24 時間後の対照だけ)と、表の列 | `scripts/analysis/diag_paths.py:174-187`・`scripts/analysis/diag_paths.py:207-213` |
| 既存の決まり | 合図の値動き(終値から h 分後の終値まで × 向き)と、日ごとの割合の区間(群の和 ÷ 群の数を日の塊で作り直す) | `scripts/analysis/diag_paths.py:130-142`・`scripts/analysis/diag_tables.py:228-249` |
| 既存の決まり | main の引数と、建てなかった合図の群の作り方 | `scripts/analysis/diag_paths.py:216-246` |
| 既存の決まり | 渡す時点の読み口・新しい試験・既存の試験の版(この版のまま作る。違っていたら問いとして返す) | `sha256sum scripts/analysis/diag_paths.py tests/research/test_diag_paths_cut.py tests/research/test_diag_paths.py` → `048a149bd923ff6626d4c09c95d2a50af65ee4d0ba10b4dbd950f3ed829eda21`・`df21b67b01aa9ed5209eb2e6c52ca05f7e9305512f9a0f8ed4efe1346e125013`・`ec705bc9a91597b35e2b41b2b2ee8590d381c0da330a460f2bcede7fa9e2a407`(渡す直前にリードが打ち直し、違えば書き直して版の印を取り直す) |
| 既存の決まり | 新しい試験は、今の読み口では落ち、既存の試験は通る | `PYTHONPATH=src python -m pytest tests/research/test_diag_paths_cut.py` → `6 failed` / `PYTHONPATH=src python -m pytest tests/research/test_diag_paths.py` → `4 passed` |
| 既存の決まり | 受け入れの試験は、リードの捨てる実装(scratchpad。リポジトリに入れていない。渡す前に消す)で新しい試験と既存の試験が全部通ることを確かめた。捨てる実装をわざと壊した 8 通り(24 時間前を 24 時間後で計算・前半の日を全部の日に・後半の日を全部の日に・表の 24 時間前の列に 24 時間後の値・`--cut` の引数を外す・後半の見出しに前半の表・24 時間前の群に 24 時間後の値の並び)のうち 7 通りは試験を 1 つ以上落とした。落ちなかった 1 通りは、境の日の合図を前半に入れる変更(前半の表は前半の日だけで数えるので、境の日の合図は前半の表に入らず、出力が変わらない) | 捨てる実装の置き場を先に読む試験の写しで `PYTHONPATH=src python -m pytest <写し>` → `10 passed`(新しい試験 6・既存の試験 4) |
| 列の意味 | 対照(24 時間後・24 時間前)= 同じ合図を 24 時間ずらした時刻に置き、同じ向きで測った値動き(向きの偏りと時間帯をそろえる)。日は合図の日で数える | `scripts/analysis/diag_paths.py:20`・`.claude/skills/analysis-lens/SKILL.md` の D5 の節の「対照が中立かを確かめる」の行(`grep -n "24 時間前の対照も並べ" .claude/skills/analysis-lens/SKILL.md` → 1 行) |

## 決めてよいこと・決めてはいけないこと

| 選び | 決め |
|---|---|
| 出力の置き場 | コードは `scripts/analysis/diag_paths.py` だけを変える。作業者が足したい試験は `tests/research/test_diag_paths_extra.py` に置いてよい。走らせの出力(`docs/RESEARCH/matilda_main/` の下)はリードが作る(この委任では書かない) |
| 分母・数え方 | 試験の頭の注のとおり(対照は足が無ければ数えない。日は合図の UTC の日) |
| 比べの方法 | この委任には無い(表を出すだけで、比べや判定の語は出さない) |
| 確かめ方 | `tests/research/test_diag_paths_cut.py` と `tests/research/test_diag_paths.py` が飛ばし 0 で全部通る |
| 依存 | 今の読み口と同じ(Python の標準ライブラリ・numpy・同じ置き場の `diag_tables`)。ほかを足さない |
| 絞り方・選び方 | 合図を絞らない(全部の群に前半・後半を作る) |
| 単位・通貨のそろえ方 | 今の読み口のまま(値動き率(bp)、時刻は ns、日は UTC の日の文字列) |
| 内部の形 | 試験で決まらない内部の形(表の並び・json の形のうち試験が見ない所)は作業者が決めてよい。決めたことを報告に書く |

## 変えないもの

- H1: 試験 `tests/research/test_diag_paths_cut.py`・`tests/research/test_diag_paths.py` と既存の試験を変えない。確かめ: `git status --short tests/` に出るのは、足してよい `tests/research/test_diag_paths_extra.py` だけ(無くてもよい)。
- H2: ほかのコードを変えない。確かめ: `git status --short src/ scripts/` に出るのは ` M scripts/analysis/diag_paths.py` だけ。
- H3: 既にある鍵・列を変えない(D4 の表・D5 の "signal"・"control_24h" と、その列)。確かめ: `git diff scripts/analysis/diag_paths.py` に、D4 の計算(`trade_life`・`d4`)の行の変更が無い。
- H4: 封印の置き場を名指さない。確かめ: `grep -nE "WINDOW1|phase2_sealed" scripts/analysis/diag_paths.py` の出力が、空(渡す前は 0 行。封印の窓の置き場を拒む検めは `diag_tables.WINDOW_MARK` を使う)。
- H5: 大きさ。`git diff --stat scripts/analysis/diag_paths.py` を報告に出す。
- H6: 試験が全部通る。確かめ: `PYTHONPATH=src python -m pytest tests/research/test_diag_paths_cut.py tests/research/test_diag_paths.py tests/research/test_diag_tables.py` が全部 passed、飛ばし 0。

## 壊す場面

| 場面 | 書いたこと |
|---|---|
| 封印の境 | この委任には無い(合成の足は封印の境より前。走らせの足の読みは今の読み口の `load_bitflyer_bars` のまま変えない) |
| 日・足・期間の境 | U2(境の日の 0 時ちょうどの合図は後半、その 1 分前は前半) |
| 等号 | U2(日 = cut は後半) |
| 欠け | U1(24 時間前に足が無い合図は対照に数えない) |
| 参照の値が無い | U1(24 時間前の足が無い)・U3(res に d5_halves が無いときは前半・後半の見出しを出さない) |
| 拒否・状態不明・届かない | この委任には無い(外の呼び出しが無い) |
| 遅れ | この委任には無い(時刻のずらしは 24 時間ちょうどで、遅れの決まりを持たない) |
| 交差と後からの変化 | U2(前半・後半の表は、それぞれその半分の日だけで区間を作る。全部の日で作ると落ちる) |
| 浮動小数・刻み・丸め | U1・U2(値は今の読み口の作りと 1e-12 まで同じ) |
| 慣らし | この委任には無い(読み口に慣らしは無い) |
| 宣言した値の書き換え | U3(表の 24 時間前の列は 24 時間前の値。24 時間後の値を書くと落ちる)・U4(`--cut` の引数) |
| 並行の変更 | この委任には無い(試験は見ない。渡す時点の読み口と試験の sha256 を読んだ事実の行に書き、違えば問いとして返す) |

## 受け入れ

各項目は、挙げた試験が、試験を変えずに通ること。全体で飛ばし 0。

- U1: 24 時間前の対照: `tests/research/test_diag_paths_cut.py::test_d5_has_24h_before_control`・`tests/research/test_diag_paths_cut.py::test_before_control_skips_missing_bars`
- U2: 前半・後半の分け: `tests/research/test_diag_paths_cut.py::test_d5_halves_split_by_utc_day`・`tests/research/test_diag_paths_cut.py::test_d5_halves_boundary_day_goes_to_second`
- U3: 表: `tests/research/test_diag_paths_cut.py::test_render_has_before_column_and_halves`
- U4: 引数: `tests/research/test_diag_paths_cut.py::test_main_has_cut_argument`
- U5: 既存の振る舞い: `tests/research/test_diag_paths.py::test_trade_life_signs_by_side`・`tests/research/test_diag_paths.py::test_trade_life_excludes_entry_bar_and_after_exit`・`tests/research/test_diag_paths.py::test_after_exit_and_signal_move_signed`・`tests/research/test_diag_paths.py::test_close_at_uses_bar_ending_at_time`

## 変異の表

作業者が作り、報告に付ける。U1〜U5 と H1〜H6 の番号ごとに 1 行以上: 「作った物をわざと壊す変更(例: 24 時間前を 24 時間後で計算する・前半の表を全部の日で作る・表の 24 時間前の列に 24 時間後の値を書く)」と「それで落ちた試験」。落ちた試験は 1 つずつ `tests/research/test_diag_paths_cut.py::test_名前` の形で、省かずに全部書く(パラメータは `[...]` を付けてよい。「何件(…ほか)」のまとめは使わない)。壊した変更は作業者の scratchpad の写しで当て、本物は壊したまま残さない。写しを当てるときは、試験の写しの頭で写しの置き場を `sys.path` の先頭に入れる(試験は `scripts/analysis` を `sys.path.insert(0, …)` で先に読むので、`-o pythonpath=` では写しが読まれない)。壊した変更で試験が 1 つも落ちなかったら、別の壊し方に差し替えずに、その行の 1 列目を U ではなく M の番号にして落ちた試験の欄に「落ちなかった」と書き、問いとして返す(「等価な変異」かどうかはリードが決める)。H の行は、確かめのコマンドと結果の 1 行の要約。

形: `| 番号 | 壊した変更 | 落ちた試験 |`

## 決まった制約
- 封印の置き場 `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読まない。2023-12-17T15:00Z より後のデータを読まない。
- `git worktree add` をしない。Do not commit. Do not push. git add もしない。
- フック・`.claude/settings.json`・`githooks/`・`.claude/agents/` を変えない。
- コード・コメント・ログ・文書にモデル名を書かない。出す文は日本語。
- 委任文に書かれていない選びが出たら、選ばずに問いとして返す(委任文の「決めてよいこと」に書かれたものだけは自分で決めてよい)。

## 終わる条件と上限

- 終わる条件: U1〜U5 の試験が飛ばし 0 で通り、H1〜H6 が通り、変異の表の全部の行で壊した変更が試験を落とした(落ちなかった行は問いとして返した)。
- 上限: 作業者 1 周、または 1 時間。試験が食い違う・決まらないと分かったら、その件は止めて問いとして返し、それに依らない部分は続ける。
- 走らせの出力を作り直さない(リードがする)。

## 報告

見出しは行頭の `## ` と次の名前に一字違わずそろえる(番号を付けない。手本 `docs/DISCUSSIONS/2026-10-08_simple_road/REPORT_s1.md`)。

- `## 着手前の表`(表の行をそのまま。その下に完了見込み時間と内訳、かかった時間)
- `## 作ったファイルの一覧と行数(H5)`
- `## 試験のコマンドと出力`(H6 のコマンド)
- `## H1〜H6 の確かめ`(コマンドと出力)
- `## 変異の表`(上の形)
- `## 試験で決まらず作業者が決めた内部の形`
- `## 問いとして返したこと`(行頭を `- Q1:` から番号にする。無ければ「問いとして返したことは無い。」と書く)
- 報告は返事に出す(リードが `docs/DISCUSSIONS/2026-10-08_matilda_main/REPORT_dpcut.md` に写す)。返す前に `python3 scripts/delegation/check_report.py <報告> --delegation docs/DISCUSSIONS/2026-10-08_matilda_main/DELEGATION_dpcut.md` を自分の scratchpad の写しで打ち、問いの行のほかに失敗が無いことを確かめる。
- 日本語で。コードの名前(関数・変数・例外の名前など)を出すときは、直後に日本語で何のことかを添える。リポジトリの根からの `grep -r`・`find .` をしない。`git ls-files` の一覧を使うときも封印の置き場を除く(`git ls-files -- . ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed'`。封印の置き場の 14 ファイルは git に載っている)。

## 途中の決め

作業者の問いにリードが答えたら、ここに `- Q数字:` の行で足し、印を取り直す。
