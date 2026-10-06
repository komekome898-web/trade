#!/usr/bin/env python3
"""部品 3: カード 8(変種 jst_day)を Binance BTCUSDT の 1 分足で回す台本(段 2 で使う。段 1 では --dry でしか動かさない)。

    (段 2)   PYTHONPATH=src python3 scripts/w4_measure/c8_binance/bn_run_c8.py [--start --end --out-root]
    (段 1)   PYTHONPATH=src python3 scripts/w4_measure/c8_binance/bn_run_c8.py --dry [--out-root <scratch>]

カードの本体は bot.research.cards.library.c8_session_mean_revert.SessionMeanRevert をそのまま import する(写さない)。
つなぎ方は scripts/w4_measure/run_b2.py の run_chunks と同じ: 暦年ごとに部品 1(bn_bars)の口で足を読み、同じカードの物を
年をまたいで使い続けて run_card に通し、run_v2.concat でつなぐ(カード 8 は view.bars(1) と自分の属性しか読まない)。

出力(bitFlyer のとき = run_b2.py + light_b2.measure と同じ物):
  daily.csv・daily_stats.json・extra.json・diagnostics.json(light_b2.diag_c8)・run_record.json・run.npz
足した物:
  trades.json.gz       取引の記録(scripts/dashboard_cards/export_card_trades.py のカード 8 の作り方。write_trades_json で書く)
  daily_mid.csv        中ほどの値 mid = (高値 + 安値) ÷ 2 で約定した日ごとの損益(c8_redo.py と同じ定義):
                       P^mid_t = e_t × (mid_{t+2} / mid_{t+1} − 1) × 10,000(t+1・t+2 は pnl.py と同じ次の空でない足)。
                       日 = 決定の時刻 t の日本時間の日(daily.csv と同じ)。
  boundary_carry_days.csv  セッションの区切りをまたいだ持ち高の決定の一覧(diag_c8 の 5_boundary_carry と同じ規則を書き直し、
                       その決定の日を足した。列: day = その決定の損益が乗った日(daily.csv と同じ日)・t・pnl_bp・
                       minutes_after_boundary)。数と和が diagnostics.json と合うことを run_record.json に書く。
  run_record.json の close_eq_mean  診断: 終値 = セッションの平均だった決定の数(整数のセントで正確に比べる。close_eq_mean)。
値段の単位: カードと run.npz の値段は部品 1 の口が返す整数のセント(0.01 USDT = 1)。trades.json.gz の値段だけ USDT に戻す。
損益の bp は値段の比なので単位に依らない。run_record.json の price_unit に書く。

--dry: (1) 作り物でない読み: 2019-01-01〜2019-01-08 の足を部品 1 の口で読み、読みの事実だけを出す(カードは回さない。
       損益は出さない)。(2) 作り物の足で、上の出力を全部作る(置き場は --out-root。無ければ一時の置き場)。
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import gc
import json
import os
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
W4 = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, W4)

import bn_bars  # noqa: E402
from common import ROOT, iso, to_iso  # noqa: E402
from post import write_json  # noqa: E402
from run_v2 import concat  # noqa: E402

from bot.bt.core import BarEvent  # noqa: E402
from bot.research.cards import cardmd  # noqa: E402
from bot.research.cards.library.c8_session_mean_revert import BAR_NS, SESSIONS, SessionMeanRevert  # noqa: E402
from bot.research.cards.measure import daily_rows, write_daily  # noqa: E402
from bot.research.cards.pnl import pnl  # noqa: E402
from bot.research.cards.run import run_card  # noqa: E402
from bot.research.trade_record import write_trades_json  # noqa: E402

CARD_ID = "c8_session_mean_revert"
VARIANT = "jst_day"
NS = 1_000_000_000
DAY_NS = 86_400 * NS
JST_NS = 9 * 3600 * NS
PERIOD = ("2017-08-17T15:00:00Z", "2023-12-17T15:00:00Z")  # 置き場の最初の日本時間の日の終わり(最初の丸 1 日の始まり)〜
DRY_READ = ("2019-01-01T00:00:00Z", "2019-01-08T00:00:00Z")
OUT_ROOT = os.path.join(ROOT, f"docs/RESEARCH/cards/{CARD_ID}/binance_gate/measure")


def declarations() -> dict:
    with open(os.path.join(ROOT, f"docs/RESEARCH/cards/{CARD_ID}/CARD.md"), encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"CARD.md の測定の設定が読めない: {problems}")
    return dict(st.declarations)


def run_chunks(card, chunks, decl: dict):
    """chunks: (名前, BarEvent の並び) の並び。同じカードの物で順に run_card に通し、concat でつなぐ。"""
    runs, log = [], []
    for name, bars in chunks:
        if not bars:
            log.append({"range": name, "bars": 0, "decisions": 0, "delivery_digest": ""})
            continue
        r = run_card(card, bars, references={}, declarations=decl, venue=bn_bars.VENUE, symbol=bn_bars.SYMBOL)
        runs.append(r)
        log.append({"range": name, "bars": len(bars), "decisions": int(r.decided.sum()),
                    "delivery_digest": r.delivery_digest})
        del bars
        gc.collect()
    return concat(runs, [x for x in log if x["bars"]]), log


def mid_pnl(run, p):
    """中ほどの値で約定した P^mid_t(p と同じ決定・同じ約定の足・同じ出の足)。"""
    mid = (run.high + run.low) / 2.0
    return p.exposure * (mid[p.exit_bar] / mid[p.fill_bar] - 1.0) * 1e4


def carry_rows(run, p, variant: str = VARIANT) -> tuple:
    """diag_c8 の 5_boundary_carry と同じ規則(セッションの最後の決定が区切りの足でなく、持ち高 ≠ 0)。
    戻り: (区切りをまたいだ回数(損益の無い最後の 2 決定も含む = diag_c8 の n_carried), 行の並び)。
    行 = 損益のある決定だけ: {day(決定の時刻 t の日本時間の日 = daily.csv の日), t, pnl_bp, minutes_after_boundary}。"""
    off = SESSIONS[variant]
    dec = np.flatnonzero(run.decided)
    end = run.end_ns[dec]
    ex = run.exposure[dec]
    ses = (end - BAR_NS + off) // DAY_NS
    at_end = ((end + off) % DAY_NS) == 0
    brk = np.flatnonzero(np.diff(ses) != 0) + 1
    stops = np.concatenate([brk, [len(ses)]])
    last = stops - 1
    carry = ((~at_end[last]) & (ex[last] != 0))[:-1]  # 最後のセッションの後には区切りが無い
    pos = {int(b): k for k, b in enumerate(p.bar)}
    rows = []
    for k in np.flatnonzero(carry):
        bi = int(dec[last[k]])
        if bi not in pos:
            continue
        j = pos[bi]
        B = (int(ses[last[k]]) + 1) * DAY_NS - off
        day = str(np.datetime64((int(p.t_ns[j]) + JST_NS) // DAY_NS, "D"))
        rows.append({"day": day, "t": to_iso(int(p.t_ns[j])), "pnl_bp": float(p.pnl_bp[j]),
                     "minutes_after_boundary": max(0, int(run.start_ns[p.exit_bar[j]]) - B) / 60e9})
    return int(carry.sum()), rows


def write_carry(rows: list, path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["day", "t", "pnl_bp", "minutes_after_boundary"])
        for r in rows:
            w.writerow([r["day"], r["t"], float.__repr__(r["pnl_bp"]), float.__repr__(float(r["minutes_after_boundary"]))])


def trades(run, p, extra_stats_fn, price_scale: float = 1.0) -> list:
    """export_card_trades.py のカード 8 の作り方(取引 = 同じ向きの決定のつながり、qty = 区間の |e| の平均)。
    entry_px・exit_px = run の始値 ÷ price_scale(セントの run なら USDT に戻す)。"""
    e_all = run.exposure[run.decided]
    _ex, tr = extra_stats_fn(p, e_all, 1)
    st, tn = tr["trade_start"], tr["trade_n"]
    last = st + tn - 1
    absum = np.concatenate([[0.0], np.cumsum(np.abs(p.exposure))])
    qty = (absum[last + 1] - absum[st]) / tn
    return [{"entry_t_ns": int(run.start_ns[p.fill_bar[a]]), "entry_px": float(run.open[p.fill_bar[a]]) / price_scale,
             "exit_t_ns": int(run.start_ns[p.exit_bar[b]]), "exit_px": float(run.open[p.exit_bar[b]]) / price_scale,
             "side": int(sd), "qty": float(q), "pnl_bp": float(pb)}
            for a, b, sd, q, pb in zip(st, last, tr["trade_side"], qty, tr["trade_pnl"])]


def close_eq_mean(run, variant: str = VARIANT) -> dict:
    """診断(委任文 fix1 の 1): 終値 = その時のセッションの平均(呼ばれた足の終値の和 ÷ 本数、今の足を含む)だった決定の数。
    値段が整数(セント)のときだけ、整数の和で正確に数える(close × 本数 == 和)。整数でない終値があれば数えない。
    内訳: セッションの最初の決定(平均 = その終値なので必ず等しい)・セッションの終わりの足(カードが 0 にする足)・それ以外。
    n_nonzero_exposure_at_eq = 等しかった決定のうち持ち高 ≠ 0 の数(カードの決まりどおりなら 0)。"""
    off = SESSIONS[variant]
    dec = np.flatnonzero(run.decided)
    c = run.close[dec]
    out = {"what": "終値 = セッションの平均(呼ばれた足の終値の和 ÷ 本数、今の足を含む)だった決定の数(整数の値段で正確に比べた)",
           "n_decisions": int(len(dec))}
    n_not_int = int(np.sum(c != np.rint(c)))
    if n_not_int:
        out.update({"n_close_not_integer": n_not_int, "not_computed": "整数でない終値があるので正確に比べられない"})
        return out
    ci = np.rint(c).astype(np.int64)
    end = run.end_ns[dec]
    ses = (end - BAR_NS + off) // DAY_NS
    at_end = ((end + off) % DAY_NS) == 0
    brk = np.flatnonzero(np.diff(ses) != 0) + 1
    starts = np.concatenate([[0], brk])
    stops = np.concatenate([brk, [len(ses)]])
    eq = np.zeros(len(dec), dtype=bool)
    first = np.zeros(len(dec), dtype=bool)
    for a, b in zip(starts, stops):
        cs = np.cumsum(ci[a:b])
        eq[a:b] = ci[a:b] * np.arange(1, b - a + 1, dtype=np.int64) == cs
        first[a] = True
    ex = run.exposure[dec]
    other = eq & ~first & ~at_end
    out.update({"n_close_not_integer": 0, "n_sessions": int(len(starts)), "n_close_eq_mean": int(eq.sum()),
                "n_first_of_session": int((eq & first).sum()), "n_session_end_bar": int((eq & ~first & at_end).sum()),
                "n_other": int(other.sum()), "n_nonzero_exposure_at_eq": int(np.sum(eq & (ex != 0))),
                "sum_upper_bound": int(np.max(np.abs(ci))) * int(np.max(stops - starts)) if len(ci) else 0})
    out["sum_exact_in_card"] = bool(out["sum_upper_bound"] < 2**53)  # カードの浮動小数の和が正確な範囲か
    return out


def write_outputs(run, outdir: str, lo: int, hi: int, record: dict, price_scale: float = bn_bars.PRICE_SCALE,
                  price_unit: str = bn_bars.PRICE_UNIT_CENTS) -> dict:
    """bitFlyer のときの出力 + daily_mid.csv・trades.json.gz・boundary_carry_days.csv。
    run の値段は price_unit(既定 = 整数のセント)。trades.json.gz の値段だけは ÷ price_scale で USDT に戻して書く。"""
    import light_b2
    os.makedirs(outdir, exist_ok=True)
    npz = os.path.join(outdir, "run.npz")
    np.savez_compressed(npz, open=run.open, high=run.high, low=run.low, close=run.close, exposure=run.exposure,
                        decided=run.decided, end_ns=run.end_ns, start_ns=run.start_ns, volume=run.volume)
    p = pnl(run)
    stats = light_b2.measure("c8", VARIANT, run, p, outdir, lo, hi)
    pm = mid_pnl(run, p)
    sha_mid = write_daily(daily_rows(dataclasses.replace(p, pnl_bp=pm), "Asia/Tokyo"), os.path.join(outdir, "daily_mid.csv"))
    n_tr = write_trades_json(os.path.join(outdir, "trades.json.gz"), trades(run, p, light_b2.extra_stats, price_scale))
    n_carried, rows = carry_rows(run, p)
    write_carry(rows, os.path.join(outdir, "boundary_carry_days.csv"))
    with open(os.path.join(outdir, "diagnostics.json"), encoding="utf-8") as fh:
        dg = json.load(fh)["5_boundary_carry"]
    carry_check = {"n_carried_diag": dg["n_carried"], "n_carried_rewrite": n_carried,
                   "carried_sum_bp_diag": dg["carried_sum_bp"], "carried_sum_bp_rewrite": float(np.sum([r["pnl_bp"] for r in rows])),
                   "n_rows_with_pnl": len(rows), "n_days": len({r["day"] for r in rows})}
    carry_check["same"] = bool(carry_check["n_carried_diag"] == n_carried
                               and abs(carry_check["carried_sum_bp_diag"] - carry_check["carried_sum_bp_rewrite"]) < 1e-9)
    summary = {"card": CARD_ID, "variant": VARIANT, "venue": bn_bars.VENUE, "symbol": bn_bars.SYMBOL,
               "period": [to_iso(lo), to_iso(hi)], "chunk": "year", **record,
               "npz": os.path.relpath(npz, ROOT) if npz.startswith(ROOT) else npz,
               "price_unit": {"run_npz_and_card": price_unit, "trades_json": f"値段 ÷ {price_scale}"},
               "daily_mid_csv_sha256": sha_mid, "n_trades_written": n_tr, "boundary_carry_check": carry_check,
               "close_eq_mean": close_eq_mean(run), "headline": stats}
    write_json(summary, os.path.join(outdir, "run_record.json"))
    return summary


def fabricated_bars(start_iso: str = "2019-01-01T12:00:00Z", n: int = 7 * 1440, *, seed: int = 20261006,
                    scale: float = 1.0, drop=(), zero_volume=(), flat=()) -> list:
    """作り物の 1 分足(試験と --dry の 2 番目)。drop の番号の足は無し、zero_volume の番号の足は量 0(取引の無い分)。
    flat の番号の足は 始値 = 高値 = 安値 = 終値 = その足の始値(同じ値段が続く平らな区間)。flat が空なら前の版と同じ足。"""
    rng = np.random.default_rng(seed)
    t0 = iso(start_iso)
    px = 100.0 * np.exp(np.cumsum(rng.normal(0, 1e-3, n + 1)))
    flat = set(flat)
    for i in sorted(flat):
        px[i + 1] = px[i]
    out = []
    for i in range(n):
        if i in drop:
            continue
        o, c = px[i] * scale, px[i + 1] * scale
        h, lo = (o, o) if i in flat else (max(o, c) * (1 + 2e-4), min(o, c) * (1 - 2e-4))
        s = t0 + i * 60 * NS
        out.append(BarEvent(received_time_ns=s + 60 * NS, start_time_ns=s, open=o, high=h, low=lo, close=c,
                            volume=0.0 if i in zero_volume else 1.0))
    return out


def dry(out_root: str | None) -> int:
    lo, hi = iso(DRY_READ[0]), iso(DRY_READ[1])
    bars, facts = bn_bars.load_chunk(lo, hi)
    print(json.dumps({"dry_read": {k: facts.get(k) for k in ("range", "n_bars_kept", "n_synthetic_dropped",
                                                              "n_missing_minutes", "anomalies", "files",
                                                              "first_start", "last_start", "n_ntrades0_volume_pos",
                                                              "n_kept_volume0", "resolution", "price_unit",
                                                              "n_not_whole_cent")},
                      "first_bar_cents": [bars[0].open, bars[0].high, bars[0].low, bars[0].close] if bars else None,
                      "card_run_on_real_bars": "しない(段 1)"}, ensure_ascii=False), flush=True)
    del bars
    out_root = out_root or tempfile.mkdtemp(prefix="c8bn_dry_")
    # 作り物の足も、本物と同じく整数のセントにしてから回す(値段を 3 万台の USDT に寄せ、セッションの最初の 60 本に平らな区間を入れる)
    fb = fabricated_bars(drop={100, 101, 179, 179 + 1440, 2000}, zero_volume={50, 1438, 2879}, scale=356.9872,
                         flat=range(180, 240))  # 179 = 14:59Z に始まる足(区切りの足)、180〜239 = セッションの最初の 60 本
    fb, _ = bn_bars.to_cents(fb)
    mid = len(fb) // 2
    run, log = run_chunks(SessionMeanRevert(VARIANT), [("fab_a", fb[:mid]), ("fab_b", fb[mid:])], declarations())
    s = write_outputs(run, os.path.join(out_root, VARIANT), int(fb[0].start_time_ns), int(fb[-1].exchange_time_ns),
                      {"chunks": log, "inputs": {"bars": "作り物(fabricated_bars)"}, "dry": True})
    od = os.path.join(out_root, VARIANT)
    print(json.dumps({"dry_fabricated_out": od,
                      "files": {f: os.path.getsize(os.path.join(od, f)) for f in sorted(os.listdir(od))},
                      "n_bars": len(fb), "boundary_carry_check": s["boundary_carry_check"],
                      "close_eq_mean": s["close_eq_mean"], "price_unit": s["price_unit"]}, ensure_ascii=False), flush=True)
    return 0 if s["boundary_carry_check"]["same"] else 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--start", default=PERIOD[0])
    ap.add_argument("--end", default=PERIOD[1])
    ap.add_argument("--out-root", default=None)
    a = ap.parse_args()
    if a.dry:
        return dry(a.out_root)
    lo, hi = iso(a.start), iso(a.end)
    bn_bars.check_range(lo, hi)
    t0 = time.time()
    facts_all = []

    def chunks():
        for y, bars, facts in bn_bars.iter_range(lo, hi):
            facts_all.append(facts)
            yield str(y), bars

    run, log = run_chunks(SessionMeanRevert(VARIANT), chunks(), declarations())
    outdir = os.path.join(a.out_root or OUT_ROOT, VARIANT)
    s = write_outputs(run, outdir, lo, hi, {"chunks": log, "inputs": {"bars": facts_all},
                                            "timing": {"total_s": round(time.time() - t0, 1)}})
    print(json.dumps({"out": outdir, "boundary_carry_check": s["boundary_carry_check"]}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
