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
2. **IsInternalFeed を書き直す**: `SubscriptionDataConfig` を再現に足し(`IsInternalFeed`・`TickType`・`SecurityType`・`Symbol`)、DataManager.cs 720-721 行 `subscriptionDataTypes == null && tickType == TickType.OpenInterest || isInternalFeed` のとおりに作る。場面の購読が内部でない根拠: 利用者が CryptoFuture を足す口 `QCAlgorithm.AddCryptoFuture`(QCAlgorithm.cs 2621-2624 行)→ `AddSecurity<T>`(3069-3083 行)は `SubscriptionDataConfigService.Add` を `isInternalFeed` を渡さずに呼び、既定は `false`(ISubscriptionDataConfigService.cs 59 行、DataManager.cs 608 行)。資金調達の率 `MarginInterestRate` は CryptoFuture の銘柄を足した時に同じ Add の中で型の組に入る(DataManager.cs 770-773 行)ので、同じく内部でない。`time_slice_create` に 181・194・329 行の条件を入れる。
3. **購読の並べ替えを書き直す**: SubscriptionCollection.cs 213-227 行の `OrderBy(SecurityType).ThenBy(TickType).ThenBy(Symbol)` を `sync` の前に当てる。鍵が同じ購読どうしの順は、原文では `_subscriptions`(ConcurrentDictionary)の列挙の順で、一次資料で決まっていない。委任文 §3「既定も決まっていないときは取りうる値を 2 つ以上走らせて全部の結果を記録に残す」に従い、足した順とその逆の 2 通りを走らせて記録に残す。
4. **Slice.AllData を書き直す**: Slice.cs 57 行 `public IEnumerable<BaseData> AllData` と 305 行 `AllData = data`(TimeSliceFactory の allDataForAlgorithm)。戦略が 1 回の呼び出しで受けた同時刻のデータの並びは、adapter が型の集まりを読む順ではなく、この並びで記録する(型の集まり Bars・Ticks・MarginInterestRates を読む順は場面集の側が決めた順で、LEAN の順ではない)。
5. **機械の試験**: 再現の試験(`test_battery_item0.py`)に、内部の購読のデータが戦略に届かないこと(181・194・329 行)、購読の並べ替えが SortSubscriptions の鍵どおりであること、場面の購読が内部でないこと(DataManager.cs 720-721 行の式)を足す。

## 結果(直した後に書いた)

`<scratchpad>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad`。

### i0-r6-02 を直した根拠

