# Scripts Reference

Inventory of Python scripts and their functionality.

## Data Ingestion (Task 1)

| Script | Purpose |
|--------|---------|
| `config.py` | Central configuration — all data paths, constants, and field names. Single source of truth for file locations. |
| `data_loader.py` | Loads all data into memory: Corpus A (75 JSON DDRs), Corpus B (192-row CSV DDR), 13 supporting CSVs, narrative text chunks, and reference doc sections. Exposes `load_all()` for Streamlit caching. |
| `vector_index.py` | Builds a FAISS semantic search index over 301 text chunks (DDR narratives + reference docs). Uses Bedrock Titan embeddings with TF-IDF fallback. Exposes `build_index()` and `search()`. |

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

## Dashboard & Heatmap (Chat Feature)

| Script | Purpose |
|--------|---------|
| `src/aws_ai_energy/dashboard.py` | Chat-driven heatmap builder. Parses natural-language feature requests into validated feature lists, builds deterministic JSON payloads with per-point provenance (catalog IDs), and locates analysis bundles. |
| `streamlit_app_sm_test.py` | Streamlit dashboard with chat interface and heatmap visualization. Chat converts user requests into heatmaps; supports scatter plots, data tables, and JSON export with download. |

### dashboard.py
- `parse_feature_request(prompt)` — Validates prompt against supported features (wells, faults, horizons, reservoir_probability, physical_data_provenance); raises `DashboardDataError` for unsupported requests
- `build_heatmap_payload(points_path, prompt, max_points, run_id)` — Deterministic: same inputs always produce identical JSON output with per-point provenance and synthetic-data notice
- `find_latest_analysis(base_dir)` — Finds newest analysis run directory containing a `manifest.json`
- `heatmap_payload_to_json(payload, path)` — Writes payload to JSON file for download

### streamlit_app_sm_test.py
- `render_chat()` — Chat interface; validates requests, builds payloads, rejects unsupported features
- `render_heatmap()` — Scatter plot + data table + JSON export with provenance counts
- `render_sidebar()` — Feature list, data status, synthetic-data notice
