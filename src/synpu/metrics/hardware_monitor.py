import json
import subprocess
import time
from pathlib import Path

LHM_DLL = Path(__file__).resolve().parents[3] / "third_party" / "lhm" / "LibreHardwareMonitorLib.dll"

WMI_COMMAND = (
    "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
    "| Select-Object -ExpandProperty CurrentTemperature | ConvertTo-Json"
)

WMI_TTL_S = 10.0
LHM_RETRY_S = 300.0


def pick_cpu_temp(sensors: list[tuple[str, float]]) -> float | None:
    package = [v for n, v in sensors if "package" in n.lower()]
    if package:
        return max(package)
    cores = [v for n, v in sensors if "core" in n.lower()]
    if cores:
        return max(cores)
    return None


class CpuTempReader:
    def __init__(self):
        self._lhm_failed = False
        self._lhm_retry_at = 0.0
        self._computer = None
        self._wmi_value: float | None = None
        self._wmi_at = float("-inf")

    def read(self) -> float | None:
        temp = self._try_lhm()
        if temp is not None:
            return temp
        now = time.monotonic()
        if now - self._wmi_at >= WMI_TTL_S:
            self._wmi_at = now
            self._wmi_value = self._try_wmi()
        return self._wmi_value

    def _mark_lhm_failed(self) -> None:
        self._lhm_failed = True
        self._lhm_retry_at = time.monotonic() + LHM_RETRY_S
        if self._computer is not None:
            try:
                self._computer.Close()
            except Exception:
                pass
            self._computer = None

    def _get_computer(self):
        if self._computer is not None:
            return self._computer
        import sys

        import clr

        if not LHM_DLL.exists():
            return None
        dll_dir = str(LHM_DLL.parent)
        if dll_dir not in sys.path:
            sys.path.append(dll_dir)
        clr.AddReference(str(LHM_DLL))
        from LibreHardwareMonitor.Hardware import Computer

        computer = Computer()
        computer.IsCpuEnabled = True
        computer.Open()
        self._computer = computer
        return computer

    def _try_lhm(self) -> float | None:
        if self._lhm_failed:
            if time.monotonic() < self._lhm_retry_at:
                return None
            self._lhm_failed = False
        try:
            computer = self._get_computer()
            if computer is None:
                self._mark_lhm_failed()
                return None
            sensors: list[tuple[str, float]] = []
            for hardware in computer.Hardware:
                if str(hardware.HardwareType) != "Cpu":
                    continue
                hardware.Update()
                for sensor in hardware.Sensors:
                    if str(sensor.SensorType) == "Temperature" and sensor.Value is not None:
                        sensors.append((str(sensor.Name), float(sensor.Value)))
            temp = pick_cpu_temp(sensors)
            if temp is None:
                self._mark_lhm_failed()
            return temp
        except Exception:
            self._mark_lhm_failed()
            return None

    def _try_wmi(self) -> float | None:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", WMI_COMMAND],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            data = json.loads(result.stdout)
            values = data if isinstance(data, list) else [data]
            temps = [v / 10.0 - 273.15 for v in values if isinstance(v, (int, float))]
            if not temps:
                return None
            return sum(temps) / len(temps)
        except Exception:
            return None
