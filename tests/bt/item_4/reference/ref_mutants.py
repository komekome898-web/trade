"""Mutation check for the item-4 reference: each mutant plants one rule
error in src/bot/bt/reference/, runs tests/bt/item_4/reference/, and
restores the file. Every mutant must be killed (a test fails).
Not collected by pytest. Run from the repository root:
    python3 tests/bt/item_4/reference/ref_mutants.py
"""
import subprocess, shutil, sys, tempfile
# run from the repository root: python3 tests/bt/item_4/reference/ref_mutants.py
E = "src/bot/bt/reference/event_sim.py"; R = "tests/bt/item_4/reference/ext_bar_modes.py"
N = "src/bot/bt/reference/bar_sim.py"  # the rule-text bar reference
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
 (N, 'if pos is None and ((d == 1 and l < p) or (d == -1 and h > p)):', 'if pos is None and ((d == 1 and l <= p) or (d == -1 and h >= p)):'),
 (N, 'if (d == 1 and h > p) or (d == -1 and l < p):', 'if (d == 1 and h >= p) or (d == -1 and l <= p):'),
 (N, 'elif o["max_hold_bars"] is not None and j == pos.entry_bar + o["max_hold_bars"]:', 'elif o["max_hold_bars"] is not None and j == pos.entry_bar + o["max_hold_bars"] + 1:'),
 (N, 'close_pos(j, taker_px(o_, buy), "taker", "max_hold")     # (2) R-H1/R-H2\n                pending_sig = None', 'close_pos(j, taker_px(o_, buy), "taker", "max_hold")     # (2) R-H1/R-H2'),
 (N, 'pos.carry += abs(pos.size) * B[j - 1][3] * carry_rate', 'pos.carry += abs(pos.size) * B[j][3] * carry_rate'),
 (N, 'adj = (o["spread_pct"] / 2 + o["slippage_pct"]) / HUNDRED', 'adj = (o["spread_pct"] + o["slippage_pct"]) / HUNDRED'),
 (N, 'size = o["order_amount"] / price                             # R-A1', 'size = o["order_amount"] / B[j][0]'),
 (N, '(d == 1 and h > pos.tp_level)', '(d == 1 and h >= pos.tp_level)'),
 (N, 'base = min(o_, pos.stop_level) if d == 1 else max(o_, pos.stop_level)', 'base = pos.stop_level'),
 (N, 'hit = (pos.tp_level, "maker", "take_profit")', 'hit = (pos.tp_level, "taker", "take_profit")'),
 (N, '# R-M3\n                        run.missed_fills += 1', '# R-M3\n                        pass'),
 (N, 'if entry_lim is None:\n', 'if entry_lim is None or entry_lim["dir"] == d:\n'),
 (N, 'if entry_allowed(d, j):', 'if entry_allowed(d, j) or True:'),
 (N, 'window = B[lo:j]', 'window = B[lo:j + 1]'),
 (N, 'if pos is not None and j > pos.entry_bar:\n            d = pos.direction', 'if pos is not None and j >= pos.entry_bar:\n            d = pos.direction'),
 (N, 'return Fraction(repr(x))', 'return Fraction(x)'),
 (N, '- f - t.entry_fee - t.carry  # R-A3', '- f - t.entry_fee  # R-A3'),
 (N, 'not o["entry_mask"][sig_bar]', 'not o["entry_mask"][min(sig_bar + 1, n - 1)]'),
 (N, 'if wick_exit_next:                                           # (1) R-W3', 'if False:'),
 (N, 'if pos is not None and pos.wick_level is not None:\n            wl = pos.wick_level\n            if (pos.direction == 1 and c < wl)', 'if pos is not None and pos.wick_level is not None:\n            wl = pos.wick_level\n            if (pos.direction == 1 and l < wl)'),
 (N, 'if exit_lim is not None and j == exit_lim["placed"] + T:\n            exit_lim = None\n            run.missed_fills += 1', 'if exit_lim is not None and j == exit_lim["placed"] + T:\n            exit_lim = None'),
 (N, 'exit_lim = None     # a waiting exit limit is dropped, not counted (R-M5)', 'run.missed_fills += exit_lim is not None\n        exit_lim = None'),
 (N, 'eq += (c - pos.entry_price) * pos.size * pos.direction - pos.entry_fee - pos.carry', 'eq += (c - pos.entry_price) * pos.size * pos.direction - pos.entry_fee'),
 (N, 'if o["entry_sides"] == "long" and direction == -1:', 'if False:'),
 (N, 'elif pending_sig is not None and closes(pending_sig[0], pos):', 'elif False:'),
 (N, 'if o["stop_loss_pct"] is not None:\n            raise RefusedConfig("R-W4', 'if False:\n            raise RefusedConfig("R-W4'),
]
killed = 0
for i, (f, a, b) in enumerate(M):
    src = open(f).read()
    assert src.count(a) == 1, (i, a)
    open(f, "w").write(src.replace(a, b))
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-x", "-p", "no:cacheprovider", "-o", "tmp_path_retention_policy=none",
                            "--basetemp", tempfile.mkdtemp(prefix="ref_mut_"), "tests/bt/item_4/reference/"],
                           env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=300)
        tail = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-200:]
        k = p.returncode != 0
        killed += k
        print(f"m{i:02d} {'KILLED' if k else 'SURVIVED'} {f.split('/')[-1]}: {b[:60]!r} :: {tail}")
    finally:
        open(f, "w").write(src)
print(f"killed {killed}/{len(M)}")
sys.exit(0 if killed == len(M) else 1)
