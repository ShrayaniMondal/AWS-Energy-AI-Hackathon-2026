"""Grounded drilling and seismic-risk agent used by the Streamlit demo.

The production AgentCore runtime lives under ``agentcore_app/``. This module is
the local demo companion: it exposes the teammate-authored tool surface, keeps a
deterministic offline fallback, and can opt into Strands/Bedrock when the
environment is configured.
"""

from __future__ import annotations

import csv
import glob
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:  # pragma: no cover - depends on optional deployment dependencies.
    from strands import Agent as StrandsAgent
    from strands import tool as strands_tool
except ImportError:  # pragma: no cover - covered indirectly by local fallback.
    StrandsAgent = None  # type: ignore[assignment]

    def strands_tool(func: Callable[..., str]) -> Callable[..., str]:
        return func


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "Hackathon" / "use-case-1" / "data"
ANALYSIS_DIR = ROOT / "outputs" / "hazard_demo" / "analysis"
_data: dict[str, Any] = {}
_raw_tools: dict[str, Callable[..., str]] = {}


def _register_tool(func: Callable[..., str]) -> Any:
    _raw_tools[func.__name__] = func
    return strands_tool(func)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row_number, row in enumerate(rows, start=2):
        row.setdefault("_source_file", str(path))
        row.setdefault("_source_row", str(row_number))
    return rows


def _load_data(data_dir: str | os.PathLike[str]) -> None:
    root = Path(data_dir)
    if _data.get("loaded") == str(root):
        return

    reports = []
    for path_name in sorted(glob.glob(str(root / "daily_drilling_reports" / "*.json"))):
        path = Path(path_name)
        with path.open(encoding="utf-8") as handle:
            report = json.load(handle)
        report["_source_file"] = str(path)
        reports.append(report)

    _data.clear()
    _data.update(
        {
            "json_reports": reports,
            "npt_incidents": _read_csv(root / "npt_incident_log.csv"),
            "well_metadata": _read_csv(root / "well_metadata.csv"),
            "well_master": _read_csv(root / "well_master.csv"),
            "bit_records": _read_csv(root / "bit_records.csv"),
            "anomaly_thresholds": _read_csv(root / "anomaly_thresholds.csv"),
            "drilling_benchmarks": _read_csv(root / "drilling_benchmarks.csv"),
            "offset_performance": _read_csv(root / "offset_well_performance.csv"),
            "loaded": str(root),
        }
    )


def _load_risk_data() -> None:
    run_dirs = sorted(path for path in ANALYSIS_DIR.glob("run_*") if path.is_dir())
    if not run_dirs:
        return
    run_dir = run_dirs[-1]
    _data["risk_run_dir"] = str(run_dir)
    for name in (
        "well_briefs",
        "fault_fracture_hotspots",
        "reservoir_targets",
        "summary",
        "faults",
    ):
        path = run_dir / f"{name}.json"
        if path.is_file():
            _data[f"risk_{name}"] = json.loads(path.read_text(encoding="utf-8"))
    for name in ("precedents", "well_screens"):
        path = run_dir / f"{name}.csv"
        if path.is_file():
            _data[f"risk_{name}"] = _read_csv(path)


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


@_register_tool
def search_reports(well_name: str = "", keyword: str = "") -> str:
    """Search daily drilling reports by well name and operations keyword."""

    results = []
    for report in _data.get("json_reports", []):
        if well_name and well_name.lower() not in report.get("well_name", "").lower():
            continue
        if keyword and keyword.lower() not in report.get("operations_summary", "").lower():
            continue
        results.append(
            {
                "report_date": report.get("report_date"),
                "well_name": report.get("well_name"),
                "depth_ft": report.get("measured_depth_ft"),
                "rop_fthr": report.get("rop_fthr"),
                "npt_hrs": report.get("npt_hrs"),
                "npt_description": report.get("npt_description"),
                "mud_weight_in_ppg": report.get("mud_weight_in_ppg"),
                "operations_summary": report.get("operations_summary"),
                "source_file": report.get("_source_file"),
            }
        )
    if not results:
        return "No reports found matching the criteria."
    return _json(results[:10])


@_register_tool
def get_npt_incidents(well_name: str = "") -> str:
    """Get non-productive-time incidents, optionally filtered by well name."""

    results = []
    for incident in _data.get("npt_incidents", []):
        if well_name and well_name.lower() not in incident.get("well_name", "").lower():
            continue
        results.append(incident)
    if not results:
        return "No NPT incidents found."
    return _json(results[:25])


@_register_tool
def get_well_info(well_name: str) -> str:
    """Look up well metadata by well name or well ID."""

    needle = well_name.lower()
    for source in ("well_metadata", "well_master"):
        for well in _data.get(source, []):
            haystacks = (well.get("well_name", ""), well.get("well_id", ""))
            if any(needle in value.lower() for value in haystacks):
                return _json(well)
    return f"No well found matching '{well_name}'."


