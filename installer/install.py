"""
NDR Upload Tracker — Graphical Installer
Click Next through the panels until Finish.
First run only: installs dependencies and creates desktop launcher.
Afterwards, double-click Run_NDR_Upload_Tracker to open the app immediately.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
DATA_DIR = ROOT / "data"


class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NDR Upload Tracker — Setup")
        self.geometry("560x420")
        self.resizable(False, False)
        self.configure(bg="#1a1a1a")
        self.step = 0
        self.install_dir = Path.home() / "NDR_Upload_Tracker_App"
        self._build()
        self.show_step()

    def _build(self):
        self.header = tk.Frame(self, bg="#c41e3a", height=64)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        tk.Label(
            self.header,
            text="NDR UPLOAD TRACKER MONITORING",
            font=("Segoe UI", 14, "bold"),
            fg="white",
            bg="#c41e3a",
        ).pack(side="left", padx=20, pady=18)

        self.body = tk.Frame(self, bg="#1a1a1a")
        self.body.pack(fill="both", expand=True, padx=24, pady=16)

        self.content = tk.Label(
            self.body,
            text="",
            font=("Segoe UI", 11),
            fg="#e5e5e5",
            bg="#1a1a1a",
            justify="left",
            wraplength=500,
            anchor="nw",
        )
        self.content.pack(fill="both", expand=True)

        self.progress = ttk.Progressbar(self.body, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(8, 0))
        self.progress.pack_forget()

        self.footer = tk.Frame(self, bg="#111111", height=56)
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)

        self.btn_back = tk.Button(
            self.footer, text="< Back", width=10, command=self.back,
            bg="#333", fg="white", relief="flat", state="disabled"
        )
        self.btn_back.pack(side="left", padx=16, pady=12)

        self.btn_next = tk.Button(
            self.footer, text="Next >", width=12, command=self.next,
            bg="#c41e3a", fg="white", relief="flat", font=("Segoe UI", 10, "bold")
        )
        self.btn_next.pack(side="right", padx=16, pady=12)

        self.btn_cancel = tk.Button(
            self.footer, text="Cancel", width=10, command=self.destroy,
            bg="#333", fg="white", relief="flat"
        )
        self.btn_cancel.pack(side="right", padx=4, pady=12)

    def show_step(self):
        self.progress.pack_forget()
        self.btn_back.config(state="normal" if self.step > 0 else "disabled")
        if self.step == 0:
            self.content.config(
                text=(
                    "Welcome to the NDR Upload Tracker Setup Wizard.\n\n"
                    "This will install:\n"
                    "  • Interactive monitoring dashboard\n"
                    "  • Desktop drop folder: NDR UPLOAD TRACKER\n"
                    "  • Required Python packages (streamlit, pandas, plotly…)\n"
                    "  • Desktop launcher for one-click start\n\n"
                    "Click Next to continue."
                )
            )
            self.btn_next.config(text="Next >")
        elif self.step == 1:
            self.content.config(
                text=(
                    "Install location:\n\n"
                    f"  {self.install_dir}\n\n"
                    "A folder named “NDR UPLOAD TRACKER” will also be created on your Desktop.\n"
                    "Drop Excel line lists there for automatic analysis.\n\n"
                    "Click Next to install."
                )
            )
            self.btn_next.config(text="Next >")
        elif self.step == 2:
            self.content.config(text="Installing… please wait.\n\nCopying files and installing dependencies.")
            self.progress.pack(fill="x", pady=(8, 0))
            self.btn_next.config(state="disabled")
            self.btn_back.config(state="disabled")
            self.btn_cancel.config(state="disabled")
            threading.Thread(target=self._do_install, daemon=True).start()
        elif self.step == 3:
            self.content.config(
                text=(
                    "Installation complete.\n\n"
                    "How to use:\n"
                    "  1. Drop your facility line list Excel into Desktop\\NDR UPLOAD TRACKER\n"
                    "  2. Double-click “Run_NDR_Upload_Tracker” on the Desktop\n"
                    "  3. The dashboard opens in your default browser\n\n"
                    "Click Finish to close this installer."
                )
            )
            self.btn_next.config(text="Finish", state="normal")
            self.btn_back.config(state="disabled")
            self.btn_cancel.config(state="disabled")

    def next(self):
        if self.step == 3:
            self.destroy()
            return
        if self.step < 2:
            self.step += 1
            self.show_step()
        elif self.step == 2:
            pass  # install thread advances

    def back(self):
        if self.step > 0 and self.step != 2:
            self.step -= 1
            self.show_step()

    def _do_install(self):
        try:
            self._set_progress(10)
            # Copy application
            if self.install_dir.exists():
                shutil.rmtree(self.install_dir, ignore_errors=True)
            self.install_dir.mkdir(parents=True, exist_ok=True)
            for name in ("app", "data"):
                src = ROOT / name
                dst = self.install_dir / name
                if src.exists():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
            shutil.copy2(ROOT / "requirements.txt", self.install_dir / "requirements.txt")
            self._set_progress(35)

            # Desktop drop folder + sample
            home = Path.home()
            desktop = home / "Desktop"
            if not desktop.exists():
                desktop = home / "OneDrive" / "Desktop"
            if not desktop.exists():
                desktop = home
            drop = desktop / "NDR UPLOAD TRACKER"
            drop.mkdir(parents=True, exist_ok=True)
            sample = self.install_dir / "data" / "NDR_Facility_LineList.xlsx"
            if sample.exists():
                shutil.copy2(sample, drop / "NDR_Facility_LineList.xlsx")
            self._set_progress(50)

            # Install Python packages
            req = self.install_dir / "requirements.txt"
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", str(req), "--quiet"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._set_progress(85)

            # Create launcher scripts on Desktop and in install dir
            run_py = self.install_dir / "app" / "run_app.py"
            launcher_py = desktop / "Run_NDR_Upload_Tracker.py"
            launcher_py.write_text(
                f'import runpy\nrunpy.run_path(r"{run_py}", run_name="__main__")\n',
                encoding="utf-8",
            )
            # Windows .bat helper
            bat = desktop / "Run_NDR_Upload_Tracker.bat"
            bat.write_text(
                f'@echo off\n"{sys.executable}" "{run_py}"\npause\n',
                encoding="utf-8",
            )
            # Also in install dir
            (self.install_dir / "Run_NDR_Upload_Tracker.bat").write_text(
                f'@echo off\n"{sys.executable}" "{run_py}"\n',
                encoding="utf-8",
            )
            self._set_progress(100)
            self.after(0, self._install_done)
        except Exception as e:
            self.after(0, lambda: self._install_fail(str(e)))

    def _set_progress(self, value: int):
        self.after(0, lambda: self.progress.configure(value=value))

    def _install_done(self):
        self.step = 3
        self.show_step()

    def _install_fail(self, err: str):
        messagebox.showerror("Installation failed", err)
        self.btn_next.config(state="normal", text="Next >")
        self.btn_cancel.config(state="normal")
        self.step = 1
        self.show_step()


if __name__ == "__main__":
    # Detect already installed — if launcher exists and packages ok, offer run
    app = InstallerApp()
    app.mainloop()
