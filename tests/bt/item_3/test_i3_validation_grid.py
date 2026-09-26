"""Adversarial grids for the validation rules (item 3, old item 7), each
against an oracle written here from the rule's text, not from the
implementation's branches (委任文 §3「提出前の吟味」(6)).

Grids (sizes are asserted, so a shrunk grid fails):
  day start       zones x dates around every 2026 DST change of the zones,
                  a midnight-less day (America/Santiago 2026-09-06), a
                  midnight fall-back (America/Santiago 2026-04-05) and a
                  skipped date (Pacific/Apia 2011-12-30); oracle = the first
                  whole minute whose local date is >= d (a minute scan).
  calendar split  zones x (train_end, val_end) pairs x rows every 2 h.
  walk-forward    train x test x step days x mode x zone x span.
  purge           every contiguous test block and every pair of blocks of
                  a 12-row set with irregular times and label horizons x
                  embargo in rows 0..3 and in ns (0, 1 row gap, 2.5 gaps);
                  oracle = the interval rule; plus the leak property (no kept
                  row's label interval meets a test block's label span).
  CPCV            n_groups 2..7 x n_test_groups x rows n..n+4.
  bootstrap       method x seed x AR(1) phi; the circular method against its
                  exact variance; every argument's refusal.
  MDE / verdict   alpha x power x sides x n x sd; estimate x interest x design
                  present / absent.
  DSR, PBO        closed form and brute-force CSCV over seeded matrices.
  ledger, seals   every append / reopen / tamper; the 16 gate combinations.

Not in the grids (and why): zones before 1970 (the data never is); a
bootstrap statistic other than the mean for the exact-variance check (no
closed form); PBO with tied in-sample bests beyond the first-index rule
(checked on one constructed matrix only).
"""
from __future__ import annotations

import itertools
import math
import random
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import NormalDist
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from bot.bt import validation as V
from bot.bt.validation.splits import day_start_ns

REPO = Path(__file__).resolve().parents[3]
NS = 1_000_000_000
_N = NormalDist()


# ---------------------------------------------------------------------------- days
def oracle_day_start(d: date, tz: str) -> int:
    z = ZoneInfo(tz)
    naive = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
    for m in range(-30 * 60, 30 * 60 + 1):
        s = naive + 60 * m
        if datetime.fromtimestamp(s, tz=timezone.utc).astimezone(z).date() >= d:
            return s * NS
    raise AssertionError("no start")


DAY_CASES = []
for tz, center in [("America/New_York", date(2026, 3, 8)), ("America/New_York", date(2026, 11, 1)),
                   ("Europe/London", date(2026, 3, 29)), ("Europe/London", date(2026, 10, 25)),
                   ("Australia/Lord_Howe", date(2026, 4, 5)), ("Australia/Lord_Howe", date(2026, 10, 4)),
                   ("America/Santiago", date(2026, 4, 5)), ("America/Santiago", date(2026, 9, 6)),
                   ("Pacific/Apia", date(2011, 12, 30)), ("Asia/Tokyo", date(2026, 1, 7)), ("UTC", date(2026, 1, 7)),
                   ("Asia/Kolkata", date(2026, 3, 1)), ("America/St_Johns", date(2026, 3, 8))]:
    for k in range(-2, 3):
        DAY_CASES.append((tz, center + timedelta(days=k)))


def test_day_start_grid():
    assert len(DAY_CASES) == 65
    for tz, d in DAY_CASES:
        assert day_start_ns(d, ZoneInfo(tz)) == oracle_day_start(d, tz), (tz, d)


