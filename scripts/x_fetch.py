#!/usr/bin/env python3
"""X(旧 Twitter)の公開投稿を fxtwitter の公開 API で取り、1 行 1 投稿の JSON にする。

経路の選定と実測は `.claude/skills/x-research/SKILL.md`(2026-09-19、L-219)。鍵は要らない。
返信先(`replying_to_status`)があれば根まで上へ辿る(`--no-walk` で止める)。1 件ごとに 1 秒待つ。
出力の各行: url / id / author / created_at / text / likes / retweets / replies / views /
quote(id, author, text の先頭 200 字)/ replying_to_status / http / fetched_at。
取れなかった行も **http と error を付けて出す**(「取れない」の記録を残すため)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.fxtwitter.com"
UA = "trade-research/1.0 (research use)"
PAUSE_S = 1.0
_ID_RE = re.compile(r"(?:status/)?(\d{8,})")


def parse_id(s: str) -> str | None:
    m = _ID_RE.search(s)
    return m.group(1) if m else None


def fetch_status(tweet_id: str, timeout: float = 20.0) -> tuple[int, dict | None, str | None]:
    req = urllib.request.Request(f"{BASE}/i/status/{tweet_id}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return e.code, None, f"HTTP {e.code}"
    except Exception as e:  # ネットワーク・JSON
        return 0, None, f"{type(e).__name__}: {e}"[:120]


def normalize(tweet_id: str, http: int, data: dict | None, err: str | None) -> dict:
    row = {"id": tweet_id, "http": http, "fetched_at": datetime.now(timezone.utc).isoformat()}
    if not data or "tweet" not in data:
        row["error"] = err or "no tweet object"
        return row
    t = data["tweet"]
    q = t.get("quote") or {}
    row.update({
        "url": t.get("url"),
        "author": (t.get("author") or {}).get("screen_name"),
        "created_at": t.get("created_at"),
        "text": t.get("text"),
        "likes": t.get("likes"), "retweets": t.get("retweets"),
        "replies": t.get("replies"), "views": t.get("views"),
        "quote": {"id": q.get("id"), "author": (q.get("author") or {}).get("screen_name"),
                  "text": (q.get("text") or "")[:200]} if q else None,
        "replying_to_status": t.get("replying_to_status"),
    })
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+", help="投稿の URL か ID")
    ap.add_argument("--no-walk", action="store_true", help="返信先を上へ辿らない")
    ap.add_argument("--max-walk", type=int, default=30)
    a = ap.parse_args()

    seen: set[str] = set()
    queue = [parse_id(x) for x in a.targets]
    bad = [x for x, i in zip(a.targets, queue) if i is None]
    for x in bad:
        print(json.dumps({"target": x, "http": 0, "error": "ID が取れない"}, ensure_ascii=False))
    queue = [i for i in queue if i]
    n_walk = 0
    while queue:
        tid = queue.pop(0)
        if tid in seen:
            continue
        seen.add(tid)
        http, data, err = fetch_status(tid)
        row = normalize(tid, http, data, err)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        parent = row.get("replying_to_status")
        if parent and not a.no_walk and n_walk < a.max_walk:
            queue.append(str(parent)); n_walk += 1
        if queue:
            time.sleep(PAUSE_S)
    return 0


if __name__ == "__main__":
    sys.exit(main())
