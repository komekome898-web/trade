"""K1 段階 G(2026-10-01、委任文 docs/DATA/delegations/20261001_k1_stage_g.md)のデータの門。

仕組みは scripts/k1_newenv_fix_datagate.py と同じ(Python の audit hook で、データの置き場
backtest_data / data / paper_logs の下の open() を、許可の一覧に無いものはすべて拒む。拒んだ
open は PermissionError を投げ、$K1G_DATAGATE_LOG に 1 行ずつ書く)。許可の一覧だけがこの委任用:

  - Binance BTCUSDT 現物 1 分足 2017〜2023 の 7 ファイル(binance_BTCUSDT_1m_20170801_20231231/)
  - bitFlyer FX_BTC_JPY 1 分足 2017〜2023 の 7 ファイル(bitflyer_lightchart_FX_BTC_JPY_1m_20260906/)
  - Bybit BTCUSDT 無期限 1 分足 2022〜2023 の 2 ファイル(bybit_BTCUSDT_1m_20260910/。2026-10-01 時点で
    ディスクに無い。ENV_DEFECTS.md G-5)
  - 封印の台帳 backtest_data/phase2_sealed/(データ層が読むたびに読む。市場データではない)
  - 段階 A の畳んだ足 backtest_data/k1_newenv_a_20260927/
  - この委任で畳んだ足 backtest_data/k1_newenv_g_20261001/(上の許可したファイルから、
    2023-12-18T00:00Z より前の行だけで作ったもの)

2023 のファイルには 2023-12-18 以降の行も入っている。ファイルを開くこと自体はここで許し、行の範囲は
データ層の range_ns(終わり = 2023-12-18T00:00Z)と、畳みのスクリプトの自前の確認で切る。

使い方(スクリプト): 最初に import k1_newenv_g_datagate(import の時点で hook が入る)。
使い方(試験): PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<file> python -m pytest ... -p k1_newenv_g_datagate
"""
import os
import sys

REPO = os.path.realpath(os.environ.get("K1G_REPO", "/home/user/trade"))
ROOTS = tuple(os.path.join(REPO, r) + os.sep for r in ("backtest_data", "data", "paper_logs"))
ALLOW_DIRS = tuple(os.path.join(REPO, r) + os.sep for r in (
    "backtest_data/phase2_sealed", "backtest_data/k1_newenv_a_20260927", "backtest_data/k1_newenv_g_20261001"))
ALLOW_FILES = frozenset(
    [os.path.join(REPO, f"backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_{y}.csv.gz")
     for y in range(2017, 2024)]
    + [os.path.join(REPO, f"backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_{y}.csv.gz")
       for y in range(2017, 2024)]
    + [os.path.join(REPO, f"backtest_data/bybit_BTCUSDT_1m_20260910/bybit_BTCUSDT_1m_{y}.csv.gz")
       for y in (2022, 2023)])
LOG = os.environ.get("K1G_DATAGATE_LOG")
OPENED = []  # 許した open の実パス(DATA_READ.md の材料)
_busy = [False]


def _hook(event, args):
    if event != "open" or _busy[0]:
        return
    path = args[0]
    if isinstance(path, int) or path is None:
        return
    try:
        p = os.fsdecode(path)
    except Exception:
        return
    _busy[0] = True
    try:
        real = os.path.realpath(p)
    finally:
        _busy[0] = False
    if not real.startswith(ROOTS):
        return
    if real.startswith(ALLOW_DIRS) or real in ALLOW_FILES:
        if real not in OPENED:
            OPENED.append(real)
        return
    if LOG:
        _busy[0] = True
        try:
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write(real + "\n")
        finally:
            _busy[0] = False
    raise PermissionError(f"k1g datagate: {real} is outside the data the delegation allows")


sys.addaudithook(_hook)


def pytest_configure(config):  # noqa: D401 - pytest plugin entry (the hook is installed at import)
    pass
