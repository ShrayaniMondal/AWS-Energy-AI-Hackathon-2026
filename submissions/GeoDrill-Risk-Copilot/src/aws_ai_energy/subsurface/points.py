from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aws_ai_energy.generate.digital_twin import stable_entity_id, stable_point_id, stable_sample_id

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
    run_id: str
    projectid: int | None
    siteid: int | None
    dataset_uid: str
    dataset_role: str
    dimension_uid: str
    dimension_axis: str
    segmentid: int | None
    segment_uid: str
    file_uid: str
    sample_uid: str
    point_uid: str
    inline_m: float
    crossline_m: float
    depth_m: float
    time_ms: float | None
    horizon_top_id: int | None
    horizon_top_uid: str
    horizon_top_m: float
    horizon_base_id: int | None
    horizon_base_uid: str
    horizon_base_m: float
    structure_depth_m: float | None
    amplitude: float | None
    phase: float | None
    coherence: float
    velocity_m_s: float | None
    impedance_ai: float | None
    fault_id: str
    fault_uid: str
    fault_throw_m: float | None
    fault_likelihood: float
    fracture_intensity: float
    reservoir_probability: float
    well_id: str
    well_uid: str
    well_distance_m: float | None
    lithology: str
    logical_size_bytes: int | None
    artifact_path: str
    source_table: str
    source_file: str
    source_row: int
    synthetic_data: bool


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
    digital_twin: dict[str, Any] | None = None

    @property
    def inline_extent_m(self) -> tuple[float, float]:
        return _extent([point.inline_m for point in self.points])

    @property
    def crossline_extent_m(self) -> tuple[float, float]:
        return _extent([point.crossline_m for point in self.points])

    @property
    def depth_extent_m(self) -> tuple[float, float]:
        return _extent([point.depth_m for point in self.points])


def load_points(
    csv_path: Path | str,
    *,
    catalog_run_id: str | None = None,
    file_lookup: dict[int, dict[str, Any]] | None = None,
) -> list[SeismicPoint]:
    path = Path(csv_path)
    if not path.is_file():
        raise SubsurfaceDataError(f"visualization points CSV not found: {path}")

    files = {} if file_lookup is None else file_lookup
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in REQUIRED_POINT_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise SubsurfaceDataError(f"{path} is missing required columns: {', '.join(missing)}")
        points = [
            _parse_point(path, index, row, catalog_run_id=catalog_run_id, file_lookup=files)
            for index, row in enumerate(reader, start=1)
        ]

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
    file_lookup = _file_lookup(tables)
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
        points=load_points(
            resolved_points,
            catalog_run_id=str(catalog["run"]["id"]) if "run" in catalog else None,
            file_lookup=file_lookup,
        ),
        catalog_path=resolved_catalog,
        catalog_run_id=str(catalog["run"]["id"]) if "run" in catalog else None,
        wells=wells,
        catalog_faults=list(tables.get("faults", [])),
        digital_twin=_load_digital_twin(catalog),
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


