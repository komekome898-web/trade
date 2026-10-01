"""K1 段階 G を閉じる委任 §2-5(G-6): データ層の load の費用を Binance 2018 の 1 ファイル(521,624 行)で測る。
データの門(k1_newenv_g_datagate)の下で回す。
  python3 scripts/k1_newenv_g_loadprof.py prof   cProfile(tottime 順の上位 30)
  python3 scripts/k1_newenv_g_loadprof.py time   load の壁時計・行数・異常・事象の列の sha256・最大 RSS(1 行の JSON)
"""
import cProfile, pstats, sys, time, io, os, json, resource
sys.path.insert(0, "/home/user/trade/scripts"); sys.path.insert(0, "/home/user/trade/src")
import k1_newenv_g_datagate  # noqa
from bot.bt.data import load
REPO = "/home/user/trade"
SPEC = {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar", "symbol": "BTCUSDT",
        "asset": "crypto", "time": {"columns": ["open_time"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
        "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start",
        "synthetic": {"column": "n_trades", "values": ["0"]}}
DS = [{"name": "d", "paths": ["backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2018.csv.gz"],
       "spec": SPEC, "range_ns": [1514764800 * 10**9, 1546300800 * 10**9]}]
mode = sys.argv[1]
if mode == "prof":
    pr = cProfile.Profile(); pr.enable(); r = load(REPO, DS); pr.disable()
    s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(30); print(s.getvalue()[:8000])
else:
    t0 = time.perf_counter(); r = load(REPO, DS); dt = time.perf_counter() - t0
    from collections import Counter
    an = Counter(a["kind"] for a in r.anomalies("d"))
    ev = r.events("d", {k: {"synthetic": "drop", "gap": "accept", "off_grid": "accept"}[k] for k in an})
    import hashlib
    h = hashlib.sha256(repr([e.to_dict() for e in ev]).encode()).hexdigest()
    print(json.dumps({"load_s": round(dt, 2), "rows": r.files()[0].rows_read, "kept": r.files()[0].rows_kept,
                      "anomalies": dict(an), "events": len(ev), "events_sha256": h,
                      "us_per_row": round(dt / r.files()[0].rows_read * 1e6, 1),
                      "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}))
