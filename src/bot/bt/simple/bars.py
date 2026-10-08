"""足の読み(SPEC.md §1): bitFlyer lightchart の 1 分足のファイルを読む。"""
from __future__ import annotations

import csv
import gzip
import os

from .common import SimpleRoadError, file_year, parse_ts

COLS = ("ts", "open", "high", "low", "close", "volume")


def read_bars(paths, seal_iso: str):
    """値段の空の足を飛ばし、封印の境以後に始まる足の行に届いたらそこで終わる(その行より先は読まない)。

    安値 > 高値の足と、始値か終値が安値〜高値の外にある足で止める。向きの決まらない足を飛ばすのは run(SPEC.md §1)。

    境の年より後の年のファイル(名前の `_YYYY.csv.gz`)は、どれも開く前に止める。
    足 = (始まりの時刻の文字列, 始値, 高値, 安値, 終値, 出来高)。
    """
    paths = [str(p) for p in paths]
    seal = parse_ts(seal_iso)
    for p in paths:
        y = file_year(p)
        if y is not None and y > seal.year:
            raise SimpleRoadError(f"封印の境 {seal_iso} の年より後の年のファイルは開かない: {os.path.basename(p)}")
    return _rows(paths, seal)


def _rows(paths, seal):
    for p in paths:
        with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            head = next(reader, None)
            if head is None or any(c not in head for c in COLS):
                raise SimpleRoadError(f"足のファイルの列が違う: {os.path.basename(p)}")
            ix = [head.index(c) for c in COLS]
            for row in reader:
                t = row[ix[0]]
                if parse_ts(t) >= seal:
                    return  # 封印の境の行 = データの終わり。この行より先は読まない
                vals = [row[i] for i in ix[1:5]]
                if all(v == "" for v in vals):
                    continue  # 値段の空の足(その分に約定が無かった)は無い足として飛ばす
                try:
                    o, h, lo, c = (float(v) for v in vals)
                    vol = float(row[ix[5]])
                except ValueError:
                    raise SimpleRoadError(f"足の行を数に直せない: {os.path.basename(p)} の {t}") from None
                if lo > h:
                    raise SimpleRoadError(f"足の安値が高値より高い: {os.path.basename(p)} の {t}")
                if not (lo <= o <= h and lo <= c <= h):
                    raise SimpleRoadError(f"足の始値か終値が安値〜高値の外: {os.path.basename(p)} の {t}")
                yield (t, o, h, lo, c, vol)
