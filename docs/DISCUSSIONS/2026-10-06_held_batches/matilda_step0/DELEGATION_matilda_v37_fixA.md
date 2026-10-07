# 委任文: マチルダ(v37)の直し A — ブレイクの向きの直の入れ替わりと、道の土台の遅さ

種類: 作る

1 版目。1 本目の委任 `DELEGATION_matilda_v37.md`(5 版目、承認 L-810)で作った戦略と土台の、オーナーが直すと決めた 2 件(L-815)のうちの 2 つ。段の約定の決まり(L-815 の 1・L-816「1.a」)と交差の扱い(L-815 の 3・L-816「3.a」)は直し B の委任で、この委任には入れない。受け入れはリードが書いた実行できる試験 `tests/road/test_matilda_v37_r2_spec.py`。

## 着手前の表

作業者は、着手の前に「やろうとすること × オーナーの原文の該当語(逐語)」の 2 列の表を出す(CLAUDE.md §0.1 のまま)。この委任文は、検めと事前の批評の後にオーナーの承認を受けてから渡す(L-793「**委任文の検査が通ったのち、私に委任してよいか聞き、私の承認が得られてから委任すれば右の列は私の承認済のものになるでしょ。**」)。承認の逐語は末尾の `## オーナーの承認` の節にある。右の列には、承認の逐語と、その行の根になる委任文の節の名前(例: 入れ替わりを直す行は「作るもの」の 1、試験を通す行は「受け入れ」)を書く。委任文のどこにも書かれていないことをする行は右が空になり、その行は着手せず「問いとして返したこと」に書く。

## 目的(オーナーの逐語)

- L-815「**2.実際にあり得ない挙動に対応する必要はないけど、この挙動は本測定で起こりうる？**」(リードの答え: ブレイクの向きの直の入れ替わりは本測定の形(b_signal を使い、玉を持っている)で起こる。試験 `test_a1_break_flip_with_position_and_b_signal` の場面。今の戦略はそこで止まる)
- L-815「**4.直す**」(測定 1 本の時間が足の本数の 2 乗で伸びる土台の所を直す)
- L-813「**いや、測定一本にかかる時間は？**」(直した後の 1 本あたりの時間を測り直して見せる)
- L-805「**族に関してはリードの案でいいが、1本測る時間によって減らすか決めたい。**」(この直しの後の時間でオーナーが族を減らすか決める)
- L-791「**測定に限らず全ての委任において、委任のミスでやり直しが発生しない委任文の書き方と仕組み**」
- リードの設計(オーナーの逐語ではない): 入れ替わりの扱いは 1 本目の委任文の途中の決め Q1(リードの決め)のとおり。土台の直しは「記録を 1 字も変えずに、呼ぶたびに今までの注文を全部見直す所をなくす」。

## 作るもの

1. `src/bot/strategy/matilda_v37.py` の M7(ブレイクの判定)で、ブレイクの旗が ±1 から ∓1 に直に変わったとき(今は `RoadStrategyError` で止まる。`src/bot/strategy/matilda_v37.py:422-425`)、止めずに次のとおりにする(1 本目の委任文の途中の決め Q1):
   - 前の合図「ブレイク」b_k を、理由「逆向きのブレイク」で消す(消す時刻はこの判定の時刻)。
   - 旗を新しい向きにし、同じ判定で新しい合図「ブレイク」b_{k+1}(向き up / down、値は今の旗が 0 から ±1 になるときと同じ close と center)を出す。
   - b_signal は変えない(原典 `docs/legacy/matilda_for_TaroCamp37.py:943-944` が変えるのは旗だけ)。
   - その後の建ての旗・決済の旗・解除の判定は今の M8〜M10b のまま(新しい旗で計算する)。
   - 理由の語は定数にする(今の `END_ENTRY`・`END_BREAK` と同じ置き方。`src/bot/strategy/matilda_v37.py:50-52`)。
2. `src/bot/bt/road/strategy.py` の、呼ぶたびに今までの注文を全部見直す所(`_pending_exit` `src/bot/bt/road/strategy.py:604-616`・`_open_rows` `src/bot/bt/road/strategy.py:601-602`・`flatten` の取り消しの輪 `src/bot/bt/road/strategy.py:505`)を、出ていてまだ閉じていない注文だけを見る形に直す。記録(4 つの表)は 1 字も変えない。決済の量の和、取り消しを出す順(今は注文を受けた順)、`flatten` の待ちの並びを今と同じにする。

