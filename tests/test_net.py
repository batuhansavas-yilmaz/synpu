from synpu.metrics.net import NetSpeedMeter


class FakeCounters:
    def __init__(self, recv, sent):
        self.bytes_recv = recv
        self.bytes_sent = sent


def test_first_sample_is_zero():
    meter = NetSpeedMeter()
    stats = meter.update(0.0, FakeCounters(0, 0))
    assert stats.down_bps == 0.0
    assert stats.up_bps == 0.0


def test_ema_smooths_instant_rate():
    meter = NetSpeedMeter(tau=1.0)
    meter.update(0.0, FakeCounters(0, 0))
    stats = meter.update(1.0, FakeCounters(1000, 500))
    assert abs(stats.down_bps - 632.12) < 1
    assert abs(stats.up_bps - 316.06) < 1


def test_zero_tau_is_instant():
    meter = NetSpeedMeter(tau=0)
    meter.update(0.0, FakeCounters(0, 0))
    stats = meter.update(1.0, FakeCounters(1000, 500))
    assert stats.down_bps == 1000.0
    assert stats.up_bps == 500.0


def test_counter_reset_never_negative():
    meter = NetSpeedMeter(tau=1.0)
    meter.update(0.0, FakeCounters(2000, 1000))
    meter.update(1.0, FakeCounters(2000, 1000))
    stats = meter.update(2.0, FakeCounters(1000, 500))
    assert stats.down_bps >= 0.0
    assert stats.up_bps >= 0.0
