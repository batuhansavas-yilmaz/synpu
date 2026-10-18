import json
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

WIFI_COMMAND = ["netsh", "wlan", "show", "interfaces"]
ISP_URL = "https://ipinfo.io/json"
PING_HOST = "9.9.9.9"
PING_COMMAND = (
    "$sw = [System.Diagnostics.Stopwatch]::StartNew(); "
    "$client = New-Object System.Net.Sockets.TcpClient; "
    "try { $task = $client.ConnectAsync('9.9.9.9', 53); "
    "if ($task.Wait(1500)) { $sw.ElapsedMilliseconds } else { -1 } } "
    "catch { -1 } finally { $client.Close() }"
)


def parse_wifi_ssid(text: str) -> str | None:
    for line in (text or "").splitlines():
        if "BSSID" in line.upper():
            continue
        match = re.match(r"^\s*SSID\s*:\s*(.+?)\s*$", line)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def parse_isp_org(payload) -> str | None:
    if not isinstance(payload, dict):
        return None
    org = str(payload.get("org") or "").strip()
    if not org:
        return None
    cleaned = re.sub(r"^AS\d+\s+", "", org).strip()
    return cleaned or None


def parse_ping_ms(text) -> int | None:
    try:
        value = int(str(text).strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def median_ping(values) -> int | None:
    valid = sorted(v for v in values if v is not None and v > 0)
    if not valid:
        return None
    return valid[len(valid) // 2]


class LatencyReader:
    def __init__(self, interval: float = 10.0, window: int = 3):
        self._interval = interval
        self._window = max(1, int(window))
        self._value: int | None = None
        self._samples: list[int] = []
        self._failures = 0
        self._lock = threading.Lock()
        threading.Thread(target=self._loop, daemon=True).start()

    def _measure(self) -> None:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", PING_COMMAND],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            value = parse_ping_ms(result.stdout) if result.returncode == 0 else None
        except Exception:
            value = None
        with self._lock:
            if value is None:
                self._failures += 1
                if self._failures >= 3:
                    self._samples.clear()
                    self._value = None
                return
            self._failures = 0
            self._samples.append(value)
            self._samples = self._samples[-self._window:]
            self._value = median_ping(self._samples)

    def _loop(self) -> None:
        while True:
            self._measure()
            time.sleep(self._interval)

    def read(self) -> int | None:
        with self._lock:
            return self._value


class WifiReader:
    def __init__(self, ttl: float = 60.0):
        self._ttl = ttl
        self._value: str | None = None
        self._at = float("-inf")

    def read(self) -> str | None:
        now = time.monotonic()
        if now - self._at < self._ttl:
            return self._value
        self._at = now
        try:
            result = subprocess.run(
                WIFI_COMMAND,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                self._value = parse_wifi_ssid(result.stdout)
        except Exception:
            pass
        return self._value


class IspReader:
    def __init__(self, ttl: float = 6 * 3600, state_path: Path | None = None):
        self._ttl = ttl
        self._value: str | None = None
        self._at = float("-inf")
        self._lock = threading.Lock()
        self._path = Path(state_path) if state_path is not None else None
        self._load_cache()
        threading.Thread(target=self._loop, daemon=True).start()

    def _load_cache(self) -> None:
        if self._path is None:
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            value = data.get("value")
            fetched_at = float(data.get("fetched_at") or 0)
            if value:
                self._value = str(value)
                age = time.time() - fetched_at
                if age < self._ttl:
                    self._at = time.monotonic() - age
        except Exception:
            pass

    def _save_cache(self) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"value": self._value, "fetched_at": time.time()}
            self._path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass

    def _fetch(self) -> None:
        try:
            request = urllib.request.Request(ISP_URL, headers={"User-Agent": "synpu-isp-check"})
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            value = parse_isp_org(payload)
            if not value:
                return
            with self._lock:
                self._value = value
                self._at = time.monotonic()
            self._save_cache()
        except Exception:
            pass

    def _loop(self) -> None:
        while True:
            with self._lock:
                fresh = time.monotonic() - self._at < self._ttl
            if not fresh:
                self._fetch()
            time.sleep(300)

    def read(self) -> str | None:
        with self._lock:
            return self._value
