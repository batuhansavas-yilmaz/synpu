import platform
import subprocess
import threading
import time
from functools import lru_cache

EDITION_NAMES = {
    "Core": "Home",
    "CoreN": "Home N",
    "CoreSingleLanguage": "Home Single Language",
    "CoreCountrySpecific": "Home China",
    "Professional": "Pro",
    "ProfessionalN": "Pro N",
    "ProfessionalEducation": "Pro Education",
    "ProfessionalEducationN": "Pro Education N",
    "ProfessionalWorkstation": "Pro for Workstations",
    "ProfessionalWorkstationN": "Pro for Workstations N",
    "Enterprise": "Enterprise",
    "EnterpriseN": "Enterprise N",
    "EnterpriseS": "Enterprise LTSC",
    "EnterpriseSN": "Enterprise LTSC N",
    "IoTEnterprise": "IoT Enterprise",
    "Education": "Education",
    "EducationN": "Education N",
}


def format_os_name(system: str | None, release: str | None,
                   version: str | None, edition: str | None) -> str | None:
    if system != "Windows":
        return None
    release = release or ""
    if release == "10":
        try:
            if int(str(version or "").split(".")[-1]) >= 22000:
                release = "11"
        except ValueError:
            pass
    edition_name = EDITION_NAMES.get(edition or "", edition or "")
    parts = ["Windows", release, edition_name]
    return " ".join(part for part in parts if part) or None


@lru_cache(maxsize=1)
def os_name() -> str | None:
    if platform.system() != "Windows":
        return None
    try:
        edition = platform.win32_edition()
    except Exception:
        edition = ""
    return format_os_name("Windows", platform.release(), platform.version(), edition)


LOGON_TIME_COMMAND = (
    "$s = Get-CimInstance Win32_LogonSession | Where-Object { $_.LogonType -in 2,10,11 } "
    "| Sort-Object StartTime -Descending | Select-Object -First 1; "
    "if ($s) { $s.StartTime.ToFileTimeUtc() }"
)


def filetime_to_unix(value: int) -> float:
    return value / 10_000_000 - 11_644_473_600


class SessionReader:
    def __init__(self, ttl: float = 30.0):
        self._ttl = ttl
        self._started: float | None = None
        self._at = float("-inf")
        self._lock = threading.Lock()

    def _query(self) -> float | None:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", LOGON_TIME_COMMAND],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode != 0:
                return None
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if not lines:
                return None
            filetime = int(lines[-1])
            if filetime <= 0:
                return None
            return filetime_to_unix(filetime)
        except Exception:
            return None

    def read(self) -> int | None:
        now = time.monotonic()
        with self._lock:
            if now - self._at >= self._ttl:
                self._started = self._query()
                self._at = now
            if self._started is None:
                return None
            return max(0, int(time.time() - self._started))
