# 委任文: マチルダ本測定 前提の直接の測り(D1b)の台本

種類: 作る

3 版目(事前の批評 2 回目 `DELEGATION_d1b_premortem2.md` の後の直し。上限 2 回を使い切ったので、この直しは批評を通っていない。直した所は末尾の `## 事前の批評の後の変更`)。マチルダの基準の前提「中心から 4 ボラ外れた値段は戻る」を、戦略を回さずに市場の 1 分足だけで数える台本 `scripts/analysis/d1b_matilda.py` を作る。決まりの正本は `docs/DISCUSSIONS/2026-10-08_matilda_main/D1B_SPEC.md`(リードが書いた)、受け入れはリードが書いた実行できる試験 `tests/research/test_d1b_spec.py`(台本の口と決まりは、試験の頭の注にある)。全期間の走らせはリードが受け取りの後にする(この委任では走らせない)。

## 着手前の表

作業者は、着手の前に「やろうとすること × オーナーの原文の該当語(逐語)」の 2 列の表を出す(CLAUDE.md §0.1 のまま)。この委任文は、検めと事前の批評の後にオーナーの承認を受けてから渡す(L-793「**委任文の検査が通ったのち、私に委任してよいか聞き、私の承認が得られてから委任すれば右の列は私の承認済のものになるでしょ。**」)。承認の逐語は末尾の `## オーナーの承認` の節にある。右の列には、承認の逐語を L-番号を引用の直前に間に何も挟まずに付けた形で書き、その行の根になる委任文の節の名前(例: 結果を決める行は「作るもの」の 2、試験を通す行は「受け入れ」)を添える。委任文のどこにも書かれていないことをする行は右が空になり、その行は着手せず「問いとして返したこと」に書く。表の下に完了見込み時間を、内訳(何を・何回・それぞれ何分)と一緒に書き、報告にその見込みとかかった時間を書く(L-844「**内訳を書くようにしましょう。 委任先にも同じことをさせてください。**」)。

## 目的(オーナーの逐語)

- L-928「**1.B**」
- L-909「**次の私の「進めてください」の合図で順次始めてください。**」・L-927「**進めてください**」
- リードの読み(オーナーの逐語ではない。OWNER_LOG の L-927・L-928 の行の解釈の欄): L-928 の 1.B は「前提の直接の測りの台本は委任で作る」への答え。L-927 は分析の持ち越し 5 件を順に始める合図で、この台本は 1 件目。
- リードの設計(オーナーの逐語ではない): この台本は分析のスキル(`.claude/skills/analysis-lens`)の D1b(前提を戦略を使わずに直接確かめる測り)の手順。線は戦略のコード(`MatildaSimple`)に足が閉じた時点(`kind: "close"`)だけを渡して `decide` で作ったものをそのまま使い、自分で計算し直さない(線の定義の読み違いを作らないため)。道の中の戦略は足の途中の呼び出しも受けるので、ブレイク中の印とブレイクの線は道の中の値と同じではない(D1B_SPEC.md §2 の限界)。足の飛ばし方は道と同じ。結果の 4 通りの決め方・区間の取り方は D1B_SPEC.md §3・§4 と試験の頭の注。

## 作るもの

1. 新しいファイル `scripts/analysis/d1b_matilda.py`(既存のコードを変えない)。試験の頭の注にある口(`SEAL`・`CUT`・`LABELS`・`base_params`・`outcome`・`starts`・`ratio_diff_ci`・`summarize`・`main`)を持つ。
2. `outcome`・`starts`・`ratio_diff_ci`・`summarize` は試験の頭の注の決まりどおり。`starts` は足を 1 回だけ前から読み、起点の後 40 分の足を待ってから結果を決める(足の全部を記憶に持たない)。
3. `main` は `--files`・`--out`・`--seal` を受け、`day_counts.csv` と `tables.md` を書く。`tables.md` の中身は試験の注のとおり(年・first・second の起点の数と 5 つの結果の割合、first・second の区間、diff の点・区間・MDE、起点の 幅 ÷ ボラ と n_win の年ごとの中央値。幅 ÷ ボラ は `width_vola.out` と母集団が違うと書く)を、4 つの見方ごとの表にする。割合は % で小数 1 桁、区間も同じ。表の形(列の並び・見出しの言い方)は作業者が決めてよい。
4. ファイルの頭の docstring に、走らせ方 `PYTHONPATH=src python3 scripts/analysis/d1b_matilda.py --files backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_201[5-9].csv.gz backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_202[0-3].csv.gz --out docs/RESEARCH/matilda_main/d1b` と、決まりの正本(D1B_SPEC.md・試験)を書く。

