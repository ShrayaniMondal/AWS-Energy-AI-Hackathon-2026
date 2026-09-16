"""Self-contained HTML hazard atlas rendered with inline SVG and no dependencies.

Color roles follow the validated reference palette: one blue ramp for fracture
magnitude, ink for fault traces, three categorical slots plus neutral gray for
lithology, and reserved status colors (always labelled) for well risk classes.
"""

from __future__ import annotations

import html
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable

from aws_ai_energy.subsurface.analysis import SurveyAnalysis, WellBrief
from aws_ai_energy.subsurface.drilling import NptIncident
from aws_ai_energy.subsurface.points import SeismicPoint, percentile

FRACTURE_BINS = (0.15, 0.25, 0.35, 0.45, 0.55, 0.70)
RISK_GLYPHS = {"low": "✓", "moderate": "!", "high": "▲", "severe": "✖"}
LITHOLOGY_SLOTS = {
    "channel_sand": "lith-1",
    "fault_damage_zone": "lith-2",
    "carbonate_basement": "lith-3",
}
SECTION_POINT_LIMIT = 1_200


def render_atlas(
    analysis: SurveyAnalysis,
    *,
    generated_at: str,
    export_files: Iterable[str] = (),
) -> str:
    ranked = analysis.ranked_briefs()
    top = ranked[0] if ranked else None
    section_svg, section_data = _section_svg(analysis, top) if top else ("", "[]")
    body = [
        "<header class='page-head'>",
        "<p class='eyebrow'>Drilling Hazard Copilot · screening atlas</p>",
        "<h1>Subsurface hazard atlas</h1>",
        (
            "<p class='lede'>Faults and fracture corridors detected from the seismic catalog, "
            "screened around each well and linked to cited drilling precedents.</p>"
        ),
        _badges(analysis, generated_at),
        "</header>",
        _stat_tiles(analysis),
        _panel(
            "Map view: fracture intensity, faults, and wells",
            "Cells show P90 fracture intensity per 100 m cell. Lines are detected fault traces; "
            "bands are their damage zones. Well markers carry the screening class.",
            _map_legend() + _map_svg(analysis),
        ),
        _panel(
            "Well screening index",
            "0–100 index from fixed weights (fault proximity 40, fracture 30, sand 15, throw 15). "
            "It ranks locations in this survey; it is not calibrated against drilling outcomes.",
            _risk_bars_svg(analysis),
        ),
    ]
    if top is not None:
        body.append(
            _panel(
                f"Section through {top.screen.well.id}",
                "Depth versus inline for samples within 80 m of the well's crossline, from one "
                "catalog dimension group so horizons align. Vertical rules are fault positions.",
                _section_legend() + section_svg,
            )
        )
        body.append(_brief_html(analysis, top))
    body.append(_tables_html(analysis))
    exports = list(export_files)
    if exports:
        items = "".join(f"<li><code>{_e(name)}</code></li>" for name in exports)
        body.append(_panel("Exported files", "Written alongside this atlas.", f"<ul>{items}</ul>"))

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Subsurface Hazard Atlas</title>"
        f"<style>{CSS}</style></head><body><main class='viz-root'>"
        + "".join(body)
        + "<div id='tip' class='tip' role='status' hidden></div>"
        + "<script type='application/json' id='section-data'>"
        + section_data.replace("</", "<\\/")
        + "</script>"
        + f"<script>{JS}</script></main></body></html>"
    )


def _badges(analysis: SurveyAnalysis, generated_at: str) -> str:
    survey = analysis.survey
    parts = [
        (
            "<span class='badge'>Seismic: generated catalog run "
            f"<code>{_e(survey.catalog_run_id or 'n/a')}</code> (synthetic)</span>"
        ),
        (
            f"<span class='badge'>{len(survey.points):,} samples from "
            f"<code>{_e(survey.points_path.name)}</code></span>"
        ),
    ]
    if analysis.drilling is not None:
        parts.append(
            "<span class='badge'>Drilling precedents: hackathon use case 1 "
            f"<code>{_e(analysis.drilling.data_dir.name)}</code></span>"
        )
    if analysis.formation:
        parts.append(f"<span class='badge'>Analog formation: {_e(analysis.formation)}</span>")
    parts.append(f"<span class='badge'>Generated {_e(generated_at)}</span>")
    return "<p class='badges'>" + "".join(parts) + "</p>"


def _stat_tiles(analysis: SurveyAnalysis) -> str:
    ranked = analysis.ranked_briefs()
    tiles = [
        ("Faults detected", str(len(analysis.faults)), ""),
        ("Fracture corridors", str(len(analysis.corridors)), ""),
        ("Wells screened", str(len(analysis.briefs)), ""),
    ]
    if ranked:
        screen = ranked[0].screen
        tiles.append(
            (
                "Highest screening index",
                f"{screen.risk_index:.0f}",
                f"{screen.well.id} · {RISK_GLYPHS[screen.risk_class]} {screen.risk_class}",
            )
        )
    if analysis.scorecard is not None:
        card = analysis.scorecard
        tiles.append(
            (
                "Fault detection vs catalog",
                f"{card.matched}/{card.catalog_faults}",
                f"recall {card.recall:.2f} · precision {card.precision:.2f}",
            )
        )
    html_tiles = "".join(
        f"<div class='tile'><div class='tile-label'>{_e(label)}</div>"
        f"<div class='tile-value'>{_e(value)}</div>"
        f"<div class='tile-note'>{_e(note)}</div></div>"
        for label, value, note in tiles
    )
    return f"<section class='tiles'>{html_tiles}</section>"


