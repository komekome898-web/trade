"""Base for survey tools whose strategy is not called per event (a rule table
or a signal array evaluated over the whole data at once). Each scene that
needs a per-event strategy call is answered `not_supported` with the
tool-specific attempt the subclass supplies (`attempt(scene_id)`), which
must be a real call into the tool. Subclasses override the scenes they can
actually run."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import SCENES, Adapter, _Abstract, method_name, not_supported  # noqa: E402,F401


class VectorBase(_Abstract):
    what = "?"

    def attempt(self, scene_id: str) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def _default(self, sc):
        return not_supported(f"{self.what}。試したこと: {self.attempt(sc.id)}")


for _s in SCENES:
    setattr(VectorBase, method_name(_s.id), VectorBase._default)
