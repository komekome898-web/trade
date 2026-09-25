"""Item 3 battery (検証・再現・出力): the scenes and their expected answers.

Every expected answer below is derived WITHOUT looking at any engine: by a
closed form (normal quantiles, the circular Bartlett sum, the deflated-Sharpe
formula), by counting/filtering the synthetic input the scene itself states,
or by an enumeration written out in this file (CSCV for PBO).  Each scene
carries ``how`` = how its answer was derived, in Japanese, for DEFINITIONS.md.

Scene fields:
    id, viewpoint (C3-1 .. C3-19, REQUIREMENTS.md §2), kind ("値" | "能力"),
    measures (何を測るか), how (正解の出し方), input (one request to a target,
    JSON-able; the forms are in i3_protocol.py), expect (the answer and the
    rule the judge applies), optional variant (a second request whose correct
    outcome is a refusal or a stated predicate; see i3_judge.py).

Nothing here imports an engine.  The only outside file a scene references is
the repository's own 4th-gate module (scripts/_research_audit_gate.py), which
the sealed-read scenes copy into their scratch root because that module IS
the gate the requirement names (load_sealed's 4th gate).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import statistics
from datetime import datetime, timedelta, timezone

NS = 1_000_000_000
H = 3600 * NS
DAY = 24 * H
T0 = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()) * NS  # 2026-01-01T00:00:00Z
TABS = ["概要", "前提", "損益", "取引", "約定の質", "費用", "分布", "検証", "再現性", "データ品質"]
WARNING = "動作確認の実行。相場の結論には使わない"


def iso(t_ns: int) -> str:
    return datetime.fromtimestamp(t_ns // NS, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# C3-1  calendar Train/Val/OOS and walk-forward
# ---------------------------------------------------------------------------
# 10 UTC days, uneven density (so a row-fraction split can never coincide
# with a calendar split): day d has K[d] rows at hours (3 + 5 j) mod 24.
_K = [2, 5, 3, 8, 1, 6, 4, 7, 2, 9]


def _split_rows() -> list[int]:
    rows = []
    for d, k in enumerate(_K):
        for h in sorted({(3 + 5 * j) % 24 for j in range(k)}):
            rows.append(T0 + d * DAY + h * H)
    return sorted(rows)


SPLIT_ROWS = _split_rows()


def _cut(rows, lo, hi):
    return [t for t in rows if (lo is None or t >= lo) and (hi is None or t < hi)]


def _day_ns(date: str, tz_hours: int) -> int:
    y, m, d = map(int, date.split("-"))
    return int(datetime(y, m, d, tzinfo=timezone(timedelta(hours=tz_hours))).timestamp()) * NS


def _split_expect(tz_hours: int) -> dict:
    a, b = _day_ns("2026-01-07", tz_hours), _day_ns("2026-01-09", tz_hours)
    return {"train": _cut(SPLIT_ROWS, None, a), "val": _cut(SPLIT_ROWS, a, b), "oos": _cut(SPLIT_ROWS, b, None)}


WF_ROWS = [T0 + i * H for i in range(20 * 24)]  # 20 UTC days, every hour


def _wf_expect(train_d, test_d, step_d, total_d):
    folds, k = [], 0
    while (k * step_d + train_d + test_d) <= total_d:
        s = T0 + k * step_d * DAY
        folds.append({"train": _cut(WF_ROWS, s, s + train_d * DAY),
                      "test": _cut(WF_ROWS, s + train_d * DAY, s + (train_d + test_d) * DAY)})
        k += 1
    return folds


def _pnl_a(t):  # +1 on days 0-2, -1 on days 3-5, +1 on 6-8 ...  (regime of 3 days)
    return 1.0 if ((t - T0) // DAY // 3) % 2 == 0 else -1.0


def _pnl_b(t):  # opposite regime, half the size, plus a small constant
    return -0.5 * _pnl_a(t) + 0.25


def _fit_eval_expect():
    out = []
    for f in _wf_expect(5, 2, 2, 20):
        sa = sum(_pnl_a(t) for t in f["train"])
        sb = sum(_pnl_b(t) for t in f["train"])
        choice = "a" if sa >= sb else "b"
        fn = _pnl_a if choice == "a" else _pnl_b
        out.append({"choice": choice, "test_score": sum(fn(t) for t in f["test"])})
    return out


# ---------------------------------------------------------------------------
# C3-2  purge / embargo / CPCV (rule of López de Prado, AFML ch. 7, as stated
#       in DEFINITIONS.md; label end = start + 2.5 h so no equality occurs)
# ---------------------------------------------------------------------------
PE_ROWS = [T0 + i * H for i in range(30)]
PE_LABEL_END = [t + 5 * H // 2 for t in PE_ROWS]


def _purged_train(test_blocks: list[list[int]], embargo_rows: int) -> list[int]:
    """Row indices kept for training (rule written in DEFINITIONS.md)."""
    n = len(PE_ROWS)
    keep = set(range(n))
    for blk in test_blocks:
        keep -= set(blk)
    for blk in test_blocks:
        t_start = PE_ROWS[blk[0]]
        max_end = max(PE_LABEL_END[i] for i in blk)
        for i in range(0, blk[0]):  # left: label must end at/before test start
            if PE_LABEL_END[i] > t_start:
                keep.discard(i)
        first_free = next((i for i in range(n) if PE_ROWS[i] >= max_end), n)
        for i in range(blk[-1] + 1, min(n, first_free + embargo_rows)):  # right: purge then embargo
            keep.discard(i)
    return sorted(keep)


CPCV_GROUPS = [list(range(g * 5, g * 5 + 5)) for g in range(6)]


# ---------------------------------------------------------------------------
# C3-3  block bootstrap: AR(1) phi 0.6, n 2000, seeded standard normal shocks
# ---------------------------------------------------------------------------
def _ar1(n=2000, phi=0.6, seed=20260925):
    r = random.Random(seed)
    x, out = 0.0, []
    for _ in range(n + 200):  # 200 burn-in
        x = phi * x + r.gauss(0.0, 1.0)
        out.append(x)
    return [round(v, 6) for v in out[200:]]


BOOT_X = _ar1()
BOOT_L = 20


def _circular_bartlett_se(x, L):
    n = len(x)
    m = sum(x) / n
    d = [v - m for v in x]
    gam = [sum(d[t] * d[(t + h) % n] for t in range(n)) / n for h in range(L)]
    var = (gam[0] + 2 * sum((1 - h / L) * gam[h] for h in range(1, L))) / n
    return m, math.sqrt(var), math.sqrt(gam[0] / n)


BOOT_MEAN, BOOT_SE, BOOT_SE_IID = _circular_bartlett_se(BOOT_X, BOOT_L)


# ---------------------------------------------------------------------------
# C3-4 / C3-5 / C3-6  closed forms
# ---------------------------------------------------------------------------
_N = statistics.NormalDist()
EULER_GAMMA = 0.5772156649015329


def mde(n, sd, alpha, power, sides):
    return (_N.inv_cdf(1 - alpha / sides) + _N.inv_cdf(power)) * sd / math.sqrt(n)


def dsr(sr, T, skew, kurt, n_trials, var_trials):
    """Deflated Sharpe ratio (Bailey & López de Prado 2014, eq. for SR0 and PSR).
    sr per period; kurt NON-excess (normal = 3); var_trials = variance of the
    trials' per-period SR estimates."""
    sr0 = math.sqrt(var_trials) * ((1 - EULER_GAMMA) * _N.inv_cdf(1 - 1 / n_trials)
                                   + EULER_GAMMA * _N.inv_cdf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr * sr)
    return _N.cdf(z)


PBO_M = [[4, 5, 4, 1], [-2, 2, 3, 1], [2, -3, 2, -1], [5, -3, 1, -1],
         [-2, 5, 5, 3], [-1, 3, 4, -1], [3, 1, -2, -3], [-2, 2, 2, -3]]


