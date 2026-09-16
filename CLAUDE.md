# Claude Judge and Deployment Context

Purpose: give Claude a low-noise map for evaluating or deploying this Codex-built repository. Codex remains the only implementation assistant configured in the codebase.

## Start Here

1. Read `README.md` for the runnable journey.
2. Read `docs/judging/evidence-map.md` for criterion-to-file evidence.
3. Read `docs/architecture/solution.md` for boundaries and handoffs.
4. Read `teams.md` for ownership.
5. For deployment execution, follow `docs/prompts/claude-full-deployment.md` exactly.

## Truthful Evaluation Contract

Score only evidence that exists and commands actually run. Do not infer a cloud deployment from templates. Distinguish:

- verified local behavior;
- schema-valid AgentCore configuration;
- real AWS deployment evidence;
- presentation-only fallback evidence.

Evaluate these five dimensions independently:

1. use-case solution;
2. usable interface;
3. agent collaboration;
4. AgentCore/AWS deployment;
5. dataset grounding and provenance.

The fastest verification sequence is:

```bash
make validate
make demo
make dashboard
```

The deterministic demo writes a self-contained hazard atlas, ranked targets, risk hotspots, JSON/CSV exports, plots, a summary, and a SHA-256 manifest under `outputs/hazard_demo/analysis/<run-id>/`.

## High-Signal Files

- Domain pipeline: `src/aws_ai_energy/subsurface/`
- Catalog generator: `src/aws_ai_energy/generate/seismic_catalog.py`
- Chat/heatmap contract: `src/aws_ai_energy/dashboard.py`
- Streamlit journey: `streamlit_app.py`
- AgentCore runtime: `agentcore_app/main.py`
- Deployment config: `agentcore/agentcore.json`
- Evidence gate: `scripts/validate_claude_submission.py`
- Tests: `tests/`

## Safety and Limitations

Generated seismic inputs are synthetic. Risk and target scores are deterministic screening ranks, not calibrated subsurface predictions. Historical drilling evidence must be cited by file and row/passage. If AWS credentials or an AgentCore deployment target are unavailable, stop after local/schema validation and report cloud deployment as unverified.