## 読んだ事実

| # | 事実 | 確かめ |
|---|---|---|
| データ | 1 分足のファイルは年ごと。2024〜2026 年のファイルもあるが、`read_bars` は封印の境の年より後の年のファイルを開く前に止める。走らせ方には 2015〜2023 年だけを渡す | `ls backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/` → `candles_1m_2015.csv.gz` 〜 `candles_1m_2026.csv.gz` ほか / `src/bot/bt/simple/bars.py:23-26` |
| データ | `read_bars` は封印の境以後に始まる足の行に届いたら終わる。値段の空の足は飛ばす。足 = (始まりの時刻の文字列, 始値, 高値, 安値, 終値, 出来高) | `src/bot/bt/simple/bars.py:13-20`・`src/bot/bt/simple/bars.py:38-44` |
| 既存の決まり | 向きの決まらない足(始値 = 終値 かつ 直前に飛ばさずに回した足の終値と同じ、またはデータの頭)は無い足として飛ばす | `src/bot/bt/simple/run.py:66-79` |
| 既存の決まり | 線の計算: ボラ・中心・幅・ブレイクの候補(`_update`)、次の足の間に使う線と門(`_make_snap`) | `src/bot/strategy/matilda_simple.py:506-537`・`src/bot/strategy/matilda_simple.py:539-555` |
| 既存の決まり | 玉が無くても、足の終値がブレイクの線を越えると戦略はブレイク中の印 `_brk` を ±1 にし、ブレイク中は建ての注文を置かない。道の中では、足の途中で見張る値段に届いたときの呼び出しでも `_brk` が動く(この台本は足が閉じた時点だけを渡すので、その分は道と違う) | `src/bot/strategy/matilda_simple.py:427-434`・`src/bot/strategy/matilda_simple.py:449-458`・`src/bot/strategy/matilda_simple.py:151-158`・`src/bot/strategy/matilda_simple.py:365-373`・`src/bot/bt/simple/run.py:127-151` |
| 既存の決まり | 足を束ねる分数 foot = 1 では、戦略は時刻が戻る足・重なる足を例外なしで受け入れる(事前の批評の担当の試し。台本が時刻の順を検める) | `src/bot/strategy/matilda_simple.py:478-482` |
| 既存の決まり | 基準の引数の値(vola_count 40・range_count 40・break_len_mult 2・break_delay 1・break_dist 0.5・beard_ignore 1・range_setting 0.00025・over_range_setting 1/6・vola_setting None) | `PYTHONPATH=src python3 -c "from bot.strategy.matilda_simple import BASE_PARAMS as B; print({k: B[k] for k in ('vola_count','range_count','break_len_mult','break_delay','break_dist','beard_ignore','range_setting','over_range_setting','vola_setting')})"` → `{'vola_count': 40, 'range_count': 40, 'break_len_mult': 2, 'break_delay': 1, 'break_dist': 0.5, 'beard_ignore': 1, 'range_setting': 0.00025, 'over_range_setting': 0.16666666666666666, 'vola_setting': None}` |
| 既存の決まり | 戦略を足ごとに進めて線を読む形の手本(リードが書いた。基準の 幅 ÷ ボラ の表) | `docs/RESEARCH/matilda_main/base/width_vola.py:13-27` |
| 既存の決まり | 割合の区間(日を選び直して Σ ÷ Σ を作り直す)と、選び直しの引き方 | `scripts/analysis/diag_tables.py:228-249`・`scripts/analysis/diag_tables.py:167-175`・`scripts/analysis/diag_tables.py:47` |
| 既存の決まり | 渡す時点の決まりの文書と試験の版(この版のまま作る。違っていたら問いとして返す) | `sha256sum docs/DISCUSSIONS/2026-10-08_matilda_main/D1B_SPEC.md tests/research/test_d1b_spec.py` → `78c366b8ce649a4acbe92886632a56691e3d5203557cab6354d58c0ae4da0919`・`af69e5cdae838bc42382cd8a4876d6b694b21ecca06fbdfe5a09ccbf14e687e9`(渡す直前にリードが打ち直し、違えば書き直して版の印を取り直す) |
| 既存の決まり | 台本が無いと、試験は飛ばしになる | `PYTHONPATH=src python -m pytest tests/research/test_d1b_spec.py` → `1 skipped` |
| 既存の決まり | 受け入れの試験は、リードの捨てる実装(scratchpad。リポジトリに入れていない。渡す前に消す)を試験の口 `D1B_MODULE_DIR` で当てて全部通ることを確かめた。捨てる実装をわざと壊した 20 通り(飛ばした足を道に入れる・利確の線の符号・入りを常に True・終わり近くの起点を残す・20 分の境を 19 に・同じ足で両方を無くす・封印の境の等号・半分が 0 本のときの割り算・41 分目を見る・区間の種・日ごとの数の行の並び・brk を常に 0・入りの門の見方で brk を見ない・時刻の順を検めない・後の封印の境を受ける・n_win を 41 分まで・`--seal` を文字列で比べる・日ごとの数に brk の列が無い・表の割合の桁・時点の門の見方で brk を見ない)は、それぞれ試験を 1 つ以上落とした。落ちなかったのは 2 通りで、起点の等号(終値 = 建ての線ちょうどを起点にする。線は足 t 自身を含めて計算するので、試験の合成の足でちょうど線に置く形を作っていない。事前の批評 2 回目の担当の試しでは、実物でも 2017 年の頭 10 万行の起点 32,830 のうち 33 で起きていた【担当の試し】)と、割合の作り直しを Σ ÷ Σ から 平均 ÷ 平均 にする変更(同じ数なので等価) | `D1B_MODULE_DIR=<捨てる実装の置き場> PYTHONPATH=src python -m pytest tests/research/test_d1b_spec.py` → `33 passed` |
| 列の意味 | 試験と D1B_SPEC.md の結果の名前: i = 20 分以内に利確の線、ii = 21〜40 分に起点の値段、iii = ブレイクの線に先に、iv = どれも無し、both = 同じ足で (i か ii) と iii | `docs/DISCUSSIONS/2026-10-08_matilda_main/D1B_SPEC.md:28-39` |

