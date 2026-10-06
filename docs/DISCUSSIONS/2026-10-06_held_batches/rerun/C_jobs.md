# 走らせ直しの一覧 — 担当 C(カード 9)

- 委任文: `docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_rerun_impl.md`(担当 C: カード 9)
- 中身(委任文の表): 「状態機械の入りと出を「成行で叩く側の約定」にし、レグごとの経路を残す」1 本
- 元の文書: `docs/ANALYSIS/2026-10-05_card9_liquidation_cascade.md` D10 の次の手 2
- 元の走らせ: `PYTHONPATH=src python3 scripts/c9_run_a.py --start 2023-06-25 --end 2024-10-14 --out data/c9_run_a/full_20230625_20241014`(`--resume` で 3 回に分けて完走)。指紋は `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/MANIFEST.md`(`run_meta.json` = `0852ebb6…6fe2`、`policy_cascades.csv.gz` = `657ae5b4…202d5b`、`policy_legs.csv.gz` = `8b00c84b…e503b`)。カード 9 には `run_record.json` が無い。
- リードの決め(2026-10-06): 約定の値段 = COIN-M BTCUSD_PERP の最良気配(Binance 公開アーカイブ `bookTicker`、目標の時刻以前で最新、買いは売り気配・売りは買い気配、古さ 300 秒越え・ファイルの無い日は値の欠け)。直前の同じ側の約定 (b) と待つ形 (a) は並べる列。期間 `--end 2023-12-17`(封印の境 2023-12-17T15:00Z より後を読まない)。どちらの側でもの形の経路は走らせない。批評家 1 回目(`docs/AUDITOR/VERDICTS/2026-10-06_c9_rerun_critic1.md`)の [止める] と [直すとよい] を受けた直し。批評家 2 回目(`docs/AUDITOR/VERDICTS/2026-10-06_c9_rerun_critic2.md`)は「走らせ #1 は走らせてよい」。ただしその [止める](走らせの後の検めが元の走らせの 2023-12-17 の出力を読む)と [直すとよい] を直した後に打つ。直しの確かめはリードが行う(批評家 3 回目は呼ばない)。
- 台本: `scripts/c9_run_a.py` に `--fill-side {any,quote}`(既定 any = 元)・`--leg-path`・`--quotes-dir`。中身は `src/bot/research/liq_cascade_fill.py` の docstring。気配の取得は `scripts/c9_fetch_bookticker.py`。

## 走らせる前に(リポジトリの直下で。担当 C が済ませたものは印)

1. 試験: `PYTHONPATH=src python -m pytest tests/research/test_liq_cascade_fill.py tests/research/test_liq_cascade_v2.py` が全部通ること。
2. 【済】境より前だけの読み口: `python3 docs/RESEARCH/cards/c9_liquidation_cascade/rerun_2026-10-06/make_cut_root.py --dst data/c9_run_a/cut_root_20231216`(約定 174 日・清算 172 日・metrics 173 日・資金調達率 7 か月のリンク。`c9_run_a.py` は `--end` の後も読む(清算 + 4 日・約定 + 11 日・資金調達率は月次 zip を全部)ので、この読み口を `--data-root` に渡す)。
3. 【済】気配の取得: `PYTHONPATH=src python3 scripts/c9_fetch_bookticker.py --data-root data/c9_run_a/cut_root_20231216 --start 2023-06-25 --end 2023-12-17 --out data/c9_bookticker`(2023-06-21〜2023-12-16 の日だけ。生のファイルは残さず、目標の時刻ごとの気配の表 `days/<日>.csv.gz` と記録 `fetch_log.jsonl`・`fetch_summary.json` を残す)。取れなかった日は担当 C の報告に数を書いた。`--start`・`--end`・`--data-root` は下の走らせと同じ値でなければならない(目標の時刻の組が同じプリントから作られる。違えば走らせが「気配の表に無い目標の時刻」で止まる)。

## 走らせ(1 行 = 1 本)

