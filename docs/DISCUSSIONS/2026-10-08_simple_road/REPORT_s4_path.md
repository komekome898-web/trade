# 報告: 単純な測りの道 2 版目(DELEGATION_s4_path.md 2 版目)

<!-- 作業者の返事を逐語で写した(10-08、リード)。見出し「着手前の表と時間」だけ、受け取りの検めの見出しの名前に合わせて「着手前の表」に替えた。 -->

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 足の決まりを直す: 向きの決まらない足とデータの頭の始値 = 終値 の足を飛ばす、始値か終値が範囲の外の足で止める(`bars.py`・`run.py`) | L-883「**yes**」(委任文「直すもの」1) |
| 道筋をたどり、最初に起きた点で `decide(ev)` を呼び、続きをたどり、終値で close を呼ぶ口(`run.py`・`fills.py`) | L-883「**yes**」(委任文「直すもの」2) |
| 注文の形を limit・stop・market にし、level・exit・close の印を止める | L-883「**yes**」(委任文「直すもの」3) |
| 残すファイルを fills.csv・signals.csv・summary.json・run.json にし、kind を tag にする | L-883「**yes**」(委任文「直すもの」4) |
| `scripts/simple/run_one.py` の側の引数を外し、BASE_PARAMS で 1 回走らせる | L-883「**yes**」(委任文「直すもの」5) |
| `tests/simple/test_run.py`・`simple_scenes.py` を 2 版目の場面に書き換える | L-883「**yes**」(委任文「直すもの」6・「受け入れ」U1〜U6) |
| 変異の表を scratchpad の src の写しで作る | L-883「**yes**」(委任文「変異の表」) |
| 速さの見積もり(2018 年の 1 年分、scratchpad の簡単な戦略) | L-883「**yes**」(委任文「報告」) |

- 見込みは 120 分でした。内訳は、実装 1 回 30 分、試験の書き換え 1 回 40 分、試験の回し直し 2 回 × 5 分、変異 約 15 件 × 1.5 分 = 25 分、速さ 1 回 5 分、報告 10 分です。
- 実際は約 35 分でした(14:48 UTC に着手し、確かめを打ち終えたのが 15:13 UTC、その後に報告を書きました)。変異は道具で一括して当て、3 回回しました。

## 直したファイルの一覧と行数(H5)

直したファイル:
- `src/bot/bt/simple/__init__.py`
- `src/bot/bt/simple/bars.py`
- `src/bot/bt/simple/fills.py`
- `src/bot/bt/simple/run.py`
- `scripts/simple/run_one.py`
- `tests/simple/simple_scenes.py`
- `tests/simple/test_run.py`

新しいファイルは作っていません。`common.py` は変えていません。

行数は `wc -l src/bot/bt/simple/*.py scripts/simple/run_one.py` で数えました。直す前は 554 行、直した後は 557 行です。

| ファイル | 行数 |
|---|---|
| `__init__.py` | 6 |
| `bars.py` | 54 |
| `common.py` | 67 |
| `fills.py` | 65 |
| `run.py` | 297 |
| `run_one.py` | 68 |

## 試験のコマンドと出力

```
$ PYTHONPATH=src python -m pytest tests/simple tests/road
....................................                                     [100%]
108 passed in 3.10s
```

飛ばしは 0 です(1 版目の `importorskip`(読み込めなければ飛ばす呼び出し)は普通の import に替えました)。

## H1〜H5 の確かめ

**H1**(3 か所の外を変えない)
- 自分が変えたファイルは上の 7 つで、全部が `src/bot/bt/simple/`・`scripts/simple/run_one.py`・`tests/simple/` の中です。
- `git status --porcelain -- src/bot/bt/simple scripts/simple tests/simple` の出力は、その 7 行の ` M` だけでした。

**H2**(古い道・模型・core を直に import しない)
```
$ (git ls-files src/bot/bt/simple; git ls-files -o --exclude-standard src/bot/bt/simple) | xargs grep -nE "bot\.bt\.(fill|core|road\.strategy|pipeline)|from \.\.(fill|core|pipeline)|from \.\.road(\.strategy| import strategy)"
```
出力は空でした(終了コード 123 は、grep が 1 件も見つけなかったことを示します)。

