"""原典の設定値の抜き出しと、仕様の表との突き合わせ(scripts/road/source_params.py、工程 0 の S3)。"""
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("source_params", os.path.join(ROOT, "scripts", "road", "source_params.py"))
SP = importlib.util.module_from_spec(spec)
sys.modules["source_params"] = SP  # dataclass が自分のモジュールを sys.modules から引くため
spec.loader.exec_module(SP)

SRC = '''# 頭
state_before = 1
# 各自の設定値ココカラ------
apikey = inifile.get("k", "v")
foot = 1  # 足
settings_inner = dict(entry_setting=2, exit_setting=2)
mode = {"a": 1, "b": 2}
x, y = 3, 4
# ※ここから下は触らない方がいいよ
state_after = 0
'''


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_extract_takes_only_the_settings_block_and_dict_keys(tmp_path):
    src = _write(tmp_path, "bot.py", SRC)
    names = [p.name for p in SP.extract(src)]
    assert names == ["apikey", "foot", "settings_inner", "settings_inner.entry_setting", "settings_inner.exit_setting",
                     "mode", "mode.a", "mode.b", "x", "y"]


def test_missing_block_marker_stops(tmp_path):
    src = _write(tmp_path, "bot.py", "foot = 1\n")
    with pytest.raises(SP.SourceParamsError, match="設定の区切りの始まり"):
        SP.extract(src)


def _spec(tmp_path, body):
    return _write(tmp_path, "SPEC.md", "# 仕様\n\n```params bot.py\n" + body + "```\n")


FULL = """apikey: 除外 API の鍵(売買に効かない)
foot: 族
settings_inner: 族
settings_inner.entry_setting: 族
settings_inner.exit_setting: 族
mode: 族
mode.a: 族
mode.b: 族
x: 族
y: 族
"""


def test_full_table_passes(tmp_path):
    src = _write(tmp_path, "bot.py", SRC)
    assert SP.check([src], _spec(tmp_path, FULL)) == []
    assert SP.main(["check", "--src", src, "--spec", str(tmp_path / "SPEC.md")]) == 0


@pytest.mark.parametrize("body,needle", [
    (FULL.replace("settings_inner.exit_setting: 族\n", ""), "settings_inner.exit_setting(= dict("),
    (FULL.replace("apikey: 除外 API の鍵(売買に効かない)", "apikey: 除外"), "「除外」に理由が無い"),
    (FULL.replace("foot: 族", "foot: 固定"), "印 '固定'"),
    (FULL + "vola_count: 族\n", "vola_count は bot.py の設定の区切りに無い名前"),
    (FULL + "foot: 族\n", "foot を 2 度書いている"),
])
def test_each_gap_fails_in_japanese(tmp_path, body, needle):
    src = _write(tmp_path, "bot.py", SRC)
    fails = SP.check([src], _spec(tmp_path, body))
    assert any(needle in f for f in fails), fails
    assert SP.main(["check", "--src", src, "--spec", str(tmp_path / "SPEC.md")]) == 1


def test_no_fence_for_a_source_fails(tmp_path):
    src = _write(tmp_path, "bot.py", SRC)
    spec_path = _write(tmp_path, "SPEC.md", "# 仕様\n")
    assert any("params の囲みが無い" in f for f in SP.check([src], spec_path))


def test_extract_output_is_a_template_that_fails_until_filled(tmp_path, capsys):
    src = _write(tmp_path, "bot.py", SRC)
    assert SP.main(["extract", "--src", src]) == 0
    tmpl = capsys.readouterr().out
    spec_path = _write(tmp_path, "SPEC.md", tmpl)
    fails = SP.check([src], spec_path)
    assert len(fails) == 10 and all("「族」でも「除外 <理由>」でもない" in f for f in fails)


def test_real_matilda_sources_extract():
    for name, must in (("matilda_for_TaroCamp37.py", {"entry_setting", "step_setting", "break_delay", "range_setting"}),
                       ("matilda_v52.py", {"settings_inner.entry_setting", "settings_outer.entry_step", "vr_setting",
                                           "exit_mode", "time_anomaly"})):
        names = {p.name for p in SP.extract(os.path.join(ROOT, "docs", "legacy", name))}
        assert must <= names, must - names


def test_family_mark_may_carry_a_note_but_not_glued_text(tmp_path):
    src = _write(tmp_path, "bot.py", SRC)
    assert SP.check([src], _spec(tmp_path, FULL.replace("foot: 族", "foot: 族 足の長さ"))) == []
    fails = SP.check([src], _spec(tmp_path, FULL.replace("foot: 族", "foot: 族外")))
    assert any("印 '族外'" in f for f in fails), fails