| # | コマンド(リポジトリの直下で) | 出力先 | 見込みの時間 |
|---|---|---|---|
| 1 | `PYTHONPATH=src python3 scripts/c9_run_a.py --start 2023-06-25 --end 2023-12-17 --data-root data/c9_run_a/cut_root_20231216 --out data/c9_run_a/rerun_quote_20230625_20231217 --fill-side quote --leg-path --quotes-dir data/c9_bookticker >> data/c9_run_a/rerun_quote_20231217.log 2>&1` | `data/c9_run_a/rerun_quote_20230625_20231217/`(git の外) | 約 30〜60 分・最大 RSS 1.7 GB 以下【推定】 |

- 上限: 1 周・1 本(L-718「**各束 1 周**」)。途中で落ちたら、**同じ引数**に `--resume` を足して 1 回だけ続きから走らせる(引数を変えて続けると日ごとの行が混ざる)。2 回目も落ちたら止めて報告する。
- 見込みの時間の出所【推定】: 元の走らせの日ごとの所要のうち 2023-06-25〜12-17 の 176 日の和 1,257 秒(対照 865・値動き 272・材料 75・状態機械 23・約定の窓 20・s 秒の曲線 2)。quote は状態機械を 4 回流す(元の付け方・気配・(b)・(a))。短い期間の確かめ(2 日)は既定 10 秒・quote 11 秒。ディスクの空きは約 2 GB(2026-10-06 の `df -h /`)。出力の大きさは未確認。
- 読み口の効き(【事実: コード】と【推定】): 2023-12-17 はファイルが無いのでプリント 0・約定の欠け・気配の欠けとして走る。2023-12-16 の束のうち出の目標の時刻が 12-17 にあるものがあれば値の欠けになるが、気配の取得で作った目標の組では 12-17 にかかる目標は 0 個【事実: `targets_for_prints` を数えた】。2023-12 のプリントの材料 10(資金調達率)は 2023-11 の最後の値(`latest_at_or_before` に古さの上限が無い)で、規則_3択 の確率にだけ効く。
- 出るもの(元と同じファイルの組に足す・変わるもの):
  - `policy_cascades.csv.gz`・`policy_legs.csv.gz`: `pnl_bp`(と `hold_s` などの主の値)が気配の値。連鎖の行に `fill_side`・`pnl_bp_anyside`・`missing_anyside`(元の付け方)・`pnl_bp_taker_prev`・`missing_taker_prev`((b))・`pnl_bp_taker_wait`・`missing_taker_wait`((a))。レグの行に経路の列 19 個(`in_target_ms`・`in_fill_ms`(気配の時刻)・`in_px`・`in_lag_ms`(≤ 0)・`in_quote_age_ms`(= 目標の時刻 − 気配の時刻)・出も同じ・`order_in`・`order_out`・`path_ok`・`path_n`・`mfe_bp`・`mae_bp`・`mfe_after_s`・`mae_after_s`)と `pnl_bp_anyside`・`pnl_bp_taker_prev`・`pnl_bp_taker_wait`。経路の起点 p0 は気配で付けた入りの値段、経路は (入りの目標, 出の目標] の約定(両側)。
  - `chunks/{cascades,legs,cascades3,legs3}_any/`: 元の付け方(1 回目)の結果を元と同じ列で書いたもの(再現の検め用)。
  - `dist_policy.csv`: 気配の `pnl_bp` で集計したもの。`期間`(作る/測る)はこの走らせの 176 日を半分にした境(2023-09-20 / 09-21)で、元の境 2024-02-19 と違う。
  - `run_meta.json`: 鍵「走らせ直し_2026-10-06」(fill_side・leg_path・quotes_dir)。
  - 規則_3択 の行は、この走らせの前半で作った模型を後半に当てたもので、元の走らせ(2024-02-18 までで作り 02-19 以降に当てた)とは別の模型。元にはこの期間の 規則_3択 の行が無い。
  - 段 3(規則_3択)の約定の窓は、quote のときだけ段 2 とそろえて前の日も読む(既定は元のとおり当日と翌日)。

## 限界と、データの穴(走らせる前から分かっていること)