def _parse_point(
    path: Path,
    index: int,
    row: dict[str, str],
    *,
    catalog_run_id: str | None,
    file_lookup: dict[int, dict[str, Any]],
) -> SeismicPoint:
    try:
        fileid = int(row["fileid"])
        sampleid = int(row["sampleid"])
        file_row = file_lookup.get(fileid, {})
        run_id = row.get("run_id") or catalog_run_id or ""
        datasetid = int(row["datasetid"])
        projectid = _optional_int(row.get("projectid") or file_row.get("projectid"))
        siteid = _optional_int(row.get("siteid") or file_row.get("siteid"))
        segmentid = _optional_int(row.get("segmentid") or file_row.get("segmentid"))
        dimensionid = row["dimensionid"]
        source_row = _optional_int(row.get("source_row")) or index
        horizon_top_id = _optional_int(row.get("horizon_top_id")) or 2
        horizon_base_id = _optional_int(row.get("horizon_base_id")) or 3
        fault_id = row.get("fault_id", "")
        well_id = row.get("well_id", "")
        artifact_path = (
            row.get("artifact_path") or str(file_row.get("artifact_path", "")) or str(path)
        )
        return SeismicPoint(
            row=index,
            datasetid=datasetid,
            dimensionid=dimensionid,
            fileid=fileid,
            sampleid=sampleid,
            run_id=run_id,
            projectid=projectid,
            siteid=siteid,
            dataset_uid=row.get("dataset_uid") or _stable_id(run_id, "dataset", datasetid),
            dataset_role=row.get("dataset_role", ""),
            dimension_uid=(
                row.get("dimension_uid")
                or ("" if not dimensionid else _stable_id(run_id, "dimension", dimensionid))
            ),
            dimension_axis=row.get("dimension_axis", ""),
            segmentid=segmentid,
            segment_uid=(
                row.get("segment_uid")
                or ("" if segmentid is None else _stable_id(run_id, "segment", segmentid))
            ),
            file_uid=row.get("file_uid") or _stable_id(run_id, "file", fileid),
            sample_uid=row.get("sample_uid") or _stable_sample(run_id, fileid, sampleid),
            point_uid=row.get("point_uid") or _stable_point(run_id, source_row),
            inline_m=float(row["inline_m"]),
            crossline_m=float(row["crossline_m"]),
            depth_m=float(row["depth_m"]),
            time_ms=_optional_float(row.get("time_ms")),
            horizon_top_id=horizon_top_id,
            horizon_top_uid=row.get("horizon_top_uid")
            or _stable_id(run_id, "horizon", horizon_top_id),
            horizon_top_m=float(row["horizon_top_m"]),
            horizon_base_id=horizon_base_id,
            horizon_base_uid=row.get("horizon_base_uid")
            or _stable_id(run_id, "horizon", horizon_base_id),
            horizon_base_m=float(row["horizon_base_m"]),
            structure_depth_m=_optional_float(row.get("structure_depth_m")),
            amplitude=_optional_float(row.get("amplitude")),
            phase=_optional_float(row.get("phase")),
            coherence=float(row["coherence"]),
            velocity_m_s=_optional_float(row.get("velocity_m_s")),
            impedance_ai=_optional_float(row.get("impedance_ai")),
            fault_id=fault_id,
            fault_uid=(
                row.get("fault_uid")
                or ("" if not fault_id else _stable_id(run_id, "fault", fault_id))
            ),
            fault_throw_m=_optional_float(row.get("fault_throw_m")),
            fault_likelihood=float(row["fault_likelihood"]),
            fracture_intensity=float(row["fracture_intensity"]),
            reservoir_probability=float(row["reservoir_probability"]),
            well_id=well_id,
            well_uid=(
                row.get("well_uid") or ("" if not well_id else _stable_id(run_id, "well", well_id))
            ),
            well_distance_m=_optional_float(row.get("well_distance_m")),
            lithology=row["lithology"],
            logical_size_bytes=_optional_int(row.get("logical_size_bytes")),
            artifact_path=artifact_path,
            source_table=row.get("source_table") or "visualization_points",
            source_file=row.get("source_file") or str(path),
            source_row=source_row,
            synthetic_data=_bool_value(row.get("synthetic_data"), default=True),
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


def _file_lookup(tables: Any) -> dict[int, dict[str, Any]]:
    files = tables.get("files", []) if isinstance(tables, dict) else []
    lookup: dict[int, dict[str, Any]] = {}
    if not isinstance(files, list):
        return lookup
    for row in files:
        if isinstance(row, dict) and "id" in row:
            lookup[int(row["id"])] = row
    return lookup


def _load_digital_twin(catalog: dict[str, Any]) -> dict[str, Any] | None:
    path = catalog.get("artifacts", {}).get("digital_twin", {}).get("seed_json")
    if not path:
        return None
    seed_path = Path(str(path))
    if not seed_path.is_file():
        return None
    return _read_json(seed_path)


def _stable_id(run_id: str, entity: str, raw_id: object) -> str:
    if run_id:
        return stable_entity_id(run_id, entity, raw_id)
    token = str(raw_id)
    if token.isdecimal():
        token = f"{int(token):06d}"
    return f"{entity}:{token}"


def _stable_sample(run_id: str, fileid: int, sampleid: int) -> str:
    if run_id:
        return stable_sample_id(run_id, fileid, sampleid)
    return f"sample:{fileid:06d}:{sampleid:06d}"


def _stable_point(run_id: str, source_row: int) -> str:
    if run_id:
        return stable_point_id(run_id, source_row)
    return f"point:{source_row:08d}"


def _optional_float(value: object | None) -> float | None:
    if value is None or value == "":
        return None
    return float(str(value))


def _optional_int(value: object | None) -> int | None:
    if value is None or value == "":
        return None
    return int(str(value))


def _bool_value(value: object | None, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
