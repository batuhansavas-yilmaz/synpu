from synpu.metrics.battery import read_battery
from synpu.metrics.display import parse_controllers, parse_monitor_name, parse_refresh_rate
from synpu.metrics.motherboard import parse_motherboard
from synpu.metrics.network_meta import parse_isp_org, parse_wifi_ssid


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


def test_parse_controllers_resolution_and_rate():
    payload = [
        {"CurrentRefreshRate": 60, "CurrentHorizontalResolution": 1920, "CurrentVerticalResolution": 1080},
        {"CurrentRefreshRate": 144, "CurrentHorizontalResolution": 2560, "CurrentVerticalResolution": 1440},
    ]
    info = parse_controllers(payload)
    assert info == {"refresh_hz": 144.0, "width": 2560, "height": 1440}


def test_parse_monitor_name_decodes():
    payload = {"UserFriendlyName": [76, 71, 32, 85, 76, 84, 82, 65, 71, 69, 65, 82],
               "ManufacturerName": [71, 83, 77]}
    assert parse_monitor_name(payload) == "LG ULTRAGEAR"


def test_parse_motherboard():
    board = parse_motherboard({"Manufacturer": "ASUSTeK COMPUTER INC.", "Product": "PRIME B660M-K D4"})
    assert board.vendor == "ASUSTeK COMPUTER INC."
    assert board.model == "PRIME B660M-K D4"
    assert parse_motherboard([]) is None


def test_parse_wifi_ssid():
    netsh_output = (
        "\n    Name                   : Wi-Fi\n"
        "    SSID                   : EvWiFi\n"
        "    BSSID                  : aa:bb:cc:dd:ee:ff\n"
    )
    assert parse_wifi_ssid(netsh_output) == "EvWiFi"
    assert parse_wifi_ssid("    State : disconnected") is None


def test_parse_isp_org():
    assert parse_isp_org({"org": "AS9121 Turk Telekom"}) == "Turk Telekom"
    assert parse_isp_org({"org": "Turk Telekom"}) == "Turk Telekom"
    assert parse_isp_org({}) is None
