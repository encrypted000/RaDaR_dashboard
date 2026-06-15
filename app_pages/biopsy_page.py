import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta

from lib.outputs_reader import (
    list_raw_snapshots,
    load_raw_snapshot,
    load_weekly_kpis,
)
from lib.constants import PAEDIATRIC_SITE_CODES

# =============================================================================
# SETTINGS
# =============================================================================

MODULE = "biopsy"

NAVY       = "#0c1f4a"
INDIGO     = "#1e3a8a"
BLUE       = "#2563eb"
SKY        = "#0ea5e9"
TEAL       = "#0d9488"
AMBER      = "#d97706"
ROSE       = "#e11d48"
SLATE      = "#475569"
GRID       = "#e2e8f0"

# =============================================================================
# DATA HELPERS
# =============================================================================

@st.cache_data
def load_snapshot_cached(path):
    return load_raw_snapshot(path)


@st.cache_data(ttl=600, show_spinner=False)
def build_hospital_weekly_trends() -> pd.DataFrame:
    """Derive per-hospital new_missing / resolved by comparing consecutive raw snapshots."""
    snaps = sorted(list_raw_snapshots(MODULE), key=lambda p: p.stem)
    if len(snaps) < 2:
        return pd.DataFrame(columns=["week_monday", "hospital_name", "new_missing", "resolved"])

    rows = []
    prev_ids_by_hosp: dict = {}

    for i, snap_path in enumerate(snaps):
        curr_df = load_snapshot_cached(snap_path)
        curr_week = snapshot_week_monday(snap_path)
        if curr_week is None or "patient_id" not in curr_df.columns or "hospital_name" not in curr_df.columns:
            prev_ids_by_hosp = {}
            continue

        curr_df = curr_df.copy()
        curr_df["patient_id"] = curr_df["patient_id"].astype(str)
        curr_ids_by_hosp: dict = (
            curr_df.groupby("hospital_name")["patient_id"].apply(set).to_dict()
        )

        if i > 0:
            for hosp in set(prev_ids_by_hosp) | set(curr_ids_by_hosp):
                prev_set = prev_ids_by_hosp.get(hosp, set())
                curr_set = curr_ids_by_hosp.get(hosp, set())
                new_m = len(curr_set - prev_set)
                res   = len(prev_set - curr_set)
                if new_m > 0 or res > 0:
                    rows.append({
                        "week_monday":   curr_week,
                        "hospital_name": hosp,
                        "new_missing":   new_m,
                        "resolved":      res,
                    })

        prev_ids_by_hosp = curr_ids_by_hosp

    return pd.DataFrame(rows)


def snapshot_week_monday(snapshot_path) -> pd.Timestamp | None:
    name = snapshot_path.stem
    prefix = f"missing_{MODULE}_"
    if not name.startswith(prefix):
        return None
    dt_str = name.replace(prefix, "")
    try:
        snap_dt = pd.to_datetime(dt_str, format="%Y-%m-%d_%H%M%S", errors="raise")
        week_monday = snap_dt.normalize() - timedelta(days=snap_dt.weekday())
        return pd.Timestamp(week_monday)
    except Exception:
        return None


