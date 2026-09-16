from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_POINT_COLUMNS = (
    "datasetid",
    "dimensionid",
    "fileid",
    "sampleid",
    "inline_m",
    "crossline_m",
    "depth_m",
    "horizon_top_m",
    "horizon_base_m",
    "coherence",
    "fault_likelihood",
    "fracture_intensity",
    "reservoir_probability",
    "lithology",
)


class SubsurfaceDataError(ValueError):
    """Raised when survey or drilling inputs are missing or malformed."""


@dataclass(frozen=True)
class SeismicPoint:
    """One interpreted sample from a catalog visualization CSV.

    ``row`` is the 1-based data row (header excluded) so every derived claim can
    cite the exact sample it came from.
    """

    row: int
    datasetid: int
    dimensionid: str
    fileid: int
    sampleid: int
    inline_m: float
    crossline_m: float
    depth_m: float
    horizon_top_m: float
    horizon_base_m: float
    coherence: float
    fault_likelihood: float
    fracture_intensity: float
    reservoir_probability: float
    lithology: str


@dataclass(frozen=True)
class WellLocation:
    id: str
    name: str
    inline_m: float
    crossline_m: float
    target_depth_m: float | None = None


@dataclass(frozen=True)
class SurveyInputs:
    points_path: Path
    points: list[SeismicPoint]
    catalog_path: Path | None
    catalog_run_id: str | None
    wells: list[WellLocation]
    catalog_faults: list[dict[str, Any]]

    @property
    def inline_extent_m(self) -> tuple[float, float]:
        return _extent([point.inline_m for point in self.points])

    @property
    def crossline_extent_m(self) -> tuple[float, float]:
        return _extent([point.crossline_m for point in self.points])

    @property
    def depth_extent_m(self) -> tuple[float, float]:
        return _extent([point.depth_m for point in self.points])


def load_points(csv_path: Path | str) -> list[SeismicPoint]:
    path = Path(csv_path)
    if not path.is_file():
        raise SubsurfaceDataError(f"visualization points CSV not found: {path}")

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in REQUIRED_POINT_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise SubsurfaceDataError(f"{path} is missing required columns: {', '.join(missing)}")
        points = [_parse_point(path, index, row) for index, row in enumerate(reader, start=1)]

    if not points:
        raise SubsurfaceDataError(f"{path} contains no data rows")
    return points


def load_survey(
    *,
    catalog_dir: Path | str | None = None,
    catalog_path: Path | str | None = None,
    points_path: Path | str | None = None,
) -> SurveyInputs:
    """Load survey points plus catalog wells and faults.

    ``catalog_dir`` is a seismic catalog generator output directory whose latest run
    is used; ``catalog_path`` selects a specific run's ``catalog.json`` instead.
    ``points_path`` overrides the catalog's visualization CSV, or stands alone when
    no catalog exists.
    """

    if catalog_dir is None and catalog_path is None and points_path is None:
        raise SubsurfaceDataError("provide a catalog directory or a visualization points CSV")

    catalog: dict[str, Any] = {}
    resolved_catalog: Path | None = None
    resolved_points = Path(points_path) if points_path is not None else None

    if catalog_path is not None:
        resolved_catalog = Path(catalog_path)
        if not resolved_catalog.is_file():
            raise SubsurfaceDataError(f"catalog JSON not found: {resolved_catalog}")
        catalog = _read_json(resolved_catalog)
        if resolved_points is None:
            recorded = str(catalog.get("artifacts", {}).get("visualization_path", ""))
            if not recorded:
                raise SubsurfaceDataError(f"{resolved_catalog} does not record a visualization CSV")
            resolved_points = _resolve_artifact(
                recorded,
                Path(catalog_dir) if catalog_dir is not None else resolved_catalog.parent,
                Path(recorded).name,
            )
    elif catalog_dir is not None:
        root = Path(catalog_dir)
        latest_run_path = root / "metadata" / "latest_run.json"
        if not latest_run_path.is_file():
            raise SubsurfaceDataError(
                f"no catalog run found under {root}; generate one with "
                "`python -m generate.seismic_catalog <dataset_count> --output-dir "
                f"{root}`"
            )
        latest_run = _read_json(latest_run_path)
        resolved_catalog = _resolve_artifact(str(latest_run["metadata_path"]), root, "catalog.json")
        catalog = _read_json(resolved_catalog)
        if resolved_points is None:
            resolved_points = _resolve_artifact(
                str(latest_run["visualization_path"]),
                root,
                Path(str(latest_run["visualization_path"])).name,
            )

    assert resolved_points is not None
    tables = catalog.get("tables", {})
    wells = [
        WellLocation(
            id=str(row["name"]),
            name=str(row["name"]),
            inline_m=float(row["inline_m"]),
            crossline_m=float(row["crossline_m"]),
            target_depth_m=float(row["target_depth_m"]) if "target_depth_m" in row else None,
        )
        for row in tables.get("wells", [])
    ]
    return SurveyInputs(
        points_path=resolved_points,
        points=load_points(resolved_points),
        catalog_path=resolved_catalog,
        catalog_run_id=str(catalog["run"]["id"]) if "run" in catalog else None,
        wells=wells,
        catalog_faults=list(tables.get("faults", [])),
    )


def parse_location(value: str) -> tuple[float, float]:
    """Parse ``INLINE,CROSSLINE`` metres into a coordinate pair."""

    parts = value.split(",")
    if len(parts) != 2:
        raise SubsurfaceDataError(f"location must be INLINE,CROSSLINE in metres, got {value!r}")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError as error:
        raise SubsurfaceDataError(f"location must be numeric, got {value!r}") from error


def percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _parse_point(path: Path, index: int, row: dict[str, str]) -> SeismicPoint:
    try:
        return SeismicPoint(
            row=index,
            datasetid=int(row["datasetid"]),
            dimensionid=row["dimensionid"],
            fileid=int(row["fileid"]),
            sampleid=int(row["sampleid"]),
            inline_m=float(row["inline_m"]),
            crossline_m=float(row["crossline_m"]),
            depth_m=float(row["depth_m"]),
            horizon_top_m=float(row["horizon_top_m"]),
            horizon_base_m=float(row["horizon_base_m"]),
            coherence=float(row["coherence"]),
            fault_likelihood=float(row["fault_likelihood"]),
            fracture_intensity=float(row["fracture_intensity"]),
            reservoir_probability=float(row["reservoir_probability"]),
            lithology=row["lithology"],
        )
    except (TypeError, ValueError) as error:
        raise SubsurfaceDataError(f"{path} data row {index} is malformed: {error}") from error


def _resolve_artifact(recorded: str, root: Path, fallback_name: str) -> Path:
    recorded_path = Path(recorded)
    if recorded_path.is_file():
        return recorded_path
    for candidate in (root / recorded_path.name, root / fallback_name):
        if candidate.is_file():
            return candidate
    raise SubsurfaceDataError(f"catalog artifact not found: {recorded}")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SubsurfaceDataError(f"{path} must contain a JSON object")
    return data


def _extent(values: list[float]) -> tuple[float, float]:
    return (min(values), max(values)) if values else (0.0, 0.0)
