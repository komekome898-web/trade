# 作り終えた後の批評家 1 回目 — 読み口の境の口 `--cut` と測定のジョブの手順 5〜7(L-903・L-905)

- 対象: コミット 315d27dd(`scripts/analysis/diag_tables.py`・`tests/research/test_diag_tables.py`)と c4e584a1(`scripts/simple/main_jobs.py`・`scripts/simple/receive_main.py`・`.claude/skills/delegated-study/SKILL.md`)
- 批評家: Agent の道具(general-purpose、下位モデル)、裏で。リードが直接書いた直し(L-905「**yes**」)の後の 1 回
- 以下は批評家の出力の逐語(受け渡しの字下げ 2 字だけを外した)。応答は末尾の表。

## 逐語

批評家の報告(読みと検算だけ。ファイルは書き換えていない。作業は /tmp/claude-0/.../scratchpad/ の中だけ)。

## 問 0 [問題なし]。ただし下の [直す] 3 件が付く
- 境の統一: 答えている。`scripts/analysis/diag_tables.py:270-293` の d1 は `h = sum(1 for d in days if d < cut)` で、渡した日で前半・後半を分ける。main 側は `:518`(口)と `:527`(`d1(daily, a.cut)`)。手順 6(`scripts/simple/main_jobs.py`)は全部の本に同じ `--cut {CUT}` を渡す。
- 次回の測定から委任できる: できる。`.claude/skills/delegated-study/SKILL.md` に【取引の行と標準の表】の節が入っている。手順 5〜7 は 1 本の中で閉じていて、基準の本が要る D7 だけをセッションから外している。
- 代わりの量や近似: 無い。文書の「限界」の記述も無い。
- 補足: CUT は `main_jobs.py` の定数で、手で計算して書き込んだ値。計算し直すと正しい。`date(2015,12,1)+timedelta(days=1469)` が 2019-12-09 で、基準の期間は 2,939 日で 2939//2=1469。次回の測定では、人が定数を書き換える必要がある(問 6 の [聞く] を参照)。

## 問 1 [問題なし]。端の扱いに [直す] と [聞く] が 1 件ずつ付く
- 向き: 同じ。`docs/RESEARCH/matilda_main/compare_family.py:25` は `exit_t[:10] < CUT` が前半、`>= CUT` が後半。d1 は `d < cut` が前半で、同じ向き。
- 数値の突き合わせ(打ったコマンド): foot_5 で `sum(pnl_bp for rows if exit_t[:10]<"2019-12-09")` が 11364.703850000084。`daily_series` の `d<cut` の和は 11364.703850000007。一致した(丸めの差だけ)。
- `--cut 2019-12-09` の実出力(foot_5): 前半は 2015-12-02〜2019-12-08 の 1468 日、後半は 2019-12-09〜2023-12-17 の 1470 日。見出しに「後半の最初の日 2019-12-09」が出る。
- 端の日(foot_5、期間は 2015-12-02〜2023-12-17):
  - cut = 最初の日(2015-12-02)は rc=1 で「期間の中に無い」と止まる。
  - cut = 期間の外(2023-12-18、2015-11-01)も rc=1 で止まる。
  - cut = 最初の日の翌日(2015-12-03)は rc=0 で、前半が 1 日(CI は「—」)。
  - cut = 最後の日(2023-12-17)は rc=0 で、後半が 1 日(CI は「—」)。
  - 日付の形が違う `2019/02/01` は、試験 `test_cut_printed_in_table` が ValueError で止まることを見ている。
- [直す] `--cut 20191209` と `--cut 2019-W50-1` が検査を通り、境が静かにずれる。
  - 原因: `diag_tables.py:523-524` の `date.fromisoformat` が、Python 3.11 では `20191209` と `2019-W50-1` も受け付ける。一方 d1 は文字列の `d < cut` で比べる。
  - 実出力: どちらも rc=0 で、後半の最初の日が 2020-01-01 になった(前半は 2015-12-02〜2019-12-31)。
  - 直し方: main で `a.cut = date.fromisoformat(a.cut).isoformat()` に正規化するか、`len(a.cut)==10` を要求する。試験は `20191209` が止まることを足す(今の試験は通る)。
- [聞く] 前半・後半のどちらかが 1 日でも止まらない(上の 2015-12-03 と 2023-12-17)。docstring は「cut の前と後の両方に日が無ければ止める」で、実装はその通りで矛盾は無い。ただし 1 日の半分は CI が出ない。最小日数で止めるか、今のまま表に「—」を出すかを聞きたい。
- 補足: 出力の cut は `days[h]`(実在する日)で、渡した日そのものではない。trades 系では暦の全日が並ぶので同じ。card 系(`daily.csv` に欠けの日がある)で欠けの日を渡すと、見出しの日が渡した日とずれる。受け取りの文字列検めを card 系に使うなら注意が要る(今回の対象外)。

