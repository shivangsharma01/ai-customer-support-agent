"""In-process event bus: graph nodes emit trace events, admin WebSockets consume them.

Nodes run in worker threads (LangGraph sync nodes under an async server), so
emit() hands events to the server's event loop thread-safely. Only public,
PII-free data may be passed to emit() — enforced by callers via public_view().
"""

import asyncio
import time
from collections import defaultdict
from typing import Any

MAX_HISTORY = 500


class EventBus:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: list[asyncio.Queue] = []
        self._history: dict[str, list[dict]] = defaultdict(list)

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    def history(self, session_id: str) -> list[dict]:
        return self._history[session_id]

    def recent(self, limit: int = 200) -> list[dict]:
        merged = [e for events in self._history.values() for e in events]
        merged.sort(key=lambda e: e["timestamp"])
        return merged[-limit:]

    def emit(self, session_id: str, event_type: str, data: dict[str, Any]) -> None:
        event = {
            "session_id": session_id,
            "type": event_type,
            "timestamp": time.time(),
            **data,
        }
        hist = self._history[session_id]
        hist.append(event)
        del hist[:-MAX_HISTORY]
        if self._loop is None:
            return
        for q in list(self._subscribers):
            self._loop.call_soon_threadsafe(q.put_nowait, event)


bus = EventBus()
