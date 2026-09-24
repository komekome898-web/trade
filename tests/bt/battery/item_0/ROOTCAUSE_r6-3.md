# 場面集への指摘ごとの根本原因と直し(項目 0、第 r6-3 回の直し、場面係、2026-09-24)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`。起動文の指紋は `4c4cfc6e4052`、作業木の版も `4c4cfc6e4052`(`sha256sum docs/DATA/delegations/20260923_backtest_env_prompt.md | cut -c1-12`、全 162 行を読んだ)。
指摘の逐語: 起動文に貼られた 2 件(br6-2-1 [止める]・br6-2-2 [聞く])。前の周の直し `ROOTCAUSE_r6-2.md`・`ROOTCAUSE_r6-1.md` も読み直した。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
当てた委任文の決まり: §3「根本的解決」(直す前に指摘ごとの根本原因と変える作りを書く / 指摘の文言だけに合わせない)、「場面集の規則」1・2・4・5・6・9、「調査結果の側の選び方」、「動かせない候補の検討と再現」(段の無い観点は「実装のコードで確かめられる候補を全部再現する」が既定で、スキップは「上位互換」を 1 能力ずつ示せるときだけ)、「提出前の吟味」(1)〜(5)。

**この節(根本原因・変える作り・[聞く] への答え)は直す前に書いた。**直した結果と根拠は最後の「結果」の節に足す。

## 直す前に確かめた穴(コマンドと出力)

`python3 <scratchpad>/bt/r6-3/item0_r6-3_scenekeeper_hole_probe.py`(出力の記録 `…/r6-3/item0_r6-3_scenekeeper_hole_probe.before.txt`)。場面集の外の一時ディレクトリに書いた偽の道具(`Event` の class と、受けた物を戦略に渡す `deliver`)を対象にし、runner の `checked` に 3 つの carrier を渡した:

```
delivered by the tool            ok   (道具の deliver が戦略に渡した Event)
built by the adapter in the call ok   (戦略の呼び出しの中で場面集の側が Event(...) を組んだ)
adapter's object, never handed   ok   (adapter が持つ Event を、道具に一度も渡さずに記録した)
```

3 つとも採点に進んだ。後の 2 つは、対象が戦略に届けていない物である。

記録の全部を数えた結果(全 36 対象の `survey_results/*.tsv` の `provenance_1` の carrier・`of`・`via` のうち、型を定義したファイルが対象の配布物にあるもの。コマンドは下):

| 対象 | carrier の型 | 対象が戦略に届けた事実(passed_by / returned_by) | 場面集の側が持つ(held_by) |
|---|---|---|---|
| 1 Basana | `BarEvent`・`TradeEvent`・`PartialOrderBookEvent`・`OrderBookDiffEvent` | passed_by = `basana/core/dispatcher/backtesting.py`・`base.py` | 無し |
| 1 Basana(試しの via) | `basana.core.bar.Bar` | 無し(受けた `ev` の属性 `ev.bar`) | 無し |
| 34 QuantCore | `quantcore._core.MarketDataEvent` | 無し(母語の `BacktestEngine.run` が呼ぶので Python のフレームに見えない) | 無し |
| 55 backtesting.py | `backtesting._util._Data` | 無し(戦略の物の属性 `self.data`) | 無し |
| 53 Rqalpha | `rqalpha.model.bar.BarObject` | 無し(受けた `bar_dict` の `[OID]` の読み) | 無し |
| 122 PyAlgoTrade | `pyalgotrade.bar.BasicBar` | 無し(受けた `bars` の `[INST]` の読み) | `pyalgotrade_adapter.py:run:feed` |
| 12 pybotters | `pybotters.store.StoreChange` | 無し(`watch()` の非同期の反復が返す) | 無し |
| 121 QSTrader | `qstrader.data.backtest_data_handler.BacktestDataHandler` | **無し。adapter が作って閉包で戦略に持たせた物**(道具が戦略に渡すのは `dt` だけ) | `qstrader_adapter.py:run:dh` |
| 20 VnPy | `vnpy.trader.object.BarData`・`TickData` | passed_by = `vnpy_ctastrategy/backtesting.py` | `vnpy_adapter.py:run:data`(adapter が組んで渡した入力) |
| 他(2・4・6・18・23・62・65・68・75) | 各道具の class | passed_by か returned_by が道具の配布物 | 無し |

