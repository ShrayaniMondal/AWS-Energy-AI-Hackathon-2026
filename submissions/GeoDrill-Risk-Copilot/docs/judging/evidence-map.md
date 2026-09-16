# Judging Evidence Map

This map points judges and reviewers to the files that prove the submitted
journey. Evidence must be regenerated or revalidated before final submission.

| Judging dimension | Evidence source |
|---|---|
| Use-case solution and business value | `Hackathon/use-case-1/one-pager.md`, `docs/proposal/drilling-hazard-copilot.md`, `README.md`, `src/aws_ai_energy/subsurface/` |
| Usable interface and caller support | `generate/analyze_catalog.py`, `src/aws_ai_energy/dashboard.py`, `src/aws_ai_energy/toolbox_docs.py`, exported atlas and JSON bundles |
| Team and agent collaboration | `teams.md`, `AGENTS.md`, `.codex/skills/`, independent Gemini/Claude review output |
| AgentCore/AWS deployment | `agentcore/agentcore.json`, `agentcore/cdk/`, `agentcore_app/`, deployment logs and smoke output when captured |
| Dataset grounding and provenance | `docs/hpc-catalog-feature-contract.md`, `docs/subsurface-digital-twin-seed.md`, `docs/toolbox-helper.md`, catalog metadata, analyzer manifests, file/row citations |

## Required Submission Evidence

- local validation commands that were actually run;
- deterministic demo output path and run identifier;
- digital-twin seed endpoints under `metadata/runs/<run_id>/digital_twin/`;
- JSON/CSV exports that preserve catalog IDs and source locators;
- dashboard or CLI transcript showing cited recommendations;
- AWS stack/runtime identifiers and smoke output, if cloud deployment is claimed.
