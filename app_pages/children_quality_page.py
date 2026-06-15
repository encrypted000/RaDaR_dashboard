import uuid

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

NAVY  = "#0c1f4a"
SLATE = "#475569"
GRID  = "#e2e8f0"

METRICS_META = {
    "height":       {"label": "Height",          "unit": "cm",            "min": 50,  "max": 220},
    "weight":       {"label": "Weight",          "unit": "kg",            "min": 2,   "max": 200},
    "acr":          {"label": "ACR",             "unit": "mg/mmol",       "min": 0,   "max": 5000},
    "pcr":          {"label": "PCR",             "unit": "mg/mmol",       "min": 0,   "max": 5000},
    "diastolic_bp": {"label": "Diastolic BP",    "unit": "mmHg",          "min": 20,  "max": 150},
    "systolic_bp":  {"label": "Systolic BP",     "unit": "mmHg",          "min": 40,  "max": 200},
    "creatinine":   {"label": "Creatinine",      "unit": "μmol/L",        "min": 5,   "max": 2000},
    "egfr":         {"label": "eGFR (Schwartz)", "unit": "mL/min/1.73m²", "min": 2,   "max": 200},
}


# =============================================================================
# DATA
# =============================================================================

from lib.db import get_live_conn as _live_conn


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_values() -> pd.DataFrame:
    from lib.queries import SQL_CHILDREN_ALL_VALUES
    from lib.utils import schwartz_egfr

    conn, _ = _live_conn()
    df = pd.read_sql(SQL_CHILDREN_ALL_VALUES, conn)

    df["patient_id"] = df["patient_id"].astype(str)
    df["obs_year"]   = pd.to_numeric(df["obs_year"], errors="coerce")
    df["egfr"]       = schwartz_egfr(df["height"], df["creatinine"])
    return df


def detect_outliers(df: pd.DataFrame) -> pd.DataFrame:
    _cols = ["Patient ID", "Hospital", "Year", "Metric", "Value", "Expected Range", "Flag"]
    metric_cols = [m for m in METRICS_META if m in df.columns]
    if not metric_cols:
        return pd.DataFrame(columns=_cols)

    id_vars = ["patient_id", "hospital_name", "obs_year"]
    long = (
        df[id_vars + metric_cols]
        .melt(id_vars=id_vars, var_name="metric_key", value_name="value")
        .dropna(subset=["value"])
    )
    if long.empty:
        return pd.DataFrame(columns=_cols)

    meta_df = pd.DataFrame.from_dict(METRICS_META, orient="index")[["label", "unit", "min", "max"]]
    meta_df.index.name = "metric_key"
    long = long.join(meta_df, on="metric_key")

    out = long[(long["value"] < long["min"]) | (long["value"] > long["max"])].copy()
    if out.empty:
        return pd.DataFrame(columns=_cols)

    direction = out["value"].lt(out["min"]).map({True: "Too low", False: "Too high"})
    return pd.DataFrame({
        "Patient ID":     out["patient_id"].astype(str).values,
        "Hospital":       out["hospital_name"].fillna("Unknown").values,
        "Year":           out["obs_year"].astype("int64").values,
        "Metric":         out["label"].values,
        "Value":          [f"{v:.1f} {u}" for v, u in zip(out["value"], out["unit"])],
        "Expected Range": [f"{mn}–{mx} {u}" for mn, mx, u in zip(out["min"], out["max"], out["unit"])],
        "Flag":           [f"{d} (expected {mn}–{mx} {u})" for d, mn, mx, u
                           in zip(direction, out["min"], out["max"], out["unit"])],
    }).reset_index(drop=True)


def schwartz_crosscheck(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["egfr"].notna() & df["height"].notna() & df["creatinine"].notna()].copy()
    if sub.empty:
        return pd.DataFrame()

    sub["egfr_flag"] = np.select(
        [
            sub["creatinine"] < 15,
            sub["egfr"] < METRICS_META["egfr"]["min"],
            sub["egfr"] > METRICS_META["egfr"]["max"],
        ],
        [
            "Possible unit error — creatinine < 15 μmol/L (entered in mg/dL?)",
            f"Critically low eGFR < {METRICS_META['egfr']['min']} mL/min/1.73m²",
            f"Implausibly high eGFR > {METRICS_META['egfr']['max']} mL/min/1.73m²",
        ],
        default=None,
    )
    flagged = sub[sub["egfr_flag"].notna()][
        ["patient_id", "hospital_name", "obs_year", "height", "creatinine", "egfr", "egfr_flag"]
    ].reset_index(drop=True)
    return flagged if not flagged.empty else pd.DataFrame()


