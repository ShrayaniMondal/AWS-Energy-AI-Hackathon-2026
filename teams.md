# Team Deliverables

All contributors work against the interfaces below. Codex is the only implementation assistant. Each owner must preserve provenance, add focused tests, update the evidence map, and pass `make validate` before handoff.

## Aditya — Subsurface Digital Twin Seed

Present the generated seismic catalog as the seed of a digital twin: wells, faults, horizons, reservoir probability, and physical data provenance. Strong architecture story, slightly bigger scope.

Owned paths:

- `src/aws_ai_energy/generate/`
- `src/aws_ai_energy/subsurface/points.py`
- digital-twin sections of `docs/architecture/solution.md`

Interface contract:

- emit stable IDs for catalog run, dataset, file, sample, well, fault, and horizon;
- retain the physical artifact path and source row for every interpreted point;
- label synthetic data explicitly;
- provide JSON/CSV structures consumable by the risk and dashboard layers.

Acceptance: a seeded catalog can be generated twice without overwriting prior run evidence, loaded by the analyzer, and traced from a displayed point back to its catalog file and row.

## Shrayani — Chat-Driven Feature Heatmaps

Build the chat feature to support the application to build heatmaps of features including wells, faults, horizons, reservoir probability, and physical data provenance, and export to JSON.

Owned paths:

- `src/aws_ai_energy/dashboard.py`
- chat and heatmap sections of `streamlit_app.py`
- heatmap JSON tests

Interface contract:

- convert a user request into an explicit, validated feature list;
- reject unsupported features rather than hallucinating them;
- produce display-ready points and a downloadable JSON payload;
- include source file/row provenance and the synthetic-data notice.

Acceptance: the same prompt and analysis bundle produce deterministic heatmap JSON for wells, faults, horizons, reservoir probability, and provenance.

## Rongrong — Risk-Ranked Prospect List

Feature to turn the analysis into a risk-ranked prospect list: reservoir probability, fault likelihood, fracture intensity, well distance, and confidence. The same can be exported to JSON to support front-end visualization.

Owned paths:

- `src/aws_ai_energy/subsurface/scoring.py`
- ranked target/hotspot exports in `src/aws_ai_energy/subsurface/export.py`
- score and export tests

Interface contract:

- expose every score component and weight;
- produce deterministic ordering and a bounded confidence value;
- preserve source point and file identifiers;
- export both CSV and JSON using the same row schema.

Acceptance: ranked results include all five named factors, deterministic tie handling, provenance, and byte-valid JSON consumed directly by the dashboard.

## Yuxin — Streamlit and AWS Cloud Delivery

Build the Streamlit and AWS Cloud deployment and dashboard application.

Owned paths:

- `streamlit_app.py`
- `Dockerfile`
- `agentcore/`
- `agentcore_app/`
- `infra/`
- `docs/runbooks/`

Interface contract:

- run the local judged journey from one command;
- show loading, empty, error, and reset states;
- expose JSON downloads and source citations;
- deploy the agent backend through Amazon Bedrock AgentCore and the dashboard through AWS infrastructure;
- record actual endpoint/stack outputs and a smoke invocation without committing credentials.

Acceptance: `make dashboard` serves a usable local journey; AgentCore config validates; deployment documentation includes dry-run, deploy, smoke, logs, rollback, and offline fallback. Cloud readiness is not claimed until real AWS evidence is captured.

## Shared Integration Order

1. Aditya publishes the catalog and provenance contract.
2. Rongrong publishes ranked CSV/JSON contracts.
3. Shrayani consumes those contracts for chat-driven heatmaps.
4. Yuxin integrates the accepted contracts into Streamlit and AgentCore/AWS delivery.
5. The team runs `make validate`, `make demo`, a dashboard walkthrough, and a real cloud smoke test when credentials are available.
