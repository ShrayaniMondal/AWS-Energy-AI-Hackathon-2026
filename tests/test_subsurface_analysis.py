from __future__ import annotations

import csv
import importlib.util
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from aws_ai_energy.generate.seismic_catalog import generate_catalog
from aws_ai_energy.subsurface.analysis import analyze_survey
from aws_ai_energy.subsurface.cli import main
from aws_ai_energy.subsurface.drilling import load_drilling_evidence, thresholds_for
from aws_ai_energy.subsurface.export import export_bundle, sha256_file
from aws_ai_energy.subsurface.points import SurveyInputs, WellLocation, load_survey
from aws_ai_energy.subsurface.scoring import score_points, score_row

CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _write_drilling_fixture(root: Path) -> Path:
    data_dir = root / "use-case-1"
    (data_dir / "reference_docs").mkdir(parents=True)
    with (data_dir / "npt_incident_log.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "incident_id", "well_name", "date", "depth_ft", "formation", "npt_category",
                "root_cause", "resolution", "hours_lost", "cost_usd",
            ]
        )
        writer.writerow(
            ["NPT-A", "Well A", "2024-01-01", "8000", "Wolfcamp A", "lost_circulation",
             "natural_fractures", "pumped_lcm_pill", "12.5", "400000"]
        )
        writer.writerow(
            ["NPT-B", "Well B", "2024-02-01", "8100", "Wolfcamp A", "well_control",
             "swabbing", "weighted_up_mud", "6.0", "150000"]
        )
        writer.writerow(
            ["NPT-C", "Well C", "2024-03-01", "6000", "Spraberry", "stuck_pipe",
             "differential_sticking", "jarred_free", "4.0", "90000"]
        )
    with (data_dir / "anomaly_thresholds.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["parameter", "formation", "low_warning", "low_critical", "high_warning",
             "high_critical", "unit"]
        )
        writer.writerow(["mud_weight_ppg", "Wolfcamp A", "9.5", "9.0", "11.0", "11.5", "ppg"])
    (data_dir / "reference_docs" / "bop_procedures.md").write_text(
        "# BOP\n\n### 3.1 Kick Detection — Warning Signs\n- Pit gain\n- Drilling break\n\n"
        "### 3.2 Shut-In Procedure\n1. Stop mud pumps\n",
        encoding="utf-8",
    )
    return data_dir


