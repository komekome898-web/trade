# 担当 G3 の本走らせ(# 10。この容器で走らせる、L-719)

- 出所(オーナーの逐語): L-719「**11 項目この形で始める**」「**この容器で走らせる**」(# 10 だけ)。行の定義は `docs/DISCUSSIONS/2026-10-06_held_batches/D1B_FRAMINGS.md` の行 10。
- 台本: `scripts/d1b/g3/g3_run.py`(決定 `g3_decisions.py`・約定の記録の読み口 `g3_trades.py`・カード 4 の約定の道 `g3_c4_replay.py`)。試験 `tests/research/test_d1b_g3.py`。
- 約定の記録はこの容器の `data/tardis/bitflyer_FX_BTC_JPY_trades/` の 2023 年の 6 本だけを開く(表に無い名前は台本が拒む)。git の外のデータなので、測定用セッションでは走らない。
- 上限: 1 回(L-718「各束 1 周」)。落ちたら直さずに止めて、ログをリードに渡す。

## 打つもの(リポジトリの直下で、この順に)

```
# 走らせる前の条件: scripts/w4_measure/common.py の未コミットの変更(担当 A の usdjpy_ref_dataset(..., extend=True))に依存する。
#   担当 A の変更のコミットの後に走らせる(コミットの前の common.py では、カード 3 の参照の読み込みが引数の誤りで止まる)。

# 0. 試験
PYTHONPATH=src python -m pytest tests/research/test_d1b_g3.py

# 1. 件数の数え上げ(済み。やり直すときだけ。損益・値動きは計算しない)
PYTHONPATH=src python3 scripts/d1b/g3/g3_run.py --counts

# 2. 本走らせ(6 日。出力 docs/RESEARCH/d1b/10_cards34589/TABLES.md・g3.json)。10 分を超えるので切り離して打つ
setsid nohup bash -c 's=$(date +%s); PYTHONPATH=src python3 scripts/d1b/g3/g3_run.py --full > data/d1b_g3_full.log 2>&1; echo "exit $? 所要 $(( $(date +%s) - s )) 秒" >> data/d1b_g3_full.log' > /dev/null 2>&1 < /dev/null &
# 待ち方(回数の上限のあるループ。1 回 10 分まで、終わらなければ打ち直す)
for i in $(seq 1 115); do grep -q "^exit" data/d1b_g3_full.log 2>/dev/null && break; sleep 5; done; cat data/d1b_g3_full.log
```

## 見込みの時間(推定)

- 実測(2026-10-06、この容器、4 コア・15 GB): `--counts` は 1,558 秒(約 26 分)、最大の常駐メモリ約 1 GB(ps の RSS を途中で 2 回見た値)。
  このうち 6 分ほどは `--short 2023-07-01 --c4-start 2023-06-28T00:00:00Z`(355 秒)と並んで走った。
- `--full` は `--counts` と同じカード 3・5・8・9 の部分に加えて、カード 4 のシミュレーターが 2 本 → 4 本になり、6 日の分で約定の道を通す。
  見込みは **45〜60 分**【推定: 数え上げの所要の内訳(カードの部分とカード 4 の部分)を測っていないので、カード 4 の部分が全体の半分〜3 分の 2 として 2 倍した】。
- 出力: `docs/RESEARCH/d1b/10_cards34589/TABLES.md`・`g3.json`(決定ごとの行を含む)。数え上げの `COUNTS.md`・`counts.json` は上書きしない。
- ログは `data/d1b_g3_full.log`(git の外。容器の再起動で消えたのは /tmp の下で、作業ツリーの下は残った)。
- **`scripts/w4_measure/common.py` が変わったら(走らせ直しの担当 A の変更のコミットを含む)、数え上げ(上の 1)を打ち直す。** 打ち直すかはリードが決める(2026-10-06 のリードの決め 9)。
- 区間(批評家 1 回目の後のリードの決め): 主 = 日を 1 塊とした区間(6 日を選び直す、1,000 回、種 20261006)と日ごとの表。決定を独立とみた Wilson の 95% 区間(印つき)を並べる。前半・後半は点だけ。`COUNTS.md` の表の形だけを変えたときは `PYTHONPATH=src python3 scripts/d1b/g3/g3_run.py --render-counts`(`counts.json` から書き直す。計算しない)。
- **依存(批評家 1 回目の問 3): `scripts/d1b/g3/g3_decisions.py` は `scripts/w4_measure/common.py` の未コミットの変更(担当 A の `usdjpy_ref_dataset(..., extend=True)`)に依存する。担当 A の変更のコミットの後に走らせる。**
