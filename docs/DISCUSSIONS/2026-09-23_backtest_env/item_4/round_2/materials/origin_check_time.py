import os, tempfile, time, gzip
from bot.bt.pipeline import market_evidence, MARKET_ROOTS
d = tempfile.mkdtemp(); p = os.path.join(d, "x.csv.gz")
open(p, "wb").write(gzip.compress(b"timestamp,open\n", mtime=0))
import hashlib; h = hashlib.sha256(open(p, "rb").read()).hexdigest()
for k in range(3):
    t = time.perf_counter(); ev = market_evidence(os.path.realpath(p), h); print("market_evidence seconds:", round(time.perf_counter() - t, 3), ev)
n = sum(len(f) for r in MARKET_ROOTS for _, _, f in os.walk(r)); print("files listed:", n)
