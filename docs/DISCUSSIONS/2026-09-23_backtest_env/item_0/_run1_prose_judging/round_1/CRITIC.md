# 項目 0(核)批評家 — 第 1 周

指紋: `docs/DATA/delegations/20260923_backtest_env_prompt.md@a723df99ad38`。固定した要件は
`docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`。前の周の指摘は無い(このセッションが項目 0 の
第 1 周の批評家として新しく起こされた者であるため)。自分で試験を書いて壊しにいった。壊れた試験は
`tests/bt/critic/item_0/` に残す。作業者が直すこと。

## 検査対象

`src/bot/bt/core/{time,events,clock,api,strategy,engine,interfaces}.py` と、作業者自身の試験
`src/bot/bt/core/tests/`(68 件、`setsid nohup ... pytest_item0_r1_worker.log` で実行され「68 passed」)。

## 実行した検査コマンドと結果(まとめ)

```
$ PYTHONPATH=src python -m pytest src/bot/bt/core/tests/ tests/bt/critic/item_0/
5 failed, 68 passed in 0.61s
```

作業者自身の 68 件はすべて通る。批評家が新たに足した 4 本(5 ケース)はすべて壊れる。以下、指摘ごとに詳細。

---

## i0-r1-01 [止める] `EngineResult.order_requests` に記録される `client_order_id` が、戦略に返した ID と一致しない

**根拠(実行したコマンドと出力)**:

```
$ PYTHONPATH=src python3 -c "
from bot.bt.core.engine import CoreEngine
from bot.bt.core.api import OrderRequest
from bot.bt.core.events import ClockEvent
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import to_nanos
T0 = to_nanos(1_700_000_000, 's')
class S(Strategy):
    def __init__(self): self.oid = None
    def on_event(self, event, ctx):
        if self.oid is None:
            self.oid = ctx.place_order(OrderRequest(side='buy', order_type='market', size=1.0))
events = [ClockEvent(received_time_ns=T0, seq=0)]
s = S()
result = CoreEngine(strategy=s, events=events).run()
print('returned id to strategy:', s.oid)
print('stored order_requests[0].client_order_id:', repr(result.order_requests[0].client_order_id))
"
returned id to strategy: core-1
stored order_requests[0].client_order_id: ''
```

試験: `tests/bt/critic/item_0/test_order_request_id_consistency.py`(壊れる。実行 = 上記 pytest 出力の
`OrderRequestRecordCarriesAssignedIdTest`)。

**何が起きているか(ファイル:行)**: `src/bot/bt/core/engine.py:68-72` の `_place_order` は、戦略が
`client_order_id` を空で渡したとき `f"core-{n}"` を生成して**戦略へは返す**が、`self._order_requests`
(`EngineResult.order_requests` の中身、`engine.py:34`)へは**元の(ID を積んでいない)`OrderRequest` を
そのまま追加する**(`engine.py:71` `self._order_requests.append(request)`)。`OrderRequest` は
frozen dataclass(`api.py:35-41`)なので、生成した ID を積み直すには `dataclasses.replace` が要るが、
それが行われていない。

**なぜ止めるか**: `CoreEngine` の docstring(`engine.py:1-9`)は `EngineResult` を「他項目が差し込む口」の
一部として位置づけ、`api.py:83-85` の `place_order` の docstring も「エンジンが割り当てた
client_order_id を返す」ことを契約にしている。しかし `EngineResult.order_requests` という、
項目 8(再現性・実行記録)・項目 2(注文の永続化)・項目 13(統合報告)が今後 `client_order_id` で
突き合わせに使うはずの記録そのものが、戦略へ返した ID と食い違う。**空文字列の ID を持つ発注記録**が
残るため、後続項目が「この発注はどの ID に対する約定/取消か」を `EngineResult.order_requests` から
逆引きできない。これは項目 0 が「他項目が差し込む口」として約束した記録の整合性そのものが壊れている
ということであり、項目 0 の完了条件(戦略 API・発注 API が決定的で他項目の土台になること)を満たさない。
作業者自身の試験(`test_engine_integration.py`)は `result.order_requests[0].client_order_id` を一度も
検証しておらず、この不整合を検出できていない。

