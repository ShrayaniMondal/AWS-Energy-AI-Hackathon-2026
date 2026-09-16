import os
import streamlit as st
from agent import create_agent
from dashboard import render_dashboard, render_risk_dashboard

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

if "agent" not in st.session_state:
    with st.spinner("Initializing agent..."):
        st.session_state.agent = create_agent(DATA_DIR)

with st.sidebar:
    st.title("💬 Seismic GPT")
    st.caption("Powered by Amazon Bedrock + Strands SDK")

    st.divider()

    page = st.radio(
        "Navigate",
        ["💬 Chat", "📊 Dashboard", "🎯 Risk Analysis"],
        label_visibility="collapsed",
    )

    st.divider()

    if page == "💬 Chat":
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