def format_week_label(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%d %b %Y")


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

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    .block-container {
        padding-top: 0.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1280px;
    }

    .stApp { background: #f0f4fc; }

    /* ── Hero ── */
    .biopsy-hero {
        background: linear-gradient(118deg, #0c1f4a 0%, #1e3a8a 52%, #1d4ed8 100%);
        border-radius: 24px;
        padding: 34px 40px 30px 40px;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 60px rgba(12,31,74,0.32);
    }
    .biopsy-hero::before {
        content:"";
        position:absolute; top:-80px; right:-80px;
        width:360px; height:360px; border-radius:50%;
        background: radial-gradient(circle, rgba(96,165,250,0.14) 0%, transparent 70%);
    }
    .biopsy-hero::after {
        content:"";
        position:absolute; bottom:-60px; left:25%;
        width:280px; height:280px; border-radius:50%;
        background: radial-gradient(circle, rgba(14,165,233,0.10) 0%, transparent 70%);
    }
    .hero-pill {
        display:inline-flex; align-items:center; gap:7px;
        background: rgba(255,255,255,0.10);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 999px; padding: 4px 14px;
        font-size: 0.70rem; font-weight:600; letter-spacing:0.14em;
        text-transform:uppercase; color:#bfdbfe;
        margin-bottom: 14px;
    }
    .hero-pill-dot {
        width:6px; height:6px; border-radius:50%;
        background:#34d399; box-shadow: 0 0 7px #34d399;
        animation: blink 2s ease-in-out infinite;
    }
    @keyframes blink {
        0%,100% { opacity:1; transform:scale(1); }
        50%      { opacity:0.5; transform:scale(1.4); }
    }
    .hero-title {
        font-family:'Syne',sans-serif;
        font-size:2.05rem; font-weight:800; color:#fff;
        line-height:1.15; letter-spacing:-0.02em; margin-bottom:8px;
    }
    .hero-sub {
        font-size:0.90rem; color:rgba(186,219,255,0.82);
        max-width:640px; line-height:1.65; font-weight:300;
    }
    .hero-stats {
        display:flex; gap:30px; margin-top:22px; flex-wrap:wrap;
    }
    .hero-stat {
        display:flex; flex-direction:column; gap:2px;
    }
    .hero-stat-val {
        font-family:'Syne',sans-serif;
        font-size:1.55rem; font-weight:800; color:#fff; line-height:1;
    }
    .hero-stat-label {
        font-size:0.70rem; color:rgba(147,197,253,0.85);
        text-transform:uppercase; letter-spacing:0.12em; font-weight:500;
    }
    .hero-stat-divider {
        width:1px; background:rgba(255,255,255,0.15); align-self:stretch; margin:4px 0;
    }

    /* ── Section heading ── */
    .sec-label {
        font-family:'Syne',sans-serif;
        font-size:0.62rem; font-weight:700;
        letter-spacing:0.20em; text-transform:uppercase;
        color:#6b7fad; margin-bottom:14px; margin-top:6px;
        display:flex; align-items:center; gap:10px;
    }
    .sec-label::after {
        content:""; flex:1; height:1px;
        background:linear-gradient(to right, #cbd5e1, transparent);
    }

    /* ── KPI card ── */
    .kpi-card {
        background:#ffffff;
        border-radius:18px;
        padding:18px 18px 14px 18px;
        border:1px solid rgba(203,213,225,0.55);
        box-shadow: 0 4px 20px rgba(30,58,138,0.06);
        position:relative; overflow:hidden;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
        height:100%;
    }
    .kpi-card:hover {
        transform:translateY(-3px);
        box-shadow: 0 12px 36px rgba(30,58,138,0.13);
    }
    .kpi-card::before {
        content:""; position:absolute;
        top:0; left:0; right:0; height:3px; border-radius:18px 18px 0 0;
    }
    .kpi-card.c-blue::before   { background:linear-gradient(90deg,#2563eb,#60a5fa); }
    .kpi-card.c-green::before  { background:linear-gradient(90deg,#16a34a,#4ade80); }
    .kpi-card.c-red::before    { background:linear-gradient(90deg,#dc2626,#f87171); }
    .kpi-card.c-violet::before { background:linear-gradient(90deg,#7c3aed,#a78bfa); }
    .kpi-card.c-amber::before  { background:linear-gradient(90deg,#d97706,#fbbf24); }
    .kpi-card.c-teal::before   { background:linear-gradient(90deg,#0d9488,#2dd4bf); }
    .kpi-card.c-orange::before { background:linear-gradient(90deg,#ea580c,#fb923c); }
    .kpi-card.c-pink::before   { background:linear-gradient(90deg,#be185d,#f472b6); }

    .kpi-icon  { font-size:1.35rem; margin-bottom:8px; }
    .kpi-label {
        font-size:0.72rem; font-weight:500; color:#64748b;
        letter-spacing:0.05em; text-transform:uppercase; margin-bottom:5px;
    }
    .kpi-value {
        font-family:'Syne',sans-serif;
        font-size:2.1rem; font-weight:800; color:#0c1f4a;
        line-height:1; letter-spacing:-0.03em;
    }
    .kpi-badge {
        display:inline-flex; align-items:center; gap:4px;
        border-radius:999px; padding:2px 9px;
        font-size:0.68rem; font-weight:600; margin-top:6px;
    }
    .badge-up   { background:#fee2e2; color:#dc2626; }
    .badge-down { background:#dcfce7; color:#16a34a; }
    .kpi-note   { font-size:0.70rem; color:#94a3b8; margin-top:5px; font-style:italic; }

    /* ── Chart card ── */
    .chart-card {
        background:#ffffff; border-radius:20px;
        padding:22px 24px 16px 24px;
        border:1px solid rgba(203,213,225,0.55);
        box-shadow:0 4px 20px rgba(30,58,138,0.06);
        margin-bottom:4px;
    }
    .chart-title {
        font-family:'Syne',sans-serif;
        font-size:0.92rem; font-weight:700; color:#0c1f4a;
        margin-bottom:2px;
    }
    .chart-sub {
        font-size:0.75rem; color:#94a3b8; margin-bottom:10px;
    }

    /* ── Info note ── */
    .info-note {
        background:#f0f9ff; border-left:3px solid #0ea5e9;
        border-radius:0 10px 10px 0;
        padding:10px 14px; font-size:0.78rem; color:#0369a1;
        line-height:1.55; margin-top:8px;
    }

    /* ── Caption ── */
    .page-caption {
        font-size:0.75rem; color:#94a3b8;
        font-style:italic; margin-top:4px;
        letter-spacing:0.02em;
    }

    /* ── Hide slider tooltips ── */
    div[data-testid="stThumbValue"] { display: none !important; }

    #MainMenu, footer, header { visibility:hidden; }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================================
    # SIDEBAR
    # =========================================================================
    st.sidebar.markdown('<div style="height:1px;background:#d0d9ee;margin:0 0 10px 0;"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div style="font-family:IBM Plex Sans,sans-serif;font-size:0.62rem;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;color:#94a3b8;margin-bottom:8px;">🔬 Biopsy Filters</div>', unsafe_allow_html=True)

    snapshots = list_raw_snapshots(MODULE)

    if not snapshots:
        st.warning("No biopsy snapshots found. Run: python -m scripts.run_biopsy_backend")
        st.stop()

    selected_idx = st.sidebar.selectbox(
        "📅 Snapshot",
        options=range(len(snapshots)),
        index=0,
        format_func=lambda i: snapshots[i].name,
    )
    selected_snapshot = snapshots[selected_idx]

    # =========================================================================
    # LOAD DATA
    # =========================================================================
    df      = load_snapshot_cached(selected_snapshot)
    kpi_df  = load_weekly_kpis(MODULE)
    snap_week = snapshot_week_monday(selected_snapshot)

    if "recruited_date" in df.columns:
        df["recruited_date"] = pd.to_datetime(df["recruited_date"], errors="coerce")
    if "diagnosed_date" in df.columns:
        df["diagnosed_date"] = pd.to_datetime(df["diagnosed_date"], errors="coerce")
    if "age" in df.columns:
        df["age"] = pd.to_numeric(df["age"], errors="coerce")

    df = df.dropna(subset=["recruited_date"])

    if df.empty:
        st.warning("Selected snapshot contains no valid recruited dates.")
        st.stop()

    df["recruitment_year"] = df["recruited_date"].dt.year.astype(int)

    if "age" in df.columns:
        df["age_group"] = df["age"].apply(
            lambda x: "Child" if pd.notna(x) and x < 18 else "Adult"
        )

    if not kpi_df.empty and "week_monday" in kpi_df.columns:
        kpi_df["week_monday"] = pd.to_datetime(kpi_df["week_monday"], errors="coerce")
        kpi_df = kpi_df.sort_values("week_monday").reset_index(drop=True)

    if "hospital_code" in df.columns:
        st.sidebar.markdown(
            '<div style="font-family:IBM Plex Sans,sans-serif;font-size:0.62rem;font-weight:600;'
            'letter-spacing:0.14em;text-transform:uppercase;color:#94a3b8;margin:8px 0 4px 0;">'
            '👶 Paediatric Centres</div>',
            unsafe_allow_html=True,
        )
        paediatric_only = st.sidebar.checkbox("Show paediatric sites only", value=False)
        if paediatric_only:
            df = df[df["hospital_code"].isin(PAEDIATRIC_SITE_CODES)]

    if "hospital_name" in df.columns:
        hospitals = sorted(df["hospital_name"].dropna().unique().tolist())
        selected_hospitals = st.sidebar.multiselect("🏥 Hospital", hospitals, default=[])
        if selected_hospitals:
            df = df[df["hospital_name"].isin(selected_hospitals)]

    if "age_group" in df.columns:
        selected_age_group = st.sidebar.multiselect("👤 Patient type", ["Adult", "Child"], default=[])
        if selected_age_group:
            df = df[df["age_group"].isin(selected_age_group)]

    if "diagnosed_date" in df.columns:
        diag_df = df[df["diagnosed_date"].notna()].copy()
        if not diag_df.empty:
            diag_df["diagnosis_year"] = diag_df["diagnosed_date"].dt.year.astype(int)
            min_dy = int(diag_df["diagnosis_year"].min())
            max_dy = int(diag_df["diagnosis_year"].max())
            if min_dy == max_dy:
                st.sidebar.caption(f"Diagnosed year: {min_dy}")
                diag_year_from, diag_year_to = min_dy, max_dy
            else:
                diag_year_from, diag_year_to = st.sidebar.slider(
                    "🩺 Diagnosed year", min_dy, max_dy, (min_dy, max_dy))
            df = df[
                df["diagnosed_date"].isna() |
                df["diagnosed_date"].dt.year.between(diag_year_from, diag_year_to)
            ]

    if df.empty:
        st.warning("No records found for the selected filters.")
        st.stop()

    min_year = int(df["recruitment_year"].min())
    max_year = int(df["recruitment_year"].max())
    if min_year == max_year:
        st.sidebar.caption(f"Recruitment year: {min_year}")
        year_from, year_to = min_year, max_year
    else:
        year_from, year_to = st.sidebar.slider(
            "📆 Recruitment year", min_year, max_year, (min_year, max_year))

    filtered = df[
        (df["recruitment_year"] >= year_from) &
        (df["recruitment_year"] <= year_to)
    ].copy()

    if filtered.empty:
        st.warning("No records found for the selected filters.")
        st.stop()

    filtered["recruited_date_only"] = filtered["recruited_date"].dt.date
    if "diagnosed_date" in filtered.columns:
        filtered["diagnosed_date_only"] = filtered["diagnosed_date"].dt.date

    # =========================================================================
    # =========================================================================
    total_eligible = uploaded = overall_missing = new_missing = resolved = "—"
    completeness = adult_missing = child_missing = "—"
    selected_kpi = None

    if not kpi_df.empty:
        if snap_week is not None:
            matched = kpi_df[kpi_df["week_monday"] == snap_week]
            if not matched.empty:
                selected_kpi = matched.iloc[-1]
        if selected_kpi is None:
            selected_kpi = kpi_df.iloc[-1]

    def _int(row, col):
        return int(row[col]) if col in row and pd.notna(row[col]) else "—"
    def _flt(row, col, fmt=".1f"):
        return f"{float(row[col]):{fmt}}%" if col in row and pd.notna(row[col]) else "—"

    if selected_kpi is not None:
        total_eligible   = _int(selected_kpi, "total_eligible")
        uploaded         = _int(selected_kpi, "uploaded")
        overall_missing  = _int(selected_kpi, "missing_count")
        completeness     = _flt(selected_kpi, "completeness_percent")
        new_missing      = _int(selected_kpi, "new_missing")
        resolved         = _int(selected_kpi, "resolved")
        adult_missing    = _int(selected_kpi, "adult_missing")
        child_missing    = _int(selected_kpi, "child_missing")

    filtered_missing          = filtered["patient_id"].astype(str).nunique()
    filtered_hospitals        = filtered["hospital_name"].dropna().nunique() if "hospital_name" in filtered.columns else "—"
    filtered_adult_missing    = "—"
    filtered_child_missing    = "—"
    if "age_group" in filtered.columns:
        filtered_adult_missing = filtered.loc[filtered["age_group"] == "Adult", "patient_id"].astype(str).nunique()
        filtered_child_missing = filtered.loc[filtered["age_group"] == "Child", "patient_id"].astype(str).nunique()

    kpi_df_view = kpi_df.copy()
    if snap_week is not None and not kpi_df_view.empty:
        kpi_df_view = kpi_df_view[kpi_df_view["week_monday"] <= snap_week].copy()
    if not kpi_df_view.empty:
        kpi_df_view["week_label"] = format_week_label(kpi_df_view["week_monday"])

    # =========================================================================
    # HERO
    # =========================================================================
    snap_label = selected_snapshot.name if selected_snapshot else "—"

    total_in_view = filtered["patient_id"].astype(str).nunique()
    hosp_in_view  = filtered["hospital_name"].dropna().nunique() if "hospital_name" in filtered.columns else "—"

    pill_style       = "display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.18);border-radius:999px;padding:4px 14px;font-size:0.80rem;font-weight:600;color:#fff;"
    pill_label_style = "opacity:0.65;font-size:0.70rem;"

    st.markdown(f"""
    <div style="background:linear-gradient(118deg,#0c1f4a 0%,#1e3a8a 52%,#1d4ed8 100%);border-radius:24px;padding:34px 40px 30px 40px;margin-bottom:28px;position:relative;overflow:hidden;box-shadow:0 20px 60px rgba(12,31,74,0.32);">
        <div style="display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.18);border-radius:999px;padding:4px 14px;font-size:0.70rem;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:#bfdbfe;margin-bottom:14px;">
            <span style="width:6px;height:6px;border-radius:50%;background:#34d399;display:inline-block;"></span>
            Biopsy · Missing Report Tracker
        </div>
        <div style="font-family:Syne,sans-serif;font-size:2.05rem;font-weight:800;color:#fff;line-height:1.15;letter-spacing:-0.02em;margin-bottom:8px;">🔬 Biopsy Report Dashboard</div>
        <div style="font-size:0.90rem;color:rgba(186,219,255,0.82);max-width:640px;line-height:1.65;font-weight:300;">Track missing biopsy reports, monitor weekly backlog trends, and identify hospitals with outstanding records across cohorts.</div>
        <div style="margin-top:20px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.13);display:flex;align-items:center;flex-wrap:wrap;gap:10px;">
            <span style="font-size:0.65rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:rgba(147,197,253,0.75);margin-right:4px;">Filtered view →</span>
            <span style="{pill_style}"><span style="{pill_label_style}">🔍 Missing</span>{filtered_missing}</span>
            <span style="{pill_style}"><span style="{pill_label_style}">👨 Adults</span>{filtered_adult_missing}</span>
            <span style="{pill_style}"><span style="{pill_label_style}">👦 Children</span>{filtered_child_missing}</span>
            <span style="{pill_style}"><span style="{pill_label_style}">🏥 Hospitals</span>{filtered_hospitals}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)



    # =========================================================================
    ACCENT = {
        "c-blue":   "linear-gradient(90deg,#2563eb,#60a5fa)",
        "c-green":  "linear-gradient(90deg,#16a34a,#4ade80)",
        "c-red":    "linear-gradient(90deg,#dc2626,#f87171)",
        "c-violet": "linear-gradient(90deg,#7c3aed,#a78bfa)",
        "c-amber":  "linear-gradient(90deg,#d97706,#fbbf24)",
        "c-teal":   "linear-gradient(90deg,#0d9488,#2dd4bf)",
        "c-orange": "linear-gradient(90deg,#ea580c,#fb923c)",
        "c-pink":   "linear-gradient(90deg,#be185d,#f472b6)",
    }

    # inject hover CSS once using a counter trick via a unique class per card
    import uuid

    def kpi(label, value, color_cls, icon, badge=None, note=None):
        bar = ACCENT.get(color_cls, ACCENT["c-blue"])
        card_id = f"kpi-{uuid.uuid4().hex[:8]}"
        badge_html = ""
        if badge == "up":
            badge_html = '<div style="display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:2px 9px;font-size:0.68rem;font-weight:600;margin-top:6px;background:#fee2e2;color:#dc2626;">↑ New this week</div>'
        elif badge == "down":
            badge_html = '<div style="display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:2px 9px;font-size:0.68rem;font-weight:600;margin-top:6px;background:#dcfce7;color:#16a34a;">↓ Resolved</div>'
        note_html = f'<div style="font-size:0.70rem;color:#94a3b8;margin-top:5px;font-style:italic;">{note}</div>' if note else ""
        st.markdown(f"""
        <style>
        #{card_id} {{
            background:#ffffff;
            border-radius:18px;
            padding:18px 18px 14px 18px;
            border:1px solid rgba(203,213,225,0.55);
            box-shadow:0 4px 20px rgba(30,58,138,0.06);
            position:relative;
            overflow:hidden;
            height:100%;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
            cursor: default;
        }}
        #{card_id}:hover {{
            transform: translateY(-3px);
            box-shadow: 0 12px 36px rgba(30,58,138,0.13);
        }}
        </style>
        <div id="{card_id}">
            <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:18px 18px 0 0;background:{bar};"></div>
            <div style="font-size:1.35rem;margin-bottom:8px;">{icon}</div>
            <div style="font-size:0.72rem;font-weight:600;color:#64748b;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:5px;font-family:'IBM Plex Sans',sans-serif;">{label}</div>
            <div style="font-family:'IBM Plex Sans',sans-serif;font-size:2.0rem;font-weight:700;color:#0c1f4a;line-height:1;letter-spacing:-0.01em;">{value}</div>
            {badge_html}{note_html}
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # WEEKLY PERFORMANCE KPIs
    # =========================================================================
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:0.62rem;font-weight:700;letter-spacing:0.20em;text-transform:uppercase;color:#6b7fad;margin-bottom:14px;margin-top:6px;display:flex;align-items:center;gap:10px;">Weekly Performance Overview <span style="flex:1;height:1px;background:linear-gradient(to right,#cbd5e1,transparent);display:inline-block;"></span></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Total eligible patients",       total_eligible,  "c-blue",   "🧑‍⚕️", note="All registered patients")
    with c2: kpi("Patients with Reports uploaded",              uploaded,        "c-green",  "✅",   note="Successfully submitted")
    with c3: kpi("Missing reports",               overall_missing, "c-red",    "⚠️",   note="Outstanding biopsy records")
    with c4: kpi("Completeness",                  completeness,    "c-violet", "📊",   note="Weekly snapshot rate")

    st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("New missing (7d)",              new_missing,     "c-amber",  "🆕",  badge="up")
    with c2: kpi("Resolved (7d)",                 resolved,        "c-teal",   "✔️",  badge="down")
    with c3: kpi("Adult missing",                 adult_missing,   "c-orange", "👨")
    with c4: kpi("Child missing",                 child_missing,   "c-pink",   "👦")

    st.markdown('<p style="font-size:0.75rem;color:#94a3b8;font-style:italic;margin-top:4px;letter-spacing:0.02em;">Weekly KPIs reflect the selected snapshot week and do not change with sidebar filters.</p>', unsafe_allow_html=True)

    # =========================================================================
    # CHART HELPERS
    # =========================================================================
    def chart_layout(fig, xlab="", ylab="", height=360):
        fig.update_layout(
            height=height,
            margin=dict(l=8, r=8, t=8, b=8),
            plot_bgcolor="#ffffff",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans", color=SLATE, size=12),
            xaxis_title=xlab,
            yaxis_title=ylab,
            legend=dict(
                bgcolor="rgba(0,0,0,0)", borderwidth=0,
                font=dict(size=11), orientation="h",
                yanchor="bottom", y=1.02, xanchor="right", x=1,
            ),
        )
        fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(size=11))
        fig.update_yaxes(showgrid=True,  gridcolor=GRID, linecolor="rgba(0,0,0,0)", tickfont=dict(size=11))
        return fig

    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:0.62rem;font-weight:700;letter-spacing:0.20em;text-transform:uppercase;color:#6b7fad;margin-bottom:14px;margin-top:22px;display:flex;align-items:center;gap:10px;">Trend Analysis <span style="flex:1;height:1px;background:linear-gradient(to right,#cbd5e1,transparent);display:inline-block;"></span></div>', unsafe_allow_html=True)

    filtered["month"] = filtered["recruited_date"].dt.to_period("M").apply(lambda r: r.start_time)
    trend = (
        filtered.groupby("month")["patient_id"]
        .nunique()
        .reset_index(name="missing_count")
        .sort_values("month")
    )

    fig1 = px.bar(trend, x="month", y="missing_count")
    fig1.update_traces(
        marker_color=BLUE,
        marker_line_color="rgba(0,0,0,0)",
        opacity=0.88,
    )
    fig1 = chart_layout(fig1, xlab="Recruitment month", ylab="Missing patients")

    colA, colB = st.columns(2, gap="large")

    with colA:
        st.markdown('<div style="background:#ffffff;border-radius:20px;padding:16px 20px 8px 20px;border:1px solid rgba(203,213,225,0.55);box-shadow:0 4px 20px rgba(30,58,138,0.06);margin-bottom:4px;"><div style="font-family:Syne,sans-serif;font-size:0.92rem;font-weight:700;color:#0c1f4a;margin-bottom:2px;">📅 Backlog by Recruitment Month</div><div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;">Patients missing reports, grouped by their recruitment month</div></div>', unsafe_allow_html=True)
        st.plotly_chart(fig1, use_container_width=True)

    with colB:
        hosp_subtitle = (
            f"Weekly movement for: {', '.join(selected_hospitals)}"
            if selected_hospitals else "Weekly movement in the missing report backlog"
        )
        st.markdown(f'<div style="background:#ffffff;border-radius:20px;padding:16px 20px 8px 20px;border:1px solid rgba(203,213,225,0.55);box-shadow:0 4px 20px rgba(30,58,138,0.06);margin-bottom:4px;"><div style="font-family:Syne,sans-serif;font-size:0.92rem;font-weight:700;color:#0c1f4a;margin-bottom:2px;">↕️ New Missing vs Resolved (Weekly)</div><div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;">{hosp_subtitle}</div></div>', unsafe_allow_html=True)

        if selected_hospitals:
            hosp_trend = build_hospital_weekly_trends()
            if not hosp_trend.empty:
                chart_df = (
                    hosp_trend[hosp_trend["hospital_name"].isin(selected_hospitals)]
                    .groupby("week_monday")[["new_missing", "resolved"]]
                    .sum().reset_index().sort_values("week_monday")
                )
                if snap_week is not None:
                    chart_df = chart_df[chart_df["week_monday"] <= snap_week]
                chart_df["week_label"] = format_week_label(chart_df["week_monday"])
            else:
                chart_df = pd.DataFrame()
        else:
            chart_df = kpi_df_view.copy() if not kpi_df_view.empty else pd.DataFrame()

        if not chart_df.empty and "new_missing" in chart_df.columns:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                name="New missing",
                x=chart_df["week_label"],
                y=chart_df["new_missing"],
                marker_color=ROSE,
                opacity=0.88,
            ))
            fig2.add_trace(go.Bar(
                name="Resolved",
                x=chart_df["week_label"],
                y=chart_df["resolved"],
                marker_color=TEAL,
                opacity=0.88,
            ))
            fig2.update_layout(barmode="group")
            fig2 = chart_layout(fig2, xlab="Week starting", ylab="Patients")
            fig2.update_xaxes(type="category")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No weekly KPI history available yet.")

        st.markdown('<div style="background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:0 10px 10px 0;padding:10px 14px;font-size:0.78rem;color:#0369a1;line-height:1.55;margin-top:8px;"><strong>New missing</strong> — patients newly appearing on the missing list since the previous snapshot.<br><strong>Resolved</strong> — patients who were missing last week but are no longer missing now.</div>', unsafe_allow_html=True)

    # =========================================================================
    # BACKLOG OVERVIEW
    # =========================================================================
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:0.62rem;font-weight:700;letter-spacing:0.20em;text-transform:uppercase;color:#6b7fad;margin-bottom:14px;margin-top:22px;display:flex;align-items:center;gap:10px;">Backlog Overview <span style="flex:1;height:1px;background:linear-gradient(to right,#cbd5e1,transparent);display:inline-block;"></span></div>', unsafe_allow_html=True)

    col_l, col_r = st.columns(2, gap="large")

    with col_l:
        st.markdown('<div style="background:#ffffff;border-radius:20px;padding:16px 20px 8px 20px;border:1px solid rgba(203,213,225,0.55);box-shadow:0 4px 20px rgba(30,58,138,0.06);margin-bottom:4px;"><div style="font-family:Syne,sans-serif;font-size:0.92rem;font-weight:700;color:#0c1f4a;margin-bottom:2px;">📈 Total Backlog Over Time</div><div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;">Cumulative missing report count per weekly snapshot</div></div>', unsafe_allow_html=True)

        if not kpi_df_view.empty and "missing_count" in kpi_df_view.columns:
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                x=kpi_df_view["week_label"],
                y=kpi_df_view["missing_count"],
                marker=dict(
                    color=kpi_df_view["missing_count"],
                    colorscale=[[0,"#bfdbfe"],[0.5,"#3b82f6"],[1,"#1e3a8a"]],
                    showscale=False,
                ),
                text=kpi_df_view["missing_count"],
                textposition="outside",
                textfont=dict(size=11, color=SLATE),
                opacity=0.92,
            ))
            fig3 = chart_layout(fig3, xlab="Week starting", ylab="Missing patients", height=400)
            fig3.update_xaxes(type="category")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No backlog trend data available yet.")

        st.markdown('<p style="font-size:0.75rem;color:#94a3b8;font-style:italic;margin-top:4px;">Backlog shows total patients missing biopsy reports each week.</p>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div style="background:#ffffff;border-radius:20px;padding:16px 20px 8px 20px;border:1px solid rgba(203,213,225,0.55);box-shadow:0 4px 20px rgba(30,58,138,0.06);margin-bottom:4px;"><div style="font-family:Syne,sans-serif;font-size:0.92rem;font-weight:700;color:#0c1f4a;margin-bottom:2px;">🏥 Top 10 Hospitals by Backlog</div><div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;">Hospitals with the most outstanding missing biopsy reports</div></div>', unsafe_allow_html=True)

        if "hospital_name" in filtered.columns:
            hospital_missing = (
                filtered.groupby("hospital_name")["patient_id"]
                .nunique()
                .reset_index(name="missing_count")
                .sort_values("missing_count", ascending=False)
            )
            top10 = hospital_missing.head(10)
        else:
            top10 = pd.DataFrame(columns=["hospital_name","missing_count"])

        if not top10.empty:
            fig4 = go.Figure(go.Bar(
                x=top10["missing_count"],
                y=top10["hospital_name"],
                orientation="h",
                text=top10["missing_count"],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(size=12, family="DM Sans"),
                marker=dict(
                    color=top10["missing_count"],
                    colorscale=[[0,"#fce7f3"],[0.5,"#ec4899"],[1,"#9d174d"]],
                    showscale=False,
                ),
                opacity=0.90,
            ))
            fig4 = chart_layout(fig4, xlab="Missing patients", height=400)
            fig4.update_layout(yaxis=dict(categoryorder="total ascending"), margin=dict(l=160, r=50))
            fig4.update_yaxes(showgrid=False)
            fig4.update_xaxes(showgrid=True, gridcolor=GRID)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No hospital backlog data available for the selected filters.")

        st.markdown('<p style="font-size:0.75rem;color:#94a3b8;font-style:italic;margin-top:4px;">Hospital ranking reflects the current filtered snapshot.</p>', unsafe_allow_html=True)

    # =========================================================================
    # PATIENT TABLE
    # =========================================================================
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:0.62rem;font-weight:700;letter-spacing:0.20em;text-transform:uppercase;color:#6b7fad;margin-bottom:14px;margin-top:22px;display:flex;align-items:center;gap:10px;">Patient Records <span style="flex:1;height:1px;background:linear-gradient(to right,#cbd5e1,transparent);display:inline-block;"></span></div>', unsafe_allow_html=True)

    with st.expander("📋  Show filtered patient list", expanded=False):
        show_cols = [c for c in [
            "patient_id", "age", "age_group",
            "diagnosed_date_only", "recruited_date_only", "hospital_name",
        ] if c in filtered.columns]

        table_df = (
            filtered[show_cols]
            .sort_values("recruited_date_only", ascending=False)
            .reset_index(drop=True)
        )

        st.dataframe(
            table_df,
            use_container_width=True,
            height=340,
        )