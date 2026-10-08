# 委任文: 単純な測りの道 直し 2(走らせの側)— L-828 の順・建玉を閉じる指値の印

種類: 作る

2 版目(事前の批評 1 回目の [直す] を入れた)。走らせ `src/bot/bt/simple/` を、オーナーの決め L-828 と、作り終えた後の批評家(直しの後の 1 回目、`docs/AUDITOR/VERDICTS/2026-10-08_simple_s1_fix_critic1.md`、応答 `CRITIC_FIX1_RESPONSE.md`)の [直す] のとおりに直す。決まりの正本は `docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md`(この直しに合わせてリードが直した版)、受け入れはリードが書いた実行できる試験 `tests/simple/test_s1_fix2_spec.py` と、前からの試験 `tests/simple/test_s1_spec.py`・`tests/simple/test_s1_fix_spec.py`。作り直しの側(`src/bot/bt/simple_refill/`)は別の委任(`DELEGATION_fix2_refill.md`)で、別の作業者が直す。

## 着手前の表

作業者は、着手の前に「やろうとすること × オーナーの原文の該当語(逐語)」の 2 列の表を出す(CLAUDE.md §0.1 のまま)。この委任文は、検めと事前の批評の後にオーナーの承認を受けてから渡す(L-793「**委任文の検査が通ったのち、私に委任してよいか聞き、私の承認が得られてから委任すれば右の列は私の承認済のものになるでしょ。**」)。承認の逐語は末尾の `## オーナーの承認` の節にある。右の列には、承認の逐語を L-番号を引用の直前に間に何も挟まずに付けた形で書き、その行の根になる委任文の節の名前(例: 記す順を直す行は「直すもの」の 1、試験を通す行は「受け入れ」)を添える。委任文のどこにも書かれていないことをする行は右が空になり、その行は着手せず「問いとして返したこと」に書く。目的の節の L-791 は委任のやり方への指示なので、右の列の根にしない。

## 目的(オーナーの逐語)

- L-828「**ⅱ**」(前からの建玉を閉じる利確が始値で約定するときだけ、同じ足の成行より先に記す。範囲の内なら成行が先)
- L-824「**(a)**」(同じ 1 分足で、前からの建玉を閉じる利確と新しい 1 段目が両方約定したら、利確を先に記す)
- L-819「**測定方法も残し方も検査もシンプルにできるはず**」
- L-791「**測定に限らず全ての委任において、委任のミスでやり直しが発生しない委任文の書き方と仕組み**」
- リードの設計(オーナーの逐語ではない): 建玉の全部を閉じる指値も L-824 の「利確」に入るとリードが読み、戦略が付ける close の印で見分ける(SPEC.md §3)。印は limit にだけ、値は true だけ。注文の記録の末尾に close の列を足す(SPEC.md §4)。印の無い指値はすべて ③ に置き、建玉を持ったまま足す指値と利確が同じ足で約定する場面にも同じ順を当てる(SPEC.md:40。L-824 の問いは「新しい 1 段目」の指値だけだったのを、リードが広げた)。

## 直すもの

コードは `src/bot/bt/simple/` の中だけを直す。

1. 1 本の足の中で約定させ記す順(SPEC.md §3): ⓪ 前からの建玉を閉じる注文(親が前の足までに約定した exit・close の印の付いた limit)のうち始値で約定するもの → ① market → ② 前からの建玉を閉じる注文のうち範囲の内で約定するもの → ③ limit(close の印の無いもの)→ ④ level → ⑤ 親がこの足で約定した exit。同じ組の中は seq の順。始値か範囲の内かは、足に入る時点で値段と足から決まる。
2. close の印(SPEC.md §3): 注文の辞書の `"close": True` を受ける。limit 以外に付いていたら止める。値が `True` でなければ止める(`False`・`1`・文字も止める)。同じ番号の比べの中身に close の印を入れる(印だけを変えて同じ番号で返したら止める)。
3. 注文の記録 `orders_<側>.csv` の末尾に列 `close` を足す(SPEC.md §4。印の付いた limit は `1`、それ以外は空)。
4. 段に付けた利確も、親の段が前の足までに約定していれば ② の組(今のコードで正しい。試験 G5 で確かめる)。

