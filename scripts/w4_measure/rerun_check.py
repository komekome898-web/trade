"""走らせ直し(2026-10-06、カード 1・2・3・6)の確かめ。新しい走らせはしない(置き場のファイルを読むだけ)。

    PYTHONPATH=src python3 scripts/w4_measure/rerun_check.py --dir <走らせ直しの置き場> --orig <元の measure/<変種>>

確かめること(結果は <置き場>/rerun_check.json と標準出力):
  (1) 元の走らせの再現: 走らせ直しの daily.csv と元の daily.csv(どちらも測定器の write_daily の形 day,pnl_bp,n)。
      sha256 が同じなら「全部同じ」。違えば、両方にある日のうち、短い方の最後の日より前の日を行の文字列で突き合わせる
      (最後の日は外して別に書く: 走らせの最後の 2 決定は P が無く、期間の終わりで日本時間の日が途中で切れるため)。
      元に無く走らせ直しにだけある日(期間を延ばした分)は数だけ書く。
  (2) 足した列の意味: 量 > 0 の足で high >= max(open, close) かつ low <= min(open, close)。決定 = 量 > 0 の足。
      カード 2(signal_color があるとき): signal_color と signal_log の行の数が同じ、色は ±1、
      signal_strong = (色 == 合図の向き)。強い・弱い × 買い・売りの数。
  (3) 置き場の中の食い違い: npz から P を計算し直した日ごとの和(測定器の pnl・daily_rows)が、同じ置き場の daily.csv と同じか。
  (4) 取引の行(git に入れる小さな出力): 既にある読み口 `scripts/analysis/card_trades.py` の build・write_trades を import して
      (写さない)、<置き場>/run.npz から <置き場>/trades.csv.gz(signal_t・entry_t・exit_t・side・pnl_bp)を書く。
      確かめ: card_trades が決定の日ごとに計算し直した和(daily_calc)が daily.csv と同じ(相対 1e-9)/ 取引の損益の和が
      daily.csv の和と同じ(trades.csv.gz は小数 6 桁で書くので、許す差 = 取引の数 × 5e-7 + 1e-9 × |和|)。
      取引を合図の時刻(signal_t)の日本時間の日に寄せた和と daily.csv の日ごとの比べは数だけ書く(判定に入れない):
      日本時間の 0 時をまたいで持った取引の損益は、daily.csv では決定の日ごとに分かれるので、その日は合わないのが正しい。
  (5) カード 2(signal_color があるとき): <置き場>/signals.csv.gz(signal_t = 足の終わり・side・signal_color・signal_strong、
      signal_log の並び)を書き、行の数が signal_log と同じか。
  (6) カード 3(持ち高が連続の値): run.npz を消す前に、持ち高を 1 本遅らせた損益の日ごとの和 <置き場>/daily_lag1.csv と、
      決定の足の持ち高 <置き場>/positions.npz(t_end_min int32・e float32)を書く(lag1_pnl の説明)。
  --require-identical(カード 1・2・3 の 22 本): (1) は daily.csv の sha256 が元と同じときだけ通す(日の数・最後の日を含む)。
      付けないとき(カード 6 の延長 2 本)は、短い方の最後の日より前の突き合わせで通す。
終わりの値: (1)〜(6) が全部通れば 0、どれかが通らなければ 3(3 のときは run.npz を消さずに残す。一覧の約束)。
高値・安値は npz にだけ残し、小さな出力には入れない(リードの決め 2026-10-06)。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import numpy as np

from bot.research.cards.measure import daily_rows, write_daily
from bot.research.cards.pnl import pnl
from bot.research.cards.run import CardRun

ANALYSIS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis")
JST = timezone(timedelta(hours=9))


def _card_trades():
    """scripts/analysis/card_trades.py を読み込む(同じ置き場の diag_tables も読むので、その置き場を sys.path に足す)。"""
    if ANALYSIS not in sys.path:
        sys.path.insert(0, ANALYSIS)
    import card_trades
    return card_trades


def _iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def write_trades_check(d: str) -> dict:
    """card_trades.build(d) → card_trades.write_trades(取引, d) で d/trades.csv.gz を書き、日ごとの和を確かめる。"""
    ct = _card_trades()
    b = ct.build(d)
    path = ct.write_trades(b["trades"], d)
    daily = ct.load_daily(d)
    calc = b["daily_calc"]
    bad_calc = [x for x in daily if abs(daily[x] - calc.get(x, 0.0)) > 1e-9 * max(1.0, abs(daily[x]))]
    extra_calc = sorted(set(calc) - set(daily))
    by_day: dict = {}
    n_tr, tot = 0, 0.0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames
        for r in rd:
            v = float(r["pnl_bp"])
            n_tr += 1
            tot += v
            day = datetime.fromisoformat(r["signal_t"].replace("Z", "+00:00")).astimezone(JST).date().isoformat()
            by_day[day] = by_day.get(day, 0.0) + v
    d_tot = float(sum(daily.values()))
    tol = n_tr * 5e-7 + 1e-9 * abs(d_tot)
    day_mis = [x for x in daily if abs(daily[x] - by_day.get(x, 0.0)) > 1e-6 * max(1.0, n_tr)]
    out = {"path": path, "columns": cols, "n_trades": n_tr,
           "sides": {"buy": sum(1 for t in b["trades"] if t["side"] > 0), "sell": sum(1 for t in b["trades"] if t["side"] < 0)},
           "daily_calc_mismatch_days": len(bad_calc), "daily_calc_mismatch_examples": bad_calc[:5],
           "daily_calc_days_not_in_daily_csv": len(extra_calc),
           "sum_trades_bp": tot, "sum_daily_bp": d_tot, "sum_abs_diff": abs(tot - d_tot), "sum_tolerance": tol,
           "info_days_where_signal_day_sum_differs": len(day_mis),
           "info_note": "取引を signal_t の日本時間の日に寄せた和と daily.csv の比べ。0 時をまたいだ取引の日は合わないのが正しい(判定に入れない)"}
    out["ok"] = (not bad_calc and not extra_calc and abs(tot - d_tot) <= tol and cols == ["signal_t", "entry_t", "exit_t", "side", "pnl_bp"])
    return out


def write_signals(z: dict, d: str) -> dict:
    """カード 2: signal_log と signal_color・signal_strong を合図 1 つ = 1 行の d/signals.csv.gz に書く(並びは signal_log のまま)。"""
    log = z["signal_log"].reshape(-1, 4)
    color, strong = z["signal_color"], z["signal_strong"]
    if not (len(log) == len(color) == len(strong)):
        return {"ok": False, "why": f"行の数が揃わない signal_log {len(log)} / signal_color {len(color)} / signal_strong {len(strong)}"}
    path = os.path.join(d, "signals.csv.gz")
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["signal_t", "side", "signal_color", "signal_strong"])
        for (end_ns, side, _small, _big), c, s in zip(log.tolist(), color.tolist(), strong.tolist()):
            w.writerow([_iso(int(end_ns)), int(side), int(c), int(bool(s))])
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        n = sum(1 for _ in csv.DictReader(fh))
    return {"path": path, "n_rows": n, "n_signal_log": int(len(log)), "ok": n == len(log)}


def _lines(path: str) -> list:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines or lines[0] != "day,pnl_bp,n":
        raise SystemExit(f"{path}: day,pnl_bp,n の形の daily.csv ではない")
    return lines[1:]


def _sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def compare_daily(new_path: str, orig_path: str, require_identical: bool = False) -> dict:
    """require_identical=True(カード 1・2・3 の同じ期間の走らせ直し): sha256 が同じとき(= 日の数・最後の日を含む全部の行が
    同じ)だけ通す。False(カード 6 の延長): 短い方の最後の日より前の日の突き合わせで通す。"""
    new, orig = _lines(new_path), _lines(orig_path)
    sha_new, sha_orig = _sha(new_path), _sha(orig_path)
    out = {"new": new_path, "orig": orig_path, "sha256_new": sha_new, "sha256_orig": sha_orig,
           "identical": sha_new == sha_orig, "n_days_new": len(new), "n_days_orig": len(orig),
           "require_identical": require_identical, "same_n_days": len(new) == len(orig),
           "same_last_line": bool(new and orig and new[-1] == orig[-1])}
    if out["identical"]:
        out["ok"] = True
        return out
    dn = {ln.split(",")[0]: ln for ln in new}
    do = {ln.split(",")[0]: ln for ln in orig}
    last = min(new[-1].split(",")[0], orig[-1].split(",")[0]) if new and orig else None
    common = sorted(set(dn) & set(do))
    body = [d for d in common if last is None or d < last]
    bad = [d for d in body if dn[d] != do[d]]
    only_orig_before = sorted(d for d in set(do) - set(dn) if last is None or d < last)
    only_new_before = sorted(d for d in set(dn) - set(do) if last is None or d < last)
    out.update({"first_day_new": new[0].split(",")[0] if new else None,
                "first_day_orig": orig[0].split(",")[0] if orig else None,
                "last_day_compared_separately": last, "n_days_compared": len(body), "n_days_mismatch": len(bad),
                "mismatch_examples": [{"day": d, "new": dn[d], "orig": do[d]} for d in bad[:10]],
                "days_only_in_orig_before_last": only_orig_before[:10], "n_days_only_in_orig_before_last": len(only_orig_before),
                "days_only_in_new_before_last": only_new_before[:10], "n_days_only_in_new_before_last": len(only_new_before),
                "n_days_only_in_new_after_orig_end": len([d for d in dn if orig and d > orig[-1].split(",")[0]]),
                "last_day": {"new": dn.get(last), "orig": do.get(last)}})
    out["ok"] = (len(body) > 0 and not bad and not only_orig_before and not only_new_before
                 and out["first_day_new"] == out["first_day_orig"])
    if require_identical:  # 同じ期間のはずなので、最後の日・日の数・期間の長さの違いも通さない(上の数は調べるために残す)
        out["ok"] = False
        out["why_not_ok"] = "--require-identical: daily.csv の sha256 が元と違う"
    return out


def check_cols(z: dict) -> dict:
    out = {"keys": sorted(z)}
    vol = z["volume"]
    nonempty = vol > 0
    out["decided_equals_nonempty"] = bool(np.array_equal(z["decided"], nonempty))
    if "high" in z and "low" in z:
        o, c, h, lo = z["open"][nonempty], z["close"][nonempty], z["high"][nonempty], z["low"][nonempty]
        bad_h = int(np.sum(~(h >= np.maximum(o, c))))
        bad_l = int(np.sum(~(lo <= np.minimum(o, c))))
        out["high_low"] = {"n_nonempty": int(nonempty.sum()), "n_high_below_open_or_close": bad_h,
                           "n_low_above_open_or_close": bad_l, "ok": bad_h == 0 and bad_l == 0}
    else:
        out["high_low"] = {"ok": False, "why": "npz に high・low が無い"}
    if "signal_color" in z:
        log = z["signal_log"].reshape(-1, 4)
        color, strong = z["signal_color"], z["signal_strong"]
        same_n = len(color) == len(log) == len(strong)
        ok = same_n and bool(np.all(np.isin(color, (-1, 1)))) and bool(np.array_equal(strong, color == log[:, 1]))
        sig = log[:, 1] if same_n else np.zeros(0)
        kinds = {}
        if same_n:
            for nm, m in (("strong_buy", strong & (sig == 1)), ("strong_sell", strong & (sig == -1)),
                          ("weak_buy", ~strong & (sig == 1)), ("weak_sell", ~strong & (sig == -1))):
                kinds[nm] = int(m.sum())
        out["c2_kind"] = {"n_signals": int(len(log)), "n_color": int(len(color)), "counts": kinds, "ok": bool(ok)}
    return out


LAG1_CARDS = ("c3_yen_premium_revert",)  # 持ち高が連続の値のカード(e = 1 − 2q)。取引の行(±1 の区間)から持ち高を作り直せない


def needs_positions(z: dict, d: str) -> bool:
    """カード 3(run_record.json の card)か、決定の持ち高に −1・0・+1 以外の値があるとき、daily_lag1.csv と positions.npz を書く。"""
    card = None
    rp = os.path.join(d, "run_record.json")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as fh:
            card = json.load(fh).get("card")
    e = z["exposure"][z["decided"]]
    return card in LAG1_CARDS or not bool(np.all(np.isin(e, (-1.0, 0.0, 1.0))))


def lag1_pnl(z: dict):
    """持ち高を 1 本遅らせた損益(カード 3 の D10 次の手 2): 決定 t の持ち高 e_t を、t の後の 2 本目と 3 本目の空でない足の始値の間
    (open_{t+2} → open_{t+3})に当てる。P1_t = e_t × (open_{t+3} / open_{t+2} − 1) × 10,000(bp、経費の前)。
    t+k = t の後の k 本目の空でない足(決定のある足。pnl.py と同じ数え方)。最後の 3 決定は P1 なし。
    戻り: (決定の時刻 t_ns, P1) 。日は daily.csv と同じく決定の時刻 t の日本時間の日。"""
    dec = np.flatnonzero(z["decided"])
    m = len(dec) - 3
    if m < 1:
        raise SystemExit(f"空でない足 {len(dec)} 本では 1 本遅らせた損益が出ない")
    bar, a, b = dec[:m], dec[2:m + 2], dec[3:m + 3]
    p1 = z["exposure"][bar] * (z["open"][b] / z["open"][a] - 1.0) * 10_000.0
    return z["end_ns"][bar], p1


def write_lag1_positions(z: dict, d: str) -> dict:
    """d/daily_lag1.csv(day・pnl_bp・n。測定器の daily_rows・write_daily の形)と、d/positions.npz(決定の足の終わりの分
    t_end_min = end_ns ÷ 60 秒(int32)・持ち高 e(float32)、圧縮)を書く。git に入れる小さな出力(run.npz は消すため)。"""
    from types import SimpleNamespace
    t, p1 = lag1_pnl(z)
    sha = write_daily(daily_rows(SimpleNamespace(t_ns=t, pnl_bp=p1), "Asia/Tokyo"), os.path.join(d, "daily_lag1.csv"))
    dec = z["decided"]
    end = z["end_ns"][dec]
    ok_min = bool(np.all(end % (60 * 10**9) == 0))
    tm = (end // (60 * 10**9)).astype(np.int32)
    e32 = z["exposure"][dec].astype(np.float32)
    path = os.path.join(d, "positions.npz")
    np.savez_compressed(path, t_end_min=tm, e=e32)
    with np.load(path) as f:
        back_t, back_e = f["t_end_min"].astype(np.int64) * 60 * 10**9, f["e"].astype(np.float64)
    max_err = float(np.max(np.abs(back_e - z["exposure"][dec]))) if len(back_e) else 0.0
    return {"daily_lag1": os.path.join(d, "daily_lag1.csv"), "daily_lag1_sha256": sha, "n_lag1": int(len(p1)),
            "positions": path, "positions_bytes": os.path.getsize(path), "n_positions": int(len(e32)),
            "times_round_trip": bool(np.array_equal(back_t, end)), "end_on_minute": ok_min,
            "e_float32_max_abs_err": max_err,
            "ok": ok_min and bool(np.array_equal(back_t, end)) and max_err <= 1e-6}


def npz_daily(z: dict) -> list:
    nan = np.full(len(z["end_ns"]), np.nan)
    run = CardRun(card="rerun_check", venue="bitflyer", symbol="FX_BTC_JPY", start_ns=z["start_ns"], end_ns=z["end_ns"],
                  open=z["open"], high=z.get("high", nan), low=z.get("low", nan), close=z["close"], volume=z["volume"],
                  decided=z["decided"], exposure=z["exposure"])
    return daily_rows(pnl(run), "Asia/Tokyo")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--orig", required=True)
    ap.add_argument("--require-identical", action="store_true")
    a = ap.parse_args()
    with np.load(os.path.join(a.dir, "run.npz")) as f:
        z = {k: f[k] for k in f.files}
    res = {"dir": a.dir, "orig": a.orig}
    res["reproduce"] = compare_daily(os.path.join(a.dir, "daily.csv"), os.path.join(a.orig, "daily.csv"),
                                     require_identical=a.require_identical)
    res["cols"] = check_cols(z)
    with tempfile.TemporaryDirectory() as td:
        sha_re = write_daily(npz_daily(z), os.path.join(td, "daily.csv"))
    res["npz_vs_daily_csv_same"] = sha_re == _sha(os.path.join(a.dir, "daily.csv"))
    res["trades"] = write_trades_check(a.dir)
    if "signal_color" in z:
        res["signals"] = write_signals(z, a.dir)
    if needs_positions(z, a.dir):
        res["lag1_positions"] = write_lag1_positions(z, a.dir)
    ok = (res["reproduce"]["ok"] and res["cols"]["decided_equals_nonempty"] and res["cols"]["high_low"]["ok"]
          and res["cols"].get("c2_kind", {"ok": True})["ok"] and res["npz_vs_daily_csv_same"]
          and res["trades"]["ok"] and res.get("signals", {"ok": True})["ok"]
          and res.get("lag1_positions", {"ok": True})["ok"])
    res["ok"] = bool(ok)
    with open(os.path.join(a.dir, "rerun_check.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res, ensure_ascii=False, sort_keys=True), flush=True)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
