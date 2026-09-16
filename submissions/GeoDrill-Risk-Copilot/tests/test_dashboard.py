from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from aws_ai_energy.dashboard import (
    DashboardDataError,
    build_heatmap_payload,
    find_latest_analysis,
    parse_feature_request,
)

FIELDNAMES = [
    "row",
    "datasetid",
    "fileid",
    "sampleid",
    "inline_m",
    "crossline_m",
    "depth_m",
    "horizon_top_m",
    "horizon_base_m",
    "fault_likelihood",
    "fracture_intensity",
    "reservoir_probability",
    "nearest_fault_id",
    "fault_distance_m",
    "nearest_well_id",
    "nearest_well_distance_m",
    "confidence_score",
]


def _write_points(path: Path, count: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for index in range(1, count + 1):
            writer.writerow(
                {
                    "row": index,
                    "datasetid": 7,
                    "fileid": 11,
                    "sampleid": index,
                    "inline_m": 100.0 * index,
                    "crossline_m": 50.0 * index,
                    "depth_m": 1500.0 + index,
                    "horizon_top_m": 1400.0,
                    "horizon_base_m": 1700.0,
                    "fault_likelihood": 0.2 * index,
                    "fracture_intensity": 0.1 * index,
                    "reservoir_probability": 0.9 - 0.1 * index,
                    "nearest_fault_id": "fault_01",
                    "fault_distance_m": 20.0 * index,
                    "nearest_well_id": "well_01",
                    "nearest_well_distance_m": 30.0 * index,
                    "confidence_score": 0.8,
                }
            )


def test_parse_feature_request_recognizes_domain_language() -> None:
    request = parse_feature_request(
        "Show wells, faults, horizons, reservoir probability, and source provenance"
    )

    assert request.features == (
        "wells",
        "faults",
        "horizons",
        "reservoir_probability",
        "physical_data_provenance",
    )


def test_parse_feature_request_rejects_unsupported_request() -> None:
    with pytest.raises(DashboardDataError, match="supported feature"):
        parse_feature_request("Predict oil price next year")


def test_build_heatmap_payload_is_deterministic_and_grounded(tmp_path: Path) -> None:
    points_path = tmp_path / "enriched_points.csv"
    _write_points(points_path, count=5)

    first = build_heatmap_payload(
        points_path,
        "Show reservoir probability with faults and provenance",
        max_points=3,
    )
    second = build_heatmap_payload(
        points_path,
        "Show reservoir probability with faults and provenance",
        max_points=3,
    )

    assert first == second
    assert first["features"] == [
        "faults",
        "reservoir_probability",
        "physical_data_provenance",
    ]
    assert first["source"]["path"] == str(points_path)
    assert first["source"]["rows_total"] == 5
    assert len(first["points"]) == 3
    assert first["points"][0]["provenance"] == {
        "datasetid": 7,
        "fileid": 11,
        "sampleid": 1,
        "source_row": 1,
    }
    assert "synthetic" in first["notice"].lower()
    json.dumps(first)


def test_find_latest_analysis_requires_manifest(tmp_path: Path) -> None:
    older = tmp_path / "run_001"
    newer = tmp_path / "run_002"
    older.mkdir()
    newer.mkdir()
    (older / "manifest.json").write_text("{}", encoding="utf-8")

    assert find_latest_analysis(tmp_path) == older

    (newer / "manifest.json").write_text("{}", encoding="utf-8")
    assert find_latest_analysis(tmp_path) == newer
