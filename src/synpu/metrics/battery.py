import psutil

from synpu.metrics.models import BatteryStats


def read_battery(psutil_mod=psutil) -> BatteryStats | None:
    try:
        battery = psutil_mod.sensors_battery()
    except Exception:
        return None
    if battery is None:
        return None
    return BatteryStats(
        percent=float(battery.percent) if battery.percent is not None else None,
        plugged=bool(battery.power_plugged) if battery.power_plugged is not None else None,
    )
