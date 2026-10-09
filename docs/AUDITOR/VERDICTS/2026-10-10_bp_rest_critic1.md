# 批評家 1 回目 — bp の残りの直し(L-925、作業者 w1〜w5 とリードの直しの未コミットの差分)

- 批評家: 委任先の下位モデル(Agent の道具、裏で)。書き換えはしない。問 0〜6(問 0 = オーナーの目的に答えるか・計算の結果が変わっていないか)
- 対象: 作業木の未コミットの差分 163 ファイル(コミット 44aff2b1 の時点)と、作業者の報告 `docs/DISCUSSIONS/2026-10-09_bp_units/codefix_rest_w1〜w5.md`
- 以下は批評家の出力の逐語。応答は末尾の表。

## 逐語

### 問 0(オーナーの目的に答えているか / 計算の結果が変わった所)
差分の大部分は、名前を `_pct` にして `×1e4 → ×100` にした直し。報告にある新旧の突き合わせ(w1〜w5)と、私の抜き取りの範囲では、判定・閾値・群の所属が変わった所は見つからなかった。

確かめたもの:
- 障壁の換算で浮動小数の値が変わらないか(`scripts/research_vr_barrier.py`)。
  `python3 -c "print(1+0.10/100==1+10.0/1e4, 1+0.05/100==1+5.0/1e4, 1-0.10/100==1-10.0/1e4, 1-0.05/100==1-5.0/1e4)"` → `True True True True`(事実)。
- `ECON_BREAKEVEN` は % どうしの比なので、単位を変えても値は同じ(読んだだけ)。

**指摘 0-1 [聞く]**: Jev に渡す文が変わる。
- 場所: `scripts/o3c_jev_state.py` の `_sent11`(`{d:.0f} bp away` → `{d:.2f} % away`)と、材料の鍵 `distance_to_liquidation_node_pct`(`o3c_signal_continue_jev` の `materials[MAT_VAR[5]]`)。出所は w3 報告の「続き 2」C の項・「続き 3」の表。
- Jev は文を読んで判定するので、同じ入力でも出る確率や判定は前と同じとは限らない【推定】。保存済みの Jev の答えとは、別の問いになる(w4 の迷ったこと 4 も同じ件)。
- 単位を直す以上、避けられない変化だと読む。走らせ直すか、前の答えを使わないと明記するかは、リードが決めること。

### 問 1(換算の取り違え・/100 を二重に掛ける所)
指摘は無い。確かめた内容:
- `/ 100` を足した行を全部出し、条件付きでないものを目で見た。
  `git diff -U0 -- '*.py' '*.js' | grep -E '^\+[^+]' | grep -E '/ ?100(\.0)?\b' | grep -vE 'if .*(not )?in|\.get\(|else|fillna|legacy|old'`
- 残った行を 1 つずつ見た。どれも「新しい名前が無いときだけ割る」か、1 レグの bp を和の表に入れるために割るもの(`c9_redo.py:318`。1 レグの断片は bp のままの決め)。新しい出力を二重に割る所は無かった。
  - 例: `p2_01_run.py:836-839`(`mean_r_net_pct_conservative` があればそれ、無ければ `_bps / 100`)、`p2_01_final.py:300-303`、`c9_redo.py:55-56`。
- `p2_08_run.read_prev_csv`(203-217 行)は、名前に単位の無い `ci_lo`・`ci_hi`・`se_cluster` を、`mean_net_bps` があって `mean_net_pct` が無い古い形のときだけ割る。
  git に入った読み先の見出しを確かめた: iter0・iter1 の `configs.csv` と `sensitivity_val_2022_only.csv` は `mean_net_bps` を持ち、`null_best_of_*.csv` は `ci_*` を持たない。取り違えは無い(事実)。

### 問 2(1 つの列・表・文の中に bp と % が混ざる所)
**指摘 2-1 [直す]**: `scripts/analysis/diag_tables.py` の表示の桁が、% の出力に合っていない。
- この差分で `load_run` が率(%)の出力も読むようになった(`_rate_pct`、`unit` = "円" か "%")。
- ところが表示は円のときの桁のまま。和は `_f(...,0)`(小数 0 桁)、1 日あたりと 1 取引あたりは `_f` の既定の小数 2 桁。
  - `render` の D3 の全体・上位・下位の和、群の和、D6 の和、D7 の突き合わせの和、D8 の決まらない足の和(diff の 486 行より後)。
