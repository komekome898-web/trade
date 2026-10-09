"""測定の後に足す計算(測定器のコードは変えない)。

week_block: 測定器と同じ P_t の系列に、bot.bt.validation.bootstrap.block_bootstrap_ci の circular を
  L_w = max(ceil(Politis-White b), 10,080 本)・1,000 回・測定器と同じ種で当てる。
  全体の平均の 95% 区間(百分位、np.quantile 線形)と se(再標本の平均の標準偏差、ddof 1)、
  MDE = bot.bt.validation.power.mde(n, sd = se × √n, 5% 両側, 検出力 80%, 正規近似)(測定器の C5 e と同じ式)。
  照合: 同じ関数で L = 測定器の L(1 日)でも計算し、measure.json の overall の区間と並べる。
"""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np

from bot.bt.repro import canonical
from bot.bt.validation import block_bootstrap_ci, mde
from bot.research.cards.measure import ALPHA, METHOD, N_RESAMPLES, POWER

WEEK_BARS = 10_080


def _boot(P: np.ndarray, L: int, seed: int) -> dict:
    ci = block_bootstrap_ci([float(x) for x in P], block_len=L, n_resamples=N_RESAMPLES, seed=seed, alpha=ALPHA, method=METHOD,
                            statistic="mean")
    n = len(P)
    return {"block_len": int(L), "n_over_block": n / L, "ci": [ci.lo, ci.hi], "se": ci.se,
            "mde": mde(n=n, sd=ci.se * math.sqrt(n), alpha=ALPHA, power=POWER, sides=2, approx="normal"),
            "estimate": ci.estimate}


def week_block(P: np.ndarray, out: dict, seed: int) -> dict:
    pw_b = out["block"]["pw_b"]
    L_day = out["block"]["block_len"]
    L_w = max(int(math.ceil(pw_b)), WEEK_BARS)
    week = _boot(P, L_w, seed)
    day_check = _boot(P, L_day, seed)
    ov = out["overall"]["mean_pct"]
    return {
        "rule": "L_w = max(ceil(Politis-White circular b of P_t), 10080)(W4 の仕様 §3 の 1 週。測定器の L は 1 日 = 1440 が下限)",
        "formula": {"ci": "block_bootstrap_ci(P_t, block_len=L, n_resamples=1000, seed, alpha=0.05, method='circular', "
                          "statistic='mean') の 2.5%・97.5% の百分位(np.quantile 線形)",
                    "se": "1,000 個の再標本の平均の標準偏差(ddof 1)",
                    "mde": "mde(n, sd = se × √n, alpha 0.05, power 0.80, sides 2, approx 'normal') = (z_0.975 + z_0.80) × se"},
        "seed": seed, "n_resamples": N_RESAMPLES, "method": METHOD, "n": int(len(P)),
        "pw_b": pw_b, "mean_pct": float(np.mean(P)),
        "day": {"block_len": L_day, "ci": ov.get("ci"), "se": ov.get("se"), "mde": ov.get("mde"),
                "from": "measure.json の overall.mean_pct(測定器が出した 1 日の区間)"},
        "day_recomputed": {**day_check, "note": "照合用。同じ関数・同じ種・同じ L で P_t から直接計算した 1 日の区間"},
        "week": week,
    }


def write_json(obj, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_sha(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def summary_row(name: str, out: dict, wb: dict) -> dict:
    ov = out["overall"]["mean_pct"]
    return {"variant": name, "n": out["n_pnl"], "mean_pct": ov["estimate"], "ci_day": ov.get("ci"),
            "ci_week": wb["week"]["ci"], "mde_day": ov.get("mde"), "mde_week": wb["week"]["mde"],
            "L_day": out["block"]["block_len"], "L_week": wb["week"]["block_len"],
            "nonzero_share": out["frequency"]["nonzero_share"], "changes": out["frequency"]["changes"],
            "control_percentile": ov.get("control_percentile"),
            "drift_removed_pct": out["overall"]["drift_removed_pct"]["estimate"],
            "drift_removed_ci_day": out["overall"]["drift_removed_pct"].get("ci")}
