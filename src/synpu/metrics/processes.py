import time

import psutil

from synpu.metrics.models import ProcessStats, TopProcesses


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
            )
        except Exception:
            pass
        return self._value
