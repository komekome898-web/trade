"""PC の常駐の 1 回目でページの上限(50 x 100)に当たった 3 人の、閉じた建玉の履歴を上限 500 で取り直す(一度だけ)。"""
import sys, json
sys.path.insert(0, '/home/user/trade/scripts')
from record_okx_traders import OkxTradersRecorder
OUT = '/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/okx_backfill/out'
CODES = ['1499200359BAE11A', '952071415C9BAD06', '08E31CADCFDDCFB8']
rec = OkxTradersRecorder(out_dir=OUT, max_pages=500)
sweep = rec._new_sweep_id()
for c in CODES:
    rec.counts = {}
    rec.record_trader(sweep, 'SWAP', c)
    rec.flush()
    print(c, json.dumps(rec.counts), flush=True)
