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

## 結果(直したあとに書いた)

合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」。この直しで、出所の検めは「対象の配布物の中にあると物から示せたものだけを対象の物に数える」形になった。調査結果の側も新実装も当方の現状も同じ検めを通る。

### 作りの変更(どこを変えたか)

- `run_battery.py`: 対象ごとの配布物の表 `TARGET_DISTS`(219 行〜)と、それを対象の環境の import の探索で置き場所に直す `Roots`・`roots_of`(257・277 行。場面集の中・調査結果の側ではこのリポジトリの中を置き場所にすると止まる)。出所の判定は `origin_problem` 1 か所(313 行): common.py が作った記録でなければ拒む → 型を定義したファイル(dtype・札も)が置き場所にあれば対象の型 → 場面集の側の型なら拒む → 共有の型は `passed_by`(対象のコードが戦略の呼び出しに渡した)・`returned_by`(対象の関数が返した)・`code_file`(対象のコードの関数)のどれかが置き場所にあり、かつ `held_by`(場面集の側が持つ・対象に渡した物と同じ)でないときだけ → 札は札だけで置き場所を見る。carrier(352 行)・reader(451 行)・reads(429 行)・試し(387 行、`_touched_ok` 376 行)は全部この判定を通す。除外の一覧 `BATTERY_TOPS`・`FOREIGN_READER_TOPS` と `made_by_scene_set` は消した(`grep -n "BATTERY_TOPS\|FOREIGN_READER_TOPS\|made_by_scene_set" run_battery.py` → 0 件)。試しの出所の欄は採点と「2 回の実行で同じ」の比べから外して出所の列に移す(`_provenance_out_of_output`、514 行)。
- `adapters/common.py`: 記録は物から作り、作った物を登録する(`Record`・`Made`・`made_here`)。`carrier`(571 行)・`carrier_tag`(579 行、札の型のファイル)・`carrier_const`(590 行、札が整数の定数のときは定数を持つ対象のモジュールと値を確かめる)・`carrier_record`(602 行、numpy の行の dtype)・`compiled`(620 行)・`qualname`(633 行、定義のファイル付き)。受け取った時点のスタックから `passed_by`・`called_by`・`in_args`・`held_by` を作る `_stack_facts`(478 行。同じ物の 2 回目以降の記録は最初の時点の事実を使う = 戦略が受け取ったあとに自分で持った物を「場面集の側が持つ」と取り違えない)。読み出しと試しの間に走ったコードのファイルを `sys.setprofile` で集める `_profiled`(644 行。numba の jitclass・pybind11 の C の方法も、対象が書いた class の定義のファイルに直す: `type_file` 362 行・`code_file` 379 行)。対象の関数を通した読み出し `read`(672 行)。例外が場面集の側の `raise` 文で起きたかを見る `_raise_site`(687 行)。adapter が道具に読ませるために書いたコードのファイルを場面集の側と宣言する `scene_set_file`(331 行、Freqtrade の戦略のファイル)。
- adapter(直した根 A〜J): 当方の現状は受け取った時点で記録(`adapters/current_impl.py` の `_Rec.on_candles`)、読み出しと試しは `of=`・`via=` = エンジンが渡した candles。98 mihircoding は事象の列を返す 5 場面を「対応なし」(`NO_CARRIER`)。23 hftbacktest は `_row_carrier` を `carrier_record(行, hftbacktest.types, "event_dtype", const=(…, "TRADE_EVENT", …))` に、足の無い feed は `common.read(hbt.wait_next_feed, …)` の戻り値に。75 Freqtrade は `bot_loop_start` の引数 `current_time` と `common.read(dp.get_analyzed_dataframe, …)` の表、戦略のファイルを `C.scene_set_file`。16 Luczinsritter は道具が戦略を呼ばないので、呼び出しで測る 5 場面(p1-one-call-per-event・p2-event-time-exact・p2-one-ns-apart・p3-bar・p5-same-stream-order)を「対応なし」(`NO_CALL`、道具の表の観察は detail に)、P0-4 の 2 場面は道具の `get_date_price` を通す読み出しだけにした。12 pybotters は受け取った変化の物(`ch`)を受け取った時点で。65 aat は受け取った時点で `carrier_tag`。62 qf-lib は `common.read(data_provider.get_price, …)`(`_bar_read` と p3 の `_type` の 2 か所)。翻訳した道具(61・69・70・33)は `common.compiled`(試しは `Attempts.compiled` と `via=common.compiled(…)`)。名指しの試しの `no_means` 9 か所に `via=`(1 Basana 2・34 QuantCore 2・37 ThePredictiveDev 2・23 hftbacktest 1・65 aat 2。`grep -c 'shape="no_means"' opponents/*.py`。16 Luczinsritter の 1 か所は新しく足した時刻の試し)。20 VnPy の試しは `via=s.cta_engine`、18 zipline-reloaded の読み出しは `common.Reads` の中で道具を呼ぶ形に、6 Ziplime は `of=data`。
- 場面の定義(`gen_definitions.py` → `DEFINITIONS.md` の「出所の検め」)と adapter の約束事(`adapters/protocol.py`)に、正の帰属の決まりを書いた。場面の入力・期待・正解・観点は変えていない(`git diff --stat -- tests/bt/battery/item_0/scenes.py` → 変更なし)。

