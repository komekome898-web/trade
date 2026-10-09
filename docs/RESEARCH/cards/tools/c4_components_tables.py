"""カード 4 の部品の 14 本の表(関門 ② の 1 回目の指摘を受けて作り直し、2026-10-03)。
列の出所: 1 日あたり・区間 = daily_stats.json / 取引・勝率・保有・買い売り = extra.json(pnl.py の規則)/
総量・日の数・年ごとの日の数・2017-08-18 以降・対の差 = daily.csv / 持ち高の大きさの平均 = run.npz。
区間 = 日ごとの系列の circular block bootstrap(bot.bt.validation.bootstrap.block_bootstrap_ci、塊 1 日、1,000 回、種 20261002、95% 百分位)。"""
import csv, json, hashlib, sys
import numpy as np
sys.path.insert(0, 'src')
from bot.bt.validation.bootstrap import block_bootstrap_ci
R = 'docs/RESEARCH/cards/c4_owner_matilda_range/measure'
V = [f"{k}_{r}" for k in ("full", "no_width", "no_trend", "no_time", "no_levels", "follow", "core") for r in ("body", "wick")]
CUT = "2017-08-18"  # CARD.md に登録していた始まり 2017-08-17T15:00Z = 日本時間 2017-08-18
def ci(x):
    c = block_bootstrap_ci([float(v) for v in x], block_len=1, n_resamples=1000, seed=20261002, alpha=0.05, method="circular", statistic="mean")
    return [float(c.lo), float(c.hi)]
def _scale100(v):
    """`*_bp` の鍵の中身(数・数の並び・{ci, se, mde} のような入れ物)の数を全部 / 100 する。"""
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return v / 100
    if isinstance(v, list):
        return [_scale100(x) for x in v]
    if isinstance(v, dict):
        return {k: _scale100(x) for k, x in v.items()}
    return v


def _to_pct(o):
    """L-920 より前の出力の損益の鍵 `*_bp`(率 × 1 万)を `*_pct`(%)に直す。新しい出力はそのまま。"""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if isinstance(k, str) and k.endswith("_bp"):
                out[k[:-3] + "_pct"] = _scale100(v)
            else:
                out[k] = _to_pct(v)
        return out
    if isinstance(o, list):
        return [_to_pct(x) for x in o]
    return o


def daily(v):
    allrows = list(csv.reader(open(f'{R}/{v}/daily.csv')))
    k_ = 100.0 if allrows[0][1] == 'pnl_bp' else 1.0  # L-920 より前の daily.csv は率 × 1 万。% にする
    return {r[0]: float(r[1]) / k_ for r in allrows[1:]}
out = {}
for v in V:
    s = _to_pct(json.load(open(f'{R}/{v}/daily_stats.json'))); x = _to_pct(json.load(open(f'{R}/{v}/extra.json')))
    d = daily(v); days = sorted(d); p = np.array([d[k] for k in days])
    sub = np.array([d[k] for k in days if k >= CUT])
    z = np.load(f'{R}/{v}/run.npz'); e = z['exposure'][z['decided']]
    yd = {}
    for k in days: yd[k[:4]] = yd.get(k[:4], 0) + 1
    out[v] = dict(per_day=s['overall']['per_day_pct'], ci=s['ci']['block_1d']['per_day_pct']['ci'], sum_pct=float(p.sum()), n_days=len(p),
                  sub_per_day=float(sub.mean()), sub_ci=ci(sub), sub_days=len(sub), sub_sum=float(sub.sum()),
                  trades=x['trades']['n'], trades_per_day=x['trades']['per_day'], per_trade=x['trades']['mean_pct'], win=x['trades']['win_rate'],
                  hold_min_med=x['trades']['hold_minutes_median'], long=x['long_short_decisions']['long']['sum_pct'], short=x['long_short_decisions']['short']['sum_pct'],
                  dd=x['drawdown']['max_pct'], mean_abs_e=float(np.mean(np.abs(e))), year_days=yd,
                  npz_sha256=hashlib.sha256(open(f'{R}/{v}/run.npz', 'rb').read()).hexdigest())
for v in V:
    base = 'full_' + v.rsplit('_', 1)[1]
    if v == base: continue
    a, b = daily(v), daily(base); ks = sorted(set(a) & set(b))
    diff = np.array([a[k] - b[k] for k in ks]); dsub = np.array([a[k] - b[k] for k in ks if k >= CUT])
    out[v]['diff_vs_full'] = dict(mean=float(diff.mean()), ci=ci(diff), n=len(diff), sub_mean=float(dsub.mean()), sub_ci=ci(dsub), sub_n=len(dsub))
json.dump(out, open(f'{R}/components_tables.json', 'w'), ensure_ascii=False, indent=1)
print('ok', len(out))
