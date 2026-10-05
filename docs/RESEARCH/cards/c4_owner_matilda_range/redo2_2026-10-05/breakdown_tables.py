"""カード 4(アドバイザーの指摘 2: L-668 の勝ち負けの分解、L-673 の比の十分位を全部)。保存済みの analysis.json の値を
写すだけ(計算は 1 取引あたり = 和 ÷ 数 と、1 日あたり = 和 ÷ 日数 だけ)。台本そのものの試験は無い。
対象 = v37・A1_center_4_3・R2_ratio_gate12.96_center_4_3・R2_ratio_gate_rolling_center_4_3、良い側・悪い側。
    python3 docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/breakdown_tables.py
出力: このフォルダの BREAKDOWN.md(全行)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "..", "limit_sim", "families_r2")
RUNS = ["v37", "A1_center_4_3", "R2_ratio_gate12.96_center_4_3", "R2_ratio_gate_rolling_center_4_3"]


def per(x, n):
    return f"{x / n:+.3f}" if n else "—"


def main():
    out = ["# カード 4: 勝ち負けの分解と比の十分位(analysis.json の写し、bp、経費の前、区間なし)", ""]
    for name in RUNS:
        for side in ("good", "bad"):
            d = os.path.join(R, f"{name}_{side}")
            a = json.load(open(os.path.join(d, "analysis.json")))
            days = json.load(open(os.path.join(d, "summary.json")))["all"]["days"]
            out += [f"## {name} {side}(日数 {days:.0f})", "", "### 出の理由(by_reason)【結果で決まる群】", "",
                    "| 出の理由 | 取引 | 和 | 1 取引あたり | 1 日あたり |", "|---|---|---|---|---|"]
            for k, v in a["by_reason"].items():
                out.append(f"| {k} | {v['trades']:,} | {v['sum_bp']:+,.0f} | {per(v['sum_bp'], v['trades'])} | {v['sum_bp'] / days:+.2f} |")
            out += ["", "### ブレイクとの関係(by_break)と、決まらない足を含まない取引(decided_only)", "",
                    "| 群 | 取引 | 勝ち | 和 | 小勝ちの和 | 大負けの和 | 1 日あたり |", "|---|---|---|---|---|---|---|"]
            rows = [("全部: " + k, v) for k, v in a["by_break"].items()]
            do = a.get("decided_only") or {}
            rows.append(("決まらない足を含まない取引 全部", do))
            rows += [("決まらない足を含まない: " + k, v) for k, v in (do.get("by_break") or {}).items()]
            for k, v in rows:
                if not v:
                    continue
                out.append(f"| {k} | {v['trades']:,} | {v['wins']:,} | {v['sum_bp']:+,.0f} | {v.get('small_win_sum_bp', 0):+,.0f} | "
                           f"{v.get('big_loss_sum_bp', 0):+,.0f} | {v['sum_bp'] / days:+.2f} |")
            out += ["", "### 保有時間の帯(by_hold、分)【結果で決まる群】", "",
                    "| 帯(分) | 取引 | 勝ち | 和 | 小勝ちの和 | 大負けの和 | 1 取引あたり |", "|---|---|---|---|---|---|---|"]
            for v in a["by_hold"]["rows"]:
                out.append(f"| {v['lo']}〜{v['hi'] if v['hi'] is not None else ''} | {v['trades']:,} | {v['wins']:,} | {v['sum_bp']:+,.0f} | "
                           f"{v['small_win_sum_bp']:+,.0f} | {v['big_loss_sum_bp']:+,.0f} | {per(v['sum_bp'], v['trades'])} |")
            out += ["", "### 比の十分位(ratio_deciles: その走らせの取引を同じ数ずつ 10 に分けた境)【建ての前に決まる群】", "",
                    "| 十分位 | 比の範囲 | 取引 | 勝ち | 勝率 | 和 | 1 取引あたり |", "|---|---|---|---|---|---|---|"]
            for v in a["ratio_deciles"]["rows"]:
                out.append(f"| {v['decile']} | {v['lo']:.2f}〜{v['hi']:.2f} | {v['trades']:,} | {v['wins']:,} | {v['wins'] / v['trades']:.1%} | "
                           f"{v['sum_bp']:+,.0f} | {v['mean_bp']:+.3f} |")
            fb = a["ratio_fixed_bins"]
            e = [None] + fb["edges"] + [None]
            out += ["", f"### 比の固定の境の区分(ratio_fixed_bins、境 {fb['edges']})【建ての前に決まる群】", "",
                    "| 区分 | 比の範囲 | 取引 | 勝ち | 和 | 小勝ちの和 | 大負けの和 | 1 取引あたり |", "|---|---|---|---|---|---|---|---|"]
            for v in fb["rows"]:
                i = v["bin"]
                rng = f"{'' if e[i-1] is None else e[i-1]}〜{'' if e[i] is None else e[i]}"
                out.append(f"| {i} | {rng} | {v['trades']:,} | {v['wins']:,} | {v['sum_bp']:+,.0f} | {v['small_win_sum_bp']:+,.0f} | "
                           f"{v['big_loss_sum_bp']:+,.0f} | {per(v['sum_bp'], v['trades'])} |")
            out.append("")
    open(os.path.join(HERE, "BREAKDOWN.md"), "w").write("\n".join(out) + "\n")
    print(len(out))


if __name__ == "__main__":
    main()
