from synpu.metrics.collector import MetricsCollector
from synpu.metrics.models import CpuStats, FpsStats, GpuStats, RamStats


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def _collector(clock=None, counters=None, gpu_source=None, ram_source=None):
    clock = clock or FakeClock()
    counters = counters if counters is not None else {}

    def bump(name):
        counters[name] = counters.get(name, 0) + 1

    def cpu():
        bump("cpu")
        return CpuStats(usage_pct=10.0, temp_c=None)

    def gpu():
        bump("gpu")
        if gpu_source is not None:
            return gpu_source()
        return GpuStats("RTX 4070 SUPER", 5.0, 40.0, 100, 1000, 50.0)

    def ram():
        bump("ram")
        if ram_source is not None:
            return ram_source()
        return RamStats(100, 200, 50.0)

    def fps(now):
        bump("fps")
        return FpsStats("game.exe", 60.0)

    def temp():
        bump("temp")
        return 55.0

    col = MetricsCollector(cpu, gpu, ram, fps, temp, hostname="pc", ttl=1.0, clock=clock)
    return col, counters, clock


def test_snapshot_schema_and_hostname():
    col, _, _ = _collector()
    d = col.snapshot()
    assert set(d) == {"hostname", "timestamp", "cpu", "gpu", "ram", "fps"}
    assert d["hostname"] == "pc"
    assert d["cpu"] == {"usage_pct": 10.0, "temp_c": 55.0}
    assert d["gpu"]["name"] == "RTX 4070 SUPER"
    assert d["ram"]["percent"] == 50.0
    assert d["fps"] == {"app": "game.exe", "value": 60.0}


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
