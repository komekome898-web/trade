"""前提の直接の測り # 6 の読み口(週ごとの行 weeks.csv.gz だけから。値動きの足は読まない)。

出すもの:
1. 主の量の写し(重み付きの戻りの割合 本体 − 対照)を週の行から作り直し、TABLES.md と一致するかを確かめる。
2. g の符号ごと(g > 0 / g < 0)の重み付きの戻りの割合 本体・対照・差。usdjpy の売値(BID)の偏りの確かめ
   (分析の文書 P の (1): 週明けの BID が中ほどより下に付くなら、g < 0 の週で戻り・g > 0 の週で続きに見える)。
3. |g| の帯(前半の週の |g| の 3 分位で境を決め、全期間・前半・後半に当てる)ごとの同じ量。
4. g に比例する分: 傾き b = Σ(m·g) ÷ Σ(g²)(原点を通る m の g への回帰)。−b = g のうち戻した割合。本体・対照・差。
区間: 週を 1 件として選び直す(iid、1,000 回、種 20261006)。台本の区間(日の塊の循環 5 日)とは作り方が違う。
本体と対照の差は同じ抽き直しで作る(対)。
対照の重み付きの分子 = ctrl_ratio × |g|(ctrl_ratio = 対照の 1 時間ごとの −m_c ÷ g の週の平均、g は週で同じなので
−m_c·sign g の週の平均 = ctrl_ratio × |g|)。対照の傾きの分子 = −ctrl_ratio × g²(m_c·g の週の平均)。
"""
import csv, gzip, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "weeks.csv.gz")
SEED, REPS = 20261006, 1000

rows = list(csv.DictReader(gzip.open(SRC, "rt")))
day = np.array([r["day"] for r in rows])
n = len(rows)
half = np.arange(n) >= n // 2   # 前半 141・後半 141(台本の境と同じ数)

def col(v, k):
    name = f"{k}_{v}_bp" if k in ("g", "m", "adv") else f"{k}_{v}"
    return np.array([float(r[name]) if r[name] not in ("", "nan") else np.nan for r in rows])

def boot(stat, idx):
    rng = np.random.default_rng(SEED)
    est = stat(idx)
    vals = []
    for _ in range(REPS):
        s = rng.choice(idx, size=len(idx), replace=True)
        vals.append(stat(s))
    vals = np.array(vals)
    return est, np.nanpercentile(vals, 2.5), np.nanpercentile(vals, 97.5)

def fmt(t, nd=3):
    e, lo, hi = t
    return f"{e:+.{nd}f} [{lo:+.{nd}f}, {hi:+.{nd}f}]"

out = ["# # 6 の読み口(週の行から。`week_reader.py`)", "",
       "区間 = 週を 1 件として選び直す(iid、1,000 回、種 20261006)。本体と対照の差は同じ抽き直し。",
       "重み付きの戻りの割合 = Σ(−m·sign g) ÷ Σ|g|。傾き −b = −Σ(m·g) ÷ Σ(g²)(g のうち戻した割合。g に比例する分)。",
       "|g| の帯の境は前半の週の |g| の 3 分位(前半で決めて後半に当てる。全期間・前半の行は帯の境が標本の中)。", ""]
