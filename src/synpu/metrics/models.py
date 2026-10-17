from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CpuStats:
    usage_pct: float | None
    temp_c: float | None


@dataclass(frozen=True)
class GpuStats:
    name: str | None
    usage_pct: float | None
    temp_c: float | None
    vram_used_mb: int | None
    vram_total_mb: int | None
    power_w: float | None


@dataclass(frozen=True)
class RamStats:
    used_mb: int
    total_mb: int
    percent: float


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

    def to_dict(self) -> dict:
        return asdict(self)
