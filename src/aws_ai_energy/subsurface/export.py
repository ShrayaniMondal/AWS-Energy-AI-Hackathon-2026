from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aws_ai_energy.subsurface.analysis import SurveyAnalysis, analysis_summary, to_jsonable
from aws_ai_energy.subsurface.atlas_html import render_atlas
from aws_ai_energy.subsurface.hazards import HAZARD_RULES
from aws_ai_energy.subsurface.scoring import ScoringConfig, score_points, score_row, top_scores

DEFAULT_TOP_N = 25
DEMO_QUESTIONS = (
    "Which planned well carries the highest fault and fracture risk, and why?",
    "What happened last time we drilled into a similar hazard in this formation?",
    "Which reservoir targets are attractive but lower risk?",
    "Which catalog samples and drilling rows support that recommendation?",
)


@dataclass(frozen=True)
class ExportResult:
    output_dir: Path
    manifest_path: Path
    summary_path: Path
    atlas_path: Path | None
    plot_paths: tuple[Path, ...]
    plot_error: str
    files: dict[str, Path]
    summary: dict[str, Any]


def export_bundle(
    analysis: SurveyAnalysis,
    output_dir: Path | str,
    *,
    top_n: int = DEFAULT_TOP_N,
    html: bool = True,
    plots: bool = False,
    scoring: ScoringConfig | None = None,
    created_at: datetime | None = None,
) -> ExportResult:
    """Write the analysis as CSV, JSON, GeoJSON, HTML, and optional PNG files.

    ``output_dir`` is a parent directory; each export gets its own run directory
    and never overwrites an earlier one.
    """

    if top_n < 1:
        raise ValueError("top_n must be greater than zero")
    created = (created_at or datetime.now(UTC)).astimezone(UTC)
    run_name = analysis.survey.catalog_run_id or "points_" + created.strftime("%Y%m%dT%H%M%SZ")
    run_dir = _unique_dir(Path(output_dir) / run_name)
    run_dir.mkdir(parents=True, exist_ok=False)

    scores = score_points(analysis, scoring)
    files: dict[str, Path] = {}

    files["enriched_points"] = _write_csv(
        run_dir / "enriched_points.csv", [score_row(score) for score in scores]
    )
    hotspots = top_scores(scores, "hazard_score", top_n)
    targets = top_scores(scores, "target_score", top_n)
    files["fault_fracture_hotspots"] = _write_csv(
        run_dir / "fault_fracture_hotspots.csv", [score_row(score) for score in hotspots]
    )
    files["reservoir_targets"] = _write_csv(
        run_dir / "reservoir_targets.csv", [score_row(score) for score in targets]
    )
    files["faults_csv"] = _write_csv(
        run_dir / "faults.csv",
        [
            {key: value for key, value in to_jsonable(fault).items() if key != "evidence_rows"}
            | {"evidence_rows": " ".join(str(row) for row in fault.evidence_rows)}
            for fault in analysis.faults
        ],
    )
    files["faults_json"] = _write_json(run_dir / "faults.json", to_jsonable(analysis.faults))
    files["fault_traces_geojson"] = _write_json(
        run_dir / "fault_traces.geojson", _fault_geojson(analysis)
    )
    files["fracture_cells"] = _write_csv(
        run_dir / "fracture_cells.csv", [to_jsonable(cell) for cell in analysis.cells]
    )
    files["fracture_corridors_csv"] = _write_csv(
        run_dir / "fracture_corridors.csv",
        [
            to_jsonable(corridor) | {"cell_ids": " ".join(corridor.cell_ids)}
            for corridor in analysis.corridors
        ],
    )
    files["fracture_corridors_json"] = _write_json(
        run_dir / "fracture_corridors.json", to_jsonable(analysis.corridors)
    )
    files["well_screens_csv"] = _write_csv(run_dir / "well_screens.csv", _well_rows(analysis))
    files["well_briefs_json"] = _write_json(
        run_dir / "well_briefs.json", to_jsonable(analysis.ranked_briefs())
    )
    files["hazard_intervals"] = _write_csv(run_dir / "hazard_intervals.csv", _interval_rows(analysis))
    files["precedents"] = _write_csv(run_dir / "precedents.csv", _precedent_rows(analysis))
    files["hazard_rules"] = _write_json(run_dir / "hazard_rules.json", to_jsonable(HAZARD_RULES))
    if analysis.scorecard is not None:
        files["fault_scorecard"] = _write_json(
            run_dir / "fault_scorecard.json", to_jsonable(analysis.scorecard)
        )
    if analysis.formation:
        files["thresholds"] = _write_csv(
            run_dir / "thresholds.csv",
            [
                to_jsonable(row) | {"citation": row.citation.text()}
                for row in analysis.thresholds
            ],
        )

    plot_paths: tuple[Path, ...] = ()
    plot_error = ""
    if plots:
        from aws_ai_energy.subsurface.plots import PlottingUnavailableError, render_png_plots

        try:
            plot_paths = tuple(render_png_plots(analysis, scores, targets, run_dir / "plots"))
        except PlottingUnavailableError as error:
            plot_error = str(error)
        for plot_path in plot_paths:
            files[f"plot_{plot_path.stem}"] = plot_path

    generated_at = created.isoformat()
    summary = analysis_summary(analysis) | {
        "project": "Drilling Hazard Copilot",
        "generated_at": generated_at,
        "decision_counts": dict(sorted(Counter(score.decision for score in scores).items())),
        "top_fault_fracture_hotspot": score_row(hotspots[0]) if hotspots else {},
        "top_reservoir_target": score_row(targets[0]) if targets else {},
        "recommended_demo_questions": list(DEMO_QUESTIONS),
        "plot_error": plot_error,
        "screening_notice": (
            "Seismic inputs are generated synthetic catalog data. Risk indices and scores are "
            "screening ranks with fixed weights, not calibrated predictions. Drilling "
            "precedents are linked through documented rules in hazard_rules.json."
        ),
    }

    atlas_path: Path | None = None
    if html:
        atlas_path = run_dir / "hazard_atlas.html"
        listing = sorted(path.relative_to(run_dir).as_posix() for path in files.values())
        atlas_path.write_text(
            render_atlas(
                analysis,
                generated_at=generated_at,
                export_files=[*listing, "summary.json", "manifest.json"],
            ),
            encoding="utf-8",
        )
        files["hazard_atlas"] = atlas_path

    summary_path = run_dir / "summary.json"
    summary["outputs"] = {name: path.relative_to(run_dir).as_posix() for name, path in files.items()}
    _write_json(summary_path, summary)
    files["summary"] = summary_path

    manifest_path = _write_json(
        run_dir / "manifest.json",
        _manifest(analysis, run_dir, files, generated_at, top_n),
    )
    return ExportResult(
        output_dir=run_dir,
        manifest_path=manifest_path,
        summary_path=summary_path,
        atlas_path=atlas_path,
        plot_paths=plot_paths,
        plot_error=plot_error,
        files=files,
        summary=summary,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(
    analysis: SurveyAnalysis,
    run_dir: Path,
    files: dict[str, Path],
    generated_at: str,
    top_n: int,
) -> dict[str, Any]:
    inputs: list[dict[str, Any]] = [
        _input_record(analysis.survey.points_path, "generated_seismic_catalog", len(analysis.survey.points))
    ]
    if analysis.survey.catalog_path is not None:
        inputs.append(_input_record(analysis.survey.catalog_path, "generated_seismic_catalog", None))
    if analysis.drilling is not None:
        for path in analysis.drilling.source_paths():
            inputs.append(_input_record(path, "hackathon_use_case_1", None))
        cited_documents = sorted(
            {
                passage.document
                for brief in analysis.briefs
                for precedent in brief.precedents
                for passage in precedent.references
            }
        )
        for document in cited_documents:
            inputs.append(
                _input_record(
                    analysis.drilling.data_dir / "reference_docs" / document,
                    "hackathon_use_case_1",
                    None,
                )
            )

    outputs = [
        {
            "name": name,
            "path": path.relative_to(run_dir).as_posix(),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "evidence_class": "derived_screening_output",
        }
        for name, path in sorted(files.items())
    ]
    return {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "catalog_run_id": analysis.survey.catalog_run_id,
        "parameters": {
            "top_n": top_n,
            "formation": analysis.formation,
            "coherence_reference": analysis.coherence_reference,
            "settings": to_jsonable(analysis.settings),
        },
        "evidence_classes": {
            "generated_seismic_catalog": "Synthetic seismic catalog produced by generate.seismic_catalog.",
            "hackathon_use_case_1": "Drilling data and reference documents supplied for use case 1.",
            "derived_screening_output": "Computed by this tool; cite its inputs, not the output.",
        },
        "inputs": inputs,
        "outputs": outputs,
    }


def _input_record(path: Path, evidence_class: str, rows: int | None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path),
        "evidence_class": evidence_class,
        "sha256": sha256_file(path) if path.is_file() else None,
    }
    if rows is not None:
        record["rows"] = rows
    return record


