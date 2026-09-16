# AWS Energy AI Hackathon 2026

GeoDrill Risk Copilot combines a synthetic HPC seismic catalog with drilling report evidence so
features can produce traceable hazard screens, prospect rankings, and dashboard-ready exports.

## Use Case 1 — Drilling Report Analysis

Analyzing drilling reports using AI to extract insights, identify patterns, and generate actionable recommendations.

## Project Structure

```
├── data/raw/              # Raw drilling datasets
├── notebooks/             # Jupyter notebooks for exploration
├── scripts/               # Python scripts for processing & analysis
├── outputs/
│   ├── reports/           # Generated analysis reports
│   └── visualizations/    # Charts, plots, figures
└── docs/                  # Additional documentation
```

## Setup

```bash
pip install -r requirements.txt
```

For the repository-local development environment:

```bash
make bootstrap
make demo
make validate
```

All generated, analyzed, visualized, or agent-returned data must follow
`docs/hpc-catalog-feature-contract.md`: preserve catalog IDs, source rows, physical artifact paths,
and stable JSON/CSV exports so advanced dashboards can reload results after a restart.

## Team

- TODO: Add team members
