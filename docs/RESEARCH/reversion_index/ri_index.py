"""逆張りの期待値の指標の 1(時間を入れない指標)と 2(年ごとのずれ)。枠組み `docs/DISCUSSIONS/2026-10-10_reversion_index/FRAMING.md` §1・§2。
入力: ri_starts.py の起点(外れた最初の足)の pkl(bitFlyer・Binance、k ごと)。
量(10 個、FRAMING §1。起点の足が閉じた時点で分かる): ブレイクの線までの距離・外れの深さ・直前 5 分の値動き・直前 60 分の値動き・幅 ÷ ボラ・ボラ ÷ 値段・時刻(日本時間 4 時間)・向き・ボラ加速度(今 ÷ 20 本前)・レンジ加速度(同)。
結果: 戻る = 20 分以内に中心の側の (k − 1) ボラの線にブレイクの線より先に届く(結果 i)。値動き = 起点の終値から 20 分後の終値まで(5・40 分も)、中心へ向かう向きを正、ボラの何倍か。
作り方: 量ごとに帯(作る期間の五分位。ブレイクの線が無い起点は別の帯)に分けた印を並べ、戻るはロジスティック回帰(IRLS、弱いリッジ 1e-3)、値動きは最小二乗。
作る期間 = bitFlyer 2016-01-01〜2019-12-08。当てる = bitFlyer 2019-12-09〜2023-12-17 と Binance 2018-01-01〜2023-12-17(作った式をそのまま当てる)。
区間は日の塊(循環 5 日・1,000 回・種 20261004)。【試験の無い台本の値】
    python3 docs/RESEARCH/reversion_index/ri_index.py <起点の置き場> <k> > docs/RESEARCH/reversion_index/ri_index_k<k>.out
"""
import glob
import gzip
import pickle
import sys

import numpy as np
import pandas as pd

D, K = sys.argv[1], int(sys.argv[2])
rng = np.random.default_rng(20261004)
CUT = "2019-12-09"


