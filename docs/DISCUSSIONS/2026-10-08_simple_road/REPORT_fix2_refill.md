## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語)と、その行の根になる委任文の節 |
|---|---|
| 1 本の足の中で約定させ記す順を SPEC.md §3 の ⓪〜⑤ に直す(始値で約定する前からの閉じる注文を成行より先に、値段が始値ちょうどの閉じる注文も ⓪、close の印の無い指値は ③) | L-833「**両方yes**」(根: 「直すもの」の 1) |
| 注文の記録の見出しを 13 列(末尾に `close`、欄は空か `1`)にする | L-833「**両方yes**」(根: 「直すもの」の 2) |
| 注文の記録から分かる止める注文の検めに 5 項目を足す(level の売買が根と違う・距離の向きが違う・exit の売買が親と同じ・exit の量が親と違う・limit 以外の close の印) | L-833「**両方yes**」(根: 「直すもの」の 3) |
| 今までの作るもの(比べ・px 列を入力にしない・足を 1 回だけ前から読む・読めない入力を例外にしない)は変えない | L-833「**両方yes**」(根: 「直すもの」の 4) |
| `tests/simple tests/road` が飛ばし 0 で全部通ることを確かめる(試験は変えない・足さない) | L-833「**両方yes**」(根: 「受け入れ」U1〜U4、「変えないもの」H1・H4) |
| 作業者専用の写しの上でわざと壊す変更を当て、落ちた試験を変異の表にする | L-833「**両方yes**」(根: 「変異の表」) |
| 報告を「報告」の節の形で返事に書く | L-833「**両方yes**」(根: 「報告」) |

H6: 走らせのコード `src/bot/bt/simple/` と他の担当の試し・写しは開かなかった・読まなかった(機械では確かめられない。限界)。

SPEC.md と `tests/simple/simple_scenes.py` の sha256 は、着手時に委任文の値と同じ(`a0968f72…`・`14f4b757…`)で、今も同じ。`tests/simple/test_refill.py` の sha256 は、リードの試験の直し(書き換えの表の行を広げた)で渡した時点の値から変わり、今は `2ec295a1…`。

## 直したファイルの一覧と行数(H5)

直したのは `src/bot/bt/simple_refill/` の 2 ファイルだけ(リードの答えを受けた後もコードは変えていない)。

| ファイル | 直す前 | 直した後 | 直したこと |
|---|---|---|---|
| `src/bot/bt/simple_refill/loader.py`(注文の記録を読む) | 187 | 191 | 見出しを 13 列にした(`ORDER_COLS` = 列の名前の一覧の末尾に `close`)。`close` の欄は空か `1` だけ読み、ほかの値は「形の違う行」の食い違いにした。`Order`(注文 1 行の入れ物)に `close` を足した |
| `src/bot/bt/simple_refill/replay.py`(作り直し本体) | 247 | 277 | `_step`(1 本の足の約定)を ⓪〜⑤ の順に直した。`_link`(根・親をたどる検め)に、level の売買が根と違う・距離の向きが違う・exit の売買が親と同じ・exit の量が親と違う・limit 以外の close の印、の検めを足した |
| `src/bot/bt/simple_refill/rules.py`・`__init__.py` | 50・8 | 50・8 | 変えていない |
| 合計 | 492 | 526 | |

## 試験のコマンドと出力

今のリポジトリ(リードの試験の直しの後)で打ち直した。

```
$ PYTHONPATH=src python -m pytest tests/simple tests/road
........................................................................ [ 66%]
........................................................................ [ 88%]
.....................................                                    [100%]
325 passed in 30.42s
```

飛ばし 0。内訳は `tests/simple` が 10、`tests/road` が 315。

## H1〜H6 の確かめ