**patchwork**: false(第 1 周。前の周の指摘への場当たり対応ではなく、初回実装そのものの欠陥)。

---

## i0-r1-02 [直す] `StrategyContext.visible_events(n=0)` が「0 件」ではなく「全件」を返す

**根拠(実行したコマンドと出力)**:

```
$ PYTHONPATH=src python3 -c "
from bot.bt.core.api import StrategyContext
from bot.bt.core.events import ClockEvent
from bot.bt.core.time import to_nanos
T0 = to_nanos(1_700_000_000, 's')
evs = tuple(ClockEvent(received_time_ns=T0, seq=i) for i in range(5))
ctx = StrategyContext(visible_events=evs, current=evs[-1], place_order_cb=lambda r: 'x', cancel_order_cb=lambda r: None)
print('n=0 ->', len(ctx.visible_events(n=0)))
"
n=0 -> 5
```

試験: `tests/bt/critic/item_0/test_visible_events_n_zero.py`(壊れる)。

**何が起きているか(ファイル:行)**: `src/bot/bt/core/api.py:79-80` は `n` 指定時に
`events = events[-n:]` を使う。Python のスライスでは `-0 == 0` なので、`n=0` は
`events[0:]`(全件)に退化する。docstring(`api.py:73-75`)は「limited to the last `n`」と
書いており、`n=0` は「0 件に絞る」以外に読みようがないが、実装は逆の「絞りをかけない」になっている。

**なぜ直すか(止めないか)**: ルックアヘッド(V3)は破っていない(返るのはすべて `now` 以前の事象)ため、
安全性そのものの欠陥ではない。しかし戦略・将来のモデル実装が「直近 n 件だけを見たい、n は計算結果で
0 になり得る」という素朴な使い方をした瞬間に無言で全履歴を渡してしまう、公開 API の契約違反である。
作業者自身の試験は `n` に 2 以上の値しか使っておらず(`test_api_coupling.py` は `n` を渡していない)、
境界値 `n=0` が一度も検査されていない。

**patchwork**: false。

---

## i0-r1-03 [止める] `CoreEngine.run` のイベントループが O(n²) で、実データ規模で使用不能になる

**根拠(実行したコマンドと出力、3 回測定)**:

```
$ PYTHONPATH=src python3 -c "
import time
from bot.bt.core.engine import CoreEngine
from bot.bt.core.events import ClockEvent
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import to_nanos
class S(Strategy):
    def on_event(self, event, ctx): pass
for n in (5000, 20000, 50000):
    events = [ClockEvent(received_time_ns=to_nanos(1_700_000_000 + i, 's'), seq=0) for i in range(n)]
    t0 = time.time()
    CoreEngine(strategy=S(), events=events).run()
    print(n, time.time() - t0)
"
5000 0.0514...
20000 1.0363...   (n が 4 倍 → 時間は約 20 倍)
50000 6.4095...   (n が 2.5 倍 → 時間は約 6.2 倍)
```

```
$ PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_engine_run_scales_quadratically.py -v
AssertionError: 9.8x longer for 4x the events (small=0.0110s, large=0.1087s)
```

試験: `tests/bt/critic/item_0/test_engine_run_scales_quadratically.py`(壊れる。n を 4 倍にしても
線形なら約 4 倍で済むはずのところ、しきい値 8 倍を超える約 9.8〜10 倍かかることを 3 回測定して確認)。

**何が起きているか(ファイル:行)**: `src/bot/bt/core/engine.py:78-82` の `run` は毎イベントごとに
`visible = self._log[: i + 1]` を計算する。`tuple` のスライスはコピーを作るため、n 件の全体では
`1 + 2 + ... + n = O(n²)` の総コストになる。ループ全体がこの 1 箇所に依存している(V3 を「構造で」
強制する設計そのものは正しいが、実装の選び方が O(n) になっていない)。

