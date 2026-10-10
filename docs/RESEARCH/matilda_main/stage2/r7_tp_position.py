"""L-967「中心からどれだけ離れた位置で利確するのがいいか」の読み (1)(L-968「(1)だけとりあえずやって」)。新しい走らせではない。

基準の取引ごとに、1 段目だけを持ったとして、利確の値段を 中心 − 向き × k × ボラ(k = 3・2.5・2・1.5・1・0・−1。k = 3 が今の利確、
0 が中心、−1 は中心を 1 ボラ越えた所。今のコードは k ≥ 0 しか置けない)に置き換え、1 分足の道筋の上で先に何が起きるかをたどる:
  - 利確の指値に届く → 利確(届いた値段。足の始まりで越えていれば始値)
  - 損の側のブレイクの線に届く → ブレイクの逆指値(線の値段。始まりで越えていれば始値)
  - 足が閉じた時点で、終値がどちらかのブレイクの線の外(R12)・反対側の建ての線(中心 ± 4 ボラ)の外(R10 イ)・1 段目の足の終わりから 40 分を超えた(R10 ロ)→ 次の足の始値で成行
線(中心・ボラ・ブレイクの線)は基準の走らせの足ごとの値(r7_snap_dump.py の書き出し)を、その足の間だけ使う(戦略と同じ)。
利確の緩め(R9): 足が閉じた時点で 20 分を超えた、または建値が中心を越えた側にあるときは、利確を「目標と利益 1 円の値段の悪い方」にする
(緩める前は良い方)。足の中の道筋は 走らせ と同じ(前の終値 → 始値 → 陽線は安値 → 高値、陰線は高値 → 安値 → 終値)。
入らないもの(目安である理由): 2 段目から先の段(平均の建値と量が変わる)・ブレイク中の建てない決まり(持ち高の違いで建つ取引が変わる)。
確かめ: 基準で 1 段のまま閉じた取引は、k = 3 の読みが基準の損益と一致するはず(数を出す)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/r7_tp_position.py <r7 の置き場> > docs/RESEARCH/matilda_main/stage2/r7_tp_position.out
"""
import glob
import sys

import numpy as np
import pandas as pd
from numba import njit

sys.path.insert(0, "src")
from bot.bt.simple import read_bars  # noqa: E402

SEAL = "2023-12-17T15:00:00+00:00"
FILES = sorted(f for f in glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz")
               if int(f[-11:-7]) <= 2023)
MIN = 60_000_000_000
KS = np.array([3.0, 2.5, 2.0, 1.5, 1.0, 0.0, -1.0])
CUT = "2019-12-09"


