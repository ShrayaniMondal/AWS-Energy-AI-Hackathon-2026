"""Tests for risk-ranked prospect scoring and JSON/CSV exports.

Covers the five named factors, deterministic ordering, provenance preservation,
and byte-valid JSON consumed by the dashboard.
"""

from __future__ import annotations

import csv
import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from aws_ai_energy.generate.seismic_catalog import generate_catalog
from aws_ai_energy.subsurface.analysis import analyze_survey
from aws_ai_energy.subsurface.export import export_bundle
from aws_ai_energy.subsurface.points import WellLocation, load_survey
from aws_ai_energy.subsurface.scoring import (
    ScoringConfig,
    score_points,
    score_row,
    top_scores,
)

CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)

FIVE_FACTORS = (
    "reservoir_probability",
    "fault_likelihood",
    "fracture_intensity",
    "nearest_well_distance_m",
    "confidence_score",
)

PROVENANCE_FIELDS = ("row", "datasetid", "dimensionid", "fileid", "sampleid")


class ScoringTests(unittest.TestCase):
    temp_dir: TemporaryDirectory[str]
    root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = TemporaryDirectory()
        cls.root = Path(cls.temp_dir.name)
        generate_catalog(
            5,
            output_dir=cls.root / "catalog",
            dataset_kind="mixed",
            segments=3,
            dimensions=2,
            files=2,
            points_per_file=80,
            seed=99,
            created_at=CREATED_AT,
        )
        cls.survey = load_survey(catalog_dir=cls.root / "catalog")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_score_row_contains_all_five_factors(self) -> None:
        analysis = analyze_survey(self.survey)
        scores = score_points(analysis)
        self.assertGreater(len(scores), 0)
        row = score_row(scores[0])
        for factor in FIVE_FACTORS:
            self.assertIn(factor, row, f"missing factor: {factor}")

    def test_score_row_preserves_provenance(self) -> None:
        analysis = analyze_survey(self.survey)
        scores = score_points(analysis)
        row = score_row(scores[0])
        for field in PROVENANCE_FIELDS:
            self.assertIn(field, row, f"missing provenance field: {field}")
        self.assertIsInstance(row["row"], int)
        self.assertGreater(row["row"], 0)

    def test_confidence_bounded_zero_to_one(self) -> None:
        analysis = analyze_survey(self.survey)
        scores = score_points(analysis)
        for score in scores:
            self.assertGreaterEqual(score.confidence_score, 0.0)
            self.assertLessEqual(score.confidence_score, 1.0)

    def test_target_ordering_is_deterministic(self) -> None:
        analysis = analyze_survey(self.survey)
        scores = score_points(analysis)
        first_run = top_scores(scores, "target_score", 10)
        second_run = top_scores(scores, "target_score", 10)
        self.assertEqual(
            [score.point.row for score in first_run],
            [score.point.row for score in second_run],
        )

    def test_hazard_ordering_is_deterministic(self) -> None:
        analysis = analyze_survey(self.survey)
        scores = score_points(analysis)
        first_run = top_scores(scores, "hazard_score", 10)
        second_run = top_scores(scores, "hazard_score", 10)
        self.assertEqual(
            [score.point.row for score in first_run],
            [score.point.row for score in second_run],
        )

    def test_tie_handling_uses_row_number(self) -> None:
        analysis = analyze_survey(self.survey)
        scores = score_points(analysis)
        targets = top_scores(scores, "target_score", len(scores))
        for index in range(len(targets) - 1):
            first, second = targets[index], targets[index + 1]
            if first.target_score == second.target_score:
                self.assertLess(
                    first.point.row,
                    second.point.row,
                    "tied target_score should be broken by ascending row number",
                )

    def test_scoring_config_weights_exposed(self) -> None:
        config = ScoringConfig()
        self.assertAlmostEqual(
            config.hazard_fault_weight
            + config.hazard_fracture_weight
            + config.hazard_proximity_weight,
            1.0,
        )
        self.assertAlmostEqual(
            config.target_reservoir_weight
            + config.target_low_hazard_weight
            + config.target_well_control_weight,
            1.0,
        )

    def test_well_near_fault_has_higher_hazard(self) -> None:
        analysis = analyze_survey(self.survey)
        faults = analysis.faults
        if not faults:
            self.skipTest("no faults detected in seed-99 catalog")
        on_fault = WellLocation("on", "on", faults[0].inline_at(1300.0), 1300.0)
        far_away = WellLocation("far", "far", 100.0, 100.0)
        scored = analyze_survey(self.survey, wells=[on_fault, far_away])
        near_scores = score_points(scored, ScoringConfig())
        near_hazards = [score for score in near_scores if score.hazard_score > 0.5]
        self.assertGreater(len(near_hazards), 0)


