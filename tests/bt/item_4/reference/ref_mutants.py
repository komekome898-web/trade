"""Mutation check for the item-4 reference: each mutant plants one rule
error in src/bot/bt/reference/, runs tests/bt/item_4/reference/, and
restores the file. Every mutant must be killed (a test fails).
Not collected by pytest. Run from the repository root:
    python3 tests/bt/item_4/reference/ref_mutants.py
"""
import subprocess, shutil, sys
# run from the repository root: python3 tests/bt/item_4/reference/ref_mutants.py
E = "src/bot/bt/reference/event_sim.py"; R = "src/bot/bt/reference/bar_sim.py"
M = [
 (E, 'return px < o.price or (limit_cross == "touch" and px == o.price)', 'return px <= o.price'),
 (E, 'apply_fill(t, o, o.price, take, "maker")', 'apply_fill(t, o, px, take, "maker")'),
 (E, '_R_EXCH, _R_ARRIVE, _R_DELIVER = 0, 1, 2', '_R_EXCH, _R_ARRIVE, _R_DELIVER = 1, 0, 2'),
 (E, 'pay = -res.position * mark * e.rate', 'pay = res.position * mark * e.rate'),
 (E, '* (1 if pos > 0 else -1)', '* 1'),
 (E, 't_recv=t_exch + lat_n', 't_recv=t_exch'),
 (E, 'lims.sort(key=lambda o: ((-o.price if o.side == "buy" else o.price), o.arrive_no))', 'lims.sort(key=lambda o: o.arrive_no)'),
 (E, 'state["consumed"][(o.side, p)] = state["consumed"].get((o.side, p), Fraction(0)) + take', 'pass'),
 (R, 'if stop_hit:', 'if stop_hit and not tp_hit:'),
 (R, 'pos = open_trade(sig, i_sig, j, b.open, "taker")', 'pos = open_trade(sig, i_sig, j, bars[j - 1].close, "taker")'),
 (R, 'j == pos.entry_bar + max_hold_bars', 'j == pos.entry_bar + max_hold_bars + 1'),
 (R, 'pos = open_trade(sig, i_sig, j, lim, "maker")', 'pos = open_trade(sig, i_sig, j, (min(lim, b.open) if sig.side == "long" else max(lim, b.open)), "maker")'),
 (R, 'pending = {"sig": sig, "signal_bar": j, "first": j + 1, "last": last}', 'pending = {"sig": sig, "signal_bar": j, "first": j + 1, "last": last - 1}'),
 (R, 'close(pos, j, pos.tp, tp_fee, "take_profit")', 'close(pos, j, pos.tp, "taker", "take_profit")'),
]
killed = 0
for i, (f, a, b) in enumerate(M):
    src = open(f).read()
    assert src.count(a) == 1, (i, a)
    open(f, "w").write(src.replace(a, b))
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-x", "-p", "no:cacheprovider", "tests/bt/item_4/reference/"],
                           env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=300)
        tail = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-200:]
        k = p.returncode != 0
        killed += k
        print(f"m{i:02d} {'KILLED' if k else 'SURVIVED'} {f.split('/')[-1]}: {b[:60]!r} :: {tail}")
    finally:
        open(f, "w").write(src)
print(f"killed {killed}/{len(M)}")
sys.exit(0 if killed == len(M) else 1)
