"""Process-wide dependencies bundled so services and routes receive one object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.clock import Clock
from app.core.config import Settings
from app.core.mail import Mailer
from app.core.rate_limit import RateLimiter


@dataclass
class AppContext:
    settings: Settings
    clock: Clock
    mailer: Mailer
    limiter: RateLimiter
    redis: Any | None = None
