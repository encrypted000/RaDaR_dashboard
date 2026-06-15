import uuid
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

MODULE  = "children"
METRICS = ["height", "weight", "acr", "pcr", "diastolic_bp", "systolic_bp", "creatinine", "egfr"]
M_LABELS = {
    "height":       "Height",
    "weight":       "Weight",
    "acr":          "ACR",
    "pcr":          "PCR",
    "diastolic_bp": "Diastolic BP",
    "systolic_bp":  "Systolic BP",
    "creatinine":   "Creatinine",
    "egfr":         "eGFR (Schwartz)",
}

NAVY   = "#0c1f4a"
BLUE   = "#2563eb"
PINK   = "#db2777"
TEAL   = "#0d9488"
AMBER  = "#d97706"
SLATE  = "#475569"
GRID   = "#e2e8f0"


# =============================================================================
# DATA HELPERS
# =============================================================================

def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@st.cache_data(ttl=300)
def load_latest_snapshot() -> pd.DataFrame:
    raw_dir = project_root() / "outputs" / MODULE / "raw"
    files = sorted(
        raw_dir.glob("children_completeness_*.csv"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return pd.DataFrame()
    df = pd.read_csv(files[0], dtype={"patient_id": "string"})
    df["obs_year"] = pd.to_numeric(df["obs_year"], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_kpis() -> pd.DataFrame:
    path = project_root() / "outputs" / MODULE / "kpis" / "weekly_kpis.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=300)
def load_biopsy_snapshot() -> pd.DataFrame:
    raw_dir = project_root() / "outputs" / "biopsy" / "raw"
    files = sorted(raw_dir.glob("missing_biopsy_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[0], dtype={"patient_id": "string"})


@st.cache_data(ttl=300)
def load_genetics_snapshot() -> pd.DataFrame:
    raw_dir = project_root() / "outputs" / "genetics" / "raw"
    files = sorted(raw_dir.glob("missing_genetics_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[0], dtype={"patient_id": "string"})


@st.cache_data(ttl=300)
def load_diagnoses_snapshot() -> pd.DataFrame:
    raw_dir = project_root() / "outputs" / "diagnoses" / "raw"
    files = sorted(raw_dir.glob("missing_diagnoses_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[0], dtype={"patient_id": "string"})


from lib.db import get_live_conn as _live_conn


def fetch_patient_values(patient_id: str) -> pd.DataFrame:
    cache_key = f"_pat_vals_{patient_id}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    from lib.queries import SQL_PATIENT_VALUES
    try:
        conn, _ = _live_conn()
        df = pd.read_sql(SQL_PATIENT_VALUES, conn, params={"patient_id": int(patient_id)})

        from lib.utils import schwartz_egfr
        df["obs_year"] = pd.to_numeric(df["obs_year"], errors="coerce").astype("Int64")
        df["egfr"]     = schwartz_egfr(df["height"], df["creatinine"])
        st.session_state[cache_key] = df
        return df
    except Exception as e:
        st.session_state[cache_key] = pd.DataFrame({"_error": [str(e)]})
        return st.session_state[cache_key]


def metric_pct(df: pd.DataFrame, col: str) -> float:
    eligible = df[col].dropna()
    if eligible.empty:
        return 0.0
    return round(float(eligible.sum()) / len(eligible) * 100, 1)


# =============================================================================
# UI COMPONENTS
# =============================================================================

def section_label(text: str):
    st.markdown(
        f'<div style="font-family:Syne,sans-serif;font-size:0.62rem;font-weight:700;'
        f'letter-spacing:0.20em;text-transform:uppercase;color:#6b7fad;margin-bottom:14px;'
        f'margin-top:6px;display:flex;align-items:center;gap:10px;">'
        f'{text} <span style="flex:1;height:1px;background:linear-gradient(to right,#cbd5e1,transparent);'
        f'display:inline-block;"></span></div>',
        unsafe_allow_html=True,
    )


def chart_wrap(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div style="background:#ffffff;border-radius:20px;padding:16px 20px 8px 20px;'
        f'border:1px solid rgba(203,213,225,0.55);box-shadow:0 4px 20px rgba(30,58,138,0.06);'
        f'margin-bottom:4px;">'
        f'<div style="font-family:Syne,sans-serif;font-size:0.92rem;font-weight:700;'
        f'color:#0c1f4a;margin-bottom:2px;">{title}</div>'
        f'<div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;">{subtitle}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value, color_cls: str, icon: str, note: str = None):
    accent_map = {
        "c-blue":   "linear-gradient(90deg,#2563eb,#60a5fa)",
        "c-green":  "linear-gradient(90deg,#16a34a,#4ade80)",
        "c-pink":   "linear-gradient(90deg,#be185d,#f472b6)",
        "c-violet": "linear-gradient(90deg,#7c3aed,#a78bfa)",
        "c-teal":   "linear-gradient(90deg,#0d9488,#2dd4bf)",
        "c-amber":  "linear-gradient(90deg,#d97706,#fbbf24)",
    }
    bar      = accent_map.get(color_cls, accent_map["c-blue"])
    cid      = f"kpi-{uuid.uuid4().hex[:8]}"
    note_html = (
        f'<div style="font-size:0.70rem;color:#94a3b8;margin-top:5px;font-style:italic;">{note}</div>'
        if note else ""
    )
    st.markdown(
        f"""
        <style>
        #{cid} {{
            background:#ffffff; border-radius:18px; padding:18px 18px 14px 18px;
            border:1px solid rgba(203,213,225,0.55);
            box-shadow:0 4px 20px rgba(30,58,138,0.06);
            position:relative; overflow:hidden; height:100%;
            transition:transform 0.18s ease, box-shadow 0.18s ease;
        }}
        #{cid}:hover {{ transform:translateY(-3px); box-shadow:0 12px 36px rgba(30,58,138,0.13); }}
        </style>
        <div id="{cid}">
            <div style="position:absolute;top:0;left:0;right:0;height:3px;
                        border-radius:18px 18px 0 0;background:{bar};"></div>
            <div style="font-size:1.35rem;margin-bottom:8px;">{icon}</div>
            <div style="font-size:0.72rem;font-weight:600;color:#64748b;letter-spacing:0.06em;
                        text-transform:uppercase;margin-bottom:5px;
                        font-family:'IBM Plex Sans',sans-serif;">{label}</div>
            <div style="font-family:'IBM Plex Sans',sans-serif;font-size:2.0rem;font-weight:700;
                        color:#0c1f4a;line-height:1;letter-spacing:-0.01em;">{value}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def bar_chart_horizontal(labels, values, height=320, x_label=""):
    colors = [
        "#ef4444" if v < 50 else ("#f59e0b" if v < 75 else "#10b981")
        for v in values
    ]
    # Text color matches bar color when outside so it stays readable
    text_colors = [
        "#ef4444" if v < 50 else ("#f59e0b" if v < 75 else "#10b981")
        for v in values
    ]
    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=11, color=text_colors),
        marker_color=colors,
        opacity=0.88,
    ))
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=55, t=8, b=8),
        plot_bgcolor="#ffffff",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans", color=SLATE, size=12),
        xaxis=dict(range=[0, 118], showgrid=True, gridcolor=GRID, ticksuffix="%", title=x_label),
        yaxis=dict(showgrid=False),
    )
    return fig


# =============================================================================
# PATIENT PROFILE
# =============================================================================

def render_patient_profile(
    pid: str,
    df_all: pd.DataFrame,
    biopsy_df: pd.DataFrame,
    genetics_df: pd.DataFrame,
    diagnoses_df: pd.DataFrame,
) -> None:
    pat_df = df_all[df_all["patient_id"] == pid].copy()
    if pat_df.empty:
        st.warning(f"Patient ID **{pid}** not found in children completeness data.")
        return

    pat_df = pat_df.sort_values("obs_year")
    info   = pat_df.iloc[0]

    hospital = str(info.get("hospital_name",     "—"))
    cohort   = str(info.get("cohort_name",        "—"))
    dx_date  = str(info.get("diagnoses_date",     "—"))
    age_dx   = str(info.get("age_at_diagnoses",   "—"))
    age_now  = str(info.get("current_age",        "—"))
    eligible_mask = pat_df[[m for m in METRICS if m in pat_df.columns]].notna().any(axis=1)
    yr_count = int(eligible_mask.sum())

    metric_cols = [m for m in METRICS if m in pat_df.columns]
    all_pcts = []
    for m in metric_cols:
        eligible = pat_df[m].dropna()
        if not eligible.empty:
            all_pcts.append(float(eligible.sum()) / len(eligible) * 100)
    overall_pct = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else 0.0
    pct_color   = "#ef4444" if overall_pct < 50 else ("#f59e0b" if overall_pct < 75 else "#34d399")

    pid_s         = str(pid)
    miss_biopsy   = (not biopsy_df.empty)   and (pid_s in biopsy_df["patient_id"].astype(str).values)
    miss_genetics = (not genetics_df.empty) and (pid_s in genetics_df["patient_id"].astype(str).values)
    miss_diag     = (not diagnoses_df.empty) and (pid_s in diagnoses_df["patient_id"].astype(str).values)

    def badge(label, missing):
        bg   = "#fca5a5" if missing else "#bbf7d0"
        fg   = "#991b1b" if missing else "#166534"
        icon = "⚠️" if missing else "✅"
        txt  = "Missing" if missing else "Present"
        return (
            f'<span style="display:inline-flex;align-items:center;gap:5px;background:{bg};'
            f'color:{fg};border-radius:999px;padding:4px 13px;font-size:0.73rem;'
            f'font-weight:600;margin-right:6px;">{icon} {label}: {txt}</span>'
        )

    info_items = [
        ("Hospital",    hospital),
        ("Cohort",      cohort),
        ("Diagnosed",   dx_date),
        ("Age at Dx",   age_dx),
        ("Current Age", age_now),
        ("Obs. Years",  yr_count),
    ]
    info_html = "".join(
        f'<div><div style="font-size:0.65rem;color:rgba(186,219,255,0.60);'
        f'text-transform:uppercase;letter-spacing:0.10em;margin-bottom:3px;">{lbl}</div>'
        f'<div style="font-size:0.88rem;color:#fff;font-weight:500;">{val}</div></div>'
        for lbl, val in info_items
    )

    st.markdown(
        f"""
        <div style="background:linear-gradient(118deg,#0c1f4a 0%,#1e3a8a 100%);
                    border-radius:20px;padding:28px 36px;margin-bottom:20px;
                    box-shadow:0 12px 40px rgba(12,31,74,0.20);">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div style="font-size:0.62rem;font-weight:600;letter-spacing:0.16em;
                                text-transform:uppercase;color:rgba(186,219,255,0.60);margin-bottom:8px;">
                        Patient ID
                    </div>
                    <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1.35rem;font-weight:600;
                                color:#fff;letter-spacing:0.01em;margin-bottom:16px;">{pid}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:0.62rem;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;
                                color:rgba(186,219,255,0.60);margin-bottom:6px;">Overall Completeness</div>
                    <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1.8rem;font-weight:700;
                                color:{pct_color};line-height:1;">{overall_pct:.1f}%</div>
                </div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:28px;margin-bottom:18px;">{info_html}</div>
            <div>{badge("Biopsy", miss_biopsy)}{badge("Genetics", miss_genetics)}{badge("Diagnosis", miss_diag)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    z_vals, text_vals, years = [], [], []
    for _, row in pat_df.iterrows():
        row_z, row_t = [], []
        for m in metric_cols:
            v = row[m]
            if pd.isna(v):
                row_z.append(-1); row_t.append("—")
            elif int(v) == 1:
                row_z.append(1);  row_t.append("Yes")
            else:
                row_z.append(0);  row_t.append("No")
        z_vals.append(row_z)
        text_vals.append(row_t)
        years.append(str(int(row["obs_year"])))

    colorscale = [
        [0.0,  "#f1f5f9"], [0.33, "#f1f5f9"],
        [0.34, "#fca5a5"], [0.67, "#fca5a5"],
        [0.68, "#86efac"], [1.0,  "#86efac"],
    ]

    fig_heat = go.Figure(go.Heatmap(
        z=z_vals,
        x=[M_LABELS[m] for m in metric_cols],
        y=years,
        text=text_vals,
        texttemplate="%{text}",
        textfont=dict(size=12, color="#1e293b"),
        colorscale=colorscale,
        zmin=-1, zmax=1,
        showscale=False,
        xgap=2, ygap=2,
        hovertemplate="%{y} · %{x}: %{text}<extra></extra>",
    ))
    fig_heat.update_layout(
        height=max(220, len(years) * 40 + 80),
        margin=dict(l=8, r=8, t=8, b=8),
        plot_bgcolor="#ffffff",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans", color=SLATE, size=12),
        xaxis=dict(side="top", showgrid=False),
        yaxis=dict(showgrid=False, autorange="reversed"),
    )

    colL, colR = st.columns([2, 1], gap="large")
    with colL:
        chart_wrap(
            "📅 Observation Timeline",
            "Green = recorded · Red = missing · Gray = pre-diagnosis (not expected)",
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with colR:
        m_pcts = []
        for m in metric_cols:
            eligible = pat_df[m].dropna()
            pct = round(float(eligible.sum()) / len(eligible) * 100, 1) if not eligible.empty else 0.0
            m_pcts.append(pct)

        chart_wrap("📊 Metric Completeness", "% of eligible years recorded")
        st.plotly_chart(
            bar_chart_horizontal([M_LABELS[m] for m in metric_cols], m_pcts, height=max(220, len(years) * 40 + 80)),
            use_container_width=True,
        )

    dl_df = pat_df[["obs_year"] + metric_cols].copy().sort_values("obs_year")
    dl_df = dl_df.rename(columns={"obs_year": "Year"})
    for m in metric_cols:
        dl_df[m] = dl_df[m].apply(lambda v: "Yes" if v == 1 else ("No" if v == 0 else "—"))
    dl_df = dl_df.rename(columns={m: M_LABELS[m] for m in metric_cols})

    st.download_button(
        label="⬇️  Download patient data as CSV",
        data=dl_df.to_csv(index=False),
        file_name=f"patient_{pid}_completeness.csv",
        mime="text/csv",
    )

    # ── Observation values (live DB query) ───────────────────────────────────
    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)
    chart_wrap(
        "🔬 Recorded Observation Values",
        "Actual measurements fetched live from the database · eGFR computed via Schwartz formula",
    )

    with st.spinner("Connecting to database…"):
        val_df = fetch_patient_values(pid)

    if val_df.empty or "_error" in val_df.columns:
        err = val_df["_error"].iloc[0] if "_error" in val_df.columns else "Unknown error"
        st.warning(f"Could not load observation values — {err}")
    else:
        VAL_COLS = [
            ("obs_year",     "Year",                  ""),
            ("height",       "Height",                "cm"),
            ("weight",       "Weight",                "kg"),
            ("acr",          "ACR",                   "mg/mmol"),
            ("pcr",          "PCR",                   "mg/mmol"),
            ("diastolic_bp", "Diastolic BP",          "mmHg"),
            ("systolic_bp",  "Systolic BP",           "mmHg"),
            ("creatinine",   "Creatinine",            "μmol/L"),
            ("egfr",         "eGFR (Schwartz)",       "mL/min/1.73m²"),
        ]

        header_cells = "".join(
            f'<th style="padding:8px 14px;text-align:left;font-size:0.72rem;font-weight:600;'
            f'color:#64748b;border-bottom:2px solid #e2e8f0;white-space:nowrap;">'
            f'{lbl}<br><span style="font-weight:400;color:#94a3b8;font-size:0.67rem;">{unit}</span></th>'
            for _, lbl, unit in VAL_COLS
        )

        rows_html = ""
        for i, (_, row) in enumerate(val_df.iterrows()):
            bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
            cells = ""
            for col, lbl, unit in VAL_COLS:
                v = row.get(col)
                if col == "obs_year":
                    yr = int(v) if v is not None and not pd.isna(v) else "—"
                    cells += (
                        f'<td style="padding:8px 14px;font-weight:600;color:#0c1f4a;'
                        f'border-bottom:1px solid #f1f5f9;">{yr}</td>'
                    )
                elif pd.isna(v) or v is None:
                    cells += (
                        f'<td style="padding:8px 14px;color:#cbd5e1;'
                        f'border-bottom:1px solid #f1f5f9;">—</td>'
                    )
                else:
                    cells += (
                        f'<td style="padding:8px 14px;color:#1e293b;'
                        f'border-bottom:1px solid #f1f5f9;">{float(v):.1f}</td>'
                    )
            rows_html += f'<tr style="background:{bg};">{cells}</tr>'

        st.markdown(
            f"""
            <div style="overflow-x:auto;border-radius:12px;border:1px solid #e2e8f0;">
            <table style="width:100%;border-collapse:collapse;
                          font-family:'IBM Plex Sans',sans-serif;font-size:0.82rem;">
                <thead style="background:#f8fafc;">
                    <tr>{header_cells}</tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(f"{len(val_df)} year(s) with at least one recorded observation · eGFR = 36.5 × height(cm) ÷ creatinine(μmol/L)")


# =============================================================================
# PAGE
# =============================================================================

def render():

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .block-container {
        padding-top:0.5rem !important;
        padding-left:2rem !important;
        padding-right:2rem !important;
        max-width:1280px;
    }
    .stApp { background:#f0f4fc; }
    div[data-testid="stThumbValue"] { display:none !important; }
    #MainMenu, footer, header { visibility:hidden; }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================================
    # LOAD DATA
    # =========================================================================
    df_all       = load_latest_snapshot()
    kpi_df       = load_kpis()
    biopsy_df    = load_biopsy_snapshot()
    genetics_df  = load_genetics_snapshot()
    diagnoses_df = load_diagnoses_snapshot()

    if df_all.empty:
        st.warning("No children data found. Run: python -m scripts.run_children_backend")
        st.stop()

    df = df_all.copy()

    # =========================================================================
    # SIDEBAR FILTERS
    # =========================================================================
    st.sidebar.markdown(
        '<div style="height:1px;background:#d0d9ee;margin:0 0 10px 0;"></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div style="font-family:IBM Plex Sans,sans-serif;font-size:0.62rem;font-weight:600;'
        'letter-spacing:0.16em;text-transform:uppercase;color:#94a3b8;margin-bottom:8px;">'
        '👶 Children Filters</div>',
        unsafe_allow_html=True,
    )

    hospitals = sorted(df["hospital_name"].dropna().unique().tolist())
    sel_hospitals = st.sidebar.multiselect("🏥 Hospital", hospitals, default=[])
    if sel_hospitals:
        df = df[df["hospital_name"].isin(sel_hospitals)]

    if "cohort_name" in df.columns:
        cohorts = sorted(df["cohort_name"].dropna().unique().tolist())
        sel_cohorts = st.sidebar.multiselect("🧬 Cohort", cohorts, default=[])
        if sel_cohorts:
            df = df[df["cohort_name"].isin(sel_cohorts)]

    if "obs_year" in df.columns and df["obs_year"].notna().any():
        yr_min = int(df["obs_year"].min())
        yr_max = int(df["obs_year"].max())
        if yr_min < yr_max:
            yr_from, yr_to = st.sidebar.slider(
                "📅 Observation year", yr_min, yr_max, (yr_min, yr_max)
            )
            df = df[(df["obs_year"] >= yr_from) & (df["obs_year"] <= yr_to)]
        else:
            st.sidebar.caption(f"Observation year: {yr_min}")

    st.sidebar.markdown(
        '<div style="height:1px;background:#d0d9ee;margin:14px 0 10px 0;"></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div style="font-family:IBM Plex Sans,sans-serif;font-size:0.62rem;font-weight:600;'
        'letter-spacing:0.16em;text-transform:uppercase;color:#94a3b8;margin-bottom:6px;">'
        '🔍 Patient Lookup</div>',
        unsafe_allow_html=True,
    )
    patient_search = st.sidebar.text_input(
        "patient_id_search",
        placeholder="Type patient ID, e.g. 315",
        label_visibility="collapsed",
        key="patient_search_input",
    )
    if patient_search and patient_search.strip():
        pid_s   = patient_search.strip()
        all_ids = df_all["patient_id"].astype(str).tolist()
        if pid_s not in all_ids:
            matches = [p for p in all_ids if pid_s in p]
            if matches:
                preview = ", ".join(matches[:5])
                suffix  = f" (+{len(matches) - 5} more)" if len(matches) > 5 else ""
                st.sidebar.caption(f"Matching: {preview}{suffix}")
            else:
                st.sidebar.caption("No matching patient IDs found.")
        st.sidebar.button(
            "✕  Clear search",
            use_container_width=True,
            on_click=lambda: st.session_state.update({"patient_search_input": ""}),
        )

    if df.empty:
        st.warning("No records for the selected filters.")
        st.stop()

    # =========================================================================
    # DERIVED KPIs
    # =========================================================================
    total_children = df["patient_id"].nunique()
    total_sites    = df["hospital_name"].dropna().nunique()

    metric_pcts = {m: metric_pct(df, m) for m in METRICS if m in df.columns}
    overall_pct = round(sum(metric_pcts.values()) / len(metric_pcts), 1) if metric_pcts else 0.0

    cur_year = pd.Timestamp.now().year
    df_cur   = df[df["obs_year"] == cur_year]
    cur_pcts = {m: metric_pct(df_cur, m) for m in METRICS if m in df_cur.columns}
    cur_overall = round(sum(cur_pcts.values()) / len(cur_pcts), 1) if cur_pcts else 0.0

    # =========================================================================
    # PATIENT MODE BANNER
    # =========================================================================
    if patient_search and patient_search.strip():
        st.markdown(
            f"""
            <div style="background:linear-gradient(90deg,#92400e,#d97706,#f59e0b);
                        border-radius:16px;padding:13px 24px;margin-bottom:16px;
                        display:flex;align-items:center;gap:14px;
                        box-shadow:0 6px 20px rgba(217,119,6,0.30);">
                <span style="font-size:1.5rem;">🔍</span>
                <div style="flex:1;">
                    <div style="font-family:Syne,sans-serif;font-size:0.98rem;font-weight:800;color:#fff;">
                        Patient View Active &mdash; ID: {patient_search.strip()}
                    </div>
                    <div style="font-size:0.75rem;color:rgba(255,255,255,0.80);margin-top:2px;">
                        Patient profile is shown below the overview cards &darr; &nbsp; Use the sidebar to clear.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =========================================================================
    # HERO
    # =========================================================================
    pill = (
        "display:inline-flex;align-items:center;gap:7px;"
        "background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.18);"
        "border-radius:999px;padding:4px 14px;font-size:0.80rem;font-weight:600;color:#fff;"
    )
    pill_lbl = "opacity:0.65;font-size:0.70rem;"

    st.markdown(
        f"""
        <div style="background:linear-gradient(118deg,#0c1f4a 0%,#831843 52%,#be185d 100%);
                    border-radius:24px;padding:34px 40px 30px 40px;margin-bottom:28px;
                    position:relative;overflow:hidden;box-shadow:0 20px 60px rgba(12,31,74,0.32);">
            <div style="display:inline-flex;align-items:center;gap:7px;
                        background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.18);
                        border-radius:999px;padding:4px 14px;font-size:0.70rem;font-weight:600;
                        letter-spacing:0.14em;text-transform:uppercase;color:#fce7f3;margin-bottom:14px;">
                <span style="width:6px;height:6px;border-radius:50%;background:#34d399;display:inline-block;"></span>
                Paediatric &middot; Observation Completeness
            </div>
            <div style="font-family:Syne,sans-serif;font-size:2.05rem;font-weight:800;color:#fff;
                        line-height:1.15;letter-spacing:-0.02em;margin-bottom:8px;">
                👶 Children's Dashboard
            </div>
            <div style="font-size:0.90rem;color:rgba(252,231,243,0.82);max-width:640px;
                        line-height:1.65;font-weight:300;">
                Track observation completeness across all 13 BAPN paediatric sites &mdash;
                height, weight, blood pressure, ACR, PCR, creatinine, and Schwartz eGFR.
            </div>
            <div style="margin-top:20px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.13);
                        display:flex;align-items:center;flex-wrap:wrap;gap:10px;">
                <span style="font-size:0.65rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;
                             color:rgba(252,231,243,0.75);margin-right:4px;">Filtered view &rarr;</span>
                <span style="{pill}"><span style="{pill_lbl}">👶 Children</span>{total_children}</span>
                <span style="{pill}"><span style="{pill_lbl}">🏥 Sites</span>{total_sites}</span>
                <span style="{pill}"><span style="{pill_lbl}">📊 Overall</span>{overall_pct:.1f}%</span>
                <span style="{pill}"><span style="{pill_lbl}">📅 {cur_year}</span>{cur_overall:.1f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================================================================
    # KPI CARDS
    # =========================================================================
    section_label("Overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Paediatric patients",      total_children,          "c-pink",   "👶", note="Currently aged < 18")
    with c2: kpi_card("Active BAPN sites",         total_sites,             "c-blue",   "🏥", note="Sites with enrolled patients")
    with c3: kpi_card("Overall completeness",      f"{overall_pct:.1f}%",   "c-violet", "📊", note="All metrics, all eligible years")
    with c4: kpi_card(f"{cur_year} completeness",  f"{cur_overall:.1f}%",   "c-teal",   "📅", note="Current year only")

    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)

    # =========================================================================
    # PATIENT PROFILE (shown when a patient ID is searched)
    # =========================================================================
    if patient_search and patient_search.strip():
        st.markdown(
            """
            <div style="background:linear-gradient(90deg,#78350f,#b45309,#d97706);
                        border-radius:14px;padding:12px 24px;margin-bottom:18px;
                        box-shadow:0 6px 20px rgba(180,83,9,0.25);">
                <div style="font-family:'IBM Plex Sans',sans-serif;font-size:0.80rem;
                            font-weight:600;color:rgba(255,255,255,0.92);letter-spacing:0.04em;">
                    🔍 &nbsp; Patient Profile
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_patient_profile(
            patient_search.strip(),
            df_all,
            biopsy_df,
            genetics_df,
            diagnoses_df,
        )
        st.markdown(
            '<div style="height:2px;background:linear-gradient(to right,#f59e0b,transparent);'
            'border-radius:99px;margin:24px 0 28px 0;"></div>',
            unsafe_allow_html=True,
        )

    # =========================================================================
    # METRIC COMPLETENESS — ALL-TIME vs CURRENT YEAR
    # =========================================================================
    section_label("Observation Completeness by Metric")
    colA, colB = st.columns(2, gap="large")

    with colA:
        chart_wrap("📊 All-Time Completeness per Metric",
                   "% of expected year-slots with an observation recorded")
        m_labels = [M_LABELS.get(m, m) for m in METRICS if m in metric_pcts]
        m_values = [metric_pcts[m] for m in METRICS if m in metric_pcts]
        st.plotly_chart(
            bar_chart_horizontal(m_labels, m_values),
            use_container_width=True,
        )

    with colB:
        chart_wrap(f"📅 {cur_year} Completeness per Metric",
                   "Current year only — what has been recorded so far this year")
        c_labels = [M_LABELS.get(m, m) for m in METRICS if m in cur_pcts]
        c_values = [cur_pcts[m] for m in METRICS if m in cur_pcts]
        st.plotly_chart(
            bar_chart_horizontal(c_labels, c_values),
            use_container_width=True,
        )

    st.markdown(
        '<div style="background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:0 10px 10px 0;'
        'padding:10px 14px;font-size:0.78rem;color:#0369a1;line-height:1.55;margin-top:4px;">'
        '<strong>Green</strong> &ge;75% &nbsp;|&nbsp; <strong>Amber</strong> 50–74% &nbsp;|&nbsp; '
        '<strong>Red</strong> &lt;50% &nbsp;&mdash;&nbsp; '
        'Only years on or after each patient\'s diagnosis date count as eligible.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)

    # =========================================================================
    # PER-SITE COMPLETENESS + HEATMAP
    # =========================================================================
    section_label("Per-Site Completeness")
    colC, colD = st.columns(2, gap="large")

    with colC:
        chart_wrap("🏥 Overall Completeness by Site",
                   "Average completeness across all metrics per hospital")

        site_rows = []
        for site, sdf in df.groupby("hospital_name"):
            pcts = [metric_pct(sdf, m) for m in METRICS if m in sdf.columns]
            avg  = round(sum(pcts) / len(pcts), 1) if pcts else 0.0
            site_rows.append({
                "Hospital":     site,
                "Completeness": avg,
                "Patients":     int(sdf["patient_id"].nunique()),
            })

        site_df = pd.DataFrame(site_rows).sort_values("Completeness", ascending=True)

        if not site_df.empty:
            site_colors = [
                "#ef4444" if v < 50 else ("#f59e0b" if v < 75 else "#10b981")
                for v in site_df["Completeness"]
            ]
            site_text_colors = [
                "#ef4444" if v < 50 else ("#f59e0b" if v < 75 else "#10b981")
                for v in site_df["Completeness"]
            ]
            fig_site = go.Figure(go.Bar(
                x=site_df["Completeness"],
                y=site_df["Hospital"],
                orientation="h",
                text=[f"{v:.1f}%" for v in site_df["Completeness"]],
                textposition="outside",
                cliponaxis=False,
                textfont=dict(size=11, color=site_text_colors),
                marker_color=site_colors,
                opacity=0.88,
                customdata=site_df["Patients"],
                hovertemplate="%{y}<br>Completeness: %{x:.1f}%<br>Patients: %{customdata}<extra></extra>",
            ))
            fig_site.update_layout(
                height=max(300, len(site_df) * 40 + 60),
                margin=dict(l=8, r=60, t=8, b=8),
                plot_bgcolor="#ffffff",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="IBM Plex Sans", color=SLATE, size=12),
                xaxis=dict(range=[0, 118], showgrid=True, gridcolor=GRID, ticksuffix="%"),
                yaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig_site, use_container_width=True)
        else:
            st.info("No site data available.")

    with colD:
        chart_wrap("🗺️ Completeness Heatmap",
                   "Each cell shows % of eligible years with an observation recorded")

        pivot_rows = []
        for site, sdf in df.groupby("hospital_name"):
            row = {"Hospital": site}
            for m in METRICS:
                if m in sdf.columns:
                    row[M_LABELS[m]] = metric_pct(sdf, m)
            pivot_rows.append(row)

        if pivot_rows:
            pivot_df  = pd.DataFrame(pivot_rows).set_index("Hospital")
            heat_cols = [M_LABELS[m] for m in METRICS if M_LABELS[m] in pivot_df.columns]
            pivot_df  = pivot_df[heat_cols]

            fig_heat = px.imshow(
                pivot_df,
                color_continuous_scale=[[0, "#fef2f2"], [0.5, "#fbbf24"], [1, "#10b981"]],
                zmin=0,
                zmax=100,
                text_auto=".0f",
                aspect="auto",
            )
            fig_heat.update_layout(
                height=max(300, len(pivot_df) * 36 + 80),
                margin=dict(l=8, r=8, t=8, b=8),
                plot_bgcolor="#ffffff",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="IBM Plex Sans", color=SLATE, size=11),
                coloraxis_showscale=False,
            )
            fig_heat.update_traces(textfont_size=10)
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("No heatmap data available.")

    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)

    # =========================================================================
    # YEAR-OVER-YEAR TREND + COHORT BREAKDOWN
    # =========================================================================
    section_label("Year-over-Year Trend")
    colE, colF = st.columns(2, gap="large")

    with colE:
        chart_wrap("📈 Overall Completeness by Year",
                   "Average across all metrics per observation year")

        if "obs_year" in df.columns:
            year_rows = []
            for yr, ydf in df.groupby("obs_year"):
                pcts = [metric_pct(ydf, m) for m in METRICS if m in ydf.columns]
                avg  = round(sum(pcts) / len(pcts), 1) if pcts else 0.0
                year_rows.append({"Year": int(yr), "Completeness": avg})

            yr_df = pd.DataFrame(year_rows).sort_values("Year")

            if not yr_df.empty:
                fig_yr = go.Figure(go.Scatter(
                    x=yr_df["Year"],
                    y=yr_df["Completeness"],
                    mode="lines+markers",
                    line=dict(color=PINK, width=2.5),
                    marker=dict(color=PINK, size=7),
                    fill="tozeroy",
                    fillcolor="rgba(219,39,119,0.06)",
                    hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
                ))
                fig_yr.update_layout(
                    height=300,
                    margin=dict(l=8, r=8, t=8, b=8),
                    plot_bgcolor="#ffffff",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="IBM Plex Sans", color=SLATE, size=12),
                    xaxis=dict(showgrid=False, linecolor=GRID, tickformat="d"),
                    yaxis=dict(showgrid=True, gridcolor=GRID, range=[0, 105], ticksuffix="%"),
                )
                st.plotly_chart(fig_yr, use_container_width=True)
            else:
                st.info("No year trend data available.")

    with colF:
        chart_wrap("🧬 Completeness by Cohort",
                   "Average completeness across all metrics per disease cohort")

        if "cohort_name" in df.columns:
            cohort_rows = []
            for cohort, cdf in df.groupby("cohort_name"):
                pcts = [metric_pct(cdf, m) for m in METRICS if m in cdf.columns]
                avg  = round(sum(pcts) / len(pcts), 1) if pcts else 0.0
                cohort_rows.append({
                    "Cohort":       cohort,
                    "Completeness": avg,
                    "Patients":     int(cdf["patient_id"].nunique()),
                })

            cohort_df = pd.DataFrame(cohort_rows).sort_values("Completeness", ascending=False)

            if not cohort_df.empty:
                # Truncate long cohort names so y-axis stays readable
                cohort_df["Label"] = cohort_df["Cohort"].apply(
                    lambda s: s if len(s) <= 38 else s[:36] + "…"
                )

                # Gradient: scale from light pink → deep navy based on rank
                n = len(cohort_df)
                gradient = [
                    f"rgba({int(190 - i * (190 - 12) / max(n - 1, 1))},"
                    f"{int(39  - i * (39  - 31) / max(n - 1, 1))},"
                    f"{int(119 - i * (119 - 74) / max(n - 1, 1))},0.85)"
                    for i in range(n)
                ]

                fig_cohort = go.Figure()

                # Reference lines at 50% and 75%
                for ref_x, ref_label, ref_color in [
                    (50, "50%", "rgba(100,116,139,0.35)"),
                    (75, "75%", "rgba(16,185,129,0.45)"),
                ]:
                    fig_cohort.add_vline(
                        x=ref_x,
                        line_width=1.2,
                        line_dash="dot",
                        line_color=ref_color,
                        annotation_text=ref_label,
                        annotation_position="top",
                        annotation_font=dict(size=10, color=ref_color),
                    )

                fig_cohort.add_trace(go.Bar(
                    x=cohort_df["Completeness"],
                    y=cohort_df["Label"],
                    orientation="h",
                    text=[f"{v:.1f}%" for v in cohort_df["Completeness"]],
                    textposition="outside",
                    cliponaxis=False,
                    textfont=dict(size=10, color=SLATE),
                    marker=dict(color=gradient, line=dict(width=0)),
                    customdata=cohort_df[["Cohort", "Patients"]].values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Completeness: %{x:.1f}%<br>"
                        "Patients: %{customdata[1]}<extra></extra>"
                    ),
                ))

                fig_cohort.update_layout(
                    height=max(380, len(cohort_df) * 30 + 60),
                    margin=dict(l=8, r=60, t=24, b=8),
                    plot_bgcolor="#ffffff",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="IBM Plex Sans", color=SLATE, size=11),
                    xaxis=dict(
                        range=[0, 118],
                        showgrid=True,
                        gridcolor=GRID,
                        ticksuffix="%",
                        zeroline=False,
                    ),
                    yaxis=dict(showgrid=False, autorange="reversed"),
                    bargap=0.3,
                )
                st.plotly_chart(fig_cohort, use_container_width=True)
            else:
                st.info("No cohort data available.")
        else:
            st.info("No cohort column in snapshot.")

    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)

    # =========================================================================
    # PATIENT RECORDS TABLE
    # =========================================================================
    section_label("Patient Records")

    with st.expander("📋 Show patient completeness table", expanded=False):
        show_cols = (
            ["patient_id", "hospital_name", "cohort_name", "current_age", "obs_year"]
            + [m for m in METRICS if m in df.columns]
        )
        table_df = (
            df[[c for c in show_cols if c in df.columns]]
            .sort_values(["patient_id", "obs_year"])
            .reset_index(drop=True)
        )

        display_df = table_df.copy()
        for m in METRICS:
            if m in display_df.columns:
                display_df[m] = display_df[m].apply(
                    lambda v: "Yes" if v == 1 else ("No" if v == 0 else "—")
                )

        rename_map = {
            "patient_id":   "Patient ID",
            "hospital_name": "Hospital",
            "cohort_name":  "Cohort",
            "current_age":  "Age",
            "obs_year":     "Year",
        }
        rename_map.update({m: M_LABELS.get(m, m) for m in METRICS})
        display_df = display_df.rename(columns=rename_map)

        st.dataframe(display_df, use_container_width=True, height=400)
        st.caption(
            f"{len(table_df):,} rows · Yes = recorded · No = missing · — = pre-diagnosis (not expected)"
        )
