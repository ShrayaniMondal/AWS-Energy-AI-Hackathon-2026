from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass

from aws_ai_energy.subsurface.faults import DetectedFault, fault_score, nearest_fault
from aws_ai_energy.subsurface.fractures import FractureConfig
from aws_ai_energy.subsurface.points import SeismicPoint, WellLocation, clamp, percentile

RISK_CLASSES = ("low", "moderate", "high", "severe")


@dataclass(frozen=True)
class HazardRule:
    """Screening assumption that links a seismic observation to drilling NPT history.

    These links are engineering judgement for screening, not findings from the
    data. They decide which use-case-1 precedents and reference passages are
    shown next to a seismic observation.
    """

    hazard: str
    title: str
    seismic_trigger: str
    npt_categories: tuple[str, ...]
    root_causes: tuple[str, ...]
    references: tuple[tuple[str, str], ...]
    rationale: str


HAZARD_RULES: tuple[HazardRule, ...] = (
    HazardRule(
        hazard="fault_damage_zone",
        title="Well path inside a fault damage zone",
        seismic_trigger="distance to nearest detected fault <= damage half-width + buffer",
        npt_categories=("lost_circulation", "well_control"),
        root_causes=("natural_fractures", "gas_influx", "formation_pressure_underestimate"),
        references=(
            ("bop_procedures.md", "Kick Detection — Warning Signs"),
            ("mwd_lwd_tool_reference.md", "lost circulation detection"),
        ),
        rationale="Faults can conduct fluid or separate pressure compartments.",
    ),
    HazardRule(
        hazard="fracture_corridor",
        title="High fracture intensity around the well",
        seismic_trigger="P90 fracture intensity within the screening radius >= high threshold",
        npt_categories=("lost_circulation",),
        root_causes=("natural_fractures", "depleted_zone"),
        references=(("mwd_lwd_tool_reference.md", "lost circulation detection"),),
        rationale="Open fractures take mud when ECD approaches the fracture gradient.",
    ),
    HazardRule(
        hazard="permeable_sand",
        title="Permeable channel sand in the section",
        seismic_trigger="channel sand fraction within the screening radius >= sand threshold",
        npt_categories=("stuck_pipe",),
        root_causes=("differential_sticking",),
        references=(("casing_design_reference.md", "differential sticking"),),
        rationale="Overbalance against permeable sand drives differential sticking.",
    ),
    HazardRule(
        hazard="fault_throw_pressure",
        title="Large-throw fault near the well",
        seismic_trigger="nearest fault throw >= throw threshold within the pressure radius",
        npt_categories=("well_control",),
        root_causes=("formation_pressure_underestimate", "gas_influx"),
        references=(("bop_procedures.md", "Shut-In Procedure"),),
        rationale="Juxtaposed fault blocks can hold different pore pressures.",
    ),
)

RULES_BY_HAZARD = {rule.hazard: rule for rule in HAZARD_RULES}


@dataclass(frozen=True)
class HazardConfig:
    radius_m: float = 300.0
    damage_zone_buffer_m: float = 100.0
    sand_fraction_threshold: float = 0.3
    throw_threshold_m: float = 120.0
    pressure_radius_m: float = 400.0
    interval_m: float = 50.0
    fault_score_threshold: float = 0.5


@dataclass(frozen=True)
class TriggeredHazard:
    hazard: str
    title: str
    measured: str


@dataclass(frozen=True)
class HazardInterval:
    depth_top_m: float
    depth_base_m: float
    point_count: int
    dominant_lithology: str
    mean_fault_score: float
    p90_fracture_intensity: float
    channel_sand_fraction: float
    hazards: tuple[str, ...]


@dataclass(frozen=True)
class WellHazardScreen:
    """Seismic screen around one well location.

    ``risk_index`` is a 0-100 screening index built from fixed weights. It ranks
    locations within one survey; it is not calibrated against drilling outcomes.
    """

    well: WellLocation
    radius_m: float
    point_count: int
    nearest_fault_id: str | None
    nearest_fault_distance_m: float | None
    nearest_fault_throw_m: float | None
    p90_fracture_intensity: float | None
    lithology_fractions: dict[str, float]
    risk_index: float
    risk_class: str
    hazards: tuple[TriggeredHazard, ...]
    intervals: tuple[HazardInterval, ...]
    evidence_rows: tuple[int, ...]


