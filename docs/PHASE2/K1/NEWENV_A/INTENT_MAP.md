# K1 段階 A — 意図マップ(K1 の規則 1 項ずつ × 新しい環境での実装)

委任文 `docs/DATA/delegations/20260927_k1_on_new_env.md` §2-1「**同じ設計**: … K1 の規則(足の畳み方・シグナルの 4 分類と門 `s*/b*`・建玉 1 単位・決済・統計の bp の定義)1 項ずつ × 新しい環境での実装(○ / △代理 / ✕未実装 / ＋意図に無い実装)。△・✕ が残れば、その升は「比べられない」と印を付ける」。

規則の出所: `docs/PHASE2/K1/RESULT.md` 第 1 部(1.1〜1.6 = **実際に測った規則**)。`PREREG.md` §1〜§4 は設計で、第 1 部と食い違う所は第 1 部を取った(その項に書く)。当時のスクリプト `scripts/measure_katsuo_effect.py` は規則の読み取りにだけ開いた(`gates()` / `signals()` / `simulate()` / `block_bootstrap()`、`measure_katsuo_dispersion.fold`)。**算術は写していない**: 実装は核の事象の口(`bot.bt.core.Strategy.on_event`)の上に書き直し、当時のスクリプトは import していない(`grep -n "measure_katsuo\|k1_source" src/bot/strategy/k1_wick.py scripts/k1_newenv_*.py` = 0 件)。

印: ○ = 意図どおり / △ = 代理(値は出るが機構が違う) / ✕ = 未実装 / ＋ = 意図に無い実装(数に効くかを書く)。

## 1. データ(RESULT.md 1.1)

| # | K1 の規則(逐語または要約) | 新しい環境での実装 | 印 | 根拠 |
|---|---|---|---|---|
| D-1 | 出所 `backtest_data/bitmex_trade_1s_XBTUSD/`、XBTUSD、2017-01-01〜2019-12-31(1,095 日) | 同じフォルダの `2017/`・`2018/`・`2019/` の日ファイル 1,095 本を `bot.bt.data.load` で 1 日ずつ読む(`scripts/k1_newenv_fold.py: fold_year`) | ○ | `FOLD_MANIFEST.json: inputs`(1,095 件、各 path・size・sha256・rows) |
| D-2 | 読み込んだ行 **49,054,818** 秒バー | 読んだ行 = `FOLD_MANIFEST.json: rows_1s_total` = **49,054,818**(一致) | ○ | 同上 |
| D-3 | 使う列は `ts,o,h,l,c` だけ | 宣言 `fields = {open:o, high:h, low:l, close:c, volume:vol}`(データ層の足の宣言は volume が必須)。**`vol` は読むが戦略は使わない**。`buy_vol,n,max_size,n_large` は宣言せず読まない | ○(vol は ＋ だが数に効かない) | `k1_newenv_fold.py: SPEC`; `k1_wick.py` は `event.volume` を参照しない |
| D-4 | 判定区間 **2020-2021 は 1 行も読んでいない** | 許可の一覧 `AllowList(roots=(…/2017, …/2018, …/2019), extra_deny=("2020*","2021*"))`。2020-01-01・2021-12-31・別フォルダの 1 ファイルを読もうとして拒まれることを開始時に実測し記録 | ○ | `FOLD_MANIFEST.json: allowlist, refusals_proven`; 実行記録の `data_quality.json: manifest.files` は畳んだ 6 ファイルだけ |
| D-5 | (PREREG §1)「約定が無い秒は行が無い」= 既知の欠陥 | データ層は `session` を宣言しないので欠け(gap)の検査は走らない(走らせると 1 日の 76% が異常になる)。`backward`/`duplicate`/`conflict` の 3 検査は走り、**異常 0 件**(異常が 1 件でもあれば畳みは止まる設計) | ○ | `FOLD_MANIFEST.json`(`fold_year` は `anomalies` があれば `SystemExit`); 各日の `checks = [backward, duplicate, conflict]` |
| D-6 | `c <= 0` の足は飛ばす(当時の `simulate`) | データ層は価格 ≤ 0 の行を**ファイルごと拒む**(`BarEvent._validate`)。拒まれなかった = そのような行は無い → 分岐は発生しない | ○(該当行なし) | 畳みが 1,095 日すべて通った |

