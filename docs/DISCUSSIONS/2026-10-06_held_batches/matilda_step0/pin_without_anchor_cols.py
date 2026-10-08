"""直し B1 の H5 の確かめ: 直し A の試験 test_a2_record_unchanged_on_walk と同じ走らせ(合成の乱歩 2,000 本・σ 3,000・seed 0・
原典の値・self_trade = cancel_both)の 4 つの表の指紋を、注文の表の各行の終わりの 3 つの欄(anchored_to・anchor_offset・
anchor_px)を文字のまま落として取る。試験の PINNED と同じなら「足した 3 列のほかは記録が変わらない」。
使い方: PYTHONPATH=src python3 <このファイル>。tmp の根に書き、市場のデータは読まない。"""
import gzip
import hashlib
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, "tests/road")
import test_matilda_v37_r2_spec as R  # noqa: E402

from bot.bt.road.tables import SCHEMA  # noqa: E402

res = R.S.run(pathlib.Path(tempfile.mkdtemp()), R._walk(2000, 0, 3000), dict(R.M.V37_ORIGINAL),
              rules={"market_ref": "next_bar_open", "self_trade": "cancel_both"})
h = hashlib.sha256()
for name in ("signals", "orders", "fills", "trades"):
    with gzip.open(os.path.join(res["store"], SCHEMA["tables"][name]["file"]), "rb") as fh:
        data = fh.read()
    if name == "orders":
        text = data.decode("utf-8")
        assert text.endswith("\n")
        lines = text[:-1].split("\n")
        # 足した 3 列は終わりにあり、マチルダは段を使わないので全部の行で空(事前の批評 2 回目)
        assert lines[0].endswith(",anchored_to,anchor_offset,anchor_px"), lines[0][-80:]
        assert all(line.endswith(",,,") for line in lines[1:]), "段の列が空でない行がある"
        data = ("\n".join(line.rsplit(",", 3)[0] for line in lines) + "\n").encode("utf-8")
    h.update(data)
print(h.hexdigest(), "PINNED" if h.hexdigest() == R.PINNED else "違う")