- H1: `git status --short tests/` → ` M tests/simple/test_refill.py` の 1 行。これは私が変えたものではなく、リードが Q1 の答えとして書き換えの表の行を広げた直し(私は `tests/` を触っていない。着手時は出力が空だった)。
- H2: `git status --short src/` → ` M src/bot/bt/simple_refill/loader.py`・` M src/bot/bt/simple_refill/replay.py` の 2 行だけ。
- H3: `(git ls-files src/bot/bt/simple_refill; git ls-files -o --exclude-standard src/bot/bt/simple_refill) | xargs grep -nE "bot\.bt\.simple([^_]|$)|from bot\.bt import|from \.\. import|from \.\.simple([^_]|$)"` → 出力が空。ファイルの一覧は 4 件(空でない)。
- H4: `PYTHONPATH=src python -m pytest tests/simple tests/road` → `325 passed`。
- H5: `wc -l src/bot/bt/simple_refill/*.py` → 8・191・277・50、合計 526(直す前は 492)。
- H6: 確かめ不能(上の 1 行のとおり)。

## 変異の表

壊した変更は、作業者専用の置き場 `fix2refill_worker/` の中の `src/` の写しの `bot/bt/simple_refill/` だけに当てた。`PYTHONPATH=<写し>/src … -o pythonpath=<写し>/src` を付けて、リポジトリの今の試験(リードの直しの後)の `tests/simple` を打った。本物は壊していない。

`tests/road` は、写しの上では走らない。道の試験は git の版を取るので、git の外の写しでは、壊す前の写しでも落ちる(`ReproError`)。また `simple_refill` を import する試験は `tests/simple/test_refill.py` だけで(`grep -rl simple_refill tests src` で確かめた)、`tests/road` と `tests/simple/test_run.py` は作り直しの側のどの変更でも影響を受けない。このため変異の確かめでは `tests/simple` だけを打ち、`tests/road` の全部は本物の上で 315 passed を確かめた(上の出力)。

表を回す試験は、続けて失敗の文に出た場面の名前を全部書いた。`test_random_strategy`(乱数の戦略の試験)の「乱数の種 N」は、場面の名前の代わりに出る回の名前。