# ---------------------------------------------------------------------------- calendar split
def test_calendar_split_grid():
    n = 0
    for tz in ("UTC", "Asia/Tokyo", "America/New_York", "America/Santiago", "Australia/Lord_Howe"):
        t0 = int(datetime(2026, 3, 1, tzinfo=timezone.utc).timestamp())
        rows = [(t0 + 7200 * i + 37) * NS for i in range(12 * 45)]  # every 2 h (+37 s), 45 days
        starts = {}
        for a_off in range(0, 40, 3):
            for gap in (1, 2, 7):
                a = date(2026, 3, 2) + timedelta(days=a_off)
                b = a + timedelta(days=gap)
                for x in (a, b):
                    starts.setdefault(x, oracle_day_start(x, tz))
                cs = V.calendar_split(rows, tz=tz, train_end=a.isoformat(), val_end=b.isoformat())
                A, B = starts[a], starts[b]
                assert [rows[i] for i in cs.train.idx] == [t for t in rows if t < A]
                assert [rows[i] for i in cs.val.idx] == [t for t in rows if A <= t < B]
                assert [rows[i] for i in cs.oos.idx] == [t for t in rows if t >= B]
                n += 1
    assert n == 5 * 14 * 3


@pytest.mark.parametrize("bad", [dict(train_end="2026-01-09", val_end="2026-01-07"), dict(train_end="2026-01-07", val_end="2026-01-07"),
                                 dict(train_end="2026-1-7", val_end="2026-01-09"), dict(train_end="2026-02-30", val_end="2026-03-09"),
                                 dict(train_end=20260107, val_end="2026-01-09"), dict(tz="Mars/Base"), dict(tz="")])
def test_calendar_split_refusals(bad):
    kw = dict(tz="UTC", train_end="2026-01-07", val_end="2026-01-09")
    kw.update(bad)
    with pytest.raises(V.ValidationError):
        V.calendar_split([1767225600 * NS], **kw)


@pytest.mark.parametrize("rows", [[3, 2], [1, True], [1.5], [2**63]])
def test_calendar_split_refuses_unsorted_or_non_int_rows(rows):
    with pytest.raises(V.ValidationError):
        V.calendar_split(rows, tz="UTC", train_end="2026-01-07", val_end="2026-01-09")


