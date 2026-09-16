from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from aws_ai_energy.subsurface.points import SeismicPoint, clamp, percentile


@dataclass(frozen=True)
class FaultDetectionConfig:
    """Tuning for attribute-based fault detection.

    A sample is a fault candidate when its fault score, the mean of fault
    likelihood and coherence loss, reaches ``score_threshold``. Candidate
    lineaments are found with a weighted Hough vote over map-view lines
    ``inline = intercept + slope * (crossline - reference_crossline)``.
    """

    score_threshold: float = 0.5
    slope_min: float = -0.45
    slope_max: float = 0.45
    slope_step: float = 0.01
    intercept_bin_m: float = 30.0
    band_half_width_m: float = 130.0
    min_support_points: int = 40
    max_faults: int = 12
    throw_window_m: float = 450.0
    min_points_per_side: int = 6
    reference_crossline_m: float | None = None


@dataclass(frozen=True)
class DetectedFault:
    id: str
    intercept_inline_m: float
    slope: float
    reference_crossline_m: float
    crossline_min_m: float
    crossline_max_m: float
    strike_azimuth_deg: float
    length_m: float
    support_points: int
    mean_fault_score: float
    mean_coherence: float
    damage_zone_half_width_m: float
    throw_m: float | None
    throw_sample_groups: int
    evidence_rows: tuple[int, ...]

    def inline_at(self, crossline_m: float) -> float:
        return self.intercept_inline_m + self.slope * (crossline_m - self.reference_crossline_m)

    def horizontal_offset_m(self, inline_m: float, crossline_m: float) -> float:
        """Signed inline offset from the trace; positive is the increasing-inline side."""

        return inline_m - self.inline_at(crossline_m)

    def distance_m(self, inline_m: float, crossline_m: float) -> float:
        """Map-view distance to the finite fault trace."""

        clamped = max(self.crossline_min_m, min(self.crossline_max_m, crossline_m))
        if clamped == crossline_m:
            return abs(self.horizontal_offset_m(inline_m, crossline_m)) / math.hypot(1.0, self.slope)
        return math.hypot(inline_m - self.inline_at(clamped), crossline_m - clamped)

    def trace(self) -> tuple[tuple[float, float], tuple[float, float]]:
        return (
            (self.inline_at(self.crossline_min_m), self.crossline_min_m),
            (self.inline_at(self.crossline_max_m), self.crossline_max_m),
        )


@dataclass(frozen=True)
class FaultMatch:
    catalog_fault_id: int
    detected_fault_id: str | None
    mean_trace_offset_m: float | None
    slope_error: float | None
    catalog_throw_m: float
    detected_throw_m: float | None
    throw_error_m: float | None


@dataclass(frozen=True)
class FaultScorecard:
    """Detection quality against the generator's synthetic fault table."""

    tolerance_m: float
    catalog_faults: int
    detected_faults: int
    matched: int
    recall: float
    precision: float
    matches: tuple[FaultMatch, ...]


def coherence_reference(points: list[SeismicPoint]) -> float:
    """Survey-wide P95 coherence, used as the undisturbed-rock baseline."""

    return max(percentile([point.coherence for point in points], 0.95), 1e-6)


def fault_score(point: SeismicPoint, coherence_ref: float) -> float:
    coherence_loss = clamp((coherence_ref - point.coherence) / coherence_ref)
    return clamp(0.5 * point.fault_likelihood + 0.5 * coherence_loss)


def detect_faults(
    points: list[SeismicPoint],
    config: FaultDetectionConfig | None = None,
) -> list[DetectedFault]:
    settings = config or FaultDetectionConfig()
    if not points:
        return []

    crosslines = [point.crossline_m for point in points]
    reference = settings.reference_crossline_m
    if reference is None:
        reference = (min(crosslines) + max(crosslines)) / 2.0

    coherence_ref = coherence_reference(points)
    remaining = [
        (point, score)
        for point in points
        if (score := fault_score(point, coherence_ref)) >= settings.score_threshold
    ]
    slope_count = round((settings.slope_max - settings.slope_min) / settings.slope_step) + 1
    slopes = [settings.slope_min + index * settings.slope_step for index in range(slope_count)]

    lines: list[tuple[float, float, list[tuple[SeismicPoint, float]]]] = []
    while remaining and len(lines) < settings.max_faults:
        peak = _hough_peak(remaining, slopes, reference, settings.intercept_bin_m)
        if peak is None:
            break
        intercept, slope = peak
        support: list[tuple[SeismicPoint, float]] = []
        for _ in range(3):
            support = [
                (point, score)
                for point, score in remaining
                if abs(point.inline_m - intercept - slope * (point.crossline_m - reference))
                <= settings.band_half_width_m
            ]
            if len(support) < 2:
                break
            intercept, slope = _weighted_line_fit(support, reference, fallback=(intercept, slope))

        if len(support) < settings.min_support_points:
            break
        lines.append((intercept, slope, support))
        support_rows = {point.row for point, _ in support}
        remaining = [(point, score) for point, score in remaining if point.row not in support_rows]

    lines.sort(key=lambda line: line[0])
    owners = _nearest_line_owner(points, [(line[0], line[1]) for line in lines], reference)
    return [
        _describe_fault(
            f"F{index}",
            intercept,
            slope,
            reference,
            support,
            [point for point in points if owners.get(point.row) == index - 1],
            settings,
        )
        for index, (intercept, slope, support) in enumerate(lines, start=1)
    ]


