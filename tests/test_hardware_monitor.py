from synpu.metrics.hardware_monitor import (
    CpuTempReader,
    HardwareReading,
    _scan_computer,
    pick_cpu_temp,
)


class FakeSensor:
    def __init__(self, sensor_type, name, value):
        self.SensorType = sensor_type
        self.Name = name
        self.Value = value


class FakeHardware:
    def __init__(self, hardware_type, name, sensors, subs=()):
        self.HardwareType = hardware_type
        self.Name = name
        self.Sensors = sensors
        self.SubHardware = list(subs)

    def Update(self):
        pass


class FakeComputer:
    def __init__(self, hardware):
        self.Hardware = hardware


def test_pick_prefers_package():
    sensors = [("CPU Core #1", 60.0), ("CPU Package", 55.0)]
    assert pick_cpu_temp(sensors) == 55.0


def test_pick_core_max_when_no_package():
    sensors = [("CPU Core #1", 61.0), ("CPU Core #2", 58.0)]
    assert pick_cpu_temp(sensors) == 61.0


def test_pick_returns_none_when_empty():
    assert pick_cpu_temp([]) is None


def test_scan_collects_cpu_fans_and_disks():
    cpu = FakeHardware("Cpu", "i5", [
        FakeSensor("Temperature", "CPU Package", 45.0),
        FakeSensor("Clock", "P-Core #1", 4200.0),
        FakeSensor("Clock", "P-Core #2", 4400.0),
        FakeSensor("Clock", "Bus Speed", 100.0),
    ])
    superio = FakeHardware("SuperIO", "Nuvoton", [FakeSensor("Fan", "CPU Fan", 1200.0)])
    board = FakeHardware("Motherboard", "Board", [], subs=[superio])
    ssd = FakeHardware("Storage", "Samsung SSD", [FakeSensor("Temperature", "Temperature", 38.0)])
    reading = _scan_computer(FakeComputer([cpu, board, ssd]))
    assert reading.cpu_temp == 45.0
    assert reading.fans == (("CPU Fan", 1200.0),)
    assert reading.disk_temps == (("Samsung SSD", 38.0),)
    assert reading.cpu_clock_mhz == 4300.0


def test_read_falls_back_to_wmi(monkeypatch):
    reader = CpuTempReader()
    monkeypatch.setattr(reader, "_try_lhm", lambda: None)
    monkeypatch.setattr(reader, "_try_wmi", lambda: 47.5)
    assert reader.read().cpu_temp == 47.5


def test_read_none_when_all_fail(monkeypatch):
    reader = CpuTempReader()
    monkeypatch.setattr(reader, "_try_lhm", lambda: None)
    monkeypatch.setattr(reader, "_try_wmi", lambda: None)
    assert reader.read().cpu_temp is None


def test_read_prefers_lhm(monkeypatch):
    reader = CpuTempReader()
    wmi_calls = []
    monkeypatch.setattr(reader, "_try_lhm", lambda: HardwareReading(cpu_temp=50.0))
    monkeypatch.setattr(reader, "_try_wmi", lambda: wmi_calls.append(1) or 30.0)
    assert reader.read().cpu_temp == 50.0
    assert wmi_calls == []


def test_wmi_result_cached(monkeypatch):
    reader = CpuTempReader()
    calls = []
    monkeypatch.setattr(reader, "_try_lhm", lambda: None)
    monkeypatch.setattr(reader, "_try_wmi", lambda: calls.append(1) or 47.5)
    assert reader.read().cpu_temp == 47.5
    assert reader.read().cpu_temp == 47.5
    assert len(calls) == 1
