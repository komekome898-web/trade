#!/usr/bin/env python3
"""段 A「清算の後の反応」の**結果の読み**(事前登録どおりに読むだけの道具)。

**判定区間を開ける前に書いた。**開封の後に読み方を書くと、出てきた数値に合わせて
読み方を調整できてしまうため(`CLAUDE.md` §0.2 の A-6「判定バーを開封後に動かさない」)。

**出所**: `docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md`(確定版・凍結)。
本ファイルは事前登録の次の節を実装したものである。**事前登録は書き換えていない。**

  §4    16 軸 = 48 群と、どの走行から取るか
  §4.3  判定の対象 = F1 の戻り到達 2 系統 × 48 群 × h 6 = 576 検定、α = 0.05/576
  §6.1  対照 (i) の、向きの要る量の重み付け
  §7.0  F1 の 12 セルの読み(4 分岐)
  §8.5  MDE の計算式と入力
  §8.6  p・s は標本 6 日で固定、n は走行後の群の件数
  §9    バー |t| ≥ 3.925、n < 30 → 不明、台地条件は隣の分位の併記
  §9.1  UTC 日クラスタのブートストラップ 2,000 回・種 1
  §10.1 576 行の表の列の順と分岐
  §10.2 観測のみの表(t と判定の列なし。前進到達を入れない)
  §10.3 「なぜ」の欄の形

**関門**(`CLAUDE.md` §5.0 の 2): 表を 1 枚も書く前に
`scripts/_research_audit_gate.py: require_audit(<unit>, "結果")` を通す。
**迂回する旗は作っていない。**

**`--root` は台帳の場所を差し替える引数である(試験用)**(走行前の再監査(4 回目)の指摘 10。
リードの決定。**前版は「台帳の場所を差し替えるだけのもので、関門そのものを外さない」と
書いていたが、`require_audit` が読むのは `<root>/docs/AUDITOR/ACTION_LOG.md` そのものなので、
別の台帳を指させば別の判定が読まれる**)。
**機械**: `--out-dir` がリポジトリの `backtest_data/` の下にあるとき、
`--root` がリポジトリ直下以外なら「[止め]」で終了コード 1(**本番の出力に試験用の台帳を使えない**)。
使った root は `summary.json` に記録する。

**判定語(予測できる / 使える / 有効)は出力に 1 つも書かない**(事前登録 §10.1 の末尾)。
**「差なし」「陰性」も書かない**(走行前の再監査の決定 2)。
**走査は表を書く前に、メモリ上の行と文字列に対して行う**(走行前の再監査(4 回目)の指摘 11。
**前版は 7 ファイルを書き終えた後に走査していたので、見つかっても書いた表が残っていた**)。
書き出した後にもう一度走査する(二重の網)。

**走行前の再監査(2 回目)で決めた 7 点**(事前登録の本文は別の委任先が同じ決定で直す。
**本ファイルは事前登録を書き換えていない**):

  1. CI は正規近似 `差 ± z × ブートストラップ SE`。2,000 回・種 1 は SE の推定に使う。
     よって「|t| ≥ z」と「CI が 0 を除外」は同値である。→ `bootstrap_diff` / `ci_normal`
  2. 分岐は 3 つ: 実群 n < 30 →「不明(n < 30)」/ |t| ≥ z →「差あり(+)(−)」/
     それ以外 →「検出されず(MDE = X)」。→ `decide`
  3. 3 分位の切り値は判定区間の実群の `np.nanpercentile([100/3, 200/3])`、同点は下側、
     欠測はどの群にも入れない。切り値が等しければ中の群は空。空の群も 576 行に出す。
     → `tertile_cuts` / `_quantile_label`
  4. MDE の p・s は、判定区間の切り値を標本 6 日の行に当てて分けた群から取る
     (標本で切り直さない)。n は走行後の群の件数。`alpha` は直接渡す。→ `mde`
  5. F1 の 12 セルの読みは 差あり(+) / 差あり(−) の件数で決め、不明のときは内訳を併記する。
     → `f1_reading`
  6. W に依らない 12 群は W8h の走行からだけ 576 に入れ、W24h 側の同じ 12 群は
     観測のみの表に出す。→ `build_groups` / `build_flat_groups_w24`
  7. 「全体」群の 実群 列は差の入力として出すが、その水準を根拠にした文を書かない
     (事前登録 §3 の #1 = a)。→ `main` の標準出力と `summary.json` の注記

**走行前の再監査(3 回目)で決めた 8 点**(同じく事前登録の本文は別の委任先が直す):

  1'. 対照 (ii) の軸の値の作り方を 3 通りに分ける(指摘 1。→ `control_axis_kinds`):
      **自前(own)** = 対照行にその列の値がある(`bin_pct` / `doi_pre_1h`)。
      **相手の符号(partner_sign)** = 対照行に**符号なしの大きさ**がある(A2〜A5 の 24 群)。
      1 対 1 の相手の実群の `side` の符号(`LIQ_SIGN`)を当てて対照自身の軸の値を作る。
      **受け継ぐ(inherit)** = 対照行に対応物が無い(E の 6 + B1 3 + B2 3 + C 2 = **14 群**)。
  5'. 対照 (ii) の `*_reactdir` は相手の実群の側の符号を当てる(指摘 5。→ `Run.values`)。
  6'. 1 対 1 の対応は `matched_liq_id` 列で取る(指摘 6)。**連番の算術による復元はやめた。**
      走行ごとに **サニティ #14**(相手が実在 / 同日 / `bin_pct` の差が許容内)を通す。
      → `check_pairing`
  8'. 相手が mixed 束の合わせた対照は**全群から落とす**(指摘 8。→ `Run.mat_usable`)。
  11'. `summary.json` に観測のみの表の行数・受け継いだ群・落とした対照の件数を出す(指摘 11)。
  12'. `z` は 1 本(`norm.ppf(1 − α/2)`)。バー・CI・MDE のすべてに同じ値を使う(指摘 12)。
  17'. MDE が計算できないセルは「**不明(MDE 未算出)**」にする(指摘 17。→ `decide`)。
  19'. `--sens NAME=DIR` で感度 4 本の観測のみの表を別ファイルに出す(指摘 19)。
  20'. W = 24h 側の 12 群(観測のみ)は **W = 24h の実群で切り直した切り値**を使う(指摘 20)。

**走行前の再監査(4 回目)で決めた点**(同じく事前登録の本文は別の委任先が直す):

  1''. `t` が非有限のセル(SE = 0 / 有限な複製 < 2)は「**不明(t 未算出)**」(指摘 1。→ `decide`)。
       **「検出されず」にしない**(検定量が出ていない行を不在の側に読ませないため = A-18)。
  2''. SE の推定に使えた**有限な複製の本数**を列 `有限な複製の本数` に出す(指摘 2。→ `bootstrap_diff`)。
       `summary.json` に最小の有限な複製の本数も出す。**閾値は置かない**(A-12)。
  3''. 対照 (ii) の軸の作り方は**事前登録で固定**した(指摘 3。→ `AXIS_KIND_FIXED` / `check_axis_kinds`)。
       走行ごとに測った結果が固定と違えば「[止め]」で終了コード 1。**黙って合わせない。**
  10''. `--root` の機械(上の「関門」)。使った root を `summary.json` に残す(指摘 10)。
  11''. 判定語の走査は**表を書く前**にメモリ上の行と文字列へ当てる(指摘 11。→ `scan_rows_forbidden`)。
  12''. サニティ #14 に**一意性**を足す(指摘 12。→ `check_pairing`):
        `matched_liq_id` が重複しない / 対照の件数 = 引けた相手の件数(mixed 相手を含めて)。
  13''. 各走行の #14 の結果を `summary.json` に残す(指摘 13)。
  14''. 列 `バー近傍`(`|t|` が z ± 0.065 に入るとき ○)を足す(指摘 14)。**観測のみ。判定は変えない。**
  15''. `mde()` から `alpha` の枝を消し、**z は定数 1 本**(`MDE_Z`)だけにする(指摘 15)。
  20''. `n2 < 30` も「**不明(n2 < 30)**」にする(指摘 20。→ `decide`)。
  22''. 列 `対照(ii)の軸の作り方`(own / partner_sign / inherit)を両方の表に足す(指摘 22)。
  8''. `--sens NAME=DIR[:SAMPLE_DIR]`。標本を渡した感度は MDE 列を出す(指摘 8)。

**走行前の再監査(5 回目)で決めた点**(同じく事前登録の本文は別の委任先が同じ決定で直す):

  1'''. **反復回数と種は定数**(`REPS = 2000` / `SEED = 1`)。**引数では変えられない**(指摘 1)。
        **前版は `--reps` / `--seed` を引数で受けており、凍結値と違っても止まらなかった。**
        **開封の後に反復を引き直して読みを取り直せる経路だったので、引数ごと消した**(A-6)。
        `summary.json` には「定数(引数では変えられない)」と書いて残す。
  2'''. **サニティ #14 は標本の走行にも掛ける**(指摘 2。→ `main`)。
        `--sample-w8` / `--sample-w24` / `--sens` の `:SAMPLE_DIR` が対象で、
        **破れれば「[止め]」で終了コード 1**(MDE の `p`・`s` の母集団が黙って変わるのを止める)。
  3'''. **`summary.json` の「MDE 列が空の理由」は「`:SAMPLE_DIR` を渡していない」と書く**(指摘 3)。
        **「在庫に無い」とは書かない**(この道具は在庫を 1 度も見ていない)。
        渡した標本ディレクトリの一覧も `summary.json` に残す。
  12'''. **走行の `summary.json` の `params` を名前と突き合わせる**(指摘 12。→ `check_run_params`)。
        判定の 2 本 = `mode: full` / gap 60 秒 / W 8h・24h / 日数 456。
        標本 = `mode: sample` / 日数 6。感度 = `mode: full` / 日数 456 / gap と W は名前のとおり。
        **食い違えば「[止め]」で終了コード 1。迂回する旗は作っていない。**
  16'''. **有限な複製の本数が `REPS` に満たないセルの一覧**(観測量・群・h・本数)を
        `summary.json` に出す(指摘 16)。**閾値は置かない**(A-12)。

**走行前の再監査(6 回目)で決めた点**(同じく事前登録の本文は別の委任先が同じ決定で直す):

  1''''. **`params` の検査に `mmr` / `seed` / `bin_pct` / `match_order` を足す**(指摘 1。
        判定 2 本・感度 4 本。→ `check_run_params(..., settings=True)`)。
        **前版はこの 4 つを見ていなかったので、`--mmr` を付け忘れた走行でも
        48 群・576 行を通り、軸 E の 72 行が黙って「不明(n < 30)」になった。**
  2''''. **`--approval` の L 番号は事前登録 §14.4 の「応答の L 番号」の欄から読む**(指摘 2。
        → `read_approval_from_prereg`)。**欄が埋まっていなければ「[止め]」。**
        判定 2 本の `params.approval` がそれと違えば「[止め]」。
  4''''. **`REPS` / `SEED` を `main()` の冒頭でリテラルと突き合わせる**(指摘 4)。
        **引数を消しただけでは閉じていなかった**(モジュール属性への代入で差し替えられた)。
  5''''. **「検出されず(MDE = X)」に単位を付ける**(指摘 5。→ `MDE_UNITS` / `mde_unit`)。
        系統ごとの固定表(到達率 = 割合 / bp 系 = bp / 秒 = 秒 / ΔOI = 枚)から付ける。
  7''''. **感度の表の MDE の列見出しを `MDE(参考。族の α に入らない)` にする**(指摘 7)。
  8''''. **`check_axis_kinds` を標本の走行にも掛ける**(指摘 8)。
  9''''. **標本側の `params` の検査に `window_hours` と `gap_ms` を足す**(指摘 9)。
  12''''. **本数の一覧から「群が空 / n < 30 で検定していないセル」を除き、
        その数を別の欄に出す**(指摘 12)。
  13''''. **F1 の 12 セルが揃わなければ「[止め]」で 1 ファイルも書かない**(指摘 13)。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np

# --- 事前登録で凍結された定数(走行の後に動かさない)-------------------------
HORIZONS = (1, 5, 15, 30, 60, 240)          # §4.1 h 6 本
N_TESTS = 576                                # §4.3 2 系統 × 48 群 × h 6
ALPHA = 0.05 / N_TESTS                       # §4.3 / §8.2
POWER = 0.80                                 # §8.2 検出力(仮定・委任先)
MIN_N = 30                                   # §9 の項 1(欠測を引いた後の実群の件数)
N_GROUPS = 48                                # §4
RUN_W8 = "gap60_w8"                          # §14.1 判定に使う走行
RUN_W24 = "gap60_w24"
UNIT = "o3c_reaction_20260918"               # 関門の単位名
# **決定 1'''(走行前の再監査(5 回目)の指摘 1)**: 反復回数と種は**定数**である。
# **前版は `--reps` / `--seed` を引数で受けていたので、開封の後に反復を引き直して
# 読みを取り直せた**(§9.1 は「走行の前に決めた 2,000 回を走行の後に変えない」と書き、
# 「|t| が 3.86〜3.99 に入る検定では反復の引き直しで判定が変わりうる」とも書いている)。
# **引数ごと消した。**この 2 つを変えるにはこのファイルを書き換えるしかなく、差分に残る。
REPS = 2000                                  # §9.1 反復回数(凍結)
SEED = 1                                     # §9.1 種(凍結)
# **決定 4''''(走行前の再監査(6 回目)の指摘 4)**: 上の 2 つは**モジュールの属性**なので、
# ファイルを書き換えなくても import して代入すれば差し替えられる(**6 回目の監査が実測した**)。
# **`main()` の冒頭でリテラルと突き合わせる。**下の 2 つがその相手である。
REPS_FROZEN_LITERAL = 2000                   # §9.1(突き合わせの相手。ここも書き換えれば差分に残る)
SEED_FROZEN_LITERAL = 1
# **決定 12'''(同 5 回目の指摘 12)**: 渡されたディレクトリが名前どおりの走行かを
# `summary.json` の `params` で見る(`scripts/o3c_reaction.py` が書く鍵)。
JUDGMENT_N_DAYS = 456                        # §3 判定区間の日数
SAMPLE_N_DAYS = 6                            # §8.6 標本の日数
GAP_SEC_JUDGE = 60                           # §14.1 判定に使う走行の gap
WINDOW_HOURS_FIXED = {RUN_W8: 8.0, RUN_W24: 24.0}
# **決定 2'''''(走行前の再監査(7 回目)の指摘 2)**: 感度は §14.2 の 4 本をすべて渡す。
# **1 本でも欠ければ「[止め]」**(感度の検査が破れても判定の表は書くようにしたので、
# 「渡さなければ検査もされない」形を先に塞ぐ)。
SENS_REQUIRED = ("gap30_w8", "gap180_w8", "gap30_w24", "gap180_w24")
# **決定 1''''(走行前の再監査(6 回目)の指摘 1)**: 凍結した入力のうち、
# §14.5 の決定 3 が「6 本すべてに付ける」と書いた `--mmr` と、§14.1 が「主指標に効く」と
# 書いた `--seed` を、前版の `params` の検査が見ていなかった(**6 回目の監査の実測**:
# `implied_leverage` が空でも 48 群・576 行を通り、E 群の 72 行が黙って「不明(n < 30)」になった)。
# **判定 2 本と感度 4 本には、下の 4 つも突き合わせる。**
MMR_FIXED = 0.004                            # §14.5 の決定 3(`--mmr 0.004` を 6 本すべてに)
RUN_SEED_FIXED = 1                           # §14.1(`--seed 1` を 6 本すべてに)
BIN_PCT_FIXED = 0.1                          # §14.4.1 の埋め込みスクリプトと同じ既定
MATCH_ORDER_FIXED = "table"                  # §6.2(本走行の順。`reversed` は順序依存の実測用)
# **決定 2''''(同 6 回目の指摘 2)**: `--approval` に渡す L 番号は、事前登録 §14.4 の
# 「応答の L 番号」の欄から読む。**欄が埋まっていなければ「[止め]」。**
PREREG_REL = "docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md"
# 欄の形は **応答の L 番号**: **L-NNN**(埋まっていなければ **(まだ無い…)**)。
# **行の形ごと固定する**(本文の他の場所にある「応答の L 番号」という語を拾わないため)。
APPROVAL_FIELD_RE = re.compile(
    r"^[ \t>]*\*\*応答の L 番号\*\*\s*[:：]\s*\*\*(.+?)\*\*\s*$", re.MULTILINE)
APPROVAL_VALUE_RE = re.compile(r"^L-\d+$")
# **決定 16(prereg 監査(8 回目)の指摘 16)+ 決定 3(10 回目の指摘 3)**: 事前登録 §14.4 の
# 「凍結した道具のコミット」の欄。**この道具自身の
# `git log -1 --format=%H -- <道具 2 ファイル>` と突き合わせ、違えば「[止め]」。**
# **欄が「(まだ無い)」でも「[止め]」である**(9 回目の指摘 3 で変えた)。
COMMIT_FIELD_RE = re.compile(
    r"^[ \t>]*\*\*凍結した道具のコミット\*\*\s*[:：]\s*\*\*(.+?)\*\*\s*$", re.MULTILINE)
COMMIT_VALUE_RE = re.compile(r"^[0-9a-f]{7,40}$")
# §10.1 の判定語 + 走行前の再監査(2 回目)の決定 2 で禁じた語。**出力に 1 つも書かない。**
FORBIDDEN = ("予測できる", "使える", "有効", "差なし", "陰性")

_ND = NormalDist()
# **z は 1 本だけ**(走行前の再監査(3 回目)の指摘 12。リードの決定)。
# 丸めた 3.925 と `norm.ppf(1 − α/2)` を使い分けると、同じ α の z が 1 つの判定の中で
# 2 通りになる(§5「同じ量が 2 か所で別の桁に見えないようにする」)。**バー・CI・MDE の
# すべてがこの `Z_ALPHA` を使う。**本文の「3.925」は丸め表示であって、計算はこの値である。
Z_ALPHA = _ND.inv_cdf(1 - ALPHA / 2)         # 3.9247896514056540...
BAR_T = Z_ALPHA                              # §9 の項 3(両側 α に対応する z)
Z_POWER = _ND.inv_cdf(POWER)                 # 0.8416212...
MDE_Z = Z_ALPHA + Z_POWER                    # §8.1 の (z_{1-α/2} + z_{1-β})
BAR_T_SHOWN = "3.925"                        # 文面に出す丸め表示(計算には使わない)

# 合わせた対照 (ii) のマッチングの許容(`scripts/o3c_reaction.py:140` の
# `MATCH_TOL_PCT = 5.0` を読んで書いた。**実測**)。サニティ #14 で使う。
MATCH_TOL_PCT = 5.0
# 清算の向きの符号(`scripts/o3c_oi_distance.py:127` の `LIQ_SIGN`。**実測**)。
LIQ_SIGN = {"SELL": 1.0, "BUY": -1.0}
# `*_liqdir` 列 -> その符号なしの元の列(`scripts/o3c_oi_distance.py:87` の
# `LIQDIR_SOURCE` を読んで書いた。**実測**)。対照行には**元の列だけ**値がある。
LIQDIR_SOURCE = {
    "dist_vwap_bp_liqdir": "dist_vwap_bp",
    "dist_node_bp_liqdir": "dist_node_bp",
    "oi_dist_vwap_bp_liqdir": "oi_dist_vwap_bp",
    "oi_dist_node_bp_liqdir": "oi_dist_node_bp",
    "oi_side_dist_vwap_bp_liqdir": "oi_side_dist_vwap_bp",
    "oi_side_dist_node_bp_liqdir": "oi_side_dist_node_bp",
}
# 対照 (ii) の軸の値の作り方(走行ごとに**測って**決める。決め打ちにしない)。
AX_OWN = "own"                   # 対照行にその列の値がある
AX_PARTNER_SIGN = "partner_sign"  # 対照行に符号なしの大きさがある -> 相手の側の符号を当てる
AX_INHERIT = "inherit"           # 対照行に対応物が無い -> 1 対 1 の相手の群を受け継ぐ

# **決定 3''(走行前の再監査(4 回目)の指摘 3)**: 対照 (ii) の軸の作り方は
# **事前登録(§4)で固定**する。**前版は走行ごとに測った結果をそのまま使っていたので、
# 判定区間で内訳が 10/24/14 と違って出ても黙って進んだ。**
# 本版は測った結果をこの固定と突き合わせ、**違えば「[止め]」で終了コード 1**。
# **黙って合わせない**(リードの決定の逐語: 「**スクリプトは走行ごとに測った結果が
# この固定と一致しなければ「[止め]」で終了コード 1(黙って合わせない)**」)。
#
# リードの決定の逐語は partner_sign を**符号なしの元の列**の名前で書いている
# (`dist_node_bp` / `dist_vwap_bp` / `oi_dist_node_bp` / `oi_dist_vwap_bp`)。
# §4 の軸の列はその `*_liqdir` 版なので、`LIQDIR_SOURCE` の対応で読み替えて置いた
# (**1 対 1 に対応する。読み替えたことをここに書く**)。
AXIS_KIND_FIXED: dict[str, str] = {
    "bin_pct": AX_OWN,
    "doi_pre_1h": AX_OWN,
    "dist_node_bp_liqdir": AX_PARTNER_SIGN,      # 元の列 dist_node_bp
    "dist_vwap_bp_liqdir": AX_PARTNER_SIGN,      # 元の列 dist_vwap_bp
    "oi_dist_node_bp_liqdir": AX_PARTNER_SIGN,   # 元の列 oi_dist_node_bp
    "oi_dist_vwap_bp_liqdir": AX_PARTNER_SIGN,   # 元の列 oi_dist_vwap_bp
    "implied_leverage": AX_INHERIT,
    "bundle_n_events_dedup": AX_INHERIT,
    "bundle_total_qty_accum": AX_INHERIT,
    "side": AX_INHERIT,
}
# **決定 14''**: `|t|` がバーの近傍に入る行に印を付ける(観測のみ)。
# 幅は §9.1 の「ブートストラップ SE 自身の相対誤差 ≈ 1/√(2·reps) = 1.58%」から出した
# ±0.062 を丸めた **±0.065**(事前登録 §9.1 の「3.86〜3.99」と同じ帯)。
BAR_NEAR_HALFWIDTH = 0.065

# --- 観測量の系統(§4.1。前進到達 `fwd_node` は 1 周目では出さない = §4.3)---
JUDGE_SYSTEMS = (
    ("reach_back_vwap_{h}m", "prop"),
    ("reach_back_node_{h}m", "prop"),
)
OBS_H_SYSTEMS = (
    ("bp_{h}m_reactdir", "mean"),
    ("mfe_{h}m_reactdir", "mean"),
    ("mae_{h}m_reactdir", "mean"),
    ("doi_post_{h}m", "mean"),
    ("reach_node_up_{h}m", "prop"),
    ("reach_node_dn_{h}m", "prop"),
)
OBS_FLAT_SYSTEMS = (
    ("reach_back_vwap_sec", "mean"),
    ("reach_back_node_sec", "mean"),
    ("reach_node_up_sec", "mean"),
    ("reach_node_dn_sec", "mean"),
    ("doi_pre_1h", "mean"),
    ("doi_pre_4h", "mean"),
    ("doi_in", "mean"),
)

# --- MDE の単位(§10.1 の固定表。走行前の再監査(6 回目)の指摘 5)-------------
# **前版は「検出されず(MDE = X)」の X に単位を書かなかった**(事前登録 §10.1 は
# 「**X はその行の MDE 列の値と単位**」と書いていたので、文面と実装が食い違っていた)。
# **単位は系統ごとに決まっている。**下が事前登録 §10.1 に置いた固定表そのものである。
UNIT_RATIO = "割合"       # 到達率(0〜1)
UNIT_BP = "bp"            # 価格変化・最大順行 / 逆行
UNIT_SEC = "秒"           # 到達までの時間
UNIT_QTY = "枚"           # ΔOI(建玉の増減)
_UNIT_TEMPLATES: dict[str, str] = {
    "reach_back_vwap_{h}m": UNIT_RATIO,
    "reach_back_node_{h}m": UNIT_RATIO,
    "reach_node_up_{h}m": UNIT_RATIO,
    "reach_node_dn_{h}m": UNIT_RATIO,
    "bp_{h}m_reactdir": UNIT_BP,
    "mfe_{h}m_reactdir": UNIT_BP,
    "mae_{h}m_reactdir": UNIT_BP,
    "doi_post_{h}m": UNIT_QTY,
    "reach_back_vwap_sec": UNIT_SEC,
    "reach_back_node_sec": UNIT_SEC,
    "reach_node_up_sec": UNIT_SEC,
    "reach_node_dn_sec": UNIT_SEC,
    "doi_pre_1h": UNIT_QTY,
    "doi_pre_4h": UNIT_QTY,
    "doi_in": UNIT_QTY,
}
MDE_UNITS: dict[str, str] = {}
for _tpl, _u in _UNIT_TEMPLATES.items():
    if "{h}" in _tpl:
        for _h in HORIZONS:
            MDE_UNITS[_tpl.format(h=_h)] = _u
    else:
        MDE_UNITS[_tpl] = _u


def mde_unit(col: str) -> str:
    """その観測量の MDE の単位(§10.1 の固定表)。表に無ければ空。"""
    return MDE_UNITS.get(col, "")

# --- 軸(§4 の表)------------------------------------------------------------
# W に依る軸: 走行ごとに切る(= だから群が 3 + 3 である)。
AXES_W = (
    ("A1", "bin_pct"),
    ("A2", "dist_node_bp_liqdir"),
    ("A3", "dist_vwap_bp_liqdir"),
    ("A4", "oi_dist_node_bp_liqdir"),
    ("A5", "oi_dist_vwap_bp_liqdir"),
    ("E", "implied_leverage"),
)
# W に依らない 3 分位の軸: gap60_w8 の実群で 1 回だけ切る(§4 の内訳表)。
AXES_FLAT = (
    ("B1", "bundle_n_events_dedup"),
    ("B2", "bundle_total_qty_accum"),
    ("D", "doi_pre_1h"),
)
KIND_LIQ = "liq"
KIND_UNI = "control_uniform"
KIND_MAT = "control_matched"


# --- 向きの要る量(§6.1)------------------------------------------------------
# 実装は対照行(side が無い)に `REACT_SIGN` = +1 を当てて生の値を入れている
# (`scripts/o3c_reaction.py` 冒頭の注 42 行目。**実測**)。よって
# `*_reactdir` の 3 系統だけが「向きの要る量」である。
# 下向き(SELL の向き)と上向き(BUY の向き)の作り方:
#   bp  : 下 = −bp_raw   / 上 = +bp_raw
#   mfe : 下 = −mae_raw  / 上 = +mfe_raw  (符号を反転すると mfe と mae が入れ替わる)
#   mae : 下 = −mfe_raw  / 上 = +mae_raw
def _directional(col: str) -> bool:
    return col.endswith("_reactdir")


def _updown_sources(col: str) -> tuple[tuple[str, float], tuple[str, float]]:
    """(下向きの (元の列, 係数), 上向きの (元の列, 係数)) を返す。"""
    if col.startswith("bp_"):
        raw = col[: -len("_reactdir")]           # bp_{h}m
        return (raw, -1.0), (raw, +1.0)
    if col.startswith("mfe_"):
        h = col[len("mfe_"): -len("_reactdir")]
        return (f"mae_{h}_reactdir", -1.0), (f"mfe_{h}_reactdir", +1.0)
    if col.startswith("mae_"):
        h = col[len("mae_"): -len("_reactdir")]
        return (f"mfe_{h}_reactdir", -1.0), (f"mae_{h}_reactdir", +1.0)
    raise KeyError(col)


# =============================================================================
# 読み込み
# =============================================================================
def _f(x) -> float:
    if x is None:
        return float("nan")
    s = str(x).strip()
    if not s:
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


class Run:
    """1 走行(`--mode full` の出力ディレクトリ)を読んだもの。"""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = Path(path)
        rows = list(csv.DictReader((self.path / "table.csv").open(encoding="utf-8", newline="")))
        mixed_p = self.path / "table_mixed.csv"
        mixed = (
            list(csv.DictReader(mixed_p.open(encoding="utf-8", newline="")))
            if mixed_p.exists()
            else []
        )
        try:
            self.summary = json.loads((self.path / "summary.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.summary = {}
        self.params = self.summary.get("params") or {}
        self.window_hours = self.params.get("window_hours")

        self.by_kind: dict[str, list[dict]] = {KIND_LIQ: [], KIND_UNI: [], KIND_MAT: []}
        for r in rows:
            if r.get("kind") in self.by_kind:
                self.by_kind[r["kind"]].append(r)

        # --- 1 対 1 の対応(決定 6')-----------------------------------------
        # **`matched_liq_id` 列で取る。**連番の算術による復元はしない
        # (走行前の再監査(3 回目)の指摘 6: 復元は mixed 束が相手のとき静かに外れ、
        # 行が黙って落ちていた)。mixed 束の行は `table_mixed.csv` 側にあるので、
        # 引き当ての辞書は主表の束 + mixed の両方から作る。
        self.mixed_ids = {r["cascade_id"] for r in mixed}
        by_id: dict[str, dict] = {r["cascade_id"]: r for r in self.by_kind[KIND_LIQ]}
        for r in mixed:
            by_id.setdefault(r["cascade_id"], r)
        self.pair_of_matched: list[dict | None] = [
            by_id.get(str(r.get("matched_liq_id") or ""))
            for r in self.by_kind[KIND_MAT]
        ]
        # 決定 8': **相手が mixed 束の合わせた対照は全群から落とす。**
        # 実群の側は mixed を主表から外しているので、残すと 1 対 1 の対称性が崩れる。
        self.mat_mixed_partner = [
            bool(str(r.get("matched_liq_id") or "") in self.mixed_ids)
            for r in self.by_kind[KIND_MAT]
        ]
        self.n_dropped_mixed_partner = int(sum(self.mat_mixed_partner))
        self.mat_usable = np.array(
            [not m for m in self.mat_mixed_partner], dtype=bool
        )
        self.pairing_worst_bin_pct_gap = float("nan")   # サニティ #14 が埋める
        self.pairing_report: dict = {}                  # サニティ #14 の結果(決定 13'')

        self.days = sorted({r["day"] for r in rows})
        self._day_index = {d: i for i, d in enumerate(self.days)}
        self.day_idx = {
            k: np.array([self._day_index[r["day"]] for r in v], dtype=np.int64)
            for k, v in self.by_kind.items()
        }
        self._cache: dict[tuple[str, str], np.ndarray] = {}

    # -- 列の値(向きの要る量は kind ごとに作り方が違う)----------------------
    def raw(self, kind: str, col: str) -> np.ndarray:
        key = (kind, "#" + col)
        if key not in self._cache:
            self._cache[key] = np.array(
                [_f(r.get(col)) for r in self.by_kind[kind]], dtype=float
            )
        return self._cache[key]

    def values(self, kind: str, col: str) -> np.ndarray:
        """§6.1 を当てた後の値。対照 (i) の向きの要る量はここでは作らない
        (下向き / 上向きの 2 本を `updown()` で別々に出してから合成する)。

        **決定 5'(走行前の再監査(3 回目)の指摘 5)**: 合わせた対照の `*_reactdir` は、
        1 対 1 の相手の実群の側の符号を当てる。下向き(SELL 側)では
        `mfe` と `mae` が入れ替わる(`mfe = max(s·up, s·dn)` の定義から)。
        **「重み付けが要らない」のではなく「相手の符号を当てる」である。**
        """
        key = (kind, col)
        if key in self._cache:
            return self._cache[key]
        if kind == KIND_MAT and _directional(col):
            # 1 対 1 の相手の束の side を当てる(§6.1 の 4)。
            dn_up = self.updown(kind, col)
            out = np.full(len(self.by_kind[kind]), np.nan)
            for i, p in enumerate(self.pair_of_matched):
                if p is None:
                    continue
                out[i] = dn_up[0][i] if p.get("side") == "SELL" else dn_up[1][i]
            self._cache[key] = out
            return out
        out = self.raw(kind, col)
        self._cache[key] = out
        return out

    def matched_partner_sign_axis(self, col: str) -> np.ndarray:
        """**決定 1'**: 合わせた対照自身の軸の値を「符号なしの大きさ × 相手の側の符号」で作る。

        `*_liqdir` 列は `LIQ_SIGN`(SELL +1 / BUY −1)を掛けたものなので
        (`scripts/o3c_oi_distance.py:542` の `_apply_liqdir_and_leverage`。**実測**)、
        対照行に残っている**符号なしの元の列**に相手の側の符号を当てれば、
        実群と同じ規則で作った**対照自身の**軸の値になる(群を受け継ぐのではない)。
        丸めも実装に合わせて 4 桁にする。
        """
        key = (KIND_MAT, "@" + col)
        if key in self._cache:
            return self._cache[key]
        src = LIQDIR_SOURCE[col]
        base_v = self.raw(KIND_MAT, src)
        out = np.full(base_v.size, np.nan)
        for i, p in enumerate(self.pair_of_matched):
            if p is None or not math.isfinite(base_v[i]):
                continue
            s = LIQ_SIGN.get(str(p.get("side") or ""))
            if s is None:
                continue
            out[i] = round(base_v[i] * s, 4)
        self._cache[key] = out
        return out

    def updown(self, kind: str, col: str) -> tuple[np.ndarray, np.ndarray]:
        (dn_col, dn_k), (up_col, up_k) = _updown_sources(col)
        return self.raw(kind, dn_col) * dn_k, self.raw(kind, up_col) * up_k

    def w_sell(self) -> float:
        """§6.1 の 1: 実群の side 比を**判定区間で**数える。"""
        sides = [r.get("side") for r in self.by_kind[KIND_LIQ]]
        ns, nb = sides.count("SELL"), sides.count("BUY")
        return (ns / (ns + nb)) if (ns + nb) else float("nan")


# =============================================================================
# 群(§4 の 48 群)
# =============================================================================
class Group:
    __slots__ = ("name", "run", "axis", "col", "q", "side", "cuts", "control_axis")

    def __init__(self, name, run, axis, col=None, q=None, side=None, cuts=None,
                 control_axis=AX_OWN):
        self.name, self.run, self.axis = name, run, axis
        self.col, self.q, self.side, self.cuts = col, q, side, cuts
        # 対照 (ii) の軸の値をどう作るか(決定 1'。走行ごとに**測って**決める)。
        #   AX_OWN          = 対照行にその列の値があるので、対照にも同じ切り方を当てる
        #   AX_PARTNER_SIGN = 対照行に符号なしの大きさがあるので、相手の側の符号を当てて
        #                     **対照自身の**軸の値を作る(受け継ぎではない)
        #   AX_INHERIT      = 対照行に対応物が無いので、1 対 1 の相手の群を受け継ぐ
        self.control_axis = control_axis

    @property
    def pair_inherit(self) -> bool:
        """**受け継ぐ**群か(= `AX_INHERIT`)。E 6 + B1 3 + B2 3 + C 2 = 14 群。"""
        return self.control_axis == AX_INHERIT

    @property
    def is_quantile(self) -> bool:
        return self.q is not None


def control_axis_kinds(run: Run) -> dict[str, str]:
    """**測って**決める: 軸の列ごとに、対照 (ii) の軸の値をどう作るか(決定 1')。

    **前版はここが 2 分岐で、「対照行にその列の値があるのは `bin_pct` と `doi_pre_1h`
    だけ」と書いていた。数えたのは `*_liqdir` の付いた列だけだった**
    (走行前の再監査(3 回目)の指摘 1)。**符号なしの列(`dist_node_bp` /
    `dist_vwap_bp` / `oi_dist_node_bp` / `oi_dist_vwap_bp`)は対照行にも値がある。**

    決め方(**走行ごとに数える。決め打ちにしない**):
      1. その列自身が対照行で 1 つでも有限 → `AX_OWN`
      2. `*_liqdir` で、符号なしの元の列が対照行で 1 つでも有限 → `AX_PARTNER_SIGN`
      3. それ以外 → `AX_INHERIT`
    `side`(軸 C)は対照行に無く、符号なしの元も無いので必ず `AX_INHERIT`。
    """
    out: dict[str, str] = {"side": AX_INHERIT}
    for _axis, col in AXES_W + AXES_FLAT:
        own = np.concatenate([run.raw(KIND_MAT, col), run.raw(KIND_UNI, col)])
        if bool(np.isfinite(own).any()):
            out[col] = AX_OWN
            continue
        src = LIQDIR_SOURCE.get(col)
        if src is not None:
            base_v = np.concatenate([run.raw(KIND_MAT, src), run.raw(KIND_UNI, src)])
            if bool(np.isfinite(base_v).any()):
                out[col] = AX_PARTNER_SIGN
                continue
        out[col] = AX_INHERIT
    return out


def check_axis_kinds(run: Run) -> list[str]:
    """**決定 3''**: 測った作り方が事前登録の固定(`AXIS_KIND_FIXED`)と一致するかを見る。

    食い違いを 1 件でも返したら、呼び出し側が「[止め]」で終了コード 1 にする。
    **測った側に合わせ直さない**(合わせると、判定区間で対照の作り方が黙って変わる)。
    """
    got = control_axis_kinds(run)
    bad: list[str] = []
    for col, want in sorted(AXIS_KIND_FIXED.items()):
        have = got.get(col)
        if have != want:
            bad.append(f"{run.name}: 軸 {col} の対照 (ii) の作り方が {have} "
                       f"(事前登録 §4 の固定は {want})")
    extra = sorted(set(got) - set(AXIS_KIND_FIXED))
    if extra:
        bad.append(f"{run.name}: 事前登録に無い軸が測られた: {extra}")
    return bad


def _sens_name_params(name: str) -> tuple[int, float] | None:
    """感度の名前 `gap<N>_w<M>` から (gap 秒, W 時間) を読む。読めなければ None。"""
    m = re.fullmatch(r"gap(\d+)_w(\d+)", name)
    return (int(m.group(1)), float(m.group(2))) if m else None


def read_approval_from_prereg(prereg: Path) -> tuple[str | None, str]:
    """**決定 2''''**: 事前登録 §14.4 の「応答の L 番号」の欄を読む。

    返り値 `(L 番号, 説明)`。**欄が「(まだ無い)」なら `None`** を返し、呼び出し側が
    「[止め]」で終了コード 1 にする(**迂回する旗は作っていない**。読む場所は
    `<--root>/docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md` に固定)。

    **前版は `--approval L-199` を §14.1 のコマンドに固定で書いていたが、
    L-199 は「1 = a、9 = a」への応答であって、§13 の 8 件と §14.4 の待つものへの
    応答ではない**(走行前の再監査(6 回目)の指摘 2)。
    **報告への応答が来ていなくても L-199 のまま走れてしまう形だったので、閉じた。**
    """
    if not prereg.exists():
        return None, f"事前登録が読めない({prereg})"
    text = prereg.read_text(encoding="utf-8", errors="replace")
    fields = [m.strip() for m in APPROVAL_FIELD_RE.findall(text)]
    if not fields:
        return None, f"事前登録に「応答の L 番号」の欄が 1 つも無い({prereg})"
    if len(set(fields)) > 1:
        return None, ("事前登録の「応答の L 番号」の欄が "
                      f"{len(set(fields))} 通りある: {sorted(set(fields))}")
    value = fields[0]
    if not APPROVAL_VALUE_RE.match(value):
        return None, ("事前登録 §14.4 の「応答の L 番号」の欄が埋まっていない"
                      f"(欄の値: {value!r})")
    return value, f"事前登録 §14.4 の「応答の L 番号」の欄({prereg})"


# **凍結した道具の 2 ファイル(prereg 監査(10 回目)の指摘 1・2・3。リードの決定 1・2・3)**。
# **版の担保はこの 2 ファイルだけに掛ける。**作業ツリー全体は、出力先・台帳・TRACE・
# 事前登録の欄の書き込みで必ず汚れるので、担保の単位に使えない(指摘 1・2 の実測)。
# **走行の道具 `scripts/o3c_reaction.py` の `TOOL_FILES_REL` と同じ 2 つである。**
TOOL_FILES_REL = ("scripts/o3c_reaction.py", "scripts/o3c_reaction_judge.py")


def tool_commit(repo: Path | None = None) -> str:
    """**凍結した道具の 2 ファイルに最後に触れたコミット**。取れなければ「不明」。

    `git log -1 --format=%H -- scripts/o3c_reaction.py scripts/o3c_reaction_judge.py`。

    **prereg 監査(10 回目)の指摘 3。リードの決定 3**:
    **前版は `git rev-parse HEAD` だった。**欄(事前登録 §14.4)に書き写した値と、
    **その書き写しをコミットした後の HEAD は定義上一致しない**(指摘 3)。
    **本版の値は「この 2 ファイルに最後に触れたコミット」なので、
    事前登録の欄を書き足しても、それをコミットしても動かない。**

    **読みの道具の版を `summary.json` に残し、6 本と欄に突き合わせるための関数である。**
    **判定にも計算にも 1 つも使わない。**
    """
    root = Path(repo) if repo is not None else Path(__file__).resolve().parent.parent
    try:
        r = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%H",
                            "--", *TOOL_FILES_REL],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "不明"
    got = (r.stdout or "").strip()
    if r.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", got):
        return "不明"
    return got


def tool_dirty(repo: Path | None = None) -> tuple[bool, int]:
    """**凍結した道具の 2 ファイルに未コミットの変更があるか。**

    `git diff --quiet HEAD -- scripts/o3c_reaction.py scripts/o3c_reaction_judge.py` の
    **終了コードが 0 でなければ「汚れている」**。返り値 `(汚れているか, 終了コード)`。
    **git が呼べない場合は「汚れている」側に倒す**(終了コード −1)。

    **prereg 監査(10 回目)の指摘 1・2。リードの決定 1・2**:
    **前版は `git status --porcelain`(作業ツリー全体)だった。**
    **出力先・台帳 `OPENED.txt`・`docs/AUDITOR/TRACE/*.json`・事前登録の欄の書き込みで
    作業ツリーは必ず汚れるので、「全体が clean」は成立しない**(指摘 1・2 の実測)。
    """
    root = Path(repo) if repo is not None else Path(__file__).resolve().parent.parent
    try:
        r = subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD",
                            "--", *TOOL_FILES_REL],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return True, -1
    return (r.returncode != 0), int(r.returncode)


def run_dirty_state(run: "Run") -> str:
    """走行の `summary.json` に残った**道具の**汚れの状態を読む(`clean` / `dirty` / `不明`)。

    **鍵が無い走行(この機械より前に走った出力)は「不明」**として扱い、
    呼び出し側が「[止め]」にする(**決定 3・15**)。
    """
    blk = run.summary.get("tool_dirty")
    if isinstance(blk, dict):
        st = blk.get("状態")
        return st if st in ("clean", "dirty", "不明") else "不明"
    return "不明"


def check_tool_versions(
    named_runs: list[tuple[str, "Run"]],
    *,
    frozen_field: str | None,
    my_commit: str,
    my_state: str,
) -> list[str]:
    """**決定 3・15(9 回目の指摘 3・15)**: 版の担保を 1 本にする。

    次の 3 つを全部満たさなければ理由の一覧を返す(呼び出し側が「[止め]」にする):

      (i)   **読みの道具の側で、凍結した道具の 2 ファイルに未コミットの変更が無い**
            (`git diff --quiet HEAD -- scripts/o3c_reaction.py scripts/o3c_reaction_judge.py` が 0)
      (ii)  **判定 2 本 + 感度 4 本の `tool_commit` がすべて同じで、かつ
            §14.4 の「凍結した道具のコミット」欄と一致する**
      (iii) **6 本とも道具が汚れていない**(各走行の `summary.json` の `tool_dirty`)

    **10 回目の指摘 1・2・3 で変えた点**: **前版の (i)(iii) は「作業ツリー全体が clean」で、
    出力先・台帳・TRACE・事前登録の書き込みで必ず汚れるため、6 本を走らせきれない。**
    (**設計上の帰結。6 本を走らせて確かめたわけではない。****測ったのは「作業ツリーが汚れる」までである**)
    **(ii) の `tool_commit` は `git rev-parse HEAD` で、欄に書ける値と定義上一致しなかった。**

    **射程(隠さずに書く)**: `named_runs` に入るのは**読めた走行だけ**である。
    **読めない感度の走行は、この検査より前に「読めない感度」として落ちており、
    その表は 1 枚も書かれない**(決定 2''''')。**よって版の検査の対象から外れる。**
    """
    bad: list[str] = []
    if my_state != "clean":
        bad.append(f"読みの道具の側で凍結した道具に未コミットの変更がある({my_state})")
    if not frozen_field:
        bad.append("事前登録 §14.4 の「凍結した道具のコミット」欄が埋まっていない"
                   "(開封の直前に書き写す欄である)")
    elif not commit_matches(frozen_field, my_commit):
        bad.append(f"読みの道具の版が §14.4 の欄と違う({my_commit} / 欄 {frozen_field})")
    for nm, r in named_runs:
        got = r.summary.get("tool_commit")
        if not isinstance(got, str) or not got:
            bad.append(f"{nm}: summary.json に tool_commit が無い")
            continue
        if not commit_matches(my_commit, got):
            bad.append(f"{nm}: 走った道具の版が読みの道具と違う({got})")
        elif frozen_field and not commit_matches(frozen_field, got):
            bad.append(f"{nm}: 走った道具の版が §14.4 の欄と違う({got})")
    for nm, r in named_runs:
        st = run_dirty_state(r)
        if st != "clean":
            bad.append(f"{nm}: 走ったときに凍結した道具が {st}")
    return bad


def read_frozen_commit_from_prereg(prereg: Path) -> tuple[str | None, str]:
    """**決定 16**: 事前登録 §14.4 の「凍結した道具のコミット」の欄を読む。

    返り値 `(コミット, 説明)`。**欄が無い / 「(まだ無い)」/ 16 進でないなら `None`** を返し、
    呼び出し側は**記録だけ**して先へ進む(開封の直前に書き写す欄だからである)。
    **埋まっているのに自分の版と違うときだけ「[止め]」にする**(呼び出し側)。
    """
    if not prereg.exists():
        return None, f"事前登録が読めない({prereg})"
    text = prereg.read_text(encoding="utf-8", errors="replace")
    fields = [m.strip() for m in COMMIT_FIELD_RE.findall(text)]
    if not fields:
        return None, f"事前登録に「凍結した道具のコミット」の欄が 1 つも無い({prereg})"
    if len(set(fields)) > 1:
        return None, ("事前登録の「凍結した道具のコミット」の欄が "
                      f"{len(set(fields))} 通りある: {sorted(set(fields))}")
    value = fields[0]
    if not COMMIT_VALUE_RE.match(value):
        return None, ("事前登録 §14.4 の「凍結した道具のコミット」の欄が埋まっていない"
                      f"(欄の値: {value!r})")
    return value, f"事前登録 §14.4 の「凍結した道具のコミット」の欄({prereg})"


def commit_matches(field: str, got: str) -> bool:
    """欄の値と自分の版が同じコミットを指すか(**短縮形も許す**)。

    欄は手書きなので短縮形(7 桁以上)がありうる。**どちらかが他方の前置なら同じとみなす。**
    `got` が「不明」なら一致しない(= 呼び出し側が「[止め]」にする)。
    """
    if not field or not got or got == "不明":
        return False
    a, b = field.lower(), got.lower()
    return a.startswith(b) or b.startswith(a)


def check_run_params(run: Run, *, mode: str, gap_sec: int | None = None,
                     window_hours: float | None = None,
                     n_days: int | None = None, label: str = "",
                     settings: bool = False,
                     approval: str | None = None) -> list[str]:
    """**決定 12'''**: 渡されたディレクトリが名前どおりの走行かを `params` で見る。

    **前版は `--run-w8` / `--run-w24` に渡されたものを無条件に `gap60_w8` / `gap60_w24` と
    名付け、`window_hours` と日数を `summary.json` に写すだけで検査していなかった**
    (走行前の再監査(5 回目)の指摘 12)。**取り違えを止める機械が無かった。**

    見るのは `scripts/o3c_reaction.py` が書く `params` である:
    `mode`(full / sample)/ `gap_ms`(= gap 秒 × 1000)/ `window_hours` / `days` の数。
    **迂回する旗は作っていない**(標本で試すときも、試験用の `summary.json` を置いた
    一時ディレクトリを渡す)。

    **決定 1''''(走行前の再監査(6 回目)の指摘 1)**: `settings=True` のとき、
    **`mmr` / `seed` / `bin_pct` / `match_order` も突き合わせる**(判定 2 本・感度 4 本)。
    **前版はこの 4 つを見ていなかったので、`--mmr` を付け忘れた走行でも
    `implied_leverage` 列が空のまま 48 群・576 行を通り、軸 E の 72 行が
    黙って「不明(n < 30)」になった**(**6 回目の監査の実測**)。

    **決定 2''''(同 6 回目の指摘 2)**: `approval` を渡したとき、
    **`params.approval` がそれと一致しなければ「[止め]」**(判定 2 本)。
    """
    p = run.params
    who = label or run.name
    bad: list[str] = []
    if not p:
        return [f"{who}: summary.json の params が読めない({run.path})"]
    got_mode = p.get("mode")
    if got_mode != mode:
        bad.append(f"{who}: params.mode が {got_mode!r}(要る値は {mode!r})")
    if gap_sec is not None:
        got_ms = p.get("gap_ms")
        if got_ms != gap_sec * 1000:
            bad.append(f"{who}: params.gap_ms が {got_ms}(要る値は {gap_sec * 1000})")
    if window_hours is not None:
        got_w = p.get("window_hours")
        if got_w is None or float(got_w) != float(window_hours):
            bad.append(f"{who}: params.window_hours が {got_w}(要る値は {window_hours})")
    if n_days is not None:
        days = p.get("days")
        got_n = len(days) if isinstance(days, list) else None
        if got_n != n_days:
            bad.append(f"{who}: params.days の日数が {got_n}(要る値は {n_days})")
    if settings:
        for key, want in (("mmr", MMR_FIXED), ("seed", RUN_SEED_FIXED),
                          ("bin_pct", BIN_PCT_FIXED),
                          ("match_order", MATCH_ORDER_FIXED)):
            got = p.get(key)
            same = (
                (got is not None and float(got) == float(want))
                if isinstance(want, (int, float)) and not isinstance(want, bool)
                else got == want
            )
            if not same:
                bad.append(f"{who}: params.{key} が {got!r}(要る値は {want!r})")
    if approval is not None:
        got = p.get("approval")
        if got != approval:
            bad.append(
                f"{who}: params.approval が {got!r}(要る値は {approval!r}"
                f" = 事前登録 §14.4 の「応答の L 番号」)")
    return bad


def check_run_approval(run: Run, approval: str, label: str = "") -> list[str]:
    """**決定 14(prereg 監査(8 回目)の指摘 14)**: 感度 4 本の `params.approval` の
    食い違いを**判定側の破れと同じ扱い**にするための、承認の番号だけを見る検査。

    **理由(リードの決定の逐語)**: 「**承認外の番号で 456 日を開けた走行が 1 本でもあれば、
    1 周目はそこで止めてオーナーに報告する**」。
    **前版は感度の approval の食い違いを「その走行の表だけ落とす」で済ませていたので、
    オーナーの応答と違う番号で 456 日を 1 本開けたことが `summary.json` の中にしか
    残らなかった**(8 回目の指摘 14)。

    **`params` が読めない場合は何も返さない**(「読めない感度」は決定 2''''' の側で
    扱う = 判定の表は書く)。**ここで見るのは `approval` の食い違いだけである。**
    """
    p = run.params
    if not p:
        return []
    who = label or run.name
    got = p.get("approval")
    if got != approval:
        return [f"{who}: params.approval が {got!r}(要る値は {approval!r}"
                f" = 事前登録 §14.4 の「応答の L 番号」)"]
    return []


def tertile_cuts(vals: np.ndarray) -> tuple[float, float]:
    """§4 の 3 分位: 判定区間の**実群**の軸の値で分位点を決める(決定 3)。

    切り値 = `np.nanpercentile(..., [100/3, 200/3])`。同点は `<=` で下側に入れる。
    欠測はどの群にも入れない。切り値 2 つが等しければ中の群は空になる。
    """
    v = vals[np.isfinite(vals)]
    if v.size == 0:
        return (float("nan"), float("nan"))
    lo, hi = np.nanpercentile(v, [100.0 / 3.0, 200.0 / 3.0])
    return (float(lo), float(hi))


def build_groups(run8: Run, run24: Run) -> list[Group]:
    """§4 の内訳表をそのまま組む。全体 1 + 3 分位 15 軸 × 3 + side 2 = 48 群。"""
    kinds = {run8.name: control_axis_kinds(run8), run24.name: control_axis_kinds(run24)}
    groups: list[Group] = []
    groups.append(Group("全体", RUN_W8, "—"))
    for axis, col in AXES_W:
        for run, tag in ((run8, "W8h"), (run24, "W24h")):
            cuts = tertile_cuts(run.values(KIND_LIQ, col))
            for q in (1, 2, 3):
                groups.append(Group(f"{axis}_{tag}_Q{q}", run.name, axis, col=col, q=q,
                                    cuts=cuts, control_axis=kinds[run.name][col]))
    for axis, col in AXES_FLAT:
        cuts = tertile_cuts(run8.values(KIND_LIQ, col))
        for q in (1, 2, 3):
            groups.append(Group(f"{axis}_Q{q}", RUN_W8, axis, col=col, q=q, cuts=cuts,
                                control_axis=kinds[RUN_W8][col]))
    for s in ("SELL", "BUY"):
        groups.append(Group(f"C_{s}", RUN_W8, "C", col="side", side=s,
                            control_axis=AX_INHERIT))
    return groups


def build_flat_groups_w24(run24: Run) -> list[Group]:
    """決定 6: W に依らない 12 群の **W = 24h 側**。

    **576 検定には入れない**(判定に使うのは W8h の走行から取った 12 群だけ)。
    ここで作った 12 群は**観測のみの表**に出す(t と判定の列なし)。

    **決定 20'(走行前の再監査(3 回目)の指摘 20)**: 切り値は **W = 24h の実群で
    切り直す**(W = 8h の切り値を持ち込まない)。W が違えば実群の分布そのものが違うので、
    W = 8h の切り値を当てると「3 分位」でなくなるためである(**リードの決定**)。
    """
    kinds = control_axis_kinds(run24)
    out = [Group("全体", RUN_W24, "—")]
    for axis, col in AXES_FLAT:
        cuts = tertile_cuts(run24.values(KIND_LIQ, col))   # ← W = 24h で切り直す
        for q in (1, 2, 3):
            out.append(Group(f"{axis}_Q{q}", RUN_W24, axis, col=col, q=q, cuts=cuts,
                             control_axis=kinds[col]))
    for s in ("SELL", "BUY"):
        out.append(Group(f"C_{s}", RUN_W24, "C", col="side", side=s,
                         control_axis=AX_INHERIT))
    return out


def build_groups_single(run: Run) -> list[Group]:
    """**決定 19'**: 感度 1 本ぶんの群(その走行の実群だけで切る)。

    全体 1 + 3 分位 9 軸(A1〜A5・E・B1・B2・D)× 3 = 27 + side 2 = **30 群**。
    **判定には 1 つも使わない**(観測のみの表にしか出さない)。
    """
    kinds = control_axis_kinds(run)
    out = [Group("全体", run.name, "—")]
    for axis, col in AXES_W + AXES_FLAT:
        cuts = tertile_cuts(run.values(KIND_LIQ, col))
        for q in (1, 2, 3):
            out.append(Group(f"{axis}_Q{q}", run.name, axis, col=col, q=q, cuts=cuts,
                             control_axis=kinds[col]))
    for s in ("SELL", "BUY"):
        out.append(Group(f"C_{s}", run.name, "C", col="side", side=s,
                         control_axis=AX_INHERIT))
    return out


def _quantile_label(v: float, cuts: tuple[float, float]) -> int:
    if not math.isfinite(v) or not math.isfinite(cuts[0]) or not math.isfinite(cuts[1]):
        return 0
    return 1 if v <= cuts[0] else (2 if v <= cuts[1] else 3)


def membership(run: Run, kind: str, g: Group) -> np.ndarray:
    """その群に入る行の真偽値。

    合わせた対照 (ii) の軸の値の作り方は 3 通り(決定 1'。`control_axis_kinds` が
    走行ごとに**測って**決める):

    - `AX_OWN`(`bin_pct` / `doi_pre_1h`)= 対照行にその列の値があるので、
      **対照にも同じ切り方を当てる**(§4)。
    - `AX_PARTNER_SIGN`(A2〜A5 の 4 軸)= 対照行に**符号なしの大きさ**があるので、
      1 対 1 の相手の側の符号を当てて**対照自身の**軸の値を作り、同じ切り値に当てる。
    - `AX_INHERIT`(E・B1・B2・C の 14 群)= 対照行に対応物が無いので、
      **1 対 1 の相手の束の群を受け継ぐ**(§6.1 の 4)。

    一様対照 (i) は 1 対 1 の相手が無いので、`AX_OWN` 以外の群には**入れない**
    (= その群の 対照 (i) と 差 (i) の欄が空になる)。

    **決定 8'**: 相手が mixed 束の合わせた対照は、どの群からも落とす
    (実群の側が mixed を主表から外しているので、残すと 1 対 1 が崩れる)。
    """
    rows = run.by_kind[kind]
    n = len(rows)
    if kind == KIND_MAT:
        usable = run.mat_usable
    if g.axis == "—":
        return usable.copy() if kind == KIND_MAT else np.ones(n, dtype=bool)
    if g.control_axis != AX_OWN and kind == KIND_UNI:
        return np.zeros(n, dtype=bool)
    if g.side is not None:
        if kind == KIND_LIQ:
            return np.array([r.get("side") == g.side for r in rows], dtype=bool)
        if kind == KIND_UNI:
            return np.zeros(n, dtype=bool)
        return np.array(
            [(p is not None and p.get("side") == g.side) for p in run.pair_of_matched],
            dtype=bool,
        ) & usable
    if kind == KIND_MAT and g.control_axis == AX_INHERIT:
        vals = np.array(
            [_f(p.get(g.col)) if p is not None else float("nan") for p in run.pair_of_matched],
            dtype=float,
        )
    elif kind == KIND_MAT and g.control_axis == AX_PARTNER_SIGN:
        vals = run.matched_partner_sign_axis(g.col)
    else:
        vals = run.values(kind, g.col)
    sel = np.array([_quantile_label(v, g.cuts) == g.q for v in vals], dtype=bool)
    return (sel & usable) if kind == KIND_MAT else sel


def check_pairing(run: Run) -> list[str]:
    """**サニティ #14**(決定 6' + 決定 12''): 1 対 1 の対応を走行ごとに測る。

    5 つを見る。1 つでも破れたら呼び出し側が「[止め]」で終了コード 1 にする
    (**崩れても静かに行が落ちるだけ、という前版の形を閉じる**)。

      1. すべての合わせた対照に相手が実在する(`matched_liq_id` が引ける)
      2. 相手が**同じ日**である
      3. `bin_pct` の差が **±5.0 ポイント以内**(`scripts/o3c_reaction.py:140` の
         `MATCH_TOL_PCT`。境界を含む = マッチングが `bp ± tol` を閉区間で取るため)
      4. **同じ `matched_liq_id` を 2 つ以上の対照が指していない**(決定 12'')
      5. **対照の件数 = 引けた相手の件数**(**mixed 相手を含めて数える**。決定 12'')

    **4 と 5 は走行前の再監査(4 回目)の指摘 12 で足した。**
    **前版は (a)(b)(c) の 3 つしか見ておらず、「1 対 1」そのもの(一意性)を測っていなかった。**
    §6.1 の 4 と決定 8'(mixed 相手を落とす)はこの一意性に依存している。
    """
    bad: list[str] = []
    rows = run.by_kind[KIND_MAT]
    n_missing = n_day = n_tol = 0
    worst = 0.0
    seen: dict[str, int] = {}
    for r, p in zip(rows, run.pair_of_matched):
        if p is None:
            n_missing += 1
            continue
        pid = str(p.get("cascade_id") or "")
        seen[pid] = seen.get(pid, 0) + 1
        if p.get("day") != r.get("day"):
            n_day += 1
        a, b = _f(r.get("bin_pct")), _f(p.get("bin_pct"))
        if math.isfinite(a) and math.isfinite(b):
            d = abs(a - b)
            worst = max(worst, d)
            if d > MATCH_TOL_PCT + 1e-9:
                n_tol += 1
    n_dup = sum(c - 1 for c in seen.values() if c > 1)
    n_pulled = len(seen)                      # 引けた相手の**異なり数**(mixed 相手も含む)
    if n_missing:
        bad.append(f"{run.name}: 相手の束が引けない合わせた対照が {n_missing} 件")
    if n_day:
        bad.append(f"{run.name}: 相手が別の日の合わせた対照が {n_day} 件")
    if n_tol:
        bad.append(
            f"{run.name}: bin_pct の差が ±{MATCH_TOL_PCT} を超える組が {n_tol} 件"
            f"(最大 {worst:.4f})"
        )
    if n_dup:
        dups = sorted(k for k, c in seen.items() if c > 1)[:5]
        bad.append(f"{run.name}: 同じ相手を指す合わせた対照が {n_dup} 件ぶん重複"
                   f"(例: {dups})")
    if n_pulled != len(rows):
        bad.append(f"{run.name}: 対照の件数 {len(rows)} と引けた相手の件数 {n_pulled} が違う"
                   f"(mixed 相手を含めて数えた)")
    run.pairing_worst_bin_pct_gap = worst
    run.pairing_report = {
        "対照の件数": len(rows),
        "引けた相手の異なり数(mixed 相手を含む)": n_pulled,
        "相手が引けない件数": n_missing,
        "相手が別の日の件数": n_day,
        f"bin_pct の差が ±{MATCH_TOL_PCT} を超える件数": n_tol,
        "同じ相手を指す重複の件数": n_dup,
        "bin_pct の差の最大": worst,
        "通過": not bad,
    }
    return bad


# =============================================================================
# 集計・ブートストラップ(§9.1)
# =============================================================================
def mean_se(vals: np.ndarray) -> tuple[float, float, int]:
    v = vals[np.isfinite(vals)]
    if v.size == 0:
        return float("nan"), float("nan"), 0
    m = float(v.mean())
    se = float(v.std(ddof=1) / math.sqrt(v.size)) if v.size > 1 else float("nan")
    return m, se, int(v.size)


def control_i(run: Run, sel: np.ndarray, col: str, w_sell: float) -> tuple[float, float, int]:
    """対照 (i)。向きの要る量は §6.1 の重み付けを必ず通す。"""
    if not _directional(col):
        return mean_se(run.values(KIND_UNI, col)[sel])
    if not math.isfinite(w_sell):
        return float("nan"), float("nan"), 0
    w_buy = 1.0 - w_sell
    dn, up = run.updown(KIND_UNI, col)
    m_dn, se_dn, n_dn = mean_se(dn[sel])
    m_up, se_up, n_up = mean_se(up[sel])
    if n_dn == 0 or n_up == 0:
        return float("nan"), float("nan"), 0
    m = w_sell * m_dn + w_buy * m_up
    # §6.1 の 3: 独立を仮定した合成 = SE を小さく見る向きの近似(結果に併記する)。
    se = (
        math.sqrt(w_sell**2 * se_dn**2 + w_buy**2 * se_up**2)
        if (math.isfinite(se_dn) and math.isfinite(se_up))
        else float("nan")
    )
    return m, se, min(n_dn, n_up)


def day_sums(vals: np.ndarray, sel: np.ndarray, day_idx: np.ndarray, n_days: int):
    ok = sel & np.isfinite(vals)
    s = np.bincount(day_idx[ok], weights=vals[ok], minlength=n_days)
    c = np.bincount(day_idx[ok], minlength=n_days).astype(float)
    return s, c


def ci_normal(diff: float, se: float) -> tuple[float, float]:
    """決定 1: CI は正規近似 `差 ± z_{1−α/2} × ブートストラップ SE`。

    **この形なので「|t| ≥ z」と「CI が 0 を除外」は同値である。**
    **z は `BAR_T`(= `Z_ALPHA` = `norm.ppf(1 − α/2)`)の 1 本だけ**(決定 12')。
    """
    if not (math.isfinite(diff) and math.isfinite(se)):
        return float("nan"), float("nan")
    return diff - BAR_T * se, diff + BAR_T * se


def bootstrap_diff(run: Run, sel_liq, sel_ctl, col: str, boot_idx: np.ndarray):
    """§9.1: クラスタ = UTC 日、置換ありで日を引き、その日の行を丸ごと採る。

    2,000 回・種 1 は**標準誤差の推定にだけ**使う(決定 1)。
    統計量 t = (実群 − 対照 (ii) の差) ÷ (その差のブートストラップ標準誤差)。
    返り値: (差, t, SE, n1, n2, **有限な複製の本数**)。

    **決定 2''(走行前の再監査(4 回目)の指摘 2)**: 非有限の複製を落とした後に
    **残った本数(有限な複製の本数)を返す。****前版はこの本数をどこにも出していなかったので、
    §9.1 の「反復 2,000 回 → SE の相対誤差 1.58%」がそのセルで成り立つかを読む材料が無かった。**
    **閾値は置かない**(`CLAUDE.md` §0.2 の A-12)。**本数を出すだけである。**
    """
    n_days = len(run.days)
    sl, cl = day_sums(run.values(KIND_LIQ, col), sel_liq, run.day_idx[KIND_LIQ], n_days)
    sc, cc = day_sums(run.values(KIND_MAT, col), sel_ctl, run.day_idx[KIND_MAT], n_days)
    n1, n2 = int(cl.sum()), int(cc.sum())
    if n1 == 0 or n2 == 0:
        return float("nan"), float("nan"), float("nan"), n1, n2, 0
    diff = float(sl.sum() / cl.sum() - sc.sum() / cc.sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        a = sl[boot_idx].sum(axis=1) / cl[boot_idx].sum(axis=1)
        b = sc[boot_idx].sum(axis=1) / cc[boot_idx].sum(axis=1)
    d = a - b
    d = d[np.isfinite(d)]
    reps_used = int(d.size)
    if reps_used < 2:
        return diff, float("nan"), float("nan"), n1, n2, reps_used
    se = float(d.std(ddof=1))
    t = diff / se if se > 0 else float("nan")
    return diff, t, se, n1, n2, reps_used


# =============================================================================
# MDE(§8.5 / §8.6)
# =============================================================================
def mde(kind: str, a: np.ndarray, b: np.ndarray, n1: int, n2: int) -> float:
    """§8.5 の式。**z は定数 1 本(`MDE_Z`)だけ**(決定 15'')。

    `a` / `b` = **標本 6 日**の実群 / 合わせた対照の値。
    **判定区間の切り値で群に分けた標本の行**を渡す(標本で切り直さない)。
    `n1` / `n2` = **走行後の群の件数**(欠測を引いた後)。

    > **【本版で消した・走行前の再監査(4 回目)の指摘 15。リードの決定】**
    > **前版は `alpha` を引数に取り、`alpha != ALPHA` のときだけ `_ND.inv_cdf(1 − alpha/2)` を
    > 作り直す枝を持っていた。**
    > **§5 は「判定のバー・CI・MDE のすべてがこの 1 本(`Z_ALPHA`)を使う」と書いており、
    > 決定 12' も「z は 1 本」だった。枝が残っていると 2 本目の z が作れる。**
    > **引数ごと消した。**判定に使う α は `ALPHA`(= 0.05/576)で固定である。
    > **§8.5 の再現コマンド(事前登録の中の別の `mde()`)は α = 0.05 の表を作るための
    > 文書側の関数で、本ファイルの関数ではない。**
    """
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size == 0 or b.size == 0 or n1 <= 0 or n2 <= 0:
        return float("nan")
    if kind == "prop":
        p1, p2 = float(a.mean()), float(b.mean())
        var = p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2
    else:
        if a.size < 2 or b.size < 2:
            return float("nan")
        var = float(a.std(ddof=1)) ** 2 / n1 + float(b.std(ddof=1)) ** 2 / n2
    if not math.isfinite(var) or var < 0:
        return float("nan")
    return MDE_Z * math.sqrt(var)


# =============================================================================
# 分岐(§10.1 + 走行前の再監査の決定 2)
# =============================================================================
UNKNOWN_N = "不明(n < 30)"
UNKNOWN_N2 = "不明(n2 < 30)"
UNKNOWN_T = "不明(t 未算出)"
UNKNOWN_MDE = "不明(MDE 未算出)"
BRANCHES = [UNKNOWN_N, UNKNOWN_N2, UNKNOWN_T, "差あり(+)", "差あり(−)",
            UNKNOWN_MDE, "検出されず(MDE = X 単位)"]


def decide(n1: int, n2: int, t: float, diff: float, m: float,
           unit: str = "") -> tuple[str, str]:
    """(判定, 検出力の欄)。上から順に当てる(決定 2 + 17' + 1'' + 20'')。

    1. その検定に使う**欠測を引いた後の実群 n1** が 30 未満 → 「不明(n < 30)」
    2. **対照 (ii) の n2 が 30 未満 → 「不明(n2 < 30)」**(決定 20'')
    3. **`t` が非有限 → 「不明(t 未算出)」**(決定 1'')
    4. |t| ≥ z(= `BAR_T`。丸め表示 3.925)→ 「差あり(+)」/「差あり(−)」
    5. MDE が計算できない → **「不明(MDE 未算出)」**
    6. それ以外 → 「検出されず(MDE = X)」

    **5 は決定 17'(走行前の再監査(3 回目)の指摘 17)で分けた。**
    前版は MDE が無くても「検出されず(MDE = 未算出)」と書いていたが、
    **「検出されず」は「この n とこの MDE では検出できなかった」という意味なので、
    MDE が無い行にその語を当てると、検出力が分からないことを不在の側に読ませてしまう**
    (`CLAUDE.md` §0.2 の A-18)。**MDE が無い行は「不明」である。**

    > **【本版で 2 つ足した・走行前の再監査(4 回目)の指摘 1・20。リードの決定】**
    > **3(決定 1'')**: `bootstrap_diff` は SE = 0 のときと有限な複製が 2 本未満のときに
    > `t = nan` を返す。**前版はこの行を n1 ≥ 30 かつ MDE があれば「検出されず」と書いていた。**
    > **検定量が計算できなかった行を「バーに届かなかった」と書く経路である**(指摘 17 と同じ型 = A-18)。
    > **`t` が非有限の行は「不明(t 未算出)」である。**
    > **2(決定 20'')**: **前版は 30 を n1 にだけ当てていた。**
    > inherit の 14 群や欠測の多い軸では n2 が小さくなりうるので、n2 にも同じ 30 を当てる。

    **「差なし」「陰性」は書かない。**MDE との比較(≥ / <)は別の列に残す。
    """
    if n1 < MIN_N:
        return UNKNOWN_N, "n < 30"
    if n2 < MIN_N:
        return UNKNOWN_N2, "n2 < 30"
    if not math.isfinite(t):
        return UNKNOWN_T, "t 未算出"
    if abs(t) >= BAR_T:
        return ("差あり(+)" if diff > 0 else "差あり(−)"), ""
    if not math.isfinite(m):
        return UNKNOWN_MDE, "MDE 未算出"
    # **決定 5''''(走行前の再監査(6 回目)の指摘 5)**: **単位を必ず併記する。**
    # 単位は系統ごとの固定表(`MDE_UNITS`。事前登録 §10.1)から来る。
    # **前版は単位を書いていなかった**(事前登録は「X はその行の MDE 列の値と単位」と
    # 書いていたので、文面と実装が食い違っていた)。
    return f"検出されず(MDE = {_fmt(m)}{(' ' + unit) if unit else ''})", ""


def bar_near(t: float) -> str:
    """**決定 14''**: `|t|` が z ± 0.065 に入るとき ○(**観測のみ。判定は変えない**)。

    §9.1 の「`|t|` が 3.86〜3.99 に入る検定では、反復の引き直しで判定が変わりうる」に
    対応する印である。**前版は帯を本文に書きながら、表にも実装にも印が無かった**
    (走行前の再監査(4 回目)の指摘 14)。
    """
    if not math.isfinite(t):
        return ""
    return "○" if abs(abs(t) - BAR_T) <= BAR_NEAR_HALFWIDTH else ""


def mde_mark(diff: float, m: float) -> str:
    if not math.isfinite(diff) or not math.isfinite(m):
        return ""
    return "≥" if abs(diff) >= m else "<"


# =============================================================================
# 表を組む
# =============================================================================
MDE_COL = "MDE(α=0.05/576)"
# **決定 7''''(走行前の再監査(6 回目)の指摘 7)**: **感度の表の MDE 列は名前を変える。**
# §10.2 は「感度の行は 576 にも α にも F1 の読みにも 1 つも入らない」と書いているのに、
# 前版は感度の表にも族の α の名前が付いた列見出しをそのまま出していた。
# **決定 6'''''(同 7 回目の指摘 6)**: **`observation_only.csv` の 2,208 行も
# 576 にも α にも F1 の読みにも 1 行も入らない**(§10.2)。**同じ理由がこの表にも当たる。**
# **族に入らない行の MDE の列見出しは 1 つにする**(`SENS_MDE_COL` は旧名。同じ文字列)。
REF_MDE_COL = "MDE(参考。族の α に入らない)"
SENS_MDE_COL = REF_MDE_COL
JUDGE_HEADER = [
    "観測量", "群", "h", "n1", "n2", "実群", "対照(i)", "対照(ii)",
    "差(ii)", "差(i)", "対照(i)SE", "走行", "対照(ii)の軸の作り方",
    "t", "ブートストラップSE", "有限な複製の本数", "CI下限", "CI上限",
    MDE_COL, "MDEとの比較", "検出力", "バー近傍", "隣の分位", "判定",
]
# §10.2: 同じ形で出すが、`t` の列と `判定` の列(とそれに付く列)を置かない。
# **`対照(ii)の軸の作り方` は両方の表に出す**(決定 22''。行単位で読む人が
# 14 群と 34 群を取り違えないため)。
OBS_DROPPED_COLS = ("t", "ブートストラップSE", "有限な複製の本数", "CI下限", "CI上限",
                    "バー近傍", "判定")
OBS_HEADER = [
    (REF_MDE_COL if c == MDE_COL else c)
    for c in JUDGE_HEADER if c not in OBS_DROPPED_COLS
]
# 感度の表も同じ見出しである(決定 6'''''。旧名 `SENS_HEADER` は残す)。
SENS_HEADER = OBS_HEADER


def to_ref_mde_rows(rows: list[dict]) -> list[dict]:
    """観測のみの表(判定にも α にも入らない行)の MDE の鍵を `REF_MDE_COL` に付け替える。

    決定 7''''(感度の表)+ **決定 6'''''(`observation_only.csv` にも当てる)**。
    """
    return [{(REF_MDE_COL if k == MDE_COL else k): v for k, v in r.items()}
            for r in rows]


# 旧名(決定 7'''' で入れた名前)。同じ関数である。
to_sens_rows = to_ref_mde_rows


def _fmt(x, nd=6) -> str:
    if x is None:
        return ""
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    v = float(x)
    return "" if not math.isfinite(v) else f"{v:.{nd}f}"


def neighbours(g: Group, per_group: dict[str, dict], judge: bool) -> str:
    """§9 の項 4 / §10.1: 同じ軸の隣の分位の 差(ii) と |t| を併記する(**観測のみ**)。"""
    if not g.is_quantile:
        return ""
    parts = []
    for q in (g.q - 1, g.q + 1):
        if not 1 <= q <= 3:
            continue
        r = per_group.get(g.name[:-1] + str(q))
        if r is None:
            continue
        s = f"Q{q}:差={_fmt(r['d2'])}"
        if judge:
            at = abs(r["t"]) if math.isfinite(r["t"]) else float("nan")
            s += f",|t|={_fmt(at, 4)}"
        parts.append(s)
    return " ".join(parts)


def judge_systems() -> list[tuple[str, str, object]]:
    return [(c.format(h=h), k, h) for c, k in JUDGE_SYSTEMS for h in HORIZONS]


def observation_systems() -> list[tuple[str, str, object]]:
    return (
        [(c.format(h=h), k, h) for c, k in OBS_H_SYSTEMS for h in HORIZONS]
        + [(c, k, "") for c, k in OBS_FLAT_SYSTEMS]
    )


def build_rows(runs: dict[str, Run], samples: dict[str, Run], groups: list[Group],
               boot: dict[str, np.ndarray], *, judge: bool,
               systems: list | None = None) -> list[dict]:
    if systems is None:
        systems = judge_systems() if judge else observation_systems()
    w_sell = {n: r.w_sell() for n, r in runs.items()}
    sel_cache: dict[tuple[str, str, str, str], np.ndarray] = {}

    def sel(g: Group, kind: str, which) -> np.ndarray:
        key = (g.name, g.run, kind, "s" if which is samples else "r")
        if key not in sel_cache:
            sel_cache[key] = membership(which[g.run], kind, g)
        return sel_cache[key]

    out: list[dict] = []
    for col, kind, h in systems:
        per_group: dict[str, dict] = {}
        for g in groups:
            run, smp = runs[g.run], samples.get(g.run)
            s_liq = sel(g, KIND_LIQ, runs)
            s_uni = sel(g, KIND_UNI, runs)
            s_mat = sel(g, KIND_MAT, runs)
            m_liq, _, n1 = mean_se(run.values(KIND_LIQ, col)[s_liq])
            m_uni, se_uni, _ = control_i(run, s_uni, col, w_sell[g.run])
            m_mat, _, n2 = mean_se(run.values(KIND_MAT, col)[s_mat])
            reps_used = None
            if judge:
                diff2, t, se_b, n1, n2, reps_used = bootstrap_diff(
                    run, s_liq, s_mat, col, boot[g.run]
                )
                lo, hi = ci_normal(diff2, se_b)
            else:
                diff2 = (
                    (m_liq - m_mat)
                    if (math.isfinite(m_liq) and math.isfinite(m_mat))
                    else float("nan")
                )
                t = se_b = lo = hi = float("nan")
            diff1 = (
                (m_liq - m_uni)
                if (math.isfinite(m_liq) and math.isfinite(m_uni))
                else float("nan")
            )
            # MDE: p・s は標本 6 日(その群の切り方を当てたもの)、n は走行後の件数(§8.6)。
            # **感度の走行(決定 19')には対を成す標本が無いので MDE を出さない。**
            # その表は観測のみで、判定にも F1 の読みにも 1 つも入らない。
            if smp is None:
                m_val = float("nan")
            else:
                sa = smp.values(KIND_LIQ, col)[sel(g, KIND_LIQ, samples)]
                sb = smp.values(KIND_MAT, col)[sel(g, KIND_MAT, samples)]
                m_val = mde(kind, sa, sb, n1, n2)
            per_group[g.name] = dict(
                g=g, n1=n1, n2=n2, liq=m_liq, uni=m_uni,
                se_uni=se_uni, mat=m_mat, d2=diff2, d1=diff1, t=t, se_b=se_b,
                lo=lo, hi=hi, mde=m_val, reps=reps_used,
            )
        for g in groups:
            r = per_group[g.name]
            row = {
                "観測量": col, "群": g.name, "h": h,
                "n1": r["n1"], "n2": r["n2"],
                "実群": _fmt(r["liq"]), "対照(i)": _fmt(r["uni"]), "対照(ii)": _fmt(r["mat"]),
                "差(ii)": _fmt(r["d2"]), "差(i)": _fmt(r["d1"]),
                "対照(i)SE": _fmt(r["se_uni"]),
                "走行": g.run,
                "対照(ii)の軸の作り方": g.control_axis,
                MDE_COL: _fmt(r["mde"]),
                "MDEとの比較": mde_mark(r["d2"], r["mde"]),
                "隣の分位": neighbours(g, per_group, judge),
            }
            if judge:
                verdict, power = decide(r["n1"], r["n2"], r["t"], r["d2"], r["mde"],
                                        mde_unit(col))
                row.update({
                    "t": _fmt(r["t"], 4), "ブートストラップSE": _fmt(r["se_b"]),
                    "有限な複製の本数": _fmt(r["reps"]),
                    "CI下限": _fmt(r["lo"]), "CI上限": _fmt(r["hi"]),
                    "検出力": power, "バー近傍": bar_near(r["t"]), "判定": verdict,
                })
            else:
                row["検出力"] = ("n < 30" if r["n1"] < MIN_N
                                 else ("n2 < 30" if r["n2"] < MIN_N else ""))
            out.append(row)
    return out


# =============================================================================
# F1 の 12 セル(§7.0)
# =============================================================================
F1_GROUP = "D_Q1"   # 主軸 D の D1 = `doi_pre_1h` が最も負の 3 分位


def f1_cut_note(groups: list) -> tuple[float | None, str]:
    """**決定 2(9 回目の指摘 2)**: D1 の**上側の切り値**と、その射程の 1 行。

    **F1 の判定は「主軸 D の D1(`doi_pre_1h` が最も負の 3 分位)」のまま**である
    (**走行後に「負の群」へ読み替えない** = A-6)。
    **切り値が 0 以上なら「D1 は負の群と一致しない(切り値 X)」を射程として必ず書く。**

    **射程**: 切り値が出ない(群が空 / NaN)ときも、そのことを 1 行書く。
    """
    g = next((x for x in groups if getattr(x, "name", None) == F1_GROUP), None)
    cuts = getattr(g, "cuts", None) if g is not None else None
    if not cuts or cuts[0] is None or not math.isfinite(float(cuts[0])):
        return None, ("D1 の上側の切り値が出ない(群が空、または NaN)ので、"
                      "D1 が負の群と一致するかを確かめられない")
    cut = float(cuts[0])
    if cut >= 0:
        return cut, (f"D1 は負の群と一致しない(切り値 {cut:.6g})"
                     "。判定は D1(最も負の 3 分位)のまま行う")
    return cut, (f"D1 の上側の切り値は {cut:.6g}(負)なので、"
                 "D1 の全員が `doi_pre_1h` < 0 である")


def f1_cells(judge_rows: list[dict]) -> list[dict]:
    """主軸 D の D1 × 戻り到達 2 系統 × h 6 本 = 12 セル。走行は gap60_w8。"""
    want = {c.format(h=h) for c, _ in JUDGE_SYSTEMS for h in HORIZONS}
    return [r for r in judge_rows if r["群"] == F1_GROUP and r["観測量"] in want]


def f1_reading(cells: list[dict]) -> str:
    """§7.0 の読み。**決定 5** の数え方で決める。

      整合 = 差あり(+) ≥ 1 かつ 差あり(−) 0
      反証 = 差あり(−) ≥ 1 かつ 差あり(+) 0
      混在 = 両方ある
      不明 = 差ありが 1 つも無い(**内訳を併記する**。決定 17' で
             「不明(MDE 未算出)」が、決定 1'' / 20'' で「不明(t 未算出)」
             「不明(n2 < 30)」が内訳に増えた)
    """
    if len(cells) != 12:
        return f"読めない(12 セルのはずが {len(cells)} セル)"
    pos = sum(1 for c in cells if c["判定"] == "差あり(+)")
    neg = sum(1 for c in cells if c["判定"] == "差あり(−)")
    if pos and neg:
        return f"混在(差あり(+) {pos} / 差あり(−) {neg})"
    if pos:
        return f"F1 と整合(差あり(+) {pos} / 差あり(−) 0)"
    if neg:
        return f"F1 の反証(差あり(−) {neg} / 差あり(+) 0)"
    few = sum(1 for c in cells if c["判定"] == UNKNOWN_N)
    few2 = sum(1 for c in cells if c["判定"] == UNKNOWN_N2)
    not_ = sum(1 for c in cells if c["判定"] == UNKNOWN_T)
    nom = sum(1 for c in cells if c["判定"] == UNKNOWN_MDE)
    nod = sum(1 for c in cells if c["判定"].startswith("検出されず"))
    return (f"不明(差あり 0。内訳: {UNKNOWN_N} {few} / {UNKNOWN_N2} {few2} / "
            f"{UNKNOWN_T} {not_} / {UNKNOWN_MDE} {nom} / 検出されず {nod})")


# =============================================================================
# 「なぜ」の欄(§10.3。欄の形だけ。中身は結果の後に書く)
# =============================================================================
WHY_HEADER = [
    "読み", "候補1:機構にエッジが無い", "候補2:実装が意図を反映していない",
    "候補3:バグ", "候補4:検出力不足", "2周目に測るもの",
]
WHY_READINGS = ("F1 と整合", "F1 の反証", "混在", "不明")
WHY_PLACEHOLDER = "(結果を見てから書く。空欄にしない)"


# =============================================================================
# 書き出し
# =============================================================================
def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def write_md5(out: Path, names: list[str]) -> None:
    lines = []
    for n in sorted(names):
        h = hashlib.md5((out / n).read_bytes()).hexdigest()
        lines.append(f"{h}  {n}")          # `./` を付けない相対パス
    (out / "MD5SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


STOPPED_NAME = "stopped.txt"

# **決定 4(prereg 監査(10 回目)の指摘 4)**: `stopped.txt` の引き金は **5 つ**である
# (params / サニティ #14 / 軸の作り方 / 承認の番号 / **道具の版**)。
# **前版は版の関門だけ `stopped.txt` を書かずに終わっていたので、
# 「456 日を 6 本開けて、理由のファイルすら残らない」経路があった。**
CHK_TOOL_VERSION = "道具の版(決定 3・15 + 1・2・3)"


# **決定 12(prereg 監査(8 回目)の指摘 12)**: `stopped.txt` に書いてよいのは
# **検査の名前・走行の名前・件数だけ**である。**値は 1 つも書かない。**
# **前版は検査の理由文をそのまま貼っていたので、`bin_pct` の差の最大値(§4 の分割軸 B の値)や
# `cascade_id` の例が出力に入りえた。**§14.4.1 の汚染の線は
# 「§4.3 の観測量も §4 の分割軸の値も含まれない」なので、そちらに揃える。
# **行は理由文から組み立てず、名前と件数だけを拾って新しく作る**
# (**濾すのではなく作る**ので、拾わなかったものは 1 つも出ない)。
_COUNT_RE = re.compile(r"(\d+)\s*件")


def stopped_line(check: str, msg: str, prefix: str = "") -> str:
    """破れた 1 件を「検査の名前 / 走行の名前 / 件数」だけの 1 行にする(決定 12)。

    走行の名前は理由文の最初の「:」より前(検査の関数が `f"{who}: …"` で書く)。
    件数は「N 件」の形で書かれているものだけを写す(**無ければ書かない**)。
    **理由文そのものは 1 文字も出さない。**
    """
    who = msg.split(":", 1)[0].strip() if ":" in msg else "(走行名なし)"
    m = _COUNT_RE.search(msg)
    cnt = f" / {m.group(1)} 件" if m else ""
    return f"  - {prefix}[{check}] {who}{cnt}"


def write_stopped(out: Path, judge_bad: list[tuple[str, str]],
                  sens_bad: dict[str, list[tuple[str, str]]]) -> Path:
    """**決定 2'''''(7 回目の指摘 2)**: 判定の側の検査が破れたときの記録を書く。

    中身は「**破れた検査の名前・走行の名前・件数**」だけである
    (**決定 12(8 回目の指摘 12)。観測量も分割軸の値も 1 つも書かない**)。

    **引き金は 5 つである**(**決定 4。10 回目の指摘 4**):
    **params / サニティ #14 / 軸の作り方 / 承認の番号 / 道具の版**。
    **前版は版の関門だけ 1 ファイルも書かずに終わっていた。**
    **表は 1 枚も書かない。**§10.3 の「なぜ」を書くときの材料はこのファイルと
    標準出力(理由の全文はそちらに出る)と `summary.json` の感度の記録である。
    **判定語の走査を通してから書く**(通らなければ検査の名前だけにする)。
    """
    lines = ["段 A の読み: 判定の表を 1 枚も書かずに止まった(決定 2''''')。", ""]
    lines.append("破れた検査(判定に使う走行とその標本。**検査の名前・走行の名前・件数だけ**):")
    for check, msg in judge_bad:
        lines.append(stopped_line(check, msg))
    if sens_bad:
        lines.append("")
        lines.append("同じ回に感度の走行でも破れた検査(参考):")
        for nm, items in sens_bad.items():
            for check, msg in items:
                lines.append(stopped_line(check, msg, prefix=f"[{nm}] "))
    lines += [
        "",
        "事前登録 §14.6 の決まり: --mode full の再走行はしない。",
        "破れた走行に依存する判定は「不明(検査で止まった)」として結果に書き、",
        "1 周目はそこで終わる。再走行は新しい開封として §3.1 に数え、オーナーの決定が要る。",
    ]
    text = "\n".join(lines) + "\n"
    if scan_rows_forbidden({STOPPED_NAME: text}):
        # 検査の文言に判定語が混ざった場合だけ、名前の一覧に落とす(語は出さない)。
        text = ("段 A の読み: 判定の表を 1 枚も書かずに止まった(決定 2''''')。\n"
                "破れた検査: "
                + " / ".join(sorted({c for c, _ in judge_bad})) + "\n"
                "理由の文言に判定語が混ざっていたので、本文は書いていない"
                "(標準出力を見る)。\n")
    out.mkdir(parents=True, exist_ok=True)
    (out / STOPPED_NAME).write_text(text, encoding="utf-8")
    return out / STOPPED_NAME


def scan_forbidden(out: Path, names: list[str]) -> list[str]:
    hits = []
    for n in names:
        text = (out / n).read_text(encoding="utf-8", errors="replace")
        for w in FORBIDDEN:
            if w in text:
                hits.append(f"{n}: {w}")
    return hits


def scan_rows_forbidden(blobs: dict[str, object]) -> list[str]:
    """**決定 11''**: 表を**書く前**に、メモリ上の行と文字列へ判定語を当てる。

    `blobs` は「出す予定のファイル名 -> 行の一覧 / 文字列 / 辞書」。
    **前版は 7 ファイルを書き終えた後に走査していたので、見つかっても書いた表が残り、
    `MD5SUMS` だけが書かれない形になっていた**(走行前の再監査(4 回目)の指摘 11)。
    §14.6 の関門も サニティ #14 も「1 ファイルも書かない」形なので、ここも揃える。
    """
    hits: list[str] = []
    for name, obj in blobs.items():
        if isinstance(obj, str):
            text = obj
        elif isinstance(obj, list):
            text = "\n".join(
                "\t".join(str(v) for v in (r.values() if isinstance(r, dict) else [r]))
                for r in obj
            )
        else:
            text = json.dumps(obj, ensure_ascii=False)
        for w in FORBIDDEN:
            if w in text:
                hits.append(f"{name}: {w}")
    return hits


def check_root_for_out_dir(out_dir: Path, root: Path) -> list[str]:
    """**決定 10''**: 本番の出力に試験用の台帳を使わせない。

    `--out-dir` がリポジトリの `backtest_data/` の下にあるのに `--root` が
    リポジトリ直下でないなら、**別の台帳の「判定: 通す」で本番の表が書ける。**
    その組を止める(**試験は `--out-dir` も一時ディレクトリに置くので当たらない**)。
    """
    repo = Path(__file__).resolve().parent.parent
    try:
        out_dir.resolve().relative_to((repo / "backtest_data").resolve())
    except ValueError:
        return []
    if root.resolve() != repo.resolve():
        return [f"--out-dir がリポジトリの backtest_data/ の下({out_dir})なのに "
                f"--root がリポジトリ直下ではない({root})。"
                f"本番の出力に試験用の台帳は使えない。"]
    return []


# =============================================================================
# 関門(`CLAUDE.md` §5.0 の 2)
# =============================================================================
def pass_audit_gate(root: Path) -> None:
    """表を 1 枚も書く前に通す。迂回する旗は無い。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _research_audit_gate import require_audit

    try:
        require_audit(UNIT, "結果", root)
    except SystemExit:
        sys.stderr.write(
            "\n[止め] 測定後・報告前の監査が通っていないので、表を 1 枚も書かずに終わる。\n"
            f"       単位: {UNIT} / 段階: 結果 / 台帳: {root}/docs/AUDITOR/ACTION_LOG.md\n"
        )
        raise SystemExit(1) from None


# =============================================================================
# 本体
# =============================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="段 A の結果を事前登録どおりに読む(判定区間を開ける前に書いた)"
    )
    ap.add_argument("--run-w8", required=True, help="gap 60 秒 × W 8h の走行の出力ディレクトリ")
    ap.add_argument("--run-w24", required=True, help="gap 60 秒 × W 24h の走行の出力ディレクトリ")
    ap.add_argument("--sample-w8", required=True,
                    help="標本 6 日の gap60_w8(MDE の p・s の出所。§8.6)")
    ap.add_argument("--sample-w24", default=None,
                    help="標本 6 日の gap60_w24(既定は --sample-w8 の隣の gap60_w24)")
    ap.add_argument("--out-dir", required=True)
    # **決定 1''': `--seed` と `--reps` は無い。**定数 `SEED` / `REPS` である
    # (走行前の再監査(5 回目)の指摘 1。**開封の後に引き直せる経路を閉じた**)。
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent),
                    help="監査の台帳(docs/AUDITOR/ACTION_LOG.md)と事前登録"
                         "(§14.4 の「応答の L 番号」)の場所を差し替える引数(試験用)。"
                         "--out-dir がリポジトリの backtest_data/ の下なら"
                         "リポジトリ直下でなければ止まる")
    ap.add_argument("--sens", action="append", default=[], metavar="NAME=DIR[:SAMPLE_DIR]",
                    help="感度の走行(繰り返し可)。観測のみの表 observation_only_<NAME>.csv "
                         "を 1 本ずつ出す(t と判定の列なし。決定 19')。"
                         "`:SAMPLE_DIR` を付けると、その標本から MDE の p・s を取る(決定 8'')")
    a = ap.parse_args(argv)

    # --- 決定 4'''': 反復回数と種を**実行時に**リテラルと突き合わせる -----------
    # **引数を消しただけでは閉じていなかった**(モジュール属性への代入で差し替えられる
    # = 走行前の再監査(6 回目)の指摘 4 の実測)。**走行のたびにここで測る。**
    if REPS != REPS_FROZEN_LITERAL or SEED != SEED_FROZEN_LITERAL:
        sys.stderr.write(
            "[止め] 反復回数と種が §9.1 で凍結した値と違う。表を 1 枚も書かずに終わる。\n"
            f"       REPS = {REPS}(凍結した値は {REPS_FROZEN_LITERAL}) / "
            f"SEED = {SEED}(凍結した値は {SEED_FROZEN_LITERAL})\n")
        return 1

    # --- 決定 5'''': MDE の単位の固定表に穴が無いか ----------------------------
    missing_units = sorted({c for c, _k, _h in judge_systems() + observation_systems()
                            if not mde_unit(c)})
    if missing_units:
        sys.stderr.write(
            "[止め] MDE の単位の固定表(§10.1)に無い観測量がある。"
            "表を 1 枚も書かずに終わる。\n"
            + "".join(f"       - {c}\n" for c in missing_units))
        return 1

    # --- 決定 10'': 本番の出力に試験用の台帳を使わせない -----------------------
    bad = check_root_for_out_dir(Path(a.out_dir), Path(a.root))
    if bad:
        sys.stderr.write("[止め] " + "".join(f"{b}\n" for b in bad))
        return 1

    s24 = Path(a.sample_w24) if a.sample_w24 else Path(a.sample_w8).parent / RUN_W24
    runs = {RUN_W8: Run(RUN_W8, Path(a.run_w8)), RUN_W24: Run(RUN_W24, Path(a.run_w24))}
    # 標本の走行は判定の走行と同じ鍵で引くが、**名前は分けておく**
    # (サニティ #14 や params の検査の文言で、どちらが破れたかが分かるように)。
    samples = {RUN_W8: Run(f"{RUN_W8}(標本)", Path(a.sample_w8)),
               RUN_W24: Run(f"{RUN_W24}(標本)", s24)}

    sens: dict[str, Run] = {}
    sens_samples: dict[str, Run] = {}
    sens_unreadable: dict[str, str] = {}   # 決定 2''''': 読めなかった感度(名前 -> 理由)
    for spec in a.sens:
        if "=" not in spec:
            sys.stderr.write(
                f"[止め] --sens は NAME=DIR または NAME=DIR:SAMPLE_DIR の形で渡す: {spec}\n")
            return 1
        nm, _, rest = spec.partition("=")
        nm = nm.strip()
        d, _, smp = rest.partition(":")       # 決定 8'': 標本は任意
        if nm in runs or nm in sens or nm in sens_unreadable:
            sys.stderr.write(f"[止め] --sens の名前が重なっている: {nm}\n")
            return 1
        # **決定 2'''''(7 回目の指摘 2)**: 感度の走行が読めないことも「その走行の検査が
        # 破れた」として扱う(**判定の表は書く**)。**判定の 2 本とその標本は上で素直に
        # 読んでいる**(読めなければ例外で落ちる = 判定の側は 1 行も出さない)。
        try:
            sens[nm] = Run(nm, Path(d.strip()))
        except OSError as e:
            sens_unreadable[nm] = f"{nm}: 感度の走行が読めない({d.strip()}): {e}"
            continue
        if smp.strip():
            try:
                sens_samples[nm] = Run(f"{nm}(標本)", Path(smp.strip()))
            except OSError as e:
                sens_unreadable[nm] = (
                    f"{nm}(標本): 感度の標本が読めない({smp.strip()}): {e}")
                sens.pop(nm, None)

    # --- 決定 2'''''(7 回目の指摘 2): 感度 4 本は必ず渡す ----------------------
    # **感度の走行の検査が破れても判定の表は書く**(下)ので、**渡し忘れで感度が
    # 「無かったこと」になる形を先に塞ぐ。**§14.2 の 4 本をすべて要求する。
    missing_sens = [nm for nm in SENS_REQUIRED
                    if nm not in sens and nm not in sens_unreadable]
    extra_sens = [nm for nm in list(sens) + list(sens_unreadable)
                  if nm not in SENS_REQUIRED]
    if missing_sens or extra_sens:
        sys.stderr.write(
            "[止め] --sens が §14.2 の 4 本と合わない。表を 1 枚も書かずに終わる。\n"
            f"       要る名前: {' / '.join(SENS_REQUIRED)}\n"
            + (f"       渡っていない: {' / '.join(missing_sens)}\n" if missing_sens else "")
            + (f"       4 本に無い名前: {' / '.join(extra_sens)}\n" if extra_sens else ""))
        return 1

    # --- 決定 2'''': 事前登録 §14.4 の「応答の L 番号」を読む -------------------
    prereg = Path(a.root) / PREREG_REL
    approval, approval_note = read_approval_from_prereg(prereg)
    if approval is None:
        sys.stderr.write(
            "[止め] 事前登録 §14.4 の「応答の L 番号」が読めないので、"
            "表を 1 枚も書かずに終わる。\n"
            f"       {approval_note}\n"
            "       オーナーの応答(L 番号)を §14.4 の欄に書き写してから走らせる。\n")
        return 1

    # --- 決定 11(8 回目の指摘 11): 関門を `stopped.txt` より前に通す ------------
    # **前版は `write_stopped` が `pass_audit_gate` より前にあったので、
    # 判定側が破れた回は台帳が閉じていても `stopped.txt` が 1 ファイル書かれた。**
    # **「閉じていれば 1 ファイルも書かない」に揃える。**
    pass_audit_gate(Path(a.root).resolve())

    # --- 決定 3・15(9 回目)+ 決定 1・2・3・4(10 回目): 版の担保 ---------------
    # **前版は「欄が「(まだ無い)」なら記録だけして進む」だった**ので、
    # **欄を空のままにすれば版の検査は 1 つも掛からなかった。**
    # **9 回目の版は「作業ツリー全体が clean」を要求したので、出力先・台帳・TRACE・
    # 事前登録の書き込みで必ず汚れ、6 本を走らせきれない**(10 回目の指摘 1・2。
    # **設計上の帰結。6 本を走らせて確かめたわけではない**)。
    # **また `tool_commit` が `git rev-parse HEAD` だったので、欄に書ける値
    # (書き写す直前のコミット)と定義上一致しなかった**(同 指摘 3)。
    # **本版は担保の単位を「凍結した道具の 2 ファイル」に限る**:
    # **(i) 読みの道具の側で 2 ファイルに未コミットの変更が無い /
    # (ii) 6 本の `tool_commit` がすべて同じで §14.4 の欄と一致 /
    # (iii) 6 本とも道具が汚れていない。**
    # **1 つでも欠ければ表を 1 枚も書かずに終わる。**
    # **決定 4(10 回目の指摘 4)**: **このとき `stopped.txt` は書く**
    # (**前版はこの関門だけ 1 ファイルも書かずに終わったので、
    # 「456 日を開けて理由のファイルすら残らない」経路があった**)。
    # **本版では台帳の関門 `pass_audit_gate` の後ろに置く**(台帳が閉じている回は、
    # **版の検査より先に止まる** = `tests/test_audit_gates_wired.py` が測っている経路)。
    my_commit = tool_commit()
    my_dirty, my_rc = tool_dirty()
    my_state = "dirty" if my_dirty else "clean"
    frozen_commit, frozen_note = read_frozen_commit_from_prereg(prereg)
    version_bad = check_tool_versions(
        [(nm, r) for nm, r in runs.items()] + [(nm, r) for nm, r in sens.items()],
        frozen_field=frozen_commit, my_commit=my_commit, my_state=my_state)
    if version_bad:
        write_stopped(Path(a.out_dir),
                      [(CHK_TOOL_VERSION, b) for b in version_bad], {})
        sys.stderr.write(
            "[止め] 道具の版が担保できない(事前登録 §14.4 の決定 3・15 と 1・2・3)。"
            "表を 1 枚も書かずに終わる"
            f"(破れた検査は {Path(a.out_dir) / STOPPED_NAME} に書いた = 決定 4)。\n"
            f"       この道具: {my_commit} / 凍結した道具の 2 ファイル: {my_state}"
            f"(git diff --quiet HEAD の終了コード {my_rc})\n"
            f"       {frozen_note}\n"
            + "".join(f"       - {b}\n" for b in version_bad))
        return 1

    # === 3 つの検査(params / サニティ #14 / 軸の作り方)==========================
    # **決定 2'''''(走行前の再監査(7 回目)の指摘 2)**:
    # **前版はこの 3 つのどれか 1 つでも破れると「表を 1 枚も書かずに終わる」形だったので、
    # 感度 1 本の食い違いでも 576 行すべてが読めなくなった。**
    # **456 日を 6 本開けたうえで 1 行も出さずに 1 周目が終わる、という帰結になる。**
    # **判定の側(判定 2 本とその標本)と感度の側を分ける**:
    #   * 判定の側が破れたら、**表は書かないが `stopped.txt`(破れた検査・走行・理由)を
    #     出力先に書く**(§10.3 の「なぜ」の材料をここに残す)。
    #   * 感度の側が破れたら、**その走行の表だけ書かず `summary.json` に記録し、
    #     判定の表は書く**(感度は観測のみで、576 にも α にも F1 の読みにも入らない)。
    judge_bad: list[tuple[str, str]] = []      # (検査の名前, 理由)
    sens_bad: dict[str, list[tuple[str, str]]] = {nm: [] for nm in sens}
    for nm, why in sens_unreadable.items():
        sens_bad.setdefault(nm, []).append(("感度の走行が読めない", why))

    def _sens_add(nm: str, check: str, msgs: list[str]) -> None:
        sens_bad[nm] += [(check, m) for m in msgs]

    # --- 決定 12''': 渡されたディレクトリが名前どおりの走行か(params の検査)-----
    CHK_PARAMS = "params の検査(決定 12''')"
    bad = []
    for nm, r in runs.items():
        # **決定 14(9 回目の指摘 14)**: **承認の番号だけは `params` の検査から外す。**
        # **前版は判定 2 本の approval の食い違いが `CHK_PARAMS` の名前で
        # `stopped.txt` に出たので、「承認の番号が破れた」ことを
        # `stopped.txt` だけでは見分けられなかった**(`stopped.txt` は理由を書かない
        # = 決定 12)。**下の `CHK_APPROVAL` で感度 4 本と同じ名前にそろえる。**
        bad += check_run_params(r, mode="full", gap_sec=GAP_SEC_JUDGE,
                                window_hours=WINDOW_HOURS_FIXED[nm],
                                n_days=JUDGMENT_N_DAYS, label=nm,
                                settings=True)
    # **決定 9''''(6 回目の指摘 9)**: 標本の側にも `window_hours` と `gap_ms` を当てる
    # (**標本 4 本の `summary.json` に値がある = 実測済み**)。
    # **前版は `mode` と日数の 2 つしか見ておらず、「W = 24h の標本を `--sample-w8` に
    # 渡す」取り違えが止まらなかった。**
    for nm, r in samples.items():
        bad += check_run_params(r, mode="sample", n_days=SAMPLE_N_DAYS,
                                gap_sec=GAP_SEC_JUDGE,
                                window_hours=WINDOW_HOURS_FIXED[nm],
                                label=f"{nm}(標本)")
    judge_bad += [(CHK_PARAMS, b) for b in bad]
    for nm, r in sens.items():
        want = _sens_name_params(nm)
        if want is None:
            _sens_add(nm, CHK_PARAMS,
                      [f"{nm}: --sens の名前が gap<秒>_w<時間> の形でないので、"
                       f"走行の params と突き合わせられない"])
            continue
        # **決定 11'''''(7 回目の指摘 11)**: **感度 4 本も同じ 456 日を開ける**ので、
        # **`params.approval` も判定 2 本と同じ L 番号と突き合わせる。**
        # **決定 14(8 回目の指摘 14)**: **`approval` の食い違いだけは判定側の破れと
        # 同じ扱いにする**(承認外の番号で 456 日を開けた走行が 1 本でもあれば、
        # 1 周目はそこで止めてオーナーに報告する)。**よってここでは `approval=None` で呼び、
        # 承認の番号は下の `CHK_APPROVAL` で `judge_bad` に入れる。**
        _sens_add(nm, CHK_PARAMS,
                  check_run_params(r, mode="full", gap_sec=want[0],
                                   window_hours=want[1], n_days=JUDGMENT_N_DAYS,
                                   label=nm, settings=True))
    for nm, r in sens_samples.items():
        want = _sens_name_params(nm)
        if want is None:
            _sens_add(nm, CHK_PARAMS,
                      [f"{nm}(標本): --sens の名前が gap<秒>_w<時間> の形でないので、"
                       f"標本の params と突き合わせられない"])
            continue
        _sens_add(nm, CHK_PARAMS,
                  check_run_params(r, mode="sample", n_days=SAMPLE_N_DAYS,
                                   gap_sec=want[0], window_hours=want[1],
                                   label=f"{nm}(標本)"))

    # --- 決定 14(8 回目の指摘 14): 承認の番号は感度でも判定側の破れとして扱う ----
    # **リードの決定の逐語**: 「**感度 4 本の `params.approval` の食い違いは判定側の
    # 破れと同じ扱い(表を 1 枚も書かず `stopped.txt`)。理由: 承認外の番号で 456 日を
    # 開けた走行が 1 本でもあれば、1 周目はそこで止めてオーナーに報告する**」。
    # **決定 14(9 回目の指摘 14)**: **判定 2 本の承認の食い違いも同じ名前で出す。**
    # **`stopped.txt` は検査の名前しか書かない**(決定 12)ので、
    # **名前が `params の検査` のままだと「承認の番号が破れた」ことが見分けられなかった。**
    CHK_APPROVAL = "承認の番号(決定 14)"
    for nm, r in runs.items():
        judge_bad += [(CHK_APPROVAL, b)
                      for b in check_run_approval(r, approval, label=nm)]
    for nm, r in sens.items():
        judge_bad += [(CHK_APPROVAL, b)
                      for b in check_run_approval(r, approval, label=nm)]

    # --- サニティ #14(決定 6' + 12'' + 2'''): 1 対 1 の対応を走行ごとに測る ----
    # **決定 2'''(5 回目の指摘 2)**: **標本の走行にも掛ける。**
    # 標本の 1 対 1 が崩れると MDE の `p`・`s` の母集団が黙って変わるので、
    # 判定の走行と同じ検査を当てる。
    CHK_PAIRING = "サニティ #14(1 対 1 の対応)"
    for r in list(runs.values()) + list(samples.values()):
        judge_bad += [(CHK_PAIRING, b) for b in check_pairing(r)]
    for nm, r in sens.items():
        _sens_add(nm, CHK_PAIRING, check_pairing(r))
    for nm, r in sens_samples.items():
        _sens_add(nm, CHK_PAIRING, check_pairing(r))

    # --- 決定 3'': 対照 (ii) の軸の作り方が事前登録の固定と一致するか ----------
    # **決定 8''''(6 回目の指摘 8)**: **標本の走行にも掛ける。**
    # 標本側の群分けも `control_axis_kinds` の結果で決まる(`membership`)ので、
    # 列の在り方が違えば MDE の `p`・`s` の母集団が変わる。サニティ #14 と同じ形にした。
    CHK_AXIS = "対照 (ii) の軸の作り方(決定 3'')"
    for r in list(runs.values()) + list(samples.values()):
        judge_bad += [(CHK_AXIS, b) for b in check_axis_kinds(r)]
    for nm, r in sens.items():
        _sens_add(nm, CHK_AXIS, check_axis_kinds(r))
    for nm, r in sens_samples.items():
        _sens_add(nm, CHK_AXIS, check_axis_kinds(r))

    # --- 判定の側が破れたら stopped.txt を書いて終わる(表は 1 枚も書かない)-----
    if judge_bad:
        write_stopped(Path(a.out_dir), judge_bad,
                      {nm: v for nm, v in sens_bad.items() if v})
        sys.stderr.write(
            "[止め] 判定に使う走行の検査が通らない。表を 1 枚も書かずに終わる"
            f"(破れた検査は {Path(a.out_dir) / STOPPED_NAME} に書いた)。\n"
            + "".join(f"       - [{c}] {b}\n" for c, b in judge_bad)
        )
        return 1

    # --- 感度の側が破れた走行は落とす(判定の表は書く。決定 2''''')--------------
    sens_dropped = {nm: v for nm, v in sens_bad.items() if v}
    for nm in sens_dropped:
        sens.pop(nm, None)
        sens_samples.pop(nm, None)
        sys.stderr.write(
            f"[注意] 感度の走行 {nm} は検査が通らないので、その表を書かない"
            "(判定の表は書く。理由は summary.json の"
            "「感度の走行の検査(決定 2''''')」)。\n"
            + "".join(f"       - [{c}] {b}\n" for c, b in sens_bad[nm])
        )

    groups = build_groups(runs[RUN_W8], runs[RUN_W24])
    if len(groups) != N_GROUPS:
        sys.stderr.write(f"[止め] 群が {len(groups)} 個。§4 の 48 群と違う。\n")
        return 1

    boot = {}
    for name, run in list(runs.items()) + list(sens.items()):
        rng = np.random.default_rng(SEED)          # 決定 1''': 定数(引数では変えられない)
        nd = len(run.days)
        boot[name] = rng.integers(0, nd, size=(REPS, nd)) if nd else np.zeros((REPS, 0), int)

    judge_rows = build_rows(runs, samples, groups, boot, judge=True)
    if len(judge_rows) != N_TESTS:
        sys.stderr.write(f"[止め] 判定の行が {len(judge_rows)} 行。§4.3 の 576 と違う。\n")
        return 1
    obs_rows = build_rows(runs, samples, groups, boot, judge=False)
    # 決定 6: W に依らない 12 群の W = 24h 側は、判定ではなく観測のみの表に出す。
    flat24 = build_flat_groups_w24(runs[RUN_W24])
    obs_rows += build_rows(runs, samples, flat24, boot, judge=False,
                           systems=judge_systems())
    # **決定 6'''''(7 回目の指摘 6)**: **この表の行も 576 にも α にも F1 の読みにも
    # 1 行も入らない**ので、MDE の列見出しを族の α の名前にしない。
    obs_rows = to_ref_mde_rows(obs_rows)
    # 決定 19': 感度 1 本ごとに観測のみの表を 1 枚ずつ出す(判定には 1 行も入らない)。
    sens_rows: dict[str, list[dict]] = {}
    for nm, r in sens.items():
        gs = build_groups_single(r)
        smp = {nm: sens_samples[nm]} if nm in sens_samples else {}
        sens_rows[nm] = to_sens_rows(build_rows(
            {nm: r}, smp, gs, boot, judge=False,
            systems=judge_systems() + observation_systems(),
        ))
    cells = f1_cells(judge_rows)
    # **決定 13''''(6 回目の指摘 13)**: **12 セルでなければ「[止め]」で 1 ファイルも書かない。**
    # **前版は「読めない(12 セルのはずが N セル)」という文字列を返すだけで、
    # そのまま全部の表が書かれ、終了コードは 0 になっていた。**
    # 同じスクリプトの他の食い違い(#14 / params / 軸の作り方 / 群の数 / 576 行)は
    # すべて「[止め]」で 1 ファイルも書かない。**F1 の 12 セルもそれに揃える。**
    if len(cells) != 12:
        sys.stderr.write(
            f"[止め] F1 の 12 セル(§7.0)が {len(cells)} セルしか揃っていない。"
            "表を 1 枚も書かずに終わる。\n"
            f"       群 {F1_GROUP} × 戻り到達 2 系統 × h {len(HORIZONS)} 本 = 12 が要る。\n")
        return 1
    reading = f1_reading(cells)

    # --- 出す中身をここで全部そろえる(まだ 1 ファイルも書かない。決定 11'')------
    out = Path(a.out_dir)
    why_rows = [{**{k: WHY_PLACEHOLDER for k in WHY_HEADER}, "読み": r}
                for r in WHY_READINGS]
    # **決定 2(9 回目の指摘 2)**: D1 の上側の切り値を必ず書き残す。
    # **「負の群」という語は事前登録から消し、判定は D1(最も負の 3 分位)のまま行う。**
    # **切り値が 0 以上なら、その射程を `f1_reading.txt` にも `summary.json` にも書く。**
    f1_cut, f1_cut_line = f1_cut_note(groups)
    f1_text = (
        "§7.0 の 4 分岐のうちの読み: " + reading + "\n"
        "見たセル: 主軸 D の D1 × 戻り到達 2 系統 × h 6 本 = "
        f"{len(cells)} セル(走行 {RUN_W8})\n"
        f"D1 の上側の切り値(doi_pre_1h): "
        f"{'(出ない)' if f1_cut is None else format(f1_cut, '.6g')}\n"
        f"射程: {f1_cut_line}\n"
    )
    # **決定 7'''''(7 回目の指摘 7)**: **「最小」「最大」も検定したセルだけから取る。**
    # **前版は `judge_rows` 全部から取っていたので、群が空で本数 0 のセルが混ざり、
    # 「最小 0」が出た。**§10.3 は「本数が少ないセル」と「検定が成り立たないセル」を
    # 別の欄に分けると決めたのに、最小・最大はその区別の外にあった(標準出力も同じ)。
    _untested = (UNKNOWN_N, UNKNOWN_N2)
    reps_used_all = [int(r["有限な複製の本数"]) for r in judge_rows
                     if r.get("有限な複製の本数") != "" and r["判定"] not in _untested]
    # **決定 16'''(5 回目の指摘 16)**: 本数が `REPS` に満たないセルを 1 行ずつ出す。
    # **閾値は置かない**(A-12)。**読む人が「本数 2 のセル」と「本数 2,000 のセル」を
    # 見分けられるようにするための一覧である**(§10.3 の併記の規約)。
    # **決定 12''''(6 回目の指摘 12)**: **群が空 / n < 30 で検定していないセルを一覧から除く。**
    # **前版は `本数 < REPS` の行を全部入れていたので、群が空で本数 0 のセル
    # (判定は「不明(n < 30)」)も混ざり、`1/√(2·n)` が `None` になっていた。**
    # **「本数が少ないセル」と「検定が成り立たないセル」は別の欄に分ける。**
    # (`_untested` は上で定義済み。決定 7''''' で最小・最大にも同じ区別を当てた。)
    low_reps_cells = [
        {"観測量": r["観測量"], "群": r["群"], "h": r["h"],
         "n1": int(r["n1"]), "n2": int(r["n2"]),
         "有限な複製の本数": int(r["有限な複製の本数"]),
         "1/√(2·n)": round(1.0 / math.sqrt(2 * int(r["有限な複製の本数"])), 6)
         if int(r["有限な複製の本数"]) > 0 else None}
        for r in judge_rows
        if r.get("有限な複製の本数") != "" and int(r["有限な複製の本数"]) < REPS
        and r["判定"] not in _untested
    ]
    untested_cells = sum(1 for r in judge_rows if r["判定"] in _untested)

    summary = {
        "単位": UNIT,
        "事前登録": "docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md(確定版・凍結)",
        # **決定 16(8 回目)+ 決定 3(10 回目)**: 読みの道具の版
        # (`git log -1 --format=%H -- <道具 2 ファイル>`)。
        "tool_commit": my_commit,
        "seed": SEED,
        "reps": REPS,
        "seed と reps の出所": ("定数(引数では変えられず、実行時にも 2000 / 1 と"
                                "突き合わせる。決定 1''' + 4''''。§9.1 で凍結した値)"),
        "CI水準": {"alpha": ALPHA, "クラスタ": "UTC 日",
                   "方法": (f"正規近似(差 ± z × ブートストラップ SE。"
                            f"z = {BAR_T_SHOWN} は丸め表示で、計算は norm.ppf(1 − α/2))"),
                   "z_{1-α/2}": BAR_T,
                   "注": "|t| ≥ z と CI が 0 を除外することは同値である"},
        "バー": {"|t|": BAR_T, "|t|の丸め表示": BAR_T_SHOWN, "最低イベント数": MIN_N,
                 "最低イベント数の当て先": "その検定に使う、欠測を引いた後の実群の件数 n1",
                 "z_{1-α/2}": Z_ALPHA, "z_{1-β}": Z_POWER, "MDEの係数": MDE_Z,
                 "最低イベント数の当て先2": "対照 (ii) の件数 n2 にも同じ 30 を当てる(決定 20'')",
                 "バー近傍の帯": {"半幅": BAR_NEAR_HALFWIDTH,
                                  "注": "|t| が z ± この幅に入る行に列「バー近傍」で ○ を付ける。"
                                        "観測のみで、判定は変えない(決定 14'')"},
                 "注": "バー・CI・MDE は同じ z(norm.ppf(1 − α/2))を使う(決定 12')"},
        "分岐": BRANCHES,
        "検定の数": len(judge_rows),
        "群の数": len(groups),
        "監査の台帳の根(--root)": str(Path(a.root).resolve()),
        "有限な複製の本数": {
            "注": "セルごとに SE の推定に使えた有限な複製の本数(決定 2'')。"
                  "§9.1 の「SE の相対誤差 ≈ 1/√(2·reps) = 1.58%」は 2,000 本すべてが"
                  "有限のときの値で、少ないセルはその本数で 1/√(2·n) を読む。"
                  "**閾値は置かない**(A-12)。",
            "指定した反復回数": REPS,
            "最小(検定したセルだけ)": (min(reps_used_all) if reps_used_all else None),
            "最大(検定したセルだけ)": (max(reps_used_all) if reps_used_all else None),
            "最小・最大の当て先": (
                "群が空 / n < 30 で検定していないセル(判定が「" + UNKNOWN_N + "」か「"
                + UNKNOWN_N2 + "」)は最小・最大からも外してある(決定 7'''''。"
                "7 回目の指摘 7。前版は judge_rows 全部から取っていたので「最小 0」が出た)。"),
            "指定した反復回数に満たないセルの数(検定したセルだけ)": len(low_reps_cells),
            "指定した反復回数に満たないセルの一覧(検定したセルだけ)": low_reps_cells,
            "群が空 / n < 30 で検定していないセル数": untested_cells,
            "この 2 つを分けた理由": (
                "本数が少ないセル(SE の相対誤差が 1/√(2·n))と、群が空 / n < 30 で"
                "そもそも検定が成り立たないセル(判定は「" + UNKNOWN_N + "」か「"
                + UNKNOWN_N2 + "」)は別の話である(決定 12''''。6 回目の指摘 12)。"),
        },
        "観測のみの表の行数": {
            "observation_only.csv": len(obs_rows),
            **{f"observation_only_{nm}.csv": len(rows_) for nm, rows_ in sens_rows.items()},
        },
        "走行": {
            n: {"path": str(r.path), "window_hours": r.window_hours,
                "日数": len(r.days), "行数": {k: len(v) for k, v in r.by_kind.items()},
                "w_SELL": r.w_sell(),
                "相手がmixed束で落とした合わせた対照": r.n_dropped_mixed_partner,
                "サニティ14_bin_pctの差の最大": r.pairing_worst_bin_pct_gap,
                "サニティ14の結果": r.pairing_report}
            for n, r in list(runs.items()) + list(sens.items())
        },
        # **決定 2''' + 12'''**: 標本の走行にも #14 と params の検査を掛けた(その結果)。
        "標本の走行(サニティ #14 と params の検査を掛けた)": {
            r.name: {"path": str(r.path), "params": {
                "mode": r.params.get("mode"),
                "window_hours": r.params.get("window_hours"),
                "gap_ms": r.params.get("gap_ms"),
                "日数": (len(r.params.get("days"))
                         if isinstance(r.params.get("days"), list) else None)},
                     "サニティ14の結果": r.pairing_report}
            for r in list(samples.values()) + list(sens_samples.values())
        },
        "走行の params の検査": (
            "判定の 2 本 = mode full / gap 60 秒 / W 8h・24h / 日数 456、"
            "標本 = mode sample / 日数 6 / gap 60 秒 / W 8h・24h(決定 9'''')、"
            "感度 = mode full / 日数 456 / gap と W は名前のとおり。"
            "判定 2 本と感度 4 本にはさらに mmr 0.004 / seed 1 / bin_pct 0.1 / "
            "match_order table を突き合わせる(決定 1'''')。"
            "判定 2 本と感度 4 本には params.approval = 事前登録 §14.4 の「応答の L 番号」も"
            "突き合わせる(決定 2'''' + 11'''''。感度 4 本も同じ 456 日を開けるため)。"
            "判定の側が食い違えば「[止め]」で終了コード 1(決定 12'''。迂回する旗は無い)。"
            "感度の側が食い違えば、その走行の表だけ書かずに判定の表は書く"
            "(決定 2'''''。下の「感度の走行の検査」)。"
            "ただし感度 4 本の params.approval の食い違いだけは判定側の破れと同じ扱いで、"
            "表を 1 枚も書かずに " + STOPPED_NAME + " を書いて終わる"
            "(決定 14。8 回目の指摘 14。承認外の番号で 456 日を開けた走行が 1 本でもあれば"
            "1 周目はそこで止める)。"),
        # **決定 2'''''(7 回目の指摘 2)**: 感度の側で破れた検査の記録。
        "感度の走行の検査(決定 2''''')": {
            "渡すべき感度": list(SENS_REQUIRED),
            "表を書かなかった感度": {
                nm: [{"検査": c, "理由": b} for c, b in items]
                for nm, items in sens_dropped.items()
            },
            "注": ("感度の走行で params / サニティ #14 / 軸の作り方 のどれかが破れたら、"
                   "その走行の観測のみの表だけを書かず、判定の表は書く。"
                   "感度の行は 576 にも α にも F1 の読みにも 1 行も入らないためである。"
                   "判定に使う 2 本とその標本で同じ検査が破れたときは、表を 1 枚も書かずに "
                   + STOPPED_NAME + " を書いて終わる。"),
        },
        "凍結した入力の突き合わせ(決定 1'''')": {
            "mmr": MMR_FIXED, "seed": RUN_SEED_FIXED,
            "bin_pct": BIN_PCT_FIXED, "match_order": MATCH_ORDER_FIXED,
            "当てた先": "判定の 2 本と感度 4 本(標本には当てていない)",
        },
        "承認の L 番号(決定 2'''')": {
            "値": approval,
            "出所": approval_note,
            # **決定 10(8 回目の指摘 10)**: 7 回目の処置で感度 4 本にも同じ
            # 突き合わせを当てた(決定 11''''')。**summary の欄も 6 本に直す。**
            "突き合わせ先": "判定 2 本 + 感度 4 本の params.approval",
            "注": "L-199 は「1 = a、9 = a」への応答であって、§13 の 8 件と"
                  "§14.4 の待つものへの応答ではない。走行のたびに事前登録の欄から読む。"
                  "感度 4 本の食い違いは判定側の破れと同じ扱いで、表を 1 枚も書かずに "
                  + STOPPED_NAME + " を書いて終わる(決定 14。8 回目の指摘 14)。",
        },
        # **決定 16(8 回目の指摘 16)**: 読みの道具の版と、事前登録 §14.4 の
        # 「凍結した道具のコミット」の欄との突き合わせ。
        "凍結した道具のコミット(決定 16 + 決定 3・15)": {
            "この道具の版(git log -1 --format=%H -- 道具 2 ファイル)": my_commit,
            "この道具の凍結した道具の状態(git diff --quiet HEAD -- 道具 2 ファイル)":
                my_state,
            "見た範囲": list(TOOL_FILES_REL),
            "git diff --quiet HEAD の終了コード": my_rc,
            "事前登録 §14.4 の欄": frozen_commit,
            "欄の出所": frozen_note,
            "走行ごとの版": {nm: r.summary.get("tool_commit")
                             for nm, r in list(runs.items()) + list(sens.items())},
            "走行ごとの道具の状態": {nm: run_dirty_state(r)
                                     for nm, r in list(runs.items()) + list(sens.items())},
            "突き合わせ": ("(i) 読みの道具の側で凍結した道具の 2 ファイルに未コミットの"
                           "変更が無い / (ii) 判定 2 本 + 感度 4 本の tool_commit が"
                           "すべて同じで §14.4 の欄と一致 / (iii) 6 本とも道具が clean。"
                           "1 つでも欠ければ「[止め]」で表を 1 枚も書かず、stopped.txt だけを"
                           "書く(prereg 監査(9 回目)の指摘 3・15 と"
                           "(10 回目)の指摘 1・2・3・4。リードの決定 1・2・3・4)。"),
            "射程": ("読めない感度の走行はこの検査より前に落ちているので、"
                     "版の検査の対象に入らない(その表は 1 枚も書かれない)。"),
        },
        "F1 の D1 の上側の切り値(決定 2)": {
            "群": F1_GROUP,
            "軸の列": "doi_pre_1h",
            "上側の切り値": f1_cut,
            "射程": f1_cut_line,
            "読み替えない": ("判定は D1(最も負の 3 分位)のまま行う。"
                             "走行の後に「負の群」へ読み替えない(A-6)。"),
        },
        "反復回数と種の実行時の突き合わせ(決定 4'''')": {
            "REPS": REPS, "凍結したリテラル": REPS_FROZEN_LITERAL,
            "SEED": SEED, "種の凍結したリテラル": SEED_FROZEN_LITERAL,
            "注": "引数では変えられず、実行時にも 2000 / 1 と突き合わせる"
                  "(モジュール属性の差し替えもここで止まる)。",
        },
        "MDE の単位の固定表(§10.1。決定 5'''')": _UNIT_TEMPLATES,
        "感度(観測のみ)": {
            nm: {"path": str(r.path),
                 "標本(MDE の p・s)": (str(sens_samples[nm].path)
                                       if nm in sens_samples else None),
                 "MDE 列": ("出す" if nm in sens_samples else "空"),
                 # **決定 3'''(5 回目の指摘 3)**: **在庫の話を書かない。**
                 # **前版は「対を成す標本の走行が在庫に無い」と機械が一律に書いていたが、
                 # この道具は在庫を 1 度も見ていない**(見ているのは引数だけ)。
                 "MDE 列が空の理由": (None if nm in sens_samples else
                                      "--sens に :SAMPLE_DIR を渡していない"
                                      "(在庫の有無はこの道具では見ていない)")}
            for nm, r in sens.items()
        },
        "標本(MDE の p・s)": {n: str(r.path) for n, r in samples.items()},
        "渡した標本ディレクトリの一覧": {
            "判定の走行": {n: str(r.path) for n, r in samples.items()},
            "感度の走行": {nm: str(r.path) for nm, r in sens_samples.items()},
            "注": "この一覧が、MDE の p・s の出所のすべてである(決定 3''')。"
                  "**在庫にどのディレクトリがあるかは、この道具では見ていない。**",
        },
        "対照(ii)の軸の作り方": {
            "own(対照行自身の値)": sorted(
                {g.name for g in groups if g.control_axis == AX_OWN}),
            "partner_sign(符号なしの大きさ × 相手の側の符号)": sorted(
                {g.name for g in groups if g.control_axis == AX_PARTNER_SIGN}),
            "inherit(相手の実群の群を受け継ぐ)": sorted(
                {g.name for g in groups if g.control_axis == AX_INHERIT}),
        },
        "対照(ii)の軸の作り方の固定(事前登録 §4)": AXIS_KIND_FIXED,
        "対照(ii)の軸の作り方の検査": (
            "走行ごとに測った結果を事前登録 §4 の固定と突き合わせ、"
            "食い違えば「[止め]」で終了コード 1(決定 3''。黙って合わせない)。"
            "本走行では全部一致した。"),
        "受け継いだ群": [
            {"群": g.name, "走行": g.run, "列": g.col,
             "n_control_matched": int(membership(runs[g.run], KIND_MAT, g).sum())}
            for g in groups if g.control_axis == AX_INHERIT
        ],
        "受け継いだ群の数": sum(1 for g in groups if g.control_axis == AX_INHERIT),
        "相手の符号を当てた群の数": sum(
            1 for g in groups if g.control_axis == AX_PARTNER_SIGN),
        "群ごと": [
            {"群": g.name, "走行": g.run, "軸": g.axis, "列": g.col,
             "分位": g.q, "side": g.side,
             "対照は1対1の束から受け継いだか": g.pair_inherit,
             "対照(ii)の軸の作り方": g.control_axis,
             "切り値": (list(g.cuts) if g.cuts else None),
             "n_liq": int(membership(runs[g.run], KIND_LIQ, g).sum()),
             "n_control_uniform": int(membership(runs[g.run], KIND_UNI, g).sum()),
             "n_control_matched": int(membership(runs[g.run], KIND_MAT, g).sum())}
            for g in groups
        ],
        "F1の読み": reading,
        "注記": [
            "対照 (i) の向きの要る量(*_reactdir)は §6.1 の重み付けを通した。"
            "SE の合成は独立を仮定しており、**SE を小さく見る向きの近似**である(§6.1 の 3)。",
            "合わせた対照の *_reactdir は 1 対 1 の相手の束の side の符号を当てた"
            "(§6.1 の 4。下向き = SELL 側では mfe と mae が入れ替わる)。",
            "対照 (ii) の軸の値の作り方は 3 通りで、走行ごとに数えて決めた"
            "(summary の「対照(ii)の軸の作り方」)。own = 対照行自身の値 /"
            " partner_sign = 対照行の符号なしの大きさに相手の側の符号を当てた対照自身の値 /"
            " inherit = 対照行に対応物が無いので 1 対 1 の相手の群を受け継いだ。"
            "一様対照は 1 対 1 の相手が無いので own 以外の群には入れていない"
            "(その群の 対照(i) と 差(i) は空になる)。",
            "相手が mixed 束の合わせた対照は全群から落とした"
            "(件数は summary の「相手がmixed束で落とした合わせた対照」)。"
            "実群の側が mixed を主表から外しているので、残すと 1 対 1 が崩れるためである。",
            "1 対 1 の対応は table.csv の matched_liq_id 列で取り、走行ごとにサニティ #14"
            "(相手が実在 / 同日 / bin_pct の差が ±5 以内 / 同じ相手を 2 つ以上の対照が"
            "指していない / 対照の件数 = 引けた相手の件数(mixed 相手を含めて))を通した"
            "(決定 12''。結果は走行ごとの「サニティ14の結果」)。",
            "判定に使う走行は gap 60 秒 × W 8h と gap 60 秒 × W 24h の 2 本で、"
            "W に依らない 12 群は gap60_w8 の走行からだけ 576 検定に入れた(§4 の内訳表)。"
            "同じ 12 群の W = 24h 側は観測のみの表に出してある(t と判定の列なし)。"
            "その 12 群の切り値は W = 24h の実群で切り直してある(決定 20')。",
            "感度の走行(--sens)は observation_only_<NAME>.csv に別の表として出した。"
            "`:SAMPLE_DIR` で対を成す標本を渡した感度は MDE の列を出し、渡していない感度は"
            "MDE の列が空である(決定 8''。どちらかは summary の「感度(観測のみ)」)。"
            "感度の行は判定にも F1 の読みにも 1 行も入れていない。"
            "感度は 4 本とも渡す(渡っていなければ表を 1 枚も書かずに終わる = 決定 2''''')。",
            "不在を断ずる語の走査は、表を 1 枚も書く前にメモリ上の行と文字列へ当てた"
            "(決定 11'')。書き出した後にもう一度走査している(二重の網)。",
            "「全体」群の 実群 の欄は差の入力として出しているだけで、"
            "その水準を根拠にした文はこの summary にも標準出力にも書いていない"
            "(事前登録 §3 の #1 = a「全体分布の水準を根拠にした主張は書かない」)。",
            "不在を断ずる語は 1 つも書かない。"
            "検出できなかったセルは「検出されず(MDE = X)」と書き、"
            "MDE が計算できなかったセルは「" + UNKNOWN_MDE + "」、"
            "t が計算できなかったセルは「" + UNKNOWN_T + "」(決定 1'')、"
            "対照の件数が 30 未満のセルは「" + UNKNOWN_N2 + "」(決定 20'')と書く。"
            "MDE との比較(≥ / <)は別の列に残してある。",
            "MDE は p・s を標本 6 日で固定し、n だけ走行後の群の件数から取った(§8.6)。"
            "群の切り方は判定区間の実群で決めた切り値を標本にも当てた(§4)。",
            "前進到達(fwd_node)はどちらの表にも入れていない(1 周目は測定不能。§4.3)。",
            "反復回数 2,000 と種 1 は定数で、引数では変えられず、"
            "実行時にも 2000 / 1 と突き合わせる(決定 1''' + 4'''')。"
            "開封の後に反復を引き直して読みを取り直す経路は無い(A-6)。",
            "「検出されず」に併記する MDE には単位を付けた(決定 5''''。"
            "到達率 = 割合 / bp 系 = bp / 秒 = 秒 / ΔOI = 枚。表は summary の"
            "「MDE の単位の固定表」)。",
            "観測のみの表(observation_only.csv と感度の表)の MDE の列見出しは"
            "「MDE(参考。族の α に入らない)」である(決定 7'''' + 6'''''。"
            "判定の表 judgment_576.csv / f1_12cells.csv の列見出しと同じ名前にしない。"
            "どちらの表の行も 576 にも α にも F1 の読みにも 1 行も入らないためである)。",
            "対照 (ii) の軸の作り方の検査(決定 3'')は標本の走行にも掛けた(決定 8'''')。",
            "F1 の 12 セルが揃わなければ表を 1 枚も書かずに終わる(決定 13'''')。",
            "サニティ #14 は標本の走行(--sample-w8 / --sample-w24 / --sens の :SAMPLE_DIR)にも"
            "掛けた(決定 2''')。標本の 1 対 1 が崩れると MDE の p・s の母集団が黙って変わるため。",
            "渡された走行が名前どおりのものかを summary.json の params で検査した(決定 12''')。"
            "食い違えば表を 1 枚も書かずに終わる。",
            "有限な複製の本数が 2,000 に満たないセルは一覧に出してある(決定 16''')。"
            "そのセルは 1.58% ではなく 1/√(2·n) で読み、結果の読みに本数と併記する(§10.3)。"
            "閾値は置いていない(A-12)。",
        ],
    }

    names = (["judgment_576.csv", "f1_12cells.csv", "observation_only.csv"]
             + [f"observation_only_{nm}.csv" for nm in sens_rows]
             + ["why_frame.csv", "f1_reading.txt", "summary.json"])

    # --- 決定 11'': 表を書く前に、メモリ上の行と文字列へ判定語を当てる -----------
    blobs: dict[str, object] = {
        "judgment_576.csv": judge_rows,
        "f1_12cells.csv": cells,
        "observation_only.csv": obs_rows,
        **{f"observation_only_{nm}.csv": rows_ for nm, rows_ in sens_rows.items()},
        "why_frame.csv": why_rows,
        "f1_reading.txt": f1_text,
        "summary.json": summary,
    }
    hits = scan_rows_forbidden(blobs)
    if hits:
        sys.stderr.write(
            "[止め] 出力に判定語が混ざっている(表を 1 枚も書かずに終わる): "
            + " / ".join(hits) + "\n")
        return 1

    # --- 表を書く前に関門をもう一度通す(閉じていれば 1 枚も書かない)-----------
    # **決定 11(8 回目の指摘 11)で、同じ関門を検査より前にも置いた**
    # (`stopped.txt` も書かせないため)。**ここは残す**: 検査から表を書くまでの間に
    # 台帳が閉じられた回も止めるためである(**2 回通す。外す旗は無い**)。
    pass_audit_gate(Path(a.root).resolve())

    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "judgment_576.csv", JUDGE_HEADER, judge_rows)
    write_csv(out / "f1_12cells.csv", JUDGE_HEADER, cells)
    write_csv(out / "observation_only.csv", OBS_HEADER, obs_rows)
    for nm, rows_ in sens_rows.items():
        write_csv(out / f"observation_only_{nm}.csv", SENS_HEADER, rows_)
    write_csv(out / "why_frame.csv", WHY_HEADER, why_rows)
    (out / "f1_reading.txt").write_text(f1_text, encoding="utf-8")
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 書き出した後の二重の網(整形で語が生まれていないか)。
    hits = scan_forbidden(out, names)
    if hits:
        sys.stderr.write("[止め] 出力に判定語が混ざっている: " + " / ".join(hits) + "\n")
        return 1
    write_md5(out, names)

    print(f"判定の表: {len(judge_rows)} 行 / 観測のみの表: {len(obs_rows)} 行 / 群 {len(groups)}")
    print(f"有限な複製の本数: 指定 {REPS} / "
          f"最小(検定したセルだけ) {summary['有限な複製の本数']['最小(検定したセルだけ)']} / "
          f"指定に満たないセル(検定したセルだけ) "
          f"{summary['有限な複製の本数']['指定した反復回数に満たないセルの数(検定したセルだけ)']}"
          f" / 群が空・n < 30 で検定していないセル {untested_cells}")
    for nm, rows_ in sens_rows.items():
        print(f"感度(観測のみ)の表 {nm}: {len(rows_)} 行")
    print(f"F1 の 12 セルの読み: {reading}")
    print(f"出力先: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
