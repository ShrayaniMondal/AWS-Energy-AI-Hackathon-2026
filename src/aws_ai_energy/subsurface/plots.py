"""Static PNG plots for decks and offline fallback, using the atlas color roles."""

from __future__ import annotations

import importlib
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from aws_ai_energy.subsurface.analysis import SurveyAnalysis
from aws_ai_energy.subsurface.faults import fault_score
from aws_ai_energy.subsurface.scoring import PointScore

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE_RAMP = ("#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b")
LITHOLOGY_COLORS = {
    "channel_sand": "#2a78d6",
    "fault_damage_zone": "#eb6834",
    "carbonate_basement": "#1baf7a",
}
OTHER_LITHOLOGY = "#c3c2b7"
STATUS = {"low": "#0ca30c", "moderate": "#fab219", "high": "#ec835a", "severe": "#d03b3b"}
GLYPHS = {"low": "✓", "moderate": "!", "high": "▲", "severe": "✖"}


class PlottingUnavailableError(RuntimeError):
    """Raised when matplotlib is not installed."""


def render_png_plots(
    analysis: SurveyAnalysis,
    scores: list[PointScore],
    targets: list[PointScore],
    output_dir: Path,
) -> list[Path]:
    plt, colors = _matplotlib()
    output_dir.mkdir(parents=True, exist_ok=True)
    ramp = colors.LinearSegmentedColormap.from_list("fracture_blue", BLUE_RAMP)
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.edgecolor": AXIS,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.titleweight": "bold",
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
        }
    )
    return [
        _hazard_map(plt, ramp, analysis, output_dir / "hazard_map.png"),
        _target_map(plt, ramp, analysis, scores, targets, output_dir / "reservoir_target_map.png"),
        _section(plt, analysis, output_dir / "drilling_risk_section.png"),
        _risk_bars(plt, analysis, output_dir / "well_screening_index.png"),
        _crossplot(plt, analysis, output_dir / "fault_attribute_crossplot.png"),
        _volume(plt, ramp, analysis, output_dir / "fault_fracture_3d.png"),
    ]


def _matplotlib() -> tuple[Any, Any]:
    try:
        matplotlib = importlib.import_module("matplotlib")
    except ModuleNotFoundError as error:
        raise PlottingUnavailableError(
            "matplotlib is not installed; install the project with "
            ".venv/bin/python -m pip install -e ."
        ) from error
    matplotlib.use("Agg")
    return importlib.import_module("matplotlib.pyplot"), importlib.import_module(
        "matplotlib.colors"
    )


def _style(axis: Any, title: str, xlabel: str, ylabel: str) -> None:
    axis.set_title(title, loc="left")
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(True, color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)


def _cell_grid(
    analysis: SurveyAnalysis, values: dict[tuple[int, int], float]
) -> tuple[Any, list[float]]:
    size = analysis.settings.fractures.cell_size_m
    xs = [ix for ix, _ in values]
    ys = [iy for _, iy in values]
    columns = max(xs) - min(xs) + 1
    rows = max(ys) - min(ys) + 1
    grid = [[math.nan] * columns for _ in range(rows)]
    for (ix, iy), value in values.items():
        grid[iy - min(ys)][ix - min(xs)] = value
    extent = [min(xs) * size, (max(xs) + 1) * size, min(ys) * size, (max(ys) + 1) * size]
    return grid, extent


def _draw_faults(axis: Any, analysis: SurveyAnalysis) -> None:
    for fault in analysis.faults:
        (x0, y0), (x1, y1) = fault.trace()
        half = fault.damage_zone_half_width_m * math.hypot(1.0, fault.slope)
        axis.fill(
            [x0 - half, x1 - half, x1 + half, x0 + half],
            [y0, y1, y1, y0],
            color=INK,
            alpha=0.08,
            linewidth=0,
        )
        axis.plot([x0, x1], [y0, y1], color=INK, linewidth=2, solid_capstyle="round")
        axis.annotate(
            fault.id,
            (x1, y1),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            color=INK,
            fontweight="bold",
        )


def _hazard_map(plt: Any, ramp: Any, analysis: SurveyAnalysis, path: Path) -> Path:
    figure, axis = plt.subplots(figsize=(11, 7))
    grid, extent = _cell_grid(
        analysis, {(cell.ix, cell.iy): cell.p90_intensity for cell in analysis.cells}
    )
    image = axis.imshow(
        grid,
        origin="lower",
        extent=extent,
        cmap=ramp,
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
        aspect="equal",
    )
    _draw_faults(axis, analysis)
    ordered = sorted(analysis.briefs, key=lambda brief: brief.screen.well.inline_m)
    for index, brief in enumerate(ordered):
        screen = brief.screen
        axis.scatter(
            [screen.well.inline_m],
            [screen.well.crossline_m],
            s=80,
            color=STATUS[screen.risk_class],
            edgecolors=SURFACE,
            linewidths=2,
            zorder=5,
        )
        axis.annotate(
            f"{screen.well.id} {GLYPHS[screen.risk_class]} {screen.risk_class}",
            (screen.well.inline_m, screen.well.crossline_m),
            xytext=(8, 7) if index % 2 == 0 else (8, -15),
            textcoords="offset points",
            color=INK,
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.15", "fc": SURFACE, "ec": "none", "alpha": 0.8},
        )
    _style(
        axis,
        "Fracture intensity (P90 per 100 m cell; blank = no samples), detected faults, "
        "and well screening",
        "Inline (m)",
        "Crossline (m)",
    )
    figure.colorbar(image, ax=axis, label="P90 fracture intensity", shrink=0.8)
    return _save(plt, figure, path)


