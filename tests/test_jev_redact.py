"""`scripts/jev/redact.py` — 通る側(伏せられる)と止まる側(伏せた後に残らない)の両方。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pytest

from scripts.jev.redact import RedactionError, assert_clean, redact, redact_json


def test_redacts_env_key_value():
    text = "TYPESAFE_API_KEY=sk-abcdefghijklmnop"
    out, counts = redact(text)
    assert "sk-abcdefghijklmnop" not in out
    assert "<redacted:env>" in out
    assert counts["env"] == 1


def test_redacts_env_key_not_in_example_but_matches_generic_pattern():
    text = "SOME_OTHER_SECRET: hunter2value"
    out, counts = redact(text)
    assert "hunter2value" not in out
    assert counts["env"] == 1


def test_redacts_bearer_token():
    text = "Authorization: Bearer abcDEF123456"
    out, counts = redact(text)
    assert "abcDEF123456" not in out
    assert "Bearer <redacted>" in out
    assert counts["bearer"] == 1


def test_redacts_long_token():
    token = "a" * 40
    text = f"id={token}"
    out, counts = redact(text)
    assert token not in out
    assert "<redacted:token>" in out
    assert counts["token"] == 1


def test_sha256_64_hex_survives():
    sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    text = f"state_sha256={sha}"
    out, counts = redact(text)
    # 鍵名にも Bearer にも当たらないので、64 桁 16 進の sha256 はそのまま残る
    assert out == text
    assert sum(counts.values()) == 0


def test_redacts_root_and_home_paths():
    text = "見つけた: /root/secret/file.txt と /home/user/trade/data/x"
    out, counts = redact(text)
    assert "/root/" not in out
    assert "/home/" not in out
    assert counts["path"] == 2


def test_redacts_email():
    text = "連絡先: komekome3ai@gmail.com"
    out, counts = redact(text)
    assert "komekome3ai@gmail.com" not in out
    assert "<email>" in out
    assert counts["email"] == 1


def test_clean_text_passes_assert_clean():
    assert_clean("これは何も秘密情報を含まない普通の日本語の文章です。")


def test_assert_clean_raises_on_leftover_secret():
    with pytest.raises(RedactionError):
        assert_clean("TYPESAFE_API_KEY=sk-abcdefghijklmnop")


def test_assert_clean_does_not_raise_after_redact():
    raw = (
        "TYPESAFE_API_KEY=sk-abcdefghijklmnop\n"
        "Authorization: Bearer abcDEF123456\n"
        "id=" + "b" * 40 + "\n"
        "連絡先: komekome3ai@gmail.com\n"
    )
    out, _ = redact(raw)
    assert_clean(out)  # 冪等性: 一度伏せた文字列は再検出されない


def test_assert_clean_ignores_paths():
    # (d) パスは assert_clean の検査対象外(仕様どおり)
    assert_clean("/home/user/trade/data/jev/x にログがある")


def test_redact_json_recurses_into_nested_structures():
    obj = {
        "a": ["TYPESAFE_API_KEY=sk-abcdefghijklmnop", 123],
        "b": {"c": "Bearer abcDEF123456"},
    }
    out = redact_json(obj)
    assert "sk-abcdefghijklmnop" not in str(out)
    assert "abcDEF123456" not in str(out)
    assert out["a"][1] == 123
