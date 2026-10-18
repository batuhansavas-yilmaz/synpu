from synpu.metrics.models import GpuStats


def read_gpu(nvml_mod=None) -> GpuStats | None:
    if nvml_mod is None:
        try:
            import pynvml as nvml_mod
        except Exception:
            return None

    try:
        nvml_mod.nvmlInit()
    except Exception:
        return None

    try:
        handle = nvml_mod.nvmlDeviceGetHandleByIndex(0)
        name = nvml_mod.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="replace")
        usage = nvml_mod.nvmlDeviceGetUtilizationRates(handle)
        temp = nvml_mod.nvmlDeviceGetTemperature(handle, nvml_mod.NVML_TEMPERATURE_GPU)
        mem = nvml_mod.nvmlDeviceGetMemoryInfo(handle)
        try:
            power_w = nvml_mod.nvmlDeviceGetPowerUsage(handle) / 1000.0
        except Exception:
            power_w = None
        try:
            freq_mhz = float(nvml_mod.nvmlDeviceGetClockInfo(handle, nvml_mod.NVML_CLOCK_GRAPHICS))
        except Exception:
            freq_mhz = None
        try:
            fan_pct = float(nvml_mod.nvmlDeviceGetFanSpeed(handle))
        except Exception:
            fan_pct = None
        try:
            rpm_reader = getattr(nvml_mod, "nvmlDeviceGetFanSpeedRPM", None)
            fan_rpm = int(rpm_reader(handle)) if rpm_reader is not None else None
        except Exception:
            fan_rpm = None
        return GpuStats(
            name=name,
            usage_pct=float(usage.gpu),
            temp_c=float(temp),
            vram_used_mb=int(mem.used) // (1024 * 1024),
            vram_total_mb=int(mem.total) // (1024 * 1024),
            power_w=power_w,
            freq_mhz=freq_mhz,
            fan_pct=fan_pct,
            fan_rpm=fan_rpm,
        )
    except Exception:
        return None
    finally:
        try:
            nvml_mod.nvmlShutdown()
        except Exception:
            pass