def nearest_fault(
    faults: list[DetectedFault],
    inline_m: float,
    crossline_m: float,
) -> tuple[DetectedFault | None, float | None]:
    best: DetectedFault | None = None
    best_distance: float | None = None
    for fault in faults:
        distance = fault.distance_m(inline_m, crossline_m)
        if best_distance is None or distance < best_distance:
            best, best_distance = fault, distance
    return best, best_distance


def score_against_catalog(
    detected: list[DetectedFault],
    catalog_faults: list[dict[str, Any]],
    *,
    crossline_extent_m: tuple[float, float],
    tolerance_m: float = 80.0,
) -> FaultScorecard:
    """Compare detected traces to the synthetic catalog's fault table."""

    samples = [
        crossline_extent_m[0],
        (crossline_extent_m[0] + crossline_extent_m[1]) / 2.0,
        crossline_extent_m[1],
    ]
    used: set[str] = set()
    matches: list[FaultMatch] = []
    for truth in catalog_faults:
        truth_intercept = float(truth["inline_intercept_m"])
        truth_slope = float(truth["slope"])
        truth_reference = float(truth["crossline_reference_m"])
        best: DetectedFault | None = None
        best_offset: float | None = None
        for fault in detected:
            if fault.id in used:
                continue
            offset = sum(
                abs(
                    fault.inline_at(crossline)
                    - (truth_intercept + truth_slope * (crossline - truth_reference))
                )
                for crossline in samples
            ) / len(samples)
            if best_offset is None or offset < best_offset:
                best, best_offset = fault, offset

        truth_throw = float(truth["throw_m"])
        if best is None or best_offset is None or best_offset > tolerance_m:
            matches.append(
                FaultMatch(int(truth["id"]), None, best_offset, None, truth_throw, None, None)
            )
            continue
        used.add(best.id)
        matches.append(
            FaultMatch(
                catalog_fault_id=int(truth["id"]),
                detected_fault_id=best.id,
                mean_trace_offset_m=round(best_offset, 1),
                slope_error=round(best.slope - truth_slope, 3),
                catalog_throw_m=round(truth_throw, 1),
                detected_throw_m=best.throw_m,
                throw_error_m=None if best.throw_m is None else round(best.throw_m - truth_throw, 1),
            )
        )

    matched = len(used)
    return FaultScorecard(
        tolerance_m=tolerance_m,
        catalog_faults=len(catalog_faults),
        detected_faults=len(detected),
        matched=matched,
        recall=round(matched / len(catalog_faults), 3) if catalog_faults else 0.0,
        precision=round(matched / len(detected), 3) if detected else 0.0,
        matches=tuple(matches),
    )


def _nearest_line_owner(
    points: list[SeismicPoint],
    lines: list[tuple[float, float]],
    reference: float,
) -> dict[int, int]:
    owners: dict[int, int] = {}
    if not lines:
        return owners
    for point in points:
        distances = [
            abs(point.inline_m - intercept - slope * (point.crossline_m - reference))
            / math.hypot(1.0, slope)
            for intercept, slope in lines
        ]
        owners[point.row] = distances.index(min(distances))
    return owners


def _hough_peak(
    candidates: list[tuple[SeismicPoint, float]],
    slopes: list[float],
    reference: float,
    bin_m: float,
) -> tuple[float, float] | None:
    votes: dict[tuple[int, int], float] = defaultdict(float)
    for point, score in candidates:
        offset = point.crossline_m - reference
        for slope_index, slope in enumerate(slopes):
            intercept_bin = math.floor((point.inline_m - slope * offset) / bin_m)
            votes[(slope_index, intercept_bin)] += score
    if not votes:
        return None

    best_key: tuple[int, int] | None = None
    best_vote = 0.0
    for (slope_index, intercept_bin), vote in votes.items():
        smoothed = (
            votes.get((slope_index, intercept_bin - 1), 0.0)
            + vote
            + votes.get((slope_index, intercept_bin + 1), 0.0)
        )
        if smoothed > best_vote:
            best_key, best_vote = (slope_index, intercept_bin), smoothed
    if best_key is None:
        return None
    return (best_key[1] + 0.5) * bin_m, slopes[best_key[0]]