```
cd tests/bt/battery/item_0 && python3 - <<'EOF'   # 出力は上の表(逐語の全文は …/r6-3/item0_r6-3_scenekeeper_inventory.before.txt)
import csv,json,glob,collections; csv.field_size_limit(10**9)
… 各記録の dict のうち type と type_file を持つもの(carriers・carriers/tag・reads/of・attempts/via)を集め、type_file が site-packages の下のものについて
  (対象, 位置, type, passed_by, returned_by, held_by, called_by の有無, in_args) → {正しさ: 場面} を出した
EOF
```

## br6-2-1 [止める] own-class の carrier に、対象が届けたかの検めが当たっていない

- **なぜ起きたか(根本原因)**:
  1. **「対象の物である」を、型の出所(誰の class か)と届いた道(誰が戦略に渡したか)の 2 つに分けずに 1 つの問いにしていた**。第 r6-1 回に「型を定義したファイルが対象の配布物にあれば対象の物」と決め、第 r6-2 回は共有の型(dict・関数)だけに「来た道」を足した。共有の型では型の出所が何も示さないので来た道が要る、と考えたが、**対象の class でも「その物を対象が戦略に届けた」ことは型からは出ない**。型は「対象がその型を持つ」ことしか示さず、「この物が対象の経路を通って届いた」ことは示さない。上の probe のとおり、adapter が戦略の呼び出しの中で対象の class を組んでも、adapter が持つ物を道具に渡さずに記録しても通った。
  2. **限界として書いた穴を、閉じずに記録だけにした**。`ROOTCAUSE_r6-2.md` の限界 1 は、この穴を「母語のコードから呼ぶ 34 QuantCore では来た道が Python に見えない」ことを理由に残した。見えない道があることは、見える道まで検めない理由にならない(母語の呼び出しは別の手段で示せる。下の 3)。しかも「3 対象だけが passed_by 等を持たない」と書いた数え方は `passed_by`・`returned_by`・`called_by`・`in_args` のどれか 1 つでもあれば「持つ」としたもので、`in_args`(戦略が受けた物の中に届く)と `called_by`(呼んだのが対象)を数えたため、実際には届けた事実の無い 55 backtesting.py・53 Rqalpha・122 PyAlgoTrade・121 QSTrader の carrier が「持つ」側に入っていた。監査役の指摘どおり、「在る」ことと「検めに使われている」ことを混ぜた書き方だった。
  3. **試験が、道具が組んで渡した物の道しか試していなかった**。第 r6-2 回の試験は偽の道具の `event()`(道具のモジュールの中で `Event(...)` を組む関数)の物を渡しただけで、場面集の側が対象の class を組んで記録する形・adapter が持つ対象の class の物を渡さずに記録する形を 1 つも試していない。

- **監査役の例(Basana・aat の `_event()`)への答え**: `opponents/basana_adapter.py` の `_event()` と `opponents/aat_adapter.py` の `_event()` は、場面の入力を対象の公開の class に直して、**対象の入口に渡す入力**を作っている(Basana は `FifoQueueEventSource(events=[...])` → dispatcher、aat は取引所の物の中の列 → engine)。これは新実装の adapter(`adapters/new_impl.py` 110-129 行の `_event` が `core.TradeEvent(...)` ほかを組んで `CoreEngine(strat, events, …)` に渡す)と当方の現状の adapter(`adapters/current_impl.py` が DataFrame を組んで渡す)と同じ形で、どの対象にも場面の入力は adapter が対象の入口の形に直して渡すしかない。場面が測っているのは、**渡された入力を対象がどう届けるか**(型を保つか・時刻の順・1 件 1 回・時刻の精度)である。よって「adapter が対象の class で入力を組んだこと」そのものは欠陥ではない。欠陥は、**戦略が記録した物が、対象が届けた物だと示されていない**こと(上の 1)で、Basana の carrier は記録の上で `passed_by` = Basana の dispatcher(`basana/core/dispatcher/backtesting.py`・`base.py`)を持つので、この検めを当てても通るはずである(直したあと、全対象を走らせ直して確かめる)。ただしこれは直したあとの機構の結果で示すことで、この文では断定しない。

