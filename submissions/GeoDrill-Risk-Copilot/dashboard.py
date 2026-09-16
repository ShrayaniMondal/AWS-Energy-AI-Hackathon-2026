"""Streamlit dashboard pages for drilling operations and seismic risk."""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
ANALYSIS_DIR = ROOT / "outputs" / "hazard_demo" / "analysis"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def load_data(data_dir: str | os.PathLike[str]) -> dict[str, pd.DataFrame]:
    root = Path(data_dir)
    reports = []
    for path_name in sorted(glob.glob(str(root / "daily_drilling_reports" / "*.json"))):
        path = Path(path_name)
        with path.open(encoding="utf-8") as handle:
            report = json.load(handle)
        report["source_file"] = str(path)
        reports.append(report)

    json_reports = pd.DataFrame(reports)
    if not json_reports.empty and "report_date" in json_reports:
        json_reports["report_date"] = pd.to_datetime(json_reports["report_date"])

    tabular_reports = _read_csv(root / "daily_drilling_reports.csv")
    if not tabular_reports.empty and "report_date" in tabular_reports:
        tabular_reports["report_date"] = pd.to_datetime(tabular_reports["report_date"])

    npt = _read_csv(root / "npt_incident_log.csv")
    if not npt.empty and "date" in npt:
        npt["date"] = pd.to_datetime(npt["date"])

    return {
        "json_reports": json_reports,
        "tabular_reports": tabular_reports,
        "npt": npt,
        "bit": _read_csv(root / "bit_records.csv"),
        "well_metadata": _read_csv(root / "well_metadata.csv"),
        "well_master": _read_csv(root / "well_master.csv"),
        "thresholds": _read_csv(root / "anomaly_thresholds.csv"),
        "benchmarks": _read_csv(root / "drilling_benchmarks.csv"),
    }


@st.cache_data
def load_risk_data() -> dict[str, object] | None:
    run_dirs = sorted(path for path in ANALYSIS_DIR.glob("run_*") if path.is_dir())
    if not run_dirs:
        return None
    run_dir = run_dirs[-1]
    data: dict[str, object] = {"run_dir": str(run_dir)}
    for name in (
        "summary",
        "fault_fracture_hotspots",
        "reservoir_targets",
        "well_briefs",
        "faults",
    ):
        path = run_dir / f"{name}.json"
        if path.is_file():
            data[name] = json.loads(path.read_text(encoding="utf-8"))
    for name in ("well_screens", "precedents", "enriched_points"):
        path = run_dir / f"{name}.csv"
        if path.is_file():
            data[name] = pd.read_csv(path)
    atlas_path = run_dir / "hazard_atlas.html"
    if atlas_path.is_file():
        data["atlas_path"] = str(atlas_path)
    return data


