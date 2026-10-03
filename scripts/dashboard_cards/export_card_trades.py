"""ダッシュボード表示用: カードの測定を走らせ直し、取引の列(矢印用)・日ごとの損益・出所を書き出す。

    PYTHONPATH=src python3 scripts/dashboard_cards/export_card_trades.py --card c4 --variant core_body
        [--work <作業置き場>] [--out-root backtest_runs_shared/cards] [--skip-run] [--keep-npz]

研究の台本(scripts/w4_measure/)は変えず、子プロセスとして呼ぶ(c4〜c8 = run_b2.py --out-root、c1〜c3 = run_v2.py --no-measure)。
封印の門(bot.bt.data)を通して読むのは研究の台本。この台本自身は backtest_data の年別ファイルの sha256 を取るだけで、
phase2_sealed は読まない。期間 [始め, 終わり) の終わりが封印の境 2023-12-18T00:00:00Z より後なら拒否する(common.check_end: 終わり > 境。終わり = 境ちょうどは通る = 境の前までの区間)。docs/RESEARCH/ には書かない。

取引の定義(= scripts/w4_measure/light_b2.py の extra_stats と同じ関数をそのまま import して使う。extra.json の trades の数え方):
  P_t = bot.research.cards.pnl.pnl(e_t × (open_{t+2}/open_{t+1} − 1) × 1e4、t+1・t+2 は次の空でない足。最後の 2 決定は P なし)。
  取引 = P のある決定を順に並べ、sign(e) が同じで 0 でない決定がつながった最長の区間(足し増し・一部決済は同じ取引のまま、
  +1 から −1 へ直接変われば 2 つの取引)。損益 = 区間の P_t の合計。
  建てた時刻・値段 = 区間の最初の決定の約定の足(fill_bar)の始まり・始値。決済の時刻・値段 = 区間の最後の決定の決済の足
  (exit_bar = 次の決定の約定の足)の始まり・始値。qty = 区間の決定の |e| の平均。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
from types import SimpleNamespace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
W4 = os.path.join(ROOT, "scripts", "w4_measure")
sys.path.insert(0, W4)
sys.path.insert(0, os.path.join(ROOT, "src"))

from common import BIN_DIR, FX_DIR, SEAL, USDJPY_PATH, check_end, iso, to_iso, years  # noqa: E402
from daily_stats import daily_stats  # noqa: E402
from light_b2 import extra_stats  # noqa: E402
from run_b2 import CARDS  # noqa: E402
from run_v2 import C2_VARIANTS  # noqa: E402

from bot.research.cards.measure import daily_rows, write_daily  # noqa: E402
from bot.research.cards.pnl import pnl  # noqa: E402

C13 = {"c1": ("c1_xborder_mom", ("2017-08-17T15:00:00Z", "2023-12-17T15:00:00Z")),
       "c3": ("c3_yen_premium_revert", ("2017-08-17T15:00:00Z", "2022-12-31T15:00:00Z"))}


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for ch in iter(lambda: fh.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def git(*a):
    return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True).stdout.strip()


def spec(card, variant):
    """(card_id, 期間, 実行コマンド(引数), npz の置き場の関数, 読むデータの置き場の組)。"""
    if card == "c1":
        cid, per = C13[card]
        return cid, per, ["run_v2.py", "--card", "c1", "--no-measure"], "default", [(FX_DIR, "candles_1m_{y}.csv.gz"), (BIN_DIR, "binance_BTCUSDT_1m_{y}.csv.gz")]
    if card == "c2":
        s, foot = variant.split("_")
        foot = int(foot.rstrip("m"))
        attr, ref_dir, ref_file, per, _d = C2_VARIANTS[s]
        return ("c2_owner_xvenue_wick", per, ["run_v2.py", "--card", "c2", "--variant", s, "--foot", str(foot), "--no-measure"],
                variant, [(FX_DIR, "candles_1m_{y}.csv.gz"), (ref_dir, ref_file)])
    if card == "c3":
        cid, per = C13[card]
        return cid, per, ["run_v2.py", "--card", "c3", "--window", variant, "--no-measure"], variant, [
            (FX_DIR, "candles_1m_{y}.csv.gz"), (BIN_DIR, "binance_BTCUSDT_1m_{y}.csv.gz"), (os.path.dirname(USDJPY_PATH), "usdjpy_1m.csv.gz")]
    cid, variants, per = CARDS[card]
    if variant not in variants:
        raise SystemExit(f"変種 {variant} は {variants} に無い")
    data = [(FX_DIR, "candles_1m_{y}.csv.gz")]
    if card == "c6":
        data.append((os.path.dirname(USDJPY_PATH), "usdjpy_1m.csv.gz"))
    return cid, per, ["run_b2.py", "--card", card, "--variant", variant], variant, data


def gz_json(obj, path):
    raw = json.dumps(obj, separators=(",", ":")).encode()
    with open(path, "wb") as fh:
        with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, compresslevel=9) as g:
            g.write(raw)


def compact(a, nd):
    a = np.round(np.asarray(a, dtype=float), nd)
    return [int(x) if x == int(x) else float(x) for x in a.tolist()]


def main_limit(a, side):
    """c4 の limit_sim/v37_full(good|bad)。scripts/w4_measure/c4_limit_run.py を既定の引数で走らせ直し、trades.csv.gz を trades.json.gz に変える。"""
    import csv
    from datetime import datetime, timezone
    cid = "c4_owner_matilda_range"
    vname = f"limit_v37_{side}"
    per = ("2015-11-28T15:00:00Z", "2023-12-17T15:00:00Z")
    lo, hi = iso(per[0]), iso(per[1])
    check_end(hi)
    work = os.path.join(a.work, cid, vname)
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
    t0 = time.time()
    cmd = [sys.executable, os.path.join(W4, "c4_limit_run.py"), "--fill-side", side, "--out", work]
    if not a.skip_run:
        try:
            r = subprocess.run(cmd, env=env, cwd=ROOT, timeout=a.timeout)
        except subprocess.TimeoutExpired:
            raise SystemExit(f"時間切れ({a.timeout}s)で止めた")
        if r.returncode:
            raise SystemExit(f"研究の台本が失敗 rc={r.returncode}")
    t_run = time.time() - t0

    def ns(t):
        return int(datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()) * 10**9
    cols = {k: [] for k in ("entry_t_ns", "entry_px", "exit_t_ns", "exit_px", "side", "qty", "pnl_bp")}
    sides = set()
    with gzip.open(os.path.join(work, "trades.csv.gz"), "rt", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sd = row["side"]
            sides.add(sd)
            cols["entry_t_ns"].append(ns(row["entry_t"]))
            cols["exit_t_ns"].append(ns(row["exit_t"]))
            cols["entry_px"].append(float(row["entry_price"]))
            cols["exit_px"].append(float(row["exit_price"]))
            cols["side"].append(1 if sd in ("1", "buy", "long", "BUY") else -1)
            cols["qty"].append(float(row["levels"]))
            cols["pnl_bp"].append(float(row["pnl_bp"]))
    trades = {"version": 1, "t_unit": "ns", **{k: (compact(v, 4) if k in ("entry_px", "exit_px", "qty", "pnl_bp") else v) for k, v in cols.items()}}
    out = os.path.join(a.out_root, cid, vname)
    os.makedirs(out, exist_ok=True)
    gz_json(trades, os.path.join(out, "trades.json.gz"))
    day = {}
    for t, pb in zip(cols["exit_t_ns"], cols["pnl_bp"]):
        d = datetime.fromtimestamp(t / 1e9 + 9 * 3600, tz=timezone.utc).strftime("%Y-%m-%d")
        v = day.setdefault(d, [0.0, 0])
        v[0] += pb
        v[1] += 1
    write_daily([(d, v[0], v[1]) for d, v in sorted(day.items())], os.path.join(out, "daily.csv"))
    gdir = os.path.join(ROOT, "docs/RESEARCH/cards", cid, "limit_sim/v37_full")
    checks, ok = {}, True

    def cmp(name, mine, theirs):
        nonlocal ok
        same = mine == theirs
        ok &= same
        checks[name] = {"same": same, "rerun": mine if not isinstance(mine, (dict, list)) else "(構造)", "git": theirs if not isinstance(theirs, (dict, list)) else "(構造)"}
    mine_s = json.load(open(os.path.join(work, "summary.json")))
    git_s = json.load(open(os.path.join(gdir, f"summary_{side}.json")))
    cmp("summary.json(全体)", mine_s, git_s)
    mine_r = json.load(open(os.path.join(work, "run_record.json")))
    git_r = json.load(open(os.path.join(gdir, f"run_record_{side}.json")))
    for k in ("params", "period", "trades", "undecided_bars_total"):
        cmp(f"run_record.{k}", mine_r[k], git_r[k])
    cmp("run_record.chunks", mine_r["chunks"], git_r["chunks"])
    cmp("run_record.inputs", mine_r["inputs"], git_r["inputs"])
    cmp("n_trades_exported", len(trades["side"]), git_r["trades"])
    cmp("sum_pnl_bp_vs_summary_all_sum_bp(小数 3 桁)", round(sum(cols["pnl_bp"]), 3), round(git_s["all"]["sum_bp"], 3))
    inputs = []
    for y in years(lo, hi):
        f = os.path.join(FX_DIR, f"candles_1m_{y}.csv.gz")
        inputs.append({"path": f, "sha256": sha_file(os.path.join(ROOT, f))})
    rr = f"docs/RESEARCH/cards/{cid}/limit_sim/v37_full/run_record_{side}.json"
    prov = {"card": cid, "variant": vname, "period": per, "display_ok": bool(ok),
            "display_ok_rule": "summary.json 全体・run_record の params/period/trades/undecided/chunks/inputs が git の記録と完全一致(取引の行は git に無いので行ごとの照合はしていない)",
            "checks": checks, "verified_items": [k for k, v in checks.items() if v["same"]],
            "not_verified": ["取引の行そのものは git に無く照合していない。日ごとの損益は走らせ直した取引から作った(git に daily.csv 無し)"],
            "n_trades": len(trades["side"]), "side_values_seen": sorted(sides), "qty_meaning": "約定した段の数(levels)",
            "source_record": {"path": rr, "sha256": sha_file(os.path.join(ROOT, rr))},
            "script": {"export": "scripts/dashboard_cards/export_card_trades.py", "export_sha256": sha_file(os.path.abspath(__file__)),
                       "research_cmd": [f"PYTHONPATH=src python3 scripts/w4_measure/c4_limit_run.py --fill-side {side} --out <作業置き場>"],
                       "research_script_sha256": sha_file(os.path.join(W4, "c4_limit_run.py"))},
            "git_sha": git("rev-parse", "HEAD"), "data_dirs_read": [FX_DIR], "inputs_sha256": inputs,
            "trade_definition": "指値の模型 bot.research.matilda_limit_sim.MatildaLimitSim が返す取引の行(trades.csv.gz)。entry_t/exit_t = 足の終わりの時刻(UTC、秒)、価格 = 約定の値段、pnl_bp = その取引の損益。成行の測定(exposure の符号の区間)とは別の定義",
            "seal": "期間の終わり %s は封印の境より前。phase2_sealed は読んでいない" % per[1],
            "seconds": {"research_run": round(t_run, 1), "total": round(time.time() - t0, 1)}}
    json.dump(prov, open(os.path.join(out, "provenance.json"), "w"), ensure_ascii=False, indent=1)
    if not a.keep_npz:
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    sz = {f: os.path.getsize(os.path.join(out, f)) for f in os.listdir(out)}
    print(json.dumps({"card": cid, "variant": vname, "display_ok": ok, "n_trades": len(trades["side"]),
                      "checks": {k: v["same"] for k, v in checks.items()}, "bytes": sz}, ensure_ascii=False))
    return 0 if ok else 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True, choices=["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"])
    ap.add_argument("--variant", default="default")
    ap.add_argument("--work", default="/tmp/claude-0/-home-user-trade/e6a4380b-afed-57da-9bf3-2f6f5951f5cf/scratchpad/cards_work")
    ap.add_argument("--out-root", default=os.path.join(ROOT, "backtest_runs_shared", "cards"))
    ap.add_argument("--skip-run", action="store_true")
    ap.add_argument("--keep-npz", action="store_true")
    ap.add_argument("--timeout", type=int, default=5400, help="研究の台本の上限(秒)。超えたら子プロセスを止めて失敗にする")
    a = ap.parse_args()
    if a.card == "c4" and a.variant.startswith("limit_v37_"):
        return main_limit(a, a.variant.rsplit("_", 1)[1])
    cid, per, cmd, vname, data = spec(a.card, a.variant)
    lo, hi = iso(per[0]), iso(per[1])
    check_end(hi)
    assert hi <= int(SEAL.timestamp()) * 10**9
    work = os.path.join(a.work, cid, vname)
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
    t0 = time.time()
    if a.card in ("c1", "c2", "c3"):
        npz = os.path.join(work, f"{vname}_year_{per[0][:10]}_{per[1][:10]}.npz")
        full = [sys.executable, os.path.join(W4, cmd[0])] + cmd[1:] + ["--save-root", work]
    else:
        npz = os.path.join(work, vname, "run.npz")
        full = [sys.executable, os.path.join(W4, cmd[0])] + cmd[1:] + ["--out-root", work]
    if not a.skip_run:
        try:
            r = subprocess.run(full, env=env, cwd=ROOT, timeout=a.timeout)
        except subprocess.TimeoutExpired:
            raise SystemExit(f"時間切れ({a.timeout}s)で止めた")
        if r.returncode:
            raise SystemExit(f"研究の台本が失敗 rc={r.returncode}")
    t_run = time.time() - t0
    z = np.load(npz)
    run = SimpleNamespace(open=z["open"], exposure=z["exposure"], decided=z["decided"], end_ns=z["end_ns"],
                          start_ns=z["start_ns"], volume=z["volume"])
    p = pnl(run)
    e_all = run.exposure[run.decided]
    ds = daily_stats(p.t_ns, p.pnl_bp, e_all)
    rows = daily_rows(p, "Asia/Tokyo")
    out = os.path.join(a.out_root, cid, vname)
    os.makedirs(out, exist_ok=True)
    sha_daily = write_daily(rows, os.path.join(out, "daily.csv"))
    ex, tr = extra_stats(p, e_all, ds["overall"]["n_days"])
    st, tn = tr["trade_start"], tr["trade_n"]
    last = st + tn - 1
    s = np.sign(p.exposure)
    absum = np.concatenate([[0.0], np.cumsum(np.abs(p.exposure))])
    qty = (absum[last + 1] - absum[st]) / tn
    trades = {"version": 1, "t_unit": "ns",
              "entry_t_ns": run.start_ns[p.fill_bar[st]].astype(np.int64).tolist(), "entry_px": compact(run.open[p.fill_bar[st]], 4),
              "exit_t_ns": run.start_ns[p.exit_bar[last]].astype(np.int64).tolist(), "exit_px": compact(run.open[p.exit_bar[last]], 4),
              "side": tr["trade_side"].astype(int).tolist(), "qty": compact(qty, 4), "pnl_bp": compact(tr["trade_pnl"], 4)}
    gz_json(trades, os.path.join(out, "trades.json.gz"))
    # ---- 再現の確かめ(git の記録との比較。直さない) ----
    cdir = os.path.join(ROOT, "docs/RESEARCH/cards", cid, "measure", vname)
    checks, ok = {}, True

    def cmp(name, mine, theirs):
        nonlocal ok
        same = mine == theirs
        ok &= same
        checks[name] = {"same": same, "rerun": mine, "git": theirs}
    cmp("daily_csv_sha256", sha_daily, sha_file(os.path.join(cdir, "daily.csv")))
    gds = json.load(open(os.path.join(cdir, "daily_stats.json")))
    cmp("daily_stats.overall", ds["overall"], gds["overall"])
    cmp("daily_stats.frequency", ds["frequency"], gds["frequency"])
    rr = None
    if os.path.exists(os.path.join(cdir, "extra.json")):
        gex = json.load(open(os.path.join(cdir, "extra.json")))
        cmp("extra.trades", ex["trades"], gex["trades"])
        cmp("extra.drawdown", ex["drawdown"], gex["drawdown"])
        rr = "docs/RESEARCH/cards/%s/measure/%s/run_record.json" % (cid, vname)
        grec = json.load(open(os.path.join(ROOT, rr)))
        frec = os.path.join(work, vname, "run_record.json")
        if os.path.exists(frec):
            cmp("run_record.headline", json.load(open(frec))["headline"], grec["headline"])
        else:
            ok = False
            checks["run_record.headline"] = {"same": False, "reason": "走らせ直しの run_record.json が無く headline を照合できない(表示しない)"}
        cmp("n_trades_exported", len(trades["side"]), gex["trades"]["n"])
    else:
        checks["trades_n"] = {"same": None, "note": "git に取引の数の記録が無い(c1〜c3)。日ごとの損益と頻度だけを照合"}
        rr = "docs/RESEARCH/cards/%s/measure/%s/%s" % (cid, vname, "measure.json" if os.path.exists(os.path.join(cdir, "measure.json")) else "daily_stats.json")
    cum = float(np.sum(tr["trade_pnl"]))
    checks["sum_trade_pnl_vs_final_cum_bp"] = {"trades_sum": cum, "final_cum_bp": ex["drawdown"]["final_cum_bp"]}
    inputs = []
    for d, pat in data:
        for y in years(lo, hi):
            f = os.path.join(d, pat.format(y=y))
            if os.path.exists(os.path.join(ROOT, f)):
                inputs.append({"path": f, "sha256": sha_file(os.path.join(ROOT, f))})
    prov = {"card": cid, "variant": vname, "period": per, "display_ok": bool(ok),
            "display_ok_rule": "daily.csv の sha256・daily_stats の overall と frequency(・c4〜c8 は extra.json の trades と drawdown・run_record の headline)が git の記録と完全一致",
            "checks": checks, "n_trades": len(trades["side"]),
            "source_record": {"path": rr, "sha256": sha_file(os.path.join(ROOT, rr))},
            "script": {"export": "scripts/dashboard_cards/export_card_trades.py", "export_sha256": sha_file(os.path.abspath(__file__)),
                       "research_cmd": ["PYTHONPATH=src python3 scripts/w4_measure/" + " ".join(cmd)] + (["(--out-root / --save-root は作業置き場)"]),
                       "research_script_sha256": sha_file(os.path.join(W4, cmd[0]))},
            "git_sha": git("rev-parse", "HEAD"), "git_dirty_w4_measure": bool(git("status", "--porcelain", "scripts/w4_measure", "docs/RESEARCH")),
            "data_dirs_read": [d for d, _ in data], "inputs_sha256": inputs,
            "trade_definition": __doc__.split("取引の定義")[1].split('"""')[0],
            "seal": "期間の終わり %s は封印の境 2023-12-18T00:00:00Z より前。phase2_sealed は読んでいない" % per[1],
            "seconds": {"research_run": round(t_run, 1), "total": round(time.time() - t0, 1)}}
    json.dump(prov, open(os.path.join(out, "provenance.json"), "w"), ensure_ascii=False, indent=1)
    prov["verified_items"] = [k for k, v in checks.items() if v.get("same") is True]
    prov["not_verified"] = (["取引数は git に記録が無く照合していない(日ごとの損益・overall・frequency の一致で表示可とした)"]
                            if "trades_n" in checks else [])
    json.dump(prov, open(os.path.join(out, "provenance.json"), "w"), ensure_ascii=False, indent=1)
    if not a.keep_npz:  # 書き出しと照合が済んだので作業置き場の変種の分を消す
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    sz = {f: os.path.getsize(os.path.join(out, f)) for f in os.listdir(out)}
    print(json.dumps({"card": cid, "variant": vname, "display_ok": ok, "n_trades": len(trades["side"]),
                      "checks": {k: v["same"] for k, v in checks.items() if "same" in v}, "bytes": sz}, ensure_ascii=False))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
