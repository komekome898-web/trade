"""K1 判定の封印ガード(`docs/PHASE2/K1/JUDGEMENT_PREREG.md` §1/§7)。

`k1_source.resolve_range` は BitMEX の `end` が 2019-12-31 を超えるとき、
**`--open-seal` と環境変数 `K1_SEAL_APPROVAL=L-085` の両方**が揃わなければ拒否する。
データは読まない(スタブした `args` だけで検査する)。
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import k1_source  # noqa: E402

OPEN_END = date(2020, 1, 1)  # 封印(end <= 2019-12-31)を超える最小の日


def _args(*, source="bitmex", start=None, end=OPEN_END, open_seal=False):
    return argparse.Namespace(source=source, start=start, end=end, open_seal=open_seal)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """このファイルの外へ承認の環境変数を漏らさない。"""
    monkeypatch.delenv(k1_source.SEAL_APPROVAL_ENV, raising=False)


def test_without_flag_bitmex_end_2020_is_refused():
    args = _args(open_seal=False)
    with pytest.raises(AssertionError):
        k1_source.resolve_range(args)


def test_with_flag_but_without_env_is_refused(monkeypatch):
    monkeypatch.delenv(k1_source.SEAL_APPROVAL_ENV, raising=False)
    args = _args(open_seal=True)
    with pytest.raises(AssertionError):
        k1_source.resolve_range(args)


def test_with_flag_and_wrong_env_is_refused(monkeypatch):
    monkeypatch.setenv(k1_source.SEAL_APPROVAL_ENV, "L-000")
    args = _args(open_seal=True)
    with pytest.raises(AssertionError):
        k1_source.resolve_range(args)


def test_with_both_flag_and_env_is_allowed(monkeypatch):
    monkeypatch.setenv(k1_source.SEAL_APPROVAL_ENV, k1_source.SEAL_APPROVAL_VALUE)
    args = _args(open_seal=True)
    start, end = k1_source.resolve_range(args)
    assert end == OPEN_END
    assert start == k1_source.default_start("bitmex")


def test_env_alone_without_flag_is_refused(monkeypatch):
    """`--open-seal` を渡し忘れたら、環境変数だけでは開かない(二重ガード)。"""
    monkeypatch.setenv(k1_source.SEAL_APPROVAL_ENV, k1_source.SEAL_APPROVAL_VALUE)
    args = _args(open_seal=False)
    with pytest.raises(AssertionError):
        k1_source.resolve_range(args)


def test_end_within_seal_never_needs_the_flag():
    """封印を超えない end は既定どおり、フラグも環境変数も無しで通る(既存挙動)。"""
    args = _args(end=date(2019, 12, 31), open_seal=False)
    start, end = k1_source.resolve_range(args)
    assert end == date(2019, 12, 31)


def test_binance_source_is_not_gated_by_the_bitmex_seal():
    """封印は BitMEX 専用。`binance` の既定終了日(2026-08-31)はガードの対象外。"""
    args = argparse.Namespace(source="binance", start=None, end=None, open_seal=False)
    start, end = k1_source.resolve_range(args)
    assert end == k1_source.default_end("binance")
