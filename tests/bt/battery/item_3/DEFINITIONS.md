# 項目 3「検証・再現・出力」の場面集 — 定義

場面係が書く(委任文 §3「場面集」「場面集の規則」1〜9)。この文書は `gen_definitions.py` が `i3_scenes.py` から作る。
場面の節は手で直さない(直すなら場面を直して作り直す)。道具の名前は書かない。

## 0. 何をどう比べるか

- 観点は固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/REQUIREMENTS.md` §2 の C3-1〜C3-19。場面は観点ごとに並べ、
  **どの観点にも値の場面を 1 つ以上**置いた(規則 3)。場面の数で観点の重みが決まらないよう、表は観点ごとに一致の数をまとめる。
- **値の場面** = その値が正しいか。合成の入力と、エンジンを見ずに閉じた式・手計算・入力の数え上げで出した正解。
  **能力の場面** = X ができるか。X を使ったときに出るはずの観測できる結果(正解)を決めておき、実際に呼んで突き合わせる(規則 1)。
  「持っている」という申告や、関数・欄の名前があることは数えない。
- 対照と変形: 「拒む」ことが正解の場面は、対照(正しく通るはずの要求)と変形(拒むのが正解の要求)の 2 つを出す。
  対照が正解と一致したときだけ変形を出し、変形の結果で場面の正しさを決める。対照を通せない対象は、変形を拒んでも正解にならない
  (何でも拒む対象が「正解」を取れないようにするため)。
- 振る舞いを見る(規則 2): 要求は宣言(入力の値と規則)だけを渡し、対象の関数の名前や作りを決めない。観測の形が 2 通りありうるもの
  (区分を行で返すか半開区間の境界で返すか)は両方を受け、判定の側が同じものに直して比べる。

## 1. 正しさと再現の欄(資料係の表のセル)

- **正しさ**(良い順。規則 5): 正解と一致 > 対応なし(対象が明示的に拒む・例外を出す)> 不一致(黙って違う値を返す)> 結果なし
  (対象に渡せなかった・欄が無い・時間切れ)。正解の欄が複数ある場面では、ある欄の値が違えば「不一致」(黙った誤りが最も悪い)、
  ある欄はすべて合っていて欠けた欄があれば「結果なし」。
- **再現**: 同じ場面を別のプロセスで 2 回走らせ、正しさの分類と、観測の要約(sha256 の頭 16 桁)が同じなら「2 回の実行で同じ」。
  要約の前に、2 回の間で正当に変わりうる値(リポジトリの HEAD の SHA・作業木の差分のハッシュ・実行 ID の文字列そのもの・
  1 回ごとの作業の置き場の path)を、出てきた順の札(`<git_sha0>`・`<run_id0>` など)に置き換える。等しさの関係(どれとどれが同じか)は
  札で保たれるので、実行 ID の決定性は v8-run-id の関係で見る。

## 2. 走らせ方

- `python3 tests/bt/battery/item_3/run_battery.py --target <対象> --out <表.tsv>`(対象の一覧は `--list-targets`)。
  場面ごとに新しい作業の置き場を作り、要求のファイルを書き、終わったら消す。1 場面の時間の上限 300 秒、1 回の実行の上限 3600 秒。
- 要求と観測の形は `i3_protocol.py`(op ごとの観測の欄)。新実装の adapter(`adapters/new_impl.py`)は口だけで、本体は資料係が毎周書く。
- 試金石: `mutant.py`(新実装を包み、1 か所だけ誤らせる。何を誤らせたかは MUTANT の文)。
- 配線の場面の壊し具: `wiring_break/sitecustomize.py`(環境変数 I3_WIRING_BREAK があるときだけ、標準の http.server の上で効く)。
- 場面にできない部分(批評家が見る): 作業木の差分が変わったときに差分のハッシュが変わること(リポジトリを書き換えないため)。
  画面の見た目(色・配置)。

## 3. 観点と場面の一覧


| 観点 | 要件の語 | 値の場面 | 能力の場面 |
|---|---|---|---|
| C3-1 | 暦日 Train/Val/OOS と walk-forward | v1-split-utc・v1-split-jst・v1-wf-rolling・v1-wf-equal | a1-wf-fit-eval |
| C3-2 | purge・embargo つき walk-forward と CPCV | v2-purge-embargo・v2-cpcv-split | a2-cpcv-paths |
| C3-3 | ブロック・ブートストラップ | v3-block-bootstrap | — |
| C3-4 | MDE の計算 | v4-mde-two-sided・v4-mde-one-sided・v4-verdict | a4-no-mde-no-negative |
| C3-5 | deflated Sharpe と PBO | v5-dsr・v5-dsr-returns・v5-pbo | — |
| C3-6 | 周回数の台帳(ITER)と封印区間の 4 門 | v6-iter-count・v6-iter-dsr | a6-sealed-env・a6-sealed-approval・a6-sealed-token・a6-sealed-audit・a6-sealed-bypass |
| C3-7 | 実行記録の内容 | v7-data-sha256・v7-seed・v7-config・v7-git-sha | a7-diff-hash・a7-version |
| C3-8 | 実行 ID = 内容のハッシュ | v8-run-id | — |
| C3-9 | 同一入力の再現性の自動確認 | v9-seeded-repro | a9-auto-repro |
| C3-10 | 事前登録ハッシュの実行記録への組み込み | v10-prereg-sha | a10-research-needs-prereg |
| C3-11 | 平均で潰さず分布で出す | v11-distribution | — |
| C3-12 | 露出あたり(bp/時) | v12-bp-per-hour | — |
| C3-13 | 約定率・取り逃し・逆選択 markout | v13-fill-rate・v13-markout-buy・v13-markout-sell | — |
| C3-14 | 費用の内訳・決済理由・ドローダウン | v14-cost-breakdown・v14-exit-reasons・v14-dd-pct・v14-dd-abs | — |
| C3-15 | 実行目的(動作確認/研究)の指標書き出しへの記載 | v15-purpose-on-exports | a15-purpose-required |
| C3-16 | 「バックテスト」タブと実行一覧→項目別タブの構成 | v16-run-tabs | a16-list-to-run |
| C3-17 | 日本語表示・CDN 不使用 | v17-no-external | a17-japanese |
| C3-18 | 配線の試験 | v18-wired-values | a18-wiring-test-api・a18-wiring-test-tab |
| C3-19 | 動作確認実行の全タブ警告表示 | v19-warning-all-tabs | — |

場面は全部で 53(値 36・能力 17)。

## 4. 場面ごとの定義(入力 / 期待 / 何を測るか / 正解の出し方)

### C3-1 暦日 Train/Val/OOS と walk-forward

#### v1-split-utc(値の場面)

- **何を測るか**: 暦日(UTC の日付の境目)で Train / Val / OOS に切れるか。行の数の割合ではなく日付で切るか。
- **入力**: `{op: "calendar_split", rows: [47 個: 最初 1767236400000000000、最後 1768086000000000000], tz: "UTC", train_end: "2026-01-07", val_end: "2026-01-09"}`。要求全体の sha256 の頭 1fd34b34a3682a63
- **期待**: 区分ごとの行: {"train": "25 行", "val": "11 行", "oos": "11 行"}(行の時刻の列そのものが正解)
- **正解の出し方**: 10 日分の行(日ごとの行の数が 2・5・3・8・1・6・4・7・2・9 と偏る)を、境目 2026-01-07 00:00 UTC と 2026-01-09 00:00 UTC で半開区間 [始まり, 07日) / [07日, 09日) / [09日, 終わり] に分けた行を数えた。行の数の割合で切ると境目がずれる並びにしてある。観測は各区分の行の時刻の列(`rows`)か、半開区間の境界(`bounds` = [始まり, 終わり))のどちらでもよい。境界で返したときは、判定の側が場面の行にその境界を当てて行の集合に直して比べる。

#### v1-split-jst(値の場面)

- **何を測るか**: 暦日の境目を時間帯つきで決められるか(Asia/Tokyo の 0 時 = 前日 15:00 UTC で切るか)。
- **入力**: `{op: "calendar_split", rows: [47 個: 最初 1767236400000000000、最後 1768086000000000000], tz: "Asia/Tokyo", train_end: "2026-01-07", val_end: "2026-01-09"}`。要求全体の sha256 の頭 170afa156acc52f1
- **期待**: 区分ごとの行: {"train": "23 行", "val": "11 行", "oos": "13 行"}(行の時刻の列そのものが正解)
- **正解の出し方**: v1-split-utc と同じ行を、境目 2026-01-07 00:00 JST(= 01-06 15:00 UTC)と 01-09 00:00 JST(= 01-08 15:00 UTC)で分けた。観測は各区分の行の時刻の列(`rows`)か、半開区間の境界(`bounds` = [始まり, 終わり))のどちらでもよい。境界で返したときは、判定の側が場面の行にその境界を当てて行の集合に直して比べる。

#### v1-wf-rolling(値の場面)

- **何を測るか**: walk-forward で窓を複数回切り直せるか(学習 5 日・評価 2 日・2 日ずつ進める転がる窓)。
- **入力**: `{op: "walk_forward", rows: [480 個: 最初 1767225600000000000、最後 1768950000000000000], tz: "UTC", train_days: 5, test_days: 2, step_days: 2, mode: "rolling"}`。要求全体の sha256 の頭 4578d44db4f4b5ee
- **期待**: 区分ごとの行: [{"train": "120 行(最初 1767225600000000000)", "test": "48 行(最初 1767657600000000000)"}, {"train": "120 行(最初 1767398400000000000)", "test": "48 行(最初 1767830400000000000)"}, {"train": "120 行(最初 1767571200000000000)", "test": "48 行(最初 1768003200000000000)"}, {"train": "120 行(最初 1767744000000000000)", "test": "48 行(最初 1768176000000000000)"}, {"train": "120 行(最初 1767916800000000000)", "test": "48 行(最初 1768348800000000000)"}, {"train": "120 行(最初 1768089600000000000)", "test": "48 行(最初 1768521600000000000)"}, {"train": "120 行(最初 1768262400000000000)", "test": "48 行(最初 1768694400000000000)"}](行の時刻の列そのものが正解)
- **正解の出し方**: 20 日分の毎時の行。k 番目の窓 = 学習 [T0+2k 日, T0+2k+5 日)・評価 [T0+2k+5 日, T0+2k+7 日)、評価の終わりが 20 日目を越えない k = 0..6 の 7 窓。各窓の行を数えた(学習 120 行・評価 48 行)。観測は各区分の行の時刻の列(`rows`)か、半開区間の境界(`bounds` = [始まり, 終わり))のどちらでもよい。境界で返したときは、判定の側が場面の行にその境界を当てて行の集合に直して比べる。

#### v1-wf-equal(値の場面)

- **何を測るか**: 学習と評価が同じ幅で、評価の幅ずつ進む walk-forward(学習 2 日・評価 2 日・2 日ずつ、16 日で 7 窓)を切れるか。
- **入力**: `{op: "walk_forward", rows: [384 個: 最初 1767225600000000000、最後 1768604400000000000], tz: "UTC", train_days: 2, test_days: 2, step_days: 2, mode: "rolling"}`。要求全体の sha256 の頭 c6a8c8516c8a5398
- **期待**: 区分ごとの行: [{"train": "48 行(最初 1767225600000000000)", "test": "48 行(最初 1767398400000000000)"}, {"train": "48 行(最初 1767398400000000000)", "test": "48 行(最初 1767571200000000000)"}, {"train": "48 行(最初 1767571200000000000)", "test": "48 行(最初 1767744000000000000)"}, {"train": "48 行(最初 1767744000000000000)", "test": "48 行(最初 1767916800000000000)"}, {"train": "48 行(最初 1767916800000000000)", "test": "48 行(最初 1768089600000000000)"}, {"train": "48 行(最初 1768089600000000000)", "test": "48 行(最初 1768262400000000000)"}, {"train": "48 行(最初 1768262400000000000)", "test": "48 行(最初 1768435200000000000)"}](行の時刻の列そのものが正解)
- **正解の出し方**: 20 日分の毎時の行の最初の 16 日。k 番目の窓 = 学習 [T0+2k 日, T0+2k+2 日)・評価 [T0+2k+2 日, T0+2k+4 日)、k = 0..6。各窓の行を数えた(学習・評価とも 48 行)。観測は各区分の行の時刻の列(`rows`)か、半開区間の境界(`bounds` = [始まり, 終わり))のどちらでもよい。境界で返したときは、判定の側が場面の行にその境界を当てて行の集合に直して比べる。

#### a1-wf-fit-eval(能力の場面)

- **何を測るか**: walk-forward の各窓で「学習区間で選び、評価区間で測る」を回して、窓ごとの評価を出せるか。
- **入力**: `{op: "walk_forward_eval", rows: [480 個: 最初 1767225600000000000、最後 1768950000000000000], columns: {a: [480 個: 最初 1.0、最後 1.0], b: [480 個: 最初 -0.25、最後 -0.25]}, tz: "UTC", train_days: 5, test_days: 2, step_days: 2, mode: "rolling", rule: "学習区間の列の合計が大きい方を選ぶ(同じなら a)。評価 = 評価区間のその列の合計"}`。要求全体の sha256 の頭 e7f71f47a5be919c
- **期待**: `{folds: [{"choice": "a", "test_score": 0.0}, {"choice": "b", "test_score": -12.0}, {"choice": "a", "test_score": -48.0}, {"choice": "a", "test_score": 0.0}, {"choice": "b", "test_score": -12.0}, {"choice": "a", "test_score": -48.0}, {"choice": "a", "test_score": 0.0}]}`(判定の規則: fold_evals)
- **正解の出し方**: 行ごとに 2 つの損益の列 a・b(a は 3 日ごとに +1 と −1 が入れ替わる、b = −0.5×a + 0.25)。各窓で学習区間の合計が大きい方(同じなら a)を選び、評価区間のその列の合計を評価とする。窓は v1-wf-rolling と同じ 7 窓。選びと評価を窓ごとに手で足した(値は 0.25 の倍数で丸めの誤差が出ない)。選ぶ規則は利用者の書く戦略(adapter が対象の walk-forward の口の上に書く)。

### C3-2 purge・embargo つき walk-forward と CPCV

#### v2-purge-embargo(値の場面)

- **何を測るか**: 学習と評価の間の purge(ラベルの重なりの除去)と embargo(評価のあとの空白)を入れた学習の行の集合を出せるか。
- **入力**: `{op: "purged_split", rows: [30 個: 最初 1767225600000000000、最後 1767330000000000000], label_end: [30 個: 最初 1767234600000000000、最後 1767339000000000000], test_rows: [12, 13, 14, 15, 16, 17], embargo_rows: 2, embargo_ns: 7200000000000}`。要求全体の sha256 の頭 57edf8f7c8c665c6
- **期待**: `{train: [18 個: 最初 0、最後 29]}`(判定の規則: index_set)
- **正解の出し方**: 規則(AFML 7 章の PurgedKFold と同じ形): 評価の塊ごとに、(左)学習の行はラベルの終わりが評価の最初の行の時刻以下のものだけ残す。(右)評価の行のラベルの終わりの最大値以上の時刻に始まる最初の行を「空き」とし、評価の最後の行の次から「空き」の手前までを除き(purge)、さらに「空き」から embargo の行数を除く。ラベルの終わりは行の時刻 + 2.5 時間(行の時刻と一致しないので「以下」と「未満」の違いが出ない)。 30 行(毎時)、評価 = 行 12〜17、embargo = 2 行(= 2 時間)。左: 行 i のラベルの終わり i+2.5 ≤ 12 → i ≤ 9。右: 評価のラベルの終わりの最大 = 行 19.5 の時刻 → 「空き」= 行 20、embargo で 20・21 を除く → 22 から。学習 = 行 0〜9 と 22〜29。(purge だけなら 0〜9 と 20〜29、embargo だけなら 0〜11 と 20〜29 で、どれとも違う。)

#### v2-cpcv-split(値の場面)

- **何を測るか**: CPCV(組合せの purge つき交差検証)で分割の数・経路の数と、ある分割の purge・embargo つきの学習の行を出せるか。
- **入力**: `{op: "cpcv", rows: [30 個: 最初 1767225600000000000、最後 1767330000000000000], label_end: [30 個: 最初 1767234600000000000、最後 1767339000000000000], n_groups: 6, n_test_groups: 2, embargo_rows: 1, embargo_ns: 3600000000000, want_train_for: [1, 3]}`。要求全体の sha256 の頭 386051959b5a5a2d
- **期待**: `{n_splits: 15, n_paths: 5, train: [10 個: 最初 0、最後 29]}`(判定の規則: cpcv_split)
- **正解の出し方**: 規則(AFML 7 章の PurgedKFold と同じ形): 評価の塊ごとに、(左)学習の行はラベルの終わりが評価の最初の行の時刻以下のものだけ残す。(右)評価の行のラベルの終わりの最大値以上の時刻に始まる最初の行を「空き」とし、評価の最後の行の次から「空き」の手前までを除き(purge)、さらに「空き」から embargo の行数を除く。ラベルの終わりは行の時刻 + 2.5 時間(行の時刻と一致しないので「以下」と「未満」の違いが出ない)。 30 行を 6 群(5 行ずつ)、評価に 2 群 → 分割の数 C(6,2) = 15、経路の数 = 2/6 × 15 = 5。評価の群 {1, 3}(行 5〜9 と 15〜19)、embargo = 1 行で、塊ごとに規則を当てた: 塊 5〜9 → 行 3・4 を左で、10・11 を右で除き、embargo で 12。塊 15〜19 → 13・14 を左で、20・21 を右で除き、embargo で 22。学習 = 行 0・1・2・23〜29。

#### a2-cpcv-paths(能力の場面)

- **何を測るか**: CPCV の分割から、各経路が全群をちょうど 1 回ずつ評価で覆う 5 本の経路を組み立てられるか。
- **入力**: `{op: "cpcv_paths", rows: [30 個: 最初 1767225600000000000、最後 1767330000000000000], label_end: [30 個: 最初 1767234600000000000、最後 1767339000000000000], n_groups: 6, n_test_groups: 2, embargo_rows: 1, embargo_ns: 3600000000000}`。要求全体の sha256 の頭 4d7704c7f926fc52
- **期待**: `{n_groups: 6, n_test_groups: 2, n_paths: 5}`(判定の規則: cpcv_paths)
- **正解の出し方**: 正解は性質で決まる: 経路は 5 本、各経路は 6 群のそれぞれに「その群を評価に含む分割」を 1 つずつ当てる、(分割, 群) の組(15 分割 × 2 群 = 30 組)が 5 本の経路にちょうど 1 回ずつ現れる。どの組をどの経路に置くかは決まらないので、判定はこの 3 つの性質だけを見る。

### C3-3 ブロック・ブートストラップ

#### v3-block-bootstrap(値の場面)

- **何を測るか**: 自己相関のある系列で、ブロック単位の再抽出による平均の 95% 信頼区間を出せるか(iid の再抽出では幅が狭すぎる)。
- **入力**: `{op: "block_bootstrap", x: [2000 個: 最初 0.460025、最後 -1.099028], block_len: 20, n_resamples: 2000, seed: 7, alpha: 0.05, statistic: "mean"}`。要求全体の sha256 の頭 76879d1cfa95cf2e
- **期待**: `{mean: 0.06349485849999997, se: 0.05168734818982483, center_tol_se: 0.25, width_band: [0.85, 1.15]}`(判定の規則: ci_band)
- **正解の出し方**: AR(1)(係数 0.6、標準正規の撹乱、種 20260925、捨てる頭 200、n = 2000、小数 6 桁)の平均の標準誤差の正解 = 円環の標本自己共分散に Bartlett の重み (1 − |h|/L) を掛けた和(L = 20)/ n の平方根 = 0.051687(円環のブロック・ブートストラップの分散の閉じた式、Politis & Romano 1992)。判定: 区間の中点が標本平均 0.063495 から 0.25 × 標準誤差以内、かつ (上 − 下) / (2 × 1.96) が標準誤差の 0.85〜1.15 倍。iid の再抽出なら 0.027967(正解の 0.54 倍)で外れる。再抽出の回数 2000、種 7。ブロックの長さを指定できない対象は自分の既定の長さで走らせ、その旨を注記に残す。

### C3-4 MDE の計算

#### v4-mde-two-sided(値の場面)

- **何を測るか**: n と分散から、検出できる最小効果量(MDE)を計算できるか(両側)。
- **入力**: `{op: "mde", n: 400, sd: 10.0, alpha: 0.05, power: 0.8, sides: 2, approx: "normal"}`。要求全体の sha256 の頭 0d94472b1a19386b
- **期待**: `{values: {mde: 1.400792609056484}, rel: 1e-06}`(判定の規則: close)
- **正解の出し方**: 正規近似の閉じた式 MDE = (z(1 − α/2) + z(検出力)) × sd / √n、n = 400、sd = 10 bp、α = 0.05 両側、検出力 0.8 → 1.400793 bp。相対の許容 1e-6(閉じた式なので、許すのは Φ⁻¹ の実装の差だけ。z を 1.96・0.84 に丸めると 6e-4 ずれて外れる)。

#### v4-mde-one-sided(値の場面)

- **何を測るか**: 片側・別の α と検出力でも MDE を計算できるか。
- **入力**: `{op: "mde", n: 100, sd: 5.0, alpha: 0.01, power: 0.9, sides: 1, approx: "normal"}`。要求全体の sha256 の頭 8b0a83251b194a3b
- **期待**: `{values: {mde: 1.8039497197927208}, rel: 1e-06}`(判定の規則: close)
- **正解の出し方**: 同じ式、n = 100、sd = 5 bp、α = 0.01 片側、検出力 0.9 → 1.803950 bp。相対の許容 1e-6(閉じた式なので、許すのは Φ⁻¹ の実装の差だけ。z を 1.96・0.84 に丸めると 6e-4 ずれて外れる)。

#### v4-verdict(値の場面)

- **何を測るか**: MDE と欲しい効果から、結果を 陰性 / 不明 / 陽性 に分けられるか(research-protocol §5 の三分類)。
- **入力**: `{op: "verdict", alpha: 0.05, power: 0.8, sides: 2, cases: [{"estimate": 0.3, "se": 0.5, "n": 400, "sd": 10.0, "interest": 3.0}, {"estimate": 0.3, "se": 0.5, "n": 400, "sd": 10.0, "interest": 1.0}, {"estimate": 2.0, "se": 0.5, "n": 400, "sd": 10.0, "interest": 3.0}]}`。要求全体の sha256 の頭 cecd0b876899edf3
- **期待**: `{values: {verdicts: ["陰性", "不明", "陽性"]}}`(判定の規則: equal)
- **正解の出し方**: research-protocol §4.1・§5: 陰性 = 欲しい効果 > MDE で効果が検出されなかった / 不明 = 欲しい効果 ≤ MDE / 陽性 = 効果が検出された(両側 α = 0.05、|推定 / 標準誤差| > 1.96)。MDE = v4-mde-two-sided と同じ 1.4008 bp。例 1: 推定 0.3 ± 0.5(z = 0.6、非有意)、欲しい効果 3.0 > MDE → 陰性。例 2: 同じ結果、欲しい効果 1.0 < MDE → 不明。例 3: 推定 2.0 ± 0.5(z = 4)→ 陽性。

#### a4-no-mde-no-negative(能力の場面)

- **何を測るか**: MDE を書けない(n か sd が無い)主張を陰性として扱わないことが構造で強制されるか。
- **入力**: `{op: "verdict", alpha: 0.05, power: 0.8, sides: 2, cases: [{"estimate": 0.3, "se": 0.5, "n": 400, "sd": 10.0, "interest": 3.0}]}`。要求全体の sha256 の頭 80df72f18e1e7788
- **期待**: `{values: {verdicts: ["陰性"]}}`(判定の規則: equal)。変形の要求: `{op: "verdict", alpha: 0.05, power: 0.8, sides: 2, cases: [{"estimate": 0.3, "se": 0.5, "interest": 3.0}]}`、変形の正解: `{refuse_or_equal: {verdicts: ["不明"]}}`
- **正解の出し方**: 対照 = v4-verdict の例 1(陰性になるのが正解)。変形 = 同じ結果から n と sd を抜いた(MDE を計算できない)。変形の正解は「陰性を返さない」= 拒む、または 不明 を返す。陰性を返したら不一致。

### C3-5 deflated Sharpe と PBO

#### v5-dsr(値の場面)

- **何を測るか**: 試行回数を踏まえた deflated Sharpe を計算できるか。
- **入力**: `{op: "dsr", sr: 0.1, T: 1000, skew: -0.5, kurtosis: 4.0, n_trials: 10, var_trials: 0.001}`。要求全体の sha256 の頭 816ddcd113718bf6
- **期待**: `{values: {dsr: 0.9386016054910485}, abs: 1e-06}`(判定の規則: close)
- **正解の出し方**: Bailey & López de Prado(2014)の閉じた式: SR0 = √V × ((1 − γ) Φ⁻¹(1 − 1/N) + γ Φ⁻¹(1 − 1/(N e)))、DSR = Φ((SR − SR0) √(T − 1) / √(1 − 歪度 × SR + (尖度 − 1)/4 × SR²))。SR は 1 期あたり 0.1、T = 1000、歪度 −0.5、尖度 4(正規 = 3 の数え方)、N = 10、試行の SR の分散 V = 0.001(= 1/T、雑音だけの試行の分散)。→ 0.938602。絶対の許容 1e-6(閉じた式なので、許すのは Φ と Φ⁻¹ の実装の差 = 1e-9 の桁だけ)。

#### v5-dsr-returns(値の場面)

- **何を測るか**: 収益の系列と試行回数から deflated Sharpe を計算できるか(積率を系列から自分で出す形)。
- **入力**: `{op: "dsr_returns", returns: [500 個: 最初 0.005601、最後 0.004083], n_trials: 10, var_trials: 0.002}`。要求全体の sha256 の頭 1ef69b0c58df7991
- **期待**: `{values: {dsr: 0.9001185518827804}, abs: 0.0005101657598348686}`(判定の規則: close)
- **正解の出し方**: 合成の収益の系列(平均 0.004・標準偏差 0.01 の正規に、確率 0.04 で下向きの跳び、種 20260926、T = 500、小数 6 桁)。系列の積率(母集団の数え方: SR = 平均 / 標準偏差(ddof 0)= 0.129374、歪度 -0.335164、尖度 3.765244(正規 = 3))をv5-dsr の閉じた式に入れた。N = 10、V = 1/T。→ 0.900119。許容 = 論文どおりの実装が選びうる流儀(SR の標準偏差の ddof 0 / 1 × 歪度・尖度の補正なし / あり、の 4 通り)で値が動く幅の最大 = 5.10e-04。式の項を落とした実装(例: 分散の項 (尖度 − 1)/4 を (尖度 − 3)/4 にしたもの)はこの幅を越えて外れる。

#### v5-pbo(値の場面)

- **何を測るか**: Probability of Backtest Overfitting(CSCV)を計算できるか。
- **入力**: `{op: "pbo", matrix: [[4, 5, 4, 1], [-2, 2, 3, 1], [2, -3, 2, -1], [5, -3, 1, -1], [-2, 5, 5, 3], [-1, 3, 4, -1], [3, 1, -2, -3], [-2, 2, 2, -3]], n_blocks: 4, metric: "mean"}`。要求全体の sha256 の頭 ad99deda6ac64110
- **期待**: `{values: {pbo: 0.5}, abs: 1e-09}`(判定の規則: close)
- **正解の出し方**: 8 行 × 4 戦略の性能の行列を 4 塊(2 行ずつ)に分け、塊の半分(2 塊)を学習に取る 6 通りのそれぞれで、学習の平均が最大の戦略の評価側での順位 r(1 = 最悪)から ω = r / 5、λ = ln(ω / (1 − ω))。PBO = λ ≤ 0 の割合。6 通りの r = 3, 3, 2, 3, 1, 2 → PBO = 0.5。性能を平均でなく Sharpe(平均 / 標準偏差)で測っても順位はすべて同じになる行列にしてある。

### C3-6 周回数の台帳(ITER)と封印区間の 4 門

#### v6-iter-count(値の場面)

- **何を測るか**: 周回数の台帳(ITER)に試行を累積し、別の読み手で開き直しても数が保たれるか。
- **入力**: `{op: "iter_ledger", ledger_dir: "ledger", first: [{"design": "d1", "sr": 0.05}, {"design": "d1", "sr": 0.1}, {"design": "d1", "sr": 0.02}], more: [{"design": "d1", "sr": 0.08}]}`。要求全体の sha256 の頭 915038d5e0550e85
- **期待**: `{values: {counts: [3, 3, 4]}}`(判定の規則: equal)
- **正解の出し方**: 台帳の置き場を空にして試行を 3 件登録 → 数 3。台帳を新しく開き直す → 3。もう 1 件登録 → 4。正解 [3, 3, 4]。

#### v6-iter-dsr(値の場面)

- **何を測るか**: 台帳の周回数が多重性(deflated Sharpe の試行回数)に算入されるか。
- **入力**: `{op: "iter_dsr", ledger_dir: "ledger", trials: [{"design": "d1", "sr": 0.05}, {"design": "d1", "sr": 0.1}, {"design": "d1", "sr": 0.02}, {"design": "d1", "sr": 0.08}], best: {sr: 0.1, T: 1000, skew: 0.0, kurtosis: 3.0}, var_trials: 0.001}`。要求全体の sha256 の頭 7bdac00491b29aa8
- **期待**: `{values: {dsr: 0.982304077698815}, abs: 1e-06}`(判定の規則: close)
- **正解の出し方**: 台帳に 4 件登録したあと、最良の SR 0.1(T = 1000、歪度 0、尖度 3、V = 0.001)の DSR を台帳の数 N で出す。正解 = N = 4 の閉じた式(v5-dsr の式)= 0.982304。試行の数を数えない(N = 1、SR0 = 0)なら Φ(0.1 × √999 / √1.005) = 0.999192 で外れる。絶対の許容 1e-6(閉じた式なので、許すのは Φ と Φ⁻¹ の実装の差 = 1e-9 の桁だけ)。

#### a6-sealed-env(能力の場面)

- **何を測るか**: 封印区間は 4 門を全部通らない限り読めないか(この場面は門「環境変数 PHASE2_FINAL_EVAL が単位の名と一致しない」)。
- **入力**: `{op: "sealed_read", unit: "u1", path: "data/d.csv", env: {PHASE2_FINAL_EVAL: "u1"}, token: "I_UNDERSTAND_THIS_IS_FINAL_EVAL"}`。ファイル: `data/d.csv`(236 バイト、sha256 dc42fa1874849bbd…)、`scripts/_research_audit_gate.py`(リポジトリの `scripts/_research_audit_gate.py` の写し)、`docs/AUDITOR/ACTION_LOG.md`(767 バイト、sha256 5edc2908d5652811…)、`backtest_data/phase2_sealed/u1/SEALED.json`(184 バイト、sha256 7cb81132fc15711b…)、`backtest_data/phase2_sealed/u1/UNSEAL_APPROVED`(40 バイト、sha256 acbe3d7c2a36d734…)。要求全体の sha256 の頭 08232bc93db04edb
- **期待**: `{values: {v: [8, 9, 10]}}`(判定の規則: equal)。変形の要求: `{op: "sealed_read", unit: "u1", path: "data/d.csv", env: {}, token: "I_UNDERSTAND_THIS_IS_FINAL_EVAL"}`、変形の正解: `{refuse: true}`
- **正解の出し方**: load_sealed の 4 門の形の置き場(合成の根: 封印の記録 SEALED.json・承認のファイル・監査の台帳・4 つ目の門のモジュール)を場面が作る。対照 = 4 門を全部通す → 封印区間の行(ts ≥ 2026-01-08 の 3 行、v = 8, 9, 10)。変形 = 環境変数 PHASE2_FINAL_EVAL が単位の名と一致しない ほかは対照と同じ → 拒むのが正解。

#### a6-sealed-approval(能力の場面)

- **何を測るか**: 封印区間は 4 門を全部通らない限り読めないか(この場面は門「承認のファイル UNSEAL_APPROVED が無い」)。
- **入力**: `{op: "sealed_read", unit: "u1", path: "data/d.csv", env: {PHASE2_FINAL_EVAL: "u1"}, token: "I_UNDERSTAND_THIS_IS_FINAL_EVAL"}`。ファイル: `data/d.csv`(236 バイト、sha256 dc42fa1874849bbd…)、`scripts/_research_audit_gate.py`(リポジトリの `scripts/_research_audit_gate.py` の写し)、`docs/AUDITOR/ACTION_LOG.md`(767 バイト、sha256 5edc2908d5652811…)、`backtest_data/phase2_sealed/u1/SEALED.json`(184 バイト、sha256 7cb81132fc15711b…)、`backtest_data/phase2_sealed/u1/UNSEAL_APPROVED`(40 バイト、sha256 acbe3d7c2a36d734…)。要求全体の sha256 の頭 08232bc93db04edb
- **期待**: `{values: {v: [8, 9, 10]}}`(判定の規則: equal)。変形の要求: `{op: "sealed_read", unit: "u1", path: "data/d.csv", env: {PHASE2_FINAL_EVAL: "u1"}, token: "I_UNDERSTAND_THIS_IS_FINAL_EVAL"}`、変形の正解: `{refuse: true}`
- **正解の出し方**: load_sealed の 4 門の形の置き場(合成の根: 封印の記録 SEALED.json・承認のファイル・監査の台帳・4 つ目の門のモジュール)を場面が作る。対照 = 4 門を全部通す → 封印区間の行(ts ≥ 2026-01-08 の 3 行、v = 8, 9, 10)。変形 = 承認のファイル UNSEAL_APPROVED が無い ほかは対照と同じ → 拒むのが正解。

#### a6-sealed-token(能力の場面)

- **何を測るか**: 封印区間は 4 門を全部通らない限り読めないか(この場面は門「確認のトークンが違う」)。
- **入力**: `{op: "sealed_read", unit: "u1", path: "data/d.csv", env: {PHASE2_FINAL_EVAL: "u1"}, token: "I_UNDERSTAND_THIS_IS_FINAL_EVAL"}`。ファイル: `data/d.csv`(236 バイト、sha256 dc42fa1874849bbd…)、`scripts/_research_audit_gate.py`(リポジトリの `scripts/_research_audit_gate.py` の写し)、`docs/AUDITOR/ACTION_LOG.md`(767 バイト、sha256 5edc2908d5652811…)、`backtest_data/phase2_sealed/u1/SEALED.json`(184 バイト、sha256 7cb81132fc15711b…)、`backtest_data/phase2_sealed/u1/UNSEAL_APPROVED`(40 バイト、sha256 acbe3d7c2a36d734…)。要求全体の sha256 の頭 08232bc93db04edb
- **期待**: `{values: {v: [8, 9, 10]}}`(判定の規則: equal)。変形の要求: `{op: "sealed_read", unit: "u1", path: "data/d.csv", env: {PHASE2_FINAL_EVAL: "u1"}, token: "not-the-token"}`、変形の正解: `{refuse: true}`
- **正解の出し方**: load_sealed の 4 門の形の置き場(合成の根: 封印の記録 SEALED.json・承認のファイル・監査の台帳・4 つ目の門のモジュール)を場面が作る。対照 = 4 門を全部通す → 封印区間の行(ts ≥ 2026-01-08 の 3 行、v = 8, 9, 10)。変形 = 確認のトークンが違う ほかは対照と同じ → 拒むのが正解。

#### a6-sealed-audit(能力の場面)

- **何を測るか**: 封印区間は 4 門を全部通らない限り読めないか(この場面は門「監査の台帳の最後の判定が「通す」でない(4 つ目の門)」)。
- **入力**: `{op: "sealed_read", unit: "u1", path: "data/d.csv", env: {PHASE2_FINAL_EVAL: "u1"}, token: "I_UNDERSTAND_THIS_IS_FINAL_EVAL"}`。ファイル: `data/d.csv`(236 バイト、sha256 dc42fa1874849bbd…)、`scripts/_research_audit_gate.py`(リポジトリの `scripts/_research_audit_gate.py` の写し)、`docs/AUDITOR/ACTION_LOG.md`(767 バイト、sha256 5edc2908d5652811…)、`backtest_data/phase2_sealed/u1/SEALED.json`(184 バイト、sha256 7cb81132fc15711b…)、`backtest_data/phase2_sealed/u1/UNSEAL_APPROVED`(40 バイト、sha256 acbe3d7c2a36d734…)。要求全体の sha256 の頭 08232bc93db04edb
- **期待**: `{values: {v: [8, 9, 10]}}`(判定の規則: equal)。変形の要求: `{op: "sealed_read", unit: "u1", path: "data/d.csv", env: {PHASE2_FINAL_EVAL: "u1"}, token: "I_UNDERSTAND_THIS_IS_FINAL_EVAL"}`、変形の正解: `{refuse: true}`
- **正解の出し方**: load_sealed の 4 門の形の置き場(合成の根: 封印の記録 SEALED.json・承認のファイル・監査の台帳・4 つ目の門のモジュール)を場面が作る。対照 = 4 門を全部通す → 封印区間の行(ts ≥ 2026-01-08 の 3 行、v = 8, 9, 10)。変形 = 監査の台帳の最後の判定が「通す」でない(4 つ目の門) ほかは対照と同じ → 拒むのが正解。

#### a6-sealed-bypass(能力の場面)

- **何を測るか**: 実行のための普通の読み込みの経路からも、封印区間の行が読めないか(4 門を迂回できないか)。
- **入力**: `{op: "data_read", path: "data/d.csv", time_column: "ts"}`。ファイル: `data/d.csv`(236 バイト、sha256 dc42fa1874849bbd…)。要求全体の sha256 の頭 de85b95941d7b976
- **期待**: `{values: {v: [10 個: 最初 1、最後 10]}}`(判定の規則: equal)。変形の要求: `{op: "data_read", path: "data/d.csv", time_column: "ts"}`、変形の正解: `{refuse_or_equal: {v: [1, 2, 3, 4, 5, 6, 7]}}`
- **正解の出し方**: 対照 = 封印の記録が無い根で data/d.csv を普通に読む → 10 行全部(v = 1..10)。変形 = 同じ根に封印の記録(ts ≥ 2026-01-08 を封印)を置いて同じ読み込み → 正解は「拒む」か「封印区間を除いた 7 行(v = 1..7)だけを返す」。

### C3-7 実行記録の内容

#### v7-data-sha256(値の場面)

- **何を測るか**: 実行記録に、読んだデータの sha256 が残るか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "動作確認"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 8d725259f030ea87
- **期待**: `{field: "data_sha256", value: {data/tape.csv: "6cdec77d20708ce813f752721e16db01974f43a6f1ccec817f6f644460e723f0"}}`(判定の規則: record)
- **正解の出し方**: 固定の実行 = 合成の約定の列 data/tape.csv(3 往復の各時刻の前後 60 秒は値が一定)に、時刻だけで決まる成行の3 往復(買い → 5 分後に売り)を費用 0・遅延 0 を明示して回す。 正解 = data/tape.csv のバイト列の sha256 = 6cdec77d20708ce813f752721e16db01974f43a6f1ccec817f6f644460e723f0(場面が書いた文字列から計算)。

#### v7-seed(値の場面)

- **何を測るか**: 実行記録に、乱数の種が残るか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "動作確認"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 8d725259f030ea87
- **期待**: `{field: "seed", value: 11}`(判定の規則: record)
- **正解の出し方**: 固定の実行 = 合成の約定の列 data/tape.csv(3 往復の各時刻の前後 60 秒は値が一定)に、時刻だけで決まる成行の3 往復(買い → 5 分後に売り)を費用 0・遅延 0 を明示して回す。 渡した種は 11。正解 = 11。

#### v7-config(値の場面)

- **何を測るか**: 実行記録に、設定が全部そのまま残るか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "動作確認"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 8d725259f030ea87
- **期待**: `{field: "config", value: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}}`(判定の規則: record)
- **正解の出し方**: 固定の実行 = 合成の約定の列 data/tape.csv(3 往復の各時刻の前後 60 秒は値が一定)に、時刻だけで決まる成行の3 往復(買い → 5 分後に売り)を費用 0・遅延 0 を明示して回す。 正解 = 渡した設定の辞書そのもの(JSON として等しい)。

#### v7-git-sha(値の場面)

- **何を測るか**: 実行記録に、コードの git の SHA が残るか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "動作確認"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 8d725259f030ea87
- **期待**: `{field: "git_sha", value: {oracle: "git_head"}}`(判定の規則: record)
- **正解の出し方**: 固定の実行 = 合成の約定の列 data/tape.csv(3 往復の各時刻の前後 60 秒は値が一定)に、時刻だけで決まる成行の3 往復(買い → 5 分後に売り)を費用 0・遅延 0 を明示して回す。 正解 = 判定の時点でリポジトリの `git rev-parse HEAD` が返す 40 桁(判定の側が自分で打つ。版が動くので繰り返しの比較からは外す)。

#### a7-diff-hash(能力の場面)

- **何を測るか**: 実行記録に、作業中の差分のハッシュが残るか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "動作確認"}, repeat: 2}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 ce28d0f1b2e2ff9e
- **期待**: `{field: "diff_hash", min_len: 16}`(判定の規則: record_stable_hex)
- **正解の出し方**: 固定の実行 = 合成の約定の列 data/tape.csv(3 往復の各時刻の前後 60 秒は値が一定)に、時刻だけで決まる成行の3 往復(買い → 5 分後に売り)を費用 0・遅延 0 を明示して回す。 同じ場面の中で固定の実行を 2 回回し、2 回とも 16 桁以上の 16 進の文字列で、互いに等しいこと(同じ作業木)。差分の中身そのものは場面の外(リポジトリの作業木)で決まるので値は比べない。版と作業木が動くので繰り返しの比較からは外す。差分が変わったときに値が変わることは場面にできない(リポジトリを書き換えない)ので、批評家が見る。

#### a7-version(能力の場面)

- **何を測るか**: 実行記録に、版(エンジンの版の文字列)が残るか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "動作確認"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 8d725259f030ea87
- **期待**: `{field: "version"}`(判定の規則: record_nonempty)
- **正解の出し方**: 固定の実行 = 合成の約定の列 data/tape.csv(3 往復の各時刻の前後 60 秒は値が一定)に、時刻だけで決まる成行の3 往復(買い → 5 分後に売り)を費用 0・遅延 0 を明示して回す。 正解 = 空でない文字列(版の値そのものは対象ごとに違うので比べない)。

### C3-8 実行 ID = 内容のハッシュ

#### v8-run-id(値の場面)

- **何を測るか**: 実行 ID が内容のハッシュ(同じ内容なら同じ、内容が違えば違う、時刻や乱数に依らない)か。
- **入力**: `{op: "run_ids", runs: [5 個: 最初 {"data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "strategy": {、最後 {"data": ["data/tape_c.csv"], "config": {"instrument": "FX_BTC_JPY", "strategy":], sleep_before_s: [0, 1.1, 0, 0, 0]}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)、`data/tape_c.csv`(5262 バイト、sha256 db1448dd1c133a14…)。要求全体の sha256 の頭 e9229140830f081e
- **期待**: `{groups: [[0, 1, 2], [3], [4]]}`(判定の規則: id_relations)
- **正解の出し方**: 5 回の実行: ① 固定の実行 ② ①と同じ(1.1 秒あけて)③ ①と同じ設定を鍵の順だけ逆にした辞書 ④ 種だけ 12 ⑤ データだけ別(値が全部 +1000 のファイル data/tape_c.csv)。正解の関係 = ①=②=③、④と⑤は①とも互いとも違う。ID の文字列そのものはコードの版で変わるので、繰り返しの比較は関係(どれとどれが等しいか)で行う。

### C3-9 同一入力の再現性の自動確認

#### v9-seeded-repro(値の場面)

- **何を測るか**: 種つきの乱数を使う実行を、対象の自動の確認が 2 回回して「一致する」と判定するか(種が効いているか)。
- **入力**: `{op: "auto_repro", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "seeded_random", runs_dir: "runs", purpose: "動作確認"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 db498a762ef5551a
- **期待**: `{values: {reproduced: true, runs: 2}}`(判定の規則: equal)
- **正解の出し方**: 戦略を「種つきの乱数」(各往復の数量を 0.01 × (1 + r / 256)、r は種 11 の random.Random(11).randrange(256) を往復の順に引く)にした固定の実行を対象の自動の確認にかける。種が同じなので 2 回の結果は同じ = 一致(真)、比べた回数 2 が正解。種を使わない実行(a9 の変形)と違い、乱数そのものは入っている。

#### a9-auto-repro(能力の場面)

- **何を測るか**: 同じ入力で 2 回回して一致を自動で確かめる仕組みがあり、一致しないときに一致しないと言えるか。
- **入力**: `{op: "auto_repro", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "動作確認"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 2197d00e6fd2935f
- **期待**: `{values: {reproduced: true}}`(判定の規則: equal)。変形の要求: `{op: "auto_repro", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "unseeded_random", runs_dir: "runs", purpose: "動作確認"}}`、変形の正解: `{equal: {reproduced: false}}`
- **正解の出し方**: 対照 = 固定の実行を対象の自動の確認にかける → 一致(真)が正解。変形 = 戦略だけを「種を使わない乱数」(各往復の数量を 0.01 × (1 + os.urandom の 1 バイト / 256))に替える → 2 回の結果(数量と円の損益)が違うので「一致しない」(偽)が正解。bp は数量に依らず同じなので、bp だけを比べる確認は変形を見逃す。

### C3-10 事前登録ハッシュの実行記録への組み込み

#### v10-prereg-sha(値の場面)

- **何を測るか**: 事前登録のファイルのハッシュが実行記録に入るか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "研究", prereg: "prereg/PREREG.md"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 f51ec9bd2dcd2106
- **期待**: `{field: "prereg_sha256", value: "574adfef3d9f80409cf2969aff7d1d01fcba1013c0539201e195534e73c3f0d1"}`(判定の規則: record)
- **正解の出し方**: 固定の実行 = 合成の約定の列 data/tape.csv(3 往復の各時刻の前後 60 秒は値が一定)に、時刻だけで決まる成行の3 往復(買い → 5 分後に売り)を費用 0・遅延 0 を明示して回す。 目的 研究、事前登録 prereg/PREREG.md。正解 = そのバイト列の sha256 = 574adfef3d9f80409cf2969aff7d1d01fcba1013c0539201e195534e73c3f0d1。

#### a10-research-needs-prereg(能力の場面)

- **何を測るか**: 目的が 研究 の実行は、事前登録のハッシュが無いと作れないか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "研究", prereg: "prereg/PREREG.md"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 f51ec9bd2dcd2106
- **期待**: `{field: "purpose", value: "研究"}`(判定の規則: record)。変形の要求: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "研究"}}`、変形の正解: `{refuse: true}`
- **正解の出し方**: 対照 = 目的 研究 + 事前登録つき → 実行ができ、記録の目的が 研究。変形 = 目的 研究・事前登録なし → 拒むのが正解。

### C3-11 平均で潰さず分布で出す

#### v11-distribution(値の場面)

- **何を測るか**: 1 件ごとの bp・分位・負の割合を、平均 1 個に潰さずに出せるか。
- **入力**: `{op: "trade_metrics", trades: [21 個: 最初 {"id": "t1", "side": "sell", "qty": 1.0, "entry_px": 10000.0, "exit_px": 9985.0,、最後 {"id": "t21", "side": "buy", "qty": 1.0, "entry_px": 10000.0, "exit_px": 10015.0], want: ["per_trade_bp", "quantiles", "neg_frac"], quantile_probs: [0.05, 0.25, 0.5, 0.75, 0.95], quantile_method: "linear"}`。要求全体の sha256 の頭 795e8656de7e5d70
- **期待**: `{abs: 1e-09, values: {per_trade_bp: [21 個: 最初 15.0、最後 15.0], quantiles: {0.05: -12.0, 0.25: 3.0, 0.5: 12.0, 0.75: 22.0, 0.95: 55.0}, neg_frac: 0.19047619047619047}}`(判定の規則: close)
- **正解の出し方**: 21 件の往復(入りの値 10000、出の値 = 買いなら 10000 + bp、売りなら 10000 − bp、費用 0)。1 件ごとの bp = 向き × (出 − 入) / 入 × 10000。分位は順序統計量の線形補間(Hyndman & Fan の 7 型、numpy の既定): p = 0.05・0.25・0.5・0.75・0.95 は (n − 1) p = 1・5・10・15・19 が整数なので並べた値そのもの。負の割合 = 負の件数 / 件数(0 は負に数えない)= 4/21。

### C3-12 露出あたり(bp/時)

#### v12-bp-per-hour(値の場面)

- **何を測るか**: 建玉を持っていた時間(露出)あたりの bp(bp/時)を出せるか。
- **入力**: `{op: "trade_metrics", trades: [3 個: 最初 {"id": "a", "side": "buy", "qty": 1.0, "entry_px": 10000.0, "exit_px": 10010.0, 、最後 {"id": "c", "side": "sell", "qty": 1.0, "entry_px": 10000.0, "exit_px": 9994.0, ], want: ["exposure_hours", "bp_per_hour"]}`。要求全体の sha256 の頭 4c414bf9d37e3a9b
- **期待**: `{abs: 1e-09, values: {exposure_hours: 2.0, bp_per_hour: 6.0}}`(判定の規則: close)
- **正解の出し方**: 3 件: 10:00–10:30 に +10 bp、11:00–12:00 に −4 bp、13:30–14:00 に +6 bp(売り)。露出の時間 = 0.5 + 1 + 0.5 = 2 時間、bp/時 = (10 − 4 + 6) / 2 = 6。最初の入りから最後の出までの 4 時間で割ると 3 になる(罠)。

### C3-13 約定率・取り逃し・逆選択 markout

#### v13-fill-rate(値の場面)

- **何を測るか**: 約定率と取り逃し(埋まらなかった指値の件数)を出せるか。
- **入力**: `{op: "fill_metrics", orders: [5 個: 最初 {"id": "o1", "t_ns": 1767225600000000000, "side": "buy", "type": "limit", "px": 、最後 {"id": "o5", "t_ns": 1767225640000000000, "side": "buy", "type": "limit", "px": ], fills: [{"order_id": "o1", "t_ns": 1767225700000000000, "px": 10000.0, "qty": 1.0}, {"order_id": "o3", "t_ns": 1767225820000000000, "px": 10100.0, "qty": 1.0}, {"order_id": "o4", "t_ns": 1767226000000000000, "px": 9950.0, "qty": 1.0}], end_t_ns: 1767226600000000000}`。要求全体の sha256 の頭 32ecece80b3d9c6d
- **期待**: `{abs: 1e-12, values: {fill_rate: 0.6, missed: 2}}`(判定の規則: close)
- **正解の出し方**: 指値 5 件(o1〜o5)、期限 1000 秒までに埋まったのは o1・o3・o4。約定率 = 3/5 = 0.6、取り逃し = 2 件。

#### v13-markout-buy(値の場面)

- **何を測るか**: 買いの約定の逆選択の markout を複数の時間窓で出せるか。
- **入力**: `{op: "markout", fills: [{"t_ns": 1767225700000000000, "px": 10000.0, "side": "buy", "qty": 1.0}, {"t_ns": 1767226000000000000, "px": 9950.0, "side": "buy", "qty": 1.0}], mids: [[1767225700000000000, 10002.0], [1767225760000000000, 9990.0], [1767225820000000000, 10098.0], [1767225880000000000, 10110.0], [1767226000000000000, 9952.0], [1767226060000000000, 9940.0], [1767226120000000000, 10085.0], [1767226300000000000, 9985.0]], horizons_s: [60, 300]}`。要求全体の sha256 の頭 cb147562efbc8b62
- **期待**: `{abs: 1e-09, values: {markout: {60: [-10.0, -10.0], 300: [-48.0, 35.0]}}}`(判定の規則: close)
- **正解の出し方**: markout(h)= 向き × (仲値(t + h) − 約定の値)、値の単位(買いは向き +1)。仲値の列は約定の時刻と t + 60 秒・t + 300 秒のそれぞれにちょうど 1 点を置いた(「以前で最後」と「以後で最初」の流儀の差が出ない)。買い 2 件: 60 秒 = [-10.0, -10.0]、300 秒 = [-48.0, 35.0]。

#### v13-markout-sell(値の場面)

- **何を測るか**: 売りの約定の markout で向きを正しく扱えるか。
- **入力**: `{op: "markout", fills: [{"t_ns": 1767225820000000000, "px": 10100.0, "side": "sell", "qty": 1.0}], mids: [[1767225700000000000, 10002.0], [1767225760000000000, 9990.0], [1767225820000000000, 10098.0], [1767225880000000000, 10110.0], [1767226000000000000, 9952.0], [1767226060000000000, 9940.0], [1767226120000000000, 10085.0], [1767226300000000000, 9985.0]], horizons_s: [60, 300]}`。要求全体の sha256 の頭 8afab6e6a48479ff
- **期待**: `{abs: 1e-09, values: {markout: {60: [-10.0], 300: [15.0]}}}`(判定の規則: close)
- **正解の出し方**: 同じ式で売りは向き −1。売り 1 件(10100、t = 220 秒): 60 秒 = [-10.0]、300 秒 = [15.0]。

### C3-14 費用の内訳・決済理由・ドローダウン

#### v14-cost-breakdown(値の場面)

- **何を測るか**: 費用を種類ごと(maker 手数料・taker 手数料・スプレッド・資金調達)の内訳で出せるか。
- **入力**: `{op: "cost_breakdown", fills: [4 個: 最初 {"id": "f1", "t_ns": 1767225600000000000, "side": "buy", "qty": 1.0, "px": 10000、最後 {"id": "f4", "t_ns": 1767225780000000000, "side": "buy", "qty": 0.5, "px": 10090], funding: [{"t_ns": 1767225630000000000, "rate": 0.0001, "mark": 10020.0}, {"t_ns": 1767225750000000000, "rate": 0.0001, "mark": 10100.0}], rates: {maker_fee_rate: 0.0002, taker_fee_rate: 0.0005}}`。要求全体の sha256 の頭 46e45084e5bc0c4d
- **期待**: `{abs: 1e-09, values: {costs: {maker_fee: 3.019, taker_fee: 7.525, spread: 10.5, funding: 0.497}}}`(判定の規則: close)
- **正解の出し方**: 約定 4 件と資金調達 2 回。手数料 = 値 × 数量 × 率(maker 0.0002・taker 0.0005)。スプレッドの費用 = 向き × (約定の値 − その時の仲値)× 数量(買い +1・売り −1、全約定)。資金調達 = その時刻の建玉 × 基準値 × 率(買い建てが払う)。maker = 3.019000、taker = 7.525000、スプレッド = 10.500000、資金調達 = 0.497000(円)。

#### v14-exit-reasons(値の場面)

- **何を測るか**: 決済理由ごとに件数と損益を集計できるか。
- **入力**: `{op: "exit_reasons", trades: [7 個: 最初 {"id": "x0", "reason": "tp", "pnl": 50.0}、最後 {"id": "x6", "reason": "tp", "pnl": 45.0}]}`。要求全体の sha256 の頭 9f5357a64b4fe1c9
- **期待**: `{abs: 1e-09, values: {by_reason: {tp: {n: 3, pnl: 135.0}, sl: {n: 2, pnl: -55.0}, time_exit: {n: 1, pnl: -5.0}, signal: {n: 1, pnl: 10.0}}}}`(判定の規則: close)
- **正解の出し方**: 7 件の往復に決済理由(tp・sl・time_exit・signal)と円の損益を付けた。理由ごとに数えて足した: tp = 3 件 +135、sl = 2 件 -55、time_exit = 1 件 -5、signal = 1 件 +10。

#### v14-dd-pct(値の場面)

- **何を測るか**: 最大ドローダウン(率)を出せるか。
- **入力**: `{op: "drawdown", equity: [100.0, 110.0, 105.0, 120.0, 90.0, 95.0, 130.0, 117.0], t_ns: [1767225600000000000, 1767229200000000000, 1767232800000000000, 1767236400000000000, 1767240000000000000, 1767243600000000000, 1767247200000000000, 1767250800000000000]}`。要求全体の sha256 の頭 cc8f7318aaf4654f
- **期待**: `{abs: 1e-09, values: {max_dd_pct: 25.0}}`(判定の規則: close)
- **正解の出し方**: 資産の列 [100.0, 110.0, 105.0, 120.0, 90.0, 95.0, 130.0, 117.0]。各時点の最高値からの下落率の最大 = (120 − 90) / 120 = 25.0 %。

#### v14-dd-abs(値の場面)

- **何を測るか**: 最大ドローダウン(額)を出せるか。
- **入力**: `{op: "drawdown", equity: [100.0, 110.0, 105.0, 120.0, 90.0, 95.0, 130.0, 117.0], t_ns: [1767225600000000000, 1767229200000000000, 1767232800000000000, 1767236400000000000, 1767240000000000000, 1767243600000000000, 1767247200000000000, 1767250800000000000]}`。要求全体の sha256 の頭 cc8f7318aaf4654f
- **期待**: `{abs: 1e-09, values: {max_dd_abs: 30.0}}`(判定の規則: close)
- **正解の出し方**: 同じ列。最高値からの下落額の最大 = 120 − 90 = 30.0(後半の 130 → 117 の 13 より大きい)。

### C3-15 実行目的(動作確認/研究)の指標書き出しへの記載

#### v15-purpose-on-exports(値の場面)

- **何を測るか**: 指標の書き出しの全部に、実行の目的(動作確認)が載るか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "動作確認"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 8d725259f030ea87
- **期待**: `{value: "動作確認"}`(判定の規則: exports_purpose)
- **正解の出し方**: 固定の実行 = 合成の約定の列 data/tape.csv(3 往復の各時刻の前後 60 秒は値が一定)に、時刻だけで決まる成行の3 往復(買い → 5 分後に売り)を費用 0・遅延 0 を明示して回す。 目的 動作確認。正解 = 書き出しのファイルが 1 つ以上あり、その全部が目的の欄 = 動作確認 を持つ。

#### a15-purpose-required(能力の場面)

- **何を測るか**: 目的を書かない実行(と書き出し)が作れないことが構造で強制されるか。
- **入力**: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs", purpose: "動作確認"}}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 8d725259f030ea87
- **期待**: `{field: "purpose", value: "動作確認"}`(判定の規則: record)。変形の要求: `{op: "run", run: {data: ["data/tape.csv"], config: {instrument: "FX_BTC_JPY", strategy: {kind: "fixed_times", legs: [6 個: 最初 {"t_ns": 1767229200000000000, "side": "buy", "qty": 0.01}、最後 {"t_ns": 1767236700000000000, "side": "sell", "qty": 0.01}]}, order_type: "market", fill: {market: "next_trade_price"}, latency_ns: {feed: 0, order: 0, cancel: 0}, costs: {maker_fee_rate: 0.0, taker_fee_rate: 0.0, funding: "none", source: "合成の場面の宣言(費用 0 を明示)"}}, seed: 11, strategy: "fixed_times", runs_dir: "runs"}}`、変形の正解: `{refuse: true}`
- **正解の出し方**: 対照 = 目的 動作確認 → 実行ができ、記録の目的 = 動作確認。変形 = 目的の欄を抜いた同じ実行 → 拒むのが正解。

### C3-16 「バックテスト」タブと実行一覧→項目別タブの構成

#### v16-run-tabs(値の場面)

- **何を測るか**: 実行ごとの項目別タブが要件の 10 項目(概要 / 前提 / 損益 / 取引 / 約定の質 / 費用 / 分布 / 検証 / 再現性 / データ品質)か。
- **入力**: `{op: "dashboard", runs: [2 個: 最初 {"key": "A", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "、最後 {"key": "B", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "]}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 ae5c8948e305adf7
- **期待**: `{tabs: [10 個: 最初 "概要"、最後 "データ品質"]}`(判定の規則: dash_run_tabs)
- **正解の出し方**: 固定の実行を 2 つ(A = 目的 動作確認、B = 目的 研究 + 事前登録)対象自身の書き出しで作り、対象のダッシュボードを空いている口で起こして読む。 正解 = A と B のそれぞれのタブの名の並び = 要件の 10 項目の順(名の後ろの括弧書きは除いて比べる)。

#### a16-list-to-run(能力の場面)

- **何を測るか**: 「バックテスト」タブがあり、実行の一覧から実行ごとのタブへ辿れるか。
- **入力**: `{op: "dashboard", runs: [2 個: 最初 {"key": "A", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "、最後 {"key": "B", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "]}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 ae5c8948e305adf7
- **期待**: `{}`(判定の規則: dash_list)
- **正解の出し方**: 固定の実行を 2 つ(A = 目的 動作確認、B = 目的 研究 + 事前登録)対象自身の書き出しで作り、対象のダッシュボードを空いている口で起こして読む。 正解 = 最上段のタブに「バックテスト」があり、実行の一覧に A と B の実行 ID が両方あり、一覧の各 ID から辿った先がその実行のタブである。

### C3-17 日本語表示・CDN 不使用

#### v17-no-external(値の場面)

- **何を測るか**: バックテストの画面が外部(CDN など)からスクリプト・スタイル・画像を読み込まないか。
- **入力**: `{op: "dashboard", runs: [2 個: 最初 {"key": "A", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "、最後 {"key": "B", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "]}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 ae5c8948e305adf7
- **期待**: `{values: {external_refs: []}}`(判定の規則: equal)
- **正解の出し方**: 固定の実行を 2 つ(A = 目的 動作確認、B = 目的 研究 + 事前登録)対象自身の書き出しで作り、対象のダッシュボードを空いている口で起こして読む。 画面と、画面が読み込むスクリプト・スタイルに現れる http:// か https:// の読み込み先の一覧。正解 = 空。

#### a17-japanese(能力の場面)

- **何を測るか**: バックテストの画面の文言(タブの名・警告)が日本語か。
- **入力**: `{op: "dashboard", runs: [2 個: 最初 {"key": "A", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "、最後 {"key": "B", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "]}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 ae5c8948e305adf7
- **期待**: `{}`(判定の規則: dash_japanese)
- **正解の出し方**: 固定の実行を 2 つ(A = 目的 動作確認、B = 目的 研究 + 事前登録)対象自身の書き出しで作り、対象のダッシュボードを空いている口で起こして読む。 正解 = 最上段の「バックテスト」、実行ごとの 10 のタブの名、A の警告の文が、どれも仮名か漢字を含む(英字だけの名が無い)。

### C3-18 配線の試験

#### v18-wired-values(値の場面)

- **何を測るか**: ダッシュボードに出る値が、書き出しの値と配線どおりに繋がっているか(値で見る配線)。
- **入力**: `{op: "dashboard", runs: [2 個: 最初 {"key": "A", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "、最後 {"key": "B", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "]}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 ae5c8948e305adf7
- **期待**: `{run: "A", values: {per_trade_bp: [100.0, -50.0, 30.0], neg_frac: 0.3333333333333333}, abs: 1e-06}`(判定の規則: dash_values)
- **正解の出し方**: 固定の実行を 2 つ(A = 目的 動作確認、B = 目的 研究 + 事前登録)対象自身の書き出しで作り、対象のダッシュボードを空いている口で起こして読む。 A の 1 件ごとの bp = [100.0, -50.0, 30.0](10,000,000 → 10,100,000 など、場面の値から手で計算)、負の割合 = 1/3。正解 = ダッシュボードが A について出すこの 2 つ。

#### a18-wiring-test-api(能力の場面)

- **何を測るか**: ダッシュボードの配線の試験が、バックテストの API の経路が切れたことを検出するか。
- **入力**: `{op: "wiring_test", break: null}`。要求全体の sha256 の頭 dfe46473c358c5e6
- **期待**: `{values: {passed: true}}`(判定の規則: equal)。変形の要求: `{op: "wiring_test", break: "api_route"}`、変形の正解: `{equal: {passed: false}}`
- **正解の出し方**: 対照 = 対象の配線の試験をそのまま回す → 通る(真)が正解。変形 = 場面集の壊し具(http.server の上で、/api/ で始まり backtest を含む GET を 404 にする)を効かせて同じ試験を回す → 落ちる(偽)が正解。

#### a18-wiring-test-tab(能力の場面)

- **何を測るか**: ダッシュボードの配線の試験が、「バックテスト」タブが消えたことを検出するか。
- **入力**: `{op: "wiring_test", break: null}`。要求全体の sha256 の頭 dfe46473c358c5e6
- **期待**: `{values: {passed: true}}`(判定の規則: equal)。変形の要求: `{op: "wiring_test", break: "tab_label"}`、変形の正解: `{equal: {passed: false}}`
- **正解の出し方**: 対照 = そのまま → 通る(真)。変形 = 壊し具(http.server の応答の本文の「バックテスト」を同じ長さの空白に替える)を効かせる → 落ちる(偽)が正解。

### C3-19 動作確認実行の全タブ警告表示

#### v19-warning-all-tabs(値の場面)

- **何を測るか**: 目的が 動作確認 の実行は全タブに「動作確認の実行。相場の結論には使わない」を出し、研究 の実行には出さないか。
- **入力**: `{op: "dashboard", runs: [2 個: 最初 {"key": "A", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "、最後 {"key": "B", "data": ["data/tape.csv"], "config": {"instrument": "FX_BTC_JPY", "]}`。ファイル: `data/tape.csv`(5262 バイト、sha256 6cdec77d20708ce8…)、`prereg/PREREG.md`(116 バイト、sha256 574adfef3d9f8040…)。要求全体の sha256 の頭 ae5c8948e305adf7
- **期待**: `{warning: "動作確認の実行。相場の結論には使わない", tabs: [10 個: 最初 "概要"、最後 "データ品質"]}`(判定の規則: dash_warning)
- **正解の出し方**: 固定の実行を 2 つ(A = 目的 動作確認、B = 目的 研究 + 事前登録)対象自身の書き出しで作り、対象のダッシュボードを空いている口で起こして読む。 正解 = A の 10 タブすべてに警告の文がある(真)、B の 10 タブのどれにも無い(偽)。


## 提出前の吟味(場面係の最初の作り。委任文 §3「提出前の吟味」、L-433)

固定した要件 §2 の C3-1〜C3-19・場面集の規則 1〜9・比較の観点を読み直し、非常に厳しい監査役・批評家なら何を [止める] に
するかを観点ごとに列べ、返す前に潰した。潰せなかったものは最後に残りとして書く。

1. **規則 1(能力の場面も正解と突き合わせる)**: 能力の場面(a1・a2・a4・a6・a7・a9・a10・a15・a16・a17・a18)はすべて、
   呼んだ結果を決めておいた正解と比べる。「拒む」が正解の場面は対照と変形の組にし、対照を通せない対象は変形を拒んでも正解に
   しない(`run_battery.py` の classify)。能力の申告・関数の有無は数えない。→ 潰した。
2. **規則 2(振る舞いを試し、作りの形を試さない)**: 区分は行でも境界でも受け、判定の側で同じものに直す。実行記録は欄の値で見て、
   ファイルの形は問わない。画面は配った中身(HTML・API)から読むことを求め、関数の名前は決めない。→ 潰した。
   残る決め: 観測の欄の名前(i3_protocol.py)は場面係が決めた口で、adapter が対象の出力をその名前に入れ替える(値の計算はしない)。
3. **規則 3(観点ごとにまとめ、各観点に値の場面)**: `test_battery_item3.py` が C3-1〜C3-19 のそれぞれに値の場面が 1 つ以上あることを
   機械で確かめる。この試験が最初の版で C3-9 に値の場面が無いこと(a9 の能力の場面だけ)を見つけたので、種つきの乱数の実行が 2 回で
   一致すると判定されるかを値で見る v9-seeded-repro を足した。→ 潰した。
4. **規則 4(動かせた道具は全部の場面に通す)**: 動かせた道具と再現は全部の場面に通し(`survey_results/opp_*.tsv` はどれも全場面の行を持つ)、
   渡せない場面は adapter が「何を探し、どこに無かったか」(道具のコードの grep = `opponents/SEARCH.tsv` と、当たりが口でない理由の行)を
   注記に残す。時間の打ち切りは 1 件も無い(`survey_results/*.tsv` の secs の列)。
   途中でリードの容量の片付け(2026-09-25 18:28 UTC、commit 08aaad4)が調査結果の側の 2 件の実行ファイル・インタプリタを消した。
   どちらも道具を読み込まずに全部の要求が「口が無い」で終わる adapter なので、最後の走行は既定のインタプリタで行い、実行ファイルの方は
   消える前に打った使い方の出力を根拠にした(どの候補かは `opponents/RUNNABILITY.tsv`・`opponents/attempts/`)。→ 潰した(経緯は記録に残した)。
5. **規則 5(最も良い結果の順)**: 判定と表の順はこの文書 §1 のとおり。複数の欄の場面で、合っている欄と欠けた欄が混ざるときの扱いを
   決めた(ある欄が違えば不一致、合っている欄だけなら結果なし)。→ 潰した。
6. **規則 6・9(検討表)**: 動かせなかった候補は観点ごとに全部を `opponents/CONSIDERED.md` に載せ、`scripts/check_bt_considered.py --write`
   で誤り 0 件にした。一次資料が読めた候補は (b) で読んで判断した。→ 潰した。
7. **規則 7(置き場)**: 場面集の試験は `tests/bt/battery/item_3/` にだけ置いた。`src/` と他の項目のファイルに触れていない
   (`git status --short` で確かめる)。→ 潰した。
8. **根拠のない設定値(A-12)**: 許容はすべて出し方を場面に書いた。閉じた式の場面(MDE・DSR)は数値の実装の差だけを許す 1e-6。
   収益の系列の DSR は、論文どおりの実装が選びうる流儀(SR の標準偏差の ddof・歪度と尖度の補正)の 4 通りで値が動く幅を許容にした。
   ブロック・ブートストラップの帯(0.85〜1.15 倍、中点 0.25 標準誤差)は、再抽出 2000 回の乱数の揺れ(分散の相対の揺れ √(2/2000) ≈ 3%、
   標準誤差で約 1.6%)と、ブロックの作り方の違い(円環 / 端を切る / 長さを乱数で決める)の差(系列の長さに対するブロックの長さ
   20 / 2000 = 1% の桁)を覆い、1 点ずつの再抽出(正解の 0.54 倍)を確実に外す幅として置いた。最初の版で DSR に置いた許容 0.002 は
   根拠が無く、式の項を落とした実装を通してしまったので外した(この吟味で見つけた)。→ 潰した。
9. **新実装に有利な偏り**: 積率だけを渡す DSR(v5-dsr)は、収益の系列だけを受ける実装を測れない。系列を渡す v5-dsr-returns を足した。
   walk-forward は「学習 5 日・評価 2 日」の形だけだと等幅の窓しか持たない実装を測れないので、等幅の v1-wf-equal を足した。
   markout は向きが片方の実装を測れるよう、買いと売りを別の場面にした。→ 潰した。
10. **断定と範囲(O-2・O-3)**: adapter の「口が無い」の文は、打った grep のコマンドと当たりの数(`SEARCH.tsv`)か、行を引いて書いた。
    adapter の文の grep は打ち直して確かめ、`deflat` の当たり 5 件(gzip の deflate)と `overfitting` の当たり 2 件
    (説明文)を最初の版の「当たり 0」から直した。→ 潰した。
11. **再現の欄の機械(規則 5 の再現の欄)**: 2 回の間で正当に変わる値(HEAD・差分のハッシュ・実行 ID)を札に置き換える処理が、最初の版では
    観測を文字列にしてから置き換えていたため、短い値が鍵の名まで書き換えた。試験(test_stable_view_keeps_equality_of_run_ids)で見つけ、
    値と鍵を 1 つずつ置き換える形に直した。→ 潰した。
12. **試金石**: `mutant.py` は purge だけを外す(ラベルの終わりを行の始まりに潰す)。独立に書いた正しい実装を包んだとき、v2-purge-embargo と
    v2-cpcv-split だけが不一致になり、ほかの要求は変わらないことを試験で確かめた(test_mutant_breaks_exactly_the_declared_scenes)。→ 潰した。

残り(この周で潰せなかったもの。批評家に見てもらう):
- 画面の場面(v16〜v19・a16・a17)は、画面をスクリプトが描く作りだと、adapter がスクリプトを実行して描かれた文を読む必要がある。
  場面は「配った中身から読む」までを決め、読み方は adapter(資料係)に任せた。
- 差分のハッシュが作業木の変化で変わることは場面にしていない(§2)。