def _panel(title: str, subtitle: str, content: str) -> str:
    return (
        f"<section class='panel'><h2>{_e(title)}</h2>"
        f"<p class='sub'>{_e(subtitle)}</p>{content}</section>"
    )


def _map_legend() -> str:
    swatches = []
    labels = ["<0.15", *[f"{value:.2f}+" for value in FRACTURE_BINS]]
    for index, label in enumerate(labels):
        swatches.append(
            f"<span class='key'><svg width='14' height='14' aria-hidden='true'>"
            f"<rect width='14' height='14' rx='2' class='seq-{index}'/></svg>{_e(label)}</span>"
        )
    status = "".join(
        f"<span class='key'><svg width='14' height='14' aria-hidden='true'>"
        f"<circle cx='7' cy='7' r='5' class='risk-{name}'/></svg>{RISK_GLYPHS[name]} {name}</span>"
        for name in RISK_GLYPHS
    )
    return (
        "<div class='legend'>"
        "<span class='legend-title'>P90 fracture intensity</span>" + "".join(swatches)
        + "<span class='key muted-note'>blank = no samples</span></div>"
        "<div class='legend'>"
        "<span class='key'><svg width='22' height='14' aria-hidden='true'>"
        "<line x1='1' y1='7' x2='21' y2='7' class='fault-line'/></svg>fault trace</span>"
        "<span class='key'><svg width='22' height='14' aria-hidden='true'>"
        "<rect x='1' y='2' width='20' height='10' class='damage-band'/></svg>damage zone</span>"
        "<span class='legend-title'>Well screening class</span>" + status + "</div>"
    )


def _map_svg(analysis: SurveyAnalysis) -> str:
    survey = analysis.survey
    cell_size = analysis.settings.fractures.cell_size_m
    inline_lo, inline_hi = _padded_extent(survey.inline_extent_m, cell_size)
    cross_lo, cross_hi = _padded_extent(survey.crossline_extent_m, cell_size)
    left, top, right, bottom = 64.0, 12.0, 16.0, 44.0
    plot_width = 880.0
    scale = plot_width / (inline_hi - inline_lo)
    plot_height = (cross_hi - cross_lo) * scale
    width, height = left + plot_width + right, top + plot_height + bottom

    def sx(inline: float) -> float:
        return left + (inline - inline_lo) * scale

    def sy(crossline: float) -> float:
        return top + (cross_hi - crossline) * scale

    parts = [_svg_open("map-svg", width, height, "Map view of fracture intensity and faults")]
    parts.append(_grid_and_axes(left, top, plot_width, plot_height, inline_lo, inline_hi, cross_lo,
                                cross_hi, sx, sy, "Inline (m)", "Crossline (m)", invert_y=False))

    corridor_by_cell = {
        cell_id: corridor.id for corridor in analysis.corridors for cell_id in corridor.cell_ids
    }
    gap = 1.0
    parts.append("<g class='cells'>")
    for cell in analysis.cells:
        x = sx(cell.ix * cell_size)
        y = sy((cell.iy + 1) * cell_size)
        size = cell_size * scale
        corridor_label = corridor_by_cell.get(cell.id)
        tip = (
            f"P90 fracture {cell.p90_intensity:.2f} ({cell.fracture_class})\n"
            f"cell {cell.id} · {cell.point_count} samples"
            + (f"\ncorridor {corridor_label}" if corridor_label else "")
        )
        parts.append(
            f"<rect x='{x + gap / 2:.1f}' y='{y + gap / 2:.1f}' width='{size - gap:.1f}' "
            f"height='{size - gap:.1f}' rx='1.5' class='seq-{_fracture_bin(cell.p90_intensity)}' "
            f"data-tip='{_e(tip)}'/>"
        )
    parts.append("</g>")

    for fault in analysis.faults:
        half = fault.damage_zone_half_width_m * math.hypot(1.0, fault.slope)
        (x0, y0), (x1, y1) = fault.trace()
        band = [
            (sx(x0 - half), sy(y0)),
            (sx(x1 - half), sy(y1)),
            (sx(x1 + half), sy(y1)),
            (sx(x0 + half), sy(y0)),
        ]
        points_attr = " ".join(f"{px:.1f},{py:.1f}" for px, py in band)
        throw = "n/a" if fault.throw_m is None else f"{fault.throw_m:.0f} m"
        tip = (
            f"{fault.id} · throw {throw}\nstrike {fault.strike_azimuth_deg:.0f}° · length "
            f"{fault.length_m:,.0f} m\ndamage half-width {fault.damage_zone_half_width_m:.0f} m · "
            f"{fault.support_points} samples"
        )
        parts.append(f"<polygon points='{points_attr}' class='damage-band'/>")
        parts.append(
            f"<line x1='{sx(x0):.1f}' y1='{sy(y0):.1f}' x2='{sx(x1):.1f}' y2='{sy(y1):.1f}' "
            f"class='fault-line'/>"
            f"<line x1='{sx(x0):.1f}' y1='{sy(y0):.1f}' x2='{sx(x1):.1f}' y2='{sy(y1):.1f}' "
            f"class='hit-line' tabindex='0' data-tip='{_e(tip)}'/>"
        )
        label_x, label_y = sx(x1), sy(y1) - 6
        parts.append(f"<text x='{label_x:.1f}' y='{label_y:.1f}' class='label halo' "
                     f"text-anchor='middle'>{_e(fault.id)}</text>")

    for corridor in analysis.corridors:
        parts.append(
            f"<text x='{sx(corridor.centroid_inline_m) + 14:.1f}' "
            f"y='{sy(corridor.centroid_crossline_m) + 4:.1f}' class='label muted halo'>"
            f"{_e(corridor.id)}</text>"
        )

    ordered = sorted(analysis.briefs, key=lambda brief: brief.screen.well.inline_m)
    for index, brief in enumerate(ordered):
        screen = brief.screen
        x, y = sx(screen.well.inline_m), sy(screen.well.crossline_m)
        label_dy = -9.0 if index % 2 == 0 else 19.0
        fault_text = (
            "no fault detected"
            if screen.nearest_fault_distance_m is None
            else f"{screen.nearest_fault_distance_m:.0f} m to {screen.nearest_fault_id}"
        )
        tip = (
            f"{screen.well.id} · index {screen.risk_index:.0f} ({screen.risk_class})\n{fault_text}\n"
            + ("; ".join(hazard.hazard for hazard in screen.hazards) or "no hazards triggered")
        )
        parts.append(
            f"<g class='well' tabindex='0' data-tip='{_e(tip)}'>"
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='14' class='hit'/>"
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='6' class='risk-{screen.risk_class} ring'/>"
            f"<text x='{x + 10:.1f}' y='{y + label_dy:.1f}' class='label halo'>{_e(screen.well.id)} "
            f"{RISK_GLYPHS[screen.risk_class]}</text></g>"
        )
    parts.append("</svg>")
    return "".join(parts)


