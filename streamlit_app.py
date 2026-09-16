import os
import sys
import json
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent import create_agent
from dashboard import render_dashboard, render_risk_dashboard
from aws_ai_energy.dashboard import (
    DashboardDataError,
    build_heatmap_payload,
    find_latest_analysis,
    parse_feature_request,
    SUPPORTED_FEATURES,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "Hackathon", "use-case-1", "data")

st.set_page_config(
    page_title="Seismic GPT",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    [data-testid="stSidebar"] { background-color: #0e1117; }
    [data-testid="stSidebar"] .stMarkdown h1 { color: #4da6ff; }
    .welcome-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #4da6ff33;
        border-radius: 12px;
        padding: 2rem;
        margin: 1rem 0;
    }
    .stat-card {
        background: #1a1a2e;
        border: 1px solid #ffffff15;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

ANALYSIS_DIR = Path(__file__).parent / "outputs" / "hazard_demo" / "analysis"


@st.cache_data
def _load_heatmap_points():
    run_dir = find_latest_analysis(ANALYSIS_DIR)
    if run_dir is None:
        return None, None
    points_path = run_dir / "enriched_points.csv"
    return (run_dir, points_path) if points_path.is_file() else (run_dir, None)


def render_heatmap_page():
    import pandas as pd

    st.header("Chat-Driven Feature Heatmaps")
    run_dir, points_path = _load_heatmap_points()
    if points_path is None:
        st.warning("No enriched points found. Run `make demo` first.")
        return

    st.caption(f"Analysis run: {run_dir.name}")

    if "hm_messages" not in st.session_state:
        st.session_state.hm_messages = []
    if "hm_payload" not in st.session_state:
        st.session_state.hm_payload = None

    chat_col, map_col = st.columns([1, 2])

    with chat_col:
        st.subheader("Chat")
        for msg in st.session_state.hm_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input(
            "Describe the heatmap (e.g. 'Show faults and reservoir probability')",
            key="hm_chat_input",
        )
        if prompt:
            st.session_state.hm_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    payload = build_heatmap_payload(points_path, prompt, max_points=500)
                    st.session_state.hm_payload = payload
                    features_list = ", ".join(f.replace("_", " ") for f in payload["features"])
                    response = (
                        f"Heatmap built with **{len(payload['points'])}** points "
                        f"(of {payload['source']['rows_total']} total).\n\n"
                        f"**Features:** {features_list}"
                    )
                except DashboardDataError as e:
                    response = f"**Error:** {e}\n\nSupported: {', '.join(SUPPORTED_FEATURES.keys())}"
                st.markdown(response)
            st.session_state.hm_messages.append({"role": "assistant", "content": response})
            st.rerun()

    with map_col:
        st.subheader("Heatmap")
        payload = st.session_state.hm_payload
        if payload is None:
            st.info("Use the chat to request a heatmap. Try: *'Show wells, faults, and reservoir probability'*")
        else:
            points = payload["points"]
            df = pd.json_normalize(points)

            c1, c2, c3 = st.columns(3)
            c1.metric("Points", len(points))
            c2.metric("Features", len(payload["features"]))
            c3.metric("Source Rows", payload["source"]["rows_total"])

            tab_map, tab_data, tab_json = st.tabs(["Scatter", "Data Table", "JSON Export"])

            with tab_map:
                color_col = None
                features = payload["features"]
                if "reservoir_probability" in features and "reservoir_probability" in df.columns:
                    color_col = "reservoir_probability"
                elif "faults" in features and "fault_likelihood" in df.columns:
                    color_col = "fault_likelihood"
                st.scatter_chart(df, x="inline_m", y="crossline_m", color=color_col, height=500)

                if "faults" in features and "nearest_fault_id" in df.columns:
                    faults = df["nearest_fault_id"].dropna().unique()
                    if len(faults):
                        st.markdown(f"**Detected faults:** {', '.join(str(f) for f in faults)}")
                if "wells" in features and "nearest_well_id" in df.columns:
                    wells = df["nearest_well_id"].dropna().unique()
                    if len(wells):
                        st.markdown(f"**Nearby wells:** {', '.join(str(w) for w in wells)}")

            with tab_data:
                st.dataframe(df, use_container_width=True, height=400)

            with tab_json:
                json_str = json.dumps(payload, indent=2, sort_keys=True)
                st.download_button("Download JSON", json_str, "heatmap_export.json", "application/json")
                with st.expander("Preview"):
                    st.code(json_str[:5000] + ("\n..." if len(json_str) > 5000 else ""), language="json")

            st.caption(payload.get("notice", ""))


if "agent" not in st.session_state:
    with st.spinner("Initializing agent..."):
        st.session_state.agent = create_agent(DATA_DIR)

with st.sidebar:
    st.title("💬 Seismic GPT")
    st.caption("Powered by Amazon Bedrock + Strands SDK")

    st.divider()

    page = st.radio(
        "Navigate",
        ["💬 Chat", "📊 Dashboard", "🎯 Risk Analysis", "🗺️ Heatmaps"],
        label_visibility="collapsed",
    )

    st.divider()

    if page == "🗺️ Heatmaps":
        st.markdown("##### 🗺️ Heatmap Features")
        st.markdown("Ask for any combination:")
        for canonical in SUPPORTED_FEATURES:
            label = canonical.replace("_", " ").title()
            st.markdown(f"- **{label}**")

    elif page == "💬 Chat":
        st.markdown("##### ⚡ Quick Queries")
        quick_queries = [
            "What caused stuck pipe on Midland State A 1H?",
            "Show all NPT incidents and their costs",
            "Which well has the highest seismic risk and why?",
            "What drilling precedents exist for fault damage zones?",
        ]
        for q in quick_queries:
            if st.button(q, use_container_width=True, key=f"quick_{q}"):
                st.session_state.quick_query = q

        st.divider()

        with st.expander("❓ Help & Examples"):
            st.markdown(
                "**Ask me about:**\n"
                "- 🔍 **Search** — Find reports by well, date, or keyword\n"
                "- ⚠️ **NPT Analysis** — Stuck pipe, lost circulation, root causes\n"
                "- 📋 **Well Info** — Metadata, formations, costs\n"
                "- 🎯 **Risk Screening** — Seismic hazards, fault proximity, drilling precedents\n\n"
                "Every answer cites specific data sources."
            )

        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent = create_agent(DATA_DIR)
            st.rerun()

    st.divider()
    st.caption("Claude Code + Bedrock AgentCore Hackathon")

if page == "📊 Dashboard":
    render_dashboard(DATA_DIR)
elif page == "🎯 Risk Analysis":
    render_risk_dashboard()
elif page == "🗺️ Heatmaps":
    render_heatmap_page()
else:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-box">
            <h2 style="margin-top:0; color:#4da6ff;">Seismic GPT</h2>
            <p style="color:#ccc; font-size:1.1rem;">
                Ask questions about daily drilling reports across 14 wells in the Permian, Eagle Ford, and Williston basins.
                Every answer is grounded in the data with full citations.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("""
            <div class="stat-card">
                <h3 style="color:#4da6ff; margin:0;">🔍 Search</h3>
                <p style="color:#999; font-size:0.9rem;">Query 267 daily drilling reports by well, date, or keyword</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="stat-card">
                <h3 style="color:#ff6b6b; margin:0;">⚠️ NPT Analysis</h3>
                <p style="color:#999; font-size:0.9rem;">Analyze 23 non-productive time incidents with root causes</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="stat-card">
                <h3 style="color:#51cf66; margin:0;">📋 Well Data</h3>
                <p style="color:#999; font-size:0.9rem;">Look up metadata, formations, and costs for any well</p>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown("""
            <div class="stat-card">
                <h3 style="color:#ff8c00; margin:0;">🎯 Risk Screen</h3>
                <p style="color:#999; font-size:0.9rem;">Seismic risk scores, faults, fractures, and drilling precedents</p>
            </div>
            """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if "quick_query" in st.session_state:
        prompt = st.session_state.pop("quick_query")
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing drilling data..."):
                try:
                    response = st.session_state.agent(prompt)
                    result = str(response)
                except Exception as e:
                    result = f"Error: {e}"
            st.markdown(result)

        st.session_state.messages.append({"role": "assistant", "content": result})
        st.rerun()

    if prompt := st.chat_input("Ask about drilling reports..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing drilling data..."):
                try:
                    response = st.session_state.agent(prompt)
                    result = str(response)
                except Exception as e:
                    result = f"Error: {e}"
            st.markdown(result)

        st.session_state.messages.append({"role": "assistant", "content": result})
