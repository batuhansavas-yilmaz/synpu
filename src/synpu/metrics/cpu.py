import psutil

from synpu.metrics.models import CpuStats


def read_cpu(psutil_mod=psutil) -> CpuStats:
    return CpuStats(usage_pct=psutil_mod.cpu_percent(interval=None), temp_c=None)
