from synpu.metrics.hardware_monitor import CpuTempReader, pick_cpu_temp


def test_pick_prefers_package():
    sensors = [("CPU Core #1", 60.0), ("CPU Package", 55.0)]
    assert pick_cpu_temp(sensors) == 55.0


def test_pick_core_max_when_no_package():
    sensors = [("CPU Core #1", 61.0), ("CPU Core #2", 58.0)]
    assert pick_cpu_temp(sensors) == 61.0


def test_pick_returns_none_when_empty():
    assert pick_cpu_temp([]) is None


def test_read_falls_back_to_wmi(monkeypatch):
    reader = CpuTempReader()
    monkeypatch.setattr(reader, "_try_lhm", lambda: None)
    monkeypatch.setattr(reader, "_try_wmi", lambda: 47.5)
    assert reader.read() == 47.5


def test_read_none_when_all_fail(monkeypatch):
    reader = CpuTempReader()
    monkeypatch.setattr(reader, "_try_lhm", lambda: None)
    monkeypatch.setattr(reader, "_try_wmi", lambda: None)
    assert reader.read() is None