def _target_map(
    plt: Any,
    ramp: Any,
    analysis: SurveyAnalysis,
    scores: list[PointScore],
    targets: list[PointScore],
    path: Path,
) -> Path:
    size = analysis.settings.fractures.cell_size_m
    best: dict[tuple[int, int], float] = defaultdict(float)
    for score in scores:
        key = (math.floor(score.point.inline_m / size), math.floor(score.point.crossline_m / size))
        best[key] = max(best[key], score.target_score)
    figure, axis = plt.subplots(figsize=(11, 7))
    grid, extent = _cell_grid(analysis, dict(best))
    image = axis.imshow(
        grid,
        origin="lower",
        extent=extent,
        cmap=ramp,
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
        aspect="equal",
    )
    _draw_faults(axis, analysis)
    top = targets[:10]
    axis.scatter(
        [t.point.inline_m for t in top],
        [t.point.crossline_m for t in top],
        marker="x",
        s=60,
        color=INK,
        linewidths=2,
        label="Top 10 target samples",
        zorder=5,
    )
    if top:
        axis.annotate(
            f"best target: row {top[0].point.row} ({top[0].target_score:.2f})",
            (top[0].point.inline_m, top[0].point.crossline_m),
            xytext=(8, -12),
            textcoords="offset points",
            color=INK,
            fontsize=8,
        )
    axis.legend(loc="upper right", frameon=False)
    _style(
        axis,
        "Reservoir target score (cell maximum): reservoir probability, low hazard, well control",
        "Inline (m)",
        "Crossline (m)",
    )
    figure.colorbar(image, ax=axis, label="Target score", shrink=0.8)
    return _save(plt, figure, path)


