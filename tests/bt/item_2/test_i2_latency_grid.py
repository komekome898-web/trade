"""Adversarial grid: the latency model (C2-9) -- feed x order x cancel x
notice, each in {0, 3 ms, 10 ms}: 81 runs, all run. Every observable is
predicted from the channels it depends on only, so a delay leaking into
another channel fails here:

  seen(b0) = T0 + feed; seen(b12) = T0+12ms + feed               (feed)
  o1 market buy sent T0+5ms: fills at T0+5ms+order, at 10001 if it arrives
     before the book of T0+12ms, else 10003                       (order)
  o1 ack seen = its arrival + notice                            (order, notice)
  o3 crossing post-only sent T0+7ms: reject seen = 7ms + order + notice
  o2 limit 9990 sent T0+6ms, cancel sent T0+25ms: the cancel arrives at
     25ms + cancel; the 9985 print at T0+30ms fills o2 only if the cancel
     arrives later; its cancel notice is seen at that arrival + notice
                                                               (cancel, notice)

Plus the seeded distributions: every Empirical draw is one of the samples,
all samples appear over 300 draws, the same seed repeats the same sequence;
SeededUniform stays in [low, high]; bad specs are refused.

Not enumerated: jittered feed delays reordering one stream (the core keeps a
stream's order, item 0), delays near the one-hour cap.
"""
from __future__ import annotations

import itertools

import pytest

from bot.bt.latency import MAX_DELAY_NS, Constant, Empirical, LatencyModel, LatencySpecError, SeededUniform
from i2_gridkit import MS, T0, avg_px, book, filled, first_t, inp, place, run, trade

VALUES = (0, 3 * MS, 10 * MS)
GRID = list(itertools.product(VALUES, VALUES, VALUES, VALUES))


def test_grid_size():
    assert len(GRID) == 81


def lat(feed, order, cancel, notice):
    return {k: {"kind": "constant", "ns": v} for k, v in
            (("feed", feed), ("order", order), ("cancel", cancel), ("notice", notice))}


@pytest.mark.parametrize("combo", GRID, ids=["-".join(str(v // MS) for v in c) for c in GRID])
def test_latency_grid(combo):
    feed, order, cancel, notice = combo
    market = [book(T0, [(9999, 5)], [(10001, 5)], label="b0"), book(T0 + 12 * MS, [(9999, 5)], [(10003, 5)],
                                                                     label="b12"),
              trade(T0 + 30 * MS, 9985, 5, "sell")]
    actions = [place(T0 + 5 * MS, "o1", "buy", "market", 1.0), place(T0 + 6 * MS, "o2", "buy", "limit", 1.0, px=9990.0),
               place(T0 + 7 * MS, "o3", "buy", "limit", 1.0, px=10005.0, post_only=True),
               {"t": T0 + 25 * MS, "op": "cancel", "ref": "o2"}]
    obs, refused = run(inp(market, actions, latency=lat(*combo)))
    assert refused is None, refused
    assert obs["seen"]["b0"] == T0 + feed
    assert obs["seen"]["b12"] == T0 + 12 * MS + feed
    arrive1 = T0 + 5 * MS + order
    assert first_t(obs, "o1") == arrive1
    assert avg_px(obs, "o1") == (10001.0 if arrive1 < T0 + 12 * MS else 10003.0)
    assert obs["notices"]["o1"]["ack"] == arrive1 + notice
    assert obs["orders"]["o3"]["status"] == "rejected"
    assert obs["notices"]["o3"]["reject"] == T0 + 7 * MS + order + notice
    cancel_at = T0 + 25 * MS + cancel
    if cancel_at < T0 + 30 * MS:
        assert obs["orders"]["o2"]["status"] == "canceled" and filled(obs, "o2") == 0.0
        assert obs["notices"]["o2"]["cancel"] == cancel_at + notice
    else:
        assert obs["orders"]["o2"]["status"] == "filled"
        assert first_t(obs, "o2") == T0 + 30 * MS


def test_empirical_draws_are_samples_and_repeat_by_seed():
    samples = (3 * MS, 7 * MS, 11 * MS)
    a = [Empirical(samples, 7).draw() for _ in range(1)]
    e1, e2, e3 = Empirical(samples, 7), Empirical(samples, 7), Empirical(samples, 8)
    s1 = [e1.draw() for _ in range(300)]
    s2 = [e2.draw() for _ in range(300)]
    s3 = [e3.draw() for _ in range(300)]
    assert s1 == s2
    assert set(s1) == set(samples) and set(s3) == set(samples)
    assert s1 != s3
    assert a[0] == s1[0]


def test_seeded_uniform_range_and_repeat():
    u1, u2 = SeededUniform(2 * MS, 9 * MS, 3), SeededUniform(2 * MS, 9 * MS, 3)
    d1 = [u1.draw() for _ in range(500)]
    assert d1 == [u2.draw() for _ in range(500)]
    assert min(d1) >= 2 * MS and max(d1) <= 9 * MS


@pytest.mark.parametrize("bad", [-1, 1.5, True, MAX_DELAY_NS + 1, "5"])
def test_bad_constant_is_refused(bad):
    with pytest.raises(LatencySpecError):
        Constant(bad)


def test_every_channel_is_required():
    with pytest.raises(TypeError):
        LatencyModel(feed=Constant(0), order=Constant(0), cancel=Constant(0))  # notice missing
    with pytest.raises(LatencySpecError):
        LatencyModel(feed=Constant(0), order=Constant(0), cancel=Constant(0), notice=5)
    with pytest.raises(LatencySpecError):
        Empirical((), 1)
    with pytest.raises(LatencySpecError):
        SeededUniform(5, 4, 1)
