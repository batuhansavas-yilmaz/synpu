import socket

from synpu.net import addresses
from synpu.net.addresses import candidate_ips, is_virtual, primary_ip


class FakeSock:
    def __init__(self, ip):
        self.ip = ip

    def connect(self, addr):
        pass

    def getsockname(self):
        return (self.ip, 12345)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeAddr:
    def __init__(self, family, address):
        self.family = family
        self.address = address


class FakeStats:
    def __init__(self, isup):
        self.isup = isup


def test_is_virtual_patterns():
    assert is_virtual("vEthernet (WSL)")
    assert is_virtual("Hyper-V Virtual Ethernet Adapter")
    assert is_virtual("Loopback Pseudo-Interface 1")
    assert is_virtual("Bluetooth Network Connection")
    assert is_virtual("TAP-Windows Adapter V9")
    assert is_virtual("Tailscale")
    assert is_virtual("ZeroTier One")
    assert not is_virtual("Ethernet")
    assert not is_virtual("Wi-Fi")


def test_primary_ip_socket_success(monkeypatch):
    monkeypatch.setattr(addresses.socket, "socket", lambda family, type: FakeSock("192.168.1.13"))
    assert primary_ip() == "192.168.1.13"


def test_primary_ip_falls_back_to_candidates(monkeypatch):
    def fake_socket(family, type):
        raise OSError("no network")

    monkeypatch.setattr(addresses.socket, "socket", fake_socket)
    monkeypatch.setattr(addresses, "candidate_ips", lambda: ["192.168.1.20"])
    assert primary_ip() == "192.168.1.20"


def test_candidate_ips_filters(monkeypatch):
    addrs = {
        "Ethernet": [FakeAddr(socket.AF_INET, "192.168.1.13"), FakeAddr(socket.AF_INET6, "fe80::1")],
        "Wi-Fi": [FakeAddr(socket.AF_INET, "169.254.10.10")],
        "vEthernet (WSL)": [FakeAddr(socket.AF_INET, "172.20.0.1")],
        "Loopback": [FakeAddr(socket.AF_INET, "127.0.0.1")],
        "Down": [FakeAddr(socket.AF_INET, "10.0.0.5")],
    }
    stats = {
        "Ethernet": FakeStats(True),
        "Wi-Fi": FakeStats(True),
        "vEthernet (WSL)": FakeStats(True),
        "Loopback": FakeStats(True),
        "Down": FakeStats(False),
    }
    monkeypatch.setattr(addresses.psutil, "net_if_addrs", lambda: addrs)
    monkeypatch.setattr(addresses.psutil, "net_if_stats", lambda: stats)
    assert candidate_ips() == ["192.168.1.13"]
