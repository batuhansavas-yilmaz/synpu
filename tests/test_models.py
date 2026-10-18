from synpu.metrics.models import Snapshot, CpuStats, RamStats, FpsStats


def test_snapshot_to_dict_nullable_gpu_and_fps():
    s = Snapshot(hostname="pc", timestamp=1.5,
                 cpu=CpuStats(usage_pct=10.0, temp_c=None),
                 gpu=None,
                 ram=RamStats(used_mb=100, total_mb=200, percent=50.0),
                 fps=FpsStats(app=None, value=None))
    d = s.to_dict()
    assert d == {"hostname": "pc", "timestamp": 1.5,
                 "cpu": {"usage_pct": 10.0, "temp_c": None, "freq_mhz": None, "name": None, "cores": None},
                 "gpu": None,
                 "ram": {"used_mb": 100, "total_mb": 200, "percent": 50.0,
                         "speed_mts": None, "mem_type": None, "module_count": None,
                         "temp_c": None},
                 "fps": {"app": None, "value": None},
                 "disks": [],
                 "net": None,
                 "fans": [],
                 "gpus": [],
                 "battery": None,
                 "uptime_s": None,
                 "session_s": None,
                 "install_s": None,
                 "display": None,
                 "motherboard": None,
                 "top": None,
                 "isp": None,
                 "wifi": None,
                 "ping_ms": None,
                 "os_name": None}
