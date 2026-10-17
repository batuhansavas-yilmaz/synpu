import threading
from collections import deque


class HistoryBuffer:
    def __init__(self, max_seconds: int = 3600, interval: float = 1.0, minute_max: int = 2880):
        self._interval = interval
        self._raw: deque[dict] = deque(maxlen=max_seconds)
        self._minute: deque[dict] = deque(maxlen=minute_max)
        self._last_at: float | None = None
        self._window_start: float | None = None
        self._sums: dict[str, float] = {}
        self._counts: dict[str, int] = {}
        self._last_sample_ts: float | None = None
        self._lock = threading.Lock()

    def record(self, now: float, sample: dict) -> None:
        with self._lock:
            if self._last_at is not None and now - self._last_at < self._interval:
                return
            self._last_at = now
            self._raw.append(sample)
            if self._window_start is None:
                self._window_start = now
            for key, value in sample.items():
                if key == "ts" or value is None:
                    continue
                self._sums[key] = self._sums.get(key, 0.0) + float(value)
                self._counts[key] = self._counts.get(key, 0) + 1
            self._last_sample_ts = sample.get("ts", now)
            if now - self._window_start >= 60.0:
                if self._counts:
                    aggregate: dict = {"ts": self._last_sample_ts}
                    for key in self._sums:
                        aggregate[key] = self._sums[key] / self._counts[key]
                    for key in sample:
                        if key != "ts" and key not in aggregate:
                            aggregate[key] = None
                    self._minute.append(aggregate)
                self._window_start = now
                self._sums = {}
                self._counts = {}

    def series(self, minutes: int, max_points: int = 180) -> list[dict]:
        with self._lock:
            if minutes <= 60:
                source = list(self._raw)
            else:
                source = list(self._minute) or list(self._raw)
        if not source:
            return []
        cutoff = source[-1]["ts"] - minutes * 60
        items = [s for s in source if s["ts"] >= cutoff]
        if len(items) > max_points:
            stride = max(1, len(items) // max_points)
            items = items[::stride]
        return items
