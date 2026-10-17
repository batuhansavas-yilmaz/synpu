import json
import re
import threading
import time
import urllib.request
from importlib import metadata

REPO = "batuhansavas-yilmaz/synpu"
CHECK_INTERVAL_S = 24 * 3600


def local_version() -> str:
    try:
        return metadata.version("synpu")
    except Exception:
        return "0.1.0"


_state_lock = threading.Lock()
_state = {
    "version": local_version(),
    "latest": None,
    "update_available": False,
    "url": f"https://github.com/{REPO}/releases/latest",
    "checked_at": 0.0,
}


def _version_tuple(text: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", text or ""))


def refresh() -> None:
    try:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/releases/latest",
            headers={"User-Agent": "synpu-update-check", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        latest = str(data.get("tag_name", "")).lstrip("vV")
        url = str(data.get("html_url") or _state["url"])
        available = bool(latest) and _version_tuple(latest) > _version_tuple(_state["version"])
        with _state_lock:
            _state.update({
                "latest": latest or None,
                "update_available": available,
                "url": url,
                "checked_at": time.time(),
            })
    except Exception:
        pass


def update_info() -> dict:
    with _state_lock:
        return dict(_state)


def background_loop(interval: float = CHECK_INTERVAL_S) -> None:
    while True:
        refresh()
        time.sleep(interval)
