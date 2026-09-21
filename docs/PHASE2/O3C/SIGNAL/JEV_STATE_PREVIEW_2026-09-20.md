# Jev に渡す状態の下見(前半 200 件 × 3 通り)の報告(2026-09-20)

委任文 `docs/DATA/delegations/20260920_o3c_signal_jev_state_prompt.md`。委任先(下位モデル)が道具・試験・帯の定数・下見の呼び出しを作り、リードが引き取りで問いの文と文の型を直して再実行した(設計 §6.5.1)。**性能の数値(一致率・分布)はここに書かない。表は `data/jev/state_preview/tables.md`(gitignore 済)。**

## (0) 件数と呼び出し数

- 対象 200 件(前半、前段の下見と同じ層化抽出: {'SELL_1': 34, 'SELL_2': 34, 'SELL_3': 33, 'BUY_1': 33, 'BUY_2': 33, 'BUY_3': 33})、呼び出し 600 回(V1・V2・V3 × 200)、エラー 0、経過 334 秒。
- 直す前の版(古い criteria)で呼んだ 146 回は `answers_partial_oldcriteria_1326.jsonl` に退避し、集計に使っていない。

## (1) 対応表(委任文 §0 の写し)

| やること | オーナーの原文の該当語(逐語) |
|---|---|
| 材料を「Jev が判断できる言葉で書けるか」で選び、英文の列で渡す | 「**jevが判断しやすいような言葉かどうかが、材料の判断基準になるのでは？**」(L-308)、「**その基準と案で進めてください**」(L-309) |
| 問いは 1 つ(60 秒以内に同じ側の次の清算が来るか) | 「**清算を検知→jevでこの清算は続くか判断**」(L-262)、「**あなたはこの問いと材料を混同してませんか？**」(L-303) |
| 前半 200 件で渡し方 3 通りを比べてから後半へ | L-309 の承認(設計 §6.5) |
| 数値の結果は `data/jev/` にだけ | `docs/JEV.md` §4-7、L-310 |

## (2) 実行したコマンド

```
PYTHONPATH=src python3 scripts/o3c_jev_state.py --stage preview   # 帯の定数 → config/o3c_jev_state_bands.yaml、下見 → data/jev/state_preview/answers.jsonl
PYTHONPATH=src python -m pytest tests/test_o3c_jev_state.py         # 25 passed
```

## (3) state の実物 10 件(V1 の英文そのまま。事後の位置は表のためだけに付けた。state には入っていない)

### 2024-02-06_00012(単発)

- SELL liquidation, among the largest fifth of prints, at 06-12 UTC.
- No same-side liquidation in the last 60 seconds.
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 0.0 seconds ago and has not pulled back.
- Over the last 60 seconds price fell 23.3 bp (range 23.2 bp); over the last 10 seconds it fell 6.0 bp.
- Taker flow in the last 5 seconds: 96% sells; over 30 seconds: 25% (more one-sided now). Price fell 4.5 bp in the last 5 seconds.
- No open interest within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: flat. Funding: positive.
- Price is some distance from the day's low. Volatility now vs the last hour: much busier. Trading activity in the last 60 seconds: among the second-busiest fifth.

### 2023-12-29_00112(単発)

- SELL liquidation, among the second-smallest fifth of prints, at 12-18 UTC.
- No same-side liquidation in the last 60 seconds.
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 0.4 seconds ago and has not pulled back.
- Over the last 60 seconds price fell 8.9 bp (range 10.1 bp); over the last 10 seconds it fell 2.6 bp.
- Taker flow in the last 5 seconds: 81% sells; over 30 seconds: 74% (more one-sided now). Price fell 2.7 bp in the last 5 seconds.
- No open interest within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: rising fast. Funding: positive.
- Price is close to the day's low. Volatility now vs the last hour: much calmer. Trading activity in the last 60 seconds: among the second-quietest fifth.

### 2023-11-13_00017(単発)

- SELL liquidation, among the smallest fifth of prints, at 00-06 UTC.
- No same-side liquidation in the last 60 seconds.
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 0.1 seconds ago and has not pulled back.
- Over the last 60 seconds price fell 15.8 bp (range 15.9 bp); over the last 10 seconds it fell 10.0 bp.
- Taker flow in the last 5 seconds: 89% sells; over 30 seconds: 72% (more one-sided now). Price fell 6.2 bp in the last 5 seconds.
- No open interest within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: falling fast. Funding: positive.
- Price is close to the day's low. Volatility now vs the last hour: calmer. Trading activity in the last 60 seconds: among the second-quietest fifth.

### 2023-07-12_00034(多件の最初)

