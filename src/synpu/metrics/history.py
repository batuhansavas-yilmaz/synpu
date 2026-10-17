import threading
from collections import deque


class HistoryBuffer:
    def __init__(self, max_seconds: int = 3600, interval: float = 1.0):
        self._interval = interval
        self._samples: deque[dict] = deque(maxlen=max_seconds)
        self._last_at: float | None = None
        self._lock = threading.Lock()

    def record(self, now: float, sample: dict) -> None:
        with self._lock:
            if self._last_at is not None and now - self._last_at < self._interval:
                return
            self._last_at = now
            self._samples.append(sample)

    def series(self, minutes: int, max_points: int = 180) -> list[dict]:
        with self._lock:
            items = list(self._samples)
        if not items:
            return []
        cutoff = items[-1]["ts"] - minutes * 60
        items = [s for s in items if s["ts"] >= cutoff]
        if len(items) > max_points:
            stride = max(1, len(items) // max_points)
            items = items[::stride]
        return items
