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
        (same pattern for opp_zipline_reloaded / opp_lib_pybroker / opp_qf_lib)

Run it twice per target (or pass --repeat 2, the default) so the report
carries the "did two runs agree" column the delegation doc asks for
(`Sec.3 "比較の表"`: 2回の実行で一致したか).

The resulting table's cells use exactly the delegation doc's vocabulary
(Sec.3 "比較の表"): 一致 / 不一致(値) / 対応なし / 実行の記録なし, plus a
raw status/output dump for anything that errored.
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
        from adapters.opponents.ziplime_adapter import ZiplimeAdapter
        return ZiplimeAdapter()
    if target == "opp_zipline_reloaded":
        from adapters.opponents.zipline_reloaded_adapter import ZiplineReloadedAdapter
        return ZiplineReloadedAdapter()
    if target == "opp_lib_pybroker":
        from adapters.opponents.lib_pybroker_adapter import LibPybrokerAdapter
        return LibPybrokerAdapter()
    if target == "opp_qf_lib":
        from adapters.opponents.qf_lib_adapter import QfLibAdapter
        return QfLibAdapter()
    if target == "mutant":
        # 審査員の試金石 (delegation doc Sec.3): 新実装の adapter を、観点4だけ
        # 1バーの先読み漏れへすり替える薄いラッパーで包む。in-repo なので
        # `PYTHONPATH=src` の current_impl/new_impl と同じ実行系列で走る。
        from mutant import LookaheadLeakMutant
        from adapters.new_impl_stub import NewImplAdapter
        return LookaheadLeakMutant(NewImplAdapter())
    raise SystemExit(
        f"unknown --target {target!r}. Known targets: current_impl, new_impl, mutant, "
        f"opp_ziplime, opp_zipline_reloaded, opp_lib_pybroker, opp_qf_lib "
        f"(each opp_* must be run under ITS OWN venv's python -- see module docstring)."
    )


def _classify_known_answer(result: SceneResult, expected) -> str:
    if result.status == "not_supported":
        return "対応なし"
    if result.status == "no_record":
        return "実行の記録なし"
    if result.status == "error":
        return "不一致(値)"  # treat an unexpected exception as a failed known-answer check
    # status == "ok"
    return "一致" if result.output == expected else "不一致(値)"


def run_target(target: str, repeat: int = 2) -> list[dict]:
    adapter = _load_adapter(target)
    rows: list[dict] = []
    for scene in SCENES:
        runs = [adapter.run_scene(scene) for _ in range(repeat)]
        first = runs[0]
        match_across_runs = all(
            (r.status, r.output) == (first.status, first.output) for r in runs
        )
        if scene.kind == "known_answer":
            verdict = _classify_known_answer(first, scene.expected)
        else:
            verdict = first.status  # capability scenes: record the raw capability status/output
        rows.append(
            {
                "target": target,
                "scene_id": scene.id,
                "viewpoint": scene.viewpoint,
                "kind": scene.kind,
                "status": first.status,
                "output": first.output,
                "expected": scene.expected if scene.kind == "known_answer" else "",
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
    # `verdict` uses the delegation doc's Japanese vocabulary for known_answer
    # rows (対応なし/実行の記録なし/不一致(値)/一致) and the adapter's raw
    # `status` word for capability rows (ok/not_supported/no_record/error) --
    # the two kinds are not directly comparable, so tally by real `status`
    # here (both kinds), which is consistent regardless of scene kind.
    by_status = {s: sum(1 for r in rows if r["status"] == s) for s in ("ok", "not_supported", "no_record", "error")}
    n_mismatched_runs = sum(1 for r in rows if not r["match_across_runs"])
    print(f"{args.target}: {n_total} scenes -> wrote {args.out}")
    print(
        f"  status: ok={by_status['ok']}, not_supported={by_status['not_supported']}, "
        f"no_record={by_status['no_record']}, error={by_status['error']}; "
        f"2回の実行で不一致={n_mismatched_runs}"
    )


if __name__ == "__main__":
    main()
