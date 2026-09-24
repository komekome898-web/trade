# 場面集への指摘ごとの根本原因と直し(項目 0、第 r6-2 回の直し、場面係、2026-09-24)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`。起動文の指紋は `4c4cfc6e4052`、作業木の版も `4c4cfc6e4052`(`sha256sum docs/DATA/delegations/20260923_backtest_env_prompt.md | cut -c1-12`、全 162 行を読んだ)。
指摘の逐語: 起動文に貼られた 2 件(br6-1-1 [止める]・br6-1-2 [直す])。前の周の直し `ROOTCAUSE_r6-1.md` も読み直した。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
当てた委任文の決まり: §3「根本的解決」(直す前に指摘ごとの根本原因と変える作りを書く / 指摘の文言だけに合わせない)、「場面集の規則」1・2・4・6・8・9、「調査結果の側の選び方」、「提出前の吟味」(1)〜(5)。
この 2 件に [聞く] は無い。

**この節(根本原因と変える作り)は直す前に書いた。**直した結果と根拠は最後の「結果」の節に足す。

## 直す前に確かめた穴(コマンドと出力)

`python3 <scratchpad>/bt/r6-2/item0_r6-2_scenekeeper_hole_probe.py`(`tests/bt/battery/item_0` で実行。出力の記録 `…/r6-2/item0_r6-2_scenekeeper_hole_probe.before.txt`)。runner の `checked` に、手で作った出所を渡した:

```
dict      ('ok', None)      carriers ["builtins.dict"]                                      (p2-event-time-exact)
function  ('ok', None)      carriers ["builtins.function"]                                  (p5-same-stream-order)
tag       ('ok', None)      carriers ["aat.core.data.event.Event[opponents.aat_adapter.MyKind.TRADE]"]  (p3-trade)
by hand   ('ok', None)      carriers ["anything.TRADE_EVENT"](物の無い、手で書いた文字列)  (p3-trade)
reader    ('ok', None)      reader "pytz.parse"(除外の一覧に無い共有の部品)                (p2-iso-utc)
```

5 つとも採点に進んだ(`ok`)。どれも「対象の配布物の物である」ことを何も示していない。

## 共通の根本原因

br6-1-1・br6-1-2 と、下の表の同じ根の欠陥は、全部ひとつに行き着く。**第 r6-1 回に作った出所の検めは、「対象の物である」ことを正に示させず、「場面集の側の名前でない」ことを確かめるだけだった**(除外の一覧による推論 = 「場面集の物でない ⇒ 対象の物」)。

