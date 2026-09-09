"""清算(強制決済)記録の読み出し。

**なぜ専用の読み手が要るか**: 記録器は常駐して `data/liquidations/<venue>_<日付>.jsonl.gz`
に**追記し続ける**。1 行ごとに `flush()` するので中身は取り出せるが、gzip の
**終端マーカーはファイルを閉じるまで書かれない**。したがって、走っている最中に
コピーされたファイル(= 共有されるファイルの大半)は `gzip.open(...).read()` が
`EOFError: Compressed file ended before the end-of-stream marker was reached` で
落ちる。**これは破損ではない。開いているだけである。**

さらに悪いことに、`gzip` の read は例外を投げるとき**それまでに解けたバイトを返さない**
ことがある。2026-09-09 に実際、11.6KB の BitMEX ファイルが「0 行」に見えた
(zlib で解き直したら 597 行あった)。**素直な読み方をすると、あるデータを無いと誤る。**

そこで:
- `read_lines()` は zlib で**メンバ単位に逐次展開**し、切れているところまでを返す。
- 最後の 1 行は**書きかけでありうる**ので、JSON にならない末尾行は静かに落とす
  (途中の行が壊れていたら、それは別の話なので `bad_lines` に数える)。

`summarise()` は「これは使えるデータか」を判定するためのもので、
**相場についての主張は一切しない** — 行数・期間・欠測・取引所ごとの内訳だけを返す。
"""
from __future__ import annotations

import json
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

GZIP_WBITS = zlib.MAX_WBITS | 16


def read_text(path: str | Path) -> str:
    """gzip を、途中で切れていても読めるところまで展開する。

    `gzip.open` と違い、終端マーカーが無くても**そこまでの中身を返す**。
    複数メンバ(再接続で開き直した場合)にも対応する。
    """
    data = Path(path).read_bytes()
    out = bytearray()
    pos = 0
    while pos < len(data):
        dec = zlib.decompressobj(GZIP_WBITS)
        try:
            out += dec.decompress(data[pos:])
            out += dec.flush()
        except zlib.error:
            break                      # このメンバは途中で切れている = ここまで
        if not dec.unused_data:
            break
        pos = len(data) - len(dec.unused_data)
    return out.decode("utf-8", errors="replace")


@dataclass
class ReadResult:
    rows: list[dict]
    bad_lines: int = 0                 # 途中の壊れた行(0 が期待値)
    truncated_tail: bool = False       # 最後の 1 行が書きかけだった


def read_rows(path: str | Path) -> ReadResult:
    """1 行 1 メッセージを読む。末尾の書きかけ行は落とし、その事実を残す。"""
    lines = [ln for ln in read_text(path).split("\n") if ln.strip()]
    rows: list[dict] = []
    bad = 0
    truncated = False
    for i, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except ValueError:
            if i == len(lines) - 1:
                truncated = True       # 書き込み途中 = 正常
            else:
                bad += 1               # 途中が壊れている = 異常
    return ReadResult(rows=rows, bad_lines=bad, truncated_tail=truncated)


def iter_rows(paths) -> Iterator[dict]:
    for p in paths:
        yield from read_rows(p).rows


# --------------------------------------------------------------------------- #
# 使えるデータかどうかの点検(相場についての判断は一切しない)
# --------------------------------------------------------------------------- #

@dataclass
class FileSummary:
    path: str
    venue: str | None
    rows: int
    bad_lines: int
    truncated_tail: bool
    first_us: int | None = None
    last_us: int | None = None
    backwards: int = 0                 # recv_us が巻き戻った回数
    duplicate_recv_us: int = 0         # 同一 recv_us の重複
    gaps: list[tuple[int, int]] = field(default_factory=list)   # (開始us, 秒)

    @property
    def span_utc(self) -> tuple[str, str] | None:
        if self.first_us is None:
            return None
        f = lambda u: datetime.fromtimestamp(  # noqa: E731
            u / 1e6, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return f(self.first_us), f(self.last_us)


def summarise(path: str | Path, gap_sec: float = 900.0) -> FileSummary:
    """1 ファイルを点検する。

    `gap_sec` 以上メッセージが来ていない区間を「欠測候補」として挙げる。
    **欠測候補は「記録が止まっていた」証拠ではない** — 静かな時間帯かもしれない。
    どちらかは記録器のログ(接続/切断)でしか決まらない。ここでは場所を示すだけ。
    """
    path = Path(path)
    res = read_rows(path)
    venue = None
    stem = path.name.split(".")[0]
    if "_" in stem:
        venue = stem.rsplit("_", 1)[0]

    out = FileSummary(path=str(path), venue=venue, rows=len(res.rows),
                      bad_lines=res.bad_lines, truncated_tail=res.truncated_tail)
    ts = [r["recv_us"] for r in res.rows if isinstance(r.get("recv_us"), int)]
    if not ts:
        return out
    out.first_us, out.last_us = min(ts), max(ts)
    out.backwards = sum(1 for a, b in zip(ts, ts[1:]) if b < a)
    out.duplicate_recv_us = len(ts) - len(set(ts))
    limit = gap_sec * 1_000_000
    out.gaps = [(a, round((b - a) / 1e6))
                for a, b in zip(ts, ts[1:]) if b - a >= limit]
    return out
