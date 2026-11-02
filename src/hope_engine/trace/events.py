"""Structured run events. Emission is opt-in: with no sink, nothing is built or sent."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    run_id: str
    seq: int
    kind: str
    payload: dict[str, object] = field(default_factory=dict)
    t: float = 0.0  # seconds since the run started


EventSink = Callable[[Event], None]


class Emitter:
    def __init__(self, run_id: str, sink: EventSink | None) -> None:
        self.run_id = run_id
        self._sink = sink
        self._seq = 0
        self._start = time.monotonic()

    @property
    def enabled(self) -> bool:
        return self._sink is not None

    def emit(self, kind: str, payload: dict[str, object] | None = None) -> None:
        if self._sink is None:
            return
        self._sink(Event(self.run_id, self._seq, kind, payload or {}, round(time.monotonic() - self._start, 4)))
        self._seq += 1


SCHEMA_VERSION = 1


def to_json(event: Event) -> str:
    """Wire format shared by the API and the dashboard."""
    import json

    return json.dumps(
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": event.run_id,
            "seq": event.seq,
            "kind": event.kind,
            "payload": event.payload,
            "t": event.t,
        },
        separators=(",", ":"),
    )
