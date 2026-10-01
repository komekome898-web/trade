"""K1 段階 G を閉じる委任(docs/DATA/delegations/20261001_k1_stage_g_close.md §2)の変異の確かめ(FIXES.md):
src の写しに 1 か所ずつ「直しを外す」変異を入れ、その直しの試験を回す(-x)。写しは作業の置き場
(環境変数 K1G_MUT_DIR。無ければ tempfile.mkdtemp() の新しいフォルダ)に作り、回した後に消す。
写しを PYTHONPATH の先頭に置き、pytest の pythonpath(pyproject.toml の "src")を空にし、import bot が写しを指すことを
変異ごとに確かめる。データの門(k1_newenv_g_datagate)の下で回す。

使い方: python3 scripts/k1_newenv_g_mutate.py"""
import os, shutil, subprocess, sys
REPO = "/home/user/trade"
import tempfile
S = os.environ.get("K1G_MUT_DIR") or tempfile.mkdtemp(prefix="k1g_mut_")
SRC = os.path.join(S, "src")
T = "tests/bt"
MUTANTS = [
    ("M0_control_no_change", None, None, None,
     [f"{T}/item_0/test_bt0_fix_g1_stream_name.py", f"{T}/item_2/test_i2_fix_g1_venue_streams.py",
      f"{T}/item_4/test_i4_fix_g1_k1_xvenue.py", f"{T}/item_1/test_i1_fix_g2_no_trade.py",
      f"{T}/item_3/test_i3_fix_g3_runner_range.py", f"{T}/item_1/test_i1_fix_g4_session.py",
      f"{T}/item_1/test_i1_fix_g6_loader_cost.py"]),
    ("M1_G1_core_no_stream_stamp", "bot/bt/core/engine.py",
     '        object.__setattr__(event, "stream", name)\n', "",
     [f"{T}/item_0/test_bt0_fix_g1_stream_name.py"]),
    ("M2_G1_venue_takes_every_stream", "bot/bt/fill/venue.py",
     "        if not self._takes(event):\n            return []", "        if False:\n            return []",
     [f"{T}/item_2/test_i2_fix_g1_venue_streams.py"]),
    ("M3_G1_strategy_first_arrival_is_signal", "bot/strategy/k1_xvenue.py",
     "        sb = w[self.signal]\n", "        sb = next(iter(w.values()))\n",
     [f"{T}/item_4/test_i4_fix_g1_k1_xvenue.py"]),
    ("M4_G2_no_trade_rows_not_recognised", "bot/bt/data/loader.py",
     "            if nt is not None and all(_blank(cells.get(f[n])) for n in nt):",
     "            if False:", [f"{T}/item_1/test_i1_fix_g2_no_trade.py"]),
    ("M5_G3_plan_ignores_the_range", "bot/bt/repro/runner.py",
     "            raw, _ = seals.read_checked(os.path.realpath(full), d.path, rng)",
     "            raw, _ = seals.read_checked(os.path.realpath(full), d.path, None)",
     [f"{T}/item_3/test_i3_fix_g3_runner_range.py"]),
    ("M6_G3_execute_reads_without_the_range", "bot/bt/repro/runner.py",
     '            ds["range_ns"] = list(rng)\n', '            pass\n',
     [f"{T}/item_3/test_i3_fix_g3_runner_range.py"]),
    ("M7_G4_session_optional_again", "bot/bt/data/spec.py",
     '        elif asset in ("crypto", "fx"):', '        elif False:',
     [f"{T}/item_1/test_i1_fix_g4_session.py"]),
    ("M8_G6_reader_per_row", "bot/bt/data/allowlist.py",
     "        return Fraction(_seal_iso_reader().read(text))",
     '        from .timestamps import TimeReader\n        return Fraction(TimeReader("iso", "UTC", (-(2**63), 2**63 - 1)).read(text))',
     [f"{T}/item_1/test_i1_fix_g6_loader_cost.py"]),
    ("M9_G6_columns_used_per_row", "bot/bt/data/loader.py",
     "        used = self.used if self.used is not None else set(self.spec.columns_used())",
     "        used = set(self.spec.columns_used())", [f"{T}/item_1/test_i1_fix_g6_loader_cost.py"]),
    ("M10_G6_identity_text_per_row", "bot/bt/data/loader.py",
     "        out.append(Row(rec, ev, fi, line, t, key, cells.rest(), synth))",
     "        json.dumps(rec, sort_keys=True)\n        out.append(Row(rec, ev, fi, line, t, key, cells.rest(), synth))",
     [f"{T}/item_1/test_i1_fix_g6_loader_cost.py"]),
    ("M11_G6_seal_time_read_twice", "bot/bt/data/loader.py",
     "                st = seal_time_ns(cells.get(ent.time_column), raw_t)",
     "                st = seal_time_ns(cells.get(ent.time_column))",
     [f"{T}/item_1/test_i1_fix_g6_loader_cost.py"]),
]
out = []
for name, rel, old, new, tests in MUTANTS:
    shutil.rmtree(SRC, ignore_errors=True)
    shutil.copytree(os.path.join(REPO, "src"), SRC, ignore=shutil.ignore_patterns("__pycache__"))
    if rel:
        p = os.path.join(SRC, rel)
        s = open(p, encoding="utf-8").read()
        assert s.count(old) == 1, (name, s.count(old))
        open(p, "w", encoding="utf-8").write(s.replace(old, new))
    chk = subprocess.run([sys.executable, "-c", "import bot; print(bot.__file__)"], cwd=REPO, capture_output=True,
                         text=True, env=dict(os.environ, PYTHONPATH=f"{REPO}/scripts:{SRC}")).stdout.strip()
    assert chk.startswith(SRC), chk  # the copy is what the tests import
    env = dict(os.environ, PYTHONPATH=f"{REPO}/scripts:{SRC}", K1G_DATAGATE_LOG=os.path.join(S, "mut_refused.log"))
    r = subprocess.run([sys.executable, "-m", "pytest", *tests, "-p", "k1_newenv_g_datagate", "-p", "no:cacheprovider",
                        "-o", "pythonpath=", f"--basetemp={S}/pt_mut", "-x"], cwd=REPO, env=env, capture_output=True, text=True)
    last = [l for l in r.stdout.strip().splitlines() if l.strip()][-1]
    out.append(f"{name}: exit {r.returncode}: {last}")
    print(out[-1], flush=True)
shutil.rmtree(SRC, ignore_errors=True)
shutil.rmtree(os.path.join(S, "pt_mut"), ignore_errors=True)