## 読んだ事実

| # | 事実 | 確かめ |
|---|---|---|
| データ | この委任は市場のデータを読まない。試験は tmp に書いた合成の足だけで走る(時刻 2023-11-14、封印の境より前) | `tests/simple/test_s1_fix2_spec.py:25`(`def ts(k)` = 2023-11-14T22:10 から 1 分ずつ) |
| 既存の決まり | 直しの試験は、今のコードで 21 件落ち 10 件通る(通るのは、印の無い指値の順・範囲の内の閉じる指値と成行・段に付けた利確・安値ちょうどの売りの閉じる指値・高値ちょうどの買いの利確の 5 つの試験の良い側・悪い側) | `PYTHONPATH=src python -m pytest tests/simple/test_s1_fix2_spec.py` → `21 failed, 10 passed` |
| 既存の決まり | 受け入れの試験は、リードが捨てる実装を scratchpad に置いて全部通ることを確かめた(置いた実装はリポジトリに入れていない。渡す前に scratchpad から消すので、作業者はこの行を打ち直せない。リードだけの確かめ) | `PYTHONPATH=<捨てる実装> python -m pytest tests/simple/test_s1_spec.py tests/simple/test_s1_fix_spec.py tests/simple/test_s1_fix2_spec.py -o pythonpath=<捨てる実装>` → `116 passed` |
| 既存の決まり | 今のコードの組の番号は `fills.py` の `_rank`(足に入る時点の状態で決める) | `src/bot/bt/simple/fills.py:47-55` |
| 既存の決まり | 今の注文の記録の列は 12 列 | `src/bot/bt/simple/run.py:17` |
| 既存の決まり | 今のコードは注文の辞書の知らない鍵を無視する(S1 の途中の決め Q8) | `docs/DISCUSSIONS/2026-10-08_simple_road/DELEGATION_s1.md:136` |
| 既存の決まり | 道の既存の試験は全部通る | `PYTHONPATH=src python -m pytest tests/road` → `315 passed` |
| 列の意味 | 記す順・close の印・注文の記録の列 | `docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md:37-42`・`docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md:58` |

## 決めてよいこと・決めてはいけないこと

| 選び | 決め |
|---|---|
| 出力の置き場 | コードは `src/bot/bt/simple/` だけ。作業者が足したい試験は `tests/simple/test_s1_fix2_extra.py` に置いてよい |
| 分母・数え方 | この委任には無い(数えない) |
| 比べの方法 | 約定の決まりの等号は SPEC.md §3 のとおり(範囲の内 = 安値 ≦ 値段 ≦ 高値。始値で約定 = 約定する向きに範囲の外) |
| 確かめ方 | `PYTHONPATH=src python -m pytest tests/simple/test_s1_spec.py tests/simple/test_s1_fix_spec.py tests/simple/test_s1_fix2_spec.py tests/road` が飛ばし 0 で全部通る。`tests/simple/test_s2_spec.py`(作り直しの受け入れ)は、作り直しの側の直しが済むまで落ちる。これは想定どおりで、この委任では見ない |
| 依存 | Python の標準ライブラリと `bot.bt.road.ledger` だけ(今のまま) |
| 絞り方・選び方 | この委任には無い(測らない) |
| 単位・通貨のそろえ方 | 今のまま(値段は円、量は BTC、時刻は足のファイルの ts の文字列) |
| 試験で決まらない内部の形 | 作業者が決めてよい。決めたことを報告に書く |

## 変えないもの

