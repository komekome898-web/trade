## 報告

## 着手前の表
右の列は、委任文末尾の承認の逐語に、根になる節の名前を添えて書きました。右が空の行はありませんでした。

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 1 本の足の中で約定させ記す順を ⓪〜⑤ に直す(始値で約定する、前からの建玉を閉じる注文を成行より先に記す)。根は「直すもの」の 1 | L-833「**両方yes**」(根: 直すもの 1) |
| 注文の辞書の `"close": True` の印を受ける。limit 以外、`True` でない値、同じ番号で印を外した場合は止める。根は「直すもの」の 2 | L-833「**両方yes**」(根: 直すもの 2) |
| 注文の記録 `orders_<側>.csv` の末尾に列 `close` を足す。根は「直すもの」の 3 | L-833「**両方yes**」(根: 直すもの 3) |
| 段に付けた利確が、親の段が前の足までに約定していれば閉じる注文の組に入ることを、場面の表で確かめる。根は「直すもの」の 4 | L-833「**両方yes**」(根: 直すもの 4) |
| `tests/simple/test_run.py` と `tests/road` を、試験を変えずに通す。根は「受け入れ」 | L-833「**両方yes**」(根: 受け入れ) |
| 変異の表を作り、scratchpad の自分専用の写しだけで壊した変更を当て、落ちた試験を記録する。根は「変異の表」 | L-833「**両方yes**」(根: 変異の表) |
| H1〜H5 を確かめて報告する。根は「変えないもの」 | L-833「**両方yes**」(根: 変えないもの) |

### 直したファイルと行数(H5)
- `src/bot/bt/simple/fills.py`(約定の関数)は 94 行から 103 行になりました。
- `src/bot/bt/simple/run.py`(走らせ)は 233 行から 236 行になりました。
- 変えたのはこの 2 ファイルだけです。
- `src/bot/bt/simple/` の合計は、直す前が 534 行、直した後が 546 行です(`wc -l src/bot/bt/simple/*.py` の合計)。

直した中身は次のとおりです。
- `fills.py` の組の番号を ⓪〜⑤ の 6 組にしました。
  - `RANK_CLOSE_OPEN`(⓪ 前からの建玉を閉じる注文のうち始値で約定するもの)を足しました。
  - `RANK_CLOSE_RANGE`(② 同じく範囲の内で約定するもの)も足しました。
  - `_rank`(組の番号を決める関数)は、足も受け取って決めるようにしました。
  - `Order`(出ている注文 1 つの状態)に `close`(閉じる指値の印)を足しました。
  - `Order.key`(同じ番号の比べの中身)に close の印を入れました。
- `run.py` の `_shape`(注文の形の検め)で、`"close"` の鍵があるときは次の 2 点を検めるようにしました。
  - 形が limit であること。
  - 値が `True` そのものであること。
  - どちらかが違えば `SimpleRoadError`(走らせを止める例外)を出します。
- `run.py` の `ORDER_COLS`(注文の記録の列)の末尾に `close` を足しました。印の付いた limit は `1`、それ以外は空で書きます。約定した行も、消えた行も、データの終わりまで残った行も同じです。

### 試験
```
$ PYTHONPATH=src python -m pytest tests/simple/test_run.py tests/road
........................................................................ [ 89%]
.................................                                        [100%]
321 passed in 27.68s
```
飛ばしは 0 です。直す前は `tests/simple/test_run.py` が 3 failed, 3 passed でした。

### H1〜H5 の確かめ
- H1: `git status --short tests/` の出力は空でした。試験は変えていません。
- H2: `git status --short src/` に出たのは `M src/bot/bt/simple/fills.py` と `M src/bot/bt/simple/run.py` だけです。`git status --short -- src tests` も同じ 2 行だけでした。
- H3: 委任文の `grep -nE` の出力は空でした。ファイルの一覧は 6 件で、空ではありません。xargs の終了コードは 123 で、grep が 1 件も見つけなかった印です。
- H4: `PYTHONPATH=src python -m pytest tests/road` は `315 passed` でした。
- H5: 直す前は 534 行、直した後は 546 行です。

## 変異の表
壊した変更は、scratchpad の自分専用の置き場(`fix2run_worker/` の下の M1 から M26 の各ディレクトリ)に `src` の写しを作って当てました。当てるときは `-o pythonpath=<写し>` を付けて `tests/simple/test_run.py` を走らせました。本物の `src/` は壊していません。「壊した変更」の欄は、実際に当てた置き換えをそのまま書いています。