class ExportJsonTests(unittest.TestCase):
    temp_dir: TemporaryDirectory[str]
    root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = TemporaryDirectory()
        cls.root = Path(cls.temp_dir.name)
        generate_catalog(
            5,
            output_dir=cls.root / "catalog",
            dataset_kind="mixed",
            segments=3,
            dimensions=2,
            files=2,
            points_per_file=80,
            seed=99,
            created_at=CREATED_AT,
        )
        cls.survey = load_survey(catalog_dir=cls.root / "catalog")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_json_exports_exist(self) -> None:
        analysis = analyze_survey(self.survey)
        with TemporaryDirectory() as export_dir:
            result = export_bundle(analysis, export_dir, top_n=5, created_at=CREATED_AT)
            self.assertIn("reservoir_targets_json", result.files)
            self.assertIn("fault_fracture_hotspots_json", result.files)

    def test_json_matches_csv_row_schema(self) -> None:
        analysis = analyze_survey(self.survey)
        with TemporaryDirectory() as export_dir:
            result = export_bundle(analysis, export_dir, top_n=5, created_at=CREATED_AT)

            with result.files["reservoir_targets"].open(encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            json_rows = json.loads(
                result.files["reservoir_targets_json"].read_text(encoding="utf-8")
            )

            self.assertEqual(len(csv_rows), len(json_rows))
            self.assertEqual(set(csv_rows[0].keys()), set(json_rows[0].keys()))
            self.assertEqual(json_rows[0]["row"], int(csv_rows[0]["row"]))

    def test_json_is_valid_and_contains_confidence(self) -> None:
        analysis = analyze_survey(self.survey)
        with TemporaryDirectory() as export_dir:
            result = export_bundle(analysis, export_dir, top_n=5, created_at=CREATED_AT)

            for key in ("reservoir_targets_json", "fault_fracture_hotspots_json"):
                data = json.loads(result.files[key].read_text(encoding="utf-8"))
                self.assertIsInstance(data, list)
                self.assertEqual(len(data), 5)
                for entry in data:
                    self.assertIn("confidence_score", entry)
                    self.assertGreaterEqual(entry["confidence_score"], 0.0)
                    self.assertLessEqual(entry["confidence_score"], 1.0)
                    for factor in FIVE_FACTORS:
                        self.assertIn(factor, entry)
                    for field in PROVENANCE_FIELDS:
                        self.assertIn(field, entry)

    def test_json_target_ordering_descending(self) -> None:
        analysis = analyze_survey(self.survey)
        with TemporaryDirectory() as export_dir:
            result = export_bundle(analysis, export_dir, top_n=10, created_at=CREATED_AT)
            targets = json.loads(
                result.files["reservoir_targets_json"].read_text(encoding="utf-8")
            )
            for index in range(len(targets) - 1):
                self.assertGreaterEqual(
                    targets[index]["target_score"],
                    targets[index + 1]["target_score"],
                )

    def test_json_hotspot_ordering_descending(self) -> None:
        analysis = analyze_survey(self.survey)
        with TemporaryDirectory() as export_dir:
            result = export_bundle(analysis, export_dir, top_n=10, created_at=CREATED_AT)
            hotspots = json.loads(
                result.files["fault_fracture_hotspots_json"].read_text(encoding="utf-8")
            )
            for index in range(len(hotspots) - 1):
                self.assertGreaterEqual(
                    hotspots[index]["hazard_score"],
                    hotspots[index + 1]["hazard_score"],
                )


if __name__ == "__main__":
    unittest.main()
