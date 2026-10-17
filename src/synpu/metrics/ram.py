import json
import subprocess
import time

import psutil

from synpu.metrics.models import RamStats

RAM_COMMAND = (
    "Get-CimInstance Win32_PhysicalMemory | "
    "Select-Object Capacity, Speed, ConfiguredClockSpeed, SMBIOSMemoryType | ConvertTo-Json"
)

MEMORY_TYPES = {
    20: "DDR",
    21: "DDR2",
    24: "DDR3",
    26: "DDR4",
    34: "DDR5",
}


def read_ram(psutil_mod=psutil) -> RamStats:
    vm = psutil_mod.virtual_memory()
    return RamStats(
        used_mb=int(vm.used) // (1024 * 1024),
        total_mb=int(vm.total) // (1024 * 1024),
        percent=float(vm.percent),
    )


def parse_ram_info(payload) -> dict | None:
    items = payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])
    items = [item for item in items if isinstance(item, dict)]
    if not items:
        return None
    speeds = []
    types = []
    for item in items:
        try:
            configured = int(item.get("ConfiguredClockSpeed") or 0)
            nominal = int(item.get("Speed") or 0)
            speed = configured if configured > 0 else nominal
        except Exception:
            speed = 0
        if speed > 0:
            speeds.append(speed)
        try:
            mem_type = MEMORY_TYPES.get(int(item.get("SMBIOSMemoryType") or 0))
        except Exception:
            mem_type = None
        if mem_type:
            types.append(mem_type)
    return {
        "speed_mts": max(speeds) if speeds else None,
        "mem_type": types[0] if types else None,
        "module_count": len(items),
    }


class RamInfoReader:
    def __init__(self, ttl: float = 300.0):
        self._ttl = ttl
        self._value: dict | None = None
        self._at = float("-inf")

    def read(self) -> dict | None:
        now = time.monotonic()
        if now - self._at < self._ttl:
            return self._value
        self._at = now
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", RAM_COMMAND],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                self._value = parse_ram_info(json.loads(result.stdout))
        except Exception:
            pass
        return self._value