def _weighted_line_fit(
    support: list[tuple[SeismicPoint, float]],
    reference: float,
    *,
    fallback: tuple[float, float],
) -> tuple[float, float]:
    weight_sum = sum(score for _, score in support)
    mean_y = sum(score * (point.crossline_m - reference) for point, score in support) / weight_sum
    mean_x = sum(score * point.inline_m for point, score in support) / weight_sum
    covariance = sum(
        score * (point.crossline_m - reference - mean_y) * (point.inline_m - mean_x)
        for point, score in support
    )
    variance = sum(score * (point.crossline_m - reference - mean_y) ** 2 for point, score in support)
    if variance <= 1e-9:
        return fallback
    slope = covariance / variance
    return mean_x - slope * mean_y, slope


def _describe_fault(
    fault_id: str,
    intercept: float,
    slope: float,
    reference: float,
    support: list[tuple[SeismicPoint, float]],
    block_points: list[SeismicPoint],
    settings: FaultDetectionConfig,
) -> DetectedFault:
    crosslines = [point.crossline_m for point, _ in support]
    crossline_min, crossline_max = min(crosslines), max(crosslines)
    offsets = [
        abs(point.inline_m - intercept - slope * (point.crossline_m - reference))
        for point, _ in support
    ]
    half_width = percentile(offsets, 0.9) / math.hypot(1.0, slope)
    throw, groups = _estimate_throw(
        block_points,
        intercept,
        slope,
        reference,
        exclusion_m=half_width,
        settings=settings,
    )
    strongest = sorted(support, key=lambda item: item[1], reverse=True)[:10]
    return DetectedFault(
        id=fault_id,
        intercept_inline_m=round(intercept, 1),
        slope=round(slope, 4),
        reference_crossline_m=round(reference, 1),
        crossline_min_m=round(crossline_min, 1),
        crossline_max_m=round(crossline_max, 1),
        strike_azimuth_deg=round(math.degrees(math.atan2(slope, 1.0)) % 180.0, 1),
        length_m=round((crossline_max - crossline_min) * math.hypot(1.0, slope), 1),
        support_points=len(support),
        mean_fault_score=round(sum(score for _, score in support) / len(support), 3),
        mean_coherence=round(sum(point.coherence for point, _ in support) / len(support), 3),
        damage_zone_half_width_m=round(half_width, 1),
        throw_m=throw,
        throw_sample_groups=groups,
        evidence_rows=tuple(sorted(point.row for point, _ in strongest)),
    )


def _estimate_throw(
    points: list[SeismicPoint],
    intercept: float,
    slope: float,
    reference: float,
    *,
    exclusion_m: float,
    settings: FaultDetectionConfig,
) -> tuple[float | None, int]:
    """Estimate vertical offset of the reservoir top across the trace.

    Only samples whose nearest detected trace is this fault are used, so offsets
    from neighbouring fault blocks do not leak into the estimate. Samples are
    grouped by catalog dimension because each dimension carries its own depth bias. Within a group the horizon top is fitted as a quadratic in
    offset plus a step at the trace; the step is the throw. Groups are combined
    with the median.
    """

    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for point in points:
        offset = point.inline_m - intercept - slope * (point.crossline_m - reference)
        if exclusion_m <= abs(offset) <= settings.throw_window_m:
            groups[point.dimensionid].append((offset, point.horizon_top_m))

    throws: list[float] = []
    for samples in groups.values():
        hanging = sum(1 for offset, _ in samples if offset > 0)
        if min(hanging, len(samples) - hanging) < settings.min_points_per_side:
            continue
        design = [
            [1.0, offset / 100.0, (offset / 100.0) ** 2, 1.0 if offset > 0 else 0.0]
            for offset, _ in samples
        ]
        solution = _least_squares(design, [depth for _, depth in samples])
        if solution is not None:
            throws.append(solution[3])

    if not throws:
        return None, 0
    return round(percentile(throws, 0.5), 1), len(throws)


def _least_squares(design: list[list[float]], target: list[float]) -> list[float] | None:
    size = len(design[0])
    normal = [[0.0] * (size + 1) for _ in range(size)]
    for row, value in zip(design, target, strict=True):
        for i in range(size):
            normal[i][size] += row[i] * value
            for j in range(size):
                normal[i][j] += row[i] * row[j]

    for column in range(size):
        pivot = max(range(column, size), key=lambda index: abs(normal[index][column]))
        if abs(normal[pivot][column]) < 1e-9:
            return None
        normal[column], normal[pivot] = normal[pivot], normal[column]
        for index in range(size):
            if index != column:
                factor = normal[index][column] / normal[column][column]
                for j in range(column, size + 1):
                    normal[index][j] -= factor * normal[column][j]
    return [normal[index][size] / normal[index][index] for index in range(size)]
