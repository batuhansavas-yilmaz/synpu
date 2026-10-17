import json
import subprocess
from pathlib import Path

LHM_DLL = Path(__file__).resolve().parents[3] / "third_party" / "lhm" / "LibreHardwareMonitorLib.dll"

WMI_COMMAND = (
    "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
    "| Select-Object -ExpandProperty CurrentTemperature | ConvertTo-Json"
)


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

    def read(self) -> float | None:
        temp = None if self._lhm_failed else self._try_lhm()
        if temp is not None:
            return temp
        return self._try_wmi()

    def _try_lhm(self) -> float | None:
        try:
            import sys

            import clr
        except Exception:
            self._lhm_failed = True
            return None

        if not LHM_DLL.exists():
            self._lhm_failed = True
            return None

        try:
            sys.path.append(str(LHM_DLL.parent))
            clr.AddReference(str(LHM_DLL))
            from LibreHardwareMonitor.Hardware import Computer

            computer = Computer()
            computer.IsCpuEnabled = True
            computer.Open()
            try:
                sensors: list[tuple[str, float]] = []
                for hardware in computer.Hardware:
                    if str(hardware.HardwareType) != "Cpu":
                        continue
                    hardware.Update()
                    for sensor in hardware.Sensors:
                        if str(sensor.SensorType) == "Temperature" and sensor.Value is not None:
                            sensors.append((str(sensor.Name), float(sensor.Value)))
                return pick_cpu_temp(sensors)
            finally:
                computer.Close()
        except Exception:
            self._lhm_failed = True
            return None

    def _try_wmi(self) -> float | None:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", WMI_COMMAND],
                capture_output=True,
                text=True,
                timeout=15,
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
