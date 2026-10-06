# 前提の直接の測り # 4・# 7 の走らせ直し(事象ごとの行を git に残す形)— ジョブ

- 出所(オーナーの逐語、L-723): 「**3.yes**」。問いは状態板の判断が要る項目 3 件目で、逐語は次のとおり。「前提の直接の測り # 4(マチルダ)と # 7(バリアレース)を、同じ台本・同じ引数で、1 回の離れごと・起点ごとの行を git に残す形でもう 1 回走らせるか(測定用セッション、見込み 30〜60 分)」
- 上限: 1 本・1 回(L-718「各束 1 周」)。
- 同じ台本・同じ引数: `scripts/d1b/g2/run_g2.py --mode full --items 4,7`。変えるのは出力の置き場だけ。
  - 表の出力 `--out-root`: 元の置き場を上書きしないように、別の置き場にする。
  - 事象ごとの行 `--records-dir`: git の中にする。

## 打つもの(この順)

1. `pip install -e ".[dev]" -q` と `PYTHONPATH=src:scripts/d1b/g2 python -m pytest tests/research/test_d1b_g2.py`(落ちたら止まる)
2. 走らせ(10 分を超えるので、Bash の道具の run_in_background で。ログは /tmp/g2_records.log):

       PYTHONPATH=src python3 scripts/d1b/g2/run_g2.py --mode full --items 4,7 --out-root docs/RESEARCH/d1b/rerun_records_2026-10-06 --records-dir docs/RESEARCH/d1b/rerun_records_2026-10-06/records

3. 同じかの確かめ: 次の 2 組の TABLES.json を比べ、`meta`(時刻・起動の記録)を除いて同じかを出す(python で json を読み、`meta` の鍵を落として == で比べる。違えば違う鍵の一覧を出す)。
   - 新しい `docs/RESEARCH/d1b/rerun_records_2026-10-06/4_card4/TABLES.json` と、元の `docs/RESEARCH/d1b/4_card4/TABLES.json`
   - 新しい `docs/RESEARCH/d1b/rerun_records_2026-10-06/7_card7/TABLES.json` と、元の `docs/RESEARCH/d1b/7_card7/TABLES.json`
4. 事象ごとの行の大きさを出す(`ls -la` と `zcat | wc -l`)。1 ファイルが 50 MB を超えたら git に入れず、止めて報告する。

## 決まり

- `backtest_data/phase2_sealed/` と `docs/RESEARCH/WINDOW1/` は読まない(ls・grep・find を含む)。台本は 2023-12-17T15:00Z より後を読まない(台本の門)。
- 各コマンドは 1 回だけ。失敗したら打ち直さず、コマンド・戻り値・ログの末尾 50 行を報告する。
- 終わったら、出力の置き場を `git add` し、英語の短い文でコミットして、指定の枝に押し出す。押し出しの関門で止まったら、関門の出力を報告して止まる(関門・フックを変えない、--no-verify を使わない)。
- 台本・試験・文書を直さない。読みや判断を書かない。

## 報告(日本語)

- 着手前の表(CLAUDE.md §0.1)
- コマンド・戻り値・所要時間・ログの末尾 20 行
- TABLES.json の同じかの結果
- 事象ごとの行のファイルの大きさと行数
- コミットの番号
