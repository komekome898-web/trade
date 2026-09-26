#!/usr/bin/env python3
"""Round 13 materials check: every `core.<name>` the new-implementation
adapter uses is in bot.bt.core.__all__, none starts with '_', and the
adapter does not import bot.bt itself (it only gets `core` passed in)."""
import re
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "src"))
import bot.bt.core as core  # noqa: E402
src = (REPO / "tests/bt/battery/item_0/adapters/new_impl.py").read_text(encoding="utf-8")
names = sorted(set(re.findall(r"\bcore\.([A-Za-z_][A-Za-z0-9_]*)", src)))
print("names used via core.:", names)
print("not in core.__all__:", [n for n in names if n not in core.__all__])
print("underscore names:", [n for n in names if n.startswith("_")])
print("imports of bot.bt in adapter:", re.findall(r"^\s*(?:from|import)\s+bot\.bt\S*", src, flags=re.M))
