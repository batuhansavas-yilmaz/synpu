from synpu.metrics.storage import read_disks


class FakePart:
    def __init__(self, device, fstype="NTFS", opts="rw,fixed"):
        self.device = device
        self.fstype = fstype
        self.opts = opts


class FakeUsage:
    def __init__(self, used, total, percent):
        self.used = used
        self.total = total
        self.percent = percent


class FakePsutil:
    def __init__(self, partitions, usages):
        self._partitions = partitions
        self._usages = usages

    def disk_partitions(self, all=False):
        return self._partitions

    def disk_usage(self, path):
        return self._usages[path]


def test_read_disks_marks_system_and_sorts():
    parts = [FakePart("D:\\"), FakePart("C:\\"), FakePart("E:\\", opts="ro,cdrom")]
    usages = {
        "D:\\": FakeUsage(100 * 1024 * 1024, 400 * 1024 * 1024, 25.0),
        "C:\\": FakeUsage(200 * 1024 * 1024, 800 * 1024 * 1024, 25.0),
    }
    disks = read_disks(FakePsutil(parts, usages), system="C:")
    assert [d.label for d in disks] == ["C:", "D:"]
    assert disks[0].is_system
    assert not disks[1].is_system
    assert disks[0].used_mb == 200
    assert disks[0].total_mb == 800


def test_read_disks_falls_back_to_system_drive():
    class Broken:
        def disk_partitions(self, all=False):
            return []

        def disk_usage(self, path):
            return FakeUsage(50 * 1024 * 1024, 100 * 1024 * 1024, 50.0)

    disks = read_disks(Broken(), system="C:")
    assert len(disks) == 1
    assert disks[0].is_system
    assert disks[0].label == "C:"
