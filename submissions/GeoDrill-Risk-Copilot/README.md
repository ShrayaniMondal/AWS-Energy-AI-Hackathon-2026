# GeoDrill Risk Copilot

GeoDrill Risk Copilot combines a synthetic, provenance-rich seismic catalog with AWS AI Energy Hackathon Use Case 1 drilling evidence. It answers one operational question:

> Where are attractive reservoir targets, where are fault/fracture drilling hazards, and which catalog files and drilling records support the recommendation?

The repository implements the subsurface digital-twin seed, deterministic
hazard/target analysis, ranked JSON/CSV exports, a Streamlit chat/dashboard
entry point, a documentation toolbox, and an AgentCore runtime contract. Four
teammate-owned features integrate through `docs/hpc-catalog-feature-contract.md`
and ownership in `teams.md`.

## Business Value

The hackathon brief states that NPT can represent 15–25% of complex-well costs and one stuck-pipe event can cost $500K–$2M (`Hackathon/use-case-1/one-pager.md`). GeoDrill's defensible value is faster precedent discovery and consistent pre-drill screening: it links every visible rank back to catalog IDs, a physical artifact, or a drilling evidence row/passage. It does not claim calibrated prediction or verified cost savings.

## Implemented Journey

```text
seeded HPC seismic catalog
  -> restartable digital-twin seed and physical file lineage
  -> fault/fracture interpretation and well hazard screens
  -> risk-ranked targets and hotspots
  -> JSON/CSV/GeoJSON/HTML/PNG evidence bundle
  -> chat/heatmap and AgentCore caller contracts
```

Generated seismic data is synthetic. Hazard, target, and confidence values are deterministic screening ranks, not calibrated reservoir predictions.

## Quick Start

```bash
make bootstrap
make validate
make demo
make dashboard
```

The deterministic demo writes immutable evidence beneath:

```text
outputs/hazard_demo/
├── catalog/metadata/runs/<catalog-run-id>/digital_twin/
└── analysis/<analysis-run-id>/
```

The analysis bundle includes `hazard_atlas.html`, `enriched_points.csv`, ranked prospect and hotspot CSV/JSON, fault/fracture/well evidence, plots, `summary.json`, and a SHA-256 `manifest.json`.

`make dashboard` starts the merged Streamlit app on `http://localhost:8501`.
The app includes chat, operations metrics, risk analysis, and chat-driven
heatmap JSON downloads. Local chat uses deterministic repository tools by
default; set `GEODRILL_USE_STRANDS=1` to route the same tool surface through
Strands/Bedrock when credentials and model access are available.

## Documentation and Code Toolbox

Build the caller-training index over repository Markdown and public Python docstrings:

```bash
PYTHONPATH=src .venv/bin/python -m aws_ai_energy.toolbox_docs \
  --root . \
  --validate-skills \
  --output artifacts/toolbox-index.json
```

The index excludes virtual environments, generated outputs, build artifacts, and AgentCore staging dependencies. Each chunk preserves a repository-relative path and line range. See `docs/toolbox-helper.md` for its Bedrock/AgentCore integration and authoring contract.

The drilling corpus loader uses `Hackathon/use-case-1/data` by default and accepts `DRILLING_DATA_DIR` as an override:

```bash
.venv/bin/python scripts/data_loader.py
```

## Main Interfaces

| Interface | Purpose |
|---|---|
| `seismic-catalog-generate` | Generate catalog tables, physical artifacts, and digital-twin endpoints |
| `seismic-catalog-analyze` | Detect hazards, screen wells, rank targets, and export evidence |
| `aws_ai_energy.dashboard` | Parse supported requests and produce deterministic heatmap JSON |
| `aws_ai_energy.toolbox_docs` | Build/search documentation and public API training context |
| `streamlit_app.py` | Merged local UI for chat, operations, risk analysis, and heatmap exports |
| `agent.py` | Local demo agent tools with optional Strands/Bedrock activation |
| `agentcore_app.main` | AgentCore invocation surface for grounded ranked prospects |

## Codex Quality Contract

Codex is the primary implementation assistant. Repository-local procedures live under `.codex/skills/`:

- `documentation-toolbox`
- `geodrill-feature-delivery`
- `agentcore-deployment`

Claude is a final packaging, video, and deployment-assistance reviewer. The
submission prompt is `clause-submissions.md`; automated review remains advisory
until a human accepts it.

## AgentCore and AWS

```bash
agentcore validate --directory .
agentcore package
agentcore deploy --target hackathon --dry-run
```

`agentcore/aws-targets.json` is intentionally empty until an authenticated operator writes the real account and region. Configuration validation is not deployment evidence. Cloud readiness requires a deployed runtime identifier, status, and successful grounded invocation.

## Data and Evidence Boundaries

- Corpus A is keyed by `well_name`; Corpus B is keyed by `well_id`. They must not be cross-joined.
- Visible recommendations retain catalog IDs, source rows, artifact paths, and manifest hashes when available.
- Missing thresholds or evidence are reported as missing instead of filled with model-generated facts.
- PDFs have maintained Markdown twins for deterministic indexing; PDF parsing is optional presentation behavior.

## Repository Map

```text
src/aws_ai_energy/generate/      catalog and digital-twin generation
src/aws_ai_energy/subsurface/    interpretation, scoring, provenance, exports
src/aws_ai_energy/dashboard.py   chat-to-heatmap contract
src/aws_ai_energy/toolbox_docs.py documentation and public API index
streamlit_app.py                  merged app entry point
agent.py                          local/Strands demo agent tools
agentcore_app/                    AgentCore runtime surface
agentcore/                        schema-first AgentCore/CDK configuration
Hackathon/use-case-1/data/       supplied drilling evidence and references
docs/                            architecture, contracts, value, judging evidence
.codex/skills/                   Codex delivery procedures
tests/                           deterministic behavior and contract tests
```

Team ownership and integration order are defined in `teams.md`.
