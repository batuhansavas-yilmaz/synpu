import os

import psutil

from synpu.metrics.models import StorageStats


def system_drive() -> str:
    return os.environ.get("SystemDrive", "C:")


def read_storage(psutil_mod=psutil, drive: str | None = None) -> StorageStats:
    drive = drive or system_drive()
    root = drive if drive.endswith("\\") else drive + "\\"
    usage = psutil_mod.disk_usage(root)
    return StorageStats(
        label=drive.rstrip("\\") or root,
        used_mb=int(usage.used) // (1024 * 1024),
        total_mb=int(usage.total) // (1024 * 1024),
        percent=float(usage.percent),
    )