- SELL liquidation, among the second-smallest fifth of prints, at 12-18 UTC.
- No same-side liquidation in the last 60 seconds.
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 25 seconds ago and has pulled back 2.2 bp since.
- Over the last 60 seconds price fell 21.4 bp (range 23.6 bp); over the last 10 seconds it fell 1.1 bp.
- Taker flow in the last 5 seconds: 87% sells; over 30 seconds: 57% (more one-sided now). Price fell 3.0 bp in the last 5 seconds.
- No open interest within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: rising fast. Funding: positive.
- Price is some distance from the day's low. Volatility now vs the last hour: busier. Trading activity in the last 60 seconds: among the second-busiest fifth.

### 2024-01-10_00042(多件の最初)

- SELL liquidation, among the largest fifth of prints, at 06-12 UTC.
- No same-side liquidation in the last 60 seconds.
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 0.1 seconds ago and has not pulled back.
- Over the last 60 seconds price fell 13.6 bp (range 29.2 bp); over the last 10 seconds it fell 8.9 bp.
- Taker flow in the last 5 seconds: 82% sells; over 30 seconds: 75% (more one-sided now). Price fell 7.2 bp in the last 5 seconds.
- No open interest within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: flat. Funding: positive.
- Price is close to the day's low. Volatility now vs the last hour: much busier. Trading activity in the last 60 seconds: among the second-busiest fifth.

### 2023-12-16_00007(多件の最初)

- SELL liquidation, among the smallest fifth of prints, at 00-06 UTC.
- No same-side liquidation in the last 60 seconds.
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 0.7 seconds ago and has not pulled back.
- Over the last 60 seconds price fell 5.1 bp (range 6.3 bp); over the last 10 seconds it fell 3.9 bp.
- Taker flow in the last 5 seconds: 99% sells; over 30 seconds: 86% (more one-sided now). Price fell 2.3 bp in the last 5 seconds.
- No open interest within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: falling. Funding: positive.
- Price is at the day's low. Volatility now vs the last hour: similar. Trading activity in the last 60 seconds: among the quietest fifth.

### 2024-01-12_00154(途中)

- SELL liquidation, among the second-smallest fifth of prints, at 12-18 UTC.
- It is the 3th same-side liquidation of a cascade that began 39 seconds ago; the amount liquidated so far is among the second-smallest fifth of cascades.
- The last two same-side liquidations were 38 and 39 seconds ago; the gaps are getting longer. This print is smaller than the previous one.
- No same-side liquidation in the last 10 seconds.
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 0.1 seconds ago and has not pulled back.
- Over the last 60 seconds price fell 17.8 bp (range 28.5 bp); over the last 10 seconds it fell 6.4 bp.
- Since the previous same-side liquidation, the largest pullback was 24.5 bp.
- Since the cascade began, price has fallen 5.0 bp.
- Taker flow in the last 5 seconds: 72% sells; over 30 seconds: 60% (more one-sided now). Price fell 6.1 bp in the last 5 seconds.
- No open interest within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: flat. Funding: positive.
- Price is very close to the day's low. Volatility now vs the last hour: calmer. Trading activity in the last 60 seconds: among the second-busiest fifth.

### 2023-10-27_00077(途中)

- SELL liquidation, among the smallest fifth of prints, at 18-24 UTC.
- It is the 2th same-side liquidation of a cascade that began 12 seconds ago; the amount liquidated so far is among the second-smallest fifth of cascades.
- The last two same-side liquidations were 12 and 137 seconds ago; the gaps are getting shorter. This print is smaller than the previous one.
- No same-side liquidation in the last 10 seconds.
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 1.5 seconds ago and has pulled back 1.9 bp since.
- Over the last 60 seconds price fell 5.9 bp (range 12.2 bp); over the last 10 seconds it rose 1.1 bp.
- Since the previous same-side liquidation, the largest pullback was 1.1 bp.
- Since the cascade began, price has risen 1.1 bp.
- Taker flow in the last 5 seconds: 55% sells; over 30 seconds: 46% (more one-sided now). Price fell 0.0 bp in the last 5 seconds.
- No open interest within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: rising. Funding: positive.
- Price is some distance from the day's low. Volatility now vs the last hour: similar. Trading activity in the last 60 seconds: among the quietest fifth.

### 2023-09-27_00057(多件の最後)

