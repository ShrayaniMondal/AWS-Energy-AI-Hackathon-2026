"""Command line for fault, fracture, well-hazard, and reservoir-target analysis.

``export`` is the default command, so ``seismic-catalog-analyze --output-dir DIR``
analyzes the latest catalog run under DIR and writes a bundle to DIR/analysis.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from aws_ai_energy.generate.seismic_catalog import DEFAULT_OUTPUT_DIR, generate_catalog
from aws_ai_energy.subsurface.analysis import (
    AnalysisSettings,
    SurveyAnalysis,
    WellBrief,
    analysis_summary,
    analyze_survey,
    to_jsonable,
)
from aws_ai_energy.subsurface.drilling import DrillingEvidence, load_drilling_evidence
from aws_ai_energy.subsurface.export import DEFAULT_TOP_N, export_bundle
from aws_ai_energy.subsurface.faults import FaultDetectionConfig
from aws_ai_energy.subsurface.fractures import FractureConfig
from aws_ai_energy.subsurface.hazards import HazardConfig
from aws_ai_energy.subsurface.points import (
    SubsurfaceDataError,
    WellLocation,
    load_survey,
    parse_location,
)
from aws_ai_energy.subsurface.scoring import score_points, score_row, top_scores

COMMANDS = ("export", "faults", "fractures", "wells", "targets", "demo")
DEFAULT_DRILLING_DATA_DIR = Path("Hackathon/use-case-1/data")
DEFAULT_DEMO_DIR = Path("outputs/hazard_demo")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seismic-catalog-analyze",
        description=(
            "Detect faults and fracture corridors in a generated seismic catalog, screen wells, "
            "link hazards to cited use-case-1 drilling precedents, and export the results."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    export = commands.add_parser("export", help="Write CSV/JSON/GeoJSON/HTML/PNG exports.")
    _survey_options(export)
    _evidence_options(export)
    _tuning_options(export)
    export.add_argument(
        "--analysis-dir", type=Path, help="Export parent. Defaults to OUTPUT_DIR/analysis."
    )
    export.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Hotspot and target rows.")
    export.add_argument("--no-plots", action="store_true", help="Skip matplotlib PNG plots.")
    export.add_argument("--no-html", action="store_true", help="Skip the HTML hazard atlas.")

    for name, text in (
        ("faults", "List detected faults and the catalog scorecard."),
        ("fractures", "List fracture corridors."),
        ("targets", "List top reservoir target samples."),
    ):
        command = commands.add_parser(name, help=text)
        _survey_options(command)
        _tuning_options(command)
        command.add_argument("--json", action="store_true", help="Print JSON.")
        if name == "targets":
            command.add_argument("--top-n", type=int, default=10, help="Rows to print.")

    wells = commands.add_parser("wells", help="Screen wells and show cited drilling precedents.")
    _survey_options(wells)
    _evidence_options(wells)
    _tuning_options(wells)
    location = wells.add_mutually_exclusive_group()
    location.add_argument("--well", help="Catalog well id, for example well_05.")
    location.add_argument(
        "--at", help="Screen a planned location given as INLINE,CROSSLINE metres."
    )
    wells.add_argument("--json", action="store_true", help="Print JSON.")

    demo = commands.add_parser("demo", help="Generate a seeded catalog, analyze it, and export.")
    demo.add_argument("--output-dir", type=Path, default=DEFAULT_DEMO_DIR)
    demo.add_argument("--datasets", type=int, default=10)
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--points-per-file", type=int, default=160)
    _evidence_options(demo)
    demo.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    demo.add_argument("--no-plots", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or (arguments[0] not in COMMANDS and arguments[0] not in {"-h", "--help"}):
        arguments.insert(0, "export")
    parser = build_parser()
    args = parser.parse_args(arguments)
    try:
        output = _dispatch(args)
    except SubsurfaceDataError as error:
        parser.exit(2, f"error: {error}\n")
    print(output)


def _dispatch(args: argparse.Namespace) -> str:
    if args.command == "demo":
        return _demo(args)

    settings = _settings(args)
    has_catalog_run = (Path(args.output_dir) / "metadata" / "latest_run.json").is_file()
    survey = load_survey(
        catalog_dir=args.output_dir if has_catalog_run or args.visualization_path is None else None,
        catalog_path=args.catalog_path,
        points_path=args.visualization_path,
    )
    if args.command in {"export", "wells"}:
        drilling = _drilling(args)
        wells = _selected_wells(args, survey.wells) if args.command == "wells" else None
        analysis = analyze_survey(
            survey,
            wells=wells,
            drilling=drilling,
            formation=args.formation or None,
            settings=settings,
        )
        if args.command == "wells":
            return _render_wells(analysis, as_json=args.json)
        result = export_bundle(
            analysis,
            args.analysis_dir or Path(args.output_dir) / "analysis",
            top_n=args.top_n,
            html=not args.no_html,
            plots=not args.no_plots,
        )
        return _render_export(result.output_dir, result.summary, result.plot_error)

    analysis = analyze_survey(survey, settings=settings)
    if args.command == "faults":
        return _render_faults(analysis, as_json=args.json)
    if args.command == "fractures":
        return _render_fractures(analysis, as_json=args.json)
    return _render_targets(analysis, top_n=args.top_n, as_json=args.json)


def _demo(args: argparse.Namespace) -> str:
    root = Path(args.output_dir)
    generated = generate_catalog(
        args.datasets,
        output_dir=root / "catalog",
        dataset_kind="mixed",
        segments=3,
        dimensions=2,
        files=2,
        points_per_file=args.points_per_file,
        seed=args.seed,
    )
    survey = load_survey(catalog_path=generated.metadata_path)
    analysis = analyze_survey(survey, drilling=_drilling(args), formation=args.formation or None)
    result = export_bundle(analysis, root / "analysis", top_n=args.top_n, plots=not args.no_plots)
    return f"catalog={generated.metadata_path}\n" + _render_export(
        result.output_dir, result.summary, result.plot_error
    )


def _survey_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Seismic catalog generator output directory. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    parser.add_argument("--catalog-path", type=Path, help="Specific run catalog.json to analyze.")
    parser.add_argument("--visualization-path", type=Path, help="Specific visualization CSV.")


def _evidence_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--drilling-data-dir",
        type=Path,
        help=f"Use-case-1 data directory. Defaults to {DEFAULT_DRILLING_DATA_DIR} when present.",
    )
    parser.add_argument(
        "--formation",
        default="Wolfcamp A",
        help="Analog formation for precedents and thresholds. Use '' for all formations.",
    )


def _tuning_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--score-threshold", type=float, default=0.5, help="Fault score threshold.")
    parser.add_argument("--cell-size", type=float, default=100.0, help="Fracture cell size (m).")
    parser.add_argument("--radius", type=float, default=300.0, help="Well screening radius (m).")


def _settings(args: argparse.Namespace) -> AnalysisSettings:
    return AnalysisSettings(
        faults=FaultDetectionConfig(score_threshold=args.score_threshold),
        fractures=FractureConfig(cell_size_m=args.cell_size),
        hazards=HazardConfig(radius_m=args.radius),
    )


def _drilling(args: argparse.Namespace) -> DrillingEvidence | None:
    if args.drilling_data_dir is not None:
        return load_drilling_evidence(args.drilling_data_dir)
    if DEFAULT_DRILLING_DATA_DIR.is_dir():
        return load_drilling_evidence(DEFAULT_DRILLING_DATA_DIR)
    return None


def _selected_wells(args: argparse.Namespace, wells: list[WellLocation]) -> list[WellLocation]:
    if args.at:
        inline, crossline = parse_location(args.at)
        return [
            WellLocation(f"site_{inline:.0f}_{crossline:.0f}", "planned site", inline, crossline)
        ]
    if args.well:
        selected = [well for well in wells if well.id == args.well]
        if not selected:
            known = ", ".join(well.id for well in wells) or "none"
            raise SubsurfaceDataError(f"well {args.well!r} is not in the catalog (known: {known})")
        return selected
    if not wells:
        raise SubsurfaceDataError("the catalog has no wells; pass --at INLINE,CROSSLINE")
    return wells


def _render_export(output_dir: Path, summary: dict[str, Any], plot_error: str) -> str:
    lines = [
        f"analysis_dir={output_dir}",
        f"atlas={output_dir / 'hazard_atlas.html'}",
        f"summary={output_dir / 'summary.json'}",
        f"manifest={output_dir / 'manifest.json'}",
        "faults={faults_detected} corridors={fracture_corridors} wells={wells_screened} "
        "highest_risk={highest_risk_well}:{highest_risk_index}".format(**summary),
    ]
    if summary.get("fault_detection_recall") is not None:
        lines.append(
            f"fault_detection recall={summary['fault_detection_recall']} "
            f"precision={summary['fault_detection_precision']}"
        )
    if summary.get("drilling_data_dir") is None:
        lines.append("drilling_evidence=not loaded (no precedents cited)")
    if plot_error:
        lines.append(f"plots=skipped ({plot_error})")
    return "\n".join(lines)


def _render_faults(analysis: SurveyAnalysis, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(
            {"faults": to_jsonable(analysis.faults), "scorecard": to_jsonable(analysis.scorecard)},
            indent=2,
        )
    if not analysis.faults:
        return "No faults detected at the configured score threshold."
    lines = ["id   inline@ref  strike  length_m  throw_m  half_width_m  samples"]
    for fault in analysis.faults:
        throw = "n/a" if fault.throw_m is None else f"{fault.throw_m:.0f}"
        lines.append(
            f"{fault.id:<4} {fault.intercept_inline_m:>10,.0f}  {fault.strike_azimuth_deg:>5.1f}°"
            f"  {fault.length_m:>8,.0f}  {throw:>7}  {fault.damage_zone_half_width_m:>12.0f}"
            f"  {fault.support_points:>7}"
        )
    if analysis.scorecard is not None:
        card = analysis.scorecard
        lines.append(
            f"catalog scorecard: matched {card.matched}/{card.catalog_faults}, recall "
            f"{card.recall:.2f}, precision {card.precision:.2f} (synthetic ground truth)"
        )
    return "\n".join(lines)


def _render_fractures(analysis: SurveyAnalysis, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(to_jsonable(analysis.corridors), indent=2)
    if not analysis.corridors:
        return "No fracture corridor reached the minimum size."
    lines = ["id   cells  length_m  width_m  strike  mean_p90  origin              nearest_fault"]
    for corridor in analysis.corridors:
        lines.append(
            f"{corridor.id:<4} {corridor.cell_count:>5}  {corridor.length_m:>8,.0f}  "
            f"{corridor.width_m:>7,.0f}  {corridor.strike_azimuth_deg:>5.1f}°  "
            f"{corridor.mean_p90_intensity:>8.2f}  {corridor.origin:<18}  "
            f"{corridor.nearest_fault_id or '-'} ({corridor.nearest_fault_distance_m} m)"
        )
    return "\n".join(lines)


def _render_targets(analysis: SurveyAnalysis, *, top_n: int, as_json: bool) -> str:
    rows = [score_row(score) for score in top_scores(score_points(analysis), "target_score", top_n)]
    if as_json:
        return json.dumps(rows, indent=2)
    lines = [f"Top {len(rows)} reservoir target samples from {analysis.survey.points_path.name}"]
    for row in rows:
        lines.append(
            f"row {row['row']}: target {row['target_score']} hazard {row['hazard_score']} "
            f"{row['lithology']} at inline {row['inline_m']}, crossline {row['crossline_m']}, "
            f"depth {row['depth_m']} m; nearest well {row['nearest_well_id'] or '-'}"
        )
    return "\n".join(lines)


def _render_wells(analysis: SurveyAnalysis, *, as_json: bool) -> str:
    briefs = analysis.ranked_briefs()
    if as_json:
        return json.dumps(
            {
                "summary": analysis_summary(analysis),
                "thresholds": to_jsonable(analysis.thresholds),
                "briefs": to_jsonable(briefs),
            },
            indent=2,
        )
    sections = [_render_brief(brief, analysis) for brief in briefs]
    if analysis.formation and analysis.drilling is not None and not analysis.thresholds:
        sections.append(
            f"anomaly_thresholds.csv has no rows for {analysis.formation!r}; "
            "no operating envelope is claimed."
        )
    return "\n\n".join(sections)


def _render_brief(brief: WellBrief, analysis: SurveyAnalysis) -> str:
    screen = brief.screen
    fault = (
        "no fault detected"
        if screen.nearest_fault_distance_m is None
        else f"{screen.nearest_fault_distance_m:.0f} m to {screen.nearest_fault_id}"
    )
    lines = [
        (
            f"{screen.well.id}: screening index {screen.risk_index:.0f} ({screen.risk_class}); "
            f"{fault}; P90 fracture {screen.p90_fracture_intensity}"
        ),
        f"  seismic evidence: {analysis.survey.points_path.name} rows "
        + ", ".join(str(row) for row in screen.evidence_rows),
    ]
    if not screen.hazards:
        lines.append("  no hazard rule triggered")
    for hazard in screen.hazards:
        lines.append(f"  - {hazard.title}: {hazard.measured}")
    for precedent in brief.precedents:
        lines.append(f"    {precedent.hazard}: {precedent.note}")
        for incident in precedent.incidents[:3]:
            lines.append(
                f"      {incident.incident_id} {incident.well_name}: {incident.root_cause} -> "
                f"{incident.resolution}, {incident.hours_lost:.1f} h, ${incident.cost_usd:,.0f} "
                f"[{incident.citation.text()}]"
            )
        for passage in precedent.references:
            first = passage.excerpt[0] if passage.excerpt else ""
            lines.append(f"      ref: {first} [{passage.citation.text()}]")
    if analysis.drilling is None:
        lines.append("  drilling evidence not loaded; no precedents cited")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
