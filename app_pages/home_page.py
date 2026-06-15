from pathlib import Path
import pandas as pd
import streamlit as st


MODULE = "home"


def render():
    # =========================
    # CSS
    # =========================
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

    .block-container {
        padding-top: 0.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1200px;
    }

    .stApp { background: #f0f4fc; }

    .hero-wrap {
        background: linear-gradient(120deg, #0f2557 0%, #1a3a8f 55%, #2563eb 100%);
        border-radius: 24px;
        padding: 36px 40px 32px 40px;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 60px rgba(15,37,87,0.30);
    }
    .hero-wrap::before {
        content: ""; position: absolute;
        top: -60px; right: -60px;
        width: 340px; height: 340px; border-radius: 50%;
        background: rgba(255,255,255,0.045);
    }
    .hero-wrap::after {
        content: ""; position: absolute;
        bottom: -80px; left: 30%;
        width: 280px; height: 280px; border-radius: 50%;
        background: rgba(99,179,255,0.07);
    }
    .hero-eyebrow {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.72rem; font-weight: 500;
        letter-spacing: 0.18em; text-transform: uppercase;
        color: rgba(147,197,253,0.9); margin-bottom: 10px;
    }
    .hero-title {
        font-family: 'Syne', sans-serif;
        font-size: 2.1rem; font-weight: 800; color: #ffffff;
        line-height: 1.15; margin-bottom: 10px; letter-spacing: -0.02em;
    }
    .hero-sub {
        font-size: 0.92rem; color: rgba(186,219,255,0.85);
        max-width: 620px; line-height: 1.6; font-weight: 300;
    }
    .hero-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18);
        border-radius: 999px; padding: 5px 14px;
        font-size: 0.75rem; color: #bfdbfe; font-weight: 500;
        margin-top: 18px; backdrop-filter: blur(6px);
    }
    .hero-badge-dot {
        width: 7px; height: 7px; background: #34d399;
        border-radius: 50%; box-shadow: 0 0 8px #34d399;
        animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.6; transform: scale(1.3); }
    }

    .section-label {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.65rem; font-weight: 700;
        letter-spacing: 0.20em; text-transform: uppercase;
        color: #6b7fad; margin-bottom: 14px;
        display: flex; align-items: center; gap: 10px;
    }
    .section-label::after {
        content: ""; flex: 1; height: 1px;
        background: linear-gradient(to right, #cbd5e1, transparent);
    }

    .kpi-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px; margin-bottom: 28px;
    }
    @media (max-width: 900px) { .kpi-row { grid-template-columns: repeat(2,1fr); } }
    @media (max-width: 520px) { .kpi-row { grid-template-columns: 1fr; } }

    .kpi-card {
        background: #ffffff; border-radius: 18px;
        padding: 20px 20px 18px 20px;
        border: 1px solid rgba(203,213,225,0.6);
        box-shadow: 0 4px 24px rgba(30,58,138,0.06);
        position: relative; overflow: hidden;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 12px 36px rgba(30,58,138,0.12); }
    .kpi-card::before {
        content: ""; position: absolute;
        top: 0; left: 0; right: 0; height: 3px; border-radius: 18px 18px 0 0;
    }
    .kpi-card.blue::before   { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
    .kpi-card.sky::before    { background: linear-gradient(90deg, #0ea5e9, #38bdf8); }
    .kpi-card.pink::before   { background: linear-gradient(90deg, #ec4899, #f472b6); }
    .kpi-card.violet::before { background: linear-gradient(90deg, #7c3aed, #a78bfa); }

    .kpi-icon  { font-size: 1.5rem; margin-bottom: 10px; }
    .kpi-label {
        font-size: 0.75rem; font-weight: 600; color: #64748b;
        letter-spacing: 0.06em; margin-bottom: 6px; text-transform: uppercase;
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .kpi-value {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 2.2rem; font-weight: 700; color: #0f2557;
        line-height: 1; letter-spacing: -0.01em;
    }
    .kpi-sub { font-size: 0.72rem; color: #94a3b8; margin-top: 6px; font-style: italic; }

    .status-pill {
        display: inline-flex; align-items: center; gap: 5px;
        border-radius: 999px; padding: 3px 10px;
        font-size: 0.72rem; font-weight: 600;
    }
    .status-good   { background:#dcfce7; color:#15803d; }
    .status-medium { background:#fef9c3; color:#a16207; }
    .status-low    { background:#fee2e2; color:#b91c1c; }

    /* Module completeness cards */
    .mod-card {
        background: #ffffff; border-radius: 20px;
        border: 1px solid rgba(203,213,225,0.55);
        box-shadow: 0 4px 24px rgba(30,58,138,0.06);
        overflow: hidden;
        transition: transform 0.22s ease, box-shadow 0.22s ease;
    }
    .mod-card:hover { transform: translateY(-5px); box-shadow: 0 18px 52px rgba(30,58,138,0.14); }

    .mod-card-top {
        padding: 22px 26px 20px 26px;
        display: flex; align-items: center; gap: 14px;
    }
    .mod-top-icon { font-size: 2.2rem; line-height: 1; flex-shrink: 0; }
    .mod-card-title {
        font-family: 'Syne', sans-serif;
        font-size: 1.1rem; font-weight: 700; color: #ffffff;
        margin-bottom: 3px; letter-spacing: -0.01em;
    }
    .mod-card-sub { font-size: 0.73rem; color: rgba(255,255,255,0.7); font-weight: 300; }

    .mod-card-body {
        padding: 26px 28px 22px;
        display: flex; flex-direction: column; align-items: center; gap: 18px;
    }
    .mod-ring-wrap { display: flex; justify-content: center; }
    .mod-ring {
        width: 156px; height: 156px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        position: relative;
    }
    .mod-ring-inner {
        width: 116px; height: 116px; border-radius: 50%;
        background: #ffffff;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        box-shadow: 0 2px 14px rgba(0,0,0,0.07);
        position: relative; z-index: 1;
    }
    .mod-pct-num {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 2.1rem; font-weight: 700; color: #0f2557; line-height: 1;
    }
    .mod-pct-sym { font-size: 1.05rem; font-weight: 500; color: #64748b; vertical-align: super; }
    .mod-pct-label {
        font-size: 0.60rem; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 0.12em; margin-top: 4px;
    }
    .mod-divider {
        width: 100%; display: flex; align-items: center; gap: 10px;
    }
    .mod-divider-line { flex: 1; height: 1px; background: #f1f5f9; }
    .mod-divider-text { font-size: 0.64rem; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.1em; white-space: nowrap; }

    .mod-bar-track {
        width: 100%; height: 9px;
        background: #f1f5f9; border-radius: 99px; overflow: hidden;
    }
    .mod-bar-fill { height: 100%; border-radius: 99px; }

    .mod-footer {
        width: 100%; display: flex;
        align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: 6px;
    }
    .mod-footer-hint { font-size: 0.68rem; color: #94a3b8; font-style: italic; }

    .mod-stats-row {
        width: 100%; display: grid; grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .mod-stat-box {
        background: #f8fafc; border-radius: 12px;
        padding: 10px 14px; border: 1px solid #f1f5f9;
        text-align: center;
    }
    .mod-stat-val {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 1.3rem; font-weight: 700; color: #0f2557; line-height: 1;
    }
    .mod-stat-lbl { font-size: 0.64rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 3px; }

    /* Cohort table */
    .cohort-wrap {
        background: #ffffff; border-radius: 20px;
        border: 1px solid rgba(203,213,225,0.55);
        box-shadow: 0 4px 20px rgba(30,58,138,0.06);
        overflow: hidden; margin-bottom: 24px; margin-top: 8px;
    }
    .cohort-header {
        padding: 18px 22px 14px 22px;
        border-bottom: 1px solid #f1f5f9;
        display: flex; align-items: center; justify-content: space-between;
    }
    .cohort-title {
        font-family: 'Syne', sans-serif; font-size: 0.95rem;
        font-weight: 700; color: #0c1f4a;
    }
    .cohort-sub { font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }
    .cohort-legend { display: flex; gap: 14px; align-items: center; }
    .cohort-legend-item {
        display: inline-flex; align-items: center;
        gap: 5px; font-size: 0.72rem; color: #64748b;
    }
    .cohort-dot {
        width: 10px; height: 10px;
        border-radius: 50%; display: inline-block;
    }
    table.cohort-table { width: 100%; border-collapse: collapse; }
    table.cohort-table thead tr { background: #f8fafc; }
    table.cohort-table thead th {
        padding: 10px 18px;
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.68rem; font-weight: 600; color: #64748b;
        letter-spacing: 0.08em; text-transform: uppercase;
        border-bottom: 1px solid #e2e8f0;
    }
    table.cohort-table thead th:first-child { text-align: left; }
    table.cohort-table thead th:not(:first-child) { text-align: right; }
    table.cohort-table tbody tr:nth-child(even) { background: #f8fafc; }
    table.cohort-table tbody tr:nth-child(odd)  { background: #ffffff; }
    table.cohort-table tbody tr.total-row {
        background: #eff6ff !important;
        border-top: 2px solid #dbeafe;
    }
    table.cohort-table tbody td {
        padding: 11px 18px;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.85rem;
    }
    table.cohort-table tbody td:first-child { color: #1e293b; }
    table.cohort-table tbody td:not(:first-child) { text-align: right; }
    table.cohort-table tbody tr.total-row td {
        font-weight: 700; color: #0c1f4a;
    }
    .adult-val { color: #2563eb; font-weight: 600; }
    .child-val { color: #db2777; font-weight: 600; }
    .total-val { color: #0c1f4a; font-weight: 700; }
    .pct-tag {
        font-size: 0.68rem; color: #94a3b8;
        font-weight: 400; margin-left: 4px;
    }
    .mini-bar-wrap {
        display: flex; height: 3px; border-radius: 99px;
        overflow: hidden; margin-top: 4px; width: 64px; margin-left: auto;
    }

    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

    # =========================
    # Helpers
    # =========================
    def project_root() -> Path:
        return Path(__file__).resolve().parents[1]

    def home_output_dir() -> Path:
        return project_root() / "outputs" / "home"

    @st.cache_data(ttl=60)
    def load_registry_overview() -> pd.DataFrame:
        path = home_output_dir() / "registry_overview.csv"
        if not path.exists():
            return pd.DataFrame(columns=["total_patients","male_patients","female_patients","total_cohorts"])
        return pd.read_csv(path)

    @st.cache_data(ttl=60)
    def load_cohort_structure() -> pd.DataFrame:
        path = home_output_dir() / "cohort_structure.csv"
        if not path.exists():
            return pd.DataFrame(columns=["id","name","total_patients","child_count","adult_count"])
        return pd.read_csv(path)

    def latest_module_completeness(module: str) -> float | None:
        path = project_root() / "outputs" / module / "kpis" / "weekly_kpis.csv"
        if not path.exists():
            return None
        df = pd.read_csv(path)
        if df.empty or "completeness_percent" not in df.columns:
            return None
        if "week_monday" in df.columns:
            df["week_monday"] = pd.to_datetime(df["week_monday"], errors="coerce")
            df = df.sort_values("week_monday")
        value = df.iloc[-1]["completeness_percent"]
        return None if pd.isna(value) else float(value)

    def fmt_num(value):
        if value == "—" or (isinstance(value, float) and pd.isna(value)):
            return "—"
        return f"{int(value):,}"

    def status_pill(value):
        if value is None:
            return "<span class='status-pill status-low'>● No data</span>"
        if value >= 75:
            return f"<span class='status-pill status-good'>● Good — {value:.1f}%</span>"
        elif value >= 50:
            return f"<span class='status-pill status-medium'>● Needs attention — {value:.1f}%</span>"
        else:
            return f"<span class='status-pill status-low'>● Low — {value:.1f}%</span>"

    # =========================
    # Load data
    # =========================
    overview_df = load_registry_overview()
    total_patients = male_patients = female_patients = total_cohorts = "—"
    unknown_sex = 0

    if not overview_df.empty:
        row = overview_df.iloc[0]
        total_patients  = int(row["total_patients"])  if pd.notna(row.get("total_patients"))  else "—"
        male_patients   = int(row["male_patients"])   if pd.notna(row.get("male_patients"))   else "—"
        female_patients = int(row["female_patients"]) if pd.notna(row.get("female_patients")) else "—"
        total_cohorts   = int(row["total_cohorts"])   if pd.notna(row.get("total_cohorts"))   else "—"
        unknown_sex     = int(row["unknown_sex"])     if pd.notna(row.get("unknown_sex"))     else 0
    else:
        st.warning("Home summary not found. Run: python -m scripts.run_home_backend")

    # =========================
    # Hero
    # =========================
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-eyebrow">🏥 UKKA · National Registry Dashboard</div>
        <div class="hero-title">RaDaR Registry Overview</div>
        <div class="hero-sub">
            Real-time overview of registry size, demographic breakdown, cohort structure,
            and data completeness across all clinical modules.
        </div>
        <div class="hero-badge">
            <span class="hero-badge-dot"></span>
            Live · Weekly KPI Snapshot
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =========================
    # KPI Cards
    # =========================
    st.markdown('<div class="section-label">Programme Overview</div>', unsafe_allow_html=True)

    _sex_note = f" · {fmt_num(unknown_sex)} sex not recorded" if unknown_sex else ""
    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-card blue">
            <div class="kpi-icon">🧑‍⚕️</div>
            <div class="kpi-label">Total Patients</div>
            <div class="kpi-value">{fmt_num(total_patients)}</div>
            <div class="kpi-sub">Registered in RaDaR{_sex_note}</div>
        </div>
        <div class="kpi-card sky">
            <div class="kpi-icon">👨</div>
            <div class="kpi-label">Male Patients</div>
            <div class="kpi-value">{fmt_num(male_patients)}</div>
            <div class="kpi-sub">Biological sex at registration (where recorded)</div>
        </div>
        <div class="kpi-card pink">
            <div class="kpi-icon">👩</div>
            <div class="kpi-label">Female Patients</div>
            <div class="kpi-value">{fmt_num(female_patients)}</div>
            <div class="kpi-sub">Biological sex at registration (where recorded)</div>
        </div>
        <div class="kpi-card violet">
            <div class="kpi-icon">🧬</div>
            <div class="kpi-label">Cohort Groups</div>
            <div class="kpi-value">{fmt_num(total_cohorts)}</div>
            <div class="kpi-sub">Active disease cohorts</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =========================
    # Module completeness card builder
    # =========================
    def completeness_card(title, icon, value, accent, accent_light, top_gradient):
        v = value if value is not None else 0
        deg = v * 3.6
        remaining_color = "#f1f5f9"

        if value is None:
            pill = "<span class='status-pill status-low'>● No data</span>"
        elif v >= 75:
            pill = f"<span class='status-pill status-good'>● Good &mdash; {v:.1f}%</span>"
        elif v >= 50:
            pill = f"<span class='status-pill status-medium'>● Needs attention &mdash; {v:.1f}%</span>"
        else:
            pill = f"<span class='status-pill status-low'>● Low &mdash; {v:.1f}%</span>"

        missing = f"{max(0, 100 - v):.1f}"

        return f"""
        <div class="mod-card">
            <div class="mod-card-top" style="background:{top_gradient};">
                <div class="mod-top-icon">{icon}</div>
                <div>
                    <div class="mod-card-title">{title}</div>
                    <div class="mod-card-sub">Data completeness &middot; Latest weekly snapshot</div>
                </div>
            </div>
            <div class="mod-card-body">
                <div class="mod-ring-wrap">
                    <div class="mod-ring" style="background: conic-gradient({accent} {deg:.1f}deg, {remaining_color} {deg:.1f}deg);">
                        <div class="mod-ring-inner">
                            <div class="mod-pct-num">{v:.0f}<span class="mod-pct-sym">%</span></div>
                            <div class="mod-pct-label">complete</div>
                        </div>
                    </div>
                </div>
                <div class="mod-stats-row">
                    <div class="mod-stat-box">
                        <div class="mod-stat-val" style="color:{accent};">{v:.1f}%</div>
                        <div class="mod-stat-lbl">Uploaded</div>
                    </div>
                    <div class="mod-stat-box">
                        <div class="mod-stat-val" style="color:#ef4444;">{missing}%</div>
                        <div class="mod-stat-lbl">Missing</div>
                    </div>
                </div>
                <div class="mod-divider">
                    <div class="mod-divider-line"></div>
                    <div class="mod-divider-text">Progress</div>
                    <div class="mod-divider-line"></div>
                </div>
                <div class="mod-bar-track">
                    <div class="mod-bar-fill" style="width:{v:.1f}%; background:linear-gradient(90deg,{accent},{accent_light});"></div>
                </div>
                <div class="mod-footer">
                    {pill}
                    <span class="mod-footer-hint">Use sidebar to explore &rarr;</span>
                </div>
            </div>
        </div>
        """

    # =========================
    # Module Completeness
    # =========================
    st.markdown('<div class="section-label">Module Completeness</div>', unsafe_allow_html=True)

    biopsy_val   = latest_module_completeness("biopsy")
    genetics_val = latest_module_completeness("genetics")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(completeness_card(
            title="Biopsy Module",
            icon="🔬",
            value=biopsy_val,
            accent="#3b82f6",
            accent_light="#93c5fd",
            top_gradient="linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)",
        ), unsafe_allow_html=True)

    with col2:
        st.markdown(completeness_card(
            title="Genetics Module",
            icon="🧬",
            value=genetics_val,
            accent="#7c3aed",
            accent_light="#c4b5fd",
            top_gradient="linear-gradient(135deg, #4c1d95 0%, #7c3aed 100%)",
        ), unsafe_allow_html=True)

    # =========================
    # Cohort Structure
    # =========================
    st.markdown('<div class="section-label" style="margin-top:24px;">Cohort Structure</div>', unsafe_allow_html=True)

    cohort_df = load_cohort_structure()

    if not cohort_df.empty:
        cohort_table = cohort_df.rename(columns={
            "name": "Cohort",
            "adult_count": "Adult",
            "child_count": "Child",
            "total_patients": "Total",
        })[["Cohort", "Adult", "Child", "Total"]]

        # Build rows — no total row
        rows_html = ""
        for i, row in cohort_table.iterrows():
            adult = int(row['Adult']) if pd.notna(row['Adult']) else 0
            child = int(row['Child']) if pd.notna(row['Child']) else 0
            total = int(row['Total']) if pd.notna(row['Total']) else 0
            def fmt_pct(num, denom):
                if denom == 0: return "—"
                pct = num / denom * 100
                if pct == 0: return "—"
                if pct < 1: return "<1%"
                return f"{round(pct)}%"

            adult_pct = fmt_pct(adult, total)
            child_pct = fmt_pct(child, total)
            bar_a = int(adult / total * 100) if total > 0 else 0
            bar_c = int(child / total * 100) if total > 0 else 0

            mini_bar = f'<div class="mini-bar-wrap"><div style="width:{bar_a}%;background:#3b82f6;"></div><div style="width:{bar_c}%;background:#db2777;"></div></div>'

            rows_html += f"""<tr>
                <td>🧬 {row['Cohort']}</td>
                <td><span class="adult-val">{adult:,}</span><span class="pct-tag">{adult_pct}</span>{mini_bar}</td>
                <td><span class="child-val">{child:,}</span><span class="pct-tag">{child_pct}</span></td>
                <td><span class="total-val">{total:,}</span></td>
            </tr>"""

        st.markdown(f"""
        <div class="cohort-wrap">
            <div class="cohort-header">
                <div>
                    <div class="cohort-title">🧬 Cohort Breakdown</div>
                    <div class="cohort-sub">Patient distribution across disease cohorts</div>
                </div>
                <div class="cohort-legend">
                    <span class="cohort-legend-item"><span class="cohort-dot" style="background:#3b82f6;"></span>Adult</span>
                    <span class="cohort-legend-item"><span class="cohort-dot" style="background:#db2777;"></span>Child</span>
                </div>
            </div>
            <table class="cohort-table">
                <thead>
                    <tr>
                        <th>Cohort</th>
                        <th>Adults</th>
                        <th>Children</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.info("No cohort structure data available. Run: python -m scripts.run_home_backend")