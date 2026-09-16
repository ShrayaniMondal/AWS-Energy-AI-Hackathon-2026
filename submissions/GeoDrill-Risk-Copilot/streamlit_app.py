"""GeoDrill Risk Copilot Streamlit entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent import create_agent
from aws_ai_energy.dashboard import (
    SUPPORTED_FEATURES,
    DashboardDataError,
    build_heatmap_payload,
    find_latest_analysis,
    heatmap_payload_to_json,
)
from dashboard import render_dashboard, render_risk_dashboard

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "Hackathon" / "use-case-1" / "data"
ANALYSIS_DIR = ROOT / "outputs" / "hazard_demo" / "analysis"


st.set_page_config(
    page_title="GeoDrill Risk Copilot",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.4rem; }
      [data-testid="stSidebar"] { border-right: 1px solid #e5e7eb; }
      .hero {
        border: 1px solid #d7dee8;
        border-radius: 8px;
        padding: 1rem 1.1rem;
        background: #f8fafc;
        margin: 0.5rem 0 1rem;
      }
      .hero h2 { margin: 0 0 0.35rem; }
      .hero p { margin: 0; color: #475569; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def _load_heatmap_points() -> tuple[Path | None, Path | None]:
    try:
        run_dir = find_latest_analysis(ANALYSIS_DIR)
    except DashboardDataError:
        return None, None
    points_path = run_dir / "enriched_points.csv"
    return run_dir, points_path if points_path.is_file() else None


def _render_heatmap_page() -> None:
    st.header("Chat-Driven Feature Heatmaps")
    run_dir, points_path = _load_heatmap_points()
    if run_dir is None or points_path is None:
        st.warning("No enriched points found. Run `make demo` to generate catalog evidence.")
        return

    st.caption(f"Analysis run: {run_dir.name}")
    st.session_state.setdefault("heatmap_messages", [])
    st.session_state.setdefault("heatmap_payload", None)

    chat_col, map_col = st.columns([1, 2])
    with chat_col:
        st.subheader("Request")
        for message in st.session_state.heatmap_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        prompt = st.chat_input(
            "Example: Show wells, faults, reservoir probability, and provenance",
            key="heatmap_prompt",
        )
        if prompt:
            st.session_state.heatmap_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    payload = build_heatmap_payload(points_path, prompt, max_points=500)
                    st.session_state.heatmap_payload = payload
                    feature_text = ", ".join(item.replace("_", " ") for item in payload["features"])
                    response = (
                        f"Built a heatmap payload with {len(payload['points'])} points "
                        f"from {payload['source']['rows_total']} source rows.\n\n"
                        f"Features: {feature_text}"
                    )
                except DashboardDataError as exc:
                    response = f"{exc}\n\nSupported features: {', '.join(SUPPORTED_FEATURES)}"
                st.markdown(response)
            st.session_state.heatmap_messages.append({"role": "assistant", "content": response})
            st.rerun()

    with map_col:
        st.subheader("Map and Export")
        payload = st.session_state.heatmap_payload
        if payload is None:
            st.info("Use the chat request to build an auditable feature payload.")
            return

        points = payload["points"]
        frame = pd.json_normalize(points)
        metrics = st.columns(3)
        metrics[0].metric("Points", len(points))
        metrics[1].metric("Features", len(payload["features"]))
        metrics[2].metric("Rows Scanned", payload["source"]["rows_total"])

        tab_map, tab_rows, tab_json = st.tabs(["Scatter", "Rows", "JSON"])
        with tab_map:
            color_col = None
            for candidate in ("values.reservoir_probability", "values.fault_likelihood"):
                if candidate in frame:
                    color_col = candidate
                    break
            st.scatter_chart(frame, x="inline_m", y="crossline_m", color=color_col, height=520)
        with tab_rows:
            st.dataframe(frame, use_container_width=True, height=430)
        with tab_json:
            json_text = heatmap_payload_to_json(payload)
            st.download_button(
                "Download JSON",
                json_text,
                "geodrill_heatmap_payload.json",
                "application/json",
            )
            preview = json_text[:6_000] + ("\n..." if len(json_text) > 6_000 else "")
            st.code(preview, language="json")
        st.caption(payload.get("notice", ""))


def _render_chat_page() -> None:
    st.markdown(
        """
        <div class="hero">
          <h2>GeoDrill Risk Copilot</h2>
          <p>Ask grounded questions across drilling reports, NPT incidents,
          synthetic seismic risk evidence, and catalog-backed provenance.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if "agent" not in st.session_state:
        with st.spinner("Loading local evidence tools..."):
            st.session_state.agent = create_agent(DATA_DIR)
    st.session_state.setdefault("messages", [])

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask about NPT, drilling performance, faults, targets, or provenance")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Reading grounded evidence..."):
                try:
                    result = str(st.session_state.agent(prompt))
                except Exception as exc:
                    result = f"Agent error: {exc}"
            st.markdown(result)
        st.session_state.messages.append({"role": "assistant", "content": result})


with st.sidebar:
    st.title("GeoDrill")
    st.caption("Risk-ranked seismic catalog, drilling evidence, and AgentCore-ready exports.")
    page = st.radio(
        "Navigate",
        ["Chat", "Operations Dashboard", "Risk Analysis", "Heatmaps"],
        label_visibility="collapsed",
    )
    st.divider()
    if page == "Chat":
        st.markdown("Quick prompts")
        quick_prompts = [
            "Which well has the highest seismic risk and why?",
            "Show NPT incidents and their costs.",
            "What drilling precedents exist for fault damage zones?",
            "Compare drilling performance against Wolfcamp A benchmarks.",
        ]
        for prompt_text in quick_prompts:
            if st.button(prompt_text, use_container_width=True):
                st.session_state.messages = st.session_state.get("messages", [])
                st.session_state.messages.append({"role": "user", "content": prompt_text})
                st.session_state.agent = st.session_state.get("agent") or create_agent(DATA_DIR)
                st.session_state.messages.append(
                    {"role": "assistant", "content": str(st.session_state.agent(prompt_text))}
                )
                st.rerun()
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    elif page == "Heatmaps":
        st.markdown("Supported features")
        for feature in SUPPORTED_FEATURES:
            st.markdown(f"- {feature.replace('_', ' ')}")
    st.divider()
    st.caption("Use `make demo` before dashboard exploration.")


if page == "Operations Dashboard":
    render_dashboard(DATA_DIR)
elif page == "Risk Analysis":
    render_risk_dashboard()
elif page == "Heatmaps":
    _render_heatmap_page()
else:
    _render_chat_page()
