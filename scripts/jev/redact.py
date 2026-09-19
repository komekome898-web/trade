"""TypeSafe Jev へ送る前に、秘密情報らしき文字列を機械的に伏せる。

対象(仕様どおり、5 種類):
  (a) `.env.example` にある鍵名 + `[A-Z0-9_]*(KEY|SECRET|PASSWORD|TOKEN)[A-Z0-9_]*` の値
      → `<redacted:env>`
  (b) `Bearer <token>` → `Bearer <redacted>`
  (c) 32 文字以上の英数字(sha256 の 64 桁 16 進はそのまま残す) → `<redacted:token>`
  (d) `/root/...` `/home/...` のパス → `<path>`
  (e) メールアドレス → `<email>`

**state の本文は呼び出し側の責任で、この関数を必ず通してから送る。**
`assert_clean` は (a)〜(c) と (e) が 1 つでも残っていれば例外を投げる(送信直前の最終検査)。
(d) パスは検査対象に含めない — 仕様どおり(パスは秘密情報ではなく、置き場所の手がかりに過ぎない)。
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class RedactionError(Exception):
    """送信直前の検査で、伏せ切れていない秘密情報らしき文字列が見つかった。"""


def _env_key_names() -> list[str]:
    """`.env.example` の鍵名を実行時に読む(ハードコードしない)。"""
    example = REPO / ".env.example"
    if not example.is_file():
        return []
    text = example.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(r"^([A-Z][A-Z0-9_]*)\s*=", text, re.M)))


def _env_pattern() -> re.Pattern:
    names = _env_key_names()
    alts = [re.escape(n) for n in names]
    alts.append(r"[A-Z0-9_]*(?:KEY|SECRET|PASSWORD|TOKEN)[A-Z0-9_]*")
    # 既に <redacted:env> になっている値は再検出しない(冪等性・assert_clean の誤検出防止)
    return re.compile(r"\b(?:" + "|".join(alts) + r")\s*[:=]\s*(?!<redacted:)(\S+)")


_BEARER_RE = re.compile(r"Bearer\s+(?!<redacted>)\S+")
# `<redacted:token>` 自体(17 文字)は 32 文字未満なので、この正規表現は再検出しない
_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_\-])[A-Za-z0-9_\-]{32,}(?![A-Za-z0-9_\-])")
_HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_PATH_RE = re.compile(r"(?:/root|/home)/[^\s\"']*")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _redact_env(text: str) -> tuple[str, int]:
    count = 0
    pat = _env_pattern()

    def repl(m: re.Match) -> str:
        nonlocal count
        count += 1
        full = m.group(0)
        val = m.group(1)
        return full[: len(full) - len(val)] + "<redacted:env>"

    return pat.sub(repl, text), count


def _redact_bearer(text: str) -> tuple[str, int]:
    count = 0

    def repl(_m: re.Match) -> str:
        nonlocal count
        count += 1
        return "Bearer <redacted>"

    return _BEARER_RE.sub(repl, text), count


def _redact_tokens(text: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        s = m.group(0)
        if len(s) == 64 and _HEX64_RE.match(s):
            return s  # sha256 はそのまま残す(台帳の指紋に使うため)
        count += 1
        return "<redacted:token>"

    return _TOKEN_RE.sub(repl, text), count


def _redact_paths(text: str) -> tuple[str, int]:
    count = 0

    def repl(_m: re.Match) -> str:
        nonlocal count
        count += 1
        return "<path>"

    return _PATH_RE.sub(repl, text), count


def _redact_email(text: str) -> tuple[str, int]:
    count = 0

    def repl(_m: re.Match) -> str:
        nonlocal count
        count += 1
        return "<email>"

    return _EMAIL_RE.sub(repl, text), count


def redact(text: str) -> tuple[str, dict[str, int]]:
    """(a)→(b)→(c)→(d)→(e) の順に適用し、(伏せた後の文字列, 型ごとの件数) を返す。"""
    counts: dict[str, int] = {}
    text, counts["env"] = _redact_env(text)
    text, counts["bearer"] = _redact_bearer(text)
    text, counts["token"] = _redact_tokens(text)
    text, counts["path"] = _redact_paths(text)
    text, counts["email"] = _redact_email(text)
    return text, counts


def assert_clean(text: str) -> None:
    """(a)〜(c) と (e) が 1 つでも残っていれば `RedactionError` を投げる。(d) は対象外。"""
    _, n_env = _redact_env(text)
    _, n_bearer = _redact_bearer(text)
    _, n_token = _redact_tokens(text)
    _, n_email = _redact_email(text)
    hits = {
        "env": n_env,
        "bearer": n_bearer,
        "token": n_token,
        "email": n_email,
    }
    remaining = {k: v for k, v in hits.items() if v > 0}
    if remaining:
        raise RedactionError(f"伏せ切れていない秘密情報らしき文字列が残っている: {remaining}")


def redact_json(obj):
    """dict / list / str を再帰的に辿り、文字列にだけ `redact` を当てる。"""
    if isinstance(obj, str):
        text, _ = redact(obj)
        return text
    if isinstance(obj, dict):
        return {k: redact_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_json(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(redact_json(v) for v in obj)
    return obj