## 問 2 [問題なし]
- 打ったコマンド: 直す前の版を `git show HEAD:scripts/analysis/diag_tables.py` で取り出し、同じ引数(`--valid-min 200`、`--cut` 無し)で、新旧を foot_5・base・alert_x2 で走らせて `diff` した。
- 結果: 3 本とも差は見出しの 1 行(31 行目)だけで、表の値は同じ。新しい見出しは「…決めた分け方。後半の最初の日 2019-12-10」(foot_5)・「…2019-12-09」(base、alert_x2)。
- json は新しい鍵 `cut`・`cut_source` が足されるだけ。`diag_tables.json` を読む台本は repo に無い(grep で確認)。

## 問 3 [問題なし]。ただし [直す] と [聞く] が 1 件ずつ付く
- 引数の突き合わせ(`PYTHONPATH=src python3 scripts/simple/main_jobs.py` を出して確認):
  - 手順 5: `simple_trades.py --run --out --alert-min`。引数名は `scripts/analysis/simple_trades.py:48-50` と一致する。
  - 手順 6: `diag_tables.py --run --out --valid-min --cut`。一致する。
  - 手順 7: `diag_paths.py --run --out`。`diag_paths.py:211-213` と一致する(`--blocked-from` は任意)。
- 列の出し方: alert は `float({**BASE_PARAMS, **MAIN_BASE, **over}["alert_count"])`、valid は 2×alert。`src/bot/strategy/matilda_simple.py:465,468` で alert_count は分の単位なので、foot_5 は alert 100・valid 200 になる。これは `batch_tables.sh` の `2*alert_count` と同じ。
- 並行のセッションで打てない手順: 無い。手順 5〜7 は自分の本の置き場だけを読む。`diag_paths` が読む 1 分足は `common.load_bars` の既定(2023-12-18 より後は読まない)。D7 だけを外してある。
- [聞く] foot_5 のコミット済みの `trades.csv.gz` は、手順 5 の alert(100)では再現しない。
  - 実測: foot_5 を `--alert-min 100` で作り直して比べると、`late_levels` が 3,384 行で違う(コミット済みは late_levels>0 が 3,403 行、作り直しは 52 行)。
  - 実測: `--alert-min 20`(既定値)で作り直すとバイト単位で一致する。つまり今の foot_5 は既定の 20 で作られている。
  - alert_count が分の単位であることは `src/bot/strategy/matilda_simple.py:465,468` で確認した。なので 100 が正しく、既存の foot_5 の `late_levels` が古い。
  - 他の本(alert_x1・x2、count_20・80)は本ごとに分布が違い、本に合った値で作られているように見える(再作成はしていない。未確認)。
  - `late_levels` を使う表があるかは未確認(`scripts/analysis/*.py` の grep では `simple_trades.py` 自身にしか出ない)。foot_5 の取引の行を作り直すかどうかを聞きたい。
- [直す] 文書の古い記述。`main_jobs.py` の docstring の「手順 6 の `--cut` は diag_tables.py に足す口(…足し終えるまで手順 6 は打てない)」と、`receive_main.py` の docstring の「`--cut` の口を足した後の形」は、口を足した今は事実と合わない。

## 問 4 [直す]
作り変えた表を `scratchpad/rm/` に置いて、`receive_main.py --tables foot` で試した。

| 作り変え | 結果 |
|---|---|
| 表が無い | 「表の欠け」で違う(正しく止まる) |
| `--cut` 無し(旧版の表、境 2019-12-10) | 「境 違う」で違う(正しく止まる) |
| `--cut 2019-12-10` | 「境 違う」で違う(正しく止まる) |
| `--cut 2019-12-09` | OK |
| 取引の行の summary.json の `check.closed_trades` を 1 減らした | 「閉じた取引 89388 89387」で違う(正しく止まる) |

- 穴 1: `trades.csv.gz` の中身の行数を数えていない。`summary.json` の数字を 89388 のまま、`trades.csv.gz` の末尾 1,000 行を削ってから表を作り直しても「表 OK … 違う・欠け 0」になった。取引の行の数が違う表は、summary.json を直さない限り「違う」にならない。`trades.csv.gz` の行数(閉じた取引の数)を数えて `closed_trades` と比べる検めを足す。
- 穴 2: `diag_paths.md` は存在しか見ていない(`touch` した空ファイルで OK になった)。大きさ 0 を弾くか、中に D4 の見出しがあるかを見る。
- 補足: 境の検めは見出しの「後半の最初の日 <CUT>」の部分一致。base は日数の真ん中も 2019-12-09 なので、`--cut` 無しで作った表でも通る(値は同じなので害は無い)。`cut_source` まで見れば厳密になる。
- 補足: 上の出力の rc=0 は `| cut` の戻り値で、スクリプト本体は「違う」があるとき `sys.exit(1)`(コード読みのみ)。