class SubsurfaceAnalysisTests(unittest.TestCase):
    temp_dir: TemporaryDirectory[str]
    root: Path
    catalog_dir: Path
    drilling_dir: Path
    survey: SurveyInputs

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = TemporaryDirectory()
        cls.root = Path(cls.temp_dir.name)
        cls.catalog_dir = cls.root / "catalog"
        generate_catalog(
            10,
            output_dir=cls.catalog_dir,
            dataset_kind="mixed",
            segments=3,
            dimensions=2,
            files=2,
            points_per_file=160,
            seed=42,
            created_at=CREATED_AT,
        )
        cls.drilling_dir = _write_drilling_fixture(cls.root)
        cls.survey = load_survey(catalog_dir=cls.catalog_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_detects_catalog_faults_within_tolerance(self) -> None:
        analysis = analyze_survey(self.survey)

        scorecard = analysis.scorecard
        assert scorecard is not None
        self.assertEqual(scorecard.catalog_faults, 4)
        self.assertEqual(scorecard.recall, 1.0)
        self.assertEqual(scorecard.precision, 1.0)
        for match in scorecard.matches:
            assert match.mean_trace_offset_m is not None
            assert match.slope_error is not None
            assert match.throw_error_m is not None
            self.assertLessEqual(match.mean_trace_offset_m, 25.0)
            self.assertLessEqual(abs(match.slope_error), 0.02)
            self.assertLessEqual(abs(match.throw_error_m), 45.0)

    def test_loaded_points_retain_digital_twin_provenance_for_scored_exports(self) -> None:
        point = self.survey.points[0]
        self.assertEqual(point.run_id, self.survey.catalog_run_id)
        self.assertTrue(point.sample_uid.startswith(f"{self.survey.catalog_run_id}:sample:"))
        self.assertTrue(Path(point.artifact_path).exists())
        self.assertEqual(point.source_table, "visualization_points")
        self.assertEqual(point.source_row, point.row)
        self.assertTrue(point.synthetic_data)

        analysis = analyze_survey(self.survey)
        row = score_row(score_points(analysis)[0])
        for column in (
            "run_id",
            "projectid",
            "siteid",
            "segmentid",
            "artifact_path",
            "source_table",
            "source_file",
            "source_row",
            "synthetic_data",
            "sample_uid",
            "file_uid",
            "horizon_top_uid",
        ):
            self.assertIn(column, row)
        self.assertEqual(row["source_row"], point.row)
        self.assertEqual(row["synthetic_data"], True)

    def test_fracture_corridors_follow_detected_faults(self) -> None:
        analysis = analyze_survey(self.survey)

        self.assertGreater(len(analysis.corridors), 0)
        fault_ids = {corridor.nearest_fault_id for corridor in analysis.corridors}
        self.assertGreaterEqual(len(fault_ids), len(analysis.faults) - 1)
        for corridor in analysis.corridors:
            if corridor.origin == "fault_damage_zone":
                assert corridor.nearest_fault_distance_m is not None
                self.assertLessEqual(corridor.nearest_fault_distance_m, 250.0)

    def test_site_on_fault_outranks_distant_site(self) -> None:
        faults = analyze_survey(self.survey).faults
        on_fault = WellLocation("on_fault", "on fault", faults[1].inline_at(1300.0), 1300.0)
        distant = WellLocation("distant", "distant", 300.0, 300.0)

        analysis = analyze_survey(self.survey, wells=[on_fault, distant])
        near_screen = analysis.brief_for("on_fault")
        far_screen = analysis.brief_for("distant")
        assert near_screen is not None and far_screen is not None

        near_hazards = {hazard.hazard for hazard in near_screen.screen.hazards}
        far_hazards = {hazard.hazard for hazard in far_screen.screen.hazards}
        self.assertIn(near_screen.screen.risk_class, {"high", "severe"})
        self.assertIn("fault_damage_zone", near_hazards)
        self.assertNotIn("fault_damage_zone", far_hazards)
        self.assertGreater(near_screen.screen.risk_index, far_screen.screen.risk_index)
        self.assertEqual(len(near_screen.screen.evidence_rows), 10)

    def test_precedents_cite_rows_and_report_missing_evidence(self) -> None:
        faults = analyze_survey(self.survey).faults
        site = WellLocation("site", "site", faults[0].inline_at(1300.0), 1300.0)
        drilling = load_drilling_evidence(self.drilling_dir)

        analysis = analyze_survey(
            self.survey, wells=[site], drilling=drilling, formation="Wolfcamp A"
        )
        brief = analysis.brief_for("site")
        assert brief is not None
        precedents = {precedent.hazard: precedent for precedent in brief.precedents}
        fault_zone = precedents["fault_damage_zone"]

        self.assertEqual(
            [incident.incident_id for incident in fault_zone.incidents], ["NPT-A", "NPT-B"]
        )
        self.assertEqual(
            fault_zone.incidents[0].citation.text(),
            "npt_incident_log.csv row 1 (incident_id=NPT-A)",
        )
        self.assertEqual(fault_zone.references[0].line, 3)
        self.assertEqual(fault_zone.references[0].excerpt, ("- Pit gain", "- Drilling break"))
        self.assertEqual(len(fault_zone.missing_references), 1)
        self.assertEqual(len(analysis.thresholds), 1)
        self.assertEqual(thresholds_for(drilling, "Spraberry"), [])
        if "permeable_sand" in precedents:
            self.assertEqual(precedents["permeable_sand"].incidents, ())
            self.assertIn("no precedent is claimed", precedents["permeable_sand"].note)

    def test_export_bundle_writes_manifest_and_never_overwrites(self) -> None:
        analysis = analyze_survey(
            self.survey,
            drilling=load_drilling_evidence(self.drilling_dir),
            formation="Wolfcamp A",
        )
        with TemporaryDirectory() as export_dir:
            first = export_bundle(analysis, export_dir, top_n=5, created_at=CREATED_AT)
            second = export_bundle(analysis, export_dir, top_n=5, created_at=CREATED_AT)

            self.assertNotEqual(first.output_dir, second.output_dir)
            self.assertEqual(second.output_dir.name, first.output_dir.name + "_1")

            manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
            outputs = {entry["name"]: entry for entry in manifest["outputs"]}
            enriched_path = first.files["enriched_points"]
            self.assertEqual(outputs["enriched_points"]["sha256"], sha256_file(enriched_path))
            input_classes = {entry["evidence_class"] for entry in manifest["inputs"]}
            self.assertEqual(input_classes, {"generated_seismic_catalog", "hackathon_use_case_1"})

            with enriched_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), len(self.survey.points))
            for column in ("hazard_score", "target_score", "decision", "fault_distance_m"):
                self.assertIn(column, rows[0])
            self.assertEqual(sum(first.summary["decision_counts"].values()), len(rows))

            with first.files["reservoir_targets"].open(encoding="utf-8", newline="") as handle:
                target_rows = list(csv.DictReader(handle))
            self.assertEqual(len(target_rows), 5)
            target_json = json.loads(
                first.files["reservoir_targets_json"].read_text(encoding="utf-8")
            )
            hotspot_json = json.loads(
                first.files["fault_fracture_hotspots_json"].read_text(encoding="utf-8")
            )
            self.assertEqual(len(target_json), 5)
            self.assertEqual(len(hotspot_json), 5)
            self.assertEqual(target_json[0]["row"], int(target_rows[0]["row"]))
            self.assertIn("confidence_score", target_json[0])
            self.assertGreaterEqual(target_json[0]["confidence_score"], 0.0)
            self.assertLessEqual(target_json[0]["confidence_score"], 1.0)
            geojson = json.loads(first.files["fault_traces_geojson"].read_text(encoding="utf-8"))
            self.assertEqual(len(geojson["features"]), 2 * len(analysis.faults))
            assert first.atlas_path is not None
            atlas = first.atlas_path.read_text(encoding="utf-8")
            self.assertIn("Subsurface hazard atlas", atlas)
            self.assertIn("npt_incident_log.csv row 1 (incident_id=NPT-A)", atlas)

    def test_cli_exports_by_default_and_fails_clearly(self) -> None:
        with TemporaryDirectory() as analysis_dir:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                main(
                    [
                        "--output-dir", str(self.catalog_dir),
                        "--analysis-dir", analysis_dir,
                        "--drilling-data-dir", str(self.drilling_dir),
                        "--no-plots",
                    ]
                )
            self.assertIn("analysis_dir=", stdout.getvalue())
            self.assertIn("fault_detection recall=1.0 precision=1.0", stdout.getvalue())

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            main(
                [
                    "wells", "--output-dir", str(self.catalog_dir), "--well", "well_05",
                    "--drilling-data-dir", str(self.drilling_dir), "--json",
                ]
            )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            [brief["screen"]["well"]["id"] for brief in payload["briefs"]],
            ["well_05"],
        )

        for arguments, message in (
            (["wells", "--output-dir", str(self.root / "missing")], "no catalog run found"),
            (["wells", "--output-dir", str(self.catalog_dir), "--well", "well_99"], "well_99"),
        ):
            stderr = io.StringIO()
            with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                main([*arguments, "--drilling-data-dir", str(self.drilling_dir)])
            self.assertEqual(raised.exception.code, 2)
            self.assertIn(message, stderr.getvalue())

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "matplotlib is not installed")
    def test_png_plots_render(self) -> None:
        analysis = analyze_survey(self.survey)
        with TemporaryDirectory() as export_dir:
            result = export_bundle(analysis, export_dir, html=False, plots=True)
            self.assertEqual(result.plot_error, "")
            self.assertEqual(len(result.plot_paths), 6)
            self.assertTrue(all(path.stat().st_size > 10_000 for path in result.plot_paths))


if __name__ == "__main__":
    unittest.main()