def site_scorecard(df: pd.DataFrame, outlier_df: pd.DataFrame) -> pd.DataFrame:
    """Outlier rate % for each site × metric combination."""
    rows = []
    for site in df["hospital_name"].dropna().unique():
        site_df = df[df["hospital_name"] == site]
        for metric, meta in METRICS_META.items():
            if metric not in df.columns:
                continue
            total = int(site_df[metric].notna().sum())
            if total == 0:
                continue
            n_flagged = (
                int(len(outlier_df[
                    (outlier_df["Hospital"] == site) &
                    (outlier_df["Metric"] == meta["label"])
                ]))
                if not outlier_df.empty else 0
            )
            rows.append({
                "site":     site,
                "metric":   meta["label"],
                "total":    total,
                "flagged":  n_flagged,
                "rate_pct": round(100.0 * n_flagged / total, 1),
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# =============================================================================
# UI COMPONENTS
# =============================================================================

def section_label(text: str):
    st.markdown(
        f'<div style="font-family:Syne,sans-serif;font-size:0.62rem;font-weight:700;'
        f'letter-spacing:0.20em;text-transform:uppercase;color:#6b7fad;margin-bottom:14px;'
        f'margin-top:6px;display:flex;align-items:center;gap:10px;">'
        f'{text}<span style="flex:1;height:1px;background:linear-gradient(to right,#cbd5e1,transparent);'
        f'display:inline-block;"></span></div>',
        unsafe_allow_html=True,
    )


def chart_wrap(title: str, subtitle: str):
    st.markdown(
        f'<div style="background:#ffffff;border-radius:20px;padding:16px 20px 8px 20px;'
        f'border:1px solid rgba(203,213,225,0.55);box-shadow:0 4px 20px rgba(30,58,138,0.06);margin-bottom:4px;">'
        f'<div style="font-family:Syne,sans-serif;font-size:0.92rem;font-weight:700;'
        f'color:#0c1f4a;margin-bottom:2px;">{title}</div>'
        f'<div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;">{subtitle}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value, icon: str, color: str, note: str = None):
    accent_map = {
        "c-blue":   "linear-gradient(90deg,#2563eb,#60a5fa)",
        "c-red":    "linear-gradient(90deg,#dc2626,#f87171)",
        "c-amber":  "linear-gradient(90deg,#d97706,#fbbf24)",
        "c-violet": "linear-gradient(90deg,#7c3aed,#a78bfa)",
        "c-green":  "linear-gradient(90deg,#16a34a,#4ade80)",
    }
    bar  = accent_map.get(color, accent_map["c-blue"])
    cid  = f"kpi-{uuid.uuid4().hex[:8]}"
    note_html = (
        f'<div style="font-size:0.70rem;color:#94a3b8;margin-top:5px;font-style:italic;">{note}</div>'
        if note else ""
    )
    st.markdown(
        f"""
        <style>
        #{cid} {{ background:#ffffff;border-radius:18px;padding:18px 18px 14px 18px;
                  border:1px solid rgba(203,213,225,0.55);
                  box-shadow:0 4px 20px rgba(30,58,138,0.06);
                  position:relative;overflow:hidden;height:100%;
                  transition:transform 0.18s ease,box-shadow 0.18s ease; }}
        #{cid}:hover {{ transform:translateY(-3px);box-shadow:0 12px 36px rgba(30,58,138,0.13); }}
        </style>
        <div id="{cid}">
            <div style="position:absolute;top:0;left:0;right:0;height:3px;
                        border-radius:18px 18px 0 0;background:{bar};"></div>
            <div style="font-size:1.35rem;margin-bottom:8px;">{icon}</div>
            <div style="font-size:0.72rem;font-weight:600;color:#64748b;letter-spacing:0.06em;
                        text-transform:uppercase;margin-bottom:5px;
                        font-family:'IBM Plex Sans',sans-serif;">{label}</div>
            <div style="font-family:'IBM Plex Sans',sans-serif;font-size:2.0rem;font-weight:700;
                        color:#0c1f4a;line-height:1;">{value}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def distribution_chart(df: pd.DataFrame, metric: str, meta: dict) -> go.Figure:
    col_data = df[["patient_id", "hospital_name", "obs_year", metric]].dropna(subset=[metric]).copy()
    if col_data.empty:
        return go.Figure()

    col_data["is_outlier"] = (
        (col_data[metric] < meta["min"]) | (col_data[metric] > meta["max"])
    )
    col_data["site"] = col_data["hospital_name"].apply(
        lambda s: s.split(" - ")[-1][:22] if " - " in s else s[:22]
    )

    normal_df  = col_data[~col_data["is_outlier"]]
    outlier_df = col_data[col_data["is_outlier"]]

    fig = go.Figure()

    if not normal_df.empty:
        fig.add_trace(go.Box(
            x=normal_df["site"],
            y=normal_df[metric].astype(float),
            name="Normal",
            marker_color="#60a5fa",
            line_color="#2563eb",
            opacity=0.75,
            boxpoints="suspectedoutliers",
            hovertemplate="<b>%{x}</b><br>%{y:.1f} " + meta["unit"] + "<extra></extra>",
        ))

    if not outlier_df.empty:
        fig.add_trace(go.Scatter(
            x=outlier_df["site"],
            y=outlier_df[metric].astype(float),
            mode="markers",
            name="Flagged",
            marker=dict(color="#ef4444", size=9, symbol="circle-open", line=dict(width=2.5)),
            customdata=outlier_df[["patient_id", "obs_year"]].values,
            hovertemplate=(
                "<b>Patient %{customdata[0]}</b> (%{customdata[1]})<br>"
                "Value: %{y:.1f} " + meta["unit"] + "<extra></extra>"
            ),
        ))

    fig.add_hline(
        y=meta["min"], line_dash="dot", line_color="rgba(239,68,68,0.45)", line_width=1.5,
        annotation_text=f"Min {meta['min']}", annotation_font_size=9,
        annotation_font_color="rgba(239,68,68,0.7)",
    )
    fig.add_hline(
        y=meta["max"], line_dash="dot", line_color="rgba(239,68,68,0.45)", line_width=1.5,
        annotation_text=f"Max {meta['max']}", annotation_font_size=9,
        annotation_font_color="rgba(239,68,68,0.7)",
    )

    fig.update_layout(
        height=300,
        margin=dict(l=8, r=8, t=8, b=70),
        plot_bgcolor="#ffffff",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans", color=SLATE, size=11),
        xaxis=dict(showgrid=False, tickangle=-35),
        yaxis=dict(showgrid=True, gridcolor=GRID, title=meta["unit"]),
        showlegend=False,
    )
    return fig


# =============================================================================
# PAGE
# =============================================================================

def render():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .block-container { padding-top:0.5rem !important; padding-left:2rem !important;
                       padding-right:2rem !important; max-width:1280px; }
    .stApp { background:#f0f4fc; }
    #MainMenu, footer, header { visibility:hidden; }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================================
    # HERO
    # =========================================================================
    st.markdown("""
    <div style="background:linear-gradient(118deg,#0c1f4a 0%,#831843 52%,#be185d 100%);
                border-radius:24px;padding:34px 40px 30px 40px;margin-bottom:28px;
                box-shadow:0 20px 60px rgba(12,31,74,0.32);">
        <div style="display:inline-flex;align-items:center;gap:7px;
                    background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.18);
                    border-radius:999px;padding:4px 14px;font-size:0.70rem;font-weight:600;
                    letter-spacing:0.14em;text-transform:uppercase;color:#fce7f3;margin-bottom:14px;">
            <span style="width:6px;height:6px;border-radius:50%;background:#f59e0b;
                         display:inline-block;"></span>
            Paediatric &middot; Data Quality
        </div>
        <div style="font-family:Syne,sans-serif;font-size:2.05rem;font-weight:800;color:#fff;
                    line-height:1.15;letter-spacing:-0.02em;margin-bottom:8px;">
            🔎 Children's Data Quality
        </div>
        <div style="font-size:0.90rem;color:rgba(252,231,243,0.82);max-width:660px;
                    line-height:1.65;font-weight:300;">
            Live validation of recorded observation values across all 13 BAPN paediatric sites —
            outlier detection, implausible values, and distribution analysis per metric and site.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================================
    # LOAD DATA
    # =========================================================================
    try:
        with st.spinner("Connecting to database and loading paediatric observations…"):
            df = fetch_all_values()
    except Exception as e:
        st.error(f"Database error: {e}")
        st.stop()

    if df.empty:
        st.warning("No data returned. Check your database connection.")
        st.stop()

    # =========================================================================
    # SIDEBAR FILTERS
    # =========================================================================
    all_sites = sorted(df["hospital_name"].dropna().unique())
    yr_min = int(df["obs_year"].min()) if df["obs_year"].notna().any() else 2008
    yr_max = int(df["obs_year"].max()) if df["obs_year"].notna().any() else 2025

    with st.sidebar:
        st.markdown(
            '<div style="height:1px;background:#d0d9ee;margin:12px 16px 14px 16px;"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-family:IBM Plex Sans,sans-serif;font-size:0.62rem;font-weight:600;'
            'letter-spacing:0.16em;text-transform:uppercase;color:#94a3b8;padding:0 18px;'
            'margin-bottom:8px;">Data Quality Filters</div>',
            unsafe_allow_html=True,
        )
        sb_sites = st.multiselect(
            "Hospital",
            options=all_sites,
            default=[],
            key="dq_site_filter",
            placeholder="All sites",
        )
        sb_years = st.slider(
            "Year range",
            min_value=yr_min, max_value=yr_max,
            value=(yr_min, yr_max),
            key="dq_year_filter",
        )
        if st.button("🔄 Refresh data", use_container_width=True, key="dq_refresh"):
            fetch_all_values.clear()
            st.rerun()

    df_view = df.copy()
    if sb_sites:
        df_view = df_view[df_view["hospital_name"].isin(sb_sites)]
    df_view = df_view[df_view["obs_year"].between(sb_years[0], sb_years[1])]

    outlier_df  = detect_outliers(df_view)
    egfr_check  = schwartz_crosscheck(df_view)
    scorecard   = site_scorecard(df_view, outlier_df)

    # =========================================================================
    # KPI CARDS
    # =========================================================================
    section_label("Overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Patient-Year Records", f"{len(df_view):,}",
                 "📋", "c-blue", "Rows with at least one value")
    with c2:
        kpi_card("Flagged Values", f"{len(outlier_df):,}",
                 "⚠️", "c-red",  "Outside expected ranges")
    with c3:
        kpi_card("Patients Affected",
                 f"{outlier_df['Patient ID'].nunique() if not outlier_df.empty else 0:,}",
                 "👤", "c-amber", "Patients with ≥1 flag")
    with c4:
        kpi_card("Sites with Flags",
                 f"{outlier_df['Hospital'].nunique() if not outlier_df.empty else 0:,}",
                 "🏥", "c-violet", "Hospitals with ≥1 flag")

    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)

    # =========================================================================
    # FLAGGED RECORDS TABLE
    # =========================================================================
    section_label("Flagged Records")

    if outlier_df.empty:
        st.success("No outliers detected — all recorded values are within expected ranges.")
    else:
        col_f1, col_f2, _ = st.columns([1, 1, 2])
        with col_f1:
            metrics_filter = st.multiselect(
                "Filter by metric",
                sorted(outlier_df["Metric"].unique()),
                default=[],
            )
        with col_f2:
            sites_filter = st.multiselect(
                "Filter by hospital",
                sorted(outlier_df["Hospital"].unique()),
                default=[],
            )

        filtered = outlier_df.copy()
        if metrics_filter:
            filtered = filtered[filtered["Metric"].isin(metrics_filter)]
        if sites_filter:
            filtered = filtered[filtered["Hospital"].isin(sites_filter)]

        chart_wrap(
            f"⚠️ Outlier Flags — {len(filtered):,} record(s)",
            "Values outside clinically expected ranges · verify and correct at the recording site",
        )
        st.dataframe(filtered.reset_index(drop=True), use_container_width=True, height=380)
        st.download_button(
            label="⬇️  Download flagged records as CSV",
            data=filtered.to_csv(index=False),
            file_name="children_data_quality_flags.csv",
            mime="text/csv",
        )

    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)

    # =========================================================================
    # PATIENT INVESTIGATION
    # =========================================================================
    flagged_pids = sorted(outlier_df["Patient ID"].unique()) if not outlier_df.empty else []
    n_fp = len(flagged_pids)

    st.markdown(f"""
    <div style="background:linear-gradient(118deg,#0c1f4a 0%,#1e3a8a 55%,#1d4ed8 100%);
                border-radius:22px;padding:28px 32px 24px 32px;margin-bottom:6px;
                box-shadow:0 16px 48px rgba(12,31,74,0.28);position:relative;overflow:hidden;">
        <div style="position:absolute;top:-50px;right:-50px;width:220px;height:220px;
                    border-radius:50%;background:rgba(255,255,255,0.04);pointer-events:none;"></div>
        <div style="position:absolute;bottom:-70px;left:40px;width:180px;height:180px;
                    border-radius:50%;background:rgba(96,165,250,0.07);pointer-events:none;"></div>
        <div style="display:flex;align-items:flex-start;gap:14px;margin-bottom:12px;">
            <div style="width:44px;height:44px;min-width:44px;border-radius:12px;
                        background:rgba(255,255,255,0.13);border:1px solid rgba(255,255,255,0.18);
                        display:flex;align-items:center;justify-content:center;font-size:1.25rem;">
                🔍
            </div>
            <div style="flex:1;">
                <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1.15rem;
                            font-weight:700;color:#fff;letter-spacing:-0.01em;line-height:1.2;">
                    Patient Investigation
                </div>
                <div style="font-size:0.78rem;color:rgba(186,219,255,0.65);margin-top:3px;">
                    Drill down into any flagged patient — view their full observation history,
                    all outlier flags, and metric trends year by year.
                </div>
            </div>
            <div style="background:rgba(239,68,68,0.18);border:1px solid rgba(239,68,68,0.40);
                        border-radius:999px;padding:5px 16px;white-space:nowrap;
                        font-family:'IBM Plex Sans',sans-serif;font-size:0.78rem;font-weight:600;
                        color:#fca5a5;">
                ⚠️ {n_fp} patient{'s' if n_fp != 1 else ''} flagged
            </div>
        </div>
        <div style="height:1px;background:rgba(255,255,255,0.10);margin-bottom:18px;"></div>
        <div style="font-size:0.75rem;color:rgba(186,219,255,0.55);letter-spacing:0.05em;
                    text-transform:uppercase;font-weight:600;margin-bottom:6px;">
            Select patient ID to investigate
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not flagged_pids:
        st.info("No flagged patients in the current filter selection.")
    else:
        inv_pid = st.selectbox(
            "Patient ID",
            options=["— select —"] + list(flagged_pids),
            key="dq_inv_patient",
            label_visibility="collapsed",
        )

        if not inv_pid or inv_pid == "— select —":
            st.markdown("""
            <div style="text-align:center;padding:32px 20px;color:#94a3b8;
                        font-family:'IBM Plex Sans',sans-serif;">
                <div style="font-size:2rem;margin-bottom:8px;">🔍</div>
                <div style="font-size:0.88rem;font-weight:500;color:#64748b;">
                    Select a patient ID above to view their full profile
                </div>
                <div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;">
                    Flags table, year-by-year observations, and metric trend chart will appear here
                </div>
            </div>
            """, unsafe_allow_html=True)

        if inv_pid and inv_pid != "— select —":
            pat_rows  = df_view[df_view["patient_id"].astype(str) == str(inv_pid)].copy()
            pat_flags = outlier_df[outlier_df["Patient ID"] == str(inv_pid)]

            if not pat_rows.empty:
                hospital  = pat_rows["hospital_name"].iloc[0]
                n_years   = pat_rows["obs_year"].nunique()
                n_flags   = len(pat_flags)
                yr_range  = (
                    f"{int(pat_rows['obs_year'].min())} – {int(pat_rows['obs_year'].max())}"
                    if n_years > 0 else "—"
                )

                st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
                _hosp  = hospital.split(' - ')[-1] if ' - ' in hospital else hospital
                _nm    = pat_flags['Metric'].nunique() if not pat_flags.empty else 0
                _nm_s  = 's' if _nm != 1 else ''
                _yr_s  = 's' if n_years != 1 else ''
                _fl_s  = 's' if n_flags != 1 else ''
                _card  = (
                    f'<div style="background:#fff;border-radius:20px;border:1px solid rgba(203,213,225,0.6);'
                    f'box-shadow:0 8px 32px rgba(12,31,74,0.10);overflow:hidden;margin-bottom:18px;">'
                    f'<div style="background:linear-gradient(90deg,#0c1f4a,#2563eb);padding:18px 24px 16px 24px;">'
                    f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
                    f'<div style="font-family:IBM Plex Sans,sans-serif;font-size:0.68rem;font-weight:700;'
                    f'letter-spacing:0.14em;text-transform:uppercase;color:rgba(186,219,255,0.65);">Patient ID</div>'
                    f'<div style="font-family:IBM Plex Sans,sans-serif;font-size:1.30rem;font-weight:700;'
                    f'color:#fff;letter-spacing:-0.01em;">{inv_pid}</div>'
                    f'<div style="margin-left:auto;display:flex;gap:8px;flex-wrap:wrap;">'
                    f'<span style="background:rgba(255,255,255,0.15);border-radius:999px;padding:3px 12px;'
                    f'font-size:0.73rem;color:#e0eaff;font-family:IBM Plex Sans,sans-serif;">📅 {yr_range}</span>'
                    f'<span style="background:rgba(239,68,68,0.25);border:1px solid rgba(239,68,68,0.45);'
                    f'border-radius:999px;padding:3px 12px;font-size:0.73rem;color:#fca5a5;'
                    f'font-family:IBM Plex Sans,sans-serif;">⚠️ {n_flags} flag{_fl_s}</span>'
                    f'</div></div></div>'
                    f'<div style="display:flex;gap:0;border-bottom:1px solid #e2e8f0;">'
                    f'<div style="flex:1;padding:14px 20px;border-right:1px solid #e2e8f0;">'
                    f'<div style="font-size:0.68rem;font-weight:600;color:#94a3b8;text-transform:uppercase;'
                    f'letter-spacing:0.08em;margin-bottom:3px;">Hospital</div>'
                    f'<div style="font-size:0.88rem;font-weight:500;color:#1e293b;">🏥 {_hosp}</div>'
                    f'</div>'
                    f'<div style="flex:1;padding:14px 20px;border-right:1px solid #e2e8f0;">'
                    f'<div style="font-size:0.68rem;font-weight:600;color:#94a3b8;text-transform:uppercase;'
                    f'letter-spacing:0.08em;margin-bottom:3px;">Years on Record</div>'
                    f'<div style="font-size:0.88rem;font-weight:500;color:#1e293b;">{n_years} year{_yr_s}</div>'
                    f'</div>'
                    f'<div style="flex:1;padding:14px 20px;">'
                    f'<div style="font-size:0.68rem;font-weight:600;color:#94a3b8;text-transform:uppercase;'
                    f'letter-spacing:0.08em;margin-bottom:3px;">Flagged Metrics</div>'
                    f'<div style="font-size:0.88rem;font-weight:500;color:#dc2626;">{_nm} unique metric{_nm_s}</div>'
                    f'</div></div></div>'
                )
                st.markdown(_card, unsafe_allow_html=True)

                if not pat_flags.empty:
                    chart_wrap(
                        f"⚠️ All Flags — Patient {inv_pid}",
                        "Every outlier detected for this patient across all metrics and years",
                    )
                    st.dataframe(pat_flags.reset_index(drop=True), use_container_width=True)

                obs_cols = [c for c in ["obs_year", "height", "weight", "acr", "pcr",
                                         "diastolic_bp", "systolic_bp", "creatinine", "egfr"]
                            if c in pat_rows.columns]
                obs_table = (
                    pat_rows[obs_cols]
                    .sort_values("obs_year")
                    .reset_index(drop=True)
                    .rename(columns={
                        "obs_year":     "Year",
                        "height":       "Height (cm)",
                        "weight":       "Weight (kg)",
                        "acr":          "ACR",
                        "pcr":          "PCR",
                        "diastolic_bp": "DBP (mmHg)",
                        "systolic_bp":  "SBP (mmHg)",
                        "creatinine":   "Creatinine (μmol/L)",
                        "egfr":         "Schwartz eGFR",
                    })
                )
                chart_wrap(
                    f"📅 Year-by-Year Observations — Patient {inv_pid}",
                    "All recorded values · eGFR = 36.5 × height(cm) ÷ creatinine(μmol/L)",
                )
                st.dataframe(obs_table, use_container_width=True)

                metric_opts = [
                    m for m in METRICS_META
                    if m in pat_rows.columns and pat_rows[m].notna().any()
                ]
                if metric_opts:
                    trend_metric = st.selectbox(
                        "Show trend for metric",
                        options=metric_opts,
                        format_func=lambda m: METRICS_META[m]["label"],
                        key=f"dq_trend_{inv_pid}",
                    )
                    tmeta = METRICS_META[trend_metric]
                    td = (
                        pat_rows[["obs_year", trend_metric]]
                        .dropna()
                        .sort_values("obs_year")
                    )
                    if not td.empty:
                        colors = [
                            "#ef4444"
                            if (float(v) < tmeta["min"] or float(v) > tmeta["max"])
                            else "#2563eb"
                            for v in td[trend_metric]
                        ]
                        fig_t = go.Figure()
                        fig_t.add_trace(go.Scatter(
                            x=td["obs_year"], y=td[trend_metric].astype(float),
                            mode="lines+markers",
                            line=dict(color="#93c5fd", width=2),
                            marker=dict(size=8, color=colors, line=dict(width=1.5,
                                        color=["#b91c1c" if c == "#ef4444" else "#1d4ed8"
                                               for c in colors])),
                            hovertemplate="%{x}<br>%{y:.1f} " + tmeta["unit"] + "<extra></extra>",
                        ))
                        fig_t.add_hline(y=tmeta["min"], line_dash="dot",
                                        line_color="rgba(239,68,68,0.5)", line_width=1.5,
                                        annotation_text=f"Min {tmeta['min']}",
                                        annotation_font_size=9)
                        fig_t.add_hline(y=tmeta["max"], line_dash="dot",
                                        line_color="rgba(239,68,68,0.5)", line_width=1.5,
                                        annotation_text=f"Max {tmeta['max']}",
                                        annotation_font_size=9)
                        fig_t.update_layout(
                            height=260,
                            margin=dict(l=8, r=8, t=8, b=40),
                            plot_bgcolor="#ffffff",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(family="IBM Plex Sans", color=SLATE, size=11),
                            xaxis=dict(title="Year", showgrid=True, gridcolor=GRID,
                                       dtick=1, tickformat="d"),
                            yaxis=dict(title=tmeta["unit"], showgrid=True, gridcolor=GRID),
                        )
                        chart_wrap(
                            f"📈 {tmeta['label']} Trend — Patient {inv_pid}",
                            f"Red = outside expected range  ·  {tmeta['min']}–{tmeta['max']} {tmeta['unit']}",
                        )
                        st.plotly_chart(fig_t, use_container_width=True)

    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)

    # =========================================================================
    # DISTRIBUTION CHARTS
    # =========================================================================
    section_label("Value Distributions by Site")

    st.markdown(
        '<div style="background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:0 10px 10px 0;'
        'padding:10px 14px;font-size:0.78rem;color:#0369a1;line-height:1.55;margin-bottom:16px;">'
        '🔵 Blue box = normal distribution per site &nbsp;|&nbsp; '
        '🔴 Red circles = flagged outliers &nbsp;|&nbsp; '
        'Dashed lines = expected min / max thresholds</div>',
        unsafe_allow_html=True,
    )

    metric_list = list(METRICS_META.items())
    for i in range(0, len(metric_list), 2):
        col1, col2 = st.columns(2, gap="large")
        for col, (metric, meta) in zip([col1, col2], metric_list[i:i + 2]):
            with col:
                n_flagged = int((
                    (df_view[metric].dropna() < meta["min"]) |
                    (df_view[metric].dropna() > meta["max"])
                ).sum()) if metric in df_view.columns else 0
                flag_txt = f" · {n_flagged} flagged" if n_flagged else ""
                chart_wrap(
                    f"📊 {meta['label']} ({meta['unit']}){flag_txt}",
                    f"Expected range: {meta['min']}–{meta['max']} {meta['unit']}",
                )
                st.plotly_chart(
                    distribution_chart(df_view, metric, meta),
                    use_container_width=True,
                )

    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)

    # =========================================================================
    # SCHWARTZ eGFR CROSS-CHECK
    # =========================================================================
    section_label("Schwartz eGFR Cross-Check")

    st.markdown(
        '<div style="background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:0 10px 10px 0;'
        'padding:10px 14px;font-size:0.78rem;color:#0369a1;line-height:1.55;margin-bottom:16px;">'
        'For every patient-year where both <strong>height</strong> and <strong>creatinine</strong> are recorded, '
        'eGFR is computed using the Schwartz formula (36.5 × height(cm) ÷ creatinine(μmol/L)). '
        'Implausible results often indicate a unit entry error — e.g. creatinine recorded in mg/dL instead of μmol/L '
        '(values below 15 μmol/L are flagged as likely wrong-unit entries).</div>',
        unsafe_allow_html=True,
    )

    n_pairs = int(df_view["egfr"].notna().sum())
    col_e1, col_e2 = st.columns(2, gap="large")
    with col_e1:
        kpi_card("Height + Creatinine Pairs", f"{n_pairs:,}", "🧮", "c-blue",
                 "Patient-years with both values recorded")
    with col_e2:
        kpi_card("Suspicious eGFR Results", f"{len(egfr_check):,}", "⚠️", "c-red",
                 "Possible unit errors or implausible eGFR values")

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    if not egfr_check.empty:
        chart_wrap(
            "🧮 Suspicious Schwartz eGFR Records",
            "Records where computed eGFR is implausible — verify creatinine unit entry",
        )
        display_egfr = egfr_check.rename(columns={
            "patient_id":    "Patient ID",
            "hospital_name": "Hospital",
            "obs_year":      "Year",
            "height":        "Height (cm)",
            "creatinine":    "Creatinine (μmol/L)",
            "egfr":          "Schwartz eGFR",
            "egfr_flag":     "Flag",
        })
        st.dataframe(display_egfr.reset_index(drop=True), use_container_width=True, height=280)
        st.download_button(
            label="⬇️  Download eGFR cross-check flags as CSV",
            data=display_egfr.to_csv(index=False),
            file_name="children_egfr_crosscheck.csv",
            mime="text/csv",
            key="dl_egfr_check",
        )
    else:
        st.success("No implausible eGFR values detected — all Schwartz-computed results appear plausible.")

    # Scatter: creatinine vs computed eGFR
    scatter_df = df_view[df_view["egfr"].notna() & df_view["creatinine"].notna()].copy()
    if not scatter_df.empty:
        suspicious_ids = set(egfr_check["patient_id"].astype(str).values) if not egfr_check.empty else set()
        scatter_df["is_suspicious"] = scatter_df["patient_id"].astype(str).isin(suspicious_ids)
        normal_s  = scatter_df[~scatter_df["is_suspicious"]]
        suspect_s = scatter_df[scatter_df["is_suspicious"]]

        fig_scatter = go.Figure()
        if not normal_s.empty:
            fig_scatter.add_trace(go.Scatter(
                x=normal_s["creatinine"], y=normal_s["egfr"],
                mode="markers", name="Normal",
                marker=dict(color="#60a5fa", size=5, opacity=0.55),
                hovertemplate="Creatinine: %{x:.0f} μmol/L<br>eGFR: %{y:.1f}<extra></extra>",
            ))
        if not suspect_s.empty:
            fig_scatter.add_trace(go.Scatter(
                x=suspect_s["creatinine"], y=suspect_s["egfr"],
                mode="markers", name="Suspicious",
                marker=dict(color="#ef4444", size=9, symbol="circle-open",
                            line=dict(width=2.5)),
                hovertemplate="Creatinine: %{x:.0f} μmol/L<br>eGFR: %{y:.1f}<extra></extra>",
            ))
        fig_scatter.add_hline(
            y=METRICS_META["egfr"]["min"], line_dash="dot",
            line_color="rgba(239,68,68,0.45)", line_width=1.5,
            annotation_text=f"eGFR min {METRICS_META['egfr']['min']}",
            annotation_font_size=9, annotation_font_color="rgba(239,68,68,0.7)",
        )
        fig_scatter.add_hline(
            y=METRICS_META["egfr"]["max"], line_dash="dot",
            line_color="rgba(239,68,68,0.45)", line_width=1.5,
            annotation_text=f"eGFR max {METRICS_META['egfr']['max']}",
            annotation_font_size=9, annotation_font_color="rgba(239,68,68,0.7)",
        )
        fig_scatter.add_vline(
            x=15, line_dash="dash",
            line_color="rgba(245,158,11,0.65)", line_width=1.5,
            annotation_text="≤15 μmol/L → possible mg/dL entry",
            annotation_font_size=9,
        )
        fig_scatter.update_layout(
            height=340,
            margin=dict(l=8, r=8, t=8, b=50),
            plot_bgcolor="#ffffff",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Sans", color=SLATE, size=11),
            xaxis=dict(title="Creatinine (μmol/L)", showgrid=True, gridcolor=GRID),
            yaxis=dict(title="Schwartz eGFR (mL/min/1.73m²)",
                       showgrid=True, gridcolor=GRID),
            legend=dict(orientation="h", x=0, y=1.1),
        )
        chart_wrap(
            "📈 Creatinine vs Schwartz eGFR",
            "All pairs · red open circles = suspicious · amber dashed line = creatinine 15 μmol/L threshold",
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)

    # =========================================================================
    # SITE QUALITY SCORECARD
    # =========================================================================
    section_label("Site Quality Scorecard")

    if scorecard.empty:
        st.info("Insufficient data to compute site scorecard.")
    else:
        # ── Heatmap: site × metric outlier rate % ─────────────────────────────
        def short_name(s):
            return (s.split(" - ")[-1][:30] if " - " in s else s[:30])

        pivot = scorecard.pivot_table(
            index="site", columns="metric", values="rate_pct", fill_value=0
        )
        pivot.index = [short_name(s) for s in pivot.index]
        site_flag_totals = scorecard.groupby("site")["flagged"].sum()
        site_order = [short_name(s) for s in
                      site_flag_totals.sort_values(ascending=False).index
                      if short_name(s) in pivot.index]
        pivot = pivot.reindex(site_order)

        z    = pivot.values.tolist()
        x    = list(pivot.columns)
        y    = list(pivot.index)
        text = [[f"{v:.1f}%" for v in row] for row in pivot.values]

        fig_heat = go.Figure(go.Heatmap(
            z=z, x=x, y=y,
            text=text, texttemplate="%{text}", textfont=dict(size=10),
            colorscale=[
                [0.00, "#f0fdf4"],
                [0.25, "#fef9c3"],
                [0.60, "#fed7aa"],
                [1.00, "#fecaca"],
            ],
            colorbar=dict(title="Outlier %", thickness=12, len=0.75,
                          ticksuffix="%"),
            hovertemplate="<b>%{y}</b><br>%{x}<br>Outlier rate: %{z:.1f}%<extra></extra>",
            zmin=0,
        ))
        fig_heat.update_layout(
            height=max(320, 38 * len(y) + 100),
            margin=dict(l=8, r=8, t=8, b=80),
            plot_bgcolor="#ffffff",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Sans", color=SLATE, size=11),
            xaxis=dict(tickangle=-30, side="bottom"),
            yaxis=dict(autorange="reversed"),
        )
        chart_wrap(
            "🏥 Site × Metric Outlier Rate (%)",
            "% of recorded values flagged outside expected range — sorted by total flags (worst → best)",
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

        # ── Bar: total flags per site ──────────────────────────────────────────
        site_totals = scorecard.groupby("site")["flagged"].sum().sort_values(ascending=False)
        short_labels = [short_name(s) for s in site_totals.index]

        fig_bar = go.Figure(go.Bar(
            x=short_labels,
            y=site_totals.values,
            marker_color="#2563eb",
            marker_line_color="#1e3a8a",
            marker_line_width=0.8,
            hovertemplate="%{x}<br>Total flags: %{y}<extra></extra>",
        ))
        fig_bar.update_layout(
            height=280,
            margin=dict(l=8, r=8, t=8, b=80),
            plot_bgcolor="#ffffff",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Sans", color=SLATE, size=11),
            xaxis=dict(tickangle=-35, showgrid=False),
            yaxis=dict(title="Total Flagged Values", showgrid=True, gridcolor=GRID),
        )
        chart_wrap(
            "📊 Total Flagged Values per Site",
            "Absolute count of all metric flags across all years",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Summary table ─────────────────────────────────────────────────────
        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
        summary_tbl = (
            scorecard.groupby("site")
            .agg(total_values=("total", "sum"), total_flags=("flagged", "sum"))
            .assign(overall_rate=lambda d: (100 * d["total_flags"] / d["total_values"]).round(1))
            .sort_values("total_flags", ascending=False)
            .reset_index()
        )
        summary_tbl["site"] = summary_tbl["site"].apply(short_name)
        summary_tbl.columns = ["Site", "Total Values", "Total Flags", "Overall Outlier Rate (%)"]
        chart_wrap(
            "📋 Site Summary",
            "Overall data quality ranking across all metrics",
        )
        st.dataframe(summary_tbl, use_container_width=True, height=320)
        st.download_button(
            label="⬇️  Download site scorecard as CSV",
            data=summary_tbl.to_csv(index=False),
            file_name="children_site_scorecard.csv",
            mime="text/csv",
            key="dl_scorecard",
        )
