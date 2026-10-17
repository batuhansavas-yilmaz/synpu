import psutil

from synpu.metrics.models import NetStats


class NetSpeedMeter:
    def __init__(self):
        self._last: tuple[int, int] | None = None
        self._last_at: float | None = None

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
        return NetStats(
            down_bps=max(0.0, (recv - prev[0]) / dt),
            up_bps=max(0.0, (sent - prev[1]) / dt),
        )
