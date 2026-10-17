import socket

import psutil

VIRTUAL_PATTERNS = (
    "vethernet",
    "hyper-v",
    "wsl",
    "loopback",
    "bluetooth",
    "tap-",
    "tailscale",
    "zerotier",
    "openvpn",
    "wireguard",
    "wintun",
)


def is_virtual(name: str) -> bool:
    lower = name.lower()
    return any(pattern in lower for pattern in VIRTUAL_PATTERNS)


def candidate_ips() -> list[str]:
    result: list[str] = []
    stats = psutil.net_if_stats()
    for iface, addr_list in psutil.net_if_addrs().items():
        iface_stats = stats.get(iface)
        if iface_stats is not None and not iface_stats.isup:
            continue
        if is_virtual(iface):
            continue
        for addr in addr_list:
            if addr.family != socket.AF_INET:
                continue
            ip = addr.address
            if ip.startswith("127.") or ip.startswith("169.254."):
                continue
            if ip not in result:
                result.append(ip)
    return result


def _interface_for_ip(ip: str) -> str | None:
    try:
        for iface, addr_list in psutil.net_if_addrs().items():
            for addr in addr_list:
                if addr.family == socket.AF_INET and addr.address == ip:
                    return iface
    except Exception:
        pass
    return None


def primary_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
        iface = _interface_for_ip(ip)
        if iface is not None and not is_virtual(iface):
            return ip
    except Exception:
        pass
    candidates = candidate_ips()
    return candidates[0] if candidates else None
