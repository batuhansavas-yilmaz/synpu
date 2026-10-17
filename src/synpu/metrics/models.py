from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CpuStats:
    usage_pct: float | None
    temp_c: float | None
    freq_mhz: float | None = None
    name: str | None = None
    cores: tuple[float, ...] | None = None


@dataclass(frozen=True)
class GpuStats:
    name: str | None
    usage_pct: float | None
    temp_c: float | None
    vram_used_mb: int | None
    vram_total_mb: int | None
    power_w: float | None
    freq_mhz: float | None = None
    hot_spot_c: float | None = None
    fan_pct: float | None = None


@dataclass(frozen=True)
class RamStats:
    used_mb: int
    total_mb: int
    percent: float
    speed_mts: int | None = None
    mem_type: str | None = None
    module_count: int | None = None
    temp_c: float | None = None


@dataclass(frozen=True)
class StorageStats:
    label: str
    used_mb: int | None = None
    total_mb: int | None = None
    percent: float | None = None
    temp_c: float | None = None
    is_system: bool = False
    read_bps: float | None = None
    write_bps: float | None = None
    health_pct: float | None = None
    power_on_hours: int | None = None


@dataclass(frozen=True)
class NetStats:
    down_bps: float | None = None
    up_bps: float | None = None


@dataclass(frozen=True)
class FanStat:
    name: str
    rpm: float


@dataclass(frozen=True)
class BatteryStats:
    percent: float | None = None
    plugged: bool | None = None


@dataclass(frozen=True)
class DisplayStats:
    refresh_hz: float | None = None
    width: int | None = None
    height: int | None = None
    name: str | None = None


@dataclass(frozen=True)
class MotherboardStats:
    vendor: str | None = None
    model: str | None = None


@dataclass(frozen=True)
class ProcessStats:
    name: str | None = None
    value: float | None = None


@dataclass(frozen=True)
class TopProcesses:
    cpu: ProcessStats | None = None
    ram: ProcessStats | None = None
    gpu: ProcessStats | None = None


@dataclass(frozen=True)
class FpsStats:
    app: str | None
    value: float | None


@dataclass(frozen=True)
class Snapshot:
    hostname: str
    timestamp: float
    cpu: CpuStats
    gpu: GpuStats | None
    ram: RamStats | None
    fps: FpsStats
    disks: list[StorageStats] = field(default_factory=list)
    net: NetStats | None = None
    fans: list[FanStat] = field(default_factory=list)
    gpus: list[GpuStats] = field(default_factory=list)
    battery: BatteryStats | None = None
    uptime_s: int | None = None
    display: DisplayStats | None = None
    motherboard: MotherboardStats | None = None
    top: TopProcesses | None = None
    isp: str | None = None
    wifi: str | None = None
    ping_ms: int | None = None
    os_name: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
