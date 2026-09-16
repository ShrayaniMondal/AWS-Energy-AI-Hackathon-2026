# Data Quality and Interpretation Notes

These notes prevent retrieval or agent layers from turning source ambiguity into an operational instruction.

## BOP Procedure Conflict

`Hackathon/use-case-1/data/reference_docs/bop_procedures.md` contains two incompatible test schedules/pressure descriptions:

- the early procedure section describes a routine test every 14 days and a high-pressure test at 70% of rated working pressure;
- a later section describes a low-pressure test every 7 days and a high-pressure test at rated working pressure.

The repository preserves the supplied document unchanged. Retrieval results must cite the exact section and flag the conflict. The application must not choose a test schedule or pressure from these passages without an operator-approved governing procedure. This is a human-review boundary, not a model inference task.

## Corpus Identifier Boundary

Corpus A uses `well_name`; Corpus B uses `well_id`. The two spaces do not cross-join. Shared formation lookups may be used only through an explicit analog workflow and must be described as analog evidence.

## Synthetic Subsurface Boundary

Generated wells, faults, horizons, and seismic attributes are synthetic. Scores are deterministic screening ranks. They are suitable for demo ranking and workflow integration, not reserves estimation, geosteering, or safety-critical drilling decisions.

## Retrieval Rule

When sources disagree, are missing, or do not support a claim, callers must return:

1. the conflicting or missing source locators;
2. the narrow facts each source actually states;
3. an explicit `human_review_required` outcome;
4. no synthesized operational instruction.
