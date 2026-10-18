from synpu.metrics.runtime import RuntimeClock, read_install_id


def test_read_install_id_marker(tmp_path):
    (tmp_path / "installed_at").write_text("1700000000", encoding="utf-8")
    assert read_install_id(tmp_path, tmp_path) == 1700000000.0


def test_runtime_clock_resumes_from_saved_total(tmp_path):
    (tmp_path / "runtime.json").write_text(
        '{"install_id": 123.0, "total_s": 100.0}', encoding="utf-8"
    )
    clock = RuntimeClock(tmp_path, 123.0, save_interval=999)
    assert clock.total() >= 100


def test_runtime_clock_resets_when_install_id_changes(tmp_path):
    (tmp_path / "runtime.json").write_text(
        '{"install_id": 123.0, "total_s": 100.0}', encoding="utf-8"
    )
    clock = RuntimeClock(tmp_path, 456.0, save_interval=999)
    assert clock.total() < 5