決まりの正本は、上の「作るもの」と試験 `tests/road/test_matilda_v37_r2_spec.py`(リードが書いた)。**試験は変えない。**試験どうし、試験とこの委任文が食い違う、または試験とこの委任文だけでは決まらない、と気づいたら、そこで止めて問いとして返す(それに依らない部分は続ける)。

## 読んだ事実

| # | 事実 | 確かめ |
|---|---|---|
| データ | この委任は市場のデータを読まない。試験と時間の測りは tmp の根の下に書いた合成の 1 分足だけで走る(時刻 2023-11-14、封印の境より前) | この委任には無い(合成の足だけ。実データは測る委任で使う) |
| 既存の決まり | 今の戦略は、ブレイクの旗が ±1 から ∓1 に直に変わると止まる | `src/bot/strategy/matilda_v37.py:422-425` |
| 既存の決まり | 原典は旗を直に入れ替える(上のブレイク中でも、下の線を割って b_signal ≠ 1 なら旗 = −1) | `docs/legacy/matilda_for_TaroCamp37.py:943-944` |
| 既存の決まり | 合図の消える理由は、消えた合図では空でも「データの終わり」でもない語が要る(検査 (iii)) | `src/bot/bt/road/check.py:794-803` |
| 既存の決まり | 受け入れの試験は、直す前のコードで、ブレイクの 2 件が「直に変わった」で止まり、遅さの試験が倍率で落ちる(5,000 個ずつで close 0.98 ミリ秒、10 個ずつの 10 倍を超える) | `PYTHONPATH=src python -m pytest tests/road/test_matilda_v37_r2_spec.py -k "a1 or cost"` → `RoadStrategyError: ブレイクの旗が 1 から -1 に直に変わった` 2 件・`AssertionError: ('close', {10: {'close': 5.43e-06, …}, 5000: {'close': 0.000984…, 'flatten': 0.0062…}})`・3 failed |
| 既存の決まり | 記録の指紋の試験は、直す前のコードで通る(約 3 分かかる。大半は試験の最後の置き場の検査 `check_outputs`) | `PYTHONPATH=src python -m pytest tests/road/test_matilda_v37_r2_spec.py -k record --durations=3` → `172.95s call …test_a2_record_unchanged_on_walk`・1 passed |
| 既存の決まり | 道の既存の試験は今全部通る | `PYTHONPATH=src python -m pytest tests/road --deselect tests/road/test_matilda_v37_r2_spec.py` → 315 passed, 4 deselected |
| 既存の決まり | 測定 1 本の時間は、足が 2 倍で約 4.7 倍に伸びる(5,000 本 22.0 秒・20,000 本 174.8 秒・40,000 本 824.7 秒) | `docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/TIMING_L813.md:7-9` |
| 既存の決まり | 走らせの中で呼び出しが本数の 2 乗で増えるのは土台の `_is_open`(1,250 本 2,539,484 回 → 5,000 本 36,594,742 回)。core の `renew` は本数に比例(1,630,770 回 → 6,348,590 回)。自分の時間の多い順の上 15 行を 2 つの本数で比べた推定で、走らせの全部を見たのではない | `PYTHONPATH=src python3 docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/prof_run.py 1250` → `2539484 … strategy.py:597(_is_open)`・`1630770 … values.py:1879(renew)`、同じく `5000` → `36594742 … _is_open`・`6348590 … renew` |
| 既存の決まり | 注文の行の state と sent_t_ns を書き換える所は、知らせを受けた時(`src/bot/bt/road/strategy.py:311-313`)、出した時(`src/bot/bt/road/strategy.py:663-665`)、量が 0 で出さない行(`src/bot/bt/road/strategy.py:444`・`src/bot/bt/road/strategy.py:465`・`src/bot/bt/road/strategy.py:519`・`src/bot/bt/road/strategy.py:550`・`src/bot/bt/road/strategy.py:580`)、土台を通さない強制の注文の行(`src/bot/bt/road/strategy.py:278`)だけ | `grep -n 'state"\] = \|state=\|sent_t_ns"\] = ' src/bot/bt/road/strategy.py` → 278・313・444・465・519・550・580・663・665 の行 |
| 既存の決まり | 出ている注文 = 出した時刻があり、状態が PENDING_NEW・OPEN・PENDING_CANCEL・STATE_UNKNOWN のどれか | `src/bot/bt/road/strategy.py:130`・`src/bot/bt/road/strategy.py:597-599` |
| 既存の決まり | 状態不明・取り消しの拒否の場面の既存の試験がある | `grep -ln "STATE_UNKNOWN\|PENDING_CANCEL\|cancel_reject" tests/road/*.py` → `tests/road/test_road_record.py` |
| 列の意味 | 記録の指紋 = 4 つの表(signals・orders・fills・trades)の置き場のファイルを gzip から戻した中身を、この順に sha256 に足したもの | `tests/road/test_matilda_v37_r2_spec.py:110-114` |
| 列の意味 | 時間の測り `timing_probe.py` は、合成の乱歩の 1 分足(σ 3,000 円、seed 0)・原典の値・self_trade = cancel_both で 1 回の実行(良い側・悪い側の両方)の秒を出す | `docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/timing_probe.py:1` |

