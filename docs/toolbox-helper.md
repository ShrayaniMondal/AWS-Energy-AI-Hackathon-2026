# GeoDrill Documentation Toolbox

## Business Purpose

GeoDrill turns scattered drilling reports, seismic catalog metadata, operating limits, and reference procedures into a caller-ready evidence toolbox. A drilling engineer should be able to ask a decision question and receive a narrow answer with the exact repository document, code API, file, row, or passage that supports it.

The business value is decision latency and repeatability. The provided use-case brief reports that NPT can represent 15–25% of complex-well cost and a single stuck-pipe event can cost $500K–$2M. The toolbox does not claim to prevent those losses; it makes historical precedents, screening assumptions, and implementation capabilities discoverable enough for an agent or engineer to inspect before acting. Those figures originate in `Hackathon/use-case-1/one-pager.md` and must be cited as hackathon context, not measured product impact.

## Caller Contract

`aws_ai_energy.toolbox_docs` indexes two evidence classes:

1. Markdown guidance, proposals, data dictionaries, reference procedures, ownership, judging evidence, and Codex skills.
2. Module and public API docstrings from repository Python code.

Each indexed chunk contains:

- repository-relative `source`;
- evidence `kind`;
- section title or public symbol;
- exact `start_line` and `end_line` when available;
- unmodified source text.

The JSON envelope adds a deterministic SHA-256 `source_digest`. AgentCore, Bedrock retrieval, Streamlit, or offline callers may add embeddings, but must preserve this citation envelope.

## Build and Search

```bash
PYTHONPATH=src python -m aws_ai_energy.toolbox_docs \
  --root . \
  --validate-skills \
  --output artifacts/toolbox-index.json
```

The build excludes virtual environments, generated outputs, packaged AgentCore staging dependencies, build artifacts, and caches. `artifacts/` is ignored because the index is reproducible from repository sources.

Python callers can search without Bedrock:

```python
from aws_ai_energy.toolbox_docs import build_toolbox_index

index = build_toolbox_index(".")
results = index.search("business value drilling NPT provenance", top_k=5)
for result in results:
    print(result.chunk.source, result.chunk.start_line, result.score)
```

Lexical search is the deterministic offline fallback. Production retrieval may embed `chunk.text` with Amazon Bedrock while retaining `source`, line range, and `source_digest`.

## Authoring Standard

Caller-facing documentation and public docstrings should state, in this order:

1. decision or task enabled;
2. accepted inputs and identifiers;
3. returned artifact or schema;
4. evidence/provenance preserved;
5. error or unsupported-evidence behavior;
6. synthetic-data, calibration, or deployment limitation.

Comments should explain a non-obvious reason, invariant, or safety boundary. Do not narrate syntax. Private implementation comments are intentionally not indexed as caller training material.

## Data Boundaries

- Corpus A uses `well_name`; Corpus B uses `well_id`. They must not be cross-joined.
- Generated seismic attributes are synthetic.
- Hazard, target, and confidence values are deterministic screening ranks, not calibrated predictions.
- A missing source, threshold, deployment ID, or model response must be reported as missing.
- PDF reference documents have maintained Markdown twins for deterministic indexing; PDF parsing is optional presentation behavior.

## Quality Gate

A documentation/toolbox change is acceptable when:

- `.codex/skills` validation returns no issues;
- the index rebuild is deterministic;
- representative searches return focused repository sources rather than staged dependencies;
- every visible recommendation remains exportable with provenance;
- `make validate` passes;
- real AWS delivery is claimed only after deployment and smoke evidence exist.
