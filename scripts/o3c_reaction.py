#!/usr/bin/env python3
"""O-3c 段 A「清算の後の値動きを測る」の観測表(2026-09-18)。

設計: `docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md`
(オーナー承認 L-197「**全てOKです。**」= 設計 §0.1 の枠組みが承認された)。

**観測表を作るだけである。判定(予測できる / 使える / 有効)は 1 つも書かない。
バーも置かない。** 判定の形は事前登録(`REACTION_PREREG_DRAFT_2026-09-18.md`)で扱う。

引き金と起点(設計 §2):
  引き金 = `build_cascades(gap_ms)` で束ねた清算の**終わり**(一意化 = 全列一致の重複を
           1 件にしたあと)。束ね方・一意化は `src/bot/research/liq_response.py` の
           関数を**そのまま**呼ぶ(定義を変えない)。
  起点   = `compute_reactions(anchor="after_shift")`。起点の点 = `at_or_after(end_ms)`、
           窓の終点 = `at_or_before(anchor_ts + h)`。

モード:
  --mode anchor   設計 §9 の手順 1(起点の妥当性)。非タイ行で
                  `bp_h(after_shift) − bp_h(before)` の分位を h ごとに出す。
                  `--granularity bar60`(既定)/ `trades`(約定そのまま)。
                  **標本 6 日の外を 1 日でも含む走行では、生の `bp_h` 列・`pred_under` ・
                  `resid` を 1 つも書かない**(差の分位だけ。2026-09-18 の監査の指摘 2)。
  --mode sample   設計 §9 の手順 2(標本 6 日)。§3 の観測量・§4 の軸の列・§5 の対照 2 本・
                  §6 の bitFlyer 1 分足の列を全部出す。
                  **`--days` で標本 6 日の外を開けるには `--approval L-NNN` が要る**
                  (2026-09-18 の監査の指摘 3)。
  --mode full     設計 §9 の手順 3。**判定区間 = 標本 6 日と、12 日走行で開いた 10 日を
                  除いた 456 日**(`judgment_days`。2026-09-18 の監査の指摘 4 と
                  指摘 2・14 / 返答 060 の #1)。
                  **開封前の関門 10 個を全部通したときだけ走る**(prereg 監査(7 回目)の
                  指摘 1・18・20、8 回目の指摘 1・2・6、9 回目の指摘 3・15・20。
                  `check_approval` の注):
                  (a) `--approval` が事前登録 §14.4 の欄「応答の L 番号」と一致 /
                  (b) その番号が L-199 より後 /
                  (c) `docs/OWNER_LOG.md` に行頭 `| L-NNN |` の行が実在 /
                  (c′) **(c) の続き**: **その L 行に「カ」「キ」「ク」の 3 文字が
                      すべて含まれる**(**答えが要る 3 件に答えが無い行は通さない**
                      = 10 回目の指摘 13。**射程: 文字が含まれることしか見ない**)/
                  (d) `--out-dir` が §14.1・§14.2 の 6 つのどれか /
                  (e) `--out-dir` がまだ存在しない(再走行・上書きを止める)/
                  (f) `--days` が渡っていない(日は `judgment_days` に固定。8 回目の指摘 6)/
                  (g) `--out-dir` が `OPENED.txt` にまだ載っていない
                      (**出力先を消してからの再走行**を止める。8 回目の指摘 2。
                      **走行が途中で落ちた回 = `done` の行が無い回も止まる** = 9 回目の指摘 1)/
                  (i) **凍結した道具の 2 ファイルに未コミットの変更が無い**
                      (`git diff --quiet HEAD -- scripts/o3c_reaction.py
                      scripts/o3c_reaction_judge.py` が 0。
                      **開封はコミット済みの道具からだけ** = 9 回目の指摘 3・15。
                      **10 回目の指摘 1・2・3 で「作業ツリー全体が clean」から
                      道具の 2 ファイルだけに狭めた** = リードの決定 1・2・3。
                      **出力先・台帳・TRACE・事前登録の書き込みで作業ツリーは必ず汚れるので、
                      「全体が clean」は 1 本目から成立しない**(設計上の帰結。6 本を走らせて確かめたわけではない)/
                  (j) **`--data-root` が既定のまま**(在庫を差し替えると (h) が
                      空回りする = 9 回目の指摘 20)。
                  1 つでも欠ければ終了コード非 0 で即座に止まる。
                  **判定区間の日は、この `--mode full` 以外では 1 日も開けない**
                  ((h)。`--mode sample --days` と `--mode anchor` は、日集合が判定区間の日を
                  1 日でも含めば `--approval` があっても止まる = 8 回目の指摘 1)。

**符号の約束(設計 §3 の 2 つの文が食い違っていたので、ここで分けた。報告の §0.1 に
(該当語なし)の行として出す)**:
  * 距離の列 `*_liqdir` は `scripts/o3c_oi_distance.py` の `LIQ_SIGN`(SELL = +1 / BUY = −1)を
    **そのまま**使う。1 つも変えていない(用語・記号の意味を変えて使い回さない)。
  * 値動き・到達・最大順行/逆行の列 `*_reactdir` は設計 §3 の操作的な文
    「**SELL 清算 = ロングの強制決済 → 下向きが正、BUY 清算 → 上向きが正**」
    「**正 = 継続、負 = 反転**」に従う = `REACT_SIGN`(SELL = −1 / BUY = +1)。
    これは `LIQ_SIGN` の符号違いである。**別の列名にして混ぜない。**
  * 対照行(side が無い)は `REACT_SIGN` を +1 として生の値を入れ、絶対値の列を併記する。

使い方:
  python3 scripts/o3c_reaction.py --mode anchor --out-dir backtest_data/o3c_reaction_20260918_anchor
  python3 scripts/o3c_reaction.py --mode sample --gap-sec 60 --window-hours 8 \
      --mmr 0.004 --out-dir backtest_data/o3c_reaction_20260918_sample/gap60_w8
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import random
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import o3c_oi_distance as oid  # noqa: E402
import o3c_price_level_table as base  # noqa: E402
import o3c_rows4 as rows4  # noqa: E402  (タイの分類 `classify` を同じ定義で使う)

from bot.research.liq_response import (  # noqa: E402
    Cascade,
    PriceSeries,
    build_cascades,
    compute_reactions,
    load_binance_cm_liquidations_with_dedup_stats,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXCHANGE = "binance_cm"

# 設計 §3。1 分は bitFlyer 1 分足と揃う最小(設計 §3 の委任先の判断)。
HORIZONS_MIN: tuple[int, ...] = (1, 5, 15, 30, 60, 240)
BAR_MS = 60_000                 # 粒度。設計 §2.2 の「60 秒バー」
STALENESS_MS = 300_000          # `compute_reactions` の既定
BUCKET_MS = oid.BUCKET_MS       # metrics の粒度(5 分)

DEFAULT_GAP_SEC = 60
GAP_SEC_CHOICES = (30, 60, 180)

# 設計 §9 の手順 2。FULL / EXT と同じ 6 日。
SAMPLE_DAYS = (
    "2023-06-25",
    "2023-06-26",
    "2024-02-19",
    "2024-02-20",
    "2024-10-13",
    "2024-10-14",
)

# 2026-09-18 の 12 日走行(`--mode sample --days 2024-02-15,...,2024-02-26`)で
# **判定区間の日を開けてしまった 10 日**。標本 6 日(2024-02-19/20)はここに入れない。
#
# 出所:
#   * `backtest_data/o3c_reaction_20260918_scale12_judgmentdays/README.txt`
#     (走行の出力を封じたディレクトリ。`table.csv` に §3 の観測量 — 価格変化・到達・
#      最大順行/逆行・ΔOI — が**全列**入っている)
#   * 2026-09-18 の `owner-auditor` 24 件の指摘 2(生の主観測量を判定区間の日で出した)と
#     指摘 14(12 日走行の出力先が成果物一覧にも MD5SUMS にも無い)
#   * 返答 060 の #1(「判定区間の日を含む走行 2 本の扱い」。オーナーの答え待ち)
#
# 理由: この 10 日は §3 の観測量が全列そろって出ており、**探索段と同じだけ開いている。**
# 案 a(全体分布は既知として扱う)でも案 b(手順 1 をやり直す)でも、この 10 日を
# 判定区間に残す形は無い = **a・b に共通**なので、答えを待たずに判定区間から外す。
SCALE12_JUDGMENT_DAYS_OPENED = (
    "2024-02-15",
    "2024-02-16",
    "2024-02-17",
    "2024-02-18",
    "2024-02-21",
    "2024-02-22",
    "2024-02-23",
    "2024-02-24",
    "2024-02-25",
    "2024-02-26",
)

# 値動きの符号(設計 §3 の操作的な文)。`oid.LIQ_SIGN` とは符号が逆で、別の列名に置く。
REACT_SIGN = {"SELL": -1.0, "BUY": 1.0}
# `load_binance_cm_liquidations` の side("long" = SELL 清算)から元の列へ戻す。
SIDE_OF_DIRECTION = {"long": "SELL", "short": "BUY"}

KIND_LIQ = "liq"
KIND_UNIFORM = "control_uniform"
KIND_MATCHED = "control_matched"

# 対照 (ii) のマッチング(設計 §5)。
MATCH_TOL_PCT = 5.0
MATCH_GRID_MS = 60_000
CONTROL_GAP_MS = base.CONTROL_GAP_MS  # ±5 分(既存と同じ)

# bitFlyer 1 分足(設計 §6)。
BITFLYER_DIR = (
    REPO_ROOT / "backtest_data" / "bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
)
XCORR_HALF_MIN = 10        # 設計 §6「起点の前後 ±10 分」
XCORR_MIN_PAIRS = 5        # 相関を出すのに要る最小の組数(設計に無い。委任先が置いた)
UTC_CHECK_MAX_LAG_MIN = 600  # 設計 §6 の 1(9 時間ずれていれば ±540 分側に出る)
UTC_CHECK_TOP_N = 100

OWNER_LOG = REPO_ROOT / "docs" / "OWNER_LOG.md"
APPROVAL_RE = re.compile(r"^L-\d{3,}$")

# --------------------------------------------------------------------------
# 開封前の関門(prereg 監査(7 回目)の指摘 1・18・20。リードの決定 1・18・20)
# --------------------------------------------------------------------------
# **前版の `--mode full` の関門は「`docs/OWNER_LOG.md` に行頭 `| L-NNN |` の行が実在するか」
# しか見ていなかった**(7 回目の監査の実測)。**読みの側は `params.approval` を事前登録
# §14.4 の欄と突き合わせるが、それは 6 本を走らせた後の段である。**
# **間違った(あるいは古い)L 番号のまま 456 日を 6 回開け終わるまで、何も止まらなかった。**
# **開封の前に、(a)〜(j) の 10 個を全部通したときだけ走る**
# (**(c) は 10 回目の指摘 13 で 2 段になった: 行が実在する かつ その行に カ・キ・ク がある**)
# (事前登録 §3.1・§14.1・§14.4・§14.6):
#   (a) 事前登録 §14.4 の欄「応答の L 番号」が埋まっていて、`--approval` と一致する
#   (b) その番号が L-199 より大きい(L-199 は「1 = a、9 = a」への応答であって、
#       報告 062 への応答ではない)
#   (c) `docs/OWNER_LOG.md` に行頭 `| L-NNN |` の行が実在する(従来どおり)
#   (c′) **(c) の続き**。その L 行に「カ」「キ」「ク」の 3 文字がすべて含まれる
#       (10 回目の指摘 13。リードの決定 13。**射程: 文字が含まれることしか見ない**)
#       **関門の数は (a)〜(j) の 10 個のままである**((c′) は (c) の 2 段目)
#   (d) `--out-dir` が §14.1・§14.2 の 6 つのパスのどれかである
#   (e) `--out-dir` が**まだ存在しない**(再走行・上書きを機械で止める
#       = 「一度だけ開ける」の機械。**開けられる回数の上限は 6 本で、それ以上は
#       この機械を変えないと走らない**)
#   (f) `--days` が渡っていない(日は `judgment_days` の 456 日に固定。8 回目の指摘 6)
#   (g) `--out-dir` が台帳 `OPENED.txt` にまだ載っていない(8 回目の指摘 2)
#   (h) **`--mode full` 以外の経路**が判定区間の日を 1 日も含まない(8 回目の指摘 1)
#   (i) 凍結した道具の 2 ファイルに未コミットの変更が無い
#       (9 回目の指摘 3・15 / 10 回目の指摘 1・2・3。リードの決定 1・2・3)
#   (j) `--data-root` が既定のまま(9 回目の指摘 20。リードの決定 20)
PREREG = (
    REPO_ROOT / "docs" / "PHASE2" / "O3C" / "PRICE_LEVEL"
    / "REACTION_PREREG_2026-09-18.md"
)
# 欄の形は **応答の L 番号**: **L-NNN**(埋まっていなければ **(まだ無い…)**)。
# **行の形ごと固定する**(本文の他の場所にある「応答の L 番号」という語を拾わないため)。
# 読みのスクリプト `scripts/o3c_reaction_judge.py` と同じ正規表現である(同じ欄を読む)。
APPROVAL_FIELD_RE = re.compile(
    r"^[ \t>]*\*\*応答の L 番号\*\*\s*[:：]\s*\*\*(.+?)\*\*\s*$", re.MULTILINE
)
APPROVAL_VALUE_RE = re.compile(r"^L-(\d+)$")
# **L-199 より大きくなければ止める**(指摘 18。リードの決定 1 の (b))。
APPROVAL_MIN_L = 199
# **`--mode full` で書いてよい出力先(事前登録 §14.1 の 2 本 + §14.2 の感度 4 本)。**
FULL_OUT_DIRS_REL = (
    "backtest_data/o3c_reaction_20260918_full/gap60_w8",
    "backtest_data/o3c_reaction_20260918_full/gap60_w24",
    "backtest_data/o3c_reaction_20260918_full/gap30_w8",
    "backtest_data/o3c_reaction_20260918_full/gap180_w8",
    "backtest_data/o3c_reaction_20260918_full/gap30_w24",
    "backtest_data/o3c_reaction_20260918_full/gap180_w24",
)
FULL_OUT_DIRS = tuple(REPO_ROOT / p for p in FULL_OUT_DIRS_REL)

# **開けた出力先の台帳(prereg 監査(8 回目)の指摘 2。リードの決定 2)。**
# **(e)「出力先が既に在れば止める」だけでは、出力先を消してから走らせ直せば止まらない。**
# **`--mode full` が走るたびにここへ「出力先・UTC 時刻・approval」を 1 行追記し、
# 既に載っている出力先は (g) で止める(出力先が在るかどうかに関わらず)。**
# **この台帳は git で追跡される**(`backtest_data/` の下だが、`.gitignore` の除外は
# `binance_*` の大容量ディレクトリだけで、この道は 1 つも掛かっていない = 実測)。
# **残る穴は §3.1 に書いた**: 台帳そのものを消す / この機械を書き換える。
# **どちらも差分に残る。**
FULL_OUT_ROOT = REPO_ROOT / "backtest_data" / "o3c_reaction_20260918_full"
FULL_OPENED_LEDGER = FULL_OUT_ROOT / "OPENED.txt"
# **凍結した道具の 2 ファイル(prereg 監査(10 回目)の指摘 1・2・3。リードの決定 1・2・3)**。
# **版の担保はこの 2 ファイルだけに掛ける。**作業ツリー全体は、出力先・台帳・TRACE・
# 事前登録の欄の書き込みで必ず汚れるので、担保の単位に使えない(指摘 1・2 の実測)。
TOOL_FILES_REL = ("scripts/o3c_reaction.py", "scripts/o3c_reaction_judge.py")

# **決定 13(10 回目の指摘 13)**: 承認の L 行に、答えが要る 3 件の名前が
# **3 文字とも含まれていなければ通さない。**
# **射程: 文字が含まれることしか見ない**(答えの中身は読まない)。
APPROVAL_LINE_REQUIRED = ("カ", "キ", "ク")

OPENED_HEADER = (
    "# `--mode full` が判定区間 456 日を開けた出力先の台帳"
    "(事前登録 §3.1。prereg 監査(8 回目)の指摘 2)。\n"
    "# 1 行 = <出力先の絶対パス>\\t<UTC 時刻>\\t<--approval の L 番号>"
    "\\t<started|done>。\n"
    "# `started` = 関門を通って開けた(出力を書く前)。`done` = 走行が最後まで終わった。\n"
    "# **走行が途中で落ちれば `done` の行は出ない。**その出力先は `started` のまま残り、\n"
    "# 再走行は出力先の有無に関わらず関門 (g) で止まる"
    "(prereg 監査(9 回目)の指摘 1。リードの決定 1)。\n"
)
# **`\t<status>` は後から足した列なので、省略されていても読めるようにする**
# (古い 3 列の行は `status` が None になる)。
OPENED_LINE_RE = re.compile(
    r"^(?P<out>[^\t]+)\t(?P<utc>[^\t]+)\t(?P<approval>[^\t]+)(?:\t(?P<status>.+))?$"
)
OPENED_STARTED = "started"
OPENED_DONE = "done"


def opened_out_dirs(ledger: Path = FULL_OPENED_LEDGER) -> set[str]:
    """台帳に載っている出力先(解決済みの絶対パスの文字列)の集合。

    **`started` / `done` を区別しない。**落ちた回(`started` だけの行)も
    「開けた」として (g) が止める(prereg 監査(9 回目)の指摘 1。リードの決定 1)。
    """
    if not ledger.exists():
        return set()
    out: set[str] = set()
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = OPENED_LINE_RE.match(s)
        if m:
            out.add(str(Path(m.group("out")).resolve()))
    return out


def opened_status(ledger: Path = FULL_OPENED_LEDGER) -> dict[str, set[str]]:
    """出力先ごとに台帳に載っている状態(`started` / `done`)の集合。

    **`done` が無い出力先 = 走行が最後まで終わっていない**(途中で落ちた回)。
    **それでも再走行は (g) で止まる**(リードの決定 1)。
    """
    if not ledger.exists():
        return {}
    out: dict[str, set[str]] = {}
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = OPENED_LINE_RE.match(s)
        if m:
            key = str(Path(m.group("out")).resolve())
            out.setdefault(key, set()).add(m.group("status") or "(状態なし)")
    return out


def record_opened(
    out_dir: Path,
    approval: str | None,
    ledger: Path = FULL_OPENED_LEDGER,
    status: str = OPENED_STARTED,
) -> Path:
    """`--mode full` が走るたびに台帳へ 1 行追記する(関門を通った直後に呼ぶ)。

    **出力を書く前に `started` を追記する。**走行が途中で落ちても「開けた」ことは残る
    (= 落ちた回を消してやり直す経路も (g) で止まる)。
    **最後まで終わった回だけ `record_done` が `done` の行を足す。**
    """
    ledger.parent.mkdir(parents=True, exist_ok=True)
    if not ledger.exists():
        ledger.write_text(OPENED_HEADER, encoding="utf-8")
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(
            f"{Path(out_dir).resolve()}\t{stamp}\t{approval or '(なし)'}\t{status}\n"
        )
    return ledger


def record_done(
    out_dir: Path, approval: str | None, ledger: Path = FULL_OPENED_LEDGER
) -> Path:
    """走行が最後まで終わった回に `done` の行を足す(prereg 監査(9 回目)の指摘 1)。

    **`done` が無い出力先は「途中で落ちた回」である。**
    **それでも再走行は (g) で止まる**(台帳は `started` を見るため)。
    """
    return record_opened(out_dir, approval, ledger, status=OPENED_DONE)


def tool_commit(repo: Path = REPO_ROOT) -> str:
    """**凍結した道具の 2 ファイルに最後に触れたコミット**。取れなければ「不明」。

    `git log -1 --format=%H -- scripts/o3c_reaction.py scripts/o3c_reaction_judge.py`。

    **prereg 監査(10 回目)の指摘 3。リードの決定 3**:
    **前版は `git rev-parse HEAD` だった。**`HEAD` は事前登録の欄を書き足して
    コミットするたびに動くので、**「欄に書ける値(直前のコミット)と、そのとき成立する HEAD」が
    定義上一致しなかった**(指摘 3)。**本版は「この 2 ファイルに最後に触れたコミット」なので、
    事前登録の欄を書き足しても値が変わらない。**

    **走行の出力にこの道具の版を残し、読みの側が突き合わせるためだけの関数である。**
    **判定にも計算にも 1 つも使わない。**
    """
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%H", "--", *TOOL_FILES_REL],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "不明"
    got = (r.stdout or "").strip()
    if r.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", got):
        return "不明"
    return got


def tool_dirty(repo: Path = REPO_ROOT) -> tuple[bool, int]:
    """**凍結した道具の 2 ファイルに未コミットの変更があるか。**

    `git diff --quiet HEAD -- scripts/o3c_reaction.py scripts/o3c_reaction_judge.py` の
    **終了コードが 0 でなければ「汚れている」**。返り値 `(汚れているか, 終了コード)`。
    **git が呼べない場合は「汚れている」側に倒す**(終了コード −1)。

    **prereg 監査(10 回目)の指摘 1・2。リードの決定 1・2**:
    **前版は `git status --porcelain` で作業ツリー全体を見ていた。**
    **出力先 `backtest_data/o3c_reaction_20260918_full/`・台帳 `OPENED.txt`・
    `docs/AUDITOR/TRACE/*.json`・事前登録の欄の書き込みで作業ツリーは必ず汚れるので、
    「全体が clean」は 1 本目が走った瞬間に成立しなくなり、2 本目は (i) で止まる**
    (**設計上の帰結。6 本を走らせて確かめたわけではない**)
    (指摘 1・2 の実測)。**版の担保を「道具のファイル」に限る。**
    """
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--", *TOOL_FILES_REL],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return True, -1
    return (r.returncode != 0), int(r.returncode)


def _dirty_block(repo: Path = REPO_ROOT) -> dict:
    """`summary.json` に書く道具の汚れの記録(決定 1・2・3)。

    **走行の後からは作り直せないので、走った回ごとに残す。**
    **`状態` の語は前版と同じ `clean` / `dirty` である**(読みの側の鍵を変えない)。
    """
    dirty, rc = tool_dirty(repo)
    return {"状態": "dirty" if dirty else "clean",
            "汚れているか": dirty,
            "見た範囲": list(TOOL_FILES_REL),
            "git diff --quiet HEAD の終了コード": rc}


def tool_version_block(repo: Path = REPO_ROOT) -> dict:
    """**出力を書く前に 1 回測る**(リードの決定 3「**`tool_dirty` の判定は出力を書く前に行う**」)。

    返り値は `summary.json` に入れる 2 鍵 `{"tool_commit": …, "tool_dirty": …}`。
    **前版は `df.to_csv()` の後で測っていたので、出力を書いたこと自体が
    「汚れている」の材料になりえた**(10 回目の指摘 1)。
    """
    return {"tool_commit": tool_commit(repo), "tool_dirty": _dirty_block(repo)}


def read_approval_from_prereg(prereg: Path = PREREG) -> tuple[str | None, str]:
    """事前登録 §14.4 の欄「応答の L 番号」を読む。返り値 `(L 番号, 説明)`。

    **欄が「(まだ無い)」なら `None`** を返し、呼び出し側が「[止め]」にする。
    **迂回する旗は作っていない**(`--approval` を渡しても、この欄と一致しなければ止まる)。
    """
    if not prereg.exists():
        return None, f"事前登録が読めない({prereg})"
    text = prereg.read_text(encoding="utf-8", errors="replace")
    fields = [m.strip() for m in APPROVAL_FIELD_RE.findall(text)]
    if not fields:
        return None, f"事前登録に「応答の L 番号」の欄が 1 つも無い({prereg})"
    if len(set(fields)) > 1:
        return None, (
            "事前登録の「応答の L 番号」の欄が "
            f"{len(set(fields))} 通りある: {sorted(set(fields))}"
        )
    value = fields[0]
    if not APPROVAL_VALUE_RE.match(value):
        return None, (
            "事前登録 §14.4 の「応答の L 番号」の欄が埋まっていない"
            f"(欄の値: {value!r})"
        )
    return value, f"事前登録 §14.4 の「応答の L 番号」の欄({prereg})"


# --------------------------------------------------------------------------
# 承認の関門(設計 §9 の手順 2 -> 3 の機械)
# --------------------------------------------------------------------------


def approval_line_text(approval: str, owner_log: Path = OWNER_LOG) -> str | None:
    """`docs/OWNER_LOG.md` の行頭 `| L-NNN |` の**行全体**を返す(無ければ None)。

    **決定 13(10 回目の指摘 13)**: (c′) が行の中身を見るために足した。
    **最初に一致した 1 行だけを返す。**
    """
    if not APPROVAL_RE.match(approval or ""):
        return None
    if not owner_log.exists():
        return None
    pat = re.compile(r"^\|\s*" + re.escape(approval) + r"\s*\|")
    with owner_log.open(encoding="utf-8") as fh:
        for line in fh:
            if pat.match(line):
                return line.rstrip("\n")
    return None


def approval_line_exists(approval: str, owner_log: Path = OWNER_LOG) -> bool:
    """`docs/OWNER_LOG.md` に行頭 `| L-NNN |` の行が実在するか。

    実在しない / ファイルが無い / 形が `L-NNN` でない、のどれでも False。
    """
    return approval_line_text(approval, owner_log) is not None


def approval_line_missing_names(
    line: str, required: tuple[str, ...] = APPROVAL_LINE_REQUIRED
) -> list[str]:
    """**決定 13(10 回目の指摘 13)**: 承認の L 行に無い名前を返す(空なら (c′) を通る)。

    **射程(隠さずに書く)**: **文字が含まれることしか見ない。**
    「カ」「キ」「ク」が別の意味で書かれていても通るし、
    **その 3 件に実際に答えているかは読んでいない。**
    """
    return [ch for ch in required if ch not in (line or "")]


def judgment_day_set(data_root: Path | None = None) -> frozenset[str]:
    """判定区間の日の集合 = 在庫の全日 − 標本 6 日 − 12 日走行の 10 日。

    **prereg 監査(8 回目)の指摘 1。リードの決定 1**:
    **判定区間の日は 6 本の `--mode full` 以外では開けない。**その判定に使う集合である。
    `judgment_days()` と同じ定義を集合で返すだけで、**新しい定義を作っていない。**

    **射程**: 集合は**在庫(`--data-root`)から作る。**在庫が読めない / 空なら空集合になり、
    この関門は何も止めない(**そのときは走らせても読む日が 1 日も無い**)。
    """
    root = Path(data_root) if data_root is not None else base.DEFAULT_DATA_ROOT
    try:
        days = all_days(root)
    except OSError:
        return frozenset()
    opened = set(SAMPLE_DAYS) | set(SCALE12_JUDGMENT_DAYS_OPENED)
    return frozenset(d for d in days if d not in opened)


def check_approval(
    mode: str,
    approval: str | None,
    owner_log: Path = OWNER_LOG,
    days: list[str] | None = None,
    out_dir: Path | None = None,
    prereg: Path = PREREG,
    allowed_out_dirs: tuple[Path, ...] = FULL_OUT_DIRS,
    data_root: Path | None = None,
    days_given: bool = False,
    ledger: Path = FULL_OPENED_LEDGER,
    tool_state: bool | None = None,
    default_data_root: Path | None = None,
) -> None:
    """判定区間の日を開ける経路に、承認行の実在を要求する。無ければ SystemExit。

    2026-09-18 の監査(指摘 3)への対応。前版は `mode != "full"` で即 return していたので、
    `--mode sample --days <判定区間の日>` が無審査で通っていた(実際に 2024-02-15〜26 の
    12 日が走った)。**関門は「モード」ではなく「どの日を開けるか」に掛ける。**

    - `--mode sample` は既定の標本 6 日(`SAMPLE_DAYS`)だけ無審査で走る。
      それ以外の日を 1 日でも含むなら `--approval L-NNN` が要る。
    - `--mode full` は **(a)〜(j) の 10 個**((c) は (c′) を含む 2 段である)を全部通したときだけ走る
      (prereg 監査(7 回目)の指摘 1・18・20、8 回目の指摘 1・2・6、
      9 回目の指摘 3・15・20。上の定数の注)。
    - `--mode anchor` は**出力の側**も絞る
      (標本 6 日以外を含む走行では生の `bp_h` 列を書かない = `emit_raw_bp`)。

    **prereg 監査(8 回目)の指摘 1。リードの決定 1**:
    **判定区間の日は 6 本の `--mode full` 以外では開けない。**
    `--mode sample --days` と `--mode anchor`(`--days` を持つ・持たないに関わらず
    全日を読む)について、**日集合が判定区間の日(`judgment_day_set`)を 1 日でも含めば
    「[止め]」**(**`--approval` があっても通さない**)。
    **前版は、この 2 経路が (c)「台帳に行頭 `| L-NNN |` がある」だけで通り、
    出力先の制限も回数の上限も掛からなかった**(8 回目の指摘 1。
    **§14.4.1 の埋め込みで実際に 456 日が 2 回開いたのがこの経路である**)。

    **prereg 監査(9 回目)の指摘 3・15 / 10 回目の指摘 1・2・3。リードの決定 1・2・3**:
    **(i)** `--mode full` は**凍結した道具の 2 ファイル(`TOOL_FILES_REL`)に
    未コミットの変更があれば「[止め]」**である(**開封はコミット済みの道具からだけ**)。
    `git diff --quiet HEAD -- <2 ファイル>` の結果は `summary.json` にも記録する。
    **前版は `git status --porcelain`(作業ツリー全体)を見ていたので、
    出力先・台帳・TRACE・事前登録の書き込みで必ず汚れ、2 本目から通らなかった**
    (10 回目の指摘 1・2 の実測)。

    **prereg 監査(10 回目)の指摘 13。リードの決定 13**:
    **(c′)** = **(c) の 2 段目**。承認の L 行に「カ」「キ」「ク」の 3 文字が
    すべて含まれていなければ「[止め]」。**射程: 文字が含まれることしか見ない。**
    **関門の数は (a)〜(j) の 10 個のままである。**

    **prereg 監査(9 回目)の指摘 20。リードの決定 20**:
    **(j)** `--mode full` は **`--data-root` の変更を受け付けない**(既定以外なら「[止め]」)。
    **(h) の集合は `--data-root` の在庫から作る**ので、在庫を差し替えると (h) だけが
    効かなくなる、という非対称があった(指摘 20)。**full の側でその差し替えを止める。**

    **`prereg` / `allowed_out_dirs` / `data_root` / `ledger` / `tool_state` /
    `default_data_root` は試験のためだけの既定引数である。CLI の旗にはしていない**
    (`main()` は `data_root` と `days_given` だけを渡し、
    `prereg` / `allowed_out_dirs` / `ledger` / `tool_state` / `default_data_root` は
    渡さない = 迂回できない)。
    """
    if mode != "full":
        # --- 決定 1: 判定区間の日は `--mode full` 以外では 1 日も開けない --------
        if mode == "anchor" and days is None:
            # `--mode anchor` は `--days` が無ければ在庫の全日を読む(`run_anchor`)。
            eff = sorted(judgment_day_set(data_root))
        else:
            eff = sorted(set(days or []) & judgment_day_set(data_root))
        if eff:
            raise SystemExit(
                f"[止め] --mode {mode} では判定区間の日を開けない"
                f"(判定区間の日が {len(eff)} 日含まれている: "
                f"{', '.join(eff[:5])}{' …' if len(eff) > 5 else ''})。\n"
                "       判定区間は事前登録 §14.1・§14.2 の 6 本の --mode full だけで開ける"
                "(prereg 監査(8 回目)の指摘 1。--approval があっても通さない)"
            )
    if mode == "sample":
        extra = sorted(set(days or []) - set(SAMPLE_DAYS))
        if not extra:
            return
        if not approval:
            raise SystemExit(
                "[止め] --mode sample で標本 6 日の外の日を開けるには --approval L-NNN が要る"
                f"(標本外: {', '.join(extra[:5])}{' …' if len(extra) > 5 else ''})"
            )
        if not approval_line_exists(approval, owner_log):
            raise SystemExit(
                f"[止め] {owner_log} に行頭 `| {approval} |` の行が無い。"
                "標本 6 日の外は走らせない(設計 §9 の機械)"
            )
        return
    if mode != "full":
        return
    # (f) `--mode full` は `--days` を受け付けない(日は `judgment_days` に固定)。
    #     **prereg 監査(8 回目)の指摘 6。リードの決定 6。**
    #     **前版の `main()` は `if a.days:` を先に見ていたので、`--mode full --days <任意>` が
    #     (a)〜(e) を全部通り、6 つの出力先の 1 つを 456 日以外の日で消費できた。**
    if days_given:
        raise SystemExit(
            "[止め] --mode full に --days は渡せない。"
            "判定区間の日は judgment_days(456 日)に固定である"
            "(prereg 監査(8 回目)の指摘 6)"
        )
    if not approval:
        raise SystemExit(
            "[止め] --mode full には --approval L-NNN が要る"
            "(設計 §9: 標本 6 日の表をオーナーに見せた回の記録の番号)"
        )
    # (a) 事前登録 §14.4 の欄と一致するか(欄が空なら止める)。
    field, note = read_approval_from_prereg(prereg)
    if field is None:
        raise SystemExit(
            "[止め] 事前登録 §14.4 の「応答の L 番号」が読めないので、判定区間を開けない。\n"
            f"       {note}\n"
            "       オーナーの応答(L 番号)を §14.4 の欄に書き写してから走らせる。"
        )
    if approval != field:
        raise SystemExit(
            f"[止め] --approval {approval} が事前登録 §14.4 の欄({field})と違う。"
            "判定区間を開けない(prereg 監査(7 回目)の指摘 1)"
        )
    # (b) L-199 より大きいか(L-199 は「1 = a、9 = a」への応答で、報告 062 への応答ではない)。
    m = APPROVAL_VALUE_RE.match(approval)
    if not m or int(m.group(1)) <= APPROVAL_MIN_L:
        raise SystemExit(
            f"[止め] --approval {approval} は L-{APPROVAL_MIN_L} より後の番号でない。"
            f"L-{APPROVAL_MIN_L} は「1 = a、9 = a」への応答であって、"
            "報告 062 への応答ではない(prereg 監査(7 回目)の指摘 18)"
        )
    # (c) 承認の行が `docs/OWNER_LOG.md` に実在するか(従来どおり)。
    line = approval_line_text(approval, owner_log)
    if line is None:
        raise SystemExit(
            f"[止め] {owner_log} に行頭 `| {approval} |` の行が無い。全件は走らせない"
            "(設計 §9 の機械)"
        )
    # (c′) その行に「カ」「キ」「ク」の 3 文字がすべて含まれるか。
    #      **prereg 監査(10 回目)の指摘 13。リードの決定 13。**
    #      **前版は (a)〜(c) が「L 番号が欄と一致し、L-199 より後で、行が実在する」だけを見たので、
    #      答えが要る 3 件(カ・キ・ク)に答えが無い別件の L 行を欄に書き写しても通った。**
    missing = approval_line_missing_names(line)
    if missing:
        raise SystemExit(
            f"[止め] {owner_log} の `| {approval} |` の行に "
            f"{' / '.join(missing)} が無い。\n"
            "       §14.4 の「答えが要る 3 件」(カ = 判定の分岐 / キ = F1 の整合・反証 /"
            " ク = 対照 (ii) の群の分け方)に答えが無い行では判定区間を開けない"
            "(prereg 監査(10 回目)の指摘 13)。\n"
            "       射程: この関門は 3 文字が含まれることしか見ない"
            "(答えの中身は読んでいない)"
        )
    # (d) 出力先が事前登録 §14.1・§14.2 の 6 つのどれかか。
    if out_dir is None:
        raise SystemExit(
            "[止め] --mode full の関門に --out-dir が渡っていない"
            "(事前登録 §14.1・§14.2 の 6 つのどれかでなければ走らせない)"
        )
    target = Path(out_dir).resolve()
    allowed = [Path(p).resolve() for p in allowed_out_dirs]
    if target not in allowed:
        raise SystemExit(
            f"[止め] --out-dir {out_dir} は事前登録 §14.1・§14.2 の 6 つに無い。\n"
            "       開けてよい出力先: " + " / ".join(FULL_OUT_DIRS_REL)
        )
    # (e) 出力先が既に在るなら止める(再走行・上書きを機械で止める)。
    if target.exists():
        raise SystemExit(
            f"[止め] --out-dir {out_dir} は既に存在する。"
            "判定区間は一度だけ開ける(事前登録 §3.1。上書き・再走行はここで止まる)"
        )
    # (g) 出力先が既に台帳 `OPENED.txt` に載っているなら止める。
    #     **prereg 監査(8 回目)の指摘 2。リードの決定 2。**
    #     **(e) は「出力先が在るとき」しか止めないので、消してから走らせ直せば通った。**
    #     **台帳は出力先の有無を見ない。**
    if str(target) in opened_out_dirs(ledger):
        raise SystemExit(
            f"[止め] --out-dir {out_dir} は既に {ledger} に載っている"
            "(この出力先で判定区間を一度開けている)。\n"
            "       出力先を消してからの再走行もここで止まる"
            "(事前登録 §3.1。prereg 監査(8 回目)の指摘 2)。\n"
            "       走行が途中で落ちた回(`done` の行が無い回)も同じく止まる"
            "(prereg 監査(9 回目)の指摘 1)"
        )
    # (i) 凍結した道具の 2 ファイルに未コミットの変更が無いか。
    #     **prereg 監査(9 回目)の指摘 3・15 / 10 回目の指摘 1・2・3。リードの決定 1・2・3。**
    #     **前版は作業ツリー全体を見ていたので、1 本目が出力先と台帳を書いた瞬間に
    #     作業ツリーが汚れ、2 本目がここで止まった**(10 回目の指摘 1 の実測)。
    #     **本版は `git diff --quiet HEAD -- <道具 2 ファイル>` だけを見る。**
    dirty, rc = (bool(tool_state), -1) if tool_state is not None else tool_dirty()
    if dirty:
        raise SystemExit(
            "[止め] 凍結した道具のファイルに未コミットの変更がある"
            f"(git diff --quiet HEAD -- {' '.join(TOOL_FILES_REL)} の終了コード {rc})。\n"
            "       判定区間はコミット済みの道具からだけ開ける"
            "(事前登録 §14.4。prereg 監査(9 回目)の指摘 3・15 / 10 回目の指摘 1・2・3)。\n"
            "       手順: 道具の 2 ファイルをコミット → その "
            "`git log -1 --format=%H -- <2 ファイル>` を §14.4 の欄に書き写す → 6 本を走らせる"
        )
    # (j) `--data-root` が既定のままか(在庫の差し替えで (h) が空回りするのを止める)。
    #     **prereg 監査(9 回目)の指摘 20。リードの決定 20。**
    dflt = Path(default_data_root if default_data_root is not None
                else base.DEFAULT_DATA_ROOT).resolve()
    if data_root is not None and Path(data_root).resolve() != dflt:
        raise SystemExit(
            f"[止め] --mode full では --data-root を既定から変えられない"
            f"(渡された値: {data_root} / 既定: {dflt})。\n"
            "       在庫を差し替えると関門 (h) の判定区間の日の集合が空になる"
            "(事前登録 §3.1 の「残る穴」。prereg 監査(9 回目)の指摘 20)"
        )


# --------------------------------------------------------------------------
# 日付・在庫
# --------------------------------------------------------------------------


def liq_dir(root: Path) -> Path:
    return root / "liquidationSnapshot" / base.SYMBOL


def all_days(root: Path) -> list[str]:
    out = []
    for p in sorted(liq_dir(root).glob(f"{base.SYMBOL}-liquidationSnapshot-*.zip")):
        out.append("-".join(p.stem.rsplit("-", 3)[1:]))
    return out


def shift_day(day: str, k: int) -> str:
    d = _dt.date.fromisoformat(day) + _dt.timedelta(days=k)
    return d.isoformat()


def judgment_days(root: Path) -> list[str]:
    """判定区間の日 = 在庫の全日から**標本 6 日と 12 日走行の 10 日を除いた**もの。

    2026-09-18 の監査、指摘 4(標本 6 日)+ 指摘 2・14 / 返答 060 の #1(12 日走行の 10 日)。

    前版の `--mode full` は `all_days(root)` = 472 日をそのまま走り、探索段で使い切った
    標本 6 日を判定区間に混ぜていた。その後、標本 6 日の外を無審査で開ける穴(指摘 3)から
    2024-02-15〜26 の 12 日が走り、うち 10 日(= `SCALE12_JUDGMENT_DAYS_OPENED`)で
    §3 の観測量が全列そろって出た。**開いた日は判定区間に残さない。**
    事前登録が宣言する 456 日(472 − 6 − 10)と、機械が走る範囲と、検出力の n を、
    この 1 関数で一致させる。
    """
    opened = set(SAMPLE_DAYS) | set(SCALE12_JUDGMENT_DAYS_OPENED)
    return [d for d in all_days(root) if d not in opened]


def emit_raw_bp(days: list[str] | None) -> bool:
    """手順 1(`--mode anchor`)の出力に、生の `bp_h` 列を書いてよいか。

    2026-09-18 の監査(指摘 2)への対応。生の `bp_h(after_shift)` / `bp_h(before)` は
    設計 §3 (a) の主観測量そのものなので、**探索段(標本 6 日)の中だけ**で出す。
    標本 6 日の外を 1 日でも含む走行では、差 `bp_h(after_shift) − bp_h(before)` の
    分位だけを出し、生の列も「参考」表も書かない。

    `pred_under_*` / `resid_*` も落とす(リードの決定 3 は名指ししていない =
    **決定に無い判断**)。`pred_under_h = bp_h(before) × lag / h` は `before` の線形変換で、
    差の分位と並べると `before` と `after_shift` の生の値が復元できるため。
    仮置きであることを `docs/AUDITOR/VERDICTS/2026-09-18_reaction_run12.md` に書いた。
    """
    return days is not None and set(days) <= set(SAMPLE_DAYS)


# --------------------------------------------------------------------------
# 価格(60 秒バー)
# --------------------------------------------------------------------------


def day_bars(root: Path, day: str) -> tuple[np.ndarray, np.ndarray]:
    """1 日の aggTrades を 60 秒バーに間引く(`o3c_rows4.build_bar_series` と同じ)。"""
    p = base.agg_path(root, day)
    if not p.exists():
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.float64)
    t, pr, _q = base.load_agg_trades(p)
    return rows4.build_bar_series(t, pr, BAR_MS)


def minute_close(
    times: np.ndarray, prices: np.ndarray, start_ms: int, n_min: int
) -> np.ndarray:
    """[start_ms, start_ms + n_min 分) の 1 分ごとの**最後の約定価格**。約定なしは NaN。"""
    out = np.full(n_min, np.nan, dtype=np.float64)
    if times.size == 0:
        return out
    inside = (times >= start_ms) & (times < start_ms + n_min * 60_000)
    if not inside.any():
        return out
    k = ((times[inside] - start_ms) // 60_000).astype(np.int64)
    p = prices[inside]
    # 各分の最後の約定(k は昇順なので、後から書いたものが残る)。
    out[k] = p
    return out


# --------------------------------------------------------------------------
# ノード(方向つき)
# --------------------------------------------------------------------------


def node_bins(qty: np.ndarray) -> np.ndarray:
    """数量の上位 10% のビン(相対番号)。`base.profile_stats` と**同じ選び方**。"""
    qty = np.asarray(qty, dtype=np.float64)
    n = int(qty.size)
    k = base._ceil_tenth(n)
    idx = np.arange(n)
    return np.lexsort((idx, -qty))[:k]


def directional_node_bp(
    qty: np.ndarray, lo_bin: int, step: float, p_ref: float, sign: float
) -> float:
    """ノードのうち `sign`(+1 = 上 / −1 = 下)の側で p_ref に最も近いものまでの bp。

    符号は `base.profile_stats` と同じ (p_target − p_ref) / p_ref * 1e4。
    その側にノードが 1 つも無ければ NaN(設計 §3 (b)「無ければ NaN と件数」)。
    """
    rel = node_bins(qty)
    if rel.size == 0:
        return float("nan")
    centers = base.bin_center_price(rel.astype(np.int64) + lo_bin, step)
    d = np.asarray(centers, dtype=np.float64) - p_ref
    ok = d * sign > 0
    if not ok.any():
        return float("nan")
    dd = d[ok]
    rr = rel[ok]
    order = np.lexsort((rr, np.abs(dd)))
    return float(dd[order[0]] / p_ref * 1e4)


# --------------------------------------------------------------------------
# 約定プロファイルの列(`base.process_day` の累積器と同じ形)
# --------------------------------------------------------------------------

PROFILE_COLUMNS = [
    "p0",
    "bin_pct",
    "dist_node_bp",
    "dist_gap_bp",
    "vol_between_ratio",
    "dist_vwap_bp",
    "n_bins",
    "total_qty",
    "node_up_bp",
    "node_dn_bp",
]


def profile_columns(
    events: list[dict],
    times: np.ndarray,
    prices: np.ndarray,
    qtys: np.ndarray,
    window_ms: int,
    step: float,
) -> tuple[list[dict], dict]:
    """時刻の昇順に並んだ行に、約定プロファイルの列を付ける。

    窓は `[t − window_ms, t)`(`base.process_day` と同じ。**同じ `base.profile_stats` を呼ぶ**)。
    `events` の各要素は `profile_ts_ms` と `p_liq`(None なら直前約定価格 p0)を持つ。
    戻り値は (列の一覧, メモ)。列が作れなかった行は全部 NaN で残す(行は落とさない)。
    """
    n = len(events)
    out: list[dict] = [dict.fromkeys(PROFILE_COLUMNS, float("nan")) for _ in range(n)]
    note = {"rows_skipped_empty_window": 0, "rows_p_liq_outside_window_range": 0}
    if n == 0 or times.size == 0:
        note["rows_skipped_empty_window"] = n
        return out, note

    bins = base.bin_index_array(prices, step)
    gmin = int(bins.min())
    rel = (bins - gmin).astype(np.int64)
    width = int(rel.max()) + 1
    acc_q = np.zeros(width, dtype=np.float64)
    acc_c = np.zeros(width, dtype=np.int64)

    lo = hi = 0
    n_trades = times.size
    for i, ev in enumerate(events):
        t = int(ev["profile_ts_ms"])
        while hi < n_trades and times[hi] < t:
            acc_q[rel[hi]] += qtys[hi]
            acc_c[rel[hi]] += 1
            hi += 1
        left = t - window_ms
        while lo < hi and times[lo] < left:
            acc_q[rel[lo]] -= qtys[lo]
            acc_c[rel[lo]] -= 1
            lo += 1
        if lo >= hi:
            note["rows_skipped_empty_window"] += 1
            continue
        nz = np.nonzero(acc_c)[0]
        r0, r1 = int(nz[0]), int(nz[-1])
        sub_q = acc_q[r0 : r1 + 1].copy()
        sub_c = acc_c[r0 : r1 + 1]
        sub_q[sub_c == 0] = 0.0
        lo_bin = gmin + r0
        p0 = float(prices[hi - 1])
        raw = ev.get("p_liq")
        p_liq = p0 if raw is None else float(raw)
        if not (p_liq > 0):
            note["rows_skipped_empty_window"] += 1
            continue
        st = base.profile_stats(sub_q, lo_bin, step, p_liq, p0)
        if not st["p_liq_in_range"]:
            note["rows_p_liq_outside_window_range"] += 1
        o = out[i]
        o["p0"] = p0
        o["bin_pct"] = round(st["bin_pct"], 4)
        o["dist_node_bp"] = round(st["dist_node_bp"], 4)
        o["dist_gap_bp"] = round(st["dist_gap_bp"], 4)
        o["vol_between_ratio"] = round(st["vol_between_ratio"], 6)
        o["dist_vwap_bp"] = round(st["dist_vwap_bp"], 4)
        o["n_bins"] = st["n_bins"]
        o["total_qty"] = st["total_qty"]
        o["node_up_bp"] = directional_node_bp(sub_q, lo_bin, step, p_liq, +1.0)
        o["node_dn_bp"] = directional_node_bp(sub_q, lo_bin, step, p_liq, -1.0)
    return out, note


# --------------------------------------------------------------------------
# metrics(ΔOI と (d′) の比)
# --------------------------------------------------------------------------

RATIO_COLUMNS = (
    "count_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
)


def load_metrics_full(path: Path) -> dict:
    """metrics zip -> {"t_ms", "oi", <比の列>}。時刻の昇順。

    `o3c_oi_distance.load_metrics` と同じ読み方に、設計 §3 (d′) の 3 列を足しただけ。
    """
    cols = ["create_time", "sum_open_interest", *RATIO_COLUMNS]
    with zipfile.ZipFile(path) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            head = fh.readline()
        has_header = b"create_time" in head
        with z.open(name) as fh:
            if has_header:
                df = pd.read_csv(fh, usecols=cols)
            else:
                df = pd.read_csv(
                    fh, header=None, names=oid.METRICS_NAMES, usecols=cols
                )
    t = (
        pd.to_datetime(df["create_time"], utc=True)
        .astype("datetime64[ms, UTC]")
        .astype("int64")
        .to_numpy(dtype=np.int64)
    )
    order = np.argsort(t, kind="stable")
    out = {"t_ms": t[order]}
    out["oi"] = pd.to_numeric(df["sum_open_interest"], errors="coerce").to_numpy(
        dtype=np.float64
    )[order]
    for c in RATIO_COLUMNS:
        out[c] = pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=np.float64)[order]
    return out


def all_deltas(t_ms: np.ndarray, oi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """ΔOI(T) = OI(T) − OI(T − 5 分)。**直前の行がちょうど 5 分前にある行だけ**。

    `o3c_oi_distance.build_delta_buckets` と同じ規則(符号で絞らないところだけが違う)。
    戻り値は (T[ms], ΔOI)。
    """
    if t_ms.size < 2:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    dt = t_ms[1:] - t_ms[:-1]
    ok = (dt == BUCKET_MS) & np.isfinite(oi[1:]) & np.isfinite(oi[:-1])
    return t_ms[1:][ok], (oi[1:] - oi[:-1])[ok]


def window_sum(
    t_end: np.ndarray, delta: np.ndarray, lo_ms: int, hi_ms: int
) -> tuple[float, int]:
    """ΔOI の桶のうち T ∈ (lo_ms, hi_ms] のものを足す。戻り値は (合計, 桶の数)。

    桶が 1 つも無ければ (NaN, 0)。**0 を返して「変化なし」に見せない。**
    """
    if t_end.size == 0 or hi_ms <= lo_ms:
        return float("nan"), 0
    a = int(np.searchsorted(t_end, lo_ms, side="right"))
    b = int(np.searchsorted(t_end, hi_ms, side="right"))
    if b <= a:
        return float("nan"), 0
    return float(delta[a:b].sum()), int(b - a)


# --------------------------------------------------------------------------
# 到達・最大順行 / 逆行
# --------------------------------------------------------------------------


def first_touch_ms(
    times: np.ndarray,
    prices: np.ndarray,
    i0: int,
    i1: int,
    anchor_price: float,
    target: float,
) -> float:
    """[i0, i1) の約定の列を歩いて、`target` を最初にまたいだ時刻[ms]。無ければ NaN。

    `target >= anchor_price` なら `price >= target`、そうでなければ `price <= target`。
    **ちょうど触れたら到達**(設計 §9 のテスト案 1)。
    """
    if not np.isfinite(target) or i1 <= i0:
        return float("nan")
    seg = prices[i0:i1]
    hit = seg >= target if target >= anchor_price else seg <= target
    if not hit.any():
        return float("nan")
    return float(times[i0 + int(np.argmax(hit))])


def running_extremes(
    prices: np.ndarray, i0: int, i1: int
) -> tuple[np.ndarray, np.ndarray]:
    """[i0, i1) の走る最大 / 最小。"""
    seg = prices[i0:i1]
    if seg.size == 0:
        return seg, seg
    return np.maximum.accumulate(seg), np.minimum.accumulate(seg)


# --------------------------------------------------------------------------
# bitFlyer 1 分足(設計 §6)
# --------------------------------------------------------------------------


def load_bitflyer_minutes(years: list[int], root: Path = BITFLYER_DIR) -> dict:
    """`candles_1m_<年>.csv.gz` を読む。戻り値は {"t_ms", "close", "high", "low"}。

    `ts` は ISO-8601 UTC 表記(README。**bitFlyer の一次文書ではない**)。
    約定が 0 の分は null のまま NaN にする(**前値で埋めない**。設計 §6)。
    """
    parts = []
    missing: list[int] = []
    for y in sorted(set(years)):
        p = root / f"candles_1m_{y}.csv.gz"
        if not p.exists():
            missing.append(y)
            continue
        df = pd.read_csv(p, usecols=["ts", "open", "high", "low", "close"])
        parts.append(df)
    if not parts:
        return {
            "t_ms": np.zeros(0, dtype=np.int64),
            "close": np.zeros(0),
            "high": np.zeros(0),
            "low": np.zeros(0),
            "years_missing": missing,
        }
    df = pd.concat(parts, ignore_index=True)
    t = (
        pd.to_datetime(df["ts"], utc=True)
        .astype("datetime64[ms, UTC]")
        .astype("int64")
        .to_numpy(dtype=np.int64)
    )
    order = np.argsort(t, kind="stable")
    return {
        "t_ms": t[order],
        "close": pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=np.float64)[
            order
        ],
        "high": pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=np.float64)[
            order
        ],
        "low": pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=np.float64)[
            order
        ],
        "years_missing": missing,
    }


def bf_close_at_or_before(bf: dict, ts_ms: int, staleness_ms: int = STALENESS_MS) -> float:
    """`ts_ms` 以前で最も新しい 1 分足の終値。null の分・遡りすぎは NaN(前値で埋めない)。"""
    t = bf["t_ms"]
    if t.size == 0:
        return float("nan")
    i = int(np.searchsorted(t, ts_ms, side="right")) - 1
    if i < 0:
        return float("nan")
    if ts_ms - int(t[i]) > staleness_ms:
        return float("nan")
    return float(bf["close"][i])


def _returns(closes: np.ndarray) -> np.ndarray:
    prev = closes[:-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(
            np.isfinite(prev) & (prev > 0), (closes[1:] - prev) / prev * 1e4, np.nan
        )
    return r


def _corr(a: np.ndarray, b: np.ndarray, min_pairs: int) -> tuple[float, int]:
    ok = np.isfinite(a) & np.isfinite(b)
    n = int(ok.sum())
    if n < min_pairs:
        return float("nan"), n
    x, y = a[ok], b[ok]
    sx, sy = x.std(), y.std()
    if sx <= 0 or sy <= 0:
        return float("nan"), n
    return float(np.corrcoef(x, y)[0, 1]), n


def xcorr_best_lag(
    bn: np.ndarray, bf: np.ndarray, max_lag: int, min_pairs: int
) -> tuple[float, float, int]:
    """1 分リターン 2 本の相互相関を lag −max_lag〜+max_lag で取り、最大の lag を返す。

    lag = L は「bitFlyer が Binance より L 分**遅れる**」向きに取る
    (`bn[i]` と `bf[i + L]` を突き合わせる)。戻り値 (最大の lag, その相関, 組数)。
    """
    best_lag, best_r, best_n = float("nan"), float("nan"), 0
    n = bn.size
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            a, b = bn[: n - lag], bf[lag:]
        else:
            a, b = bn[-lag:], bf[: n + lag]
        if a.size == 0:
            continue
        r, npair = _corr(a, b, min_pairs)
        if np.isfinite(r) and (not np.isfinite(best_r) or r > best_r):
            best_lag, best_r, best_n = float(lag), r, npair
    return best_lag, best_r, best_n


# --------------------------------------------------------------------------
# 列の並び
# --------------------------------------------------------------------------


def horizon_columns() -> list[str]:
    cols: list[str] = []
    for h in HORIZONS_MIN:
        cols += [f"bp_{h}m", f"bp_{h}m_reactdir", f"bp_{h}m_abs"]
    for h in HORIZONS_MIN:
        cols += [f"mfe_{h}m_reactdir", f"mae_{h}m_reactdir"]
    for tgt in REACH_TARGETS:
        cols.append(f"reach_{tgt}_sec")
        cols += [f"reach_{tgt}_{h}m" for h in HORIZONS_MIN]
    for h in HORIZONS_MIN:
        cols += [f"doi_post_{h}m", f"doi_post_{h}m_n"]
    for h in HORIZONS_MIN:
        cols += [f"bf_bp_{h}m", f"bf_bp_{h}m_reactdir"]
    return cols


REACH_TARGETS = ("back_vwap", "back_node", "fwd_node", "node_up", "node_dn")

BASE_COLUMNS = [
    "kind",
    "day",
    "cascade_id",
    "side",
    "direction",
    "start_ms",
    "end_ms",
    "time_ms",
    "profile_ts_ms",
    "bundle_width_ms",
    "bundle_n_events_dedup",
    "bundle_total_qty_accum",
    "bundle_total_notional",
    "p_liq",
]

ANCHOR_COLUMNS = [
    "anchor_ts_ms",
    "anchor_price",
    "anchor_before_ts_ms",
    "anchor_before_price",
    "anchor_lag_ms",
    "anchor_price_diff_bp",
]

DOI_COLUMNS = [
    "doi_pre_1h",
    "doi_pre_1h_n",
    "doi_pre_4h",
    "doi_pre_4h_n",
    "doi_in",
    "doi_in_n",
]

RATIO_OUT_COLUMNS = ["m_ts_ms"] + [f"m_{c}" for c in RATIO_COLUMNS]

TARGET_PRICE_COLUMNS = [f"p_tgt_{t}" for t in REACH_TARGETS]

BF_COLUMNS = [
    "bf_anchor_ts_ms",
    "bf_anchor_close",
    "bf_xcorr_best_lag_min",
    "bf_xcorr_best_r",
    "bf_xcorr_n",
]

# 合わせた対照 (ii) の 1 対 1 の相手の束の `cascade_id`(束の行と一様対照の行では空)。
# **列の並びの末尾に足す**ので、既にある列の位置は 1 つも動かない
# (2026-09-18、prereg 監査(3 回目)の指摘 6。読みの道具が 1 対 1 の対応を
# `cascade_id` の連番の算術で**復元**していたのを、列で取る形に替えるため)。
MATCHED_PAIR_COLUMNS = ["matched_liq_id"]


def sample_columns() -> list[str]:
    return (
        BASE_COLUMNS
        + PROFILE_COLUMNS
        + oid.OI_COLUMNS
        + [dst for _, dst in oid.LIQDIR_SOURCE]
        + oid.LEVERAGE_COLUMNS
        + ["oi_covered"]
        + ANCHOR_COLUMNS
        + TARGET_PRICE_COLUMNS
        + horizon_columns()
        + DOI_COLUMNS
        + RATIO_OUT_COLUMNS
        + BF_COLUMNS
        + MATCHED_PAIR_COLUMNS
    )


# --------------------------------------------------------------------------
# 束と対照
# --------------------------------------------------------------------------


def cascade_event_segments(events: list, cascades: list[Cascade]) -> list[list]:
    """束 1 個ぶんのイベントの並びを取り出す(`build_cascades` の切り方をなぞらない)。

    `build_cascades` は入力の時刻順の**連続した区間**を 1 束にするので、`n_events` を
    順に切り出せばよい。両端の時刻が `start_ms` / `end_ms` と一致することを必ず確かめる。
    """
    evs = sorted(
        (e for e in events if e.exchange == EXCHANGE), key=lambda e: e.ts_ms
    )
    out: list[list] = []
    i = 0
    for c in cascades:
        seg = evs[i : i + c.n_events]
        i += c.n_events
        assert seg and seg[0].ts_ms == c.start_ms and seg[-1].ts_ms == c.end_ms, (
            c.cascade_id,
            seg[0].ts_ms if seg else None,
            seg[-1].ts_ms if seg else None,
        )
        out.append(seg)
    assert i == len(evs), (i, len(evs))
    return out


def matched_controls(
    liq_bin_pct: list[float],
    cand_times: list[int],
    cand_bin_pct: list[float],
    rng: random.Random,
    tol: float = MATCH_TOL_PCT,
) -> tuple[list[int | None], dict]:
    """`bin_pct` を ±tol 以内で合わせる、同日・置換なしのマッチング(設計 §5 (ii))。

    束 1 個に対し候補 1 点。**±tol 以内に候補が無い束は対照を作らない**(None を返す)。
    同点は `rng` で 1 つ選ぶ。戻り値は (束ごとの候補時刻 or None, メモ)。
    """
    avail = [
        (v, t) for v, t in zip(cand_bin_pct, cand_times) if np.isfinite(v)
    ]
    avail.sort()
    vals = [v for v, _ in avail]
    used = [False] * len(avail)
    out: list[int | None] = []
    n_no_candidate = 0
    for bp in liq_bin_pct:
        if not np.isfinite(bp):
            out.append(None)
            n_no_candidate += 1
            continue
        lo = int(np.searchsorted(vals, bp - tol, side="left"))
        hi = int(np.searchsorted(vals, bp + tol, side="right"))
        best: list[int] = []
        best_d = None
        for j in range(lo, hi):
            if used[j]:
                continue
            d = abs(avail[j][0] - bp)
            if best_d is None or d < best_d - 1e-12:
                best_d, best = d, [j]
            elif abs(d - best_d) <= 1e-12:
                best.append(j)
        if not best:
            out.append(None)
            n_no_candidate += 1
            continue
        j = best[0] if len(best) == 1 else rng.choice(best)
        used[j] = True
        out.append(int(avail[j][1]))
    return out, {
        "candidates": len(avail),
        "bundles_without_candidate": n_no_candidate,
        "match_tolerance_pct": tol,
    }


# --------------------------------------------------------------------------
# 手順 1: 起点の妥当性(--mode anchor)
# --------------------------------------------------------------------------

ANCHOR_BASE_COLUMNS = [
    "cascade_id",
    "day",
    "start_ms",
    "end_ms",
    "bundle_width_ms",
    "direction",
    "n_events",
    "tie_after_shift",
    "path_after_shift",
    "tie_before",
    "path_before",
    "anchor_ts_ms",
    "anchor_price",
    "anchor_before_ts_ms",
    "anchor_before_price",
    "anchor_lag_ms",
    "anchor_price_diff_bp",
]

# 生の主観測量(`emit_raw_bp` が False の走行では 1 列も書かない)。
ANCHOR_RAW_COLUMNS = (
    [f"bp_{h}m_after_shift" for h in HORIZONS_MIN]
    + [f"bp_{h}m_before" for h in HORIZONS_MIN]
    + [f"pred_under_{h}m" for h in HORIZONS_MIN]
    + [f"resid_{h}m" for h in HORIZONS_MIN]
)


def anchor_table_columns(emit_raw: bool) -> list[str]:
    """手順 1 の `table.csv` の列。`emit_raw` が False なら生の `bp_h` 系を落とす。"""
    cols = list(ANCHOR_BASE_COLUMNS) + [f"bp_{h}m_diff" for h in HORIZONS_MIN]
    if emit_raw:
        cols += ANCHOR_RAW_COLUMNS
    return cols

QUANTS = (5, 25, 50, 75, 95)


def _quant_block(x: np.ndarray) -> dict | None:
    v = np.asarray(x, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    out = {f"q{q}": round(float(np.percentile(v, q)), 4) for q in QUANTS}
    out["n"] = int(v.size)
    out["mean"] = round(float(v.mean()), 4)
    return out


def cascade_day(c: Cascade) -> str:
    return _dt.datetime.fromtimestamp(
        c.end_ms / 1000, _dt.timezone.utc
    ).date().isoformat()


def _anchor_chunks_bar60(
    root: Path, cascades: list[Cascade], days: list[str] | None
) -> tuple[list[tuple[list[Cascade], PriceSeries]], int, list[str]]:
    """60 秒バー: 全期間を 1 本の系列にする(`o3c_rows4.run_ties` と同じ形)。"""
    use_days = list(days) if days is not None else all_days(root)
    if days is not None:
        # h = 240 分の窓が翌日に出るので、翌日も読む(在庫にある日だけ)。
        stock = set(all_days(root))
        for d in list(use_days):
            nxt = shift_day(d, 1)
            if nxt in stock and nxt not in use_days:
                use_days.append(nxt)
        use_days = sorted(use_days)
    bt: list[np.ndarray] = []
    bp: list[np.ndarray] = []
    missing: list[str] = []
    for d in use_days:
        t, p = day_bars(root, d)
        if t.size == 0:
            missing.append(d)
            continue
        bt.append(t)
        bp.append(p)
    times = np.concatenate(bt) if bt else np.zeros(0, dtype=np.int64)
    prices_arr = np.concatenate(bp) if bp else np.zeros(0)
    order = np.argsort(times, kind="stable")
    prices = PriceSeries(ts_ms=times[order].tolist(), price=prices_arr[order].tolist())
    print(f"60 秒バー {len(prices.ts_ms)} 点 / 読めなかった日 {len(missing)}", flush=True)
    return [(cascades, prices)], len(prices.ts_ms), missing


def _anchor_chunks_trades(
    root: Path, cascades: list[Cascade], days: list[str] | None
):
    """約定そのまま: 日ごとに、要る範囲だけ切った系列を作る(`run_ties` と同じ形)。

    全期間の約定を 1 本にすると載らないため、束の終わりの日ごとに
    `[最小 start − 5 分, 最大 end + 240 分 + 5 分]` を覆う日だけ読む。
    """
    stock = all_days(root)
    by_day: dict[str, list[Cascade]] = {}
    for c in cascades:
        by_day.setdefault(cascade_day(c), []).append(c)
    use_days = sorted(by_day) if days is None else sorted(set(days) & set(by_day))
    cache: dict[str, tuple] = {}
    missing: list[str] = []
    n_points = 0

    def agg_day(d: str):
        if d not in cache:
            p = base.agg_path(root, d)
            if p.exists():
                cache[d] = base.load_agg_trades(p)
            else:
                cache[d] = None
                if d not in missing and d in stock:
                    missing.append(d)
        return cache[d]

    max_h_ms = max(HORIZONS_MIN) * 60_000
    for i, d in enumerate(use_days):
        cs = by_day[d]
        lo = min(c.start_ms for c in cs) - STALENESS_MS
        hi = max(c.end_ms for c in cs) + max_h_ms + STALENESS_MS
        d_lo = _dt.datetime.fromtimestamp(lo / 1000, _dt.timezone.utc).date().isoformat()
        d_hi = _dt.datetime.fromtimestamp(hi / 1000, _dt.timezone.utc).date().isoformat()
        need = [d_lo]
        while need[-1] < d_hi:
            need.append(shift_day(need[-1], 1))
        parts = [agg_day(x) for x in need]
        parts = [x for x in parts if x is not None and x[0].size]
        if parts:
            tt = np.concatenate([x[0] for x in parts])
            pp = np.concatenate([x[1] for x in parts])
            if not bool(np.all(tt[1:] >= tt[:-1])):
                o = np.argsort(tt, kind="stable")
                tt, pp = tt[o], pp[o]
            m = (tt >= lo) & (tt <= hi)
            ps = PriceSeries(ts_ms=tt[m].tolist(), price=pp[m].tolist())
            n_points += int(m.sum())
        else:
            ps = PriceSeries(ts_ms=[], price=[])
        yield_chunk = (cs, ps)
        for k in list(cache):
            if k < d:
                del cache[k]
        if (i + 1) % 50 == 0:
            print(f"  約定そのまま {i + 1}/{len(use_days)} 日", flush=True)
        yield yield_chunk, n_points, missing


def run_anchor(
    root: Path,
    out_dir: Path,
    gap_ms: int,
    days: list[str] | None,
    granularity: str = "bar60",
) -> dict:
    t0 = time.time()
    # **決定 3(10 回目の指摘 1)**: 出力を 1 バイトも書く前に道具の版と汚れを測る。
    tool = tool_version_block()
    events, dedup_stats = load_binance_cm_liquidations_with_dedup_stats(liq_dir(root))
    cascades = build_cascades(events, EXCHANGE, gap_ms=gap_ms)
    print(
        f"清算 一意 {len(events)} 件(生 {dedup_stats.n_in})-> 束 {len(cascades)} 個"
        f"(gap {gap_ms} ms)",
        flush=True,
    )

    if days is not None:
        keep = set(days)
        cascades = [c for c in cascades if cascade_day(c) in keep]

    emit_raw = emit_raw_bp(days)
    out_rows: list[dict] = []
    n_points = 0
    missing: list[str] = []

    if granularity == "bar60":
        chunks, n_points, missing = _anchor_chunks_bar60(root, cascades, days)
        chunk_iter = iter(chunks)
    else:
        def _gen():
            nonlocal n_points, missing
            for chunk, npts, miss in _anchor_chunks_trades(root, cascades, days):
                n_points, missing = npts, miss
                yield chunk
        chunk_iter = _gen()

    for cs, prices in chunk_iter:
        out_rows.extend(_anchor_rows(cs, prices))

    if granularity != "bar60":
        print(f"約定そのまま {n_points} 点 / 読めなかった日 {len(missing)}", flush=True)

    df = pd.DataFrame(out_rows, columns=anchor_table_columns(emit_raw))
    return _finish_anchor(
        df,
        out_dir,
        gap_ms,
        days,
        granularity,
        emit_raw,
        dedup_stats,
        root,
        t0,
        n_points,
        missing,
        tool,
    )


def _anchor_rows(cascades: list[Cascade], prices: PriceSeries) -> list[dict]:
    rows_after = compute_reactions(
        cascades,
        prices,
        horizons_min=HORIZONS_MIN,
        anchor_max_staleness_ms=STALENESS_MS,
        future_max_staleness_ms=STALENESS_MS,
        anchor="after_shift",
    )
    rows_before = compute_reactions(
        cascades,
        prices,
        horizons_min=HORIZONS_MIN,
        anchor_max_staleness_ms=STALENESS_MS,
        future_max_staleness_ms=STALENESS_MS,
        anchor="before",
    )
    cls_after = {r["cascade_id"]: r for r in rows4.classify(prices, cascades, "after_shift")}
    cls_before = {r["cascade_id"]: r for r in rows4.classify(prices, cascades, "before")}

    out_rows: list[dict] = []
    for c, ra, rb in zip(cascades, rows_after, rows_before):
        ca = cls_after[c.cascade_id]
        cb = cls_before[c.cascade_id]
        anchor_ts = ra["anchor_ts_ms"]
        lag = (int(anchor_ts) - int(c.end_ms)) if anchor_ts is not None else float("nan")
        pa, pb = ra["anchor_price"], ra.get("anchor_before_price", float("nan"))
        pdiff = (
            (pa - pb) / pb * 1e4
            if np.isfinite(pa) and np.isfinite(pb) and pb > 0
            else float("nan")
        )
        row = {
            "cascade_id": c.cascade_id,
            "day": _dt.datetime.fromtimestamp(
                c.end_ms / 1000, _dt.timezone.utc
            ).date().isoformat(),
            "start_ms": c.start_ms,
            "end_ms": c.end_ms,
            "bundle_width_ms": c.end_ms - c.start_ms,
            "direction": c.direction,
            "n_events": c.n_events,
            "tie_after_shift": ca["tie"],
            "path_after_shift": ca["path"],
            "tie_before": cb["tie"],
            "path_before": cb["path"],
            "anchor_ts_ms": anchor_ts,
            "anchor_price": pa,
            "anchor_before_ts_ms": ra.get("anchor_before_ts_ms"),
            "anchor_before_price": pb,
            "anchor_lag_ms": lag,
            "anchor_price_diff_bp": pdiff,
        }
        for h in HORIZONS_MIN:
            a = ra[f"bp_{h}m"]
            b = rb[f"bp_{h}m"]
            row[f"bp_{h}m_after_shift"] = a
            row[f"bp_{h}m_before"] = b
            row[f"bp_{h}m_diff"] = a - b
            # 設計 §2.3 の 3。「仕込み」の代わりに `before` の値を当てた予想。
            pred = (
                b * (lag / (h * 60_000.0))
                if np.isfinite(b) and isinstance(lag, int)
                else float("nan")
            )
            row[f"pred_under_{h}m"] = pred
            row[f"resid_{h}m"] = (b - a) - pred if np.isfinite(pred) else float("nan")
        out_rows.append(row)
    return out_rows


def _finish_anchor(
    df: pd.DataFrame,
    out_dir: Path,
    gap_ms: int,
    days: list[str] | None,
    granularity: str,
    emit_raw: bool,
    dedup_stats,
    root: Path,
    t0: float,
    n_points: int,
    missing: list[str],
    tool: dict | None = None,
) -> dict:
    # **決定 3(10 回目の指摘 1)**: `tool` は**出力を書く前に**測った道具の版と汚れ。
    tool = tool if tool is not None else tool_version_block()
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "table.csv", index=False)

    non_tie = df[df["tie_after_shift"] == False]  # noqa: E712
    # 2026-09-18 の監査(指摘 1)・リードの決定 1。
    # 「非タイ」は `tie_after_shift == False` だけで切っており、その 8 割近くは
    # `before` 側ではタイである。**両側とも非タイ**の集合を別に出す。
    non_tie_both = df[
        (df["tie_after_shift"] == False) & (df["tie_before"] == False)  # noqa: E712
    ]
    summary = {
        "params": {
            "mode": "anchor",
            "gap_ms": gap_ms,
            "granularity": "60s_bar" if granularity == "bar60" else "trades",
            "horizons_min": list(HORIZONS_MIN),
            "staleness_ms": STALENESS_MS,
            "days": list(days) if days is not None else f"all({len(all_days(root))})",
            "raw_bp_columns_emitted": bool(emit_raw),
            "price_points": int(n_points),
            "days_unreadable": list(missing),
            "data_root": str(root),
            "design": "docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md",
        },
        # **決定 16(8 回目)+ 決定 3(10 回目)**: 走行の道具の版
        # (`git log -1 --format=%H -- <道具 2 ファイル>`)。**出力を書く前に測った値である。**
        "tool_commit": tool["tool_commit"],
        # **決定 3・15(9 回目)+ 決定 1・2・3(10 回目)**: 道具の 2 ファイルが汚れていたか
        # (`git diff --quiet HEAD -- <道具 2 ファイル>`)。**版の担保を 1 本にする。**
        "tool_dirty": tool["tool_dirty"],
        "elapsed_sec": round(time.time() - t0, 2),
        "liq_rows_raw": dedup_stats.n_in,
        "liq_rows_unique": dedup_stats.n_out,
        "liq_rows_dropped_dedup": dedup_stats.n_dropped,
        "bundles": int(len(df)),
        "bundles_width_zero": int((df["bundle_width_ms"] == 0).sum()),
        "bundles_by_direction": {
            str(k): int(v) for k, v in df["direction"].value_counts().items()
        },
        "tie_counts": {
            "after_shift": {
                "tie": int((df["tie_after_shift"] == True).sum()),  # noqa: E712
                "non_tie": int(len(non_tie)),
                "missing": int(df["tie_after_shift"].isna().sum()),
                "paths": {
                    str(k): int(v)
                    for k, v in df["path_after_shift"].value_counts().items()
                },
            },
            "before": {
                "tie": int((df["tie_before"] == True).sum()),  # noqa: E712
                "non_tie": int((df["tie_before"] == False).sum()),  # noqa: E712
                "missing": int(df["tie_before"].isna().sum()),
                "paths": {
                    str(k): int(v)
                    for k, v in df["path_before"].value_counts().items()
                },
            },
            # 指摘 1: 「非タイ」の中身を 2x2 で開く。
            "crosstab_after_shift_x_before": {
                "both_non_tie": int(len(non_tie_both)),
                "after_shift_non_tie_but_before_tie": int(
                    ((df["tie_after_shift"] == False) & (df["tie_before"] == True)).sum()  # noqa: E712
                ),
                "after_shift_tie_but_before_non_tie": int(
                    ((df["tie_after_shift"] == True) & (df["tie_before"] == False)).sum()  # noqa: E712
                ),
                "both_tie": int(
                    ((df["tie_after_shift"] == True) & (df["tie_before"] == True)).sum()  # noqa: E712
                ),
            },
        },
        "anchor_lag_ms": {
            "all": _quant_block(df["anchor_lag_ms"].to_numpy(dtype=np.float64)),
            "non_tie": _quant_block(non_tie["anchor_lag_ms"].to_numpy(dtype=np.float64)),
            "non_tie_both": _quant_block(
                non_tie_both["anchor_lag_ms"].to_numpy(dtype=np.float64)
            ),
        },
        "anchor_price_diff_bp": {
            "all": _quant_block(df["anchor_price_diff_bp"].to_numpy(dtype=np.float64)),
            "non_tie": _quant_block(
                non_tie["anchor_price_diff_bp"].to_numpy(dtype=np.float64)
            ),
            "non_tie_both": _quant_block(
                non_tie_both["anchor_price_diff_bp"].to_numpy(dtype=np.float64)
            ),
        },
        "diff_quantiles": {},
        "notes": [
            "観測のみ。判定は書いていない。",
            "タイの定義と経路は scripts/o3c_rows4.py: classify をそのまま呼んでいる"
            "(時間分解能 / 価格の刻み)。",
            "bp_*_diff = bp(after_shift) − bp(before)。",
            "pred_under_* = before の bp × (anchor_ts − end_ms) / h(設計 §2.3 の 3。"
            "合成の「仕込み」の代わりに before の値を当てた予想。**before が非タイ行では"
            "正しいという仮定に依存する**)。resid_* = (before − after_shift) − pred_under。",
            "非タイ = tie_after_shift == False。その部分集合として "
            "non_tie_both = tie_after_shift も tie_before も False の行を別に出す"
            "(2026-09-18 の監査の指摘 1)。",
            (
                "生の bp_h 列・pred_under・resid を出した(標本 6 日の中だけ)。"
                if emit_raw
                else "生の bp_h 列・pred_under・resid は書いていない"
                "(標本 6 日の外を含む走行。2026-09-18 の監査の指摘 2)。"
            ),
            f"粒度は {'60 秒バー' if granularity == 'bar60' else '約定そのまま'}。",
        ],
    }
    if emit_raw:
        summary["notes"].insert(
            3,
            "pred_under_* = before の bp × (anchor_ts − end_ms) / h(設計 §2.3 の 3。"
            "合成の「仕込み」の代わりに before の値を当てた予想。**before が非タイ行では"
            "正しいという仮定に依存する**)。resid_* = (before − after_shift) − pred_under。",
        )
    for h in HORIZONS_MIN:
        block: dict = {}
        for label, sub in (("non_tie", non_tie), ("non_tie_both", non_tie_both), ("all", df)):
            entry = {
                "diff": _quant_block(sub[f"bp_{h}m_diff"].to_numpy(dtype=np.float64)),
                "abs_diff": _quant_block(
                    np.abs(sub[f"bp_{h}m_diff"].to_numpy(dtype=np.float64))
                ),
            }
            if emit_raw and label != "all":
                entry["after_shift"] = _quant_block(
                    sub[f"bp_{h}m_after_shift"].to_numpy(dtype=np.float64)
                )
                entry["before"] = _quant_block(
                    sub[f"bp_{h}m_before"].to_numpy(dtype=np.float64)
                )
                entry["pred_under"] = _quant_block(
                    sub[f"pred_under_{h}m"].to_numpy(dtype=np.float64)
                )
                entry["resid"] = _quant_block(
                    sub[f"resid_{h}m"].to_numpy(dtype=np.float64)
                )
            block[label] = entry
        summary["diff_quantiles"][f"h{h}m"] = block
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    base.write_md5sums(out_dir, ["table.csv", "summary.json"])
    return summary


# --------------------------------------------------------------------------
# 手順 2 / 3: 観測表(--mode sample / full)
# --------------------------------------------------------------------------


def build_day_rows(
    day: str,
    root: Path,
    metrics_root: Path,
    cascades_of_day: list[Cascade],
    segs_of_day: list[list],
    liq_times_of_day: list[int],
    window_hours: float,
    bin_pct: float,
    seed: int,
    mmr: float | None,
    agg_cache: dict,
    metrics_cache: dict,
    bf: dict,
    match_order: str = "table",
) -> tuple[list[dict], list[dict], dict]:
    """1 日ぶんの行(清算 + 対照 2 本)を作る。戻り値は (主表の行, mixed の行, メモ)。"""
    step = base.log_step(bin_pct)
    window_ms = int(round(window_hours * 3600 * 1000))
    day_start, day_end = base.day_bounds_ms(day)
    max_h_ms = max(HORIZONS_MIN) * 60_000

    # --- 約定(前の日 .. 翌日。h = 240 分の窓が翌日に出るため) --------------
    n_prev = base.required_prev_days(window_hours)
    need_days = base.prev_days(day, n_prev) + [day, shift_day(day, 1)]
    missing_agg: list[str] = []
    parts = []
    for d in need_days:
        if d not in agg_cache:
            p = base.agg_path(root, d)
            agg_cache[d] = base.load_agg_trades(p) if p.exists() else None
        if agg_cache[d] is None:
            missing_agg.append(d)
        else:
            parts.append(agg_cache[d])
    if not parts:
        raise SystemExit(f"[止め] {day} の aggTrades が 1 日も読めない")
    times = np.concatenate([p[0] for p in parts])
    prices = np.concatenate([p[1] for p in parts])
    qtys = np.concatenate([p[2] for p in parts])
    if not bool(np.all(times[1:] >= times[:-1])):
        o = np.argsort(times, kind="stable")
        times, prices, qtys = times[o], prices[o], qtys[o]

    # --- 対照 (i) 一様 ------------------------------------------------------
    rng = random.Random(f"{seed}|{day}")
    n_bundles = len(cascades_of_day)
    ctrl_times = base.sample_control_times(
        liq_times_of_day, day_start, day_end, n_bundles, rng, CONTROL_GAP_MS
    )

    # --- 対照 (ii) の候補(1 分刻み・清算から ±5 分以上) --------------------
    intervals = base.allowed_intervals(
        liq_times_of_day, day_start, day_end, CONTROL_GAP_MS
    )
    cand_times: list[int] = []
    for a, b in intervals:
        t = int(math.ceil(a / MATCH_GRID_MS) * MATCH_GRID_MS)
        while t < b:
            cand_times.append(t)
            t += MATCH_GRID_MS

    # --- プロファイルを 1 回のなめらかな走査で全部に付ける ------------------
    # 束 = 束の直前 W(profile_ts = start_ms)、対照 = その時刻。
    prof_events: list[dict] = []
    for c, seg in zip(cascades_of_day, segs_of_day):
        prof_events.append(
            {
                "tag": ("liq", c.cascade_id),
                "profile_ts_ms": int(c.start_ms),
                "time_ms": int(c.start_ms),
                "p_liq": float(seg[0].price),
                "side": SIDE_OF_DIRECTION.get(c.direction, ""),
            }
        )
    for i, t in enumerate(ctrl_times):
        prof_events.append(
            {
                "tag": ("uniform", i),
                "profile_ts_ms": int(t),
                "time_ms": int(t),
                "p_liq": None,
                "side": "",
            }
        )
    for i, t in enumerate(cand_times):
        prof_events.append(
            {
                "tag": ("cand", i),
                "profile_ts_ms": int(t),
                "time_ms": int(t),
                "p_liq": None,
                "side": "",
            }
        )
    prof_events.sort(key=lambda e: (e["profile_ts_ms"], e["tag"][0]))
    prof_cols, prof_note = profile_columns(
        prof_events, times, prices, qtys, window_ms, step
    )
    for ev, pc in zip(prof_events, prof_cols):
        ev.update(pc)
        if ev["p_liq"] is None:
            ev["p_liq"] = pc["p0"]

    by_tag = {ev["tag"]: (ev, pc) for ev, pc in zip(prof_events, prof_cols)}

    # --- 対照 (ii) のマッチング -------------------------------------------
    liq_bp = [by_tag[("liq", c.cascade_id)][0]["bin_pct"] for c in cascades_of_day]
    cand_bp = [by_tag[("cand", i)][0]["bin_pct"] for i in range(len(cand_times))]
    rng_m = random.Random(f"{seed}|{day}|matched")
    # 2026-09-18 の監査(指摘 21)。マッチングは貪欲・置換なしで**束の順に依存する**。
    # `match_order="reversed"` は束の順を逆にして同じ手続きを当て、
    # 「候補なし」になる束の集合が変わるかを実測するための経路である
    # (**既定は "table" で、走行の結果を変えない**)。
    if match_order == "reversed":
        order = list(range(len(liq_bp)))[::-1]
        m_rev, match_note = matched_controls(
            [liq_bp[i] for i in order], cand_times, cand_bp, rng_m
        )
        matched = [None] * len(liq_bp)
        for pos, i in enumerate(order):
            matched[i] = m_rev[pos]
    else:
        matched, match_note = matched_controls(liq_bp, cand_times, cand_bp, rng_m)
    unmatched_bin_pct = [
        liq_bp[i] for i, t in enumerate(matched) if t is None and np.isfinite(liq_bp[i])
    ]
    unmatched_ids = [
        cascades_of_day[i].cascade_id for i, t in enumerate(matched) if t is None
    ]

    # --- 建玉(ΔOI)--------------------------------------------------------
    metrics_need = base.prev_days(day, max(n_prev, 1)) + [day, shift_day(day, 1)]
    metrics_missing: list[str] = []
    md_list = []
    for d in metrics_need:
        if d not in metrics_cache:
            p = oid.metrics_path(metrics_root, d)
            metrics_cache[d] = load_metrics_full(p) if p.exists() else None
        m = metrics_cache[d]
        if m is None:
            metrics_missing.append(d)
        else:
            md_list.append(m)
    if md_list:
        m_t = np.concatenate([m["t_ms"] for m in md_list])
        m_oi = np.concatenate([m["oi"] for m in md_list])
        m_ratio = {c: np.concatenate([m[c] for m in md_list]) for c in RATIO_COLUMNS}
        o = np.argsort(m_t, kind="stable")
        m_t, m_oi = m_t[o], m_oi[o]
        m_ratio = {c: v[o] for c, v in m_ratio.items()}
    else:
        m_t = np.zeros(0, dtype=np.int64)
        m_oi = np.zeros(0)
        m_ratio = {c: np.zeros(0) for c in RATIO_COLUMNS}
    doi_t, doi_v = all_deltas(m_t, m_oi)

    # 建玉プロファイル(OI_DIST と同じ関数)。5 分桶の VWAP/按分は同じ作り方で作る。
    bucket_lookup: dict[int, tuple] = {}
    for d in metrics_need:
        p = base.agg_path(root, d)
        if not p.exists():
            continue
        key = f"__bucket__{d}"
        if key not in agg_cache:
            tt, pp, qq, mm = oid.load_agg_trades_with_maker(p)
            agg_cache[key] = oid.bucket_trade_stats(d, tt, pp, qq, mm)
        bs = agg_cache[key]
        for k in range(int(oid.BUCKETS_PER_DAY)):
            bucket_lookup[int(bs["start_ms"][k])] = (
                float(bs["vwap"][k]),
                float(bs["buy_share"][k]),
                float(bs["vol"][k]),
                int(bs["n"][k]),
                float(bs["vwap_buy"][k]),
                float(bs["vwap_sell"][k]),
            )
    buckets = oid.build_delta_buckets(
        [(m["t_ms"], m["oi"]) for m in md_list], bucket_lookup
    )
    cov = oid.coverage_start_ms(buckets["t_all"])

    # --- 行を組み立てる -----------------------------------------------------
    rows: list[dict] = []
    mixed_rows: list[dict] = []
    cascade_list: list[tuple[str, Cascade | None, dict, int]] = []
    # **束の行を先頭に、`cascades_of_day` と同じ順番で詰める**(下で segs_of_day[i_row] を引く)。
    for c, seg in zip(cascades_of_day, segs_of_day):
        cascade_list.append((KIND_LIQ, c, by_tag[("liq", c.cascade_id)][0], 0))
    for i, t in enumerate(ctrl_times):
        cascade_list.append((KIND_UNIFORM, None, by_tag[("uniform", i)][0], i))
    for i, t in enumerate(matched):
        if t is None:
            continue
        j = cand_times.index(t)
        cascade_list.append((KIND_MATCHED, None, by_tag[("cand", j)][0], i))

    # 反応は `compute_reactions` に同じ規則で当てる(対照も Cascade の形にする)。
    react_cascades: list[Cascade] = []
    for kind, c, ev, i in cascade_list:
        if c is not None:
            react_cascades.append(c)
        else:
            t = int(ev["time_ms"])
            react_cascades.append(
                Cascade(
                    cascade_id=f"{kind}_{day}_{i:05d}",
                    exchange=EXCHANGE,
                    kind="placebo",
                    start_ms=t,
                    end_ms=t,
                    n_events=0,
                    total_size=0.0,
                    direction="none",
                    first_price=None,
                    last_price=None,
                )
            )
    react_prices = PriceSeries(ts_ms=times.tolist(), price=prices.tolist())
    react_rows = compute_reactions(
        react_cascades,
        react_prices,
        horizons_min=HORIZONS_MIN,
        anchor_max_staleness_ms=STALENESS_MS,
        future_max_staleness_ms=STALENESS_MS,
        anchor="after_shift",
    )

    # 建玉側の列(OI_DIST の関数をそのまま)。時刻の昇順が要る。
    def _f(x) -> float:
        try:
            v = float(x)
        except (TypeError, ValueError):
            return float("nan")
        return v

    oi_input = [
        {
            "time_ms": int(ev["profile_ts_ms"]),
            "p_liq": _f(ev["p_liq"]),
            "p0": _f(ev["p0"]),
            "side": SIDE_OF_DIRECTION.get(c.direction, "") if c is not None else "",
        }
        for (kind, c, ev, i) in cascade_list
    ]
    # プロファイルが作れなかった行(窓に約定が 1 件も無い)は建玉側も作らない。
    usable = [
        i
        for i in range(len(oi_input))
        if np.isfinite(oi_input[i]["p_liq"])
        and oi_input[i]["p_liq"] > 0
        and np.isfinite(oi_input[i]["p0"])
        and oi_input[i]["p0"] > 0
    ]
    oi_order = sorted(usable, key=lambda i: oi_input[i]["time_ms"])
    oi_sorted = [oi_input[i] for i in oi_order]
    oi_cols_sorted, n_uncovered = oid.oi_columns_for_rows(
        oi_sorted, buckets, window_ms, step, cov, side_price="same"
    )
    blank = dict.fromkeys(oid.OI_COLUMNS, float("nan"))
    blank["oi_covered"] = 0
    oi_cols: list[dict] = [dict(blank) for _ in oi_input]
    for pos, i in enumerate(oi_order):
        oi_cols[i] = oi_cols_sorted[pos]
    n_oi_skipped = len(oi_input) - len(usable)

    n_bf_years = None
    for i_row, ((kind, c, ev, i), rr, oc) in enumerate(
        zip(cascade_list, react_rows, oi_cols)
    ):
        side = SIDE_OF_DIRECTION.get(c.direction, "") if c is not None else ""
        sign = REACT_SIGN.get(side, 1.0)
        anchor_ts = rr["anchor_ts_ms"]
        anchor_price = rr["anchor_price"]
        before_ts = rr.get("anchor_before_ts_ms")
        before_price = rr.get("anchor_before_price", float("nan"))
        end_ms = int(c.end_ms) if c is not None else int(ev["time_ms"])
        start_ms = int(c.start_ms) if c is not None else int(ev["time_ms"])
        p_liq = float(ev["p_liq"])

        row: dict = {
            "kind": kind,
            "day": day,
            "cascade_id": rr["cascade_id"],
            "side": side,
            "direction": c.direction if c is not None else "none",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "time_ms": end_ms,
            "profile_ts_ms": int(ev["profile_ts_ms"]),
            "bundle_width_ms": (end_ms - start_ms) if c is not None else "",
            "bundle_n_events_dedup": c.n_events if c is not None else "",
            # 束の行は cascade_list の先頭に順番どおり詰めてあるので i_row が使える。
            "bundle_total_qty_accum": (
                round(sum(e.qty for e in segs_of_day[i_row]), 6)
                if c is not None
                else ""
            ),
            "bundle_total_notional": round(c.total_size, 4) if c is not None else "",
            "p_liq": p_liq,
            "anchor_ts_ms": anchor_ts,
            "anchor_price": anchor_price,
            "anchor_before_ts_ms": before_ts,
            "anchor_before_price": before_price,
            "anchor_lag_ms": (int(anchor_ts) - end_ms) if anchor_ts is not None else "",
            "anchor_price_diff_bp": (
                round((anchor_price - before_price) / before_price * 1e4, 4)
                if np.isfinite(anchor_price)
                and np.isfinite(before_price)
                and before_price > 0
                else float("nan")
            ),
            # 合わせた対照 (ii) の 1 対 1 の相手の束の id(`i` は `cascades_of_day`
            # の添字である = 上の `cascade_list` の詰め方)。相手が mixed の束なら
            # その行は `table_mixed.csv` 側に出るが、id はここに残る。
            "matched_liq_id": (
                cascades_of_day[i].cascade_id if kind == KIND_MATCHED else ""
            ),
        }
        for k in PROFILE_COLUMNS:
            row[k] = ev[k]
        row.update(oc)
        oid._apply_liqdir_and_leverage(row, mmr)

        # ---- (a) 価格変化 --------------------------------------------------
        for h in HORIZONS_MIN:
            v = rr[f"bp_{h}m"]
            row[f"bp_{h}m"] = round(v, 4) if np.isfinite(v) else float("nan")
            row[f"bp_{h}m_reactdir"] = (
                round(v * sign, 4) if np.isfinite(v) else float("nan")
            )
            row[f"bp_{h}m_abs"] = round(abs(v), 4) if np.isfinite(v) else float("nan")

        # ---- (b)(c) 到達・最大順行 / 逆行 ---------------------------------
        for t_name in REACH_TARGETS:
            row[f"p_tgt_{t_name}"] = float("nan")
            row[f"reach_{t_name}_sec"] = float("nan")
            for h in HORIZONS_MIN:
                row[f"reach_{t_name}_{h}m"] = float("nan")
        for h in HORIZONS_MIN:
            row[f"mfe_{h}m_reactdir"] = float("nan")
            row[f"mae_{h}m_reactdir"] = float("nan")

        if anchor_ts is not None and np.isfinite(anchor_price) and anchor_price > 0:
            a_ts = int(anchor_ts)
            i0 = int(np.searchsorted(times, a_ts, side="left"))
            i1 = int(np.searchsorted(times, a_ts + max_h_ms, side="right"))
            targets = {
                "back_vwap": ev["dist_vwap_bp"],
                "back_node": ev["dist_node_bp"],
                "node_up": ev["node_up_bp"],
                "node_dn": ev["node_dn_bp"],
            }
            targets["fwd_node"] = (
                ev["node_dn_bp"]
                if side == "SELL"
                else (ev["node_up_bp"] if side == "BUY" else float("nan"))
            )
            for t_name, bp_val in targets.items():
                tgt = (
                    p_liq * (1.0 + float(bp_val) / 1e4)
                    if np.isfinite(float(bp_val if bp_val is not None else np.nan))
                    and np.isfinite(p_liq)
                    else float("nan")
                )
                row[f"p_tgt_{t_name}"] = round(tgt, 4) if np.isfinite(tgt) else float("nan")
                touch = first_touch_ms(times, prices, i0, i1, anchor_price, tgt)
                if np.isfinite(touch):
                    sec = (touch - a_ts) / 1000.0
                    row[f"reach_{t_name}_sec"] = round(sec, 3)
                for h in HORIZONS_MIN:
                    if not np.isfinite(tgt):
                        continue
                    if np.isfinite(touch) and (touch - a_ts) <= h * 60_000:
                        row[f"reach_{t_name}_{h}m"] = 1
                    else:
                        # 窓の終わりまで歩けているかを確かめる(足りなければ NaN)。
                        i_h = int(np.searchsorted(times, a_ts + h * 60_000, side="right"))
                        row[f"reach_{t_name}_{h}m"] = 0 if i_h > i0 else float("nan")
            if i1 > i0:
                rmax, rmin = running_extremes(prices, i0, i1)
                seg_t = times[i0:i1]
                for h in HORIZONS_MIN:
                    j = int(np.searchsorted(seg_t, a_ts + h * 60_000, side="right")) - 1
                    if j < 0:
                        continue
                    up = (rmax[j] - anchor_price) / anchor_price * 1e4
                    dn = (rmin[j] - anchor_price) / anchor_price * 1e4
                    a_, b_ = (up * sign, dn * sign)
                    row[f"mfe_{h}m_reactdir"] = round(max(a_, b_), 4)
                    row[f"mae_{h}m_reactdir"] = round(min(a_, b_), 4)

        # ---- (d) ΔOI ------------------------------------------------------
        v, n = window_sum(doi_t, doi_v, start_ms - 3_600_000, start_ms)
        row["doi_pre_1h"], row["doi_pre_1h_n"] = (round(v, 4) if np.isfinite(v) else v), n
        v, n = window_sum(doi_t, doi_v, start_ms - 14_400_000, start_ms)
        row["doi_pre_4h"], row["doi_pre_4h_n"] = (round(v, 4) if np.isfinite(v) else v), n
        v, n = window_sum(doi_t, doi_v, start_ms, end_ms)
        row["doi_in"], row["doi_in_n"] = (round(v, 4) if np.isfinite(v) else v), n
        for h in HORIZONS_MIN:
            if anchor_ts is None:
                row[f"doi_post_{h}m"], row[f"doi_post_{h}m_n"] = float("nan"), 0
                continue
            v, n = window_sum(
                doi_t, doi_v, int(anchor_ts), int(anchor_ts) + h * 60_000
            )
            row[f"doi_post_{h}m"] = round(v, 4) if np.isfinite(v) else v
            row[f"doi_post_{h}m_n"] = n

        # ---- (d′) 比(起点以前の最後の metrics 行)------------------------
        row["m_ts_ms"] = ""
        for c_name in RATIO_COLUMNS:
            row[f"m_{c_name}"] = float("nan")
        if m_t.size and anchor_ts is not None:
            k = int(np.searchsorted(m_t, int(anchor_ts), side="right")) - 1
            if k >= 0 and int(anchor_ts) - int(m_t[k]) <= 2 * BUCKET_MS:
                row["m_ts_ms"] = int(m_t[k])
                for c_name in RATIO_COLUMNS:
                    row[f"m_{c_name}"] = float(m_ratio[c_name][k])

        # ---- bitFlyer(§6)-------------------------------------------------
        row["bf_anchor_ts_ms"] = ""
        row["bf_anchor_close"] = float("nan")
        row["bf_xcorr_best_lag_min"] = float("nan")
        row["bf_xcorr_best_r"] = float("nan")
        row["bf_xcorr_n"] = 0
        for h in HORIZONS_MIN:
            row[f"bf_bp_{h}m"] = float("nan")
            row[f"bf_bp_{h}m_reactdir"] = float("nan")
        if anchor_ts is not None and bf["t_ms"].size:
            a_ts = int(anchor_ts)
            i_bf = int(np.searchsorted(bf["t_ms"], a_ts, side="right")) - 1
            if i_bf >= 0 and a_ts - int(bf["t_ms"][i_bf]) <= STALENESS_MS:
                row["bf_anchor_ts_ms"] = int(bf["t_ms"][i_bf])
                c0 = float(bf["close"][i_bf])
                row["bf_anchor_close"] = c0
                if np.isfinite(c0) and c0 > 0:
                    for h in HORIZONS_MIN:
                        c1 = bf_close_at_or_before(bf, a_ts + h * 60_000)
                        if np.isfinite(c1):
                            v = (c1 - c0) / c0 * 1e4
                            row[f"bf_bp_{h}m"] = round(v, 4)
                            row[f"bf_bp_{h}m_reactdir"] = round(v * sign, 4)
                # 相互相関(±10 分の 1 分リターン)。
                w0 = a_ts - XCORR_HALF_MIN * 60_000
                n_min = 2 * XCORR_HALF_MIN + 1
                w0 = (w0 // 60_000) * 60_000
                j0 = int(np.searchsorted(bf["t_ms"], w0, side="left"))
                bf_seg = np.full(n_min, np.nan)
                j1 = min(j0 + n_min, bf["t_ms"].size)
                if j1 > j0:
                    bf_seg[: j1 - j0] = bf["close"][j0:j1]
                bn_seg = minute_close(times, prices, w0, n_min)
                lag, r, npair = xcorr_best_lag(
                    _returns(bn_seg), _returns(bf_seg), XCORR_HALF_MIN, XCORR_MIN_PAIRS
                )
                row["bf_xcorr_best_lag_min"] = lag
                row["bf_xcorr_best_r"] = round(r, 4) if np.isfinite(r) else r
                row["bf_xcorr_n"] = npair

        if c is not None and c.direction == "mixed":
            mixed_rows.append(row)
        else:
            rows.append(row)

    note = {
        "day": day,
        "bundles": n_bundles,
        "bundles_mixed": len(mixed_rows),
        "bundles_width_zero": sum(
            1 for c in cascades_of_day if c.end_ms == c.start_ms
        ),
        "liq_events_in_day": len(liq_times_of_day),
        "control_uniform_drawn": len(ctrl_times),
        "control_matched_made": sum(1 for t in matched if t is not None),
        "control_matched_candidates": match_note["candidates"],
        "bundles_without_matched_candidate": match_note["bundles_without_candidate"],
        "unmatched_bin_pct_quantiles": _quant_block(
            np.array(unmatched_bin_pct, dtype=np.float64)
        ),
        # 指摘 21: 「候補なし」になった束を id で残す(順序依存を実測するため)。
        "unmatched_cascade_ids": unmatched_ids,
        "match_order": match_order,
        "agg_days_required": need_days,
        "agg_days_missing": missing_agg,
        "metrics_days_required": metrics_need,
        "metrics_days_missing": metrics_missing,
        "oi_coverage_start_ms": cov,
        "rows_oi_uncovered": int(n_uncovered),
        "rows_oi_skipped_no_profile": int(n_oi_skipped),
        "doi_rows": int(doi_t.size),
        "bf_years_missing": bf.get("years_missing", []),
    }
    note.update(prof_note)
    return rows, mixed_rows, note


def utc_check_block(
    days: list[str], root: Path, bf: dict, agg_cache: dict
) -> dict:
    """設計 §6 の時刻合わせの確認(1): 同じ分どうしの相互相関の lag を広く取る。

    **これは照合であって一次資料ではない**(設計 §10 の 3)。
    """
    bn_parts: list[np.ndarray] = []
    bf_parts: list[np.ndarray] = []
    rng_parts: list[np.ndarray] = []
    for d in days:
        p = base.agg_path(root, d)
        if not p.exists():
            continue
        if d not in agg_cache or agg_cache[d] is None:
            agg_cache[d] = base.load_agg_trades(p)
        t, pr, _q = agg_cache[d]
        ds, _de = base.day_bounds_ms(d)
        bn = minute_close(t, pr, ds, 1440)
        i0 = int(np.searchsorted(bf["t_ms"], ds, side="left"))
        seg = np.full(1440, np.nan)
        i1 = min(i0 + 1440, bf["t_ms"].size)
        if i1 > i0:
            seg[: i1 - i0] = bf["close"][i0:i1]
        hi = np.full(1440, np.nan)
        lo = np.full(1440, np.nan)
        if i1 > i0:
            hi[: i1 - i0] = bf["high"][i0:i1]
            lo[: i1 - i0] = bf["low"][i0:i1]
        bn_parts.append(bn)
        bf_parts.append(seg)
        with np.errstate(invalid="ignore"):
            rng_parts.append((hi - lo) / seg * 1e4)
    if not bn_parts:
        return {}
    bn = np.concatenate(bn_parts)
    bfc = np.concatenate(bf_parts)
    rng = np.concatenate(rng_parts)
    rbn, rbf = _returns(bn), _returns(bfc)
    lag, r, npair = xcorr_best_lag(rbn, rbf, UTC_CHECK_MAX_LAG_MIN, 30)
    # 値幅の大きい上位 N 分だけに絞った版。
    rr = rng[1:]
    top = np.full(rr.size, False)
    finite = np.where(np.isfinite(rr))[0]
    if finite.size:
        k = min(UTC_CHECK_TOP_N, finite.size)
        sel = finite[np.argsort(-rr[finite])[:k]]
        top[sel] = True
    rbn_t = np.where(top, rbn, np.nan)
    lag_t, r_t, n_t = xcorr_best_lag(rbn_t, rbf, UTC_CHECK_MAX_LAG_MIN, 10)
    return {
        "minutes": int(bn.size),
        "lag_scan_min": [-UTC_CHECK_MAX_LAG_MIN, UTC_CHECK_MAX_LAG_MIN],
        "all_minutes": {
            "best_lag_min": lag,
            "best_r": round(r, 4) if np.isfinite(r) else r,
            "pairs": npair,
        },
        "top_range_minutes": {
            "n_selected": int(top.sum()),
            "best_lag_min": lag_t,
            "best_r": round(r_t, 4) if np.isfinite(r_t) else r_t,
            "pairs": n_t,
        },
        "note": (
            "lag は「bitFlyer が Binance より何分遅れるか」。JST = UTC+9 なので、"
            "9 時間ずれていれば ±540 分側に出る。**照合であって一次資料ではない。**"
        ),
    }


def run_table(
    mode: str,
    days: list[str],
    root: Path,
    metrics_root: Path,
    out_dir: Path,
    window_hours: float,
    bin_pct: float,
    gap_ms: int,
    seed: int,
    mmr: float | None,
    match_order: str = "table",
    approval: str | None = None,
) -> dict:
    t0 = time.time()
    # **決定 3(10 回目の指摘 1)**: **道具の版と汚れは、出力を 1 バイトも書く前に測る。**
    # **前版は表を書いた後で測っていた。**
    tool = tool_version_block()
    events, dedup_stats = load_binance_cm_liquidations_with_dedup_stats(liq_dir(root))
    cascades = build_cascades(events, EXCHANGE, gap_ms=gap_ms)
    segs = cascade_event_segments(events, cascades)
    print(
        f"清算 一意 {len(events)} 件(生 {dedup_stats.n_in})-> 束 {len(cascades)} 個"
        f"(gap {gap_ms} ms)",
        flush=True,
    )

    def day_of(ts_ms: int) -> str:
        return (
            _dt.datetime.fromtimestamp(ts_ms / 1000, _dt.timezone.utc)
            .date()
            .isoformat()
        )

    want = set(days)
    by_day: dict[str, list[tuple[Cascade, list]]] = {d: [] for d in days}
    for c, seg in zip(cascades, segs):
        d = day_of(c.end_ms)
        if d in want:
            by_day[d].append((c, seg))
    liq_by_day: dict[str, list[int]] = {d: [] for d in days}
    for e in events:
        d = day_of(e.ts_ms)
        if d in want:
            liq_by_day[d].append(e.ts_ms)

    years = sorted({int(d[:4]) for d in days} | {int(shift_day(d, 1)[:4]) for d in days})
    bf = load_bitflyer_minutes(years)

    agg_cache: dict = {}
    metrics_cache: dict = {}
    all_rows: list[dict] = []
    all_mixed: list[dict] = []
    notes: list[dict] = []
    for i_day, day in enumerate(days):
        pairs = by_day[day]
        rows, mixed, note = build_day_rows(
            day,
            root,
            metrics_root,
            [c for c, _ in pairs],
            [s for _, s in pairs],
            sorted(liq_by_day[day]),
            window_hours,
            bin_pct,
            seed,
            mmr,
            agg_cache,
            metrics_cache,
            bf,
            match_order,
        )
        all_rows.extend(rows)
        all_mixed.extend(mixed)
        notes.append(note)
        print(
            f"[{day}] 束 {note['bundles']}(mixed {note['bundles_mixed']} / "
            f"幅 0 {note['bundles_width_zero']})/ 一様 {note['control_uniform_drawn']} / "
            f"合わせた対照 {note['control_matched_made']} -> 主表 {len(rows)} 行",
            flush=True,
        )
        keep = set(
            base.prev_days(day, base.required_prev_days(window_hours))
            + [day, shift_day(day, 1)]
        )
        if i_day + 1 < len(days):
            nd = days[i_day + 1]
            keep |= set(
                base.prev_days(nd, base.required_prev_days(window_hours))
                + [nd, shift_day(nd, 1)]
            )
        for k in list(agg_cache):
            kk = k.replace("__bucket__", "")
            if kk not in keep:
                del agg_cache[k]
        for k in list(metrics_cache):
            if k not in keep:
                del metrics_cache[k]

    cols = sample_columns()
    df = pd.DataFrame(all_rows, columns=cols)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "table.csv", index=False)
    out_names = ["table.csv", "summary.json"]
    if all_mixed:
        pd.DataFrame(all_mixed, columns=cols).to_csv(
            out_dir / "table_mixed.csv", index=False
        )
        out_names.append("table_mixed.csv")

    utc = utc_check_block(days, root, bf, agg_cache)
    summary = build_table_summary(
        df, all_mixed, notes, utc, dedup_stats, time.time() - t0,
        {
            "mode": mode,
            "days": days,
            "window_hours": window_hours,
            "bin_pct": bin_pct,
            "gap_ms": gap_ms,
            "granularity": "trades(反応・到達)/ 60 秒バーは使っていない",
            "horizons_min": list(HORIZONS_MIN),
            "staleness_ms": STALENESS_MS,
            "seed": seed,
            "mmr": mmr,
            "side_price": "same",
            "control_gap_minutes": CONTROL_GAP_MS / 60000,
            "match_tolerance_pct": MATCH_TOL_PCT,
            "match_order": match_order,
            # 走行に渡した承認の番号(prereg 監査(6 回目)の指摘 2。読みの側が
            # 事前登録 §14.4 の欄と突き合わせる)。
            "approval": approval,
            "data_root": str(root),
            "metrics_root": str(metrics_root),
            "bitflyer_dir": str(BITFLYER_DIR),
            "design": "docs/PHASE2/O3C/PRICE_LEVEL/REACTION_DESIGN_2026-09-18.md",
        },
        tool=tool,
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    base.write_md5sums(out_dir, out_names)
    return summary


def build_table_summary(
    df: pd.DataFrame,
    mixed: list[dict],
    notes: list[dict],
    utc: dict,
    dedup_stats,
    elapsed: float,
    params: dict,
    tool: dict | None = None,
) -> dict:
    """`tool` は**出力を書く前に測った**道具の版と汚れ(決定 3。10 回目の指摘 1)。"""
    tool = tool if tool is not None else tool_version_block()

    def block(sub: pd.DataFrame) -> dict:
        out: dict = {"n": int(len(sub))}
        q: dict = {}
        for h in params["horizons_min"]:
            q[f"h{h}m"] = {
                "bp_reactdir": _quant_block(
                    pd.to_numeric(sub[f"bp_{h}m_reactdir"], errors="coerce").to_numpy()
                ),
                "bp_abs": _quant_block(
                    pd.to_numeric(sub[f"bp_{h}m_abs"], errors="coerce").to_numpy()
                ),
                "mfe_reactdir": _quant_block(
                    pd.to_numeric(sub[f"mfe_{h}m_reactdir"], errors="coerce").to_numpy()
                ),
                "mae_reactdir": _quant_block(
                    pd.to_numeric(sub[f"mae_{h}m_reactdir"], errors="coerce").to_numpy()
                ),
                "bf_bp_reactdir": _quant_block(
                    pd.to_numeric(sub[f"bf_bp_{h}m_reactdir"], errors="coerce").to_numpy()
                ),
                "doi_post": _quant_block(
                    pd.to_numeric(sub[f"doi_post_{h}m"], errors="coerce").to_numpy()
                ),
            }
        out["horizons"] = q
        reach: dict = {}
        for t_name in REACH_TARGETS:
            reach[t_name] = {}
            for h in params["horizons_min"]:
                s = pd.to_numeric(sub[f"reach_{t_name}_{h}m"], errors="coerce").dropna()
                reach[t_name][f"h{h}m"] = {
                    "n_defined": int(s.size),
                    "n_reached": int((s == 1).sum()),
                    "rate": (
                        round(float((s == 1).sum()) / s.size, 6) if s.size else None
                    ),
                }
            reach[t_name]["sec"] = _quant_block(
                pd.to_numeric(sub[f"reach_{t_name}_sec"], errors="coerce").to_numpy()
            )
        out["reach"] = reach
        # 設計 §7「位置が作れない行は第 4 の群『作れない』として件数を出す」。
        out["target_undefined"] = {
            t: int(pd.to_numeric(sub[f"p_tgt_{t}"], errors="coerce").isna().sum())
            for t in REACH_TARGETS
        }
        out["axes"] = {
            c: _quant_block(pd.to_numeric(sub[c], errors="coerce").to_numpy())
            for c in (
                "bin_pct",
                "dist_node_bp",
                "dist_vwap_bp",
                "dist_node_bp_liqdir",
                "dist_vwap_bp_liqdir",
                "oi_dist_node_bp_liqdir",
                "oi_dist_vwap_bp_liqdir",
                "oi_side_dist_node_bp_liqdir",
                "oi_side_dist_vwap_bp_liqdir",
                "implied_leverage",
                "implied_leverage_side",
                "bundle_n_events_dedup",
                "bundle_total_qty_accum",
                "doi_pre_1h",
                "doi_pre_4h",
                "doi_in",
                "anchor_lag_ms",
                "anchor_price_diff_bp",
            )
            if c in sub.columns
        }
        out["ratios"] = {
            f"m_{c}": _quant_block(
                pd.to_numeric(sub[f"m_{c}"], errors="coerce").to_numpy()
            )
            for c in RATIO_COLUMNS
        }
        out["bf_xcorr_best_lag_min"] = _quant_block(
            pd.to_numeric(sub["bf_xcorr_best_lag_min"], errors="coerce").to_numpy()
        )
        out["oi_covered"] = int(
            pd.to_numeric(sub["oi_covered"], errors="coerce").fillna(0).sum()
        )
        return out

    kinds = [KIND_LIQ, KIND_UNIFORM, KIND_MATCHED]
    summary = {
        "params": params,
        # **決定 16(8 回目の指摘 16)+ 決定 3(10 回目の指摘 3)**: 走行の道具の版を
        # 出力に残す(**`git log -1 --format=%H -- <道具 2 ファイル>`**。取れなければ「不明」)。
        # **params には入れない**(読みの側の `params` の検査の鍵の数を変えないため)。
        "tool_commit": tool["tool_commit"],
        # **決定 3・15(9 回目)+ 決定 1・2・3(10 回目)**: 道具の 2 ファイルが
        # 汚れていたか。**読みの側はこれを見て「6 本とも汚れていない」を確かめる。**
        # **出力を書く前に測った値である。**
        "tool_dirty": tool["tool_dirty"],
        "elapsed_sec": round(elapsed, 2),
        "liq_rows_raw": dedup_stats.n_in,
        "liq_rows_unique": dedup_stats.n_out,
        "rows_total": int(len(df)),
        "rows_by_kind": {k: int((df["kind"] == k).sum()) for k in kinds},
        "rows_mixed_excluded": len(mixed),
        "mixed_cascade_ids": [r["cascade_id"] for r in mixed],
        "side_counts": {
            str(k): int(v)
            for k, v in df[df["kind"] == KIND_LIQ]["side"].value_counts().items()
        },
        "by_kind": {k: block(df[df["kind"] == k]) for k in kinds},
        "by_side": {
            str(s): block(df[(df["kind"] == KIND_LIQ) & (df["side"] == s)])
            for s in sorted(df[df["kind"] == KIND_LIQ]["side"].dropna().unique())
        },
        "utc_check": utc,
        "per_day": notes,
        "notes": [
            "観測表のみ。判定(予測できる / 使える / 有効)は書いていない。バーも置いていない。",
            "*_liqdir は o3c_oi_distance.LIQ_SIGN(SELL=+1 / BUY=−1)のまま。"
            "*_reactdir は設計 §3 の「SELL 清算は下向きが正」に従う REACT_SIGN"
            "(SELL=−1 / BUY=+1)。**符号が逆なので別の列名にしてある。**",
            "束の直前 W のプロファイル(profile_ts_ms = 束の開始 start_ms)と、"
            "反応の起点(anchor = after_shift(end_ms))は別の時刻である。",
            "doi_pre_1h / doi_pre_4h は (start−窓, start] の ΔOI、doi_in は (start, end] の ΔOI。"
            "**どれも起点(anchor)より後の metrics 行を読まない。**"
            "幅 0 の束では doi_in の桶が 0 個になり NaN(0 を入れて「変化なし」に見せない)。",
            "doi_post_* は起点より後を読む = 結果の側の量。分ける条件に使わない(設計 §4)。",
            "対照 (i) control_uniform = 同じ日の一様、(ii) control_matched = bin_pct を "
            "±5 ポイントで合わせた同日・置換なし。作れなかった束の件数と bin_pct の分位は "
            "per_day に出している。",
            "mixed の束は主表から外し、件数と id をここに残して table_mixed.csv に書いている。",
            "bundle_total_qty_accum は accumulated_fill_quantity の合計。"
            "EXT の bundle_total_qty は original_quantity の合計で、**別の列である。**",
            "bitFlyer 1 分足の null は NaN のまま(前値で埋めていない)。",
        ],
    }
    return summary


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("anchor", "sample", "full"), required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument(
        "--days", default=None,
        help="日(カンマ区切り)。sample は既定で標本 6 日。"
             "--mode full には渡せない(日は judgment_days に固定 = 8 回目の指摘 6)",
    )
    ap.add_argument("--gap-sec", type=int, default=DEFAULT_GAP_SEC)
    ap.add_argument("--window-hours", type=float, default=8.0)
    ap.add_argument("--bin-pct", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument(
        "--mmr",
        type=float,
        default=None,
        help="維持証拠金率(小数)。渡したときだけ implied_leverage を出す",
    )
    ap.add_argument("--data-root", default=str(base.DEFAULT_DATA_ROOT))
    ap.add_argument("--metrics-root", default=str(oid.DEFAULT_METRICS_ROOT))
    ap.add_argument(
        "--granularity",
        choices=("bar60", "trades"),
        default="bar60",
        help="--mode anchor のときだけ効く。bar60 = 60 秒バー / trades = 約定そのまま",
    )
    ap.add_argument(
        "--match-order",
        choices=("table", "reversed"),
        default="table",
        help="対照 (ii) のマッチングに束を渡す順。reversed は順序依存を実測するための経路"
        "(2026-09-18 の監査の指摘 21)。既定 table が本走行の順",
    )
    ap.add_argument(
        "--approval",
        default=None,
        help="--mode full は必須。--mode sample も標本 6 日の外を開けるなら必須"
        "(docs/OWNER_LOG.md に行頭 `| L-NNN |` が要る)。"
        "--mode full では事前登録 §14.4 の欄「応答の L 番号」と一致し、L-199 より後で、"
        "--out-dir が §14.1・§14.2 の 6 つのどれかで、まだ存在しないことも要る",
    )
    a = ap.parse_args(argv)

    root = Path(a.data_root)
    metrics_root = Path(a.metrics_root)
    out_dir = Path(a.out_dir)
    gap_ms = int(a.gap_sec) * 1000

    # 日を先に決めてから関門に掛ける(2026-09-18 の監査の指摘 3。
    # 前版は days を渡さずに呼んでいたので `--mode sample --days <判定区間の日>` が素通りした)。
    # **決定 6(8 回目の指摘 6)**: `--mode full` は `--days` を受け付けない。
    # **日の決め方より先に関門へ渡す**(関門の (f) が止める)。
    if a.mode == "full":
        days = judgment_days(root)
        # 判定区間 = 標本 6 日と 12 日走行の 10 日を除いた 456 日
        # (指摘 4 / 指摘 2・14 / 返答 060 の #1)。**`--days` では上書きできない。**
    elif a.days:
        days = [d.strip() for d in a.days.split(",") if d.strip()]
    elif a.mode == "sample":
        days = list(SAMPLE_DAYS)
    else:
        days = None

    check_approval(a.mode, a.approval, days=days, out_dir=out_dir,
                   data_root=root, days_given=bool(a.days))
    if a.mode == "full":
        # **決定 2(8 回目の指摘 2)**: 開けた出力先を台帳に残す(出力を書く前に)。
        record_opened(out_dir, a.approval)

    if a.mode == "anchor":
        s = run_anchor(root, out_dir, gap_ms, days, granularity=a.granularity)
        print(
            f"束 {s['bundles']}(非タイ {s['tie_counts']['after_shift']['non_tie']}"
            f" / 両側とも非タイ "
            f"{s['tie_counts']['crosstab_after_shift_x_before']['both_non_tie']})"
            f" / 粒度 {s['params']['granularity']}"
            f" / 生の bp_h 列 {'あり' if s['params']['raw_bp_columns_emitted'] else 'なし'}"
            f" / 所要 {s['elapsed_sec']} 秒 -> {out_dir}"
        )
        return 0

    s = run_table(
        a.mode,
        days,
        root,
        metrics_root,
        out_dir,
        a.window_hours,
        a.bin_pct,
        gap_ms,
        a.seed,
        a.mmr,
        a.match_order,
        approval=a.approval,
    )
    print(
        f"行 {s['rows_total']}("
        + " / ".join(f"{k} {v}" for k, v in s["rows_by_kind"].items())
        + f")/ mixed 除外 {s['rows_mixed_excluded']}"
        f" / W = {a.window_hours}h / gap = {a.gap_sec}s"
        f" / 所要 {s['elapsed_sec']} 秒 -> {out_dir}"
    )
    if a.mode == "full":
        # **決定 1(9 回目の指摘 1)**: 最後まで終わった回だけ `done` を足す。
        # **落ちた回は `started` のまま残り、再走行は (g) で止まる。**
        record_done(out_dir, a.approval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