## 決めてよいこと・決めてはいけないこと

| 選び | 決め |
|---|---|
| 出力の置き場 | コードは `scripts/analysis/d1b_matilda.py` だけ。作業者が足したい試験は `tests/research/test_d1b_extra.py` に置いてよい。全期間の走らせの出力(`docs/RESEARCH/matilda_main/d1b/`)はリードが作る(この委任では書かない) |
| 分母・数え方 | 試験の頭の注のとおり(割合の分母 = その見方・期間の起点の数、日 = 評価した足のある UTC の日) |
| 比べの方法 | 前半・後半の割合の差 = `ratio_diff_ci`(試験の頭の注)。ほかの比べは作らない |
| 確かめ方 | 試験 `tests/research/test_d1b_spec.py` が飛ばし 0 で全部通り、`tests/research` の既存の試験の結果が渡す前と変わらない(`test_c4_w6b_order.py` は封印の置き場を読む試験で、この容器では元から落ちる。打たない) |
| 依存 | Python の標準ライブラリと numpy、`bot.strategy.matilda_simple`、`bot.bt.simple.read_bars`、同じ置き場の `diag_tables`(`group_ratio_ci`・`SEED`)。ほかを足さない |
| 絞り方・選び方 | 起点を門・側・年で絞らない(全部を記録し、見方は `summarize` が分ける)。結果を見て見方を足さない |
| 単位・通貨のそろえ方 | 値段は円、時刻は足のファイルの ts の文字列のまま、日は UTC の日(ts の頭 10 字)。割合は 0〜1 の数で返し、`tables.md` だけ % |
| 内部の形 | 試験で決まらない内部の形(関数の分け方・40 分待つ入れ物の作り方・`tables.md` の表の形)は作業者が決めてよい。決めたことを報告に書く |

## 変えないもの

