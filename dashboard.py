import os
import json
import glob
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


ANALYSIS_DIR = os.path.join(os.path.dirname(__file__), "outputs", "hazard_demo", "analysis")


@st.cache_data
def load_data(data_dir):
    reports = []
    for f in sorted(glob.glob(os.path.join(data_dir, "daily_drilling_reports", "*.json"))):
        with open(f) as fh:
            reports.append(json.load(fh))
    df_reports_a = pd.DataFrame(reports)
    df_reports_a["report_date"] = pd.to_datetime(df_reports_a["report_date"])

    df_reports_b = pd.read_csv(os.path.join(data_dir, "daily_drilling_reports.csv"))
    df_reports_b["report_date"] = pd.to_datetime(df_reports_b["report_date"])

    npt = pd.read_csv(os.path.join(data_dir, "npt_incident_log.csv"))
    npt["date"] = pd.to_datetime(npt["date"])
    bit = pd.read_csv(os.path.join(data_dir, "bit_records.csv"))
    wells_a = pd.read_csv(os.path.join(data_dir, "well_metadata.csv"))
    wells_b = pd.read_csv(os.path.join(data_dir, "well_master.csv"))
    thresholds = pd.read_csv(os.path.join(data_dir, "anomaly_thresholds.csv"))
    benchmarks = pd.read_csv(os.path.join(data_dir, "drilling_benchmarks.csv"))

    return df_reports_a, df_reports_b, npt, bit, wells_a, wells_b, thresholds, benchmarks


@st.cache_data
def load_risk_data():
    run_dirs = sorted(glob.glob(os.path.join(ANALYSIS_DIR, "run_*")))
    if not run_dirs:
        return None
    run_dir = run_dirs[-1]
    data = {}
    for name in ("summary", "fault_fracture_hotspots", "reservoir_targets", "well_briefs", "faults"):
        path = os.path.join(run_dir, f"{name}.json")
        if os.path.exists(path):
            with open(path) as f:
                data[name] = json.load(f)
    for name in ("well_screens", "precedents", "enriched_points"):
        path = os.path.join(run_dir, f"{name}.csv")
        if os.path.exists(path):
            data[name] = pd.read_csv(path)
    atlas_path = os.path.join(run_dir, "hazard_atlas.html")
    if os.path.exists(atlas_path):
        data["atlas_path"] = atlas_path
    data["run_dir"] = run_dir
    return data