def _section(plt: Any, analysis: SurveyAnalysis, path: Path) -> Path:
    figure, axis = plt.subplots(figsize=(11, 5.5))
    ranked = analysis.ranked_briefs()
    if not ranked:
        axis.text(0.5, 0.5, "No wells screened", ha="center", transform=axis.transAxes)
        return _save(plt, figure, path)
    brief = ranked[0]
    well = brief.screen.well
    band = [p for p in analysis.survey.points if abs(p.crossline_m - well.crossline_m) <= 80.0]
    group = Counter(p.dimensionid for p in band).most_common(1)[0][0] if band else ""
    members = [p for p in band if p.dimensionid == group]
    others = [p for p in members if p.lithology not in LITHOLOGY_COLORS]
    axis.scatter(
        [p.inline_m for p in others],
        [p.depth_m for p in others],
        s=14,
        color=OTHER_LITHOLOGY,
        edgecolors=SURFACE,
        linewidths=0.5,
        label="shale",
    )
    for lithology, color in LITHOLOGY_COLORS.items():
        subset = [p for p in members if p.lithology == lithology]
        if subset:
            axis.scatter(
                [p.inline_m for p in subset],
                [p.depth_m for p in subset],
                s=16,
                color=color,
                edgecolors=SURFACE,
                linewidths=0.5,
                label=lithology.replace("_", " "),
            )
    for attribute, label in (
        ("horizon_top_m", "reservoir top"),
        ("horizon_base_m", "reservoir base"),
    ):
        bins: dict[int, list[float]] = defaultdict(list)
        for point in members:
            bins[math.floor(point.inline_m / 100.0)].append(float(getattr(point, attribute)))
        line = [
            ((key + 0.5) * 100.0, sorted(values)[len(values) // 2])
            for key, values in sorted(bins.items())
        ]
        if len(line) >= 2:
            axis.plot(
                [x for x, _ in line],
                [y for _, y in line],
                color=INK_2,
                linewidth=1.5,
                label=label if attribute == "horizon_top_m" else None,
            )
            axis.annotate(
                label,
                line[-1],
                xytext=(6, 0),
                textcoords="offset points",
                va="center",
                color=INK_2,
                fontsize=8,
            )
    for fault in analysis.faults:
        axis.axvline(fault.inline_at(well.crossline_m), color=INK, linewidth=1.2, alpha=0.7)
        axis.annotate(
            fault.id,
            (fault.inline_at(well.crossline_m), 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(4, -12),
            textcoords="offset points",
            ha="left",
            color=INK,
            fontweight="bold",
        )
    target = well.target_depth_m or max(p.depth_m for p in members)
    axis.plot(
        [well.inline_m, well.inline_m],
        [min(p.depth_m for p in members), target],
        color=INK,
        linewidth=2,
    )
    axis.scatter(
        [well.inline_m],
        [target],
        s=80,
        color=STATUS[brief.screen.risk_class],
        edgecolors=SURFACE,
        linewidths=2,
        zorder=5,
    )
    axis.annotate(
        f"{well.id} TD {GLYPHS[brief.screen.risk_class]} {brief.screen.risk_class}",
        (well.inline_m, target),
        xytext=(8, 4),
        textcoords="offset points",
        color=INK,
    )
    axis.invert_yaxis()
    axis.legend(loc="lower left", frameon=False, ncol=5)
    _style(
        axis,
        f"Section through {well.id} (crossline ±80 m, one dimension group)",
        "Inline (m)",
        "Depth (m)",
    )
    axis.set_title(axis.get_title("left"), loc="left", pad=10)
    return _save(plt, figure, path)


def _risk_bars(plt: Any, analysis: SurveyAnalysis, path: Path) -> Path:
    ranked = list(reversed(analysis.ranked_briefs()))
    figure, axis = plt.subplots(figsize=(9, 0.45 * max(len(ranked), 2) + 1.2))
    labels = [brief.screen.well.id for brief in ranked]
    values = [brief.screen.risk_index for brief in ranked]
    axis.barh(labels, values, height=0.55, color=[STATUS[b.screen.risk_class] for b in ranked])
    for index, brief in enumerate(ranked):
        axis.annotate(
            f"{brief.screen.risk_index:.0f} · {GLYPHS[brief.screen.risk_class]} "
            f"{brief.screen.risk_class}",
            (brief.screen.risk_index, index),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            color=INK,
        )
    axis.set_xlim(0, 115)
    axis.set_xticks([0, 25, 50, 75, 100])
    _style(axis, "Well screening index (fixed weights, not calibrated)", "Screening index", "")
    axis.grid(True, axis="x", color=GRID)
    axis.grid(False, axis="y")
    return _save(plt, figure, path)


def _crossplot(plt: Any, analysis: SurveyAnalysis, path: Path) -> Path:
    threshold = analysis.settings.faults.score_threshold
    points = analysis.survey.points
    step = max(1, len(points) // 6_000)
    sample = points[::step]
    candidates = [p for p in sample if fault_score(p, analysis.coherence_reference) >= threshold]
    background = [p for p in sample if fault_score(p, analysis.coherence_reference) < threshold]
    figure, axis = plt.subplots(figsize=(7.5, 6))
    axis.scatter(
        [p.fault_likelihood for p in background],
        [p.coherence for p in background],
        s=10,
        color=OTHER_LITHOLOGY,
        alpha=0.6,
        linewidths=0,
        label="below threshold",
    )
    axis.scatter(
        [p.fault_likelihood for p in candidates],
        [p.coherence for p in candidates],
        s=12,
        color=LITHOLOGY_COLORS["channel_sand"],
        alpha=0.8,
        linewidths=0,
        label=f"fault candidate (score ≥ {threshold:.2f})",
    )
    axis.legend(loc="upper right", frameon=False)
    _style(
        axis,
        "Fault detection inputs: fault likelihood vs coherence",
        "Fault likelihood",
        "Coherence",
    )
    return _save(plt, figure, path)


def _volume(plt: Any, ramp: Any, analysis: SurveyAnalysis, path: Path) -> Path:
    numpy = importlib.import_module("numpy")
    points = analysis.survey.points
    step = max(1, len(points) // 5_000)
    sample = points[::step]
    figure = plt.figure(figsize=(10, 8))
    axis = figure.add_subplot(111, projection="3d")
    scatter = axis.scatter(
        [p.inline_m for p in sample],
        [p.crossline_m for p in sample],
        [p.depth_m for p in sample],
        c=[p.fracture_intensity for p in sample],
        cmap=ramp,
        vmin=0.0,
        vmax=1.0,
        s=5,
        alpha=0.7,
        linewidths=0,
    )
    depth_lo, depth_hi = analysis.survey.depth_extent_m
    for fault in analysis.faults:
        (x0, y0), (x1, y1) = fault.trace()
        axis.plot_surface(
            numpy.array([[x0, x1], [x0, x1]]),
            numpy.array([[y0, y1], [y0, y1]]),
            numpy.array([[depth_lo, depth_lo], [depth_hi, depth_hi]]),
            color=INK,
            alpha=0.12,
            linewidth=0,
        )
        axis.text(x1, y1, depth_lo, fault.id, color=INK)
    for brief in analysis.briefs:
        well = brief.screen.well
        axis.plot(
            [well.inline_m, well.inline_m],
            [well.crossline_m, well.crossline_m],
            [depth_lo, well.target_depth_m or depth_hi],
            color=STATUS[brief.screen.risk_class],
            linewidth=2.5,
        )
    axis.set_xlabel("Inline (m)")
    axis.set_ylabel("Crossline (m)")
    axis.set_zlabel("Depth (m)")
    axis.invert_zaxis()
    axis.set_title("Fracture intensity volume with detected fault planes and wells", loc="left")
    figure.colorbar(scatter, ax=axis, label="Fracture intensity", shrink=0.6)
    return _save(plt, figure, path)


def _save(plt: Any, figure: Any, path: Path) -> Path:
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path