def _fault_geojson(analysis: SurveyAnalysis) -> dict[str, Any]:
    features = []
    for fault in analysis.faults:
        (x0, y0), (x1, y1) = fault.trace()
        half = fault.damage_zone_half_width_m * math.hypot(1.0, fault.slope)
        properties = {
            key: value for key, value in to_jsonable(fault).items() if key != "evidence_rows"
        }
        features.append(
            {
                "type": "Feature",
                "id": fault.id,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[round(x0, 1), round(y0, 1)], [round(x1, 1), round(y1, 1)]],
                },
                "properties": properties | {"feature": "fault_trace"},
            }
        )
        features.append(
            {
                "type": "Feature",
                "id": f"{fault.id}-damage-zone",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [round(x0 - half, 1), round(y0, 1)],
                            [round(x1 - half, 1), round(y1, 1)],
                            [round(x1 + half, 1), round(y1, 1)],
                            [round(x0 + half, 1), round(y0, 1)],
                            [round(x0 - half, 1), round(y0, 1)],
                        ]
                    ],
                },
                "properties": {"fault_id": fault.id, "feature": "damage_zone"},
            }
        )
    return {
        "type": "FeatureCollection",
        "name": "detected_fault_traces",
        "coordinate_system": "survey-local metres: x = inline_m, y = crossline_m (not WGS84)",
        "features": features,
    }