- 型の順と型の決め方: `scenes.py` 140 行 `TYPE_ORDER`(固定した要件 §1 の並び)、156 行 `plan_types`、546 行 `for_target_types`、104 行 `Scene.type_plan`。場面ごとの作り: 182 行 `_merge_by_time`(A・B・C に型の順を割り当て、2 種なら A・B・A、最低 2 種)、223 行 `_typed_events`(最初の 2 種)、403 行 `_same_time_twice`・413 行 `_hand_over_order`(最初の 4 種まで、渡す順は全ての順)。定義の入力に `type_rule` の文、共通の決まりに「型を測らない観点の場面の型(第 r7-1 回)」の段を足した(`gen_definitions.py`、`DEFINITIONS.md` は生成し直し、`python3 gen_definitions.py --check` → `OK`)。
- p1-one-call-per-event は型を採点しない: 期待は `{"observed_ts_ns": [...5 件]}`、`run_battery.py` 189 行 `_grade_times` が出力の列から時刻の列を作る(199 行で GRADERS に入れた)。入力の注記「型は対象が受ける型(対象の配布物の型)を 1 つ選んでよい」。
- runner: `run_battery.py` 610 行 `target_types`(同じ回の p3-<型> が ok・受けた列が空でない・型が全部その型)、632 行 `run_for_types`(型が足りなければ adapter を呼ばずに対応なし、理由に p3 の結果)、652 行 `run_target`(p3 の 6 場面を先に走らせ、1 回目と 2 回目はそれぞれの回の p3 から型を作る。表の行の並びは場面集の順)。
- 規則: `stated_rules.py` の `FIXED_PREDICTED`(132 行。対象ごとに、その対象の型で作った入力に手で当てた並び)と、再現した LEAN の規則(108-117 行。`SubscriptionCollection.SortSubscriptions` の鍵のうち場面で違いうる TickType、同じ鍵は決まらない)。
- adapter: 1 Basana(`opponents/basana_adapter.py` 426・435 行。型ごとに event source、公開の引数 priority は前からの固定値 `TYPE_PRIORITY`)、61 barter-rs(`barter_adapter.py` 225・234 行。入力は 1 本なので連結。同時刻の規則は crate に見つからなかった: `barter/src/backtest/market_data.rs` 28-31 行の説明の逐語を adapter の注釈に書いた)、65 aat・20 VnPy(注記を型に依らない文にした。VnPy は自分の 2 つの型を 1 つの回に混ぜられないことを足の回と tick の回の両方で試した)、23 hftbacktest の p1-one-call-per-event(未定義の番号 99 をやめ、この道具の型の約定で渡す。この場面は型を採点しないので、対象が持つ型を使う)、52 LEAN の再現(`opponents/repro_lean52.py` 239・250 行)、新実装・当方の現状の注記。
- 全 36 対象と再現 1 つを走らせ直した(`sh <scratchpad>/bt/r7-1/item0_r7-1_scenekeeper_runall.sh`、出力 `…/r7-1/item0_r7-1_scenekeeper_runall1.out`、37 行とも `32 scenes`)。記録を `survey_results/*.tsv` に置き換えた。直す前の記録(コミット `4082053`)からの正しさの変化は 18 セル(`…/r7-1/item0_r7-1_scenekeeper_cell_changes.txt`。再現の欄は全部「2 回の実行で同じ」):
  - 1 Basana: p1-merge-by-time・p5-same-time-twice・p5-hand-over-order が 対応なし → 正解と一致(約定・板の写真・板の差分(・足)を型ごとの source で渡した)。
  - 61 barter-rs: p1-merge-by-time・p5 の 2 場面が 対応なし → 不一致(1 本の入力を渡した順のまま処理する。同時刻の規則を書いていない)。52 LEAN の再現: p5 の 2 場面が 対応なし → 不一致(同じ鍵の購読の順は一次資料で決まらない)。
  - 65 aat: p1-one-call-per-event・p1-typed-events が 不一致 → 正解と一致。23 hftbacktest・33 sarthak・37 predictivedev: p1-one-call-per-event が 不一致 → 正解と一致(型の欄を採点しない)。
  - 69 gobacktest・34 QuantCore・23 hftbacktest の p1-typed-events と 23 の p5 の 2 場面: 不一致 → 対応なし(型が 1 種で、runner が adapter を呼ばない)。
- 調査結果の側の場面ごとの最良(規則 5 の順)で正解と一致でないのは p3-mixed-one-run だけになった(P0-3 の場面で、型を持つかそのもの)。P0-5 は 3 場面とも最良が正解と一致(p5-same-time-twice・p5-hand-over-order = 1 Basana)。
- 批評家の試験 `tests/bt/critic/item_0/test_i0r6_battery_p5_measures_order_not_types.py` → 3 passed(直す前 2 failed, 1 passed)。
- 当方の現状は型が足の 1 種なので、p1-merge-by-time・p1-typed-events・p5 の 2 場面は runner が対応なし(直す前も対応なし)。新実装は 32 場面とも正解と一致、試金石は p4-received-time だけが変わる(`PYTHONPATH=src python3 mutant.py --check` → `changed scenes: ['p4-received-time']` / `OK`)。
- 検討表: P0-1 と P0-5 の冒頭の文、P0-1 の 4 行の Basana の p1-typed-events の受けた物、P0-5 の 11 OctoBot の行(probe の記録を引いていた含む側を、新しい場面の記録で書き直し、p5 の 2 場面の「最良が正解と一致でない場面」の文を消した)。`python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md --write` → `OK 誤り 0 件`。
- 足した試験(`test_battery_item0.py` の第 r7-1 回の節、1066-1210 行): `test_no_scene_outside_p0_3_fixes_its_event_types`(P0-3 以外の全場面が、型を対象から取る・対象が選び型を採点しない・約定か足、のどれか)、`test_typed_scenes_are_built_by_their_rule_for_any_set_of_types`(定義の例 = 6 種の場合、1 種・0 種は作らない、2・3 種の割り当てと期待、事象の中身は p3 の見本と同じ)、`test_the_runner_takes_the_types_from_the_p3_results_and_never_asks_the_adapter`、`test_every_record_of_a_typed_scene_used_the_types_of_its_own_p3_rows`(全記録)、`test_every_target_with_a_type_has_a_trade_or_a_bar`(any_type と P0-4 の前提を機械で見る)、`test_one_call_per_event_grades_the_times_of_the_calls_not_the_type`、`test_no_stale_best_claim_in_the_review_table`(検討表の「最良が正解と一致でない場面」が記録と合う。直す途中で P0-5 の 11 の行の古い文をこれが落とした)。書き直した試験: `test_p5_same_time_needs_every_event_and_the_rule_fixed_in_the_scene_set`・`test_p5_hand_over_single_input_…`・`test_stated_rule_recipes_reproduce_the_hand_written_orders`・`test_single_input_form_is_graded_correct_…`(入力の型が対象から決まる形に合わせた。消した試験は無い)。

