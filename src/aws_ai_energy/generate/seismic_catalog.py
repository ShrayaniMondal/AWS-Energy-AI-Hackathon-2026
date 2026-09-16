from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

DatasetKind = Literal["standard", "multidimensional", "mixed"]

DEFAULT_RANGE_MIN = 1
DEFAULT_RANGE_MAX = 10
DEFAULT_OUTPUT_DIR = Path("outputs/seismic_catalog")
DEFAULT_POINTS_PER_FILE = 128
SURVEY_INLINE_MAX = 4_000.0
SURVEY_CROSSLINE_MAX = 2_600.0
DATASET_ROLES = (
    "amplitude",
    "velocity",
    "impedance",
    "coherence",
    "reservoir",
    "fracture",
)


@dataclass(frozen=True)
class CatalogGenerationResult:
    run_id: str
    metadata_path: Path
    visualization_path: Path
    files_root: Path
    run_dir: Path
    table_dir: Path
    metadata: dict[str, Any]


def generate_catalog(
    dataset_count: int,
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    segments: int | None = None,
    dimensions: int | None = None,
    files: int | None = None,
    dataset_kind: DatasetKind = "mixed",
    points_per_file: int = DEFAULT_POINTS_PER_FILE,
    seed: int | None = None,
    max_logical_file_size_mb: int = 1023,
    physical_file_bytes: int = 64_000,
    created_at: datetime | None = None,
) -> CatalogGenerationResult:
    """Generate seismic catalog metadata, plot-ready 3D points, and data files.

    The generated points are sampled from a shared synthetic basin model with
    horizons, channel sands, wells, and faults. Adding datasets increases
    coverage and complementary seismic attributes while preserving the catalog
    table relationships.
    """

    _validate_positive("dataset_count", dataset_count)
    _validate_optional_positive("segments", segments)
    _validate_optional_positive("dimensions", dimensions)
    _validate_optional_positive("files", files)
    _validate_positive("points_per_file", points_per_file)
    _validate_positive("max_logical_file_size_mb", max_logical_file_size_mb)
    if max_logical_file_size_mb >= 1024:
        raise ValueError("max_logical_file_size_mb must be less than 1024")
    if physical_file_bytes < 0:
        raise ValueError("physical_file_bytes must be greater than or equal to 0")
    if dataset_kind not in {"standard", "multidimensional", "mixed"}:
        raise ValueError("dataset_kind must be standard, multidimensional, or mixed")

    rng = random.Random(seed)
    root = Path(output_dir)
    metadata_dir = root / "metadata"
    files_root = root / "files"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    files_root.mkdir(parents=True, exist_ok=True)

    created = (created_at or datetime.now(UTC)).astimezone(UTC)
    generated_at = created.isoformat()
    run_id = _build_run_id(created, metadata_dir)
    run_dir = metadata_dir / "runs" / run_id
    table_dir = run_dir / "tables"
    run_dir.mkdir(parents=True, exist_ok=False)
    table_dir.mkdir(parents=True, exist_ok=False)
    max_size_bytes = max_logical_file_size_mb * 1024 * 1024
    basin_model = _build_basin_model(dataset_count, rng)

    tables: dict[str, list[dict[str, Any]]] = {
        "projects": _build_projects(dataset_count),
        "sites": _build_sites(dataset_count),
        "machines": [
            {"id": 1, "name": "adroy@houdmtdev001"},
            {"id": 2, "name": "adroy@adroy"},
        ],
        "filesystems": [
            {"id": 1, "machineid": 1, "name": "/data"},
            {"id": 2, "machineid": 1, "name": "/scratch"},
            {"id": 3, "machineid": 2, "name": "/data"},
        ],
        "wells": _attach_project_site(basin_model["wells"], dataset_count),
        "faults": _attach_project_site(basin_model["faults"], dataset_count),
        "horizons": _attach_project_site(basin_model["horizons"], dataset_count),
        "datasets": [],
        "dimensions": [],
        "segments": [],
        "files": [],
    }

    metadata: dict[str, Any] = {
        "schema_version": "1.1",
        "run": {
            "id": run_id,
            "metadata_dir": str(metadata_dir),
            "run_dir": str(run_dir),
            "table_dir": str(table_dir),
        },
        "generated_at": generated_at,
        "inputs": {
            "dataset_count": dataset_count,
            "segments": segments,
            "dimensions": dimensions,
            "files": files,
            "dataset_kind": dataset_kind,
            "points_per_file": points_per_file,
            "seed": seed,
            "max_logical_file_size_mb": max_logical_file_size_mb,
            "physical_file_bytes": physical_file_bytes,
        },
        "model": {
            "name": "synthetic_faulted_clastic_basin",
            "description": (
                "Coherent synthetic seismic exploration model with folded "
                "horizons, channel sands, fault damage zones, and wells."
            ),
            "inline_extent_m": [0, SURVEY_INLINE_MAX],
            "crossline_extent_m": [0, SURVEY_CROSSLINE_MAX],
            "dataset_roles": list(DATASET_ROLES),
        },
        "defaults": {
            "random_range": [DEFAULT_RANGE_MIN, DEFAULT_RANGE_MAX],
            "max_logical_file_size_mb": max_logical_file_size_mb,
            "physical_file_bytes": physical_file_bytes,
            "points_per_file": points_per_file,
        },
        "tables": tables,
        "artifacts": {},
    }

    dimension_id = 1
    segment_id = 1
    file_id = 1
    visualization_path, visualization_collision_index = _unique_path(
        root / "visualization_points.csv"
    )

    with visualization_path.open("w", newline="", encoding="utf-8") as csv_handle:
        point_writer = csv.DictWriter(csv_handle, fieldnames=_visualization_fieldnames())
        point_writer.writeheader()

        for dataset_id in range(1, dataset_count + 1):
            project = tables["projects"][(dataset_id - 1) % len(tables["projects"])]
            site = tables["sites"][(dataset_id - 1) % len(tables["sites"])]
            current_kind = _choose_dataset_kind(dataset_kind, rng)
            role = DATASET_ROLES[(dataset_id - 1) % len(DATASET_ROLES)]
            dataset_row = {
                "id": dataset_id,
                "projectid": project["id"],
                "siteid": site["id"],
                "created": generated_at,
                "revision": rng.randint(1, 5),
                "kind": current_kind,
                "role": role,
                "name": f"{role}_{current_kind}_dataset_{dataset_id:06d}",
            }
            tables["datasets"].append(dataset_row)

            if current_kind == "standard":
                segment_total = _count_or_random(segments, rng)
                for segment_index in range(1, segment_total + 1):
                    segment_id, file_id = _add_segment_and_files(
                        tables=tables,
                        basin_model=basin_model,
                        rng=rng,
                        files_root=files_root,
                        point_writer=point_writer,
                        dataset_row=dataset_row,
                        dimension_row=None,
                        segment_id=segment_id,
                        file_id=file_id,
                        segment_index=segment_index,
                        segment_total=segment_total,
                        files_per_segment=files,
                        points_per_file=points_per_file,
                        max_size_bytes=max_size_bytes,
                        physical_file_bytes=physical_file_bytes,
                    )
                continue

            dimension_total = _count_or_random(dimensions, rng)
            for dimension_index in range(1, dimension_total + 1):
                dimension_row = {
                    "id": dimension_id,
                    "projectid": dataset_row["projectid"],
                    "siteid": dataset_row["siteid"],
                    "datasetid": dataset_id,
                    "name": f"dimension_{dimension_index:02d}",
                    "axis": _axis_name(dimension_index),
                    "depth_bias_m": 55 * (dimension_index - 1),
                }
                tables["dimensions"].append(dimension_row)
                dimension_id += 1

                segment_total = _count_or_random(segments, rng)
                for segment_index in range(1, segment_total + 1):
                    segment_id, file_id = _add_segment_and_files(
                        tables=tables,
                        basin_model=basin_model,
                        rng=rng,
                        files_root=files_root,
                        point_writer=point_writer,
                        dataset_row=dataset_row,
                        dimension_row=dimension_row,
                        segment_id=segment_id,
                        file_id=file_id,
                        segment_index=segment_index,
                        segment_total=segment_total,
                        files_per_segment=files,
                        points_per_file=points_per_file,
                        max_size_bytes=max_size_bytes,
                        physical_file_bytes=physical_file_bytes,
                    )

    row_counts = _row_counts(tables)
    row_counts["visualization_points"] = sum(int(row["sample_count"]) for row in tables["files"])
    row_counts["physical_sample_rows"] = sum(
        int(row["physical_sample_rows"]) for row in tables["files"]
    )
    table_exports = _write_table_exports(table_dir, tables)
    metadata_path = run_dir / "catalog.json"
    latest_metadata_path = metadata_dir / "catalog.json"
    run_index_path = metadata_dir / "run_index.jsonl"
    latest_run_path = metadata_dir / "latest_run.json"
    metadata["row_counts"] = row_counts
    metadata["artifacts"] = {
        "metadata_path": str(metadata_path),
        "latest_metadata_path": str(latest_metadata_path),
        "run_index_path": str(run_index_path),
        "latest_run_path": str(latest_run_path),
        "visualization_path": str(visualization_path),
        "visualization_collision_index": visualization_collision_index,
        "files_root": str(files_root),
        "table_exports": table_exports,
        "matplotlib_example": "generate/plot_matplotlib.py",
        "ggplot_example": "generate/plot_ggplot.R",
    }
    _write_json(metadata_path, metadata)
    _write_json(latest_metadata_path, metadata)

    run_record = {
        "run_id": run_id,
        "generated_at": generated_at,
        "metadata_path": str(metadata_path),
        "visualization_path": str(visualization_path),
        "files_root": str(files_root),
        "row_counts": row_counts,
        "inputs": metadata["inputs"],
    }
    _write_json(latest_run_path, run_record)
    _append_run_index(run_index_path, run_record)

    return CatalogGenerationResult(
        run_id=run_id,
        metadata_path=metadata_path,
        visualization_path=visualization_path,
        files_root=files_root,
        run_dir=run_dir,
        table_dir=table_dir,
        metadata=metadata,
    )