periods = {"全期間": np.ones(n, bool), "前半": ~half, "後半": half}
for v in ("btc", "usdjpy"):
    g = col(v, "g"); m = col(v, "m"); cr = col(v, "ctrl_ratio")
    ok = np.isfinite(g) & np.isfinite(m) & (g != 0)
    okc = ok & np.isfinite(cr)
    w_b = -m * np.sign(g); w_c = cr * np.abs(g)
    def wr(i, which):
        i = i[okc[i]]
        num = (w_b if which == "b" else w_c)[i].sum()
        return num / np.abs(g[i]).sum()
    def slope(i, which):
        i = i[okc[i]]
        num = (m * g)[i].sum() if which == "b" else (-cr * g * g)[i].sum()
        return -num / (g[i] ** 2).sum()
    out += [f"## {v}", "", "### 1・4 主の量の写しと g に比例する分", "",
            "| 期間 | 週 | 重み付き 本体 | 対照 | 本体 − 対照 | 傾き −b 本体 | 対照 | 本体 − 対照 |", "|---|---|---|---|---|---|---|---|"]
    for p, mask in periods.items():
        idx = np.where(mask)[0]
        out.append(f"| {p} | {int(okc[idx].sum())} | {fmt(boot(lambda i: wr(i,'b'), idx))} | {fmt(boot(lambda i: wr(i,'c'), idx))} | "
                   f"{fmt(boot(lambda i: wr(i,'b') - wr(i,'c'), idx))} | {fmt(boot(lambda i: slope(i,'b'), idx))} | "
                   f"{fmt(boot(lambda i: slope(i,'c'), idx))} | {fmt(boot(lambda i: slope(i,'b') - slope(i,'c'), idx))} |")
    out += ["", "### 2 g の符号ごと(重み付きの戻りの割合)", "",
            "| 期間 | g の符号 | 週 | 本体 | 対照 | 本体 − 対照 |", "|---|---|---|---|---|---|"]
    for p, mask in periods.items():
        for sname, smask in (("g > 0", g > 0), ("g < 0", g < 0)):
            idx = np.where(mask & smask)[0]
            out.append(f"| {p} | {sname} | {int(okc[idx].sum())} | {fmt(boot(lambda i: wr(i,'b'), idx))} | "
                       f"{fmt(boot(lambda i: wr(i,'c'), idx))} | {fmt(boot(lambda i: wr(i,'b') - wr(i,'c'), idx))} |")
    q = np.nanpercentile(np.abs(g[~half & ok]), [100/3, 200/3])
    out += ["", f"### 3 |g| の帯(境 = 前半の 3 分位 {q[0]:.2f}・{q[1]:.2f} bp)", "",
            "| 期間 | 帯 | 週 | |g| の中央値 bp | 本体 | 対照 | 本体 − 対照 |", "|---|---|---|---|---|---|---|"]
    bands = {"小": np.abs(g) < q[0], "中": (np.abs(g) >= q[0]) & (np.abs(g) < q[1]), "大": np.abs(g) >= q[1]}
    for p, mask in periods.items():
        for bname, bmask in bands.items():
            idx = np.where(mask & bmask & ok)[0]
            out.append(f"| {p} | {bname} | {int(okc[idx].sum())} | {np.median(np.abs(g[idx])):.1f} | {fmt(boot(lambda i: wr(i,'b'), idx))} | "
                       f"{fmt(boot(lambda i: wr(i,'c'), idx))} | {fmt(boot(lambda i: wr(i,'b') - wr(i,'c'), idx))} |")
    # 5 向きによらない平均の動き(表を見た後に足した。探索)と、それを引いた戻りの割合
    mc = -cr * g   # 対照の 1 時間の動きの週の平均(bp)
    def dmean(i, which):
        i = i[okc[i]]
        return (m if which == "b" else mc)[i].mean()
    def wr_dm(i, which):
        i = i[okc[i]]
        x = m if which == "b" else mc
        return (-(x[i] - x[i].mean()) * np.sign(g[i])).sum() / np.abs(g[i]).sum()
    out += ["", "### 5 向きによらない平均の動き D(bp/週)と、D を引いた重み付きの戻りの割合(表を見た後に足した。探索)", "",
            "D = 1 時間の動き m の週の平均(g の符号を掛けない)。D を引いた形 = Σ(−(m − D)·sign g) ÷ Σ|g|(D は抽き直しの中で作る)。",
            "", "| 期間 | D 本体 | D 対照 | D 本体 − 対照 | D を引いた 本体 | 対照 | 本体 − 対照 |", "|---|---|---|---|---|---|---|"]
    for p, mask in periods.items():
        idx = np.where(mask)[0]
        out.append(f"| {p} | {fmt(boot(lambda i: dmean(i,'b'), idx), 2)} | {fmt(boot(lambda i: dmean(i,'c'), idx), 2)} | "
                   f"{fmt(boot(lambda i: dmean(i,'b') - dmean(i,'c'), idx), 2)} | {fmt(boot(lambda i: wr_dm(i,'b'), idx))} | "
                   f"{fmt(boot(lambda i: wr_dm(i,'c'), idx))} | {fmt(boot(lambda i: wr_dm(i,'b') - wr_dm(i,'c'), idx))} |")
    # 5b(監査役 1 回目の止める 1): 全週の平均 D を引いてから符号で分ける形は恒等式(Σ(m − D) = 0 なので 2 群の分子が
    # 同じ大きさになる)。そのため出さない。代わりに、共通の切片と、上げた週・下げた週で別の傾きを持つ回帰
    # m = a + b⁺·max(g, 0) + b⁻·min(g, 0)(最小二乗)の −b⁺・−b⁻ を出す(恒等式にならない。傾きは各群の中の |g| の
    # ばらつきから決まる)。対照も同じ回帰を m_c で。表を見た後に足した(探索)。
    gp, gn = np.maximum(g, 0), np.minimum(g, 0)
    def slopes(i, which):
        i = i[okc[i]]
        y = (m if which == "b" else mc)[i]
        X = np.column_stack([np.ones(len(i)), gp[i], gn[i]])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        return -coef[1], -coef[2], coef[0]
    out += ["", "### 5b 共通の切片と、符号ごとの傾き(m = a + b⁺·g⁺ + b⁻·g⁻。−b = g のうち戻した割合。表を見た後に足した。探索)", "",
            "| 期間 | 上げた週 −b⁺ 本体 − 対照 | 下げた週 −b⁻ 本体 − 対照 | 下げた週 − 上げた週 | 切片 a 本体 − 対照(bp) |", "|---|---|---|---|---|"]
    for p, mask in periods.items():
        idx = np.where(mask)[0]
        c1 = boot(lambda i: slopes(i,'b')[0] - slopes(i,'c')[0], idx)
        c2 = boot(lambda i: slopes(i,'b')[1] - slopes(i,'c')[1], idx)
        c3 = boot(lambda i: (slopes(i,'b')[1] - slopes(i,'c')[1]) - (slopes(i,'b')[0] - slopes(i,'c')[0]), idx)
        c4 = boot(lambda i: slopes(i,'b')[2] - slopes(i,'c')[2], idx)
        out.append(f"| {p} | {fmt(c1)} | {fmt(c2)} | {fmt(c3)} | {fmt(c4, 2)} |")
    # 2b(監査役 1 回目の直す 4): D を引く前の符号ごとの差(下げた週 − 上げた週)の区間。分子の差は定義から n × D に等しい
    def sgn_diff(i):
        i = i[okc[i]]
        def grp(j):
            return ((w_b[j] - w_c[j]).sum()) / np.abs(g[j]).sum()
        return grp(i[g[i] < 0]) - grp(i[g[i] > 0])
    out += ["", "### 2b 重み付きの戻りの割合 本体 − 対照 の、下げた週 − 上げた週(D を引く前)", "",
            "| 期間 | 下げた週 − 上げた週 |", "|---|---|"]
    for p, mask in periods.items():
        out.append(f"| {p} | {fmt(boot(sgn_diff, np.where(mask)[0]))} |")
    # 7(監査役 1 回目の直す 8): 週ごとの寄与の集まり。寄与 c_w = (−m·sign g) − 対照の (−m_c·sign g)(bp)。主の量 = Σ c_w ÷ Σ|g|
    cw = (w_b - w_c)
    o = np.where(okc)[0]
    order = o[np.argsort(-cw[o])]
    tot = cw[o].sum(); den = np.abs(g[o]).sum()
    out += ["", "### 7 週ごとの寄与の集まり(全期間。寄与 = (−m·sign g) − 対照の同じ量、bp)", "",
            f"寄与の和 {tot:+.1f} bp・Σ|g| {den:.1f} bp・主の量 {tot/den:+.3f}。寄与が正の週 {int((cw[o] > 0).sum())} / {len(o)}。", "",
            "| 外した週 | 外した週の寄与の和 bp | 残りの主の量 |", "|---|---|---|"]
    for k in (1, 3, 5, 10, 14, 28):
        top = order[:k]; rest = np.setdiff1d(o, top)
        out.append(f"| 寄与の上位 {k} 週 | {cw[top].sum():+.1f} | {cw[rest].sum() / np.abs(g[rest]).sum():+.3f} |")
    for k in (5, 14):
        bot = order[::-1][:k]; rest = np.setdiff1d(o, bot)
        out.append(f"| 寄与の下位 {k} 週 | {cw[bot].sum():+.1f} | {cw[rest].sum() / np.abs(g[rest]).sum():+.3f} |")
    out += ["", "半分ごと(寄与の上位 k 週を外した主の量と区間。上位を外すと必ず下がる向きの操作なので、検定ではなく集まりの記述):", "",
            "| 半分 | 外さない | 上位 1 | 上位 3 | 上位 5 | 上位 7 | 上位 14 |", "|---|---|---|---|---|---|---|"]
    for p, mask in (("前半", ~half), ("後半", half)):
        oo = np.where(mask & okc)[0]; ordh = oo[np.argsort(-cw[oo])]
        cells = []
        for k in (0, 1, 3, 5, 7, 14):
            rest = np.setdiff1d(oo, ordh[:k])
            cells.append(fmt(boot(lambda i: cw[i].sum() / np.abs(g[i]).sum(), rest)))
        out.append(f"| {p} | " + " | ".join(cells) + " |")
    top5 = order[:5]
    out.append("")
    out.append("寄与の上位 5 週(r の日・g bp・m bp・寄与 bp): " + "; ".join(f"{day[j]} {g[j]:+.0f} {m[j]:+.0f} {cw[j]:+.0f}" for j in top5))
    # 6 後半 − 前半(主の量。2 つの半分をそれぞれ選び直した差)
    i1, i2 = np.where(~half)[0], np.where(half)[0]
    rng = np.random.default_rng(SEED)
    def dd(a, b): return (wr(b,'b') - wr(b,'c')) - (wr(a,'b') - wr(a,'c'))
    bs = [dd(rng.choice(i1, len(i1)), rng.choice(i2, len(i2))) for _ in range(REPS)]
    out += ["", "### 6 主の量の 後半 − 前半", "", f"{dd(i1, i2):+.3f} [{np.percentile(bs, 2.5):+.3f}, {np.percentile(bs, 97.5):+.3f}](2 つの半分をそれぞれ選び直した差)", ""]
open(os.path.join(HERE, "week_reader.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