**なぜ止めるか**: 委任文 §2 項目 0 の行は「事象の型(約定・板の写真・板の差分・…)」を核の対象に含み、
項目 13(統合)は「bitFlyer の約定 + 板 top10 の 1 日、Binance aggTrades の 1 日」をこの核に通すことを
要求している。板の差分・ティックは 1 日で数十万〜百万件に達し得る規模であり、実測の増加率(n を 4 倍で
約 10 倍)をそのまま延長すると、10 万件規模でも数分〜数十分、100 万件規模では現実的な時間で終わらない
(50,000 件で 6.4 秒。50,000→1,000,000 は 20 倍なので、O(n²) なら 6.4 秒 × 20² ≈ 2,560 秒 ≈ 43 分。
実測は 20,000→50,000 の区間でむしろ増加率が緩んでいるため、この外挿は下限の見積もりでしかない)。
これは「汎用バックテスト環境」というオーナーの完了の形(委任文 §0)そのものに反する。作業者自身の
試験は最大でも 5 件程度の事象しか使っておらず、この規模の欠陥を検出できる作りになっていない。

**patchwork**: false。

---

## i0-r1-04 [直す] `LiquidationEvent` に口座(`Account`)への差し込み口が無い(`FundingEvent` との非対称)

**根拠(実行したコマンドと出力)**:

```
$ PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_liquidation_has_no_account_hook.py -v
FAILED ...test_account_protocol_has_a_liquidation_hook
FAILED ...test_engine_notifies_the_account_of_a_liquidation_event
AssertionError: 0 != 1 : CoreEngine.run special-cases FUNDING to call account.apply_funding
but has no equivalent call for LIQUIDATION
```

**何が起きているか(ファイル:行)**: `src/bot/bt/core/engine.py:98-99` は
`if event.EVENT_TYPE is EventType.FUNDING: self._account.apply_funding(event)` と、資金調達だけを
口座へ明示的に配線している。`src/bot/bt/core/interfaces.py:71-74` の `Account` プロトコルにも
`apply_liquidation` に相当するメソッドが無い。一方 `LiquidationEvent` の docstring
(`src/bot/bt/core/events.py:93`)は「forced liquidation print (ours or market-wide)」と、
**自分の建玉の強制決済**を表しうると明記している。

**なぜ直すか**: 委任文 §2 項目 0 の行は「資金調達・清算」を並記しており、両方とも「口座が差し込む口」に
関わりうる決済系の事象である。しかし現状は資金調達だけが `engine.py` に直接ハードコードされて口座へ
届き、清算は届かない。`interfaces.py` 自身の docstring(1-14 行)は「item 3/4/5/6 は
`engine.py` を編集せずに差し込める」ことを核の価値として謳っているが、資金調達の配線が既に
`engine.py` への直書きになっている以上、清算も同じ要求(自分の建玉が強制決済されたら口座に反映する)が
出た時点で、また `engine.py` を書き換える必要が生じる ――「核を書き換えずに差し込める」という項目 0 の
約束を、項目 0 自身がその場しのぎで破っている。危険側(建玉が消えたのに口座残高が更新されない)に
振れる欠陥になりうるため「止める」に近いが、清算の口座反映自体は項目 6(口座と会計)の本体作業であり、
項目 0 の役目は「口座が差し込む口」を漏れなく用意することなので、ここでは「直す」とする
(`apply_funding` と対称な `apply_liquidation` をプロトコルに足し、`engine.py` の配線も対称にする)。

**patchwork**: false。

---

## 残された良い点(正直に書く)

- V1(`time.py`)・V4(`clock.py`)・V2(`events.py`)は、作業者自身の試験に加えて上記の壊しにいく試験
  (`test_visible_events_n_zero.py` 以外)でも崩れなかった。特に `to_nanos` の妥当性窓
  (`time.py:33-34`)と `clock.py` の全順序(`seq` を一意にすることで tie が起きない設計、
  `clock.py:47-57`)は、単位混在・タイの再現性という具体的な失敗モードに対して機構で効いている。
- V6 の骨格(`interfaces.py` の 4 つの `Protocol` + `Null*` 既定)は、i0-r1-04 の非対称を除けば
  「核を書き換えずに差し込める」ことを `test_extension_points.py` で実測どおりに示せている。

## 圧倒の判定への影響

[止める] が 2 件(i0-r1-01, i0-r1-03)残っている時点で、委任文 §0 の圧倒の判定(「[止める] が 0 件」)を
満たさない。この周は完了ではない。

## リードに聞くこと

無し(すべて項目 0 の設計・実装で解ける範囲の指摘であり、オーナー判断・データ不足には該当しない)。
