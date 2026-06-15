import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import uuid

from lib.db import read_sql_df, read_sql_params, get_live_conn as _live_conn
from lib.queries import SQL_KF_COHORTS, SQL_KIDNEY_FAILURE_EVENTS, EGFR_OBS_ID

# =============================================================================
# SETTINGS
# =============================================================================

NAVY   = "#0c1f4a"
VIOLET = "#6d28d9"
TEAL   = "#0d9488"
ROSE   = "#e11d48"
AMBER  = "#d97706"
BLUE   = "#2563eb"
SLATE  = "#475569"
GRID   = "#e2e8f0"

RULE_COLORS = {
    "Transplant":  "#2563eb",
    "Dialysis":    "#0d9488",
    "eGFR <15 x2": "#e11d48",
}

ACCENT = {
    "c-blue":   "linear-gradient(90deg,#2563eb,#60a5fa)",
    "c-teal":   "linear-gradient(90deg,#0d9488,#2dd4bf)",
    "c-rose":   "linear-gradient(90deg,#e11d48,#fb7185)",
    "c-amber":  "linear-gradient(90deg,#d97706,#fbbf24)",
    "c-violet": "linear-gradient(90deg,#6d28d9,#a78bfa)",
    "c-slate":  "linear-gradient(90deg,#475569,#94a3b8)",
}

# =============================================================================
# DATA HELPERS
# =============================================================================


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_cohorts() -> pd.DataFrame:
    try:
        conn, _ = _live_conn()
        return read_sql_df(conn, SQL_KF_COHORTS)
    except Exception as e:
        return pd.DataFrame({"_error": [str(e)]})


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_events(cohort_id: int) -> pd.DataFrame:
    try:
        conn, _ = _live_conn()
        return read_sql_params(conn, SQL_KIDNEY_FAILURE_EVENTS,
                               {"cohort_id": cohort_id, "egfr_obs_id": EGFR_OBS_ID})
    except Exception as e:
        return pd.DataFrame({"_error": [str(e)]})


# =============================================================================
# UI HELPERS
# =============================================================================

def kpi_card(label: str, value, color_cls: str, icon: str, note: str = ""):
    bar     = ACCENT.get(color_cls, ACCENT["c-blue"])
    card_id = f"kpi-{uuid.uuid4().hex[:8]}"
    note_html = f'<div style="font-size:0.70rem;color:#94a3b8;margin-top:5px;font-style:italic;">{note}</div>' if note else ""
    st.markdown(f"""
    <style>
    #{card_id} {{
        background:#ffffff;border-radius:18px;padding:18px 18px 14px 18px;
        border:1px solid rgba(203,213,225,0.55);
        box-shadow:0 4px 20px rgba(30,58,138,0.06);
        position:relative;overflow:hidden;height:100%;
        transition:transform 0.18s ease,box-shadow 0.18s ease;cursor:default;
    }}
    #{card_id}:hover {{ transform:translateY(-3px);box-shadow:0 12px 36px rgba(30,58,138,0.13); }}
    </style>
    <div id="{card_id}">
        <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:18px 18px 0 0;background:{bar};"></div>
        <div style="font-size:1.35rem;margin-bottom:8px;">{icon}</div>
        <div style="font-size:0.72rem;font-weight:600;color:#64748b;letter-spacing:0.06em;
                    text-transform:uppercase;margin-bottom:5px;font-family:'IBM Plex Sans',sans-serif;">{label}</div>
        <div style="font-family:'IBM Plex Sans',sans-serif;font-size:2.0rem;font-weight:700;
                    color:#0c1f4a;line-height:1;letter-spacing:-0.01em;">{value}</div>
        {note_html}
    </div>
    """, unsafe_allow_html=True)


