import os
import subprocess
from pathlib import Path


def _startup_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def shortcut_path() -> Path:
    return _startup_dir() / "Synpu.lnk"


def is_enabled() -> bool:
    try:
        return shortcut_path().exists()
    except Exception:
        return False


def set_enabled(enabled: bool) -> bool:
    path = shortcut_path()
    try:
        if not enabled:
            if path.exists():
                path.unlink()
            return True
        root = Path(__file__).resolve().parents[2]
        vbs = root / "scripts" / "launch.vbs"
        icon = root / "static" / "icon.ico"
        wscript = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wscript.exe"
        script = (
            "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('" + str(path) + "'); "
            "$s.TargetPath = '" + str(wscript) + "'; "
            "$s.Arguments = '\"" + str(vbs) + "\"'; "
            "$s.WorkingDirectory = '" + str(root) + "'; "
            "$s.IconLocation = '" + str(icon) + "'; "
            "$s.Description = 'Synpu'; "
            "$s.Save()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return path.exists()
    except Exception:
        return False