| 番号 | 壊した変更 | 落ちた試験 |
|---|---|---|
| U1 | 始値で約定する閉じる注文も ② に入れる(⓪ を成行より先にしない) | `tests/simple/test_refill.py::test_scenes`(場面: 前からの利確が始値なら成行より先(L-828)、買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い)))・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5) |
| U1 | 値段が始値ちょうどの閉じる注文を ② にする(範囲の外で始値になるものだけ ⓪) | `tests/simple/test_refill.py::test_scenes`(場面: 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い)))・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・3・4・5) |
| U1 | 買いの閉じる注文を常に ② にする(売りだけ ⓪) | `tests/simple/test_refill.py::test_scenes`(場面: 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い)))・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5) |
| U1 | close の印を見ない(印の付いた指値を ③ の普通の指値に戻す) | `tests/simple/test_refill.py::test_scenes`(場面: close の印の指値は新しい指値より先・印の無い指値は出した順、買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))、売りの close の印の指値が安値ちょうどなら成行の後)・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5) |
| U1 | ③ で close の印の付いた指値を除かない(⓪・② で約定した後に ③ でもう一度約定する) | `tests/simple/test_refill.py::test_scenes`(場面: close の印の指値は新しい指値より先・印の無い指値は出した順、買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))、売りの close の印の指値が安値ちょうどなら成行の後)・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5) |
| U1 | 始値ちょうどの比べを、切り捨てた後でなく切り捨てる前の戦略の値段(`px_calc`)で行う | `tests/simple/test_refill.py::test_scenes`(場面: 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い)))・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 1・3・4・5) |
| U1 | ⓪ を close の印の指値だけにし、前からの利確は始値でも ② にする | `tests/simple/test_refill.py::test_scenes`(場面: 前からの利確が始値なら成行より先(L-828)、買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い)))・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5) |
| U1 | ⓪ を前からの利確だけにし、close の印の指値は始値でも ② にする | `tests/simple/test_refill.py::test_scenes`(場面: 買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い)))・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5) |
| U1 | この足で親が約定した利確(根が指値)も、前からの閉じる注文として ⓪・② に入れる | `tests/simple/test_refill.py::test_scenes`(場面: 指値と利確の切り捨て・付けた利確は良い側だけ親の足、親の足で範囲の外の利確は良い側でも約定しない(始値でも))・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5) |
| U2 | ② の中の順を seq の逆順にする | `tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5) |
| U3 | `close` の欄の値を見ない(空と `1` 以外も通す) | `tests/simple/test_refill.py::test_tampered_records_are_caught`(場面: close の欄に 0 を書く) |
| U3 | limit 以外の close の印を見ない | `tests/simple/test_refill.py::test_tampered_records_are_caught`(場面: 利確に close の印を書く、成行に close の印を書く) |
| U3 | 利確の量の検めを外す | `tests/simple/test_refill.py::test_tampered_records_are_caught`(場面: 約定しない親の利確の量を親と違えて書く) |
| U3 | 段の距離の向きの検めを外す | `tests/simple/test_refill.py::test_tampered_records_are_caught`(場面: 約定しない根の段の距離の向きを逆に書く) |
| U3 | 段の売買が根と違う検めを外す(距離の向きの検めは残す)。リードの試験の直しの後に当て直した | `tests/simple/test_refill.py::test_tampered_records_are_caught`(場面: 約定しない根の段の売買を根と違えて書く(距離の向きは売りに合わせる)) |
| U3 | 利確の売買が親と同じ検めを外す | `tests/simple/test_refill.py::test_tampered_records_are_caught`(場面: 約定しない親の利確の売買を親と同じに書く) |
| U3 | 注文の記録の `close` の列が無い 12 列の見出しを通す | `tests/simple/test_refill.py::test_scenes`(場面: 段は根の最初の約定値段から・根の足と次の足(L-816 の例)、買いの段の切り捨て、売りの段の切り捨て・根の足で約定、段の値段は 10 進の和(刻み 0.1)、指値と利確の切り捨て・付けた利確は良い側だけ親の足、指値の範囲の外・約定する向きの外は始値・成行、段に付けた利確は良い側だけ親の足、親が約定した後に初めて出た利確は次の足から、親の足で範囲の外の利確は良い側でも約定しない(始値でも)、段・利確が後の足で始値、同じ足で同じ組の約定は出した順、根が約定しないまま消える(段の値段は空)、欠けた分の後の次の足、データの終わりまで出ていた注文・最後の足で出た注文・終わらなかった合図、約定しない close の印の指値(消えた・データの終わりまで)と seq、前の足までに親が約定した利確は新しい指値より先(L-824)、段に付けた利確も新しい指値より先、close の印の指値は新しい指値より先・印の無い指値は出した順、前からの利確が始値なら成行より先(L-828)、買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い))、売りの close の印の指値が安値ちょうどなら成行の後、買いの前からの利確が高値ちょうどなら成行の後)・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5)・`tests/simple/test_refill.py::test_tampered_records_are_caught`(場面は名前が出ず `AssertionError` の形で落ちた。表の全場面が対象)・`tests/simple/test_refill.py::test_bars_are_not_kept` |
| U3 | `close` の印を読まず全部空として扱う | `tests/simple/test_refill.py::test_scenes`(場面: close の印の指値は新しい指値より先・印の無い指値は出した順、買いの利確と close の印の指値が始値ちょうどなら成行より先(L-831 の (い)))・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5)・`tests/simple/test_refill.py::test_tampered_records_are_caught`(場面: 利確に close の印を書く、成行に close の印を書く) |
| U3 | 段の距離の向きの検めを逆向きにする(買いで正を通し、買いで負を止める) | `tests/simple/test_refill.py::test_scenes`(場面: 段は根の最初の約定値段から・根の足と次の足(L-816 の例)、買いの段の切り捨て、売りの段の切り捨て・根の足で約定、段の値段は 10 進の和(刻み 0.1)、段に付けた利確は良い側だけ親の足、段・利確が後の足で始値、根が約定しないまま消える(段の値段は空)、段に付けた利確も新しい指値より先)・`tests/simple/test_refill.py::test_random_strategy`(乱数の種 0・1・2・3・4・5)・`tests/simple/test_refill.py::test_tampered_records_are_caught`(場面は名前が出ず `AssertionError` の形で落ちた) |
| U3 | 注文の記録の px 列を、計算し直した値と突き合わせない | `tests/simple/test_refill.py::test_tampered_records_are_caught`(場面: 指値の px 列だけを書き換える、利確の px 列だけを書き換える、段の px 列だけを書き換える) |
| U4 | 足を全部記憶に持つ(足の並びを list に溜める) | `tests/simple/test_refill.py::test_bars_are_not_kept` |
| H1 | `git status --short tests/` | ` M tests/simple/test_refill.py` の 1 行(リードの試験の直しで、私の変更ではない) |
| H2 | `git status --short src/` | `simple_refill/loader.py` と `simple_refill/replay.py` の 2 行だけ(通った) |
| H3 | 走らせの包みの import を探す grep | 出力が空、ファイル 4 件(通った) |
| H4 | `PYTHONPATH=src python -m pytest tests/simple tests/road` | 325 passed(通った) |
| H5 | `wc -l src/bot/bt/simple_refill/*.py` | 合計 526 行(直す前 492)。報告に出した |
| H6 | 走らせのコードと他の担当の試しを開かなかった | 確かめ不能 |

表の下の注: U2 の行(② の中の順を seq の逆順にする)は `test_random_strategy` だけが見つけ、`test_scenes` は見つけなかった(Q2 の答えで、試験は足さない・広げない)。前の返事の「参考」の行(段の売買と距離の向きの検めの両方を外す)は、U3 の行が落ちるようになったので外した。 U4 の `tests/simple/test_run.py` と `tests/road` が通ったままか: 変異は当てていない(`simple_refill` を import しない試験なので、作り直しの側のどの変更でも影響を受けない)。本物の上で `PYTHONPATH=src python -m pytest tests/simple tests/road` → 325 passed。

## 試験で決まらず作業者が決めた内部の形

- close の印は `Order`(注文 1 行の入れ物)の `close`(真偽値)に持つ。`close` の欄は、空なら偽、`1` なら真。空と `1` 以外は「形の違う行」(`load_orders` = 注文の記録を読む関数)。
- 前からの閉じる注文の組分けは、足に入った時点で 1 回だけ決める。親が前の足までに約定した exit、または close の印の limit を、`limit_fill`(指値の約定の関数)の結果で組分けする。約定値段が始値ちょうどなら ⓪、それ以外の約定は ②。値段が始値ちょうどかの比べは、切り捨てた後の約定値段で行う。case(`range` と `open`)は書き換えていない。
- ③ の指値は、close の印の付いたものを除く。⓪・② で約定していない close の印の指値は、③ でも約定させない(⓪・② で約定しない値段は ③ でも約定しない同じ決まりなので、結果は同じ)。
- 食い違いを見つけた注文は、`bad`(約定を試さない印)にする。段の距離が 0 は向きを持たないので通す(乱数の戦略が距離 0 の段を出す。「買いは負、売りは正」の読みで、0 は買いも売りも許す)。exit の量の比べは、記録から読んだ float どうしの `!=`。
- 止める注文の検めは `_link`(根・親をたどる関数)に集め、約定を試す前に注文の記録の全部の行へ当てる(`from_ts` が空の行にも効く)。

## 問いとして返したこと

- Q1: 変異「段の売買が根と違う検めを外す(距離の向きの検めは残す)」で、試験が 1 つも落ちなかった(`tests/simple` が 10 passed)。別の壊し方に差し替えていない。理由の推定: 試験の「約定しない根の段の売買を根と違えて書く」は、段の売買を `sell` に変える書き換えだが、段の距離(買いの -100)は変わらないので、売りで距離が負になり、距離の向きの検めでも食い違いになる。売買の検めと距離の向きの検めが互いに重なって、売買の検めを単独で外すと試験が見分けられない。両方を外すと「約定しない根の段の売買を根と違えて書く」と「約定しない根の段の距離の向きを逆に書く」が落ちる(参考の行)。売買だけを変えて距離の向きは合う書き換え(例: 買いの根に売りの段と正の距離を書く)は、今の試験には無い。試験を足さない決まりなので、足さずに返す。この検め(SPEC.md §3 の「根・売買が違う level」)の単独の確かめをどうするかは、リードの判断。
- Q2: 変異「② の中の順を seq の逆順にする」は `test_random_strategy` だけが見つけ、`test_scenes` の表は見つけない。場面の表に、② に 2 本以上入る場面が無いためと見る(推定)。試験を足さない決まりなので、足さずに返す。