# ---------------------------------------------------------------------------- walk-forward
def oracle_wf(rows, tz, tr, te, st, mode):
    z = ZoneInfo(tz)
    loc = lambda t: datetime.fromtimestamp(t // NS, tz=timezone.utc).astimezone(z).date()  # noqa: E731
    d0, dend = loc(rows[0]), loc(rows[-1]) + timedelta(days=1)
    end = oracle_day_start(dend, tz)
    out, k = [], 0
    while True:
        s = d0 + timedelta(days=k * st)
        ts, tend = s + timedelta(days=tr), s + timedelta(days=tr + te)
        if oracle_day_start(tend, tz) > end:
            return out
        S = oracle_day_start(d0 if mode == "anchored" else s, tz)
        A, B = oracle_day_start(ts, tz), oracle_day_start(tend, tz)
        out.append(([t for t in rows if S <= t < A], [t for t in rows if A <= t < B]))
        k += 1


def test_walk_forward_grid():
    n = 0
    cache = {}
    for tz in ("UTC", "America/New_York"):
        for span in (7, 14):
            t0 = int(datetime(2026, 3, 2, 5, tzinfo=timezone.utc).timestamp())
            rows = [(t0 + 3600 * i) * NS for i in range(24 * span)]
            for tr, te, st, mode in itertools.product((1, 2, 3, 4), (1, 2, 3), (1, 2, 3), ("rolling", "anchored")):
                key = (tz, span, tr, te, st, mode)
                if key not in cache:
                    cache[key] = oracle_wf(rows, tz, tr, te, st, mode)
                got = V.walk_forward(rows, tz=tz, train_days=tr, test_days=te, step_days=st, mode=mode)
                want = cache[key]
                assert [([rows[i] for i in f.train.idx], [rows[i] for i in f.test.idx]) for f in got] == want, key
                n += 1
    assert n == 2 * 2 * 4 * 3 * 3 * 2


def test_walk_forward_purges_labels_that_reach_the_test_window():
    rows = [(1767225600 + 3600 * i) * NS for i in range(24 * 6)]
    rng = random.Random(3)
    le = [t + rng.choice((0, 1800, 7200, 30 * 3600)) * NS for t in rows]
    for f in V.walk_forward(rows, tz="UTC", train_days=2, test_days=1, step_days=1, mode="rolling", label_end=le):
        A = f.test.start_ns
        assert all(le[i] <= A for i in f.train.idx)
        assert set(f.purged) == {i for i in range(len(rows)) if f.train.start_ns <= rows[i] < A and le[i] > A}


@pytest.mark.parametrize("bad", [dict(train_days=0), dict(test_days=True), dict(step_days=1.0), dict(mode="expanding"),
                                 dict(label_end=[0])])
def test_walk_forward_refusals(bad):
    kw = dict(tz="UTC", train_days=1, test_days=1, step_days=1, mode="rolling")
    kw.update(bad)
    with pytest.raises(V.ValidationError):
        V.walk_forward([1767225600 * NS, 1767312000 * NS], **kw)


def test_walk_forward_eval_fit_never_sees_test_rows():
    rows = [(1767225600 + 3600 * i) * NS for i in range(24 * 10)]
    cols = {"i": list(range(len(rows)))}
    folds = V.walk_forward(rows, tz="UTC", train_days=3, test_days=2, step_days=1, mode="rolling")
    seen = []
    V.walk_forward_eval(folds, cols, fit=lambda c: seen.append(set(c["i"])) or max(c["i"]),
                        evaluate=lambda ch, c: min(c["i"]) - ch)
    for f, s in zip(folds, seen):
        assert s == set(f.train.idx) and not s & set(f.test.idx)


# ---------------------------------------------------------------------------- purge
def _purge_rows():
    rng = random.Random(20260925)
    t, cur = [], 1767225600 * NS
    for _ in range(12):
        cur += rng.choice((1, 2, 3)) * 3600 * NS
        t.append(cur)
    le = [x + rng.choice((0, 1, 2, 5, 9)) * 1800 * NS for x in t]
    return t, le


def oracle_purge(t, le, blocks, emb_kind, emb):
    keep = []
    for i in range(len(t)):
        drop = any(i in b for b in blocks)
        for b in blocks:
            s0, e0 = t[b[0]], max(le[j] for j in b)
            # 「空き」= the first row AFTER the block starting at or after e0 (the rule's text: the purge runs
            # from the row after the last test row up to 空き, so 空き lies after the block)
            f = next((j for j in range(b[-1] + 1, len(t)) if t[j] >= e0), None)
            if i < b[0] and le[i] > s0:
                drop = True
            if i > b[-1] and t[i] < e0:
                drop = True
            if f is not None and emb_kind == "rows" and f <= i < f + emb:
                drop = True
            if f is not None and emb_kind == "ns" and t[f] <= t[i] < t[f] + emb:
                drop = True
        if not drop:
            keep.append(i)
    return keep


def test_purge_grid():
    t, le = _purge_rows()
    n = len(t)
    blocks = [list(range(a, b + 1)) for a in range(n) for b in range(a, n)]
    pairs = [(x, y) for x in blocks for y in blocks if len(x) <= 3 and len(y) <= 3 and x[-1] + 1 < y[0]]
    embargoes = [("rows", k) for k in range(4)] + [("ns", e) for e in (0, 3600 * NS, int(2.5 * 3600 * NS))]
    count = 0
    for bl in [[b] for b in blocks] + [list(p) for p in pairs]:
        test = [i for b in bl for i in b]
        for kind, e in embargoes:
            kw = {"embargo_rows": e} if kind == "rows" else {"embargo_ns": e}
            got = V.purged_train(t, le, test, **kw)
            assert list(got.train) == oracle_purge(t, le, bl, kind, e), (bl, kind, e)
            for i in got.train:  # the leak property
                for b in bl:
                    s0, e0 = t[b[0]], max(le[j] for j in b)
                    assert le[i] <= s0 or t[i] >= e0
            assert set(got.train) | set(got.test) | set(got.purged) | set(got.embargoed) == set(range(n))
            count += 1
    assert count == (len(blocks) + len(pairs)) * len(embargoes) and len(blocks) == 78


@pytest.mark.parametrize("kw", [{}, {"embargo_rows": 1, "embargo_ns": 1}, {"embargo_rows": -1}, {"embargo_ns": 1.0},
                                {"embargo_rows": True}])
def test_purge_embargo_must_be_exactly_one_form(kw):
    t, le = _purge_rows()
    with pytest.raises(V.ValidationError):
        V.purged_train(t, le, [3, 4], **kw)


def test_purge_refuses_bad_labels_and_tests():
    t, le = _purge_rows()
    for args in ((t, le[:-1], [1]), (t, [x - 1 for x in t], [1]), (t, le, []), (t, le, [1, 1]), (t, le, [99])):
        with pytest.raises(V.ValidationError):
            V.purged_train(*args, embargo_rows=0)


# ---------------------------------------------------------------------------- CPCV
def test_cpcv_grid():
    count = 0
    for N in range(2, 8):
        for k in range(1, N):
            for n in range(N, N + 5):
                t = [(1767225600 + 3600 * i) * NS for i in range(n)]
                le = [x + 5400 * NS for x in t]
                c = V.cpcv(t, le, n_groups=N, n_test_groups=k, embargo_rows=1)
                assert c.n_splits == math.comb(N, k) and c.n_paths == math.comb(N, k) * k // N
                sizes = [len(g) for g in c.groups]
                assert sum(sizes) == n and max(sizes) - min(sizes) <= 1
                assert [i for g in c.groups for i in g] == list(range(n))
                pairs = sorted((s, g) for p in c.paths() for s, g in p)
                assert pairs == sorted((s, g) for s in itertools.combinations(range(N), k) for g in s)
                for p in c.paths():
                    assert sorted(g for _, g in p) == list(range(N)) and all(g in s for s, g in p)
                for sp in c.splits:
                    test = [i for g in sp.test_groups for i in c.groups[g]]
                    assert sp.purged == V.purged_train(t, le, test, embargo_rows=1)
                count += 1
    assert count == sum((N - 1) * 5 for N in range(2, 8))


# ---------------------------------------------------------------------------- bootstrap
def _ar1(phi, n=600, seed=1):
    r = random.Random(seed)
    x, out = 0.0, []
    for _ in range(n + 100):
        x = phi * x + r.gauss(0, 1)
        out.append(x)
    return out[100:]


def test_bootstrap_grid():
    for phi in (0.0, 0.3, 0.6, 0.9):
        x = _ar1(phi)
        for method in V.BOOTSTRAP_METHODS:
            for seed in (1, 2):
                a = V.block_bootstrap_ci(x, block_len=15, n_resamples=400, seed=seed, alpha=0.1, method=method, statistic="mean")
                b = V.block_bootstrap_ci(x, block_len=15, n_resamples=400, seed=seed, alpha=0.1, method=method, statistic="mean")
                assert a == b and a.lo < a.estimate < a.hi
            c = V.block_bootstrap_ci(x, block_len=15, n_resamples=400, seed=3, alpha=0.1, method=method, statistic="mean")
            assert c != a
        exact = V.circular_block_se_of_mean(x, 15)
        est = V.block_bootstrap_ci(x, block_len=15, n_resamples=3000, seed=5, alpha=0.1, method="circular", statistic="mean").se
        assert abs(est / exact - 1) < 0.08, (phi, est, exact)


@pytest.mark.parametrize("bad", [dict(block_len=0), dict(block_len=11), dict(block_len=True), dict(block_len=2.0),
                                 dict(n_resamples=1), dict(alpha=0.0), dict(alpha=1.0), dict(method="iid"),
                                 dict(method=None), dict(seed=None), dict(seed=1.5), dict(statistic="median"),
                                 dict(x=[1.0] * 9 + [float("nan")])])
def test_bootstrap_refusals(bad):
    kw = dict(x=list(range(10)), block_len=3, n_resamples=10, seed=1, alpha=0.1, method="circular", statistic="mean")
    kw.update(bad)
    with pytest.raises(V.ValidationError):
        V.block_bootstrap_ci(**kw)


# ---------------------------------------------------------------------------- MDE / verdict
def test_mde_grid():
    n = 0
    for a, p, s, nn, sd in itertools.product((0.01, 0.05, 0.1), (0.5, 0.8, 0.9), (1, 2), (10, 400), (0.5, 10.0)):
        want = (_N.inv_cdf(1 - a / s) + _N.inv_cdf(p)) * sd / math.sqrt(nn)
        assert V.mde(n=nn, sd=sd, alpha=a, power=p, sides=s, approx="normal") == pytest.approx(want, rel=1e-12)
        n += 1
    assert n == 72


def test_verdict_grid_never_negative_without_a_design():
    count = 0
    for sides, zmul, imul, design in itertools.product((1, 2), (-3.0, -0.5, 0.0, 0.5, 3.0), (0.5, 1.0, 3.0), (True, False)):
        m = V.mde(n=400, sd=10.0, alpha=0.05, power=0.8, sides=sides, approx="normal")
        est, se, interest = zmul * 0.5, 0.5, imul * m
        kw = dict(n=400, sd=10.0) if design else {}
        v = V.verdict(estimate=est, se=se, interest=interest, alpha=0.05, power=0.8, sides=sides, approx="normal", **kw)
        crit = _N.inv_cdf(1 - 0.05 / sides)
        z = est / se
        detected = abs(z) > crit if sides == 2 else z > crit
        want = "陽性" if detected else ("陰性" if design and interest > m else "不明")
        assert v.label == want, (sides, zmul, imul, design)
        count += 1
    assert count == 60


@pytest.mark.parametrize("bad", [dict(se=0.0), dict(interest=0.0), dict(n=400), dict(sd=1.0), dict(sides=3),
                                 dict(approx="t"), dict(alpha=1.0), dict(estimate=float("inf"))])
def test_verdict_refusals(bad):
    kw = dict(estimate=0.3, se=0.5, interest=3.0, alpha=0.05, power=0.8, sides=2, approx="normal")
    kw.update(bad)
    with pytest.raises(V.ValidationError):
        V.verdict(**kw)


# ---------------------------------------------------------------------------- DSR / PBO
def oracle_dsr(sr, T, sk, ku, N, Vt):
    g = 0.5772156649015329
    sr0 = 0.0 if N == 1 else math.sqrt(Vt) * ((1 - g) * _N.inv_cdf(1 - 1 / N) + g * _N.inv_cdf(1 - 1 / (N * math.e)))
    return _N.cdf((sr - sr0) * math.sqrt(T - 1) / math.sqrt(1 - sk * sr + (ku - 1) / 4 * sr * sr))


def test_dsr_grid():
    n = 0
    for sr, T, sk, ku, N, Vt in itertools.product((-0.05, 0.0, 0.1, 0.3), (50, 1000), (-1.0, 0.0, 0.5), (3.0, 6.0),
                                                  (1, 2, 10, 1000), (0.0, 0.001, 0.01)):
        got = V.deflated_sharpe(sr=sr, T=T, skew=sk, kurtosis=ku, n_trials=N, var_trials=Vt).dsr
        assert got == pytest.approx(oracle_dsr(sr, T, sk, ku, N, Vt), abs=1e-12)
        n += 1
    assert n == 4 * 2 * 3 * 2 * 4 * 3
    prev = 1.0
    for N in (1, 2, 5, 50, 5000):
        d = V.deflated_sharpe(sr=0.1, T=500, skew=0.0, kurtosis=3.0, n_trials=N, var_trials=0.002).dsr
        assert d <= prev
        prev = d
    with pytest.raises(V.ValidationError):
        V.deflated_sharpe(sr=1.0, T=100, skew=3.0, kurtosis=1.0, n_trials=2, var_trials=0.0)


def oracle_pbo(M, S):
    T, N = len(M), len(M[0])
    b = T // S
    lam = []
    for comb in itertools.combinations(range(S), S // 2):
        IS = [r for k in comb for r in range(k * b, (k + 1) * b)]
        OOS = [r for r in range(T) if r not in IS]
        mis = [np.mean([M[r][j] for r in IS]) for j in range(N)]
        mos = [np.mean([M[r][j] for r in OOS]) for j in range(N)]
        best = int(np.argmax(mis))  # first on ties
        rank = int(np.sum(np.array(mos) < mos[best])) + 1
        w = rank / (N + 1)
        lam.append(math.log(w / (1 - w)))
    return sum(1 for x in lam if x <= 0) / len(lam)


def test_pbo_grid():
    rng = random.Random(9)
    n = 0
    for T, N, S in itertools.product((4, 8, 12), (2, 3, 5), (2, 4)):
        if T % S:
            continue
        for _ in range(5):
            M = [[rng.choice((-2, -1, 0, 1, 2, 3)) for _ in range(N)] for _ in range(T)]
            assert V.pbo(M, n_blocks=S, metric="mean").pbo == pytest.approx(oracle_pbo(M, S), abs=1e-12)
            n += 1
    assert n == 3 * 3 * 2 * 5  # every T here is divisible by both S
    for bad in (dict(n_blocks=3), dict(n_blocks=8), dict(metric="median")):
        kw = dict(n_blocks=2, metric="mean")
        kw.update(bad)
        with pytest.raises(V.ValidationError):
            V.pbo([[1, 2], [2, 1], [0, 1], [1, 0]], **kw)


# ---------------------------------------------------------------------------- ledger
def test_ledger_counts_reopen_and_refuses_tampering(tmp_path):
    d = str(tmp_path / "led")
    led = V.IterLedger(d)
    for k in range(5):
        led.add(design="d1" if k % 2 else "d2", sr=0.01 * k)
        assert V.IterLedger(d).count() == k + 1
    assert V.IterLedger(d).count(design="d1") == 2
    lines = (tmp_path / "led" / "ITER.jsonl").read_text(encoding="utf-8").splitlines()
    variants = {"edit": lines[:2] + [lines[2].replace('"sr":0.02', '"sr":0.5')] + lines[3:],
                "drop": lines[:2] + lines[3:], "swap": [lines[1], lines[0]] + lines[2:], "blank": lines + [""],
                "junk": lines + ["{"]}
    for name, ls in variants.items():
        bad = tmp_path / name
        shutil.copytree(d, bad)
        (bad / "ITER.jsonl").write_text("\n".join(ls) + "\n", encoding="utf-8")
        with pytest.raises(V.LedgerError):
            V.IterLedger(str(bad))
    hand = tmp_path / "hand"
    hand.mkdir()
    (hand / "ITER.md").write_text("# 手で書いた台帳\n", encoding="utf-8")
    with pytest.raises(V.LedgerError):
        V.IterLedger(str(hand))
    r = V.deflated_sharpe_from_ledger(V.IterLedger(d), sr=0.1, T=1000, skew=0.0, kurtosis=3.0, var_trials=0.001)
    assert r.n_trials == 5 and r.dsr == pytest.approx(oracle_dsr(0.1, 1000, 0.0, 3.0, 5, 0.001), abs=1e-12)
    srs = [0.01 * k for k in range(5)]
    v = np.var(srs, ddof=1)
    r2 = V.deflated_sharpe_from_ledger(V.IterLedger(d), sr=0.1, T=1000, skew=0.0, kurtosis=3.0, var_trials=None)
    assert r2.var_trials == pytest.approx(v)
    with pytest.raises(V.ValidationError):
        V.deflated_sharpe_from_ledger(V.IterLedger(str(tmp_path / "empty")), sr=0.1, T=10, skew=0.0, kurtosis=3.0,
                                      var_trials=0.1)


# ---------------------------------------------------------------------------- seals
SEAL_CSV = "ts,v\n" + "".join(f"2026-01-{d:02d}T00:00:00Z,{d}\n" for d in range(1, 11))
SEAL_REC = ('{"unit": "u1", "forward_start": "2026-03-01T00:00:00+00:00", "files": [{"path": "data/d.csv", '
            '"time_column": "ts", "seal_from_ts": "2026-01-08T00:00:00+00:00"}]}')


def _seal_root(root: Path, approval: bool, audit: str) -> None:
    (root / "data").mkdir(parents=True)
    (root / "data" / "d.csv").write_text(SEAL_CSV, encoding="utf-8")
    (root / "scripts").mkdir()
    shutil.copyfile(REPO / "scripts" / "_research_audit_gate.py", root / "scripts" / "_research_audit_gate.py")
    (root / "docs" / "AUDITOR").mkdir(parents=True)
    body = "\n".join(f"指摘 {i}: 合成の記録の行。" for i in range(1, 7))
    (root / "docs" / "AUDITOR" / "ACTION_LOG.md").write_text(
        "# 台帳\n\n## 監査の記録\n監査対象: u1/封印の開封\n監査役: owner-auditor(合成)\n" + body + f"\n判定: {audit}\n",
        encoding="utf-8")
    sd = root / "backtest_data" / "phase2_sealed" / "u1"
    sd.mkdir(parents=True)
    (sd / "SEALED.json").write_text(SEAL_REC, encoding="utf-8")
    if approval:
        (sd / "UNSEAL_APPROVED").write_text("承認\n", encoding="utf-8")


def test_sealed_gates_all_sixteen(tmp_path, monkeypatch):
    n = 0
    for env, approval, token, audit in itertools.product((True, False), repeat=4):
        root = tmp_path / f"r{n}"
        _seal_root(root, approval, "通す" if audit else "止める")
        monkeypatch.delenv("PHASE2_FINAL_EVAL", raising=False)
        if env:
            monkeypatch.setenv("PHASE2_FINAL_EVAL", "u1")
        tok = "I_UNDERSTAND_THIS_IS_FINAL_EVAL" if token else "x"
        if env and approval and token and audit:
            df = V.read_sealed(str(root / "data" / "d.csv"), unit="u1", token=tok, root=str(root))
            assert df["v"].tolist() == [8, 9, 10]
        else:
            with pytest.raises(V.SealedRefused):
                V.read_sealed(str(root / "data" / "d.csv"), unit="u1", token=tok, root=str(root))
        n += 1
    assert n == 16


def test_ordinary_read_never_returns_a_sealed_row(tmp_path):
    root = tmp_path / "r"
    _seal_root(root, True, "通す")
    cut = int(datetime(2026, 1, 8, tzinfo=timezone.utc).timestamp()) * NS
    lo = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()) * NS
    with pytest.raises(V.SealedRefused):
        V.read_table(str(root), "data/d.csv", time_column="ts")
    with pytest.raises(V.SealedRefused):
        V.read_table(str(root), "data/d.csv", time_column="ts", range_ns=(lo, cut + 1))
    assert V.read_table(str(root), "data/d.csv", time_column="ts", range_ns=(lo, cut))["v"].tolist() == list(range(1, 8))
    (root / "data" / "copy.csv").write_text(SEAL_CSV, encoding="utf-8")  # the same bytes under another name
    with pytest.raises(V.SealedRefused):
        V.read_table(str(root), "data/copy.csv", time_column="ts")
    (root / "elsewhere").mkdir()
    (root / "elsewhere" / "x.csv").write_text(SEAL_CSV, encoding="utf-8")
    with pytest.raises(V.SealedRefused):
        V.read_table(str(root), "elsewhere/x.csv", time_column="ts")
    (root / "data" / "free.csv").write_text("ts,v\n2026-02-01T00:00:00Z,1\n", encoding="utf-8")
    assert V.read_table(str(root), "data/free.csv", time_column="ts")["v"].tolist() == [1]