### br6-1-1 の根拠

- 穴の再現(直したあと): 同じ probe(`…/r6-2/item0_r6-2_scenekeeper_hole_probe.py`)の出力(`…hole_probe.after.txt`)は 5 つとも `error`。逐語: `dict      ('error', 'carrier が common.py で物から作った記録でない(手で書いた値): builtins.dict')` ほか。
- 物から作った記録でも、共有の型は来た道で決まる: 試験 `test_shared_type_carriers_are_placed_by_how_they_reached_the_strategy`(`test_battery_item0.py` 587 行)。場面集の外の一時ディレクトリに書いた偽の道具で、(1) 道具が作って渡した `dict` → 通る、(2) adapter の `dict` を道具が転送しただけ → `場面集の側が持つ物` で拒む、(3) 戦略の呼び出しの中で場面集の側が作った `dict` → `共有の型` で拒む、(4) adapter の `lambda` → 拒む、(5) 道具の関数 → 通る。
- 記録(全 36 対象を走らせ直した `survey_results/*.tsv`): 出所の検めの拒否は 0 件(`test_no_recorded_result_was_refused_by_the_provenance_check`)。37 ThePredictiveDev の `builtins.dict` は `passed_by` = 道具の `trading_simulator/backtest/runner.py`(`t.on_market_data(market_data)` で渡した辞書。`market_data = {"symbol": …}` はその関数の中で作られる)で、p2-event-time-exact・p2-one-ns-apart・p5-same-stream-order は正解と一致のまま(正の検めを通った)。98 mihircoding の `builtins.function`(adapter の `lambda: None`)は消え、事象の列の 5 場面は対応なし。
- 直す前と直したあとの記録の差(`python3 …/r6-2/item0_r6-2_scenekeeper_diff.py`、正しさか再現が変わったセルの全部): `opp_luczinsritter` p1-one-call-per-event・p2-event-time-exact・p2-one-ns-apart・p3-bar・p5-same-stream-order が 不一致 → 対応なし / `opp_mihircoding_lob` p1-merge-by-time・p1-one-call-per-event・p2-event-time-exact・p2-one-ns-apart が 不一致 → 対応なし、p5-same-stream-order が 正解と一致 → 対応なし / `changed cells 10`。再現の欄の変化は 0。**調査結果の側の最良の行は変わらない**(p5-same-stream-order は 10 候補が正解と一致、p1・p2 の 4 場面も他の候補が正解と一致のまま。数え: 下の試験の節のコマンド)。
- 当方の現状と新実装も同じ検めを通る: `--target current_impl` → `{'対応なし': 23, '正解と一致': 8, '不一致': 1}; 2 回で違う=0`(直す前と同じ。carriers は `passed_by` = `src/bot/backtest/engine.py`)、`--target new_impl` → `{'正解と一致': 32}; 2 回で違う=0`、`--target mutant` → `{'正解と一致': 31, '不一致': 1}`。

### br6-1-2 の根拠

- 札は物と別に検める: 試験 `test_a_tag_is_checked_as_well_as_the_object`(627 行)。道具の enum の札 → 通る、場面集の側の enum の札(`MyKind.TRADE`)→ `札` で拒む、場面集の側のモジュールの定数 → 拒む、名乗った定数の値が違えば `carrier_const` が `ValueError`。
- 今の札付きの carrier は 65 aat(`aat.config.enums.EventType`、札の型のファイルは aat の配布物)と 23 hftbacktest(`hftbacktest.types.TRADE_EVENT` と `event_dtype`)。記録の `provenance_1` の `tag.type_file`・`dtype.type_file` が道具の venv の `site-packages/aat/…`・`site-packages/hftbacktest/types.py`。「1 つの型に 2 つの kind」の鍵は物の型と札の両方(`run_battery._key`、343 行)。

### 同じ根の直りの確かめ