def _well_rows(analysis: SurveyAnalysis) -> list[dict[str, Any]]:
    rows = []
    for brief in analysis.ranked_briefs():
        screen = brief.screen
        rows.append(
            {
                "well_id": screen.well.id,
                "inline_m": screen.well.inline_m,
                "crossline_m": screen.well.crossline_m,
                "risk_index": screen.risk_index,
                "risk_class": screen.risk_class,
                "nearest_fault_id": screen.nearest_fault_id or "",
                "nearest_fault_distance_m": _blank(screen.nearest_fault_distance_m),
                "nearest_fault_throw_m": _blank(screen.nearest_fault_throw_m),
                "p90_fracture_intensity": _blank(screen.p90_fracture_intensity),
                "samples_in_radius": screen.point_count,
                "hazards": " ".join(hazard.hazard for hazard in screen.hazards),
                "evidence_rows": " ".join(str(row) for row in screen.evidence_rows),
                "precedent_incidents": " ".join(
                    sorted(
                        {
                            incident.incident_id
                            for precedent in brief.precedents
                            for incident in precedent.incidents
                        }
                    )
                ),
            }
        )
    return rows


def _interval_rows(analysis: SurveyAnalysis) -> list[dict[str, Any]]:
    return [
        {"well_id": brief.screen.well.id}
        | to_jsonable(interval)
        | {"hazards": " ".join(interval.hazards)}
        for brief in analysis.ranked_briefs()
        for interval in brief.screen.intervals
    ]


def _precedent_rows(analysis: SurveyAnalysis) -> list[dict[str, Any]]:
    rows = []
    for brief in analysis.ranked_briefs():
        for precedent in brief.precedents:
            for incident in precedent.incidents:
                rows.append(
                    {
                        "well_id": brief.screen.well.id,
                        "hazard": precedent.hazard,
                        "incident_id": incident.incident_id,
                        "incident_well": incident.well_name,
                        "formation": incident.formation,
                        "npt_category": incident.npt_category,
                        "root_cause": incident.root_cause,
                        "resolution": incident.resolution,
                        "hours_lost": incident.hours_lost,
                        "cost_usd": incident.cost_usd,
                        "citation": incident.citation.text(),
                    }
                )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if fieldnames:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        key: json.dumps(value) if isinstance(value, (dict, list)) else value
                        for key, value in row.items()
                    }
                )
    return path


def _write_json(path: Path, data: Any) -> Path:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def _unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.name}_{index}")
        if not candidate.exists():
            return candidate
        index += 1


def _blank(value: float | None) -> float | str:
    return "" if value is None else value
