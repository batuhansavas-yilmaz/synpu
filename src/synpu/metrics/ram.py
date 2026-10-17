import psutil

from synpu.metrics.models import RamStats


def read_ram(psutil_mod=psutil) -> RamStats:
    vm = psutil_mod.virtual_memory()
    return RamStats(
        used_mb=int(vm.used) // (1024 * 1024),
        total_mb=int(vm.total) // (1024 * 1024),
        percent=float(vm.percent),
    )
