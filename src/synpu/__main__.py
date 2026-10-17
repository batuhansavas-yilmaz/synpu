import os
import socket
import sys
import threading
from pathlib import Path

HEADLESS = sys.stderr is None
if HEADLESS:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")

import uvicorn

from synpu import config
from synpu.metrics.collector import MetricsCollector
from synpu.metrics.cpu import read_cpu
from synpu.metrics.fps import FpsTracker, PresentMonSampler
from synpu.metrics.gpu import read_gpu
from synpu.metrics.hardware_monitor import CpuTempReader
from synpu.metrics.ram import read_ram
from synpu.net.addresses import primary_ip
from synpu.server.app import create_app
from synpu.ui.qr_window import run_ui

ROOT = Path(__file__).resolve().parents[2]
PRESENTMON_EXE = ROOT / "third_party" / "presentmon" / "PresentMon.exe"
STATE_DIR = Path.home() / "AppData" / "Local" / "Synpu"
EXCLUDE_APPS = frozenset({
    "dwm.exe",
    "application frame host",
    "explorer.exe",
    "searchhost.exe",
    "textinputhost.exe",
})


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
            return False
        except OSError:
            return True


def _fail(message: str) -> None:
    if not HEADLESS and sys.stderr is not None:
        print(message, file=sys.stderr)
    if HEADLESS:
        try:
            import tkinter.messagebox as messagebox

            messagebox.showerror("Synpu", message)
        except Exception:
            pass
    sys.exit(1)


def main() -> None:
    if _port_in_use(config.PORT):
        _fail(
            f"Port {config.PORT} kullanımda — Synpu zaten çalışıyor olabilir.\n"
            f"Farklı port için SYNPU_PORT ortam değişkenini ayarlayın (örn. SYNPU_PORT=8788)."
        )

    tracker = FpsTracker(exclude_apps=EXCLUDE_APPS, stale_s=config.FPS_STALE_S)
    sampler = PresentMonSampler(PRESENTMON_EXE, tracker)
    if PRESENTMON_EXE.exists():
        sampler.start()

    temp_reader = CpuTempReader()
    collector = MetricsCollector(
        cpu_source=read_cpu,
        gpu_source=read_gpu,
        ram_source=read_ram,
        fps_source=tracker.current,
        temp_reader=temp_reader.read,
    )

    app = create_app(collector)
    server = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": "0.0.0.0", "port": config.PORT, "log_level": "warning"},
        daemon=True,
    )
    server.start()

    try:
        run_ui(lambda: f"http://{primary_ip()}:{config.PORT}", STATE_DIR)
    finally:
        sampler.stop()


if __name__ == "__main__":
    main()