**H3**(道の既存の試験)
```
$ PYTHONPATH=src python -m pytest tests/road
103 passed in 0.61s
```
着手前も `103 passed` でした。

**H4**(戦略のファイルを変えない)
- H1 の一覧に `src/bot/strategy/` の下のファイルはありません。

**H5**(大きさ)
- 上の表のとおり、554 行から 557 行になりました。

## 速さの見積もり(受け入れではない。SPEC.md §6)

- 足は実物の `candles_1m_2018.csv.gz` だけで、`read_bars`(足のファイルの読み)で読みました。
- 戦略は scratchpad の `speed.py` の `Ten`(コミットしない)です。
  - 買いの limit を 今の値段 − 500×k、売りの limit を 今の値段 + 500×k(k = 1〜5)に出し続けます。
  - 約定した分は新しい番号で補います。
  - 見張る値段は 今の値段 ± 300・± 600 の 4 つで、呼ぶたびに出し直します。
- 結果は次のとおりです(事実)。
  - 走らせの秒数: 160.9 秒
  - 最大の記憶: 40 MB(`resource.getrusage` の ru_maxrss)
  - 戦略を呼んだ回数: 3,659,154 回
  - 約定: 9,065 本

## 変異の表

- 壊した変更は、scratchpad の `mutate.py` で `src` の木を丸ごと写し、文字の置き換えで当てました。
- 回し方は `PYTHONPATH=<写しの src>`・`-o pythonpath=<写しの src>`・`tests/simple tests/road` です。
- 壊さない写しは `108 passed` でした。本物は壊していません。
- 下の表は 3 回目に回したときの結果です。

