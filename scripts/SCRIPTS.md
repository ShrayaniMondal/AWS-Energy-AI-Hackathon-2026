# Scripts Reference

Inventory of Python scripts and their functionality.

## Data Ingestion (Task 1)

| Script | Purpose |
|--------|---------|
| `config.py` | Central configuration — all data paths, constants, and field names. Single source of truth for file locations. |
| `data_loader.py` | Loads all data into memory: Corpus A (75 JSON DDRs), Corpus B (192-row CSV DDR), 13 supporting CSVs, narrative text chunks, and reference doc sections. Exposes `load_all()` for Streamlit caching. |
| `vector_index.py` | Builds a FAISS semantic search index over DDR narratives and reference docs. Uses Bedrock Titan embeddings with TF-IDF fallback. Exposes `build_index()` and `search()`. |

The loader defaults to `Hackathon/use-case-1/data` and accepts the `DRILLING_DATA_DIR` environment variable. Corpus A and Corpus B remain separate identifier spaces.

## Repository Documentation Toolbox

`src/aws_ai_energy/toolbox_docs.py` indexes repository Markdown plus public Python module/API docstrings into deterministic JSON. It preserves repository-relative citations and line ranges, excludes generated/staged dependencies, and validates `.codex/skills` before delivery. See `docs/toolbox-helper.md`.

## Key Functions

### data_loader.py
- `load_corpus_a()` — Returns DataFrame of 75 JSON DDRs (keyed on `well_name`)
- `load_corpus_b()` — Returns DataFrame of 192 tabular DDR rows (keyed on `well_id`)
- `load_supporting_csvs()` — Returns dict of 13 DataFrames (NPT log, bit records, benchmarks, etc.)
- `load_narrative_chunks()` — Extracts 267 narrative text passages tagged with source/well/date for citation
- `load_reference_docs()` — Splits 4 reference markdown docs into 34 indexed sections
- `load_all()` — One-call loader returning everything; designed for `@st.cache_data`

### vector_index.py
- `build_index(use_bedrock=True)` — Builds FAISS index; returns index + parallel chunk array
- `search(query, index_data, top_k=5)` — Semantic search returning ranked results with scores and source citations
