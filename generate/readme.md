# Seismic Catalog Generator

Generate coherent seismic exploration data with catalog metadata and lightweight file artifacts.

## Setup

Create and sync the local development environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Ruff, pytest, and mypy are then available under `.venv/bin` and through:

```bash
.venv/bin/python -m ruff check src tests generate
```

## Generate Data

Minimum input is the dataset count:

```bash
.venv/bin/python -m generate.seismic_catalog 5
```

More controlled example:

```bash
.venv/bin/python -m generate.seismic_catalog 5 \
  --output-dir outputs/seismic_catalog_5 \
  --dataset-kind mixed \
  --segments 4 \
  --dimensions 3 \
  --files 2 \
  --points-per-file 200 \
  --seed 42
```

When `--segments`, `--dimensions`, or `--files` are omitted, each count is selected from 1 to 10.
The catalog records logical file sizes under 1 GiB, while the generated physical files stay small.

## Outputs

- `metadata/catalog.json`: latest catalog snapshot.
- `metadata/latest_run.json`: latest run pointer with paths and row counts.
- `metadata/run_index.jsonl`: append-only run index for discovering prior runs after restart.
- `metadata/runs/<run_id>/catalog.json`: immutable run-level catalog.
- `metadata/runs/<run_id>/tables/`: per-table JSON and CSV exports for projects, sites, machines,
  filesystems, wells, faults, horizons, datasets, dimensions, segments, and files.
- `visualization_points.csv`: plot-ready rows with inline, crossline, depth, amplitude, velocity,
  impedance, fault likelihood, fracture intensity, reservoir probability, well distance, and lithology.
- `files/`: lightweight physical CSV files matching records in the `files` catalog table.

The generator never overwrites generated data files. If a path already exists, the basename is
suffixed before the extension: `file_0001.seismic.csv`, `file_0001_1.seismic.csv`,
`file_0001_2.seismic.csv`, and so on. The same rule applies to aggregate visualization CSV files.

## Resume Or Inspect Existing Metadata

List known runs without generating new data:

```bash
.venv/bin/python -m generate.seismic_catalog --output-dir outputs/seismic_catalog_5 --list-runs
```

Print the latest run-level catalog path:

```bash
.venv/bin/python -m generate.seismic_catalog --output-dir outputs/seismic_catalog_5 --latest-metadata
```

Python callers can load the latest catalog directly:

```python
from aws_ai_energy.generate.seismic_catalog import load_latest_catalog

catalog = load_latest_catalog("outputs/seismic_catalog_5")
files = catalog["tables"]["files"]
```

## Plot With Matplotlib

Install plotting support if needed:

```bash
.venv/bin/python -m pip install matplotlib
```

Create PNG plots from the aggregate CSV:

```bash
.venv/bin/python generate/plot_matplotlib.py \
  outputs/seismic_catalog_5/visualization_points.csv \
  --output-dir outputs/seismic_catalog_5/plots
```

## Plot With ggplot2

From an R environment with `ggplot2` installed:

```bash
Rscript generate/plot_ggplot.R \
  outputs/seismic_catalog_5/visualization_points.csv \
  outputs/seismic_catalog_5/plots
```

## Analyze Faults, Fractures, Well Hazards, And Reservoir Targets

One analyzer turns a generated catalog into drilling hazard evidence linked to Use Case 1:

- **Faults:** detected from fault likelihood and coherence loss with a weighted Hough line search,
  with throw and damage-zone width estimates and a scorecard against the catalog fault table.
- **Fracture corridors:** P90 fracture intensity on a 100 m grid, grouped into connected corridors
  and attributed to the nearest fault or well.
- **Well screens:** a 0-100 screening index per well, hazard intervals by depth, and cited
  `npt_incident_log.csv` precedents, `anomaly_thresholds.csv` rows, and reference-doc passages.
- **Per-sample scores:** `hazard_score`, `target_score`, and a `decision` of `geomechanics_review`,
  `drilling_candidate`, or `watch_zone`.

Offline end-to-end demo (seeded catalog, analysis, exports, atlas, and PNG plots):

```bash
.venv/bin/python -m generate.analyze_catalog demo --output-dir outputs/hazard_demo
```

Analyze an existing catalog (`export` is the default command):

```bash
.venv/bin/python -m generate.analyze_catalog \
  --output-dir outputs/seismic_catalog_5 \
  --drilling-data-dir Hackathon/use-case-1/data \
  --formation "Wolfcamp A" \
  --top-n 25
```

Inspect results in the terminal:

```bash
.venv/bin/python -m generate.analyze_catalog faults --output-dir outputs/seismic_catalog_5
.venv/bin/python -m generate.analyze_catalog fractures --output-dir outputs/seismic_catalog_5
.venv/bin/python -m generate.analyze_catalog wells --output-dir outputs/seismic_catalog_5 --well well_05
.venv/bin/python -m generate.analyze_catalog wells --output-dir outputs/seismic_catalog_5 --at 2250,1100
.venv/bin/python -m generate.analyze_catalog targets --output-dir outputs/seismic_catalog_5 --top-n 10
```

Each export run writes to `analysis/<run_id>/` (never overwriting) and includes:

| File | Contents |
|---|---|
| `hazard_atlas.html` | Self-contained map, well ranking, section, drilling brief, and tables |
| `enriched_points.csv` | Every sample with fault score, nearest fault, fracture class, corridor, scores, decision |
| `fault_fracture_hotspots.csv`, `reservoir_targets.csv` | Top-N samples by hazard and target score |
| `faults.csv`, `faults.json`, `fault_traces.geojson` | Detected faults; GeoJSON uses survey-local metres |
| `fracture_cells.csv`, `fracture_corridors.csv`, `fracture_corridors.json` | Gridded intensity and corridors |
| `well_screens.csv`, `well_briefs.json`, `hazard_intervals.csv` | Well screens with hazards and precedents |
| `precedents.csv`, `thresholds.csv`, `hazard_rules.json` | Cited drilling evidence and the screening rules |
| `fault_scorecard.json` | Detection accuracy against the synthetic catalog fault table |
| `plots/*.png` | Hazard map, target map, section, well ranking, attribute crossplot, 3D volume |
| `summary.json`, `manifest.json` | Run summary and SHA-256 lineage for every input and output |

Pass `--no-plots` to skip matplotlib or `--no-html` to skip the atlas. The seismic catalog is
synthetic; screening indices use fixed weights and are not calibrated predictions. Precedents come
from Use Case 1 through the documented rules in `hazard_rules.json`, and the analog formation is an
explicit user choice rather than a join between synthetic samples and real wells.