### i0-r6-04 を直した根拠

- 一次資料(版 `856327ff33869cba98393781000c4ab1d2af423d`)をこの周に `git show` で取った: `<scratchpad>/bt/item0_r7-1_scenekeeper_{SubscriptionDataConfig,SubscriptionManager,QCAlgorithm,ISubscriptionDataConfigService,DataManager,SubscriptionSynchronizer,SubscriptionFrontierTimeProvider,AlgorithmManager,SubscriptionData,Slice,SubscriptionCollection,Global,Subscription,FileSystemDataFeed}.cs`(TimeSliceFactory.cs は第 r6-3 回の `…/r6-3/item0_r6-3_scenekeeper_TimeSliceFactory.cs`)。読むだけで、何も走らせていない。
- IsInternalFeed: `opponents/repro_engines/lean52.py` の `time_slice_create` に 181 行(319 行)・194 行(322 行)・329 行(329 行)の条件を入れた。140 行 `IsSubscriptionRemoved`(314 行)・148 行 `list.Count == 0` も入れた。書き直さない条件(151-163・165-173・225-311・316-317・322-325・331-363・375-386 行)は、場面で成り立たない理由を行で注釈に書いた。
- 場面の購読が内部でない根拠: `data_manager_add`(150 行)= DataManager.cs 720-721 行の式。利用者の CryptoFuture は `AddCryptoFuture`(QCAlgorithm.cs 2621-2624 行)→ `AddSecurity<T>`(3069-3083 行)で `isInternalFeed` を渡さない(既定 false、ISubscriptionDataConfigService.cs 59 行・DataManager.cs 608 行)。資金調達の率は DataManager.cs 770-773 行で同じ Add の型の組に入る。
- 同じ根で落としていた機構: 購読の並べ替え(205 行 `sort_subscriptions` = SubscriptionCollection.cs 213-227 行、`sync` の 351 行で当てる)、`Slice.AllData`(277 行、Slice.cs 57・305 行。adapter は型の集まりを読む順ではなくこの順で記録する、`repro_lean52.py` 134 行)、frontier の MoveNext の条件(234 行 = SubscriptionFrontierTimeProvider.cs 63-73 行)、fill-forward(場面集の側が公開の引数 `fillForward: false` で足す。FileSystemDataFeed.cs 239・274-277 行で、偽なら FillForwardEnumerator を足さない。SubscriptionDataConfig.cs 242 行)。Sync・AlgorithmManager の書き直さない条件も行と理由を注釈に書いた。
- 同じ鍵の購読の順は一次資料で決まらない(ConcurrentDictionary の列挙の順)ので、足した順と逆の順の 2 通りを走らせ、逆の順の結果を記録の detail に残した(p5 の 2 場面)。
- 再現の結果: 直す前と同じ場面は同じ正しさ(p1 の 3 場面・p3・p5-same-stream-order)。p5 の 2 場面が走るようになり不一致(上)。
- 試験: `test_lean_reproduction_keeps_internal_feeds_out_of_the_slice`(内部の購読の約定と資金調達の率は OnData に届かない、場面の購読は内部でない、OpenInterest は内部)、`test_lean_reproduction_sorts_the_subscriptions_by_their_key`。

### 試験の結果(コマンドと末尾の行)

- `PYTHONPATH=src python -m pytest tests/bt/`(`setsid nohup` で切り離し、記録 `<scratchpad>/bt/r7-1/pytest_item0_r7-1_scenekeeper.log`)→ `1 failed, 923 passed, 2 skipped in 89.92s`。その後の直し(再現の注釈と fill-forward の欄だけ)の後に `PYTHONPATH=src python -m pytest tests/bt/battery/item_0/ tests/bt/critic/item_0/test_i0r6_battery_p5_measures_order_not_types.py tests/bt/critic/item_0/test_i0r5_battery_opponent_grading.py` → `70 passed`。
- 落ちる 1 件 `tests/bt/critic/item_0/test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order` は**試験自身の誤り**と判断した(場面集の規則 8。批評家の試験は変えていない): 試験の中の `_event`(64-72 行)が約定・足・資金調達・清算の 4 型だけを核の事象にし、それ以外を清算として作る。定義に載せた p5 の入力は、第 r7-1 回から 6 種を持つ対象の例 = 約定・板の写真・板の差分・足なので、板の写真で `KeyError: 'price'` になる。試験が確かめる性質(1 本の入力の順を守る対象を、その形の規則で採点すると正解と一致)は、同じ核を 4 型(約定・足・資金調達・清算)の入力で通す場面集の試験 `test_single_input_form_is_graded_correct_for_the_core_keeping_one_input_in_order` が通っている(`scenes.for_target_types` でその 4 型の入力を作る)。次の周の批評家に確かめてもらう。

