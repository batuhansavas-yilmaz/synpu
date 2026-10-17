import socket
import threading
import time
from dataclasses import replace

from synpu.metrics.hardware_monitor import HardwareReading
from synpu.metrics.history import HistoryBuffer
from synpu.metrics.models import CpuStats, FanStat, FpsStats, Snapshot


class MetricsCollector:
    def __init__(self, cpu_source, gpu_source, ram_source, fps_source, hw_reader,
                 hostname=None, ttl=1.0, clock=time.monotonic,
                 storage_source=None, net_meter=None, disk_temp_source=None):
        self._cpu_source = cpu_source
        self._gpu_source = gpu_source
        self._ram_source = ram_source
        self._fps_source = fps_source
        self._hw_reader = hw_reader
        self._hostname = hostname or socket.gethostname()
        self._ttl = ttl
        self._clock = clock
        self._storage_source = storage_source
        self._net_meter = net_meter
        self._disk_temp_source = disk_temp_source
        self._cached: dict | None = None
        self._cached_at: float | None = None
        self._lock = threading.Lock()
        self.history = HistoryBuffer()

    def snapshot(self) -> dict:
        with self._lock:
            return self._snapshot_locked()

    def _snapshot_locked(self) -> dict:
        now = self._clock()
        if self._cached is not None and self._cached_at is not None and now - self._cached_at < self._ttl:
            return self._cached

        try:
            hw = self._hw_reader()
        except Exception:
            hw = HardwareReading()

        try:
            cpu = self._cpu_source()
        except Exception:
            cpu = CpuStats(usage_pct=None, temp_c=None)
        if hw.cpu_temp is not None:
            cpu = replace(cpu, temp_c=hw.cpu_temp)

        try:
            gpu = self._gpu_source()
        except Exception:
            gpu = None
        try:
            ram = self._ram_source()
        except Exception:
            ram = None
        try:
            fps = self._fps_source(now)
        except Exception:
            fps = FpsStats(app=None, value=None)

        storage = []
        if self._storage_source is not None:
            try:
                storage = list(self._storage_source() or [])
            except Exception:
                storage = []
            if storage and hw.disk_temps:
                temps = [temp for _, temp in hw.disk_temps]
                if len(temps) == len(storage):
                    storage = [replace(disk, temp_c=temp) for disk, temp in zip(storage, temps)]
                else:
                    storage[0] = replace(storage[0], temp_c=temps[0])
            if storage and self._disk_temp_source is not None:
                try:
                    smart_temps = self._disk_temp_source() or {}
                except Exception:
                    smart_temps = {}
                if smart_temps:
                    storage = [
                        replace(disk, temp_c=smart_temps[disk.label])
                        if disk.temp_c is None and disk.label in smart_temps else disk
                        for disk in storage
                    ]

        net = None
        if self._net_meter is not None:
            try:
                net = self._net_meter.update(now)
            except Exception:
                net = None

        fans = [FanStat(name=name, rpm=rpm) for name, rpm in hw.fans]

        snapshot = Snapshot(
            hostname=self._hostname,
            timestamp=time.time(),
            cpu=cpu,
            gpu=gpu,
            ram=ram,
            fps=fps,
            disks=storage,
            net=net,
            fans=fans,
        )
        self._cached = snapshot.to_dict()
        self._cached_at = now
        self.history.record(now, self._history_sample(snapshot.timestamp, cpu, gpu, ram, storage, net))
        return self._cached

    @staticmethod
    def _history_sample(ts, cpu, gpu, ram, disks, net) -> dict:
        system_disk = next((d for d in disks if d.is_system), disks[0] if disks else None)
        return {
            "ts": ts,
            "cpu_usage": cpu.usage_pct,
            "cpu_temp": cpu.temp_c,
            "cpu_freq": cpu.freq_mhz,
            "gpu_usage": gpu.usage_pct if gpu is not None else None,
            "gpu_temp": gpu.temp_c if gpu is not None else None,
            "gpu_freq": gpu.freq_mhz if gpu is not None else None,
            "gpu_power": gpu.power_w if gpu is not None else None,
            "ram_percent": ram.percent if ram is not None else None,
            "disk_percent": system_disk.percent if system_disk is not None else None,
            "disk_temp": system_disk.temp_c if system_disk is not None else None,
            "net_down": net.down_bps if net is not None else None,
            "net_up": net.up_bps if net is not None else None,
        }
