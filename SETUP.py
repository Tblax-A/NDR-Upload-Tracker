"""
NDR Upload Tracker — Entry point
--------------------------------
FIRST TIME: double-click this file → installer panel (Next … Finish).
AFTER INSTALL: double-click Desktop\\Run_NDR_Upload_Tracker to open the dashboard.
"""

from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
install_marker = Path.home() / "NDR_Upload_Tracker_App" / "app" / "run_app.py"

if install_marker.exists():
    # Already installed → run app immediately
    runpy.run_path(str(install_marker), run_name="__main__")
else:
    # First run → installer
    installer = HERE / "installer" / "install.py"
    runpy.run_path(str(installer), run_name="__main__")
