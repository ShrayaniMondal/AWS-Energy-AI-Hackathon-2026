from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from aws_ai_energy.subsurface.faults import DetectedFault, nearest_fault
from aws_ai_energy.subsurface.points import SeismicPoint, WellLocation, percentile

FRACTURE_CLASSES = ("low", "moderate", "high")


@dataclass(frozen=True)
class FractureConfig:
    """Map-view gridding and classification for fracture intensity.

    Cells are classified on their P90 fracture intensity, so a cell is ``high``
    when at least one in ten samples in its column reaches ``high_threshold``.
    """

    cell_size_m: float = 100.0
    moderate_threshold: float = 0.35
    high_threshold: float = 0.55
    min_corridor_cells: int = 3
    fault_association_m: float = 250.0
    well_association_m: float = 450.0


@dataclass(frozen=True)
class FractureCell:
    id: str
    ix: int
    iy: int
    inline_center_m: float
    crossline_center_m: float
    point_count: int
    mean_intensity: float
    p90_intensity: float
    max_intensity: float
    fracture_class: str


@dataclass(frozen=True)
class FractureCorridor:
    id: str
    cell_ids: tuple[str, ...]
    cell_count: int
    area_m2: float
    centroid_inline_m: float
    centroid_crossline_m: float
    strike_azimuth_deg: float
    length_m: float
    width_m: float
    mean_p90_intensity: float
    nearest_fault_id: str | None
    nearest_fault_distance_m: float | None
    nearest_well_id: str | None
    nearest_well_distance_m: float | None
    origin: str


def grid_fracture_cells(
    points: list[SeismicPoint],
    config: FractureConfig | None = None,
) -> list[FractureCell]:
    settings = config or FractureConfig()
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for point in points:
        key = (
            math.floor(point.inline_m / settings.cell_size_m),
            math.floor(point.crossline_m / settings.cell_size_m),
        )
        buckets[key].append(point.fracture_intensity)

    cells = []
    for (ix, iy), values in sorted(buckets.items()):
        p90 = percentile(values, 0.9)
        cells.append(
            FractureCell(
                id=cell_id(ix, iy),
                ix=ix,
                iy=iy,
                inline_center_m=round((ix + 0.5) * settings.cell_size_m, 1),
                crossline_center_m=round((iy + 0.5) * settings.cell_size_m, 1),
                point_count=len(values),
                mean_intensity=round(sum(values) / len(values), 4),
                p90_intensity=round(p90, 4),
                max_intensity=round(max(values), 4),
                fracture_class=classify_intensity(p90, settings),
            )
        )
    return cells


def classify_intensity(value: float, config: FractureConfig | None = None) -> str:
    settings = config or FractureConfig()
    if value >= settings.high_threshold:
        return "high"
    if value >= settings.moderate_threshold:
        return "moderate"
    return "low"


def cell_id(ix: int, iy: int) -> str:
    return f"X{ix:03d}Y{iy:03d}"


def find_corridors(
    cells: list[FractureCell],
    faults: list[DetectedFault],
    wells: list[WellLocation] | None = None,
    config: FractureConfig | None = None,
) -> list[FractureCorridor]:
    """Group 8-connected high-intensity cells into corridors and attribute them."""

    settings = config or FractureConfig()
    high = {(cell.ix, cell.iy): cell for cell in cells if cell.fracture_class == "high"}
    seen: set[tuple[int, int]] = set()
    components: list[list[FractureCell]] = []
    for start in sorted(high):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component: list[FractureCell] = []
        while stack:
            ix, iy = stack.pop()
            component.append(high[(ix, iy)])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbour = (ix + dx, iy + dy)
                    if neighbour in high and neighbour not in seen:
                        seen.add(neighbour)
                        stack.append(neighbour)
        if len(component) >= settings.min_corridor_cells:
            components.append(component)

    components.sort(key=lambda group: (-len(group), min(cell.id for cell in group)))
    return [
        _describe_corridor(f"K{index}", component, faults, wells or [], settings)
        for index, component in enumerate(components, start=1)
    ]


def _describe_corridor(
    corridor_id: str,
    component: list[FractureCell],
    faults: list[DetectedFault],
    wells: list[WellLocation],
    settings: FractureConfig,
) -> FractureCorridor:
    weights = [cell.p90_intensity for cell in component]
    total = sum(weights)
    centroid_inline = (
        sum(w * c.inline_center_m for w, c in zip(weights, component, strict=True)) / total
    )
    centroid_crossline = (
        sum(w * c.crossline_center_m for w, c in zip(weights, component, strict=True)) / total
    )

    var_inline = sum(
        w * (c.inline_center_m - centroid_inline) ** 2
        for w, c in zip(weights, component, strict=True)
    )
    var_crossline = sum(
        w * (c.crossline_center_m - centroid_crossline) ** 2
        for w, c in zip(weights, component, strict=True)
    )
    covariance = sum(
        w * (c.inline_center_m - centroid_inline) * (c.crossline_center_m - centroid_crossline)
        for w, c in zip(weights, component, strict=True)
    )
    major_angle = 0.5 * math.atan2(2.0 * covariance, var_crossline - var_inline)
    along = (math.sin(major_angle), math.cos(major_angle))
    across = (math.cos(major_angle), -math.sin(major_angle))
    along_positions = [
        (c.inline_center_m - centroid_inline) * along[0]
        + (c.crossline_center_m - centroid_crossline) * along[1]
        for c in component
    ]
    across_positions = [
        (c.inline_center_m - centroid_inline) * across[0]
        + (c.crossline_center_m - centroid_crossline) * across[1]
        for c in component
    ]

    fault, fault_distance = nearest_fault(faults, centroid_inline, centroid_crossline)
    well, well_distance = _nearest_well(wells, centroid_inline, centroid_crossline)
    if fault_distance is not None and fault_distance <= settings.fault_association_m:
        origin = "fault_damage_zone"
    elif well_distance is not None and well_distance <= settings.well_association_m:
        origin = "near_well"
    else:
        origin = "isolated"

    return FractureCorridor(
        id=corridor_id,
        cell_ids=tuple(sorted(cell.id for cell in component)),
        cell_count=len(component),
        area_m2=round(len(component) * settings.cell_size_m**2, 1),
        centroid_inline_m=round(centroid_inline, 1),
        centroid_crossline_m=round(centroid_crossline, 1),
        strike_azimuth_deg=round(math.degrees(major_angle) % 180.0, 1),
        length_m=round(max(along_positions) - min(along_positions) + settings.cell_size_m, 1),
        width_m=round(max(across_positions) - min(across_positions) + settings.cell_size_m, 1),
        mean_p90_intensity=round(total / len(component), 4),
        nearest_fault_id=None if fault is None else fault.id,
        nearest_fault_distance_m=None if fault_distance is None else round(fault_distance, 1),
        nearest_well_id=None if well is None else well.id,
        nearest_well_distance_m=None if well_distance is None else round(well_distance, 1),
        origin=origin,
    )


def _nearest_well(
    wells: list[WellLocation],
    inline_m: float,
    crossline_m: float,
) -> tuple[WellLocation | None, float | None]:
    best: WellLocation | None = None
    best_distance: float | None = None
    for well in wells:
        distance = math.hypot(well.inline_m - inline_m, well.crossline_m - crossline_m)
        if best_distance is None or distance < best_distance:
            best, best_distance = well, distance
    return best, best_distance
