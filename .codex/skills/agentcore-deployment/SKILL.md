---
name: agentcore-deployment
description: Deploy GeoDrill through AgentCore with evidence.
version: 0.1.0
author: GeoDrill Team, Codex
license: MIT
platforms: [linux, macos, windows]
metadata:
  codex:
    tags: [aws, agentcore, deployment]
---

# AgentCore Deployment

Validate, package, deploy, and smoke-test the deterministic GeoDrill tools through Amazon Bedrock AgentCore. Separate local readiness from real AWS delivery.

## When to Use

- Modifying `agentcore/`, `agentcore_app/`, IAM, model configuration, or deployment runbooks.
- Preparing a cloud milestone or final hackathon submission.
- Reviewing claims about AWS deployment.

## Prerequisites

- AgentCore CLI, AWS CLI, Node.js, and Python project dependencies are installed.
- The active AWS identity and region are explicitly verified.
- `agentcore/aws-targets.json` contains the intended account and region without secrets.

## Procedure

1. Read `agentcore/agentcore.json`, `agentcore/.llm-context/`, and `docs/prompts/claude-full-deployment.md`.
2. Run `make validate` and stop on any failure.
3. Run `agentcore validate --directory .` and `agentcore package`; retain exact output.
4. Run `agentcore deploy --target hackathon --dry-run` and inspect replacements, permissions, and region.
5. Deploy only with an authenticated identity and explicit operator approval.
6. Capture stack name, runtime ARN or endpoint, region, deployment status, and timestamp.
7. Invoke the deployed runtime with a grounded prospect question and verify citations and synthetic-data notice.
8. Record smoke output and rollback commands without committing credentials or transient state.

## Pitfalls

- CodeZip packages must include every imported local module and runtime dependency.
- An empty or placeholder target file is not deployable evidence.
- A successful schema validation proves configuration shape, not runtime behavior.
- Bedrock model access and IAM permissions can fail independently of deployment.

## Verification

Cloud delivery passes only when schema validation, packaging, deployment, status, and a deployed smoke invocation all succeed. Otherwise report the exact completed stage and blocker.
