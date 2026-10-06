"""# 11(カード 5・7・8 をまたいで): 「静かな時期は続く」を同じ物差しで並べると、3 つの形で同じ向きか。

D1B_FRAMINGS.md # 11 の行: 何を何通り = 前の日の荒れ具合の区分 3 × 続き・戻りの割合。3 つの形(朝の向きの続き・一定幅の
線・平均からの離れ)/ 何を 1 件 = 1 日 × 窓 / データ = bitFlyer FX の 1 分足 / 対照 = 区分の間の比べ(K-135 の物差し)。

量の作り方:
- 前の日の荒れ具合の区分 = scripts/w4_measure/vol_split_daily.py の daily_vol・classify(前の日の 1 分足の |対数の値動き| の
  平均を、前の暦年の日の 3 分位で low / mid / high。2017 年から。判断の時点で分かる値)。日 = 窓の日本時間の日。
- 続きの割合(3 つの形):
  朝の向きの続き(カード 5): # 5 の朝の窓(k = 0)の一致の割合(0 時から t までの向きが t から 9 時 55 分まで続いた分の割合)。
  一定幅の線(カード 7): # 7 の続きの割合(当たりの向き == 起点の前の向き window_move。リードの決め 2)。3 つの窓。
  平均からの離れ(カード 8): # 8 の 1 − 一致の割合(値動きが平均から離れる向き = 続き)。組はリードの決め 4:
  区切り jst_day(日本時間 0 時始まり = UTC 15 時)・時間 15 分・起点 約定の値段(次の足の始値)・1 分目を除く(C8_CELL)。
- 区分の間の比べ: 区分ごとの続きの割合 [区間] と、low − high の差 [区間](同じ日の抽き直しで両方を作る)。
"""
from __future__ import annotations

import numpy as np

import g2lib as L

CLASSES = ("low", "mid", "high")
C8_CELL = (15, 15, "約定", True)  # (区切り h, 時間 H, 起点, 1 分目を除く) リードの決め 4
C7_PRIOR = "window_move"  # リードの決め 2


def _mask_days(days: L.Days, cls: dict, c: str) -> np.ndarray:
    return np.array([cls.get(int(d)) == c for d in days.nums], dtype=float)


def form_rows(days: L.Days, cls: dict, num: np.ndarray, den: np.ndarray, nums) -> dict:
    """日ごとの 続き(num)・分母(den)(日の並び全体の配列)から、区分ごとの割合と low − high。"""
    k = np.asarray(nums, dtype=np.int64) - days.nums[0]
    out = {}
    m = {c: _mask_days(days, cls, c)[k] for c in CLASSES}
    for c in CLASSES:
        out[c] = L.ratio_ci(num[k] * m[c], den[k] * m[c])
    out["low − high"] = L.diff_ratio_ci(num[k] * m["low"], den[k] * m["low"], num[k] * m["high"], den[k] * m["high"])
    return out


def c7_daily(days: L.Days, res7: dict, window: str, prior: str):
    wv = res7["windows"][window]
    pr = wv["prior_" + prior]
    ok = (wv["side"] != 0) & (pr != 0)
    acc = L.DayAcc(days, ("num", "den"))
    acc.add(wv["day"][ok], num=(wv["side"][ok] == pr[ok]).astype(float), den=1.0)
    return acc.s["num"], acc.s["den"]


def tables(days: L.Days, cls: dict, res5: dict, res7: dict, res8: dict, c7_prior: str = C7_PRIOR, c8_cell=C8_CELL) -> tuple:
    md = ["# # 11 カード 5・7・8: 前の日の荒れ具合 × 続きの割合(D1b)", "",
          "区分 = 前の日の荒れ具合(vol_split_daily.classify、2017 年から)。続きの割合の区間 = 日の塊"
          "(循環 5 日・1,000 回・種 20261006)。MDE = 2.8 × se。対照 = 区分の間の比べ(low − high)。", "",
          "| 形 | 期間 | low [区間] | mid [区間] | high [区間] | low − high [区間] | MDE(差) |", "|---|---|---|---|---|---|---|"]
    obj = {"periods": days.describe(), "class_days": {c: int(sum(1 for d in days.nums if cls.get(int(d)) == c)) for c in CLASSES},
           "forms": {}}
    forms = {}
    a5 = res5["accs"][0]
    forms["朝の向きの続き(カード 5、k = 0)"] = (a5.s["agree"], a5.s["den"])
    if c7_prior is not None:
        for w in res7["windows"]:
            forms[f"一定幅の線(カード 7、{w}、前の向き {c7_prior})"] = c7_daily(days, res7, w, c7_prior)
    if c8_cell is not None:
        acc = res8["kept"][c8_cell]
        forms[f"平均からの離れ(カード 8、区切り {c8_cell[0]}・{c8_cell[1]} 分・{c8_cell[2]}・1 分目 {'除く' if c8_cell[3] else '含む'})"] = (
            acc.s["den"] - acc.s["agree"], acc.s["den"])
    for fname, (num, den) in forms.items():
        obj["forms"][fname] = {}
        for pname, nums in days.parts().items():
            r = form_rows(days, cls, num, den, nums)
            obj["forms"][fname][pname] = r
            md.append(f"| {fname} | {pname} | {L.fci(r['low'])} | {L.fci(r['mid'])} | {L.fci(r['high'])} | "
                      f"{L.fci(r['low − high'])} | {L.fmde(r['low − high'])} |")
    md += ["", "## 年ごと(記述。区間なし)", "", "| 形 | 年 | low | mid | high |", "|---|---|---|---|---|"]
    for fname, (num, den) in forms.items():
        for y, nums in days.years().items():
            k = np.asarray(nums) - days.nums[0]
            cells = []
            for c in CLASSES:
                m = _mask_days(days, cls, c)[k]
                dd = (den[k] * m).sum()
                cells.append(L.f((num[k] * m).sum() / dd) if dd > 0 else "—")
            md.append(f"| {fname} | {y} | " + " | ".join(cells) + " |")
    return md, obj


def count(days: L.Days, cls: dict) -> dict:
    d = np.array([x for x in days.nums if int(x) in cls], dtype=np.int64)
    cols = {c: np.array([x for x in days.nums if cls.get(int(x)) == c], dtype=np.int64) for c in CLASSES}
    return {"lines": L.count_table(days, d, "区分のある日", {f"{c} の日": v for c, v in cols.items()})}