- 確かめたもの: `python3 -c "print(f'{0.0042:+.0f}', f'{0.0121:+.2f}')"` → `+0 +0.01`。
  % では、和は 1 %(= 100 bp)刻み、1 取引あたりは 0.01 % 刻みになり、ほぼ情報が残らない。単位を混ぜる誤りではないが、表の値が読めなくなる。
- 判定に使う `stop` は符号で決まるので、判定そのものは変わらない(読んだだけ)。
- なお w5 の報告は「`diag_tables.py` は変えていない」「今の `load_run` は率の出力で止める」と書いているが、作業木の `diag_tables.py` は変わっていて、率の出力を読むようになっている(`git diff --stat scripts/analysis/diag_tables.py` → `87 insertions(+), 51 deletions(-)`)。誰がいつ直したかは、報告からは分からない。

### 問 3(書き手を変えたのに読み手が古いままの所)
指摘は無い。確かめた内容:
- 差分の `-` 行にあって `+` 行に無い bp 付きの名前 216 個を、git に入った `.py`・`.js` 全部で grep した。まだ使っている名前は 16 個。
- 16 個を 1 つずつ見た。どれも次のどれかで、変えた書き手を古い名前で読む所は無かった。
  - 別の書き手の、値動き率の列(例: p2_03 の `sd_bps`・`se_bps`・`mde_bps_*` は `r_night_bps` のグロス)
  - 文書の中の語(`20260920_o3c_cascade_read.py` の 249・482 行)
  - 変えていない台本(`maker_fill_ref*.py`。下の 4-1)
- 定数と鍵の古い名前(`realized_round_trip_bps`・`COST_BURST_BPS`・`node_ahead_bp_batch` ほか 12 個)の grep の当たりは、説明のコメント 3 行だけ。
- 封印済みの帯 `config/o3c_jev_state_bands.yaml` の `oi_ahead_20bp` は、建玉の量の五分位。名前を写すだけで割らないのが正しい(`o3c_jev_state.py:212-219`)。
- 封印の置き場を外した `git ls-files` で作った一覧に対して打った。

### 問 4(決めとの食い違い)
**指摘 4-1 [聞く]**: 同じ量なのに、台本によって単位が違う。
- `scripts/qa/maker_fill_ref.py:284`・`maker_fill_ref_packet.py:234`・`maker_fill_ref_packet_r2.py:288` は差分に無く、`net_bps = sign*(exit-entry)/entry*1e4` のまま。
- これが再現する `make_known_answer_maker3.py` の建玉ごとの `net_bps` は、w2 が `net_pct` にした。式は同じ。
- 量 1 の 1 回の建てから出まで(費用の差し引き無し)として bp に残すのか、名前が「net」で約定の値段を使うので % にするのか。どちらにそろえるかが決まっていない。

**指摘 4-2 [直す]**: グロスが % になっている。
- 場所: `scripts/phase2/g1_state_analysis.py:379-381`。`values = values_all[keep] / 100.0` で、グロス(`r_night_bps`、量 1・費用前)を % にしている。
- その結果、`gross_ci` と表の「無条件グロス平均 [CI](%)」もグロスが % で出る。リードの決め「グロス(量 1、費用前)は bp」と食い違う。
- 費用付きの `state_split` は % で正しい。p2_08・p2_04・p2_01b は、グロスの脚を bp に戻すか、脚ごとに単位を持たせてそろえてある。

**指摘 4-3 [聞く]**: レンジの縁からの障壁・距離を % にした所。
- w4 の迷ったこと 1 と同じ件: `research_vr_barrier.py` の `BARRIERS`、`research_calm_range`・`research_range_reversed`・`research_fx_sessions` ほか。
- 入りの約定から測る TP は bp のままなので、そろっていない。range_reversed の `tp_dist` だけが %。
- 判定は変わらない(上の浮動小数の確かめ)。名前と単位をどちらにするかの読みはリードが決めること。

