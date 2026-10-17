import psutil

from synpu.metrics.models import CpuStats

_CPU_NAME: str | None = None
_NAME_LOADED = False


def cpu_name() -> str | None:
    global _CPU_NAME, _NAME_LOADED
    if _NAME_LOADED:
        return _CPU_NAME
    _NAME_LOADED = True
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        try:
            _CPU_NAME = str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        finally:
            winreg.CloseKey(key)
    except Exception:
        _CPU_NAME = None
    return _CPU_NAME


def read_cpu(psutil_mod=psutil) -> CpuStats:
    usage = psutil_mod.cpu_percent(interval=None)
    freq = None
    try:
        info = psutil_mod.cpu_freq()
        if info and info.current:
            freq = float(info.current)
    except Exception:
        freq = None
    return CpuStats(usage_pct=usage, temp_c=None, freq_mhz=freq, name=cpu_name())
