"""Outbound mail. Only a console backend ships; swap in SMTP/SES by implementing ``Mailer``."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

log = logging.getLogger("app.mail")


@dataclass
class Message:
    to: str
    subject: str
    body: str
    action_url: str | None = None
    meta: dict[str, str] = field(default_factory=dict)


class Mailer(Protocol):
    async def send(self, message: Message) -> None: ...


class ConsoleMailer:
    """Writes the mail to the log and keeps the last messages in memory (tests read them)."""

    def __init__(self, keep: int = 100) -> None:
        self.outbox: list[Message] = []
        self._keep = keep

    async def send(self, message: Message) -> None:
        self.outbox.append(message)
        del self.outbox[: -self._keep]
        log.info(
            "mail to=%s subject=%r url=%s", message.to, message.subject, message.action_url or "-"
        )

    def last_for(self, email: str) -> Message | None:
        for message in reversed(self.outbox):
            if message.to == email:
                return message
        return None
