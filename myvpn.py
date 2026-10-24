#!/usr/bin/env python3
"""
MyVPN - Desktop efarmogi VPN (Windows / Linux / macOS)

Kathe server einai ena WireGuard arxeio .conf mesa ston fakelo "servers/".
To onoma tou arxeiou einai to onoma pou fainetai sti lista
(p.x. servers/Germany.conf, servers/Greece.conf).

Prepei na trexei me dikaiomata diaxeiristi:
  Windows:      deksi klik -> "Run as administrator"
  Linux/macOS:  sudo python3 myvpn.py
Xreiazetai egkatestimeno to WireGuard (https://www.wireguard.com/install/).
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import messagebox, ttk

APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
SERVERS_DIR = Path(__file__).resolve().parent / "servers"
IFACE = "myvpn0"  # onoma tunnel
SYSTEM = platform.system()  # "Windows", "Linux", "Darwin"


# ---------------------------------------------------------------- backend
def is_admin() -> bool:
    if SYSTEM == "Windows":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.geteuid() == 0


def find_wireguard() -> str | None:
    if SYSTEM == "Windows":
        for p in (r"C:\Program Files\WireGuard\wireguard.exe",
                  r"C:\Program Files (x86)\WireGuard\wireguard.exe"):
            if Path(p).exists():
                return p
        return shutil.which("wireguard")
    return shutil.which("wg-quick")


def run(cmd: list[str]) -> tuple[bool, str]:
    kw = {}
    if SYSTEM == "Windows":
        kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kw)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return False, str(e)


class VPN:
    def __init__(self):
        self.tool = find_wireguard()
        self.workdir = Path(tempfile.gettempdir()) / "myvpn"
        self.workdir.mkdir(exist_ok=True)
        self.conf_path = self.workdir / f"{IFACE}.conf"
        self.connected_to: str | None = None

    def is_up(self) -> bool:
        if SYSTEM == "Windows":
            ok, out = run(["sc", "query", f"WireGuardTunnel${IFACE}"])
            return ok and "RUNNING" in out
        wg = shutil.which("wg")
        if not wg:
            return False
        ok, out = run([wg, "show", "interfaces"])
        if SYSTEM == "Darwin":  # sto macOS to onoma antistoixei se utunX
            return ok and bool(out) and Path(f"/var/run/wireguard/{IFACE}.name").exists()
        return ok and IFACE in out.split()

    def connect(self, server_conf: Path) -> tuple[bool, str]:
        if not self.tool:
            return False, "Den vrethike to WireGuard. Egkatestise to apo wireguard.com/install"
        if self.is_up():
            ok, msg = self.disconnect()
            if not ok:
                return False, msg
        shutil.copyfile(server_conf, self.conf_path)
        if SYSTEM != "Windows":
            os.chmod(self.conf_path, 0o600)
            ok, out = run([self.tool, "up", str(self.conf_path)])
        else:
            ok, out = run([self.tool, "/installtunnelservice", str(self.conf_path)])
        if ok:
            self.connected_to = server_conf.stem
        return ok, out

    def disconnect(self) -> tuple[bool, str]:
        if not self.tool:
            return False, "Den vrethike to WireGuard."
        if SYSTEM == "Windows":
            ok, out = run([self.tool, "/uninstalltunnelservice", IFACE])
        else:
            ok, out = run([self.tool, "down", str(self.conf_path)])
        if ok:
            self.connected_to = None
        return ok, out


def public_ip_info() -> str:
    try:
        with urllib.request.urlopen("https://ipinfo.io/json", timeout=6) as r:
            d = json.load(r)
        return f"{d.get('ip', '?')}  ({d.get('city', '')}, {d.get('country', '')})"
    except Exception:
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=6) as r:
                return r.read().decode()
        except Exception:
            return "agnosti"


def load_servers() -> list[Path]:
    SERVERS_DIR.mkdir(exist_ok=True)
    return sorted(p for p in SERVERS_DIR.glob("*.conf")
                  if re.search(r"^\s*\[Peer\]", p.read_text(errors="ignore"), re.M))


# ---------------------------------------------------------------- GUI
class App(tk.Tk):
    BG, FG, GREEN, RED, CARD = "#14161c", "#e8eaf0", "#2ecc71", "#e74c3c", "#1f232c"

    def __init__(self):
        super().__init__()
        self.vpn = VPN()
        self.title("MyVPN")
        self.geometry("380x520")
        self.resizable(False, False)
        self.configure(bg=self.BG)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=self.CARD, background=self.CARD,
                        foreground=self.FG, arrowcolor=self.FG)

        tk.Label(self, text="MyVPN", font=("Segoe UI", 24, "bold"),
                 bg=self.BG, fg=self.FG).pack(pady=(24, 4))
        self.status = tk.Label(self, text="", font=("Segoe UI", 12), bg=self.BG)
        self.status.pack()

        self.btn = tk.Canvas(self, width=170, height=170, bg=self.BG, highlightthickness=0,
                             cursor="hand2")
        self.btn.pack(pady=22)
        self.btn.bind("<Button-1>", lambda _: self.toggle())

        tk.Label(self, text="Server", font=("Segoe UI", 10), bg=self.BG,
                 fg="#9aa0ad").pack()
        self.server_var = tk.StringVar()
        self.combo = ttk.Combobox(self, textvariable=self.server_var, state="readonly",
                                  width=28, font=("Segoe UI", 11))
        self.combo.pack(pady=4)
        tk.Button(self, text="Ananeosi listas", command=self.refresh_servers,
                  bg=self.CARD, fg=self.FG, relief="flat", activebackground="#2a2f3a",
                  activeforeground=self.FG).pack(pady=4)

        self.ip_lbl = tk.Label(self, text="IP: ...", font=("Segoe UI", 10),
                               bg=self.BG, fg="#9aa0ad")
        self.ip_lbl.pack(pady=(16, 0))

        self.busy = False
        self.refresh_servers()
        self.update_ui()
        self.check_ip()
        self.after(100, self.startup_checks)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- helpers
    def startup_checks(self):
        if not is_admin():
            hint = ("Kane deksi klik -> Run as administrator" if SYSTEM == "Windows"
                    else "Trexe: sudo python3 myvpn.py")
            messagebox.showwarning("MyVPN", f"Xreiazontai dikaiomata diaxeiristi.\n{hint}")
        if not self.vpn.tool:
            messagebox.showwarning("MyVPN", "Den vrethike to WireGuard.\n"
                                   "Egkatestise to apo https://www.wireguard.com/install/")
        if not self.servers:
            messagebox.showinfo("MyVPN", f"Den yparxoun servers.\nVale arxeia .conf ston "
                                f"fakelo:\n{SERVERS_DIR}")

    def refresh_servers(self):
        self.servers = load_servers()
        names = [p.stem for p in self.servers]
        self.combo["values"] = names
        if names and self.server_var.get() not in names:
            self.server_var.set(names[0])

    def draw_button(self, color, label):
        c = self.btn
        c.delete("all")
        c.create_oval(8, 8, 162, 162, outline=color, width=4)
        c.create_oval(22, 22, 148, 148, fill=self.CARD, outline="")
        c.create_text(85, 85, text=label, fill=color, font=("Segoe UI", 15, "bold"))

    def update_ui(self, connecting=False):
        if connecting:
            self.status.config(text="Syndesi...", fg="#f1c40f")
            self.draw_button("#f1c40f", "...")
            return
        up = self.vpn.is_up()
        if up:
            name = self.vpn.connected_to or "VPN"
            self.status.config(text=f"Syndedemeno - {name}", fg=self.GREEN)
            self.draw_button(self.GREEN, "DISCONNECT")
        else:
            self.status.config(text="Aposyndedemeno", fg=self.RED)
            self.draw_button(self.RED, "CONNECT")
        self.combo.config(state="disabled" if up else "readonly")

    def check_ip(self):
        self.ip_lbl.config(text="IP: ...")
        threading.Thread(target=lambda: self.after(
            0, self.ip_lbl.config, {"text": "IP: " + public_ip_info()}), daemon=True).start()

    # --- actions
    def toggle(self):
        if self.busy:
            return
        up = self.vpn.is_up()
        if not up:
            name = self.server_var.get()
            match = [p for p in self.servers if p.stem == name]
            if not match:
                messagebox.showerror("MyVPN", "Dialekse server.")
                return
        self.busy = True
        self.update_ui(connecting=True)

        def work():
            ok, msg = self.vpn.disconnect() if up else self.vpn.connect(match[0])
            self.after(0, self.done, ok, msg)
        threading.Thread(target=work, daemon=True).start()

    def done(self, ok, msg):
        self.busy = False
        if not ok:
            messagebox.showerror("MyVPN", f"Apotyxia:\n{msg[-800:]}")
        self.update_ui()
        self.after(1500, self.check_ip)

    def on_close(self):
        if self.vpn.is_up() and messagebox.askyesno("MyVPN", "Aposyndesi prin to kleisimo?"):
            self.vpn.disconnect()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
