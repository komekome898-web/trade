"""診断(関門 ② の後、検定の数に入れない): bitFlyer FX_BTC_JPY が海外の 1 分の値動きに追いつく速さの年ごとの変化。
仮説(結果の文書の「なぜ」): カード 2 の短い足のプラスが年とともに縮むのは、bitFlyer が海外に追いつく速さが上がったから。
測るもの(年ごと、海外の市場 V ごと): 1 分の対数の値動き r_bf(m)・r_V(m)(m = 足の始まりの時刻、両方に足がある分だけ)。
  β0 = r_bf(m) を r_V(m) に回帰した傾き(同じ分に付いてくる割合)
  β1 = r_bf(m) を r_V(m-1) に回帰した傾き(海外の 1 分前の動きが次の分に遅れて出る割合)
  β2 = r_bf(m) を r_V(m-2) に回帰した傾き
  (それぞれ単回帰。1 本ずつ。)
bitFlyer の足は c2 の a_1m の npz(封印の門から読んだもの、2017-08-17〜2023-12-17)。海外の終値は封印の門(load_reference)で読む。
"""
import sys, json, numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/w4/measure')
sys.path.insert(0, '/home/user/trade/src')
from common import ROOT, paths, BIN_DIR  # noqa
from datetime import datetime
def to_ns(x): return int(datetime.fromisoformat(x.replace('Z','+00:00')).timestamp())*10**9
from bot.bt.data.reference import load_reference
from bot.research.cards import cardmd
M = '/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/w4/measure/runs/c2_owner_xvenue_wick/a_1m.npz'
z = np.load(M); s_ns = z['start_ns']; c_bf = z['close']
st, _ = cardmd.settings(cardmd.parse(open(f'{ROOT}/docs/RESEARCH/cards/c2_owner_xvenue_wick/CARD.md').read()))
decl = dict(st.declarations)
VEN = {'spot': ('binance_close', BIN_DIR, 'binance_BTCUSDT_1m_{y}.csv.gz', '2017-08-17T15:00:00Z', '2023-12-17T15:00:00Z'),
       'um': ('binance_um_close', 'backtest_data/binance_um_BTCUSDT_1m_20261002', 'binance_um_BTCUSDT_1m_{y}.csv.gz', '2020-01-01T15:00:00Z', '2023-12-17T15:00:00Z'),
       'bitmex': ('bitmex_close', 'backtest_data/bitmex_XBTUSD_1m_from1s_20261002', 'bitmex_XBTUSD_1m_{y}.csv.gz', '2017-08-17T15:00:00Z', '2021-12-31T15:00:00Z')}
print('declared names:', [n for n in decl if 'close' in n], flush=True)
out = {}
for v, (name, d, pat, lo_s, hi_s) in VEN.items():
    lo, hi = to_ns(lo_s), to_ns(hi_s)
    ds = {"name": name, "paths": paths(d, pat, lo, hi), "range_ns": [lo, hi],
          "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip",
                   "time": {"columns": ["open_time"], "unit": "iso", "tz": "UTC"}, "value": "close"}}
    s = load_reference(ROOT, ds, declarations=decl)
    t_v = np.array(s.times_ns, dtype=np.int64); c_v = np.array(s.values, dtype=float)
    MIN = 60 * 10**9
    # 1 分ごとの格子に並べる
    g0 = lo; n = (hi - lo) // MIN
    bf = np.full(n, np.nan); vv = np.full(n, np.nan)
    i = (s_ns - g0) // MIN; k = (i >= 0) & (i < n); bf[i[k]] = c_bf[k]
    j = (t_v - g0) // MIN; k = (j >= 0) & (j < n) & ((t_v - g0) % MIN == 0); vv[j[k]] = c_v[k]
    rb = np.r_[np.nan, np.diff(np.log(bf))]; rv = np.r_[np.nan, np.diff(np.log(vv))]
    years = ((g0 + np.arange(n) * MIN) // 10**9).astype('datetime64[s]').astype('datetime64[Y]').astype(int) + 1970
    res = {}
    for y in np.unique(years):
        row = {}
        for lag in (0, 1, 2):
            x = np.r_[np.full(lag, np.nan), rv[:n - lag]] if lag else rv
            ok = (years == y) & np.isfinite(rb) & np.isfinite(x)
            a, b = rb[ok], x[ok]
            row[f'beta{lag}'] = float((a * b).sum() / (b * b).sum() - 0) if ok.sum() > 1000 else None
            row[f'corr{lag}'] = float(np.corrcoef(a, b)[0, 1]) if ok.sum() > 1000 else None
            row[f'n{lag}'] = int(ok.sum())
        res[int(y)] = row
        print(v, int(y), {k2: (round(x2, 4) if isinstance(x2, float) else x2) for k2, x2 in row.items()}, flush=True)
    out[v] = {'reference': name, 'period': [lo_s, hi_s], 'by_year': res, 'manifest': [list(m) for m in s.manifest]}
json.dump(out, open('/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/w4/diag/leadlag.json', 'w'), ensure_ascii=False, indent=1)
