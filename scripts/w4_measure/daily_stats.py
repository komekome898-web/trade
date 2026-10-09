"""日ごとの損益の系列から出す軽い測定(リードの測り方の変更、2026-10-02)。

入力: P_t(pnl.py と同じ)と決定の時刻 t、持ち高 e(1 分ごと)。日の境は Asia/Tokyo(measure.daily_rows と同じ)。
出すもの:
  overall   全体の平均: 1 分あたり = ΣP / n(決定の数)、1 日あたり = Σ_d S_d / D(S_d = その日の P の合計、D = 日の数)
  ci        日を塊にした circular block bootstrap(bot.bt.validation.bootstrap.block_bootstrap_ci)、塊 1 日と 5 日、
            1,000 回、種 20261002、95%(百分位)。日の番号を再標本にし、同じ再標本から
              1 日あたり = 再標本の S_d の平均、1 分あたり = 再標本の ΣS_d ÷ 再標本の Σn_d(比の推定)
            を出す。se = 再標本の標準偏差(ddof 1)、MDE = mde(n, sd = se × √n, 5% 両側, 80%, 正規近似)
            (n は 1 日あたりなら D、1 分あたりなら決定の数。測定器の C5 e と同じ式)
  year      暦年(日本時間の日の年)ごとの合計・平均(1 日あたり・1 分あたり)・日の数・決定の数
  weekday   日本時間の曜日(月 = 0)ごと: 日の数・1 日あたりの平均・1 分あたりの平均
  hour_jst  決定 t の日本時間の時ごと: P_t の合計・決定の数・1 分あたりの平均
  frequency 持ち高 != 0 の決定の割合、持ち高が変わった回数(測定器の C5 f と同じ定義)
"""
from __future__ import annotations

import math

import numpy as np

from bot.bt.validation import block_bootstrap_ci, mde

SEED = 20261002
N_RES = 1000
ALPHA, POWER = 0.05, 0.80
NS = 1_000_000_000
DAY_NS = 86_400 * NS
JST = 9 * 3600 * NS


def _boot(S: np.ndarray, n: np.ndarray, L: int) -> dict:
    D = len(S)
    seen = []

    def stat(xs):
        i = xs.astype(np.int64)
        v = (S[i].mean(), S[i].sum() / n[i].sum())
        seen.append(v)
        return float(v[0])

    ci = block_bootstrap_ci([float(i) for i in range(D)], block_len=L, n_resamples=N_RES, seed=SEED, alpha=ALPHA,
                            method="circular", statistic=stat)
    reps = np.array(seen[:N_RES])
    out = {"block_days": L, "n_days": D}
    for k, name, nn in ((0, "per_day_pct", D), (1, "per_minute_pct", int(n.sum()))):
        lo, hi = np.quantile(reps[:, k], [ALPHA / 2, 1 - ALPHA / 2])
        se = float(np.std(reps[:, k], ddof=1))
        out[name] = {"ci": [float(lo), float(hi)], "se": se,
                     "mde": mde(n=nn, sd=se * math.sqrt(nn), alpha=ALPHA, power=POWER, sides=2, approx="normal")}
    assert abs(ci.lo - out["per_day_pct"]["ci"][0]) < 1e-12
    return out


def daily_stats(t_ns: np.ndarray, P: np.ndarray, e_all_decided: np.ndarray) -> dict:
    day = (t_ns + JST) // DAY_NS
    uniq, inv = np.unique(day, return_inverse=True)
    S = np.bincount(inv, weights=P)
    n = np.bincount(inv).astype(float)
    D = len(S)
    out = {"what": "日ごとの損益の系列からの軽い測定(リードの測り方の変更 2026-10-02)。式はこのファイルの formula",
           "formula": __doc__, "seed": SEED, "n_resamples": N_RES,
           "overall": {"n_decisions": int(len(P)), "n_days": D, "per_minute_pct": float(P.sum() / len(P)),
                       "per_day_pct": float(S.mean()), "sum_pct": float(P.sum())},
           "ci": {"block_1d": _boot(S, n, 1), "block_5d": _boot(S, n, 5)}}
    years = (uniq * DAY_NS).astype("datetime64[ns]").astype("datetime64[Y]").astype(np.int64) + 1970
    out["year"] = {str(int(y)): {"n_days": int((years == y).sum()), "n_decisions": int(n[years == y].sum()),
                                  "sum_pct": float(S[years == y].sum()), "per_day_pct": float(S[years == y].mean()),
                                  "per_minute_pct": float(S[years == y].sum() / n[years == y].sum())}
                   for y in np.unique(years)}
    wd = (uniq + 3) % 7
    out["weekday_jst"] = {str(int(w)): {"n_days": int((wd == w).sum()), "per_day_pct": float(S[wd == w].mean()),
                                        "per_minute_pct": float(S[wd == w].sum() / n[wd == w].sum())}
                          for w in range(7) if (wd == w).any()}
    hr = ((t_ns + JST) // (3600 * NS)) % 24
    out["hour_jst"] = {f"{h:02d}": {"n": int((hr == h).sum()), "sum_pct": float(P[hr == h].sum()),
                                    "per_minute_pct": float(P[hr == h].mean()) if (hr == h).any() else None}
                       for h in range(24)}
    out["frequency"] = {"n_decisions": int(len(e_all_decided)), "nonzero_share": float(np.mean(e_all_decided != 0)),
                        "changes": int(np.sum(e_all_decided[1:] != e_all_decided[:-1]))}
    return out
