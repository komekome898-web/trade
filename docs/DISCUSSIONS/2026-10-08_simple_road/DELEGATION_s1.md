# 委任文: 単純な測りの道 S1 — 走らせ・約定・残し方・数の作り直し

種類: 作る

1 版目。測りの道を単純な形に作り直す(L-819・L-821)3 本の委任の 1 本目。S2(約定の作り直し = 検査 1、別の作業者)と S3(マチルダを新しい道に移す)はこの委任に入れない。決まりの正本は `docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md`、受け入れはリードが書いた実行できる試験 `tests/simple/test_s1_spec.py`。

## 着手前の表

作業者は、着手の前に「やろうとすること × オーナーの原文の該当語(逐語)」の 2 列の表を出す(CLAUDE.md §0.1 のまま)。この委任文は、検めと事前の批評の後にオーナーの承認を受けてから渡す(L-793「**委任文の検査が通ったのち、私に委任してよいか聞き、私の承認が得られてから委任すれば右の列は私の承認済のものになるでしょ。**」)。承認の逐語は末尾の `## オーナーの承認` の節にある。右の列には、承認の逐語と、その行の根になる委任文の節の名前(例: 約定の関数を作る行は「作るもの」の 2、試験を通す行は「受け入れ」)を書く。委任文のどこにも書かれていないことをする行は右が空になり、その行は着手せず「問いとして返したこと」に書く。目的の節の L-791 は委任のやり方への指示なので、右の列の根にしない。

## 目的(オーナーの逐語)

- L-819「**なんか継ぎ足しでどんどん複雑になってない？このまま足し続けても新たな穴ができるだけだと思う。**」「**測定方法も残し方も検査もシンプルにできるはず**」
- L-821「**1.よい 2.よい**」(`DESIGN.md` の決めること: 1 = 足ごとに「出しておく注文の全部」を返し、返さなかったものは取り消す。2 = 走らせごとの検査は約定の作り直しと数の作り直しの 2 つ)
- L-816「**1.a**」・L-817「**問い 2(B-1) a**」(段の値段は 1 段目の約定値段から。1 段目が約定した足でも、良い側・悪い側とも約定させる)
- L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」(数は帳簿のツールで約定から計算する)
- L-791「**測定に限らず全ての委任において、委任のミスでやり直しが発生しない委任文の書き方と仕組み**」
- リードの設計(オーナーの逐語ではない): SPEC.md の「リードの決め」の印の付いた所(値段の空の足を飛ばす・同じ番号で中身が違えば止める・約定した番号をまた返せば止める・1 本の足の中で約定させる順・止める注文の一覧・親が約定した後に出た利確の扱い)。

## 作るもの

1. 新しい包み `src/bot/bt/simple/`(既存のコードを変えない)。`from bot.bt.simple import run, read_bars, check_numbers, SimpleRoadError` で読める(試験の冒頭の注の口)。
2. 約定の関数: SPEC.md §2・§3 のとおり。1 本の足について、出ている注文と足から約定を返す。
3. 走らせ `run(bars, strategy, side, out_dir, tick, meta)`: 足を古い順に回し、足ごとに 約定 → 戦略に知らせる → 判定(SPEC.md §2)。止める場面は `SimpleRoadError`(日本語の文)。
4. 足の読み `read_bars(paths, seal_iso)`: SPEC.md §1。bitFlyer lightchart の 1 分足のファイル(`backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/README.md` の列)を読み、値段の空の足を飛ばし、封印の境以後の足で止める。境の年より後の年のファイル(名前の `_YYYY.csv.gz`)は開かずに止める。
5. 残し方: SPEC.md §4 のファイルを、足を回しながら書き足す(注文の行は消えた時か約定した時に書き、ファイルに出す)。最後に帳簿のツール `book`(`src/bot/bt/road/ledger.py:254`)で約定から trades・summary を作る。
6. 数の作り直し `check_numbers(out_dir, side)`: SPEC.md §5 の 2。`book` で約定のファイルから計算し直した数と、書いた trades・summary の食い違いの並び(無ければ空)。

## 読んだ事実