| 番号 | 壊した変更 | 落ちた試験 |
|---|---|---|
| U1 | run.py `pts = (op, hi, lo, cl)  # 陰線` → `pts = (op, lo, hi, cl)  # 陰線` | `tests/simple/test_run.py::test_scenes`(場面: 陰線の道筋は 始値 → 高値 → 安値 → 終値 / 始値 = 終値 で上がって始まった足は 始値 → 高値 → 安値 → 終値) |
| U1 | run.py `_fill`(約定させる関数)で、始値への飛びのとき(case が None)の約定値段を `o.px if (case is None and o.px is not None) else price` にした | `tests/simple/test_run.py::test_scenes`(場面: 始値への飛び: 注文と見張る値段は始値で・逆指値は始値で(L-877 3.b)・同じ値段はまとめて 1 回) |
| U1 | run.py の各区間の頭(始値を除く折り返しの点)で、その点に等しい見張る値段を到達として `_stop`(足の途中で止まって呼ぶ関数)を呼ぶ行を足した | `tests/simple/test_run.py::test_scenes`(場面: 見張る値段は折り返しの点ちょうどで 1 回・刻みに切り捨ててから比べ touched は返した値のまま) |
| U1 | run.py `if o.px == x), key=lambda o: o.seq)` → 末尾に `[:1]` | `tests/simple/test_run.py::test_scenes`(場面: 道筋で先に届く値段から順・同じ値段の約定と見張る値段はまとめて 1 回・値段の切り捨て・安値ちょうど) |
| U1 | run.py `_stop` の `got = [o for o in self.live.values() if o.fills_at(price)]` → `got = []` | `tests/simple/test_run.py::test_scenes`(場面: 呼んだ点で返した注文がすぐ約定するなら同じ点でもう一度呼ぶ(now。2 回目は新しい約定だけ・touched は空)・返さなかった注文はその点で取り消す)、`tests/simple/test_run.py::test_stops`(場面: 同じ点で 101 回目の呼び出し) |
| U1 | run.py `_orders`(返した注文を受ける関数)の `kept.append(old)` の後に `kept += [o for o in self.live.values() if o.id not in orders]` | `tests/simple/test_run.py::test_gone_orders_are_not_kept`、`tests/simple/test_run.py::test_scenes`(場面: 呼んだ点で返した注文がすぐ約定するなら…取り消す)、`tests/simple/test_run.py::test_stops`(場面: 消えた番号をまた返す) |
| U1 | run.py `self.wfloor = [floor_tick(x, self.tick) for x in self.watches]` → `[float(x) for x in self.watches]` | `tests/simple/test_run.py::test_scenes`(場面: 見張る値段は折り返しの点ちょうどで 1 回・刻みに切り捨ててから比べ touched は返した値のまま) |
| U1 | run.py `touched = [v for v, f in …if f == x]` → `[f for v, f in …]` | `tests/simple/test_run.py::test_scenes`(場面: 同上) |
| U1 | run.py の飛びの到達の条件 `if op != prev and lo <= f <= hi and f != prev]` → `if False]` | `tests/simple/test_run.py::test_scenes`(場面: 始値への飛び: …同じ値段はまとめて 1 回) |
| U1 | run.py の stop の ev に `"bar": None` を足す | `tests/simple/test_run.py::test_scenes`(場面: 陽線の道筋は 始値 → 安値 → 高値 → 終値 / 陰線の道筋は 始値 → 高値 → 安値 → 終値 / 始値 = 終値 で上がって始まった足は… / 始値 = 終値 で下がって始まった足は… / 見張る値段は折り返しの点ちょうどで 1 回… / 始値への飛び: … / 道筋で先に届く値段から順… / 呼んだ点で返した注文がすぐ約定するなら… / 足が閉じたときの成行は飛ばさない次の足の始値・向きの決まらない足は戦略を呼ばず約定もさせない) |
| U1 | fills.py `self.px = floor_tick(raw["px"], tick)` → `self.px = -floor_tick(-raw["px"], tick)`(切り上げ) | `tests/simple/test_run.py::test_scenes`(場面: 始値への飛び: … / 道筋で先に届く値段から順・…値段の切り捨て・安値ちょうど) |
| U1 | run.py `fills, touched = self._fill(ts, got, price, "now"), []` → `fills = fills + self._fill(ts, got, price, "now")`(リードの途中の決め Q1 の逆) | `tests/simple/test_run.py::test_scenes`(場面: 呼んだ点で返した注文がすぐ約定するなら同じ点でもう一度呼ぶ(now。2 回目は新しい約定だけ・touched は空)・返さなかった注文はその点で取り消す) |
| U2 | run.py の close の呼び出しの後に `self._fill(ts, [o for o in self.live.values() if o.form == "market"], pts[3], "market")` を足した(終値で成行) | `tests/simple/test_run.py::test_files`、`tests/simple/test_run.py::test_scenes`(場面: 足が閉じたときの成行は飛ばさない次の足の始値・向きの決まらない足は戦略を呼ばず約定もさせない) |
| U2 | run.py `_stop` の got に `and o.form != "market"` を足した(足の途中の成行をその点で約定させない) | `tests/simple/test_run.py::test_scenes`(場面: 呼んだ点で返した注文がすぐ約定するなら…)、`tests/simple/test_run.py::test_stops`(場面: 同じ点で 101 回目の呼び出し) |
| U3 | run.py `if op == cl and (prev is None or op == prev):` → `if op == cl and prev is None:` | `tests/simple/test_run.py::test_scenes`(場面: 足が閉じたときの成行は飛ばさない次の足の始値・… / データの頭の始値 = 終値 の足は値段を変えて続いても飛ばす) |
| U3 | 同じ行を `if op == cl and prev is not None and op == prev:` にした | `tests/simple/test_run.py::test_scenes`(場面: データの頭の始値 = 終値 の足は値段を変えて続いても飛ばす)、`tests/simple/test_run.py::test_stops`(場面: 封印の境以後に始まる足) |
| U3 | run.py `_check_bar`(足の検め)の始値・終値の範囲の外の検め 2 行を `pass` にした | `tests/simple/test_run.py::test_stops`(場面: 始値が安値〜高値の外の足 / 終値が安値〜高値の外の足) |
| U3 | bars.py `if not (lo <= o <= h and lo <= c <= h):` → `if False:` | `tests/simple/test_run.py::test_read_bars` |
| U4 | fills.py `extra = [k for k in o if k not in KEYS]` → `extra = []` | `tests/simple/test_run.py::test_stops`(場面: close の印 / 知らない鍵) |
| U4 | fills.py `FORMS = ("limit", "stop", "market")` → `level`・`exit` を足した | `tests/simple/test_run.py::test_stops`(場面: level の形 / exit の形) |
| U4 | fills.py `if "px" in o:` → `if False:` | `tests/simple/test_run.py::test_stops`(場面: 値段のある market)。1 回目に回したときは落ちませんでした(下の Q2) |
| U4 | fills.py `if "tag" in o and not isinstance(o["tag"], str):` → `if False:` | `tests/simple/test_run.py::test_stops`(場面: tag が文字でない) |
| U4 | run.py `raw.get("px"), raw.get("tag")) != old.key` → `raw.get("px"), old.tag) != old.key` | `tests/simple/test_run.py::test_stops`(場面: 同じ番号で tag が違う) |
| U4 | run.py `if oid in self.used:` → `if False:` | `tests/simple/test_run.py::test_stops`(場面: 約定し終えた番号をまた返す / 消えた番号をまた返す) |
| U4 | run.py `if calls > MAX_CALLS_AT_POINT:` → `if calls > MAX_CALLS_AT_POINT + 1:` | `tests/simple/test_run.py::test_stops`(場面: 同じ点で 101 回目の呼び出し) |
| U4 | 同じ行を `if calls >= MAX_CALLS_AT_POINT:` にした | `tests/simple/test_run.py::test_stops`(表の後の「100 回までは止めない」の確かめで落ちた) |
| U5 | run.py `summarize`(まとめを数える関数)の `if pos == 0:` → `if pos == 0 or row[ix["kind"]] == "close":` | `tests/simple/test_run.py::test_files` |
| U5 | fills.py `return self.form if self.tag is None else self.tag` → `return self.form` | `tests/simple/test_run.py::test_files` |
| U5 | run.py `path("fills.csv")`(2 か所)→ `path("fills_optimistic.csv")` | `tests/simple/test_run.py::test_files`、`tests/simple/test_run.py::test_scenes`(場面: 表の 10 場面全部。陽線の道筋は… / 陰線の道筋は… / 始値 = 終値 で上がって… / 始値 = 終値 で下がって… / 見張る値段は折り返しの点ちょうどで 1 回… / 始値への飛び: … / 道筋で先に届く値段から順… / 呼んだ点で返した注文がすぐ約定するなら… / 足が閉じたときの成行は… / データの頭の始値 = 終値 の足は…) |
| U5 | run.py `_orders` の頭に、消えた注文を `self.gone` の辞書に持ち続ける行を足した | `tests/simple/test_run.py::test_gone_orders_are_not_kept` |
| U5 | bars.py `return  # 封印の境の行` → `continue  # 封印の境の行` | `tests/simple/test_run.py::test_read_bars` |
| U5 | run.py `if t >= seal:` → `if t >= seal and not (bar[1] == bar[4]):`(封印の境の検めを飛ばす判定の後にした形) | `tests/simple/test_run.py::test_stops`(場面: 封印の境以後に始まる足) |
| U6 | 写しの `bot/bt/road/ledger.py` `"closed_trades": len(closed),` → `len(closed) + 1,` | `tests/road/test_road_ledger.py::test_critic_add_partial_add_close_total_4`、`::test_critic_doten_add_close_two_trades_total_5`、`::test_critic_three_buys_of_0_1_sell_0_3_exactly_15`、`::test_critic_three_partial_closes_exactly_3`、`::test_critic_two_adds_same_ns_close_at_10020_is_exactly_zero`、`::test_open_trade_partial_pnl_not_in_sum`、`::test_scene1_owner_example_L747`、`::test_scene2_doten`、`::test_scene3_partial_close`、`::test_scene5_open_at_end`、`::test_scene6_usd_converted_at_trade_start[USDT]`、`::test_scene6_usd_converted_at_trade_start[USD]`、`::test_usd_doten_new_trade_uses_rate_at_doten`、`tests/simple/test_run.py::test_files` |
| H1 | `git status --porcelain -- src/bot/bt/simple scripts/simple tests/simple` | 委任文に書かれた 7 ファイルの ` M` だけ |
| H2 | 委任文の grep | 出力は空 |
| H3 | `PYTHONPATH=src python -m pytest tests/road` | `103 passed` |
| H4 | H1 の一覧に `src/bot/strategy/` が無いかを見た | 無い |
| H5 | `wc -l src/bot/bt/simple/*.py scripts/simple/run_one.py` | 554 → 557 行 |

