"""族の分析の文書に写す表を、読み口の出力(diag_tables.json・diag_paths.json)と取引の行から 1 つの md にまとめる(L-907)。
新しい計算は 2 つだけ: (1) 保有 0 分の帯(1 段目と同じ足で閉じた取引)と 0 分超 の前半・後半の 1 日あたり(D3 の保有時間の帯を
半分に分けたもの)、(2) 本 − 基準 の日ごとの差の前半・後半(D7)。どちらも境 = 後半の最初の日 2019-12-09(L-903 の境の統一)、
区間は読み口の mean_ci(日の塊 5・1,000 回・種 20261004)。円 = bp × 20(pnl_bp は口座 20 万円に対する bp)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/fam_tables.py <族> <本> [<本> ...] > docs/RESEARCH/matilda_main/<族>/fam_tables.md
"""
import json
import sys

sys.path.insert(0, "scripts/analysis")
import diag_tables as dt  # noqa: E402

T = "backtest_runs_shared/matilda_main_trades/"
R = "backtest_runs_shared/matilda_main/"
M = "docs/RESEARCH/matilda_main/"
CUT = "2019-12-09"
fam, names = sys.argv[1], sys.argv[2:]
runs = names + ["base"]


def y(v, nd=0):
    return "—" if v is None else f"{v * 20:+,.{nd}f}"


def ci(r, nd=0):
    if r.get("mean") is None:
        return "—"
    if r.get("lo") is None:
        return y(r["mean"], nd)
    return f"{y(r['mean'], nd)} [{y(r['lo'], nd)}, {y(r['hi'], nd)}]"


def mv(r, nd=2):
    return "—" if r.get("per_trade") is None else f"{r['per_trade']:+.{nd}f} [{r['lo']:+.{nd}f}, {r['hi']:+.{nd}f}]"


tab = {n: json.load(open(M + n + "/diag_tables.json")) for n in runs}
pth = {}
for n in runs:
    try:
        pth[n] = json.load(open(M + n + "/diag_paths.json"))
    except FileNotFoundError:
        pth[n] = None
base_p = json.load(open(R + "base/run.json"))["params"]

print(f"# 族 {fam} の表(`fam_tables.py` が出した。手で書いていない)\n")
print("## D0 引数と取引\n")
print("| 本 | 基準と違う引数 | 期間の始まり | 閉じた取引 | 損益の和 円 | 有効期間(分)を越えた建て | D1 の境 |")
print("|---|---|---|---|---|---|---|")
for n in runs:
    p = json.load(open(R + n + "/run.json"))["params"]
    diff = {k: p[k] for k in p if p[k] != base_p.get(k)}
    s = json.load(open(T + n + "/summary.json"))
    z = tab[n]["d0"]
    sd = z.get("signal_delay") or {}
    late = sd.get("late", {}).get("trades")
    seg = tab[n]["d1"]["segments"]
    print(f"| {n} | `{json.dumps(diff)}` | {z['period'][0][:10]} | {s['check']['closed_trades']:,} | {s['check']['pnl_jpy']} | "
          f"{late} / {sd.get('valid_min')} | {seg.get('cut', seg['second']['from'])}({seg.get('cut_source', '日数の真ん中')}) |")

print("\n## D1 前半・後半(1 日あたり 円 [区間](MDE))\n")
print("| 本 | 前半 | 後半 | 後半 − 前半 | 結果 | 全期間 |")
print("|---|---|---|---|---|---|")
for n in runs:
    sg = tab[n]["d1"]["segments"]
    allr = tab[n]["d1"]["rows"][0]
    print(f"| {n} | {ci(sg['first'])}({y(sg['first']['mde'])}) | {ci(sg['second'])}({y(sg['second']['mde'])}) | {ci(sg['diff'])} | "
          f"{sg['outcome']} | {ci(allr)} |")
years = [r["label"] for r in tab["base"]["d1"]["rows"][1:]]
print("\n年ごと(1 日あたり 円。括弧は区間が 0 を)\n")
print("| 本 | " + " | ".join(years) + " |")
print("|---|" + "---|" * len(years))
for n in runs:
    rows = {r["label"]: r for r in tab[n]["d1"]["rows"]}
    print(f"| {n} | " + " | ".join(f"{y(rows[k]['mean'])}({rows[k]['zero']})" if k in rows else "—" for k in years) + " |")

print("\n## D3 保有 0 分の帯(1 段目と同じ足で閉じた)と 0 分超 の前半・後半(1 日あたり 円 [区間]、境 2019-12-09)\n")
print("| 本 | 帯 | 本数 | 前半 | 後半 |")
print("|---|---|---|---|---|")
for n in runs:
    run = dt.load_run(T + n)
    days = dt.period_days(run)
    for grp, sel in (("0 分", lambda t: t["exit_ns"] <= t["entry_ns"]), ("0 分超", lambda t: t["exit_ns"] > t["entry_ns"])):
        d = {x: 0.0 for x in days}
        cnt = 0
        for t in run["trades"]:
            if sel(t):
                cnt += 1
                k = dt.utc_day(t["exit_ns"])
                if k in d:
                    d[k] += t["pnl_bp"]
        a = dt.mean_ci([d[x] for x in days if x < CUT])
        b = dt.mean_ci([d[x] for x in days if x >= CUT])
        print(f"| {n} | {grp} | {cnt:,} | {ci(a)} | {ci(b)} |")

