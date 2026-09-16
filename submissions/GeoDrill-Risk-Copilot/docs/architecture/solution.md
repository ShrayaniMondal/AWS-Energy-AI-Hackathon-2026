# Solution Architecture

GeoDrill Risk Copilot joins a generated HPC seismic catalog with Use Case 1
drilling evidence so a drilling engineer can ask for a pre-drill hazard screen
and receive cited recommendations.

## Boundaries

- `generate/` and `src/aws_ai_energy/generate/` create restartable synthetic
  catalog metadata and dense seismic data.
- `src/aws_ai_energy/subsurface/` turns catalog points into interpreted faults,
  fractures, reservoir targets, well screens, exports, and plots.
- Dashboard and chat features consume exported JSON/CSV bundles and preserve the
  catalog keys described in `docs/hpc-catalog-feature-contract.md`.
- `src/aws_ai_energy/toolbox_docs.py` converts repository guidance and public API
  docstrings into deterministic, line-cited chunks for offline or Bedrock-backed
  caller support; generated environments and AgentCore staging dependencies are excluded.
- AgentCore runtime hosts the same deterministic tools used locally. Model
  responses compose answers; they do not invent numeric measurements.

## Data Flow

```text
catalog generator
  -> metadata/catalog.json and run tables
  -> metadata/runs/<run_id>/digital_twin seed, points, metrics, and layers
  -> subsurface analyzer
  -> fault/fracture/target/well exports
  -> CLI chat, Streamlit dashboard, AgentCore runtime
  -> cited JSON/CSV evidence bundle
```

## Digital Twin Seed

Each catalog run publishes a synthetic subsurface digital-twin seed under
`metadata/runs/<run_id>/digital_twin/`. The seed presents wells, faults,
horizons, reservoir probability samples, and physical data provenance as
file-backed endpoints:

- `digital_twin_seed.json`: run envelope, stable entity IDs, catalog entities,
  and endpoint links.
- `digital_twin_points.csv`: one row per interpreted point with `run_id`,
  project/site/dataset/dimension/segment/file/sample keys, stable UIDs,
  `artifact_path`, `source_file`, `source_row`, and `synthetic_data=true`.
- `digital_twin_metrics.json`: row counts, entity counts, extents, lithology
  counts, and attribute min/max/mean for exploration dashboards.
- `digital_twin_layers.geojson`: survey-local well, fault, and horizon layers
  for visualization.

The analyzer loads catalog runs with those fields intact, then propagates them
into scored exports such as `enriched_points.csv`, hotspot JSON, reservoir target
JSON, and heatmap payloads. A displayed target can therefore be traced to the
catalog file row and physical artifact without depending on private in-memory
state.

## Compatibility Rule

All components must retain `run_id`, project/site/dataset/dimension/segment/file
identifiers, source rows, and artifact paths when those values are available.
Any feature that shows a chart or recommendation must also export the same data
in a dashboard-friendly JSON or CSV shape.
