"""Item 3 battery (検証・再現・出力): the protocol between the runner and a target adapter.

A target adapter is a module defining ``TARGET`` (an object with ``name`` and
``run(scene_input: dict) -> dict``).  The runner hands it ONE request at a
time (a scene's ``input`` or ``variant``; JSON-able) with ``root`` added: a
fresh scratch directory holding the request's ``files`` (written by the
runner; ``text`` is UTF-8, ``copy_from_repo`` copies that repository file).
Every path in a request is relative to ``root``.

Requests (``op``) and the observation each must return (only these keys are read):

  calendar_split   rows [t_ns], tz, train_end, val_end (dates; half-open at 00:00 in tz)
                   -> {"parts": {"train"|"val"|"oos": [t_ns] | {"bounds": [start_ns, end_ns]}}}
  walk_forward     rows, tz, train_days, test_days, step_days, mode
                   -> {"folds": [{"train": rows|{"bounds"}, "test": rows|{"bounds"}}, ...]}
  walk_forward_eval  as walk_forward + columns {"a": [...], "b": [...]} + rule (the strategy, user code)
                   -> {"folds": [{"choice": "a"|"b", "test_score": float}, ...]}
  purged_split     rows, label_end [t_ns], test_rows [index], embargo_rows, embargo_ns
                   -> {"train": [t_ns]} or {"train_idx": [index]}
  cpcv             rows, label_end, n_groups, n_test_groups, embargo_rows, embargo_ns, want_train_for [group]
                   -> {"n_splits": int, "n_paths": int, "train": [t_ns] | "train_idx": [index]}
  cpcv_paths       as cpcv -> {"paths": [[{"split": [group, ...], "group": group}, ...], ...]}
  block_bootstrap  x, block_len, n_resamples, seed, alpha, statistic -> {"ci": [lo, hi]}
  mde              n, sd, alpha, power, sides, approx -> {"mde": float}
  verdict          alpha, power, sides, cases [{estimate, se, n?, sd?, interest}] -> {"verdicts": ["陰性"|"不明"|"陽性"]}
  dsr              sr, T, skew, kurtosis (non-excess), n_trials, var_trials -> {"dsr": float}
  dsr_returns      returns [float], n_trials, var_trials -> {"dsr": float}
  pbo              matrix [[...]] rows x strategies, n_blocks, metric -> {"pbo": float}
  iter_ledger      ledger_dir, first [trial], more [trial] -> {"counts": [after first, after reopen, after more]}
  iter_dsr         ledger_dir, trials [trial], best {sr, T, skew, kurtosis}, var_trials -> {"dsr": float}
  sealed_read      unit, path, env {name: value} (exactly these are set; PHASE2_FINAL_EVAL is unset
                   when absent), token -> {"v": [the v column of the rows returned]}
  data_read        path, time_column (the target's ORDINARY read for a run, not the sealed loader)
                   -> {"v": [...]}
  run              run {data [path], config, seed, strategy, runs_dir, purpose?, prereg?}, repeat?
                   strategy: "fixed_times" = the config's legs as market orders; "seeded_random" = the same legs,
                   each round trip's quantity 0.01 * (1 + r / 256) with r drawn in leg order from
                   random.Random(seed).randrange(256); "unseeded_random" = the same with r = one byte of os.urandom
                   -> {"run_id": str, "record": {git_sha, diff_hash, config, data_sha256 {path: hex},
                       seed, version, prereg_sha256, purpose}, "exports": {path: purpose}}
                   (with repeat = k: {"records": [record, ...]} as well)
  run_ids          runs [run spec], sleep_before_s [float] -> {"ids": [str, ...]}
  auto_repro       run -> {"reproduced": bool, "runs": int}   (the TARGET's own comparison: how many times
                   it ran the same input and whether the results were identical)
  trade_metrics    trades [{id, side, qty, entry_px, exit_px, entry_t_ns, exit_t_ns}], want [...]
                   -> {"per_trade_bp": [...], "quantiles": {"0.05": ...}, "neg_frac": float,
                       "exposure_hours": float, "bp_per_hour": float}  (the keys in want)
  fill_metrics     orders, fills, end_t_ns -> {"fill_rate": float, "missed": int}
  markout         fills [{t_ns, px, side, qty}], mids [[t_ns, mid]], horizons_s -> {"markout": {"60": [...], ...}}
  cost_breakdown   fills, funding, rates -> {"costs": {maker_fee, taker_fee, spread, funding}}
  exit_reasons     trades [{id, reason, pnl}] -> {"by_reason": {reason: {"n": int, "pnl": float}}}
  drawdown         equity, t_ns -> {"max_dd_pct": float} / {"max_dd_abs": float}
  dashboard        runs [{key, ...run spec}] -> {"run_ids": {key: id}, "top_tabs": [label],
                   "run_list": [id], "run_tabs": {id: [label]}, "tab_text": {id: {label: text}},
                   "external_refs": [url], "values": {id: {"per_trade_bp": [...], "neg_frac": float}}}
                   (the adapter creates the runs with the target's own writer, starts the target's
                   dashboard on a free 127.0.0.1 port, reads what it SERVES and stops it)
  wiring_test      break None | "api_route" | "tab_label" -> {"passed": bool}
                   (the target's own wiring tests run in a subprocess whose PYTHONPATH starts with
                   wiring_break/ and whose env has I3_WIRING_BREAK = break; see wiring_break/sitecustomize.py)

Rules for every adapter (the scene-keeper's fixed mouth; 委任文 §3):
- Hand the request to the target through its public API, translating the
  request's declarative fields into the target's own options.  Never compute
  a value the target did not produce (a unit or container change of the
  target's own output is allowed: seconds -> ns, DataFrame -> list, a param
  string back to the JSON value it was logged from).  Never read the scene's
  expected answer, never special-case a scene id.
- The strategy of a request (walk_forward_eval's rule, run's fixed legs) is
  user code: the adapter writes it on top of the target's API.
- A target that has no knob for a stated field (e.g. a block length) is run
  with its own default and the adapter says so in ``note``.

Three ways a request can end without an observation:
- ``Refused``: the TARGET refused (raised, or returned an explicit error) -- 「対応なし」,
  except where the scene's variant expects a refusal (then it is the correct answer).
- ``NotExpressible``: the ADAPTER found no public way to give the request to the
  target -- 「結果なし」 with the reason (what was looked for, where).
- any other exception escaping the adapter -- 「結果なし」 with the traceback tail.
"""
from __future__ import annotations


class Refused(Exception):
    """The target itself refused the request (exception or explicit error)."""


class NotExpressible(Exception):
    """The adapter has no public way to give this request to the target."""


def need(cond: bool, what: str) -> None:
    if not cond:
        raise NotExpressible(what)


def not_expressible_all(target_name: str, what_looked_for: str):
    """A TARGET whose every request is NotExpressible, with the search that was made."""

    class _T:
        name = target_name

        def run(self, inp: dict) -> dict:
            raise NotExpressible(f"{inp.get('op')}: {what_looked_for}")

    return _T()
