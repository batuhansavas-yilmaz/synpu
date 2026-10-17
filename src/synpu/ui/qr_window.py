import json
import threading
import tkinter as tk
from pathlib import Path
from typing import Callable

import pystray
import qrcode
from PIL import Image, ImageDraw, ImageTk

from synpu import config, startup
from synpu.net.addresses import candidate_ips

BG = "#0a1124"
PANEL = "#0f1a33"
BORDER = "#24365e"
TEXT = "#e8eefc"
MUTED = "#8b97ad"
ACCENT = "#2563eb"


def build_qr_image(url: str) -> Image.Image:
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").get_image()


def _system_uses_light_theme() -> bool:
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return bool(value)
    except Exception:
        return True


def _apply_titlebar_theme(root: tk.Tk) -> None:
    try:
        import ctypes

        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        value = ctypes.c_int(0 if _system_uses_light_theme() else 1)
        for attribute in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
            )
            if result == 0:
                break
    except Exception:
        pass


def should_autoshow(state_dir: Path) -> bool:
    state_file = state_dir / "state.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            state = {}
    except Exception:
        state = {}
    if state.get("first_run_done"):
        return False
    state["first_run_done"] = True
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state), encoding="utf-8")
    except Exception:
        pass
    return True


def _tray_image() -> Image.Image:
    img = Image.new("RGB", (64, 64), "#0a1124")
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill="#1b2a4a")
    draw.text((26, 22), "S", fill="white")
    return img


def _app_icon(size: int) -> Image.Image:
    path = Path(__file__).resolve().parents[3] / "static" / "icon-192.png"
    try:
        return Image.open(path).convert("RGBA").resize((size, size))
    except Exception:
        return _tray_image().resize((size, size))