### 問 5(封印の置き場・関門の門)
指摘は無い。
- `git diff --stat -- src/bot/research/sealed.py scripts/_research_audit_gate.py .claude githooks docs/AUDITOR/HOOK_MANIFEST.sha256 docs/ANALYSIS docs/OWNER_LOG.md docs/OWNER_STATUS.md` → `p2_02_final.py` 以外は出力なし。
- `p2_02_final.py` で変わった所の始まりは 89 行と 404 行より後だけ(`git diff -U0 scripts/phase2/p2_02_final.py | grep '^@@'`)。`check_guards` は 123 行から。門の中は変わっていない。
- 足した行の中で封印の置き場や門を呼ぶ所: `git diff | grep -nE '^[+-].*(phase2_sealed|WINDOW1|load_sealed|load_unsealed|check_guards|UNSEAL)'` → 出力なし。
- 台帳に載ったファイルの変更: 差分のファイルを 1 つずつ `HOOK_MANIFEST.sha256` と照らした → 当たりなし。
- 新しい `trade_rows.check_dir` は `diag_tables.load_run` と同じ `WINDOW_MARK` の文字列で止める。

### 問 6(試験の確かめが弱くなった所)
指摘は無い。1 か所だけ確かめ方が変わったので書く。
- `tests/test_phase2_p2_04.py:679-723` は、バイトが同じことの確かめを、数値の比べ(`rtol` 1e-9・`atol` 1e-12)に変えた。リードの決めでしたもの。
- 列の名前と並びは完全に一致することを求めている(689 行)。÷100 する列は試験の中に名指しで並べてあり、漏れや余分があれば落ちる形。文字の列は完全一致。強さはほぼ保たれていると読む【推定】。
- ほかの試験の許す差の変更は、どれも 1/100 の換算どおりだった(`git diff -U0 -- tests/ | grep -iE 'approx|abs=|rel=|tol|...'` で全部の行を見た)。

### 試験
- 変えたモジュールに関わる試験 53 本(p2_04 を除く)を `PYTHONPATH=src python -m pytest -p no:cacheprovider <53 本>` で回し始めたが、上限のため 24% で止めた。そこまでに落ちた試験は無い。
- 残りは**未確認**。作業者の報告にある試験の結果は、私は回し直していない。

### 指摘の数
5 件([止める] 0・[直す] 2・[聞く] 3)。
- [直す]: 2-1・4-2
- [聞く]: 0-1・4-1・4-3

## 応答

| # | 応答 |
|---|---|
| 0-1 | リードの判断: 単位を直す以上、避けられない変化。前の Jev の答え(bp の文で問うたもの)は、新しい出力(% の文)と組み合わせて使わない。走らせ直すのは、Jev が届くようになり、その問いを次に使うときにする(今は 402 で届かない) |
| 1 | 指摘なし |
| 2-1 | 直した。`diag_tables.py` の `_f` に最小の桁 `_MIN_ND` を置き、`render` が % の出力のときだけ 4(0.0001 % = 0.01 bp)にした。円の出力の桁は変わらない(読み口の試験 17 本通過)。`diag_tables.py` を率の出力も読む形に直したのはリード(w5 の報告の後。w5 の報告の判断待ち 1 への応答) |
| 3 | 指摘なし |
| 4-1 | リードの判断: 2 つの約定の値段の間の往復は、スプレッドの取り分が入るので値動き率ではない(w4 の 1 単位の往復と同じ扱い)。`maker_fill_ref.py`・`_packet.py`・`_packet_r2.py` の `net_bps` を `net_pct`(× 100)にそろえた。markout(約定の後 5 秒の仲値の動き)は bp のまま。試験 `tests/test_qa_maker_fill_ref.py` は、前の答え(bp)を / 100 して比べる形に合わせた(52 通過・1 飛ばし) |
| 4-2 | 直した。`g1_state_analysis.py` で、無条件のグロスの平均と区間を bp(÷100 する前の値)で出し、表の見出しを「(bp)」に、要約の鍵を `uncond_mean_bps`・`uncond_ci_*_bps` にした。費用後と状態の分けは % のまま |
| 4-3 | リードの判断: w4 の読みを認める。レンジの縁からの距離は同じ時刻の 2 つの値段の距離なので %、入りの約定から測る利確・損切りは値動き率なので bp。range_reversed の `tp_dist` は、台本の中で「利確に届いたときの 1 本の取り分」として費用(%)と引き算に使うので % のまま |
| 6 | 指摘なし |