1. **除外で決めた**。`made_by_scene_set` は carrier の文字列の最初のドットまでが `BATTERY_TOPS`(場面集のファイル名)にあるかだけを見た。p2-iso の reader も `BATTERY_TOPS` と `FOREIGN_READER_TOPS`(pandas・datetime・builtins ほか 13 個)の除外だった。この推論が成り立つのは、型がどちらか一方だけに定義されているときに限る。**誰でも作れる共有の型**(`builtins.dict`・関数・標準の `datetime`・`pandas.DataFrame`・numpy の行・numba が作った class)の物は、場面集の側が作っても対象が作っても同じ名前になり、除外の一覧に無いので「対象の物」に数えられた(br6-1-1)。reader の一覧も、一覧に無い共有の部品(pytz など)を通す同じ形だった。
2. **物ではなく、adapter が渡した文字列を見た**。runner は carrier を文字列として受け取り、その先頭だけを読んだ。そのため (a) carrier の後ろの部分(`carrier_tag` の `[…]` の札の出所)を読まなかった(br6-1-2)、(b) 物から作っていない文字列が通った: hftbacktest の adapter は `f"hftbacktest.{name}"` を自分で組み(`opponents/hftbacktest_adapter.py` 111-118 行 `_row_carrier`)、`C.carrier(hbt) + ".wait_next_feed"` と文字列を足した(128 行)。mihircoding の adapter は、戦略が受け取った物ではなく、adapter が自分で書いた `lambda: None` の class を carrier にした(`opponents/mihircoding_lob_adapter.py` 66 行 `ACTION = C.carrier(lambda: None)`)。runner には、その文字列が物から作られたのかを確かめる所が無かった。
3. **「対象が作った」を示す手段が、型の名前しか無かった**。共有の型の物が対象の物であることは、型の名前では示せない(br6-1-1 の指摘どおり)。示せるのは、**物がどこから来たか**(対象のコードが戦略の呼び出しに引数として渡したか、戦略が対象の関数を呼んで返ってきたか)だけで、その記録が出所の形に無かった。
4. **試験が除外の一覧の例しか試さなかった**。第 r6-1 回に足した試験(`test_provenance_check_refuses_an_adapter_made_carrier_and_a_shared_one` ほか)は、場面集の名前(`basana_adapter.Generic`)が拒まれ、それ以外の名前(`somepkg.events.FundingEvent`)が通ることだけを確かめた。共有の型・札・手で書いた文字列を渡す試験が無く、穴が機械で見えなかった。
5. **前の周の記録の書き手(場面係)が、機構の結果ではなく自分の読みで一括りにした**。`ROOTCAUSE_r6-1.md` 117 行は `builtins.dict` を「(ThePredictiveDev の run_backtest が戦略に渡す辞書)」と注記して「carriers はどれも対象の物」と書いた。道具のコードを読めば渡しているのは対象だと分かるが、その読みは runner が確かめたものではなく、同じ `builtins.dict` を adapter が作っても runner は同じに通す。書いた文は機構で裏付けられていなかった。

同じ根から出た、指摘の外の欠陥(場面集の全体を探した結果。直す前に見つけたもの):

| # | どこ | 何が起きているか | 見つけた方法 |
|---|---|---|---|
| A | 37 ThePredictiveDev(carrier `builtins.dict`) | p2-event-time-exact・p2-one-ns-apart・p5-same-stream-order が正解と一致(br6-1-1 の例)。道具が作った辞書だと読めるが、runner は確かめていない | `survey_results/*.tsv` の `provenance_1` の carriers・reader・reads の全部を、対象ごと・場面ごとに一覧にした(下のコマンド) |
| B | 98 mihircoding(carrier `builtins.function`) | carrier は adapter の `lambda: None` の class。事象は adapter が書いた閉包(`lambda e=e: on_event(e, bus.now_us)`)が運び、値(`e["price"]`)は場面の辞書から読む。p5-same-stream-order が正解と一致、p1-merge-by-time・p1-one-call-per-event・p2-event-time-exact・p2-one-ns-apart が不一致。場面集の共通の決まり「型の印を付けた辞書や関数で事象を運ばない」そのもの | 同上。adapter の 60-66 行・185-190 行を読んだ |
| C | 23 hftbacktest(carrier `hftbacktest.TRADE_EVENT`・`numba…HashMapMarketDepthBacktest.wait_next_feed`) | 物からではなく adapter が組んだ文字列。p2-event-time-exact・p2-one-ns-apart・p3-trade が正解と一致 | 同上。adapter の 107-128 行 |
| D | 当方の現状(carrier `pandas.DataFrame`) | 共有の型。しかも carrier は走らせたあとに `rec.seen` から作っていて、受け取った時点のものではない(`adapters/current_impl.py` 110・137・154・241 行) | 同上 |
| E | 75 Freqtrade・16 Luczinsritter(carrier `pandas.DataFrame`) | 共有の型。Freqtrade は戦略が中で読んだ表、Luczinsritter は戦略の物の属性 `s.data` で、しかも**戦略を呼ぶのは道具ではなく adapter の書いた loop**(`opponents/luczinsritter_adapter.py` 81-92 行 `run`、道具の説明「The engine does not call the strategy」)。「事象ごとに 1 回呼ばれるか」を adapter の loop で測っていた | 同上。adapter を読んだ |
| F | 12 pybotters(carrier `pybotters.models.bitflyer.Executions`) | 戦略が受け取った変化の物(`watch()` が返す `ch`)ではなく、その変化が来た倉庫(store)の class を carrier にしている(`opponents/pybotters_adapter.py` 92 行) | 同上 |
| G | 翻訳した道具の carrier(61 barter-rs・69 gobacktest・70 pineforge・33 SarthakDalmia1・101/102/104 の C++ 板) | `made_by_scene_set` は `rust:`・`go:` などで始まる名前に「battery・driver・adapter・scene の語が無いか」の除外だけを当てた。どんな文字列でも語が無ければ通る | `run_battery.py` 223-227 行を読んだ |
| H | p2-iso-utc・p2-iso-offset の reader | 除外の一覧(`FOREIGN_READER_TOPS`)。一覧に無い共有の部品は通る(上の probe の `pytz.parse`) | 同上 |
| I | p4-visible-at-step の reads | 読み出しの手段(`means`)は adapter が書いた文だけで、読み出しが対象のコードを通ったかを何も見ていない。戦略が自分で貯めた列を返す関数を `reads.read("tool.history()", …)` に渡しても通る(第 r6-1 回の C は、detail を人が読んで見つけた。機械は見ていない) | 第 r6-1 回の試験 `test_provenance_check_refuses_a_foreign_reader_and_a_strategy_kept_list` の `good` の例が、出所を何も持たない reads で通っている |
| J | p4-future-read-attempt の試し | 「止まった」を正解の側に数えるのに、例外がどこで起きたかを見ていない。adapter が自分の `raise` で止めた試し、場面集の側の列(戦略が貯めた list など)への添字の失敗も「止まった」に数えられる | runner の `_grade_future_reads`・`_attempts_problem`(136-142 行・255-281 行)を読んだ |