def _risk_bars_svg(analysis: SurveyAnalysis) -> str:
    ranked = analysis.ranked_briefs()
    if not ranked:
        return "<p class='empty'>No wells were screened.</p>"
    left, top, right, bottom = 96.0, 8.0, 150.0, 36.0
    band, thickness = 30.0, 18.0
    plot_width = 640.0
    plot_height = band * len(ranked)
    width, height = left + plot_width + right, top + plot_height + bottom

    def sx(value: float) -> float:
        return left + value / 100.0 * plot_width

    parts = [_svg_open("bars-svg", width, height, "Well screening index ranking")]
    for tick in (0, 25, 50, 75, 100):
        parts.append(
            f"<line x1='{sx(tick):.1f}' y1='{top:.1f}' x2='{sx(tick):.1f}' "
            f"y2='{top + plot_height:.1f}' class='{'axis' if tick == 0 else 'grid'}'/>"
            f"<text x='{sx(tick):.1f}' y='{top + plot_height + 18:.1f}' class='tick' "
            f"text-anchor='middle'>{tick}</text>"
        )
    parts.append(
        f"<text x='{left + plot_width / 2:.1f}' y='{height - 4:.1f}' class='axis-title' "
        "text-anchor='middle'>Screening index (0–100)</text>"
    )
    for index, brief in enumerate(ranked):
        screen = brief.screen
        y = top + index * band + (band - thickness) / 2
        end = sx(screen.risk_index)
        radius = min(4.0, max(0.0, end - left))
        path = (
            f"M{left:.1f},{y:.1f} H{end - radius:.1f} Q{end:.1f},{y:.1f} {end:.1f},{y + radius:.1f} "
            f"V{y + thickness - radius:.1f} Q{end:.1f},{y + thickness:.1f} "
            f"{end - radius:.1f},{y + thickness:.1f} H{left:.1f} Z"
        )
        tip = f"{screen.risk_index:.1f}\n{screen.well.id} · {screen.risk_class}"
        parts.append(
            f"<g tabindex='0' data-tip='{_e(tip)}'>"
            f"<rect x='0' y='{top + index * band:.1f}' width='{width:.1f}' height='{band:.1f}' "
            "class='hit'/>"
            f"<path d='{path}' class='risk-{screen.risk_class}'/>"
            f"<text x='{left - 10:.1f}' y='{y + thickness - 5:.1f}' class='tick' "
            f"text-anchor='end'>{_e(screen.well.id)}</text>"
            f"<text x='{end + 8:.1f}' y='{y + thickness - 5:.1f}' class='value'>"
            f"{screen.risk_index:.0f} · {RISK_GLYPHS[screen.risk_class]} {screen.risk_class}</text>"
            "</g>"
        )
    parts.append("</svg>")
    return "".join(parts)