def _pbo_cscv(M, S=4, metric="mean"):
    rows_per = len(M) // S
    blocks = [list(range(b * rows_per, (b + 1) * rows_per)) for b in range(S)]
    N = len(M[0])

    def perf(rows, j):
        x = [M[r][j] for r in rows]
        m = sum(x) / len(x)
        return m if metric == "mean" else m / statistics.stdev(x)

    lams = []
    for comb in itertools.combinations(range(S), S // 2):
        IS = [r for b in comb for r in blocks[b]]
        OOS = [r for b in range(S) if b not in comb for r in blocks[b]]
        pis = [perf(IS, j) for j in range(N)]
        po = [perf(OOS, j) for j in range(N)]
        best = max(range(N), key=lambda j: pis[j])
        rank = sorted(po).index(po[best]) + 1
        w = rank / (N + 1)
        lams.append({"is_blocks": list(comb), "best": best, "oos_rank": rank, "logit": math.log(w / (1 - w))})
    return sum(1 for x in lams if x["logit"] <= 0) / len(lams), lams


PBO_VALUE, PBO_LAMBDAS = _pbo_cscv(PBO_M)
assert (PBO_VALUE, [x["oos_rank"] for x in PBO_LAMBDAS]) == (
    _pbo_cscv(PBO_M, metric="sharpe")[0], [x["oos_rank"] for x in _pbo_cscv(PBO_M, metric="sharpe")[1]])


# ---------------------------------------------------------------------------
# C3-6  sealed data (a scratch repository root laid out like load_sealed's)
# ---------------------------------------------------------------------------
SEAL_CSV = "ts,v\n" + "".join(f"2026-01-{d:02d}T00:00:00Z,{d}\n" for d in range(1, 11))
SEAL_RECORD = json.dumps({
    "unit": "u1", "forward_start": "2026-03-01T00:00:00+00:00",
    "files": [{"path": "data/d.csv", "time_column": "ts", "seal_from_ts": "2026-01-08T00:00:00+00:00"}],
}, ensure_ascii=False, indent=1)


def _action_log(verdict: str) -> str:
    body = "\n".join(f"指摘 {i}: 合成の場面のための記録の行であり、実際の監査の記録ではない。" for i in range(1, 7))
    return ("# 合成の場面の台帳\n\n## 監査の記録\n監査対象: u1/封印の開封\n"
            "監査役: owner-auditor(合成の場面のための名前の行)\n" + body + f"\n判定: {verdict}\n")


def _seal_files(record=True, approval=True, audit="通す"):
    fs = [{"path": "data/d.csv", "text": SEAL_CSV},
          {"path": "scripts/_research_audit_gate.py", "copy_from_repo": "scripts/_research_audit_gate.py"},
          {"path": "docs/AUDITOR/ACTION_LOG.md", "text": _action_log(audit)}]
    if record:
        fs.append({"path": "backtest_data/phase2_sealed/u1/SEALED.json", "text": SEAL_RECORD})
    if approval:
        fs.append({"path": "backtest_data/phase2_sealed/u1/UNSEAL_APPROVED", "text": "合成の場面の承認のファイル\n"})
    return fs


TOKEN = "I_UNDERSTAND_THIS_IS_FINAL_EVAL"


def _sealed_input(env=True, approval=True, token=True, audit="通す"):
    return {"op": "sealed_read", "unit": "u1", "path": "data/d.csv",
            "env": ({"PHASE2_FINAL_EVAL": "u1"} if env else {}),
            "token": TOKEN if token else "not-the-token",
            "files": _seal_files(approval=approval, audit=audit)}


# ---------------------------------------------------------------------------
# the fixed run (C3-7 .. C3-10, C3-15 .. C3-19)
# ---------------------------------------------------------------------------
LEGS = [  # (decision time, side, price flat for +-60 s around it)
    (T0 + 1 * H, "buy", 10_000_000.0), (T0 + 1 * H + 300 * NS, "sell", 10_100_000.0),
    (T0 + 2 * H, "buy", 10_200_000.0), (T0 + 2 * H + 300 * NS, "sell", 10_149_000.0),
    (T0 + 3 * H, "buy", 10_000_000.0), (T0 + 3 * H + 300 * NS, "sell", 10_030_000.0),
]
RUN_BP = [100.0, -50.0, 30.0]  # (10.1M-10M)/10M, (10.149M-10.2M)/10.2M, (10.03M-10M)/10M in bp


def _tape(shift_px: float = 0.0) -> str:
    rows = []
    for t, _side, px in LEGS:
        for k in range(-12, 13):  # every 5 s from -60 s to +60 s
            rows.append((t + k * 5 * NS, px + shift_px))
    return "t_ns,px,qty\n" + "".join(f"{t},{p:.1f},5.0\n" for t, p in sorted(rows))


TAPE = _tape()
TAPE_C = _tape(shift_px=1000.0)  # different content (every price +1000), used only by C3-8
PREREG = "# 合成の事前登録\n\n合成の場面のための事前登録の本文。相場についての主張は無い。\n"


def run_config(seed_note: str = "") -> dict:
    return {
        "instrument": "FX_BTC_JPY",
        "strategy": {"kind": "fixed_times",
                     "legs": [{"t_ns": t, "side": s, "qty": 0.01} for t, s, _ in LEGS]},
        "order_type": "market",
        "fill": {"market": "next_trade_price"},
        "latency_ns": {"feed": 0, "order": 0, "cancel": 0},
        "costs": {"maker_fee_rate": 0.0, "taker_fee_rate": 0.0, "funding": "none",
                  "source": "合成の場面の宣言(費用 0 を明示)"},
    }


def run_spec(purpose="動作確認", seed=11, prereg=False, strategy="fixed_times", data="data/tape.csv",
             config=None):
    cfg = config if config is not None else run_config()
    spec = {"data": [data], "config": cfg, "seed": seed, "strategy": strategy, "runs_dir": "runs"}
    if purpose is not None:
        spec["purpose"] = purpose
    if prereg:
        spec["prereg"] = "prereg/PREREG.md"
    return spec


def _permuted(d):
    if isinstance(d, dict):
        return {k: _permuted(d[k]) for k in reversed(list(d))}
    if isinstance(d, list):
        return [_permuted(v) for v in d]
    return d


RUN_FILES = [{"path": "data/tape.csv", "text": TAPE}, {"path": "prereg/PREREG.md", "text": PREREG}]


def _run_input(**kw):
    return {"op": "run", "files": RUN_FILES, "run": run_spec(**kw)}


# ---------------------------------------------------------------------------
# C3-11 .. C3-14  metrics on stated synthetic records
# ---------------------------------------------------------------------------
DIST_BP = [15, -12, 80, 3, 0, 22, -5, 41, 12, 7, -30, 18, 4, 55, -5, 10, 25, 8, 30, 20, 15]
DIST_TRADES = []
for _i, _bp in enumerate(DIST_BP):
    _side = "buy" if _i % 3 else "sell"
    _entry = 10000.0
    _exit = _entry + _bp if _side == "buy" else _entry - _bp
    DIST_TRADES.append({"id": f"t{_i + 1}", "side": _side, "qty": 1.0, "entry_px": _entry, "exit_px": _exit,
                        "entry_t_ns": T0 + _i * H, "exit_t_ns": T0 + _i * H + 600 * NS})


def _q7(xs, p):  # linear interpolation between order statistics (Hyndman & Fan type 7)
    s = sorted(xs)
    h = (len(s) - 1) * p
    lo = math.floor(h)
    return s[lo] + (h - lo) * (s[min(lo + 1, len(s) - 1)] - s[lo])


QPROBS = [0.05, 0.25, 0.5, 0.75, 0.95]

BPH_TRADES = [
    {"id": "a", "side": "buy", "qty": 1.0, "entry_px": 10000.0, "exit_px": 10010.0,
     "entry_t_ns": T0 + 10 * H, "exit_t_ns": T0 + 10 * H + 30 * 60 * NS},
    {"id": "b", "side": "buy", "qty": 1.0, "entry_px": 10000.0, "exit_px": 9996.0,
     "entry_t_ns": T0 + 11 * H, "exit_t_ns": T0 + 12 * H},
    {"id": "c", "side": "sell", "qty": 1.0, "entry_px": 10000.0, "exit_px": 9994.0,
     "entry_t_ns": T0 + 13 * H + 30 * 60 * NS, "exit_t_ns": T0 + 14 * H},
]

FILL_ORDERS = [
    {"id": "o1", "t_ns": T0, "side": "buy", "type": "limit", "px": 10000.0, "qty": 1.0},
    {"id": "o2", "t_ns": T0 + 10 * NS, "side": "sell", "type": "limit", "px": 10200.0, "qty": 1.0},
    {"id": "o3", "t_ns": T0 + 20 * NS, "side": "sell", "type": "limit", "px": 10100.0, "qty": 1.0},
    {"id": "o4", "t_ns": T0 + 30 * NS, "side": "buy", "type": "limit", "px": 9950.0, "qty": 1.0},
    {"id": "o5", "t_ns": T0 + 40 * NS, "side": "buy", "type": "limit", "px": 9800.0, "qty": 1.0},
]
FILL_FILLS = [
    {"order_id": "o1", "t_ns": T0 + 100 * NS, "px": 10000.0, "qty": 1.0},
    {"order_id": "o3", "t_ns": T0 + 220 * NS, "px": 10100.0, "qty": 1.0},
    {"order_id": "o4", "t_ns": T0 + 400 * NS, "px": 9950.0, "qty": 1.0},
]
FILL_END_NS = T0 + 1000 * NS  # orders not filled by then are missed (expired)

# mid path with a sample exactly at every fill time and every fill time + 60 s / 300 s
MO_BUY = [(T0 + 100 * NS, 10000.0), (T0 + 400 * NS, 9950.0)]  # (fill time, fill px) of buys o1, o4
MO_SELL = [(T0 + 220 * NS, 10100.0)]
MIDS = {  # t (s after T0) -> mid
    100: 10002.0, 160: 9990.0, 220: 10098.0, 280: 10110.0, 400: 9952.0, 460: 9940.0,
    520: 10085.0, 700: 9985.0,
}
MID_PATH = sorted((T0 + s * NS, v) for s, v in MIDS.items())


def _mid_at(t):  # exact sample (the path has one at every time asked)
    for tt, v in MID_PATH:
        if tt == t:
            return v
    raise KeyError(t)


def _markouts(fills, sign):
    return {str(h): [sign * (_mid_at(t + h * NS) - px) for t, px in fills] for h in (60, 300)}


COST_FILLS = [
    {"id": "f1", "t_ns": T0 + 0 * NS, "side": "buy", "qty": 1.0, "px": 10000.0, "liquidity": "taker", "mid": 9995.0},
    {"id": "f2", "t_ns": T0 + 60 * NS, "side": "sell", "qty": 1.0, "px": 10050.0, "liquidity": "maker", "mid": 10052.0},
    {"id": "f3", "t_ns": T0 + 120 * NS, "side": "sell", "qty": 0.5, "px": 10100.0, "liquidity": "taker", "mid": 10105.0},
    {"id": "f4", "t_ns": T0 + 180 * NS, "side": "buy", "qty": 0.5, "px": 10090.0, "liquidity": "maker", "mid": 10088.0},
]
COST_FUNDING = [{"t_ns": T0 + 30 * NS, "rate": 0.0001, "mark": 10020.0},
                {"t_ns": T0 + 150 * NS, "rate": 0.0001, "mark": 10100.0}]
COST_RATES = {"maker_fee_rate": 0.0002, "taker_fee_rate": 0.0005}


def _cost_expect():
    fee = {"maker": 0.0, "taker": 0.0}
    spread = 0.0
    for f in COST_FILLS:
        fee[f["liquidity"]] += f["px"] * f["qty"] * COST_RATES[f["liquidity"] + "_fee_rate"]
        spread += (1 if f["side"] == "buy" else -1) * (f["px"] - f["mid"]) * f["qty"]
    funding = 0.0
    for ev in COST_FUNDING:
        pos = sum((1 if f["side"] == "buy" else -1) * f["qty"] for f in COST_FILLS if f["t_ns"] < ev["t_ns"])
        funding += pos * ev["mark"] * ev["rate"]
    return {"maker_fee": fee["maker"], "taker_fee": fee["taker"], "spread": spread, "funding": funding}


EXIT_TRADES = [("tp", 50.0), ("sl", -30.0), ("tp", 40.0), ("time_exit", -5.0), ("signal", 10.0),
               ("sl", -25.0), ("tp", 45.0)]
EQUITY = [100.0, 110.0, 105.0, 120.0, 90.0, 95.0, 130.0, 117.0]


def _dd():
    peak, worst_abs, worst_pct = -math.inf, 0.0, 0.0
    for v in EQUITY:
        peak = max(peak, v)
        worst_abs = max(worst_abs, peak - v)
        worst_pct = max(worst_pct, (peak - v) / peak * 100)
    return worst_abs, worst_pct


# ---------------------------------------------------------------------------
# the scenes
# ---------------------------------------------------------------------------
def _dash_input():
    return {"op": "dashboard", "files": RUN_FILES,
            "runs": [{"key": "A", **run_spec(purpose="動作確認")},
                     {"key": "B", **run_spec(purpose="研究", prereg=True)}]}


SCENES: list[dict] = []


def scene(**kw):
    SCENES.append(kw)


_ROWS_NOTE = ("観測は各区分の行の時刻の列(`rows`)か、半開区間の境界(`bounds` = [始まり, 終わり))のどちらでもよい。"
              "境界で返したときは、判定の側が場面の行にその境界を当てて行の集合に直して比べる。")

# --- C3-1
scene(id="v1-split-utc", viewpoint="C3-1", kind="値",
      measures="暦日(UTC の日付の境目)で Train / Val / OOS に切れるか。行の数の割合ではなく日付で切るか。",
      how=("10 日分の行(日ごとの行の数が 2・5・3・8・1・6・4・7・2・9 と偏る)を、境目 2026-01-07 00:00 UTC と "
           "2026-01-09 00:00 UTC で半開区間 [始まり, 07日) / [07日, 09日) / [09日, 終わり] に分けた行を数えた。"
           "行の数の割合で切ると境目がずれる並びにしてある。" + _ROWS_NOTE),
      input={"op": "calendar_split", "rows": SPLIT_ROWS, "tz": "UTC", "train_end": "2026-01-07", "val_end": "2026-01-09"},
      expect={"check": "parts", "parts": _split_expect(0)})
scene(id="v1-split-jst", viewpoint="C3-1", kind="値",
      measures="暦日の境目を時間帯つきで決められるか(Asia/Tokyo の 0 時 = 前日 15:00 UTC で切るか)。",
      how="v1-split-utc と同じ行を、境目 2026-01-07 00:00 JST(= 01-06 15:00 UTC)と 01-09 00:00 JST(= 01-08 15:00 UTC)で分けた。" + _ROWS_NOTE,
      input={"op": "calendar_split", "rows": SPLIT_ROWS, "tz": "Asia/Tokyo", "train_end": "2026-01-07", "val_end": "2026-01-09"},
      expect={"check": "parts", "parts": _split_expect(9)})
scene(id="v1-wf-rolling", viewpoint="C3-1", kind="値",
      measures="walk-forward で窓を複数回切り直せるか(学習 5 日・評価 2 日・2 日ずつ進める転がる窓)。",
      how=("20 日分の毎時の行。k 番目の窓 = 学習 [T0+2k 日, T0+2k+5 日)・評価 [T0+2k+5 日, T0+2k+7 日)、"
           "評価の終わりが 20 日目を越えない k = 0..6 の 7 窓。各窓の行を数えた(学習 120 行・評価 48 行)。" + _ROWS_NOTE),
      input={"op": "walk_forward", "rows": WF_ROWS, "tz": "UTC", "train_days": 5, "test_days": 2, "step_days": 2,
             "mode": "rolling"},
      expect={"check": "folds", "folds": _wf_expect(5, 2, 2, 20)})
scene(id="v1-wf-equal", viewpoint="C3-1", kind="値",
      measures="学習と評価が同じ幅で、評価の幅ずつ進む walk-forward(学習 2 日・評価 2 日・2 日ずつ、16 日で 7 窓)を切れるか。",
      how=("20 日分の毎時の行の最初の 16 日。k 番目の窓 = 学習 [T0+2k 日, T0+2k+2 日)・評価 [T0+2k+2 日, T0+2k+4 日)、"
           "k = 0..6。各窓の行を数えた(学習・評価とも 48 行)。" + _ROWS_NOTE),
      input={"op": "walk_forward", "rows": WF_ROWS[:16 * 24], "tz": "UTC", "train_days": 2, "test_days": 2,
             "step_days": 2, "mode": "rolling"},
      expect={"check": "folds", "folds": [{"train": _cut(WF_ROWS, T0 + 2 * k * DAY, T0 + (2 * k + 2) * DAY),
                                           "test": _cut(WF_ROWS, T0 + (2 * k + 2) * DAY, T0 + (2 * k + 4) * DAY)}
                                          for k in range(7)]})
scene(id="a1-wf-fit-eval", viewpoint="C3-1", kind="能力",
      measures="walk-forward の各窓で「学習区間で選び、評価区間で測る」を回して、窓ごとの評価を出せるか。",
      how=("行ごとに 2 つの損益の列 a・b(a は 3 日ごとに +1 と −1 が入れ替わる、b = −0.5×a + 0.25)。"
           "各窓で学習区間の合計が大きい方(同じなら a)を選び、評価区間のその列の合計を評価とする。"
           "窓は v1-wf-rolling と同じ 7 窓。選びと評価を窓ごとに手で足した(値は 0.25 の倍数で丸めの誤差が出ない)。"
           "選ぶ規則は利用者の書く戦略(adapter が対象の walk-forward の口の上に書く)。"),
      input={"op": "walk_forward_eval", "rows": WF_ROWS,
             "columns": {"a": [_pnl_a(t) for t in WF_ROWS], "b": [_pnl_b(t) for t in WF_ROWS]},
             "tz": "UTC", "train_days": 5, "test_days": 2, "step_days": 2, "mode": "rolling",
             "rule": "学習区間の列の合計が大きい方を選ぶ(同じなら a)。評価 = 評価区間のその列の合計"},
      expect={"check": "fold_evals", "folds": _fit_eval_expect()})

# --- C3-2
_PE_NOTE = ("規則(AFML 7 章の PurgedKFold と同じ形): 評価の塊ごとに、(左)学習の行はラベルの終わりが評価の最初の行の時刻"
            "以下のものだけ残す。(右)評価の行のラベルの終わりの最大値以上の時刻に始まる最初の行を「空き」とし、評価の最後の行の"
            "次から「空き」の手前までを除き(purge)、さらに「空き」から embargo の行数を除く。ラベルの終わりは行の時刻 + 2.5 時間"
            "(行の時刻と一致しないので「以下」と「未満」の違いが出ない)。")
scene(id="v2-purge-embargo", viewpoint="C3-2", kind="値",
      measures="学習と評価の間の purge(ラベルの重なりの除去)と embargo(評価のあとの空白)を入れた学習の行の集合を出せるか。",
      how=_PE_NOTE + " 30 行(毎時)、評価 = 行 12〜17、embargo = 2 行(= 2 時間)。左: 行 i のラベルの終わり i+2.5 ≤ 12 → i ≤ 9。"
      "右: 評価のラベルの終わりの最大 = 行 19.5 の時刻 → 「空き」= 行 20、embargo で 20・21 を除く → 22 から。学習 = 行 0〜9 と 22〜29。"
      "(purge だけなら 0〜9 と 20〜29、embargo だけなら 0〜11 と 20〜29 で、どれとも違う。)",
      input={"op": "purged_split", "rows": PE_ROWS, "label_end": PE_LABEL_END, "test_rows": list(range(12, 18)),
             "embargo_rows": 2, "embargo_ns": 2 * H},
      expect={"check": "index_set", "train": _purged_train([list(range(12, 18))], 2)})
scene(id="v2-cpcv-split", viewpoint="C3-2", kind="値",
      measures="CPCV(組合せの purge つき交差検証)で分割の数・経路の数と、ある分割の purge・embargo つきの学習の行を出せるか。",
      how=_PE_NOTE + " 30 行を 6 群(5 行ずつ)、評価に 2 群 → 分割の数 C(6,2) = 15、経路の数 = 2/6 × 15 = 5。"
      "評価の群 {1, 3}(行 5〜9 と 15〜19)、embargo = 1 行で、塊ごとに規則を当てた: 塊 5〜9 → 行 3・4 を左で、10・11 を右で除き、"
      "embargo で 12。塊 15〜19 → 13・14 を左で、20・21 を右で除き、embargo で 22。学習 = 行 0・1・2・23〜29。",
      input={"op": "cpcv", "rows": PE_ROWS, "label_end": PE_LABEL_END, "n_groups": 6, "n_test_groups": 2,
             "embargo_rows": 1, "embargo_ns": 1 * H, "want_train_for": [1, 3]},
      expect={"check": "cpcv_split", "n_splits": 15, "n_paths": 5,
              "train": _purged_train([CPCV_GROUPS[1], CPCV_GROUPS[3]], 1)})
scene(id="a2-cpcv-paths", viewpoint="C3-2", kind="能力",
      measures="CPCV の分割から、各経路が全群をちょうど 1 回ずつ評価で覆う 5 本の経路を組み立てられるか。",
      how=("正解は性質で決まる: 経路は 5 本、各経路は 6 群のそれぞれに「その群を評価に含む分割」を 1 つずつ当てる、"
           "(分割, 群) の組(15 分割 × 2 群 = 30 組)が 5 本の経路にちょうど 1 回ずつ現れる。どの組をどの経路に置くかは"
           "決まらないので、判定はこの 3 つの性質だけを見る。"),
      input={"op": "cpcv_paths", "rows": PE_ROWS, "label_end": PE_LABEL_END, "n_groups": 6, "n_test_groups": 2,
             "embargo_rows": 1, "embargo_ns": 1 * H},
      expect={"check": "cpcv_paths", "n_groups": 6, "n_test_groups": 2, "n_paths": 5})

# --- C3-3
scene(id="v3-block-bootstrap", viewpoint="C3-3", kind="値",
      measures="自己相関のある系列で、ブロック単位の再抽出による平均の 95% 信頼区間を出せるか(iid の再抽出では幅が狭すぎる)。",
      how=(f"AR(1)(係数 0.6、標準正規の撹乱、種 20260925、捨てる頭 200、n = 2000、小数 6 桁)の平均の標準誤差の正解 = "
           f"円環の標本自己共分散に Bartlett の重み (1 − |h|/L) を掛けた和(L = 20)/ n の平方根 = {BOOT_SE:.6f}"
           f"(円環のブロック・ブートストラップの分散の閉じた式、Politis & Romano 1992)。判定: 区間の中点が標本平均 {BOOT_MEAN:.6f} "
           f"から 0.25 × 標準誤差以内、かつ (上 − 下) / (2 × 1.96) が標準誤差の 0.85〜1.15 倍。iid の再抽出なら "
           f"{BOOT_SE_IID:.6f}(正解の {BOOT_SE_IID / BOOT_SE:.2f} 倍)で外れる。再抽出の回数 2000、種 7。ブロックの長さを"
           "指定できない対象は自分の既定の長さで走らせ、その旨を注記に残す。"),
      input={"op": "block_bootstrap", "x": BOOT_X, "block_len": BOOT_L, "n_resamples": 2000, "seed": 7, "alpha": 0.05,
             "statistic": "mean"},
      expect={"check": "ci_band", "mean": BOOT_MEAN, "se": BOOT_SE, "center_tol_se": 0.25, "width_band": [0.85, 1.15]})

# --- C3-4
scene(id="v4-mde-two-sided", viewpoint="C3-4", kind="値",
      measures="n と分散から、検出できる最小効果量(MDE)を計算できるか(両側)。",
      how=f"正規近似の閉じた式 MDE = (z(1 − α/2) + z(検出力)) × sd / √n、n = 400、sd = 10 bp、α = 0.05 両側、検出力 0.8 → {mde(400, 10, 0.05, 0.8, 2):.6f} bp。相対の許容 1e-6(閉じた式なので、許すのは Φ⁻¹ の実装の差だけ。z を 1.96・0.84 に丸めると 6e-4 ずれて外れる)。",
      input={"op": "mde", "n": 400, "sd": 10.0, "alpha": 0.05, "power": 0.8, "sides": 2, "approx": "normal"},
      expect={"check": "close", "values": {"mde": mde(400, 10, 0.05, 0.8, 2)}, "rel": 1e-6})
scene(id="v4-mde-one-sided", viewpoint="C3-4", kind="値",
      measures="片側・別の α と検出力でも MDE を計算できるか。",
      how=f"同じ式、n = 100、sd = 5 bp、α = 0.01 片側、検出力 0.9 → {mde(100, 5, 0.01, 0.9, 1):.6f} bp。相対の許容 1e-6(閉じた式なので、許すのは Φ⁻¹ の実装の差だけ。z を 1.96・0.84 に丸めると 6e-4 ずれて外れる)。",
      input={"op": "mde", "n": 100, "sd": 5.0, "alpha": 0.01, "power": 0.9, "sides": 1, "approx": "normal"},
      expect={"check": "close", "values": {"mde": mde(100, 5, 0.01, 0.9, 1)}, "rel": 1e-6})
_CASES = [
    {"estimate": 0.3, "se": 0.5, "n": 400, "sd": 10.0, "interest": 3.0},
    {"estimate": 0.3, "se": 0.5, "n": 400, "sd": 10.0, "interest": 1.0},
    {"estimate": 2.0, "se": 0.5, "n": 400, "sd": 10.0, "interest": 3.0},
]
scene(id="v4-verdict", viewpoint="C3-4", kind="値",
      measures="MDE と欲しい効果から、結果を 陰性 / 不明 / 陽性 に分けられるか(research-protocol §5 の三分類)。",
      how=("research-protocol §4.1・§5: 陰性 = 欲しい効果 > MDE で効果が検出されなかった / 不明 = 欲しい効果 ≤ MDE / "
           "陽性 = 効果が検出された(両側 α = 0.05、|推定 / 標準誤差| > 1.96)。MDE = v4-mde-two-sided と同じ 1.4008 bp。"
           "例 1: 推定 0.3 ± 0.5(z = 0.6、非有意)、欲しい効果 3.0 > MDE → 陰性。例 2: 同じ結果、欲しい効果 1.0 < MDE → 不明。"
           "例 3: 推定 2.0 ± 0.5(z = 4)→ 陽性。"),
      input={"op": "verdict", "alpha": 0.05, "power": 0.8, "sides": 2, "cases": _CASES},
      expect={"check": "equal", "values": {"verdicts": ["陰性", "不明", "陽性"]}})
scene(id="a4-no-mde-no-negative", viewpoint="C3-4", kind="能力",
      measures="MDE を書けない(n か sd が無い)主張を陰性として扱わないことが構造で強制されるか。",
      how=("対照 = v4-verdict の例 1(陰性になるのが正解)。変形 = 同じ結果から n と sd を抜いた(MDE を計算できない)。"
           "変形の正解は「陰性を返さない」= 拒む、または 不明 を返す。陰性を返したら不一致。"),
      input={"op": "verdict", "alpha": 0.05, "power": 0.8, "sides": 2, "cases": [_CASES[0]]},
      expect={"check": "equal", "values": {"verdicts": ["陰性"]}},
      variant={"op": "verdict", "alpha": 0.05, "power": 0.8, "sides": 2,
               "cases": [{"estimate": 0.3, "se": 0.5, "interest": 3.0}]},
      variant_expect={"refuse_or_equal": {"verdicts": ["不明"]}})

# --- C3-5
_DSR_IN = {"sr": 0.1, "T": 1000, "skew": -0.5, "kurtosis": 4.0, "n_trials": 10, "var_trials": 0.001}
scene(id="v5-dsr", viewpoint="C3-5", kind="値",
      measures="試行回数を踏まえた deflated Sharpe を計算できるか。",
      how=("Bailey & López de Prado(2014)の閉じた式: SR0 = √V × ((1 − γ) Φ⁻¹(1 − 1/N) + γ Φ⁻¹(1 − 1/(N e)))、"
           "DSR = Φ((SR − SR0) √(T − 1) / √(1 − 歪度 × SR + (尖度 − 1)/4 × SR²))。SR は 1 期あたり 0.1、T = 1000、"
           "歪度 −0.5、尖度 4(正規 = 3 の数え方)、N = 10、試行の SR の分散 V = 0.001(= 1/T、雑音だけの試行の分散)。"
           f"→ {dsr(**{'sr': 0.1, 'T': 1000, 'skew': -0.5, 'kurt': 4.0, 'n_trials': 10, 'var_trials': 0.001}):.6f}。絶対の許容 1e-6(閉じた式なので、許すのは Φ と Φ⁻¹ の実装の差 = 1e-9 の桁だけ)。"),
      input={"op": "dsr", **_DSR_IN},
      expect={"check": "close", "values": {"dsr": dsr(0.1, 1000, -0.5, 4.0, 10, 0.001)}, "abs": 1e-6})
def _dsr_series(T=500, seed=20260926):
    r = random.Random(seed)
    out = []
    for _ in range(T):
        x = r.gauss(0.004, 0.01)
        if r.random() < 0.04:  # occasional down jumps: negative skew, fat tails
            x -= abs(r.gauss(0.03, 0.01))
        out.append(round(x, 6))
    return out


def _moments(x, ddof_sd=0, adjusted=False):
    """(SR, skew, kurtosis non-excess) of a series under one of the conventions a paper-faithful
    implementation may pick: the sd in SR with ddof 0 or 1, and the plain or the adjusted
    (Fisher-Pearson G1 / G2) sample skewness and kurtosis."""
    n = len(x)
    m = sum(x) / n
    m2 = sum((v - m) ** 2 for v in x) / n
    m3 = sum((v - m) ** 3 for v in x) / n
    m4 = sum((v - m) ** 4 for v in x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - ddof_sd))
    g1, g2 = m3 / m2 ** 1.5, m4 / m2 ** 2
    if adjusted:
        g1 = g1 * math.sqrt(n * (n - 1)) / (n - 2)
        g2 = ((n + 1) * (g2 - 3) + 6) * (n - 1) / ((n - 2) * (n - 3)) + 3
    return m / sd, g1, g2