- H1: 試験 `tests/research/test_d1b_spec.py` と既存の試験を変えない。確かめ: `git status --short tests/` に出るのは、足してよい `tests/research/test_d1b_extra.py` だけ(無くてもよい)。
- H2: 既存のコードを変えない。確かめ: `git status --short src/ scripts/` に出るのは `scripts/analysis/d1b_matilda.py` だけ。
- H3: 線を自分で計算し直さない。確かめ: `grep -nE "vola_count|range_count|break_dist|beard_ignore" scripts/analysis/d1b_matilda.py` の出力が空(引数の名前を台本が読むなら、線を計算し直している疑い。`exit_setting` は利確の線のために読んでよい)。
- H4: 封印の置き場と 2024 年より後のファイルを名指さない。確かめ: `grep -nE "WINDOW1|phase2_sealed|candles_1m_202[4-9]" scripts/analysis/d1b_matilda.py` の出力が空(SEAL より後の `--seal` を拒むのは U5 の試験が見る)。
- H5: 大きさ。`wc -l scripts/analysis/d1b_matilda.py` を報告に出す。
- H6: 試験が全部通る。確かめ: `PYTHONPATH=src python -m pytest tests/research/test_d1b_spec.py tests/research/test_diag_tables.py tests/research/test_diag_paths.py` が全部 passed、飛ばし 0。

## 壊す場面

| 場面 | 書いたこと |
|---|---|
| 封印の境 | U3(封印の境の足より先を求めない・起点の時刻 + 41 分が境を越える起点を記録しない) |
| 日・足・期間の境 | U1(20 分目・21 分目・40 分目・41 分目)・U3(データの終わり近くの起点を記録しない)・U4(前半・後半の境の日、年の境) |
| 等号 | U1(利確の線ちょうど・ブレイクの線ちょうど・起点の値段ちょうど) |
| 欠け | U1(足の欠け = 1 分目と 35 分目だけ)・U2(足の欠けを含む合成の足)・U4(半分の起点が 0 本) |
| 参照の値が無い | U1(ブレイクの線が None)・U2(線の無い慣らしの間の足は起点にも日にも入れない) |
| 拒否・状態不明・届かない | U2(時刻が増えない足で ValueError。ファイルの順の誤りを黙って進めない)。`read_bars` の例外(`SimpleRoadError`、足の読みの誤り)は台本で捕まえずにそのまま上げる(試験は見ない) |
| 遅れ | U2(線は足 t 自身を含めて計算した線。起点の後の足だけで結果を決める。brk は足 t の decide の後の印)・U1(起点の足より後だけを見る) |
| 交差と後からの変化 | U1(同じ足で利確とブレイクの両方・戻りとブレイクの両方)・U2(入りか時点か = 直前に評価した足が同じ側の起点か) |
| 浮動小数・刻み・丸め | U2(線は戦略の値をそのまま。比べは誤差 1e-6 円まで)・U4(割合の区間の作り直しは同じ式で 1e-12 まで) |
| 慣らし | U2(戦略の `_snap` が None か vola ≤ 0 の足は起点にしない。ブレイク中の起点は記録し、門の見方からだけ外す) |
| 宣言した値の書き換え | U2(基準の引数 = `base_params()`。既定の引数で同じ結果)・U3(門を大きくすると門の閉じた起点が記録される = 門で起点を落とさない)・U5(SEAL より後の `--seal` を、時差の付いた値も含めて拒む) |
| 並行の変更 | この委任には無い(試験は見ない。渡す時点の決まりの文書と試験の sha256 を読んだ事実の行に書き、違えば問いとして返す) |

## 受け入れ

各項目は、試験 `tests/research/test_d1b_spec.py` の挙げた試験が、試験を変えずに通ること。全体で飛ばし 0。

- U1: 結果の決め方: `tests/research/test_d1b_spec.py::test_outcome_cases`(18 場面)
- U2: 起点・線・入りと時点・飛ばす足が、戦略そのもので作った参照と同じ: `tests/research/test_d1b_spec.py::test_base_params`・`tests/research/test_d1b_spec.py::test_starts_match_strategy_reference`・`tests/research/test_d1b_spec.py::test_starts_default_params_are_base`・`tests/research/test_d1b_spec.py::test_skipped_bars_are_not_in_path`・`tests/research/test_d1b_spec.py::test_starts_refuse_non_increasing_time`(2 場面)
- U3: 封印の境・データの終わり・門の閉じた起点: `tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts`・`tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end`・`tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded`
- U4: 割合・区間・差の区間・空の半分: `tests/research/test_d1b_spec.py::test_ratio_diff_ci_formula`・`tests/research/test_d1b_spec.py::test_summarize_empty_half_is_none`・`tests/research/test_d1b_spec.py::test_summarize_counts_and_cis`
- U5: 出力(日ごとの数の列と、表の割合が summarize と同じこと)と封印の境の引数: `tests/research/test_d1b_spec.py::test_main_writes_day_counts`・`tests/research/test_d1b_spec.py::test_main_refuses_later_seal`(2 場面)

