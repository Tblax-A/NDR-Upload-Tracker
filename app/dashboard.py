"""
NDR UPLOAD TRACKER MONITORING — Interactive Dashboard
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tracker_engine import (
    REFERENCE_DATE,
    analyze,
    get_drop_folder,
    load_line_list,
    noncompliant_chart_data,
)

st.set_page_config(
    page_title="NDR UPLOAD TRACKER MONITORING",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ──────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: linear-gradient(160deg, #0f1419 0%, #1a2332 50%, #0f1419 100%); }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }

h1, h2, h3 { color: #f5f7fa !important; letter-spacing: -0.02em; }

.hero {
  background: linear-gradient(135deg, #c41e3a 0%, #8b152a 60%, #5c0e1c 100%);
  border-radius: 18px;
  padding: 1.4rem 1.8rem;
  margin-bottom: 1.4rem;
  box-shadow: 0 12px 40px rgba(196,30,58,0.35);
  border: 1px solid rgba(255,255,255,0.08);
}
.hero h1 {
  margin: 0; font-size: 1.75rem; font-weight: 800; color: #fff !important;
}
.hero p { margin: 0.35rem 0 0; color: rgba(255,255,255,0.85); font-size: 0.95rem; }

/* 3D metric cards */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.metric-card {
  background: linear-gradient(145deg, #1e2a3a 0%, #15202b 100%);
  border-radius: 16px;
  padding: 1.25rem 1.35rem;
  position: relative;
  overflow: hidden;
  box-shadow:
    0 10px 30px rgba(0,0,0,0.45),
    0 1px 0 rgba(255,255,255,0.06) inset,
    0 -2px 0 rgba(0,0,0,0.3) inset;
  border: 1px solid rgba(255,255,255,0.06);
  transform: perspective(800px) rotateX(2deg);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.metric-card:hover {
  transform: perspective(800px) rotateX(0deg) translateY(-4px);
  box-shadow: 0 18px 40px rgba(0,0,0,0.55), 0 1px 0 rgba(255,255,255,0.08) inset;
}
.metric-card .accent {
  position: absolute; top: 0; left: 0; right: 0; height: 4px;
  border-radius: 16px 16px 0 0;
}
.metric-card .label {
  font-size: 0.78rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.06em; color: #94a3b8; margin-bottom: 0.45rem;
}
.metric-card .value {
  font-size: 2.4rem; font-weight: 800; line-height: 1; color: #f8fafc;
}
.metric-card .sub {
  margin-top: 0.45rem; font-size: 0.8rem; color: #64748b;
}

.section-title {
  font-size: 1.05rem; font-weight: 700; color: #e2e8f0;
  margin: 0.5rem 0 0.85rem; padding-left: 0.6rem;
  border-left: 3px solid #c41e3a;
}

div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

.stAlert { border-radius: 12px; }

footer { visibility: hidden; }
</style>
""",
    unsafe_allow_html=True,
)


def status_color(gap, status):
    if status == "Compliant":
        return "#16a34a"
    # Red gradient by severity
    if gap is None or (isinstance(gap, float) and pd.isna(gap)):
        return "#7f1d1d"
    g = int(gap)
    if g <= 3:
        return "#f87171"
    if g <= 7:
        return "#ef4444"
    if g <= 14:
        return "#dc2626"
    return "#991b1b"


