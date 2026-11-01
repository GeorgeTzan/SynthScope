"""Structured run events. Emission is opt-in: with no sink, nothing is built or sent."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    run_id: str
    seq: int
    kind: str
    payload: dict[str, object] = field(default_factory=dict)


EventSink = Callable[[Event], None]


class Emitter:
    def __init__(self, run_id: str, sink: EventSink | None) -> None:
        self.run_id = run_id
        self._sink = sink
        self._seq = 0

    @property
    def enabled(self) -> bool:
        return self._sink is not None

    def emit(self, kind: str, payload: dict[str, object] | None = None) -> None:
        if self._sink is None:
            return
        self._sink(Event(self.run_id, self._seq, kind, payload or {}))
        self._seq += 1
