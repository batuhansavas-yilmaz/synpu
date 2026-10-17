from synpu.metrics.battery import read_battery
from synpu.metrics.display import parse_refresh_rate


class FakeBattery:
    percent = 88.0
    power_plugged = False


class FakePsutilBattery:
    def sensors_battery(self):
        return FakeBattery()


class NonePsutil:
    def sensors_battery(self):
        return None


def test_read_battery():
    battery = read_battery(FakePsutilBattery())
    assert battery.percent == 88.0
    assert battery.plugged is False


def test_read_battery_none():
    assert read_battery(NonePsutil()) is None


def test_parse_refresh_rate():
    assert parse_refresh_rate([{"CurrentRefreshRate": 60}, {"CurrentRefreshRate": 144}]) == 144.0
    assert parse_refresh_rate({"CurrentRefreshRate": 0}) is None
