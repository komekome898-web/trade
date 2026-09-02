"""RC1 judgment — equal-weight composite of crowd psychology x large traders x technicals.

Verbatim transcription of the frozen pre-registration
(docs/PREREG_regime_composite.md, frozen 2026-09-01):

    # PREREG — RC1: 大衆心理×大口×テクニカルの等重量合成指標(週次・方向)

    **凍結日: 2026-09-01。以降の変更は事前登録の破棄。**
    オーナー提案「楽観・悲観、大口の予測、テクニカルを組み合わせたインジケーター」を、
    掘り出しが構造的に起きない形に限定して一発判定する。

    ## 0. なぜこの形か(判定可能性の条件)

    - サイクル・タイミング(n≈4)は判定不能と結論済み(SURVEY_ATTENTION_DATA §3)。
      **週次ホライズン**なら 2020〜2026 で非重複サンプル ≈350週、OOSだけで ≈190週 — 判定可能。
    - 重みをデータに合わせた瞬間に「4レジームへの曲線当てはめ」になる(Freqtrade評価 §7、
      S4の教訓)。よって**重みは等しく固定、各成分の符号は機構から本文書で事前固定**し、
      判定後に一切動かさない。
    - 注目Z(Wikipedia)は方向予測として閉鎖済み(§3)のため**方向合成には入れない**。
      楽観/悲観の代理は GDELT の報道トーン(日次・2017〜・無料)。

    ## 1. 成分(6つ・符号固定・変更禁止)

    各成分は直近365日ローリングZに標準化し、下記符号を掛けて**単純平均**する。

    | # | 成分 | データ | 符号 | 機構(事前分布) |
    |---|---|---|---|---|
    | 1 | 資金調達率(直近3日平均) | Binance BTCUSDT fundingRate(2020-01〜) | **−** | 高い資金調達=ロング過密→翌週リターン低下(混雑の逆張り、文献多数) |
    | 2 | 先物プレミアム(日次平均) | Binance premiumIndexKlines 1d | **−** | 同上(ベーシス過熱の逆張り) |
    | 3 | 全体ロング/ショート口座比 | Binance metrics `count_long_short_ratio`(2021-01〜) | **−** | 個人口座のロング偏重は逆張り |
    | 4 | **トップトレーダー建玉L/S比**(大口) | Binance metrics `sum_toptrader_long_short_ratio` | **+** | 情報優位者の順張り |
    | 5 | 報道トーン(楽観−悲観、7日平均) | GDELT timelinetone "bitcoin" | **−** | 楽観極値は逆張り(注目・過大評価→反転) |
    | 6 | 4週モメンタム(28日リターンの符号付きZ) | Bitstamp日足(attention.csv) | **+** | 短期時系列モメンタム(Liu–Tsyvinski) |

    成分3・4は 2021-01 以前が欠測。**判定窓(OOS)は全成分が揃う期間のみ**。欠測成分がある
    週は残り成分の平均(最低4成分揃わない週は除外)。

    ## 2. 標本設計

    - 観測: **毎週月曜 00:00 UTC** に合成値を計算(直前の日曜までのデータのみ。公開ラグ:
      Binance/GDELT は同日利用可)。目的変数 = **翌7日間の対数リターン**(Bitstamp終値)。非重複。
    - 探索(フィージビリティ)窓: **2021-01-04 〜 2022-12-26**(汚染面。合成の符号確認のみ)
    - **判定窓(OOS、一度だけ): 2023-01-02 〜 2026-08-31**

    ## 3. フィージビリティ足切り(探索窓で先に適用)

    合成値と翌週リターンのSpearman IC が **t<0**(符号が事前分布と逆)なら、OOSを開けずに
    **実現可能性で棄却**(OOSの処女性を再設計のために温存)。IC>0 なら符号の合否に関わらず
    OOS判定へ進む(探索窓のt値は採用根拠にしない)。

    ## 4. 判定基準(OOS、凍結)

    1. **IC**: Spearman(合成_t, 翌週リターン) > 0 かつ **t ≥ 2.0**(週サンプル、n≈190)
    2. **分位スプレッド**: 合成の上位20%週 − 下位20%週 の平均翌週リターン > 0 かつ t ≥ 1.5
    3. **台地(成分の符号整合)**: 6成分中 **4つ以上**がOOSで事前指定と同符号のIC
       (合成が1成分に支配されていないことの要求)
    4. コスト: 週次の建玉切替を想定し **往復6bps/週**(bitFlyer taker)を分位スプレッドから控除しても正

    ## 5. 必須報告

    成分ごとのOOS IC(符号・t)/ 合成IC・分位5段の平均リターン表 / 年次分解(2023/24/25/26)/
    探索窓の同表(参考)/ 欠測週数 / 決定性(2回実行ハッシュ)/ ルックアヘッド0の構造説明
    (全特徴量は月曜00:00 UTC以前のデータのみ)。

    ## 6. 読み方(先に決める)

    | 結果 | 結論 |
    |---|---|
    | 1〜4すべて通過 | **方向の合成指標として初の通過**。次段 = 週次ロング/フラット(/ショート)オーバーレイの新PREREG(戦略化はそこで別途判定)。採用ではない |
    | 1 or 2 が落ちる | 方向合成は棄却。成分別に「規模(ボラ)ゲート」への転用のみ検討 |
    | 3のみ落ちる | 単一成分支配。その成分単独の新PREREGでなければ再検定不可(合成としては棄却) |
    | 探索で t<0 | 実現可能性で棄却(OOS未開封) |

    ## 7. 多重性

    合成1本・重み固定・符号固定・成分6(事前指名)。探索窓での成分入替・符号反転・
    重み調整は禁止(やれば本登録の破棄)。

    署名: リード。実装: `scripts/research_regime_composite.py`(本文書逐語 docstring、
    seed 20260901、一度だけ実行しそのまま報告)。データは
    `backtest_data/regime_composite_20260901/` に恒久保存。

Run: PYTHONPATH=src python scripts/research_regime_composite.py
Input:  backtest_data/regime_composite_20260901/features_daily.csv (scripts/fetch_regime_composite.py)
Output: stdout, mirrored to backtest_data/regime_composite_20260901/RC1_RUN.txt
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "backtest_data" / "regime_composite_20260901"
FEATURES = DATA / "features_daily.csv"
RUNLOG = DATA / "RC1_RUN.txt"

SEED = 20260901
N_BOOT = 10_000
COST_PER_WEEK = 0.0006          # PREREG §4.4 -- 6 bps round trip / week
Z_WINDOW = 365                  # trailing rows, current day EXCLUDED
Z_MIN_OBS = 300                 # non-missing rows required inside that window
MIN_COMPONENTS = 4              # PREREG §1

# PREREG §1 -- component name, feature column, fixed sign.  NEVER edited post-freeze.
COMPONENTS: list[tuple[str, str, int]] = [
    ("1 funding_3d_mean (資金調達率3日平均)", "funding_3d_mean", -1),
    ("2 premium_1d (先物プレミアム日次)", "premium_1d", -1),
    ("3 ls_ratio (全体L/S口座比)", "ls_ratio", -1),
    ("4 toptrader_ls (大口建玉L/S比)", "toptrader_ls", +1),
    ("5 tone_7d_mean (GDELT報道トーン7日)", "tone_7d_mean", -1),
    ("6 ret_28d (4週モメンタム)", "ret_28d", +1),
]

EXPLORE = (date(2021, 1, 4), date(2022, 12, 26))
OOS = (date(2023, 1, 2), date(2026, 8, 31))

_BUF = io.StringIO()


def say(line: str = "") -> None:
    print(line)
    _BUF.write(line + "\n")


# ----------------------------------------------------------------- statistics
def rankdata(x: np.ndarray) -> np.ndarray:
    """Average ranks, ties shared (Spearman needs this)."""
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    sx = x[order]
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and sx[j + 1] == sx[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3:
        return float("nan")
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float(a @ a) * float(b @ b))
    return float(a @ b) / den if den > 0 else float("nan")


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    return pearson(rankdata(a), rankdata(b))


def corr_t(r: float, n: int) -> float:
    """Simple t on a correlation, n non-overlapping weekly samples."""
    if not np.isfinite(r) or n < 4 or abs(r) >= 1.0:
        return float("nan")
    return r * math.sqrt((n - 2) / (1.0 - r * r))


def welch_t(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    if va + vb <= 0:
        return float("nan")
    return float((a.mean() - b.mean()) / math.sqrt(va + vb))


# ----------------------------------------------------------------- data layer
def load_features() -> dict[str, dict[str, float]]:
    if not FEATURES.exists():
        raise SystemExit(f"missing {FEATURES}; run scripts/fetch_regime_composite.py")
    out: dict[str, dict[str, float]] = {}
    with FEATURES.open() as fh:
        for row in csv.DictReader(fh):
            rec = {}
            for k, v in row.items():
                if k == "date":
                    continue
                v = (v or "").strip()
                rec[k] = float(v) if v else float("nan")
            out[row["date"]] = rec
    return out


def rolling_z(days: list[str], raw: dict[str, float]) -> dict[str, float]:
    """Z of day d against the trailing Z_WINDOW rows STRICTLY BEFORE d.

    std == 0 -> missing (PREREG §1).  Excluding the current row is what makes
    the feature computable at Monday 00:00 UTC from Sunday-and-earlier data.
    """
    vals = np.array([raw.get(d, float("nan")) for d in days], dtype=float)
    z: dict[str, float] = {}
    for i, d in enumerate(days):
        x = vals[i]
        if not np.isfinite(x):
            continue
        lo = max(0, i - Z_WINDOW)
        win = vals[lo:i]
        win = win[np.isfinite(win)]
        if len(win) < Z_MIN_OBS:
            continue
        sd = win.std(ddof=1)
        if not np.isfinite(sd) or sd <= 0:
            continue
        z[d] = float((x - win.mean()) / sd)
    return z


def mondays(first: str, last: str) -> list[date]:
    d0, d1 = date.fromisoformat(first), date.fromisoformat(last)
    d = d0 + timedelta(days=(7 - d0.weekday()) % 7)
    out = []
    while d <= d1:
        out.append(d)
        d += timedelta(days=7)
    return out


def build_samples(feat: dict[str, dict[str, float]]):
    """One row per Monday 00:00 UTC.  Returns (samples, diagnostics)."""
    days = sorted(feat)
    zs = {col: rolling_z(days, {d: feat[d][col] for d in days})
          for _, col, _ in COMPONENTS}
    close = {d: feat[d]["close"] for d in days if np.isfinite(feat[d]["close"])}

    samples, dropped_few, dropped_noret = [], 0, 0
    for m in mondays(days[0], days[-1]):
        sunday = (m - timedelta(days=1)).isoformat()
        parts, per_comp = [], {}
        for name, col, sign in COMPONENTS:
            v = zs[col].get(sunday)
            if v is None:
                per_comp[col] = float("nan")
                continue
            per_comp[col] = sign * v
            parts.append(sign * v)
        if len(parts) < MIN_COMPONENTS:
            dropped_few += 1
            continue
        ms, ns = m.isoformat(), (m + timedelta(days=7)).isoformat()
        if ms not in close or ns not in close:
            dropped_noret += 1
            continue
        # zero look-ahead: every feature is the Sunday row, strictly before the
        # Monday 00:00 UTC sample stamp -- asserted here, not merely asserted in prose.
        assert sunday < ms
        samples.append({
            "monday": m, "feature_date": sunday, "n_comp": len(parts),
            "composite": float(np.mean(parts)),
            "fwd": math.log(close[ns] / close[ms]),
            **per_comp,
        })
    return samples, {"dropped_lt4_components": dropped_few,
                     "dropped_no_forward_return": dropped_noret,
                     "z_window": Z_WINDOW, "z_min_obs": Z_MIN_OBS}


def window(samples, lo: date, hi: date):
    return [s for s in samples if lo <= s["monday"] <= hi]


# ----------------------------------------------------------------- reporting
def quintile_table(rows) -> tuple[list[dict], float, float]:
    x = np.array([r["composite"] for r in rows])
    y = np.array([r["fwd"] for r in rows])
    order = np.argsort(rankdata(x), kind="mergesort")
    groups = np.array_split(order, 5)
    table = []
    for i, g in enumerate(groups, 1):
        table.append({"q": i, "n": len(g),
                      "comp_lo": float(x[g].min()), "comp_hi": float(x[g].max()),
                      "mean_fwd": float(y[g].mean()),
                      "median_fwd": float(np.median(y[g])),
                      "hit": float((y[g] > 0).mean())})
    q1, q5 = y[groups[0]], y[groups[-1]]
    return table, float(q5.mean() - q1.mean()), welch_t(q5, q1)


def block_bootstrap_ic(rows, seed: int = SEED, reps: int = N_BOOT):
    """Weekly-block bootstrap (blocks are the non-overlapping weekly samples)."""
    x = np.array([r["composite"] for r in rows])
    y = np.array([r["fwd"] for r in rows])
    rng = np.random.default_rng(seed)
    n = len(x)
    out = np.empty(reps)
    for i in range(reps):
        idx = rng.integers(0, n, n)
        out[i] = spearman(x[idx], y[idx])
    return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))


def report_window(rows, label: str) -> dict:
    say(f"--- {label}: n={len(rows)} weeks "
        f"({rows[0]['monday']} .. {rows[-1]['monday']}) ---")
    x = np.array([r["composite"] for r in rows])
    y = np.array([r["fwd"] for r in rows])
    ic = spearman(x, y)
    t = corr_t(ic, len(rows))
    say(f"composite Spearman IC = {ic:+.4f}   t = {t:+.3f}   n = {len(rows)}")
    say(f"composite mean/sd = {x.mean():+.4f} / {x.std(ddof=1):.4f}; "
        f"fwd mean = {y.mean()*100:+.3f}%/wk")

    say("")
    say("component IC (signed component vs next-week return; >0 == prior sign held)")
    say(f"  {'component':44s} {'n':>5s} {'IC':>8s} {'t':>7s}  prior  ok")
    comp_ok = 0
    comp_rows = []
    for name, col, sign in COMPONENTS:
        v = np.array([r[col] for r in rows])
        m = np.isfinite(v)
        if m.sum() < 10:
            say(f"  {name:44s} {int(m.sum()):5d} {'--':>8s} {'--':>7s}"
                f"   {'+' if sign > 0 else '-'}    n/a")
            comp_rows.append({"col": col, "n": int(m.sum()), "ic": float('nan'),
                              "t": float('nan'), "ok": False})
            continue
        c = spearman(v[m], y[m])
        tc = corr_t(c, int(m.sum()))
        ok = c > 0
        comp_ok += int(ok)
        comp_rows.append({"col": col, "n": int(m.sum()), "ic": c, "t": tc, "ok": ok})
        say(f"  {name:44s} {int(m.sum()):5d} {c:+8.4f} {tc:+7.2f}"
            f"   {'+' if sign > 0 else '-'}   {'YES' if ok else 'no'}")
    say(f"  components with prior sign held: {comp_ok}/6")

    say("")
    table, spread, tspread = quintile_table(rows)
    say("quintiles of the composite (Q1 = most bearish signal, Q5 = most bullish)")
    say(f"  {'Q':>2s} {'n':>4s} {'comp range':>20s} {'mean fwd':>10s} "
        f"{'median':>9s} {'hit':>7s}")
    for r in table:
        say(f"  {r['q']:2d} {r['n']:4d} "
            f"[{r['comp_lo']:+7.3f},{r['comp_hi']:+7.3f}] "
            f"{r['mean_fwd']*100:+9.3f}% {r['median_fwd']*100:+8.3f}% "
            f"{r['hit']*100:6.1f}%")
    say(f"  Q5-Q1 spread = {spread*100:+.3f}%/wk   Welch t = {tspread:+.3f}")
    say(f"  after {COST_PER_WEEK*1e4:.0f} bps/wk cost: "
        f"{(spread - COST_PER_WEEK)*100:+.3f}%/wk")

    say("")
    say("annual decomposition")
    say(f"  {'year':>5s} {'n':>4s} {'IC':>8s} {'t':>7s} {'Q5-Q1':>10s}")
    for yr in sorted({r["monday"].year for r in rows}):
        sub = [r for r in rows if r["monday"].year == yr]
        if len(sub) < 10:
            say(f"  {yr:5d} {len(sub):4d} {'--':>8s} {'--':>7s} {'--':>10s}")
            continue
        sx = np.array([r["composite"] for r in sub])
        sy = np.array([r["fwd"] for r in sub])
        sic = spearman(sx, sy)
        _, sspread, _ = quintile_table(sub)
        say(f"  {yr:5d} {len(sub):4d} {sic:+8.4f} {corr_t(sic, len(sub)):+7.2f} "
            f"{sspread*100:+9.3f}%")
    say("")
    return {"ic": ic, "t": t, "n": len(rows), "spread": spread,
            "t_spread": tspread, "comp_ok": comp_ok, "comp_rows": comp_rows,
            "table": table}


def digest(rows) -> str:
    h = hashlib.sha256()
    for r in rows:
        h.update(f"{r['monday']}|{r['composite']:.12f}|{r['fwd']:.12f}|"
                 f"{r['n_comp']}".encode())
    return h.hexdigest()[:16]


# ----------------------------------------------------------------- main
def main() -> None:
    say("=" * 78)
    say("RC1 — 大衆心理×大口×テクニカルの等重量合成指標(PREREG 2026-09-01 凍結)")
    say("=" * 78)
    say(f"features: {FEATURES.relative_to(ROOT)}")
    say(f"seed={SEED}  bootstrap reps={N_BOOT}  cost={COST_PER_WEEK*1e4:.0f} bps/week")
    say("")

    feat = load_features()
    samples, diag = build_samples(feat)
    say(f"daily feature rows: {len(feat)} "
        f"({min(feat)} .. {max(feat)})")
    say(f"weekly samples built: {len(samples)} "
        f"({samples[0]['monday']} .. {samples[-1]['monday']})")
    say(f"dropped weeks — <4 components: {diag['dropped_lt4_components']}, "
        f"no forward return: {diag['dropped_no_forward_return']}")
    say("")
    say("look-ahead structure (PREREG §5): each sample is stamped Monday 00:00 UTC.")
    say("  Every component is a rolling Z of the SUNDAY daily row against the")
    say(f"  {Z_WINDOW} rows strictly BEFORE that Sunday (current row excluded), so the")
    say("  newest datum touching a feature is Sunday 23:59 UTC — strictly earlier")
    say("  than the sample stamp; `assert feature_date < monday` enforces it per row.")
    say("  The target is the Monday close -> next Monday close log return (Bitstamp),")
    say("  i.e. entirely in the future of the feature.  Weeks are non-overlapping.")
    say("")

    # ---------------- Phase A: feasibility gate on the exploration window (§3)
    say("=" * 78)
    say("§3 フィージビリティ足切り(探索窓 2021-01-04 .. 2022-12-26)")
    say("=" * 78)
    ex = window(samples, *EXPLORE)
    if len(ex) < 20:
        say(f"FATAL: exploration window has only {len(ex)} weeks")
        raise SystemExit(1)
    ex_stats = report_window(ex, "EXPLORATION (参考・符号確認のみ)")
    if not (ex_stats["t"] >= 0):
        say("=" * 78)
        say(">>> フィージビリティ棄却 (feasibility rejected): "
            f"exploration t = {ex_stats['t']:+.3f} < 0")
        say(">>> 事前分布と逆符号。PREREG §3 によりOOSは開封せず終了(処女性を温存)。")
        say(">>> 結論(§6): 探索で t<0 → 実現可能性で棄却(OOS未開封)")
        say("=" * 78)
        RUNLOG.write_text(_BUF.getvalue())
        return
    say(f">>> feasibility PASSED (exploration t = {ex_stats['t']:+.3f} >= 0) "
        "→ proceed to OOS (§4). Exploration t is NOT evidence of adoption.")
    say("")

    # ---------------- Phase B: OOS judgment (§4), opened once
    say("=" * 78)
    say("§4 判定窓 OOS 2023-01-02 .. 2026-08-31(一度だけ開封)")
    say("=" * 78)
    oo = window(samples, *OOS)
    st = report_window(oo, "OOS (判定窓)")
    lo, hi = block_bootstrap_ic(oo)
    say(f"weekly-block bootstrap IC 95% CI (seed {SEED}, {N_BOOT} reps): "
        f"[{lo:+.4f}, {hi:+.4f}]")
    say("  (blocks are the weekly non-overlapping samples themselves; the simple t")
    say("   above is the pre-registered statistic, this CI is a confirmation only)")
    say("")

    c1 = (st["ic"] > 0) and (st["t"] >= 2.0)
    c2 = (st["spread"] > 0) and (st["t_spread"] >= 1.5)
    c3 = st["comp_ok"] >= 4
    c4 = (st["spread"] - COST_PER_WEEK) > 0
    say("=" * 78)
    say("§4 判定(凍結基準)")
    say("=" * 78)
    say(f"  基準1 IC > 0 かつ t >= 2.0        : IC={st['ic']:+.4f} t={st['t']:+.3f} "
        f"-> {'PASS' if c1 else 'FAIL'}")
    say(f"  基準2 Q5-Q1 > 0 かつ t >= 1.5     : "
        f"spread={st['spread']*100:+.3f}%/wk t={st['t_spread']:+.3f} "
        f"-> {'PASS' if c2 else 'FAIL'}")
    say(f"  基準3 6成分中4以上が事前符号      : {st['comp_ok']}/6 "
        f"-> {'PASS' if c3 else 'FAIL'}")
    say(f"  基準4 6bps/週控除後も正           : "
        f"{(st['spread']-COST_PER_WEEK)*100:+.3f}%/wk "
        f"-> {'PASS' if c4 else 'FAIL'}")
    say("")
    allpass = c1 and c2 and c3 and c4
    say("§6 読み方に従う結論:")
    if allpass:
        say("  1〜4すべて通過 → 方向の合成指標として初の通過。次段 = 週次ロング/フラット")
        say("  オーバーレイの新PREREG(戦略化はそこで別途判定)。**採用ではない**。")
    elif not c1 or not c2:
        say("  基準1 or 2 が落ちた → **方向合成は棄却**。成分別に「規模(ボラ)ゲート」")
        say("  への転用のみ検討可(方向としては再検定しない)。")
    elif not c3:
        say("  基準3のみ落ちた → 単一成分支配。その成分単独の新PREREGでなければ")
        say("  再検定不可(合成としては棄却)。")
    else:
        say("  コスト控除で落ちた → 分位スプレッドが執行コストを覆えない。合成としては棄却。")
    say("")

    # ---------------- determinism (§5)
    h1 = digest(samples)
    feat2 = load_features()
    samples2, _ = build_samples(feat2)
    h2 = digest(samples2)
    b1 = block_bootstrap_ic(oo)
    b2 = block_bootstrap_ic(oo)
    say("=" * 78)
    say("§5 決定性")
    say("=" * 78)
    say(f"  sample digest run#1 = {h1}")
    say(f"  sample digest run#2 = {h2}   -> {'MATCH' if h1 == h2 else 'MISMATCH'}")
    say(f"  bootstrap CI run#1 = [{b1[0]:+.6f}, {b1[1]:+.6f}]")
    say(f"  bootstrap CI run#2 = [{b2[0]:+.6f}, {b2[1]:+.6f}]   "
        f"-> {'MATCH' if b1 == b2 else 'MISMATCH'}")
    say("=" * 78)

    RUNLOG.write_text(_BUF.getvalue())
    print(f"\n[saved] {RUNLOG}")


if __name__ == "__main__":
    main()
