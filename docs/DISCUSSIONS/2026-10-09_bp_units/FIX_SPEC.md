# bp の直しの仕様(L-920)

オーナーの指示(逐語、L-920): 「**たまたま見つかったやつも含めてわかってる修正が必要なもの全部直してください 方針はbpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること**」
書いた人: リード。2026-10-09 20:4x JST。状態: 仕様の書き出し(書き換えはオーナーの 2 つの答えの後。`OWNER_STATUS.md` の「判断が要る項目」)。

## 0. 決まり(この直しの全部に当てる)

- **bp = 値動き率 だけ**: 同じものの値段が時間とともに動いた率 × 10,000(`(後の値段 ÷ 前の値段 − 1) × 1e4`、向きを掛けたものを含む)。名前に `bp`・`bps` を含む変数・列・鍵・表の見出し・文書の語は、これ以外の量に使わない。
- 損益は **円**(`pnl_jpy`)で持ち、円で計算し、円で出す。口座に対する率が要るときは %(`損益 ÷ 証拠金 × 100`)と書き、bp と呼ばない。
- 手数料率・損益の率・建玉で重みを付けた損益は bp と呼ばない(% か円、または `_rate` などの別の名前)。
- 同じ時刻の 2 つの値段の差の率(スプレッド・ベーシス・約定の値段のずれ)を bp に入れるかは、オーナーの答え待ち(判断が要る項目 1)。
- 古い意味の `pnl_bp` を受け取る口は、黙って受けずに止める(止める文で、何が来たか・何を渡せばよいかを言う)。

## 1. 計算の仕組み(段 1〜3)

| ファイル | 今 | 直した後 |
|---|---|---|
| `scripts/analysis/simple_trades.py` | 列 `pnl_bp`(:83)、summary の `sum_bp` | `pnl_bp` 列と `sum_bp` を出さない。円の列 `pnl_jpy` だけ。docstring の列の説明も直す |
| `scripts/analysis/diag_tables.py` | `pnl_bp` を読み(:68・80・92)、全部 bp で計算し「bp」と出す | `trades.csv.gz` の `pnl_jpy` を読み、全部円で計算し「円」と出す(`円/日`・`円/取引`)。`daily.csv`(カードの率)・`trades.json.gz`(各台本の定義の率)・`pnl_jpy` の無い `trades.csv.gz` は止める。内部の鍵の名前も `pnl_jpy` に |
| 同 D7(:365-) | 2 本の期間の日の共通部分だけで差を取る(基準だけの日が落ちる) | 2 本の期間の日の和集合で、取引の無い日を 0 円として差を取る(`docs/RESEARCH/matilda_main/d7_fullperiod.py` と同じ値になることを試験で確かめる) |
| `scripts/analysis/diag_paths.py` | D4 の群の「損益の和」が `pnl_bp`(:98・146-154)、値動きは「bp」とだけ | 損益の和は `pnl_jpy` の円。値動きは「値動き率(bp)」と書く。群の名前に「1 段目の値段に対する」を入れる(例「1 段目の値段に対する MFE > 0 で負けた」)。出の後・合図の後も「値動き率(bp)」 |
| `docs/RESEARCH/matilda_main/fam_tables.py`・`half_diff.py`・`both_halves.py`・`same_bar_daily.py`・`foot/foot_boundary.py` | 読み口の bp で計算し表示で × 20 | 円のまま計算して出す(× 20 を無くす)。値動きの列は「値動き率(bp)」 |
| `docs/RESEARCH/matilda_main/*/ledger_rows_*.py` | 台帳の文に bp(口座)・move_bp | 文書の直し(段 5)と同じ書き方に |
| `.claude/skills/analysis-lens/SKILL.md` | 「損益はすべて取引の向きの符号を付けた値(pnl_bp)」(:95)、D0 の表の `pnl_bp`(:126・137-139) | 損益は円(`pnl_jpy`)、値動きは値動き率(bp)と書き分ける。D0 の表の列も直す。直した後、分析の文書 16 本の写しを `scripts/analysis/diag_skeleton.py --refresh` で入れ替える |
| `.claude/skills/delegated-study/SKILL.md` §3【取引の行と標準の表】、`scripts/simple/main_jobs.py`、`receive_main.py` | `pnl_bp` の列を前提にした文・検め(あれば) | `pnl_jpy` だけを前提に |
| 試験 `tests/research/test_diag_tables.py`・`test_diag_paths.py` ほか | `pnl_bp` の行で作った場面 | 円の場面に。足す試験: (1) 読み口が円で出し、出力の文字に値動き率の文脈の外の「bp」が無い (2) `pnl_bp` だけの入力・`daily.csv`・`trades.json.gz` で止まる (3) D7 が和集合の日で 0 を入れる(片方だけの日がある場面で、共通部分だけの計算と値が違う) (4) D4 の和が円 |
| 調べの記録の台本(`display_x20_*.py`・`unit_roundtrip_check.py`・`move_bp_*.py`・`bare_bp.py`・`calc_path_check.py`・`d4_*.py`) | 口座の bp を調べるために書いたもの | 書き換えない。頭に「L-920 で口座の bp は廃止した。この台本は廃止前の列を読む調べの記録」と書く(判断が要る項目にはしていないが、着手前の表で「該当語なし」と出した) |

