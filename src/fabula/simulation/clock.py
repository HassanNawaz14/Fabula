"""Simulation clock: integer minutes mapped to real seconds."""

from __future__ import annotations


class Clock:
    """1 simulation minute = 60 real seconds; the session lasts 10 minutes."""

    def __init__(self, duration_minutes: int = 10, seconds_per_minute: int = 60) -> None:
        if duration_minutes < 1:
            raise ValueError("duration_minutes must be at least 1")
        if seconds_per_minute < 1:
            raise ValueError("seconds_per_minute must be at least 1")
        self.duration_minutes = duration_minutes
        self.seconds_per_minute = seconds_per_minute
        self._elapsed_seconds = 0.0
        self._paused = False

    @property
    def elapsed_seconds(self) -> float:
        return self._elapsed_seconds

    @property
    def minute(self) -> int:
        minute = int(self._elapsed_seconds // self.seconds_per_minute)
        return min(minute, self.duration_minutes)

    @property
    def finished(self) -> bool:
        return self._elapsed_seconds >= self.duration_minutes * self.seconds_per_minute

    @property
    def paused(self) -> bool:
        return self._paused

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("cannot advance the clock by a negative amount")
        if not self._paused:
            self._elapsed_seconds += seconds

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False


class FakeClock(Clock):
    """Deterministic clock advanced explicitly by tests or scripted demos."""