@_register_tool
def detect_anomalies(well_name: str, parameter: str = "") -> str:
    """Check recent drilling parameters against configured formation thresholds."""

    reports = [
        report
        for report in _data.get("json_reports", [])
        if well_name.lower() in report.get("well_name", "").lower()
    ]
    if not reports:
        return f"No reports found for '{well_name}'."

    param_map = {
        "rop": ("rop_fthr", "rop_ft_hr"),
        "mud_weight": ("mud_weight_in_ppg", "mud_weight_ppg"),
        "wob": ("wob_klbs", "wob_klbs"),
    }
    anomalies = []
    for report in reports[-5:]:
        for threshold in _data.get("anomaly_thresholds", []):
            if parameter and parameter.lower() not in threshold.get("parameter", "").lower():
                continue
            for label, (report_key, _) in param_map.items():
                if label not in threshold.get("parameter", ""):
                    continue
                value = report.get(report_key)
                if value is None:
                    continue
                numeric = float(value)
                low = float(threshold["low_warning"])
                high = float(threshold["high_warning"])
                if numeric < low or numeric > high:
                    threshold_label = "low" if numeric < low else "high"
                    threshold_value = low if numeric < low else high
                    anomalies.append(
                        {
                            "date": report.get("report_date"),
                            "well": report.get("well_name"),
                            "parameter": threshold.get("parameter"),
                            "value": numeric,
                            "threshold": f"{threshold_label}={threshold_value}",
                            "formation": threshold.get("formation"),
                            "source_file": report.get("_source_file"),
                        }
                    )
    if not anomalies:
        return f"No anomalies detected in the last 5 reports for '{well_name}'."
    return _json(anomalies)


@_register_tool
def compare_performance(well_name: str, formation: str = "Wolfcamp A") -> str:
    """Compare drilling performance against offset wells and benchmarks."""

    reports = [
        report
        for report in _data.get("json_reports", [])
        if not well_name or well_name.lower() in report.get("well_name", "").lower()
    ]
    if not reports:
        return f"No reports found for '{well_name}'."

    avg_rop = sum(float(report["rop_fthr"]) for report in reports) / len(reports)
    avg_wob = sum(float(report["wob_klbs"]) for report in reports) / len(reports)
    benchmarks = [
        row
        for row in _data.get("drilling_benchmarks", [])
        if formation.lower() in row.get("formation", "").lower()
    ]
    offsets = [
        row
        for row in _data.get("offset_performance", [])
        if formation.lower() in row.get("formation", "").lower()
    ]
    source_files = sorted(
        {report.get("_source_file") for report in reports if report.get("_source_file")}
    )
    result: dict[str, Any] = {
        "well": well_name or "all JSON DDR wells",
        "formation": formation,
        "well_avg_rop": round(avg_rop, 1),
        "well_avg_wob": round(avg_wob, 1),
        "reports_analyzed": len(reports),
        "source_files": source_files,
    }
    if benchmarks:
        benchmark = benchmarks[0]
        benchmark_rop = float(benchmark["benchmark_rop_ft_hr"])
        result["benchmark_rop"] = benchmark["benchmark_rop_ft_hr"]
        result["benchmark_wob"] = benchmark["benchmark_wob_klbs"]
        result["rop_vs_benchmark"] = round(avg_rop - benchmark_rop, 1)
    if offsets:
        offset_avg_rop = sum(float(row["avg_rop_ft_hr"]) for row in offsets) / len(offsets)
        result["offset_avg_rop"] = round(offset_avg_rop, 1)
        result["offset_well_count"] = len(offsets)
        result["rop_vs_offsets"] = round(avg_rop - offset_avg_rop, 1)
    return _json(result)


@_register_tool
def get_well_risk_screening(well_id: str = "") -> str:
    """Get seismic well risk screening with nearby faults and triggered hazards."""

    briefs = _data.get("risk_well_briefs", [])
    if not briefs:
        return "Risk analysis data not available. Run `make demo` first."
    results = []
    for brief in briefs:
        screen = brief["screen"]
        current_well_id = screen["well"]["id"]
        if well_id and well_id.lower() != current_well_id.lower():
            continue
        results.append(
            {
                "well_id": current_well_id,
                "risk_index": screen["risk_index"],
                "risk_class": screen["risk_class"],
                "nearest_fault_id": screen.get("nearest_fault_id"),
                "nearest_fault_distance_m": screen.get("nearest_fault_distance_m"),
                "p90_fracture_intensity": screen.get("p90_fracture_intensity"),
                "hazards": [
                    {
                        "hazard": hazard["hazard"],
                        "title": hazard["title"],
                        "measured": hazard["measured"],
                    }
                    for hazard in screen.get("hazards", [])
                ],
                "precedent_count": sum(
                    len(precedent.get("incidents", [])) for precedent in brief.get("precedents", [])
                ),
                "analysis_run_dir": _data.get("risk_run_dir"),
            }
        )
    if not results:
        return f"No risk data found for well '{well_id}'."
    return _json(results)