def _section_legend() -> str:
    keys = [
        ("lith-1", "channel sand"),
        ("lith-2", "fault damage zone"),
        ("lith-3", "carbonate basement"),
        ("lith-other", "shale"),
    ]
    items = "".join(
        f"<span class='key'><svg width='14' height='14' aria-hidden='true'>"
        f"<circle cx='7' cy='7' r='5' class='{css}'/></svg>{_e(label)}</span>"
        for css, label in keys
    )
    return (
        "<div class='legend'><span class='legend-title'>Lithology</span>" + items +
        "<span class='key'><svg width='22' height='14' aria-hidden='true'>"
        "<line x1='1' y1='7' x2='21' y2='7' class='horizon-line'/></svg>reservoir top / base</span>"
        "</div>"
    )


def _section_svg(analysis: SurveyAnalysis, brief: WellBrief) -> tuple[str, str]:
    well = brief.screen.well
    band = [
        point
        for point in analysis.survey.points
        if abs(point.crossline_m - well.crossline_m) <= 80.0
    ]
    if not band:
        return "<p class='empty'>No samples within 80 m of this crossline.</p>", "[]"
    group = Counter(point.dimensionid for point in band).most_common(1)[0][0]
    members = [point for point in band if point.dimensionid == group]
    step = max(1, math.ceil(len(members) / SECTION_POINT_LIMIT))
    shown = members[::step]

    inline_lo, inline_hi = _padded_extent(analysis.survey.inline_extent_m, 500.0)
    depths = [point.depth_m for point in members] + [
        value for point in members for value in (point.horizon_top_m, point.horizon_base_m)
    ]
    if well.target_depth_m is not None:
        depths.append(well.target_depth_m)
    depth_lo, depth_hi = _padded_extent((min(depths), max(depths)), 100.0)
    left, top, right, bottom = 64.0, 22.0, 120.0, 44.0
    plot_width, plot_height = 820.0, 380.0
    width, height = left + plot_width + right, top + plot_height + bottom

    def sx(inline: float) -> float:
        return left + (inline - inline_lo) / (inline_hi - inline_lo) * plot_width

    def sy(depth: float) -> float:
        return top + (depth - depth_lo) / (depth_hi - depth_lo) * plot_height

    parts = [_svg_open("section-svg", width, height, f"Depth section through {well.id}")]
    parts.append(_grid_and_axes(left, top, plot_width, plot_height, inline_lo, inline_hi, depth_lo,
                                depth_hi, sx, sy, "Inline (m)", "Depth (m)", invert_y=True,
                                y_step=100.0))

    for name, attribute in (("top", "horizon_top_m"), ("base", "horizon_base_m")):
        line = _horizon_polyline(members, attribute)
        if len(line) >= 2:
            coordinates = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in line)
            parts.append(f"<polyline points='{coordinates}' class='horizon-line'/>")
            end_x, end_y = line[-1]
            parts.append(f"<text x='{sx(end_x) + 6:.1f}' y='{sy(end_y) + 4:.1f}' "
                         f"class='label muted halo'>reservoir {name}</text>")

    data = []
    for point in shown:
        css = LITHOLOGY_SLOTS.get(point.lithology, "lith-other")
        x, y = sx(point.inline_m), sy(point.depth_m)
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' class='{css} dot'/>")
        data.append(
            [
                round(x, 1),
                round(y, 1),
                (
                    f"{point.depth_m:,.0f} m · {point.lithology.replace('_', ' ')}\n"
                    f"inline {point.inline_m:,.0f} m · fracture {point.fracture_intensity:.2f} · "
                    f"coherence {point.coherence:.2f}\nCSV row {point.row}"
                ),
            ]
        )

    for fault in analysis.faults:
        inline = fault.inline_at(well.crossline_m)
        if inline_lo <= inline <= inline_hi:
            parts.append(
                f"<line x1='{sx(inline):.1f}' y1='{top:.1f}' x2='{sx(inline):.1f}' "
                f"y2='{top + plot_height:.1f}' class='fault-rule'/>"
                f"<text x='{sx(inline):.1f}' y='{top - 6:.1f}' class='label' "
                f"text-anchor='middle'>{_e(fault.id)}</text>"
            )

    well_x = sx(well.inline_m)
    target = well.target_depth_m if well.target_depth_m is not None else depth_hi
    parts.append(
        f"<line x1='{well_x:.1f}' y1='{top:.1f}' x2='{well_x:.1f}' y2='{sy(target):.1f}' "
        f"class='well-path'/>"
        f"<circle cx='{well_x:.1f}' cy='{sy(target):.1f}' r='6' "
        f"class='risk-{brief.screen.risk_class} ring'/>"
        f"<text x='{well_x + 10:.1f}' y='{sy(target) + 4:.1f}' class='label halo'>"
        f"{_e(well.id)} TD {RISK_GLYPHS[brief.screen.risk_class]}</text>"
        f"<circle id='section-focus' r='7' class='focus-ring' cx='-20' cy='-20'/>"
    )
    parts.append("</svg>")
    return "".join(parts), json.dumps(data)


