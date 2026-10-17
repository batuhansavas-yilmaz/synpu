from synpu.metrics.collector import MetricsCollector, collect_gpu_candidates, pick_active_gpu
from synpu.metrics.hardware_monitor import HardwareReading
from synpu.metrics.models import (
    BatteryStats, CpuStats, DisplayStats, FpsStats, GpuStats, MotherboardStats, NetStats,
    ProcessStats, RamStats, StorageStats, TopProcesses,
)


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


def _collector(clock=None, counters=None, gpu_source=None, ram_source=None, disk_temp_source=None, gpus=(), ram_info_source=None,
               battery_source=None, uptime_source=None, disk_io_source=None, disk_map_source=None, display_source=None,
               motherboard_source=None, top_source=None, wifi_source=None, isp_source=None):
    clock = clock or FakeClock()
    counters = counters if counters is not None else {}

    def bump(name):
        counters[name] = counters.get(name, 0) + 1

    def cpu():
        bump("cpu")
        return CpuStats(usage_pct=10.0, temp_c=None, freq_mhz=4200.0, name="i5-13500",
                        cores=(50.0, 60.0))

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
        ram_info_source=ram_info_source,
        battery_source=battery_source,
        uptime_source=uptime_source,
        disk_io_source=disk_io_source,
        disk_map_source=disk_map_source,
        display_source=display_source,
        motherboard_source=motherboard_source,
        top_source=top_source,
        wifi_source=wifi_source,
        isp_source=isp_source,
    )
    return col, counters, clock


def test_snapshot_schema_and_hostname():
    col, _, _ = _collector()
    d = col.snapshot()
    assert set(d) == {"hostname", "timestamp", "cpu", "gpu", "ram", "fps", "disks", "net", "fans", "gpus",
                      "battery", "uptime_s", "display", "motherboard", "top", "isp", "wifi"}
    assert d["cpu"]["cores"] == (50.0, 60.0)
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
         "temp_c": 38.0, "is_system": True, "read_bps": None, "write_bps": None},
        {"label": "D:", "used_mb": 50, "total_mb": 200, "percent": 25.0,
         "temp_c": None, "is_system": False, "read_bps": None, "write_bps": None},
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
    sample = col.history.series(60)[0]
    assert sample["gpu_RTX4070SUPER_usage"] == 5.0
    assert sample["gpu_IntelRUHDGraphics770_usage"] == 40.0


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


def test_ram_info_enrichment():
    col, _, _ = _collector(ram_info_source=lambda: {"speed_mts": 6000, "mem_type": "DDR5", "module_count": 2})
    d = col.snapshot()
    assert d["ram"]["speed_mts"] == 6000
    assert d["ram"]["mem_type"] == "DDR5"
    assert d["ram"]["module_count"] == 2


def test_disk_io_enrichment():
    col, _, _ = _collector(
        disk_io_source=lambda now: {"PhysicalDrive1": (1_048_576.0, 524_288.0)},
        disk_map_source=lambda: {"C:": "PhysicalDrive1"},
    )
    d = col.snapshot()
    assert d["disks"][0]["read_bps"] == 1_048_576.0
    assert d["disks"][0]["write_bps"] == 524_288.0
    assert d["disks"][1]["read_bps"] is None


def test_battery_uptime_display():
    col, _, _ = _collector(
        battery_source=lambda: BatteryStats(percent=77.0, plugged=True),
        uptime_source=lambda: 3661,
        display_source=lambda: DisplayStats(refresh_hz=144.0, width=2560, height=1440, name="Test Monitor"),
    )
    d = col.snapshot()
    assert d["battery"] == {"percent": 77.0, "plugged": True}
    assert d["uptime_s"] == 3661
    assert d["display"] == {"refresh_hz": 144.0, "width": 2560, "height": 1440, "name": "Test Monitor"}


def test_network_meta():
    col, _, _ = _collector(wifi_source=lambda: "EvWiFi", isp_source=lambda: "Turk Telekom")
    d = col.snapshot()
    assert d["isp"] == "Turk Telekom"
    assert d["wifi"] == "EvWiFi"


def test_motherboard():
    col, _, _ = _collector(motherboard_source=lambda: MotherboardStats("ASUS", "PRIME B660M-K D4"))
    d = col.snapshot()
    assert d["motherboard"] == {"vendor": "ASUS", "model": "PRIME B660M-K D4"}


def test_top_processes():
    col, _, _ = _collector(top_source=lambda: TopProcesses(
        cpu=ProcessStats("chrome.exe", 12.5),
        ram=ProcessStats("chrome.exe", 800.0),
    ))
    d = col.snapshot()
    assert d["top"] == {
        "cpu": {"name": "chrome.exe", "value": 12.5},
        "ram": {"name": "chrome.exe", "value": 800.0},
        "gpu": None,
    }


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
    assert samples[0]["ram_used_mb"] == 100
    assert samples[0]["disk_C_percent"] == 25.0
    assert samples[0]["disk_D_percent"] == 25.0
    assert samples[0]["disk_C_temp"] == 38.0
    assert samples[0]["cpu_core_1"] == 50.0
    assert samples[0]["cpu_core_2"] == 60.0
    assert samples[0]["disk_temp"] == 38.0
