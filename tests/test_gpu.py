from synpu.metrics.gpu import read_gpu


class FakeNVMLError(Exception):
    pass


class FakeUtilization:
    gpu = 15


class FakeMemory:
    used = 1650 * 1024 * 1024
    total = 12282 * 1024 * 1024


class FakeNvml:
    NVMLError = FakeNVMLError
    NVML_TEMPERATURE_GPU = 0

    def __init__(self, fail_init=False, fail_power=False):
        self.fail_init = fail_init
        self.fail_power = fail_power
        self.shutdown_called = False

    def nvmlInit(self):
        if self.fail_init:
            raise FakeNVMLError("no driver")

    def nvmlShutdown(self):
        self.shutdown_called = True

    def nvmlDeviceGetHandleByIndex(self, index):
        return f"gpu{index}"

    def nvmlDeviceGetName(self, handle):
        return b"NVIDIA GeForce RTX 4070 SUPER"

    def nvmlDeviceGetUtilizationRates(self, handle):
        return FakeUtilization()

    def nvmlDeviceGetTemperature(self, handle, sensor):
        return 37

    def nvmlDeviceGetMemoryInfo(self, handle):
        return FakeMemory()

    def nvmlDeviceGetPowerUsage(self, handle):
        if self.fail_power:
            raise FakeNVMLError("not supported")
        return 11660


def test_read_gpu_returns_fields():
    g = read_gpu(FakeNvml())
    assert g.name == "NVIDIA GeForce RTX 4070 SUPER"
    assert g.usage_pct == 15.0
    assert g.temp_c == 37.0
    assert g.vram_used_mb == 1650
    assert g.vram_total_mb == 12282
    assert round(g.power_w, 2) == 11.66


def test_read_gpu_no_device_returns_none():
    assert read_gpu(FakeNvml(fail_init=True)) is None


def test_power_unsupported_yields_none_power():
    g = read_gpu(FakeNvml(fail_power=True))
    assert g is not None
    assert g.power_w is None
    assert g.usage_pct == 15.0
