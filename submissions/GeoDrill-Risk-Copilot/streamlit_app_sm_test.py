"""Minimal Streamlit smoke app for feature heatmap payloads."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from aws_ai_energy.dashboard import (
    SUPPORTED_FEATURES,
    DashboardDataError,
    build_heatmap_payload,
    find_latest_analysis,
    heatmap_payload_to_json,
)

ROOT = Path(__file__).parent
ANALYSIS_DIR = ROOT / "outputs" / "hazard_demo" / "analysis"

st.set_page_config(page_title="GeoDrill Heatmap Smoke", layout="wide")
st.title("GeoDrill Feature Heatmap Smoke Test")

try:
    run_dir = find_latest_analysis(ANALYSIS_DIR)
except DashboardDataError as exc:
    st.warning(f"{exc}. Run `make demo` first.")
    st.stop()

points_path = run_dir / "enriched_points.csv"
prompt = st.text_input(
    "Feature request",
    value="Show wells, faults, reservoir probability, horizons, and provenance",
)
max_points = st.slider("Max points", min_value=50, max_value=2_000, value=500, step=50)

try:
    payload = build_heatmap_payload(points_path, prompt, max_points=max_points)
except DashboardDataError as exc:
    st.error(f"{exc}. Supported features: {', '.join(SUPPORTED_FEATURES)}")
    st.stop()

frame = pd.json_normalize(payload["points"])
st.caption(f"Run: {run_dir.name}")
st.scatter_chart(frame, x="inline_m", y="crossline_m", height=520)
st.dataframe(frame, use_container_width=True, height=320)
st.download_button(
    "Download JSON",
    heatmap_payload_to_json(payload),
    "geodrill_heatmap_smoke.json",
    "application/json",
)