- 手で組んだ carrier の文字列が残っていない: `test_no_adapter_composes_a_carrier_string`(754 行。`C.carrier(...) +`・`carrier(lambda` が全 adapter に 0 件)。
- 対象ごとの置き場所は runner の表だけ: `test_every_target_has_its_distribution_in_the_runner`(722 行)、場面集を置き場所にすると止まる `test_the_scene_set_is_never_a_place_of_a_target`(731 行)。
- 道具に読ませるために adapter が書いたコードのファイル: `test_generated_code_files_are_declared_as_the_scene_sets`(743 行)。
- reader・reads・試し: `test_readers_reads_and_attempts_must_run_the_targets_code`(650 行。標準の `datetime.fromisoformat`・手で書いた名前・場面集の関数の reader → 拒む / 戦略が貯めた列の読み出し → `1 行も走らず` で拒む / 手で書いた reads → 拒む / adapter の `raise` で止まった試し → `raise 文` で拒む / 道具の関数を通した読み出しと試し → 通る)、名指しの網羅と記録の出所 `test_p4_attempts_must_cover_the_fixed_namings_and_only_compiled_means_may_skip_one`(695 行)。
- 検討表の含む側の文が引く場面が今の記録で正解と一致: `test_every_scene_a_containment_cites_as_correct_is_correct_in_the_records` は通る。検討表の P0-5 の冒頭の数を今の記録に合わせた(「11 候補」→「10 候補」、理由を併記)。Basana の含む側の試し(`survey_results/attempts/1.log` の「probe r6-1」)は新しい検めで走らせ直した(同じ log の「probe r6-2」、コード `survey_results/attempts/1_probe_r6-2.py`。出力の逐語: `P1-MERGE … EQUAL True`、`P5 hand_over ['trades', 'bars'] … carrier_check None … FOLLOWS True`、`P5 hand_over ['bars', 'trades'] … carrier_check None … FOLLOWS True`、`P5 distinct_orders_over_hand_overs 1`)。r6-1 の probe のコードは第 r6-1 回の記録として残し、変えていない(新しい runner の呼び口とは合わない)。

### この検めが見ないもの(限界。全部書く)

1. **対象の class の物は、型だけで対象の物に数える**(第 r6-1 回の線のまま)。〔第 r6-3 回の注: 監査役の br6-2-1 で、この限界は閉じた(対象の class にも届いた道の検めを当てた)。下の「3 対象だけが…持たない」の数えは `in_args`・`called_by` を含めた誤りで、実際には 55・53・122・121 も届けた事実を持たなかった。`ROOTCAUSE_r6-3.md` を見よ。この段落は第 r6-2 回の記録として残す〕adapter が戦略の呼び出しの中で対象の class の物を自分で作って記録しても、機械は止めない。共有の型に当てた「来た道」を対象の class にも当てると、道具が母語のコード(pybind11・C++)から戦略を呼ぶ 34 QuantCore では呼び出し元のフレームが Python に見えず、区別できない。記録には `called_by`・`in_args`・`passed_by`・`returned_by` を残した(全記録を数えた結果、対象の class の carrier でこのどれも無いのは 34 QuantCore(母語のコードからの呼び出し)・12 pybotters(`watch()` の非同期の反復が返す物)・121 QSTrader(戦略が読む data handler)の 3 対象。人が読む材料)。
2. `held_by` が見るのは、場面集の側のフレームの局所変数と、場面集の側が呼んだ対象の関数の引数から、深さ 4 までの列・辞書・場面集の側の物の属性。これより深く隠した物(対象の物の属性の中など)を対象が転送したときは見つけない。
3. 読み出しと試しの「対象のコードが走った」は、走ったことしか見ない。対象の関数を 1 回呼んだうえで自分の列を返す書き方は止めない(adapter の書き方の問題で、批評家と監査役が読む)。非同期の試し(`run_async`)は、待つ間に同じスレッドで走った別の処理のコードも数える。
4. 翻訳した道具の名前は driver(場面集の側が書いた翻訳のコード)が型から名付けたもので、Python の側から物を見られない。確かめるのは名前の頭が対象の名前の空間にあることだけ(driver のコードは各道具の導入の記録に残してある)。
5. 置き場所の表 `TARGET_DISTS` は場面集の側(場面係)が書く。表そのものの正しさ(道具の配布物のモジュールの名前)は、批評家と監査役が導入の記録と突き合わせて確かめる。

## 提出前の吟味(委任文 §3「提出前の吟味」(1)〜(5))

