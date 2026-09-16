import os
import json
import glob
import csv
from strands import Agent, tool

_data = {}


def _load_data(data_dir):
    if _data.get("loaded") == data_dir:
        return
    reports = []
    for f in sorted(glob.glob(os.path.join(data_dir, "daily_drilling_reports", "*.json"))):
        with open(f) as fh:
            reports.append(json.load(fh))
    _data["json_reports"] = reports

    def load_csv(name):
        with open(os.path.join(data_dir, name)) as fh:
            return list(csv.DictReader(fh))

    _data["npt_incidents"] = load_csv("npt_incident_log.csv")
    _data["well_metadata"] = load_csv("well_metadata.csv")
    _data["well_master"] = load_csv("well_master.csv")
    _data["bit_records"] = load_csv("bit_records.csv")
    _data["anomaly_thresholds"] = load_csv("anomaly_thresholds.csv")
    _data["drilling_benchmarks"] = load_csv("drilling_benchmarks.csv")
    _data["offset_performance"] = load_csv("offset_well_performance.csv")
    _data["loaded"] = data_dir


@tool
def search_reports(well_name: str = "", keyword: str = "") -> str:
    """Search daily drilling reports by well name and/or keyword in the operations summary.

    Args:
        well_name: Filter by well name (partial match). E.g. "Midland State A" or "W-001".
        keyword: Search keyword in operations_summary text.
    """
    results = []
    for r in _data["json_reports"]:
        if well_name and well_name.lower() not in r["well_name"].lower():
            continue
        if keyword and keyword.lower() not in r.get("operations_summary", "").lower():
            continue
        results.append({
            "report_date": r["report_date"],
            "well_name": r["well_name"],
            "depth_ft": r["measured_depth_ft"],
            "rop_fthr": r["rop_fthr"],
            "npt_hrs": r["npt_hrs"],
            "npt_description": r["npt_description"],
            "mud_weight_in_ppg": r["mud_weight_in_ppg"],
            "operations_summary": r["operations_summary"],
        })
    if not results:
        return "No reports found matching the criteria."
    return json.dumps(results[:10], indent=2)


@tool
def get_npt_incidents(well_name: str = "") -> str:
    """Get non-productive time incidents, optionally filtered by well name.

    Args:
        well_name: Filter by well name (partial match). Leave empty for all.
    """
    results = []
    for inc in _data["npt_incidents"]:
        if well_name and well_name.lower() not in inc["well_name"].lower():
            continue
        results.append(inc)
    if not results:
        return "No NPT incidents found."
    return json.dumps(results, indent=2)


@tool
def get_well_info(well_name: str) -> str:
    """Look up well metadata by name. Searches both Corpus A (well_metadata) and Corpus B (well_master).

    Args:
        well_name: Well name or ID to look up (partial match).
    """
    for w in _data["well_metadata"]:
        if well_name.lower() in w["well_name"].lower():
            return json.dumps(w, indent=2)
    for w in _data["well_master"]:
        if well_name.lower() in w.get("well_name", "").lower() or well_name.lower() in w.get("well_id", "").lower():
            return json.dumps(w, indent=2)
    return f"No well found matching '{well_name}'."


@tool
def detect_anomalies(well_name: str, parameter: str = "") -> str:
    """Check drilling parameters against anomaly thresholds for a given well.

    Args:
        well_name: Well name to check.
        parameter: Specific parameter to check (e.g. 'rop_ft_hr', 'mud_weight'). Leave empty for all.
    """
    thresholds = _data["anomaly_thresholds"]
    reports = [r for r in _data["json_reports"] if well_name.lower() in r["well_name"].lower()]
    if not reports:
        return f"No reports found for '{well_name}'."

    param_map = {
        "rop": ("rop_fthr", "rop_ft_hr"),
        "mud_weight": ("mud_weight_in_ppg", "mud_weight_ppg"),
        "wob": ("wob_klbs", "wob_klbs"),
    }

    anomalies = []
    for r in reports[-5:]:
        for thresh in thresholds:
            if parameter and parameter.lower() not in thresh["parameter"].lower():
                continue
            for label, (report_key, _) in param_map.items():
                if thresh["parameter"].startswith(label) or label in thresh["parameter"]:
                    val = r.get(report_key)
                    if val is None:
                        continue
                    val = float(val)
                    if val < float(thresh["low_warning"]):
                        anomalies.append({
                            "date": r["report_date"], "well": r["well_name"],
                            "parameter": thresh["parameter"], "value": val,
                            "threshold": f"low_warning={thresh['low_warning']}",
                            "formation": thresh["formation"],
                        })
                    elif val > float(thresh["high_warning"]):
                        anomalies.append({
                            "date": r["report_date"], "well": r["well_name"],
                            "parameter": thresh["parameter"], "value": val,
                            "threshold": f"high_warning={thresh['high_warning']}",
                            "formation": thresh["formation"],
                        })
    if not anomalies:
        return f"No anomalies detected in the last 5 reports for '{well_name}'."
    return json.dumps(anomalies, indent=2)