## 変異の表

作業者が作り、報告に付ける。U1〜U5 と H1〜H6 の番号ごとに 1 行以上: 「作った物をわざと壊す変更(例: 飛ばした足を結果の道に入れる・利確の線の符号を逆にする・入りを常に True にする・41 分目の足を見る・区間の種を変える)」と「それで落ちた試験」。落ちた試験は 1 つずつ `tests/research/test_d1b_spec.py::test_名前` の形で、省かずに全部書く(パラメータは `[...]` を付けてよい。「何件(…ほか)」のまとめは使わない)。壊した変更は作業者の scratchpad の写しの置き場(`d1b_matilda.py` だけを置く)で当て、本物は壊したまま残さない。当て方は `D1B_MODULE_DIR=<写しの置き場> PYTHONPATH=src python -m pytest tests/research/test_d1b_spec.py`(試験がその置き場を本物より先に読む)。壊した変更で試験が 1 つも落ちなかったら、別の壊し方に差し替えずに、その行の落ちた試験の欄に「落ちなかった」と書き、問いとして返す(「等価な変異」かどうかはリードが決める)。H の行は、確かめのコマンドと結果の 1 行の要約。

形: `| 番号 | 壊した変更 | 落ちた試験 |`

## 決まった制約
- 封印の置き場 `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読まない。2023-12-17T15:00Z より後のデータを読まない。
- `git worktree add` をしない。Do not commit. Do not push. git add もしない。
- フック・`.claude/settings.json`・`githooks/`・`.claude/agents/` を変えない。
- コード・コメント・ログ・文書にモデル名を書かない。出す文は日本語。
- 委任文に書かれていない選びが出たら、選ばずに問いとして返す(委任文の「決めてよいこと」に書かれたものだけは自分で決めてよい)。

## 終わる条件と上限

- 終わる条件: U1〜U5 の試験が飛ばし 0 で通り、H1〜H6 が通り、変異の表の全部の行で壊した変更が試験を落とした(落ちなかった行は問いとして返した)。
- 上限: 作業者 1 周、または 1 時間 30 分。試験が食い違う・決まらないと分かったら、その件は止めて問いとして返し、それに依らない部分は続ける。
- 試験と D1B_SPEC.md が食い違うと思ったら、どちらのどの行かを書いて問いとして返す。どちらかに合わせて黙って決めない。全期間の足で走らせない(走らせはリードがする)。

## 報告

- 着手前の表(その下に完了見込み時間と内訳)と、かかった時間
- 作ったファイルの一覧と行数(H5)
- 試験のコマンドと出力(H6 のコマンド)
- H1〜H6 の確かめのコマンドと出力
- `## 変異の表`(上の形)
- 試験で決まらず作業者が決めた内部の形の一覧
- `## 問いとして返したこと`(行頭を `- Q1:` から番号にする。無ければ「問いとして返したことは無い。」と書く)
- 報告は返事に出す(リードが `docs/DISCUSSIONS/2026-10-08_matilda_main/REPORT_d1b.md` に写す)
- 日本語で。コードの名前(関数・変数・例外の名前など)を出すときは、直後に日本語で何のことかを添える。リポジトリの根からの `grep -r`・`find .` をしない。`git ls-files` の一覧を使うときも封印の置き場を除く(`git ls-files -- . ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed'`。封印の置き場の 14 ファイルは git に載っている)。

## 途中の決め

作業者の問いにリードが答えたら、ここに `- Q数字:` の行で足し、印を取り直す。

