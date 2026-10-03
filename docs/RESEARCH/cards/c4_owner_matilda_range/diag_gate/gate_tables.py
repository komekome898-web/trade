"""カード 4 の静観の門の診断(L-574)。集計部分。gate_diag.py の probe.npz を読む。

    python3 docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/gate_tables.py <probe.npz の置き場> > gate_tables.out

P = 門の無いカード(no_trend_body)の 1 分ごとの損益(W1 の測定器と同じ e_t × (open_{t+2}/open_{t+1} − 1) × 1e4)。
年・日 = 日本時間(決定の時刻 + 9 時間)。日の数 = その年に決定がある日本時間の日の数。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

JST = 9 * 3600 * 10**9
DAY = 86400 * 10**9
SEED = 20261002


def boot_ci(daily: np.ndarray, n: int = 1000) -> list:
    rng = np.random.default_rng(SEED)
    k = len(daily)
    m = np.array([daily[rng.integers(0, k, k)].mean() for _ in range(n)])
    return [round(float(np.percentile(m, 2.5)), 2), round(float(np.percentile(m, 97.5)), 2)]


def main() -> int:
    z = np.load(os.path.join(sys.argv[1], "probe.npz"))
    bar_t, pnl_bp, r_bp = z["bar_t"], z["pnl_bp"], z["r_bp"]
    rec_t = z["rec_t"]
    idx = np.searchsorted(bar_t, rec_t)
    ok = (idx < len(bar_t)) & (bar_t[np.minimum(idx, len(bar_t) - 1)] == rec_t)
    idx = idx[ok]
    P = pnl_bp[idx]
    E = np.sign(z["exposure"][idx])
    R = r_bp[idx]
    ratio = z["ratio"][ok]
    center, close = z["center"][ok], z["close"][ok]
    fix10, v37 = z["fix10"][ok], z["v37"][ok]
    side = np.sign(close - center)
    t = rec_t[ok]
    day = (t + JST) // DAY
    year = np.array([np.datetime64(int(d), "D").astype(object).year for d in np.unique(day)])
    uday = np.unique(day)
    year_of_day = dict(zip(uday.tolist(), year.tolist()))
    yr = np.vectorize(year_of_day.get)(day)
    years = sorted(set(year.tolist()))
    ndays = {y: int((year == y).sum()) for y in years}
    out = {"n_matched": int(ok.sum()), "n_records": int(len(rec_t)), "P_sum_matched": round(float(P.sum()), 3),
           "P_sum_all": round(float(pnl_bp.sum()), 3), "ndays": ndays}

    def per_day(mask):
        """年ごとの 1 日あたり(bp)と、全期間の日ごとの系列の平均と 95% の幅。"""
        row = {y: round(float(P[mask & (yr == y)].sum()) / ndays[y], 2) for y in years}
        d = np.zeros(len(uday))
        np.add.at(d, np.searchsorted(uday, day[mask]), P[mask])
        row["all"] = round(float(d.mean()), 2)
        row["all_ci"] = boot_ci(d)
        sub = np.isin(uday, [u for u in uday if year_of_day[u] >= 2022])
        row["2022-23"] = round(float(d[sub].mean()), 2)
        row["2022-23_ci"] = boot_ci(d[sub])
        return row

    def share(mask):
        return {y: round(float(mask[yr == y].mean()), 3) for y in years} | {"all": round(float(mask.mean()), 3)}

    held = np.ones(len(P), bool)
    out["all_minutes"] = per_day(held)
    for name, st in (("fix10", fix10), ("v37brk", v37)):
        closed = st != 0
        out[name] = {"share_closed": share(closed), "P_closed": per_day(closed), "P_open": per_day(~closed),
                     # 門が閉じている間の損益を、カードの持ち高の向きで分ける(逆張り = 一方向の動きに逆らう持ち高)
                     "P_closed_against": per_day(closed & (E == -st)), "P_closed_along": per_day(closed & (E == st))}
    # 比の十分位(表示の切り方。門の値ではない)
    fin = np.isfinite(ratio)
    edges = np.percentile(ratio[fin], np.arange(0, 101, 10))
    out["ratio_decile_edges"] = [round(float(e), 2) for e in edges]
    q = np.clip(np.searchsorted(edges[1:-1], ratio, side="right"), 0, 9)
    q[~fin] = 9
    dec = []
    for k in range(10):
        m = q == k
        ex = m & (P != 0)
        dec.append({"decile": k + 1, "lo": round(float(edges[k]), 2), "hi": round(float(edges[k + 1]), 2),
                    "share": share(m), "P_per_day": per_day(m),
                    # 前提の列: 中心から離れた側への次の分の値動き(+ なら続く、− なら戻る)
                    "premise_bp": {y: round(float((side[m & (yr == y)] * R[m & (yr == y)]).mean()), 3)
                                   for y in years} | {"all": round(float((side[m] * R[m]).mean()), 3)},
                    "card_P_per_held_min": round(float(P[ex].mean()), 3) if ex.any() else None})
    out["ratio_deciles"] = dec
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