print("\n## D3 出の理由・保有時間の帯(1 取引あたり 円 [区間]。結果で決まる群。帯の境は本ごとの四分位 = 標本の中)\n")
for n in runs:
    g = tab[n]["d3"]["groups"]
    parts = []
    for gname, tb in g.items():
        parts.append(gname.split("【")[0] + ": " + "・".join(f"{k} {v['trades']:,} 本 {ci({'mean': v['per_trade'], 'lo': v['lo'], 'hi': v['hi']}, 1)}" for k, v in tb.items()))
    d3 = tab[n]["d3"]
    print(f"- {n}: " + " / ".join(parts) + f" / 上位 5% の日の和 {y(d3['top5_days_sum'])}・下位 5% {y(d3['bottom5_days_sum'])}(全体 {y(d3['total'])})")

print("\n## D4 取引の一生(母数 = 1 段目の足の後まで持った取引。損益の和は円、MFE・MAE は move_bp の中央値)\n")
print("| 本 | 母数 | 群 | 取引 | 和 円 | MFE | MAE |")
print("|---|---|---|---|---|---|---|")
for n in runs:
    if not pth[n]:
        print(f"| {n} | (D4・D5 の表が無い) | | | | | |")
        continue
    d4 = pth[n]["d4"]
    for gname, v in d4["groups"].items():
        print(f"| {n} | {d4['analysed']:,} / {d4['of']:,} | {gname} | {v['trades']:,} | {y(v['pnl_sum'])} | {v['mfe_median']:.2f} | {v['mae_median']:.2f} |")
print("\n出の後の値動き(move_bp、取引の向き [区間])と勝ち取引の 頂点までの分 ÷ 保有の分(25・50・75%):\n")
for n in runs:
    if pth[n]:
        d4 = pth[n]["d4"]
        print(f"- {n}: " + "・".join(f"{k} 分 {mv(v)}" for k, v in d4["after_exit"].items()) + " / 頂点の比 " + "・".join(f"{q:.2f}" for q in d4["win_peak_share_q"]))

print("\n## D5 合図の後の値動き(起点 = 建ての時刻、move_bp [区間]、対照 = 24 時間後)\n")
print("| 本 | 1 分 | 5 分 | 15 分 | 60 分 | 対照 60 分 |")
print("|---|---|---|---|---|---|")
for n in runs:
    if pth[n]:
        d5 = pth[n]["d5"]["建てた合図(起点 = 建ての時刻)"]
        print(f"| {n} | " + " | ".join(mv(d5[k]["signal"]) for k in ("1", "5", "15", "60")) + f" | {mv(d5['60']['control_24h'])} |")

print("\n## D6 前の出から次の建てまでの間隔の帯(1 取引あたり 円 [区間]。帯の境は標本の中)\n")
for n in runs:
    g = tab[n]["d6"]["groups"]
    print(f"- {n}: " + "・".join(f"{k} {v['trades']:,} 本 {ci({'mean': v['per_trade'], 'lo': v['lo'], 'hi': v['hi']}, 1)}" for k, v in g.items()))

print("\n## D7 本 − 基準(同じ日どうしの日ごとの差、円/日 [区間](MDE))\n")
print("| 比べ | 全期間 | 前半 | 後半 | 0 を含まない年 |")
print("|---|---|---|---|---|")
bd = dt.daily_series(dt.load_run(T + "base"))
for n in names:
    d7 = tab[n]["d7"]
    rd = dt.daily_series(dt.load_run(T + n))
    common = sorted(set(rd) & set(bd))
    a = dt.mean_ci([rd[x] - bd[x] for x in common if x < CUT])
    b = dt.mean_ci([rd[x] - bd[x] for x in common if x >= CUT])
    yrs = [f"{k} {ci(v)}" for k, v in d7["years"].items() if v.get("lo") is not None and (v["lo"] > 0 or v["hi"] < 0)]
    print(f"| {n} − base | {ci(d7['all'], 1)}({y(d7['all']['mde'], 1)}) | {ci(a)}({y(a['mde'])}) | {ci(b)}({y(b['mde'])}) | {'、'.join(yrs) or '無い'} |")
print("\n年ごと(円/日):\n")
print("| 比べ | " + " | ".join(years) + " |")
print("|---|" + "---|" * len(years))
for n in names:
    yv = tab[n]["d7"]["years"]
    print(f"| {n} − base | " + " | ".join(y(yv[k]["mean"]) if k in yv else "—" for k in years) + " |")
print("\n取引の突き合わせ(合図の時刻。円):\n")
print("| 比べ | 両方にある取引(差の和) | こちらだけ(和) | 基準だけ(和) |")
print("|---|---|---|---|")
for n in names:
    m = tab[n]["d7"]["match"]
    print(f"| {n} − base | {m['both']:,} 本({y(m['sum_both_a_minus_b'])}) | {m['only_a']:,} 本({y(m['sum_only_a'])}) | {m['only_b']:,} 本({y(m['sum_only_b'])}) |")
