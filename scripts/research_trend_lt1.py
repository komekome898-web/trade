"""LT1 — 長期トレンド(現物ロング/フラット)の B&H 超え判定。read-only / 冪等 / seed 20260828。

================================ 事前登録(逐語転記)================================
docs/PREREG_trend_lt1.md — 凍結日 2026-08-28。以降の変更は「事前登録の破棄」。

# PREREG — LT1 長期トレンド(現物ロング/フラット、B&H超え判定)

**凍結日: 2026-08-28。以降の変更は「事前登録の破棄」。**
オーナー指示: 「できるだけ長期のバックテストで、buy&hold の期待値を超えるものが条件」。

## 0. 位置づけ

本登録は分〜秒スケールのアルファ抽出(全線閉鎖済み、第22〜33報)とは別クラスの
**リスクプレミア収穫**である。主張は「取引所固有の非効率」ではなく
「深い弱気相場を避けることで複利を守る」という数十年文書化された時系列トレンドの機構。
第b報の棄却(2年・単一資産・素朴モメンタム → OOS全負 = 丸暗記)との差別化は、
(a) 10年超・複数サイクルのデータ、(b) **主セルをデータではなく文献事前分布から指名**、
(c) 資産横断の再現要求、で行う。

## 1. 執行モデル(凍結)

- 対象: **現物 BTC**(スワップなし。CFD は 0.04%/日 ≈ 年15% で長期保有不可と明記)。
  ロング or フラットのみ(現物のためショートなし)。フラット時は JPY(利息ゼロ)。
- シグナルは日足終値で判定、**翌日終値で執行**(1日の執行ラグ = 保守側)。
- コスト: スイッチ1回あたり **0.20%**(taker 0.15% + スリッページ0.05%、片側)。
- 税・入出金は対象外(戦略比較のスコープ外と明記)。

## 2. 主セルと感度族(選択をしない設計)

- **主セル(文献事前分布・データから選ばない): 200日SMA ロング/フラット**
  (終値 > SMA200 でロング、下回ればフラット)。
- 感度族(全報告・選択不可): 規則 {SMAクロス, TSMOM(N日リターン符号)} ×
  N {100, 200, 365} = 6セル。**台地条件: 6セル中過半がバー(下記①②)を満たすこと** —
  「クラスが効く」ことの要求であり、最良セル選びではない。

## 3. データ

- BTCUSD 日足を**取得可能な最長**(目標2011年〜、Bitstamp 起点)。独立2ソース以上で
  クロスチェックし、接合・欠損・外れ値の処理を明記。BTCJPY への読み替えは行わない
  (為替の寄与はスコープ外と明記。円建て感度は参考出力)。
- 再現用資産: **ETHUSD**(2016年〜)。
- 全データはリポジトリにスナップショット保存(恒久性)。

## 4. 判定基準(オーナーのバーの操作的定義。凍結)

主セルが全期間(最長ウィンドウ)で**すべて**満たすこと:

1. **CAGR ≥ B&H の CAGR**(コスト込み)
2. **maxDD ≤ 0.6 × B&H の maxDD**
3. 期間を半分割した**前半・後半それぞれで Sharpe ≥ B&H の Sharpe**
   (年率化、日次リターン。CAGRの半期比較はサイクル位相に支配されるため
   リスク調整で判定 — この選択自体を先に固定する)
4. **ETH 再現**: 同じ主セル(200日SMA)が ETH 全期間で ①②を満たす
   (満たさない場合、最低限 Sharpe > B&H を要し「部分再現」と格下げ報告)

加えて台地条件(§2)。**判定は一度だけ実行し、そのまま報告**(全データが過去である
ため「新鮮データ」は存在しない — 代わりに (3)(4) の構造的頑健性と、通過時の
2段目 = **今日以降のフォワード追跡**(現物ペーパー、月次評価)を新鮮性の代替とする)。

## 5. 必須報告

1. 主セル+6セル+B&H の全期間表(CAGR・年率ボラ・Sharpe・maxDD・MAR・スイッチ回数・
   コスト総額)と資産曲線
2. サイクル別分解(2011-15 / 15-18 / 18-22 / 22-26 等)— どのサイクルで稼ぎ、
   どこでB&Hに負けるか
3. 直近レジーム(2023-2026)単体の成績 — トレンドプレミアが近年も生きているか
4. コスト・ラグ感度(コスト2倍、ラグ2日)
5. サニティ: ルックアヘッド0(シグナルは前日以前の終値のみ)、データ接合の検証
   (ソース間の日次リターン相関・乖離日数)、決定性
6. 多重性: 6セル+主セル事前指名の構造を明記

## 6. 結果の読み方(先に決める)

| 結果 | 結論 |
|---|---|
| 主セルが①〜④+台地を満たす | **2段目 = 今日からのフォワード追跡**(現物ペーパー、月次レビュー)へ。採用ではない |
| ①②は通るが③(半期)が落ちる | 「サイクル依存」として棄却水準を明記、不採用 |
| 直近レジーム(2023-26)で崩壊 | プレミア消失の証拠として棄却 |
| 感度族だけ通り主セルが落ちる | 掘り出しとして不採用 |

## 7. オーナー承認項目

(1) 本バーの操作的定義(§4 — 特に半期はSharpe比較であること)、
(2) 執行対象が現物であること(CFD不可の理由)、(3) 通過時のフォワード追跡開始。

署名: リード(LT1設計)。実装: `scripts/research_trend_lt1.py`(本文書逐語 docstring、
seed 20260828)。
=====================================================================================

実装上の固定事項(事前登録の運用解釈。実行前に固定):
- 主系列: 資産ごとに「最長履歴のソース」。BTCUSD = Bitstamp(2011-08-22〜)、
  ETHUSD = Coinbase(2016-05-18〜)。接合(スプライス)は行わない — 主系列は単一ソース。
  他ソースはクロスチェック専用。
- 最終バーの扱い: 取得日 2026-08-28 (UTC) は未完了日のため除外。評価終端 2026-08-27。
- 欠損日: 完全な暦日グリッドに reindex し、close を前日値で埋める(N日窓を暦日で
  一致させるため)。埋めた日数は報告する。
- ポジション定義: pos[t] = sig[t-2](sig[s] は s 日終値までの情報のみで決まる)。
  したがって pos[t] は close[<=t-2] のみの関数 = 翌日終値執行。
- コスト計上: pos が変化した日に 0.20% × |Δpos| を日次リターンから減算。
- B&H ベンチマーク: コストゼロ(戦略に対し保守側の厳しいバー)。参考として
  初回エントリに 0.20% を課した版も併記。
- サイクル境界: サイクル安値アンカー 2015-01-14 / 2018-12-15 / 2022-11-21。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260828
REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "backtest_data"
STAMP = "20260828"

COST_PER_SWITCH = 0.0020          # PREREG §1
LAG_DAYS = 1                      # 翌日終値執行 (pos[t] = sig[t-2])
END_DATE = pd.Timestamp("2026-08-27")   # 最終完全 UTC 日
DAYS_PER_YEAR = 365.25

PRIMARY_SOURCE = {"btcusd": "bitstamp", "ethusd": "coinbase"}
ALL_SOURCES = ["bitstamp", "yahoo", "coinbase"]

# 感度族 (PREREG §2) — 列挙固定、後から追加しない
CELLS = [(rule, n) for rule in ("SMA", "TSMOM") for n in (100, 200, 365)]
PRIMARY_CELL = ("SMA", 200)

CYCLES = [
    ("C1 2011-15", None, pd.Timestamp("2015-01-14")),
    ("C2 2015-18", pd.Timestamp("2015-01-15"), pd.Timestamp("2018-12-15")),
    ("C3 2018-22", pd.Timestamp("2018-12-16"), pd.Timestamp("2022-11-21")),
    ("C4 2022-26", pd.Timestamp("2022-11-22"), None),
]

OUT: list[str] = []


def emit(line: str = "") -> None:
    OUT.append(line)
    print(line, flush=True)


# ------------------------------------------------------------------ data ---
def load_raw(sym: str, source: str) -> pd.DataFrame:
    p = DATA / f"daily_{sym}_{source}_{STAMP}.csv.gz"
    d = pd.read_csv(p)
    d["date"] = pd.to_datetime(d["date"])
    d = d[d["date"] <= END_DATE].sort_values("date").reset_index(drop=True)
    return d.set_index("date")


def primary_series(sym: str) -> tuple[pd.Series, dict]:
    """主系列 = 単一ソース。暦日グリッドに reindex して close を前埋め。"""
    src = PRIMARY_SOURCE[sym]
    d = load_raw(sym, src)
    grid = pd.date_range(d.index.min(), d.index.max(), freq="D")
    close = d["close"].reindex(grid)
    n_filled = int(close.isna().sum())
    close = close.ffill()
    info = {
        "source": src,
        "start": str(grid[0].date()),
        "end": str(grid[-1].date()),
        "n_days": len(close),
        "n_filled": n_filled,
        "n_raw_bars": len(d),
        "zero_or_neg_close": int((d["close"] <= 0).sum()),
    }
    return close, info


# --------------------------------------------------------------- signals ---
def signal(close: np.ndarray, rule: str, n: int) -> np.ndarray:
    """sig[s] ∈ {0,1,nan}: s 日終値までの情報のみ。"""
    s = pd.Series(close)
    if rule == "SMA":
        ref = s.rolling(n, min_periods=n).mean()
        sig = (s > ref).astype(float)
        sig[ref.isna()] = np.nan
    elif rule == "TSMOM":
        past = s.shift(n)
        sig = (s / past - 1.0 > 0).astype(float)
        sig[past.isna()] = np.nan
    else:
        raise ValueError(rule)
    return sig.to_numpy()


def positions(close: np.ndarray, rule: str, n: int, lag: int = LAG_DAYS) -> np.ndarray:
    """pos[t] = sig[t-1-lag]。lag=1 → 翌日終値執行 → close[<=t-2] のみに依存。"""
    return pd.Series(signal(close, rule, n)).shift(1 + lag).to_numpy()


# --------------------------------------------------------------- metrics ---
def metrics(daily: np.ndarray, dates: pd.DatetimeIndex) -> dict:
    daily = np.asarray(daily, dtype=float)
    if len(daily) < 2:
        return {k: float("nan") for k in
                ("cagr", "vol", "sharpe", "maxdd", "mar", "total_ret", "n")}
    eq = np.cumprod(1.0 + daily)
    years = (dates[-1] - dates[0]).days / DAYS_PER_YEAR
    cagr = eq[-1] ** (1.0 / years) - 1.0 if years > 0 and eq[-1] > 0 else float("nan")
    sd = daily.std(ddof=1)
    vol = sd * np.sqrt(365.0)
    sharpe = (daily.mean() / sd * np.sqrt(365.0)) if sd > 0 else float("nan")
    peak = np.maximum.accumulate(eq)
    maxdd = float((eq / peak - 1.0).min())
    mar = cagr / abs(maxdd) if maxdd < 0 else float("nan")
    return {"cagr": cagr, "vol": vol, "sharpe": sharpe, "maxdd": maxdd,
            "mar": mar, "total_ret": eq[-1] - 1.0, "n": len(daily), "years": years,
            "equity": eq}


def run_cell(close: pd.Series, rule: str, n: int, cost: float = COST_PER_SWITCH,
             lag: int = LAG_DAYS) -> dict:
    c = close.to_numpy(dtype=float)
    pos = positions(c, rule, n, lag)
    r = np.concatenate([[np.nan], c[1:] / c[:-1] - 1.0])
    valid = ~np.isnan(pos) & ~np.isnan(r)
    first = int(np.argmax(valid)) if valid.any() else len(c)
    idx = close.index[first:]
    p = pos[first:]
    rr = r[first:]
    prev = np.concatenate([[0.0], p[:-1]])   # 開始前はフラット
    switches = np.abs(p - prev)
    strat = p * rr - cost * switches
    bh = rr.copy()
    m_s = metrics(strat, idx)
    m_b = metrics(bh, idx)
    m_s["switches"] = float(switches.sum())
    m_s["switch_per_year"] = m_s["switches"] / m_s["years"]
    m_s["cost_total_pct"] = m_s["switches"] * cost * 100.0
    m_s["time_in_market"] = float(p.mean())
    return {"dates": idx, "strat": strat, "bh": bh, "pos": p,
            "m_strat": m_s, "m_bh": m_b, "rule": rule, "n": n,
            "label": f"{rule}{n}"}


def window(res: dict, lo: pd.Timestamp | None, hi: pd.Timestamp | None) -> dict | None:
    d = res["dates"]
    mask = np.ones(len(d), dtype=bool)
    if lo is not None:
        mask &= (d >= lo)
    if hi is not None:
        mask &= (d <= hi)
    if mask.sum() < 30:
        return None
    return {"m_strat": metrics(res["strat"][mask], d[mask]),
            "m_bh": metrics(res["bh"][mask], d[mask]),
            "n": int(mask.sum())}


def fmt(m: dict) -> str:
    return (f"{m['cagr']*100:8.2f} {m['vol']*100:8.1f} {m['sharpe']:7.3f} "
            f"{m['maxdd']*100:8.1f} {m['mar']:7.3f}")


# ---------------------------------------------------------------- sanity ---
def sanity_lookahead() -> list[str]:
    """pos[t] が close[t-1], close[t] に依存しないこと(= SMA当日を含めない)を assert。"""
    rng = np.random.default_rng(SEED)
    msgs = []
    base = np.exp(np.cumsum(rng.normal(0, 0.04, 2000))) * 100.0
    for rule, n in CELLS:
        p_full = positions(base, rule, n)
        # (a) 末尾撹乱不変性: index t 以降を破壊しても pos[0..t] は不変
        for t in rng.integers(n + 5, 1990, size=8):
            t = int(t)
            pert = base.copy()
            pert[t - 1:] *= rng.uniform(0.5, 2.0, size=len(pert) - (t - 1))
            p_p = positions(pert, rule, n)
            a, b = p_full[: t + 1], p_p[: t + 1]
            ok = np.array_equal(np.nan_to_num(a, nan=-1), np.nan_to_num(b, nan=-1))
            assert ok, f"LOOKAHEAD {rule}{n} at t={t}"
        # (b) 切り詰め不変性
        for k in (int(n * 1.5) + 10, 900, 1500):
            p_t = positions(base[:k], rule, n)
            a, b = p_full[:k], p_t
            assert np.array_equal(np.nan_to_num(a, nan=-1), np.nan_to_num(b, nan=-1)), \
                f"TRUNC {rule}{n} k={k}"
        msgs.append(f"  {rule}{n}: 末尾撹乱不変(8点) + 切り詰め不変(3点) PASS")
    # (c) 明示 assert: SMA 当日を含めない
    c = np.arange(1.0, 400.0)
    sig = signal(c, "SMA", 200)
    pos = positions(c, "SMA", 200)
    assert np.isnan(sig[198]) and not np.isnan(sig[199]), "SMA warmup boundary"
    assert np.isnan(pos[200]) and not np.isnan(pos[201]), "pos lag = 2 days"
    msgs.append("  SMA200: sig は index199 で初出(200点必要)、pos は index201 で初出"
                "(= 2日遅れ)を assert PASS")
    return msgs


def cross_check(sym: str) -> list[str]:
    lines = []
    series = {}
    for s in ALL_SOURCES:
        p = DATA / f"daily_{sym}_{s}_{STAMP}.csv.gz"
        if p.exists():
            series[s] = load_raw(sym, s)["close"]
    keys = sorted(series)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = series[keys[i]], series[keys[j]]
            common = a.index.intersection(b.index)
            if len(common) < 100:
                continue
            aa, bb = a.loc[common].sort_index(), b.loc[common].sort_index()
            both = pd.concat([aa.pct_change(), bb.pct_change()], axis=1).dropna()
            corr = float(both.iloc[:, 0].corr(both.iloc[:, 1]))
            dev = (aa / bb - 1.0).abs()
            n2 = int((dev > 0.02).sum())
            lines.append(f"  {keys[i]:9s} vs {keys[j]:9s} "
                         f"overlap={len(common):5d}d  日次リターン相関={corr:.6f}  "
                         f"|Δclose|>2% の日数={n2} ({n2/len(common)*100:.2f}%)  "
                         f"中央値|Δ|={float(dev.median())*100:.3f}%")
    return lines


# ------------------------------------------------------------------ main ---
def analyse() -> dict:
    digest: dict = {}

    emit("=" * 96)
    emit("LT1 — 長期トレンド(現物ロング/フラット)の B&H 超え判定")
    emit(f"seed={SEED}  コスト={COST_PER_SWITCH*100:.2f}%/スイッチ  "
         f"執行=翌日終値(pos[t]=sig[t-2])  評価終端={END_DATE.date()}")
    emit("=" * 96)

    # ---------------- データ
    emit("\n## 0. データ")
    infos = {}
    closes = {}
    for sym in ("btcusd", "ethusd"):
        close, info = primary_series(sym)
        closes[sym], infos[sym] = close, info
        emit(f"[{sym}] 主系列={info['source']} {info['start']}..{info['end']} "
             f"暦日={info['n_days']} 生バー={info['n_raw_bars']} "
             f"前埋め欠損日={info['n_filled']} close<=0={info['zero_or_neg_close']} "
             f"年数={(pd.Timestamp(info['end'])-pd.Timestamp(info['start'])).days/DAYS_PER_YEAR:.2f}")
    digest["data"] = infos

    emit("\n### ソース間クロスチェック(BTCUSD)")
    for ln in cross_check("btcusd"):
        emit(ln)
    emit("### ソース間クロスチェック(ETHUSD)")
    for ln in cross_check("ethusd"):
        emit(ln)

    # ---------------- サニティ: ルックアヘッド
    emit("\n## 1. サニティ — ルックアヘッド 0")
    for ln in sanity_lookahead():
        emit(ln)

    # ---------------- 全期間表
    results = {}
    for sym in ("btcusd", "ethusd"):
        results[sym] = {f"{r}{n}": run_cell(closes[sym], r, n) for r, n in CELLS}

    for sym in ("btcusd", "ethusd"):
        emit(f"\n## 2. 全期間表 [{sym}] (主系列 {infos[sym]['source']})")
        emit(f"{'セル':14s} {'開始':11s} {'CAGR%':>8s} {'ボラ%':>8s} {'Sharpe':>7s} "
             f"{'maxDD%':>8s} {'MAR':>7s} {'sw/年':>7s} {'コスト%':>8s} {'在市%':>6s}")
        for lbl in [f"{r}{n}" for r, n in CELLS]:
            res = results[sym][lbl]
            m = res["m_strat"]
            star = " *主" if (res["rule"], res["n"]) == PRIMARY_CELL else ""
            emit(f"{lbl+star:14s} {str(res['dates'][0].date()):11s} {fmt(m)} "
                 f"{m['switch_per_year']:7.2f} {m['cost_total_pct']:8.1f} "
                 f"{m['time_in_market']*100:6.1f}")
        # B&H は主セル窓で
        pres = results[sym][f"{PRIMARY_CELL[0]}{PRIMARY_CELL[1]}"]
        emit(f"{'B&H(主セル窓)':14s} {str(pres['dates'][0].date()):11s} "
             f"{fmt(pres['m_bh'])} {0.0:7.2f} {0.0:8.1f} {100.0:6.1f}")
        emit(f"  注: 各セルの B&H は同一窓で別途比較する(下記判定表)。"
             f"主セル窓 B&H 終値倍率 = {pres['m_bh']['equity'][-1]:,.1f}x, "
             f"主セル戦略 = {pres['m_strat']['equity'][-1]:,.1f}x")

    # ---------------- 資産曲線の数値要約
    emit("\n## 3. 資産曲線の数値要約(対数節目 / 年末倍率)[btcusd 主セル SMA200]")
    pres = results["btcusd"]["SMA200"]
    d = pres["dates"]
    for name, eq in (("戦略", pres["m_strat"]["equity"]), ("B&H", pres["m_bh"]["equity"])):
        hits = []
        for mult in (10, 100, 1_000, 10_000):
            k = np.argmax(eq >= mult)
            hits.append(f"{mult}x={str(d[k].date()) if eq.max() >= mult else '未達'}")
        emit(f"  {name}: 終端={eq[-1]:,.1f}x  最大={eq.max():,.1f}x  " + "  ".join(hits))
    emit(f"  {'年':6s} {'戦略(倍)':>12s} {'B&H(倍)':>12s} {'戦略年率%':>10s} {'B&H年率%':>10s} {'在市%':>7s}")
    df = pd.DataFrame({"strat": pres["strat"], "bh": pres["bh"], "pos": pres["pos"]}, index=d)
    for y, g in df.groupby(df.index.year):
        es = float(np.prod(1 + g["strat"].to_numpy()))
        eb = float(np.prod(1 + g["bh"].to_numpy()))
        eqs = float(np.prod(1 + df.loc[df.index.year <= y, "strat"].to_numpy()))
        eqb = float(np.prod(1 + df.loc[df.index.year <= y, "bh"].to_numpy()))
        emit(f"  {y:<6d} {eqs:12,.2f} {eqb:12,.2f} {(es-1)*100:10.1f} {(eb-1)*100:10.1f} "
             f"{g['pos'].mean()*100:7.1f}")

    # ---------------- サイクル別
    emit("\n## 4. サイクル別分解 [btcusd 主セル SMA200](安値アンカー)")
    emit(f"  {'区間':14s} {'日数':>6s} | {'戦CAGR%':>9s} {'戦Shp':>7s} {'戦DD%':>8s} | "
         f"{'BHCAGR%':>9s} {'BHShp':>7s} {'BHDD%':>8s} | {'総リタ戦%':>10s} {'総リタBH%':>10s}")
    for name, lo, hi in CYCLES:
        w = window(pres, lo, hi)
        if w is None:
            emit(f"  {name:14s} データ不足")
            continue
        a, b = w["m_strat"], w["m_bh"]
        emit(f"  {name:14s} {w['n']:6d} | {a['cagr']*100:9.1f} {a['sharpe']:7.3f} "
             f"{a['maxdd']*100:8.1f} | {b['cagr']*100:9.1f} {b['sharpe']:7.3f} "
             f"{b['maxdd']*100:8.1f} | {a['total_ret']*100:10.1f} {b['total_ret']*100:10.1f}")

    # ---------------- 直近レジーム
    emit("\n## 5. 直近レジーム 2023-01-01 .. 2026-08-27 単体(プレミア存続の検定)")
    for sym in ("btcusd", "ethusd"):
        for lbl in [f"{r}{n}" for r, n in CELLS]:
            w = window(results[sym][lbl], pd.Timestamp("2023-01-01"), None)
            if w is None:
                continue
            a, b = w["m_strat"], w["m_bh"]
            mark = " *主" if lbl == "SMA200" else ""
            emit(f"  [{sym}] {lbl+mark:10s} 戦: CAGR {a['cagr']*100:7.1f}% Shp {a['sharpe']:6.3f} "
                 f"DD {a['maxdd']*100:6.1f}%  |  B&H: CAGR {b['cagr']*100:7.1f}% "
                 f"Shp {b['sharpe']:6.3f} DD {b['maxdd']*100:6.1f}%")

    # ---------------- 感度
    emit("\n## 6. 感度(コスト2倍 0.40%/スイッチ、執行ラグ2日)")
    emit(f"  {'資産/セル':20s} {'条件':16s} {'CAGR%':>8s} {'Sharpe':>7s} {'maxDD%':>8s} "
         f"{'MAR':>7s} {'vs B&H CAGR':>12s}")
    for sym in ("btcusd", "ethusd"):
        for lbl, (r, n) in [(f"{r}{n}", (r, n)) for r, n in CELLS]:
            for cname, kw in (("基準", {}),
                              ("コスト2倍", {"cost": 2 * COST_PER_SWITCH}),
                              ("ラグ2日", {"lag": 2})):
                res = run_cell(closes[sym], r, n, **kw)
                a, b = res["m_strat"], res["m_bh"]
                emit(f"  {sym+'/'+lbl:20s} {cname:16s} {a['cagr']*100:8.2f} "
                     f"{a['sharpe']:7.3f} {a['maxdd']*100:8.1f} {a['mar']:7.3f} "
                     f"{(a['cagr']-b['cagr'])*100:+12.2f}")

    # ---------------- 半期(判定③)
    emit("\n## 7. 半期分割 Sharpe(判定③)")
    halves = {}
    for sym in ("btcusd", "ethusd"):
        for lbl in [f"{r}{n}" for r, n in CELLS]:
            res = results[sym][lbl]
            mid = len(res["dates"]) // 2
            h = []
            for tag, sl in (("前半", slice(0, mid)), ("後半", slice(mid, None))):
                dd = res["dates"][sl]
                a = metrics(res["strat"][sl], dd)
                b = metrics(res["bh"][sl], dd)
                h.append((tag, dd[0].date(), dd[-1].date(), a["sharpe"], b["sharpe"]))
            halves[(sym, lbl)] = h
            if lbl == "SMA200":
                for tag, d0, d1, sa, sb in h:
                    emit(f"  [{sym}] {lbl} {tag} {d0}..{d1}  戦Sharpe={sa:.4f}  "
                         f"B&H Sharpe={sb:.4f}  {'PASS' if sa >= sb else 'FAIL'}")

    # ---------------- 判定表
    emit("\n## 8. 判定表(PREREG §4 逐語)")
    pb = results["btcusd"]["SMA200"]
    a, b = pb["m_strat"], pb["m_bh"]
    c1 = a["cagr"] >= b["cagr"]
    c2 = a["maxdd"] >= 0.6 * b["maxdd"]      # maxdd は負値。|DD_s| <= 0.6|DD_b|
    hb = halves[("btcusd", "SMA200")]
    c3 = all(sa >= sb for _, _, _, sa, sb in hb)
    pe = results["ethusd"]["SMA200"]
    ea, eb = pe["m_strat"], pe["m_bh"]
    e1 = ea["cagr"] >= eb["cagr"]
    e2 = ea["maxdd"] >= 0.6 * eb["maxdd"]
    e_sharpe = ea["sharpe"] > eb["sharpe"]
    c4 = e1 and e2
    plateau_hits = []
    for lbl in [f"{r}{n}" for r, n in CELLS]:
        rs = results["btcusd"][lbl]
        ok1 = rs["m_strat"]["cagr"] >= rs["m_bh"]["cagr"]
        ok2 = rs["m_strat"]["maxdd"] >= 0.6 * rs["m_bh"]["maxdd"]
        plateau_hits.append((lbl, ok1, ok2, ok1 and ok2))
    n_plateau = sum(1 for _, _, _, ok in plateau_hits if ok)
    c5 = n_plateau >= 4   # 6セル中「過半」

    emit(f"  ① CAGR≥B&H          : 戦 {a['cagr']*100:.2f}% vs B&H {b['cagr']*100:.2f}%  "
         f"→ {'PASS' if c1 else 'FAIL'}")
    emit(f"  ② maxDD≤0.6×B&H     : 戦 {a['maxdd']*100:.1f}% vs バー "
         f"{0.6*b['maxdd']*100:.1f}% (B&H {b['maxdd']*100:.1f}%)  → {'PASS' if c2 else 'FAIL'}")
    emit(f"  ③ 前後半 Sharpe≥B&H : 前半 {hb[0][3]:.4f}/{hb[0][4]:.4f}, "
         f"後半 {hb[1][3]:.4f}/{hb[1][4]:.4f}  → {'PASS' if c3 else 'FAIL'}")
    emit(f"  ④ ETH 再現(①②)    : CAGR {ea['cagr']*100:.2f}% vs {eb['cagr']*100:.2f}% "
         f"({'○' if e1 else '×'}), maxDD {ea['maxdd']*100:.1f}% vs バー "
         f"{0.6*eb['maxdd']*100:.1f}% ({'○' if e2 else '×'}), "
         f"Sharpe {ea['sharpe']:.3f} vs {eb['sharpe']:.3f} ({'○' if e_sharpe else '×'}) "
         f"→ {'PASS' if c4 else ('部分再現' if e_sharpe else 'FAIL')}")
    emit(f"  台地 (6セル中①②同時): {n_plateau}/6 → {'PASS' if c5 else 'FAIL'}")
    for lbl, ok1, ok2, ok in plateau_hits:
        emit(f"      {lbl:9s} ①{'○' if ok1 else '×'} ②{'○' if ok2 else '×'} "
             f"→ {'○' if ok else '×'}")
    verdict = all([c1, c2, c3, c4, c5])
    emit(f"  総合: {'ALL PASS' if verdict else 'FAIL'}")

    digest["judgement"] = {"c1": bool(c1), "c2": bool(c2), "c3": bool(c3),
                           "c4": bool(c4), "eth_sharpe": bool(e_sharpe),
                           "plateau": int(n_plateau), "verdict": bool(verdict)}
    digest["primary_btc"] = {k: float(a[k]) for k in
                             ("cagr", "vol", "sharpe", "maxdd", "mar", "switches")}
    digest["primary_btc_bh"] = {k: float(b[k]) for k in
                                ("cagr", "vol", "sharpe", "maxdd", "mar")}
    digest["primary_eth"] = {k: float(ea[k]) for k in
                             ("cagr", "vol", "sharpe", "maxdd", "mar")}

    # ---------------- 参考: 円建て
    emit("\n## 9. 参考出力(スコープ外): 円建て換算 [btcusd SMA200]")
    fx = pd.read_csv(DATA / "fred_DEXJPUS.csv")
    fx["observation_date"] = pd.to_datetime(fx["observation_date"])
    fx = fx.set_index("observation_date")["DEXJPUS"]
    fx = pd.to_numeric(fx, errors="coerce").reindex(
        pd.date_range(fx.index.min(), pres["dates"][-1], freq="D")).ffill()
    common = pres["dates"].intersection(fx.index)
    if len(common) > 100:
        j = fx.loc[common]
        rj = (j / j.shift(1) - 1.0).to_numpy()[1:]
        sub = pd.Series(pres["strat"], index=pres["dates"]).loc[common].to_numpy()[1:]
        bsub = pd.Series(pres["bh"], index=pres["dates"]).loc[common].to_numpy()[1:]
        dj = common[1:]
        mj_s = metrics((1 + sub) * (1 + rj) - 1, dj)
        mj_b = metrics((1 + bsub) * (1 + rj) - 1, dj)
        emit(f"  円建て 戦略: CAGR {mj_s['cagr']*100:.2f}% Sharpe {mj_s['sharpe']:.3f} "
             f"maxDD {mj_s['maxdd']*100:.1f}%")
        emit(f"  円建て B&H : CAGR {mj_b['cagr']*100:.2f}% Sharpe {mj_b['sharpe']:.3f} "
             f"maxDD {mj_b['maxdd']*100:.1f}%  (FX 終端 {fx.index[-1].date()} まで)")
    else:
        emit("  FX データ不足のためスキップ")

    # ---------------- 多重性
    emit("\n## 10. 多重性")
    emit(f"  探索セル数 = {len(CELLS)}(規則2 × N3、事前登録で列挙・凍結)。"
         f"主セル SMA200 は文献事前分布から事前指名(データ選択なし)。")
    emit(f"  判定は主セル1本のみ。感度族は台地条件(過半)の材料であり選択には使わない。")
    emit(f"  資産 2(BTC 主判定 / ETH 再現要求)。実行回数 1。")

    return digest


def main() -> int:
    d1 = analyse()
    h1 = hashlib.sha256(json.dumps(d1, sort_keys=True).encode()).hexdigest()[:16]
    saved = OUT[:]
    OUT.clear()
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        d2 = analyse()
    h2 = hashlib.sha256(json.dumps(d2, sort_keys=True).encode()).hexdigest()[:16]
    OUT[:] = saved
    print(f"\n## 11. 決定性: 2回実行の要約ハッシュ {h1} / {h2} → "
          f"{'一致 PASS' if h1 == h2 else '不一致 FAIL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