- H1: 試験 `tests/simple/*.py` と既存の試験を変えない。確かめ: `git status --short tests/` が空(足してよい `tests/simple/test_s1_fix2_extra.py` だけは出てよい)。
- H2: `src/bot/bt/simple/` の外のコードを変えない。確かめ: `git status --short src/` に出るのは `src/bot/bt/simple/` の下だけ。
- H3: 取引所の模型・core・道の土台・走らせを直に import しない(今のまま)。確かめ: `(git ls-files src/bot/bt/simple; git ls-files -o --exclude-standard src/bot/bt/simple) | xargs grep -nE "bot\.bt\.(fill|core|road\.strategy|pipeline)|from \.\.(fill|core|pipeline)|from \.\.road(\.strategy| import strategy)"` が空(一覧は空でない)。
- H4: 道の既存の試験が全部通る。確かめ: `PYTHONPATH=src python -m pytest tests/road` が全部 passed。
- H5: 大きさ。直した後の `src/bot/bt/simple/` の行数の合計を、直す前(534 行)と並べて報告に出す。確かめ: `wc -l src/bot/bt/simple/*.py`。

## 壊す場面

| 場面 | 書いたこと |
|---|---|
| 封印の境 | この委任には無い(封印の境の扱いは変えない。U4 の前からの試験が見る) |
| 日・足・期間の境 | U1(親が前の足で約定した利確・段に付けた利確と、この足で親が約定した利確で組が違う) |
| 等号 | U1(閉じる注文の値段が安値・高値ちょうどなら範囲の内 = ②、約定する向きに外れれば始値 = ⓪。G1・G7 は範囲の外、G2 は範囲の内、G8 は安値・高値ちょうど) |
| 欠け | U2(印の無い指値は ③ のまま。G2 の印の無い場面)・U3(約定せずに消えた・データの終わりまで残った印付きの指値も close の列は `1`。G9) |
| 参照の値が無い | この委任には無い(根・親の参照の決まりは変えない。U4 の前からの試験が見る) |
| 拒否・状態不明・届かない | U2(limit 以外の印・true でない印・同じ番号で印を変える、で止める)・U3(約定しない印付きの指値の記録。G9) |
| 遅れ | U1(前の足までに親が約定した利確と、この足で親が約定した利確) |
| 交差と後からの変化 | U1(同じ足で前からの建玉を閉じる注文・成行・新しい 1 段目が約定する。売りの閉じる注文は G1・G2・G3、買いの閉じる注文(空売りを閉じる側)は G7) |
| 浮動小数・刻み・丸め | この委任には無い(値段の計算は変えない。U4 の前からの試験が見る) |
| 慣らし | この委任には無い(慣らしは戦略の仕事) |
| 宣言した値の書き換え | U2(同じ番号で印を変えたら止める)・U3(注文の記録の close の列) |
| 並行の変更 | U4(作り直しの側 `src/bot/bt/simple_refill/` の直しは別の置き場で、リードがこの委任の結果を受け取りコミットした後に、別の作業者に渡す。この委任の間、リードとほかの担当は `src/` と `tests/` を変えない。渡す時点で `git status --short` は空。この委任は `src/bot/bt/simple/` だけを変え、作り直しの受け入れ `tests/simple/test_s2_spec.py` は見ない) |

## 受け入れ

各項目は、挙げた試験が、試験を変えずに通ること。`PYTHONPATH=src python -m pytest tests/simple/test_s1_spec.py tests/simple/test_s1_fix_spec.py tests/simple/test_s1_fix2_spec.py tests/road` で飛ばし 0。

- U1: 足の中の記す順(L-824・L-828): `tests/simple/test_s1_fix2_spec.py::test_g1_exit_at_open_before_market`・`tests/simple/test_s1_fix2_spec.py::test_g2_close_limit_before_new_limit`・`tests/simple/test_s1_fix2_spec.py::test_g3_close_limit_at_open_before_market`・`tests/simple/test_s1_fix2_spec.py::test_g3_close_limit_in_range_after_market`・`tests/simple/test_s1_fix2_spec.py::test_g5_exit_on_level_of_earlier_bar_before_new_limit`・`tests/simple/test_s1_fix2_spec.py::test_g7_buy_exit_at_open_before_market`・`tests/simple/test_s1_fix2_spec.py::test_g7_buy_close_limit_before_new_limit`・`tests/simple/test_s1_fix2_spec.py::test_g7_buy_close_limit_at_open_before_market`・`tests/simple/test_s1_fix2_spec.py::test_g8_sell_close_at_low_is_in_range`・`tests/simple/test_s1_fix2_spec.py::test_g8_buy_exit_at_high_is_in_range`(どれも良い側・悪い側)
- U2: close の印の受け方と止め方: `tests/simple/test_s1_fix2_spec.py::test_g2_unmarked_limit_keeps_seq_order`・`tests/simple/test_s1_fix2_spec.py::test_g4_close_mark_stops`(7 通り)
- U3: 注文の記録の close の列: `tests/simple/test_s1_fix2_spec.py::test_g6_orders_close_column`・`tests/simple/test_s1_fix2_spec.py::test_g9_close_column_on_unfilled_orders`
- U4: 前からの受け入れが全部通ったまま: `tests/simple/test_s1_spec.py` と `tests/simple/test_s1_fix_spec.py` の全部

