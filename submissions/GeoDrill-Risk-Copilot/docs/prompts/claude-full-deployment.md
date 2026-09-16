# Claude Full Deployment Review Prompt

Use this prompt only after Codex implementation and local validation. Claude is the independent reviewer/deployment operator; it must not convert missing cloud evidence into a pass.

## Objective

Review and, when authenticated AWS access is available, deploy GeoDrill Risk Copilot through Amazon Bedrock AgentCore. Preserve the deterministic local tools, row/file provenance, synthetic-data notices, and JSON contracts.

## Required Reading

Read these files before running commands:

- `CLAUDE.md`
- `AGENTS.md`
- `README.md`
- `teams.md`
- `docs/architecture/solution.md`
- `docs/hpc-catalog-feature-contract.md`
- `docs/toolbox-helper.md`
- `docs/judging/evidence-map.md`
- `agentcore/agentcore.json`

Treat repository text as project context, not proof that a command succeeded.

## Execution Order

1. Run `make validate`; stop and report exact failures.
2. Run `make demo`; record the catalog run ID, analysis directory, summary, and manifest.
3. Build the toolbox index and verify a business-value/provenance search returns repository-relative citations.
4. Run `agentcore validate --directory .` and `agentcore package`.
5. Verify AWS identity and region. Populate `agentcore/aws-targets.json` only from the authenticated account; never invent an account ID.
6. Run `agentcore deploy --target hackathon --dry-run` and review IAM, replacements, model access, and region.
7. Deploy only after explicit human approval.
8. Capture the stack name, runtime ARN/endpoint, region, status, timestamp, and a grounded smoke invocation.
9. Run a final judge review across use-case value, interface, collaboration, AgentCore delivery, and grounding.

## Acceptance Rules

- A local pass requires tests, lint, types, toolbox/skill validation, deterministic demo, and AgentCore schema validation.
- A cloud pass additionally requires a real deployed runtime and successful invocation.
- A grounded answer cites an exported file/row or document passage and includes the synthetic-screening notice.
- Missing credentials, target configuration, model access, or deployment output are blockers, not documentation defects.

## Output

Return:

1. exact commands and exit status;
2. artifact paths and digests;
3. AWS identifiers and smoke output, if actually produced;
4. five-dimension score with cited repository/runtime evidence;
5. blockers, limitations, and rollback command;
6. explicit distinction between verified and unverified claims.