@_register_tool
def get_risk_hotspots(limit: int = 10) -> str:
    """Get top fault/fracture hazard hotspots from the seismic analysis."""

    hotspots = _data.get("risk_fault_fracture_hotspots", [])
    if not hotspots:
        return "Risk hotspot data not available. Run `make demo` first."
    results = [
        {
            "hazard_score": row["hazard_score"],
            "target_score": row["target_score"],
            "confidence": row["confidence_score"],
            "decision": row["decision"],
            "lithology": row["lithology"],
            "depth_ft": row["depth_ft"],
            "nearest_fault": row["nearest_fault_id"],
            "fault_distance_m": row["fault_distance_m"],
            "fracture_class": row["fracture_class"],
            "nearest_well": row["nearest_well_id"],
            "source_row": row.get("source_row"),
            "fileid": row.get("fileid"),
            "artifact_path": row.get("artifact_path"),
        }
        for row in hotspots[:limit]
    ]
    return _json(results)


@_register_tool
def get_drilling_precedents(well_id: str = "", hazard: str = "") -> str:
    """Get drilling precedents linked to detected seismic hazards."""

    precedents = _data.get("risk_precedents", [])
    if not precedents:
        return "Precedent data not available. Run `make demo` first."
    results = []
    for precedent in precedents:
        if well_id and well_id.lower() != precedent.get("well_id", "").lower():
            continue
        if hazard and hazard.lower() not in precedent.get("hazard", "").lower():
            continue
        results.append(precedent)
    if not results:
        return f"No precedents found for well_id='{well_id}', hazard='{hazard}'."
    return _json(results[:20])


SYSTEM_PROMPT = """You are Seismic GPT, the AI agent for the GeoDrill Risk Copilot.
You help drilling engineers analyze daily drilling reports, operational data,
and synthetic seismic risk evidence.

Rules:
- Cite well names, report dates, incident IDs, files, rows, or analysis run IDs.
- State when evidence is synthetic generated seismic data.
- Treat risk scores as deterministic screening ranks, not calibrated predictions.
- Do not join narrative and tabular DDR corpora by well identifier; describe them
  as separate corpora when needed.
"""


class LocalRiskAgent:
    """Small deterministic fallback for offline demos and tests."""

    def __init__(self, init_error: str | None = None) -> None:
        self.init_error = init_error

    def __call__(self, prompt: str) -> str:
        prompt_l = prompt.lower()
        sections = []
        well = _match_well(prompt_l)
        if self.init_error:
            sections.append(
                "Local fallback is active because Strands did not initialize: "
                f"{self.init_error}"
            )
        if any(term in prompt_l for term in ("risk", "seismic", "fault", "fracture", "hazard")):
            sections.append("Seismic risk screening:\n" + _raw_tools["get_well_risk_screening"](""))
            sections.append("Risk hotspots:\n" + _raw_tools["get_risk_hotspots"](5))
        if any(term in prompt_l for term in ("npt", "stuck", "lost", "incident", "cost")):
            sections.append("NPT evidence:\n" + _raw_tools["get_npt_incidents"](well))
        if any(term in prompt_l for term in ("benchmark", "performance", "rop", "wob")):
            sections.append("Performance comparison:\n" + _raw_tools["compare_performance"](well))
        if any(term in prompt_l for term in ("report", "summary", "operation")):
            sections.append("Report search:\n" + _raw_tools["search_reports"](well, ""))
        if not sections:
            sections.append(
                "Ask about NPT incidents, well metadata, drilling performance, "
                "or seismic risk screening. All answers are grounded in local data."
            )
        return "\n\n".join(sections)


def _match_well(prompt_l: str) -> str:
    for source in ("well_metadata", "well_master"):
        for row in _data.get(source, []):
            for key in ("well_name", "well_id"):
                value = row.get(key, "")
                if value and value.lower() in prompt_l:
                    return value
    return ""


def create_agent(data_dir: str | os.PathLike[str] | None = None) -> Any:
    """Create the demo agent.

    Set ``GEODRILL_USE_STRANDS=1`` to route chat calls through Strands/Bedrock.
    Without that flag the app uses the deterministic local agent so demos remain
    resettable even before AWS credentials and Bedrock model access are present.
    """

    _load_data(data_dir or DATA_DIR)
    _load_risk_data()
    use_strands = os.getenv("GEODRILL_USE_STRANDS", "").lower() in {"1", "true", "yes"}
    if StrandsAgent is not None and use_strands:
        try:  # pragma: no cover - requires external runtime configuration.
            return StrandsAgent(
                system_prompt=SYSTEM_PROMPT,
                tools=[
                    search_reports,
                    get_npt_incidents,
                    get_well_info,
                    detect_anomalies,
                    compare_performance,
                    get_well_risk_screening,
                    get_risk_hotspots,
                    get_drilling_precedents,
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on optional runtime.
            return LocalRiskAgent(init_error=str(exc))
    return LocalRiskAgent()
