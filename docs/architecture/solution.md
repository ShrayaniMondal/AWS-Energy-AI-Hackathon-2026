# Solution Architecture

GeoDrill Risk Copilot joins a generated HPC seismic catalog with Use Case 1
drilling evidence so a drilling engineer can ask for a pre-drill hazard screen
and receive cited recommendations.

## Boundaries

- `generate/` and `src/aws_ai_energy/generate/` create restartable synthetic
  catalog metadata and dense seismic data.
- `src/aws_ai_energy/subsurface/` turns catalog points into interpreted faults,
  fractures, reservoir targets, well screens, exports, and plots.
- `src/aws_ai_energy/subsurface/scoring.py` produces risk-ranked prospect lists.
  Each sample receives a `hazard_score`, `target_score`, and `confidence_score`
  (all bounded 0–1) computed from five named factors: reservoir probability,
  fault likelihood, fracture intensity, well distance, and evidence strength.
  Scores are deterministic screening ranks with fixed weights, not calibrated
  predictions.
- `src/aws_ai_energy/subsurface/export.py` writes ranked targets and hotspots as
  both CSV and JSON using the same `score_row` schema, preserving catalog IDs
  and source row provenance for dashboard consumption.
- Dashboard and chat features consume exported JSON/CSV bundles and preserve the
  catalog keys described in `docs/hpc-catalog-feature-contract.md`.
- AgentCore runtime hosts the same deterministic tools used locally. Model
  responses compose answers; they do not invent numeric measurements.

## Data Flow

```text
catalog generator
  -> metadata/catalog.json and run tables
  -> subsurface analyzer
  -> fault/fracture detection
  -> risk-ranked prospect scoring (5 factors + confidence)
  -> target/hotspot/well exports (CSV + JSON, same schema)
  -> CLI chat, Streamlit dashboard, AgentCore runtime
  -> cited JSON/CSV evidence bundle
```

## Compatibility Rule

All components must retain `run_id`, project/site/dataset/dimension/segment/file
identifiers, source rows, and artifact paths when those values are available.
Any feature that shows a chart or recommendation must also export the same data
in a dashboard-friendly JSON or CSV shape.