- SELL liquidation, among the second-smallest fifth of prints, at 12-18 UTC.
- It is the 2th same-side liquidation of a cascade that began 42 seconds ago; the amount liquidated so far is among the second-smallest fifth of cascades.
- The last two same-side liquidations were 42 and 132 seconds ago; the gaps are getting shorter. This print is smaller than the previous one.
- No same-side liquidation in the last 10 seconds.
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 1.2 seconds ago and has pulled back 9.4 bp since.
- Over the last 60 seconds price fell 6.3 bp (range 15.7 bp); over the last 10 seconds it rose 1.8 bp.
- Since the previous same-side liquidation, the largest pullback was 1.0 bp.
- Since the cascade began, price has fallen 2.8 bp.
- Taker flow in the last 5 seconds: 49% sells; over 30 seconds: 49% (about the same). Price rose 0.5 bp in the last 5 seconds.
- Open interest among the largest fifth within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: falling fast. Funding: positive.
- Price is far from the day's low. Volatility now vs the last hour: similar. Trading activity in the last 60 seconds: among the middle fifth.

### 2023-12-11_00250(多件の最後)

- SELL liquidation, among the middle fifth of prints, at 18-24 UTC.
- It is the 3th same-side liquidation of a cascade that began 2.5 seconds ago; the amount liquidated so far is among the second-smallest fifth of cascades.
- The last two same-side liquidations were 1.0 and 2.5 seconds ago; the gaps are getting shorter. This print is larger than the previous one.
- Same-side liquidations in the last 10 seconds: among the middle fifth (of prints that had any).
- No opposite-side liquidation in the last 60 seconds.
- Price made a new 60-second low 1.1 seconds ago and has pulled back 8.5 bp since.
- Over the last 60 seconds price fell 38.9 bp (range 47.8 bp); over the last 10 seconds it fell 16.7 bp.
- Since the previous same-side liquidation, the largest pullback was 9.3 bp.
- Since the cascade began, price has risen 1.3 bp.
- Taker flow in the last 5 seconds: 58% sells; over 30 seconds: 74% (less one-sided now). Price fell 12.3 bp in the last 5 seconds.
- No open interest within 20 bp below the current price; within 5 bp: none (coverage: yes). Nearest liquidation level below: none within the mapped range.
- Open interest over the last hour: rising fast. Funding: positive.
- Price is far from the day's low. Volatility now vs the last hour: busier. Trading activity in the last 60 seconds: among the busiest fifth.

## (4) 設計に無い判断(委任先 10 件 + リードの直し 3 件 = 設計 §6.5.1 に記録)

委任先: 間隔・規模の「同程度」の幅 = 比 1 ± 0.15 / 成行の偏りの変化「変わらない」の幅 = 0.10 / 戻り 0 の閾値 = 0.05 bp / 日の極値「at」= 0.05 bp 以内、他 4 段は正の値の四分位 / 建玉の傾き 5 段 = 前半の五分位 / 型 9 は価格の経路から直接計算 / 型 4・5 の「無し」の文言を "No X in the last Ys." に統一 / 1 件目の判定 = `cand_1 == 0` / V3 に `assert_clean` を掛けない / 型 7・10 の数は符号つき(→ リードが語に直した)。
リード: V1 の問いを設計 §6.3 の文に置き換え(委任先は前段の古い criteria を使っていた)/ 型 7・10 の向きを語で書く / 「getting about the same」→「about the same」。

## (5) サニティ

- 未来を使わない: 試験 `test_no_future_data`・`test_p0_rewrite_invariance`(ts 以後の約定を変えても、p₀ に当たる約定の価格を書き換えても同じ文)。
- 決定性: 同じ入力で同じ文(試験)。帯の境界は前半だけ(後半の値を変えても同じ、試験)。
- リードが 3 件(単発・多件の最初・多件の最後)の英文を読み、文の型 13 本と向きの語を確かめた(設計 §6.5.1)。
- 版 `jev-1.13.0`、応答の `model` を全件記録(600 件とも一致)。

## (6) 限界

- 200 件は前半の下見で、選ぶ側の標本。ここでの一致は後半の較正ではない。
- 帯の言葉は前半の分布に対する相対の位置。後半でも同じ境界を使う。
- 位置ごとの答えの違いは表にだけ出し、判断には使っていない。

## (7) 作ったファイル

- `scripts/o3c_jev_state.py`、`tests/test_o3c_jev_state.py`(25 件)、`config/o3c_jev_state_bands.yaml`、`data/jev/state_preview/{answers.jsonl, preview_notes.json, tables.md, calls/}`(gitignore 済)、この報告。

## (8) テストの末尾行

- `tests/test_o3c_jev_state.py`: `25 passed in 0.48s`(リードの直しの後)。
- 全スイート(リードが直した版、`PYTHONPATH=src python -m pytest`、`-q` 無し): `2729 passed, 5 skipped, 1 warning in 454.57s (0:07:34)`