一覧を作ったコマンド(全 36 対象の記録、`tests/bt/battery/item_0` で実行):

```
python3 - <<'EOF'
import csv,json,glob,collections
csv.field_size_limit(10**9)
agg=collections.defaultdict(set)
for f in sorted(glob.glob('survey_results/*.tsv')):
    for r in csv.DictReader(open(f,encoding='utf-8'),delimiter='\t'):
        p=json.loads(r['provenance_1'])
        if not isinstance(p,dict): continue
        ... (carriers を平らにし、reader・reads の means と合わせて (対象, 出所) → {(場面, 正しさ)} に集めた)
EOF
```

出力のうち共有の型・手で組んだ名前のもの(逐語): `opp_predictivedev_tradesim.tsv | builtins.dict | [('p1-one-call-per-event', '不一致'), ('p2-event-time-exact', '正解と一致'), ('p2-one-ns-apart', '正解と一致'), ('p3-bar', '不一致'), ('p5-same-stream-order', '正解と一致')]` / `opp_mihircoding_lob.tsv | builtins.function | [('p1-merge-by-time', '不一致'), ('p1-one-call-per-event', '不一致'), ('p2-event-time-exact', '不一致'), ('p2-one-ns-apart', '不一致'), ('p5-same-stream-order', '正解と一致')]` / `opp_hftbacktest.tsv | hftbacktest.TRADE_EVENT | [('p1-typed-events', '不一致'), ('p2-event-time-exact', '正解と一致'), ('p2-one-ns-apart', '正解と一致'), ('p3-mixed-one-run', '不一致'), ('p3-trade', '正解と一致'), ('p5-hand-over-order', '不一致')]` / `opp_hftbacktest.tsv | numba.experimental.jitclass.boxing.HashMapMarketDepthBacktest.wait_next_feed | …(8 場面、全部 不一致)` / `opp_freqtrade.tsv | pandas.DataFrame | [('p1-one-call-per-event', '不一致')]` / `opp_luczinsritter.tsv | pandas.core.frame.DataFrame | [('p1-one-call-per-event', '不一致'), ('p5-same-stream-order', '不一致')]`。当方の現状は `pandas.DataFrame`(記録 `scratchpad/bt/item0_r6-1_scenekeeper_current_impl.tsv`)。