## 変異の表

作業者が作り、報告に付ける。U1〜U4 と H1〜H5 の番号ごとに 1 行以上: 「作った物をわざと壊す変更(例: 閉じる注文を始値でも成行の後にする・買いの閉じる注文を常に ② にする・値段が安値ちょうどの閉じる注文を ⓪ にする・close の列を約定した行にだけ書く・close の印を見ない・同じ番号の比べから印を外す)」と「それで落ちた試験」。落ちた試験は 1 つずつ `tests/simple/<ファイル>::test_名前` の形で、省かずに全部書く(パラメータは `[...]` を付けてよい。「何件(…ほか)」のまとめは使わない)。壊した変更は作業者の scratchpad の写しで当て、本物は壊したまま残さない。写しを当てるときは `-o pythonpath=<写し>` も付ける。壊した変更で試験が 1 つも落ちなかったら、別の壊し方に差し替えずに、その行の落ちた試験の欄に「落ちなかった」と書き、問いとして返す(その欄には経緯の文を書かない)。H の行は、確かめのコマンドと結果の 1 行の要約。「壊した変更」の欄には、実際に当てた変更をそのまま書く(書いた変更と当てた変更が違うと、試験が見ていない所を見ているように読めてしまう。二つ目の作り終えた後の批評家)。

形: `| 番号 | 壊した変更 | 落ちた試験 |`

## 決まった制約
- 封印の置き場 `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読まない。2023-12-17T15:00Z より後のデータを読まない。
- `git worktree add` をしない。Do not commit. Do not push. git add もしない。
- フック・`.claude/settings.json`・`githooks/`・`.claude/agents/` を変えない。
- コード・コメント・ログ・文書にモデル名を書かない。出す文は日本語。
- 委任文に書かれていない選びが出たら、選ばずに問いとして返す(委任文の「決めてよいこと」に書かれたものだけは自分で決めてよい)。

## 終わる条件と上限

- 終わる条件: U1〜U4 の試験が飛ばし 0 で通り、H1〜H5 が通り、変異の表の全部の行で壊した変更が試験を落とした(落ちなかった行は問いとして返した)。
- 上限: 作業者 1 周、または 2 時間。試験が食い違う・決まらないと分かったら、その件は止めて問いとして返し、それに依らない部分は続ける。

## 報告

- 着手前の表
- 直したファイルの一覧と、直す前と後の行数(H5)
- 試験のコマンドと出力(`PYTHONPATH=src python -m pytest tests/simple/test_s1_spec.py tests/simple/test_s1_fix_spec.py tests/simple/test_s1_fix2_spec.py tests/road`)
- H1〜H5 の確かめのコマンドと出力
- `## 変異の表`(上の形)
- 試験で決まらず作業者が決めた内部の形の一覧
- `## 問いとして返したこと`(行頭を `- Q1:` から番号にする。無ければ「問いとして返したことは無い。」と書く)
- 報告は返事に出す(リードが `docs/DISCUSSIONS/2026-10-08_simple_road/REPORT_fix2_run.md` に写す)
- 日本語で。コードの名前(関数・変数・例外の名前など)を出すときは、直後に日本語で何のことかを添える。リポジトリの根からの `grep -r`・`find .` をしない。`git ls-files` の一覧を使うときも封印の置き場を除く(`git ls-files -- . ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed'`)。

## 途中の決め

作業者の問いにリードが答えたら、ここに `- Q数字:` の行で足し、印を取り直す。
