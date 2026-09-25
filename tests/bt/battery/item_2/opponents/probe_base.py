"""Item 2 battery: shared shape of the adapters for survey tools that have no order-level API (whole-series
backtests, execution-cost functions, API clients).  Every scene makes a real call into the tool (`probe`: the
tool's own function signature(s) or help text, read from the installed tool at run time) and, unless the adapter
has a way to hand the scene to the tool (`express`), is answered 結果なし with the missing part and the probe's
output as what was tried.  No answer is computed here."""
from __future__ import annotations

from i2_protocol import NotExpressible


def signature_probe(*fns) -> str:
    import inspect
    out = []
    for f in fns:
        try:
            out.append(f"{getattr(f, '__module__', '?')}.{getattr(f, '__qualname__', f)}{inspect.signature(f)}")
        except (TypeError, ValueError) as exc:
            out.append(f"{f}: {type(exc).__name__}: {exc}")
    return " / ".join(out)


class ProbeAdapter:
    tool = "?"
    what = ""  # one sentence: what the tool's execution-related public API is

    def probe(self) -> str:
        raise NotImplementedError

    def express(self, inp):
        """Return an observation, or None when the scene cannot be handed to the tool (then why_not is used)."""
        return None

    def why_not(self, inp) -> str:
        return "場面の注文を渡す口が無い"

    def run(self, inp):
        got = self.express(inp)
        if got is not None:
            return got
        raise NotExpressible(f"{self.tool}: {self.why_not(inp)}。{self.what}。試したこと(道具の公開の口を実際に読んだ): {self.probe()[:500]}")
