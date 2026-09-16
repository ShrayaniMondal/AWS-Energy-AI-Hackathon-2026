SHELL := /usr/bin/env bash
PYTHON ?= .venv/bin/python

.PHONY: bootstrap test test-coverage lint typecheck demo dashboard toolbox-index codex-validate validate claude-validate agentcore-validate agentcore-package agentcore-dev agentcore-deploy-dry-run

bootstrap:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e '.[dev,dashboard,agentcore]'

test:
	$(PYTHON) -m pytest

test-coverage:
	$(PYTHON) -m coverage run -m pytest
	$(PYTHON) -m coverage report
	$(PYTHON) -m coverage xml -o coverage.xml

lint:
	$(PYTHON) -m ruff check src tests generate scripts agentcore_app

typecheck:
	$(PYTHON) -m mypy

demo:
	$(PYTHON) -m generate.analyze_catalog demo --output-dir outputs/hazard_demo --seed 42 --top-n 20

dashboard:
	$(PYTHON) -m streamlit run streamlit_app.py --server.port 8501

toolbox-index:
	PYTHONPATH=src $(PYTHON) -m aws_ai_energy.toolbox_docs --root . --output artifacts/toolbox-index.json

codex-validate:
	PYTHONPATH=src $(PYTHON) -m aws_ai_energy.toolbox_docs --root . --validate-skills --output artifacts/toolbox-index.json

claude-validate:
	$(PYTHON) scripts/validate_claude_submission.py --repo .

agentcore-validate:
	agentcore validate --directory .

agentcore-package:
	agentcore package

agentcore-dev:
	agentcore dev

agentcore-deploy-dry-run:
	agentcore deploy --target hackathon --dry-run

validate: lint typecheck test-coverage codex-validate claude-validate agentcore-validate