DSR_X = _dsr_series()
_DT = len(DSR_X)
DSR_R_VALUE = dsr(*_moments(DSR_X)[:1], _DT, *_moments(DSR_X)[1:], 10, 1 / _DT)
DSR_R_TOL = max(abs(dsr(*_moments(DSR_X, d, a)[:1], _DT, *_moments(DSR_X, d, a)[1:], 10, 1 / _DT) - DSR_R_VALUE)
                for d in (0, 1) for a in (False, True))
_SR, _SK, _KU = _moments(DSR_X)
scene(id="v5-dsr-returns", viewpoint="C3-5", kind="値",
      measures="収益の系列と試行回数から deflated Sharpe を計算できるか(積率を系列から自分で出す形)。",
      how=(f"合成の収益の系列(平均 0.004・標準偏差 0.01 の正規に、確率 0.04 で下向きの跳び、種 20260926、T = {_DT}、小数 6 桁)。"
           f"系列の積率(母集団の数え方: SR = 平均 / 標準偏差(ddof 0)= {_SR:.6f}、歪度 {_SK:.6f}、尖度 {_KU:.6f}(正規 = 3))を"
           f"v5-dsr の閉じた式に入れた。N = 10、V = 1/T。→ {DSR_R_VALUE:.6f}。許容 = 論文どおりの実装が選びうる流儀"
           f"(SR の標準偏差の ddof 0 / 1 × 歪度・尖度の補正なし / あり、の 4 通り)で値が動く幅の最大 = {DSR_R_TOL:.2e}。"
           "式の項を落とした実装(例: 分散の項 (尖度 − 1)/4 を (尖度 − 3)/4 にしたもの)はこの幅を越えて外れる。"),
      input={"op": "dsr_returns", "returns": DSR_X, "n_trials": 10, "var_trials": 1 / _DT},
      expect={"check": "close", "values": {"dsr": DSR_R_VALUE}, "abs": DSR_R_TOL})