## 2. 足を作る(RESULT.md 1.2)

| # | K1 の規則 | 実装 | 印 | 根拠 |
|---|---|---|---|---|
| F-1 | 秒バーを UTC の壁時計で `foot` 分ごとに畳む | `bot.bt.vector.bars.bars_from_bars`(新設): start = floor(秒バーの start / (foot×60 s)) × 間隔、UTC epoch 格子 | ○ | `tests/bt/item_1/test_i1_bars_from_bars.py::test_hand_scene_60s` |
| F-2 | 始値 = 窓内最初の秒の `o`、高値 = 最大の `h`、安値 = 最小の `l`、終値 = 最後の秒の `c` | 同じ(`np.maximum.reduceat` / `np.minimum.reduceat`、先頭の `o`、末尾の `c`) | ○ | 同上 |
| F-3 | **約定が 1 秒も無い足は行を作らない** | 秒バーが 1 本も無い区間には足を作らない(区間の切れ目だけで足を作る) | ○ | 同上(00:01 の足が無いことを検査) |
| F-4 | 足の水準 1 / 3 / 5 / 15 / 30 / 60 分 | `--feet 1 3 5 15 30 60`、出力 `xbtusd_{foot}m_2017_2019.csv.gz` | ○ | `FOLD_MANIFEST.json: outputs` |
| F-5 | (K1 には無い)畳んだ足を**ファイルに書き、実行はそのファイルを読む** | 当時は秒バーをメモリで畳んで直接使った。新しい環境では実行記録に「読んだファイルの指紋」を残すため、畳んだ足を `backtest_data/k1_newenv_a_20260927/` に書き、実行記録はその sha256 を持つ。秒バー → 畳んだ足の対応は `FOLD_MANIFEST.json` が持つ(2 段の来歴) | ＋(数に効かない: 足の値そのものは同じ。書き出しは `repr(float)` なので 1 bit も落ちない) | `k1_newenv_fold.py: main`(`{b['open']!r}` …) |
| F-6 | 日をまたぐ足 | foot ≤ 60 分は 86,400 s を割り切るので、日ごとに畳んでも足の境界は同じ | ○ | 算術(60 × 60 = 3,600 が 86,400 を割る) |

## 3. 1 本の足からシグナルを決める(RESULT.md 1.3)

| # | K1 の規則(1.3 の擬似コード) | 実装(`k1_wick.py: signal_of_bar`) | 印 | 根拠 |
|---|---|---|---|---|
| S-1 | `candle = c - o`、`csign = +1/−1/0`、同値 → シグナル無し | 同じ | ○ | `tests/test_k1_wick.py::test_signal_rule_text`(同値の足) |
| S-2 | 陽線 `top = h − c, under = o − l`、陰線 `top = h − o, under = c − l` | 同じ | ○ | 同上 |
| S-3 | `int(top) > int(under)` → 売り候補(`w = top, lcprice = h`)、`int(under) > int(top)` → 買い候補(`w = under, lcprice = l`)、同値 → 無し | 同じ(`int()` 切り捨て) | ○ | 同上(0.5 vs 1 が 0 vs 1 になる場面) |
| S-4 | `wbp = w / c × 10000` | 同じ | ○ | 同上 |
| S-5 | 小門の枝 = `s != off` かつ (`s` 無し または `wbp ≥ s`) かつ `w > |candle|` | 同じ(`s` は文字列 `"off"/"-"/"10"/"19"/"30"`) | ○ | 同上(s19 通る / s30 落ちる場面) |
| S-6 | 大門の枝 = `b` あり かつ `wbp ≥ b`(実体条件を飛ばす) | 同じ | ○ | `test_gate_branches_change_which_bars_signal`(w = 実体 の足を b だけが通す) |
| S-7 | シグナル ⇔ 小門 または 大門 | 同じ | ○ | 同上 |
| S-8 | 強さ = 強い if `sig == csign` else 弱い | 同じ | ○ | `test_signal_rule_text` |
| S-9 | 門 13 通り(`s=off,b=-` は空、`s > b` は `(off, b)` と同じ規則で除外) | `gates()`: 同じ 13 通り、同じ順(`soff/b24 … s30/b40`) | ○ | `test_thirteen_gates` |
| S-10 | 族 = 6 × 13 × 3 = 234 セル | `k1_newenv_run.py` の cells(強さ both → strong → weak、足 60 → 1) | ○ | `runs_index.json`(測った升の一覧) |

