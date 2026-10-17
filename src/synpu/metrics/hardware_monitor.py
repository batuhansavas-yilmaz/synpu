import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from synpu.metrics.models import GpuStats

LHM_DLL = Path(__file__).resolve().parents[3] / "third_party" / "lhm" / "LibreHardwareMonitorLib.dll"

WMI_COMMAND = (
    "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
    "| Select-Object -ExpandProperty CurrentTemperature | ConvertTo-Json"
)

WMI_TTL_S = 10.0
LHM_RETRY_S = 300.0


@dataclass(frozen=True)
class HardwareReading:
    cpu_temp: float | None = None
    fans: tuple[tuple[str, float], ...] = ()
    disk_temps: tuple[tuple[str, float], ...] = ()
    cpu_clock_mhz: float | None = None
    gpus: tuple[GpuStats, ...] = ()


def pick_cpu_temp(sensors: list[tuple[str, float]]) -> float | None:
    package = [v for n, v in sensors if "package" in n.lower()]
    if package:
        return max(package)
    cores = [v for n, v in sensors if "core" in n.lower()]
    if cores:
        return max(cores)
    return None


def _scan_computer(computer) -> HardwareReading:
    cpu_sensors: list[tuple[str, float]] = []
    cpu_clocks: list[float] = []
    fans: list[tuple[str, float]] = []
    disks: list[tuple[str, float]] = []
    gpus: list[GpuStats] = []

    def scan_gpu(hardware) -> GpuStats:
        usage = None
        temp = None
        power = None
        freq = None
        vram_used = None
        vram_total = None
        fallback_usage = None
        for sensor in hardware.Sensors:
            sensor_type = str(sensor.SensorType)
            sensor_name = str(sensor.Name)
            value = sensor.Value
            if value is None:
                continue
            if sensor_type == "Load" and sensor_name == "GPU Core":
                usage = float(value)
            elif sensor_type == "Load" and sensor_name == "D3D 3D" and fallback_usage is None:
                fallback_usage = float(value)
            elif sensor_type == "Temperature" and sensor_name == "GPU Core":
                temp = float(value)
            elif sensor_type == "Power" and sensor_name == "GPU Package":
                power = float(value)
            elif sensor_type == "Clock" and sensor_name == "GPU Core":
                freq = float(value)
            elif sensor_type == "SmallData" and sensor_name == "GPU Memory Used":
                vram_used = int(value)
            elif sensor_type == "SmallData" and sensor_name == "GPU Memory Total":
                vram_total = int(value)
        return GpuStats(
            name=str(hardware.Name),
            usage_pct=usage if usage is not None else fallback_usage,
            temp_c=temp,
            vram_used_mb=vram_used,
            vram_total_mb=vram_total,
            power_w=power,
            freq_mhz=freq,
        )

    def visit(hardware, depth=0):
        hardware_type = str(hardware.HardwareType)
        try:
            hardware.Update()
        except Exception:
            pass
        if hardware_type == "Cpu":
            for sensor in hardware.Sensors:
                sensor_type = str(sensor.SensorType)
                if sensor_type == "Temperature" and sensor.Value is not None:
                    cpu_sensors.append((str(sensor.Name), float(sensor.Value)))
                elif sensor_type == "Clock" and sensor.Value is not None:
                    if "bus" not in str(sensor.Name).lower():
                        cpu_clocks.append(float(sensor.Value))
        elif hardware_type == "Storage":
            for sensor in hardware.Sensors:
                if str(sensor.SensorType) == "Temperature" and sensor.Value is not None:
                    disks.append((str(hardware.Name), float(sensor.Value)))
        elif hardware_type in ("GpuNvidia", "GpuAmd", "GpuIntel"):
            gpus.append(scan_gpu(hardware))
        for sensor in hardware.Sensors:
            if str(sensor.SensorType) == "Fan" and sensor.Value is not None:
                fans.append((str(sensor.Name), float(sensor.Value)))
        if depth < 2:
            for sub in getattr(hardware, "SubHardware", []) or []:
                visit(sub, depth + 1)

    for hardware in computer.Hardware:
        visit(hardware)
    clock = round(sum(cpu_clocks) / len(cpu_clocks)) if cpu_clocks else None
    return HardwareReading(
        cpu_temp=pick_cpu_temp(cpu_sensors),
        fans=tuple(fans),
        disk_temps=tuple(disks),
        cpu_clock_mhz=float(clock) if clock is not None else None,
        gpus=tuple(gpus),
    )


class CpuTempReader:
    def __init__(self):
        self._lhm_failed = False
        self._lhm_retry_at = 0.0
        self._computer = None
        self._wmi_value: float | None = None
        self._wmi_at = float("-inf")

    def read(self) -> HardwareReading:
        reading = self._try_lhm()
        if reading is not None and reading.cpu_temp is not None:
            return reading
        fans = reading.fans if reading is not None else ()
        disks = reading.disk_temps if reading is not None else ()
        now = time.monotonic()
        if now - self._wmi_at >= WMI_TTL_S:
            self._wmi_at = now
            self._wmi_value = self._try_wmi()
        return HardwareReading(cpu_temp=self._wmi_value, fans=fans, disk_temps=disks)

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
        computer.IsMotherboardEnabled = True
        computer.IsStorageEnabled = True
        computer.IsGpuEnabled = True
        computer.Open()
        self._computer = computer
        return computer

    def _try_lhm(self) -> HardwareReading | None:
        if self._lhm_failed:
            if time.monotonic() < self._lhm_retry_at:
                return None
            self._lhm_failed = False
        try:
            computer = self._get_computer()
            if computer is None:
                self._mark_lhm_failed()
                return None
            reading = _scan_computer(computer)
            if reading.cpu_temp is None:
                self._mark_lhm_failed()
            return reading
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
