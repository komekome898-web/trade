"""Pluggable notifications. Discord webhook first; others can be added by
implementing Notifier. Notification failures never crash the bot."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import requests

from bot.logging_setup import redact
from bot.settings import Secret

logger = logging.getLogger("bot.notify")


class Notifier(ABC):
    @abstractmethod
    def send(self, title: str, message: str, *, urgent: bool = False) -> bool:
        ...


class NullNotifier(Notifier):
    def send(self, title: str, message: str, *, urgent: bool = False) -> bool:
        return True


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: Secret, session: requests.Session | None = None,
                 timeout: float = 10.0):
        self._url = webhook_url
        self._session = session or requests.Session()
        self._timeout = timeout

    def send(self, title: str, message: str, *, urgent: bool = False) -> bool:
        """Post to the webhook, REDACTED.

        Alerts are assembled from whatever the failing path had to hand —
        exception strings, venue responses, kill-switch details — and any of
        those can carry a registered secret. Logs pass through `redact` on
        every line; this is the same choke point for the other way text leaves
        the process, and it is here rather than at each call site so a new
        alert cannot be written without it. Redaction runs BEFORE the length
        cap, so a truncated message can never end mid-secret.
        """
        if not self._url:
            return False
        prefix = "🚨 " if urgent else ""
        try:
            resp = self._session.post(
                self._url.reveal(),
                json={"content": redact(f"{prefix}**{title}**\n{message}")[:1900]},
                timeout=self._timeout,
            )
            return resp.status_code < 300
        except requests.exceptions.RequestException as e:
            logger.warning("notification failed", extra={"data": {
                "event": "notify_failed", "error": type(e).__name__}})
            return False
