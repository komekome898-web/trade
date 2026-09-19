"""TypeSafe Jev(`https://api.typesafe.ai`)への薄い包み。

**bot の実行系(`src/bot/`)からは import しない**(`docs/DISCUSSIONS/2026-09-19_jev_adoption_review.md`
§2)。鍵(環境変数 `TYPESAFE_API_KEY`)が無くても構築・送信はできる — その場合 Authorization
ヘッダを付けずに送り、実行環境の代理サーバーが「API 資格情報」を付ける経路に依存する
(2026-09-19 の実測: 資格情報を置いていない状態では 403 "Must supply an API key" が返る =
代理サーバーは素通し。到達性は確認できた)。401 / 403 は `JevError`。
ネットワークへは `urllib.request` でのみ触れる(`requests` は使わない)。

呼び出しのたびに `log_dir/calls_<UTC日付>.jsonl` へ 1 行追記する。**state の本文は書かない**
(モデル名・質問 ID・state の sha256/文字数・usage・レイテンシ・ステータスだけ)。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_RETRY_STATUSES = (429, 529)
_RETRY_DELAYS = (2, 4, 8)  # 秒。最大 3 回再試行(初回 + 3 回 = 最大 4 回叩く)


class JevError(Exception):
    """Jev への呼び出しが失敗した(鍵/モデル未指定、または API のエラー応答)。"""


class JevClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
        log_dir: str = "data/jev",
        base_url: str = "https://api.typesafe.ai",
    ) -> None:
        if api_key is None:
            api_key = os.environ.get("TYPESAFE_API_KEY")
        # 鍵が無くても構築は失敗させない。この実行環境では、鍵を「API 資格情報」として
        # 代理サーバー側に置く経路がありうる(その場合 api.typesafe.ai 宛ての要求に
        # 代理サーバーが Authorization を付ける。鍵はこのプロセスには渡らない、という前提は
        # **未確認**。実際に鍵が無い・無効なまま送ると 401 が返るので、そこで JevError にする
        # (2026-09-19、コーディネーターの追加指示による変更)。
        if not model:
            raise JevError(
                "model が無い。版付き ID を明示すること(例: jev-1.13.0)。"
                "jev-latest は予告なく変わるので呼び出し側が固定すること"
            )
        if model == "jev-latest":
            print(
                "[jev] 警告: model=jev-latest は別名であり予告なく変わる。版付き ID を推奨する",
                file=sys.stderr,
            )
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.log_dir = Path(log_dir)
        self.base_url = base_url.rstrip("/")

    # -- 内部: 呼び出しログ --------------------------------------------------
    def _log_call(self, *, question_ids, state_sha256, state_chars, usage,
                  latency_ms, status, model_answered) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.log_dir / f"calls_{stamp}.jsonl"
        line = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "model_requested": self.model,
            "model_answered": model_answered,
            "question_ids": list(question_ids),
            "state_sha256": state_sha256,
            "state_chars": state_chars,
            "usage": usage,
            "latency_ms": latency_ms,
            "status": status,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            print(
                "[jev] 鍵なしで送信。代理サーバーの資格情報に依存",
                file=sys.stderr,
            )
        return headers

    def _post(self, path: str, body: dict) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = self._headers()
        last_err: Exception | None = None
        for attempt, delay in enumerate((*_RETRY_DELAYS, None)):
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body_head = e.read().decode("utf-8", errors="replace")[:200]
                if e.code == 401:
                    raise JevError(
                        "401: 鍵が無いか無効。環境変数 TYPESAFE_API_KEY か、"
                        "環境の API 資格情報を確認"
                    ) from e
                if e.code in _RETRY_STATUSES and delay is not None:
                    last_err = JevError(f"{e.code}: {body_head}")
                    time.sleep(delay)
                    continue
                raise JevError(f"{e.code}: {body_head}") from e
        # ここには到達しない想定(最後の要素は delay=None で必ず return か raise する)
        raise last_err or JevError("不明なエラー")

    def evaluate(self, state, questions: dict) -> dict:
        state_str = state if isinstance(state, str) else json.dumps(
            state, ensure_ascii=False, sort_keys=True, default=str
        )
        state_sha256 = hashlib.sha256(state_str.encode("utf-8")).hexdigest()
        state_chars = len(state_str)
        question_ids = list(questions.keys())
        body = {"state": state, "model": self.model, "questions": questions}

        t0 = time.monotonic()
        status = "error"
        model_answered = None
        usage = None
        try:
            resp = self._post("/v1/systemone", body)
        except JevError:
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            self._log_call(
                question_ids=question_ids, state_sha256=state_sha256,
                state_chars=state_chars, usage=usage, latency_ms=latency_ms,
                status=status, model_answered=model_answered,
            )
            raise
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        status = "ok"
        model_answered = resp.get("model")
        usage = resp.get("usage")
        self._log_call(
            question_ids=question_ids, state_sha256=state_sha256,
            state_chars=state_chars, usage=usage, latency_ms=latency_ms,
            status=status, model_answered=model_answered,
        )
        return resp

    def list_models(self) -> dict:
        url = f"{self.base_url}/v1/models"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise JevError(
                    "401: 鍵が無いか無効。環境変数 TYPESAFE_API_KEY か、"
                    "環境の API 資格情報を確認"
                ) from e
            body_head = e.read().decode("utf-8", errors="replace")[:200]
            raise JevError(f"{e.code}: {body_head}") from e
