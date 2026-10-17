from synpu.metrics.disk_io import DiskSpeedMeter, parse_partition_map


class FakeIo:
    def __init__(self, read, write):
        self.read_bytes = read
        self.write_bytes = write


def test_parse_partition_map_single():
    assert parse_partition_map({"letter": "C:", "disk": 1}) == {"C:": "PhysicalDrive1"}


def test_parse_partition_map_list():
    payload = [{"letter": "C:", "disk": 1}, {"letter": "D:", "disk": 0}]
    assert parse_partition_map(payload) == {"C:": "PhysicalDrive1", "D:": "PhysicalDrive0"}


def test_disk_speed_meter_delta():
    meter = DiskSpeedMeter()
    assert meter.update(100.0, {"PhysicalDrive0": FakeIo(1000, 2000)}) == {}
    speeds = meter.update(102.0, {"PhysicalDrive0": FakeIo(3148, 4048)})
    assert speeds["PhysicalDrive0"] == ((3148 - 1000) / 2.0, (4048 - 2000) / 2.0)
