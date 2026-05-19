
import streamlit as st
import os
import sys
import importlib

# Add both tool folders to path
sys.path.append(os.path.join(os.path.dirname(__file__), "tracker"))
sys.path.append(os.path.join(os.path.dirname(__file__), "rate_calculator"))

st.set_page_config(page_title="EMC Facility Toolkit", layout="wide", page_icon="🔬")

st.sidebar.title("🔬 EMC Toolkit")
app_mode = st.sidebar.selectbox("Choose a Tool:", ["🏠 Welcome", "🔭 Publication Tracker", "💰 Rate Calculator"])

if app_mode == "🏠 Welcome":
    st.title("Welcome to the EMC Facility Toolkit")
    st.write("---")
    c1, c2 = st.columns(2)
    with c1:
        st.info("### 🔭 Publication Tracker")
        st.write("Automate Google Scholar scans and manage PI citations.")
    with c2:
        st.success("### 💰 Rate Calculator")
        st.write("Generate university-compliant hourly rates with perfect Excel sync.")

elif app_mode == "🔭 Publication Tracker":
    import app as tracker
    importlib.reload(tracker)
    tracker.main_logic() if hasattr(tracker, 'main_logic') else None

elif app_mode == "💰 Rate Calculator":
    import rate_app as calculator
    importlib.reload(calculator)
    calculator.main_logic() if hasattr(calculator, 'main_logic') else None
