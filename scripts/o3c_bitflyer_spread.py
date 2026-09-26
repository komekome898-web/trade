#!/usr/bin/env python3
"""bitFlyer FX_BTC_JPY の**実効スプレッド**(費用 c の材料)を標本日ごとに測る道具
(2026-09-21)。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md` §4・Q5
委任文: `docs/DATA/delegations/20260921_o3c_signal_value_prompt.md`【作るもの】1 の費用

**この道具がすること**
  - 入力は tardis 形式の bitFlyer 約定(向き付き)
    `data/tardis/bitflyer_FX_BTC_JPY_trades/FX_BTC_JPY_YYYYMM01.csv.gz`(16 標本日、
    **gitignore 域**)。列は `exchange,symbol,timestamp,local_timestamp,id,side,
    price,amount`(`timestamp` は取引所時刻のマイクロ秒)。
  - **実効スプレッド** = 1 秒以内に隣り合う買い約定と売り約定の価格差 ÷ 中値(bp)。
    「隣り合う」= 時刻順に並べた約定列で**連続する 2 件**(i, i+1)のうち向きが違い、
    時刻差が 1 秒以内のもの。生の値は (買いの値段 − 売りの値段) ÷ 中値 × 1e4(符号付き。
    相場が動いている間は負にもなる)。
  - **主の分位は絶対値で取る**(反証者レビュー9 D-1、リードの決定 2026-09-21)。
    板を叩いて払う費用は向きに依らず正なので、符号付きの中央値は費用を小さく見せる
    (実測: 符号付き 1.7869 / 絶対値 1.9176 / 正の対だけ 2.2574)。
    符号付きの中央値と正の対だけの中央値は**参考列**として同じ表に残す。
  - 標本日ごとに分布(p25 / p50 / p75 / p90、対の数)を **2 通り**で出す:
    (i) 全時刻、(ii) Binance の清算の直後(t₀ + 1〜5 秒)。
    **「清算直後」は、窓内に清算が複数あっても各清算の [t₀+1, t₀+5] に入る全部の対を取る**
    (反証者レビュー9 D-2。直前 1 件だけを見ると、より新しい清算から 1 秒未満の対 = 清算の
    直後の最も荒い瞬間が落ちる)。
  - 清算の時刻は `rows_continue.csv.gz` の `ts_ms` **だけ**を読む
    (`usecols=["kind","day","half","ts_ms"]`。ラベル・価格・材料の列は読まない。
    後半の標本日についても同じで、読むのは時刻だけ)。
  - 主の c = 清算直後の 16 日プールの**絶対値の中央値**、絶対値の p75 を併記。

**生データは `data/`(gitignore 域)から読むだけで、リポジトリに入れるのは
標本日 × 分位の集計表だけ**(Tardis 利用規約 9.2、設計 §4)。

**探索段なので判定語を 1 つも書かない。`paper_logs/` は開かない。**
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parent
NAN = float("nan")

_spec_cont = importlib.util.spec_from_file_location(
    "o3c_signal_continue", _HERE / "o3c_signal_continue.py")
cont = importlib.util.module_from_spec(_spec_cont)
assert _spec_cont.loader is not None
_spec_cont.loader.exec_module(cont)

check_no_banned = cont.check_no_banned
quantiles = cont.quantiles
md5_of = cont.md5_of
write_csv = cont.write_csv
md_table = cont.md_table
normalize_rows = cont.normalize_rows

# ---------------------------------------------------------------------------
# 固定値(設計 §4。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
TARDIS_DIR = REPO_ROOT / "data" / "tardis" / "bitflyer_FX_BTC_JPY_trades"
ROWS_CONTINUE = (REPO_ROOT / "backtest_data" / "o3c_signal_continue_20260920"
                 / "rows_continue.csv.gz")
DEFAULT_OUT = (REPO_ROOT / "backtest_data" / "o3c_signal_value_20260921" / "spread")

PAIR_MAX_GAP_MS = 1_000        # 「1 秒以内に隣り合う」
POST_LIQ_LO_MS = 1_000         # 清算の直後 t₀ + 1 秒
POST_LIQ_HI_MS = 5_000         # 〜 t₀ + 5 秒
QUANTILES = (25, 50, 75, 90)
SCOPE_ALL = "全時刻"
SCOPE_POST_LIQ = "清算直後(t0+1〜5秒)"
POOL_LABEL = "(標本日プール)"


# ===========================================================================
# 1. 標本日の約定(向き付き)
# ===========================================================================
def sample_day_paths(tardis_dir: Path = TARDIS_DIR) -> list:
    """`FX_BTC_JPY_YYYYMMDD.csv.gz` を日付順に並べて返す。"""
    return sorted(Path(tardis_dir).glob("FX_BTC_JPY_*.csv.gz"))


def day_of_path(path: Path) -> str:
    stem = path.name.replace("FX_BTC_JPY_", "").replace(".csv.gz", "")
    return f"{stem[0:4]}-{stem[4:6]}-{stem[6:8]}"


def load_tardis_day(path: Path) -> tuple:
    """(時刻 ms, 値段, 向き符号)。向きは buy = +1 / sell = −1。`unknown` の行は落とす
    (向きが無いと買い約定と売り約定の対が作れないため。設計に無い判断 → 報告に記す)。"""
    df = pd.read_csv(path, usecols=["timestamp", "side", "price"])
    side = df["side"].astype(str).to_numpy()
    keep = (side == "buy") | (side == "sell")
    t_us = df["timestamp"].to_numpy(np.int64)[keep]
    price = df["price"].to_numpy(float)[keep]
    sgn = np.where(side[keep] == "buy", 1, -1).astype(np.int8)
    order = np.argsort(t_us, kind="stable")
    t_ms = (t_us[order] // 1000).astype(np.int64)
    return t_ms, price[order], sgn[order]


# ===========================================================================
# 2. 実効スプレッドの対(1 秒以内に隣り合う買いと売り)
# ===========================================================================
def effective_spread_pairs(t_ms: np.ndarray, price: np.ndarray, sgn: np.ndarray,
                           max_gap_ms: int = PAIR_MAX_GAP_MS) -> tuple:
    """時刻順の約定列から、連続する 2 件で向きが違い時刻差が `max_gap_ms` 以内の対を
    すべて取り、(対の開始時刻 ms, 実効スプレッド bp) を返す。

    実効スプレッド = (買いの値段 − 売りの値段) ÷ 中値 × 1e4(符号付き)。"""
    t_ms = np.asarray(t_ms, dtype=np.int64)
    price = np.asarray(price, dtype=float)
    sgn = np.asarray(sgn)
    if t_ms.size < 2:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    gap = t_ms[1:] - t_ms[:-1]
    opp = sgn[1:] != sgn[:-1]
    ok = opp & (gap >= 0) & (gap <= max_gap_ms)
    i = np.nonzero(ok)[0]
    if i.size == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    p0, p1 = price[i], price[i + 1]
    s0 = sgn[i]
    p_buy = np.where(s0 > 0, p0, p1)
    p_sell = np.where(s0 > 0, p1, p0)
    mid = (p_buy + p_sell) / 2.0
    good = mid > 0
    return t_ms[i][good], ((p_buy - p_sell) / mid * 1e4)[good]


def mask_post_liquidation(pair_ts: np.ndarray, liq_ts: np.ndarray,
                          lo_ms: int = POST_LIQ_LO_MS,
                          hi_ms: int = POST_LIQ_HI_MS) -> np.ndarray:
    """対の開始時刻が、**どれかの**清算 t₀ の [t₀+lo, t₀+hi] に入るか。

    反証者レビュー9 D-2 の直し: 直前の清算 1 件だけを見る実装だと、清算が 1 秒以内に
    続くとき(連鎖)に、前の清算の窓に入る対でもより新しい清算からの差が lo 未満だと
    落ちていた(全体の 26%)。ここでは
    `t₀ ∈ [pair_ts − hi, pair_ts − lo]` を満たす清算が 1 件でもあるかを数える。"""
    pair_ts = np.asarray(pair_ts, dtype=np.int64)
    liq_ts = np.asarray(liq_ts, dtype=np.int64)
    if pair_ts.size == 0 or liq_ts.size == 0:
        return np.zeros(pair_ts.size, dtype=bool)
    liq = np.sort(liq_ts)
    lo_edge = np.searchsorted(liq, pair_ts - hi_ms, side="left")
    hi_edge = np.searchsorted(liq, pair_ts - lo_ms, side="right")
    return hi_edge > lo_edge


# ===========================================================================
# 3. 清算の時刻(`ts_ms` だけを読む)
# ===========================================================================
def liquidation_ts_by_day(rows_continue: Path = ROWS_CONTINUE) -> tuple:
    """`rows_continue.csv.gz` から `kind == "print"` の (day -> ts_ms の配列)。
    **読む列は `kind` / `day` / `half` / `ts_ms` の 4 本だけ**(ラベル・価格・材料は
    読まない)。`half` は表に載せる内訳のためだけに読む。"""
    df = pd.read_csv(rows_continue, usecols=["kind", "day", "half", "ts_ms"],
                     low_memory=False)
    df = df[df["kind"] == "print"]
    out, halves = {}, {}
    for day, g in df.groupby("day", sort=True):
        out[str(day)] = np.sort(g["ts_ms"].to_numpy(np.int64))
        halves[str(day)] = sorted(set(g["half"].astype(str)))
    return out, halves


# ===========================================================================
# 4. 表
# ===========================================================================
def _dist_row(day: str, scope: str, vals: np.ndarray, half_label: str) -> dict:
    """主の分位は**絶対値**(D-1)。符号付きと正の対だけの中央値は参考列。"""
    vals = np.asarray(vals, dtype=float)
    av = np.abs(vals)
    pos = vals[vals > 0]
    q = quantiles(av, list(QUANTILES)) if av.size else [NAN] * len(QUANTILES)
    qs = quantiles(vals, [50]) if vals.size else [NAN]
    qp = quantiles(pos, [50]) if pos.size else [NAN]
    return {"標本日": day, "半期": half_label, "区分": scope, "対の数": int(vals.size),
            "p25_bp": q[0], "p50_bp": q[1], "p75_bp": q[2], "p90_bp": q[3],
            "参考_符号付きp50_bp": qs[0], "参考_正の対だけp50_bp": qp[0],
            "負の対の割合": (float(np.mean(vals < 0)) if vals.size else NAN)}


def build_spread_table(out_dir: Path = DEFAULT_OUT, tardis_dir: Path = TARDIS_DIR,
                       rows_continue: Path = ROWS_CONTINUE) -> dict:
    """標本日ごとの実効スプレッドの表を作り、`spread_by_day.csv` に書く。
    戻り値に主の c(清算直後のプールの中央値)と p75 を入れる。"""
    t_start = time.time()
    liq_by_day, halves_by_day = liquidation_ts_by_day(rows_continue)
    paths = sample_day_paths(tardis_dir)
    if not paths:
        raise SystemExit(f"[止め] 標本日の約定が無い: {tardis_dir}")

    rows = []
    pool_all, pool_post = [], []
    n_rows_read = {}
    for p in paths:
        day = day_of_path(p)
        t_ms, price, sgn = load_tardis_day(p)
        n_rows_read[day] = int(t_ms.size)
        pair_ts, spread_bp = effective_spread_pairs(t_ms, price, sgn)
        liq = liq_by_day.get(day, np.zeros(0, dtype=np.int64))
        half_label = "/".join(halves_by_day.get(day, [])) or "(清算なし)"
        m_post = mask_post_liquidation(pair_ts, liq)
        rows.append(_dist_row(day, SCOPE_ALL, spread_bp, half_label))
        rows.append(_dist_row(day, SCOPE_POST_LIQ, spread_bp[m_post], half_label))
        pool_all.append(spread_bp)
        pool_post.append(spread_bp[m_post])
        print(f"  {day}: 約定 {t_ms.size} / 対 {pair_ts.size} / 清算直後の対 "
              f"{int(m_post.sum())}(清算 {liq.size} 件)", flush=True)

    all_v = np.concatenate(pool_all) if pool_all else np.zeros(0)
    post_v = np.concatenate(pool_post) if pool_post else np.zeros(0)
    rows.append(_dist_row(POOL_LABEL, SCOPE_ALL, all_v, "前半+後半"))
    rows.append(_dist_row(POOL_LABEL, SCOPE_POST_LIQ, post_v, "前半+後半"))

    qp = (quantiles(np.abs(post_v), list(QUANTILES)) if post_v.size else [NAN] * 4)
    c_main, c_p75 = float(qp[1]), float(qp[2])

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = normalize_rows(rows)
    write_csv(out_dir / "spread_by_day.csv", rows)

    md = ["# bitFlyer FX_BTC_JPY 実効スプレッド(標本日 × 分位、集計だけ)", "",
          "- 設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md` §4・Q5",
          "- 入力(読むだけ): tardis 形式の約定(`data/tardis/`、gitignore 域)と "
          "`rows_continue.csv.gz` の `ts_ms`",
          f"- 対の作り方: 時刻順に連続する 2 件で向きが違い、時刻差 ≤ {PAIR_MAX_GAP_MS} ms。"
          "値 = (買いの値段 − 売りの値段) ÷ 中値 × 1e4",
          "- **p25 / p50 / p75 / p90 は絶対値の分位**(D-1)。符号付きと正の対だけの"
          "中央値は参考列",
          f"- 清算直後 = **どれかの**清算の [t₀+{POST_LIQ_LO_MS} ms, t₀+{POST_LIQ_HI_MS} ms] "
          "に入る対(D-2)",
          f"- 主の c(清算直後のプールの絶対値の中央値) = {c_main:.4f} bp / "
          f"絶対値の p75 = {c_p75:.4f} bp", "",
          md_table(rows), ""]
    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "spread/tables.md")
    (out_dir / "tables.md").write_text(mdtxt, encoding="utf-8")

    summary = {
        "道具": "scripts/o3c_bitflyer_spread.py",
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md §4・Q5",
        "標本日数": len(paths),
        "標本日": [day_of_path(p) for p in paths],
        "標本日ごとの約定件数(向きが buy/sell の行だけ)": n_rows_read,
        "対の最大の時刻差_ms": PAIR_MAX_GAP_MS,
        "清算直後の窓_ms": [POST_LIQ_LO_MS, POST_LIQ_HI_MS],
        "全時刻の対の数(プール)": int(all_v.size),
        "清算直後の対の数(プール)": int(post_v.size),
        "主のc_清算直後プールの絶対値の中央値_bp": c_main,
        "併記_清算直後プールの絶対値のp75_bp": c_p75,
        "参考_清算直後プールの符号付きの中央値_bp": (
            float(quantiles(post_v, [50])[0]) if post_v.size else NAN),
        "参考_清算直後プールの正の対だけの中央値_bp": (
            float(quantiles(post_v[post_v > 0], [50])[0])
            if post_v[post_v > 0].size else NAN),
        "清算直後の窓の取り方": "どれかの清算の [t0+1s, t0+5s] に入る全部の対(D-2)",
        "分位の取り方": "絶対値(D-1)",
        "生データはリポジトリに入れない": True,
        "読んだ列(rows_continue)": ["kind", "day", "half", "ts_ms"],
        "所要秒": round(time.time() - t_start, 1),
    }
    txt = json.dumps(summary, ensure_ascii=False, indent=2)
    check_no_banned(txt, "spread/summary.json")
    (out_dir / "summary.json").write_text(txt, encoding="utf-8")

    lines = []
    for q in sorted(out_dir.iterdir()):
        if q.name == "MD5SUMS" or q.is_dir():
            continue
        lines.append(f"{md5_of(q)}  {q.name}")
    (out_dir / "MD5SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"c_main": c_main, "c_p75": c_p75, "rows": rows, "summary": summary}


def read_cost(out_dir: Path = DEFAULT_OUT) -> tuple:
    """`spread_by_day.csv` から主の c と p75 を読む(集計表だけを読む)。"""
    path = Path(out_dir) / "spread_by_day.csv"
    if not path.exists():
        raise SystemExit(
            f"[止め] 費用の表が無い: {path}。先に "
            "`PYTHONPATH=src python3 scripts/o3c_bitflyer_spread.py` を実行する")
    df = pd.read_csv(path)
    pool = df[(df["標本日"] == POOL_LABEL) & (df["区分"] == SCOPE_POST_LIQ)]
    if pool.empty:
        raise SystemExit(f"[止め] {path} にプールの行が無い")
    return float(pool["p50_bp"].iloc[0]), float(pool["p75_bp"].iloc[0])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="bitFlyer 実効スプレッド(標本日)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tardis-dir", type=Path, default=TARDIS_DIR)
    a = ap.parse_args(argv)
    res = build_spread_table(a.out, a.tardis_dir)
    print(json.dumps({"主のc_bp": res["c_main"], "p75_bp": res["c_p75"],
                      "行数": len(res["rows"])}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
