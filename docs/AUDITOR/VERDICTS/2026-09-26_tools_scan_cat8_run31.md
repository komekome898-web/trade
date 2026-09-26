# 検収: 道具サーベイ 区分 8 の 31 回目(2026-09-26、リード)

対象: `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の `## 区分8 — 31 回目の実行(2026-09-26)`(44025 行目から)/ 生ログ `docs/DATA/probes/20260923_tools_8_run31.log`(224,896 バイト)。受け取ったままの形はコミット 7181863。

## 0. 費用と時間

調査班 509,378 トークン・2,177,080 ms(36.3 分)・道具 238 回。

## 1. 受け入れ検査(リードが打ち直した)

- `check_scan_report.py`(31 本): `---- 合計 58 件`(調査班の貼付と一致)
- `check-elements --round 31`: **14 件**(全部「`/tmp` の直下(scratchpad の外)のファイルを使う手」。生ログ 8・38・63・75・100・202・504・526・552・556・566・587・1375・1923 行)。1375 行は scratchpad の道の中の `/tmp/pandas_titles.py` を使う手で、これも当たり。
- `check "" run31.log`: 0 件 / 過去の節から消えた行: 0
- `/root/.m2` 無し、`/root/.gradle` は 2026-03-31 のまま、`/root/.cache/pip` 728M のまま(リードの打ち直し)。

## 2. リードが見つけたこと(監査の前)

1. **生ログに無い `pip` の手が 1 つあり、それが第三者のコードを §6-1 の前に動かした。**証拠(リードの実測):
   - `/tmp/pip-download-aqz_ek8j`(27M、中に pandas の sdist を開いたもの)・`/tmp/pip-unpack-sse80wjj`(`pandas-3.0.6.tar.gz`)・`/tmp/pip-build-env-j24p8q2a`・`/tmp/pip-build-tracker-ie0q6o8k` が 17:13:52 に作られ、build-tracker の最終更新は 17:16:22。
   - scratchpad の `cat8/pipcache/wheels/` の下に、この窓の時刻で、ソースから作った wheel が 18 個ある(`hatchling-1.32.4`・`meson-1.12.1`・`meson_python-0.22.0`・`patchelf-0.19.1.0`・`setuptools-84.0.0`・`scikit_build_core-1.1.0`・`poetry_core-2.5.0`・`flit_core-4.1.0` など)。ソースから wheel を作るのは、その配布物の作りの手順(第三者のコード)を動かすこと。
   - `/usr/lib/python3/dist-packages/setuptools/`・`wheel/` の下に、17:14〜17:15 に新しく作られた `.pyc` が 111 個(作られた時刻 `stat -c %w` で確かめた)。
   - 生ログで 17:13:45 の `pip download --no-deps --no-binary=:none:` の出力は wheel 1 個だけで、ソースから作った跡は無い。17:16:17 の次の手は `curl` で sdist を取り直している。**この間の手は生ログに無い。**報告にも書かれていない。
   - この手は §6-1 の結論(生ログ 484 行、17:17:08)より前。
