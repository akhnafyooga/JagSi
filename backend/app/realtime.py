"""Fan-out of live events to the dashboard (issue #13).

Two kinds of listeners share this hub:

* ``GET /api/stream`` (SSE, Week 6) gets every event: telemetry, status, alerts.
* ``WS /ws/alerts`` (Week 8) only gets ``alert`` and ``alert_ack``, because that
  socket exists to raise the emergency screen and to carry the caregiver's
  acknowledgement back.

Why a class instead of the old module-level ``set`` of queues: events are
published from three different threads (the paho MQTT network thread via the
bridge, FastAPI's threadpool for sync endpoints such as ``POST /ack``, and the
event loop itself). ``asyncio.Queue`` is not thread-safe. The Week 6 code called
``put_nowait`` straight from the threadpool; that stores the item but does not
wake the loop. It only worked because the threadpool wakes the loop anyway when
the request finishes. A publisher that is not a request (a background job, a
second worker) would leave listeners waiting until their next keepalive. Every
subscriber here remembers the loop it lives on and is fed through
``loop.call_soon_threadsafe``, which wakes that loop itself.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional

ALERT_EVENTS: FrozenSet[str] = frozenset({"alert", "alert_ack"})


@dataclass(eq=False)
class Subscription:
    queue: asyncio.Queue
    loop: asyncio.AbstractEventLoop
    kinds: Optional[FrozenSet[str]] = None   # None means every event type
    dropped: int = field(default=0)

    def wants(self, event: Dict[str, Any]) -> bool:
        return self.kinds is None or event.get("type") in self.kinds

    def _put(self, event: Dict[str, Any]) -> None:
        # Runs on the subscriber's own loop. A full queue means this client is
        # not keeping up: drop its oldest update rather than block everyone.
        if self.queue.full():
            try:
                self.queue.get_nowait()
                self.dropped += 1
            except asyncio.QueueEmpty:
                pass
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped += 1


class Hub:
    def __init__(self, maxsize: int = 50) -> None:
        self._maxsize = maxsize
        self._subs: set[Subscription] = set()
        self._lock = threading.Lock()

    def subscribe(self, kinds: Optional[FrozenSet[str]] = None) -> Subscription:
        """Registers a listener on the *current* event loop. Call from async code."""
        sub = Subscription(asyncio.Queue(maxsize=self._maxsize), asyncio.get_running_loop(), kinds)
        with self._lock:
            self._subs.add(sub)
        return sub

    def unsubscribe(self, sub: Subscription) -> None:
        with self._lock:
            self._subs.discard(sub)

    def publish(self, event: Dict[str, Any]) -> int:
        """Delivers ``event`` to every interested listener. Safe from any thread.

        Returns how many listeners it was handed to.
        """
        with self._lock:
            targets = [s for s in self._subs if s.wants(event)]
        delivered = 0
        for sub in targets:
            try:
                sub.loop.call_soon_threadsafe(sub._put, event)
                delivered += 1
            except RuntimeError:
                # That listener's loop has closed; it will never read again.
                self.unsubscribe(sub)
        return delivered

    def count(self, kinds: Optional[FrozenSet[str]] = None) -> int:
        with self._lock:
            if kinds is None:
                return len(self._subs)
            return sum(1 for s in self._subs if s.kinds == kinds)