## br6-1-1 [止める] runner の出所の検めが `builtins` を当てず、adapter が組める `dict`・関数が通る

- **なぜ起きたか**: 上の共通の根本原因 1・3・4・5。carrier の検めは除外の一覧(場面集の名前)だけで、共有の型を「対象の物」とも「場面集の物」とも決められないのに、決められないものを「対象の物」の側に倒していた。reader の検めは `builtins` を除外に入れていたので、同じファイルの 2 つの検めで扱いが食い違っていた(指摘のとおり)。食い違いは偶然ではなく、どちらも「一覧に載せた名前を拒む」形で、一覧に何を載せるかを検めごとに書き手が決めていたから。
- **どの作りを変えるか**:
  1. **除外をやめ、正に帰属させる**。runner は対象ごとに、その対象の配布物のモジュール(Python)か翻訳した道具の型の名前の頭(Rust・Go・C・C++)を表に持つ(`run_battery.py` の `TARGET_DISTS`。adapter には書かせない)。Python のモジュールは、その対象の venv の中で import の探索(`importlib.util.find_spec`)で置き場所のディレクトリに直す。**出所が「対象の物」と言えるのは、物の出所のファイルがその置き場所の中にあるときだけ**。場面集のディレクトリと、調査結果の側の対象ではこのリポジトリの中を置き場所にすることは runner が拒む。`BATTERY_TOPS`・`FOREIGN_READER_TOPS` の除外の一覧は消す。
  2. **物から作った記録だけを受ける**。carrier・reader・reads・試しの出所は、`adapters/common.py` が物(受け取った物・呼んだ関数・読んだ物)から作る記録にする。記録は common が作った印(`common.Record` / `common.Made`)を持ち、runner は印の無いもの(adapter が手で書いた文字列・辞書)を採点しない。翻訳した道具は `common.compiled(名前)` で作り、名前の頭を表と突き合わせる。
  3. **共有の型の物は、来た道で示させる**。記録には、物の型を定義したファイルに加えて、(α)その物を**戦略の呼び出しに引数として渡した呼び出し元**(戦略の関数を呼んだ、場面集の外のフレームのファイルの並び)、(β)戦略が `common.read(対象の関数, …)` で読んだとき、**その物を返した対象の関数**の定義のファイル、(γ)関数の物はそのコードのファイル、を common が書く。runner の決まり: 型を定義したファイルが対象の置き場所にあれば対象の型(第 r6-1 回の線。Basana の配布物の class を配布物の入口に渡したもの)。場面集の置き場所なら拒む。**それ以外(共有の型)は、α か β のファイルが対象の置き場所にあり、かつその物が場面集の側のフレームが持つ物(adapter が渡した入力の列など)でないときだけ**対象の物とする。後半は「adapter が作った辞書を対象がそのまま転送した」を止めるための検め(common が、戦略の呼び出しより外側にある場面集の側のフレームの局所変数を深さ 4 まで辿り、同じ物が無いかを見る)。
  4. **試験を、除外の例ではなく穴の形ごとに書く**: adapter が作った `dict`・adapter が書いた関数・場面集の側の札・手で書いた文字列・共有の部品の reader・戦略が貯めた列の reads・adapter の `raise` で止まった試しを、runner が全部拒むこと。対象のコードが渡した `dict`・対象の関数が返した表は通ること。
  5. **記録の文は機構の結果で書く**: 検討表と ROOTCAUSE の「対象の物」の文は、runner の検めを通った記録(`provenance_1` の記録の判定)だけを引く。

## br6-1-2 [直す] `carrier_tag` の札の側のモジュールを `_carrier_problem` が見ない

