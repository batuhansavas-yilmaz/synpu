import json
import subprocess
import time

from synpu.metrics.models import MotherboardStats

BOARD_COMMAND = (
    "Get-CimInstance Win32_BaseBoard | "
    "Select-Object Manufacturer, Product | ConvertTo-Json"
)


def parse_motherboard(payload) -> MotherboardStats | None:
    items = payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])
    for item in items:
        if not isinstance(item, dict):
            continue
        vendor = str(item.get("Manufacturer") or "").strip() or None
        model = str(item.get("Product") or "").strip() or None
        if vendor or model:
            return MotherboardStats(vendor=vendor, model=model)
    return None


class MotherboardReader:
    def __init__(self, ttl: float = 300.0):
        self._ttl = ttl
        self._value: MotherboardStats | None = None
        self._at = float("-inf")

    def read(self) -> MotherboardStats | None:
        now = time.monotonic()
        if now - self._at < self._ttl:
            return self._value
        self._at = now
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", BOARD_COMMAND],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                self._value = parse_motherboard(json.loads(result.stdout))
        except Exception:
            pass
        return self._value
