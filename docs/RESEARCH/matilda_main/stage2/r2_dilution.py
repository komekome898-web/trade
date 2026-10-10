"""段 2 の読み R2(STAGE2_MATERIALS §9.1、K-375。L-963「1を裏で走らせながら」)。
幅の下の門 0.5133%(range_lo_p50)× 線を近づける(break_dist_0.25)の相互作用が、
(a) 門で取引が減る分の希釈か (b) 同じ取引に 2 回効く重なりか を、4 本の取引の行で数える。
分け方: 基準の合図(signal_t)を、門の本にもある = 「門で残る」/ 門の本に無い = 「門で外れる」に分ける
(門の本に無い合図には、持ち高の違いで建たなかった合図も入る。gate_overlap.py と同じ近似)。
線を近づける効き(break_dist_0.25 − 基準)を、合図で突き合わせた取引の差と、片方だけの取引の和に分け、残る・外れるの側ごとに足す。
希釈なら: 相互作用 ≈ −(外れる側の線の効き)。重なりなら: (組 − 門) が (残る側の線の効き) と違う。
日数は暦日(前半 2015-12-01〜2019-12-08、計 2,939 日 = 段 1 の分析と同じ、後半 2019-12-09〜2023-12-17)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/r2_dilution.py > docs/RESEARCH/matilda_main/stage2/r2_dilution.out
"""
import pandas as pd

T = "backtest_runs_shared/matilda_main_trades"
CUT = "2019-12-09"
DAYS = {"前半": (pd.Timestamp(CUT) - pd.Timestamp("2015-12-01")).days,
        "後半": (pd.Timestamp("2023-12-17") - pd.Timestamp(CUT)).days + 1}


def load(r):
    d = pd.read_csv(f"{T}/{r}/trades.csv.gz", usecols=["signal_t", "pnl_jpy"])
    d["half"] = (d.signal_t.str[:10] >= CUT).map({False: "前半", True: "後半"})
    return d


b, g, l, c = (load(r) for r in ("base", "range_lo_p50", "break_dist_0.25", "range_lo_p50_break_dist_0.25"))
kept = set(g.signal_t)


def effect(x, y, keyset):
    """y − x を、合図が keyset に入る側(残る)と入らない側(外れる)に分けて返す。片方だけの取引も、その合図の側に入れる。"""
    out = {}
    for h in ("前半", "後半"):
        xx, yy = x[x.half == h], y[y.half == h]
        m = xx.merge(yy, on="signal_t", how="outer", suffixes=("_x", "_y")).fillna({"pnl_jpy_x": 0, "pnl_jpy_y": 0})
        m["d"] = m.pnl_jpy_y - m.pnl_jpy_x
        m["both"] = m.signal_t.isin(set(xx.signal_t)) & m.signal_t.isin(set(yy.signal_t))
        m["k"] = m.signal_t.isin(keyset)
        for k, lab in ((True, "残る"), (False, "外れる")):
            s = m[m.k == k]
            out[(h, lab)] = (s.d.sum(), s[s.both].d.sum(), len(s[s.both]), s[~s.both & s.signal_t.isin(set(yy.signal_t))].pnl_jpy_y.sum(),
                             len(s[~s.both & s.signal_t.isin(set(yy.signal_t))]), -s[~s.both & s.signal_t.isin(set(xx.signal_t))].pnl_jpy_x.sum(),
                             len(s[~s.both & s.signal_t.isin(set(xx.signal_t))]))
    return out


e_line = effect(b, l, kept)          # 門の無いところでの線の効き
e_comb = effect(g, c, kept)          # 門のあるところでの線の効き(全部「残る」側に入るはず)
print("## 線を近づける効きを、門で残る合図・外れる合図に分ける(円の和と 1 日あたり)\n")
print("| 比べ | 半分 | 側 | 差の和(円) | 円/日 | うち両方にある取引の差(本) | 比べ先だけの取引の和(本) | 比べ元だけの取引の和の負(本) |")
print("|---|---|---|---|---|---|---|---|")
for name, e in (("break_dist_0.25 − 基準", e_line), ("組 − range_lo_p50", e_comb)):
    for (h, lab), v in e.items():
        print(f"| {name} | {h} | {lab} | {v[0]:+,.0f} | {v[0] / DAYS[h]:+.1f} | {v[1]:+,.0f}({v[2]:,}) | {v[3]:+,.0f}({v[4]:,}) | {v[5]:+,.0f}({v[6]:,}) |")
print("\n## 相互作用と、希釈の見込みとの比べ(円/日)\n")
print("| 半分 | 日数 | 線の効き(門なし) | 線の効き(門あり) | 相互作用 = 門あり − 門なし | 希釈なら = −(外れる側の線の効き) | 残り = 相互作用 − 希釈(= 門あり − 残る側の線の効き。門ありの外れる側はほぼ 0) |")
print("|---|---|---|---|---|---|---|")
for h in ("前半", "後半"):
    a = (e_line[(h, "残る")][0] + e_line[(h, "外れる")][0]) / DAYS[h]
    k = e_line[(h, "残る")][0] / DAYS[h]
    w = (e_comb[(h, "残る")][0] + e_comb[(h, "外れる")][0]) / DAYS[h]
    dil = -e_line[(h, "外れる")][0] / DAYS[h]
    print(f"| {h} | {DAYS[h]} | {a:+.1f} | {w:+.1f} | {w - a:+.1f} | {dil:+.1f} | {w - a - dil:+.1f} |")
