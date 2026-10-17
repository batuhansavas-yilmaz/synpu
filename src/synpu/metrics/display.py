import json
import subprocess
import time

DISPLAY_COMMAND = (
    "Get-CimInstance Win32_VideoController | "
    "Select-Object CurrentRefreshRate | ConvertTo-Json"
)


def parse_refresh_rate(payload) -> float | None:
    items = payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])
    rates = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            rate = float(item.get("CurrentRefreshRate") or 0)
        except (TypeError, ValueError):
            rate = 0
        if rate > 0:
            rates.append(rate)
    return max(rates) if rates else None


class DisplayInfoReader:
    def __init__(self, ttl: float = 300.0):
        self._ttl = ttl
        self._value: float | None = None
        self._at = float("-inf")

    def read(self) -> float | None:
        now = time.monotonic()
        if now - self._at < self._ttl:
            return self._value
        self._at = now
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", DISPLAY_COMMAND],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                self._value = parse_refresh_rate(json.loads(result.stdout))
        except Exception:
            pass
        return self._value