def _brief_html(analysis: SurveyAnalysis, brief: WellBrief) -> str:
    screen = brief.screen
    rows = "".join(
        f"<tr><td>{_e(hazard.title)}</td><td><code>{_e(hazard.hazard)}</code></td>"
        f"<td>{_e(hazard.measured)}</td></tr>"
        for hazard in screen.hazards
    ) or "<tr><td colspan='3'>No hazard rule triggered for this location.</td></tr>"
    parts = [
        f"<section class='panel'><h2>Drilling brief: {_e(screen.well.id)}</h2>",
        (
            f"<p class='sub'>Screening index {screen.risk_index:.0f} "
            f"({RISK_GLYPHS[screen.risk_class]} {screen.risk_class}). Seismic evidence rows: "
            f"{_e(', '.join(str(row) for row in screen.evidence_rows))} in "
            f"<code>{_e(analysis.survey.points_path.name)}</code>.</p>"
        ),
        (
            "<table><thead><tr><th>Seismic observation</th><th>Rule</th><th>Measured</th></tr>"
            f"</thead><tbody>{rows}</tbody></table>"
        ),
    ]
    if analysis.drilling is None:
        parts.append(
            "<p class='empty'>No drilling evidence directory was supplied, so no precedents are "
            "shown.</p>"
        )
    for precedent in brief.precedents:
        parts.append(f"<h3>{_e(precedent.hazard)} → {_e(', '.join(precedent.npt_categories))}</h3>")
        parts.append(f"<p class='sub'>{_e(precedent.note)}</p>")
        if precedent.incidents:
            parts.append(_incident_table(list(precedent.incidents)))
        for passage in precedent.references:
            excerpt = "".join(f"<li>{_e(_strip_list_marker(line))}</li>" for line in passage.excerpt)
            parts.append(
                f"<blockquote><p class='cite'>{_e(passage.citation.text())}</p>"
                f"<ul>{excerpt}</ul></blockquote>"
            )
        for missing in precedent.missing_references:
            parts.append(f"<p class='empty'>Reference not found: {_e(missing)}</p>")
    parts.append("</section>")
    return "".join(parts)


