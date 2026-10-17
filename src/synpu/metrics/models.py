from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CpuStats:
    usage_pct: float | None
    temp_c: float | None
    freq_mhz: float | None = None
    name: str | None = None


@dataclass(frozen=True)
class GpuStats:
    name: str | None
    usage_pct: float | None
    temp_c: float | None
    vram_used_mb: int | None
    vram_total_mb: int | None
    power_w: float | None
    freq_mhz: float | None = None


@dataclass(frozen=True)
class RamStats:
    used_mb: int
    total_mb: int
    percent: float
    speed_mts: int | None = None
    mem_type: str | None = None
    module_count: int | None = None


@dataclass(frozen=True)
class StorageStats:
    label: str
    used_mb: int | None = None
    total_mb: int | None = None
    percent: float | None = None
    temp_c: float | None = None
    is_system: bool = False


@dataclass(frozen=True)
class NetStats:
    down_bps: float | None = None
    up_bps: float | None = None


@dataclass(frozen=True)
class FanStat:
    name: str
    rpm: float


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

    def to_dict(self) -> dict:
        return asdict(self)
