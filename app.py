from __future__ import annotations

import streamlit as st

from chart_builder import build_comparison_chart, build_single_profile_chart
from example_data import load_example_profiles
from export_utils import profiles_to_csv_zip
from profile_loader import load_uploaded_files
from profile_processing import max_duration, max_temperature, total_readings

st.set_page_config(page_title="Cook Profile Dashboard", page_icon="🌡️", layout="wide")

st.markdown(
    """
<style>
.stApp {background: #08111f; color: #e5edf7;}
[data-testid="stSidebar"] {background: #0b1727;}
.cp-title {font-size: 2rem; font-weight: 700; margin-bottom: 0.1rem;}
.cp-kicker {color: #fb923c; font-size: 0.78rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase;}
.cp-note {color: #94a3b8; font-size: .9rem;}
div[data-testid="stMetric"] {background: #0d1b2d; border: 1px solid #203047; padding: 1rem; border-radius: 14px;}
</style>
""",
    unsafe_allow_html=True,
)

if "profiles" not in st.session_state:
    st.session_state.profiles = load_example_profiles()
if "settings" not in st.session_state:
    st.session_state.settings = {
        "unit": "C",
        "align_mode": "Elapsed time",
        "show_grid": True,
        "show_legend": True,
        "line_width": 2.5,
        "theme": "Dark",
    }

profiles = st.session_state.profiles
settings = st.session_state.settings

with st.sidebar:
    st.header("Data")
    uploads = st.file_uploader(
        "Upload CSV or Excel files",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        help="Each numeric temperature column becomes a selectable profile. A date/time or elapsed-time column is detected automatically.",
    )
    append_mode = st.checkbox("Keep existing profiles when importing", value=True)
    if st.button("Import uploaded files", type="primary", use_container_width=True, disabled=not uploads):
        try:
            loaded, messages = load_uploaded_files(uploads)
            st.session_state.profiles = (profiles + loaded) if append_mode else loaded
            for message in messages:
                st.info(message)
            st.success(f"Imported {len(loaded)} profiles.")
            st.rerun()
        except Exception as exc:
            st.error(f"Import failed: {exc}")

    c1, c2 = st.columns(2)
    if c1.button("Load examples", use_container_width=True):
        st.session_state.profiles = load_example_profiles()
        st.rerun()
    if c2.button("Clear", use_container_width=True):
        st.session_state.profiles = []
        st.rerun()

    st.divider()
    st.header("Display")
    settings["unit"] = st.radio("Temperature unit", ["C", "F"], horizontal=True)
    settings["align_mode"] = st.selectbox("Timeline", ["Elapsed time", "Clock time"])
    settings["theme"] = st.selectbox("Chart theme", ["Dark", "Light"])
    settings["show_grid"] = st.checkbox("Grid lines", value=settings["show_grid"])
    settings["show_legend"] = st.checkbox("Legend", value=settings["show_legend"])
    settings["line_width"] = st.slider("Line width", 1.0, 5.0, settings["line_width"], 0.5)

st.markdown('<div class="cp-kicker">Cook profile studio</div>', unsafe_allow_html=True)
st.markdown('<div class="cp-title">Cook Profile Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="cp-note">Upload, organize, customize and compare cook temperature profiles. No tenderness analysis is applied.</div>', unsafe_allow_html=True)

if not profiles:
    st.info("Upload one or more CSV or Excel files, or load the included examples.")
    st.stop()

all_names = [p.name for p in profiles]
visible_names = st.multiselect("Profiles shown", all_names, default=[p.name for p in profiles if p.visible])
for p in profiles:
    p.visible = p.name in visible_names
visible = [p for p in profiles if p.visible]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Visible profiles", len(visible))
m2.metric("Longest profile", f"{max_duration(visible):.1f} h")
m3.metric("Highest reading", f"{max_temperature(visible, settings['unit']):.1f} °{settings['unit']}")
m4.metric("Displayed readings", f"{total_readings(visible):,}")

main, controls = st.columns([3.4, 1.2], gap="large")
with controls:
    st.subheader("Customize profile")
    selected_name = st.selectbox("Selected profile", all_names)
    selected = next(p for p in profiles if p.name == selected_name)
    new_name = st.text_input("Display name", value=selected.name)
    selected.channel = st.text_input("Channel label", value=selected.channel)
    selected.offset_hours = st.slider("Time offset (hours)", -24.0, 24.0, float(selected.offset_hours), 0.25)
    selected.color = st.color_picker("Line color", selected.color)
    if new_name and new_name != selected.name:
        if new_name in all_names:
            st.warning("Profile names must be unique.")
        else:
            selected.name = new_name
            st.rerun()
    if st.button("Remove selected profile", use_container_width=True):
        st.session_state.profiles = [p for p in profiles if p.profile_id != selected.profile_id]
        st.rerun()

    st.divider()
    st.subheader("Export")
    export_blob = profiles_to_csv_zip(visible, settings["unit"])
    st.download_button(
        "Download visible data",
        data=export_blob,
        file_name="cook_profiles_export.zip",
        mime="application/zip",
        use_container_width=True,
        disabled=not visible,
    )

with main:
    st.subheader("Temperature profiles")
    fig = build_comparison_chart(visible, settings)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "toImageButtonOptions": {"format": "png", "filename": "cook_profiles"}})

st.divider()
st.subheader("Profile details")
tabs = st.tabs([p.name for p in visible]) if visible else []
for tab, profile in zip(tabs, visible):
    with tab:
        a, b, c, d = st.columns(4)
        a.metric("Duration", f"{profile.duration_hours:.1f} h")
        b.metric("Readings", f"{len(profile.data):,}")
        c.metric("Minimum", f"{profile.temperature_min(settings['unit']):.1f} °{settings['unit']}")
        d.metric("Maximum", f"{profile.temperature_max(settings['unit']):.1f} °{settings['unit']}")
        st.plotly_chart(build_single_profile_chart(profile, settings), use_container_width=True, config={"displaylogo": False})
        with st.expander("Preview imported data"):
            st.dataframe(profile.export_frame(settings["unit"]).head(500), use_container_width=True)