| # | 事実 | 確かめ |
|---|---|---|
| データ | この委任は市場のデータを読まない。試験は tmp に書いた合成の足だけで走る(時刻 2023-11-14・2023-12-17、封印の境より前)。足のファイルの形は README の列と、2016 年のファイルの頭の 3 行で確かめた | `zcat backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2016.csv.gz \| head -3` → `ts,open,high,low,close,volume,col7_inferred_long_oi,col8_inferred_short_oi,buy_volume,sell_volume`・`2016-01-01T00:03:00+00:00,51810.0,51810.0,51810.0,51810.0,4.45622112,,,,`・`2016-01-01T00:04:00+00:00,,,,,0.0,,,,` |
| 既存の決まり | 帳簿のツール `book` は、約定の列から取引ごとの表とまとめを作る。同じ時刻の約定を受け付ける | `PYTHONPATH=src python3 -c "from bot.bt.road.ledger import book; f=[{'t_ns':60,'side':'buy','qty':0.009,'px':100.0,'ccy':'JPY'},{'t_ns':60,'side':'buy','qty':0.009,'px':99.0,'ccy':'JPY'},{'t_ns':120,'side':'sell','qty':0.018,'px':101.0,'ccy':'JPY'}]; print(book(f).summary)"` → `{'fill_count': 3, 'closed_trades': 1, 'pnl_jpy': '0.027', 'open_trades': 0, 'trades': [...]}` |
| 既存の決まり | 取引の表の欄の名前 | `src/bot/bt/road/ledger.py:86-87` |
| 既存の決まり | 受け入れの試験は、作る前は包みが無いので飛ばしになる | `PYTHONPATH=src python -m pytest tests/simple` → `1 skipped` |
| 既存の決まり | 受け入れの試験の期待の値は、リードが捨てる前提の実装を一時的に置いて確かめ、全部通った(置いた実装は外した) | `PYTHONPATH=src python -m pytest tests/simple` → `32 passed`(捨てる実装を置いた時) |
| 既存の決まり | 道の既存の試験は全部通る | `PYTHONPATH=src python -m pytest tests/road` → `315 passed` |
| 列の意味 | 足のファイルの ts は 1 分の始まりの UTC(ISO 8601)、値段が空の足はその分に約定が無かった足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/README.md:35-38` |
| 列の意味 | 単純な道の決まりと残すファイルの列 | `docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md:1` |

## 決めてよいこと・決めてはいけないこと

| 選び | 決め |
|---|---|
| 出力の置き場 | コードは `src/bot/bt/simple/` だけ。作業者が足したい試験は `tests/simple/test_s1_extra.py` に置いてよい。走らせの出力は試験の tmp だけ |
| 分母・数え方 | この委任には無い(数えない。数は帳簿のツールのまま) |
| 比べの方法 | 約定の決まりの等号は SPEC.md §3 のとおり(範囲の内 = 安値 ≦ 値段 ≦ 高値)。数の作り直しは文字列で 1 字違わず比べる |
| 確かめ方 | 試験 `tests/simple/test_s1_spec.py` が飛ばし 0 で全部通り、`tests/road` が全部通る |
| 依存 | Python の標準ライブラリと、このリポジトリの `bot.bt.road.ledger`(帳簿のツール)だけ。取引所の模型・core・道の土台・走らせ(`bot.bt.fill`・`bot.bt.core`・`bot.bt.road.strategy`・`bot.bt.pipeline`)を import しない |
| 絞り方・選び方 | この委任には無い(測らない) |
| 単位・通貨のそろえ方 | 値段は円、量は BTC(0.001 の刻み)、時刻は足のファイルの ts の文字列のまま。`book` に渡す時刻だけ UTC の ns |
| 試験で決まらない内部の形 | 作業者が決めてよい(関数の分け方・ファイルの分け方・数の文字列の書き方のうち試験が見ない所)。決めたことを報告に書く |

## 変えないもの

- H1: 試験 `tests/simple/test_s1_spec.py` と既存の試験を変えない。確かめ: `git diff --stat tests/` が空。
- H2: 既存のコードを変えない。確かめ: `git diff --stat src/` が空(足したのは `src/bot/bt/simple/` の新しいファイルだけ。`git status --short src/` に出るのはそれだけ)。
- H3: 依存の決めのとおり、取引所の模型・core・道の土台・走らせを import しない。確かめ: `grep -rn "bot.bt.fill\|bot.bt.core\|bot.bt.road.strategy\|bot.bt.pipeline" src/bot/bt/simple/` が空。
- H4: 道の既存の試験が全部通る。確かめ: `PYTHONPATH=src python -m pytest tests/road` が全部 passed。
- H5: 大きさ。`src/bot/bt/simple/` の行数の合計を報告に出す(上限は決めない。L-819 の「シンプル」の確かめとして見せる)。確かめ: `wc -l src/bot/bt/simple/*.py`。

## 壊す場面

| 場面 | 書いたこと |
|---|---|
| 封印の境 | U6(境ちょうどの足で止める・境の年より後の年のファイルは開かない) |
| 日・足・期間の境 | U6(欠けた分の後の「次の足」は、データにある次の足)・U1(段が根の足と次の足で当たり方が変わる) |
| 等号 | U1(段の値段 = 安値ちょうど)・U2(売りの段の値段 = 高値ちょうど)・U4(利確の値段 = 高値ちょうど) |
| 欠け | U6(値段の空の足を飛ばす)・U5(根が約定しないまま消える → 段の値段は空) |
| 参照の値が無い | U7(根の無い段・親の無い利確で止める) |
| 拒否・状態不明・届かない | U7(止める注文の 10 通り) |
| 遅れ | U4(悪い側の利確は次の足から・親が約定した後に出た利確は次の足から) |
| 交差と後からの変化 | U7(同じ番号で中身が違う・約定した番号をまた返す・根が約定した後に初めて出た段) |
| 浮動小数・刻み・丸め | U2(買いと売りの切り捨て・10 進の和・戦略の値段と切り捨てた値段の両方を残す) |
| 慣らし | この委任には無い(慣らしは戦略の仕事。S3 で扱う) |
| 宣言した値の書き換え | U8(書いた summary を書き換えると数の作り直しが食い違いを出す) |
| 並行の変更 | この委任には無い(作業者は 1 名。新しいファイルだけを足し、既存のファイルに触れない) |

## 受け入れ

各項目は、試験 `tests/simple/test_s1_spec.py` の挙げた試験が、試験を変えずに通ること。全体で飛ばし 0。

- U1: 段の約定(L-816 の例): `test_t1_levels_from_root_fill`(良い側・悪い側)
- U2: 刻みの切り捨てと 10 進の和: `test_t2_buy_level_floored`・`test_t2_sell_level_floored`・`test_t2_decimal_sum`・`test_t2_limit_floored_and_calc_kept`
- U3: 指値・成行の決まり: `test_t3_limit_cases_and_market`
- U4: 付けた利確: `test_t4_exit_on_level`・`test_t4_exit_after_parent_filled_is_plain_limit`
- U5: 根と段が消える: `test_t5_root_and_level_withdrawn`
- U6: 欠けた足・値段の空の足・封印: `test_t6_next_bar_is_next_present_bar`・`test_t6_read_bars_skips_null_and_stops_at_seal`・`test_t6_read_bars_refuses_files_after_seal_year`
- U7: 止める場面: `test_t7_stops`(10 通り)
- U8: 残し方と数の作り直し: `test_t8_files_signals_and_numbers`・`test_t8_records_are_written_while_running`

## 変異の表

作業者が作り、報告に付ける。U1〜U8 と H1〜H5 の番号ごとに 1 行以上: 「作った物をわざと壊す変更(例: 段の値段を切り上げにする・悪い側でも親の足で利確を試す・約定させる順を exit → level にする)」と「それで落ちた試験(`tests/simple/test_s1_spec.py::test_名前`)」。壊した変更は作業者の tmp の写しで当て、本物は壊したまま残さない。壊した変更で試験が 1 つも落ちなかったら、その行の落ちた試験の欄は「落ちなかった」と書き、問いとして返す(受け取りの検めはその行を落とす)。H の行は、確かめのコマンドと結果の 1 行の要約。

形: `| 番号 | 壊した変更 | 落ちた試験 |`

## 決まった制約
- 封印の置き場 `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読まない。2023-12-17T15:00Z より後のデータを読まない。
- `git worktree add` をしない。Do not commit. Do not push. git add もしない。
- フック・`.claude/settings.json`・`githooks/`・`.claude/agents/` を変えない。
- コード・コメント・ログ・文書にモデル名を書かない。出す文は日本語。
- 委任文に書かれていない選びが出たら、選ばずに問いとして返す(委任文の「決めてよいこと」に書かれたものだけは自分で決めてよい)。

## 終わる条件と上限

- 終わる条件: U1〜U8 の試験が飛ばし 0 で通り、H1〜H5 が通り、変異の表の全部の行で壊した変更が試験を落とした。
- 上限: 作業者 1 周、または 2 時間。試験が食い違う・決まらないと分かったら、その件は止めて問いとして返し、それに依らない部分は続ける。

## 報告

- 着手前の表
- 作ったファイルの一覧と行数(H5)
- 試験のコマンドと出力(`PYTHONPATH=src python -m pytest tests/simple tests/road`)
- H1〜H5 の確かめのコマンドと出力
- `## 変異の表`(上の形)
- 試験で決まらず作業者が決めた内部の形の一覧
- `## 問いとして返したこと`(行頭を `- Q1:` から番号にする。無ければ「問いとして返したことは無い。」と書く)
- 報告は返事に出す(リードが `docs/DISCUSSIONS/2026-10-08_simple_road/REPORT_s1.md` に写す)
- 日本語で。

## 途中の決め

作業者の問いにリードが答えたら、ここに `- Q数字:` の行で足し、印を取り直す。
