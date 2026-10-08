# 委任文: 単純な測りの道 S1 の直し — 作り終えた後の批評家 1 回目と L-824

種類: 作る

2 版目(事前の批評 1 回目 `DELEGATION_s1_fix_premortem1.md` の「次の版で直す」を入れた)。S1(`DELEGATION_s1.md`、承認 L-823)で作った `src/bot/bt/simple/` を、作り終えた後の批評家 1 回目(`docs/AUDITOR/VERDICTS/2026-10-08_simple_s1_critic1.md`、リードの応答 `CRITIC1_RESPONSE.md`)の [直す] と、オーナーの決め L-824 のとおりに直す。決まりの正本は `docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md`(この直しに合わせてリードが直した版)、受け入れはリードが書いた実行できる試験 `tests/simple/test_s1_fix_spec.py` と、S1 の試験 `tests/simple/test_s1_spec.py`。

## 着手前の表

作業者は、着手の前に「やろうとすること × オーナーの原文の該当語(逐語)」の 2 列の表を出す(CLAUDE.md §0.1 のまま)。この委任文は、検めと事前の批評の後にオーナーの承認を受けてから渡す(L-793「**委任文の検査が通ったのち、私に委任してよいか聞き、私の承認が得られてから委任すれば右の列は私の承認済のものになるでしょ。**」)。承認の逐語は末尾の `## オーナーの承認` の節にある。右の列には、承認の逐語を L-番号を引用の直前に間に何も挟まずに付けた形で書き、その行の根になる委任文の節の名前(例: 記す順を直す行は「直すもの」の 1、試験を通す行は「受け入れ」)を添える。委任文のどこにも書かれていないことをする行は右が空になり、その行は着手せず「問いとして返したこと」に書く。目的の節の L-791 は委任のやり方への指示なので、右の列の根にしない。

## 目的(オーナーの逐語)

- L-824「**(a)**」(同じ 1 分足で、前からの建玉を閉じる利確と新しい 1 段目の指値が両方約定したら、利確を先に帳簿に記す)
- L-819「**測定方法も残し方も検査もシンプルにできるはず**」
- L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」(数は帳簿のツールで約定から計算し、検査が確かめる)
- L-791「**測定に限らず全ての委任において、委任のミスでやり直しが発生しない委任文の書き方と仕組み**」
- リードの設計(オーナーの逐語ではない): 批評家の [直す] への直し(SPEC.md の「作り終えた後の批評家 1 回目」「リードの決め」の印の所): 安値 > 高値の足で止める・消えた注文の中身を記憶に持ち続けない・数の作り直しが壊した記録を通さず例外にもしない・git の版の印に帳簿のツールも入れる。

## 直すもの

コードは `src/bot/bt/simple/` の中だけを直す。

1. 1 本の足の中で約定させ記す順(SPEC.md §3): ① 成行 market → ② 親が前の足までに約定した利確 exit → ③ 指値 limit → ④ 段 level → ⑤ 親がこの足で約定した利確 exit。同じ組の中は番号を出した順(seq)。
2. 封印の境の行より先は読まない(SPEC.md §1。今のコードは正しく、試験を足しただけ。変えないで通ることを確かめる)。
3. 安値が高値より高い足は `read_bars` でも `run` でも `SimpleRoadError` で止める(SPEC.md §1)。
4. 数の作り直し `check_numbers`(SPEC.md §5 の 2): fills は見出しの行が決まった列と 1 字違わず同じで各行の欄の数が見出しと同じ・0 バイトは食い違い・trades はファイル全体を作り直した中身と 1 字違わず比べる・summary は 4 つの鍵ちょうどの辞書で値は Python の型(整数・小数・文字・真偽値)まで同じ・読めない入力はどんな例外も拾い、例外にせず食い違いの行で返す・約定 0 本の走らせは合格。
5. 消えた注文の中身を記憶に持ち続けない(SPEC.md §4。番号の使い回しの検めには番号だけを持つ。約定した注文は段・利確の検めに要る中身を持ってよい)。
6. `run_<側>.json` の git の版の印は、`src/` の下のどこかに未コミットの変更があれば付ける(SPEC.md §4)。

## 読んだ事実

