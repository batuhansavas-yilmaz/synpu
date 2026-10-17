import json
import threading
import tkinter as tk
from pathlib import Path
from typing import Callable

import pystray
import qrcode
from PIL import Image, ImageDraw, ImageTk

from synpu import config
from synpu.net.addresses import candidate_ips


def build_qr_image(url: str) -> Image.Image:
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").get_image()


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
    img = Image.new("RGB", (64, 64), "#0f1117")
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill="#2b3149")
    draw.text((26, 22), "S", fill="white")
    return img


def run_ui(url_provider: Callable[[], str], state_dir: Path) -> None:
    root = tk.Tk()
    root.title("Synpu — Telefonla Bağlan")
    root.geometry("360x500")
    root.resizable(False, False)
    root.configure(bg="#0f1117")

    qr_label = tk.Label(root, bg="#0f1117", bd=0)
    qr_label.pack(pady=(16, 8))

    url_var = tk.StringVar(value="...")
    tk.Label(root, textvariable=url_var, fg="#e6e8ee", bg="#0f1117",
             font=("Segoe UI", 13, "bold")).pack()

    tk.Label(root, text="Diğer adresler:", fg="#9aa1b2", bg="#0f1117",
             font=("Segoe UI", 10)).pack(pady=(12, 2))
    others = tk.Text(root, height=4, width=42, state="disabled", bd=0,
                     bg="#171a23", fg="#9aa1b2", font=("Segoe UI", 10))
    others.pack()

    def copy_url():
        text = url_var.get()
        if text and text != "...":
            root.clipboard_clear()
            root.clipboard_append(text)

    tk.Button(root, text="Adresi Kopyala", command=copy_url,
              bg="#232735", fg="#e6e8ee", bd=0, padx=12, pady=6).pack(pady=12)

    state = {"url": None}

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
        others.configure(state="normal")
        others.delete("1.0", "end")
        others.insert("1.0", "\n".join(other_lines) if other_lines else "(yok)")
        others.configure(state="disabled")
        root.after(30000, refresh)

    def show_window():
        root.after(0, lambda: (root.deiconify(), root.lift(), root.focus_force()))

    def quit_app():
        try:
            icon.stop()
        except Exception:
            pass
        root.after(0, root.destroy)

    root.protocol("WM_DELETE_WINDOW", root.withdraw)

    icon = pystray.Icon(
        "synpu",
        _tray_image(),
        "Synpu",
        menu=pystray.Menu(
            pystray.MenuItem("QR'ı Göster", lambda: show_window()),
            pystray.MenuItem("Adresi Kopyala", lambda: root.after(0, copy_url)),
            pystray.MenuItem("Çıkış", lambda: quit_app()),
        ),
    )
    threading.Thread(target=icon.run, daemon=True).start()

    refresh()
    if not should_autoshow(state_dir):
        root.withdraw()
    root.mainloop()
    try:
        icon.stop()
    except Exception:
        pass
