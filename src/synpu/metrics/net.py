import math

import psutil

from synpu.metrics.models import NetStats


class NetSpeedMeter:
    def __init__(self, tau: float = 2.0):
        self._last: tuple[int, int] | None = None
        self._last_at: float | None = None
        self._tau = tau
        self._down = 0.0
        self._up = 0.0

    def update(self, now: float, counters=None) -> NetStats | None:
        try:
            c = counters if counters is not None else psutil.net_io_counters()
            recv, sent = int(c.bytes_recv), int(c.bytes_sent)
        except Exception:
            return None
        prev, prev_at = self._last, self._last_at
        self._last, self._last_at = (recv, sent), now
        if prev is None or prev_at is None:
            return NetStats(down_bps=0.0, up_bps=0.0)
        dt = now - prev_at
        if dt <= 0:
            return None
        instant_down = max(0.0, (recv - prev[0]) / dt)
        instant_up = max(0.0, (sent - prev[1]) / dt)
        alpha = 1.0 if self._tau <= 0 else 1.0 - math.exp(-dt / self._tau)
        self._down += alpha * (instant_down - self._down)
        self._up += alpha * (instant_up - self._up)
        return NetStats(down_bps=self._down, up_bps=self._up)
