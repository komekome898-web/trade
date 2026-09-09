#!/usr/bin/env python3
"""BitMEX の公開アーカイブを、取引所が閉じる前に**生のまま**丸ごと保全する。

**期限【事実 2026-09-09、一次情報】**: BitMEX 自身の告知
(`GET https://www.bitmex.com/api/v1/announcement`)に、**2026-09-16 12:00 UTC** に
XBTUSD 等を上場廃止・清算、**2026-09-23** に**取引所そのものを閉鎖**とある。
アーカイブ(`public.bitmex.com`)は 2014-11-22 〜 2025-02-22 で既に更新が止まっているが、
**閉鎖後も置かれ続ける保証はどこにも無い。**

**方針(オーナー決定 2026-09-09)**: 「データは最重要で、今必要でなくてもいずれ必要に
なるかもしれず、その時に取得できなくなっていてはいけない。**取れる時に取れるだけ取る**」。
したがって**変換も間引きもせず、配布されているファイルをそのまま**置く。
解釈は後からいくらでもやり直せるが、消えたデータは戻らない。

実測した中身(2026-09-09):

| 系統 | ファイル | 容量 | 中身 |
|---|---|---|---|
| `data/trade/` | 3,746 | **47.9 GB** | 約定 1 件ごと(全銘柄・全期間) |
| `data/quote/` | 3,746 | **197.8 GB** | 板の最良気配の更新 1 件ごと |
| `data/porl/`  | 1,532 | **85.9 GB** | 資産・負債の証明(準備金証明)。**相場データではない** |

既定は **trade + quote = 245.7 GB**。`porl` は取引所の財務証明で研究に使わないので
既定では取らない(`--include-porl` で取れる)。

安全側の性質:
- **追記のみ・冪等**。既にあるファイルはサイズを照合して飛ばす。何度実行してもよい。
- **途中で止めてよい**。`.part` に書いて完了時に改名するので、中途半端なファイルが残らない。
- **空きが減ったら自分で止まる**(既定 20 GB を切ったら中断)。
- **状態を毎回ファイルに書く** → `paper_logs/bitmex_mirror_status.json` は共有されるので、
  リードは**オーナーに聞かずに進捗を読める**。

Usage(Windows は deploy\\mirror_bitmex.bat をダブルクリックするだけ):
    python scripts/mirror_bitmex_archive.py
    python scripts/mirror_bitmex_archive.py --only trade      # 約定だけ先に
    python scripts/mirror_bitmex_archive.py --include-porl    # 準備金証明も
    python scripts/mirror_bitmex_archive.py --dry-run         # 何をどれだけ取るか見るだけ
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
BUCKET = "https://s3-eu-west-1.amazonaws.com/public.bitmex.com/"
UA = {"User-Agent": "bitflyer-bot research archive mirror"}
PREFIXES = {"trade": "data/trade/", "quote": "data/quote/", "porl": "data/porl/"}
DEFAULT_OUT = REPO / "data" / "archive" / "bitmex"
SHARED_STATUS = REPO / "paper_logs" / "bitmex_mirror_status.json"
MIN_FREE_GB = 20.0
CHUNK = 1 << 20

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

_ENTRY = re.compile(
    r"<Key>([^<]+)</Key>\s*<LastModified>[^<]+</LastModified>"
    r"\s*<ETag>[^<]*</ETag>\s*<Size>(\d+)</Size>")


def _log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}", flush=True)


def _gb(n: int | float) -> str:
    return f"{n / 1e9:.1f} GB"


def free_bytes(path: Path) -> int:
    """まだ存在しない保存先でも空きを測れるよう、存在する親まで遡る。"""
    p = path.resolve()
    while not p.exists() and p != p.parent:
        p = p.parent
    return shutil.disk_usage(p).free


def list_prefix(prefix: str) -> list[tuple[str, int]]:
    """S3 の一覧。(キー, サイズ)。サイズ 0 の擬似ディレクトリは落とす。"""
    out: list[tuple[str, int]] = []
    token = None
    while True:
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        r = requests.get(BUCKET, params=params, timeout=120, headers=UA)
        r.raise_for_status()
        out += [(k, int(s)) for k, s in _ENTRY.findall(r.text) if int(s) > 0]
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", r.text)
        if not m:
            return out
        token = m.group(1)


def download(key: str, size: int, dest: Path, retries: int = 5) -> bool:
    """1 ファイル。`.part` に落として完了時に改名する(中断が残らない)。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    backoff = 3.0
    for _ in range(retries):
        try:
            with requests.get(BUCKET + key, timeout=300, headers=UA, stream=True) as r:
                if r.status_code != 200:
                    _log(f"  HTTP {r.status_code} {key} — {backoff:.0f}s 後に再試行")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60.0)
                    continue
                with open(part, "wb") as fh:
                    for chunk in r.iter_content(CHUNK):
                        fh.write(chunk)
        except Exception as e:  # noqa: BLE001
            _log(f"  通信失敗 {type(e).__name__}: {str(e)[:80]} — {backoff:.0f}s 後に再試行")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
            continue
        got = part.stat().st_size
        if got != size:
            # サイズが合わないものは**残さない**。半端なファイルは、無いより悪い。
            _log(f"  サイズ不一致 {key}: {got} != {size} — 破棄して再試行")
            part.unlink(missing_ok=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
            continue
        part.replace(dest)
        return True
    return False


def write_status(out_dir: Path, status: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(status, ensure_ascii=False, indent=2)
    (out_dir / "STATUS.json").write_text(text, encoding="utf-8")
    try:
        SHARED_STATUS.parent.mkdir(parents=True, exist_ok=True)
        SHARED_STATUS.write_text(text, encoding="utf-8")   # 共有されるので聞かずに読める
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--only", action="append", choices=sorted(PREFIXES),
                    help="この系統だけ(複数可)。既定は trade と quote")
    ap.add_argument("--include-porl", action="store_true",
                    help="準備金証明(85.9 GB)も取る。相場データではない")
    ap.add_argument("--min-free-gb", type=float, default=MIN_FREE_GB,
                    help="空きがこれを切ったら中断する(既定 20 GB)")
    ap.add_argument("--dry-run", action="store_true", help="何をどれだけ取るか見るだけ")
    ap.add_argument("--max-files", type=int, default=None,
                    help="この本数で止める。**まず少しだけ試す**ときに使う(既定: 全部)")
    args = ap.parse_args()

    if args.only:
        wanted = list(dict.fromkeys(args.only))
    else:
        wanted = ["trade", "quote"] + (["porl"] if args.include_porl else [])

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)     # 空きの計測より先に用意する
    _log(f"保存先: {out_dir}")
    _log(f"対象: {wanted}")

    todo: list[tuple[str, int, Path]] = []
    have_bytes = 0
    plan = {}
    for name in wanted:
        keys = list_prefix(PREFIXES[name])
        missing = []
        for key, size in keys:
            dest = out_dir / key
            if dest.exists() and dest.stat().st_size == size:
                have_bytes += size
                continue
            missing.append((key, size, dest))
        plan[name] = {"files": len(keys), "bytes": sum(s for _, s in keys),
                      "missing_files": len(missing),
                      "missing_bytes": sum(s for _, s, _ in missing)}
        todo += missing
        _log(f"  {name:6s} {len(keys):5d} ファイル {_gb(plan[name]['bytes']):>10s}"
             f"  / 未取得 {len(missing):5d} {_gb(plan[name]['missing_bytes']):>10s}")

    if args.max_files is not None:
        todo = todo[:args.max_files]
        _log(f"--max-files {args.max_files}: 今回は {len(todo)} 本だけ取る")

    need = sum(s for _, s, _ in todo)
    free = free_bytes(out_dir)
    _log(f"必要 {_gb(need)} / 空き {_gb(free)}")
    if args.dry_run:
        return 0
    if not todo:
        _log("すべて取得済み。")
        write_status(out_dir, {"finished_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"), "plan": plan, "remaining_files": 0})
        return 0
    if free < need + args.min_free_gb * 1e9:
        _log(f"**空きが足りません**: 必要 {_gb(need)} + 余裕 {args.min_free_gb:.0f} GB "
             f"> 空き {_gb(free)}。--only trade で分けるか、空きを作ってください。")
        return 2

    started = time.time()
    done_files = 0
    done_bytes = 0
    failed: list[str] = []
    try:
        for i, (key, size, dest) in enumerate(todo, 1):
            if free_bytes(out_dir) < args.min_free_gb * 1e9:
                _log(f"**空きが {args.min_free_gb:.0f} GB を切ったので中断**。"
                     "空けてから再実行すれば続きから進みます。")
                break
            if download(key, size, dest):
                done_files += 1
                done_bytes += size
            else:
                failed.append(key)
                _log(f"  **取得失敗**: {key}(あとで再実行すれば再挑戦します)")
            if i % 25 == 0 or i == len(todo):
                elapsed = time.time() - started
                rate = done_bytes / elapsed if elapsed > 0 else 0
                left = need - done_bytes
                eta = left / rate / 3600 if rate > 0 else float("nan")
                _log(f"  {i}/{len(todo)}  {_gb(done_bytes)} 取得  "
                     f"{rate / 1e6:.1f} MB/s  残り {_gb(left)}  あと約 {eta:.1f} 時間")
                write_status(out_dir, {
                    "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "plan": plan, "downloaded_files": done_files,
                    "downloaded_bytes": done_bytes,
                    "remaining_files": len(todo) - i,
                    "remaining_bytes": need - done_bytes,
                    "rate_mb_s": round(rate / 1e6, 2),
                    "failed": failed[:50],
                    "free_bytes": free_bytes(out_dir),
                })
    except KeyboardInterrupt:
        _log("中断(Ctrl+C)。再実行すれば続きから進みます。")

    write_status(out_dir, {
        "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan": plan, "downloaded_files": done_files, "downloaded_bytes": done_bytes,
        "remaining_files": len(todo) - done_files - len(failed),
        "failed": failed[:50],
        "free_bytes": free_bytes(out_dir),
        "note": "STATUS.json is the truth about what is on disk. A key listed in "
                "failed was attempted and did not complete; re-running retries it. "
                "A key in neither the directory nor failed was never attempted.",
    })
    _log(f"今回 {done_files} ファイル / {_gb(done_bytes)} 取得。失敗 {len(failed)}。")
    if failed or done_files + len(failed) < len(todo):
        _log("**未完了があります。もう一度同じコマンドを実行すれば続きから進みます。**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