scene(id="v5-pbo", viewpoint="C3-5", kind="値",
      measures="Probability of Backtest Overfitting(CSCV)を計算できるか。",
      how=("8 行 × 4 戦略の性能の行列を 4 塊(2 行ずつ)に分け、塊の半分(2 塊)を学習に取る 6 通りのそれぞれで、学習の平均が"
           "最大の戦略の評価側での順位 r(1 = 最悪)から ω = r / 5、λ = ln(ω / (1 − ω))。PBO = λ ≤ 0 の割合。"
           "6 通りの r = " + ", ".join(str(x["oos_rank"]) for x in PBO_LAMBDAS) + f" → PBO = {PBO_VALUE}。"
           "性能を平均でなく Sharpe(平均 / 標準偏差)で測っても順位はすべて同じになる行列にしてある。"),
      input={"op": "pbo", "matrix": PBO_M, "n_blocks": 4, "metric": "mean"},
      expect={"check": "close", "values": {"pbo": PBO_VALUE}, "abs": 1e-9})

# --- C3-6
scene(id="v6-iter-count", viewpoint="C3-6", kind="値",
      measures="周回数の台帳(ITER)に試行を累積し、別の読み手で開き直しても数が保たれるか。",
      how="台帳の置き場を空にして試行を 3 件登録 → 数 3。台帳を新しく開き直す → 3。もう 1 件登録 → 4。正解 [3, 3, 4]。",
      input={"op": "iter_ledger", "ledger_dir": "ledger",
             "first": [{"design": "d1", "sr": 0.05}, {"design": "d1", "sr": 0.10}, {"design": "d1", "sr": 0.02}],
             "more": [{"design": "d1", "sr": 0.08}]},
      expect={"check": "equal", "values": {"counts": [3, 3, 4]}})