def load_catalog(metadata_path: Path | str) -> dict[str, Any]:
    """Load a generated catalog JSON document from disk."""

    with Path(metadata_path).open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise TypeError(f"Catalog metadata must be a JSON object: {metadata_path}")
    return loaded


def load_latest_catalog(output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Load the latest catalog snapshot for an output directory."""

    return load_catalog(Path(output_dir) / "metadata" / "catalog.json")


def list_catalog_runs(output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> list[dict[str, Any]]:
    """List known catalog generation runs from metadata/run_index.jsonl."""

    run_index_path = Path(output_dir) / "metadata" / "run_index.jsonl"
    if not run_index_path.exists():
        return []
    runs = []
    with run_index_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                loaded = json.loads(stripped)
                if isinstance(loaded, dict):
                    runs.append(loaded)
    return runs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate seismic catalog tables, coherent exploration attributes, "
            "and lightweight physical files for HPC catalog demos."
        )
    )
    parser.add_argument(
        "dataset_count",
        nargs="?",
        type=int,
        help="Required number of datasets to create.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    parser.add_argument(
        "--segments",
        type=int,
        help=(
            "Segments per standard dataset or multidimensional dimension. "
            "Defaults to random 1-10."
        ),
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        help="Dimensions per multidimensional dataset. Defaults to random 1-10.",
    )
    parser.add_argument(
        "--files",
        type=int,
        help="Files per segment. Defaults to random 1-10.",
    )
    parser.add_argument(
        "--dataset-kind",
        choices=["standard", "multidimensional", "mixed"],
        default="mixed",
        help="Dataset type mix to generate. Defaults to mixed.",
    )
    parser.add_argument(
        "--points-per-file",
        type=int,
        default=DEFAULT_POINTS_PER_FILE,
        help=f"Visualization rows emitted per file. Defaults to {DEFAULT_POINTS_PER_FILE}.",
    )
    parser.add_argument("--seed", type=int, help="Random seed for repeatable demo data.")
    parser.add_argument(
        "--max-logical-file-size-mb",
        type=int,
        default=1023,
        help="Maximum recorded file size in MiB. Must be less than 1024.",
    )
    parser.add_argument(
        "--physical-file-bytes",
        type=int,
        default=64_000,
        help="Approximate cap for each lightweight on-disk data file. Defaults to 64000.",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List persisted run metadata for --output-dir instead of generating data.",
    )
    parser.add_argument(
        "--latest-metadata",
        action="store_true",
        help="Print the latest catalog metadata path for --output-dir instead of generating data.",
    )
    return parser


def run_cli(argv: Sequence[str] | None = None) -> CatalogGenerationResult:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_runs or args.latest_metadata:
        parser.error("--list-runs and --latest-metadata are available through the CLI entrypoint")
    if args.dataset_count is None:
        parser.error("dataset_count is required unless --list-runs or --latest-metadata is used")
    return _generate_from_args(args)


def _generate_from_args(args: argparse.Namespace) -> CatalogGenerationResult:
    return generate_catalog(
        args.dataset_count,
        output_dir=args.output_dir,
        segments=args.segments,
        dimensions=args.dimensions,
        files=args.files,
        dataset_kind=args.dataset_kind,
        points_per_file=args.points_per_file,
        seed=args.seed,
        max_logical_file_size_mb=args.max_logical_file_size_mb,
        physical_file_bytes=args.physical_file_bytes,
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_runs:
        print(json.dumps(list_catalog_runs(args.output_dir), indent=2, sort_keys=True))
        return
    if args.latest_metadata:
        latest_run_path = args.output_dir / "metadata" / "latest_run.json"
        if not latest_run_path.exists():
            raise SystemExit(f"No latest run metadata found under {args.output_dir}")
        latest = load_catalog(latest_run_path)
        print(latest["metadata_path"])
        return
    if args.dataset_count is None:
        parser.error("dataset_count is required unless --list-runs or --latest-metadata is used")

    result = _generate_from_args(args)
    tables = result.metadata["tables"]
    row_counts = result.metadata["row_counts"]
    print(f"run_id={result.run_id}")
    print(f"metadata={result.metadata_path}")
    print(f"visualization={result.visualization_path}")
    print(f"files_root={result.files_root}")
    print(f"table_dir={result.table_dir}")
    print(
        "rows="
        f"datasets:{len(tables['datasets'])} "
        f"dimensions:{len(tables['dimensions'])} "
        f"segments:{len(tables['segments'])} "
        f"files:{len(tables['files'])} "
        f"visualization_points:{row_counts['visualization_points']}"
    )


def _add_segment_and_files(
    *,
    tables: dict[str, list[dict[str, Any]]],
    basin_model: dict[str, Any],
    rng: random.Random,
    files_root: Path,
    point_writer: csv.DictWriter[str],
    dataset_row: dict[str, Any],
    dimension_row: dict[str, Any] | None,
    segment_id: int,
    file_id: int,
    segment_index: int,
    segment_total: int,
    files_per_segment: int | None,
    points_per_file: int,
    max_size_bytes: int,
    physical_file_bytes: int,
) -> tuple[int, int]:
    inline_start, inline_end = _window_bounds(
        segment_index,
        segment_total,
        SURVEY_INLINE_MAX,
    )
    dimension_id = None if dimension_row is None else dimension_row["id"]
    segment_row = {
        "id": segment_id,
        "projectid": dataset_row["projectid"],
        "siteid": dataset_row["siteid"],
        "datasetid": dataset_row["id"],
        "dimensionid": dimension_id,
        "name": f"segment_{segment_index:04d}",
        "inline_min_m": round(inline_start, 3),
        "inline_max_m": round(inline_end, 3),
    }
    tables["segments"].append(segment_row)

    file_total = _count_or_random(files_per_segment, rng)
    for file_index in range(1, file_total + 1):
        crossline_start, crossline_end = _window_bounds(
            file_index,
            file_total,
            SURVEY_CROSSLINE_MAX,
        )
        machine = rng.choice(tables["machines"])
        machine_filesystems = [
            filesystem
            for filesystem in tables["filesystems"]
            if filesystem["machineid"] == machine["id"]
        ]
        filesystem = rng.choice(machine_filesystems)
        logical_size = rng.randint(1024 * 1024, max_size_bytes)
        path = _catalog_path(dataset_row, dimension_row, segment_row)
        requested_name = f"file_{file_index:04d}.seismic.csv"
        requested_artifact_path = _artifact_path(
            files_root,
            machine["name"],
            filesystem["name"],
            path,
            requested_name,
        )
        artifact_path, collision_index = _unique_path(requested_artifact_path)
        name = artifact_path.name
        file_row = {
            "id": file_id,
            "projectid": dataset_row["projectid"],
            "siteid": dataset_row["siteid"],
            "datasetid": dataset_row["id"],
            "segmentid": segment_id,
            "machineid": machine["id"],
            "filesystemid": filesystem["id"],
            "path": path,
            "name": name,
            "requested_name": requested_name,
            "logical_size_bytes": logical_size,
            "artifact_path": str(artifact_path),
            "path_collision_index": collision_index,
            "sample_count": points_per_file,
            "crossline_min_m": round(crossline_start, 3),
            "crossline_max_m": round(crossline_end, 3),
        }
        tables["files"].append(file_row)

        physical_rows = _write_points(
            artifact_path=artifact_path,
            file_row=file_row,
            point_writer=point_writer,
            points=_build_points(
                rng=rng,
                basin_model=basin_model,
                dataset_row=dataset_row,
                dimension_row=dimension_row,
                segment_row=segment_row,
                file_row=file_row,
                points_per_file=points_per_file,
                inline_range=(inline_start, inline_end),
                crossline_range=(crossline_start, crossline_end),
            ),
            physical_file_bytes=physical_file_bytes,
        )
        file_row["physical_sample_rows"] = physical_rows
        file_id += 1

    return segment_id + 1, file_id


def _build_points(
    *,
    rng: random.Random,
    basin_model: dict[str, Any],
    dataset_row: dict[str, Any],
    dimension_row: dict[str, Any] | None,
    segment_row: dict[str, Any],
    file_row: dict[str, Any],
    points_per_file: int,
    inline_range: tuple[float, float],
    crossline_range: tuple[float, float],
) -> Iterable[dict[str, Any]]:
    grid_columns = max(2, math.ceil(math.sqrt(points_per_file)))
    grid_rows = max(2, math.ceil(points_per_file / grid_columns))
    depth_bias = 0.0 if dimension_row is None else float(dimension_row["depth_bias_m"])

    for point_index in range(points_per_file):
        column = point_index % grid_columns
        row = point_index // grid_columns
        inline = _lerp(inline_range[0], inline_range[1], (column + 0.5) / grid_columns)
        crossline = _lerp(crossline_range[0], crossline_range[1], (row + 0.5) / grid_rows)
        inline += rng.uniform(-4.0, 4.0)
        crossline += rng.uniform(-4.0, 4.0)

        interpretation = _interpret_sample(
            inline=inline,
            crossline=crossline,
            dataset_role=str(dataset_row["role"]),
            depth_bias=depth_bias,
            basin_model=basin_model,
            rng=rng,
        )
        yield {
            "datasetid": dataset_row["id"],
            "projectid": dataset_row["projectid"],
            "siteid": dataset_row["siteid"],
            "dataset_role": dataset_row["role"],
            "dimensionid": "" if dimension_row is None else dimension_row["id"],
            "dimension_axis": "" if dimension_row is None else dimension_row["axis"],
            "segmentid": segment_row["id"],
            "fileid": file_row["id"],
            "sampleid": point_index + 1,
            "inline_m": round(inline, 5),
            "crossline_m": round(crossline, 5),
            "depth_m": round(float(interpretation["depth_m"]), 5),
            "time_ms": round(float(interpretation["time_ms"]), 5),
            "horizon_top_m": round(float(interpretation["horizon_top_m"]), 5),
            "horizon_base_m": round(float(interpretation["horizon_base_m"]), 5),
            "structure_depth_m": round(float(interpretation["structure_depth_m"]), 5),
            "amplitude": round(float(interpretation["amplitude"]), 6),
            "phase": round(float(interpretation["phase"]), 6),
            "coherence": round(float(interpretation["coherence"]), 6),
            "velocity_m_s": round(float(interpretation["velocity_m_s"]), 5),
            "impedance_ai": round(float(interpretation["impedance_ai"]), 5),
            "fault_id": interpretation["fault_id"],
            "fault_throw_m": round(float(interpretation["fault_throw_m"]), 5),
            "fault_likelihood": round(float(interpretation["fault_likelihood"]), 6),
            "fracture_intensity": round(float(interpretation["fracture_intensity"]), 6),
            "reservoir_probability": round(
                float(interpretation["reservoir_probability"]),
                6,
            ),
            "well_id": interpretation["well_id"],
            "well_distance_m": round(float(interpretation["well_distance_m"]), 5),
            "lithology": interpretation["lithology"],
            "logical_size_bytes": file_row["logical_size_bytes"],
        }


def _interpret_sample(
    *,
    inline: float,
    crossline: float,
    dataset_role: str,
    depth_bias: float,
    basin_model: dict[str, Any],
    rng: random.Random,
) -> dict[str, Any]:
    fault = _nearest_fault(inline, crossline, basin_model["faults"])
    well = _nearest_well(inline, crossline, basin_model["wells"])
    signed_fault_distance = float(fault["signed_distance_m"])
    fault_distance = abs(signed_fault_distance)
    throw = float(fault["throw_m"]) if signed_fault_distance > 0 else 0.0
    damage_zone = float(fault["damage_zone_m"])
    fault_likelihood = _clamp(math.exp(-((fault_distance / damage_zone) ** 2)), 0.0, 1.0)

    channel_center = 1_220.0 + 360.0 * math.sin(inline / 620.0)
    channel_distance = abs(crossline - channel_center)
    channel_strength = math.exp(-((channel_distance / 270.0) ** 2))
    near_well = math.exp(-((float(well["distance_m"]) / 480.0) ** 2))

    folded_top = (
        1_560.0
        + 175.0 * math.sin(inline / 680.0)
        + 80.0 * math.cos(crossline / 430.0)
        + throw
    )
    reservoir_thickness = 210.0 + 70.0 * channel_strength - 35.0 * fault_likelihood
    horizon_top = folded_top + depth_bias * 0.35
    horizon_base = horizon_top + reservoir_thickness
    structure_depth = horizon_top + reservoir_thickness * 0.52

    depth = structure_depth + rng.uniform(-42.0, 42.0)
    reservoir_probability = _clamp(
        0.12 + channel_strength * 0.72 + near_well * 0.18 - fault_likelihood * 0.25,
        0.0,
        1.0,
    )
    fracture_intensity = _clamp(
        0.08 + fault_likelihood * 0.78 + near_well * 0.12 + rng.uniform(-0.02, 0.02),
        0.0,
        1.0,
    )

    velocity = (
        2_480.0
        + depth * 0.62
        - reservoir_probability * 420.0
        + fault_likelihood * 130.0
    )
    density = 2.05 + depth / 4_800.0 - reservoir_probability * 0.18
    impedance = velocity * density
    coherence = _clamp(0.92 - fault_likelihood * 0.68 + rng.uniform(-0.04, 0.04), 0.0, 1.0)
    phase = math.atan2(crossline - channel_center, depth - structure_depth + 20.0)
    amplitude = _role_amplitude(
        dataset_role=dataset_role,
        inline=inline,
        crossline=crossline,
        depth=depth,
        reservoir_probability=reservoir_probability,
        fracture_intensity=fracture_intensity,
        fault_likelihood=fault_likelihood,
        coherence=coherence,
        velocity=velocity,
        impedance=impedance,
        rng=rng,
    )

    lithology = "shale"
    if reservoir_probability >= 0.62:
        lithology = "channel_sand"
    if fault_likelihood >= 0.7:
        lithology = "fault_damage_zone"
    if depth > horizon_base + 90.0:
        lithology = "carbonate_basement"

    return {
        "depth_m": depth,
        "time_ms": depth / velocity * 2_000.0,
        "horizon_top_m": horizon_top,
        "horizon_base_m": horizon_base,
        "structure_depth_m": structure_depth,
        "amplitude": amplitude,
        "phase": phase,
        "coherence": coherence,
        "velocity_m_s": velocity,
        "impedance_ai": impedance,
        "fault_id": fault["id"],
        "fault_throw_m": throw,
        "fault_likelihood": fault_likelihood,
        "fracture_intensity": fracture_intensity,
        "reservoir_probability": reservoir_probability,
        "well_id": well["id"],
        "well_distance_m": well["distance_m"],
        "lithology": lithology,
    }


def _role_amplitude(
    *,
    dataset_role: str,
    inline: float,
    crossline: float,
    depth: float,
    reservoir_probability: float,
    fracture_intensity: float,
    fault_likelihood: float,
    coherence: float,
    velocity: float,
    impedance: float,
    rng: random.Random,
) -> float:
    wavelet = math.sin(inline / 115.0) * math.cos(crossline / 170.0) * math.sin(depth / 140.0)
    noise = rng.uniform(-0.08, 0.08)
    if dataset_role == "velocity":
        return (velocity - 3_350.0) / 850.0 + noise
    if dataset_role == "impedance":
        return (impedance - 9_000.0) / 2_400.0 + noise
    if dataset_role == "coherence":
        return coherence * 2.0 - 1.0 + noise
    if dataset_role == "reservoir":
        return reservoir_probability * 2.0 - 1.0 + wavelet * 0.25 + noise
    if dataset_role == "fracture":
        return fracture_intensity * 2.0 - 1.0 - fault_likelihood * 0.2 + noise
    return wavelet + reservoir_probability * 0.9 - fault_likelihood * 0.45 + noise


def _write_points(
    *,
    artifact_path: Path,
    file_row: dict[str, Any],
    point_writer: csv.DictWriter[str],
    points: Iterable[dict[str, Any]],
    physical_file_bytes: int,
) -> int:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    physical_rows = 0
    with artifact_path.open("w", newline="", encoding="utf-8") as handle:
        handle.write("# catalog_file=" + json.dumps(file_row, sort_keys=True) + "\n")
        writer = csv.DictWriter(handle, fieldnames=_visualization_fieldnames())
        writer.writeheader()
        for point in points:
            point_writer.writerow(point)
            if physical_file_bytes == 0 or handle.tell() < physical_file_bytes:
                writer.writerow(point)
                physical_rows += 1
    return physical_rows


def _build_basin_model(dataset_count: int, rng: random.Random) -> dict[str, Any]:
    fault_count = max(1, min(4, math.ceil(dataset_count / 3)))
    well_count = max(2, min(8, dataset_count + 1))
    faults = [
        {
            "id": fault_id,
            "name": f"fault_{fault_id:02d}",
            "inline_intercept_m": 850.0 + fault_id * 690.0 + rng.uniform(-80.0, 80.0),
            "crossline_reference_m": SURVEY_CROSSLINE_MAX / 2,
            "slope": rng.uniform(-0.28, 0.24),
            "throw_m": rng.uniform(75.0, 210.0),
            "damage_zone_m": rng.uniform(90.0, 180.0),
        }
        for fault_id in range(1, fault_count + 1)
    ]
    wells = []
    for well_id in range(1, well_count + 1):
        fraction = well_id / (well_count + 1)
        inline = 320.0 + fraction * (SURVEY_INLINE_MAX - 640.0)
        crossline = 1_220.0 + 360.0 * math.sin(inline / 620.0)
        wells.append(
            {
                "id": well_id,
                "name": f"well_{well_id:02d}",
                "inline_m": round(inline + rng.uniform(-85.0, 85.0), 3),
                "crossline_m": round(crossline + rng.uniform(-120.0, 120.0), 3),
                "target_depth_m": round(1_720.0 + rng.uniform(-130.0, 170.0), 3),
            }
        )
    horizons = [
        {"id": 1, "name": "seal_top", "base_depth_m": 1_350.0},
        {"id": 2, "name": "reservoir_top", "base_depth_m": 1_560.0},
        {"id": 3, "name": "reservoir_base", "base_depth_m": 1_790.0},
        {"id": 4, "name": "basement_marker", "base_depth_m": 2_150.0},
    ]
    return {"faults": faults, "wells": wells, "horizons": horizons}


def _nearest_fault(
    inline: float,
    crossline: float,
    faults: list[dict[str, Any]],
) -> dict[str, Any]:
    nearest: dict[str, Any] | None = None
    for fault in faults:
        fault_inline = float(fault["inline_intercept_m"]) + float(fault["slope"]) * (
            crossline - float(fault["crossline_reference_m"])
        )
        signed_distance = inline - fault_inline
        candidate = dict(fault)
        candidate["signed_distance_m"] = signed_distance
        if nearest is None or abs(signed_distance) < abs(float(nearest["signed_distance_m"])):
            nearest = candidate
    if nearest is None:
        raise ValueError("basin model must include at least one fault")
    return nearest


def _nearest_well(
    inline: float,
    crossline: float,
    wells: list[dict[str, Any]],
) -> dict[str, Any]:
    nearest: dict[str, Any] | None = None
    for well in wells:
        distance = math.hypot(inline - float(well["inline_m"]), crossline - float(well["crossline_m"]))
        candidate = dict(well)
        candidate["distance_m"] = distance
        if nearest is None or distance < float(nearest["distance_m"]):
            nearest = candidate
    if nearest is None:
        raise ValueError("basin model must include at least one well")
    return nearest


def _build_projects(dataset_count: int) -> list[dict[str, Any]]:
    project_count = max(1, min(3, dataset_count))
    return [
        {
            "id": project_id,
            "name": f"energy_seismic_project_{project_id:02d}",
        }
        for project_id in range(1, project_count + 1)
    ]


def _build_sites(dataset_count: int) -> list[dict[str, Any]]:
    site_count = max(1, min(4, dataset_count))
    return [
        {
            "id": site_id,
            "projectid": ((site_id - 1) % max(1, min(3, dataset_count))) + 1,
            "name": f"basin_site_{site_id:02d}",
        }
        for site_id in range(1, site_count + 1)
    ]


def _attach_project_site(rows: list[dict[str, Any]], dataset_count: int) -> list[dict[str, Any]]:
    project_count = max(1, min(3, dataset_count))
    site_count = max(1, min(4, dataset_count))
    attached = []
    for index, row in enumerate(rows, start=1):
        attached.append(
            {
                "projectid": ((index - 1) % project_count) + 1,
                "siteid": ((index - 1) % site_count) + 1,
                **row,
            }
        )
    return attached


def _choose_dataset_kind(
    dataset_kind: DatasetKind,
    rng: random.Random,
) -> Literal["standard", "multidimensional"]:
    if dataset_kind == "mixed":
        return rng.choice(["standard", "multidimensional"])
    return dataset_kind


def _count_or_random(value: int | None, rng: random.Random) -> int:
    return value if value is not None else rng.randint(DEFAULT_RANGE_MIN, DEFAULT_RANGE_MAX)


def _axis_name(index: int) -> str:
    axis_names = ["inline", "crossline", "depth", "time", "offset", "azimuth"]
    if index <= len(axis_names):
        return axis_names[index - 1]
    return f"attribute_{index:02d}"


def _window_bounds(index: int, total: int, upper: float) -> tuple[float, float]:
    start = (index - 1) / total * upper
    end = index / total * upper
    return start, end


def _lerp(start: float, end: float, fraction: float) -> float:
    return start + (end - start) * fraction


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _catalog_path(
    dataset_row: dict[str, Any],
    dimension_row: dict[str, Any] | None,
    segment_row: dict[str, Any],
) -> str:
    parts = [
        "seismic",
        f"project_{int(dataset_row['projectid']):03d}",
        f"site_{int(dataset_row['siteid']):03d}",
        f"dataset_{int(dataset_row['id']):06d}",
    ]
    if dimension_row is not None:
        parts.append(f"dimension_{int(dimension_row['id']):06d}")
    parts.append(f"segment_{int(segment_row['id']):06d}")
    return "/" + "/".join(parts)


def _artifact_path(
    files_root: Path,
    machine_name: str,
    filesystem_name: str,
    catalog_path: str,
    file_name: str,
) -> Path:
    safe_machine = _safe_path_token(machine_name)
    safe_filesystem = filesystem_name.strip("/").replace("/", "_") or "root"
    relative_catalog_path = catalog_path.strip("/")
    return files_root / safe_machine / safe_filesystem / relative_catalog_path / file_name


def _safe_path_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")


def _build_run_id(created: datetime, metadata_dir: Path) -> str:
    base = "run_" + created.strftime("%Y%m%dT%H%M%S%fZ")
    candidate = base
    index = 1
    while (metadata_dir / "runs" / candidate).exists():
        candidate = f"{base}_{index}"
        index += 1
    return candidate


def _unique_path(path: Path) -> tuple[Path, int]:
    if not path.exists():
        return path, 0

    suffix = "".join(path.suffixes)
    if suffix:
        stem = path.name[: -len(suffix)]
    else:
        stem = path.name

    index = 1
    while True:
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate, index
        index += 1


def _write_table_exports(
    table_dir: Path,
    tables: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, str]]:
    exports = {}
    for table_name, rows in tables.items():
        json_path = table_dir / f"{table_name}.json"
        csv_path = table_dir / f"{table_name}.csv"
        _write_json(json_path, rows)
        _write_table_csv(csv_path, rows)
        exports[table_name] = {
            "json": str(json_path),
            "csv": str(csv_path),
        }
    return exports


def _write_table_csv(csv_path: Path, rows: list[dict[str, Any]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _fieldnames_for_rows(rows)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        if not fieldnames:
            return
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fieldnames_for_rows(rows: list[dict[str, Any]]) -> list[str]:
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for fieldname in row:
            if fieldname not in seen:
                fieldnames.append(fieldname)
                seen.add(fieldname)
    return fieldnames


def _row_counts(tables: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {table_name: len(rows) for table_name, rows in tables.items()}


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _append_run_index(path: Path, run_record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(run_record, sort_keys=True))
        handle.write("\n")


def _visualization_fieldnames() -> list[str]:
    return [
        "datasetid",
        "projectid",
        "siteid",
        "dataset_role",
        "dimensionid",
        "dimension_axis",
        "segmentid",
        "fileid",
        "sampleid",
        "inline_m",
        "crossline_m",
        "depth_m",
        "time_ms",
        "horizon_top_m",
        "horizon_base_m",
        "structure_depth_m",
        "amplitude",
        "phase",
        "coherence",
        "velocity_m_s",
        "impedance_ai",
        "fault_id",
        "fault_throw_m",
        "fault_likelihood",
        "fracture_intensity",
        "reservoir_probability",
        "well_id",
        "well_distance_m",
        "lithology",
        "logical_size_bytes",
    ]


def _validate_positive(name: str, value: int) -> None:
    if value < 1:
        raise ValueError(f"{name} must be greater than zero")


def _validate_optional_positive(name: str, value: int | None) -> None:
    if value is not None:
        _validate_positive(name, value)


if __name__ == "__main__":
    main()
