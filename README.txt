================================================================================
  NDR UPLOAD TRACKER MONITORING
  Caritas Nigeria · Imo State
================================================================================

QUICK START
-----------
1. Double-click  SETUP.py
2. Click  Next  →  Next  →  Finish  on the installation panel
3. After install, double-click  Run_NDR_Upload_Tracker  on your Desktop
   (or Run_NDR_Upload_Tracker.bat)

The dashboard opens in your default web browser.

DATA DROP FOLDER
----------------
Desktop\NDR UPLOAD TRACKER

Place Excel/CSV line lists here with columns:
  Facility | LGA | Last NDR Update | Last EMR Update

COMPLIANCE RULES (default reference date: 26/08/2026 — changeable in sidebar)
---------------------------------------------
• Facilities with "Health Center" in the name → Compliant if Days Gap ≤ 5
• All other facilities → Compliant if Days Gap ≤ 0
• Days Gap = max(0, 26/08/2026 − Last EMR Update)
• "Ndukwu Health Center" is always excluded from analysis

DASHBOARD SHOWS
---------------
• 3D metric cards: Total facilities, Health Centers, Compliant, Non-compliant
• Horizontal bar chart (red gradient) for non-compliant facilities
• Colour-coded detail table (green = compliant, red gradient = non-compliant)

REQUIREMENTS
------------
Python 3.9+ with pip. The installer installs: streamlit, pandas, plotly, openpyxl.

================================================================================

SIDEBAR FILTERS
---------------
• Reference date — drives Days Gap and Compliant / Non-compliant counts
• Optional Last EMR Update range — include only facilities updated in that window
• State filter — Abia / Enugu / Imo (multi-select)