def screen_well(
    well: WellLocation,
    points: list[SeismicPoint],
    faults: list[DetectedFault],
    *,
    coherence_ref: float,
    config: HazardConfig | None = None,
    fracture_config: FractureConfig | None = None,
) -> WellHazardScreen:
    settings = config or HazardConfig()
    fracture_settings = fracture_config or FractureConfig()
    nearby = [
        point
        for point in points
        if math.hypot(point.inline_m - well.inline_m, point.crossline_m - well.crossline_m)
        <= settings.radius_m
    ]
    fault, fault_distance = nearest_fault(faults, well.inline_m, well.crossline_m)

    if nearby:
        p90_fracture: float | None = percentile([p.fracture_intensity for p in nearby], 0.9)
        counts = Counter(point.lithology for point in nearby)
        lithology_fractions = {
            name: round(count / len(nearby), 3) for name, count in sorted(counts.items())
        }
    else:
        p90_fracture = None
        lithology_fractions = {}
    sand_fraction = lithology_fractions.get("channel_sand", 0.0)

    hazards: list[TriggeredHazard] = []
    proximity = 0.0
    throw_proximity = 0.0
    if fault is not None and fault_distance is not None:
        reach = fault.damage_zone_half_width_m + settings.damage_zone_buffer_m
        proximity = math.exp(-((fault_distance / reach) ** 2))
        if fault_distance <= reach:
            hazards.append(
                _triggered(
                    "fault_damage_zone",
                    f"{fault_distance:.0f} m from {fault.id} (damage half-width "
                    f"{fault.damage_zone_half_width_m:.0f} m + {settings.damage_zone_buffer_m:.0f} m)",
                )
            )
        if fault.throw_m is not None:
            throw_proximity = clamp(abs(fault.throw_m) / 200.0) * math.exp(
                -((fault_distance / settings.pressure_radius_m) ** 2)
            )
            if (
                abs(fault.throw_m) >= settings.throw_threshold_m
                and fault_distance <= settings.pressure_radius_m
            ):
                hazards.append(
                    _triggered(
                        "fault_throw_pressure",
                        f"{fault.id} throw {fault.throw_m:.0f} m at {fault_distance:.0f} m",
                    )
                )
    if p90_fracture is not None and p90_fracture >= fracture_settings.high_threshold:
        hazards.append(
            _triggered(
                "fracture_corridor",
                f"P90 fracture intensity {p90_fracture:.2f} within {settings.radius_m:.0f} m "
                f"(threshold {fracture_settings.high_threshold:.2f})",
            )
        )
    if nearby and sand_fraction >= settings.sand_fraction_threshold:
        hazards.append(
            _triggered(
                "permeable_sand",
                f"channel sand {sand_fraction:.0%} of {len(nearby)} samples within "
                f"{settings.radius_m:.0f} m",
            )
        )

    fracture_component = 0.0 if p90_fracture is None else clamp((p90_fracture - 0.2) / 0.7)
    risk_index = round(
        40.0 * proximity
        + 30.0 * fracture_component
        + 15.0 * clamp(sand_fraction / 0.5)
        + 15.0 * throw_proximity,
        1,
    )
    strongest = sorted(nearby, key=lambda point: fault_score(point, coherence_ref), reverse=True)
    return WellHazardScreen(
        well=well,
        radius_m=settings.radius_m,
        point_count=len(nearby),
        nearest_fault_id=None if fault is None else fault.id,
        nearest_fault_distance_m=None if fault_distance is None else round(fault_distance, 1),
        nearest_fault_throw_m=None if fault is None else fault.throw_m,
        p90_fracture_intensity=None if p90_fracture is None else round(p90_fracture, 3),
        lithology_fractions=lithology_fractions,
        risk_index=risk_index,
        risk_class=risk_class(risk_index),
        hazards=tuple(hazards),
        intervals=tuple(
            _intervals(nearby, coherence_ref, settings, fracture_settings.high_threshold)
        ),
        evidence_rows=tuple(sorted(point.row for point in strongest[:10])),
    )


def risk_class(risk_index: float) -> str:
    if risk_index >= 75:
        return "severe"
    if risk_index >= 50:
        return "high"
    if risk_index >= 25:
        return "moderate"
    return "low"


def _triggered(hazard: str, measured: str) -> TriggeredHazard:
    return TriggeredHazard(hazard=hazard, title=RULES_BY_HAZARD[hazard].title, measured=measured)


def _intervals(
    nearby: list[SeismicPoint],
    coherence_ref: float,
    settings: HazardConfig,
    fracture_high: float,
) -> list[HazardInterval]:
    bins: dict[int, list[SeismicPoint]] = defaultdict(list)
    for point in nearby:
        bins[math.floor(point.depth_m / settings.interval_m)].append(point)

    intervals = []
    for index in sorted(bins):
        members = bins[index]
        lithologies = Counter(point.lithology for point in members)
        mean_score = sum(fault_score(point, coherence_ref) for point in members) / len(members)
        p90_fracture = percentile([point.fracture_intensity for point in members], 0.9)
        sand_fraction = lithologies.get("channel_sand", 0) / len(members)
        flags = []
        if mean_score >= settings.fault_score_threshold or (
            lithologies.most_common(1)[0][0] == "fault_damage_zone"
        ):
            flags.append("fault_damage_zone")
        if p90_fracture >= fracture_high:
            flags.append("fracture_corridor")
        if sand_fraction >= settings.sand_fraction_threshold:
            flags.append("permeable_sand")
        intervals.append(
            HazardInterval(
                depth_top_m=index * settings.interval_m,
                depth_base_m=(index + 1) * settings.interval_m,
                point_count=len(members),
                dominant_lithology=lithologies.most_common(1)[0][0],
                mean_fault_score=round(mean_score, 3),
                p90_fracture_intensity=round(p90_fracture, 3),
                channel_sand_fraction=round(sand_fraction, 3),
                hazards=tuple(flags),
            )
        )
    return intervals