def render_dashboard(data_dir: str | os.PathLike[str]) -> None:
    data = load_data(data_dir)
    json_reports = data["json_reports"]
    tabular_reports = data["tabular_reports"]
    npt = data["npt"]
    bit = data["bit"]
    well_metadata = data["well_metadata"]
    well_master = data["well_master"]
    benchmarks = data["benchmarks"]

    st.header("Drilling Operations Dashboard")
    if json_reports.empty:
        st.warning("No JSON daily drilling reports were found.")
        return

    all_wells = sorted(json_reports["well_name"].dropna().unique())
    all_categories = sorted(npt["npt_category"].dropna().unique()) if not npt.empty else []
    with st.expander("Filters", expanded=True):
        filter_cols = st.columns(3)
        with filter_cols[0]:
            well_filter = st.multiselect("Wells", all_wells, default=all_wells)
        with filter_cols[1]:
            npt_filter = st.multiselect("NPT category", all_categories, default=all_categories)
        with filter_cols[2]:
            min_date = json_reports["report_date"].min().date()
            max_date = json_reports["report_date"].max().date()
            date_range = st.date_input(
                "Date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )

    filtered_reports = json_reports[json_reports["well_name"].isin(well_filter)]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        filtered_reports = filtered_reports[
            (filtered_reports["report_date"].dt.date >= date_range[0])
            & (filtered_reports["report_date"].dt.date <= date_range[1])
        ]
    filtered_npt = npt[npt["npt_category"].isin(npt_filter)] if not npt.empty else npt
    if not filtered_npt.empty and well_filter != all_wells:
        filtered_npt = filtered_npt[filtered_npt["well_name"].isin(well_filter)]

    metrics = st.columns(5)
    metrics[0].metric("Total Wells", f"{len(well_metadata) + len(well_master)}")
    metrics[1].metric("DDR Rows", f"{len(filtered_reports) + len(tabular_reports):,}")
    metrics[2].metric("NPT Hours", f"{filtered_npt.get('hours_lost', pd.Series()).sum():.1f}")
    metrics[3].metric("NPT Cost", f"${filtered_npt.get('cost_usd', pd.Series()).sum():,.0f}")
    avg_rop = filtered_reports["rop_fthr"].mean() if not filtered_reports.empty else 0
    metrics[4].metric("Avg ROP", f"{avg_rop:.1f} ft/hr")

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("NPT Hours by Category")
        if filtered_npt.empty:
            st.info("No NPT incidents match the selected filters.")
        else:
            npt_by_category = (
                filtered_npt.groupby("npt_category")
                .agg(hours=("hours_lost", "sum"), incidents=("incident_id", "count"))
                .reset_index()
            )
            fig = px.bar(
                npt_by_category,
                x="npt_category",
                y="hours",
                color="npt_category",
                text="incidents",
                labels={"hours": "Hours Lost", "npt_category": "Category"},
            )
            fig.update_layout(showlegend=False, margin=dict(t=10, b=10), height=350)
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("NPT Cost by Well")
        if filtered_npt.empty:
            st.info("No NPT incidents match the selected filters.")
        else:
            npt_by_well = (
                filtered_npt.groupby("well_name")
                .agg(total_cost=("cost_usd", "sum"), total_hours=("hours_lost", "sum"))
                .reset_index()
                .sort_values("total_cost")
            )
            fig = px.bar(
                npt_by_well,
                x="total_cost",
                y="well_name",
                color="total_hours",
                orientation="h",
                labels={"total_cost": "Cost (USD)", "well_name": "Well"},
                color_continuous_scale="Reds",
            )
            fig.update_layout(margin=dict(t=10, b=10), height=350)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Rate of Penetration Over Time")
    if filtered_reports.empty:
        st.info("No reports match the selected filters.")
    else:
        fig = px.line(
            filtered_reports,
            x="report_date",
            y="rop_fthr",
            color="well_name",
            markers=True,
            labels={"rop_fthr": "ROP (ft/hr)", "report_date": "Date", "well_name": "Well"},
        )
        fig.update_layout(
            margin=dict(t=10, b=10),
            height=400,
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    left2, right2 = st.columns(2)
    with left2:
        st.subheader("Depth Progress")
        if not filtered_reports.empty:
            depth_data = (
                filtered_reports.groupby("well_name")
                .agg(max_depth=("measured_depth_ft", "max"), footage=("footage_drilled_ft", "sum"))
                .reset_index()
                .sort_values("max_depth")
            )
            fig = px.bar(
                depth_data,
                x="max_depth",
                y="well_name",
                color="footage",
                orientation="h",
                labels={"max_depth": "Max Depth (ft)", "well_name": "Well"},
                color_continuous_scale="Blues",
            )
            fig.update_layout(margin=dict(t=10, b=10), height=320)
            st.plotly_chart(fig, use_container_width=True)
    with right2:
        st.subheader("Bit Performance")
        bit_filtered = bit[bit["well_name"].isin(well_filter)] if not bit.empty else bit
        if bit_filtered.empty:
            st.info("No bit records match the selected wells.")
        else:
            fig = px.scatter(
                bit_filtered,
                x="footage_ft",
                y="avg_rop_fthr",
                color="bit_type",
                size="hours",
                hover_data=["well_name", "manufacturer", "dull_grade_iadc"],
                labels={"footage_ft": "Footage Drilled (ft)", "avg_rop_fthr": "Avg ROP"},
            )
            fig.update_layout(margin=dict(t=10, b=10), height=320)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Data Explorer")
    table_choice = st.selectbox(
        "Dataset",
        [
            "Well Metadata",
            "Well Master",
            "NPT Incident Log",
            "Bit Records",
            "Drilling Benchmarks",
        ],
    )
    table_map = {
        "Well Metadata": well_metadata,
        "Well Master": well_master,
        "NPT Incident Log": npt,
        "Bit Records": bit,
        "Drilling Benchmarks": benchmarks,
    }
    st.dataframe(table_map[table_choice], use_container_width=True, hide_index=True)


def render_risk_dashboard() -> None:
    risk = load_risk_data()
    if risk is None:
        st.warning("No risk analysis outputs found. Run `make demo` to generate them.")
        return

    summary = risk.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    st.header("Subsurface Risk Analysis")
    st.caption(
        f"Run: {summary.get('catalog_run_id', 'N/A')} | "
        f"Formation: {summary.get('formation', 'N/A')}"
    )

    metrics = st.columns(5)
    metrics[0].metric("Points Analyzed", f"{summary.get('points', 0):,}")
    metrics[1].metric("Faults Detected", summary.get("faults_detected", 0))
    metrics[2].metric("Fracture Corridors", summary.get("fracture_corridors", 0))
    metrics[3].metric("Wells Screened", summary.get("wells_screened", 0))
    highest = summary.get("highest_risk_well", "N/A")
    metrics[4].metric("Highest Risk", f"{highest} ({summary.get('highest_risk_index', 0)})")

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("Well Risk Screening")
        well_screens = risk.get("well_screens")
        if isinstance(well_screens, pd.DataFrame) and not well_screens.empty:
            ordered = well_screens.sort_values("risk_index")
            colors = ordered["risk_class"].map(
                {"severe": "#d73027", "high": "#fc8d59", "moderate": "#fee08b", "low": "#1a9850"}
            )
            fig = go.Figure(
                go.Bar(
                    x=ordered["risk_index"],
                    y=ordered["well_id"],
                    orientation="h",
                    marker_color=colors.tolist(),
                    text=ordered["risk_class"],
                )
            )
            fig.update_layout(
                xaxis_title="Risk Index",
                yaxis_title="Well",
                margin=dict(t=10, b=10),
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Decision Distribution")
        decisions = summary.get("decision_counts", {})
        if isinstance(decisions, dict) and decisions:
            fig = go.Figure(
                go.Pie(
                    labels=list(decisions.keys()),
                    values=list(decisions.values()),
                    hole=0.38,
                )
            )
            fig.update_layout(margin=dict(t=10, b=10), height=360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    left2, right2 = st.columns(2)
    with left2:
        st.subheader("Top Hazard Hotspots")
        hotspots = risk.get("fault_fracture_hotspots", [])
        if isinstance(hotspots, list) and hotspots:
            df_hotspots = pd.DataFrame(hotspots)
            fig = px.scatter(
                df_hotspots,
                x="inline_m",
                y="crossline_m",
                color="hazard_score",
                size="fault_score",
                hover_data=["lithology", "nearest_fault_id", "fracture_class", "depth_ft"],
                color_continuous_scale="Reds",
                labels={"inline_m": "Inline (m)", "crossline_m": "Crossline (m)"},
            )
            fig.update_layout(margin=dict(t=10, b=10), height=420)
            st.plotly_chart(fig, use_container_width=True)
    with right2:
        st.subheader("Top Reservoir Targets")
        targets = risk.get("reservoir_targets", [])
        if isinstance(targets, list) and targets:
            df_targets = pd.DataFrame(targets)
            fig = px.scatter(
                df_targets,
                x="inline_m",
                y="crossline_m",
                color="target_score",
                size="confidence_score",
                hover_data=["lithology", "reservoir_probability", "nearest_well_id", "depth_ft"],
                color_continuous_scale="Greens",
                labels={"inline_m": "Inline (m)", "crossline_m": "Crossline (m)"},
            )
            fig.update_layout(margin=dict(t=10, b=10), height=420)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Hazard vs Target Score")
    enriched = risk.get("enriched_points")
    if isinstance(enriched, pd.DataFrame) and not enriched.empty:
        sample = enriched.sample(min(2_000, len(enriched)), random_state=42)
        fig = px.scatter(
            sample,
            x="hazard_score",
            y="target_score",
            color="decision",
            hover_data=["lithology", "depth_ft", "nearest_well_id", "fileid", "source_row"],
            opacity=0.65,
        )
        fig.update_layout(
            margin=dict(t=10, b=10),
            height=420,
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    precedents = risk.get("precedents")
    if isinstance(precedents, pd.DataFrame) and not precedents.empty:
        st.subheader("Drilling Precedents Linked to Seismic Hazards")
        left3, right3 = st.columns(2)
        with left3:
            grouped = (
                precedents.groupby("hazard")
                .agg(total_cost=("cost_usd", "sum"), incidents=("incident_id", "count"))
                .reset_index()
                .sort_values("total_cost")
            )
            fig = px.bar(
                grouped,
                x="total_cost",
                y="hazard",
                color="incidents",
                orientation="h",
                labels={"total_cost": "Total Cost (USD)", "hazard": "Hazard"},
                color_continuous_scale="OrRd",
            )
            fig.update_layout(margin=dict(t=10, b=10), height=320)
            st.plotly_chart(fig, use_container_width=True)
        with right3:
            visible_columns = [
                "well_id",
                "hazard",
                "incident_id",
                "incident_well",
                "npt_category",
                "root_cause",
                "hours_lost",
                "cost_usd",
            ]
            st.dataframe(
                precedents[[col for col in visible_columns if col in precedents]],
                use_container_width=True,
                hide_index=True,
                height=320,
            )

    atlas_path = risk.get("atlas_path")
    if isinstance(atlas_path, str) and Path(atlas_path).is_file():
        st.divider()
        st.subheader("Interactive Hazard Atlas")
        st.components.v1.html(
            Path(atlas_path).read_text(encoding="utf-8"),
            height=700,
            scrolling=True,
        )
