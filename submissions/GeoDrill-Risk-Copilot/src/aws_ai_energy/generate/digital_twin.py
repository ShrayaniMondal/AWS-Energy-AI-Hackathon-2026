from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DIGITAL_TWIN_SCHEMA_VERSION = "1.0"
SYNTHETIC_NOTICE = (
    "Synthetic seismic catalog seed. Reservoir probability, fault likelihood, "
    "fracture intensity, hazards, and targets are deterministic screening signals, "
    "not calibrated predictions or field measurements."
)

POINT_METRIC_FIELDS = (
    "amplitude",
    "coherence",
    "fault_likelihood",
    "fracture_intensity",
    "reservoir_probability",
    "depth_m",
)

DIGITAL_TWIN_POINT_COLUMNS = (
    "point_uid",
    "run_id",
    "projectid",
    "siteid",
    "datasetid",
    "dataset_uid",
    "dataset_role",
    "dimensionid",
    "dimension_uid",
    "dimension_axis",
    "segmentid",
    "segment_uid",
    "fileid",
    "file_uid",
    "sampleid",
    "sample_uid",
    "inline_m",
    "crossline_m",
    "depth_m",
    "time_ms",
    "horizon_top_id",
    "horizon_top_uid",
    "horizon_top_m",
    "horizon_base_id",
    "horizon_base_uid",
    "horizon_base_m",
    "structure_depth_m",
    "amplitude",
    "phase",
    "coherence",
    "velocity_m_s",
    "impedance_ai",
    "fault_id",
    "fault_uid",
    "fault_throw_m",
    "fault_likelihood",
    "fracture_intensity",
    "reservoir_probability",
    "well_id",
    "well_uid",
    "well_distance_m",
    "lithology",
    "logical_size_bytes",
    "artifact_path",
    "source_table",
    "source_file",
    "source_row",
    "synthetic_data",
)