## 決めてよいこと・決めてはいけないこと

| 選び | 決め |
|---|---|
| 出力の置き場 | 直すのは `src/bot/strategy/matilda_v37.py` と `src/bot/bt/road/strategy.py` だけ。作業者が足したい試験は `tests/road/test_matilda_v37_fixA_extra.py` に置いてよい。走らせの出力は試験と測りの tmp だけ(`docs/`・`backtest_data/` に書かない) |
| 分母・数え方 | 1 本あたりの時間 = `timing_probe.py` が出す秒 ÷ 本数。比べるのは 5,000 本と 20,000 本 |
| 比べの方法 | 記録は指紋の一致(1 字も違わない)。時間は 20,000 本の 1 本あたり ≦ 5,000 本の 1 本あたり × 1.5 |
| 確かめ方 | 試験 `tests/road/test_matilda_v37_r2_spec.py` と `tests/road` の全部が飛ばし 0 で通り、時間の測りのコマンドと出力を報告に出す |
| 依存 | Python の標準ライブラリと、このリポジトリの今あるもの。新しい外の包みを入れない |
| 絞り方・選び方 | この委任には無い(測らない。族を減らすかはオーナーが時間を見て決める。L-805) |
| 単位・通貨のそろえ方 | 時間は秒(1 本あたりはミリ秒)。この直しは値段・量の単位を変えない |
| 試験で決まらない内部の形 | 作業者が決めてよい(出ている注文の持ち方・関数の分け方・定数の名前)。決めたことを報告に書く |

## 変えないもの

- H1: 試験 `tests/road/test_matilda_v37_r2_spec.py`・`tests/road/test_matilda_v37_spec.py` と、既存の試験(`tests/road/` の今あるファイル)を変えない。確かめ: `git diff --stat tests/` が空(足した `tests/road/test_matilda_v37_fixA_extra.py` は新しいファイルなので出ない。`git status --short tests/` に出るのはそれだけ)。
- H2: 道の試験が全部通る。確かめ: `PYTHONPATH=src python -m pytest tests/road` が全部 passed(飛ばし 0)。
- H3: 道の記録の表の列を変えない。確かめ: `PYTHONPATH=src python -c "from bot.bt.road.tables import SCHEMA; print({k: [c[0] for c in v['columns']] for k, v in SCHEMA['tables'].items()})"` の出力が、直す前と直した後で同じ。
- H4: 約定の決まり・取引所の模型・走らせ・検査・表を変えない。確かめ: `git diff --stat src/bot/bt/fill src/bot/bt/core src/bot/bt/pipeline.py src/bot/bt/road/check.py src/bot/bt/road/tables.py src/bot/bt/road/ledger.py` が空。
- H5: 戦略の直しは M7 の入れ替わりの所だけ。確かめ: `git diff src/bot/strategy/matilda_v37.py` の変わった行が、M7 の旗の入れ替わりの枝と理由の定数だけ(報告に diff を出す)。

## 壊す場面

| 場面 | 書いたこと |
|---|---|
| 封印の境 | この委任には無い(合成の足だけで走らせ、時刻は 2023-11-14。実データを読まない) |
| 日・足・期間の境 | U1(入れ替わりの後の合図がデータの終わりまで消えない → 理由「データの終わり」)・U1 の 2 件目(入れ替わりの判定の次の足で決済が約定し、その次の判定で建ての合図が消える) |
| 等号 | U1 の 2 件目(入れ替わりの 1 つ前の判定が last = 中心 ちょうど。「last < 中心」でないので解除しない) |
| 欠け | この委任には無い(足の抜けの扱いを変えない。1 本目の受け入れの足の抜けの試験 `test_u9_foot5_missing_minute` などが H2 で通る) |
| 参照の値が無い | この委任には無い(旗が ±1 のときは「ブレイク」の合図が必ず出ている。M7。出ていなければ今のまま止める) |
| 拒否・状態不明・届かない | U3 と H2(出ている注文に PENDING_CANCEL・STATE_UNKNOWN も入る。状態不明・取り消しの拒否の既存の試験 `tests/road/test_road_record.py` が通る) |
| 遅れ | この委任には無い(遅れ 0 の決まりを変えない。H4) |
| 交差と後からの変化 | U2(注文の状態が後から出ている → 閉じた に変わる走らせ 2,000 本で記録が同じ)・U1 の 2 件目(入れ替わりの判定で建ての合図が入れ替わり、決済が出る) |
| 浮動小数・刻み・丸め | U2(決済の量の和は今の Decimal のまま。記録の指紋が同じ) |
| 慣らし | この委任には無い(慣らしの扱いを変えない。1 本目の受け入れの `test_u10_no_decision_before_warm` が H2 で通る)。土台は注文が 0 個のときも今と同じ(H2 の既存の試験) |
| 宣言した値の書き換え | U2(記録の指紋は直す前のコードで取った値を試験に書いた。土台の直しで記録が変われば落ちる) |
| 並行の変更 | この委任には無い(作業者は 1 名。未コミットの変更は `docs/AUDITOR/TRACE/` の 1 本だけで、触れるファイルと重ならない。`git status --short` で確かめた) |

