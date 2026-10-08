委任文 sha256: 30ba4b04be7385f411efa65ebbb15d7c606fa526af3640fe501cee71b62d254c

<!-- 事前の批評 2 回目(試験の受け入れの形の 2 回目 = 上限)。担当の返事を逐語で写し、各指摘の下にリードの「応答:」を足した(10-08)。最後の回なので「直した」は書かず、直しは委任文の `## 事前の批評の後の変更` に書いた。 -->

(`python3 scripts/delegation/check_delegation.py docs/DISCUSSIONS/2026-10-08_simple_road/DELEGATION_s1.md --print-hash` → 同じ値。検めの本体は「最後の回の記録 DELEGATION_s1_premortem1.md の 1 行目 23c1296a74db… が、今の委任文の … 30ba4b04be73… と違う / 不合格: 失敗 1 件」を出す。この回の記録がまだ無いためで、指摘ではなく知らせ。)

## とくに見てほしいことへの答え
- 1 回目の「直した」20 件: 19 件は本文・SPEC.md・試験に入っていた(maker の行を外した SPEC:40、刻みの読み SPEC:25、3 つの印 SPEC:31・32・39、並行 SPEC:67・委任文:79、売りの段 +100 test:252、根が段の段 test:253、データの終わり test:331-340、同じ足の順 test:344-351、meta の seal test:37・SPEC:50、repr SPEC:53、消えた番号 SPEC:20・test:254、seq SPEC:47、from/to 空 SPEC:47、合図の終わり SPEC:49、依存 SPEC:66・委任文:60、全部決済は limit SPEC:38、封印はデータの終わり SPEC:11・test:224-231、trades の書き換え test:297-309、次の足の始値 test:355-365)。入っていない 1 件は問1 の 1 行目。
- 試験の期待の値: SPEC.md の決まりから手で計算し直し(T7 の 12 通りは、それぞれ狙った止める場面の 1 つだけに当たる。T8 は r 6,999,800(open)・x は足 2 の高値 6,999,800 より上で約定せず足 2 の判定で消える・m は足 3 の始値 7,000,000、0.009×200 = 1.8。T9 は w (ts1,ts1)・v ("","")・合図は空と「データの終わり」、z→a の順、r→l2 6,999,500(open)→x 7,000,000(open))、全部合った。さらにリポジトリの外で独立の試作を書き、試験の import の 1 行だけ替えて走らせた: `MUT= PYTHONPATH=/home/user/trade/src:. python3 -m pytest -p no:cacheprovider -q test_proto.py` → `41 passed in 0.23s`。分かれの確かめ: 根が limit かの確かめを外すと `test_t7_stops[根が段の段]` だけが落ち、順を exit→level にすると `test_t4_exit_on_level` だけが落ちた(売買と向きの 2 つは分かれている)。
- S2 が書けるか: orders の列(seq・form・side・qty・px_calc・root・offset・parent・from_ts・to_ts)と run.json の tick と足だけから fills を作り直す試作を書き、41 の走らせ全部で fills と 1 字違わず一致した(`test_s2.py` → `41 passed in 0.27s`)。ただし case の名前(range / open / anchor_bar / entry_bar / market)をどの決まりが出すかは試験から読んで書いた。SPEC.md だけからは決まらない(問3 の 1 行目)。

## 問1 着手前の表
- [直す] 1 回目の「親が約定した後に出た利確」の指摘への応答は、委任文:18 の一覧から外しただけで、SPEC.md:37 には今も「リードの決め」の印もオーナーの逐語も無い。L-770(b) は「**建ての指値と一緒に決済の指値を出しておき**」の場面だけ(OWNER_LOG.md:830)なので、SPEC.md:4「新しく決める約定の決まりは無い」と食い違い、オーナーは承認のときにリードの決めとして見られない。改善案: SPEC.md:37 に印を付け、委任文:18 の一覧に戻す。
  応答: 次の版で直す(SPEC の該当の行に「リードの決め」の印を付け、委任文の一覧に戻した)
- [直す] 印の無いリードの決めがまだある: 「知らない形」で止める(test:257)は SPEC.md:36 の止める一覧に無い。SPEC.md:38 の「建玉を超えて決済しないのは戦略の仕事」「建玉の全部を決済する指値は exit ではなく limit で出す」にも印が無い(L-816「3.a」が言うのは交差だけ。OWNER_LOG.md:876)。
  応答: 次の版で直す(「知らない形」を止める一覧に足し、建玉を超えない・全部の決済は limit の 2 つに「リードの決め」の印を付けた)
