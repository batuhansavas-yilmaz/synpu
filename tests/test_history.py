import time

from synpu.metrics.history import HistoryBuffer


def test_history_series_uses_active_time():
    h = HistoryBuffer(interval=0.0)
    base = 1000.0
    h.record(base, {"ts": base, "active_ts": 0.0, "v": 1.0})
    h.record(base + 60, {"ts": base + 60, "active_ts": 60.0, "v": 2.0})
    h.record(base + 120, {"ts": base + 120, "active_ts": 120.0, "v": 3.0})
    assert [s["v"] for s in h.series(1)] == [2.0, 3.0]

def test_history_persists_across_instances(tmp_path):
    path = tmp_path / "history.json"
    h = HistoryBuffer(interval=0.0, path=path, save_interval=0.0)
    now = time.time()
    for i in range(5):
        h.record(now + i, {"ts": now + i, "v": float(i)})
    h.flush()
    assert path.exists()
    restored = HistoryBuffer(interval=0.0, path=path)
    series = restored.series(60)
    assert [sample["v"] for sample in series] == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_minute_aggregate_persists(tmp_path):
    path = tmp_path / "history.json"
    h = HistoryBuffer(interval=0.0, path=path, save_interval=0.0)
    now = time.time()
    h.record(now, {"ts": now, "v": 0.0})
    h.record(now + 61, {"ts": now + 61, "v": 2.0})
    h.flush()
    restored = HistoryBuffer(interval=0.0, path=path)
    series = restored.series(120)
    assert len(series) == 1
    assert series[0]["v"] == 1.0



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


def test_long_ranges_use_minute_buffer():
    h = HistoryBuffer(interval=0.0)
    for i in range(121):
        h.record(float(i), {"ts": float(i), "v": float(i)})
    assert len(h.series(60)) == 121
    long_series = h.series(120)
    assert 2 <= len(long_series) <= 4
    assert long_series[-1]["ts"] == 120
    assert all("v" in sample for sample in long_series)


def test_long_range_falls_back_to_raw_until_minute_buffer_fills():
    h = HistoryBuffer(interval=0.0)
    for i in range(30):
        h.record(float(i), {"ts": float(i), "v": float(i)})
    assert len(h.series(720)) == 30