def render_dashboard():
    drop = get_drop_folder()

    st.markdown(
        f"""
        <div class="hero">
          <h1>📡 NDR UPLOAD TRACKER MONITORING</h1>
          <p>Imo State · EMR ↔ NDR compliance · Reference date 26/08/2026 ·
          Drop folder: <b>{drop}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### 📁 Data source")
        st.caption(f"Watching:\n`{drop}`")
        uploaded = st.file_uploader("Or upload Excel/CSV", type=["xlsx", "xls", "csv"])
        st.markdown("---")
        st.markdown("### Rules")
        st.markdown(
            """
- **Health Center** in name → allowed gap **≤ 5 days**
- **Other facilities** → allowed gap **≤ 0 days**
- **Days Gap** = max(0, 26/08/2026 − Last EMR Update)
- **Excluded:** Ndukwu Health Center
            """
        )
        if st.button("🔄 Refresh analysis", use_container_width=True):
            st.rerun()

    try:
        if uploaded is not None:
            tmp = drop / f"_upload_{uploaded.name}"
            tmp.write_bytes(uploaded.getvalue())
            raw = load_line_list(tmp)
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            raw = load_line_list()
    except Exception as e:
        st.error(f"**Could not load line list**\n\n{e}")
        st.info(
            f"Place an Excel file with columns **Facility, LGA, Last NDR Update, Last EMR Update** "
            f"into:\n\n`{drop}`"
        )
        return

    # ── Sidebar filters: State + Date range (drives compliance) ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📅 Compliance date controls")
        st.caption(
            "Days Gap = max(0, **Reference date − Last EMR Update**).\n\n"
            "• Health Center → compliant if gap ≤ **5**\n"
            "• Other facilities → compliant if gap ≤ **0**\n\n"
            "Changing the reference date recalculates **Compliant** and **Non-compliant**."
        )

        default_ref = date(2026, 8, 26)
        ref_date = st.date_input(
            "Reference date (for Days Gap)",
            value=default_ref,
            min_value=date(2020, 1, 1),
            max_value=date(2030, 12, 31),
            help="Classification cut-off: how many days since Last EMR Update.",
        )

        # Optional window on Last EMR Update
        emr_series = raw["Last EMR Update"].dropna()
        if len(emr_series) > 0:
            min_emr = emr_series.min().date()
            max_emr = emr_series.max().date()
        else:
            min_emr, max_emr = date(2020, 1, 1), date(2030, 12, 31)

        use_emr_range = st.checkbox(
            "Filter by Last EMR Update range",
            value=False,
            help="Only include facilities whose Last EMR Update falls in this range.",
        )
        if use_emr_range:
            emr_range = st.date_input(
                "Last EMR Update range",
                value=(min_emr, max_emr),
                min_value=date(2020, 1, 1),
                max_value=date(2030, 12, 31),
            )
            if isinstance(emr_range, (list, tuple)) and len(emr_range) == 2:
                start_emr, end_emr = emr_range
                raw = raw[
                    raw["Last EMR Update"].notna()
                    & (raw["Last EMR Update"] >= pd.Timestamp(start_emr))
                    & (raw["Last EMR Update"] <= pd.Timestamp(end_emr))
                ].copy()
                st.caption(f"EMR window: {start_emr.strftime('%d/%m/%Y')} → {end_emr.strftime('%d/%m/%Y')}")

        st.markdown("---")
        st.markdown("### 🗺️ State filter")
        has_state = "State" in raw.columns and raw["State"].notna().any()
        if has_state:
            states = sorted(raw["State"].dropna().astype(str).unique().tolist())
            selected_states = st.multiselect(
                "Select state(s)",
                options=states,
                default=states,
                help="Filter facilities by state.",
            )
            if not selected_states:
                st.warning("Select at least one state.")
                return
            raw = raw[raw["State"].astype(str).isin(selected_states)].copy()
            st.caption(f"**{len(raw)}** facilities · {', '.join(selected_states)}")
        else:
            st.caption("No State column in file — showing all facilities.")
            selected_states = []

    if raw.empty:
        st.warning("No facilities match the current filters.")
        return

    try:
        ref_dt = datetime(ref_date.year, ref_date.month, ref_date.day)
        result, metrics = analyze(raw, ref_dt)
    except Exception as e:
        st.error(f"**Analysis failed**\n\n{e}")
        return

    # ── 3D metric cards ─────────────────────────────────────
    st.markdown(
        f"""
        <div class="metric-grid">
          <div class="metric-card">
            <div class="accent" style="background:linear-gradient(90deg,#3b82f6,#60a5fa);"></div>
            <div class="label">Total Facilities</div>
            <div class="value">{metrics['total_facilities']}</div>
            <div class="sub">Excluding Ndukwu Health Center</div>
          </div>
          <div class="metric-card">
            <div class="accent" style="background:linear-gradient(90deg,#8b5cf6,#a78bfa);"></div>
            <div class="label">Health Center facilities</div>
            <div class="value">{metrics['health_centers']}</div>
            <div class="sub">Name contains “Health Center”</div>
          </div>
          <div class="metric-card">
            <div class="accent" style="background:linear-gradient(90deg,#16a34a,#4ade80);"></div>
            <div class="label">Compliant</div>
            <div class="value">{metrics['compliant']}</div>
            <div class="sub">Within allowed gap · ref {metrics['reference_date']}</div>
          </div>
          <div class="metric-card">
            <div class="accent" style="background:linear-gradient(90deg,#c41e3a,#f87171);"></div>
            <div class="label">Non-compliant</div>
            <div class="value">{metrics['non_compliant']}</div>
            <div class="sub">Exceeded allowed gap · ref {metrics['reference_date']}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Horizontal bar chart — non-compliant ────────────────
    st.markdown('<div class="section-title">Non-compliant facilities — Days Gap</div>', unsafe_allow_html=True)
    nc = noncompliant_chart_data(result)
    if nc.empty:
        st.success("All facilities are compliant.")
    else:
        # Red gradient by days gap
        fig = go.Figure(
            go.Bar(
                x=nc["Days Gap"],
                y=nc["Facility"],
                orientation="h",
                text=nc["Days Gap"],
                textposition="outside",
                marker=dict(
                    color=nc["Days Gap"],
                    colorscale=[
                        [0.0, "#fecaca"],
                        [0.25, "#f87171"],
                        [0.5, "#ef4444"],
                        [0.75, "#dc2626"],
                        [1.0, "#7f1d1d"],
                    ],
                    showscale=True,
                    colorbar=dict(title="Days", thickness=12),
                    line=dict(width=0),
                ),
                hovertemplate="<b>%{y}</b><br>Days Gap: %{x}<extra></extra>",
            )
        )
        fig.update_layout(
            height=max(320, 28 * len(nc) + 80),
            margin=dict(l=20, r=40, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", family="Inter"),
            xaxis=dict(title="Days Gap", gridcolor="rgba(255,255,255,0.06)", zeroline=False),
            yaxis=dict(title="", automargin=True),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Detail table ────────────────────────────────────────
    st.markdown('<div class="section-title">Facility detail table</div>', unsafe_allow_html=True)

    cols = ["Facility", "LGA", "Days Gap", "Status", "Last EMR Update", "Last NDR Update", "Allowed Gap"]
    if "State" in result.columns:
        cols = ["State"] + cols
    table = result[cols].copy()
    table["Last EMR Update"] = table["Last EMR Update"].apply(
        lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "—"
    )
    table["Last NDR Update"] = table["Last NDR Update"].apply(
        lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "—"
    )

    def style_row(row):
        styles = [""] * len(row)
        # Status column index
        status_idx = list(row.index).index("Status")
        gap_idx = list(row.index).index("Days Gap")
        gap = row["Days Gap"]
        status = row["Status"]
        color = status_color(gap, status)
        if status == "Compliant":
            styles[status_idx] = f"background-color: #14532d; color: #bbf7d0; font-weight: 600;"
        else:
            styles[status_idx] = f"background-color: {color}; color: #fff; font-weight: 700;"
            styles[gap_idx] = f"color: {color}; font-weight: 700;"
        return styles

    styled = table.style.apply(style_row, axis=1)
    st.dataframe(styled, use_container_width=True, height=min(560, 40 + 35 * len(table)))

    st.caption(
        f"Reference date: **{metrics['reference_date']}** · "
        f"Health Center allowed ≤5 days · Others ≤0 days · "
        f"Ndukwu Health Center excluded"
    )

    # Download
    csv = table.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download analysis CSV",
        data=csv,
        file_name="NDR_Upload_Tracker_Analysis.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    render_dashboard()
