SHELL := /usr/bin/env bash
PYTHON ?= .venv/bin/python

.PHONY: bootstrap test lint typecheck demo dashboard validate claude-validate agentcore-validate agentcore-package agentcore-dev agentcore-deploy-dry-run

bootstrap:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e '.[dev,dashboard,agentcore]'

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests generate scripts agentcore_app

typecheck:
	$(PYTHON) -m mypy

demo:
	$(PYTHON) -m generate.analyze_catalog demo --output-dir outputs/hazard_demo --seed 42 --top-n 20

dashboard:
	$(PYTHON) -m streamlit run streamlit_app.py --server.port 8501

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

validate: lint typecheck test claude-validate agentcore-validate
