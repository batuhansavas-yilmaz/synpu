import re

import psutil

from synpu.metrics.models import CpuStats

_CPU_NAME: str | None = None
_NAME_LOADED = False


def short_cpu_name(name: str) -> str:
    text = name or ""
    text = text.replace("(R)", "").replace("(TM)", "")
    text = re.sub(r"@\s*[\d.]+\s*GHz", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+(?:st|nd|rd|th)\s+Gen\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+-Core\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCore\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCPU\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bProcessor\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(i[3579])-(\w+)", r"\1 \2", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text or name


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
            _CPU_NAME = short_cpu_name(str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip())
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
    cores = None
    try:
        percpu = psutil_mod.cpu_percent(interval=None, percpu=True)
        if percpu:
            cores = tuple(float(value) for value in percpu)
    except Exception:
        cores = None
    return CpuStats(usage_pct=usage, temp_c=None, freq_mhz=freq, name=cpu_name(), cores=cores)
