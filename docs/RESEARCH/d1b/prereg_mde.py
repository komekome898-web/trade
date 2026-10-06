"""前提の直接の測り(11 項目)の事前登録の MDE の表(2026-10-06、走らせる前。値動き・損益は読まない)。

件数は各項目の `docs/RESEARCH/d1b/<#>_<カード>/COUNTS*.md` の表から、行(全期間・前半・後半)と列の見出しで読む(手で写さない)。
MDE は 5% 両側・80%・正規近似の 2.8 × se(2.8 = 1.96 + 0.84)。日の塊の区間の実効の件数は、件の数(件を独立とみる)と
日の数(1 日を 1 件とみる)の間にあるとみて、両端を並べる。
- 割合の量: MDE = 2.8 × √(0.5 × 0.5 ÷ n)(割合 0.5 のときが一番広い)。単位は % ポイント。
- 連続の量(値動き・損益): MDE ÷ σ = 2.8 ÷ √n(σ = 1 件のばらつき。走らせる前は分からないので σ の倍で書き、
  走らせた後に実測の MDE を並べる)。
- 相関: se ≈ 1 ÷ √n とみて MDE = 2.8 ÷ √n(相関の単位)。

    python3 docs/RESEARCH/d1b/prereg_mde.py
"""
from __future__ import annotations

import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS = ("全期間", "前半", "後半")


def tables(path):
    """md の表を出てくる順に [(見出しの列, {行の頭: [セル]})] で返す。"""
    out, lines = [], open(path, encoding="utf-8").read().splitlines()
    i = 0
    while i < len(lines) - 1:
        if lines[i].startswith("|") and lines[i + 1].startswith("|---"):
            head = [c.strip() for c in lines[i].strip("|").split("|")]
            rows = {}
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                cells = [c.strip() for c in lines[j].strip("|").split("|")]
                rows[cells[0]] = cells
                j += 1
            out.append((head, rows))
            i = j
        else:
            i += 1
    return out


def pick(path, t_index, col):
    """表 t_index の列 col(見出しの前方一致)を、全期間・前半・後半の行で返す。行の頭は「前半(…)」の形も許す。"""
    head, rows = tables(os.path.join(HERE, path))[t_index]
    k = next(i for i, h in enumerate(head) if h.startswith(col))
    res = {}
    for r in REGIONS:
        key = next(x for x in rows if x == r or x.startswith(r + "("))
        res[r] = int(rows[key][k].replace(",", ""))
    return res


def mde_p(n):
    return 100 * 2.8 * math.sqrt(0.25 / n)


def mde_s(n):
    return 2.8 / math.sqrt(n)


# (項目, 主の量, 量の種類 p=割合 / s=連続 / r=相関, 件の数の出所, 日の数の出所, 族の掛け算, 注)
ITEMS = [
    ("1 今の paper bot", "持つ先 Binance / bitFlyer の 1 日あたりの損益と、その差", "s",
     None, ("1_card1/COUNTS.md", 0, "日数"), [("持つ先と差", 3)], "1 件 = 1 日(損益は日ごと)。戻るまでの分(1 合図)は分布の記述"),
    ("2 カツオ(USD-M)", "合図の後の、ヒゲと逆の向きの値動き(終点・一番深い点)", "s",
     ("2_card2/COUNTS_um.md", 2, "合図の数"), ("2_card2/COUNTS_um.md", 2, "日数"),
     [("出所", 2), ("強弱", 2), ("時間", 4), ("終点・一番深い点", 2)], "現物の出所の件数は COUNTS_spot.md"),
    ("2 カツオ(現物)", "同上", "s",
     ("2_card2/COUNTS_spot.md", 2, "合図の数"), ("2_card2/COUNTS_spot.md", 2, "日数"), [], "族は上の行に含めた"),
    ("3 円の上乗せ(窓 1 時間)", "端に寄った後の、脚ごとの戻りの値動き", "s",
     ("3_card3/COUNTS_outside_onset_last1m.md", 0, "合図の数"), ("3_card3/COUNTS_outside_onset_last1m.md", 0, "日数"),
     [("窓", 3), ("脚", 3), ("時間", 4), ("開いた原因の脚", 3)], "2022-12-31 までの数え。2023 年を足す数え直し(担当 A の common.py のコミットの後)で置き換える。窓 1 日・1 週は同じ md の後の表"),
    ("4 マチルダ", "1 回の離れの後に中心へ戻る割合", "p",
     ("4_card4/COUNTS.md", 0, "1 回の離れ"), ("4_card4/COUNTS.md", 0, "日数"),
     [("比の区分", 3), ("戻る割合・一番深い不利な点", 2)], "比の区分ごとの件数は同じ md の 2 つ目の表"),
    ("5 東京仲値", "朝の窓の向きの一致の割合(1 日 × 1 分)と相関 r̄", "p",
     ("5_card5/COUNTS.md", 0, "朝の窓(k=0)の 日×分"), ("5_card5/COUNTS.md", 0, "窓 k=0 の日"),
     [("窓", 24), ("一致の割合・相関", 2)], "相関の MDE は下の注の式(日の数で)"),
    ("6 週末ギャップ", "週明け 1 時間で g と逆へ戻した幅 ÷ g(連続)と符号の一致(割合)", "s",
     ("6_card6/COUNTS.md", 0, "週明け"), ("6_card6/COUNTS.md", 0, "週明け"),
     [("btc・usdjpy", 2), ("符号の一致・戻した幅・一番深い点", 3)], "1 件 = 1 週(日の数の欄も週の数。区間は週を選び直す)"),
    ("7 バリアレース(窓 1 時間)", "上下の線のどちらに先に当たるか(続きの割合)", "p",
     ("7_card7/COUNTS.md", 0, "数える起点 1h"), ("7_card7/COUNTS.md", 0, "日数"),
     [("窓", 3), ("幅の帯", 3), ("そのまま・流れを抜いた値", 2)], "窓 1 日・1 週は同じ md の後の表"),
    ("8 セッション内の平均回帰(区切り 15 時)", "平均から離れた後の、平均へ戻る向きの値動き(1 日 × 1 分)", "s",
     ("8_card8/COUNTS.md", 0, "区切り 15 時"), ("8_card8/COUNTS.md", 0, "日数"),
     [("時間", 4), ("区切り", 24), ("起点 約定・中ほど", 2), ("1 分目を除く・含む", 2)],
     "件数は 2023-12-17 までの数え(区切り 15 時の列)"),
    ("9 清算の連鎖", "清算の後の bitFlyer − Binance の動きの差(時間 4)", "s",
     ("9_card9/COUNTS.md", 0, "件数"), ("9_card9/COUNTS.md", 0, "件数"),
     [("時間", 4), ("差・遅れの相互相関", 2)],
     "境より後の行を読んだ数え。境で切った数え直しの後に置き換える。日の数は 176(前半・後半 88)"),
    ("11 カード 5・7・8 をまたいで", "前の日の荒れ具合の区分ごとの続き・戻りの割合", "p",
     None, ("11_cards5_7_8/COUNTS.md", 0, "区分のある日"),
     [("区分", 3), ("3 つの形", 3)], "1 件 = 1 日 × 窓。区分ごとの日数は low・mid・high の列"),
]


