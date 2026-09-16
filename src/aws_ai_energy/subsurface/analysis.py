from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aws_ai_energy.subsurface.drilling import (
    DrillingEvidence,
    NptIncident,
    ReferencePassage,
    ThresholdRow,
    find_precedents,
    find_reference_passage,
    summarize_incidents,
    thresholds_for,
)
from aws_ai_energy.subsurface.faults import (
    DetectedFault,
    FaultDetectionConfig,
    FaultScorecard,
    coherence_reference,
    detect_faults,
    score_against_catalog,
)
from aws_ai_energy.subsurface.fractures import (
    FractureCell,
    FractureConfig,
    FractureCorridor,
    find_corridors,
    grid_fracture_cells,
)
from aws_ai_energy.subsurface.hazards import (
    RULES_BY_HAZARD,
    HazardConfig,
    WellHazardScreen,
    screen_well,
)
from aws_ai_energy.subsurface.points import SurveyInputs, WellLocation


@dataclass(frozen=True)
class HazardPrecedents:
    hazard: str
    npt_categories: tuple[str, ...]
    incidents: tuple[NptIncident, ...]
    summary: dict[str, object]
    references: tuple[ReferencePassage, ...]
    missing_references: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class WellBrief:
    screen: WellHazardScreen
    precedents: tuple[HazardPrecedents, ...]


@dataclass(frozen=True)
class AnalysisSettings:
    faults: FaultDetectionConfig = field(default_factory=FaultDetectionConfig)
    fractures: FractureConfig = field(default_factory=FractureConfig)
    hazards: HazardConfig = field(default_factory=HazardConfig)
    max_precedents: int = 5


@dataclass(frozen=True)
class SurveyAnalysis:
    survey: SurveyInputs
    settings: AnalysisSettings
    coherence_reference: float
    faults: list[DetectedFault]
    cells: list[FractureCell]
    corridors: list[FractureCorridor]
    briefs: list[WellBrief]
    scorecard: FaultScorecard | None
    formation: str | None
    thresholds: list[ThresholdRow]
    drilling: DrillingEvidence | None

    def brief_for(self, well_id: str) -> WellBrief | None:
        return next((brief for brief in self.briefs if brief.screen.well.id == well_id), None)

    def ranked_briefs(self) -> list[WellBrief]:
        return sorted(self.briefs, key=lambda brief: brief.screen.risk_index, reverse=True)


def analyze_survey(
    survey: SurveyInputs,
    *,
    wells: list[WellLocation] | None = None,
    drilling: DrillingEvidence | None = None,
    formation: str | None = None,
    settings: AnalysisSettings | None = None,
) -> SurveyAnalysis:
    active = settings or AnalysisSettings()
    targets = survey.wells if wells is None else wells
    coherence_ref = coherence_reference(survey.points)
    faults = detect_faults(survey.points, active.faults)
    cells = grid_fracture_cells(survey.points, active.fractures)
    corridors = find_corridors(cells, faults, targets, active.fractures)
    scorecard = (
        score_against_catalog(
            faults,
            survey.catalog_faults,
            crossline_extent_m=survey.crossline_extent_m,
        )
        if survey.catalog_faults
        else None
    )
    briefs = []
    for well in targets:
        screen = screen_well(
            well,
            survey.points,
            faults,
            coherence_ref=coherence_ref,
            config=active.hazards,
            fracture_config=active.fractures,
        )
        precedents = (
            tuple(
                _precedents_for(hazard.hazard, drilling, formation, active.max_precedents)
                for hazard in screen.hazards
            )
            if drilling is not None
            else ()
        )
        briefs.append(WellBrief(screen=screen, precedents=precedents))

    return SurveyAnalysis(
        survey=survey,
        settings=active,
        coherence_reference=round(coherence_ref, 4),
        faults=faults,
        cells=cells,
        corridors=corridors,
        briefs=briefs,
        scorecard=scorecard,
        formation=formation,
        thresholds=thresholds_for(drilling, formation) if drilling and formation else [],
        drilling=drilling,
    )


def to_jsonable(value: Any) -> Any:
    """Convert analysis dataclasses into JSON-ready structures."""

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: to_jsonable(getattr(value, item.name)) for item in dataclasses.fields(value)
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def analysis_summary(analysis: SurveyAnalysis) -> dict[str, Any]:
    ranked = analysis.ranked_briefs()
    return {
        "catalog_run_id": analysis.survey.catalog_run_id,
        "points_path": str(analysis.survey.points_path),
        "points": len(analysis.survey.points),
        "faults_detected": len(analysis.faults),
        "fracture_cells_high": sum(1 for cell in analysis.cells if cell.fracture_class == "high"),
        "fracture_corridors": len(analysis.corridors),
        "wells_screened": len(analysis.briefs),
        "highest_risk_well": None if not ranked else ranked[0].screen.well.id,
        "highest_risk_index": None if not ranked else ranked[0].screen.risk_index,
        "fault_detection_recall": None if analysis.scorecard is None else analysis.scorecard.recall,
        "fault_detection_precision": (
            None if analysis.scorecard is None else analysis.scorecard.precision
        ),
        "formation": analysis.formation,
        "thresholds_found": len(analysis.thresholds),
        "drilling_data_dir": None if analysis.drilling is None else str(analysis.drilling.data_dir),
    }


def _precedents_for(
    hazard: str,
    drilling: DrillingEvidence,
    formation: str | None,
    limit: int,
) -> HazardPrecedents:
    rule = RULES_BY_HAZARD[hazard]
    incidents = find_precedents(
        drilling,
        categories=rule.npt_categories,
        root_causes=rule.root_causes,
        formation=formation,
    )
    references = []
    missing = []
    for document, phrase in rule.references:
        passage = find_reference_passage(drilling.data_dir, document, phrase)
        if passage is None:
            missing.append(f"{document}: {phrase!r} not found")
        else:
            references.append(passage)

    scope = f"formation {formation!r}" if formation else "all formations"
    if incidents:
        note = f"{len(incidents)} incident(s) in {', '.join(rule.npt_categories)} for {scope}."
    else:
        note = (
            f"No incidents in {', '.join(rule.npt_categories)} for {scope} in "
            "npt_incident_log.csv; no precedent is claimed."
        )
    return HazardPrecedents(
        hazard=hazard,
        npt_categories=rule.npt_categories,
        incidents=tuple(incidents[:limit]),
        summary=summarize_incidents(incidents),
        references=tuple(references),
        missing_references=tuple(missing),
        note=note,
    )