@tool
def compare_performance(well_name: str, formation: str = "Wolfcamp A") -> str:
    """Compare a well's drilling performance against offset wells and benchmarks.

    Args:
        well_name: Well name to compare.
        formation: Formation to compare against (default: Wolfcamp A).
    """
    reports = [r for r in _data["json_reports"] if well_name.lower() in r["well_name"].lower()]
    if not reports:
        return f"No reports found for '{well_name}'."

    avg_rop = sum(r["rop_fthr"] for r in reports) / len(reports)
    avg_wob = sum(r["wob_klbs"] for r in reports) / len(reports)

    benchmarks = [b for b in _data["drilling_benchmarks"] if formation.lower() in b["formation"].lower()]
    offsets = [o for o in _data["offset_performance"] if formation.lower() in o["formation"].lower()]

    result = {
        "well": well_name,
        "formation": formation,
        "well_avg_rop": round(avg_rop, 1),
        "well_avg_wob": round(avg_wob, 1),
        "reports_analyzed": len(reports),
    }

    if benchmarks:
        b = benchmarks[0]
        result["benchmark_rop"] = b["benchmark_rop_ft_hr"]
        result["benchmark_wob"] = b["benchmark_wob_klbs"]
        result["rop_vs_benchmark"] = f"{'+' if avg_rop > float(b['benchmark_rop_ft_hr']) else ''}{round(avg_rop - float(b['benchmark_rop_ft_hr']), 1)} ft/hr"

    if offsets:
        offset_avg_rop = sum(float(o["avg_rop_ft_hr"]) for o in offsets) / len(offsets)
        result["offset_avg_rop"] = round(offset_avg_rop, 1)
        result["offset_well_count"] = len(offsets)
        result["rop_vs_offsets"] = f"{'+' if avg_rop > offset_avg_rop else ''}{round(avg_rop - offset_avg_rop, 1)} ft/hr"

    return json.dumps(result, indent=2)


ANALYSIS_DIR = os.path.join(os.path.dirname(__file__), "outputs", "hazard_demo", "analysis")


def _load_risk_data():
    run_dirs = sorted(glob.glob(os.path.join(ANALYSIS_DIR, "run_*")))
    if not run_dirs:
        return
    run_dir = run_dirs[-1]
    for name in ("well_briefs", "fault_fracture_hotspots", "reservoir_targets", "summary", "faults"):
        path = os.path.join(run_dir, f"{name}.json")
        if os.path.exists(path):
            with open(path) as f:
                _data[f"risk_{name}"] = json.load(f)
    for name in ("precedents", "well_screens"):
        path = os.path.join(run_dir, f"{name}.csv")
        if os.path.exists(path):
            with open(path) as f:
                _data[f"risk_{name}"] = list(csv.DictReader(f))


