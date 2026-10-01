#!/usr/bin/env python3
"""K1 段階 G: 封印の境(P2-08 seal_from_ts = 2023-12-18T00:00Z)が機械で守られるかを確かめ、自前でも確かめる。
データの門の下で回す。結果は標準出力(DATA_READ.md に写す)。

  1. データ層: 2023 のファイル(Binance・bitFlyer)を range 無し / 終わりが境 + 1 分 で読む → SealedRangeError を期待
  2. 記録の口(runner.plan_run): 生の 2023 のファイルを入力に渡す → ReproError(SealedRangeError)を期待
  3. 畳んだ足(backtest_data/k1_newenv_g_20261001/*.csv.gz)を全部データ層で読み、最後の足の終わり <= 境を自前で確かめる
     (畳んだ足は封印の台帳に無い別のファイルなので、データ層は封印として扱わない = G-3)
"""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k1_newenv_g_datagate  # noqa: E402,F401

from bot.bt.data import SealedRangeError, load  # noqa: E402
from bot.bt.repro.errors import ReproError  # noqa: E402
from bot.bt.repro.runner import DataInput, plan_run  # noqa: E402
from k1_newenv_g_fold import BF_SPEC, BIN_SPEC, CUT, NS, iso  # noqa: E402
from k1_newenv_g_run import spec  # noqa: E402
from bot.strategy.k1_xvenue import K1XSetup  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RAW = {"binance_2023": ("backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz", BIN_SPEC),
       "bitflyer_2023": ("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz", BF_SPEC)}
lo2023 = 1672531200 * NS
for name, (rel, sp) in RAW.items():
    for label, rng in (("range 無し", None), ("終わり = 境 + 1 分", [lo2023, CUT + 60 * NS])):
        ds = {"name": "d", "paths": [rel], "spec": sp}
        if rng:
            ds["range_ns"] = rng
        try:
            load(REPO, [ds])
            print(f"1 {name} {label}: 読めた(拒まれなかった)")
        except SealedRangeError as e:
            print(f"1 {name} {label}: SealedRangeError: {str(e)[:160]}")
    try:
        plan_run(root=REPO, data=[DataInput(rel, spec(1, "X"))], config={"instrument": "FX_BTC_JPY", "foot_min": 1,
                 "gate": {"s": "19", "b": "24"}, "strength": "weak", "mode": "design", "fill": "last_bar_close",
                 "costs": {"maker_fee_rate": 0, "taker_fee_rate": 0, "source": "x"}}, seed=0, setup=K1XSetup(),
                 purpose="動作確認")
        print(f"2 {name} runner.plan_run: 通った(拒まれなかった)")
    except ReproError as e:
        print(f"2 {name} runner.plan_run: ReproError: {str(e)[:200]}")
bad = 0
for p in sorted(glob.glob(os.path.join(REPO, "backtest_data/k1_newenv_g_20261001/*.csv.gz"))):
    rel = os.path.relpath(p, REPO)
    foot = int(os.path.basename(p).split("_")[1].rstrip("m"))
    r = load(REPO, [{"name": "d", "paths": [rel], "spec": spec(foot, "X")}])
    recs = r.records("d")
    first, last = recs[0]["start_ns"], max(x["start_ns"] for x in recs)
    end = last + foot * 60 * NS
    ok = end <= CUT
    bad += not ok
    print(f"3 {rel}: rows {len(recs)} first {iso(first)} last {iso(last)} last_end {iso(end)} <= cut {ok} "
          f"sealed_unit {r.files()[0].sealed_unit}")
print(f"3 files over the cut: {bad}")
