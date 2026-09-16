# Judging Evidence Map

This map points judges and reviewers to the files that prove the submitted
journey. Evidence must be regenerated or revalidated before final submission.

| Judging dimension | Evidence source |
|---|---|
| Use-case solution | `docs/Use-Case-1-Drilling-Report-Analysis-Agent.md`, `docs/proposal/drilling-hazard-copilot.md`, `src/aws_ai_energy/subsurface/`, risk-ranked scoring in `scoring.py` and JSON/CSV exports in `export.py` |
| Usable interface | `generate/analyze_catalog.py`, `streamlit_app.py` when present, exported atlas and JSON bundles |
| Agent collaboration | `teams.md`, `.claude/prompts/implement-deliverable.md`, `CLAUDE.md` |
| AgentCore/AWS deployment | `agentcore/agentcore.json`, `agentcore/cdk/`, deployment logs and smoke output when captured |
| Dataset grounding | `docs/hpc-catalog-feature-contract.md`, catalog metadata, analyzer manifests, file/row citations, `tests/test_scoring_and_export.py` verifies provenance fields |

## Required Submission Evidence

- local validation commands that were actually run;
- deterministic demo output path and run identifier;
- JSON/CSV exports that preserve catalog IDs and source locators;
- dashboard or CLI transcript showing cited recommendations;
- AWS stack/runtime identifiers and smoke output, if cloud deployment is claimed.