## 受け入れ

各項目は、試験 `tests/road/test_matilda_v37_r2_spec.py` の挙げた試験が、試験を変えずに通ること。全体で飛ばし 0。

- U1: ブレイクの向きの直の入れ替わり: `test_a1_break_flip_ends_old_signal_and_starts_new`・`test_a1_break_flip_with_position_and_b_signal`
- U2: 土台の直しで記録が変わらない: `test_a2_record_unchanged_on_walk`
- U3: 出ていない注文が溜まっても close と flatten が重くならない: `test_a2_cost_does_not_grow_with_closed_orders`
- U4: 1 本あたりの時間が本数で伸びない: `PYTHONPATH=src python3 docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/timing_probe.py 5000 0 3000` と `… 20000 0 3000` を打ち、20,000 本の 1 本あたり ≦ 5,000 本の 1 本あたり × 1.5。コマンドと出力を報告に出す。外れたら、自分の時間の多い順の上 15 行(`prof_run.py 5000` と `prof_run.py 20000`)を付けて問いとして返す(土台の外を直さない)

## 変異の表

作業者が作り、報告に付ける。U1〜U4 と H1〜H5 の番号ごとに 1 行以上: 「直した物をわざと壊す変更(例: 理由の語を「中心に戻った」にする)」と「それで落ちた試験(`tests/road/test_matilda_v37_r2_spec.py::test_名前`)」。U4 は落ちた試験の欄に、壊した変更で打った時間の測りの出力の 1 行を書く。壊した変更は作業者の tmp の写しで当て、本物は壊したまま残さない。壊した変更で試験が 1 つも落ちなかったら、その行の落ちた試験の欄は「落ちなかった」と書き、問いとして返す(受け取りの検めはその行を落とす)。H の行は、確かめのコマンドと結果の 1 行の要約。

形: `| 番号 | 壊した変更 | 落ちた試験 |`

## 決まった制約
- 封印の置き場 `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読まない。2023-12-17T15:00Z より後のデータを読まない。
- `git worktree add` をしない。Do not commit. Do not push. git add もしない。
- フック・`.claude/settings.json`・`githooks/`・`.claude/agents/` を変えない。
- コード・コメント・ログ・文書にモデル名を書かない。出す文は日本語。
- 委任文に書かれていない選びが出たら、選ばずに問いとして返す(委任文の「決めてよいこと」に書かれたものだけは自分で決めてよい)。

## 終わる条件と上限

- 終わる条件: U1〜U3 の試験が飛ばし 0 で通り、U4 の時間の比べが通り、H1〜H5 が通り、変異の表の全部の行で壊した変更が試験を落とした。
- 上限: 作業者 1 周、または 2 時間。試験が食い違う・決まらないと分かったら、その件は止めて問いとして返し、それに依らない部分は続ける。

## 報告

- 着手前の表
- 直したファイルの一覧
- 試験のコマンドと出力(`PYTHONPATH=src python -m pytest tests/road`)
- U4 の時間の測りのコマンドと出力、1 本あたりの時間と比
- H1〜H5 の確かめのコマンドと出力(H5 は `git diff src/bot/strategy/matilda_v37.py`)
- `## 変異の表`(上の形)
- 試験で決まらず作業者が決めた内部の形の一覧
- `## 問いとして返したこと`(行頭を `- Q1:` から番号にする。無ければ「問いとして返したことは無い。」と書く)
- 報告は返事に出す(リードが `docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/REPORT_matilda_v37_fixA.md` に写す)
- 日本語で。

## 途中の決め

作業者の問いにリードが答えたら、ここに `- Q数字:` の行で足し、印を取り直す。