| 番号 | 壊した変更 | 落ちた試験 |
|---|---|---|
| U1(M1) | `_close_rank`(閉じる注文の組を決める関数)を、始値でも常に ②(範囲の内の組)にする。`return RANK_CLOSE_OPEN if res is not None and res[0] == bar[1] else RANK_CLOSE_RANGE` を `return RANK_CLOSE_RANGE` に置き換えた | `tests/simple/test_run.py::test_scenes`(場面: 前からの利確が始値なら成行より先(L-828)/ 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M2) | 値段が始値ちょうどの閉じる注文を ② にする(⓪ の条件を `res[1] == "open"` だけにした) | `tests/simple/test_run.py::test_scenes`(場面: 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M3) | 買いの閉じる注文を常に ② にする(⓪ の条件を `res[1] == "open" and o.side == "sell"` にした) | `tests/simple/test_run.py::test_scenes`(場面: 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M4) | 値段が安値ちょうどの閉じる注文を ⓪ にする(⓪ の条件に `res[0] == bar[3]` を足した) | `tests/simple/test_run.py::test_scenes`(場面: 売りの close の印の指値が安値ちょうどなら成行の後) |
| U1(M24) | 切り捨てる前の戦略の値段だけで始値ちょうどを比べる(⓪ の条件を `res[1] == "open" or o.px_calc == bar[1]` にした) | `tests/simple/test_run.py::test_scenes`(場面: 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M25) | 前の足までに親が約定した利確では、値段が始値ちょうどのものを ② にする(始値で約定するときだけ ⓪) | `tests/simple/test_run.py::test_scenes`(場面: 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M26) | close の印の指値では、値段が始値ちょうどのものを ② にする(始値で約定するときだけ ⓪) | `tests/simple/test_run.py::test_scenes`(場面: 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M9) | 印の無い指値も ② にする(`return _close_rank(o, bar) if o.close else RANK_LIMIT` を `return RANK_CLOSE_RANGE` に置き換えた) | `tests/simple/test_run.py::test_scenes`(場面: 前の足までに親が約定した利確は新しい指値より先(L-824)/ 段に付けた利確も新しい指値より先 / close の印の指値は新しい指値より先・印の無い指値は出した順 / 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M10) | 前の足までに親が約定した利確を ⑤(親がこの足で約定した利確の組)にする | `tests/simple/test_run.py::test_scenes`(場面: 前の足までに親が約定した利確は新しい指値より先(L-824)/ 段に付けた利確も新しい指値より先 / 前からの利確が始値なら成行より先(L-828)/ 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M11) | close の印を見ずに、指値を常に ③ にする(`return _close_rank(o, bar) if o.close else RANK_LIMIT` を `return RANK_LIMIT` に置き換えた) | `tests/simple/test_run.py::test_scenes`(場面: close の印の指値は新しい指値より先・印の無い指値は出した順 / 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M12) | 前の足までに親が約定した利確を、始値でも常に ② にする | `tests/simple/test_run.py::test_scenes`(場面: 前からの利確が始値なら成行より先(L-828)/ 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))) |
| U1(M22) | 悪い側でも、親が約定した足に付けた利確を試す(`side == "optimistic"` の条件を外した) | `tests/simple/test_run.py::test_scenes`(場面: 指値と利確の切り捨て・付けた利確は良い側だけ親の足 / 段に付けた利確は良い側だけ親の足) |
| U1(M5) | 注文の記録の close の列を、約定した行にだけ書く(`"1" if o.close and o.state == "filled" else None`) | `tests/simple/test_run.py::test_scenes`(場面: 約定しない close の印の指値(消えた・データの終わりまで)と seq) |
| U1(M17) | 注文の記録の close の列に、いつも空を書く | `tests/simple/test_run.py::test_scenes`(場面: 約定しない close の印の指値(消えた・データの終わりまで)と seq / close の印の指値は新しい指値より先・印の無い指値は出した順) |
| U1(M18) | 注文の記録の close の列に、limit の行はすべて `1` を書く | `tests/simple/test_run.py::test_scenes`(場面: close の印の指値は新しい指値より先・印の無い指値は出した順) |
| U1(M6) | close の印を見ない(`Order.close` を常に False にした) | `tests/simple/test_run.py::test_scenes`(場面: 約定しない close の印の指値(消えた・データの終わりまで)と seq / close の印の指値は新しい指値より先・印の無い指値は出した順 / 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い)))と `tests/simple/test_run.py::test_stops`(場面: 同じ番号で close の印を外す) |
| U2(M7) | 同じ番号の比べ(`Order.key`)から close の印を外す | `tests/simple/test_run.py::test_stops`(場面: 同じ番号で close の印を外す) |
| U2(M13) | close の印が limit 以外に付いても止めない(`f != "limit"` の検めを外した) | `tests/simple/test_run.py::test_stops`(場面: 利確に close の印 / 成行に close の印) |
| U2(M14) | close の値が `True` かを見ない(`o["close"] is not True` の検めを外し、形の検めだけ残した) | `tests/simple/test_run.py::test_stops`(場面: close の印が false / close の印が 1) |
| U2(M15) | close の値を `not o["close"]` で見る(`False` は止まるが `1` は通る) | `tests/simple/test_run.py::test_stops`(場面: close の印が 1) |
| U3(M16) | 注文の記録の見出しから `close` を外す | `tests/simple/test_run.py::test_files` と `tests/simple/test_run.py::test_scenes`(場面: 約定しない close の印の指値(消えた・データの終わりまで)と seq / close の印の指値は新しい指値より先・印の無い指値は出した順) |
| U4(M19) | 封印の境ちょうどに始まる足を止めない(`t >= seal` を `t > seal` に) | `tests/simple/test_run.py::test_stops`(場面: 封印の境以後に始まる足) |
| U4(M20) | 消えた注文の番号を `seen` に残さない(`seen.add(oid)` を `pass` に) | `tests/simple/test_run.py::test_stops`(場面: 消えた番号をまた返す) |
| U4(M21) | `check_numbers`(数の作り直し)で fills の見出しの検めを外す | `tests/simple/test_run.py::test_check_numbers`(場面: fills の見出しがでたらめ・行なし・trades と summary は約定 0 本 / fills の見出しに余計な列) |
| U4(M23) | 足のファイルの読みで、安値が高値より高い足を止めない | `tests/simple/test_run.py::test_read_bars` |

