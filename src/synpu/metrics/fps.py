import csv
import ctypes
import io
import subprocess
import threading
import time
from pathlib import Path

from synpu.metrics.models import FpsStats


def foreground_pid() -> int | None:
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value) or None
    except Exception:
        return None


class FpsTracker:
    def __init__(self, exclude_apps: frozenset[str], stale_s: float):
        self._exclude = {a.lower() for a in exclude_apps}
        self._stale_s = stale_s
        self._app_idx: int | None = None
        self._ms_idx: int | None = None
        self._pid_idx: int | None = None
        self._latest: dict[str, tuple[float, float, int | None]] = {}

    def feed_line(self, line: str) -> None:
        try:
            row = next(csv.reader(io.StringIO(line)))
        except Exception:
            return
        if "Application" in row and "MsBetweenPresents" in row:
            self._app_idx = row.index("Application")
            self._ms_idx = row.index("MsBetweenPresents")
            self._pid_idx = row.index("ProcessID") if "ProcessID" in row else None
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
        pid = None
        if self._pid_idx is not None:
            try:
                pid = int(row[self._pid_idx])
            except (IndexError, ValueError):
                pid = None
        self._latest[app] = (time.monotonic(), ms, pid)

    def current(self, now: float, foreground_pid: int | None = None) -> FpsStats:
        best: tuple[float, str, float] | None = None
        items = list(self._latest.items())
        for app, (ts, ms, pid) in items:
            if now - ts > self._stale_s:
                self._latest.pop(app, None)
                continue
            if app.lower() in self._exclude:
                continue
            if foreground_pid is not None and pid != foreground_pid:
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
        self._stop_event = threading.Event()

    def start(self) -> None:
        if not self._exe.exists():
            return
        self._stop_event.clear()
        self._spawn()
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _spawn(self) -> None:
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

    def _read_loop(self) -> None:
        while not self._stop_event.is_set():
            proc = self._proc
            if proc is None:
                self._spawn()
                proc = self._proc
                if proc is None:
                    self._stop_event.wait(5.0)
                    continue
            try:
                for line in proc.stdout:
                    self._tracker.feed_line(line)
                    if self._stop_event.is_set():
                        break
            except Exception:
                pass
            if self._stop_event.is_set():
                break
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            self._proc = None
            self._stop_event.wait(5.0)

    def stop(self) -> None:
        self._stop_event.set()
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
