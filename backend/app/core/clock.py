from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class ManualClock:
    """Deterministic clock for tests."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> datetime:
        from datetime import timedelta

        self._now += timedelta(**kwargs)
        return self._now


_current: Clock = SystemClock()


def use_clock(clock: Clock) -> Clock:
    """Swap the process-wide clock (tests install a ManualClock). Returns the previous one."""
    global _current
    previous = _current
    _current = clock
    return previous


def utcnow() -> datetime:
    """Current time from the installed clock; used for model defaults."""
    return _current.now()
