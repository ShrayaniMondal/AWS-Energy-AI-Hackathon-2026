from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from aws_ai_energy.subsurface.points import SubsurfaceDataError

NPT_LOG = "npt_incident_log.csv"
THRESHOLDS = "anomaly_thresholds.csv"
REFERENCE_DIR = "reference_docs"


@dataclass(frozen=True)
class Citation:
    source: str
    locator: str

    def text(self) -> str:
        return f"{self.source} {self.locator}"


@dataclass(frozen=True)
class NptIncident:
    incident_id: str
    well_name: str
    date: str
    depth_ft: float
    formation: str
    npt_category: str
    root_cause: str
    resolution: str
    hours_lost: float
    cost_usd: float
    citation: Citation


@dataclass(frozen=True)
class ThresholdRow:
    parameter: str
    formation: str
    low_warning: str
    low_critical: str
    high_warning: str
    high_critical: str
    unit: str
    citation: Citation


@dataclass(frozen=True)
class ReferencePassage:
    document: str
    heading: str
    line: int
    excerpt: tuple[str, ...]
    citation: Citation


@dataclass(frozen=True)
class DrillingEvidence:
    data_dir: Path
    incidents: tuple[NptIncident, ...]
    thresholds: tuple[ThresholdRow, ...]

    def source_paths(self) -> list[Path]:
        return [self.data_dir / NPT_LOG, self.data_dir / THRESHOLDS]


def load_drilling_evidence(data_dir: Path | str) -> DrillingEvidence:
    """Load the use-case-1 tables that the hazard screen cites."""

    root = Path(data_dir)
    incidents_path = root / NPT_LOG
    thresholds_path = root / THRESHOLDS
    for path in (incidents_path, thresholds_path):
        if not path.is_file():
            raise SubsurfaceDataError(f"drilling evidence file not found: {path}")

    incidents = tuple(
        NptIncident(
            incident_id=row["incident_id"],
            well_name=row["well_name"],
            date=row["date"],
            depth_ft=float(row["depth_ft"]),
            formation=row["formation"],
            npt_category=row["npt_category"],
            root_cause=row["root_cause"],
            resolution=row["resolution"],
            hours_lost=float(row["hours_lost"]),
            cost_usd=float(row["cost_usd"]),
            citation=Citation(NPT_LOG, f"row {index} (incident_id={row['incident_id']})"),
        )
        for index, row in _read_rows(incidents_path)
    )
    thresholds = tuple(
        ThresholdRow(
            parameter=row["parameter"],
            formation=row["formation"],
            low_warning=row["low_warning"],
            low_critical=row["low_critical"],
            high_warning=row["high_warning"],
            high_critical=row["high_critical"],
            unit=row.get("unit", ""),
            citation=Citation(THRESHOLDS, f"row {index} ({row['parameter']}, {row['formation']})"),
        )
        for index, row in _read_rows(thresholds_path)
    )
    return DrillingEvidence(data_dir=root, incidents=incidents, thresholds=thresholds)


def find_precedents(
    evidence: DrillingEvidence,
    *,
    categories: tuple[str, ...],
    root_causes: tuple[str, ...] = (),
    formation: str | None = None,
) -> list[NptIncident]:
    """Incidents in the given NPT categories, root-cause matches and costliest first."""

    matches = [
        incident
        for incident in evidence.incidents
        if incident.npt_category in categories
        and (formation is None or incident.formation.lower() == formation.lower())
    ]
    return sorted(
        matches,
        key=lambda incident: (incident.root_cause not in root_causes, -incident.cost_usd),
    )


def summarize_incidents(incidents: list[NptIncident]) -> dict[str, object]:
    by_root_cause: dict[str, dict[str, float]] = {}
    for incident in incidents:
        bucket = by_root_cause.setdefault(
            incident.root_cause,
            {"incidents": 0.0, "hours_lost": 0.0, "cost_usd": 0.0},
        )
        bucket["incidents"] += 1
        bucket["hours_lost"] += incident.hours_lost
        bucket["cost_usd"] += incident.cost_usd
    return {
        "incidents": len(incidents),
        "hours_lost": round(sum(incident.hours_lost for incident in incidents), 1),
        "cost_usd": round(sum(incident.cost_usd for incident in incidents), 2),
        "by_root_cause": {
            cause: {
                "incidents": int(values["incidents"]),
                "hours_lost": round(values["hours_lost"], 1),
                "cost_usd": round(values["cost_usd"], 2),
            }
            for cause, values in sorted(by_root_cause.items())
        },
    }


def thresholds_for(evidence: DrillingEvidence, formation: str) -> list[ThresholdRow]:
    return [row for row in evidence.thresholds if row.formation.lower() == formation.lower()]


def find_reference_passage(
    data_dir: Path | str,
    document: str,
    phrase: str,
    *,
    max_lines: int = 8,
) -> ReferencePassage | None:
    """Locate a passage in a use-case reference document and cite its line number.

    When the phrase is in a heading, the excerpt is that section's body. Otherwise
    the excerpt is the matching line and the lines that follow it in the same block.
    Returns ``None`` when the document or phrase is absent, so callers can say so.
    """

    path = Path(data_dir) / REFERENCE_DIR / document
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    needle = phrase.lower()
    for index, line in enumerate(lines):
        if needle not in line.lower():
            continue
        heading = line.lstrip("#").strip() if line.startswith("#") else _enclosing_heading(lines, index)
        start = index + 1 if line.startswith("#") else index
        excerpt: list[str] = []
        for body in lines[start:]:
            if body.startswith("#") or (excerpt and not body.strip()):
                break
            if body.strip():
                excerpt.append(body.strip())
            if len(excerpt) >= max_lines:
                break
        return ReferencePassage(
            document=document,
            heading=heading,
            line=index + 1,
            excerpt=tuple(excerpt),
            citation=Citation(f"{REFERENCE_DIR}/{document}", f"line {index + 1} ({heading})"),
        )
    return None


def _enclosing_heading(lines: list[str], index: int) -> str:
    for line in reversed(lines[:index]):
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def _read_rows(path: Path) -> list[tuple[int, dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(enumerate(csv.DictReader(handle), start=1))