scene(id="v6-iter-dsr", viewpoint="C3-6", kind="値",
      measures="台帳の周回数が多重性(deflated Sharpe の試行回数)に算入されるか。",
      how=(f"台帳に 4 件登録したあと、最良の SR 0.1(T = 1000、歪度 0、尖度 3、V = 0.001)の DSR を台帳の数 N で出す。"
           f"正解 = N = 4 の閉じた式(v5-dsr の式)= {dsr(0.1, 1000, 0.0, 3.0, 4, 0.001):.6f}。"
           f"試行の数を数えない(N = 1、SR0 = 0)なら Φ(0.1 × √999 / √1.005) = {_N.cdf(0.1 * math.sqrt(999) / math.sqrt(1.005)):.6f} で外れる。絶対の許容 1e-6(閉じた式なので、許すのは Φ と Φ⁻¹ の実装の差 = 1e-9 の桁だけ)。"),
      input={"op": "iter_dsr", "ledger_dir": "ledger",
             "trials": [{"design": "d1", "sr": s} for s in (0.05, 0.10, 0.02, 0.08)],
             "best": {"sr": 0.1, "T": 1000, "skew": 0.0, "kurtosis": 3.0}, "var_trials": 0.001},
      expect={"check": "close", "values": {"dsr": dsr(0.1, 1000, 0.0, 3.0, 4, 0.001)}, "abs": 1e-6})
