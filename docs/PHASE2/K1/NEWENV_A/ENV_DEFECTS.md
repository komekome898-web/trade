# K1 段階 A — 環境の欠陥(再現手順・ファイル:行・根本原因・直したか・試験)

委任文 §2-4「**欠陥**: `ENV_DEFECTS.md`(再現手順・ファイル:行・根本原因・直したか・試験)。直したら関係する試験(`tests/bt/item_*`・`tests/bt/critic/item_*`・場面集)を私有の basetemp で回す。核を変えたら CORE_VERSION を上げる。場面集と規則の文は変えない」。オーナー逐語(L-476)「**研究の最初の単位を回して、そこで出る欠陥を直す**」。

「欠陥」の範囲: K1 と同じ入力・同じ規則を通すのに**足りなかった物**と、**通したときに壊れた物**。数の違いの裁きは DIFF.md。**核(`src/bot/bt/core/`)は 1 行も変えていない → CORE_VERSION は据え置き。** 場面集(`tests/bt/battery/`)と規則の文(`DEFINITIONS.md`)も変えていない。

| # | 何が起きたか(再現手順) | 場所 | 根本原因 | 直したか | 試験 |
|---|---|---|---|---|---|
| E-1 | **データ層に「細かい足 → 粗い足」の畳みが無い。** `grep -rn "def .*fold\|resample\|bars_from_bars" src/bot/bt` → `bars_from_trades`(約定 → 足)だけ | `src/bot/bt/vector/bars.py`(V7 は約定からの足だけを定義) | 項目 1 の要件が「約定 → 足」だけを置き、既製の秒バーからの畳みを想定していなかった | **直した(追加)**: `bars_from_bars(start_ns, o, h, l, c, v, interval_s)` を `vector/bars.py` に新設し `bot.bt.vector` から公開。規則は RESULT.md 1.2 のとおり(UTC 格子・最初/最大/最小/最後・無い区間は作らない) | `tests/bt/item_1/test_i1_bars_from_bars.py`(手計算の場面、1s→3s→6s の連鎖 = 直接畳みの一致、空・逆順の拒否)+ `tests/bt/item_1/` 全部 |
| E-2 | **秒バー 3 年分(49,054,818 行)を 1 回の `load()` で読めない。** 1 日 46,448 行の読みが 2.98 s・最大 RSS 127 MB(`scripts/k1_newenv_fold.py --days-limit 2` 相当の実測 = 64 µs/行、行ごとに `Row` + `BarEvent` + JSON の identity を持つ)。線形に外挿すると 3 年で **約 52 分・数十 GB**(推定)。この機械は 15 GB | `src/bot/bt/data/loader.py:459-511`(`load` は全ファイルの全行を Python の物として保持)、`loader.py:507`(`identity = (json.dumps(rec), cells.rest())` を行ごとに作る) | データ層の設計が「読んだ行を全部持って検査する」であり、流し読み(streaming)や列指向の読みを持たない。要件(項目 1)は正確さと拒否を優先し規模を扱っていない | **直していない**(設計の変更 = リードの判断)。**回避**: 日ファイルごとに `load()` して即座に畳み、秒バーは捨てる(`scripts/k1_newenv_fold.py: fold_year`)。3 年 3 プロセス並列で **`FOLD_MANIFEST.json: wall_s_total`** 秒(PERFORMANCE.md) | — |
| E-3 | **統合の口 `bot.bt.pipeline` の約定の模型 `SimVenue` は、足だけの銘柄の成行を「その足の終値」で約定できない。** `orders/rules.py` の `market_ref` は `next_bar_open`(次の足の始値 + スプレッド/2)か `last_trade`(約定事象が無い足の列では `last_trade is None` → `no_price_yet` で閉じる) | `src/bot/bt/fill/venue.py:554-567`(`_aggress_no_book`)、`venue.py:734-748`(`_on_bar`: `bar_open` 状態の注文だけ) | 項目 2 の約定の模型が「先読みしない = 次の足の始値」を足の列の唯一の成行の値付けとした。K1 の規則(RESULT.md 1.4「建値も決済値も『その足の終値』」)は足を受けた瞬間の終値で建てる規則で、この模型には無い | **直していない**(項目 2 の規則の追加 = 設計の判断。リードに聞く: D-1) 。**回避**: 記録の口 `bot.bt.repro.runner`(setup が約定の口を差す設計)を使い、`k1_wick.py: BarCloseMarketFill`(直前に受けた足の終値で全量即時約定)を setup から差した。核の順序(`ordering.py`: venue market data → arriving requests → deliveries)により、足を受けた戦略の注文は同じ瞬間に同じ足の終値で約定する | `tests/test_k1_wick.py::test_scene_a_both`(e1 = 足 0 の終値、時刻 = 足 0 の閉じる時刻) |
| E-4 | **`bot.bt.validation.bootstrap.block_bootstrap_ci` は固定長ブロック(`block_len`)で、K1 の「入口の日でブロック」(日ごとの本数が違う)を表せない** | `src/bot/bt/validation/bootstrap.py:64-` | 検証の道具が時系列の一般形(固定長ブロック)だけを置いた | **直していない**(統計の追加 = 設計の判断)。**回避**: 表の生成側 `scripts/k1_newenv_tables.py: block_bootstrap` に規則の文どおりの日ブロックを書いた(INTENT_MAP T-5 = △) | — |
| E-5 | **`bot.bt.pipeline` の `module` 戦略の口(L-476 の O-1 の途中の編集、457dcef4 で checkpoint)は段階 A に要らない**(E-3 のとおり pipeline は K1 の約定規則を持たないので、module の口があっても K1 は pipeline で回せない) | `src/bot/bt/pipeline.py`(457dcef4 の +67 行)、`src/bot/strategy/u1_range_center.py`、`tests/bt/item_4/test_i4_module_strategy.py` | 委任文 §3「取り下げなので、要らなければ消し、要るなら理由を書いて使う」 | **消した**: `git checkout 457dcef4~1 -- src/bot/bt/pipeline.py` + 2 ファイルの削除(コミットはしない = 作業木の差分として残す) | `tests/bt/item_4/`(pipeline の既存の試験)を回す |
| E-6 | `/usr/bin/time` がこの環境に無い(`/usr/bin/time: No such file or directory`、EXIT 127) | 実行環境 | 道具が入っていない | **回避**: `resource.getrusage(RUSAGE_SELF / RUSAGE_CHILDREN)` の `ru_maxrss` と `time.time()` を各スクリプトが記録 | — |
| E-7 | **`runner._execute` は 1 セルにつき足ファイルを 2 回読む**(2 回実行して byte 比較する設計)。1 分足(3 年で約 1.4M 行)の読みは 1 回 **PERFORMANCE.md の値** 秒で、核の実行より長い | `src/bot/bt/repro/runner.py:157-160`(`_execute` 内で `load`)、`runner.py:261-275`(`_twice`) | 再現の確認を「入力から全部やり直す」と定義した(データの読みを 2 回目に省く設計は、読みの再現も確かめる意図と衝突する) | **直していない**(設計どおり。性能の事実として記録) | — |

## 直した試験の実行(私有の basetemp)

コマンドと末尾の行は報告の (b) に写す。

```
PYTHONPATH=src python3 -m pytest tests/bt/item_1 tests/test_k1_wick.py tests/bt/item_4 tests/bt/critic tests/bt/battery -p no:cacheprovider --basetemp=/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/pt_k1a
```

## リードに聞くこと(設計の判断が要るもの)

- **D-1(E-3)**: 項目 2 の `market_ref` に「直前の足の終値」を足すか(K1 系の規則を `bot.bt.pipeline` で回せるようにする)。段階 A は `runner` + setup の約定の口で回したので、統合の口(両側の約定・遅延・費用・口座)は通っていない。
- **D-2(E-2)**: データ層に流し読み(ファイルごとの逐次処理・列指向)を足すか。今回は日ファイルごとの `load()` で回避したが、秒バーの 1 回読みで数十 GB という壁は残る。
- **D-3(E-4)**: 検証の道具に「日でブロック」を足すか。
