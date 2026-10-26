"""
NDR Upload Tracker Monitoring — Analysis Engine
Reference date: 26/08/2026
Rules:
  - Facilities with "Health Center" in name: compliant if Days Gap <= 5
  - All other facilities: compliant if Days Gap <= 0
  - Days Gap = max(0, reference_date - Last EMR Update)
  - Exclude any facility whose name contains "Ndukwu"
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

REFERENCE_DATE = datetime(2026, 8, 26)
EXCLUDE_KEYWORD = "ndukwu"


def get_drop_folder() -> Path:
    home = Path.home()
    desktop = home / "Desktop"
    if not desktop.exists():
        desktop = home / "OneDrive" / "Desktop"
    if not desktop.exists():
        desktop = home
    folder = desktop / "NDR UPLOAD TRACKER"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def parse_date(value) -> Optional[pd.Timestamp]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.Timestamp(value).normalize()
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none", "-"}:
        return None
    for fmt in (
        "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y",
        "%a %b %d %Y", "%b %d %Y", "%m/%d/%Y",
    ):
        try:
            return pd.Timestamp(datetime.strptime(text, fmt)).normalize()
        except ValueError:
            continue
    try:
        return pd.to_datetime(text, dayfirst=True).normalize()
    except Exception:
        return None


def is_health_center(name: str) -> bool:
    return "health center" in str(name).lower()


def allowed_gap(name: str) -> int:
    return 5 if is_health_center(name) else 0


def load_line_list(path: Optional[Path] = None) -> pd.DataFrame:
    drop = get_drop_folder()
    if path is None:
        candidates = sorted(
            list(drop.glob("*.xlsx")) + list(drop.glob("*.xls")) + list(drop.glob("*.csv")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        candidates = [p for p in candidates if not p.name.startswith("~$")]
        if not candidates:
            raise FileNotFoundError(
                f"No Excel/CSV file found in drop folder:\n{drop}\n\n"
                "Drop a line list with columns: Facility, LGA, Last NDR Update, Last EMR Update"
            )
        path = candidates[0]

    path = Path(path)
    if path.suffix.lower() == ".csv":
        raw = pd.read_csv(path)
    else:
        # Auto-detect header row for NDR export format
        preview = pd.read_excel(path, header=None, nrows=8)
        header_row = 0
        for i in range(len(preview)):
            vals = [str(v).lower() for v in preview.iloc[i].tolist()]
            if any("facility" in v for v in vals) and any("lga" in v for v in vals):
                header_row = i
                break
        raw = pd.read_excel(path, header=header_row)

    colmap = {c: str(c).strip() for c in raw.columns}
    raw = raw.rename(columns=colmap)

    def find_col(options):
        lower = {str(c).lower().strip(): c for c in raw.columns}
        for opt in options:
            if opt in lower:
                return lower[opt]
        for key, orig in lower.items():
            for opt in options:
                if opt in key:
                    return orig
        return None

    fac_c = find_col(["facility", "facility name", "facility_name", "site"])
    lga_c = find_col(["lga", "local government", "lgas"])
    state_c = find_col(["state"])
    ndr_c = find_col(["last ndr update", "ndr update", "ndr", "last ndr"])
    emr_c = find_col(["last emr update", "emr update", "emr", "last emr"])
    datim_c = find_col(["datim code", "datim", "datim_code"])

    missing = [n for n, c in [("Facility", fac_c), ("Last EMR Update", emr_c)] if c is None]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}. Found: {list(raw.columns)}")

    data = {
        "Facility": raw[fac_c].astype(str).str.strip(),
        "LGA": raw[lga_c].astype(str).str.strip() if lga_c else "",
        "Last NDR Update": raw[ndr_c].apply(parse_date) if ndr_c else None,
        "Last EMR Update": raw[emr_c].apply(parse_date),
    }
    if state_c:
        data["State"] = raw[state_c].astype(str).str.strip()
    if datim_c:
        data["DATIM Code"] = raw[datim_c].astype(str).str.strip()

    df = pd.DataFrame(data)
    df = df[df["Facility"].notna() & (df["Facility"].str.lower() != "nan") & (df["Facility"] != "")]
    # Exclude Ndukwu (Hospital or Health Center)
    df = df[~df["Facility"].str.lower().str.contains(EXCLUDE_KEYWORD, na=False)].copy()
    return df.reset_index(drop=True)


def analyze(df: pd.DataFrame, reference_date: datetime = REFERENCE_DATE) -> Tuple[pd.DataFrame, dict]:
    ref = pd.Timestamp(reference_date).normalize()
    out = df.copy()

    def days_gap(emr):
        if emr is None or pd.isna(emr):
            return None
        delta = (ref - pd.Timestamp(emr).normalize()).days
        return max(0, int(delta))

    out["Days Gap"] = out["Last EMR Update"].apply(days_gap)
    out["Is Health Center"] = out["Facility"].apply(is_health_center)
    out["Allowed Gap"] = out["Facility"].apply(allowed_gap)

    def status(row):
        gap = row["Days Gap"]
        if gap is None or pd.isna(gap):
            return "Non-compliant"
        return "Compliant" if gap <= row["Allowed Gap"] else "Non-compliant"

    out["Status"] = out.apply(status, axis=1)
    out["_sort"] = out["Status"].map({"Non-compliant": 0, "Compliant": 1})
    out = out.sort_values(["_sort", "Days Gap"], ascending=[True, False]).drop(columns=["_sort"])
    out = out.reset_index(drop=True)

    total = len(out)
    hc = int(out["Is Health Center"].sum())
    compliant = int((out["Status"] == "Compliant").sum())
    non_compliant = int((out["Status"] == "Non-compliant").sum())

    metrics = {
        "total_facilities": total,
        "health_centers": hc,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "reference_date": ref.strftime("%d/%m/%Y"),
        "source_rows": total,
    }
    return out, metrics


def noncompliant_chart_data(df: pd.DataFrame) -> pd.DataFrame:
    nc = df[df["Status"] == "Non-compliant"].copy()
    if nc.empty:
        return nc
    return nc.sort_values("Days Gap", ascending=True)[["Facility", "LGA", "Days Gap"]]