for gate, kw, what in [("env", {"env": False}, "環境変数 PHASE2_FINAL_EVAL が単位の名と一致しない"),
                       ("approval", {"approval": False}, "承認のファイル UNSEAL_APPROVED が無い"),
                       ("token", {"token": False}, "確認のトークンが違う"),
                       ("audit", {"audit": "止める"}, "監査の台帳の最後の判定が「通す」でない(4 つ目の門)")]:
    scene(id=f"a6-sealed-{gate}", viewpoint="C3-6", kind="能力",
          measures=f"封印区間は 4 門を全部通らない限り読めないか(この場面は門「{what}」)。",
          how=("load_sealed の 4 門の形の置き場(合成の根: 封印の記録 SEALED.json・承認のファイル・監査の台帳・4 つ目の門の"
               "モジュール)を場面が作る。対照 = 4 門を全部通す → 封印区間の行(ts ≥ 2026-01-08 の 3 行、v = 8, 9, 10)。"
               f"変形 = {what} ほかは対照と同じ → 拒むのが正解。"),
          input=_sealed_input(), expect={"check": "equal", "values": {"v": [8, 9, 10]}},
          variant=_sealed_input(**kw), variant_expect={"refuse": True})
scene(id="a6-sealed-bypass", viewpoint="C3-6", kind="能力",
      measures="実行のための普通の読み込みの経路からも、封印区間の行が読めないか(4 門を迂回できないか)。",
      how=("対照 = 封印の記録が無い根で data/d.csv を普通に読む → 10 行全部(v = 1..10)。変形 = 同じ根に封印の記録"
           "(ts ≥ 2026-01-08 を封印)を置いて同じ読み込み → 正解は「拒む」か「封印区間を除いた 7 行(v = 1..7)だけを返す」。"),
      input={"op": "data_read", "path": "data/d.csv", "time_column": "ts",
             "files": [{"path": "data/d.csv", "text": SEAL_CSV}]},
      expect={"check": "equal", "values": {"v": list(range(1, 11))}},
      variant={"op": "data_read", "path": "data/d.csv", "time_column": "ts",
               "files": [{"path": "data/d.csv", "text": SEAL_CSV},
                         {"path": "backtest_data/phase2_sealed/u1/SEALED.json", "text": SEAL_RECORD}]},
      variant_expect={"refuse_or_equal": {"v": list(range(1, 8))}})

# --- C3-7
_RUN_NOTE = ("固定の実行 = 合成の約定の列 data/tape.csv(3 往復の各時刻の前後 60 秒は値が一定)に、時刻だけで決まる成行の"
             "3 往復(買い → 5 分後に売り)を費用 0・遅延 0 を明示して回す。")
scene(id="v7-data-sha256", viewpoint="C3-7", kind="値",
      measures="実行記録に、読んだデータの sha256 が残るか。",
      how=_RUN_NOTE + f" 正解 = data/tape.csv のバイト列の sha256 = {sha256_text(TAPE)}(場面が書いた文字列から計算)。",
      input=_run_input(), expect={"check": "record", "field": "data_sha256", "value": {"data/tape.csv": sha256_text(TAPE)}})
scene(id="v7-seed", viewpoint="C3-7", kind="値",
      measures="実行記録に、乱数の種が残るか。", how=_RUN_NOTE + " 渡した種は 11。正解 = 11。",
      input=_run_input(), expect={"check": "record", "field": "seed", "value": 11})
scene(id="v7-config", viewpoint="C3-7", kind="値",
      measures="実行記録に、設定が全部そのまま残るか。", how=_RUN_NOTE + " 正解 = 渡した設定の辞書そのもの(JSON として等しい)。",
      input=_run_input(), expect={"check": "record", "field": "config", "value": run_config()})
scene(id="v7-git-sha", viewpoint="C3-7", kind="値",
      measures="実行記録に、コードの git の SHA が残るか。",
      how=_RUN_NOTE + " 正解 = 判定の時点でリポジトリの `git rev-parse HEAD` が返す 40 桁(判定の側が自分で打つ。版が動くので繰り返しの比較からは外す)。",
      input=_run_input(), expect={"check": "record", "field": "git_sha", "value": {"oracle": "git_head"}})
scene(id="a7-diff-hash", viewpoint="C3-7", kind="能力",
      measures="実行記録に、作業中の差分のハッシュが残るか。",
      how=(_RUN_NOTE + " 同じ場面の中で固定の実行を 2 回回し、2 回とも 16 桁以上の 16 進の文字列で、互いに等しいこと(同じ作業木)。"
           "差分の中身そのものは場面の外(リポジトリの作業木)で決まるので値は比べない。版と作業木が動くので繰り返しの比較からは外す。"
           "差分が変わったときに値が変わることは場面にできない(リポジトリを書き換えない)ので、批評家が見る。"),
      input={**_run_input(), "repeat": 2}, expect={"check": "record_stable_hex", "field": "diff_hash", "min_len": 16})
scene(id="a7-version", viewpoint="C3-7", kind="能力",
      measures="実行記録に、版(エンジンの版の文字列)が残るか。",
      how=_RUN_NOTE + " 正解 = 空でない文字列(版の値そのものは対象ごとに違うので比べない)。",
      input=_run_input(), expect={"check": "record_nonempty", "field": "version"})

# --- C3-8
_IDS_RUNS = [run_spec(), run_spec(), run_spec(config=_permuted(run_config())), run_spec(seed=12),
             run_spec(data="data/tape_c.csv")]
scene(id="v8-run-id", viewpoint="C3-8", kind="値",
      measures="実行 ID が内容のハッシュ(同じ内容なら同じ、内容が違えば違う、時刻や乱数に依らない)か。",
      how=("5 回の実行: ① 固定の実行 ② ①と同じ(1.1 秒あけて)③ ①と同じ設定を鍵の順だけ逆にした辞書 ④ 種だけ 12 "
           "⑤ データだけ別(値が全部 +1000 のファイル data/tape_c.csv)。正解の関係 = ①=②=③、④と⑤は①とも互いとも違う。"
           "ID の文字列そのものはコードの版で変わるので、繰り返しの比較は関係(どれとどれが等しいか)で行う。"),
      input={"op": "run_ids", "files": RUN_FILES + [{"path": "data/tape_c.csv", "text": TAPE_C}], "runs": _IDS_RUNS,
             "sleep_before_s": [0, 1.1, 0, 0, 0]},
      expect={"check": "id_relations", "groups": [[0, 1, 2], [3], [4]]})

