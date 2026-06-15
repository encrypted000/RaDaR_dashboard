import streamlit as st
from lib.layout import render_sidebar_logo

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="RaDaR Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# NATIVE PAGE DEFINITIONS
# =============================================================================
pg = st.navigation(
    [
        st.Page("pages/home.py",             title="Home",                  icon="🏥"),
        st.Page("pages/biopsy.py",           title="Biopsy Tracking",       icon="🔬"),
        st.Page("pages/genetics.py",         title="Genetics Tracking",     icon="🧬"),
        st.Page("pages/diagnoses.py",        title="Diagnoses Tracking",    icon="🩺"),
        st.Page("pages/kidney_failure.py",   title="Kidney Failure Events", icon="🫀"),
        st.Page("pages/children.py",         title="Children Dashboard",    icon="👶"),
        st.Page("pages/children_quality.py", title="Children Data Quality", icon="🔎"),
        st.Page("pages/adult_quality.py",    title="Adult Data Quality",    icon="🏥"),
    ],
    position="hidden",
)

# =============================================================================
# GLOBAL STYLING
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    width: 20rem !important;
    min-width: 20rem !important;
    background: #e4eaf6 !important;
    border-right: 1px solid #d0d9ee !important;
    box-shadow: 2px 0 12px rgba(15, 37, 87, 0.07) !important;
    overflow: hidden !important;
}
section[data-testid="stSidebar"] > div {
    padding: 0 !important;
    overflow-y: auto !important;
    height: 100vh !important;
    background: #e4eaf6 !important;
}

/* ── Collapse arrow ──────────────────────────────────────────────────────── */
[data-testid="collapsedControl"] {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: #e4eaf6 !important;
    border: 1px solid #d0d9ee !important;
    border-left: none !important;
    border-radius: 0 8px 8px 0 !important;
    box-shadow: 2px 0 8px rgba(15, 37, 87, 0.08) !important;
    top: 50% !important;
    color: #64748b !important;
}
[data-testid="collapsedControl"]:hover {
    background: #d4ddf0 !important;
    color: #1e3a8a !important;
}
[data-testid="collapsedControl"] svg {
    color: #64748b !important;
}

/* ── Sidebar image ───────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] [data-testid="stImage"] {
    padding: 20px 20px 0 20px !important;
}

/* ── Sidebar labels ──────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] label {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: #64748b !important;
    letter-spacing: 0.04em !important;
}

/* ── Sidebar dropdowns ───────────────────────────────────────────────────── */
section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div,
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.85rem !important;
}
section[data-testid="stSidebar"] [data-testid="stSlider"] {
    padding: 0 !important;
}

/* ── Nav page links ──────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] [data-testid="stPageLink"] {
    padding: 0 8px !important;
    margin-bottom: 2px !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 400 !important;
    color: #475569 !important;
    padding: 10px 14px !important;
    border-radius: 8px !important;
    display: block !important;
    transition: all 0.15s ease !important;
    border-left: 3px solid transparent !important;
    text-decoration: none !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: #d4ddf0 !important;
    color: #1e3a8a !important;
    border-left: 3px solid #93c5fd !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
    background: #c7d6f0 !important;
    color: #1d4ed8 !important;
    font-weight: 600 !important;
    border-left: 3px solid #2563eb !important;
}

/* ── Sidebar section headings ────────────────────────────────────────────── */
section[data-testid="stSidebar"] h3 {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.80rem !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.10em !important;
    padding: 0 4px !important;
    margin-bottom: 8px !important;
}

/* ── Main content area ───────────────────────────────────────────────────── */
.stApp {
    background: #f0f4fc;
}
.block-container {
    padding-top: 0.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}
[data-testid="stThumbValue"]      { display: none !important; }
.main > div                       { min-height: 0 !important; }
[data-testid="stAppViewContainer"] { min-height: 100vh !important; }
[data-testid="block-container"]    { min-height: 0 !important; }

/* ── Splash screen container ─────────────────────────────────────────────── */
#splash-screen {
    position: fixed;
    inset: 0;
    background: linear-gradient(135deg, #0c1f4a 0%, #1a3a8f 50%, #1d4ed8 100%);
    z-index: 999999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    animation: splashFade 0.6s ease 2.1s forwards;
    pointer-events: none;
    overflow: hidden;
}

/* ── Prevent Plotly resize flash ─────────────────────────────────────────── */
.js-plotly-plot,
.plotly,
.plot-container,
.stPlotlyChart,
.stPlotlyChart * {
    transition: none !important;
    animation: none !important;
}

