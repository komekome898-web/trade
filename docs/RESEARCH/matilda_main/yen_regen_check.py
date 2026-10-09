# リードが書いた。委任・批評家を通していない(数えるだけ)。L-920 の直しの確かめ。
# 作り直した読み口の出力(円)が、直す前の出力(口座の bp、コミット 45b773a8 の前の版 = 64368036 の時点の json)× 20 と合うかを葉ごとに見る。
# D7(読み口の日の取り方を和集合に直したので、期間の始まりが違う本で値が変わる)と、D4 の群の名前の変更は別に数える。
# 使い方(リポジトリの根から): python3 docs/RESEARCH/matilda_main/yen_regen_check.py > docs/RESEARCH/matilda_main/yen_regen_check.out
import json
import os
import subprocess
from collections import Counter

M = "docs/RESEARCH/matilda_main/"
OLD = "64368036"
NOT_MONEY = {"n", "trades", "days", "k", "n_trades", "count", "both", "only_a", "only_b", "analysed", "of", "share_trades", "steps",
             "hold_edges_min", "gap_edges_min", "win_peak_share_q", "mfe_median", "mae_median", "t_mfe", "hold", "days_needed",
             "days_needed_first", "days_needed_second", "d0", "signal_delay", "zero", "outcome", "cut", "cut_source", "from", "to",
             "label", "same_sign", "stop", "match_key", "after_exit", "d5", "valid_min", "q", "max"}


def leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in NOT_MONEY:
                yield from leaves(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{path}[{i}]")
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield path, float(o)


def old_json(p):
    r = subprocess.run(["git", "show", f"{OLD}:{p}"], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


c = Counter()
bad = []
for run in sorted(os.listdir(M)):
    for name in ("diag_tables.json", "diag_paths.json"):
        p = f"{M}{run}/{name}"
        if not os.path.isfile(p):
            continue
        new, old = json.load(open(p)), old_json(p)
        if old is None:
            continue
        if name == "diag_paths.json":  # 損益の和だけが円になった。群の名前は変わったので並び順で結ぶ
            new = [g["pnl_sum"] for g in new["d4"]["groups"].values()]
            old = [g["pnl_sum"] for g in old["d4"]["groups"].values()]
            pairs = [(f"d4.groups[{i}].pnl_sum", a, b) for i, (a, b) in enumerate(zip(old, new))]
        else:
            lo, ln = dict(leaves(old)), dict(leaves(new))
            pairs = [(k, lo[k], ln.get(k)) for k in lo]
        for k, a, b in pairs:
            kind = "D7" if k.startswith(".d7") else "そのほか"
            if b is None:
                c[(kind, "新しい出力に無い")] += 1
                continue
            ok = abs(b - a * 20) <= 1e-6 * max(1.0, abs(b))
            c[(kind, "合う" if ok else "合わない")] += 1
            if not ok:
                bad.append((run, name, k, a * 20, b))
print("| 種類 | 結果 | 葉の数 |\n|---|---|---|")
for (k, r), n in sorted(c.items()):
    print(f"| {k} | {r} | {n:,} |")
print("\n合わない葉(前の bp × 20 / 新しい円):")
for x in bad[:300]:
    print("-", x)
print(f"(全 {len(bad)} 件)")