# --- C3-9
scene(id="a9-auto-repro", viewpoint="C3-9", kind="能力",
      measures="同じ入力で 2 回回して一致を自動で確かめる仕組みがあり、一致しないときに一致しないと言えるか。",
      how=("対照 = 固定の実行を対象の自動の確認にかける → 一致(真)が正解。変形 = 戦略だけを「種を使わない乱数」"
           "(各往復の数量を 0.01 × (1 + os.urandom の 1 バイト / 256))に替える → 2 回の結果(数量と円の損益)が違うので"
           "「一致しない」(偽)が正解。bp は数量に依らず同じなので、bp だけを比べる確認は変形を見逃す。"),
      input={"op": "auto_repro", "files": RUN_FILES, "run": run_spec()},
      expect={"check": "equal", "values": {"reproduced": True}},
      variant={"op": "auto_repro", "files": RUN_FILES, "run": run_spec(strategy="unseeded_random")},
      variant_expect={"equal": {"reproduced": False}})

# --- C3-10
scene(id="v10-prereg-sha", viewpoint="C3-10", kind="値",
      measures="事前登録のファイルのハッシュが実行記録に入るか。",
      how=_RUN_NOTE + f" 目的 研究、事前登録 prereg/PREREG.md。正解 = そのバイト列の sha256 = {sha256_text(PREREG)}。",
      input=_run_input(purpose="研究", prereg=True),
      expect={"check": "record", "field": "prereg_sha256", "value": sha256_text(PREREG)})
scene(id="a10-research-needs-prereg", viewpoint="C3-10", kind="能力",
      measures="目的が 研究 の実行は、事前登録のハッシュが無いと作れないか。",
      how="対照 = 目的 研究 + 事前登録つき → 実行ができ、記録の目的が 研究。変形 = 目的 研究・事前登録なし → 拒むのが正解。",
      input=_run_input(purpose="研究", prereg=True), expect={"check": "record", "field": "purpose", "value": "研究"},
      variant=_run_input(purpose="研究", prereg=False), variant_expect={"refuse": True})

# --- C3-11
scene(id="v11-distribution", viewpoint="C3-11", kind="値",
      measures="1 件ごとの bp・分位・負の割合を、平均 1 個に潰さずに出せるか。",
      how=("21 件の往復(入りの値 10000、出の値 = 買いなら 10000 + bp、売りなら 10000 − bp、費用 0)。1 件ごとの bp = "
           "向き × (出 − 入) / 入 × 10000。分位は順序統計量の線形補間(Hyndman & Fan の 7 型、numpy の既定): "
           "p = 0.05・0.25・0.5・0.75・0.95 は (n − 1) p = 1・5・10・15・19 が整数なので並べた値そのもの。"
           f"負の割合 = 負の件数 / 件数(0 は負に数えない)= {sum(1 for b in DIST_BP if b < 0)}/21。"),
      input={"op": "trade_metrics", "trades": DIST_TRADES, "want": ["per_trade_bp", "quantiles", "neg_frac"],
             "quantile_probs": QPROBS, "quantile_method": "linear"},
      expect={"check": "close", "abs": 1e-9, "values": {
          "per_trade_bp": [float(b) for b in DIST_BP],
          "quantiles": {str(p): float(_q7(DIST_BP, p)) for p in QPROBS},
          "neg_frac": sum(1 for b in DIST_BP if b < 0) / len(DIST_BP)}})

# --- C3-12
scene(id="v12-bp-per-hour", viewpoint="C3-12", kind="値",
      measures="建玉を持っていた時間(露出)あたりの bp(bp/時)を出せるか。",
      how=("3 件: 10:00–10:30 に +10 bp、11:00–12:00 に −4 bp、13:30–14:00 に +6 bp(売り)。露出の時間 = 0.5 + 1 + 0.5 = 2 時間、"
           "bp/時 = (10 − 4 + 6) / 2 = 6。最初の入りから最後の出までの 4 時間で割ると 3 になる(罠)。"),
      input={"op": "trade_metrics", "trades": BPH_TRADES, "want": ["exposure_hours", "bp_per_hour"]},
      expect={"check": "close", "abs": 1e-9, "values": {"exposure_hours": 2.0, "bp_per_hour": 6.0}})

# --- C3-13
scene(id="v13-fill-rate", viewpoint="C3-13", kind="値",
      measures="約定率と取り逃し(埋まらなかった指値の件数)を出せるか。",
      how="指値 5 件(o1〜o5)、期限 1000 秒までに埋まったのは o1・o3・o4。約定率 = 3/5 = 0.6、取り逃し = 2 件。",
      input={"op": "fill_metrics", "orders": FILL_ORDERS, "fills": FILL_FILLS, "end_t_ns": FILL_END_NS},
      expect={"check": "close", "abs": 1e-12, "values": {"fill_rate": 0.6, "missed": 2}})
scene(id="v13-markout-buy", viewpoint="C3-13", kind="値",
      measures="買いの約定の逆選択の markout を複数の時間窓で出せるか。",
      how=("markout(h)= 向き × (仲値(t + h) − 約定の値)、値の単位(買いは向き +1)。仲値の列は約定の時刻と t + 60 秒・"
           "t + 300 秒のそれぞれにちょうど 1 点を置いた(「以前で最後」と「以後で最初」の流儀の差が出ない)。"
           f"買い 2 件: 60 秒 = {_markouts(MO_BUY, 1)['60']}、300 秒 = {_markouts(MO_BUY, 1)['300']}。"),
      input={"op": "markout", "fills": [{"t_ns": t, "px": p, "side": "buy", "qty": 1.0} for t, p in MO_BUY],
             "mids": MID_PATH, "horizons_s": [60, 300]},
      expect={"check": "close", "abs": 1e-9, "values": {"markout": _markouts(MO_BUY, 1)}})
scene(id="v13-markout-sell", viewpoint="C3-13", kind="値",
      measures="売りの約定の markout で向きを正しく扱えるか。",
      how=f"同じ式で売りは向き −1。売り 1 件(10100、t = 220 秒): 60 秒 = {_markouts(MO_SELL, -1)['60']}、300 秒 = {_markouts(MO_SELL, -1)['300']}。",
      input={"op": "markout", "fills": [{"t_ns": t, "px": p, "side": "sell", "qty": 1.0} for t, p in MO_SELL],
             "mids": MID_PATH, "horizons_s": [60, 300]},
      expect={"check": "close", "abs": 1e-9, "values": {"markout": _markouts(MO_SELL, -1)}})

# --- C3-14
_CE = _cost_expect()
scene(id="v14-cost-breakdown", viewpoint="C3-14", kind="値",
      measures="費用を種類ごと(maker 手数料・taker 手数料・スプレッド・資金調達)の内訳で出せるか。",
      how=("約定 4 件と資金調達 2 回。手数料 = 値 × 数量 × 率(maker 0.0002・taker 0.0005)。スプレッドの費用 = 向き × "
           "(約定の値 − その時の仲値)× 数量(買い +1・売り −1、全約定)。資金調達 = その時刻の建玉 × 基準値 × 率(買い建てが払う)。"
           f"maker = {_CE['maker_fee']:.6f}、taker = {_CE['taker_fee']:.6f}、スプレッド = {_CE['spread']:.6f}、"
           f"資金調達 = {_CE['funding']:.6f}(円)。"),
      input={"op": "cost_breakdown", "fills": COST_FILLS, "funding": COST_FUNDING, "rates": COST_RATES},
      expect={"check": "close", "abs": 1e-9, "values": {"costs": _CE}})
_EX = {}
for _r, _p in EXIT_TRADES:
    _EX.setdefault(_r, {"n": 0, "pnl": 0.0})
    _EX[_r]["n"] += 1
    _EX[_r]["pnl"] += _p
