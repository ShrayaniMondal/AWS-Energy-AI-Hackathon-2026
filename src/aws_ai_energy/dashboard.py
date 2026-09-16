"""Chat-driven heatmap builder for the Drilling Report Analysis dashboard.

Converts natural-language feature requests into validated, deterministic heatmap
JSON payloads with full provenance.  Every point is keyed to catalog IDs
(datasetid, fileid, sampleid, source_row) so heatmaps can be filtered by
project, site, dataset, segment, file, and physical artifact path.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DashboardDataError(ValueError):
    """Raised when a request or data source is invalid."""


SUPPORTED_FEATURES: dict[str, tuple[str, ...]] = {
    "wells": ("wells", "well", "well locations", "well positions"),
    "faults": ("faults", "fault", "fault lines", "fault traces"),
    "horizons": ("horizons", "horizon", "horizon tops", "horizon bases"),
    "reservoir_probability": (
        "reservoir probability",
        "reservoir",
        "reservoir prob",
        "reservoir score",
    ),
    "physical_data_provenance": (
        "provenance",
        "physical data provenance",
        "source provenance",
        "data provenance",
        "data source",
        "file provenance",
    ),
}

PROVENANCE_KEYS = ("datasetid", "fileid", "sampleid")


@dataclass(frozen=True)
class FeatureRequest:
    """Validated set of features parsed from a user prompt."""

    features: tuple[str, ...]
    raw_prompt: str


def parse_feature_request(prompt: str) -> FeatureRequest:
    """Parse a natural-language prompt into a validated feature list.

    Raises ``DashboardDataError`` when no supported feature is recognized.
    """
    lower = prompt.lower()
    matched: list[str] = []

    for canonical, aliases in SUPPORTED_FEATURES.items():
        for alias in aliases:
            if alias in lower:
                if canonical not in matched:
                    matched.append(canonical)
                break

    if not matched:
        supported = ", ".join(SUPPORTED_FEATURES)
        raise DashboardDataError(
            f"No supported feature found in request. "
            f"Supported features: {supported}"
        )

    ordered = [f for f in SUPPORTED_FEATURES if f in matched]
    return FeatureRequest(features=tuple(ordered), raw_prompt=prompt)


def build_heatmap_payload(
    points_path: Path | str,
    prompt: str,
    *,
    max_points: int | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, JSON-serializable heatmap payload.

    Reads an enriched-points CSV, filters to the requested features, attaches
    per-point provenance, and returns a payload ready for Streamlit rendering
    or JSON download.

    The same ``points_path`` + ``prompt`` + ``max_points`` always produces
    identical output (deterministic).
    """
    path = Path(points_path)
    if not path.is_file():
        raise DashboardDataError(f"Points file not found: {path}")

    request = parse_feature_request(prompt)
    rows = _read_csv(path)
    total = len(rows)

    if max_points is not None and max_points < total:
        rows = rows[:max_points]

    points = []
    for row in rows:
        point = _build_point(row, request.features)
        points.append(point)

    payload: dict[str, Any] = {
        "features": list(request.features),
        "source": {
            "path": str(path),
            "rows_total": total,
        },
        "points": points,
        "notice": (
            "Synthetic data notice: seismic inputs are generated catalog data. "
            "Risk and target scores are deterministic screening ranks, not "
            "calibrated subsurface predictions."
        ),
    }

    if run_id is not None:
        payload["run_id"] = run_id

    return payload


def find_latest_analysis(base_dir: Path | str) -> Path | None:
    """Find the latest analysis run directory that contains a manifest.

    Scans immediate subdirectories of ``base_dir`` for ``manifest.json``,
    returning the lexicographically last (newest) match, or ``None``.
    """
    base = Path(base_dir)
    if not base.is_dir():
        return None

    candidates = sorted(
        (child for child in base.iterdir() if child.is_dir() and (child / "manifest.json").is_file()),
        key=lambda p: p.name,
    )
    return candidates[-1] if candidates else None


def heatmap_payload_to_json(payload: dict[str, Any], path: Path | str) -> Path:
    """Write a heatmap payload to a JSON file for download."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return out


def _build_point(row: dict[str, str], features: tuple[str, ...]) -> dict[str, Any]:
    """Build a single heatmap point from a CSV row."""
    point: dict[str, Any] = {
        "inline_m": _float(row, "inline_m"),
        "crossline_m": _float(row, "crossline_m"),
        "depth_m": _float(row, "depth_m"),
    }

    if "wells" in features:
        point["nearest_well_id"] = row.get("nearest_well_id", "")
        point["nearest_well_distance_m"] = _float_or_none(row, "nearest_well_distance_m")

    if "faults" in features:
        point["fault_likelihood"] = _float(row, "fault_likelihood")
        point["nearest_fault_id"] = row.get("nearest_fault_id", "")
        point["fault_distance_m"] = _float_or_none(row, "fault_distance_m")

    if "horizons" in features:
        point["horizon_top_m"] = _float(row, "horizon_top_m")
        point["horizon_base_m"] = _float(row, "horizon_base_m")

    if "reservoir_probability" in features:
        point["reservoir_probability"] = _float(row, "reservoir_probability")

    if "physical_data_provenance" in features:
        point["provenance"] = {
            "datasetid": _int(row, "datasetid"),
            "fileid": _int(row, "fileid"),
            "sampleid": _int(row, "sampleid"),
            "source_row": _int(row, "row"),
        }

    return point


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _float(row: dict[str, str], key: str) -> float:
    val = row.get(key, "")
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _float_or_none(row: dict[str, str], key: str) -> float | None:
    val = row.get(key, "")
    if val == "" or val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _int(row: dict[str, str], key: str) -> int:
    val = row.get(key, "")
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0
