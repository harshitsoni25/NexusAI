"""Notifications for scheduled job outcomes.

A ``Notifier`` is any object with an ``emit`` method. The scheduler calls it on
retry, success and permanent failure. Built-in notifiers log, print, or POST to a
webhook; a ``CompositeNotifier`` fans out to several. Desktop/native notifications
belong to the Electron layer and can subscribe over the webhook or a custom notifier.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .models import RunState

logger = logging.getLogger("nexusai_pro_scheduler.notify")


@dataclass(slots=True)
class Notification:
    schedule_id: str
    schedule_name: str
    state: RunState
    attempt: int
    message: str
    job_id: str | None = None
    at: datetime | None = None

    def __post_init__(self) -> None:
        if self.at is None:
            self.at = datetime.now()

    def to_dict(self) -> dict[str, object]:
        return {
            "schedule_id": self.schedule_id,
            "schedule_name": self.schedule_name,
            "state": self.state.value,
            "attempt": self.attempt,
            "message": self.message,
            "job_id": self.job_id,
            "at": self.at.isoformat() if self.at else None,
        }


class Notifier(Protocol):
    def emit(self, notification: Notification) -> None: ...


class LoggingNotifier:
    """Writes each notification to the standard logging system."""

    def emit(self, notification: Notification) -> None:
        level = logging.ERROR if notification.state in (RunState.FAILED, RunState.DEAD) else logging.INFO
        logger.log(level, "%s", json.dumps(notification.to_dict()))


class ConsoleNotifier:
    """Prints a concise human-readable line; handy for local runs."""

    def emit(self, notification: Notification) -> None:
        print(f"[{notification.state.value}] {notification.schedule_name}: {notification.message}")


class WebhookNotifier:
    """POSTs the notification as JSON to a URL (fire-and-forget, best effort)."""

    def __init__(self, url: str, *, timeout: float = 5.0) -> None:
        self._url = url
        self._timeout = timeout

    def emit(self, notification: Notification) -> None:
        try:
            data = json.dumps(notification.to_dict()).encode("utf-8")
            request = urllib.request.Request(self._url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(request, timeout=self._timeout).close()  # noqa: S310 - explicit http(s) webhook
        except Exception as exc:  # noqa: BLE001 - notifications never break scheduling
            logger.warning("webhook notify failed: %s", exc)


class CollectingNotifier:
    """Keeps notifications in memory — used by tests and in-process consumers."""

    def __init__(self) -> None:
        self.notifications: list[Notification] = []

    def emit(self, notification: Notification) -> None:
        self.notifications.append(notification)


class CompositeNotifier:
    """Delivers each notification to every wrapped notifier."""

    def __init__(self, *notifiers: Notifier) -> None:
        self._notifiers = list(notifiers)

    def add(self, notifier: Notifier) -> None:
        self._notifiers.append(notifier)

    def emit(self, notification: Notification) -> None:
        for notifier in self._notifiers:
            try:
                notifier.emit(notification)
            except Exception as exc:  # noqa: BLE001
                logger.warning("notifier failed: %s", exc)