| # | 事実 | 確かめ |
|---|---|---|
| データ | この委任は市場のデータを読まない。試験は tmp に書いた合成の足だけで走る(時刻 2020-01-01・2023-01-01・2023-11-14・2023-12-17、どれも封印の境より前。2020-01-01 は `datetime(2020, 1, 1, …)` で作る) | `grep -oh '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]' tests/simple/test_s1_spec.py tests/simple/test_s1_fix_spec.py \| sort -u` → `2023-01-01`・`2023-11-14`・`2023-12-17`(と `test_s1_fix_spec.py:289` の `datetime(2020, 1, 1, tzinfo=timezone.utc)`) |
| 既存の決まり | 直しの試験は、今のコードで 19 件落ち 11 件通る(落ちるのは記す順 4・安値 > 高値 2・数の作り直し 12・記憶 1。数の作り直しの「真偽値に」「小数に」は今のコードでは通るが、辞書の等号で比べる形にすると落ちる) | `PYTHONPATH=src python -m pytest tests/simple/test_s1_fix_spec.py` → `19 failed, 11 passed` |
| 既存の決まり | 受け入れの試験は、リードが捨てる実装を scratchpad に置いて全部通ることを確かめた(置いた実装はリポジトリに入れていない) | `PYTHONPATH=<捨てる実装> python -m pytest tests/simple/test_s1_spec.py tests/simple/test_s1_fix_spec.py -o pythonpath=<捨てる実装>` → `80 passed` |
| 既存の決まり | 消えた注文 1 つあたりの記憶の増え方は、今のコードで約 456 バイト、番号だけを持つ捨てる実装で約 96 バイト(試験の閾値は 200 バイト) | scratchpad の `s1fix/mem.py`(2,000 本と 12,000 本の tracemalloc の最大の差 ÷ 10,000)→ `455.7846` / `95.835` |
| 既存の決まり | 帳簿のツール `book` は同じ時刻の約定を並びの順に記し、利確が先なら取引が 1 回閉じる(F1 と同じ 3 本の約定) | `PYTHONPATH=src python3 -c "from bot.bt.road.ledger import book; a=[{'t_ns':60,'side':'buy','qty':0.009,'px':7000000.0,'ccy':'JPY'},{'t_ns':120,'side':'sell','qty':0.009,'px':7000100.0,'ccy':'JPY'},{'t_ns':120,'side':'buy','qty':0.009,'px':6999900.0,'ccy':'JPY'}]; print(book(a).summary['closed_trades'], book([a[0],a[2],a[1]]).summary['closed_trades'])"` → `1 0`(利確が先 / 新しい指値が先) |
| 既存の決まり | 今のコードの記す順は `fills.py` の `RANK`(market → limit → level → exit) | `src/bot/bt/simple/fills.py:8` |
| 既存の決まり | 今の数の作り直しは `OSError` などしか拾わず、summary が `[]` で例外になる | `src/bot/bt/simple/check.py:24-47` |
| 既存の決まり | 道の既存の試験は全部通る | `PYTHONPATH=src python -m pytest tests/road` → `315 passed` |
| 列の意味 | 残すファイルの列と、数の作り直しの決まり | `docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md:47-74` |

## 決めてよいこと・決めてはいけないこと

| 選び | 決め |
|---|---|
| 出力の置き場 | コードは `src/bot/bt/simple/` だけ。作業者が足したい試験は `tests/simple/test_s1_fix_extra.py` に置いてよい。走らせの出力は試験の tmp だけ |
| 分母・数え方 | この委任には無い(数えない。数は帳簿のツールのまま) |
| 比べの方法 | 約定の決まりの等号は SPEC.md §3 のとおり。数の作り直しは SPEC.md §5 の 2 のとおり(trades はファイル全体を 1 字違わず、summary は値と Python の型) |
| 確かめ方 | 試験 `tests/simple/test_s1_fix_spec.py` と `tests/simple/test_s1_spec.py` が飛ばし 0 で全部通り、`tests/road` が全部通る。`tests/simple/test_s2_spec.py`(二つ目の受け入れ)は作り直しの包みがまだ無いので 1 件の飛ばしになる。これは想定どおりで、この委任では見ない |
| 依存 | Python の標準ライブラリと、このリポジトリの `bot.bt.road.ledger`(帳簿のツール)だけ。S1 と同じ |
| 絞り方・選び方 | この委任には無い(測らない) |
| 単位・通貨のそろえ方 | S1 と同じ(値段は円、量は BTC、時刻は足のファイルの ts の文字列のまま) |
| 試験で決まらない内部の形 | 作業者が決めてよい(関数の分け方・記憶の持ち方のうち試験が見ない所)。決めたことを報告に書く |

