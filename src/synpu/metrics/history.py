import json
import os
import threading
import time
from collections import deque
from pathlib import Path


class HistoryBuffer:
    def __init__(self, max_seconds: int = 3600, interval: float = 1.0, minute_max: int = 2880,
                 path: Path | None = None, save_interval: float = 20.0):
        self._interval = interval
        self._raw: deque[dict] = deque(maxlen=max_seconds)
        self._minute: deque[dict] = deque(maxlen=minute_max)
        self._last_at: float | None = None
        self._window_start: float | None = None
        self._sums: dict[str, float] = {}
        self._counts: dict[str, int] = {}
        self._last_sample_ts: float | None = None
        self._path = Path(path) if path is not None else None
        self._save_interval = save_interval
        self._last_save = 0.0
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if self._path is None:
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return
        raw = data.get("raw") or []
        minute = data.get("minute") or []
        for sample in raw[-self._raw.maxlen:]:
            if isinstance(sample, dict) and "ts" in sample:
                self._raw.append(sample)
        for sample in minute[-self._minute.maxlen:]:
            if isinstance(sample, dict) and "ts" in sample:
                self._minute.append(sample)
        self._prune(time.time())

    def _prune(self, now_ts: float) -> None:
        raw_cutoff = now_ts - (self._raw.maxlen or 3600)
        minute_cutoff = now_ts - (self._minute.maxlen or 2880) * 60
        while self._raw and float(self._raw[0].get("ts", 0)) < raw_cutoff:
            self._raw.popleft()
        while self._minute and float(self._minute[0].get("ts", 0)) < minute_cutoff:
            self._minute.popleft()

    def _save_locked(self) -> None:
        if self._path is None:
            return
        try:
            self._prune(time.time())
            payload = {
                "saved_at": time.time(),
                "raw": list(self._raw),
                "minute": list(self._minute),
            }
            tmp = self._path.with_suffix(".tmp")
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            os.replace(tmp, self._path)
        except Exception:
            pass

    def flush(self) -> None:
        with self._lock:
            self._save_locked()

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
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    continue
                self._sums[key] = self._sums.get(key, 0.0) + number
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
            monotonic_now = time.monotonic()
            if self._path is not None and monotonic_now - self._last_save >= self._save_interval:
                self._last_save = monotonic_now
                self._save_locked()

    def series(self, minutes: int, max_points: int = 180) -> list[dict]:
        with self._lock:
            if minutes <= 60:
                source = list(self._raw)
            else:
                source = list(self._minute)
                if source:
                    last_minute_ts = source[-1].get("ts", 0)
                    source.extend(
                        sample for sample in self._raw
                        if sample.get("ts", 0) > last_minute_ts
                    )
                else:
                    source = list(self._raw)
        if not source:
            return []
        cutoff = source[-1]["ts"] - minutes * 60
        items = [s for s in source if s["ts"] >= cutoff]
        if len(items) > max_points:
            stride = max(1, len(items) // max_points)
            items = items[::stride]
        return items
