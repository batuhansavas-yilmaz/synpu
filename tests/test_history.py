from synpu.metrics.history import HistoryBuffer


def test_record_respects_interval():
    h = HistoryBuffer(interval=1.0)
    h.record(0.0, {"ts": 0.0, "v": 1})
    h.record(0.4, {"ts": 0.4, "v": 2})
    h.record(1.0, {"ts": 1.0, "v": 3})
    assert [s["v"] for s in h.series(60)] == [1, 3]


def test_series_filters_by_minutes():
    h = HistoryBuffer(interval=0.0)
    for i in range(120):
        h.record(float(i), {"ts": float(i), "v": i})
    series = h.series(1)
    assert series[0]["ts"] >= 119 - 60
    assert series[-1]["ts"] == 119


def test_series_downsampled():
    h = HistoryBuffer(interval=0.0)
    for i in range(600):
        h.record(float(i), {"ts": float(i), "v": i})
    assert len(h.series(60, max_points=100)) <= 100