def render_risk_dashboard():
    risk = load_risk_data()
    if risk is None:
        st.warning("No risk analysis outputs found. Run `make demo` to generate them.")
        return

    summary = risk.get("summary", {})
    st.header("Subsurface Risk Analysis")
    st.caption(f"Run: {summary.get('catalog_run_id', 'N/A')} | Formation: {summary.get('formation', 'N/A')}")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Points Analyzed", f"{summary.get('points', 0):,}")
    k2.metric("Faults Detected", summary.get("faults_detected", 0))
    k3.metric("Fracture Corridors", summary.get("fracture_corridors", 0))
    k4.metric("Wells Screened", summary.get("wells_screened", 0))
    highest = summary.get("highest_risk_well", "N/A")
    idx = summary.get("highest_risk_index", 0)
    k5.metric("Highest Risk", f"{highest} ({idx})")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Well Risk Screening")
        ws = risk.get("well_screens")
        if ws is not None and not ws.empty:
            ws_sorted = ws.sort_values("risk_index", ascending=True)
            colors = ws_sorted["risk_class"].map({
                "severe": "#ff4444", "high": "#ff8c00",
                "moderate": "#ffd700", "low": "#51cf66",
            })
            fig = go.Figure(go.Bar(
                x=ws_sorted["risk_index"],
                y=ws_sorted["well_id"],
                orientation="h",
                marker_color=colors.tolist(),
                text=ws_sorted["risk_class"],
                textposition="auto",
            ))
            fig.update_layout(
                xaxis_title="Risk Index",
                yaxis_title="Well",
                margin=dict(t=10, b=10),
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Decision Distribution")
        decisions = summary.get("decision_counts", {})
        if decisions:
            colors_map = {
                "geomechanics_review": "#ff4444",
                "drilling_candidate": "#51cf66",
                "watch_zone": "#ffd700",
            }
            fig = go.Figure(go.Pie(
                labels=list(decisions.keys()),
                values=list(decisions.values()),
                marker_colors=[colors_map.get(k, "#999") for k in decisions],
                textinfo="label+value+percent",
                hole=0.4,
            ))
            fig.update_layout(margin=dict(t=10, b=10), height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    left2, right2 = st.columns(2)

    with left2:
        st.subheader("Top Hazard Hotspots")
        hotspots = risk.get("fault_fracture_hotspots", [])
        if hotspots:
            df_h = pd.DataFrame(hotspots)
            fig = px.scatter(
                df_h, x="inline_m", y="crossline_m",
                color="hazard_score", size="fault_score",
                hover_data=["lithology", "nearest_fault_id", "fracture_class", "depth_ft"],
                color_continuous_scale="Reds",
                labels={"inline_m": "Inline (m)", "crossline_m": "Crossline (m)"},
            )
            fig.update_layout(margin=dict(t=10, b=10), height=400)
            st.plotly_chart(fig, use_container_width=True)

    with right2:
        st.subheader("Top Reservoir Targets")
        targets = risk.get("reservoir_targets", [])
        if targets:
            df_t = pd.DataFrame(targets)
            fig = px.scatter(
                df_t, x="inline_m", y="crossline_m",
                color="target_score", size="confidence_score",
                hover_data=["lithology", "reservoir_probability", "nearest_well_id", "depth_ft"],
                color_continuous_scale="Greens",
                labels={"inline_m": "Inline (m)", "crossline_m": "Crossline (m)"},
            )
            fig.update_layout(margin=dict(t=10, b=10), height=400)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Hazard vs Target Score — All Enriched Points")
    enriched = risk.get("enriched_points")
    if enriched is not None and not enriched.empty:
        sample = enriched.sample(min(2000, len(enriched)), random_state=42)
        fig = px.scatter(
            sample, x="hazard_score", y="target_score",
            color="decision",
            color_discrete_map={
                "geomechanics_review": "#ff4444",
                "drilling_candidate": "#51cf66",
                "watch_zone": "#ffd700",
            },
            hover_data=["lithology", "depth_ft", "nearest_well_id"],
            labels={"hazard_score": "Hazard Score", "target_score": "Target Score"},
            opacity=0.6,
        )
        fig.update_layout(margin=dict(t=10, b=10), height=400, legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Drilling Precedents Linked to Seismic Hazards")
    prec = risk.get("precedents")
    if prec is not None and not prec.empty:
        left3, right3 = st.columns(2)
        with left3:
            prec_cost = prec.groupby("hazard").agg(
                total_cost=("cost_usd", "sum"),
                incidents=("incident_id", "count"),
            ).reset_index().sort_values("total_cost", ascending=True)
            fig = px.bar(
                prec_cost, x="total_cost", y="hazard",
                color="incidents",
                orientation="h",
                labels={"total_cost": "Total Cost (USD)", "hazard": "Hazard Type"},
                color_continuous_scale="OrRd",
            )
            fig.update_layout(margin=dict(t=10, b=10), height=300)
            st.plotly_chart(fig, use_container_width=True)
        with right3:
            st.dataframe(
                prec[["well_id", "hazard", "incident_id", "incident_well", "npt_category",
                       "root_cause", "hours_lost", "cost_usd"]],
                use_container_width=True, hide_index=True, height=300,
            )

    st.divider()

    briefs = risk.get("well_briefs", [])
    if briefs:
        st.subheader("Well Hazard Briefs")
        well_ids = [b["screen"]["well"]["id"] for b in briefs]
        selected = st.selectbox("Select well", well_ids)
        brief = next(b for b in briefs if b["screen"]["well"]["id"] == selected)
        screen = brief["screen"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk Index", f"{screen['risk_index']:.1f}")
        c2.metric("Risk Class", screen["risk_class"].upper())
        c3.metric("Nearest Fault", f"{screen.get('nearest_fault_distance_m', 'N/A')} m")
        c4.metric("Samples", screen["point_count"])

        if screen.get("hazards"):
            st.markdown("**Triggered Hazards:**")
            for h in screen["hazards"]:
                st.markdown(f"- **{h['hazard']}**: {h['title']} — {h['measured']}")

        if brief.get("precedents"):
            st.markdown("**Linked Drilling Precedents:**")
            for p in brief["precedents"]:
                with st.expander(f"{p['hazard']}: {p['note'][:80]}..."):
                    for inc in p.get("incidents", []):
                        st.markdown(
                            f"- **{inc['incident_id']}** ({inc['well_name']}): "
                            f"{inc['root_cause']} → {inc['resolution']} | "
                            f"{inc['hours_lost']}h, ${inc['cost_usd']:,.0f}"
                        )
                    for ref in p.get("references", []):
                        excerpt = ref["excerpt"][0] if ref.get("excerpt") else ""
                        st.markdown(f"  - *{ref['document']}* line {ref['line']}: {excerpt}")

    atlas_path = risk.get("atlas_path")
    if atlas_path:
        st.divider()
        st.subheader("Interactive Hazard Atlas")
        with open(atlas_path) as f:
            st.components.v1.html(f.read(), height=700, scrolling=True)


def render_dashboard(data_dir):
    df_a, df_b, npt, bit, wells_a, wells_b, thresholds, benchmarks = load_data(data_dir)

    st.header("Drilling Operations Dashboard")

    # --- Filters ---
    with st.expander("🔧 Filters", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        all_wells_a = sorted(df_a["well_name"].unique())
        all_npt_cats = sorted(npt["npt_category"].unique())
        with fc1:
            well_filter = st.multiselect(
                "Wells (Corpus A)",
                options=all_wells_a,
                default=all_wells_a,
                key="drill_well_filter",
            )
        with fc2:
            npt_cat_filter = st.multiselect(
                "NPT Category",
                options=all_npt_cats,
                default=all_npt_cats,
                key="drill_npt_filter",
            )
        with fc3:
            min_date = df_a["report_date"].min().date()
            max_date = df_a["report_date"].max().date()
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="drill_date_filter",
            )

    # Apply filters
    df_a_f = df_a[df_a["well_name"].isin(well_filter)]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        df_a_f = df_a_f[(df_a_f["report_date"].dt.date >= date_range[0]) & (df_a_f["report_date"].dt.date <= date_range[1])]
    npt_f = npt[npt["npt_category"].isin(npt_cat_filter)]
    if well_filter != all_wells_a:
        npt_f = npt_f[npt_f["well_name"].isin(well_filter)]

    # --- Metrics (filtered) ---
    k1, k2, k3, k4, k5 = st.columns(5)
    total_npt_hrs = npt_f["hours_lost"].sum()
    total_npt_cost = npt_f["cost_usd"].sum()
    avg_rop = df_a_f["rop_fthr"].mean() if not df_a_f.empty else 0
    k1.metric("Total Wells", f"{len(wells_a) + len(wells_b)}")
    k2.metric("DDR Reports", f"{len(df_a_f) + len(df_b)}")
    k3.metric("NPT Hours", f"{total_npt_hrs:.1f}")
    k4.metric("NPT Cost", f"${total_npt_cost:,.0f}")
    k5.metric("Avg ROP (ft/hr)", f"{avg_rop:.1f}")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("NPT Incidents by Category")
        if npt_f.empty:
            st.info("No NPT incidents match the selected filters.")
        else:
            npt_cat = npt_f.groupby("npt_category").agg(
                count=("incident_id", "count"),
                hours=("hours_lost", "sum"),
            ).reset_index()
            fig = px.bar(
                npt_cat, x="npt_category", y="hours",
                color="npt_category",
                text="count",
                labels={"hours": "Hours Lost", "npt_category": "Category", "count": "Incidents"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(showlegend=False, margin=dict(t=10, b=10), height=350)
            fig.update_traces(texttemplate="%{text} incidents", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("NPT Cost by Well")
        if npt_f.empty:
            st.info("No NPT incidents match the selected filters.")
        else:
            npt_well = npt_f.groupby("well_name").agg(
                total_cost=("cost_usd", "sum"),
                total_hours=("hours_lost", "sum"),
            ).reset_index().sort_values("total_cost", ascending=True)
            fig = px.bar(
                npt_well, x="total_cost", y="well_name",
                color="total_hours",
                labels={"total_cost": "Cost (USD)", "well_name": "Well", "total_hours": "Hours Lost"},
                color_continuous_scale="Reds",
                orientation="h",
            )
            fig.update_layout(margin=dict(t=10, b=10), height=350)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Rate of Penetration (ROP) Over Time")
    if df_a_f.empty:
        st.info("No reports match the selected filters.")
    else:
        fig = px.line(
            df_a_f, x="report_date", y="rop_fthr",
            color="well_name",
            markers=True,
            labels={"rop_fthr": "ROP (ft/hr)", "report_date": "Date", "well_name": "Well"},
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig.update_layout(margin=dict(t=10, b=10), height=400, legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    left2, right2 = st.columns(2)

    with left2:
        st.subheader("Depth Progress by Well")
        if df_a_f.empty:
            st.info("No data for selected wells.")
        else:
            depth_data = df_a_f.groupby("well_name").agg(
                max_depth=("measured_depth_ft", "max"),
                total_footage=("footage_drilled_ft", "sum"),
            ).reset_index().sort_values("max_depth", ascending=True)
            fig = px.bar(
                depth_data, x="max_depth", y="well_name",
                color="total_footage",
                labels={"max_depth": "Max Depth (ft)", "well_name": "Well", "total_footage": "Total Footage"},
                color_continuous_scale="Blues",
                orientation="h",
            )
            fig.update_layout(margin=dict(t=10, b=10), height=300)
            st.plotly_chart(fig, use_container_width=True)

    with right2:
        st.subheader("Cumulative Cost by Well")
        if df_a_f.empty:
            st.info("No data for selected wells.")
        else:
            cost_data = df_a_f.sort_values("report_date").groupby("well_name").last().reset_index()
            fig = px.bar(
                cost_data, x="well_name", y="cumulative_cost_usd",
                color="well_name",
                labels={"cumulative_cost_usd": "Cumulative Cost (USD)", "well_name": "Well"},
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(showlegend=False, margin=dict(t=10, b=10), height=300)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Bit Performance — Avg ROP by Type & Well")
    bit_f = bit[bit["well_name"].isin(well_filter)] if well_filter != all_wells_a else bit
    if bit_f.empty:
        st.info("No bit records match the selected wells.")
    else:
        fig = px.scatter(
            bit_f, x="footage_ft", y="avg_rop_fthr",
            color="bit_type", size="hours",
            hover_data=["well_name", "manufacturer", "dull_grade_iadc"],
            labels={
                "footage_ft": "Footage Drilled (ft)",
                "avg_rop_fthr": "Avg ROP (ft/hr)",
                "bit_type": "Bit Type",
                "hours": "Hours",
            },
            color_discrete_sequence=px.colors.qualitative.Vivid,
        )
        fig.update_layout(margin=dict(t=10, b=10), height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Data Explorer")
    table_choice = st.selectbox("Select dataset", [
        "Well Metadata (Corpus A)",
        "Well Master (Corpus B)",
        "NPT Incident Log",
        "Bit Records",
        "Drilling Benchmarks",
    ])
    table_map = {
        "Well Metadata (Corpus A)": wells_a,
        "Well Master (Corpus B)": wells_b,
        "NPT Incident Log": npt,
        "Bit Records": bit,
        "Drilling Benchmarks": benchmarks,
    }
    st.dataframe(table_map[table_choice], use_container_width=True, hide_index=True)
