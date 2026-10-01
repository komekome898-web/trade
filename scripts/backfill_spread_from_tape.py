#!/usr/bin/env python3
"""bot の気配記録(spread_FX_BTC_JPY.csv)の抜けを、WebSocket の tape から補う台本。

目的
    取引 bot は REST で 5 秒ごとに気配を取って CSV に追記する。キルスイッチの発動中・bot の停止中は
    その記録だけが止まる。別プロセスの tape(WebSocket)は動き続けていたので、bot の記録の抜けの
    区間の中だけ、tape から同じ列の行を作る。bot の元の CSV は読むだけで書かない。

入力(すべて読むだけ)
    --bot-csv    spread_FX_BTC_JPY.csv  列 timestamp,best_bid,best_ask,ltp(timestamp は UNIX 秒)。
                 NUL バイトで壊れた行があるので、NUL を除き、4 列に満たない・数値でない行は捨てる。
    --bot-jsonl  bot.jsonl  "event": "kill_switch" の行(発動の時刻と detail)と
                 "event": "paper_state_restored" の行(再起動の印)を読む。
    --tape-dir   tape/ticker_YYYYMMDD.csv.gz(ts,best_bid,best_ask,...  気配が変化した行のみ)と
                 tape/executions_YYYYMMDD.csv.gz(ts,price,size,side)。ts は UTC の ISO 8601(末尾 Z)。

出力(--out-dir)
    spread_backfill.csv.gz  作った行。列 timestamp,best_bid,best_ask,ltp,source(source = tape_ws)
    gaps.csv                抜けごとの開始・終了・長さ・重なる発動・作った行数・tape の抜け
    標準出力                突き合わせの結果(README に転記する)
    MD5SUMS と README.md は出力ディレクトリに人が置く(この台本は書かない)。

閾値の根拠(実データで確認した値。再計算は標準出力の「行間隔の分布」)
    --gap-sec 60      bot の記録の行間隔が 60 秒を超えたら「抜け」。bot 自身の「データが古い」の
                      定義 config/config.yaml market_data.max_staleness_sec = 60 に合わせた。
                      行間隔の分布は p50=5.068 秒・p99=7.97 秒・p99.9=13.5 秒で、p99.9 までは通常の
                      REST の遅れ。60 秒超は 57 件(10 分超は 11 件)。
    --period-sec 5    作る行の刻み。config/config.yaml poll.ticker_sec = 5。実測の中央値 5.068 秒と整合。
    --tape-stale-sec 60  行の時刻以前の最新の ticker がこれより古い時刻は、tape の抜けとして行を作らない。
                      同じ 60 秒(bot の鮮度の定義)。tape の ticker の行間隔は p99.9=11.1 秒・
                      p99.99=33.2 秒で、60 秒超は 300 件(約 427 万行間隔のうち)。
    --ltp-stale-sec 608  ltp は executions の、その時刻以前の最新の約定値。約定は静かな時間帯に 60 秒以上空くのが
                      普通(60 秒超が 2,782 件)なので 60 秒は使わない。ticker が 60 秒以内の間隔で更新され続けて
                      いる間の約定の空きの実測の最大が 608 秒(2026-08-30 05:18:31→05:28:39)で、これを超える
                      約定の空きは ticker が生きていても約定の記録の欠測として行を作らない。
                      (約定の空きが 300 秒を超えた 90 件のうち ticker が連続して生きていたのは 5 件、608 秒超は 0 件。
                      実測の最大 37,307 秒の空きは ticker も同時に止まっていた。)

性質: 冪等(同じ入力から同じ出力。gzip の時刻は 0 固定)・乱数なし・ネットワークなし。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import gzip
import io
import json
import os
import sys

import numpy as np
import pandas as pd


def utc(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- 入力 ----
def load_bot_csv(path: str):
    raw = open(path, "rb").read()
    nul = raw.count(b"\0")
    lines = raw.replace(b"\0", b"").decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
    rows, dropped = [], 0
    for ln in lines[1:]:
        if not ln:
            continue
        p = ln.split(",")
        try:
            if len(p) != 4:
                raise ValueError
            rows.append([float(x) for x in p])
        except ValueError:
            dropped += 1
    arr = np.array(rows, dtype=np.float64)
    return arr, nul, dropped


def _parse_ts(s: pd.Series) -> np.ndarray:
    s = s.astype(str)
    if not s.str.endswith("Z").all():
        raise ValueError("ts の末尾が Z でない行がある(UTC 前提を確かめ直すこと)")
    sec = np.array(s.str[:19].to_numpy(), dtype="datetime64[s]").astype("int64").astype(np.float64)
    frac = s.str[19:-1].replace("", "0").astype(float).to_numpy()
    return sec + frac


def load_tape(tape_dir: str, kind: str, cols: list[str]) -> np.ndarray:
    parts = []
    for f in sorted(glob.glob(os.path.join(tape_dir, f"{kind}_*.csv.gz"))):
        df = pd.read_csv(f, usecols=cols, dtype={"ts": str})
        a = np.empty((len(df), len(cols)), dtype=np.float64)
        a[:, 0] = _parse_ts(df["ts"])
        for j, c in enumerate(cols[1:], start=1):
            a[:, j] = df[c].to_numpy(dtype=np.float64)
        parts.append(a)
    out = np.concatenate(parts)
    if (np.diff(out[:, 0]) < 0).any():  # 日をまたいで時刻が戻る行は整列して扱う
        out = out[np.argsort(out[:, 0], kind="stable")]
    return out


def load_events(path: str):
    kills, restores = [], []
    for ln in open(path, encoding="utf-8", errors="replace"):
        try:
            j = json.loads(ln)
        except ValueError:
            continue
        ev = j.get("event")
        if ev not in ("kill_switch", "paper_state_restored"):
            continue
        t = dt.datetime.fromisoformat(j["timestamp"]).timestamp()
        if ev == "kill_switch":
            kills.append((t, j.get("detail", ""), (j.get("state") or {}).get("time")))
        else:
            restores.append(t)
    kills.sort()
    restores.sort()
    return kills, np.array(restores)


# ------------------------------------------------------------ tape の引き ----
class Tape:
    def __init__(self, tk: np.ndarray, ex: np.ndarray, stale_sec: float, ltp_stale_sec: float):
        self.tt, self.bid, self.ask = tk[:, 0], tk[:, 1], tk[:, 2]
        self.et, self.px = ex[:, 0], ex[:, 1]
        self.stale = stale_sec
        self.ltp_stale = ltp_stale_sec

    def at(self, t: np.ndarray):
        """時刻 t 以前の最新の値。ticker_age / exec_age は秒(無ければ nan)。"""
        i = np.searchsorted(self.tt, t, side="right") - 1
        j = np.searchsorted(self.et, t, side="right") - 1
        ok_i, ok_j = i >= 0, j >= 0
        ii, jj = np.where(ok_i, i, 0), np.where(ok_j, j, 0)
        tk_age = np.where(ok_i, t - self.tt[ii], np.nan)
        ex_age = np.where(ok_j, t - self.et[jj], np.nan)
        bid = np.where(ok_i, self.bid[ii], np.nan)
        ask = np.where(ok_i, self.ask[ii], np.nan)
        ltp = np.where(ok_j, self.px[jj], np.nan)
        return bid, ask, ltp, tk_age, ex_age

    def ticker_ok(self, tk_age):
        return tk_age <= self.stale  # nan(tape の開始前)は False

    def usable(self, tk_age, ex_age):
        return self.ticker_ok(tk_age) & (ex_age <= self.ltp_stale)


def runs(times: np.ndarray, mask: np.ndarray):
    """mask が True の連続区間の (最初の時刻, 最後の時刻) の一覧。"""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            k = i
            while k + 1 < n and mask[k + 1]:
                k += 1
            out.append((times[i], times[k]))
            i = k + 1
        else:
            i += 1
    return out


def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else float("nan")


# ------------------------------------------------------------------ 本体 ----
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bot-csv", required=True)
    ap.add_argument("--bot-jsonl", required=True)
    ap.add_argument("--tape-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--gap-sec", type=float, default=60.0)
    ap.add_argument("--period-sec", type=float, default=5.0)
    ap.add_argument("--tape-stale-sec", type=float, default=60.0)
    ap.add_argument("--ltp-stale-sec", type=float, default=608.0)
    ap.add_argument("--compare-window-sec", type=float, default=3600.0)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    bot, nul, dropped = load_bot_csv(a.bot_csv)
    t = bot[:, 0]
    if (np.diff(t) <= 0).any():
        raise SystemExit("bot の時刻が単調増加でない: 台本の前提が崩れている")
    d = np.diff(t)
    print(f"[bot] 行数 {len(t)}  NUL バイト {nul}  捨てた行 {dropped}  最初 {utc(t[0])}  最後 {utc(t[-1])}")
    print("[行間隔の分布(秒)] " + "  ".join(f"p{q}={pct(d, q):.3f}" for q in (50, 90, 99, 99.9, 99.99))
          + f"  最大={d.max():.3f}")
    for th in (6, 10, 30, 60, 180, 600):
        print(f"  行間隔 > {th} 秒: {(d > th).sum()} 件")

    tk = load_tape(a.tape_dir, "ticker", ["ts", "best_bid", "best_ask"])
    ex = load_tape(a.tape_dir, "executions", ["ts", "price"])
    tape = Tape(tk, ex, a.tape_stale_sec, a.ltp_stale_sec)
    dtk = np.diff(tk[:, 0])
    print(f"[tape ticker] 行数 {len(tk)}  最初 {utc(tk[0,0])}  最後 {utc(tk[-1,0])}  行間隔 "
          + "  ".join(f"p{q}={pct(dtk, q):.3f}" for q in (50, 99, 99.9, 99.99)) + f"  60 秒超 {(dtk > 60).sum()} 件")
    print(f"[tape executions] 行数 {len(ex)}  最初 {utc(ex[0,0])}  最後 {utc(ex[-1,0])}")

    kills, restores = load_events(a.bot_jsonl)
    gi = np.where(d > a.gap_sec)[0]
    print(f"[抜け] 閾値 {a.gap_sec} 秒超: {len(gi)} 件(うち 600 秒超 {(d[gi] > 600).sum()} 件)")

    gap_rows, out_lines = [], []
    ltp_ages = []
    for n, i in enumerate(gi, start=1):
        s, e = float(t[i]), float(t[i + 1])
        k = np.arange(1, int(np.ceil((e - s) / a.period_sec)))
        grid = s + k * a.period_sec
        grid = grid[grid < e]
        bid, ask, ltp, tka, exa = tape.at(grid)
        ok = tape.usable(tka, exa)
        n_tk_skip = int((~tape.ticker_ok(tka)).sum())
        for tt_, b_, a_, l_ in zip(grid[ok], bid[ok], ask[ok], ltp[ok]):
            out_lines.append(f"{tt_:.3f},{float(b_)!r},{float(a_)!r},{float(l_)!r},tape_ws\n")
        ltp_ages.append(exa[ok])
        skipped = runs(grid, ~ok)
        kk = [(kt, kd, kst) for kt, kd, kst in kills if s <= kt <= e]
        kill_txt = ";".join(f"{utc(kt)} {kd}" for kt, kd, _ in kk) if kk else "発動なし"
        n_rest = int(((restores >= s) & (restores <= e)).sum())
        made = int(ok.sum())
        if len(grid) == 0:
            note = "区間が周期より短く行を作る時刻が無い"
        elif made == 0 and s + a.period_sec < tk[0, 0]:
            note = "作れなかった: 抜けの全体が tape の開始(%s)より前" % utc(tk[0, 0])
        elif made == 0:
            note = "作れなかった: 区間の全時刻で tape の ticker が %g 秒より古い、または約定が %g 秒より古い" % (a.tape_stale_sec, a.ltp_stale_sec)
        elif skipped:
            note = "一部作れなかった(tape の抜け): %d/%d 行" % (made, len(grid))
        else:
            note = ""
        gap_rows.append([
            n, utc(s), utc(e), f"{s:.3f}", f"{e:.3f}", f"{e - s:.3f}", kill_txt, n_rest,
            len(grid), made, len(grid) - made, n_tk_skip, len(grid) - made - n_tk_skip,
            ";".join(f"{utc(x)}~{utc(y)}" for x, y in skipped), note,
        ])
    covered = [(float(t[i]), float(t[i + 1])) for i in gi]
    print(f"[作成] 抜け {len(gi)} 件  作った行 {len(out_lines)}")
    la = np.concatenate(ltp_ages) if ltp_ages else np.array([])
    if len(la):
        print("[作った行の ltp の古さ(秒)] " + "  ".join(f"p{q}={pct(la, q):.1f}" for q in (50, 90, 99)) + f"  最大={la.max():.1f}"
              f"  300 秒超 {(la > 300).sum()} 行")
    # 抜けの外にある発動
    for kt, kd, _ in kills:
        if not any(s <= kt <= e for s, e in covered):
            where = "bot の CSV の範囲より前" if kt < t[0] else "抜けの外"
            print(f"[抜けと重ならない発動] {utc(kt)} {kd} ({where})")

    with open(os.path.join(a.out_dir, "spread_backfill.csv.gz"), "wb") as fo, \
            gzip.GzipFile(filename="", mode="wb", fileobj=fo, mtime=0) as gz:
        gz.write(("timestamp,best_bid,best_ask,ltp,source\n" + "".join(out_lines)).encode("utf-8"))
    with open(os.path.join(a.out_dir, "gaps.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["gap_id", "start_utc", "end_utc", "start_ts", "end_ts", "length_sec", "kill_switch",
                    "restart_events", "rows_expected", "rows_made", "rows_skipped",
                    "skipped_ticker_stale", "skipped_ltp_stale", "tape_gaps_utc", "note"])
        w.writerows(gap_rows)

    # ------------------------------------------------ 突き合わせ(抜けの外) ----
    win = np.zeros(len(t), dtype=bool)
    for i in gi:
        s, e = t[i], t[i + 1]
        win |= (t >= s - a.compare_window_sec) & (t <= s)
        win |= (t >= e) & (t <= e + a.compare_window_sec)
    cover_end = min(tk[-1, 0], ex[-1, 0])
    report_compare("抜けの前後 %g 秒" % a.compare_window_sec, bot, win & (t <= cover_end), tape, a)
    report_compare("参考: 記録全体(tape の範囲内)", bot, (t <= cover_end) & (t >= max(tk[0, 0], ex[0, 0])), tape, a)
    return 0


def report_compare(label, bot, sel, tape, a):
    t = bot[:, 0]
    idx = np.where(sel)[0]
    bid, ask, ltp, tka, exa = tape.at(t[idx])
    ok = tape.usable(tka, exa)
    n_all, n_ok = len(idx), int(ok.sum())
    stale = ~ok
    # tape の ticker が古い行で、REST の気配が tape の最後の値と違う割合(tape の抜けが本当に欠測かの手がかり)
    st_idx = idx[stale & ~np.isnan(tka)]
    differs = ((bot[st_idx, 1] != bid[stale & ~np.isnan(tka)]) | (bot[st_idx, 2] != ask[stale & ~np.isnan(tka)])).sum()
    print(f"\n[突き合わせ: {label}] bot の行 {n_all}  tape で作れた行 {n_ok}  作れなかった行 {int(stale.sum())}"
          f"(うち REST の bid/ask が tape の最後の値と異なる {int(differs)})")
    i2, bid, ask, ltp = idx[ok], bid[ok], ask[ok], ltp[ok]
    mid_b = (bot[i2, 1] + bot[i2, 2]) / 2
    mid_t = (bid + ask) / 2
    dmid = (mid_t - mid_b) / mid_b * 1e4
    adm = np.abs(dmid)
    print(f"  mid の差 (tape - REST, bp): 符号付き中央値 {np.median(dmid):.3f}  絶対値の中央値 {np.median(adm):.3f}"
          f"  絶対値の p95 {pct(adm, 95):.3f}  絶対値の p99 {pct(adm, 99):.3f}")
    sp_b = (bot[i2, 2] - bot[i2, 1]) / mid_b * 1e4
    sp_t = (ask - bid) / mid_t * 1e4
    print(f"  スプレッド幅 (bp): REST 中央値 {np.median(sp_b):.3f}  tape 中央値 {np.median(sp_t):.3f}"
          f"  差(tape-REST)の絶対値の中央値 {np.median(np.abs(sp_t - sp_b)):.3f}  p95 {pct(np.abs(sp_t - sp_b), 95):.3f}")
    print(f"  bid/ask が完全一致する行: bid {np.mean(bot[i2,1]==bid)*100:.1f}%  ask {np.mean(bot[i2,2]==ask)*100:.1f}%")
    dl = (ltp - bot[i2, 3]) / bot[i2, 3] * 1e4
    print(f"  ltp の差 (bp): 絶対値の中央値 {np.median(np.abs(dl)):.3f}  p95 {pct(np.abs(dl), 95):.3f}"
          f"  完全一致 {np.mean(ltp == bot[i2, 3])*100:.1f}%")
    # 基準: bot の連続する 2 行(約 5 秒)の mid の動き
    cons = np.where(np.isin(idx[:-1] + 1, idx[1:]) & (np.diff(idx) == 1))[0]
    if len(cons):
        a_, b_ = idx[cons], idx[cons] + 1
        m0, m1 = (bot[a_, 1] + bot[a_, 2]) / 2, (bot[b_, 1] + bot[b_, 2]) / 2
        step = np.abs(m1 - m0) / m0 * 1e4
        print(f"  基準 bot の連続 2 行(約 5 秒)の mid の動き (bp): 絶対値の中央値 {np.median(step):.3f}  p95 {pct(step, 95):.3f}")


if __name__ == "__main__":
    sys.exit(main())
