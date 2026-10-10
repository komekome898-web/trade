#!/usr/bin/env python3
"""PC の常駐の記録器の見張り(オーナー PC で fetch_all.bat から毎回走る)。

オーナーの逐語(2026-10-11):
- L-984「**なんのために収集してんねん**」
- L-988「**穴あるけどほっときますなんか通じるわけないやろ**」(リードが「記録が止まったことは見つけられるが PC 側は直せない」と書いた穴への指摘)

経緯: venues の記録器(scripts/record_venues.py)が 2026-10-05 で書くのを止めたまま、4 日以上だれも気づかなかった。
start_all.bat は「プロセスが居なければ起こす」だけなので、プロセスは居るが書いていない(固まった)記録器は起こし直さない。

この台本がすること:
1. 記録器ごとに、出力の置き場で一番新しいファイルの更新時刻を見る。
2. 決めた時間より古ければ「固まった」とみなし、その記録器のプロセスを止め、start_all.bat で起こし直す
   (start_all.bat は居ない記録器だけを起こす)。
3. 結果を data/recorder_health.json に書き、各記録器のログの末尾 200 行を data/recorder_logs/<名前>.tail.log に写す
   (share_logs.bat が paper_logs/ へ写して共有する。研究側が原因を読めるように)。

「古い」の時間: 記録器ごとに、ふだん書く間隔より十分長く取った(下の表)。値の根拠は表の各行の注。

Usage(PC):
    .venv\\Scripts\\python.exe scripts\\data_repair\\watch_recorders.py           # 見て、固まったものを起こし直す
    .venv\\Scripts\\python.exe scripts\\data_repair\\watch_recorders.py --dry-run # 見るだけ
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# (名前, プロセスを見分ける文字, 出力の置き場, ファイルの型, 古いとみなす時間[時], ログ, 注)
RECORDERS = (
    ("venue-recorder", "record_venues.py", "data/venues", "*.csv.gz", 2, "logs/venues.out.log",
     "国内の他社の約定・気配。常に追記する(日のファイル)。2 時間書かなければ固まり"),
    ("ws-recorder", "record_realtime.py", "data/ws", "*.jsonl.gz", 2, "logs/recorder.out.log",
     "bitFlyer の WS。常に追記する"),
    ("liq-recorder", "record_liquidations.py", "data/liquidations", "*.jsonl.gz", 6, "logs/liquidations.out.log",
     "清算。静かな時間はメッセージが来ないので 6 時間"),
    ("hl-recorder", "record_hyperliquid.py", "data/hyperliquid", "*.csv.gz", 6, "logs/hyperliquid.out.log",
     "Hyperliquid。1 周に数分〜数時間かかる(start_all.bat の注)ので 6 時間"),
    ("okx-trader-recorder", "record_okx_traders.py", "data/okx_traders", "*.csv.gz", 4, "logs/okx_traders.out.log",
     "OKX の上位トレーダー。1 時間ごと(--loop 3600)なので 4 時間"),
)


def newest(dirpath: Path, pattern: str) -> tuple[str, float | None]:
    files = list(dirpath.glob(pattern)) if dirpath.exists() else []
    if not files:
        return "", None
    p = max(files, key=lambda f: f.stat().st_mtime)
    return p.name, p.stat().st_mtime


def stale(age_h: float | None, limit_h: float) -> bool:
    return age_h is None or age_h > limit_h


def kill_matching(match: str) -> str:
    """Windows: コマンド行に match を含む python のプロセスを止める。"""
    ps = ("$m = Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
          f"Where-Object {{ $_.CommandLine -like '*{match}*' }}; "
          "foreach ($p in $m) { Stop-Process -Id $p.ProcessId -Force; Write-Output $p.ProcessId }")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60)
    return (r.stdout or "").strip().replace("\n", ",")


def tail(path: Path, n: int = 200) -> str:
    if not path.exists():
        return ""
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - 200_000))
        data = fh.read().decode("utf-8", errors="replace")
    return "\n".join(data.splitlines()[-n:]) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    now = time.time()
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "recorders": []}
    restarted = []
    logdir = ROOT / "data" / "recorder_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    for name, match, out_dir, pattern, limit_h, log, note in RECORDERS:
        fname, mtime = newest(ROOT / out_dir, pattern)
        age_h = None if mtime is None else round((now - mtime) / 3600, 2)
        row = {"name": name, "newest_file": fname, "age_hours": age_h, "limit_hours": limit_h, "note": note,
               "action": "ok"}
        if stale(age_h, limit_h):
            if args.dry_run:
                row["action"] = "stale (dry-run, not restarted)"
            else:
                killed = kill_matching(match) if sys.platform.startswith("win") else ""
                row["action"] = f"stale -> killed [{killed}] and relaunched by start_all.bat"
                restarted.append(name)
        (logdir / f"{name}.tail.log").write_text(tail(ROOT / log), encoding="utf-8")
        report["recorders"].append(row)
    if restarted and not args.dry_run and sys.platform.startswith("win"):
        subprocess.run(["cmd", "/c", str(ROOT / "deploy" / "start_all.bat")], cwd=ROOT, timeout=300)
    report["restarted"] = restarted
    (ROOT / "data" / "recorder_health.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                                        encoding="utf-8")
    for r in report["recorders"]:
        print(f"[watch_recorders] {r['name']}: newest={r['newest_file']} age_h={r['age_hours']} -> {r['action']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
