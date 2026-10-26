"""
NDR Upload Tracker — Application Launcher
Double-click this file after installation to start the dashboard.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent


def find_free_port(start: int = 8501) -> int:
    port = start
    while port < start + 30:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    return start


def ensure_drop_folder():
    home = Path.home()
    desktop = home / "Desktop"
    if not desktop.exists():
        desktop = home / "OneDrive" / "Desktop"
    if not desktop.exists():
        desktop = home
    folder = desktop / "NDR UPLOAD TRACKER"
    folder.mkdir(parents=True, exist_ok=True)
    # Seed sample if empty
    if not any(folder.glob("*.xlsx")) and not any(folder.glob("*.csv")):
        sample = ROOT / "data" / "NDR_Facility_LineList.xlsx"
        if sample.exists():
            import shutil
            shutil.copy(sample, folder / "NDR_Facility_LineList.xlsx")
    return folder


def main():
    os.chdir(APP_DIR)
    ensure_drop_folder()
    port = find_free_port()
    dashboard = APP_DIR / "dashboard.py"

    # Prefer streamlit from same environment
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(dashboard),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--theme.base",
        "dark",
    ]

    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"

    proc = subprocess.Popen(cmd, cwd=str(APP_DIR), env=env)
    url = f"http://localhost:{port}"
    # Wait briefly for server, then open browser
    time.sleep(2.5)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("=" * 60)
    print("  NDR UPLOAD TRACKER MONITORING")
    print(f"  Open: {url}")
    print("  Press Ctrl+C in this window to stop the server.")
    print("=" * 60)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