@dataclass
class MetricAccumulator:
    count: int = 0
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None

    def add(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    def as_dict(self) -> dict[str, float | int | None]:
        return {
            "count": self.count,
            "min": None if self.minimum is None else round(self.minimum, 6),
            "max": None if self.maximum is None else round(self.maximum, 6),
            "mean": None if self.count == 0 else round(self.total / self.count, 6),
        }


def stable_entity_id(run_id: str, entity: str, raw_id: object) -> str:
    """Build a stable, run-scoped identifier for catalog and interpreted entities."""

    return f"{run_id}:{entity}:{_stable_token(raw_id)}"


def stable_sample_id(run_id: str, fileid: int, sampleid: int) -> str:
    return f"{run_id}:sample:{fileid:06d}:{sampleid:06d}"


def stable_point_id(run_id: str, source_row: int) -> str:
    return f"{run_id}:point:{source_row:08d}"


def write_digital_twin_artifacts(
    metadata: dict[str, Any],
    run_dir: Path,
    visualization_path: Path,
) -> dict[str, Any]:
    """Write restartable JSON/CSV digital-twin seed endpoints for one catalog run."""

    run_id = str(metadata["run"]["id"])
    output_dir = run_dir / "digital_twin"
    output_dir.mkdir(parents=True, exist_ok=False)

    points_csv = output_dir / "digital_twin_points.csv"
    metrics_json = output_dir / "digital_twin_metrics.json"
    layers_geojson = output_dir / "digital_twin_layers.geojson"
    seed_json = output_dir / "digital_twin_seed.json"
    manifest_json = output_dir / "digital_twin_manifest.json"

    file_lookup = _file_lookup(metadata)
    metrics = _write_points_endpoint(
        run_id=run_id,
        visualization_path=visualization_path,
        points_csv=points_csv,
        file_lookup=file_lookup,
        metadata=metadata,
    )
    layers = _build_layers_geojson(metadata, run_id)
    endpoints = {
        "seed": {"format": "json", "path": str(seed_json)},
        "points": {
            "format": "csv",
            "path": str(points_csv),
            "rows": metrics["row_counts"]["digital_twin_points"],
        },
        "metrics": {"format": "json", "path": str(metrics_json)},
        "layers": {"format": "geojson", "path": str(layers_geojson)},
        "catalog": {"format": "json", "path": str(metadata["artifacts"]["metadata_path"])},
        "tables": metadata["artifacts"].get("table_exports", {}),
    }
    seed = _build_seed(metadata, run_id, endpoints, metrics)

    _write_json(metrics_json, metrics)
    _write_json(layers_geojson, layers)
    _write_json(seed_json, seed)
    manifest = _build_manifest(
        run_id=run_id,
        visualization_path=visualization_path,
        outputs={
            "seed_json": seed_json,
            "points_csv": points_csv,
            "metrics_json": metrics_json,
            "layers_geojson": layers_geojson,
        },
    )
    _write_json(manifest_json, manifest)

    return {
        "schema_version": DIGITAL_TWIN_SCHEMA_VERSION,
        "seed_json": str(seed_json),
        "points_csv": str(points_csv),
        "metrics_json": str(metrics_json),
        "layers_geojson": str(layers_geojson),
        "manifest_json": str(manifest_json),
        "synthetic_data": True,
        "notice": SYNTHETIC_NOTICE,
        "endpoint_names": ["seed", "points", "metrics", "layers", "catalog", "tables"],
    }


def build_digital_twin_point_record(
    row: dict[str, str],
    *,
    run_id: str,
    source_row: int,
    source_file: Path,
    file_lookup: dict[int, dict[str, Any]],
) -> dict[str, object]:
    """Enrich one visualization row with stable IDs and provenance."""

    fileid = _int_value(row.get("fileid"), "fileid")
    sampleid = _int_value(row.get("sampleid"), "sampleid")
    file_row = file_lookup.get(fileid, {})
    datasetid = _int_value(row.get("datasetid") or file_row.get("datasetid"), "datasetid")
    projectid = _int_value(row.get("projectid") or file_row.get("projectid"), "projectid")
    siteid = _int_value(row.get("siteid") or file_row.get("siteid"), "siteid")
    segmentid = _int_value(row.get("segmentid") or file_row.get("segmentid"), "segmentid")
    dimensionid = _string_value(row.get("dimensionid"))
    fault_id = _string_value(row.get("fault_id"))
    well_id = _string_value(row.get("well_id"))
    horizon_top_id = _int_value(row.get("horizon_top_id") or 2, "horizon_top_id")
    horizon_base_id = _int_value(row.get("horizon_base_id") or 3, "horizon_base_id")

    artifact_path = _string_value(row.get("artifact_path") or file_row.get("artifact_path"))
    if not artifact_path:
        artifact_path = str(source_file)

    record: dict[str, object] = {
        "point_uid": stable_point_id(run_id, source_row),
        "run_id": run_id,
        "projectid": projectid,
        "siteid": siteid,
        "datasetid": datasetid,
        "dataset_uid": stable_entity_id(run_id, "dataset", datasetid),
        "dataset_role": _string_value(row.get("dataset_role")),
        "dimensionid": dimensionid,
        "dimension_uid": (
            "" if not dimensionid else stable_entity_id(run_id, "dimension", dimensionid)
        ),
        "dimension_axis": _string_value(row.get("dimension_axis")),
        "segmentid": segmentid,
        "segment_uid": stable_entity_id(run_id, "segment", segmentid),
        "fileid": fileid,
        "file_uid": stable_entity_id(run_id, "file", fileid),
        "sampleid": sampleid,
        "sample_uid": stable_sample_id(run_id, fileid, sampleid),
        "horizon_top_id": horizon_top_id,
        "horizon_top_uid": stable_entity_id(run_id, "horizon", horizon_top_id),
        "horizon_base_id": horizon_base_id,
        "horizon_base_uid": stable_entity_id(run_id, "horizon", horizon_base_id),
        "fault_id": fault_id,
        "fault_uid": "" if not fault_id else stable_entity_id(run_id, "fault", fault_id),
        "well_id": well_id,
        "well_uid": "" if not well_id else stable_entity_id(run_id, "well", well_id),
        "artifact_path": artifact_path,
        "source_table": _string_value(row.get("source_table") or "visualization_points"),
        "source_file": _string_value(row.get("source_file") or source_file),
        "source_row": source_row,
        "synthetic_data": _bool_value(row.get("synthetic_data"), default=True),
    }
    for column in DIGITAL_TWIN_POINT_COLUMNS:
        if column not in record:
            record[column] = _string_value(row.get(column))
    for column, value in row.items():
        if column not in record:
            record[column] = value
    return record


def load_digital_twin_seed(path: Path | str) -> dict[str, Any]:
    """Load a digital-twin seed JSON document or a catalog that points to one."""

    candidate = Path(path)
    data = _read_json(candidate)
    if "digital_twin" in data:
        return data
    seed_path = data.get("artifacts", {}).get("digital_twin", {}).get("seed_json")
    if not seed_path:
        raise ValueError(f"{candidate} does not contain a digital-twin endpoint")
    return _read_json(Path(str(seed_path)))


def _write_points_endpoint(
    *,
    run_id: str,
    visualization_path: Path,
    points_csv: Path,
    file_lookup: dict[int, dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    stats = {field: MetricAccumulator() for field in POINT_METRIC_FIELDS}
    extents = {
        "inline_m": MetricAccumulator(),
        "crossline_m": MetricAccumulator(),
        "depth_m": MetricAccumulator(),
    }
    row_count = 0
    provenance_complete = 0
    synthetic_rows = 0
    lithology_counts: dict[str, int] = {}

    with visualization_path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = _point_fieldnames(reader.fieldnames or [])
        with points_csv.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=fieldnames)
            writer.writeheader()
            for source_row, row in enumerate(reader, start=1):
                record = build_digital_twin_point_record(
                    row,
                    run_id=run_id,
                    source_row=source_row,
                    source_file=visualization_path,
                    file_lookup=file_lookup,
                )
                writer.writerow(_csv_record(record))
                row_count += 1
                if record["artifact_path"] and record["source_row"]:
                    provenance_complete += 1
                if record["synthetic_data"] is True:
                    synthetic_rows += 1
                lithology = str(record.get("lithology", ""))
                lithology_counts[lithology] = lithology_counts.get(lithology, 0) + 1
                for field in POINT_METRIC_FIELDS:
                    _add_float(stats[field], record.get(field))
                for field in extents:
                    _add_float(extents[field], record.get(field))

    return {
        "schema_version": DIGITAL_TWIN_SCHEMA_VERSION,
        "run_id": run_id,
        "synthetic_data": True,
        "notice": SYNTHETIC_NOTICE,
        "row_counts": {
            **dict(metadata.get("row_counts", {})),
            "digital_twin_points": row_count,
        },
        "entity_counts": {
            name: len(rows)
            for name, rows in metadata.get("tables", {}).items()
            if isinstance(rows, list)
        },
        "point_metrics": {field: stats[field].as_dict() for field in POINT_METRIC_FIELDS},
        "extents_m": {field: extents[field].as_dict() for field in extents},
        "lithology_counts": dict(sorted(lithology_counts.items())),
        "provenance": {
            "points_with_artifact_path_and_source_row": provenance_complete,
            "synthetic_rows": synthetic_rows,
            "source_file": str(visualization_path),
        },
    }


def _build_seed(
    metadata: dict[str, Any],
    run_id: str,
    endpoints: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    tables = metadata.get("tables", {})
    return {
        "schema_version": DIGITAL_TWIN_SCHEMA_VERSION,
        "digital_twin": {
            "id": stable_entity_id(run_id, "digital_twin", "seed"),
            "name": "synthetic_subsurface_digital_twin_seed",
            "synthetic_data": True,
            "notice": SYNTHETIC_NOTICE,
        },
        "run": {
            "run_id": run_id,
            "generated_at": metadata.get("generated_at"),
            "catalog_metadata_path": metadata.get("artifacts", {}).get("metadata_path"),
        },
        "model": metadata.get("model", {}),
        "catalog_entities": {
            "datasets": _entity_rows(run_id, "datasets", "dataset", tables.get("datasets", [])),
            "files": _entity_rows(run_id, "files", "file", tables.get("files", [])),
            "segments": _entity_rows(run_id, "segments", "segment", tables.get("segments", [])),
        },
        "features": {
            "wells": _entity_rows(run_id, "wells", "well", tables.get("wells", [])),
            "faults": _entity_rows(run_id, "faults", "fault", tables.get("faults", [])),
            "horizons": _entity_rows(run_id, "horizons", "horizon", tables.get("horizons", [])),
        },
        "metrics": metrics,
        "endpoints": endpoints,
    }


def _build_layers_geojson(metadata: dict[str, Any], run_id: str) -> dict[str, Any]:
    model = metadata.get("model", {})
    inline_min, inline_max = _extent_pair(model.get("inline_extent_m"), [0.0, 4000.0])
    crossline_min, crossline_max = _extent_pair(model.get("crossline_extent_m"), [0.0, 2600.0])
    features: list[dict[str, Any]] = []

    for source_row, well in enumerate(metadata.get("tables", {}).get("wells", []), start=1):
        features.append(
            {
                "type": "Feature",
                "id": stable_entity_id(run_id, "well", well.get("id")),
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(well["inline_m"]),
                        float(well["crossline_m"]),
                        float(well.get("target_depth_m", 0.0)),
                    ],
                },
                "properties": _entity_properties(
                    run_id, "wells", "well", source_row, well, "well_uid"
                )
                | {"feature": "well"},
            }
        )

    for source_row, fault in enumerate(metadata.get("tables", {}).get("faults", []), start=1):
        intercept = float(fault["inline_intercept_m"])
        reference = float(fault["crossline_reference_m"])
        slope = float(fault["slope"])
        x0 = intercept + slope * (crossline_min - reference)
        x1 = intercept + slope * (crossline_max - reference)
        features.append(
            {
                "type": "Feature",
                "id": stable_entity_id(run_id, "fault", fault.get("id")),
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(x0, 3), crossline_min],
                        [round(x1, 3), crossline_max],
                    ],
                },
                "properties": _entity_properties(
                    run_id, "faults", "fault", source_row, fault, "fault_uid"
                )
                | {"feature": "fault_trace"},
            }
        )

    rectangle = [
        [inline_min, crossline_min],
        [inline_max, crossline_min],
        [inline_max, crossline_max],
        [inline_min, crossline_max],
        [inline_min, crossline_min],
    ]
    for source_row, horizon in enumerate(metadata.get("tables", {}).get("horizons", []), start=1):
        features.append(
            {
                "type": "Feature",
                "id": stable_entity_id(run_id, "horizon", horizon.get("id")),
                "geometry": {"type": "Polygon", "coordinates": [rectangle]},
                "properties": _entity_properties(
                    run_id, "horizons", "horizon", source_row, horizon, "horizon_uid"
                )
                | {"feature": "horizon_extent"},
            }
        )

    return {
        "type": "FeatureCollection",
        "name": "synthetic_subsurface_digital_twin_layers",
        "coordinate_system": "survey-local metres: x = inline_m, y = crossline_m",
        "synthetic_data": True,
        "features": features,
    }


