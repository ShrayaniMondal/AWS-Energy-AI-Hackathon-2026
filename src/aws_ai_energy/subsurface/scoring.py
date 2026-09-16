from __future__ import annotations

import math
from dataclasses import dataclass

from aws_ai_energy.subsurface.analysis import SurveyAnalysis
from aws_ai_energy.subsurface.faults import fault_score, nearest_fault
from aws_ai_energy.subsurface.fractures import cell_id, classify_intensity
from aws_ai_energy.subsurface.points import SeismicPoint, clamp

FEET_PER_METER = 3.28084
WELL_CONTROL_RADIUS_M = 1_500.0
DECISIONS = ("geomechanics_review", "drilling_candidate", "watch_zone")


@dataclass(frozen=True)
class ScoringConfig:
    """Per-sample screening weights.

    ``hazard_score`` blends fault score, fracture intensity, and proximity to a
    detected fault trace. ``target_score`` favours reservoir probability, low
    hazard, and nearby well control. Both are screening ranks, not predictions.
    """

    hazard_fault_weight: float = 0.45
    hazard_fracture_weight: float = 0.40
    hazard_proximity_weight: float = 0.15
    target_reservoir_weight: float = 0.60
    target_low_hazard_weight: float = 0.25
    target_well_control_weight: float = 0.15
    review_hazard_threshold: float = 0.60
    candidate_target_threshold: float = 0.60
    candidate_max_hazard: float = 0.35


@dataclass(frozen=True)
class PointScore:
    point: SeismicPoint
    depth_ft: float
    fault_score: float
    nearest_fault_id: str | None
    fault_distance_m: float | None
    fracture_cell_id: str
    fracture_class: str
    corridor_id: str | None
    nearest_well_id: str | None
    nearest_well_distance_m: float | None
    hazard_score: float
    target_score: float
    confidence_score: float
    decision: str


def score_points(
    analysis: SurveyAnalysis,
    config: ScoringConfig | None = None,
) -> list[PointScore]:
    settings = config or ScoringConfig()
    cell_size = analysis.settings.fractures.cell_size_m
    corridor_by_cell = {
        member: corridor.id for corridor in analysis.corridors for member in corridor.cell_ids
    }
    wells = analysis.survey.wells
    scores = []
    for point in analysis.survey.points:
        score = fault_score(point, analysis.coherence_reference)
        fault, distance = nearest_fault(analysis.faults, point.inline_m, point.crossline_m)
        proximity = 0.0
        if fault is not None and distance is not None:
            reach = fault.damage_zone_half_width_m + analysis.settings.hazards.damage_zone_buffer_m
            proximity = math.exp(-((distance / reach) ** 2))
        hazard = clamp(
            settings.hazard_fault_weight * score
            + settings.hazard_fracture_weight * point.fracture_intensity
            + settings.hazard_proximity_weight * proximity
        )

        well_id: str | None = None
        well_distance: float | None = None
        for well in wells:
            candidate = math.hypot(point.inline_m - well.inline_m, point.crossline_m - well.crossline_m)
            if well_distance is None or candidate < well_distance:
                well_id, well_distance = well.id, candidate
        well_control = (
            0.0
            if well_distance is None
            else clamp(1.0 - min(well_distance, WELL_CONTROL_RADIUS_M) / WELL_CONTROL_RADIUS_M)
        )
        target = clamp(
            settings.target_reservoir_weight * point.reservoir_probability
            + settings.target_low_hazard_weight * (1.0 - hazard)
            + settings.target_well_control_weight * well_control
        )

        decision = "watch_zone"
        if hazard >= settings.review_hazard_threshold:
            decision = "geomechanics_review"
        elif (
            target >= settings.candidate_target_threshold
            and hazard <= settings.candidate_max_hazard
        ):
            decision = "drilling_candidate"

        confidence = _confidence(
            reservoir_probability=point.reservoir_probability,
            fault_score_value=score,
            fracture_intensity=point.fracture_intensity,
            well_control=well_control,
            has_fault=fault is not None,
        )

        cell = cell_id(
            math.floor(point.inline_m / cell_size),
            math.floor(point.crossline_m / cell_size),
        )
        scores.append(
            PointScore(
                point=point,
                depth_ft=round(point.depth_m * FEET_PER_METER, 1),
                fault_score=round(score, 4),
                nearest_fault_id=None if fault is None else fault.id,
                fault_distance_m=None if distance is None else round(distance, 1),
                fracture_cell_id=cell,
                fracture_class=classify_intensity(
                    point.fracture_intensity, analysis.settings.fractures
                ),
                corridor_id=corridor_by_cell.get(cell),
                nearest_well_id=well_id,
                nearest_well_distance_m=None if well_distance is None else round(well_distance, 1),
                hazard_score=round(hazard, 4),
                target_score=round(target, 4),
                confidence_score=round(confidence, 4),
                decision=decision,
            )
        )
    return scores


def top_scores(scores: list[PointScore], field: str, limit: int) -> list[PointScore]:
    if field not in {"hazard_score", "target_score"}:
        raise ValueError("field must be hazard_score or target_score")
    return sorted(
        scores,
        key=lambda item: (float(getattr(item, field)), -item.point.row),
        reverse=True,
    )[:limit]


def _confidence(
    *,
    reservoir_probability: float,
    fault_score_value: float,
    fracture_intensity: float,
    well_control: float,
    has_fault: bool,
) -> float:
    """Bounded [0, 1] evidence-strength score for the ranking.

    Higher when nearby wells provide ground truth, when a fault has been
    detected, and when attribute signals are decisive rather than ambiguous.
    """
    reservoir_decisiveness = abs(2.0 * reservoir_probability - 1.0)
    fault_decisiveness = abs(2.0 * fault_score_value - 1.0)
    fracture_decisiveness = abs(2.0 * fracture_intensity - 1.0)
    return clamp(
        0.30 * well_control
        + 0.20 * reservoir_decisiveness
        + 0.20 * fault_decisiveness
        + 0.15 * fracture_decisiveness
        + 0.15 * (1.0 if has_fault else 0.0)
    )


def score_row(score: PointScore) -> dict[str, object]:
    point = score.point
    return {
        "row": point.row,
        "datasetid": point.datasetid,
        "dimensionid": point.dimensionid,
        "fileid": point.fileid,
        "sampleid": point.sampleid,
        "inline_m": point.inline_m,
        "crossline_m": point.crossline_m,
        "depth_m": point.depth_m,
        "depth_ft": score.depth_ft,
        "lithology": point.lithology,
        "coherence": point.coherence,
        "fault_likelihood": point.fault_likelihood,
        "fracture_intensity": point.fracture_intensity,
        "reservoir_probability": point.reservoir_probability,
        "fault_score": score.fault_score,
        "nearest_fault_id": score.nearest_fault_id or "",
        "fault_distance_m": "" if score.fault_distance_m is None else score.fault_distance_m,
        "fracture_cell_id": score.fracture_cell_id,
        "fracture_class": score.fracture_class,
        "corridor_id": score.corridor_id or "",
        "nearest_well_id": score.nearest_well_id or "",
        "nearest_well_distance_m": (
            "" if score.nearest_well_distance_m is None else score.nearest_well_distance_m
        ),
        "hazard_score": score.hazard_score,
        "target_score": score.target_score,
        "confidence_score": score.confidence_score,
        "decision": score.decision,
    }