@tool
def get_well_risk_screening(well_id: str = "") -> str:
    """Get seismic risk screening for wells. Shows risk index, risk class, nearby faults, and triggered hazards.

    Args:
        well_id: Well ID to look up (e.g. 'well_05'). Leave empty for all wells ranked by risk.
    """
    briefs = _data.get("risk_well_briefs", [])
    if not briefs:
        return "Risk analysis data not available. Run the subsurface pipeline first."
    results = []
    for b in briefs:
        screen = b["screen"]
        wid = screen["well"]["id"]
        if well_id and well_id.lower() != wid.lower():
            continue
        entry = {
            "well_id": wid,
            "risk_index": screen["risk_index"],
            "risk_class": screen["risk_class"],
            "nearest_fault_id": screen.get("nearest_fault_id"),
            "nearest_fault_distance_m": screen.get("nearest_fault_distance_m"),
            "p90_fracture_intensity": screen.get("p90_fracture_intensity"),
            "hazards": [{"hazard": h["hazard"], "title": h["title"], "measured": h["measured"]} for h in screen.get("hazards", [])],
            "precedent_count": sum(len(p.get("incidents", [])) for p in b.get("precedents", [])),
        }
        results.append(entry)
    if not results:
        return f"No risk data found for well '{well_id}'."
    return json.dumps(results, indent=2)


@tool
def get_risk_hotspots(limit: int = 10) -> str:
    """Get top fault/fracture hazard hotspots from the seismic risk analysis.

    Args:
        limit: Number of hotspots to return (default 10).
    """
    hotspots = _data.get("risk_fault_fracture_hotspots", [])
    if not hotspots:
        return "Risk hotspot data not available."
    results = []
    for h in hotspots[:limit]:
        results.append({
            "hazard_score": h["hazard_score"],
            "target_score": h["target_score"],
            "confidence": h["confidence_score"],
            "decision": h["decision"],
            "lithology": h["lithology"],
            "depth_ft": h["depth_ft"],
            "nearest_fault": h["nearest_fault_id"],
            "fault_distance_m": h["fault_distance_m"],
            "fracture_class": h["fracture_class"],
            "nearest_well": h["nearest_well_id"],
        })
    return json.dumps(results, indent=2)


@tool
def get_drilling_precedents(well_id: str = "", hazard: str = "") -> str:
    """Get drilling precedents linked to seismic hazards. Shows past NPT incidents relevant to detected risks.

    Args:
        well_id: Filter by well ID (e.g. 'well_05'). Leave empty for all.
        hazard: Filter by hazard type (e.g. 'fault_damage_zone'). Leave empty for all.
    """
    prec = _data.get("risk_precedents", [])
    if not prec:
        return "Precedent data not available."
    results = []
    for p in prec:
        if well_id and well_id.lower() != p["well_id"].lower():
            continue
        if hazard and hazard.lower() not in p["hazard"].lower():
            continue
        results.append(p)
    if not results:
        return f"No precedents found for well_id='{well_id}', hazard='{hazard}'."
    return json.dumps(results[:20], indent=2)


SYSTEM_PROMPT = """You are Seismic GPT, the AI agent for the GeoDrill Risk Copilot. You help drilling engineers analyze Daily Drilling Reports (DDRs) and operational data, and provide subsurface risk assessments.

You have access to:
- 75 daily drilling reports (JSON) for 5 Permian Basin wells (W-001 to W-005)
- 192 tabular DDR rows for 9 wells across Permian, Eagle Ford, and Williston basins
- NPT (non-productive time) incident log with root causes and resolutions
- Well metadata for both corpora
- Anomaly thresholds per formation
- Offset well performance and drilling benchmarks
- Seismic risk analysis: 8 screened wells with risk indices, hazard classifications,
  fault/fracture detection, and drilling precedent links (from synthetic catalog)

IMPORTANT RULES:
- Always cite your sources: mention the well name, report date, incident ID, or file when stating facts.
- If the data doesn't support a conclusion, say so clearly — do not fill the gap.
- Be concise but thorough.
- When comparing performance, reference specific benchmark values and offset wells.
- Risk scores are deterministic screening ranks, not calibrated predictions.
- Seismic inputs are generated synthetic catalog data — state this when presenting risk results.
"""


def create_agent(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "Hackathon", "use-case-1", "data")
    _load_data(data_dir)
    _load_risk_data()
    return Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[
            search_reports, get_npt_incidents, get_well_info,
            detect_anomalies, compare_performance,
            get_well_risk_screening, get_risk_hotspots, get_drilling_precedents,
        ],
    )
