# HPC Catalog Feature Contract

This contract keeps every hackathon feature compatible with the synthetic HPC
seismic catalog, the drilling evidence, and downstream dashboards. Use it when
building CLI, agent, Streamlit, export, and AWS runtime features.

## Canonical Catalog Model

Every catalog-aware feature must preserve the identifiers needed to join back to
physical files and project context.

Required logical tables:

- `projects`: `id`, `name`
- `sites`: `id`, `name`
- `datasets`: `id`, `projectid`, `siteid`, `created`, `revision`, dataset type/name
- `dimensions`: `id`, `projectid`, `siteid`, `datasetid`, axis or dimension details
- `segments`: `id`, `projectid`, `siteid`, `datasetid`, nullable `dimensionid`
- `files`: `id`, `projectid`, `siteid`, `datasetid`, `segmentid`, `machineid`,
  `filesystemid`, `path`, `name`
- `machines`: `id`, host name such as `adroy@houdmtdev001`
- `filesystems`: `id`, mount name such as `/data`

Standard datasets map directly to one or more segments where `dimensionid` is
null. Multi-dimensional datasets map to one or more dimensions, then to one or
more segments per dimension. Segments map to one or more files.

## Physical File Provenance

The `files` table is the closest physical abstraction. A stored object is
addressed by:

```text
machineid + filesystemid + path + name
```

Do not infer a local path without consulting catalog metadata. If a generated
file would collide with an existing path/name, resolve the conflict with suffixes
on the file stem: `name.ext`, `name_1.ext`, `name_2.ext`, and so on.

Features that create derived artifacts must keep both:

- logical provenance: `run_id`, `projectid`, `siteid`, `datasetid`,
  `dimensionid`, `segmentid`, `fileid`, and source row/sample identifiers when
  available;
- artifact provenance: physical or exported `artifact_path`, plus manifest hash
  when the export pipeline provides one.

## Seismic Visualization Data

Dense seismic points, fault/fracture detections, reservoir targets, hazard
intervals, and heatmaps must remain joinable to catalog metadata. Preferred
point-level fields are:

- catalog keys: `run_id`, `projectid`, `siteid`, `datasetid`, `dimensionid`,
  `segmentid`, `fileid`, `sampleid` or `source_row`;
- geometry: `inline`, `crossline`, `depth_m`, optional `x`, `y`, `z`;
- interpretation: `amplitude`, `coherence`, `fault_likelihood`,
  `fracture_intensity`, `reservoir_probability`, `hazard_score`;
- traceability: `artifact_path`, `source_table`, `source_file`, `source_row`,
  and `synthetic_data=true` for generated seismic data.

Visualization-only state is not enough. If a chart, chat answer, or map can be
shown to a judge, the same content must be exportable as stable JSON or CSV with
the fields above.

## Drilling Evidence Boundaries

Use Case 1 drilling data and the generated seismic catalog are related by an
explicit analog workflow, not by hidden well joins.

- Cite drilling evidence by file and row, passage, or section.
- Do not join Corpus A narrative DDRs and Corpus B tabular DDRs by well
  identifier; their identifier spaces differ.
- Do not claim generated seismic samples are real field measurements.
- Label target and risk scores as deterministic screening ranks, not calibrated
  predictions.
- When a threshold, formation, or source row is missing, say it is missing.

## Feature Requirements

Every new software feature must answer these questions before handoff:

1. Which catalog table or analyzer export does it consume?
2. Which stable JSON/CSV contract does it produce?
3. Which identifiers let the output join back to `projects`, `sites`,
   `datasets`, `dimensions`, `segments`, and `files`?
4. Which physical artifact path or source row supports each visible claim?
5. How will Streamlit, CLI chat, AgentCore, or a dashboard consume the result
   without recomputing private in-memory state?

## Risk-Ranked Prospect List (scoring.py / export.py)

Answers to the feature-requirement questions above:

1. **Consumed**: `SurveyAnalysis` (catalog points, faults, fractures, wells).
2. **Produced**: `reservoir_targets.csv`, `reservoir_targets.json`,
   `fault_fracture_hotspots.csv`, `fault_fracture_hotspots.json` — all using the
   same `score_row` schema.
3. **Joinable identifiers**: `row` (1-based source row), `datasetid`,
   `dimensionid`, `fileid`, `sampleid`.
4. **Provenance**: every row traces to a catalog point via `row`/`fileid`/
   `sampleid`; every score exposes its five component factors and weights.
5. **Dashboard consumption**: JSON exports are byte-valid arrays of objects with
   the same keys as the CSV headers; Streamlit and AgentCore consume them
   without recomputation.

Scoring limitations:
- `confidence_score` is a deterministic evidence-strength index, not a
  statistical confidence interval.
- `hazard_score` and `target_score` use fixed weights defined in
  `ScoringConfig`; they are screening ranks, not calibrated predictions.
- Tie-breaking uses ascending `row` number for reproducibility.

## Definition of Done Addendum

A catalog-compatible feature is done only when:

- generated or derived data is restartable from metadata under `metadata/` or an
  analyzer `analysis/<run_id>/` bundle;
- output rows keep catalog IDs and evidence locators;
- dashboards and chat responses use exported payloads, not untraceable ad hoc
  objects;
- tests cover at least one success path and one missing/unsupported evidence
  path;
- documentation states any synthetic-data, scoring, or source-coverage limit.
