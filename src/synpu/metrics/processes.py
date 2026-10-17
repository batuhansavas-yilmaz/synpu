import json
import re
import subprocess
import time

import psutil

from synpu.metrics.models import ProcessStats, TopProcesses

GPU_ENGINE_COMMAND = (
    "Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine | "
    "Where-Object { $_.Name -match 'engtype_3D' } | "
    "Select-Object Name, UtilizationPercentage | ConvertTo-Json"
)


def parse_gpu_engine(payload) -> dict[int, float]:
    items = payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])
    usage: dict[int, float] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("Name") or "")
        match = re.search(r"pid_(\d+)", name)
        if not match:
            continue
        try:
            pid = int(match.group(1))
            value = float(item.get("UtilizationPercentage") or 0)
        except (TypeError, ValueError):
            continue
        usage[pid] = usage.get(pid, 0.0) + value
    return usage


def _gpu_top() -> ProcessStats | None:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", GPU_ENGINE_COMMAND],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        usage = parse_gpu_engine(json.loads(result.stdout))
    except Exception:
        return None
    if not usage:
        return None
    pid, value = max(usage.items(), key=lambda item: item[1])
    if value <= 0:
        return None
    try:
        name = psutil.Process(pid).name()
    except Exception:
        return None
    if not name or name.strip().lower() in ("system idle process", "idle"):
        return None
    return ProcessStats(name=name, value=value)


class ProcessTopReader:
    def __init__(self, ttl: float = 2.0):
        self._ttl = ttl
        self._value: TopProcesses | None = None
        self._at = float("-inf")

    def read(self) -> TopProcesses | None:
        now = time.monotonic()
        if now - self._at < self._ttl:
            return self._value
        self._at = now
        try:
            best_cpu: tuple[str, float] | None = None
            best_ram: tuple[str, int] | None = None
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info.get("name") or "?"
                    if name.strip().lower() in ("system idle process", "idle"):
                        continue
                    cpu = proc.cpu_percent(None)
                    ram = proc.memory_info().rss
                except Exception:
                    continue
                if cpu > 0 and (best_cpu is None or cpu > best_cpu[1]):
                    best_cpu = (name, cpu)
                if best_ram is None or ram > best_ram[1]:
                    best_ram = (name, ram)
            self._value = TopProcesses(
                cpu=ProcessStats(name=best_cpu[0], value=best_cpu[1]) if best_cpu else None,
                ram=ProcessStats(name=best_ram[0], value=best_ram[1] / (1024 * 1024)) if best_ram else None,
                gpu=_gpu_top(),
            )
        except Exception:
            pass
        return self._value
