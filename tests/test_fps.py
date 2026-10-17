import time
from pathlib import Path

from synpu.metrics.fps import FpsTracker, PresentMonSampler
from synpu.metrics.models import FpsStats

HEADER = "Application,ProcessID,SwapChainAddress,MsBetweenPresents,MsBetweenDisplayChange"
ROW_GAME = "game.exe,1234,0x1,10.0,16.7"


def _tracker():
    return FpsTracker(exclude_apps=frozenset({"dwm.exe"}), stale_s=2.0)


def test_tracker_parses_and_computes_fps():
    t = _tracker()
    t.feed_line(HEADER)
    t.feed_line(ROW_GAME)
    fps = t.current(time.monotonic())
    assert fps.app == "game.exe"
    assert abs(fps.value - 100.0) < 1e-6


def test_tracker_excludes_dwm_and_stale():
    t = _tracker()
    t.feed_line(HEADER)
    t.feed_line("dwm.exe,99,0x1,10.0,16.7")
    assert t.current(time.monotonic()) == FpsStats(None, None)
    t.feed_line(ROW_GAME)
    assert t.current(time.monotonic()).app == "game.exe"
    assert t.current(time.monotonic() + 3.0) == FpsStats(None, None)


def test_malformed_lines_ignored():
    t = _tracker()
    t.feed_line(HEADER)
    t.feed_line("")
    t.feed_line("garbage")
    t.feed_line("too,few")
    t.feed_line("game.exe,1234,0x1,notanumber,16.7")
    assert t.current(time.monotonic()) == FpsStats(None, None)
    t.feed_line(ROW_GAME)
    assert t.current(time.monotonic()).app == "game.exe"


def test_tracker_foreground_only():
    t = _tracker()
    t.feed_line(HEADER)
    t.feed_line(ROW_GAME)
    assert t.current(time.monotonic(), foreground_pid=999) == FpsStats(None, None)
    assert t.current(time.monotonic(), foreground_pid=1234).app == "game.exe"


def test_sampler_missing_exe_does_not_raise():
    sampler = PresentMonSampler(Path("definitely_missing_presentmon.exe"), _tracker())
    sampler.start()
    sampler.stop()
