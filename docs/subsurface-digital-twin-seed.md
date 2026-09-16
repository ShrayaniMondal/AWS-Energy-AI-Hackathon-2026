# Subsurface Digital Twin Seed

Aditya's catalog stack turns each generated seismic catalog run into a restartable
digital-twin seed. The seed is synthetic by design and keeps every interpreted
point joinable to catalog tables, source rows, and physical file artifacts.

## Generate

```bash
.venv/bin/python -m generate.seismic_catalog 10 \
  --output-dir outputs/seismic_catalog_10 \
  --dataset-kind mixed \
  --segments 3 \
  --dimensions 2 \
  --files 2 \
  --points-per-file 160 \
  --seed 42
```

List the file-backed exploration endpoints for the latest run:

```bash
.venv/bin/python -m generate.seismic_catalog \
  --output-dir outputs/seismic_catalog_10 \
  --digital-twin-endpoints
```

## Endpoint Files

Each run writes immutable evidence under `metadata/runs/<run_id>/digital_twin/`.
New runs use a new `run_id`, so prior evidence is not overwritten.

| Endpoint | File | Purpose |
|---|---|---|
| `seed` | `digital_twin_seed.json` | Run envelope, stable IDs, wells, faults, horizons, datasets, files, and links to other endpoints |
| `points` | `digital_twin_points.csv` | Point-level inline/crossline/depth, attributes, stable IDs, synthetic label, physical artifact path, and source row |
| `metrics` | `digital_twin_metrics.json` | Row counts, entity counts, extents, lithology counts, and attribute min/max/mean |
| `layers` | `digital_twin_layers.geojson` | Survey-local well, fault, and horizon features for visualization |
| `catalog` | `catalog.json` | Full catalog metadata for the run |
| `tables` | `tables/*.json`, `tables/*.csv` | Canonical catalog tables |

## Stable IDs

The seed uses run-scoped IDs that can be consumed by risk, dashboard, or agent
layers without hidden joins:

- `run_id`
- `dataset_uid`, `segment_uid`, `file_uid`
- `sample_uid`, `point_uid`
- `well_uid`, `fault_uid`, `horizon_top_uid`, `horizon_base_uid`

Numeric catalog keys are retained beside the UIDs: `projectid`, `siteid`,
`datasetid`, `dimensionid`, `segmentid`, `fileid`, and `sampleid`.

## Provenance

Every generated point carries:

- `artifact_path`: the lightweight physical seismic CSV written for its catalog file;
- `source_table`: `visualization_points`;
- `source_file`: the aggregate visualization CSV used by the analyzer;
- `source_row`: the 1-based data row in that CSV;
- `synthetic_data`: `true`.

Analyzer exports such as `enriched_points.csv`, `reservoir_targets.json`, and
dashboard heatmap payloads preserve those fields, so a displayed point can be
traced back to its catalog file and source row.

## Limits

The basin, wells, faults, horizons, and seismic attributes are generated
synthetically. Reservoir probability and risk scores are fixed-weight screening
ranks for demonstrations, not calibrated reservoir predictions or real field
measurements.