- **注文の大きさを考えない約定(限界)**: 主の値段は最良気配の値段で、注文の数量にかかわらずその値段で全量が約定したとみなす。気配の数量の列(`best_bid_qty`・`best_ask_qty`)は取得の台本 `read_quotes` が読まずに落とし、生のファイルは消してあるので、この走らせの出力からは数量の効きを測れない(取り直しはしない。リードの決め)。カードは注文の大きさを決めていない。参考に、批評家 2 回目は 07-01 の目標で最良気配の数量の最小と 1% の点が 1 枚(100 USD)だったと書いている【事実: 批評家 2 回目の記録】。
- **2023-09-21 の気配の穴**: アーカイブの気配が 18:05:10 から 19:16:06 まで 1 本も無い(批評家 2 回目。その間に約定は 3,331 件)。この日の目標 414 個のうち 14 個(目標の時刻 19:11:20〜19:16:06)は、使える最新の気配が 18:05:10 で古さが 300 秒を越えるので、主(気配)の値が欠けになる【事実: `data/c9_bookticker/days/2023-09-21.csv.gz` を数えた】。欠けになる連鎖・レグの数は走らせの後の検めで数える。
- **2023-09-25**: 気配のファイルがアーカイブに無い(HTTP 404)。この日に当たる目標の時刻は 0 個【事実】。

## 走らせの後の検め

```
python3 docs/RESEARCH/cards/c9_liquidation_cascade/rerun_2026-10-06/check_repro.py \
    --orig data/c9_run_a/full_20230625_20241014 --new data/c9_run_a/rerun_quote_20230625_20231217 \
    --start 2023-06-25 --end 2023-12-17 --ignore period --skip-policy 規則_3択 \
    --quotes-dir data/c9_bookticker
```

- **境の守り**: 元の走らせの置き場は 2023-12-16 までの日しか開かない。2023-12-17 の日は元と比べず、新しい出力の行の数・主の値の検め・気配の表との突き合わせ・欠けの数だけを出す(`check_repro.read_orig` が 2023-12-17 以後の日を開こうとしたら止める。試験 `test_check_repro_never_opens_orig_after_seal`)。元の走らせの 2023-12-17 の出力は、境より後の約定から計算した値を含みうるので読まない(批評家 2 回目の [止める])。
- (1) 再現(2023-06-25〜12-16): 新しい走らせの `chunks/*_any/`(元の付け方の 1 回目)の行を、元の `chunks/` の同じ日の行と (side, gap_s, start_ms, delay_s, policy, type) と並び順で突き合わせ、元の列すべてが同じかを見る。主の付け方でレグの数が変わっても落ちない。2023-12-16 は、出の目標が 12-17 にかかる束があれば元と違いうる(読み口に 12-17 が無い)【推定。気配の取得の目標の組では 12-17 にかかる目標は 0 個だったので、違いは出ないはず】。
- (2) 主の値の検め(全日): 遅れ ≤ 0・古さ = −遅れ ≤ 300 秒・`order_in` = 束の側 × 順張り/逆張り・`order_out` = −`order_in`・`pnl_bp` を `in_px`・`out_px` から計算し直した一致・`mfe_bp` ≥ 0 ≥ `mae_bp`・連鎖の `pnl_bp` = レグの和。
- (3) 気配の表との突き合わせ(全日): `in_px`・`out_px`・`in_fill_ms`・`out_fill_ms` を `data/c9_bookticker/days/` から引き直した値(買いは売り気配・売りは買い気配)と比べる。
- (4) 付け方ごとの値の欠けの数(全日と合計): 主(気配)・元の付け方・(b)・(a) ごとに、欠けた連鎖の数・その連鎖のレグの数・レグの損益の列が NaN のレグの数(主は列が無いので数えない)。2023-09-21 の 14 個の目標が、主の欠けの連鎖として出るはず。比べるときは同じ連鎖の組でそろえる(読みの段でリードが行う)。
- 「違いと外れの合計」が 0 で終了コード 0 なら通った。0 でなければ止めて報告する。(4) の数は外れに数えない(報告に添える)。
- 見込みの時間: 未確認(07-01 の 1 日は数秒)。
