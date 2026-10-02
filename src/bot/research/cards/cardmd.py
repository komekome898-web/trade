"""Reading a card's description, docs/RESEARCH/cards/<id>/CARD.md (W1 spec C6).

Fields are `## <name>` headings (text may follow the name in brackets:
`## 原文(逐語)`). The field check is scripts/check_card.py; this module is
the reading both it and `measure_card` use.

The field 測定の設定 fixes, before measuring, the settings the spec leaves
open (the lead's answer of 2026-10-02): one line per setting, each with its
source after `| 出所:`.

    ## 測定の設定
    - vr_q_bars: 5 | 出所: <where this q comes from>          (or `なし`: no variance ratio)
    - day_zone: UTC | 出所: <...>                              (UTC or Asia/Tokyo)
    - 参照: <name> | lag_ns: <int> | 出所: <...>               (a constant lag)
    - 参照: <name> | available_at: per_row | 出所: <...>       (each row's own available_at)
      either may add `| 場面: category` or `| 場面: continuous` to use the series as a scene variable
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

FIELDS = ("原文", "意図の地図", "なぜ", "期待する向きと場面", "反証", "関数のパス", "水準とその出所",
          "使うデータと遅れ", "約定の模型", "測定の設定")
PERIOD = "測る期間"
DATA = "使うデータと遅れ"
SETTINGS = "測定の設定"
DAY_ZONES = ("UTC", "Asia/Tokyo")
SCENE_KINDS = ("category", "continuous")

_HEAD = re.compile(r"^##\s+(.+?)\s*$")
_LINE = re.compile(r"^\s*[-*]\s*([^:：|]+?)\s*[:：]\s*(.*?)\s*$")
_KV = re.compile(r"^\s*([^:：]+?)\s*[:：]\s*(.*?)\s*$")


@dataclass(frozen=True)
class Card:
    sections: dict  # name -> list of bodies (one per heading of that name)


def parse(text: str) -> Card:
    sections: dict = {}
    current: Optional[str] = None
    for line in text.splitlines():
        m = _HEAD.match(line)
        if m:
            title = m.group(1)
            current = None
            for name in FIELDS + (PERIOD,):
                if title == name or re.match(re.escape(name) + r"\s*[(（]", title):
                    current = name
                    sections.setdefault(name, []).append([])
                    break
            continue
        if line.startswith("# "):
            current = None
            continue
        if current is not None:
            sections[current][-1].append(line)
    return Card({k: ["\n".join(b) for b in v] for k, v in sections.items()})


def body(card: Card, name: str) -> tuple[Optional[str], Optional[str]]:
    """(body, problem)."""
    bodies = card.sections.get(name, [])
    if not bodies:
        return None, f"欄「{name}」が無い"
    if len(bodies) > 1:
        return None, f"欄「{name}」の見出しが {len(bodies)} つある"
    if not bodies[0].strip():
        return None, f"欄「{name}」が空"
    return bodies[0], None


@dataclass(frozen=True)
class Settings:
    vr_q_bars: Optional[int]
    day_zone: str
    declarations: dict = field(default_factory=dict)  # name -> {"lag_ns": int, "source": str} | per_row
    ref_scenes: dict = field(default_factory=dict)  # name -> "category" | "continuous"


def settings(card: Card) -> tuple[Optional[Settings], list[str]]:
    """The settings of 測定の設定, or None with the problems (a missing field is not reported here)."""
    text, why = body(card, SETTINGS)
    if why:
        return None, []
    problems: list[str] = []
    found: dict = {}
    decls: dict = {}
    scenes: dict = {}
    for ln in text.splitlines():
        if not ln.strip():
            continue
        m = _LINE.match(ln)
        if not m:
            problems.append(f"欄「{SETTINGS}」の行が読めない: {ln.strip()!r}")
            continue
        key = m.group(1).strip()
        parts = [p.strip() for p in m.group(2).split("|")]
        value, rest = parts[0], {}
        for p in parts[1:]:
            kv = _KV.match(p)
            if not kv:
                problems.append(f"欄「{SETTINGS}」の {key}: 「{p}」が「名前: 値」でない")
                continue
            rest[kv.group(1).strip()] = kv.group(2).strip()
        source = rest.pop("出所", "")
        if not source:
            problems.append(f"欄「{SETTINGS}」の {key}: {value} に出所が無い")
        if key == "vr_q_bars":
            if value == "なし":
                found[key] = None
            elif re.fullmatch(r"\d+", value) and int(value) >= 2:
                found[key] = int(value)
            else:
                problems.append(f"欄「{SETTINGS}」の vr_q_bars は 2 以上の整数か「なし」: {value!r}")
        elif key == "day_zone":
            if value in DAY_ZONES:
                found[key] = value
            else:
                problems.append(f"欄「{SETTINGS}」の day_zone は {list(DAY_ZONES)} のどれか: {value!r}")
        elif key == "参照":
            if not value or value in decls:
                problems.append(f"欄「{SETTINGS}」の参照の名前が空か、2 回ある: {value!r}")
                continue
            scene = rest.pop("場面", None)
            if scene is not None:
                if scene in SCENE_KINDS:
                    scenes[value] = scene
                else:
                    problems.append(f"欄「{SETTINGS}」の参照 {value}: 場面は {list(SCENE_KINDS)} のどれか: {scene!r}")
            if set(rest) == {"lag_ns"} and re.fullmatch(r"\d+", rest["lag_ns"]):
                decls[value] = {"lag_ns": int(rest["lag_ns"]), "source": source}
            elif rest == {"available_at": "per_row"}:
                decls[value] = {"available_at": "per_row", "source": source}
            else:
                problems.append(f"欄「{SETTINGS}」の参照 {value}: 「lag_ns: <整数>」か「available_at: per_row」の"
                                f"どちらか 1 つが要る(ほかの項目は書かない): {rest!r}")
        else:
            problems.append(f"欄「{SETTINGS}」に知らない設定がある: {key!r}")
    for req in ("vr_q_bars", "day_zone"):
        n = sum(1 for ln in text.splitlines() if (m := _LINE.match(ln)) and m.group(1).strip() == req)
        if n == 0:
            problems.append(f"欄「{SETTINGS}」に {req} が無い")
        elif n > 1:
            problems.append(f"欄「{SETTINGS}」に {req} が {n} 回ある")
    if problems:
        return None, problems
    return Settings(found["vr_q_bars"], found["day_zone"], decls, scenes), []


__all__ = ["Card", "DATA", "DAY_ZONES", "FIELDS", "PERIOD", "SCENE_KINDS", "SETTINGS", "Settings", "body", "parse",
           "settings"]