## 問 5 [問題なし]
- `grep -rn "d1(" scripts tests --include=*.py`(封印の置き場は除く)で、`diag_tables.d1` を呼ぶのは `diag_tables.py:527` と `tests/research/test_diag_tables.py` だけ。他の台本に呼び出しは無い。位置引数の 2 番目に `cut` を足しただけで、既存の呼び出しは壊れない。
- `diag_paths.py`・`c9_halves.py`・`card_trades.py` は `diag_tables` から `mean_ci`・`diff_ci`・`group_ratio_ci` を import するだけで、d1 を使わない。
- 試験 `PYTHONPATH=src python -m pytest tests/research/test_diag_tables.py` は 13 件通った。tests/research 全体と tests/simple の通しは 2 分を超えて、結果を取れていない(未確認)。
- [聞く] `--cut` を渡さない既存の台本が残っている。`docs/RESEARCH/matilda_main/batch_tables.sh` は `--cut` 無しで diag_tables を回す(本ごとに境が 12-09/10/11 にずれる元のまま)。`half_diff.py` は `h = len(days)//2` で、「diag_tables.d1 と同じ」と書いてある。既存の 32 本の表を作り直すか、これらの台本に `--cut` を足すか、次回からだけ使うかを聞きたい。今回の依頼は「次回の測定から」なので、必須ではないと判断した。

## 印ごとの件数
[止める] 0 件 / [直す] 3 件(`--cut 20191209`・`2019-W50-1` が静かにずれる、`receive_main.py --tables` が取引の行の中身と `diag_paths.md` の中身を見ない、docstring の古い記述 2 か所) / [聞く] 3 件(foot_5 の取引の行が alert 20 で作られている、1 日の前半・後半を止めるか、既存の表と台本の `--cut`) / [問題なし] 問 0・1(向きと端の止まり方)・2・3(引数の突き合わせ)・5 の 5 項目。

## 応答

| # | 印 | 応答 |
|---|---|---|
| 問 1 の直す | 直す | 直した。`--cut` は `YYYY-MM-DD` の 10 字で、`date.fromisoformat(x).isoformat() == x` のときだけ受ける(`20191209`・`2019-W50-1` は止まる)。試験を足した |
| 問 1 の聞く(1 日の半分) | 聞く | 今のまま(止めない)。最小の日数を置くと根拠のない値になる(A-12)。1 日の半分は区間が「—」と表に出るので読み手に見える。リードが決めた |
| 問 3 の聞く(foot_5 の late_levels) | 聞く | 作り直さない。`late_levels` は `docs/ANALYSIS/` のどの文書にも出てこない(grep で 0 件。手元の表では D0 の列の一覧に名前が出るだけ)ので、読みに使っていない。foot_5 の取引の行は git に入っていない(手元だけ)。次回の測定は手順 5 で本ごとの alert を渡すので同じことは起きない |
| 問 3 の直す(docstring) | 直す | 直した。main_jobs.py と receive_main.py の「足し終えるまで打てない」「足した後の形」を今の事実に合わせた |
| 問 4 の直す | 直す | 直した。`--tables` は (1) `trades.csv.gz` の行数を数えて走らせの閉じた取引の数と比べる (2) `diag_paths.md` に「## D4 取引の一生」の見出しがあるかを見る (3) 境は `diag_tables.json` の `cut` が CUT で `cut_source` が「渡した日(--cut)」かを見る、にした。作り変えた表で試した(結果は下) |
| 問 5 の聞く(既存の表と台本) | 聞く | 次回からだけ使う。オーナーの逐語は「次回の測定から」(L-903)で、分析は区切り中(L-896)。段 1 の 32 本の表と `batch_tables.sh`・`half_diff.py` は作り直さない。済んだ文書で境が要る所は、両方の境の数を並べてある(foot の `foot_boundary.out` ほか) |

## 直しの後の確かめ(リード、作り変えた表は scratchpad の中だけ)

`receive_main.py --tables foot`(置き場を scratchpad に向けて回した):

| 作り変え | 出力 | 終了コード |
|---|---|---|
| そのまま(`--cut 2019-12-09`) | `表 OK 閉じた取引 89388 89388 行 89388 境 2019-12-09 D4 あり` | 0 |
| `trades.csv.gz` の末尾 1,000 行を削った | `表 違う … 行 88388` | 1 |
| `diag_paths.md` を空にした | `表 違う … D4 無い` | 1 |
| `--cut` 無しで作った表(foot_5、真ん中は 12-10) | `表 違う … 境 違う` | 1 |
| `--cut` 無しで作った表(base、真ん中も 12-09) | `表 違う … 境 違う` | 1 |

`diag_tables.py --cut 20191209` と `--cut 2019-W50-1` は「YYYY-MM-DD の形でない」で終了コード 1。`tests/research/test_diag_tables.py` は通った。
この直しは 2 回目の批評に掛けていない。
