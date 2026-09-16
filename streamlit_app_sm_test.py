"""Drilling Report Analysis — Streamlit Dashboard.

Chat-driven heatmap explorer with grounded evidence from DDR corpora and
synthetic seismic catalog data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

# Allow imports from scripts/ and src/
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aws_ai_energy.dashboard import (
    DashboardDataError,
    build_heatmap_payload,
    find_latest_analysis,
    heatmap_payload_to_json,
    parse_feature_request,
    SUPPORTED_FEATURES,
)

OUTPUTS_DIR = Path(__file__).parent / "outputs"
ANALYSIS_DIR = OUTPUTS_DIR / "hazard_demo" / "analysis"
EXPORT_DIR = OUTPUTS_DIR / "heatmap_exports"

st.set_page_config(
    page_title="Drilling Report Analysis",
    page_icon="⛽",
    layout="wide",
)


@st.cache_data
def load_analysis_bundle() -> tuple[Path | None, Path | None]:
    """Locate the latest analysis run and its enriched-points CSV."""
    run_dir = find_latest_analysis(ANALYSIS_DIR)
    if run_dir is None:
        return None, None
    points_path = run_dir / "enriched_points.csv"
    if not points_path.is_file():
        return run_dir, None
    return run_dir, points_path


def render_sidebar():
    """Sidebar with feature info and data status."""
    st.sidebar.title("Heatmap Features")
    st.sidebar.markdown("Ask for any combination of:")
    for canonical in SUPPORTED_FEATURES:
        label = canonical.replace("_", " ").title()
        st.sidebar.markdown(f"- **{label}**")

    st.sidebar.divider()
    run_dir, points_path = load_analysis_bundle()
    if run_dir is not None:
        st.sidebar.success(f"Analysis: `{run_dir.name}`")
    else:
        st.sidebar.warning("No analysis bundle found. Run `make demo` first.")
    if points_path is not None:
        st.sidebar.info(f"Points: `{points_path.name}`")

    st.sidebar.divider()
    st.sidebar.caption(
        "Synthetic data notice: seismic inputs are generated catalog data. "
        "Scores are screening ranks, not calibrated predictions."
    )


def render_chat():
    """Chat interface for heatmap feature requests."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_payload" not in st.session_state:
        st.session_state.last_payload = None

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Describe the heatmap you want (e.g., 'Show faults and reservoir probability with provenance')")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    _, points_path = load_analysis_bundle()

    with st.chat_message("assistant"):
        if points_path is None:
            response = (
                "No enriched-points CSV found. Please run the analysis pipeline first:\n\n"
                "```bash\nmake demo\n```"
            )
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            return

        try:
            request = parse_feature_request(prompt)
        except DashboardDataError as e:
            response = f"**Unsupported request:** {e}\n\nTry asking for: {', '.join(SUPPORTED_FEATURES.keys())}"
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            return

        try:
            payload = build_heatmap_payload(
                points_path,
                prompt,
                max_points=500,
            )
        except DashboardDataError as e:
            response = f"**Error building heatmap:** {e}"
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            return

        st.session_state.last_payload = payload
        features_list = ", ".join(f.replace("_", " ") for f in payload["features"])
        response = (
            f"Heatmap built with **{len(payload['points'])}** points "
            f"(of {payload['source']['rows_total']} total).\n\n"
            f"**Features:** {features_list}\n\n"
            f"View the heatmap below or download the JSON export."
        )
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})


def render_heatmap():
    """Render the heatmap visualization from the latest payload."""
    payload = st.session_state.get("last_payload")
    if payload is None:
        st.info("Use the chat to request a heatmap. Try: *'Show wells, faults, and reservoir probability with provenance'*")
        return

    features = payload["features"]
    points = payload["points"]

    if not points:
        st.warning("No points in the payload.")
        return

    import pandas as pd

    df = pd.json_normalize(points)

    col1, col2, col3 = st.columns(3)
    col1.metric("Points", len(points))
    col2.metric("Features", len(features))
    col3.metric("Source Rows", payload["source"]["rows_total"])

    tab_map, tab_data, tab_json = st.tabs(["Heatmap", "Data Table", "JSON Export"])

    with tab_map:
        _render_scatter(df, features)

    with tab_data:
        st.dataframe(df, use_container_width=True, height=400)

    with tab_json:
        _render_json_export(payload)

    st.caption(payload.get("notice", ""))


def _render_scatter(df, features: list[str]):
    """Render a scatter plot of the heatmap points."""
    if "inline_m" not in df.columns or "crossline_m" not in df.columns:
        st.warning("Missing coordinate columns for scatter plot.")
        return

    color_col = None
    if "reservoir_probability" in features and "reservoir_probability" in df.columns:
        color_col = "reservoir_probability"
    elif "fault_likelihood" in df.columns and "faults" in features:
        color_col = "fault_likelihood"

    st.scatter_chart(
        df,
        x="inline_m",
        y="crossline_m",
        color=color_col,
        height=500,
    )

    if "faults" in features and "nearest_fault_id" in df.columns:
        fault_ids = df["nearest_fault_id"].dropna().unique()
        if len(fault_ids) > 0:
            st.markdown(f"**Detected faults:** {', '.join(str(f) for f in fault_ids)}")

    if "wells" in features and "nearest_well_id" in df.columns:
        well_ids = df["nearest_well_id"].dropna().unique()
        if len(well_ids) > 0:
            st.markdown(f"**Nearby wells:** {', '.join(str(w) for w in well_ids)}")

    if "horizons" in features:
        horizon_cols = [c for c in ("horizon_top_m", "horizon_base_m") if c in df.columns]
        if horizon_cols:
            st.markdown(f"**Horizon range:** {df.get('horizon_top_m', pd.Series()).min():.0f}m – {df.get('horizon_base_m', pd.Series()).max():.0f}m")


def _render_json_export(payload: dict):
    """Render the JSON export with download button."""
    json_str = json.dumps(payload, indent=2, sort_keys=True)

    st.download_button(
        label="Download Heatmap JSON",
        data=json_str,
        file_name="heatmap_export.json",
        mime="application/json",
    )

    with st.expander("Preview JSON payload"):
        st.code(json_str[:5000] + ("\n..." if len(json_str) > 5000 else ""), language="json")

    provenance_count = sum(1 for p in payload["points"] if "provenance" in p)
    if provenance_count > 0:
        st.markdown(f"**Provenance attached:** {provenance_count}/{len(payload['points'])} points have catalog-keyed provenance (datasetid, fileid, sampleid, source_row).")


def main():
    st.title("Drilling Report Analysis Agent")
    st.markdown("**Use Case 1** — Chat-driven heatmap explorer with grounded evidence")

    render_sidebar()

    chat_col, map_col = st.columns([1, 2])

    with chat_col:
        st.subheader("Chat")
        render_chat()

    with map_col:
        st.subheader("Heatmap")
        render_heatmap()


if __name__ == "__main__":
    main()
