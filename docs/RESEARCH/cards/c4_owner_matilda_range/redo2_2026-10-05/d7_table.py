"""カード 4 の D7 の表: d7/*.json(読み口 diag_tables.py の --run / --vs の出力)の値を写すだけ。台本そのものの試験は無い。
行 = 比べ(新しい形の側 − 元の形の側)。L-666 の一番不利な組み合わせ = 新しい形の悪い側 − 元の形の良い側。
    python3 docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d7_table.py
出力: このフォルダの D7_TABLE.md(全行)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
D7 = os.path.join(HERE, "d7")
NM = {("bad", "good"): "悪 − 良(一番不利)", ("good", "good"): "良 − 良", ("bad", "bad"): "悪 − 悪"}


def main():
    out = ["# カード 4 の D7: 日ごとの差(新しい形 − 元の形、bp/日、経費の前、区間 95% 日の塊 5 日)", "",
           "年ごとの列 = 年ごとの差の区間が 0 より上の年の数 / 0 を含む / 0 より下(区切りの判断には使わない記述)。",
           "取引の突き合わせ = 建ての時刻(合図の時刻の列が無い)で両方にある取引の数・片方だけの取引の数と和。", "",
           "| 新しい形 | 元の形 | 側 | 全期間の差 [区間] | MDE | 年: 上/含む/下 | 両方にある取引 | 新しい形だけ(数・和) | 元の形だけ(数・和) | 両方にある取引の差の和 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for f in sorted(os.listdir(D7)):
        if not f.endswith(".json"):
            continue
        new, rest = f[:-5].split("__", 1)
        sn, rest = rest.split("_vs_", 1)
        base, sb = rest.rsplit("__", 1)
        d = json.load(open(os.path.join(D7, f)))["d7"]
        a, m = d["all"], d["match"]
        ys = d["years"].values() if isinstance(d["years"], dict) else d["years"]
        up = sum(1 for y in ys if y.get("lo") is not None and y["lo"] > 0)
        dn = sum(1 for y in ys if y.get("hi") is not None and y["hi"] < 0)
        n = sum(1 for y in ys if y.get("lo") is not None)
        out.append(f"| {new} | {base} | {NM[(sn, sb)]} | {a['mean']:+.2f} [{a['lo']:+.2f}, {a['hi']:+.2f}] | {a['mde']:.2f} | "
                   f"{up}/{n - up - dn}/{dn} | {m['both']:,} | {m['only_a']:,}・{m['sum_only_a']:+,.0f} | "
                   f"{m['only_b']:,}・{m['sum_only_b']:+,.0f} | {m['sum_both_a_minus_b']:+,.0f} |")
    open(os.path.join(HERE, "D7_TABLE.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
