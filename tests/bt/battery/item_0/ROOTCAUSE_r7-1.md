# 場面集への指摘ごとの根本原因と直し(項目 0、第 r7-1 回の直し、場面係、2026-09-24)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`。起動文の指紋は `4c4cfc6e4052`、作業木の版も `4c4cfc6e4052`(`sha256sum docs/DATA/delegations/20260923_backtest_env_prompt.md | cut -c1-12`、全 162 行を読んだ)。
指摘の逐語: 起動文に貼られた 2 件(i0-r6-02 [止める]・i0-r6-04 [直す])。前の周の直し `ROOTCAUSE_r6-3.md`・`ROOTCAUSE_r6-2.md`・`ROOTCAUSE_r6-1.md` も読み直した(i0-r6-02 の形は r6-1 の [判断] に自分で書いて残したもの)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
当てた委任文の決まり: §3「根本的解決」(直す前に指摘ごとの根本原因と変える作りを書く / 指摘の文言だけに合わせない / 同じ根を全体で探す)、「場面集」(監査の観点「新実装に有利な範囲への偏り」)、「場面集の規則」2・3・5・6・9、「動かせない候補の検討と再現」(「再現の根拠は…注釈に 1 対 1 で書く。一次資料に無い工夫を足さない、弱めもしない」)、「提出前の吟味」。

**この節(根本原因・変える作り)は直す前に書いた。**直した結果と根拠は最後の「結果」の節に足す。今回の 2 件に [聞く] は無い。

## 直す前に確かめたこと(コマンドと出力)

批評家の試験(直す前): `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r6_battery_p5_measures_order_not_types.py` → `2 failed, 1 passed`(p5-same-time-twice・p5-hand-over-order。記録 `<scratchpad>/bt/r7-1/item0_r7-1_scenekeeper_critic_p5.before.txt`)。

各対象が p3-<型> で**その型の事象を戦略に届けた**型(`survey_results/*.tsv` の p3-<型> の run 1 が status ok で、受けた列が空でなく型が全部その型)と、型を固定した場面の今の結果:

```
cd tests/bt/battery/item_0/survey_results && python3 - <<'EOF'
import csv,glob,json; csv.field_size_limit(10**9)
kinds=["trade","book_snapshot","book_delta","bar","funding","liquidation"]
for f in sorted(glob.glob('*.tsv')):
    rows={r['scene_id']:r for r in csv.DictReader(open(f),delimiter='\t')}
    def c(k):
        r=rows['p3-'+k]
        if r['status_1']!='ok': return False
        s=json.loads(r['output_1']).get('sequence') or []
        return bool(s) and all(x[0]==k for x in s)
    car=[k for k in kinds if c(k)]
    if car: print(f[:-4], car, {s:rows[s]['correctness'] for s in ['p1-merge-by-time','p1-typed-events','p5-same-time-twice']})
EOF
```

| 対象 | 届けた型 | p1-merge-by-time | p1-typed-events | p5-same-time-twice |
|---|---|---|---|---|
| 65 aat | 約定・板の差分 | 不一致 | 不一致 | 不一致 |
| 61 barter-rs | 約定・板の写真・板の差分・足・清算 | 対応なし(資金調達が無い) | 正解と一致 | 対応なし(資金調達が無い) |
| 1 Basana | 約定・板の写真・板の差分・足 | 対応なし(資金調達が無い) | 正解と一致 | 対応なし(資金調達・清算が無い) |
| 20 VnPy | 板の写真・足 | 対応なし | 対応なし | 対応なし |
| 52 LEAN(再現) | 約定・足・資金調達 | 正解と一致 | 正解と一致 | 対応なし(清算が無い) |
| 足か約定の 1 種だけ(13 対象) | 1 種 | 対応なし | 対応なし・不一致 | 対応なし・不一致 |
| 新実装 | 6 種 | 正解と一致 | 正解と一致 | 正解と一致 |