## 変えないもの

- H1: 試験 `tests/simple/test_s1_spec.py`・`tests/simple/test_s1_fix_spec.py` と既存の試験を変えない。確かめ: `git diff --stat tests/` が空。
- H2: `src/bot/bt/simple/` の外のコードを変えない。確かめ: `git status --short src/` に出るのは `src/bot/bt/simple/` の下だけ。
- H3: 取引所の模型・core・道の土台・走らせを直に import しない。確かめ: `git ls-files src/bot/bt/simple | xargs grep -n "bot.bt.fill\|bot.bt.core\|bot.bt.road.strategy\|bot.bt.pipeline"` が空。
- H4: 道の既存の試験が全部通る。確かめ: `PYTHONPATH=src python -m pytest tests/road` が全部 passed。
- H5: 大きさ。直した後の `src/bot/bt/simple/` の行数の合計を、直す前(474 行)と並べて報告に出す。確かめ: `wc -l src/bot/bt/simple/*.py`。
- H6: git の版の印の検めが `src/` 全体を見る。確かめ: その行のコードを報告に出し、コードが git に渡す道が git に載っていることを `git -C src/bot/bt/simple ls-files --error-unmatch <コードが渡す道>` の終了コード 0 で示す(道を書き違えると git は出力も終了コードも黙るため。試験は無い。リポジトリのファイルを書き換えて確かめない)。

## 壊す場面

| 場面 | 書いたこと |
|---|---|
| 封印の境 | U2(境の行の次の行が壊れていても読まない) |
| 日・足・期間の境 | U1(親が前の足で約定した利確と、親がこの足で約定した利確で、記す順が違う) |
| 等号 | U1・U3(安値と高値が等しい平らな足 FLAT では止めない)・U1(同じ組の中は seq の順。r2 と x1 の seq の大小を入れ替えても記す順は組で決まる) |
| 欠け | U4(0 バイトのファイル・見出しだけのファイル・欄の足りない約定の行・約定 0 本の走らせ) |
| 参照の値が無い | U5(根・親を約定の前に取り下げ、段・利確だけを残すと止める) |
| 拒否・状態不明・届かない | U3(安値 > 高値の足で止める)・U4(読めない入力を例外にせず食い違いで返す) |
| 遅れ | U1(親の約定の後に出した利確と、親と一緒に出した利確の両方) |
| 交差と後からの変化 | U1(同じ足で前からの建玉を閉じる利確と新しい 1 段目が両方約定する) |
| 浮動小数・刻み・丸め | U4(summary の値の型: 整数と小数・整数と真偽値・数と文字) |
| 慣らし | この委任には無い(慣らしは戦略の仕事。S3 で扱う) |
| 宣言した値の書き換え | U4(見出し・鍵・値の型・行の数を書き換えると数の作り直しが食い違いを出す) |
| 並行の変更 | U7(二つ目の受け入れの試験 `tests/simple/test_s2_spec.py` が同じ置き場にあり、作り直しの包みが無いので 1 件の飛ばしになる。受け入れと報告の試験のコマンドは、この委任の試験のファイルと `tests/road` に絞る。S2 は直した SPEC.md から書くので、この直しの途中で SPEC.md を直したらリードが S2 の委任文にも書く) |

## 受け入れ

各項目は、挙げた試験が、試験を変えずに通ること。`PYTHONPATH=src python -m pytest tests/simple/test_s1_spec.py tests/simple/test_s1_fix_spec.py tests/road` で飛ばし 0。

