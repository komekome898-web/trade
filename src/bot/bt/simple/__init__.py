"""単純な測りの道(2 版目): 足の中の道筋をたどる走らせ・約定・残し方。決まりの正本は docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md。"""
from .bars import read_bars
from .common import SimpleRoadError
from .run import run

__all__ = ["run", "read_bars", "SimpleRoadError"]