- 目的の節の逐語(L-819・L-821・L-816・L-817・L-754・L-791・L-793)は OWNER_LOG.md:879・881・876・877・813・851・853 と一致した。

## 問2 壊す場面
- [直す] 「並行の変更 = この委任には無い」(委任文:79)だが、起きうる。残すファイルは名前に `_<側>` が付く(SPEC.md:47-49)のに、run.json だけは 1 つで、中に side を持つ(SPEC.md:50)。SPEC.md:43「1 回の走らせ = 1 つのディレクトリ」と側の付いた名前からは、良い側と悪い側を同じディレクトリに書く読みが出る。その場合、後の走らせが run.json を上書きする(並行に走らせても同じ)。試験は `out = tmp_path / side`(test:65)で側ごとに分けているので見つからない。改善案: 「側ごとに 1 つのディレクトリ」か「run_<側>.json」のどちらかを SPEC に書く。
  応答: 次の版で直す(run.json を run_<側>.json にした。良い側と悪い側は同じディレクトリに書ける。試験も run_<側>.json を読む)
- [直す] 「浮動小数・刻み・丸め U2(買いと売りの切り捨て…)」(委任文:76)の期待は、実際より広い。売りで切り捨てを試しているのは段(test:122-128)だけ。売りの limit と exit の値段は、どの試験でも整数。試作で売りの limit・exit を切り上げにしても(`MUT=sellceil` → `41 passed in 0.22s`)、exit を切り捨てないままにしても(`MUT=exitnofloor` → `41 passed in 0.23s`)、全部通った。L-783 の(1)は「買い・売りとも」(OWNER_LOG.md:843)。
  応答: 次の版で直す(試験 `test_t2_sell_limit_and_exit_floored` を足した。売りの limit 6,999,700.9 → 6,999,700、売りの exit 6,999,800.7 → 6,999,800)
- [直す] 「等号」と「遅れ」の行に、良い側で親の足に、約定する向きに範囲の外の exit(例: 売りの exit < 安値)の場面が無い。SPEC.md:31 は「範囲の内なら」だけを決めている。この場面でも始値で約定させる試作(`MUT=exitopen` → `41 passed in 0.27s`)が通る。
  応答: 次の版で直す(試験 `test_t4_exit_beyond_range_on_parent_bar_waits` を足した。良い側でも親の足では約定せず、次の足から)

## 問3 決めていない選び(試験の合否か目的に当たるものだけ)
- [直す](S2 のため)fills の case の 5 つの名前(SPEC.md:48)を、どの決まりが出すかが SPEC.md §3 に無い。段が根の足で約定 → anchor_bar、利確が親の足で約定 → entry_bar、次の足からの段・利確 → range / open、成行 → market は試験(test:94-100・177・364)にしか無い。S2 は SPEC.md だけから書き、1 字違わずで比べる(SPEC.md:60)ので、名前を当て推量することになる。改善案: §3 の表の各行に case の名前を書く。
  応答: 次の版で直す(§3 の表の各行に case の名前を書いた)
- [直す](S2 のため)切り捨てのやり方を Decimal(repr) と決めているのは段だけ(SPEC.md:30)。limit・exit の「刻みに切り捨てる」(SPEC.md:25)にはやり方が無い。浮動小数で切り捨てると刻みが 1 でないときに割れる: `python3 -c "import math; print(math.floor(0.29/0.01)*0.01)"` → `0.28`。S1 と S2 が別のやり方を選ぶと、刻みが 1 でない市場で検査 1 が食い違う。
  応答: 次の版で直す(切り捨てのやり方を 1 つにした: Decimal(repr(値段)) を Decimal(repr(刻み)) で割って ROUND_FLOOR で整数にし、刻みを掛けて float に戻す。limit・exit・段とも)
- [直す] exit の決まり(SPEC.md:31「親(limit か level の番号)」「量は親と同じ量で出す」)を破る注文(親が market や exit・量が親と違う・売買が親と同じ)が、SPEC.md:36 の止める一覧に無い。作業者は「止める / 量を親の量に書き換える / そのまま受ける」から選ぶことになり、どれを選ぶかで S3 の建玉が変わる。
  応答: 次の版で直す(止める一覧に足し、止める場面の試験に 3 通り足した)
- [直す] out_dir に前のファイルがあるときの扱いが無い。SPEC.md:43 の「書き足す」は追記の形に読める。試作を追記の形(`MUT=append`)にしても `41 passed in 0.25s`(試験は毎回新しい tmp に書く)。同じディレクトリで走らせ直すと行が 2 重になり、trades・summary が誤る。
  応答: 次の版で直す(run は始めにその側のファイルを新しく作る(前の中身は残さない)と書き、同じディレクトリで 2 回走らせる試験を足した)
