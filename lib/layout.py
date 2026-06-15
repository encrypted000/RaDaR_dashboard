import streamlit as st
from pathlib import Path

def render_sidebar_logo():
    logo_path = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=180)
    st.sidebar.markdown("---")
