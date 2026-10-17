from synpu.metrics.models import Snapshot, CpuStats, RamStats, FpsStats


def test_snapshot_to_dict_nullable_gpu_and_fps():
    s = Snapshot(hostname="pc", timestamp=1.5,
                 cpu=CpuStats(usage_pct=10.0, temp_c=None),
                 gpu=None,
                 ram=RamStats(used_mb=100, total_mb=200, percent=50.0),
                 fps=FpsStats(app=None, value=None))
    d = s.to_dict()
    assert d == {"hostname": "pc", "timestamp": 1.5,
                 "cpu": {"usage_pct": 10.0, "temp_c": None, "freq_mhz": None, "name": None},
                 "gpu": None,
                 "ram": {"used_mb": 100, "total_mb": 200, "percent": 50.0},
                 "fps": {"app": None, "value": None},
                 "disks": [],
                 "net": None,
                 "fans": []}
