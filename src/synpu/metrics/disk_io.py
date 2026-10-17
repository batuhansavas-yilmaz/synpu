import json
import subprocess
import time

import psutil

PARTITION_COMMAND = (
    "Get-Partition | Where-Object DriveLetter | "
    "ForEach-Object { [pscustomobject]@{ letter = \"$($_.DriveLetter):\"; disk = $_.DiskNumber } } | ConvertTo-Json"
)


def parse_partition_map(payload) -> dict[str, str]:
    items = payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])
    result: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        letter = str(item.get("letter") or "")
        try:
            disk = int(item.get("disk"))
        except (TypeError, ValueError):
            continue
        if letter:
            result[letter] = f"PhysicalDrive{disk}"
    return result


class DiskDeviceMap:
    def __init__(self, ttl: float = 300.0):
        self._ttl = ttl
        self._value: dict[str, str] = {}
        self._at = float("-inf")

    def read(self) -> dict[str, str]:
        now = time.monotonic()
        if now - self._at < self._ttl:
            return self._value
        self._at = now
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", PARTITION_COMMAND],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                self._value = parse_partition_map(json.loads(result.stdout))
        except Exception:
            pass
        return self._value


class DiskSpeedMeter:
    def __init__(self):
        self._last = None
        self._last_at: float | None = None

    def update(self, now: float, counters=None) -> dict[str, tuple[float, float]]:
        try:
            current = counters if counters is not None else psutil.disk_io_counters(perdisk=True)
        except Exception:
            return {}
        result: dict[str, tuple[float, float]] = {}
        if self._last is not None and self._last_at is not None:
            dt = now - self._last_at
            if dt > 0:
                for device, io in current.items():
                    prev = self._last.get(device)
                    if prev is None:
                        continue
                    read = max(0.0, (io.read_bytes - prev.read_bytes) / dt)
                    write = max(0.0, (io.write_bytes - prev.write_bytes) / dt)
                    result[device] = (read, write)
        self._last = dict(current)
        self._last_at = now
        return result
