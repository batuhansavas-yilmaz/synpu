import os

import psutil

from synpu.metrics.models import StorageStats


def system_drive() -> str:
    return os.environ.get("SystemDrive", "C:")


def _is_system(device: str, system: str) -> bool:
    return device.upper().rstrip("\\").startswith(system.upper().rstrip("\\"))


def read_disks(psutil_mod=psutil, system: str | None = None) -> list[StorageStats]:
    system = (system or system_drive()).rstrip("\\")
    disks: list[StorageStats] = []
    try:
        partitions = psutil_mod.disk_partitions(all=False)
    except Exception:
        partitions = []
    for part in partitions:
        fstype = (getattr(part, "fstype", "") or "").lower()
        opts = (getattr(part, "opts", "") or "").lower()
        if "cdrom" in opts or fstype in ("", "cdrom"):
            continue
        try:
            usage = psutil_mod.disk_usage(part.device)
        except Exception:
            continue
        label = str(part.device).rstrip("\\") or str(part.device)
        disks.append(StorageStats(
            label=label,
            used_mb=int(usage.used) // (1024 * 1024),
            total_mb=int(usage.total) // (1024 * 1024),
            percent=float(usage.percent),
            is_system=_is_system(str(part.device), system),
        ))
    if not disks:
        try:
            usage = psutil_mod.disk_usage(system + "\\")
            disks.append(StorageStats(
                label=system,
                used_mb=int(usage.used) // (1024 * 1024),
                total_mb=int(usage.total) // (1024 * 1024),
                percent=float(usage.percent),
                is_system=True,
            ))
        except Exception:
            pass
    disks.sort(key=lambda d: (not d.is_system, d.label))
    return disks
