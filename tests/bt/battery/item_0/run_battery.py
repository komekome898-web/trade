#!/usr/bin/env python3
"""Runner for the item-0 ("核") scene battery.

Drives one target through every scene in `scenes.SCENES`, twice, and writes a
TSV report. It does NOT itself know how to import a candidate's package --
each target must be run under the Python interpreter that can actually
import it:

    当方の現状 / 新実装 / 試金石 (in-repo, needs `src/` on PYTHONPATH):
        PYTHONPATH=src python3 run_battery.py --target current_impl --out OUT.tsv
        PYTHONPATH=src python3 run_battery.py --target new_impl     --out OUT.tsv
        PYTHONPATH=src python3 run_battery.py --target mutant       --out OUT.tsv

    調査結果の候補 (each installed in its own isolated venv under
    <scratchpad>/bt/venvs/item_0/<candidate>/, per delegation doc Sec.4):
        <scratchpad>/bt/venvs/item_0/ziplime/bin/python3 run_battery.py \
            --target opp_ziplime --out OUT.tsv
        (same pattern for opp_zipline_reloaded / opp_lib_pybroker / opp_qf_lib / opp_basana)

Run it twice per target (or pass --repeat 2, the default) so the report
carries the "did two runs agree" column the delegation doc asks for
(`Sec.3 "比較の表"`: 2回の実行で一致したか).

The resulting table's cells use exactly the delegation doc's vocabulary
(Sec.1 用語 / Sec.3 場面集の規則5): 一致 / 対応なし / 不一致(値) / 結果なし,
plus a raw status/output dump for anything that errored.

2026-09-23 fix (場面集の規則1): every scene -- known_answer AND capability
-- is now graded by comparing `SceneResult.output` to `Scene.expected`
(`_grade`, below). Earlier this file only did that for known_answer scenes;
a capability scene's `verdict` was just the adapter's own self-reported
`status` word, so an adapter (or a hostile mutant) that merely *claimed*
"ok" with a fabricated `output` could not be told apart, by this script,
from a genuine positive result. `scenes.py` now gives every capability
scene an `expected` too, so the same closed comparison applies to both
kinds. See `scenes.py`'s module docstring for the full rationale.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_ITEM0_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_ITEM0_DIR))
sys.path.insert(0, str(_ITEM0_DIR / "adapters"))

from scenes import SCENES  # noqa: E402
from adapters.protocol import Adapter, SceneResult  # noqa: E402


def _load_adapter(target: str) -> Adapter:
    if target == "current_impl":
        from adapters.current_impl import CurrentImplAdapter
        return CurrentImplAdapter()
    if target == "new_impl":
        from adapters.new_impl_stub import NewImplAdapter
        return NewImplAdapter()
    if target == "opp_ziplime":
        from opponents.ziplime_adapter import ZiplimeAdapter
        return ZiplimeAdapter()
    if target == "opp_zipline_reloaded":
        from opponents.zipline_reloaded_adapter import ZiplineReloadedAdapter
        return ZiplineReloadedAdapter()
    if target == "opp_lib_pybroker":
        from opponents.lib_pybroker_adapter import LibPybrokerAdapter
        return LibPybrokerAdapter()
    if target == "opp_qf_lib":
        from opponents.qf_lib_adapter import QfLibAdapter
        return QfLibAdapter()
    if target == "opp_basana":
        from opponents.basana_adapter import BasanaAdapter
        return BasanaAdapter()
    if target == "mutant":
        # 審査員の試金石 (delegation doc Sec.3): 新実装の adapter を、観点4だけ
        # 1バーの先読み漏れへすり替える薄いラッパーで包む。in-repo なので
        # `PYTHONPATH=src` の current_impl/new_impl と同じ実行系列で走る。
        from mutant import LookaheadLeakMutant
        from adapters.new_impl_stub import NewImplAdapter
        return LookaheadLeakMutant(NewImplAdapter())
    raise SystemExit(
        f"unknown --target {target!r}. Known targets: current_impl, new_impl, mutant, "
        f"opp_ziplime, opp_zipline_reloaded, opp_lib_pybroker, opp_qf_lib, opp_basana "
        f"(each opp_* must be run under ITS OWN venv's python -- see module docstring)."
    )


def _output_matches_expected(output, expected) -> bool:
    """Compare an adapter's real output to a scene's `expected`.

    A dict `expected` is graded as a REQUIRED-SUBSET match against a dict
    `output`: every key in `expected` must be present in `output` with an
    equal value; extra keys in `output` (diagnostic/informational fields a
    capability scene's adapters attach, e.g. `callback_count` alongside
    `event_driven`) are ignored. This lets heterogeneous adapters (current
    impl / new impl / opponents) report extra detail without being
    penalised, while still requiring the specific field(s) the scene cares
    about to be exactly right. Any other `expected` type (int/str/bool/full
    dict for a known-answer scene) is graded by plain equality, which is
    what the known-answer scenes have always used (they build `expected` to
    equal the adapter's whole output dict already).
    """
    if isinstance(expected, dict):
        if not isinstance(output, dict):
            return False
        return all(output.get(k) == v for k, v in expected.items())
    return output == expected


def _grade(result: SceneResult, expected) -> str:
    """One SceneResult -> one of the delegation doc's four 正しさ words.

    Applied uniformly to known_answer AND capability scenes (2026-09-23,
    場面集の規則1) -- see this module's docstring and scenes.py's.
    """
    if result.status == "not_supported":
        return "対応なし"
    if result.status == "no_record":
        return "結果なし"
    if result.status == "error":
        return "不一致(値)"  # an unexpected exception is a failed check, not a "no result"
    # status == "ok" -- still independently checked against `expected`, never
    # trusted just because the adapter itself claims "ok" (this is exactly
    # the check the round-1 build was missing for capability scenes).
    return "一致" if _output_matches_expected(result.output, expected) else "不一致(値)"


def run_target(target: str, repeat: int = 2) -> list[dict]:
    adapter = _load_adapter(target)
    rows: list[dict] = []
    for scene in SCENES:
        runs = [adapter.run_scene(scene) for _ in range(repeat)]
        first = runs[0]
        match_across_runs = all(
            (r.status, r.output) == (first.status, first.output) for r in runs
        )
        verdict = _grade(first, scene.expected)
        rows.append(
            {
                "target": target,
                "scene_id": scene.id,
                "viewpoint": scene.viewpoint,
                "kind": scene.kind,
                "status": first.status,
                "output": first.output,
                "expected": scene.expected,
                "verdict": verdict,
                "match_across_runs": match_across_runs,
                "detail": first.detail,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", required=True, help="one target name (see module docstring for the full list)")
    parser.add_argument("--out", required=True, type=Path, help="TSV path to write the report to")
    parser.add_argument("--repeat", type=int, default=2, help="how many times to run each scene (default 2, per delegation doc's determinism check)")
    args = parser.parse_args()

    rows = run_target(args.target, repeat=args.repeat)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["target", "scene_id", "viewpoint", "kind", "status", "output", "expected", "verdict", "match_across_runs", "detail"]
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    n_total = len(rows)
    # `verdict` now uses the same four delegation-doc words for BOTH kinds
    # (2026-09-23 fix, 場面集の規則1): 一致/対応なし/不一致(値)/結果なし.
    by_verdict = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("一致", "対応なし", "不一致(値)", "結果なし")}
    n_mismatched_runs = sum(1 for r in rows if not r["match_across_runs"])
    print(f"{args.target}: {n_total} scenes -> wrote {args.out}")
    print(
        f"  正しさ: 一致={by_verdict['一致']}, 対応なし={by_verdict['対応なし']}, "
        f"不一致(値)={by_verdict['不一致(値)']}, 結果なし={by_verdict['結果なし']}; "
        f"再現(2回の実行で不一致)={n_mismatched_runs}"
    )


if __name__ == "__main__":
    main()
