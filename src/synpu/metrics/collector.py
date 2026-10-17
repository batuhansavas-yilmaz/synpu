import socket
import threading
import time

from synpu.metrics.models import CpuStats, FpsStats, Snapshot


class MetricsCollector:
    def __init__(self, cpu_source, gpu_source, ram_source, fps_source, temp_reader,
                 hostname=None, ttl=1.0, clock=time.monotonic):
        self._cpu_source = cpu_source
        self._gpu_source = gpu_source
        self._ram_source = ram_source
        self._fps_source = fps_source
        self._temp_reader = temp_reader
        self._hostname = hostname or socket.gethostname()
        self._ttl = ttl
        self._clock = clock
        self._cached: dict | None = None
        self._cached_at: float | None = None
        self._lock = threading.Lock()

    def snapshot(self) -> dict:
        with self._lock:
            return self._snapshot_locked()

    def _snapshot_locked(self) -> dict:
        now = self._clock()
        if self._cached is not None and self._cached_at is not None and now - self._cached_at < self._ttl:
            return self._cached

        try:
            cpu = self._cpu_source()
        except Exception:
            cpu = CpuStats(usage_pct=None, temp_c=None)
        try:
            temp = self._temp_reader()
        except Exception:
            temp = None
        if temp is not None:
            cpu = CpuStats(usage_pct=cpu.usage_pct, temp_c=temp)

        try:
            gpu = self._gpu_source()
        except Exception:
            gpu = None
        try:
            ram = self._ram_source()
        except Exception:
            ram = None
        try:
            fps = self._fps_source(now)
        except Exception:
            fps = FpsStats(app=None, value=None)

        snapshot = Snapshot(
            hostname=self._hostname,
            timestamp=time.time(),
            cpu=cpu,
            gpu=gpu,
            ram=ram,
            fps=fps,
        )
        self._cached = snapshot.to_dict()
        self._cached_at = now
        return self._cached
