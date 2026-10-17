import json
import re
import subprocess
import time

SMART_COMMAND = r"""
$disks = @(Get-PhysicalDisk | ForEach-Object {
    $letters = (Get-Partition -DiskNumber $_.DeviceId -ErrorAction SilentlyContinue | Where-Object DriveLetter | ForEach-Object { "$($_.DriveLetter):" }) -join ','
    [pscustomobject]@{ model = $_.FriendlyName; letters = $letters }
})
$smart = @(Get-CimInstance -Namespace root/wmi -ClassName MSStorageDriver_ATAPISmartData -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{ instance = $_.InstanceName; bytes = @($_.VendorSpecific) }
})
@{ disks = $disks; smart = $smart } | ConvertTo-Json -Depth 5
"""

SMART_TTL_S = 60.0


def parse_smart_temp(raw: bytes) -> float | None:
    attrs: dict[int, bytes] = {}
    index = 2
    while index + 12 <= len(raw):
        attr_id = raw[index]
        if attr_id == 0:
            break
        attrs[attr_id] = raw[index + 5:index + 11]
        index += 12
    for key in (194, 190):
        raw_value = attrs.get(key)
        if raw_value and 0 < raw_value[0] < 120:
            return float(raw_value[0])
    return None


def _normalize(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _smart_model(instance: str) -> str:
    match = re.search(r"Ven_([^&\\]+)&Prod_([^\\]+)", instance, re.IGNORECASE)
    if match:
        return _normalize(match.group(1) + match.group(2))
    return _normalize(instance)


def parse_smart_payload(payload: dict) -> dict[str, float]:
    result: dict[str, float] = {}
    if not isinstance(payload, dict):
        return result
    disks = payload.get("disks") or []
    smart = payload.get("smart") or []
    if isinstance(disks, dict):
        disks = [disks]
    if isinstance(smart, dict):
        smart = [smart]
    temps: list[tuple[str, float]] = []
    for entry in smart:
        try:
            temp = parse_smart_temp(bytes(entry.get("bytes") or []))
            model = _smart_model(str(entry.get("instance", "")))
        except Exception:
            continue
        if temp is not None and model:
            temps.append((model, temp))
    for disk in disks:
        model = _normalize(str(disk.get("model", "")))
        if not model:
            continue
        for smart_model, temp in temps:
            if model in smart_model or smart_model in model:
                letters = str(disk.get("letters", ""))
                for letter in [part.strip() for part in letters.split(",") if part.strip()]:
                    result[letter] = temp
                break
    return result


class SmartTempReader:
    def __init__(self, ttl: float = SMART_TTL_S):
        self._ttl = ttl
        self._value: dict[str, float] = {}
        self._at = float("-inf")

    def read(self) -> dict[str, float]:
        now = time.monotonic()
        if now - self._at < self._ttl:
            return self._value
        self._at = now
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", SMART_COMMAND],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return self._value
            self._value = parse_smart_payload(json.loads(result.stdout))
        except Exception:
            pass
        return self._value