## 試験で決まらず作業者が決めた内部の形

1. 同じ点でもう一度呼ぶときは、ev の fills にその回に新しく約定した注文だけを入れ、touched は空にしました。リードの途中の決め Q1 に従ったものです。場面「呼んだ点で返した注文がすぐ約定するなら…」で、2 回目の呼び出しを見ています。
2. 始値の点の約定の case は次のように分けました(どれも値段は始値です)。
   - 前の close で返した limit・stop が始値で約定する側にあれば `open`。
   - 前の close で返した成行は `market`。
   - その点の stop の呼び出しで返してすぐ約定したものは `now`。
3. 戦略を呼んだ点では、出ている注文のどれも今の値段で約定する側にいない形にしました(すぐ約定するものはその点で約定させて呼び直すため)。この前提で、上へ届く注文(売りの limit・買いの stop)を値段の安い順に、下へ届く注文(買いの limit・売りの stop)を値段の高い順に並べて持ちます。見張る値段は切り捨てた値を小さい順に並べ、bisect(二分探索)で「次に届く値段」を探します。並べ直すのは、注文か見張る値段が変わったときだけです。
4. 同じ点の呼び出しの回数は、stop の点ごとに 1 から数えます。終値の close の呼び出しは数えません。
5. 見張る値段の並びに同じ値が 2 つあれば、touched にも 2 つ入れます(返した順)。
6. 足の検めは、時刻・封印の境・古い順・数・安値 > 高値・始値か終値が範囲の外、の順にし、その後で飛ばすかを決めます。飛ばす足も古い順の検めに入れます。
7. 番号の使い回しの検めは、受けた番号を 1 つの集合に持つだけにしました。止まったときの文は「約定し終えた・消えた注文の番号 … をもう一度返した」で、約定し終えた番号か消えた番号かを分けていません。
8. `run_one.py`(1 本走らせる台本)の記録は、側の名前を外した `report.json` の 1 つにしました。この台本は走らせていません(委任文のとおり)。
9. 試験の戦略 `Script`(試験の場面で使う決まった手順の戦略)は、plan に無い呼び出しでは、前に返した注文から約定し終えた番号を除いたものと、前の見張る値段をそのまま返します(`simple_scenes.py` の頭の注に書きました)。
10. 止める場面の表は、止まった理由の文の一部を `pytest.raises(match=…)` で照らす形にしました(下の Q2)。

## 問いとして返したこと

- Q1: SPEC.md に無い止め方を 2 つ置きました。決めでよいか、または外すかをお決めください。
  - 見張る値段の並びに数でないものがあれば止めます(止めないと、比べのところで型の誤りとして落ちます)。
  - limit・stop の値段が 0 以下、または切り捨てた値段が 0 以下のときに止めます(1 版目から残しました)。
  - decide の返り値が 3 つの組でないときも止めますが、これは SPEC §2.2 の口の形の検めとして置いています。
- Q2: 変異「値段のある market を止めない」で、1 回目は試験が 1 つも落ちませんでした。止める場面が raw(約定し終えた番号も返す設定)なので、ねらいの理由より先に「約定し終えた番号をまた返す」で止まり、場面が通っていたためです。
  - 壊し方は差し替えていません。試験の側を「止まった理由の文を照らす」形に直し、同じ変更を当て直したら落ちました(上の表)。
  - 同じ原因で、1 回目は「level・exit を知っている形にする」でも「level の形」の場面が落ちていませんでした(「exit の形」の場面だけ落ちた)。直した後は両方落ちます。
  - 委任文の「落ちなかったら問いとして返す」の扱いとして、この直し方でよいかをお決めください。