def chart_card(title: str, subtitle: str):
    st.markdown(
        f'<div style="background:#ffffff;border-radius:20px;padding:16px 20px 8px 20px;'
        f'border:1px solid rgba(203,213,225,0.55);box-shadow:0 4px 20px rgba(30,58,138,0.06);'
        f'margin-bottom:4px;">'
        f'<div style="font-family:Syne,sans-serif;font-size:0.92rem;font-weight:700;color:#0c1f4a;margin-bottom:2px;">{title}</div>'
        f'<div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;">{subtitle}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def section_label(text: str):
    st.markdown(
        f'<div style="font-family:Syne,sans-serif;font-size:0.62rem;font-weight:700;'
        f'letter-spacing:0.20em;text-transform:uppercase;color:#6b7fad;margin-bottom:14px;'
        f'margin-top:22px;display:flex;align-items:center;gap:10px;">'
        f'{text} <span style="flex:1;height:1px;background:linear-gradient(to right,#cbd5e1,transparent);'
        f'display:inline-block;"></span></div>',
        unsafe_allow_html=True,
    )


def chart_layout(fig, xlab="", ylab="", height=360):
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=8, b=8),
        plot_bgcolor="#ffffff", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans", color=SLATE, size=12),
        xaxis_title=xlab, yaxis_title=ylab,
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=11),
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(size=11))
    fig.update_yaxes(showgrid=True,  gridcolor=GRID, linecolor="rgba(0,0,0,0)", tickfont=dict(size=11))
    return fig


# =============================================================================
# PAGE
# =============================================================================