def main() -> int:
    L = ["# 前提の直接の測り — 事前登録の MDE の表(走らせる前)", "",
         "`prereg_mde.py` が出した。件数は各項目の COUNTS の表から読んだ。MDE = 2.8 × se(2.8 = 1.96 + 0.84。5% 両側・80%・正規近似)。",
         "「件を独立」と「1 日を 1 件」は、日の塊の区間の実効の件数の両端。割合は % ポイント、連続の量は σ(1 件のばらつき)の倍。", "",
         "| 項目 | 主の量 | 種類 | 区分 | 件の数 | 日の数 | MDE(件を独立) | MDE(1 日を 1 件) | 族の大きさ | 注 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for name, q, kind, src_n, src_d, fam, note in ITEMS:
        days = pick(*src_d)
        if name.startswith("9 "):
            days = {"全期間": 176, "前半": 88, "後半": 88}
        if name.startswith("11 "):
            days = pick(*src_d)
        ns = pick(*src_n) if src_n else days
        size = math.prod(f for _, f in fam) if fam else None
        fam_s = (" × ".join(f"{a} {b}" for a, b in fam) + f" = {size}") if fam else "—"
        for i, r in enumerate(REGIONS):
            n, d = ns[r], days[r]
            if kind == "p":
                a, b = f"{mde_p(n):.2f} pt", f"{mde_p(d):.2f} pt"
            else:
                a, b = f"{mde_s(n):.4f} σ", f"{mde_s(d):.4f} σ"
            L.append(f"| {name if i == 0 else ''} | {q if i == 0 else ''} | {kind if i == 0 else ''} | {r} | {n} | {d} | {a} | {b} | {fam_s if i == 0 else ''} | {note if i == 0 else ''} |")
    # 5 の相関
    d5 = pick("5_card5/COUNTS.md", 0, "窓 k=0 の日")
    L += ["", "# 5 の相関 r(t) の MDE(1 件 = 1 日、se ≈ 1 ÷ √日数): " +
          "・".join(f"{r} {2.8 / math.sqrt(d5[r]):.4f}" for r in REGIONS)]
    # 10
    L += ["", "# 10(約定の記録、6 日)は日の塊の区間を出さず(6 日は塊 5 日の 2 倍に届かない)、決定を独立とみた割合の MDE だけ:", "",
          "| 型 | 決定(6 日) | MDE(割合 0.5 の周り) |", "|---|---|---|"]
    t10 = tables(os.path.join(HERE, "10_cards34589/COUNTS.md"))
    for head, rows in t10[:3]:
        k = head.index("合計")
        for key, cells in rows.items():
            if key in ("c3_1h・all", "c3_1h・flip", "c5・flip", "c8_jst_day・flip", "c8_bf_maint・flip", "good", "bad",
                       "t0 以後に約定がある(「秒」、主)"):
                n = int(cells[k])
                L.append(f"| {key} | {n} | {mde_p(n):.2f} pt |")
    out = os.path.join(HERE, "PREREG_MDE.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
