"""Item 3 battery: the wiring breaker (壊し具) used by the scenes a18-wiring-test-*.

Loaded automatically by any Python process whose PYTHONPATH starts with this
directory (Python imports ``sitecustomize`` at start-up), so it also reaches a
dashboard server the target's tests start in a subprocess.  It acts only when
the environment variable I3_WIRING_BREAK is set, and only on servers built on
the standard library's http.server:

  api_route  -- a GET whose path starts with /api/ and contains "backtest"
                is answered 404 before the handler sees it;
  tab_label  -- every byte string "バックテスト" (UTF-8) the handler writes is
                replaced by the same number of spaces (lengths are kept, so
                Content-Length stays right).

It never touches the target's files.  With I3_WIRING_BREAK unset it does nothing.
"""
import os

_MODE = os.environ.get("I3_WIRING_BREAK", "")

if _MODE:
    import http.server as _hs

    _orig_parse = _hs.BaseHTTPRequestHandler.parse_request
    _LABEL = "バックテスト".encode("utf-8")

    class _Filter:
        def __init__(self, raw):
            self._raw = raw

        def write(self, b):
            return self._raw.write(bytes(b).replace(_LABEL, b" " * len(_LABEL)))

        def __getattr__(self, k):
            return getattr(self._raw, k)

    def _parse(self):
        ok = _orig_parse(self)
        if not ok:
            return ok
        path = (self.path or "").split("?", 1)[0]
        if _MODE == "api_route" and path.startswith("/api/") and "backtest" in path.lower():
            self.send_error(404, "broken by the item 3 battery (api_route)")
            return False
        if _MODE == "tab_label" and not isinstance(self.wfile, _Filter):
            self.wfile = _Filter(self.wfile)
        return ok

    _hs.BaseHTTPRequestHandler.parse_request = _parse