- Q1: 変異の表で落ちなかった行が 6 通りある(M07・M14・M15・M20・M24・M31)。差し替えずに残した。「等価な変異」かどうかの判断をお願いする。受け取りの検めは、U の番号が付いた行に「落ちなかった」があると不合格にするので、この 6 行だけ 1 列目を M の番号にして U の番号を付けていない(表の 2 列目の頭に属する U の番号を書いた。行は消していない)。 — 答え(リード): 6 行とも M の番号のまま残してよい(落ちなかったことを隠さない形として受ける)。M07・M20・M24・M31 は台本の作りの上で等価な変異と決める(M07 = starts は起点の足を道に渡さない、M20 = 戦略が price を使うのは足の途中の呼び出しの処理 `matilda_simple.py` 381・387 行だけ、M24・M31 = 作業者の説明どおり)。M14・M15 は試験の穴(合成の足にボラ 0 の足が無い・1 日分しか無い)で、台本はリードが読んで正しい(`d1b_matilda.py` 162〜166 行)。試験は足さず、全期間の走らせの後に、年ごとの日の数とボラ 0 の足の扱いをリードが確かめる。
- Q2: 気づき(判断を求めるものではない)。day_counts.csv は起点の無い日の行を書かない(試験の決まり)ので、CSV だけでは区間を作り直せない。日の一覧が要るなら別の出力が要る。今回は何も足していない。 — 答え(リード): 足さない。区間は台本の summarize が日の一覧から作る。CSV は見方ごとの数の作り直しのために置く。

## オーナーの承認

- L-929「**yes**」(問いと答えは OWNER_LOG の L-929 の行。問いに委任文の名前と版の印を入れた。L-796)

## 事前の批評の後の変更

見た版の sha256: 6fad1fa56f310d54c3956d3480f2c0446f6e76c7267fc39ab712d3e069c3a130

(最後の回 = 2 回目が見た版。1 回目が見た版は f2e37052118786eb2b10141b74c13b5447b3f27b02631d1e8f10efd82a96b1b2)

### 1 版目 → 2 版目(1 回目の記録 `DELEGATION_d1b_premortem1.md` の [直す] 6 件と [聞く] 5 件)

- 線とブレイク中の印: 試験の注・参照に `brk`(戦略の `_brk`)を足し、「門が開いている」の見方を「門が開いていて brk = 0」にした。D1B_SPEC.md §2 のリードの誤り(「玉は持たないので `_brk` = 0」)を直した。
- 時刻の順: 試験 `test_starts_refuse_non_increasing_time` を足した。
- `--seal`: 試験 `test_main_refuses_later_seal` を足した。
- 疎らさ: 起点ごとの `n_win` を試験の鍵に足し、tables.md に年ごとの中央値を並べる。
- 幅 ÷ ボラ の母集団: 起点の時点の値と書き、`width_vola.out` と違うと表に書く。
- H4 の正規表現と種(`diag_tables.SEED`)、変異の表の当て方(試験の口 `D1B_MODULE_DIR`)、目的の節の L-702 の行(逐語ではないので外した)。
- 受け入れの試験は 32 件(捨てる実装で 32 passed)。

### 2 版目 → 3 版目(2 回目の記録 `DELEGATION_d1b_premortem2.md` の [直す] 7 件と [聞く] 6 件。事前の批評の上限 2 回を使い切ったので、この直しは批評を通っていない)

- ブレイク中の印: 道と同じ呼び方(足の途中の呼び出し)にはそろえず、足が閉じた時点だけを渡す形のままにした。目的の節・読んだ事実・D1B_SPEC.md §2 に限界(道の中の値と起点の約 9〜12% で違う。担当の試し【推定】)を書き、見方の名前から「戦略が建てうる」を外して「足が閉じた時点の判定でブレイク中でない」にした。
- 入りの決まり: D1B_SPEC.md §2 を試験に合わせた(直前に評価した足が同じ側の起点でない)。
- `--seal`: 試験に時差の付いた値(2023-12-17T09:00:00-08:00)の場面を足した。
- `day_counts.csv` に brk の列を足した(門の見方を CSV から作り直せるように)。
- tables.md: 試験に「表の割合が summarize の値と同じ(% で小数 1 桁)」を足した。
- 並行の変更の行、目的の節の括弧書き(リードの読みとして分けた)、読んだ事実の等号の行。
- 受け入れの試験は 33 件(捨てる実装で 33 passed、壊した 20 通りが全部 1 つ以上の試験を落とした)。
