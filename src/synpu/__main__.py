import os
import socket
import sys
import threading
import time
from pathlib import Path

HEADLESS = sys.stderr is None
if HEADLESS:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")

import psutil
import uvicorn

from synpu import config
from synpu.metrics.battery import read_battery
from synpu.metrics.collector import MetricsCollector
from synpu.metrics.cpu import read_cpu
from synpu.metrics.disk_io import DiskDeviceMap, DiskSpeedMeter
from synpu.metrics.display import DisplayInfoReader
from synpu.metrics.fps import FpsTracker, PresentMonSampler, foreground_pid
from synpu.metrics.gpu import read_gpu
from synpu.metrics.hardware_monitor import CpuTempReader
from synpu.metrics.motherboard import MotherboardReader
from synpu.metrics.net import NetSpeedMeter
from synpu.metrics.network_meta import IspReader, LatencyReader, WifiReader
from synpu.metrics.processes import ProcessTopReader
from synpu.metrics.ram import RamInfoReader, read_ram
from synpu.metrics.smart import SmartTempReader
from synpu.metrics.storage import read_disks
from synpu.net.addresses import primary_ip
from synpu.server.app import create_app
from synpu.ui.qr_window import run_ui
from synpu.updates import background_loop as update_loop

ROOT = Path(__file__).resolve().parents[2]
PRESENTMON_EXE = ROOT / "third_party" / "presentmon" / "PresentMon.exe"
LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
STATE_DIR = Path(LOCALAPPDATA) / "Synpu"
EXCLUDE_APPS = frozenset({
    "dwm.exe",
    "applicationframehost.exe",
    "explorer.exe",
    "searchhost.exe",
    "textinputhost.exe",
    "shellexperiencehost.exe",
})


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
            return False
        except OSError:
            return True


def _wait_port_free(port: int, timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _port_in_use(port):
            return True
        time.sleep(0.5)
    return not _port_in_use(port)


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
    if not _wait_port_free(config.PORT):
        _fail(
            f"Port {config.PORT} kullanımda — Synpu zaten çalışıyor olabilir.\n"
            f"Farklı port için SYNPU_PORT ortam değişkenini ayarlayın (örn. SYNPU_PORT=8788)."
        )

    tracker = FpsTracker(exclude_apps=EXCLUDE_APPS, stale_s=config.FPS_STALE_S)
    sampler = PresentMonSampler(PRESENTMON_EXE, tracker)
    if PRESENTMON_EXE.exists():
        sampler.start()

    temp_reader = CpuTempReader()
    disk_meter = DiskSpeedMeter()
    disk_map = DiskDeviceMap()
    collector = MetricsCollector(
        cpu_source=read_cpu,
        gpu_source=read_gpu,
        ram_source=read_ram,
        fps_source=lambda now: tracker.current(now, foreground_pid()),
        hw_reader=temp_reader.read,
        storage_source=read_disks,
        net_meter=NetSpeedMeter(),
        disk_temp_source=SmartTempReader().read,
        ram_info_source=RamInfoReader().read,
        battery_source=read_battery,
        uptime_source=lambda: time.time() - psutil.boot_time(),
        disk_io_source=disk_meter.update,
        disk_map_source=disk_map.read,
        display_source=DisplayInfoReader().read,
        motherboard_source=MotherboardReader().read,
        top_source=ProcessTopReader().read,
        wifi_source=WifiReader().read,
        isp_source=IspReader(state_path=STATE_DIR / "isp.json").read,
        ping_source=LatencyReader().read,
        history_path=STATE_DIR / "history.json",
        ttl=config.PUSH_INTERVAL_S,
    )

    show_event = threading.Event()
    app = create_app(collector, on_show=show_event.set)
    server = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": "0.0.0.0", "port": config.PORT, "log_level": "warning"},
        daemon=True,
    )
    server.start()

    def sampling_loop() -> None:
        while True:
            time.sleep(1.0)
            try:
                collector.snapshot()
            except Exception:
                pass

    threading.Thread(target=sampling_loop, daemon=True).start()
    threading.Thread(target=update_loop, daemon=True).start()

    try:
        run_ui(_url_provider, STATE_DIR, show_event=show_event)
    finally:
        try:
            collector.history.flush()
        except Exception:
            pass
        sampler.stop()


def _url_provider() -> str | None:
    ip = primary_ip()
    return f"http://{ip}:{config.PORT}" if ip else None


if __name__ == "__main__":
    main()