- **どの作りを変えるか**:
  1. **型の出所と届いた道を、すべての carrier(`carriers`・読み出しの `of`・試しの `via`)に別々に要求する**(`run_battery.origin_problem`)。
     - (T)型: 対象の class(型・dtype・札を定義したファイルが対象の配布物)か、共有の型なら「対象が作った物」(場面集の側が持つ物でない = 第 r6-2 回の `held_by` の決まりのまま)。
     - (D)**届いた道**(新しく、対象の class にも当てる): 次のどれかが対象の配布物のコードである。(α)戦略の呼び出しにその物を引数として渡した呼び出し元(`passed_by`)。(α')その物を中に持つ引数を渡した呼び出し元(`reached_by`。場面集の側の物の属性を通る道は数えない = 戦略の `self` に adapter が付けた物を拒むため)。(α-母語)戦略を母語のコードから呼んだ対象の関数(`native_by`。下の 3)。(β)その物を返した対象の関数(`returned_by`。`common.read`、属性の読み `common.attr`、反復 `common.iterate`・`common.aiterate`)。
     - 対象の class の物を adapter が入力として組んで対象に渡し、対象が届けたもの(`held_by` があり D も満たす)は通し、記録に `input: adapter が組んで対象に渡した入力` と残す(新実装・当方の現状・調査結果の側のどれも同じ)。共有の型で `held_by` があるものは第 r6-2 回どおり拒む(型を adapter が決めているので)。
  2. **記録の欄の意味を固定する**: `in_args`・`called_by` は判定に使わない欄なので記録から外し、判定に使う欄(`passed_by`・`reached_by`・`native_by`・`returned_by`・`held_by`)だけを残す。「持つ」と「使われている」を取り違えない。
  3. **母語の呼び出し元を記録する**: runner が各場面を走らせる間だけ `sys.setprofile` で「今走っている C の関数と、それを呼んだ Python のフレーム」の列を持ち(`common.native_tracker`)、戦略のフレームの 1 つ外が C の関数の呼び出しの途中なら、その C の関数の定義のファイル(pybind11 なら拡張の `.so`)を `native_by` にする(34 QuantCore の `BacktestEngine.run`)。`common._profiled` はこの追跡を途切れさせないよう前の hook に渡す。
  4. **adapter を、届いた道が記録に出る形に直す**(場当たりの特別扱いをせず、共通の部品で): 55 backtesting.py は `self.data`(道具の `Strategy.data` の property)を `common.attr` で、53 Rqalpha・122 PyAlgoTrade は受けた物の `[…]` を `common.read(bar_dict.__getitem__, …)` で、12 pybotters は `watch()` の反復を `common.aiterate` で、1 Basana の試しの via `ev.bar` は `reached_by` で示す。121 QSTrader は道具が戦略に渡すのが `dt` だけなので、carrier を `dt`(道具が渡した物)にし、足の型を戦略に届けない p3-bar は「対応なし」にする(要件 P0-3「型が無ければ『対応なし』」)。
  5. **試験を穴の形ごとに書く**: 場面集の側が戦略の呼び出しの中で対象の class を組んだ物 / adapter が持つ対象の class の物を渡さずに記録した物 / 戦略の `self` に adapter が付けた対象の class の物 → 拒む。道具が渡した物・道具の関数が返した物・道具が渡した物の中の物・母語のコードが渡した物・adapter が組んで道具に渡し道具が届けた入力 → 通る。
  6. **検討表の含む側の文を、直した検めを通った記録だけで引く**: `test_every_scene_a_containment_cites_as_correct_is_correct_in_the_records` は今の `survey_results` の正しさを見ているので、走らせ直した記録で落ちれば文を直す。

- **同じ根の欠陥を場面集の全体で探した場所**: carrier(21 の値の場面・能力の場面の CARRIER_SCENES)・読み出し(p4-visible-at-step の `of`)・試し(p4-future-read-attempt の `via`)・reader(p2-iso-* の `qualname`: これは「対象の関数か」だけを見る欄で、読んだ値は戦略の側の `fn(...)` の返り値を場面の出力に書くので、届いた道の問いに当たらない。関数そのものの定義のファイルが対象の配布物かは第 r6-2 回の検めのまま)・札(`carrier_tag`・`carrier_const` の札は物ではなく印なので、物の側に D を当てれば足りる)・当方の現状と新実装の adapter(同じ検めを通る)。

## br6-2-2 [聞く] 検討表の再現が 0 件で、スキップが全部「上位互換」なのは族の縮小になっていないか

- **答え**: 行ごとに 1 能力ずつ含む側を書いていた(`test_superset_and_absent_rows_answer_every_ability_with_a_source` が形を、`test_every_scene_a_containment_cites_as_correct_is_correct_in_the_records` が引いた場面の結果を機械で見ている)ので、理由の無いスキップではない。しかし**判断の作りに穴があり、その穴によって再現すべき候補を 1 件スキップしていた**。よって「再現 0 件」は、規則どおりの結果ではなく、作りの穴の結果を含む。KA-06/KA-24 と同じ型(族を縮める向きの誤り)が 1 件あった、と答える。
- **なぜ起きたか(根本原因)**:
  1. **「上位互換」を機構の水準だけで判定し、「その候補を再現したら調査結果の側の場面ごとの最良が上がるか」を問わなかった**。スキップしてよい理由は「明らかに弱い」ことで、比べる相手の強さは場面ごとの最良の行で決まる(委任文 §3「場面ごとに動かせた道具のうち最も良い結果を寄せるのは、1 つの道具より強い相手を置くため」)。ところが含む側の文は「機構 X は機構 Y を含む」で止まり、**含む側の候補がその場面で正解と一致でないとき**(入力の型を持たないため対応なし)も、入力の型を外した試し(`survey_results/attempts/1.log` の probe)で「含む」と書いた。走った候補の最良が正解と一致でない場面は、今の記録で p1-merge-by-time・p3-funding・p3-mixed-one-run・p5-same-time-twice・p5-hand-over-order の 5 つ(コマンドは下)。この 5 場面に届くかは、スキップする候補の側の型で決まるのに、それを行で問うていなかった。
  2. その結果、**52 QuantConnect LEAN(観点 P0-1)をスキップしていた**。P0-1 の行は能 3(時刻の順に合わせる)を Basana の `EventMultiplexer` で「含む」とし、Basana は資金調達の型を持たないので p1-merge-by-time は対応なしと書いた。しかし LEAN は資金調達の率の型 `MarginInterestRate`(`Common/Data/Market/MarginInterestRate.cs`。取引所の先物の資金調達を `Common/Securities/CryptoFuture/BinanceFutureMarginInterestRateModel.cs` がこの型で口座に当てる)を、足・ティックと同じ同期の機構(`Engine/DataFeeds/SubscriptionSynchronizer.cs`)で `Slice.MarginInterestRates`(`Common/Data/Slice.cs` 164-166 行)として戦略に渡す。版は `856327ff33869cba98393781000c4ab1d2af423d`(この周に中身を取らない clone で読んだ。記録 `…/r6-3/item0_r6-3_scenekeeper_lean`)。**LEAN を再現すれば p1-merge-by-time の最良が「対応なし」から上がりうる**ので、「明らかに弱い」とは言えない。
  3. 観点の間の能力の受け渡しを行で書かなかった。p1-merge-by-time は「時刻の順」(P0-1)と「資金調達の型」(P0-3)の両方を要るが、52 は P0-3 の候補の集まりに無いので、資金調達の型をどこでも読んでいなかった。
  4. 機械の検めが「場面が正解と一致と書いた場所」しか見ておらず、「最良が正解と一致でない場面について、スキップする候補がそこへ届かないこと」を見ていなかった(穴が機械で見えなかった)。
- **どの作りを変えるか**:
  1. **スキップの行の決まりに 1 つ足す**(検討表の「読み方」の節): その観点の場面のうち、走った候補と再現した候補の最良が正解と一致でない場面ごとに、`最良が正解と一致でない場面 <場面>: <その場面に要る型か能力>が無い(出所の行)` と書く。書けない(その候補がその場面に届きうる)ときは、スキップせず再現する。
  2. **機械で検める**(`test_battery_item0.py` に足す): 今の `survey_results` から観点ごとに最良が正解と一致でない場面を出し、スキップの行ごとにその場面が上の形で書かれていることを確かめる。場面が変われば(再現で最良が上がれば)要る場面の組も変わる。
  3. **52 LEAN を P0-1 で再現する**(`opponents/repro_52_lean.py`)。一次資料どおりの最小の書き直し: 型(`TradeBar`・`Tick`・`MarginInterestRate`、時刻は 100 ns 刻みの `DateTime`)、同期(`SubscriptionFrontierTimeProvider` の「各入力の次の EmitTimeUtc の最小」を frontier にし、`SubscriptionSynchronizer.Sync` が frontier 以下の事象を入力ごとに集める)、`TimeSliceFactory.Create` の `Slice`(型ごとの集まり)、`AlgorithmManager` の `if (timeSlice.Slice.HasData) algorithm.OnData(slice)`。再現の注釈に行と URL を 1 対 1 で書く。再現しない機構(注文・約定・費用・口座・時計)の場面は「結果なし」(再現していないので結果が無い。「対応なし」にすると、機構を持つ LEAN を持たないと書くことになり、場面ごとの最良を不当に上げうる)。再現の中の対象の側のコード(同期と Slice)は `opponents/repro_engines/` に分け、runner はそのファイルだけを再現の対象の置き場所にする(adapter の側と同じファイルに置くと、戦略を呼んだのが対象のコードか場面集の側かを見分けられない)。
  4. 検討表の P0-1 の 52 の行を「再現した」にし、同じ観点の他のスキップの行(13・57・63・123)と、P0-3(11・57)・P0-5(11)・P0-6・P0-7 のスキップの行に、上の 1 の文を足す(P0-6・P0-7 は全場面で最良が正解と一致なので足す場面は無い)。
- **上位互換の判定そのものの見直し(同じ根の全行)**: 16 行のスキップを全部、上の 1 の問いで読み直す。今の記録で最良が正解と一致でない 5 場面に要る型は、資金調達(p1-merge-by-time・p3-funding)と清算(p3-mixed-one-run・p5-same-time-twice・p5-hand-over-order は資金調達と清算の両方)。各スキップの候補がこの型を持つかを、既に行に書いた出所で確かめ、持つ候補は再現に回す。

最良が正解と一致でない場面を出したコマンド(全 36 対象の記録):

```
cd tests/bt/battery/item_0 && python3 - <<'EOF'
import csv,glob,collections; csv.field_size_limit(10**9)
order={'正解と一致':0,'対応なし':1,'不一致':2,'結果なし':3}; best={}
for f in glob.glob('survey_results/opp_*.tsv'):
    for r in csv.DictReader(open(f,encoding='utf-8'),delimiter='\t'):
        s=r['scene_id']; c=r['correctness']
        if s not in best or order[c]<order[best[s]]: best[s]=c
print(sorted(s for s,c in best.items() if c!='正解と一致'))
EOF
→ ['p1-merge-by-time', 'p3-funding', 'p3-mixed-one-run', 'p5-hand-over-order', 'p5-same-time-twice']
```

**変えないもの**: 場面の入力・期待・正解の出し方・観点・判定の順(場面集の規則 5)。変えるのは、採点の前の出所の検め、それに合わせた adapter、検討表のスキップの決まりと機械、再現の追加。

## 結果(直したあとに書いた)

合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」。この直しで、(1) 出所の検めは型と届いた道を別々に求める形になり、新実装・当方の現状・調査結果の側・再現のすべてに同じ検めが当たる。(2) 調査結果の側は、スキップが場面ごとの最良を下げていないことを機械で確かめる形になり、スキップしていた 52 LEAN を再現して相手を強くした(新実装が勝ちにくい向き)。

### 作りの変更(どこを変えたか)

- `run_battery.py`: `origin_problem`(型 = 対象の class か、共有の型なら場面集の側が持つ物でない / 届いた道 = `delivered`)。`delivered` と `DELIVERY_FACTS`(`passed_by`・`reached_by`・`native_by` のどれかのファイルか `returned_by` が置き場所にある)。読み出しの `of`・試しの `via` は、対象のコードの関数・method なら届いた道を問わない(`means=True`。コードは事象を運ばない)。場面ごとに `C.native_tracker()` の中で adapter を走らせる(`run_target`)。記録の `compact` で、対象の class の物に `held_by` があれば `input`(adapter が対象の型で組んで対象に渡した入力)と書く。再現の置き場所は `opponents.repro_engines.<名>` だけ(`roots_of`)。
- `adapters/common.py`: `_stack_facts_now` が `passed_by`(物そのものが引数)・`reached_by`(引数の中。場面集の側の物の中は辿らない = `_reachable`)・`native_by`(母語の関数が戦略のフレームを呼んだ。`_ACTIVE_C`・`_track`・`native_tracker`)・`held_by` を作る。判定に使わない `in_args`・`called_by` は記録から外した。`_profiled` は前の hook に渡す(`_chain`)。`attr`(property の getter を `read` で通す)・`iterate`・`aiterate`(反復の `__next__`/`__anext__` が返した物を `returned_by` にする)。`in_scene_set` は `opponents/repro_engines/` を場面集に数えない。
- adapter(届いた道が記録に出る形に。共通の部品で): 55 backtesting.py は `C.attr(s, "data")`(`Strategy.data` の property、backtesting.py 278-279 行)。2 Backtrader は `self.data` が metaclass の付ける素の属性(lineiterator.py 83 行)なので、公開の `Strategy.getdatabyname`(strategy.py 764 行)を `C.read` で通した `_fed(s)`。12 pybotters は `C.aiterate(stream)`。20 VnPy は、VnPy が戦略を作るときに渡す engine(`add_strategy` → `strategy_class(self, …)`)を `_Strat.__init__` で受けた時点に記録(試しの `via=s.cta_engine` はその事実を使う)。121 QSTrader は carrier を QSTrader が渡す `dt` に、同じ時刻の 3 行の場面は `C.read(dh.get_asset_latest_mid_price, dt, SYM)` の返り値に、p3-bar は「対応なし」(戦略に届くのは `dt` だけで足の物が届かない。配布物の Bar・Event を名に持つ class を pkgutil で全部辿って detail に書いた)。
- 再現: `opponents/repro_lean52.py`(場面集の側)と `opponents/repro_engines/lean52.py`(再現した LEAN のデータの道。注釈に一次資料の行)。
- 検討表 `opponents/CONSIDERED.md`: 読み方に「場面ごとの最良と照らす」の決まりを足し、P0-1 の 52 を「再現した」に、P0-1 の 13・57・63・123 の能 3 の含む側を再現した LEAN に、P0-3 の 11・57 と P0-5 の 11 に「最良が正解と一致でない場面」の文を足した。集計は道具が書いた(下)。`survey_counts.py` は再現を検討表の番号で数える。
- 場面の定義(`gen_definitions.py` → `DEFINITIONS.md` の「出所の検め」)と adapter の約束事(`adapters/protocol.py`)に、型と届いた道を別々に示す決まりを書いた。**場面の入力・期待・正解・観点は変えていない**(`git diff --stat -- tests/bt/battery/item_0/scenes.py tests/bt/battery/item_0/stated_rules.py` → 出力なし)。

### br6-2-1 の根拠

- 穴の再現: 直す前 `…/r6-3/item0_r6-3_scenekeeper_hole_probe.before.txt`(`git stash` で `run_battery.py`・`common.py` を HEAD に戻して走らせた。HEAD の 2 本は第 r6-2 回の検めを持つ): `delivered by the tool ok` / `built by the adapter in the call ok` / `adapter's object, never handed ok`。直したあと `…after.txt`: `ok` / `error` / `error`。
- 試験(`test_battery_item0.py` の第 r6-3 回の節): `test_own_class_carriers_must_have_been_delivered_by_the_target`(道具が組んで渡した物 → 通る / 戦略の呼び出しの中で場面集の側が道具の class を組んだ物 → 拒む / adapter が持つだけの物 → 拒む / 戦略の `self` に adapter が付けた物 → 拒む / 道具が渡した物の中の物 → 通る / adapter が組んで道具に渡し道具が届けた入力 → 通り、記録に `input`・`held_by` / 道具の関数が返した物 → 通る)、`test_a_strategy_called_from_compiled_code_shows_the_compiled_caller`(母語の関数 `contextvars.Context.run`(lib-dynload の `_contextvars` の .so)が戦略を呼ぶ形: 追跡の中なら `native_by` = その .so で通る、追跡が無ければ拒む、戦略の中で組んだ物は拒む)、`test_every_recorded_carrier_shows_how_the_target_delivered_it`(全記録の carrier・of・via が届いた道の事実を持つ。`in_args`・`called_by` が記録に無い)、`test_quantcore_is_placed_by_its_compiled_caller`。
- 全 36 対象と再現 1 つを走らせ直した(`sh …/r6-3/item0_r6-3_scenekeeper_runall.sh`、出力 `…/r6-3/item0_r6-3_scenekeeper_runall2.out`、37 行とも `32 scenes`)。出所の検めの拒否は 0 件(`grep -l "出所の検めで採点しない" …/r6-3/opp_*.tsv …/r6-3/repro_*.tsv` → 出力なし)。第 r6-2 回の記録からの正しさと再現の欄の変化は 1 セルだけ: `('opp_qstrader', 'p3-bar') ('不一致', …) -> ('対応なし', …)`(上の QSTrader の直し)。**1 Basana の全 32 場面の結果は変わらない**(`{'対応なし': 12, '正解と一致': 18, '不一致': 2}`)。Basana の carrier は `passed_by` = `basana/core/dispatcher/backtesting.py`・`base.py`(dispatcher が handler に渡した)で、届いた道の検めを通った(記録の一覧 `…/r6-3/item0_r6-3_scenekeeper_inventory.after.txt`)。65 aat の carrier も `passed_by` = `aat/engine/engine.py`。
- 直す前に届けた事実の無かった carrier の、直したあとの事実(同じ一覧から): 55 backtesting.py `returned_by` = `backtesting/backtesting.py` / 2 Backtrader `returned_by` = `backtrader/strategy.py` / 12 pybotters `returned_by` = `pybotters/store.py` / 34 QuantCore `native_by` = `quantcore/_core.cpython-311-x86_64-linux-gnu.so` / 53 Rqalpha・122 PyAlgoTrade `reached_by`(受けた `bar_dict`・`bars` の中) / 121 QSTrader `passed_by` = `qstrader/trading/backtest.py` ほか(carrier は `dt`) / 20 VnPy の試しの via `passed_by` = `vnpy_ctastrategy/backtesting.py`。
- 当方の現状と新実装も同じ検めを通る: `--target new_impl` → `{'正解と一致': 32}; 2 回で違う=0`、`--target current_impl` → `{'対応なし': 23, '正解と一致': 8, '不一致': 1}; 2 回で違う=0`(第 r6-2 回と同じ)、`--target mutant` → `{'正解と一致': 31, '不一致': 1}`(記録 `…/r6-3/item0_r6-3_scenekeeper_{new_impl,current_impl,mutant}.tsv`)。
- 検討表の含む側の文が引く場面が今の記録で正解と一致: `test_every_scene_a_containment_cites_as_correct_is_correct_in_the_records` が通る(引く候補に再現した 52 を足した)。

### br6-2-2 の根拠

- 52 LEAN の再現の結果(`survey_results/repro_lean52.tsv`、全 32 場面を 2 回): `{'正解と一致': 6, '結果なし': 17, '不一致': 3, '対応なし': 6}; 2 回で違う=0`。正解と一致は p1-merge-by-time・p1-one-call-per-event・p1-typed-events・p3-bar・p3-funding・p5-same-stream-order。不一致は p2-event-time-exact(`1700006400123456700`、DateTime は 100 ns 刻み)・p2-one-ns-apart(2 件とも同じ刻み)・p3-trade(LEAN の約定のティックに売り買いの向きの欄が無い)。対応なしは板・板の差分・清算と、清算を含む p3-mixed-one-run・p5-same-time-twice・p5-hand-over-order。結果なしは再現しなかった機構の 17 場面。
- 調査結果の側の場面ごとの最良(走った候補と再現): p1-merge-by-time と p3-funding が「対応なし」から「正解と一致」に上がった。最良が正解と一致でない場面は p3-mixed-one-run・p5-same-time-twice・p5-hand-over-order の 3 つになった(`_best_by_scene`)。
- 機械の検め: `test_every_skip_names_what_it_lacks_for_each_scene_the_survey_side_misses`(スキップの 15 行のうち、最良が正解と一致でない場面を持つ観点の行 = P0-3 の 11・57、P0-5 の 11 に、場面ごとの「無い」と出所の行があること)、`test_the_reproduction_raised_the_best_where_the_review_said_it_would`、`test_superset_and_absent_rows_answer_every_ability_with_a_source`(含む側に再現した候補を認める)。
- 検討表の集計(道具が書いた): P0-1 は 再現した 1・スキップ 4・再現できない 2。計は 動かせない 31 のうち 再現した 1・持たないと確認した 4・スキップ 15・再現できない 11。
- 残るスキップ 15 行の読み直し(同じ根の全行): P0-1 の 13・57・63・123 は、この観点の 3 場面の最良が全部正解と一致(p1-merge-by-time は再現した LEAN)なので、再現しても最良は上がらない。P0-6 の 13・52・123、P0-7 の 13・38・52・63・123 も、その観点の全場面で最良が正解と一致。P0-3 の 11・57 は p3-mixed-one-run に要る型(11: 板の差分・資金調達・清算を検証の入力から流す型、57: 資金調達と清算)が無いことを行で示した。P0-5 の 11 は p5-same-time-twice・p5-hand-over-order に要る資金調達と清算を検証の入力から流す型が無い。よって今のスキップは、どれも場面ごとの最良を下げていない。

### この検めが見ないもの(限界。全部書く)

1. **`returned_by` は、読みが戦略の呼び出しの中で行われたかを見ない**。対象の関数が返した物は、adapter が戦略の外で呼んで記録しても「返した」になる(23 hftbacktest は利用者が自分で loop を書く作りなので、呼び出しの中かを求めると区別できない)。対象の関数が物を作って返したことは示す。
2. **`reached_by` は、引数の中の深さ 3 まで**(`_reachable`)。それより深い所の物は届いた道を示せず、拒まれる向き(採点しない向き)に倒れる。
3. **母語の呼び出しの記録は、runner が場面を走らせる主の thread の中だけ**。道具が別の thread から戦略を呼ぶと `native_by` は付かない(Python のフレームで呼ぶなら `passed_by` が付く)。
4. **試しの `via` が対象のコードの関数・method なら、その試しの中でその関数が呼ばれたかは見ない**。引数の束ねで止まった呼び出し(`TypeError`)は対象のフレームが立たないので、走ったコードに出ないため(1 Basana・37 ThePredictiveDev の名指しの試し)。
5. **対象の class の入力(adapter が組んで対象に渡した物)は数える**。場面の入力はどの対象にも adapter が入口の形に直して渡すしかないので、これを拒むと新実装も含めて全対象の型の場面が測れない。対象がその入力を届けたこと(届いた道)は求める。
6. 読み出しの「対象のコードが走った」は走ったことしか見ない(第 r6-2 回の限界 3 のまま)。
7. 再現の機構の正しさ(一次資料どおりか)は機械では見ない。注釈の行と一次資料を批評家と監査役が突き合わせる。再現しなかった機構の 17 場面は結果なしで、そこでの LEAN の強さとは比べていない(P0-6・P0-7 は走った候補の最良が全場面で正解と一致なので、比べる相手の強さは下がらない)。