scene(id="v14-exit-reasons", viewpoint="C3-14", kind="値",
      measures="決済理由ごとに件数と損益を集計できるか。",
      how="7 件の往復に決済理由(tp・sl・time_exit・signal)と円の損益を付けた。理由ごとに数えて足した: "
          + "、".join(f"{k} = {v['n']} 件 {v['pnl']:+.0f}" for k, v in _EX.items()) + "。",
      input={"op": "exit_reasons", "trades": [{"id": f"x{i}", "reason": r, "pnl": p} for i, (r, p) in enumerate(EXIT_TRADES)]},
      expect={"check": "close", "abs": 1e-9, "values": {"by_reason": _EX}})
_DDA, _DDP = _dd()
scene(id="v14-dd-pct", viewpoint="C3-14", kind="値",
      measures="最大ドローダウン(率)を出せるか。",
      how=f"資産の列 {EQUITY}。各時点の最高値からの下落率の最大 = (120 − 90) / 120 = {_DDP:.1f} %。",
      input={"op": "drawdown", "equity": EQUITY, "t_ns": [T0 + i * H for i in range(len(EQUITY))]},
      expect={"check": "close", "abs": 1e-9, "values": {"max_dd_pct": _DDP}})
scene(id="v14-dd-abs", viewpoint="C3-14", kind="値",
      measures="最大ドローダウン(額)を出せるか。",
      how=f"同じ列。最高値からの下落額の最大 = 120 − 90 = {_DDA:.1f}(後半の 130 → 117 の 13 より大きい)。",
      input={"op": "drawdown", "equity": EQUITY, "t_ns": [T0 + i * H for i in range(len(EQUITY))]},
      expect={"check": "close", "abs": 1e-9, "values": {"max_dd_abs": _DDA}})

# --- C3-15
scene(id="v15-purpose-on-exports", viewpoint="C3-15", kind="値",
      measures="指標の書き出しの全部に、実行の目的(動作確認)が載るか。",
      how=_RUN_NOTE + " 目的 動作確認。正解 = 書き出しのファイルが 1 つ以上あり、その全部が目的の欄 = 動作確認 を持つ。",
      input=_run_input(), expect={"check": "exports_purpose", "value": "動作確認"})
scene(id="a15-purpose-required", viewpoint="C3-15", kind="能力",
      measures="目的を書かない実行(と書き出し)が作れないことが構造で強制されるか。",
      how="対照 = 目的 動作確認 → 実行ができ、記録の目的 = 動作確認。変形 = 目的の欄を抜いた同じ実行 → 拒むのが正解。",
      input=_run_input(), expect={"check": "record", "field": "purpose", "value": "動作確認"},
      variant=_run_input(purpose=None), variant_expect={"refuse": True})

# --- C3-16 .. C3-19 (the dashboard, fed by two fixed runs: A = 動作確認, B = 研究 + 事前登録)
_DASH_NOTE = ("固定の実行を 2 つ(A = 目的 動作確認、B = 目的 研究 + 事前登録)対象自身の書き出しで作り、対象のダッシュボードを"
              "空いている口で起こして読む。")
scene(id="v16-run-tabs", viewpoint="C3-16", kind="値",
      measures="実行ごとの項目別タブが要件の 10 項目(概要 / 前提 / 損益 / 取引 / 約定の質 / 費用 / 分布 / 検証 / 再現性 / データ品質)か。",
      how=_DASH_NOTE + " 正解 = A と B のそれぞれのタブの名の並び = 要件の 10 項目の順(名の後ろの括弧書きは除いて比べる)。",
      input=_dash_input(), expect={"check": "dash_run_tabs", "tabs": TABS})
scene(id="a16-list-to-run", viewpoint="C3-16", kind="能力",
      measures="「バックテスト」タブがあり、実行の一覧から実行ごとのタブへ辿れるか。",
      how=_DASH_NOTE + " 正解 = 最上段のタブに「バックテスト」があり、実行の一覧に A と B の実行 ID が両方あり、一覧の各 ID から辿った先がその実行のタブである。",
      input=_dash_input(), expect={"check": "dash_list"})
scene(id="v17-no-external", viewpoint="C3-17", kind="値",
      measures="バックテストの画面が外部(CDN など)からスクリプト・スタイル・画像を読み込まないか。",
      how=_DASH_NOTE + " 画面と、画面が読み込むスクリプト・スタイルに現れる http:// か https:// の読み込み先の一覧。正解 = 空。",
      input=_dash_input(), expect={"check": "equal", "values": {"external_refs": []}})
scene(id="a17-japanese", viewpoint="C3-17", kind="能力",
      measures="バックテストの画面の文言(タブの名・警告)が日本語か。",
      how=_DASH_NOTE + " 正解 = 最上段の「バックテスト」、実行ごとの 10 のタブの名、A の警告の文が、どれも仮名か漢字を含む(英字だけの名が無い)。",
      input=_dash_input(), expect={"check": "dash_japanese"})
scene(id="v18-wired-values", viewpoint="C3-18", kind="値",
      measures="ダッシュボードに出る値が、書き出しの値と配線どおりに繋がっているか(値で見る配線)。",
      how=_DASH_NOTE + f" A の 1 件ごとの bp = {RUN_BP}(10,000,000 → 10,100,000 など、場面の値から手で計算)、負の割合 = 1/3。正解 = ダッシュボードが A について出すこの 2 つ。",
      input=_dash_input(), expect={"check": "dash_values", "run": "A", "values": {"per_trade_bp": RUN_BP, "neg_frac": 1 / 3}, "abs": 1e-6})
scene(id="a18-wiring-test-api", viewpoint="C3-18", kind="能力",
      measures="ダッシュボードの配線の試験が、バックテストの API の経路が切れたことを検出するか。",
      how=("対照 = 対象の配線の試験をそのまま回す → 通る(真)が正解。変形 = 場面集の壊し具(http.server の上で、"
           "/api/ で始まり backtest を含む GET を 404 にする)を効かせて同じ試験を回す → 落ちる(偽)が正解。"),
      input={"op": "wiring_test", "break": None}, expect={"check": "equal", "values": {"passed": True}},
      variant={"op": "wiring_test", "break": "api_route"}, variant_expect={"equal": {"passed": False}})
scene(id="a18-wiring-test-tab", viewpoint="C3-18", kind="能力",
      measures="ダッシュボードの配線の試験が、「バックテスト」タブが消えたことを検出するか。",
      how=("対照 = そのまま → 通る(真)。変形 = 壊し具(http.server の応答の本文の「バックテスト」を同じ長さの空白に替える)を効かせる"
           " → 落ちる(偽)が正解。"),
      input={"op": "wiring_test", "break": None}, expect={"check": "equal", "values": {"passed": True}},
      variant={"op": "wiring_test", "break": "tab_label"}, variant_expect={"equal": {"passed": False}})
scene(id="v19-warning-all-tabs", viewpoint="C3-19", kind="値",
      measures="目的が 動作確認 の実行は全タブに「動作確認の実行。相場の結論には使わない」を出し、研究 の実行には出さないか。",
      how=_DASH_NOTE + " 正解 = A の 10 タブすべてに警告の文がある(真)、B の 10 タブのどれにも無い(偽)。",
      input=_dash_input(), expect={"check": "dash_warning", "warning": WARNING, "tabs": TABS})


def expected(scene: dict) -> dict:
    return scene["expect"]


def by_id(sid: str) -> dict:
    for s in SCENES:
        if s["id"] == sid:
            return s
    raise KeyError(sid)


VIEWPOINTS = {
    "C3-1": "暦日 Train/Val/OOS と walk-forward", "C3-2": "purge・embargo つき walk-forward と CPCV",
    "C3-3": "ブロック・ブートストラップ", "C3-4": "MDE の計算", "C3-5": "deflated Sharpe と PBO",
    "C3-6": "周回数の台帳(ITER)と封印区間の 4 門", "C3-7": "実行記録の内容", "C3-8": "実行 ID = 内容のハッシュ",
    "C3-9": "同一入力の再現性の自動確認", "C3-10": "事前登録ハッシュの実行記録への組み込み",
    "C3-11": "平均で潰さず分布で出す", "C3-12": "露出あたり(bp/時)", "C3-13": "約定率・取り逃し・逆選択 markout",
    "C3-14": "費用の内訳・決済理由・ドローダウン", "C3-15": "実行目的(動作確認/研究)の指標書き出しへの記載",
    "C3-16": "「バックテスト」タブと実行一覧→項目別タブの構成", "C3-17": "日本語表示・CDN 不使用",
    "C3-18": "配線の試験", "C3-19": "動作確認実行の全タブ警告表示",
}
