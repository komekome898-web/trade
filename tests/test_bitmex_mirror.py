"""BitMEX アーカイブの丸ごと保全(scripts/mirror_bitmex_archive.py)。

ネットワークには出ない。固定するのは**やり直せる性質**だけ:
取引所は 2026-09-23 に閉じるので、途中で失敗した時に**もう一度走らせれば済む**
ことが、速さより大事である。半端なファイルを残す実装は、無いより悪い。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = REPO / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mir = _load("mirror_bitmex_archive")


class _Resp:
    def __init__(self, body: bytes, status: int = 200):
        self.content = body
        self.status_code = status

    def iter_content(self, _n):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_a_complete_download_lands_atomically(tmp_path, monkeypatch):
    """`.part` に書いて完了時に改名する = 途中の姿が本名で見えない。"""
    body = b"x" * 1234
    monkeypatch.setattr(mir.requests, "get", lambda *a, **k: _Resp(body))
    dest = tmp_path / "data" / "trade" / "20190904.csv.gz"

    assert mir.download("data/trade/20190904.csv.gz", len(body), dest) is True
    assert dest.read_bytes() == body
    assert not list(dest.parent.glob("*.part"))          # 後片付けまで済んでいる


def test_a_short_download_leaves_nothing_behind(tmp_path, monkeypatch):
    """サイズが合わないものは**捨てる**。半端なファイルが残ると、
    次回の「サイズ照合で飛ばす」判定を騙して**永久に欠けたまま**になる。"""
    monkeypatch.setattr(mir.requests, "get", lambda *a, **k: _Resp(b"short"))
    monkeypatch.setattr(mir.time, "sleep", lambda *_: None)
    dest = tmp_path / "data" / "trade" / "20190904.csv.gz"

    assert mir.download("data/trade/20190904.csv.gz", 999_999, dest, retries=2) is False
    assert not dest.exists()
    assert not list(dest.parent.glob("*.part"))


def test_an_http_error_is_retried_then_reported_not_raised(tmp_path, monkeypatch):
    """1 本の失敗で全体を止めない。**再実行で拾える**ように False を返す。"""
    monkeypatch.setattr(mir.requests, "get", lambda *a, **k: _Resp(b"", 503))
    monkeypatch.setattr(mir.time, "sleep", lambda *_: None)
    dest = tmp_path / "data" / "trade" / "x.csv.gz"
    assert mir.download("data/trade/x.csv.gz", 10, dest, retries=2) is False


def test_free_space_can_be_measured_before_the_target_exists(tmp_path):
    """保存先がまだ無い状態でも空きを測れること
    (存在しないパスに statvfs すると落ちる — 実際に踏んだ)。"""
    missing = tmp_path / "not" / "yet" / "there"
    assert mir.free_bytes(missing) > 0


def test_porl_is_not_mirrored_by_default():
    """準備金証明は 85.9 GB あるが**相場データではない**。既定に入れない。
    (オーナーの「取れるだけ取る」は容量の無駄遣いの許可ではない。旗で選べる)"""
    src = (REPO / "scripts" / "mirror_bitmex_archive.py").read_text(encoding="utf-8")
    assert '"--include-porl"' in src
    assert 'wanted = ["trade", "quote"]' in src


def test_progress_is_written_where_it_gets_shared(tmp_path, monkeypatch):
    """**オーナーに貼らせない**ための要。状態は paper_logs に出て共有される。"""
    shared = tmp_path / "paper_logs" / "bitmex_mirror_status.json"
    monkeypatch.setattr(mir, "SHARED_STATUS", shared)
    mir.write_status(tmp_path / "out", {"downloaded_files": 7})

    assert json.loads(shared.read_text(encoding="utf-8"))["downloaded_files"] == 7
    assert (tmp_path / "out" / "STATUS.json").exists()


def test_the_launcher_is_safe_to_rerun_and_forces_utf8():
    bat = (REPO / "deploy" / "mirror_bitmex.bat").read_text(
        encoding="utf-8", errors="surrogateescape")
    assert "PYTHONUTF8=1" in bat and "PYTHONIOENCODING=utf-8:replace" in bat
    assert "mirror_bitmex_archive.py" in bat
    # 走っているコンポーネントに触らないこと(停止・起動・pull をしない)
    for forbidden in ("stop_all", "start_all", "git pull", "git push"):
        assert forbidden not in bat, forbidden


def test_the_output_goes_where_git_ignores_it():
    """246 GB を作業ツリーに置くと git が二度と使えなくなる。
    `data/` は .gitignore 済みで、そこに書くこと。"""
    src = (REPO / "scripts" / "mirror_bitmex_archive.py").read_text(encoding="utf-8")
    assert 'REPO / "data" / "archive" / "bitmex"' in src
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert any(line.strip() in {"data/", "data"} for line in ignored)


@pytest.mark.parametrize("name,prefix", sorted(mir.PREFIXES.items()))
def test_prefixes_are_public_read_only(name, prefix):
    assert prefix.startswith("data/")
    assert mir.BUCKET.startswith("https://")