## 4. 建玉を 1 単位持って回す(RESULT.md 1.4)

| # | K1 の規則 | 実装(`k1_wick.py: K1WickStrategy.on_event`) | 印 | 根拠 |
|---|---|---|---|---|
| P-1 | 行動対象 = シグナルあり かつ 強さの絞りを通った | `actionable = sig != 0 and (keep == "both" or strength == keep)` | ○ | `test_scene_a_strong_only` / `_weak_only` |
| P-2 | 行動対象でない場合、建玉あり かつ **足の色が建玉と反対**なら: 買い建玉で `終値 ≤ lcline` → 決済 invalidated、売り建玉で `終値 ≥ lcline` → 決済 | 同じ(`csign == -pos` のときだけ、終値で判定) | ○ | `test_invalidation_uses_updated_line_and_only_on_opposite_colour`(同色の足では見ない、更新後の線で判定) |
| P-3 | 同じ向きなら何も見ない(原典どおり) | 同じ(`return`) | ○ | 同上(場面 A の足 2) |
| P-4 | 行動対象: 建玉が同じ向き → 何もしない、`lcline` だけ更新(増し玉なし) | 同じ(注文を出さない) | ○ | 同上(足 1: 注文 0 本、線 3990) |
| P-5 | 建玉が反対向き → 決済。強いシグナルなら**その足の終値で逆に建て直す**(reversed)、弱いなら建て直さない(opposite_weak) | 決済の成行 `x<k>`(理由を `exit_reasons` に記録)、強いなら続けて新規の成行 `e<k>`。同じ足の終値で 2 本とも約定 | ○ | `test_scene_a_both`(足 5: x4 と e5 が同じ 3990.5)、`test_opposite_weak_closes_without_reentry` |
| P-6 | 建玉が無い → その足の終値で新規(強弱を問わず) | 同じ | ○ | 場面 A の足 0・足 4 |
| P-7 | **建値も決済値も「その足の終値」。板も気配も使っていない** | 約定の口 `BarCloseMarketFill`: 直前に受けた足の終値で成行を全量・即時に約定。核は足を**先に約定の口へ渡し、次に戦略へ届ける**(`ordering.py`: venue market data → arriving requests → deliveries)ので、戦略が出した注文は同じ瞬間に同じ足の終値で約定する | ○ | `test_scene_a_both`(e1 = 4000.5 = 足 0 の終値、時刻 = 足 0 の閉じる時刻) |
| P-8 | 建玉 1 単位 | `size = 1.0`、同方向では追加しない | ○ | 同上(fills の qty 1.0、同方向で注文なし) |
| P-9 | 1 取引のリターン `r = sig × (決済の終値 / 建玉の終値 − 1) × 10⁴` [bp] | 実行記録の `trades.json`(`round_trips`: FIFO、entry_px / exit_px / side)から `scripts/k1_newenv_tables.py: cell_stats` で同じ式を計算。**環境の指標(`pnl` = 価格差 × 数量)は使わない** | ○(式は表の生成側) | `cell_stats`; 手計算 −28.75 bp(場面 A の 1 本目)= `+1 × (3989/4000.5 − 1) × 1e4` |
| P-10 | 経費は引いていない | `costs = {maker 0, taker 0}` を設定に明記し、`DeclaredFeeCost` が 0 を返す。実行記録に `config.costs.source = 「経費は引いていない」` | ○ | `record.json: config.costs`、`fills.json` の `fee = 0.0` |
| P-11 | 最後の足で開いたままの建玉は取引にならない(当時の `simulate` は決済時にだけ trades に足す) | `round_trips` は閉じたロットだけを取引にする | ○ | `test_scene_a_weak_only`(建玉が残り trades = []) |
| P-12 | (PREREG §4.2)上限 96 本で打ち切る | **第 1 部 1.4 の規則に無く、当時のスクリプト `simulate()` にも無い**(PREREG 4.1-a は「上限 96 本はほぼ効いていない(到達 0.0〜0.1%)」)。第 1 部に合わせて**実装しない** | —(測った規則に無い) | RESULT.md 1.4 / 1.6 に記載なし |