1. 読み直したもの: 固定した要件(`REQUIREMENTS.md` §2 の P0-1〜P0-7、特に P0-3「型が無ければ『対応なし』」)、委任文の「場面集の規則」1〜9・「調査結果の側の選び方」・「動かせない候補の検討と再現」・「根本的解決」、これまでの指摘(第 5 周の i0-r5-01〜07、br6-1-1・br6-1-2)と前の周の根本原因(`ROOTCAUSE.md`・`ROOTCAUSE_r4-1.md`・`ROOTCAUSE_r5-1.md`・`ROOTCAUSE_r6-1.md`)。
2. 指摘ごとの根拠は上の「br6-1-1 の根拠」「br6-1-2 の根拠」に、ファイルと行・コマンドと出力で書いた。
3. 同じ根の全箇所: 指摘の 2 か所(carrier の先頭のモジュール・札)だけでなく、同じ「除外の一覧・手で書いた名前で決める」形の reader(H)・reads(I)・試し(J)と、adapter の 10 の根(A〜G)を全部同じ判定 `origin_problem` に通した。見つけ方は直す前の表の「見つけた方法」の列。直している途中で見つけて直したもの: (i) Freqtrade が道具に読ませる戦略のファイルが場面集の外にあり、場面集の側のコードと見分けられなかった(`scene_set_file`)、(ii) 対象に渡した引数の中の物の転送(偽の道具の試験が最初に落ちて見つけた)、(iii) 標準の `<frozen importlib…>` のフレームを場面集の側と数えていた、(iv) numba の jitclass と pybind11 の方法が置き場所に直らなかった、(v) 試しの出所の欄が「2 回の実行で同じ」の比べに入っていた。
4. 試験: 下の「試験の結果」。
5. 非常に厳しい批評家が止めそうなものと扱い:
   - 「対象の class の物を adapter が作っても通る」: 上の限界 1。第 r6-1 回の線(対象の配布物の class を対象の公開の入口に渡した物は対象の型)を変えていない。変えると母語の呼び出し元の道具が区別できない。記録に来た道の事実を残した。
   - 「Luczinsritter・mihircoding が 不一致 → 対応なし に上がった」: 場面集の規則 5 の順で、この 2 つの候補の行は良くなった。どちらも道具が事象を戦略に届けない(Luczinsritter は戦略を呼ばない、mihircoding は adapter の閉包を呼ぶ)ことを、道具を実際に動かして detail に書いた(`_table_seen`・`NO_CARRIER` の試したこと)。場面集の共通の決まり「対象がその型・手段を持たないときは『対応なし』」のとおり。調査結果の側の最良の行は変わらない。
   - 「P0-4 の Luczinsritter は呼び出しが無いのに採点している」: P0-4 は先の値を読もうとして止まるかを見る場面で、道具の例の回し方の回に道具の `get_date_price` で読んだ結果を採点した(道具の関数が走ったことを記録)。先の値は読めて止まらない(不一致、直す前と同じ)。
   - 「`TARGET_DISTS` を場面係が書く」: 限界 5。
   - [判断] **新実装の adapter(資料係の持ち物)は変えていない**。呼び口(`C.carrier`・`C.qualname`・`C.Reads().read`・`C.try_*_namings`・`att.run`)の形を変えずに新しい検めを通るように common.py を作った。新実装の 32 場面は正解と一致のまま。

## 試験の結果

- 場面係の試験: `PYTHONPATH=src python -m pytest tests/bt/battery/item_0` → `43 passed`(第 r6-1 回の 37 件のうち、除外の一覧の例だけを試していた 2 件と名指しの網羅の 1 件を書き直し、第 r6-2 回の 9 件を足した: 587〜754 行の試験)。
- 批評家と作業者の試験: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 tests/bt/item_0` → `6 failed, 738 passed, 2 skipped`。落ちた 6 件は第 r6-1 回と同じ `test_i0r5_battery_opponent_grading.py::test_basana_is_not_credited_with_an_event_type_its_adapter_wrote` の 6 つ(60 行の `assert "class Generic(bs.Event)" in adapter` が、指摘どおり消した adapter の class の存在を前提にしている。試験自身の誤りの理由は `ROOTCAUSE_r6-1.md` の i0-r5-02 の結果の節。場面集の規則 8 により試験は変えていない)。
- 全試験(`setsid nohup … python -m pytest`、記録 `scratchpad/bt/pytest_item0_r6-2_scenekeeper.log`、2026-09-24T08:25:03Z 開始・08:33:33Z に終わりを確かめた): `6 failed, 3675 passed, 6 skipped, 1 warning in 493.09s (0:08:13)`。落ちたのは上の 6 件だけ(`grep ^FAILED` の全行)。
- mutant: `PYTHONPATH=src python3 mutant.py --check` → `changed scenes: ['p4-received-time']` / `OK`。
- 定義: `python3 gen_definitions.py` → `wrote … DEFINITIONS.md (32 scenes)`(`test_definitions_in_sync_with_scenes` が通る)。
- 検討表: `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md --write` → `OK 誤り 0 件`。
- 全 36 対象の走らせ直し: `sh …/r6-2/item0_r6-2_scenekeeper_runall.sh`(対象ごとに自分の venv の python。出力 `…/r6-2/item0_r6-2_scenekeeper_runall5.out`、36 行とも `32 scenes`)。出所の検めの拒否 0 件、「2 回で違う」は 37 ThePredictiveDev の p7-latency-model-swap 1 件(道具が約定の時刻に `pd.Timestamp.now()` を入れる。直す前の記録と同じ)。記録は `survey_results/opp_*.tsv` に置き換えた。
