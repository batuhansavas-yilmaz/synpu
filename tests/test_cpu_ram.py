from synpu.metrics.cpu import read_cpu
from synpu.metrics.ram import read_ram


class FakeVm:
    used = 100 * 1024 * 1024
    total = 400 * 1024 * 1024
    percent = 25.0


class FakeFreq:
    current = 4200.0


class FakePsutil:
    def cpu_percent(self, interval=None):
        return 12.5

    def virtual_memory(self):
        return FakeVm()

    def cpu_freq(self):
        return FakeFreq()


def test_read_cpu():
    c = read_cpu(FakePsutil())
    assert c.usage_pct == 12.5 and c.temp_c is None
    assert c.freq_mhz == 4200.0


def test_read_ram():
    r = read_ram(FakePsutil())
    assert (r.used_mb, r.total_mb, r.percent) == (100, 400, 25.0)