p1-one-call-per-event(足 5 本で固定)の、足を持たない対象の結果: 65 aat = 不一致(detail「足の型が無いので足を DATA の事象(型の無い Data)として…」、期待の型の欄 `bar` に対し `data`)、33 sarthak = 不一致(「足の型が無いので足を Tick…」、型の欄 `tick`)。どちらも時刻の列は入力と同じ 5 件(`output_1` を読んだ)。

## i0-r6-02 [止める](P0-5 の 2 場面が型の欠けで決まる)

### なぜ起きたか(根本原因)

1. **型を測らない観点の場面に、型の組を固定して書いていた。**P0-1 の 3 場面と P0-5 の 2 場面は、入力の事象の型を場面の定義で決め打ちにした(p1-merge-by-time = 約定・足・資金調達、p1-typed-events = 足・約定、p1-one-call-per-event = 足、p5 の 2 場面 = 約定・足・資金調達・清算)。これらの場面が測るのは「時刻の順に合わせる」「型を見分ける」「事象ごとに呼ぶ」「同時刻の並びが規則どおり」であって、どの型を持つかではない(型を持つかは P0-3 が型ごとに測る)。固定した型の 1 つでも欠けた対象は、その観点の機構の有無と関係なく対応なし・不一致になる。**型の組を場面の側が決める作りだったので、場面の結果に P0-3 の結果が混ざった。**
2. **それを検める仕組みが無かった。**場面集の規則 3(観点ごとにまとめる)は表の数え方を定めたが、「ある観点の場面の結果が、別の観点が測るもので決まっていないか」を見る試験も文も無かった。第 r6-1 回の場面係(自分)はこの形に気づいて [判断] に書いたが、「要件の型で作るのは要件どおり」「型を減らすと並べ方の試しが 24 通りから 2 通りに弱まる」を理由に残した。この理由は誤りだった: 要件(REQUIREMENTS.md §2 P0-5)の測り方は「同時刻に**複数型**の事象」で、どの型かを決めていない。4 型を対象が持つ型から選べば 24 通りは弱まらない(4 型を持つ対象は 24 通り、持つ型の数が少ない対象ほど通りが減る = 調査結果の側に不利な向きにしか動かない)。

### 同じ根を全体で探した結果(全 32 場面・全観点)

型をどう決めているかを場面ごとに見た(`scenes.py` の全 `add(...)` を読んだ):

| 場面 | 型の決め方(直す前) | 測るもの | 同じ根か |
|---|---|---|---|
| p1-merge-by-time | 約定・足・資金調達で固定 | 時刻の順に合わせる | **同じ根**(資金調達を持たない Basana・barter-rs が対応なし) |
| p1-typed-events | 足・約定で固定 | 型を見分ける | **同じ根**(足と約定の両方を持たないと測れない。板の写真と足を持つ対象も対応なし) |
| p1-one-call-per-event | 足で固定、期待に型の欄 `bar` | 事象ごとに 1 回・その時刻 | **同じ根**(足を持たない aat・sarthak は、時刻の列が入力と同じでも型の欄で不一致) |
| p5-same-time-twice・p5-hand-over-order | 約定・足・資金調達・清算で固定 | 同時刻の並びが規則どおり | **同じ根**(指摘の場所) |
| p2-event-time-exact・p2-one-ns-apart・p5-same-stream-order | 「対象が受ける型を 1 つ選んでよい」 | 時刻の保ち方・同じ入力の中の順 | 違う(型は対象が持つもの。期待に型の欄が無い) |
| any_type の 11 場面(p3-clock-timer・p3-notice-*・p4-received-time・P0-6・P0-7) | 約定。約定を受けない対象は同じ時刻の足に代えてよい | 時計・通知・受け取りの時刻・発注と取消・差し込み口 | 違う(約定か足のどちらかを持てば測れる。届けた型のある全 18 対象が約定か足を持つ — 上の表。機械の試験を足して、この前提が崩れたら落ちるようにする) |
| p4-visible-at-step・p4-future-read-attempt | 足。足を受けない対象は約定に代えてよい | 過去の読み・先読みの止め | 違う(同上) |
| P0-3 の 11 場面 | 型そのもの | 型を持つか | 型を測る観点そのもの(p3-mixed-one-run は 6 種を 1 回に混ぜられるか) |

