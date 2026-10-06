#!/usr/bin/env python3
"""部品 4: 門の読み方の台本。部品 3 の出力(daily.csv・daily_mid.csv・diagnostics.json・boundary_carry_days.csv)と
部品 2 の区分(classes.json)を読み、数を全部この台本が出す(手で書かない)。段 1 では作り物でしか動かさない。

    PYTHONPATH=src python3 scripts/w4_measure/c8_binance/bn_read_gate.py --run-dir <部品 3 の出力> --classes <classes.json> --out <置き場>

決まり(結果を見る前に、この台本と tests/research/test_c8_binance.py で固める):
  G0 母数 = 区分のある日(classes.json の日)のうち、daily.csv に行のある日。区分の無い日は数えない。
     区分があって daily.csv に行の無い日の数は別に出す(その日は母数に入れない)。
  G1 門の形 3 つ(日 d の区分 = 前の日 d − 1 の荒れ具合。classify の出したまま):
       門なし: 母数の日の全部に入る。
       A: 区分が high の日だけ入る。ほかの日の損益は 0。
       B: 区分が low の日は入らない(損益 0)。ほかの日はそのまま。
  G2 形ごと: 「全部の日に均した」= 母数の日の全部(入らない日は 0)の 1 日あたり・95% 区間・MDE、
     「入った日だけ」= 入った日の 1 日あたり・区間・MDE、入った日の数・母数のうちの割合。
     A と B に順位は付けない(全部の日に均した値は 0 の日の割合が違うので、A と B を比べる物差しにしない)。
  G3 差: A − 門なし、B − 門なし = 同じ日どうしの差の系列(母数の日)の 1 日あたり・区間・MDE。
  G4 区分ごとの表: low / mid / high × 全期間・前半・後半の、門なしの 1 日あたり・区間。
  G5 全部を、始値 → 始値(daily.csv)と中ほど(daily_mid.csv)の両方で。前半・後半にも分ける
     (境 = classes.json の half_boundary_day。その日から後半)。
  G6 区間 = 日の塊のブートストラップ: bot.bt.validation.block_bootstrap_ci(method "circular"、塊 5 日、1,000 回、
     種 20261006、統計量 = 平均、95% 百分位)。日の系列は日付順(入った日だけのときは入った日を日付順に詰めた列)。
     se = 再標本の平均の標準偏差(ddof 1)。MDE = 2.8 × se(委任文の式。5% 両側・80%)。日が 5 日未満なら塊 = 日数、
     2 日未満なら区間なし。
     G6 の感度(委任文 fix2 の 5、批評家 2 回目の問 2 (5)): G3 の差(read_block の diffs。全期間・前半・後半・
     またぎの日を外した差・G9 の年ごと)には、塊 20 日(仮定。ほかは同じ: circular・1,000 回・種 20261006。日が 20 日未満なら
     塊 = 日数)の区間・se・MDE も block20 として横に並べる。感度として並べるだけで、印(G7)も読みの決まりも塊 5 日だけで決める。
  G7 読みの結果の印(値は段 2 まで出ない): 各差の区間が 0 より上 / 0 を含む / 0 より下(mark)。
  G8 セッションをまたいだ持ち高: diagnostics.json の 5_boundary_carry(回数・その決定の損益の和)をそのまま写し、
     boundary_carry_days.csv の day(またいだ持ち高の損益が乗った日)を母数から外した A − 門なし・B − 門なし も並べる
     (中ほども同じ日を外す。またいだ決定の損益は始値でも中ほどでも同じ日に乗る)。
  G9 年ごとの表(事前登録 PREREG.md の「区分が年に偏っている」): 母数の日を年(日付の先頭 4 文字。2019〜2023)で分け、
     年ごとに A − 門なし・B − 門なし(その年の母数の日に均した 1 日あたり・区間・MDE・印)と、区分ごとの門なしの
     1 日あたり・区間・日数(G4 と同じ作り)。始値と中ほどの両方。区間は G6 のまま(年ごとの日の列に当てる)。
  G10 対照群(補助帰無、事前登録の「補助帰無の手順」。批評家 2 回目の [止める] の後に G10a を主にした): 全期間の母数の日
     (日付順、n 日)で、実際の門の外す日の印 = A は high 以外の日、B は low の日(母数の中で数える。外す日数 m)。
     どの対照も、差 = (外した日の損益を 0 にした門 − 門なし)の、母数の n 日に均した 1 日あたり = −Σ外した日の損益 ÷ n。
     出す物(3 つとも同じ): 実際の差(G3 の全期間の 1 日あたり)、上側の割合 = 対照の差のうち実際の差以上(≥)の割合、
     対照の 95 点 = numpy.quantile(対照の差, 0.95)(既定の線形補間)、実際の差 > 95 点か、対照の差の平均・標準偏差。
     始値と中ほどの両方。
   G10a(主)区分の並びの循環ずらし: 外す日の印を、母数の日の並びの上で k 日ずらす(k = 1〜n − 1 の全部。乱数なし)。
     ずらした印 = numpy.roll(印, k)(日 t の印 = 元の印の (t − k) を n で割った余りの日)。d_k = −Σ x·roll(印, k) ÷ n。
     k = 0 の値が実際の差(G3)と同じことも出す。
   G10b 年ごと: 母数の日を年(日付の先頭 4 文字)で分け、年ごとに実際の門と同じ日数 m_y(その年の母数の日のうち実際の門が
     外す日の数)を、その年の母数の日(日付順、n_y 日)の中だけで、G10c と同じ手順(5 日の塊・循環はその年の日の中で回る・
     最後の塊を切る)で外す。1,000 回、乱数 = numpy.random.default_rng(20261007) を形(A・B)ごとに新しく作る。
     引く順: 1 回ごとに、年を古い順に回す(1 回目の 2019 年・2020 年 …、2 回目の 2019 年 …)。同じ形では始値と中ほどに
     同じ外し方を当てる。外した日数が全回・全年で m_y ちょうどだったかも出す。
   G10c 元の作り方(並べて出すだけ): m 日ちょうどを次の手順で外す: 乱数で始めの番号 s(0〜n − 1 の一様)を引き、
     s, s+1, …, s+4(n で割った余り = 循環)の 5 日の塊の日を、まだ外していない日だけ順に外す。外した日が m に届いたら、
     その塊の残りは外さない(最後の塊を切る)。届くまで塊を引き続ける。1,000 回。乱数 = numpy.random.default_rng(20261007) を
     形(A・B)ごとに新しく作る(同じ形では、始値と中ほどに同じ外し方の 1,000 通りを当てる)。外した日数が全回で m ちょうどか。
   G3 × G10a の読み(事前登録の「G3 と G10 の組み合わせの読み方」の 5 行。READING の表と関数 g3_g10a_reading):
     A・B × 始値・中ほどごとに、G3 の全期間の差の印(G7、塊 5 日)と G10a の「実際 > 95 点」から行を 1 つ選び、
     その行の「書く読み」の文をそのまま出す。印が無い(区間なし)ときは文を出さない。
     P1(G4)と G9 はこの表で読まない(事前登録のとおり)。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import numpy as np

from bot.bt.validation import block_bootstrap_ci  # noqa: E402

SEED = 20261006
N_RES = 1000
BLOCK = 5
PLACEBO_SEED = 20261007  # G10(事前登録の「補助帰無の手順」の種)
PLACEBO_N = 1000
PLACEBO_BLOCK = 5
PLACEBO_Q = 0.95
SENS_BLOCK = 20  # G6 の感度の塊(仮定。委任文 fix2 の 5「20 は仮定。感度として並べるだけで読みの決まりには使わない」)
MDE_K = 2.8  # 委任文「MDE = 2.8 × 標準誤差(5% 両側・80%)」の 2.8 のまま(z_0.975 + z_0.80 = 2.8016 とは丸めの差がある)
FORMS = ("none", "A", "B")
CLASSES = ("low", "mid", "high")
PRICES = {"open": "daily.csv", "mid": "daily_mid.csv"}


def read_daily(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines or lines[0] != "day,pnl_bp,n":
        raise ValueError(f"{path}: daily.csv の形でない")
    return {ln.split(",")[0]: float(ln.split(",")[1]) for ln in lines[1:]}


def read_carry_days(path: str) -> set:
    with open(path, encoding="utf-8") as fh:
        return {r["day"] for r in csv.DictReader(fh)}


def enters(form: str, c: str) -> bool:
    if form == "none":
        return True
    if form == "A":
        return c == "high"
    if form == "B":
        return c != "low"
    raise ValueError(form)


def gated(days: list, pnl: dict, cls: dict, form: str) -> np.ndarray:
    """母数の日(日付順)の門ありの損益(入らない日は 0)。"""
    return np.array([pnl[d] if enters(form, cls[d]) else 0.0 for d in days], dtype=float)


def stat(x, block: int = BLOCK) -> dict:
    """1 日あたり・95% 区間・se・MDE(G6)。block は塊の日数(既定 = 主の 5 日。感度のときだけ SENS_BLOCK)。"""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return {"n_days": 0, "per_day_bp": None, "ci": None, "se": None, "mde": None}
    if n < 2:
        return {"n_days": n, "per_day_bp": float(x.mean()), "ci": None, "se": None, "mde": None}
    ci = block_bootstrap_ci(x.tolist(), block_len=min(block, n), n_resamples=N_RES, seed=SEED, alpha=0.05,
                            method="circular", statistic="mean")
    return {"n_days": n, "per_day_bp": float(x.mean()), "ci": [ci.lo, ci.hi], "se": ci.se, "mde": MDE_K * ci.se}


def mark(ci) -> str | None:
    """G7: 区間が 0 より上 / 0 を含む / 0 より下。"""
    if ci is None:
        return None
    lo, hi = ci
    if lo > 0:
        return "0 より上"
    if hi < 0:
        return "0 より下"
    return "0 を含む"


def read_block(days: list, pnl: dict, cls: dict, n_universe: int | None = None) -> dict:
    """1 つの母数(日の並び)で、形ごと(G2)・差(G3)・印(G7)。"""
    n_u = len(days) if n_universe is None else n_universe
    base = gated(days, pnl, cls, "none")
    out = {"n_days": len(days), "forms": {}, "diffs": {}}
    for f in FORMS:
        g = gated(days, pnl, cls, f)
        ent = [i for i, d in enumerate(days) if enters(f, cls[d])]
        out["forms"][f] = {"all_days": stat(g), "entered_days": stat(g[ent]) if ent else stat([]),
                           "n_entered": len(ent), "entered_share": (len(ent) / n_u) if n_u else None}
    for f in ("A", "B"):
        dx = gated(days, pnl, cls, f) - base
        s = stat(dx)
        s["mark"] = mark(s["ci"])
        s20 = stat(dx, SENS_BLOCK)  # G6 の感度(印は付けない。読みの決まりに使わない)
        s["block20"] = {"block_days": SENS_BLOCK, "ci": s20["ci"], "se": s20["se"], "mde": s20["mde"]}
        out["diffs"][f"{f}-none"] = s
    return out


def by_class(days: list, pnl: dict, cls: dict) -> dict:
    """G4: 区分ごとの門なしの 1 日あたり・区間。"""
    out = {}
    for k in CLASSES:
        x = [pnl[d] for d in days if cls[d] == k]
        s = stat(x)
        out[k] = {"n_days": s["n_days"], "per_day_bp": s["per_day_bp"], "ci": s["ci"]}
    return out


def by_year(days: list, pnl: dict, cls: dict) -> dict:
    """G9: 年ごとの A − 門なし・B − 門なし(その年の日に均した値)と、区分ごとの門なし。"""
    out = {}
    for y in sorted({d[:4] for d in days}):
        ds = [d for d in days if d[:4] == y]
        r = read_block(ds, pnl, cls)
        out[y] = {"n_days": len(ds), "diffs": r["diffs"], "by_class": by_class(ds, pnl, cls)}
    return out


def placebo_removed(n: int, m: int, rng, block: int = PLACEBO_BLOCK) -> np.ndarray:
    """G10 の 1 回の外し方: n 日(日付順)のうち m 日ちょうどを、循環する block 日の塊を単位に外した印(bool の列)。"""
    if not 0 <= m <= n:
        raise ValueError(f"外す日数 {m} が 0〜{n} の外")
    rm = np.zeros(n, dtype=bool)
    k = 0
    while k < m:
        s = int(rng.integers(0, n))
        for j in range(block):
            i = (s + j) % n
            if not rm[i]:
                rm[i] = True
                k += 1
                if k == m:
                    break
    return rm


def placebo_masks(n: int, m: int, seed: int = PLACEBO_SEED, n_res: int = PLACEBO_N, block: int = PLACEBO_BLOCK) -> np.ndarray:
    """G10: 外し方 n_res 通り((n_res, n) の bool)。乱数は seed から新しく作る。"""
    rng = np.random.default_rng(seed)
    return np.array([placebo_removed(n, m, rng, block) for _ in range(n_res)], dtype=bool).reshape(n_res, n)


def null_compare(d, actual: float) -> dict:
    """G10a・b・c 共通: 対照の差の並び d と実際の差を比べる(上側の割合 ≥・95 点・実際 > 95 点・平均・標準偏差)。"""
    d = np.asarray(d, dtype=float)
    q = float(np.quantile(d, PLACEBO_Q))
    return {"actual_bp": float(actual), "upper_share": float(np.mean(d >= actual)), "q95_bp": q,
            "actual_gt_q95": bool(actual > q), "placebo_mean_bp": float(d.mean()),
            "placebo_sd_bp": float(d.std(ddof=1)) if len(d) > 1 else None, "n_resamples": int(len(d))}


def placebo_compare(x, masks: np.ndarray, actual: float) -> dict:
    """G10b・G10c: x = 母数の日の門なしの損益(日付順)。対照の差 = −Σ外した日の損益 ÷ n。"""
    x = np.asarray(x, dtype=float)
    n = len(x)
    return null_compare(-(masks.astype(float) @ x) / n, actual)


def rot_diffs(x, removed) -> np.ndarray:
    """G10a: d_k = −Σ x·roll(removed, k) ÷ n(k = 1〜n − 1、この順)。roll(removed, k)[t] = removed[(t − k) mod n]。"""
    x = np.asarray(x, dtype=float)
    rm = np.asarray(removed, dtype=bool)
    n = len(x)
    if len(rm) != n:
        raise ValueError("印と損益の長さが違う")
    if n < 2:
        return np.zeros(0)
    # Σ_t x[t]·rm[(t − k) mod n] = Σ_s rm[s]·x[(s + k) mod n]。x を 2 回つないだ列の k 番目からの n 個 = x[(s + k) mod n]
    win = np.lib.stride_tricks.sliding_window_view(np.concatenate([x, x]), n)[1:n]  # 行 k−1 = k 日ずらし
    return -(win @ rm.astype(float)) / n


def removed_mask(univ: list, cls: dict, form: str) -> np.ndarray:
    """実際の門が外す日の印(母数の日の並び = 日付順)。"""
    return np.array([not enters(form, cls[d]) for d in univ], dtype=bool)


def placebo_rot(pnls: dict, cls: dict, actual: dict) -> dict:
    """G10a(主): 区分の並びの循環ずらし(k = 1〜n − 1 の全部、乱数なし)。"""
    out = {"what": "区分の並びの循環ずらし(k = 1〜n − 1 の全部、乱数なし)", "primary": True, "quantile": PLACEBO_Q,
           "forms": {}}
    for f in ("A", "B"):
        r = {}
        for price, pnl in pnls.items():
            univ = sorted(d for d in cls if d in pnl)
            n = len(univ)
            rm = removed_mask(univ, cls, f)
            x = np.array([pnl[d] for d in univ], dtype=float)
            if n < 2:
                r[price] = {"actual_bp": None, "n_days": n, "n_removed": int(rm.sum()), "n_shifts": max(n - 1, 0)}
                continue
            res = null_compare(rot_diffs(x, rm), actual[price][f])
            k0 = float(-(x[rm]).sum() / n)
            res.update({"n_days": n, "n_removed": int(rm.sum()), "n_shifts": n - 1, "k0_bp": k0,
                        "k0_equals_actual": bool(abs(k0 - float(actual[price][f])) <= 1e-9 * max(1.0, abs(k0)))})
            r[price] = res
        out["forms"][f] = r
    return out


def year_masks(univ: list, removed, seed: int = PLACEBO_SEED, n_res: int = PLACEBO_N,
               block: int = PLACEBO_BLOCK) -> tuple:
    """G10b の外し方 n_res 通り((n_res, n) の bool)と、年 → 外す日数 m_y。
    年ごとに、その年の日(univ の中で日付順)の中だけで placebo_removed(n_y, m_y) を当てる(循環はその年の日の中)。
    引く順: 1 回ごとに年を古い順。乱数は seed から新しく作る。"""
    rm = np.asarray(removed, dtype=bool)
    n = len(univ)
    years = sorted({d[:4] for d in univ})
    pos = {y: np.array([i for i, d in enumerate(univ) if d[:4] == y], dtype=int) for y in years}
    m_y = {y: int(rm[pos[y]].sum()) for y in years}
    rng = np.random.default_rng(seed)
    out = np.zeros((n_res, n), dtype=bool)
    for r in range(n_res):
        for y in years:
            out[r, pos[y][placebo_removed(len(pos[y]), m_y[y], rng, block)]] = True
    return out, m_y


def placebo_year(pnls: dict, cls: dict, actual: dict, seed: int = PLACEBO_SEED, n_res: int = PLACEBO_N) -> dict:
    """G10b: 年ごとに実際の門と同じ日数を、その年の中で 5 日の塊を単位に外す。"""
    out = {"what": "年ごとに実際の門と同じ日数を、その年の中で 5 日の塊(循環)で外す", "seed": seed, "n_resamples": n_res,
           "block_days": PLACEBO_BLOCK, "quantile": PLACEBO_Q, "forms": {}}
    for f in ("A", "B"):
        cache = {}
        r = {}
        for price, pnl in pnls.items():
            univ = sorted(d for d in cls if d in pnl)
            n = len(univ)
            rm = removed_mask(univ, cls, f)
            key = (tuple(univ), f)
            if key not in cache:  # 同じ母数なら、始値と中ほどに同じ外し方を当てる
                cache[key] = year_masks(univ, rm, seed, n_res)
            masks, m_y = cache[key]
            if n == 0:
                r[price] = {"actual_bp": None, "n_days": 0, "n_removed": 0, "removed_by_year": m_y}
                continue
            res = placebo_compare([pnl[d] for d in univ], masks, actual[price][f])
            yrs = np.array([d[:4] for d in univ])
            exact = all(bool(np.all(masks[:, yrs == y].sum(axis=1) == m)) for y, m in m_y.items())
            res.update({"n_days": n, "n_removed": int(rm.sum()), "removed_by_year": m_y,
                        "removed_by_year_exactly": exact})
            r[price] = res
        out["forms"][f] = r
    return out


# G3 × G10a の読み(事前登録 PREREG.md「G3 と G10 の組み合わせの読み方」の 5 行。文は事前登録の「書く読み」のまま)。
# 2 列目: True = G10a の 95 点を超える、False = 超えない、None = どちらでも。
READING = (
    ("0 より上", True, "「Binance でも、前の日の区分で外したことが効いた」(予言 P2・P3 が当たった)"),
    ("0 より上", False, "「門の差は 0 より上だが、区分の並びをずらしたのと区別がつかない。差は区分の効きでなく、"
                        "外した時期(年・流れ)の分の公算」。予言は当たったと書かない"),
    ("0 を含む", True, "「区分の効きの向きは対照より上だが、日ごとの区間では 0 と区別がつかない(MDE と並べる)」。"
                       "予言は当たったと書かない"),
    ("0 を含む", False, "「区別がつかない(MDE と並べる)」"),
    ("0 より下", None, "「門で外すと下がった(予言と逆向き)」"),
)


def g3_g10a_reading(g3_mark: str | None, g10a_gt_q95: bool | None) -> dict | None:
    """G3 の印(G7)と G10a の「実際 > 95 点」から READING の行を 1 つ選ぶ。印か比べが無ければ None。"""
    if g3_mark is None or g10a_gt_q95 is None:
        return None
    for i, (m, g, text) in enumerate(READING):
        if m == g3_mark and (g is None or g == bool(g10a_gt_q95)):
            return {"row": i + 1, "g3_mark": g3_mark, "g10a_actual_gt_q95": bool(g10a_gt_q95), "text": text}
    raise ValueError(f"読みの表に無い組み合わせ: {g3_mark!r}, {g10a_gt_q95!r}")


def placebo(pnls: dict, cls: dict, actual: dict, seed: int = PLACEBO_SEED, n_res: int = PLACEBO_N) -> dict:
    """G10c: pnls = {"open": 日 → 損益, "mid": …}、actual = {price: {"A": 実際の差, "B": …}}。母数 = 各 price の全期間の母数。"""
    out = {"what": "区分のある日の全体から 5 日の塊(循環)をでたらめに外す(元の作り方。並べて出すだけ)", "seed": seed,
           "n_resamples": n_res, "block_days": PLACEBO_BLOCK, "quantile": PLACEBO_Q, "forms": {}}
    univs = {price: sorted(d for d in cls if d in pnl) for price, pnl in pnls.items()}
    for f in ("A", "B"):
        cache = {}
        r = {}
        for price, pnl in pnls.items():
            univ = univs[price]
            n = len(univ)
            m = sum(1 for d in univ if not enters(f, cls[d]))
            if (n, m) not in cache:  # 同じ母数なら、始値と中ほどに同じ外し方を当てる
                cache[(n, m)] = placebo_masks(n, m, seed, n_res) if n else np.zeros((n_res, 0), dtype=bool)
            masks = cache[(n, m)]
            res = placebo_compare([pnl[d] for d in univ], masks, actual[price][f]) if n else {"actual_bp": None}
            res.update({"n_days": n, "n_removed": m, "removed_exactly_m": bool(np.all(masks.sum(axis=1) == m))})
            r[price] = res
        out["forms"][f] = r
    return out


def read_all(pnls: dict, cls: dict, boundary: str, carry_days: set, carry_diag: dict | None,
             placebo_n: int = PLACEBO_N) -> dict:
    """pnls: {"open": 日 → 損益, "mid": 日 → 損益}。"""
    out = {"rules": __doc__, "seed": SEED, "n_resamples": N_RES, "block_days": BLOCK, "mde_k": MDE_K,
           "placebo_seed": PLACEBO_SEED, "sens_block_days": SENS_BLOCK,
           "half_boundary_day": boundary, "prices": {}}
    for price, pnl in pnls.items():
        univ = sorted(d for d in cls if d in pnl)
        parts = {"all": univ, "first_half": [d for d in univ if d < boundary],
                 "second_half": [d for d in univ if d >= boundary]}
        r = {"n_classified": len(cls), "n_classified_without_daily_row": sum(1 for d in cls if d not in pnl),
             "n_daily_rows_without_class": sum(1 for d in pnl if d not in cls)}
        for pn, ds in parts.items():
            r[pn] = read_block(ds, pnl, cls)
            r[pn]["by_class"] = by_class(ds, pnl, cls)
            kept = [d for d in ds if d not in carry_days]
            ex = read_block(kept, pnl, cls)
            r[pn]["without_carry_days"] = {"n_days": len(kept), "n_removed": len(ds) - len(kept),
                                           "diffs": ex["diffs"]}
        r["by_year"] = {"open_and_mid": "G9", "years": by_year(univ, pnl, cls)}
        out["prices"][price] = r
    actual = {price: {f: r["all"]["diffs"][f"{f}-none"]["per_day_bp"] for f in ("A", "B")}
              for price, r in out["prices"].items()}
    out["placebo"] = {"primary": "G10a", "G10a": placebo_rot(pnls, cls, actual),
                      "G10b": placebo_year(pnls, cls, actual, n_res=placebo_n),
                      "G10c": placebo(pnls, cls, actual, n_res=placebo_n)}
    out["reading_g3_g10a"] = {
        f: {price: g3_g10a_reading(out["prices"][price]["all"]["diffs"][f"{f}-none"]["mark"],
                                   out["placebo"]["G10a"]["forms"][f][price].get("actual_gt_q95"))
            for price in out["prices"]}
        for f in ("A", "B")}
    out["boundary_carry"] = {"from_diagnostics": carry_diag, "n_carry_days": len(carry_days),
                             "n_carry_days_in_universe": sum(1 for d in carry_days if d in cls)}
    return out


def fmt(s: dict) -> str:
    if s.get("per_day_bp") is None:
        return "—"
    t = f"{s['per_day_bp']:+.3f}"
    if s.get("ci"):
        t += f" [{s['ci'][0]:+.3f}, {s['ci'][1]:+.3f}]"
    if s.get("mde") is not None:
        t += f" MDE {s['mde']:.3f}"
    return t


def fmt_ci(s: dict) -> str:
    """区間と MDE だけ(G6 の感度の列)。"""
    if not s.get("ci"):
        return "—"
    return f"[{s['ci'][0]:+.3f}, {s['ci'][1]:+.3f}] MDE {s['mde']:.3f}"


def to_md(res: dict) -> str:
    L = ["# カード 8 の門(Binance)の読み", "", "`scripts/w4_measure/c8_binance/bn_read_gate.py` が出した。bp、経費の前。"
         "決まりは台本の docstring(G0〜G10)。A と B に順位は付けない。", "",
         f"前半・後半の境(後半の最初の日): {res['half_boundary_day']}", ""]
    J = {"all": "全期間", "first_half": "前半", "second_half": "後半"}
    for price, r in res["prices"].items():
        L += [f"## 約定 = {'始値 → 始値(daily.csv)' if price == 'open' else '中ほど(daily_mid.csv)'}", "",
              f"区分のある日 {r['n_classified']}・そのうち daily の行の無い日 {r['n_classified_without_daily_row']}", "",
              "| 期間 | 形 | 全部の日に均した 1 日あたり [区間] | 入った日だけ [区間] | 入った日の数 | 割合 |", "|---|---|---|---|---|---|"]
        for pn in ("all", "first_half", "second_half"):
            for f in FORMS:
                x = r[pn]["forms"][f]
                L.append(f"| {J[pn]} | {f} | {fmt(x['all_days'])} | {fmt(x['entered_days'])} | {x['n_entered']} | "
                         f"{x['entered_share']:.4f} |" if x["entered_share"] is not None else f"| {J[pn]} | {f} | — | — | 0 | — |")
        L += ["", f"G3 の差。「塊 {SENS_BLOCK} 日」の列は G6 の感度(仮定の塊。並べるだけで、印と読みは塊 {BLOCK} 日の区間で決める)", "",
              f"| 期間 | 差 | 1 日あたり [区間](塊 {BLOCK} 日) | 印 | 塊 {SENS_BLOCK} 日の区間・MDE(感度) | "
              "またぎの日を外した 1 日あたり [区間](外した日数) | 印 |", "|---|---|---|---|---|---|---|"]
        for pn in ("all", "first_half", "second_half"):
            w = r[pn]["without_carry_days"]
            for k in ("A-none", "B-none"):
                a, b = r[pn]["diffs"][k], w["diffs"][k]
                L.append(f"| {J[pn]} | {k} | {fmt(a)} | {a['mark']} | {fmt_ci(a['block20'])} | "
                         f"{fmt(b)}({w['n_removed']}) | {b['mark']} |")
        L += ["", "| 期間 | low [区間] | mid [区間] | high [区間] |", "|---|---|---|---|"]
        for pn in ("all", "first_half", "second_half"):
            c = r[pn]["by_class"]
            L.append(f"| {J[pn]} | " + " | ".join(f"{fmt(c[k])}({c[k]['n_days']})" for k in CLASSES) + " |")
        L += ["", "G9 年ごと(その年の日に均した値)", "",
              "| 年 | 日数 | A − 門なし [区間] | 印 | B − 門なし [区間] | 印 | low [区間](日数) | mid [区間](日数) | high [区間](日数) |",
              "|---|---|---|---|---|---|---|---|---|"]
        for y, yr in r["by_year"]["years"].items():
            a, b, c = yr["diffs"]["A-none"], yr["diffs"]["B-none"], yr["by_class"]
            L.append(f"| {y} | {yr['n_days']} | {fmt(a)} | {a['mark']} | {fmt(b)} | {b['mark']} | "
                     + " | ".join(f"{fmt(c[k])}({c[k]['n_days']})" for k in CLASSES) + " |")
        P = res["placebo"]
        L += ["", "G10 対照群(主 = G10a。「区分で外したことが効いた」と書くのは G10a の 95 点を超えるときだけ)", "",
              "- G10a(主): 区分の並びの循環ずらし(k = 1〜n − 1 の全部、乱数なし)",
              f"- G10b: 年ごとに実際の門と同じ日数を、その年の中で {P['G10b']['block_days']} 日の塊(循環)で外す"
              f"({P['G10b']['n_resamples']} 回、種 {P['G10b']['seed']})",
              f"- G10c: 区分のある日の全体から {P['G10c']['block_days']} 日の塊(循環)をでたらめに外す(元の作り方、"
              f"{P['G10c']['n_resamples']} 回、種 {P['G10c']['seed']})", "",
              "| 対照 | 差 | 外した日数 / 母数 | 対照の数 | 実際の差 | 対照の 95 点 | 実際 > 95 点 | 上側の割合 | 対照の平均 ± 標準偏差 |",
              "|---|---|---|---|---|---|---|---|---|"]
        for g, name in (("G10a", "G10a(主)"), ("G10b", "G10b"), ("G10c", "G10c")):
            for f in ("A", "B"):
                q = P[g]["forms"][f][price]
                if q.get("actual_bp") is None:
                    L.append(f"| {name} | {f} − 門なし | {q['n_removed']} / {q['n_days']} | — | — | — | — | — | — |")
                    continue
                L.append(f"| {name} | {f} − 門なし | {q['n_removed']} / {q['n_days']} | {q['n_resamples']} | "
                         f"{q['actual_bp']:+.3f} | {q['q95_bp']:+.3f} | {'はい' if q['actual_gt_q95'] else 'いいえ'} | "
                         f"{q['upper_share']:.3f} | {q['placebo_mean_bp']:+.3f} ± {q['placebo_sd_bp']:.3f} |")
        L += ["", "G3 × G10a の読み(事前登録の「G3 と G10 の組み合わせの読み方」の行。G3 = 全期間の差の印)", ""]
        for f in ("A", "B"):
            rd = res["reading_g3_g10a"][f][price]
            if rd is None:
                L.append(f"- {f} − 門なし: 読めない(G3 の区間か G10a の比べが無い)")
                continue
            L.append(f"- {f} − 門なし: G3 {rd['g3_mark']}・G10a {'超える' if rd['g10a_actual_gt_q95'] else '超えない'}"
                     f" → 行 {rd['row']}: {rd['text']}")
        L.append("")
    bc = res["boundary_carry"]
    L += ["## セッションをまたいだ持ち高", "", f"diagnostics.json の 5_boundary_carry: {json.dumps(bc['from_diagnostics'], ensure_ascii=False)}",
          f"またぎのあった日の数: {bc['n_carry_days']}(区分のある日のうち {bc['n_carry_days_in_universe']})", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--classes", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with open(a.classes, encoding="utf-8") as fh:
        cj = json.load(fh)
    pnls = {k: read_daily(os.path.join(a.run_dir, f)) for k, f in PRICES.items()}
    with open(os.path.join(a.run_dir, "diagnostics.json"), encoding="utf-8") as fh:
        dg = json.load(fh).get("5_boundary_carry")
    carry = read_carry_days(os.path.join(a.run_dir, "boundary_carry_days.csv"))
    res = read_all(pnls, cj["classes"], cj["half_boundary_day"], carry, dg)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "gate_read.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, allow_nan=False)
    with open(os.path.join(a.out, "GATE_READ.md"), "w", encoding="utf-8") as fh:
        fh.write(to_md(res) + "\n")
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
