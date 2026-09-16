import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(
    os.getenv("DRILLING_DATA_DIR", str(PROJECT_ROOT / "Hackathon" / "use-case-1" / "data"))
).expanduser()

# Corpus A — Narrative JSON DDRs (keyed on well_name)
CORPUS_A_DIR = DATA_DIR / "daily_drilling_reports"

# Corpus B — Tabular CSV DDRs (keyed on well_id)
CORPUS_B_PATH = DATA_DIR / "daily_drilling_reports.csv"

# Operational context CSVs
CSV_PATHS = {
    "well_metadata": DATA_DIR / "well_metadata.csv",
    "well_master": DATA_DIR / "well_master.csv",
    "npt_incident_log": DATA_DIR / "npt_incident_log.csv",
    "bit_records": DATA_DIR / "bit_records.csv",
    "mud_log_summary": DATA_DIR / "mud_log_summary.csv",
    "formation_tops": DATA_DIR / "formation_tops.csv",
    "drilling_plan": DATA_DIR / "drilling_plan.csv",
    "npt_categories": DATA_DIR / "npt_categories.csv",
}

# Benchmarks and thresholds
BENCHMARK_PATHS = {
    "anomaly_thresholds": DATA_DIR / "anomaly_thresholds.csv",
    "drilling_benchmarks": DATA_DIR / "drilling_benchmarks.csv",
    "offset_well_performance": DATA_DIR / "offset_well_performance.csv",
}

# Report config
REPORT_PATHS = {
    "report_templates": DATA_DIR / "report_templates.csv",
    "distribution_list": DATA_DIR / "distribution_list.csv",
}

# Reference documents (markdown versions for indexing)
REFERENCE_DOCS_DIR = DATA_DIR / "reference_docs"

# Narrative text fields used for vector search
CORPUS_A_TEXT_FIELD = "operations_summary"
CORPUS_B_TEXT_FIELD = "remarks"