def _entity_rows(
    run_id: str,
    table_name: str,
    entity: str,
    rows: Any,
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    uid_name = f"{entity}_uid"
    return [
        _entity_properties(run_id, table_name, entity, source_row, row, uid_name)
        for source_row, row in enumerate(rows, start=1)
        if isinstance(row, dict)
    ]


def _entity_properties(
    run_id: str,
    table_name: str,
    entity: str,
    source_row: int,
    row: dict[str, Any],
    uid_name: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        uid_name: stable_entity_id(run_id, entity, row.get("id", source_row)),
        "synthetic_data": True,
        "source_table": table_name,
        "source_row": source_row,
        **row,
    }


def _build_manifest(
    *,
    run_id: str,
    visualization_path: Path,
    outputs: dict[str, Path],
) -> dict[str, Any]:
    return {
        "schema_version": DIGITAL_TWIN_SCHEMA_VERSION,
        "run_id": run_id,
        "synthetic_data": True,
        "notice": SYNTHETIC_NOTICE,
        "inputs": [
            {
                "name": "visualization_points",
                "path": str(visualization_path),
                "sha256": _sha256_file(visualization_path),
            }
        ],
        "outputs": [
            {
                "name": name,
                "path": str(path),
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for name, path in sorted(outputs.items())
        ],
    }


def _file_lookup(metadata: dict[str, Any]) -> dict[int, dict[str, Any]]:
    files = metadata.get("tables", {}).get("files", [])
    lookup: dict[int, dict[str, Any]] = {}
    if not isinstance(files, list):
        return lookup
    for row in files:
        if isinstance(row, dict) and "id" in row:
            lookup[int(row["id"])] = row
    return lookup


def _point_fieldnames(source_fieldnames: Sequence[str]) -> list[str]:
    fieldnames = list(DIGITAL_TWIN_POINT_COLUMNS)
    for fieldname in source_fieldnames:
        if fieldname not in fieldnames:
            fieldnames.append(fieldname)
    return fieldnames


def _csv_record(record: dict[str, object]) -> dict[str, object]:
    converted: dict[str, object] = {}
    for key, value in record.items():
        if isinstance(value, bool):
            converted[key] = "true" if value else "false"
        else:
            converted[key] = value
    return converted


def _stable_token(raw_id: object) -> str:
    text = str(raw_id)
    if text.isdecimal():
        return f"{int(text):06d}"
    return re.sub(r"[^A-Za-z0-9._:-]+", "_", text).strip("_") or "unknown"


def _int_value(value: object, name: str) -> int:
    if value is None or value == "":
        raise ValueError(f"{name} is required for digital-twin point provenance")
    return int(str(value))


def _string_value(value: object | None) -> str:
    return "" if value is None else str(value)


def _bool_value(value: object | None, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _add_float(accumulator: MetricAccumulator, value: object | None) -> None:
    try:
        number = float("" if value is None else str(value))
    except ValueError:
        return
    if math.isfinite(number):
        accumulator.add(number)


def _extent_pair(value: object, fallback: list[float]) -> tuple[float, float]:
    if isinstance(value, list | tuple) and len(value) == 2:
        return float(value[0]), float(value[1])
    return fallback[0], fallback[1]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()
