import json
import subprocess
import time

from synpu.metrics.models import DisplayStats

CONTROLLER_COMMAND = (
    "Get-CimInstance Win32_VideoController | "
    "Select-Object CurrentRefreshRate, CurrentHorizontalResolution, CurrentVerticalResolution | ConvertTo-Json"
)

MONITOR_COMMAND = (
    "Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorID | "
    "Select-Object ManufacturerName, UserFriendlyName | ConvertTo-Json"
)


def _as_list(payload) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    return []


def parse_controllers(payload) -> dict:
    result = {"refresh_hz": None, "width": None, "height": None}
    best_area = 0
    rates = []
    for item in _as_list(payload):
        if not isinstance(item, dict):
            continue
        try:
            rate = float(item.get("CurrentRefreshRate") or 0)
        except (TypeError, ValueError):
            rate = 0
        if rate > 0:
            rates.append(rate)
        try:
            width = int(item.get("CurrentHorizontalResolution") or 0)
            height = int(item.get("CurrentVerticalResolution") or 0)
        except (TypeError, ValueError):
            width = height = 0
        if width * height > best_area:
            best_area = width * height
            result["width"] = width or None
            result["height"] = height or None
    if rates:
        result["refresh_hz"] = max(rates)
    return result


def _decode_id(value) -> str | None:
    if not isinstance(value, list):
        return None
    try:
        text = "".join(chr(int(char)) for char in value if int(char) > 0).strip()
    except (TypeError, ValueError):
        return None
    return text or None


def parse_monitor_name(payload) -> str | None:
    for item in _as_list(payload):
        if not isinstance(item, dict):
            continue
        name = _decode_id(item.get("UserFriendlyName")) or _decode_id(item.get("ManufacturerName"))
        if name:
            return name
    return None


def parse_refresh_rate(payload) -> float | None:
    return parse_controllers(payload)["refresh_hz"]


class DisplayInfoReader:
    def __init__(self, ttl: float = 300.0):
        self._ttl = ttl
        self._value: DisplayStats | None = None
        self._at = float("-inf")

    def _run(self, command: str):
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except Exception:
            pass
        return None

    def read(self) -> DisplayStats | None:
        now = time.monotonic()
        if now - self._at < self._ttl:
            return self._value
        self._at = now
        controllers = self._run(CONTROLLER_COMMAND)
        if controllers is None:
            return self._value
        info = parse_controllers(controllers)
        name = parse_monitor_name(self._run(MONITOR_COMMAND))
        self._value = DisplayStats(
            refresh_hz=info["refresh_hz"],
            width=info["width"],
            height=info["height"],
            name=name,
        )
        return self._value
