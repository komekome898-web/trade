#!/usr/bin/env python3
"""# PREREG — ONR: J-REIT オーバーナイト・プレミアムの指数水準・新鮮期間による一発判定

**凍結日: 2026-09-04。以降の変更は「事前登録の破棄」。**

## 0. 位置づけと汚染の申告

- 発端: 「儲かる新戦略」探索(第40報)で、JPX上場ETFの日足を **寄り→引け / 引け→翌寄り** に
  分解したところ、夜間プレミアムは N225 だけでなく TOPIX・JPX400・J-REIT・グロース250 に
  **市場横断で存在**した。うち J-REIT ETF(1343、東証REIT指数連動、売買代金中央値 15億円/日)は
  2011-09〜2026-09 の **ETF約定水準**で ON +4.77bps/日 t=+4.60(年率 +11.0%)、日中 −5.6%/年、
  N225 夜間との相関 +0.51、Sharpe 1.19(N225 の 0.86 より高い)。
- **この 2011-09〜2026-09 の ETF 水準データは探索で全面的に見た(汚染面)**。本判定には使わず、
  参考として併記するだけ。
- 薄い REIT ETF(1476/1488、売買代金 2〜3億円)は夜間 +22〜27%/年と**過大**に出る。薄い ETF は
  「引け値ディスカウント・寄り値プレミアム」の約定アーティファクトを含む → **判定は ETF の
  約定水準ではなく指数水準で行う**(下記)。指数の始値は未寄り銘柄の前日終値を含む
  (stale-open)ため夜間を**過小**評価する = 保守側。
- 実弾の適性: 現物 ETF・手数料0(SOR条件、`SURVEY_JP_EQUITIES.md` §1.2)・板寄せ執行・
  1口 ¥19k・信用/先物口座不要。ON1(先物・FOP口座待ち)より早く最小実弾×自動化に入れる。
- 最大の帰無仮説: (i) ETF 水準の夜間は約定アーティファクトで、指数水準では縮む/消える、
  (ii) 2011年以前(2008年危機・上場初期)で符号が反転する。

## 1. 判定セル(唯一・パラメータゼロ。変更・追加禁止)

- **毎営業日**: 東証クロージング・オークション(15:30、2024-11-05以前は15:00)で 1343 を買い →
  翌営業日オープニング・オークション(9:00)で売り。フィルタなし、調整なし、サイズ固定。
- リターン定義: `r_t = ln(open(t+1) / close(t))`。
- **判定データ①(主)**: 東証REIT指数の日次四本値(JPX 公表値、始値・終値)。
  窓 = 取得可能な全期間(指数算出 2003-04〜)〜2026-09-03。**未閲覧**。
- **判定データ②(副)**: 1343 の ETF 約定水準 **2008-08-20(上場)〜2011-09-04** — 探索で
  未閲覧の新鮮期間。符号確認のみに使う(n≈750)。
- 参考(汚染、判定不使用): 1343 2011-09-05〜2026-09-03。
- 指数の四本値が入手不能なら、判定は②のみで **仮判定**とし、通過しても「指数水準未確認」
  の但し書きで前進(フォワード・ペーパーで ETF-vs-指数の乖離を実測する)。

## 2. コストモデル(凍結)

- 手数料: **0**(三菱UFJ eスマート証券、2026-05-18〜、SOR 条件)。ただし **寄成/引成 の
  板寄せ注文が無料条件(SOR)を満たすかは未確認**。満たさない場合は 1日定額(100万円まで0円)
  の有無を確認し、どちらも不成立なら ワンショット手数料(例 ¥99/片道)を元本で割った値に
  差し替えて③を再計算する(差し替えは本文書の付記として記録、選択には使わない)。
- 板寄せ参加はスプレッド越えなし。呼値の丸めは対称(期待値0)。
- **基準コスト: 0.0bps**。**保守コスト: 1.0bps/日 往復**(ON1 の保守引当と同水準。
  自注文が板寄せ値を動かす・約定価格の不利側偏りの引当)。
- ストレス(報告のみ、バーではない): 2.6bps/日 往復(ETF 呼値 ¥1 の 1/4 ティック片道が
  常に不利になる仮定)。
- 分配金(年 ≈3.5%、権利落ち日に夜間保有者が受領)は**判定に含めない**(含めれば夜間が
  さらに有利 = 保守側)。必須報告で分配金込みの年率を併記。

## 3. 判定基準(凍結)

1. **① 機構(グロス・指数水準)**: 判定データ①の全窓平均 > 0 かつ **t ≥ 2.0**
   (確認として定常ブロック・ブートストラップ 平均ブロック10日・10,000回・seed 20260904 の
   95%CI 下限 > 0)。
2. **② 台地**: 4分割 [2003-2008][2009-2014][2015-2020][2021-2026] のうち **3つ以上で平均 > 0**、
   かつ [2021-2026] が正。
3. **③ 新鮮期間の非矛盾**: 判定データ②(1343 2008-08〜2011-09)の平均 > 0。
4. **④ コスト後**: 保守コスト 1.0bps/日 控除後の指数水準平均 > 0 かつ **t ≥ 1.5**。

## 4. 必須報告(選択には使わない)

年次表 / 曜日別 / 日中(寄り→引け)の同表 / ETF水準(汚染面 2011-26)と指数水準の同一日付
比較(縮小率 = 指数ON平均 ÷ ETF ON平均)/ 分配金込み年率 / B&H(1343 終日保有)との比較
(年率・Sharpe・maxDD、ボラ一致レバレッジ換算)/ N225 夜間(1321)との相関と 50/50 合成の
Sharpe / ストレスコスト後の t / 決定性(2回実行ハッシュ)/ ルックアヘッド0の構造説明。

## 5. 多重性

- 本判定は横断サーベイ(第40報: 米株ETF 7本・JPX指数ETF 8本・REIT ETF 5本・大型株4)から
  「最も流動的で N225 と独立な夜間」を1つ選んだもの。**選択は ETF 水準の 2011-26**、
  **判定は指数水準(楽器方向の新鮮性)+ 2008-11(時間方向の新鮮性)**。セル1・自由パラメータ0。
- 通過時の2段目 = フォワード・ペーパー(ON1 forward と同型)→ 最小実弾×自動化(1口)。

## 6. 読み方(先に決める)

| 結果 | 結論 |
|---|---|
| ①〜④すべて通過 | オーナーへ提示: ON1 と同じ (c) リスク調整枠組み → フォワード追跡 + kabu 現物発注経路の実装判断。**採用ではない** |
| ① or ② が落ちる | **REIT の夜間は ETF 約定アーティファクト、または時代限定** → 棄却(機構水準) |
| ③ のみ落ちる | 上場初期・危機期の反転を記録。通過扱いにせず、フォワードでの再判定条件を別途登録 |
| ④ のみ落ちる | コスト律速として記録。格下げ通過はしない |

署名: リード。実装: `scripts/research_overnight_onr.py`(本文書逐語 docstring、seed 20260904、
一度だけ実行しそのまま報告)。データは `backtest_data/reit_onr_20260904/`(MD5SUMS つき)。

---
実装ノート(2026-09-04 実行時点。上の凍結文書には含まれない):
JPXの指数水準・日次四本値(2003-04〜)は無料では取得できなかった(試行と理由は
`backtest_data/reit_onr_20260904/manifest.md` に記録)。取得できたのは Kabutan の
無料日足ページ(直近 ~1年、2025-06-16〜2026-09-03)のみ。したがって判定基準①②④
(いずれも指数の全期間データが前提)は「仮判定・未確認」として扱い、本文書 §1 が
明示する縮退運転(「判定は②のみで仮判定」)に従う。③(新鮮期間 1343 2008-09〜2011-09、
実データは08-08-20でなく08-09-16開始。理由は同manifest)のみを正式判定として実行する。
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backtest_data" / "reit_onr_20260904"
SEED = 20260904
CUTOFF = "2026-09-03"
COST_CONSERVATIVE_BPS = 1.0
COST_STRESS_BPS = 2.6
GLITCH_ABS_LOG_RET = 0.10
TRADING_DAYS = 245

ERAS = [
    ("2003-2008", "2003-01-01", "2008-12-31"),
    ("2009-2014", "2009-01-01", "2014-12-31"),
    ("2015-2020", "2015-01-01", "2020-12-31"),
    ("2021-2026", "2021-01-01", "2026-12-31"),
]
FRESH_START, FRESH_END = "2008-08-20", "2011-09-04"
CONTAM_START, CONTAM_END = "2011-09-05", "2026-09-03"


# ---------------------------------------------------------------------- I/O #

def load_ohlc(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df[df["date"] <= pd.Timestamp(CUTOFF)].reset_index(drop=True)
    n_before = len(df)
    df = df[(df["open"] > 0) & (df["close"] > 0)].reset_index(drop=True)
    n_invalid = n_before - len(df)
    if n_invalid:
        print(f"[data quality] {path.name}: dropped {n_invalid} rows with open<=0 or "
              f"close<=0 (missing-data artifact, not a >10% glitch)", file=sys.stderr)
    return df


# ------------------------------------------------------------- return legs #

def overnight_returns(df: pd.DataFrame) -> pd.DataFrame:
    """r_t = ln(open(t+1)/close(t)), dated at t (the close date)."""
    o1 = df["open"].shift(-1)
    r = np.log(o1 / df["close"])
    out = pd.DataFrame({"date": df["date"], "r": r})
    return out.iloc[:-1].reset_index(drop=True)


def intraday_returns(df: pd.DataFrame) -> pd.DataFrame:
    r = np.log(df["close"] / df["open"])
    return pd.DataFrame({"date": df["date"], "r": r}).reset_index(drop=True)


def drop_glitches(df: pd.DataFrame, threshold: float = GLITCH_ABS_LOG_RET) -> tuple[pd.DataFrame, int]:
    mask = df["r"].abs() > threshold
    n = int(mask.sum())
    return df.loc[~mask].reset_index(drop=True), n


# --------------------------------------------------------------- stats -- #

def mean_t(x: np.ndarray) -> tuple[float, float, int]:
    n = len(x)
    if n < 2:
        return (float(x.mean()) if n else float("nan"), float("nan"), n)
    m = float(x.mean())
    s = float(x.std(ddof=1))
    t = m / (s / np.sqrt(n)) if s > 0 else float("nan")
    return m, t, n


def net_mean_t(x: np.ndarray, cost_bps: float) -> tuple[float, float]:
    cost = cost_bps * 1e-4
    n = len(x)
    s = float(x.std(ddof=1)) if n > 1 else float("nan")
    m_net = float(x.mean()) - cost
    t_net = m_net / (s / np.sqrt(n)) if s > 0 else float("nan")
    return m_net, t_net


def stationary_bootstrap_ci(x: np.ndarray, mean_block: float = 10, n_boot: int = 10000,
                             seed: int = SEED, alpha: float = 0.05) -> tuple[float, float]:
    """Politis-Romano stationary bootstrap of the mean; geometric block length."""
    n = len(x)
    if n < 5:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    p = 1.0 / mean_block
    boot_means = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.empty(n, dtype=np.int64)
        cur = rng.integers(0, n)
        cont = rng.random(n) >= p  # True => continue block, False => new random start
        for i in range(n):
            idx[i] = cur
            cur = (cur + 1) % n if cont[i] else int(rng.integers(0, n))
        boot_means[b] = x[idx].mean()
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def era_table(df: pd.DataFrame) -> list[dict]:
    rows = []
    for label, start, end in ERAS:
        sub = df[(df["date"] >= start) & (df["date"] <= end)]["r"].to_numpy()
        m, t, n = mean_t(sub)
        rows.append({"era": label, "n": n, "mean_bps": m * 1e4, "t": t})
    return rows


def weekday_table(df: pd.DataFrame) -> list[dict]:
    d = df.copy()
    d["wd"] = d["date"].dt.dayofweek
    names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    rows = []
    for wd, name in enumerate(names):
        sub = d[d["wd"] == wd]["r"].to_numpy()
        m, t, n = mean_t(sub)
        rows.append({"weekday": name, "n": n, "mean_bps": m * 1e4, "t": t})
    return rows


def yearly_table(df: pd.DataFrame) -> list[dict]:
    d = df.copy()
    d["yr"] = d["date"].dt.year
    rows = []
    for yr, sub in d.groupby("yr"):
        m, t, n = mean_t(sub["r"].to_numpy())
        rows.append({"year": int(yr), "n": n, "mean_bps": m * 1e4, "t": t})
    return rows


def annualized_from_daily_log_mean(mean_log: float, days: int = TRADING_DAYS) -> float:
    return float(np.expm1(mean_log * days))


def sharpe_annualized(x: np.ndarray, days: int = TRADING_DAYS) -> float:
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * np.sqrt(days))


def max_drawdown(log_returns: np.ndarray) -> float:
    if len(log_returns) == 0:
        return float("nan")
    equity = np.exp(np.cumsum(log_returns))
    peak = np.maximum.accumulate(equity)
    dd = equity / peak - 1.0
    return float(dd.min())


# ----------------------------------------------------------------- report #

def fmt_table(rows: list[dict], cols: list[str]) -> str:
    lines = [" | ".join(f"{c:>10}" for c in cols)]
    for r in rows:
        vals = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                vals.append(f"{v:10.3f}")
            else:
                vals.append(f"{str(v):>10}")
        lines.append(" | ".join(vals))
    return "\n".join(lines)


def main() -> int:
    out: list[str] = []

    def p(s: str = "") -> None:
        out.append(s)

    p("=" * 78)
    p("ONR — J-REIT overnight, index-level + fresh-period one-shot judgment")
    p(f"run date 2026-09-04, seed={SEED}, cutoff={CUTOFF}")
    p("=" * 78)

    # ---- load ---- #
    idx = load_ohlc(DATA / "reit_index_daily.csv")
    etf = load_ohlc(DATA / "etf_1343_daily.csv")
    n225 = load_ohlc(DATA / "etf_1321_daily.csv")
    div = pd.read_csv(DATA / "etf_1343_dividends.csv", parse_dates=["ex_date"])

    p(f"\n[data] index-level rows: {len(idx)} ({idx['date'].min().date()}..{idx['date'].max().date()}) "
      f"— PARTIAL, see manifest.md (full 2003-2026 window not obtainable free)")
    p(f"[data] 1343 ETF rows: {len(etf)} ({etf['date'].min().date()}..{etf['date'].max().date()})")
    p(f"[data] 1321 ETF rows: {len(n225)} ({n225['date'].min().date()}..{n225['date'].max().date()})")

    # ---- overnight legs, glitch filter ---- #
    idx_on_raw = overnight_returns(idx)
    etf_on_raw = overnight_returns(etf)
    n225_on_raw = overnight_returns(n225)
    idx_on, idx_dropped = drop_glitches(idx_on_raw)
    etf_on, etf_dropped = drop_glitches(etf_on_raw)
    n225_on, n225_dropped = drop_glitches(n225_on_raw)
    p(f"\n[glitch filter |log r|>{GLITCH_ABS_LOG_RET}] index dropped {idx_dropped}/{len(idx_on_raw)}, "
      f"1343 dropped {etf_dropped}/{len(etf_on_raw)}, 1321 dropped {n225_dropped}/{len(n225_on_raw)}")

    idx_intra = intraday_returns(idx)
    etf_intra = intraday_returns(etf)

    # ==================================================================== #
    # Judgment data ① (index-level, partial window only)
    # ==================================================================== #
    p("\n" + "-" * 78)
    p("[Judgment data (1) index-level overnight — PARTIAL WINDOW, see manifest]")
    x1 = idx_on["r"].to_numpy()
    m1, t1, n1 = mean_t(x1)
    ci_lo, ci_hi = stationary_bootstrap_ci(x1)
    p(f"n={n1}  mean={m1*1e4:+.3f}bps  t={t1:+.3f}  bootstrap95%CI=[{ci_lo*1e4:+.3f},{ci_hi*1e4:+.3f}]bps")
    m1_cons, t1_cons = net_mean_t(x1, COST_CONSERVATIVE_BPS)
    m1_stress, t1_stress = net_mean_t(x1, COST_STRESS_BPS)
    p(f"net @ conservative {COST_CONSERVATIVE_BPS}bps/day: mean={m1_cons*1e4:+.3f}bps t={t1_cons:+.3f}")
    p(f"net @ stress {COST_STRESS_BPS}bps/day (report only): t={t1_stress:+.3f}")

    p("\nera table (index-level; eras with no overlapping data are unavailable):")
    p(fmt_table(era_table(idx_on), ["era", "n", "mean_bps", "t"]))

    p("\nweekday table (index-level):")
    p(fmt_table(weekday_table(idx_on), ["weekday", "n", "mean_bps", "t"]))
    p("\nweekday table (index-level, intraday open->close):")
    p(fmt_table(weekday_table(idx_intra), ["weekday", "n", "mean_bps", "t"]))

    p("\nyearly table (index-level, overnight):")
    p(fmt_table(yearly_table(idx_on), ["year", "n", "mean_bps", "t"]))
    p("yearly table (index-level, intraday open->close):")
    p(fmt_table(yearly_table(idx_intra), ["year", "n", "mean_bps", "t"]))

    # ==================================================================== #
    # Judgment data ② (1343 ETF, fresh 2008-09..2011-09)
    # ==================================================================== #
    p("\n" + "-" * 78)
    p(f"[Judgment data (2) 1343 ETF-level overnight, fresh period nominal "
      f"{FRESH_START}..{FRESH_END}]")
    fresh_mask = (etf_on["date"] >= FRESH_START) & (etf_on["date"] <= FRESH_END)
    x2 = etf_on.loc[fresh_mask, "r"].to_numpy()
    m2, t2, n2 = mean_t(x2)
    actual_start = etf_on.loc[fresh_mask, "date"].min()
    p(f"actual data start {actual_start.date() if n2 else 'n/a'} "
      f"(nominal {FRESH_START}; Yahoo has no 1343 bars before 2008-09-16, see manifest)")
    p(f"n={n2}  mean={m2*1e4:+.3f}bps  t={t2:+.3f}  (sign check only, per PREREG)")

    # ==================================================================== #
    # Reference (contaminated, 2011-09-05..2026-09-03) — NOT used for judgment
    # ==================================================================== #
    p("\n" + "-" * 78)
    p(f"[Reference, CONTAMINATED, not used for judgment] 1343 ETF overnight "
      f"{CONTAM_START}..{CONTAM_END}]")
    ref_mask = (etf_on["date"] >= CONTAM_START) & (etf_on["date"] <= CONTAM_END)
    x_ref = etf_on.loc[ref_mask, "r"].to_numpy()
    m_ref, t_ref, n_ref = mean_t(x_ref)
    p(f"n={n_ref}  mean={m_ref*1e4:+.3f}bps  t={t_ref:+.3f}  ann={annualized_from_daily_log_mean(m_ref)*100:+.2f}%")

    # ==================================================================== #
    # Required report: ETF-vs-index same-date comparison + shrink ratio
    # ==================================================================== #
    p("\n" + "-" * 78)
    p("[Required report] ETF-vs-index same-date overnight comparison (overlap window)")
    merged = idx_on.merge(etf_on, on="date", suffixes=("_idx", "_etf"))
    p(f"overlap n={len(merged)} ({merged['date'].min().date() if len(merged) else 'n/a'}"
      f"..{merged['date'].max().date() if len(merged) else 'n/a'})")
    if len(merged):
        m_idx_o, t_idx_o, _ = mean_t(merged["r_idx"].to_numpy())
        m_etf_o, t_etf_o, _ = mean_t(merged["r_etf"].to_numpy())
        shrink = m_idx_o / m_etf_o if m_etf_o else float("nan")
        p(f"index ON mean={m_idx_o*1e4:+.3f}bps (t={t_idx_o:+.3f})  "
          f"ETF ON mean={m_etf_o*1e4:+.3f}bps (t={t_etf_o:+.3f})  shrink ratio={shrink:.3f}")
    else:
        p("no overlap — comparison unavailable")

    # ==================================================================== #
    # Required report: dividend-inclusive annualized overnight
    # ==================================================================== #
    p("\n" + "-" * 78)
    p("[Required report] dividend-inclusive annualized overnight return (1343 ETF, full window)")
    etf_full = etf.set_index("date")
    on_full = etf_on.copy()
    on_full["r_div"] = on_full["r"]
    prev_close = etf_full["close"].reindex(on_full["date"]).to_numpy()
    div_by_date = div.set_index("ex_date")["amount"]
    div_add = on_full["date"].shift(-1).map(div_by_date).fillna(0.0).to_numpy()
    # dividend on ex_date accrues to the overnight leg landing ON that ex_date's open
    with np.errstate(divide="ignore", invalid="ignore"):
        on_full["r_div"] = on_full["r"] + np.where(prev_close > 0, div_add / prev_close, 0.0)
    m_div, _, _ = mean_t(on_full["r_div"].to_numpy())
    m_nodiv, _, _ = mean_t(on_full["r"].to_numpy())
    p(f"overnight-only ann (no div): {annualized_from_daily_log_mean(m_nodiv)*100:+.2f}%   "
      f"dividend-inclusive ann: {annualized_from_daily_log_mean(m_div)*100:+.2f}%   "
      f"(n dividends applied={int((div_add>0).sum())})")

    # ==================================================================== #
    # Required report: B&H vs overnight-only, vol-matched leverage
    # ==================================================================== #
    p("\n" + "-" * 78)
    p("[Required report] Buy&Hold 1343 (close->close) vs overnight-only")
    close_full = etf["close"].to_numpy()
    bh_r = np.diff(np.log(close_full))
    on_r = etf_on["r"].to_numpy()
    bh_ann = annualized_from_daily_log_mean(bh_r.mean())
    on_ann = annualized_from_daily_log_mean(on_r.mean())
    bh_sharpe = sharpe_annualized(bh_r)
    on_sharpe = sharpe_annualized(on_r)
    bh_mdd = max_drawdown(bh_r)
    on_mdd = max_drawdown(on_r)
    p(f"B&H:        ann={bh_ann*100:+.2f}%  Sharpe={bh_sharpe:.2f}  maxDD={bh_mdd*100:.2f}%")
    p(f"ON-only:    ann={on_ann*100:+.2f}%  Sharpe={on_sharpe:.2f}  maxDD={on_mdd*100:.2f}%")
    vol_bh, vol_on = bh_r.std(ddof=1), on_r.std(ddof=1)
    lev = vol_bh / vol_on if vol_on > 0 else float("nan")
    on_lev_ann = annualized_from_daily_log_mean(on_r.mean() * lev)
    p(f"vol-matched leverage on ON-only to match B&H daily vol: {lev:.2f}x -> ann={on_lev_ann*100:+.2f}% "
      f"(gross, cost/borrow of leverage not modeled)")

    # ==================================================================== #
    # Required report: correlation with 1321 overnight, 50/50 Sharpe
    # ==================================================================== #
    p("\n" + "-" * 78)
    p("[Required report] correlation with 1321 (N225 ETF) overnight, 50/50 blend")
    m2_ = etf_on.merge(n225_on, on="date", suffixes=("_1343", "_1321"))
    if len(m2_) > 2:
        corr = float(np.corrcoef(m2_["r_1343"], m2_["r_1321"])[0, 1])
        blend = 0.5 * m2_["r_1343"] + 0.5 * m2_["r_1321"]
        blend_sharpe = sharpe_annualized(blend.to_numpy())
        p(f"n overlap={len(m2_)}  corr(1343_ON, 1321_ON)={corr:+.3f}  50/50 blend Sharpe={blend_sharpe:.2f}")
    else:
        p("insufficient overlap for correlation")

    # ==================================================================== #
    # Lookahead-0 structural note
    # ==================================================================== #
    p("\n" + "-" * 78)
    p("[Structural note] lookahead = 0: r_t uses close(t) [observed at/after 15:30 close\n"
      "  auction, trade date t] and open(t+1) [observed at/after 9:00 open auction, next\n"
      "  trading date]. Both prices are realized, tradable auction prints; no feature or\n"
      "  label window overlaps the other side of the trade. Entry (buy at close t) and\n"
      "  exit (sell at open t+1) are both auctions the strategy participates in, not\n"
      "  observed-then-predicted continuous-session prices.")

    # ==================================================================== #
    # Verdict block
    # ==================================================================== #
    p("\n" + "=" * 78)
    p("VERDICT (PREREG §3)")
    p("=" * 78)

    era_rows = era_table(idx_on)
    n_positive_eras = sum(1 for r in era_rows if r["n"] > 0 and r["mean_bps"] > 0)
    n_eras_with_data = sum(1 for r in era_rows if r["n"] > 0)
    last_era_positive = era_rows[-1]["n"] > 0 and era_rows[-1]["mean_bps"] > 0

    verdict1 = "UNVERIFIED (index full-window data unavailable, see manifest.md)"
    verdict2 = ("UNVERIFIED (index full-window data unavailable; only "
                f"{n_eras_with_data}/4 eras have data)")
    verdict3_pass = bool(n2 and m2 > 0)
    verdict3 = "PASS" if verdict3_pass else ("FAIL" if n2 else "NO DATA")
    verdict4 = "UNVERIFIED (index full-window data unavailable, see manifest.md)"

    p(f"① 機構(グロス・指数水準, 全窓 mean>0 & t>=2.0, CI下限>0): {verdict1}")
    p(f"   [partial-window diagnostic only] mean={m1*1e4:+.3f}bps t={t1:+.3f} "
      f"CI_lo={ci_lo*1e4:+.3f}bps")
    p(f"② 台地(4era中3つ+ かつ [2021-2026]正): {verdict2}")
    p(f"   [partial] eras with data={n_eras_with_data}/4, positive among those={n_positive_eras}, "
      f"[2021-2026] positive={last_era_positive}")
    p(f"③ 新鮮期間の非矛盾(1343 {FRESH_START}~{FRESH_END}, mean>0): {verdict3}  "
      f"(n={n2}, mean={m2*1e4:+.3f}bps, t={t2:+.3f})")
    p(f"④ コスト後(指数水準, 保守1.0bps/日控除後 mean>0 & t>=1.5): {verdict4}")

    p("\nOVERALL: PROVISIONAL (仮判定) per PREREG §1 fallback — index-level full-window\n"
      "  data (2003-04~2026-09) could not be obtained free of charge (see manifest.md).\n"
      "  Only ③ (fresh 2008-2011 ETF-level sign check) is a bona fide pre-registered\n"
      "  judgment; it " + ("PASSES" if verdict3_pass else "FAILS") + f" (mean={m2*1e4:+.3f}bps, "
      f"t={t2:+.3f}, n={n2}). ①②④ require the missing index-level history and are\n"
      "  reported as diagnostics on the partial (2025-06~2026-09) index window only —\n"
      "  NOT a substitute for the pre-registered full-window bar. Per PREREG §6, a\n"
      "  provisional pass on ③ alone does not authorize forward tracking on its own;\n"
      "  it should be read with the \"指数水準未確認\" caveat the document itself specifies.")

    # ==================================================================== #
    # Determinism hash
    # ==================================================================== #
    body = "\n".join(out)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    p("\n" + "=" * 78)
    p(f"determinism hash (sha256 of report body above): {digest}")

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
