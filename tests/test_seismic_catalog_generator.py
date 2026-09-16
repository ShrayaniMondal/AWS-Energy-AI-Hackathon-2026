from __future__ import annotations

import csv
import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from aws_ai_energy.generate.seismic_catalog import (
    generate_catalog,
    list_catalog_runs,
    load_latest_catalog,
    run_cli,
)

CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class SeismicCatalogGeneratorTests(unittest.TestCase):
    def test_standard_dataset_relationships_and_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = generate_catalog(
                2,
                output_dir=Path(temp_dir),
                dataset_kind="standard",
                segments=2,
                files=2,
                points_per_file=3,
                seed=7,
                created_at=CREATED_AT,
            )

            tables = result.metadata["tables"]
            self.assertEqual(len(tables["datasets"]), 2)
            self.assertEqual(len(tables["dimensions"]), 0)
            self.assertEqual(len(tables["segments"]), 4)
            self.assertEqual(len(tables["files"]), 8)
            self.assertGreaterEqual(len(tables["wells"]), 2)
            self.assertGreaterEqual(len(tables["faults"]), 1)
            self.assertTrue(
                all(segment["dimensionid"] is None for segment in tables["segments"])
            )
            self.assertTrue(
                all(row["logical_size_bytes"] < 1024 * 1024 * 1024 for row in tables["files"])
            )
            self.assertTrue(result.metadata_path.exists())
            self.assertTrue(result.visualization_path.exists())
            self.assertTrue(all(Path(row["artifact_path"]).exists() for row in tables["files"]))

            with result.visualization_path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 24)
            self.assertEqual(rows[0]["dimensionid"], "")
            self.assertIn("reservoir_probability", rows[0])
            self.assertIn("fault_likelihood", rows[0])
            self.assertIn("amplitude", rows[0])

            with result.metadata_path.open(encoding="utf-8") as handle:
                serialized = json.load(handle)
            self.assertEqual(
                serialized["tables"]["datasets"][0]["created"],
                CREATED_AT.isoformat(),
            )

    def test_multidimensional_dataset_relationships(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = generate_catalog(
                1,
                output_dir=Path(temp_dir),
                dataset_kind="multidimensional",
                dimensions=2,
                segments=2,
                files=1,
                points_per_file=2,
                seed=3,
                created_at=CREATED_AT,
            )

            tables = result.metadata["tables"]
            self.assertEqual(len(tables["datasets"]), 1)
            self.assertEqual(len(tables["dimensions"]), 2)
            self.assertEqual(len(tables["segments"]), 4)
            self.assertEqual(len(tables["files"]), 4)
            self.assertTrue(
                all(segment["dimensionid"] is not None for segment in tables["segments"])
            )

    def test_multiple_datasets_create_complementary_plot_attributes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = generate_catalog(
                5,
                output_dir=Path(temp_dir),
                dataset_kind="standard",
                segments=1,
                files=1,
                points_per_file=20,
                seed=19,
                created_at=CREATED_AT,
            )

            roles = {row["role"] for row in result.metadata["tables"]["datasets"]}
            self.assertEqual(
                roles,
                {"amplitude", "velocity", "impedance", "coherence", "reservoir"},
            )

            with result.visualization_path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 100)
            reservoir_values = [float(row["reservoir_probability"]) for row in rows]
            fault_values = [float(row["fault_likelihood"]) for row in rows]
            depths = [float(row["depth_m"]) for row in rows]

            self.assertGreater(max(reservoir_values), min(reservoir_values))
            self.assertGreater(max(fault_values), min(fault_values))
            self.assertGreater(max(depths), min(depths))

    def test_metadata_exports_and_path_collisions_are_restart_safe(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            first = generate_catalog(
                1,
                output_dir=output_dir,
                dataset_kind="standard",
                segments=1,
                files=1,
                points_per_file=2,
                seed=23,
                created_at=CREATED_AT,
            )
            second = generate_catalog(
                1,
                output_dir=output_dir,
                dataset_kind="standard",
                segments=1,
                files=1,
                points_per_file=2,
                seed=23,
                created_at=CREATED_AT,
            )

            self.assertNotEqual(first.run_id, second.run_id)
            self.assertEqual(first.visualization_path.name, "visualization_points.csv")
            self.assertEqual(second.visualization_path.name, "visualization_points_1.csv")

            first_file = first.metadata["tables"]["files"][0]
            second_file = second.metadata["tables"]["files"][0]
            self.assertEqual(first_file["name"], "file_0001.seismic.csv")
            self.assertEqual(second_file["name"], "file_0001_1.seismic.csv")
            self.assertEqual(second_file["path_collision_index"], 1)

            for table_name in ("datasets", "segments", "files", "wells", "faults", "horizons"):
                table_export = second.metadata["artifacts"]["table_exports"][table_name]
                self.assertTrue(Path(table_export["json"]).exists())
                self.assertTrue(Path(table_export["csv"]).exists())

            latest = load_latest_catalog(output_dir)
            self.assertEqual(latest["run"]["id"], second.run_id)
            self.assertEqual(latest["row_counts"]["visualization_points"], 2)

            runs = list_catalog_runs(output_dir)
            self.assertEqual([run["run_id"] for run in runs], [first.run_id, second.run_id])

    def test_cli_accepts_required_dataset_count_and_optional_counts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = run_cli(
                [
                    "1",
                    "--output-dir",
                    temp_dir,
                    "--dataset-kind",
                    "standard",
                    "--segments",
                    "1",
                    "--files",
                    "1",
                    "--points-per-file",
                    "1",
                    "--seed",
                    "11",
                ]
            )

            tables = result.metadata["tables"]
            self.assertEqual(len(tables["datasets"]), 1)
            self.assertEqual(len(tables["segments"]), 1)
            self.assertEqual(len(tables["files"]), 1)


if __name__ == "__main__":
    unittest.main()