def closes(venue):
    if venue == "bitflyer":
        F = sorted(f for f in glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz") if int(f[-11:-7]) <= 2023)
        b = pd.concat(pd.read_csv(f, usecols=["ts", "close"]) for f in F).dropna()
        t = pd.to_datetime(b.ts, utc=True)
    else:
        F = sorted(glob.glob("backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_20[12][0-9].csv.gz"))
        b = pd.concat(pd.read_csv(f, usecols=["open_time", "close"]) for f in F).dropna()
        t = pd.to_datetime(b.open_time, utc=True).dt.floor("min")
    s = pd.Series(b.close.to_numpy(), index=t)
    s = s[~s.index.duplicated()].sort_index()
    return s[s.index < pd.Timestamp("2023-12-17T15:00Z")]


def load(venue):
    d = pd.DataFrame(pickle.load(open(f"{D}/{venue}_k{K}.pkl", "rb")))
    c = closes(venue)
    t0 = pd.to_datetime(d.ts, utc=True)
    EP = pd.Timestamp("1970-01-01", tz="UTC")
    idx = ((c.index - EP) // pd.Timedelta("1ns")).to_numpy(dtype=np.int64)  # 単位の取り違えを避ける(research-protocol §6)
    t0n = ((t0 - EP) // pd.Timedelta("1ns")).to_numpy(dtype=np.int64)
    cv = c.to_numpy()

    def last_le(dt):
        """起点の dt 分後(負は前)の時刻以前で最後の 1 分足の終値。"""
        j = np.searchsorted(idx, t0n + dt * 60_000_000_000, side="right") - 1
        return np.where(j >= 0, cv[np.clip(j, 0, None)], np.nan)

    s = d.side.to_numpy()
    d["y"] = (d.outcome == "i").astype(float)
    d["line"] = s * (d.c0 - d.break_line.astype(float)) / d.vola
    d["depth"] = s * (d.center - d.c0) / d.vola
    d["mom5"] = s * (d.c0 / last_le(-5) - 1) * 1e4
    d["mom60"] = s * (d.c0 / last_le(-60) - 1) * 1e4
    d["w_v"] = d.width / d.vola
    d["v_bp"] = d.vola / d.c0 * 1e4
    d["hour"] = ((t0.dt.hour + 9) % 24 // 4 * 4).to_numpy()
    d["vacc"] = d.vola / d.vola20.astype(float)
    d["racc"] = d.width / d.width20.astype(float)
    for h in (5, 20, 40):
        d[f"r{h}"] = s * (last_le(h) - d.c0) / d.vola
    d["y_"] = d.day.str[:4].astype(int)
    return d


NUM = ["line", "depth", "mom5", "mom60", "w_v", "v_bp", "vacc", "racc"]
NAME = {"line": "ブレイクの線まで(ボラ)", "depth": "外れの深さ(ボラ)", "mom5": "直前 5 分(bp、負 = 外れる向き)", "mom60": "直前 60 分(bp)",
        "w_v": "幅 ÷ ボラ", "v_bp": "ボラ ÷ 値段(bp)", "vacc": "ボラ加速度", "racc": "レンジ加速度"}


def design(d, edges):
    cols, names = [np.ones(len(d))], ["切片"]
    for k in NUM:
        e = edges[k]
        b = np.digitize(d[k].to_numpy(), e)  # 0..4、nan は 5
        b = np.where(np.isnan(d[k].to_numpy()), 5, b)
        for j in (0, 1, 3, 4, 5):  # 真ん中の帯(2)が基準
            if k != "line" and j == 5:
                continue
            cols.append((b == j).astype(float)); names.append(f"{k}:{j}")
    for h in (0, 4, 8, 16, 20):  # 12〜16 時が基準
        cols.append((d.hour.to_numpy() == h).astype(float)); names.append(f"hour:{h}")
    cols.append((d.side.to_numpy() == -1).astype(float)); names.append("side:売りの側")
    X = np.column_stack(cols)
    X[np.isnan(X)] = 0
    return X, names


def logit_fit(X, y, lam=1e-3):
    b = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ b))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + lam * np.eye(X.shape[1])
        g = X.T @ (y - p) - lam * b
        step = np.linalg.solve(H, g)
        b += step
        if np.abs(step).max() < 1e-8:
            break
    return b


def auc(p, y):
    o = np.argsort(p)
    r = np.empty(len(p)); r[o] = np.arange(1, len(p) + 1)
    n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def ci_mean(v, days):
    g = pd.DataFrame({"v": v, "d": days}).groupby("d").v.agg(["sum", "size"]).to_numpy()
    n = len(g)
    st = rng.integers(0, n, size=(1000, int(np.ceil(n / 5))))
    idx = (st[:, :, None] + np.arange(5)).reshape(1000, -1)[:, :n] % n
    m = g[idx, 0].sum(axis=1) / g[idx, 1].sum(axis=1)
    return f"{v.mean():+.3f} [{np.percentile(m, 2.5):+.3f}, {np.percentile(m, 97.5):+.3f}]"


bf, bn = load("bitflyer"), load("binance")
bf = bf[bf.y_ >= 2016]
bn = bn[bn.y_ >= 2018]
fit = bf[bf.day < CUT]
edges = {k: fit[k].dropna().quantile([0.2, 0.4, 0.6, 0.8]).to_numpy() for k in NUM}
Xf, names = design(fit, edges)
beta = logit_fit(Xf, fit.y.to_numpy())
ok = ~np.isnan(fit.r20.to_numpy())
gam = np.linalg.lstsq(Xf[ok], fit.r20.to_numpy()[ok], rcond=None)[0]

print(f"# 逆張りの期待値の指標 k = {K}(戻りの線 = {K - 1} ボラ、待ち 20 分)\n")
print(f"起点: bitFlyer {len(bf):,}(作る {len(fit):,})・Binance {len(bn):,}\n")
print("## 帯の境(作る期間の五分位)\n")
for k in NUM:
    print(f"- {NAME[k]}: " + " / ".join(f"{x:.3g}" for x in edges[k]))
print("\n## 戻る確率の式(対数オッズ。基準 = 各量の真ん中の帯・12〜16 時・買いの側)\n")
print("| 項 | 係数 | 値動きの式の係数(ボラ) |")
print("|---|---|---|")
for n_, a, g in zip(names, beta, gam):
    print(f"| {n_} | {a:+.3f} | {g:+.3f} |")

sets = {"bitFlyer 作る(2016〜2019-12-08)": fit, "bitFlyer 当てる(2019-12-09〜2023)": bf[bf.day >= CUT], "Binance 当てる(2018〜2023)": bn}
print("\n## 当たり具合\n")
print("| 集まり | 起点 | 戻った割合 | 予想の平均 | AUC | Brier(式) | Brier(割合一定) | 20 分の値動き 実際 | 予想 |")
print("|---|---|---|---|---|---|---|---|---|")
pred = {}
for lab, x in sets.items():
    X, _ = design(x, edges)
    p = 1 / (1 + np.exp(-X @ beta)); e = X @ gam
    pred[lab] = (p, e)
    y = x.y.to_numpy(); r = x.r20.to_numpy(); m = ~np.isnan(r)
    print(f"| {lab} | {len(x):,} | {y.mean():.1%} | {p.mean():.1%} | {auc(p, y):.3f} | {np.mean((p - y) ** 2):.4f} | {np.mean((y.mean() - y) ** 2):.4f} | {r[m].mean():+.3f} | {e[m].mean():+.3f} |")

print("\n## 較正(予想した戻る確率の十分位ごと。十分位の境は各集まりの中)\n")
print("| 十分位 | " + " | ".join(f"{lab} 予想 / 実際 / 20 分の値動き" for lab in sets) + " |")
print("|---|" + "---|" * len(sets))
rows = []
for lab, x in sets.items():
    p, e = pred[lab]
    q = pd.qcut(p, 10, labels=False, duplicates="drop")
    df = pd.DataFrame({"q": q, "p": p, "y": x.y.to_numpy(), "r": x.r20.to_numpy()})
    rows.append(df.groupby("q").agg(p=("p", "mean"), y=("y", "mean"), r=("r", "mean")))
for i in range(10):
    print(f"| {i + 1} | " + " | ".join(f"{g.p.iloc[i]:.1%} / {g.y.iloc[i]:.1%} / {g.r.iloc[i]:+.2f}" if i < len(g) else "—" for g in rows) + " |")

print("\n## 2. 年ごとのずれ(実際に戻った割合 − 予想の平均。値動きは 実際 − 予想、ボラ)。区間は日の塊\n")
print("| 年 | bitFlyer 起点 | bitFlyer 戻る: 実際 − 予想 | bitFlyer 値動き: 実際 − 予想 | Binance 起点 | Binance 戻る: 実際 − 予想 | Binance 値動き: 実際 − 予想 |")
print("|---|---|---|---|---|---|---|")
allbf = pd.concat([fit, bf[bf.day >= CUT]])
Xa, _ = design(allbf, edges); pa = 1 / (1 + np.exp(-Xa @ beta)); ea = Xa @ gam
Xb, _ = design(bn, edges); pb = 1 / (1 + np.exp(-Xb @ beta)); eb = Xb @ gam
for yy in range(2016, 2024):
    cells = []
    for x, p, e in ((allbf, pa, ea), (bn, pb, eb)):
        m = (x.y_ == yy).to_numpy()
        if m.sum() == 0:
            cells += ["—", "—", "—"]; continue
        r = x.r20.to_numpy()[m]; ok2 = ~np.isnan(r)
        cells += [f"{m.sum():,}", ci_mean(x.y.to_numpy()[m] - p[m], x.day.to_numpy()[m]),
                  ci_mean(r[ok2] - e[m][ok2], x.day.to_numpy()[m][ok2])]
    print(f"| {yy} | " + " | ".join(cells) + " |")