def load_bars():
    ts, pts, prevs = [], [], []
    prev = None
    for b in read_bars(FILES, SEAL):
        t, op, hi, lo, cl = b[0], float(b[1]), float(b[2]), float(b[3]), float(b[4])
        if op == cl and (prev is None or op == prev):
            continue
        if cl > op or (cl == op and op < prev):
            p = (op, lo, hi, cl)
        else:
            p = (op, hi, lo, cl)
        ts.append(t)
        pts.append(p)
        prevs.append(np.nan if prev is None else prev)
        prev = cl
    tsn = ((pd.to_datetime(pd.Series(ts), utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta("1ns")).to_numpy(dtype=np.int64)
    print(f"足 {len(tsn):,} 本・最初 {ts[0]} = {tsn[0]} ns")  # 単位の取り違えの確かめ(research-protocol §6)
    return tsn, np.array(pts), np.array(prevs)


@njit(cache=True)
def walk(i0, side, px, qty, tsn, pts, prevs, sidx, center, vola, bu, bd, k):
    """1 段目の足 i0 で px に約定した取引を k の利確でたどる。返すのは (損益の円, 理由 0 利確 1 ブレイク 2 成行 3 データの終わり)。"""
    n = tsn.shape[0]
    t0 = tsn[i0] + 60_000_000_000
    one = px + side * 1.0 / qty
    loosen = False
    i = i0
    first = True
    while i < n:
        j = sidx[i]
        if j < 0:
            return 0.0, 3
        c, v = center[j], vola[j]
        line = bd[j] if side == 1 else bu[j]
        tgt = c - side * k * v
        if side == 1:
            tp = min(tgt, one) if loosen else max(tgt, one)
        else:
            tp = max(tgt, one) if loosen else min(tgt, one)
        tp = np.floor(tp)  # 注文の値段は刻み 1 円に切り下げ(走らせの floor_tick と同じ)
        if not np.isnan(line):
            line = np.floor(line)
        has_line = not np.isnan(line) and side * (tp - line) > 0
        o, x1, x2, cl = pts[i, 0], pts[i, 1], pts[i, 2], pts[i, 3]
        seq = np.array([prevs[i], o, x1, x2, cl])
        s0 = 1
        if first:
            # 1 段目の約定点を探す: 買いは道筋が px 以下に届いた最初の区間、売りは px 以上
            s0 = -1
            for s in range(1, 5):
                a, b = seq[s - 1], seq[s]
                if s == 1:
                    if not np.isnan(a) and side * (b - px) <= 0:
                        s0 = 1
                        break
                elif side * (min(a, b) - px) <= 0 if side == 1 else side * (max(a, b) - px) <= 0:
                    s0 = s
                    break
            if s0 < 0:
                return 0.0, 3
            seq[s0 - 1] = px  # 約定した点から先をたどる
            if s0 == 1:
                seq[0] = px
            first = False
        for s in range(s0, 5):
            a, b = seq[s - 1], seq[s]
            gap = s == 1
            # 利確: 買いは道筋が tp 以上に届く
            if side == 1:
                hit_tp = max(a, b) >= tp if not np.isnan(a) else b >= tp
                hit_ln = has_line and (min(a, b) <= line if not np.isnan(a) else b <= line)
            else:
                hit_tp = min(a, b) <= tp if not np.isnan(a) else b <= tp
                hit_ln = has_line and (max(a, b) >= line if not np.isnan(a) else b >= line)
            if gap and not np.isnan(a):
                # 始まりで越えていれば始値(前の終値の時点で既に越えている注文も始値)
                if side * (o - tp) >= 0:
                    return qty * side * (o - px), 0
                if has_line and side * (o - line) <= 0:
                    return qty * side * (o - px), 1
                continue
            if hit_tp:
                return qty * side * (tp - px), 0
            if hit_ln:
                return qty * side * (line - px), 1
        # 足が閉じた(_rejudge: その足の線で): R12 終値がどちらかのブレイクの線の外 → 成行 / R10 イ 終値が反対側の建ての線の外 → 成行
        nxt = pts[i + 1, 0] if i + 1 < n else np.nan
        if (not np.isnan(bu[j]) and cl >= bu[j]) or (not np.isnan(bd[j]) and cl <= bd[j]):
            return (qty * side * (nxt - px), 1) if i + 1 < n else (0.0, 3)
        if side * (cl - (c + side * 4.0 * v)) >= 0:
            return (qty * side * (nxt - px), 2) if i + 1 < n else (0.0, 3)
        # 新しい線で(_place): R10 ロ 40 分を超えた → 成行、R9 緩め
        mins = (tsn[i] + 60_000_000_000 - t0) // 60_000_000_000
        if mins > 40:
            if i + 1 < n:
                return qty * side * (nxt - px), 2
            return 0.0, 3
        jn = sidx[i + 1] if i + 1 < n else -1
        cn = center[jn] if jn >= 0 else c
        if jn >= 0 and side * (cl - (cn + side * 4.0 * vola[jn])) >= 0:  # _rejudge_new の R10 イ(新しい線で)
            return (qty * side * (nxt - px), 2) if i + 1 < n else (0.0, 3)
        loosen = mins > 20 or side * (px - cn) > 0
        i += 1
    return 0.0, 3


def main(d):
    tsn, pts, prevs = load_bars()
    sn = np.load(f"{d}/snaps.npz")
    # 足 i の間に使う線 = 足 i の始まり以前に閉じた最後の窓の線(足が抜けた分・飛ばした足があっても、戦略は前の線を使い続ける)
    sidx = np.searchsorted(sn["end"], tsn, side="right").astype(np.int64) - 1
    e = pd.read_csv(f"{d}/entries.csv")
    bix = {int(t): i for i, t in enumerate(tsn)}
    tr = pd.read_csv("backtest_runs_shared/matilda_main_trades/base/trades.csv.gz")
    e["entry_t"] = pd.to_datetime(e.start + MIN, utc=True)
    tr["entry_t"] = pd.to_datetime(tr.entry_t, utc=True)
    tr = tr.merge(e[["entry_t", "start", "px", "qty"]], on="entry_t", how="left")
    tr["i0"] = tr.start.map(lambda s: bix.get(int(s), -1))
    tr["half"] = np.where(tr.signal_t.str[:10] >= CUT, "後半", "前半")
    tr["day"] = tr.signal_t.str[:10]
    args = (tsn, pts, prevs, sidx, sn["center"], sn["vola"], sn["bu"], sn["bd"])
    for k in KS:
        res = [walk(int(a), int(s), float(p), float(q), *args, float(k)) for a, s, p, q in zip(tr.i0, tr.side, tr.px, tr.qty)]
        tr[f"pnl_{k:g}"] = [r[0] for r in res]
        tr[f"why_{k:g}"] = [r[1] for r in res]
    return tr


if __name__ == "__main__":
    tr = main(sys.argv[1])
    tr.to_pickle(f"{sys.argv[1]}/tp_walk.pkl")
    one = tr[tr.levels == 1]
    ok = (one["pnl_3"] - one.pnl_jpy).abs() < 0.01
    print(f"確かめ: 基準で 1 段のまま閉じた取引 {len(one):,} 本のうち、k = 3 の読みが基準の損益と 0.01 円以内で一致 {ok.sum():,} 本({ok.mean():.1%})")
    bad = one[~ok]
    print("一致しない取引の基準の閉じ方:", bad.exit_reason.value_counts().to_dict(), " 読みの理由:", bad["why_3"].value_counts().to_dict())
    days = {"前半": pd.date_range("2015-12-01", "2019-12-08").strftime("%Y-%m-%d"), "後半": pd.date_range(CUT, "2023-12-17").strftime("%Y-%m-%d")}
    rng = np.random.default_rng(20261004)

    def ci(x, h):
        v = x.groupby(tr.loc[x.index, "day"]).sum().reindex(days[h], fill_value=0).to_numpy()
        nn = len(v)
        st = rng.integers(0, nn, size=(1000, int(np.ceil(nn / 5))))
        idx = (st[:, :, None] + np.arange(5)).reshape(1000, -1)[:, :nn] % nn
        m = v[idx].mean(axis=1)
        return f"{v.mean():+.1f} [{np.percentile(m, 2.5):+.1f}, {np.percentile(m, 97.5):+.1f}]"

    print("\n## 1 段目だけを持ったとき、利確を 中心 − 向き × k × ボラ に置いた読み(基準の取引 348,783 本の 1 段目)\n")
    print("| k(中心からのボラ) | 半分 | 利確 本(割合) | ブレイク 本 | 成行 本 | 円/日 [区間] | 利確 1 本の円 | ブレイク 1 本の円 | 成行 1 本の円 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for k in KS:
        for h in ("前半", "後半"):
            x = tr[(tr.half == h) & (tr[f"why_{k:g}"] != 3)]
            w, pn = x[f"why_{k:g}"], x[f"pnl_{k:g}"]
            print(f"| {k:g} | {h} | {(w == 0).sum():,}({(w == 0).mean():.1%}) | {(w == 1).sum():,} | {(w == 2).sum():,} | {ci(pn, h)} | "
                  f"{pn[w == 0].mean():+.1f} | {pn[w == 1].mean():+.1f} | {pn[w == 2].mean():+.1f} |")
    print("\n## 同じ取引どうしの差: k − 3(今の利確)の円/日 [区間](日の塊で日を選び直す)\n")
    print("| k | 前半 | 後半 |")
    print("|---|---|---|")
    for k in KS[1:]:
        r = []
        for h in ("前半", "後半"):
            x = tr[(tr.half == h) & (tr[f"why_{k:g}"] != 3) & (tr["why_3"] != 3)]
            r.append(ci(x[f"pnl_{k:g}"] - x["pnl_3"], h))
        print(f"| {k:g} | {r[0]} | {r[1]} |")
    print("\n(データの終わり・約定点を探せなかった取引は除いた: " + ", ".join(f"k={k:g} {(tr[f'why_{k:g}'] == 3).sum()}" for k in KS) + ")")