等価として外した変異: M8(Q1 の答え)

U4 の `test_gone_orders_are_not_kept`(消えた注文を記憶に持ち続けない)と `tests/road` については、それを落とす変異の行を作っていません。

H の行は次のとおりです。
| 番号 | 確かめ | 結果 |
|---|---|---|
| H1 | `git status --short tests/` | 出力が空 |
| H2 | `git status --short src/` と `git status --short -- src tests` | `src/bot/bt/simple/fills.py` と `src/bot/bt/simple/run.py` の 2 行だけ |
| H3 | 委任文の `grep -nE` | 出力が空。ファイルの一覧は 6 件 |
| H4 | `PYTHONPATH=src python -m pytest tests/road` | `315 passed` |
| H5 | `wc -l src/bot/bt/simple/*.py` | 534 行から 546 行 |

### 試験で決まらず作業者が決めた内部の形
- 閉じる注文の組(⓪ か ②)は、`_close_rank`(閉じる注文の組を決める新しい関数)で決めました。
  - 切り捨てた後の値段 `o.px` に `_limit_rule`(範囲の内なら値段で、約定する向きに範囲の外なら始値で約定する決まり)を当てます。
  - 約定値段が始値なら ⓪、そうでなければ ②(約定しない注文も ②。約定しないので記す順に影響しません)にします。
  - 前の足までに親が約定した利確と、印の付いた指値が、同じ関数を通ります。
- `Order.close` は、形が limit で `raw.get("close") is True` のときだけ True にしました。`_shape` が先に検めるので、他の値はここに来ません。
- 同じ番号の比べ(`Order.key`)には、close の印を最後の要素として足しました。
- 注文の記録の close の欄は、印があれば文字 `"1"`、なければ `None`(`cell` 関数で空の欄)で書きました。
- close の印の検めは `_shape` の中で、`f in ("limit", "exit")` の値段の検めの前に置きました。

## 問いとして返したこと
- Q1: 変異 M8(切り捨てた後の比べを残したまま、⓪ の条件に切り捨てる前の戦略の値段が始値ちょうども足す変更)は、試験が 1 つも落ちませんでした(`tests/simple/test_run.py` は 6 passed)。M8 は、委任文の例(切り捨てる前の値段で比べる)を当てたときの形の 1 つです。典型の M24(切り捨てる前の値段だけで比べる)は `tests/simple/test_run.py::test_scenes` が落ちました。M8 のような「両方で比べる」形は、場面の表に差を出す場面が無いため、試験では見分けられません。決まりの正本(SPEC.md §3 の「切り捨てた後の値段で比べる」)から見て、M8 の差を見分ける場面を足すかはリードの判断です。私は試験を足していません。

補足です。作業中に `docs/AUDITOR/TRACE/2026-10-08_220780c0.json` が変わっていました。これは私が変えたものではなく、`git diff --stat` で見えたものです。H2 の `git status --short -- src tests` には出ません。
