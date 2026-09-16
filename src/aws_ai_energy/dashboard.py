from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_FEATURES = (
    "wells",
    "faults",
    "horizons",
    "reservoir_probability",
    "physical_data_provenance",
)

FEATURE_ALIASES = {
    "wells": ("well", "wells", "wellbore", "wellbores"),
    "faults": ("fault", "faults", "fracture", "fractures"),
    "horizons": ("horizon", "horizons", "formation", "formations"),
    "reservoir_probability": ("reservoir", "probability", "target", "prospect"),
    "physical_data_provenance": (
        "provenance",
        "source",
        "sources",
        "lineage",
        "artifact",
        "file",
        "catalog",
    ),
}

NOTICE = (
    "Seismic inputs are synthetic catalog data. Scores are deterministic screening "
    "ranks and every point should retain catalog identifiers, source rows, and "
    "physical artifact provenance when available."
)


class DashboardDataError(ValueError):
    """Raised when dashboard feature requests or source bundles are unsupported."""


@dataclass(frozen=True)
class FeatureRequest:
    prompt: str
    features: tuple[str, ...]


def parse_feature_request(prompt: str) -> FeatureRequest:
    """Convert a user phrase into an explicit supported feature list."""

    normalized = prompt.lower()
    features = tuple(
        feature
        for feature in SUPPORTED_FEATURES
        if any(alias in normalized for alias in FEATURE_ALIASES[feature])
    )
    if not features:
        supported = ", ".join(SUPPORTED_FEATURES)
        raise DashboardDataError(f"Ask for at least one supported feature: {supported}")
    return FeatureRequest(prompt=prompt, features=features)


def build_heatmap_payload(
    points_path: Path | str,
    prompt: str,
    *,
    max_points: int = 2_000,
) -> dict[str, Any]:
    """Build deterministic dashboard JSON from a scored or digital-twin point CSV."""

    if max_points < 1:
        raise DashboardDataError("max_points must be greater than zero")
    path = Path(points_path)
    if not path.is_file():
        raise DashboardDataError(f"points CSV not found: {path}")

    request = parse_feature_request(prompt)
    points: list[dict[str, Any]] = []
    rows_total = 0
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for rows_total, row in enumerate(reader, start=1):
            if len(points) < max_points:
                points.append(_display_point(row, rows_total, request.features))

    return {
        "schema_version": "1.0",
        "features": list(request.features),
        "source": {
            "path": str(path),
            "rows_total": rows_total,
            "rows_returned": len(points),
        },
        "points": points,
        "notice": NOTICE,
    }


def heatmap_payload_to_json(payload: dict[str, Any]) -> str:
    """Serialize dashboard payloads with stable key ordering for exports."""

    return json.dumps(payload, indent=2, sort_keys=True)


def find_latest_analysis(analysis_dir: Path | str) -> Path:
    """Return the lexically latest analysis run directory with a manifest."""

    root = Path(analysis_dir)
    if not root.is_dir():
        raise DashboardDataError(f"analysis directory not found: {root}")
    candidates = [
        path for path in root.iterdir() if path.is_dir() and (path / "manifest.json").is_file()
    ]
    if not candidates:
        raise DashboardDataError(f"no analysis manifest found under {root}")
    return sorted(candidates, key=lambda path: path.name)[-1]


def _display_point(
    row: dict[str, str],
    row_number: int,
    features: tuple[str, ...],
) -> dict[str, Any]:
    source_row = _int_or_text(row.get("source_row") or row.get("row") or row_number)
    payload: dict[str, Any] = {
        "id": row.get("point_uid") or f"row:{source_row}",
        "inline_m": _float_or_text(row.get("inline_m")),
        "crossline_m": _float_or_text(row.get("crossline_m")),
        "depth_m": _float_or_text(row.get("depth_m")),
        "values": {},
        "provenance": _provenance(row, source_row),
    }
    values = payload["values"]
    if not isinstance(values, dict):
        raise DashboardDataError("internal payload error")
    if "reservoir_probability" in features:
        values["reservoir_probability"] = _float_or_text(row.get("reservoir_probability"))
    if "faults" in features:
        values["fault_likelihood"] = _float_or_text(row.get("fault_likelihood"))
        values["nearest_fault_id"] = row.get("nearest_fault_id") or row.get("fault_id") or ""
        values["fault_distance_m"] = _float_or_text(row.get("fault_distance_m"))
    if "wells" in features:
        values["nearest_well_id"] = row.get("nearest_well_id") or row.get("well_id") or ""
        values["nearest_well_distance_m"] = _float_or_text(row.get("nearest_well_distance_m"))
    if "horizons" in features:
        values["horizon_top_m"] = _float_or_text(row.get("horizon_top_m"))
        values["horizon_base_m"] = _float_or_text(row.get("horizon_base_m"))
    if "physical_data_provenance" in features:
        values["artifact_path"] = row.get("artifact_path", "")
        values["source_file"] = row.get("source_file", "")
        values["source_row"] = source_row
    return payload


def _provenance(row: dict[str, str], source_row: int | str) -> dict[str, Any]:
    provenance: dict[str, Any] = {}
    for column in (
        "run_id",
        "projectid",
        "siteid",
        "datasetid",
        "dimensionid",
        "segmentid",
        "fileid",
        "sampleid",
        "artifact_path",
    ):
        value = row.get(column)
        if value not in (None, ""):
            provenance[column] = _int_or_text(value)
    provenance["source_row"] = source_row
    return provenance


def _float_or_text(value: object | None) -> float | str:
    if value is None or value == "":
        return ""
    try:
        return float(str(value))
    except ValueError:
        return str(value)


def _int_or_text(value: object) -> int | str:
    try:
        return int(str(value))
    except ValueError:
        return str(value)
