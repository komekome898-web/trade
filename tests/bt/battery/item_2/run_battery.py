#!/usr/bin/env python3
"""Item 2 battery runner (執行の模型).

    python3 tests/bt/battery/item_2/run_battery.py --target current_impl --out OUT.tsv
    python3 tests/bt/battery/item_2/run_battery.py --target new_impl     --out OUT.tsv
    python3 tests/bt/battery/item_2/run_battery.py --target mutant       --out OUT.tsv
    python3 tests/bt/battery/item_2/run_battery.py --target opp_<name>   --out OUT.tsv
    python3 tests/bt/battery/item_2/run_battery.py --list-targets

Every scene is run TWICE, each pass in a fresh process under the target's own
interpreter (a survey tool runs under its isolated venv, see i2_targets.py).
OUT.tsv has one row per scene: both passes' correctness class, detail and
observation digest, and the reproducibility cell.  OUT.obs.jsonl keeps the raw
observations of both passes (for the materials; the table uses OUT.tsv only).

Correctness: 正解と一致 / 対応なし / 不一致 / 結果なし (i2_judge.CLASSES).
Reproducibility: 「2 回の実行で同じ」 when both passes give the same class and
the same observation digest, 「2 回で違う(…)」 otherwise, 「結果なし」 when
neither pass produced a result.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))

SCENE_TIMEOUT_S = int(os.environ.get("I2_SCENE_TIMEOUT_S", "120"))
PASS_TIMEOUT_S = int(os.environ.get("I2_PASS_TIMEOUT_S", "3600"))


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout(f"場面の時間の上限 {SCENE_TIMEOUT_S} 秒を超えた")


def load_target(name: str):
    import i2_targets
    spec = i2_targets.TARGETS[name]
    path = HERE / spec["module"]
    mspec = importlib.util.spec_from_file_location(f"i2_target_{name}", path)
    mod = importlib.util.module_from_spec(mspec)
    sys.modules[mspec.name] = mod
    mspec.loader.exec_module(mod)
    return mod.TARGET


def run_one(target, inp):
    """('ok', obs) | ('refused', detail) | ('none', detail)."""
    from i2_protocol import NotExpressible, Refused
    import copy
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(SCENE_TIMEOUT_S)
    try:
        obs = target.run(copy.deepcopy(inp))
        return "ok", obs
    except Refused as exc:
        return "refused", str(exc)[:600]
    except NotExpressible as exc:
        return "none", "adapter: " + str(exc)[:600]
    except _Timeout as exc:
        return "none", str(exc)
    except Exception as exc:  # adapter or harness defect: recorded, never a refusal
        tb = traceback.format_exc().strip().splitlines()[-3:]
        return "none", f"{type(exc).__name__}: {exc} | " + " / ".join(tb)[:600]
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def classify(scene, target):
    import i2_judge as J
    import i2_scenes as S
    exp = S.expected(scene)
    kind, val = run_one(target, scene["input"])
    obs_rec = {"control": val if kind == "ok" else None}
    if kind == "refused":
        return "対応なし", val, obs_rec
    if kind == "none":
        return "結果なし", val, obs_rec
    cls, detail = J.compare(exp, val, scene["input"])
    if "variant" not in scene or cls != "正解と一致":
        return cls, ("対照: " + detail if "variant" in scene and detail else detail), obs_rec
    vkind, vval = run_one(target, scene["variant"])
    obs_rec["variant"] = vval if vkind == "ok" else None
    if vkind == "refused":
        return "正解と一致", "変形を断った: " + vval[:300], obs_rec
    if vkind == "none":
        return "結果なし", "変形: " + vval, obs_rec
    return "不一致", "変形を断らずに走った(単一の結果を返した)", obs_rec


def child(name: str, jsonl: str, only: list[str] | None) -> int:
    import i2_judge as J
    import i2_scenes as S
    try:
        target = load_target(name)
    except Exception as exc:
        tb = traceback.format_exc().strip().splitlines()[-2:]
        with open(jsonl, "w", encoding="utf-8") as fh:
            for s in S.SCENES:
                if only and s["id"] not in only:
                    continue
                fh.write(json.dumps({"scene": s["id"], "class": "結果なし",
                                     "detail": f"対象を読み込めない: {type(exc).__name__}: {exc} | {' / '.join(tb)}"[:600],
                                     "digest": "-", "secs": 0.0, "obs": None}, ensure_ascii=False) + "\n")
        return 0
    with open(jsonl, "w", encoding="utf-8") as fh:
        for s in S.SCENES:
            if only and s["id"] not in only:
                continue
            t = time.monotonic()
            cls, detail, obs = classify(s, target)
            dig = J.digest({"class": cls, "obs": obs}) if cls != "結果なし" else "-"
            fh.write(json.dumps({"scene": s["id"], "class": cls, "detail": detail, "digest": dig,
                                 "secs": round(time.monotonic() - t, 3), "obs": obs},
                                ensure_ascii=False, default=str) + "\n")
            fh.flush()
    return 0


def interpreter(name: str) -> tuple[str, dict]:
    import i2_targets
    spec = i2_targets.TARGETS[name]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPO / "src"), str(HERE), env.get("PYTHONPATH", "")]))
    if spec.get("venv"):
        py = Path(i2_targets.VENV_ROOT) / spec["venv"] / "bin" / "python"
        return str(py), env
    return sys.executable, env


def repro_cell(a: dict, b: dict) -> str:
    if a["class"] == "結果なし" and b["class"] == "結果なし":
        return "結果なし"
    if a["class"] == b["class"] and a["digest"] == b["digest"]:
        return "2 回の実行で同じ"
    return f"2 回で違う({a['class']}/{a['digest']} と {b['class']}/{b['digest']})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target")
    ap.add_argument("--out")
    ap.add_argument("--scenes", default="")
    ap.add_argument("--list-targets", action="store_true")
    ap.add_argument("--child-pass", default="")
    a = ap.parse_args()
    only = [x for x in a.scenes.split(",") if x] or None
    if a.list_targets:
        import i2_targets
        for k, v in i2_targets.TARGETS.items():
            print(k, v.get("venv") or "-", v["module"], sep="\t")
        return 0
    if a.child_pass:
        return child(a.target, a.child_pass, only)
    import i2_scenes as S
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    py, env = interpreter(a.target)
    passes = []
    for k in (1, 2):
        jl = out.with_suffix(f".pass{k}.jsonl")
        cmd = [py, str(Path(__file__).resolve()), "--target", a.target, "--child-pass", str(jl)]
        if only:
            cmd += ["--scenes", ",".join(only)]
        t0 = time.time()
        try:
            r = subprocess.run(cmd, env=env, cwd=str(REPO), capture_output=True, text=True, timeout=PASS_TIMEOUT_S)
            err = (r.stderr or "")[-600:]
        except subprocess.TimeoutExpired:
            err = f"1 回の実行の時間の上限 {PASS_TIMEOUT_S} 秒を超えた"
        except OSError as exc:
            err = f"{type(exc).__name__}: {exc}"
        rows = {}
        if jl.exists():
            for line in jl.read_text(encoding="utf-8").splitlines():
                d = json.loads(line)
                rows[d["scene"]] = d
        for s in S.SCENES:
            if (only and s["id"] not in only) or s["id"] in rows:
                continue
            rows[s["id"]] = {"scene": s["id"], "class": "結果なし", "digest": "-", "secs": 0.0, "obs": None,
                             "detail": f"実行が行を残さなかった(開始 {time.strftime('%H:%M:%S', time.gmtime(t0))} UTC、"
                                       f"終わり {time.strftime('%H:%M:%S', time.gmtime())} UTC): {err}"}
        passes.append(rows)
    with open(out, "w", encoding="utf-8") as fh, open(out.with_suffix(".obs.jsonl"), "w", encoding="utf-8") as oj:
        fh.write("scene\tviewpoint\tkind\tclass_1\tdetail_1\tdigest_1\tclass_2\tdetail_2\tdigest_2\trepro\tsecs_1\tsecs_2\n")
        for s in S.SCENES:
            if only and s["id"] not in only:
                continue
            p1, p2 = passes[0][s["id"]], passes[1][s["id"]]
            clean = lambda x: str(x).replace("\t", " ").replace("\n", " ")  # noqa: E731
            fh.write("\t".join([s["id"], s["viewpoint"], s["kind"], p1["class"], clean(p1["detail"]), p1["digest"],
                                p2["class"], clean(p2["detail"]), p2["digest"], repro_cell(p1, p2),
                                str(p1["secs"]), str(p2["secs"])]) + "\n")
            oj.write(json.dumps({"scene": s["id"], "pass1": p1.get("obs"), "pass2": p2.get("obs")},
                                ensure_ascii=False, default=str) + "\n")
    for k in (1, 2):
        try:
            out.with_suffix(f".pass{k}.jsonl").unlink()
        except OSError:
            pass
    print(f"{a.target}: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