## 5. 統計(RESULT.md 1.5)

| # | K1 の規則 | 実装(`scripts/k1_newenv_tables.py`) | 印 | 根拠 |
|---|---|---|---|---|
| T-1 | `mean(r)`、標準偏差 | 同じ式(標本標準偏差、n − 1) | ○ | `cell_stats` |
| T-2 | 保有本数の中央値 | 決済の足の index − 建玉の足の index(index は実行が読んだ足ファイルの行番号。約定の無い足は存在しない)、`sorted(holds)[n // 2]` | ○ | `bar_index` / `cell_stats` |
| T-3 | 決済理由の内訳 | `trades.json` の `reason`(invalidated / opposite_weak / reversed) | ○ | `record.json` には理由の元 `exit_reasons` は無いが、`trades.json` の各行に載る |
| T-4 | 年ごとの平均 | 建玉の足の UTC 年で分ける | ○ | `cell_stats: per_year` |
| T-5 | 95% 信頼区間 = 日単位のブロックブートストラップ(入口の日でブロック、日を復元抽出、200 回、種 20260909) | **環境の `bot.bt.validation.bootstrap.block_bootstrap_ci` は固定長ブロック(block_len)で、日ブロックではない。** 規則の文どおりの日ブロックを表の生成側に書いた(`block_bootstrap`)。乱数は `random.Random(20260909)` 1 本を K1 の周回順(足 1→60、門、強さ strong→weak→both)で使う | △(環境の機構ではなく表の生成側の統計。`*` の印は代理) | `k1_newenv_tables.py: block_bootstrap`。**2.1〜2.3 の `*` は「比べられない(代理)」の印付き**(平均の値そのものは ○) |
| T-6 | 取引 30 件未満のセルは出力しない | 同じ | ○ | `cell_stats` が `None` |

## 6. ＋ 意図に無い実装(新しい環境が足すもの。数に効くかを書く)

| # | 何を足すか | 数に効くか | 根拠 |
|---|---|---|---|
| X-1 | 核の注文の流れ(OrderRequest → Ack → Fill → FillNotice → 費用の口 → 口座の口) | 効かない(約定値は足の終値、費用 0、口座は `NullAccount`) | 場面 A の fills が手計算と一致 |
| X-2 | 遅延 `ZeroLatency`(全 0 ns) | 効かない | 同上 |
| X-3 | 実行を 2 回回して全出力を byte 比較(`runner.run`) | 効かない(同一でなければ止まる) | 各 `repro.json: identical = true` |
| X-4 | データ層の検査(backward / duplicate / conflict)と価格の検証 | 効かない(異常 0 件) | `data_quality.json: anomalies = []` |
| X-5 | `seed`(記録に必要)| 効かない(K1 は乱数を引かない。`notes.seed = "unused"`) | `record.json: components.notes` |
| X-6 | 畳んだ足のファイル化(F-5) | 効かない(`repr(float)`) | F-5 |

## 7. 「比べられない」升

- △ は **T-5(`*` の印)だけ**。したがって **2.1〜2.3 の平均の値は全升で比べられる**が、**`*` の一致・不一致は代理の統計の一致であり、環境の検査にはならない**(DIFF.md では `*` を別欄に置く)。
- ✕ は無い。
- P-12(上限 96 本)は「測った規則に無い」ので実装せず、比較の対象外。