- U1: 足の中の記す順(L-824): `tests/simple/test_s1_fix_spec.py::test_f1_exit_of_earlier_parent_before_new_limit`(4 通り)・`tests/simple/test_s1_fix_spec.py::test_f1_exit_of_same_bar_parent_stays_after`(良い側・悪い側)
- U2: 封印の境の行より先を読まない: `tests/simple/test_s1_fix_spec.py::test_f2_read_bars_does_not_read_past_seal_row`
- U3: 安値 > 高値の足で止める: `tests/simple/test_s1_fix_spec.py::test_f3_run_stops_on_low_above_high`・`tests/simple/test_s1_fix_spec.py::test_f3_read_bars_stops_on_low_above_high`
- U4: 数の作り直し: `tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records`(17 通り)・`tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_passes_true_zero_fill_run`
- U5: 取り下げた根・親: `tests/simple/test_s1_fix_spec.py::test_f5_withdrawn_reference_stops`(2 通り)
- U6: 消えた注文を記憶に持ち続けない: `tests/simple/test_s1_fix_spec.py::test_f6_gone_orders_are_not_kept`
- U7: S1 の受け入れが全部通ったまま: `tests/simple/test_s1_spec.py` の全部

## 変異の表

作業者が作り、報告に付ける。U1〜U7 と H1〜H6 の番号ごとに 1 行以上: 「作った物をわざと壊す変更(例: 記す順を元の market → limit → level → exit に戻す・消えた注文を持ち続ける・数の作り直しで見出しを見ない)」と「それで落ちた試験」。落ちた試験は 1 つずつ `tests/simple/<ファイル>::test_名前` の形で、省かずに全部書く(パラメータは `[...]` を付けてよい。「何件(…ほか)」のまとめは使わない)。壊した変更は作業者の scratchpad の写しで当て、本物は壊したまま残さない。写しを当てるときは `-o pythonpath=<写し>` も付ける(`pyproject.toml` の `pythonpath = ["src"]` が先に効くため。S1 の報告の事実)。壊した変更で試験が 1 つも落ちなかったら、別の壊し方に差し替えずに、その行の落ちた試験の欄に「落ちなかった」と書き、問いとして返す(「等価な変異」かどうかはリードが決める)。H の行は、確かめのコマンドと結果の 1 行の要約。

形: `| 番号 | 壊した変更 | 落ちた試験 |`

## 決まった制約
- 封印の置き場 `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読まない。2023-12-17T15:00Z より後のデータを読まない。
- `git worktree add` をしない。Do not commit. Do not push. git add もしない。
- フック・`.claude/settings.json`・`githooks/`・`.claude/agents/` を変えない。
- コード・コメント・ログ・文書にモデル名を書かない。出す文は日本語。
- 委任文に書かれていない選びが出たら、選ばずに問いとして返す(委任文の「決めてよいこと」に書かれたものだけは自分で決めてよい)。

## 終わる条件と上限

- 終わる条件: U1〜U7 の試験が飛ばし 0 で通り、H1〜H6 が通り、変異の表の全部の行で壊した変更が試験を落とした(落ちなかった行は問いとして返した)。
- 上限: 作業者 1 周、または 2 時間。試験が食い違う・決まらないと分かったら、その件は止めて問いとして返し、それに依らない部分は続ける。

## 報告

- 着手前の表
- 直したファイルの一覧と、直す前と後の行数(H5)
- 試験のコマンドと出力(`PYTHONPATH=src python -m pytest tests/simple/test_s1_spec.py tests/simple/test_s1_fix_spec.py tests/road`)
- H1〜H6 の確かめのコマンドと出力
- `## 変異の表`(上の形)
- 試験で決まらず作業者が決めた内部の形の一覧
- `## 問いとして返したこと`(行頭を `- Q1:` から番号にする。無ければ「問いとして返したことは無い。」と書く)
- 報告は返事に出す(リードが `docs/DISCUSSIONS/2026-10-08_simple_road/REPORT_s1_fix.md` に写す)
- 日本語で。コードの名前(関数・変数・例外の名前など)を出すときは、直後に日本語で何のことかを添える(L-824 の指摘)。リポジトリの根からの `grep -r`・`find .` をしない(`git ls-files` に絞る)。

## 途中の決め

作業者の問いにリードが答えたら、ここに `- Q数字:` の行で足し、印を取り直す。
