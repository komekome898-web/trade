"""Pluggable notifications. Discord webhook first; others can be added by
implementing Notifier. Notification failures never crash the bot."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import requests

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
        if not self._url:
            return False
        prefix = "🚨 " if urgent else ""
        try:
            resp = self._session.post(
                self._url.reveal(),
                json={"content": f"{prefix}**{title}**\n{message}"[:1900]},
                timeout=self._timeout,
            )
            return resp.status_code < 300
        except requests.exceptions.RequestException as e:
            logger.warning("notification failed", extra={"data": {
                "event": "notify_failed", "error": type(e).__name__}})
            return False