def render():

    # =========================================================================
    # CSS
    # =========================================================================
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .block-container {
        padding-top: 0.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1280px;
    }
    .stApp { background: #f0f4fc; }
    div[data-testid="stThumbValue"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================================
    # SIDEBAR
    # =========================================================================
    st.sidebar.markdown(
        '<div style="height:1px;background:#d0d9ee;margin:0 0 10px 0;"></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div style="font-family:IBM Plex Sans,sans-serif;font-size:0.62rem;font-weight:600;'
        'letter-spacing:0.16em;text-transform:uppercase;color:#94a3b8;margin-bottom:8px;">'
        '🫀 Kidney Failure Filters</div>',
        unsafe_allow_html=True,
    )

    cohorts_df = fetch_cohorts()

    if "_error" in cohorts_df.columns:
        st.error(f"Database error loading cohorts: {cohorts_df['_error'].iloc[0]}")
        st.stop()

    if cohorts_df.empty:
        st.warning("No cohorts found. Check DB connection.")
        st.stop()

    cohort_options = {
        f"{row['name']} ({int(row['patient_count'])} pts)": int(row["id"])
        for _, row in cohorts_df.iterrows()
    }

    selected_label = st.sidebar.selectbox(
        "🧬 Cohort",
        options=list(cohort_options.keys()),
        index=0,
    )
    selected_cohort_id   = cohort_options[selected_label]
    selected_cohort_name = cohorts_df.loc[cohorts_df["id"] == selected_cohort_id, "name"].iloc[0]

    selected_rule = st.sidebar.selectbox(
        "📋 Event Type",
        options=["All", "Transplant", "Dialysis", "eGFR <15 x2"],
        index=0,
    )
    rule_filter = (
        ["Transplant", "Dialysis", "eGFR <15 x2"]
        if selected_rule == "All"
        else [selected_rule]
    )

    if st.sidebar.button("🔄 Refresh data"):
        fetch_events.clear()
        fetch_cohorts.clear()
        st.rerun()

    # =========================================================================
    # HERO
    # =========================================================================
    st.markdown(f"""
    <div style="background:linear-gradient(118deg,#1e1b4b 0%,#4c1d95 52%,#6d28d9 100%);
                border-radius:24px;padding:34px 40px 30px 40px;margin-bottom:28px;
                position:relative;overflow:hidden;box-shadow:0 20px 60px rgba(30,27,75,0.35);">
        <div style="display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,0.10);
                    border:1px solid rgba(255,255,255,0.18);border-radius:999px;padding:4px 14px;
                    font-size:0.70rem;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;
                    color:#ddd6fe;margin-bottom:14px;">
            <span style="width:6px;height:6px;border-radius:50%;background:#34d399;display:inline-block;"></span>
            Kidney Failure Events · Clinical Audit
        </div>
        <div style="font-family:Syne,sans-serif;font-size:2.05rem;font-weight:800;color:#fff;
                    line-height:1.15;letter-spacing:-0.02em;margin-bottom:8px;">
            🫀 Kidney Failure Events
        </div>
        <div style="font-size:0.90rem;color:rgba(221,214,254,0.82);max-width:640px;
                    line-height:1.65;font-weight:300;">
            Patients meeting kidney failure criteria: transplant, dialysis, or two eGFR readings
            below 15 mL/min/1.73m² at least 28 days apart with no intervening recovery.
        </div>
        <div style="margin-top:20px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.13);">
            <span style="font-size:0.68rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;
                         color:rgba(196,181,253,0.75);">
                {selected_cohort_name}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================================
    # LOAD DATA
    # =========================================================================
    with st.spinner("Fetching data…"):
        df = fetch_events(selected_cohort_id)

    if "_error" in df.columns:
        st.error(f"Database error: {df['_error'].iloc[0]}")
        st.stop()

    if df.empty:
        st.info(f"No kidney failure events found for cohort: {selected_cohort_name}")
        st.stop()

    for col in ["event_date", "transplant_date", "dialysis_date",
                "egfr_first_date", "egfr_second_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["egfr_first_value", "egfr_second_value", "egfr_days_between"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df_view = df[df["rule"].isin(rule_filter)] if rule_filter else df.copy()

    if df_view.empty:
        st.warning("No events match the selected rule filter.")
        df_view = df.copy()

    # =========================================================================
    # METRICS
    # =========================================================================
    unique_patients   = df_view["patient_id"].nunique()
    transplant_count  = df_view.loc[df_view["rule"] == "Transplant",  "patient_id"].nunique()
    dialysis_count    = df_view.loc[df_view["rule"] == "Dialysis",    "patient_id"].nunique()
    egfr_count        = df_view.loc[df_view["rule"] == "eGFR <15 x2","patient_id"].nunique()
    multi_trigger     = (
        df_view.groupby("patient_id")["rule"].nunique().ge(2).sum()
    )
    earliest = df_view["event_date"].min()
    latest   = df_view["event_date"].max()
    earliest_str = earliest.strftime("%d %b %Y") if pd.notna(earliest) else "—"
    latest_str   = latest.strftime("%d %b %Y")   if pd.notna(latest)   else "—"

    # =========================================================================
    # KPI CARDS — ROW 1
    # =========================================================================
    section_label("Event Summary")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Patients with Events",  f"{unique_patients:,}", "c-violet", "🫀", "Unique patients meeting ≥1 criterion")
    with c2: kpi_card("Transplant",            f"{transplant_count:,}", "c-blue",  "🔬", "Received a kidney transplant")
    with c3: kpi_card("Dialysis",              f"{dialysis_count:,}",  "c-teal",   "💉", "Started renal replacement therapy")
    with c4: kpi_card("eGFR <15 ×2",           f"{egfr_count:,}",     "c-rose",   "📉", "Two readings <15, ≥28 days apart")

    st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Multiple Triggers",  f"{multi_trigger:,}", "c-amber",  "⚡", "Patients meeting 2+ criteria")
    with c2: kpi_card("Earliest Event",     earliest_str,         "c-slate",  "📅", "First recorded kidney failure event")
    with c3: kpi_card("Latest Event",       latest_str,           "c-slate",  "📅", "Most recent event in this cohort")
    with c4: kpi_card("Total Event Rows",   f"{len(df_view):,}",  "c-slate",  "📋", "One row per patient-rule combination")

    # =========================================================================
    # CHARTS
    # =========================================================================
    section_label("Event Breakdown")
    col_l, col_r = st.columns(2, gap="large")

    with col_l:
        chart_card("🔢 Patients by Event Type", "How many unique patients meet each kidney failure criterion")
        rule_counts = (
            df_view.groupby("rule")["patient_id"].nunique()
            .reset_index(name="patients").sort_values("patients", ascending=True)
        )
        if not rule_counts.empty:
            colors = [RULE_COLORS.get(r, BLUE) for r in rule_counts["rule"]]
            fig1 = go.Figure(go.Bar(
                x=rule_counts["patients"], y=rule_counts["rule"],
                orientation="h",
                text=rule_counts["patients"], textposition="auto",
                insidetextanchor="end",
                textfont=dict(size=13, family="IBM Plex Sans", color="#fff"),
                marker=dict(color=colors),
                opacity=0.92,
            ))
            fig1 = chart_layout(fig1, xlab="Unique patients", height=280)
            fig1.update_layout(yaxis=dict(categoryorder="total ascending"), margin=dict(l=130, r=20, t=10, b=8))
            fig1.update_yaxes(showgrid=False)
            st.plotly_chart(fig1, use_container_width=True)

    with col_r:
        chart_card("📅 Events by Year", "Distribution of first kidney failure events over time")
        if "event_date" in df_view.columns:
            yr_df = df_view.dropna(subset=["event_date"]).copy()
            yr_df["year"] = yr_df["event_date"].dt.year.astype(int)
            yr_pivot = (
                yr_df.groupby(["year", "rule"])["patient_id"].nunique()
                .reset_index(name="patients")
            )
            if not yr_pivot.empty:
                # Pivot to wide so all rules share the same sorted year index
                yr_wide = (
                    yr_pivot.pivot(index="year", columns="rule", values="patients")
                    .fillna(0)
                    .sort_index()
                    .reset_index()
                )
                x_years = yr_wide["year"].astype(str).tolist()
                fig2 = go.Figure()
                for rule, color in RULE_COLORS.items():
                    if rule in yr_wide.columns:
                        fig2.add_trace(go.Bar(
                            name=rule, x=x_years, y=yr_wide[rule],
                            marker_color=color, opacity=0.88,
                        ))
                fig2.update_layout(barmode="stack")
                fig2 = chart_layout(fig2, xlab="Year", ylab="Patients", height=280)
                fig2.update_xaxes(type="category", tickangle=-45)
                st.plotly_chart(fig2, use_container_width=True)

    # =========================================================================
    # EVIDENCE TABLE
    # =========================================================================
    section_label("Patient Evidence")

    display_df = df_view.copy()

    date_cols = ["event_date", "transplant_date", "dialysis_date",
                 "egfr_first_date", "egfr_second_date"]
    for col in date_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].dt.strftime("%d-%m-%Y").where(
                display_df[col].notna(), other=""
            )

    col_rename = {
        "patient_id":        "Patient ID",
        "event_date":        "Event Date",
        "rule":              "Rule",
        "transplant_date":   "Transplant Date",
        "dialysis_date":     "Dialysis Date",
        "egfr_first_value":  "eGFR 1st (mL/min)",
        "egfr_first_date":   "eGFR 1st Date",
        "egfr_second_value": "eGFR 2nd (mL/min)",
        "egfr_second_date":  "eGFR 2nd Date",
        "egfr_days_between": "Days Between",
    }
    display_df = display_df.rename(columns=col_rename)
    show_cols  = [c for c in col_rename.values() if c in display_df.columns]
    display_df = display_df[show_cols].reset_index(drop=True)

    for col in ["eGFR 1st (mL/min)", "eGFR 2nd (mL/min)"]:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors="coerce").round(1)

    st.markdown(
        f'<div style="font-size:0.80rem;color:#64748b;margin-bottom:8px;">'
        f'Showing <strong>{len(display_df):,}</strong> event rows for '
        f'<strong>{unique_patients:,}</strong> unique patients — '
        f'one row per patient per rule triggered.</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(display_df, use_container_width=True, height=420)

    # =========================================================================
    # DOWNLOAD
    # =========================================================================
    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️  Download evidence table (CSV)",
        data=csv_bytes,
        file_name=f"kidney_failure_{selected_cohort_name.replace(' ', '_')}.csv",
        mime="text/csv",
    )