## 2. 出力の作り直し(段 4)

`backtest_runs_shared/matilda_main_trades/<本>/`(32 本)を `simple_trades.py` で作り直し → `diag_tables.py`(32 本、`--vs base`・`--cut 2019-12-09` は今と同じ引数)→ `diag_paths.py`(32 本と `--blocked-from` の 3 本)→ `fam_tables.py`(10 族)→ 族の台本の `.out`。引数は `docs/RESEARCH/matilda_main/batch_tables.sh` と各文書に書いたコマンドのまま。作り直した後、円の値が前の出力の bp × 20 と(D7 の 6 本を除き)浮動小数の誤差の内で合うことを機械で確かめる。

## 3. 文書の直し(段 5)

対象: `docs/ANAL` `YSIS/2026-10-09_matilda_main_*.md`(15 本)・`2026-10-08_simple_road_check.md`、`docs/RESEARCH/FINDINGS_LEDGER.md` の K-301〜K-364、`docs/DISCUSSIONS/2026-10-08_matilda_main/STAGE1_FAMILY_TABLES.md`。
- 口座の bp の数は全部、作り直した出力の円の値(文書の桁に丸める)に置き換える。手で × 20 した数(型 E の 149 個)、丸めた円どうしの足し引き(型 F の 31 個)も出力の値か、出力から機械で計算した値にする。
- 「1 bp = 20 円」「pnl_bp は口座に対する bp」の定義の文、「bp/日 × 20 = 円」の出所の書き方を消し、出所は円の出力を指す。
- 値動きは「値動き率(bp)」と書く(`move_bp` の語は使わない)。
- K-317・K-357 の文を円で書き直す。段数の族の「2016 年が最も良い」を表に合わせて直す。
- 「一度は有利に動いてから負けた」(K-322・K-330 の見出し、`count.md`・`foot.md` の読み)は「1 段目の値段から見て」と書き、持ち高全体の含みで数えた値(`d4_position_mfe.out`)を並べる。
- 読み口の D7 の直しで値が変わる 6 本の D7 の数を直す。
- 終わりの検め(機械): 対象の文書で、「bp」の字が「値動き率」の文脈(同じ文に 値動き・MFE・MAE・合図の後・出の後・値動き率)の外に出る数が 0。円の数が作り直した出力と合う(`display_x20_suspects.py` と同じ突き合わせを円の出力で回す)。
- 直した文書に関門 ② を掛け直す(CLAUDE.md §5 ②)。

## 4. 動いている経路(段 7)と流れていない台本・試験(段 8)

一覧は `audit_8_repo.md` 表 1〜3 と `audit_9_repo_rest.md`。種類 ③(建玉で重みを付けた損益の率)・④(手数料率ほか)を名前と単位から外す。段 7 で直すもの: `scripts/paper_on1.py:115-117`(対数 → 型の定義どおりの単純な比)、`src/bot/bt/report/metrics.py:80`(手数料を引いた率を bp と呼ばない)、`src/bot/monitoring/backtest_chart.py:356・379`(2 つの定義を同じ `bp` にしない)、`backtest_cards.py`・`aggregate.py`・`etf_auction_executor.py`・`research_clock_burst.py`・`board.py`・`data_quality.py`・`record_funding_basis.py` ほか。データの列の名前を変えるものは、読む側と一緒に変え、今ある記録のファイルを読めなくしない。範囲は判断が要る項目 1 の答えで決まる。
