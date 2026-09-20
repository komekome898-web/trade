# 反証者レビュー7(段2 = 後半 5,000 件の一度きりの測定に入る前、2026-09-20)

対象: `SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §6・§7(特に §7.4 logistic、§7.5 段2 手順と
「較正の良い方」の決め方、段1 の結果を受けた決定 = 段2 は Jev V1)、`V4_STAGE1_REPORT_2026-09-20.md`、
`scripts/o3c_signal_logit.py`・`scripts/o3c_jev_state.py`・`scripts/jev/client.py`、
`config/o3c_signal_logit_first.yaml`・`config/o3c_signal_logit_chain.yaml`・`config/o3c_jev_state_bands.yaml`、
`backtest_data/o3c_signal_continue_20260920/jev/selection_manifest.json`。

**方法**: 静的読解 + `backtest_data/o3c_signal_materials_20260920/rows_materials.csv.gz`
(材料の表、前半・後半とも列は既にリポジトリにある)からの独立再計算。**Jev は 1 回も呼んでいない。**
`paper_logs/` は開いていない。本書に書く数値は前半の材料の表の数値と件数、および `config/` に既に
コミットされている logistic の係数・切り値(§7.4 の成果物としてリポジトリに置く設計)だけで、
`data/jev/` 配下の確率・的中・較正の数値は書いていない。

---

## 致命

### C1. `cand_8`(先の建玉)の五分位ランクが「連鎖の中」場面で完全に退化している

根拠: `scripts/o3c_signal_logit.py` の `quintile_rank()`(69–80 行)は `np.quantile` で
切り値 4 本を前半の値そのもの(0 を含む)から作り、`np.searchsorted(cuts, values, side="right")`
で帯を決める。`cand_8`(=「この先 5/10/20bp 以内の建玉の量」、決定表 §7.1 で「連鎖の中」に
「先の建玉(多い側の五分位だけ止まる側)」として残された材料)は、前半「連鎖の中」12,769 件のうち
**84.1% が厳密に 0**。5 分位の切り値 4 本(q=0.2,0.4,0.6,0.8)が全部 0 になるため、`searchsorted`
は 0 の値も正の値も区別なく最後の帯(rank 0.9)に入れる。再計算(下記コマンド)で確認した結果:

```
chain  cand_8     fracmissing=0.013 fraczero=0.841 cuts=[0.0, 0.0, 0.0, 0.0] bandcounts={-1: 169, 4: 12600}
```

前半「連鎖の中」の有限値 12,600 件が**全件**同じ帯(rank 0.9)に入り、欠測(169 件、rank 0.5)以外に
分散が無い。`config/o3c_signal_logit_chain.yaml` の `cand_8` の係数(-0.421、11 本中 4 番目に絶対値が
大きい)は、実質「欠測か否か」だけの定数項に等しく働いており、材料 8 が本来持つはずの「先の建玉が
多いか少ないか」という情報を一切使っていない。

「1 件目」場面でも同じ材料は 2 つの帯(0.7 に 7,190 件、0.9 に 1,798 件)にしか分布せず、5 段階のうち
3 段階(0.1/0.3/0.5)が空である:

```
first  cand_8     fracmissing=0.009 fraczero=0.613 cuts=[0.0, 0.0, 0.0, 6148.362623000002] bandcounts={-1: 81, 3: 7190, 4: 1879}
```

**これは問い 2(logistic の入力の材料と決定表の対応、順位の付け方が後半で同じ手続きで再現できるか)への
具体的な反例である。** Jev に渡す文(`_sent11`、`oi_ahead_20bp` 帯)は `QUINTILE_SOURCES` の
`("mat8_amt_20bp", "positive_covered")`(`o3c_jev_state.py` 81 行)で **0/未被覆を除いた正の値だけ**
から五分位を取っており、退化しない(`config/o3c_jev_state_bands.yaml` の `oi_ahead_20bp` は
[3961.6, 8218.3, 14613.2, 25834.6] と単調に増える正常な切り値)。つまり**同じ材料 8 を、Jev への
文章化と logistic への数値化で違う手続きにかけており**、logistic 側だけが 0 の集中に対して壊れている。

**なぜ致命か**: §6.3 は「code の規則…を Jev が上回らなければ判断に置く意味は無い」とし、§7.4 の
logistic は §7.5 の段2 で Jev と較正を比べる「code の比較相手」そのものである。比較相手の入力が
決定表で名指しされた材料の 1 つで実質的に定数化していれば、その材料の軸で Jev が(壊れていない
文章表現のおかげで)相対的に有利に見える可能性があり、「較正の良い方」の判定がロジックの巧拙ではなく
実装の欠陥で傾く。これは段2 に入る前に直すべき実装のバグであり、後半に触れてから気づいても
判定を一度しかできない規則(§4)の下ではやり直しが効かない。

### C2. 段1 報告「(5) 設計に無い判断」の 3 項目のうち 2 項目が、実際には段2 に影響する

根拠: `V4_STAGE1_REPORT_2026-09-20.md` §7.5 の末尾は「委任先が推測で埋めた 2 点(連鎖の中で
A3・A9 を『外す』側に置いた / N2 の定義)は V4 の中身で、段2 では V4 を使わないので後半の測定に
影響しない」と書く。しかし:

- **A3・A9 の扱い**: `scripts/o3c_signal_logit.py` 62–63 行の `FEATURES_CHAIN` は
  `["cand_F5", "cand_1", "cand_F3", "cand_14", "cand_A6", "cand_C4", "cand_15", "cand_11",
  "cand_C3", "cand_8", "cand_2"]` で、`cand_A3`・`cand_A9` を含まない。この材料選択は
  決定表(§7.1)の「連鎖の中 11 本」という**同じ解釈**(A3・A9 を「外す」側に数える)に基づいて
  作られており、V4 の文章構成だけでなく **§7.4 の logistic(= 段2 で使う code の比較相手)にも
  そのまま及んでいる**。報告の「段2 に影響しない」という整理は V4 の文章側しか見ておらず、
  同じ判断が logistic の特徴量選択にも使われている事実を見落としている。
- **N2 の定義**: 報告 (5)-5 は「設計は…数式を与えていない」と自認したうえで独自の線形位置
  (0〜1)を定義している。この N2 は V4 の文章(`_sentN2`)だけでなく、`FEATURES_FIRST` の
  10 本目(`cand_N2`)として **`config/o3c_signal_logit_first.yaml` の係数(-0.0536)に
  焼き込まれ、段2 でそのまま使われる**。A3・A9 と違って「V4 限定」ではないので、報告の
  安全宣言はそもそも N2 に触れていない。

**なぜ致命か**: 段2 は一度きりの測定であり(§4「反証者レビューは境目を置いた後、較正の前に」)、
比較相手の logistic の中身(どの材料をどう解釈して選んだか)に未検証の判断が 2 つ埋め込まれたまま
後半に進むと、後から「実は logistic の方が本来ならもっと強い/弱いはずだった」という反証ができない。
段2 に進む前に、決定表の A3・A9 の扱いと N2 の数式をオーナー/設計側で確定させる(または少なくとも
「logistic にも効く」と明記して感度を残す)必要がある。

### C3. 前半で固定した五分位の切り値を後半に適用するコードが存在しない

根拠: `scripts/o3c_signal_logit.py` を全文(299 行)読んだ限り、量子化(五分位ランク化)の経路は
`build_matrix(df, features)`(83–94 行)の 1 つしか無く、これは**渡された `df` 自身の分布から**
`np.quantile` で切り値を作る(`quintile_rank` を各列に対して新規に呼ぶ)。「前半だけに絞ってから
当てはめる」ための `fit_beta_front_half`(151–158 行)も、内部で `build_matrix(df_fh, features)` を
呼ぶだけで、**切り値を受け取って再利用する引数が無い**。

```
$ grep -n "後半\|second_half\|apply_frozen\|predict_scene\|score_scene\|def predict\b" scripts/o3c_signal_logit.py
122:def predict(X: np.ndarray, beta: np.ndarray) -> np.ndarray:
149:# 3. 前半だけに絞ってから当てはめる(後半の値を変えても同じになることの検査に使う)
```

`config/o3c_signal_logit_{first,chain}.yaml` には「五分位の切り値」がちゃんと保存されているので、
**データとしては前半だけから固定されている**(この点は正しい)。しかし、これを後半 5,000 件の
生の材料値に適用してスコアを出す関数が今のところ無い。もし段2 の実装が(既存の唯一の経路である)
`build_matrix`/`run_scene` を後半データにそのまま流用すれば、**後半の分布から新しい切り値を
計算し直してしまい**、config に固定したはずの切り値を無視する。これは §7.5「後半では読むだけ」
という設計の文言と矛盾する実装になる。

既存のテスト `test_logit_beta_determined_by_front_half_only`(`tests/test_o3c_jev_state.py`
586–598 行)は**係数**が前半だけから決まることしか検査しておらず、**切り値**を後半データに
正しく再利用できるかは検査していない。さらにこのテストの合成データ(`_synthetic_logit_df`、
560–570 行)は `rng.normal()` の連続値で作られており、`cand_8` のような点質量(0 が 6〜8 割)を
持つ分布は 1 つも無い ── つまり C1 の退化も、この後半適用の欠落も、**今の試験群には検出できない
形で残っている**。

**なぜ致命か**: これは「判定区間を開ける前に固定されているべきもの」(問い 1)が、コード上は
まだ「開ける」ための道具そのものが安全に作られていないという意味で、段2 着手の前提条件が
満たされていない。

---

## 直すべき

### D1. `cand_R1`(1 件目場面)も同種の(より軽い)退化がある

```
first  cand_R1    fracmissing=0.000 fraczero=0.475 cuts=[-0.0, 0.0, 0.14279120000000015, 1.8263140000000009] bandcounts={2: 5441, 3: 1814, 4: 1814}
```

47.5% が厳密に 0 で、帯 0・1(rank 0.1/0.3)が空になり、0 の 47.5% がすべて帯 2(rank 0.5)に
吸収される。C1 ほど壊滅的ではない(帯 3・4 は正常に分かれている)が、同じ `searchsorted` の
仕組みが点質量に弱いことを示す 2 例目であり、他の材料(将来足すものを含む)にも同じ危険がある
ことの確認として書く。C1 の修正(点質量を持つ材料の量子化方式の見直し ── 例えばタイの扱いを
`scipy.stats.rankdata` の平均順位にする、あるいは「0 か否か」を別の 2 値の文にしてから残りの
正の値だけを五分位にする、など)を検討する際、R1 も同じ枠で直すべき。

### D2. §7.5「較正の良い方」の判定手続きがまだコード化されておらず、帯の境界・少数帯の扱いが
    設計文書の文言だけでは一意に決まらない

```
$ grep -rn "0.05刻み\|較正の良い方\|calib_bin\|bin_edges\|0\.05 刻み" scripts/ config/ docs/PHASE2/O3C/SIGNAL/ | grep -v "\.md:"
scripts/o3c_jev_state.py:1054:    それぞれの V1・V4 の順位分離(ブートストラップ SE つき)・0.05 刻みの分布・
scripts/o3c_jev_state.py:1104:                     "0.05 刻みの分布(件数): " + ", ".join(
```

前半の下見表(`build_v4_preview_tables`)には `bins = np.arange(0, 1.0001, 0.05)` という
実装済みの慣行があるが、これは確率の**分布**(ヒストグラム)であって、§7.5 が求める
「|実際の割合 − 帯の中央| の件数重み平均」という**較正**の指標を作るコードはまだどこにも無い。
設計文書 §7.5 は次を明記していない:

- 帯の起点(`[0,0.05)` から始めるか、`[-0.025,0.025)` のように中央を軸に取るか)。
- 「件数の少ない帯」の下限(件数 0 の帯、あるいは件数 1〜数件の帯を指標の計算にどう含める/除くか)。
  件数重み平均なので少数帯の寄与は自動的に小さくはなるが、**除外するかどうか**自体が後半を見てから
  決められる余地として残っている。

段2 のコードを書く前に、この 2 点を設計文書(または委任文)に数式・定数として書き下ろし、
「後半を見てから動かせない」形にしてから着手すべき(§7.5 自身が「決め方(事前)」と明言している
以上、事前の定義が曖昧なままでは事前登録の体を成さない)。

### D3. 後半 5,000 件の層化選定が「1 件目」対「連鎖の中」の自然な比率を歪めている

`backtest_data/o3c_signal_continue_20260920/jev/selection_manifest.json` は側 × 材料1(cand_1)の
3 群(`0` / `1-2` / `3+`)をほぼ均等に割り付けている(層ごとの内訳、6 層 × 約 833〜834 件)。
再計算した後半母集団(30,162 件、`rows_materials.csv.gz` の `half=="後半"`)の自然な内訳:

```
後半総数 30162
cand_1==0 (1件目) 12528 0.41535707181221404
cand_1 in 1-2      9665 0.32043631058948346
cand_1>=3           7969 0.2642066175983025
連鎖の中(1+)       17634 0.584642928187786
```

選定 5,000 件の内訳(層ごとの内訳の合計):

```
group counts Counter({'0': 1667, '1-2': 1667, '3+': 1666})
```

自然比率は「1 件目 : 連鎖の中」= 41.5% : 58.5%(前半の比率 9,069:12,769 ≈ 41.5%:58.5% と
ほぼ同じ、内的整合はある)だが、選定後は 33.3% : 66.7% になり、「連鎖の中」を約 8 ポイント
過大に選んでいる。さらに「連鎖の中」の内部でも自然比率は 1-2 件目 : 3 件目以降 ≈ 54.8% : 45.2%
なのに対し、選定後はほぼ 50.0% : 50.0% で、深い連鎖(3+)を相対的に多く選んでいる。

§7.5 は「1 件目 / 連鎖の中 それぞれの…較正」と場面ごとに較正曲線を分けるので、この歪みが
較正曲線そのものを直接ゆがめるわけではない。しかし「連鎖の中」バケツの中身(浅い連鎖と深い連鎖の
混合比)が自然populationと異なることは、結果を「後半の印刷全体に対する性能」として読むときに
無視できない前提であり、報告(段2 の結果を書くとき)に明記すべきである。この選定自体は
清算の向き・cand_1(ts だけで決まる量)という結果ラベルに依存しない量での層化であり、
「一度きり」規則そのものには抵触しない。

### D4. `StateBuilder` が帯を毎回再計算しており、frozen yaml と一致することを保証する仕組みが無い

`scripts/o3c_jev_state.py` 544–564 行: `StateBuilder.__init__` は `bands` 引数を省略すると
`compute_bands(self.rows_fh)` を**その場で**再計算する(`config/o3c_jev_state_bands.yaml` を
読みには行かない)。現時点では `rows_materials.csv.gz` の前半部分が変わっていないので
再計算値と yaml の値は一致する(`o3c_signal_logit_chain.yaml` の `cand_F3` 切り値と
`o3c_jev_state_bands.yaml` の `chain_notional` 切り値が一致することを目視で確認した)。
しかし材料 CSV が将来更新された場合(§5.4–5.5 で実際に材料が 22→24 本に更新されている前例が
ある)、`StateBuilder()` を引数無しで呼ぶだけで静かに違う帯を使うようになり、frozen yaml との
不一致を検出する仕組み(テストや起動時チェック)が無い。段2 の実装では `bands=load_bands_yaml()`
を明示的に渡すか、再計算値と yaml の一致を assert するコードを足すべき。

---

## 示唆

### S1. Jev への提示形式(V1)は、前半データを使った選定を 2 回経ている

1. `SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §6.5: 前半 200 件 × (V1 / V2 / V3) = 600 回の
   呼び出しで V1 を採用(V2・V3 に対して)。
2. `V4_STAGE1_REPORT_2026-09-20.md` (0): 前半 900 件 × (V1 / V4) = 1,800 回の呼び出しで
   V1 を維持(V4 に対して)。

いずれも「前半で選ぶのは許されている」(§4)の範囲内で、規則には反していない。ただし、
段2 で最終的に使う V1 が、実際には**前半のデータを使った 2 回の別々の選定イベント**(合計
2,400 回の Jev 呼び出し、延べ 4 つの候補形式との比較)を経て残った形だという事実が、
どちらの文書にも一箇所にまとめて数えられていない。§4 の材料候補数のような明示的な
カウント表(候補の数 = 多重性に数える、という既存の規律)に倣って、Jev の提示形式についても
「前半での選定回数」を段2 の報告の冒頭に一行でまとめておくと、後で「何回選んだか」を
数え直す必要が無くなる。

### S2. §7 の決定表からロジスティック回帰の入力・V4 の文構成に至る一連の解釈判断に、
    §4 のような統一的な多重性カウントが無い

§5.2–§5.5(材料の選定)には「行 2,583 + 160」「反証者のセル 1,167」「候補の数」という
明示的な多重性のカウントがある一方、§7(決定表 → logistic 入力 → V4 の文 → N1/N2 の追加
判定 → V1/V4 比較)には同種のカウントが無い。C2 で指摘した「決定表の空欄の解釈」のような
判断が、材料選定の候補数カウントの外側で複数回起きている(A3/A9 の扱い、N2 の定義、
先の建玉の代表値を `cand_8` だけにする判断、など)。段2 に進む前に、これらを一覧にして
多重性としてカウントするか、少なくとも「カウントしないと決めた理由」を明記すべき。

---

## 再計算に使ったコマンドと出力(まとめ)

```
$ python3 -c "
import pandas as pd, numpy as np, collections
df = pd.read_csv('backtest_data/o3c_signal_materials_20260920/rows_materials.csv.gz', low_memory=False)
fh = df[df['half']=='前半']
cand1 = pd.to_numeric(fh['cand_1'], errors='coerce')
chain = fh[cand1>0]
first = fh[cand1==0]
print('chain n', len(chain), 'first n', len(first))
for name, sub in [('chain', chain), ('first', first)]:
    v = pd.to_numeric(sub['cand_8'], errors='coerce').to_numpy(float)
    finite = v[np.isfinite(v)]
    cuts = [float(np.quantile(finite,q)) for q in (0.2,0.4,0.6,0.8)]
    band = np.searchsorted(cuts, v, side='right')
    print(name, 'n finite', finite.size, 'frac zero', (finite==0).mean(), 'cuts', cuts,
          'band counts', collections.Counter(band.tolist()))
"
chain n 12769 first n 9069
chain n finite 12600 frac zero 0.841031746031746 cuts [0.0, 0.0, 0.0, 0.0] band counts Counter({4: 12769})
first n finite 8988 frac zero 0.6133733867378727 cuts [0.0, 0.0, 0.0, 6148.362623000002] band counts Counter({3: 7190, 4: 1879})
```

(上のコマンドは欠測行にも `searchsorted` の結果を残したままの版。欠測を `-1` にして
NaN 件数を分けた再実行の出力を「致命 C1」に載せた。両者は band=4/3 の実数値件数で一致する。)

```
$ python3 -c "
import pandas as pd
df = pd.read_csv('backtest_data/o3c_signal_materials_20260920/rows_materials.csv.gz', low_memory=False, usecols=['print_id','half','cand_1'])
bh = df[df['half']=='後半']
cand1 = pd.to_numeric(bh['cand_1'], errors='coerce')
n0 = (cand1==0).sum(); n12 = ((cand1>=1)&(cand1<=2)).sum(); n3p = (cand1>=3).sum(); tot=len(bh)
print('後半総数', tot)
print('cand_1==0 (1件目)', n0, n0/tot)
print('cand_1 in 1-2', n12, n12/tot)
print('cand_1>=3', n3p, n3p/tot)
print('連鎖の中(1+)', tot-n0, (tot-n0)/tot)
"
後半総数 30162
cand_1==0 (1件目) 12528 0.41535707181221404
cand_1 in 1-2 9665 0.32043631058948346
cand_1>=3 7969 0.2642066175983025
連鎖の中(1+) 17634 0.584642928187786
```

```
$ python3 -c "
import json
d = json.load(open('backtest_data/o3c_signal_continue_20260920/jev/selection_manifest.json'))
for row in d['層ごとの内訳']: print(row)
import collections
print('group counts', collections.Counter(p['group'] for p in d['prints']))
"
{'side': 'BUY', '_group': '0', 'n': 833}
{'side': 'BUY', '_group': '1-2', 'n': 833}
{'side': 'BUY', '_group': '3+', 'n': 833}
{'side': 'SELL', '_group': '0', 'n': 834}
{'side': 'SELL', '_group': '1-2', 'n': 834}
{'side': 'SELL', '_group': '3+', 'n': 833}
group counts Counter({'0': 1667, '1-2': 1667, '3+': 1666})
```

```
$ grep -n "後半\|second_half\|apply_frozen\|predict_scene\|score_scene\|def predict\b" scripts/o3c_signal_logit.py
122:def predict(X: np.ndarray, beta: np.ndarray) -> np.ndarray:
149:# 3. 前半だけに絞ってから当てはめる(後半の値を変えても同じになることの検査に使う)

$ grep -rn "0.05刻み\|較正の良い方\|calib_bin\|bin_edges\|0\.05 刻み" scripts/ config/ docs/PHASE2/O3C/SIGNAL/ | grep -v "\.md:"
scripts/o3c_jev_state.py:1054:    それぞれの V1・V4 の順位分離(ブートストラップ SE つき)・0.05 刻みの分布・
scripts/o3c_jev_state.py:1104:                     "0.05 刻みの分布(件数): " + ", ".join(
```

```
$ python3 -c "
import pandas as pd
df = pd.read_csv('backtest_data/o3c_signal_materials_20260920/rows_materials.csv.gz', low_memory=False, nrows=1)
print(df.columns.tolist())
"
['print_id', 'day', 'side', 'half', 'ts_ms', 'bundle_id', 'bundle_pos', 'bundle_pos_single', 'group', 'pos_label',
 'cand_1', 'cand_2', 'cand_3', 'cand_5p', 'cand_6', 'cand_8', 'cand_9', 'cand_10', 'cand_11', 'cand_12', 'cand_13',
 'cand_14', 'cand_15', 'cand_F3', 'cand_F4', 'cand_A3', 'cand_A4', 'cand_A5', 'cand_A6', 'cand_A9', 'cand_C3',
 'cand_C4', 'cand_R1', 'cand_F5', 'cand_A9_count']
```
(`cand_A3`・`cand_A9` の列自体は材料の表に存在するが、`o3c_signal_logit.py` の
`FEATURES_CHAIN`(60–63 行)には含まれていないことを確認した ── C2 の根拠。)

---

## 確認できたこと(壊せなかった箇所)

- 問い 1 のうち、**係数**が前半だけから決まることは `test_logit_beta_determined_by_front_half_only`
  で機械的に検査されており、後半の材料・ラベルを書き換えても前半の係数は変わらない(合成データでの
  検査だが、`fit_beta_front_half` が `half=="前半"` でフィルタしてから `build_matrix` を呼ぶという
  実装そのものは cand_8 の点質量の有無と無関係に成立する)。
- N1・N2 が ts 以後の価格を使わないことは `test_v4_n1_n2_ignore_future_prices_and_p0` /
  `test_n2_position_uses_only_causal_window` で確認されている(p0 を書き換える形の試験を含む)。
- 帯(`config/o3c_jev_state_bands.yaml`)・logistic の切り値・係数(`config/o3c_signal_logit_*.yaml`)は
  いずれも `half=="前半"` の行だけから計算するコード経路になっており、現在の `rows_materials.csv.gz`
  から再計算しても yaml の値と(丸め誤差の範囲で)一致した。
- Jev の問い・criteria(`JEV_QUESTIONS_V1` / `JEV_QUESTIONS_V4_FIRST` / `_CHAIN`)はコード中の
  リテラルな辞書であり、データから計算される値ではないので、後半を見ても変わりようがない。
- `selection_manifest.json` の層化は側・cand_1(ts だけで決まる、結果ラベルに依存しない量)だけを
  使っており、後半の続く/止まるのラベルを覗いた形跡は無い。
