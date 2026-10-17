from synpu.metrics.collector import MetricsCollector, collect_gpu_candidates, pick_active_gpu
from synpu.metrics.hardware_monitor import HardwareReading
from synpu.metrics.models import CpuStats, FpsStats, GpuStats, NetStats, RamStats, StorageStats


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


class FakeNet:
    def update(self, now):
        return NetStats(down_bps=1_000_000.0, up_bps=200_000.0)


def _collector(clock=None, counters=None, gpu_source=None, ram_source=None, disk_temp_source=None, gpus=()):
    clock = clock or FakeClock()
    counters = counters if counters is not None else {}

    def bump(name):
        counters[name] = counters.get(name, 0) + 1

    def cpu():
        bump("cpu")
        return CpuStats(usage_pct=10.0, temp_c=None, freq_mhz=4200.0, name="i5-13500")

    def gpu():
        bump("gpu")
        if gpu_source is not None:
            return gpu_source()
        return GpuStats("RTX 4070 SUPER", 5.0, 40.0, 100, 1000, 50.0, 2610.0)

    def ram():
        bump("ram")
        if ram_source is not None:
            return ram_source()
        return RamStats(100, 200, 50.0)

    def fps(now):
        bump("fps")
        return FpsStats("game.exe", 60.0)

    def hw():
        bump("hw")
        return HardwareReading(
            cpu_temp=55.0,
            fans=(("CPU Fan", 1200.0), ("Ağ Fan", 800.0)),
            disk_temps=(("Samsung SSD", 38.0),),
            cpu_clock_mhz=4300.0,
            gpus=tuple(gpus),
        )

    def storage():
        bump("storage")
        return [
            StorageStats(label="C:", used_mb=100, total_mb=400, percent=25.0, is_system=True),
            StorageStats(label="D:", used_mb=50, total_mb=200, percent=25.0),
        ]

    col = MetricsCollector(
        cpu, gpu, ram, fps, hw,
        hostname="pc", ttl=1.0, clock=clock,
        storage_source=storage, net_meter=FakeNet(),
        disk_temp_source=disk_temp_source,
    )
    return col, counters, clock


def test_snapshot_schema_and_hostname():
    col, _, _ = _collector()
    d = col.snapshot()
    assert set(d) == {"hostname", "timestamp", "cpu", "gpu", "ram", "fps", "disks", "net", "fans", "gpus"}
    assert d["hostname"] == "pc"
    assert d["cpu"]["usage_pct"] == 10.0
    assert d["cpu"]["temp_c"] == 55.0
    assert d["cpu"]["freq_mhz"] == 4300.0
    assert d["cpu"]["name"] == "i5-13500"
    assert d["gpu"]["name"] == "RTX 4070 SUPER"
    assert d["gpu"]["freq_mhz"] == 2610.0
    assert d["ram"]["percent"] == 50.0
    assert d["fps"] == {"app": "game.exe", "value": 60.0}
    assert d["disks"] == [
        {"label": "C:", "used_mb": 100, "total_mb": 400, "percent": 25.0,
         "temp_c": 38.0, "is_system": True},
        {"label": "D:", "used_mb": 50, "total_mb": 200, "percent": 25.0,
         "temp_c": None, "is_system": False},
    ]
    assert d["net"] == {"down_bps": 1_000_000.0, "up_bps": 200_000.0}
    assert d["fans"] == [
        {"name": "CPU Fan", "rpm": 1200.0},
        {"name": "Ağ Fan", "rpm": 800.0},
    ]
    assert [g["name"] for g in d["gpus"]] == ["RTX 4070 SUPER"]


def test_snapshot_cached_within_ttl():
    col, counters, clock = _collector()
    col.snapshot()
    col.snapshot()
    assert counters["cpu"] == 1
    clock.advance(1.5)
    col.snapshot()
    assert counters["cpu"] == 2


def test_source_failure_isolated():
    def boom():
        raise RuntimeError("nvml dead")

    col, _, _ = _collector(gpu_source=boom)
    d = col.snapshot()
    assert d["gpu"] is None
    assert d["cpu"]["usage_pct"] == 10.0
    assert d["ram"]["percent"] == 50.0


def test_ram_failure_yields_null():
    def boom():
        raise RuntimeError("psutil dead")

    col, _, _ = _collector(ram_source=boom)
    d = col.snapshot()
    assert d["ram"] is None
    assert d["cpu"]["usage_pct"] == 10.0


def test_disk_temp_smart_fallback():
    col, _, _ = _collector(disk_temp_source=lambda: {"D:": 33.0})
    d = col.snapshot()
    assert d["disks"][0]["temp_c"] == 38.0
    assert d["disks"][1]["temp_c"] == 33.0


def test_dual_gpu_both_listed_and_active_is_busiest():
    intel = GpuStats("Intel(R) UHD Graphics 770", 40.0, 45.0, 128, 1024, None, 1550.0)
    col, _, _ = _collector(gpus=(intel,))
    d = col.snapshot()
    assert [g["name"] for g in d["gpus"]] == ["RTX 4070 SUPER", "Intel(R) UHD Graphics 770"]
    assert d["gpu"]["name"] == "Intel(R) UHD Graphics 770"


def test_pick_active_prefers_busier_gpu():
    nv = GpuStats("RTX", 70.0, 60.0, 100, 1000, 100.0, 2500.0)
    ig = GpuStats("Intel", 5.0, 40.0, 50, 500, None, 1200.0)
    assert pick_active_gpu(nv, (ig,)).name == "RTX"
    idle = GpuStats("RTX", 0.0, None, None, None, None, None)
    busy = GpuStats("Intel", 12.0, None, None, None, None, None)
    assert pick_active_gpu(idle, (busy,)).name == "Intel"


def test_pick_active_merges_duplicate_names():
    nv = GpuStats("NVIDIA GeForce RTX 4070 SUPER", None, 40.0, 100, 1000, None, None)
    duplicate = GpuStats("NVIDIA GeForce RTX 4070 SUPER", 30.0, 41.0, 200, 1000, 50.0, 2500.0)
    merged = pick_active_gpu(nv, (duplicate,))
    assert merged.usage_pct == 30.0
    assert merged.temp_c == 40.0
    assert merged.freq_mhz == 2500.0


def test_pick_active_none_cases():
    assert pick_active_gpu(None, ()) is None
    intel = GpuStats("Intel", 8.0, None, None, None, None, None)
    assert pick_active_gpu(None, (intel,)).name == "Intel"


def test_history_records_samples():
    col, _, clock = _collector()
    col.snapshot()
    clock.advance(1.5)
    col.snapshot()
    samples = col.history.series(60)
    assert len(samples) == 2
    assert samples[0]["cpu_usage"] == 10.0
    assert samples[0]["cpu_temp"] == 55.0
    assert samples[0]["gpu_usage"] == 5.0
    assert samples[0]["ram_percent"] == 50.0
    assert samples[0]["disk_temp"] == 38.0
