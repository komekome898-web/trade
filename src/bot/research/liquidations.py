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

**2026-09-13 修正(`docs/DATA/probes/20260913_liquidation_integrity.md` §5)**:
上記の「素直な読み方」の弱点が、この読み手自身の旧実装にも残っていた。
1 メンバ目の途中で `zlib.error`(`invalid block type` 等)が起きると、
その decompress 呼び出しが**例外を投げる前に解けていたバイトごと**失われ、
`read_rows` は**エラーを出さず 0 行を返して**いた(実測)。0 行は「イベントが
無かった」と区別が付かないため、清算のある/無しを比べる研究の対照群が
気付かれずに汚染されうる。

直し方は回収ツール(`bot.research.gz_members`)と同じ: **展開する前に**、
生バイト列を gzip メンバの境界(magic bytes)で切ってから、メンバごとに
個別の展開器へ渡す。これで「あるメンバの壊れた末尾に次のメンバのヘッダが
直結している」形の破損でも、decompress 1 回の呼び出しに 2 つのメンバの
バイトが混ざらない。そのうえで:
- `read_rows` は既定 (`strict=True`) で、破損を検知したら
  `LiquidationFileCorrupted` を送出する(黙って部分結果や 0 行を返さない)。
- 呼び出し側が明示的に `strict=False` を渡したときだけ、読めたところまでの
  行を `ReadResult(truncated=True, error=...)` として返す。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from bot.research.gz_members import decompress_piece, split_raw_members


class LiquidationFileCorrupted(RuntimeError):
    """`read_rows(path)`(既定 `strict=True`)が gzip 破損を検知したときに送出する。

    黙って 0 行・部分結果を返さないためのもの。原因調査や回収
    (`scripts/repair_liquidation_gz.py`)のあとで読み直すか、
    診断目的でどうしても部分結果が要るときだけ `strict=False` を渡す。
    """


@dataclass
class _Decoded:
    text: str
    members_found: int
    members_complete: int
    error: str | None                  # None なら破損なし(境界も中身も正常)


def _decode_all_members(data: bytes) -> _Decoded:
    """生バイト列をメンバ境界で先に切ってから、メンバごとに展開する。

    `bot.research.gz_members`(回収ツールと共通)を使う — 展開前に境界を
    切るので、あるメンバの decompress 呼び出しが次のメンバのヘッダバイトを
    誤って読み込んで丸ごと例外になる、という旧実装の弱点が起きない。
    """
    pieces = split_raw_members(data)
    out = bytearray()
    members_complete = 0
    error: str | None = None
    n = len(pieces)
    for i, piece in enumerate(pieces):
        member = decompress_piece(piece)
        out += member.decompressed
        if member.complete:
            members_complete += 1
        elif member.error is not None:
            # decode 自体が失敗 = 正真正銘の破損(境界の問題ではない)
            if error is None:
                error = member.error
        elif i != n - 1:
            # 最後以外のメンバが終端マーカーに達しないまま終わった
            # = 記録中の開きっぱなし(それは常に「最後の」メンバのはず)ではあり得ない
            #   境界破損の疑い(例: 旧クラッシュで次のメンバのヘッダが直結した)
            if error is None:
                error = f"gzip メンバ {i + 1}/{n} が終端マーカー前に終わっている(境界破損の疑い)"
    return _Decoded(text=out.decode("utf-8", errors="replace"),
                     members_found=n, members_complete=members_complete, error=error)


def read_text(path: str | Path) -> str:
    """gzip を、途中で切れていても読めるところまで展開する。

    `gzip.open` と違い、終端マーカーが無くても**そこまでの中身を返す**。
    複数メンバ(再接続で開き直した場合)にも対応する。破損の有無を
    プログラムで判定したい場合は `read_rows` を使うこと(この関数は文字列
    しか返さないので、破損か本当に空かを呼び出し側は区別できない)。
    """
    data = Path(path).read_bytes()
    return _decode_all_members(data).text


@dataclass
class ReadResult:
    rows: list[dict]
    bad_lines: int = 0                 # 途中の壊れた行(0 が期待値)
    truncated_tail: bool = False       # 最後の 1 行が書きかけだった(記録中 = 正常)
    truncated: bool = False            # gzip 破損で読み切れなかった(異常)
    error: str | None = None           # 破損の詳細(truncated=True のときのみ)
    members_found: int = 0             # 見つかった gzip メンバ数
    members_complete: int = 0          # うち終端マーカーまで読めたメンバ数


def read_rows(path: str | Path, *, strict: bool = True) -> ReadResult:
    """1 行 1 メッセージを読む。末尾の書きかけ行は落とし、その事実を残す。

    `strict=True`(既定・安全側): gzip 破損を検知したら
    `LiquidationFileCorrupted` を送出する。**0 行だから空だった、とは限らない
    ので、既定では呼び出し側に破損を握り潰させない。**
    `strict=False`: 例外を上げず、読めたところまでの行を
    `ReadResult(truncated=True, error=...)` として返す(診断・回収目的)。
    """
    path = Path(path)
    decoded = _decode_all_members(path.read_bytes())
    lines = [ln for ln in decoded.text.split("\n") if ln.strip()]
    rows: list[dict] = []
    bad = 0
    truncated_tail = False
    for i, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except ValueError:
            if i == len(lines) - 1:
                truncated_tail = True  # 書き込み途中 = 正常
            else:
                bad += 1               # 途中が壊れている = 異常

    truncated = decoded.error is not None
    if truncated and strict:
        raise LiquidationFileCorrupted(
            f"{path}: gzip 破損を検知({decoded.error})。"
            f"strict=False を渡せば読めた {len(rows)} 行を取得できる")
    return ReadResult(rows=rows, bad_lines=bad, truncated_tail=truncated_tail,
                       truncated=truncated, error=decoded.error,
                       members_found=decoded.members_found,
                       members_complete=decoded.members_complete)


def iter_rows(paths, *, strict: bool = True) -> Iterator[dict]:
    for p in paths:
        yield from read_rows(p, strict=strict).rows


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
    truncated: bool = False            # gzip 破損で読み切れなかった(異常)
    error: str | None = None           # 破損の詳細(truncated=True のときのみ)
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

    点検が目的なので `read_rows` は `strict=False` で呼ぶ(破損があっても
    例外にせず、`truncated`/`error` として結果に載せる — 点検ツール自身が
    落ちては本末転倒)。
    """
    path = Path(path)
    res = read_rows(path, strict=False)
    venue = None
    stem = path.name.split(".")[0]
    if "_" in stem:
        venue = stem.rsplit("_", 1)[0]

    out = FileSummary(path=str(path), venue=venue, rows=len(res.rows),
                      bad_lines=res.bad_lines, truncated_tail=res.truncated_tail,
                      truncated=res.truncated, error=res.error)
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
