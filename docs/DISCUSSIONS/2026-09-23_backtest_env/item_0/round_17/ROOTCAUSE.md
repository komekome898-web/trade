# 項目 0「核」第 17 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(全 170 行を読んだ)。**指紋の食い違い**: 起動文は `@cdf623e4fb24` と書くが、作業木とコミット abb256d の版を `sha256sum … | cut -c1-12` で測ると `20487e2d8aec`。`cdf623e4fb24` は 1 つ前の版(コミット dc3f666)。違いは L-445(核の約束の射程)の行と批評家の格付けの 1 文で、作業者の手順は変わらない。起動文の「委任文が優先する」に従い今の版で作業した。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
固定した要件: `item_0/REQUIREMENTS.md`(変えない。§0 の射程 L-445 を読んだ)。リードの設計: `round_7/LEAD_DESIGN.md`(§2・§3.1〜§3.4・§9.2・§9.3・§11・§12)。批評家の記録: `round_16/CRITIC.md`。前の周の自分の根本原因: `round_16/ROOTCAUSE.md`。リードの答え: `docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_run11_item0.md` の第 16 周の節(F4「作業者の格子の「直す前に落ちる」記録も materials に置く」を当て、直す前の記録をこの周のフォルダの `materials/` に写した)。
一時ファイルは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r17_worker/`(以下 `<W>`)。HEAD は `1d8a107`。

## 0. この周に直す対象と、この周の初めに確かめたこと

`PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r16_accepted_keys_read_back.py tests/bt/critic/item_0/test_i0r16_colliding_frozendict_chain_frames.py tests/bt/critic/item_0/test_i0r16_shared_containers_bounded_work.py -p no:cacheprovider` → `15 failed, 1 passed in 40.47s`(`materials/pytest_item0_r17_worker_start.log`)。

| id | 格 | 相手 | repeat_of | この周の初めの確かめ |
|---|---|---|---|---|
| i0-r16-02 | 止める | 実装 | i0-r15-02 | 上の実行で 10 件が落ちる(thaw 5 形・約定の模型の `extra_dict()` 5 形)。落ち方は全部 `TypeError: unhashable type` |
| i0-r16-01 | 直す | 実装 | i0-r15-03 | 上の実行で 20・40・90 段の 3 件が落ちる(10 段は通る) |
| i0-r16-03 | 直す | 実装 | null | 上の実行で freeze・settle の 2 件が 20 秒で終わらない。自分の試し(`materials/item0_r17_worker_probe_before.out`): 入れ子 18 で freeze(tuple の共有)0.68 秒・freeze(list の共有)1.58 秒・thaw 1.73 秒・renew 1.18 秒・freeze(dict の共有)8.88 秒。どれも入れ子が 2 増えるごとに約 4 倍(2 のべき) |
| i0-r16-04・05 | 止める・示唆 | 場面集 | null | 場面係の持ち物(`tests/bt/battery/`)。作業者は直さない |
| i0-r15-01〜04・07 | — | 実装 | — | 第 16 周の批評家が直りを確かめた(`round_16/CRITIC.md`「前の周の指摘の直り」)。この周は構造を変えない |
| i0-r11-01・03、i0-r13-01、i0-r14-01・02・04 | — | 実装 | — | 第 15・16 周の批評家が直りを確かめた。この周は構造を変えない |

## 1. 3 つの指摘に共通する根: 核の値の操作の単位を「送り手が渡した物」ではなく「展開した木」と「その値の型」で決めていた

核が平らなデータにする操作は 4 つある: 作り直す(freeze・settle・renew・thaw の歩き)、hash を取る(辞書の鍵・集合の要素にするとき、FrozenDict を作るとき)、比べる(hash が衝突したとき)、読み手に戻す(thaw)。第 15・16 周の私は、このうち「再帰を反復に替える」「hash の無い値を断る」を直したが、**どの操作も、値を「道ごとに 1 回たどる木」として扱い、値がどの位置(辞書の鍵か、値か)にあるかを見ていなかった**:

- 作り直す・比べる・hash を取るの 3 つは、同じ入れ物を 2 か所から指す値(共有。循環ではない)を、道ごとに展開した木としてたどる。仕事は渡された物の数ではなく、展開した木の大きさ(2 のべき)で決まる(i0-r16-03)。比べる操作は、相手の側に同じ hash の鍵が複数あるとき、候補ごとに Python の呼び出しを入れ子にし、その入れ子は展開した木の深さで積み上がる(i0-r16-01)。
- 読み手に戻す操作(thaw)は、入れ物の型だけで戻す形を決め(FrozenList → list、FrozenDict → dict、FrozenSet → set)、それが辞書の鍵・集合の要素の位置にあるかを見ない。鍵の位置で list / dict / set に戻すと、インタプリタの規則(鍵は hash を持つ)に反する(i0-r16-02)。

第 16 周の私の格子は、入れ物の型 × 段数 × 衝突の置き方を列べたが、**共有(同じ物を 2 か所から指す)と位置(鍵か値か)の 2 つの軸が無かった**。神託は「作れた物は thaw も通る」を hash の無い sNaN の位置だけで確かめた(round_16/ROOTCAUSE.md §4 の「受け手の thaw と renew は変えない」)。どちらの軸も、送り手が普通の Python の値として作れる形(公開の `FrozenDict(...)`・`FrozenSet(...)`・`FrozenList(...)` と tuple・list・dict・int)で、プロセスを書き換えない(要件 §0 の射程の中)。

## 2. i0-r16-02(受け付けた鍵を thaw が hash の無い型に戻す)

### なぜ起きたか(根本原因)

`thaw`(values.py 1567 行)は `_thaw_open`(1574 行)で入れ物の型だけを見て、FrozenList → list、FrozenDict → dict、FrozenSet → set を作り、tuple と frozenset はその中身を同じ規則で戻す。辞書の鍵・集合の要素は、送り手の辞書・集合の中にあった時点で hash を持つ物(送り手の辞書がそれを要る)だったが、`thaw` はそれを hash の無い型に戻してから新しい辞書・集合を作るので、インタプリタが `TypeError: unhashable type` を出す。`freeze` の側は鍵の位置の FrozenDict・FrozenSet・FrozenList を受け付け(送り手の辞書が持てる鍵なので正しい)、型も保つ。**「元の形に戻す」の約束を型だけで決め、位置で決めていなかった。**

第 16 周の私が「thaw と renew は核が作った入れ物からしか作らないので変えない」と書いたのは、`thaw` の後の鍵の型が変わることを見落としていた(批評家の指摘のとおり)。

### どの構造を変えるか

- **`thaw` の戻す形を位置で決める**: 辞書の鍵・集合と frozenset の要素の位置にある物は、その下の全部を核の不変の写し(`renew` と同じ形: tuple・frozenset・FrozenList・FrozenSet・FrozenDict を型ごと保つ)で戻す。送り手の辞書の鍵にあった物は、送り手が渡した時点で hash を持つ不変の物だったので、それと同じ型・同じ値で戻るのが「元の形」である。それ以外の位置(辞書の値・list と tuple の中身・根)は今までどおり list / dict / set に戻す。
- 読み手は `thaw` を通るもの全部(`OrderRequest.extra_dict()` と `values.thaw` の直接の呼び出し)。`renew` は元から全部を不変の写しで作るので変えない(格子で確かめる)。
- 契約の文(`PLAIN_DATA_RULE`・values.py の説明・api.py の `extra_dict` の説明)に位置の規則を書く。
- 採らなかった案: 鍵の位置の核の入れ物を `freeze` で断る — 送り手が普通に持てる辞書(`{FrozenDict({"a": 1}): 3}`)を断ることになり、受け付けを狭める(機能を外して要件から逃げる形)。

## 3. i0-r16-03(共有された入れ物を道ごとに作り直す)

### なぜ起きたか(根本原因)

`_walk`(values.py 977 行)は、入れ物に入るたびに `open_node` を呼び、その子を全部たどる。循環は自分の道の上の入れ物(`path`)で断るが、**一度作り直した入れ物を覚えていない**ので、同じ物が別の道からもう一度出ると、その下を全部作り直す。t_k = (t_{k-1}, t_{k-1}) は物が k + 1 個なのに、作り直しは 2^(k+1) 個になる。同じ形の展開が、核の値に対する残りの操作にもある:

- **FrozenDict の hash を作るとき**: `_fd_fill` は作った時点で `_pairs_hash` を呼び、各組 (鍵, 値) の hash を取る。値が共有された tuple なら、インタプリタの tuple の hash(Python 3.11 では覚えない)が展開した木をたどる。公開の `FrozenDict({"a": t})` も、freeze が作る FrozenDict も同じ。送り手が一度も hash を取っていない値(辞書の値)の hash を核が取るので、送り手の仕事で上から抑えられない。
- **`_plain_equal` の比べ**: 積み上げに (x, y) の組を積むとき、同じ組をもう一度積んでも覚えていない。共有された 2 つの値の比べは展開した木の組の数になる。`_match` は比べるたびに相手の鍵の hash を取り直す(tuple の鍵は hash を覚えない)。
- **thaw・renew**: 同じ `_walk` なので同じ。

### どの構造を変えるか

- **`_walk` は入れ物を物ごとに 1 回だけ作り直す**: 作り終えた入れ物を、その物の id(と、thaw では位置の印)で覚え、同じ物がもう一度出たら、覚えた新しい物をその位置に置く。作り直した値の中の共有は、送り手が渡した共有と同じ形になる(`copy.deepcopy` と同じ規則。値の外の物とは何も共有しない)。入れ子の上限(`MAX_NESTING`)は、覚えた物の高さ(その下の入れ物の段数)を一緒に覚え、置く位置の深さ + 高さで確かめる(超えるなら覚えた物を使わずにたどり、今と同じ所で同じ誤りになる)。
- **FrozenDict の hash は、要るときに 1 回だけ作る**(作った時点では取らない)。hash を取るのは、その FrozenDict が辞書の鍵・集合の要素になるとき(送り手の辞書・集合がそれを要ったので、送り手も同じ hash を取っている)か、読み手が自分で hash を取るときだけ。取るときは、中の FrozenDict の hash を反復で下から作り(物ごとに 1 回)、インタプリタの再帰は tuple・frozenset の段だけにする。
- **`_plain_equal` は、比べた組を覚え、hash が衝突した候補の比べも同じ積み上げの上で行う**: 比べを「組の比べの課題」の明示の積み上げにし、候補が複数の鍵は、候補ごとに子の課題を積んで答えを待つ(Python の呼び出しを入れ子にしない)。課題の答えは (id, id) で覚え、同じ組は 1 回しか比べない。鍵の hash は比べ 1 回の中で物ごとに 1 回だけ取る。これで i0-r16-01 の枠(段数に比例)と、批評家が「列に入れていない」と書いた 3 つ以上の衝突の鎖の仕事(段数の指数)の両方が、同じ構造で閉じる。
- 契約の文(process_state・plain_data)に、仕事の単位(渡された物ごとに 1 回)と、残るインタプリタの仕事(tuple の鍵の hash と比べはインタプリタの C が行い、送り手の辞書・集合も同じ仕事をした)を書く。
- 採らなかった案: 展開した大きさに上限を置いて入口の誤りで断る — 上限の値に根拠が無く(A-12)、送り手が普通に作れる小さな値を断ることになる。

## 4. i0-r16-01(衝突した候補が複数ある段で比べが入れ子になる)

### なぜ起きたか(根本原因)

§3 の `_plain_equal` の項のとおり。第 16 周の私は「候補が 1 つならその組を積み、複数なら候補ごとに `_plain_equal` を呼ぶ」とした(round_16/ROOTCAUSE.md §5)。候補が複数の枝は「どれか 1 つが等しい」の問いで、積み上げの「全部が等しい」の問いと形が違うので、呼び出しの入れ子で解いた。格子 F は衝突の置き方を「一番下で違う・途中で違う・等しい」で列べ、「相手の側に同じ hash の鍵が複数ある段」を列に入れていなかった。

### どの構造を変えるか

§3 の `_plain_equal` の項。比べは「課題」(組の全部が等しいか)の積み上げで、候補が複数の段は親の課題を止めて子の課題(候補との比べ)を積み、子の答えで親を進める。枠の数は段数にも候補の数にもよらない。

## 5. 先に書く敵対者の試験(委任文 §3「提出前の吟味」(6))

`tests/bt/item_0/test_bt0_r17_shared_and_placed.py`。入力の空間は実装の場合分けから作らない:

- **格子 K(位置 × 入れ物 × 読み手)**: 鍵・要素になれる値(hash を持つ物)を、入れ物の型(tuple・frozenset・公開の FrozenList・FrozenSet・FrozenDict)と平らな値から、種つきの乱数の文法で段数 1〜4 まで作り、位置(辞書の鍵・set の要素・frozenset の要素・公開の FrozenSet の要素・公開の FrozenDict の鍵・list の中の辞書の鍵・辞書の値の中の set の要素・鍵の tuple の中)に置く。読み手は `values.thaw`・`values.renew(freeze)`・約定の模型の `order.extra_dict()`(実行の中)・戦略自身の `extra_dict()`。神託: `freeze` が受け付けたら、読み手は例外を出さず、戻した値は渡した値と Python の `==` で等しい(送り手の値は、値の位置に list・dict・set だけ、鍵の位置に核の入れ物を持つ形で作るので、`thaw` の「値の位置は list / dict / set」と両立する)。加えて全ての形で `freeze(thaw(freeze(x))) == freeze(x)`。
- **格子 S(共有 × 入口 × 入れ子)**: 共有の形(tuple・list・dict・公開の FrozenList・FrozenDict の 2 か所から同じ物、種類を交互に混ぜた形、鍵の位置の FrozenDict の共有)× 入口(freeze・settle・renew・thaw・`FrozenDict` の公開の構築・`hash`・`_plain_equal` と `==`・発注の extra と約定の模型の `extra_dict()`・出口の箱)× 入れ子 {8(神託と照らす), 90(子のプロセスで時間の上限つき)}。神託: 入れ子 8 は Python の値の比べ(共有を展開しても 256 なので速い)で答えが同じ。入れ子 90 は展開すれば 2^90 なので、終われば仕事が物の数で決まっている(20 秒の上限は展開したときとの差が 2^60 倍以上あるので、機械の速さに依らない)。
- **格子 C(衝突した鍵の鎖)**: 1 段の衝突する鍵の数 {2, 3, 4} × 段数 {1, 10, 20, 40, 90} × 入れ物(FrozenDict の鍵・FrozenSet の要素・frozenset の要素)× 答え(等しい・一番下で違う・途中で違う)。神託: 作り方の引数から決まる答え(同じ種から作った鎖だけが等しい)と一致。要る枠は契約の文の CALL_FRAMES + 段数 以下。3 つ以上の衝突は子のプロセスで時間の上限つき。

列に入れなかったもの(試験のファイルに書く): tuple の鍵そのものが共有された形(送り手の辞書が作るときにインタプリタが同じ展開をするので、送り手が 2^90 の仕事をしないと作れない)、送り手が書いた class(射程の外)、スレッド。

## 6. 厳しい批評家が [止める] にしそうな点(返す前に潰す。直したあと §7 に結果を書く)

1. 共有を保つと、thaw の結果の 2 か所が同じ list になり、片方を変えるともう片方も変わる。「changing it changes nothing else」に反しないか → 送り手が渡した共有と同じ形で、値の外の物(送り手・核・ほかの受け手)とは何も共有しない。送り手の値の中で共有されていない物は、戻した値でも共有されない(格子で確かめる)。
2. 覚えた物を使うと、入れ子の上限(MAX_NESTING)を素通りしないか → 覚えた物の高さを一緒に覚え、置く位置の深さ + 高さで確かめる(格子で、浅い所で覚えて深い所に置く形を確かめる)。
3. FrozenDict の hash を遅らせると、hash の無い値(sNaN)の断りの時機が変わらないか → 核が鍵・要素にする所(`_dict_of`・`_set_of`)で hash を取るので、そこで入口の誤りになるのは同じ。値の位置の sNaN は前も今も受け付ける。
4. 比べを課題の積み上げにしたとき、Python の `==` と答えが違わないか → 格子 C の神託と、第 16 周の格子 F の乱数の組を回し直す。
5. 速さ(1 本の足あたりの時間)が落ちないか → 第 16 周と同じ測りで比べる。

## 7. 直した場所と、直したあとの確かめ(コマンドと出力)

直した場所(ファイル:行は直した後の作業木。リードが途中の版を a77c0af に記録したので、差分は `git diff 1d8a107 -- src/bot/bt/core` で見る):
- i0-r16-03(物ごとに 1 回): `values.py` 1002 行 `_walk`(1020 行の覚え、1038 行の再利用と高さの確かめ)。FrozenDict の hash を要るときに 1 回: 1445 行 `__hash__`、1458 行 `_fd_fill`(作った時点では取らない)、1466 行 `_fd_of_table`(核が作った辞書をそのまま表にし、鍵の hash を取り直さない)、1478 行 `_fd_hash`(下から反復で)、1356 行 `_HashOnly`(int の子。hash と == は C の slot で、frozenset を作る間に Python の枠が走らない)、1374-1375 行(「hash が無い」「まだ」の印をインタプリタが 1 つだけ持つ `False`・`None` にした。`object()` だと受け手どうしが同じ物を持つことになり、第 8 周の送り手の敵対者の試験が落ちた)。
- i0-r16-01(候補が複数の段): `values.py` 1546 行 `_plain_equal`(課題の積み上げ、1550 行の答えの覚え、1559 行)、1644 行 `_match`(候補が複数なら「探す」項目を積む。hash は比べ 1 回の中で物ごとに 1 回)。
- i0-r16-02(位置で戻す): `values.py` 1730 行 `thaw`、1747 行の 2 つの位置、1750 行 `_thaw_open`(鍵・要素の位置は `_renew_open` と同じ不変の写し)。`api.py` 164-168 行 `extra_dict` の説明。
- 契約: `contract.py` 15 行(版 `core-18`)、process_state の比べの文(候補が複数の段)と仕事の単位の文(i0-r16-03)、要る枠の実測(22 → 24)。`values.py` の説明の文と `PLAIN_DATA_RULE`。

確かめ:
- 批評家の第 16 周の試験 3 本(実装の側): 直す前 `15 failed, 1 passed in 40.47s`(`materials/pytest_item0_r17_worker_start.log`)→ 直した後、第 15 周の 2 本と合わせて `47 passed in 0.82s`。
- 新しい格子 `tests/bt/item_0/test_bt0_r17_shared_and_placed.py`(495 件): 直す前の核(`git archive 1d8a107 src/bot` を `<W>/head_src` に取り出し、`-o pythonpath=` と PYTHONPATH で差し替え。子のプロセスも親と同じ `bot` を読む)で `334 failed, 161 passed in 679.23s`(`materials/pytest_item0_r17_worker_grid_before_fix.log`。格子 K 308・格子 S 18(子のプロセスの 9 入口は全部 60 秒で終わらない)・格子 C 8)。直した後 `495 passed`。途中で試験の側の誤りを 3 つ直した(renew の神託を渡した値でなく凍った値と比べる / FrozenSet を FrozenDict に入れる形が 1 段で 2 つの入れ物になり 90 段で上限を超えた → 1 段 1 つで交互に / 子のプロセスが編集可能な導入の `bot` を読み、直す前の核で走っていなかった → 親の `bot` の場所を PYTHONPATH に置き、子で確かめる)。直す前の記録は 3 回目(子の直しの後)のもの。
- 共有された値の仕事(`materials/item0_r17_worker_probe_after.out`): 8 形 × freeze・settle・renew・thaw・別々に作った 2 つの `==` の 40 通りが全部 5 ミリ秒以下(直す前は入れ子 18 で 0.68〜8.9 秒、`materials/item0_r17_worker_probe_before.out`)。
- 衝突の鎖(`materials/item0_r17_worker_chain_times.out`): 深い候補 3 つ・90 段で 2.78 秒以下。段数に対しておよそ 2 乗で増える(インタプリタが辞書を作るときの鍵の比べは呼び出しごとに新しい覚えで始まる。送り手の公開の構築 `FrozenDict({...})` も同じ比べをする)。
- 要る枠(`materials/item0_r17_worker_headroom.py` を直す前後の核で): 戦略の呼び出しの中の place_order は、list・tuple・set の入れ子で 19(前後同じ)、dict で 20(前は 22)、FrozenDict の鍵の入れ子で 24(前は 22)。CALL_FRAMES = 30 の中。最初の版は `_hashed` の下に `_fd_hash → _pairs_hash → 内包表記 → _HashOnly.__init__` が積まれて 30 を超え、第 15 周の自分の格子 D が落ちた(`test_an_entry_takes_a_value_alike_at_every_stack_depth[frozendict_key-place_order]`)。内包表記を繰り返しに、`_HashOnly` を C の slot だけの int の子にして 24 に戻した。
- 速さ(`materials/item0_r17_worker_speed.out`、2 万本の足、10 本ごとに extra つきの発注、3 回の最良、同じ機械で交互に 5 組): 直した後 140.92〜154.87 us/bar、直す前 141.60〜152.95 us/bar。差は揺れの中。
- 自分の項目と批評家の試験(直す途中の版、切り離して 1 回): `5 failed, 6689 passed, 2 skipped`(`<W>/pytest_item0_r17_worker_item_critic.log`)。落ちた 5 件は、上の枠の 1 件、送り手の敵対者の 2 件(印の `object()`)、格子 C の子の 2 件(実行の途中で試験のファイルを書き換えた)。直した後、該当の 7 ファイルで `4691 passed`(`<W>/affected.log`)。全試験は §8。
- 書き直した自分の試験(消した試験は無い): `test_bt0_r14_process_state.py`(版 `core-18` と理由の注釈)。

## 8. 全試験

- 1 回目(11:52 UTC〜): ディスクの空きが 19M になり、88% 以降の多くの試験が準備の段の誤り(E)で止まり、報告の書き出しの途中でログが切れた(`df -h /` → `252G 38G 19M 100%`)。自分の実行の一時フォルダ `/tmp/pytest-of-root/pytest-487`(217M、11:55〜12:09 に作られた)だけを消した(空き 236M)。ほかの者の全試験(12:10〜12:31)が終わるのを待った。
- 2 回目(12:31 UTC〜、一時フォルダを試験ごとに消す設定 `-o tmp_path_retention_policy=none`。場面集を含む。場面集の実行はこの 1 回): `PYTHONPATH=src python -m pytest -p no:cacheprovider -rf -o tmp_path_retention_policy=none` → `9891 passed, 6 skipped, 4 warnings in 1150.47s (0:19:10)`(`materials/pytest_item0_r17_worker_full_tail.log`)。落ちたものは無い(批評家の第 16 周の試験 4 本のうち場面集の側の 1 本 `test_i0r16_no_int_scene_tells_refusal_from_no_entry.py` も、並行の場面係の直しの後の場面集で通った)。