検討表(`opponents/CONSIDERED.md`)も同じ根を持つ: P0-1 の冒頭の文(「p1-merge-by-time は入力に資金調達があり…」)と、P0-5 の冒頭の文・11 OctoBot の行の「最良が正解と一致でない場面 p5-…: 資金調達と清算を検証の入力から流す型が無い」は、型の欠けを観点の欠けとして書いている。

### どの作りを変えるか

1. **型を測らない観点で型を使う場面は、型を対象が持つ型から機械で決める**(`scenes.py`)。
   - 型の順 `TYPE_ORDER` = 固定した要件 §1 の事象の型の並び(約定・板の写真・板の差分・足・資金調達・清算)。対象によらず 1 つ。
   - 「対象の型」= その対象が p3-<型> の場面で、その型の事象を戦略に届けた型(出所の検めを通り、受けた列が空でなく、型が全部その型)。runner が同じ実行の p3 の 6 場面の結果から作る(adapter は選ばない。1 回目と 2 回目は、それぞれの回の p3 の結果から作る)。
   - p1-merge-by-time: 3 つの入力 A・B・C(A = 2・5 日後、B = 1・4 日後、C = 3 日後)の型は、対象の型を `TYPE_ORDER` の順に A・B・C へ割り当てる(2 種なら A・B・A)。**最低 2 種。**理由: P0-1 は「同期のバー逐次ループではないこと」を問う(REQUIREMENTS.md §2)。同じ型だけの入力を時刻で合わせることは、足の逐次ループ(複数の足の feed を日時で揃える)でもできるので、1 種では P0-1 の区別が測れない。
   - p1-typed-events: 対象の型の最初の 2 種を 1 日後・2 日後に 1 件ずつ(最低 2 種 = 見分けるには 2 種が要る)。
   - p5-same-time-twice・p5-hand-over-order: 対象の型の最初の 4 種まで(最低 2 種 = 要件の「複数型」)を同時刻に 1 入力 1 件。p5-hand-over-order の渡す順は、その入力の全ての順(4 種なら 24 通り、3 種なら 6 通り、2 種なら 2 通り)。
   - 対象の型が最低に足りなければ、runner がその場面を「対応なし」にし、理由に p3 の結果を書く(adapter を呼ばない)。
   - 期待(正解)は、場面ごとの決まった式で対象の型の入力から作る(時刻の昇順・入力の件数・規則を当てた並び)。定義には、全 6 種を持つ対象に当たる入力と期待(`TYPE_ORDER` の最初からの型)を例として載せ、式を「正解の出し方」に書く。
   - 入力の名前は型の名前ではなく A・B・C・D にする(型が対象ごとに変わるので)。