### 提出前の吟味(委任文 §3、直す役の (1)〜(5))

1. 読み直したもの: 固定した要件(REQUIREMENTS.md §1・§2 の P0-1・P0-5 の測り方)、場面集の規則 1〜9、これまでの指摘(i0-r6-02・i0-r6-04 と、ROOTCAUSE_r6-1〜r6-3 の指摘)。指摘ごとの根拠は上の 2 節。
2. 同じ根の全箇所: i0-r6-02 は全 32 場面の型の決め方を表にし(上の「同じ根を全体で探した結果」)、p1-merge-by-time・p1-typed-events・p1-one-call-per-event・p5 の 2 場面の 5 場面を直した。約定か足を許す場面(any_type と P0-4 の 2 場面)は、届けた型のある全対象が約定か足を持つことを機械の試験にした。検討表の同じ根の文(P0-1・P0-5 の冒頭、11 OctoBot の行、Basana の p1-typed-events の受けた物)を直し、古い「最良が正解と一致でない場面」を機械で落とす試験を足した。i0-r6-04 は再現が引く一次資料の範囲の全部の条件を数え、書き直すか、行で理由を書いた(IsInternalFeed の 3 か所、並べ替え、AllData、frontier の条件、fill-forward)。
3. 批評家の試験と場面集の試験: 上の「試験の結果」。落ちる 1 件は試験自身の誤り(理由は上)。
4. 非常に厳しい批評家なら何を [止める] にするか、と潰したこと:
   - 「p1-merge-by-time の最低 2 種は要件に無い。1 種の対象を型の数で対応なしにしている」→ 固定した要件 P0-1 は「同期のバー逐次ループではないこと」を問い、同じ型だけの入力を時刻で合わせるのはバーの逐次ループ(複数の系列を日時で揃える)でもできるので、1 種では P0-1 の区別が測れない。理由を「正解の出し方」に書いた。当方の現状(足 1 種)も同じ扱い(直す前も対応なし)。
   - 「型の順が新実装に有利」→ 順は固定した要件 §1 の並びで、対象によらず 1 つ。新実装は 6 種を持つのでどの順でも同じ。型の少ない対象ほど p5-hand-over-order の渡す順の通りが減る(新実装 24 通り、2 種の対象 2 通り)ので、動くのは調査結果の側に有利な向きだけ。
   - 「adapter が型を選べる」→ 選ぶのは runner(`run_for_types`)。adapter は受け取った入力を渡すだけで、全記録の detail の型が同じ記録の p3 の行から作った型と同じことを試験で見る。
   - 「p3 の結果が他の観点を決めている」→ runner が使うのは「その型の事象を届けたか」だけ(値・時刻・件数の正しさは使わない: 1 本多く届けた足の対象も足を持つと数える、試験 `test_the_runner_takes_…`)。
   - 「p1-one-call-per-event の型を採点しないのは緩めた」→ 固定した要件の P0-1 の測り方に型の名前の一致は無く、この場面が測るのは呼び出しの回数と時刻(「何を測るか」)。型を持つかは P0-3 と p1-typed-events が測る。出所の検め(対象の型で、対象が届けた)はそのまま当たる。
   - 「LEAN の fill-forward を切るのは弱めた/足した工夫」→ 公開の引数で選べる設定(QCAlgorithm.cs 2621 行)で、1 Basana の priority と同じく場面集の側が決めた設定。注釈に行を書いた。
   - 「barter-rs に同時刻の規則を与えていない」→ crate の説明と engine の時計を読んで、同時刻の並べ方を書いた文が無かった(adapter の注釈と記録の detail に場所)。規則を明記していない対象は規則どおりにならない(場面の定義どおり)。
5. 場当たりの直しでないか: 指摘の 2 場面の型を Basana の型に合わせる直しにはしていない。型を場面の側で決める作り自体をやめ、対象の型から機械で作る作りに替え、全場面・検討表・再現に同じ決まりを当てた。試験だけを特別扱いする分岐は無い(runner の分岐は `Scene.type_plan` の有無だけで、対象の名前を見ない)。