2. **導入で入った依存(`numpy 2.4.6`・`python-dateutil 2.9.0.post0`・`six 1.17.0`、生ログ 1649〜1668 行)の中身を開いた手が無い。**§6-1 の結論の行(484 行)に並ぶのは pandas だけ。起動文 §2.5「導入・実行で使う配布物の名前と版を全部並べ、その全部について中身を開いた手の行を引く」に反する。
3. `/tmp` の直下に 36 個のファイル・ディレクトリ(上の 4 つの `pip-*` を含む)。
4. **E2 の `印`**: 引いた逐語(`duplicated`「Return boolean Series denoting duplicate rows」、`merge(indicator=True)`)は汎用の表(DataFrame)についてのもので、述語の「時系列・約定・板・足・参照データについて」に届く逐語が無い(24 回目 Prefect・26 回目 Debezium・28 回目 Kafka と同じ当て方)。
5. **E3a の `なし`**: ファイルの表(報告の節の 424 行目から)44 ファイルのうち約 40 ファイルに同じ文「ソフトウェアのメモリ/リソース(ファイル記述子・スレッド)の「漏れ」(leak)の意…」を当てている。当たった行には、メモリ・資源の漏れではないものがある(`web/pandas/about/governance.md:181`「leak into their work with the Project.」、`pandas/tests/io/pytables/test_select.py:105`「extra rows leak through」、`pandas/tests/io/parser/common/test_read_errors.py:58`「leaked a cryptic error」、`pandas/tests/indexes/multi/test_indexing.py:1301`「leak the NaN row」など)。理由の文が当たった行を読んだ結果になっていない。起動文 §2.4「同じ文を何行・何ファイルにも当てた `なし` は受け取られない」。
6. **§4.0「宣伝詐欺の兆候」**: 理由が「X等で…専用に探す検索はこの回では実施していない」で、値は「見当たらない」、印は `推定`。起動文が理由として認めない文(「この回では実施していない」)。
7. **E4・E6 の案 B の記録**: 読んだ範囲は「doc/source 全 216 件の題 + pandas/io・core 直下のファイル名」。起動文 §1 の「関わりうる頁の本文を読む」の頁の道の一覧、§1 の「ディレクトリを要素の語の一覧で機械的に選ぶ(`find <src> -type d` の全部と `grep -i -E` の出力)」が無い(1593 行は `find pandas -maxdepth 1 -type d`)。案 B の条件(読んだ範囲と当たりの行の数が書いてある)を満たすか、リードは「満たさない」と読む。

## 3. 中身の監査(126 回目、owner-auditor)の逐語

(監査の後に書く)

## 4. 処置(リード、監査 126 回目)

(監査の後に書く)

### リードの読みの案(監査に掛ける)

- **この回の実測の値は受け取らない**(2 の 1・2。§6-1 の前に第三者のコードが動き、導入した依存の §6-1 も無い)。`実測` の印の要素は、同じ生ログの中の一次資料の逐語(ソースの docstring を `sed -n` で印字した手)が述語に届くものだけ `一次資料` として受け取る: E1a 印・段 4(`assert_frame_equal`、生ログ 1770〜1811 行)/ E1b 印・段 2(`groupby`・`corr`、1812〜1824 行。29 回目の Kafka の窓集計と同じ当て方)/ E3b 印・段 4(`merge_asof` の backward、1851〜1894 行。述語の例「時点の揃った結合」)/ E5 印・段 2(`random_state`、1895〜1901 行)。
- E2 → `未判別`(2 の 4)。E3a → `未判別`(2 の 5)。E4・E6 → `未判別` のまま、案 B の記録は足りないので 8-034 は「残り」に数える(2 の 7)。
- §4.0 の `実測` のうち導入・実行によるもの(版の実測・導入可否・install 所要秒・pip check・最小実行・実行所要秒・当方データ投入・時刻の扱い・規模の見積・外部送信・登録の要否)は「§6-1 を済ませる前の導入による値」とする。宣伝詐欺の兆候は `未確認`(2 の 6)。
- 片付け(リードが行った): `/tmp` 直下の 36 個を `scratchpad/cat8/run31_tmp/` へ移した。`/usr/lib/python3/dist-packages` の下の新しい `.pyc` 111 個を消した(一覧は `scratchpad/cat8/run31_pyc.txt`。消す前に 111 個とも作られた時刻が 17:14〜17:15 で `.pyc` だけであることを確かめた)。ソースから作った wheel 18 個は scratchpad の `pipcache` に残した(証拠)。
- 32 回目 = 8-034 の残り: §6-1 をやり直す(依存も含め、`--only-binary :all:` で取り、ソースから作らない)、最小実行をやり直す、E2 の対象の逐語、E3a のファイルの表のやり直し、E4・E6 の案 B の記録、宣伝詐欺の兆候の投稿の本文。
