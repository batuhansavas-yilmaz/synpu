import json
import os
import time
from pathlib import Path


def read_install_id(state_dir: Path, app_root: Path) -> float | None:
    try:
        raw = (state_dir / "installed_at").read_text(encoding="utf-8").strip()
        if raw:
            return float(raw)
    except Exception:
        pass
    try:
        return os.path.getctime(app_root)
    except Exception:
        return None


class RuntimeClock:
    def __init__(self, state_dir: Path, install_id: float | None,
                 save_interval: float = 20.0):
        self._dir = Path(state_dir)
        self._file = self._dir / "runtime.json"
        self._install_id = install_id
        self._save_interval = save_interval
        self._total = 0.0
        self._started = time.monotonic()
        self._last_save = self._started
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, dict):
            return
        if self._install_id is not None and data.get("install_id") != self._install_id:
            return
        try:
            self._total = max(0.0, float(data.get("total_s") or 0.0))
        except (TypeError, ValueError):
            self._total = 0.0

    def _now(self) -> float:
        return self._total + max(0.0, time.monotonic() - self._started)

    def _save(self, total: float | None = None) -> None:
        if total is None:
            total = self._now()
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            payload = {"install_id": self._install_id, "total_s": round(total, 3)}
            self._file.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass

    def total(self) -> int:
        now = time.monotonic()
        total = self._now()
        if now - self._last_save >= self._save_interval:
            self._last_save = now
            self._save(total)
        return int(total)

    def flush(self) -> None:
        self._save()
