#!/usr/bin/env python3
"""続く/止まるの単位 — Jev を後半 5,000 件(+ Q7 対照候補)に呼ぶ(2026-09-20)。

委任文: `docs/DATA/delegations/20260920_o3c_signal_continue_jev_prompt.md`
設計:   `docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md`(§2 Q3/Q4/Q7, §7)

**この道具がすること**
  - 後半のプリント(`rows_continue.csv.gz` の `kind == print` かつ `half == 後半`)から、
    側 × 材料 1(`same_side_count_60s_and_elapsed`)の 3 群(0 / 1〜2 / 3 以上)で
    層化無作為に 5,000 件(種 20260920)を選ぶ。**前半には呼ばない。**
  - 各件に `scripts/o3c_signal_continue.py` の下見(200 件)と**同じ** state 作り
    (`jev_state_for_print`。ts 以前だけ、p₀・ts 以後は渡さない)・同じ問い(`JEV_QUESTIONS`)・
    同じ Jev(`jev-1.13.0`)・同じ 2 件/秒を、そのままその関数を import して使う。
  - 同じ 5,000 件のうち Q7 の対照候補(`q7_matched_print_id` で結ばれた
    `kind == q7_candidate` の行)がある件についても、候補の state(向き = 直前 10 秒の
    変位の符号 `dir_sign`、ts 相当 = 候補の `ts_ms`)で同じ問いを呼ぶ。
  - 呼び出しは `data/jev/continue/*.jsonl` に 1 行ずつ追記する(**確率もここにだけ書く**)。
    再実行すると、そこに無い件だけを呼ぶ(冪等な再開)。
  - 表は `backtest_data/o3c_signal_continue_20260920/jev/` に書く。
    **既存の `q0〜q7.csv` / `tables.md` / `summary.json` / 上位の `MD5SUMS` は変更しない。**

判定語(陽性/陰性/有意/差あり/検出されず/支持/棄却)は書かない。`paper_logs/` は開かない。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# 既存の下見の実装(state の作り方・noul の問い・criteria・2 件/秒)をそのまま使う。
_spec = importlib.util.spec_from_file_location(
    "o3c_signal_continue", SCRIPTS_DIR / "o3c_signal_continue.py")
cont = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cont)

NAN = float("nan")
SEED = 20260920
N_SAMPLE = 5000
RATE_PER_SEC = 2.0
MODEL = "jev-1.13.0"

ROWS_PATH = REPO_ROOT / "backtest_data" / "o3c_signal_continue_20260920" / "rows_continue.csv.gz"
PRINTS_CSV_PATH = cont.DEFAULT_ROWS  # PrintsCSV(rows_prints.csv.gz) と同じ母集団
DATA_ROOT = cont.DEFAULT_DATA_ROOT
OUT_DIR = REPO_ROOT / "backtest_data" / "o3c_signal_continue_20260920" / "jev"
STATE_DIR = REPO_ROOT / "data" / "jev" / "continue"  # 確率はここにだけ
MANIFEST_PATH = OUT_DIR / "selection_manifest.json"
PRINTS_ANSWERS_PATH = STATE_DIR / "prints_answers.jsonl"
Q7_ANSWERS_PATH = STATE_DIR / "q7_answers.jsonl"

STRATA_SIDES = ("SELL", "BUY")            # 下見(run_jev_preview)と同じ順
STRATA_GROUPS = ("0", "1-2", "3+")


# ===========================================================================
# 1. 純関数(テスト対象)
# ===========================================================================
def count_group(cnt) -> str:
    """材料 1(直前 60 秒の同じ側の件数)を 0 / 1〜2 / 3 以上 の 3 群に分ける。"""
    if cnt is None or (isinstance(cnt, float) and not math.isfinite(cnt)):
        return "欠測"
    c = float(cnt)
    if c <= 0:
        return "0"
    if c <= 2:
        return "1-2"
    return "3+"


def select_5000(df_bh: pd.DataFrame, seed: int = SEED, n_sample: int = N_SAMPLE,
                mat1_col: str = "mat1_same_side_count_60s_and_elapsed") -> list:
    """後半のプリント(`half == 後半` の行だけを渡すこと)から、側 × 材料1の3群で
    層化無作為に `n_sample` 件を選ぶ。`print_id` の list を返す(呼び出し順 = 選定順)。

    下見(`run_jev_preview`)と同じ組み立て: 層のリストを固定順で回し、層ごとに
    プールを sort → `rng.shuffle` → 先頭 k 件を取る。層の数で割った余りは
    列挙順の先頭の層から 1 件ずつ足す。
    """
    cnt = pd.to_numeric(df_bh[mat1_col], errors="coerce")
    grp = cnt.map(count_group)
    strata = [(s, g) for s in STRATA_SIDES for g in STRATA_GROUPS]
    rng = random.Random(seed)
    per = n_sample // len(strata)
    extra = n_sample - per * len(strata)
    picked = []
    for i, (s, g) in enumerate(strata):
        pool = sorted(df_bh.loc[(df_bh["side"] == s) & (grp == g), "print_id"].tolist())
        k = per + (1 if i < extra else 0)
        rng.shuffle(pool)
        picked += pool[:k]
    return picked


def predict_continue(prob, threshold: float = 0.5):
    """prob >= threshold を「続く」と判断する。prob が無ければ None(引けない)。"""
    if prob is None or (isinstance(prob, float) and not math.isfinite(prob)):
        return None
    return bool(float(prob) >= threshold)


def jev_state_for_q7_candidate(cand_row: dict, all_ts: np.ndarray, all_side: np.ndarray,
                               all_notional: np.ndarray, times: np.ndarray,
                               prices: np.ndarray) -> dict:
    """Q7 対照候補の state。`cont.jev_state_for_print` と同じ組み立てだが、
    `side`(REACT_SIGN)の代わりに候補の `dir_sign`(直前 10 秒の変位の符号)を使う。
    候補は `pc`(実プリントの表)に無いので print_id では引けない — 行を直接渡す。
    """
    ts = int(cand_row["ts_ms"])
    dir_sign = float(cand_row["dir_sign"])
    side_label = "BUY" if dir_sign > 0 else "SELL"
    lo = np.searchsorted(all_ts, ts - cont.SAME_SIDE_WINDOW_MS, side="left")
    hi = np.searchsorted(all_ts, ts, side="left")
    prints_last_60s = [
        {"t_rel_s": round((int(all_ts[j]) - ts) / 1000.0, 3),
         "notional_usd": round(float(all_notional[j]), 2),
         "side": str(all_side[j])}
        for j in range(lo, hi)]
    anchor_px, _t = cont.price_at_or_before(times, prices, ts - 1)
    path = []
    for sec in range(-60, 1):
        px, _t = cont.price_at_or_before(times, prices, ts + sec * 1000)
        if px == px and anchor_px == anchor_px and anchor_px > 0:
            path.append(round(dir_sign * (px - anchor_px) / anchor_px * 1e4, 4))
        else:
            path.append(None)
    materials = {}
    for n in cont.MAT_NUMS:
        v = cand_row.get(cont.MAT_COL[n])
        if n == 6:
            materials[cont.MAT_VAR[n]] = v if isinstance(v, str) and v else None
        else:
            materials[cont.MAT_VAR[n]] = (
                None if v is None or (isinstance(v, float) and not math.isfinite(v))
                else float(v))
    return {"side": side_label, "prints_last_60s": prints_last_60s,
            "price_path_bp_last_60s": path, "materials": materials}


# ===========================================================================
# 2. 選定(stage=select)
# ===========================================================================
def load_rows() -> pd.DataFrame:
    return pd.read_csv(ROWS_PATH, low_memory=False)


def build_manifest(df: pd.DataFrame) -> dict:
    prints = df[df["kind"] == "print"].reset_index(drop=True)
    bh = prints[prints["half"] == "後半"].reset_index(drop=True)
    fh_ids = set(prints.loc[prints["half"] == "前半", "print_id"].tolist())
    selected = select_5000(bh, SEED, N_SAMPLE)
    assert not (set(selected) & fh_ids), "前半のプリントが混入した"
    sel_set = set(selected)
    bh_sel = bh[bh["print_id"].isin(sel_set)].copy()
    cnt = pd.to_numeric(bh_sel["mat1_same_side_count_60s_and_elapsed"], errors="coerce")
    bh_sel["_group"] = cnt.map(count_group)
    strata_n = (bh_sel.groupby(["side", "_group"]).size()
                .rename("n").reset_index().to_dict("records"))

    q7 = df[df["kind"] == "q7_candidate"].reset_index(drop=True)
    q7_sel = q7[q7["q7_matched_print_id"].isin(sel_set)].copy()

    order = {pid: i for i, pid in enumerate(selected)}
    bh_sel["_order"] = bh_sel["print_id"].map(order)
    bh_sel = bh_sel.sort_values("_order")
    prints_manifest = [
        {"print_id": r["print_id"], "day": r["day"], "side": r["side"],
         "group": count_group(r["mat1_same_side_count_60s_and_elapsed"])}
        for _, r in bh_sel.iterrows()]
    q7_manifest = [
        {"candidate_id": r["print_id"], "matched_print_id": r["q7_matched_print_id"],
         "day": r["day"]}
        for _, r in q7_sel.iterrows()]
    return {
        "作成時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "種": SEED, "件数(目標)": N_SAMPLE,
        "後半プリント母数": int(bh.shape[0]),
        "選んだプリント数": len(prints_manifest),
        "層ごとの内訳": strata_n,
        "Q7対照候補が取れた件数": len(q7_manifest),
        "prints": prints_manifest,
        "q7_candidates": q7_manifest,
    }


# ===========================================================================
# 3. 呼び出し(stage=call)
# ===========================================================================
def _read_done_ids(path: Path, key: str) -> set:
    done = set()
    if not path.exists():
        return done
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if key in rec:
                done.add(rec[key])
    return done


class RateLimiter:
    def __init__(self, per_sec: float):
        self.min_dt = 1.0 / per_sec
        self.t_last = 0.0

    def wait(self):
        dt = time.time() - self.t_last
        if dt < self.min_dt:
            time.sleep(self.min_dt - dt)
        self.t_last = time.time()


def _call_one(client, state: dict) -> dict:
    """Jev を 1 回呼び、記録用の辞書を返す(確率はここに残る。呼び出し側が
    どこへ書くかを決める — このファイル内では data/jev/continue/*.jsonl だけに書く)。"""
    t0 = time.time()
    try:
        resp = client.evaluate(state, cont.JEV_QUESTIONS)
        latency = time.time() - t0
        usage = resp.get("usage") or {}
        ans = resp.get("answers", {}).get("continue", {})
        prob = ans.get("noul")
        return {"status": "ok", "prob": prob, "latency_s": round(latency, 4),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens")}
    except cont.JevError as e:
        latency = time.time() - t0
        return {"status": "error", "error": str(e), "prob": None,
                "latency_s": round(latency, 4)}


def run_call_stage(manifest: dict, progress_every: int = 100,
                   max_calls: int | None = None) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    done_prints = _read_done_ids(PRINTS_ANSWERS_PATH, "print_id")
    done_q7 = _read_done_ids(Q7_ANSWERS_PATH, "candidate_id")

    pc = cont.PrintsCSV(PRINTS_CSV_PATH)
    all_ts = pc.all_ts_sorted()
    o = np.argsort(pc.ts, kind="stable")
    all_side = pc.side[o]
    all_notional = pc.notional[o]

    df = load_rows()
    prints_by_id = {r["print_id"]: r for r in
                    df[df["kind"] == "print"].to_dict("records")}
    q7_by_id = {r["print_id"]: r for r in
                df[df["kind"] == "q7_candidate"].to_dict("records")}

    todo_prints = [m for m in manifest["prints"] if m["print_id"] not in done_prints]
    todo_q7 = [m for m in manifest["q7_candidates"]
              if m["candidate_id"] not in done_q7]

    client = cont.JevClient(model=MODEL, log_dir=str(STATE_DIR))
    limiter = RateLimiter(RATE_PER_SEC)
    trade_cache: dict = {}
    n_new = 0

    by_day: dict = defaultdict(list)
    for m in todo_prints:
        by_day[m["day"]].append(("print", m["print_id"]))
    for m in todo_q7:
        by_day[m["day"]].append(("q7", m["candidate_id"]))

    fh_prints = PRINTS_ANSWERS_PATH.open("a", encoding="utf-8")
    fh_q7 = Q7_ANSWERS_PATH.open("a", encoding="utf-8")
    try:
        for day in sorted(by_day.keys()):
            times, prices, _q, _miss, _need = cont.load_window5(
                DATA_ROOT, day, trade_cache, 400_000, 0)
            for kind, pid in by_day[day]:
                if max_calls is not None and n_new >= max_calls:
                    return {"打ち止め": "max_calls に到達", "新規呼び出し数": n_new}
                limiter.wait()
                if kind == "print":
                    row = prints_by_id[pid]
                    state = cont.jev_state_for_print(
                        pid, pc, all_ts, all_side, all_notional, times, prices, row)
                    r = _call_one(client, state)
                    rec = {"print_id": pid, "day": day, "side": row.get("side"), **r}
                    fh_prints.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh_prints.flush()
                else:
                    row = q7_by_id[pid]
                    state = jev_state_for_q7_candidate(
                        row, all_ts, all_side, all_notional, times, prices)
                    r = _call_one(client, state)
                    rec = {"candidate_id": pid,
                           "matched_print_id": row.get("q7_matched_print_id"),
                           "day": day, **r}
                    fh_q7.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh_q7.flush()
                n_new += 1
                if n_new % progress_every == 0:
                    print(f"[jev-call] 新規 {n_new} 件処理(直近: {kind} {pid} "
                          f"status={r['status']})", flush=True)
    finally:
        fh_prints.close()
        fh_q7.close()
    return {"新規呼び出し数": n_new}


# ===========================================================================
# 4. 表(stage=tables)
# ===========================================================================
def _load_answers(path: Path, id_key: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=[id_key, "status", "prob", "error",
                                     "latency_s", "input_tokens", "output_tokens"])
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    # 同じ件が再実行で複数回書かれていたら最後の行を使う(冪等な再開の結果)
    df = df.drop_duplicates(subset=[id_key], keep="last").reset_index(drop=True)
    for c in (id_key, "status", "prob", "error", "latency_s", "input_tokens",
             "output_tokens"):
        if c not in df.columns:
            df[c] = NAN
    return df


def build_tables(manifest: dict) -> dict:
    df = load_rows()
    prints_all = df[df["kind"] == "print"].reset_index(drop=True)
    base_fh_60 = float(prints_all.loc[prints_all["half"] == "前半", "label_60"].mean())
    cuts = cont.first_half_cuts(prints_all)
    prints_all = cont.add_bands(prints_all, cuts)
    rule_bands, rule_continue_set, top3 = cont.build_rules(prints_all, cuts, base_fh_60)

    sel_ids = [m["print_id"] for m in manifest["prints"]]
    bh = prints_all[prints_all["print_id"].isin(sel_ids)].copy()
    order = {pid: i for i, pid in enumerate(sel_ids)}
    bh["_order"] = bh["print_id"].map(order)
    bh = bh.sort_values("_order").reset_index(drop=True)

    ans_p = _load_answers(PRINTS_ANSWERS_PATH, "print_id")
    bh = bh.merge(ans_p[["print_id", "status", "prob", "error"]],
                  on="print_id", how="left")
    bh["prob"] = pd.to_numeric(bh["prob"], errors="coerce")
    bh["pred_0.5"] = bh["prob"].map(predict_continue)
    bh["pred_0.3"] = bh["prob"].map(lambda p: predict_continue(p, 0.3))
    bh["pred_0.7"] = bh["prob"].map(lambda p: predict_continue(p, 0.7))

    q3 = make_q3_jev(bh, base_fh_60)
    q3 += _q3_rule_agreement(bh, rule_bands, rule_continue_set, top3, base_fh_60)
    q3 += _q3_strata(bh)
    q4 = make_q4_jev(bh)
    q5 = make_q5_jev(bh)

    cand_ids = [m["candidate_id"] for m in manifest["q7_candidates"]]
    q7df = df[(df["kind"] == "q7_candidate") & (df["print_id"].isin(cand_ids))].copy()
    ans_q7 = _load_answers(Q7_ANSWERS_PATH, "candidate_id")
    q7df = q7df.merge(
        ans_q7[["candidate_id", "status", "prob", "error"]].rename(
            columns={"candidate_id": "print_id"}), on="print_id", how="left")
    q7df["prob"] = pd.to_numeric(q7df["prob"], errors="coerce")
    q7df["pred_0.5"] = q7df["prob"].map(predict_continue)
    bh_matched = bh[bh["print_id"].isin(
        q7df["q7_matched_print_id"].dropna().tolist())].copy()
    q7 = make_q7_jev(q7df, bh_matched)

    call_summary = summarize_calls(ans_p, ans_q7)

    return {"q3": q3, "q4": q4, "q5": q5, "q7": q7, "bh": bh, "q7df": q7df,
            "call_summary": call_summary, "top3": top3, "base_fh_60": base_fh_60}


def make_q3_jev(bh: pd.DataFrame, base_fh_60: float) -> list:
    rows = []
    has_prob = bh["prob"].notna()
    for h in cont.LABEL_SECONDS:
        y = bh[f"label_{h}"].astype(float)
        pred = bh["pred_0.5"]
        has = pred.notna() & y.notna()
        p = pred[has].astype(bool)
        yy = y[has]
        n_tot = int(has.sum())
        tp = int(((p) & (yy == 1)).sum())
        fp = int(((p) & (yy == 0)).sum())
        fn = int(((~p) & (yy == 1)).sum())
        tn = int(((~p) & (yy == 0)).sum())
        acc = (tp + tn) / n_tot if n_tot else NAN
        prec = tp / (tp + fp) if (tp + fp) else NAN
        rec = tp / (tp + fn) if (tp + fn) else NAN
        rows.append({"区分": "的中率・適合率・再現率", "h(秒)": h, "n": n_tot,
                    "基準率(この5000件)": float(y.mean()) if y.notna().any() else NAN,
                    "的中率": acc, "適合率": prec, "再現率": rec,
                    "「続く」と言った件数": int(p.sum())})
    # 較正: 確率の10帯ごとの件数と実際の続く割合(label_60)
    b = np.floor(bh["prob"].to_numpy(float) * 10).clip(0, 9)
    for k in range(10):
        mask = has_prob & (b == k)
        v = bh.loc[mask, "label_60"].astype(float)
        rows.append({"区分": "確率帯ごとの実際の続く割合(較正)",
                    "確率帯": f"[{k/10:.1f},{(k+1)/10:.1f})", "n": int(mask.sum()),
                    "実際の続く割合": float(v.mean()) if v.size else NAN})
    return rows


def _q3_rule_agreement(bh: pd.DataFrame, rule_bands: dict, rule_continue_set: dict,
                       top3: list, base_fh_60: float) -> list:
    rows = []
    rule_pred = {
        "rule_1": cont.apply_rule(bh, 1, rule_continue_set),
        "rule_14": cont.apply_rule(bh, 14, rule_continue_set),
        "rule_combo": cont.apply_combo(bh, top3, rule_bands, base_fh_60),
    }
    jev_pred = bh["pred_0.5"]
    for name, pred in rule_pred.items():
        both = jev_pred.notna() & pred.notna()
        agree = (jev_pred[both].astype(bool) == pred[both].astype(bool))
        rows.append({"区分": "規則との一致率", "規則": name, "n": int(both.sum()),
                    "一致率": float(agree.mean()) if both.any() else NAN})
    return rows


def _q3_strata(bh: pd.DataFrame) -> list:
    rows = []
    cnt = pd.to_numeric(bh["mat1_same_side_count_60s_and_elapsed"], errors="coerce")
    grp = cnt.map(count_group)
    for (side, g), sub in bh.groupby([bh["side"], grp]):
        rows.append({"区分": "層ごとの n", "側": side, "材料1の群": g,
                    "n": int(sub.shape[0]),
                    "呼べた件数(prob あり)": int(sub["prob"].notna().sum())})
    return rows


def make_q4_jev(bh: pd.DataFrame) -> list:
    rows = []
    s = bh["dir_sign"].astype(float)
    grids = [(e, h) for e in cont.ENTRY_DELAYS_S for h in cont.HOLD_SECONDS]
    for (e, h) in grids:
        is_main = (e == cont.MAIN_ENTRY and h == cont.MAIN_HOLD)
        entry = bh[f"p_entry_{e}"]
        exitp = bh[f"p_exit_e{e}_h{h}"]
        pred = bh["pred_0.5"]
        for branch_label, branch_bool in (("続く", True), ("止まる", False)):
            mask = (pred == branch_bool)
            dirn = np.where(branch_bool, s, -s)
            pnl = dirn * (exitp - entry) / entry * 1e4
            pnl = pd.Series(pnl, index=bh.index).where(mask, NAN)
            st = cont.branch_stats(pnl.to_numpy(float), bh["day"].to_numpy(object))
            rows.append({"格子": ("主(t0+1s→60s)" if is_main else "副"),
                        "entry_s": e, "hold_s": h, "判断": "jev_0.5",
                        "閾値": 0.5, "枝": branch_label, **st})
    # 主格子だけ、閾値 0.3 / 0.7
    entry = bh["p_entry_1"]
    exitp = bh["p_exit_e1_h60"]
    for thr in (0.3, 0.7):
        pred = bh[f"pred_{thr}"]
        for branch_label, branch_bool in (("続く", True), ("止まる", False)):
            mask = (pred == branch_bool)
            dirn = np.where(branch_bool, s, -s)
            pnl = dirn * (exitp - entry) / entry * 1e4
            pnl = pd.Series(pnl, index=bh.index).where(mask, NAN)
            st = cont.branch_stats(pnl.to_numpy(float), bh["day"].to_numpy(object))
            rows.append({"格子": "主(t0+1s→60s)", "entry_s": 1, "hold_s": 60,
                        "判断": f"jev_{thr}", "閾値": thr, "枝": branch_label, **st})
    return rows


def make_q5_jev(bh: pd.DataFrame) -> list:
    entry = bh["p_entry_1"]
    exitp = bh["p_exit_e1_h60"]
    s = bh["dir_sign"].astype(float)
    pred = bh["pred_0.5"]
    dirn = pred.map(lambda x: (1.0 if x else -1.0) if x is not None else NAN)
    pnl = dirn.astype(float) * s * (exitp - entry) / entry * 1e4
    v = pnl.to_numpy(float)
    d = bh["day"].to_numpy(object)
    fin = np.isfinite(v)
    vv, dd = v[fin], d[fin]
    if vv.size == 0:
        return [{"判断": "jev_0.5", "日数": 0, "負の日の割合": NAN,
                "上位5日の寄与の和÷全体": NAN, "合計bp": NAN}]
    daily = pd.Series(vv).groupby(dd).sum()
    total = float(daily.sum())
    top5 = float(daily.sort_values(ascending=False).head(5).sum())
    return [{"判断": "jev_0.5", "日数": int(daily.size),
            "負の日の割合": float((daily < 0).mean()),
            "上位5日の寄与の和÷全体": (top5 / total) if total != 0 else NAN,
            "合計bp": total}]


def make_q7_jev(q7df: pd.DataFrame, bh_matched: pd.DataFrame) -> list:
    rows = []
    s = q7df["dir_sign"].astype(float)
    entry = q7df["p_entry_1"]
    exitp = q7df["p_exit_e1_h60"]
    pred = q7df["pred_0.5"]
    said = float((pred == True).sum()) / max(int(pred.notna().sum()), 1)  # noqa: E712
    for branch_label, branch_bool in (("続く", True), ("止まる", False)):
        mask = (pred == branch_bool)
        dirn = np.where(branch_bool, s, -s)
        pnl = dirn * (exitp - entry) / entry * 1e4
        pnl = pd.Series(pnl, index=q7df.index).where(mask, NAN)
        st = cont.branch_stats(pnl.to_numpy(float), q7df["day"].to_numpy(object))
        rows.append({"側": "候補(清算の無い時刻)", "枝": branch_label,
                    "続くと言った割合": said, **st})

    s2 = bh_matched["dir_sign"].astype(float)
    entry2 = bh_matched["p_entry_1"]
    exitp2 = bh_matched["p_exit_e1_h60"]
    pred2 = bh_matched["pred_0.5"]
    said2 = (float((pred2 == True).sum()) / max(int(pred2.notna().sum()), 1)  # noqa: E712
            if pred2.size else NAN)
    for branch_label, branch_bool in (("続く", True), ("止まる", False)):
        mask = (pred2 == branch_bool)
        dirn = np.where(branch_bool, s2, -s2)
        pnl = dirn * (exitp2 - entry2) / entry2 * 1e4
        pnl = pd.Series(pnl, index=bh_matched.index).where(mask, NAN)
        st = cont.branch_stats(pnl.to_numpy(float), bh_matched["day"].to_numpy(object))
        rows.append({"側": "プリント(同じ件、対照候補が取れたものだけ)",
                    "枝": branch_label, "続くと言った割合": said2, **st})
    return rows


def summarize_calls(ans_p: pd.DataFrame, ans_q7: pd.DataFrame) -> dict:
    def _q(df, col):
        v = pd.to_numeric(df[col], errors="coerce").to_numpy(float)
        v = v[np.isfinite(v)]
        return {str(q): (float(np.percentile(v, q)) if v.size else None)
                for q in (10, 25, 50, 75, 90, 100)}

    out = {}
    for name, df in (("prints", ans_p), ("q7_candidates", ans_q7)):
        n = int(df.shape[0])
        n_ok = int((df.get("status") == "ok").sum()) if n else 0
        n_err = int((df.get("status") == "error").sum()) if n else 0
        err_kinds: dict = defaultdict(int)
        if n_err and "error" in df.columns:
            for e in df.loc[df["status"] == "error", "error"].dropna():
                err_kinds[str(e)[:40]] += 1
        out[name] = {
            "呼び出し試行数": n, "成功": n_ok, "エラー": n_err,
            "エラーの種類": dict(err_kinds),
            "遅延の分位(秒)": _q(df, "latency_s") if n else {},
            "入力トークンの分位": _q(df, "input_tokens") if n else {},
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O3C SIGNAL 続く/止まる — 後半 Jev(5,000 件 + Q7)")
    ap.add_argument("--stage", choices=("select", "call", "tables", "all"), default="all")
    ap.add_argument("--progress-every", type=int, default=100)
    ap.add_argument("--max-calls", type=int, default=None,
                    help="この 1 回の呼び出しで新規に叩く上限(デバッグ用)")
    a = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if a.stage in ("select", "all") or not MANIFEST_PATH.exists():
        df = load_rows()
        manifest = build_manifest(df)
        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"選定 完了: プリント {len(manifest['prints'])} 件、"
              f"Q7 対照候補 {len(manifest['q7_candidates'])} 件", flush=True)
    else:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    if a.stage == "select":
        return 0

    if a.stage in ("call", "all"):
        note = run_call_stage(manifest, a.progress_every, a.max_calls)
        print(f"[jev-call] {note}", flush=True)
    if a.stage == "call":
        return 0

    built = build_tables(manifest)
    write_output(manifest, built)
    return 0


def write_output(manifest: dict, built: dict) -> None:
    q3, q4, q5, q7 = built["q3"], built["q4"], built["q5"], built["q7"]
    named = [("q3_jev.csv", q3, "Q3"), ("q4_jev.csv", q4, "Q4"),
             ("q5_jev.csv", q5, "Q5"), ("q7_jev.csv", q7, "Q7")]
    norm = {name: cont.normalize_rows(rows) for name, rows, _k in named}
    for name, rows, _k in named:
        cont.write_csv(OUT_DIR / name, norm[name])

    md = ["# O3C SIGNAL 続く/止まるの単位 — 後半 Jev(5,000 件 + Q7 対照)",
          "",
          "- 委任文: `docs/DATA/delegations/20260920_o3c_signal_continue_jev_prompt.md`",
          "- 設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md`(§2 Q3/Q4/Q7)",
          f"- 選んだプリント数: {len(manifest['prints'])} / "
          f"Q7 対照候補が取れた件数: {len(manifest['q7_candidates'])}",
          "- 判断の閾値: Jev は確率 >= 0.5 を「続く」とする(Q4 は 0.3 / 0.7 も併記)",
          ""]
    for name, rows, key in named:
        md += [f"## {key}(`{name}`、{len(norm[name])} 行)", "", cont.md_table(norm[name]), ""]
    mdtxt = "\n".join(md)
    cont.check_no_banned(mdtxt, "tables_jev.md")
    (OUT_DIR / "tables_jev.md").write_text(mdtxt, encoding="utf-8")

    summary = {
        "実行時刻(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_CONTINUE_DESIGN_2026-09-20.md",
        "種": SEED, "件数(目標)": N_SAMPLE,
        "選んだプリント数": len(manifest["prints"]),
        "層ごとの内訳": manifest["層ごとの内訳"],
        "Q7対照候補が取れた件数": len(manifest["q7_candidates"]),
        "呼び出しの集計": built["call_summary"],
        "上位3材料(組の規則、既存の Q2/Q4 と同じ top3)": built["top3"],
        "基準率(前半、60秒、既存と同じ計算)": built["base_fh_60"],
        "表の行数": {name: len(rows) for name, rows, _k in named},
    }
    txt = json.dumps(summary, ensure_ascii=False, indent=2)
    cont.check_no_banned(txt, "summary_jev.json")
    (OUT_DIR / "summary_jev.json").write_text(txt, encoding="utf-8")

    lines = []
    for p in sorted(OUT_DIR.iterdir()):
        if p.name in ("MD5SUMS", "selection_manifest.json") or p.is_dir():
            continue
        if p.suffix in (".csv", ".md", ".json"):
            cont.check_no_banned(p.read_text(encoding="utf-8"), p.name)
        lines.append(f"{cont.md5_of(p)}  {p.name}")
    (OUT_DIR / "MD5SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
