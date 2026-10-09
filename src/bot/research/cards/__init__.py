"""Cards and their measurement (W1, docs/DISCUSSIONS/2026-10-02_W1_spec.md).

A card is one idea turned into a function that, at the end of each bar,
answers how much to hold (-1 .. +1). This package measures a card's effect
before costs, per scene, without looking ahead, against a control and with
its power. Costs (stage 5), the combiner (stage 4) and the bridge to the
live bot (stage 7) are not here.

  card     the mouth (`Card`, `SeriesSpec`) and what a card sees (`CardView`)      C1
  run      `run_card`: the card called through bot.bt.core's event flow           C2
  pnl      P_t = e_t * (open_{t+2} / open_{t+1} - 1) * 100 (%), empty bars skipped  C2
  scenes   scene variables at t from the past only, 365-day positions            C4
  blocklen the Politis-White circular block length of the P_t series             C5 c
  measure  a..h: means, drift-removed means, intervals, control, MDE, frequency,
           breakdown, the daily series; `daily_correlation`; `measure_card`
           (the settings fixed in the card's CARD.md)                               C5
  cardmd   reading CARD.md (its fields and 測定の設定)                               C6

Reference series and their availability (C3) are in `bot.bt.data.reference`.
The field check of a card's description (C6) is `scripts/check_card.py`.
Known-answer checks T1..T8: tests/research/cards/.
"""
from .card import Card, CardError, CardView, ExposureError, RefLookAheadError, SeriesSpec
from .measure import daily_correlation, measure, measure_card
from .pnl import PnL, pnl
from .run import CardRun, run_card

__all__ = ["Card", "CardError", "CardRun", "CardView", "ExposureError", "PnL", "RefLookAheadError", "SeriesSpec",
           "daily_correlation", "measure", "measure_card", "pnl", "run_card"]