- [聞く] 同じ番号で中身が同じかを比べるとき(SPEC.md:18)、「値段」は戦略が出した値段(px_calc)か、切り捨てた値段(px)か。戦略が足ごとに値段を計算し直して浮動小数の差が出ると、前者では走らせが止まり、後者では止まらない。どちらを比べるかで、行に残す px_calc が最初の値か最後の値かも変わる。
  応答: 次の版で直す(リードの決め: 戦略が出した値段そのもの(px_calc)で比べる。同じ番号なら px_calc も同じなので、行に残す px_calc は 1 つに決まる)
- [聞く] run は meta["seal"] を受け取るが、渡された足が封印の境より前かを確かめる決まりが無い(封印を守るのは read_bars だけ。SPEC.md:11)。S3 が read_bars 以外の読み方で足を渡すと、境より後の足もそのまま通る。
  応答: 次の版で直す(run も meta の seal を見て、境以後の足が来たら止める、と書き、試験を足した)

## 問4 読んだ事実
無し。全部の行を打ち直して実物と合った。
- データ: `zcat backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2016.csv.gz | head -3` → 見出しの行、`2016-01-01T00:03:00+00:00,51810.0,…,4.45622112,,,,`、`2016-01-01T00:04:00+00:00,,,,,0.0,,,,`。一致。
- book: 委任文のコマンド → `{'fill_count': 3, 'closed_trades': 1, 'pnl_jpy': '0.027', 'open_trades': 0, 'trades': [...]}`。一致。
- ledger.py:86-87: `SUMMARY_KEYS = (...)`・`TRADE_KEYS = ("first_t_ns", ..., "status")`。一致。`def book` は :254 で一致。
- `PYTHONPATH=src python -m pytest tests/simple` → `1 skipped in 0.09s`。一致。
- 「41 passed(捨てる実装)」: リードの実装は残っていないので、そのものは確かめられない。独立の試作で `41 passed`(上)を得たので、期待の値と合う。
- モジュールの読み込み: 委任文のコマンド → 出力に `bot.bt.core.*`・`bot.bt.fill.*`・`bot.bt.road.strategy` が並ぶ(ほかに `bot.bt.orders.*`・`bot.bt.portfolio.*`)。一致。
- `PYTHONPATH=src python -m pytest tests/road` → `315 passed in 20.26s`。一致。
- README.md:35-38(ts は 1 分の始まりの ISO-8601 UTC、値段は約定 0 の分で null)。一致。SPEC.md:43-57 は §4 の範囲で合う(57 は空の行)。

## 問5 通るのに間違う道筋
1. [直す] 売りの limit・exit を切り上げるか、exit を切り捨てない作り。41 件とも通る(`MUT=sellceil`・`MUT=exitnofloor` → `41 passed`)。S3 のマチルダは整数でない値段の利確を出すので、利確の約定の値段が 1 刻みずれる。これは S2 で見つかって初めて分かり、作り直しになる。改善案: 整数でない売りの exit の値段(例 6,999,800.7 → 6,999,800)を試験に 1 件足す。
   応答: 次の版で直す(問2 の 2 件目と同じ。`test_t2_sell_limit_and_exit_floored`)
2. [直す] 数の作り直しが、summary の fill_count と trades の pnl_jpy だけを比べる作り。T8 の 2 件とも通る(`MUT=cnweak` → `41 passed in 0.21s`。test:290 が書き換えるのは最初の鍵 = fill_count)。summary の pnl_jpy・closed_trades・open_trades や、trades の hold_ns・max_position・levels の食い違いは見逃す。改善案: summary の書き換えの的を pnl_jpy にする。
   応答: 次の版で直す(summary の書き換えの的を pnl_jpy に、trades の書き換えの的に hold_ns を足した)
3. [直す] 良い側で親が約定した足に、約定する向きに範囲の外の exit を始値で約定させる作り。41 件とも通る(`MUT=exitopen`)。SPEC.md:31 では、この exit はその足では約定せず、次の足から約定する。良い側の約定が多く、早く出る。これも S2 が見つけるまで残る。
   応答: 次の版で直す(問2 の 3 件目と同じ。`test_t4_exit_beyond_range_on_parent_bar_waits`)

試作と変異は全部 /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/p2/(simple_proto.py・simple_proto2.py・s2.py・test_proto.py・test_proto2.py・test_s2.py)に置いた。リポジトリのファイルは書いても変えてもいない。封印の置き場は読んでいない。根からの grep -r・find . も打っていない。
