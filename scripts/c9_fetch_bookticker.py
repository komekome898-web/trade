#!/usr/bin/env python3
"""カード 9 の走らせ直し(2026-10-06): COIN-M BTCUSD_PERP の最良気配を、状態機械の目標の時刻の分だけ引き出す。

リードの決め(批評家 1 回目 `docs/AUDITOR/VERDICTS/2026-10-06_c9_rerun_critic1.md` の [止める] を受けた直し):
約定の値段 = Binance 公開アーカイブ `futures/cm/daily/bookTicker/BTCUSD_PERP/` の最良気配。
取るのは `--first-day`〜`--last-day`(既定 2023-06-21〜2023-12-16)の日だけ。2023-12-17 以後の日付の
ファイルは取らない・問い合わせない(`--last-day` に 2023-12-17 以後を渡すと止まる)。

1 日ずつ: zip と `.CHECKSUM` を取る → sha256 を照らす → zip の中の CSV を直接読む(展開物を書かない)→
その日の目標の時刻ごとに「目標の時刻以前(ちょうどを含む)で最新の気配」を引く → zip を消す。
生のファイルは残さない。残すのは `--out` の下の
- `days/<日>.csv.gz`: 列 target_ms・q_ms・bid・ask・src(当日 / 前日 / 無し)
- `fetch_log.jsonl`: 1 日 1 行(day・status・bytes・sha256・行数・目標の数・最後の気配・所要)
- `targets_meta.json`: 目標の組の出所(読み口・期間・数)

目標の時刻の組 = `liq_cascade_fill.targets_for_prints`(各プリント + 遅れ ∪ 各束の最後 + g + 遅れ)。
プリントは `c9_run_a.py` と同じく `--data-root` から [`--start` − 4 日, `--end` + 4 日] を読む
(走らせと同じ引数を渡す)。
気配の時刻は `transaction_time`。同じ ms の行は後の行(update_id の大きい方)を最新とする。
目標の日の中に目標以前の気配が無いときは、前の日が取れていればその日の最後の気配を書く(src = 前日)。
前の日が取れていなければ書かない(src = 無し。欠けた日を越えて埋めない)。古さ 300 秒の判定は
走らせの側(`QuoteBook.lookup`)で行う。取れなかった日は `status` に理由を書き、表は作らない。

    PYTHONPATH=src python3 scripts/c9_fetch_bookticker.py \
        --data-root data/c9_run_a/cut_root_20231216 --start 2023-06-25 --end 2023-12-17 \
        --out data/c9_bookticker

途中で止まっても、同じコマンドで続きから(`fetch_log.jsonl` に ok のある日は飛ばす)。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.research import liq_cascade_fill as fill  # noqa: E402
from bot.research import liq_cascade_v2 as v2  # noqa: E402

BASE_URL = "https://data.binance.vision/data/futures/cm/daily/bookTicker/BTCUSD_PERP"
LAST_ALLOWED = date(2023, 12, 16)     # 封印の境 2023-12-17T15:00Z を越えない最後の日まるごと
PRINT_MARGIN_DAYS = 4                 # c9_run_a.PRINT_MARGIN_DAYS と同じ


def file_name(day: str) -> str:
    return f"BTCUSD_PERP-bookTicker-{day}.zip"


def curl(url: str, dest: Path, tries: int = 3) -> tuple[int, str]:
    """(HTTP の番号, 誤りの文)。成功は (200, "")。"""
    last = (0, "")
    for k in range(tries):
        r = subprocess.run(["curl", "-sS", "-o", str(dest), "-w", "%{http_code}", url],
                           capture_output=True, text=True)
        code = int(r.stdout.strip() or 0) if r.stdout.strip().isdigit() else 0
        if code == 200:
            return 200, ""
        last = (code, r.stderr.strip()[:200])
        if code == 404:
            break
        time.sleep(2 * (k + 1))
    return last


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_quotes(zp: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zp) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise RuntimeError(f"zip の中の CSV が 1 つでない: {names}")
        with z.open(names[0]) as fh:
            df = pd.read_csv(fh, usecols=["update_id", "best_bid_price", "best_ask_price",
                                          "transaction_time"])
    return df.sort_values(["transaction_time", "update_id"], kind="stable").reset_index(drop=True)


def quotes_at(df: pd.DataFrame, targets: np.ndarray, prev_last: dict | None) -> list[dict]:
    """目標の時刻ごとに、以前(ちょうどを含む)で最新の気配。"""
    tt = df["transaction_time"].to_numpy(np.int64)
    bid = df["best_bid_price"].to_numpy(float)
    ask = df["best_ask_price"].to_numpy(float)
    i = np.searchsorted(tt, targets, side="right") - 1
    rows = []
    for t, k in zip(targets.tolist(), i.tolist()):
        if k >= 0:
            rows.append({"target_ms": t, "q_ms": int(tt[k]), "bid": float(bid[k]),
                         "ask": float(ask[k]), "src": "当日"})
        elif prev_last is not None:
            rows.append({"target_ms": t, "q_ms": prev_last["q_ms"], "bid": prev_last["bid"],
                         "ask": prev_last["ask"], "src": "前日"})
        else:
            rows.append({"target_ms": t, "q_ms": "", "bid": "", "ask": "", "src": "無し"})
    return rows


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".part")
    with gzip.open(tmp, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["target_ms", "q_ms", "bid", "ask", "src"])
        w.writeheader()
        for r in rows:
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in r.items()})
    tmp.replace(path)


def load_log(p: Path) -> dict:
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["day"]] = r
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", required=True, help="c9_run_a.py に渡す読み口(プリントを読む)")
    ap.add_argument("--start", required=True, help="c9_run_a.py の --start")
    ap.add_argument("--end", required=True, help="c9_run_a.py の --end")
    ap.add_argument("--out", required=True)
    ap.add_argument("--first-day", default="2023-06-21")
    ap.add_argument("--last-day", default=LAST_ALLOWED.isoformat())
    ap.add_argument("--base-url", default=BASE_URL)
    args = ap.parse_args(argv)
    first, last = date.fromisoformat(args.first_day), date.fromisoformat(args.last_day)
    if last > LAST_ALLOWED:
        raise SystemExit(f"[止め] --last-day {last} は 2023-12-17 以後の日を含む(取らない・問い合わせない)")
    out = Path(args.out)
    tmpdir = out / "tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    logp = out / "fetch_log.jsonl"
    done = load_log(logp)

    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    pr = v2.load_prints(Path(args.data_root), start - timedelta(days=PRINT_MARGIN_DAYS),
                        end + timedelta(days=PRINT_MARGIN_DAYS))
    targets = fill.targets_for_prints(pr)
    tday = np.array([fill.day_of(t) for t in targets.tolist()], dtype=object)
    (out / "targets_meta.json").write_text(json.dumps({
        "data_root": str(args.data_root), "start": args.start, "end": args.end,
        "プリント": len(pr), "目標の時刻": int(targets.size),
        "目標の日の範囲": [str(tday.min()), str(tday.max())] if targets.size else [],
        "取る日": [first.isoformat(), last.isoformat()]}, ensure_ascii=False, indent=1))
    print(f"[bt] プリント {len(pr)} 目標 {targets.size}", flush=True)

    d = first
    prev_last = None
    while d <= last:
        day = d.isoformat()
        r0 = done.get(day)
        if r0 is not None and r0.get("status") == "ok":
            prev_last = r0.get("last_quote")
            d += timedelta(days=1)
            continue
        t0 = time.time()
        zp = tmpdir / file_name(day)
        cp = tmpdir / (file_name(day) + ".CHECKSUM")
        rec = {"day": day, "url": f"{args.base_url}/{file_name(day)}"}
        code, err = curl(f"{args.base_url}/{file_name(day)}.CHECKSUM", cp)
        code2, err2 = (curl(f"{args.base_url}/{file_name(day)}", zp) if code == 200
                       else (code, err))
        if code != 200 or code2 != 200:
            rec |= {"status": f"取れない(HTTP {code}/{code2})", "err": err or err2}
            prev_last = None
        else:
            want = cp.read_text().split()[0].strip()
            got = sha256(zp)
            rec |= {"bytes": zp.stat().st_size, "sha256": got, "checksum_file": want}
            if want != got:
                rec |= {"status": "sha256 が CHECKSUM と違う"}
                prev_last = None
            else:
                df = read_quotes(zp)
                tg = targets[tday == day]
                rows = quotes_at(df, tg, prev_last)
                write_rows(out / "days" / f"{day}.csv.gz", rows)
                lq = {"q_ms": int(df["transaction_time"].iloc[-1]),
                      "bid": float(df["best_bid_price"].iloc[-1]),
                      "ask": float(df["best_ask_price"].iloc[-1])} if len(df) else None
                src = pd.Series([r["src"] for r in rows]).value_counts().to_dict()
                rec |= {"status": "ok", "行数": int(len(df)),
                        "最初の気配_ms": int(df["transaction_time"].iloc[0]) if len(df) else None,
                        "目標の数": int(tg.size), "src": src, "last_quote": lq}
                prev_last = lq
        for p in (zp, cp):
            if p.exists():
                p.unlink()
        rec["所要_秒"] = round(time.time() - t0, 2)
        with open(logp, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[bt] {day} {rec['status']} {rec.get('bytes', '')} {rec['所要_秒']}s", flush=True)
        d += timedelta(days=1)
    log = load_log(logp)
    days = [x for x in log.values() if first.isoformat() <= x["day"] <= last.isoformat()]
    summ = {"取る日の数": (last - first).days + 1,
            "取れた日": sum(1 for x in days if x["status"] == "ok"),
            "取れなかった日": sorted(x["day"] for x in days if x["status"] != "ok"),
            "合計バイト": sum(int(x.get("bytes", 0)) for x in days if x["status"] == "ok")}
    (out / "fetch_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1))
    print(json.dumps(summ, ensure_ascii=False), flush=True)
    try:
        tmpdir.rmdir()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