def run_ui(url_provider: Callable[[], "str | None"], state_dir: Path,
           show_event: threading.Event | None = None) -> None:
    root = tk.Tk()
    root.title("Synpu — Telefonla Bağlan")
    root.geometry("380x640")
    root.resizable(False, False)
    root.configure(bg=BG)
    try:
        icon_photo = ImageTk.PhotoImage(_app_icon(64))
        root.iconphoto(False, icon_photo)
        root._icon_photo = icon_photo
    except Exception:
        pass
    ico_path = Path(__file__).resolve().parents[3] / "static" / "icon.ico"
    try:
        root.iconbitmap(str(ico_path))
    except Exception:
        pass
    root.update_idletasks()
    _apply_titlebar_theme(root)

    header = tk.Frame(root, bg=BG)
    header.pack(fill="x", padx=20, pady=(18, 10))
    try:
        logo_photo = ImageTk.PhotoImage(_app_icon(44))
        logo_label = tk.Label(header, image=logo_photo, bg=BG, bd=0)
        logo_label.image = logo_photo
        logo_label.pack(side="left")
    except Exception:
        pass
    title_box = tk.Frame(header, bg=BG)
    title_box.pack(side="left", padx=(10, 0))
    tk.Label(title_box, text="Synpu", fg=TEXT, bg=BG,
             font=("Segoe UI", 17, "bold")).pack(anchor="w")
    tk.Label(title_box, text="Telefonla bağlanmak için QR'ı okut", fg=MUTED, bg=BG,
             font=("Segoe UI", 9)).pack(anchor="w")

    qr_panel = tk.Frame(root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    qr_panel.pack(padx=20)
    qr_label = tk.Label(qr_panel, bg="white", bd=0, padx=12, pady=12)
    qr_label.pack(padx=14, pady=14)

    url_var = tk.StringVar(value="Ağ bekleniyor...")
    tk.Label(root, textvariable=url_var, fg=TEXT, bg=BG,
             font=("Segoe UI", 14, "bold")).pack(pady=(12, 2))

    def copy_url():
        text = state["url"]
        if text:
            root.clipboard_clear()
            root.clipboard_append(text)

    def open_browser():
        url = state["url"] or f"http://127.0.0.1:{config.PORT}"
        try:
            import webbrowser

            webbrowser.open(url)
        except Exception:
            pass

    def open_github():
        try:
            import webbrowser

            webbrowser.open("https://github.com/batuhansavas-yilmaz/synpu/releases")
        except Exception:
            pass

    buttons = tk.Frame(root, bg=BG)
    buttons.pack(pady=(8, 14))
    tk.Button(buttons, text="Tarayıcıda Aç", command=open_browser, bg=ACCENT, fg="white",
              activebackground="#1d4ed8", activeforeground="white", relief="flat",
              bd=0, padx=14, pady=7, font=("Segoe UI", 10, "bold"),
              cursor="hand2").pack(side="left", padx=(0, 8))
    tk.Button(buttons, text="Adresi Kopyala", command=copy_url, bg="#182543", fg=TEXT,
              activebackground="#223355", activeforeground=TEXT, relief="flat",
              bd=0, padx=14, pady=7, font=("Segoe UI", 10),
              cursor="hand2").pack(side="left")

    tk.Label(root, text="Diğer adresler", fg=MUTED, bg=BG,
             font=("Segoe UI", 8)).pack()
    others_label = tk.Label(root, text="(yok)", fg=MUTED, bg=BG, font=("Segoe UI", 9))
    others_label.pack(pady=(2, 4))

    tk.Label(root, text="Pencereyi kapatabilirsin — Synpu tepside çalışmaya devam eder.",
             fg=MUTED, bg=BG, font=("Segoe UI", 8), wraplength=320,
             justify="center").pack(side="bottom", pady=(0, 14))

    state: dict = {"url": None}

    def refresh():
        try:
            url = url_provider()
        except Exception:
            url = None
        if not url:
            state["url"] = None
            qr_label.configure(image="")
            qr_label.image = None
            url_var.set("Ağ bekleniyor...")
        elif url != state["url"]:
            state["url"] = url
            photo = ImageTk.PhotoImage(build_qr_image(url))
            qr_label.configure(image=photo)
            qr_label.image = photo
            url_var.set(url)
        try:
            lines = [f"http://{ip}:{config.PORT}" for ip in candidate_ips()]
        except Exception:
            lines = []
        other_lines = [line for line in lines if line != state["url"]]
        others_label.configure(text="\n".join(other_lines) if other_lines else "(yok)")
        root.after(30000, refresh)

    def show_window():
        def reveal():
            root.deiconify()
            _apply_titlebar_theme(root)
            root.lift()
            root.focus_force()

        root.after(0, reveal)

    def quit_app():
        try:
            icon.stop()
        except Exception:
            pass
        root.after(0, root.destroy)

    def toggle_startup(tray_icon, item):
        try:
            startup.set_enabled(not startup.is_enabled())
            tray_icon.update_menu()
        except Exception:
            pass

    root.protocol("WM_DELETE_WINDOW", root.withdraw)

    icon = pystray.Icon(
        "synpu",
        _app_icon(64),
        "Synpu",
        menu=pystray.Menu(
            pystray.MenuItem("QR'ı Göster", lambda: show_window(),
                             default=True, visible=False),
            pystray.MenuItem(
                "Başlangıçta çalıştır",
                toggle_startup,
                checked=lambda item: startup.is_enabled(),
            ),
            pystray.MenuItem("Hakkında", lambda: open_github()),
            pystray.MenuItem("Çıkış", lambda: quit_app()),
        ),
    )
    threading.Thread(target=icon.run, daemon=True).start()

    def poll_show():
        if show_event is not None and show_event.is_set():
            show_event.clear()
            show_window()
        root.after(250, poll_show)

    refresh()
    poll_show()
    if not should_autoshow(state_dir):
        root.withdraw()
    root.mainloop()
    try:
        icon.stop()
    except Exception:
        pass