2. **p1-one-call-per-event は型の欄で採点しない**: 型は「対象が受ける型を 1 つ選んでよい」(P0-2 の場面と同じ決まり)にし、期待を「戦略が受けた事象の時刻の列」(= 呼ばれた回数と各回の時刻)にする。runner が出力の列から時刻の列を作る(`graded_from`)。出所の検め(対象の型・対象が届けた)はそのまま当たる。
3. **stated_rules.py**: 手で書いた p5-same-time-twice の並び(`FIXED_PREDICTED`)を新しい例の入力(約定・板の写真・板の差分・足)で書き直す。52 LEAN の再現が p5 の 2 場面に出るようになる(3 種を持つ)ので、LEAN の規則(同じ時刻のデータは 1 つの Slice に入り、その並びは購読の並べ替え `SubscriptionCollection.SortSubscriptions` の鍵 (SecurityType, TickType, Symbol) で決まる。鍵が同じ購読どうしは決まらない)を一次資料の行で写す。
4. **機械の試験**(`test_battery_item0.py`): (a) P0-3 以外の観点の場面で、入力に型を固定して持つものが無い(型は `TYPE_ORDER` と対象の型から作る場面か、「対象が受ける型を選ぶ」「約定か足」の場面だけ)、(b) 例の入力・期待が `TYPE_ORDER` の全 6 種から作ったものと同じ、(c) 型の数ごとに作った入力と期待が式どおり(2・3・4 種)、(d) 届けた型のある全対象が約定か足を持つ(any_type と P0-4 の前提)、(e) runner が対象の型を p3 の結果から作り、足りなければ adapter を呼ばずに対応なしにする。
5. 型を多く持つ対象の adapter(新実装・65 aat・61 barter-rs・1 Basana・20 VnPy・52 LEAN の再現)を、A・B・C・D の入力と対象ごとの型で動くように直す。1 種だけの対象は runner が対応なしにするので呼ばれない。
6. 全対象を走らせ直し、検討表の P0-1・P0-5 の文と 11 OctoBot の行を、新しい記録で書き直す(「最良が正解と一致でない場面」の文は、記録が示すときだけ残す)。

## i0-r6-04 [直す](LEAN の再現が IsInternalFeed の条件を落とした)

### なぜ起きたか(根本原因)

1. **再現の注釈は「書き直した文の行」だけを引き、その文を囲む条件の行を引いていなかった。**`time_slice_create` の注釈は 184 行(`allDataForAlgorithm.Add`)と 365-372 行(`marginInterestRates[...] = ...`)を引いたが、それぞれを囲む 181 行 `if (!packet.Configuration.IsInternalFeed)` と 329 行 `else if ((delisting = baseData as Delisting) != null || !packet.Configuration.IsInternalFeed)` は書き直しにも注釈にも無い。194 行 `if (!packet.Configuration.IsInternalFeed)`(Ticks・Bars への振り分けを囲む)も同じく落としていた(指摘の 2 か所に加えて 3 か所目)。
2. **「落としてよい条件」と「落としてはいけない条件」を分ける決まりが無かった。**委任文 §3 の「弱めもしない」に照らすと、場面で成り立たない条件を落とすなら、成り立たないことを一次資料の行で示す必要がある。示さずに落とした条件は、再現を強くも弱くもしうる(IsInternalFeed を落とすと、内部の購読のデータも戦略に届く = 調査結果の側を強くする向き)。

### 同じ根を全体で探した結果

再現は 52 LEAN の 1 本だけ(`opponents/repro_*.py`。33 の再現は第 r6-3 回に退けて `survey_results/stale/` にある)。再現が引く一次資料の範囲の全部を、版 `856327ff33869cba98393781000c4ab1d2af423d` の原文(この周に中身を取らない clone から `git show` で取った: `<scratchpad>/bt/item0_r7-1_scenekeeper_*.cs`)と突き合わせ、書き直した文を囲む条件を全部数えた:

| 一次資料の範囲 | 再現が落としていた条件 | 場面で成り立つか |
|---|---|---|
| TimeSliceFactory.cs Create(95-392) | 140 行 `packet.IsSubscriptionRemoved` で飛ばす / 148 行 `list.Count == 0` で飛ばす / **181・194・329 行 `IsInternalFeed`** / 322 行(板の気配の下の型の更新、Auxiliary でない型の中) | 181・194・329 は購読の性質で決まる(下の 3)。140 は購読が宇宙から外された時だけ真(外さない)。148 は空の packet(Sync が空の packet を足さない、SubscriptionSynchronizer.cs 170 行 `if (packet?.Count > 0)`) |
| SubscriptionSynchronizer.cs Sync(88-262) | 109 行の購読の列の**並び**(`subscriptions` は `SubscriptionCollection` で、列挙の前に `SortSubscriptions` が (SecurityType, TickType, Symbol) で並べる、SubscriptionCollection.cs 123-126・213-227 行)/ 149-160 行 Delisting の扱い / 173-199 行 宇宙の購読 / 220-248 行 宇宙の選び直しの繰り返し | **並び**は同じ時刻に複数の購読があるとき効く(p5 の 2 場面)。再現は adapter が渡した順のまま回していた = 一次資料の並べ替えを落としていた。Delisting・宇宙は場面に無い |
| SubscriptionFrontierTimeProvider.cs UpdateCurrentTime(57-96) | 63-73 行の MoveNext の条件(`subscription.UtcStartTime == _utcNow` など) | 再現では購読は全て最初の frontier の時刻に始まる。以後 `Current == null` で終わっていない購読は無い |
| AlgorithmManager.cs Run | 197-201 行(状態が Running でないと止める)/ 204 行(取消で止める)/ 216 行(口座の評価額 ≤ 0 で止める)/ 247 行 時刻の脈 / 256 行以降 口座・予定の事象・分割・注文の処理 / 360-369 行(状態・実行時の誤りで止める) | 注文を出さない場面だけを走らせる。時刻の脈は宇宙の選び直しの時だけ |

### どの作りを変えるか

1. **再現の書き直しの決まりを「囲む条件も含めて 1 対 1」にする**: 再現のコード(`opponents/repro_engines/lean52.py`)の各関数の注釈に、引いた範囲の中の条件を全部並べ、(i) 書き直した条件は行を付けてコードに入れる、(ii) 書き直さない条件は、場面でその条件が成り立たない理由を一次資料の行で書く。理由を行で示せない条件は書き直す。
2. **IsInternalFeed を書き直す**: `SubscriptionDataConfig` を再現に足し(`IsInternalFeed`・`TickType`・`SecurityType`・`Symbol`)、DataManager.cs 720-721 行 `subscriptionDataTypes == null && tickType == TickType.OpenInterest || isInternalFeed` のとおりに作る。場面の購読が内部でない根拠: 利用者が銘柄を足す口 `QCAlgorithm.AddSecurity`(QCAlgorithm.cs 2056-2071 行)は `SubscriptionDataConfigService.Add` を `isInternalFeed` を渡さずに呼び、既定は `false`(ISubscriptionDataConfigService.cs 59 行、DataManager.cs 608 行)。資金調達の率 `MarginInterestRate` は CryptoFuture の銘柄を足した時に同じ Add の中で型の組に入る(DataManager.cs 770-773 行)ので、同じく内部でない。`time_slice_create` に 181・194・329 行の条件を入れる。
3. **購読の並べ替えを書き直す**: SubscriptionCollection.cs 213-227 行の `OrderBy(SecurityType).ThenBy(TickType).ThenBy(Symbol)` を `sync` の前に当てる。鍵が同じ購読どうしの順は、原文では `_subscriptions`(ConcurrentDictionary)の列挙の順で、一次資料で決まっていない。委任文 §3「既定も決まっていないときは取りうる値を 2 つ以上走らせて全部の結果を記録に残す」に従い、足した順とその逆の 2 通りを走らせて記録に残す。
4. **Slice.AllData を書き直す**: Slice.cs 57 行 `public IEnumerable<BaseData> AllData` と 305 行 `AllData = data`(TimeSliceFactory の allDataForAlgorithm)。戦略が 1 回の呼び出しで受けた同時刻のデータの並びは、adapter が型の集まりを読む順ではなく、この並びで記録する(型の集まり Bars・Ticks・MarginInterestRates を読む順は場面集の側が決めた順で、LEAN の順ではない)。
5. **機械の試験**: 再現の試験(`test_battery_item0.py`)に、内部の購読のデータが戦略に届かないこと(181・194・329 行)、購読の並べ替えが SortSubscriptions の鍵どおりであること、場面の購読が内部でないこと(DataManager.cs 720-721 行の式)を足す。
