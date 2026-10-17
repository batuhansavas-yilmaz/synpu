import csv
import io
import subprocess
import threading
import time
from pathlib import Path

from synpu.metrics.models import FpsStats


class FpsTracker:
    def __init__(self, exclude_apps: frozenset[str], stale_s: float):
        self._exclude = {a.lower() for a in exclude_apps}
        self._stale_s = stale_s
        self._app_idx: int | None = None
        self._ms_idx: int | None = None
        self._latest: dict[str, tuple[float, float]] = {}

    def feed_line(self, line: str) -> None:
        try:
            row = next(csv.reader(io.StringIO(line)))
        except Exception:
            return
        if "Application" in row and "MsBetweenPresents" in row:
            self._app_idx = row.index("Application")
            self._ms_idx = row.index("MsBetweenPresents")
            return
        if self._app_idx is None or self._ms_idx is None:
            return
        try:
            app = str(row[self._app_idx]).strip()
            ms = float(row[self._ms_idx])
        except (IndexError, ValueError):
            return
        if not app or ms <= 0:
            return
        self._latest[app] = (time.monotonic(), ms)

    def current(self, now: float) -> FpsStats:
        best: tuple[float, str, float] | None = None
        for app, (ts, ms) in self._latest.items():
            if app.lower() in self._exclude:
                continue
            if now - ts > self._stale_s:
                continue
            if best is None or ts > best[0]:
                best = (ts, app, ms)
        if best is None:
            return FpsStats(app=None, value=None)
        return FpsStats(app=best[1], value=1000.0 / best[2])


class PresentMonSampler:
    def __init__(self, exe_path: Path, tracker: FpsTracker):
        self._exe = Path(exe_path)
        self._tracker = tracker
        self._proc: subprocess.Popen | None = None

    def start(self) -> None:
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self) -> None:
        if not self._exe.exists():
            return
        try:
            self._proc = subprocess.Popen(
                [
                    str(self._exe),
                    "--output_stdout",
                    "--no_console_stats",
                    "--stop_existing_session",
                    "--session_name",
                    "SynpuSession",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            self._proc = None
            return
        try:
            for line in self._proc.stdout:
                self._tracker.feed_line(line)
        except Exception:
            pass

    def stop(self) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