- **なぜ起きたか**: 共通の根本原因 2。carrier を文字列にし、その最初のドットまでしか読まなかった。札(enum の値・定数)は「その物の型を対象がどう印で持つか」を示す部分で、札が場面集の側の物なら型を決めているのは場面集の側なのに、文字列の後ろにあったので読まれなかった。今の 1 か所(aat の `EventType`)で問題が出ていないのは、たまたま adapter が対象の enum を渡したからで、機構が止めたからではない。
- **どの作りを変えるか**: 札も物として記録する(`common.carrier_tag(物, 札)` は、物の記録と、札の型を定義したファイル・札の名前を別の欄に持つ記録を作る)。札が整数などの共有の型の定数のときは、`common.carrier_const(物, 対象のモジュール, 名前)` で**その定数を持つ対象のモジュール**を記録し、common がそのモジュールのその名前の値と札が同じであることを確かめる。runner は物と札の**両方**を上の決まり 1・3 で検め、どちらかが対象の置き場所に帰属しなければ採点しない。numpy の記録型の行は、`common.carrier_record(行, 対象のモジュール, 名前)` で**行の dtype が対象のモジュールの定義した dtype と同じ**ことを記録する(hftbacktest の `event_dtype`)。「1 つの型に 2 つの kind」の検めの鍵は、物の型と札の両方にする。

## 同じ根の欠陥の直し方(A〜J)

- A(ThePredictiveDev): 変える作りの 3 の α(道具の `run_backtest` が `t.on_market_data(market_data)` で辞書を渡す)で示す。示せなければ採点しない。
- B(mihircoding): 道具は事象の物を戦略に渡さない(戦略の呼び出しは adapter が書いた閉包)。事象を運ぶ物が道具に無いので、事象の列を返す場面は「対応なし」にし、試したことを detail に書く(場面集の共通の決まりの最後の文「対象がその型・手段を持たないときは『対応なし』」)。
- C(hftbacktest): 手で組んだ文字列をやめ、行は `carrier_record`(dtype)+ `carrier_const`(型の番号の定数)で、足の無い feed は `wait_next_feed` の戻り値を `common.read` で読んだ物として記録する。numba の jitclass は、共通の部品が `_numba_type_.class_type.class_def`(元の class)の定義のファイルに帰属させる。
- D(当方の現状): 受け取った時点で `common.carrier` を呼ぶ(α = 当方の `engine.py` が `strategy.on_candles(...)` で渡した物)。
- E: Freqtrade は戦略が受け取った物(`bot_loop_start(current_time)` の引数、α)と、中で読んだ表(`common.read(dp.get_analyzed_dataframe, …)`、β)で記録する。Luczinsritter は道具が戦略を呼ばない(利用者が loop を書く)ので、「戦略の呼び出し」を測る場面は「対応なし」にし、道具の表の観察は detail に残す。
- F(pybotters): 受け取った変化の物(`ch`)を受け取った時点で記録する。
- G(翻訳した道具): `common.compiled(名前)` で作り、名前の頭を `TARGET_DISTS` の対象の頭と突き合わせる(正の帰属)。
- H(reader): 文字列の reader は runner が import で定義のファイルに直し、対象の置き場所にあるかを見る。
- I(reads): `common.Reads.read` が、読み出しの間に**走ったコードのファイル**を記録する(`sys.setprofile`)。読み出しの手段が対象の物(戦略が受け取った物・読んだ物)なら `of=` でその物の記録を付ける。runner は、走ったコードか `of` のどちらかが対象の置き場所に帰属しなければ採点しない(戦略が貯めた列だけを返す読み出しは、対象のコードが 1 行も走らないので拒まれる)。
- J(試し): 試しにも走ったコードのファイルと、手段の物(`via=`)の記録を付ける。名指しの試しは、どちらかが対象の置き場所に帰属しなければ採点しない。例外は、場面集の側のファイルの `raise` の命令で起きたものなら、止まったに数えない(runner が拒む)。

**変えないもの**: 場面の入力・期待・正解の出し方、観点、判定の順(場面集の規則 5)。変えるのは、採点の前の出所の検めと、それに合わせた adapter だけ。新実装の adapter(資料係の持ち物)は `common.carrier`・`common.qualname`・`common.Reads`・`common.try_*_namings` の呼び方を変えずに新しい検めを通る作りにする(呼び口の形を変えない)。
