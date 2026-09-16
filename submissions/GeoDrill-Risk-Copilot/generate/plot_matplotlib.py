from __future__ import annotations

import argparse
import csv
import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def read_points(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict[str, Any], key: str) -> float:
    return float(row[key])


def plot(csv_path: Path, output_dir: Path) -> list[Path]:
    try:
        plt = importlib.import_module("matplotlib.pyplot")
    except ModuleNotFoundError as error:
        raise SystemExit(
            "matplotlib is required for this plotting helper. "
            "Install it with: .venv/bin/python -m pip install matplotlib"
        ) from error

    rows = read_points(csv_path)
    if not rows:
        raise SystemExit(f"No rows found in {csv_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    inline = [as_float(row, "inline_m") for row in rows]
    crossline = [as_float(row, "crossline_m") for row in rows]
    depth = [as_float(row, "depth_m") for row in rows]
    amplitude = [as_float(row, "amplitude") for row in rows]
    reservoir = [as_float(row, "reservoir_probability") for row in rows]
    fault = [as_float(row, "fault_likelihood") for row in rows]

    paths = [
        output_dir / "inline_depth_amplitude.png",
        output_dir / "reservoir_map.png",
        output_dir / "fault_fracture_3d.png",
    ]

    figure, axis = plt.subplots(figsize=(11, 6))
    scatter = axis.scatter(inline, depth, c=amplitude, s=8, cmap="seismic", alpha=0.8)
    axis.invert_yaxis()
    axis.set_xlabel("Inline (m)")
    axis.set_ylabel("Depth (m)")
    axis.set_title("Synthetic seismic section: amplitude by inline and depth")
    figure.colorbar(scatter, ax=axis, label="Amplitude")
    figure.tight_layout()
    figure.savefig(paths[0], dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 7))
    scatter = axis.scatter(inline, crossline, c=reservoir, s=10, cmap="viridis", alpha=0.85)
    axis.set_xlabel("Inline (m)")
    axis.set_ylabel("Crossline (m)")
    axis.set_title("Reservoir probability map")
    figure.colorbar(scatter, ax=axis, label="Reservoir probability")
    figure.tight_layout()
    figure.savefig(paths[1], dpi=180)
    plt.close(figure)

    figure = plt.figure(figsize=(10, 8))
    axis = figure.add_subplot(111, projection="3d")
    scatter = axis.scatter(inline, crossline, depth, c=fault, s=7, cmap="magma", alpha=0.75)
    axis.set_xlabel("Inline (m)")
    axis.set_ylabel("Crossline (m)")
    axis.set_zlabel("Depth (m)")
    axis.invert_zaxis()
    axis.set_title("Fault likelihood and fractured subsurface volume")
    figure.colorbar(scatter, ax=axis, label="Fault likelihood", shrink=0.65)
    figure.tight_layout()
    figure.savefig(paths[2], dpi=180)
    plt.close(figure)

    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot generated seismic catalog CSV data.")
    parser.add_argument("csv_path", type=Path, help="Path to visualization_points.csv.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/seismic_catalog/plots"),
        help="Directory for generated PNG files.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    paths = plot(args.csv_path, args.output_dir)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
