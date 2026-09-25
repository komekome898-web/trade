"""Item 1 battery (データと時刻): the protocol between the runner and a target adapter.

A target adapter is a module that defines ``TARGET`` (an object with a ``name``
string and a ``run(scene_input: dict) -> dict`` method).  The runner hands the
adapter ONE scene input at a time (a plain JSON-able dict; the forms are in
DEFINITIONS.md「入力の形」) and gets back an observation dict.  Only the keys
the scene's expected answer names are read:

    {
      "events":    {dataset_name: [record, ...]},   # in the order the target delivers them
      "anomalies": {dataset_name: [{"kind": "duplicate"|"conflict"|"backward"|"gap",
                                    "t_ns": int}, ...]},
      "hashes":    {relative_path: sha256 hex},      # what the target recorded for the files it read
      "adjusted":  {code: [{"date", "open", "high", "low", "close", "volume"}, ...]},
      "universe":  {date: [code, ...]},
      "paths":     {"event": {...}, "vector": {...}},  # item 12 (bars / sma / position / equity)
      "timing":    {"event_s": float, "vector_s": float},
    }

Records:
    trade: {"t_ns": int, "px": float, "qty": float, "side": "buy"|"sell"|"", "id": str}
    quote: {"t_ns": int, "bid": float, "ask": float, "bid_qty": float, "ask_qty": float}
    bar:   {"start_ns": int, "open": float, "high": float, "low": float,
            "close": float, "volume": float}

What the input asks for (``scene_input["want"]``):
    "events"    -- full records for every dataset (all keys of the record form)
    "times"     -- records of which only the time key (t_ns / start_ns) is judged;
                   a target that gives only times may return records with just that key
    "anomalies" / "hashes" -- the keys above

Rules for every adapter (the scene-keeper's fixed mouth; 委任文 §3):
- Pass the scene's files to the target by PATH (``scene_input["root"]`` joined
  with each dataset's ``paths``) and the scene's declarative ``spec`` translated
  into the target's own public options.  The adapter never opens, parses or
  rewrites a data file itself, never computes a value the target did not
  produce, never reads the expected answer, never special-cases a scene id.
- Structured inputs (item 1 V6 ``bars``/``actions``/``listings``, V7 ``trades``/
  ``bars``) may be handed to the target in whatever in-memory container its
  public API takes (a DataFrame, a list of its event objects); that is a change
  of container, not a computation.
- For V7 the scene's rule (DEFINITIONS.md「V7 の規則」) is written by the adapter
  on top of the target's own event API and its own vector API (the rule is the
  strategy, which is user code in every target).

Three ways a run can end without an observation:
- ``Refused``: the TARGET refused (raised, or returned an explicit error) --
  classified 「対応なし」.
- ``NotExpressible``: the ADAPTER found no public way to hand this scene to the
  target -- classified 「結果なし」 with the reason (what was looked for, where).
- any other exception escaping the adapter -- 「結果なし」 with the traceback
  tail (an adapter defect; recorded, never counted as a refusal).
"""
from __future__ import annotations

import os


class Refused(Exception):
    """The target itself refused the run (exception or explicit error)."""


class NotExpressible(Exception):
    """The adapter has no public way to give this scene to the target."""


def need(cond: bool, what: str) -> None:
    """Raise NotExpressible(what) unless cond."""
    if not cond:
        raise NotExpressible(what)


def dataset_paths(inp: dict, ds: dict) -> list[str]:
    """Absolute paths of one dataset's files (joined to the scene root, not resolved)."""
    return [os.path.join(inp["root"], p) for p in ds["paths"]]