def _incident_table(incidents: list[NptIncident]) -> str:
    rows = "".join(
        f"<tr><td>{_e(incident.incident_id)}</td><td>{_e(incident.well_name)}</td>"
        f"<td>{_e(incident.formation)}</td><td>{_e(incident.root_cause)}</td>"
        f"<td>{_e(incident.resolution)}</td><td class='num'>{incident.hours_lost:,.1f}</td>"
        f"<td class='num'>${incident.cost_usd:,.0f}</td>"
        f"<td class='cite'>{_e(incident.citation.text())}</td></tr>"
        for incident in incidents
    )
    return (
        "<table><thead><tr><th>Incident</th><th>Well</th><th>Formation</th><th>Root cause</th>"
        "<th>Resolution</th><th class='num'>Hours</th><th class='num'>Cost</th><th>Source</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def _tables_html(analysis: SurveyAnalysis) -> str:
    matches = {}
    if analysis.scorecard is not None:
        matches = {
            match.detected_fault_id: match
            for match in analysis.scorecard.matches
            if match.detected_fault_id
        }
    fault_rows = "".join(
        f"<tr><td>{_e(fault.id)}</td><td class='num'>{fault.intercept_inline_m:,.0f}</td>"
        f"<td class='num'>{fault.strike_azimuth_deg:.1f}°</td>"
        f"<td class='num'>{fault.length_m:,.0f}</td>"
        f"<td class='num'>{_num(fault.throw_m, 0)}</td>"
        f"<td class='num'>{fault.damage_zone_half_width_m:.0f}</td>"
        f"<td class='num'>{fault.support_points}</td>"
        f"<td class='num'>{fault.mean_coherence:.2f}</td>"
        f"<td>{_match_text(matches.get(fault.id))}</td></tr>"
        for fault in analysis.faults
    ) or "<tr><td colspan='9'>No faults detected at the configured threshold.</td></tr>"
    corridor_rows = "".join(
        f"<tr><td>{_e(corridor.id)}</td><td class='num'>{corridor.cell_count}</td>"
        f"<td class='num'>{corridor.length_m:,.0f} × {corridor.width_m:,.0f}</td>"
        f"<td class='num'>{corridor.strike_azimuth_deg:.1f}°</td>"
        f"<td class='num'>{corridor.mean_p90_intensity:.2f}</td>"
        f"<td>{_e(corridor.origin.replace('_', ' '))}</td>"
        f"<td>{_e(corridor.nearest_fault_id or '—')} ({_num(corridor.nearest_fault_distance_m, 0)} m)"
        "</td></tr>"
        for corridor in analysis.corridors
    ) or "<tr><td colspan='7'>No corridor reached the minimum size.</td></tr>"
    well_rows = "".join(
        f"<tr><td>{_e(b.screen.well.id)}</td><td class='num'>{b.screen.risk_index:.1f}</td>"
        f"<td>{RISK_GLYPHS[b.screen.risk_class]} {_e(b.screen.risk_class)}</td>"
        f"<td>{_e(b.screen.nearest_fault_id or '—')}</td>"
        f"<td class='num'>{_num(b.screen.nearest_fault_distance_m, 0)}</td>"
        f"<td class='num'>{_num(b.screen.p90_fracture_intensity, 2)}</td>"
        f"<td>{_e(', '.join(h.hazard for h in b.screen.hazards) or 'none')}</td></tr>"
        for b in analysis.ranked_briefs()
    )
    if analysis.formation and analysis.thresholds:
        threshold_rows = "".join(
            f"<tr><td>{_e(row.parameter)}</td><td class='num'>{_e(row.low_critical)}</td>"
            f"<td class='num'>{_e(row.low_warning)}</td><td class='num'>{_e(row.high_warning)}</td>"
            f"<td class='num'>{_e(row.high_critical)}</td><td>{_e(row.unit)}</td>"
            f"<td class='cite'>{_e(row.citation.text())}</td></tr>"
            for row in analysis.thresholds
        )
        thresholds = (
            "<table><thead><tr><th>Parameter</th><th class='num'>Low critical</th>"
            "<th class='num'>Low warning</th><th class='num'>High warning</th>"
            "<th class='num'>High critical</th><th>Unit</th><th>Source</th></tr></thead>"
            f"<tbody>{threshold_rows}</tbody></table>"
        )
    elif analysis.formation and analysis.drilling is not None:
        thresholds = (
            f"<p class='empty'>anomaly_thresholds.csv has no rows for "
            f"{_e(analysis.formation)}; no operating envelope is claimed.</p>"
        )
    else:
        thresholds = "<p class='empty'>No analog formation selected.</p>"

    return (
        _panel(
            "Detected faults",
            "Attribute-based detection (fault likelihood and coherence loss); the last column "
            "compares against the generator's synthetic fault table.",
            "<table><thead><tr><th>Fault</th><th class='num'>Inline at ref (m)</th>"
            "<th class='num'>Strike</th><th class='num'>Length (m)</th>"
            "<th class='num'>Throw (m)</th><th class='num'>Half-width (m)</th>"
            "<th class='num'>Samples</th><th class='num'>Coherence</th><th>Catalog match</th>"
            f"</tr></thead><tbody>{fault_rows}</tbody></table>",
        )
        + _panel(
            "Fracture corridors",
            "Connected high-intensity cells, attributed to the nearest fault or well.",
            "<table><thead><tr><th>Corridor</th><th class='num'>Cells</th>"
            "<th class='num'>Length × width (m)</th><th class='num'>Strike</th>"
            "<th class='num'>Mean P90</th><th>Origin</th><th>Nearest fault</th></tr></thead>"
            f"<tbody>{corridor_rows}</tbody></table>",
        )
        + _panel(
            "Well screening table",
            "Table view of the map markers and ranking bars.",
            "<table><thead><tr><th>Well</th><th class='num'>Index</th><th>Class</th>"
            "<th>Nearest fault</th><th class='num'>Distance (m)</th>"
            "<th class='num'>P90 fracture</th><th>Hazards</th></tr></thead>"
            f"<tbody>{well_rows}</tbody></table>",
        )
        + _panel(
            f"Operating envelope{': ' + analysis.formation if analysis.formation else ''}",
            "Per-formation thresholds from the use-case-1 anomaly table.",
            thresholds,
        )
    )


def _match_text(match: object) -> str:
    if match is None:
        return "—"
    offset = getattr(match, "mean_trace_offset_m", None)
    throw_error = getattr(match, "throw_error_m", None)
    catalog_id = getattr(match, "catalog_fault_id", "?")
    throw_text = "" if throw_error is None else f", throw error {throw_error:+.0f} m"
    return _e(f"catalog fault {catalog_id}: offset {offset:.0f} m{throw_text}")


def _horizon_polyline(members: list[SeismicPoint], attribute: str) -> list[tuple[float, float]]:
    bins: dict[int, list[float]] = defaultdict(list)
    for point in members:
        bins[math.floor(point.inline_m / 100.0)].append(float(getattr(point, attribute)))
    return [
        ((index + 0.5) * 100.0, percentile(values, 0.5))
        for index, values in sorted(bins.items())
    ]


def _grid_and_axes(
    left: float,
    top: float,
    plot_width: float,
    plot_height: float,
    x_lo: float,
    x_hi: float,
    y_lo: float,
    y_hi: float,
    sx: object,
    sy: object,
    x_title: str,
    y_title: str,
    *,
    invert_y: bool,
    x_step: float = 500.0,
    y_step: float = 500.0,
) -> str:
    assert callable(sx) and callable(sy)
    parts = []
    tick = math.ceil(x_lo / x_step) * x_step
    while tick <= x_hi + 1e-6:
        x = sx(tick)
        parts.append(
            f"<line x1='{x:.1f}' y1='{top:.1f}' x2='{x:.1f}' y2='{top + plot_height:.1f}' "
            "class='grid'/>"
            f"<text x='{x:.1f}' y='{top + plot_height + 18:.1f}' class='tick' "
            f"text-anchor='middle'>{tick:,.0f}</text>"
        )
        tick += x_step
    tick = math.ceil(y_lo / y_step) * y_step
    while tick <= y_hi + 1e-6:
        y = sy(tick)
        parts.append(
            f"<line x1='{left:.1f}' y1='{y:.1f}' x2='{left + plot_width:.1f}' y2='{y:.1f}' "
            "class='grid'/>"
            f"<text x='{left - 8:.1f}' y='{y + 4:.1f}' class='tick' text-anchor='end'>"
            f"{tick:,.0f}</text>"
        )
        tick += y_step
    baseline_y = top if invert_y else top + plot_height
    parts.append(
        f"<line x1='{left:.1f}' y1='{baseline_y:.1f}' x2='{left + plot_width:.1f}' "
        f"y2='{baseline_y:.1f}' class='axis'/>"
        f"<line x1='{left:.1f}' y1='{top:.1f}' x2='{left:.1f}' y2='{top + plot_height:.1f}' "
        "class='axis'/>"
        f"<text x='{left + plot_width / 2:.1f}' y='{top + plot_height + 38:.1f}' "
        f"class='axis-title' text-anchor='middle'>{_e(x_title)}</text>"
        f"<text x='14' y='{top + plot_height / 2:.1f}' class='axis-title' text-anchor='middle' "
        f"transform='rotate(-90 14 {top + plot_height / 2:.1f})'>{_e(y_title)}</text>"
    )
    return "".join(parts)


def _svg_open(element_id: str, width: float, height: float, label: str) -> str:
    return (
        f"<svg id='{element_id}' viewBox='0 0 {width:.0f} {height:.0f}' role='img' "
        f"aria-label='{_e(label)}' preserveAspectRatio='xMidYMid meet'>"
    )


def _padded_extent(extent: tuple[float, float], step: float) -> tuple[float, float]:
    low = math.floor(extent[0] / step) * step
    high = math.ceil(extent[1] / step) * step
    return (low, high if high > low else low + step)


def _strip_list_marker(line: str) -> str:
    return line[2:] if line.startswith(("- ", "* ")) else line


def _fracture_bin(value: float) -> int:
    return sum(1 for bound in FRACTURE_BINS if value >= bound)


def _num(value: float | None, digits: int) -> str:
    return "—" if value is None else f"{value:,.{digits}f}"


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink-2:#52514e;
--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);
--lith-1:#2a78d6;--lith-2:#eb6834;--lith-3:#1baf7a;--lith-other:#c3c2b7;
--good:#0ca30c;--warning:#fab219;--serious:#ec835a;--critical:#d03b3b;
--seq-0:#cde2fb;--seq-1:#9ec5f4;--seq-2:#6da7ec;--seq-3:#3987e5;--seq-4:#256abf;
--seq-5:#184f95;--seq-6:#0d366b;--band:rgba(11,11,11,.08)}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;
--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink-2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;
--axis:#383835;--border:rgba(255,255,255,.10);--lith-1:#3987e5;--lith-2:#d95926;
--lith-3:#199e70;--lith-other:#52514e;--seq-0:#0d366b;--seq-1:#184f95;--seq-2:#256abf;
--seq-3:#3987e5;--seq-4:#6da7ec;--seq-5:#9ec5f4;--seq-6:#cde2fb;--band:rgba(255,255,255,.10)}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;
--ink-2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
--lith-1:#3987e5;--lith-2:#d95926;--lith-3:#199e70;--lith-other:#52514e;--seq-0:#0d366b;
--seq-1:#184f95;--seq-2:#256abf;--seq-3:#3987e5;--seq-4:#6da7ec;--seq-5:#9ec5f4;
--seq-6:#cde2fb;--band:rgba(255,255,255,.10)}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);
font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
.viz-root{max-width:1120px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:28px;margin:4px 0 8px}h2{font-size:17px;margin:0 0 4px}h3{font-size:14px;margin:18px 0 4px}
.eyebrow{margin:0;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.lede{margin:0 0 12px;color:var(--ink-2);max-width:760px}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin:0}
.badge{border:1px solid var(--border);border-radius:999px;padding:2px 10px;color:var(--ink-2);
font-size:12px;background:var(--surface)}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0}
.tile,.panel{background:var(--surface);border:1px solid var(--border);border-radius:12px}
.tile{padding:14px 16px}.tile-label{color:var(--ink-2);font-size:12px}
.tile-value{font-size:28px;font-weight:600}.tile-note{color:var(--muted);font-size:12px}
.panel{padding:18px;margin:16px 0;overflow-x:auto}
.sub{margin:0 0 12px;color:var(--ink-2);font-size:13px}
.legend{display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;margin:4px 0 8px;
color:var(--ink-2);font-size:12px}
.legend-title{color:var(--ink);font-weight:600}
.key{display:inline-flex;align-items:center;gap:5px}
svg[role='img']{display:block;width:100%;height:auto;min-width:640px}
.key svg{display:inline-block;flex:none}
.grid{stroke:var(--grid);stroke-width:1}.axis{stroke:var(--axis);stroke-width:1}
.tick{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.axis-title{fill:var(--ink-2);font-size:12px}
.label{fill:var(--ink);font-size:12px;font-weight:600}.label.muted{fill:var(--ink-2);font-weight:500}
.value{fill:var(--ink);font-size:12px}
.halo{paint-order:stroke;stroke:var(--surface);stroke-width:3px;stroke-linejoin:round}
.seq-0{fill:var(--seq-0)}.seq-1{fill:var(--seq-1)}.seq-2{fill:var(--seq-2)}.seq-3{fill:var(--seq-3)}
.seq-4{fill:var(--seq-4)}.seq-5{fill:var(--seq-5)}.seq-6{fill:var(--seq-6)}
.cells rect:hover{stroke:var(--ink);stroke-width:1.5}
.damage-band{fill:var(--band)}
.fault-line{stroke:var(--ink);stroke-width:2;stroke-linecap:round}
.fault-rule{stroke:var(--ink);stroke-width:1.5;opacity:.7}
.hit-line{stroke:transparent;stroke-width:18;cursor:default}
.hit{fill:transparent}
.ring{stroke:var(--surface);stroke-width:2}
.well:focus,.hit-line:focus,g[tabindex]:focus{outline:none}
.well:focus .ring,.well:hover .ring{stroke:var(--ink)}
.risk-low{fill:var(--good)}.risk-moderate{fill:var(--warning)}
.risk-high{fill:var(--serious)}.risk-severe{fill:var(--critical)}
.lith-1{fill:var(--lith-1)}.lith-2{fill:var(--lith-2)}.lith-3{fill:var(--lith-3)}
.lith-other{fill:var(--lith-other)}
.dot{stroke:var(--surface);stroke-width:1;opacity:.85}
.horizon-line{fill:none;stroke:var(--ink-2);stroke-width:2;stroke-linejoin:round}
.well-path{stroke:var(--ink);stroke-width:2}
.focus-ring{fill:none;stroke:var(--ink);stroke-width:2;pointer-events:none}
table{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0 10px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid);vertical-align:top}
th{color:var(--ink-2);font-weight:600}
td:first-child{white-space:nowrap}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.cite{color:var(--muted);font-size:12px}
blockquote{margin:8px 0;padding:8px 12px;border-left:3px solid var(--axis);color:var(--ink-2)}
blockquote ul{margin:4px 0 0;padding-left:18px}
.empty{color:var(--ink-2);font-style:italic}
.muted-note{color:var(--muted)}
.tip{position:fixed;z-index:10;pointer-events:none;background:var(--surface);color:var(--ink-2);
border:1px solid var(--border);border-radius:8px;padding:6px 10px;font-size:12px;
box-shadow:0 4px 16px rgba(0,0,0,.12);max-width:320px}
.tip .lead{color:var(--ink);font-weight:600}
"""

JS = """
(() => {
  const tip = document.getElementById('tip');
  const show = (text, x, y) => {
    tip.replaceChildren(...text.split('\\n').map((line, index) => {
      const row = document.createElement('div');
      row.textContent = line;
      if (index === 0) row.className = 'lead';
      return row;
    }));
    tip.hidden = false;
    const box = tip.getBoundingClientRect();
    const left = Math.min(x + 14, window.innerWidth - box.width - 8);
    const top = y + 14 + box.height > window.innerHeight ? y - box.height - 14 : y + 14;
    tip.style.left = Math.max(8, left) + 'px';
    tip.style.top = Math.max(8, top) + 'px';
  };
  const hide = () => { tip.hidden = true; };
  document.addEventListener('pointermove', (event) => {
    if (event.target.closest && event.target.closest('#section-svg')) return;
    const el = event.target.closest ? event.target.closest('[data-tip]') : null;
    if (el) show(el.dataset.tip, event.clientX, event.clientY); else hide();
  });
  document.addEventListener('focusin', (event) => {
    const el = event.target.closest ? event.target.closest('[data-tip]') : null;
    if (!el) return;
    const box = el.getBoundingClientRect();
    show(el.dataset.tip, box.right, box.top);
  });
  document.addEventListener('focusout', hide);
  const section = document.getElementById('section-svg');
  const dataNode = document.getElementById('section-data');
  if (!section || !dataNode) return;
  const points = JSON.parse(dataNode.textContent);
  const focus = document.getElementById('section-focus');
  section.addEventListener('pointermove', (event) => {
    const matrix = section.getScreenCTM();
    if (!matrix) return;
    const cursor = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
    let best = null;
    let bestDistance = Infinity;
    for (const point of points) {
      const distance = (point[0] - cursor.x) ** 2 + (point[1] - cursor.y) ** 2;
      if (distance < bestDistance) { best = point; bestDistance = distance; }
    }
    if (best && bestDistance < 24 * 24) {
      focus.setAttribute('cx', best[0]);
      focus.setAttribute('cy', best[1]);
      show(best[2], event.clientX, event.clientY);
    } else {
      focus.setAttribute('cx', -20);
      hide();
    }
  });
  section.addEventListener('pointerleave', () => { focus.setAttribute('cx', -20); hide(); });
})();
"""