/* ── Streamlit chrome ────────────────────────────────────────────────────── */
#MainMenu                       { visibility: hidden; }
header[data-testid="stHeader"]  { visibility: hidden; height: 0 !important; }
footer                          { visibility: hidden; }

/* ── Scrollbars ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar             { width: 4px; height: 4px; }
::-webkit-scrollbar-track       { background: transparent; }
::-webkit-scrollbar-thumb       { background: #cbd5e1; border-radius: 99px; }

section[data-testid="stSidebar"] ::-webkit-scrollbar       { width: 3px; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-track  { background: #e4eaf6; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb  { background: #b0bcd4; border-radius: 99px; }

/* ── Animations ──────────────────────────────────────────────────────────── */
@keyframes splashFade {
    0%   { opacity: 1; visibility: visible; }
    100% { opacity: 0; visibility: hidden; }
}
@keyframes orbFloat {
    0%, 100% { transform: translateY(0) scale(1); }
    50%       { transform: translateY(-30px) scale(1.05); }
}
@keyframes iconDrop {
    from { opacity: 0; transform: translateY(-24px) scale(0.82); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes loadBar {
    0%   { width: 0%; }
    60%  { width: 75%; }
    100% { width: 100%; }
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SPLASH  (first load only)
# =============================================================================
if "_splash_shown" not in st.session_state:
    st.session_state["_splash_shown"] = True
    st.markdown("""
    <style>
    /* Hide UI until splash finishes */
    section[data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        animation: showSidebar 0s linear 2.35s forwards;
        visibility: hidden;
    }
    .block-container {
        animation: showMain 0s linear 2.35s forwards;
        visibility: hidden;
    }
    @keyframes showSidebar { to { visibility: visible; } }
    @keyframes showMain    { to { visibility: visible; } }

    /* ── Background orbs ─────────────────────────────────────────────── */
    .s-orb1 {
        position: absolute; top: -80px; right: -80px;
        width: 420px; height: 420px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(99, 179, 255, 0.10) 0%, transparent 70%);
        animation: orbFloat 6s ease-in-out infinite;
        pointer-events: none;
    }
    .s-orb2 {
        position: absolute; bottom: -100px; left: -60px;
        width: 360px; height: 360px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(52, 211, 153, 0.07) 0%, transparent 70%);
        animation: orbFloat 8s ease-in-out 1s infinite reverse;
        pointer-events: none;
    }

    /* ── Icon wrapper ────────────────────────────────────────────────── */
    .s-icon-wrap {
        position: relative;
        display: flex; align-items: center; justify-content: center; gap: 6px;
        width: 140px; height: 100px;
        margin-bottom: 24px;
        animation: iconDrop 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) 0.1s both;
    }
    .s-ring {
        position: absolute; inset: -16px;
        border-radius: 50%;
        border: 1.5px dashed rgba(96, 165, 250, 0.35);
        animation: spinRing 14s linear infinite;
    }
    .s-ring2 {
        position: absolute; inset: -6px;
        border-radius: 50%;
        border: 1px solid rgba(96, 165, 250, 0.12);
    }

    /* ── Kidney shapes ───────────────────────────────────────────────── */
    .s-k1 {
        position: relative;
        width: 44px; height: 64px;
        background: linear-gradient(145deg, #c0392b, #96281b, #7b241c);
        border-radius: 50% 38% 38% 50% / 50% 42% 42% 50%;
        box-shadow: 0 0 22px rgba(150, 40, 27, 0.7);
        transform: rotate(-10deg);
        animation: heartbeat 1.5s ease-in-out infinite;
    }
    .s-k1::before {
        content: "";
        position: absolute; top: 10px; left: 8px;
        width: 12px; height: 20px;
        background: rgba(255, 255, 255, 0.20);
        border-radius: 50%;
        transform: rotate(-15deg);
    }
    .s-k1::after {
        content: "";
        position: absolute; top: 50%; right: -4px;
        width: 10px; height: 18px;
        background: linear-gradient(145deg, #5a0e0e, #7b1a1a);
        border-radius: 0 50% 50% 0;
        transform: translateY(-50%);
    }
    .s-k2 {
        position: relative;
        width: 44px; height: 64px;
        background: linear-gradient(225deg, #c0392b, #96281b, #7b241c);
        border-radius: 38% 50% 50% 38% / 42% 50% 50% 42%;
        box-shadow: 0 0 22px rgba(150, 40, 27, 0.7);
        transform: rotate(10deg);
        animation: heartbeat 1.5s ease-in-out 0.15s infinite;
    }
    .s-k2::before {
        content: "";
        position: absolute; top: 10px; right: 8px;
        width: 12px; height: 20px;
        background: rgba(255, 255, 255, 0.20);
        border-radius: 50%;
        transform: rotate(15deg);
    }
    .s-k2::after {
        content: "";
        position: absolute; top: 50%; left: -4px;
        width: 10px; height: 18px;
        background: linear-gradient(225deg, #5a0e0e, #7b1a1a);
        border-radius: 50% 0 0 50%;
        transform: translateY(-50%);
    }

    /* ── Text ────────────────────────────────────────────────────────── */
    .s-title {
        font-family: 'Syne', sans-serif;
        font-size: 3.2rem; font-weight: 800;
        color: #fff;
        letter-spacing: -0.03em; line-height: 1;
        margin-bottom: 8px;
        animation: fadeUp 0.6s ease 0.4s both;
    }
    .s-sub {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.78rem;
        color: rgba(186, 219, 255, 0.65);
        letter-spacing: 0.18em; text-transform: uppercase;
        animation: fadeUp 0.6s ease 0.55s both;
    }
    .s-divider {
        width: 48px; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(96, 165, 250, 0.45), transparent);
        margin: 18px auto 0;
        animation: fadeUp 0.6s ease 0.65s both;
    }

    /* ── Progress bar ────────────────────────────────────────────────── */
    .s-barwrap {
        width: 180px; height: 2px;
        background: rgba(255, 255, 255, 0.10);
        border-radius: 99px; overflow: hidden;
        margin-top: 18px;
        animation: fadeUp 0.6s ease 0.7s both;
    }
    .s-bar {
        height: 100%; width: 0%;
        background: linear-gradient(90deg, #60a5fa, #34d399);
        border-radius: 99px;
        animation: loadBar 1.8s ease 0.8s forwards;
    }
    .s-tag {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.70rem;
        color: rgba(147, 197, 253, 0.40);
        margin-top: 12px; letter-spacing: 0.08em;
        animation: fadeUp 0.6s ease 0.85s both;
    }

    /* ── Splash animations ───────────────────────────────────────────── */
    @keyframes spinRing {
        to { transform: rotate(360deg); }
    }
    @keyframes heartbeat {
        0%,  100% { transform: scale(1)    rotate(-10deg); }
        14%        { transform: scale(1.09) rotate(-10deg); }
        28%        { transform: scale(1)    rotate(-10deg); }
        42%        { transform: scale(1.06) rotate(-10deg); }
        56%        { transform: scale(1)    rotate(-10deg); }
    }
    </style>

    <div id="splash-screen">
        <div class="s-orb1"></div>
        <div class="s-orb2"></div>
        <div class="s-icon-wrap">
            <div class="s-ring"></div>
            <div class="s-ring2"></div>
            <div class="s-k1"></div>
            <div class="s-k2"></div>
        </div>
        <div class="s-title">RaDaR</div>
        <div class="s-sub">UKKA · Registry Analytics Dashboard</div>
        <div class="s-divider"></div>
        <div class="s-barwrap"><div class="s-bar"></div></div>
        <div class="s-tag">Initialising clinical data...</div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================
with st.sidebar:
    render_sidebar_logo()
    st.markdown(
        '<div style="height:1px;background:#d0d9ee;margin:12px 16px 14px 16px;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="font-family: IBM Plex Sans, sans-serif; font-size: 0.62rem;
                    font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase;
                    color: #94a3b8; padding: 0 18px; margin-bottom: 6px;">
            Navigation
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/home.py",             label="🏥  Home")
    st.page_link("pages/biopsy.py",           label="🔬  Biopsy Tracking")
    st.page_link("pages/genetics.py",         label="🧬  Genetics Tracking")
    st.page_link("pages/diagnoses.py",        label="🩺  Diagnoses Tracking")
    st.page_link("pages/kidney_failure.py",   label="🫀  Kidney Failure Events")
    st.page_link("pages/children.py",         label="👶  Children Dashboard")
    st.page_link("pages/children_quality.py", label="🔎  Children Data Quality")
    st.page_link("pages/adult_quality.py",    label="🏥  Adult Data Quality")

pg.run()
